Refactoring Types: ['Extract Superclass', 'Move Class']
RestTest.java
/**
 * This file is part of Graylog.
 *
 * Graylog is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Graylog is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Graylog.  If not, see <http://www.gnu.org/licenses/>.
 */
package integration;

import com.github.zafarkhaja.semver.Version;
import com.google.common.base.CaseFormat;
import com.google.common.collect.Sets;
import com.google.common.io.Resources;
import com.jayway.restassured.RestAssured;
import com.jayway.restassured.builder.RequestSpecBuilder;
import com.jayway.restassured.config.MatcherConfig;
import com.jayway.restassured.matcher.ResponseAwareMatcher;
import com.jayway.restassured.response.Response;
import integration.util.graylog.GraylogControl;
import org.hamcrest.BaseMatcher;
import org.hamcrest.Description;
import org.hamcrest.Matcher;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.testng.IHookCallBack;
import org.testng.IHookable;
import org.testng.ITestResult;
import org.testng.SkipException;
import org.testng.annotations.BeforeSuite;
import org.testng.annotations.Listeners;

import java.io.IOException;
import java.net.URL;
import java.util.Collections;
import java.util.Map;
import java.util.Set;

import static com.jayway.restassured.RestAssured.given;
import static com.jayway.restassured.RestAssured.preemptive;
import static com.jayway.restassured.http.ContentType.JSON;

@Listeners({BaseRestTest.class, SeedListener.class})
public class BaseRestTest implements IHookable {
    private static final Logger log = LoggerFactory.getLogger(BaseRestTest.class);
    private static Version serverUnderTestVersion;

    /**
     * Returns a {@link com.jayway.restassured.matcher.ResponseAwareMatcher} which checks that all given keys are present,
     * and that no additional keys are in the given path.
     * Given this JSON
     * <pre>
     *     {
     *      "version": "2.0.0",
     *      "codename": "foo"
     *     }
     * </pre>
     * to validate that it contains the keys <code>version</code> and <code>codename</code> and only those keys, use
     * <pre>
     *     given()
     *        .when()
     *          .get("/")
     *        .then()
     *          .body(".", containsAllKeys("codename", "version"));
     * </pre>
     * If any of the keys are missing, or there are other keys in the JSON document, the matcher will fail.
     * @param keys the keys that need to be present
     * @return matcher
     */
    public static ResponseAwareMatcher<Response> containsAllKeys(String... keys) {
        return new KeysPresentMatcher(keys);
    }

    @BeforeSuite
    public void setupTestSuite() {
        if (System.getProperty("gl2.integration.tests") == null) {
            throw new SkipException("Not running REST API integration tests. Add -Dgl2.integration.tests to run them.");
        }

        GraylogControl graylogController = new GraylogControl();
        URL url = graylogController.getServerUrl();
        RestAssured.baseURI = url.getProtocol() + "://" + url.getHost();
        RestAssured.port = url.getPort();
        String[] userInfo = url.getUserInfo().split(":");
        RestAssured.authentication = preemptive().basic(userInfo[0], userInfo[1]);

        // we want all the details for failed tests
        RestAssured.enableLoggingOfRequestAndResponseIfValidationFails();

        // we want to be able to describe mismatches in a custom way.
        final MatcherConfig matcherConfig = RestAssured.config().getMatcherConfig().errorDescriptionType(MatcherConfig.ErrorDescriptionType.HAMCREST);
        RestAssured.config = RestAssured.config().matcherConfig(matcherConfig);

        // we usually send and receive JSON, so we preconfigure for that.
        RestAssured.requestSpecification = new RequestSpecBuilder().build().accept(JSON).contentType(JSON);

        // immediately query the server for its version number, we need it to be able to process the RequireVersion annotations.
        given().when()
                .get("/system")
                .then()
                .body("version", new BaseMatcher<Object>() {
                    @Override
                    public boolean matches(Object item) {
                        if (item instanceof String) {
                            String str = (String) item;
                            try {
                                // clean our slightly non-semver version number
                                str = str.replaceAll("\\(.*?\\)", "").trim();
                                serverUnderTestVersion = Version.valueOf(str);
                                return true;
                            } catch (RuntimeException e) {
                                return false;
                            }
                        }
                        return false;
                    }

                    @Override
                    public void describeTo(Description description) {
                        description.appendText("parse the system under test's version number");
                    }
                });
        if (serverUnderTestVersion == null) {
            throw new RuntimeException("");
        }
    }

    /**
     * Use this method to load a json file from the classpath.
     * <p>
     *     It will be looked for relative to the caller's object's class.
     * </p>
     * For example if you have a class in the package <code>integration.system.users</code> and call <code>jsonResource("abc.json")</code>
     * on the instance of your test class (i.e. <code>this</code>), it will look for a file in <code>resources/integration/system/inputs/abc.json</code>.
     * <p>
     *     If the file does not exist or cannot be read, a {@link java.lang.IllegalStateException} will be raised which should cause your test to fail.
     * </p>
     * @param relativeFileName the name of the file relative to the caller's class.
     * @return the bytes in that file.
     */
    protected byte[] jsonResource(String relativeFileName) {
        final URL resource = Resources.getResource(this.getClass(), relativeFileName);
        if (resource == null) {
            throw new IllegalStateException("Unable to find JSON resource " + relativeFileName + " for test. This is a bug.");
        }
        try {
            return Resources.toByteArray(resource);
        } catch (IOException e) {
            throw new IllegalStateException("Unable to read JSON resource " + relativeFileName + " for test. This is a bug.");
        }
    }

    /**
     * Same as @{link #jsonResource} but guesses the file name from the caller's method name. Be careful when refactoring.
     * @return the bytes in that file
     */
    protected byte[] jsonResourceForMethod() {
        final StackTraceElement[] stackTraceElements = Thread.currentThread().getStackTrace();
        final String testMethodName = stackTraceElements[2].getMethodName();

        final String filename = CaseFormat.LOWER_CAMEL.to(CaseFormat.LOWER_HYPHEN, testMethodName);

        return jsonResource(filename + ".json");
    }

    @Override
    public void run(IHookCallBack callBack, ITestResult testResult) {
        log.trace("Running version check hook on test {}", testResult.getMethod());

        final RequiresVersion methodAnnotation = testResult.getMethod().getConstructorOrMethod()
                .getMethod().getAnnotation(RequiresVersion.class);
        final RequiresVersion classAnnotation = (RequiresVersion) testResult.getTestClass().getRealClass().getAnnotation(RequiresVersion.class);
        String versionRequirement = null;
        if (classAnnotation != null) {
            versionRequirement = classAnnotation.value();
        } else if (methodAnnotation != null) {
            versionRequirement = methodAnnotation.value();
        }

        log.info("Checking {} against version {}: ", versionRequirement, serverUnderTestVersion, versionRequirement != null ? serverUnderTestVersion.satisfies(versionRequirement) : "skipped");
        if (serverUnderTestVersion != null && versionRequirement != null && !serverUnderTestVersion.satisfies(versionRequirement)) {

            log.info("Skipping test <{}> because its version requirement <{}> does not meet the server's API version {}",
                     testResult.getName(), versionRequirement, serverUnderTestVersion);
            throw new SkipException("API Version " + serverUnderTestVersion +
                                            " does not meet test requirement " + versionRequirement);
        }
        callBack.runTestMethod(testResult);
    }

    private static class KeysPresentMatcher extends ResponseAwareMatcher<Response> {
        private final Set<String> keys = Sets.newHashSet();
        public KeysPresentMatcher(String... keys) {
            Collections.addAll(this.keys, keys);
        }

        @Override
        public Matcher<?> matcher(Response response) throws Exception {
            return new BaseMatcher<Response>() {

                private Sets.SetView difference;

                @Override
                public boolean matches(Object item) {
                    if (item instanceof Map) {
                        final Set keySet = ((Map) item).keySet();
                        difference = Sets.symmetricDifference(keySet, keys);
                        return difference.isEmpty();
                    }
                    return false;
                }

                @Override
                public void describeTo(Description description) {
                    description.appendText("JSON Contains all keys: ").appendValueList("[", ", ", "]", keys);
                }

                @Override
                public void describeMismatch(Object item, Description description) {
                    super.describeMismatch(item, description);
                    description.appendValueList(" has extra or missing keys: [", ", ", "]", difference);
                }
            };
        }
    }
}


File: integration-tests/src/test/java/integration/SeedListener.java
/**
 * This file is part of Graylog.
 *
 * Graylog is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Graylog is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Graylog.  If not, see <http://www.gnu.org/licenses/>.
 */
package integration;

import integration.util.graylog.GraylogControl;
import integration.util.mongodb.MongodbSeed;
import org.testng.ITestContext;
import org.testng.ITestListener;
import org.testng.ITestResult;

public class SeedListener implements ITestListener {

    @Override
    public void onTestStart(ITestResult iTestResult) {
        final MongoDbSeed classAnnotation = iTestResult.getMethod().getConstructorOrMethod().getMethod().getAnnotation(MongoDbSeed.class);
        if (classAnnotation != null) {
            MongodbSeed mongodbSeed = new MongodbSeed();
            GraylogControl graylogController = new GraylogControl();
            String nodeId = graylogController.getNodeId();
            graylogController.stopServer();
            mongodbSeed.loadDataset(classAnnotation.location(), classAnnotation.database(), nodeId);
            graylogController.startServer();
        }
    }

    @Override
    public void onTestSuccess(ITestResult iTestResult) {

    }

    @Override
    public void onTestFailure(ITestResult iTestResult) {

    }

    @Override
    public void onTestSkipped(ITestResult iTestResult) {

    }

    @Override
    public void onTestFailedButWithinSuccessPercentage(ITestResult iTestResult) {

    }

    @Override
    public void onStart(ITestContext iTestContext) {

    }

    @Override
    public void onFinish(ITestContext iTestContext) {

    }
}


File: integration-tests/src/test/java/integration/counts/TotalTest.java
/**
 * This file is part of Graylog.
 *
 * Graylog is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Graylog is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Graylog.  If not, see <http://www.gnu.org/licenses/>.
 */
package integration.counts;

import integration.BaseRestTest;
import org.testng.annotations.Test;

import static com.jayway.restassured.RestAssured.given;

public class TotalTest extends BaseRestTest {
    @Test
    public void total() {
        given()
                .when()
                    .get("/count/total")
                .then()
                    .statusCode(200)
                    .body(".", containsAllKeys("events"));
    }
}


File: integration-tests/src/test/java/integration/system/SystemTest.java
/**
 * This file is part of Graylog.
 *
 * Graylog is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Graylog is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Graylog.  If not, see <http://www.gnu.org/licenses/>.
 */
package integration.system;

import integration.BaseRestTest;
import org.testng.annotations.Test;

import static com.jayway.restassured.RestAssured.given;

public class SystemTest extends BaseRestTest {

    @Test
    public void system() {
        given()
                .when()
                    .get("/system")
                .then()
                    .body(".", containsAllKeys(
                            "codename",
                            "facility",
                            "hostname",
                            "is_processing",
                            "lb_status",
                            "lifecycle",
                            "server_id",
                            "started_at",
                            "timezone",
                            "version"
                    ));
    }

}


File: integration-tests/src/test/java/integration/system/collectors/CollectorsTest.java
/**
 * This file is part of Graylog.
 *
 * Graylog is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Graylog is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Graylog.  If not, see <http://www.gnu.org/licenses/>.
 */
package integration.system.collectors;

import integration.BaseRestTest;
import integration.RequiresVersion;
import org.joda.time.DateTime;
import org.testng.annotations.Test;

import java.util.List;

import static com.jayway.restassured.RestAssured.get;
import static com.jayway.restassured.RestAssured.given;
import static com.jayway.restassured.path.json.JsonPath.from;
import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.is;
import static org.hamcrest.Matchers.notNullValue;
import static org.assertj.jodatime.api.Assertions.assertThat;

@RequiresVersion(">=1.1.0")
public class CollectorsTest extends BaseRestTest {
    private final String resourcePrefix = "/system/collectors";

    @Test
    public void testRegisterCollector() throws Exception {
        given().when()
                    .header("X-Graylog-Collector-Version", "0.0.0")
                    .body(jsonResourceForMethod())
                    .put(getResourceEndpoint("collectorId"))
                .then()
                    .statusCode(202);
    }

    @Test
    public void testRegisterInvalidCollector() throws Exception {
        given().when()
                    .header("X-Graylog-Collector-Version", "0.0.0")
                    .body(jsonResourceForMethod())
                    .put(getResourceEndpoint("invalidCollector"))
                .then()
                    .statusCode(400);
    }

    @Test
    public void testListCollectors() throws Exception {
        given().when()
                    .get(resourcePrefix)
                .then()
                    .statusCode(200)
                    .assertThat().body("collectors", notNullValue());
    }

    @Test
    public void testGetCollector() throws Exception {
        given().when()
                    .header("X-Graylog-Collector-Version", "0.0.0")
                    .body(jsonResourceForMethod())
                    .put(getResourceEndpoint("getCollectorTest"))
                .then()
                    .statusCode(202);

        given().when()
                    .get(resourcePrefix + "/getCollectorTest")
                .then()
                    .statusCode(200)
                    .assertThat()
                        .body("id", is("getCollectorTest"))
                        .body(".", containsAllKeys("id", "node_id", "node_details", "last_seen", "active"))
                        .body("active", is(true));
    }

    @Test
    public void testTouchCollector() throws Exception {
        final String collectorId = "testTouchCollectorId";

        given().when()
                    .header("X-Graylog-Collector-Version", "0.0.0")
                    .body(jsonResourceForMethod())
                    .put(getResourceEndpoint(collectorId))
                .then()
                    .statusCode(202);

        final DateTime lastSeenBefore = getLastSeenForCollectorId(collectorId);

        given().when()
                    .header("X-Graylog-Collector-Version", "0.0.0")
                    .body(jsonResource("test-register-collector.json"))
                    .put(getResourceEndpoint(collectorId))
                .then()
                    .statusCode(202);

        final DateTime lastSeenAfterOtherRegistration = getLastSeenForCollectorId(collectorId);

        given().when()
                    .header("X-Graylog-Collector-Version", "0.0.0")
                    .body(jsonResourceForMethod())
                    .put(getResourceEndpoint(collectorId))
                .then()
                    .statusCode(202);

        final DateTime lastSeenAfter = getLastSeenForCollectorId(collectorId);

        assertThat(lastSeenBefore).isEqualTo(lastSeenAfterOtherRegistration);
        assertThat(lastSeenBefore)
                .isNotEqualTo(lastSeenAfter)
                .isBefore(lastSeenAfter);
    }

    private DateTime getLastSeenForCollectorId(String collectorId) {
        final String content = get(resourcePrefix).asString();
        final List<String> lastSeenStringsBefore = from(content).get("collectors.findAll { collector -> collector.id == \"" + collectorId + "\" }.last_seen");
        assertThat(lastSeenStringsBefore).isNotEmpty().hasSize(1);

        return DateTime.parse(lastSeenStringsBefore.get(0));
    }

    private String getResourceEndpoint(String collectorId) {
        return resourcePrefix + "/" + collectorId;
    }
}


File: integration-tests/src/test/java/integration/system/grok/GrokTests.java
/**
 * This file is part of Graylog.
 *
 * Graylog is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Graylog is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Graylog.  If not, see <http://www.gnu.org/licenses/>.
 */
package integration.system.grok;

import com.jayway.restassured.response.ValidatableResponse;
import integration.BaseRestTest;
import org.testng.annotations.Test;

import static com.jayway.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.notNullValue;

public class GrokTests extends BaseRestTest {

    private String id;

    @Test
    public void createGrokPattern() {
        final ValidatableResponse validatableResponse = given().when()
                .body(jsonResourceForMethod()).post("/system/grok")
                .then()
                .statusCode(201)
                .statusLine(notNullValue());

        id = validatableResponse.extract().body().jsonPath().get("id").toString();
        validatableResponse
            .body(".", containsAllKeys(
                    "id",
                    "name",
                    "pattern"
            ));
    }
    
    @Test(dependsOnMethods = "createGrokPattern")
    public void listPatterns() {
        // we have just created one pattern, so we should find it again.
        given().when()
                .get("/system/grok/{patternid}", id)
            .then()
                .statusCode(200)
                .statusLine(notNullValue())
            .body(".", containsAllKeys(
                    "id",
                    "name",
                    "pattern"
            ));
    }
    
    @Test(dependsOnMethods = "listPatterns")
    public void deletePattern() {
        given()
            .when()
                .delete("/system/grok/{patternid}", id)
            .then()
                .statusCode(204);
        
    }
}


File: integration-tests/src/test/java/integration/system/inputs/InputsTest.java
/**
 * This file is part of Graylog.
 *
 * Graylog is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Graylog is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Graylog.  If not, see <http://www.gnu.org/licenses/>.
 */
package integration.system.inputs;

import integration.BaseRestTest;
import integration.MongoDbSeed;
import integration.RequiresVersion;
import org.testng.annotations.Test;

import static com.jayway.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.notNullValue;

@RequiresVersion(">=0.90.0")
public class InputsTest extends BaseRestTest {

    @Test
    @MongoDbSeed(location = "graylog", database = "graylog2")
    public void createInputTest() {

        given().when()
                .body(jsonResourceForMethod()).post("/system/inputs")
                .then()
                    .statusCode(400).statusLine(notNullValue());
    }

    @Test(dependsOnMethods = "createInputTest")
    public void listInput() {
        given().when().get("/system/inputs").then().statusCode(200);
    }
}



File: integration-tests/src/test/java/integration/util/graylog/GraylogControl.java
/**
 * This file is part of Graylog.
 *
 * Graylog is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Graylog is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Graylog.  If not, see <http://www.gnu.org/licenses/>.
 */
package integration.util.graylog;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.commons.codec.binary.Base64;
import org.apache.http.client.utils.URIBuilder;
import org.testng.SkipException;

import java.io.IOException;
import java.io.InputStream;
import java.net.*;

public class GraylogControl {
    private URL url;
    private static final int HTTP_TIMEOUT = 1000;

    public GraylogControl() {
        this.url = getServerUrl();
    }

    public GraylogControl(URL url) {
        this.url = url;
    }

    public void startServer() {
        System.out.println("Starting Graylog server...");
        try {
            URL startupUrl = new URL("http", url.getHost(), 5000, "/sv/up/graylog-server");

            doRequest(startupUrl);
            waitForStartup();
        } catch (MalformedURLException e) {
            e.printStackTrace();
        }
    }

    public void stopServer() {
        System.out.println("Stoping Graylog server...");
        try {
            URL shutdownUrl = new URL("http", url.getHost(), 5000, "/sv/down/graylog-server");

            doRequest(shutdownUrl);
            waitForShutdown();
        } catch (MalformedURLException e) {
            e.printStackTrace();
        }

    }
    public void restartServer() {
        System.out.println("Reestarting Graylog server...");
        stopServer();
        startServer();
    }

    public void waitForStartup() {
        try {
            URL apiCheckUrl = new URL(url, "/system/stats");
            URL svCheckUrl = new URL("http", url.getHost(), 5000, "/sv/status/graylog-server");

            Boolean serverRunning = false;
            while (!serverRunning) {
                Boolean apiAvailable = doRequest(apiCheckUrl);
                Boolean svStatusUp = doRequest(svCheckUrl);
                serverRunning = apiAvailable && svStatusUp;

                sleep(1000);
            }
        } catch (MalformedURLException e) {
            e.printStackTrace();
        }
    }

    public void waitForShutdown() {
        try {
            URL apiCheckUrl = new URL(url, "/system/stats");
            URL svCheckUrl = new URL("http", url.getHost(), 5000, "/sv/status/graylog-server");

            Boolean serverRunning = true;
            while (serverRunning) {
                Boolean apiAvailable = doRequest(apiCheckUrl);
                Boolean svStatusUp = doRequest(svCheckUrl);
                serverRunning = apiAvailable && svStatusUp;

                sleep(1000);
            }
        } catch (MalformedURLException e) {
            e.printStackTrace();
        }
    }

    private boolean doRequest(URL url) {
        try {
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setConnectTimeout(HTTP_TIMEOUT);
            connection.setReadTimeout(HTTP_TIMEOUT);
            connection.setRequestMethod("GET");

            if (url.getUserInfo() != null) {
                String encodedUserInfo = Base64.encodeBase64String(url.getUserInfo().getBytes());
                connection.setRequestProperty("Authorization", "Basic " + encodedUserInfo);
            }

            int responseCode = connection.getResponseCode();
            return (200 <= responseCode && responseCode <= 399);
        } catch (IOException e) {
            return false;
        }
    }

    public String getNodeId() {
        ObjectMapper mapper = new ObjectMapper();

        try {
            HttpURLConnection connection = (HttpURLConnection) new URL(url, "/system").openConnection();
            connection.setConnectTimeout(HTTP_TIMEOUT);
            connection.setReadTimeout(HTTP_TIMEOUT);
            connection.setRequestMethod("GET");

            if (url.getUserInfo() != null) {
                String encodedUserInfo = Base64.encodeBase64String(url.getUserInfo().getBytes());
                connection.setRequestProperty("Authorization", "Basic " + encodedUserInfo);
            }

            InputStream inputStream = connection.getInputStream();
            JsonNode json = mapper.readTree(inputStream);
            return json.get("server_id").toString();
        } catch (JsonProcessingException e) {
            e.printStackTrace();
        } catch (MalformedURLException e) {
            e.printStackTrace();
        } catch (ProtocolException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        }
        return "00000000-0000-0000-0000-000000000000";
    }

    public URL getServerUrl() {
        URL url;
        try {
            URIBuilder uriBuilder = new URIBuilder(System.getProperty("gl2.baseuri", "http://localhost"));
            uriBuilder.setPort(Integer.parseInt(System.getProperty("gl2.port", "12900")));
            uriBuilder.setUserInfo(System.getProperty("gl2.admin_user", "admin"), System.getProperty("gl2.admin_password", "admin"));
            url = uriBuilder.build().toURL();
        } catch (URISyntaxException e) {
            throw new SkipException("Invalid URI given. Skipping integration tests.");
        } catch (MalformedURLException e) {
            throw new SkipException("Invalid URI given. Skipping integration tests.");
        }
        return url;
    }

    private static void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            // interrupted
        }
    }
}


File: integration-tests/src/test/java/integration/util/mongodb/MongodbSeed.java
/**
 * This file is part of Graylog.
 *
 * Graylog is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Graylog is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Graylog.  If not, see <http://www.gnu.org/licenses/>.
 */
package integration.util.mongodb;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.mongodb.MongoClient;
import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoDatabase;
import org.apache.commons.io.FilenameUtils;
import org.bson.BSONDecoder;
import org.bson.BSONObject;
import org.bson.BasicBSONDecoder;
import org.bson.Document;
import org.testng.TestException;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.net.URI;
import java.net.URL;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class MongodbSeed {
    public List<Document> readBsonFile(String filename){
        Path filePath = Paths.get(filename);
        List<Document> dataset = new ArrayList<>();

        try {
            ByteArrayInputStream fileBytes = new ByteArrayInputStream(Files.readAllBytes(filePath));
            BSONDecoder decoder = new BasicBSONDecoder();
            BSONObject obj;

            while((obj = decoder.readObject(fileBytes)) != null) {
                if(!obj.toString().trim().isEmpty()) {
                    Document mongoDocument = new Document();
                    mongoDocument.putAll(obj.toMap());
                    dataset.add(mongoDocument);
                }
            }
        } catch (FileNotFoundException e) {
            e.printStackTrace();
            throw new TestException("Can not open BSON input file.", e);
        } catch (JsonProcessingException e) {
            e.printStackTrace();
            throw new TestException("Can not parse BSON data.", e);
        } catch (IOException e) {
            //EOF
        }

        return dataset;
    }

    public Map<String, List<Document>> parseDatabaseDump(String dbPath){
        Map<String, List<Document>> collections = new HashMap<>();

        URL seedUrl = Thread.currentThread().getContextClassLoader().getResource("integration/seeds/mongodb/" + dbPath);
        File dir = new File(seedUrl.getPath());
        File[] collectionListing = dir.listFiles();

        if (collectionListing != null) {
            for (File collection : collectionListing) {
                if (collection.getName().endsWith(".bson") && !collection.getName().startsWith("system.indexes.")) {
                    List<Document> collectionData = readBsonFile(collection.getAbsolutePath());
                    collections.put(FilenameUtils.removeExtension(collection.getName()), collectionData);
                }
            }
        }


        return collections;
    }

    public Map<String, List<Document>> updateNodeIdFirstNode(Map<String, List<Document>> collections, String nodeId) {
        List<Document> nodes = new ArrayList<>();

        for (Map.Entry<String, List<Document>> collection : collections.entrySet()) {
            if(collection.getKey().equals("nodes")) {
                nodes = collection.getValue();
            }
        }

        Document firstNode = nodes.get(0);
        firstNode.put("node_id", nodeId);
        nodes.set(0, firstNode);

        collections.remove("nodes");
        collections.put("nodes", nodes);

        return collections;
    }

    public Map<String, List<Document>> updateNodeIdInputs(Map<String, List<Document>> collections, String nodeId) {
        List<Document> inputs = new ArrayList<>();

        for (Map.Entry<String, List<Document>> collection : collections.entrySet()) {
            if(collection.getKey().equals("inputs")) {
                for (Document input : collection.getValue()){
                    input.remove("node_id");
                    input.put("node_id", nodeId);
                    inputs.add(input);
                }

            }
        }

        collections.remove("inputs");
        collections.put("inputs", inputs);

        return collections;
    }

    public void loadDataset(String dbPath, String dbName, String nodeId){
        Map<String, List<Document>> collections = parseDatabaseDump(dbPath);
        collections = updateNodeIdFirstNode(collections, nodeId);
        collections = updateNodeIdInputs(collections, nodeId);

        MongoClient mongoClient = new MongoClient(
                URI.create(System.getProperty("gl2.baseuri", "http://localhost")).getHost(),
                Integer.parseInt(System.getProperty("mongodb.port", "27017")));

        mongoClient.dropDatabase(dbName);
        MongoDatabase mongoDatabase = mongoClient.getDatabase(dbName);

        for (Map.Entry<String, List<Document>> collection : collections.entrySet()) {
            String collectionName = collection.getKey();
            mongoDatabase.createCollection(collectionName);
            MongoCollection<Document> mongoCollection = mongoDatabase.getCollection(collection.getKey());
            for (Document document : collection.getValue()) {
                mongoCollection.insertOne(document);
            }
        }
    }
}
