Refactoring Types: ['Extract Method', 'Move Attribute']
pplicationTest.java
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

import android.app.Activity;

import com.facebook.junittests.MainActivity;

import org.junit.Test;
import org.robolectric.Robolectric;

import static org.junit.Assert.*;

public class ApplicationTest extends FacebookTestCase {
    @Test
    public void testCreateActivity() throws Exception {
        Activity activity = Robolectric.buildActivity(MainActivity.class).create().get();
        assertTrue(activity != null);
    }
}


File: facebook/junitTests/src/test/java/com/facebook/GraphRequestTest.java
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

import android.graphics.Bitmap;
import android.location.Location;
import android.net.Uri;
import android.os.Bundle;

import com.facebook.internal.GraphUtil;
import com.facebook.internal.ServerProtocol;
import com.facebook.share.internal.ShareInternalUtility;

import org.json.JSONException;
import org.json.JSONObject;
import org.junit.Before;
import org.junit.Test;
import org.powermock.core.classloader.annotations.PrepareForTest;

import java.net.HttpURLConnection;

import static org.junit.Assert.*;
import static org.powermock.api.mockito.PowerMockito.mockStatic;
import static org.powermock.api.mockito.PowerMockito.when;

@PrepareForTest( { FacebookSdk.class, AccessTokenManager.class })
public class GraphRequestTest extends FacebookPowerMockTestCase {

    @Before
    public void before() {
        mockStatic(FacebookSdk.class);
        when(FacebookSdk.isInitialized()).thenReturn(true);
        when(FacebookSdk.getApplicationId()).thenReturn("1234");
        when(FacebookSdk.getClientToken()).thenReturn("5678");
    }

    @Test
    public void testCreateRequest() {
        GraphRequest request = new GraphRequest();
        assertTrue(request != null);
        assertEquals(HttpMethod.GET, request.getHttpMethod());
    }

    @Test
    public void testCreatePostRequest() {
        JSONObject graphObject = new JSONObject();
        GraphRequest request = GraphRequest.newPostRequest(null, "me/statuses", graphObject, null);
        assertTrue(request != null);
        assertEquals(HttpMethod.POST, request.getHttpMethod());
        assertEquals("me/statuses", request.getGraphPath());
        assertEquals(graphObject, request.getGraphObject());
    }

    @Test
    public void testCreateMeRequest() {
        GraphRequest request = GraphRequest.newMeRequest(null, null);
        assertTrue(request != null);
        assertEquals(HttpMethod.GET, request.getHttpMethod());
        assertEquals("me", request.getGraphPath());
    }

    @Test
    public void testCreateMyFriendsRequest() {
        GraphRequest request = GraphRequest.newMyFriendsRequest(null, null);
        assertTrue(request != null);
        assertEquals(HttpMethod.GET, request.getHttpMethod());
        assertEquals("me/friends", request.getGraphPath());
    }

    @Test
    public void testCreateUploadPhotoRequest() {
        Bitmap image = Bitmap.createBitmap(128, 128, Bitmap.Config.ALPHA_8);

        GraphRequest request =
                ShareInternalUtility.newUploadPhotoRequest(
                        ShareInternalUtility.MY_PHOTOS,
                        null,
                        image,
                        null,
                        null,
                        null);
        assertTrue(request != null);

        Bundle parameters = request.getParameters();
        assertTrue(parameters != null);

        assertTrue(parameters.containsKey("picture"));
        assertEquals(image, parameters.getParcelable("picture"));
        assertEquals("me/photos", request.getGraphPath());
    }

    @Test
    public void testCreatePlacesSearchRequestWithLocation() {
        Location location = new Location("");
        location.setLatitude(47.6204);
        location.setLongitude(-122.3491);

        GraphRequest request = GraphRequest.newPlacesSearchRequest(null, location, 1000, 50, null, null);

        assertTrue(request != null);
        assertEquals(HttpMethod.GET, request.getHttpMethod());
        assertEquals("search", request.getGraphPath());
    }

    @Test
    public void testCreatePlacesSearchRequestWithSearchText() {
        GraphRequest request = GraphRequest.newPlacesSearchRequest(null, null, 1000, 50, "Starbucks", null);

        assertTrue(request != null);
        assertEquals(HttpMethod.GET, request.getHttpMethod());
        assertEquals("search", request.getGraphPath());
    }

    @Test
    public void testCreatePlacesSearchRequestRequiresLocationOrSearchText() {
        try {
            GraphRequest.newPlacesSearchRequest(null, null, 1000, 50, null, null);
            fail("expected exception");
        } catch (FacebookException exception) {
            // Success
        }
    }

    @Test
    public void testNewPostOpenGraphObjectRequestRequiresObject() {
        try {
            ShareInternalUtility.newPostOpenGraphObjectRequest(null, null, null);
            fail("expected exception");
        } catch (FacebookException exception) {
            // Success
        }
    }

    @Test
    public void testNewPostOpenGraphObjectRequestRequiresObjectType() {
        try {
            JSONObject object = GraphUtil.createOpenGraphObjectForPost(null);
            ShareInternalUtility.newPostOpenGraphObjectRequest(null, object, null);
            fail("expected exception");
        } catch (FacebookException exception) {
            // Success
        }
    }

    @Test
    public void testNewPostOpenGraphObjectRequestRequiresNonEmptyObjectType() throws JSONException {
        try {
            JSONObject object = GraphUtil.createOpenGraphObjectForPost("");
            object.put("title", "bar");
            ShareInternalUtility.newPostOpenGraphObjectRequest(null, object, null);
            fail("expected exception");
        } catch (FacebookException exception) {
            // Success
        }
    }

    @Test
    public void testNewPostOpenGraphObjectRequestRequiresTitle() {
        try {
            JSONObject object = GraphUtil.createOpenGraphObjectForPost("foo");
            ShareInternalUtility.newPostOpenGraphObjectRequest(null, object, null);
            fail("expected exception");
        } catch (FacebookException exception) {
            // Success
        }
    }

    @Test
    public void testNewPostOpenGraphObjectRequestRequiresNonEmptyTitle() throws JSONException {
        try {
            JSONObject object = GraphUtil.createOpenGraphObjectForPost("foo");
            object.put("title", "");
            ShareInternalUtility.newPostOpenGraphObjectRequest(null, object, null);
            fail("expected exception");
        } catch (FacebookException exception) {
            // Success
        }
    }

    @Test
    public void testNewPostOpenGraphObjectRequest() throws JSONException {
        JSONObject object = GraphUtil.createOpenGraphObjectForPost("foo");
        object.put("title", "bar");
        GraphRequest request = ShareInternalUtility.newPostOpenGraphObjectRequest(
                null,
                object,
                null);
        assertNotNull(request);
    }

    @Test
    public void testNewPostOpenGraphActionRequestRequiresAction() {
        try {
            ShareInternalUtility.newPostOpenGraphActionRequest(null, null, null);
            fail("expected exception");
        } catch (FacebookException exception) {
            // Success
        }
    }

    @Test
    public void testNewPostOpenGraphActionRequestRequiresActionType() {
        try {
            JSONObject action = GraphUtil.createOpenGraphActionForPost(null);
            ShareInternalUtility.newPostOpenGraphActionRequest(null, action, null);
            fail("expected exception");
        } catch (FacebookException exception) {
            // Success
        }
    }

    @Test
    public void testNewPostOpenGraphActionRequestRequiresNonEmptyActionType() {
        try {
            JSONObject action = GraphUtil.createOpenGraphActionForPost("");
            ShareInternalUtility.newPostOpenGraphActionRequest(null, action, null);
            fail("expected exception");
        } catch (FacebookException exception) {
            // Success
        }
    }

    @Test
    public void testNewPostOpenGraphActionRequest() {
        JSONObject action = GraphUtil.createOpenGraphActionForPost("foo");
        GraphRequest request = ShareInternalUtility.newPostOpenGraphActionRequest(
                null,
                action,
                null);
        assertNotNull(request);
    }

    @Test
    public void testSetHttpMethodToNilGivesDefault() {
        GraphRequest request = new GraphRequest();
        assertEquals(HttpMethod.GET, request.getHttpMethod());

        request.setHttpMethod(null);
        assertEquals(HttpMethod.GET, request.getHttpMethod());
    }

    @Test
    public void testExecuteBatchWithNullRequestsThrows() {
        try {
            GraphRequest.executeBatchAndWait((GraphRequest[]) null);
            fail("expected NullPointerException");
        } catch (NullPointerException exception) {
        }
    }

    @Test
    public void testExecuteBatchWithZeroRequestsThrows() {
        try {
            GraphRequest.executeBatchAndWait(new GraphRequest[]{});
            fail("expected IllegalArgumentException");
        } catch (IllegalArgumentException exception) {
        }
    }

    @Test
    public void testExecuteBatchWithNullRequestThrows() {
        try {
            GraphRequest.executeBatchAndWait(new GraphRequest[]{null});
            fail("expected NullPointerException");
        } catch (NullPointerException exception) {
        }
    }

    @Test
    public void testToHttpConnectionWithNullRequestsThrows() {
        try {
            GraphRequest.toHttpConnection((GraphRequest[]) null);
            fail("expected NullPointerException");
        } catch (NullPointerException exception) {
        }
    }

    @Test
    public void testToHttpConnectionWithZeroRequestsThrows() {
        try {
            GraphRequest.toHttpConnection(new GraphRequest[]{});
            fail("expected IllegalArgumentException");
        } catch (IllegalArgumentException exception) {
        }
    }

    @Test
    public void testToHttpConnectionWithNullRequestThrows() {
        try {
            GraphRequest.toHttpConnection(new GraphRequest[]{null});
            fail("expected NullPointerException");
        } catch (NullPointerException exception) {
        }
    }

    @Test
    public void testSingleGetToHttpRequest() throws Exception {
        GraphRequest requestMe = new GraphRequest(null, "TourEiffel");
        HttpURLConnection connection = GraphRequest.toHttpConnection(requestMe);

        assertTrue(connection != null);

        assertEquals("GET", connection.getRequestMethod());
        assertEquals("/" + ServerProtocol.getAPIVersion() + "/TourEiffel",
            connection.getURL().getPath());

        assertTrue(connection.getRequestProperty("User-Agent").startsWith("FBAndroidSDK"));

        Uri uri = Uri.parse(connection.getURL().toString());
        assertEquals("android", uri.getQueryParameter("sdk"));
        assertEquals("json", uri.getQueryParameter("format"));
    }

    @Test
    public void testBuildsClientTokenIfNeeded() throws Exception {
        GraphRequest requestMe = new GraphRequest(null, "TourEiffel");
        HttpURLConnection connection = GraphRequest.toHttpConnection(requestMe);

        assertTrue(connection != null);

        Uri uri = Uri.parse(connection.getURL().toString());
        String accessToken = uri.getQueryParameter("access_token");
        assertNotNull(accessToken);
        assertTrue(accessToken.contains(FacebookSdk.getApplicationId()));
        assertTrue(accessToken.contains(FacebookSdk.getClientToken()));
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
import org.robolectric.RuntimeEnvironment;

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
        FacebookSdk.sdkInitialize(RuntimeEnvironment.application);
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


File: facebook/junitTests/src/test/java/com/facebook/login/LoginHandlerTestCase.java
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
import android.support.v4.app.FragmentActivity;

import com.facebook.FacebookPowerMockTestCase;

import org.junit.Before;
import org.robolectric.Robolectric;

import java.util.Arrays;
import java.util.Date;
import java.util.HashSet;

import static org.junit.Assert.assertTrue;
import static org.powermock.api.mockito.PowerMockito.mock;
import static org.powermock.api.mockito.PowerMockito.when;

public abstract class LoginHandlerTestCase extends FacebookPowerMockTestCase {
    protected static final String ACCESS_TOKEN = "An access token";
    protected static final String USER_ID = "1000";
    protected static final long EXPIRES_IN_DELTA = 3600 * 24 * 60;
    protected static final HashSet<String> PERMISSIONS = new HashSet<String>(
            Arrays.asList("go outside", "come back in"));
    protected static final String ERROR_MESSAGE = "This is bad!";

    protected FragmentActivity activity;
    protected LoginClient mockLoginClient;

    @Before
    public void before() throws Exception {
        mockLoginClient = mock(LoginClient.class);
        activity = Robolectric.buildActivity(FragmentActivity.class).create().get();
        when(mockLoginClient.getActivity()).thenReturn(activity);
    }

    protected LoginClient.Request createRequest() {
        return createRequest(null);
    }

    protected LoginClient.Request createRequest(String previousAccessTokenString) {

        return new LoginClient.Request(
                LoginBehavior.SSO_WITH_FALLBACK,
                new HashSet<String>(PERMISSIONS),
                DefaultAudience.FRIENDS,
                "1234",
                "5678");
    }

    protected void assertDateDiffersWithinDelta(Date expected, Date actual, long expectedDifference,
                                                long deltaInMsec) {

        long delta = Math.abs(expected.getTime() - actual.getTime()) - expectedDifference;
        assertTrue(delta < deltaInMsec);
    }
}


File: facebook/junitTests/src/test/java/com/facebook/login/LoginManagerTest.java
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
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.support.v4.app.Fragment;
import android.support.v4.app.FragmentActivity;

import com.facebook.AccessToken;
import com.facebook.AccessTokenSource;
import com.facebook.FacebookActivity;
import com.facebook.FacebookCallback;
import com.facebook.FacebookException;
import com.facebook.FacebookPowerMockTestCase;
import com.facebook.FacebookSdk;
import com.facebook.FacebookSdkNotInitializedException;
import com.facebook.Profile;

import org.apache.maven.profiles.ProfileManager;
import org.junit.Before;
import org.junit.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.powermock.core.classloader.annotations.PrepareForTest;

import java.util.Arrays;
import java.util.Collection;
import java.util.Date;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ThreadPoolExecutor;

import static org.junit.Assert.*;
import static org.mockito.Matchers.any;
import static org.mockito.Matchers.anyInt;
import static org.mockito.Matchers.eq;
import static org.mockito.Matchers.isA;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.powermock.api.mockito.PowerMockito.*;

@PrepareForTest({ FacebookSdk.class, AccessToken.class, Profile.class})
public class LoginManagerTest extends FacebookPowerMockTestCase {

    private static final String MOCK_APP_ID = "1234";
    private static final String USER_ID = "1000";
    private final String TOKEN_STRING = "A token of my esteem";
    private final List<String> PERMISSIONS = Arrays.asList("walk", "chew gum");
    private final Date EXPIRES = new Date(2025, 5, 3);
    private final Date LAST_REFRESH = new Date(2023, 8, 15);

    @Mock private Activity mockActivity;
    @Mock private Fragment mockFragment;
    @Mock private Context mockApplicationContext;
    @Mock private PackageManager mockPackageManager;
    @Mock private FacebookCallback<LoginResult> mockCallback;
    @Mock private ThreadPoolExecutor threadExecutor;
    @Mock private FragmentActivity mockFragmentActivity;

    @Before
    public void before() throws Exception {
        mockStatic(FacebookSdk.class);
        stub(method(AccessToken.class, "getCurrentAccessToken")).toReturn(null);
        stub(method(AccessToken.class, "setCurrentAccessToken")).toReturn(null);
        stub(method(Profile.class, "fetchProfileForCurrentAccessToken")).toReturn(null);

        when(FacebookSdk.isInitialized()).thenReturn(true);
        when(FacebookSdk.getApplicationId()).thenReturn(MOCK_APP_ID);
        when(FacebookSdk.getApplicationContext()).thenReturn(mockApplicationContext);
        when(FacebookSdk.getExecutor()).thenReturn(threadExecutor);
        when(mockFragment.getActivity()).thenReturn(mockFragmentActivity);

        // We use mocks rather than RobolectricPackageManager because it's simpler to not
        // have to specify Intents. Default to resolving all intents to something.
        ResolveInfo resolveInfo = new ResolveInfo();
        when(mockApplicationContext.getPackageManager()).thenReturn(mockPackageManager);
        when(mockPackageManager.resolveActivity(any(Intent.class), anyInt()))
                .thenReturn(resolveInfo);
    }

    @Test
    public void testRequiresSdkToBeInitialized() {
        try {
            when(FacebookSdk.isInitialized()).thenReturn(false);

            LoginManager loginManager = new LoginManager();

            fail();
        } catch (FacebookSdkNotInitializedException exception) {
        }
    }

    @Test
    public void testGetInstance() {
        LoginManager loginManager = LoginManager.getInstance();
        assertNotNull(loginManager);
    }

    @Test
    public void testLoginBehaviorDefaultsToSsoWithFallback() {
        LoginManager loginManager = new LoginManager();
        assertEquals(LoginBehavior.SSO_WITH_FALLBACK, loginManager.getLoginBehavior());
    }

    @Test
    public void testCanChangeLoginBehavior() {
        LoginManager loginManager = new LoginManager();
        loginManager.setLoginBehavior(LoginBehavior.SSO_ONLY);
        assertEquals(LoginBehavior.SSO_ONLY, loginManager.getLoginBehavior());
    }

    @Test
    public void testDefaultAudienceDefaultsToFriends() {
        LoginManager loginManager = new LoginManager();
        assertEquals(DefaultAudience.FRIENDS, loginManager.getDefaultAudience());
    }

    @Test
    public void testCanChangeDefaultAudience() {
        LoginManager loginManager = new LoginManager();
        loginManager.setDefaultAudience(DefaultAudience.EVERYONE);
        assertEquals(DefaultAudience.EVERYONE, loginManager.getDefaultAudience());
    }

    @Test
    public void testLogInWithReadAndActivityThrowsIfPublishPermissionGiven() {
        LoginManager loginManager = new LoginManager();
        try {
            loginManager.logInWithReadPermissions(mockActivity,
                Arrays.asList("public_profile", "publish_actions"));
            fail();
        } catch(FacebookException exception) {
        }
    }

    @Test
    public void testLogInWithPublishAndActivityThrowsIfPublishPermissionGiven() {
        LoginManager loginManager = new LoginManager();
        try {
            loginManager.logInWithPublishPermissions(mockActivity,
                Arrays.asList("public_profile", "publish_actions"));
            fail();
        } catch(FacebookException exception) {
        }
    }

    @Test
    public void testLogInThrowsIfCannotResolveFacebookActivity() {
        when(mockPackageManager.resolveActivity(any(Intent.class), anyInt())).thenReturn(null);

        LoginManager loginManager = new LoginManager();

        try {
            loginManager.logInWithReadPermissions(mockActivity,
                Arrays.asList("public_profile", "user_friends"));
            fail();
        } catch(FacebookException exception) {
        }
    }

    @Test
    public void testLogInThrowsIfCannotStartFacebookActivity() {
        doThrow(new ActivityNotFoundException()).when(mockActivity)
            .startActivityForResult(any(Intent.class), anyInt());

        LoginManager loginManager = new LoginManager();

        try {
            loginManager.logInWithReadPermissions(mockActivity,
                Arrays.asList("public_profile", "user_friends"));
            fail();
        } catch(FacebookException exception) {
        }
    }

    @Test
    public void testRequiresNonNullActivity() {
        try {
            LoginManager loginManager = new LoginManager();
            loginManager.logInWithReadPermissions((Activity) null,
                Arrays.asList("public_profile", "user_friends"));
            fail();
        } catch (NullPointerException exception) {
        }
    }

    @Test
    public void testRequiresNonNullFragment() {
        try {
            LoginManager loginManager = new LoginManager();
            loginManager.logInWithReadPermissions((Fragment) null,
                    Arrays.asList("public_profile", "user_friends"));
            fail();
        } catch (NullPointerException exception) {
        }
    }

    @Test
    public void testLogInWithReadDoesNotThrowWithReadPermissions() {
        LoginManager loginManager = new LoginManager();
        loginManager.logInWithReadPermissions(mockActivity,
            Arrays.asList("public_profile", "user_friends"));
    }

    @Test
    public void testLogInWithReadListCreatesPendingRequestWithCorrectValues() {
        LoginManager loginManager = new LoginManager();
        // Change some defaults so we can verify the pending request picks them up.
        loginManager.setLoginBehavior(LoginBehavior.SSO_ONLY);
        loginManager.setDefaultAudience(DefaultAudience.EVERYONE);
        loginManager.logInWithReadPermissions(mockActivity,
            Arrays.asList("public_profile", "user_friends"));

        implTestLogInCreatesPendingRequestWithCorrectValues(loginManager,
                Arrays.asList("public_profile", "user_friends"));
    }

    @Test
    public void testLogInWithReadAndAccessTokenCreatesReauthRequest() {
        AccessToken accessToken = createAccessToken();
        stub(method(AccessToken.class, "getCurrentAccessToken")).toReturn(accessToken);

        LoginManager loginManager = new LoginManager();
        loginManager.logInWithReadPermissions(mockActivity,
            Arrays.asList("public_profile", "user_friends"));

        LoginClient.Request request = loginManager.getPendingLoginRequest();
        assertNotNull(loginManager.getPendingLoginRequest());
    }

    public void implTestLogInCreatesPendingRequestWithCorrectValues(
            LoginManager loginManager,
            Collection<String> expectedPermissions) {

        LoginClient.Request request = loginManager.getPendingLoginRequest();

        assertNotNull(request);

        assertEquals(MOCK_APP_ID, request.getApplicationId());
        assertEquals(LoginBehavior.SSO_ONLY, request.getLoginBehavior());
        assertEquals(DefaultAudience.EVERYONE, request.getDefaultAudience());

        Set<String> permissions = request.getPermissions();
        for (String permission : expectedPermissions) {
            assertTrue(permissions.contains(permission));

        }
    }

    @Test
    public void testLogInWithReadAndActivityStartsFacebookActivityWithCorrectRequest() {

        LoginManager loginManager = new LoginManager();
        loginManager.logInWithReadPermissions(mockActivity,
            Arrays.asList("public_profile", "user_friends"));

        ArgumentCaptor<Intent> intentArgumentCaptor = ArgumentCaptor.forClass(Intent.class);
        verify(mockActivity).startActivityForResult(intentArgumentCaptor.capture(), anyInt());
        Intent intent = intentArgumentCaptor.getValue();

        ComponentName componentName = intent.getComponent();
        assertEquals(FacebookActivity.class.getName(), componentName.getClassName());
        assertEquals(LoginBehavior.SSO_WITH_FALLBACK.name(), intent.getAction());
    }

    @Test
    public void testLogInWithReadAndFragmentStartsFacebookActivityWithCorrectRequest() {

        LoginManager loginManager = new LoginManager();
        loginManager.logInWithReadPermissions(mockFragment,
                Arrays.asList("public_profile", "user_friends"));

        ArgumentCaptor<Intent> intentArgumentCaptor = ArgumentCaptor.forClass(Intent.class);
        verify(mockFragment).startActivityForResult(intentArgumentCaptor.capture(), anyInt());
        Intent intent = intentArgumentCaptor.getValue();

        ComponentName componentName = intent.getComponent();
        assertEquals(FacebookActivity.class.getName(), componentName.getClassName());
        assertEquals(LoginBehavior.SSO_WITH_FALLBACK.name(), intent.getAction());
    }

    @Test
    public void testLogInWitPublishDoesNotThrowWithPublishPermissions() {
        LoginManager loginManager = new LoginManager();
        loginManager.logInWithPublishPermissions(mockActivity,
            Arrays.asList("publish_actions", "publish_stream"));
    }

    @Test
    public void testLogInWithPublishListCreatesPendingRequestWithCorrectValues() {
        LoginManager loginManager = new LoginManager();
        // Change some defaults so we can verify the pending request picks them up.
        loginManager.setLoginBehavior(LoginBehavior.SSO_ONLY);
        loginManager.setDefaultAudience(DefaultAudience.EVERYONE);
        loginManager.logInWithPublishPermissions(mockActivity,
            Arrays.asList("publish_actions", "publish_stream"));

        implTestLogInCreatesPendingRequestWithCorrectValues(loginManager,
            Arrays.asList("publish_actions", "publish_stream"));
    }

    @Test
    public void testLogInWithPublishAndAccessTokenCreatesReauthRequest() {
        AccessToken accessToken = createAccessToken();
        stub(method(AccessToken.class, "getCurrentAccessToken")).toReturn(accessToken);

        LoginManager loginManager = new LoginManager();
        loginManager.logInWithPublishPermissions(mockActivity,
            Arrays.asList("publish_actions", "publish_stream"));

        assertNotNull(loginManager.getPendingLoginRequest());
    }

    @Test
    public void testOnActivityResultReturnsFalseIfNoPendingRequest() {
        LoginManager loginManager = new LoginManager();

        Intent intent = createSuccessResultIntent();

        boolean result = loginManager.onActivityResult(0, intent);

        assertFalse(result);
    }

    @Test
    public void testOnActivityResultReturnsTrueAndCallsCallbackOnCancelResultCode() {
        LoginManager loginManager = new LoginManager();
        loginManager.logInWithReadPermissions(mockActivity,
            Arrays.asList("public_profile", "user_friends"));

        boolean result = loginManager.onActivityResult(
                Activity.RESULT_CANCELED, null, mockCallback);

        assertTrue(result);
        verify(mockCallback, times(1)).onCancel();
        verify(mockCallback, never()).onSuccess(isA(LoginResult.class));
    }

    @Test
    public void testOnActivityResultReturnsTrueAndCallsCallbackOnCancelResultCodeEvenWithData() {
        LoginManager loginManager = new LoginManager();
        loginManager.logInWithReadPermissions(mockActivity,
            Arrays.asList("public_profile", "user_friends"));

        Intent intent = createSuccessResultIntent();
        boolean result = loginManager.onActivityResult(
                Activity.RESULT_CANCELED, intent, mockCallback);

        assertTrue(result);
        verify(mockCallback, times(1)).onCancel();
        verify(mockCallback, never()).onSuccess(isA(LoginResult.class));
    }

    @Test
    public void testOnActivityResultDoesNotModifyCurrentAccessTokenOnCancelResultCode() {
        LoginManager loginManager = new LoginManager();
        loginManager.logInWithReadPermissions(mockActivity,
                Arrays.asList("public_profile", "user_friends"));

        loginManager.onActivityResult(Activity.RESULT_CANCELED, null, mockCallback);

        verifyStatic(never());
        AccessToken.setCurrentAccessToken(any(AccessToken.class));
    }

    @Test
    public void testOnActivityResultHandlesMissingCallbackOnCancelResultCode() {
        LoginManager loginManager = new LoginManager();
        loginManager.logInWithReadPermissions(mockActivity,
            Arrays.asList("public_profile", "user_friends"));

        boolean result = loginManager.onActivityResult(
                Activity.RESULT_CANCELED,
                null);

        assertTrue(result);
    }

    @Test
    public void testOnActivityResultReturnsTrueAndCallsCallbackOnNullData() {
        LoginManager loginManager = new LoginManager();
        loginManager.logInWithReadPermissions(mockActivity,
            Arrays.asList("public_profile", "user_friends"));

        boolean result = loginManager.onActivityResult(
                Activity.RESULT_OK, null, mockCallback);

        assertTrue(result);
        verify(mockCallback, times(1)).onError(isA(FacebookException.class));
        verify(mockCallback, never()).onSuccess(isA(LoginResult.class));
    }

    @Test
    public void testOnActivityResultReturnsTrueAndCallsCallbackOnMissingResult() {
        LoginManager loginManager = new LoginManager();
        loginManager.logInWithReadPermissions(mockActivity,
            Arrays.asList("public_profile", "user_friends"));

        Intent intent = createSuccessResultIntent();
        intent.removeExtra(LoginFragment.RESULT_KEY);
        boolean result = loginManager.onActivityResult(
                Activity.RESULT_OK, intent, mockCallback);

        assertTrue(result);
        verify(mockCallback, times(1)).onError(isA(FacebookException.class));
        verify(mockCallback, never()).onSuccess(isA(LoginResult.class));
    }

    @Test
    public void testOnActivityResultReturnsTrueAndCallsCallbackOnErrorResult() {
        LoginManager loginManager = new LoginManager();
        loginManager.logInWithReadPermissions(mockActivity,
            Arrays.asList("public_profile", "user_friends"));

        boolean result = loginManager.onActivityResult(
                Activity.RESULT_OK, createErrorResultIntent(), mockCallback);

        ArgumentCaptor<FacebookException> exceptionArgumentCaptor =
                ArgumentCaptor.forClass(FacebookException.class);

        assertTrue(result);
        verify(mockCallback, times(1)).onError(exceptionArgumentCaptor.capture());
        verify(mockCallback, never()).onSuccess(isA(LoginResult.class));
        assertEquals("foo: bar", exceptionArgumentCaptor.getValue().getMessage());
    }

    @Test
    public void testOnActivityResultReturnsTrueAndCallsCallbackOnCancelResult() {
        LoginManager loginManager = new LoginManager();
        loginManager.logInWithReadPermissions(mockActivity,
            Arrays.asList("public_profile", "user_friends"));

        boolean result = loginManager.onActivityResult(
                Activity.RESULT_CANCELED, createCancelResultIntent(), mockCallback);

        assertTrue(result);
        verify(mockCallback, times(1)).onCancel();
        verify(mockCallback, never()).onSuccess(isA(LoginResult.class));
    }

    @Test
    public void testOnActivityResultDoesNotModifyCurrentAccessTokenOnErrorResultCode() {
        LoginManager loginManager = new LoginManager();
        loginManager.logInWithReadPermissions(mockActivity,
            Arrays.asList("public_profile", "user_friends"));

        loginManager.onActivityResult(
                Activity.RESULT_CANCELED,
                createErrorResultIntent(),
                mockCallback);

        verifyStatic(never());
        AccessToken.setCurrentAccessToken(any(AccessToken.class));
    }

    @Test
    public void testOnActivityResultReturnsTrueAndCallsCallbackOnSuccessResult() {
        LoginManager loginManager = new LoginManager();
        loginManager.logInWithReadPermissions(mockActivity,
            Arrays.asList("public_profile", "user_friends"));

        boolean result = loginManager.onActivityResult(
                Activity.RESULT_OK, createSuccessResultIntent(), mockCallback);

        assertTrue(result);
        verify(mockCallback, never()).onError(any(FacebookException.class));
        verify(mockCallback, times(1)).onSuccess(isA(LoginResult.class));
    }

    @Test
    public void testOnHandlesMissingCallbackkOnSuccessResult() {
        LoginManager loginManager = new LoginManager();
        loginManager.logInWithReadPermissions(mockActivity,
            Arrays.asList("public_profile", "user_friends"));

        boolean result = loginManager.onActivityResult(
                Activity.RESULT_OK, createSuccessResultIntent(), null);

        assertTrue(result);
    }

    @Test
    public void testOnActivityResultSetsCurrentAccessTokenOnSuccessResult() {
        LoginManager loginManager = new LoginManager();
        loginManager.logInWithReadPermissions(mockActivity,
            Arrays.asList("public_profile", "user_friends"));

        boolean result = loginManager.onActivityResult(
                Activity.RESULT_OK, createSuccessResultIntent(), mockCallback);

        verifyStatic(times(1));
        AccessToken.setCurrentAccessToken(eq(createAccessToken()));
    }

    private Intent createSuccessResultIntent() {
        Intent intent = new Intent();

        LoginClient.Request request = mock(LoginClient.Request.class);

        AccessToken accessToken = createAccessToken();
        LoginClient.Result result = LoginClient.Result.createTokenResult(request, accessToken);
        intent.putExtra(LoginFragment.RESULT_KEY, result);

        return intent;
    }

    private Intent createErrorResultIntent() {
        Intent intent = new Intent();

        LoginClient.Request request = mock(LoginClient.Request.class);

        LoginClient.Result result = LoginClient.Result.createErrorResult(request, "foo", "bar");
        intent.putExtra(LoginFragment.RESULT_KEY, result);

        return intent;
    }

    private Intent createCancelResultIntent() {
        Intent intent = new Intent();

        LoginClient.Request request = mock(LoginClient.Request.class);

        LoginClient.Result result = LoginClient.Result.createCancelResult(request, null);
        intent.putExtra(LoginFragment.RESULT_KEY, result);

        return intent;
    }

    private AccessToken createAccessToken() {
        return new AccessToken(
                TOKEN_STRING,
                MOCK_APP_ID,
                USER_ID,
                PERMISSIONS,
                null,
                AccessTokenSource.WEB_VIEW,
                EXPIRES,
                LAST_REFRESH);
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
import org.robolectric.RuntimeEnvironment;

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
        FacebookSdk.sdkInitialize(RuntimeEnvironment.application);
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
    public static final String BUILD = "4.3.0";
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

            // For the unity sdk we need to append the unity user agent
            String customUserAgent = InternalSettings.getCustomUserAgent();
            if (!Utility.isNullOrEmpty(customUserAgent)) {
                userAgent = String.format(
                        Locale.ROOT,
                        "%s/%s",
                        userAgent,
                        customUserAgent);
            }
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

import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.database.Cursor;
import android.net.Uri;
import android.os.Binder;
import android.os.IBinder;
import android.os.IInterface;
import android.os.Looper;
import android.os.Parcel;
import android.os.RemoteException;
import android.util.Log;

import com.facebook.FacebookException;

import java.lang.reflect.Method;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingDeque;
import java.util.concurrent.atomic.AtomicBoolean;

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
        AttributionIdentifiers identifiers = getAndroidIdViaReflection(context);
        if (identifiers == null) {
            identifiers = getAndroidIdViaService(context);
            if (identifiers == null) {
                identifiers = new AttributionIdentifiers();
            }
        }
        return identifiers;
    }

    private static AttributionIdentifiers getAndroidIdViaReflection(Context context) {
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
                return null;
            }

            Object connectionResult = Utility.invokeMethodQuietly(
                    null, isGooglePlayServicesAvailable, context);
            if (!(connectionResult instanceof Integer)
                    || (Integer) connectionResult != CONNECTION_RESULT_SUCCESS) {
                return null;
            }

            Method getAdvertisingIdInfo = Utility.getMethodQuietly(
                    "com.google.android.gms.ads.identifier.AdvertisingIdClient",
                    "getAdvertisingIdInfo",
                    Context.class
            );
            if (getAdvertisingIdInfo == null) {
                return null;
            }
            Object advertisingInfo = Utility.invokeMethodQuietly(
                    null, getAdvertisingIdInfo, context);
            if (advertisingInfo == null) {
                return null;
            }

            Method getId = Utility.getMethodQuietly(advertisingInfo.getClass(), "getId");
            Method isLimitAdTrackingEnabled = Utility.getMethodQuietly(
                    advertisingInfo.getClass(),
                    "isLimitAdTrackingEnabled");
            if (getId == null || isLimitAdTrackingEnabled == null) {
                return null;
            }

            AttributionIdentifiers identifiers = new AttributionIdentifiers();
            identifiers.androidAdvertiserId =
                    (String) Utility.invokeMethodQuietly(advertisingInfo, getId);
            identifiers.limitTracking = (Boolean) Utility.invokeMethodQuietly(
                    advertisingInfo,
                    isLimitAdTrackingEnabled);
        } catch (Exception e) {
            Utility.logd("android_id", e);
        }
        return null;
    }

    private static AttributionIdentifiers getAndroidIdViaService(Context context) {
        GoogleAdServiceConnection connection = new GoogleAdServiceConnection();
        Intent intent = new Intent("com.google.android.gms.ads.identifier.service.START");
        intent.setPackage("com.google.android.gms");
        if(context.bindService(intent, connection, Context.BIND_AUTO_CREATE)) {
            try {
                GoogleAdInfo adInfo = new GoogleAdInfo(connection.getBinder());
                AttributionIdentifiers identifiers = new AttributionIdentifiers();
                identifiers.androidAdvertiserId = adInfo.getAdvertiserId();
                identifiers.limitTracking = adInfo.isTrackingLimited();
                return identifiers;
            } catch (Exception exception) {
                Utility.logd("android_id", exception);
            } finally {
                context.unbindService(connection);
            }
        }
        return null;
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

    private static final class GoogleAdServiceConnection implements ServiceConnection {
        private AtomicBoolean consumed = new AtomicBoolean(false);
        private final BlockingQueue<IBinder> queue = new LinkedBlockingDeque<>();

        @Override
        public void onServiceConnected(ComponentName name, IBinder service) {
            try {
                queue.put(service);
            } catch (InterruptedException e) {
            }
        }

        @Override
        public void onServiceDisconnected(ComponentName name) {
        }

        public IBinder getBinder() throws InterruptedException {
            if (consumed.compareAndSet(true, true)) {
                throw new IllegalStateException("Binder already consumed");
            }
            return queue.take();
        }
    }

    private static final class GoogleAdInfo implements IInterface {
        private static final int FIRST_TRANSACTION_CODE = Binder.FIRST_CALL_TRANSACTION;
        private static final int SECOND_TRANSACTION_CODE = FIRST_TRANSACTION_CODE + 1;

        private IBinder binder;

        GoogleAdInfo(IBinder binder) {
            this.binder = binder;
        }

        @Override
        public IBinder asBinder() {
            return binder;
        }

        public String getAdvertiserId() throws RemoteException {
            Parcel data = Parcel.obtain();
            Parcel reply = Parcel.obtain();
            String id;
            try {
                data.writeInterfaceToken(
                        "com.google.android.gms.ads.identifier.internal.IAdvertisingIdService");
                binder.transact(FIRST_TRANSACTION_CODE, data, reply, 0);
                reply.readException();
                id = reply.readString();
            } finally {
                reply.recycle();
                data.recycle();
            }
            return id;
        }

        public boolean isTrackingLimited() throws RemoteException {
            Parcel data = Parcel.obtain();
            Parcel reply = Parcel.obtain();
            boolean limitAdTracking;
            try {
                data.writeInterfaceToken(
                        "com.google.android.gms.ads.identifier.internal.IAdvertisingIdService");
                data.writeInt(1);
                binder.transact(SECOND_TRANSACTION_CODE, data, reply, 0);
                reply.readException();
                limitAdTracking = 0 != reply.readInt();
            } finally {
                reply.recycle();
                data.recycle();
            }
            return limitAdTracking;
        }
    }
}


File: facebook/src/com/facebook/internal/ServerProtocol.java
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
import android.os.Bundle;
import android.util.Log;

import com.facebook.FacebookSdk;
import com.facebook.LoggingBehavior;

import org.json.JSONException;
import org.json.JSONObject;

import java.util.Collection;

/**
 * com.facebook.internal is solely for the use of other packages within the Facebook SDK for
 * Android. Use of any of the classes in this package is unsupported, and they may be modified or
 * removed without warning at any time.
 */
public final class ServerProtocol {
    private static final String TAG = ServerProtocol.class.getName();

    private static final String DIALOG_AUTHORITY_FORMAT = "m.%s";
    public static final String DIALOG_PATH = "dialog/";
    public static final String DIALOG_PARAM_ACCESS_TOKEN = "access_token";
    public static final String DIALOG_PARAM_APP_ID = "app_id";
    public static final String DIALOG_PARAM_AUTH_TYPE = "auth_type";
    public static final String DIALOG_PARAM_CLIENT_ID = "client_id";
    public static final String DIALOG_PARAM_DISPLAY = "display";
    public static final String DIALOG_PARAM_DISPLAY_TOUCH = "touch";
    public static final String DIALOG_PARAM_E2E = "e2e";
    public static final String DIALOG_PARAM_LEGACY_OVERRIDE = "legacy_override";
    public static final String DIALOG_PARAM_REDIRECT_URI = "redirect_uri";
    public static final String DIALOG_PARAM_RESPONSE_TYPE = "response_type";
    public static final String DIALOG_PARAM_RETURN_SCOPES = "return_scopes";
    public static final String DIALOG_PARAM_SCOPE = "scope";
    public static final String DIALOG_PARAM_DEFAULT_AUDIENCE = "default_audience";
    public static final String DIALOG_REREQUEST_AUTH_TYPE = "rerequest";
    public static final String DIALOG_RESPONSE_TYPE_TOKEN_AND_SIGNED_REQUEST
            = "token,signed_request";
    public static final String DIALOG_RETURN_SCOPES_TRUE = "true";
    public static final String DIALOG_REDIRECT_URI = "fbconnect://success";
    public static final String DIALOG_CANCEL_URI = "fbconnect://cancel";

    public static final String FALLBACK_DIALOG_PARAM_APP_ID = "app_id";
    public static final String FALLBACK_DIALOG_PARAM_BRIDGE_ARGS = "bridge_args";
    public static final String FALLBACK_DIALOG_PARAM_KEY_HASH = "android_key_hash";
    public static final String FALLBACK_DIALOG_PARAM_METHOD_ARGS = "method_args";
    public static final String FALLBACK_DIALOG_PARAM_METHOD_RESULTS = "method_results";
    public static final String FALLBACK_DIALOG_PARAM_VERSION = "version";
    public static final String FALLBACK_DIALOG_DISPLAY_VALUE_TOUCH = "touch";

    // URL components
    private static final String GRAPH_VIDEO_URL_FORMAT = "https://graph-video.%s";
    private static final String GRAPH_URL_FORMAT = "https://graph.%s";
    public static final String GRAPH_API_VERSION = "v2.3";

    public static final Collection<String> errorsProxyAuthDisabled =
            Utility.unmodifiableCollection("service_disabled", "AndroidAuthKillSwitchException");
    public static final Collection<String> errorsUserCanceled =
            Utility.unmodifiableCollection("access_denied", "OAuthAccessDeniedException");

    public static final String getDialogAuthority() {
        return String.format(DIALOG_AUTHORITY_FORMAT, FacebookSdk.getFacebookDomain());
    }

    public static final String getGraphUrlBase() {
        return String.format(GRAPH_URL_FORMAT, FacebookSdk.getFacebookDomain());
    }

    public static final String getGraphVideoUrlBase() {
        return String.format(GRAPH_VIDEO_URL_FORMAT, FacebookSdk.getFacebookDomain());
    }

    public static final String getAPIVersion() {
        return GRAPH_API_VERSION;
    }

    public static Bundle getQueryParamsForPlatformActivityIntentWebFallback(
            String callId,
            int version,
            Bundle methodArgs) {

        Context context = FacebookSdk.getApplicationContext();
        String keyHash = FacebookSdk.getApplicationSignature(context);
        if (Utility.isNullOrEmpty(keyHash)) {
            return null;
        }

        Bundle webParams = new Bundle();

        webParams.putString(FALLBACK_DIALOG_PARAM_KEY_HASH, keyHash);
        webParams.putString(FALLBACK_DIALOG_PARAM_APP_ID, FacebookSdk.getApplicationId());
        webParams.putInt(FALLBACK_DIALOG_PARAM_VERSION, version);
        webParams.putString(DIALOG_PARAM_DISPLAY, FALLBACK_DIALOG_DISPLAY_VALUE_TOUCH);

        Bundle bridgeArguments = new Bundle();
        bridgeArguments.putString(NativeProtocol.BRIDGE_ARG_ACTION_ID_STRING, callId);

        methodArgs = (methodArgs == null) ? new Bundle() : methodArgs;

        try {
            JSONObject bridgeArgsJSON = BundleJSONConverter.convertToJSON(bridgeArguments);
            JSONObject methodArgsJSON = BundleJSONConverter.convertToJSON(methodArgs);

            if (bridgeArgsJSON == null || methodArgsJSON == null) {
                return null;
            }

            webParams.putString(FALLBACK_DIALOG_PARAM_BRIDGE_ARGS, bridgeArgsJSON.toString());
            webParams.putString(FALLBACK_DIALOG_PARAM_METHOD_ARGS, methodArgsJSON.toString());
        } catch (JSONException je) {
            webParams = null;
            Logger.log(LoggingBehavior.DEVELOPER_ERRORS, Log.ERROR, TAG,
                    "Error creating Url -- " + je);
        }

        return webParams;
    }
}


File: facebook/src/com/facebook/internal/Utility.java
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
import android.content.SharedPreferences;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Parcel;
import android.os.StatFs;
import android.provider.OpenableColumns;
import android.telephony.TelephonyManager;
import android.text.TextUtils;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.Display;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.CookieSyncManager;

import com.facebook.AccessToken;
import com.facebook.FacebookException;
import com.facebook.FacebookSdk;
import com.facebook.GraphRequest;
import com.facebook.GraphResponse;
import com.facebook.HttpMethod;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.json.JSONTokener;

import java.io.*;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.HttpURLConnection;
import java.net.URLConnection;

import java.net.URLDecoder;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.regex.Pattern;

/**
 * com.facebook.internal is solely for the use of other packages within the Facebook SDK for
 * Android. Use of any of the classes in this package is unsupported, and they may be modified or
 * removed without warning at any time.
 */
public final class Utility {
    static final String LOG_TAG = "FacebookSDK";
    private static final String HASH_ALGORITHM_MD5 = "MD5";
    private static final String HASH_ALGORITHM_SHA1 = "SHA-1";
    private static final String URL_SCHEME = "https";
    private static final String APP_SETTINGS_PREFS_STORE =
            "com.facebook.internal.preferences.APP_SETTINGS";
    private static final String APP_SETTINGS_PREFS_KEY_FORMAT =
            "com.facebook.internal.APP_SETTINGS.%s";
    private static final String APP_SETTING_SUPPORTS_IMPLICIT_SDK_LOGGING =
            "supports_implicit_sdk_logging";
    private static final String APP_SETTING_NUX_CONTENT = "gdpv4_nux_content";
    private static final String APP_SETTING_NUX_ENABLED = "gdpv4_nux_enabled";
    private static final String APP_SETTING_DIALOG_CONFIGS = "android_dialog_configs";
    private static final String APP_SETTING_ANDROID_SDK_ERROR_CATEGORIES =
            "android_sdk_error_categories";
    private static final String EXTRA_APP_EVENTS_INFO_FORMAT_VERSION = "a2";
    private static final String DIALOG_CONFIG_DIALOG_NAME_FEATURE_NAME_SEPARATOR = "\\|";
    private static final String DIALOG_CONFIG_NAME_KEY = "name";
    private static final String DIALOG_CONFIG_VERSIONS_KEY = "versions";
    private static final String DIALOG_CONFIG_URL_KEY = "url";

    private final static String UTF8 = "UTF-8";

    private static final String[] APP_SETTING_FIELDS = new String[]{
            APP_SETTING_SUPPORTS_IMPLICIT_SDK_LOGGING,
            APP_SETTING_NUX_CONTENT,
            APP_SETTING_NUX_ENABLED,
            APP_SETTING_DIALOG_CONFIGS,
            APP_SETTING_ANDROID_SDK_ERROR_CATEGORIES
    };
    private static final String APPLICATION_FIELDS = "fields";

    // This is the default used by the buffer streams, but they trace a warning if you do not
    // specify.
    public static final int DEFAULT_STREAM_BUFFER_SIZE = 8192;

    // Refresh extended device info every 30 minutes
    private static final int REFRESH_TIME_FOR_EXTENDED_DEVICE_INFO_MILLIS = 30 * 60 * 1000;

    private static final String noCarrierConstant = "NoCarrier";

    private static final int GINGERBREAD_MR1 = 10;

    private static Map<String, FetchedAppSettings> fetchedAppSettings =
            new ConcurrentHashMap<String, FetchedAppSettings>();

    private static AtomicBoolean loadingSettings = new AtomicBoolean(false);

    private static int numCPUCores = 0;

    private static long timestampOfLastCheck = -1;
    private static long totalExternalStorageGB = -1;
    private static long availableExternalStorageGB = -1;
    private static String deviceTimezone = "";
    private static String carrierName = noCarrierConstant;

    public static class FetchedAppSettings {
        private boolean supportsImplicitLogging;
        private String nuxContent;
        private boolean nuxEnabled;
        private Map<String, Map<String, DialogFeatureConfig>> dialogConfigMap;
        private FacebookRequestErrorClassification errorClassification;

        private FetchedAppSettings(boolean supportsImplicitLogging,
                                   String nuxContent,
                                   boolean nuxEnabled,
                                   Map<String, Map<String, DialogFeatureConfig>> dialogConfigMap,
                                   FacebookRequestErrorClassification errorClassification) {
            this.supportsImplicitLogging = supportsImplicitLogging;
            this.nuxContent = nuxContent;
            this.nuxEnabled = nuxEnabled;
            this.dialogConfigMap = dialogConfigMap;
            this.errorClassification = errorClassification;
        }

        public boolean supportsImplicitLogging() {
            return supportsImplicitLogging;
        }

        public String getNuxContent() {
            return nuxContent;
        }

        public boolean getNuxEnabled() {
            return nuxEnabled;
        }

        public Map<String, Map<String, DialogFeatureConfig>> getDialogConfigurations() {
            return dialogConfigMap;
        }

        public FacebookRequestErrorClassification getErrorClassification() {
            return errorClassification;
        }
    }

    public static class DialogFeatureConfig {
        private static DialogFeatureConfig parseDialogConfig(JSONObject dialogConfigJSON) {
            String dialogNameWithFeature = dialogConfigJSON.optString(DIALOG_CONFIG_NAME_KEY);
            if (Utility.isNullOrEmpty(dialogNameWithFeature)) {
                return null;
            }

            String[] components = dialogNameWithFeature.split(
                    DIALOG_CONFIG_DIALOG_NAME_FEATURE_NAME_SEPARATOR);
            if (components.length != 2) {
                // We expect the format to be dialogName|FeatureName, where both components are
                // non-empty.
                return null;
            }

            String dialogName = components[0];
            String featureName = components[1];
            if (isNullOrEmpty(dialogName) || isNullOrEmpty(featureName)) {
                return null;
            }

            String urlString = dialogConfigJSON.optString(DIALOG_CONFIG_URL_KEY);
            Uri fallbackUri = null;
            if (!Utility.isNullOrEmpty(urlString)) {
                fallbackUri = Uri.parse(urlString);
            }

            JSONArray versionsJSON = dialogConfigJSON.optJSONArray(DIALOG_CONFIG_VERSIONS_KEY);

            int[] featureVersionSpec = parseVersionSpec(versionsJSON);

            return new DialogFeatureConfig(
                    dialogName, featureName, fallbackUri, featureVersionSpec);
        }

        private static int[] parseVersionSpec(JSONArray versionsJSON) {
            // Null signifies no overrides to the min-version as specified by the SDK.
            // An empty array would basically turn off the dialog (i.e no supported versions), so
            // DON'T default to that.
            int[] versionSpec = null;
            if (versionsJSON != null) {
                int numVersions = versionsJSON.length();
                versionSpec = new int[numVersions];
                for (int i = 0; i < numVersions; i++) {
                    // See if the version was stored directly as an Integer
                    int version = versionsJSON.optInt(i, NativeProtocol.NO_PROTOCOL_AVAILABLE);
                    if (version == NativeProtocol.NO_PROTOCOL_AVAILABLE) {
                        // If not, then see if it was stored as a string that can be parsed out.
                        // If even that fails, then we will leave it as NO_PROTOCOL_AVAILABLE
                        String versionString = versionsJSON.optString(i);
                        if (!isNullOrEmpty(versionString)) {
                            try {
                                version = Integer.parseInt(versionString);
                            } catch (NumberFormatException nfe) {
                                logd(LOG_TAG, nfe);
                                version = NativeProtocol.NO_PROTOCOL_AVAILABLE;
                            }
                        }
                    }

                    versionSpec[i] = version;
                }
            }

            return versionSpec;
        }

        private String dialogName;
        private String featureName;
        private Uri fallbackUrl;
        private int[] featureVersionSpec;

        private DialogFeatureConfig(
                String dialogName,
                String featureName,
                Uri fallbackUrl,
                int[] featureVersionSpec) {
            this.dialogName = dialogName;
            this.featureName = featureName;
            this.fallbackUrl = fallbackUrl;
            this.featureVersionSpec = featureVersionSpec;
        }

        public String getDialogName() {
            return dialogName;
        }

        public String getFeatureName() {
            return featureName;
        }

        public Uri getFallbackUrl() {
            return fallbackUrl;
        }

        public int[] getVersionSpec() {
            return featureVersionSpec;
        }
    }

    /**
     * Each array represents a set of closed or open Range, like so: [0,10,50,60] - Ranges are
     * {0-9}, {50-59} [20] - Ranges are {20-} [30,40,100] - Ranges are {30-39}, {100-}
     * <p/>
     * All Ranges in the array have a closed lower bound. Only the last Range in each array may be
     * open. It is assumed that the passed in arrays are sorted with ascending order. It is assumed
     * that no two elements in a given are equal (i.e. no 0-length ranges)
     * <p/>
     * The method returns an intersect of the two passed in Range-sets
     *
     * @param range1 The first range
     * @param range2 The second range
     * @return The intersection of the two ranges.
     */
    public static int[] intersectRanges(int[] range1, int[] range2) {
        if (range1 == null) {
            return range2;
        } else if (range2 == null) {
            return range1;
        }

        int[] outputRange = new int[range1.length + range2.length];
        int outputIndex = 0;
        int index1 = 0, lower1, upper1;
        int index2 = 0, lower2, upper2;
        while (index1 < range1.length && index2 < range2.length) {
            int newRangeLower = Integer.MIN_VALUE, newRangeUpper = Integer.MAX_VALUE;
            lower1 = range1[index1];
            upper1 = Integer.MAX_VALUE;

            lower2 = range2[index2];
            upper2 = Integer.MAX_VALUE;

            if (index1 < range1.length - 1) {
                upper1 = range1[index1 + 1];
            }
            if (index2 < range2.length - 1) {
                upper2 = range2[index2 + 1];
            }

            if (lower1 < lower2) {
                if (upper1 > lower2) {
                    newRangeLower = lower2;
                    if (upper1 > upper2) {
                        newRangeUpper = upper2;
                        index2 += 2;
                    } else {
                        newRangeUpper = upper1;
                        index1 += 2;
                    }
                } else {
                    index1 += 2;
                }
            } else {
                if (upper2 > lower1) {
                    newRangeLower = lower1;
                    if (upper2 > upper1) {
                        newRangeUpper = upper1;
                        index1 += 2;
                    } else {
                        newRangeUpper = upper2;
                        index2 += 2;
                    }
                } else {
                    index2 += 2;
                }
            }

            if (newRangeLower != Integer.MIN_VALUE) {
                outputRange[outputIndex++] = newRangeLower;
                if (newRangeUpper != Integer.MAX_VALUE) {
                    outputRange[outputIndex++] = newRangeUpper;
                } else {
                    // If we reach an unbounded/open range, then we know we're done.
                    break;
                }
            }
        }

        return Arrays.copyOf(outputRange, outputIndex);
    }

    // Returns true iff all items in subset are in superset, treating null and
    // empty collections as
    // the same.
    public static <T> boolean isSubset(Collection<T> subset, Collection<T> superset) {
        if ((superset == null) || (superset.size() == 0)) {
            return ((subset == null) || (subset.size() == 0));
        }

        HashSet<T> hash = new HashSet<T>(superset);
        for (T t : subset) {
            if (!hash.contains(t)) {
                return false;
            }
        }
        return true;
    }

    public static <T> boolean isNullOrEmpty(Collection<T> c) {
        return (c == null) || (c.size() == 0);
    }

    public static boolean isNullOrEmpty(String s) {
        return (s == null) || (s.length() == 0);
    }

    /**
     * Use this when you want to normalize empty and null strings
     * This way, Utility.areObjectsEqual can used for comparison, where a null string is to be
     * treated the same as an empty string.
     *
     * @param s                  The string to coerce
     * @param valueIfNullOrEmpty The value if s is null or empty.
     * @return The original string s if it's not null or empty, otherwise the valueIfNullOrEmpty
     */
    public static String coerceValueIfNullOrEmpty(String s, String valueIfNullOrEmpty) {
        if (isNullOrEmpty(s)) {
            return valueIfNullOrEmpty;
        }

        return s;
    }

    public static <T> Collection<T> unmodifiableCollection(T... ts) {
        return Collections.unmodifiableCollection(Arrays.asList(ts));
    }

    public static <T> ArrayList<T> arrayList(T... ts) {
        ArrayList<T> arrayList = new ArrayList<T>(ts.length);
        for (T t : ts) {
            arrayList.add(t);
        }
        return arrayList;
    }

    public static <T> HashSet<T> hashSet(T... ts) {
        HashSet<T> hashSet = new HashSet<T>(ts.length);
        for (T t : ts) {
            hashSet.add(t);
        }
        return hashSet;
    }

    public static String md5hash(String key) {
        return hashWithAlgorithm(HASH_ALGORITHM_MD5, key);
    }

    public static String sha1hash(String key) {
        return hashWithAlgorithm(HASH_ALGORITHM_SHA1, key);
    }

    public static String sha1hash(byte[] bytes) {
        return hashWithAlgorithm(HASH_ALGORITHM_SHA1, bytes);
    }

    private static String hashWithAlgorithm(String algorithm, String key) {
        return hashWithAlgorithm(algorithm, key.getBytes());
    }

    private static String hashWithAlgorithm(String algorithm, byte[] bytes) {
        MessageDigest hash;
        try {
            hash = MessageDigest.getInstance(algorithm);
        } catch (NoSuchAlgorithmException e) {
            return null;
        }
        return hashBytes(hash, bytes);
    }

    private static String hashBytes(MessageDigest hash, byte[] bytes) {
        hash.update(bytes);
        byte[] digest = hash.digest();
        StringBuilder builder = new StringBuilder();
        for (int b : digest) {
            builder.append(Integer.toHexString((b >> 4) & 0xf));
            builder.append(Integer.toHexString((b >> 0) & 0xf));
        }
        return builder.toString();
    }

    public static Uri buildUri(String authority, String path, Bundle parameters) {
        Uri.Builder builder = new Uri.Builder();
        builder.scheme(URL_SCHEME);
        builder.authority(authority);
        builder.path(path);
        if (parameters != null) {
            for (String key : parameters.keySet()) {
                Object parameter = parameters.get(key);
                if (parameter instanceof String) {
                    builder.appendQueryParameter(key, (String) parameter);
                }
            }
        }
        return builder.build();
    }

    public static Bundle parseUrlQueryString(String queryString) {
        Bundle params = new Bundle();
        if (!isNullOrEmpty(queryString)) {
            String array[] = queryString.split("&");
            for (String parameter : array) {
                String keyValuePair[] = parameter.split("=");

                try {
                    if (keyValuePair.length == 2) {
                        params.putString(
                                URLDecoder.decode(keyValuePair[0], UTF8),
                                URLDecoder.decode(keyValuePair[1], UTF8));
                    } else if (keyValuePair.length == 1) {
                        params.putString(
                                URLDecoder.decode(keyValuePair[0], UTF8),
                                "");
                    }
                } catch (UnsupportedEncodingException e) {
                    // shouldn't happen
                    logd(LOG_TAG, e);
                }
            }
        }
        return params;
    }

    public static void putNonEmptyString(Bundle b, String key, String value) {
        if (!Utility.isNullOrEmpty(value)) {
            b.putString(key, value);
        }
    }

    public static void putCommaSeparatedStringList(Bundle b, String key, ArrayList<String> list) {
        if (list != null) {
            StringBuilder builder = new StringBuilder();
            for (String string : list) {
                builder.append(string);
                builder.append(",");
            }
            String commaSeparated = "";
            if (builder.length() > 0) {
                commaSeparated = builder.substring(0, builder.length() - 1);
            }
            b.putString(key, commaSeparated);
        }
    }

    public static void putUri(Bundle b, String key, Uri uri) {
        if (uri != null) {
            Utility.putNonEmptyString(b, key, uri.toString());
        }
    }

    public static boolean putJSONValueInBundle(Bundle bundle, String key, Object value) {
        if (value == null) {
            bundle.remove(key);
        } else if (value instanceof Boolean) {
            bundle.putBoolean(key, (boolean) value);
        } else if (value instanceof boolean[]) {
            bundle.putBooleanArray(key, (boolean[]) value);
        } else if (value instanceof Double) {
            bundle.putDouble(key, (double) value);
        } else if (value instanceof double[]) {
            bundle.putDoubleArray(key, (double[]) value);
        } else if (value instanceof Integer) {
            bundle.putInt(key, (int) value);
        } else if (value instanceof int[]) {
            bundle.putIntArray(key, (int[]) value);
        } else if (value instanceof Long) {
            bundle.putLong(key, (long) value);
        } else if (value instanceof long[]) {
            bundle.putLongArray(key, (long[]) value);
        } else if (value instanceof String) {
            bundle.putString(key, (String) value);
        } else if (value instanceof JSONArray) {
            bundle.putString(key, ((JSONArray) value).toString());
        } else if (value instanceof JSONObject) {
            bundle.putString(key, ((JSONObject) value).toString());
        } else {
            return false;
        }
        return true;
    }

    public static void closeQuietly(Closeable closeable) {
        try {
            if (closeable != null) {
                closeable.close();
            }
        } catch (IOException ioe) {
            // ignore
        }
    }

    public static void disconnectQuietly(URLConnection connection) {
        if (connection instanceof HttpURLConnection) {
            ((HttpURLConnection) connection).disconnect();
        }
    }

    public static String getMetadataApplicationId(Context context) {
        Validate.notNull(context, "context");

        FacebookSdk.sdkInitialize(context);

        return FacebookSdk.getApplicationId();
    }

    static Map<String, Object> convertJSONObjectToHashMap(JSONObject jsonObject) {
        HashMap<String, Object> map = new HashMap<String, Object>();
        JSONArray keys = jsonObject.names();
        for (int i = 0; i < keys.length(); ++i) {
            String key;
            try {
                key = keys.getString(i);
                Object value = jsonObject.get(key);
                if (value instanceof JSONObject) {
                    value = convertJSONObjectToHashMap((JSONObject) value);
                }
                map.put(key, value);
            } catch (JSONException e) {
            }
        }
        return map;
    }

    // Returns either a JSONObject or JSONArray representation of the 'key' property of
    // 'jsonObject'.
    public static Object getStringPropertyAsJSON(
            JSONObject jsonObject,
            String key,
            String nonJSONPropertyKey
    ) throws JSONException {
        Object value = jsonObject.opt(key);
        if (value != null && value instanceof String) {
            JSONTokener tokener = new JSONTokener((String) value);
            value = tokener.nextValue();
        }

        if (value != null && !(value instanceof JSONObject || value instanceof JSONArray)) {
            if (nonJSONPropertyKey != null) {
                // Facebook sometimes gives us back a non-JSON value such as
                // literal "true" or "false" as a result.
                // If we got something like that, we present it to the caller as a JSONObject
                // with a single property. We only do this if the caller wants that behavior.
                jsonObject = new JSONObject();
                jsonObject.putOpt(nonJSONPropertyKey, value);
                return jsonObject;
            } else {
                throw new FacebookException("Got an unexpected non-JSON object.");
            }
        }

        return value;

    }

    public static String readStreamToString(InputStream inputStream) throws IOException {
        BufferedInputStream bufferedInputStream = null;
        InputStreamReader reader = null;
        try {
            bufferedInputStream = new BufferedInputStream(inputStream);
            reader = new InputStreamReader(bufferedInputStream);
            StringBuilder stringBuilder = new StringBuilder();

            final int bufferSize = 1024 * 2;
            char[] buffer = new char[bufferSize];
            int n = 0;
            while ((n = reader.read(buffer)) != -1) {
                stringBuilder.append(buffer, 0, n);
            }

            return stringBuilder.toString();
        } finally {
            closeQuietly(bufferedInputStream);
            closeQuietly(reader);
        }
    }

    public static int copyAndCloseInputStream(InputStream inputStream, OutputStream outputStream)
            throws IOException {
        BufferedInputStream bufferedInputStream = null;
        int totalBytes = 0;
        try {
            bufferedInputStream = new BufferedInputStream(inputStream);

            byte[] buffer = new byte[8192];
            int bytesRead;
            while ((bytesRead = bufferedInputStream.read(buffer)) != -1) {
                outputStream.write(buffer, 0, bytesRead);
                totalBytes += bytesRead;
            }
        } finally {
            if (bufferedInputStream != null) {
                bufferedInputStream.close();
            }
            if (inputStream != null) {
                inputStream.close();
            }
        }

        return totalBytes;
    }

    public static boolean stringsEqualOrEmpty(String a, String b) {
        boolean aEmpty = TextUtils.isEmpty(a);
        boolean bEmpty = TextUtils.isEmpty(b);

        if (aEmpty && bEmpty) {
            // Both null or empty, they match.
            return true;
        }
        if (!aEmpty && !bEmpty) {
            // Both non-empty, check equality.
            return a.equals(b);
        }
        // One empty, one non-empty, can't match.
        return false;
    }

    private static void clearCookiesForDomain(Context context, String domain) {
        // This is to work around a bug where CookieManager may fail to instantiate if
        // CookieSyncManager has never been created.
        CookieSyncManager syncManager = CookieSyncManager.createInstance(context);
        syncManager.sync();

        CookieManager cookieManager = CookieManager.getInstance();

        String cookies = cookieManager.getCookie(domain);
        if (cookies == null) {
            return;
        }

        String[] splitCookies = cookies.split(";");
        for (String cookie : splitCookies) {
            String[] cookieParts = cookie.split("=");
            if (cookieParts.length > 0) {
                String newCookie = cookieParts[0].trim() +
                        "=;expires=Sat, 1 Jan 2000 00:00:01 UTC;";
                cookieManager.setCookie(domain, newCookie);
            }
        }
        cookieManager.removeExpiredCookie();
    }

    public static void clearFacebookCookies(Context context) {
        // setCookie acts differently when trying to expire cookies between builds of Android that
        // are using Chromium HTTP stack and those that are not. Using both of these domains to
        // ensure it works on both.
        clearCookiesForDomain(context, "facebook.com");
        clearCookiesForDomain(context, ".facebook.com");
        clearCookiesForDomain(context, "https://facebook.com");
        clearCookiesForDomain(context, "https://.facebook.com");
    }

    public static void logd(String tag, Exception e) {
        if (FacebookSdk.isDebugEnabled() && tag != null && e != null) {
            Log.d(tag, e.getClass().getSimpleName() + ": " + e.getMessage());
        }
    }

    public static void logd(String tag, String msg) {
        if (FacebookSdk.isDebugEnabled() && tag != null && msg != null) {
            Log.d(tag, msg);
        }
    }

    public static void logd(String tag, String msg, Throwable t) {
        if (FacebookSdk.isDebugEnabled() && !isNullOrEmpty(tag)) {
            Log.d(tag, msg, t);
        }
    }

    public static <T> boolean areObjectsEqual(T a, T b) {
        if (a == null) {
            return b == null;
        }
        return a.equals(b);
    }

    public static boolean hasSameId(JSONObject a, JSONObject b) {
        if (a == null || b == null || !a.has("id") || !b.has("id")) {
            return false;
        }
        if (a.equals(b)) {
            return true;
        }
        String idA = a.optString("id");
        String idB = b.optString("id");
        if (idA == null || idB == null) {
            return false;
        }
        return idA.equals(idB);
    }

    public static void loadAppSettingsAsync(
            final Context context,
            final String applicationId
    ) {
        boolean canStartLoading = loadingSettings.compareAndSet(false, true);
        if (Utility.isNullOrEmpty(applicationId) ||
                fetchedAppSettings.containsKey(applicationId) ||
                !canStartLoading) {
            return;
        }

        final String settingsKey = String.format(APP_SETTINGS_PREFS_KEY_FORMAT, applicationId);

        FacebookSdk.getExecutor().execute(new Runnable() {
            @Override
            public void run() {
                JSONObject resultJSON = getAppSettingsQueryResponse(applicationId);
                if (resultJSON != null) {
                    parseAppSettingsFromJSON(applicationId, resultJSON);

                    SharedPreferences sharedPrefs = context.getSharedPreferences(
                            APP_SETTINGS_PREFS_STORE,
                            Context.MODE_PRIVATE);
                    sharedPrefs.edit()
                            .putString(settingsKey, resultJSON.toString())
                            .apply();
                }

                loadingSettings.set(false);
            }
        });

        // Also see if we had a cached copy and use that immediately.
        SharedPreferences sharedPrefs = context.getSharedPreferences(
                APP_SETTINGS_PREFS_STORE,
                Context.MODE_PRIVATE);
        String settingsJSONString = sharedPrefs.getString(settingsKey, null);
        if (!isNullOrEmpty(settingsJSONString)) {
            JSONObject settingsJSON = null;
            try {
                settingsJSON = new JSONObject(settingsJSONString);
            } catch (JSONException je) {
                logd(LOG_TAG, je);
            }
            if (settingsJSON != null) {
                parseAppSettingsFromJSON(applicationId, settingsJSON);
            }
        }
    }

    // This call only gets the app settings if they're already fetched
    public static FetchedAppSettings getAppSettingsWithoutQuery(final String applicationId) {
        return applicationId != null ? fetchedAppSettings.get(applicationId) : null;
    }

    // Note that this method makes a synchronous Graph API call, so should not be called from the
    // main thread.
    public static FetchedAppSettings queryAppSettings(
            final String applicationId,
            final boolean forceRequery) {
        // Cache the last app checked results.
        if (!forceRequery && fetchedAppSettings.containsKey(applicationId)) {
            return fetchedAppSettings.get(applicationId);
        }

        JSONObject response = getAppSettingsQueryResponse(applicationId);
        if (response == null) {
            return null;
        }

        return parseAppSettingsFromJSON(applicationId, response);
    }

    private static FetchedAppSettings parseAppSettingsFromJSON(
            String applicationId,
            JSONObject settingsJSON) {
        JSONArray errorClassificationJSON =
                settingsJSON.optJSONArray(APP_SETTING_ANDROID_SDK_ERROR_CATEGORIES);
        FacebookRequestErrorClassification errorClassification =
                errorClassificationJSON == null
                        ? FacebookRequestErrorClassification.getDefaultErrorClassification()
                        : FacebookRequestErrorClassification.createFromJSON(
                        errorClassificationJSON
                );
        FetchedAppSettings result = new FetchedAppSettings(
                settingsJSON.optBoolean(APP_SETTING_SUPPORTS_IMPLICIT_SDK_LOGGING, false),
                settingsJSON.optString(APP_SETTING_NUX_CONTENT, ""),
                settingsJSON.optBoolean(APP_SETTING_NUX_ENABLED, false),
                parseDialogConfigurations(settingsJSON.optJSONObject(APP_SETTING_DIALOG_CONFIGS)),
                errorClassification
        );

        fetchedAppSettings.put(applicationId, result);

        return result;
    }

    // Note that this method makes a synchronous Graph API call, so should not be called from the
    // main thread.
    private static JSONObject getAppSettingsQueryResponse(String applicationId) {
        Bundle appSettingsParams = new Bundle();
        appSettingsParams.putString(APPLICATION_FIELDS, TextUtils.join(",", APP_SETTING_FIELDS));

        GraphRequest request = GraphRequest.newGraphPathRequest(null, applicationId, null);
        request.setSkipClientToken(true);
        request.setParameters(appSettingsParams);

        return request.executeAndWait().getJSONObject();
    }

    public static DialogFeatureConfig getDialogFeatureConfig(
            String applicationId,
            String actionName,
            String featureName) {
        if (Utility.isNullOrEmpty(actionName) || Utility.isNullOrEmpty(featureName)) {
            return null;
        }

        FetchedAppSettings settings = fetchedAppSettings.get(applicationId);
        if (settings != null) {
            Map<String, DialogFeatureConfig> featureMap =
                    settings.getDialogConfigurations().get(actionName);
            if (featureMap != null) {
                return featureMap.get(featureName);
            }
        }
        return null;
    }

    private static Map<String, Map<String, DialogFeatureConfig>> parseDialogConfigurations(
            JSONObject dialogConfigResponse) {
        HashMap<String, Map<String, DialogFeatureConfig>> dialogConfigMap = new HashMap<String, Map<String, DialogFeatureConfig>>();

        if (dialogConfigResponse != null) {
            JSONArray dialogConfigData = dialogConfigResponse.optJSONArray("data");
            if (dialogConfigData != null) {
                for (int i = 0; i < dialogConfigData.length(); i++) {
                    DialogFeatureConfig dialogConfig = DialogFeatureConfig.parseDialogConfig(
                            dialogConfigData.optJSONObject(i));
                    if (dialogConfig == null) {
                        continue;
                    }

                    String dialogName = dialogConfig.getDialogName();
                    Map<String, DialogFeatureConfig> featureMap = dialogConfigMap.get(dialogName);
                    if (featureMap == null) {
                        featureMap = new HashMap<String, DialogFeatureConfig>();
                        dialogConfigMap.put(dialogName, featureMap);
                    }
                    featureMap.put(dialogConfig.getFeatureName(), dialogConfig);
                }
            }
        }

        return dialogConfigMap;
    }

    public static String safeGetStringFromResponse(JSONObject response, String propertyName) {
        return response != null ? response.optString(propertyName, "") : "";
    }

    public static JSONObject tryGetJSONObjectFromResponse(JSONObject response, String propertyKey) {
        return response != null ? response.optJSONObject(propertyKey) : null;
    }

    public static JSONArray tryGetJSONArrayFromResponse(JSONObject response, String propertyKey) {
        return response != null ? response.optJSONArray(propertyKey) : null;
    }

    public static void clearCaches(Context context) {
        ImageDownloader.clearCache(context);
    }

    public static void deleteDirectory(File directoryOrFile) {
        if (!directoryOrFile.exists()) {
            return;
        }

        if (directoryOrFile.isDirectory()) {
            for (File child : directoryOrFile.listFiles()) {
                deleteDirectory(child);
            }
        }
        directoryOrFile.delete();
    }

    public static <T> List<T> asListNoNulls(T... array) {
        ArrayList<T> result = new ArrayList<T>();
        for (T t : array) {
            if (t != null) {
                result.add(t);
            }
        }
        return result;
    }

    public static List<String> jsonArrayToStringList(JSONArray jsonArray) throws JSONException {
        ArrayList<String> result = new ArrayList<>();

        for (int i = 0; i < jsonArray.length(); i++) {
            result.add(jsonArray.getString(i));
        }

        return result;
    }

    public static Set<String> jsonArrayToSet(JSONArray jsonArray) throws JSONException {
        Set<String> result = new HashSet<>();
        for (int i = 0; i < jsonArray.length(); i++) {
            result.add(jsonArray.getString(i));
        }

        return result;
    }

    public static void setAppEventAttributionParameters(
            JSONObject params,
            AttributionIdentifiers attributionIdentifiers,
            String anonymousAppDeviceGUID,
            boolean limitEventUsage) throws JSONException {
        if (attributionIdentifiers != null && attributionIdentifiers.getAttributionId() != null) {
            params.put("attribution", attributionIdentifiers.getAttributionId());
        }

        if (attributionIdentifiers != null &&
                attributionIdentifiers.getAndroidAdvertiserId() != null) {
            params.put("advertiser_id", attributionIdentifiers.getAndroidAdvertiserId());
            params.put("advertiser_tracking_enabled", !attributionIdentifiers.isTrackingLimited());
        }

        params.put("anon_id", anonymousAppDeviceGUID);
        params.put("application_tracking_enabled", !limitEventUsage);
    }

    public static void setAppEventExtendedDeviceInfoParameters(
            JSONObject params,
            Context appContext
    ) throws JSONException {
        JSONArray extraInfoArray = new JSONArray();
        extraInfoArray.put(EXTRA_APP_EVENTS_INFO_FORMAT_VERSION);

        Utility.refreshPeriodicExtendedDeviceInfo(appContext);

        // Application Manifest info:
        String pkgName = appContext.getPackageName();
        int versionCode = -1;
        String versionName = "";

        try {
            PackageInfo pi = appContext.getPackageManager().getPackageInfo(pkgName, 0);
            versionCode = pi.versionCode;
            versionName = pi.versionName;
        } catch (PackageManager.NameNotFoundException e) {
            // Swallow
        }

        // Application Manifest info:
        extraInfoArray.put(pkgName);
        extraInfoArray.put(versionCode);
        extraInfoArray.put(versionName);

        // OS/Device info
        extraInfoArray.put(Build.VERSION.RELEASE);
        extraInfoArray.put(Build.MODEL);

        // Locale
        Locale locale = null;
        try {
            locale = appContext.getResources().getConfiguration().locale;
        } catch (Exception e) {
            locale = Locale.getDefault();
        }
        extraInfoArray.put(locale.getLanguage() + "_" + locale.getCountry());

        // Time zone
        extraInfoArray.put(deviceTimezone);

        // Carrier
        extraInfoArray.put(carrierName);

        // Screen dimensions
        int width = 0;
        int height = 0;
        double density = 0;
        try {
            WindowManager wm = (WindowManager) appContext.getSystemService(Context.WINDOW_SERVICE);
            if (wm != null) {
                Display display = wm.getDefaultDisplay();
                DisplayMetrics displayMetrics = new DisplayMetrics();
                display.getMetrics(displayMetrics);
                width = displayMetrics.widthPixels;
                height = displayMetrics.heightPixels;
                density = displayMetrics.density;
            }
        } catch (Exception e) {
            // Swallow
        }
        extraInfoArray.put(width);
        extraInfoArray.put(height);
        extraInfoArray.put(String.format("%.2f", density));

        // CPU Cores
        extraInfoArray.put(refreshBestGuessNumberOfCPUCores());

        // External Storage
        extraInfoArray.put(totalExternalStorageGB);
        extraInfoArray.put(availableExternalStorageGB);

        params.put("extinfo", extraInfoArray.toString());
    }

    public static Method getMethodQuietly(
            Class<?> clazz,
            String methodName,
            Class<?>... parameterTypes) {
        try {
            return clazz.getMethod(methodName, parameterTypes);
        } catch (NoSuchMethodException ex) {
            return null;
        }
    }

    public static Method getMethodQuietly(
            String className,
            String methodName,
            Class<?>... parameterTypes) {
        try {
            Class<?> clazz = Class.forName(className);
            return getMethodQuietly(clazz, methodName, parameterTypes);
        } catch (ClassNotFoundException ex) {
            return null;
        }
    }

    public static Object invokeMethodQuietly(Object receiver, Method method, Object... args) {
        try {
            return method.invoke(receiver, args);
        } catch (IllegalAccessException ex) {
            return null;
        } catch (InvocationTargetException ex) {
            return null;
        }
    }

    /**
     * Returns the name of the current activity if the context is an activity, otherwise return
     * "unknown"
     */
    public static String getActivityName(Context context) {
        if (context == null) {
            return "null";
        } else if (context == context.getApplicationContext()) {
            return "unknown";
        } else {
            return context.getClass().getSimpleName();
        }
    }

    public interface Predicate<T> {
        public boolean apply(T item);
    }

    public static <T> List<T> filter(final List<T> target, final Predicate<T> predicate) {
        if (target == null) {
            return null;
        }
        final List<T> list = new ArrayList<T>();
        for (T item : target) {
            if (predicate.apply(item)) {
                list.add(item);
            }
        }
        return (list.size() == 0 ? null : list);
    }

    public interface Mapper<T, K> {
        public K apply(T item);
    }

    public static <T, K> List<K> map(final List<T> target, final Mapper<T, K> mapper) {
        if (target == null) {
            return null;
        }
        final List<K> list = new ArrayList<K>();
        for (T item : target) {
            final K mappedItem = mapper.apply(item);
            if (mappedItem != null) {
                list.add(mappedItem);
            }
        }
        return (list.size() == 0 ? null : list);
    }

    public static String getUriString(final Uri uri) {
        return (uri == null ? null : uri.toString());
    }

    public static boolean isWebUri(final Uri uri) {
        return (uri != null)
                && ("http".equalsIgnoreCase(uri.getScheme())
                || "https".equalsIgnoreCase(uri.getScheme()));
    }

    public static boolean isContentUri(final Uri uri) {
        return (uri != null) && ("content".equalsIgnoreCase(uri.getScheme()));
    }

    public static boolean isFileUri(final Uri uri) {
        return (uri != null) && ("file".equalsIgnoreCase(uri.getScheme()));
    }

    public static long getContentSize(final Uri contentUri) {
        Cursor cursor = null;
        try {
            cursor = FacebookSdk
                    .getApplicationContext()
                    .getContentResolver()
                    .query(contentUri, null, null, null, null);
            int sizeIndex = cursor.getColumnIndex(OpenableColumns.SIZE);

            cursor.moveToFirst();
            return cursor.getLong(sizeIndex);
        } finally {
            if (cursor != null) {
                cursor.close();
            }
        }
    }

    public static Date getBundleLongAsDate(Bundle bundle, String key, Date dateBase) {
        if (bundle == null) {
            return null;
        }

        long secondsFromBase = Long.MIN_VALUE;

        Object secondsObject = bundle.get(key);
        if (secondsObject instanceof Long) {
            secondsFromBase = (Long) secondsObject;
        } else if (secondsObject instanceof String) {
            try {
                secondsFromBase = Long.parseLong((String) secondsObject);
            } catch (NumberFormatException e) {
                return null;
            }
        } else {
            return null;
        }

        if (secondsFromBase == 0) {
            return new Date(Long.MAX_VALUE);
        } else {
            return new Date(dateBase.getTime() + (secondsFromBase * 1000L));
        }
    }

    public static void writeStringMapToParcel(Parcel parcel, final Map<String, String> map) {
        if (map == null) {
            // 0 is for empty map, -1 to indicate null
            parcel.writeInt(-1);
        } else {
            parcel.writeInt(map.size());
            for (Map.Entry<String, String> entry : map.entrySet()) {
                parcel.writeString(entry.getKey());
                parcel.writeString(entry.getValue());
            }
        }
    }

    public static Map<String, String> readStringMapFromParcel(Parcel parcel) {
        int size = parcel.readInt();
        if (size < 0) {
            return null;
        }
        Map<String, String> map = new HashMap<>();
        for (int i = 0; i < size; i++) {
            map.put(parcel.readString(), parcel.readString());
        }
        return map;
    }

    public static boolean isCurrentAccessToken(AccessToken token) {
        return token != null ? token.equals(AccessToken.getCurrentAccessToken()) : false;
    }

    public interface GraphMeRequestWithCacheCallback {
        void onSuccess(JSONObject userInfo);

        void onFailure(FacebookException error);
    }

    public static void getGraphMeRequestWithCacheAsync(
            final String accessToken,
            final GraphMeRequestWithCacheCallback callback) {
        JSONObject cachedValue = ProfileInformationCache.getProfileInformation(accessToken);
        if (cachedValue != null) {
            callback.onSuccess(cachedValue);
            return;
        }

        GraphRequest.Callback graphCallback = new GraphRequest.Callback() {
            @Override
            public void onCompleted(GraphResponse response) {
                if (response.getError() != null) {
                    callback.onFailure(response.getError().getException());
                } else {
                    ProfileInformationCache.putProfileInformation(
                            accessToken,
                            response.getJSONObject());
                    callback.onSuccess(response.getJSONObject());
                }
            }
        };
        GraphRequest graphRequest = getGraphMeRequestWithCache(accessToken);
        graphRequest.setCallback(graphCallback);
        graphRequest.executeAsync();
    }

    public static JSONObject awaitGetGraphMeRequestWithCache(
            final String accessToken) {
        JSONObject cachedValue = ProfileInformationCache.getProfileInformation(accessToken);
        if (cachedValue != null) {
            return cachedValue;
        }

        GraphRequest graphRequest = getGraphMeRequestWithCache(accessToken);
        GraphResponse response = graphRequest.executeAndWait();
        if (response.getError() != null) {
            return null;
        }

        return response.getJSONObject();
    }

    private static GraphRequest getGraphMeRequestWithCache(
            final String accessToken) {
        Bundle parameters = new Bundle();
        parameters.putString("fields", "id,name,first_name,middle_name,last_name,link");
        parameters.putString("access_token", accessToken);
        GraphRequest graphRequest = new GraphRequest(
                null,
                "me",
                parameters,
                HttpMethod.GET,
                null);
        return graphRequest;
    }

    /**
     * Return our best guess at the available number of cores. Will always return at least 1.
     * @return The minimum number of CPU cores
     */
    private static int refreshBestGuessNumberOfCPUCores() {
        // If we have calculated this before, return that value
        if (numCPUCores > 0) {
            return numCPUCores;
        }

        // Gingerbread doesn't support giving a single application access to both cores,
        // so for our purposes GB devices are effectively single core.
        if (Build.VERSION.SDK_INT <= Utility.GINGERBREAD_MR1) {
            numCPUCores = 1;
            return numCPUCores;
        }

        // Enumerate all available CPU files and try to count the number of CPU cores.
        try {
            int res = 0;
            File cpuDir = new File("/sys/devices/system/cpu/");
            File[] cpuFiles = cpuDir.listFiles(new FilenameFilter() {
                @Override
                public boolean accept(File dir, String fileName) {
                    return Pattern.matches("cpu[0-9]+", fileName);
                }
            });

            numCPUCores = cpuFiles.length;
        } catch (Exception e) {
        }

        // If enumerating and counting the CPU cores fails, use the runtime. Fallback to 1 if
        // that returns bogus values.
        if (numCPUCores <= 0) {
            numCPUCores = Math.max(Runtime.getRuntime().availableProcessors(), 1);
        }
        return numCPUCores;
    }

    private static void refreshPeriodicExtendedDeviceInfo(Context appContext) {
        if (timestampOfLastCheck == -1 ||
                (System.currentTimeMillis() - timestampOfLastCheck) >=
                        Utility.REFRESH_TIME_FOR_EXTENDED_DEVICE_INFO_MILLIS) {
            timestampOfLastCheck = System.currentTimeMillis();
            Utility.refreshTimezone();
            Utility.refreshCarrierName(appContext);
            Utility.refreshTotalExternalStorage();
            Utility.refreshAvailableExternalStorage();
        }
    }

    private static void refreshTimezone() {
        try {
            TimeZone tz = TimeZone.getDefault();
            deviceTimezone = tz.getDisplayName(tz.inDaylightTime(new Date()), TimeZone.SHORT);
        } catch (Exception e) {
        }
    }

    /**
     * Get and cache the carrier name since this won't change during the lifetime of the app.
     * @return The carrier name
     */
    private static void refreshCarrierName(Context appContext) {
        if (carrierName.equals(noCarrierConstant)) {
            try {
                TelephonyManager telephonyManager =
                        ((TelephonyManager) appContext.getSystemService(Context.TELEPHONY_SERVICE));
                carrierName = telephonyManager.getNetworkOperatorName();
            } catch (Exception e) {
            }
        }
    }

    /**
     * @return whether there is external storage:
     */
    private static boolean externalStorageExists() {
        return Environment.MEDIA_MOUNTED.equals(Environment.getExternalStorageState());
    }

    // getAvailableBlocks/getBlockSize deprecated but required pre-API v18
    @SuppressWarnings("deprecation")
    private static void refreshAvailableExternalStorage() {
        try {
            if (externalStorageExists()) {
                File path = Environment.getExternalStorageDirectory();
                StatFs stat = new StatFs(path.getPath());
                availableExternalStorageGB =
                        (long)stat.getAvailableBlocks() * (long)stat.getBlockSize();
            }
            availableExternalStorageGB =
                    Utility.convertBytesToGB(availableExternalStorageGB);
        } catch (Exception e) {
            // Swallow
        }
    }

    // getAvailableBlocks/getBlockSize deprecated but required pre-API v18
    @SuppressWarnings("deprecation")
    private static void refreshTotalExternalStorage() {
        try {
            if (externalStorageExists()) {
                File path = Environment.getExternalStorageDirectory();
                StatFs stat = new StatFs(path.getPath());
                totalExternalStorageGB = (long)stat.getBlockCount() * (long)stat.getBlockSize();
            }
            totalExternalStorageGB = Utility.convertBytesToGB(totalExternalStorageGB);
        } catch (Exception e) {
            // Swallow
        }
    }

    private static long convertBytesToGB(double bytes) {
        return Math.round(bytes / (1024.0 * 1024.0 * 1024.0));
    }
}


File: facebook/src/com/facebook/login/KatanaProxyLoginMethodHandler.java
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
import android.os.Bundle;
import android.os.Parcel;
import android.os.Parcelable;

import com.facebook.AccessToken;
import com.facebook.AccessTokenSource;
import com.facebook.FacebookException;
import com.facebook.internal.CallbackManagerImpl;
import com.facebook.internal.NativeProtocol;
import com.facebook.internal.ServerProtocol;
import com.facebook.internal.Utility;

class KatanaProxyLoginMethodHandler extends LoginMethodHandler {

    KatanaProxyLoginMethodHandler(LoginClient loginClient) {
        super(loginClient);
    }

    @Override
    String getNameForLogging() {
        return "katana_proxy_auth";
    }

    @Override
    boolean tryAuthorize(LoginClient.Request request) {
        String e2e = LoginClient.getE2E();
        Intent intent = NativeProtocol.createProxyAuthIntent(
                loginClient.getActivity(),
                request.getApplicationId(),
                request.getPermissions(),
                e2e,
                request.isRerequest(),
                request.hasPublishPermission(),
                request.getDefaultAudience());

        addLoggingExtra(ServerProtocol.DIALOG_PARAM_E2E, e2e);

        return tryIntent(intent, LoginClient.getLoginRequestCode());
    }

    @Override
    boolean onActivityResult(int requestCode, int resultCode, Intent data) {
        // Handle stuff
        LoginClient.Result outcome;

        LoginClient.Request request = loginClient.getPendingRequest();

        if (data == null) {
            // This happens if the user presses 'Back'.
            outcome = LoginClient.Result.createCancelResult(request, "Operation canceled");
        } else if (resultCode == Activity.RESULT_CANCELED) {
            outcome = LoginClient.Result.createCancelResult(request, data.getStringExtra("error"));
        } else if (resultCode != Activity.RESULT_OK) {
            outcome = LoginClient.Result.createErrorResult(request,
                    "Unexpected resultCode from authorization.", null);
        } else {
            outcome = handleResultOk(request, data);
        }

        if (outcome != null) {
            loginClient.completeAndValidate(outcome);
        } else {
            loginClient.tryNextHandler();
        }
        return true;
    }

    private LoginClient.Result handleResultOk(LoginClient.Request request, Intent data) {
        Bundle extras = data.getExtras();
        String error = extras.getString("error");
        if (error == null) {
            error = extras.getString("error_type");
        }
        String errorCode = extras.getString("error_code");
        String errorMessage = extras.getString("error_message");
        if (errorMessage == null) {
            errorMessage = extras.getString("error_description");
        }

        String e2e = extras.getString(NativeProtocol.FACEBOOK_PROXY_AUTH_E2E_KEY);
        if (!Utility.isNullOrEmpty(e2e)) {
            logWebLoginCompleted(e2e);
        }

        if (error == null && errorCode == null && errorMessage == null) {
            try {
                AccessToken token = createAccessTokenFromWebBundle(request.getPermissions(),
                        extras, AccessTokenSource.FACEBOOK_APPLICATION_WEB,
                        request.getApplicationId());
                return LoginClient.Result.createTokenResult(request, token);
            } catch (FacebookException ex) {
                return LoginClient.Result.createErrorResult(request, null, ex.getMessage());
            }
        } else if (ServerProtocol.errorsProxyAuthDisabled.contains(error)) {
            return null;
        } else if (ServerProtocol.errorsUserCanceled.contains(error)) {
            return LoginClient.Result.createCancelResult(request, null);
        } else {
            return LoginClient.Result.createErrorResult(request, error, errorMessage, errorCode);
        }
    }

    protected boolean tryIntent(Intent intent, int requestCode) {
        if (intent == null) {
            return false;
        }

        try {
            loginClient.getFragment().startActivityForResult(intent, requestCode);
        } catch (ActivityNotFoundException e) {
            // We don't expect this to happen, since we've already validated the intent and bailed
            // out before now if it couldn't be resolved.
            return false;
        }

        return true;
    }

    KatanaProxyLoginMethodHandler(Parcel source) {
        super(source);
    }

    @Override
    public int describeContents() {
        return 0;
    }

    @Override
    public void writeToParcel(Parcel dest, int flags) {
        super.writeToParcel(dest, flags);
    }

    public static final Parcelable.Creator<KatanaProxyLoginMethodHandler> CREATOR =
            new Parcelable.Creator() {

                @Override
                public KatanaProxyLoginMethodHandler createFromParcel(Parcel source) {
                    return new KatanaProxyLoginMethodHandler(source);
                }

                @Override
                public KatanaProxyLoginMethodHandler[] newArray(int size) {
                    return new KatanaProxyLoginMethodHandler[size];
                }
            };
}


File: facebook/src/com/facebook/login/LoginBehavior.java
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

/**
 * Specifies the behaviors to try during login.
 */
public enum LoginBehavior {
    /**
     * Specifies that login should attempt Single Sign On (SSO), and if that
     * does not work fall back to dialog auth. This is the default behavior.
     */
    SSO_WITH_FALLBACK(true, true),

    /**
     * Specifies that login should only attempt SSO. If SSO fails, then the
     * login fails.
     */
    SSO_ONLY(true, false),

    /**
     * Specifies that SSO should not be attempted, and to only use dialog auth.
     */
    SUPPRESS_SSO(false, true);

    private final boolean allowsKatanaAuth;
    private final boolean allowsWebViewAuth;

    private LoginBehavior(boolean allowsKatanaAuth, boolean allowsWebViewAuth) {
        this.allowsKatanaAuth = allowsKatanaAuth;
        this.allowsWebViewAuth = allowsWebViewAuth;
    }

    boolean allowsKatanaAuth() {
        return allowsKatanaAuth;
    }

    boolean allowsWebViewAuth() {
        return allowsWebViewAuth;
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
        if (context == null || pendingLoginRequest == null) {
            return null;
        }

        LoginLogger logger = this.loginLogger;
        if (logger == null ||
                !logger.getApplicationId().equals(pendingLoginRequest.getApplicationId())) {
            logger = new LoginLogger(context, pendingLoginRequest.getApplicationId());
        }
        return logger;
    }

    private void logStartLogin() {
        if (loginLogger != null && pendingLoginRequest != null) {
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

        this.pendingLoginRequest = null;
        this.loginLogger = null;
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


File: facebook/src/com/facebook/login/widget/LoginButton.java
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

import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.res.Resources;
import android.content.res.TypedArray;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.os.Bundle;
import android.util.AttributeSet;
import android.view.View;
import com.facebook.*;
import com.facebook.appevents.AppEventsLogger;
import com.facebook.internal.AnalyticsEvents;
import com.facebook.internal.CallbackManagerImpl;
import com.facebook.internal.LoginAuthorizationType;
import com.facebook.internal.Utility;
import com.facebook.internal.Utility.FetchedAppSettings;
import com.facebook.login.DefaultAudience;
import com.facebook.login.LoginBehavior;
import com.facebook.login.LoginManager;
import com.facebook.login.LoginResult;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/**
 * A Log In/Log Out button that maintains login state and logs in/out for the app.
 * <p/>
 * This control requires the app ID to be specified in the AndroidManifest.xml.
 */
public class LoginButton extends FacebookButtonBase {

    // ***
    // Keep all the enum values in sync with attrs.xml
    // ***

    /**
     * The display modes for the login button tool tip.
     */
    public enum ToolTipMode {
        /**
         * Default display mode. A server query will determine if the tool tip should be displayed
         * and, if so, what the string shown to the user should be.
         */
        AUTOMATIC("automatic", 0),

        /**
         * Display the tool tip with a local string--regardless of what the server returns
         */
        DISPLAY_ALWAYS("display_always", 1),

        /**
         * Never display the tool tip--regardless of what the server says
         */
        NEVER_DISPLAY("never_display", 2);

        public static ToolTipMode DEFAULT = AUTOMATIC;

        public static ToolTipMode fromInt(int enumValue) {
            for (ToolTipMode mode : values()) {
                if (mode.getValue() == enumValue) {
                    return mode;
                }
            }

            return null;
        }

        private String stringValue;
        private int intValue;
        ToolTipMode(String stringValue, int value) {
            this.stringValue = stringValue;
            this.intValue = value;
        }

        @Override
        public String toString() {
            return stringValue;
        }

        public int getValue() {
            return intValue;
        }
    }

    private static final String TAG = LoginButton.class.getName();
    private boolean confirmLogout;
    private String loginText;
    private String logoutText;
    private LoginButtonProperties properties = new LoginButtonProperties();
    private String loginLogoutEventName = AnalyticsEvents.EVENT_LOGIN_VIEW_USAGE;
    private boolean toolTipChecked;
    private ToolTipPopup.Style toolTipStyle = ToolTipPopup.Style.BLUE;
    private ToolTipMode toolTipMode;
    private long toolTipDisplayTime = ToolTipPopup.DEFAULT_POPUP_DISPLAY_TIME;
    private ToolTipPopup toolTipPopup;
    private AccessTokenTracker accessTokenTracker;
    private LoginManager loginManager;

    static class LoginButtonProperties {
        private DefaultAudience defaultAudience = DefaultAudience.FRIENDS;
        private List<String> permissions = Collections.<String>emptyList();
        private LoginAuthorizationType authorizationType = null;
        private LoginBehavior loginBehavior = LoginBehavior.SSO_WITH_FALLBACK;

        public void setDefaultAudience(DefaultAudience defaultAudience) {
            this.defaultAudience = defaultAudience;
        }

        public DefaultAudience getDefaultAudience() {
            return defaultAudience;
        }

        public void setReadPermissions(List<String> permissions) {

            if (LoginAuthorizationType.PUBLISH.equals(authorizationType)) {
                throw new UnsupportedOperationException("Cannot call setReadPermissions after " +
                        "setPublishPermissions has been called.");
            }
            this.permissions = permissions;
            authorizationType = LoginAuthorizationType.READ;
        }

        public void setPublishPermissions(List<String> permissions) {

            if (LoginAuthorizationType.READ.equals(authorizationType)) {
                throw new UnsupportedOperationException("Cannot call setPublishPermissions after " +
                        "setReadPermissions has been called.");
            }
            if (Utility.isNullOrEmpty(permissions)) {
                throw new IllegalArgumentException(
                        "Permissions for publish actions cannot be null or empty.");
            }
            this.permissions = permissions;
            authorizationType = LoginAuthorizationType.PUBLISH;
        }

        List<String> getPermissions() {
            return permissions;
        }

        public void clearPermissions() {
            permissions = null;
            authorizationType = null;
        }

        public void setLoginBehavior(LoginBehavior loginBehavior) {
            this.loginBehavior = loginBehavior;
        }

        public LoginBehavior getLoginBehavior() {
            return loginBehavior;
        }
    }

    /**
     * Create the LoginButton by inflating from XML
     *
     * @see View#View(Context, AttributeSet)
     */
    public LoginButton(Context context) {
        super(
                context,
                null,
                0,
                0,
                AnalyticsEvents.EVENT_LOGIN_BUTTON_CREATE);
    }

    /**
     * Create the LoginButton by inflating from XML
     *
     * @see View#View(Context, AttributeSet)
     */
    public LoginButton(Context context, AttributeSet attrs) {
        super(
                context,
                attrs,
                0,
                0,
                AnalyticsEvents.EVENT_LOGIN_BUTTON_CREATE);
    }

    /**
     * Create the LoginButton by inflating from XML and applying a style.
     *
     * @see View#View(Context, AttributeSet, int)
     */
    public LoginButton(Context context, AttributeSet attrs, int defStyle) {
        super(
                context,
                attrs,
                defStyle,
                0,
                AnalyticsEvents.EVENT_LOGIN_BUTTON_CREATE);
    }

    /**
     * Sets the default audience to use when the user logs in.
     * This value is only useful when specifying publish permissions for the native
     * login dialog.
     *
     * @param defaultAudience the default audience value to use
     */
    public void setDefaultAudience(DefaultAudience defaultAudience) {
        properties.setDefaultAudience(defaultAudience);
    }

    /**
     * Gets the default audience to use when the user logs in.
     * This value is only useful when specifying publish permissions for the native
     * login dialog.
     *
     * @return the default audience value to use
     */
    public DefaultAudience getDefaultAudience() {
        return properties.getDefaultAudience();
    }

    /**
     * Set the permissions to use when the user logs in. The permissions here
     * can only be read permissions. If any publish permissions are included, the login
     * attempt by the user will fail. The LoginButton can only be associated with either
     * read permissions or publish permissions, but not both. Calling both
     * setReadPermissions and setPublishPermissions on the same instance of LoginButton
     * will result in an exception being thrown unless clearPermissions is called in between.
     * <p/>
     * This method is only meaningful if called before the user logs in. If this is called
     * after login, and the list of permissions passed in is not a subset
     * of the permissions granted during the authorization, it will log an error.
     * <p/>
     * It's important to always pass in a consistent set of permissions to this method, or
     * manage the setting of permissions outside of the LoginButton class altogether
     * (by using the LoginManager explicitly).
     *
     * @param permissions the read permissions to use
     * @throws UnsupportedOperationException if setPublishPermissions has been called
     */
    public void setReadPermissions(List<String> permissions) {
        properties.setReadPermissions(permissions);
    }

    /**
     * Set the permissions to use when the user logs in. The permissions here
     * can only be read permissions. If any publish permissions are included, the login
     * attempt by the user will fail. The LoginButton can only be associated with either
     * read permissions or publish permissions, but not both. Calling both
     * setReadPermissions and setPublishPermissions on the same instance of LoginButton
     * will result in an exception being thrown unless clearPermissions is called in between.
     * <p/>
     * This method is only meaningful if called before the user logs in. If this is called
     * after login, and the list of permissions passed in is not a subset
     * of the permissions granted during the authorization, it will log an error.
     * <p/>
     * It's important to always pass in a consistent set of permissions to this method, or
     * manage the setting of permissions outside of the LoginButton class altogether
     * (by using the LoginManager explicitly).
     *
     * @param permissions the read permissions to use
     * @throws UnsupportedOperationException if setPublishPermissions has been called
     */
    public void setReadPermissions(String... permissions) {
        properties.setReadPermissions(Arrays.asList(permissions));
    }


    /**
     * Set the permissions to use when the user logs in. The permissions here
     * should only be publish permissions. If any read permissions are included, the login
     * attempt by the user may fail. The LoginButton can only be associated with either
     * read permissions or publish permissions, but not both. Calling both
     * setReadPermissions and setPublishPermissions on the same instance of LoginButton
     * will result in an exception being thrown unless clearPermissions is called in between.
     * <p/>
     * This method is only meaningful if called before the user logs in. If this is called
     * after login, and the list of permissions passed in is not a subset
     * of the permissions granted during the authorization, it will log an error.
     * <p/>
     * It's important to always pass in a consistent set of permissions to this method, or
     * manage the setting of permissions outside of the LoginButton class altogether
     * (by using the LoginManager explicitly).
     *
     * @param permissions the publish permissions to use
     * @throws UnsupportedOperationException if setReadPermissions has been called
     * @throws IllegalArgumentException      if permissions is null or empty
     */
    public void setPublishPermissions(List<String> permissions) {
        properties.setPublishPermissions(permissions);
    }

    /**
     * Set the permissions to use when the user logs in. The permissions here
     * should only be publish permissions. If any read permissions are included, the login
     * attempt by the user may fail. The LoginButton can only be associated with either
     * read permissions or publish permissions, but not both. Calling both
     * setReadPermissions and setPublishPermissions on the same instance of LoginButton
     * will result in an exception being thrown unless clearPermissions is called in between.
     * <p/>
     * This method is only meaningful if called before the user logs in. If this is called
     * after login, and the list of permissions passed in is not a subset
     * of the permissions granted during the authorization, it will log an error.
     * <p/>
     * It's important to always pass in a consistent set of permissions to this method, or
     * manage the setting of permissions outside of the LoginButton class altogether
     * (by using the LoginManager explicitly).
     *
     * @param permissions the publish permissions to use
     * @throws UnsupportedOperationException if setReadPermissions has been called
     * @throws IllegalArgumentException      if permissions is null or empty
     */
    public void setPublishPermissions(String... permissions) {
        properties.setPublishPermissions(Arrays.asList(permissions));
    }


    /**
     * Clears the permissions currently associated with this LoginButton.
     */
    public void clearPermissions() {
        properties.clearPermissions();
    }

    /**
     * Sets the login behavior during authorization. If null is specified, the default
     * ({@link com.facebook.login.LoginBehavior LoginBehavior.SSO_WITH_FALLBACK}
     * will be used.
     *
     * @param loginBehavior The {@link com.facebook.login.LoginBehavior LoginBehavior} that
     *                      specifies what behaviors should be attempted during
     *                      authorization.
     */
    public void setLoginBehavior(LoginBehavior loginBehavior) {
        properties.setLoginBehavior(loginBehavior);
    }

    /**
     * Gets the login behavior during authorization. If null is returned, the default
     * ({@link com.facebook.login.LoginBehavior LoginBehavior.SSO_WITH_FALLBACK}
     * will be used.
     *
     * @return loginBehavior The {@link com.facebook.login.LoginBehavior LoginBehavior} that
     * specifies what behaviors should be attempted during
     * authorization.
     */
    public LoginBehavior getLoginBehavior() {
        return properties.getLoginBehavior();
    }

    /**
     * Sets the style (background) of the Tool Tip popup. Currently a blue style and a black
     * style are supported. Blue is default
     *
     * @param toolTipStyle The style of the tool tip popup.
     */
    public void setToolTipStyle(ToolTipPopup.Style toolTipStyle) {
        this.toolTipStyle = toolTipStyle;
    }

    /**
     * Sets the mode of the Tool Tip popup. Currently supported modes are default (normal
     * behavior), always_on (popup remains up until forcibly dismissed), and always_off (popup
     * doesn't show)
     *
     * @param toolTipMode The new mode for the tool tip
     */
    public void setToolTipMode(ToolTipMode toolTipMode) {
        this.toolTipMode = toolTipMode;
    }

    /**
     * Return the current {@link ToolTipMode} for this LoginButton
     *
     * @return The {@link ToolTipMode}
     */
    public ToolTipMode getToolTipMode() {
        return toolTipMode;
    }

    /**
     * Sets the amount of time (in milliseconds) that the tool tip will be shown to the user. The
     * default is {@value ToolTipPopup#DEFAULT_POPUP_DISPLAY_TIME}. Any value that is less than or
     * equal to zero will cause the tool tip to be displayed indefinitely.
     *
     * @param displayTime The amount of time (in milliseconds) that the tool tip will be displayed
     *                    to the user
     */
    public void setToolTipDisplayTime(long displayTime) {
        this.toolTipDisplayTime = displayTime;
    }

    /**
     * Gets the current amount of time (in ms) that the tool tip will be displayed to the user.
     *
     * @return The current amount of time (in ms) that the tool tip will be displayed.
     */
    public long getToolTipDisplayTime() {
        return toolTipDisplayTime;
    }

    /**
     * Dismisses the Tooltip if it is currently visible
     */
    public void dismissToolTip() {
        if (toolTipPopup != null) {
            toolTipPopup.dismiss();
            toolTipPopup = null;
        }
    }

    /**
     * Registers a login callback to the given callback manager.
     *
     * @param callbackManager The callback manager that will encapsulate the callback.
     * @param callback        The login callback that will be called on login completion.
     */
    public void registerCallback(
            final CallbackManager callbackManager,
            final FacebookCallback<LoginResult> callback) {
        getLoginManager().registerCallback(callbackManager, callback);
    }

    @Override
    protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        if (accessTokenTracker != null && !accessTokenTracker.isTracking()) {
            accessTokenTracker.startTracking();
            setButtonText();
        }
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);

        if (!toolTipChecked && !isInEditMode()) {
            toolTipChecked = true;
            checkToolTipSettings();
        }
    }

    private void showToolTipPerSettings(FetchedAppSettings settings) {
        if (settings != null && settings.getNuxEnabled() && getVisibility() == View.VISIBLE) {
            String toolTipString = settings.getNuxContent();
            displayToolTip(toolTipString);
        }
    }

    private void displayToolTip(String toolTipString) {
        toolTipPopup = new ToolTipPopup(toolTipString, this);
        toolTipPopup.setStyle(toolTipStyle);
        toolTipPopup.setNuxDisplayTime(toolTipDisplayTime);
        toolTipPopup.show();
    }

    private void checkToolTipSettings() {
        switch (toolTipMode) {
            case AUTOMATIC:
                // kick off an async request
                final String appId = Utility.getMetadataApplicationId(getContext());
                FacebookSdk.getExecutor().execute(new Runnable() {
                    @Override
                    public void run() {
                        final FetchedAppSettings settings = Utility.queryAppSettings(appId, false);
                        getActivity().runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                showToolTipPerSettings(settings);
                            }
                        });
                    }
                });
                break;
            case DISPLAY_ALWAYS:
                String toolTipString = getResources().getString(
                        R.string.com_facebook_tooltip_default);
                displayToolTip(toolTipString);
                break;
            case NEVER_DISPLAY:
                break;
        }
    }

    @Override
    protected void onLayout(boolean changed, int left, int top, int right, int bottom) {
        super.onLayout(changed, left, top, right, bottom);
        setButtonText();
    }

    @Override
    protected void onDetachedFromWindow() {
        super.onDetachedFromWindow();
        if (accessTokenTracker != null) {
            accessTokenTracker.stopTracking();
        }
        dismissToolTip();
    }

    @Override
    protected void onVisibilityChanged(View changedView, int visibility) {
        super.onVisibilityChanged(changedView, visibility);
        // If the visibility is not VISIBLE, we want to dismiss the tooltip if it is there
        if (visibility != VISIBLE) {
            dismissToolTip();
        }
    }

    // For testing purposes only
    List<String> getPermissions() {
        return properties.getPermissions();
    }

    void setProperties(LoginButtonProperties properties) {
        this.properties = properties;
    }

    @Override
    protected void configureButton(
            final Context context,
            final AttributeSet attrs,
            final int defStyleAttr,
            final int defStyleRes) {
        super.configureButton(context, attrs, defStyleAttr, defStyleRes);
        setInternalOnClickListener(new LoginClickListener());

        parseLoginButtonAttributes(context, attrs, defStyleAttr, defStyleRes);

        if (isInEditMode()) {
            // cannot use a drawable in edit mode, so setting the background color instead
            // of a background resource.
            setBackgroundColor(getResources().getColor(R.color.com_facebook_blue));
            // hardcoding in edit mode as getResources().getString() doesn't seem to work in
            // IntelliJ
            loginText = "Log in with Facebook";
        } else {
            accessTokenTracker = new AccessTokenTracker() {
                @Override
                protected void onCurrentAccessTokenChanged(
                        AccessToken oldAccessToken,
                        AccessToken currentAccessToken) {
                    setButtonText();
                }
            };
        }

        setButtonText();
    }

    @Override
    protected int getDefaultStyleResource() {
        return R.style.com_facebook_loginview_default_style;
    }

    private void parseLoginButtonAttributes(
            final Context context,
            final AttributeSet attrs,
            final int defStyleAttr,
            final int defStyleRes) {
        this.toolTipMode = ToolTipMode.DEFAULT;
        final TypedArray a = context.getTheme().obtainStyledAttributes(
                attrs,
                R.styleable.com_facebook_login_view,
                defStyleAttr,
                defStyleRes);
        try {
            confirmLogout = a.getBoolean(R.styleable.com_facebook_login_view_com_facebook_confirm_logout, true);
            loginText = a.getString(R.styleable.com_facebook_login_view_com_facebook_login_text);
            logoutText = a.getString(R.styleable.com_facebook_login_view_com_facebook_logout_text);
            toolTipMode = ToolTipMode.fromInt(a.getInt(
                    R.styleable.com_facebook_login_view_com_facebook_tooltip_mode,
                    ToolTipMode.DEFAULT.getValue()));
        } finally {
            a.recycle();
        }
    }

    @Override
    protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
        Paint.FontMetrics fontMetrics = getPaint().getFontMetrics();
        int height = (getCompoundPaddingTop() +
                (int)Math.ceil(Math.abs(fontMetrics.top) + Math.abs(fontMetrics.bottom)) +
                getCompoundPaddingBottom());

        final Resources resources = getResources();
        String text = loginText;
        int logInWidth;
        int width;
        if (text == null) {
            text = resources.getString(R.string.com_facebook_loginview_log_in_button_long);
            logInWidth = measureButtonWidth(text);
            width = resolveSize(logInWidth, widthMeasureSpec);
            if (width < logInWidth) {
                text = resources.getString(R.string.com_facebook_loginview_log_in_button);
            }
        }
        logInWidth = measureButtonWidth(text);

        text = logoutText;
        if (text == null) {
            text = resources.getString(R.string.com_facebook_loginview_log_out_button);
        }
        int logOutWidth = measureButtonWidth(text);

        width = resolveSize(Math.max(logInWidth, logOutWidth), widthMeasureSpec);
        setMeasuredDimension(width, height);
    }

    private int measureButtonWidth(final String text) {
        int textWidth = measureTextWidth(text);
        int width = (getCompoundPaddingLeft() +
                getCompoundDrawablePadding() +
                textWidth +
                getCompoundPaddingRight());
        return width;
    }

    private void setButtonText() {
        final Resources resources = getResources();
        if (!isInEditMode() && AccessToken.getCurrentAccessToken() != null) {
            setText((logoutText != null) ?
                    logoutText :
                    resources.getString(R.string.com_facebook_loginview_log_out_button));
        } else {
            if (loginText != null) {
                setText(loginText);
            } else {
                String text = resources.getString(
                        R.string.com_facebook_loginview_log_in_button_long);
                int width = getWidth();
                // if the width is 0, we are going to measure size, so use the long text
                if (width != 0) {
                    // we have a specific width, check if the long text fits
                    int measuredWidth = measureButtonWidth(text);
                    if (measuredWidth > width) {
                        // it doesn't fit, use the shorter text
                        text = resources.getString(R.string.com_facebook_loginview_log_in_button);
                    }
                }
                setText(text);
            }
        }
    }

    @Override
    protected int getDefaultRequestCode() {
        return CallbackManagerImpl.RequestCodeOffset.Login.toRequestCode();
    }

    private class LoginClickListener implements OnClickListener {

        @Override
        public void onClick(View v) {
            callExternalOnClickListener(v);

            Context context = getContext();

            AccessToken accessToken = AccessToken.getCurrentAccessToken();

            if (accessToken != null) {
                // Log out
                if (confirmLogout) {
                    // Create a confirmation dialog
                    String logout = getResources().getString(
                            R.string.com_facebook_loginview_log_out_action);
                    String cancel = getResources().getString(
                            R.string.com_facebook_loginview_cancel_action);
                    String message;
                    Profile profile = Profile.getCurrentProfile();
                    if (profile != null && profile.getName() != null) {
                        message = String.format(
                                getResources().getString(
                                        R.string.com_facebook_loginview_logged_in_as),
                                profile.getName());
                    } else {
                        message = getResources().getString(
                                R.string.com_facebook_loginview_logged_in_using_facebook);
                    }
                    AlertDialog.Builder builder = new AlertDialog.Builder(context);
                    builder.setMessage(message)
                            .setCancelable(true)
                            .setPositiveButton(logout, new DialogInterface.OnClickListener() {
                                public void onClick(DialogInterface dialog, int which) {
                                    getLoginManager().logOut();
                                }
                            })
                            .setNegativeButton(cancel, null);
                    builder.create().show();
                } else {
                    getLoginManager().logOut();
                }
            } else {
                LoginManager loginManager = getLoginManager();
                loginManager.setDefaultAudience(getDefaultAudience());
                loginManager.setLoginBehavior(getLoginBehavior());

                if (LoginAuthorizationType.PUBLISH.equals(properties.authorizationType)) {
                    if (LoginButton.this.getFragment() != null) {
                        loginManager.logInWithPublishPermissions(
                                LoginButton.this.getFragment(),
                                properties.permissions);
                    } else {
                        loginManager.logInWithPublishPermissions(
                                LoginButton.this.getActivity(),
                                properties.permissions);
                    }
                } else {
                    if (LoginButton.this.getFragment() != null) {
                        loginManager.logInWithReadPermissions(
                                LoginButton.this.getFragment(),
                                properties.permissions);
                    } else {
                        loginManager.logInWithReadPermissions(
                                LoginButton.this.getActivity(),
                                properties.permissions);
                    }
                }
            }

            AppEventsLogger logger = AppEventsLogger.newLogger(getContext());

            Bundle parameters = new Bundle();
            parameters.putInt("logging_in", (accessToken != null) ? 0 : 1);

            logger.logSdkEvent(loginLogoutEventName, null, parameters);
        }
    }

    LoginManager getLoginManager() {
        if (loginManager == null) {
            loginManager = LoginManager.getInstance();
        }
        return loginManager;
    }

    void setLoginManager(LoginManager loginManager) {
        this.loginManager = loginManager;
    }
}


File: facebook/src/com/facebook/share/ShareApi.java
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

package com.facebook.share;

import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Bundle;
import android.text.TextUtils;
import android.util.Log;

import com.facebook.AccessToken;
import com.facebook.FacebookCallback;
import com.facebook.FacebookException;
import com.facebook.FacebookGraphResponseException;
import com.facebook.FacebookRequestError;
import com.facebook.GraphRequest;
import com.facebook.GraphResponse;
import com.facebook.HttpMethod;
import com.facebook.internal.CollectionMapper;
import com.facebook.internal.Mutable;
import com.facebook.internal.Utility;
import com.facebook.share.internal.ShareContentValidation;
import com.facebook.share.internal.ShareInternalUtility;
import com.facebook.share.internal.VideoUploader;
import com.facebook.share.model.*;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.FileNotFoundException;
import java.io.UnsupportedEncodingException;
import java.net.URLEncoder;
import java.util.*;

/**
 * Provides an interface for sharing through the graph API. Using this class requires an access
 * token in AccessToken.currentAccessToken that has been granted the "publish_actions" permission.
 */
public final class ShareApi {
    private static final String TAG = "ShareApi";
    private static final String DEFAULT_GRAPH_NODE = "me";
    private static final String PHOTOS_EDGE = "photos";
    private static final String GRAPH_PATH_FORMAT = "%s/%s";
    private static final String DEFAULT_CHARSET = "UTF-8";

    private String message;
    private String graphNode;
    private final ShareContent shareContent;

    /**
     * Convenience method to share a piece of content.
     *
     * @param shareContent the content to share.
     * @param callback     the callback to call once the share is complete.
     */
    public static void share(
            final ShareContent shareContent,
            final FacebookCallback<Sharer.Result> callback) {
        new ShareApi(shareContent)
                .share(callback);
    }

    /**
     * Constructs a new instance.
     *
     * @param shareContent the content to share.
     */
    public ShareApi(final ShareContent shareContent) {
        this.shareContent = shareContent;
        this.graphNode = DEFAULT_GRAPH_NODE;
    }

    /**
     * Returns the message the person has provided through the custom dialog that will accompany the
     * share content.
     * @return the message.
     */
    public String getMessage() {
        return this.message;
    }

    /**
     * Sets the message the person has provided through the custom dialog that will accompany the
     * share content.
     * @param message the message.
     */
    public void setMessage(final String message) {
        this.message = message;
    }

    /**
     * Returns the graph node to share to.
     * @return the graph node.
     */
    public String getGraphNode() {
        return this.graphNode;
    }

    /**
     * Sets the graph node to share to (this can be a user id, event id, page id, group id, album
     * id, etc).
     * @param graphNode the graph node to share to.
     */
    public void setGraphNode(final String graphNode) {
        this.graphNode = graphNode;
    }

    /**
     * Returns the content to be shared.
     *
     * @return the content to be shared.
     */
    public ShareContent getShareContent() {
        return this.shareContent;
    }

    /**
     * Returns true if the content can be shared. Warns if the access token is missing the
     * publish_actions permission. Doesn't fail when this permission is missing, because the app
     * could have been granted that permission in another installation.
     *
     * @return true if the content can be shared.
     */
    public boolean canShare() {
        if (this.getShareContent() == null) {
            return false;
        }
        final AccessToken accessToken = AccessToken.getCurrentAccessToken();
        if (accessToken == null) {
            return false;
        }
        final Set<String> permissions = accessToken.getPermissions();
        if (permissions == null || !permissions.contains("publish_actions")) {
            Log.w(TAG, "The publish_actions permissions are missing, the share will fail unless" +
                    " this app was authorized to publish in another installation.");
        }

        return true;
    }

    /**
     * Share the content.
     *
     * @param callback the callback to call once the share is complete.
     */
    public void share(FacebookCallback<Sharer.Result> callback) {
        if (!this.canShare()) {
            ShareInternalUtility.invokeCallbackWithError(
                    callback, "Insufficient permissions for sharing content via Api.");
            return;
        }
        final ShareContent shareContent = this.getShareContent();

        // Validate the share content
        try {
            ShareContentValidation.validateForApiShare(shareContent);
        } catch (FacebookException ex) {
            ShareInternalUtility.invokeCallbackWithException(callback, ex);
            return;
        }

        if (shareContent instanceof ShareLinkContent) {
            this.shareLinkContent((ShareLinkContent) shareContent, callback);
        } else if (shareContent instanceof SharePhotoContent) {
            this.sharePhotoContent((SharePhotoContent) shareContent, callback);
        } else if (shareContent instanceof ShareVideoContent) {
            this.shareVideoContent((ShareVideoContent) shareContent, callback);
        } else if (shareContent instanceof ShareOpenGraphContent) {
            this.shareOpenGraphContent((ShareOpenGraphContent) shareContent, callback);
        }
    }

    // Get the graph path, pathAfterGraphNode must be properly URL encoded
    private String getGraphPath(final String pathAfterGraphNode) {
        try {
            return String.format(
                    Locale.ROOT, GRAPH_PATH_FORMAT,
                    URLEncoder.encode(getGraphNode(), DEFAULT_CHARSET),
                    pathAfterGraphNode);
        } catch (UnsupportedEncodingException e) {
            return null;
        }
    }

    private void addCommonParameters(final Bundle bundle, ShareContent shareContent) {
        final List<String> peopleIds = shareContent.getPeopleIds();
        if (!Utility.isNullOrEmpty(peopleIds)) {
            bundle.putString("tags", TextUtils.join(", ", peopleIds));
        }

        if (!Utility.isNullOrEmpty(shareContent.getPlaceId())) {
            bundle.putString("place", shareContent.getPlaceId());
        }

        if (!Utility.isNullOrEmpty(shareContent.getRef())) {
            bundle.putString("ref", shareContent.getRef());
        }
    }

    private void shareOpenGraphContent(final ShareOpenGraphContent openGraphContent,
                                       final FacebookCallback<Sharer.Result> callback) {
        // In order to create a new Open Graph action using a custom object that does not already
        // exist (objectID or URL), you must first send a request to post the object and then
        // another to post the action.  If a local image is supplied with the object or action, that
        // must be staged first and then referenced by the staging URL that is returned by that
        // request.
        final GraphRequest.Callback requestCallback = new GraphRequest.Callback() {
            @Override
            public void onCompleted(GraphResponse response) {
                final JSONObject data = response.getJSONObject();
                final String postId = (data == null ? null : data.optString("id"));
                ShareInternalUtility.invokeCallbackWithResults(callback, postId, response);
            }
        };
        final ShareOpenGraphAction action = openGraphContent.getAction();
        final Bundle parameters = action.getBundle();
        this.addCommonParameters(parameters, openGraphContent);
        if (!Utility.isNullOrEmpty(this.getMessage())) {
            parameters.putString("message", this.getMessage());
        }

        final CollectionMapper.OnMapperCompleteListener stageCallback = new CollectionMapper
                .OnMapperCompleteListener() {
            @Override
            public void onComplete() {
                try {
                    handleImagesOnAction(parameters);

                    new GraphRequest(
                            AccessToken.getCurrentAccessToken(),
                            getGraphPath(
                                    URLEncoder.encode(action.getActionType(), DEFAULT_CHARSET)),
                            parameters,
                            HttpMethod.POST,
                            requestCallback).executeAsync();
                } catch (final UnsupportedEncodingException ex) {
                    ShareInternalUtility.invokeCallbackWithException(callback, ex);
                }
            }

            @Override
            public void onError(FacebookException exception) {
                ShareInternalUtility.invokeCallbackWithException(callback, exception);
            }
        };
        this.stageOpenGraphAction(parameters, stageCallback);
    }

    private static void handleImagesOnAction(Bundle parameters) {
        // In general, graph objects are passed by reference (ID/URL). But if this is an OG Action,
        // we need to pass the entire values of the contents of the 'image' property, as they
        // contain important metadata beyond just a URL.
        String imageStr = parameters.getString("image");
        if (imageStr != null) {
            try {
                // Check to see if this is an json array. Will throw if not
                JSONArray images = new JSONArray(imageStr);
                for (int i = 0; i < images.length(); ++i) {
                    JSONObject jsonImage = images.optJSONObject(i);
                    if(jsonImage != null) {
                        putImageInBundleWithArrayFormat(parameters, i, jsonImage);
                    } else {
                        // If we don't have jsonImage we probably just have a url
                        String url = images.getString(i);
                        parameters.putString(String.format(Locale.ROOT, "image[%d][url]", i), url);
                    }
                }
                parameters.remove("image");
                return;
            } catch (JSONException ex) {
                // We couldn't parse the string as an array
            }

            // If the image is not in an array it might just be an single photo
            try {
                JSONObject image = new JSONObject(imageStr);
                putImageInBundleWithArrayFormat(parameters, 0, image);
                parameters.remove("image");
            } catch (JSONException exception) {
                // The image was not in array format or a json object and can be safely passed
                // without modification
            }
        }
    }

    private static void putImageInBundleWithArrayFormat(
            Bundle parameters,
            int index,
            JSONObject image) throws JSONException{
        Iterator<String> keys = image.keys();
        while (keys.hasNext()) {
            String property = keys.next();
            String key = String.format(Locale.ROOT, "image[%d][%s]", index, property);
            parameters.putString(key, image.get(property).toString());
        }
    }

    private void sharePhotoContent(final SharePhotoContent photoContent,
                                   final FacebookCallback<Sharer.Result> callback) {
        final Mutable<Integer> requestCount = new Mutable<Integer>(0);
        final AccessToken accessToken = AccessToken.getCurrentAccessToken();
        final ArrayList<GraphRequest> requests = new ArrayList<GraphRequest>();
        final ArrayList<JSONObject> results = new ArrayList<JSONObject>();
        final ArrayList<GraphResponse> errorResponses = new ArrayList<GraphResponse>();
        final GraphRequest.Callback requestCallback = new GraphRequest.Callback() {
            @Override
            public void onCompleted(GraphResponse response) {
                final JSONObject result = response.getJSONObject();
                if (result != null) {
                    results.add(result);
                }
                if (response.getError() != null) {
                    errorResponses.add(response);
                }
                requestCount.value -= 1;
                if (requestCount.value == 0) {
                    if (!errorResponses.isEmpty()) {
                        ShareInternalUtility.invokeCallbackWithResults(
                                callback,
                                null,
                                errorResponses.get(0));
                    } else if (!results.isEmpty()) {
                        final String postId = results.get(0).optString("id");
                        ShareInternalUtility.invokeCallbackWithResults(
                                callback,
                                postId,
                                response);
                    }
                }
            }
        };
        try {
            for (SharePhoto photo : photoContent.getPhotos()) {
                final Bitmap bitmap = photo.getBitmap();
                final Uri photoUri = photo.getImageUrl();
                String caption = photo.getCaption();
                if (caption == null) {
                    caption = this.getMessage();
                }
                if (bitmap != null) {
                    requests.add(ShareInternalUtility.newUploadPhotoRequest(
                            getGraphPath(PHOTOS_EDGE),
                            accessToken,
                            bitmap,
                            caption,
                            photo.getParameters(),
                            requestCallback));
                } else if (photoUri != null) {
                    requests.add(ShareInternalUtility.newUploadPhotoRequest(
                            getGraphPath(PHOTOS_EDGE),
                            accessToken,
                            photoUri,
                            caption,
                            photo.getParameters(),
                            requestCallback));
                }
            }
            requestCount.value += requests.size();
            for (GraphRequest request : requests) {
                request.executeAsync();
            }
        } catch (final FileNotFoundException ex) {
            ShareInternalUtility.invokeCallbackWithException(callback, ex);
        }
    }

    private void shareLinkContent(final ShareLinkContent linkContent,
                                  final FacebookCallback<Sharer.Result> callback) {
        final GraphRequest.Callback requestCallback = new GraphRequest.Callback() {
            @Override
            public void onCompleted(GraphResponse response) {
                final JSONObject data = response.getJSONObject();
                final String postId = (data == null ? null : data.optString("id"));
                ShareInternalUtility.invokeCallbackWithResults(callback, postId, response);
            }
        };
        final Bundle parameters = new Bundle();
        this.addCommonParameters(parameters, linkContent);
        parameters.putString("message", this.getMessage());
        parameters.putString("link", Utility.getUriString(linkContent.getContentUrl()));
        parameters.putString("picture", Utility.getUriString(linkContent.getImageUrl()));
        parameters.putString("name", linkContent.getContentTitle());
        parameters.putString("description", linkContent.getContentDescription());
        parameters.putString("ref", linkContent.getRef());
        new GraphRequest(
                AccessToken.getCurrentAccessToken(),
                getGraphPath("feed"),
                parameters,
                HttpMethod.POST,
                requestCallback).executeAsync();
    }

    private void shareVideoContent(final ShareVideoContent videoContent,
                                   final FacebookCallback<Sharer.Result> callback) {
        try {
            VideoUploader.uploadAsync(videoContent, getGraphNode(), callback);
        } catch (final FileNotFoundException ex) {
            ShareInternalUtility.invokeCallbackWithException(callback, ex);
        }
    }

    private void stageArrayList(final ArrayList arrayList,
                                       final CollectionMapper.OnMapValueCompleteListener
                                               onArrayListStagedListener) {
        final JSONArray stagedObject = new JSONArray();
        final CollectionMapper.Collection<Integer> collection = new CollectionMapper
                .Collection<Integer>() {
            @Override
            public Iterator<Integer> keyIterator() {
                final int size = arrayList.size();
                final Mutable<Integer> current = new Mutable<Integer>(0);
                return new Iterator<Integer>() {
                    @Override
                    public boolean hasNext() {
                        return current.value < size;
                    }

                    @Override
                    public Integer next() {
                        return current.value++;
                    }

                    @Override
                    public void remove() {
                    }
                };
            }

            @Override
            public Object get(Integer key) {
                return arrayList.get(key);
            }

            @Override
            public void set(Integer key,
                            Object value,
                            CollectionMapper.OnErrorListener onErrorListener) {
                try {
                    stagedObject.put(key, value);
                } catch (final JSONException ex) {
                    String message = ex.getLocalizedMessage();
                    if (message == null) {
                        message = "Error staging object.";
                    }
                    onErrorListener.onError(new FacebookException(message));
                }
            }
        };
        final CollectionMapper.OnMapperCompleteListener onStagedArrayMapperCompleteListener =
                new CollectionMapper.OnMapperCompleteListener() {
                    @Override
                    public void onComplete() {
                        onArrayListStagedListener.onComplete(stagedObject);
                    }

                    @Override
                    public void onError(FacebookException exception) {
                        onArrayListStagedListener.onError(exception);
                    }
                };
        stageCollectionValues(collection, onStagedArrayMapperCompleteListener);
    }

    private <T> void stageCollectionValues(final CollectionMapper.Collection<T> collection,
                                                  final CollectionMapper.OnMapperCompleteListener
                                                          onCollectionValuesStagedListener) {
        final CollectionMapper.ValueMapper valueMapper = new CollectionMapper.ValueMapper() {
            @Override
            public void mapValue(Object value,
                                 CollectionMapper.OnMapValueCompleteListener
                                         onMapValueCompleteListener) {
                if (value instanceof ArrayList) {
                    stageArrayList((ArrayList) value, onMapValueCompleteListener);
                } else if (value instanceof ShareOpenGraphObject) {
                    stageOpenGraphObject(
                            (ShareOpenGraphObject) value,
                            onMapValueCompleteListener);
                } else if (value instanceof SharePhoto) {
                    stagePhoto((SharePhoto) value, onMapValueCompleteListener);
                } else {
                    onMapValueCompleteListener.onComplete(value);
                }
            }
        };
        CollectionMapper.iterate(collection, valueMapper, onCollectionValuesStagedListener);
    }

    private void stageOpenGraphAction(final Bundle parameters,
                                             final CollectionMapper.OnMapperCompleteListener
                                                     onOpenGraphActionStagedListener) {
        final CollectionMapper.Collection<String> collection = new CollectionMapper
                .Collection<String>() {
            @Override
            public Iterator<String> keyIterator() {
                return parameters.keySet().iterator();
            }

            @Override
            public Object get(String key) {
                return parameters.get(key);
            }

            @Override
            public void set(String key,
                            Object value,
                            CollectionMapper.OnErrorListener onErrorListener) {
                if (!Utility.putJSONValueInBundle(parameters, key, value)) {
                    onErrorListener.onError(
                            new FacebookException("Unexpected value: " + value.toString()));
                }
            }
        };
        stageCollectionValues(collection, onOpenGraphActionStagedListener);
    }

    private void stageOpenGraphObject(final ShareOpenGraphObject object,
                                             final CollectionMapper.OnMapValueCompleteListener
                                                     onOpenGraphObjectStagedListener) {
        String type = object.getString("type");
        if (type == null) {
            type = object.getString("og:type");
        }

        if (type == null) {
            onOpenGraphObjectStagedListener.onError(
                    new FacebookException("Open Graph objects must contain a type value."));
            return;
        }
        final JSONObject stagedObject = new JSONObject();
        final CollectionMapper.Collection<String> collection = new CollectionMapper
                .Collection<String>() {
            @Override
            public Iterator<String> keyIterator() {
                return object.keySet().iterator();
            }

            @Override
            public Object get(String key) {
                return object.get(key);
            }

            @Override
            public void set(String key,
                            Object value,
                            CollectionMapper.OnErrorListener onErrorListener) {
                try {
                    stagedObject.put(key, value);
                } catch (final JSONException ex) {
                    String message = ex.getLocalizedMessage();
                    if (message == null) {
                        message = "Error staging object.";
                    }
                    onErrorListener.onError(new FacebookException(message));
                }
            }
        };
        final GraphRequest.Callback requestCallback = new GraphRequest.Callback() {
            @Override
            public void onCompleted(GraphResponse response) {
                final FacebookRequestError error = response.getError();
                if (error != null) {
                    String message = error.getErrorMessage();
                    if (message == null) {
                        message = "Error staging Open Graph object.";
                    }
                    onOpenGraphObjectStagedListener.onError(
                            new FacebookGraphResponseException(response, message));
                    return;
                }
                final JSONObject data = response.getJSONObject();
                if (data == null) {
                    onOpenGraphObjectStagedListener.onError(
                            new FacebookGraphResponseException(response,
                                    "Error staging Open Graph object."));
                    return;
                }
                final String stagedObjectId = data.optString("id");
                if (stagedObjectId == null) {
                    onOpenGraphObjectStagedListener.onError(
                            new FacebookGraphResponseException(response,
                                    "Error staging Open Graph object."));
                    return;
                }
                onOpenGraphObjectStagedListener.onComplete(stagedObjectId);
            }
        };
        final String ogType = type;
        final CollectionMapper.OnMapperCompleteListener onMapperCompleteListener =
                new CollectionMapper.OnMapperCompleteListener() {
                    @Override
                    public void onComplete() {
                        final String objectString = stagedObject.toString();
                        final Bundle parameters = new Bundle();
                        parameters.putString("object", objectString);
                        try {
                            new GraphRequest(
                                    AccessToken.getCurrentAccessToken(),
                                    getGraphPath(
                                            "objects/" +
                                                    URLEncoder.encode(ogType, DEFAULT_CHARSET)),
                                    parameters,
                                    HttpMethod.POST,
                                    requestCallback).executeAsync();
                        } catch (final UnsupportedEncodingException ex) {
                            String message = ex.getLocalizedMessage();
                            if (message == null) {
                                message = "Error staging Open Graph object.";
                            }
                            onOpenGraphObjectStagedListener.onError(new FacebookException(message));
                        }
                    }

                    @Override
                    public void onError(FacebookException exception) {
                        onOpenGraphObjectStagedListener.onError(exception);
                    }
                };
        stageCollectionValues(collection, onMapperCompleteListener);
    }

    private void stagePhoto(final SharePhoto photo,
                                   final CollectionMapper.OnMapValueCompleteListener
                                           onPhotoStagedListener) {
        final Bitmap bitmap = photo.getBitmap();
        final Uri imageUrl = photo.getImageUrl();
        if ((bitmap != null) || (imageUrl != null)) {
            final GraphRequest.Callback requestCallback = new GraphRequest.Callback() {
                @Override
                public void onCompleted(GraphResponse response) {
                    final FacebookRequestError error = response.getError();
                    if (error != null) {
                        String message = error.getErrorMessage();
                        if (message == null) {
                            message = "Error staging photo.";
                        }
                        onPhotoStagedListener.onError(
                                new FacebookGraphResponseException(response, message));
                        return;
                    }
                    final JSONObject data = response.getJSONObject();
                    if (data == null) {
                        onPhotoStagedListener.onError(
                                new FacebookException("Error staging photo."));
                        return;
                    }
                    final String stagedImageUri = data.optString("uri");
                    if (stagedImageUri == null) {
                        onPhotoStagedListener.onError(
                                new FacebookException("Error staging photo."));
                        return;
                    }

                    final JSONObject stagedObject = new JSONObject();
                    try {
                        stagedObject.put("url", stagedImageUri);
                        stagedObject.put("user_generated", photo.getUserGenerated());
                    } catch (final JSONException ex) {
                        String message = ex.getLocalizedMessage();
                        if (message == null) {
                            message = "Error staging photo.";
                        }
                        onPhotoStagedListener.onError(new FacebookException(message));
                        return;
                    }
                    onPhotoStagedListener.onComplete(stagedObject);
                }
            };
            if (bitmap != null) {
                ShareInternalUtility.newUploadStagingResourceWithImageRequest(
                        AccessToken.getCurrentAccessToken(),
                        bitmap,
                        requestCallback).executeAsync();
            } else {
                try {
                    ShareInternalUtility.newUploadStagingResourceWithImageRequest(
                            AccessToken.getCurrentAccessToken(),
                            imageUrl,
                            requestCallback).executeAsync();
                } catch (final FileNotFoundException ex) {
                    String message = ex.getLocalizedMessage();
                    if (message == null) {
                        message = "Error staging photo.";
                    }
                    onPhotoStagedListener.onError(new FacebookException(message));
                }
            }
        } else {
            onPhotoStagedListener.onError(
                    new FacebookException("Photos must have an imageURL or bitmap."));
        }
    }
}


File: facebook/src/com/facebook/share/internal/ShareConstants.java
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

/**
 * com.facebook.share.internal is solely for the use of other packages within the
 * Facebook SDK for Android. Use of any of the classes in this package is
 * unsupported, and they may be modified or removed without warning at any time.
 */
public class ShareConstants {

    public static final int MIN_API_VERSION_FOR_WEB_FALLBACK_DIALOGS = 14;

    public static final String WEB_DIALOG_PARAM_DATA = "data";
    public static final String WEB_DIALOG_PARAM_MESSAGE = "message";
    public static final String WEB_DIALOG_PARAM_TO = "to";
    public static final String WEB_DIALOG_PARAM_TITLE = "title";
    public static final String WEB_DIALOG_PARAM_ACTION_TYPE = "action_type";
    public static final String WEB_DIALOG_PARAM_OBJECT_ID = "object_id";
    public static final String WEB_DIALOG_PARAM_FILTERS = "filters";
    public static final String WEB_DIALOG_PARAM_SUGGESTIONS = "suggestions";

    public static final String WEB_DIALOG_PARAM_HREF = "href";
    public static final String WEB_DIALOG_PARAM_ACTION_PROPERTIES = "action_properties";

    public static final String WEB_DIALOG_PARAM_LINK = "link";
    public static final String WEB_DIALOG_PARAM_PICTURE = "picture";
    public static final String WEB_DIALOG_PARAM_NAME = "name";
    public static final String WEB_DIALOG_PARAM_DESCRIPTION = "description";

    public static final String WEB_DIALOG_PARAM_ID = "id";

    public static final String WEB_DIALOG_PARAM_PRIVACY = "privacy";

    public static final String WEB_DIALOG_RESULT_PARAM_POST_ID = "post_id";
    public static final String WEB_DIALOG_RESULT_PARAM_REQUEST_ID = "request";
    public static final String WEB_DIALOG_RESULT_PARAM_TO_ARRAY_MEMBER = "to[%d]";

    // Extras supported for ACTION_FEED_DIALOG:
    public static final String LEGACY_PLACE_TAG = "com.facebook.platform.extra.PLACE";
    public static final String LEGACY_FRIEND_TAGS = "com.facebook.platform.extra.FRIENDS";
    public static final String LEGACY_LINK = "com.facebook.platform.extra.LINK";
    public static final String LEGACY_IMAGE = "com.facebook.platform.extra.IMAGE";
    public static final String LEGACY_TITLE = "com.facebook.platform.extra.TITLE";
    public static final String LEGACY_DESCRIPTION = "com.facebook.platform.extra.DESCRIPTION";
    public static final String LEGACY_REF = "com.facebook.platform.extra.REF";
    public static final String LEGACY_DATA_FAILURES_FATAL =
            "com.facebook.platform.extra.DATA_FAILURES_FATAL";
    public static final String LEGACY_PHOTOS = "com.facebook.platform.extra.PHOTOS";

    public static final String PLACE_ID = "PLACE";
    public static final String PEOPLE_IDS = "FRIENDS";
    public static final String CONTENT_URL = "LINK";
    public static final String IMAGE_URL = "IMAGE";
    public static final String TITLE = "TITLE";
    public static final String DESCRIPTION = "DESCRIPTION";
    public static final String REF = "REF";
    public static final String DATA_FAILURES_FATAL = "DATA_FAILURES_FATAL";
    public static final String PHOTOS = "PHOTOS";
    public static final String VIDEO_URL = "VIDEO";

    // Extras supported for ACTION_OGACTIONPUBLISH_DIALOG:
    public static final String LEGACY_ACTION = "com.facebook.platform.extra.ACTION";
    public static final String LEGACY_ACTION_TYPE = "com.facebook.platform.extra.ACTION_TYPE";
    public static final String LEGACY_PREVIEW_PROPERTY_NAME =
            "com.facebook.platform.extra.PREVIEW_PROPERTY_NAME";

    public static final String ACTION = "ACTION";
    public static final String ACTION_TYPE = "ACTION_TYPE";
    public static final String PREVIEW_PROPERTY_NAME = "PREVIEW_PROPERTY_NAME";

    // Method args supported for ACTION_LIKE_DIALOG
    public static final String OBJECT_ID = "object_id";
    public static final String OBJECT_TYPE = "object_type";

    // Method args supported for ACTION_APPINVITE_DIALOG
    public static final String APPLINK_URL = "app_link_url";
    public static final String PREVIEW_IMAGE_URL = "preview_image_url";

    // Extras supported for MESSAGE_GET_LIKE_STATUS_REQUEST:
    public static final String EXTRA_OBJECT_ID = "com.facebook.platform.extra.OBJECT_ID";

    // Extras supported in MESSAGE_GET_LIKE_STATUS_REPLY:
    public static final String EXTRA_OBJECT_IS_LIKED =
            "com.facebook.platform.extra.OBJECT_IS_LIKED";
    public static final String EXTRA_LIKE_COUNT_STRING_WITH_LIKE =
            "com.facebook.platform.extra.LIKE_COUNT_STRING_WITH_LIKE";
    public static final String EXTRA_LIKE_COUNT_STRING_WITHOUT_LIKE =
            "com.facebook.platform.extra.LIKE_COUNT_STRING_WITHOUT_LIKE";
    public static final String EXTRA_SOCIAL_SENTENCE_WITH_LIKE =
            "com.facebook.platform.extra.SOCIAL_SENTENCE_WITH_LIKE";
    public static final String EXTRA_SOCIAL_SENTENCE_WITHOUT_LIKE =
            "com.facebook.platform.extra.SOCIAL_SENTENCE_WITHOUT_LIKE";
    public static final String EXTRA_UNLIKE_TOKEN = "com.facebook.platform.extra.UNLIKE_TOKEN";

    // Result keys from Native sharing dialogs
    public static final String EXTRA_RESULT_POST_ID = "com.facebook.platform.extra.POST_ID";
    public static final String RESULT_POST_ID = "postId";

    public static final int MAXIMUM_PHOTO_COUNT = 6;
    static final String MY_VIDEOS = "me/videos";
}


File: facebook/src/com/facebook/share/internal/ShareInternalUtility.java
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

import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import android.support.annotation.Nullable;
import android.text.TextUtils;
import android.util.Pair;

import com.facebook.AccessToken;
import com.facebook.CallbackManager;
import com.facebook.FacebookCallback;
import com.facebook.FacebookException;
import com.facebook.FacebookGraphResponseException;
import com.facebook.FacebookOperationCanceledException;
import com.facebook.FacebookRequestError;
import com.facebook.FacebookSdk;
import com.facebook.GraphRequest;
import com.facebook.GraphRequest.Callback;
import com.facebook.GraphResponse;
import com.facebook.internal.GraphUtil;
import com.facebook.HttpMethod;
import com.facebook.appevents.AppEventsLogger;
import com.facebook.internal.AnalyticsEvents;
import com.facebook.internal.AppCall;
import com.facebook.internal.CallbackManagerImpl;
import com.facebook.internal.NativeAppCallAttachmentStore;
import com.facebook.internal.NativeProtocol;
import com.facebook.internal.Utility;
import com.facebook.share.Sharer;
import com.facebook.share.model.ShareOpenGraphAction;
import com.facebook.share.model.ShareOpenGraphContent;
import com.facebook.share.model.SharePhoto;
import com.facebook.share.model.SharePhotoContent;
import com.facebook.share.model.ShareVideoContent;
import com.facebook.share.widget.LikeView;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileNotFoundException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * com.facebook.share.internal is solely for the use of other packages within the
 * Facebook SDK for Android. Use of any of the classes in this package is
 * unsupported, and they may be modified or removed without warning at any time.
 */
public final class ShareInternalUtility {
    private static final String OBJECT_PARAM = "object";
    public static final String MY_PHOTOS = "me/photos";
    private static final String MY_FEED = "me/feed";
    private static final String MY_STAGING_RESOURCES = "me/staging_resources";
    private static final String MY_OBJECTS_FORMAT = "me/objects/%s";
    private static final String MY_ACTION_FORMAT = "me/%s";

    // Parameter names/values
    private static final String PICTURE_PARAM = "picture";
    private static final String CAPTION_PARAM = "caption";
    private static final String STAGING_PARAM = "file";

    public static void invokeCallbackWithException(
            FacebookCallback<Sharer.Result> callback,
            final Exception exception) {
        if (exception instanceof FacebookException) {
            invokeOnErrorCallback(callback, (FacebookException) exception);
            return;
        }
        invokeCallbackWithError(
                callback,
                "Error preparing share content: " + exception.getLocalizedMessage());
    }

    public static void invokeCallbackWithError(
            FacebookCallback<Sharer.Result> callback,
            String error) {
        invokeOnErrorCallback(callback, error);
    }

    public static void invokeCallbackWithResults(
            FacebookCallback<Sharer.Result> callback,
            final String postId,
            final GraphResponse graphResponse) {
        FacebookRequestError requestError = graphResponse.getError();
        if (requestError != null) {
            String errorMessage = requestError.getErrorMessage();
            if (Utility.isNullOrEmpty(errorMessage)) {
                errorMessage = "Unexpected error sharing.";
            }
            invokeOnErrorCallback(callback, graphResponse, errorMessage);
        } else {
            invokeOnSuccessCallback(callback, postId);
        }
    }

    /**
     * Determines whether the native dialog completed normally (without error or exception).
     *
     * @param result the bundle passed back to onActivityResult
     * @return true if the native dialog completed normally
     */
    public static boolean getNativeDialogDidComplete(Bundle result) {
        if (result.containsKey(NativeProtocol.RESULT_ARGS_DIALOG_COMPLETE_KEY)) {
            return result.getBoolean(NativeProtocol.RESULT_ARGS_DIALOG_COMPLETE_KEY);
        }
        return result.getBoolean(NativeProtocol.EXTRA_DIALOG_COMPLETE_KEY, false);
    }

    /**
     * Returns the gesture with which the user completed the native dialog. This is only returned
     * if the user has previously authorized the calling app with basic permissions.
     *
     * @param result the bundle passed back to onActivityResult
     * @return "post" or "cancel" as the completion gesture
     */
    public static String getNativeDialogCompletionGesture(Bundle result) {
        if (result.containsKey(NativeProtocol.RESULT_ARGS_DIALOG_COMPLETION_GESTURE_KEY)) {
            return result.getString(NativeProtocol.RESULT_ARGS_DIALOG_COMPLETION_GESTURE_KEY);
        }
        return result.getString(NativeProtocol.EXTRA_DIALOG_COMPLETION_GESTURE_KEY);
    }

    /**
     * Returns the id of the published post. This is only returned if the user has previously
     * given the app publish permissions.
     *
     * @param result the bundle passed back to onActivityResult
     * @return the id of the published post
     */
    public static String getShareDialogPostId(Bundle result) {
        if (result.containsKey(ShareConstants.RESULT_POST_ID)) {
            return result.getString(ShareConstants.RESULT_POST_ID);
        }
        if (result.containsKey(ShareConstants.EXTRA_RESULT_POST_ID)) {
            return result.getString(ShareConstants.EXTRA_RESULT_POST_ID);
        }
        return result.getString(ShareConstants.WEB_DIALOG_RESULT_PARAM_POST_ID);
    }

    public static boolean handleActivityResult(
            int requestCode,
            int resultCode,
            Intent data,
            ResultProcessor resultProcessor) {
        AppCall appCall = getAppCallFromActivityResult(requestCode, resultCode, data);
        if (appCall == null) {
            return false;
        }

        NativeAppCallAttachmentStore.cleanupAttachmentsForCall(appCall.getCallId());
        if (resultProcessor == null) {
            return true;
        }

        FacebookException exception = NativeProtocol.getExceptionFromErrorData(
                NativeProtocol.getErrorDataFromResultIntent(data));
        if (exception != null) {
            if (exception instanceof FacebookOperationCanceledException) {
                resultProcessor.onCancel(appCall);
            } else {
                resultProcessor.onError(appCall, exception);
            }
        } else {
            // If here, we did not find an error in the result.
            Bundle results = NativeProtocol.getSuccessResultsFromIntent(data);
            resultProcessor.onSuccess(appCall, results);
        }

        return true;
    }

    // Custom handling for Share so that we can log results
    public static ResultProcessor getShareResultProcessor(
            final FacebookCallback<Sharer.Result> callback) {
        return new ResultProcessor(callback) {
            @Override
            public void onSuccess(AppCall appCall, Bundle results) {
                if (results != null) {
                    final String gesture = getNativeDialogCompletionGesture(results);
                    if (gesture == null || "post".equalsIgnoreCase(gesture)) {
                        String postId = getShareDialogPostId(results);
                        invokeOnSuccessCallback(callback, postId);
                    } else if ("cancel".equalsIgnoreCase(gesture)) {
                        invokeOnCancelCallback(callback);
                    } else {
                        invokeOnErrorCallback(
                                callback,
                                new FacebookException(NativeProtocol.ERROR_UNKNOWN_ERROR));
                    }
                }
            }

            @Override
            public void onCancel(AppCall appCall) {
                invokeOnCancelCallback(callback);
            }

            @Override
            public void onError(AppCall appCall, FacebookException error) {
                invokeOnErrorCallback(callback, error);
            }
        };
    }

    private static AppCall getAppCallFromActivityResult(int requestCode,
                                                        int resultCode,
                                                        Intent data) {
        UUID callId = NativeProtocol.getCallIdFromIntent(data);
        if (callId == null) {
            return null;
        }

        return AppCall.finishPendingCall(callId, requestCode);
    }

    public static void registerStaticShareCallback(
            final int requestCode) {
        CallbackManagerImpl.registerStaticCallback(
                requestCode,
                new CallbackManagerImpl.Callback() {
                    @Override
                    public boolean onActivityResult(int resultCode, Intent data) {
                        return handleActivityResult(
                                requestCode,
                                resultCode,
                                data,
                                getShareResultProcessor(null));
                    }
                }
        );
    }

    public static void registerSharerCallback(
            final int requestCode,
            final CallbackManager callbackManager,
            final FacebookCallback<Sharer.Result> callback) {
        if (!(callbackManager instanceof CallbackManagerImpl)) {
            throw new FacebookException("Unexpected CallbackManager, " +
                    "please use the provided Factory.");
        }

        ((CallbackManagerImpl) callbackManager).registerCallback(
                requestCode,
                new CallbackManagerImpl.Callback() {
                    @Override
                    public boolean onActivityResult(int resultCode, Intent data) {
                        return handleActivityResult(
                                requestCode,
                                resultCode,
                                data,
                                getShareResultProcessor(callback));
                    }
                });
    }

    public static List<String> getPhotoUrls(
            final SharePhotoContent photoContent,
            final UUID appCallId) {
        List<SharePhoto> photos;
        if (photoContent == null || (photos = photoContent.getPhotos()) == null) {
            return null;
        }

        List<NativeAppCallAttachmentStore.Attachment> attachments = Utility.map(
                photos,
                new Utility.Mapper<SharePhoto, NativeAppCallAttachmentStore.Attachment>() {
                    @Override
                    public NativeAppCallAttachmentStore.Attachment apply(SharePhoto item) {
                        return getAttachment(appCallId, item);
                    }
                });

        List<String> attachmentUrls = Utility.map(
                attachments,
                new Utility.Mapper<NativeAppCallAttachmentStore.Attachment, String>() {
                    @Override
                    public String apply(NativeAppCallAttachmentStore.Attachment item) {
                        return item.getAttachmentUrl();
                    }
                });

        NativeAppCallAttachmentStore.addAttachments(attachments);

        return attachmentUrls;
    }

    public static String getVideoUrl(final ShareVideoContent videoContent, final UUID appCallId) {
        if (videoContent == null || videoContent.getVideo() == null) {
            return null;
        }

        NativeAppCallAttachmentStore.Attachment attachment =
                NativeAppCallAttachmentStore.createAttachment(
                        appCallId,
                        videoContent.getVideo().getLocalUrl());

        ArrayList<NativeAppCallAttachmentStore.Attachment> attachments = new ArrayList<>(1);
        attachments.add(attachment);
        NativeAppCallAttachmentStore.addAttachments(attachments);

        return attachment.getAttachmentUrl();
    }

    public static JSONObject toJSONObjectForCall(
            final UUID callId,
            final ShareOpenGraphContent content)
            throws JSONException {
        final ShareOpenGraphAction action = content.getAction();
        final ArrayList<NativeAppCallAttachmentStore.Attachment> attachments = new ArrayList<>();
        JSONObject actionJSON = OpenGraphJSONUtility.toJSONObject(
                action,
                new OpenGraphJSONUtility.PhotoJSONProcessor() {
                    @Override
                    public JSONObject toJSONObject(SharePhoto photo) {
                        NativeAppCallAttachmentStore.Attachment attachment = getAttachment(
                                callId,
                                photo);

                        if (attachment == null) {
                            return null;
                        }

                        attachments.add(attachment);

                        JSONObject photoJSONObject = new JSONObject();
                        try {
                            photoJSONObject.put(
                                    NativeProtocol.IMAGE_URL_KEY, attachment.getAttachmentUrl());
                            if (photo.getUserGenerated()) {
                                photoJSONObject.put(NativeProtocol.IMAGE_USER_GENERATED_KEY, true);
                            }
                        } catch (JSONException e) {
                            throw new FacebookException("Unable to attach images", e);
                        }
                        return photoJSONObject;
                    }
                });

        NativeAppCallAttachmentStore.addAttachments(attachments);
        // People and place tags must be moved from the share content to the open graph action
        if (content.getPlaceId() != null) {
            String placeTag = actionJSON.optString("place");

            // Only if the place tag is already empty or null replace with the id from the
            // share content
            if (Utility.isNullOrEmpty(placeTag)) {
                actionJSON.put("place", content.getPlaceId());
            }
        }

        if (content.getPeopleIds() != null) {
            JSONArray peopleTags = actionJSON.optJSONArray("tags");
            Set<String> peopleIdSet = peopleTags == null
                    ? new HashSet<String>()
                    : Utility.jsonArrayToSet(peopleTags);

            for (String peopleId : content.getPeopleIds()) {
                peopleIdSet.add(peopleId);
            }
            actionJSON.put("tags", new ArrayList<>(peopleIdSet));
        }

        return actionJSON;
    }

    public static JSONObject toJSONObjectForWeb(
            final ShareOpenGraphContent shareOpenGraphContent)
            throws JSONException {
        ShareOpenGraphAction action = shareOpenGraphContent.getAction();

        return OpenGraphJSONUtility.toJSONObject(
                action,
                new OpenGraphJSONUtility.PhotoJSONProcessor() {
                    @Override
                    public JSONObject toJSONObject(SharePhoto photo) {
                        Uri photoUri = photo.getImageUrl();
                        JSONObject photoJSONObject = new JSONObject();
                        try {
                            photoJSONObject.put(
                                    NativeProtocol.IMAGE_URL_KEY, photoUri.toString());
                        } catch (JSONException e) {
                            throw new FacebookException("Unable to attach images", e);
                        }
                        return photoJSONObject;
                    }
                });
    }

    public static JSONArray removeNamespacesFromOGJsonArray(
            JSONArray jsonArray,
            boolean requireNamespace) throws JSONException {
        JSONArray newArray = new JSONArray();
        for (int i = 0; i < jsonArray.length(); ++i) {
            Object value = jsonArray.get(i);
            if (value instanceof JSONArray) {
                value = removeNamespacesFromOGJsonArray((JSONArray) value, requireNamespace);
            } else if (value instanceof JSONObject) {
                value = removeNamespacesFromOGJsonObject((JSONObject) value, requireNamespace);
            }
            newArray.put(value);
        }

        return newArray;
    }

    public static JSONObject removeNamespacesFromOGJsonObject(
            JSONObject jsonObject,
            boolean requireNamespace) {
        if (jsonObject == null) {
            return null;
        }

        try {
            JSONObject newJsonObject = new JSONObject();
            JSONObject data = new JSONObject();
            JSONArray names = jsonObject.names();
            for (int i = 0; i < names.length(); ++i) {
                String key = names.getString(i);
                Object value = null;
                value = jsonObject.get(key);
                if (value instanceof JSONObject) {
                    value = removeNamespacesFromOGJsonObject((JSONObject) value, true);
                } else if (value instanceof JSONArray) {
                    value = removeNamespacesFromOGJsonArray((JSONArray) value, true);
                }

                Pair<String, String> fieldNameAndNamespace = getFieldNameAndNamespaceFromFullName(
                        key);
                String namespace = fieldNameAndNamespace.first;
                String fieldName = fieldNameAndNamespace.second;

                if (requireNamespace) {
                    if (namespace != null && namespace.equals("fbsdk")) {
                        newJsonObject.put(key, value);
                    } else if (namespace == null || namespace.equals("og")) {
                        newJsonObject.put(fieldName, value);
                    } else {
                        data.put(fieldName, value);
                    }
                } else if (namespace != null && namespace.equals("fb")) {
                    newJsonObject.put(key, value);
                } else {
                    newJsonObject.put(fieldName, value);
                }
            }

            if (data.length() > 0) {
                newJsonObject.put("data", data);
            }

            return newJsonObject;
        } catch (JSONException e) {
            throw new FacebookException("Failed to create json object from share content");
        }
    }

    public static Pair<String, String> getFieldNameAndNamespaceFromFullName(String fullName) {
        String namespace = null;
        String fieldName;
        int index = fullName.indexOf(':');
        if (index != -1 && fullName.length() > index + 1) {
            namespace = fullName.substring(0, index);
            fieldName = fullName.substring(index + 1);
        } else {
            fieldName = fullName;
        }
        return new Pair<>(namespace, fieldName);
    }

    ;

    private ShareInternalUtility() {
    }

    private static NativeAppCallAttachmentStore.Attachment getAttachment(
            UUID callId,
            SharePhoto photo) {
        Bitmap bitmap = photo.getBitmap();
        Uri photoUri = photo.getImageUrl();
        NativeAppCallAttachmentStore.Attachment attachment = null;
        if (bitmap != null) {
            attachment = NativeAppCallAttachmentStore.createAttachment(
                    callId,
                    bitmap);
        } else if (photoUri != null) {
            attachment = NativeAppCallAttachmentStore.createAttachment(
                    callId,
                    photoUri);
        }

        return attachment;
    }

    static void invokeOnCancelCallback(FacebookCallback<Sharer.Result> callback) {
        logShareResult(AnalyticsEvents.PARAMETER_SHARE_OUTCOME_CANCELLED, null);
        if (callback != null) {
            callback.onCancel();
        }
    }

    static void invokeOnSuccessCallback(
            FacebookCallback<Sharer.Result> callback,
            String postId) {
        logShareResult(AnalyticsEvents.PARAMETER_SHARE_OUTCOME_SUCCEEDED, null);
        if (callback != null) {
            callback.onSuccess(new Sharer.Result(postId));
        }
    }

    static void invokeOnErrorCallback(
            FacebookCallback<Sharer.Result> callback,
            GraphResponse response,
            String message) {
        logShareResult(AnalyticsEvents.PARAMETER_SHARE_OUTCOME_ERROR, message);
        if (callback != null) {
            callback.onError(new FacebookGraphResponseException(response, message));
        }
    }


    static void invokeOnErrorCallback(
            FacebookCallback<Sharer.Result> callback,
            String message) {
        logShareResult(AnalyticsEvents.PARAMETER_SHARE_OUTCOME_ERROR, message);
        if (callback != null) {
            callback.onError(new FacebookException(message));
        }
    }

    static void invokeOnErrorCallback(
            FacebookCallback<Sharer.Result> callback,
            FacebookException ex) {
        logShareResult(AnalyticsEvents.PARAMETER_SHARE_OUTCOME_ERROR, ex.getMessage());
        if (callback != null) {
            callback.onError(ex);
        }
    }

    private static void logShareResult(String shareOutcome, String errorMessage) {
        Context context = FacebookSdk.getApplicationContext();
        AppEventsLogger logger = AppEventsLogger.newLogger(context);
        Bundle parameters = new Bundle();
        parameters.putString(
                AnalyticsEvents.PARAMETER_SHARE_OUTCOME,
                shareOutcome
        );

        if (errorMessage != null) {
            parameters.putString(AnalyticsEvents.PARAMETER_SHARE_ERROR_MESSAGE, errorMessage);
        }
        logger.logSdkEvent(AnalyticsEvents.EVENT_SHARE_RESULT, null, parameters);
    }

    /**
     * Creates a new Request configured to create a user owned Open Graph object.
     *
     * @param accessToken     the accessToken to use, or null
     * @param openGraphObject the Open Graph object to create; must not be null, and must have a
     *                        non-empty type and title
     * @param callback        a callback that will be called when the request is completed to handle
     *                        success or error conditions
     * @return a Request that is ready to execute
     */
    public static GraphRequest newPostOpenGraphObjectRequest(
            AccessToken accessToken,
            JSONObject openGraphObject,
            Callback callback) {
        if (openGraphObject == null) {
            throw new FacebookException("openGraphObject cannot be null");
        }
        if (Utility.isNullOrEmpty(openGraphObject.optString("type"))) {
            throw new FacebookException("openGraphObject must have non-null 'type' property");
        }
        if (Utility.isNullOrEmpty(openGraphObject.optString("title"))) {
            throw new FacebookException("openGraphObject must have non-null 'title' property");
        }

        String path = String.format(MY_OBJECTS_FORMAT, openGraphObject.optString("type"));
        Bundle bundle = new Bundle();
        bundle.putString(OBJECT_PARAM, openGraphObject.toString());
        return new GraphRequest(accessToken, path, bundle, HttpMethod.POST, callback);
    }

    /**
     * Creates a new Request configured to create a user owned Open Graph object.
     *
     * @param accessToken      the access token to use, or null
     * @param type             the fully-specified Open Graph object type (e.g.,
     *                         my_app_namespace:my_object_name); must not be null
     * @param title            the title of the Open Graph object; must not be null
     * @param imageUrl         the link to an image to be associated with the Open Graph object; may
     *                         be null
     * @param url              the url to be associated with the Open Graph object; may be null
     * @param description      the description to be associated with the object; may be null
     * @param objectProperties any additional type-specific properties for the Open Graph object;
     *                         may be null
     * @param callback         a callback that will be called when the request is completed to
     *                         handle success or error conditions; may be null
     * @return a Request that is ready to execute
     */
    public static GraphRequest newPostOpenGraphObjectRequest(
            AccessToken accessToken,
            String type,
            String title,
            String imageUrl,
            String url,
            String description,
            JSONObject objectProperties,
            Callback callback) {
        JSONObject openGraphObject = GraphUtil.createOpenGraphObjectForPost(
                type, title, imageUrl, url, description, objectProperties, null);
        return newPostOpenGraphObjectRequest(accessToken, openGraphObject, callback);
    }

    /**
     * Creates a new Request configured to publish an Open Graph action.
     *
     * @param accessToken     the access token to use, or null
     * @param openGraphAction the Open Graph action to create; must not be null, and must have a
     *                        non-empty 'type'
     * @param callback        a callback that will be called when the request is completed to handle
     *                        success or error conditions
     * @return a Request that is ready to execute
     */
    public static GraphRequest newPostOpenGraphActionRequest(
            AccessToken accessToken,
            JSONObject openGraphAction,
            Callback callback) {
        if (openGraphAction == null) {
            throw new FacebookException("openGraphAction cannot be null");
        }
        String type = openGraphAction.optString("type");
        if (Utility.isNullOrEmpty(type)) {
            throw new FacebookException("openGraphAction must have non-null 'type' property");
        }

        String path = String.format(MY_ACTION_FORMAT, type);
        return GraphRequest.newPostRequest(accessToken, path, openGraphAction, callback);
    }

    /**
     * Creates a new Request configured to update a user owned Open Graph object.
     *
     * @param accessToken     the access token to use, or null
     * @param openGraphObject the Open Graph object to update, which must have a valid 'id'
     *                        property
     * @param callback        a callback that will be called when the request is completed to handle
     *                        success or error conditions
     * @return a Request that is ready to execute
     */
    public static GraphRequest newUpdateOpenGraphObjectRequest(
            AccessToken accessToken,
            JSONObject openGraphObject,
            Callback callback) {
        if (openGraphObject == null) {
            throw new FacebookException("openGraphObject cannot be null");
        }

        String path = openGraphObject.optString("id");
        if (path == null) {
            throw new FacebookException("openGraphObject must have an id");
        }

        Bundle bundle = new Bundle();
        bundle.putString(OBJECT_PARAM, openGraphObject.toString());
        return new GraphRequest(accessToken, path, bundle, HttpMethod.POST, callback);
    }

    /**
     * Creates a new Request configured to update a user owned Open Graph object.
     *
     * @param accessToken      the access token to use, or null
     * @param id               the id of the Open Graph object
     * @param title            the title of the Open Graph object
     * @param imageUrl         the link to an image to be associated with the Open Graph object
     * @param url              the url to be associated with the Open Graph object
     * @param description      the description to be associated with the object
     * @param objectProperties any additional type-specific properties for the Open Graph object
     * @param callback         a callback that will be called when the request is completed to
     *                         handle success or error conditions
     * @return a Request that is ready to execute
     */
    public static GraphRequest newUpdateOpenGraphObjectRequest(
            AccessToken accessToken,
            String id,
            String title,
            String imageUrl,
            String url,
            String description,
            JSONObject objectProperties,
            Callback callback) {
        JSONObject openGraphObject = GraphUtil.createOpenGraphObjectForPost(
                null, title, imageUrl, url, description, objectProperties, id);
        return newUpdateOpenGraphObjectRequest(accessToken, openGraphObject, callback);
    }

    /**
     * Creates a new Request configured to upload a photo to the specified graph path.
     *
     * @param graphPath   the graph path to use
     * @param accessToken the access token to use, or null
     * @param image       the image to upload
     * @param caption     the user generated caption for the photo.
     * @param params      the parameters
     * @param callback    a callback that will be called when the request is completed to handle
     *                    success or error conditions
     * @return a Request that is ready to execute
     */
    public static GraphRequest newUploadPhotoRequest(
            String graphPath,
            AccessToken accessToken,
            Bitmap image,
            String caption,
            Bundle params,
            Callback callback) {
        Bundle parameters = new Bundle();
        if (params != null) {
            parameters.putAll(params);
        }
        parameters.putParcelable(PICTURE_PARAM, image);
        if (caption != null && !caption.isEmpty()) {
            parameters.putString(CAPTION_PARAM, caption);
        }

        return new GraphRequest(accessToken, graphPath, parameters, HttpMethod.POST, callback);
    }

    /**
     * Creates a new Request configured to upload a photo to the specified graph path. The
     * photo will be read from the specified file.
     *
     * @param graphPath   the graph path to use
     * @param accessToken the access token to use, or null
     * @param file        the file containing the photo to upload
     * @param caption     the user generated caption for the photo.
     * @param params      the parameters
     * @param callback    a callback that will be called when the request is completed to handle
     *                    success or error conditions
     * @return a Request that is ready to execute
     * @throws java.io.FileNotFoundException
     */
    public static GraphRequest newUploadPhotoRequest(
            String graphPath,
            AccessToken accessToken,
            File file,
            String caption,
            Bundle params,
            Callback callback
    ) throws FileNotFoundException {
        ParcelFileDescriptor descriptor =
                ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY);
        Bundle parameters = new Bundle();
        if (params != null) {
            parameters.putAll(params);
        }
        parameters.putParcelable(PICTURE_PARAM, descriptor);
        if (caption != null && !caption.isEmpty()) {
            parameters.putString(CAPTION_PARAM, caption);
        }

        return new GraphRequest(accessToken, graphPath, parameters, HttpMethod.POST, callback);
    }

    /**
     * Creates a new Request configured to upload a photo to the specified graph path. The
     * photo will be read from the specified Uri.
     *
     * @param graphPath   the graph path to use
     * @param accessToken the access token to use, or null
     * @param photoUri    the file:// or content:// Uri to the photo on device.
     * @param caption     the user generated caption for the photo.
     * @param params      the parameters
     * @param callback    a callback that will be called when the request is completed to handle
     *                    success or error conditions
     * @return a Request that is ready to execute
     * @throws FileNotFoundException
     */
    public static GraphRequest newUploadPhotoRequest(
            String graphPath,
            AccessToken accessToken,
            Uri photoUri,
            String caption,
            Bundle params,
            Callback callback)
            throws FileNotFoundException {
        if (Utility.isFileUri(photoUri)) {
            return newUploadPhotoRequest(
                    graphPath,
                    accessToken,
                    new File(photoUri.getPath()),
                    caption,
                    params,
                    callback);
        } else if (!Utility.isContentUri(photoUri)) {
            throw new FacebookException("The photo Uri must be either a file:// or content:// Uri");
        }

        Bundle parameters = new Bundle();
        if (params != null) {
            parameters.putAll(params);
        }
        parameters.putParcelable(PICTURE_PARAM, photoUri);

        return new GraphRequest(accessToken, graphPath, parameters, HttpMethod.POST, callback);
    }

    /**
     * Creates a new Request configured to post a status update to a user's feed.
     *
     * @param accessToken the access token to use, or null
     * @param message     the text of the status update
     * @param callback    a callback that will be called when the request is completed to handle
     *                    success or error conditions
     * @return a Request that is ready to execute
     */
    public static GraphRequest newStatusUpdateRequest(
            AccessToken accessToken,
            String message,
            Callback callback) {
        return newStatusUpdateRequest(accessToken, message, (String) null, null, callback);
    }

    /**
     * Creates a new Request configured to post a status update to a user's feed.
     *
     * @param accessToken the access token to use, or null
     * @param message     the text of the status update
     * @param placeId     an optional place id to associate with the post
     * @param tagIds      an optional list of user ids to tag in the post
     * @param callback    a callback that will be called when the request is completed to handle
     *                    success or error conditions
     * @return a Request that is ready to execute
     */
    private static GraphRequest newStatusUpdateRequest(
            AccessToken accessToken,
            String message,
            String placeId,
            List<String> tagIds,
            Callback callback) {

        Bundle parameters = new Bundle();
        parameters.putString("message", message);

        if (placeId != null) {
            parameters.putString("place", placeId);
        }

        if (tagIds != null && tagIds.size() > 0) {
            String tags = TextUtils.join(",", tagIds);
            parameters.putString("tags", tags);
        }

        return new GraphRequest(accessToken, MY_FEED, parameters, HttpMethod.POST, callback);
    }

    /**
     * Creates a new Request configured to post a status update to a user's feed.
     *
     * @param accessToken the access token to use, or null
     * @param message     the text of the status update
     * @param place       an optional place to associate with the post
     * @param tags        an optional list of users to tag in the post
     * @param callback    a callback that will be called when the request is completed to handle
     *                    success or error conditions
     * @return a Request that is ready to execute
     */
    public static GraphRequest newStatusUpdateRequest(
            AccessToken accessToken,
            String message,
            JSONObject place,
            List<JSONObject> tags,
            Callback callback) {

        List<String> tagIds = null;
        if (tags != null) {
            tagIds = new ArrayList<String>(tags.size());
            for (JSONObject tag : tags) {
                tagIds.add(tag.optString("id"));
            }
        }
        String placeId = place == null ? null : place.optString("id");
        return newStatusUpdateRequest(accessToken, message, placeId, tagIds, callback);
    }


    /**
     * Creates a new Request configured to upload an image to create a staging resource. Staging
     * resources allow you to post binary data such as images, in preparation for a post of an Open
     * Graph object or action which references the image. The URI returned when uploading a staging
     * resource may be passed as the image property for an Open Graph object or action.
     *
     * @param accessToken the access token to use, or null
     * @param image       the image to upload
     * @param callback    a callback that will be called when the request is completed to handle
     *                    success or error conditions
     * @return a Request that is ready to execute
     */
    public static GraphRequest newUploadStagingResourceWithImageRequest(
            AccessToken accessToken,
            Bitmap image,
            Callback callback) {
        Bundle parameters = new Bundle(1);
        parameters.putParcelable(STAGING_PARAM, image);

        return new GraphRequest(
                accessToken,
                MY_STAGING_RESOURCES,
                parameters,
                HttpMethod.POST,
                callback);
    }

    /**
     * Creates a new Request configured to upload an image to create a staging resource. Staging
     * resources allow you to post binary data such as images, in preparation for a post of an Open
     * Graph object or action which references the image. The URI returned when uploading a staging
     * resource may be passed as the image property for an Open Graph object or action.
     *
     * @param accessToken the access token to use, or null
     * @param file        the file containing the image to upload
     * @param callback    a callback that will be called when the request is completed to handle
     *                    success or error conditions
     * @return a Request that is ready to execute
     * @throws FileNotFoundException
     */
    public static GraphRequest newUploadStagingResourceWithImageRequest(
            AccessToken accessToken,
            File file,
            Callback callback
    ) throws FileNotFoundException {
        ParcelFileDescriptor descriptor =
                ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY);
        GraphRequest.ParcelableResourceWithMimeType<ParcelFileDescriptor> resourceWithMimeType =
                new GraphRequest.ParcelableResourceWithMimeType<>(descriptor, "image/png");
        Bundle parameters = new Bundle(1);
        parameters.putParcelable(STAGING_PARAM, resourceWithMimeType);

        return new GraphRequest(
                accessToken,
                MY_STAGING_RESOURCES,
                parameters,
                HttpMethod.POST,
                callback);
    }

    /**
     * Creates a new Request configured to upload an image to create a staging resource. Staging
     * resources allow you to post binary data such as images, in preparation for a post of an Open
     * Graph object or action which references the image. The URI returned when uploading a staging
     * resource may be passed as the image property for an Open Graph object or action.
     *
     * @param accessToken the access token to use, or null
     * @param imageUri    the file:// or content:// Uri pointing to the image to upload
     * @param callback    a callback that will be called when the request is completed to handle
     *                    success or error conditions
     * @return a Request that is ready to execute
     * @throws FileNotFoundException
     */
    public static GraphRequest newUploadStagingResourceWithImageRequest(
            AccessToken accessToken,
            Uri imageUri,
            Callback callback
    ) throws FileNotFoundException {
        if (Utility.isFileUri(imageUri)) {
            return newUploadStagingResourceWithImageRequest(
                    accessToken,
                    new File(imageUri.getPath()),
                    callback);
        } else if (!Utility.isContentUri(imageUri)) {
            throw new FacebookException("The image Uri must be either a file:// or content:// Uri");
        }

        GraphRequest.ParcelableResourceWithMimeType<Uri> resourceWithMimeType =
                new GraphRequest.ParcelableResourceWithMimeType<>(imageUri, "image/png");
        Bundle parameters = new Bundle(1);
        parameters.putParcelable(STAGING_PARAM, resourceWithMimeType);

        return new GraphRequest(
                accessToken,
                MY_STAGING_RESOURCES,
                parameters,
                HttpMethod.POST,
                callback);
    }

    @Nullable
    public static LikeView.ObjectType getMostSpecificObjectType(
            LikeView.ObjectType objectType1,
            LikeView.ObjectType objectType2) {
        if (objectType1 == objectType2) {
            return objectType1;
        }

        if (objectType1 == LikeView.ObjectType.UNKNOWN) {
            return objectType2;
        } else if (objectType2 == LikeView.ObjectType.UNKNOWN) {
            return objectType1;
        } else {
            // We can't have a PAGE and an OPEN_GRAPH type be compatible.
            return null;
        }
    }
}


File: facebook/src/com/facebook/share/internal/WebDialogParameters.java
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

import android.os.Bundle;

import com.facebook.FacebookException;
import com.facebook.internal.Utility;
import com.facebook.share.model.AppGroupCreationContent;
import com.facebook.share.model.GameRequestContent;
import com.facebook.share.model.ShareLinkContent;
import com.facebook.share.model.ShareOpenGraphContent;

import org.json.JSONException;
import org.json.JSONObject;

import java.util.Locale;

/**
 * com.facebook.share.internal is solely for the use of other packages within the
 * Facebook SDK for Android. Use of any of the classes in this package is
 * unsupported, and they may be modified or removed without warning at any time.
 */
public class WebDialogParameters {

    public static Bundle create(AppGroupCreationContent appGroupCreationContent) {
        Bundle webParams = new Bundle();

        Utility.putNonEmptyString(
                webParams,
                ShareConstants.WEB_DIALOG_PARAM_NAME,
                appGroupCreationContent.getName());

        Utility.putNonEmptyString(
                webParams,
                ShareConstants.WEB_DIALOG_PARAM_DESCRIPTION,
                appGroupCreationContent.getDescription());

        Utility.putNonEmptyString(
                webParams,
                ShareConstants.WEB_DIALOG_PARAM_PRIVACY,
                appGroupCreationContent
                        .getAppGroupPrivacy().toString().toLowerCase(Locale.ENGLISH));

        return webParams;
    }

    public static Bundle create(GameRequestContent gameRequestContent) {
        Bundle webParams = new Bundle();

        Utility.putNonEmptyString(
                webParams,
                ShareConstants.WEB_DIALOG_PARAM_MESSAGE,
                gameRequestContent.getMessage());
        Utility.putNonEmptyString(
                webParams,
                ShareConstants.WEB_DIALOG_PARAM_TO,
                gameRequestContent.getTo());
        Utility.putNonEmptyString(
                webParams,
                ShareConstants.WEB_DIALOG_PARAM_TITLE,
                gameRequestContent.getTitle());
        Utility.putNonEmptyString(
                webParams,
                ShareConstants.WEB_DIALOG_PARAM_DATA,
                gameRequestContent.getData());
        if (gameRequestContent.getActionType() != null) {
            Utility.putNonEmptyString(
                    webParams,
                    ShareConstants.WEB_DIALOG_PARAM_ACTION_TYPE,
                    gameRequestContent.getActionType().toString().toLowerCase(Locale.ENGLISH));
        }
        Utility.putNonEmptyString(
                webParams,
                ShareConstants.WEB_DIALOG_PARAM_OBJECT_ID,
                gameRequestContent.getObjectId());
        if (gameRequestContent.getFilters() != null) {
            Utility.putNonEmptyString(
                    webParams,
                    ShareConstants.WEB_DIALOG_PARAM_FILTERS,
                    gameRequestContent.getFilters().toString().toLowerCase(Locale.ENGLISH));
        }
        Utility.putCommaSeparatedStringList(
                webParams,
                ShareConstants.WEB_DIALOG_PARAM_SUGGESTIONS,
                gameRequestContent.getSuggestions());
        return webParams;
    }

    public static Bundle create(ShareLinkContent shareLinkContent) {
        Bundle params = new Bundle();
        Utility.putUri(
                params,
                ShareConstants.WEB_DIALOG_PARAM_HREF,
                shareLinkContent.getContentUrl());

        return params;
    }

    public static Bundle create(ShareOpenGraphContent shareOpenGraphContent) {
        Bundle params = new Bundle();

        Utility.putNonEmptyString(
                params,
                ShareConstants.WEB_DIALOG_PARAM_ACTION_TYPE,
                shareOpenGraphContent.getAction().getActionType());

        try {
            JSONObject ogJSON = ShareInternalUtility.toJSONObjectForWeb(shareOpenGraphContent);
            ogJSON = ShareInternalUtility.removeNamespacesFromOGJsonObject(ogJSON, false);
            if (ogJSON != null) {
                Utility.putNonEmptyString(
                        params,
                        ShareConstants.WEB_DIALOG_PARAM_ACTION_PROPERTIES,
                        ogJSON.toString());
            }
        } catch (JSONException e) {
            throw new FacebookException("Unable to serialize the ShareOpenGraphContent to JSON", e);
        }

        return params;
    }

    public static Bundle createForFeed(ShareLinkContent shareLinkContent) {
        Bundle webParams = new Bundle();

        Utility.putNonEmptyString(
                webParams,
                ShareConstants.WEB_DIALOG_PARAM_NAME,
                shareLinkContent.getContentTitle());

        Utility.putNonEmptyString(
                webParams,
                ShareConstants.WEB_DIALOG_PARAM_DESCRIPTION,
                shareLinkContent.getContentDescription());

        Utility.putNonEmptyString(
                webParams,
                ShareConstants.WEB_DIALOG_PARAM_LINK,
                Utility.getUriString(shareLinkContent.getContentUrl()));

        Utility.putNonEmptyString(
                webParams,
                ShareConstants.WEB_DIALOG_PARAM_PICTURE,
                Utility.getUriString(shareLinkContent.getImageUrl()));

        return webParams;
    }
}


File: facebook/src/com/facebook/share/model/ShareContent.java
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

import android.net.Uri;
import android.os.Parcel;
import android.support.annotation.Nullable;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Provides the base class for content to be shared. Contains all common methods for
 * the different types of content.
 */
public abstract class ShareContent<P extends ShareContent, E extends ShareContent.Builder>
        implements ShareModel {
    private final Uri contentUrl;
    private final List<String> peopleIds;
    private final String placeId;
    private final String ref;

    protected ShareContent(final Builder builder) {
        super();
        this.contentUrl = builder.contentUrl;
        this.peopleIds = builder.peopleIds;
        this.placeId = builder.placeId;
        this.ref = builder.ref;
    }

    ShareContent(final Parcel in) {
        this.contentUrl = in.readParcelable(Uri.class.getClassLoader());
        this.peopleIds = readUnmodifiableStringList(in);
        this.placeId = in.readString();
        this.ref = in.readString();
    }

    /**
     * URL for the content being shared.  This URL will be checked for app link meta tags for
     * linking in platform specific ways.
     * <p/>
     * See documentation for <a href="https://developers.facebook.com/docs/applinks/">App Links</a>.
     *
     * @return {@link android.net.Uri} representation of the content link.
     */
    @Nullable
    public Uri getContentUrl() {
        return this.contentUrl;
    }

    /**
     * List of Ids for taggable people to tag with this content.
     * <p/>
     * See documentation for
     * <a href="https://developers.facebook.com/docs/graph-api/reference/user/taggable_friends">
     * Taggable Friends</a>.
     *
     * @return {@link java.util.List} of Ids for people to tag.
     */
    @Nullable
    public List<String> getPeopleIds() {
        return this.peopleIds;
    }

    /**
     * The Id for a place to tag with this content.
     *
     * @return The Id for the place to tag.
     */
    @Nullable
    public String getPlaceId() {
        return this.placeId;
    }

    /**
     * A value to be added to the referrer URL when a person follows a link from this shared
     * content on feed.
     *
     * @return The ref for the content.
     */
    @Nullable
    public String getRef() {
        return this.ref;
    }

    public int describeContents() {
        return 0;
    }

    public void writeToParcel(final Parcel out, final int flags) {
        out.writeParcelable(this.contentUrl, 0);
        out.writeStringList(this.peopleIds);
        out.writeString(this.placeId);
        out.writeString(this.ref);
    }

    private List<String> readUnmodifiableStringList(final Parcel in) {
        final List<String> list = new ArrayList<String>();
        in.readStringList(list);
        return (list.size() == 0 ? null : Collections.unmodifiableList(list));
    }

    /**
     * Abstract builder for {@link com.facebook.share.model.ShareContent}
     */
    public abstract static class Builder<P extends ShareContent, E extends Builder>
            implements ShareModelBuilder<P, E> {
        private Uri contentUrl;
        private List<String> peopleIds;
        private String placeId;
        private String ref;

        /**
         * Set the URL for the content being shared.
         *
         * @param contentUrl {@link android.net.Uri} representation of the content link.
         * @return The builder.
         */
        public E setContentUrl(@Nullable final Uri contentUrl) {
            this.contentUrl = contentUrl;
            return (E) this;
        }

        /**
         * Set the list of Ids for taggable people to tag with this content.
         *
         * @param peopleIds {@link java.util.List} of Ids for people to tag.
         * @return The builder.
         */
        public E setPeopleIds(@Nullable final List<String> peopleIds) {
            this.peopleIds = (peopleIds == null ? null : Collections.unmodifiableList(peopleIds));
            return (E) this;
        }

        /**
         * Set the Id for a place to tag with this content.
         *
         * @param placeId The Id for the place to tag.
         * @return The builder.
         */
        public E setPlaceId(@Nullable final String placeId) {
            this.placeId = placeId;
            return (E) this;
        }

        /**
         * Set the value to be added to the referrer URL when a person follows a link from this
         * shared content on feed.
         *
         * @param ref The ref for the content.
         * @return The builder.
         */
        public E setRef(@Nullable final String ref) {
            this.ref = ref;
            return (E) this;
        }

        @Override
        public E readFrom(final P content) {
            if (content == null) {
                return (E) this;
            }
            return (E) this
                    .setContentUrl(content.getContentUrl())
                    .setPeopleIds(content.getPeopleIds())
                    .setPlaceId(content.getPlaceId())
                    .setRef(content.getRef());
        }
    }
}


File: facebook/src/com/facebook/share/widget/ShareDialog.java
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

package com.facebook.share.widget;

import android.app.Activity;
import android.content.Context;
import android.net.Uri;
import android.os.Bundle;
import android.support.v4.app.Fragment;

import com.facebook.FacebookCallback;
import com.facebook.FacebookException;
import com.facebook.appevents.AppEventsLogger;
import com.facebook.internal.AnalyticsEvents;
import com.facebook.internal.AppCall;
import com.facebook.internal.CallbackManagerImpl;
import com.facebook.internal.DialogFeature;
import com.facebook.internal.DialogPresenter;
import com.facebook.internal.FacebookDialogBase;
import com.facebook.internal.Utility;
import com.facebook.share.Sharer;
import com.facebook.share.internal.LegacyNativeDialogParameters;
import com.facebook.share.internal.NativeDialogParameters;
import com.facebook.share.internal.OpenGraphActionDialogFeature;
import com.facebook.share.internal.ShareContentValidation;
import com.facebook.share.internal.ShareDialogFeature;
import com.facebook.share.internal.ShareInternalUtility;
import com.facebook.share.internal.WebDialogParameters;
import com.facebook.share.model.*;

import java.util.ArrayList;
import java.util.List;

/**
 * Provides functionality to share content via the Facebook Share Dialog
 */
public final class ShareDialog
        extends FacebookDialogBase<ShareContent, Sharer.Result>
        implements Sharer {

    /**
     * The mode for the share dialog.
     */
    public enum Mode {
        /**
         * The mode is determined automatically.
         */
        AUTOMATIC,
        /**
         * The native dialog is used.
         */
        NATIVE,
        /**
         * The web dialog is used.
         */
        WEB,
        /**
         * The feed dialog is used.
         */
        FEED
    }

    private static final String FEED_DIALOG = "feed";
    private static final String WEB_SHARE_DIALOG = "share";
    private static final String WEB_OG_SHARE_DIALOG = "share_open_graph";

    private static final int DEFAULT_REQUEST_CODE =
            CallbackManagerImpl.RequestCodeOffset.Share.toRequestCode();

    private  boolean shouldFailOnDataError = false;
    // Keep track of Mode overrides for logging purposes.
    private boolean isAutomaticMode = true;

    /**
     * Helper to show the provided {@link com.facebook.share.model.ShareContent} using the provided
     * Activity. No callback will be invoked.
     *
     * @param activity Activity to use to share the provided content
     * @param shareContent Content to share
     */
    public static void show(
            final Activity activity,
            final ShareContent shareContent) {
        new ShareDialog(activity).show(shareContent);
    }

    /**
     * Helper to show the provided {@link com.facebook.share.model.ShareContent} using the provided
     * Fragment. No callback will be invoked.
     *
     * @param fragment Fragment to use to share the provided content
     * @param shareContent Content to share
     */
    public static void show(
            final Fragment fragment,
            final ShareContent shareContent) {
        new ShareDialog(fragment).show(shareContent);
    }

    /**
     * Indicates whether it is possible to show the dialog for
     * {@link com.facebook.share.model.ShareContent} of the specified type.
     *
     * @param contentType Class of the intended {@link com.facebook.share.model.ShareContent} to
     *                    share.
     * @return True if the specified content type can be shown via the dialog
     */
    public static boolean canShow(Class<? extends ShareContent> contentType) {
        return canShowWebTypeCheck(contentType) || canShowNative(contentType);
    }

    private static boolean canShowNative(Class<? extends ShareContent> contentType) {
        DialogFeature feature = getFeature(contentType);

        return feature != null && DialogPresenter.canPresentNativeDialogWithFeature(feature);
    }

    private static boolean canShowWebTypeCheck(Class<? extends ShareContent> contentType) {
        // If we don't have an instance of a ShareContent, then all we can do is check whether
        // this is a ShareLinkContent, which can be shared if configured properly.
        // The instance method version of this check is more accurate and should be used on
        // ShareDialog instances.

        return ShareLinkContent.class.isAssignableFrom(contentType)
                || ShareOpenGraphContent.class.isAssignableFrom(contentType);
    }

    /**
     * Constructs a new ShareDialog.
     * @param activity Activity to use to share the provided content.
     */
    public ShareDialog(Activity activity) {
        super(activity, DEFAULT_REQUEST_CODE);

        ShareInternalUtility.registerStaticShareCallback(DEFAULT_REQUEST_CODE);
    }

    /**
     * Constructs a new ShareDialog.
     * @param fragment Fragment to use to share the provided content.
     */
    public ShareDialog(Fragment fragment) {
        super(fragment, DEFAULT_REQUEST_CODE);

        ShareInternalUtility.registerStaticShareCallback(DEFAULT_REQUEST_CODE);
    }

    // for ShareDialog use only
    ShareDialog(Activity activity, int requestCode) {
        super(activity, requestCode);

        ShareInternalUtility.registerStaticShareCallback(requestCode);
    }

    // for ShareDialog use only
    ShareDialog(Fragment fragment, int requestCode) {
        super(fragment, requestCode);

        ShareInternalUtility.registerStaticShareCallback(requestCode);
    }

    @Override
    protected void registerCallbackImpl(
            final CallbackManagerImpl callbackManager,
            final FacebookCallback<Result> callback) {
        ShareInternalUtility.registerSharerCallback(
                getRequestCode(), callbackManager, callback);
    }

    @Override
    public boolean getShouldFailOnDataError() {
        return this.shouldFailOnDataError;
    }

    @Override
    public void setShouldFailOnDataError(boolean shouldFailOnDataError) {
        this.shouldFailOnDataError = shouldFailOnDataError;
    }

    /**
     * Call this to check if the Share Dialog can be shown in a specific mode.
     *
     * @param mode Mode of the Share Dialog
     * @return True if the dialog can be shown in the passed in Mode
     */
    public boolean canShow(ShareContent content, Mode mode) {
        return canShowImpl(content, (mode == Mode.AUTOMATIC) ? BASE_AUTOMATIC_MODE : mode);
    }

    /**
     * Call this to show the Share Dialog in a specific mode
     * @param mode Mode of the Share Dialog
     */
    public void show(ShareContent content, Mode mode) {
        isAutomaticMode = (mode == Mode.AUTOMATIC);

        showImpl(content, isAutomaticMode ? BASE_AUTOMATIC_MODE : mode);
    }

    @Override
    protected AppCall createBaseAppCall() {
        return new AppCall(getRequestCode());
    }

    @Override
    protected List<ModeHandler> getOrderedModeHandlers() {
        ArrayList<ModeHandler> handlers = new ArrayList<>();
        handlers.add(new NativeHandler());
        handlers.add(new FeedHandler()); // Feed takes precedence for link-shares for Mode.AUTOMATIC
        handlers.add(new WebShareHandler());

        return handlers;
    }

    private class NativeHandler extends ModeHandler {
        @Override
        public Object getMode() {
            return Mode.NATIVE;
        }

        @Override
        public boolean canShow(final ShareContent content) {
            return content != null && ShareDialog.canShowNative(content.getClass());
        }

        @Override
        public AppCall createAppCall(final ShareContent content) {
            logDialogShare(getActivityContext(), content, Mode.NATIVE);

            ShareContentValidation.validateForNativeShare(content);

            final AppCall appCall = createBaseAppCall();
            final boolean shouldFailOnDataError = getShouldFailOnDataError();

            DialogPresenter.setupAppCallForNativeDialog(
                    appCall,
                    new DialogPresenter.ParameterProvider() {
                        @Override
                        public Bundle getParameters() {
                            return NativeDialogParameters.create(
                                    appCall.getCallId(),
                                    content,
                                    shouldFailOnDataError);
                        }

                        @Override
                        public Bundle getLegacyParameters() {
                            return LegacyNativeDialogParameters.create(
                                    appCall.getCallId(),
                                    content,
                                    shouldFailOnDataError);
                        }
                    },
                    getFeature(content.getClass()));

            return appCall;
        }
    }

    private class WebShareHandler extends ModeHandler {
        @Override
        public Object getMode() {
            return Mode.WEB;
        }

        @Override
        public boolean canShow(final ShareContent content) {
            return (content != null) && ShareDialog.canShowWebTypeCheck(content.getClass());
        }

        @Override
        public AppCall createAppCall(final ShareContent content) {
            logDialogShare(getActivityContext(), content, Mode.WEB);

            final AppCall appCall = createBaseAppCall();

            ShareContentValidation.validateForWebShare(content);

            Bundle params;
            if (content instanceof ShareLinkContent) {
                params = WebDialogParameters.create((ShareLinkContent)content);
            } else {
                params = WebDialogParameters.create((ShareOpenGraphContent)content);
            }

            DialogPresenter.setupAppCallForWebDialog(
                    appCall,
                    getActionName(content),
                    params);

            return appCall;
        }

        private String getActionName(ShareContent shareContent) {
            if (shareContent instanceof ShareLinkContent) {
                return WEB_SHARE_DIALOG;
            } else if (shareContent instanceof ShareOpenGraphContent) {
                return WEB_OG_SHARE_DIALOG;
            }

            return null;
        }
    }

    private class FeedHandler extends ModeHandler {
        @Override
        public Object getMode() {
            return Mode.FEED;
        }

        @Override
        public boolean canShow(final ShareContent content) {
            return (content instanceof ShareLinkContent);
        }

        @Override
        public AppCall createAppCall(final ShareContent content) {
            logDialogShare(getActivityContext(), content, Mode.FEED);

            final ShareLinkContent linkContent = (ShareLinkContent)content;
            final AppCall appCall = createBaseAppCall();

            ShareContentValidation.validateForWebShare(linkContent);

            DialogPresenter.setupAppCallForWebDialog(
                    appCall,
                    FEED_DIALOG,
                    WebDialogParameters.createForFeed(linkContent));

            return appCall;
        }
    }

    private static DialogFeature getFeature(
            Class<? extends ShareContent> contentType) {
        if (ShareLinkContent.class.isAssignableFrom(contentType)) {
            return ShareDialogFeature.SHARE_DIALOG;
        } else if (SharePhotoContent.class.isAssignableFrom(contentType)) {
            return ShareDialogFeature.PHOTOS;
        } else if (ShareVideoContent.class.isAssignableFrom(contentType)) {
            return ShareDialogFeature.VIDEO;
        } else if (ShareOpenGraphContent.class.isAssignableFrom(contentType)) {
            return OpenGraphActionDialogFeature.OG_ACTION_DIALOG;
        }
        return null;
    }

    private void logDialogShare(Context context, ShareContent content, Mode mode) {
        String displayType;
        if (isAutomaticMode) {
            mode = Mode.AUTOMATIC;
        }

        switch (mode) {
            case AUTOMATIC:
                displayType = AnalyticsEvents.PARAMETER_SHARE_DIALOG_SHOW_AUTOMATIC;
                break;
            case WEB:
                displayType = AnalyticsEvents.PARAMETER_SHARE_DIALOG_SHOW_WEB;
                break;
            case NATIVE:
                displayType = AnalyticsEvents.PARAMETER_SHARE_DIALOG_SHOW_NATIVE;
                break;
            default:
                displayType = AnalyticsEvents.PARAMETER_SHARE_DIALOG_SHOW_UNKNOWN;
                break;
        }

        String contentType;
        DialogFeature dialogFeature = getFeature(content.getClass());
        if (dialogFeature == ShareDialogFeature.SHARE_DIALOG) {
            contentType = AnalyticsEvents.PARAMETER_SHARE_DIALOG_CONTENT_STATUS;
        } else if (dialogFeature == ShareDialogFeature.PHOTOS) {
            contentType = AnalyticsEvents.PARAMETER_SHARE_DIALOG_CONTENT_PHOTO;
        } else if (dialogFeature == ShareDialogFeature.VIDEO) {
            contentType = AnalyticsEvents.PARAMETER_SHARE_DIALOG_CONTENT_VIDEO;
        } else if (dialogFeature == OpenGraphActionDialogFeature.OG_ACTION_DIALOG) {
            contentType = AnalyticsEvents.PARAMETER_SHARE_DIALOG_CONTENT_OPENGRAPH;
        } else {
            contentType = AnalyticsEvents.PARAMETER_SHARE_DIALOG_CONTENT_UNKNOWN;
        }

        AppEventsLogger logger = AppEventsLogger.newLogger(context);
        Bundle parameters = new Bundle();
        parameters.putString(
                AnalyticsEvents.PARAMETER_SHARE_DIALOG_SHOW,
                displayType
        );
        parameters.putString(
                AnalyticsEvents.PARAMETER_SHARE_DIALOG_CONTENT_TYPE,
                contentType
        );
        logger.logSdkEvent(AnalyticsEvents.EVENT_SHARE_DIALOG_SHOW, null, parameters);
    }
}


File: facebook/tests/src/com/facebook/AsyncRequestTests.java
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

import android.graphics.Bitmap;
import android.test.suitebuilder.annotation.LargeTest;
import android.test.suitebuilder.annotation.MediumTest;
import android.test.suitebuilder.annotation.SmallTest;

import com.facebook.share.internal.ShareInternalUtility;

import org.json.JSONArray;
import org.json.JSONObject;

import java.net.HttpURLConnection;
import java.util.Arrays;

public class AsyncRequestTests extends FacebookTestCase {

    @SmallTest
    @MediumTest
    @LargeTest
    public void testCanLaunchAsyncRequestFromUiThread() {
        GraphRequest request = GraphRequest.newPostRequest(null, "me/feeds", null, null);
        try {
            TestGraphRequestAsyncTask task = createAsyncTaskOnUiThread(request);
            assertNotNull(task);
        } catch (Throwable throwable) {
            assertNull(throwable);
        }
    }

    @SmallTest
    @MediumTest
    @LargeTest
    public void testExecuteWithNullRequestsThrows() throws Exception {
        try {
            TestGraphRequestAsyncTask task = new TestGraphRequestAsyncTask((GraphRequest[]) null);

            task.executeOnBlockerThread();

            waitAndAssertSuccessOrRethrow(1);

            fail("expected NullPointerException");
        } catch (NullPointerException exception) {
        }
    }

    @SmallTest
    @MediumTest
    @LargeTest
    public void testExecuteBatchWithZeroRequestsThrows() throws Exception {
        try {
            TestGraphRequestAsyncTask task = new TestGraphRequestAsyncTask(new GraphRequest[] {});

            task.executeOnBlockerThread();

            waitAndAssertSuccessOrRethrow(1);

            fail("expected IllegalArgumentException");
        } catch (IllegalArgumentException exception) {
        }
    }

    @SmallTest
    @MediumTest
    @LargeTest
    public void testExecuteBatchWithNullRequestThrows() throws Exception {
        try {
            TestGraphRequestAsyncTask task = new TestGraphRequestAsyncTask(
                    new GraphRequest[] { null });

            task.executeOnBlockerThread();

            waitAndAssertSuccessOrRethrow(1);

            fail("expected NullPointerException");
        } catch (NullPointerException exception) {
        }

    }

    @MediumTest
    @LargeTest
    public void testExecuteSingleGet() {
        final AccessToken accessToken = getAccessTokenForSharedUser();
        GraphRequest request = new GraphRequest(accessToken, "TourEiffel", null, null,
                new ExpectSuccessCallback() {
            @Override
            protected void performAsserts(GraphResponse response) {
                assertNotNull(response);
                JSONObject graphPlace = response.getJSONObject();
                assertEquals("Paris", graphPlace.optJSONObject("location").optString("city"));
            }
        });

        TestGraphRequestAsyncTask task = new TestGraphRequestAsyncTask(request);

        task.executeOnBlockerThread();

        // Wait on 2 signals: request and task will both signal.
        waitAndAssertSuccess(2);
    }

    @MediumTest
    @LargeTest
    public void testExecuteSingleGetUsingHttpURLConnection() {
        final AccessToken accessToken = getAccessTokenForSharedUser();
        GraphRequest request = new GraphRequest(accessToken, "TourEiffel", null, null,
                new ExpectSuccessCallback() {
            @Override
            protected void performAsserts(GraphResponse response) {
                assertNotNull(response);
                JSONObject graphPlace = response.getJSONObject();
                assertEquals("Paris", graphPlace.optJSONObject("location").optString("city"));
            }
        });
        HttpURLConnection connection = GraphRequest.toHttpConnection(request);

        TestGraphRequestAsyncTask task = new TestGraphRequestAsyncTask(connection, Arrays.asList(new GraphRequest[] { request }));

        task.executeOnBlockerThread();

        // Wait on 2 signals: request and task will both signal.
        waitAndAssertSuccess(2);
    }

    @MediumTest
    @LargeTest
    public void testExecuteSingleGetFailureCase() {
        final AccessToken accessToken = getAccessTokenForSharedUser();
        GraphRequest request = new GraphRequest(accessToken, "-1", null, null,
                new ExpectFailureCallback());

        TestGraphRequestAsyncTask task = new TestGraphRequestAsyncTask(request);

        task.executeOnBlockerThread();

        // Wait on 2 signals: request and task will both signal.
        waitAndAssertSuccess(2);
    }

    @SmallTest
    @MediumTest
    @LargeTest
    public void testBatchWithoutAppIDIsError() throws Throwable {
        GraphRequest request1 = new GraphRequest(null, "TourEiffel", null, null, new ExpectFailureCallback());
        GraphRequest request2 = new GraphRequest(null, "SpaceNeedle", null, null, new ExpectFailureCallback());

        TestGraphRequestAsyncTask task = new TestGraphRequestAsyncTask(request1, request2);

        task.executeOnBlockerThread();

        // Wait on 3 signals: request1, request2, and task will all signal.
        waitAndAssertSuccessOrRethrow(3);
    }

    @LargeTest
    public void testMixedSuccessAndFailure() {
        final AccessToken accessToken = getAccessTokenForSharedUser();

        final int NUM_REQUESTS = 8;
        GraphRequest[] requests = new GraphRequest[NUM_REQUESTS];
        for (int i = 0; i < NUM_REQUESTS; ++i) {
            boolean shouldSucceed = (i % 2) == 1;
            if (shouldSucceed) {
                requests[i] = new GraphRequest(accessToken, "me", null, null,
                        new ExpectSuccessCallback());
            } else {
                requests[i] = new GraphRequest(accessToken, "-1", null, null,
                        new ExpectFailureCallback());
            }
        }

        TestGraphRequestAsyncTask task = new TestGraphRequestAsyncTask(requests);

        task.executeOnBlockerThread();

        // Note: plus 1, because the overall async task signals as well.
        waitAndAssertSuccess(NUM_REQUESTS + 1);
    }

    @MediumTest
    @LargeTest
    public void testStaticExecuteMeAsync() {
        final AccessToken accessToken = getAccessTokenForSharedUser();

        class MeCallback extends ExpectSuccessCallback implements GraphRequest.GraphJSONObjectCallback {
            @Override
            public void onCompleted(JSONObject me, GraphResponse response) {
                assertNotNull(me);
                assertEquals(accessToken.getUserId(), me.optString("id"));
                RequestTests.validateMeResponse(accessToken, response);
                onCompleted(response);
            }
        }

        runOnBlockerThread(new Runnable() {
            @Override
            public void run() {
                GraphRequest.newMeRequest(accessToken, new MeCallback()).executeAsync();
            }
        }, false);
        waitAndAssertSuccess(1);
    }

    @MediumTest
    @LargeTest
    public void testStaticExecuteMyFriendsAsync() {
        final AccessToken accessToken = getAccessTokenForSharedUser();

        class FriendsCallback extends ExpectSuccessCallback implements GraphRequest.GraphJSONArrayCallback {
            @Override
            public void onCompleted(JSONArray friends, GraphResponse response) {
                assertNotNull(friends);
                RequestTests.validateMyFriendsResponse(response);
                onCompleted(response);
            }
        }

        runOnBlockerThread(new Runnable() {
            @Override
            public void run() {
                GraphRequest.newMyFriendsRequest(accessToken, new FriendsCallback()).executeAsync();
            }
        }, false);
        waitAndAssertSuccess(1);
    }

    @LargeTest
    public void testBatchUploadPhoto() {
        final AccessToken accessToken = getAccessTokenForSharedUserWithPermissions(null,
                "user_photos", "publish_actions");

        final int image1Size = 120;
        final int image2Size = 150;

        Bitmap bitmap1 = createTestBitmap(image1Size);
        Bitmap bitmap2 = createTestBitmap(image2Size);

        GraphRequest uploadRequest1 = ShareInternalUtility.newUploadPhotoRequest(
                ShareInternalUtility.MY_PHOTOS,
                accessToken,
                bitmap1,
                null,
                null,
                null);
        uploadRequest1.setBatchEntryName("uploadRequest1");
        GraphRequest uploadRequest2 = ShareInternalUtility.newUploadPhotoRequest(
                ShareInternalUtility.MY_PHOTOS,
                accessToken,
                bitmap2,
                null,
                null,
                null);
        uploadRequest2.setBatchEntryName("uploadRequest2");
        GraphRequest getRequest1 = new GraphRequest(
                accessToken,
                "{result=uploadRequest1:$.id}",
                null,
                null,
                new ExpectSuccessCallback() {
                    @Override
                    protected void performAsserts(GraphResponse response) {
                        assertNotNull(response);
                        JSONObject retrievedPhoto = response.getJSONObject();
                        assertNotNull(retrievedPhoto);
                        assertEquals(image1Size, retrievedPhoto.optInt("width"));
                    }
                });
        GraphRequest getRequest2 = new GraphRequest(
                accessToken,
                "{result=uploadRequest2:$.id}",
                null,
                null,
                new ExpectSuccessCallback() {
                    @Override
                    protected void performAsserts(GraphResponse response) {
                        assertNotNull(response);
                        JSONObject retrievedPhoto = response.getJSONObject();
                        assertNotNull(retrievedPhoto);
                        assertEquals(image2Size, retrievedPhoto.optInt("width"));
                    }
                });

        TestGraphRequestAsyncTask task = new TestGraphRequestAsyncTask(
                uploadRequest1,
                uploadRequest2,
                getRequest1,
                getRequest2);
        task.executeOnBlockerThread();

        // Wait on 3 signals: getRequest1, getRequest2, and task will all signal.
        waitAndAssertSuccess(3);
    }

    @MediumTest
    @LargeTest
    public void testShortTimeoutCausesFailure() {
        final AccessToken accessToken = getAccessTokenForSharedUser();

        GraphRequest request = new GraphRequest(accessToken, "me/likes", null, null,
                new ExpectFailureCallback());

        GraphRequestBatch requestBatch = new GraphRequestBatch(request);

        // 1 millisecond timeout should be too short for response from server.
        requestBatch.setTimeout(1);

        TestGraphRequestAsyncTask task = new TestGraphRequestAsyncTask(requestBatch);
        task.executeOnBlockerThread();

        // Note: plus 1, because the overall async task signals as well.
        waitAndAssertSuccess(2);
    }

    @LargeTest
    public void testLongTimeoutAllowsSuccess() {
        final AccessToken accessToken = getAccessTokenForSharedUser();

        GraphRequest request = new GraphRequest(accessToken, "me", null, null,
                new ExpectSuccessCallback());

        GraphRequestBatch requestBatch = new GraphRequestBatch(request);

        // 10 second timeout should be long enough for successful response from server.
        requestBatch.setTimeout(10000);

        TestGraphRequestAsyncTask task = new TestGraphRequestAsyncTask(requestBatch);
        task.executeOnBlockerThread();

        // Note: plus 1, because the overall async task signals as well.
        waitAndAssertSuccess(2);
    }
}


File: facebook/tests/src/com/facebook/BatchRequestTests.java
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

import android.graphics.Bitmap;
import android.test.suitebuilder.annotation.LargeTest;

import com.facebook.share.internal.ShareInternalUtility;

import org.json.JSONObject;

import java.io.IOException;
import java.lang.Override;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

public class BatchRequestTests extends FacebookTestCase {
    protected void setUp() throws Exception {
        super.setUp();

        // Tests that need this set should explicitly set it.
        GraphRequest.setDefaultBatchApplicationId(null);
    }

    protected String[] getDefaultPermissions()
    {
        return new String[] { "email", "publish_actions", "read_stream" };
    };

    @LargeTest
    public void testCreateNonemptyRequestBatch() {
        GraphRequest meRequest = GraphRequest.newMeRequest(null, null);

        GraphRequestBatch batch = new GraphRequestBatch(new GraphRequest[] { meRequest, meRequest });
        assertEquals(2, batch.size());
        assertEquals(meRequest, batch.get(0));
        assertEquals(meRequest, batch.get(1));
    }

    @LargeTest
    public void testBatchWithoutAppIDIsError() {
        GraphRequest request1 = new GraphRequest(null, "TourEiffel", null, null, new ExpectFailureCallback());
        GraphRequest request2 = new GraphRequest(null, "SpaceNeedle", null, null, new ExpectFailureCallback());
        GraphRequest.executeBatchAndWait(request1, request2);
    }

    @LargeTest
    public void testExecuteBatchRequestsPathEncoding() throws IOException {
        // ensures that paths passed to batch requests are encoded properly before
        // we send it up to the server

        final AccessToken accessToken = getAccessTokenForSharedUser();

        GraphRequest request1 = new GraphRequest(accessToken, "TourEiffel");
        request1.setBatchEntryName("eiffel");
        request1.setBatchEntryOmitResultOnSuccess(false);
        GraphRequest request2 = new GraphRequest(accessToken, "{result=eiffel:$.id}");

        List<GraphResponse> responses = GraphRequest.executeBatchAndWait(request1, request2);
        assertEquals(2, responses.size());
        assertTrue(responses.get(0).getError() == null);
        assertTrue(responses.get(1).getError() == null);

        JSONObject eiffelTower1 = responses.get(0).getJSONObject();
        JSONObject eiffelTower2 = responses.get(1).getJSONObject();
        assertTrue(eiffelTower1 != null);
        assertTrue(eiffelTower2 != null);

        assertEquals("Paris", eiffelTower1.optJSONObject("location").optString("city"));
        assertEquals("Paris", eiffelTower2.optJSONObject("location").optString("city"));
    }

    @LargeTest
    public void testExecuteBatchedGets() throws IOException {
        final AccessToken accessToken = getAccessTokenForSharedUser();

        GraphRequest request1 = new GraphRequest(accessToken, "TourEiffel");
        GraphRequest request2 = new GraphRequest(accessToken, "SpaceNeedle");

        List<GraphResponse> responses = GraphRequest.executeBatchAndWait(request1, request2);
        assertEquals(2, responses.size());
        assertTrue(responses.get(0).getError() == null);
        assertTrue(responses.get(1).getError() == null);

        JSONObject eiffelTower = responses.get(0).getJSONObject();
        JSONObject spaceNeedle = responses.get(1).getJSONObject();
        assertTrue(eiffelTower != null);
        assertTrue(spaceNeedle != null);

        assertEquals("Paris", eiffelTower.optJSONObject("location").optString("city"));
        assertEquals("Seattle", spaceNeedle.optJSONObject("location").optString("city"));
    }

    @LargeTest
    public void testFacebookErrorResponsesCreateErrors() {
        setBatchApplicationIdForTestApp();

        GraphRequest request1 = new GraphRequest(null, "somestringthatshouldneverbeavalidfobjectid");
        GraphRequest request2 = new GraphRequest(null, "someotherstringthatshouldneverbeavalidfobjectid");
        List<GraphResponse> responses = GraphRequest.executeBatchAndWait(request1, request2);

        assertEquals(2, responses.size());
        assertTrue(responses.get(0).getError() != null);
        assertTrue(responses.get(1).getError() != null);

        FacebookRequestError error = responses.get(0).getError();
        assertTrue(error.getException() instanceof FacebookServiceException);
        assertTrue(error.getErrorType() != null);
        assertTrue(error.getErrorCode() != FacebookRequestError.INVALID_ERROR_CODE);
    }

    @LargeTest
    public void testBatchPostStatusUpdate() {
        final AccessToken accessToken = getAccessTokenForSharedUser();

        JSONObject statusUpdate1 = createStatusUpdate("1");
        JSONObject statusUpdate2 = createStatusUpdate("2");

        GraphRequest postRequest1 = GraphRequest.newPostRequest(accessToken, "me/feed", statusUpdate1, null);
        postRequest1.setBatchEntryName("postRequest1");
        postRequest1.setBatchEntryOmitResultOnSuccess(false);
        GraphRequest postRequest2 = GraphRequest.newPostRequest(accessToken, "me/feed", statusUpdate2, null);
        postRequest2.setBatchEntryName("postRequest2");
        postRequest2.setBatchEntryOmitResultOnSuccess(false);
        GraphRequest getRequest1 = new GraphRequest(accessToken, "{result=postRequest1:$.id}");
        GraphRequest getRequest2 = new GraphRequest(accessToken, "{result=postRequest2:$.id}");

        List<GraphResponse> responses = GraphRequest.executeBatchAndWait(postRequest1, postRequest2, getRequest1, getRequest2);
        assertNotNull(responses);
        assertEquals(4, responses.size());
        assertNoErrors(responses);

        JSONObject retrievedStatusUpdate1 = responses.get(2).getJSONObject();
        JSONObject retrievedStatusUpdate2 = responses.get(3).getJSONObject();
        assertNotNull(retrievedStatusUpdate1);
        assertNotNull(retrievedStatusUpdate2);

        assertEquals(statusUpdate1.optString("message"), retrievedStatusUpdate1.optString("message"));
        assertEquals(statusUpdate2.optString("message"), retrievedStatusUpdate2.optString("message"));
    }

    @LargeTest
    public void testTwoDifferentAccessTokens() {
        final AccessToken accessToken1 = getAccessTokenForSharedUser();
        final AccessToken accessToken2 = getAccessTokenForSharedUser(SECOND_TEST_USER_TAG);

        GraphRequest request1 = GraphRequest.newMeRequest(accessToken1, null);
        GraphRequest request2 = GraphRequest.newMeRequest(accessToken2, null);

        List<GraphResponse> responses = GraphRequest.executeBatchAndWait(request1, request2);
        assertNotNull(responses);
        assertEquals(2, responses.size());

        JSONObject user1 = responses.get(0).getJSONObject();
        JSONObject user2 = responses.get(1).getJSONObject();

        assertNotNull(user1);
        assertNotNull(user2);

        assertFalse(user1.optString("id").equals(user2.optString("id")));
        assertEquals(accessToken1.getUserId(), user1.optString("id"));
        assertEquals(accessToken2.getUserId(), user2.optString("id"));
    }

    @LargeTest
    public void testBatchWithValidSessionAndNoSession() {
        final AccessToken accessToken = getAccessTokenForSharedUser();

        GraphRequest request1 = new GraphRequest(accessToken, "me");
        GraphRequest request2 = new GraphRequest(null, "me");

        List<GraphResponse> responses = GraphRequest.executeBatchAndWait(request1, request2);
        assertNotNull(responses);
        assertEquals(2, responses.size());

        JSONObject user1 = responses.get(0).getJSONObject();
        JSONObject user2 = responses.get(1).getJSONObject();

        assertNotNull(user1);
        assertNull(user2);

        assertEquals(accessToken.getUserId(), user1.optString("id"));
    }

    @LargeTest
    public void testBatchWithNoSessionAndValidSession() {
        final AccessToken accessToken = getAccessTokenForSharedUser();

        GraphRequest request1 = new GraphRequest(null, "me");
        GraphRequest request2 = new GraphRequest(accessToken, "me");

        List<GraphResponse> responses = GraphRequest.executeBatchAndWait(request1, request2);
        assertNotNull(responses);
        assertEquals(2, responses.size());

        JSONObject user1 = responses.get(0).getJSONObject();
        JSONObject user2 = responses.get(1).getJSONObject();

        assertNull(user1);
        assertNotNull(user2);

        assertEquals(accessToken.getUserId(), user2.optString("id"));
    }

    @LargeTest
    public void testMixedSuccessAndFailure() {
        final AccessToken accessToken = getAccessTokenForSharedUser();

        final int NUM_REQUESTS = 8;
        GraphRequest[] requests = new GraphRequest[NUM_REQUESTS];
        for (int i = 0; i < NUM_REQUESTS; ++i) {
            boolean shouldSucceed = (i % 2) == 1;
            requests[i] = new GraphRequest(accessToken, shouldSucceed ? "me" : "-1");
        }

        List<GraphResponse> responses = GraphRequest.executeBatchAndWait(requests);
        assertNotNull(responses);
        assertEquals(NUM_REQUESTS, responses.size());

        for (int i = 0; i < NUM_REQUESTS; ++i) {
            boolean shouldSucceed = (i % 2) == 1;

            GraphResponse response = responses.get(i);
            assertNotNull(response);
            if (shouldSucceed) {
                assertNull(response.getError());
                assertNotNull(response.getJSONObject());
            } else {
                assertNotNull(response.getError());
                assertNull(response.getJSONObject());
            }
        }
    }

    @LargeTest
    public void testBatchUploadPhoto() {
        final AccessToken accessToken = getAccessTokenForSharedUserWithPermissions(null,
                "user_photos", "publish_actions");

        final int image1Size = 120;
        final int image2Size = 150;

        Bitmap bitmap1 = createTestBitmap(image1Size);
        Bitmap bitmap2 = createTestBitmap(image2Size);

        GraphRequest uploadRequest1 = ShareInternalUtility.newUploadPhotoRequest(
                ShareInternalUtility.MY_PHOTOS,
                accessToken,
                bitmap1,
                null,
                null,
                null);
        uploadRequest1.setBatchEntryName("uploadRequest1");
        GraphRequest uploadRequest2 = ShareInternalUtility.newUploadPhotoRequest(
                ShareInternalUtility.MY_PHOTOS,
                accessToken,
                bitmap2,
                null,
                null,
                null);
        uploadRequest2.setBatchEntryName("uploadRequest2");
        GraphRequest getRequest1 = new GraphRequest(accessToken, "{result=uploadRequest1:$.id}");
        GraphRequest getRequest2 = new GraphRequest(accessToken, "{result=uploadRequest2:$.id}");

        List<GraphResponse> responses = GraphRequest.executeBatchAndWait(
                uploadRequest1,
                uploadRequest2,
                getRequest1,
                getRequest2);
        assertNotNull(responses);
        assertEquals(4, responses.size());
        assertNoErrors(responses);

        JSONObject retrievedPhoto1 = responses.get(2).getJSONObject();
        JSONObject retrievedPhoto2 = responses.get(3).getJSONObject();
        assertNotNull(retrievedPhoto1);
        assertNotNull(retrievedPhoto2);

        assertEquals(image1Size, retrievedPhoto1.optInt("width"));
        assertEquals(image2Size, retrievedPhoto2.optInt("width"));
    }

    @LargeTest
    public void testCallbacksAreCalled() {
        setBatchApplicationIdForTestApp();

        ArrayList<GraphRequest> requests = new ArrayList<GraphRequest>();
        final ArrayList<Boolean> calledBack = new ArrayList<Boolean>();

        final int NUM_REQUESTS = 4;
        for (int i = 0; i < NUM_REQUESTS; ++i) {
            GraphRequest request = new GraphRequest(null, "4");

            request.setCallback(new GraphRequest.Callback() {
                @Override
                public void onCompleted(GraphResponse response) {
                    calledBack.add(true);
                }
            });

            requests.add(request);
        }

        List<GraphResponse> responses = GraphRequest.executeBatchAndWait(requests);
        assertNotNull(responses);
        assertTrue(calledBack.size() == NUM_REQUESTS);
    }


    @LargeTest
    public void testExplicitDependencyDefaultsToOmitFirstResponse() {
        final AccessToken accessToken = getAccessTokenForSharedUser();

        GraphRequest requestMe = GraphRequest.newMeRequest(accessToken, null);
        requestMe.setBatchEntryName("me_request");

        GraphRequest requestMyFriends = GraphRequest.newMyFriendsRequest(accessToken, null);
        requestMyFriends.setBatchEntryDependsOn("me_request");

        List<GraphResponse> responses = GraphRequest.executeBatchAndWait(requestMe, requestMyFriends);

        GraphResponse meResponse = responses.get(0);
        GraphResponse myFriendsResponse = responses.get(1);

        assertNull(meResponse.getJSONObject());
        assertNotNull(myFriendsResponse.getJSONObject());
    }

    @LargeTest
    public void testExplicitDependencyCanIncludeFirstResponse() {
        final AccessToken accessToken = getAccessTokenForSharedUser();

        GraphRequest requestMe = GraphRequest.newMeRequest(accessToken, null);
        requestMe.setBatchEntryName("me_request");
        requestMe.setBatchEntryOmitResultOnSuccess(false);

        GraphRequest requestMyFriends = GraphRequest.newMyFriendsRequest(accessToken, null);
        requestMyFriends.setBatchEntryDependsOn("me_request");

        List<GraphResponse> responses = GraphRequest.executeBatchAndWait(requestMe, requestMyFriends);

        GraphResponse meResponse = responses.get(0);
        GraphResponse myFriendsResponse = responses.get(1);

        assertNotNull(meResponse.getJSONObject());
        assertNotNull(myFriendsResponse.getJSONObject());
    }

    @LargeTest
    public void testAddAndRemoveBatchCallbacks() {
        GraphRequestBatch batch = new GraphRequestBatch();

        GraphRequestBatch.Callback callback1 = new GraphRequestBatch.Callback() {
            @Override
            public void onBatchCompleted(GraphRequestBatch batch) {
            }
        };

        GraphRequestBatch.Callback callback2 = new GraphRequestBatch.Callback() {
            @Override
            public void onBatchCompleted(GraphRequestBatch batch) {
            }
        };

        batch.addCallback(callback1);
        batch.addCallback(callback2);

        assertEquals(2, batch.getCallbacks().size());

        batch.removeCallback(callback1);
        batch.removeCallback(callback2);

        assertEquals(0, batch.getCallbacks().size());
    }

    @LargeTest
    public void testBatchCallbackIsCalled() {
        final AtomicInteger count = new AtomicInteger();
        GraphRequest request1 = GraphRequest.newGraphPathRequest(null, "4", new GraphRequest.Callback() {
            @Override
            public void onCompleted(GraphResponse response) {
                count.incrementAndGet();
            }
        });
        GraphRequest request2 = GraphRequest.newGraphPathRequest(null, "4", new GraphRequest.Callback() {
            @Override
            public void onCompleted(GraphResponse response) {
                count.incrementAndGet();
            }
        });

        GraphRequestBatch batch = new GraphRequestBatch(request1, request2);
        batch.addCallback(new GraphRequestBatch.Callback() {
            @Override
            public void onBatchCompleted(GraphRequestBatch batch) {
                count.incrementAndGet();
            }
        });

        batch.executeAndWait();
        assertEquals(3, count.get());
    }

    @LargeTest
    public void testBatchOnProgressCallbackIsCalled() {
        final AtomicInteger count = new AtomicInteger();

        final AccessToken accessToken = getAccessTokenForSharedUser();

        String appId = getApplicationId();
        GraphRequest.setDefaultBatchApplicationId(appId);

        GraphRequest request1 = GraphRequest.newGraphPathRequest(accessToken, "4", null);
        assertNotNull(request1);
        GraphRequest request2 = GraphRequest.newGraphPathRequest(accessToken, "4", null);
        assertNotNull(request2);

        GraphRequestBatch batch = new GraphRequestBatch(request1, request2);
        batch.addCallback(new GraphRequestBatch.OnProgressCallback() {
            @Override
            public void onBatchCompleted(GraphRequestBatch batch) {
            }

            @Override
            public void onBatchProgress(GraphRequestBatch batch, long current, long max) {
                count.incrementAndGet();
            }
        });

        batch.executeAndWait();
        assertEquals(1, count.get());
    }

    @LargeTest
    public void testBatchLastOnProgressCallbackIsCalledOnce() {
        final AtomicInteger count = new AtomicInteger();

        final AccessToken accessToken = getAccessTokenForSharedUser();

        String appId = getApplicationId();
        GraphRequest.setDefaultBatchApplicationId(appId);

        GraphRequest request1 = GraphRequest.newGraphPathRequest(accessToken, "4", null);
        assertNotNull(request1);
        GraphRequest request2 = GraphRequest.newGraphPathRequest(accessToken, "4", null);
        assertNotNull(request2);

        GraphRequestBatch batch = new GraphRequestBatch(request1, request2);
        batch.addCallback(new GraphRequestBatch.OnProgressCallback() {
            @Override
            public void onBatchCompleted(GraphRequestBatch batch) {
            }

            @Override
            public void onBatchProgress(GraphRequestBatch batch, long current, long max) {
                if (current == max) {
                    count.incrementAndGet();
                }
                else if (current > max) {
                    count.set(0);
                }
            }
        });

        batch.executeAndWait();
        assertEquals(1, count.get());
    }


    @LargeTest
    public void testMixedBatchCallbacks() {
        final AtomicInteger requestProgressCount = new AtomicInteger();
        final AtomicInteger requestCompletedCount = new AtomicInteger();
        final AtomicInteger batchProgressCount = new AtomicInteger();
        final AtomicInteger batchCompletedCount = new AtomicInteger();

        final AccessToken accessToken = getAccessTokenForSharedUser();

        String appId = getApplicationId();
        GraphRequest.setDefaultBatchApplicationId(appId);

        GraphRequest request1 = GraphRequest.newGraphPathRequest(
                null, "4", new GraphRequest.OnProgressCallback() {
            @Override
            public void onCompleted(GraphResponse response) {
                requestCompletedCount.incrementAndGet();
            }

            @Override
            public void onProgress(long current, long max) {
                if (current == max) {
                    requestProgressCount.incrementAndGet();
                }
                else if (current > max) {
                    requestProgressCount.set(0);
                }
            }
        });
        assertNotNull(request1);

        GraphRequest request2 = GraphRequest.newGraphPathRequest(null, "4", null);
        assertNotNull(request2);

        GraphRequestBatch batch = new GraphRequestBatch(request1, request2);
        batch.addCallback(new GraphRequestBatch.OnProgressCallback() {
            @Override
            public void onBatchCompleted(GraphRequestBatch batch) {
                batchCompletedCount.incrementAndGet();
            }

            @Override
            public void onBatchProgress(GraphRequestBatch batch, long current, long max) {
                if (current == max) {
                    batchProgressCount.incrementAndGet();
                } else if (current > max) {
                    batchProgressCount.set(0);
                }
            }
        });

        batch.executeAndWait();
        
        assertEquals(1, requestProgressCount.get());
        assertEquals(1, requestCompletedCount.get());
        assertEquals(1, batchProgressCount.get());
        assertEquals(1, batchCompletedCount.get());
    }
}


File: facebook/tests/src/com/facebook/FacebookActivityTestCase.java
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

import android.app.Activity;
import android.content.res.AssetManager;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.os.Bundle;
import android.os.ConditionVariable;
import android.os.Handler;
import android.test.ActivityInstrumentationTestCase2;
import android.util.Log;
import com.facebook.internal.Utility;
import junit.framework.AssertionFailedError;
import org.json.JSONException;
import org.json.JSONObject;
import org.json.JSONTokener;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

public class FacebookActivityTestCase<T extends Activity> extends ActivityInstrumentationTestCase2<T> {
    private static final String TAG = FacebookActivityTestCase.class.getSimpleName();

    private static String applicationId;
    private static String applicationSecret;
    private static String clientToken;
    private static TestUserManager testUserManager;

    public final static String SECOND_TEST_USER_TAG = "Second";
    public final static String THIRD_TEST_USER_TAG = "Third";

    private TestBlocker testBlocker;

    protected synchronized TestBlocker getTestBlocker() {
        if (testBlocker == null) {
            testBlocker = TestBlocker.createTestBlocker();
        }
        return testBlocker;
    }

    public FacebookActivityTestCase(Class<T> activityClass) {
        super("", activityClass);
    }

    protected String[] getDefaultPermissions() { return null; };

    protected AccessToken getAccessTokenForSharedUser() {
        return getAccessTokenForSharedUser(null);
    }

    protected AccessToken getAccessTokenForSharedUser(String sessionUniqueUserTag) {
        return getAccessTokenForSharedUserWithPermissions(sessionUniqueUserTag,
                getDefaultPermissions());
    }

    protected AccessToken getAccessTokenForSharedUserWithPermissions(String sessionUniqueUserTag,
        List<String> permissions) {
        return getTestUserManager().getAccessTokenForSharedUser(permissions, sessionUniqueUserTag);
    }

    protected AccessToken getAccessTokenForSharedUserWithPermissions(String sessionUniqueUserTag,
                                                                      String... permissions) {
        List<String> permissionList = (permissions != null) ? Arrays.asList(permissions) : null;
        return getAccessTokenForSharedUserWithPermissions(sessionUniqueUserTag, permissionList);
    }

    protected TestUserManager getTestUserManager() {
        if (testUserManager == null) {
            synchronized (FacebookActivityTestCase.class) {
                if (testUserManager == null) {
                    readApplicationIdAndSecret();
                    testUserManager = new TestUserManager(applicationSecret, applicationId);
                }
            }
        }

        return testUserManager;
    }

    // Turns exceptions from the TestBlocker into JUnit assertions
    protected void waitAndAssertSuccess(TestBlocker testBlocker, int numSignals) {
        try {
            testBlocker.waitForSignalsAndAssertSuccess(numSignals);
        } catch (AssertionFailedError e) {
            throw e;
        } catch (Exception e) {
            fail("Got exception: " + e.getMessage());
        }
    }

    protected void waitAndAssertSuccess(int numSignals) {
        waitAndAssertSuccess(getTestBlocker(), numSignals);
    }

    protected void waitAndAssertSuccessOrRethrow(int numSignals) throws Exception {
        getTestBlocker().waitForSignalsAndAssertSuccess(numSignals);
    }

    protected void runAndBlockOnUiThread(final int expectedSignals, final Runnable runnable) throws Throwable {
        final TestBlocker blocker = getTestBlocker();
        runTestOnUiThread(new Runnable() {
            @Override
            public void run() {
                runnable.run();
                blocker.signal();
            }
        });
        // We wait for the operation to complete; wait for as many other signals as we expect.
        blocker.waitForSignals(1 + expectedSignals);
        // Wait for the UI thread to become idle so any UI updates the runnable triggered have a chance
        // to finish before we return.
        getInstrumentation().waitForIdleSync();
    }

    protected synchronized void readApplicationIdAndSecret() {
        synchronized (FacebookTestCase.class) {
            if (applicationId != null && applicationSecret != null && clientToken != null) {
                return;
            }

            AssetManager assets = getInstrumentation().getTargetContext().getResources().getAssets();
            InputStream stream = null;
            final String errorMessage = "could not read applicationId and applicationSecret from config.json; ensure "
                    + "you have run 'configure_unit_tests.sh'. Error: ";
            try {
                stream = assets.open("config.json");
                String string = Utility.readStreamToString(stream);

                JSONTokener tokener = new JSONTokener(string);
                Object obj = tokener.nextValue();
                if (!(obj instanceof JSONObject)) {
                    fail(errorMessage + "could not deserialize a JSONObject");
                }
                JSONObject jsonObject = (JSONObject) obj;

                applicationId = jsonObject.optString("applicationId");
                applicationSecret = jsonObject.optString("applicationSecret");
                clientToken = jsonObject.optString("clientToken");

                if (Utility.isNullOrEmpty(applicationId) || Utility.isNullOrEmpty(applicationSecret) ||
                        Utility.isNullOrEmpty(clientToken)) {
                    fail(errorMessage + "config values are missing");
                }
            } catch (IOException e) {
                fail(errorMessage + e.toString());
            } catch (JSONException e) {
                fail(errorMessage + e.toString());
            } finally {
                if (stream != null) {
                    try {
                        stream.close();
                    } catch (IOException e) {
                        fail(errorMessage + e.toString());
                    }
                }
            }
        }
    }

    protected static String getApplicationId() {
        return applicationId;
    }

    protected static String getApplicationSecret() {
        return applicationSecret;
    }

    protected void setUp() throws Exception {
        super.setUp();

        // Make sure the logging is turned on.
        FacebookSdk.setIsDebugEnabled(true);

        // Make sure we have read application ID and secret.
        readApplicationIdAndSecret();

        FacebookSdk.sdkInitialize(getInstrumentation().getTargetContext());
        FacebookSdk.setApplicationId(applicationId);
        FacebookSdk.setClientToken(clientToken);

        // These are useful for debugging unit test failures.
        FacebookSdk.addLoggingBehavior(LoggingBehavior.REQUESTS);
        FacebookSdk.addLoggingBehavior(LoggingBehavior.INCLUDE_ACCESS_TOKENS);

        // We want the UI thread to be in StrictMode to catch any violations.
        // TODO: reenable this
        // turnOnStrictModeForUiThread();

        // Needed to bypass a dexmaker bug for mockito
        System.setProperty("dexmaker.dexcache",
                getInstrumentation().getTargetContext().getCacheDir().getPath());
    }

    protected void tearDown() throws Exception {
        super.tearDown();

        synchronized (this) {
            if (testBlocker != null) {
                testBlocker.quit();
            }
        }
    }

    protected Bundle getNativeLinkingExtras(String token, String userId) {
        readApplicationIdAndSecret();

        Bundle extras = new Bundle();
        String extraLaunchUriString = String
                .format("fbrpc://facebook/nativethirdparty?app_id=%s&package_name=com.facebook.sdk.tests&class_name=com.facebook.FacebookActivityTests$FacebookTestActivity&access_token=%s",
                        applicationId, token);
        extras.putString("extra_launch_uri", extraLaunchUriString);
        extras.putString("expires_in", "3600");
        extras.putLong("app_id", Long.parseLong(applicationId));
        extras.putString("access_token", token);
        if(userId != null && !userId.isEmpty()) {
            extras.putString("user_id", userId);
        }

        return extras;
    }

    protected JSONObject getAndAssert(AccessToken accessToken, String id) {
        GraphRequest request = new GraphRequest(accessToken, id);
        GraphResponse response = request.executeAndWait();
        assertNotNull(response);

        assertNull(response.getError());

        JSONObject result = response.getJSONObject();
        assertNotNull(result);

        return result;
    }

    protected JSONObject postGetAndAssert(AccessToken accessToken, String path,
                                          JSONObject graphObject) {
        GraphRequest request = GraphRequest.newPostRequest(accessToken, path, graphObject, null);
        GraphResponse response = request.executeAndWait();
        assertNotNull(response);

        assertNull(response.getError());

        JSONObject result = response.getJSONObject();
        assertNotNull(result);
        assertNotNull(result.optString("id"));

        return getAndAssert(accessToken, result.optString("id"));
    }

    protected void setBatchApplicationIdForTestApp() {
        readApplicationIdAndSecret();
        GraphRequest.setDefaultBatchApplicationId(applicationId);
    }

    protected JSONObject batchCreateAndGet(AccessToken accessToken, String graphPath,
                                           JSONObject graphObject, String fields) {
        GraphRequest create = GraphRequest.newPostRequest(accessToken, graphPath, graphObject,
                new ExpectSuccessCallback());
        create.setBatchEntryName("create");
        GraphRequest get = GraphRequest.newGraphPathRequest(accessToken, "{result=create:$.id}",
                new ExpectSuccessCallback());
        if (fields != null) {
            Bundle parameters = new Bundle();
            parameters.putString("fields", fields);
            get.setParameters(parameters);
        }

        return batchPostAndGet(create, get);
    }

    protected JSONObject batchUpdateAndGet(AccessToken accessToken, String graphPath,
                                           JSONObject graphObject, String fields) {
        GraphRequest update = GraphRequest.newPostRequest(accessToken, graphPath, graphObject,
                new ExpectSuccessCallback());
        GraphRequest get = GraphRequest.newGraphPathRequest(accessToken, graphPath,
                new ExpectSuccessCallback());
        if (fields != null) {
            Bundle parameters = new Bundle();
            parameters.putString("fields", fields);
            get.setParameters(parameters);
        }

        return batchPostAndGet(update, get);
    }

    protected JSONObject batchPostAndGet(GraphRequest post, GraphRequest get) {
        List<GraphResponse> responses = GraphRequest.executeBatchAndWait(post, get);
        assertEquals(2, responses.size());

        JSONObject resultGraphObject = responses.get(1).getJSONObject();
        assertNotNull(resultGraphObject);
        return resultGraphObject;
    }

    protected JSONObject createStatusUpdate(String unique) {
        JSONObject statusUpdate = new JSONObject();
        String message = String.format(
                "Check out my awesome new status update posted at: %s. Some chars for you: +\"[]:,%s", new Date(),
                unique);
        try {
            statusUpdate.put("message", message);
        } catch (JSONException e) {
            throw new RuntimeException(e);
        }
        return statusUpdate;
    }

    protected Bitmap createTestBitmap(int size) {
        Bitmap image = Bitmap.createBitmap(size, size, Bitmap.Config.RGB_565);
        image.eraseColor(Color.BLUE);
        return image;
    }

    protected void assertDateEqualsWithinDelta(Date expected, Date actual, long deltaInMsec) {
        long delta = Math.abs(expected.getTime() - actual.getTime());
        assertTrue(delta < deltaInMsec);
    }

    protected void assertDateDiffersWithinDelta(Date expected, Date actual, long expectedDifference, long deltaInMsec) {
        long delta = Math.abs(expected.getTime() - actual.getTime()) - expectedDifference;
        assertTrue(delta < deltaInMsec);
    }

    protected void assertNoErrors(List<GraphResponse> responses) {
        for (int i = 0; i < responses.size(); ++i) {
            GraphResponse response = responses.get(i);
            assertNotNull(response);
            assertNull(response.getError());
        }
    }

    protected File createTempFileFromAsset(String assetPath) throws IOException {
        InputStream inputStream = null;
        FileOutputStream outStream = null;

        try {
            AssetManager assets = getActivity().getResources().getAssets();
            inputStream = assets.open(assetPath);

            File outputDir = getActivity().getCacheDir(); // context being the Activity pointer
            File outputFile = File.createTempFile("prefix", assetPath, outputDir);
            outStream = new FileOutputStream(outputFile);

            final int bufferSize = 1024 * 2;
            byte[] buffer = new byte[bufferSize];
            int n = 0;
            while ((n = inputStream.read(buffer)) != -1) {
                outStream.write(buffer, 0, n);
            }

            return outputFile;
        } finally {
            Utility.closeQuietly(outStream);
            Utility.closeQuietly(inputStream);
        }
    }

    protected void runOnBlockerThread(final Runnable runnable, boolean waitForCompletion) {
        Runnable runnableToPost = runnable;
        final ConditionVariable condition = waitForCompletion ? new ConditionVariable(!waitForCompletion) : null;

        if (waitForCompletion) {
            runnableToPost = new Runnable() {
                @Override
                public void run() {
                    runnable.run();
                    condition.open();
                }
            };
        }

        TestBlocker blocker = getTestBlocker();
        Handler handler = blocker.getHandler();
        handler.post(runnableToPost);

        if (waitForCompletion) {
            boolean success = condition.block(10000);
            assertTrue(success);
        }
    }

    protected void closeBlockerAndAssertSuccess() {
        TestBlocker blocker;
        synchronized (this) {
            blocker = getTestBlocker();
            testBlocker = null;
        }

        blocker.quit();

        boolean joined = false;
        while (!joined) {
            try {
                blocker.join();
                joined = true;
            } catch (InterruptedException e) {
            }
        }

        try {
            blocker.assertSuccess();
        } catch (Exception e) {
            fail(e.toString());
        }
    }

    protected TestGraphRequestAsyncTask createAsyncTaskOnUiThread(final GraphRequest... requests) throws Throwable {
        final ArrayList<TestGraphRequestAsyncTask> result = new ArrayList<TestGraphRequestAsyncTask>();
        runTestOnUiThread(new Runnable() {
            @Override
            public void run() {
                result.add(new TestGraphRequestAsyncTask(requests));
            }
        });
        return result.isEmpty() ? null : result.get(0);
    }

    /*
     * Classes and helpers related to asynchronous requests.
     */

    // A subclass of RequestAsyncTask that knows how to interact with TestBlocker to ensure that tests can wait
    // on and assert success of async tasks.
    protected class TestGraphRequestAsyncTask extends GraphRequestAsyncTask {
        private final TestBlocker blocker = FacebookActivityTestCase.this.getTestBlocker();

        public TestGraphRequestAsyncTask(GraphRequest... requests) {
            super(requests);
        }

        public TestGraphRequestAsyncTask(List<GraphRequest> requests) {
            super(requests);
        }

        public TestGraphRequestAsyncTask(GraphRequestBatch requests) {
            super(requests);
        }

        public TestGraphRequestAsyncTask(HttpURLConnection connection, GraphRequest... requests) {
            super(connection, requests);
        }

        public TestGraphRequestAsyncTask(HttpURLConnection connection, List<GraphRequest> requests) {
            super(connection, requests);
        }

        public TestGraphRequestAsyncTask(HttpURLConnection connection, GraphRequestBatch requests) {
            super(connection, requests);
        }

        public final TestBlocker getBlocker() {
            return blocker;
        }

        public final Exception getThrowable() {
            return getException();
        }

        protected void onPostExecute(List<GraphResponse> result) {
            try {
                super.onPostExecute(result);

                if (getException() != null) {
                    blocker.setException(getException());
                }
            } finally {
                Log.d("TestRequestAsyncTask", "signaling blocker");
                blocker.signal();
            }
        }

        // In order to be able to block and accumulate exceptions, we want to ensure the async task is really
        // being started on the blocker's thread, rather than the test's thread. Use this instead of calling
        // execute directly in unit tests.
        public void executeOnBlockerThread() {
            ensureAsyncTaskLoaded();

            Runnable runnable = new Runnable() {
                public void run() {
                    execute();
                }
            };
            Handler handler = new Handler(blocker.getLooper());
            handler.post(runnable);
        }

        private void ensureAsyncTaskLoaded() {
            // Work around this issue on earlier frameworks: http://stackoverflow.com/a/7818839/782044
            try {
                runAndBlockOnUiThread(0, new Runnable() {
                    @Override
                    public void run() {
                        try {
                            Class.forName("android.os.AsyncTask");
                        } catch (ClassNotFoundException e) {
                        }
                    }
                });
            } catch (Throwable throwable) {
            }
        }
    }

    // Provides an implementation of Request.Callback that will assert either success (no error) or failure (error)
    // of a request, and allow derived classes to perform additional asserts.
    protected class TestCallback implements GraphRequest.Callback {
        private final TestBlocker blocker;
        private final boolean expectSuccess;

        public TestCallback(TestBlocker blocker, boolean expectSuccess) {
            this.blocker = blocker;
            this.expectSuccess = expectSuccess;
        }

        public TestCallback(boolean expectSuccess) {
            this(FacebookActivityTestCase.this.getTestBlocker(), expectSuccess);
        }

        @Override
        public void onCompleted(GraphResponse response) {
            try {
                // We expect to be called on the right thread.
                if (Thread.currentThread() != blocker) {
                    throw new FacebookException("Invalid thread " + Thread.currentThread().getId()
                            + "; expected to be called on thread " + blocker.getId());
                }

                // We expect either success or failure.
                if (expectSuccess && response.getError() != null) {
                    throw response.getError().getException();
                } else if (!expectSuccess && response.getError() == null) {
                    throw new FacebookException("Expected failure case, received no error");
                }

                // Some tests may want more fine-grained control and assert additional conditions.
                performAsserts(response);
            } catch (Exception e) {
                blocker.setException(e);
            } finally {
                // Tell anyone waiting on us that this callback was called.
                blocker.signal();
            }
        }

        protected void performAsserts(GraphResponse response) {
        }
    }

    // A callback that will assert if the request resulted in an error.
    protected class ExpectSuccessCallback extends TestCallback {
        public ExpectSuccessCallback() {
            super(true);
        }
    }

    // A callback that will assert if the request did NOT result in an error.
    protected class ExpectFailureCallback extends TestCallback {
        public ExpectFailureCallback() {
            super(false);
        }
    }

    public static abstract class MockGraphRequest extends GraphRequest {
        public abstract GraphResponse createResponse();
    }

    public static class MockGraphRequestBatch extends GraphRequestBatch {
        public MockGraphRequestBatch(MockGraphRequest... requests) {
            super(requests);
        }

        // Caller must ensure that all the requests in the batch are, in fact, MockRequests.
        public MockGraphRequestBatch(GraphRequestBatch requests) {
            super(requests);
        }

        @Override
        List<GraphResponse> executeAndWaitImpl() {
            List<GraphRequest> requests = getRequests();

            List<GraphResponse> responses = new ArrayList<GraphResponse>();
            for (GraphRequest request : requests) {
                MockGraphRequest mockRequest = (MockGraphRequest) request;
                responses.add(mockRequest.createResponse());
            }

            GraphRequest.runCallbacks(this, responses);

            return responses;
        }
    }

    private AtomicBoolean strictModeOnForUiThread = new AtomicBoolean();

    protected void turnOnStrictModeForUiThread() {
        // We only ever need to do this once. If the boolean is true, we know that the next runnable
        // posted to the UI thread will have strict mode on.
        if (strictModeOnForUiThread.get() == false) {
            try {
                runTestOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        // Double-check whether we really need to still do this on the UI thread.
                        if (strictModeOnForUiThread.compareAndSet(false, true)) {
                            turnOnStrictModeForThisThread();
                        }
                    }
                });
            } catch (Throwable throwable) {
            }
        }
    }

    protected void turnOnStrictModeForThisThread() {
        // We use reflection, because Instrumentation will complain about any references to
        // StrictMode in API versions < 9 when attempting to run the unit tests. No particular
        // effort has been made to make this efficient, since we expect to call it just once.
        try {
            ClassLoader loader = Thread.currentThread().getContextClassLoader();
            Class<?> strictModeClass = Class.forName("android.os.StrictMode", true, loader);
            Class<?> threadPolicyClass = Class.forName(
                    "android.os.StrictMode$ThreadPolicy",
                    true,
                    loader);
            Class<?> threadPolicyBuilderClass = Class.forName(
                    "android.os.StrictMode$ThreadPolicy$Builder",
                    true,
                    loader);

            Object threadPolicyBuilder = threadPolicyBuilderClass.getConstructor().newInstance();
            threadPolicyBuilder = threadPolicyBuilderClass.getMethod("detectAll").invoke(
                    threadPolicyBuilder);
            threadPolicyBuilder = threadPolicyBuilderClass.getMethod("penaltyDeath").invoke(
                    threadPolicyBuilder);

            Object threadPolicy = threadPolicyBuilderClass.getMethod("build").invoke(
                    threadPolicyBuilder);
            strictModeClass.getMethod("setThreadPolicy", threadPolicyClass).invoke(
                    strictModeClass,
                    threadPolicy);
        } catch (Exception ex) {
        }
    }
}


File: facebook/tests/src/com/facebook/RequestTests.java
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

import android.graphics.Bitmap;
import android.location.Location;
import android.net.Uri;
import android.os.Bundle;
import android.test.suitebuilder.annotation.LargeTest;

import com.facebook.share.ShareApi;
import com.facebook.share.Sharer;
import com.facebook.share.internal.ShareInternalUtility;
import com.facebook.share.model.SharePhoto;
import com.facebook.share.model.SharePhotoContent;
import com.facebook.share.model.ShareVideo;
import com.facebook.share.model.ShareVideoContent;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

public class RequestTests extends FacebookTestCase {
    private static final String TEST_OG_TYPE = "facebooksdktests:test";
    private static final long REQUEST_TIMEOUT_MILLIS = 10000;

    protected String[] getDefaultPermissions()
    {
        return new String[] {
                "email",
                "publish_actions",
                "read_stream",
                "user_photos",
                "user_videos" };
    };

    @Override
    public void setUp() throws Exception {
        super.setUp();
        AccessToken.setCurrentAccessToken(getAccessTokenForSharedUser());
    }

    @Override
    public void tearDown() throws Exception {
        AccessToken.setCurrentAccessToken(null);
        super.tearDown();
    }

    @LargeTest
    public void testExecuteSingleGet() {
        GraphRequest request = new GraphRequest(AccessToken.getCurrentAccessToken(), "TourEiffel");
        GraphResponse response = request.executeAndWait();

        assertTrue(response != null);
        assertTrue(response.getError() == null);
        assertNotNull(response.getJSONObject());
        assertNotNull(response.getRawResponse());

        JSONObject graphPlace = response.getJSONObject();
        assertEquals("Paris", graphPlace.optJSONObject("location").optString("city"));
    }

    @LargeTest
    public void testBuildsUploadPhotoHttpURLConnection() throws Exception {
        Bitmap image = createTestBitmap(128);

        GraphRequest request = ShareInternalUtility.newUploadPhotoRequest(
                ShareInternalUtility.MY_PHOTOS,
                AccessToken.getCurrentAccessToken(),
                image,
                "Test photo messsage",
                null,
                null);
        HttpURLConnection connection = GraphRequest.toHttpConnection(request);

        assertTrue(connection != null);
        assertNotSame("gzip", connection.getRequestProperty("Content-Encoding"));
        assertNotSame("application/x-www-form-urlencoded", connection.getRequestProperty("Content-Type"));
    }

    @LargeTest
    public void testExecuteSingleGetUsingHttpURLConnection() throws IOException {
        GraphRequest request = new GraphRequest(AccessToken.getCurrentAccessToken(), "TourEiffel");
        HttpURLConnection connection = GraphRequest.toHttpConnection(request);

        assertEquals("gzip", connection.getRequestProperty("Content-Encoding"));
        assertEquals("application/x-www-form-urlencoded", connection.getRequestProperty("Content-Type"));

        List<GraphResponse> responses = GraphRequest.executeConnectionAndWait(connection, Arrays.asList(new GraphRequest[]{request}));
        assertNotNull(responses);
        assertEquals(1, responses.size());

        GraphResponse response = responses.get(0);

        assertTrue(response != null);
        assertTrue(response.getError() == null);
        assertNotNull(response.getJSONObject());
        assertNotNull(response.getRawResponse());

        JSONObject graphPlace = response.getJSONObject();
        assertEquals("Paris", graphPlace.optJSONObject("location").optString("city"));

        // Make sure calling code can still access HTTP headers and call disconnect themselves.
        int code = connection.getResponseCode();
        assertEquals(200, code);
        assertTrue(connection.getHeaderFields().keySet().contains("Content-Type"));
        connection.disconnect();
    }

    @LargeTest
    public void testFacebookErrorResponseCreatesError() {
        GraphRequest request = new GraphRequest(null, "somestringthatshouldneverbeavalidfobjectid");
        GraphResponse response = request.executeAndWait();

        assertTrue(response != null);

        FacebookRequestError error = response.getError();
        assertNotNull(error);
        FacebookException exception = error.getException();
        assertNotNull(exception);

        assertTrue(exception instanceof FacebookServiceException);
        assertNotNull(error.getErrorType());
        assertTrue(error.getErrorCode() != FacebookRequestError.INVALID_ERROR_CODE);
        assertNotNull(error.getRequestResultBody());
    }

    @LargeTest
    public void testRequestWithNoTokenFails() {
        GraphRequest request = new GraphRequest(null, "me");
        GraphResponse response = request.executeAndWait();

        assertNotNull(response.getError());
    }

    @LargeTest
    public void testExecuteRequestMe() {
        GraphRequest request = GraphRequest.newMeRequest(AccessToken.getCurrentAccessToken(), null);
        GraphResponse response = request.executeAndWait();

        validateMeResponse(AccessToken.getCurrentAccessToken(), response);
    }

    static void validateMeResponse(AccessToken accessToken, GraphResponse response) {
        assertNull(response.getError());

        JSONObject me = response.getJSONObject();
        assertNotNull(me);
        assertEquals(accessToken.getUserId(), me.optString("id"));
        assertNotNull(response.getRawResponse());
    }

    @LargeTest
    public void testExecuteMyFriendsRequest() {
        GraphRequest request =
                GraphRequest.newMyFriendsRequest(AccessToken.getCurrentAccessToken(), null);
        GraphResponse response = request.executeAndWait();

        validateMyFriendsResponse(response);
    }

    static void validateMyFriendsResponse(GraphResponse response) {
        assertNotNull(response);

        assertNull(response.getError());

        JSONObject graphResult = response.getJSONObject();
        assertNotNull(graphResult);

        JSONArray results = graphResult.optJSONArray("data");
        assertNotNull(results);

        assertNotNull(response.getRawResponse());
    }

    @LargeTest
    public void testExecutePlaceRequestWithLocation() {
        Location location = new Location("");
        location.setLatitude(47.6204);
        location.setLongitude(-122.3491);

        GraphRequest request = GraphRequest.newPlacesSearchRequest(
                AccessToken.getCurrentAccessToken(),
                location,
                5,
                5,
                null,
                null);
        GraphResponse response = request.executeAndWait();
        assertNotNull(response);

        assertNull(response.getError());

        JSONObject graphResult = response.getJSONObject();
        assertNotNull(graphResult);

        JSONArray results = graphResult.optJSONArray("data");
        assertNotNull(results);

        assertNotNull(response.getRawResponse());
    }

    @LargeTest
    public void testExecutePlaceRequestWithSearchText() {
        // Pass a distance without a location to ensure it is correctly ignored.
        GraphRequest request = GraphRequest.newPlacesSearchRequest(
                AccessToken.getCurrentAccessToken(),
                null,
                1000,
                5,
                "Starbucks",
                null);
        GraphResponse response = request.executeAndWait();
        assertNotNull(response);

        assertNull(response.getError());

        JSONObject graphResult = response.getJSONObject();
        assertNotNull(graphResult);

        JSONArray results = graphResult.optJSONArray("data");
        assertNotNull(results);

        assertNotNull(response.getRawResponse());
    }

    @LargeTest
    public void testExecutePlaceRequestWithLocationAndSearchText() {
        Location location = new Location("");
        location.setLatitude(47.6204);
        location.setLongitude(-122.3491);

        GraphRequest request = GraphRequest.newPlacesSearchRequest(
                AccessToken.getCurrentAccessToken(),
                location,
                1000,
                5,
                "Starbucks",
                null);
        GraphResponse response = request.executeAndWait();
        assertNotNull(response);

        assertNull(response.getError());

        JSONObject graphResult = response.getJSONObject();
        assertNotNull(graphResult);

        JSONArray results = graphResult.optJSONArray("data");
        assertNotNull(results);

        assertNotNull(response.getRawResponse());
    }

    private String executePostOpenGraphRequest() {
        JSONObject data = new JSONObject();
        try {
            data.put("a_property", "hello");
        } catch (JSONException e) {
            throw new RuntimeException(e);
        }

        GraphRequest request = ShareInternalUtility.newPostOpenGraphObjectRequest(
                AccessToken.getCurrentAccessToken(),
                TEST_OG_TYPE,
                "a title",
                "http://www.facebook.com",
                "http://www.facebook.com/zzzzzzzzzzzzzzzzzzz",
                "a description",
                data,
                null);
        GraphResponse response = request.executeAndWait();
        assertNotNull(response);

        assertNull(response.getError());

        JSONObject graphResult = response.getJSONObject();
        assertNotNull(graphResult);
        assertNotNull(graphResult.optString("id"));

        assertNotNull(response.getRawResponse());

        return (String) graphResult.optString("id");
    }

    @LargeTest
    public void testExecutePostOpenGraphRequest() {
        executePostOpenGraphRequest();
    }

    @LargeTest
    public void testDeleteObjectRequest() {
        String id = executePostOpenGraphRequest();

        GraphRequest request = GraphRequest.newDeleteObjectRequest(
                AccessToken.getCurrentAccessToken(),
                id,
                null);
        GraphResponse response = request.executeAndWait();
        assertNotNull(response);

        assertNull(response.getError());

        JSONObject result = response.getJSONObject();
        assertNotNull(result);

        assertTrue(result.optBoolean(GraphResponse.SUCCESS_KEY));
        assertNotNull(response.getRawResponse());
    }

    @LargeTest
    public void testUpdateOpenGraphObjectRequest() throws JSONException {
        String id = executePostOpenGraphRequest();

        JSONObject data = new JSONObject();
        data.put("a_property", "goodbye");

        GraphRequest request = ShareInternalUtility.newUpdateOpenGraphObjectRequest(
                AccessToken.getCurrentAccessToken(),
                id,
                "another title",
                null,
                "http://www.facebook.com/aaaaaaaaaaaaaaaaa",
                "another description",
                data,
                null);
        GraphResponse response = request.executeAndWait();
        assertNotNull(response);

        assertNull(response.getError());

        JSONObject result = response.getJSONObject();
        assertNotNull(result);
        assertNotNull(response.getRawResponse());
    }

    @LargeTest
    public void testExecuteUploadPhoto() {
        Bitmap image = createTestBitmap(128);

        GraphRequest request = ShareInternalUtility.newUploadPhotoRequest(
                ShareInternalUtility.MY_PHOTOS,
                AccessToken.getCurrentAccessToken(),
                image,
                "Test photo message",
                null,
                null);
        GraphResponse response = request.executeAndWait();
        assertNotNull(response);

        assertNull(response.getError());

        JSONObject result = response.getJSONObject();
        assertNotNull(result);
        assertNotNull(response.getRawResponse());
    }

    @LargeTest
    public void testExecuteUploadPhotoViaFile() throws IOException {
        File outputFile = null;
        FileOutputStream outStream = null;

        try {
            Bitmap image = createTestBitmap(128);

            File outputDir = getActivity().getCacheDir(); // context being the Activity pointer
            outputFile = File.createTempFile("prefix", "extension", outputDir);

            outStream = new FileOutputStream(outputFile);
            image.compress(Bitmap.CompressFormat.PNG, 100, outStream);
            outStream.close();
            outStream = null;

            GraphRequest request = ShareInternalUtility.newUploadPhotoRequest(
                    ShareInternalUtility.MY_PHOTOS,
                    AccessToken.getCurrentAccessToken(),
                    outputFile,
                    "Test photo message",
                    null,
                    null);
            GraphResponse response = request.executeAndWait();
            assertNotNull(response);

            assertNull(response.getError());

            JSONObject result = response.getJSONObject();
            assertNotNull(result);
            assertNotNull(response.getRawResponse());
        } finally {
            if (outStream != null) {
                outStream.close();
            }
            if (outputFile != null) {
                outputFile.delete();
            }
        }
    }

    @LargeTest
    public void testExecuteUploadPhotoToAlbum() throws InterruptedException, JSONException {
        // first create an album
        Bundle params = new Bundle();
        params.putString("name", "Foo");
        GraphRequest request =
                new GraphRequest(
                        AccessToken.getCurrentAccessToken(),
                        "me/albums",
                        params,
                        HttpMethod.POST);

        GraphResponse response = request.executeAndWait();
        JSONObject jsonResponse = response.getJSONObject();
        assertNotNull(jsonResponse);
        String albumId = jsonResponse.optString("id");
        assertNotNull(albumId);

        // upload an image to the album
        Bitmap image = createTestBitmap(128);
        SharePhoto photo = new SharePhoto.Builder()
                .setBitmap(image)
                .setUserGenerated(true)
                .setParameter("caption", "Caption")
                .build();
        SharePhotoContent content = new SharePhotoContent.Builder().addPhoto(photo).build();
        final ShareApi shareApi = new ShareApi(content);
        shareApi.setGraphNode(albumId);
        final AtomicReference<String> imageId = new AtomicReference<>(null);
        getActivity().runOnUiThread(new Runnable() {
            @Override
            public void run() {
                shareApi.share(new FacebookCallback<Sharer.Result>() {
                    @Override
                    public void onSuccess(Sharer.Result result) {
                        imageId.set(result.getPostId());
                        notifyShareFinished();
                    }

                    @Override
                    public void onCancel() {
                        notifyShareFinished();
                    }

                    @Override
                    public void onError(FacebookException error) {
                        notifyShareFinished();
                    }

                    private void notifyShareFinished() {
                        synchronized (shareApi) {
                            shareApi.notifyAll();
                        }
                    }
                });
            }
        });

        synchronized (shareApi) {
            shareApi.wait(REQUEST_TIMEOUT_MILLIS);
        }
        assertNotNull(imageId.get());

        // now check to see if the image is in the album
        GraphRequest listRequest =
                new GraphRequest(AccessToken.getCurrentAccessToken(), albumId + "/photos");

        GraphResponse listResponse = listRequest.executeAndWait();
        JSONObject listObject = listResponse.getJSONObject();
        assertNotNull(listObject);
        JSONArray jsonList = listObject.optJSONArray("data");
        assertNotNull(jsonList);

        boolean found = false;
        for (int i = 0; i < jsonList.length(); i++) {
            JSONObject imageObject = jsonList.getJSONObject(i);
            if (imageId.get().equals(imageObject.optString("id"))) {
                found = true;
            }
        }
        assertTrue(found);
    }

    @LargeTest
    public void testUploadVideoFile() throws IOException, URISyntaxException {
        File tempFile = null;
        try {
            tempFile = createTempFileFromAsset("DarkScreen.mov");
            ShareVideo video = new ShareVideo.Builder()
                    .setLocalUrl(Uri.fromFile(tempFile))
                    .setParameter("caption", "Caption")
                    .build();
            ShareVideoContent content = new ShareVideoContent.Builder().setVideo(video).build();
            final ShareApi shareApi = new ShareApi(content);
            final AtomicReference<String> videoId = new AtomicReference<>(null);
            getActivity().runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    shareApi.share(new FacebookCallback<Sharer.Result>() {
                        @Override
                        public void onSuccess(Sharer.Result result) {
                            videoId.set(result.getPostId());
                            notifyShareFinished();
                        }

                        @Override
                        public void onCancel() {
                            notifyShareFinished();
                        }

                        @Override
                        public void onError(FacebookException error) {
                            notifyShareFinished();
                        }

                        private void notifyShareFinished() {
                            synchronized (shareApi) {
                                shareApi.notifyAll();
                            }
                        }
                    });
                }
            });

            synchronized (shareApi) {
                shareApi.wait(REQUEST_TIMEOUT_MILLIS);
            }
            assertNotNull(videoId.get());
        } catch (Exception ex) {
            fail();
        } finally {
            if (tempFile != null) {
                tempFile.delete();
            }
        }
    }

    @LargeTest
    public void testUploadVideoFileToUserId() throws IOException, URISyntaxException {
        File tempFile = null;
        try {
            GraphRequest meRequest =
                    GraphRequest.newMeRequest(AccessToken.getCurrentAccessToken(), null);
            GraphResponse meResponse = meRequest.executeAndWait();
            JSONObject meJson = meResponse.getJSONObject();
            assertNotNull(meJson);

            String userId = meJson.optString("id");
            assertNotNull(userId);

            tempFile = createTempFileFromAsset("DarkScreen.mov");
            ShareVideo video = new ShareVideo.Builder()
                    .setLocalUrl(Uri.fromFile(tempFile))
                    .setParameter("caption", "Caption")
                    .build();
            ShareVideoContent content = new ShareVideoContent.Builder().setVideo(video).build();
            final ShareApi shareApi = new ShareApi(content);
            shareApi.setGraphNode(userId);
            final AtomicReference<String> videoId = new AtomicReference<>(null);
            getActivity().runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    shareApi.share(new FacebookCallback<Sharer.Result>() {
                        @Override
                        public void onSuccess(Sharer.Result result) {
                            videoId.set(result.getPostId());
                            notifyShareFinished();
                        }

                        @Override
                        public void onCancel() {
                            notifyShareFinished();
                        }

                        @Override
                        public void onError(FacebookException error) {
                            notifyShareFinished();
                        }

                        private void notifyShareFinished() {
                            synchronized (shareApi) {
                                shareApi.notifyAll();
                            }
                        }
                    });
                }
            });

            synchronized (shareApi) {
                shareApi.wait(REQUEST_TIMEOUT_MILLIS);
            }
            assertNotNull(videoId.get());
        } catch (Exception ex) {
            fail();
        } finally {
            if (tempFile != null) {
                tempFile.delete();
            }
        }
    }

    @LargeTest
    public void testPostStatusUpdate() {
        JSONObject statusUpdate = createStatusUpdate("");

        JSONObject retrievedStatusUpdate = postGetAndAssert(
                AccessToken.getCurrentAccessToken(),
                "me/feed",
                statusUpdate);

        assertEquals(statusUpdate.optString("message"), retrievedStatusUpdate.optString("message"));
    }

    @LargeTest
    public void testCallbackIsCalled() {
        GraphRequest request = new GraphRequest(null, "4");

        final ArrayList<Boolean> calledBack = new ArrayList<Boolean>();
        request.setCallback(new GraphRequest.Callback() {
            @Override
            public void onCompleted(GraphResponse response) {
                calledBack.add(true);
            }
        });

        GraphResponse response = request.executeAndWait();
        assertNotNull(response);
        assertTrue(calledBack.size() == 1);
    }

    @LargeTest
    public void testOnProgressCallbackIsCalled() {
        Bitmap image = Bitmap.createBitmap(128, 128, Bitmap.Config.ALPHA_8);

        GraphRequest request = ShareInternalUtility.newUploadPhotoRequest(
                ShareInternalUtility.MY_PHOTOS,
                null,
                image,
                null,
                null,
                null);
        assertTrue(request != null);

        final ArrayList<Boolean> calledBack = new ArrayList<Boolean>();
        request.setCallback(new GraphRequest.OnProgressCallback() {
            @Override
            public void onCompleted(GraphResponse response) {
            }

            @Override
            public void onProgress(long current, long max) {
                calledBack.add(true);
            }
        });

        GraphResponse response = request.executeAndWait();
        assertNotNull(response);
        assertFalse(calledBack.isEmpty());
    }

    @LargeTest
    public void testLastOnProgressCallbackIsCalledOnce() {
        Bitmap image = Bitmap.createBitmap(128, 128, Bitmap.Config.ALPHA_8);

        GraphRequest request = ShareInternalUtility.newUploadPhotoRequest(
                ShareInternalUtility.MY_PHOTOS,
                null,
                image,
                null,
                null,
                null);
        assertTrue(request != null);

        final ArrayList<Boolean> calledBack = new ArrayList<Boolean>();
        request.setCallback(new GraphRequest.OnProgressCallback() {
            @Override
            public void onCompleted(GraphResponse response) {
            }

            @Override
            public void onProgress(long current, long max) {
                if (current == max) calledBack.add(true);
                else if (current > max) calledBack.clear();
            }
        });

        GraphResponse response = request.executeAndWait();
        assertNotNull(response);
        assertEquals(1, calledBack.size());
    }

    @LargeTest
    public void testBatchTimeoutIsApplied() {
        GraphRequest request = new GraphRequest(null, "me");
        GraphRequestBatch batch = new GraphRequestBatch(request);

        // We assume 5 ms is short enough to fail
        batch.setTimeout(1);

        List<GraphResponse> responses = GraphRequest.executeBatchAndWait(batch);
        assertNotNull(responses);
        assertTrue(responses.size() == 1);
        GraphResponse response = responses.get(0);
        assertNotNull(response);
        assertNotNull(response.getError());
    }

    @LargeTest
    public void testBatchTimeoutCantBeNegative() {
        try {
            GraphRequestBatch batch = new GraphRequestBatch();
            batch.setTimeout(-1);
            fail();
        } catch (IllegalArgumentException ex) {
        }
    }

    @LargeTest
    public void testCantUseComplexParameterInGetRequest() {
        Bundle parameters = new Bundle();
        parameters.putShortArray("foo", new short[1]);

        GraphRequest request = new GraphRequest(
                AccessToken.getCurrentAccessToken(),
                "me",
                parameters,
                HttpMethod.GET,
                new ExpectFailureCallback());
        GraphResponse response = request.executeAndWait();

        FacebookRequestError error = response.getError();
        assertNotNull(error);
        FacebookException exception = error.getException();
        assertNotNull(exception);
        assertTrue(exception.getMessage().contains("short[]"));
    }

    private final Location SEATTLE_LOCATION = new Location("") {
        {
            setLatitude(47.6097);
            setLongitude(-122.3331);
        }
    };

    @LargeTest
    public void testPaging() {
        final List<JSONObject> returnedPlaces = new ArrayList<JSONObject>();
        GraphRequest request = GraphRequest
                .newPlacesSearchRequest(
                        AccessToken.getCurrentAccessToken(),
                        SEATTLE_LOCATION,
                        1000,
                        3,
                        null,
                        new GraphRequest.GraphJSONArrayCallback() {
                            @Override
                            public void onCompleted(JSONArray places, GraphResponse response) {
                                if (places == null) {
                                    assertNotNull(places);
                                }
                                for (int i = 0; i < places.length(); ++i) {
                                    returnedPlaces.add(places.optJSONObject(i));
                                }
                            }
                        });
        GraphResponse response = request.executeAndWait();

        assertNull(response.getError());
        assertNotNull(response.getJSONObject());
        assertNotSame(0, returnedPlaces.size());

        returnedPlaces.clear();

        GraphRequest nextRequest = response.getRequestForPagedResults(GraphResponse.PagingDirection.NEXT);
        assertNotNull(nextRequest);

        nextRequest.setCallback(request.getCallback());
        response = nextRequest.executeAndWait();

        assertNull(response.getError());
        assertNotNull(response.getJSONObject());
        assertNotSame(0, returnedPlaces.size());

        returnedPlaces.clear();

        GraphRequest previousRequest = response.getRequestForPagedResults(GraphResponse.PagingDirection.PREVIOUS);
        assertNotNull(previousRequest);

        previousRequest.setCallback(request.getCallback());
        response = previousRequest.executeAndWait();

        assertNull(response.getError());
        assertNotNull(response.getJSONObject());
        assertNotSame(0, returnedPlaces.size());
    }
}


File: facebook/tests/src/com/facebook/login/LoginClientTests.java
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
import android.test.suitebuilder.annotation.LargeTest;
import android.test.suitebuilder.annotation.MediumTest;

import com.facebook.AccessToken;
import com.facebook.FacebookTestCase;
import com.facebook.GraphRequest;
import com.facebook.GraphRequestBatch;
import com.facebook.GraphRequestBatchBridge;
import com.facebook.GraphResponse;
import com.facebook.GraphResponseBridge;
import com.facebook.TestBlocker;
import com.facebook.TestUtils;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.*;
import java.util.*;

public class LoginClientTests extends FacebookTestCase {
    private static final Set<String> PERMISSIONS = new HashSet<String>(
            Arrays.asList("go outside", "come back in"));

    class MockLoginClient extends LoginClient {
        Result result;
        boolean triedNextHandler = false;

        MockLoginClient(Fragment fragment) {
            super(fragment);
        }

        Request getRequest() {
            return pendingRequest;
        }

        void setRequest(Request request) {
            pendingRequest = request;
        }

        @Override
        void complete(Result result) {
            this.result = result;
        }

        @Override
        void tryNextHandler() {
            triedNextHandler = true;
        }
    }

    LoginClient.Request createRequest() {
        return new LoginClient.Request(
                LoginBehavior.SSO_WITH_FALLBACK,
                PERMISSIONS,
                DefaultAudience.FRIENDS,
                "1234",
                null
        );
    }

    class MockValidatingLoginClient extends MockLoginClient {
        private final HashMap<String, String> mapAccessTokenToFbid = new HashMap<String, String>();
        private Set<String> permissionsToReport = new HashSet<String>();
        private TestBlocker blocker;

        public MockValidatingLoginClient(Fragment fragment, TestBlocker blocker) {
            super(fragment);
            this.blocker = blocker;
        }

        public void addAccessTokenToFbidMapping(String accessToken, String fbid) {
            mapAccessTokenToFbid.put(accessToken, fbid);
        }

        public void setPermissionsToReport(Set<String> permissionsToReport) {
            this.permissionsToReport = permissionsToReport;
        }

        @Override
        void complete(Result result) {
            super.complete(result);
            blocker.signal();
        }
    }

    static final String USER_1_FBID = "user1";
    static final String USER_1_ACCESS_TOKEN = "An access token for user 1";
    static final String USER_2_FBID = "user2";
    static final String USER_2_ACCESS_TOKEN = "An access token for user 2";
    static final String APP_ID = "1234";

    LoginClient.Request createNewPermissionRequest() {
        return new LoginClient.Request(
                LoginBehavior.SSO_WITH_FALLBACK,
                PERMISSIONS,
                DefaultAudience.FRIENDS,
                "1234",
                null
        );
    }

    @LargeTest
    public void testReauthorizationWithSameFbidSucceeds() throws Exception {
        TestBlocker blocker = getTestBlocker();

        MockValidatingLoginClient client = new MockValidatingLoginClient(null, blocker);
        client.addAccessTokenToFbidMapping(USER_1_ACCESS_TOKEN, USER_1_FBID);
        client.addAccessTokenToFbidMapping(USER_2_ACCESS_TOKEN, USER_2_FBID);
        client.setPermissionsToReport(PERMISSIONS);

        LoginClient.Request request = createNewPermissionRequest();
        client.setRequest(request);

        AccessToken token = new AccessToken(
                USER_1_ACCESS_TOKEN,
                APP_ID,
                USER_1_FBID,
                PERMISSIONS,
                null,
                null,
                null,
                null);
        AccessToken.setCurrentAccessToken(token);
        LoginClient.Result result = LoginClient.Result.createTokenResult(request, token);

        client.completeAndValidate(result);

        blocker.waitForSignals(1);

        assertNotNull(client.result);
        assertEquals(LoginClient.Result.Code.SUCCESS, client.result.code);

        AccessToken resultToken = client.result.token;
        assertNotNull(resultToken);
        assertEquals(USER_1_ACCESS_TOKEN, resultToken.getToken());

        // We don't care about ordering.
        assertEquals(new HashSet<String>(PERMISSIONS), new HashSet<String>(resultToken.getPermissions()));
    }

    @LargeTest
    public void testReauthorizationWithDifferentFbidsFails() throws Exception {
        TestBlocker blocker = getTestBlocker();

        MockValidatingLoginClient client = new MockValidatingLoginClient(null, blocker);
        client.addAccessTokenToFbidMapping(USER_1_ACCESS_TOKEN, USER_1_FBID);
        client.addAccessTokenToFbidMapping(USER_2_ACCESS_TOKEN, USER_2_FBID);
        client.setPermissionsToReport(PERMISSIONS);

        LoginClient.Request request = createNewPermissionRequest();
        client.setRequest(request);

        AccessToken userOneToken = new AccessToken(
                USER_1_ACCESS_TOKEN,
                APP_ID,
                USER_1_FBID,
                PERMISSIONS,
                null,
                null,
                null,
                null);
        AccessToken.setCurrentAccessToken(userOneToken);

        AccessToken userTwoToken = new AccessToken(
                USER_2_ACCESS_TOKEN,
                APP_ID,
                USER_2_FBID,
                PERMISSIONS,
                null,
                null,
                null,
                null);
        LoginClient.Result result = LoginClient.Result.createTokenResult(request, userTwoToken);

        client.completeAndValidate(result);

        blocker.waitForSignals(1);

        assertNotNull(client.result);
        assertEquals(LoginClient.Result.Code.ERROR, client.result.code);

        assertNull(client.result.token);
        assertNotNull(client.result.errorMessage);
    }
}


File: samples/SwitchUserSample/src/com/example/switchuser/SettingsFragment.java
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

package com.example.switchuser;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.os.Bundle;
import android.support.v4.app.ListFragment;
import android.view.*;
import android.widget.*;

import com.facebook.AccessToken;
import com.facebook.CallbackManager;
import com.facebook.FacebookCallback;
import com.facebook.FacebookException;
import com.facebook.FacebookSdk;
import com.facebook.Profile;
import com.facebook.ProfileTracker;
import com.facebook.login.LoginBehavior;
import com.facebook.login.LoginManager;
import com.facebook.login.LoginResult;
import com.facebook.login.widget.ProfilePictureView;

import java.util.ArrayList;
import java.util.Arrays;

public class SettingsFragment extends ListFragment {

    public static final String TAG = "SettingsFragment";
    private static final String CURRENT_SLOT_KEY = "CurrentSlot";

    private SlotManager slotManager;
    private Menu optionsMenu;
    private CallbackManager callbackManager;
    private ProfileTracker profileTracker;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        slotManager = new SlotManager();
        slotManager.restore(
                getActivity(),
                savedInstanceState != null ?
                        savedInstanceState.getInt(CURRENT_SLOT_KEY, SlotManager.NO_SLOT) :
                        SlotManager.NO_SLOT);
        ArrayList<Slot> slotList = new ArrayList<Slot>(
                Arrays.asList(slotManager.getAllSlots()));

        Slot currentSlot = slotManager.getSelectedSlot();
        if (currentSlot != null && currentSlot.getAccessToken() != null) {
            AccessToken.setCurrentAccessToken(currentSlot.getAccessToken());
        }

        setListAdapter(new SlotAdapter(slotList));
        setHasOptionsMenu(true);
        setUpCallbacks();
        currentUserChanged();
    }

    @Override
    public void onCreateOptionsMenu(Menu menu, MenuInflater inflater) {
        super.onCreateOptionsMenu(menu, inflater);
        inflater.inflate(R.menu.context_settings, menu);
        optionsMenu = menu;
        updateMenuVisibility();
    }

    private void setUpCallbacks() {
        callbackManager = CallbackManager.Factory.create();
        LoginManager manager = LoginManager.getInstance();
        manager.registerCallback(callbackManager, new FacebookCallback<LoginResult>() {
            @Override
            public void onSuccess(LoginResult loginResult) {
                Profile.fetchProfileForCurrentAccessToken();
            }

            @Override
            public void onError(FacebookException exception) {
                AccessToken.setCurrentAccessToken(null);
                currentUserChanged();
            }

            @Override
            public void onCancel() {
                AccessToken.setCurrentAccessToken(null);
                currentUserChanged();
            }
        });

        profileTracker = new ProfileTracker() {
            @Override
            protected void onCurrentProfileChanged(Profile oldProfile, Profile currentProfile) {
                Slot currentSlot = slotManager.getSelectedSlot();
                AccessToken currentAccessToken = AccessToken.getCurrentAccessToken();
                if(currentSlot != null && currentAccessToken != null && currentProfile != null) {
                    currentSlot.setUserInfo(
                            new UserInfo(currentProfile.getName(), currentAccessToken));
                    currentUserChanged();
                }
            }
        };
    }

    @Override
    public void onListItemClick(ListView l, View view, int position, long id) {
        slotManager.setCurrentUserSlot(position);
        Slot newSlot = slotManager.getSelectedSlot();
        if (newSlot.getAccessToken() == null) {
            final LoginManager manager = LoginManager.getInstance();
            manager.setLoginBehavior(newSlot.getLoginBehavior());
            manager.logInWithReadPermissions(this, null);
        } else {
            AccessToken.setCurrentAccessToken(newSlot.getAccessToken());
        }
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        Slot slot = slotManager.getSelectedSlot();

        if (item.getItemId() == R.id.menu_item_clear_slot) {
            if (slot.getUserId() != null) {
                // Clear out data that this app stored in the cache
                // Not calling Session.closeAndClearTokenInformation() because we have
                // additional data stored in the cache.
                slot.clear();
                if (slot == slotManager.getSelectedSlot()) {
                    slotManager.setCurrentUserSlot(SlotManager.NO_SLOT);
                }

                currentUserChanged();
            }
            return true;
        }

        return super.onContextItemSelected(item);
    }

    @Override
    public void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        outState.putInt(CURRENT_SLOT_KEY, slotManager.getSelectedSlotNumber());
    }

    @Override
    public void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        callbackManager.onActivityResult(requestCode, resultCode, data);
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        profileTracker.stopTracking();
    }

    private void updateMenuVisibility() {
        if (optionsMenu != null) {
            if (slotManager.getSelectedSlot() == null) {
                optionsMenu.setGroupVisible(0, false);
            } else if (optionsMenu != null) {
                optionsMenu.setGroupVisible(0, true);
            }
        }
    }

    private void currentUserChanged() {
        if (slotManager == null) {
            // Fragment has not had onCreate called yet.
            return;
        }

        updateMenuVisibility();
        updateListView();
        Slot currentSlot = slotManager.getSelectedSlot();
        AccessToken currentToken = (currentSlot != null) ? currentSlot.getAccessToken() : null;
        AccessToken.setCurrentAccessToken(currentToken);
    }

    private void updateListView() {
        SlotAdapter adapter = (SlotAdapter) getListAdapter();

        // Adapter will be null if the list is not shown
        if (adapter != null) {
            adapter.notifyDataSetChanged();
        }
    }

    private class SlotManager {
        static final int NO_SLOT = -1;

        private final static int MAX_SLOTS = 4;

        private static final String SETTINGS_CURRENT_SLOT_KEY = "CurrentSlot";
        private static final String SETTINGS_NAME = "UserManagerSettings";

        private SharedPreferences settings;
        private int selectedSlotNumber = NO_SLOT;

        private Slot[] slots;

        public void restore(Context context, int oldSelectedSlot) {
            if (context == null) {
                throw new IllegalArgumentException("context cannot be null");
            }

            slots = new Slot[MAX_SLOTS];
            for (int i = 0; i < MAX_SLOTS; i++) {
                LoginBehavior loginBehavior = (i == 0) ?
                        LoginBehavior.SSO_WITH_FALLBACK :
                        LoginBehavior.SUPPRESS_SSO;
                slots[i] = new Slot(i, loginBehavior);
            }

            // Restore the last known state from when the app ran last.
            settings = FacebookSdk.getApplicationContext().getSharedPreferences(
                    SETTINGS_NAME, Context.MODE_PRIVATE);
            int savedSlotNumber = settings.getInt(SETTINGS_CURRENT_SLOT_KEY, NO_SLOT);
            if (savedSlotNumber != NO_SLOT && savedSlotNumber != oldSelectedSlot) {
                // This will trigger the full flow of login
                setCurrentUserSlot(savedSlotNumber);
            } else {
                // We already knew which slot was selected. So don't notify that a new slot was
                // selected since that will log out and start login process. And
                // doing so will have the effect of clearing out state like the profile pic.
                setCurrentUserSlot(savedSlotNumber);
            }
        }

        public Slot getSelectedSlot() {
            if (selectedSlotNumber == NO_SLOT) {
                return null;
            } else {
                return getSlot(selectedSlotNumber);
            }
        }

        public int getSelectedSlotNumber() {
            return selectedSlotNumber;
        }

        public void setCurrentUserSlot(int slot) {
            if (slot != selectedSlotNumber) {
                // Store the selected slot number for when the app is closed and restarted
                settings.edit().putInt(SETTINGS_CURRENT_SLOT_KEY, slot).apply();
                selectedSlotNumber = slot;
                currentUserChanged();
            }
        }

        private Slot[] getAllSlots() {
            return slots;
        }

        private Slot getSlot(int slot) {
            validateSlot(slot);
            return slots[slot];
        }

        private void validateSlot(int slot) {
            if (slot <= NO_SLOT || slot >= MAX_SLOTS) {
                throw new IllegalArgumentException(
                        String.format("Choose a slot between 0 and %d inclusively", MAX_SLOTS - 1));
            }
        }
    }

    private class SlotAdapter extends ArrayAdapter<Slot> {

        public SlotAdapter(ArrayList<Slot> slots) {
            super(getActivity(), android.R.layout.simple_list_item_1, slots);
        }

        @Override
        public View getView(final int position, View convertView, ViewGroup parent) {
            if (null == convertView) {
                convertView = getActivity().getLayoutInflater()
                        .inflate(R.layout.list_item_user, parent, false);
            }

            Slot slot = getItem(position);
            if (slot.getLoginBehavior() != LoginBehavior.SUPPRESS_SSO) {
                convertView.setBackgroundColor(Color.argb(50, 255, 255, 255));
            }

            String userName = slot.getUserName();
            if (userName == null) {
                userName = getString(R.string.empty_slot);
            }

            String userId = slot.getUserId();
            ProfilePictureView profilePic = (ProfilePictureView) convertView.findViewById(
                    R.id.slotPic);
            if (userId != null) {
                profilePic.setProfileId(userId);
            } else {
                profilePic.setProfileId(null);
            }

            TextView userNameTextView = (TextView) convertView.findViewById(
                    R.id.slotUserName);
            userNameTextView.setText(userName);

            final CheckBox currentUserCheckBox = (CheckBox) convertView.findViewById(
                    R.id.currentUserIndicator);
            currentUserCheckBox.setChecked(
                    slotManager.getSelectedSlot() == slot
                            && slot.getUserInfo() != null);
            currentUserCheckBox.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    if (currentUserCheckBox.isChecked()) {
                        slotManager.setCurrentUserSlot(position);
                    } else {
                        slotManager.setCurrentUserSlot(SlotManager.NO_SLOT);
                    }
                    SlotAdapter adapter = (SlotAdapter) getListAdapter();
                    adapter.notifyDataSetChanged();
                }
            });

            currentUserCheckBox.setEnabled(slot.getAccessToken() != null);

            return convertView;
        }

    }
}
