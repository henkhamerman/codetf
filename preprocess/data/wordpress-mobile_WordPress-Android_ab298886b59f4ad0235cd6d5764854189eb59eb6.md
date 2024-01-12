Refactoring Types: ['Extract Method']
rdpress/android/ui/ActivityLauncher.java
package org.wordpress.android.ui;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.support.v4.app.ActivityCompat;
import android.support.v4.app.ActivityOptionsCompat;

import org.wordpress.android.R;
import org.wordpress.android.WordPress;
import org.wordpress.android.analytics.AnalyticsTracker;
import org.wordpress.android.models.Blog;
import org.wordpress.android.models.Post;
import org.wordpress.android.networking.SSLCertsViewActivity;
import org.wordpress.android.networking.SelfSignedSSLCertsManager;
import org.wordpress.android.ui.accounts.HelpActivity;
import org.wordpress.android.ui.accounts.NewAccountActivity;
import org.wordpress.android.ui.accounts.NewBlogActivity;
import org.wordpress.android.ui.accounts.SignInActivity;
import org.wordpress.android.ui.comments.CommentsActivity;
import org.wordpress.android.ui.main.SitePickerActivity;
import org.wordpress.android.ui.media.MediaBrowserActivity;
import org.wordpress.android.ui.media.WordPressMediaUtils;
import org.wordpress.android.ui.posts.EditPostActivity;
import org.wordpress.android.ui.posts.PagesListActivity;
import org.wordpress.android.ui.posts.PostsListActivity;
import org.wordpress.android.ui.prefs.BlogPreferencesActivity;
import org.wordpress.android.ui.prefs.SettingsActivity;
import org.wordpress.android.ui.stats.StatsActivity;
import org.wordpress.android.ui.stats.StatsSinglePostDetailsActivity;
import org.wordpress.android.ui.stats.models.PostModel;
import org.wordpress.android.ui.themes.ThemeBrowserActivity;
import org.wordpress.android.util.AppLog;
import org.wordpress.android.util.HelpshiftHelper;
import org.wordpress.android.util.HelpshiftHelper.Tag;

import java.io.IOException;
import java.security.GeneralSecurityException;

public class ActivityLauncher {

    private static final String ARG_DID_SLIDE_IN_FROM_RIGHT = "did_slide_in_from_right";

    public static void showSitePickerForResult(Activity activity, int blogLocalTableId) {
        Intent intent = new Intent(activity, SitePickerActivity.class);
        intent.putExtra(SitePickerActivity.KEY_LOCAL_ID, blogLocalTableId);
        ActivityOptionsCompat options = ActivityOptionsCompat.makeCustomAnimation(
                activity,
                R.anim.activity_slide_in_from_left,
                R.anim.do_nothing);
        ActivityCompat.startActivityForResult(activity, intent, RequestCodes.SITE_PICKER, options.toBundle());
    }

    public static void viewCurrentSite(Context context) {
        Intent intent = new Intent(context, ViewSiteActivity.class);
        slideInFromRight(context, intent);
    }

    public static void viewBlogStats(Context context, int blogLocalTableId) {
        if (blogLocalTableId == 0) return;

        Intent intent = new Intent(context, StatsActivity.class);
        intent.putExtra(StatsActivity.ARG_LOCAL_TABLE_BLOG_ID, blogLocalTableId);
        slideInFromRight(context, intent);
    }

    public static void viewCurrentBlogPosts(Context context) {
        Intent intent = new Intent(context, PostsListActivity.class);
        slideInFromRight(context, intent);
    }

    public static void viewCurrentBlogMedia(Context context) {
        Intent intent = new Intent(context, MediaBrowserActivity.class);
        slideInFromRight(context, intent);
    }

    public static void viewCurrentBlogPages(Context context) {
        Intent intent = new Intent(context, PagesListActivity.class);
        intent.putExtra(PostsListActivity.EXTRA_VIEW_PAGES, true);
        slideInFromRight(context, intent);
    }

    public static void viewCurrentBlogComments(Context context) {
        Intent intent = new Intent(context, CommentsActivity.class);
        slideInFromRight(context, intent);
    }

    public static void viewCurrentBlogThemes(Context context) {
        if (ThemeBrowserActivity.isAccessible()) {
            Intent intent = new Intent(context, ThemeBrowserActivity.class);
            slideInFromRight(context, intent);
        }
    }

    public static void viewBlogSettingsForResult(Activity activity, Blog blog) {
        if (blog == null) return;

        Intent intent = new Intent(activity, BlogPreferencesActivity.class);
        intent.putExtra(BlogPreferencesActivity.ARG_LOCAL_BLOG_ID, blog.getLocalTableBlogId());
        slideInFromRightForResult(activity, intent, RequestCodes.BLOG_SETTINGS);
    }

    public static void viewBlogAdmin(Context context, Blog blog) {
        if (blog == null) return;

        AnalyticsTracker.track(AnalyticsTracker.Stat.OPENED_VIEW_ADMIN);

        Intent intent = new Intent(context, WPWebViewActivity.class);
        intent.putExtra(WPWebViewActivity.AUTHENTICATION_USER, blog.getUsername());
        intent.putExtra(WPWebViewActivity.AUTHENTICATION_PASSWD, blog.getPassword());
        intent.putExtra(WPWebViewActivity.URL_TO_LOAD, blog.getAdminUrl());
        intent.putExtra(WPWebViewActivity.AUTHENTICATION_URL, WPWebViewActivity.getBlogLoginUrl(blog));
        intent.putExtra(WPWebViewActivity.LOCAL_BLOG_ID, blog.getLocalTableBlogId());
        slideInFromRight(context, intent);
    }

    public static void addNewBlogPostOrPageForResult(Activity context, Blog blog, boolean isPage) {
        if (blog == null) return;

        // Create a new post object
        Post newPost = new Post(blog.getLocalTableBlogId(), isPage);
        WordPress.wpDB.savePost(newPost);

        Intent intent = new Intent(context, EditPostActivity.class);
        intent.putExtra(EditPostActivity.EXTRA_POSTID, newPost.getLocalTablePostId());
        intent.putExtra(EditPostActivity.EXTRA_IS_PAGE, isPage);
        intent.putExtra(EditPostActivity.EXTRA_IS_NEW_POST, true);
        context.startActivityForResult(intent, RequestCodes.EDIT_POST);
    }

    public static void editBlogPostOrPageForResult(Activity activity, long postOrPageId, boolean isPage) {
        Intent intent = new Intent(activity.getApplicationContext(), EditPostActivity.class);
        intent.putExtra(EditPostActivity.EXTRA_POSTID, postOrPageId);
        intent.putExtra(EditPostActivity.EXTRA_IS_PAGE, isPage);
        activity.startActivityForResult(intent, RequestCodes.EDIT_POST);
    }

    public static void addMedia(Activity activity) {
        WordPressMediaUtils.launchPictureLibrary(activity);
    }

    public static void viewAccountSettings(Activity activity) {
        Intent intent = new Intent(activity, SettingsActivity.class);
        slideInFromRightForResult(activity, intent, RequestCodes.ACCOUNT_SETTINGS);
    }

    public static void viewHelpAndSupport(Context context, Tag origin) {
        Intent intent = new Intent(context, HelpActivity.class);
        intent.putExtra(HelpshiftHelper.ORIGIN_KEY, origin);
        slideInFromRight(context, intent);
    }

    public static void viewSSLCerts(Context context) {
        try {
            Intent intent = new Intent(context, SSLCertsViewActivity.class);
            SelfSignedSSLCertsManager selfSignedSSLCertsManager = SelfSignedSSLCertsManager.getInstance(context);
            String lastFailureChainDescription =
                    selfSignedSSLCertsManager.getLastFailureChainDescription().replaceAll("\n", "<br/>");
            intent.putExtra(SSLCertsViewActivity.CERT_DETAILS_KEYS, lastFailureChainDescription);
            context.startActivity(intent);
        } catch (GeneralSecurityException e) {
            AppLog.e(AppLog.T.API, e);
        } catch (IOException e) {
            AppLog.e(AppLog.T.API, e);
        }
    }

    public static void newAccountForResult(Activity activity) {
        Intent intent = new Intent(activity, NewAccountActivity.class);
        activity.startActivityForResult(intent, SignInActivity.CREATE_ACCOUNT_REQUEST);
    }

    public static void newBlogForResult(Activity activity) {
        Intent intent = new Intent(activity, NewBlogActivity.class);
        intent.putExtra(NewBlogActivity.KEY_START_MODE, NewBlogActivity.CREATE_BLOG);
        activity.startActivityForResult(intent, RequestCodes.CREATE_BLOG);
    }

    public static void showSignInForResult(Activity activity) {
        Intent intent = new Intent(activity, SignInActivity.class);
        activity.startActivityForResult(intent, RequestCodes.ADD_ACCOUNT);
    }

    public static void viewStatsSinglePostDetails(Context context, PostModel post) {
        if (post == null) return;

        Intent statsPostViewIntent = new Intent(context, StatsSinglePostDetailsActivity.class);
        statsPostViewIntent.putExtra(StatsSinglePostDetailsActivity.ARG_REMOTE_POST_OBJECT, post);
        context.startActivity(statsPostViewIntent);
    }

    public static void addSelfHostedSiteForResult(Activity activity) {
        Intent intent = new Intent(activity, SignInActivity.class);
        intent.putExtra(SignInActivity.START_FRAGMENT_KEY, SignInActivity.ADD_SELF_HOSTED_BLOG);
        activity.startActivityForResult(intent, SignInActivity.CREATE_ACCOUNT_REQUEST);
    }

    public static void slideInFromRight(Context context, Intent intent) {
        if (context instanceof Activity) {
            intent.putExtra(ARG_DID_SLIDE_IN_FROM_RIGHT, true);
            Activity activity = (Activity) context;
            ActivityOptionsCompat options = ActivityOptionsCompat.makeCustomAnimation(
                    activity,
                    R.anim.activity_slide_in_from_right,
                    R.anim.do_nothing);
            ActivityCompat.startActivity(activity, intent, options.toBundle());
        } else {
            context.startActivity(intent);
        }
    }

    public static void slideInFromRightForResult(Activity activity, Intent intent, int requestCode) {
        intent.putExtra(ARG_DID_SLIDE_IN_FROM_RIGHT, true);
        ActivityOptionsCompat options = ActivityOptionsCompat.makeCustomAnimation(
                activity,
                R.anim.activity_slide_in_from_right,
                R.anim.do_nothing);
        ActivityCompat.startActivityForResult(activity, intent, requestCode, options.toBundle());
    }

    /*
     * called in an activity's finish to slide it out to the right if it slid in
     * from the right when started
     */
    public static void slideOutToRight(Activity activity) {
        if (activity != null
                && activity.getIntent() != null
                && activity.getIntent().hasExtra(ARG_DID_SLIDE_IN_FROM_RIGHT)) {
            activity.overridePendingTransition(R.anim.do_nothing, R.anim.activity_slide_out_to_right);
        }
    }
}


File: WordPress/src/main/java/org/wordpress/android/ui/stats/StatsUtils.java
package org.wordpress.android.ui.stats;

import android.annotation.SuppressLint;
import android.content.Context;

import com.android.volley.NetworkResponse;
import com.android.volley.VolleyError;

import org.json.JSONException;
import org.json.JSONObject;
import org.wordpress.android.R;
import org.wordpress.android.WordPress;
import org.wordpress.android.models.AccountHelper;
import org.wordpress.android.models.Blog;
import org.wordpress.android.ui.WPWebViewActivity;
import org.wordpress.android.ui.reader.ReaderActivityLauncher;
import org.wordpress.android.ui.stats.exceptions.StatsError;
import org.wordpress.android.ui.stats.models.AuthorsModel;
import org.wordpress.android.ui.stats.models.ClicksModel;
import org.wordpress.android.ui.stats.models.CommentFollowersModel;
import org.wordpress.android.ui.stats.models.CommentsModel;
import org.wordpress.android.ui.stats.models.FollowersModel;
import org.wordpress.android.ui.stats.models.GeoviewsModel;
import org.wordpress.android.ui.stats.models.InsightsAllTimeModel;
import org.wordpress.android.ui.stats.models.InsightsPopularModel;
import org.wordpress.android.ui.stats.models.InsightsTodayModel;
import org.wordpress.android.ui.stats.models.PostModel;
import org.wordpress.android.ui.stats.models.PublicizeModel;
import org.wordpress.android.ui.stats.models.ReferrersModel;
import org.wordpress.android.ui.stats.models.SearchTermsModel;
import org.wordpress.android.ui.stats.models.TagsContainerModel;
import org.wordpress.android.ui.stats.models.TopPostsAndPagesModel;
import org.wordpress.android.ui.stats.models.VideoPlaysModel;
import org.wordpress.android.ui.stats.models.VisitsModel;
import org.wordpress.android.ui.stats.service.StatsService;
import org.wordpress.android.util.AppLog;
import org.wordpress.android.util.AppLog.T;

import java.io.Serializable;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.TimeZone;
import java.util.concurrent.TimeUnit;

public class StatsUtils {
    @SuppressLint("SimpleDateFormat")
    private static long toMs(String date, String pattern) {
        if (date == null) {
            return -1;
        }

        if (pattern == null) {
            AppLog.w(T.UTILS, "Trying to parse with a null pattern");
            return -1;
        }

        SimpleDateFormat sdf = new SimpleDateFormat(pattern);
        try {
            return sdf.parse(date).getTime();
        } catch (ParseException e) {
            AppLog.e(T.UTILS, e);
        }
        return -1;
    }

    /**
     * Converts date in the form of 2013-07-18 to ms *
     */
    public static long toMs(String date) {
        return toMs(date, StatsConstants.STATS_INPUT_DATE_FORMAT);
    }

    public static String msToString(long ms, String format) {
        SimpleDateFormat sdf = new SimpleDateFormat(format);
        return sdf.format(new Date(ms));
    }

    /**
     * Get the current date of the blog in the form of yyyy-MM-dd (EX: 2013-07-18) *
     */
    public static String getCurrentDateTZ(int localTableBlogID) {
        String timezone = StatsUtils.getBlogTimezone(WordPress.getBlog(localTableBlogID));
        if (timezone == null) {
            AppLog.w(T.UTILS, "Timezone is null. Returning the device time!!");
            return getCurrentDate();
        }

        return getCurrentDateTimeTZ(timezone, StatsConstants.STATS_INPUT_DATE_FORMAT);
    }

    /**
     * Get the current datetime of the blog *
     */
    public static String getCurrentDateTimeTZ(int localTableBlogID) {
        String timezone = StatsUtils.getBlogTimezone(WordPress.getBlog(localTableBlogID));
        if (timezone == null) {
            AppLog.w(T.UTILS, "Timezone is null. Returning the device time!!");
            return getCurrentDatetime();
        }
        String pattern = "yyyy-MM-dd HH:mm:ss"; // precision to seconds
        return getCurrentDateTimeTZ(timezone, pattern);
    }

    /**
     * Get the current datetime of the blog in Ms *
     */
    public static long getCurrentDateTimeMsTZ(int localTableBlogID) {
        String timezone = StatsUtils.getBlogTimezone(WordPress.getBlog(localTableBlogID));
        if (timezone == null) {
            AppLog.w(T.UTILS, "Timezone is null. Returning the device time!!");
            return new Date().getTime();
        }
        String pattern = "yyyy-MM-dd HH:mm:ss"; // precision to seconds
        return toMs(getCurrentDateTimeTZ(timezone, pattern), pattern);
    }

    /**
     * Get the current date in the form of yyyy-MM-dd (EX: 2013-07-18) *
     */
    private static String getCurrentDate() {
        SimpleDateFormat sdf = new SimpleDateFormat(StatsConstants.STATS_INPUT_DATE_FORMAT);
        return sdf.format(new Date());
    }

    /**
     * Get the current date in the form of "yyyy-MM-dd HH:mm:ss"
     */
    private static String getCurrentDatetime() {
        String pattern = "yyyy-MM-dd HH:mm:ss"; // precision to seconds
        SimpleDateFormat sdf = new SimpleDateFormat(pattern);
        return sdf.format(new Date());
    }

    private static String getBlogTimezone(Blog blog) {
        if (blog == null) {
            AppLog.w(T.UTILS, "Blog object is null!! Can't read timezone opt then.");
            return null;
        }

        JSONObject jsonOptions = blog.getBlogOptionsJSONObject();
        String timezone = null;
        if (jsonOptions != null && jsonOptions.has("time_zone")) {
            try {
                timezone = jsonOptions.getJSONObject("time_zone").getString("value");
            } catch (JSONException e) {
                AppLog.e(T.UTILS, "Cannot load time_zone from options: " + jsonOptions, e);
            }
        } else {
            AppLog.w(T.UTILS, "Blog options are null, or doesn't contain time_zone");
        }
        return timezone;
    }

    private static String getCurrentDateTimeTZ(String blogTimeZoneOption, String pattern) {
        Date date = new Date();
        SimpleDateFormat gmtDf = new SimpleDateFormat(pattern);

        if (blogTimeZoneOption == null) {
            AppLog.w(T.UTILS, "blogTimeZoneOption is null. getCurrentDateTZ() will return the device time!");
            return gmtDf.format(date);
        }

        /*
        Convert the timezone to a form that is compatible with Java TimeZone class
        WordPress returns something like the following:
           UTC+0:30   ---->  0.5
           UTC+1      ---->  1.0
           UTC-0:30   ----> -1.0
        */

        AppLog.d(T.STATS, "Parsing the following Timezone received from WP: " + blogTimeZoneOption);
        String timezoneNormalized;
        if (blogTimeZoneOption.equals("0") || blogTimeZoneOption.equals("0.0")) {
            timezoneNormalized = "GMT";
        } else {
            String[] timezoneSplitted = org.apache.commons.lang.StringUtils.split(blogTimeZoneOption, ".");
            timezoneNormalized = timezoneSplitted[0];
            if(timezoneSplitted.length > 1 && timezoneSplitted[1].equals("5")){
                timezoneNormalized += ":30";
            }
            if (timezoneNormalized.startsWith("-")) {
                timezoneNormalized = "GMT" + timezoneNormalized;
            } else {
                if (timezoneNormalized.startsWith("+")) {
                    timezoneNormalized = "GMT" + timezoneNormalized;
                } else {
                    timezoneNormalized = "GMT+" + timezoneNormalized;
                }
            }
        }

        AppLog.d(T.STATS, "Setting the following Timezone: " + timezoneNormalized);
        gmtDf.setTimeZone(TimeZone.getTimeZone(timezoneNormalized));
        return gmtDf.format(date);
    }

    public static String parseDate(String timestamp, String fromFormat, String toFormat) {
        SimpleDateFormat from = new SimpleDateFormat(fromFormat);
        SimpleDateFormat to = new SimpleDateFormat(toFormat);
        try {
            Date date = from.parse(timestamp);
            return to.format(date);
        } catch (ParseException e) {
            AppLog.e(T.STATS, e);
        }
        return "";
    }

    /**
     * Get a diff between two dates
     * @param date1 the oldest date in Ms
     * @param date2 the newest date in Ms
     * @param timeUnit the unit in which you want the diff
     * @return the diff value, in the provided unit
     */
    public static long getDateDiff(Date date1, Date date2, TimeUnit timeUnit) {
        long diffInMillies = date2.getTime() - date1.getTime();
        return timeUnit.convert(diffInMillies, TimeUnit.MILLISECONDS);
    }


    //Calculate the correct start/end date for the selected period
    public static String getPublishedEndpointPeriodDateParameters(StatsTimeframe timeframe, String date) {
        if (date == null) {
            AppLog.w(AppLog.T.STATS, "Can't calculate start and end period without a reference date");
            return null;
        }

        try {
            SimpleDateFormat sdf = new SimpleDateFormat(StatsConstants.STATS_INPUT_DATE_FORMAT);
            Calendar c = Calendar.getInstance();
            c.setFirstDayOfWeek(Calendar.MONDAY);
            Date parsedDate = sdf.parse(date);
            c.setTime(parsedDate);


            final String after;
            final String before;
            switch (timeframe) {
                case DAY:
                    after = StatsUtils.msToString(c.getTimeInMillis(), StatsConstants.STATS_INPUT_DATE_FORMAT);
                    c.add(Calendar.DAY_OF_YEAR, +1);
                    before =  StatsUtils.msToString(c.getTimeInMillis(), StatsConstants.STATS_INPUT_DATE_FORMAT);
                    break;
                case WEEK:
                    c.set(Calendar.DAY_OF_WEEK, Calendar.MONDAY);
                    after = StatsUtils.msToString(c.getTimeInMillis(), StatsConstants.STATS_INPUT_DATE_FORMAT);
                    c.set(Calendar.DAY_OF_WEEK, Calendar.SUNDAY);
                    c.add(Calendar.DAY_OF_YEAR, +1);
                    before = StatsUtils.msToString(c.getTimeInMillis(), StatsConstants.STATS_INPUT_DATE_FORMAT);
                break;
                case MONTH:
                    //first day of the next month
                    c.set(Calendar.DAY_OF_MONTH, c.getActualMaximum(Calendar.DAY_OF_MONTH));
                    c.add(Calendar.DAY_OF_YEAR, +1);
                    before =  StatsUtils.msToString(c.getTimeInMillis(), StatsConstants.STATS_INPUT_DATE_FORMAT);

                    //last day of the prev month
                    c.setTime(parsedDate);
                    c.set(Calendar.DAY_OF_MONTH, c.getActualMinimum(Calendar.DAY_OF_MONTH));
                    after = StatsUtils.msToString(c.getTimeInMillis(), StatsConstants.STATS_INPUT_DATE_FORMAT);
                    break;
                case YEAR:
                    //first day of the next year
                    c.set(Calendar.MONTH, Calendar.DECEMBER);
                    c.set(Calendar.DAY_OF_MONTH, 31);
                    c.add(Calendar.DAY_OF_YEAR, +1);
                    before =  StatsUtils.msToString(c.getTimeInMillis(), StatsConstants.STATS_INPUT_DATE_FORMAT);

                    c.setTime(parsedDate);
                    c.set(Calendar.MONTH, Calendar.JANUARY);
                    c.set(Calendar.DAY_OF_MONTH, 1);
                    after = StatsUtils.msToString(c.getTimeInMillis(), StatsConstants.STATS_INPUT_DATE_FORMAT);
                    break;
                default:
                    AppLog.w(AppLog.T.STATS, "Can't calculate start and end period without a reference timeframe");
                    return null;
            }
            return "&after=" + after + "&before=" + before;
        } catch (ParseException e) {
            AppLog.e(AppLog.T.UTILS, e);
            return null;
        }
    }

    public static int getSmallestWidthDP() {
        return WordPress.getContext().getResources().getInteger(R.integer.smallest_width_dp);
    }

    /**
     * Return the credentials for the  blog or null if not available.
     *
     * 1. Read the credentials at blog level (Jetpack connected with a wpcom account != main account)
     * 2. If credentials are empty read the global wpcom credentials
     * 3. Check that credentials are not empty before launching the activity
     *
     */
    public static String getBlogStatsUsername(int localTableBlogID) {
        Blog currentBlog = WordPress.getBlog(localTableBlogID);
        if (currentBlog == null) {
            return null;
        }
        String statsAuthenticatedUser = currentBlog.getDotcom_username();

        if (org.apache.commons.lang.StringUtils.isEmpty(statsAuthenticatedUser)) {
            // Let's try the global wpcom credentials
            statsAuthenticatedUser = AccountHelper.getDefaultAccount().getUserName();
        }

        if (org.apache.commons.lang.StringUtils.isEmpty(statsAuthenticatedUser)) {
            AppLog.e(AppLog.T.STATS, "WPCOM Credentials for the current blog are null!");
            return null;
        }

        return statsAuthenticatedUser;
    }

    /**
     * Return the remote blogId as stored on the wpcom backend.
     * <p>
     * blogId is always available for dotcom blogs. It could be null on Jetpack blogs
     * with blogOptions still empty or when the option 'jetpack_client_id' is not available in blogOptions.
     * </p>
     * @return String  blogId or null
     */
    public static String getBlogId(int localTableBlogID) {
        Blog currentBlog = WordPress.getBlog(localTableBlogID);
        if (currentBlog == null) {
            return null;
        }
        if (currentBlog.isDotcomFlag()) {
            return String.valueOf(currentBlog.getRemoteBlogId());
        } else {
            return currentBlog.getApi_blogid();
        }
    }

    public static synchronized void logVolleyErrorDetails(final VolleyError volleyError) {
        if (volleyError == null) {
            AppLog.e(T.STATS, "Tried to log a VolleyError, but the error obj was null!");
            return;
        }
        if (volleyError.networkResponse != null) {
            NetworkResponse networkResponse = volleyError.networkResponse;
            AppLog.e(T.STATS, "Network status code: " + networkResponse.statusCode);
            if (networkResponse.data != null) {
                AppLog.e(T.STATS, "Network data: " + new String(networkResponse.data));
            }
        }
        AppLog.e(T.STATS, "Volley Error details: " + volleyError.getMessage(), volleyError);
    }

    public static synchronized Serializable parseResponse(StatsService.StatsEndpointsEnum endpointName, String blogID, JSONObject response)
            throws JSONException {
        Serializable model = null;
        switch (endpointName) {
            case VISITS:
                model = new VisitsModel(blogID, response);
                break;
            case TOP_POSTS:
                model = new TopPostsAndPagesModel(blogID, response);
                break;
            case REFERRERS:
                model = new ReferrersModel(blogID, response);
                break;
            case CLICKS:
                model = new ClicksModel(blogID, response);
                break;
            case GEO_VIEWS:
                model = new GeoviewsModel(blogID, response);
                break;
            case AUTHORS:
                model = new AuthorsModel(blogID, response);
                break;
            case VIDEO_PLAYS:
                model = new VideoPlaysModel(blogID, response);
                break;
            case COMMENTS:
                model = new CommentsModel(blogID, response);
                break;
            case FOLLOWERS_WPCOM:
                model = new FollowersModel(blogID, response);
                break;
            case FOLLOWERS_EMAIL:
                model = new FollowersModel(blogID, response);
                break;
            case COMMENT_FOLLOWERS:
                model = new CommentFollowersModel(blogID, response);
                break;
            case TAGS_AND_CATEGORIES:
                model = new TagsContainerModel(blogID, response);
                break;
            case PUBLICIZE:
                model = new PublicizeModel(blogID, response);
                break;
            case SEARCH_TERMS:
                model = new SearchTermsModel(blogID, response);
                break;
            case INSIGHTS_ALL_TIME:
                model = new InsightsAllTimeModel(blogID, response);
                break;
            case INSIGHTS_POPULAR:
                model = new InsightsPopularModel(blogID, response);
                break;
            case INSIGHTS_TODAY:
                model = new InsightsTodayModel(blogID, response);
                break;
        }
        return model;
    }

    public static void openPostInReaderOrInAppWebview(Context ctx, final PostModel post) {
        final String postType = post.getPostType();
        final String url = post.getUrl();
        final long blogID = Long.parseLong(post.getBlogID());
        final long itemID = Long.parseLong(post.getItemID());
        if (postType.equals("post") || postType.equals("page")) {
            // If the post/page has ID == 0 is the home page, and we need to load the blog preview,
            // otherwise 404 is returned if we try to show the post in the reader
            if (itemID == 0) {
                ReaderActivityLauncher.showReaderBlogPreview(
                        ctx,
                        blogID
                );
            } else {
                ReaderActivityLauncher.showReaderPostDetail(
                        ctx,
                        blogID,
                        itemID
                );
            }
        } else if (postType.equals("homepage")) {
            ReaderActivityLauncher.showReaderBlogPreview(
                    ctx,
                    blogID
            );
        } else {
            AppLog.d(AppLog.T.UTILS, "Opening the in-app browser: " + url);
            WPWebViewActivity.openURL(ctx, url);
        }
    }

    /*
     * This function rewrites a VolleyError into a simple Stats Error by getting the error message.
     * This is a FIX for https://github.com/wordpress-mobile/WordPress-Android/issues/2228 where
     * VolleyErrors cannot be serializable.
     */
    public static StatsError rewriteVolleyError(VolleyError volleyError, String defaultErrorString) {
        if (volleyError != null && volleyError.getMessage() != null) {
            return new StatsError(volleyError.getMessage());
        }

        if (defaultErrorString != null) {
            return new StatsError(defaultErrorString);
        }

        // Error string should be localized here, but don't want to pass a context
        return new StatsError("Stats couldn't be refreshed at this time");
    }
}
