Refactoring Types: ['Move Method']
-java/src/test/java/com/jayway/restassured/itest/java/SSLITest.java
/*
 * Copyright 2013 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.jayway.restassured.itest.java;

import com.jayway.restassured.RestAssured;
import com.jayway.restassured.builder.RequestSpecBuilder;
import com.jayway.restassured.builder.ResponseSpecBuilder;
import com.jayway.restassured.specification.RequestSpecification;
import com.jayway.restassured.specification.ResponseSpecification;
import org.junit.Ignore;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.ExpectedException;

import javax.net.ssl.SSLException;
import java.io.IOException;
import java.io.InputStream;
import java.security.KeyStore;

import static com.jayway.restassured.RestAssured.*;
import static com.jayway.restassured.authentication.CertificateAuthSettings.certAuthSettings;
import static com.jayway.restassured.config.RestAssuredConfig.newConfig;
import static com.jayway.restassured.config.SSLConfig.sslConfig;
import static com.jayway.restassured.http.ContentType.HTML;
import static org.hamcrest.Matchers.containsString;

@Ignore
public class SSLITest {
    @Rule
    public ExpectedException exception = ExpectedException.none();

    public static ResponseSpecification eurosportSpec() {
        return new ResponseSpecBuilder().
                expectBody(containsString("An error occurred while processing your request.")).
                expectContentType(HTML).
                expectStatusCode(500).build();
    }

    @Test(expected = SSLException.class)
    public void throwsSSLExceptionWhenHostnameInCertDoesntMatch() throws Exception {
        get("https://tv.eurosport.com/");
    }

    @Test
    public void givenKeystoreDefinedStaticallyWhenSpecifyingJksKeyStoreFileWithCorrectPasswordAllowsToUseSSL() throws Exception {
        RestAssured.keystore("truststore_eurosport.jks", "test4321");
        try {
            expect().spec(eurosportSpec()).get("https://tv.eurosport.com/");
        } finally {
            RestAssured.reset();
        }
    }

    @Test
    public void whenEnablingAllowAllHostNamesVerifierWithoutActivatingAKeyStoreTheCallTo() throws Exception {
        RestAssured.config = config().sslConfig(sslConfig().allowAllHostnames());
        try {
            get("https://tv.eurosport.com/").then().spec(eurosportSpec());
        } finally {
            RestAssured.reset();
        }
    }

    @Test
    public void usingStaticallyConfiguredCertificateAuthenticationWorks() throws Exception {
        RestAssured.authentication = certificate("truststore_eurosport.jks", "test4321", certAuthSettings().allowAllHostnames());
        try {
            get("https://tv.eurosport.com/").then().spec(eurosportSpec());
        } finally {
            RestAssured.reset();
        }
    }

    @Test(expected = SSLException.class)
    public void usingStaticallyConfiguredCertificateAuthenticationWithIllegalHostNameInCertDoesntWork() throws Exception {
        RestAssured.authentication = certificate("truststore_mjvmobile.jks", "test4321");
        try {
            get("https://tv.eurosport.com/").then().body(containsString("eurosport"));
        } finally {
            RestAssured.reset();
        }
    }

    @Test
    public void usingStaticallyConfiguredCertificateAuthenticationWithIllegalHostNameInCertWorksWhenSSLConfigIsConfiguredToAllowAllHostNames() throws Exception {
        RestAssured.config = newConfig().sslConfig(sslConfig().allowAllHostnames());
        RestAssured.authentication = certificate("truststore_eurosport.jks", "test4321");
        try {
            get("https://tv.eurosport.com/").then().spec(eurosportSpec());
        } finally {
            RestAssured.reset();
        }
    }

    @Test
    public void givenKeystoreDefinedUsingGivenWhenSpecifyingJksKeyStoreFileWithCorrectPasswordAllowsToUseSSL() throws Exception {
        given().keystore("/truststore_eurosport.jks", "test4321").then().expect().spec(eurosportSpec()).get("https://tv.eurosport.com/");
    }

    @Test
    public void throwsIOExceptionWhenPasswordIsIncorrect() throws Exception {
        exception.expect(IOException.class);
        exception.expectMessage("Keystore was tampered with, or password was incorrect");

        given().
                auth().certificate("truststore_eurosport.jks", "test4333").
        when().
                get("https://tv.eurosport.com/").
        then().
                body(containsString("eurosport"));
    }

    @Test
    public void certificateAuthenticationWorks() throws Exception {
        given().
                auth().certificate("truststore_eurosport.jks", "test4321", certAuthSettings().allowAllHostnames()).
        when().
                get("https://tv.eurosport.com/").
        then().
                spec(eurosportSpec());
    }

    @Ignore("Temporary ignored since site has changed") @Test public void
    allows_specifying_trust_store_in_dsl() throws Exception {
        InputStream keyStoreStream = Thread.currentThread().getContextClassLoader().getResourceAsStream("truststore_cloudamqp.jks");
        KeyStore keyStore = KeyStore.getInstance(KeyStore.getDefaultType());
        keyStore.load(keyStoreStream, "cloud1234".toCharArray());

        given().trustStore(keyStore).then().get("https://bunny.cloudamqp.com/api/").then().statusCode(200);
    }

    @Ignore("Temporary ignored since site has changed") @Test public void
    allows_specifying_trust_store_statically() throws Exception {

        InputStream keyStoreStream = Thread.currentThread().getContextClassLoader().getResourceAsStream("truststore_cloudamqp.jks");
        KeyStore keyStore = KeyStore.getInstance(KeyStore.getDefaultType());
        keyStore.load(keyStoreStream, "cloud1234".toCharArray());

        RestAssured.trustStore(keyStore);

        try {
            get("https://bunny.cloudamqp.com/api/").then().statusCode(200);
        } finally {
            RestAssured.reset();
        }
    }

    @Test public void
    allows_specifying_trust_store_and_allow_all_host_names_in_config_using_dsl() throws Exception {
        InputStream keyStoreStream = Thread.currentThread().getContextClassLoader().getResourceAsStream("truststore_eurosport.jks");
        KeyStore keyStore = KeyStore.getInstance(KeyStore.getDefaultType());
        keyStore.load(keyStoreStream, "test4321".toCharArray());

        given().config(config().sslConfig(sslConfig().trustStore(keyStore).and().allowAllHostnames())).then().get("https://tv.eurosport.com/").then().spec(eurosportSpec());
    }

    @Test public void
    relaxed_https_validation_works_using_instance_config() {
        given().config(config().sslConfig(sslConfig().relaxedHTTPSValidation())).then().get("https://tv.eurosport.com/").then().spec(eurosportSpec());
    }

    @Test public void
    relaxed_https_validation_works_using_instance_dsl() {
        given().relaxedHTTPSValidation().then().get("https://bunny.cloudamqp.com/api/").then().statusCode(200);
    }

    @Test public void
    relaxed_https_validation_works_when_defined_statically() {
        RestAssured.useRelaxedHTTPSValidation();

        try {
            get("https://bunny.cloudamqp.com/api/").then().statusCode(200);
        } finally {
            RestAssured.reset();
        }
    }

    @Test public void
    relaxed_https_validation_works_when_defined_statically_with_base_uri() {
        RestAssured.useRelaxedHTTPSValidation();
        RestAssured.baseURI = "https://bunny.cloudamqp.com";

        try {
            get("/api/").then().statusCode(200);
        } finally {
            RestAssured.reset();
        }
    }

    @Test public void
    keystore_works_with_static_base_uri() {
        RestAssured.baseURI = "https://tv.eurosport.com/";

        try {
            given().keystore("/truststore_eurosport.jks", "test4321").when().get().then().spec(eurosportSpec());
        } finally {
            RestAssured.reset();
        }
    }

    @Ignore("Temporary ignored since site has changed") @Test public void
    truststrore_works_with_static_base_uri() throws Exception{
        RestAssured.baseURI = "https://bunny.cloudamqp.com/";

        InputStream keyStoreStream = Thread.currentThread().getContextClassLoader().getResourceAsStream("truststore_cloudamqp.jks");
        KeyStore keyStore = KeyStore.getInstance(KeyStore.getDefaultType());
        keyStore.load(keyStoreStream, "cloud1234".toCharArray());

        try {
            given().trustStore(keyStore).when().get("/api/").then().statusCode(200);
        } finally {
            RestAssured.reset();
        }
    }


    @Test public void
    can_make_request_to_sites_that_with_valid_ssl_cert() {
        get("https://duckduckgo.com/").then().statusCode(200);
    }

    @Test public void
    allows_specifying_trust_store_statically_with_request_builder() throws Exception {
        // Load the trust store
        InputStream trustStoreStream = Thread.currentThread().getContextClassLoader().getResourceAsStream("truststore_eurosport.jks");
        KeyStore trustStore = KeyStore.getInstance(KeyStore.getDefaultType());
        trustStore.load(trustStoreStream, "test4321".toCharArray());

        // Set the truststore on the global config
        RestAssured.config = RestAssured.config().sslConfig(sslConfig().trustStore(trustStore).and().allowAllHostnames());

        final RequestSpecification spec = new RequestSpecBuilder().build();
        given().spec(spec).get("https://tv.eurosport.com/").then().spec(eurosportSpec());
    }

}


File: examples/rest-assured-itest-java/src/test/java/com/jayway/restassured/itest/java/SpecificationBuilderITest.java
/*
 * Copyright 2013 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.jayway.restassured.itest.java;

import com.jayway.restassured.RestAssured;
import com.jayway.restassured.builder.RequestSpecBuilder;
import com.jayway.restassured.builder.ResponseSpecBuilder;
import com.jayway.restassured.itest.java.support.WithJetty;
import com.jayway.restassured.response.Cookies;
import com.jayway.restassured.specification.RequestSpecification;
import com.jayway.restassured.specification.ResponseSpecification;
import org.apache.commons.io.output.WriterOutputStream;
import org.hamcrest.Matchers;
import org.junit.Test;

import java.io.PrintStream;
import java.io.StringWriter;

import static com.jayway.restassured.RestAssured.*;
import static com.jayway.restassured.config.LogConfig.logConfig;
import static com.jayway.restassured.config.RedirectConfig.redirectConfig;
import static com.jayway.restassured.config.RestAssuredConfig.newConfig;
import static com.jayway.restassured.filter.log.LogDetail.ALL;
import static com.jayway.restassured.itest.java.SSLITest.eurosportSpec;
import static java.util.Arrays.asList;
import static org.hamcrest.Matchers.*;
import static org.junit.Assert.assertThat;

public class SpecificationBuilderITest extends WithJetty {

    @Test
    public void expectingSpecificationMergesTheCurrentSpecificationWithTheSuppliedOne() throws Exception {
        final ResponseSpecBuilder builder = new ResponseSpecBuilder();
        builder.expectBody("store.book.size()", is(4)).expectStatusCode(200);
        final ResponseSpecification responseSpecification = builder.build();

        expect().
                specification(responseSpecification).
                body("store.book[0].author", equalTo("Nigel Rees")).
        when().
                get("/jsonStore");
    }

    @Test
    public void supportsSpecifyingDefaultResponseSpec() throws Exception {
        RestAssured.responseSpecification = new ResponseSpecBuilder().expectBody("store.book.size()", is(4)).expectStatusCode(200).build();

        try {
            expect().
                    body("store.book[0].author", equalTo("Nigel Rees")).
            when().
                    get("/jsonStore");
        } finally {
            RestAssured.reset();
        }
    }

    @Test
    public void expectingSpecMergesTheCurrentSpecificationWithTheSuppliedOne() throws Exception {
        final ResponseSpecBuilder builder = new ResponseSpecBuilder();
        builder.expectBody("store.book.size()", is(4)).expectStatusCode(200);
        final ResponseSpecification responseSpecification = builder.build();

        expect().
                spec(responseSpecification).
                body("store.book[0].author", equalTo("Nigel Rees")).
        when().
                get("/jsonStore");
    }

    @Test
    public void bodyExpectationsAreNotOverwritten() throws Exception {
        final ResponseSpecBuilder builder = new ResponseSpecBuilder();
        builder.expectBody("store.book.size()", is(4)).expectStatusCode(200);
        final ResponseSpecification responseSpecification = builder.build();

        expect().
                body("store.book.author", hasItems("Nigel Rees", "Evelyn Waugh", "Herman Melville", "J. R. R. Tolkien")).
                spec(responseSpecification).
                body("store.book[0].author", equalTo("Nigel Rees")).
        when().
                get("/jsonStore");
    }

    @Test
    public void responseSpecificationSupportsMergingWithAnotherResponseSpecification() throws Exception {
        final ResponseSpecification specification = expect().body("store.book.size()", equalTo(4));
        final ResponseSpecification built = new ResponseSpecBuilder().expectStatusCode(200).addResponseSpecification(specification).build();

        expect().
                body("store.book.author", hasItems("Nigel Rees", "Evelyn Waugh", "Herman Melville", "J. R. R. Tolkien")).
                spec(built).
                body("store.book[0].author", equalTo("Nigel Rees")).
        when().
                get("/jsonStore");
    }

    @Test
    public void responseSpecificationCanExpectBodyWithArgs () throws Exception {
        final ResponseSpecification spec = new ResponseSpecBuilder().rootPath("store.book[%d]").expectBody("author", withArgs(0), equalTo("Nigel Rees")).build();

        expect().
                spec(spec).
                body("title", withArgs(1), equalTo("Sword of Honour")).
        when().
                get("/jsonStore");
    }

    @Test
    public void responseSpecificationCanExpectContentWithArgs () throws Exception {
        final ResponseSpecification spec = new ResponseSpecBuilder().rootPath("store.book[%d]").expectContent("author", withArgs(0), equalTo("Nigel Rees")).build();

        expect().
                spec(spec).
                content("title", withArgs(1), equalTo("Sword of Honour")).
        when().
                get("/jsonStore");
    }

    @Test
    public void supportsSpecifyingParametersInRequestSpecBuilder() throws Exception {
        final RequestSpecification spec = new RequestSpecBuilder().addParameter("firstName", "John").addParam("lastName", "Doe").build();

        given().
                spec(spec).
        expect().
                body("greeting.firstName", equalTo("John")).
                body("greeting.lastName", equalTo("Doe")).
        when().
                get("/greetXML");
    }

    @Test
    public void supportsSpecifyingDefaultRequestSpec() throws Exception {
        RestAssured.requestSpecification = new RequestSpecBuilder().addParameter("firstName", "John").addParam("lastName", "Doe").build();
        try {
            expect().
                    body("greeting.firstName", equalTo("John")).
                    body("greeting.lastName", equalTo("Doe")).
            when().
                    get("/greetXML");
        } finally {
            RestAssured.reset();
        }
    }

    @Test
    public void supportsSpecifyingQueryParametersInRequestSpecBuilderWhenGet() throws Exception {
        final RequestSpecification spec = new RequestSpecBuilder().addQueryParameter("firstName", "John").addQueryParam("lastName", "Doe").build();

        given().
                spec(spec).
        expect().
                body("greeting.firstName", equalTo("John")).
                body("greeting.lastName", equalTo("Doe")).
        when().
                get("/greetXML");
    }

    @Test
    public void supportsSpecifyingQueryParametersInRequestSpecBuilderWhenPost() throws Exception {
        final RequestSpecification spec = new RequestSpecBuilder().addQueryParameter("firstName", "John").addQueryParam("lastName", "Doe").build();

        given().
                spec(spec).
        expect().
                body("greeting.firstName", equalTo("John")).
                body("greeting.lastName", equalTo("Doe")).
        when().
                post("/greetXML");
    }

    @Test
    public void supportsMergesParametersWhenUsingRequestSpecBuilder() throws Exception {
        final RequestSpecification spec = new RequestSpecBuilder().addParameter("firstName", "John").build();

        given().
                spec(spec).
                param("lastName", "Doe").
        expect().
                body("greeting.firstName", equalTo("John")).
                body("greeting.lastName", equalTo("Doe")).
        when().
                get("/greetXML");
    }

    @Test
    public void supportsMergingCookiesWhenUsingRequestSpecBuilder() throws Exception {
        final RequestSpecification spec1 = new RequestSpecBuilder().addCookie("cookie3", "value3").build();
        final RequestSpecification spec2 = new RequestSpecBuilder().addCookie("cookie1", "value1").addRequestSpecification(spec1).build();

        given().
                spec(spec2).
                cookie("cookie2", "value2").
        expect().
                body(equalTo("cookie1, cookie3, cookie2")).
        when().
                get("/cookie");
    }

    @Test
    public void supportsMergingHeadersWhenUsingRequestSpecBuilder() throws Exception {
        final RequestSpecification spec = new RequestSpecBuilder().addHeader("header1", "value1").build();

        given().
                spec(spec).
                header("header2", "value2").
        expect().
                body(containsString("header1")).
                body(containsString("header2")).
        when().
                get("/header");
    }

    @Test
    public void supportsMergingRequestSpecHeadersUsingTheBuilder() throws Exception {
        final RequestSpecification spec = given().header("header2", "value2");
        final RequestSpecification spec2 = new RequestSpecBuilder().addHeader("header1", "value1").addRequestSpecification(spec).build();

        given().
                spec(spec2).
                header("header3", "value3").
        expect().
                body(containsString("header1")).
                body(containsString("header2")).
                body(containsString("header3")).
        when().
                get("/header");
    }

    @Test
    public void requestSpecBuilderSupportsSettingAuthentication() throws Exception {
        final RequestSpecification spec = new RequestSpecBuilder().setAuth(basic("jetty", "jetty")).build();

        given().
                spec(spec).
        expect().
                statusCode(200).
        when().
                get("/secured/hello");
    }

    @Test
    public void supportsMergingMultiValueParametersWhenUsingRequestSpecBuilder() throws Exception {
        final RequestSpecification spec = new RequestSpecBuilder().addParam("list", "1", "2", "3").build();

        given().
                spec(spec).
        expect().
                body("list", equalTo("1,2,3")).
        when().
                get("/multiValueParam");
    }

    @Test
    public void supportsMergingMultiValueQueryParametersWhenUsingRequestSpecBuilder() throws Exception {
        final RequestSpecification spec = new RequestSpecBuilder().addQueryParam("list", "1", "2", "3").build();

        given().
                spec(spec).
        expect().
                body("list", equalTo("1,2,3")).
        when().
                get("/multiValueParam");
    }

    @Test
    public void supportsMergingMultiValueFormParametersWhenUsingRequestSpecBuilder() throws Exception {
        final RequestSpecification spec = new RequestSpecBuilder().addFormParam("list", "1", "2", "3").build();

        given().
                spec(spec).
        expect().
                body("list", equalTo("1,2,3")).
        when().
                put("/multiValueParam");
    }

    @Test
    public void supportsMergingMultiValueParametersUsingListWhenUsingRequestSpecBuilder() throws Exception {
        final RequestSpecification spec = new RequestSpecBuilder().addParam("list", asList("1", "2", "3")).build();

        given().
                spec(spec).
        expect().
                body("list", equalTo("1,2,3")).
        when().
                get("/multiValueParam");
    }

    @Test
    public void supportsMergingMultiValueQueryParametersUsingListWhenUsingRequestSpecBuilder() throws Exception {
        final RequestSpecification spec = new RequestSpecBuilder().addQueryParam("list", asList("1", "2", "3")).build();

        given().
                spec(spec).
        expect().
                body("list", equalTo("1,2,3")).
        when().
                get("/multiValueParam");
    }

    @Test
    public void supportsMergingMultiValueFormParametersUsingListWhenUsingRequestSpecBuilder() throws Exception {
        final RequestSpecification spec = new RequestSpecBuilder().addFormParam("list", asList("1", "2", "3")).build();

        given().
                spec(spec).
        expect().
                body("list", equalTo("1,2,3")).
        when().
                put("/multiValueParam");
    }

    @Test
    public void supportsMergingFormParametersWhenUsingRequestSpecBuilder() throws Exception {
        final RequestSpecification spec = new RequestSpecBuilder().addFormParam("lastName", "Doe").build();

        given().
                spec(spec).
                formParameter("firstName", "John").
        expect().
                body("greeting", Matchers.equalTo("Greetings John Doe")).
        when().
                put("/greetPut");
    }

    @Test
    public void supportsMergingPathParametersWhenUsingRequestSpecBuilder() throws Exception {
        final RequestSpecification spec = new RequestSpecBuilder().addPathParam("lastName", "Doe").build();

        given().
                spec(spec).
                pathParameter("firstName", "John").
        expect().
                body("fullName", equalTo("John Doe")).
        when().
               get("/{firstName}/{lastName}");
    }

    @Test
    public void supportsSettingLoggingWhenUsingRequestSpecBuilder() throws Exception {
        final StringWriter writer = new StringWriter();
        final PrintStream captor = new PrintStream(new WriterOutputStream(writer), true);
        final RequestSpecification spec = new RequestSpecBuilder().setConfig(newConfig().logConfig(logConfig().defaultStream(captor))).and().log(ALL).build();

        given().
                spec(spec).
                pathParameter("firstName", "John").
                pathParameter("lastName", "Doe").
        when().
                get("/{firstName}/{lastName}").
        then().
                body("fullName", equalTo("John Doe"));

        assertThat(writer.toString(), equalTo("Request method:\tGET\nRequest path:\thttp://localhost:8080/John/Doe\nProxy:\t\t\t<none>\nRequest params:\t<none>\nQuery params:\t<none>\nForm params:\t<none>\nPath params:\tfirstName=John\n\t\t\t\tlastName=Doe\nMultiparts:\t\t<none>\nHeaders:\t\tAccept=*/*\nCookies:\t\t<none>\nBody:\t\t\t<none>\n"));
    }

    @Test
    public void supportsSettingConfigWhenUsingRequestSpecBuilder() throws Exception {
        final RequestSpecification spec = new RequestSpecBuilder().setConfig(newConfig().redirect(redirectConfig().followRedirects(false))).build();

        given().
                param("url", "/hello").
                spec(spec).
        expect().
                statusCode(302).
                header("Location", is("http://localhost:8080/hello")).
        when().
                get("/redirect");
    }

    @Test
    public void mergesStaticallyDefinedResponseSpecificationsCorrectly() throws Exception {
        RestAssured.responseSpecification = new ResponseSpecBuilder().expectCookie("Cookie1", "Value1").build();
        ResponseSpecification reqSpec1 = new ResponseSpecBuilder().expectCookie("Cookie2", "Value2").build();
        ResponseSpecification reqSpec2 = new ResponseSpecBuilder().expectCookie("Cookie3", "Value3").build();

        try {
            Cookies cookies =
            given().
                    cookie("Cookie1", "Value1").
                    cookie("Cookie2", "Value2").
            when().
                    get("/reflect").
            then().
                    assertThat().
                    spec(reqSpec1).
            extract().
                    detailedCookies();

            assertThat(cookies.size(), is(2));
            assertThat(cookies.hasCookieWithName("Cookie1"), is(true));
            assertThat(cookies.hasCookieWithName("Cookie2"), is(true));

            cookies =
            given().
                    cookie("Cookie1", "Value1").
                    cookie("Cookie3", "Value3").
            when().
                    get("/reflect").
            then().
                    assertThat().
                    spec(reqSpec2).
            extract().
                    detailedCookies();

            assertThat(cookies.size(), is(2));
            assertThat(cookies.hasCookieWithName("Cookie1"), is(true));
            assertThat(cookies.hasCookieWithName("Cookie3"), is(true));
        } finally {
            RestAssured.reset();
        }
    }

    @Test
    public void mergesStaticallyDefinedRequestSpecificationsCorrectly() throws Exception {
        RestAssured.requestSpecification = new RequestSpecBuilder().addCookie("Cookie1", "Value1").build();
        RequestSpecification reqSpec1 = new RequestSpecBuilder().addCookie("Cookie2", "Value2").build();
        RequestSpecification reqSpec2 = new RequestSpecBuilder().addCookie("Cookie3", "Value3").build();

        try {
            Cookies cookies =
            given().
                    spec(reqSpec1).
            when().
                    get("/reflect").
            then().
                    extract().
                    detailedCookies();

            assertThat(cookies.size(), is(2));
            assertThat(cookies.hasCookieWithName("Cookie1"), is(true));
            assertThat(cookies.hasCookieWithName("Cookie2"), is(true));

            cookies =
            given().
                    spec(reqSpec2).
            when().
                    get("/reflect").
            then().
                    extract().
                    detailedCookies();

            assertThat(cookies.size(), is(2));
            assertThat(cookies.hasCookieWithName("Cookie1"), is(true));
            assertThat(cookies.hasCookieWithName("Cookie3"), is(true));
        } finally {
            RestAssured.reset();
        }
    }

    @Test
    public void supportsSpecifyingKeystore() throws Exception {
        final RequestSpecification spec = new RequestSpecBuilder().setKeystore("/truststore_eurosport.jks", "test4321").build();
        given().spec(spec).expect().spec(eurosportSpec()).get("https://tv.eurosport.com/");
    }

    @Test
    public void supportsOverridingKeystore() throws Exception {
        final RequestSpecification spec = new RequestSpecBuilder().setKeystore("/truststore_eurosport.jks", "wrong pw").build();
        given().spec(spec).keystore("/truststore_eurosport.jks", "test4321").expect().spec(eurosportSpec()).get("https://tv.eurosport.com/");
    }
}
