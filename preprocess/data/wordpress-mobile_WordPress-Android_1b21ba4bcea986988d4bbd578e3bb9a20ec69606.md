Refactoring Types: ['Extract Method']
rdpress/android/ui/prefs/BlogPreferencesActivity.java
package org.wordpress.android.ui.prefs;

import android.app.Fragment;
import android.os.Bundle;
import android.support.v7.app.ActionBar;
import android.support.v7.app.AppCompatActivity;
import android.view.MenuItem;
import android.widget.Toast;

import org.wordpress.android.R;
import org.wordpress.android.WordPress;
import org.wordpress.android.models.Blog;
import org.wordpress.android.ui.ActivityLauncher;
import org.wordpress.android.util.StringUtils;

/**
 * Activity for configuring blog specific settings.
 */
public class BlogPreferencesActivity extends AppCompatActivity {
    public static final String ARG_LOCAL_BLOG_ID = "local_blog_id";
    public static final int RESULT_BLOG_REMOVED = RESULT_FIRST_USER;

    // The blog this activity is managing settings for.
    private Blog blog;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        Integer id = getIntent().getIntExtra(ARG_LOCAL_BLOG_ID, -1);
        blog = WordPress.getBlog(id);

        if (blog == null) {
            Toast.makeText(this, getString(R.string.blog_not_found), Toast.LENGTH_SHORT).show();
            finish();
            return;
        }

        Fragment siteSettingsFragment = new SiteSettingsFragment();
        siteSettingsFragment.setArguments(getIntent().getExtras());
        getFragmentManager().beginTransaction()
                .replace(android.R.id.content, siteSettingsFragment)
                .commit();

        ActionBar actionBar = getSupportActionBar();
        if (actionBar != null) {
            actionBar.setElevation(0.0f);
            actionBar.setTitle(StringUtils.unescapeHTML(blog.getNameOrHostUrl()));
            actionBar.setDisplayHomeAsUpEnabled(true);
        }
    }

    @Override
    public void finish() {
        super.finish();
        ActivityLauncher.slideOutToRight(this);
    }

    @Override
    protected void onPause() {
        super.onPause();

        WordPress.wpDB.saveBlog(blog);

        if (WordPress.getCurrentBlog().getLocalTableBlogId() == blog.getLocalTableBlogId()) {
            WordPress.currentBlog = blog;
        }
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        int itemID = item.getItemId();
        if (itemID == android.R.id.home) {
            finish();
            return true;
        }

        return super.onOptionsItemSelected(item);
    }
}


File: WordPress/src/main/java/org/wordpress/android/ui/prefs/SiteSettingsFragment.java
package org.wordpress.android.ui.prefs;

import android.os.Bundle;
import android.preference.EditTextPreference;
import android.preference.ListPreference;
import android.preference.MultiSelectListPreference;
import android.preference.Preference;
import android.preference.PreferenceFragment;
import android.preference.PreferenceManager;
import android.view.Menu;
import android.view.MenuInflater;
import android.view.MenuItem;

import com.android.volley.VolleyError;
import com.wordpress.rest.RestRequest;

import org.json.JSONObject;
import org.wordpress.android.R;
import org.wordpress.android.WordPress;
import org.wordpress.android.models.Blog;
import org.wordpress.android.networking.RestClientUtils;
import org.wordpress.android.util.ToastUtils;

import java.util.HashMap;
import java.util.Locale;

/**
 * Handles changes to WordPress site settings. Syncs with host automatically when user leaves.
 */

public class SiteSettingsFragment extends PreferenceFragment
        implements Preference.OnPreferenceChangeListener {
    private static final HashMap<String, Integer> LANGUAGE_CODES = new HashMap<>();

    static {
        LANGUAGE_CODES.put("az", 79);
        LANGUAGE_CODES.put("en", 1);
        LANGUAGE_CODES.put("de", 15);
        LANGUAGE_CODES.put("el", 17);
        LANGUAGE_CODES.put("es", 19);
        LANGUAGE_CODES.put("fr", 24);
        LANGUAGE_CODES.put("gd", 476);
        LANGUAGE_CODES.put("hi", 30);
        LANGUAGE_CODES.put("hu", 31);
        LANGUAGE_CODES.put("id", 33);
        LANGUAGE_CODES.put("it", 35);
        LANGUAGE_CODES.put("ja", 36);
        LANGUAGE_CODES.put("ko", 40);
        LANGUAGE_CODES.put("nb", -1);// ??
        LANGUAGE_CODES.put("nl", 49);
        LANGUAGE_CODES.put("pl", 58);
        LANGUAGE_CODES.put("ru", 62);
        LANGUAGE_CODES.put("sv", 68);
        LANGUAGE_CODES.put("th", 71);
        LANGUAGE_CODES.put("uz", 458);
        LANGUAGE_CODES.put("zh-CN", 449);
        LANGUAGE_CODES.put("zh-TW", 452);
        LANGUAGE_CODES.put("zh-HK", 452);// ??
        LANGUAGE_CODES.put("en-GB", 482);
        LANGUAGE_CODES.put("tr", 78);
        LANGUAGE_CODES.put("eu", 429);
        LANGUAGE_CODES.put("he", 29);
        LANGUAGE_CODES.put("pt-BR", 438);
        LANGUAGE_CODES.put("ar", 3);
        LANGUAGE_CODES.put("ro", 61);
        LANGUAGE_CODES.put("mk", 435);
        LANGUAGE_CODES.put("en-AU", 482);// ??
        LANGUAGE_CODES.put("sr", 67);
        LANGUAGE_CODES.put("sk", 64);
        LANGUAGE_CODES.put("cy", 13);
        LANGUAGE_CODES.put("da", 14);
    }

    private Blog mBlog;
    private EditTextPreference mTitlePreference;
    private EditTextPreference mTaglinePreference;
    private EditTextPreference mAddressPreference;
    private ListPreference mLanguagePreference;
    private MultiSelectListPreference mCategoryPreference;
    private ListPreference mFormatPreference;
    private ListPreference mVisibilityPreference;
    private MenuItem mSaveItem;
    private HashMap<String, String> mLanguageCodes = new HashMap<>();

    private String mRemoteTitle;
    private String mRemoteTagline;
    private String mRemoteAddress;
    private String mRemoteLanguage;
    private int mRemotePrivacy;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        PreferenceManager.getDefaultSharedPreferences(getActivity()).edit().remove(getString(R.string.pref_key_site_language)).commit();

        addPreferencesFromResource(R.xml.site_settings);

        Integer id = getArguments().getInt(BlogPreferencesActivity.ARG_LOCAL_BLOG_ID, -1);
        mBlog = WordPress.getBlog(id);

        if (mBlog == null) return;

        initPreferences();

        WordPress.getRestClientUtils().getGeneralSettings(
                String.valueOf(mBlog.getRemoteBlogId()), new RestRequest.Listener() {
                    @Override
                    public void onResponse(JSONObject response) {
                        if (mTitlePreference != null) {
                            mRemoteTitle = response.optString(RestClientUtils.SITE_TITLE_KEY);
                            mTitlePreference.setText(mRemoteTitle);
                            mTitlePreference.setSummary(mRemoteTitle);
                        }

                        if (mTaglinePreference != null) {
                            mRemoteTagline = response.optString(RestClientUtils.SITE_DESC_KEY);
                            mTaglinePreference.setText(mRemoteTagline);
                            mTaglinePreference.setSummary(mRemoteTagline);
                        }

                        if (mAddressPreference != null) {
                            mRemoteAddress = response.optString(RestClientUtils.SITE_URL_KEY);
                            mAddressPreference.setText(mRemoteAddress);
                            mAddressPreference.setSummary(mRemoteAddress);
                        }

                        if (mLanguagePreference != null) {
                            mRemoteLanguage = getLanguageString(response.optString(RestClientUtils.SITE_LANGUAGE_KEY));
                            mLanguagePreference.setDefaultValue(mRemoteLanguage);
                            mLanguagePreference.setSummary(mRemoteLanguage);
                        }

                        if (mVisibilityPreference != null) {
                            mRemotePrivacy = response.optJSONObject("settings").optInt("blog_public");
                            mVisibilityPreference.setValue(String.valueOf(mRemotePrivacy));
                        }
                    }
                }, new RestRequest.ErrorListener() {
                    @Override
                    public void onErrorResponse(VolleyError error) {
                        if (isAdded()) {
                            ToastUtils.showToast(getActivity(), "Error getting site info");
                        }
                    }
                });

        setHasOptionsMenu(true);

        String[] languageIds = getResources().getStringArray(R.array.lang_ids);
        String[] languageCodes = getResources().getStringArray(R.array.language_codes);

        for (int i = 0; i < languageIds.length && i < languageCodes.length; ++i) {
            mLanguageCodes.put(languageCodes[i], languageIds[i]);
        }
    }

    @Override
    public void onCreateOptionsMenu(Menu menu, MenuInflater menuInflater) {
        super.onCreateOptionsMenu(menu, menuInflater);

        menuInflater.inflate(R.menu.site_settings, menu);

        if (menu == null || (mSaveItem = menu.findItem(R.id.save_site_settings)) == null) return;

        mSaveItem.setOnMenuItemClickListener(
                new MenuItem.OnMenuItemClickListener() {
                    @Override
                    public boolean onMenuItemClick(MenuItem item) {
                        applySettings();
                        return true;
                    }
                });
    }

    @Override
    public boolean onPreferenceChange(Preference preference, Object newValue) {
        if (newValue == null) return false;

        if (preference == mTitlePreference &&
                !newValue.equals(mTitlePreference.getText())) {
            mTitlePreference.setText(newValue.toString());
            mTitlePreference.setSummary(newValue.toString());
            getActivity().setTitle(newValue.toString());

            return true;
        } else if (preference == mTaglinePreference &&
                !newValue.equals(mTaglinePreference.getText())) {
            mTaglinePreference.setText(newValue.toString());
            mTaglinePreference.setSummary(newValue.toString());

            return true;
        } else if (preference == mLanguagePreference &&
                !newValue.equals(mLanguagePreference.getSummary())) {
            mLanguagePreference.setSummary(getLanguageString(newValue.toString()));

            return true;
        } else if (preference == mVisibilityPreference) {
            switch (Integer.valueOf(newValue.toString())) {
                case -1:
                    mVisibilityPreference.setSummary("I would like my site to be private, visible only to users I choose");
                    break;
                case 0:
                    mVisibilityPreference.setSummary("Discourage search engines from indexing this site");
                    break;
                case 1:
                    mVisibilityPreference.setSummary("Allow search engines to index this site");
                    break;
            }

            return true;
        }

        return false;
    }

    /**
     * Helper method to create the parameters for the site settings POST request
     */
    private HashMap<String, String> generatePostParams() {
        HashMap<String, String> params = new HashMap<>();

        // Using undocumented endpoint WPCOM_JSON_API_Site_Settings_Endpoint
        // https://wpcom.trac.automattic.com/browser/trunk/public.api/rest/json-endpoints.php#L1903
        if (mTitlePreference != null && !mTitlePreference.getText().equals(mRemoteTitle)) {
            params.put("blogname", mTitlePreference.getText());
        }

        if (mTaglinePreference != null && !mTaglinePreference.getText().equals(mRemoteTagline)) {
            params.put("blogdescription", mTaglinePreference.getText());
        }

        if (mLanguagePreference != null &&
                mLanguageCodes.containsKey(mLanguagePreference.getValue()) &&
                !mRemoteLanguage.equals(mLanguageCodes.get(mLanguagePreference.getValue()))) {
            params.put("lang_id", String.valueOf(LANGUAGE_CODES.get(mLanguagePreference.getValue())));
        }

        if (mVisibilityPreference != null && Integer.valueOf(mVisibilityPreference.getValue()) != mRemotePrivacy) {
            params.put("blog_public", mVisibilityPreference.getValue());
        }

        return params;
    }

    /**
     * Sends a REST POST request to update site settings
     */
    private void applySettings() {
        final HashMap<String, String> params = generatePostParams();

        WordPress.getRestClientUtils().setGeneralSiteSettings(
                String.valueOf(mBlog.getRemoteBlogId()), new RestRequest.Listener() {
            @Override
            public void onResponse(JSONObject response) {
                // Update local Blog name
                if (params.containsKey("blogname")) {
                    mBlog.setBlogName(params.get("blogname"));
                }
            }
        }, new RestRequest.ErrorListener() {
            @Override
            public void onErrorResponse(VolleyError error) {
                if (mTaglinePreference != null) {
                    mTaglinePreference.setEnabled(false);
                    mTaglinePreference.setSummary("Failed to retrieve :(");
                }
            }
        }, params);
    }

    /**
     * Helper method to set preference references
     */
    private void initPreferences() {
        mTitlePreference =
                (EditTextPreference) findPreference(getString(R.string.pref_key_site_title));
        mTaglinePreference =
                (EditTextPreference) findPreference(getString(R.string.pref_key_site_tagline));
        mLanguagePreference =
                (ListPreference) findPreference(getString(R.string.pref_key_site_language));
        mVisibilityPreference =
                (ListPreference) findPreference(getString(R.string.pref_key_site_visibility));
        mCategoryPreference =
                (MultiSelectListPreference) findPreference(getString(R.string.pref_key_site_category));
        mFormatPreference =
                (ListPreference) findPreference(getString(R.string.pref_key_site_format));
        mAddressPreference =
                (EditTextPreference) findPreference(getString(R.string.pref_key_site_address));

        if (mTitlePreference != null) {
            mTitlePreference.setOnPreferenceChangeListener(this);
        }

        if (mTaglinePreference != null) {
            mTaglinePreference.setOnPreferenceChangeListener(this);
        }

        if (mLanguagePreference != null) {
            mLanguagePreference.setEntries(createLanguageDisplayStrings(mLanguagePreference.getEntryValues()));
            mLanguagePreference.setOnPreferenceChangeListener(this);
        }

        if (mVisibilityPreference != null) {
            mVisibilityPreference.setOnPreferenceChangeListener(this);
        }

        if (mFormatPreference != null) {
            mFormatPreference.setOnPreferenceChangeListener(this);
        }
    }

    private CharSequence[] createLanguageDisplayStrings(CharSequence[] languageCodes) {
        if (languageCodes == null || languageCodes.length < 1) return null;

        CharSequence[] displayStrings = new CharSequence[languageCodes.length];

        for (int i = 0; i < languageCodes.length; ++i) {
            displayStrings[i] = getLanguageString(String.valueOf(languageCodes[i]));
        }

        return displayStrings;
    }

    /**
     * Return a non-null display string for a given language code.
     */
    private String getLanguageString(String languagueCode) {
        if (languagueCode == null || languagueCode.length() < 2) {
            return "";
        } else if (languagueCode.length() == 2) {
            return new Locale(languagueCode).getDisplayLanguage();
        } else {
            return new Locale(languagueCode.substring(0, 2)).getDisplayLanguage() + languagueCode.substring(2);
        }
    }

    private void toggleSaveItemVisibility(boolean on) {
        if (mSaveItem != null) {
            mSaveItem.setVisible(on);
            mSaveItem.setEnabled(on);
        }
    }
}


File: libs/utils/WordPressUtils/src/main/java/org/wordpress/android/util/StringUtils.java
package org.wordpress.android.util;

import android.text.Html;
import android.text.TextUtils;

import org.wordpress.android.util.AppLog.T;

import java.math.BigInteger;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class StringUtils {
    public static String[] mergeStringArrays(String array1[], String array2[]) {
        if (array1 == null || array1.length == 0) {
            return array2;
        }
        if (array2 == null || array2.length == 0) {
            return array1;
        }
        List<String> array1List = Arrays.asList(array1);
        List<String> array2List = Arrays.asList(array2);
        List<String> result = new ArrayList<String>(array1List);
        List<String> tmp = new ArrayList<String>(array1List);
        tmp.retainAll(array2List);
        result.addAll(array2List);
        return ((String[]) result.toArray(new String[result.size()]));
    }

    public static String convertHTMLTagsForUpload(String source) {
        // bold
        source = source.replace("<b>", "<strong>");
        source = source.replace("</b>", "</strong>");

        // italics
        source = source.replace("<i>", "<em>");
        source = source.replace("</i>", "</em>");

        return source;
    }

    public static String convertHTMLTagsForDisplay(String source) {
        // bold
        source = source.replace("<strong>", "<b>");
        source = source.replace("</strong>", "</b>");

        // italics
        source = source.replace("<em>", "<i>");
        source = source.replace("</em>", "</i>");

        return source;
    }

    public static String addPTags(String source) {
        String[] asploded = source.split("\n\n");

        if (asploded.length > 0) {
            StringBuilder wrappedHTML = new StringBuilder();
            for (int i = 0; i < asploded.length; i++) {
                String trimmed = asploded[i].trim();
                if (trimmed.length() > 0) {
                    trimmed = trimmed.replace("<br />", "<br>").replace("<br/>", "<br>").replace("<br>\n", "<br>")
                                     .replace("\n", "<br>");
                    wrappedHTML.append("<p>");
                    wrappedHTML.append(trimmed);
                    wrappedHTML.append("</p>");
                }
            }
            return wrappedHTML.toString();
        } else {
            return source;
        }
    }

    public static BigInteger getMd5IntHash(String input) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] messageDigest = md.digest(input.getBytes());
            BigInteger number = new BigInteger(1, messageDigest);
            return number;
        } catch (NoSuchAlgorithmException e) {
            AppLog.e(T.UTILS, e);
            return null;
        }
    }

    public static String getMd5Hash(String input) {
        BigInteger number = getMd5IntHash(input);
        String md5 = number.toString(16);
        while (md5.length() < 32) {
            md5 = "0" + md5;
        }
        return md5;
    }

    public static String unescapeHTML(String html) {
        if (html != null) {
            return Html.fromHtml(html).toString();
        } else {
            return "";
        }
    }

    /*
     * nbradbury - adapted from Html.escapeHtml(), which was added in API Level 16
     * TODO: not thoroughly tested yet, so marked as private - not sure I like the way
     * this replaces two spaces with "&nbsp;"
     */
    private static String escapeHtml(final String text) {
        if (text == null) {
            return "";
        }

        StringBuilder out = new StringBuilder();
        int length = text.length();

        for (int i = 0; i < length; i++) {
            char c = text.charAt(i);

            if (c == '<') {
                out.append("&lt;");
            } else if (c == '>') {
                out.append("&gt;");
            } else if (c == '&') {
                out.append("&amp;");
            } else if (c > 0x7E || c < ' ') {
                out.append("&#").append((int) c).append(";");
            } else if (c == ' ') {
                while (i + 1 < length && text.charAt(i + 1) == ' ') {
                    out.append("&nbsp;");
                    i++;
                }

                out.append(' ');
            } else {
                out.append(c);
            }
        }

        return out.toString();
    }

    /*
     * returns empty string if passed string is null, otherwise returns passed string
     */
    public static String notNullStr(String s) {
        if (s == null) {
            return "";
        }
        return s;
    }

    /**
     * returns true if two strings are equal or two strings are null
     */
    public static boolean equals(String s1, String s2) {
        if (s1 == null) {
            return s2 == null;
        }
        return s1.equals(s2);
    }

    /*
     * capitalizes the first letter in the passed string - based on Apache commons/lang3/StringUtils
     * http://svn.apache.org/viewvc/commons/proper/lang/trunk/src/main/java/org/apache/commons/lang3/StringUtils.java?revision=1497829&view=markup
     */
    public static String capitalize(final String str) {
        int strLen;
        if (str == null || (strLen = str.length()) == 0) {
            return str;
        }

        char firstChar = str.charAt(0);
        if (Character.isTitleCase(firstChar)) {
            return str;
        }

        return new StringBuilder(strLen).append(Character.toTitleCase(firstChar)).append(str.substring(1)).toString();
    }

    /*
     * Wrap an image URL in a photon URL
     * Check out http://developer.wordpress.com/docs/photon/
     */
    public static String getPhotonUrl(String imageUrl, int size) {
        imageUrl = imageUrl.replace("http://", "").replace("https://", "");
        return "http://i0.wp.com/" + imageUrl + "?w=" + size;
    }

    public static String getHost(String url) {
        if (TextUtils.isEmpty(url)) {
            return "";
        }

        int doubleslash = url.indexOf("//");
        if (doubleslash == -1) {
            doubleslash = 0;
        } else {
            doubleslash += 2;
        }

        int end = url.indexOf('/', doubleslash);
        end = (end >= 0) ? end : url.length();

        return url.substring(doubleslash, end);
    }

    public static String replaceUnicodeSurrogateBlocksWithHTMLEntities(final String inputString) {
        final int length = inputString.length();
        StringBuilder out = new StringBuilder(); // Used to hold the output.
        for (int offset = 0; offset < length; ) {
            final int codepoint = inputString.codePointAt(offset);
            final char current = inputString.charAt(offset);
            if (Character.isHighSurrogate(current) || Character.isLowSurrogate(current)) {
                if (EmoticonsUtils.wpSmiliesCodePointToText.get(codepoint) != null) {
                    out.append(EmoticonsUtils.wpSmiliesCodePointToText.get(codepoint));
                } else {
                    final String htmlEscapedChar = "&#x" + Integer.toHexString(codepoint) + ";";
                    out.append(htmlEscapedChar);
                }
            } else {
                out.append(current);
            }
            offset += Character.charCount(codepoint);
        }
        return out.toString();
    }

    /**
     * This method ensures that the output String has only
     * valid XML unicode characters as specified by the
     * XML 1.0 standard. For reference, please see
     * <a href="http://www.w3.org/TR/2000/REC-xml-20001006#NT-Char">the
     * standard</a>. This method will return an empty
     * String if the input is null or empty.
     *
     * @param in The String whose non-valid characters we want to remove.
     * @return The in String, stripped of non-valid characters.
     */
    public static final String stripNonValidXMLCharacters(String in) {
        StringBuilder out = new StringBuilder(); // Used to hold the output.
        char current; // Used to reference the current character.

        if (in == null || ("".equals(in))) {
            return ""; // vacancy test.
        }
        for (int i = 0; i < in.length(); i++) {
            current = in.charAt(i); // NOTE: No IndexOutOfBoundsException caught here; it should not happen.
            if ((current == 0x9) ||
                (current == 0xA) ||
                (current == 0xD) ||
                ((current >= 0x20) && (current <= 0xD7FF)) ||
                ((current >= 0xE000) && (current <= 0xFFFD)) ||
                ((current >= 0x10000) && (current <= 0x10FFFF))) {
                out.append(current);
            }
        }
        return out.toString();
    }

    /*
     * simple wrapper for Integer.valueOf(string) so caller doesn't need to catch NumberFormatException
     */
    public static int stringToInt(String s) {
        return stringToInt(s, 0);
    }
    public static int stringToInt(String s, int defaultValue) {
        if (s == null)
            return defaultValue;
        try {
            return Integer.valueOf(s);
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }

    public static long stringToLong(String s) {
        return stringToLong(s, 0L);
    }
    public static long stringToLong(String s, long defaultValue) {
        if (s == null)
            return defaultValue;
        try {
            return Long.valueOf(s);
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }
}
