Refactoring Types: ['Extract Method']
rdpress/android/ui/main/MeFragment.java
package org.wordpress.android.ui.main;

import android.annotation.TargetApi;
import android.app.AlertDialog;
import android.app.Fragment;
import android.content.DialogInterface;
import android.graphics.Outline;
import android.os.Build;
import android.os.Bundle;
import android.text.TextUtils;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewOutlineProvider;
import android.widget.TextView;

import org.wordpress.android.R;
import org.wordpress.android.WordPress;
import org.wordpress.android.models.Account;
import org.wordpress.android.models.AccountHelper;
import org.wordpress.android.ui.ActivityId;
import org.wordpress.android.ui.ActivityLauncher;
import org.wordpress.android.util.GravatarUtils;
import org.wordpress.android.util.HelpshiftHelper.Tag;
import org.wordpress.android.widgets.WPNetworkImageView;

public class MeFragment extends Fragment {

    private ViewGroup mAvatarFrame;
    private WPNetworkImageView mAvatarImageView;
    private TextView mDisplayNameTextView;
    private TextView mUsernameTextView;
    private TextView mLoginLogoutTextView;

    public static MeFragment newInstance() {
        return new MeFragment();
    }

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container,
                             Bundle savedInstanceState) {
        final ViewGroup rootView = (ViewGroup) inflater.inflate(R.layout.me_fragment, container, false);

        mAvatarFrame = (ViewGroup) rootView.findViewById(R.id.frame_avatar);
        mAvatarImageView = (WPNetworkImageView) rootView.findViewById(R.id.me_avatar);
        mDisplayNameTextView = (TextView) rootView.findViewById(R.id.me_display_name);
        mUsernameTextView = (TextView) rootView.findViewById(R.id.me_username);
        mLoginLogoutTextView = (TextView) rootView.findViewById(R.id.me_login_logout_text_view);

        addDropShadowToAvatar();
        refreshAccountDetails();

        rootView.findViewById(R.id.row_settings).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                ActivityLauncher.viewAccountSettings(getActivity());
            }
        });

        rootView.findViewById(R.id.row_support).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                ActivityLauncher.viewHelpAndSupport(getActivity(), Tag.ORIGIN_ME_SCREEN_HELP);
            }
        });

        rootView.findViewById(R.id.row_logout).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                if (AccountHelper.isSignedInWordPressDotCom()) {
                    signOutWordPressComWithConfirmation();
                } else {
                    ActivityLauncher.showSignInForResult(getActivity());
                }
            }
        });

        return rootView;
    }

    /*
     * Workaround for the ViewPager that only shows one page at a time, but the pre-cached fragments are also put to "visible" state
     * (actually invisible). So we can't keep track of which screen is visible on the screen by using the onResume method of Fragment.
     *
     * Note that this is only the half-part of the solution that keeps tracks of last active screen with the ViewPager.
     * WPMainActivity contains the other part of the code in its onResume method. In that method we track the current active screen
     * for situations like the following: Me Fragment -> Help & Support -> back to Me fragment, that's a case where
     * setMenuVisibility is not called on Fragments contained in the ViewPager;
     *
     */
    @Override
    public void setMenuVisibility(final boolean visible) {
        super.setMenuVisibility(visible);
        if (visible) {
            ActivityId.trackLastActivity(ActivityId.ME);
        }
    }

    /*
     * adds a circular drop shadow to the avatar's parent view (Lollipop+ only)
     */
    @TargetApi(Build.VERSION_CODES.LOLLIPOP)
    private void addDropShadowToAvatar() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            mAvatarFrame.setOutlineProvider(new ViewOutlineProvider() {
                @Override
                public void getOutline(View view, Outline outline) {
                    outline.setOval(0, 0, view.getWidth(), view.getHeight());
                }
            });
            mAvatarFrame.setElevation(mAvatarFrame.getResources().getDimensionPixelSize(R.dimen.card_elevation));
        }
    }

    private void refreshAccountDetails() {
        // we only want to show user details for WordPress.com users
        if (AccountHelper.isSignedInWordPressDotCom()) {
            Account defaultAccount = AccountHelper.getDefaultAccount();

            mDisplayNameTextView.setVisibility(View.VISIBLE);
            mUsernameTextView.setVisibility(View.VISIBLE);
            mAvatarFrame.setVisibility(View.VISIBLE);

            int avatarSz = getResources().getDimensionPixelSize(R.dimen.avatar_sz_large);
            String avatarUrl = GravatarUtils.fixGravatarUrl(defaultAccount.getAvatarUrl(), avatarSz);
            mAvatarImageView.setImageUrl(avatarUrl, WPNetworkImageView.ImageType.AVATAR);

            mUsernameTextView.setText("@" + defaultAccount.getUserName());
            mLoginLogoutTextView.setText(R.string.me_disconnect_from_wordpress_com);

            String displayName = defaultAccount.getDisplayName();
            if (!TextUtils.isEmpty(displayName)) {
                mDisplayNameTextView.setText(displayName);
            } else {
                mDisplayNameTextView.setText(defaultAccount.getUserName());
            }
        } else {
            mDisplayNameTextView.setVisibility(View.GONE);
            mUsernameTextView.setVisibility(View.GONE);
            mAvatarFrame.setVisibility(View.GONE);
            mLoginLogoutTextView.setText(R.string.me_connect_to_wordpress_com);
        }
    }

    private void signOutWordPressComWithConfirmation() {
        String message = String.format(getString(R.string.sign_out_wpcom_confirm), AccountHelper.getDefaultAccount()
                .getUserName());

        new AlertDialog.Builder(getActivity())
                .setMessage(message)
                .setPositiveButton(R.string.signout, new DialogInterface.OnClickListener() {
                    public void onClick(DialogInterface dialog, int whichButton) {
                        signOutWordPressCom();
                    }
                })
                .setNegativeButton(R.string.cancel, null)
                .setCancelable(true)
                .create().show();
    }

    private void signOutWordPressCom() {
        // note that signing out sends a CoreEvents.UserSignedOutWordPressCom EventBus event,
        // which will cause the main activity to recreate this fragment
        WordPress.signOutWordPressComAsyncWithProgressBar(getActivity());
    }
}


File: WordPress/src/main/java/org/wordpress/android/ui/main/MySiteFragment.java
package org.wordpress.android.ui.main;

import android.app.Activity;
import android.app.Fragment;
import android.content.Intent;
import android.os.Bundle;
import android.text.TextUtils;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.view.animation.AlphaAnimation;
import android.view.animation.Animation;
import android.view.animation.Interpolator;
import android.widget.LinearLayout;
import android.widget.RelativeLayout;
import android.widget.ScrollView;

import org.wordpress.android.R;
import org.wordpress.android.WordPress;
import org.wordpress.android.models.Blog;
import org.wordpress.android.ui.ActivityId;
import org.wordpress.android.ui.ActivityLauncher;
import org.wordpress.android.ui.RequestCodes;
import org.wordpress.android.ui.posts.EditPostActivity;
import org.wordpress.android.ui.stats.service.StatsService;
import org.wordpress.android.ui.themes.ThemeBrowserActivity;
import org.wordpress.android.util.AniUtils;
import org.wordpress.android.util.CoreEvents;
import org.wordpress.android.util.GravatarUtils;
import org.wordpress.android.util.ServiceUtils;
import org.wordpress.android.util.StringUtils;
import org.wordpress.android.widgets.WPNetworkImageView;
import org.wordpress.android.widgets.WPTextView;

import de.greenrobot.event.EventBus;

public class MySiteFragment extends Fragment
        implements WPMainActivity.OnScrollToTopListener {

    private static final long ALERT_ANIM_OFFSET_MS   = 1000l;
    private static final long ALERT_ANIM_DURATION_MS = 1000l;

    private WPNetworkImageView mBlavatarImageView;
    private WPTextView mBlogTitleTextView;
    private WPTextView mBlogSubtitleTextView;
    private LinearLayout mLookAndFeelHeader;
    private RelativeLayout mThemesContainer;
    private View mFabView;

    private int mFabTargetYTranslation;
    private int mBlavatarSz;

    private Blog mBlog;

    public static MySiteFragment newInstance() {
        return new MySiteFragment();
    }

    public void setBlog(Blog blog) {
        mBlog = blog;
        refreshBlogDetails();
    }

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        mBlog = WordPress.getCurrentBlog();
    }

    @Override
    public void onResume() {
        super.onResume();
        if (ServiceUtils.isServiceRunning(getActivity(), StatsService.class)) {
            getActivity().stopService(new Intent(getActivity(), StatsService.class));
        }
    }

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container,
                             Bundle savedInstanceState) {
        final ViewGroup rootView = (ViewGroup) inflater.inflate(R.layout.my_site_fragment, container, false);

        int fabHeight = getResources().getDimensionPixelSize(com.getbase.floatingactionbutton.R.dimen.fab_size_normal);
        int fabMargin = getResources().getDimensionPixelSize(R.dimen.fab_margin);
        mFabTargetYTranslation = (fabHeight + fabMargin) * 2;
        mBlavatarSz = getResources().getDimensionPixelSize(R.dimen.blavatar_sz_small);

        mBlavatarImageView = (WPNetworkImageView) rootView.findViewById(R.id.my_site_blavatar);
        mBlogTitleTextView = (WPTextView) rootView.findViewById(R.id.my_site_title_label);
        mBlogSubtitleTextView = (WPTextView) rootView.findViewById(R.id.my_site_subtitle_label);
        mLookAndFeelHeader = (LinearLayout) rootView.findViewById(R.id.my_site_look_and_feel_header);
        mThemesContainer = (RelativeLayout) rootView.findViewById(R.id.row_themes);
        mFabView = rootView.findViewById(R.id.fab_button);

        mFabView.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                ActivityLauncher.addNewBlogPostOrPageForResult(getActivity(), mBlog, false);
            }
        });

        rootView.findViewById(R.id.switch_site).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                showSitePicker();
            }
        });

        rootView.findViewById(R.id.row_view_site).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                ActivityLauncher.viewCurrentSite(getActivity());
            }
        });

        rootView.findViewById(R.id.row_stats).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                if (mBlog != null) {
                    ActivityLauncher.viewBlogStats(getActivity(), mBlog.getLocalTableBlogId());
                }
            }
        });

        rootView.findViewById(R.id.row_blog_posts).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                ActivityLauncher.viewCurrentBlogPosts(getActivity());
            }
        });

        rootView.findViewById(R.id.row_media).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                ActivityLauncher.viewCurrentBlogMedia(getActivity());
            }
        });

        rootView.findViewById(R.id.row_pages).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                ActivityLauncher.viewCurrentBlogPages(getActivity());
            }
        });

        rootView.findViewById(R.id.row_comments).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                ActivityLauncher.viewCurrentBlogComments(getActivity());
            }
        });

        mThemesContainer.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                ActivityLauncher.viewCurrentBlogThemes(getActivity());
            }
        });

        rootView.findViewById(R.id.row_settings).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                ActivityLauncher.viewBlogSettingsForResult(getActivity(), mBlog);
            }
        });

        rootView.findViewById(R.id.row_admin).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                ActivityLauncher.viewBlogAdmin(getActivity(), mBlog);
            }
        });

        refreshBlogDetails();

        return rootView;
    }

    @Override
    public void setMenuVisibility(final boolean visible) {
        super.setMenuVisibility(visible);
        if (visible) {
            ActivityId.trackLastActivity(ActivityId.MY_SITE);
        }
    }

    private void showSitePicker() {
        if (isAdded()) {
            AniUtils.showFab(mFabView, false);
            int localBlogId = (mBlog != null ? mBlog.getLocalTableBlogId() : 0);
            ActivityLauncher.showSitePickerForResult(getActivity(), localBlogId);
        }
    }

    @Override
    public void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        switch (requestCode) {
            case RequestCodes.SITE_PICKER:
                // RESULT_OK = site picker changed the current blog
                if (resultCode == Activity.RESULT_OK) {
                    setBlog(WordPress.getCurrentBlog());
                }
                // redisplay the hidden fab after a short delay
                long delayMs = getResources().getInteger(android.R.integer.config_shortAnimTime);
                AniUtils.showFabDelayed(mFabView, true, delayMs);
                break;

            case RequestCodes.EDIT_POST:
                // if user returned from adding a post via the FAB and it was saved as a local
                // draft, briefly animate the background of the "Blog posts" view to give the
                // user a cue as to where to go to return to that post
                if (resultCode == Activity.RESULT_OK
                        && getView() != null
                        && data != null
                        && data.getBooleanExtra(EditPostActivity.EXTRA_SAVED_AS_LOCAL_DRAFT, false)) {
                    showAlert(getView().findViewById(R.id.postsGlowBackground));
                }
                break;
        }
    }

    private void showAlert(View view) {
        if (isAdded() && view != null) {
            Animation highlightAnimation = new AlphaAnimation(0.0f, 1.0f);
            highlightAnimation.setInterpolator(new Interpolator() {
                private float bounce(float t) {
                    return t * t * 24.0f;
                }

                public float getInterpolation(float t) {
                    t *= 1.1226f;
                    if (t < 0.184f) return bounce(t);
                    else if (t < 0.545f) return bounce(t - 0.40719f);
                    else if (t < 0.7275f) return -bounce(t - 0.6126f) + 1.0f;
                    else return 0.0f;
                }
            });
            highlightAnimation.setStartOffset(ALERT_ANIM_OFFSET_MS);
            highlightAnimation.setRepeatCount(1);
            highlightAnimation.setRepeatMode(Animation.RESTART);
            highlightAnimation.setDuration(ALERT_ANIM_DURATION_MS);
            view.startAnimation(highlightAnimation);
        }
    }

    private void refreshBlogDetails() {
        if (!isAdded() || mBlog == null) {
            return;
        }

        int themesVisibility = ThemeBrowserActivity.isAccessible() ? View.VISIBLE : View.GONE;
        mLookAndFeelHeader.setVisibility(themesVisibility);
        mThemesContainer.setVisibility(themesVisibility);

        mBlavatarImageView.setImageUrl(GravatarUtils.blavatarFromUrl(mBlog.getUrl(), mBlavatarSz), WPNetworkImageView.ImageType.BLAVATAR);

        String blogName = StringUtils.unescapeHTML(mBlog.getBlogName());
        String hostName = StringUtils.getHost(mBlog.getUrl());
        String blogTitle = TextUtils.isEmpty(blogName) ? hostName : blogName;

        mBlogTitleTextView.setText(blogTitle);
        mBlogSubtitleTextView.setText(hostName);
    }

    @Override
    public void onScrollToTop() {
        if (isAdded()) {
            ScrollView scrollView = (ScrollView) getView().findViewById(R.id.scroll_view);
            scrollView.smoothScrollTo(0, 0);
        }
    }

    @Override
    public void onStop() {
        EventBus.getDefault().unregister(this);
        super.onStop();
    }

    @Override
    public void onStart() {
        super.onStart();
        EventBus.getDefault().register(this);
    }

    /*
     * animate the fab as the users scrolls the "My Site" page in the main activity's ViewPager
     */
    @SuppressWarnings("unused")
    public void onEventMainThread(CoreEvents.MainViewPagerScrolled event) {
        mFabView.setTranslationY(mFabTargetYTranslation * event.mXOffset);
    }
}


File: WordPress/src/main/java/org/wordpress/android/ui/main/WPMainActivity.java
package org.wordpress.android.ui.main;

import android.annotation.TargetApi;
import android.app.Activity;
import android.app.Fragment;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.support.v4.view.ViewPager;
import android.text.TextUtils;
import android.view.View;

import com.simperium.client.Bucket;
import com.simperium.client.BucketObjectMissingException;

import org.wordpress.android.GCMIntentService;
import org.wordpress.android.R;
import org.wordpress.android.WordPress;
import org.wordpress.android.analytics.AnalyticsTracker;
import org.wordpress.android.models.AccountHelper;
import org.wordpress.android.models.CommentStatus;
import org.wordpress.android.models.Note;
import org.wordpress.android.networking.SelfSignedSSLCertsManager;
import org.wordpress.android.ui.ActivityId;
import org.wordpress.android.ui.ActivityLauncher;
import org.wordpress.android.ui.RequestCodes;
import org.wordpress.android.ui.media.MediaAddFragment;
import org.wordpress.android.ui.notifications.NotificationEvents;
import org.wordpress.android.ui.notifications.NotificationsListFragment;
import org.wordpress.android.ui.notifications.utils.NotificationsUtils;
import org.wordpress.android.ui.notifications.utils.SimperiumUtils;
import org.wordpress.android.ui.prefs.AppPrefs;
import org.wordpress.android.ui.prefs.BlogPreferencesActivity;
import org.wordpress.android.ui.prefs.SettingsFragment;
import org.wordpress.android.ui.reader.ReaderEvents;
import org.wordpress.android.ui.reader.ReaderPostListFragment;
import org.wordpress.android.util.AppLog;
import org.wordpress.android.util.AppLog.T;
import org.wordpress.android.util.AuthenticationDialogUtils;
import org.wordpress.android.util.CoreEvents;
import org.wordpress.android.util.CoreEvents.MainViewPagerScrolled;
import org.wordpress.android.util.CoreEvents.UserSignedOutCompletely;
import org.wordpress.android.util.CoreEvents.UserSignedOutWordPressCom;
import org.wordpress.android.util.DisplayUtils;
import org.wordpress.android.util.StringUtils;
import org.wordpress.android.util.ToastUtils;
import org.wordpress.android.widgets.SlidingTabLayout;
import org.wordpress.android.widgets.WPViewPager;

import de.greenrobot.event.EventBus;

/**
 * Main activity which hosts sites, reader, me and notifications tabs
 */
public class WPMainActivity extends Activity
    implements ViewPager.OnPageChangeListener,
        SlidingTabLayout.SingleTabClickListener,
        MediaAddFragment.MediaAddFragmentCallback,
        Bucket.Listener<Note> {
    private WPViewPager mViewPager;
    private SlidingTabLayout mTabs;
    private WPMainTabAdapter mTabAdapter;

    public static final String ARG_OPENED_FROM_PUSH = "opened_from_push";

    /*
     * tab fragments implement this if their contents can be scrolled, called when user
     * requests to scroll to the top
     */
    public interface OnScrollToTopListener {
        void onScrollToTop();
    }

    @Override
    public void onCreate(Bundle savedInstanceState) {
        setStatusBarColor();

        super.onCreate(savedInstanceState);
        setContentView(R.layout.main_activity);

        mViewPager = (WPViewPager) findViewById(R.id.viewpager_main);
        mTabAdapter = new WPMainTabAdapter(getFragmentManager());
        mViewPager.setAdapter(mTabAdapter);

        mTabs = (SlidingTabLayout) findViewById(R.id.sliding_tabs);
        mTabs.setSelectedIndicatorColors(getResources().getColor(R.color.tab_indicator));

        // tabs are left-aligned rather than evenly distributed in landscape
        mTabs.setDistributeEvenly(!DisplayUtils.isLandscape(this));

        Integer icons[] = {R.drawable.main_tab_sites,
                           R.drawable.main_tab_reader,
                           R.drawable.main_tab_me,
                           R.drawable.main_tab_notifications};
        mTabs.setCustomTabView(R.layout.tab_icon, R.id.tab_icon, R.id.tab_badge, icons);

        // content descriptions
        mTabs.setContentDescription(WPMainTabAdapter.TAB_MY_SITE, getString(R.string.tabbar_accessibility_label_my_site));
        mTabs.setContentDescription(WPMainTabAdapter.TAB_READER, getString(R.string.reader));
        mTabs.setContentDescription(WPMainTabAdapter.TAB_ME, getString(R.string.tabbar_accessibility_label_me));
        mTabs.setContentDescription(WPMainTabAdapter.TAB_NOTIFS, getString(R.string.notifications));

        mTabs.setViewPager(mViewPager);
        mTabs.setOnSingleTabClickListener(this);

        // page change listener must be set on the tab layout rather than the ViewPager
        mTabs.setOnPageChangeListener(this);

        if (savedInstanceState == null) {
            if (AccountHelper.isSignedIn()) {
                // open note detail if activity called from a push, otherwise return to the tab
                // that was showing last time
                boolean openedFromPush = (getIntent() != null && getIntent().getBooleanExtra(ARG_OPENED_FROM_PUSH,
                        false));
                if (openedFromPush) {
                    getIntent().putExtra(ARG_OPENED_FROM_PUSH, false);
                    launchWithNoteId();
                } else {
                    int position = AppPrefs.getMainTabIndex();
                    if (mTabAdapter.isValidPosition(position) && position != mViewPager.getCurrentItem()) {
                        mViewPager.setCurrentItem(position);
                    }
                }
            } else {
                ActivityLauncher.showSignInForResult(this);
            }
        }
    }

    @TargetApi(Build.VERSION_CODES.LOLLIPOP)
    private void setStatusBarColor() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            getWindow().setStatusBarColor(getResources().getColor(R.color.status_bar_tint));
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        AppLog.i(T.MAIN, "main activity > new intent");
        if (intent.hasExtra(NotificationsListFragment.NOTE_ID_EXTRA)) {
            launchWithNoteId();
        }
    }

    /*
     * called when app is launched from a push notification, switches to the notification tab
     * and opens the desired note detail
     */
    private void launchWithNoteId() {
        if (isFinishing() || getIntent() == null) return;

        // Check for push authorization request
        if (getIntent().hasExtra(NotificationsUtils.ARG_PUSH_AUTH_TOKEN)) {
            Bundle extras = getIntent().getExtras();
            String token = extras.getString(NotificationsUtils.ARG_PUSH_AUTH_TOKEN, "");
            String title = extras.getString(NotificationsUtils.ARG_PUSH_AUTH_TITLE, "");
            String message = extras.getString(NotificationsUtils.ARG_PUSH_AUTH_MESSAGE, "");
            long expires = extras.getLong(NotificationsUtils.ARG_PUSH_AUTH_EXPIRES, 0);

            long now = System.currentTimeMillis() / 1000;
            if (expires > 0 && now > expires) {
                // Show a toast if the user took too long to open the notification
                ToastUtils.showToast(this, R.string.push_auth_expired, ToastUtils.Duration.LONG);
                AnalyticsTracker.track(AnalyticsTracker.Stat.PUSH_AUTHENTICATION_EXPIRED);
            } else {
                NotificationsUtils.showPushAuthAlert(this, token, title, message);
            }
        }

        mViewPager.setCurrentItem(WPMainTabAdapter.TAB_NOTIFS);

        String noteId = getIntent().getStringExtra(NotificationsListFragment.NOTE_ID_EXTRA);
        boolean shouldShowKeyboard = getIntent().getBooleanExtra(NotificationsListFragment.NOTE_INSTANT_REPLY_EXTRA, false);

        if (!TextUtils.isEmpty(noteId)) {
            NotificationsListFragment.openNote(this, noteId, shouldShowKeyboard, false);
            GCMIntentService.clearNotificationsMap();
        }
    }

    @Override
    public void onPageSelected(int position) {
        // remember the index of this page
        AppPrefs.setMainTabIndex(position);

        switch (position) {
            case WPMainTabAdapter.TAB_NOTIFS:
                if (getNotificationListFragment() != null) {
                    getNotificationListFragment().updateLastSeenTime();
                    mTabs.setBadge(WPMainTabAdapter.TAB_NOTIFS, false);
                }
                break;
        }
    }

    @Override
    public void onPageScrollStateChanged(int state) {
        // noop
    }

    @Override
    public void onPageScrolled(int position, float positionOffset, int positionOffsetPixels) {
        // fire event if the "My Site" page is being scrolled so the fragment can
        // animate its fab to match
        if (position == WPMainTabAdapter.TAB_MY_SITE) {
            EventBus.getDefault().post(new MainViewPagerScrolled(positionOffset));
        }
    }

    /*
     * user tapped a tab above the viewPager - detect when the active tab is clicked and scroll
     * the fragment to the top if available
     */
    @Override
    public void onTabClick(View view, int position) {
        if (position == mViewPager.getCurrentItem()) {
            Fragment fragment = mTabAdapter.getFragment(position);
            if (fragment instanceof OnScrollToTopListener) {
                ((OnScrollToTopListener) fragment).onScrollToTop();
            }
        }
    }

    @Override
    protected void onPause() {
        if (SimperiumUtils.getNotesBucket() != null) {
            SimperiumUtils.getNotesBucket().removeListener(this);
        }

        super.onPause();
    }

    @Override
    protected void onStop() {
        EventBus.getDefault().unregister(this);
        super.onStop();
    }

    @Override
    protected void onStart() {
        super.onStart();
        EventBus.getDefault().register(this);
    }

    @Override
    protected void onResume() {
        super.onResume();

        // Start listening to Simperium Note bucket
        if (SimperiumUtils.getNotesBucket() != null) {
            SimperiumUtils.getNotesBucket().addListener(this);
        }
        checkNoteBadge();

        // We need to track the current item on the screen when this activity is resumed.
        // Ex: Notifications -> notifications detail -> back to notifications
        int position = (mViewPager.getCurrentItem());
        switch (position) {
            case WPMainTabAdapter.TAB_MY_SITE:
                ActivityId.trackLastActivity(ActivityId.MY_SITE);
                break;
            case WPMainTabAdapter.TAB_READER:
                ActivityId.trackLastActivity(ActivityId.READER);
                break;
            case WPMainTabAdapter.TAB_ME:
                ActivityId.trackLastActivity(ActivityId.ME);
                break;
            case WPMainTabAdapter.TAB_NOTIFS:
                ActivityId.trackLastActivity(ActivityId.NOTIFICATIONS);
                break;
            default:
                break;
        }
    }

    /*
     * re-create the fragment adapter so all its fragments are also re-created - used when
     * user signs in/out so the fragments reflect the active account
     */
    private void resetFragments() {
        AppLog.i(AppLog.T.MAIN, "main activity > reset fragments");

        // remove the event that determines when followed tags/blogs are updated so they're
        // updated when the fragment is recreated (necessary after signin/disconnect)
        EventBus.getDefault().removeStickyEvent(ReaderEvents.UpdatedFollowedTagsAndBlogs.class);

        // remember the current tab position, then recreate the adapter so new fragments are created
        int position = mViewPager.getCurrentItem();
        mTabAdapter = new WPMainTabAdapter(getFragmentManager());
        mViewPager.setAdapter(mTabAdapter);

        // restore previous position
        if (mTabAdapter.isValidPosition(position)) {
            mViewPager.setCurrentItem(position);
        }
    }

    private void moderateCommentOnActivityResult(Intent data) {
        try {
            if (SimperiumUtils.getNotesBucket() != null) {
                Note note = SimperiumUtils.getNotesBucket().get(StringUtils.notNullStr(data.getStringExtra
                        (NotificationsListFragment.NOTE_MODERATE_ID_EXTRA)));
                CommentStatus status = CommentStatus.fromString(data.getStringExtra(
                        NotificationsListFragment.NOTE_MODERATE_STATUS_EXTRA));
                NotificationsUtils.moderateCommentForNote(note, status, this);
            }
        } catch (BucketObjectMissingException e) {
            AppLog.e(T.NOTIFS, e);
        }
    }

    @Override
    public void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        switch (requestCode) {
            case RequestCodes.EDIT_POST:
                if (resultCode == RESULT_OK) {
                    MySiteFragment mySiteFragment = getMySiteFragment();
                    if (mySiteFragment != null) {
                        mySiteFragment.onActivityResult(requestCode, resultCode, data);
                    }
                }
                break;
            case RequestCodes.READER_SUBS:
            case RequestCodes.READER_REBLOG:
                ReaderPostListFragment readerFragment = getReaderListFragment();
                if (readerFragment != null) {
                    readerFragment.onActivityResult(requestCode, resultCode, data);
                }
                break;
            case RequestCodes.ADD_ACCOUNT:
                if (resultCode == RESULT_OK) {
                    WordPress.registerForCloudMessaging(this);
                    resetFragments();
                } else if (!AccountHelper.isSignedIn()) {
                    // can't do anything if user isn't signed in (either to wp.com or self-hosted)
                    finish();
                }
                break;
            case RequestCodes.REAUTHENTICATE:
                if (resultCode == RESULT_CANCELED) {
                    ActivityLauncher.showSignInForResult(this);
                } else {
                    WordPress.registerForCloudMessaging(this);
                }
                break;
            case RequestCodes.NOTE_DETAIL:
                if (resultCode == RESULT_OK && data != null) {
                    moderateCommentOnActivityResult(data);
                }
                break;
            case RequestCodes.SITE_PICKER:
                if (getMySiteFragment() != null) {
                    getMySiteFragment().onActivityResult(requestCode, resultCode, data);
                }
                break;
            case RequestCodes.BLOG_SETTINGS:
                if (resultCode == BlogPreferencesActivity.RESULT_BLOG_REMOVED) {
                    // user removed the current (self-hosted) blog from blog settings
                    if (!AccountHelper.isSignedIn()) {
                        ActivityLauncher.showSignInForResult(this);
                    } else {
                        MySiteFragment mySiteFragment = getMySiteFragment();
                        if (mySiteFragment != null) {
                            mySiteFragment.setBlog(WordPress.getCurrentBlog());
                        }
                    }
                }
                break;
            case RequestCodes.ACCOUNT_SETTINGS:
                if (resultCode == SettingsFragment.LANGUAGE_CHANGED) {
                    resetFragments();
                }
                break;
        }
    }

    /*
     * returns the reader list fragment from the reader tab
     */
    private ReaderPostListFragment getReaderListFragment() {
        return getFragmentByPosition(WPMainTabAdapter.TAB_READER, ReaderPostListFragment.class);
    }

    /*
     * returns the notification list fragment from the notification tab
     */
    private NotificationsListFragment getNotificationListFragment() {
        return getFragmentByPosition(WPMainTabAdapter.TAB_NOTIFS, NotificationsListFragment.class);
    }

    /*
     * returns the my site fragment from the sites tab
     */
    public MySiteFragment getMySiteFragment() {
        return getFragmentByPosition(WPMainTabAdapter.TAB_MY_SITE, MySiteFragment.class);
    }

    private <T> T getFragmentByPosition(int position, Class<T> type) {
        Fragment fragment = mTabAdapter != null ? mTabAdapter.getFragment(position) : null;

        if (fragment != null && type.isInstance(fragment)) {
            return type.cast(fragment);
        }

        return null;
    }

    /*
     * badges the notifications tab depending on whether there are unread notes
     */
    private boolean mIsCheckingNoteBadge;
    private void checkNoteBadge() {
        if (mIsCheckingNoteBadge) {
            AppLog.v(AppLog.T.MAIN, "main activity > already checking note badge");
            return;
        } else if (isViewingNotificationsTab()) {
            // Don't show the badge if the notifications tab is active
            if (mTabs.isBadged(WPMainTabAdapter.TAB_NOTIFS)) {
                mTabs.setBadge(WPMainTabAdapter.TAB_NOTIFS, false);
            }

            return;
        }

        mIsCheckingNoteBadge = true;
        new Thread() {
            @Override
            public void run() {
                final boolean hasUnreadNotes = SimperiumUtils.hasUnreadNotes();
                boolean isBadged = mTabs.isBadged(WPMainTabAdapter.TAB_NOTIFS);
                if (hasUnreadNotes != isBadged) {
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            mTabs.setBadge(WPMainTabAdapter.TAB_NOTIFS, hasUnreadNotes);
                            mIsCheckingNoteBadge = false;
                        }
                    });
                } else {
                    mIsCheckingNoteBadge = false;
                }
            }
        }.start();
    }

    private boolean isViewingNotificationsTab() {
        return mViewPager.getCurrentItem() == WPMainTabAdapter.TAB_NOTIFS;
    }

    // Events

    @SuppressWarnings("unused")
    public void onEventMainThread(UserSignedOutWordPressCom event) {
        resetFragments();
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(UserSignedOutCompletely event) {
        ActivityLauncher.showSignInForResult(this);
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(CoreEvents.InvalidCredentialsDetected event) {
        AuthenticationDialogUtils.showAuthErrorView(this);
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(CoreEvents.RestApiUnauthorized event) {
        AuthenticationDialogUtils.showAuthErrorView(this);
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(CoreEvents.TwoFactorAuthenticationDetected event) {
        AuthenticationDialogUtils.showAuthErrorView(this);
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(CoreEvents.InvalidSslCertificateDetected event) {
        SelfSignedSSLCertsManager.askForSslTrust(this, null);
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(CoreEvents.LoginLimitDetected event) {
        ToastUtils.showToast(this, R.string.limit_reached, ToastUtils.Duration.LONG);
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(NotificationEvents.NotificationsChanged event) {
        checkNoteBadge();
    }

    /*
     * Simperium Note bucket listeners
     */
    @Override
    public void onNetworkChange(Bucket<Note> noteBucket, Bucket.ChangeType changeType, String s) {
        if (changeType == Bucket.ChangeType.INSERT || changeType == Bucket.ChangeType.MODIFY) {
            checkNoteBadge();
        }
    }

    @Override
    public void onBeforeUpdateObject(Bucket<Note> noteBucket, Note note) {
        // noop
    }

    @Override
    public void onDeleteObject(Bucket<Note> noteBucket, Note note) {
        // noop
    }

    @Override
    public void onSaveObject(Bucket<Note> noteBucket, Note note) {
        // noop
    }

    @Override
    public void onMediaAdded(String mediaId) {
    }
}


File: WordPress/src/main/java/org/wordpress/android/ui/notifications/NotificationsListFragment.java
package org.wordpress.android.ui.notifications;

import android.app.Activity;
import android.app.Fragment;
import android.app.NotificationManager;
import android.content.Intent;
import android.os.Bundle;
import android.support.annotation.StringRes;
import android.support.v7.widget.DefaultItemAnimator;
import android.support.v7.widget.LinearLayoutManager;
import android.support.v7.widget.RecyclerView;
import android.text.TextUtils;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.TextView;

import com.simperium.client.Bucket;
import com.simperium.client.BucketObject;
import com.simperium.client.BucketObjectMissingException;

import org.wordpress.android.GCMIntentService;
import org.wordpress.android.R;
import org.wordpress.android.models.AccountHelper;
import org.wordpress.android.models.Note;
import org.wordpress.android.ui.ActivityId;
import org.wordpress.android.ui.ActivityLauncher;
import org.wordpress.android.ui.RequestCodes;
import org.wordpress.android.ui.main.WPMainActivity;
import org.wordpress.android.ui.notifications.adapters.NotesAdapter;
import org.wordpress.android.ui.notifications.utils.SimperiumUtils;
import org.wordpress.android.util.AppLog;
import org.wordpress.android.util.ToastUtils;
import org.wordpress.android.util.ToastUtils.Duration;

import javax.annotation.Nonnull;

import de.greenrobot.event.EventBus;

public class NotificationsListFragment extends Fragment
        implements Bucket.Listener<Note>,
                   WPMainActivity.OnScrollToTopListener {
    public static final String NOTE_ID_EXTRA = "noteId";
    public static final String NOTE_INSTANT_REPLY_EXTRA = "instantReply";
    public static final String NOTE_MODERATE_ID_EXTRA = "moderateNoteId";
    public static final String NOTE_MODERATE_STATUS_EXTRA = "moderateNoteStatus";

    private static final String KEY_LIST_SCROLL_POSITION = "scrollPosition";

    private NotesAdapter mNotesAdapter;
    private LinearLayoutManager mLinearLayoutManager;
    private RecyclerView mRecyclerView;
    private ViewGroup mEmptyView;

    private int mRestoredScrollPosition;

    private Bucket<Note> mBucket;

    public static NotificationsListFragment newInstance() {
        return new NotificationsListFragment();
    }

    /**
     * For responding to tapping of notes
     */
    public interface OnNoteClickListener {
        public void onClickNote(String noteId);
    }

    @Override
    public View onCreateView(@Nonnull LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.notifications_fragment_notes_list, container, false);

        mRecyclerView = (RecyclerView) view.findViewById(R.id.recycler_view_notes);
        mEmptyView = (ViewGroup) view.findViewById(R.id.empty_view);

        RecyclerView.ItemAnimator animator = new DefaultItemAnimator();
        animator.setSupportsChangeAnimations(true);
        mRecyclerView.setItemAnimator(animator);
        mLinearLayoutManager = new LinearLayoutManager(getActivity());
        mRecyclerView.setLayoutManager(mLinearLayoutManager);

        // setup the initial notes adapter, starts listening to the bucket
        mBucket = SimperiumUtils.getNotesBucket();
        if (mBucket != null) {
            if (mNotesAdapter == null) {
                mNotesAdapter = new NotesAdapter(getActivity(), mBucket);
                mNotesAdapter.setOnNoteClickListener(new OnNoteClickListener() {
                    @Override
                    public void onClickNote(String noteId) {
                        if (TextUtils.isEmpty(noteId)) return;

                        // open the latest version of this note just in case it has changed - this can
                        // happen if the note was tapped from the list fragment after it was updated
                        // by another fragment (such as NotificationCommentLikeFragment)
                        openNote(getActivity(), noteId, false, true);
                    }
                });
            }

            mRecyclerView.setAdapter(mNotesAdapter);
        } else {
            if (!AccountHelper.isSignedInWordPressDotCom()) {
                // let user know that notifications require a wp.com account and enable sign-in
                showEmptyView(R.string.notifications_account_required, true);
            } else {
                // failed for some other reason
                showEmptyView(R.string.error_refresh_notifications, false);
            }
        }

        return view;
    }

    @Override
    public void onActivityCreated(Bundle savedInstanceState) {
        super.onActivityCreated(savedInstanceState);

        if (savedInstanceState != null) {
            setRestoredListPosition(savedInstanceState.getInt(KEY_LIST_SCROLL_POSITION, RecyclerView.NO_POSITION));
        }
    }

    @Override
    public void onResume() {
        super.onResume();
        refreshNotes();

        // start listening to bucket change events
        if (mBucket != null) {
            mBucket.addListener(this);
        }

        // Remove notification if it is showing when we resume this activity.
        NotificationManager notificationManager = (NotificationManager) getActivity().getSystemService(GCMIntentService.NOTIFICATION_SERVICE);
        notificationManager.cancel(GCMIntentService.PUSH_NOTIFICATION_ID);

        if (SimperiumUtils.isUserAuthorized()) {
            SimperiumUtils.startBuckets();
            AppLog.i(AppLog.T.NOTIFS, "Starting Simperium buckets");
        }
    }

    @Override
    public void onPause() {
        // unregister the listener
        if (mBucket != null) {
            mBucket.removeListener(this);
        }
        super.onPause();
    }

    @Override
    public void onDestroy() {
        // Close Simperium cursor
        if (mNotesAdapter != null) {
            mNotesAdapter.closeCursor();
        }

        super.onDestroy();
    }

    @Override
    public void setMenuVisibility(final boolean visible) {
        super.setMenuVisibility(visible);
        if (visible) {
            ActivityId.trackLastActivity(ActivityId.NOTIFICATIONS);
        }
    }

    /**
     * Open a note fragment based on the type of note
     */
    public static void openNote(Activity activity,
                                String noteId,
                                boolean shouldShowKeyboard,
                                boolean shouldSlideIn) {
        if (noteId == null || activity == null) {
            return;
        }

        Intent detailIntent = new Intent(activity, NotificationsDetailActivity.class);
        detailIntent.putExtra(NOTE_ID_EXTRA, noteId);
        detailIntent.putExtra(NOTE_INSTANT_REPLY_EXTRA, shouldShowKeyboard);
        if (shouldSlideIn) {
            ActivityLauncher.slideInFromRightForResult(activity, detailIntent, RequestCodes.NOTE_DETAIL);
        } else {
            activity.startActivityForResult(detailIntent, RequestCodes.NOTE_DETAIL);
        }
    }

    private void setNoteIsHidden(String noteId, boolean isHidden) {
        if (mNotesAdapter == null) return;

        if (isHidden) {
            mNotesAdapter.addHiddenNoteId(noteId);
        } else {
            // Scroll the row into view if it isn't visible so the animation can be seen
            int notePosition = mNotesAdapter.getPositionForNote(noteId);
            if (notePosition != RecyclerView.NO_POSITION &&
                    mLinearLayoutManager.findFirstCompletelyVisibleItemPosition() > notePosition) {
                mLinearLayoutManager.scrollToPosition(notePosition);
            }

            mNotesAdapter.removeHiddenNoteId(noteId);
        }
    }

    private void setNoteIsModerating(String noteId, boolean isModerating) {
        if (mNotesAdapter == null) return;

        if (isModerating) {
            mNotesAdapter.addModeratingNoteId(noteId);
        } else {
            mNotesAdapter.removeModeratingNoteId(noteId);
        }
    }

    public void updateLastSeenTime() {
        // set the timestamp to now
        try {
            if (mNotesAdapter != null && mNotesAdapter.getCount() > 0 && SimperiumUtils.getMetaBucket() != null) {
                Note newestNote = mNotesAdapter.getNote(0);
                BucketObject meta = SimperiumUtils.getMetaBucket().get("meta");
                if (meta != null && newestNote != null) {
                    meta.setProperty("last_seen", newestNote.getTimestamp());
                    meta.save();
                }
            }
        } catch (BucketObjectMissingException e) {
            // try again later, meta is created by wordpress.com
        }
    }

    private void showEmptyView(@StringRes int stringResId, boolean showSignIn) {
        if (isAdded() && mEmptyView != null) {
            ((TextView) mEmptyView.findViewById(R.id.text_empty)).setText(stringResId);
            mEmptyView.setVisibility(View.VISIBLE);
            Button btnSignIn = (Button) mEmptyView.findViewById(R.id.button_sign_in);
            btnSignIn.setVisibility(showSignIn ? View.VISIBLE : View.GONE);
            if (showSignIn) {
                btnSignIn.setOnClickListener(new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        ActivityLauncher.showSignInForResult(getActivity());
                    }
                });
            }
        }
    }

    private void hideEmptyView() {
        if (isAdded() && mEmptyView != null) {
            mEmptyView.setVisibility(View.GONE);
        }
    }

    void refreshNotes() {
        if (!isAdded() || mNotesAdapter == null) {
            return;
        }

        getActivity().runOnUiThread(new Runnable() {
            @Override
            public void run() {
                mNotesAdapter.reloadNotes();
                restoreListScrollPosition();
                if (mNotesAdapter.getCount() > 0) {
                    hideEmptyView();
                } else {
                    showEmptyView(R.string.notifications_empty_list, false);
                }
            }
        });
    }

    private void restoreListScrollPosition() {
        if (isAdded() && mRecyclerView != null && mRestoredScrollPosition != RecyclerView.NO_POSITION
                && mRestoredScrollPosition < mNotesAdapter.getCount()) {
            // Restore scroll position in list
            mLinearLayoutManager.scrollToPosition(mRestoredScrollPosition);
            mRestoredScrollPosition = RecyclerView.NO_POSITION;
        }
    }

    @Override
    public void onSaveInstanceState(@Nonnull Bundle outState) {
        if (outState.isEmpty()) {
            outState.putBoolean("bug_19917_fix", true);
        }

        // Save list view scroll position
        outState.putInt(KEY_LIST_SCROLL_POSITION, getScrollPosition());

        super.onSaveInstanceState(outState);
    }

    private int getScrollPosition() {
        if (!isAdded() || mRecyclerView == null) {
            return RecyclerView.NO_POSITION;
        }

        return mLinearLayoutManager.findFirstVisibleItemPosition();
    }

    private void setRestoredListPosition(int listPosition) {
        mRestoredScrollPosition = listPosition;
    }

    /**
     * Simperium bucket listener methods
     */
    @Override
    public void onSaveObject(Bucket<Note> bucket, final Note object) {
        refreshNotes();
    }

    @Override
    public void onDeleteObject(Bucket<Note> bucket, final Note object) {
        refreshNotes();
    }

    @Override
    public void onNetworkChange(Bucket<Note> bucket, final Bucket.ChangeType type, final String key) {
        // Reset the note's local status when a remote change is received
        if (type == Bucket.ChangeType.MODIFY) {
            try {
                Note note = bucket.get(key);
                if (note.isCommentType()) {
                    note.setLocalStatus(null);
                    note.save();
                }
            } catch (BucketObjectMissingException e) {
                AppLog.e(AppLog.T.NOTIFS, "Could not create note after receiving change.");
            }
        }

        refreshNotes();
    }

    @Override
    public void onBeforeUpdateObject(Bucket<Note> noteBucket, Note note) {
        //noop
    }

    @Override
    public void onScrollToTop() {
        if (isAdded() && getScrollPosition() > 0) {
            mLinearLayoutManager.smoothScrollToPosition(mRecyclerView, null, 0);
        }
    }

    @Override
    public void onStop() {
        EventBus.getDefault().unregister(this);
        super.onStop();
    }

    @Override
    public void onStart() {
        super.onStart();
        EventBus.getDefault().registerSticky(this);
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(NotificationEvents.NoteModerationStatusChanged event) {
        setNoteIsModerating(event.mNoteId, event.mIsModerating);

        EventBus.getDefault().removeStickyEvent(NotificationEvents.NoteModerationStatusChanged.class);
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(NotificationEvents.NoteVisibilityChanged event) {
        setNoteIsHidden(event.mNoteId, event.mIsHidden);

        EventBus.getDefault().removeStickyEvent(NotificationEvents.NoteVisibilityChanged.class);
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(NotificationEvents.NoteModerationFailed event) {
        if (isAdded()) {
            ToastUtils.showToast(getActivity(), R.string.error_moderate_comment, Duration.LONG);
        }

        EventBus.getDefault().removeStickyEvent(NotificationEvents.NoteModerationFailed.class);
    }
}


File: WordPress/src/main/java/org/wordpress/android/ui/reader/ReaderPostListFragment.java
package org.wordpress.android.ui.reader;

import android.animation.Animator;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.Fragment;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Parcelable;
import android.support.v7.widget.LinearLayoutManager;
import android.support.v7.widget.RecyclerView;
import android.support.v7.widget.Toolbar;
import android.text.Html;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.LayoutInflater;
import android.view.MenuItem;
import android.view.View;
import android.view.ViewAnimationUtils;
import android.view.ViewGroup;
import android.view.ViewTreeObserver;
import android.view.animation.AccelerateDecelerateInterpolator;
import android.view.animation.Animation;
import android.view.animation.AnimationUtils;
import android.widget.AdapterView;
import android.widget.ImageView;
import android.widget.PopupMenu;
import android.widget.ProgressBar;
import android.widget.Spinner;
import android.widget.TextView;

import com.cocosw.undobar.UndoBarController;

import org.wordpress.android.R;
import org.wordpress.android.analytics.AnalyticsTracker;
import org.wordpress.android.datasets.ReaderBlogTable;
import org.wordpress.android.datasets.ReaderDatabase;
import org.wordpress.android.datasets.ReaderPostTable;
import org.wordpress.android.datasets.ReaderTagTable;
import org.wordpress.android.models.ReaderBlog;
import org.wordpress.android.models.ReaderPost;
import org.wordpress.android.models.ReaderTag;
import org.wordpress.android.models.ReaderTagType;
import org.wordpress.android.ui.ActivityId;
import org.wordpress.android.ui.RequestCodes;
import org.wordpress.android.ui.main.WPMainActivity;
import org.wordpress.android.ui.prefs.AppPrefs;
import org.wordpress.android.ui.reader.ReaderTypes.ReaderPostListType;
import org.wordpress.android.ui.reader.actions.ReaderActions;
import org.wordpress.android.ui.reader.actions.ReaderBlogActions;
import org.wordpress.android.ui.reader.actions.ReaderTagActions;
import org.wordpress.android.ui.reader.adapters.ReaderPostAdapter;
import org.wordpress.android.ui.reader.adapters.ReaderTagSpinnerAdapter;
import org.wordpress.android.ui.reader.services.ReaderPostService;
import org.wordpress.android.ui.reader.services.ReaderPostService.UpdateAction;
import org.wordpress.android.ui.reader.services.ReaderUpdateService;
import org.wordpress.android.ui.reader.utils.ReaderUtils;
import org.wordpress.android.ui.reader.views.ReaderBlogInfoView;
import org.wordpress.android.ui.reader.views.ReaderFollowButton;
import org.wordpress.android.ui.reader.views.ReaderRecyclerView;
import org.wordpress.android.ui.reader.views.ReaderRecyclerView.ReaderItemDecoration;
import org.wordpress.android.util.AniUtils;
import org.wordpress.android.util.AppLog;
import org.wordpress.android.util.AppLog.T;
import org.wordpress.android.util.HtmlUtils;
import org.wordpress.android.util.NetworkUtils;
import org.wordpress.android.util.ToastUtils;
import org.wordpress.android.util.WPActivityUtils;
import org.wordpress.android.util.helpers.SwipeToRefreshHelper;
import org.wordpress.android.util.helpers.SwipeToRefreshHelper.RefreshListener;
import org.wordpress.android.util.widgets.CustomSwipeRefreshLayout;

import java.util.ArrayList;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.Map;
import java.util.Stack;

import de.greenrobot.event.EventBus;

public class ReaderPostListFragment extends Fragment
        implements ReaderInterfaces.OnPostSelectedListener,
                   ReaderInterfaces.OnTagSelectedListener,
                   ReaderInterfaces.OnPostPopupListener,
                   WPMainActivity.OnScrollToTopListener {

    private Toolbar mTagToolbar;
    private Spinner mTagSpinner;
    private ReaderTagSpinnerAdapter mSpinnerAdapter;

    private ReaderPostAdapter mPostAdapter;
    private ReaderRecyclerView mRecyclerView;

    private SwipeToRefreshHelper mSwipeToRefreshHelper;
    private CustomSwipeRefreshLayout mSwipeToRefreshLayout;

    private View mNewPostsBar;
    private View mEmptyView;
    private ProgressBar mProgress;

    private ViewGroup mTagInfoView;
    private ReaderBlogInfoView mBlogInfoView;
    private ReaderFollowButton mFollowButton;

    private ReaderTag mCurrentTag;
    private long mCurrentBlogId;
    private long mCurrentFeedId;
    private ReaderPostListType mPostListType;

    private int mRestorePosition;
    private int mTagToolbarOffset;

    private boolean mIsUpdating;
    private boolean mWasPaused;
    private boolean mIsAnimatingOutNewPostsBar;
    private boolean mIsLoggedOutReader;

    private final HistoryStack mTagPreviewHistory = new HistoryStack("tag_preview_history");

    private static class HistoryStack extends Stack<String> {
        private final String keyName;
        HistoryStack(String keyName) {
            this.keyName = keyName;
        }
        void restoreInstance(Bundle bundle) {
            clear();
            if (bundle.containsKey(keyName)) {
                ArrayList<String> history = bundle.getStringArrayList(keyName);
                if (history != null) {
                    this.addAll(history);
                }
            }
        }
        void saveInstance(Bundle bundle) {
            if (!isEmpty()) {
                ArrayList<String> history = new ArrayList<>();
                history.addAll(this);
                bundle.putStringArrayList(keyName, history);
            }
        }
    }

    public static ReaderPostListFragment newInstance() {
        ReaderTag tag = AppPrefs.getReaderTag();
        if (tag == null) {
            tag = ReaderTag.getDefaultTag();
        }
        return newInstanceForTag(tag, ReaderPostListType.TAG_FOLLOWED);
    }

    /*
     * show posts with a specific tag (either TAG_FOLLOWED or TAG_PREVIEW)
     */
    static ReaderPostListFragment newInstanceForTag(ReaderTag tag, ReaderPostListType listType) {
        AppLog.d(T.READER, "reader post list > newInstance (tag)");

        Bundle args = new Bundle();
        args.putSerializable(ReaderConstants.ARG_TAG, tag);
        args.putSerializable(ReaderConstants.ARG_POST_LIST_TYPE, listType);

        ReaderPostListFragment fragment = new ReaderPostListFragment();
        fragment.setArguments(args);

        return fragment;
    }

    /*
     * show posts in a specific blog
     */
    public static ReaderPostListFragment newInstanceForBlog(long blogId) {
        AppLog.d(T.READER, "reader post list > newInstance (blog)");

        Bundle args = new Bundle();
        args.putLong(ReaderConstants.ARG_BLOG_ID, blogId);
        args.putSerializable(ReaderConstants.ARG_POST_LIST_TYPE, ReaderPostListType.BLOG_PREVIEW);

        ReaderPostListFragment fragment = new ReaderPostListFragment();
        fragment.setArguments(args);

        return fragment;
    }

    public static ReaderPostListFragment newInstanceForFeed(long feedId) {
        AppLog.d(T.READER, "reader post list > newInstance (blog)");

        Bundle args = new Bundle();
        args.putLong(ReaderConstants.ARG_FEED_ID, feedId);
        args.putLong(ReaderConstants.ARG_BLOG_ID, feedId);
        args.putSerializable(ReaderConstants.ARG_POST_LIST_TYPE, ReaderPostListType.BLOG_PREVIEW);

        ReaderPostListFragment fragment = new ReaderPostListFragment();
        fragment.setArguments(args);

        return fragment;
    }

    @Override
    public void setArguments(Bundle args) {
        super.setArguments(args);

        if (args != null) {
            if (args.containsKey(ReaderConstants.ARG_TAG)) {
                mCurrentTag = (ReaderTag) args.getSerializable(ReaderConstants.ARG_TAG);
            }
            if (args.containsKey(ReaderConstants.ARG_POST_LIST_TYPE)) {
                mPostListType = (ReaderPostListType) args.getSerializable(ReaderConstants.ARG_POST_LIST_TYPE);
            }

            mCurrentBlogId = args.getLong(ReaderConstants.ARG_BLOG_ID);
            mCurrentFeedId = args.getLong(ReaderConstants.ARG_FEED_ID);

            if (getPostListType() == ReaderPostListType.TAG_PREVIEW && hasCurrentTag()) {
                mTagPreviewHistory.push(getCurrentTagName());
            }
        }
    }

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        mIsLoggedOutReader = ReaderUtils.isLoggedOutReader();

        if (savedInstanceState != null) {
            AppLog.d(T.READER, "reader post list > restoring instance state");
            if (savedInstanceState.containsKey(ReaderConstants.ARG_TAG)) {
                mCurrentTag = (ReaderTag) savedInstanceState.getSerializable(ReaderConstants.ARG_TAG);
            }
            if (savedInstanceState.containsKey(ReaderConstants.ARG_BLOG_ID)) {
                mCurrentBlogId = savedInstanceState.getLong(ReaderConstants.ARG_BLOG_ID);
            }
            if (savedInstanceState.containsKey(ReaderConstants.ARG_FEED_ID)) {
                mCurrentFeedId = savedInstanceState.getLong(ReaderConstants.ARG_FEED_ID);
            }
            if (savedInstanceState.containsKey(ReaderConstants.ARG_POST_LIST_TYPE)) {
                mPostListType = (ReaderPostListType) savedInstanceState.getSerializable(ReaderConstants.ARG_POST_LIST_TYPE);
            }
            if (getPostListType() == ReaderPostListType.TAG_PREVIEW) {
                mTagPreviewHistory.restoreInstance(savedInstanceState);
            }
            mRestorePosition = savedInstanceState.getInt(ReaderConstants.KEY_RESTORE_POSITION);
            mWasPaused = savedInstanceState.getBoolean(ReaderConstants.KEY_WAS_PAUSED);
        }
    }

    @Override
    public void onPause() {
        super.onPause();
        mWasPaused = true;
    }

    @Override
    public void onResume() {
        super.onResume();

        if (mWasPaused) {
            AppLog.d(T.READER, "reader post list > resumed from paused state");
            mWasPaused = false;
            // refresh the posts in case the user returned from an activity that
            // changed one (or more) of the posts
            refreshPosts();
            // likewise for tags
            refreshTags();

            // auto-update the current tag if it's time
            if (!isUpdating()
                    && getPostListType() == ReaderPostListType.TAG_FOLLOWED
                    && ReaderTagTable.shouldAutoUpdateTag(mCurrentTag)) {
                AppLog.i(T.READER, "reader post list > auto-updating current tag after resume");
                updatePostsWithTag(getCurrentTag(), UpdateAction.REQUEST_NEWER);
            }
        }
    }

    @Override
    public void onStart() {
        super.onStart();

        EventBus.getDefault().register(this);

        purgeDatabaseIfNeeded();
        performInitialUpdateIfNeeded();
        if (getPostListType() == ReaderPostListType.TAG_FOLLOWED) {
            updateFollowedTagsAndBlogsIfNeeded();
        }
    }

    @Override
    public void onStop() {
        super.onStop();
        EventBus.getDefault().unregister(this);
    }

    @Override
    public void setMenuVisibility(final boolean visible) {
        super.setMenuVisibility(visible);
        if (visible) {
            ActivityId.trackLastActivity(ActivityId.READER);
        }
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(ReaderEvents.FollowedTagsChanged event) {
        if (getPostListType() == ReaderTypes.ReaderPostListType.TAG_FOLLOWED) {
            // list fragment is viewing followed tags, tell it to refresh the list of tags
            refreshTags();
            // update the current tag if the list fragment is empty - this will happen if
            // the tag table was previously empty (ie: first run)
            if (isPostAdapterEmpty()) {
                updateCurrentTag();
            }
        }
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(ReaderEvents.FollowedBlogsChanged event) {
        // refresh posts if user is viewing "Blogs I Follow"
        if (getPostListType() == ReaderTypes.ReaderPostListType.TAG_FOLLOWED
                && hasCurrentTag()
                && getCurrentTag().isBlogsIFollow()) {
            refreshPosts();
        }
    }

    @Override
    public void onSaveInstanceState(Bundle outState) {
        AppLog.d(T.READER, "reader post list > saving instance state");

        if (mCurrentTag != null) {
            outState.putSerializable(ReaderConstants.ARG_TAG, mCurrentTag);
        }
        if (getPostListType() == ReaderPostListType.TAG_PREVIEW) {
            mTagPreviewHistory.saveInstance(outState);
        }

        outState.putLong(ReaderConstants.ARG_BLOG_ID, mCurrentBlogId);
        outState.putLong(ReaderConstants.ARG_FEED_ID, mCurrentFeedId);
        outState.putBoolean(ReaderConstants.KEY_WAS_PAUSED, mWasPaused);
        outState.putInt(ReaderConstants.KEY_RESTORE_POSITION, getCurrentPosition());
        outState.putSerializable(ReaderConstants.ARG_POST_LIST_TYPE, getPostListType());

        super.onSaveInstanceState(outState);
    }

    private int getCurrentPosition() {
        if (mRecyclerView != null && hasPostAdapter()) {
            return ((LinearLayoutManager) mRecyclerView.getLayoutManager()).findFirstVisibleItemPosition();
        } else {
            return -1;
        }
    }

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        final ViewGroup rootView = (ViewGroup) inflater.inflate(R.layout.reader_fragment_post_cards, container, false);
        mRecyclerView = (ReaderRecyclerView) rootView.findViewById(R.id.recycler_view);

        Context context = container.getContext();
        int spacingHorizontal = context.getResources().getDimensionPixelSize(R.dimen.content_margin);
        int spacingVertical = context.getResources().getDimensionPixelSize(R.dimen.reader_card_gutters);
        mRecyclerView.addItemDecoration(new ReaderItemDecoration(spacingHorizontal, spacingVertical));

        // bar that appears at top after new posts are loaded
        mNewPostsBar = rootView.findViewById(R.id.layout_new_posts);
        mNewPostsBar.setVisibility(View.GONE);
        mNewPostsBar.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                scrollRecycleViewToPosition(0);
                refreshPosts();
            }
        });

        // add the tag/blog header - note that this remains invisible until animated in
        ViewGroup header = (ViewGroup) rootView.findViewById(R.id.frame_header);
        switch (getPostListType()) {
            case TAG_PREVIEW:
                mTagInfoView = (ViewGroup) inflater.inflate(R.layout.reader_tag_info_view, container, false);
                header.addView(mTagInfoView);
                header.setVisibility(View.INVISIBLE);
                break;

            case BLOG_PREVIEW:
                mBlogInfoView = new ReaderBlogInfoView(context);
                header.addView(mBlogInfoView);
                header.setVisibility(View.INVISIBLE);
                break;
        }

        // view that appears when current tag/blog has no posts - box images in this view are
        // displayed and animated for tags only
        mEmptyView = rootView.findViewById(R.id.empty_view);
        mEmptyView.findViewById(R.id.layout_box_images).setVisibility(shouldShowBoxAndPagesAnimation() ? View.VISIBLE : View.GONE);

        // progress bar that appears when loading more posts
        mProgress = (ProgressBar) rootView.findViewById(R.id.progress_footer);
        mProgress.setVisibility(View.GONE);

        // swipe to refresh setup
        mSwipeToRefreshLayout = (CustomSwipeRefreshLayout) rootView.findViewById(R.id.ptr_layout);
        mSwipeToRefreshHelper = new SwipeToRefreshHelper(getActivity(),
                mSwipeToRefreshLayout,
                new RefreshListener() {
                    @Override
                    public void onRefreshStarted() {
                        if (!isAdded()) {
                            return;
                        }
                        if (!NetworkUtils.checkConnection(getActivity())) {
                            showSwipeToRefreshProgress(false);
                            return;
                        }
                        switch (getPostListType()) {
                            case TAG_FOLLOWED:
                            case TAG_PREVIEW:
                                updatePostsWithTag(getCurrentTag(), UpdateAction.REQUEST_NEWER);
                                break;
                            case BLOG_PREVIEW:
                                updatePostsInCurrentBlogOrFeed(UpdateAction.REQUEST_NEWER);
                                break;
                        }
                        // make sure swipe-to-refresh progress shows since this is a manual refresh
                        showSwipeToRefreshProgress(true);
                    }
                }
        );

        return rootView;
    }

    /*
     * animate in the blog/tag info header after a brief delay
     */
    @SuppressLint("NewApi")
    private void animateHeaderDelayed() {
        if (!isAdded()) {
            return;
        }

        final ViewGroup header = (ViewGroup) getView().findViewById(R.id.frame_header);
        if (header == null || header.getVisibility() == View.VISIBLE) {
            return;
        }

        // must wait for header to be fully laid out (ie: measured) or else we risk
        // "IllegalStateException: Cannot start this animator on a detached view"
        header.getViewTreeObserver().addOnGlobalLayoutListener(new ViewTreeObserver.OnGlobalLayoutListener() {
            @Override
            public void onGlobalLayout() {
                header.getViewTreeObserver().removeGlobalOnLayoutListener(this);
                new Handler().postDelayed(new Runnable() {
                    @Override
                    public void run() {
                        if (!isAdded()) {
                            return;
                        }
                        header.setVisibility(View.VISIBLE);
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                            Animator animator = ViewAnimationUtils.createCircularReveal(
                                    header,
                                    header.getWidth() / 2,
                                    0,
                                    0,
                                    (float) Math.hypot(header.getWidth(), header.getHeight()));
                            animator.setInterpolator(new AccelerateDecelerateInterpolator());
                            animator.start();
                        } else {
                            AniUtils.startAnimation(header, R.anim.reader_top_bar_in);
                        }
                    }
                }, 250);
            }
        });
    }

    private void scrollRecycleViewToPosition(int position) {
        if (!isAdded() || mRecyclerView == null) return;

        mRecyclerView.scrollToPosition(position);

        // we need to reposition the tag toolbar here, but we need to wait for the
        // recycler to settle before doing so - note that RecyclerView doesn't
        // fire it's scroll listener when scrollToPosition() is called, so we
        // can't rely on that to position the toolbar in this situation
        if (shouldShowTagToolbar()) {
            new Handler().postDelayed(new Runnable() {
                @Override
                public void run() {
                    positionTagToolbar();
                }
            }, 250);
        }
    }

    /*
     * position the tag toolbar based on the recycler's scroll position - this will make it
     * appear to scroll along with the recycler
     */
    private void positionTagToolbar() {
        if (!isAdded() || mTagToolbar == null) return;

        int distance = mRecyclerView.getVerticalScrollOffset();
        int newVisibility;
        if (distance <= mTagToolbarOffset) {
            newVisibility = View.VISIBLE;
            mTagToolbar.setTranslationY(-distance);
        } else {
            newVisibility = View.GONE;
        }
        if (mTagToolbar.getVisibility() != newVisibility) {
            mTagToolbar.setVisibility(newVisibility);
        }
    }

    @Override
    public void onActivityCreated(Bundle savedInstanceState) {
        super.onActivityCreated(savedInstanceState);

        // configure the toolbar for posts in followed tags (shown in main viewpager activity)
        if (shouldShowTagToolbar()) {
            mTagToolbar = (Toolbar) getActivity().findViewById(R.id.toolbar_reader);

            // the toolbar is hidden by the layout, so we need to show it here unless we know we're
            // going to restore the list position once the adapter is loaded (which will take care
            // of showing/hiding the toolbar)
            mTagToolbar.setVisibility(mRestorePosition > 0 ? View.GONE : View.VISIBLE);

            // enable customizing followed tags/blogs if user is logged in
            if (!mIsLoggedOutReader) {
                mTagToolbar.inflateMenu(R.menu.reader_list);
                mTagToolbar.setOnMenuItemClickListener(new Toolbar.OnMenuItemClickListener() {
                    @Override
                    public boolean onMenuItemClick(MenuItem menuItem) {
                        if (menuItem.getItemId() == R.id.menu_tags) {
                            ReaderActivityLauncher.showReaderSubsForResult(getActivity());
                            return true;
                        }
                        return false;
                    }
                });
            }

            // scroll the tag toolbar with the recycler
            int toolbarHeight = getResources().getDimensionPixelSize(R.dimen.toolbar_height);
            mTagToolbarOffset = (int) (toolbarHeight + (toolbarHeight * 0.25));
            mRecyclerView.setOnScrollListener(new RecyclerView.OnScrollListener() {
                @Override
                public void onScrolled(RecyclerView recyclerView, int dx, int dy) {
                    super.onScrolled(recyclerView, dx, dy);
                    positionTagToolbar();
                }
            });

            // create the tag spinner in the toolbar
            if (mTagSpinner == null) {
                enableTagSpinner();
            }
            selectTagInSpinner(getCurrentTag());
        }

        boolean adapterAlreadyExists = hasPostAdapter();
        mRecyclerView.setAdapter(getPostAdapter());

        // if adapter didn't already exist, populate it now then update the tag - this
        // check is important since without it the adapter would be reset and posts would
        // be updated every time the user moves between fragments
        if (!adapterAlreadyExists && getPostListType().isTagType()) {
            boolean isRecreated = (savedInstanceState != null);
            getPostAdapter().setCurrentTag(mCurrentTag);
            if (!isRecreated && ReaderTagTable.shouldAutoUpdateTag(mCurrentTag)) {
                updatePostsWithTag(getCurrentTag(), UpdateAction.REQUEST_NEWER);
            }
        }

        if (getPostListType().isPreviewType() && !mIsLoggedOutReader) {
            createFollowButton();
        }

        switch (getPostListType()) {
            case BLOG_PREVIEW:
                loadBlogOrFeedInfo();
                animateHeaderDelayed();
                break;
            case TAG_PREVIEW:
                updateTagPreviewHeader();
                animateHeaderDelayed();
                break;
        }
    }

    /*
     * adds a follow button to the activity toolbar for tag/blog preview
     */
    private void createFollowButton() {
        if (!isAdded()) {
            return;
        }

        Toolbar toolbar = (Toolbar) getActivity().findViewById(R.id.toolbar);
        if (toolbar == null) {
            return;
        }

        Context context = toolbar.getContext();
        int padding = context.getResources().getDimensionPixelSize(R.dimen.margin_small);
        int paddingRight = context.getResources().getDimensionPixelSize(R.dimen.reader_card_content_padding);
        int marginRight = context.getResources().getDimensionPixelSize(R.dimen.content_margin);

        mFollowButton = new ReaderFollowButton(context);
        mFollowButton.setPadding(padding, padding, paddingRight, padding);

        Toolbar.LayoutParams params =
                new Toolbar.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,
                                             ViewGroup.LayoutParams.WRAP_CONTENT,
                                             Gravity.RIGHT | Gravity.CENTER_VERTICAL);
        params.setMargins(0, 0, marginRight, 0);
        mFollowButton.setLayoutParams(params);

        toolbar.addView(mFollowButton);
        updateFollowButton();

        mFollowButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                if (getPostListType() == ReaderPostListType.BLOG_PREVIEW) {
                    toggleBlogFollowStatus();
                } else {
                    toggleTagFollowStatus();
                }
            }
        });
    }

    private void updateFollowButton() {
        if (!isAdded() || mFollowButton == null) {
            return;
        }
        boolean isFollowing;
        switch (getPostListType()) {
            case BLOG_PREVIEW:
                if (mCurrentFeedId != 0) {
                    isFollowing = ReaderBlogTable.isFollowedFeed(mCurrentFeedId);
                } else {
                    isFollowing = ReaderBlogTable.isFollowedBlog(mCurrentBlogId);
                }
                break;
            default:
                isFollowing = ReaderTagTable.isFollowedTagName(getCurrentTagName());
                break;
        }
        mFollowButton.setIsFollowed(isFollowing);
    }

    /*
     * blocks the blog associated with the passed post and removes all posts in that blog
     * from the adapter
     */
    private void blockBlogForPost(final ReaderPost post) {
        if (post == null || !hasPostAdapter()) {
            return;
        }

        if (!NetworkUtils.checkConnection(getActivity())) {
            return;
        }

        ReaderActions.ActionListener actionListener = new ReaderActions.ActionListener() {
            @Override
            public void onActionResult(boolean succeeded) {
                if (!succeeded && isAdded()) {
                    hideUndoBar();
                    ToastUtils.showToast(getActivity(), R.string.reader_toast_err_block_blog, ToastUtils.Duration.LONG);
                }
            }
        };

        // perform call to block this blog - returns list of posts deleted by blocking so
        // they can be restored if the user undoes the block
        final ReaderBlogActions.BlockedBlogResult blockResult =
                ReaderBlogActions.blockBlogFromReader(post.blogId, actionListener);
        AnalyticsTracker.track(AnalyticsTracker.Stat.READER_BLOCKED_BLOG);

        // remove posts in this blog from the adapter
        getPostAdapter().removePostsInBlog(post.blogId);

        // show the undo bar enabling the user to undo the block
        UndoBarController.UndoListener undoListener = new UndoBarController.UndoListener() {
            @Override
            public void onUndo(Parcelable parcelable) {
                ReaderBlogActions.undoBlockBlogFromReader(blockResult);
                refreshPosts();
            }
        };
        new UndoBarController.UndoBar(getActivity())
                .message(getString(R.string.reader_toast_blog_blocked))
                .listener(undoListener)
                .translucent(true)
                .show();

    }

    private void hideUndoBar() {
        if (isAdded()) {
            UndoBarController.clear(getActivity());
        }
    }

    /*
     * enables the tag spinner in the toolbar, used only for posts in followed tags
     */
    private void enableTagSpinner() {
        if (!isAdded()) return;

        mTagSpinner = (Spinner) mTagToolbar.findViewById(R.id.reader_spinner);
        mTagSpinner.setAdapter(getSpinnerAdapter());
        mTagSpinner.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                final ReaderTag tag = (ReaderTag) getSpinnerAdapter().getItem(position);
                if (tag == null) {
                    return;
                }
                if (!isCurrentTag(tag)) {
                    Map<String, String> properties = new HashMap<>();
                    properties.put("tag", tag.getTagName());
                    AnalyticsTracker.track(AnalyticsTracker.Stat.READER_LOADED_TAG, properties);
                    if (tag.isFreshlyPressed()) {
                        AnalyticsTracker.track(AnalyticsTracker.Stat.READER_LOADED_FRESHLY_PRESSED);
                    }
                }
                setCurrentTag(tag, true);
                AppLog.d(T.READER, String.format("reader post list > tag %s displayed", tag.getTagNameForLog()));
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
                // nop
            }
        });
    }

    /*
     * returns true if the fragment should have it's own toolbar - used when showing posts in
     * followed tags so user can select a different tag from the toolbar spinner
     */
    private boolean shouldShowTagToolbar() {
        return (getPostListType() == ReaderPostListType.TAG_FOLLOWED);
    }

    /*
     * box/pages animation that appears when loading an empty list (only appears for tags)
     */
    private boolean shouldShowBoxAndPagesAnimation() {
        return getPostListType().isTagType();
    }
    private void startBoxAndPagesAnimation() {
        if (!isAdded()) {
            return;
        }

        ImageView page1 = (ImageView) mEmptyView.findViewById(R.id.empty_tags_box_page1);
        ImageView page2 = (ImageView) mEmptyView.findViewById(R.id.empty_tags_box_page2);
        ImageView page3 = (ImageView) mEmptyView.findViewById(R.id.empty_tags_box_page3);

        page1.startAnimation(AnimationUtils.loadAnimation(getActivity(), R.anim.box_with_pages_slide_up_page1));
        page2.startAnimation(AnimationUtils.loadAnimation(getActivity(), R.anim.box_with_pages_slide_up_page2));
        page3.startAnimation(AnimationUtils.loadAnimation(getActivity(), R.anim.box_with_pages_slide_up_page3));
    }

    private void setEmptyTitleAndDescription(boolean requestFailed) {
        if (!isAdded()) {
            return;
        }

        int titleResId;
        int descriptionResId = 0;

        if (!NetworkUtils.isNetworkAvailable(getActivity())) {
            titleResId = R.string.reader_empty_posts_no_connection;
        } else if (requestFailed) {
            titleResId = R.string.reader_empty_posts_request_failed;
        } else if (isUpdating()) {
            titleResId = R.string.reader_empty_posts_in_tag_updating;
        } else if (getPostListType() == ReaderPostListType.BLOG_PREVIEW) {
            titleResId = R.string.reader_empty_posts_in_blog;
        } else if (getPostListType() == ReaderPostListType.TAG_FOLLOWED && hasCurrentTag()) {
            if (getCurrentTag().isBlogsIFollow()) {
                titleResId = R.string.reader_empty_followed_blogs_title;
                descriptionResId = R.string.reader_empty_followed_blogs_description;
            } else if (getCurrentTag().isPostsILike()) {
                titleResId = R.string.reader_empty_posts_liked;
            } else {
                titleResId = R.string.reader_empty_posts_in_tag;
            }
        } else {
            titleResId = R.string.reader_empty_posts_in_tag;
        }

        TextView titleView = (TextView) mEmptyView.findViewById(R.id.title_empty);
        titleView.setText(getString(titleResId));

        TextView descriptionView = (TextView) mEmptyView.findViewById(R.id.description_empty);
        if (descriptionResId == 0) {
            descriptionView.setVisibility(View.INVISIBLE);
        } else {
            descriptionView.setText(getString(descriptionResId));
            descriptionView.setVisibility(View.VISIBLE);
        }
    }

    /*
     * called by post adapter when data has been loaded
     */
    private final ReaderInterfaces.DataLoadedListener mDataLoadedListener = new ReaderInterfaces.DataLoadedListener() {
        @Override
        public void onDataLoaded(boolean isEmpty) {
            if (!isAdded()) {
                return;
            }
            if (isEmpty) {
                setEmptyTitleAndDescription(false);
                mEmptyView.setVisibility(View.VISIBLE);
                if (shouldShowBoxAndPagesAnimation()) {
                    startBoxAndPagesAnimation();
                }
            } else {
                mEmptyView.setVisibility(View.GONE);
                if (mRestorePosition > 0) {
                    AppLog.d(T.READER, "reader post list > restoring position");
                    scrollRecycleViewToPosition(mRestorePosition);
                }
            }
            mRestorePosition = 0;
        }
    };

    /*
     * called by post adapter to load older posts when user scrolls to the last post
     */
    private final ReaderActions.DataRequestedListener mDataRequestedListener = new ReaderActions.DataRequestedListener() {
        @Override
        public void onRequestData() {
            // skip if update is already in progress
            if (isUpdating()) {
                return;
            }

            // request older posts unless we already have the max # to show
            switch (getPostListType()) {
                case TAG_FOLLOWED:
                case TAG_PREVIEW:
                    if (ReaderPostTable.getNumPostsWithTag(mCurrentTag) < ReaderConstants.READER_MAX_POSTS_TO_DISPLAY) {
                        // request older posts
                        updatePostsWithTag(getCurrentTag(), UpdateAction.REQUEST_OLDER);
                        AnalyticsTracker.track(AnalyticsTracker.Stat.READER_INFINITE_SCROLL);
                    }
                    break;

                case BLOG_PREVIEW:
                    int numPosts;
                    if (mCurrentFeedId != 0) {
                        numPosts = ReaderPostTable.getNumPostsInFeed(mCurrentFeedId);
                    } else {
                        numPosts = ReaderPostTable.getNumPostsInBlog(mCurrentBlogId);
                    }
                    if (numPosts < ReaderConstants.READER_MAX_POSTS_TO_DISPLAY) {
                        updatePostsInCurrentBlogOrFeed(UpdateAction.REQUEST_OLDER);
                        AnalyticsTracker.track(AnalyticsTracker.Stat.READER_INFINITE_SCROLL);
                    }
                    break;
            }
        }
    };

    /*
     * called by post adapter when user requests to reblog a post
     */
    private final ReaderInterfaces.RequestReblogListener mRequestReblogListener = new ReaderInterfaces.RequestReblogListener() {
        @Override
        public void onRequestReblog(ReaderPost post, View view) {
            if (isAdded()) {
                ReaderActivityLauncher.showReaderReblogForResult(getActivity(), post, view);
            }
        }
    };

    private ReaderPostAdapter getPostAdapter() {
        if (mPostAdapter == null) {
            AppLog.d(T.READER, "reader post list > creating post adapter");
            Context context = WPActivityUtils.getThemedContext(getActivity());
            mPostAdapter = new ReaderPostAdapter(context, getPostListType());
            mPostAdapter.setOnPostSelectedListener(this);
            mPostAdapter.setOnTagSelectedListener(this);
            mPostAdapter.setOnPostPopupListener(this);
            mPostAdapter.setOnDataLoadedListener(mDataLoadedListener);
            mPostAdapter.setOnDataRequestedListener(mDataRequestedListener);
            mPostAdapter.setOnReblogRequestedListener(mRequestReblogListener);
            // show spacer above the first post to accommodate toolbar
            mPostAdapter.setShowToolbarSpacer(shouldShowTagToolbar());
        }
        return mPostAdapter;
    }

    private boolean hasPostAdapter() {
        return (mPostAdapter != null);
    }

    private boolean isPostAdapterEmpty() {
        return (mPostAdapter == null || mPostAdapter.isEmpty());
    }

    private boolean isCurrentTag(final ReaderTag tag) {
        return ReaderTag.isSameTag(tag, mCurrentTag);
    }
    private boolean isCurrentTagName(String tagName) {
        return (tagName != null && tagName.equalsIgnoreCase(getCurrentTagName()));
    }

    private ReaderTag getCurrentTag() {
        return mCurrentTag;
    }

    private String getCurrentTagName() {
        return (mCurrentTag != null ? mCurrentTag.getTagName() : "");
    }

    private boolean hasCurrentTag() {
        return mCurrentTag != null;
    }

    private void setCurrentTag(final ReaderTag tag, boolean allowAutoUpdate) {
        if (tag == null) {
            return;
        }

        // skip if this is already the current tag and the post adapter is already showing it - this
        // will happen when the list fragment is restored and the current tag is re-selected in the
        // toolbar dropdown
        if (isCurrentTag(tag)
                && hasPostAdapter()
                && getPostAdapter().isCurrentTag(tag)) {
            return;
        }

        mCurrentTag = tag;

        switch (getPostListType()) {
            case TAG_FOLLOWED:
                // remember this as the current tag if viewing followed tag
                AppPrefs.setReaderTag(tag);
                break;
            case TAG_PREVIEW:
                mTagPreviewHistory.push(tag.getTagName());
                break;
        }

        getPostAdapter().setCurrentTag(tag);
        hideNewPostsBar();
        hideUndoBar();
        showLoadingProgress(false);

        if (getPostListType() == ReaderPostListType.TAG_PREVIEW) {
            updateTagPreviewHeader();
            updateFollowButton();
        }

        // update posts in this tag if it's time to do so
        if (allowAutoUpdate && ReaderTagTable.shouldAutoUpdateTag(tag)) {
            updatePostsWithTag(tag, UpdateAction.REQUEST_NEWER);
        }
    }

    /*
    * when previewing posts with a specific tag, a history of previewed tags is retained so
    * the user can navigate back through them - this is faster and requires less memory
    * than creating a new fragment for each previewed tag
    */
    boolean goBackInTagHistory() {
        if (mTagPreviewHistory.empty()) {
            return false;
        }

        String tagName = mTagPreviewHistory.pop();
        if (isCurrentTagName(tagName)) {
            if (mTagPreviewHistory.empty()) {
                return false;
            }
            tagName = mTagPreviewHistory.pop();
        }

        setCurrentTag(new ReaderTag(tagName, ReaderTagType.FOLLOWED), false);
        updateFollowButton();

        return true;
    }

    /*
     * if we're previewing a tag, show the current tag name in the header and update the
     * follow button to show the correct follow state for the tag
     */
    private void updateTagPreviewHeader() {
        if (mTagInfoView == null) {
            return;
        }

        final TextView txtTagName = (TextView) mTagInfoView.findViewById(R.id.text_tag_name);
        String color = HtmlUtils.colorResToHtmlColor(getActivity(), R.color.white);
        String htmlTag = "<font color=" + color + ">" + getCurrentTagName() + "</font>";
        String htmlLabel = getString(R.string.reader_label_tag_preview, htmlTag);
        txtTagName.setText(Html.fromHtml(htmlLabel));
    }

    /*
     * refresh adapter so latest posts appear
     */
    private void refreshPosts() {
        hideNewPostsBar();
        if (hasPostAdapter()) {
            getPostAdapter().refresh();
        }
    }

    /*
     * tell the adapter to reload a single post - called when user returns from detail, where the
     * post may have been changed (either by the user, or because it updated)
     */
    private void reloadPost(ReaderPost post) {
        if (post != null && hasPostAdapter()) {
            getPostAdapter().reloadPost(post);
        }
    }

    /*
     * get posts for the current blog from the server
     */
    private void updatePostsInCurrentBlogOrFeed(final UpdateAction updateAction) {
        if (!NetworkUtils.isNetworkAvailable(getActivity())) {
            AppLog.i(T.READER, "reader post list > network unavailable, canceled blog update");
            return;
        }
        if (mCurrentFeedId != 0) {
            ReaderPostService.startServiceForFeed(getActivity(), mCurrentFeedId, updateAction);
        } else {
            ReaderPostService.startServiceForBlog(getActivity(), mCurrentBlogId, updateAction);
        }
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(ReaderEvents.UpdatePostsStarted event) {
        if (!isAdded()) return;

        setIsUpdating(true, event.getAction());
        setEmptyTitleAndDescription(false);
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(ReaderEvents.UpdatePostsEnded event) {
        if (!isAdded()) return;

        setIsUpdating(false, event.getAction());
        if (event.getReaderTag() != null && !isCurrentTag(event.getReaderTag())) {
            return;
        }

        // determine whether to show the "new posts" bar - when this is shown, the newly
        // downloaded posts aren't displayed until the user taps the bar - only appears
        // when there are new posts in a followed tag and the user has scrolled the list
        // beyond the first post
        if (event.getResult() == ReaderActions.UpdateResult.HAS_NEW
                && event.getAction() == UpdateAction.REQUEST_NEWER
                && getPostListType() == ReaderPostListType.TAG_FOLLOWED
                && !isPostAdapterEmpty()
                && !isFirstPostVisible()) {
            showNewPostsBar();
        } else if (event.getResult().isNewOrChanged()) {
            refreshPosts();
        } else {
            boolean requestFailed = (event.getResult() == ReaderActions.UpdateResult.FAILED);
            setEmptyTitleAndDescription(requestFailed);
        }
    }

    /*
     * returns true if the first post is still visible in the RecyclerView - will return
     * false if the first post is scrolled out of view, or if the list is empty
     */
    private boolean isFirstPostVisible() {
        if (!isAdded()
                || mRecyclerView == null
                || mRecyclerView.getLayoutManager() == null) {
            return false;
        }

        View child = mRecyclerView.getLayoutManager().getChildAt(0);
        return (child != null && mRecyclerView.getLayoutManager().getPosition(child) == 0);
    }

    /*
     * get latest posts for this tag from the server
     */
    private void updatePostsWithTag(ReaderTag tag, UpdateAction updateAction) {
        if (!NetworkUtils.isNetworkAvailable(getActivity())) {
            AppLog.i(T.READER, "reader post list > network unavailable, canceled tag update");
            return;
        }
        ReaderPostService.startServiceForTag(getActivity(), tag, updateAction);
    }

    private void updateCurrentTag() {
        updatePostsWithTag(getCurrentTag(), UpdateAction.REQUEST_NEWER);
    }

    private boolean isUpdating() {
        return mIsUpdating;
    }

    private void showSwipeToRefreshProgress(boolean showProgress) {
        if (mSwipeToRefreshHelper != null && mSwipeToRefreshHelper.isRefreshing() != showProgress) {
            mSwipeToRefreshHelper.setRefreshing(showProgress);
        }
    }

    /*
    * show/hide progress bar which appears at the bottom of the activity when loading more posts
    */
    private void showLoadingProgress(boolean showProgress) {
        if (isAdded() && mProgress != null) {
            if (showProgress) {
                mProgress.bringToFront();
                mProgress.setVisibility(View.VISIBLE);
            } else {
                mProgress.setVisibility(View.GONE);
            }
        }
    }

    private void setIsUpdating(boolean isUpdating, UpdateAction updateAction) {
        if (!isAdded() || mIsUpdating == isUpdating) {
            return;
        }

        if (updateAction == UpdateAction.REQUEST_OLDER) {
            // show/hide progress bar at bottom if these are older posts
            showLoadingProgress(isUpdating);
        } else if (isUpdating && isPostAdapterEmpty()) {
            // show swipe-to-refresh if update started and no posts are showing
            showSwipeToRefreshProgress(true);
        } else if (!isUpdating) {
            // hide swipe-to-refresh progress if update is complete
            showSwipeToRefreshProgress(false);
        }
        mIsUpdating = isUpdating;
    }

    /*
     * bar that appears at the top when new posts have been retrieved
     */
    private boolean isNewPostsBarShowing() {
        return (mNewPostsBar != null && mNewPostsBar.getVisibility() == View.VISIBLE);
    }

    private void showNewPostsBar() {
        if (!isAdded() || isNewPostsBarShowing()) {
            return;
        }

        AniUtils.startAnimation(mNewPostsBar, R.anim.reader_top_bar_in);
        mNewPostsBar.setVisibility(View.VISIBLE);
    }

    private void hideNewPostsBar() {
        if (!isAdded() || !isNewPostsBarShowing() || mIsAnimatingOutNewPostsBar) {
            return;
        }

        mIsAnimatingOutNewPostsBar = true;

        Animation.AnimationListener listener = new Animation.AnimationListener() {
            @Override
            public void onAnimationStart(Animation animation) { }
            @Override
            public void onAnimationEnd(Animation animation) {
                if (isAdded()) {
                    mNewPostsBar.setVisibility(View.GONE);
                    mIsAnimatingOutNewPostsBar = false;
                }
            }
            @Override
            public void onAnimationRepeat(Animation animation) { }
        };
        AniUtils.startAnimation(mNewPostsBar, R.anim.reader_top_bar_out, listener);
    }

    /*
     * make sure current tag still exists, reset to default if it doesn't
     */
    private void checkCurrentTag() {
        if (hasCurrentTag()
                && getPostListType().equals(ReaderPostListType.TAG_FOLLOWED)
                && !ReaderTagTable.tagExists(getCurrentTag())) {
            mCurrentTag = ReaderTag.getDefaultTag();
        }
    }

    /*
     * refresh the list of tags shown in the toolbar spinner
     */
    private void refreshTags() {
        if (!isAdded()) {
            return;
        }
        checkCurrentTag();
        if (hasSpinnerAdapter()) {
            getSpinnerAdapter().refreshTags();
        }
    }

    /*
     * called from host activity after user adds/removes tags
     */
    private void doTagsChanged(final String newCurrentTag) {
        checkCurrentTag();
        getSpinnerAdapter().reloadTags();
        if (!TextUtils.isEmpty(newCurrentTag)) {
            setCurrentTag(new ReaderTag(newCurrentTag, ReaderTagType.FOLLOWED), true);
        }
    }

    /*
     * are we showing all posts with a specific tag (followed or previewed), or all
     * posts in a specific blog?
     */
    private ReaderPostListType getPostListType() {
        return (mPostListType != null ? mPostListType : ReaderTypes.DEFAULT_POST_LIST_TYPE);
    }

    /*
     * toolbar spinner adapter which shows list of tags
     */
    private ReaderTagSpinnerAdapter getSpinnerAdapter() {
        if (mSpinnerAdapter == null) {
            AppLog.d(T.READER, "reader post list > creating spinner adapter");
            ReaderInterfaces.DataLoadedListener dataListener = new ReaderInterfaces.DataLoadedListener() {
                @Override
                public void onDataLoaded(boolean isEmpty) {
                    if (isAdded()) {
                        AppLog.d(T.READER, "reader post list > spinner adapter loaded");
                        selectTagInSpinner(getCurrentTag());
                    }
                }
            };
            mSpinnerAdapter = new ReaderTagSpinnerAdapter(getActivity(), dataListener);
        }

        return mSpinnerAdapter;
    }

    private boolean hasSpinnerAdapter() {
        return (mSpinnerAdapter != null);
    }

    /*
     * make sure the passed tag is the one selected in the spinner
     */
    private void selectTagInSpinner(final ReaderTag tag) {
        if (mTagSpinner == null || !hasSpinnerAdapter()) {
            return;
        }
        int position = getSpinnerAdapter().getIndexOfTag(tag);
        if (position > -1 && position != mTagSpinner.getSelectedItemPosition()) {
            mTagSpinner.setSelection(position);
        }
    }

    /*
     * used by blog preview - tell the blog info view to show the current blog/feed
     * if it's not already loaded, then shows/updates posts once the info is loaded
     */
    private void loadBlogOrFeedInfo() {
        if (mBlogInfoView != null && mBlogInfoView.isEmpty()) {
            AppLog.d(T.READER, "reader post list > loading blogInfo");
            ReaderBlogInfoView.BlogInfoListener listener = new ReaderBlogInfoView.BlogInfoListener() {
                @Override
                public void onBlogInfoLoaded(ReaderBlog blogInfo) {
                    if (isAdded()) {
                        mCurrentBlogId = blogInfo.blogId;
                        mCurrentFeedId = blogInfo.feedId;
                        if (isPostAdapterEmpty()) {
                            getPostAdapter().setCurrentBlog(mCurrentBlogId);
                            updatePostsInCurrentBlogOrFeed(UpdateAction.REQUEST_NEWER);
                        }
                        if (mFollowButton != null) {
                            mFollowButton.setIsFollowed(blogInfo.isFollowing);
                        }
                    }
                }
                @Override
                public void onBlogInfoFailed() {
                    if (isAdded()) {
                        ToastUtils.showToast(getActivity(), R.string.reader_toast_err_get_blog_info, ToastUtils.Duration.LONG);
                    }
                }
            };
            if (mCurrentFeedId != 0) {
                mBlogInfoView.loadFeedInfo(mCurrentFeedId, listener);
            } else {
                mBlogInfoView.loadBlogInfo(mCurrentBlogId, listener);
            }
        }
    }

    /*
    * user tapped follow button in toolbar to follow/unfollow the current blog
    */
    private void toggleBlogFollowStatus() {
        if (!isAdded() || mFollowButton == null) {
            return;
        }

        final boolean isAskingToFollow;
        if (mCurrentFeedId != 0) {
            isAskingToFollow = !ReaderBlogTable.isFollowedFeed(mCurrentFeedId);
        } else {
            isAskingToFollow = !ReaderBlogTable.isFollowedBlog(mCurrentBlogId);
        }

        ReaderActions.ActionListener followListener = new ReaderActions.ActionListener() {
            @Override
            public void onActionResult(boolean succeeded) {
                if (!succeeded && isAdded()) {
                    mFollowButton.setIsFollowed(!isAskingToFollow);
                }
            }
        };

        mFollowButton.setIsFollowedAnimated(isAskingToFollow);
        if (mCurrentFeedId != 0) {
            ReaderBlogActions.followFeedById(mCurrentFeedId, isAskingToFollow, followListener);
        } else {
            ReaderBlogActions.followBlogById(mCurrentBlogId, isAskingToFollow, followListener);
        }
    }

    /*
     * user tapped follow button in toolbar to follow/unfollow the current tag
     */
    private void toggleTagFollowStatus() {
        if (!isAdded() || mFollowButton == null) {
            return;
        }

        boolean isAskingToFollow = !ReaderTagTable.isFollowedTagName(getCurrentTagName());
        mFollowButton.setIsFollowedAnimated(isAskingToFollow);
        ReaderTagActions.TagAction action = (isAskingToFollow ? ReaderTagActions.TagAction.ADD : ReaderTagActions.TagAction.DELETE);
        ReaderTagActions.performTagAction(getCurrentTag(), action, null);
    }

    /*
     * called from adapter when user taps a post
     */
    @Override
    public void onPostSelected(long blogId, long postId) {
        if (!isAdded()) return;

        ReaderPostListType type = getPostListType();
        Map<String, Object> analyticsProperties = new HashMap<>();

        switch (type) {
            case TAG_FOLLOWED:
            case TAG_PREVIEW:
                String key = (type == ReaderPostListType.TAG_PREVIEW ?
                        AnalyticsTracker.READER_DETAIL_TYPE_TAG_PREVIEW :
                        AnalyticsTracker.READER_DETAIL_TYPE_NORMAL);
                analyticsProperties.put(AnalyticsTracker.READER_DETAIL_TYPE_KEY, key);
                ReaderActivityLauncher.showReaderPostPagerForTag(
                        getActivity(),
                        getCurrentTag(),
                        getPostListType(),
                        blogId,
                        postId);
                break;
            case BLOG_PREVIEW:
                analyticsProperties.put(AnalyticsTracker.READER_DETAIL_TYPE_KEY,
                        AnalyticsTracker.READER_DETAIL_TYPE_BLOG_PREVIEW);
                ReaderActivityLauncher.showReaderPostPagerForBlog(
                        getActivity(),
                        blogId,
                        postId);
                break;
        }
        AnalyticsTracker.track(AnalyticsTracker.Stat.READER_OPENED_ARTICLE, analyticsProperties);
    }

    /*
     * called from adapter when user taps a tag on a post
     */
    @Override
    public void onTagSelected(String tagName) {
        if (!isAdded()) return;

        ReaderTag tag = new ReaderTag(tagName, ReaderTagType.FOLLOWED);
        if (getPostListType().equals(ReaderTypes.ReaderPostListType.TAG_PREVIEW)) {
            // user is already previewing a tag, so change current tag in existing preview
            setCurrentTag(tag, true);
        } else {
            // user isn't previewing a tag, so open in tag preview
            ReaderActivityLauncher.showReaderTagPreview(getActivity(), tag);
        }
    }

    /*
     * called when user taps dropdown arrow icon next to a post - shows a popup menu
     * that enables blocking the blog the post is in
     */
    @Override
    public void onShowPostPopup(View view, final ReaderPost post) {
        if (view == null || post == null || !isAdded()) {
            return;
        }

        PopupMenu popup = new PopupMenu(getActivity(), view);
        MenuItem menuItem = popup.getMenu().add(getString(R.string.reader_menu_block_blog));
        menuItem.setOnMenuItemClickListener(new MenuItem.OnMenuItemClickListener() {
            @Override
            public boolean onMenuItemClick(MenuItem item) {
                blockBlogForPost(post);
                return true;
            }
        });
        popup.show();
    }

    /*
     * called from activity to handle reader-related onActivityResult
     */
    @Override
    public void onActivityResult(int requestCode, int resultCode, Intent data) {
        switch (requestCode) {
            // user just returned from the tags/subs activity
            case RequestCodes.READER_SUBS:
                if (data != null) {
                    boolean tagsChanged = data.getBooleanExtra(ReaderSubsActivity.KEY_TAGS_CHANGED, false);
                    boolean blogsChanged = data.getBooleanExtra(ReaderSubsActivity.KEY_BLOGS_CHANGED, false);
                    // reload tags if they were changed, and set the last tag added as the current one
                    if (tagsChanged) {
                        String lastAddedTag = data.getStringExtra(ReaderSubsActivity.KEY_LAST_ADDED_TAG_NAME);
                        doTagsChanged(lastAddedTag);
                    }
                    // refresh posts if blogs changed and user is viewing "Blogs I Follow"
                    if (blogsChanged
                            && getPostListType() == ReaderTypes.ReaderPostListType.TAG_FOLLOWED
                            && hasCurrentTag()
                            && getCurrentTag().isBlogsIFollow()) {
                        refreshPosts();
                    }
                }
                break;

            // user just returned from reblogging activity, reload the displayed post if reblogging
            // succeeded
            case RequestCodes.READER_REBLOG:
                if (resultCode == Activity.RESULT_OK && data != null) {
                    long blogId = data.getLongExtra(ReaderConstants.ARG_BLOG_ID, 0);
                    long postId = data.getLongExtra(ReaderConstants.ARG_POST_ID, 0);
                    reloadPost(ReaderPostTable.getPost(blogId, postId, true));
                }
                break;
        }
    }

    /*
     * purge reader db if it hasn't been done yet, but only if there's an active connection
     * since we don't want to purge posts that the user would expect to see when offline
     */
    private void purgeDatabaseIfNeeded() {
        if (EventBus.getDefault().getStickyEvent(ReaderEvents.HasPurgedDatabase.class) == null
                && NetworkUtils.isNetworkAvailable(getActivity())) {
            AppLog.d(T.READER, "reader post list > purging database");
            ReaderDatabase.purgeAsync();
            EventBus.getDefault().postSticky(new ReaderEvents.HasPurgedDatabase());
        }
    }

    /*
     * initial update performed the first time the user opens the reader
     */
    private void performInitialUpdateIfNeeded() {
        if (EventBus.getDefault().getStickyEvent(ReaderEvents.HasPerformedInitialUpdate.class) == null
                && NetworkUtils.isNetworkAvailable(getActivity())) {
            // update current user to ensure we have their user_id as well as their latest info
            // in case they changed their avatar, name, etc. since last time
            AppLog.d(T.READER, "reader post list > updating current user");
            EventBus.getDefault().postSticky(new ReaderEvents.HasPerformedInitialUpdate());
        }
    }

    /*
     * start background service to get the latest followed tags and blogs if it's time to do so
     */
    private void updateFollowedTagsAndBlogsIfNeeded() {
        ReaderEvents.UpdatedFollowedTagsAndBlogs lastUpdateEvent =
                EventBus.getDefault().getStickyEvent(ReaderEvents.UpdatedFollowedTagsAndBlogs.class);
        if (lastUpdateEvent != null && lastUpdateEvent.minutesSinceLastUpdate() < 120) {
            return;
        }

        AppLog.d(T.READER, "reader post list > updating tags and blogs");
        EventBus.getDefault().postSticky(new ReaderEvents.UpdatedFollowedTagsAndBlogs());

        ReaderUpdateService.startService(getActivity(),
                EnumSet.of(ReaderUpdateService.UpdateTask.TAGS,
                           ReaderUpdateService.UpdateTask.FOLLOWED_BLOGS));
    }

    @Override
    public void onScrollToTop() {
        if (isAdded() && getCurrentPosition() > 0) {
            mRecyclerView.getLayoutManager().smoothScrollToPosition(mRecyclerView, null, 0);
        }
    }
}
