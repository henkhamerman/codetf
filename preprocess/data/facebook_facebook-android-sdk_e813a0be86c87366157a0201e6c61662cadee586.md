Refactoring Types: ['Rename Package', 'Extract Method']
unittests/MainActivity.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook.junittests;

import android.support.v7.app.ActionBarActivity;
import android.os.Bundle;
import android.view.Menu;
import android.view.MenuItem;

import com.facebook.FacebookSdk;


public class MainActivity extends ActionBarActivity {
    private static String APP_ID = "1234";
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        FacebookSdk.sdkInitialize(getApplicationContext());
        FacebookSdk.setApplicationId(APP_ID);
        setContentView(R.layout.activity_main);
    }


    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        // Inflate the menu; this adds items to the action bar if it is present.
        getMenuInflater().inflate(R.menu.menu_main, menu);
        return true;
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        // Handle action bar item clicks here. The action bar will
        // automatically handle clicks on the Home/Up button, so long
        // as you specify a parent activity in AndroidManifest.xml.
        int id = item.getItemId();

        //noinspection SimplifiableIfStatement
        if (id == R.id.action_settings) {
            return true;
        }

        return super.onOptionsItemSelected(item);
    }
}


File: facebook/junitTests/src/test/java/com/facebook/AccessTokenCacheTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Bundle;

import com.facebook.internal.Utility;

import org.json.JSONException;
import org.json.JSONObject;
import org.junit.Before;
import org.junit.Test;
import org.mockito.Mock;
import org.powermock.api.mockito.PowerMockito;
import org.powermock.core.classloader.annotations.PrepareForTest;
import org.robolectric.Robolectric;

import java.util.Arrays;
import java.util.Date;
import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;
import static org.mockito.Matchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyZeroInteractions;
import static org.powermock.api.mockito.PowerMockito.mockStatic;
import static org.powermock.api.mockito.PowerMockito.when;
import static org.powermock.api.mockito.PowerMockito.mock;
import static org.powermock.api.support.membermodification.MemberModifier.stub;

@PrepareForTest( {
        AccessTokenCache.class,
        FacebookSdk.class,
        LegacyTokenHelper.class,
        Utility.class})
public class AccessTokenCacheTest extends FacebookPowerMockTestCase {

    private final String TOKEN_STRING = "A token of my esteem";
    private final String USER_ID = "1000";
    private final List<String> PERMISSIONS = Arrays.asList("walk", "chew gum");
    private final Date EXPIRES = new Date(2025, 5, 3);
    private final Date LAST_REFRESH = new Date(2023, 8, 15);
    private final String APP_ID = "1234";

    private SharedPreferences sharedPreferences;
    @Mock private LegacyTokenHelper cachingStrategy;
    private AccessTokenCache.SharedPreferencesTokenCachingStrategyFactory
            cachingStrategyFactory;

    @Before
    public void before() throws Exception {
        mockStatic(FacebookSdk.class);
        sharedPreferences = Robolectric.application.getSharedPreferences(
                AccessTokenManager.SHARED_PREFERENCES_NAME, Context.MODE_PRIVATE);
        sharedPreferences.edit().clear().commit();
        cachingStrategyFactory = mock(
                AccessTokenCache.SharedPreferencesTokenCachingStrategyFactory.class);
        when(cachingStrategyFactory.create()).thenReturn(cachingStrategy);
        stub(PowerMockito.method(Utility.class, "awaitGetGraphMeRequestWithCache")).toReturn(
                new JSONObject().put("id", "1000"));
    }


    @Test
    public void testLoadReturnsFalseIfNoCachedToken() {
        AccessTokenCache cache = new AccessTokenCache(sharedPreferences, cachingStrategyFactory);

        AccessToken accessToken = cache.load();

        assertNull(accessToken);
        PowerMockito.verifyZeroInteractions(cachingStrategy);
    }

    @Test
    public void testLoadReturnsFalseIfNoCachedOrLegacyToken() {
        when(FacebookSdk.isLegacyTokenUpgradeSupported()).thenReturn(true);

        AccessTokenCache cache = new AccessTokenCache(sharedPreferences, cachingStrategyFactory);

        AccessToken accessToken = cache.load();

        assertNull(accessToken);
    }

    @Test
    public void testLoadReturnsFalseIfEmptyCachedTokenAndDoesNotCheckLegacy() {

        JSONObject jsonObject = new JSONObject();
        sharedPreferences.edit().putString(AccessTokenCache.CACHED_ACCESS_TOKEN_KEY,
                jsonObject.toString()).commit();

        AccessTokenCache cache = new AccessTokenCache(sharedPreferences, cachingStrategyFactory);

        AccessToken accessToken = cache.load();

        assertNull(accessToken);
        verifyZeroInteractions(cachingStrategy);
    }

    @Test
    public void testLoadReturnsFalseIfNoCachedTokenAndEmptyLegacyToken() {
        when(FacebookSdk.isLegacyTokenUpgradeSupported()).thenReturn(true);

        when(cachingStrategy.load()).thenReturn(new Bundle());

        AccessTokenCache cache = new AccessTokenCache(sharedPreferences, cachingStrategyFactory);

        AccessToken accessToken = cache.load();

        assertNull(accessToken);
    }

    @Test
    public void testLoadValidCachedToken() throws JSONException {
        AccessToken accessToken = createAccessToken();
        JSONObject jsonObject = accessToken.toJSONObject();
        sharedPreferences.edit().putString(AccessTokenCache.CACHED_ACCESS_TOKEN_KEY,
                jsonObject.toString()).commit();

        AccessTokenCache cache = new AccessTokenCache(sharedPreferences, cachingStrategyFactory);

        AccessToken loadedAccessToken = cache.load();

        assertNotNull(loadedAccessToken);
        assertEquals(accessToken, loadedAccessToken);
    }

    @Test
    public void testLoadSetsCurrentTokenIfNoCachedTokenButValidLegacyToken() {
        when(FacebookSdk.isLegacyTokenUpgradeSupported()).thenReturn(true);

        AccessToken accessToken = createAccessToken();
        when(cachingStrategy.load()).thenReturn(
                AccessTokenTestHelper.toLegacyCacheBundle(accessToken));

        AccessTokenCache cache = new AccessTokenCache(sharedPreferences, cachingStrategyFactory);

        AccessToken loadedAccessToken = cache.load();

        assertNotNull(loadedAccessToken);
        assertEquals(accessToken, loadedAccessToken);
    }

    @Test
    public void testLoadSavesTokenWhenUpgradingFromLegacyToken() throws JSONException {
        when(FacebookSdk.isLegacyTokenUpgradeSupported()).thenReturn(true);

        AccessToken accessToken = createAccessToken();
        when(cachingStrategy.load()).thenReturn(
                AccessTokenTestHelper.toLegacyCacheBundle(accessToken));

        AccessTokenCache cache = new AccessTokenCache(sharedPreferences, cachingStrategyFactory);
        cache.load();

        assertTrue(sharedPreferences.contains(AccessTokenCache.CACHED_ACCESS_TOKEN_KEY));

        AccessToken savedAccessToken = AccessToken.createFromJSONObject(
                new JSONObject(sharedPreferences.getString(
                        AccessTokenCache.CACHED_ACCESS_TOKEN_KEY, null)));
        assertEquals(accessToken, savedAccessToken);
    }

    @Test
    public void testLoadClearsLegacyCacheWhenUpgradingFromLegacyToken() {
        when(FacebookSdk.isLegacyTokenUpgradeSupported()).thenReturn(true);

        AccessToken accessToken = createAccessToken();
        when(cachingStrategy.load()).thenReturn(
                AccessTokenTestHelper.toLegacyCacheBundle(accessToken));

        AccessTokenCache cache = new AccessTokenCache(sharedPreferences, cachingStrategyFactory);
        cache.load();

        verify(cachingStrategy, times(1)).clear();
    }

    @Test
    public void testSaveRequiresToken() {
        AccessTokenCache cache = new AccessTokenCache(sharedPreferences, cachingStrategyFactory);

        try {
            cache.save(null);
            fail();
        } catch (NullPointerException exception) {
        }
    }

    @Test
    public void testSaveWritesToCacheIfToken() throws JSONException {
        AccessToken accessToken = createAccessToken();
        AccessTokenCache cache = new AccessTokenCache(sharedPreferences, cachingStrategyFactory);

        cache.save(accessToken);

        verify(cachingStrategy, never()).save(any(Bundle.class));
        assertTrue(sharedPreferences.contains(AccessTokenCache.CACHED_ACCESS_TOKEN_KEY));

        AccessToken savedAccessToken = AccessToken.createFromJSONObject(
                new JSONObject(sharedPreferences.getString(
                        AccessTokenCache.CACHED_ACCESS_TOKEN_KEY, null)));
        assertEquals(accessToken, savedAccessToken);
    }

    @Test
    public void testClearCacheClearsCache() {
        AccessToken accessToken = createAccessToken();
        AccessTokenCache cache = new AccessTokenCache(sharedPreferences, cachingStrategyFactory);

        cache.save(accessToken);

        cache.clear();

        assertFalse(sharedPreferences.contains(AccessTokenCache.CACHED_ACCESS_TOKEN_KEY));
        verify(cachingStrategy, never()).clear();
    }

    @Test
    public void testClearCacheClearsLegacyCache() {
        when(FacebookSdk.isLegacyTokenUpgradeSupported()).thenReturn(true);

        AccessToken accessToken = createAccessToken();
        AccessTokenCache cache = new AccessTokenCache(sharedPreferences, cachingStrategyFactory);

        cache.save(accessToken);

        cache.clear();

        assertFalse(sharedPreferences.contains(AccessTokenCache.CACHED_ACCESS_TOKEN_KEY));
        verify(cachingStrategy, times(1)).clear();
    }

    private AccessToken createAccessToken() {
        return createAccessToken(TOKEN_STRING, USER_ID);
    }

    private AccessToken createAccessToken(String tokenString, String userId) {
        return new AccessToken(
                tokenString,
                APP_ID,
                userId,
                PERMISSIONS,
                null,
                AccessTokenSource.WEB_VIEW,
                EXPIRES,
                LAST_REFRESH);
    }
}


File: facebook/junitTests/src/test/java/com/facebook/AccessTokenManagerTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.support.v4.content.LocalBroadcastManager;

import com.facebook.internal.Utility;

import org.json.JSONException;
import org.junit.Before;
import org.junit.Test;
import org.mockito.Mock;
import org.powermock.api.mockito.PowerMockito;
import org.powermock.core.classloader.annotations.PrepareForTest;
import org.robolectric.Robolectric;

import java.util.Arrays;
import java.util.Date;
import java.util.List;

import static org.mockito.Mockito.*;
import static org.junit.Assert.*;
import static org.powermock.api.mockito.PowerMockito.mockStatic;
import static org.powermock.api.mockito.PowerMockito.when;
import static org.powermock.api.support.membermodification.MemberMatcher.method;
import static org.powermock.api.support.membermodification.MemberModifier.suppress;

@PrepareForTest({FacebookSdk.class, AccessTokenCache.class, Utility.class})
public class AccessTokenManagerTest extends FacebookPowerMockTestCase {

    private final String TOKEN_STRING = "A token of my esteem";
    private final String USER_ID = "1000";
    private final List<String> PERMISSIONS = Arrays.asList("walk", "chew gum");
    private final Date EXPIRES = new Date(2025, 5, 3);
    private final Date LAST_REFRESH = new Date(2023, 8, 15);
    private final String APP_ID = "1234";

    private LocalBroadcastManager localBroadcastManager;
    private AccessTokenCache accessTokenCache;

    @Before
    public void before() throws Exception {
        mockStatic(FacebookSdk.class);
        when(FacebookSdk.isInitialized()).thenReturn(true);
        when(FacebookSdk.getApplicationContext()).thenReturn(Robolectric.application);
        suppress(method(Utility.class, "clearFacebookCookies"));

        localBroadcastManager = LocalBroadcastManager.getInstance(Robolectric.application);
        accessTokenCache = mock(AccessTokenCache.class);
    }

    @Test
    public void testRequiresLocalBroadcastManager() {
        try {
            AccessTokenManager accessTokenManager = new AccessTokenManager(null, accessTokenCache);
            fail();
        } catch (NullPointerException ex) {
        }
    }

    @Test
    public void testRequiresTokenCache() {
        try {
            AccessTokenManager accessTokenManager = new AccessTokenManager(localBroadcastManager,
                    null);
            fail();
        } catch (NullPointerException ex) {
        }
    }

    @Test
    public void testDefaultsToNoCurrentAccessToken() {
        AccessTokenManager accessTokenManager = createAccessTokenManager();

        assertNull(accessTokenManager.getCurrentAccessToken());
    }

    @Test
    public void testCanSetCurrentAccessToken() {
        AccessTokenManager accessTokenManager = createAccessTokenManager();

        AccessToken accessToken = createAccessToken();

        accessTokenManager.setCurrentAccessToken(accessToken);

        assertEquals(accessToken, accessTokenManager.getCurrentAccessToken());
    }

    @Test
    public void testChangingAccessTokenSendsBroadcast() {
        AccessTokenManager accessTokenManager = createAccessTokenManager();

        AccessToken accessToken = createAccessToken();

        accessTokenManager.setCurrentAccessToken(accessToken);

        final Intent intents[] = new Intent[1];
        final BroadcastReceiver broadcastReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                intents[0] = intent;
            }
        };

        localBroadcastManager.registerReceiver(broadcastReceiver,
                new IntentFilter(AccessTokenManager.ACTION_CURRENT_ACCESS_TOKEN_CHANGED));

        AccessToken anotherAccessToken = createAccessToken("another string", "1000");

        accessTokenManager.setCurrentAccessToken(anotherAccessToken);

        localBroadcastManager.unregisterReceiver(broadcastReceiver);

        Intent intent = intents[0];

        assertNotNull(intent);

        AccessToken oldAccessToken =
                (AccessToken) intent.getParcelableExtra(AccessTokenManager.EXTRA_OLD_ACCESS_TOKEN);
        AccessToken newAccessToken =
                (AccessToken) intent.getParcelableExtra(AccessTokenManager.EXTRA_NEW_ACCESS_TOKEN);

        assertEquals(accessToken.getToken(), oldAccessToken.getToken());
        assertEquals(anotherAccessToken.getToken(), newAccessToken.getToken());
    }

    @Test
    public void testLoadReturnsFalseIfNoCachedToken() {
        AccessTokenManager accessTokenManager = createAccessTokenManager();

        boolean result = accessTokenManager.loadCurrentAccessToken();

        assertFalse(result);
    }

    @Test
    public void testLoadReturnsTrueIfCachedToken() {
        AccessToken accessToken = createAccessToken();
        when(accessTokenCache.load()).thenReturn(accessToken);

        AccessTokenManager accessTokenManager = createAccessTokenManager();

        boolean result = accessTokenManager.loadCurrentAccessToken();

        assertTrue(result);
    }

    @Test
    public void testLoadSetsCurrentTokenIfCached() {
        AccessToken accessToken = createAccessToken();
        when(accessTokenCache.load()).thenReturn(accessToken);

        AccessTokenManager accessTokenManager = createAccessTokenManager();

        accessTokenManager.loadCurrentAccessToken();

        assertEquals(accessToken, accessTokenManager.getCurrentAccessToken());
    }

    @Test
    public void testSaveWritesToCacheIfToken() throws JSONException {
        AccessToken accessToken = createAccessToken();
        AccessTokenManager accessTokenManager = createAccessTokenManager();

        accessTokenManager.setCurrentAccessToken(accessToken);

        verify(accessTokenCache, times(1)).save(any(AccessToken.class));
    }

    @Test
    public void testSetEmptyTokenClearsCache() {
        AccessTokenManager accessTokenManager = createAccessTokenManager();

        accessTokenManager.setCurrentAccessToken(null);

        verify(accessTokenCache, times(1)).clear();
    }

    @Test
    public void testLoadDoesNotSave() {
        AccessToken accessToken = createAccessToken();
        when(accessTokenCache.load()).thenReturn(accessToken);

        AccessTokenManager accessTokenManager = createAccessTokenManager();

        accessTokenManager.loadCurrentAccessToken();

        verify(accessTokenCache, never()).save(any(AccessToken.class));
    }

    private AccessTokenManager createAccessTokenManager() {
        return new AccessTokenManager(localBroadcastManager, accessTokenCache);
    }

    private AccessToken createAccessToken() {
        return createAccessToken(TOKEN_STRING, USER_ID);
    }

    private AccessToken createAccessToken(String tokenString, String userId) {
        return new AccessToken(
                tokenString,
                APP_ID,
                userId,
                PERMISSIONS,
                null,
                AccessTokenSource.WEB_VIEW,
                EXPIRES,
                LAST_REFRESH);
    }
}


File: facebook/junitTests/src/test/java/com/facebook/AccessTokenTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook;

import android.os.Bundle;

import com.facebook.internal.Utility;

import org.json.JSONException;
import org.json.JSONObject;
import org.junit.Before;
import org.junit.Test;
import org.powermock.api.mockito.PowerMockito;
import org.powermock.core.classloader.annotations.PrepareForTest;
import org.robolectric.Robolectric;

import java.io.IOException;
import java.util.Arrays;
import java.util.Collection;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.junit.Assert.*;
import static org.powermock.api.support.membermodification.MemberModifier.stub;

@PrepareForTest( {Utility.class})
public final class AccessTokenTest extends FacebookPowerMockTestCase {

    @Before
    public void before() throws Exception {
        stub(PowerMockito.method(Utility.class, "awaitGetGraphMeRequestWithCache")).toReturn(
                new JSONObject().put("id", "1000"));
    }

    @Test
    public void testNullTokenThrows() {
        try {
            AccessToken token = new AccessToken(
                    null,
                    "1234",
                    "1000",
                    Utility.arrayList("something"),
                    Utility.arrayList("something_else"),
                    AccessTokenSource.CLIENT_TOKEN,
                    new Date(),
                    new Date());
            fail();
        } catch (IllegalArgumentException e) {
        }
    }

    @Test
    public void testEmptyTokenThrows() {
        try {
            AccessToken token = new AccessToken(
                    "",
                    "1234",
                    "1000",
                    Utility.arrayList("something"),
                    Utility.arrayList("something_else"),
                    AccessTokenSource.CLIENT_TOKEN,
                    new Date(),
                    new Date());
            fail();
        } catch (IllegalArgumentException e) {
        }
    }

    @Test
    public void testNullUserIdThrows() {
        try {
            AccessToken token = new AccessToken(
                    "a token",
                    "1234",
                    null,
                    Utility.arrayList("something"),
                    Utility.arrayList("something_else"),
                    AccessTokenSource.CLIENT_TOKEN,
                    new Date(),
                    new Date());
            fail();
        } catch (IllegalArgumentException e) {
        }
    }

    @Test
    public void testEmptyUserIdThrows() {
        try {
            AccessToken token = new AccessToken(
                    "a token",
                    "1234",
                    "",
                    Utility.arrayList("something"),
                    Utility.arrayList("something_else"),
                    AccessTokenSource.CLIENT_TOKEN,
                    new Date(),
                    new Date());
            fail();
        } catch (IllegalArgumentException e) {
        }
    }

    @Test
    public void testCreateFromRefreshFailure() {
        AccessToken accessToken = new AccessToken(
                "a token",
                "1234",
                "1000",
                Utility.arrayList("stream_publish"),
                null,
                AccessTokenSource.WEB_VIEW,
                null,
                null);

        String token = "AnImaginaryTokenValue";

        Bundle bundle = new Bundle();
        bundle.putString("access_token", "AnImaginaryTokenValue");
        bundle.putString("expires_in", "60");

        try {
            AccessToken.createFromRefresh(accessToken, bundle);
            fail("Expected exception");
        } catch (FacebookException ex) {
            assertEquals("Invalid token source: " + AccessTokenSource.WEB_VIEW, ex.getMessage());
        }
    }

    @Test
    public void testCacheRoundtrip() {
        Set<String> permissions = Utility.hashSet("stream_publish", "go_outside_and_play");
        Set<String> declinedPermissions = Utility.hashSet("no you may not", "no soup for you");
        String token = "AnImaginaryTokenValue";
        Date later = TestUtils.nowPlusSeconds(60);
        Date earlier = TestUtils.nowPlusSeconds(-60);
        String applicationId = "1234";

        Bundle bundle = new Bundle();
        LegacyTokenHelper.putToken(bundle, token);
        LegacyTokenHelper.putExpirationDate(bundle, later);
        LegacyTokenHelper.putSource(
                bundle,
                AccessTokenSource.FACEBOOK_APPLICATION_WEB);
        LegacyTokenHelper.putLastRefreshDate(bundle, earlier);
        LegacyTokenHelper.putPermissions(bundle, permissions);
        LegacyTokenHelper.putDeclinedPermissions(bundle, declinedPermissions);
        LegacyTokenHelper.putApplicationId(bundle, applicationId);

        AccessToken accessToken = AccessToken.createFromLegacyCache(bundle);
        TestUtils.assertSamePermissions(permissions, accessToken);
        assertEquals(token, accessToken.getToken());
        assertEquals(AccessTokenSource.FACEBOOK_APPLICATION_WEB, accessToken.getSource());
        assertTrue(!accessToken.isExpired());

        Bundle cache = AccessTokenTestHelper.toLegacyCacheBundle(accessToken);
        TestUtils.assertEqualContentsWithoutOrder(bundle, cache);
    }

    @Test
    public void testFromCacheWithMissingApplicationId() {
        String token = "AnImaginaryTokenValue";
        String applicationId = "1234";

        Bundle bundle = new Bundle();
        LegacyTokenHelper.putToken(bundle, token);
        // no app id

        FacebookSdk.sdkInitialize(Robolectric.application);
        FacebookSdk.setApplicationId(applicationId);

        AccessToken accessToken = AccessToken.createFromLegacyCache(bundle);

        assertEquals(applicationId, accessToken.getApplicationId());
    }

    @Test
    public void testCachePutGet() {
        Bundle bundle = new Bundle();

        for (String token : new String[] { "", "A completely random token value" }) {
            LegacyTokenHelper.putToken(bundle, token);
            assertEquals(token, LegacyTokenHelper.getToken(bundle));
        }

        for (Date date : new Date[] { new Date(42), new Date() }) {
            LegacyTokenHelper.putExpirationDate(bundle, date);
            assertEquals(date, LegacyTokenHelper.getExpirationDate(bundle));

            LegacyTokenHelper.putLastRefreshDate(bundle, date);
            assertEquals(date, LegacyTokenHelper.getLastRefreshDate(bundle));
        }

        for (long milliseconds : new long[] { 0, -1, System.currentTimeMillis() }) {
            LegacyTokenHelper.putExpirationMilliseconds(bundle, milliseconds);
            assertEquals(
                    milliseconds,
                    LegacyTokenHelper.getExpirationMilliseconds(bundle));

            LegacyTokenHelper.putLastRefreshMilliseconds(bundle, milliseconds);
            assertEquals(
                    milliseconds,
                    LegacyTokenHelper.getLastRefreshMilliseconds(bundle));
        }

        for (AccessTokenSource source : AccessTokenSource.values()) {
            LegacyTokenHelper.putSource(bundle, source);
            assertEquals(source, LegacyTokenHelper.getSource(bundle));
        }

        String userId = "1000";

        List<String> normalList = Arrays.asList("", "Another completely random token value");
        List<String> emptyList = Arrays.asList();
        HashSet<String> normalArrayList = new HashSet<String>(normalList);
        HashSet<String> emptyArrayList = new HashSet<String>();
        @SuppressWarnings("unchecked")
        List<Collection<String>> permissionLists = Arrays
                .asList(normalList, emptyList, normalArrayList, emptyArrayList);
        for (Collection<String> list : permissionLists) {
            LegacyTokenHelper.putPermissions(bundle, list);
            TestUtils.assertSamePermissions(
                    list,
                    LegacyTokenHelper.getPermissions(bundle));
        }
        normalArrayList.add(null);
    }

    @Test
    public void testRoundtripJSONObject() throws JSONException {
        AccessToken accessToken = new AccessToken(
                "a token",
                "1234",
                "1000",
                Arrays.asList("permission_1", "permission_2"),
                Arrays.asList("declined permission_1", "declined permission_2"),
                AccessTokenSource.WEB_VIEW,
                new Date(2015, 3, 3),
                new Date(2015, 1, 1));

        JSONObject jsonObject = accessToken.toJSONObject();

        AccessToken deserializedAccessToken = AccessToken.createFromJSONObject(jsonObject);

        assertEquals(accessToken, deserializedAccessToken);
    }

    @Test
    public void testParceling() throws IOException {
        String token = "a token";
        String appId = "1234";
        String userId = "1000";
        Set<String> permissions = new HashSet<String>(
                Arrays.asList("permission_1", "permission_2"));
        Set<String> declinedPermissions = new HashSet<String>(
                Arrays.asList("permission_3"));
        AccessTokenSource source = AccessTokenSource.WEB_VIEW;
        AccessToken accessToken1 = new AccessToken(
                token,
                appId,
                userId,
                permissions,
                declinedPermissions,
                source,
                null,
                null);

        AccessToken accessToken2 = TestUtils.parcelAndUnparcel(accessToken1);
        assertEquals(accessToken1, accessToken2);
        assertEquals(token, accessToken2.getToken());
        assertEquals(appId, accessToken2.getApplicationId());
        assertEquals(permissions, accessToken2.getPermissions());
        assertEquals(declinedPermissions, accessToken2.getDeclinedPermissions());
        assertEquals(accessToken1.getExpires(), accessToken2.getExpires());
        assertEquals(accessToken1.getLastRefresh(), accessToken2.getLastRefresh());
        assertEquals(accessToken1.getUserId(), accessToken2.getUserId());
    }

    @Test
    public void testPermissionsAreImmutable() {
        Set<String> permissions = Utility.hashSet("go to Jail", "do not pass Go");
        AccessToken accessToken = new AccessToken(
                "some token",
                "1234",
                "1000",
                permissions,
                null,
                AccessTokenSource.FACEBOOK_APPLICATION_WEB,
                new Date(),
                new Date());

        permissions = accessToken.getPermissions();

        try {
            permissions.add("can't touch this");
            fail();
        } catch (UnsupportedOperationException ex) {
        }
    }

    @Test
    public void testCreateFromExistingTokenDefaults() {
        final String token = "A token of my esteem";
        final String applicationId = "1234";
        final String userId = "1000";

        AccessToken accessToken = new AccessToken(
                token,
                applicationId,
                userId,
                null,
                null,
                null,
                null,
                null);

        assertEquals(token, accessToken.getToken());
        assertEquals(new Date(Long.MAX_VALUE), accessToken.getExpires());
        assertEquals(AccessTokenSource.FACEBOOK_APPLICATION_WEB, accessToken.getSource());
        assertEquals(0, accessToken.getPermissions().size());
        assertEquals(applicationId, accessToken.getApplicationId());
        assertEquals(userId, accessToken.getUserId());
        // Allow slight variation for test execution time
        long delta = accessToken.getLastRefresh().getTime() - new Date().getTime();
        assertTrue(delta < 1000);
    }

    @Test
    public void testAccessTokenConstructor() {
        final String token = "A token of my esteem";
        final Set<String> permissions = Utility.hashSet("walk", "chew gum");
        final Set<String> declinedPermissions = Utility.hashSet("jump");
        final Date expires = new Date(2025, 5, 3);
        final Date lastRefresh = new Date(2023, 8, 15);
        final AccessTokenSource source = AccessTokenSource.WEB_VIEW;
        final String applicationId = "1234";
        final String userId = "1000";

        AccessToken accessToken = new AccessToken(
                token,
                applicationId,
                userId,
                permissions,
                declinedPermissions,
                source,
                expires,
                lastRefresh);

        assertEquals(token, accessToken.getToken());
        assertEquals(expires, accessToken.getExpires());
        assertEquals(lastRefresh, accessToken.getLastRefresh());
        assertEquals(source, accessToken.getSource());
        assertEquals(permissions, accessToken.getPermissions());
        assertEquals(declinedPermissions, accessToken.getDeclinedPermissions());
        assertEquals(applicationId, accessToken.getApplicationId());
        assertEquals(userId, accessToken.getUserId());
    }
}


File: facebook/junitTests/src/test/java/com/facebook/AccessTokenTrackerTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook;

import android.content.Intent;
import android.support.v4.content.LocalBroadcastManager;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.powermock.core.classloader.annotations.PrepareForTest;
import org.robolectric.Robolectric;

import java.util.Arrays;
import java.util.Date;
import java.util.List;

import static org.junit.Assert.*;
import static org.powermock.api.mockito.PowerMockito.*;

@PrepareForTest( { FacebookSdk.class })
public class AccessTokenTrackerTest extends FacebookPowerMockTestCase {

    private final List<String> PERMISSIONS = Arrays.asList("walk", "chew gum");
    private final Date EXPIRES = new Date(2025, 5, 3);
    private final Date LAST_REFRESH = new Date(2023, 8, 15);
    private final String APP_ID = "1234";
    private final String USER_ID = "1000";

    private LocalBroadcastManager localBroadcastManager;
    private TestAccessTokenTracker accessTokenTracker = null;

    @Before
    public void before() throws Exception {
        mockStatic(FacebookSdk.class);
        when(FacebookSdk.isInitialized()).thenReturn(true);
        when(FacebookSdk.getApplicationContext()).thenReturn(Robolectric.application);

        localBroadcastManager = LocalBroadcastManager.getInstance(Robolectric.application);
    }

    @After
    public void after() throws Exception {
        if (accessTokenTracker != null && accessTokenTracker.isTracking()) {
            accessTokenTracker.stopTracking();
        }
    }

    @Test
    public void testRequiresSdkToBeInitialized() {
        try {
            when(FacebookSdk.isInitialized()).thenReturn(false);

            accessTokenTracker = new TestAccessTokenTracker();

            fail();
        } catch (FacebookSdkNotInitializedException exception) {
        }
    }

    @Test
    public void testDefaultsToTracking() {
        accessTokenTracker = new TestAccessTokenTracker();

        assertTrue(accessTokenTracker.isTracking());
    }

    @Test
    public void testCanTurnTrackingOff() {
        accessTokenTracker = new TestAccessTokenTracker();

        accessTokenTracker.stopTracking();

        assertFalse(accessTokenTracker.isTracking());
    }

    @Test
    public void testCanTurnTrackingOn() {
        accessTokenTracker = new TestAccessTokenTracker();

        accessTokenTracker.stopTracking();
        accessTokenTracker.startTracking();

        assertTrue(accessTokenTracker.isTracking());
    }

    @Test
    public void testCallbackCalledOnBroadcastReceived() throws Exception {
        accessTokenTracker = new TestAccessTokenTracker();

        AccessToken oldAccessToken = createAccessToken("I'm old!");
        AccessToken currentAccessToken = createAccessToken("I'm current!");

        sendBroadcast(oldAccessToken, currentAccessToken);


        assertNotNull(accessTokenTracker.currentAccessToken);
        assertEquals(currentAccessToken.getToken(), accessTokenTracker.currentAccessToken.getToken());
        assertNotNull(accessTokenTracker.oldAccessToken);
        assertEquals(oldAccessToken.getToken(), accessTokenTracker.oldAccessToken.getToken());
    }

    private AccessToken createAccessToken(String tokenString) {
        return new AccessToken(
                tokenString,
                APP_ID,
                USER_ID,
                PERMISSIONS,
                null,
                AccessTokenSource.WEB_VIEW,
                EXPIRES,
                LAST_REFRESH);
    }

    private void sendBroadcast(AccessToken oldAccessToken, AccessToken currentAccessToken) {
        Intent intent = new Intent(AccessTokenManager.ACTION_CURRENT_ACCESS_TOKEN_CHANGED);

        intent.putExtra(AccessTokenManager.EXTRA_OLD_ACCESS_TOKEN, oldAccessToken);
        intent.putExtra(AccessTokenManager.EXTRA_NEW_ACCESS_TOKEN, currentAccessToken);

        localBroadcastManager.sendBroadcast(intent);
    }

    class TestAccessTokenTracker extends AccessTokenTracker {

        public AccessToken currentAccessToken;
        public AccessToken oldAccessToken;

        public TestAccessTokenTracker() {
            super();
        }

        @Override
        protected void onCurrentAccessTokenChanged(AccessToken oldAccessToken,
            AccessToken currentAccessToken) {
            this.oldAccessToken = oldAccessToken;
            this.currentAccessToken = currentAccessToken;
        }
    }
}


File: facebook/junitTests/src/test/java/com/facebook/FacebookContentProviderTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook;

import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.util.Pair;

import com.facebook.internal.NativeAppCallAttachmentStore;

import org.junit.Before;
import org.junit.Test;
import org.powermock.core.classloader.annotations.PrepareForTest;
import org.robolectric.Robolectric;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import static org.junit.Assert.*;
import static org.powermock.api.mockito.PowerMockito.mockStatic;
import static org.powermock.api.mockito.PowerMockito.when;

@PrepareForTest({ NativeAppCallAttachmentStore.class })
public class FacebookContentProviderTest extends FacebookPowerMockTestCase {
    private static final String APP_ID = "12345";
    private static final UUID CALL_ID = UUID.randomUUID();
    private static final String ATTACHMENT_NAME = "attachMe";

    private FacebookContentProvider providerUnderTest;

    @Before
    public void before() throws Exception {
        mockStatic(NativeAppCallAttachmentStore.class);
        providerUnderTest = new FacebookContentProvider();
    }

    @Test
    public void testGetAttachmentUrl() {
        String url = FacebookContentProvider.getAttachmentUrl(APP_ID, CALL_ID, ATTACHMENT_NAME);
        assertEquals("content://com.facebook.app.FacebookContentProvider" +
                APP_ID + "/" + CALL_ID + "/" + ATTACHMENT_NAME, url);
    }

    @Test
    public void testOnCreate() throws Exception {
        assertTrue(providerUnderTest.onCreate());
    }

    @Test
    public void testQuery() throws Exception {
        assertNull(providerUnderTest.query(null, null, null, null, null));
    }

    @Test
    public void testGetType() throws Exception {
        assertNull(providerUnderTest.getType(null));
    }

    @Test
    public void testInsert() throws Exception {
        assertNull(providerUnderTest.insert(null, null));
    }

    @Test
    public void testDelete() throws Exception {
        assertEquals(0, providerUnderTest.delete(null, null, null));
    }

    @Test
    public void testUpdate() throws Exception {
        assertEquals(0, providerUnderTest.update(null, null, null, null));
    }

    @SuppressWarnings("unused")
    @Test
    public void testOpenFileWithNullUri() throws Exception {
        try {
            ParcelFileDescriptor pfd = providerUnderTest.openFile(null, "r");
            fail("expected FileNotFoundException");
        } catch (FileNotFoundException e) {
        }
    }

    @SuppressWarnings("unused")
    @Test
    public void testOpenFileWithBadPath() throws Exception {
        try {
            ParcelFileDescriptor pfd = providerUnderTest.openFile(Uri.parse("/"), "r");
            fail("expected FileNotFoundException");
        } catch (FileNotFoundException e) {
        }
    }

    @SuppressWarnings("unused")
    @Test
    public void testOpenFileWithoutCallIdAndAttachment() throws Exception {
        try {
            ParcelFileDescriptor pfd = providerUnderTest.openFile(Uri.parse("/foo"), "r");
            fail("expected FileNotFoundException");
        } catch (FileNotFoundException e) {
        }
    }

    @SuppressWarnings("unused")
    @Test
    public void testOpenFileWithBadCallID() throws Exception {
        try {
            ParcelFileDescriptor pfd = providerUnderTest.openFile(Uri.parse("/foo/bar"), "r");
            fail("expected FileNotFoundException");
        } catch (FileNotFoundException e) {
        }
    }

    @Test
    public void testOpenFileWithUnknownUri() throws Exception {
        try {
            ParcelFileDescriptor pfd = getTestAttachmentParcelFileDescriptor(UUID.randomUUID());
            assertNotNull(pfd);
            pfd.close();

            fail("expected FileNotFoundException");
        } catch (FileNotFoundException e) {
        }
    }

    @Test
    public void testOpenFileWithKnownUri() throws Exception {
        MockAttachmentStore.addAttachment(CALL_ID, ATTACHMENT_NAME);

        ParcelFileDescriptor pfd = getTestAttachmentParcelFileDescriptor(CALL_ID);
        assertNotNull(pfd);
        pfd.close();
    }

    private ParcelFileDescriptor getTestAttachmentParcelFileDescriptor(UUID callId)
            throws Exception {
        when(NativeAppCallAttachmentStore.openAttachment(callId, ATTACHMENT_NAME))
                .thenReturn(MockAttachmentStore.openAttachment(callId, ATTACHMENT_NAME));

        Uri uri = Uri.parse(
                FacebookContentProvider.getAttachmentUrl(APP_ID, callId, ATTACHMENT_NAME));

        return providerUnderTest.openFile(uri, "r");
    }

    static class MockAttachmentStore {
        private static List<Pair<UUID, String>> attachments = new ArrayList<>();
        private static final String DUMMY_FILE_NAME = "dummyfile";

        public static void addAttachment(UUID callId, String attachmentName) {
            attachments.add(new Pair<>(callId, attachmentName));
        }

        public static File openAttachment(UUID callId, String attachmentName)
                throws FileNotFoundException {
            if (attachments.contains(new Pair<>(callId, attachmentName))) {
                File cacheDir = Robolectric.application.getCacheDir();
                File dummyFile = new File(cacheDir, DUMMY_FILE_NAME);
                if (!dummyFile.exists()) {
                    try {
                        dummyFile.createNewFile();
                    } catch (IOException e) {
                    }
                }

                return dummyFile;
            }

            throw new FileNotFoundException();
        }
    }
}


File: facebook/junitTests/src/test/java/com/facebook/FacebookGraphRequestErrorTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook;

import com.facebook.junittests.R;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.junit.Test;

import static org.junit.Assert.*;

public class FacebookGraphRequestErrorTest extends FacebookTestCase {
    public static final String ERROR_SINGLE_RESPONSE =
            "{\n" +
            "  \"error\": {\n" +
            "    \"message\": \"Unknown path components: /unknown\",\n" +
            "    \"type\": \"OAuthException\",\n" +
            "    \"code\": 2500\n" +
            "  }\n" +
            "}";

    public static final String ERROR_BATCH_RESPONSE =
            "[\n" +
            "  {\n" +
            "    \"headers\": [\n" +
            "      {\n" +
            "        \"value\": \"*\",\n" +
            "        \"name\": \"Access-Control-Allow-Origin\"\n" +
            "      },\n" +
            "      {\n" +
            "        \"value\": \"no-store\",\n" +
            "        \"name\": \"Cache-Control\"\n" +
            "      },\n" +
            "      {\n" +
            "        \"value\": \"close\",\n" +
            "        \"name\": \"Connection\"\n" +
            "      },\n" +
            "      {\n" +
            "        \"value\": \"text\\/javascript; charset=UTF-8\",\n" +
            "        \"name\": \"Content-Type\"\n" +
            "      },\n" +
            "      {\n" +
            "        \"value\": \"Sat, 01 Jan 2000 00:00:00 GMT\",\n" +
            "        \"name\": \"Expires\"\n" +
            "      },\n" +
            "      {\n" +
            "        \"value\": \"no-cache\",\n" +
            "        \"name\": \"Pragma\"\n" +
            "      },\n" +
            "      {\n" +
            "        \"value\": \"OAuth \\\"Facebook Platform\\\" \\\"invalid_request\\\" \\\"An active access token must be used to query information about the current user.\\\"\",\n" +
            "        \"name\": \"WWW-Authenticate\"\n" +
            "      }\n" +
            "    ],\n" +
            "    \"body\": \"{\\\"error\\\":{\\\"message\\\":\\\"An active access token must be used to query information about the current user.\\\",\\\"type\\\":\\\"OAuthException\\\",\\\"code\\\":2500}}\",\n" +
            "    \"code\": 400\n" +
            "  },\n" +
            "  {\n" +
            "    \"headers\": [\n" +
            "      {\n" +
            "        \"value\": \"*\",\n" +
            "        \"name\": \"Access-Control-Allow-Origin\"\n" +
            "      },\n" +
            "      {\n" +
            "        \"value\": \"no-store\",\n" +
            "        \"name\": \"Cache-Control\"\n" +
            "      },\n" +
            "      {\n" +
            "        \"value\": \"close\",\n" +
            "        \"name\": \"Connection\"\n" +
            "      },\n" +
            "      {\n" +
            "        \"value\": \"text\\/javascript; charset=UTF-8\",\n" +
            "        \"name\": \"Content-Type\"\n" +
            "      },\n" +
            "      {\n" +
            "        \"value\": \"Sat, 01 Jan 2000 00:00:00 GMT\",\n" +
            "        \"name\": \"Expires\"\n" +
            "      },\n" +
            "      {\n" +
            "        \"value\": \"no-cache\",\n" +
            "        \"name\": \"Pragma\"\n" +
            "      },\n" +
            "      {\n" +
            "        \"value\": \"OAuth \\\"Facebook Platform\\\" \\\"invalid_request\\\" \\\"An active access token must be used to query information about the current user.\\\"\",\n" +
            "        \"name\": \"WWW-Authenticate\"\n" +
            "      }\n" +
            "    ],\n" +
            "    \"body\": \"{\\\"error\\\":{\\\"message\\\":\\\"An active access token must be used to query information about the current user.\\\",\\\"type\\\":\\\"OAuthException\\\",\\\"code\\\":2500}}\",\n" +
            "    \"code\": 400\n" +
            "  }\n" +
            "]";


    public static final String ERROR_SINGLE_RESPONSE_THROTTLE =
            "{\n" +
            "  \"error\": {\n" +
            "    \"message\": \"Application request limit reached\",\n" +
            "    \"code\": 4\n" +
            "  }\n" +
            "}";

    public static final String ERROR_SINGLE_RESPONSE_SERVER =
            "{\n" +
            "  \"error\": {\n" +
            "    \"message\": \"Some Server Error\",\n" +
            "    \"code\": 2\n" +
            "  }\n" +
            "}";

    public static final String ERROR_SINGLE_RESPONSE_PERMISSION =
            "{\n" +
            "  \"error\": {\n" +
            "    \"type\": \"OAuthException\",\n" +
            "    \"message\": \"(#200) Requires extended permission: publish_actions\",\n" +
            "    \"code\": 200\n" +
            "  }\n" +
            "}";

    public static final String ERROR_SINGLE_RESPONSE_WEB_LOGIN =
            "{\n" +
            "  \"error\": {\n" +
            "    \"message\": \"User need to login\",\n" +
            "    \"type\": \"OAuthException\",\n" +
            "    \"code\": 102,\n" +
            "    \"error_subcode\": 459\n" +
            "  }\n" +
            "}";

    public static final String ERROR_SINGLE_RESPONSE_RELOGIN =
            "{\n" +
            "  \"error\": {\n" +
            "    \"message\": \"User need to relogin\",\n" +
            "    \"type\": \"OAuthException\",\n" +
            "    \"code\": 102\n" +
            "  }\n" +
            "}";

    public static final String ERROR_SINGLE_RESPONSE_RELOGIN_DELETED_APP =
            "{\n" +
            "  \"error\": {\n" +
            "    \"message\": \"User need to relogin\",\n" +
            "    \"type\": \"OAuthException\",\n" +
            "    \"code\": 190,\n" +
            "    \"error_subcode\": 458\n" +
            "  }\n" +
            "}";

    @Test
    public void testClientException() {
        final String errorMsg = "some error happened";
        FacebookRequestError error =
                new FacebookRequestError(null, new FacebookException(errorMsg));
        assertEquals(errorMsg, error.getErrorMessage());
        assertEquals(FacebookRequestError.Category.OTHER, error.getCategory());
        assertEquals(FacebookRequestError.INVALID_ERROR_CODE, error.getErrorCode());
        assertEquals(FacebookRequestError.INVALID_HTTP_STATUS_CODE, error.getRequestStatusCode());
    }

    @Test
    public void testSingleRequestWithoutBody() throws JSONException {
        JSONObject withStatusCode = new JSONObject();
        withStatusCode.put("code", 400);
        FacebookRequestError error =
                FacebookRequestError.checkResponseAndCreateError(
                        withStatusCode, withStatusCode, null);
        assertNotNull(error);
        assertEquals(400, error.getRequestStatusCode());
        assertEquals(FacebookRequestError.Category.OTHER, error.getCategory());
    }

    @Test
    public void testSingleErrorWithBody() throws JSONException {
        JSONObject originalResponse = new JSONObject(ERROR_SINGLE_RESPONSE);
        JSONObject withStatusCodeAndBody = new JSONObject();
        withStatusCodeAndBody.put("code", 400);
        withStatusCodeAndBody.put("body", originalResponse);
        FacebookRequestError error =
                FacebookRequestError.checkResponseAndCreateError(
                        withStatusCodeAndBody, originalResponse, null);
        assertNotNull(error);
        assertEquals(400, error.getRequestStatusCode());
        assertEquals("Unknown path components: /unknown", error.getErrorMessage());
        assertEquals("OAuthException", error.getErrorType());
        assertEquals(2500, error.getErrorCode());
        assertTrue(error.getBatchRequestResult() instanceof JSONObject);
        assertEquals(FacebookRequestError.Category.OTHER, error.getCategory());
    }

    @Test
    public void testBatchRequest() throws JSONException {
        JSONArray batchResponse = new JSONArray(ERROR_BATCH_RESPONSE);
        assertEquals(2, batchResponse.length());
        JSONObject firstResponse = (JSONObject) batchResponse.get(0);
        FacebookRequestError error =
                FacebookRequestError.checkResponseAndCreateError(
                        firstResponse, batchResponse, null);
        assertNotNull(error);
        assertEquals(400, error.getRequestStatusCode());
        assertEquals("An active access token must be used to query information about the current user.",
                error.getErrorMessage());
        assertEquals("OAuthException", error.getErrorType());
        assertEquals(2500, error.getErrorCode());
        assertTrue(error.getBatchRequestResult() instanceof  JSONArray);
        assertEquals(FacebookRequestError.Category.OTHER, error.getCategory());
    }

    @Test
    public void testSingleThrottledError() throws JSONException {
        JSONObject originalResponse = new JSONObject(ERROR_SINGLE_RESPONSE_THROTTLE);
        JSONObject withStatusCodeAndBody = new JSONObject();
        withStatusCodeAndBody.put("code", 403);
        withStatusCodeAndBody.put("body", originalResponse);
        FacebookRequestError error =
                FacebookRequestError.checkResponseAndCreateError(
                        withStatusCodeAndBody, originalResponse, null);
        assertNotNull(error);
        assertEquals(403, error.getRequestStatusCode());
        assertEquals("Application request limit reached", error.getErrorMessage());
        assertNull(error.getErrorType());
        assertEquals(4, error.getErrorCode());
        assertTrue(error.getBatchRequestResult() instanceof JSONObject);
        assertEquals(FacebookRequestError.Category.TRANSIENT, error.getCategory());
    }

    @Test
    public void testSingleServerError() throws JSONException {
        JSONObject originalResponse = new JSONObject(ERROR_SINGLE_RESPONSE_SERVER);
        JSONObject withStatusCodeAndBody = new JSONObject();
        withStatusCodeAndBody.put("code", 500);
        withStatusCodeAndBody.put("body", originalResponse);
        FacebookRequestError error =
                FacebookRequestError.checkResponseAndCreateError(
                        withStatusCodeAndBody, originalResponse, null);
        assertNotNull(error);
        assertEquals(500, error.getRequestStatusCode());
        assertEquals("Some Server Error", error.getErrorMessage());
        assertNull(error.getErrorType());
        assertEquals(2, error.getErrorCode());
        assertTrue(error.getBatchRequestResult() instanceof JSONObject);
        assertEquals(FacebookRequestError.Category.TRANSIENT, error.getCategory());
    }

    @Test
    public void testSinglePermissionError() throws JSONException {
        JSONObject originalResponse = new JSONObject(ERROR_SINGLE_RESPONSE_PERMISSION);
        JSONObject withStatusCodeAndBody = new JSONObject();
        withStatusCodeAndBody.put("code", 400);
        withStatusCodeAndBody.put("body", originalResponse);
        FacebookRequestError error =
                FacebookRequestError.checkResponseAndCreateError(
                        withStatusCodeAndBody, originalResponse, null);
        assertNotNull(error);
        assertEquals(400, error.getRequestStatusCode());
        assertEquals(
                "(#200) Requires extended permission: publish_actions",
                error.getErrorMessage());
        assertEquals("OAuthException", error.getErrorType());
        assertEquals(200, error.getErrorCode());
        assertEquals(FacebookRequestError.INVALID_ERROR_CODE, error.getSubErrorCode());
        assertTrue(error.getBatchRequestResult() instanceof JSONObject);
        assertEquals(FacebookRequestError.Category.OTHER, error.getCategory());
    }

    @Test
    public void testSingleWebLoginError() throws JSONException {
        JSONObject originalResponse = new JSONObject(ERROR_SINGLE_RESPONSE_WEB_LOGIN);
        JSONObject withStatusCodeAndBody = new JSONObject();
        withStatusCodeAndBody.put("code", 400);
        withStatusCodeAndBody.put("body", originalResponse);
        FacebookRequestError error =
                FacebookRequestError.checkResponseAndCreateError(
                        withStatusCodeAndBody, originalResponse, null);
        assertNotNull(error);
        assertEquals(400, error.getRequestStatusCode());
        assertEquals("User need to login", error.getErrorMessage());
        assertEquals("OAuthException", error.getErrorType());
        assertEquals(102, error.getErrorCode());
        assertEquals(459, error.getSubErrorCode());
        assertTrue(error.getBatchRequestResult() instanceof JSONObject);
        assertEquals(FacebookRequestError.Category.LOGIN_RECOVERABLE, error.getCategory());
    }

    @Test
    public void testSingleReloginError() throws JSONException {
        JSONObject originalResponse = new JSONObject(ERROR_SINGLE_RESPONSE_RELOGIN);
        JSONObject withStatusCodeAndBody = new JSONObject();
        withStatusCodeAndBody.put("code", 400);
        withStatusCodeAndBody.put("body", originalResponse);
        FacebookRequestError error =
                FacebookRequestError.checkResponseAndCreateError(
                        withStatusCodeAndBody, originalResponse, null);
        assertNotNull(error);
        assertEquals(400, error.getRequestStatusCode());
        assertEquals("User need to relogin", error.getErrorMessage());
        assertEquals("OAuthException", error.getErrorType());
        assertEquals(102, error.getErrorCode());
        assertEquals(FacebookRequestError.INVALID_ERROR_CODE, error.getSubErrorCode());
        assertTrue(error.getBatchRequestResult() instanceof JSONObject);
        assertEquals(FacebookRequestError.Category.LOGIN_RECOVERABLE, error.getCategory());
    }

    @Test
    public void testSingleReloginDeletedAppError() throws JSONException {
        JSONObject originalResponse = new JSONObject(ERROR_SINGLE_RESPONSE_RELOGIN_DELETED_APP);
        JSONObject withStatusCodeAndBody = new JSONObject();
        withStatusCodeAndBody.put("code", 400);
        withStatusCodeAndBody.put("body", originalResponse);
        FacebookRequestError error =
                FacebookRequestError.checkResponseAndCreateError(
                        withStatusCodeAndBody, originalResponse, null);
        assertNotNull(error);
        assertEquals(400, error.getRequestStatusCode());
        assertEquals("User need to relogin", error.getErrorMessage());
        assertEquals("OAuthException", error.getErrorType());
        assertEquals(190, error.getErrorCode());
        assertEquals(458, error.getSubErrorCode());
        assertTrue(error.getBatchRequestResult() instanceof JSONObject);
        assertEquals(FacebookRequestError.Category.LOGIN_RECOVERABLE, error.getCategory());
    }
}


File: facebook/junitTests/src/test/java/com/facebook/FacebookSdkPowerMockTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook;

import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.os.ConditionVariable;

import com.facebook.internal.CallbackManagerImpl;
import com.facebook.internal.ServerProtocol;
import com.facebook.internal.Utility;

import org.junit.Before;
import org.junit.Test;
import org.powermock.core.classloader.annotations.PrepareForTest;
import org.powermock.reflect.Whitebox;
import org.robolectric.Robolectric;

import java.util.concurrent.Executor;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.powermock.api.support.membermodification.MemberMatcher.method;
import static org.powermock.api.support.membermodification.MemberModifier.stub;

@PrepareForTest({ FacebookSdk.class, Utility.class })
public final class FacebookSdkPowerMockTest extends FacebookPowerMockTestCase {

    @Before
    public void before() {
        Whitebox.setInternalState(FacebookSdk.class, "callbackRequestCodeOffset", 0xface);
        Whitebox.setInternalState(FacebookSdk.class, "sdkInitialized", false);
        stub(method(Utility.class, "loadAppSettingsAsync")).toReturn(null);

    }

    @Test
    public void testGetExecutor() {
        final ConditionVariable condition = new ConditionVariable();

        FacebookSdk.getExecutor().execute(new Runnable() {
            @Override
            public void run() {
                condition.open();
            }
        });

        boolean success = condition.block(5000);
        assertTrue(success);
    }

    @Test
    public void testSetExecutor() {
        final ConditionVariable condition = new ConditionVariable();

        final Runnable runnable = new Runnable() {
            @Override
            public void run() { }
        };

        final Executor executor = new Executor() {
            @Override
            public void execute(Runnable command) {
                assertEquals(runnable, command);
                command.run();

                condition.open();
            }
        };

        Executor original = FacebookSdk.getExecutor();
        try {
            FacebookSdk.setExecutor(executor);
            FacebookSdk.getExecutor().execute(runnable);

            boolean success = condition.block(5000);
            assertTrue(success);
        } finally {
            FacebookSdk.setExecutor(original);
        }
    }

    @Test
    public void testFacebookDomain() {
        FacebookSdk.setFacebookDomain("beta.facebook.com");

        String graphUrlBase = ServerProtocol.getGraphUrlBase();
        assertEquals("https://graph.beta.facebook.com", graphUrlBase);

        FacebookSdk.setFacebookDomain("facebook.com");
    }

    @Test
    public void testLoadDefaults() throws Exception {
        stub(method(FacebookSdk.class, "isInitialized")).toReturn(true);
        FacebookSdk.loadDefaultsFromMetadata(mockContextWithAppIdAndClientToken());

        assertEquals("1234", FacebookSdk.getApplicationId());
        assertEquals("abcd", FacebookSdk.getClientToken());
    }


    private Context mockContextWithAppIdAndClientToken() throws Exception {
        Bundle bundle = mock(Bundle.class);

        when(bundle.get(FacebookSdk.APPLICATION_ID_PROPERTY)).thenReturn("1234");
        when(bundle.getString(FacebookSdk.CLIENT_TOKEN_PROPERTY)).thenReturn("abcd");
        ApplicationInfo applicationInfo = mock(ApplicationInfo.class);
        applicationInfo.metaData = bundle;

        PackageManager packageManager = mock(PackageManager.class);
        when(packageManager.getApplicationInfo("packageName", PackageManager.GET_META_DATA))
                .thenReturn(applicationInfo);

        Context context = mock(Context.class);
        when(context.getPackageName()).thenReturn("packageName");
        when(context.getPackageManager()).thenReturn(packageManager);
        return context;
    }

    @Test
    public void testLoadDefaultsDoesNotOverwrite() throws Exception {
        stub(method(FacebookSdk.class, "isInitialized")).toReturn(true);
        FacebookSdk.setApplicationId("hello");
        FacebookSdk.setClientToken("world");

        FacebookSdk.loadDefaultsFromMetadata(mockContextWithAppIdAndClientToken());

        assertEquals("hello", FacebookSdk.getApplicationId());
        assertEquals("world", FacebookSdk.getClientToken());
    }

    @Test
    public void testRequestCodeOffsetAfterInit() throws Exception {
        FacebookSdk.sdkInitialize(Robolectric.application);

        try {
            FacebookSdk.sdkInitialize(Robolectric.application, 1000);
            fail();
        } catch (FacebookException exception) {
            assertEquals(FacebookSdk.CALLBACK_OFFSET_CHANGED_AFTER_INIT, exception.getMessage());
        }
    }

    @Test
    public void testRequestCodeOffsetNegative() throws Exception {
        try {
            // last bit set, so negative
            FacebookSdk.sdkInitialize(Robolectric.application, 0xFACEB00C);
            fail();
        } catch (FacebookException exception) {
            assertEquals(FacebookSdk.CALLBACK_OFFSET_NEGATIVE, exception.getMessage());
        }
    }

    @Test
    public void testRequestCodeOffset() throws Exception {
        FacebookSdk.sdkInitialize(Robolectric.application, 1000);
        assertEquals(1000, FacebookSdk.getCallbackRequestCodeOffset());
    }

    @Test
    public void testRequestCodeRange() {
        FacebookSdk.sdkInitialize(Robolectric.application, 1000);
        assertTrue(FacebookSdk.isFacebookRequestCode(1000));
        assertTrue(FacebookSdk.isFacebookRequestCode(1099));
        assertFalse(FacebookSdk.isFacebookRequestCode(999));
        assertFalse(FacebookSdk.isFacebookRequestCode(1100));
        assertFalse(FacebookSdk.isFacebookRequestCode(0));
    }
}


File: facebook/junitTests/src/test/java/com/facebook/GraphErrorTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook;

import com.facebook.internal.FacebookRequestErrorClassification;
import com.facebook.internal.Utility;

import org.json.JSONException;
import org.json.JSONObject;
import org.junit.Before;
import org.junit.Test;
import org.powermock.api.mockito.PowerMockito;
import org.powermock.core.classloader.annotations.PrepareForTest;
import org.robolectric.Robolectric;

import java.io.IOException;
import java.net.HttpURLConnection;

import static org.junit.Assert.*;
import static org.powermock.api.mockito.PowerMockito.doNothing;
import static org.powermock.api.mockito.PowerMockito.mock;
import static org.powermock.api.mockito.PowerMockito.mockStatic;
import static org.powermock.api.mockito.PowerMockito.when;
import static org.powermock.api.support.membermodification.MemberMatcher.method;
import static org.powermock.api.support.membermodification.MemberModifier.stub;
import static org.powermock.api.support.membermodification.MemberModifier.suppress;

@PrepareForTest( {
        AccessToken.class,
        AccessTokenCache.class,
        FacebookSdk.class,
        GraphRequest.class,
        Utility.class
})
public final class GraphErrorTest extends FacebookPowerMockTestCase {

    @Before
    public void before() throws Exception {
        mockStatic(FacebookSdk.class);
        suppress(method(Utility.class, "clearFacebookCookies"));
        when(FacebookSdk.isInitialized()).thenReturn(true);
        when(FacebookSdk.getApplicationContext()).thenReturn(Robolectric.application);
        stub(method(AccessTokenCache.class, "save")).toReturn(null);
    }

    @Test
    public void testAccessTokenResetOnTokenError() throws JSONException, IOException {
        AccessToken accessToken = mock(AccessToken.class);
        AccessToken.setCurrentAccessToken(accessToken);

        JSONObject errorBody = new JSONObject();
        errorBody.put("message", "Invalid OAuth access token.");
        errorBody.put("type", "OAuthException");
        errorBody.put("code", FacebookRequestErrorClassification.EC_INVALID_TOKEN);
        JSONObject error = new JSONObject();
        error.put("error", errorBody);
        String errorString = error.toString();

        HttpURLConnection connection = mock(HttpURLConnection.class);
        when(connection.getResponseCode()).thenReturn(400);

        GraphRequest request = mock(GraphRequest.class);
        when(request.getAccessToken()).thenReturn(accessToken);
        GraphRequestBatch batch = new GraphRequestBatch(request);

        assertNotNull(AccessToken.getCurrentAccessToken());
        GraphResponse.createResponsesFromString(errorString, connection, batch);
        assertNull(AccessToken.getCurrentAccessToken());
    }
}


File: facebook/junitTests/src/test/java/com/facebook/LegacyTokenCacheTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook;

import android.os.Bundle;

import com.facebook.internal.Utility;

import org.json.JSONObject;
import org.junit.Before;
import org.junit.Test;
import org.powermock.api.mockito.PowerMockito;
import org.powermock.core.classloader.annotations.PrepareForTest;
import org.robolectric.Robolectric;

import java.lang.reflect.Array;
import java.util.ArrayList;
import java.util.Date;
import java.util.Iterator;
import java.util.List;
import java.util.Random;
import java.util.Set;

import static org.junit.Assert.*;
import static org.powermock.api.support.membermodification.MemberModifier.stub;

@PrepareForTest( {Utility.class})
public final class LegacyTokenCacheTest extends FacebookPowerMockTestCase {

    private static final String BOOLEAN_KEY = "booleanKey";
    private static final String BOOLEAN_ARRAY_KEY = "booleanArrayKey";
    private static final String BYTE_KEY = "byteKey";
    private static final String BYTE_ARRAY_KEY = "byteArrayKey";
    private static final String SHORT_KEY = "shortKey";
    private static final String SHORT_ARRAY_KEY = "shortArrayKey";
    private static final String INT_KEY = "intKey";
    private static final String INT_ARRAY_KEY = "intArrayKey";
    private static final String LONG_KEY = "longKey";
    private static final String LONG_ARRAY_KEY = "longArrayKey";
    private static final String FLOAT_ARRAY_KEY = "floatKey";
    private static final String FLOAT_KEY = "floatArrayKey";
    private static final String DOUBLE_KEY = "doubleKey";
    private static final String DOUBLE_ARRAY_KEY = "doubleArrayKey";
    private static final String CHAR_KEY = "charKey";
    private static final String CHAR_ARRAY_KEY = "charArrayKey";
    private static final String STRING_KEY = "stringKey";
    private static final String STRING_LIST_KEY = "stringListKey";
    private static final String SERIALIZABLE_KEY = "serializableKey";

    private static Random random = new Random((new Date()).getTime());

    @Override
    public void setUp() {
        super.setUp();

        FacebookSdk.sdkInitialize(Robolectric.application);
    }

    @Before
    public void before() throws Exception {
        stub(PowerMockito.method(Utility.class, "awaitGetGraphMeRequestWithCache")).toReturn(
                new JSONObject().put("id", "1000"));
    }

    @Test
    public void testAllTypes() {
        Bundle originalBundle = new Bundle();

        putBoolean(BOOLEAN_KEY, originalBundle);
        putBooleanArray(BOOLEAN_ARRAY_KEY, originalBundle);
        putByte(BYTE_KEY, originalBundle);
        putByteArray(BYTE_ARRAY_KEY, originalBundle);
        putShort(SHORT_KEY, originalBundle);
        putShortArray(SHORT_ARRAY_KEY, originalBundle);
        putInt(INT_KEY, originalBundle);
        putIntArray(INT_ARRAY_KEY, originalBundle);
        putLong(LONG_KEY, originalBundle);
        putLongArray(LONG_ARRAY_KEY, originalBundle);
        putFloat(FLOAT_KEY, originalBundle);
        putFloatArray(FLOAT_ARRAY_KEY, originalBundle);
        putDouble(DOUBLE_KEY, originalBundle);
        putDoubleArray(DOUBLE_ARRAY_KEY, originalBundle);
        putChar(CHAR_KEY, originalBundle);
        putCharArray(CHAR_ARRAY_KEY, originalBundle);
        putString(STRING_KEY, originalBundle);
        putStringList(STRING_LIST_KEY, originalBundle);
        originalBundle.putSerializable(SERIALIZABLE_KEY, AccessTokenSource.FACEBOOK_APPLICATION_WEB);

        ensureApplicationContext();

        LegacyTokenHelper cache = new LegacyTokenHelper(Robolectric.application);
        cache.save(originalBundle);

        LegacyTokenHelper cache2 = new LegacyTokenHelper(Robolectric.application);
        Bundle cachedBundle = cache2.load();

        assertEquals(originalBundle.getBoolean(BOOLEAN_KEY), cachedBundle.getBoolean(BOOLEAN_KEY));
        assertArrayEquals(originalBundle.getBooleanArray(BOOLEAN_ARRAY_KEY), cachedBundle.getBooleanArray(BOOLEAN_ARRAY_KEY));
        assertEquals(originalBundle.getByte(BYTE_KEY), cachedBundle.getByte(BYTE_KEY));
        assertArrayEquals(originalBundle.getByteArray(BYTE_ARRAY_KEY), cachedBundle.getByteArray(BYTE_ARRAY_KEY));
        assertEquals(originalBundle.getShort(SHORT_KEY), cachedBundle.getShort(SHORT_KEY));
        assertArrayEquals(originalBundle.getShortArray(SHORT_ARRAY_KEY), cachedBundle.getShortArray(SHORT_ARRAY_KEY));
        assertEquals(originalBundle.getInt(INT_KEY), cachedBundle.getInt(INT_KEY));
        assertArrayEquals(originalBundle.getIntArray(INT_ARRAY_KEY), cachedBundle.getIntArray(INT_ARRAY_KEY));
        assertEquals(originalBundle.getLong(LONG_KEY), cachedBundle.getLong(LONG_KEY));
        assertArrayEquals(originalBundle.getLongArray(LONG_ARRAY_KEY), cachedBundle.getLongArray(LONG_ARRAY_KEY));
        assertEquals(originalBundle.getFloat(FLOAT_KEY), cachedBundle.getFloat(FLOAT_KEY), TestUtils.DOUBLE_EQUALS_DELTA);
        assertArrayEquals(originalBundle.getFloatArray(FLOAT_ARRAY_KEY), cachedBundle.getFloatArray(FLOAT_ARRAY_KEY));
        assertEquals(originalBundle.getDouble(DOUBLE_KEY), cachedBundle.getDouble(DOUBLE_KEY), TestUtils.DOUBLE_EQUALS_DELTA);
        assertArrayEquals(originalBundle.getDoubleArray(DOUBLE_ARRAY_KEY), cachedBundle.getDoubleArray(DOUBLE_ARRAY_KEY));
        assertEquals(originalBundle.getChar(CHAR_KEY), cachedBundle.getChar(CHAR_KEY));
        assertArrayEquals(originalBundle.getCharArray(CHAR_ARRAY_KEY), cachedBundle.getCharArray(CHAR_ARRAY_KEY));
        assertEquals(originalBundle.getString(STRING_KEY), cachedBundle.getString(STRING_KEY));
        assertListEquals(originalBundle.getStringArrayList(STRING_LIST_KEY), cachedBundle.getStringArrayList(
                STRING_LIST_KEY));
        assertEquals(originalBundle.getSerializable(SERIALIZABLE_KEY),
                cachedBundle.getSerializable(SERIALIZABLE_KEY));
    }

    @Test
    public void testMultipleCaches() {
        Bundle bundle1 = new Bundle(), bundle2 = new Bundle();

        bundle1.putInt(INT_KEY, 10);
        bundle1.putString(STRING_KEY, "ABC");
        bundle2.putInt(INT_KEY, 100);
        bundle2.putString(STRING_KEY, "xyz");

        ensureApplicationContext();

        LegacyTokenHelper cache1 = new LegacyTokenHelper(Robolectric.application);
        LegacyTokenHelper cache2 = new LegacyTokenHelper(Robolectric.application, "CustomCache");

        cache1.save(bundle1);
        cache2.save(bundle2);

        // Get new references to make sure we are getting persisted data.
        // Reverse the cache references for fun.
        cache1 = new LegacyTokenHelper(Robolectric.application, "CustomCache");
        cache2 = new LegacyTokenHelper(Robolectric.application);

        Bundle newBundle1 = cache1.load(), newBundle2 = cache2.load();

        assertEquals(bundle2.getInt(INT_KEY), newBundle1.getInt(INT_KEY));
        assertEquals(bundle2.getString(STRING_KEY), newBundle1.getString(STRING_KEY));
        assertEquals(bundle1.getInt(INT_KEY), newBundle2.getInt(INT_KEY));
        assertEquals(bundle1.getString(STRING_KEY), newBundle2.getString(STRING_KEY));
    }

    @Test
    public void testCacheRoundtrip() {
        Set<String> permissions = Utility.hashSet("stream_publish", "go_outside_and_play");
        String token = "AnImaginaryTokenValue";
        Date later = TestUtils.nowPlusSeconds(60);
        Date earlier = TestUtils.nowPlusSeconds(-60);
        String applicationId = "1234";

        LegacyTokenHelper cache =
                new LegacyTokenHelper(Robolectric.application);
        cache.clear();

        Bundle bundle = new Bundle();
        LegacyTokenHelper.putToken(bundle, token);
        LegacyTokenHelper.putExpirationDate(bundle, later);
        LegacyTokenHelper.putSource(
                bundle,
                AccessTokenSource.FACEBOOK_APPLICATION_NATIVE);
        LegacyTokenHelper.putLastRefreshDate(bundle, earlier);
        LegacyTokenHelper.putPermissions(bundle, permissions);
        LegacyTokenHelper.putDeclinedPermissions(
                bundle,
                Utility.arrayList("whatever"));
        LegacyTokenHelper.putApplicationId(bundle, applicationId);

        cache.save(bundle);
        bundle = cache.load();

        AccessToken accessToken = AccessToken.createFromLegacyCache(bundle);
        TestUtils.assertSamePermissions(permissions, accessToken);
        assertEquals(token, accessToken.getToken());
        assertEquals(AccessTokenSource.FACEBOOK_APPLICATION_NATIVE, accessToken.getSource());
        assertTrue(!accessToken.isExpired());

        Bundle cachedBundle = AccessTokenTestHelper.toLegacyCacheBundle(accessToken);
        TestUtils.assertEqualContentsWithoutOrder(bundle, cachedBundle);
    }

    private static void assertArrayEquals(Object a1, Object a2) {
        assertNotNull(a1);
        assertNotNull(a2);
        assertEquals(a1.getClass(), a2.getClass());
        assertTrue("Not an array", a1.getClass().isArray());

        int length = Array.getLength(a1);
        assertEquals(length, Array.getLength(a2));
        for (int i = 0; i < length; i++) {
            Object a1Value = Array.get(a1, i);
            Object a2Value = Array.get(a2, i);

            assertEquals(a1Value, a2Value);
        }
    }

    private static void assertListEquals(List<?> l1, List<?> l2) {
        assertNotNull(l1);
        assertNotNull(l2);

        Iterator<?> i1 = l1.iterator(), i2 = l2.iterator();
        while (i1.hasNext() && i2.hasNext()) {
            assertEquals(i1.next(), i2.next());
        }

        assertTrue("Lists not of the same length", !i1.hasNext());
        assertTrue("Lists not of the same length", !i2.hasNext());
    }

    private static void putInt(String key, Bundle bundle) {
        bundle.putInt(key, random.nextInt());
    }

    private static void putIntArray(String key, Bundle bundle) {
        int length = random.nextInt(50);
        int[] array = new int[length];
        for (int i = 0; i < length; i++) {
            array[i] = random.nextInt();
        }
        bundle.putIntArray(key, array);
    }

    private static void putShort(String key, Bundle bundle) {
        bundle.putShort(key, (short)random.nextInt());
    }

    private static void putShortArray(String key, Bundle bundle) {
        int length = random.nextInt(50);
        short[] array = new short[length];
        for (int i = 0; i < length; i++) {
            array[i] = (short)random.nextInt();
        }
        bundle.putShortArray(key, array);
    }

    private static void putByte(String key, Bundle bundle) {
        bundle.putByte(key, (byte)random.nextInt());
    }

    private static void putByteArray(String key, Bundle bundle) {
        int length = random.nextInt(50);
        byte[] array = new byte[length];
        random.nextBytes(array);
        bundle.putByteArray(key, array);
    }

    private static void putBoolean(String key, Bundle bundle) {
        bundle.putBoolean(key, random.nextBoolean());
    }

    private static void putBooleanArray(String key, Bundle bundle) {
        int length = random.nextInt(50);
        boolean[] array = new boolean[length];
        for (int i = 0; i < length; i++) {
            array[i] = random.nextBoolean();
        }
        bundle.putBooleanArray(key, array);
    }

    private static void putLong(String key, Bundle bundle) {
        bundle.putLong(key, random.nextLong());
    }

    private static void putLongArray(String key, Bundle bundle) {
        int length = random.nextInt(50);
        long[] array = new long[length];
        for (int i = 0; i < length; i++) {
            array[i] = random.nextLong();
        }
        bundle.putLongArray(key, array);
    }

    private static void putFloat(String key, Bundle bundle) {
        bundle.putFloat(key, random.nextFloat());
    }

    private static void putFloatArray(String key, Bundle bundle) {
        int length = random.nextInt(50);
        float[] array = new float[length];
        for (int i = 0; i < length; i++) {
            array[i] = random.nextFloat();
        }
        bundle.putFloatArray(key, array);
    }

    private static void putDouble(String key, Bundle bundle) {
        bundle.putDouble(key, random.nextDouble());
    }

    private static void putDoubleArray(String key, Bundle bundle) {
        int length = random.nextInt(50);
        double[] array = new double[length];
        for (int i = 0; i < length; i++) {
            array[i] = random.nextDouble();
        }
        bundle.putDoubleArray(key, array);
    }

    private static void putChar(String key, Bundle bundle) {
        bundle.putChar(key, getChar());
    }

    private static void putCharArray(String key, Bundle bundle) {
        bundle.putCharArray(key, getCharArray());
    }

    private static void putString(String key, Bundle bundle) {
        bundle.putString(key, new String(getCharArray()));
    }

    private static void putStringList(String key, Bundle bundle) {
        int length = random.nextInt(50);
        ArrayList<String> stringList = new ArrayList<String>(length);
        while (0 < length--) {
            if (length == 0) {
                stringList.add(null);
            } else {
                stringList.add(new String(getCharArray()));
            }
        }

        bundle.putStringArrayList(key, stringList);
    }

    private static char[] getCharArray() {
        int length = random.nextInt(50);
        char[] array = new char[length];
        for (int i = 0; i < length; i++) {
            array[i] = getChar();
        }

        return array;
    }

    private static char getChar() {
        return (char)random.nextInt(255);
    }

    private void ensureApplicationContext() {
        // Since the test case is not running on the UI thread, the applicationContext might
        // not be ready (i.e. it might be null). Wait for a bit to resolve this.
        long waitedFor = 0;
        try {
            // Don't hold up execution for too long.
            while (Robolectric.application.getApplicationContext() == null && waitedFor <= 2000) {
                Thread.sleep(50);
                waitedFor += 50;
            }
        }
        catch (InterruptedException e) {
        }
    }

}


File: facebook/junitTests/src/test/java/com/facebook/ProfileCacheTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook;

import android.content.Context;

import org.junit.Before;
import org.junit.Test;
import org.robolectric.Robolectric;

import static org.junit.Assert.*;

public final class ProfileCacheTest extends FacebookTestCase {
    @Before
    public void before() throws Exception {
        FacebookSdk.sdkInitialize(Robolectric.application);
        Robolectric.application.getSharedPreferences(
                ProfileCache.SHARED_PREFERENCES_NAME,
                Context.MODE_PRIVATE)
                .edit().
                clear().
                commit();
    }

    @Test
    public void testEmptyCase() {
        ProfileCache cache = new ProfileCache();
        assertNull(cache.load());
    }

    @Test
    public void testSaveGetAndClear() {
        ProfileCache cache = new ProfileCache();
        Profile profile1 = ProfileTest.createDefaultProfile();
        cache.save(profile1);
        Profile profile2 = cache.load();
        ProfileTest.assertDefaultObjectGetters(profile2);
        assertEquals(profile1, profile2);

        profile1 = ProfileTest.createMostlyNullsProfile();
        cache.save(profile1);
        profile2 = cache.load();
        ProfileTest.assertMostlyNullsObjectGetters(profile2);
        assertEquals(profile1, profile2);

        cache.clear();
        assertNull(cache.load());
    }
}


File: facebook/junitTests/src/test/java/com/facebook/ProfileManagerTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook;

import android.content.Intent;
import android.support.v4.content.LocalBroadcastManager;

import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;
import org.powermock.core.classloader.annotations.PrepareForTest;
import org.robolectric.Robolectric;

import java.util.InputMismatchException;

import static org.junit.Assert.*;
import static org.mockito.Matchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.powermock.api.mockito.PowerMockito.mock;

@PrepareForTest( { ProfileCache.class })
public class ProfileManagerTest extends FacebookPowerMockTestCase {

    @Before
    public void before() {
        FacebookSdk.sdkInitialize(Robolectric.application);
    }

    @Test
    public void testLoadCurrentProfileEmptyCache() {
        ProfileCache profileCache = mock(ProfileCache.class);
        LocalBroadcastManager localBroadcastManager = mock(LocalBroadcastManager.class);
        ProfileManager profileManager = new ProfileManager(
                localBroadcastManager,
                profileCache
        );
        assertFalse(profileManager.loadCurrentProfile());
        verify(profileCache, times(1)).load();
    }

    @Test
    public void testLoadCurrentProfileWithCache() {
        ProfileCache profileCache = mock(ProfileCache.class);
        Profile profile = ProfileTest.createDefaultProfile();
        when(profileCache.load()).thenReturn(profile);
        LocalBroadcastManager localBroadcastManager = mock(LocalBroadcastManager.class);
        ProfileManager profileManager = new ProfileManager(
                localBroadcastManager,
                profileCache
        );
        assertTrue(profileManager.loadCurrentProfile());
        verify(profileCache, times(1)).load();

        // Verify that we don't save it back
        verify(profileCache, never()).save(any(Profile.class));

        // Verify that we broadcast
        verify(localBroadcastManager).sendBroadcast(any(Intent.class));

        // Verify that if we set the same (semantically) profile there is no additional broadcast.
        profileManager.setCurrentProfile(ProfileTest.createDefaultProfile());
        verify(localBroadcastManager, times(1)).sendBroadcast(any(Intent.class));

        // Verify that if we unset the profile there is a broadcast
        profileManager.setCurrentProfile(null);
        verify(localBroadcastManager, times(2)).sendBroadcast(any(Intent.class));
    }
}


File: facebook/junitTests/src/test/java/com/facebook/ProfileTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook;

import android.net.Uri;
import android.os.Parcel;

import org.json.JSONObject;
import org.junit.Test;
import org.robolectric.Robolectric;

import static org.junit.Assert.*;

public final class ProfileTest extends FacebookTestCase {
    static final String ID = "ID";
    static final String ANOTHER_ID = "ANOTHER_ID";
    static final String FIRST_NAME = "FIRST_NAME";
    static final String MIDDLE_NAME = "MIDDLE_NAME";
    static final String LAST_NAME = "LAST_NAME";
    static final String NAME = "NAME";
    static final Uri LINK_URI = Uri.parse("https://www.facebook.com/name");

    public static Profile createDefaultProfile() {
        return new Profile(
                ID,
                FIRST_NAME,
                MIDDLE_NAME,
                LAST_NAME,
                NAME,
                LINK_URI
        );
    }

    static void assertDefaultObjectGetters(Profile profile) {
        assertEquals(ID, profile.getId());
        assertEquals(FIRST_NAME, profile.getFirstName());
        assertEquals(MIDDLE_NAME, profile.getMiddleName());
        assertEquals(LAST_NAME, profile.getLastName());
        assertEquals(NAME, profile.getName());
        assertEquals(LINK_URI, profile.getLinkUri());
    }

    static Profile createMostlyNullsProfile() {
        return new Profile(ANOTHER_ID, null, null, null, null, null);
    }

    static void assertMostlyNullsObjectGetters(Profile profile) {
        assertEquals(ANOTHER_ID, profile.getId());
        assertNull(profile.getFirstName());
        assertNull(profile.getMiddleName());
        assertNull(profile.getLastName());
        assertNull(profile.getName());
        assertNull(profile.getLinkUri());
    }


    @Test
    public void testProfileCtorAndGetters() {
        Profile profile = createDefaultProfile();
        assertDefaultObjectGetters(profile);

        profile = createMostlyNullsProfile();
        assertMostlyNullsObjectGetters(profile);
    }

    @Test
    public void testHashCode() {
        Profile profile1 = createDefaultProfile();
        Profile profile2 = createDefaultProfile();
        assertEquals(profile1.hashCode(), profile2.hashCode());

        Profile profile3 = createMostlyNullsProfile();
        assertNotEquals(profile1.hashCode(), profile3.hashCode());
    }

    @Test
    public void testEquals() {
        Profile profile1 = createDefaultProfile();
        Profile profile2 = createDefaultProfile();
        assertEquals(profile1, profile2);

        Profile profile3 = createMostlyNullsProfile();
        assertNotEquals(profile1, profile3);
    }

    @Test
    public void testJsonSerialization() {
        Profile profile1 = createDefaultProfile();
        JSONObject jsonObject = profile1.toJSONObject();
        Profile profile2 = new Profile(jsonObject);
        assertDefaultObjectGetters(profile2);
        assertEquals(profile1, profile2);

        // Check with nulls
        profile1 = createMostlyNullsProfile();
        jsonObject = profile1.toJSONObject();
        profile2 = new Profile(jsonObject);
        assertMostlyNullsObjectGetters(profile2);
        assertEquals(profile1, profile2);
    }

    @Test
    public void testParcelSerialization() {
        Profile profile1 = createDefaultProfile();
        Profile profile2 = TestUtils.parcelAndUnparcel(profile1);

        assertDefaultObjectGetters(profile2);
        assertEquals(profile1, profile2);

        // Check with nulls
        profile1 = createMostlyNullsProfile();
        profile2 = TestUtils.parcelAndUnparcel(profile1);
        assertMostlyNullsObjectGetters(profile2);
        assertEquals(profile1, profile2);
    }

    @Test
    public void testGetSetCurrentProfile() {
        FacebookSdk.sdkInitialize(Robolectric.application);
        Profile profile1 = createDefaultProfile();
        Profile.setCurrentProfile(profile1);
        assertEquals(ProfileManager.getInstance().getCurrentProfile(), profile1);
        assertEquals(profile1, Profile.getCurrentProfile());

        Profile.setCurrentProfile(null);
        assertNull(ProfileManager.getInstance().getCurrentProfile());
        assertNull(Profile.getCurrentProfile());
    }
}


File: facebook/junitTests/src/test/java/com/facebook/ProfileTrackerTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook;

import android.content.Intent;
import android.support.v4.content.LocalBroadcastManager;

import org.junit.Test;
import org.robolectric.Robolectric;

import static org.junit.Assert.*;

public class ProfileTrackerTest extends FacebookPowerMockTestCase {
    @Test
    public void testStartStopTrackingAndBroadcast() {
        FacebookSdk.sdkInitialize(Robolectric.application);
        LocalBroadcastManager localBroadcastManager =
                LocalBroadcastManager.getInstance(Robolectric.application);
        TestProfileTracker testProfileTracker = new TestProfileTracker();
        // Starts tracking
        assertTrue(testProfileTracker.isTracking());

        testProfileTracker.stopTracking();
        assertFalse(testProfileTracker.isTracking());
        sendBroadcast(localBroadcastManager, null, ProfileTest.createDefaultProfile());
        assertFalse(testProfileTracker.isCallbackCalled);
        testProfileTracker.startTracking();
        assertTrue(testProfileTracker.isTracking());
        Profile profile = ProfileTest.createDefaultProfile();
        sendBroadcast(localBroadcastManager, null, profile);
        assertNull(testProfileTracker.oldProfile);
        assertEquals(profile, testProfileTracker.currentProfile);
        assertTrue(testProfileTracker.isCallbackCalled);

        Profile profile1 = ProfileTest.createMostlyNullsProfile();
        Profile profile2 = ProfileTest.createDefaultProfile();
        sendBroadcast(localBroadcastManager, profile1, profile2);
        ProfileTest.assertMostlyNullsObjectGetters(testProfileTracker.oldProfile);
        ProfileTest.assertDefaultObjectGetters(testProfileTracker.currentProfile);
        assertEquals(profile1, testProfileTracker.oldProfile);
        assertEquals(profile2, testProfileTracker.currentProfile);

        testProfileTracker.stopTracking();
    }

    private static void sendBroadcast(
            LocalBroadcastManager localBroadcastManager,
            Profile oldProfile,
            Profile currentProfile) {
        Intent intent = new Intent(ProfileManager.ACTION_CURRENT_PROFILE_CHANGED);

        intent.putExtra(ProfileManager.EXTRA_OLD_PROFILE, oldProfile);
        intent.putExtra(ProfileManager.EXTRA_NEW_PROFILE, currentProfile);

        localBroadcastManager.sendBroadcast(intent);
    }

    static class TestProfileTracker extends ProfileTracker {
        Profile oldProfile;
        Profile currentProfile;
        boolean isCallbackCalled = false;

        @Override
        protected void onCurrentProfileChanged(Profile oldProfile, Profile currentProfile) {
            this.oldProfile = oldProfile;
            this.currentProfile = currentProfile;
            isCallbackCalled = true;
        }
    }

}


File: facebook/junitTests/src/test/java/com/facebook/ProgressNoopOutputStreamTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.robolectric.Robolectric;

import static org.junit.Assert.*;


public class ProgressNoopOutputStreamTest extends FacebookTestCase {
    private ProgressNoopOutputStream stream;

    @Before
    public void before() throws Exception {
        FacebookSdk.sdkInitialize(Robolectric.application);
        stream = new ProgressNoopOutputStream(null);
    }

    @After
    public void after() throws Exception {
        stream.close();
    }

    @Test
    public void testSetup() {
        assertEquals(0, stream.getMaxProgress());
        assertTrue(stream.getProgressMap().isEmpty());
    }

    @Test
    public void testWriting() {
        assertEquals(0, stream.getMaxProgress());

        stream.write(0);
        assertEquals(1, stream.getMaxProgress());

        final byte[] buf = new byte[8];

        stream.write(buf);
        assertEquals(9, stream.getMaxProgress());

        stream.write(buf, 2, 2);
        assertEquals(11, stream.getMaxProgress());

        stream.addProgress(16);
        assertEquals(27, stream.getMaxProgress());
    }
}


File: facebook/junitTests/src/test/java/com/facebook/ProgressOutputStreamTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.robolectric.Robolectric;

import java.io.ByteArrayOutputStream;
import java.util.HashMap;
import java.util.Map;

import static org.junit.Assert.*;

public class ProgressOutputStreamTest extends FacebookTestCase {
    private static final int MAX_PROGRESS = 10;

    private GraphRequest r1, r2;
    private Map<GraphRequest, RequestProgress> progressMap;
    private GraphRequestBatch requests;
    private ProgressOutputStream stream;

    @Before
    public void before() throws Exception {
        FacebookSdk.sdkInitialize(Robolectric.application);
        r1 = new GraphRequest(null, "4");
        r2 = new GraphRequest(null, "4");

        progressMap = new HashMap<GraphRequest, RequestProgress>();
        progressMap.put(r1, new RequestProgress(null, r1));
        progressMap.get(r1).addToMax(5);
        progressMap.put(r2, new RequestProgress(null, r2));
        progressMap.get(r2).addToMax(5);

        requests = new GraphRequestBatch(r1, r2);

        ByteArrayOutputStream backing = new ByteArrayOutputStream();
        stream = new ProgressOutputStream(backing, requests, progressMap, MAX_PROGRESS);
    }

    @After
    public void after() throws Exception {
        stream.close();
    }

    @Test
    public void testSetup() {
        assertEquals(0, stream.getBatchProgress());
        assertEquals(MAX_PROGRESS, stream.getMaxProgress());

        for (RequestProgress p : progressMap.values()) {
            assertEquals(0, p.getProgress());
            assertEquals(5, p.getMaxProgress());
        }
    }

    @Test
    public void testWriting() {
        try {
            assertEquals(0, stream.getBatchProgress());

            stream.setCurrentRequest(r1);
            stream.write(0);
            assertEquals(1, stream.getBatchProgress());

            final byte[] buf = new byte[4];
            stream.write(buf);
            assertEquals(5, stream.getBatchProgress());

            stream.setCurrentRequest(r2);
            stream.write(buf, 2, 2);
            stream.write(buf, 1, 3);
            assertEquals(MAX_PROGRESS, stream.getBatchProgress());

            assertEquals(stream.getMaxProgress(), stream.getBatchProgress());
            assertEquals(progressMap.get(r1).getMaxProgress(), progressMap.get(r1).getProgress());
            assertEquals(progressMap.get(r2).getMaxProgress(), progressMap.get(r2).getProgress());
        }
        catch (Exception ex) {
            fail(ex.getMessage());
        }
    }
}


File: facebook/junitTests/src/test/java/com/facebook/internal/CallbackManagerImplPowerMockTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook.internal;

import android.content.Intent;

import com.facebook.FacebookPowerMockTestCase;
import com.facebook.FacebookSdk;

import org.junit.Before;
import org.junit.Test;
import org.powermock.core.classloader.annotations.PrepareForTest;
import org.powermock.reflect.Whitebox;
import org.robolectric.Robolectric;

import java.util.HashMap;

import bolts.Capture;

import static org.junit.Assert.*;

@PrepareForTest({ CallbackManagerImpl.class })
public final class CallbackManagerImplPowerMockTest extends FacebookPowerMockTestCase {

    @Before
    public void before() {
        FacebookSdk.sdkInitialize(Robolectric.application);
        // Reset the static state every time so tests don't interfere with each other.
        Whitebox.setInternalState(
                CallbackManagerImpl.class,
                "staticCallbacks",
                new HashMap<Integer, CallbackManagerImpl.Callback>());
    }

    @Test
    public void testStaticRegisterValidations() {
        try {
            CallbackManagerImpl.registerStaticCallback(
                    CallbackManagerImpl.RequestCodeOffset.Login.toRequestCode(), null);
            fail();
        } catch (NullPointerException exception) { }
    }

    @Test
    public void testRegisterValidations() {
        CallbackManagerImpl callbackManagerImpl = new CallbackManagerImpl();
        try {
            callbackManagerImpl.registerCallback(
                    CallbackManagerImpl.RequestCodeOffset.Login.toRequestCode(), null);
            fail();
        } catch (NullPointerException exception) { }
    }

    @Test
    public void testCallbackExecuted() {
        final Capture<Boolean> capture = new Capture(false);

        final CallbackManagerImpl callbackManagerImpl = new CallbackManagerImpl();

        callbackManagerImpl.registerCallback(
                CallbackManagerImpl.RequestCodeOffset.Login.toRequestCode(),
                new CallbackManagerImpl.Callback() {
                    @Override
                    public boolean onActivityResult(int resultCode, Intent data) {
                        capture.set(true);
                        return true;
                    }
                });
        callbackManagerImpl.onActivityResult(
                FacebookSdk.getCallbackRequestCodeOffset(),
                1,
                new Intent());
        assertTrue(capture.get());
    }

    @Test
    public void testRightCallbackExecuted() {
        final Capture<Boolean> capture = new Capture(false);

        final CallbackManagerImpl callbackManagerImpl = new CallbackManagerImpl();

        callbackManagerImpl.registerCallback(
                123,
                new CallbackManagerImpl.Callback() {
                    @Override
                    public boolean onActivityResult(int resultCode, Intent data) {
                        capture.set(true);
                        return true;
                    }
                });
        callbackManagerImpl.registerCallback(
                456,
                new CallbackManagerImpl.Callback() {
                    @Override
                    public boolean onActivityResult(int resultCode, Intent data) {
                        return false;
                    }
                });
        callbackManagerImpl.onActivityResult(
                123,
                1,
                new Intent());
        assertTrue(capture.get());
    }

    @Test
    public void testStaticCallbackExecuted() {
        final Capture<Boolean> capture = new Capture(false);

        final CallbackManagerImpl callbackManagerImpl = new CallbackManagerImpl();

        callbackManagerImpl.registerStaticCallback(
                CallbackManagerImpl.RequestCodeOffset.Login.toRequestCode(),
                new CallbackManagerImpl.Callback() {
                    @Override
                    public boolean onActivityResult(int resultCode, Intent data) {
                        capture.set(true);
                        return true;
                    }
                });
        callbackManagerImpl.onActivityResult(
                FacebookSdk.getCallbackRequestCodeOffset(),
                1,
                new Intent());
        assertTrue(capture.get());
    }

    @Test
    public void testStaticCallbackSkipped() {
        final Capture<Boolean> capture = new Capture(false);
        final Capture<Boolean> captureStatic = new Capture(false);

        final CallbackManagerImpl callbackManagerImpl = new CallbackManagerImpl();

        callbackManagerImpl.registerCallback(
                CallbackManagerImpl.RequestCodeOffset.Login.toRequestCode(),
                new CallbackManagerImpl.Callback() {
                    @Override
                    public boolean onActivityResult(int resultCode, Intent data) {
                        capture.set(true);
                        return true;
                    }
                });
        callbackManagerImpl.registerStaticCallback(
                CallbackManagerImpl.RequestCodeOffset.Login.toRequestCode(),
                new CallbackManagerImpl.Callback() {
                    @Override
                    public boolean onActivityResult(int resultCode, Intent data) {
                        captureStatic.set(true);
                        return true;
                    }
                });
        callbackManagerImpl.onActivityResult(
                FacebookSdk.getCallbackRequestCodeOffset(),
                1,
                new Intent());
        assertTrue(capture.get());
        assertFalse(captureStatic.get());
    }
}


File: facebook/junitTests/src/test/java/com/facebook/internal/FileLruCacheTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook.internal;


import com.facebook.FacebookSdk;
import com.facebook.FacebookTestCase;
import com.facebook.TestUtils;

import org.junit.Before;
import org.junit.Test;
import org.robolectric.Robolectric;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Random;

import static org.junit.Assert.*;

public final class FileLruCacheTest extends FacebookTestCase {
    private static final Random random = new Random();

    @Before
    public void before() {
        FacebookSdk.sdkInitialize(Robolectric.application);
    }

    @Test
    public void testCacheOutputStream() throws Exception {
        int dataSize = 1024;
        byte[] data = generateBytes(dataSize);
        String key = "a";

        // Limit to 2x to allow for extra header data
        FileLruCache cache = new FileLruCache("testCacheOutputStream", limitCacheSize(2*dataSize));

        try {
            put(cache, key, data);
            checkValue(cache, key, data);
        } finally {
            TestUtils.clearAndDeleteLruCacheDirectory(cache);
        }
    }

    @Test
    public void testCacheInputStream() throws Exception {
        int dataSize = 1024;
        byte[] data = generateBytes(dataSize);
        String key = "a";
        InputStream stream = new ByteArrayInputStream(data);

        // Limit to 2x to allow for extra header data
        FileLruCache cache = new FileLruCache("testCacheInputStream", limitCacheSize(2*dataSize));
        try {
            TestUtils.clearFileLruCache(cache);

            InputStream wrapped = cache.interceptAndPut(key, stream);
            consumeAndClose(wrapped);
            checkValue(cache, key, data);
        } finally {
            TestUtils.clearAndDeleteLruCacheDirectory(cache);
        }
    }

    @Test
    public void testCacheClear() throws Exception {
        int dataSize = 1024;
        byte[] data = generateBytes(dataSize);
        String key = "a";

        // Limit to 2x to allow for extra header data
        FileLruCache cache = new FileLruCache("testCacheClear", limitCacheSize(2*dataSize));
        try {
            TestUtils.clearFileLruCache(cache);

            put(cache, key, data);
            checkValue(cache, key, data);

            TestUtils.clearFileLruCache(cache);
            assertEquals(false, hasValue(cache, key));
            assertEquals(0, cache.sizeInBytesForTest());
        } finally {
            TestUtils.clearAndDeleteLruCacheDirectory(cache);
        }
    }

    @Test
    public void testCacheClearMidBuffer() throws Exception {
        int dataSize = 1024;
        byte[] data = generateBytes(dataSize);
        String key = "a";
        String key2 = "b";

        // Limit to 2x to allow for extra header data
        FileLruCache cache = new FileLruCache("testCacheClear", limitCacheSize(2*dataSize));
        try {
            TestUtils.clearFileLruCache(cache);

            put(cache, key, data);
            checkValue(cache, key, data);
            OutputStream stream = cache.openPutStream(key2);
            Thread.sleep(200);

            TestUtils.clearFileLruCache(cache);

            stream.write(data);
            stream.close();

            assertEquals(false, hasValue(cache, key));
            assertEquals(false, hasValue(cache, key2));
            assertEquals(0, cache.sizeInBytesForTest());
        } finally {
            TestUtils.clearAndDeleteLruCacheDirectory(cache);
        }
    }

    @Test
    public void testSizeInBytes() throws Exception {
        int count = 17;
        int dataSize = 53;
        int cacheSize = count * dataSize;
        byte[] data = generateBytes(dataSize);

        // Limit to 2x to allow for extra header data
        FileLruCache cache = new FileLruCache("testSizeInBytes", limitCacheSize(2*cacheSize));
        try {
            TestUtils.clearFileLruCache(cache);

            for (int i = 0; i < count; i++) {
                put(cache, i, data);

                // The size reported by sizeInBytes includes a version/size token as well
                // as a JSON blob that records the name.  Verify that the cache size is larger
                // than the data content but not more than twice as large.  This guarantees
                // that sizeInBytes is doing at least approximately the right thing.
                int totalDataSize = (i + 1) * dataSize;
                assertTrue(cache.sizeInBytesForTest() > totalDataSize);
                assertTrue(cache.sizeInBytesForTest() < 2 * totalDataSize);
            }
            for (int i = 0; i < count; i++) {
                String key = Integer.valueOf(i).toString();
                checkValue(cache, key, data);
            }
        } finally {
            TestUtils.clearAndDeleteLruCacheDirectory(cache);
        }
    }

    @Test
    public void testCacheSizeLimit() throws Exception {
        int count = 64;
        int dataSize = 32;
        int cacheSize = count * dataSize / 2;
        byte[] data = generateBytes(dataSize);

        // Here we do not set the limit to 2x to make sure we hit the limit well before we have
        // added all the data.
        FileLruCache cache = new FileLruCache("testCacheSizeLimit", limitCacheSize(cacheSize));
        try {
            TestUtils.clearFileLruCache(cache);

            for (int i = 0; i < count; i++) {
                put(cache, i, data);

                // See comment in testSizeInBytes for why this is not an exact calculation.
                //
                // This changes verification such that the final cache size lands somewhere
                // between half and full quota.
                int totalDataSize = (i + 1) * dataSize;
                assertTrue(cache.sizeInBytesForTest() > Math.min(totalDataSize, cacheSize / 2));
                assertTrue(cache.sizeInBytesForTest() < Math.min(2 * totalDataSize, cacheSize));
            }

            // sleep for a bit to make sure the trim finishes
            Thread.sleep(200);

            // Verify that some keys exist and others do not
            boolean hasValueExists = false;
            boolean hasNoValueExists = false;

            for (int i = 0; i < count; i++) {
                String key = Integer.valueOf(i).toString();
                if (hasValue(cache, key)) {
                    hasValueExists = true;
                    checkValue(cache, key, data);
                } else {
                    hasNoValueExists = true;
                }
            }

            assertEquals(true, hasValueExists);
            assertEquals(true, hasNoValueExists);
        } finally {
            TestUtils.clearAndDeleteLruCacheDirectory(cache);
        }
    }

    @Test
    public void testCacheCountLimit() throws Exception {
        int count = 64;
        int dataSize = 32;
        int cacheCount = count / 2;
        byte[] data = generateBytes(dataSize);

        // Here we only limit by count, and we allow half of the entries.
        FileLruCache cache = new FileLruCache("testCacheCountLimit", limitCacheCount(cacheCount));
        try {
            TestUtils.clearFileLruCache(cache);

            for (int i = 0; i < count; i++) {
                put(cache, i, data);
            }

            // sleep for a bit to make sure the trim finishes
            Thread.sleep(200);

            // Verify that some keys exist and others do not
            boolean hasValueExists = false;
            boolean hasNoValueExists = false;

            for (int i = 0; i < count; i++) {
                if (hasValue(cache, i)) {
                    hasValueExists = true;
                    checkValue(cache, i, data);
                } else {
                    hasNoValueExists = true;
                }
            }

            assertEquals(true, hasValueExists);
            assertEquals(true, hasNoValueExists);
        } finally {
            TestUtils.clearAndDeleteLruCacheDirectory(cache);
        }
    }

    @Test
    public void testCacheLru() throws IOException, InterruptedException {
        int keepCount = 10;
        int otherCount = 5;
        int dataSize = 64;
        byte[] data = generateBytes(dataSize);

        // Limit by count, and allow all the keep keys plus one other.
        FileLruCache cache = new FileLruCache("testCacheLru", limitCacheCount(keepCount + 1));
        try {
            TestUtils.clearFileLruCache(cache);

            for (int i = 0; i < keepCount; i++) {
                put(cache, i, data);
            }

            // Make sure operations are separated by enough time that the file timestamps are all different.
            // On the test device, it looks like lastModified has 1-second resolution, so we have to wait at
            // least a second to guarantee that updated timestamps will come later.
            Thread.sleep(1000);
            for (int i = 0; i < otherCount; i++) {
                put(cache, keepCount + i, data);
                Thread.sleep(1000);

                // By verifying all the keep keys, they should be LRU and survive while the others do not.
                for (int keepIndex = 0; keepIndex < keepCount; keepIndex++) {
                    checkValue(cache, keepIndex, data);
                }
                Thread.sleep(200);
            }

            // All but the last other key should have been pushed out
            for (int i = 0; i < (otherCount - 1); i++) {
                String key = Integer.valueOf(keepCount + i).toString();
                assertEquals(false, hasValue(cache, key));
            }
        } finally {
            TestUtils.clearAndDeleteLruCacheDirectory(cache);
        }
    }

    @Test
    public void testConcurrentWritesToSameKey() throws IOException, InterruptedException {
        final int count = 5;
        final int dataSize = 81;
        final int threadCount = 31;
        final int iterationCount = 10;
        final byte[] data = generateBytes(dataSize);

        final FileLruCache cache = new FileLruCache(
                "testConcurrentWritesToSameKey", limitCacheCount(count+1));
        try {
            TestUtils.clearFileLruCache(cache);

            Runnable run = new Runnable() {
                @Override
                public void run() {
                    for (int iterations = 0; iterations < iterationCount; iterations++) {
                        for (int i = 0; i < count; i++) {
                            put(cache, i, data);
                        }
                    }
                }
            };

            // Create a bunch of threads to write a set of keys repeatedly
            Thread[] threads = new Thread[threadCount];
            for (int i = 0; i < threads.length; i++) {
                threads[i] = new Thread(run);
            }

            for (Thread thread : threads) {
                thread.start();
            }

            for (Thread thread : threads) {
                thread.join(10 * 1000, 0);
            }

            // Verify that the file state ended up consistent in the end
            for (int i = 0; i < count; i++) {
                checkValue(cache, i, data);
            }
        } finally {
            TestUtils.clearAndDeleteLruCacheDirectory(cache);
        }
    }

    byte[] generateBytes(int n) {
        byte[] bytes = new byte[n];
        random.nextBytes(bytes);
        return bytes;
    }

    FileLruCache.Limits limitCacheSize(int n) {
        FileLruCache.Limits limits = new FileLruCache.Limits();
        limits.setByteCount(n);
        return limits;
    }

    FileLruCache.Limits limitCacheCount(int n) {
        FileLruCache.Limits limits = new FileLruCache.Limits();
        limits.setFileCount(n);
        return limits;
    }

    void put(FileLruCache cache, int i, byte[] data) {
        put(cache, Integer.valueOf(i).toString(), data);
    }

    void put(FileLruCache cache, String key, byte[] data) {
        try {
            OutputStream stream = cache.openPutStream(key);
            assertNotNull(stream);

            stream.write(data);
            stream.close();
        } catch (IOException e) {
            // Fail test and print Exception
            assertNull(e);
        }
    }

    void checkValue(FileLruCache cache, int i, byte[] expected) {
        checkValue(cache, Integer.valueOf(i).toString(), expected);
    }

    void checkValue(FileLruCache cache, String key, byte[] expected) {
        try {
            InputStream stream = cache.get(key);
            assertNotNull(stream);

            checkInputStream(expected, stream);
            stream.close();
        } catch (IOException e) {
            // Fail test and print Exception
            assertNull(e);
        }
    }

    boolean hasValue(FileLruCache cache, int i) {
        return hasValue(cache, Integer.valueOf(i).toString());
    }

    boolean hasValue(FileLruCache cache, String key) {
        InputStream stream = null;

        try {
            stream = cache.get(key);
        } catch (IOException e) {
            // Fail test and print Exception
            assertNull(e);
        }

        return stream != null;
    }

    void checkInputStream(byte[] expected, InputStream actual) {
        try {
            for (int i = 0; i < expected.length; i++) {
                int b = actual.read();
                assertEquals(((int)expected[i]) & 0xff, b);
            }

            int eof = actual.read();
            assertEquals(-1, eof);
        } catch (IOException e) {
            // Fail test and print Exception
            assertNull(e);
        }
    }

    void consumeAndClose(InputStream stream) {
        try {
            byte[] buffer = new byte[1024];
            while (stream.read(buffer) > -1) {
                // these bytes intentionally ignored
            }
            stream.close();
        } catch (IOException e) {
            // Fail test and print Exception
            assertNull(e);
        }
    }
}


File: facebook/junitTests/src/test/java/com/facebook/login/KatanaProxyLoginMethodHandlerTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook.login;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;

import com.facebook.AccessToken;
import com.facebook.FacebookSdk;
import com.facebook.TestUtils;

import org.junit.Before;
import org.junit.Test;
import org.mockito.ArgumentCaptor;
import org.powermock.core.classloader.annotations.PrepareForTest;
import org.robolectric.Robolectric;

import java.util.Date;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.mockito.Matchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.powermock.api.mockito.PowerMockito.when;

@PrepareForTest( { LoginClient.class })
public class KatanaProxyLoginMethodHandlerTest extends LoginHandlerTestCase {
    private final static String SIGNED_REQUEST_STR = "ggarbage.eyJhbGdvcml0aG0iOiJITUFDSEEyNTYiLCJ"
            + "jb2RlIjoid2h5bm90IiwiaXNzdWVkX2F0IjoxNDIyNTAyMDkyLCJ1c2VyX2lkIjoiMTIzIn0";

    @Before
    @Override
    public void before() throws Exception {
        super.before();
        FacebookSdk.sdkInitialize(Robolectric.application);
    }

    @Test
    public void testProxyAuthHandlesSuccess() {
        Bundle bundle = new Bundle();
        bundle.putLong("expires_in", EXPIRES_IN_DELTA);
        bundle.putString("access_token", ACCESS_TOKEN);
        bundle.putString("signed_request", SIGNED_REQUEST_STR);

        Intent intent = new Intent();
        intent.putExtras(bundle);

        KatanaProxyLoginMethodHandler handler = new KatanaProxyLoginMethodHandler(mockLoginClient);

        LoginClient.Request request = createRequest();
        when(mockLoginClient.getPendingRequest()).thenReturn(request);

        handler.tryAuthorize(request);
        handler.onActivityResult(0, Activity.RESULT_OK, intent);

        ArgumentCaptor<LoginClient.Result> resultArgumentCaptor =
                ArgumentCaptor.forClass(LoginClient.Result.class);
        verify(mockLoginClient, times(1)).completeAndValidate(resultArgumentCaptor.capture());

        LoginClient.Result result = resultArgumentCaptor.getValue();

        assertNotNull(result);
        assertEquals(LoginClient.Result.Code.SUCCESS, result.code);

        AccessToken token = result.token;
        assertNotNull(token);
        assertEquals(ACCESS_TOKEN, token.getToken());
        assertDateDiffersWithinDelta(new Date(), token.getExpires(), EXPIRES_IN_DELTA * 1000, 1000);
        TestUtils.assertSamePermissions(PERMISSIONS, token.getPermissions());
    }

    @Test
    public void testProxyAuthHandlesCancel() {
        Bundle bundle = new Bundle();
        bundle.putString("error", ERROR_MESSAGE);

        Intent intent = new Intent();
        intent.putExtras(bundle);

        KatanaProxyLoginMethodHandler handler = new KatanaProxyLoginMethodHandler(mockLoginClient);

        LoginClient.Request request = createRequest();
        handler.tryAuthorize(request);
        handler.onActivityResult(0, Activity.RESULT_CANCELED, intent);

        ArgumentCaptor<LoginClient.Result> resultArgumentCaptor =
                ArgumentCaptor.forClass(LoginClient.Result.class);
        verify(mockLoginClient, times(1)).completeAndValidate(resultArgumentCaptor.capture());

        LoginClient.Result result = resultArgumentCaptor.getValue();

        assertNotNull(result);
        assertEquals(LoginClient.Result.Code.CANCEL, result.code);

        assertNull(result.token);
        assertNotNull(result.errorMessage);
        assertTrue(result.errorMessage.contains(ERROR_MESSAGE));
    }

    @Test
    public void testProxyAuthHandlesCancelErrorMessage() {
        Bundle bundle = new Bundle();
        bundle.putString("error", "access_denied");

        Intent intent = new Intent();
        intent.putExtras(bundle);

        KatanaProxyLoginMethodHandler handler = new KatanaProxyLoginMethodHandler(mockLoginClient);

        LoginClient.Request request = createRequest();
        handler.tryAuthorize(request);
        handler.onActivityResult(0, Activity.RESULT_CANCELED, intent);

        ArgumentCaptor<LoginClient.Result> resultArgumentCaptor =
                ArgumentCaptor.forClass(LoginClient.Result.class);
        verify(mockLoginClient, times(1)).completeAndValidate(resultArgumentCaptor.capture());

        LoginClient.Result result = resultArgumentCaptor.getValue();

        assertNotNull(result);
        assertEquals(LoginClient.Result.Code.CANCEL, result.code);

        assertNull(result.token);
    }

    @Test
    public void testProxyAuthHandlesDisabled() {
        Bundle bundle = new Bundle();
        bundle.putString("error", "service_disabled");

        Intent intent = new Intent();
        intent.putExtras(bundle);

        KatanaProxyLoginMethodHandler handler = new KatanaProxyLoginMethodHandler(mockLoginClient);

        LoginClient.Request request = createRequest();
        handler.tryAuthorize(request);
        handler.onActivityResult(0, Activity.RESULT_OK, intent);

        verify(mockLoginClient, never()).completeAndValidate(any(LoginClient.Result.class));
        verify(mockLoginClient, times(1)).tryNextHandler();
    }
}


File: facebook/junitTests/src/test/java/com/facebook/login/LoginClientTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook.login;

import android.support.v4.app.Fragment;
import android.support.v4.app.FragmentActivity;

import com.facebook.AccessToken;
import com.facebook.FacebookPowerMockTestCase;
import com.facebook.FacebookSdk;
import com.facebook.TestUtils;

import org.junit.Before;
import org.junit.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.powermock.core.classloader.annotations.PrepareForTest;
import org.robolectric.Robolectric;

import java.util.Arrays;
import java.util.HashSet;

import static org.junit.Assert.*;
import static org.mockito.Mockito.verify;
import static org.powermock.api.mockito.PowerMockito.mock;
import static org.powermock.api.mockito.PowerMockito.when;

@PrepareForTest({ LoginClient.class })
public class LoginClientTest extends FacebookPowerMockTestCase {

    private static final String ACCESS_TOKEN = "An access token for user 1";
    private static final String USER_ID = "1001";
    private static final String APP_ID = "2002";


    private static final long EXPIRES_IN_DELTA = 3600 * 24 * 60;
    private static final HashSet<String> PERMISSIONS = new HashSet<String>(
        Arrays.asList("go outside", "come back in"));
    private static final String ERROR_MESSAGE = "This is bad!";

    @Mock private Fragment mockFragment;

    @Before
    public void before() throws Exception {
        FragmentActivity activity =
            Robolectric.buildActivity(FragmentActivity.class).create().get();
        when(mockFragment.getActivity()).thenReturn(activity);
    }

    @Test
    public void testReauthorizationWithSameFbidSucceeds() throws Exception {
        FacebookSdk.sdkInitialize(Robolectric.application);
        LoginClient.Request request = createRequest(ACCESS_TOKEN);

        AccessToken token = new AccessToken(
                ACCESS_TOKEN,
                APP_ID,
                USER_ID,
                PERMISSIONS,
                null,
                null,
                null,
                null);
        LoginClient.Result result = LoginClient.Result.createTokenResult(request, token);

        LoginClient.OnCompletedListener listener = mock(LoginClient.OnCompletedListener.class);

        LoginClient client = new LoginClient(mockFragment);
        client.setOnCompletedListener(listener);

        client.completeAndValidate(result);

        ArgumentCaptor<LoginClient.Result> resultArgumentCaptor =
            ArgumentCaptor.forClass(LoginClient.Result.class);

        verify(listener).onCompleted(resultArgumentCaptor.capture());

        result = resultArgumentCaptor.getValue();

        assertNotNull(result);
        assertEquals(LoginClient.Result.Code.SUCCESS, result.code);

        AccessToken resultToken = result.token;
        assertNotNull(resultToken);
        assertEquals(ACCESS_TOKEN, resultToken.getToken());

        // We don't care about ordering.
        assertEquals(PERMISSIONS, resultToken.getPermissions());
    }

    @Test
    public void testRequestParceling() {
        LoginClient.Request request = createRequest(ACCESS_TOKEN);

        LoginClient.Request unparceledRequest = TestUtils.parcelAndUnparcel(request);

        assertEquals(LoginBehavior.SSO_WITH_FALLBACK, unparceledRequest.getLoginBehavior());
        assertEquals(new HashSet<String>(PERMISSIONS), unparceledRequest.getPermissions());
        assertEquals(DefaultAudience.FRIENDS, unparceledRequest.getDefaultAudience());
        assertEquals("1234", unparceledRequest.getApplicationId());
        assertEquals("5678", unparceledRequest.getAuthId());
        assertFalse(unparceledRequest.isRerequest());
    }

    @Test
    public void testResultParceling() {
        LoginClient.Request request = new LoginClient.Request(
                LoginBehavior.SUPPRESS_SSO,
                null,
                DefaultAudience.EVERYONE,
                null,
                null);
        request.setRerequest(true);
        AccessToken token1 = new AccessToken(
                "Token2",
                "12345",
                "1000",
                null,
                null,
                null,
                null,
                null);
        LoginClient.Result result = new LoginClient.Result(
                request,
                LoginClient.Result.Code.SUCCESS,
                token1,
                "error 1",
                "123"
        );

        LoginClient.Result unparceledResult = TestUtils.parcelAndUnparcel(result);
        LoginClient.Request unparceledRequest = unparceledResult.request;

        assertEquals(LoginBehavior.SUPPRESS_SSO, unparceledRequest.getLoginBehavior());
        assertEquals(new HashSet<String>(), unparceledRequest.getPermissions());
        assertEquals(DefaultAudience.EVERYONE, unparceledRequest.getDefaultAudience());
        assertEquals(null, unparceledRequest.getApplicationId());
        assertEquals(null, unparceledRequest.getAuthId());
        assertTrue(unparceledRequest.isRerequest());

        assertEquals(LoginClient.Result.Code.SUCCESS, unparceledResult.code);
        assertEquals(token1, unparceledResult.token);
        assertEquals("error 1", unparceledResult.errorMessage);
        assertEquals("123", unparceledResult.errorCode);
    }


    protected LoginClient.Request createRequest(String previousAccessTokenString) {
        return new LoginClient.Request(
                LoginBehavior.SSO_WITH_FALLBACK,
                new HashSet<String>(PERMISSIONS),
                DefaultAudience.FRIENDS,
                "1234",
                "5678");
    }

}


File: facebook/junitTests/src/test/java/com/facebook/login/LoginResultTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook.login;

import com.facebook.AccessToken;
import com.facebook.FacebookSdk;
import com.facebook.FacebookTestCase;

import org.junit.Before;
import org.junit.Test;
import org.robolectric.Robolectric;

import java.util.HashSet;
import java.util.Set;

import static org.junit.Assert.*;

public class LoginResultTest extends FacebookTestCase {

    private final Set<String> EMAIL_SET = new HashSet<String>(){{ add("email"); }};
    private final Set<String> LIKES_EMAIL_SET = new HashSet<String>(){{
        add("user_likes");
        add("email");
    }};
    private final Set<String> PROFILE_EMAIL_SET = new HashSet<String>(){{
        add("user_profile");
        add("email");
    }};

    @Before
    public void before() throws Exception {
        FacebookSdk.sdkInitialize(Robolectric.application);
    }

    @Test
    public void testInitialLogin() {
        LoginClient.Request request = createRequest(EMAIL_SET, false);
        AccessToken accessToken = createAccessToken(PROFILE_EMAIL_SET, new HashSet<String>());
        LoginResult result = LoginManager.computeLoginResult(request, accessToken);
        assertEquals(accessToken, result.getAccessToken());
        assertEquals(PROFILE_EMAIL_SET, result.getRecentlyGrantedPermissions());
        assertEquals(0, result.getRecentlyDeniedPermissions().size());
    }

    @Test
    public void testReAuth() {
        LoginClient.Request request = createRequest(EMAIL_SET, true);
        AccessToken accessToken = createAccessToken(PROFILE_EMAIL_SET, new HashSet<String>());
        LoginResult result = LoginManager.computeLoginResult(request, accessToken);
        assertEquals(accessToken, result.getAccessToken());
        assertEquals(EMAIL_SET, result.getRecentlyGrantedPermissions());
        assertEquals(0, result.getRecentlyDeniedPermissions().size());
    }

    @Test
    public void testDeniedPermissions() {
        LoginClient.Request request = createRequest(LIKES_EMAIL_SET, true);
        AccessToken accessToken = createAccessToken(EMAIL_SET, new HashSet<String>());
        LoginResult result = LoginManager.computeLoginResult(request, accessToken);
        assertEquals(accessToken, result.getAccessToken());
        assertEquals(EMAIL_SET, result.getRecentlyGrantedPermissions());
        assertEquals(
                new HashSet<String>(){{ add("user_likes"); }},
                result.getRecentlyDeniedPermissions());
    }


    private AccessToken createAccessToken(Set<String> permissions,
                                          Set<String> declinedPermissions) {
        return new AccessToken(
            "token",
            "123",
            "234",
            permissions,
            declinedPermissions,
            null,
            null,
            null
        );
    }

    private LoginClient.Request createRequest(Set<String> permissions, boolean isRerequest) {
        LoginClient.Request request = new LoginClient.Request(
                LoginBehavior.SSO_WITH_FALLBACK,
                permissions,
                DefaultAudience.EVERYONE,
                "123",
                "authid"
        );
        request.setRerequest(isRerequest);
        return request;
    }
}


File: facebook/junitTests/src/test/java/com/facebook/login/widget/LoginButtonTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook.login.widget;

import android.app.Activity;

import com.facebook.FacebookTestCase;
import com.facebook.junittests.MainActivity;
import com.facebook.junittests.R;
import com.facebook.login.DefaultAudience;
import com.facebook.login.LoginManager;

import org.junit.Test;
import org.robolectric.Robolectric;

import java.util.ArrayList;

import static org.junit.Assert.fail;
import static org.mockito.Matchers.anyCollection;
import static org.mockito.Matchers.isA;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.powermock.api.mockito.PowerMockito.mock;

public class LoginButtonTest extends FacebookTestCase {

    @Test
    public void testLoginButtonWithReadPermissions() throws Exception {
        LoginManager loginManager = mock(LoginManager.class);
        Activity activity = Robolectric.buildActivity(MainActivity.class).create().get();

        LoginButton loginButton = (LoginButton) activity.findViewById(R.id.login_button);
        ArrayList<String> permissions = new ArrayList<>();
        permissions.add("user_location");
        loginButton.setReadPermissions(permissions);
        loginButton.setDefaultAudience(DefaultAudience.EVERYONE);
        loginButton.setLoginManager(loginManager);
        loginButton.performClick();

        verify(loginManager).logInWithReadPermissions(activity, permissions);
        verify(loginManager, never())
                .logInWithPublishPermissions(isA(Activity.class), anyCollection());
        // Verify default audience is channeled
        verify(loginManager).setDefaultAudience(DefaultAudience.EVERYONE);
    }

    @Test
    public void testLoginButtonWithPublishPermissions() throws Exception {
        LoginManager loginManager = mock(LoginManager.class);
        Activity activity = Robolectric.buildActivity(MainActivity.class).create().get();

        LoginButton loginButton = (LoginButton) activity.findViewById(R.id.login_button);
        ArrayList<String> permissions = new ArrayList<>();
        permissions.add("publish_actions");
        loginButton.setPublishPermissions(permissions);
        loginButton.setLoginManager(loginManager);
        loginButton.performClick();

        verify(loginManager, never())
                .logInWithReadPermissions(isA(Activity.class), anyCollection());
        verify(loginManager).logInWithPublishPermissions(activity, permissions);
    }

    @Test
    public void testCantSetReadThenPublishPermissions() throws Exception {
        Activity activity = Robolectric.buildActivity(MainActivity.class).create().get();

        LoginButton loginButton = (LoginButton) activity.findViewById(R.id.login_button);
        loginButton.setReadPermissions("user_location");
        try {
            loginButton.setPublishPermissions("publish_actions");
        } catch (UnsupportedOperationException e) {
            return;
        }
        fail();
    }

    @Test
    public void testCantSetPublishThenReadPermissions() throws Exception {
        Activity activity = Robolectric.buildActivity(MainActivity.class).create().get();

        LoginButton loginButton = (LoginButton) activity.findViewById(R.id.login_button);
        loginButton.setPublishPermissions("publish_actions");
        try {
            loginButton.setReadPermissions("user_location");
        } catch (UnsupportedOperationException e) {
            return;
        }
        fail();
    }
}


File: facebook/junitTests/src/test/java/com/facebook/messenger/MessengerUtilsTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook.messenger;

import android.app.Activity;
import android.content.ContentResolver;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.Bundle;

import com.facebook.FacebookSdk;

import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.ArgumentCaptor;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;

import java.util.Arrays;

import static org.junit.Assert.*;
import static org.junit.Assert.assertEquals;
import static org.mockito.Mockito.*;

/**
 * Tests for {@link com.facebook.messenger.MessengerUtils}
 */
@RunWith(RobolectricTestRunner.class)
@Config(emulateSdk = 18, manifest = Config.NONE)
public class MessengerUtilsTest {

  private Activity mMockActivity;
  private PackageManager mMockPackageManager;
  private ContentResolver mMockContentResolver;

  @Before
  public void setup() {
    mMockActivity = mock(Activity.class);
    mMockPackageManager = mock(PackageManager.class);
    mMockContentResolver = mock(ContentResolver.class);
    when(mMockActivity.getPackageManager()).thenReturn(mMockPackageManager);
    when(mMockActivity.getContentResolver()).thenReturn(mMockContentResolver);
    FacebookSdk.sdkInitialize(Robolectric.application);
    FacebookSdk.setApplicationId("200");
  }

  @Test
  public void testMessengerIsInstalled() throws Exception {
    setupPackageManagerForMessenger(true);
    assertTrue(MessengerUtils.hasMessengerInstalled(mMockActivity));
  }

  @Test
  public void testMessengerNotInstalled() throws Exception {
    setupPackageManagerForMessenger(false);
    assertFalse(MessengerUtils.hasMessengerInstalled(mMockActivity));
  }

  @Test
  public void testShareToMessengerWith20150314Protocol() throws Exception {
    setupPackageManagerForMessenger(true);
    setupContentResolverForProtocolVersions(20150314);


    Uri uri = Uri.parse("file:///foo.jpeg");
    Uri externalUri = Uri.parse("http://example.com/foo.jpeg");
    ShareToMessengerParams params = ShareToMessengerParams
        .newBuilder(uri, "image/jpeg")
        .setMetaData("{}")
        .setExternalUri(externalUri)
        .build();
    MessengerUtils.shareToMessenger(mMockActivity, 1, params);

    // Expect it to have launched messenger with the right intent.
    ArgumentCaptor<Intent> intentArgumentCaptor = ArgumentCaptor.forClass(Intent.class);
    verify(mMockActivity).startActivityForResult(
        intentArgumentCaptor.capture(),
        eq(1));
    Intent intent = intentArgumentCaptor.getValue();
    assertEquals(Intent.ACTION_SEND, intent.getAction());
    assertEquals(Intent.FLAG_GRANT_READ_URI_PERMISSION, intent.getFlags());
    assertEquals("com.facebook.orca", intent.getPackage());
    assertEquals(uri, intent.getParcelableExtra(Intent.EXTRA_STREAM));
    assertEquals("image/jpeg", intent.getType());
    assertEquals("200", intent.getStringExtra("com.facebook.orca.extra.APPLICATION_ID"));
    assertEquals(20150314, intent.getIntExtra("com.facebook.orca.extra.PROTOCOL_VERSION", -1));
    assertEquals("{}", intent.getStringExtra("com.facebook.orca.extra.METADATA"));
    assertEquals(externalUri, intent.getParcelableExtra("com.facebook.orca.extra.EXTERNAL_URI"));
  }

  @Test
  public void testShareToMessengerWithNoProtocol() throws Exception {
    setupPackageManagerForMessenger(true);
    setupContentResolverForProtocolVersions(/* empty */);

    Uri uri = Uri.parse("file:///foo.jpeg");
    Uri externalUri = Uri.parse("http://example.com/foo.jpeg");
    ShareToMessengerParams params = ShareToMessengerParams
        .newBuilder(uri, "image/jpeg")
        .setMetaData("{}")
        .setExternalUri(externalUri)
        .build();
    MessengerUtils.shareToMessenger(mMockActivity, 1, params);


    // Expect it to have gone to the play store.
    ArgumentCaptor<Intent> intentArgumentCaptor = ArgumentCaptor.forClass(Intent.class);
    verify(mMockActivity).startActivity(intentArgumentCaptor.capture());
    Intent intent = intentArgumentCaptor.getValue();
    assertEquals(Intent.ACTION_VIEW, intent.getAction());
    assertEquals(Uri.parse("market://details?id=com.facebook.orca"), intent.getData());
  }

  @Test
  public void testGetMessengerThreadParamsForIntentWith20150314Protocol() throws Exception {
    // Simulate an intent that Messenger would send.
    Intent intent = new Intent();
    intent.addCategory("com.facebook.orca.category.PLATFORM_THREAD_20150314");
    Bundle extrasBundle = setupIntentWithAppLinkExtrasBundle(intent);
    extrasBundle.putString("com.facebook.orca.extra.THREAD_TOKEN", "thread_token");
    extrasBundle.putString("com.facebook.orca.extra.METADATA", "{}");
    extrasBundle.putString("com.facebook.orca.extra.PARTICIPANTS", "100,400,500");
    extrasBundle.putBoolean("com.facebook.orca.extra.IS_REPLY", true);

    // Check the parsing logic.
    MessengerThreadParams params = MessengerUtils.getMessengerThreadParamsForIntent(intent);
    assertEquals(MessengerThreadParams.Origin.REPLY_FLOW, params.origin);
    assertEquals("thread_token", params.threadToken);
    assertEquals("{}", params.metadata);
    assertEquals(Arrays.asList("100", "400", "500"), params.participants);
  }

  @Test
  public void testGetMessengerThreadParamsForIntentWithUnrecognizedIntent() throws Exception {
    // Simulate an intent that Messenger would send.
    Intent intent = new Intent();
    assertNull(MessengerUtils.getMessengerThreadParamsForIntent(intent));
  }

  @Test
  public void testFinishShareToMessengerWith20150314Protocol() throws Exception {
    // Simulate an intent that Messenger would send.
    Intent originalIntent = new Intent();
    originalIntent.addCategory("com.facebook.orca.category.PLATFORM_THREAD_20150314");
    Bundle extrasBundle = setupIntentWithAppLinkExtrasBundle(originalIntent);
    extrasBundle.putString("com.facebook.orca.extra.THREAD_TOKEN", "thread_token");
    extrasBundle.putString("com.facebook.orca.extra.METADATA", "{}");
    extrasBundle.putString("com.facebook.orca.extra.PARTICIPANTS", "100,400,500");
    when(mMockActivity.getIntent()).thenReturn(originalIntent);

    // Setup the data the app will send back to messenger.
    Uri uri = Uri.parse("file:///foo.jpeg");
    Uri externalUri = Uri.parse("http://example.com/foo.jpeg");
    ShareToMessengerParams params = ShareToMessengerParams
        .newBuilder(uri, "image/jpeg")
        .setMetaData("{}")
        .setExternalUri(externalUri)
        .build();

    // Call finishShareToMessenger and verify the results.
    MessengerUtils.finishShareToMessenger(mMockActivity, params);
    ArgumentCaptor<Intent> intentArgumentCaptor = ArgumentCaptor.forClass(Intent.class);
    verify(mMockActivity).setResult(eq(Activity.RESULT_OK), intentArgumentCaptor.capture());
    verify(mMockActivity).finish();

    Intent intent = intentArgumentCaptor.getValue();
    assertNotNull(intent);
    assertEquals(Intent.FLAG_GRANT_READ_URI_PERMISSION, intent.getFlags());
    assertEquals(20150314, intent.getIntExtra("com.facebook.orca.extra.PROTOCOL_VERSION", -1));
    assertEquals("thread_token", intent.getStringExtra("com.facebook.orca.extra.THREAD_TOKEN"));
    assertEquals(uri, intent.getData());
    assertEquals("image/jpeg", intent.getType());
    assertEquals("200", intent.getStringExtra("com.facebook.orca.extra.APPLICATION_ID"));
    assertEquals("{}", intent.getStringExtra("com.facebook.orca.extra.METADATA"));
    assertEquals(externalUri, intent.getParcelableExtra("com.facebook.orca.extra.EXTERNAL_URI"));
  }

  @Test
  public void testFinishShareToMessengerWithUnexpectedIntent() throws Exception {
    // Simulate an intent that Messenger would send.
    Intent originalIntent = new Intent();
    when(mMockActivity.getIntent()).thenReturn(originalIntent);

    // Setup the data the app will send back to messenger.
    Uri uri = Uri.parse("file:///foo.jpeg");
    Uri externalUri = Uri.parse("http://example.com/foo.jpeg");
    ShareToMessengerParams params = ShareToMessengerParams
        .newBuilder(uri, "image/jpeg")
        .setMetaData("{}")
        .setExternalUri(externalUri)
        .build();

    // Call finishShareToMessenger and verify the results.
    MessengerUtils.finishShareToMessenger(mMockActivity, params);
    verify(mMockActivity).setResult(Activity.RESULT_CANCELED, null);
    verify(mMockActivity).finish();
  }

  /**
   * Sets up the PackageManager to return what we expect depending on whether messenger is
   * installed.
   *
   * @param isInstalled true to simulate that messenger is installed
   */
  private void setupPackageManagerForMessenger(boolean isInstalled) throws Exception {
    if (isInstalled) {
      when(mMockPackageManager.getPackageInfo("com.facebook.orca", 0))
          .thenReturn(new PackageInfo());
    } else {
      when(mMockPackageManager.getPackageInfo("com.facebook.orca", 0))
          .thenThrow(new PackageManager.NameNotFoundException());
    }
  }

  /**
   * Sets up the Messenger content resolver to reply that it supports the specified versions.
   *
   * @param versions the versions that it should support
   */
  private void setupContentResolverForProtocolVersions(int... versions) {
    MatrixCursor matrixCursor = new MatrixCursor(new String[]{"version"});
    for (int version : versions) {
      matrixCursor.addRow(new Object[]{version});
    }

    when(mMockContentResolver.query(
        Uri.parse("content://com.facebook.orca.provider.MessengerPlatformProvider/versions"),
        new String[]{"version"},
        null,
        null,
        null))
        .thenReturn(matrixCursor);
  }

  /**
   * Adds the structure to the Intent to look like an app link and returns the Extras section
   * which is where the messenger parameters go.
   *
   * @param intent the intent to add to
   * @return the extras Bundle
   */
  private Bundle setupIntentWithAppLinkExtrasBundle(Intent intent) {
    Bundle appLinksDataBundle = new Bundle();
    intent.putExtra("al_applink_data", appLinksDataBundle);
    Bundle extrasBundle = new Bundle();
    appLinksDataBundle.putBundle("extras", extrasBundle);
    return extrasBundle;
  }

}


File: facebook/junitTests/src/test/java/com/facebook/share/internal/ShareOpenGraphUtilityTest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook.share.internal;

import com.facebook.FacebookTestCase;
import com.facebook.TestUtils;
import com.facebook.share.model.ShareOpenGraphAction;
import com.facebook.share.model.ShareOpenGraphObject;

import org.apache.maven.artifact.ant.shaded.IOUtil;
import org.json.JSONException;
import org.json.JSONObject;
import org.junit.Test;
import org.robolectric.Robolectric;
import org.robolectric.util.RobolectricBackgroundExecutorService;

import java.io.IOException;
import java.net.URL;
import java.util.ArrayList;

import static junit.framework.Assert.assertNotNull;

public class ShareOpenGraphUtilityTest extends FacebookTestCase {
    private static final String TYPE_KEY = "type";

    @Test
    public void testToJSONObject() throws IOException, JSONException {
        final JSONObject actual = OpenGraphJSONUtility.toJSONObject(this.getAction(), null);
        final JSONObject expected = this.getActionJSONObject();
        TestUtils.assertEquals(expected, actual);
    }

    private static <E> ArrayList<E> createArrayList(E... params) {
        final ArrayList<E> list = new ArrayList<E>();
        for (E item : params) {
            list.add(item);
        }
        return list;
    }

    private ShareOpenGraphAction getAction() {
        return new ShareOpenGraphAction.Builder()
                .putString(TYPE_KEY, "myActionType")
                .putObject(
                        "myObject",
                        new ShareOpenGraphObject.Builder()
                                .putString("myString", "value")
                                .putInt("myInt", 42)
                                .putBoolean("myBoolean", true)
                                .putStringArrayList(
                                        "myStringArray",
                                        createArrayList(
                                                "string1",
                                                "string2",
                                                "string3")
                                )
                                .putObject(
                                        "myObject",
                                        new ShareOpenGraphObject.Builder()
                                                .putDouble("myPi", 3.14)
                                                .build()
                                )
                                .build()).build();
    }

    private JSONObject getActionJSONObject() throws IOException, JSONException {
        return new JSONObject(this.getActionJSONString());
    }

    private String getActionJSONString() throws IOException {
        return TestUtils.getAssetFileStringContents(
                Robolectric.getShadowApplication().getApplicationContext(),
                "ShareOpenGraphUtilityTests_actionJSON.json"
        );
    }
}


File: facebook/src/com/facebook/FacebookSdk.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook;

import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.os.AsyncTask;
import android.util.Base64;
import android.util.Log;

import com.facebook.appevents.AppEventsLogger;
import com.facebook.internal.AppEventsLoggerUtility;
import com.facebook.internal.BoltsMeasurementEventListener;
import com.facebook.internal.AttributionIdentifiers;
import com.facebook.internal.NativeProtocol;
import com.facebook.internal.Utility;
import com.facebook.internal.Validate;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.lang.reflect.Field;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

/**
 * This class allows some customization of Facebook SDK behavior.
 */
public final class FacebookSdk {
    private static final String TAG = FacebookSdk.class.getCanonicalName();
    private static final HashSet<LoggingBehavior> loggingBehaviors =
            new HashSet<LoggingBehavior>(Arrays.asList(LoggingBehavior.DEVELOPER_ERRORS));
    private static volatile Executor executor;
    private static volatile String applicationId;
    private static volatile String applicationName;
    private static volatile String appClientToken;
    private static volatile int webDialogTheme;
    private static final String FACEBOOK_COM = "facebook.com";
    private static volatile String facebookDomain = FACEBOOK_COM;
    private static AtomicLong onProgressThreshold = new AtomicLong(65536);
    private static volatile boolean isDebugEnabled = BuildConfig.DEBUG;
    private static boolean isLegacyTokenUpgradeSupported = false;
    private static File cacheDir;
    private static Context applicationContext;
    private static final int DEFAULT_CORE_POOL_SIZE = 5;
    private static final int DEFAULT_MAXIMUM_POOL_SIZE = 128;
    private static final int DEFAULT_KEEP_ALIVE = 1;
    private static int callbackRequestCodeOffset = 0xface;
    private static final Object LOCK = new Object();

    private static final int MAX_REQUEST_CODE_RANGE = 100;

    private static final String ATTRIBUTION_PREFERENCES = "com.facebook.sdk.attributionTracking";
    private static final String PUBLISH_ACTIVITY_PATH = "%s/activities";

    private static final BlockingQueue<Runnable> DEFAULT_WORK_QUEUE =
            new LinkedBlockingQueue<Runnable>(10);

    private static final ThreadFactory DEFAULT_THREAD_FACTORY = new ThreadFactory() {
        private final AtomicInteger counter = new AtomicInteger(0);

        public Thread newThread(Runnable runnable) {
            return new Thread(runnable, "FacebookSdk #" + counter.incrementAndGet());
        }
    };

    static final String CALLBACK_OFFSET_CHANGED_AFTER_INIT =
            "The callback request code offset can't be updated once the SDK is initialized.";

    static final String CALLBACK_OFFSET_NEGATIVE =
            "The callback request code offset can't be negative.";


    /**
     * The key for the application ID in the Android manifest.
     */
    public static final String APPLICATION_ID_PROPERTY = "com.facebook.sdk.ApplicationId";

    /**
     * The key for the application name in the Android manifest.
     */
    public static final String APPLICATION_NAME_PROPERTY = "com.facebook.sdk.ApplicationName";

    /**
     * The key for the client token in the Android manifest.
     */
    public static final String CLIENT_TOKEN_PROPERTY = "com.facebook.sdk.ClientToken";

    /**
     * The key for the web dialog theme in the Android manifest.
     */
    public static final String WEB_DIALOG_THEME = "com.facebook.sdk.WebDialogTheme";

    private static Boolean sdkInitialized = false;

    /**
     * This function initializes the Facebook SDK, the behavior of Facebook SDK functions are
     * undetermined if this function is not called. It should be called as early as possible.
     * @param applicationContext The application context
     * @param callbackRequestCodeOffset The request code offset that Facebook activities will be
     *                                  called with. Please do not use the range between the
     *                                  value you set and another 100 entries after it in your
     *                                  other requests.
     */
    public static synchronized void sdkInitialize(
            Context applicationContext,
            int callbackRequestCodeOffset) {
        if (sdkInitialized && callbackRequestCodeOffset != FacebookSdk.callbackRequestCodeOffset) {
            throw new FacebookException(CALLBACK_OFFSET_CHANGED_AFTER_INIT);
        }
        if (callbackRequestCodeOffset < 0) {
            throw new FacebookException(CALLBACK_OFFSET_NEGATIVE);
        }
        FacebookSdk.callbackRequestCodeOffset = callbackRequestCodeOffset;
        sdkInitialize(applicationContext);
    }


    /**
     * This function initializes the Facebook SDK, the behavior of Facebook SDK functions are
     * undetermined if this function is not called. It should be called as early as possible.
     * @param applicationContext The application context
     */
    public static synchronized void sdkInitialize(Context applicationContext) {
        if (sdkInitialized == true) {
          return;
        }

        Validate.notNull(applicationContext, "applicationContext");

        // Don't throw for these validations here, just log an error. We'll throw when we actually
        // need them
        Validate.hasFacebookActivity(applicationContext, false);
        Validate.hasInternetPermissions(applicationContext, false);

        FacebookSdk.applicationContext = applicationContext.getApplicationContext();

        // Make sure we've loaded default settings if we haven't already.
        FacebookSdk.loadDefaultsFromMetadata(FacebookSdk.applicationContext);
        // Load app settings from network so that dialog configs are available
        Utility.loadAppSettingsAsync(FacebookSdk.applicationContext, applicationId);
        // Fetch available protocol versions from the apps on the device
        NativeProtocol.updateAllAvailableProtocolVersionsAsync();

        BoltsMeasurementEventListener.getInstance(FacebookSdk.applicationContext);

        cacheDir = FacebookSdk.applicationContext.getCacheDir();

        FutureTask<Void> accessTokenLoadFutureTask =
                new FutureTask<Void>(new Callable<Void>() {
                    @Override
                    public Void call() throws Exception {
                        AccessTokenManager.getInstance().loadCurrentAccessToken();
                        ProfileManager.getInstance().loadCurrentProfile();
                        if (AccessToken.getCurrentAccessToken() != null &&
                                Profile.getCurrentProfile() == null) {
                            // Access token and profile went out of sync due to a network or caching
                            // issue, retry
                            Profile.fetchProfileForCurrentAccessToken();
                        }
                        return null;
                    }
                });
        getExecutor().execute(accessTokenLoadFutureTask);

        sdkInitialized = true;
    }

    /**
     * Indicates whether the Facebook SDK has been initialized.
     * @return true if initialized, false if not
     */
    public static synchronized boolean isInitialized() {
        return sdkInitialized;
    }

    /**
     * Certain logging behaviors are available for debugging beyond those that should be
     * enabled in production.
     *
     * Returns the types of extended logging that are currently enabled.
     *
     * @return a set containing enabled logging behaviors
     */
    public static Set<LoggingBehavior> getLoggingBehaviors() {
        synchronized (loggingBehaviors) {
            return Collections.unmodifiableSet(new HashSet<LoggingBehavior>(loggingBehaviors));
        }
    }

    /**
     * Certain logging behaviors are available for debugging beyond those that should be
     * enabled in production.
     *
     * Enables a particular extended logging in the SDK.
     *
     * @param behavior
     *          The LoggingBehavior to enable
     */
    public static void addLoggingBehavior(LoggingBehavior behavior) {
        synchronized (loggingBehaviors) {
            loggingBehaviors.add(behavior);
            updateGraphDebugBehavior();
        }
    }

    /**
     * Certain logging behaviors are available for debugging beyond those that should be
     * enabled in production.
     *
     * Disables a particular extended logging behavior in the SDK.
     *
     * @param behavior
     *          The LoggingBehavior to disable
     */
    public static void removeLoggingBehavior(LoggingBehavior behavior) {
        synchronized (loggingBehaviors) {
            loggingBehaviors.remove(behavior);
        }
    }

    /**
     * Certain logging behaviors are available for debugging beyond those that should be
     * enabled in production.
     *
     * Disables all extended logging behaviors.
     */
    public static void clearLoggingBehaviors() {
        synchronized (loggingBehaviors) {
            loggingBehaviors.clear();
        }
    }

    /**
     * Certain logging behaviors are available for debugging beyond those that should be
     * enabled in production.
     *
     * Checks if a particular extended logging behavior is enabled.
     *
     * @param behavior
     *          The LoggingBehavior to check
     * @return whether behavior is enabled
     */
    public static boolean isLoggingBehaviorEnabled(LoggingBehavior behavior) {
        synchronized (loggingBehaviors) {
            return FacebookSdk.isDebugEnabled() && loggingBehaviors.contains(behavior);
        }
    }

    /**
     * Indicates if we are in debug mode.
     */
    public static boolean isDebugEnabled() {
        return isDebugEnabled;
    }

    /**
     * Used to enable or disable logging, and other debug features. Defaults to BuildConfig.DEBUG.
     * @param enabled Debug features (like logging) are enabled if true, disabled if false.
     */
    public static void setIsDebugEnabled(boolean enabled) {
        isDebugEnabled = enabled;
    }

    /**
     * Indicates if the SDK should fallback and read the legacy token. This is turned off by default
     * for performance.
     * @return if the legacy token upgrade is supported.
     */
    public static boolean isLegacyTokenUpgradeSupported() {
        return isLegacyTokenUpgradeSupported;
    }

    private static void updateGraphDebugBehavior() {
        if (loggingBehaviors.contains(LoggingBehavior.GRAPH_API_DEBUG_INFO)
           && !loggingBehaviors.contains(LoggingBehavior.GRAPH_API_DEBUG_WARNING)) {
            loggingBehaviors.add(LoggingBehavior.GRAPH_API_DEBUG_WARNING);
        }
    }

    /**
     * Setter for legacy token upgrade.
     * @param supported True if upgrade should be supported.
     */
    public static void setLegacyTokenUpgradeSupported(boolean supported) {
        isLegacyTokenUpgradeSupported = supported;
    }

    /**
     * Returns the Executor used by the SDK for non-AsyncTask background work.
     *
     * By default this uses AsyncTask Executor via reflection if the API level is high enough.
     * Otherwise this creates a new Executor with defaults similar to those used in AsyncTask.
     *
     * @return an Executor used by the SDK.  This will never be null.
     */
    public static Executor getExecutor() {
        synchronized (LOCK) {
            if (FacebookSdk.executor == null) {
                Executor executor = getAsyncTaskExecutor();
                if (executor == null) {
                    executor = new ThreadPoolExecutor(
                            DEFAULT_CORE_POOL_SIZE, DEFAULT_MAXIMUM_POOL_SIZE, DEFAULT_KEEP_ALIVE,
                            TimeUnit.SECONDS, DEFAULT_WORK_QUEUE, DEFAULT_THREAD_FACTORY);
                }
                FacebookSdk.executor = executor;
            }
        }
        return FacebookSdk.executor;
    }

    /**
     * Sets the Executor used by the SDK for non-AsyncTask background work.
     *
     * @param executor
     *          the Executor to use; must not be null.
     */
    public static void setExecutor(Executor executor) {
        Validate.notNull(executor, "executor");
        synchronized (LOCK) {
            FacebookSdk.executor = executor;
        }
    }

    /**
     * Gets the base Facebook domain to use when making Web requests; in production code this will
     * always be "facebook.com".
     *
     * @return the Facebook domain
     */
    public static String getFacebookDomain() {
        return facebookDomain;
    }

    /**
     * Sets the base Facebook domain to use when making Web requests. This defaults to
     * "facebook.com", but may be overridden to, e.g., "beta.facebook.com" to direct requests at a
     * different domain. This method should never be called from production code.
     *
     * @param facebookDomain the base domain to use instead of "facebook.com"
     */
    public static void setFacebookDomain(String facebookDomain) {
        if (!BuildConfig.DEBUG) {
            Log.w(TAG, "WARNING: Calling setFacebookDomain from non-DEBUG code.");
        }

        FacebookSdk.facebookDomain = facebookDomain;
    }

    /**
     * The getter for the context of the current application.
     * @return The context of the current application.
     */
    public static Context getApplicationContext() {
        Validate.sdkInitialized();
        return applicationContext;
    }

    private static Executor getAsyncTaskExecutor() {
        Field executorField = null;
        try {
            executorField = AsyncTask.class.getField("THREAD_POOL_EXECUTOR");
        } catch (NoSuchFieldException e) {
            return null;
        }

        Object executorObject = null;
        try {
            executorObject = executorField.get(null);
        } catch (IllegalAccessException e) {
            return null;
        }

        if (executorObject == null) {
            return null;
        }

        if (!(executorObject instanceof Executor)) {
            return null;
        }

        return (Executor) executorObject;
    }

    /**
     * This method is public in order to be used by app events, please don't use directly.
     * @param context       The application context.
     * @param applicationId The application id.
     */
    public static void publishInstallAsync(final Context context, final String applicationId) {
        // grab the application context ahead of time, since we will return to the caller
        // immediately.
        final Context applicationContext = context.getApplicationContext();
        FacebookSdk.getExecutor().execute(new Runnable() {
            @Override
            public void run() {
                FacebookSdk.publishInstallAndWaitForResponse(applicationContext, applicationId);
            }
        });
    }

    static GraphResponse publishInstallAndWaitForResponse(
            final Context context,
            final String applicationId) {
        try {
            if (context == null || applicationId == null) {
                throw new IllegalArgumentException("Both context and applicationId must be non-null");
            }
            AttributionIdentifiers identifiers = AttributionIdentifiers.getAttributionIdentifiers(context);
            SharedPreferences preferences = context.getSharedPreferences(ATTRIBUTION_PREFERENCES, Context.MODE_PRIVATE);
            String pingKey = applicationId+"ping";
            String jsonKey = applicationId+"json";
            long lastPing = preferences.getLong(pingKey, 0);
            String lastResponseJSON = preferences.getString(jsonKey, null);

            JSONObject publishParams;
            try {
                publishParams = AppEventsLoggerUtility.getJSONObjectForGraphAPICall(
                        AppEventsLoggerUtility.GraphAPIActivityType.MOBILE_INSTALL_EVENT,
                        identifiers,
                        AppEventsLogger.getAnonymousAppDeviceGUID(context),
                        getLimitEventAndDataUsage(context),
                        context);
            } catch (JSONException e) {
                throw new FacebookException("An error occurred while publishing install.", e);
            }

            String publishUrl = String.format(PUBLISH_ACTIVITY_PATH, applicationId);
            GraphRequest publishRequest = GraphRequest.newPostRequest(null, publishUrl, publishParams, null);

            if (lastPing != 0) {
                JSONObject graphObject = null;
                try {
                    if (lastResponseJSON != null) {
                        graphObject = new JSONObject(lastResponseJSON);
                    }
                }
                catch (JSONException je) {
                    // return the default graph object if there is any problem reading the data.
                }
                if (graphObject == null) {
                    return GraphResponse.createResponsesFromString(
                            "true",
                            null,
                            new GraphRequestBatch(publishRequest)
                    ).get(0);
                } else {
                    return new GraphResponse(null, null, null, graphObject);
                }

            } else {

                GraphResponse publishResponse = publishRequest.executeAndWait();

                // denote success since no error threw from the post.
                SharedPreferences.Editor editor = preferences.edit();
                lastPing = System.currentTimeMillis();
                editor.putLong(pingKey, lastPing);

                // if we got an object response back, cache the string of the JSON.
                if (publishResponse.getJSONObject() != null) {
                    editor.putString(jsonKey, publishResponse.getJSONObject().toString());
                }
                editor.apply();

                return publishResponse;
            }
        } catch (Exception e) {
            // if there was an error, fall through to the failure case.
            Utility.logd("Facebook-publish", e);
            return new GraphResponse(null, null, new FacebookRequestError(null, e));
        }
    }

    /**
     * Returns the current version of the Facebook SDK for Android as a string.
     *
     * @return the current version of the SDK
     */
    public static String getSdkVersion() {
        Validate.sdkInitialized();
        return FacebookSdkVersion.BUILD;
    }

    /**
     * Returns whether data such as those generated through AppEventsLogger and sent to Facebook
     * should be restricted from being used for purposes other than analytics and conversions, such
     * as targeting ads to this user.  Defaults to false.  This value is stored on the device and
     * persists across app launches.
     *
     * @param context  Used to read the value.
     */
    public static boolean getLimitEventAndDataUsage(Context context) {
        Validate.sdkInitialized();
        SharedPreferences preferences = context.getSharedPreferences(
                AppEventsLogger.APP_EVENT_PREFERENCES, Context.MODE_PRIVATE);
        return preferences.getBoolean("limitEventUsage", false);
    }

    /**
     * Sets whether data such as those generated through AppEventsLogger and sent to Facebook should
     * be restricted from being used for purposes other than analytics and conversions, such as
     * targeting ads to this user.  Defaults to false.  This value is stored on the device and
     * persists across app launches.  Changes to this setting will apply to app events currently
     * queued to be flushed.
     *
     * @param context Used to persist this value across app runs.
     */
    public static void setLimitEventAndDataUsage(Context context, boolean limitEventUsage) {
        context.getSharedPreferences(AppEventsLogger.APP_EVENT_PREFERENCES, Context.MODE_PRIVATE)
            .edit()
            .putBoolean("limitEventUsage", limitEventUsage)
            .apply();
    }

    /**
     * Gets the threshold used to report progress on requests.
     */
    public static long getOnProgressThreshold() {
        Validate.sdkInitialized();
        return onProgressThreshold.get();
    }

    /**
     * Sets the threshold used to report progress on requests. Note that the value will be read when
     * the request is started and cannot be changed during a request (or batch) execution.
     *
     * @param threshold The number of bytes progressed to force a callback.
     */
    public static void setOnProgressThreshold(long threshold) {
        onProgressThreshold.set(threshold);
    }

    // Package private for testing only
    static void loadDefaultsFromMetadata(Context context) {
        if (context == null) {
            return;
        }

        ApplicationInfo ai = null;
        try {
            ai = context.getPackageManager().getApplicationInfo(
                    context.getPackageName(), PackageManager.GET_META_DATA);
        } catch (PackageManager.NameNotFoundException e) {
            return;
        }

        if (ai == null || ai.metaData == null) {
            return;
        }

        if (applicationId == null) {
            Object appId = ai.metaData.get(APPLICATION_ID_PROPERTY);
            if (appId instanceof String) {
                applicationId = (String) appId;
            } else if (appId instanceof Integer) {
                applicationId = appId.toString();
            }
        }

        if (applicationName == null) {
            applicationName = ai.metaData.getString(APPLICATION_NAME_PROPERTY);
        }

        if (appClientToken == null) {
            appClientToken = ai.metaData.getString(CLIENT_TOKEN_PROPERTY);
        }

        if (webDialogTheme == 0) {
            setWebDialogTheme(ai.metaData.getInt(WEB_DIALOG_THEME));
        }
    }

    /**
     * Internal call please don't use directly.
     * @param context The application context.
     * @return The application signature.
     */
    public static String getApplicationSignature(Context context) {
        Validate.sdkInitialized();
        if (context == null) {
            return null;
        }
        PackageManager packageManager = context.getPackageManager();
        if (packageManager == null) {
            return null;
        }

        String packageName = context.getPackageName();
        PackageInfo pInfo;
        try {
            pInfo = packageManager.getPackageInfo(packageName, PackageManager.GET_SIGNATURES);
        } catch (PackageManager.NameNotFoundException e) {
            return null;
        }

        Signature[] signatures = pInfo.signatures;
        if (signatures == null || signatures.length == 0) {
            return null;
        }

        MessageDigest md;
        try {
            md = MessageDigest.getInstance("SHA-1");
        } catch (NoSuchAlgorithmException e) {
            return null;
        }

        md.update(pInfo.signatures[0].toByteArray());
        return Base64.encodeToString(md.digest(),  Base64.URL_SAFE | Base64.NO_PADDING);
    }

    /**
     * Gets the Facebook application ID for the current app. This should only be called after the
     * SDK has been initialized by calling FacebookSdk.sdkInitialize().
     *
     * @return the application ID
     */
    public static String getApplicationId() {
        Validate.sdkInitialized();
        return applicationId;
    }

    /**
     * Sets the Facebook application ID for the current app.
     * @param applicationId the application ID
     */
    public static void setApplicationId(String applicationId) {
        FacebookSdk.applicationId = applicationId;
    }

    /**
     * Gets the Facebook application name of the current app. This should only be called after the
     * SDK has been initialized by calling FacebookSdk.sdkInitialize().
     *
     * @return the application name
     */
    public static String getApplicationName() {
        Validate.sdkInitialized();
        return applicationName;
    }

    /**
     * Sets the Facebook application name for the current app.
     * @param applicationName the application name
     */
    public static void setApplicationName(String applicationName) {
        FacebookSdk.applicationName = applicationName;
    }

    /**
     * Gets the client token for the current app. This will be null unless explicitly set or unless
     * loadDefaultsFromMetadata has been called.
     * @return the client token
     */
    public static String getClientToken() {
        Validate.sdkInitialized();
        return appClientToken;
    }

    /**
     * Sets the Facebook client token for the current app.
     * @param clientToken the client token
     */
    public static void setClientToken(String clientToken) {
        appClientToken = clientToken;
    }

    /**
     * Gets the theme used by {@link com.facebook.internal.WebDialog}
     * @return the theme
     */
    public static int getWebDialogTheme() {
        Validate.sdkInitialized();
        return webDialogTheme;
    }

    /**
     * Sets the theme used by {@link com.facebook.internal.WebDialog}
     * @param theme A theme to use
     */
    public static void setWebDialogTheme(int theme) {
        webDialogTheme = theme;
    }

    /**
     * Gets the cache directory to use for caching responses, etc. The default will be the value
     * returned by Context.getCacheDir() when the SDK was initialized, but it can be overridden.
     *
     * @return the cache directory
     */
    public static File getCacheDir() {
        Validate.sdkInitialized();
        return cacheDir;
    }

    /**
     * Sets the cache directory to use for caching responses, etc.
     * @param cacheDir the cache directory
     */
    public static void setCacheDir(File cacheDir) {
        FacebookSdk.cacheDir = cacheDir;
    }

    /**
     * Getter for the callback request code offset. The request codes starting at this offset and
     * the next 100 values are used by the Facebook SDK.
     *
     * @return The callback request code offset.
     */
    public static int getCallbackRequestCodeOffset() {
        Validate.sdkInitialized();
        return callbackRequestCodeOffset;
    }

    /**
     * Returns true if the request code is within the range used by Facebook SDK requests. This does
     * not include request codes that you explicitly set on the dialogs, buttons or LoginManager.
     * The range of request codes that the SDK uses starts at the callbackRequestCodeOffset and
     * continues for the next 100 values.
     *
     * @param requestCode the request code to check.
     * @return true if the request code is within the range used by the Facebook SDK.
     */
    public static boolean isFacebookRequestCode(int requestCode) {
        return requestCode >= callbackRequestCodeOffset
                && requestCode < callbackRequestCodeOffset + MAX_REQUEST_CODE_RANGE;
    }
}


File: facebook/src/com/facebook/FacebookSdkVersion.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook;

final class FacebookSdkVersion {
    public static final String BUILD = "4.2.0";
}


File: facebook/src/com/facebook/GraphRequest.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook;

import android.content.Context;
import android.graphics.Bitmap;
import android.location.Location;
import android.net.Uri;
import android.os.*;
import android.text.TextUtils;
import android.util.Log;
import android.util.Pair;

import com.facebook.internal.*;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.URL;
import java.net.URLEncoder;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.GZIPOutputStream;

/**
 * <p>
 * A single request to be sent to the Facebook Platform through the <a
 * href="https://developers.facebook.com/docs/reference/api/">Graph API</a>. The Request class
 * provides functionality relating to serializing and deserializing requests and responses, making
 * calls in batches (with a single round-trip to the service) and making calls asynchronously.
 * </p>
 * <p>
 * The particular service endpoint that a request targets is determined by a graph path (see the
 * {@link #setGraphPath(String) setGraphPath} method).
 * </p>
 * <p>
 * A Request can be executed either anonymously or representing an authenticated user. In the former
 * case, no AccessToken needs to be specified, while in the latter, an AccessToken must be provided.
 * If requests are executed in a batch, a Facebook application ID must be associated with the batch,
 * either by setting the application ID in the AndroidManifest.xml or via FacebookSdk or by calling
 * the {@link #setDefaultBatchApplicationId(String) setDefaultBatchApplicationId} method.
 * </p>
 * <p>
 * After completion of a request, the AccessToken, if not null and taken from AccessTokenManager,
 * will be checked to determine if its Facebook access token needs to be extended; if so, a request
 * to extend it will be issued in the background.
 * </p>
 */
public class GraphRequest {
    /**
     * The maximum number of requests that can be submitted in a single batch. This limit is
     * enforced on the service side by the Facebook platform, not by the Request class.
     */
    public static final int MAXIMUM_BATCH_SIZE = 50;

    public static final String TAG = GraphRequest.class.getSimpleName();

    private static final String VIDEOS_SUFFIX = "/videos";
    private static final String ME = "me";
    private static final String MY_FRIENDS = "me/friends";
    private static final String SEARCH = "search";
    private static final String USER_AGENT_BASE = "FBAndroidSDK";
    private static final String USER_AGENT_HEADER = "User-Agent";
    private static final String CONTENT_TYPE_HEADER = "Content-Type";
    private static final String ACCEPT_LANGUAGE_HEADER = "Accept-Language";
    private static final String CONTENT_ENCODING_HEADER = "Content-Encoding";

    // Parameter names/values
    private static final String FORMAT_PARAM = "format";
    private static final String FORMAT_JSON = "json";
    private static final String SDK_PARAM = "sdk";
    private static final String SDK_ANDROID = "android";
    private static final String ACCESS_TOKEN_PARAM = "access_token";
    private static final String BATCH_ENTRY_NAME_PARAM = "name";
    private static final String BATCH_ENTRY_OMIT_RESPONSE_ON_SUCCESS_PARAM =
            "omit_response_on_success";
    private static final String BATCH_ENTRY_DEPENDS_ON_PARAM = "depends_on";
    private static final String BATCH_APP_ID_PARAM = "batch_app_id";
    private static final String BATCH_RELATIVE_URL_PARAM = "relative_url";
    private static final String BATCH_BODY_PARAM = "body";
    private static final String BATCH_METHOD_PARAM = "method";
    private static final String BATCH_PARAM = "batch";
    private static final String ATTACHMENT_FILENAME_PREFIX = "file";
    private static final String ATTACHED_FILES_PARAM = "attached_files";
    private static final String ISO_8601_FORMAT_STRING = "yyyy-MM-dd'T'HH:mm:ssZ";
    private static final String DEBUG_PARAM = "debug";
    private static final String DEBUG_SEVERITY_INFO = "info";
    private static final String DEBUG_SEVERITY_WARNING = "warning";
    private static final String DEBUG_KEY = "__debug__";
    private static final String DEBUG_MESSAGES_KEY = "messages";
    private static final String DEBUG_MESSAGE_KEY = "message";
    private static final String DEBUG_MESSAGE_TYPE_KEY = "type";
    private static final String DEBUG_MESSAGE_LINK_KEY = "link";

    private static final String MIME_BOUNDARY = "3i2ndDfv2rTHiSisAbouNdArYfORhtTPEefj3q2f";

    private static String defaultBatchApplicationId;

    // Group 1 in the pattern is the path without the version info
    private static Pattern versionPattern = Pattern.compile("^/?v\\d+\\.\\d+/(.*)");

    private AccessToken accessToken;
    private HttpMethod httpMethod;
    private String graphPath;
    private JSONObject graphObject;
    private String batchEntryName;
    private String batchEntryDependsOn;
    private boolean batchEntryOmitResultOnSuccess = true;
    private Bundle parameters;
    private Callback callback;
    private String overriddenURL;
    private Object tag;
    private String version;
    private boolean skipClientToken = false;

    /**
     * Constructs a request without an access token, graph path, or any other parameters.
     */
    public GraphRequest() {
        this(null, null, null, null, null);
    }

    /**
     * Constructs a request with an access token to retrieve a particular graph path.
     * An access token need not be provided, in which case the request is sent without an access
     * token and thus is not executed in the context of any particular user. Only certain graph
     * requests can be expected to succeed in this case.
     *
     * @param accessToken the access token to use, or null
     * @param graphPath   the graph path to retrieve
     */
    public GraphRequest(AccessToken accessToken, String graphPath) {
        this(accessToken, graphPath, null, null, null);
    }

    /**
     * Constructs a request with a specific AccessToken, graph path, parameters, and HTTP method. An
     * access token need not be provided, in which case the request is sent without an access token
     * and thus is not executed in the context of any particular user. Only certain graph requests
     * can be expected to succeed in this case.
     * <p/>
     * Depending on the httpMethod parameter, the object at the graph path may be retrieved,
     * created, or deleted.
     *
     * @param accessToken the access token to use, or null
     * @param graphPath   the graph path to retrieve, create, or delete
     * @param parameters  additional parameters to pass along with the Graph API request; parameters
     *                    must be Strings, Numbers, Bitmaps, Dates, or Byte arrays.
     * @param httpMethod  the {@link HttpMethod} to use for the request, or null for default
     *                    (HttpMethod.GET)
     */
    public GraphRequest(
            AccessToken accessToken,
            String graphPath,
            Bundle parameters,
            HttpMethod httpMethod) {
        this(accessToken, graphPath, parameters, httpMethod, null);
    }

    /**
     * Constructs a request with a specific access token, graph path, parameters, and HTTP method.
     * An access token need not be provided, in which case the request is sent without an access
     * token and thus is not executed in the context of any particular user. Only certain graph
     * requests can be expected to succeed in this case.
     * <p/>
     * Depending on the httpMethod parameter, the object at the graph path may be retrieved,
     * created, or deleted.
     *
     * @param accessToken the access token to use, or null
     * @param graphPath   the graph path to retrieve, create, or delete
     * @param parameters  additional parameters to pass along with the Graph API request; parameters
     *                    must be Strings, Numbers, Bitmaps, Dates, or Byte arrays.
     * @param httpMethod  the {@link HttpMethod} to use for the request, or null for default
     *                    (HttpMethod.GET)
     * @param callback    a callback that will be called when the request is completed to handle
     *                    success or error conditions
     */
    public GraphRequest(
            AccessToken accessToken,
            String graphPath,
            Bundle parameters,
            HttpMethod httpMethod,
            Callback callback) {
        this(accessToken, graphPath, parameters, httpMethod, callback, null);
    }

    /**
     * Constructs a request with a specific access token, graph path, parameters, and HTTP method.
     * An access token need not be provided, in which case the request is sent without an access
     * token and thus is not executed in the context of any particular user. Only certain graph
     * requests can be expected to succeed in this case.
     * <p/>
     * Depending on the httpMethod parameter, the object at the graph path may be retrieved,
     * created, or deleted.
     *
     * @param accessToken the access token to use, or null
     * @param graphPath   the graph path to retrieve, create, or delete
     * @param parameters  additional parameters to pass along with the Graph API request; parameters
     *                    must be Strings, Numbers, Bitmaps, Dates, or Byte arrays.
     * @param httpMethod  the {@link HttpMethod} to use for the request, or null for default
     *                    (HttpMethod.GET)
     * @param callback    a callback that will be called when the request is completed to handle
     *                    success or error conditions
     * @param version     the version of the Graph API
     */
    public GraphRequest(
            AccessToken accessToken,
            String graphPath,
            Bundle parameters,
            HttpMethod httpMethod,
            Callback callback,
            String version) {
        this.accessToken = accessToken;
        this.graphPath = graphPath;
        this.version = version;

        setCallback(callback);
        setHttpMethod(httpMethod);

        if (parameters != null) {
            this.parameters = new Bundle(parameters);
        } else {
            this.parameters = new Bundle();
        }

        if (this.version == null) {
            this.version = ServerProtocol.getAPIVersion();
        }
    }

    GraphRequest(AccessToken accessToken, URL overriddenURL) {
        this.accessToken = accessToken;
        this.overriddenURL = overriddenURL.toString();

        setHttpMethod(HttpMethod.GET);

        this.parameters = new Bundle();
    }

    /**
     * Creates a new Request configured to delete a resource through the Graph API.
     *
     * @param accessToken the access token to use, or null
     * @param id          the id of the object to delete
     * @param callback    a callback that will be called when the request is completed to handle
     *                    success or error conditions
     * @return a Request that is ready to execute
     */
    public static GraphRequest newDeleteObjectRequest(
            AccessToken accessToken,
            String id,
            Callback callback) {
        return new GraphRequest(accessToken, id, null, HttpMethod.DELETE, callback);
    }

    /**
     * Creates a new Request configured to retrieve a user's own profile.
     *
     * @param accessToken the access token to use, or null
     * @param callback    a callback that will be called when the request is completed to handle
     *                    success or error conditions
     * @return a Request that is ready to execute
     */
    public static GraphRequest newMeRequest(
            AccessToken accessToken,
            final GraphJSONObjectCallback callback) {
        Callback wrapper = new Callback() {
            @Override
            public void onCompleted(GraphResponse response) {
                if (callback != null) {
                    callback.onCompleted(response.getJSONObject(), response);
                }
            }
        };
        return new GraphRequest(accessToken, ME, null, null, wrapper);
    }

    /**
     * Creates a new Request configured to post a GraphObject to a particular graph path, to either
     * create or update the object at that path.
     *
     * @param accessToken the access token to use, or null
     * @param graphPath   the graph path to retrieve, create, or delete
     * @param graphObject the graph object to create or update
     * @param callback    a callback that will be called when the request is completed to handle
     *                    success or error conditions
     * @return a Request that is ready to execute
     */
    public static GraphRequest newPostRequest(
            AccessToken accessToken,
            String graphPath,
            JSONObject graphObject,
            Callback callback) {
        GraphRequest request = new GraphRequest(
                accessToken,
                graphPath,
                null,
                HttpMethod.POST,
                callback);
        request.setGraphObject(graphObject);
        return request;
    }

    /**
     * Creates a new Request configured to retrieve a user's friend list.
     *
     * @param accessToken the access token to use, or null
     * @param callback    a callback that will be called when the request is completed to handle
     *                    success or error conditions
     * @return a Request that is ready to execute
     */
    public static GraphRequest newMyFriendsRequest(
            AccessToken accessToken,
            final GraphJSONArrayCallback callback) {
        Callback wrapper = new Callback() {
            @Override
            public void onCompleted(GraphResponse response) {
                if (callback != null) {
                    JSONObject result = response.getJSONObject();
                    JSONArray data = result != null ? result.optJSONArray("data") : null;
                    callback.onCompleted(data, response);
                }
            }
        };
        return new GraphRequest(accessToken, MY_FRIENDS, null, null, wrapper);
    }

    /**
     * Creates a new Request configured to retrieve a particular graph path.
     *
     * @param accessToken the access token to use, or null
     * @param graphPath   the graph path to retrieve
     * @param callback    a callback that will be called when the request is completed to handle
     *                    success or error conditions
     * @return a Request that is ready to execute
     */
    public static GraphRequest newGraphPathRequest(
            AccessToken accessToken,
            String graphPath,
            Callback callback) {
        return new GraphRequest(accessToken, graphPath, null, null, callback);
    }

    /**
     * Creates a new Request that is configured to perform a search for places near a specified
     * location via the Graph API. At least one of location or searchText must be specified.
     *
     * @param accessToken    the access token to use, or null
     * @param location       the location around which to search; only the latitude and longitude
     *                       components of the location are meaningful
     * @param radiusInMeters the radius around the location to search, specified in meters; this is
     *                       ignored if no location is specified
     * @param resultsLimit   the maximum number of results to return
     * @param searchText     optional text to search for as part of the name or type of an object
     * @param callback       a callback that will be called when the request is completed to handle
     *                       success or error conditions
     * @return a Request that is ready to execute
     * @throws FacebookException If neither location nor searchText is specified
     */
    public static GraphRequest newPlacesSearchRequest(
            AccessToken accessToken,
            Location location,
            int radiusInMeters,
            int resultsLimit,
            String searchText,
            final GraphJSONArrayCallback callback) {
        if (location == null && Utility.isNullOrEmpty(searchText)) {
            throw new FacebookException("Either location or searchText must be specified.");
        }

        Bundle parameters = new Bundle(5);
        parameters.putString("type", "place");
        parameters.putInt("limit", resultsLimit);
        if (location != null) {
            parameters.putString("center",
                    String.format(
                            Locale.US,
                            "%f,%f",
                            location.getLatitude(),
                            location.getLongitude()));
            parameters.putInt("distance", radiusInMeters);
        }
        if (!Utility.isNullOrEmpty(searchText)) {
            parameters.putString("q", searchText);
        }

        Callback wrapper = new Callback() {
            @Override
            public void onCompleted(GraphResponse response) {
                if (callback != null) {
                    JSONObject result = response.getJSONObject();
                    JSONArray data = result != null ? result.optJSONArray("data") : null;
                    callback.onCompleted(data, response);
                }
            }
        };

        return new GraphRequest(accessToken, SEARCH, parameters, HttpMethod.GET, wrapper);
    }


    /**
     * Creates a new Request configured to retrieve an App User ID for the app's Facebook user.
     * Callers will send this ID back to their own servers, collect up a set to create a Facebook
     * Custom Audience with, and then use the resultant Custom Audience to target ads.
     * <p/>
     * The GraphObject in the response will include a "custom_audience_third_party_id" property,
     * with the value being the ID retrieved.  This ID is an encrypted encoding of the Facebook
     * user's ID and the invoking Facebook app ID.  Multiple calls with the same user will return
     * different IDs, thus these IDs cannot be used to correlate behavior across devices or
     * applications, and are only meaningful when sent back to Facebook for creating Custom
     * Audiences.
     * <p/>
     * The ID retrieved represents the Facebook user identified in the following way: if the
     * specified access token (or active access token if `null`) is valid, the ID will represent the
     * user associated with the active access token; otherwise the ID will represent the user logged
     * into the native Facebook app on the device. A `null` ID will be provided into the callback if
     * a) there is no native Facebook app, b) no one is logged into it, or c) the app has previously
     * called {@link FacebookSdk#setLimitEventAndDataUsage(android.content.Context, boolean)} ;}
     * with `true` for this user. <b>You must call this method from a background thread for it to
     * work properly.</b>
     *
     * @param accessToken   the access token to issue the Request on, or null If there is no
     *                      logged-in Facebook user, null is the expected choice.
     * @param context       the Application context from which the app ID will be pulled, and from
     *                      which the 'attribution ID' for the Facebook user is determined.  If
     *                      there has been no app ID set, an exception will be thrown.
     * @param applicationId explicitly specified Facebook App ID.  If null, the application ID from
     *                      the access token will be used, if any; if not, the application ID from
     *                      metadata will be used.
     * @param callback      a callback that will be called when the request is completed to handle
     *                      success or error conditions. The GraphObject in the Response will
     *                      contain a "custom_audience_third_party_id" property that represents the
     *                      user as described above.
     * @return a Request that is ready to execute
     */
    public static GraphRequest newCustomAudienceThirdPartyIdRequest(AccessToken accessToken,
                                                                    Context context,
                                                                    String applicationId,
                                                                    Callback callback) {

        if (applicationId == null && accessToken != null) {
            applicationId = accessToken.getApplicationId();
        }

        if (applicationId == null) {
            applicationId = Utility.getMetadataApplicationId(context);
        }

        if (applicationId == null) {
            throw new FacebookException("Facebook App ID cannot be determined");
        }

        String endpoint = applicationId + "/custom_audience_third_party_id";
        AttributionIdentifiers attributionIdentifiers =
                AttributionIdentifiers.getAttributionIdentifiers(context);
        Bundle parameters = new Bundle();

        if (accessToken == null) {
            // Only use the attributionID if we don't have an access token.  If we do, then the user
            // token will be used to identify the user, and is more reliable than the attributionID.
            String udid = attributionIdentifiers.getAttributionId() != null
                    ? attributionIdentifiers.getAttributionId()
                    : attributionIdentifiers.getAndroidAdvertiserId();
            if (attributionIdentifiers.getAttributionId() != null) {
                parameters.putString("udid", udid);
            }
        }

        // Server will choose to not provide the App User ID in the event that event usage has been
        // limited for this user for this app.
        if (FacebookSdk.getLimitEventAndDataUsage(context)
                || attributionIdentifiers.isTrackingLimited()) {
            parameters.putString("limit_event_usage", "1");
        }

        return new GraphRequest(accessToken, endpoint, parameters, HttpMethod.GET, callback);
    }

    /**
     * Creates a new Request configured to retrieve an App User ID for the app's Facebook user.
     * Callers will send this ID back to their own servers, collect up a set to create a Facebook
     * Custom Audience with, and then use the resultant Custom Audience to target ads.
     * <p/>
     * The GraphObject in the response will include a "custom_audience_third_party_id" property,
     * with the value being the ID retrieved.  This ID is an encrypted encoding of the Facebook
     * user's ID and the invoking Facebook app ID.  Multiple calls with the same user will return
     * different IDs, thus these IDs cannot be used to correlate behavior across devices or
     * applications, and are only meaningful when sent back to Facebook for creating Custom
     * Audiences.
     * <p/>
     * The ID retrieved represents the Facebook user identified in the following way: if the
     * specified access token (or active access token if `null`) is valid, the ID will represent the
     * user associated with the active access token; otherwise the ID will represent the user logged
     * into the native Facebook app on the device. A `null` ID will be provided into the callback if
     * a) there is no native Facebook app, b) no one is logged into it, or c) the app has previously
     * called {@link FacebookSdk#setLimitEventAndDataUsage(android.content.Context, boolean)} with
     * `true` for this user. <b>You must call this method from a background thread for it to work
     * properly.</b>
     *
     * @param accessToken the access token to issue the Request on, or null If there is no logged-in
     *                    Facebook user, null is the expected choice.
     * @param context     the Application context from which the app ID will be pulled, and from
     *                    which the 'attribution ID' for the Facebook user is determined.  If there
     *                    has been no app ID set, an exception will be thrown.
     * @param callback    a callback that will be called when the request is completed to handle
     *                    success or error conditions. The GraphObject in the Response will contain
     *                    a "custom_audience_third_party_id" property that represents the user as
     *                    described above.
     * @return a Request that is ready to execute
     */
    public static GraphRequest newCustomAudienceThirdPartyIdRequest(
            AccessToken accessToken,
            Context context,
            Callback callback) {
        return newCustomAudienceThirdPartyIdRequest(accessToken, context, null, callback);
    }

    /**
     * Returns the GraphObject, if any, associated with this request.
     *
     * @return the GraphObject associated with this request, or null if there is none
     */
    public final JSONObject getGraphObject() {
        return this.graphObject;
    }

    /**
     * Sets the GraphObject associated with this request. This is meaningful only for POST
     * requests.
     *
     * @param graphObject the GraphObject to upload along with this request
     */
    public final void setGraphObject(JSONObject graphObject) {
        this.graphObject = graphObject;
    }

    /**
     * Returns the graph path of this request, if any.
     *
     * @return the graph path of this request, or null if there is none
     */
    public final String getGraphPath() {
        return this.graphPath;
    }

    /**
     * Sets the graph path of this request.
     *
     * @param graphPath the graph path for this request
     */
    public final void setGraphPath(String graphPath) {
        this.graphPath = graphPath;
    }

    /**
     * Returns the {@link HttpMethod} to use for this request.
     *
     * @return the HttpMethod
     */
    public final HttpMethod getHttpMethod() {
        return this.httpMethod;
    }

    /**
     * Sets the {@link HttpMethod} to use for this request.
     *
     * @param httpMethod the HttpMethod, or null for the default (HttpMethod.GET).
     */
    public final void setHttpMethod(HttpMethod httpMethod) {
        if (overriddenURL != null && httpMethod != HttpMethod.GET) {
            throw new FacebookException("Can't change HTTP method on request with overridden URL.");
        }
        this.httpMethod = (httpMethod != null) ? httpMethod : HttpMethod.GET;
    }

    /**
     * Returns the version of the API that this request will use.  By default this is the current
     * API at the time the SDK is released.
     *
     * @return the version that this request will use
     */
    public final String getVersion() {
        return this.version;
    }

    /**
     * Set the version to use for this request.  By default the version will be the current API at
     * the time the SDK is released.  Only use this if you need to explicitly override.
     *
     * @param version The version to use.  Should look like "v2.0"
     */
    public final void setVersion(String version) {
        this.version = version;
    }

    /**
     * This is an internal function that is not meant to be used by developers.
     */
    public final void setSkipClientToken(boolean skipClientToken) {
        this.skipClientToken = skipClientToken;
    }

    /**
     * Returns the parameters for this request.
     *
     * @return the parameters
     */
    public final Bundle getParameters() {
        return this.parameters;
    }

    /**
     * Sets the parameters for this request.
     *
     * @param parameters the parameters
     */
    public final void setParameters(Bundle parameters) {
        this.parameters = parameters;
    }

    /**
     * Returns the access token associated with this request.
     *
     * @return the access token associated with this request, or null if none has been specified
     */
    public final AccessToken getAccessToken() {
        return this.accessToken;
    }

    /**
     * Sets the access token to use for this request.
     *
     * @param accessToken the access token to use for this request
     */
    public final void setAccessToken(AccessToken accessToken) {
        this.accessToken = accessToken;
    }

    /**
     * Returns the name of this requests entry in a batched request.
     *
     * @return the name of this requests batch entry, or null if none has been specified
     */
    public final String getBatchEntryName() {
        return this.batchEntryName;
    }

    /**
     * Sets the name of this request's entry in a batched request. This value is only used if this
     * request is submitted as part of a batched request. It can be used to specified dependencies
     * between requests.
     * See <a href="https://developers.facebook.com/docs/reference/api/batch/">Batch Requests</a> in
     * the Graph API documentation for more details.
     *
     * @param batchEntryName the name of this requests entry in a batched request, which must be
     *                       unique within a particular batch of requests
     */
    public final void setBatchEntryName(String batchEntryName) {
        this.batchEntryName = batchEntryName;
    }

    /**
     * Returns the name of the request that this request entry explicitly depends on in a batched
     * request.
     *
     * @return the name of this requests dependency, or null if none has been specified
     */
    public final String getBatchEntryDependsOn() {
        return this.batchEntryDependsOn;
    }

    /**
     * Sets the name of the request entry that this request explicitly depends on in a batched
     * request. This value is only used if this request is submitted as part of a batched request.
     * It can be used to specified dependencies between requests. See <a
     * href="https://developers.facebook.com/docs/reference/api/batch/">Batch Requests</a> in the
     * Graph API documentation for more details.
     *
     * @param batchEntryDependsOn the name of the request entry that this entry depends on in a
     *                            batched request
     */
    public final void setBatchEntryDependsOn(String batchEntryDependsOn) {
        this.batchEntryDependsOn = batchEntryDependsOn;
    }


    /**
     * Returns whether or not this batch entry will return a response if it is successful. Only
     * applies if another request entry in the batch specifies this entry as a dependency.
     *
     * @return the name of this requests dependency, or null if none has been specified
     */
    public final boolean getBatchEntryOmitResultOnSuccess() {
        return this.batchEntryOmitResultOnSuccess;
    }

    /**
     * Sets whether or not this batch entry will return a response if it is successful. Only applies
     * if another request entry in the batch specifies this entry as a dependency. See <a
     * href="https://developers.facebook.com/docs/reference/api/batch/">Batch Requests</a> in the
     * Graph API documentation for more details.
     *
     * @param batchEntryOmitResultOnSuccess the name of the request entry that this entry depends on
     *                                      in a batched request
     */
    public final void setBatchEntryOmitResultOnSuccess(boolean batchEntryOmitResultOnSuccess) {
        this.batchEntryOmitResultOnSuccess = batchEntryOmitResultOnSuccess;
    }

    /**
     * Gets the default Facebook application ID that will be used to submit batched requests.
     * Batched requests require an application ID, so either at least one request in a batch must
     * provide an access token or the application ID must be specified explicitly.
     *
     * @return the Facebook application ID to use for batched requests if none can be determined
     */
    public static final String getDefaultBatchApplicationId() {
        return GraphRequest.defaultBatchApplicationId;
    }

    /**
     * Sets the default application ID that will be used to submit batched requests if none of those
     * requests specifies an access token. Batched requests require an application ID, so either at
     * least one request in a batch must specify an access token or the application ID must be
     * specified explicitly.
     *
     * @param applicationId the Facebook application ID to use for batched requests if none can
     *                      be determined
     */
    public static final void setDefaultBatchApplicationId(String applicationId) {
        defaultBatchApplicationId = applicationId;
    }

    /**
     * Returns the callback which will be called when the request finishes.
     *
     * @return the callback
     */
    public final Callback getCallback() {
        return callback;
    }

    /**
     * Sets the callback which will be called when the request finishes.
     *
     * @param callback the callback
     */
    public final void setCallback(final Callback callback) {
        // Wrap callback to parse debug response if Graph Debug Mode is Enabled.
        if (FacebookSdk.isLoggingBehaviorEnabled(LoggingBehavior.GRAPH_API_DEBUG_INFO)
                || FacebookSdk.isLoggingBehaviorEnabled(LoggingBehavior.GRAPH_API_DEBUG_WARNING)) {
            Callback wrapper = new Callback() {
                @Override
                public void onCompleted(GraphResponse response) {
                    JSONObject responseObject = response.getJSONObject();
                    JSONObject debug =
                            responseObject != null ? responseObject.optJSONObject(DEBUG_KEY) : null;
                    JSONArray debugMessages =
                            debug != null ? debug.optJSONArray(DEBUG_MESSAGES_KEY) : null;
                    if (debugMessages != null) {
                        for (int i = 0; i < debugMessages.length(); ++i) {
                            JSONObject debugMessageObject = debugMessages.optJSONObject(i);
                            String debugMessage = debugMessageObject != null
                                    ? debugMessageObject.optString(DEBUG_MESSAGE_KEY)
                                    : null;
                            String debugMessageType = debugMessageObject != null
                                    ? debugMessageObject.optString(DEBUG_MESSAGE_TYPE_KEY)
                                    : null;
                            String debugMessageLink = debugMessageObject != null
                                    ? debugMessageObject.optString(DEBUG_MESSAGE_LINK_KEY)
                                    : null;
                            if (debugMessage != null && debugMessageType != null) {
                                LoggingBehavior behavior = LoggingBehavior.GRAPH_API_DEBUG_INFO;
                                if (debugMessageType.equals("warning")) {
                                    behavior = LoggingBehavior.GRAPH_API_DEBUG_WARNING;
                                }
                                if (!Utility.isNullOrEmpty(debugMessageLink)) {
                                    debugMessage += " Link: " + debugMessageLink;
                                }
                                Logger.log(behavior, TAG, debugMessage);
                            }
                        }
                    }
                    if (callback != null) {
                        callback.onCompleted(response);
                    }
                }
            };
            this.callback = wrapper;
        } else {
            this.callback = callback;
        }

    }

    /**
     * Sets the tag on the request; this is an application-defined object that can be used to
     * distinguish between different requests. Its value has no effect on the execution of the
     * request.
     *
     * @param tag an object to serve as a tag, or null
     */
    public final void setTag(Object tag) {
        this.tag = tag;
    }

    /**
     * Gets the tag on the request; this is an application-defined object that can be used to
     * distinguish between different requests. Its value has no effect on the execution of the
     * request.
     *
     * @return an object that serves as a tag, or null
     */
    public final Object getTag() {
        return tag;
    }

    /**
     * Executes this request on the current thread and blocks while waiting for the response.
     * <p/>
     * This should only be called if you have transitioned off the UI thread.
     *
     * @return the Response object representing the results of the request
     * @throws FacebookException        If there was an error in the protocol used to communicate
     * with the service
     * @throws IllegalArgumentException
     */
    public final GraphResponse executeAndWait() {
        return GraphRequest.executeAndWait(this);
    }

    /**
     * Executes the request asynchronously. This function will return immediately,
     * and the request will be processed on a separate thread. In order to process result of a
     * request, or determine whether a request succeeded or failed, a callback must be specified
     * (see the {@link #setCallback(Callback) setCallback} method).
     * <p/>
     * This should only be called from the UI thread.
     *
     * @return a RequestAsyncTask that is executing the request
     * @throws IllegalArgumentException
     */
    public final GraphRequestAsyncTask executeAsync() {
        return GraphRequest.executeBatchAsync(this);
    }

    /**
     * Serializes one or more requests but does not execute them. The resulting HttpURLConnection
     * can be executed explicitly by the caller.
     *
     * @param requests one or more Requests to serialize
     * @return an HttpURLConnection which is ready to execute
     * @throws FacebookException        If any of the requests in the batch are badly constructed or
     *                                  if there are problems contacting the service
     * @throws IllegalArgumentException if the passed in array is zero-length
     * @throws NullPointerException     if the passed in array or any of its contents are null
     */
    public static HttpURLConnection toHttpConnection(GraphRequest... requests) {
        return toHttpConnection(Arrays.asList(requests));
    }

    /**
     * Serializes one or more requests but does not execute them. The resulting HttpURLConnection
     * can be executed explicitly by the caller.
     *
     * @param requests one or more Requests to serialize
     * @return an HttpURLConnection which is ready to execute
     * @throws FacebookException        If any of the requests in the batch are badly constructed or
     *                                  if there are problems contacting the service
     * @throws IllegalArgumentException if the passed in collection is empty
     * @throws NullPointerException     if the passed in collection or any of its contents are null
     */
    public static HttpURLConnection toHttpConnection(Collection<GraphRequest> requests) {
        Validate.notEmptyAndContainsNoNulls(requests, "requests");

        return toHttpConnection(new GraphRequestBatch(requests));
    }

    /**
     * Serializes one or more requests but does not execute them. The resulting HttpURLConnection
     * can be executed explicitly by the caller.
     *
     * @param requests a RequestBatch to serialize
     * @return an HttpURLConnection which is ready to execute
     * @throws FacebookException        If any of the requests in the batch are badly constructed or
     *                                  if there are problems contacting the service
     * @throws IllegalArgumentException
     */
    public static HttpURLConnection toHttpConnection(GraphRequestBatch requests) {

        URL url;
        try {
            if (requests.size() == 1) {
                // Single request case.
                GraphRequest request = requests.get(0);
                // In the non-batch case, the URL we use really is the same one returned by
                // getUrlForSingleRequest.
                url = new URL(request.getUrlForSingleRequest());
            } else {
                // Batch case -- URL is just the graph API base, individual request URLs are
                // serialized as relative_url parameters within each batch entry.
                url = new URL(ServerProtocol.getGraphUrlBase());
            }
        } catch (MalformedURLException e) {
            throw new FacebookException("could not construct URL for request", e);
        }

        HttpURLConnection connection;
        try {
            connection = createConnection(url);

            serializeToUrlConnection(requests, connection);
        } catch (IOException e) {
            throw new FacebookException("could not construct request body", e);
        } catch (JSONException e) {
            throw new FacebookException("could not construct request body", e);
        }

        return connection;
    }

    /**
     * Executes a single request on the current thread and blocks while waiting for the response.
     * <p/>
     * This should only be used if you have transitioned off the UI thread.
     *
     * @param request the Request to execute
     * @return the Response object representing the results of the request
     * @throws FacebookException If there was an error in the protocol used to communicate with the
     *                           service
     */
    public static GraphResponse executeAndWait(GraphRequest request) {
        List<GraphResponse> responses = executeBatchAndWait(request);

        if (responses == null || responses.size() != 1) {
            throw new FacebookException("invalid state: expected a single response");
        }

        return responses.get(0);
    }

    /**
     * Executes requests on the current thread as a single batch and blocks while waiting for the
     * response.
     * <p/>
     * This should only be used if you have transitioned off the UI thread.
     *
     * @param requests the Requests to execute
     * @return a list of Response objects representing the results of the requests; responses are
     * returned in the same order as the requests were specified.
     * @throws NullPointerException In case of a null request
     * @throws FacebookException    If there was an error in the protocol used to communicate with
     *                              the service
     */
    public static List<GraphResponse> executeBatchAndWait(GraphRequest... requests) {
        Validate.notNull(requests, "requests");

        return executeBatchAndWait(Arrays.asList(requests));
    }

    /**
     * Executes requests as a single batch on the current thread and blocks while waiting for the
     * responses.
     * <p/>
     * This should only be used if you have transitioned off the UI thread.
     *
     * @param requests the Requests to execute
     * @return a list of Response objects representing the results of the requests; responses are
     * returned in the same order as the requests were specified.
     * @throws FacebookException If there was an error in the protocol used to communicate with the
     *                           service
     */
    public static List<GraphResponse> executeBatchAndWait(Collection<GraphRequest> requests) {
        return executeBatchAndWait(new GraphRequestBatch(requests));
    }

    /**
     * Executes requests on the current thread as a single batch and blocks while waiting for the
     * responses.
     * <p/>
     * This should only be used if you have transitioned off the UI thread.
     *
     * @param requests the batch of Requests to execute
     * @return a list of Response objects representing the results of the requests; responses are
     * returned in the same order as the requests were specified.
     * @throws FacebookException        If there was an error in the protocol used to communicate
     *                                  with the service
     * @throws IllegalArgumentException if the passed in RequestBatch is empty
     * @throws NullPointerException     if the passed in RequestBatch or any of its contents are
     *                                  null
     */
    public static List<GraphResponse> executeBatchAndWait(GraphRequestBatch requests) {
        Validate.notEmptyAndContainsNoNulls(requests, "requests");

        HttpURLConnection connection = null;
        try {
            connection = toHttpConnection(requests);
        } catch (Exception ex) {
            List<GraphResponse> responses = GraphResponse.constructErrorResponses(
                    requests.getRequests(),
                    null,
                    new FacebookException(ex));
            runCallbacks(requests, responses);
            return responses;
        }

        List<GraphResponse> responses = executeConnectionAndWait(connection, requests);
        return responses;
    }

    /**
     * Executes requests as a single batch asynchronously. This function will return immediately,
     * and the requests will be processed on a separate thread. In order to process results of a
     * request, or determine whether a request succeeded or failed, a callback must be specified
     * (see the {@link #setCallback(Callback) setCallback} method).
     * <p/>
     * This should only be called from the UI thread.
     *
     * @param requests the Requests to execute
     * @return a RequestAsyncTask that is executing the request
     * @throws NullPointerException If a null request is passed in
     */
    public static GraphRequestAsyncTask executeBatchAsync(GraphRequest... requests) {
        Validate.notNull(requests, "requests");

        return executeBatchAsync(Arrays.asList(requests));
    }

    /**
     * Executes requests as a single batch asynchronously. This function will return immediately,
     * and the requests will be processed on a separate thread. In order to process results of a
     * request, or determine whether a request succeeded or failed, a callback must be specified
     * (see the {@link #setCallback(Callback) setCallback} method).
     * <p/>
     * This should only be called from the UI thread.
     *
     * @param requests the Requests to execute
     * @return a RequestAsyncTask that is executing the request
     * @throws IllegalArgumentException if the passed in collection is empty
     * @throws NullPointerException     if the passed in collection or any of its contents are null
     */
    public static GraphRequestAsyncTask executeBatchAsync(Collection<GraphRequest> requests) {
        return executeBatchAsync(new GraphRequestBatch(requests));
    }

    /**
     * Executes requests as a single batch asynchronously. This function will return immediately,
     * and the requests will be processed on a separate thread. In order to process results of a
     * request, or determine whether a request succeeded or failed, a callback must be specified
     * (see the {@link #setCallback(Callback) setCallback} method).
     * <p/>
     * This should only be called from the UI thread.
     *
     * @param requests the RequestBatch to execute
     * @return a RequestAsyncTask that is executing the request
     * @throws IllegalArgumentException if the passed in RequestBatch is empty
     * @throws NullPointerException     if the passed in RequestBatch or any of its contents are
     *                                  null
     */
    public static GraphRequestAsyncTask executeBatchAsync(GraphRequestBatch requests) {
        Validate.notEmptyAndContainsNoNulls(requests, "requests");

        GraphRequestAsyncTask asyncTask = new GraphRequestAsyncTask(requests);
        asyncTask.executeOnSettingsExecutor();
        return asyncTask;
    }

    /**
     * Executes requests that have already been serialized into an HttpURLConnection. No validation
     * is done that the contents of the connection actually reflect the serialized requests, so it
     * is the caller's responsibility to ensure that it will correctly generate the desired
     * responses.
     * <p/>
     * This should only be called if you have transitioned off the UI thread.
     *
     * @param connection the HttpURLConnection that the requests were serialized into
     * @param requests   the requests represented by the HttpURLConnection
     * @return a list of Responses corresponding to the requests
     * @throws FacebookException If there was an error in the protocol used to communicate with the
     *                           service
     */
    public static List<GraphResponse> executeConnectionAndWait(
            HttpURLConnection connection,
            Collection<GraphRequest> requests) {
        return executeConnectionAndWait(connection, new GraphRequestBatch(requests));
    }

    /**
     * Executes requests that have already been serialized into an HttpURLConnection. No validation
     * is done that the contents of the connection actually reflect the serialized requests, so it
     * is the caller's responsibility to ensure that it will correctly generate the desired
     * responses.
     * <p/>
     * This should only be called if you have transitioned off the UI thread.
     *
     * @param connection the HttpURLConnection that the requests were serialized into
     * @param requests   the RequestBatch represented by the HttpURLConnection
     * @return a list of Responses corresponding to the requests
     * @throws FacebookException If there was an error in the protocol used to communicate with the
     *                           service
     */
    public static List<GraphResponse> executeConnectionAndWait(
            HttpURLConnection connection,
            GraphRequestBatch requests) {
        List<GraphResponse> responses = GraphResponse.fromHttpConnection(connection, requests);

        Utility.disconnectQuietly(connection);

        int numRequests = requests.size();
        if (numRequests != responses.size()) {
            throw new FacebookException(
                    String.format(Locale.US,
                            "Received %d responses while expecting %d",
                            responses.size(),
                            numRequests));
        }

        runCallbacks(requests, responses);

        // Try extending the current access token in case it's needed.
        AccessTokenManager.getInstance().extendAccessTokenIfNeeded();

        return responses;
    }

    /**
     * Asynchronously executes requests that have already been serialized into an HttpURLConnection.
     * No validation is done that the contents of the connection actually reflect the serialized
     * requests, so it is the caller's responsibility to ensure that it will correctly generate the
     * desired responses. This function will return immediately, and the requests will be processed
     * on a separate thread. In order to process results of a request, or determine whether a
     * request succeeded or failed, a callback must be specified (see the {@link
     * #setCallback(Callback) setCallback} method).
     * <p/>
     * This should only be called from the UI thread.
     *
     * @param connection the HttpURLConnection that the requests were serialized into
     * @param requests   the requests represented by the HttpURLConnection
     * @return a RequestAsyncTask that is executing the request
     */
    public static GraphRequestAsyncTask executeConnectionAsync(
            HttpURLConnection connection,
            GraphRequestBatch requests) {
        return executeConnectionAsync(null, connection, requests);
    }

    /**
     * Asynchronously executes requests that have already been serialized into an HttpURLConnection.
     * No validation is done that the contents of the connection actually reflect the serialized
     * requests, so it is the caller's responsibility to ensure that it will correctly generate the
     * desired responses. This function will return immediately, and the requests will be processed
     * on a separate thread. In order to process results of a request, or determine whether a
     * request succeeded or failed, a callback must be specified (see the {@link
     * #setCallback(Callback) setCallback} method)
     * <p/>
     * This should only be called from the UI thread.
     *
     * @param callbackHandler a Handler that will be used to post calls to the callback for each
     *                        request; if null, a Handler will be instantiated on the calling
     *                        thread
     * @param connection      the HttpURLConnection that the requests were serialized into
     * @param requests        the requests represented by the HttpURLConnection
     * @return a RequestAsyncTask that is executing the request
     */
    public static GraphRequestAsyncTask executeConnectionAsync(
            Handler callbackHandler,
            HttpURLConnection connection,
            GraphRequestBatch requests) {
        Validate.notNull(connection, "connection");

        GraphRequestAsyncTask asyncTask = new GraphRequestAsyncTask(connection, requests);
        requests.setCallbackHandler(callbackHandler);
        asyncTask.executeOnSettingsExecutor();
        return asyncTask;
    }

    /**
     * Returns a string representation of this Request, useful for debugging.
     *
     * @return the debugging information
     */
    @Override
    public String toString() {
        return new StringBuilder()
                .append("{Request: ")
                .append(" accessToken: ")
                .append(accessToken == null ? "null" : accessToken)
                .append(", graphPath: ")
                .append(graphPath)
                .append(", graphObject: ")
                .append(graphObject)
                .append(", httpMethod: ")
                .append(httpMethod)
                .append(", parameters: ")
                .append(parameters)
                .append("}")
                .toString();
    }

    static void runCallbacks(final GraphRequestBatch requests, List<GraphResponse> responses) {
        int numRequests = requests.size();

        // Compile the list of callbacks to call and then run them either on this thread or via the
        // Handler we received
        final ArrayList<Pair<Callback, GraphResponse>> callbacks = new ArrayList<Pair<Callback, GraphResponse>>();
        for (int i = 0; i < numRequests; ++i) {
            GraphRequest request = requests.get(i);
            if (request.callback != null) {
                callbacks.add(
                        new Pair<Callback, GraphResponse>(request.callback, responses.get(i)));
            }
        }

        if (callbacks.size() > 0) {
            Runnable runnable = new Runnable() {
                public void run() {
                    for (Pair<Callback, GraphResponse> pair : callbacks) {
                        pair.first.onCompleted(pair.second);
                    }

                    List<GraphRequestBatch.Callback> batchCallbacks = requests.getCallbacks();
                    for (GraphRequestBatch.Callback batchCallback : batchCallbacks) {
                        batchCallback.onBatchCompleted(requests);
                    }
                }
            };

            Handler callbackHandler = requests.getCallbackHandler();
            if (callbackHandler == null) {
                // Run on this thread.
                runnable.run();
            } else {
                // Post to the handler.
                callbackHandler.post(runnable);
            }
        }
    }

    private static HttpURLConnection createConnection(URL url) throws IOException {
        HttpURLConnection connection;
        connection = (HttpURLConnection) url.openConnection();

        connection.setRequestProperty(USER_AGENT_HEADER, getUserAgent());
        connection.setRequestProperty(ACCEPT_LANGUAGE_HEADER, Locale.getDefault().toString());

        connection.setChunkedStreamingMode(0);
        return connection;
    }


    private void addCommonParameters() {
        if (this.accessToken != null) {
            if (!this.parameters.containsKey(ACCESS_TOKEN_PARAM)) {
                String token = accessToken.getToken();
                Logger.registerAccessToken(token);
                this.parameters.putString(ACCESS_TOKEN_PARAM, token);
            }
        } else if (!skipClientToken && !this.parameters.containsKey(ACCESS_TOKEN_PARAM)) {
            String appID = FacebookSdk.getApplicationId();
            String clientToken = FacebookSdk.getClientToken();
            if (!Utility.isNullOrEmpty(appID) && !Utility.isNullOrEmpty(clientToken)) {
                String accessToken = appID + "|" + clientToken;
                this.parameters.putString(ACCESS_TOKEN_PARAM, accessToken);
            } else {
                Log.d(TAG, "Warning: Request without access token missing application ID or" +
                        " client token.");
            }
        }
        this.parameters.putString(SDK_PARAM, SDK_ANDROID);
        this.parameters.putString(FORMAT_PARAM, FORMAT_JSON);

        if (FacebookSdk.isLoggingBehaviorEnabled(LoggingBehavior.GRAPH_API_DEBUG_INFO)) {
            this.parameters.putString(DEBUG_PARAM, DEBUG_SEVERITY_INFO);
        } else if (FacebookSdk.isLoggingBehaviorEnabled(LoggingBehavior.GRAPH_API_DEBUG_WARNING)) {
            this.parameters.putString(DEBUG_PARAM, DEBUG_SEVERITY_WARNING);
        }
    }

    private String appendParametersToBaseUrl(String baseUrl) {
        Uri.Builder uriBuilder = new Uri.Builder().encodedPath(baseUrl);

        Set<String> keys = this.parameters.keySet();
        for (String key : keys) {
            Object value = this.parameters.get(key);

            if (value == null) {
                value = "";
            }

            if (isSupportedParameterType(value)) {
                value = parameterToString(value);
            } else {
                if (httpMethod == HttpMethod.GET) {
                    throw new IllegalArgumentException(
                            String.format(
                                    Locale.US,
                                    "Unsupported parameter type for GET request: %s",
                                    value.getClass().getSimpleName()));
                }
                continue;
            }

            uriBuilder.appendQueryParameter(key, value.toString());
        }

        return uriBuilder.toString();
    }

    final String getUrlForBatchedRequest() {
        if (overriddenURL != null) {
            throw new FacebookException("Can't override URL for a batch request");
        }

        String baseUrl = getGraphPathWithVersion();
        addCommonParameters();
        return appendParametersToBaseUrl(baseUrl);
    }

    final String getUrlForSingleRequest() {
        if (overriddenURL != null) {
            return overriddenURL.toString();
        }

        String graphBaseUrlBase;
        if (this.getHttpMethod() == HttpMethod.POST
                && graphPath != null
                && graphPath.endsWith(VIDEOS_SUFFIX)) {
            graphBaseUrlBase = ServerProtocol.getGraphVideoUrlBase();
        } else {
            graphBaseUrlBase = ServerProtocol.getGraphUrlBase();
        }
        String baseUrl = String.format("%s/%s", graphBaseUrlBase, getGraphPathWithVersion());

        addCommonParameters();
        return appendParametersToBaseUrl(baseUrl);
    }

    private String getGraphPathWithVersion() {
        Matcher matcher = versionPattern.matcher(this.graphPath);
        if (matcher.matches()) {
            return this.graphPath;
        }
        return String.format("%s/%s", this.version, this.graphPath);
    }

    private static class Attachment {
        private final GraphRequest request;
        private final Object value;

        public Attachment(GraphRequest request, Object value) {
            this.request = request;
            this.value = value;
        }

        public GraphRequest getRequest() {
            return request;
        }

        public Object getValue() {
            return value;
        }
    }

    private void serializeToBatch(
            JSONArray batch,
            Map<String, Attachment> attachments
    ) throws JSONException, IOException {
        JSONObject batchEntry = new JSONObject();

        if (this.batchEntryName != null) {
            batchEntry.put(BATCH_ENTRY_NAME_PARAM, this.batchEntryName);
            batchEntry.put(
                    BATCH_ENTRY_OMIT_RESPONSE_ON_SUCCESS_PARAM,
                    this.batchEntryOmitResultOnSuccess);
        }
        if (this.batchEntryDependsOn != null) {
            batchEntry.put(BATCH_ENTRY_DEPENDS_ON_PARAM, this.batchEntryDependsOn);
        }

        String relativeURL = getUrlForBatchedRequest();
        batchEntry.put(BATCH_RELATIVE_URL_PARAM, relativeURL);
        batchEntry.put(BATCH_METHOD_PARAM, httpMethod);
        if (this.accessToken != null) {
            String token = this.accessToken.getToken();
            Logger.registerAccessToken(token);
        }

        // Find all of our attachments. Remember their names and put them in the attachment map.
        ArrayList<String> attachmentNames = new ArrayList<String>();
        Set<String> keys = this.parameters.keySet();
        for (String key : keys) {
            Object value = this.parameters.get(key);
            if (isSupportedAttachmentType(value)) {
                // Make the name unique across this entire batch.
                String name = String.format(
                        Locale.ROOT,
                        "%s%d",
                        ATTACHMENT_FILENAME_PREFIX,
                        attachments.size());
                attachmentNames.add(name);
                attachments.put(name, new Attachment(this, value));
            }
        }

        if (!attachmentNames.isEmpty()) {
            String attachmentNamesString = TextUtils.join(",", attachmentNames);
            batchEntry.put(ATTACHED_FILES_PARAM, attachmentNamesString);
        }

        if (this.graphObject != null) {
            // Serialize the graph object into the "body" parameter.
            final ArrayList<String> keysAndValues = new ArrayList<String>();
            processGraphObject(this.graphObject, relativeURL, new KeyValueSerializer() {
                @Override
                public void writeString(String key, String value) throws IOException {
                    keysAndValues.add(String.format(
                            Locale.US,
                            "%s=%s",
                            key,
                            URLEncoder.encode(value, "UTF-8")));
                }
            });
            String bodyValue = TextUtils.join("&", keysAndValues);
            batchEntry.put(BATCH_BODY_PARAM, bodyValue);
        }

        batch.put(batchEntry);
    }

    private static boolean hasOnProgressCallbacks(GraphRequestBatch requests) {
        for (GraphRequestBatch.Callback callback : requests.getCallbacks()) {
            if (callback instanceof GraphRequestBatch.OnProgressCallback) {
                return true;
            }
        }

        for (GraphRequest request : requests) {
            if (request.getCallback() instanceof OnProgressCallback) {
                return true;
            }
        }

        return false;
    }

    private static void setConnectionContentType(
            HttpURLConnection connection,
            boolean shouldUseGzip) {
        if (shouldUseGzip) {
            connection.setRequestProperty(CONTENT_TYPE_HEADER, "application/x-www-form-urlencoded");
            connection.setRequestProperty(CONTENT_ENCODING_HEADER, "gzip");
        } else {
            connection.setRequestProperty(CONTENT_TYPE_HEADER, getMimeContentType());
        }
    }

    private static boolean isGzipCompressible(GraphRequestBatch requests) {
        for (GraphRequest request : requests) {
            for (String key : request.parameters.keySet()) {
                Object value = request.parameters.get(key);
                if (isSupportedAttachmentType(value)) {
                    return false;
                }
            }
        }
        return true;
    }

    final static void serializeToUrlConnection(
            GraphRequestBatch requests,
            HttpURLConnection connection
    ) throws IOException, JSONException {
        Logger logger = new Logger(LoggingBehavior.REQUESTS, "Request");

        int numRequests = requests.size();
        boolean shouldUseGzip = isGzipCompressible(requests);

        HttpMethod connectionHttpMethod =
                (numRequests == 1) ? requests.get(0).httpMethod : HttpMethod.POST;
        connection.setRequestMethod(connectionHttpMethod.name());
        setConnectionContentType(connection, shouldUseGzip);

        URL url = connection.getURL();
        logger.append("Request:\n");
        logger.appendKeyValue("Id", requests.getId());
        logger.appendKeyValue("URL", url);
        logger.appendKeyValue("Method", connection.getRequestMethod());
        logger.appendKeyValue("User-Agent", connection.getRequestProperty("User-Agent"));
        logger.appendKeyValue("Content-Type", connection.getRequestProperty("Content-Type"));

        connection.setConnectTimeout(requests.getTimeout());
        connection.setReadTimeout(requests.getTimeout());

        // If we have a single non-POST request, don't try to serialize anything or
        // HttpURLConnection will turn it into a POST.
        boolean isPost = (connectionHttpMethod == HttpMethod.POST);
        if (!isPost) {
            logger.log();
            return;
        }

        connection.setDoOutput(true);

        OutputStream outputStream = null;
        try {
            outputStream = new BufferedOutputStream(connection.getOutputStream());
            if (shouldUseGzip) {
                outputStream = new GZIPOutputStream(outputStream);
            }

            if (hasOnProgressCallbacks(requests)) {
                ProgressNoopOutputStream countingStream = null;
                countingStream = new ProgressNoopOutputStream(requests.getCallbackHandler());
                processRequest(requests, null, numRequests, url, countingStream, shouldUseGzip);

                int max = countingStream.getMaxProgress();
                Map<GraphRequest, RequestProgress> progressMap = countingStream.getProgressMap();

                outputStream = new ProgressOutputStream(outputStream, requests, progressMap, max);
            }

            processRequest(requests, logger, numRequests, url, outputStream, shouldUseGzip);
        } finally {
            if (outputStream != null) {
                outputStream.close();
            }
        }

        logger.log();
    }

    private static void processRequest(GraphRequestBatch requests, Logger logger, int numRequests,
                                       URL url, OutputStream outputStream, boolean shouldUseGzip)
            throws IOException, JSONException {
        Serializer serializer = new Serializer(outputStream, logger, shouldUseGzip);

        if (numRequests == 1) {
            GraphRequest request = requests.get(0);

            Map<String, Attachment> attachments = new HashMap<String, Attachment>();
            for (String key : request.parameters.keySet()) {
                Object value = request.parameters.get(key);
                if (isSupportedAttachmentType(value)) {
                    attachments.put(key, new Attachment(request, value));
                }
            }

            if (logger != null) {
                logger.append("  Parameters:\n");
            }
            serializeParameters(request.parameters, serializer, request);

            if (logger != null) {
                logger.append("  Attachments:\n");
            }
            serializeAttachments(attachments, serializer);

            if (request.graphObject != null) {
                processGraphObject(request.graphObject, url.getPath(), serializer);
            }
        } else {
            String batchAppID = getBatchAppId(requests);
            if (Utility.isNullOrEmpty(batchAppID)) {
                throw new FacebookException(
                        "App ID was not specified at the request or Settings.");
            }

            serializer.writeString(BATCH_APP_ID_PARAM, batchAppID);

            // We write out all the requests as JSON, remembering which file attachments they have,
            // then write out the attachments.
            Map<String, Attachment> attachments = new HashMap<String, Attachment>();
            serializeRequestsAsJSON(serializer, requests, attachments);

            if (logger != null) {
                logger.append("  Attachments:\n");
            }
            serializeAttachments(attachments, serializer);
        }
    }

    private static boolean isMeRequest(String path) {
        Matcher matcher = versionPattern.matcher(path);
        if (matcher.matches()) {
            // Group 1 contains the path aside from version
            path = matcher.group(1);
        }
        if (path.startsWith("me/") || path.startsWith("/me/")) {
            return true;
        }
        return false;
    }

    private static void processGraphObject(
            JSONObject graphObject,
            String path,
            KeyValueSerializer serializer
    ) throws IOException {
        // In general, graph objects are passed by reference (ID/URL). But if this is an OG Action,
        // we need to pass the entire values of the contents of the 'image' property, as they
        // contain important metadata beyond just a URL. We don't have a 100% foolproof way of
        // knowing if we are posting an OG Action, given that batched requests can have parameter
        // substitution, but passing the OG Action type as a substituted parameter is unlikely.
        // It looks like an OG Action if it's posted to me/namespace:action[?other=stuff].
        boolean isOGAction = false;
        if (isMeRequest(path)) {
            int colonLocation = path.indexOf(":");
            int questionMarkLocation = path.indexOf("?");
            isOGAction = colonLocation > 3
                    && (questionMarkLocation == -1 || colonLocation < questionMarkLocation);
        }

        Iterator<String> keyIterator = graphObject.keys();
        while (keyIterator.hasNext()) {
            String key = keyIterator.next();
            Object value = graphObject.opt(key);
            boolean passByValue = isOGAction && key.equalsIgnoreCase("image");
            processGraphObjectProperty(key, value, serializer, passByValue);
        }
    }

    private static void processGraphObjectProperty(
            String key,
            Object value,
            KeyValueSerializer serializer,
            boolean passByValue
    ) throws IOException {
        Class<?> valueClass = value.getClass();

        if (JSONObject.class.isAssignableFrom(valueClass)) {
            JSONObject jsonObject = (JSONObject) value;
            if (passByValue) {
                // We need to pass all properties of this object in key[propertyName] format.
                @SuppressWarnings("unchecked")
                Iterator<String> keys = jsonObject.keys();
                while (keys.hasNext()) {
                    String propertyName = keys.next();
                    String subKey = String.format("%s[%s]", key, propertyName);
                    processGraphObjectProperty(
                            subKey,
                            jsonObject.opt(propertyName),
                            serializer,
                            passByValue);
                }
            } else {
                // Normal case is passing objects by reference, so just pass the ID or URL, if any,
                // as the value for "key"
                if (jsonObject.has("id")) {
                    processGraphObjectProperty(
                            key,
                            jsonObject.optString("id"),
                            serializer,
                            passByValue);
                } else if (jsonObject.has("url")) {
                    processGraphObjectProperty(
                            key,
                            jsonObject.optString("url"),
                            serializer,
                            passByValue);
                } else if (jsonObject.has(NativeProtocol.OPEN_GRAPH_CREATE_OBJECT_KEY)) {
                    processGraphObjectProperty(key, jsonObject.toString(), serializer, passByValue);
                }
            }
        } else if (JSONArray.class.isAssignableFrom(valueClass)) {
            JSONArray jsonArray = (JSONArray) value;
            int length = jsonArray.length();
            for (int i = 0; i < length; ++i) {
                String subKey = String.format(Locale.ROOT, "%s[%d]", key, i);
                processGraphObjectProperty(subKey, jsonArray.opt(i), serializer, passByValue);
            }
        } else if (String.class.isAssignableFrom(valueClass) ||
                Number.class.isAssignableFrom(valueClass) ||
                Boolean.class.isAssignableFrom(valueClass)) {
            serializer.writeString(key, value.toString());
        } else if (Date.class.isAssignableFrom(valueClass)) {
            Date date = (Date) value;
            // The "Events Timezone" platform migration affects what date/time formats Facebook
            // accepts and returns. Apps created after 8/1/12 (or apps that have explicitly enabled
            // the migration) should send/receive dates in ISO-8601 format. Pre-migration apps can
            // send as Unix timestamps. Since the future is ISO-8601, that is what we support here.
            // Apps that need pre-migration behavior can explicitly send these as integer timestamps
            // rather than Dates.
            final SimpleDateFormat iso8601DateFormat = new SimpleDateFormat(
                    ISO_8601_FORMAT_STRING,
                    Locale.US);
            serializer.writeString(key, iso8601DateFormat.format(date));
        }
    }

    private static void serializeParameters(
            Bundle bundle,
            Serializer serializer,
            GraphRequest request
    ) throws IOException {
        Set<String> keys = bundle.keySet();

        for (String key : keys) {
            Object value = bundle.get(key);
            if (isSupportedParameterType(value)) {
                serializer.writeObject(key, value, request);
            }
        }
    }

    private static void serializeAttachments(
            Map<String, Attachment> attachments,
            Serializer serializer
    ) throws IOException {
        Set<String> keys = attachments.keySet();

        for (String key : keys) {
            Attachment attachment = attachments.get(key);
            if (isSupportedAttachmentType(attachment.getValue())) {
                serializer.writeObject(key, attachment.getValue(), attachment.getRequest());
            }
        }
    }

    private static void serializeRequestsAsJSON(
            Serializer serializer,
            Collection<GraphRequest> requests,
            Map<String, Attachment> attachments
    ) throws JSONException, IOException {
        JSONArray batch = new JSONArray();
        for (GraphRequest request : requests) {
            request.serializeToBatch(batch, attachments);
        }

        serializer.writeRequestsAsJson(BATCH_PARAM, batch, requests);
    }

    private static String getMimeContentType() {
        return String.format("multipart/form-data; boundary=%s", MIME_BOUNDARY);
    }

    private static volatile String userAgent;

    private static String getUserAgent() {
        if (userAgent == null) {
            userAgent = String.format("%s.%s", USER_AGENT_BASE, FacebookSdkVersion.BUILD);
        }

        return userAgent;
    }

    private static String getBatchAppId(GraphRequestBatch batch) {
        if (!Utility.isNullOrEmpty(batch.getBatchApplicationId())) {
            return batch.getBatchApplicationId();
        }

        for (GraphRequest request : batch) {
            AccessToken accessToken = request.accessToken;
            if (accessToken != null) {
                String applicationId = accessToken.getApplicationId();
                if (applicationId != null) {
                    return applicationId;
                }
            }
        }
        if (!Utility.isNullOrEmpty(GraphRequest.defaultBatchApplicationId)) {
            return GraphRequest.defaultBatchApplicationId;
        }
        return FacebookSdk.getApplicationId();
    }

    private static boolean isSupportedAttachmentType(Object value) {
        return value instanceof Bitmap ||
                value instanceof byte[] ||
                value instanceof Uri ||
                value instanceof ParcelFileDescriptor ||
                value instanceof ParcelableResourceWithMimeType;
    }

    private static boolean isSupportedParameterType(Object value) {
        return value instanceof String || value instanceof Boolean || value instanceof Number ||
                value instanceof Date;
    }

    private static String parameterToString(Object value) {
        if (value instanceof String) {
            return (String) value;
        } else if (value instanceof Boolean || value instanceof Number) {
            return value.toString();
        } else if (value instanceof Date) {
            final SimpleDateFormat iso8601DateFormat = new SimpleDateFormat(
                    ISO_8601_FORMAT_STRING, Locale.US);
            return iso8601DateFormat.format(value);
        }
        throw new IllegalArgumentException("Unsupported parameter type.");
    }

    private interface KeyValueSerializer {
        void writeString(String key, String value) throws IOException;
    }

    private static class Serializer implements KeyValueSerializer {
        private final OutputStream outputStream;
        private final Logger logger;
        private boolean firstWrite = true;
        private boolean useUrlEncode = false;

        public Serializer(OutputStream outputStream, Logger logger, boolean useUrlEncode) {
            this.outputStream = outputStream;
            this.logger = logger;
            this.useUrlEncode = useUrlEncode;
        }

        public void writeObject(String key, Object value, GraphRequest request) throws IOException {
            if (outputStream instanceof RequestOutputStream) {
                ((RequestOutputStream) outputStream).setCurrentRequest(request);
            }

            if (isSupportedParameterType(value)) {
                writeString(key, parameterToString(value));
            } else if (value instanceof Bitmap) {
                writeBitmap(key, (Bitmap) value);
            } else if (value instanceof byte[]) {
                writeBytes(key, (byte[]) value);
            } else if (value instanceof Uri) {
                writeContentUri(key, (Uri) value, null);
            } else if (value instanceof ParcelFileDescriptor) {
                writeFile(key, (ParcelFileDescriptor) value, null);
            } else if (value instanceof ParcelableResourceWithMimeType) {
                ParcelableResourceWithMimeType resourceWithMimeType =
                        (ParcelableResourceWithMimeType) value;
                Parcelable resource = resourceWithMimeType.getResource();
                String mimeType = resourceWithMimeType.getMimeType();
                if (resource instanceof ParcelFileDescriptor) {
                    writeFile(key, (ParcelFileDescriptor) resource, mimeType);
                } else if (resource instanceof Uri) {
                    writeContentUri(key, (Uri) resource, mimeType);
                } else {
                    throw getInvalidTypeError();
                }
            } else {
                throw getInvalidTypeError();
            }
        }

        private RuntimeException getInvalidTypeError() {
            return new IllegalArgumentException("value is not a supported type.");
        }

        public void writeRequestsAsJson(
                String key,
                JSONArray requestJsonArray,
                Collection<GraphRequest> requests
        ) throws IOException, JSONException {
            if (!(outputStream instanceof RequestOutputStream)) {
                writeString(key, requestJsonArray.toString());
                return;
            }

            RequestOutputStream requestOutputStream = (RequestOutputStream) outputStream;
            writeContentDisposition(key, null, null);
            write("[");
            int i = 0;
            for (GraphRequest request : requests) {
                JSONObject requestJson = requestJsonArray.getJSONObject(i);
                requestOutputStream.setCurrentRequest(request);
                if (i > 0) {
                    write(",%s", requestJson.toString());
                } else {
                    write("%s", requestJson.toString());
                }
                i++;
            }
            write("]");
            if (logger != null) {
                logger.appendKeyValue("    " + key, requestJsonArray.toString());
            }
        }

        public void writeString(String key, String value) throws IOException {
            writeContentDisposition(key, null, null);
            writeLine("%s", value);
            writeRecordBoundary();
            if (logger != null) {
                logger.appendKeyValue("    " + key, value);
            }
        }

        public void writeBitmap(String key, Bitmap bitmap) throws IOException {
            writeContentDisposition(key, key, "image/png");
            // Note: quality parameter is ignored for PNG
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, outputStream);
            writeLine("");
            writeRecordBoundary();
            if (logger != null) {
                logger.appendKeyValue("    " + key, "<Image>");
            }
        }

        public void writeBytes(String key, byte[] bytes) throws IOException {
            writeContentDisposition(key, key, "content/unknown");
            this.outputStream.write(bytes);
            writeLine("");
            writeRecordBoundary();
            if (logger != null) {
                logger.appendKeyValue(
                        "    " + key,
                        String.format(Locale.ROOT, "<Data: %d>", bytes.length));
            }
        }

        public void writeContentUri(String key, Uri contentUri, String mimeType)
                throws IOException {
            if (mimeType == null) {
                mimeType = "content/unknown";
            }
            writeContentDisposition(key, key, mimeType);

            InputStream inputStream = FacebookSdk
                    .getApplicationContext()
                    .getContentResolver()
                    .openInputStream(contentUri);

            int totalBytes = 0;
            if (outputStream instanceof ProgressNoopOutputStream) {
                // If we are only counting bytes then skip reading the file
                long contentSize = Utility.getContentSize(contentUri);

                ((ProgressNoopOutputStream) outputStream).addProgress(contentSize);
            } else {
                totalBytes += Utility.copyAndCloseInputStream(inputStream, outputStream);
            }

            writeLine("");
            writeRecordBoundary();
            if (logger != null) {
                logger.appendKeyValue(
                        "    " + key,
                        String.format(Locale.ROOT, "<Data: %d>", totalBytes));
            }
        }

        public void writeFile(
                String key,
                ParcelFileDescriptor descriptor,
                String mimeType
        ) throws IOException {
            if (mimeType == null) {
                mimeType = "content/unknown";
            }
            writeContentDisposition(key, key, mimeType);

            int totalBytes = 0;

            if (outputStream instanceof ProgressNoopOutputStream) {
                // If we are only counting bytes then skip reading the file
                ((ProgressNoopOutputStream) outputStream).addProgress(descriptor.getStatSize());
            } else {
                ParcelFileDescriptor.AutoCloseInputStream inputStream =
                        new ParcelFileDescriptor.AutoCloseInputStream(descriptor);
                totalBytes += Utility.copyAndCloseInputStream(inputStream, outputStream);
            }
            writeLine("");
            writeRecordBoundary();
            if (logger != null) {
                logger.appendKeyValue(
                        "    " + key,
                        String.format(Locale.ROOT, "<Data: %d>", totalBytes));
            }
        }

        public void writeRecordBoundary() throws IOException {
            if (!useUrlEncode) {
                writeLine("--%s", MIME_BOUNDARY);
            } else {
                this.outputStream.write("&".getBytes());
            }
        }

        public void writeContentDisposition(
                String name,
                String filename,
                String contentType
        ) throws IOException {
            if (!useUrlEncode) {
                write("Content-Disposition: form-data; name=\"%s\"", name);
                if (filename != null) {
                    write("; filename=\"%s\"", filename);
                }
                writeLine(""); // newline after Content-Disposition
                if (contentType != null) {
                    writeLine("%s: %s", CONTENT_TYPE_HEADER, contentType);
                }
                writeLine(""); // blank line before content
            } else {
                this.outputStream.write(String.format("%s=", name).getBytes());
            }
        }

        public void write(String format, Object... args) throws IOException {
            if (!useUrlEncode) {
                if (firstWrite) {
                    // Prepend all of our output with a boundary string.
                    this.outputStream.write("--".getBytes());
                    this.outputStream.write(MIME_BOUNDARY.getBytes());
                    this.outputStream.write("\r\n".getBytes());
                    firstWrite = false;
                }
                this.outputStream.write(String.format(format, args).getBytes());
            } else {
                this.outputStream.write(
                        URLEncoder.encode(
                                String.format(Locale.US, format, args), "UTF-8").getBytes());
            }
        }

        public void writeLine(String format, Object... args) throws IOException {
            write(format, args);
            if (!useUrlEncode) {
                write("\r\n");
            }
        }

    }

    /**
     * Specifies the interface that consumers of the Request class can implement in order to be
     * notified when a particular request completes, either successfully or with an error.
     */
    public interface Callback {
        /**
         * The method that will be called when a request completes.
         *
         * @param response the Response of this request, which may include error information if the
         *                 request was unsuccessful
         */
        void onCompleted(GraphResponse response);
    }

    /**
     * Specifies the interface that consumers of the Request class can implement in order to be
     * notified when a progress is made on a particular request. The frequency of the callbacks can
     * be controlled using {@link FacebookSdk#setOnProgressThreshold(long)}
     */
    public interface OnProgressCallback extends Callback {
        /**
         * The method that will be called when progress is made.
         *
         * @param current the current value of the progress of the request.
         * @param max     the maximum value (target) value that the progress will have.
         */
        void onProgress(long current, long max);
    }

    /**
     * Callback for requests that result in an array of JSONObjects.
     */
    public interface GraphJSONArrayCallback {
        /**
         * The method that will be called when the request completes.
         *
         * @param objects  the list of GraphObjects representing the returned objects, or null
         * @param response the Response of this request, which may include error information if the
         *                 request was unsuccessful
         */
        void onCompleted(JSONArray objects, GraphResponse response);
    }

    /**
     * Callback for requests that result in a JSONObject.
     */
    public interface GraphJSONObjectCallback {
        /**
         * The method that will be called when the request completes.
         *
         * @param object   the GraphObject representing the returned object, or null
         * @param response the Response of this request, which may include error information if the
         *                 request was unsuccessful
         */
        void onCompleted(JSONObject object, GraphResponse response);
    }

    /**
     * Used during serialization for the graph request.
     * @param <RESOURCE> The Parcelable type parameter.
     */
    public static class ParcelableResourceWithMimeType<RESOURCE extends Parcelable>
            implements Parcelable {
        private final String mimeType;
        private final RESOURCE resource;

        public String getMimeType() {
            return mimeType;
        }

        public RESOURCE getResource() {
            return resource;
        }

        public int describeContents() {
            return CONTENTS_FILE_DESCRIPTOR;
        }

        public void writeToParcel(Parcel out, int flags) {
            out.writeString(mimeType);
            out.writeParcelable(resource, flags);
        }

        @SuppressWarnings("unused")
        public static final Parcelable.Creator<ParcelableResourceWithMimeType> CREATOR
                = new Parcelable.Creator<ParcelableResourceWithMimeType>() {
            public ParcelableResourceWithMimeType createFromParcel(Parcel in) {
                return new ParcelableResourceWithMimeType(in);
            }

            public ParcelableResourceWithMimeType[] newArray(int size) {
                return new ParcelableResourceWithMimeType[size];
            }
        };

        /**
         * The constructor.
         * @param resource The resource to parcel.
         * @param mimeType The mime type.
         */
        public ParcelableResourceWithMimeType(
                RESOURCE resource,
                String mimeType
        ) {
            this.mimeType = mimeType;
            this.resource = resource;
        }

        private ParcelableResourceWithMimeType(Parcel in) {
            mimeType = in.readString();
            resource = in.readParcelable(FacebookSdk.getApplicationContext().getClassLoader());
        }
    }
}


File: facebook/src/com/facebook/appevents/AppEventsLogger.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook.appevents;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.support.v4.content.LocalBroadcastManager;
import android.util.Log;
import bolts.AppLinks;

import com.facebook.AccessToken;
import com.facebook.FacebookException;
import com.facebook.FacebookRequestError;
import com.facebook.FacebookSdk;
import com.facebook.GraphRequest;
import com.facebook.GraphResponse;
import com.facebook.LoggingBehavior;
import com.facebook.internal.AppEventsLoggerUtility;
import com.facebook.internal.AttributionIdentifiers;
import com.facebook.internal.Logger;
import com.facebook.internal.Utility;
import com.facebook.internal.Validate;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.FileNotFoundException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.io.Serializable;
import java.io.UnsupportedEncodingException;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Currency;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.TimeUnit;


/**
 * <p>
 * The AppEventsLogger class allows the developer to log various types of events back to Facebook.  In order to log
 * events, the app must create an instance of this class via a {@link #newLogger newLogger} method, and then call
 * the various "log" methods off of that.
 * </p>
 * <p>
 * This client-side event logging is then available through Facebook App Insights
 * and for use with Facebook Ads conversion tracking and optimization.
 * </p>
 * <p>
 * The AppEventsLogger class has a few related roles:
 * </p>
 * <ul>
 * <li>
 * Logging predefined and application-defined events to Facebook App Insights with a
 * numeric value to sum across a large number of events, and an optional set of key/value
 * parameters that define "segments" for this event (e.g., 'purchaserStatus' : 'frequent', or
 * 'gamerLevel' : 'intermediate').  These events may also be used for ads conversion tracking,
 * optimization, and other ads related targeting in the future.
 * </li>
 * <li>
 * Methods that control the way in which events are flushed out to the Facebook servers.
 * </li>
 * </ul>
 * <p>
 * Here are some important characteristics of the logging mechanism provided by AppEventsLogger:
 * <ul>
 * <li>
 * Events are not sent immediately when logged.  They're cached and flushed out to the
 * Facebook servers in a number of situations:
 * <ul>
 * <li>when an event count threshold is passed (currently 100 logged events).</li>
 * <li>when a time threshold is passed (currently 15 seconds).</li>
 * <li>when an app has gone to background and is then brought back to the foreground.</li>
 * </ul>
 * <li>
 * Events will be accumulated when the app is in a disconnected state, and sent when the connection
 * is restored and one of the above 'flush' conditions are met.
 * </li>
 * <li>
 * The AppEventsLogger class is intended to be used from the thread it was created on.  Multiple
 * AppEventsLoggers may be created on other threads if desired.
 * </li>
 * <li>
 * The developer can call the setFlushBehavior method to force the flushing of events to only
 * occur on an explicit call to the `flush` method.
 * </li>
 * <li>
 * The developer can turn on console debug output for event logging and flushing to the server by
 * calling FacebookSdk.addLoggingBehavior(LoggingBehavior.APP_EVENTS);
 * </li>
 * </ul>
 * </p>
 * <p>
 * Some things to note when logging events:
 * <ul>
 * <li>
 * There is a limit on the number of unique event names an app can use, on the order of 300.
 * </li>
 * <li>
 * There is a limit to the number of unique parameter names in the provided parameters that can
 * be used per event, on the order of 25.  This is not just for an individual call, but for all
 * invocations for that eventName.
 * </li>
 * <li>
 * Event names and parameter names (the keys in the NSDictionary) must be between 2 and 40
 * characters, and must consist of alphanumeric characters, _, -, or spaces.
 * </li>
 * <li>
 * The length of each parameter value can be no more than on the order of 100 characters.
 * </li>
 * </ul>
 * </p>
 */
public class AppEventsLogger {
    // Enums

    /**
     * Controls when an AppEventsLogger sends log events to the server
     */
    public enum FlushBehavior {
        /**
         * Flush automatically: periodically (every 15 seconds or after every 100 events), and
         * always at app reactivation. This is the default value.
         */
        AUTO,

        /**
         * Only flush when AppEventsLogger.flush() is explicitly invoked.
         */
        EXPLICIT_ONLY,
    }

    // Constants
    private static final String TAG = AppEventsLogger.class.getCanonicalName();

    private static final int NUM_LOG_EVENTS_TO_TRY_TO_FLUSH_AFTER = 100;
    private static final int FLUSH_PERIOD_IN_SECONDS = 15;
    private static final int APP_SUPPORTS_ATTRIBUTION_ID_RECHECK_PERIOD_IN_SECONDS = 60 * 60 * 24;
    private static final int FLUSH_APP_SESSION_INFO_IN_SECONDS = 30;

    public static final String APP_EVENT_PREFERENCES = "com.facebook.sdk.appEventPreferences";

    private static final String SOURCE_APPLICATION_HAS_BEEN_SET_BY_THIS_INTENT =
            "_fbSourceApplicationHasBeenSet";

    // Instance member variables
    private final String uiName;
    private final AccessTokenAppIdPair accessTokenAppId;

    private static Map<AccessTokenAppIdPair, SessionEventsState> stateMap =
            new ConcurrentHashMap<AccessTokenAppIdPair, SessionEventsState>();
    private static ScheduledThreadPoolExecutor backgroundExecutor;
    private static FlushBehavior flushBehavior = FlushBehavior.AUTO;
    private static boolean requestInFlight;
    private static Context applicationContext;
    private static Object staticLock = new Object();
    private static String anonymousAppDeviceGUID;
    private static String sourceApplication;
    private static boolean isOpenedByApplink;

    private static class AccessTokenAppIdPair implements Serializable {
        private static final long serialVersionUID = 1L;
        private final String accessTokenString;
        private final String applicationId;

        AccessTokenAppIdPair(AccessToken accessToken) {
            this(accessToken.getToken(), FacebookSdk.getApplicationId());
        }

        AccessTokenAppIdPair(String accessTokenString, String applicationId) {
            this.accessTokenString = Utility.isNullOrEmpty(accessTokenString)
                    ? null
                    : accessTokenString;
            this.applicationId = applicationId;
        }

        String getAccessTokenString() {
            return accessTokenString;
        }

        String getApplicationId() {
            return applicationId;
        }

        @Override
        public int hashCode() {
            return (accessTokenString == null ? 0 : accessTokenString.hashCode()) ^
                    (applicationId == null ? 0 : applicationId.hashCode());
        }

        @Override
        public boolean equals(Object o) {
            if (!(o instanceof AccessTokenAppIdPair)) {
                return false;
            }
            AccessTokenAppIdPair p = (AccessTokenAppIdPair) o;
            return Utility.areObjectsEqual(p.accessTokenString, accessTokenString) &&
                    Utility.areObjectsEqual(p.applicationId, applicationId);
        }

        private static class SerializationProxyV1 implements Serializable {
            private static final long serialVersionUID = -2488473066578201069L;
            private final String accessTokenString;
            private final String appId;

            private SerializationProxyV1(String accessTokenString, String appId) {
                this.accessTokenString = accessTokenString;
                this.appId = appId;
            }

            private Object readResolve() {
                return new AccessTokenAppIdPair(accessTokenString, appId);
            }
        }

        private Object writeReplace() {
            return new SerializationProxyV1(accessTokenString, applicationId);
        }
    }

    /**
     * Notifies the events system that the app has launched & logs an activatedApp event.  Should be
     * called whenever your app becomes active, typically in the onResume() method of each
     * long-running Activity of your app.
     * <p/>
     * Use this method if your application ID is stored in application metadata, otherwise see
     * {@link AppEventsLogger#activateApp(android.content.Context, String)}.
     *
     * @param context Used to access the applicationId and the attributionId for non-authenticated
     *                users.
     */
    public static void activateApp(Context context) {
        FacebookSdk.sdkInitialize(context);
        activateApp(context, Utility.getMetadataApplicationId(context));
    }

    /**
     * Notifies the events system that the app has launched & logs an activatedApp event.  Should be
     * called whenever your app becomes active, typically in the onResume() method of each
     * long-running Activity of your app.
     *
     * @param context       Used to access the attributionId for non-authenticated users.
     * @param applicationId The specific applicationId to report the activation for.
     */
    public static void activateApp(Context context, String applicationId) {
        if (context == null || applicationId == null) {
            throw new IllegalArgumentException("Both context and applicationId must be non-null");
        }

        if ((context instanceof Activity)) {
            setSourceApplication((Activity) context);
        } else {
          // If context is not an Activity, we cannot get intent nor calling activity.
          resetSourceApplication();
          Log.d(AppEventsLogger.class.getName(),
              "To set source application the context of activateApp must be an instance of" +
                      " Activity");
        }

        // activateApp supersedes publishInstall in the public API, so we need to explicitly invoke
        // it, since the server can't reliably infer install state for all conditions of an app
        // activate.
        FacebookSdk.publishInstallAsync(context, applicationId);

        final AppEventsLogger logger = new AppEventsLogger(context, applicationId, null);
        final long eventTime = System.currentTimeMillis();
        final String sourceApplicationInfo = getSourceApplication();
        backgroundExecutor.execute(new Runnable() {
            @Override
            public void run() {
                logger.logAppSessionResumeEvent(eventTime, sourceApplicationInfo);
            }
        });
    }

    /**
     * Notifies the events system that the app has been deactivated (put in the background) and
     * tracks the application session information. Should be called whenever your app becomes
     * inactive, typically in the onPause() method of each long-running Activity of your app.
     *
     * Use this method if your application ID is stored in application metadata, otherwise see
     * {@link AppEventsLogger#deactivateApp(android.content.Context, String)}.
     *
     * @param context Used to access the applicationId and the attributionId for non-authenticated
     *                users.
     */
    public static void deactivateApp(Context context) {
        deactivateApp(context, Utility.getMetadataApplicationId(context));
    }

    /**
     * Notifies the events system that the app has been deactivated (put in the background) and
     * tracks the application session information. Should be called whenever your app becomes
     * inactive, typically in the onPause() method of each long-running Activity of your app.
     *
     * @param context       Used to access the attributionId for non-authenticated users.
     * @param applicationId The specific applicationId to track session information for.
     */
    public static void deactivateApp(Context context, String applicationId) {
        if (context == null || applicationId == null) {
            throw new IllegalArgumentException("Both context and applicationId must be non-null");
        }

        resetSourceApplication();

        final AppEventsLogger logger = new AppEventsLogger(context, applicationId, null);
        final long eventTime = System.currentTimeMillis();
        backgroundExecutor.execute(new Runnable() {
            @Override
            public void run() {
                logger.logAppSessionSuspendEvent(eventTime);
            }
        });
    }

    private void logAppSessionResumeEvent(long eventTime, String sourceApplicationInfo) {
        PersistedAppSessionInfo.onResume(
                applicationContext,
                accessTokenAppId,
                this,
                eventTime,
                sourceApplicationInfo);
    }

    private void logAppSessionSuspendEvent(long eventTime) {
        PersistedAppSessionInfo.onSuspend(applicationContext, accessTokenAppId, this, eventTime);
    }

    /**
     * Build an AppEventsLogger instance to log events through.  The Facebook app that these events
     * are targeted at comes from this application's metadata. The application ID used to log events
     * will be determined from the app ID specified in the package metadata.
     *
     * @param context Used to access the applicationId and the attributionId for non-authenticated
     *                users.
     * @return AppEventsLogger instance to invoke log* methods on.
     */
    public static AppEventsLogger newLogger(Context context) {
        return new AppEventsLogger(context, null, null);
    }

    /**
     * Build an AppEventsLogger instance to log events through.
     *
     * @param context Used to access the attributionId for non-authenticated users.
     * @param accessToken Access token to use for logging events. If null, the active access token
     *                    will be used, if any; if not the logging will happen against the default
     *                    app ID specified in the package metadata.
     */
    public static AppEventsLogger newLogger(Context context, AccessToken accessToken) {
        return new AppEventsLogger(context, null, accessToken);
    }

    /**
     * Build an AppEventsLogger instance to log events through.
     *
     * @param context       Used to access the attributionId for non-authenticated users.
     * @param applicationId Explicitly specified Facebook applicationId to log events against.  If
     *                      null, the default app ID specified in the package metadata will be
     *                      used.
     * @param accessToken   Access token to use for logging events. If null, the active access token
     *                      will be used, if any; if not the logging will happen against the default
     *                      app ID specified in the package metadata.
     * @return AppEventsLogger instance to invoke log* methods on.
     */
    public static AppEventsLogger newLogger(
            Context context,
            String applicationId,
            AccessToken accessToken) {
        return new AppEventsLogger(context, applicationId, accessToken);
    }

    /**
     * Build an AppEventsLogger instance to log events that are attributed to the application but
     * not to any particular Session.
     *
     * @param context       Used to access the attributionId for non-authenticated users.
     * @param applicationId Explicitly specified Facebook applicationId to log events against.  If
     *                      null, the default app ID specified in the package metadata will be
     *                      used.
     * @return AppEventsLogger instance to invoke log* methods on.
     */
    public static AppEventsLogger newLogger(Context context, String applicationId) {
        return new AppEventsLogger(context, applicationId, null);
    }

    /**
     * The action used to indicate that a flush of app events has occurred. This should
     * be used as an action in an IntentFilter and BroadcastReceiver registered with
     * the {@link android.support.v4.content.LocalBroadcastManager}.
     */
    public static final String ACTION_APP_EVENTS_FLUSHED = "com.facebook.sdk.APP_EVENTS_FLUSHED";

    public static final String APP_EVENTS_EXTRA_NUM_EVENTS_FLUSHED =
            "com.facebook.sdk.APP_EVENTS_NUM_EVENTS_FLUSHED";
    public static final String APP_EVENTS_EXTRA_FLUSH_RESULT =
            "com.facebook.sdk.APP_EVENTS_FLUSH_RESULT";

    /**
     * Access the behavior that AppEventsLogger uses to determine when to flush logged events to the
     * server. This setting applies to all instances of AppEventsLogger.
     *
     * @return Specified flush behavior.
     */
    public static FlushBehavior getFlushBehavior() {
        synchronized (staticLock) {
            return flushBehavior;
        }
    }

    /**
     * Set the behavior that this AppEventsLogger uses to determine when to flush logged events to
     * the server. This setting applies to all instances of AppEventsLogger.
     *
     * @param flushBehavior the desired behavior.
     */
    public static void setFlushBehavior(FlushBehavior flushBehavior) {
        synchronized (staticLock) {
            AppEventsLogger.flushBehavior = flushBehavior;
        }
    }

    /**
     * Log an app event with the specified name.
     *
     * @param eventName eventName used to denote the event.  Choose amongst the EVENT_NAME_*
     *                  constants in {@link AppEventsConstants} when possible.  Or create your own
     *                  if none of the EVENT_NAME_* constants are applicable. Event names should be
     *                  40 characters or less, alphanumeric, and can include spaces, underscores or
     *                  hyphens, but must not have a space or hyphen as the first character.  Any
     *                  given app should have no more than ~300 distinct event names.
     */
    public void logEvent(String eventName) {
        logEvent(eventName, null);
    }

    /**
     * Log an app event with the specified name and the supplied value.
     *
     * @param eventName  eventName used to denote the event.  Choose amongst the EVENT_NAME_*
     *                   constants in {@link AppEventsConstants} when possible.  Or create your own
     *                   if none of the EVENT_NAME_* constants are applicable. Event names should be
     *                   40 characters or less, alphanumeric, and can include spaces, underscores or
     *                   hyphens, but must not have a space or hyphen as the first character.  Any
     *                   given app should have no more than ~300 distinct event names. * @param
     *                   eventName
     * @param valueToSum a value to associate with the event which will be summed up in Insights for
     *                   across all instances of the event, so that average values can be
     *                   determined, etc.
     */
    public void logEvent(String eventName, double valueToSum) {
        logEvent(eventName, valueToSum, null);
    }

    /**
     * Log an app event with the specified name and set of parameters.
     *
     * @param eventName  eventName used to denote the event.  Choose amongst the EVENT_NAME_*
     *                   constants in {@link AppEventsConstants} when possible.  Or create your own
     *                   if none of the EVENT_NAME_* constants are applicable. Event names should be
     *                   40 characters or less, alphanumeric, and can include spaces, underscores or
     *                   hyphens, but must not have a space or hyphen as the first character.  Any
     *                   given app should have no more than ~300 distinct event names.
     * @param parameters A Bundle of parameters to log with the event.  Insights will allow looking
     *                   at the logs of these events via different parameter values.  You can log on
     *                   the order of 10 parameters with each distinct eventName.  It's advisable to
     *                   limit the number of unique values provided for each parameter in the
     *                   thousands.  As an example, don't attempt to provide a unique
     *                   parameter value for each unique user in your app.  You won't get meaningful
     *                   aggregate reporting on so many parameter values.  The values in the bundles
     *                   should be Strings or numeric values.
     */
    public void logEvent(String eventName, Bundle parameters) {
        logEvent(eventName, null, parameters, false);
    }

    /**
     * Log an app event with the specified name, supplied value, and set of parameters.
     *
     * @param eventName  eventName used to denote the event.  Choose amongst the EVENT_NAME_*
     *                   constants in {@link AppEventsConstants} when possible.  Or create your own
     *                   if none of the EVENT_NAME_* constants are applicable. Event names should be
     *                   40 characters or less, alphanumeric, and can include spaces, underscores or
     *                   hyphens, but must not have a space or hyphen as the first character.  Any
     *                   given app should have no more than ~300 distinct event names.
     * @param valueToSum a value to associate with the event which will be summed up in Insights for
     *                   across all instances of the event, so that average values can be
     *                   determined, etc.
     * @param parameters A Bundle of parameters to log with the event.  Insights will allow looking
     *                   at the logs of these events via different parameter values.  You can log on
     *                   the order of 10 parameters with each distinct eventName.  It's advisable to
     *                   limit the number of unique values provided for each parameter in the
     *                   thousands.  As an example, don't attempt to provide a unique
     *                   parameter value for each unique user in your app.  You won't get meaningful
     *                   aggregate reporting on so many parameter values.  The values in the bundles
     *                   should be Strings or numeric values.
     */
    public void logEvent(String eventName, double valueToSum, Bundle parameters) {
        logEvent(eventName, valueToSum, parameters, false);
    }

    /**
     * Logs a purchase event with Facebook, in the specified amount and with the specified
     * currency.
     *
     * @param purchaseAmount Amount of purchase, in the currency specified by the 'currency'
     *                       parameter. This value will be rounded to the thousandths place (e.g.,
     *                       12.34567 becomes 12.346).
     * @param currency       Currency used to specify the amount.
     */
    public void logPurchase(BigDecimal purchaseAmount, Currency currency) {
        logPurchase(purchaseAmount, currency, null);
    }

    /**
     * Logs a purchase event with Facebook, in the specified amount and with the specified currency.
     * Additional detail about the purchase can be passed in through the parameters bundle.
     *
     * @param purchaseAmount Amount of purchase, in the currency specified by the 'currency'
     *                       parameter. This value will be rounded to the thousandths place (e.g.,
     *                       12.34567 becomes 12.346).
     * @param currency       Currency used to specify the amount.
     * @param parameters     Arbitrary additional information for describing this event. This should
     *                       have no more than 10 entries, and keys should be mostly consistent from
     *                       one purchase event to the next.
     */
    public void logPurchase(BigDecimal purchaseAmount, Currency currency, Bundle parameters) {

        if (purchaseAmount == null) {
            notifyDeveloperError("purchaseAmount cannot be null");
            return;
        } else if (currency == null) {
            notifyDeveloperError("currency cannot be null");
            return;
        }

        if (parameters == null) {
            parameters = new Bundle();
        }
        parameters.putString(AppEventsConstants.EVENT_PARAM_CURRENCY, currency.getCurrencyCode());

        logEvent(AppEventsConstants.EVENT_NAME_PURCHASED, purchaseAmount.doubleValue(), parameters);
        eagerFlush();
    }

    /**
     * Explicitly flush any stored events to the server.  Implicit flushes may happen depending on
     * the value of getFlushBehavior.  This method allows for explicit, app invoked flushing.
     */
    public void flush() {
        flush(FlushReason.EXPLICIT);
    }

    /**
     * Call this when the consuming Activity/Fragment receives an onStop() callback in order to
     * persist any outstanding events to disk so they may be flushed at a later time. The next
     * flush (explicit or not) will check for any outstanding events and if present, include them
     * in that flush. Note that this call may trigger an I/O operation on the calling thread.
     * Explicit use of this method is necessary.
     */
    public static void onContextStop() {
        // TODO: (v4) add onContextStop() to samples that use the logger.
        PersistedEvents.persistEvents(applicationContext, stateMap);
    }

    /**
     * Determines if the logger is valid for the given access token.
     * @param accessToken The access token to check.
     * @return True if the access token is valid for this logger.
     */
    public boolean isValidForAccessToken(AccessToken accessToken) {
        AccessTokenAppIdPair other = new AccessTokenAppIdPair(accessToken);
        return accessTokenAppId.equals(other);
    }

    /**
     * This method is intended only for internal use by the Facebook SDK and other use is
     * unsupported.
     */
    public void logSdkEvent(String eventName, Double valueToSum, Bundle parameters) {
        logEvent(eventName, valueToSum, parameters, true);
    }

    /**
     * Returns the app ID this logger was configured to log to.
     *
     * @return the Facebook app ID
     */
    public String getApplicationId() {
        return accessTokenAppId.getApplicationId();
    }

    //
    // Private implementation
    //

    @SuppressWarnings("UnusedDeclaration")
    private enum FlushReason {
        EXPLICIT,
        TIMER,
        SESSION_CHANGE,
        PERSISTED_EVENTS,
        EVENT_THRESHOLD,
        EAGER_FLUSHING_EVENT,
    }

    @SuppressWarnings("UnusedDeclaration")
    private enum FlushResult {
        SUCCESS,
        SERVER_ERROR,
        NO_CONNECTIVITY,
        UNKNOWN_ERROR
    }

    /**
     * Constructor is private, newLogger() methods should be used to build an instance.
     */
    private AppEventsLogger(Context context, String applicationId, AccessToken accessToken) {
        Validate.notNull(context, "context");
        uiName = Utility.getActivityName(context);

        if (accessToken == null) {
            accessToken = AccessToken.getCurrentAccessToken();
        }

        // If we have a session and the appId passed is null or matches the session's app ID:
        if (accessToken != null &&
                (applicationId == null || applicationId.equals(accessToken.getApplicationId()))
                ) {
            accessTokenAppId = new AccessTokenAppIdPair(accessToken);
        } else {
            // If no app ID passed, get it from the manifest:
            if (applicationId == null) {
                applicationId = Utility.getMetadataApplicationId(context);
            }
            accessTokenAppId = new AccessTokenAppIdPair(null, applicationId);
        }

        synchronized (staticLock) {

            if (applicationContext == null) {
                applicationContext = context.getApplicationContext();
            }
        }

        initializeTimersIfNeeded();
    }

    private static void initializeTimersIfNeeded() {
        synchronized (staticLock) {
            if (backgroundExecutor != null) {
                return;
            }
            backgroundExecutor = new ScheduledThreadPoolExecutor(1);
        }

        final Runnable flushRunnable = new Runnable() {
            @Override
            public void run() {
                if (getFlushBehavior() != FlushBehavior.EXPLICIT_ONLY) {
                    flushAndWait(FlushReason.TIMER);
                }
            }
        };

        backgroundExecutor.scheduleAtFixedRate(
                flushRunnable,
                0,
                FLUSH_PERIOD_IN_SECONDS,
                TimeUnit.SECONDS
        );

        final Runnable attributionRecheckRunnable = new Runnable() {
            @Override
            public void run() {
                Set<String> applicationIds = new HashSet<String>();
                synchronized (staticLock) {
                    for (AccessTokenAppIdPair accessTokenAppId : stateMap.keySet()) {
                        applicationIds.add(accessTokenAppId.getApplicationId());
                    }
                }
                for (String applicationId : applicationIds) {
                    Utility.queryAppSettings(applicationId, true);
                }
            }
        };

        backgroundExecutor.scheduleAtFixedRate(
                attributionRecheckRunnable,
                0,
                APP_SUPPORTS_ATTRIBUTION_ID_RECHECK_PERIOD_IN_SECONDS,
                TimeUnit.SECONDS
        );
    }

    private void logEvent(
            String eventName,
            Double valueToSum,
            Bundle parameters,
            boolean isImplicitlyLogged) {
        AppEvent event = new AppEvent(
                uiName,
                eventName,
                valueToSum,
                parameters,
                isImplicitlyLogged);
        logEvent(applicationContext, event, accessTokenAppId);
    }

    private static void logEvent(final Context context,
                                 final AppEvent event,
                                 final AccessTokenAppIdPair accessTokenAppId) {
        FacebookSdk.getExecutor().execute(new Runnable() {
            @Override
            public void run() {
                SessionEventsState state = getSessionEventsState(context, accessTokenAppId);
                state.addEvent(event);
                flushIfNecessary();
            }
        });
    }

    static void eagerFlush() {
        if (getFlushBehavior() != FlushBehavior.EXPLICIT_ONLY) {
            flush(FlushReason.EAGER_FLUSHING_EVENT);
        }
    }

    private static void flushIfNecessary() {
        synchronized (staticLock) {
            if (getFlushBehavior() != FlushBehavior.EXPLICIT_ONLY) {
                if (getAccumulatedEventCount() > NUM_LOG_EVENTS_TO_TRY_TO_FLUSH_AFTER) {
                    flush(FlushReason.EVENT_THRESHOLD);
                }
            }
        }
    }

    private static int getAccumulatedEventCount() {
        synchronized (staticLock) {

            int result = 0;
            for (SessionEventsState state : stateMap.values()) {
                result += state.getAccumulatedEventCount();
            }
            return result;
        }
    }

    // Creates a new SessionEventsState if not already in the map.
    private static SessionEventsState getSessionEventsState(
            Context context,
            AccessTokenAppIdPair accessTokenAppId) {
        // Do this work outside of the lock to prevent deadlocks in implementation of
        // AdvertisingIdClient.getAdvertisingIdInfo, because that implementation blocks waiting on
        // the main thread, which may also grab this staticLock.
        SessionEventsState state = stateMap.get(accessTokenAppId);
        AttributionIdentifiers attributionIdentifiers = null;
        if (state == null) {
            // Retrieve attributionId, but we will only send it if attribution is supported for the
            // app.
            attributionIdentifiers = AttributionIdentifiers.getAttributionIdentifiers(context);
        }

        synchronized (staticLock) {
            // Check state again while we're locked.
            state = stateMap.get(accessTokenAppId);
            if (state == null) {
                state = new SessionEventsState(
                        attributionIdentifiers,
                        context.getPackageName(),
                        getAnonymousAppDeviceGUID(context));
                stateMap.put(accessTokenAppId, state);
            }
            return state;
        }
    }

    private static SessionEventsState getSessionEventsState(AccessTokenAppIdPair accessTokenAppId) {
        synchronized (staticLock) {
            return stateMap.get(accessTokenAppId);
        }
    }

    private static void flush(final FlushReason reason) {

        FacebookSdk.getExecutor().execute(new Runnable() {
            @Override
            public void run() {
                flushAndWait(reason);
            }
        });
    }

    private static void flushAndWait(final FlushReason reason) {

        Set<AccessTokenAppIdPair> keysToFlush;
        synchronized (staticLock) {
            if (requestInFlight) {
                return;
            }
            requestInFlight = true;
            keysToFlush = new HashSet<AccessTokenAppIdPair>(stateMap.keySet());
        }

        accumulatePersistedEvents();

        FlushStatistics flushResults = null;
        try {
            flushResults = buildAndExecuteRequests(reason, keysToFlush);
        } catch (Exception e) {
            Utility.logd(TAG, "Caught unexpected exception while flushing: ", e);
        }

        synchronized (staticLock) {
            requestInFlight = false;
        }

        if (flushResults != null) {
            final Intent intent = new Intent(ACTION_APP_EVENTS_FLUSHED);
            intent.putExtra(APP_EVENTS_EXTRA_NUM_EVENTS_FLUSHED, flushResults.numEvents);
            intent.putExtra(APP_EVENTS_EXTRA_FLUSH_RESULT, flushResults.result);
            LocalBroadcastManager.getInstance(applicationContext).sendBroadcast(intent);
        }
    }

    private static FlushStatistics buildAndExecuteRequests(
            FlushReason reason,
            Set<AccessTokenAppIdPair> keysToFlush) {
        FlushStatistics flushResults = new FlushStatistics();

        boolean limitEventUsage = FacebookSdk.getLimitEventAndDataUsage(applicationContext);

        List<GraphRequest> requestsToExecute = new ArrayList<GraphRequest>();
        for (AccessTokenAppIdPair accessTokenAppId : keysToFlush) {
            SessionEventsState sessionEventsState = getSessionEventsState(accessTokenAppId);
            if (sessionEventsState == null) {
                continue;
            }

            GraphRequest request = buildRequestForSession(
                    accessTokenAppId,
                    sessionEventsState,
                    limitEventUsage,
                    flushResults);
            if (request != null) {
                requestsToExecute.add(request);
            }
        }

        if (requestsToExecute.size() > 0) {
            Logger.log(LoggingBehavior.APP_EVENTS, TAG, "Flushing %d events due to %s.",
                    flushResults.numEvents,
                    reason.toString());

            for (GraphRequest request : requestsToExecute) {
                // Execute the request synchronously. Callbacks will take care of handling errors
                // and updating our final overall result.
                request.executeAndWait();
            }
            return flushResults;
        }

        return null;
    }

    private static class FlushStatistics {
        public int numEvents = 0;
        public FlushResult result = FlushResult.SUCCESS;
    }

    private static GraphRequest buildRequestForSession(
            final AccessTokenAppIdPair accessTokenAppId,
            final SessionEventsState sessionEventsState,
            final boolean limitEventUsage,
            final FlushStatistics flushState) {
        String applicationId = accessTokenAppId.getApplicationId();

        Utility.FetchedAppSettings fetchedAppSettings =
                Utility.queryAppSettings(applicationId, false);

        final GraphRequest postRequest = GraphRequest.newPostRequest(
                null,
                String.format("%s/activities", applicationId),
                null,
                null);

        Bundle requestParameters = postRequest.getParameters();
        if (requestParameters == null) {
            requestParameters = new Bundle();
        }
        requestParameters.putString("access_token", accessTokenAppId.getAccessTokenString());
        postRequest.setParameters(requestParameters);

        if (fetchedAppSettings == null) {
            return null;
        }

        int numEvents = sessionEventsState.populateRequest(
                postRequest,
                fetchedAppSettings.supportsImplicitLogging(),
                limitEventUsage);

        if (numEvents == 0) {
            return null;
        }

        flushState.numEvents += numEvents;

        postRequest.setCallback(new GraphRequest.Callback() {
            @Override
            public void onCompleted(GraphResponse response) {
                handleResponse(accessTokenAppId, postRequest, response, sessionEventsState, flushState);
            }
        });

        return postRequest;
    }

    private static void handleResponse(
            AccessTokenAppIdPair accessTokenAppId,
            GraphRequest request,
            GraphResponse response,
            SessionEventsState sessionEventsState,
            FlushStatistics flushState) {
        FacebookRequestError error = response.getError();
        String resultDescription = "Success";

        FlushResult flushResult = FlushResult.SUCCESS;

        if (error != null) {
            final int NO_CONNECTIVITY_ERROR_CODE = -1;
            if (error.getErrorCode() == NO_CONNECTIVITY_ERROR_CODE) {
                resultDescription = "Failed: No Connectivity";
                flushResult = FlushResult.NO_CONNECTIVITY;
            } else {
                resultDescription = String.format("Failed:\n  Response: %s\n  Error %s",
                        response.toString(),
                        error.toString());
                flushResult = FlushResult.SERVER_ERROR;
            }
        }

        if (FacebookSdk.isLoggingBehaviorEnabled(LoggingBehavior.APP_EVENTS)) {
            String eventsJsonString = (String) request.getTag();
            String prettyPrintedEvents;

            try {
                JSONArray jsonArray = new JSONArray(eventsJsonString);
                prettyPrintedEvents = jsonArray.toString(2);
            } catch (JSONException exc) {
                prettyPrintedEvents = "<Can't encode events for debug logging>";
            }

            Logger.log(LoggingBehavior.APP_EVENTS, TAG,
                    "Flush completed\nParams: %s\n  Result: %s\n  Events JSON: %s",
                    request.getGraphObject().toString(),
                    resultDescription,
                    prettyPrintedEvents);
        }

        sessionEventsState.clearInFlightAndStats(error != null);

        if (flushResult == FlushResult.NO_CONNECTIVITY) {
            // We may call this for multiple requests in a batch, which is slightly inefficient
            // since in principle we could call it once for all failed requests, but the impact is
            // likely to be minimal. We don't call this for other server errors, because if an event
            // failed because it was malformed, etc., continually retrying it will cause subsequent
            // events to not be logged either.
            PersistedEvents.persistEvents(applicationContext, accessTokenAppId, sessionEventsState);
        }

        if (flushResult != FlushResult.SUCCESS) {
            // We assume that connectivity issues are more significant to report than server issues.
            if (flushState.result != FlushResult.NO_CONNECTIVITY) {
                flushState.result = flushResult;
            }
        }
    }

    private static int accumulatePersistedEvents() {
        PersistedEvents persistedEvents = PersistedEvents.readAndClearStore(applicationContext);

        int result = 0;
        for (AccessTokenAppIdPair accessTokenAppId : persistedEvents.keySet()) {
            SessionEventsState sessionEventsState =
                    getSessionEventsState(applicationContext, accessTokenAppId);

            List<AppEvent> events = persistedEvents.getEvents(accessTokenAppId);
            sessionEventsState.accumulatePersistedEvents(events);
            result += events.size();
        }

        return result;
    }

    /**
     * Invoke this method, rather than throwing an Exception, for situations where user/server input
     * might reasonably cause this to occur, and thus don't want an exception thrown at production
     * time, but do want logging notification.
     */
    private static void notifyDeveloperError(String message) {
        Logger.log(LoggingBehavior.DEVELOPER_ERRORS, "AppEvents", message);
    }

    /**
     * Source Application setters and getters
     */
    private static void setSourceApplication(Activity activity) {

        ComponentName callingApplication = activity.getCallingActivity();
        if (callingApplication != null) {
            String callingApplicationPackage = callingApplication.getPackageName();
            if (callingApplicationPackage.equals(activity.getPackageName())) {
                // open by own app.
                resetSourceApplication();
                return;
            }
            sourceApplication = callingApplicationPackage;
        }

        // Tap icon to open an app will still get the old intent if the activity was opened by an
        // intent before. Introduce an extra field in the intent to force clear the
        // sourceApplication.
        Intent openIntent = activity.getIntent();
        if (openIntent == null ||
                openIntent.getBooleanExtra(SOURCE_APPLICATION_HAS_BEEN_SET_BY_THIS_INTENT, false)) {
            resetSourceApplication();
            return;
        }

        Bundle applinkData = AppLinks.getAppLinkData(openIntent);

        if (applinkData == null) {
            resetSourceApplication();
            return;
        }

        isOpenedByApplink = true;

        Bundle applinkReferrerData = applinkData.getBundle("referer_app_link");

        if (applinkReferrerData == null) {
            sourceApplication = null;
            return;
        }

        String applinkReferrerPackage = applinkReferrerData.getString("package");
        sourceApplication = applinkReferrerPackage;

        // Mark this intent has been used to avoid use this intent again and again.
        openIntent.putExtra(SOURCE_APPLICATION_HAS_BEEN_SET_BY_THIS_INTENT, true);

        return;
    }

    static void setSourceApplication(String applicationPackage, boolean openByAppLink) {
        sourceApplication = applicationPackage;
        isOpenedByApplink = openByAppLink;
    }

    static String getSourceApplication() {
        String openType = "Unclassified";
        if (isOpenedByApplink) {
            openType = "Applink";
        }
        if (sourceApplication != null) {
            return openType + "(" + sourceApplication + ")";
        }
        return openType;
    }

    static void resetSourceApplication() {
        sourceApplication = null;
        isOpenedByApplink = false;
    }

    /**
     * Each app/device pair gets an GUID that is sent back with App Events and persisted with this
     * app/device pair.
     * @param context The application context.
     * @return The GUID for this app/device pair.
     */
    public static String getAnonymousAppDeviceGUID(Context context) {

        if (anonymousAppDeviceGUID == null) {
            synchronized (staticLock) {
                if (anonymousAppDeviceGUID == null) {

                    SharedPreferences preferences = context.getSharedPreferences(
                            APP_EVENT_PREFERENCES,
                            Context.MODE_PRIVATE);
                    anonymousAppDeviceGUID = preferences.getString("anonymousAppDeviceGUID", null);
                    if (anonymousAppDeviceGUID == null) {
                        // Arbitrarily prepend XZ to distinguish from device supplied identifiers.
                        anonymousAppDeviceGUID = "XZ" + UUID.randomUUID().toString();

                        context.getSharedPreferences(APP_EVENT_PREFERENCES, Context.MODE_PRIVATE)
                                .edit()
                                .putString("anonymousAppDeviceGUID", anonymousAppDeviceGUID)
                                .apply();
                    }
                }
            }
        }

        return anonymousAppDeviceGUID;
    }

    //
    // Deprecated Stuff
    //


    static class SessionEventsState {
        private List<AppEvent> accumulatedEvents = new ArrayList<AppEvent>();
        private List<AppEvent> inFlightEvents = new ArrayList<AppEvent>();
        private int numSkippedEventsDueToFullBuffer;
        private AttributionIdentifiers attributionIdentifiers;
        private String packageName;
        private String anonymousAppDeviceGUID;

        public static final String EVENT_COUNT_KEY = "event_count";
        public static final String ENCODED_EVENTS_KEY = "encoded_events";
        public static final String NUM_SKIPPED_KEY = "num_skipped";

        private final int MAX_ACCUMULATED_LOG_EVENTS = 1000;

        public SessionEventsState(
                AttributionIdentifiers identifiers,
                String packageName,
                String anonymousGUID) {
            this.attributionIdentifiers = identifiers;
            this.packageName = packageName;
            this.anonymousAppDeviceGUID = anonymousGUID;
        }

        // Synchronize here and in other methods on this class, because could be coming in from
        // different AppEventsLoggers on different threads pointing at the same session.
        public synchronized void addEvent(AppEvent event) {
            if (accumulatedEvents.size() + inFlightEvents.size() >= MAX_ACCUMULATED_LOG_EVENTS) {
                numSkippedEventsDueToFullBuffer++;
            } else {
                accumulatedEvents.add(event);
            }
        }

        public synchronized int getAccumulatedEventCount() {
            return accumulatedEvents.size();
        }

        public synchronized void clearInFlightAndStats(boolean moveToAccumulated) {
            if (moveToAccumulated) {
                accumulatedEvents.addAll(inFlightEvents);
            }
            inFlightEvents.clear();
            numSkippedEventsDueToFullBuffer = 0;
        }

        public int populateRequest(GraphRequest request, boolean includeImplicitEvents,
                                   boolean limitEventUsage) {

            int numSkipped;
            JSONArray jsonArray;
            synchronized (this) {
                numSkipped = numSkippedEventsDueToFullBuffer;

                // move all accumulated events to inFlight.
                inFlightEvents.addAll(accumulatedEvents);
                accumulatedEvents.clear();

                jsonArray = new JSONArray();
                for (AppEvent event : inFlightEvents) {
                    if (includeImplicitEvents || !event.getIsImplicit()) {
                        jsonArray.put(event.getJSONObject());
                    }
                }

                if (jsonArray.length() == 0) {
                    return 0;
                }
            }

            populateRequest(request, numSkipped, jsonArray, limitEventUsage);
            return jsonArray.length();
        }

        public synchronized List<AppEvent> getEventsToPersist() {
            // We will only persist accumulated events, not ones currently in-flight. This means if
            // an in-flight request fails, those requests will not be persisted and thus might be
            // lost if the process terminates while the flush is in progress.
            List<AppEvent> result = accumulatedEvents;
            accumulatedEvents = new ArrayList<AppEvent>();
            return result;
        }

        public synchronized void accumulatePersistedEvents(List<AppEvent> events) {
            // We won't skip events due to a full buffer, since we already accumulated them once and
            // persisted them. But they will count against the buffer size when further events are
            // accumulated.
            accumulatedEvents.addAll(events);
        }

        private void populateRequest(GraphRequest request, int numSkipped, JSONArray events,
                                     boolean limitEventUsage) {
            JSONObject publishParams = null;
            try {
                publishParams = AppEventsLoggerUtility.getJSONObjectForGraphAPICall(
                        AppEventsLoggerUtility.GraphAPIActivityType.CUSTOM_APP_EVENTS,
                        attributionIdentifiers,
                        anonymousAppDeviceGUID,
                        limitEventUsage,
                        applicationContext);

                if (numSkippedEventsDueToFullBuffer > 0) {
                    publishParams.put("num_skipped_events", numSkipped);
                }
            } catch (JSONException e) {
                // Swallow
                publishParams = new JSONObject();
            }
            request.setGraphObject(publishParams);

            Bundle requestParameters = request.getParameters();
            if (requestParameters == null) {
                requestParameters = new Bundle();
            }

            String jsonString = events.toString();
            if (jsonString != null) {
                requestParameters.putByteArray(
                        "custom_events_file",
                        getStringAsByteArray(jsonString));
                request.setTag(jsonString);
            }
            request.setParameters(requestParameters);
        }

        private byte[] getStringAsByteArray(String jsonString) {
            byte[] jsonUtf8 = null;
            try {
                jsonUtf8 = jsonString.getBytes("UTF-8");
            } catch (UnsupportedEncodingException e) {
                // shouldn't happen, but just in case:
                Utility.logd("Encoding exception: ", e);
            }
            return jsonUtf8;
        }
    }

    static class AppEvent implements Serializable {
        private static final long serialVersionUID = 1L;

        private JSONObject jsonObject;
        private boolean isImplicit;
        private static final HashSet<String> validatedIdentifiers = new HashSet<String>();
        private String name;

        public AppEvent(
                String uiName,
                String eventName,
                Double valueToSum,
                Bundle parameters,
                boolean isImplicitlyLogged
        ) {
            try {
                validateIdentifier(eventName);

                this.name = eventName;
                isImplicit = isImplicitlyLogged;
                jsonObject = new JSONObject();

                jsonObject.put("_eventName", eventName);
                jsonObject.put("_logTime", System.currentTimeMillis() / 1000);
                jsonObject.put("_ui", uiName);

                if (valueToSum != null) {
                    jsonObject.put("_valueToSum", valueToSum.doubleValue());
                }

                if (isImplicit) {
                    jsonObject.put("_implicitlyLogged", "1");
                }

                if (parameters != null) {
                    for (String key : parameters.keySet()) {

                        validateIdentifier(key);

                        Object value = parameters.get(key);
                        if (!(value instanceof String) && !(value instanceof Number)) {
                            throw new FacebookException(
                                    String.format(
                                            "Parameter value '%s' for key '%s' should be a string" +
                                                    " or a numeric type.",
                                            value,
                                            key)
                            );
                        }

                        jsonObject.put(key, value.toString());
                    }
                }

                if (!isImplicit) {
                    Logger.log(LoggingBehavior.APP_EVENTS, "AppEvents",
                            "Created app event '%s'", jsonObject.toString());
                }
            } catch (JSONException jsonException) {

                // If any of the above failed, just consider this an illegal event.
                Logger.log(LoggingBehavior.APP_EVENTS, "AppEvents",
                        "JSON encoding for app event failed: '%s'", jsonException.toString());
                jsonObject = null;

            } catch (FacebookException e) {
                // If any of the above failed, just consider this an illegal event.
                Logger.log(LoggingBehavior.APP_EVENTS, "AppEvents",
                        "Invalid app event name or parameter:", e.toString());
                jsonObject = null;
            }
        }

        public String getName() {
            return name;
        }

        private AppEvent(String jsonString, boolean isImplicit) throws JSONException {
            jsonObject = new JSONObject(jsonString);
            this.isImplicit = isImplicit;
        }

        public boolean getIsImplicit() {
            return isImplicit;
        }

        public JSONObject getJSONObject() {
            return jsonObject;
        }

        // throw exception if not valid.
        private void validateIdentifier(String identifier) throws FacebookException {

            // Identifier should be 40 chars or less, and only have 0-9A-Za-z, underscore, hyphen,
            // and space (but no hyphen or space in the first position).
            final String regex = "^[0-9a-zA-Z_]+[0-9a-zA-Z _-]*$";

            final int MAX_IDENTIFIER_LENGTH = 40;
            if (identifier == null
                    || identifier.length() == 0
                    || identifier.length() > MAX_IDENTIFIER_LENGTH) {
                if (identifier == null) {
                    identifier = "<None Provided>";
                }
                throw new FacebookException(
                    String.format(
                            Locale.ROOT,
                            "Identifier '%s' must be less than %d characters",
                            identifier,
                            MAX_IDENTIFIER_LENGTH)
                );
            }

            boolean alreadyValidated = false;
            synchronized (validatedIdentifiers) {
                alreadyValidated = validatedIdentifiers.contains(identifier);
            }

            if (!alreadyValidated) {
                if (identifier.matches(regex)) {
                    synchronized (validatedIdentifiers) {
                        validatedIdentifiers.add(identifier);
                    }
                } else {
                    throw new FacebookException(
                            String.format(
                                    "Skipping event named '%s' due to illegal name - must be " +
                                            "under 40 chars and alphanumeric, _, - or space, and " +
                                            "not start with a space or hyphen.",
                                    identifier
                            )
                    );
                }
            }
        }

        private static class SerializationProxyV1 implements Serializable {
            private static final long serialVersionUID = -2488473066578201069L;
            private final String jsonString;
            private final boolean isImplicit;

            private SerializationProxyV1(String jsonString, boolean isImplicit) {
                this.jsonString = jsonString;
                this.isImplicit = isImplicit;
            }

            private Object readResolve() throws JSONException {
                return new AppEvent(jsonString, isImplicit);
            }
        }

        private Object writeReplace() {
            return new SerializationProxyV1(jsonObject.toString(), isImplicit);
        }

        @Override
        public String toString() {
            return String.format(
                    "\"%s\", implicit: %b, json: %s",
                    jsonObject.optString("_eventName"),
                    isImplicit,
                    jsonObject.toString());
        }
    }

    static class PersistedAppSessionInfo {
        private static final String PERSISTED_SESSION_INFO_FILENAME =
                "AppEventsLogger.persistedsessioninfo";

        private static final Object staticLock = new Object();
        private static boolean hasChanges = false;
        private static boolean isLoaded = false;
        private static Map<AccessTokenAppIdPair, FacebookTimeSpentData> appSessionInfoMap;

        private static final Runnable appSessionInfoFlushRunnable = new Runnable() {
            @Override
            public void run() {
                PersistedAppSessionInfo.saveAppSessionInformation(applicationContext);
            }
        };

        @SuppressWarnings("unchecked")
        private static void restoreAppSessionInformation(Context context) {
            ObjectInputStream ois = null;

            synchronized (staticLock) {
                if (!isLoaded) {
                    try {
                        ois =
                                new ObjectInputStream(
                                        context.openFileInput(PERSISTED_SESSION_INFO_FILENAME));
                        appSessionInfoMap = (HashMap<AccessTokenAppIdPair, FacebookTimeSpentData>)
                                ois.readObject();
                        Logger.log(
                                LoggingBehavior.APP_EVENTS,
                                "AppEvents",
                                "App session info loaded");
                    } catch (FileNotFoundException fex) {
                    } catch (Exception e) {
                        Log.d(TAG, "Got unexpected exception: " + e.toString());
                    } finally {
                        Utility.closeQuietly(ois);
                        context.deleteFile(PERSISTED_SESSION_INFO_FILENAME);
                        if (appSessionInfoMap == null) {
                            appSessionInfoMap =
                                    new HashMap<AccessTokenAppIdPair, FacebookTimeSpentData>();
                        }
                        // Regardless of the outcome of the load, the session information cache
                        // is always deleted. Therefore, always treat the session information cache
                        // as loaded
                        isLoaded = true;
                        hasChanges = false;
                    }
                }
            }
        }

        static void saveAppSessionInformation(Context context) {
            ObjectOutputStream oos = null;

            synchronized (staticLock) {
                if (hasChanges) {
                    try {
                        oos = new ObjectOutputStream(
                                new BufferedOutputStream(
                                        context.openFileOutput(
                                                PERSISTED_SESSION_INFO_FILENAME,
                                                Context.MODE_PRIVATE)
                                )
                        );
                        oos.writeObject(appSessionInfoMap);
                        hasChanges = false;
                        Logger.log(
                                LoggingBehavior.APP_EVENTS,
                                "AppEvents",
                                "App session info saved");
                    } catch (Exception e) {
                        Log.d(TAG, "Got unexpected exception: " + e.toString());
                    } finally {
                        Utility.closeQuietly(oos);
                    }
                }
            }
        }

        static void onResume(
                Context context,
                AccessTokenAppIdPair accessTokenAppId,
                AppEventsLogger logger,
                long eventTime,
                String sourceApplicationInfo
        ) {
            synchronized (staticLock) {
                FacebookTimeSpentData timeSpentData = getTimeSpentData(context, accessTokenAppId);
                timeSpentData.onResume(logger, eventTime, sourceApplicationInfo);
                onTimeSpentDataUpdate();
            }
        }

        static void onSuspend(
                Context context,
                AccessTokenAppIdPair accessTokenAppId,
                AppEventsLogger logger,
                long eventTime
        ) {
            synchronized (staticLock) {
                FacebookTimeSpentData timeSpentData = getTimeSpentData(context, accessTokenAppId);
                timeSpentData.onSuspend(logger, eventTime);
                onTimeSpentDataUpdate();
            }
        }

        private static FacebookTimeSpentData getTimeSpentData(
                Context context,
                AccessTokenAppIdPair accessTokenAppId
        ) {
            restoreAppSessionInformation(context);
            FacebookTimeSpentData result = null;

            result = appSessionInfoMap.get(accessTokenAppId);
            if (result == null) {
                result = new FacebookTimeSpentData();
                appSessionInfoMap.put(accessTokenAppId, result);
            }

            return result;
        }

        private static void onTimeSpentDataUpdate() {
            if (!hasChanges) {
                hasChanges = true;
                backgroundExecutor.schedule(
                        appSessionInfoFlushRunnable,
                        FLUSH_APP_SESSION_INFO_IN_SECONDS,
                        TimeUnit.SECONDS);
            }
        }
    }

    // Read/write operations are thread-safe/atomic across all instances of PersistedEvents, but
    // modifications to any individual instance are not thread-safe.
    static class PersistedEvents {
        static final String PERSISTED_EVENTS_FILENAME = "AppEventsLogger.persistedevents";

        private static Object staticLock = new Object();

        private Context context;
        private HashMap<AccessTokenAppIdPair, List<AppEvent>> persistedEvents =
                new HashMap<AccessTokenAppIdPair, List<AppEvent>>();

        private PersistedEvents(Context context) {
            this.context = context;
        }

        public static PersistedEvents readAndClearStore(Context context) {
            synchronized (staticLock) {
                PersistedEvents persistedEvents = new PersistedEvents(context);

                persistedEvents.readAndClearStore();

                return persistedEvents;
            }
        }

        public static void persistEvents(Context context, AccessTokenAppIdPair accessTokenAppId,
                                         SessionEventsState eventsToPersist) {
            Map<AccessTokenAppIdPair, SessionEventsState> map = new HashMap<AccessTokenAppIdPair, SessionEventsState>();
            map.put(accessTokenAppId, eventsToPersist);
            persistEvents(context, map);
        }

        public static void persistEvents(
                Context context,
                Map<AccessTokenAppIdPair,
                        SessionEventsState> eventsToPersist) {
            synchronized (staticLock) {
                // Note that we don't track which instance of AppEventsLogger added a particular
                // event to SessionEventsState; when a particular Context is being destroyed, we'll
                // persist all accumulated events. More sophisticated tracking could be done to try
                // to reduce unnecessary persisting of events, but the overall number of events is
                // not expected to be large.
                PersistedEvents persistedEvents = readAndClearStore(context);

                for (Map.Entry<AccessTokenAppIdPair, SessionEventsState> entry
                        : eventsToPersist.entrySet()) {
                    List<AppEvent> events = entry.getValue().getEventsToPersist();
                    if (events.size() == 0) {
                        continue;
                    }

                    persistedEvents.addEvents(entry.getKey(), events);
                }

                persistedEvents.write();
            }
        }

        public Set<AccessTokenAppIdPair> keySet() {
            return persistedEvents.keySet();
        }

        public List<AppEvent> getEvents(AccessTokenAppIdPair accessTokenAppId) {
            return persistedEvents.get(accessTokenAppId);
        }

        private void write() {
            ObjectOutputStream oos = null;
            try {
                oos = new ObjectOutputStream(
                        new BufferedOutputStream(
                                context.openFileOutput(PERSISTED_EVENTS_FILENAME, 0)));
                oos.writeObject(persistedEvents);
            } catch (Exception e) {
                Log.d(TAG, "Got unexpected exception: " + e.toString());
            } finally {
                Utility.closeQuietly(oos);
            }
        }

        private void readAndClearStore() {
            ObjectInputStream ois = null;
            try {
                ois = new ObjectInputStream(
                        new BufferedInputStream(context.openFileInput(PERSISTED_EVENTS_FILENAME)));

                @SuppressWarnings("unchecked")
                HashMap<AccessTokenAppIdPair, List<AppEvent>> obj =
                        (HashMap<AccessTokenAppIdPair, List<AppEvent>>) ois.readObject();

                // Note: We delete the store before we store the events; this means we'd prefer to
                // lose some events in the case of exception rather than potentially log them twice.
                context.getFileStreamPath(PERSISTED_EVENTS_FILENAME).delete();
                persistedEvents = obj;
            } catch (FileNotFoundException e) {
                // Expected if we never persisted any events.
            } catch (Exception e) {
                Log.d(TAG, "Got unexpected exception: " + e.toString());
            } finally {
                Utility.closeQuietly(ois);
            }
        }

        public void addEvents(
                AccessTokenAppIdPair accessTokenAppId,
                List<AppEvent> eventsToPersist) {
            if (!persistedEvents.containsKey(accessTokenAppId)) {
                persistedEvents.put(accessTokenAppId, new ArrayList<AppEvent>());
            }
            persistedEvents.get(accessTokenAppId).addAll(eventsToPersist);
        }
    }
}


File: facebook/src/com/facebook/internal/AttributionIdentifiers.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook.internal;

import android.content.Context;
import android.database.Cursor;
import android.net.Uri;
import android.os.Looper;
import android.util.Log;

import com.facebook.FacebookException;

import java.lang.reflect.Method;

/**
 * com.facebook.internal is solely for the use of other packages within the Facebook SDK for
 * Android. Use of any of the classes in this package is unsupported, and they may be modified or
 * removed without warning at any time.
 */
public class AttributionIdentifiers {
    private static final String TAG = AttributionIdentifiers.class.getCanonicalName();
    private static final String ATTRIBUTION_ID_CONTENT_PROVIDER =
            "com.facebook.katana.provider.AttributionIdProvider";
    private static final String ATTRIBUTION_ID_CONTENT_PROVIDER_WAKIZASHI =
            "com.facebook.wakizashi.provider.AttributionIdProvider";
    private static final String ATTRIBUTION_ID_COLUMN_NAME = "aid";
    private static final String ANDROID_ID_COLUMN_NAME = "androidid";
    private static final String LIMIT_TRACKING_COLUMN_NAME = "limit_tracking";

    // com.google.android.gms.common.ConnectionResult.SUCCESS
    private static final int CONNECTION_RESULT_SUCCESS = 0;

    private static final long IDENTIFIER_REFRESH_INTERVAL_MILLIS = 3600 * 1000;

    private String attributionId;
    private String androidAdvertiserId;
    private boolean limitTracking;
    private long fetchTime;

    private static AttributionIdentifiers recentlyFetchedIdentifiers;

    private static AttributionIdentifiers getAndroidId(Context context) {
        AttributionIdentifiers identifiers = new AttributionIdentifiers();
        try {
            // We can't call getAdvertisingIdInfo on the main thread or the app will potentially
            // freeze, if this is the case throw:
            if (Looper.myLooper() == Looper.getMainLooper()) {
              throw new FacebookException("getAndroidId cannot be called on the main thread.");
            }
            Method isGooglePlayServicesAvailable = Utility.getMethodQuietly(
                    "com.google.android.gms.common.GooglePlayServicesUtil",
                    "isGooglePlayServicesAvailable",
                    Context.class
            );

            if (isGooglePlayServicesAvailable == null) {
                return identifiers;
            }

            Object connectionResult = Utility.invokeMethodQuietly(
                    null, isGooglePlayServicesAvailable, context);
            if (!(connectionResult instanceof Integer)
                    || (Integer) connectionResult != CONNECTION_RESULT_SUCCESS) {
                return identifiers;
            }

            Method getAdvertisingIdInfo = Utility.getMethodQuietly(
                    "com.google.android.gms.ads.identifier.AdvertisingIdClient",
                    "getAdvertisingIdInfo",
                    Context.class
            );
            if (getAdvertisingIdInfo == null) {
                return identifiers;
            }
            Object advertisingInfo = Utility.invokeMethodQuietly(
                    null, getAdvertisingIdInfo, context);
            if (advertisingInfo == null) {
                return identifiers;
            }

            Method getId = Utility.getMethodQuietly(advertisingInfo.getClass(), "getId");
            Method isLimitAdTrackingEnabled = Utility.getMethodQuietly(
                    advertisingInfo.getClass(),
                    "isLimitAdTrackingEnabled");
            if (getId == null || isLimitAdTrackingEnabled == null) {
                return identifiers;
            }

            identifiers.androidAdvertiserId =
                    (String) Utility.invokeMethodQuietly(advertisingInfo, getId);
            identifiers.limitTracking = (Boolean) Utility.invokeMethodQuietly(
                    advertisingInfo,
                    isLimitAdTrackingEnabled);
        } catch (Exception e) {
            Utility.logd("android_id", e);
        }
        return identifiers;
    }

    public static AttributionIdentifiers getAttributionIdentifiers(Context context) {
        if (recentlyFetchedIdentifiers != null &&
            System.currentTimeMillis() - recentlyFetchedIdentifiers.fetchTime <
                    IDENTIFIER_REFRESH_INTERVAL_MILLIS) {
            return recentlyFetchedIdentifiers;
        }

        AttributionIdentifiers identifiers = getAndroidId(context);
        Cursor c = null;
        try {
            String [] projection = {
                    ATTRIBUTION_ID_COLUMN_NAME,
                    ANDROID_ID_COLUMN_NAME,
                    LIMIT_TRACKING_COLUMN_NAME};
            Uri providerUri = null;
            if (context.getPackageManager().resolveContentProvider(
                    ATTRIBUTION_ID_CONTENT_PROVIDER, 0) != null) {
                providerUri = Uri.parse("content://" + ATTRIBUTION_ID_CONTENT_PROVIDER);
            } else if (context.getPackageManager().resolveContentProvider(
                    ATTRIBUTION_ID_CONTENT_PROVIDER_WAKIZASHI, 0) != null) {
                providerUri = Uri.parse("content://" + ATTRIBUTION_ID_CONTENT_PROVIDER_WAKIZASHI);
            }
            if (providerUri == null) {
                return identifiers;
            }
            c = context.getContentResolver().query(providerUri, projection, null, null, null);
            if (c == null || !c.moveToFirst()) {
                return identifiers;
            }
            int attributionColumnIndex = c.getColumnIndex(ATTRIBUTION_ID_COLUMN_NAME);
            int androidIdColumnIndex = c.getColumnIndex(ANDROID_ID_COLUMN_NAME);
            int limitTrackingColumnIndex = c.getColumnIndex(LIMIT_TRACKING_COLUMN_NAME);

            identifiers.attributionId = c.getString(attributionColumnIndex);

            // if we failed to call Google's APIs directly (due to improper integration by the
            // client), it may be possible for the local facebook application to relay it to us.
            if (androidIdColumnIndex > 0 && limitTrackingColumnIndex > 0 &&
                    identifiers.getAndroidAdvertiserId() == null) {
                identifiers.androidAdvertiserId = c.getString(androidIdColumnIndex);
                identifiers.limitTracking =
                        Boolean.parseBoolean(c.getString(limitTrackingColumnIndex));
            }
        } catch (Exception e) {
            Log.d(TAG, "Caught unexpected exception in getAttributionId(): " + e.toString());
            return null;
        } finally {
            if (c != null) {
                c.close();
            }
        }

        identifiers.fetchTime = System.currentTimeMillis();
        recentlyFetchedIdentifiers = identifiers;
        return identifiers;
    }

    public String getAttributionId() {
        return attributionId;
    }

    public String getAndroidAdvertiserId() {
        return androidAdvertiserId;
    }

    public boolean isTrackingLimited() {
        return limitTracking;
    }
}


File: facebook/src/com/facebook/login/LoginManager.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook.login;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.ResolveInfo;
import android.os.Bundle;
import android.support.v4.app.Fragment;
import android.content.Context;

import com.facebook.AccessToken;
import com.facebook.CallbackManager;
import com.facebook.FacebookActivity;
import com.facebook.FacebookAuthorizationException;
import com.facebook.FacebookCallback;
import com.facebook.FacebookException;
import com.facebook.FacebookSdk;
import com.facebook.GraphResponse;
import com.facebook.Profile;
import com.facebook.internal.CallbackManagerImpl;
import com.facebook.internal.Validate;
import com.facebook.appevents.AppEventsConstants;

import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * This class manages login and permissions for Facebook.
 */
public class LoginManager {
    private static final String PUBLISH_PERMISSION_PREFIX = "publish";
    private static final String MANAGE_PERMISSION_PREFIX = "manage";
    private static final Set<String> OTHER_PUBLISH_PERMISSIONS = getOtherPublishPermissions();

    private static volatile LoginManager instance;

    private LoginBehavior loginBehavior = LoginBehavior.SSO_WITH_FALLBACK;
    private DefaultAudience defaultAudience = DefaultAudience.FRIENDS;
    private LoginClient.Request pendingLoginRequest;
    private HashMap<String, String> pendingLoggingExtras;
    private LoginLogger loginLogger;

    LoginManager() {
        Validate.sdkInitialized();
    }

    /**
     * Getter for the login manager.
     * @return The login manager.
     */
    public static LoginManager getInstance() {
        if (instance == null) {
            synchronized (LoginManager.class) {
                if (instance == null) {
                    instance = new LoginManager();
                }
            }
        }

        return instance;
    }

    /**
     * Starts the login process to resolve the error defined in the response. The registered login
     * callbacks will be called on completion.
     *
     * @param activity The activity which is starting the login process.
     * @param response The response that has the error.
     */
    public void resolveError(final Activity activity, final GraphResponse response) {
        startLogin(
                new ActivityStartActivityDelegate(activity),
                createLoginRequestFromResponse(response)
        );
    }

    /**
     * Starts the login process to resolve the error defined in the response. The registered login
     * callbacks will be called on completion.
     *
     * @param fragment The fragment which is starting the login process.
     * @param response The response that has the error.
     */
    public void resolveError(final Fragment fragment, final GraphResponse response) {
        startLogin(
                new FragmentStartActivityDelegate(fragment),
                createLoginRequestFromResponse(response)
        );
    }

    private LoginClient.Request createLoginRequestFromResponse(final GraphResponse response) {
        Validate.notNull(response, "response");
        AccessToken failedToken = response.getRequest().getAccessToken();
        return createLoginRequest(failedToken != null ? failedToken.getPermissions() : null);
    }

    /**
     * Registers a login callback to the given callback manager.
     * @param callbackManager The callback manager that will encapsulate the callback.
     * @param callback The login callback that will be called on login completion.
     */
    public void registerCallback(
            final CallbackManager callbackManager,
            final FacebookCallback<LoginResult> callback) {
        if (!(callbackManager instanceof CallbackManagerImpl)) {
            throw new FacebookException("Unexpected CallbackManager, " +
                    "please use the provided Factory.");
        }
        ((CallbackManagerImpl) callbackManager).registerCallback(
                CallbackManagerImpl.RequestCodeOffset.Login.toRequestCode(),
                new CallbackManagerImpl.Callback() {
                    @Override
                    public boolean onActivityResult(int resultCode, Intent data) {
                        return LoginManager.this.onActivityResult(
                                resultCode,
                                data,
                                callback);
                    }
                }
        );
    }

    boolean onActivityResult(int resultCode, Intent data) {
        return onActivityResult(resultCode, data, null);
    }

    boolean onActivityResult(int resultCode, Intent data, FacebookCallback<LoginResult>  callback) {

        if (pendingLoginRequest == null) {
            return false;
        }

        FacebookException exception = null;
        AccessToken newToken = null;
        LoginClient.Result.Code code = LoginClient.Result.Code.ERROR;
        Map<String, String> loggingExtras = null;

        boolean isCanceled = false;
        if (data != null) {
            LoginClient.Result result = (LoginClient.Result)
                    data.getParcelableExtra(LoginFragment.RESULT_KEY);
            if (result != null) {
                code = result.code;
                if (resultCode == Activity.RESULT_OK) {
                    if (result.code == LoginClient.Result.Code.SUCCESS) {
                        newToken = result.token;
                    } else {
                        exception = new FacebookAuthorizationException(result.errorMessage);
                    }
                } else if (resultCode == Activity.RESULT_CANCELED) {
                    isCanceled = true;
                }
                loggingExtras = result.loggingExtras;
            }
        } else if (resultCode == Activity.RESULT_CANCELED) {
            isCanceled = true;
            code = LoginClient.Result.Code.CANCEL;
        }

        if (exception == null && newToken == null && !isCanceled) {
            exception = new FacebookException("Unexpected call to LoginManager.onActivityResult");
        }

        logCompleteLogin(code, loggingExtras, exception);

        finishLogin(newToken, exception, isCanceled, callback);

        return true;
    }

    /**
     * Getter for the login behavior.
     * @return the login behavior.
     */
    public LoginBehavior getLoginBehavior() {
        return loginBehavior;
    }

    /**
     * Setter for the login behavior.
     * @param loginBehavior The login behavior.
     * @return The login manager.
     */
    public LoginManager setLoginBehavior(LoginBehavior loginBehavior) {
        this.loginBehavior = loginBehavior;
        return this;
    }

    /**
     * Getter for the default audience.
     * @return The default audience.
     */
    public DefaultAudience getDefaultAudience() {
        return defaultAudience;
    }

    /**
     * Setter for the default audience.
     * @param defaultAudience The default audience.
     * @return The login manager.
     */
    public LoginManager setDefaultAudience(DefaultAudience defaultAudience) {
        this.defaultAudience = defaultAudience;
        return this;
    }

    /**
     * Logs out the user.
     */
    public void logOut() {
        AccessToken.setCurrentAccessToken(null);
        Profile.setCurrentProfile(null);
    }

    /**
     * Logs the user in with the requested read permissions.
     * @param fragment    The fragment which is starting the login process.
     * @param permissions The requested permissions.
     */
    public void logInWithReadPermissions(Fragment fragment, Collection<String> permissions) {
        validateReadPermissions(permissions);

        LoginClient.Request loginRequest = createLoginRequest(permissions);
        startLogin(new FragmentStartActivityDelegate(fragment), loginRequest);
    }

    /**
     * Logs the user in with the requested read permissions.
     * @param activity    The activity which is starting the login process.
     * @param permissions The requested permissions.
     */
    public void logInWithReadPermissions(Activity activity, Collection<String> permissions) {
        validateReadPermissions(permissions);

        LoginClient.Request loginRequest = createLoginRequest(permissions);
        startLogin(new ActivityStartActivityDelegate(activity), loginRequest);
    }

    /**
     * Logs the user in with the requested publish permissions.
     * @param fragment    The fragment which is starting the login process.
     * @param permissions The requested permissions.
     */
    public void logInWithPublishPermissions(Fragment fragment, Collection<String> permissions) {
        validatePublishPermissions(permissions);

        LoginClient.Request loginRequest = createLoginRequest(permissions);
        startLogin(new FragmentStartActivityDelegate(fragment), loginRequest);
    }

    /**
     * Logs the user in with the requested publish permissions.
     * @param activity    The activity which is starting the login process.
     * @param permissions The requested permissions.
     */
    public void logInWithPublishPermissions(Activity activity, Collection<String> permissions) {
        validatePublishPermissions(permissions);

        LoginClient.Request loginRequest = createLoginRequest(permissions);
        startLogin(new ActivityStartActivityDelegate(activity), loginRequest);
    }

    LoginClient.Request getPendingLoginRequest() {
        return pendingLoginRequest;
    }

    private void validateReadPermissions(Collection<String> permissions) {
        if (permissions == null) {
            return;
        }
        for (String permission : permissions) {
            if (isPublishPermission(permission)) {
                throw new FacebookException(
                    String.format(
                        "Cannot pass a publish or manage permission (%s) to a request for read " +
                                "authorization",
                        permission));
            }
        }
    }

    private void validatePublishPermissions(Collection<String> permissions) {
        if (permissions == null) {
            return;
        }
        for (String permission : permissions) {
            if (!isPublishPermission(permission)) {
                throw new FacebookException(
                    String.format(
                        "Cannot pass a read permission (%s) to a request for publish authorization",
                        permission));
            }
        }
    }

    static boolean isPublishPermission(String permission) {
        return permission != null &&
            (permission.startsWith(PUBLISH_PERMISSION_PREFIX) ||
                permission.startsWith(MANAGE_PERMISSION_PREFIX) ||
                OTHER_PUBLISH_PERMISSIONS.contains(permission));
    }

    private static Set<String> getOtherPublishPermissions() {
        HashSet<String> set = new HashSet<String>() {{
            add("ads_management");
            add("create_event");
            add("rsvp_event");
        }};
        return Collections.unmodifiableSet(set);
    }

    private LoginClient.Request createLoginRequest(Collection<String> permissions) {
        LoginClient.Request request = new LoginClient.Request(
                loginBehavior,
                Collections.unmodifiableSet(
                        permissions != null ? new HashSet(permissions) : new HashSet<String>()),
                defaultAudience,
                FacebookSdk.getApplicationId(),
                UUID.randomUUID().toString()
        );
        request.setRerequest(AccessToken.getCurrentAccessToken() != null);
        return request;
    }

    private void startLogin(
            StartActivityDelegate startActivityDelegate,
            LoginClient.Request request
    ) throws FacebookException {

        this.pendingLoginRequest = request;
        this.pendingLoggingExtras = new HashMap<>();
        this.loginLogger = getLoggerForContext(startActivityDelegate.getActivityContext());

        logStartLogin();

        // Make sure the static handler for login is registered if there isn't an explicit callback
        CallbackManagerImpl.registerStaticCallback(
                CallbackManagerImpl.RequestCodeOffset.Login.toRequestCode(),
                new CallbackManagerImpl.Callback() {
                    @Override
                    public boolean onActivityResult(int resultCode, Intent data) {
                        return LoginManager.this.onActivityResult(resultCode, data);
                    }
                }
        );

        boolean started = tryFacebookActivity(startActivityDelegate, request);

        pendingLoggingExtras.put(
                LoginLogger.EVENT_EXTRAS_TRY_LOGIN_ACTIVITY,
                started ?
                AppEventsConstants.EVENT_PARAM_VALUE_YES : AppEventsConstants.EVENT_PARAM_VALUE_NO
        );

        if (!started) {
            FacebookException exception = new FacebookException(
                    "Log in attempt failed: FacebookActivity could not be started." +
                            " Please make sure you added FacebookActivity to the AndroidManifest.");
            logCompleteLogin(LoginClient.Result.Code.ERROR, null, exception);
            this.pendingLoginRequest = null;
            throw exception;
        }
    }

    private LoginLogger getLoggerForContext(Context context) {
        if (loginLogger == null ||
                !loginLogger.getApplicationId().equals(
                        pendingLoginRequest.getApplicationId())) {
            return new LoginLogger(
                    context,
                    pendingLoginRequest.getApplicationId());
        }
        return loginLogger;
    }

    private void logStartLogin() {
        if (loginLogger != null) {
            loginLogger.logStartLogin(pendingLoginRequest);
        }
    }

    private void logCompleteLogin(LoginClient.Result.Code result, Map<String, String> resultExtras,
                                  Exception exception) {
        if (loginLogger == null) {
            return;
        }
        if (pendingLoginRequest == null) {
            // We don't expect this to happen, but if it does, log an event for diagnostic purposes.
            loginLogger.logUnexpectedError(
                    LoginLogger.EVENT_NAME_LOGIN_COMPLETE,
                    "Unexpected call to logCompleteLogin with null pendingAuthorizationRequest."
            );
        } else {
            loginLogger.logCompleteLogin(
                    pendingLoginRequest.getAuthId(),
                    pendingLoggingExtras,
                    result,
                    resultExtras,
                    exception);
        }
    }

    private boolean tryFacebookActivity(
            StartActivityDelegate startActivityDelegate,
            LoginClient.Request request) {

        Intent intent = getFacebookActivityIntent(request);

        if (!resolveIntent(intent)) {
            return false;
        }

        try {
            startActivityDelegate.startActivityForResult(
                    intent,
                    LoginClient.getLoginRequestCode());
        } catch (ActivityNotFoundException e) {
            return false;
        }

        return true;
    }

    private boolean resolveIntent(Intent intent) {
        ResolveInfo resolveInfo = FacebookSdk.getApplicationContext().getPackageManager()
            .resolveActivity(intent, 0);
        if (resolveInfo == null) {
            return false;
        }
        return true;
    }

    private Intent getFacebookActivityIntent(LoginClient.Request request) {
        Intent intent = new Intent();
        intent.setClass(FacebookSdk.getApplicationContext(), FacebookActivity.class);
        intent.setAction(request.getLoginBehavior().toString());

        // Let FacebookActivity populate extras appropriately
        LoginClient.Request authClientRequest = request;
        Bundle extras = LoginFragment.populateIntentExtras(authClientRequest);
        intent.putExtras(extras);

        return intent;
    }

    static LoginResult computeLoginResult(
            final LoginClient.Request request,
            final AccessToken newToken
    ) {
        Set<String> requestedPermissions = request.getPermissions();
        Set<String> grantedPermissions = new HashSet<String>(newToken.getPermissions());

        // If it's a reauth, subset the granted permissions to just the requested permissions
        // so we don't report implicit permissions like user_profile as recently granted.
        if (request.isRerequest()) {
            grantedPermissions.retainAll(requestedPermissions);
        }

        Set<String> deniedPermissions = new HashSet<String>(requestedPermissions);
        deniedPermissions.removeAll(grantedPermissions);
        return new LoginResult(newToken, grantedPermissions, deniedPermissions);
    }

    private void finishLogin(
            AccessToken newToken,
            FacebookException exception,
            boolean isCanceled,
            FacebookCallback<LoginResult>  callback) {
        if (newToken != null) {
            AccessToken.setCurrentAccessToken(newToken);
            Profile.fetchProfileForCurrentAccessToken();
        }

        if (callback != null) {
            LoginResult loginResult = newToken != null
                    ? computeLoginResult(pendingLoginRequest, newToken)
                    : null;
            // If there are no granted permissions, the operation is treated as cancel.
            if (isCanceled
                    || (loginResult != null
                           && loginResult.getRecentlyGrantedPermissions().size() == 0)) {
                callback.onCancel();
            } else if (exception != null) {
                callback.onError(exception);
            } else if (newToken != null) {
                callback.onSuccess(loginResult);
            }
        }

        pendingLoginRequest = null;
    }

    private static class ActivityStartActivityDelegate implements StartActivityDelegate {
        private final Activity activity;

        ActivityStartActivityDelegate(final Activity activity) {
            Validate.notNull(activity, "activity");
            this.activity = activity;
        }

        @Override
        public void startActivityForResult(Intent intent, int requestCode) {
            activity.startActivityForResult(intent, requestCode);
        }

        @Override
        public Activity getActivityContext() {
            return activity;
        }
    }

    private static class FragmentStartActivityDelegate implements StartActivityDelegate {
        private final Fragment fragment;

        FragmentStartActivityDelegate(final Fragment fragment) {
            Validate.notNull(fragment, "fragment");
            this.fragment = fragment;
        }

        @Override
        public void startActivityForResult(Intent intent, int requestCode) {
            fragment.startActivityForResult(intent, requestCode);
        }

        @Override
        public Activity getActivityContext() {
            return fragment.getActivity();
        }
    }
}


File: facebook/src/com/facebook/share/model/ShareMedia.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook.share.model;

import android.os.Bundle;
import android.os.Parcel;

/**
 * Base class for shared media (photos, videos, etc).
 */
public abstract class ShareMedia implements ShareModel {

    private final Bundle params;

    protected ShareMedia(final Builder builder) {
        this.params = new Bundle(builder.params);
    }

    ShareMedia(final Parcel in) {
        this.params = in.readBundle();
    }

    /**
     * Returns the parameters associated with the shared media.
     *
     * @return the parameters of the share.
     */
    public Bundle getParameters() {
        return new Bundle(params);
    }

    @Override
    public int describeContents() {
        return 0;
    }

    @Override
    public void writeToParcel(Parcel dest, int flags) {
        dest.writeBundle(params);
    }

    /**
     * Builder for the {@link com.facebook.share.model.ShareMedia} class.
     */
    public static abstract class Builder<M extends ShareMedia, B extends Builder>
            implements ShareModelBuilder<M, B> {
        private Bundle params = new Bundle();

        /**
         * Set a parameter for the shared media.
         * @param key the key.
         * @param value the value.
         * @return the builder.
         */
        public B setParameter(final String key, final String value) {
            params.putString(key, value);
            return (B) this;
        }

        /**
         * Set the parameters for the shared media.
         * @param parameters a bundle containing the parameters for the share.
         * @return the builder.
         */
        public B setParameters(final Bundle parameters) {
            params.putAll(parameters);
            return (B) this;
        }

        @Override
        public B readFrom(final M model) {
            if (model == null) {
                return (B) this;
            }
            return this.setParameters(model.getParameters());
        }
    }
}


File: facebook/tests/src/com/facebook/appevents/AppEventsLoggerTests.java
/**
 * Copyright (c) 2014-present, Facebook, Inc. All rights reserved.
 *
 * You are hereby granted a non-exclusive, worldwide, royalty-free license to use,
 * copy, modify, and distribute this software in source code or binary form for use
 * in connection with the web services and APIs provided by Facebook.
 *
 * As with any software that integrates with the Facebook platform, your use of
 * this software is subject to the Facebook Developer Principles and Policies
 * [http://developers.facebook.com/policy/]. This copyright notice shall be
 * included in all copies or substantial portions of the software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 * COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 * IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.facebook.appevents;

import android.content.Intent;
import android.content.IntentFilter;
import android.os.Bundle;
import android.support.v4.content.LocalBroadcastManager;

import com.facebook.AccessToken;
import com.facebook.FacebookTestCase;
import com.facebook.WaitForBroadcastReceiver;
import com.facebook.appevents.AppEventsLogger;

import java.io.FileInputStream;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.util.HashMap;
import java.util.List;

public class AppEventsLoggerTests extends FacebookTestCase {
    public void testSimpleCall() throws InterruptedException {
        AppEventsLogger.setFlushBehavior(AppEventsLogger.FlushBehavior.EXPLICIT_ONLY);

        AccessToken accessToken1 = getAccessTokenForSharedUser();
        AccessToken accessToken2 = getAccessTokenForSharedUser(SECOND_TEST_USER_TAG);

        AppEventsLogger logger1 = AppEventsLogger.newLogger(getActivity(), accessToken1);
        AppEventsLogger logger2 = AppEventsLogger.newLogger(getActivity(), accessToken2);

        final WaitForBroadcastReceiver waitForBroadcastReceiver = new WaitForBroadcastReceiver();
        waitForBroadcastReceiver.incrementExpectCount();

        final LocalBroadcastManager broadcastManager = LocalBroadcastManager.getInstance(getActivity());

        try {
            // Need to get notifications on another thread so we can wait for them.
            runOnBlockerThread(new Runnable() {
                @Override
                public void run() {
                    broadcastManager.registerReceiver(waitForBroadcastReceiver,
                            new IntentFilter(AppEventsLogger.ACTION_APP_EVENTS_FLUSHED));
                }
            }, true);

            logger1.logEvent("an_event");
            logger2.logEvent("another_event");

            // test illegal event name and event key, should not crash in non-debug environment.
            logger1.logEvent("$illegal_event_name");
            Bundle params = new Bundle();
            params.putString("illegal%key", "good_value");
            logger1.logEvent("legal_event_name", params);
            char[] val = {'b', 'a', 'd'};
            params.putCharArray("legal_key", val);
            logger1.logEvent("legal_event",params);

            logger1.flush();

            waitForBroadcastReceiver.waitForExpectedCalls();

            closeBlockerAndAssertSuccess();
        } finally {
            broadcastManager.unregisterReceiver(waitForBroadcastReceiver);
        }
    }

    public void testPersistedEvents() throws IOException, ClassNotFoundException {
        AppEventsLogger.setFlushBehavior(AppEventsLogger.FlushBehavior.EXPLICIT_ONLY);

        final WaitForBroadcastReceiver waitForBroadcastReceiver = new WaitForBroadcastReceiver();
        final LocalBroadcastManager broadcastManager =
                LocalBroadcastManager.getInstance(getActivity());

        try {
            broadcastManager.registerReceiver(waitForBroadcastReceiver,
                    new IntentFilter(AppEventsLogger.ACTION_APP_EVENTS_FLUSHED));

            getActivity().getFileStreamPath(
                    AppEventsLogger.PersistedEvents.PERSISTED_EVENTS_FILENAME).delete();

            AccessToken accessToken = getAccessTokenForSharedUser();
            AppEventsLogger logger1 = AppEventsLogger.newLogger(getActivity(), accessToken);

            logger1.logEvent("an_event");

            AppEventsLogger.onContextStop();

            FileInputStream fis = getActivity().openFileInput(
                    AppEventsLogger.PersistedEvents.PERSISTED_EVENTS_FILENAME);
            assertNotNull(fis);

            ObjectInputStream ois = new ObjectInputStream(fis);
            Object obj = ois.readObject();
            ois.close();

            assertTrue(obj instanceof HashMap);

            logger1.logEvent("another_event");

            waitForBroadcastReceiver.incrementExpectCount();

            // Events are added async if we flush right away the event might not have made it to the
            // queue to be flushed. As a workaround give the other thread time to add it.
            try {
                Thread.sleep(100l);
            } catch (Exception ex) {
                // Ignore
            }
            logger1.flush();

            waitForBroadcastReceiver.waitForExpectedCalls();
            List<Intent> receivedIntents = waitForBroadcastReceiver.getReceivedIntents();
            assertEquals(1, receivedIntents.size());

            Intent intent = receivedIntents.get(0);
            assertNotNull(intent);

            assertEquals(2, intent.getIntExtra(
                    AppEventsLogger.APP_EVENTS_EXTRA_NUM_EVENTS_FLUSHED, 0));
        } finally {
            broadcastManager.unregisterReceiver(waitForBroadcastReceiver);
        }
    }
}
