Refactoring Types: ['Extract Method']
springframework/test/util/JsonPathExpectationsHelper.java
/*
 * Copyright 2002-2015 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.test.util;

import java.lang.reflect.Array;
import java.lang.reflect.Method;
import java.text.ParseException;
import java.util.List;

import com.jayway.jsonpath.InvalidPathException;
import com.jayway.jsonpath.JsonPath;
import org.hamcrest.Matcher;

import org.springframework.util.Assert;
import org.springframework.util.ReflectionUtils;

import static org.hamcrest.MatcherAssert.*;
import static org.springframework.test.util.AssertionErrors.*;

/**
 * A helper class for applying assertions via JSON path expressions.
 *
 * <p>Based on the <a href="https://github.com/jayway/JsonPath">JsonPath</a>
 * project: requiring version 0.9+, with 1.1+ strongly recommended.
 *
 * @author Rossen Stoyanchev
 * @author Juergen Hoeller
 * @since 3.2
 */
public class JsonPathExpectationsHelper {

	private static Method compileMethod;

	private static Object emptyFilters;

	static {
		// Reflective bridging between JsonPath 0.9.x and 1.x
		for (Method candidate : JsonPath.class.getMethods()) {
			if (candidate.getName().equals("compile")) {
				Class<?>[] paramTypes = candidate.getParameterTypes();
				if (paramTypes.length == 2 && String.class == paramTypes[0] && paramTypes[1].isArray()) {
					compileMethod = candidate;
					emptyFilters = Array.newInstance(paramTypes[1].getComponentType(), 0);
					break;
				}
			}
		}
		Assert.state(compileMethod != null, "Unexpected JsonPath API - no compile(String, ...) method found");
	}


	private final String expression;

	private final JsonPath jsonPath;


	/**
	 * Construct a new JsonPathExpectationsHelper.
	 * @param expression the JsonPath expression
	 * @param args arguments to parameterize the JSON path expression with
	 * formatting specifiers defined in {@link String#format(String, Object...)}
	 */
	public JsonPathExpectationsHelper(String expression, Object... args) {
		this.expression = String.format(expression, args);
		this.jsonPath = (JsonPath) ReflectionUtils.invokeMethod(
				compileMethod, null, this.expression, emptyFilters);
	}


	/**
	 * Evaluate the JSON path and assert the resulting value with the given {@code Matcher}.
	 * @param content the response content
	 * @param matcher the matcher to assert on the resulting json path
	 */
	@SuppressWarnings("unchecked")
	public <T> void assertValue(String content, Matcher<T> matcher) throws ParseException {
		T value = (T) evaluateJsonPath(content);
		assertThat("JSON path " + this.expression, value, matcher);
	}

	private Object evaluateJsonPath(String content) throws ParseException  {
		String message = "No value for JSON path: " + this.expression + ", exception: ";
		try {
			return this.jsonPath.read(content);
		}
		catch (InvalidPathException ex) {
			throw new AssertionError(message + ex.getMessage());
		}
		catch (ArrayIndexOutOfBoundsException ex) {
			throw new AssertionError(message + ex.getMessage());
		}
		catch (IndexOutOfBoundsException ex) {
			throw new AssertionError(message + ex.getMessage());
		}
	}

	/**
	 * Apply the JSON path and assert the resulting value.
	 */
	public void assertValue(String responseContent, Object expectedValue) throws ParseException {
		Object actualValue = evaluateJsonPath(responseContent);
		if ((actualValue instanceof List) && !(expectedValue instanceof List)) {
			@SuppressWarnings("rawtypes")
			List actualValueList = (List) actualValue;
			if (actualValueList.isEmpty()) {
				fail("No matching value for JSON path \"" + this.expression + "\"");
			}
			if (actualValueList.size() != 1) {
				fail("Got a list of values " + actualValue + " instead of the value " + expectedValue);
			}
			actualValue = actualValueList.get(0);
		}
		else if (actualValue != null && expectedValue != null) {
			assertEquals("For JSON path " + this.expression + " type of value",
					expectedValue.getClass(), actualValue.getClass());
		}
		assertEquals("JSON path " + this.expression, expectedValue, actualValue);
	}

	/**
	 * Apply the JSON path and assert the resulting value is an array.
	 */
	public void assertValueIsArray(String responseContent) throws ParseException {
		Object actualValue = evaluateJsonPath(responseContent);
		assertTrue("No value for JSON path \"" + this.expression + "\"", actualValue != null);
		String reason = "Expected array at JSON path " + this.expression + " but found " + actualValue;
		assertTrue(reason, actualValue instanceof List);
	}

	/**
	 * Evaluate the JSON path and assert the resulting content exists.
	 */
	public void exists(String content) throws ParseException {
		Object value = evaluateJsonPath(content);
		String reason = "No value for JSON path " + this.expression;
		assertTrue(reason, value != null);
		if (List.class.isInstance(value)) {
			assertTrue(reason, !((List<?>) value).isEmpty());
		}
	}

	/**
	 * Evaluate the JSON path and assert it doesn't point to any content.
	 */
	public void doesNotExist(String content) throws ParseException {
		Object value;
		try {
			value = evaluateJsonPath(content);
		}
		catch (AssertionError ex) {
			return;
		}
		String reason = String.format("Expected no value for JSON path: %s but found: %s", this.expression, value);
		if (List.class.isInstance(value)) {
			assertTrue(reason, ((List<?>) value).isEmpty());
		}
		else {
			assertTrue(reason, value == null);
		}
	}

}


File: spring-test/src/main/java/org/springframework/test/web/servlet/result/JsonPathResultMatchers.java
/*
 * Copyright 2002-2015 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.test.web.servlet.result;

import org.hamcrest.Matcher;

import org.springframework.test.util.JsonPathExpectationsHelper;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.ResultMatcher;

/**
 * Factory for assertions on the response content using
 * <a href="http://goessner.net/articles/JsonPath/">JSONPath</a> expressions.
 * <p>An instance of this class is typically accessed via
 * {@link MockMvcResultMatchers#jsonPath}.
 *
 * @author Rossen Stoyanchev
 * @since 3.2
 */
public class JsonPathResultMatchers {

	private final JsonPathExpectationsHelper jsonPathHelper;


	/**
	 * Protected constructor. Use
	 * {@link MockMvcResultMatchers#jsonPath(String, Object...)} or
	 * {@link MockMvcResultMatchers#jsonPath(String, Matcher)}.
	 */
	protected JsonPathResultMatchers(String expression, Object ... args) {
		this.jsonPathHelper = new JsonPathExpectationsHelper(expression, args);
	}


	/**
	 * Evaluate the JSONPath and assert the value of the content found with the
	 * given Hamcrest {@code Matcher}.
	 */
	public <T> ResultMatcher value(final Matcher<T> matcher) {
		return new ResultMatcher() {
			@Override
			public void match(MvcResult result) throws Exception {
				String content = result.getResponse().getContentAsString();
				jsonPathHelper.assertValue(content, matcher);
			}
		};
	}

	/**
	 * Evaluate the JSONPath and assert the value of the content found.
	 */
	public ResultMatcher value(final Object expectedValue) {
		return new ResultMatcher() {
			@Override
			public void match(MvcResult result) throws Exception {
				jsonPathHelper.assertValue(result.getResponse().getContentAsString(), expectedValue);
			}
		};
	}

	/**
	 * Evaluate the JSONPath and assert that content exists.
	 */
	public ResultMatcher exists() {
		return new ResultMatcher() {
			@Override
			public void match(MvcResult result) throws Exception {
				String content = result.getResponse().getContentAsString();
				jsonPathHelper.exists(content);
			}
		};
	}

	/**
	 * Evaluate the JSON path and assert not content was found.
	 */
	public ResultMatcher doesNotExist() {
		return new ResultMatcher() {
			@Override
			public void match(MvcResult result) throws Exception {
				String content = result.getResponse().getContentAsString();
				jsonPathHelper.doesNotExist(content);
			}
		};
	}

	/**
	 * Evluate the JSON path and assert the content found is an array.
	 */
	public ResultMatcher isArray() {
		return new ResultMatcher() {
			@Override
			public void match(MvcResult result) throws Exception {
				String content = result.getResponse().getContentAsString();
				jsonPathHelper.assertValueIsArray(content);
			}
		};
	}

}


File: spring-test/src/main/java/org/springframework/test/web/servlet/result/MockMvcResultMatchers.java
/*
 * Copyright 2002-2015 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.test.web.servlet.result;

import java.util.Map;
import javax.xml.xpath.XPathExpressionException;

import org.hamcrest.Matcher;

import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.ResultMatcher;
import org.springframework.util.AntPathMatcher;

import static org.springframework.test.util.AssertionErrors.*;

/**
 * Static factory methods for {@link ResultMatcher}-based result actions.
 *
 * <h3>Eclipse Users</h3>
 * <p>Consider adding this class as a Java editor favorite. To navigate to
 * this setting, open the Preferences and type "favorites".
 *
 * @author Rossen Stoyanchev
 * @author Brian Clozel
 * @since 3.2
 */
public abstract class MockMvcResultMatchers {

	private static final AntPathMatcher pathMatcher = new AntPathMatcher();


	/**
	 * Access to request-related assertions.
	 */
	public static RequestResultMatchers request() {
		return new RequestResultMatchers();
	}

	/**
	 * Access to assertions for the handler that handled the request.
	 */
	public static HandlerResultMatchers handler() {
		return new HandlerResultMatchers();
	}

	/**
	 * Access to model-related assertions.
	 */
	public static ModelResultMatchers model() {
		return new ModelResultMatchers();
	}

	/**
	 * Access to assertions on the selected view.
	 */
	public static ViewResultMatchers view() {
		return new ViewResultMatchers();
	}

	/**
	 * Access to flash attribute assertions.
	 */
	public static FlashAttributeResultMatchers flash() {
		return new FlashAttributeResultMatchers();
	}

	/**
	 * Asserts the request was forwarded to the given URL.
	 * This methods accepts only exact matches.
	 * @param expectedUrl the exact URL expected
	 */
	public static ResultMatcher forwardedUrl(final String expectedUrl) {
		return new ResultMatcher() {
			@Override
			public void match(MvcResult result) {
				assertEquals("Forwarded URL", expectedUrl, result.getResponse().getForwardedUrl());
			}
		};
	}

	/**
	 * Asserts the request was forwarded to the given URL.
	 * This methods accepts {@link org.springframework.util.AntPathMatcher} expressions.
	 * @param urlPattern an AntPath expression to match against
	 * @since 4.0
	 * @see org.springframework.util.AntPathMatcher
	 */
	public static ResultMatcher forwardedUrlPattern(final String urlPattern) {
		return new ResultMatcher() {
			@Override
			public void match(MvcResult result) {
				assertTrue("AntPath expression", pathMatcher.isPattern(urlPattern));
				assertTrue("Forwarded URL does not match the expected URL pattern",
						pathMatcher.match(urlPattern, result.getResponse().getForwardedUrl()));
			}
		};
	}

	/**
	 * Asserts the request was redirected to the given URL.
	 * This methods accepts only exact matches.
	 * @param expectedUrl the exact URL expected
	 */
	public static ResultMatcher redirectedUrl(final String expectedUrl) {
		return new ResultMatcher() {
			@Override
			public void match(MvcResult result) {
				assertEquals("Redirected URL", expectedUrl, result.getResponse().getRedirectedUrl());
			}
		};
	}

	/**
	 * Asserts the request was redirected to the given URL.
	 * This methods accepts {@link org.springframework.util.AntPathMatcher} expressions.
	 * @param expectedUrl an AntPath expression to match against
	 * @see org.springframework.util.AntPathMatcher
	 * @since 4.0
	 */
	public static ResultMatcher redirectedUrlPattern(final String expectedUrl) {
		return new ResultMatcher() {
			@Override
			public void match(MvcResult result) {
				assertTrue("AntPath expression",pathMatcher.isPattern(expectedUrl));
				assertTrue("Redirected URL",
						pathMatcher.match(expectedUrl, result.getResponse().getRedirectedUrl()));
			}
		};
	}

	/**
	 * Access to response status assertions.
	 */
	public static StatusResultMatchers status() {
		return new StatusResultMatchers();
	}

	/**
	 * Access to response header assertions.
	 */
	public static HeaderResultMatchers header() {
		return new HeaderResultMatchers();
	}

	/**
	 * Access to response body assertions.
	 */
	public static ContentResultMatchers content() {
		return new ContentResultMatchers();
	}

	/**
	 * Access to response body assertions using a <a
	 * href="http://goessner.net/articles/JsonPath/">JSONPath</a> expression to
	 * inspect a specific subset of the body. The JSON path expression can be a
	 * parameterized string using formatting specifiers as defined in
	 * {@link String#format(String, Object...)}.
	 * @param expression the JSON path optionally parameterized with arguments
	 * @param args arguments to parameterize the JSON path expression with
	 */
	public static JsonPathResultMatchers jsonPath(String expression, Object ... args) {
		return new JsonPathResultMatchers(expression, args);
	}

	/**
	 * Access to response body assertions using a <a
	 * href="http://goessner.net/articles/JsonPath/">JSONPath</a> expression to
	 * inspect a specific subset of the body and a Hamcrest match for asserting
	 * the value found at the JSON path.
	 * @param expression the JSON path expression
	 * @param matcher a matcher for the value expected at the JSON path
	 */
	public static <T> ResultMatcher jsonPath(String expression, Matcher<T> matcher) {
		return new JsonPathResultMatchers(expression).value(matcher);
	}

	/**
	 * Access to response body assertions using an XPath to inspect a specific
	 * subset of the body. The XPath expression can be a parameterized string
	 * using formatting specifiers as defined in
	 * {@link String#format(String, Object...)}.
	 * @param expression the XPath optionally parameterized with arguments
	 * @param args arguments to parameterize the XPath expression with
	 */
	public static XpathResultMatchers xpath(String expression, Object... args) throws XPathExpressionException {
		return new XpathResultMatchers(expression, null, args);
	}

	/**
	 * Access to response body assertions using an XPath to inspect a specific
	 * subset of the body. The XPath expression can be a parameterized string
	 * using formatting specifiers as defined in
	 * {@link String#format(String, Object...)}.
	 * @param expression the XPath optionally parameterized with arguments
	 * @param namespaces namespaces referenced in the XPath expression
	 * @param args arguments to parameterize the XPath expression with
	 */
	public static XpathResultMatchers xpath(String expression, Map<String, String> namespaces, Object... args)
			throws XPathExpressionException {

		return new XpathResultMatchers(expression, namespaces, args);
	}

	/**
	 * Access to response cookie assertions.
	 */
	public static CookieResultMatchers cookie() {
		return new CookieResultMatchers();
	}

}


File: spring-test/src/test/java/org/springframework/test/util/JsonPathExpectationsHelperTests.java
/*
 * Copyright 2004-2013 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.test.util;

import org.junit.Test;

import static org.junit.Assert.*;

/**
 * Test fixture for {@link JsonPathExpectationsHelper}.
 *
 * @author Rossen Stoyanchev
 */
public class JsonPathExpectationsHelperTests {


	@Test
	public void test() throws Exception {
		try {
			new JsonPathExpectationsHelper("$.nr").assertValue("{ \"nr\" : 5 }", "5");
			fail("Expected exception");
		}
		catch (AssertionError ex) {
			assertEquals("For JSON path $.nr type of value expected:<class java.lang.String> but was:<class java.lang.Integer>",
					ex.getMessage());
		}
	}

}


File: spring-test/src/test/java/org/springframework/test/web/servlet/result/JsonPathResultMatchersTests.java
/*
 * Copyright 2002-2012 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.test.web.servlet.result;

import org.hamcrest.Matchers;
import org.junit.Test;

import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.test.web.servlet.StubMvcResult;

/**
 * Tests for {@link JsonPathResultMatchers}.
 *
 * @author Rossen Stoyanchev
 */
public class JsonPathResultMatchersTests {

	@Test
	public void value() throws Exception {
		new JsonPathResultMatchers("$.foo").value("bar").match(getStubMvcResult());
	}

	@Test(expected=AssertionError.class)
	public void valueNoMatch() throws Exception {
		new JsonPathResultMatchers("$.foo").value("bogus").match(getStubMvcResult());
	}

	@Test
	public void valueMatcher() throws Exception {
		new JsonPathResultMatchers("$.foo").value(Matchers.equalTo("bar")).match(getStubMvcResult());
	}

	@Test(expected=AssertionError.class)
	public void valueMatcherNoMatch() throws Exception {
		new JsonPathResultMatchers("$.foo").value(Matchers.equalTo("bogus")).match(getStubMvcResult());
	}

	@Test
	public void exists() throws Exception {
		new JsonPathResultMatchers("$.foo").exists().match(getStubMvcResult());
	}

	@Test(expected=AssertionError.class)
	public void existsNoMatch() throws Exception {
		new JsonPathResultMatchers("$.bogus").exists().match(getStubMvcResult());
	}

	@Test
	public void doesNotExist() throws Exception {
		new JsonPathResultMatchers("$.bogus").doesNotExist().match(getStubMvcResult());
	}

	@Test(expected=AssertionError.class)
	public void doesNotExistNoMatch() throws Exception {
		new JsonPathResultMatchers("$.foo").doesNotExist().match(getStubMvcResult());
	}

	@Test
	public void isArrayMatch() throws Exception {
		new JsonPathResultMatchers("$.qux").isArray().match(getStubMvcResult());
	}

	@Test(expected=AssertionError.class)
	public void isArrayNoMatch() throws Exception {
		new JsonPathResultMatchers("$.bar").isArray().match(getStubMvcResult());
	}


	private static final String RESPONSE_CONTENT = "{\"foo\":\"bar\", \"qux\":[\"baz1\",\"baz2\"]}";

	private StubMvcResult getStubMvcResult() throws Exception {
		MockHttpServletResponse response = new MockHttpServletResponse();
		response.addHeader("Content-Type", "application/json");
		response.getWriter().print(new String(RESPONSE_CONTENT.getBytes("ISO-8859-1")));
		return new StubMvcResult(null, null, null, null, null, null, response);
	}

}
