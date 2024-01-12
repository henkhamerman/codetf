Refactoring Types: ['Inline Method']
etty/handler/codec/http/DefaultFullHttpRequest.java
/*
 * Copyright 2013 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */
package io.netty.handler.codec.http;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;

/**
 * Default implementation of {@link FullHttpRequest}.
 */
public class DefaultFullHttpRequest extends DefaultHttpRequest implements FullHttpRequest {
    private static final int HASH_CODE_PRIME = 31;
    private final ByteBuf content;
    private final HttpHeaders trailingHeader;
    private final boolean validateHeaders;

    public DefaultFullHttpRequest(HttpVersion httpVersion, HttpMethod method, String uri) {
        this(httpVersion, method, uri, Unpooled.buffer(0));
    }

    public DefaultFullHttpRequest(HttpVersion httpVersion, HttpMethod method, String uri, ByteBuf content) {
        this(httpVersion, method, uri, content, true);
    }

    public DefaultFullHttpRequest(HttpVersion httpVersion, HttpMethod method, String uri, boolean validateHeaders) {
        this(httpVersion, method, uri, Unpooled.buffer(0), true);
    }

    public DefaultFullHttpRequest(HttpVersion httpVersion, HttpMethod method, String uri,
                                  ByteBuf content, boolean validateHeaders) {
        super(httpVersion, method, uri, validateHeaders);
        if (content == null) {
            throw new NullPointerException("content");
        }
        this.content = content;
        trailingHeader = new DefaultHttpHeaders(validateHeaders);
        this.validateHeaders = validateHeaders;
    }

    @Override
    public HttpHeaders trailingHeaders() {
        return trailingHeader;
    }

    @Override
    public ByteBuf content() {
        return content;
    }

    @Override
    public int refCnt() {
        return content.refCnt();
    }

    @Override
    public FullHttpRequest retain() {
        content.retain();
        return this;
    }

    @Override
    public FullHttpRequest retain(int increment) {
        content.retain(increment);
        return this;
    }

    @Override
    public FullHttpRequest touch() {
        content.touch();
        return this;
    }

    @Override
    public FullHttpRequest touch(Object hint) {
        content.touch(hint);
        return this;
    }

    @Override
    public boolean release() {
        return content.release();
    }

    @Override
    public boolean release(int decrement) {
        return content.release(decrement);
    }

    @Override
    public FullHttpRequest setProtocolVersion(HttpVersion version) {
        super.setProtocolVersion(version);
        return this;
    }

    @Override
    public FullHttpRequest setMethod(HttpMethod method) {
        super.setMethod(method);
        return this;
    }

    @Override
    public FullHttpRequest setUri(String uri) {
        super.setUri(uri);
        return this;
    }

    /**
     * Copy this object
     *
     * @param copyContent
     * <ul>
     * <li>{@code true} if this object's {@link #content()} should be used to copy.</li>
     * <li>{@code false} if {@code newContent} should be used instead.</li>
     * </ul>
     * @param newContent
     * <ul>
     * <li>if {@code copyContent} is false then this will be used in the copy's content.</li>
     * <li>if {@code null} then a default buffer of 0 size will be selected</li>
     * </ul>
     * @return A copy of this object
     */
    private FullHttpRequest copy(boolean copyContent, ByteBuf newContent) {
        DefaultFullHttpRequest copy = new DefaultFullHttpRequest(
                protocolVersion(), method(), uri(),
                copyContent ? content().copy() :
                    newContent == null ? Unpooled.buffer(0) : newContent);
        copy.headers().set(headers());
        copy.trailingHeaders().set(trailingHeaders());
        return copy;
    }

    @Override
    public FullHttpRequest copy(ByteBuf newContent) {
        return copy(false, newContent);
    }

    @Override
    public FullHttpRequest copy() {
        return copy(true, null);
    }

    @Override
    public FullHttpRequest duplicate() {
        DefaultFullHttpRequest duplicate = new DefaultFullHttpRequest(
                protocolVersion(), method(), uri(), content().duplicate(), validateHeaders);
        duplicate.headers().set(headers());
        duplicate.trailingHeaders().set(trailingHeaders());
        return duplicate;
    }

    @Override
    public int hashCode() {
        int result = 1;
        result = HASH_CODE_PRIME * result + content().hashCode();
        result = HASH_CODE_PRIME * result + trailingHeaders().hashCode();
        result = HASH_CODE_PRIME * result + super.hashCode();
        return result;
    }

    @Override
    public boolean equals(Object o) {
        if (!(o instanceof DefaultFullHttpRequest)) {
            return false;
        }

        DefaultFullHttpRequest other = (DefaultFullHttpRequest) o;

        return super.equals(other) &&
               content().equals(other.content()) &&
               trailingHeaders().equals(other.trailingHeaders());
    }

    @Override
    public String toString() {
        return HttpMessageUtil.appendFullRequest(new StringBuilder(256), this).toString();
    }
}


File: codec-http/src/main/java/io/netty/handler/codec/http/DefaultHttpHeaders.java
/*
 * Copyright 2012 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */
package io.netty.handler.codec.http;

import io.netty.handler.codec.DefaultTextHeaders;
import io.netty.handler.codec.TextHeaders;
import io.netty.util.AsciiString;
import io.netty.util.ByteProcessor;
import io.netty.util.internal.PlatformDependent;

import java.util.Calendar;
import java.util.Date;

public class DefaultHttpHeaders extends DefaultTextHeaders implements HttpHeaders {

    private static final int HIGHEST_INVALID_NAME_CHAR_MASK = ~63;
    private static final int HIGHEST_INVALID_VALUE_CHAR_MASK = ~15;

    /**
     * A look-up table used for checking if a character in a header name is prohibited.
     */
    private static final byte[] LOOKUP_TABLE = new byte[~HIGHEST_INVALID_NAME_CHAR_MASK + 1];

    static {
        LOOKUP_TABLE['\t'] = -1;
        LOOKUP_TABLE['\n'] = -1;
        LOOKUP_TABLE[0x0b] = -1;
        LOOKUP_TABLE['\f'] = -1;
        LOOKUP_TABLE[' '] = -1;
        LOOKUP_TABLE[','] = -1;
        LOOKUP_TABLE[':'] = -1;
        LOOKUP_TABLE[';'] = -1;
        LOOKUP_TABLE['='] = -1;
    }

    private static final class HttpHeadersValidationConverter extends DefaultTextValueTypeConverter {
        private final boolean validate;

        HttpHeadersValidationConverter(boolean validate) {
            this.validate = validate;
        }

        @Override
        public CharSequence convertObject(Object value) {
            if (value == null) {
                throw new NullPointerException("value");
            }

            CharSequence seq;
            if (value instanceof CharSequence) {
                seq = (CharSequence) value;
            } else if (value instanceof Number) {
                seq = value.toString();
            } else if (value instanceof Date) {
                seq = HttpHeaderDateFormat.get().format((Date) value);
            } else if (value instanceof Calendar) {
                seq = HttpHeaderDateFormat.get().format(((Calendar) value).getTime());
            } else {
                seq = value.toString();
            }

            if (validate) {
                if (value instanceof AsciiString) {
                    validateValue((AsciiString) seq);
                } else {
                    validateValue(seq);
                }
            }

            return seq;
        }

        private static final class ValidateValueProcessor implements ByteProcessor {
            private final CharSequence seq;
            private int state;

            public ValidateValueProcessor(CharSequence seq) {
                this.seq = seq;
            }

            @Override
            public boolean process(byte value) throws Exception {
                state = validateValueChar(state, (char) value, seq);
                return true;
            }

            public int state() {
                return state;
            }
        }

        private static void validateValue(AsciiString seq) {
            ValidateValueProcessor processor = new ValidateValueProcessor(seq);
            try {
                seq.forEachByte(processor);
            } catch (Throwable t) {
                PlatformDependent.throwException(t);
            }

            if (processor.state() != 0) {
                throw new IllegalArgumentException("a header value must not end with '\\r' or '\\n':" + seq);
            }
        }

        private static void validateValue(CharSequence seq) {
            int state = 0;
            // Start looping through each of the character
            for (int index = 0; index < seq.length(); index++) {
                state = validateValueChar(state, seq.charAt(index), seq);
            }

            if (state != 0) {
                throw new IllegalArgumentException("a header value must not end with '\\r' or '\\n':" + seq);
            }
        }

        private static int validateValueChar(int state, char c, CharSequence seq) {
            /*
             * State:
             * 0: Previous character was neither CR nor LF
             * 1: The previous character was CR
             * 2: The previous character was LF
             */
            if ((c & HIGHEST_INVALID_VALUE_CHAR_MASK) == 0) {
                // Check the absolutely prohibited characters.
                switch (c) {
                case 0x0: // NULL
                    throw new IllegalArgumentException("a header value contains a prohibited character '\0': " + seq);
                case 0x0b: // Vertical tab
                    throw new IllegalArgumentException("a header value contains a prohibited character '\\v': " + seq);
                case '\f':
                    throw new IllegalArgumentException("a header value contains a prohibited character '\\f': " + seq);
                }
            }

            // Check the CRLF (HT | SP) pattern
            switch (state) {
            case 0:
                switch (c) {
                case '\r':
                    state = 1;
                    break;
                case '\n':
                    state = 2;
                    break;
                }
                break;
            case 1:
                switch (c) {
                case '\n':
                    state = 2;
                    break;
                default:
                    throw new IllegalArgumentException("only '\\n' is allowed after '\\r': " + seq);
                }
                break;
            case 2:
                switch (c) {
                case '\t':
                case ' ':
                    state = 0;
                    break;
                default:
                    throw new IllegalArgumentException("only ' ' and '\\t' are allowed after '\\n': " + seq);
                }
            }
            return state;
        }
    }

    static class HttpHeadersNameConverter implements NameConverter<CharSequence> {
        protected final boolean validate;

        private static final class ValidateNameProcessor implements ByteProcessor {
            private final CharSequence seq;

            public ValidateNameProcessor(CharSequence seq) {
                this.seq = seq;
            }

            @Override
            public boolean process(byte value) throws Exception {
                // Check to see if the character is not an ASCII character.
                if (value < 0) {
                    throw new IllegalArgumentException("a header name cannot contain non-ASCII character: " + seq);
                }
                validateNameChar(value, seq);
                return true;
            }
        }

        HttpHeadersNameConverter(boolean validate) {
            this.validate = validate;
        }

        @Override
        public CharSequence convertName(CharSequence name) {
            if (validate) {
                if (name instanceof AsciiString) {
                    validateName((AsciiString) name);
                } else {
                    validateName(name);
                }
            }

            return name;
        }

        private static void validateName(AsciiString name) {
            try {
                name.forEachByte(new ValidateNameProcessor(name));
            } catch (Throwable t) {
                PlatformDependent.throwException(t);
            }
        }

        private static void validateName(CharSequence name) {
            // Go through each characters in the name.
            for (int index = 0; index < name.length(); index++) {
                char c = name.charAt(index);

                // Check to see if the character is not an ASCII character.
                if (c > 127) {
                    throw new IllegalArgumentException("a header name cannot contain non-ASCII characters: " + name);
                }

                // Check for prohibited characters.
                validateNameChar(c, name);
            }
        }

        private static void validateNameChar(int character, CharSequence seq) {
            if ((character & HIGHEST_INVALID_NAME_CHAR_MASK) == 0 && LOOKUP_TABLE[character] != 0) {
                throw new IllegalArgumentException(
                        "a header name cannot contain the following prohibited characters: =,;: \\t\\r\\n\\v\\f: " +
                                seq);
            }
        }
    }

    private static final HttpHeadersValidationConverter
        VALIDATE_OBJECT_CONVERTER = new HttpHeadersValidationConverter(true);
    private static final HttpHeadersValidationConverter
        NO_VALIDATE_OBJECT_CONVERTER = new HttpHeadersValidationConverter(false);
    private static final HttpHeadersNameConverter VALIDATE_NAME_CONVERTER = new HttpHeadersNameConverter(true);
    private static final HttpHeadersNameConverter NO_VALIDATE_NAME_CONVERTER = new HttpHeadersNameConverter(false);

    public DefaultHttpHeaders() {
        this(true);
    }

    public DefaultHttpHeaders(boolean validate) {
        this(true, validate? VALIDATE_NAME_CONVERTER : NO_VALIDATE_NAME_CONVERTER, false);
    }

    protected DefaultHttpHeaders(boolean validate, boolean singleHeaderFields) {
        this(true, validate? VALIDATE_NAME_CONVERTER : NO_VALIDATE_NAME_CONVERTER, singleHeaderFields);
    }

    protected DefaultHttpHeaders(boolean validate, NameConverter<CharSequence> nameConverter,
                                 boolean singleHeaderFields) {
        super(true, validate ? VALIDATE_OBJECT_CONVERTER : NO_VALIDATE_OBJECT_CONVERTER, nameConverter,
                singleHeaderFields);
    }

    @Override
    public HttpHeaders add(CharSequence name, CharSequence value) {
        super.add(name, value);
        return this;
    }

    @Override
    public HttpHeaders add(CharSequence name, Iterable<? extends CharSequence> values) {
        super.add(name, values);
        return this;
    }

    @Override
    public HttpHeaders add(CharSequence name, CharSequence... values) {
        super.add(name, values);
        return this;
    }

    @Override
    public HttpHeaders addObject(CharSequence name, Object value) {
        super.addObject(name, value);
        return this;
    }

    @Override
    public HttpHeaders addObject(CharSequence name, Iterable<?> values) {
        super.addObject(name, values);
        return this;
    }

    @Override
    public HttpHeaders addObject(CharSequence name, Object... values) {
        super.addObject(name, values);
        return this;
    }

    @Override
    public HttpHeaders addBoolean(CharSequence name, boolean value) {
        super.addBoolean(name, value);
        return this;
    }

    @Override
    public HttpHeaders addChar(CharSequence name, char value) {
        super.addChar(name, value);
        return this;
    }

    @Override
    public HttpHeaders addByte(CharSequence name, byte value) {
        super.addByte(name, value);
        return this;
    }

    @Override
    public HttpHeaders addShort(CharSequence name, short value) {
        super.addShort(name, value);
        return this;
    }

    @Override
    public HttpHeaders addInt(CharSequence name, int value) {
        super.addInt(name, value);
        return this;
    }

    @Override
    public HttpHeaders addLong(CharSequence name, long value) {
        super.addLong(name, value);
        return this;
    }

    @Override
    public HttpHeaders addFloat(CharSequence name, float value) {
        super.addFloat(name, value);
        return this;
    }

    @Override
    public HttpHeaders addDouble(CharSequence name, double value) {
        super.addDouble(name, value);
        return this;
    }

    @Override
    public HttpHeaders addTimeMillis(CharSequence name, long value) {
        super.addTimeMillis(name, value);
        return this;
    }

    @Override
    public HttpHeaders add(TextHeaders headers) {
        super.add(headers);
        return this;
    }

    @Override
    public HttpHeaders set(CharSequence name, CharSequence value) {
        super.set(name, value);
        return this;
    }

    @Override
    public HttpHeaders set(CharSequence name, Iterable<? extends CharSequence> values) {
        super.set(name, values);
        return this;
    }

    @Override
    public HttpHeaders set(CharSequence name, CharSequence... values) {
        super.set(name, values);
        return this;
    }

    @Override
    public HttpHeaders setObject(CharSequence name, Object value) {
        super.setObject(name, value);
        return this;
    }

    @Override
    public HttpHeaders setObject(CharSequence name, Iterable<?> values) {
        super.setObject(name, values);
        return this;
    }

    @Override
    public HttpHeaders setObject(CharSequence name, Object... values) {
        super.setObject(name, values);
        return this;
    }

    @Override
    public HttpHeaders setBoolean(CharSequence name, boolean value) {
        super.setBoolean(name, value);
        return this;
    }

    @Override
    public HttpHeaders setChar(CharSequence name, char value) {
        super.setChar(name, value);
        return this;
    }

    @Override
    public HttpHeaders setByte(CharSequence name, byte value) {
        super.setByte(name, value);
        return this;
    }

    @Override
    public HttpHeaders setShort(CharSequence name, short value) {
        super.setShort(name, value);
        return this;
    }

    @Override
    public HttpHeaders setInt(CharSequence name, int value) {
        super.setInt(name, value);
        return this;
    }

    @Override
    public HttpHeaders setLong(CharSequence name, long value) {
        super.setLong(name, value);
        return this;
    }

    @Override
    public HttpHeaders setFloat(CharSequence name, float value) {
        super.setFloat(name, value);
        return this;
    }

    @Override
    public HttpHeaders setDouble(CharSequence name, double value) {
        super.setDouble(name, value);
        return this;
    }

    @Override
    public HttpHeaders setTimeMillis(CharSequence name, long value) {
        super.setTimeMillis(name, value);
        return this;
    }

    @Override
    public HttpHeaders set(TextHeaders headers) {
        super.set(headers);
        return this;
    }

    @Override
    public HttpHeaders setAll(TextHeaders headers) {
        super.setAll(headers);
        return this;
    }

    @Override
    public HttpHeaders clear() {
        super.clear();
        return this;
    }
}


File: codec-http/src/main/java/io/netty/handler/codec/http/DefaultLastHttpContent.java
/*
 * Copyright 2012 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */
package io.netty.handler.codec.http;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import io.netty.util.internal.StringUtil;

import java.util.Map;

/**
 * The default {@link LastHttpContent} implementation.
 */
public class DefaultLastHttpContent extends DefaultHttpContent implements LastHttpContent {

    private final HttpHeaders trailingHeaders;
    private final boolean validateHeaders;

    public DefaultLastHttpContent() {
        this(Unpooled.buffer(0));
    }

    public DefaultLastHttpContent(ByteBuf content) {
        this(content, true);
    }

    public DefaultLastHttpContent(ByteBuf content, boolean validateHeaders) {
        super(content);
        trailingHeaders = new TrailingHttpHeaders(validateHeaders);
        this.validateHeaders = validateHeaders;
    }

    @Override
    public LastHttpContent copy() {
        DefaultLastHttpContent copy = new DefaultLastHttpContent(content().copy(), validateHeaders);
        copy.trailingHeaders().set(trailingHeaders());
        return copy;
    }

    @Override
    public LastHttpContent duplicate() {
        DefaultLastHttpContent copy = new DefaultLastHttpContent(content().duplicate(), validateHeaders);
        copy.trailingHeaders().set(trailingHeaders());
        return copy;
    }

    @Override
    public LastHttpContent retain(int increment) {
        super.retain(increment);
        return this;
    }

    @Override
    public LastHttpContent retain() {
        super.retain();
        return this;
    }

    @Override
    public LastHttpContent touch() {
        super.touch();
        return this;
    }

    @Override
    public LastHttpContent touch(Object hint) {
        super.touch(hint);
        return this;
    }

    @Override
    public HttpHeaders trailingHeaders() {
        return trailingHeaders;
    }

    @Override
    public String toString() {
        StringBuilder buf = new StringBuilder(super.toString());
        buf.append(StringUtil.NEWLINE);
        appendHeaders(buf);

        // Remove the last newline.
        buf.setLength(buf.length() - StringUtil.NEWLINE.length());
        return buf.toString();
    }

    private void appendHeaders(StringBuilder buf) {
        for (Map.Entry<CharSequence, CharSequence> e : trailingHeaders()) {
            buf.append(e.getKey());
            buf.append(": ");
            buf.append(e.getValue());
            buf.append(StringUtil.NEWLINE);
        }
    }

    private static final class TrailingHttpHeaders extends DefaultHttpHeaders {
        private static final class TrailingHttpHeadersNameConverter extends HttpHeadersNameConverter {
            TrailingHttpHeadersNameConverter(boolean validate) {
                super(validate);
            }

            @Override
            public CharSequence convertName(CharSequence name) {
                name = super.convertName(name);
                if (validate) {
                    if (HttpHeaderNames.CONTENT_LENGTH.equalsIgnoreCase(name)
                                    || HttpHeaderNames.TRANSFER_ENCODING.equalsIgnoreCase(name)
                                    || HttpHeaderNames.TRAILER.equalsIgnoreCase(name)) {
                        throw new IllegalArgumentException("prohibited trailing header: " + name);
                    }
                }
                return name;
            }
        }

        private static final TrailingHttpHeadersNameConverter
            VALIDATE_NAME_CONVERTER = new TrailingHttpHeadersNameConverter(true);
        private static final TrailingHttpHeadersNameConverter
            NO_VALIDATE_NAME_CONVERTER = new TrailingHttpHeadersNameConverter(false);

        TrailingHttpHeaders(boolean validate) {
            super(validate, validate ? VALIDATE_NAME_CONVERTER : NO_VALIDATE_NAME_CONVERTER, false);
        }
    }
}


File: codec-http/src/main/java/io/netty/handler/codec/http/HttpHeaderUtil.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package io.netty.handler.codec.http;

import io.netty.buffer.ByteBuf;

import java.util.Iterator;
import java.util.List;

public final class HttpHeaderUtil {

    /**
     * Returns {@code true} if and only if the connection can remain open and
     * thus 'kept alive'.  This methods respects the value of the
     * {@code "Connection"} header first and then the return value of
     * {@link HttpVersion#isKeepAliveDefault()}.
     */
    public static boolean isKeepAlive(HttpMessage message) {
        CharSequence connection = message.headers().get(HttpHeaderNames.CONNECTION);
        if (connection != null && HttpHeaderValues.CLOSE.equalsIgnoreCase(connection)) {
            return false;
        }

        if (message.protocolVersion().isKeepAliveDefault()) {
            return !HttpHeaderValues.CLOSE.equalsIgnoreCase(connection);
        } else {
            return HttpHeaderValues.KEEP_ALIVE.equalsIgnoreCase(connection);
        }
    }

    /**
     * Sets the value of the {@code "Connection"} header depending on the
     * protocol version of the specified message.  This getMethod sets or removes
     * the {@code "Connection"} header depending on what the default keep alive
     * mode of the message's protocol version is, as specified by
     * {@link HttpVersion#isKeepAliveDefault()}.
     * <ul>
     * <li>If the connection is kept alive by default:
     *     <ul>
     *     <li>set to {@code "close"} if {@code keepAlive} is {@code false}.</li>
     *     <li>remove otherwise.</li>
     *     </ul></li>
     * <li>If the connection is closed by default:
     *     <ul>
     *     <li>set to {@code "keep-alive"} if {@code keepAlive} is {@code true}.</li>
     *     <li>remove otherwise.</li>
     *     </ul></li>
     * </ul>
     */
    public static void setKeepAlive(HttpMessage message, boolean keepAlive) {
        HttpHeaders h = message.headers();
        if (message.protocolVersion().isKeepAliveDefault()) {
            if (keepAlive) {
                h.remove(HttpHeaderNames.CONNECTION);
            } else {
                h.set(HttpHeaderNames.CONNECTION, HttpHeaderValues.CLOSE);
            }
        } else {
            if (keepAlive) {
                h.set(HttpHeaderNames.CONNECTION, HttpHeaderValues.KEEP_ALIVE);
            } else {
                h.remove(HttpHeaderNames.CONNECTION);
            }
        }
    }

    /**
     * Returns the length of the content.  Please note that this value is
     * not retrieved from {@link HttpContent#content()} but from the
     * {@code "Content-Length"} header, and thus they are independent from each
     * other.
     *
     * @return the content length
     *
     * @throws NumberFormatException
     *         if the message does not have the {@code "Content-Length"} header
     *         or its value is not a number
     */
    public static long getContentLength(HttpMessage message) {
        Long value = message.headers().getLong(HttpHeaderNames.CONTENT_LENGTH);
        if (value != null) {
            return value;
        }

        // We know the content length if it's a Web Socket message even if
        // Content-Length header is missing.
        long webSocketContentLength = getWebSocketContentLength(message);
        if (webSocketContentLength >= 0) {
            return webSocketContentLength;
        }

        // Otherwise we don't.
        throw new NumberFormatException("header not found: " + HttpHeaderNames.CONTENT_LENGTH);
    }

    /**
     * Returns the length of the content.  Please note that this value is
     * not retrieved from {@link HttpContent#content()} but from the
     * {@code "Content-Length"} header, and thus they are independent from each
     * other.
     *
     * @return the content length or {@code defaultValue} if this message does
     *         not have the {@code "Content-Length"} header or its value is not
     *         a number
     */
    public static long getContentLength(HttpMessage message, long defaultValue) {
        Long value = message.headers().getLong(HttpHeaderNames.CONTENT_LENGTH);
        if (value != null) {
            return value;
        }

        // We know the content length if it's a Web Socket message even if
        // Content-Length header is missing.
        long webSocketContentLength = getWebSocketContentLength(message);
        if (webSocketContentLength >= 0) {
            return webSocketContentLength;
        }

        // Otherwise we don't.
        return defaultValue;
    }

    /**
     * Returns the content length of the specified web socket message.  If the
     * specified message is not a web socket message, {@code -1} is returned.
     */
    private static int getWebSocketContentLength(HttpMessage message) {
        // WebSockset messages have constant content-lengths.
        HttpHeaders h = message.headers();
        if (message instanceof HttpRequest) {
            HttpRequest req = (HttpRequest) message;
            if (HttpMethod.GET.equals(req.method()) &&
                    h.contains(HttpHeaderNames.SEC_WEBSOCKET_KEY1) &&
                    h.contains(HttpHeaderNames.SEC_WEBSOCKET_KEY2)) {
                return 8;
            }
        } else if (message instanceof HttpResponse) {
            HttpResponse res = (HttpResponse) message;
            if (res.status().code() == 101 &&
                    h.contains(HttpHeaderNames.SEC_WEBSOCKET_ORIGIN) &&
                    h.contains(HttpHeaderNames.SEC_WEBSOCKET_LOCATION)) {
                return 16;
            }
        }

        // Not a web socket message
        return -1;
    }

    /**
     * Sets the {@code "Content-Length"} header.
     */
    public static void setContentLength(HttpMessage message, long length) {
        message.headers().setLong(HttpHeaderNames.CONTENT_LENGTH, length);
    }

    public static boolean isContentLengthSet(HttpMessage m) {
        return m.headers().contains(HttpHeaderNames.CONTENT_LENGTH);
    }

    /**
     * Returns {@code true} if and only if the specified message contains the
     * {@code "Expect: 100-continue"} header.
     */
    public static boolean is100ContinueExpected(HttpMessage message) {
        // Expect: 100-continue is for requests only.
        if (!(message instanceof HttpRequest)) {
            return false;
        }

        // It works only on HTTP/1.1 or later.
        if (message.protocolVersion().compareTo(HttpVersion.HTTP_1_1) < 0) {
            return false;
        }

        // In most cases, there will be one or zero 'Expect' header.
        CharSequence value = message.headers().get(HttpHeaderNames.EXPECT);
        if (value == null) {
            return false;
        }
        if (HttpHeaderValues.CONTINUE.equalsIgnoreCase(value)) {
            return true;
        }

        // Multiple 'Expect' headers.  Search through them.
        return message.headers().contains(HttpHeaderNames.EXPECT, HttpHeaderValues.CONTINUE, true);
    }

    /**
     * Sets or removes the {@code "Expect: 100-continue"} header to / from the
     * specified message.  If the specified {@code value} is {@code true},
     * the {@code "Expect: 100-continue"} header is set and all other previous
     * {@code "Expect"} headers are removed.  Otherwise, all {@code "Expect"}
     * headers are removed completely.
     */
    public static void set100ContinueExpected(HttpMessage message, boolean expected) {
        if (expected) {
            message.headers().set(HttpHeaderNames.EXPECT, HttpHeaderValues.CONTINUE);
        } else {
            message.headers().remove(HttpHeaderNames.EXPECT);
        }
    }

    /**
     * Checks to see if the transfer encoding in a specified {@link HttpMessage} is chunked
     *
     * @param message The message to check
     * @return True if transfer encoding is chunked, otherwise false
     */
    public static boolean isTransferEncodingChunked(HttpMessage message) {
        return message.headers().contains(HttpHeaderNames.TRANSFER_ENCODING, HttpHeaderValues.CHUNKED, true);
    }

    public static void setTransferEncodingChunked(HttpMessage m, boolean chunked) {
        if (chunked) {
            m.headers().add(HttpHeaderNames.TRANSFER_ENCODING, HttpHeaderValues.CHUNKED);
            m.headers().remove(HttpHeaderNames.CONTENT_LENGTH);
        } else {
            List<CharSequence> values = m.headers().getAll(HttpHeaderNames.TRANSFER_ENCODING);
            if (values.isEmpty()) {
                return;
            }
            Iterator<CharSequence> valuesIt = values.iterator();
            while (valuesIt.hasNext()) {
                CharSequence value = valuesIt.next();
                if (HttpHeaderValues.CHUNKED.equalsIgnoreCase(value)) {
                    valuesIt.remove();
                }
            }
            if (values.isEmpty()) {
                m.headers().remove(HttpHeaderNames.TRANSFER_ENCODING);
            } else {
                m.headers().set(HttpHeaderNames.TRANSFER_ENCODING, values);
            }
        }
    }

    static void encodeAscii0(CharSequence seq, ByteBuf buf) {
        int length = seq.length();
        for (int i = 0 ; i < length; i++) {
            buf.writeByte(c2b(seq.charAt(i)));
        }
    }

    private static byte c2b(char c) {
        if (c > 255) {
            return '?';
        }
        return (byte) c;
    }

    private HttpHeaderUtil() { }
}


File: codec-http/src/main/java/io/netty/handler/codec/http/HttpHeadersEncoder.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package io.netty.handler.codec.http;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufUtil;
import io.netty.handler.codec.TextHeaders.EntryVisitor;
import io.netty.util.AsciiString;

import java.util.Map.Entry;

final class HttpHeadersEncoder implements EntryVisitor {

    private final ByteBuf buf;

    HttpHeadersEncoder(ByteBuf buf) {
        this.buf = buf;
    }

    @Override
    public boolean visit(Entry<CharSequence, CharSequence> entry) throws Exception {
        final CharSequence name = entry.getKey();
        final CharSequence value = entry.getValue();
        final ByteBuf buf = this.buf;
        final int nameLen = name.length();
        final int valueLen = value.length();
        final int entryLen = nameLen + valueLen + 4;
        int offset = buf.writerIndex();
        buf.ensureWritable(entryLen);
        writeAscii(buf, offset, name, nameLen);
        offset += nameLen;
        buf.setByte(offset ++, ':');
        buf.setByte(offset ++, ' ');
        writeAscii(buf, offset, value, valueLen);
        offset += valueLen;
        buf.setByte(offset ++, '\r');
        buf.setByte(offset ++, '\n');
        buf.writerIndex(offset);
        return true;
    }

    private static void writeAscii(ByteBuf buf, int offset, CharSequence value, int valueLen) {
        if (value instanceof AsciiString) {
            writeAsciiString(buf, offset, (AsciiString) value, valueLen);
        } else {
            writeCharSequence(buf, offset, value, valueLen);
        }
    }

    private static void writeAsciiString(ByteBuf buf, int offset, AsciiString value, int valueLen) {
        ByteBufUtil.copy(value, 0, buf, offset, valueLen);
    }

    private static void writeCharSequence(ByteBuf buf, int offset, CharSequence value, int valueLen) {
        for (int i = 0; i < valueLen; i ++) {
            buf.setByte(offset ++, c2b(value.charAt(i)));
        }
    }

    private static int c2b(char ch) {
        return ch < 256? (byte) ch : '?';
    }
}


File: codec-http/src/main/java/io/netty/handler/codec/http/HttpObjectEncoder.java
/*
 * Copyright 2012 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */
package io.netty.handler.codec.http;

import io.netty.buffer.ByteBuf;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.FileRegion;
import io.netty.handler.codec.MessageToMessageEncoder;
import io.netty.util.CharsetUtil;
import io.netty.util.internal.PlatformDependent;
import io.netty.util.internal.StringUtil;

import java.util.List;

import static io.netty.buffer.Unpooled.*;
import static io.netty.handler.codec.http.HttpConstants.*;

/**
 * Encodes an {@link HttpMessage} or an {@link HttpContent} into
 * a {@link ByteBuf}.
 *
 * <h3>Extensibility</h3>
 *
 * Please note that this encoder is designed to be extended to implement
 * a protocol derived from HTTP, such as
 * <a href="http://en.wikipedia.org/wiki/Real_Time_Streaming_Protocol">RTSP</a> and
 * <a href="http://en.wikipedia.org/wiki/Internet_Content_Adaptation_Protocol">ICAP</a>.
 * To implement the encoder of such a derived protocol, extend this class and
 * implement all abstract methods properly.
 */
public abstract class HttpObjectEncoder<H extends HttpMessage> extends MessageToMessageEncoder<Object> {
    private static final byte[] CRLF = { CR, LF };
    private static final byte[] ZERO_CRLF = { '0', CR, LF };
    private static final byte[] ZERO_CRLF_CRLF = { '0', CR, LF, CR, LF };
    private static final ByteBuf CRLF_BUF = unreleasableBuffer(directBuffer(CRLF.length).writeBytes(CRLF));
    private static final ByteBuf ZERO_CRLF_CRLF_BUF = unreleasableBuffer(directBuffer(ZERO_CRLF_CRLF.length)
            .writeBytes(ZERO_CRLF_CRLF));

    private static final int ST_INIT = 0;
    private static final int ST_CONTENT_NON_CHUNK = 1;
    private static final int ST_CONTENT_CHUNK = 2;

    @SuppressWarnings("RedundantFieldInitialization")
    private int state = ST_INIT;

    @Override
    protected void encode(ChannelHandlerContext ctx, Object msg, List<Object> out) throws Exception {
        ByteBuf buf = null;
        if (msg instanceof HttpMessage) {
            if (state != ST_INIT) {
                throw new IllegalStateException("unexpected message type: " + StringUtil.simpleClassName(msg));
            }

            @SuppressWarnings({ "unchecked", "CastConflictsWithInstanceof" })
            H m = (H) msg;

            buf = ctx.alloc().buffer();
            // Encode the message.
            encodeInitialLine(buf, m);
            encodeHeaders(m.headers(), buf);
            buf.writeBytes(CRLF);
            state = HttpHeaderUtil.isTransferEncodingChunked(m) ? ST_CONTENT_CHUNK : ST_CONTENT_NON_CHUNK;
        }

        // Bypass the encoder in case of an empty buffer, so that the following idiom works:
        //
        //     ch.write(Unpooled.EMPTY_BUFFER).addListener(ChannelFutureListener.CLOSE);
        //
        // See https://github.com/netty/netty/issues/2983 for more information.

        if (msg instanceof ByteBuf && !((ByteBuf) msg).isReadable()) {
            out.add(EMPTY_BUFFER);
            return;
        }

        if (msg instanceof HttpContent || msg instanceof ByteBuf || msg instanceof FileRegion) {

            if (state == ST_INIT) {
                throw new IllegalStateException("unexpected message type: " + StringUtil.simpleClassName(msg));
            }

            final long contentLength = contentLength(msg);
            if (state == ST_CONTENT_NON_CHUNK) {
                if (contentLength > 0) {
                    if (buf != null && buf.writableBytes() >= contentLength && msg instanceof HttpContent) {
                        // merge into other buffer for performance reasons
                        buf.writeBytes(((HttpContent) msg).content());
                        out.add(buf);
                    } else {
                        if (buf != null) {
                            out.add(buf);
                        }
                        out.add(encodeAndRetain(msg));
                    }
                } else {
                    if (buf != null) {
                        out.add(buf);
                    } else {
                        // Need to produce some output otherwise an
                        // IllegalStateException will be thrown
                        out.add(EMPTY_BUFFER);
                    }
                }

                if (msg instanceof LastHttpContent) {
                    state = ST_INIT;
                }
            } else if (state == ST_CONTENT_CHUNK) {
                if (buf != null) {
                    out.add(buf);
                }
                encodeChunkedContent(ctx, msg, contentLength, out);
            } else {
                throw new Error();
            }
        } else {
            if (buf != null) {
                out.add(buf);
            }
        }
    }

    /**
     * Encode the {@link HttpHeaders} into a {@link ByteBuf}.
     */
    protected void encodeHeaders(HttpHeaders headers, ByteBuf buf) throws Exception {
        headers.forEachEntry(new HttpHeadersEncoder(buf));
    }

    private void encodeChunkedContent(ChannelHandlerContext ctx, Object msg, long contentLength, List<Object> out) {
        if (contentLength > 0) {
            byte[] length = Long.toHexString(contentLength).getBytes(CharsetUtil.US_ASCII);
            ByteBuf buf = ctx.alloc().buffer(length.length + 2);
            buf.writeBytes(length);
            buf.writeBytes(CRLF);
            out.add(buf);
            out.add(encodeAndRetain(msg));
            out.add(CRLF_BUF.duplicate());
        }

        if (msg instanceof LastHttpContent) {
            HttpHeaders headers = ((LastHttpContent) msg).trailingHeaders();
            if (headers.isEmpty()) {
                out.add(ZERO_CRLF_CRLF_BUF.duplicate());
            } else {
                ByteBuf buf = ctx.alloc().buffer();
                buf.writeBytes(ZERO_CRLF);
                try {
                    encodeHeaders(headers, buf);
                } catch (Exception ex) {
                    buf.release();
                    PlatformDependent.throwException(ex);
                }
                buf.writeBytes(CRLF);
                out.add(buf);
            }

            state = ST_INIT;
        } else {
            if (contentLength == 0) {
                // Need to produce some output otherwise an
                // IllegalstateException will be thrown
                out.add(EMPTY_BUFFER);
            }
        }
    }

    @Override
    public boolean acceptOutboundMessage(Object msg) throws Exception {
        return msg instanceof HttpObject || msg instanceof ByteBuf || msg instanceof FileRegion;
    }

    private static Object encodeAndRetain(Object msg) {
        if (msg instanceof ByteBuf) {
            return ((ByteBuf) msg).retain();
        }
        if (msg instanceof HttpContent) {
            return ((HttpContent) msg).content().retain();
        }
        if (msg instanceof FileRegion) {
            return ((FileRegion) msg).retain();
        }
        throw new IllegalStateException("unexpected message type: " + StringUtil.simpleClassName(msg));
    }

    private static long contentLength(Object msg) {
        if (msg instanceof HttpContent) {
            return ((HttpContent) msg).content().readableBytes();
        }
        if (msg instanceof ByteBuf) {
            return ((ByteBuf) msg).readableBytes();
        }
        if (msg instanceof FileRegion) {
            return ((FileRegion) msg).count();
        }
        throw new IllegalStateException("unexpected message type: " + StringUtil.simpleClassName(msg));
    }

    protected abstract void encodeInitialLine(ByteBuf buf, H message) throws Exception;
}


File: codec-http/src/main/java/io/netty/handler/codec/spdy/DefaultSpdyHeaders.java
/*
 * Copyright 2013 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */
package io.netty.handler.codec.spdy;

import io.netty.handler.codec.DefaultTextHeaders;
import io.netty.handler.codec.Headers;
import io.netty.handler.codec.TextHeaders;
import io.netty.util.AsciiString;

import java.util.Locale;

public class DefaultSpdyHeaders extends DefaultTextHeaders implements SpdyHeaders {
    private static final Headers.ValueConverter<CharSequence> SPDY_VALUE_CONVERTER =
            new DefaultTextValueTypeConverter() {
        @Override
        public CharSequence convertObject(Object value) {
            CharSequence seq;
            if (value instanceof CharSequence) {
                seq = (CharSequence) value;
            } else {
                seq = value.toString();
            }

            SpdyCodecUtil.validateHeaderValue(seq);
            return seq;
        }
    };

    private static final NameConverter<CharSequence> SPDY_NAME_CONVERTER = new NameConverter<CharSequence>() {
        @Override
        public CharSequence convertName(CharSequence name) {
            if (name instanceof AsciiString) {
                name = ((AsciiString) name).toLowerCase();
            } else {
                name = name.toString().toLowerCase(Locale.US);
            }
            SpdyCodecUtil.validateHeaderName(name);
            return name;
        }
    };

    public DefaultSpdyHeaders() {
        super(true, SPDY_VALUE_CONVERTER, SPDY_NAME_CONVERTER);
    }

    @Override
    public SpdyHeaders add(CharSequence name, CharSequence value) {
        super.add(name, value);
        return this;
    }

    @Override
    public SpdyHeaders add(CharSequence name, Iterable<? extends CharSequence> values) {
        super.add(name, values);
        return this;
    }

    @Override
    public SpdyHeaders add(CharSequence name, CharSequence... values) {
        super.add(name, values);
        return this;
    }

    @Override
    public SpdyHeaders addObject(CharSequence name, Object value) {
        super.addObject(name, value);
        return this;
    }

    @Override
    public SpdyHeaders addObject(CharSequence name, Iterable<?> values) {
        super.addObject(name, values);
        return this;
    }

    @Override
    public SpdyHeaders addObject(CharSequence name, Object... values) {
        super.addObject(name, values);
        return this;
    }

    @Override
    public SpdyHeaders addBoolean(CharSequence name, boolean value) {
        super.addBoolean(name, value);
        return this;
    }

    @Override
    public SpdyHeaders addChar(CharSequence name, char value) {
        super.addChar(name, value);
        return this;
    }

    @Override
    public SpdyHeaders addByte(CharSequence name, byte value) {
        super.addByte(name, value);
        return this;
    }

    @Override
    public SpdyHeaders addShort(CharSequence name, short value) {
        super.addShort(name, value);
        return this;
    }

    @Override
    public SpdyHeaders addInt(CharSequence name, int value) {
        super.addInt(name, value);
        return this;
    }

    @Override
    public SpdyHeaders addLong(CharSequence name, long value) {
        super.addLong(name, value);
        return this;
    }

    @Override
    public SpdyHeaders addFloat(CharSequence name, float value) {
        super.addFloat(name, value);
        return this;
    }

    @Override
    public SpdyHeaders addDouble(CharSequence name, double value) {
        super.addDouble(name, value);
        return this;
    }

    @Override
    public SpdyHeaders addTimeMillis(CharSequence name, long value) {
        super.addTimeMillis(name, value);
        return this;
    }

    @Override
    public SpdyHeaders add(TextHeaders headers) {
        super.add(headers);
        return this;
    }

    @Override
    public SpdyHeaders set(CharSequence name, CharSequence value) {
        super.set(name, value);
        return this;
    }

    @Override
    public SpdyHeaders set(CharSequence name, Iterable<? extends CharSequence> values) {
        super.set(name, values);
        return this;
    }

    @Override
    public SpdyHeaders set(CharSequence name, CharSequence... values) {
        super.set(name, values);
        return this;
    }

    @Override
    public SpdyHeaders setObject(CharSequence name, Object value) {
        super.setObject(name, value);
        return this;
    }

    @Override
    public SpdyHeaders setObject(CharSequence name, Iterable<?> values) {
        super.setObject(name, values);
        return this;
    }

    @Override
    public SpdyHeaders setObject(CharSequence name, Object... values) {
        super.setObject(name, values);
        return this;
    }

    @Override
    public SpdyHeaders setBoolean(CharSequence name, boolean value) {
        super.setBoolean(name, value);
        return this;
    }

    @Override
    public SpdyHeaders setChar(CharSequence name, char value) {
        super.setChar(name, value);
        return this;
    }

    @Override
    public SpdyHeaders setByte(CharSequence name, byte value) {
        super.setByte(name, value);
        return this;
    }

    @Override
    public SpdyHeaders setShort(CharSequence name, short value) {
        super.setShort(name, value);
        return this;
    }

    @Override
    public SpdyHeaders setInt(CharSequence name, int value) {
        super.setInt(name, value);
        return this;
    }

    @Override
    public SpdyHeaders setLong(CharSequence name, long value) {
        super.setLong(name, value);
        return this;
    }

    @Override
    public SpdyHeaders setFloat(CharSequence name, float value) {
        super.setFloat(name, value);
        return this;
    }

    @Override
    public SpdyHeaders setDouble(CharSequence name, double value) {
        super.setDouble(name, value);
        return this;
    }

    @Override
    public SpdyHeaders setTimeMillis(CharSequence name, long value) {
        super.setTimeMillis(name, value);
        return this;
    }

    @Override
    public SpdyHeaders set(TextHeaders headers) {
        super.set(headers);
        return this;
    }

    @Override
    public SpdyHeaders setAll(TextHeaders headers) {
        super.setAll(headers);
        return this;
    }

    @Override
    public SpdyHeaders clear() {
        super.clear();
        return this;
    }
}


File: codec-http/src/main/java/io/netty/handler/codec/spdy/SpdyCodecUtil.java
/*
 * Copyright 2013 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */
package io.netty.handler.codec.spdy;

import io.netty.buffer.ByteBuf;

final class SpdyCodecUtil {

    static final int SPDY_SESSION_STREAM_ID = 0;

    static final int SPDY_HEADER_TYPE_OFFSET   = 2;
    static final int SPDY_HEADER_FLAGS_OFFSET  = 4;
    static final int SPDY_HEADER_LENGTH_OFFSET = 5;
    static final int SPDY_HEADER_SIZE          = 8;

    static final int SPDY_MAX_LENGTH = 0xFFFFFF; // Length is a 24-bit field

    static final byte SPDY_DATA_FLAG_FIN = 0x01;

    static final int SPDY_DATA_FRAME          = 0;
    static final int SPDY_SYN_STREAM_FRAME    = 1;
    static final int SPDY_SYN_REPLY_FRAME     = 2;
    static final int SPDY_RST_STREAM_FRAME    = 3;
    static final int SPDY_SETTINGS_FRAME      = 4;
    static final int SPDY_PUSH_PROMISE_FRAME  = 5;
    static final int SPDY_PING_FRAME          = 6;
    static final int SPDY_GOAWAY_FRAME        = 7;
    static final int SPDY_HEADERS_FRAME       = 8;
    static final int SPDY_WINDOW_UPDATE_FRAME = 9;

    static final byte SPDY_FLAG_FIN            = 0x01;
    static final byte SPDY_FLAG_UNIDIRECTIONAL = 0x02;

    static final byte SPDY_SETTINGS_CLEAR         = 0x01;
    static final byte SPDY_SETTINGS_PERSIST_VALUE = 0x01;
    static final byte SPDY_SETTINGS_PERSISTED     = 0x02;

    static final int SPDY_SETTINGS_MAX_ID = 0xFFFFFF; // ID is a 24-bit field

    static final int SPDY_MAX_NV_LENGTH = 0xFFFF; // Length is a 16-bit field

    // Zlib Dictionary
    static final byte[] SPDY_DICT = {
        0x00, 0x00, 0x00, 0x07, 0x6f, 0x70, 0x74, 0x69,   // - - - - o p t i
        0x6f, 0x6e, 0x73, 0x00, 0x00, 0x00, 0x04, 0x68,   // o n s - - - - h
        0x65, 0x61, 0x64, 0x00, 0x00, 0x00, 0x04, 0x70,   // e a d - - - - p
        0x6f, 0x73, 0x74, 0x00, 0x00, 0x00, 0x03, 0x70,   // o s t - - - - p
        0x75, 0x74, 0x00, 0x00, 0x00, 0x06, 0x64, 0x65,   // u t - - - - d e
        0x6c, 0x65, 0x74, 0x65, 0x00, 0x00, 0x00, 0x05,   // l e t e - - - -
        0x74, 0x72, 0x61, 0x63, 0x65, 0x00, 0x00, 0x00,   // t r a c e - - -
        0x06, 0x61, 0x63, 0x63, 0x65, 0x70, 0x74, 0x00,   // - a c c e p t -
        0x00, 0x00, 0x0e, 0x61, 0x63, 0x63, 0x65, 0x70,   // - - - a c c e p
        0x74, 0x2d, 0x63, 0x68, 0x61, 0x72, 0x73, 0x65,   // t - c h a r s e
        0x74, 0x00, 0x00, 0x00, 0x0f, 0x61, 0x63, 0x63,   // t - - - - a c c
        0x65, 0x70, 0x74, 0x2d, 0x65, 0x6e, 0x63, 0x6f,   // e p t - e n c o
        0x64, 0x69, 0x6e, 0x67, 0x00, 0x00, 0x00, 0x0f,   // d i n g - - - -
        0x61, 0x63, 0x63, 0x65, 0x70, 0x74, 0x2d, 0x6c,   // a c c e p t - l
        0x61, 0x6e, 0x67, 0x75, 0x61, 0x67, 0x65, 0x00,   // a n g u a g e -
        0x00, 0x00, 0x0d, 0x61, 0x63, 0x63, 0x65, 0x70,   // - - - a c c e p
        0x74, 0x2d, 0x72, 0x61, 0x6e, 0x67, 0x65, 0x73,   // t - r a n g e s
        0x00, 0x00, 0x00, 0x03, 0x61, 0x67, 0x65, 0x00,   // - - - - a g e -
        0x00, 0x00, 0x05, 0x61, 0x6c, 0x6c, 0x6f, 0x77,   // - - - a l l o w
        0x00, 0x00, 0x00, 0x0d, 0x61, 0x75, 0x74, 0x68,   // - - - - a u t h
        0x6f, 0x72, 0x69, 0x7a, 0x61, 0x74, 0x69, 0x6f,   // o r i z a t i o
        0x6e, 0x00, 0x00, 0x00, 0x0d, 0x63, 0x61, 0x63,   // n - - - - c a c
        0x68, 0x65, 0x2d, 0x63, 0x6f, 0x6e, 0x74, 0x72,   // h e - c o n t r
        0x6f, 0x6c, 0x00, 0x00, 0x00, 0x0a, 0x63, 0x6f,   // o l - - - - c o
        0x6e, 0x6e, 0x65, 0x63, 0x74, 0x69, 0x6f, 0x6e,   // n n e c t i o n
        0x00, 0x00, 0x00, 0x0c, 0x63, 0x6f, 0x6e, 0x74,   // - - - - c o n t
        0x65, 0x6e, 0x74, 0x2d, 0x62, 0x61, 0x73, 0x65,   // e n t - b a s e
        0x00, 0x00, 0x00, 0x10, 0x63, 0x6f, 0x6e, 0x74,   // - - - - c o n t
        0x65, 0x6e, 0x74, 0x2d, 0x65, 0x6e, 0x63, 0x6f,   // e n t - e n c o
        0x64, 0x69, 0x6e, 0x67, 0x00, 0x00, 0x00, 0x10,   // d i n g - - - -
        0x63, 0x6f, 0x6e, 0x74, 0x65, 0x6e, 0x74, 0x2d,   // c o n t e n t -
        0x6c, 0x61, 0x6e, 0x67, 0x75, 0x61, 0x67, 0x65,   // l a n g u a g e
        0x00, 0x00, 0x00, 0x0e, 0x63, 0x6f, 0x6e, 0x74,   // - - - - c o n t
        0x65, 0x6e, 0x74, 0x2d, 0x6c, 0x65, 0x6e, 0x67,   // e n t - l e n g
        0x74, 0x68, 0x00, 0x00, 0x00, 0x10, 0x63, 0x6f,   // t h - - - - c o
        0x6e, 0x74, 0x65, 0x6e, 0x74, 0x2d, 0x6c, 0x6f,   // n t e n t - l o
        0x63, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x00, 0x00,   // c a t i o n - -
        0x00, 0x0b, 0x63, 0x6f, 0x6e, 0x74, 0x65, 0x6e,   // - - c o n t e n
        0x74, 0x2d, 0x6d, 0x64, 0x35, 0x00, 0x00, 0x00,   // t - m d 5 - - -
        0x0d, 0x63, 0x6f, 0x6e, 0x74, 0x65, 0x6e, 0x74,   // - c o n t e n t
        0x2d, 0x72, 0x61, 0x6e, 0x67, 0x65, 0x00, 0x00,   // - r a n g e - -
        0x00, 0x0c, 0x63, 0x6f, 0x6e, 0x74, 0x65, 0x6e,   // - - c o n t e n
        0x74, 0x2d, 0x74, 0x79, 0x70, 0x65, 0x00, 0x00,   // t - t y p e - -
        0x00, 0x04, 0x64, 0x61, 0x74, 0x65, 0x00, 0x00,   // - - d a t e - -
        0x00, 0x04, 0x65, 0x74, 0x61, 0x67, 0x00, 0x00,   // - - e t a g - -
        0x00, 0x06, 0x65, 0x78, 0x70, 0x65, 0x63, 0x74,   // - - e x p e c t
        0x00, 0x00, 0x00, 0x07, 0x65, 0x78, 0x70, 0x69,   // - - - - e x p i
        0x72, 0x65, 0x73, 0x00, 0x00, 0x00, 0x04, 0x66,   // r e s - - - - f
        0x72, 0x6f, 0x6d, 0x00, 0x00, 0x00, 0x04, 0x68,   // r o m - - - - h
        0x6f, 0x73, 0x74, 0x00, 0x00, 0x00, 0x08, 0x69,   // o s t - - - - i
        0x66, 0x2d, 0x6d, 0x61, 0x74, 0x63, 0x68, 0x00,   // f - m a t c h -
        0x00, 0x00, 0x11, 0x69, 0x66, 0x2d, 0x6d, 0x6f,   // - - - i f - m o
        0x64, 0x69, 0x66, 0x69, 0x65, 0x64, 0x2d, 0x73,   // d i f i e d - s
        0x69, 0x6e, 0x63, 0x65, 0x00, 0x00, 0x00, 0x0d,   // i n c e - - - -
        0x69, 0x66, 0x2d, 0x6e, 0x6f, 0x6e, 0x65, 0x2d,   // i f - n o n e -
        0x6d, 0x61, 0x74, 0x63, 0x68, 0x00, 0x00, 0x00,   // m a t c h - - -
        0x08, 0x69, 0x66, 0x2d, 0x72, 0x61, 0x6e, 0x67,   // - i f - r a n g
        0x65, 0x00, 0x00, 0x00, 0x13, 0x69, 0x66, 0x2d,   // e - - - - i f -
        0x75, 0x6e, 0x6d, 0x6f, 0x64, 0x69, 0x66, 0x69,   // u n m o d i f i
        0x65, 0x64, 0x2d, 0x73, 0x69, 0x6e, 0x63, 0x65,   // e d - s i n c e
        0x00, 0x00, 0x00, 0x0d, 0x6c, 0x61, 0x73, 0x74,   // - - - - l a s t
        0x2d, 0x6d, 0x6f, 0x64, 0x69, 0x66, 0x69, 0x65,   // - m o d i f i e
        0x64, 0x00, 0x00, 0x00, 0x08, 0x6c, 0x6f, 0x63,   // d - - - - l o c
        0x61, 0x74, 0x69, 0x6f, 0x6e, 0x00, 0x00, 0x00,   // a t i o n - - -
        0x0c, 0x6d, 0x61, 0x78, 0x2d, 0x66, 0x6f, 0x72,   // - m a x - f o r
        0x77, 0x61, 0x72, 0x64, 0x73, 0x00, 0x00, 0x00,   // w a r d s - - -
        0x06, 0x70, 0x72, 0x61, 0x67, 0x6d, 0x61, 0x00,   // - p r a g m a -
        0x00, 0x00, 0x12, 0x70, 0x72, 0x6f, 0x78, 0x79,   // - - - p r o x y
        0x2d, 0x61, 0x75, 0x74, 0x68, 0x65, 0x6e, 0x74,   // - a u t h e n t
        0x69, 0x63, 0x61, 0x74, 0x65, 0x00, 0x00, 0x00,   // i c a t e - - -
        0x13, 0x70, 0x72, 0x6f, 0x78, 0x79, 0x2d, 0x61,   // - p r o x y - a
        0x75, 0x74, 0x68, 0x6f, 0x72, 0x69, 0x7a, 0x61,   // u t h o r i z a
        0x74, 0x69, 0x6f, 0x6e, 0x00, 0x00, 0x00, 0x05,   // t i o n - - - -
        0x72, 0x61, 0x6e, 0x67, 0x65, 0x00, 0x00, 0x00,   // r a n g e - - -
        0x07, 0x72, 0x65, 0x66, 0x65, 0x72, 0x65, 0x72,   // - r e f e r e r
        0x00, 0x00, 0x00, 0x0b, 0x72, 0x65, 0x74, 0x72,   // - - - - r e t r
        0x79, 0x2d, 0x61, 0x66, 0x74, 0x65, 0x72, 0x00,   // y - a f t e r -
        0x00, 0x00, 0x06, 0x73, 0x65, 0x72, 0x76, 0x65,   // - - - s e r v e
        0x72, 0x00, 0x00, 0x00, 0x02, 0x74, 0x65, 0x00,   // r - - - - t e -
        0x00, 0x00, 0x07, 0x74, 0x72, 0x61, 0x69, 0x6c,   // - - - t r a i l
        0x65, 0x72, 0x00, 0x00, 0x00, 0x11, 0x74, 0x72,   // e r - - - - t r
        0x61, 0x6e, 0x73, 0x66, 0x65, 0x72, 0x2d, 0x65,   // a n s f e r - e
        0x6e, 0x63, 0x6f, 0x64, 0x69, 0x6e, 0x67, 0x00,   // n c o d i n g -
        0x00, 0x00, 0x07, 0x75, 0x70, 0x67, 0x72, 0x61,   // - - - u p g r a
        0x64, 0x65, 0x00, 0x00, 0x00, 0x0a, 0x75, 0x73,   // d e - - - - u s
        0x65, 0x72, 0x2d, 0x61, 0x67, 0x65, 0x6e, 0x74,   // e r - a g e n t
        0x00, 0x00, 0x00, 0x04, 0x76, 0x61, 0x72, 0x79,   // - - - - v a r y
        0x00, 0x00, 0x00, 0x03, 0x76, 0x69, 0x61, 0x00,   // - - - - v i a -
        0x00, 0x00, 0x07, 0x77, 0x61, 0x72, 0x6e, 0x69,   // - - - w a r n i
        0x6e, 0x67, 0x00, 0x00, 0x00, 0x10, 0x77, 0x77,   // n g - - - - w w
        0x77, 0x2d, 0x61, 0x75, 0x74, 0x68, 0x65, 0x6e,   // w - a u t h e n
        0x74, 0x69, 0x63, 0x61, 0x74, 0x65, 0x00, 0x00,   // t i c a t e - -
        0x00, 0x06, 0x6d, 0x65, 0x74, 0x68, 0x6f, 0x64,   // - - m e t h o d
        0x00, 0x00, 0x00, 0x03, 0x67, 0x65, 0x74, 0x00,   // - - - - g e t -
        0x00, 0x00, 0x06, 0x73, 0x74, 0x61, 0x74, 0x75,   // - - - s t a t u
        0x73, 0x00, 0x00, 0x00, 0x06, 0x32, 0x30, 0x30,   // s - - - - 2 0 0
        0x20, 0x4f, 0x4b, 0x00, 0x00, 0x00, 0x07, 0x76,   // - O K - - - - v
        0x65, 0x72, 0x73, 0x69, 0x6f, 0x6e, 0x00, 0x00,   // e r s i o n - -
        0x00, 0x08, 0x48, 0x54, 0x54, 0x50, 0x2f, 0x31,   // - - H T T P - 1
        0x2e, 0x31, 0x00, 0x00, 0x00, 0x03, 0x75, 0x72,   // - 1 - - - - u r
        0x6c, 0x00, 0x00, 0x00, 0x06, 0x70, 0x75, 0x62,   // l - - - - p u b
        0x6c, 0x69, 0x63, 0x00, 0x00, 0x00, 0x0a, 0x73,   // l i c - - - - s
        0x65, 0x74, 0x2d, 0x63, 0x6f, 0x6f, 0x6b, 0x69,   // e t - c o o k i
        0x65, 0x00, 0x00, 0x00, 0x0a, 0x6b, 0x65, 0x65,   // e - - - - k e e
        0x70, 0x2d, 0x61, 0x6c, 0x69, 0x76, 0x65, 0x00,   // p - a l i v e -
        0x00, 0x00, 0x06, 0x6f, 0x72, 0x69, 0x67, 0x69,   // - - - o r i g i
        0x6e, 0x31, 0x30, 0x30, 0x31, 0x30, 0x31, 0x32,   // n 1 0 0 1 0 1 2
        0x30, 0x31, 0x32, 0x30, 0x32, 0x32, 0x30, 0x35,   // 0 1 2 0 2 2 0 5
        0x32, 0x30, 0x36, 0x33, 0x30, 0x30, 0x33, 0x30,   // 2 0 6 3 0 0 3 0
        0x32, 0x33, 0x30, 0x33, 0x33, 0x30, 0x34, 0x33,   // 2 3 0 3 3 0 4 3
        0x30, 0x35, 0x33, 0x30, 0x36, 0x33, 0x30, 0x37,   // 0 5 3 0 6 3 0 7
        0x34, 0x30, 0x32, 0x34, 0x30, 0x35, 0x34, 0x30,   // 4 0 2 4 0 5 4 0
        0x36, 0x34, 0x30, 0x37, 0x34, 0x30, 0x38, 0x34,   // 6 4 0 7 4 0 8 4
        0x30, 0x39, 0x34, 0x31, 0x30, 0x34, 0x31, 0x31,   // 0 9 4 1 0 4 1 1
        0x34, 0x31, 0x32, 0x34, 0x31, 0x33, 0x34, 0x31,   // 4 1 2 4 1 3 4 1
        0x34, 0x34, 0x31, 0x35, 0x34, 0x31, 0x36, 0x34,   // 4 4 1 5 4 1 6 4
        0x31, 0x37, 0x35, 0x30, 0x32, 0x35, 0x30, 0x34,   // 1 7 5 0 2 5 0 4
        0x35, 0x30, 0x35, 0x32, 0x30, 0x33, 0x20, 0x4e,   // 5 0 5 2 0 3 - N
        0x6f, 0x6e, 0x2d, 0x41, 0x75, 0x74, 0x68, 0x6f,   // o n - A u t h o
        0x72, 0x69, 0x74, 0x61, 0x74, 0x69, 0x76, 0x65,   // r i t a t i v e
        0x20, 0x49, 0x6e, 0x66, 0x6f, 0x72, 0x6d, 0x61,   // - I n f o r m a
        0x74, 0x69, 0x6f, 0x6e, 0x32, 0x30, 0x34, 0x20,   // t i o n 2 0 4 -
        0x4e, 0x6f, 0x20, 0x43, 0x6f, 0x6e, 0x74, 0x65,   // N o - C o n t e
        0x6e, 0x74, 0x33, 0x30, 0x31, 0x20, 0x4d, 0x6f,   // n t 3 0 1 - M o
        0x76, 0x65, 0x64, 0x20, 0x50, 0x65, 0x72, 0x6d,   // v e d - P e r m
        0x61, 0x6e, 0x65, 0x6e, 0x74, 0x6c, 0x79, 0x34,   // a n e n t l y 4
        0x30, 0x30, 0x20, 0x42, 0x61, 0x64, 0x20, 0x52,   // 0 0 - B a d - R
        0x65, 0x71, 0x75, 0x65, 0x73, 0x74, 0x34, 0x30,   // e q u e s t 4 0
        0x31, 0x20, 0x55, 0x6e, 0x61, 0x75, 0x74, 0x68,   // 1 - U n a u t h
        0x6f, 0x72, 0x69, 0x7a, 0x65, 0x64, 0x34, 0x30,   // o r i z e d 4 0
        0x33, 0x20, 0x46, 0x6f, 0x72, 0x62, 0x69, 0x64,   // 3 - F o r b i d
        0x64, 0x65, 0x6e, 0x34, 0x30, 0x34, 0x20, 0x4e,   // d e n 4 0 4 - N
        0x6f, 0x74, 0x20, 0x46, 0x6f, 0x75, 0x6e, 0x64,   // o t - F o u n d
        0x35, 0x30, 0x30, 0x20, 0x49, 0x6e, 0x74, 0x65,   // 5 0 0 - I n t e
        0x72, 0x6e, 0x61, 0x6c, 0x20, 0x53, 0x65, 0x72,   // r n a l - S e r
        0x76, 0x65, 0x72, 0x20, 0x45, 0x72, 0x72, 0x6f,   // v e r - E r r o
        0x72, 0x35, 0x30, 0x31, 0x20, 0x4e, 0x6f, 0x74,   // r 5 0 1 - N o t
        0x20, 0x49, 0x6d, 0x70, 0x6c, 0x65, 0x6d, 0x65,   // - I m p l e m e
        0x6e, 0x74, 0x65, 0x64, 0x35, 0x30, 0x33, 0x20,   // n t e d 5 0 3 -
        0x53, 0x65, 0x72, 0x76, 0x69, 0x63, 0x65, 0x20,   // S e r v i c e -
        0x55, 0x6e, 0x61, 0x76, 0x61, 0x69, 0x6c, 0x61,   // U n a v a i l a
        0x62, 0x6c, 0x65, 0x4a, 0x61, 0x6e, 0x20, 0x46,   // b l e J a n - F
        0x65, 0x62, 0x20, 0x4d, 0x61, 0x72, 0x20, 0x41,   // e b - M a r - A
        0x70, 0x72, 0x20, 0x4d, 0x61, 0x79, 0x20, 0x4a,   // p r - M a y - J
        0x75, 0x6e, 0x20, 0x4a, 0x75, 0x6c, 0x20, 0x41,   // u n - J u l - A
        0x75, 0x67, 0x20, 0x53, 0x65, 0x70, 0x74, 0x20,   // u g - S e p t -
        0x4f, 0x63, 0x74, 0x20, 0x4e, 0x6f, 0x76, 0x20,   // O c t - N o v -
        0x44, 0x65, 0x63, 0x20, 0x30, 0x30, 0x3a, 0x30,   // D e c - 0 0 - 0
        0x30, 0x3a, 0x30, 0x30, 0x20, 0x4d, 0x6f, 0x6e,   // 0 - 0 0 - M o n
        0x2c, 0x20, 0x54, 0x75, 0x65, 0x2c, 0x20, 0x57,   // - - T u e - - W
        0x65, 0x64, 0x2c, 0x20, 0x54, 0x68, 0x75, 0x2c,   // e d - - T h u -
        0x20, 0x46, 0x72, 0x69, 0x2c, 0x20, 0x53, 0x61,   // - F r i - - S a
        0x74, 0x2c, 0x20, 0x53, 0x75, 0x6e, 0x2c, 0x20,   // t - - S u n - -
        0x47, 0x4d, 0x54, 0x63, 0x68, 0x75, 0x6e, 0x6b,   // G M T c h u n k
        0x65, 0x64, 0x2c, 0x74, 0x65, 0x78, 0x74, 0x2f,   // e d - t e x t -
        0x68, 0x74, 0x6d, 0x6c, 0x2c, 0x69, 0x6d, 0x61,   // h t m l - i m a
        0x67, 0x65, 0x2f, 0x70, 0x6e, 0x67, 0x2c, 0x69,   // g e - p n g - i
        0x6d, 0x61, 0x67, 0x65, 0x2f, 0x6a, 0x70, 0x67,   // m a g e - j p g
        0x2c, 0x69, 0x6d, 0x61, 0x67, 0x65, 0x2f, 0x67,   // - i m a g e - g
        0x69, 0x66, 0x2c, 0x61, 0x70, 0x70, 0x6c, 0x69,   // i f - a p p l i
        0x63, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x2f, 0x78,   // c a t i o n - x
        0x6d, 0x6c, 0x2c, 0x61, 0x70, 0x70, 0x6c, 0x69,   // m l - a p p l i
        0x63, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x2f, 0x78,   // c a t i o n - x
        0x68, 0x74, 0x6d, 0x6c, 0x2b, 0x78, 0x6d, 0x6c,   // h t m l - x m l
        0x2c, 0x74, 0x65, 0x78, 0x74, 0x2f, 0x70, 0x6c,   // - t e x t - p l
        0x61, 0x69, 0x6e, 0x2c, 0x74, 0x65, 0x78, 0x74,   // a i n - t e x t
        0x2f, 0x6a, 0x61, 0x76, 0x61, 0x73, 0x63, 0x72,   // - j a v a s c r
        0x69, 0x70, 0x74, 0x2c, 0x70, 0x75, 0x62, 0x6c,   // i p t - p u b l
        0x69, 0x63, 0x70, 0x72, 0x69, 0x76, 0x61, 0x74,   // i c p r i v a t
        0x65, 0x6d, 0x61, 0x78, 0x2d, 0x61, 0x67, 0x65,   // e m a x - a g e
        0x3d, 0x67, 0x7a, 0x69, 0x70, 0x2c, 0x64, 0x65,   // - g z i p - d e
        0x66, 0x6c, 0x61, 0x74, 0x65, 0x2c, 0x73, 0x64,   // f l a t e - s d
        0x63, 0x68, 0x63, 0x68, 0x61, 0x72, 0x73, 0x65,   // c h c h a r s e
        0x74, 0x3d, 0x75, 0x74, 0x66, 0x2d, 0x38, 0x63,   // t - u t f - 8 c
        0x68, 0x61, 0x72, 0x73, 0x65, 0x74, 0x3d, 0x69,   // h a r s e t - i
        0x73, 0x6f, 0x2d, 0x38, 0x38, 0x35, 0x39, 0x2d,   // s o - 8 8 5 9 -
        0x31, 0x2c, 0x75, 0x74, 0x66, 0x2d, 0x2c, 0x2a,   // 1 - u t f - - -
        0x2c, 0x65, 0x6e, 0x71, 0x3d, 0x30, 0x2e          // - e n q - 0 -
    };

    private SpdyCodecUtil() {
    }

    /**
     * Reads a big-endian unsigned short integer from the buffer.
     */
    static int getUnsignedShort(ByteBuf buf, int offset) {
        return (buf.getByte(offset)     & 0xFF) << 8 |
                buf.getByte(offset + 1) & 0xFF;
    }

    /**
     * Reads a big-endian unsigned medium integer from the buffer.
     */
    static int getUnsignedMedium(ByteBuf buf, int offset) {
        return (buf.getByte(offset)     & 0xFF) << 16 |
               (buf.getByte(offset + 1) & 0xFF) <<  8 |
                buf.getByte(offset + 2) & 0xFF;
    }

    /**
     * Reads a big-endian (31-bit) integer from the buffer.
     */
    static int getUnsignedInt(ByteBuf buf, int offset) {
        return (buf.getByte(offset)     & 0x7F) << 24 |
               (buf.getByte(offset + 1) & 0xFF) << 16 |
               (buf.getByte(offset + 2) & 0xFF) <<  8 |
                buf.getByte(offset + 3) & 0xFF;
    }

    /**
     * Reads a big-endian signed integer from the buffer.
     */
    static int getSignedInt(ByteBuf buf, int offset) {
        return (buf.getByte(offset)     & 0xFF) << 24 |
               (buf.getByte(offset + 1) & 0xFF) << 16 |
               (buf.getByte(offset + 2) & 0xFF) <<  8 |
                buf.getByte(offset + 3) & 0xFF;
    }

    /**
     * Returns {@code true} if ID is for a server initiated stream or ping.
     */
    static boolean isServerId(int id) {
        // Server initiated streams and pings have even IDs
        return id % 2 == 0;
    }

    /**
     * Validate a SPDY header name.
     */
    static void validateHeaderName(CharSequence name) {
        if (name == null) {
            throw new NullPointerException("name");
        }
        if (name.length() == 0) {
            throw new IllegalArgumentException(
                    "name cannot be length zero");
        }
        // Since name may only contain ascii characters, for valid names
        // name.length() returns the number of bytes when UTF-8 encoded.
        if (name.length() > SPDY_MAX_NV_LENGTH) {
            throw new IllegalArgumentException(
                    "name exceeds allowable length: " + name);
        }
        for (int i = 0; i < name.length(); i ++) {
            char c = name.charAt(i);
            if (c == 0) {
                throw new IllegalArgumentException(
                        "name contains null character: " + name);
            }
            if (c > 127) {
                throw new IllegalArgumentException(
                        "name contains non-ascii character: " + name);
            }
        }
    }

    /**
     * Validate a SPDY header value. Does not validate max length.
     */
    static void validateHeaderValue(CharSequence value) {
        if (value == null) {
            throw new NullPointerException("value");
        }
        for (int i = 0; i < value.length(); i ++) {
            char c = value.charAt(i);
            if (c == 0) {
                throw new IllegalArgumentException(
                        "value contains null character: " + value);
            }
        }
    }
}


File: codec-http/src/test/java/io/netty/handler/codec/spdy/SpdySessionHandlerTest.java
/*
 * Copyright 2013 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */
package io.netty.handler.codec.spdy;

import io.netty.channel.ChannelHandlerAdapter;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.embedded.EmbeddedChannel;
import io.netty.util.internal.logging.InternalLogger;
import io.netty.util.internal.logging.InternalLoggerFactory;
import org.junit.Test;

import java.util.List;
import java.util.Map;

import static org.junit.Assert.*;

public class SpdySessionHandlerTest {

    private static final InternalLogger logger =
            InternalLoggerFactory.getInstance(SpdySessionHandlerTest.class);

    private static final int closeSignal = SpdyCodecUtil.SPDY_SETTINGS_MAX_ID;
    private static final SpdySettingsFrame closeMessage = new DefaultSpdySettingsFrame();

    static {
        closeMessage.setValue(closeSignal, 0);
    }

    private static void assertDataFrame(Object msg, int streamId, boolean last) {
        assertNotNull(msg);
        assertTrue(msg instanceof SpdyDataFrame);
        SpdyDataFrame spdyDataFrame = (SpdyDataFrame) msg;
        assertEquals(streamId, spdyDataFrame.streamId());
        assertEquals(last, spdyDataFrame.isLast());
    }

    private static void assertSynReply(Object msg, int streamId, boolean last, SpdyHeaders headers) {
        assertNotNull(msg);
        assertTrue(msg instanceof SpdySynReplyFrame);
        assertHeaders(msg, streamId, last, headers);
    }

    private static void assertRstStream(Object msg, int streamId, SpdyStreamStatus status) {
        assertNotNull(msg);
        assertTrue(msg instanceof SpdyRstStreamFrame);
        SpdyRstStreamFrame spdyRstStreamFrame = (SpdyRstStreamFrame) msg;
        assertEquals(streamId, spdyRstStreamFrame.streamId());
        assertEquals(status, spdyRstStreamFrame.status());
    }

    private static void assertPing(Object msg, int id) {
        assertNotNull(msg);
        assertTrue(msg instanceof SpdyPingFrame);
        SpdyPingFrame spdyPingFrame = (SpdyPingFrame) msg;
        assertEquals(id, spdyPingFrame.id());
    }

    private static void assertGoAway(Object msg, int lastGoodStreamId) {
        assertNotNull(msg);
        assertTrue(msg instanceof SpdyGoAwayFrame);
        SpdyGoAwayFrame spdyGoAwayFrame = (SpdyGoAwayFrame) msg;
        assertEquals(lastGoodStreamId, spdyGoAwayFrame.lastGoodStreamId());
    }

    private static void assertHeaders(Object msg, int streamId, boolean last, SpdyHeaders headers) {
        assertNotNull(msg);
        assertTrue(msg instanceof SpdyHeadersFrame);
        SpdyHeadersFrame spdyHeadersFrame = (SpdyHeadersFrame) msg;
        assertEquals(streamId, spdyHeadersFrame.streamId());
        assertEquals(last, spdyHeadersFrame.isLast());
        for (CharSequence name: headers.names()) {
            List<CharSequence> expectedValues = headers.getAll(name);
            List<CharSequence> receivedValues = spdyHeadersFrame.headers().getAll(name);
            assertTrue(receivedValues.containsAll(expectedValues));
            receivedValues.removeAll(expectedValues);
            assertTrue(receivedValues.isEmpty());
            spdyHeadersFrame.headers().remove(name);
        }
        assertTrue(spdyHeadersFrame.headers().isEmpty());
    }

    private static void testSpdySessionHandler(SpdyVersion version, boolean server) {
        EmbeddedChannel sessionHandler = new EmbeddedChannel(
                new SpdySessionHandler(version, server), new EchoHandler(closeSignal, server));

        while (sessionHandler.readOutbound() != null) {
            continue;
        }

        int localStreamId = server ? 1 : 2;
        int remoteStreamId = server ? 2 : 1;

        SpdySynStreamFrame spdySynStreamFrame =
                new DefaultSpdySynStreamFrame(localStreamId, 0, (byte) 0);
        spdySynStreamFrame.headers().set("Compression", "test");

        SpdyDataFrame spdyDataFrame = new DefaultSpdyDataFrame(localStreamId);
        spdyDataFrame.setLast(true);

        // Check if session handler returns INVALID_STREAM if it receives
        // a data frame for a Stream-ID that is not open
        sessionHandler.writeInbound(new DefaultSpdyDataFrame(localStreamId));
        assertRstStream(sessionHandler.readOutbound(), localStreamId, SpdyStreamStatus.INVALID_STREAM);
        assertNull(sessionHandler.readOutbound());

        // Check if session handler returns PROTOCOL_ERROR if it receives
        // a data frame for a Stream-ID before receiving a SYN_REPLY frame
        sessionHandler.writeInbound(new DefaultSpdyDataFrame(remoteStreamId));
        assertRstStream(sessionHandler.readOutbound(), remoteStreamId, SpdyStreamStatus.PROTOCOL_ERROR);
        assertNull(sessionHandler.readOutbound());
        remoteStreamId += 2;

        // Check if session handler returns PROTOCOL_ERROR if it receives
        // multiple SYN_REPLY frames for the same active Stream-ID
        sessionHandler.writeInbound(new DefaultSpdySynReplyFrame(remoteStreamId));
        assertNull(sessionHandler.readOutbound());
        sessionHandler.writeInbound(new DefaultSpdySynReplyFrame(remoteStreamId));
        assertRstStream(sessionHandler.readOutbound(), remoteStreamId, SpdyStreamStatus.STREAM_IN_USE);
        assertNull(sessionHandler.readOutbound());
        remoteStreamId += 2;

        // Check if frame codec correctly compresses/uncompresses headers
        sessionHandler.writeInbound(spdySynStreamFrame);
        assertSynReply(sessionHandler.readOutbound(), localStreamId, false, spdySynStreamFrame.headers());
        assertNull(sessionHandler.readOutbound());
        SpdyHeadersFrame spdyHeadersFrame = new DefaultSpdyHeadersFrame(localStreamId);

        spdyHeadersFrame.headers().add("HEADER", "test1");
        spdyHeadersFrame.headers().add("HEADER", "test2");

        sessionHandler.writeInbound(spdyHeadersFrame);
        assertHeaders(sessionHandler.readOutbound(), localStreamId, false, spdyHeadersFrame.headers());
        assertNull(sessionHandler.readOutbound());
        localStreamId += 2;

        // Check if session handler closed the streams using the number
        // of concurrent streams and that it returns REFUSED_STREAM
        // if it receives a SYN_STREAM frame it does not wish to accept
        spdySynStreamFrame.setStreamId(localStreamId);
        spdySynStreamFrame.setLast(true);
        spdySynStreamFrame.setUnidirectional(true);

        sessionHandler.writeInbound(spdySynStreamFrame);
        assertRstStream(sessionHandler.readOutbound(), localStreamId, SpdyStreamStatus.REFUSED_STREAM);
        assertNull(sessionHandler.readOutbound());

        // Check if session handler rejects HEADERS for closed streams
        int testStreamId = spdyDataFrame.streamId();
        sessionHandler.writeInbound(spdyDataFrame);
        assertDataFrame(sessionHandler.readOutbound(), testStreamId, spdyDataFrame.isLast());
        assertNull(sessionHandler.readOutbound());
        spdyHeadersFrame.setStreamId(testStreamId);

        sessionHandler.writeInbound(spdyHeadersFrame);
        assertRstStream(sessionHandler.readOutbound(), testStreamId, SpdyStreamStatus.INVALID_STREAM);
        assertNull(sessionHandler.readOutbound());

        // Check if session handler drops active streams if it receives
        // a RST_STREAM frame for that Stream-ID
        sessionHandler.writeInbound(new DefaultSpdyRstStreamFrame(remoteStreamId, 3));
        assertNull(sessionHandler.readOutbound());
        //remoteStreamId += 2;

        // Check if session handler honors UNIDIRECTIONAL streams
        spdySynStreamFrame.setLast(false);
        sessionHandler.writeInbound(spdySynStreamFrame);
        assertNull(sessionHandler.readOutbound());
        spdySynStreamFrame.setUnidirectional(false);

        // Check if session handler returns PROTOCOL_ERROR if it receives
        // multiple SYN_STREAM frames for the same active Stream-ID
        sessionHandler.writeInbound(spdySynStreamFrame);
        assertRstStream(sessionHandler.readOutbound(), localStreamId, SpdyStreamStatus.PROTOCOL_ERROR);
        assertNull(sessionHandler.readOutbound());
        localStreamId += 2;

        // Check if session handler returns PROTOCOL_ERROR if it receives
        // a SYN_STREAM frame with an invalid Stream-ID
        spdySynStreamFrame.setStreamId(localStreamId - 1);
        sessionHandler.writeInbound(spdySynStreamFrame);
        assertRstStream(sessionHandler.readOutbound(), localStreamId - 1, SpdyStreamStatus.PROTOCOL_ERROR);
        assertNull(sessionHandler.readOutbound());
        spdySynStreamFrame.setStreamId(localStreamId);

        // Check if session handler returns PROTOCOL_ERROR if it receives
        // an invalid HEADERS frame
        spdyHeadersFrame.setStreamId(localStreamId);

        spdyHeadersFrame.setInvalid();
        sessionHandler.writeInbound(spdyHeadersFrame);
        assertRstStream(sessionHandler.readOutbound(), localStreamId, SpdyStreamStatus.PROTOCOL_ERROR);
        assertNull(sessionHandler.readOutbound());

        sessionHandler.finish();
    }

    private static void testSpdySessionHandlerPing(SpdyVersion version, boolean server) {
        EmbeddedChannel sessionHandler = new EmbeddedChannel(
                new SpdySessionHandler(version, server), new EchoHandler(closeSignal, server));

        while (sessionHandler.readOutbound() != null) {
            continue;
        }

        int localStreamId = server ? 1 : 2;
        int remoteStreamId = server ? 2 : 1;

        SpdyPingFrame localPingFrame = new DefaultSpdyPingFrame(localStreamId);
        SpdyPingFrame remotePingFrame = new DefaultSpdyPingFrame(remoteStreamId);

        // Check if session handler returns identical local PINGs
        sessionHandler.writeInbound(localPingFrame);
        assertPing(sessionHandler.readOutbound(), localPingFrame.id());
        assertNull(sessionHandler.readOutbound());

        // Check if session handler ignores un-initiated remote PINGs
        sessionHandler.writeInbound(remotePingFrame);
        assertNull(sessionHandler.readOutbound());

        sessionHandler.finish();
    }

    private static void testSpdySessionHandlerGoAway(SpdyVersion version, boolean server) {
        EmbeddedChannel sessionHandler = new EmbeddedChannel(
                new SpdySessionHandler(version, server), new EchoHandler(closeSignal, server));

        while (sessionHandler.readOutbound() != null) {
            continue;
        }

        int localStreamId = server ? 1 : 2;

        SpdySynStreamFrame spdySynStreamFrame =
                new DefaultSpdySynStreamFrame(localStreamId, 0, (byte) 0);
        spdySynStreamFrame.headers().set("Compression", "test");

        SpdyDataFrame spdyDataFrame = new DefaultSpdyDataFrame(localStreamId);
        spdyDataFrame.setLast(true);

        // Send an initial request
        sessionHandler.writeInbound(spdySynStreamFrame);
        assertSynReply(sessionHandler.readOutbound(), localStreamId, false, spdySynStreamFrame.headers());
        assertNull(sessionHandler.readOutbound());
        sessionHandler.writeInbound(spdyDataFrame);
        assertDataFrame(sessionHandler.readOutbound(), localStreamId, true);
        assertNull(sessionHandler.readOutbound());

        // Check if session handler sends a GOAWAY frame when closing
        sessionHandler.writeInbound(closeMessage);
        assertGoAway(sessionHandler.readOutbound(), localStreamId);
        assertNull(sessionHandler.readOutbound());
        localStreamId += 2;

        // Check if session handler returns REFUSED_STREAM if it receives
        // SYN_STREAM frames after sending a GOAWAY frame
        spdySynStreamFrame.setStreamId(localStreamId);
        sessionHandler.writeInbound(spdySynStreamFrame);
        assertRstStream(sessionHandler.readOutbound(), localStreamId, SpdyStreamStatus.REFUSED_STREAM);
        assertNull(sessionHandler.readOutbound());

        // Check if session handler ignores Data frames after sending
        // a GOAWAY frame
        spdyDataFrame.setStreamId(localStreamId);
        sessionHandler.writeInbound(spdyDataFrame);
        assertNull(sessionHandler.readOutbound());

        sessionHandler.finish();
    }

    @Test
    public void testSpdyClientSessionHandler() {
        logger.info("Running: testSpdyClientSessionHandler v3.1");
        testSpdySessionHandler(SpdyVersion.SPDY_3_1, false);
    }

    @Test
    public void testSpdyClientSessionHandlerPing() {
        logger.info("Running: testSpdyClientSessionHandlerPing v3.1");
        testSpdySessionHandlerPing(SpdyVersion.SPDY_3_1, false);
    }

    @Test
    public void testSpdyClientSessionHandlerGoAway() {
        logger.info("Running: testSpdyClientSessionHandlerGoAway v3.1");
        testSpdySessionHandlerGoAway(SpdyVersion.SPDY_3_1, false);
    }

    @Test
    public void testSpdyServerSessionHandler() {
        logger.info("Running: testSpdyServerSessionHandler v3.1");
        testSpdySessionHandler(SpdyVersion.SPDY_3_1, true);
    }

    @Test
    public void testSpdyServerSessionHandlerPing() {
        logger.info("Running: testSpdyServerSessionHandlerPing v3.1");
        testSpdySessionHandlerPing(SpdyVersion.SPDY_3_1, true);
    }

    @Test
    public void testSpdyServerSessionHandlerGoAway() {
        logger.info("Running: testSpdyServerSessionHandlerGoAway v3.1");
        testSpdySessionHandlerGoAway(SpdyVersion.SPDY_3_1, true);
    }

    // Echo Handler opens 4 half-closed streams on session connection
    // and then sets the number of concurrent streams to 1
    private static class EchoHandler extends ChannelHandlerAdapter {
        private final int closeSignal;
        private final boolean server;

        EchoHandler(int closeSignal, boolean server) {
            this.closeSignal = closeSignal;
            this.server = server;
        }

        @Override
        public void channelActive(ChannelHandlerContext ctx) throws Exception {
            // Initiate 4 new streams
            int streamId = server ? 2 : 1;
            SpdySynStreamFrame spdySynStreamFrame =
                    new DefaultSpdySynStreamFrame(streamId, 0, (byte) 0);
            spdySynStreamFrame.setLast(true);
            ctx.writeAndFlush(spdySynStreamFrame);
            spdySynStreamFrame.setStreamId(spdySynStreamFrame.streamId() + 2);
            ctx.writeAndFlush(spdySynStreamFrame);
            spdySynStreamFrame.setStreamId(spdySynStreamFrame.streamId() + 2);
            ctx.writeAndFlush(spdySynStreamFrame);
            spdySynStreamFrame.setStreamId(spdySynStreamFrame.streamId() + 2);
            ctx.writeAndFlush(spdySynStreamFrame);

            // Limit the number of concurrent streams to 1
            SpdySettingsFrame spdySettingsFrame = new DefaultSpdySettingsFrame();
            spdySettingsFrame.setValue(SpdySettingsFrame.SETTINGS_MAX_CONCURRENT_STREAMS, 1);
            ctx.writeAndFlush(spdySettingsFrame);
        }

        @Override
        public void channelRead(ChannelHandlerContext ctx, Object msg) throws Exception {
            if (msg instanceof SpdySynStreamFrame) {

                SpdySynStreamFrame spdySynStreamFrame = (SpdySynStreamFrame) msg;
                if (!spdySynStreamFrame.isUnidirectional()) {
                    int streamId = spdySynStreamFrame.streamId();
                    SpdySynReplyFrame spdySynReplyFrame = new DefaultSpdySynReplyFrame(streamId);
                    spdySynReplyFrame.setLast(spdySynStreamFrame.isLast());
                    for (Map.Entry<CharSequence, CharSequence> entry: spdySynStreamFrame.headers()) {
                        spdySynReplyFrame.headers().add(entry.getKey(), entry.getValue());
                    }

                    ctx.writeAndFlush(spdySynReplyFrame);
                }
                return;
            }

            if (msg instanceof SpdySynReplyFrame) {
                return;
            }

            if (msg instanceof SpdyDataFrame ||
                msg instanceof SpdyPingFrame ||
                msg instanceof SpdyHeadersFrame) {

                ctx.writeAndFlush(msg);
                return;
            }

            if (msg instanceof SpdySettingsFrame) {
                SpdySettingsFrame spdySettingsFrame = (SpdySettingsFrame) msg;
                if (spdySettingsFrame.isSet(closeSignal)) {
                    ctx.close();
                }
            }
        }
    }
}


File: codec-http2/src/main/java/io/netty/handler/codec/http2/DefaultHttp2Headers.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License, version 2.0 (the
 * "License"); you may not use this file except in compliance with the License. You may obtain a
 * copy of the License at:
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */
package io.netty.handler.codec.http2;

import static io.netty.util.internal.StringUtil.UPPER_CASE_TO_LOWER_CASE_ASCII_OFFSET;
import io.netty.handler.codec.BinaryHeaders;
import io.netty.handler.codec.DefaultBinaryHeaders;
import io.netty.util.AsciiString;
import io.netty.util.ByteProcessor;
import io.netty.util.ByteString;
import io.netty.util.internal.PlatformDependent;

public class DefaultHttp2Headers extends DefaultBinaryHeaders implements Http2Headers {
    private static final ByteProcessor HTTP2_ASCII_UPPERCASE_PROCESSOR = new ByteProcessor() {
        @Override
        public boolean process(byte value) throws Exception {
            return value < 'A' || value > 'Z';
        }
    };

    private static final class Http2AsciiToLowerCaseConverter implements ByteProcessor {
        private final byte[] result;
        private int i;

        public Http2AsciiToLowerCaseConverter(int length) {
            result = new byte[length];
        }

        @Override
        public boolean process(byte value) throws Exception {
            result[i++] = (value >= 'A' && value <= 'Z')
                    ? (byte) (value + UPPER_CASE_TO_LOWER_CASE_ASCII_OFFSET) : value;
            return true;
        }

        public byte[] result() {
            return result;
        }
    };

    private static final NameConverter<ByteString> HTTP2_ASCII_TO_LOWER_CONVERTER = new NameConverter<ByteString>() {
        @Override
        public ByteString convertName(ByteString name) {
            if (name instanceof AsciiString) {
                return ((AsciiString) name).toLowerCase();
            }

            try {
                if (name.forEachByte(HTTP2_ASCII_UPPERCASE_PROCESSOR) == -1) {
                    return name;
                }

                Http2AsciiToLowerCaseConverter converter = new Http2AsciiToLowerCaseConverter(name.length());
                name.forEachByte(converter);
                return new ByteString(converter.result(), false);
            } catch (Exception e) {
                PlatformDependent.throwException(e);
                return null;
            }
        }
    };

    /**
     * Creates an instance that will convert all header names to lowercase.
     */
    public DefaultHttp2Headers() {
        this(true);
    }

    /**
     * Creates an instance that can be configured to either do header field name conversion to
     * lowercase, or not do any conversion at all.
     * <p>
     *
     * <strong>Note</strong> that setting {@code forceKeyToLower} to {@code false} can violate the
     * <a href="https://tools.ietf.org/html/draft-ietf-httpbis-http2-16#section-8.1.2">HTTP/2 specification</a>
     * which specifies that a request or response containing an uppercase header field MUST be treated
     * as malformed. Only set {@code forceKeyToLower} to {@code false} if you are explicitly using lowercase
     * header field names and want to avoid the conversion to lowercase.
     *
     * @param forceKeyToLower if @{code false} no header name conversion will be performed
     */
    public DefaultHttp2Headers(boolean forceKeyToLower) {
        super(forceKeyToLower ? HTTP2_ASCII_TO_LOWER_CONVERTER : IDENTITY_NAME_CONVERTER);
    }

    @Override
    public Http2Headers add(ByteString name, ByteString value) {
        super.add(name, value);
        return this;
    }

    @Override
    public Http2Headers add(ByteString name, Iterable<? extends ByteString> values) {
        super.add(name, values);
        return this;
    }

    @Override
    public Http2Headers add(ByteString name, ByteString... values) {
        super.add(name, values);
        return this;
    }

    @Override
    public Http2Headers addObject(ByteString name, Object value) {
        super.addObject(name, value);
        return this;
    }

    @Override
    public Http2Headers addObject(ByteString name, Iterable<?> values) {
        super.addObject(name, values);
        return this;
    }

    @Override
    public Http2Headers addObject(ByteString name, Object... values) {
        super.addObject(name, values);
        return this;
    }

    @Override
    public Http2Headers addBoolean(ByteString name, boolean value) {
        super.addBoolean(name, value);
        return this;
    }

    @Override
    public Http2Headers addChar(ByteString name, char value) {
        super.addChar(name, value);
        return this;
    }

    @Override
    public Http2Headers addByte(ByteString name, byte value) {
        super.addByte(name, value);
        return this;
    }

    @Override
    public Http2Headers addShort(ByteString name, short value) {
        super.addShort(name, value);
        return this;
    }

    @Override
    public Http2Headers addInt(ByteString name, int value) {
        super.addInt(name, value);
        return this;
    }

    @Override
    public Http2Headers addLong(ByteString name, long value) {
        super.addLong(name, value);
        return this;
    }

    @Override
    public Http2Headers addFloat(ByteString name, float value) {
        super.addFloat(name, value);
        return this;
    }

    @Override
    public Http2Headers addDouble(ByteString name, double value) {
        super.addDouble(name, value);
        return this;
    }

    @Override
    public Http2Headers addTimeMillis(ByteString name, long value) {
        super.addTimeMillis(name, value);
        return this;
    }

    @Override
    public Http2Headers add(BinaryHeaders headers) {
        super.add(headers);
        return this;
    }

    @Override
    public Http2Headers set(ByteString name, ByteString value) {
        super.set(name, value);
        return this;
    }

    @Override
    public Http2Headers set(ByteString name, Iterable<? extends ByteString> values) {
        super.set(name, values);
        return this;
    }

    @Override
    public Http2Headers set(ByteString name, ByteString... values) {
        super.set(name, values);
        return this;
    }

    @Override
    public Http2Headers setObject(ByteString name, Object value) {
        super.setObject(name, value);
        return this;
    }

    @Override
    public Http2Headers setObject(ByteString name, Iterable<?> values) {
        super.setObject(name, values);
        return this;
    }

    @Override
    public Http2Headers setObject(ByteString name, Object... values) {
        super.setObject(name, values);
        return this;
    }

    @Override
    public Http2Headers setBoolean(ByteString name, boolean value) {
        super.setBoolean(name, value);
        return this;
    }

    @Override
    public Http2Headers setChar(ByteString name, char value) {
        super.setChar(name, value);
        return this;
    }

    @Override
    public Http2Headers setByte(ByteString name, byte value) {
        super.setByte(name, value);
        return this;
    }

    @Override
    public Http2Headers setShort(ByteString name, short value) {
        super.setShort(name, value);
        return this;
    }

    @Override
    public Http2Headers setInt(ByteString name, int value) {
        super.setInt(name, value);
        return this;
    }

    @Override
    public Http2Headers setLong(ByteString name, long value) {
        super.setLong(name, value);
        return this;
    }

    @Override
    public Http2Headers setFloat(ByteString name, float value) {
        super.setFloat(name, value);
        return this;
    }

    @Override
    public Http2Headers setDouble(ByteString name, double value) {
        super.setDouble(name, value);
        return this;
    }

    @Override
    public Http2Headers setTimeMillis(ByteString name, long value) {
        super.setTimeMillis(name, value);
        return this;
    }

    @Override
    public Http2Headers set(BinaryHeaders headers) {
        super.set(headers);
        return this;
    }

    @Override
    public Http2Headers setAll(BinaryHeaders headers) {
        super.setAll(headers);
        return this;
    }

    @Override
    public Http2Headers clear() {
        super.clear();
        return this;
    }

    @Override
    public Http2Headers method(ByteString value) {
        set(PseudoHeaderName.METHOD.value(), value);
        return this;
    }

    @Override
    public Http2Headers scheme(ByteString value) {
        set(PseudoHeaderName.SCHEME.value(), value);
        return this;
    }

    @Override
    public Http2Headers authority(ByteString value) {
        set(PseudoHeaderName.AUTHORITY.value(), value);
        return this;
    }

    @Override
    public Http2Headers path(ByteString value) {
        set(PseudoHeaderName.PATH.value(), value);
        return this;
    }

    @Override
    public Http2Headers status(ByteString value) {
        set(PseudoHeaderName.STATUS.value(), value);
        return this;
    }

    @Override
    public ByteString method() {
        return get(PseudoHeaderName.METHOD.value());
    }

    @Override
    public ByteString scheme() {
        return get(PseudoHeaderName.SCHEME.value());
    }

    @Override
    public ByteString authority() {
        return get(PseudoHeaderName.AUTHORITY.value());
    }

    @Override
    public ByteString path() {
        return get(PseudoHeaderName.PATH.value());
    }

    @Override
    public ByteString status() {
        return get(PseudoHeaderName.STATUS.value());
    }
}


File: codec-http2/src/main/java/io/netty/handler/codec/http2/DefaultHttp2HeadersEncoder.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License, version 2.0 (the
 * "License"); you may not use this file except in compliance with the License. You may obtain a
 * copy of the License at:
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package io.netty.handler.codec.http2;

import static io.netty.handler.codec.http2.Http2CodecUtil.DEFAULT_HEADER_TABLE_SIZE;
import static io.netty.handler.codec.http2.Http2Error.COMPRESSION_ERROR;
import static io.netty.handler.codec.http2.Http2Error.INTERNAL_ERROR;
import static io.netty.handler.codec.http2.Http2Error.PROTOCOL_ERROR;
import static io.netty.handler.codec.http2.Http2Exception.connectionError;
import static io.netty.util.internal.ObjectUtil.checkNotNull;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufOutputStream;
import io.netty.handler.codec.BinaryHeaders.EntryVisitor;
import io.netty.util.ByteString;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.util.Map.Entry;

import com.twitter.hpack.Encoder;

public class DefaultHttp2HeadersEncoder implements Http2HeadersEncoder, Http2HeadersEncoder.Configuration {
    private final Encoder encoder;
    private final ByteArrayOutputStream tableSizeChangeOutput = new ByteArrayOutputStream();
    private final SensitivityDetector sensitivityDetector;
    private final Http2HeaderTable headerTable;

    public DefaultHttp2HeadersEncoder() {
        this(DEFAULT_HEADER_TABLE_SIZE, NEVER_SENSITIVE);
    }

    public DefaultHttp2HeadersEncoder(int maxHeaderTableSize, SensitivityDetector sensitivityDetector) {
        this.sensitivityDetector = checkNotNull(sensitivityDetector, "sensitiveDetector");
        encoder = new Encoder(maxHeaderTableSize);
        headerTable = new Http2HeaderTableEncoder();
    }

    @Override
    public void encodeHeaders(Http2Headers headers, ByteBuf buffer) throws Http2Exception {
        final OutputStream stream = new ByteBufOutputStream(buffer);
        try {
            if (headers.size() > headerTable.maxHeaderListSize()) {
                throw connectionError(PROTOCOL_ERROR, "Number of headers (%d) exceeds maxHeaderListSize (%d)",
                        headers.size(), headerTable.maxHeaderListSize());
            }

            // If there was a change in the table size, serialize the output from the encoder
            // resulting from that change.
            if (tableSizeChangeOutput.size() > 0) {
                buffer.writeBytes(tableSizeChangeOutput.toByteArray());
                tableSizeChangeOutput.reset();
            }

            // Write pseudo headers first as required by the HTTP/2 spec.
            for (Http2Headers.PseudoHeaderName pseudoHeader : Http2Headers.PseudoHeaderName.values()) {
                ByteString name = pseudoHeader.value();
                ByteString value = headers.get(name);
                if (value != null) {
                    encodeHeader(name, value, stream);
                }
            }

            headers.forEachEntry(new EntryVisitor() {
                @Override
                public boolean visit(Entry<ByteString, ByteString> entry) throws Exception {
                    final ByteString name = entry.getKey();
                    final ByteString value = entry.getValue();
                    if (!Http2Headers.PseudoHeaderName.isPseudoHeader(name)) {
                        encodeHeader(name, value, stream);
                    }
                    return true;
                }
            });
        } catch (Http2Exception e) {
            throw e;
        } catch (Throwable t) {
            throw connectionError(COMPRESSION_ERROR, t, "Failed encoding headers block: %s", t.getMessage());
        } finally {
            try {
                stream.close();
            } catch (IOException e) {
                throw connectionError(INTERNAL_ERROR, e, e.getMessage());
            }
        }
    }

    @Override
    public Http2HeaderTable headerTable() {
        return headerTable;
    }

    @Override
    public Configuration configuration() {
        return this;
    }

    private void encodeHeader(ByteString key, ByteString value, OutputStream stream) throws IOException {
        encoder.encodeHeader(stream,
                key.isEntireArrayUsed() ? key.array() : new ByteString(key, true).array(),
                value.isEntireArrayUsed() ? value.array() : new ByteString(value, true).array(),
                sensitivityDetector.isSensitive(key, value));
    }

    /**
     * {@link Http2HeaderTable} implementation to support {@link Http2HeadersEncoder}
     */
    private final class Http2HeaderTableEncoder extends DefaultHttp2HeaderTableListSize implements Http2HeaderTable {
        @Override
        public void maxHeaderTableSize(int max) throws Http2Exception {
            if (max < 0) {
                throw connectionError(PROTOCOL_ERROR, "Header Table Size must be non-negative but was %d", max);
            }
            try {
                // No headers should be emitted. If they are, we throw.
                encoder.setMaxHeaderTableSize(tableSizeChangeOutput, max);
            } catch (IOException e) {
                throw new Http2Exception(COMPRESSION_ERROR, e.getMessage(), e);
            } catch (Throwable t) {
                throw new Http2Exception(PROTOCOL_ERROR, t.getMessage(), t);
            }
        }

        @Override
        public int maxHeaderTableSize() {
            return encoder.getMaxHeaderTableSize();
        }
    }
}


File: codec-http2/src/main/java/io/netty/handler/codec/http2/Http2Headers.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License, version 2.0 (the
 * "License"); you may not use this file except in compliance with the License. You may obtain a
 * copy of the License at:
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package io.netty.handler.codec.http2;

import io.netty.handler.codec.BinaryHeaders;
import io.netty.util.ByteString;
import io.netty.util.CharsetUtil;

import java.util.HashSet;
import java.util.Set;

/**
 * A collection of headers sent or received via HTTP/2.
 */
public interface Http2Headers extends BinaryHeaders {

    /**
     * HTTP/2 pseudo-headers names.
     */
    enum PseudoHeaderName {
        /**
         * {@code :method}.
         */
        METHOD(":method"),

        /**
         * {@code :scheme}.
         */
        SCHEME(":scheme"),

        /**
         * {@code :authority}.
         */
        AUTHORITY(":authority"),

        /**
         * {@code :path}.
         */
        PATH(":path"),

        /**
         * {@code :status}.
         */
        STATUS(":status");

        private final ByteString value;
        private static final Set<ByteString> PSEUDO_HEADERS = new HashSet<ByteString>();
        static {
            for (PseudoHeaderName pseudoHeader : PseudoHeaderName.values()) {
                PSEUDO_HEADERS.add(pseudoHeader.value());
            }
        }

        PseudoHeaderName(String value) {
            this.value = new ByteString(value, CharsetUtil.UTF_8);
        }

        public ByteString value() {
            // Return a slice so that the buffer gets its own reader index.
            return value;
        }

        /**
         * Indicates whether the given header name is a valid HTTP/2 pseudo header.
         */
        public static boolean isPseudoHeader(ByteString header) {
            return PSEUDO_HEADERS.contains(header);
        }
    }

    @Override
    Http2Headers add(ByteString name, ByteString value);

    @Override
    Http2Headers add(ByteString name, Iterable<? extends ByteString> values);

    @Override
    Http2Headers add(ByteString name, ByteString... values);

    @Override
    Http2Headers addObject(ByteString name, Object value);

    @Override
    Http2Headers addObject(ByteString name, Iterable<?> values);

    @Override
    Http2Headers addObject(ByteString name, Object... values);

    @Override
    Http2Headers addBoolean(ByteString name, boolean value);

    @Override
    Http2Headers addByte(ByteString name, byte value);

    @Override
    Http2Headers addChar(ByteString name, char value);

    @Override
    Http2Headers addShort(ByteString name, short value);

    @Override
    Http2Headers addInt(ByteString name, int value);

    @Override
    Http2Headers addLong(ByteString name, long value);

    @Override
    Http2Headers addFloat(ByteString name, float value);

    @Override
    Http2Headers addDouble(ByteString name, double value);

    @Override
    Http2Headers addTimeMillis(ByteString name, long value);

    @Override
    Http2Headers add(BinaryHeaders headers);

    @Override
    Http2Headers set(ByteString name, ByteString value);

    @Override
    Http2Headers set(ByteString name, Iterable<? extends ByteString> values);

    @Override
    Http2Headers set(ByteString name, ByteString... values);

    @Override
    Http2Headers setObject(ByteString name, Object value);

    @Override
    Http2Headers setObject(ByteString name, Iterable<?> values);

    @Override
    Http2Headers setObject(ByteString name, Object... values);

    @Override
    Http2Headers setBoolean(ByteString name, boolean value);

    @Override
    Http2Headers setByte(ByteString name, byte value);

    @Override
    Http2Headers setChar(ByteString name, char value);

    @Override
    Http2Headers setShort(ByteString name, short value);

    @Override
    Http2Headers setInt(ByteString name, int value);

    @Override
    Http2Headers setLong(ByteString name, long value);

    @Override
    Http2Headers setFloat(ByteString name, float value);

    @Override
    Http2Headers setDouble(ByteString name, double value);

    @Override
    Http2Headers setTimeMillis(ByteString name, long value);

    @Override
    Http2Headers set(BinaryHeaders headers);

    @Override
    Http2Headers setAll(BinaryHeaders headers);

    @Override
    Http2Headers clear();

    /**
     * Sets the {@link PseudoHeaderName#METHOD} header or {@code null} if there is no such header
     */
    Http2Headers method(ByteString value);

    /**
     * Sets the {@link PseudoHeaderName#SCHEME} header if there is no such header
     */
    Http2Headers scheme(ByteString value);

    /**
     * Sets the {@link PseudoHeaderName#AUTHORITY} header or {@code null} if there is no such header
     */
    Http2Headers authority(ByteString value);

    /**
     * Sets the {@link PseudoHeaderName#PATH} header or {@code null} if there is no such header
     */
    Http2Headers path(ByteString value);

    /**
     * Sets the {@link PseudoHeaderName#STATUS} header or {@code null} if there is no such header
     */
    Http2Headers status(ByteString value);

    /**
     * Gets the {@link PseudoHeaderName#METHOD} header or {@code null} if there is no such header
     */
    ByteString method();

    /**
     * Gets the {@link PseudoHeaderName#SCHEME} header or {@code null} if there is no such header
     */
    ByteString scheme();

    /**
     * Gets the {@link PseudoHeaderName#AUTHORITY} header or {@code null} if there is no such header
     */
    ByteString authority();

    /**
     * Gets the {@link PseudoHeaderName#PATH} header or {@code null} if there is no such header
     */
    ByteString path();

    /**
     * Gets the {@link PseudoHeaderName#STATUS} header or {@code null} if there is no such header
     */
    ByteString status();
}


File: codec-http2/src/main/java/io/netty/handler/codec/http2/HttpUtil.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License, version 2.0 (the
 * "License"); you may not use this file except in compliance with the License. You may obtain a
 * copy of the License at:
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */
package io.netty.handler.codec.http2;

import static io.netty.handler.codec.http2.Http2Error.PROTOCOL_ERROR;
import static io.netty.handler.codec.http2.Http2Exception.connectionError;
import static io.netty.handler.codec.http2.Http2Exception.streamError;
import static io.netty.util.internal.ObjectUtil.checkNotNull;
import io.netty.handler.codec.BinaryHeaders;
import io.netty.handler.codec.TextHeaders.EntryVisitor;
import io.netty.handler.codec.http.DefaultFullHttpRequest;
import io.netty.handler.codec.http.DefaultFullHttpResponse;
import io.netty.handler.codec.http.FullHttpMessage;
import io.netty.handler.codec.http.FullHttpRequest;
import io.netty.handler.codec.http.FullHttpResponse;
import io.netty.handler.codec.http.HttpHeaderNames;
import io.netty.handler.codec.http.HttpHeaderUtil;
import io.netty.handler.codec.http.HttpHeaderValues;
import io.netty.handler.codec.http.HttpHeaders;
import io.netty.handler.codec.http.HttpMessage;
import io.netty.handler.codec.http.HttpMethod;
import io.netty.handler.codec.http.HttpRequest;
import io.netty.handler.codec.http.HttpResponse;
import io.netty.handler.codec.http.HttpResponseStatus;
import io.netty.handler.codec.http.HttpVersion;
import io.netty.util.AsciiString;
import io.netty.util.ByteString;

import java.net.URI;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Provides utility methods and constants for the HTTP/2 to HTTP conversion
 */
public final class HttpUtil {
    /**
     * The set of headers that should not be directly copied when converting headers from HTTP to HTTP/2.
     */
    @SuppressWarnings("deprecation")
    private static final Set<CharSequence> HTTP_TO_HTTP2_HEADER_BLACKLIST = new HashSet<CharSequence>() {
        private static final long serialVersionUID = -5678614530214167043L;
        {
            add(HttpHeaderNames.CONNECTION);
            add(HttpHeaderNames.KEEP_ALIVE);
            add(HttpHeaderNames.PROXY_CONNECTION);
            add(HttpHeaderNames.TRANSFER_ENCODING);
            add(HttpHeaderNames.HOST);
            add(HttpHeaderNames.UPGRADE);
            add(ExtensionHeaderNames.STREAM_ID.text());
            add(ExtensionHeaderNames.AUTHORITY.text());
            add(ExtensionHeaderNames.SCHEME.text());
            add(ExtensionHeaderNames.PATH.text());
        }
    };

    /**
     * This will be the method used for {@link HttpRequest} objects generated out of the HTTP message flow defined in <a
     * href="http://tools.ietf.org/html/draft-ietf-httpbis-http2-16#section-8.1.">HTTP/2 Spec Message Flow</a>
     */
    public static final HttpMethod OUT_OF_MESSAGE_SEQUENCE_METHOD = HttpMethod.OPTIONS;

    /**
     * This will be the path used for {@link HttpRequest} objects generated out of the HTTP message flow defined in <a
     * href="http://tools.ietf.org/html/draft-ietf-httpbis-http2-16#section-8.1.">HTTP/2 Spec Message Flow</a>
     */
    public static final String OUT_OF_MESSAGE_SEQUENCE_PATH = "";

    /**
     * This will be the status code used for {@link HttpResponse} objects generated out of the HTTP message flow defined
     * in <a href="http://tools.ietf.org/html/draft-ietf-httpbis-http2-16#section-8.1.">HTTP/2 Spec Message Flow</a>
     */
    public static final HttpResponseStatus OUT_OF_MESSAGE_SEQUENCE_RETURN_CODE = HttpResponseStatus.OK;

    /**
     * This pattern will use to avoid compile it each time it is used
     * when we need to replace some part of authority.
     */
    private static final Pattern AUTHORITY_REPLACEMENT_PATTERN = Pattern.compile("^.*@");

    private HttpUtil() {
    }

    /**
     * Provides the HTTP header extensions used to carry HTTP/2 information in HTTP objects
     */
    public enum ExtensionHeaderNames {
        /**
         * HTTP extension header which will identify the stream id from the HTTP/2 event(s) responsible for generating a
         * {@code HttpObject}
         * <p>
         * {@code "x-http2-stream-id"}
         */
        STREAM_ID("x-http2-stream-id"),

        /**
         * HTTP extension header which will identify the authority pseudo header from the HTTP/2 event(s) responsible
         * for generating a {@code HttpObject}
         * <p>
         * {@code "x-http2-authority"}
         */
        AUTHORITY("x-http2-authority"),
        /**
         * HTTP extension header which will identify the scheme pseudo header from the HTTP/2 event(s) responsible for
         * generating a {@code HttpObject}
         * <p>
         * {@code "x-http2-scheme"}
         */
        SCHEME("x-http2-scheme"),
        /**
         * HTTP extension header which will identify the path pseudo header from the HTTP/2 event(s) responsible for
         * generating a {@code HttpObject}
         * <p>
         * {@code "x-http2-path"}
         */
        PATH("x-http2-path"),
        /**
         * HTTP extension header which will identify the stream id used to create this stream in a HTTP/2 push promise
         * frame
         * <p>
         * {@code "x-http2-stream-promise-id"}
         */
        STREAM_PROMISE_ID("x-http2-stream-promise-id"),
        /**
         * HTTP extension header which will identify the stream id which this stream is dependent on. This stream will
         * be a child node of the stream id associated with this header value.
         * <p>
         * {@code "x-http2-stream-dependency-id"}
         */
        STREAM_DEPENDENCY_ID("x-http2-stream-dependency-id"),
        /**
         * HTTP extension header which will identify the weight (if non-default and the priority is not on the default
         * stream) of the associated HTTP/2 stream responsible responsible for generating a {@code HttpObject}
         * <p>
         * {@code "x-http2-stream-weight"}
         */
        STREAM_WEIGHT("x-http2-stream-weight");

        private final AsciiString text;

        ExtensionHeaderNames(String text) {
            this.text = new AsciiString(text);
        }

        public AsciiString text() {
            return text;
        }
    }

    /**
     * Apply HTTP/2 rules while translating status code to {@link HttpResponseStatus}
     *
     * @param status The status from an HTTP/2 frame
     * @return The HTTP/1.x status
     * @throws Http2Exception If there is a problem translating from HTTP/2 to HTTP/1.x
     */
    public static HttpResponseStatus parseStatus(ByteString status) throws Http2Exception {
        HttpResponseStatus result;
        try {
            result = HttpResponseStatus.parseLine(status);
            if (result == HttpResponseStatus.SWITCHING_PROTOCOLS) {
                throw connectionError(PROTOCOL_ERROR, "Invalid HTTP/2 status code '%d'", result.code());
            }
        } catch (Http2Exception e) {
            throw e;
        } catch (Throwable t) {
            throw connectionError(PROTOCOL_ERROR, t,
                            "Unrecognized HTTP status code '%s' encountered in translation to HTTP/1.x", status);
        }
        return result;
    }

    /**
     * Create a new object to contain the response data
     *
     * @param streamId The stream associated with the response
     * @param http2Headers The initial set of HTTP/2 headers to create the response with
     * @param validateHttpHeaders <ul>
     *        <li>{@code true} to validate HTTP headers in the http-codec</li>
     *        <li>{@code false} not to validate HTTP headers in the http-codec</li>
     *        </ul>
     * @return A new response object which represents headers/data
     * @throws Http2Exception see {@link #addHttp2ToHttpHeaders(int, Http2Headers, FullHttpMessage, boolean)}
     */
    public static FullHttpResponse toHttpResponse(int streamId, Http2Headers http2Headers, boolean validateHttpHeaders)
                    throws Http2Exception {
        HttpResponseStatus status = parseStatus(http2Headers.status());
        // HTTP/2 does not define a way to carry the version or reason phrase that is included in an
        // HTTP/1.1 status line.
        FullHttpResponse msg = new DefaultFullHttpResponse(HttpVersion.HTTP_1_1, status, validateHttpHeaders);
        addHttp2ToHttpHeaders(streamId, http2Headers, msg, false);
        return msg;
    }

    /**
     * Create a new object to contain the request data
     *
     * @param streamId The stream associated with the request
     * @param http2Headers The initial set of HTTP/2 headers to create the request with
     * @param validateHttpHeaders <ul>
     *        <li>{@code true} to validate HTTP headers in the http-codec</li>
     *        <li>{@code false} not to validate HTTP headers in the http-codec</li>
     *        </ul>
     * @return A new request object which represents headers/data
     * @throws Http2Exception see {@link #addHttp2ToHttpHeaders(int, Http2Headers, FullHttpMessage, boolean)}
     */
    public static FullHttpRequest toHttpRequest(int streamId, Http2Headers http2Headers, boolean validateHttpHeaders)
                    throws Http2Exception {
        // HTTP/2 does not define a way to carry the version identifier that is included in the HTTP/1.1 request line.
        final ByteString method = checkNotNull(http2Headers.method(),
                "method header cannot be null in conversion to HTTP/1.x");
        final ByteString path = checkNotNull(http2Headers.path(),
                "path header cannot be null in conversion to HTTP/1.x");
        FullHttpRequest msg = new DefaultFullHttpRequest(HttpVersion.HTTP_1_1, HttpMethod.valueOf(method
                        .toString()), path.toString(), validateHttpHeaders);
        addHttp2ToHttpHeaders(streamId, http2Headers, msg, false);
        return msg;
    }

    /**
     * Translate and add HTTP/2 headers to HTTP/1.x headers
     *
     * @param streamId The stream associated with {@code sourceHeaders}
     * @param sourceHeaders The HTTP/2 headers to convert
     * @param destinationMessage The object which will contain the resulting HTTP/1.x headers
     * @param addToTrailer {@code true} to add to trailing headers. {@code false} to add to initial headers.
     * @throws Http2Exception If not all HTTP/2 headers can be translated to HTTP/1.x
     */
    public static void addHttp2ToHttpHeaders(int streamId, Http2Headers sourceHeaders,
                    FullHttpMessage destinationMessage, boolean addToTrailer) throws Http2Exception {
        HttpHeaders headers = addToTrailer ? destinationMessage.trailingHeaders() : destinationMessage.headers();
        boolean request = destinationMessage instanceof HttpRequest;
        Http2ToHttpHeaderTranslator visitor = new Http2ToHttpHeaderTranslator(streamId, headers, request);
        try {
            sourceHeaders.forEachEntry(visitor);
        } catch (Http2Exception ex) {
            throw ex;
        } catch (Throwable t) {
            throw streamError(streamId, PROTOCOL_ERROR, t, "HTTP/2 to HTTP/1.x headers conversion error");
        }

        headers.remove(HttpHeaderNames.TRANSFER_ENCODING);
        headers.remove(HttpHeaderNames.TRAILER);
        if (!addToTrailer) {
            headers.setInt(ExtensionHeaderNames.STREAM_ID.text(), streamId);
            HttpHeaderUtil.setKeepAlive(destinationMessage, true);
        }
    }

    /**
     * Converts the given HTTP/1.x headers into HTTP/2 headers.
     */
    public static Http2Headers toHttp2Headers(HttpMessage in) throws Exception {
        final Http2Headers out = new DefaultHttp2Headers();
        HttpHeaders inHeaders = in.headers();
        if (in instanceof HttpRequest) {
            HttpRequest request = (HttpRequest) in;
            out.path(new AsciiString(request.uri()));
            out.method(new AsciiString(request.method().toString()));

            String value = inHeaders.getAndConvert(HttpHeaderNames.HOST);
            if (value != null) {
                URI hostUri = URI.create(value);
                // The authority MUST NOT include the deprecated "userinfo" subcomponent
                value = hostUri.getAuthority();
                if (value != null) {
                    out.authority(new AsciiString(AUTHORITY_REPLACEMENT_PATTERN.matcher(value).replaceFirst("")));
                }
                value = hostUri.getScheme();
                if (value != null) {
                    out.scheme(new AsciiString(value));
                }
            }

            // Consume the Authority extension header if present
            CharSequence cValue = inHeaders.get(ExtensionHeaderNames.AUTHORITY.text());
            if (cValue != null) {
                out.authority(AsciiString.of(cValue));
            }

            // Consume the Scheme extension header if present
            cValue = inHeaders.get(ExtensionHeaderNames.SCHEME.text());
            if (cValue != null) {
                out.scheme(AsciiString.of(cValue));
            }
        } else if (in instanceof HttpResponse) {
            HttpResponse response = (HttpResponse) in;
            out.status(new AsciiString(Integer.toString(response.status().code())));
        }

        // Add the HTTP headers which have not been consumed above
        return out.add(toHttp2Headers(inHeaders));
    }

    public static Http2Headers toHttp2Headers(HttpHeaders inHeaders) throws Exception {
        if (inHeaders.isEmpty()) {
            return EmptyHttp2Headers.INSTANCE;
        }

        final Http2Headers out = new DefaultHttp2Headers();

        inHeaders.forEachEntry(new EntryVisitor() {
            @Override
            public boolean visit(Entry<CharSequence, CharSequence> entry) throws Exception {
                final AsciiString aName = AsciiString.of(entry.getKey()).toLowerCase();
                if (!HTTP_TO_HTTP2_HEADER_BLACKLIST.contains(aName)) {
                    AsciiString aValue = AsciiString.of(entry.getValue());
                    // https://tools.ietf.org/html/draft-ietf-httpbis-http2-16#section-8.1.2.2
                    // makes a special exception for TE
                    if (!aName.equalsIgnoreCase(HttpHeaderNames.TE) ||
                        aValue.equalsIgnoreCase(HttpHeaderValues.TRAILERS)) {
                        out.add(aName, aValue);
                    }
                }
                return true;
            }
        });
        return out;
    }

    /**
     * A visitor which translates HTTP/2 headers to HTTP/1 headers
     */
    private static final class Http2ToHttpHeaderTranslator implements BinaryHeaders.EntryVisitor {
        /**
         * Translations from HTTP/2 header name to the HTTP/1.x equivalent.
         */
        private static final Map<ByteString, ByteString>
            REQUEST_HEADER_TRANSLATIONS = new HashMap<ByteString, ByteString>();
        private static final Map<ByteString, ByteString>
            RESPONSE_HEADER_TRANSLATIONS = new HashMap<ByteString, ByteString>();
        static {
            RESPONSE_HEADER_TRANSLATIONS.put(Http2Headers.PseudoHeaderName.AUTHORITY.value(),
                            ExtensionHeaderNames.AUTHORITY.text());
            RESPONSE_HEADER_TRANSLATIONS.put(Http2Headers.PseudoHeaderName.SCHEME.value(),
                            ExtensionHeaderNames.SCHEME.text());
            REQUEST_HEADER_TRANSLATIONS.putAll(RESPONSE_HEADER_TRANSLATIONS);
            RESPONSE_HEADER_TRANSLATIONS.put(Http2Headers.PseudoHeaderName.PATH.value(),
                            ExtensionHeaderNames.PATH.text());
        }

        private final int streamId;
        private final HttpHeaders output;
        private final Map<ByteString, ByteString> translations;

        /**
         * Create a new instance
         *
         * @param output The HTTP/1.x headers object to store the results of the translation
         * @param request if {@code true}, translates headers using the request translation map. Otherwise uses the
         *        response translation map.
         */
        Http2ToHttpHeaderTranslator(int streamId, HttpHeaders output, boolean request) {
            this.streamId = streamId;
            this.output = output;
            translations = request ? REQUEST_HEADER_TRANSLATIONS : RESPONSE_HEADER_TRANSLATIONS;
        }

        @Override
        public boolean visit(Entry<ByteString, ByteString> entry) throws Http2Exception {
            final ByteString name = entry.getKey();
            final ByteString value = entry.getValue();
            ByteString translatedName = translations.get(name);
            if (translatedName != null || !Http2Headers.PseudoHeaderName.isPseudoHeader(name)) {
                if (translatedName == null) {
                    translatedName = name;
                }

                // http://tools.ietf.org/html/draft-ietf-httpbis-http2-16#section-8.1.2.3
                // All headers that start with ':' are only valid in HTTP/2 context
                if (translatedName.isEmpty() || translatedName.byteAt(0) == ':') {
                    throw streamError(streamId, PROTOCOL_ERROR,
                            "Invalid HTTP/2 header '%s' encountered in translation to HTTP/1.x", translatedName);
                } else {
                    output.add(new AsciiString(translatedName, false), new AsciiString(value, false));
                }
            }
            return true;
        }
    }
}


File: codec-http2/src/main/java/io/netty/handler/codec/http2/InboundHttp2ToHttpPriorityAdapter.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License, version 2.0 (the
 * "License"); you may not use this file except in compliance with the License. You may obtain a
 * copy of the License at:
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */
package io.netty.handler.codec.http2;

import static io.netty.handler.codec.http2.Http2Error.PROTOCOL_ERROR;
import static io.netty.handler.codec.http2.Http2Exception.connectionError;

import java.util.Map.Entry;

import io.netty.channel.ChannelHandlerContext;
import io.netty.handler.codec.TextHeaders.EntryVisitor;
import io.netty.handler.codec.http.DefaultHttpHeaders;
import io.netty.handler.codec.http.FullHttpMessage;
import io.netty.handler.codec.http.HttpHeaders;
import io.netty.util.AsciiString;
import io.netty.util.collection.IntObjectHashMap;
import io.netty.util.collection.IntObjectMap;
import io.netty.util.internal.PlatformDependent;

/**
 * Translate header/data/priority HTTP/2 frame events into HTTP events.  Just as {@link InboundHttp2ToHttpAdapter}
 * may generate multiple {@link FullHttpMessage} objects per stream, this class is more likely to
 * generate multiple messages per stream because the chances of an HTTP/2 event happening outside
 * the header/data message flow is more likely.
 */
public final class InboundHttp2ToHttpPriorityAdapter extends InboundHttp2ToHttpAdapter {
    private static final AsciiString OUT_OF_MESSAGE_SEQUENCE_METHOD = new AsciiString(
            HttpUtil.OUT_OF_MESSAGE_SEQUENCE_METHOD.toString());
    private static final AsciiString OUT_OF_MESSAGE_SEQUENCE_PATH = new AsciiString(
            HttpUtil.OUT_OF_MESSAGE_SEQUENCE_PATH);
    private static final AsciiString OUT_OF_MESSAGE_SEQUENCE_RETURN_CODE = new AsciiString(
            HttpUtil.OUT_OF_MESSAGE_SEQUENCE_RETURN_CODE.toString());
    private final IntObjectMap<HttpHeaders> outOfMessageFlowHeaders;

    public static final class Builder extends InboundHttp2ToHttpAdapter.Builder {

        /**
         * Creates a new {@link InboundHttp2ToHttpPriorityAdapter} builder for the specified {@link Http2Connection}.
         *
         * @param connection The object which will provide connection notification events for the current connection
         */
        public Builder(Http2Connection connection) {
            super(connection);
        }

        @Override
        public InboundHttp2ToHttpPriorityAdapter build() {
            final InboundHttp2ToHttpPriorityAdapter instance = new InboundHttp2ToHttpPriorityAdapter(this);
            instance.connection.addListener(instance);
            return instance;
        }
    }

    InboundHttp2ToHttpPriorityAdapter(Builder builder) {
        super(builder);
        outOfMessageFlowHeaders = new IntObjectHashMap<HttpHeaders>();
    }

    @Override
    protected void removeMessage(int streamId) {
        super.removeMessage(streamId);
        outOfMessageFlowHeaders.remove(streamId);
    }

    /**
     * Get either the header or the trailing headers depending on which is valid to add to
     * @param msg The message containing the headers and trailing headers
     * @return The headers object which can be appended to or modified
     */
    private static HttpHeaders getActiveHeaders(FullHttpMessage msg) {
        return msg.content().isReadable() ? msg.trailingHeaders() : msg.headers();
    }

    /**
     * This method will add the {@code headers} to the out of order headers map
     * @param streamId The stream id associated with {@code headers}
     * @param headers Newly encountered out of order headers which must be stored for future use
     */
    private void importOutOfMessageFlowHeaders(int streamId, HttpHeaders headers) {
        final HttpHeaders outOfMessageFlowHeader = outOfMessageFlowHeaders.get(streamId);
        if (outOfMessageFlowHeader == null) {
            outOfMessageFlowHeaders.put(streamId, headers);
        } else {
            outOfMessageFlowHeader.setAll(headers);
        }
    }

    /**
     * Take any saved out of order headers and export them to {@code headers}
     * @param streamId The stream id to search for out of order headers for
     * @param headers If any out of order headers exist for {@code streamId} they will be added to this object
     */
    private void exportOutOfMessageFlowHeaders(int streamId, final HttpHeaders headers) {
        final HttpHeaders outOfMessageFlowHeader = outOfMessageFlowHeaders.get(streamId);
        if (outOfMessageFlowHeader != null) {
            headers.setAll(outOfMessageFlowHeader);
        }
    }

    /**
     * This will remove all headers which are related to priority tree events
     * @param headers The headers to remove the priority tree elements from
     */
    private static void removePriorityRelatedHeaders(HttpHeaders headers) {
        headers.remove(HttpUtil.ExtensionHeaderNames.STREAM_DEPENDENCY_ID.text());
        headers.remove(HttpUtil.ExtensionHeaderNames.STREAM_WEIGHT.text());
    }

    /**
     * Initializes the pseudo header fields for out of message flow HTTP/2 headers
     * @param headers The headers to be initialized with pseudo header values
     */
    private void initializePseudoHeaders(Http2Headers headers) {
        if (connection.isServer()) {
            headers.method(OUT_OF_MESSAGE_SEQUENCE_METHOD).path(OUT_OF_MESSAGE_SEQUENCE_PATH);
        } else {
            headers.status(OUT_OF_MESSAGE_SEQUENCE_RETURN_CODE);
        }
    }

    /**
     * Add all the HTTP headers into the HTTP/2 headers object
     * @param httpHeaders The HTTP headers to translate to HTTP/2
     * @param http2Headers The target HTTP/2 headers
     */
    private static void addHttpHeadersToHttp2Headers(HttpHeaders httpHeaders, final Http2Headers http2Headers) {
        try {
            httpHeaders.forEachEntry(new EntryVisitor() {
                @Override
                public boolean visit(Entry<CharSequence, CharSequence> entry) throws Exception {
                    http2Headers.add(AsciiString.of(entry.getKey()), AsciiString.of(entry.getValue()));
                    return true;
                }
            });
        } catch (Exception ex) {
            PlatformDependent.throwException(ex);
        }
    }

    @Override
    protected void fireChannelRead(ChannelHandlerContext ctx, FullHttpMessage msg, int streamId) {
        exportOutOfMessageFlowHeaders(streamId, getActiveHeaders(msg));
        super.fireChannelRead(ctx, msg, streamId);
    }

    @Override
    protected FullHttpMessage processHeadersBegin(ChannelHandlerContext ctx, int streamId, Http2Headers headers,
            boolean endOfStream, boolean allowAppend, boolean appendToTrailer) throws Http2Exception {
        FullHttpMessage msg = super.processHeadersBegin(ctx, streamId, headers,
                endOfStream, allowAppend, appendToTrailer);
        if (msg != null) {
            exportOutOfMessageFlowHeaders(streamId, getActiveHeaders(msg));
        }
        return msg;
    }

    @Override
    public void onPriorityTreeParentChanged(Http2Stream stream, Http2Stream oldParent) {
        Http2Stream parent = stream.parent();
        FullHttpMessage msg = messageMap.get(stream.id());
        if (msg == null) {
            // msg may be null if a HTTP/2 frame event in received outside the HTTP message flow
            // For example a PRIORITY frame can be received in any state
            // and the HTTP message flow exists in OPEN.
            if (parent != null && !parent.equals(connection.connectionStream())) {
                HttpHeaders headers = new DefaultHttpHeaders();
                headers.setInt(HttpUtil.ExtensionHeaderNames.STREAM_DEPENDENCY_ID.text(), parent.id());
                importOutOfMessageFlowHeaders(stream.id(), headers);
            }
        } else {
            if (parent == null) {
                removePriorityRelatedHeaders(msg.headers());
                removePriorityRelatedHeaders(msg.trailingHeaders());
            } else if (!parent.equals(connection.connectionStream())) {
                HttpHeaders headers = getActiveHeaders(msg);
                headers.setInt(HttpUtil.ExtensionHeaderNames.STREAM_DEPENDENCY_ID.text(), parent.id());
            }
        }
    }

    @Override
    public void onWeightChanged(Http2Stream stream, short oldWeight) {
        FullHttpMessage msg = messageMap.get(stream.id());
        final HttpHeaders headers;
        if (msg == null) {
            // msg may be null if a HTTP/2 frame event in received outside the HTTP message flow
            // For example a PRIORITY frame can be received in any state
            // and the HTTP message flow exists in OPEN.
            headers = new DefaultHttpHeaders();
            importOutOfMessageFlowHeaders(stream.id(), headers);
        } else {
            headers = getActiveHeaders(msg);
        }
        headers.setShort(HttpUtil.ExtensionHeaderNames.STREAM_WEIGHT.text(), stream.weight());
    }

    @Override
    public void onPriorityRead(ChannelHandlerContext ctx, int streamId, int streamDependency, short weight,
                    boolean exclusive) throws Http2Exception {
        FullHttpMessage msg = messageMap.get(streamId);
        if (msg == null) {
            HttpHeaders httpHeaders = outOfMessageFlowHeaders.remove(streamId);
            if (httpHeaders == null) {
                throw connectionError(PROTOCOL_ERROR, "Priority Frame recieved for unknown stream id %d", streamId);
            }

            Http2Headers http2Headers = new DefaultHttp2Headers();
            initializePseudoHeaders(http2Headers);
            addHttpHeadersToHttp2Headers(httpHeaders, http2Headers);
            msg = newMessage(streamId, http2Headers, validateHttpHeaders);
            fireChannelRead(ctx, msg, streamId);
        }
    }
}


File: codec-http2/src/test/java/io/netty/handler/codec/http2/DefaultHttp2HeadersTest.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License, version
 * 2.0 (the "License"); you may not use this file except in compliance with the
 * License. You may obtain a copy of the License at:
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */
package io.netty.handler.codec.http2;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import io.netty.util.AsciiString;
import io.netty.util.ByteString;
import io.netty.util.CharsetUtil;

import org.junit.Test;

public class DefaultHttp2HeadersTest {

    private static final byte[] NAME_BYTES = { 'T', 'E', 's', 'T' };
    private static final byte[] NAME_BYTES_LOWERCASE = { 't', 'e', 's', 't' };
    private static final ByteString NAME_BYTESTRING = new ByteString(NAME_BYTES);
    private static final AsciiString NAME_ASCIISTRING = new AsciiString("Test");
    private static final ByteString VALUE = new ByteString("some value", CharsetUtil.UTF_8);

    @Test
    public void defaultLowercase() {
        Http2Headers headers = new DefaultHttp2Headers().set(NAME_BYTESTRING, VALUE);
        assertArrayEquals(NAME_BYTES_LOWERCASE, first(headers).toByteArray());
    }

    @Test
    public void defaultLowercaseAsciiString() {
        Http2Headers headers = new DefaultHttp2Headers().set(NAME_ASCIISTRING, VALUE);
        assertEquals(NAME_ASCIISTRING.toLowerCase(), first(headers));
    }

    @Test
    public void caseInsensitive() {
        Http2Headers headers = new DefaultHttp2Headers(false).set(NAME_BYTESTRING, VALUE);
        assertArrayEquals(NAME_BYTES, first(headers).toByteArray());
    }

    private static ByteString first(Http2Headers headers) {
        return headers.names().iterator().next();
    }
}


File: codec-http2/src/test/java/io/netty/handler/codec/http2/Http2TestUtil.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License, version 2.0 (the
 * "License"); you may not use this file except in compliance with the License. You may obtain a
 * copy of the License at:
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */
package io.netty.handler.codec.http2;

import io.netty.buffer.ByteBuf;
import io.netty.channel.Channel;
import io.netty.channel.ChannelHandlerContext;
import io.netty.handler.codec.ByteToMessageDecoder;
import io.netty.util.AsciiString;
import io.netty.util.ByteString;

import java.util.List;
import java.util.Random;
import java.util.concurrent.CountDownLatch;

/**
 * Utilities for the integration tests.
 */
final class Http2TestUtil {
    /**
     * Interface that allows for running a operation that throws a {@link Http2Exception}.
     */
    interface Http2Runnable {
        void run() throws Http2Exception;
    }

    /**
     * Runs the given operation within the event loop thread of the given {@link Channel}.
     */
    static void runInChannel(Channel channel, final Http2Runnable runnable) {
        channel.eventLoop().execute(new Runnable() {
            @Override
            public void run() {
                try {
                    runnable.run();
                } catch (Http2Exception e) {
                    throw new RuntimeException(e);
                }
            }
        });
    }

    /**
     * Converts a {@link String} into an {@link AsciiString}.
     */
    public static AsciiString as(String value) {
        return new AsciiString(value);
    }

    /**
     * Converts a byte array into an {@link AsciiString}.
     */
    public static ByteString as(byte[] value) {
        return new ByteString(value);
    }

    /**
     * Returns a byte array filled with random data.
     */
    public static byte[] randomBytes() {
        return randomBytes(100);
    }

    /**
     * Returns a byte array filled with random data.
     */
    public static byte[] randomBytes(int size) {
        byte[] data = new byte[size];
        new Random().nextBytes(data);
        return data;
    }

    /**
     * Returns an {@link AsciiString} that wraps a randomly-filled byte array.
     */
    public static ByteString randomString() {
        return as(randomBytes());
    }

    private Http2TestUtil() {
    }

    static class FrameAdapter extends ByteToMessageDecoder {
        private final Http2Connection connection;
        private final Http2FrameListener listener;
        private final DefaultHttp2FrameReader reader;
        private final CountDownLatch latch;

        FrameAdapter(Http2FrameListener listener, CountDownLatch latch) {
            this(null, listener, latch);
        }

        FrameAdapter(Http2Connection connection, Http2FrameListener listener, CountDownLatch latch) {
            this(connection, new DefaultHttp2FrameReader(), listener, latch);
        }

        FrameAdapter(Http2Connection connection, DefaultHttp2FrameReader reader, Http2FrameListener listener,
                CountDownLatch latch) {
            this.connection = connection;
            this.listener = listener;
            this.reader = reader;
            this.latch = latch;
        }

        private Http2Stream getOrCreateStream(int streamId, boolean halfClosed) throws Http2Exception {
            return getOrCreateStream(connection, streamId, halfClosed);
        }

        public static Http2Stream getOrCreateStream(Http2Connection connection, int streamId, boolean halfClosed)
                throws Http2Exception {
            if (connection != null) {
                Http2Stream stream = connection.stream(streamId);
                if (stream == null) {
                    if (connection.isServer() && streamId % 2 == 0 || !connection.isServer() && streamId % 2 != 0) {
                        stream = connection.local().createStream(streamId, halfClosed);
                    } else {
                        stream = connection.remote().createStream(streamId, halfClosed);
                    }
                }
                return stream;
            }
            return null;
        }

        private void closeStream(Http2Stream stream) {
            closeStream(stream, false);
        }

        protected void closeStream(Http2Stream stream, boolean dataRead) {
            if (stream != null) {
                stream.close();
            }
        }

        @Override
        protected void decode(ChannelHandlerContext ctx, ByteBuf in, List<Object> out) throws Exception {
            reader.readFrame(ctx, in, new Http2FrameListener() {
                @Override
                public int onDataRead(ChannelHandlerContext ctx, int streamId, ByteBuf data, int padding,
                        boolean endOfStream) throws Http2Exception {
                    Http2Stream stream = getOrCreateStream(streamId, endOfStream);
                    int processed = listener.onDataRead(ctx, streamId, data, padding, endOfStream);
                    if (endOfStream) {
                        closeStream(stream, true);
                    }
                    latch.countDown();
                    return processed;
                }

                @Override
                public void onHeadersRead(ChannelHandlerContext ctx, int streamId, Http2Headers headers, int padding,
                        boolean endStream) throws Http2Exception {
                    Http2Stream stream = getOrCreateStream(streamId, endStream);
                    listener.onHeadersRead(ctx, streamId, headers, padding, endStream);
                    if (endStream) {
                        closeStream(stream);
                    }
                    latch.countDown();
                }

                @Override
                public void onHeadersRead(ChannelHandlerContext ctx, int streamId, Http2Headers headers,
                        int streamDependency, short weight, boolean exclusive, int padding, boolean endStream)
                        throws Http2Exception {
                    Http2Stream stream = getOrCreateStream(streamId, endStream);
                    if (stream != null) {
                        stream.setPriority(streamDependency, weight, exclusive);
                    }
                    listener.onHeadersRead(ctx, streamId, headers, streamDependency, weight, exclusive, padding,
                            endStream);
                    if (endStream) {
                        closeStream(stream);
                    }
                    latch.countDown();
                }

                @Override
                public void onPriorityRead(ChannelHandlerContext ctx, int streamId, int streamDependency, short weight,
                        boolean exclusive) throws Http2Exception {
                    Http2Stream stream = getOrCreateStream(streamId, false);
                    if (stream != null) {
                        stream.setPriority(streamDependency, weight, exclusive);
                    }
                    listener.onPriorityRead(ctx, streamId, streamDependency, weight, exclusive);
                    latch.countDown();
                }

                @Override
                public void onRstStreamRead(ChannelHandlerContext ctx, int streamId, long errorCode)
                        throws Http2Exception {
                    Http2Stream stream = getOrCreateStream(streamId, false);
                    listener.onRstStreamRead(ctx, streamId, errorCode);
                    closeStream(stream);
                    latch.countDown();
                }

                @Override
                public void onSettingsAckRead(ChannelHandlerContext ctx) throws Http2Exception {
                    listener.onSettingsAckRead(ctx);
                    latch.countDown();
                }

                @Override
                public void onSettingsRead(ChannelHandlerContext ctx, Http2Settings settings) throws Http2Exception {
                    listener.onSettingsRead(ctx, settings);
                    latch.countDown();
                }

                @Override
                public void onPingRead(ChannelHandlerContext ctx, ByteBuf data) throws Http2Exception {
                    listener.onPingRead(ctx, data);
                    latch.countDown();
                }

                @Override
                public void onPingAckRead(ChannelHandlerContext ctx, ByteBuf data) throws Http2Exception {
                    listener.onPingAckRead(ctx, data);
                    latch.countDown();
                }

                @Override
                public void onPushPromiseRead(ChannelHandlerContext ctx, int streamId, int promisedStreamId,
                        Http2Headers headers, int padding) throws Http2Exception {
                    getOrCreateStream(promisedStreamId, false);
                    listener.onPushPromiseRead(ctx, streamId, promisedStreamId, headers, padding);
                    latch.countDown();
                }

                @Override
                public void onGoAwayRead(ChannelHandlerContext ctx, int lastStreamId, long errorCode, ByteBuf debugData)
                        throws Http2Exception {
                    listener.onGoAwayRead(ctx, lastStreamId, errorCode, debugData);
                    latch.countDown();
                }

                @Override
                public void onWindowUpdateRead(ChannelHandlerContext ctx, int streamId, int windowSizeIncrement)
                        throws Http2Exception {
                    getOrCreateStream(streamId, false);
                    listener.onWindowUpdateRead(ctx, streamId, windowSizeIncrement);
                    latch.countDown();
                }

                @Override
                public void onUnknownFrame(ChannelHandlerContext ctx, byte frameType, int streamId, Http2Flags flags,
                        ByteBuf payload) throws Http2Exception {
                    listener.onUnknownFrame(ctx, frameType, streamId, flags, payload);
                    latch.countDown();
                }
            });
        }
    }

    /**
     * A decorator around a {@link Http2FrameListener} that counts down the latch so that we can await the completion of
     * the request.
     */
    static class FrameCountDown implements Http2FrameListener {
        private final Http2FrameListener listener;
        private final CountDownLatch messageLatch;
        private final CountDownLatch settingsAckLatch;
        private final CountDownLatch dataLatch;
        private final CountDownLatch trailersLatch;
        private final CountDownLatch goAwayLatch;

        FrameCountDown(Http2FrameListener listener, CountDownLatch settingsAckLatch, CountDownLatch messageLatch) {
            this(listener, settingsAckLatch, messageLatch, null, null);
        }

        FrameCountDown(Http2FrameListener listener, CountDownLatch settingsAckLatch, CountDownLatch messageLatch,
                CountDownLatch dataLatch, CountDownLatch trailersLatch) {
            this(listener, settingsAckLatch, messageLatch, dataLatch, trailersLatch, messageLatch);
        }

        FrameCountDown(Http2FrameListener listener, CountDownLatch settingsAckLatch, CountDownLatch messageLatch,
                CountDownLatch dataLatch, CountDownLatch trailersLatch, CountDownLatch goAwayLatch) {
            this.listener = listener;
            this.messageLatch = messageLatch;
            this.settingsAckLatch = settingsAckLatch;
            this.dataLatch = dataLatch;
            this.trailersLatch = trailersLatch;
            this.goAwayLatch = goAwayLatch;
        }

        @Override
        public int onDataRead(ChannelHandlerContext ctx, int streamId, ByteBuf data, int padding, boolean endOfStream)
                throws Http2Exception {
            int numBytes = data.readableBytes();
            int processed = listener.onDataRead(ctx, streamId, data, padding, endOfStream);
            messageLatch.countDown();
            if (dataLatch != null) {
                for (int i = 0; i < numBytes; ++i) {
                    dataLatch.countDown();
                }
            }
            return processed;
        }

        @Override
        public void onHeadersRead(ChannelHandlerContext ctx, int streamId, Http2Headers headers, int padding,
                boolean endStream) throws Http2Exception {
            listener.onHeadersRead(ctx, streamId, headers, padding, endStream);
            messageLatch.countDown();
            if (trailersLatch != null && endStream) {
                trailersLatch.countDown();
            }
        }

        @Override
        public void onHeadersRead(ChannelHandlerContext ctx, int streamId, Http2Headers headers, int streamDependency,
                short weight, boolean exclusive, int padding, boolean endStream) throws Http2Exception {
            listener.onHeadersRead(ctx, streamId, headers, streamDependency, weight, exclusive, padding, endStream);
            messageLatch.countDown();
            if (trailersLatch != null && endStream) {
                trailersLatch.countDown();
            }
        }

        @Override
        public void onPriorityRead(ChannelHandlerContext ctx, int streamId, int streamDependency, short weight,
                boolean exclusive) throws Http2Exception {
            listener.onPriorityRead(ctx, streamId, streamDependency, weight, exclusive);
            messageLatch.countDown();
        }

        @Override
        public void onRstStreamRead(ChannelHandlerContext ctx, int streamId, long errorCode) throws Http2Exception {
            listener.onRstStreamRead(ctx, streamId, errorCode);
            messageLatch.countDown();
        }

        @Override
        public void onSettingsAckRead(ChannelHandlerContext ctx) throws Http2Exception {
            listener.onSettingsAckRead(ctx);
            settingsAckLatch.countDown();
        }

        @Override
        public void onSettingsRead(ChannelHandlerContext ctx, Http2Settings settings) throws Http2Exception {
            listener.onSettingsRead(ctx, settings);
            messageLatch.countDown();
        }

        @Override
        public void onPingRead(ChannelHandlerContext ctx, ByteBuf data) throws Http2Exception {
            listener.onPingRead(ctx, data);
            messageLatch.countDown();
        }

        @Override
        public void onPingAckRead(ChannelHandlerContext ctx, ByteBuf data) throws Http2Exception {
            listener.onPingAckRead(ctx, data);
            messageLatch.countDown();
        }

        @Override
        public void onPushPromiseRead(ChannelHandlerContext ctx, int streamId, int promisedStreamId,
                Http2Headers headers, int padding) throws Http2Exception {
            listener.onPushPromiseRead(ctx, streamId, promisedStreamId, headers, padding);
            messageLatch.countDown();
        }

        @Override
        public void onGoAwayRead(ChannelHandlerContext ctx, int lastStreamId, long errorCode, ByteBuf debugData)
                throws Http2Exception {
            listener.onGoAwayRead(ctx, lastStreamId, errorCode, debugData);
            goAwayLatch.countDown();
        }

        @Override
        public void onWindowUpdateRead(ChannelHandlerContext ctx, int streamId, int windowSizeIncrement)
                throws Http2Exception {
            listener.onWindowUpdateRead(ctx, streamId, windowSizeIncrement);
            messageLatch.countDown();
        }

        @Override
        public void onUnknownFrame(ChannelHandlerContext ctx, byte frameType, int streamId, Http2Flags flags,
                ByteBuf payload) throws Http2Exception {
            listener.onUnknownFrame(ctx, frameType, streamId, flags, payload);
            messageLatch.countDown();
        }
    }
}


File: codec-stomp/src/main/java/io/netty/handler/codec/stomp/DefaultStompHeaders.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package io.netty.handler.codec.stomp;

import io.netty.handler.codec.DefaultTextHeaders;
import io.netty.handler.codec.TextHeaders;

public class DefaultStompHeaders extends DefaultTextHeaders implements StompHeaders {

    @Override
    public StompHeaders add(CharSequence name, CharSequence value) {
        super.add(name, value);
        return this;
    }

    @Override
    public StompHeaders add(CharSequence name, Iterable<? extends CharSequence> values) {
        super.add(name, values);
        return this;
    }

    @Override
    public StompHeaders add(CharSequence name, CharSequence... values) {
        super.add(name, values);
        return this;
    }

    @Override
    public StompHeaders addObject(CharSequence name, Object value) {
        super.addObject(name, value);
        return this;
    }

    @Override
    public StompHeaders addObject(CharSequence name, Iterable<?> values) {
        super.addObject(name, values);
        return this;
    }

    @Override
    public StompHeaders addObject(CharSequence name, Object... values) {
        super.addObject(name, values);
        return this;
    }

    @Override
    public StompHeaders addBoolean(CharSequence name, boolean value) {
        super.addBoolean(name, value);
        return this;
    }

    @Override
    public StompHeaders addChar(CharSequence name, char value) {
        super.addChar(name, value);
        return this;
    }

    @Override
    public StompHeaders addByte(CharSequence name, byte value) {
        super.addByte(name, value);
        return this;
    }

    @Override
    public StompHeaders addShort(CharSequence name, short value) {
        super.addShort(name, value);
        return this;
    }

    @Override
    public StompHeaders addInt(CharSequence name, int value) {
        super.addInt(name, value);
        return this;
    }

    @Override
    public StompHeaders addLong(CharSequence name, long value) {
        super.addLong(name, value);
        return this;
    }

    @Override
    public StompHeaders addFloat(CharSequence name, float value) {
        super.addFloat(name, value);
        return this;
    }

    @Override
    public StompHeaders addDouble(CharSequence name, double value) {
        super.addDouble(name, value);
        return this;
    }

    @Override
    public StompHeaders addTimeMillis(CharSequence name, long value) {
        super.addTimeMillis(name, value);
        return this;
    }

    @Override
    public StompHeaders add(TextHeaders headers) {
        super.add(headers);
        return this;
    }

    @Override
    public StompHeaders set(CharSequence name, CharSequence value) {
        super.set(name, value);
        return this;
    }

    @Override
    public StompHeaders set(CharSequence name, Iterable<? extends CharSequence> values) {
        super.set(name, values);
        return this;
    }

    @Override
    public StompHeaders set(CharSequence name, CharSequence... values) {
        super.set(name, values);
        return this;
    }

    @Override
    public StompHeaders setObject(CharSequence name, Object value) {
        super.setObject(name, value);
        return this;
    }

    @Override
    public StompHeaders setObject(CharSequence name, Iterable<?> values) {
        super.setObject(name, values);
        return this;
    }

    @Override
    public StompHeaders setObject(CharSequence name, Object... values) {
        super.setObject(name, values);
        return this;
    }

    @Override
    public StompHeaders setBoolean(CharSequence name, boolean value) {
        super.setBoolean(name, value);
        return this;
    }

    @Override
    public StompHeaders setChar(CharSequence name, char value) {
        super.setChar(name, value);
        return this;
    }

    @Override
    public StompHeaders setByte(CharSequence name, byte value) {
        super.setByte(name, value);
        return this;
    }

    @Override
    public StompHeaders setShort(CharSequence name, short value) {
        super.setShort(name, value);
        return this;
    }

    @Override
    public StompHeaders setInt(CharSequence name, int value) {
        super.setInt(name, value);
        return this;
    }

    @Override
    public StompHeaders setLong(CharSequence name, long value) {
        super.setLong(name, value);
        return this;
    }

    @Override
    public StompHeaders setFloat(CharSequence name, float value) {
        super.setFloat(name, value);
        return this;
    }

    @Override
    public StompHeaders setDouble(CharSequence name, double value) {
        super.setDouble(name, value);
        return this;
    }

    @Override
    public StompHeaders setTimeMillis(CharSequence name, long value) {
        super.setTimeMillis(name, value);
        return this;
    }

    @Override
    public StompHeaders set(TextHeaders headers) {
        super.set(headers);
        return this;
    }

    @Override
    public StompHeaders setAll(TextHeaders headers) {
        super.setAll(headers);
        return this;
    }

    @Override
    public StompHeaders clear() {
        super.clear();
        return this;
    }
}


File: codec-stomp/src/main/java/io/netty/handler/codec/stomp/StompSubframeEncoder.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */
package io.netty.handler.codec.stomp;

import io.netty.buffer.ByteBuf;
import io.netty.channel.ChannelHandlerContext;
import io.netty.handler.codec.AsciiHeadersEncoder;
import io.netty.handler.codec.AsciiHeadersEncoder.NewlineType;
import io.netty.handler.codec.AsciiHeadersEncoder.SeparatorType;
import io.netty.handler.codec.MessageToMessageEncoder;
import io.netty.util.CharsetUtil;
import io.netty.util.internal.PlatformDependent;

import java.util.List;

/**
 * Encodes a {@link StompFrame} or a {@link StompSubframe} into a {@link ByteBuf}.
 */
public class StompSubframeEncoder extends MessageToMessageEncoder<StompSubframe> {

    @Override
    protected void encode(ChannelHandlerContext ctx, StompSubframe msg, List<Object> out) throws Exception {
        if (msg instanceof StompFrame) {
            StompFrame frame = (StompFrame) msg;
            ByteBuf frameBuf = encodeFrame(frame, ctx);
            out.add(frameBuf);
            ByteBuf contentBuf = encodeContent(frame, ctx);
            out.add(contentBuf);
        } else if (msg instanceof StompHeadersSubframe) {
            StompHeadersSubframe frame = (StompHeadersSubframe) msg;
            ByteBuf buf = encodeFrame(frame, ctx);
            out.add(buf);
        } else if (msg instanceof StompContentSubframe) {
            StompContentSubframe stompContentSubframe = (StompContentSubframe) msg;
            ByteBuf buf = encodeContent(stompContentSubframe, ctx);
            out.add(buf);
        }
    }

    private static ByteBuf encodeContent(StompContentSubframe content, ChannelHandlerContext ctx) {
        if (content instanceof LastStompContentSubframe) {
            ByteBuf buf = ctx.alloc().buffer(content.content().readableBytes() + 1);
            buf.writeBytes(content.content());
            buf.writeByte(StompConstants.NUL);
            return buf;
        } else {
            return content.content().retain();
        }
    }

    private static ByteBuf encodeFrame(StompHeadersSubframe frame, ChannelHandlerContext ctx) {
        ByteBuf buf = ctx.alloc().buffer();

        buf.writeBytes(frame.command().toString().getBytes(CharsetUtil.US_ASCII));
        buf.writeByte(StompConstants.LF);
        try {
            frame.headers().forEachEntry(new AsciiHeadersEncoder(buf, SeparatorType.COLON, NewlineType.LF));
        } catch (Exception ex) {
            buf.release();
            PlatformDependent.throwException(ex);
        }
        buf.writeByte(StompConstants.LF);
        return buf;
    }
}


File: codec-stomp/src/test/java/io/netty/handler/codec/stomp/StompTestConstants.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */
package io.netty.handler.codec.stomp;

public final class StompTestConstants {
    public static final String CONNECT_FRAME =
        "CONNECT\n" +
            "host:stomp.github.org\n" +
            "accept-version:1.1,1.2\n" +
            '\n' +
            '\0';
    public static final String CONNECTED_FRAME =
        "CONNECTED\n" +
            "version:1.2\n" +
            '\n' +
            "\0\n";
    public static final String SEND_FRAME_1 =
        "SEND\n" +
            "destination:/queue/a\n" +
            "content-type:text/plain\n" +
            '\n' +
            "hello, queue a!" +
            "\0\n";
    public static final String SEND_FRAME_2 =
        "SEND\n" +
            "destination:/queue/a\n" +
            "content-type:text/plain\n" +
            "content-length:17\n" +
            '\n' +
            "hello, queue a!!!" +
            "\0\n";

    private StompTestConstants() { }
}


File: codec/src/main/java/io/netty/handler/codec/AsciiHeadersEncoder.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package io.netty.handler.codec;


import java.util.Map.Entry;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufUtil;
import io.netty.handler.codec.TextHeaders.EntryVisitor;
import io.netty.util.AsciiString;

public final class AsciiHeadersEncoder implements EntryVisitor {

    /**
     * The separator characters to insert between a header name and a header value.
     */
    public enum SeparatorType {
        /**
         * {@code ':'}
         */
        COLON,
        /**
         * {@code ': '}
         */
        COLON_SPACE,
    }

    /**
     * The newline characters to insert between header entries.
     */
    public enum NewlineType {
        /**
         * {@code '\n'}
         */
        LF,
        /**
         * {@code '\r\n'}
         */
        CRLF
    }

    private final ByteBuf buf;
    private final SeparatorType separatorType;
    private final NewlineType newlineType;

    public AsciiHeadersEncoder(ByteBuf buf) {
        this(buf, SeparatorType.COLON_SPACE, NewlineType.CRLF);
    }

    public AsciiHeadersEncoder(ByteBuf buf, SeparatorType separatorType, NewlineType newlineType) {
        if (buf == null) {
            throw new NullPointerException("buf");
        }
        if (separatorType == null) {
            throw new NullPointerException("separatorType");
        }
        if (newlineType == null) {
            throw new NullPointerException("newlineType");
        }

        this.buf = buf;
        this.separatorType = separatorType;
        this.newlineType = newlineType;
    }

    @Override
    public boolean visit(Entry<CharSequence, CharSequence> entry) throws Exception {
        final CharSequence name = entry.getKey();
        final CharSequence value = entry.getValue();
        final ByteBuf buf = this.buf;
        final int nameLen = name.length();
        final int valueLen = value.length();
        final int entryLen = nameLen + valueLen + 4;
        int offset = buf.writerIndex();
        buf.ensureWritable(entryLen);
        writeAscii(buf, offset, name, nameLen);
        offset += nameLen;

        switch (separatorType) {
            case COLON:
                buf.setByte(offset ++, ':');
                break;
            case COLON_SPACE:
                buf.setByte(offset ++, ':');
                buf.setByte(offset ++, ' ');
                break;
            default:
                throw new Error();
        }

        writeAscii(buf, offset, value, valueLen);
        offset += valueLen;

        switch (newlineType) {
            case LF:
                buf.setByte(offset ++, '\n');
                break;
            case CRLF:
                buf.setByte(offset ++, '\r');
                buf.setByte(offset ++, '\n');
                break;
            default:
                throw new Error();
        }

        buf.writerIndex(offset);
        return true;
    }

    private static void writeAscii(ByteBuf buf, int offset, CharSequence value, int valueLen) {
        if (value instanceof AsciiString) {
            writeAsciiString(buf, offset, (AsciiString) value, valueLen);
        } else {
            writeCharSequence(buf, offset, value, valueLen);
        }
    }

    private static void writeAsciiString(ByteBuf buf, int offset, AsciiString value, int valueLen) {
        ByteBufUtil.copy(value, 0, buf, offset, valueLen);
    }

    private static void writeCharSequence(ByteBuf buf, int offset, CharSequence value, int valueLen) {
        for (int i = 0; i < valueLen; i ++) {
            buf.setByte(offset ++, c2b(value.charAt(i)));
        }
    }

    private static int c2b(char ch) {
        return ch < 256? (byte) ch : '?';
    }
}


File: codec/src/main/java/io/netty/handler/codec/BinaryHeaders.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package io.netty.handler.codec;

import io.netty.util.ByteString;

/**
 * A typical {@code ByteString} multimap used by protocols that use binary headers (such as HTTP/2) for the
 * representation of arbitrary key-value data. {@link ByteString} is just a wrapper around a byte array but provides
 * some additional utility when handling text data.
 */
public interface BinaryHeaders extends Headers<ByteString> {
    /**
     * Provides an abstraction to iterate over elements maintained in the {@link Headers} collection.
     */
    interface EntryVisitor extends Headers.EntryVisitor<ByteString> {
    }

    /**
     * Provides an abstraction to iterate over elements maintained in the {@link Headers} collection.
     */
    interface NameVisitor extends Headers.NameVisitor<ByteString> {
    }

    @Override
    BinaryHeaders add(ByteString name, ByteString value);

    @Override
    BinaryHeaders add(ByteString name, Iterable<? extends ByteString> values);

    @Override
    BinaryHeaders add(ByteString name, ByteString... values);

    @Override
    BinaryHeaders addObject(ByteString name, Object value);

    @Override
    BinaryHeaders addObject(ByteString name, Iterable<?> values);

    @Override
    BinaryHeaders addObject(ByteString name, Object... values);

    @Override
    BinaryHeaders addBoolean(ByteString name, boolean value);

    @Override
    BinaryHeaders addByte(ByteString name, byte value);

    @Override
    BinaryHeaders addChar(ByteString name, char value);

    @Override
    BinaryHeaders addShort(ByteString name, short value);

    @Override
    BinaryHeaders addInt(ByteString name, int value);

    @Override
    BinaryHeaders addLong(ByteString name, long value);

    @Override
    BinaryHeaders addFloat(ByteString name, float value);

    @Override
    BinaryHeaders addDouble(ByteString name, double value);

    @Override
    BinaryHeaders addTimeMillis(ByteString name, long value);

    /**
     * See {@link Headers#add(Headers)}
     */
    BinaryHeaders add(BinaryHeaders headers);

    @Override
    BinaryHeaders set(ByteString name, ByteString value);

    @Override
    BinaryHeaders set(ByteString name, Iterable<? extends ByteString> values);

    @Override
    BinaryHeaders set(ByteString name, ByteString... values);

    @Override
    BinaryHeaders setObject(ByteString name, Object value);

    @Override
    BinaryHeaders setObject(ByteString name, Iterable<?> values);

    @Override
    BinaryHeaders setObject(ByteString name, Object... values);

    @Override
    BinaryHeaders setBoolean(ByteString name, boolean value);

    @Override
    BinaryHeaders setByte(ByteString name, byte value);

    @Override
    BinaryHeaders setChar(ByteString name, char value);

    @Override
    BinaryHeaders setShort(ByteString name, short value);

    @Override
    BinaryHeaders setInt(ByteString name, int value);

    @Override
    BinaryHeaders setLong(ByteString name, long value);

    @Override
    BinaryHeaders setFloat(ByteString name, float value);

    @Override
    BinaryHeaders setDouble(ByteString name, double value);

    @Override
    BinaryHeaders setTimeMillis(ByteString name, long value);

    /**
     * See {@link Headers#set(Headers)}
     */
    BinaryHeaders set(BinaryHeaders headers);

    /**
     * See {@link Headers#setAll(Headers)}
     */
    BinaryHeaders setAll(BinaryHeaders headers);

    @Override
    BinaryHeaders clear();
}


File: codec/src/main/java/io/netty/handler/codec/ConvertibleHeaders.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License, version 2.0 (the
 * "License"); you may not use this file except in compliance with the License. You may obtain a
 * copy of the License at:
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */
package io.netty.handler.codec;

import java.util.Comparator;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;

/**
 * Extension to the {@link Headers} interface to provide methods which convert the
 * native {@code UnconvertedType} to the not-native {@code ConvertedType}
 */
public interface ConvertibleHeaders<UnconvertedType, ConvertedType> extends Headers<UnconvertedType> {

    /**
     * Interface to do conversions to and from the two generic type parameters
     */
    interface TypeConverter<UnconvertedType, ConvertedType> {
        /**
         * Convert a native value
         * @param value The value to be converted
         * @return The conversion results
         */
        ConvertedType toConvertedType(UnconvertedType value);

        /**
         * Undo a conversion and restore the original native type
         * @param value The converted value
         * @return The original native type
         */
        UnconvertedType toUnconvertedType(ConvertedType value);
    }

    /**
     * Invokes {@link Headers#get(Object)} and does a conversion on the results if not {@code null}
     * @param name The name of entry to get
     * @return The value corresponding to {@code name} and then converted
     */
    ConvertedType getAndConvert(UnconvertedType name);

    /**
     * Invokes {@link Headers#get(Object, Object)} and does a conversion on the results if not {@code null}
     * @param name The name of entry to get
     * @return The value corresponding to {@code name} and then converted
     */
    ConvertedType getAndConvert(UnconvertedType name, ConvertedType defaultValue);

    /**
     * Invokes {@link Headers#getAndRemove(Object)} and does a conversion on the results if not {@code null}
     * @param name The name of entry to get
     * @return The value corresponding to {@code name} and then converted
     */
    ConvertedType getAndRemoveAndConvert(UnconvertedType name);

    /**
     * Invokes {@link Headers#getAndRemove(Object, Object)} and does
     * a conversion on the results if not {@code null}
     * @param name The name of entry to get
     * @return The value corresponding to {@code name} and then converted
     */
    ConvertedType getAndRemoveAndConvert(UnconvertedType name, ConvertedType defaultValue);

    /**
     * Invokes {@link Headers#getAll(Object)} and does a conversion on the results if not {@code null}
     * @param name The name of entry to get
     * @return The values corresponding to {@code name} and then converted
     */
    List<ConvertedType> getAllAndConvert(UnconvertedType name);

    /**
     * Invokes {@link Headers#getAllAndRemove(Object)} and does a conversion on the results if not {@code null}
     * @param name The name of entry to get
     * @return The values corresponding to {@code name} and then converted
     */
    List<ConvertedType> getAllAndRemoveAndConvert(UnconvertedType name);

    /**
     * Invokes {@link Headers#entries()} and lazily does a conversion on the results as they are accessed
     *
     * @return The values corresponding to {@code name} and then lazily converted
     */
    List<Map.Entry<ConvertedType, ConvertedType>> entriesConverted();

    /**
     * Invokes {@link Headers#iterator()} and lazily does a conversion on the results as they are accessed
     *
     * @return Iterator which will provide converted values corresponding to {@code name}
     */
    Iterator<Entry<ConvertedType, ConvertedType>> iteratorConverted();

    /**
     * Invokes {@link Headers#names()} and does a conversion on the results
     *
     * @return The values corresponding to {@code name} and then converted
     */
    Set<ConvertedType> namesAndConvert(Comparator<ConvertedType> comparator);
}


File: codec/src/main/java/io/netty/handler/codec/DefaultBinaryHeaders.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License, version 2.0 (the
 * "License"); you may not use this file except in compliance with the License. You may obtain a
 * copy of the License at:
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */
package io.netty.handler.codec;

import io.netty.util.ByteString;
import io.netty.util.CharsetUtil;
import io.netty.util.internal.PlatformDependent;

import java.nio.charset.Charset;
import java.text.ParseException;

public class DefaultBinaryHeaders extends DefaultHeaders<ByteString> implements BinaryHeaders {
    private static final ValueConverter<ByteString> OBJECT_TO_BYTE = new ValueConverter<ByteString>() {
        private final Charset DEFAULT_CHARSET = CharsetUtil.UTF_8;
        @Override
        public ByteString convertObject(Object value) {
            if (value instanceof ByteString) {
                return (ByteString) value;
            }
            if (value instanceof CharSequence) {
                return new ByteString((CharSequence) value, DEFAULT_CHARSET);
            }
            return new ByteString(value.toString(), DEFAULT_CHARSET);
        }

        @Override
        public ByteString convertInt(int value) {
            return new ByteString(String.valueOf(value), DEFAULT_CHARSET);
        }

        @Override
        public ByteString convertLong(long value) {
            return new ByteString(String.valueOf(value), DEFAULT_CHARSET);
        }

        @Override
        public ByteString convertDouble(double value) {
            return new ByteString(String.valueOf(value), DEFAULT_CHARSET);
        }

        @Override
        public ByteString convertChar(char value) {
            return new ByteString(String.valueOf(value), DEFAULT_CHARSET);
        }

        @Override
        public ByteString convertBoolean(boolean value) {
            return new ByteString(String.valueOf(value), DEFAULT_CHARSET);
        }

        @Override
        public ByteString convertFloat(float value) {
            return new ByteString(String.valueOf(value), DEFAULT_CHARSET);
        }

        @Override
        public int convertToInt(ByteString value) {
            return value.parseAsciiInt();
        }

        @Override
        public long convertToLong(ByteString value) {
            return value.parseAsciiLong();
        }

        @Override
        public ByteString convertTimeMillis(long value) {
            return new ByteString(String.valueOf(value), DEFAULT_CHARSET);
        }

        @Override
        public long convertToTimeMillis(ByteString value) {
            try {
                return HeaderDateFormat.get().parse(value.toString());
            } catch (ParseException e) {
                PlatformDependent.throwException(e);
            }
            return 0;
        }

        @Override
        public double convertToDouble(ByteString value) {
            return value.parseAsciiDouble();
        }

        @Override
        public char convertToChar(ByteString value) {
            return value.parseChar();
        }

        @Override
        public boolean convertToBoolean(ByteString value) {
            return value.byteAt(0) != 0;
        }

        @Override
        public float convertToFloat(ByteString value) {
            return value.parseAsciiFloat();
        }

        @Override
        public ByteString convertShort(short value) {
            return new ByteString(String.valueOf(value), DEFAULT_CHARSET);
        }

        @Override
        public short convertToShort(ByteString value) {
            return value.parseAsciiShort();
        }

        @Override
        public ByteString convertByte(byte value) {
            return new ByteString(String.valueOf(value), DEFAULT_CHARSET);
        }

        @Override
        public byte convertToByte(ByteString value) {
            return value.byteAt(0);
        }
    };

    private static final HashCodeGenerator<ByteString> JAVA_HASH_CODE_GENERATOR =
            new JavaHashCodeGenerator<ByteString>();
    protected static final NameConverter<ByteString> IDENTITY_NAME_CONVERTER = new IdentityNameConverter<ByteString>();

    public DefaultBinaryHeaders() {
        this(IDENTITY_NAME_CONVERTER);
    }

    public DefaultBinaryHeaders(NameConverter<ByteString> nameConverter) {
        super(ByteString.DEFAULT_COMPARATOR, ByteString.DEFAULT_COMPARATOR,
                JAVA_HASH_CODE_GENERATOR, OBJECT_TO_BYTE, nameConverter);
    }

    @Override
    public BinaryHeaders add(ByteString name, ByteString value) {
        super.add(name, value);
        return this;
    }

    @Override
    public BinaryHeaders add(ByteString name, Iterable<? extends ByteString> values) {
        super.add(name, values);
        return this;
    }

    @Override
    public BinaryHeaders add(ByteString name, ByteString... values) {
        super.add(name, values);
        return this;
    }

    @Override
    public BinaryHeaders addObject(ByteString name, Object value) {
        super.addObject(name, value);
        return this;
    }

    @Override
    public BinaryHeaders addObject(ByteString name, Iterable<?> values) {
        super.addObject(name, values);
        return this;
    }

    @Override
    public BinaryHeaders addObject(ByteString name, Object... values) {
        super.addObject(name, values);
        return this;
    }

    @Override
    public BinaryHeaders addBoolean(ByteString name, boolean value) {
        super.addBoolean(name, value);
        return this;
    }

    @Override
    public BinaryHeaders addChar(ByteString name, char value) {
        super.addChar(name, value);
        return this;
    }

    @Override
    public BinaryHeaders addByte(ByteString name, byte value) {
        super.addByte(name, value);
        return this;
    }

    @Override
    public BinaryHeaders addShort(ByteString name, short value) {
        super.addShort(name, value);
        return this;
    }

    @Override
    public BinaryHeaders addInt(ByteString name, int value) {
        super.addInt(name, value);
        return this;
    }

    @Override
    public BinaryHeaders addLong(ByteString name, long value) {
        super.addLong(name, value);
        return this;
    }

    @Override
    public BinaryHeaders addFloat(ByteString name, float value) {
        super.addFloat(name, value);
        return this;
    }

    @Override
    public BinaryHeaders addDouble(ByteString name, double value) {
        super.addDouble(name, value);
        return this;
    }

    @Override
    public BinaryHeaders addTimeMillis(ByteString name, long value) {
        super.addTimeMillis(name, value);
        return this;
    }

    @Override
    public BinaryHeaders add(BinaryHeaders headers) {
        super.add(headers);
        return this;
    }

    @Override
    public BinaryHeaders set(ByteString name, ByteString value) {
        super.set(name, value);
        return this;
    }

    @Override
    public BinaryHeaders set(ByteString name, Iterable<? extends ByteString> values) {
        super.set(name, values);
        return this;
    }

    @Override
    public BinaryHeaders set(ByteString name, ByteString... values) {
        super.set(name, values);
        return this;
    }

    @Override
    public BinaryHeaders setObject(ByteString name, Object value) {
        super.setObject(name, value);
        return this;
    }

    @Override
    public BinaryHeaders setObject(ByteString name, Iterable<?> values) {
        super.setObject(name, values);
        return this;
    }

    @Override
    public BinaryHeaders setObject(ByteString name, Object... values) {
        super.setObject(name, values);
        return this;
    }

    @Override
    public BinaryHeaders setBoolean(ByteString name, boolean value) {
        super.setBoolean(name, value);
        return this;
    }

    @Override
    public BinaryHeaders setChar(ByteString name, char value) {
        super.setChar(name, value);
        return this;
    }

    @Override
    public BinaryHeaders setByte(ByteString name, byte value) {
        super.setByte(name, value);
        return this;
    }

    @Override
    public BinaryHeaders setShort(ByteString name, short value) {
        super.setShort(name, value);
        return this;
    }

    @Override
    public BinaryHeaders setInt(ByteString name, int value) {
        super.setInt(name, value);
        return this;
    }

    @Override
    public BinaryHeaders setLong(ByteString name, long value) {
        super.setLong(name, value);
        return this;
    }

    @Override
    public BinaryHeaders setFloat(ByteString name, float value) {
        super.setFloat(name, value);
        return this;
    }

    @Override
    public BinaryHeaders setDouble(ByteString name, double value) {
        super.setDouble(name, value);
        return this;
    }

    @Override
    public BinaryHeaders setTimeMillis(ByteString name, long value) {
        super.setTimeMillis(name, value);
        return this;
    }

    @Override
    public BinaryHeaders set(BinaryHeaders headers) {
        super.set(headers);
        return this;
    }

    @Override
    public BinaryHeaders setAll(BinaryHeaders headers) {
        super.setAll(headers);
        return this;
    }

    @Override
    public BinaryHeaders clear() {
        super.clear();
        return this;
    }
}


File: codec/src/main/java/io/netty/handler/codec/DefaultConvertibleHeaders.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License, version 2.0 (the
 * "License"); you may not use this file except in compliance with the License. You may obtain a
 * copy of the License at:
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */
package io.netty.handler.codec;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.Iterator;
import java.util.List;
import java.util.Map.Entry;
import java.util.Set;
import java.util.TreeSet;

public class DefaultConvertibleHeaders<UnconvertedType, ConvertedType> extends DefaultHeaders<UnconvertedType>
        implements ConvertibleHeaders<UnconvertedType, ConvertedType> {

    private final TypeConverter<UnconvertedType, ConvertedType> typeConverter;

    public DefaultConvertibleHeaders(Comparator<? super UnconvertedType> keyComparator,
            Comparator<? super UnconvertedType> valueComparator,
            HashCodeGenerator<UnconvertedType> hashCodeGenerator,
            ValueConverter<UnconvertedType> valueConverter,
            TypeConverter<UnconvertedType, ConvertedType> typeConverter) {
        super(keyComparator, valueComparator, hashCodeGenerator, valueConverter);
        this.typeConverter = typeConverter;
    }

    public DefaultConvertibleHeaders(Comparator<? super UnconvertedType> keyComparator,
            Comparator<? super UnconvertedType> valueComparator,
            HashCodeGenerator<UnconvertedType> hashCodeGenerator,
            ValueConverter<UnconvertedType> valueConverter,
            TypeConverter<UnconvertedType, ConvertedType> typeConverter,
            NameConverter<UnconvertedType> nameConverter) {
        super(keyComparator, valueComparator, hashCodeGenerator, valueConverter, nameConverter);
        this.typeConverter = typeConverter;
    }

    @Override
    public ConvertedType getAndConvert(UnconvertedType name) {
        return getAndConvert(name, null);
    }

    @Override
    public ConvertedType getAndConvert(UnconvertedType name, ConvertedType defaultValue) {
        UnconvertedType v = get(name);
        if (v == null) {
            return defaultValue;
        }
        return typeConverter.toConvertedType(v);
    }

    @Override
    public ConvertedType getAndRemoveAndConvert(UnconvertedType name) {
        return getAndRemoveAndConvert(name, null);
    }

    @Override
    public ConvertedType getAndRemoveAndConvert(UnconvertedType name, ConvertedType defaultValue) {
        UnconvertedType v = getAndRemove(name);
        if (v == null) {
            return defaultValue;
        }
        return typeConverter.toConvertedType(v);
    }

    @Override
    public List<ConvertedType> getAllAndConvert(UnconvertedType name) {
        List<UnconvertedType> all = getAll(name);
        List<ConvertedType> allConverted = new ArrayList<ConvertedType>(all.size());
        for (int i = 0; i < all.size(); ++i) {
            allConverted.add(typeConverter.toConvertedType(all.get(i)));
        }
        return allConverted;
    }

    @Override
    public List<ConvertedType> getAllAndRemoveAndConvert(UnconvertedType name) {
        List<UnconvertedType> all = getAllAndRemove(name);
        List<ConvertedType> allConverted = new ArrayList<ConvertedType>(all.size());
        for (int i = 0; i < all.size(); ++i) {
            allConverted.add(typeConverter.toConvertedType(all.get(i)));
        }
        return allConverted;
    }

    @Override
    public List<Entry<ConvertedType, ConvertedType>> entriesConverted() {
        List<Entry<UnconvertedType, UnconvertedType>> entries = entries();
        List<Entry<ConvertedType, ConvertedType>> entriesConverted = new ArrayList<Entry<ConvertedType, ConvertedType>>(
                entries.size());
        for (int i = 0; i < entries.size(); ++i) {
            entriesConverted.add(new ConvertedEntry(entries.get(i)));
        }
        return entriesConverted;
    }

    @Override
    public Iterator<Entry<ConvertedType, ConvertedType>> iteratorConverted() {
        return new ConvertedIterator();
    }

    @Override
    public Set<ConvertedType> namesAndConvert(Comparator<ConvertedType> comparator) {
        Set<UnconvertedType> names = names();
        Set<ConvertedType> namesConverted = new TreeSet<ConvertedType>(comparator);
        for (UnconvertedType unconverted : names) {
            namesConverted.add(typeConverter.toConvertedType(unconverted));
        }
        return namesConverted;
    }

    private final class ConvertedIterator implements Iterator<Entry<ConvertedType, ConvertedType>> {
        private final Iterator<Entry<UnconvertedType, UnconvertedType>> iter = iterator();

        @Override
        public boolean hasNext() {
            return iter.hasNext();
        }

        @Override
        public Entry<ConvertedType, ConvertedType> next() {
            Entry<UnconvertedType, UnconvertedType> next = iter.next();

            return new ConvertedEntry(next);
        }

        @Override
        public void remove() {
            throw new UnsupportedOperationException();
        }
    }

    private final class ConvertedEntry implements Entry<ConvertedType, ConvertedType> {
        private final Entry<UnconvertedType, UnconvertedType> entry;
        private ConvertedType name;
        private ConvertedType value;

        ConvertedEntry(Entry<UnconvertedType, UnconvertedType> entry) {
            this.entry = entry;
        }

        @Override
        public ConvertedType getKey() {
            if (name == null) {
                name = typeConverter.toConvertedType(entry.getKey());
            }
            return name;
        }

        @Override
        public ConvertedType getValue() {
            if (value == null) {
                value = typeConverter.toConvertedType(entry.getValue());
            }
            return value;
        }

        @Override
        public ConvertedType setValue(ConvertedType value) {
            ConvertedType old = getValue();
            entry.setValue(typeConverter.toUnconvertedType(value));
            return old;
        }

        @Override
        public String toString() {
            return entry.toString();
        }
    }
}


File: codec/src/main/java/io/netty/handler/codec/DefaultHeaders.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License, version 2.0 (the
 * "License"); you may not use this file except in compliance with the License. You may obtain a
 * copy of the License at:
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */
package io.netty.handler.codec;

import io.netty.util.collection.IntObjectHashMap;
import io.netty.util.collection.IntObjectMap;
import io.netty.util.concurrent.FastThreadLocal;
import io.netty.util.internal.PlatformDependent;

import java.text.DateFormat;
import java.text.ParseException;
import java.text.ParsePosition;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Date;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Map.Entry;
import java.util.NoSuchElementException;
import java.util.Set;
import java.util.TimeZone;
import java.util.TreeSet;

import static io.netty.util.internal.ObjectUtil.*;

public class DefaultHeaders<T> implements Headers<T> {
    /**
     * Allows users of this interface to specify a hash code other than the default {@link Object#hashCode()}
     */
    public interface HashCodeGenerator<T> {
        /**
         * Obtain the hash code for the given {@code name}
         *
         * @param name The name to generate the hash code for
         * @return The hash code for {@code name}
         */
        int generateHashCode(T name);
    }

    /**
     * Allows users to convert the {@code name} elements before being processed by this map
     */
    public interface NameConverter<T> {
        /**
         * Convert the {@code name} to some other form of the same object type
         *
         * @param name The object to convert
         * @return The results of the conversion
         */
        T convertName(T name);
    }

    /**
     * Uses the {@link #hashCode()} method to generate the hash code.
     */
    public static final class JavaHashCodeGenerator<T> implements HashCodeGenerator<T> {
        @Override
        public int generateHashCode(T name) {
            return name.hashCode();
        }
    }

    /**
     * A name converted which does not covert but instead just returns this {@code name} unchanged
     */
    public static final class IdentityNameConverter<T> implements NameConverter<T> {
        @Override
        public T convertName(T name) {
            return name;
        }
    }

    private static final int HASH_CODE_PRIME = 31;
    private static final int DEFAULT_BUCKET_SIZE = 17;
    private static final int DEFAULT_MAP_SIZE = 4;
    private static final NameConverter<Object> DEFAULT_NAME_CONVERTER = new IdentityNameConverter<Object>();

    private final IntObjectMap<HeaderEntry> entries;
    private final IntObjectMap<HeaderEntry> tailEntries;
    private final HeaderEntry head;
    private final Comparator<? super T> keyComparator;
    private final Comparator<? super T> valueComparator;
    private final HashCodeGenerator<T> hashCodeGenerator;
    private final ValueConverter<T> valueConverter;
    private final NameConverter<T> nameConverter;
    private final int bucketSize;
    int size;

    @SuppressWarnings("unchecked")
    public DefaultHeaders(Comparator<? super T> keyComparator, Comparator<? super T> valueComparator,
            HashCodeGenerator<T> hashCodeGenerator, ValueConverter<T> typeConverter) {
        this(keyComparator, valueComparator, hashCodeGenerator, typeConverter,
                (NameConverter<T>) DEFAULT_NAME_CONVERTER);
    }

    public DefaultHeaders(Comparator<? super T> keyComparator, Comparator<? super T> valueComparator,
            HashCodeGenerator<T> hashCodeGenerator, ValueConverter<T> typeConverter, NameConverter<T> nameConverter) {
        this(keyComparator, valueComparator, hashCodeGenerator, typeConverter, nameConverter, DEFAULT_BUCKET_SIZE,
                DEFAULT_MAP_SIZE);
    }

    public DefaultHeaders(Comparator<? super T> keyComparator, Comparator<? super T> valueComparator,
            HashCodeGenerator<T> hashCodeGenerator, ValueConverter<T> valueConverter, NameConverter<T> nameConverter,
            int bucketSize, int initialMapSize) {
        if (keyComparator == null) {
            throw new NullPointerException("keyComparator");
        }
        if (valueComparator == null) {
            throw new NullPointerException("valueComparator");
        }
        if (hashCodeGenerator == null) {
            throw new NullPointerException("hashCodeGenerator");
        }
        if (valueConverter == null) {
            throw new NullPointerException("valueConverter");
        }
        if (nameConverter == null) {
            throw new NullPointerException("nameConverter");
        }
        if (bucketSize < 1) {
            throw new IllegalArgumentException("bucketSize must be a positive integer");
        }
        head = new HeaderEntry();
        head.before = head.after = head;
        this.keyComparator = keyComparator;
        this.valueComparator = valueComparator;
        this.hashCodeGenerator = hashCodeGenerator;
        this.valueConverter = valueConverter;
        this.nameConverter = nameConverter;
        this.bucketSize = bucketSize;
        entries = new IntObjectHashMap<HeaderEntry>(initialMapSize);
        tailEntries = new IntObjectHashMap<HeaderEntry>(initialMapSize);
    }

    @Override
    public T get(T name) {
        checkNotNull(name, "name");

        int h = hashCodeGenerator.generateHashCode(name);
        int i = index(h);
        HeaderEntry e = entries.get(i);
        while (e != null) {
            if (e.hash == h && keyComparator.compare(e.name, name) == 0) {
                return e.value;
            }
            e = e.next;
        }
        return null;
    }

    @Override
    public T get(T name, T defaultValue) {
        T value = get(name);
        if (value == null) {
            return defaultValue;
        }
        return value;
    }

    @Override
    public T getAndRemove(T name) {
        checkNotNull(name, "name");
        int h = hashCodeGenerator.generateHashCode(name);
        int i = index(h);
        HeaderEntry e = entries.get(i);
        if (e == null) {
            return null;
        }

        T value = null;
        for (;;) {
            if (e.hash == h && keyComparator.compare(e.name, name) == 0) {
                if (value == null) {
                    value = e.value;
                }
                e.remove();
                HeaderEntry next = e.next;
                if (next != null) {
                    entries.put(i, next);
                    e = next;
                } else {
                    entries.remove(i);
                    tailEntries.remove(i);
                    return value;
                }
            } else {
                break;
            }
        }

        for (;;) {
            HeaderEntry next = e.next;
            if (next == null) {
                break;
            }
            if (next.hash == h && keyComparator.compare(e.name, name) == 0) {
                if (value == null) {
                    value = next.value;
                }
                e.next = next.next;
                if (e.next == null) {
                    tailEntries.put(i, e);
                }
                next.remove();
            } else {
                e = next;
            }
        }

        return value;
    }

    @Override
    public T getAndRemove(T name, T defaultValue) {
        T value = getAndRemove(name);
        if (value == null) {
            return defaultValue;
        }
        return value;
    }

    @Override
    public List<T> getAll(T name) {
        checkNotNull(name, "name");
        List<T> values = new ArrayList<T>(4);
        int h = hashCodeGenerator.generateHashCode(name);
        int i = index(h);
        HeaderEntry e = entries.get(i);
        while (e != null) {
            if (e.hash == h && keyComparator.compare(e.name, name) == 0) {
                values.add(e.value);
            }
            e = e.next;
        }

        return values;
    }

    @Override
    public List<T> getAllAndRemove(T name) {
        checkNotNull(name, "name");
        int h = hashCodeGenerator.generateHashCode(name);
        int i = index(h);
        HeaderEntry e = entries.get(i);
        if (e == null) {
            return null;
        }

        List<T> values = new ArrayList<T>(4);
        for (;;) {
            if (e.hash == h && keyComparator.compare(e.name, name) == 0) {
                values.add(e.value);
                e.remove();
                HeaderEntry next = e.next;
                if (next != null) {
                    entries.put(i, next);
                    e = next;
                } else {
                    entries.remove(i);
                    tailEntries.remove(i);
                    return values;
                }
            } else {
                break;
            }
        }

        for (;;) {
            HeaderEntry next = e.next;
            if (next == null) {
                break;
            }
            if (next.hash == h && keyComparator.compare(next.name, name) == 0) {
                values.add(next.value);
                e.next = next.next;
                if (e.next == null) {
                    tailEntries.put(i, e);
                }
                next.remove();
            } else {
                e = next;
            }
        }

        return values;
    }

    @Override
    public List<Entry<T, T>> entries() {
        final int size = size();
        List<Map.Entry<T, T>> localEntries = new ArrayList<Map.Entry<T, T>>(size);

        HeaderEntry e = head.after;
        while (e != head) {
            localEntries.add(e);
            e = e.after;
        }

        assert size == localEntries.size();
        return localEntries;
    }

    @Override
    public boolean contains(T name) {
        return get(name) != null;
    }

    @Override
    public boolean contains(T name, T value) {
        return contains(name, value, keyComparator, valueComparator);
    }

    @Override
    public boolean containsObject(T name, Object value) {
        return contains(name, valueConverter.convertObject(checkNotNull(value, "value")));
    }

    @Override
    public boolean containsBoolean(T name, boolean value) {
        return contains(name, valueConverter.convertBoolean(checkNotNull(value, "value")));
    }

    @Override
    public boolean containsByte(T name, byte value) {
        return contains(name, valueConverter.convertByte(checkNotNull(value, "value")));
    }

    @Override
    public boolean containsChar(T name, char value) {
        return contains(name, valueConverter.convertChar(checkNotNull(value, "value")));
    }

    @Override
    public boolean containsShort(T name, short value) {
        return contains(name, valueConverter.convertShort(checkNotNull(value, "value")));
    }

    @Override
    public boolean containsInt(T name, int value) {
        return contains(name, valueConverter.convertInt(checkNotNull(value, "value")));
    }

    @Override
    public boolean containsLong(T name, long value) {
        return contains(name, valueConverter.convertLong(checkNotNull(value, "value")));
    }

    @Override
    public boolean containsFloat(T name, float value) {
        return contains(name, valueConverter.convertFloat(checkNotNull(value, "value")));
    }

    @Override
    public boolean containsDouble(T name, double value) {
        return contains(name, valueConverter.convertDouble(checkNotNull(value, "value")));
    }

    @Override
    public boolean containsTimeMillis(T name, long value) {
        return contains(name, valueConverter.convertTimeMillis(checkNotNull(value, "value")));
    }

    @Override
    public boolean contains(T name, T value, Comparator<? super T> comparator) {
        return contains(name, value, comparator, comparator);
    }

    @Override
    public boolean contains(T name, T value,
            Comparator<? super T> keyComparator, Comparator<? super T> valueComparator) {
        checkNotNull(name, "name");
        checkNotNull(value, "value");
        checkNotNull(keyComparator, "keyComparator");
        checkNotNull(valueComparator, "valueComparator");
        int h = hashCodeGenerator.generateHashCode(name);
        int i = index(h);
        HeaderEntry e = entries.get(i);
        while (e != null) {
            if (e.hash == h &&
                    keyComparator.compare(e.name, name) == 0 &&
                    valueComparator.compare(e.value, value) == 0) {
                return true;
            }
            e = e.next;
        }
        return false;
    }

    @Override
    public boolean containsObject(T name, Object value, Comparator<? super T> comparator) {
        return containsObject(name, value, comparator, comparator);
    }

    @Override
    public boolean containsObject(T name, Object value, Comparator<? super T> keyComparator,
            Comparator<? super T> valueComparator) {
        return contains(
                name, valueConverter.convertObject(checkNotNull(value, "value")), keyComparator, valueComparator);
    }

    @Override
    public int size() {
        return size;
    }

    @Override
    public boolean isEmpty() {
        return head == head.after;
    }

    @Override
    public Set<T> names() {
        final Set<T> names = new TreeSet<T>(keyComparator);

        HeaderEntry e = head.after;
        while (e != head) {
            names.add(e.name);
            e = e.after;
        }

        return names;
    }

    @Override
    public List<T> namesList() {
        final List<T> names = new ArrayList<T>(size());

        HeaderEntry e = head.after;
        while (e != head) {
            names.add(e.name);
            e = e.after;
        }

        return names;
    }

    @Override
    public Headers<T> add(T name, T value) {
        name = convertName(name);
        checkNotNull(value, "value");
        int h = hashCodeGenerator.generateHashCode(name);
        int i = index(h);
        add0(h, i, name, value);
        return this;
    }

    @Override
    public Headers<T> add(T name, Iterable<? extends T> values) {
        name = convertName(name);
        checkNotNull(values, "values");

        int h = hashCodeGenerator.generateHashCode(name);
        int i = index(h);
        for (T v : values) {
            if (v == null) {
                break;
            }
            add0(h, i, name, v);
        }
        return this;
    }

    @Override
    public Headers<T> add(T name, T... values) {
        name = convertName(name);
        checkNotNull(values, "values");

        int h = hashCodeGenerator.generateHashCode(name);
        int i = index(h);
        for (T v : values) {
            if (v == null) {
                break;
            }
            add0(h, i, name, v);
        }
        return this;
    }

    @Override
    public Headers<T> addObject(T name, Object value) {
        return add(name, valueConverter.convertObject(checkNotNull(value, "value")));
    }

    @Override
    public Headers<T> addObject(T name, Iterable<?> values) {
        name = convertName(name);
        checkNotNull(values, "values");

        int h = hashCodeGenerator.generateHashCode(name);
        int i = index(h);
        for (Object o : values) {
            if (o == null) {
                break;
            }
            T converted = valueConverter.convertObject(o);
            checkNotNull(converted, "converted");
            add0(h, i, name, converted);
        }
        return this;
    }

    @Override
    public Headers<T> addObject(T name, Object... values) {
        name = convertName(name);
        checkNotNull(values, "values");

        int h = hashCodeGenerator.generateHashCode(name);
        int i = index(h);
        for (Object o : values) {
            if (o == null) {
                break;
            }
            T converted = valueConverter.convertObject(o);
            checkNotNull(converted, "converted");
            add0(h, i, name, converted);
        }
        return this;
    }

    @Override
    public Headers<T> addInt(T name, int value) {
        return add(name, valueConverter.convertInt(value));
    }

    @Override
    public Headers<T> addLong(T name, long value) {
        return add(name, valueConverter.convertLong(value));
    }

    @Override
    public Headers<T> addDouble(T name, double value) {
        return add(name, valueConverter.convertDouble(value));
    }

    @Override
    public Headers<T> addTimeMillis(T name, long value) {
        return add(name, valueConverter.convertTimeMillis(value));
    }

    @Override
    public Headers<T> addChar(T name, char value) {
        return add(name, valueConverter.convertChar(value));
    }

    @Override
    public Headers<T> addBoolean(T name, boolean value) {
        return add(name, valueConverter.convertBoolean(value));
    }

    @Override
    public Headers<T> addFloat(T name, float value) {
        return add(name, valueConverter.convertFloat(value));
    }

    @Override
    public Headers<T> addByte(T name, byte value) {
        return add(name, valueConverter.convertByte(value));
    }

    @Override
    public Headers<T> addShort(T name, short value) {
        return add(name, valueConverter.convertShort(value));
    }

    @Override
    public Headers<T> add(Headers<T> headers) {
        checkNotNull(headers, "headers");

        add0(headers);
        return this;
    }

    @Override
    public Headers<T> set(T name, T value) {
        name = convertName(name);
        checkNotNull(value, "value");
        int h = hashCodeGenerator.generateHashCode(name);
        int i = index(h);
        remove0(h, i, name);
        add0(h, i, name, value);
        return this;
    }

    @Override
    public Headers<T> set(T name, Iterable<? extends T> values) {
        name = convertName(name);
        checkNotNull(values, "values");

        int h = hashCodeGenerator.generateHashCode(name);
        int i = index(h);
        remove0(h, i, name);
        for (T v : values) {
            if (v == null) {
                break;
            }
            add0(h, i, name, v);
        }

        return this;
    }

    @Override
    public Headers<T> set(T name, T... values) {
        name = convertName(name);
        checkNotNull(values, "values");

        int h = hashCodeGenerator.generateHashCode(name);
        int i = index(h);
        remove0(h, i, name);
        for (T v : values) {
            if (v == null) {
                break;
            }
            add0(h, i, name, v);
        }

        return this;
    }

    @Override
    public Headers<T> setObject(T name, Object value) {
        return set(name, valueConverter.convertObject(checkNotNull(value, "value")));
    }

    @Override
    public Headers<T> setObject(T name, Iterable<?> values) {
        name = convertName(name);
        checkNotNull(values, "values");

        int h = hashCodeGenerator.generateHashCode(name);
        int i = index(h);
        remove0(h, i, name);
        for (Object o : values) {
            if (o == null) {
                break;
            }
            T converted = valueConverter.convertObject(o);
            checkNotNull(converted, "converted");
            add0(h, i, name, converted);
        }

        return this;
    }

    @Override
    public Headers<T> setObject(T name, Object... values) {
        name = convertName(name);
        checkNotNull(values, "values");

        int h = hashCodeGenerator.generateHashCode(name);
        int i = index(h);
        remove0(h, i, name);
        for (Object o : values) {
            if (o == null) {
                break;
            }
            T converted = valueConverter.convertObject(o);
            checkNotNull(converted, "converted");
            add0(h, i, name, converted);
        }

        return this;
    }

    @Override
    public Headers<T> setInt(T name, int value) {
        return set(name, valueConverter.convertInt(value));
    }

    @Override
    public Headers<T> setLong(T name, long value) {
        return set(name, valueConverter.convertLong(value));
    }

    @Override
    public Headers<T> setDouble(T name, double value) {
        return set(name, valueConverter.convertDouble(value));
    }

    @Override
    public Headers<T> setTimeMillis(T name, long value) {
        return set(name, valueConverter.convertTimeMillis(value));
    }

    @Override
    public Headers<T> setFloat(T name, float value) {
        return set(name, valueConverter.convertFloat(value));
    }

    @Override
    public Headers<T> setChar(T name, char value) {
        return set(name, valueConverter.convertChar(value));
    }

    @Override
    public Headers<T> setBoolean(T name, boolean value) {
        return set(name, valueConverter.convertBoolean(value));
    }

    @Override
    public Headers<T> setByte(T name, byte value) {
        return set(name, valueConverter.convertByte(value));
    }

    @Override
    public Headers<T> setShort(T name, short value) {
        return set(name, valueConverter.convertShort(value));
    }

    @Override
    public Headers<T> set(Headers<T> headers) {
        checkNotNull(headers, "headers");

        clear();
        add0(headers);
        return this;
    }

    @Override
    public Headers<T> setAll(Headers<T> headers) {
        checkNotNull(headers, "headers");

        if (headers instanceof DefaultHeaders) {
            DefaultHeaders<T> m = (DefaultHeaders<T>) headers;
            HeaderEntry e = m.head.after;
            while (e != m.head) {
                set(e.name, e.value);
                e = e.after;
            }
        } else {
            try {
                headers.forEachEntry(setAllVisitor());
            } catch (Exception ex) {
                PlatformDependent.throwException(ex);
            }
        }

        return this;
    }

    @Override
    public boolean remove(T name) {
        checkNotNull(name, "name");
        int h = hashCodeGenerator.generateHashCode(name);
        int i = index(h);
        return remove0(h, i, name);
    }

    @Override
    public Headers<T> clear() {
        entries.clear();
        tailEntries.clear();
        head.before = head.after = head;
        size = 0;
        return this;
    }

    @Override
    public Iterator<Entry<T, T>> iterator() {
        return new KeyValueHeaderIterator();
    }

    @Override
    public Map.Entry<T, T> forEachEntry(EntryVisitor<T> visitor) throws Exception {
        HeaderEntry e = head.after;
        while (e != head) {
            if (!visitor.visit(e)) {
                return e;
            }
            e = e.after;
        }
        return null;
    }

    @Override
    public T forEachName(NameVisitor<T> visitor) throws Exception {
        HeaderEntry e = head.after;
        while (e != head) {
            if (!visitor.visit(e.name)) {
                return e.name;
            }
            e = e.after;
        }
        return null;
    }

    @Override
    public Boolean getBoolean(T name) {
        T v = get(name);
        if (v == null) {
            return null;
        }
        try {
            return valueConverter.convertToBoolean(v);
        } catch (Throwable ignored) {
            return null;
        }
    }

    @Override
    public boolean getBoolean(T name, boolean defaultValue) {
        Boolean v = getBoolean(name);
        return v == null ? defaultValue : v;
    }

    @Override
    public Byte getByte(T name) {
        T v = get(name);
        if (v == null) {
            return null;
        }
        try {
            return valueConverter.convertToByte(v);
        } catch (Throwable ignored) {
            return null;
        }
    }

    @Override
    public byte getByte(T name, byte defaultValue) {
        Byte v = getByte(name);
        return v == null ? defaultValue : v;
    }

    @Override
    public Character getChar(T name) {
        T v = get(name);
        if (v == null) {
            return null;
        }
        try {
            return valueConverter.convertToChar(v);
        } catch (Throwable ignored) {
            return null;
        }
    }

    @Override
    public char getChar(T name, char defaultValue) {
        Character v = getChar(name);
        return v == null ? defaultValue : v;
    }

    @Override
    public Short getShort(T name) {
        T v = get(name);
        if (v == null) {
            return null;
        }
        try {
            return valueConverter.convertToShort(v);
        } catch (Throwable ignored) {
            return null;
        }
    }

    @Override
    public short getInt(T name, short defaultValue) {
        Short v = getShort(name);
        return v == null ? defaultValue : v;
    }

    @Override
    public Integer getInt(T name) {
        T v = get(name);
        if (v == null) {
            return null;
        }
        try {
            return valueConverter.convertToInt(v);
        } catch (Throwable ignored) {
            return null;
        }
    }

    @Override
    public int getInt(T name, int defaultValue) {
        Integer v = getInt(name);
        return v == null ? defaultValue : v;
    }

    @Override
    public Long getLong(T name) {
        T v = get(name);
        if (v == null) {
            return null;
        }
        try {
            return valueConverter.convertToLong(v);
        } catch (Throwable ignored) {
            return null;
        }
    }

    @Override
    public long getLong(T name, long defaultValue) {
        Long v = getLong(name);
        return v == null ? defaultValue : v;
    }

    @Override
    public Float getFloat(T name) {
        T v = get(name);
        if (v == null) {
            return null;
        }
        try {
            return valueConverter.convertToFloat(v);
        } catch (Throwable ignored) {
            return null;
        }
    }

    @Override
    public float getFloat(T name, float defaultValue) {
        Float v = getFloat(name);
        return v == null ? defaultValue : v;
    }

    @Override
    public Double getDouble(T name) {
        T v = get(name);
        if (v == null) {
            return null;
        }
        try {
            return valueConverter.convertToDouble(v);
        } catch (Throwable ignored) {
            return null;
        }
    }

    @Override
    public double getDouble(T name, double defaultValue) {
        Double v = getDouble(name);
        return v == null ? defaultValue : v;
    }

    @Override
    public Long getTimeMillis(T name) {
        T v = get(name);
        if (v == null) {
            return null;
        }
        try {
            return valueConverter.convertToTimeMillis(v);
        } catch (Throwable ignored) {
            return null;
        }
    }

    @Override
    public long getTimeMillis(T name, long defaultValue) {
        Long v = getTimeMillis(name);
        return v == null ? defaultValue : v;
    }

    @Override
    public Boolean getBooleanAndRemove(T name) {
        T v = getAndRemove(name);
        if (v == null) {
            return null;
        }
        try {
            return valueConverter.convertToBoolean(v);
        } catch (Throwable ignored) {
            return null;
        }
    }

    @Override
    public boolean getBooleanAndRemove(T name, boolean defaultValue) {
        Boolean v = getBooleanAndRemove(name);
        return v == null ? defaultValue : v;
    }

    @Override
    public Byte getByteAndRemove(T name) {
        T v = getAndRemove(name);
        if (v == null) {
            return null;
        }
        try {
            return valueConverter.convertToByte(v);
        } catch (Throwable ignored) {
            return null;
        }
    }

    @Override
    public byte getByteAndRemove(T name, byte defaultValue) {
        Byte v = getByteAndRemove(name);
        return v == null ? defaultValue : v;
    }

    @Override
    public Character getCharAndRemove(T name) {
        T v = getAndRemove(name);
        if (v == null) {
            return null;
        }
        try {
            return valueConverter.convertToChar(v);
        } catch (Throwable ignored) {
            return null;
        }
    }

    @Override
    public char getCharAndRemove(T name, char defaultValue) {
        Character v = getCharAndRemove(name);
        return v == null ? defaultValue : v;
    }

    @Override
    public Short getShortAndRemove(T name) {
        T v = getAndRemove(name);
        if (v == null) {
            return null;
        }
        try {
            return valueConverter.convertToShort(v);
        } catch (Throwable ignored) {
            return null;
        }
    }

    @Override
    public short getShortAndRemove(T name, short defaultValue) {
        Short v = getShortAndRemove(name);
        return v == null ? defaultValue : v;
    }

    @Override
    public Integer getIntAndRemove(T name) {
        T v = getAndRemove(name);
        if (v == null) {
            return null;
        }
        try {
            return valueConverter.convertToInt(v);
        } catch (Throwable ignored) {
            return null;
        }
    }

    @Override
    public int getIntAndRemove(T name, int defaultValue) {
        Integer v = getIntAndRemove(name);
        return v == null ? defaultValue : v;
    }

    @Override
    public Long getLongAndRemove(T name) {
        T v = getAndRemove(name);
        if (v == null) {
            return null;
        }
        try {
            return valueConverter.convertToLong(v);
        } catch (Throwable ignored) {
            return null;
        }
    }

    @Override
    public long getLongAndRemove(T name, long defaultValue) {
        Long v = getLongAndRemove(name);
        return v == null ? defaultValue : v;
    }

    @Override
    public Float getFloatAndRemove(T name) {
        T v = getAndRemove(name);
        if (v == null) {
            return null;
        }
        try {
            return valueConverter.convertToFloat(v);
        } catch (Throwable ignored) {
            return null;
        }
    }

    @Override
    public float getFloatAndRemove(T name, float defaultValue) {
        Float v = getFloatAndRemove(name);
        return v == null ? defaultValue : v;
    }

    @Override
    public Double getDoubleAndRemove(T name) {
        T v = getAndRemove(name);
        if (v == null) {
            return null;
        }
        try {
            return valueConverter.convertToDouble(v);
        } catch (Throwable ignored) {
            return null;
        }
    }

    @Override
    public double getDoubleAndRemove(T name, double defaultValue) {
        Double v = getDoubleAndRemove(name);
        return v == null ? defaultValue : v;
    }

    @Override
    public Long getTimeMillisAndRemove(T name) {
        T v = getAndRemove(name);
        if (v == null) {
            return null;
        }
        try {
            return valueConverter.convertToTimeMillis(v);
        } catch (Throwable ignored) {
            return null;
        }
    }

    @Override
    public long getTimeMillisAndRemove(T name, long defaultValue) {
        Long v = getTimeMillisAndRemove(name);
        return v == null ? defaultValue : v;
    }

    @Override
    public boolean equals(Object o) {
        if (!(o instanceof DefaultHeaders)) {
            return false;
        }

        @SuppressWarnings("unchecked")
        DefaultHeaders<T> h2 = (DefaultHeaders<T>) o;
        // First, check that the set of names match. Don't use a TreeSet for comparison
        // because we want to force the keyComparator to be used for all comparisons
        List<T> namesList = namesList();
        List<T> otherNamesList = h2.namesList();
        if (!equals(namesList, otherNamesList, keyComparator)) {
            return false;
        }

        // Compare the values for each name. Don't use a TreeSet for comparison
        // because we want to force the valueComparator to be used for all comparisons
        Set<T> names = new TreeSet<T>(keyComparator);
        names.addAll(namesList);
        for (T name : names) {
            if (!equals(getAll(name), h2.getAll(name), valueComparator)) {
                return false;
            }
        }

        return true;
    }

    /**
     * Compare two lists using the {@code comparator} for all comparisons (not using the equals() operator)
     * @param lhs Left hand side
     * @param rhs Right hand side
     * @param comparator Comparator which will be used for all comparisons (equals() on objects will not be used)
     * @return True if {@code lhs} == {@code rhs} according to {@code comparator}. False otherwise.
     */
    private static <T> boolean equals(List<T> lhs, List<T> rhs, Comparator<? super T> comparator) {
        final int lhsSize = lhs.size();
        if (lhsSize != rhs.size()) {
            return false;
        }

        // Don't use a TreeSet to do the comparison.  We want to force the comparator
        // to be used instead of the object's equals()
        Collections.sort(lhs, comparator);
        Collections.sort(rhs, comparator);
        for (int i = 0; i < lhsSize; ++i) {
            if (comparator.compare(lhs.get(i), rhs.get(i)) != 0) {
                return false;
            }
        }
        return true;
    }

    @Override
    public int hashCode() {
        int result = 1;
        for (T name : names()) {
            result = HASH_CODE_PRIME * result + name.hashCode();
            List<T> values = getAll(name);
            Collections.sort(values, valueComparator);
            for (int i = 0; i < values.size(); ++i) {
                result = HASH_CODE_PRIME * result + hashCodeGenerator.generateHashCode(values.get(i));
            }
        }
        return result;
    }

    @Override
    public String toString() {
        StringBuilder builder = new StringBuilder(getClass().getSimpleName()).append('[');
        for (T name : names()) {
            List<T> values = getAll(name);
            Collections.sort(values, valueComparator);
            for (int i = 0; i < values.size(); ++i) {
                builder.append(name).append(": ").append(values.get(i)).append(", ");
            }
        }
        if (builder.length() > 2) { // remove the trailing ", "
            builder.setLength(builder.length() - 2);
        }
        return builder.append(']').toString();
    }

    protected ValueConverter<T> valueConverter() {
        return valueConverter;
    }

    private T convertName(T name) {
        return nameConverter.convertName(checkNotNull(name, "name"));
    }

    private int index(int hash) {
        return Math.abs(hash % bucketSize);
    }

    private void add0(Headers<T> headers) {
        if (headers.isEmpty()) {
            return;
        }

        if (headers instanceof DefaultHeaders) {
            DefaultHeaders<T> m = (DefaultHeaders<T>) headers;
            HeaderEntry e = m.head.after;
            while (e != m.head) {
                add(e.name, e.value);
                e = e.after;
            }
        } else {
            try {
                headers.forEachEntry(addAllVisitor());
            } catch (Exception ex) {
                PlatformDependent.throwException(ex);
            }
        }
    }

    private void add0(int h, int i, T name, T value) {
        // Update the per-bucket hash table linked list
        HeaderEntry newEntry = new HeaderEntry(h, name, value);
        HeaderEntry oldTail = tailEntries.get(i);
        if (oldTail == null) {
            entries.put(i, newEntry);
        } else {
            oldTail.next = newEntry;
        }
        tailEntries.put(i, newEntry);

        // Update the overall insertion order linked list
        newEntry.addBefore(head);
    }

    private boolean remove0(int h, int i, T name) {
        HeaderEntry e = entries.get(i);
        if (e == null) {
            return false;
        }

        boolean removed = false;
        for (;;) {
            if (e.hash == h && keyComparator.compare(e.name, name) == 0) {
                e.remove();
                HeaderEntry next = e.next;
                if (next != null) {
                    entries.put(i, next);
                    e = next;
                } else {
                    entries.remove(i);
                    tailEntries.remove(i);
                    return true;
                }
                removed = true;
            } else {
                break;
            }
        }

        for (;;) {
            HeaderEntry next = e.next;
            if (next == null) {
                break;
            }
            if (next.hash == h && keyComparator.compare(next.name, name) == 0) {
                e.next = next.next;
                if (e.next == null) {
                    tailEntries.put(i, e);
                }
                next.remove();
                removed = true;
            } else {
                e = next;
            }
        }

        return removed;
    }

    private EntryVisitor<T> setAllVisitor() {
        return new EntryVisitor<T>() {
            @Override
            public boolean visit(Entry<T, T> entry) {
                set(entry.getKey(), entry.getValue());
                return true;
            }
        };
    }

    private EntryVisitor<T> addAllVisitor() {
        return new EntryVisitor<T>() {
            @Override
            public boolean visit(Entry<T, T> entry) {
                add(entry.getKey(), entry.getValue());
                return true;
            }
        };
    }

    private final class HeaderEntry implements Map.Entry<T, T> {
        final int hash;
        final T name;
        T value;
        /**
         * In bucket linked list
         */
        HeaderEntry next;
        /**
         * Overall insertion order linked list
         */
        HeaderEntry before, after;

        HeaderEntry(int hash, T name, T value) {
            this.hash = hash;
            this.name = name;
            this.value = value;
        }

        HeaderEntry() {
            hash = -1;
            name = null;
            value = null;
        }

        void remove() {
            before.after = after;
            after.before = before;
            --size;
        }

        void addBefore(HeaderEntry e) {
            after = e;
            before = e.before;
            before.after = this;
            after.before = this;
            ++size;
        }

        @Override
        public T getKey() {
            return name;
        }

        @Override
        public T getValue() {
            return value;
        }

        @Override
        public T setValue(T value) {
            checkNotNull(value, "value");
            T oldValue = this.value;
            this.value = value;
            return oldValue;
        }

        @Override
        public String toString() {
            return new StringBuilder()
                .append(name)
                .append('=')
                .append(value)
                .toString();
        }
    }

    protected final class KeyValueHeaderIterator implements Iterator<Entry<T, T>> {

        private HeaderEntry current = head;

        @Override
        public boolean hasNext() {
            return current.after != head;
        }

        @Override
        public Entry<T, T> next() {
            current = current.after;

            if (current == head) {
                throw new NoSuchElementException();
            }

            return current;
        }

        @Override
        public void remove() {
            throw new UnsupportedOperationException();
        }
    }

    /**
     * This DateFormat decodes 3 formats of {@link java.util.Date}, but only encodes the one, the first:
     * <ul>
     * <li>Sun, 06 Nov 1994 08:49:37 GMT: standard specification, the only one with valid generation</li>
     * <li>Sun, 06 Nov 1994 08:49:37 GMT: obsolete specification</li>
     * <li>Sun Nov 6 08:49:37 1994: obsolete specification</li>
     * </ul>
     */
    static final class HeaderDateFormat {
        private static final ParsePosition parsePos = new ParsePosition(0);
        private static final FastThreadLocal<HeaderDateFormat> dateFormatThreadLocal =
                new FastThreadLocal<HeaderDateFormat>() {
            @Override
            protected HeaderDateFormat initialValue() {
                return new HeaderDateFormat();
            }
        };

        static HeaderDateFormat get() {
            return dateFormatThreadLocal.get();
        }

        /**
         * Standard date format:
         *
         * <pre>
         * Sun, 06 Nov 1994 08:49:37 GMT -> E, d MMM yyyy HH:mm:ss z
         * </pre>
         */
        private final DateFormat dateFormat1 = new SimpleDateFormat("E, dd MMM yyyy HH:mm:ss z", Locale.ENGLISH);
        /**
         * First obsolete format:
         *
         * <pre>
         * Sunday, 06-Nov-94 08:49:37 GMT -> E, d-MMM-y HH:mm:ss z
         * </pre>
         */
        private final DateFormat dateFormat2 = new SimpleDateFormat("E, dd-MMM-yy HH:mm:ss z", Locale.ENGLISH);
        /**
         * Second obsolete format
         *
         * <pre>
         * Sun Nov 6 08:49:37 1994 -> EEE, MMM d HH:mm:ss yyyy
         * </pre>
         */
        private final DateFormat dateFormat3 = new SimpleDateFormat("E MMM d HH:mm:ss yyyy", Locale.ENGLISH);

        private HeaderDateFormat() {
            TimeZone tz = TimeZone.getTimeZone("GMT");
            dateFormat1.setTimeZone(tz);
            dateFormat2.setTimeZone(tz);
            dateFormat3.setTimeZone(tz);
        }

        long parse(String text) throws ParseException {
            Date date = dateFormat1.parse(text, parsePos);
            if (date == null) {
                date = dateFormat2.parse(text, parsePos);
            }
            if (date == null) {
                date = dateFormat3.parse(text, parsePos);
            }
            if (date == null) {
                throw new ParseException(text, 0);
            }
            return date.getTime();
        }

        long parse(String text, long defaultValue) {
            Date date = dateFormat1.parse(text, parsePos);
            if (date == null) {
                date = dateFormat2.parse(text, parsePos);
            }
            if (date == null) {
                date = dateFormat3.parse(text, parsePos);
            }
            if (date == null) {
                return defaultValue;
            }
            return date.getTime();
        }
    }
}


File: codec/src/main/java/io/netty/handler/codec/DefaultTextHeaders.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package io.netty.handler.codec;

import static io.netty.util.AsciiString.CHARSEQUENCE_CASE_INSENSITIVE_ORDER;
import static io.netty.util.AsciiString.CHARSEQUENCE_CASE_SENSITIVE_ORDER;
import static io.netty.util.internal.StringUtil.COMMA;
import io.netty.util.AsciiString;
import io.netty.util.internal.PlatformDependent;
import io.netty.util.internal.StringUtil;

import java.text.ParseException;
import java.util.Comparator;
import java.util.Iterator;

public class DefaultTextHeaders extends DefaultConvertibleHeaders<CharSequence, String> implements TextHeaders {
    private static final HashCodeGenerator<CharSequence> CHARSEQUECE_CASE_INSENSITIVE_HASH_CODE_GENERATOR =
            new HashCodeGenerator<CharSequence>() {
        @Override
        public int generateHashCode(CharSequence name) {
            return AsciiString.caseInsensitiveHashCode(name);
        }
    };

    private static final HashCodeGenerator<CharSequence> CHARSEQUECE_CASE_SENSITIVE_HASH_CODE_GENERATOR =
            new JavaHashCodeGenerator<CharSequence>();

    public static class DefaultTextValueTypeConverter implements ValueConverter<CharSequence> {
        @Override
        public CharSequence convertObject(Object value) {
            if (value instanceof CharSequence) {
                return (CharSequence) value;
            }
            return value.toString();
        }

        @Override
        public CharSequence convertInt(int value) {
            return String.valueOf(value);
        }

        @Override
        public CharSequence convertLong(long value) {
            return String.valueOf(value);
        }

        @Override
        public CharSequence convertDouble(double value) {
            return String.valueOf(value);
        }

        @Override
        public CharSequence convertChar(char value) {
            return String.valueOf(value);
        }

        @Override
        public CharSequence convertBoolean(boolean value) {
            return String.valueOf(value);
        }

        @Override
        public CharSequence convertFloat(float value) {
            return String.valueOf(value);
        }

        @Override
        public boolean convertToBoolean(CharSequence value) {
            return Boolean.parseBoolean(value.toString());
        }

        @Override
        public CharSequence convertByte(byte value) {
            return String.valueOf(value);
        }

        @Override
        public byte convertToByte(CharSequence value) {
            return Byte.valueOf(value.toString());
        }

        @Override
        public char convertToChar(CharSequence value) {
            return value.charAt(0);
        }

        @Override
        public CharSequence convertShort(short value) {
            return String.valueOf(value);
        }

        @Override
        public short convertToShort(CharSequence value) {
            return Short.valueOf(value.toString());
        }

        @Override
        public int convertToInt(CharSequence value) {
            return Integer.parseInt(value.toString());
        }

        @Override
        public long convertToLong(CharSequence value) {
            return Long.parseLong(value.toString());
        }

        @Override
        public AsciiString convertTimeMillis(long value) {
            return new AsciiString(String.valueOf(value));
        }

        @Override
        public long convertToTimeMillis(CharSequence value) {
            try {
                return HeaderDateFormat.get().parse(value.toString());
            } catch (ParseException e) {
                PlatformDependent.throwException(e);
            }
            return 0;
        }

        @Override
        public float convertToFloat(CharSequence value) {
            return Float.valueOf(value.toString());
        }

        @Override
        public double convertToDouble(CharSequence value) {
            return Double.valueOf(value.toString());
        }
    }

    private static final ValueConverter<CharSequence> CHARSEQUENCE_FROM_OBJECT_CONVERTER =
            new DefaultTextValueTypeConverter();
    private static final TypeConverter<CharSequence, String> CHARSEQUENCE_TO_STRING_CONVERTER =
            new TypeConverter<CharSequence, String>() {
        @Override
        public String toConvertedType(CharSequence value) {
            return value.toString();
        }

        @Override
        public CharSequence toUnconvertedType(String value) {
            return value;
        }
    };

    private static final NameConverter<CharSequence> CHARSEQUENCE_IDENTITY_CONVERTER =
            new IdentityNameConverter<CharSequence>();
    /**
     * An estimate of the size of a header value.
     */
    private static final int DEFAULT_VALUE_SIZE = 10;

    private final ValuesComposer valuesComposer;

    public DefaultTextHeaders() {
        this(true);
    }

    public DefaultTextHeaders(boolean ignoreCase) {
        this(ignoreCase, CHARSEQUENCE_FROM_OBJECT_CONVERTER, CHARSEQUENCE_IDENTITY_CONVERTER, false);
    }

    public DefaultTextHeaders(boolean ignoreCase, boolean singleHeaderFields) {
        this(ignoreCase, CHARSEQUENCE_FROM_OBJECT_CONVERTER, CHARSEQUENCE_IDENTITY_CONVERTER, singleHeaderFields);
    }

    protected DefaultTextHeaders(boolean ignoreCase, Headers.ValueConverter<CharSequence> valueConverter,
            NameConverter<CharSequence> nameConverter) {
        this(ignoreCase, valueConverter, nameConverter, false);
    }

    public DefaultTextHeaders(boolean ignoreCase, ValueConverter<CharSequence> valueConverter,
                              NameConverter<CharSequence> nameConverter, boolean singleHeaderFields) {
        super(comparator(ignoreCase), comparator(ignoreCase),
                ignoreCase ? CHARSEQUECE_CASE_INSENSITIVE_HASH_CODE_GENERATOR
                        : CHARSEQUECE_CASE_SENSITIVE_HASH_CODE_GENERATOR, valueConverter,
                CHARSEQUENCE_TO_STRING_CONVERTER, nameConverter);
        valuesComposer = singleHeaderFields ? new SingleHeaderValuesComposer() : new MultipleFieldsValueComposer();
    }

    @Override
    public boolean contains(CharSequence name, CharSequence value, boolean ignoreCase) {
        return contains(name, value, comparator(ignoreCase));
    }

    @Override
    public boolean containsObject(CharSequence name, Object value, boolean ignoreCase) {
        return containsObject(name, value, comparator(ignoreCase));
    }

    @Override
    public TextHeaders add(CharSequence name, CharSequence value) {
        return valuesComposer.add(name, value);
    }

    @Override
    public TextHeaders add(CharSequence name, Iterable<? extends CharSequence> values) {
        return valuesComposer.add(name, values);
    }

    @Override
    public TextHeaders add(CharSequence name, CharSequence... values) {
        return valuesComposer.add(name, values);
    }

    @Override
    public TextHeaders addObject(CharSequence name, Object value) {
        return valuesComposer.addObject(name, value);
    }

    @Override
    public TextHeaders addObject(CharSequence name, Iterable<?> values) {
        return valuesComposer.addObject(name, values);
    }

    @Override
    public TextHeaders addObject(CharSequence name, Object... values) {
        return valuesComposer.addObject(name, values);
    }

    @Override
    public TextHeaders addBoolean(CharSequence name, boolean value) {
        super.addBoolean(name, value);
        return this;
    }

    @Override
    public TextHeaders addChar(CharSequence name, char value) {
        super.addChar(name, value);
        return this;
    }

    @Override
    public TextHeaders addByte(CharSequence name, byte value) {
        super.addByte(name, value);
        return this;
    }

    @Override
    public TextHeaders addShort(CharSequence name, short value) {
        super.addShort(name, value);
        return this;
    }

    @Override
    public TextHeaders addInt(CharSequence name, int value) {
        super.addInt(name, value);
        return this;
    }

    @Override
    public TextHeaders addLong(CharSequence name, long value) {
        super.addLong(name, value);
        return this;
    }

    @Override
    public TextHeaders addFloat(CharSequence name, float value) {
        super.addFloat(name, value);
        return this;
    }

    @Override
    public TextHeaders addDouble(CharSequence name, double value) {
        super.addDouble(name, value);
        return this;
    }

    @Override
    public TextHeaders addTimeMillis(CharSequence name, long value) {
        super.addTimeMillis(name, value);
        return this;
    }

    @Override
    public TextHeaders add(TextHeaders headers) {
        super.add(headers);
        return this;
    }

    @Override
    public TextHeaders set(CharSequence name, CharSequence value) {
        super.set(name, value);
        return this;
    }

    @Override
    public TextHeaders set(CharSequence name, Iterable<? extends CharSequence> values) {
        return valuesComposer.set(name, values);
    }

    @Override
    public TextHeaders set(CharSequence name, CharSequence... values) {
        return valuesComposer.set(name, values);
    }

    @Override
    public TextHeaders setObject(CharSequence name, Object value) {
        super.setObject(name, value);
        return this;
    }

    @Override
    public TextHeaders setObject(CharSequence name, Iterable<?> values) {
        return valuesComposer.setObject(name, values);
    }

    @Override
    public TextHeaders setObject(CharSequence name, Object... values) {
        return valuesComposer.setObject(name, values);
    }

    @Override
    public TextHeaders setBoolean(CharSequence name, boolean value) {
        super.setBoolean(name, value);
        return this;
    }

    @Override
    public TextHeaders setChar(CharSequence name, char value) {
        super.setChar(name, value);
        return this;
    }

    @Override
    public TextHeaders setByte(CharSequence name, byte value) {
        super.setByte(name, value);
        return this;
    }

    @Override
    public TextHeaders setShort(CharSequence name, short value) {
        super.setShort(name, value);
        return this;
    }

    @Override
    public TextHeaders setInt(CharSequence name, int value) {
        super.setInt(name, value);
        return this;
    }

    @Override
    public TextHeaders setLong(CharSequence name, long value) {
        super.setLong(name, value);
        return this;
    }

    @Override
    public TextHeaders setFloat(CharSequence name, float value) {
        super.setFloat(name, value);
        return this;
    }

    @Override
    public TextHeaders setDouble(CharSequence name, double value) {
        super.setDouble(name, value);
        return this;
    }

    @Override
    public TextHeaders setTimeMillis(CharSequence name, long value) {
        super.setTimeMillis(name, value);
        return this;
    }

    @Override
    public TextHeaders set(TextHeaders headers) {
        super.set(headers);
        return this;
    }

    @Override
    public TextHeaders setAll(TextHeaders headers) {
        super.setAll(headers);
        return this;
    }

    @Override
    public TextHeaders clear() {
        super.clear();
        return this;
    }

    private static Comparator<CharSequence> comparator(boolean ignoreCase) {
        return ignoreCase ? CHARSEQUENCE_CASE_INSENSITIVE_ORDER : CHARSEQUENCE_CASE_SENSITIVE_ORDER;
    }

    /*
     * This interface enables different implementations for adding/setting header values.
     * Concrete implementations can control how values are added, for example to add all
     * values for a header as a comma separated string instead of adding them as multiple
     * headers with a single value.
     */
    private interface ValuesComposer {
        TextHeaders add(CharSequence name, CharSequence value);
        TextHeaders add(CharSequence name, CharSequence... values);
        TextHeaders add(CharSequence name, Iterable<? extends CharSequence> values);

        TextHeaders addObject(CharSequence name, Iterable<?> values);
        TextHeaders addObject(CharSequence name, Object... values);

        TextHeaders set(CharSequence name, CharSequence... values);
        TextHeaders set(CharSequence name, Iterable<? extends CharSequence> values);

        TextHeaders setObject(CharSequence name, Object... values);
        TextHeaders setObject(CharSequence name, Iterable<?> values);
    }

    /*
     * Will add multiple values for the same header as multiple separate headers.
     */
    private final class MultipleFieldsValueComposer implements ValuesComposer {

        @Override
        public TextHeaders add(CharSequence name, CharSequence value) {
            DefaultTextHeaders.super.add(name, value);
            return DefaultTextHeaders.this;
        }

        @Override
        public TextHeaders add(CharSequence name, CharSequence... values) {
            DefaultTextHeaders.super.add(name, values);
            return DefaultTextHeaders.this;
        }

        @Override
        public TextHeaders add(CharSequence name, Iterable<? extends CharSequence> values) {
            DefaultTextHeaders.super.add(name, values);
            return DefaultTextHeaders.this;
        }

        @Override
        public TextHeaders addObject(CharSequence name, Iterable<?> values) {
            DefaultTextHeaders.super.addObject(name, values);
            return DefaultTextHeaders.this;
        }

        @Override
        public TextHeaders addObject(CharSequence name, Object... values) {
            DefaultTextHeaders.super.addObject(name, values);
            return DefaultTextHeaders.this;
        }

        @Override
        public TextHeaders set(CharSequence name, CharSequence... values) {
            DefaultTextHeaders.super.set(name, values);
            return DefaultTextHeaders.this;
        }

        @Override
        public TextHeaders set(CharSequence name, Iterable<? extends CharSequence> values) {
            DefaultTextHeaders.super.set(name, values);
            return DefaultTextHeaders.this;
        }

        @Override
        public TextHeaders setObject(CharSequence name, Object... values) {
            DefaultTextHeaders.super.setObject(name, values);
            return DefaultTextHeaders.this;
        }

        @Override
        public TextHeaders setObject(CharSequence name, Iterable<?> values) {
            DefaultTextHeaders.super.setObject(name, values);
            return DefaultTextHeaders.this;
        }
    }

    /**
     * Will add multiple values for the same header as single header with a comma separated list of values.
     *
     * Please refer to section <a href="https://tools.ietf.org/html/rfc7230#section-3.2.2">3.2.2 Field Order</a>
     * of RFC-7230 for details.
     */
    private final class SingleHeaderValuesComposer implements ValuesComposer {

        private final ValueConverter<CharSequence> valueConverter = valueConverter();
        private CsvValueEscaper<Object> objectEscaper;
        private CsvValueEscaper<CharSequence> charSequenceEscaper;

        private CsvValueEscaper<Object> objectEscaper() {
            if (objectEscaper == null) {
                objectEscaper = new CsvValueEscaper<Object>() {
                    @Override
                    public CharSequence escape(Object value) {
                        return StringUtil.escapeCsv(valueConverter.convertObject(value));
                    }
                };
            }
            return objectEscaper;
        }

        private CsvValueEscaper<CharSequence> charSequenceEscaper() {
            if (charSequenceEscaper == null) {
                charSequenceEscaper = new CsvValueEscaper<CharSequence>() {
                    @Override
                    public CharSequence escape(CharSequence value) {
                        return StringUtil.escapeCsv(value);
                    }
                };
            }
            return charSequenceEscaper;
        }

        @Override
        public TextHeaders add(CharSequence name, CharSequence value) {
            return addEscapedValue(name, StringUtil.escapeCsv(value));
        }

        @Override
        public TextHeaders add(CharSequence name, CharSequence... values) {
            return addEscapedValue(name, commaSeparate(charSequenceEscaper(), values));
        }

        @Override
        public TextHeaders add(CharSequence name, Iterable<? extends CharSequence> values) {
            return addEscapedValue(name, commaSeparate(charSequenceEscaper(), values));
        }

        @Override
        public TextHeaders addObject(CharSequence name, Iterable<?> values) {
            return addEscapedValue(name, commaSeparate(objectEscaper(), values));
        }

        @Override
        public TextHeaders addObject(CharSequence name, Object... values) {
            return addEscapedValue(name, commaSeparate(objectEscaper(), values));
        }

        @Override
        public TextHeaders set(CharSequence name, CharSequence... values) {
            DefaultTextHeaders.super.set(name, commaSeparate(charSequenceEscaper(), values));
            return DefaultTextHeaders.this;
        }

        @Override
        public TextHeaders set(CharSequence name, Iterable<? extends CharSequence> values) {
            DefaultTextHeaders.super.set(name, commaSeparate(charSequenceEscaper(), values));
            return DefaultTextHeaders.this;
        }

        @Override
        public TextHeaders setObject(CharSequence name, Object... values) {
            DefaultTextHeaders.super.set(name, commaSeparate(objectEscaper(), values));
            return DefaultTextHeaders.this;
        }

        @Override
        public TextHeaders setObject(CharSequence name, Iterable<?> values) {
            DefaultTextHeaders.super.set(name, commaSeparate(objectEscaper(), values));
            return DefaultTextHeaders.this;
        }

        private TextHeaders addEscapedValue(CharSequence name, CharSequence escapedValue) {
            CharSequence currentValue = DefaultTextHeaders.super.get(name);
            if (currentValue == null) {
                DefaultTextHeaders.super.add(name, escapedValue);
            } else {
                DefaultTextHeaders.super.set(name, commaSeparateEscapedValues(currentValue, escapedValue));
            }
            return DefaultTextHeaders.this;
        }

        private <T> CharSequence commaSeparate(CsvValueEscaper<T> escaper, T... values) {
            StringBuilder sb = new StringBuilder(values.length * DEFAULT_VALUE_SIZE);
            if (values.length > 0) {
                int end = values.length - 1;
                for (int i = 0; i < end; i++) {
                    sb.append(escaper.escape(values[i])).append(COMMA);
                }
                sb.append(escaper.escape(values[end]));
            }
            return sb;
        }

        private <T> CharSequence commaSeparate(CsvValueEscaper<T> escaper, Iterable<? extends T> values) {
            StringBuilder sb = new StringBuilder();
            Iterator<? extends T> iterator = values.iterator();
            if (iterator.hasNext()) {
                T next = iterator.next();
                while (iterator.hasNext()) {
                    sb.append(escaper.escape(next)).append(COMMA);
                    next = iterator.next();
                }
                sb.append(escaper.escape(next));
            }
            return sb;
        }

        private CharSequence commaSeparateEscapedValues(CharSequence currentValue, CharSequence value) {
            return new StringBuilder(currentValue.length() + 1 + value.length())
                    .append(currentValue)
                    .append(COMMA)
                    .append(value);
        }
    }

    /**
     * Escapes comma separated values (CSV).
     *
     * @param <T> The type that a concrete implementation handles
     */
    private interface CsvValueEscaper<T> {
        /**
         * Appends the value to the specified {@link StringBuilder}, escaping if necessary.
         *
         * @param value the value to be appended, escaped if necessary
         */
        CharSequence escape(T value);
    }
}


File: codec/src/main/java/io/netty/handler/codec/EmptyConvertibleHeaders.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License, version 2.0 (the
 * "License"); you may not use this file except in compliance with the License. You may obtain a
 * copy of the License at:
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */
package io.netty.handler.codec;

import java.util.Collections;
import java.util.Comparator;
import java.util.Iterator;
import java.util.List;
import java.util.Map.Entry;
import java.util.Set;

public class EmptyConvertibleHeaders<UnconvertedType, ConvertedType> extends
        EmptyHeaders<UnconvertedType> implements ConvertibleHeaders<UnconvertedType, ConvertedType> {

    @Override
    public ConvertedType getAndConvert(UnconvertedType name) {
        return null;
    }

    @Override
    public ConvertedType getAndConvert(UnconvertedType name, ConvertedType defaultValue) {
        return defaultValue;
    }

    @Override
    public ConvertedType getAndRemoveAndConvert(UnconvertedType name) {
        return null;
    }

    @Override
    public ConvertedType getAndRemoveAndConvert(UnconvertedType name, ConvertedType defaultValue) {
        return defaultValue;
    }

    @Override
    public List<ConvertedType> getAllAndConvert(UnconvertedType name) {
        return Collections.emptyList();
    }

    @Override
    public List<ConvertedType> getAllAndRemoveAndConvert(UnconvertedType name) {
        return Collections.emptyList();
    }

    @Override
    public List<Entry<ConvertedType, ConvertedType>> entriesConverted() {
        return Collections.emptyList();
    }

    @Override
    public Iterator<Entry<ConvertedType, ConvertedType>> iteratorConverted() {
        return entriesConverted().iterator();
    }

    @Override
    public Set<ConvertedType> namesAndConvert(Comparator<ConvertedType> comparator) {
        return Collections.emptySet();
    }
}


File: codec/src/main/java/io/netty/handler/codec/EmptyHeaders.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License, version 2.0 (the
 * "License"); you may not use this file except in compliance with the License. You may obtain a
 * copy of the License at:
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */
package io.netty.handler.codec;

import java.util.Collections;
import java.util.Comparator;
import java.util.Iterator;
import java.util.List;
import java.util.Map.Entry;
import java.util.Set;

public class EmptyHeaders<T> implements Headers<T> {
    @Override
    public T get(T name) {
        return null;
    }

    @Override
    public T get(T name, T defaultValue) {
        return null;
    }

    @Override
    public T getAndRemove(T name) {
        return null;
    }

    @Override
    public T getAndRemove(T name, T defaultValue) {
        return null;
    }

    @Override
    public List<T> getAll(T name) {
        return Collections.emptyList();
    }

    @Override
    public List<T> getAllAndRemove(T name) {
        return Collections.emptyList();
    }

    @Override
    public Boolean getBoolean(T name) {
        return null;
    }

    @Override
    public boolean getBoolean(T name, boolean defaultValue) {
        return defaultValue;
    }

    @Override
    public Byte getByte(T name) {
        return null;
    }

    @Override
    public byte getByte(T name, byte defaultValue) {
        return defaultValue;
    }

    @Override
    public Character getChar(T name) {
        return null;
    }

    @Override
    public char getChar(T name, char defaultValue) {
        return defaultValue;
    }

    @Override
    public Short getShort(T name) {
        return null;
    }

    @Override
    public short getInt(T name, short defaultValue) {
        return defaultValue;
    }

    @Override
    public Integer getInt(T name) {
        return null;
    }

    @Override
    public int getInt(T name, int defaultValue) {
        return defaultValue;
    }

    @Override
    public Long getLong(T name) {
        return null;
    }

    @Override
    public long getLong(T name, long defaultValue) {
        return defaultValue;
    }

    @Override
    public Float getFloat(T name) {
        return null;
    }

    @Override
    public float getFloat(T name, float defaultValue) {
        return defaultValue;
    }

    @Override
    public Double getDouble(T name) {
        return null;
    }

    @Override
    public double getDouble(T name, double defaultValue) {
        return defaultValue;
    }

    @Override
    public Long getTimeMillis(T name) {
        return null;
    }

    @Override
    public long getTimeMillis(T name, long defaultValue) {
        return defaultValue;
    }

    @Override
    public Boolean getBooleanAndRemove(T name) {
        return null;
    }

    @Override
    public boolean getBooleanAndRemove(T name, boolean defaultValue) {
        return defaultValue;
    }

    @Override
    public Byte getByteAndRemove(T name) {
        return null;
    }

    @Override
    public byte getByteAndRemove(T name, byte defaultValue) {
        return defaultValue;
    }

    @Override
    public Character getCharAndRemove(T name) {
        return null;
    }

    @Override
    public char getCharAndRemove(T name, char defaultValue) {
        return defaultValue;
    }

    @Override
    public Short getShortAndRemove(T name) {
        return null;
    }

    @Override
    public short getShortAndRemove(T name, short defaultValue) {
        return defaultValue;
    }

    @Override
    public Integer getIntAndRemove(T name) {
        return null;
    }

    @Override
    public int getIntAndRemove(T name, int defaultValue) {
        return defaultValue;
    }

    @Override
    public Long getLongAndRemove(T name) {
        return null;
    }

    @Override
    public long getLongAndRemove(T name, long defaultValue) {
        return defaultValue;
    }

    @Override
    public Float getFloatAndRemove(T name) {
        return null;
    }

    @Override
    public float getFloatAndRemove(T name, float defaultValue) {
        return defaultValue;
    }

    @Override
    public Double getDoubleAndRemove(T name) {
        return null;
    }

    @Override
    public double getDoubleAndRemove(T name, double defaultValue) {
        return defaultValue;
    }

    @Override
    public Long getTimeMillisAndRemove(T name) {
        return null;
    }

    @Override
    public long getTimeMillisAndRemove(T name, long defaultValue) {
        return defaultValue;
    }

    @Override
    public List<Entry<T, T>> entries() {
        return Collections.emptyList();
    }

    @Override
    public boolean contains(T name) {
        return false;
    }

    @Override
    public boolean contains(T name, T value) {
        return false;
    }

    @Override
    public boolean containsObject(T name, Object value) {
        return false;
    }

    @Override
    public boolean containsBoolean(T name, boolean value) {
        return false;
    }

    @Override
    public boolean containsByte(T name, byte value) {
        return false;
    }

    @Override
    public boolean containsChar(T name, char value) {
        return false;
    }

    @Override
    public boolean containsShort(T name, short value) {
        return false;
    }

    @Override
    public boolean containsInt(T name, int value) {
        return false;
    }

    @Override
    public boolean containsLong(T name, long value) {
        return false;
    }

    @Override
    public boolean containsFloat(T name, float value) {
        return false;
    }

    @Override
    public boolean containsDouble(T name, double value) {
        return false;
    }

    @Override
    public boolean containsTimeMillis(T name, long value) {
        return false;
    }

    @Override
    public boolean contains(T name, T value, Comparator<? super T> comparator) {
        return false;
    }

    @Override
    public boolean contains(T name, T value,
            Comparator<? super T> keyComparator, Comparator<? super T> valueComparator) {
        return false;
    }

    @Override
    public boolean containsObject(T name, Object value, Comparator<? super T> comparator) {
        return false;
    }

    @Override
    public boolean containsObject(T name, Object value, Comparator<? super T> keyComparator,
            Comparator<? super T> valueComparator) {
        return false;
    }

    @Override
    public int size() {
        return 0;
    }

    @Override
    public boolean isEmpty() {
        return true;
    }

    @Override
    public Set<T> names() {
        return Collections.emptySet();
    }

    @Override
    public List<T> namesList() {
        return Collections.emptyList();
    }

    @Override
    public Headers<T> add(T name, T value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> add(T name, Iterable<? extends T> values) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> add(T name, T... values) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> addObject(T name, Object value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> addObject(T name, Iterable<?> values) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> addObject(T name, Object... values) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> addBoolean(T name, boolean value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> addByte(T name, byte value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> addChar(T name, char value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> addShort(T name, short value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> addInt(T name, int value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> addLong(T name, long value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> addFloat(T name, float value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> addDouble(T name, double value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> addTimeMillis(T name, long value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> add(Headers<T> headers) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> set(T name, T value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> set(T name, Iterable<? extends T> values) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> set(T name, T... values) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> setObject(T name, Object value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> setObject(T name, Iterable<?> values) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> setObject(T name, Object... values) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> setBoolean(T name, boolean value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> setByte(T name, byte value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> setChar(T name, char value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> setShort(T name, short value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> setInt(T name, int value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> setLong(T name, long value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> setFloat(T name, float value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> setDouble(T name, double value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> setTimeMillis(T name, long value) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> set(Headers<T> headers) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public Headers<T> setAll(Headers<T> headers) {
        throw new UnsupportedOperationException("read only");
    }

    @Override
    public boolean remove(T name) {
        return false;
    }

    @Override
    public Headers<T> clear() {
        return this;
    }

    @Override
    public Iterator<Entry<T, T>> iterator() {
        return entries().iterator();
    }

    @Override
    public Entry<T, T> forEachEntry(Headers.EntryVisitor<T> visitor) throws Exception {
        return null;
    }

    @Override
    public T forEachName(Headers.NameVisitor<T> visitor) throws Exception {
        return null;
    }

    @Override
    public boolean equals(Object o) {
        if (!(o instanceof Headers)) {
            return false;
        }

        Headers<?> rhs = (Headers<?>) o;
        return isEmpty() && rhs.isEmpty();
    }

    @Override
    public int hashCode() {
        return 1;
    }

    @Override
    public String toString() {
        return new StringBuilder(getClass().getSimpleName()).append('[').append(']').toString();
    }
}


File: codec/src/main/java/io/netty/handler/codec/EmptyTextHeaders.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package io.netty.handler.codec;

public class EmptyTextHeaders extends EmptyConvertibleHeaders<CharSequence, String> implements TextHeaders {
    protected EmptyTextHeaders() {
    }

    @Override
    public boolean contains(CharSequence name, CharSequence value, boolean ignoreCase) {
        return false;
    }

    @Override
    public boolean containsObject(CharSequence name, Object value, boolean ignoreCase) {
        return false;
    }

    @Override
    public TextHeaders add(CharSequence name, CharSequence value) {
        super.add(name, value);
        return this;
    }

    @Override
    public TextHeaders add(CharSequence name, Iterable<? extends CharSequence> values) {
        super.add(name, values);
        return this;
    }

    @Override
    public TextHeaders add(CharSequence name, CharSequence... values) {
        super.add(name, values);
        return this;
    }

    @Override
    public TextHeaders addObject(CharSequence name, Object value) {
        super.addObject(name, value);
        return this;
    }

    @Override
    public TextHeaders addObject(CharSequence name, Iterable<?> values) {
        super.addObject(name, values);
        return this;
    }

    @Override
    public TextHeaders addObject(CharSequence name, Object... values) {
        super.addObject(name, values);
        return this;
    }

    @Override
    public TextHeaders addBoolean(CharSequence name, boolean value) {
        super.addBoolean(name, value);
        return this;
    }

    @Override
    public TextHeaders addChar(CharSequence name, char value) {
        super.addChar(name, value);
        return this;
    }

    @Override
    public TextHeaders addByte(CharSequence name, byte value) {
        super.addByte(name, value);
        return this;
    }

    @Override
    public TextHeaders addShort(CharSequence name, short value) {
        super.addShort(name, value);
        return this;
    }

    @Override
    public TextHeaders addInt(CharSequence name, int value) {
        super.addInt(name, value);
        return this;
    }

    @Override
    public TextHeaders addLong(CharSequence name, long value) {
        super.addLong(name, value);
        return this;
    }

    @Override
    public TextHeaders addFloat(CharSequence name, float value) {
        super.addFloat(name, value);
        return this;
    }

    @Override
    public TextHeaders addDouble(CharSequence name, double value) {
        super.addDouble(name, value);
        return this;
    }

    @Override
    public TextHeaders addTimeMillis(CharSequence name, long value) {
        super.addTimeMillis(name, value);
        return this;
    }

    @Override
    public TextHeaders add(TextHeaders headers) {
        super.add(headers);
        return this;
    }

    @Override
    public TextHeaders set(CharSequence name, CharSequence value) {
        super.set(name, value);
        return this;
    }

    @Override
    public TextHeaders set(CharSequence name, Iterable<? extends CharSequence> values) {
        super.set(name, values);
        return this;
    }

    @Override
    public TextHeaders set(CharSequence name, CharSequence... values) {
        super.set(name, values);
        return this;
    }

    @Override
    public TextHeaders setObject(CharSequence name, Object value) {
        super.setObject(name, value);
        return this;
    }

    @Override
    public TextHeaders setObject(CharSequence name, Iterable<?> values) {
        super.setObject(name, values);
        return this;
    }

    @Override
    public TextHeaders setObject(CharSequence name, Object... values) {
        super.setObject(name, values);
        return this;
    }

    @Override
    public TextHeaders setBoolean(CharSequence name, boolean value) {
        super.setBoolean(name, value);
        return this;
    }

    @Override
    public TextHeaders setChar(CharSequence name, char value) {
        super.setChar(name, value);
        return this;
    }

    @Override
    public TextHeaders setByte(CharSequence name, byte value) {
        super.setByte(name, value);
        return this;
    }

    @Override
    public TextHeaders setShort(CharSequence name, short value) {
        super.setShort(name, value);
        return this;
    }

    @Override
    public TextHeaders setInt(CharSequence name, int value) {
        super.setInt(name, value);
        return this;
    }

    @Override
    public TextHeaders setLong(CharSequence name, long value) {
        super.setLong(name, value);
        return this;
    }

    @Override
    public TextHeaders setFloat(CharSequence name, float value) {
        super.setFloat(name, value);
        return this;
    }

    @Override
    public TextHeaders setDouble(CharSequence name, double value) {
        super.setDouble(name, value);
        return this;
    }

    @Override
    public TextHeaders setTimeMillis(CharSequence name, long value) {
        super.setTimeMillis(name, value);
        return this;
    }

    @Override
    public TextHeaders set(TextHeaders headers) {
        super.set(headers);
        return this;
    }

    @Override
    public TextHeaders setAll(TextHeaders headers) {
        super.setAll(headers);
        return this;
    }

    @Override
    public TextHeaders clear() {
        super.clear();
        return this;
    }
}


File: codec/src/main/java/io/netty/handler/codec/Headers.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License, version 2.0 (the
 * "License"); you may not use this file except in compliance with the License. You may obtain a
 * copy of the License at:
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */
package io.netty.handler.codec;

import java.util.Comparator;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;

public interface Headers<T> extends Iterable<Map.Entry<T, T>> {
    /**
     * Provides an abstraction to iterate over elements maintained in the {@link Headers} collection.
     */
    interface EntryVisitor<T> {
        /**
         * @return <ul>
         *         <li>{@code true} if the processor wants to continue the loop and handle the entry.</li>
         *         <li>{@code false} if the processor wants to stop handling headers and abort the loop.</li>
         *         </ul>
         */
        boolean visit(Map.Entry<T, T> entry) throws Exception;
    }

    /**
     * Provides an abstraction to iterate over elements maintained in the {@link Headers} collection.
     */
    interface NameVisitor<T> {
        /**
         * @return <ul>
         *         <li>{@code true} if the processor wants to continue the loop and handle the entry.</li>
         *         <li>{@code false} if the processor wants to stop handling headers and abort the loop.</li>
         *         </ul>
         */
        boolean visit(T name) throws Exception;
    }

    /**
     * Converts to/from a generic object to the type of the name for this map
     */
    interface ValueConverter<T> {
        T convertObject(Object value);

        T convertBoolean(boolean value);

        boolean convertToBoolean(T value);

        T convertByte(byte value);

        byte convertToByte(T value);

        T convertChar(char value);

        char convertToChar(T value);

        T convertShort(short value);

        short convertToShort(T value);

        T convertInt(int value);

        int convertToInt(T value);

        T convertLong(long value);

        long convertToLong(T value);

        T convertTimeMillis(long value);

        long convertToTimeMillis(T value);

        T convertFloat(float value);

        float convertToFloat(T value);

        T convertDouble(double value);

        double convertToDouble(T value);
    }

    /**
     * Returns the value of a header with the specified name. If there are more than one values for the specified name,
     * the first value is returned.
     *
     * @param name the name of the header to search
     * @return the first header value if the header is found. {@code null} if there's no such header.
     */
    T get(T name);

    /**
     * Returns the value of a header with the specified name. If there are more than one values for the specified name,
     * the first value is returned.
     *
     * @param name the name of the header to search
     * @param defaultValue the default value
     * @return the first header value if the header is found. {@code defaultValue} if there's no such header.
     */
    T get(T name, T defaultValue);

    /**
     * Returns and removes the value of a header with the specified name. If there are more than one values for the
     * specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @return the first header value or {@code null} if there is no such header
     */
    T getAndRemove(T name);

    /**
     * Returns and removes the value of a header with the specified name. If there are more than one values for the
     * specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @param defaultValue the default value
     * @return the first header value or {@code defaultValue} if there is no such header
     */
    T getAndRemove(T name, T defaultValue);

    /**
     * Returns the values of headers with the specified name
     *
     * @param name The name of the headers to search
     * @return A {@link List} of header values which will be empty if no values are found
     */
    List<T> getAll(T name);

    /**
     * Returns and Removes the values of headers with the specified name
     *
     * @param name The name of the headers to search
     * @return A {@link List} of header values which will be empty if no values are found
     */
    List<T> getAllAndRemove(T name);

    /**
     * Returns the boolean value of a header with the specified name. If there are more than one values for the
     * specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @return the first header value if the header is found and its value is a boolean. {@code null} if there's no such
     *         header or its value is not a boolean.
     */
    Boolean getBoolean(T name);

    /**
     * Returns the boolean value of a header with the specified name. If there are more than one values for the
     * specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @param defaultValue the default value
     * @return the first header value if the header is found and its value is a boolean. {@code defaultValue} if there's
     *         no such header or its value is not a boolean.
     */
    boolean getBoolean(T name, boolean defaultValue);

    /**
     * Returns the byte value of a header with the specified name. If there are more than one values for the specified
     * name, the first value is returned.
     *
     * @param name the name of the header to search
     * @return the first header value if the header is found and its value is a byte. {@code null} if there's no such
     *         header or its value is not a byte.
     */
    Byte getByte(T name);

    /**
     * Returns the byte value of a header with the specified name. If there are more than one values for the specified
     * name, the first value is returned.
     *
     * @param name the name of the header to search
     * @param defaultValue the default value
     * @return the first header value if the header is found and its value is a byte. {@code defaultValue} if there's no
     *         such header or its value is not a byte.
     */
    byte getByte(T name, byte defaultValue);

    /**
     * Returns the char value of a header with the specified name. If there are more than one values for the specified
     * name, the first value is returned.
     *
     * @param name the name of the header to search
     * @return the first header value if the header is found and its value is a char. {@code null} if there's no such
     *         header or its value is not a char.
     */
    Character getChar(T name);

    /**
     * Returns the char value of a header with the specified name. If there are more than one values for the specified
     * name, the first value is returned.
     *
     * @param name the name of the header to search
     * @param defaultValue the default value
     * @return the first header value if the header is found and its value is a char. {@code defaultValue} if there's no
     *         such header or its value is not a char.
     */
    char getChar(T name, char defaultValue);

    /**
     * Returns the short value of a header with the specified name. If there are more than one values for the specified
     * name, the first value is returned.
     *
     * @param name the name of the header to search
     * @return the first header value if the header is found and its value is a short. {@code null} if there's no such
     *         header or its value is not a short.
     */
    Short getShort(T name);

    /**
     * Returns the short value of a header with the specified name. If there are more than one values for the specified
     * name, the first value is returned.
     *
     * @param name the name of the header to search
     * @param defaultValue the default value
     * @return the first header value if the header is found and its value is a short. {@code defaultValue} if there's
     *         no such header or its value is not a short.
     */
    short getInt(T name, short defaultValue);

    /**
     * Returns the integer value of a header with the specified name. If there are more than one values for the
     * specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @return the first header value if the header is found and its value is an integer. {@code null} if there's no
     *         such header or its value is not an integer.
     */
    Integer getInt(T name);

    /**
     * Returns the integer value of a header with the specified name. If there are more than one values for the
     * specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @param defaultValue the default value
     * @return the first header value if the header is found and its value is an integer. {@code defaultValue} if
     *         there's no such header or its value is not an integer.
     */
    int getInt(T name, int defaultValue);

    /**
     * Returns the long value of a header with the specified name. If there are more than one values for the specified
     * name, the first value is returned.
     *
     * @param name the name of the header to search
     * @return the first header value if the header is found and its value is a long. {@code null} if there's no such
     *         header or its value is not a long.
     */
    Long getLong(T name);

    /**
     * Returns the long value of a header with the specified name. If there are more than one values for the specified
     * name, the first value is returned.
     *
     * @param name the name of the header to search
     * @param defaultValue the default value
     * @return the first header value if the header is found and its value is a long. {@code defaultValue} if there's no
     *         such header or its value is not a long.
     */
    long getLong(T name, long defaultValue);

    /**
     * Returns the float value of a header with the specified name. If there are more than one values for the specified
     * name, the first value is returned.
     *
     * @param name the name of the header to search
     * @return the first header value if the header is found and its value is a float. {@code null} if there's no such
     *         header or its value is not a float.
     */
    Float getFloat(T name);

    /**
     * Returns the float value of a header with the specified name. If there are more than one values for the specified
     * name, the first value is returned.
     *
     * @param name the name of the header to search
     * @param defaultValue the default value
     * @return the first header value if the header is found and its value is a float. {@code defaultValue} if there's
     *         no such header or its value is not a float.
     */
    float getFloat(T name, float defaultValue);

    /**
     * Returns the double value of a header with the specified name. If there are more than one values for the specified
     * name, the first value is returned.
     *
     * @param name the name of the header to search
     * @return the first header value if the header is found and its value is a double. {@code null} if there's no such
     *         header or its value is not a double.
     */
    Double getDouble(T name);

    /**
     * Returns the double value of a header with the specified name. If there are more than one values for the specified
     * name, the first value is returned.
     *
     * @param name the name of the header to search
     * @param defaultValue the default value
     * @return the first header value if the header is found and its value is a double. {@code defaultValue} if there's
     *         no such header or its value is not a double.
     */
    double getDouble(T name, double defaultValue);

    /**
     * Returns the date value of a header with the specified name as milliseconds. If there are more than one values for
     * the specified name, the first value is returned.
     *
     * @param name The name of the header to search
     * @return the first header value in milliseconds if the header is found and its value is a date. {@code null} if
     *         there's no such header or its value is not a date.
     */
    Long getTimeMillis(T name);

    /**
     * Returns the date value of a header with the specified name as milliseconds. If there are more than one values for
     * the specified name, the first value is returned.
     *
     * @param name The name of the header to search
     * @param defaultValue default value
     * @return the first header value in milliseconds if the header is found and its value is a date.
     *         {@code defaultValue} if there's no such header or its value is not a date.
     */
    long getTimeMillis(T name, long defaultValue);

    /**
     * Returns and removes the boolean value of a header with the specified name. If there are more than one values for
     * the specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @return the first header value if the header is found and its value is a boolean. {@code null} if there's no such
     *         header or its value is not a boolean.
     */
    Boolean getBooleanAndRemove(T name);

    /**
     * Returns and removes the boolean value of a header with the specified name. If there are more than one values for
     * the specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @param defaultValue the default value
     * @return the first header value if the header is found and its value is a boolean. {@code defaultValue} if there
     *         is no such header or its value of header is not a boolean.
     */
    boolean getBooleanAndRemove(T name, boolean defaultValue);

    /**
     * Returns and removes the byte value of a header with the specified name. If there are more than one values for the
     * specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @return the first header value if the header is found and its value is a byte. {@code null} if there's no such
     *         header or its value is not a byte.
     */
    Byte getByteAndRemove(T name);

    /**
     * Returns and removes the byte value of a header with the specified name. If there are more than one values for the
     * specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @param defaultValue the default value
     * @return the first header value if the header is found and its value is a byte. {@code defaultValue} if there is
     *         no such header or its value of header is not a byte.
     */
    byte getByteAndRemove(T name, byte defaultValue);

    /**
     * Returns and removes the char value of a header with the specified name. If there are more than one values for the
     * specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @return the first header value if the header is found and its value is a char. {@code null} if there's no such
     *         header or its value is not a char.
     */
    Character getCharAndRemove(T name);

    /**
     * Returns and removes the char value of a header with the specified name. If there are more than one values for the
     * specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @param defaultValue the default value
     * @return the first header value if the header is found and its value is a char. {@code defaultValue} if there is
     *         no such header or its value of header is not a char.
     */
    char getCharAndRemove(T name, char defaultValue);

    /**
     * Returns and removes the short value of a header with the specified name. If there are more than one values for
     * the specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @return the first header value if the header is found and its value is a short. {@code null} if there's no such
     *         header or its value is not a short.
     */
    Short getShortAndRemove(T name);

    /**
     * Returns and removes the short value of a header with the specified name. If there are more than one values for
     * the specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @param defaultValue the default value
     * @return the first header value if the header is found and its value is a short. {@code defaultValue} if there is
     *         no such header or its value of header is not a short.
     */
    short getShortAndRemove(T name, short defaultValue);

    /**
     * Returns and removes the integer value of a header with the specified name. If there are more than one values for
     * the specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @return the first header value if the header is found and its value is an integer. {@code null} if there's no
     *         such header or its value is not an integer.
     */
    Integer getIntAndRemove(T name);

    /**
     * Returns and removes the integer value of a header with the specified name. If there are more than one values for
     * the specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @param defaultValue the default value
     * @return the first header value if the header is found and its value is an integer. {@code defaultValue} if there
     *         is no such header or its value of header is not an integer.
     */
    int getIntAndRemove(T name, int defaultValue);

    /**
     * Returns and removes the long value of a header with the specified name. If there are more than one values for the
     * specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @return the first header value if the header is found and its value is a long. {@code null} if there's no such
     *         header or its value is not a long.
     */
    Long getLongAndRemove(T name);

    /**
     * Returns and removes the long value of a header with the specified name. If there are more than one values for the
     * specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @param defaultValue the default value
     * @return the first header value if the header is found and its value is a long. {@code defaultValue} if there's no
     *         such header or its value is not a long.
     */
    long getLongAndRemove(T name, long defaultValue);

    /**
     * Returns and removes the float value of a header with the specified name. If there are more than one values for
     * the specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @return the first header value if the header is found and its value is a float. {@code null} if there's no such
     *         header or its value is not a float.
     */
    Float getFloatAndRemove(T name);

    /**
     * Returns and removes the float value of a header with the specified name. If there are more than one values for
     * the specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @param defaultValue the default value
     * @return the first header value if the header is found and its value is a float. {@code defaultValue} if there's
     *         no such header or its value is not a float.
     */
    float getFloatAndRemove(T name, float defaultValue);

    /**
     * Returns and removes the double value of a header with the specified name. If there are more than one values for
     * the specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @return the first header value if the header is found and its value is a double. {@code null} if there's no such
     *         header or its value is not a double.
     */
    Double getDoubleAndRemove(T name);

    /**
     * Returns and removes the double value of a header with the specified name. If there are more than one values for
     * the specified name, the first value is returned.
     *
     * @param name the name of the header to search
     * @param defaultValue the default value
     * @return the first header value if the header is found and its value is a double. {@code defaultValue} if there's
     *         no such header or its value is not a double.
     */
    double getDoubleAndRemove(T name, double defaultValue);

    /**
     * Returns and removes the date value of a header with the specified name as milliseconds. If there are more than
     * one values for the specified name, the first value is returned.
     *
     * @param name The name of the header to search
     * @return the first header value in milliseconds if the header is found and its value is a date. {@code null} if
     *         there's no such header or its value is not a date.
     */
    Long getTimeMillisAndRemove(T name);

    /**
     * Returns and removes the date value of a header with the specified name as milliseconds. If there are more than
     * one values for the specified name, the first value is returned.
     *
     * @param name The name of the header to search
     * @param defaultValue default value
     * @return the first header value in milliseconds if the header is found and its value is a date.
     *         {@code defaultValue} if there's no such header or its value is not a date.
     */
    long getTimeMillisAndRemove(T name, long defaultValue);

    /**
     * Returns a new {@link List} that contains all headers in this object. Note that modifying the returned
     * {@link List} will not affect the state of this object. If you intend to enumerate over the header entries only,
     * use {@link #iterator()} instead, which has much less overhead.
     */
    List<Entry<T, T>> entries();

    /**
     * Returns {@code true} if and only if this collection contains the header with the specified name.
     *
     * @param name The name of the header to search for
     * @return {@code true} if at least one header is found
     */
    boolean contains(T name);

    /**
     * Returns {@code true} if a header with the name and value exists.
     *
     * @param name the header name
     * @param value the header value
     * @return {@code true} if it contains it {@code false} otherwise
     */
    boolean contains(T name, T value);

    /**
     * Returns {@code true} if a header with the name and value exists.
     *
     * @param name the header name
     * @param value the header value
     * @return {@code true} if it contains it {@code false} otherwise
     */
    boolean containsObject(T name, Object value);

    /**
     * Returns {@code true} if a header with the name and value exists.
     *
     * @param name the header name
     * @param value the header value
     * @return {@code true} if it contains it {@code false} otherwise
     */
    boolean containsBoolean(T name, boolean value);

    /**
     * Returns {@code true} if a header with the name and value exists.
     *
     * @param name the header name
     * @param value the header value
     * @return {@code true} if it contains it {@code false} otherwise
     */
    boolean containsByte(T name, byte value);

    /**
     * Returns {@code true} if a header with the name and value exists.
     *
     * @param name the header name
     * @param value the header value
     * @return {@code true} if it contains it {@code false} otherwise
     */
    boolean containsChar(T name, char value);

    /**
     * Returns {@code true} if a header with the name and value exists.
     *
     * @param name the header name
     * @param value the header value
     * @return {@code true} if it contains it {@code false} otherwise
     */
    boolean containsShort(T name, short value);

    /**
     * Returns {@code true} if a header with the name and value exists.
     *
     * @param name the header name
     * @param value the header value
     * @return {@code true} if it contains it {@code false} otherwise
     */
    boolean containsInt(T name, int value);

    /**
     * Returns {@code true} if a header with the name and value exists.
     *
     * @param name the header name
     * @param value the header value
     * @return {@code true} if it contains it {@code false} otherwise
     */
    boolean containsLong(T name, long value);

    /**
     * Returns {@code true} if a header with the name and value exists.
     *
     * @param name the header name
     * @param value the header value
     * @return {@code true} if it contains it {@code false} otherwise
     */
    boolean containsFloat(T name, float value);

    /**
     * Returns {@code true} if a header with the name and value exists.
     *
     * @param name the header name
     * @param value the header value
     * @return {@code true} if it contains it {@code false} otherwise
     */
    boolean containsDouble(T name, double value);

    /**
     * Returns {@code true} if a header with the name and value exists.
     *
     * @param name the header name
     * @param value the header value
     * @return {@code true} if it contains it {@code false} otherwise
     */
    boolean containsTimeMillis(T name, long value);

    /**
     * Returns {@code true} if a header with the name and value exists.
     *
     * @param name the header name
     * @param value the header value
     * @param comparator The comparator to use when comparing {@code name} and {@code value} to entries in this map
     * @return {@code true} if it contains it {@code false} otherwise
     */
    boolean contains(T name, T value, Comparator<? super T> comparator);

    /**
     * Returns {@code true} if a header with the name and value exists.
     *
     * @param name the header name
     * @param value the header value
     * @param keyComparator The comparator to use when comparing {@code name} to names in this map
     * @param valueComparator The comparator to use when comparing {@code value} to values in this map
     * @return {@code true} if it contains it {@code false} otherwise
     */
    boolean contains(T name, T value, Comparator<? super T> keyComparator, Comparator<? super T> valueComparator);

    /**
     * Returns {@code true} if a header with the name and value exists.
     *
     * @param name the header name
     * @param value the header value
     * @param comparator The comparator to use when comparing {@code name} and {@code value} to entries in this map
     * @return {@code true} if it contains it {@code false} otherwise
     */
    boolean containsObject(T name, Object value, Comparator<? super T> comparator);

    /**
     * Returns {@code true} if a header with the name and value exists.
     *
     * @param name the header name
     * @param value the header value
     * @param keyComparator The comparator to use when comparing {@code name} to names in this map
     * @param valueComparator The comparator to use when comparing {@code value} to values in this map
     * @return {@code true} if it contains it {@code false} otherwise
     */
    boolean containsObject(T name, Object value, Comparator<? super T> keyComparator,
            Comparator<? super T> valueComparator);

    /**
     * Returns the number of header entries in this collection.
     */
    int size();

    /**
     * Returns {@code true} if and only if this collection contains no header entries.
     */
    boolean isEmpty();

    /**
     * Returns a new {@link Set} that contains the names of all headers in this object. Note that modifying the returned
     * {@link Set} will not affect the state of this object. If you intend to enumerate over the header entries only,
     * use {@link #iterator()} instead, which has much less overhead.
     */
    Set<T> names();

    /**
     * Returns a new {@link List} that contains the names of all headers in this object. Note that modifying the
     * returned {@link List} will not affect the state of this object. If you intend to enumerate over the header
     * entries only, use {@link #iterator()} instead, which has much less overhead.
     */
    List<T> namesList();

    /**
     * Adds a new header with the specified name and value. If the specified value is not a {@link String}, it is
     * converted into a {@link String} by {@link Object#toString()}, except in the cases of {@link java.util.Date} and
     * {@link java.util.Calendar}, which are formatted to the date format defined in <a
     * href="http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.3.1">RFC2616</a>.
     *
     * @param name the name of the header being added
     * @param value the value of the header being added
     * @return {@code this}
     */
    Headers<T> add(T name, T value);

    /**
     * Adds a new header with the specified name and values. This getMethod can be represented approximately as the
     * following code:
     *
     * <pre>
     * for (Object v : values) {
     *     if (v == null) {
     *         break;
     *     }
     *     headers.add(name, v);
     * }
     * </pre>
     *
     * @param name the name of the headepublic abstract rs being set
     * @param values the values of the headers being set
     * @return {@code this}
     */
    Headers<T> add(T name, Iterable<? extends T> values);

    /**
     * Adds a new header with the specified name and values. This getMethod can be represented approximately as the
     * following code:
     *
     * <pre>
     * for (Object v : values) {
     *     if (v == null) {
     *         break;
     *     }
     *     headers.add(name, v);
     * }
     * </pre>
     *
     * @param name the name of the headepublic abstract rs being set
     * @param values the values of the headers being set
     * @return {@code this}
     */
    Headers<T> add(T name, T... values);

    /**
     * Adds a new header with the specified name and value. If the specified value is not a {@link String}, it is
     * converted into a {@link String} by {@link Object#toString()}, except in the cases of {@link java.util.Date} and
     * {@link java.util.Calendar}, which are formatted to the date format defined in <a
     * href="http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.3.1">RFC2616</a>.
     *
     * @param name the name of the header being added
     * @param value the value of the header being added
     * @return {@code this}
     */
    Headers<T> addObject(T name, Object value);

    /**
     * Adds a new header with the specified name and values. This getMethod can be represented approximately as the
     * following code:
     *
     * <pre>
     * for (Object v : values) {
     *     if (v == null) {
     *         break;
     *     }
     *     headers.add(name, v);
     * }
     * </pre>
     *
     * @param name the name of the headepublic abstract rs being set
     * @param values the values of the headers being set
     * @return {@code this}
     */
    Headers<T> addObject(T name, Iterable<?> values);

    /**
     * Adds a new header with the specified name and values. This getMethod can be represented approximately as the
     * following code:
     *
     * <pre>
     * for (Object v : values) {
     *     if (v == null) {
     *         break;
     *     }
     *     headers.add(name, v);
     * }
     * </pre>
     *
     * @param name the name of the headepublic abstract rs being set
     * @param values the values of the headers being set
     * @return {@code this}
     */
    Headers<T> addObject(T name, Object... values);

    /**
     * Add the {@code name} to {@code value}.
     * @param name The name to modify
     * @param value The value
     * @return {@code this}
     */
    Headers<T> addBoolean(T name, boolean value);

    /**
     * Add the {@code name} to {@code value}.
     * @param name The name to modify
     * @param value The value
     * @return {@code this}
     */
    Headers<T> addByte(T name, byte value);

    /**
     * Add the {@code name} to {@code value}.
     * @param name The name to modify
     * @param value The value
     * @return {@code this}
     */
    Headers<T> addChar(T name, char value);

    /**
     * Add the {@code name} to {@code value}.
     * @param name The name to modify
     * @param value The value
     * @return {@code this}
     */
    Headers<T> addShort(T name, short value);

    /**
     * Add the {@code name} to {@code value}.
     * @param name The name to modify
     * @param value The value
     * @return {@code this}
     */
    Headers<T> addInt(T name, int value);

    /**
     * Add the {@code name} to {@code value}.
     * @param name The name to modify
     * @param value The value
     * @return {@code this}
     */
    Headers<T> addLong(T name, long value);

    /**
     * Add the {@code name} to {@code value}.
     * @param name The name to modify
     * @param value The value
     * @return {@code this}
     */
    Headers<T> addFloat(T name, float value);

    /**
     * Add the {@code name} to {@code value}.
     * @param name The name to modify
     * @param value The value
     * @return {@code this}
     */
    Headers<T> addDouble(T name, double value);

    /**
     * Add the {@code name} to {@code value}.
     * @param name The name to modify
     * @param value The value
     * @return {@code this}
     */
    Headers<T> addTimeMillis(T name, long value);

    /**
     * Adds all header entries of the specified {@code headers}.
     *
     * @return {@code this}
     */
    Headers<T> add(Headers<T> headers);

    /**
     * Sets a header with the specified name and value. If there is an existing header with the same name, it is
     * removed. If the specified value is not a {@link String}, it is converted into a {@link String} by
     * {@link Object#toString()}, except for {@link java.util.Date} and {@link java.util.Calendar}, which are formatted
     * to the date format defined in <a
     * href="http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.3.1">RFC2616</a>.
     *
     * @param name The name of the header being set
     * @param value The value of the header being set
     * @return {@code this}
     */
    Headers<T> set(T name, T value);

    /**
     * Sets a header with the specified name and values. If there is an existing header with the same name, it is
     * removed. This getMethod can be represented approximately as the following code:
     *
     * <pre>
     * headers.remove(name);
     * for (Object v : values) {
     *     if (v == null) {
     *         break;
     *     }
     *     headers.add(name, v);
     * }
     * </pre>
     *
     * @param name the name of the headers being set
     * @param values the values of the headers being set
     * @return {@code this}
     */
    Headers<T> set(T name, Iterable<? extends T> values);

    /**
     * Sets a header with the specified name and values. If there is an existing header with the same name, it is
     * removed. This getMethod can be represented approximately as the following code:
     *
     * <pre>
     * headers.remove(name);
     * for (Object v : values) {
     *     if (v == null) {
     *         break;
     *     }
     *     headers.add(name, v);
     * }
     * </pre>
     *
     * @param name the name of the headers being set
     * @param values the values of the headers being set
     * @return {@code this}
     */
    Headers<T> set(T name, T... values);

    /**
     * Sets a header with the specified name and value. If there is an existing header with the same name, it is
     * removed. If the specified value is not a {@link String}, it is converted into a {@link String} by
     * {@link Object#toString()}, except for {@link java.util.Date} and {@link java.util.Calendar}, which are formatted
     * to the date format defined in <a
     * href="http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.3.1">RFC2616</a>.
     *
     * @param name The name of the header being set
     * @param value The value of the header being set
     * @return {@code this}
     */
    Headers<T> setObject(T name, Object value);

    /**
     * Sets a header with the specified name and values. If there is an existing header with the same name, it is
     * removed. This getMethod can be represented approximately as the following code:
     *
     * <pre>
     * headers.remove(name);
     * for (Object v : values) {
     *     if (v == null) {
     *         break;
     *     }
     *     headers.add(name, v);
     * }
     * </pre>
     *
     * @param name the name of the headers being set
     * @param values the values of the headers being set
     * @return {@code this}
     */
    Headers<T> setObject(T name, Iterable<?> values);

    /**
     * Sets a header with the specified name and values. If there is an existing header with the same name, it is
     * removed. This getMethod can be represented approximately as the following code:
     *
     * <pre>
     * headers.remove(name);
     * for (Object v : values) {
     *     if (v == null) {
     *         break;
     *     }
     *     headers.add(name, v);
     * }
     * </pre>
     *
     * @param name the name of the headers being set
     * @param values the values of the headers being set
     * @return {@code this}
     */
    Headers<T> setObject(T name, Object... values);

    /**
     * Set the {@code name} to {@code value}. This will remove all previous values associated with {@code name}.
     * @param name The name to modify
     * @param value The value
     * @return {@code this}
     */
    Headers<T> setBoolean(T name, boolean value);

    /**
     * Set the {@code name} to {@code value}. This will remove all previous values associated with {@code name}.
     * @param name The name to modify
     * @param value The value
     * @return {@code this}
     */
    Headers<T> setByte(T name, byte value);

    /**
     * Set the {@code name} to {@code value}. This will remove all previous values associated with {@code name}.
     * @param name The name to modify
     * @param value The value
     * @return {@code this}
     */
    Headers<T> setChar(T name, char value);

    /**
     * Set the {@code name} to {@code value}. This will remove all previous values associated with {@code name}.
     * @param name The name to modify
     * @param value The value
     * @return {@code this}
     */
    Headers<T> setShort(T name, short value);

    /**
     * Set the {@code name} to {@code value}. This will remove all previous values associated with {@code name}.
     * @param name The name to modify
     * @param value The value
     * @return {@code this}
     */
    Headers<T> setInt(T name, int value);

    /**
     * Set the {@code name} to {@code value}. This will remove all previous values associated with {@code name}.
     * @param name The name to modify
     * @param value The value
     * @return {@code this}
     */
    Headers<T> setLong(T name, long value);

    /**
     * Set the {@code name} to {@code value}. This will remove all previous values associated with {@code name}.
     * @param name The name to modify
     * @param value The value
     * @return {@code this}
     */
    Headers<T> setFloat(T name, float value);

    /**
     * Set the {@code name} to {@code value}. This will remove all previous values associated with {@code name}.
     * @param name The name to modify
     * @param value The value
     * @return {@code this}
     */
    Headers<T> setDouble(T name, double value);

    /**
     * Set the {@code name} to {@code value}. This will remove all previous values associated with {@code name}.
     * @param name The name to modify
     * @param value The value
     * @return {@code this}
     */
    Headers<T> setTimeMillis(T name, long value);

    /**
     * Cleans the current header entries and copies all header entries of the specified {@code headers}.
     *
     * @return {@code this}
     */
    Headers<T> set(Headers<T> headers);

    /**
     * Retains all current headers but calls {@link #set(Object, Object)} for each entry in {@code headers}
     *
     * @param headers The headers used to {@link #set(Object, Object)} values in this instance
     * @return {@code this}
     */
    Headers<T> setAll(Headers<T> headers);

    /**
     * Removes the header with the specified name.
     *
     * @param name The name of the header to remove
     * @return {@code true} if and only if at least one entry has been removed
     */
    boolean remove(T name);

    /**
     * Removes all headers.
     *
     * @return {@code this}
     */
    Headers<T> clear();

    @Override
    Iterator<Entry<T, T>> iterator();

    /**
     * Provides an abstraction to iterate over elements maintained in the {@link Headers} collection.
     * @param visitor The visitor which will visit each element in this map
     * @return The last entry before iteration stopped or {@code null} if iteration went past the end
     */
    Map.Entry<T, T> forEachEntry(EntryVisitor<T> visitor) throws Exception;

    /**
     * Provides an abstraction to iterate over elements maintained in the {@link Headers} collection.
     * @param visitor The visitor which will visit each element in this map
     * @return The last key before iteration stopped or {@code null} if iteration went past the end
     */
    T forEachName(NameVisitor<T> visitor) throws Exception;
}


File: codec/src/main/java/io/netty/handler/codec/TextHeaders.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package io.netty.handler.codec;

/**
 * A typical string multimap used by text protocols such as HTTP for the representation of arbitrary key-value data. One
 * thing to note is that it uses {@link CharSequence} as its primary key and value type rather than {@link String}. When
 * you invoke the operations that produce {@link String}s such as {@link #get(Object)}, a {@link CharSequence} is
 * implicitly converted to a {@link String}. This is particularly useful for speed optimization because this multimap
 * can hold a special {@link CharSequence} implementation that a codec can treat specially, such as {@link CharSequence}
 * .
 */
public interface TextHeaders extends ConvertibleHeaders<CharSequence, String> {
    /**
     * A visitor that helps reduce GC pressure while iterating over a collection of {@link Headers}.
     */
    interface EntryVisitor extends Headers.EntryVisitor<CharSequence> {
    }

    /**
     * A visitor that helps reduce GC pressure while iterating over a collection of {@link Headers}.
     */
    interface NameVisitor extends Headers.NameVisitor<CharSequence> {
    }

    /**
     * Returns {@code true} if a header with the name and value exists.
     * @param name the header name
     * @param value the header value
     * @return {@code true} if it contains it {@code false} otherwise
     */
    boolean contains(CharSequence name, CharSequence value, boolean ignoreCase);

    /**
     * Returns {@code true} if a header with the name and value exists.
     * @param name the header name
     * @param value the header value
     * @return {@code true} if it contains it {@code false} otherwise
     */
    boolean containsObject(CharSequence name, Object value, boolean ignoreCase);

    @Override
    TextHeaders add(CharSequence name, CharSequence value);

    @Override
    TextHeaders add(CharSequence name, Iterable<? extends CharSequence> values);

    @Override
    TextHeaders add(CharSequence name, CharSequence... values);

    @Override
    TextHeaders addObject(CharSequence name, Object value);

    @Override
    TextHeaders addObject(CharSequence name, Iterable<?> values);

    @Override
    TextHeaders addObject(CharSequence name, Object... values);

    @Override
    TextHeaders addBoolean(CharSequence name, boolean value);

    @Override
    TextHeaders addByte(CharSequence name, byte value);

    @Override
    TextHeaders addChar(CharSequence name, char value);

    @Override
    TextHeaders addShort(CharSequence name, short value);

    @Override
    TextHeaders addInt(CharSequence name, int value);

    @Override
    TextHeaders addLong(CharSequence name, long value);

    @Override
    TextHeaders addFloat(CharSequence name, float value);

    @Override
    TextHeaders addDouble(CharSequence name, double value);

    @Override
    TextHeaders addTimeMillis(CharSequence name, long value);

    /**
     * See {@link Headers#add(Headers)}
     */
    TextHeaders add(TextHeaders headers);

    @Override
    TextHeaders set(CharSequence name, CharSequence value);

    @Override
    TextHeaders set(CharSequence name, Iterable<? extends CharSequence> values);

    @Override
    TextHeaders set(CharSequence name, CharSequence... values);

    @Override
    TextHeaders setObject(CharSequence name, Object value);

    @Override
    TextHeaders setObject(CharSequence name, Iterable<?> values);

    @Override
    TextHeaders setObject(CharSequence name, Object... values);

    @Override
    TextHeaders setBoolean(CharSequence name, boolean value);

    @Override
    TextHeaders setByte(CharSequence name, byte value);

    @Override
    TextHeaders setChar(CharSequence name, char value);

    @Override
    TextHeaders setShort(CharSequence name, short value);

    @Override
    TextHeaders setInt(CharSequence name, int value);

    @Override
    TextHeaders setLong(CharSequence name, long value);

    @Override
    TextHeaders setFloat(CharSequence name, float value);

    @Override
    TextHeaders setDouble(CharSequence name, double value);

    @Override
    TextHeaders setTimeMillis(CharSequence name, long value);

    /**
     * See {@link Headers#set(Headers)}
     */
    TextHeaders set(TextHeaders headers);

    /**
     * See {@link Headers#setAll(Headers)}
     */
    TextHeaders setAll(TextHeaders headers);

    @Override
    TextHeaders clear();
}


File: codec/src/test/java/io/netty/handler/codec/DefaultBinaryHeadersTest.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License, version 2.0 (the
 * "License"); you may not use this file except in compliance with the License. You may obtain a
 * copy of the License at:
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */
package io.netty.handler.codec;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import io.netty.util.AsciiString;
import io.netty.util.ByteString;

import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.NoSuchElementException;
import java.util.Random;
import java.util.Set;

import org.junit.Test;

/**
 * Tests for {@link DefaultBinaryHeaders}.
 */
public class DefaultBinaryHeadersTest {

    @Test
    public void binaryHeadersWithSameValuesShouldBeEquivalent() {
        byte[] key1 = randomBytes();
        byte[] value1 = randomBytes();
        byte[] key2 = randomBytes();
        byte[] value2 = randomBytes();

        DefaultBinaryHeaders h1 = new DefaultBinaryHeaders();
        h1.set(as(key1), as(value1));
        h1.set(as(key2), as(value2));

        DefaultBinaryHeaders h2 = new DefaultBinaryHeaders();
        h2.set(as(key1), as(value1));
        h2.set(as(key2), as(value2));

        assertTrue(h1.equals(h2));
        assertTrue(h2.equals(h1));
        assertTrue(h2.equals(h2));
        assertTrue(h1.equals(h1));
    }

    @Test
    public void binaryHeadersWithSameDuplicateValuesShouldBeEquivalent() {
        byte[] k1 = randomBytes();
        byte[] k2 = randomBytes();
        byte[] v1 = randomBytes();
        byte[] v2 = randomBytes();
        byte[] v3 = randomBytes();
        byte[] v4 = randomBytes();

        DefaultBinaryHeaders h1 = new DefaultBinaryHeaders();
        h1.set(as(k1), as(v1));
        h1.set(as(k2), as(v2));
        h1.add(as(k2), as(v3));
        h1.add(as(k1), as(v4));

        DefaultBinaryHeaders h2 = new DefaultBinaryHeaders();
        h2.set(as(k1), as(v1));
        h2.set(as(k2), as(v2));
        h2.add(as(k1), as(v4));
        h2.add(as(k2), as(v3));

        assertTrue(h1.equals(h2));
        assertTrue(h2.equals(h1));
        assertTrue(h2.equals(h2));
        assertTrue(h1.equals(h1));
    }

    @Test
    public void binaryHeadersWithDifferentValuesShouldNotBeEquivalent() {
        byte[] k1 = randomBytes();
        byte[] k2 = randomBytes();
        byte[] v1 = randomBytes();
        byte[] v2 = randomBytes();
        byte[] v3 = randomBytes();
        byte[] v4 = randomBytes();

        DefaultBinaryHeaders h1 = new DefaultBinaryHeaders();
        h1.set(as(k1), as(v1));
        h1.set(as(k2), as(v2));
        h1.add(as(k2), as(v3));
        h1.add(as(k1), as(v4));

        DefaultBinaryHeaders h2 = new DefaultBinaryHeaders();
        h2.set(as(k1), as(v1));
        h2.set(as(k2), as(v2));
        h2.add(as(k1), as(v4));

        assertFalse(h1.equals(h2));
        assertFalse(h2.equals(h1));
        assertTrue(h2.equals(h2));
        assertTrue(h1.equals(h1));
    }

    @Test
    public void binarySetAllShouldMergeHeaders() {
        byte[] k1 = randomBytes();
        byte[] k2 = randomBytes();
        byte[] v1 = randomBytes();
        byte[] v2 = randomBytes();
        byte[] v3 = randomBytes();
        byte[] v4 = randomBytes();

        DefaultBinaryHeaders h1 = new DefaultBinaryHeaders();
        h1.set(as(k1), as(v1));
        h1.set(as(k2), as(v2));
        h1.add(as(k2), as(v3));
        h1.add(as(k1), as(v4));

        DefaultBinaryHeaders h2 = new DefaultBinaryHeaders();
        h2.set(as(k1), as(v1));
        h2.set(as(k2), as(v2));
        h2.add(as(k1), as(v4));

        DefaultBinaryHeaders expected = new DefaultBinaryHeaders();
        expected.set(as(k1), as(v1));
        expected.set(as(k2), as(v2));
        expected.add(as(k2), as(v3));
        expected.add(as(k1), as(v4));
        expected.set(as(k1), as(v1));
        expected.set(as(k2), as(v2));
        expected.set(as(k1), as(v4));

        h1.setAll(h2);

        assertEquals(expected, h1);
    }

    @Test
    public void binarySetShouldReplacePreviousValues() {
        byte[] k1 = randomBytes();
        byte[] v1 = randomBytes();
        byte[] v2 = randomBytes();
        byte[] v3 = randomBytes();

        DefaultBinaryHeaders h1 = new DefaultBinaryHeaders();
        h1.add(as(k1), as(v1));
        h1.add(as(k1), as(v2));
        assertEquals(2, h1.size());

        h1.set(as(k1), as(v3));
        assertEquals(1, h1.size());
        List<ByteString> list = h1.getAll(as(k1));
        assertEquals(1, list.size());
        assertEquals(as(v3), list.get(0));
    }

    @Test
    public void headersWithSameValuesShouldBeEquivalent() {
        DefaultBinaryHeaders h1 = new DefaultBinaryHeaders();
        h1.set(as("foo"), as("goo"));
        h1.set(as("foo2"), as("goo2"));

        DefaultBinaryHeaders h2 = new DefaultBinaryHeaders();
        h2.set(as("foo"), as("goo"));
        h2.set(as("foo2"), as("goo2"));

        assertTrue(h1.equals(h2));
        assertTrue(h2.equals(h1));
        assertTrue(h2.equals(h2));
        assertTrue(h1.equals(h1));
    }

    @Test
    public void headersWithSameDuplicateValuesShouldBeEquivalent() {
        DefaultBinaryHeaders h1 = new DefaultBinaryHeaders();
        h1.set(as("foo"), as("goo"));
        h1.set(as("foo2"), as("goo2"));
        h1.add(as("foo2"), as("goo3"));
        h1.add(as("foo"), as("goo4"));

        DefaultBinaryHeaders h2 = new DefaultBinaryHeaders();
        h2.set(as("foo"), as("goo"));
        h2.set(as("foo2"), as("goo2"));
        h2.add(as("foo"), as("goo4"));
        h2.add(as("foo2"), as("goo3"));

        assertTrue(h1.equals(h2));
        assertTrue(h2.equals(h1));
        assertTrue(h2.equals(h2));
        assertTrue(h1.equals(h1));
    }

    @Test
    public void headersWithDifferentValuesShouldNotBeEquivalent() {
        DefaultBinaryHeaders h1 = new DefaultBinaryHeaders();
        h1.set(as("foo"), as("goo"));
        h1.set(as("foo2"), as("goo2"));
        h1.add(as("foo2"), as("goo3"));
        h1.add(as("foo"), as("goo4"));

        DefaultBinaryHeaders h2 = new DefaultBinaryHeaders();
        h2.set(as("foo"), as("goo"));
        h2.set(as("foo2"), as("goo2"));
        h2.add(as("foo"), as("goo4"));

        assertFalse(h1.equals(h2));
        assertFalse(h2.equals(h1));
        assertTrue(h2.equals(h2));
        assertTrue(h1.equals(h1));
    }

    @Test
    public void setAllShouldMergeHeaders() {
        DefaultBinaryHeaders h1 = new DefaultBinaryHeaders();
        h1.set(as("foo"), as("goo"));
        h1.set(as("foo2"), as("goo2"));
        h1.add(as("foo2"), as("goo3"));
        h1.add(as("foo"), as("goo4"));

        DefaultBinaryHeaders h2 = new DefaultBinaryHeaders();
        h2.set(as("foo"), as("goo"));
        h2.set(as("foo2"), as("goo2"));
        h2.add(as("foo"), as("goo4"));

        DefaultBinaryHeaders expected = new DefaultBinaryHeaders();
        expected.set(as("foo"), as("goo"));
        expected.set(as("foo2"), as("goo2"));
        expected.add(as("foo2"), as("goo3"));
        expected.add(as("foo"), as("goo4"));
        expected.set(as("foo"), as("goo"));
        expected.set(as("foo2"), as("goo2"));
        expected.set(as("foo"), as("goo4"));

        h1.setAll(h2);

        assertEquals(expected, h1);
    }

    @Test
    public void setShouldReplacePreviousValues() {
        DefaultBinaryHeaders h1 = new DefaultBinaryHeaders();
        h1.add(as("foo"), as("goo"));
        h1.add(as("foo"), as("goo2"));
        assertEquals(2, h1.size());

        h1.set(as("foo"), as("goo3"));
        assertEquals(1, h1.size());
        List<ByteString> list = h1.getAll(as("foo"));
        assertEquals(1, list.size());
        assertEquals(as("goo3"), list.get(0));
    }

    @Test(expected = NoSuchElementException.class)
    public void iterateEmptyHeadersShouldThrow() {
        Iterator<Map.Entry<ByteString, ByteString>> iterator = new DefaultBinaryHeaders().iterator();
        assertFalse(iterator.hasNext());
        iterator.next();
    }

    @Test
    public void iterateHeadersShouldReturnAllValues() {
        Set<String> headers = new HashSet<String>();
        headers.add("a:1");
        headers.add("a:2");
        headers.add("a:3");
        headers.add("b:1");
        headers.add("b:2");
        headers.add("c:1");

        // Build the headers from the input set.
        DefaultBinaryHeaders h1 = new DefaultBinaryHeaders();
        for (String header : headers) {
            String[] parts = header.split(":");
            h1.add(as(parts[0]), as(parts[1]));
        }

        // Now iterate through the headers, removing them from the original set.
        for (Map.Entry<ByteString, ByteString> entry : h1) {
            assertTrue(headers.remove(entry.getKey().toString() + ':' + entry.getValue().toString()));
        }

        // Make sure we removed them all.
        assertTrue(headers.isEmpty());
    }

    @Test
    public void getAndRemoveShouldReturnFirstEntry() {
        DefaultBinaryHeaders h1 = new DefaultBinaryHeaders();
        h1.add(as("foo"), as("goo"));
        h1.add(as("foo"), as("goo2"));
        assertEquals(as("goo"), h1.getAndRemove(as("foo")));
        assertEquals(0, h1.size());
        List<ByteString> values = h1.getAll(as("foo"));
        assertEquals(0, values.size());
    }

    private static byte[] randomBytes() {
        byte[] data = new byte[100];
        new Random().nextBytes(data);
        return data;
    }

    private AsciiString as(byte[] bytes) {
        return new AsciiString(bytes);
    }

    private AsciiString as(String value) {
        return new AsciiString(value);
    }
}


File: codec/src/test/java/io/netty/handler/codec/DefaultTextHeadersTest.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License, version
 * 2.0 (the "License"); you may not use this file except in compliance with the
 * License. You may obtain a copy of the License at:
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */
package io.netty.handler.codec;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static io.netty.util.internal.StringUtil.COMMA;
import static io.netty.util.internal.StringUtil.DOUBLE_QUOTE;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.Test;

public class DefaultTextHeadersTest {

    private static final String HEADER_NAME = "testHeader";

    @Test
    public void testEqualsMultipleHeaders() {
        DefaultTextHeaders h1 = new DefaultTextHeaders();
        h1.set("Foo", "goo");
        h1.set("foo2", "goo2");

        DefaultTextHeaders h2 = new DefaultTextHeaders();
        h2.set("FoO", "goo");
        h2.set("fOO2", "goo2");

        assertTrue(h1.equals(h2));
        assertTrue(h2.equals(h1));
        assertTrue(h2.equals(h2));
        assertTrue(h1.equals(h1));
    }

    @Test
    public void testEqualsDuplicateMultipleHeaders() {
        DefaultTextHeaders h1 = new DefaultTextHeaders();
        h1.set("FOO", "goo");
        h1.set("Foo2", "goo2");
        h1.add("fOo2", "goo3");
        h1.add("foo", "goo4");

        DefaultTextHeaders h2 = new DefaultTextHeaders();
        h2.set("foo", "goo");
        h2.set("foo2", "goo2");
        h2.add("foo", "goo4");
        h2.add("foO2", "goo3");

        assertTrue(h1.equals(h2));
        assertTrue(h2.equals(h1));
        assertTrue(h2.equals(h2));
        assertTrue(h1.equals(h1));
    }

    @Test
    public void testNotEqualsDuplicateMultipleHeaders() {
        DefaultTextHeaders h1 = new DefaultTextHeaders();
        h1.set("FOO", "goo");
        h1.set("foo2", "goo2");
        h1.add("foo2", "goo3");
        h1.add("foo", "goo4");

        DefaultTextHeaders h2 = new DefaultTextHeaders();
        h2.set("foo", "goo");
        h2.set("foo2", "goo2");
        h2.add("foo", "goo4");

        assertFalse(h1.equals(h2));
        assertFalse(h2.equals(h1));
        assertTrue(h2.equals(h2));
        assertTrue(h1.equals(h1));
    }

    @Test
    public void testSetAll() {
        DefaultTextHeaders h1 = new DefaultTextHeaders();
        h1.set("FOO", "goo");
        h1.set("foo2", "goo2");
        h1.add("foo2", "goo3");
        h1.add("foo", "goo4");

        DefaultTextHeaders h2 = new DefaultTextHeaders();
        h2.set("foo", "goo");
        h2.set("foo2", "goo2");
        h2.add("foo", "goo4");

        DefaultTextHeaders expected = new DefaultTextHeaders();
        expected.set("FOO", "goo");
        expected.set("foo2", "goo2");
        expected.add("foo2", "goo3");
        expected.add("foo", "goo4");
        expected.set("foo", "goo");
        expected.set("foo2", "goo2");
        expected.set("foo", "goo4");

        h1.setAll(h2);

        assertEquals(expected, h1);
    }

    @Test
    public void addCharSequences() {
        final TextHeaders headers = newDefaultTextHeaders();
        headers.add(HEADER_NAME, HeaderValue.THREE.asArray());
        assertDefaultValues(headers, HeaderValue.THREE);
    }

    @Test
    public void addCharSequencesCsv() {
        final TextHeaders headers = newCsvTextHeaders();
        headers.add(HEADER_NAME, HeaderValue.THREE.asArray());
        assertCsvValues(headers, HeaderValue.THREE);
    }

    @Test
    public void addCharSequencesCsvWithExistingHeader() {
        final TextHeaders headers = newCsvTextHeaders();
        headers.add(HEADER_NAME, HeaderValue.THREE.asArray());
        headers.add(HEADER_NAME, HeaderValue.FIVE.subset(4));
        assertCsvValues(headers, HeaderValue.FIVE);
    }

    @Test
    public void addCharSequencesCsvWithValueContainingComma() {
        final TextHeaders headers = newCsvTextHeaders();
        headers.add(HEADER_NAME, HeaderValue.SIX_QUOTED.subset(4));
        assertEquals(HeaderValue.SIX_QUOTED.subsetAsCsvString(4), headers.getAndConvert(HEADER_NAME));
        assertEquals(HeaderValue.SIX_QUOTED.subsetAsCsvString(4), headers.getAllAndConvert(HEADER_NAME).get(0));
    }

    @Test
    public void addCharSequencesCsvWithValueContainingCommas() {
        final TextHeaders headers = newCsvTextHeaders();
        headers.add(HEADER_NAME, HeaderValue.EIGHT.subset(6));
        assertEquals(HeaderValue.EIGHT.subsetAsCsvString(6), headers.getAndConvert(HEADER_NAME));
        assertEquals(HeaderValue.EIGHT.subsetAsCsvString(6), headers.getAllAndConvert(HEADER_NAME).get(0));
    }

    @Test (expected = NullPointerException.class)
    public void addCharSequencesCsvNullValue() {
        final TextHeaders headers = newCsvTextHeaders();
        final String value = null;
        headers.add(HEADER_NAME, value);
    }

    @Test
    public void addCharSequencesCsvMultipleTimes() {
        final TextHeaders headers = newCsvTextHeaders();
        for (int i = 0; i < 5; ++i) {
            headers.add(HEADER_NAME, "value");
        }
        assertEquals("value,value,value,value,value", headers.getAndConvert(HEADER_NAME));
    }

    @Test
    public void addCharSequenceCsv() {
        final TextHeaders headers = newCsvTextHeaders();
        addValues(headers, HeaderValue.ONE, HeaderValue.TWO, HeaderValue.THREE);
        assertCsvValues(headers, HeaderValue.THREE);
    }

    @Test
    public void addCharSequenceCsvSingleValue() {
        final TextHeaders headers = newCsvTextHeaders();
        addValues(headers, HeaderValue.ONE);
        assertCsvValue(headers, HeaderValue.ONE);
    }

    @Test
    public void addIterable() {
        final TextHeaders headers = newDefaultTextHeaders();
        headers.add(HEADER_NAME, HeaderValue.THREE.asList());
        assertDefaultValues(headers, HeaderValue.THREE);
    }

    @Test
    public void addIterableCsv() {
        final TextHeaders headers = newCsvTextHeaders();
        headers.add(HEADER_NAME, HeaderValue.THREE.asList());
        assertCsvValues(headers, HeaderValue.THREE);
    }

    @Test
    public void addIterableCsvWithExistingHeader() {
        final TextHeaders headers = newCsvTextHeaders();
        headers.add(HEADER_NAME, HeaderValue.THREE.asArray());
        headers.add(HEADER_NAME, HeaderValue.FIVE.subset(4));
        assertCsvValues(headers, HeaderValue.FIVE);
    }

    @Test
    public void addIterableCsvSingleValue() {
        final TextHeaders headers = newCsvTextHeaders();
        headers.add(HEADER_NAME, HeaderValue.ONE.asList());
        assertCsvValue(headers, HeaderValue.ONE);
    }

    @Test
    public void addIterableCsvEmtpy() {
        final TextHeaders headers = newCsvTextHeaders();
        headers.add(HEADER_NAME, Collections.<CharSequence>emptyList());
        assertEquals("", headers.getAllAndConvert(HEADER_NAME).get(0));
    }

    @Test
    public void addObjectCsv() {
        final TextHeaders headers = newCsvTextHeaders();
        addObjectValues(headers, HeaderValue.ONE, HeaderValue.TWO, HeaderValue.THREE);
        assertCsvValues(headers, HeaderValue.THREE);
    }

    @Test
    public void addObjects() {
        final TextHeaders headers = newDefaultTextHeaders();
        headers.addObject(HEADER_NAME, HeaderValue.THREE.asArray());
        assertDefaultValues(headers, HeaderValue.THREE);
    }

    @Test
    public void addObjectsCsv() {
        final TextHeaders headers = newCsvTextHeaders();
        headers.addObject(HEADER_NAME, HeaderValue.THREE.asArray());
        assertCsvValues(headers, HeaderValue.THREE);
    }

    @Test
    public void addObjectsIterableCsv() {
        final TextHeaders headers = newCsvTextHeaders();
        headers.addObject(HEADER_NAME, HeaderValue.THREE.asList());
        assertCsvValues(headers, HeaderValue.THREE);
    }

    @Test
    public void addObjectsCsvWithExistingHeader() {
        final TextHeaders headers = newCsvTextHeaders();
        headers.addObject(HEADER_NAME, HeaderValue.THREE.asArray());
        headers.addObject(HEADER_NAME, HeaderValue.FIVE.subset(4));
        assertCsvValues(headers, HeaderValue.FIVE);
    }

    @Test
    public void setCharSequences() {
        final TextHeaders headers = newDefaultTextHeaders();
        headers.set(HEADER_NAME, HeaderValue.THREE.asArray());
        assertDefaultValues(headers, HeaderValue.THREE);
    }

    @Test
    public void setCharSequenceCsv() {
        final TextHeaders headers = newCsvTextHeaders();
        headers.set(HEADER_NAME, HeaderValue.THREE.asArray());
        assertCsvValues(headers, HeaderValue.THREE);
    }

    @Test
    public void setIterable() {
        final TextHeaders headers = newDefaultTextHeaders();
        headers.set(HEADER_NAME, HeaderValue.THREE.asList());
        assertDefaultValues(headers, HeaderValue.THREE);
    }

    @Test
    public void setIterableCsv() {
        final TextHeaders headers = newCsvTextHeaders();
        headers.set(HEADER_NAME, HeaderValue.THREE.asList());
        assertCsvValues(headers, HeaderValue.THREE);
    }

    @Test
    public void setObjectObjects() {
        final TextHeaders headers = newDefaultTextHeaders();
        headers.setObject(HEADER_NAME, HeaderValue.THREE.asArray());
        assertDefaultValues(headers, HeaderValue.THREE);
    }

    @Test
    public void setObjectObjectsCsv() {
        final TextHeaders headers = newCsvTextHeaders();
        headers.setObject(HEADER_NAME, HeaderValue.THREE.asArray());
        assertCsvValues(headers, HeaderValue.THREE);
    }

    @Test
    public void setObjectIterable() {
        final TextHeaders headers = newDefaultTextHeaders();
        headers.setObject(HEADER_NAME, HeaderValue.THREE.asList());
        assertDefaultValues(headers, HeaderValue.THREE);
    }

    @Test
    public void setObjectIterableCsv() {
        final TextHeaders headers = newCsvTextHeaders();
        headers.setObject(HEADER_NAME, HeaderValue.THREE.asList());
        assertCsvValues(headers, HeaderValue.THREE);
    }

    private static void assertDefaultValues(final TextHeaders headers, final HeaderValue headerValue) {
        assertEquals(headerValue.asArray()[0], headers.get(HEADER_NAME));
        assertEquals(headerValue.asList(), headers.getAll(HEADER_NAME));
    }

    private static void assertCsvValues(final TextHeaders headers, final HeaderValue headerValue) {
        assertEquals(headerValue.asCsv(), headers.getAndConvert(HEADER_NAME));
        assertEquals(headerValue.asCsv(), headers.getAllAndConvert(HEADER_NAME).get(0));
    }

    private static void assertCsvValue(final TextHeaders headers, final HeaderValue headerValue) {
        assertEquals(headerValue.toString(), headers.getAndConvert(HEADER_NAME));
        assertEquals(headerValue.toString(), headers.getAllAndConvert(HEADER_NAME).get(0));
    }

    private static TextHeaders newDefaultTextHeaders() {
        return new DefaultTextHeaders();
    }

    private static TextHeaders newCsvTextHeaders() {
        return new DefaultTextHeaders(true, true);
    }

    private static void addValues(final TextHeaders headers, HeaderValue... headerValues) {
        for (HeaderValue v: headerValues) {
            headers.add(HEADER_NAME, v.toString());
        }
    }

    private static void addObjectValues(final TextHeaders headers, HeaderValue... headerValues) {
        for (HeaderValue v: headerValues) {
            headers.addObject(HEADER_NAME, v.toString());
        }
    }

    private enum HeaderValue {
        UNKNOWN("unknown", 0),
        ONE("one", 1),
        TWO("two", 2),
        THREE("three", 3),
        FOUR("four", 4),
        FIVE("five", 5),
        SIX_QUOTED("six,", 6),
        SEVEN_QUOTED("seven; , GMT", 7),
        EIGHT("eight", 8);

        private final int nr;
        private final String value;
        private String[] array;
        private static final String DOUBLE_QUOTE_STRING = String.valueOf(DOUBLE_QUOTE);

        HeaderValue(final String value, final int nr) {
            this.nr = nr;
            this.value = value;
        }

        @Override
        public String toString() {
            return value;
        }

        public String[] asArray() {
            if (array == null) {
                final String[] arr = new String[nr];
                for (int i = 1, y = 0; i <= nr; i++, y++) {
                    arr[y] = of(i).toString();
                }
                array = arr;
            }
            return array;
        }

        public String[] subset(final int from) {
            final int size = from - 1;
            final String[] arr = new String[nr - size];
            System.arraycopy(asArray(), size, arr, 0, arr.length);
            return arr;
        }

        public String subsetAsCsvString(final int from) {
            final String[] subset = subset(from);
            return asCsv(subset);
        }

        public List<CharSequence> asList() {
            return Arrays.<CharSequence>asList(asArray());
        }

        public String asCsv(final String[] arr) {
            final StringBuilder sb = new StringBuilder();
            int end = arr.length - 1;
            for (int i = 0; i < end; i++) {
                final String value = arr[i];
                quoted(sb, value).append(COMMA);
            }
            quoted(sb, arr[end]);
            return sb.toString();
        }

        public String asCsv() {
            return asCsv(asArray());
        }

        private static StringBuilder quoted(final StringBuilder sb, final String value) {
            if (value.contains(String.valueOf(COMMA)) && !value.contains(DOUBLE_QUOTE_STRING)) {
                return sb.append(DOUBLE_QUOTE).append(value).append(DOUBLE_QUOTE);
            }
            return sb.append(value);
        }

        public static String quoted(final String value) {
            return quoted(new StringBuilder(), value).toString();
        }

        private static final Map<Integer, HeaderValue> MAP;

        static {
            final Map<Integer, HeaderValue> map = new HashMap<Integer, HeaderValue>();
            for (HeaderValue v : values()) {
                final int nr = v.nr;
                map.put(Integer.valueOf(nr), v);
            }
            MAP = map;
        }

        public static HeaderValue of(final int nr) {
            final HeaderValue v = MAP.get(Integer.valueOf(nr));
            return v == null ? UNKNOWN : v;
        }
    }
}


File: common/src/main/java/io/netty/util/AsciiString.java
/*
 * Copyright 2014 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */
package io.netty.util;

import static io.netty.util.internal.ObjectUtil.checkNotNull;
import static io.netty.util.internal.StringUtil.UPPER_CASE_TO_LOWER_CASE_ASCII_OFFSET;
import io.netty.util.ByteProcessor.IndexOfProcessor;
import io.netty.util.internal.EmptyArrays;
import io.netty.util.internal.PlatformDependent;

import java.nio.ByteBuffer;
import java.nio.charset.Charset;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

/**
 * A string which has been encoded into a character encoding whose character always takes a single byte, similarly to
 * ASCII. It internally keeps its content in a byte array unlike {@link String}, which uses a character array, for
 * reduced memory footprint and faster data transfer from/to byte-based data structures such as a byte array and
 * {@link ByteBuffer}. It is often used in conjunction with {@link TextHeaders}.
 */
public final class AsciiString extends ByteString implements CharSequence, Comparable<CharSequence> {

    private static final char MAX_CHAR_VALUE = 255;
    public static final AsciiString EMPTY_STRING = new AsciiString("");

    public static final Comparator<AsciiString> CASE_INSENSITIVE_ORDER = new Comparator<AsciiString>() {
        @Override
        public int compare(AsciiString o1, AsciiString o2) {
            return CHARSEQUENCE_CASE_INSENSITIVE_ORDER.compare(o1, o2);
        }
    };
    public static final Comparator<AsciiString> CASE_SENSITIVE_ORDER = new Comparator<AsciiString>() {
        @Override
        public int compare(AsciiString o1, AsciiString o2) {
            return CHARSEQUENCE_CASE_SENSITIVE_ORDER.compare(o1, o2);
        }
    };

    public static final Comparator<CharSequence> CHARSEQUENCE_CASE_INSENSITIVE_ORDER = new Comparator<CharSequence>() {
        @Override
        public int compare(CharSequence o1, CharSequence o2) {
            if (o1 == o2) {
                return 0;
            }

            AsciiString a1 = o1 instanceof AsciiString ? (AsciiString) o1 : null;
            AsciiString a2 = o2 instanceof AsciiString ? (AsciiString) o2 : null;

            int result;
            int length1 = o1.length();
            int length2 = o2.length();
            int minLength = Math.min(length1, length2);
            if (a1 != null && a2 != null) {
                final int a1Len = minLength + a1.arrayOffset();
                for (int i = a1.arrayOffset(), j = a2.arrayOffset(); i < a1Len; i++, j++) {
                    byte v1 = a1.value[i];
                    byte v2 = a2.value[j];
                    if (v1 == v2) {
                        continue;
                    }
                    int c1 = toLowerCase(v1);
                    int c2 = toLowerCase(v2);
                    result = c1 - c2;
                    if (result != 0) {
                        return result;
                    }
                }
            } else if (a1 != null) {
                for (int i = a1.arrayOffset(), j = 0; j < minLength; i++, j++) {
                    int c1 = toLowerCase(a1.value[i]);
                    int c2 = toLowerCase(o2.charAt(j));
                    result = c1 - c2;
                    if (result != 0) {
                        return result;
                    }
                }
            } else if (a2 != null) {
                for (int i = 0, j = a2.arrayOffset(); i < minLength; i++, j++) {
                    int c1 = toLowerCase(o1.charAt(i));
                    int c2 = toLowerCase(a2.value[j]);
                    result = c1 - c2;
                    if (result != 0) {
                        return result;
                    }
                }
            } else {
                for (int i = 0; i < minLength; i++) {
                    int c1 = toLowerCase(o1.charAt(i));
                    int c2 = toLowerCase(o2.charAt(i));
                    result = c1 - c2;
                    if (result != 0) {
                        return result;
                    }
                }
            }

            return length1 - length2;
        }
    };

    public static final Comparator<CharSequence> CHARSEQUENCE_CASE_SENSITIVE_ORDER = new Comparator<CharSequence>() {
        @Override
        public int compare(CharSequence o1, CharSequence o2) {
            if (o1 == o2) {
                return 0;
            }

            AsciiString a1 = o1 instanceof AsciiString ? (AsciiString) o1 : null;
            AsciiString a2 = o2 instanceof AsciiString ? (AsciiString) o2 : null;

            int result;
            int length1 = o1.length();
            int length2 = o2.length();
            int minLength = Math.min(length1, length2);
            if (a1 != null && a2 != null) {
                final int a1Len = minLength + a1.arrayOffset();
                for (int i = a1.arrayOffset(), j = a2.arrayOffset(); i < a1Len; i++, j++) {
                    byte v1 = a1.value[i];
                    byte v2 = a2.value[j];
                    result = v1 - v2;
                    if (result != 0) {
                        return result;
                    }
                }
            } else if (a1 != null) {
                for (int i = a1.arrayOffset(), j = 0; j < minLength; i++, j++) {
                    int c1 = a1.value[i];
                    int c2 = o2.charAt(j);
                    result = c1 - c2;
                    if (result != 0) {
                        return result;
                    }
                }
            } else if (a2 != null) {
                for (int i = 0, j = a2.arrayOffset(); i < minLength; i++, j++) {
                    int c1 = o1.charAt(i);
                    int c2 = a2.value[j];
                    result = c1 - c2;
                    if (result != 0) {
                        return result;
                    }
                }
            } else {
                for (int i = 0; i < minLength; i++) {
                    int c1 = o1.charAt(i);
                    int c2 = o2.charAt(i);
                    result = c1 - c2;
                    if (result != 0) {
                        return result;
                    }
                }
            }

            return length1 - length2;
        }
    };

    /**
     * Factory which uses the {@link #AsciiString(byte[], int, int, boolean)} constructor.
     */
    private static final ByteStringFactory DEFAULT_FACTORY = new ByteStringFactory() {
        @Override
        public ByteString newInstance(byte[] value, int start, int length, boolean copy) {
            return new AsciiString(value, start, length, copy);
        }
    };

    /**
     * Returns the case-insensitive hash code of the specified string. Note that this method uses the same hashing
     * algorithm with {@link #hashCode()} so that you can put both {@link AsciiString}s and arbitrary
     * {@link CharSequence}s into the same {@link TextHeaders}.
     */
    public static int caseInsensitiveHashCode(CharSequence value) {
        if (value instanceof AsciiString) {
            try {
                ByteProcessor processor = new ByteProcessor() {
                    private int hash;
                    @Override
                    public boolean process(byte value) throws Exception {
                        hash = hash * HASH_CODE_PRIME ^ toLowerCase(value) & HASH_CODE_PRIME;
                        return true;
                    }

                    @Override
                    public int hashCode() {
                        return hash;
                    }
                };
                ((AsciiString) value).forEachByte(processor);
                return processor.hashCode();
            } catch (Exception e) {
                PlatformDependent.throwException(e);
            }
        }

        int hash = 0;
        final int end = value.length();
        for (int i = 0; i < end; i++) {
            hash = hash * HASH_CODE_PRIME ^ toLowerCase(value.charAt(i)) & HASH_CODE_PRIME;
        }
        return hash;
    }

    /**
     * Returns {@code true} if both {@link CharSequence}'s are equals when ignore the case. This only supports 8-bit
     * ASCII.
     */
    public static boolean equalsIgnoreCase(CharSequence a, CharSequence b) {
        if (a == b) {
            return true;
        }

        if (a instanceof AsciiString) {
            AsciiString aa = (AsciiString) a;
            return aa.equalsIgnoreCase(b);
        }

        if (b instanceof AsciiString) {
            AsciiString ab = (AsciiString) b;
            return ab.equalsIgnoreCase(a);
        }

        if (a == null || b == null) {
            return false;
        }

        return a.toString().equalsIgnoreCase(b.toString());
    }

    /**
     * Returns {@code true} if both {@link CharSequence}'s are equals. This only supports 8-bit ASCII.
     */
    public static boolean equals(CharSequence a, CharSequence b) {
        if (a == b) {
            return true;
        }

        if (a instanceof AsciiString) {
            AsciiString aa = (AsciiString) a;
            return aa.equals(b);
        }

        if (b instanceof AsciiString) {
            AsciiString ab = (AsciiString) b;
            return ab.equals(a);
        }

        if (a == null || b == null) {
            return false;
        }

        return a.equals(b);
    }

    private String string;

    /**
     * Returns an {@link AsciiString} containing the given character sequence. If the given string is already a
     * {@link AsciiString}, just returns the same instance.
     */
    public static AsciiString of(CharSequence string) {
        return string instanceof AsciiString ? (AsciiString) string : new AsciiString(string);
    }

    public AsciiString(byte[] value) {
        super(value);
    }

    public AsciiString(byte[] value, boolean copy) {
        super(value, copy);
    }

    public AsciiString(byte[] value, int start, int length, boolean copy) {
        super(value, start, length, copy);
    }

    public AsciiString(ByteString value, boolean copy) {
        super(value, copy);
    }

    public AsciiString(ByteBuffer value) {
        super(value);
    }

    public AsciiString(ByteBuffer value, int start, int length, boolean copy) {
        super(value, start, length, copy);
    }

    public AsciiString(char[] value) {
        this(checkNotNull(value, "value"), 0, value.length);
    }

    public AsciiString(char[] value, int start, int length) {
        super(length);
        if (start < 0 || start > checkNotNull(value, "value").length - length) {
            throw new IndexOutOfBoundsException("expected: " + "0 <= start(" + start + ") <= start + length(" + length
                            + ") <= " + "value.length(" + value.length + ')');
        }

        for (int i = 0, j = start; i < length; i++, j++) {
            this.value[i] = c2b(value[j]);
        }
    }

    public AsciiString(CharSequence value) {
        this(checkNotNull(value, "value"), 0, value.length());
    }

    public AsciiString(CharSequence value, int start, int length) {
        super(length);
        if (start < 0 || length < 0 || length > checkNotNull(value, "value").length() - start) {
            throw new IndexOutOfBoundsException("expected: " + "0 <= start(" + start + ") <= start + length(" + length
                            + ") <= " + "value.length(" + value.length() + ')');
        }

        for (int i = 0, j = start; i < length; i++, j++) {
            this.value[i] = c2b(value.charAt(j));
        }
    }

    @Override
    public char charAt(int index) {
        return b2c(byteAt(index));
    }

    @Override
    public void arrayChanged() {
        string = null;
        super.arrayChanged();
    }

    private static byte c2b(char c) {
        if (c > MAX_CHAR_VALUE) {
            return '?';
        }
        return (byte) c;
    }

    private static char b2c(byte b) {
        return (char) (b & 0xFF);
    }

    private static byte toLowerCase(byte b) {
        if ('A' <= b && b <= 'Z') {
            return (byte) (b + UPPER_CASE_TO_LOWER_CASE_ASCII_OFFSET);
        }
        return b;
    }

    private static char toLowerCase(char c) {
        if ('A' <= c && c <= 'Z') {
            return (char) (c + UPPER_CASE_TO_LOWER_CASE_ASCII_OFFSET);
        }
        return c;
    }

    private static byte toUpperCase(byte b) {
        if ('a' <= b && b <= 'z') {
            return (byte) (b - UPPER_CASE_TO_LOWER_CASE_ASCII_OFFSET);
        }
        return b;
    }

    @Override
    public String toString(Charset charset, int start, int end) {
        if (start == 0 && end == length()) {
            if (string == null) {
                string = super.toString(charset, start, end);
            }
            return string;
        }

        return super.toString(charset, start, end);
    }

    /**
     * Compares the specified string to this string using the ASCII values of the characters. Returns 0 if the strings
     * contain the same characters in the same order. Returns a negative integer if the first non-equal character in
     * this string has an ASCII value which is less than the ASCII value of the character at the same position in the
     * specified string, or if this string is a prefix of the specified string. Returns a positive integer if the first
     * non-equal character in this string has a ASCII value which is greater than the ASCII value of the character at
     * the same position in the specified string, or if the specified string is a prefix of this string.
     *
     * @param string the string to compare.
     * @return 0 if the strings are equal, a negative integer if this string is before the specified string, or a
     *         positive integer if this string is after the specified string.
     * @throws NullPointerException if {@code string} is {@code null}.
     */
    @Override
    public int compareTo(CharSequence string) {
        if (this == string) {
            return 0;
        }

        int result;
        int length1 = length();
        int length2 = string.length();
        int minLength = Math.min(length1, length2);
        for (int i = 0, j = arrayOffset(); i < minLength; i++, j++) {
            result = b2c(value[j]) - string.charAt(i);
            if (result != 0) {
                return result;
            }
        }

        return length1 - length2;
    }

    /**
     * Compares the specified string to this string using the ASCII values of the characters, ignoring case differences.
     * Returns 0 if the strings contain the same characters in the same order. Returns a negative integer if the first
     * non-equal character in this string has an ASCII value which is less than the ASCII value of the character at the
     * same position in the specified string, or if this string is a prefix of the specified string. Returns a positive
     * integer if the first non-equal character in this string has an ASCII value which is greater than the ASCII value
     * of the character at the same position in the specified string, or if the specified string is a prefix of this
     * string.
     *
     * @param string the string to compare.
     * @return 0 if the strings are equal, a negative integer if this string is before the specified string, or a
     *         positive integer if this string is after the specified string.
     * @throws NullPointerException if {@code string} is {@code null}.
     */
    public int compareToIgnoreCase(CharSequence string) {
        return CHARSEQUENCE_CASE_INSENSITIVE_ORDER.compare(this, string);
    }

    /**
     * Concatenates this string and the specified string.
     *
     * @param string the string to concatenate
     * @return a new string which is the concatenation of this string and the specified string.
     */
    public AsciiString concat(CharSequence string) {
        int thisLen = length();
        int thatLen = string.length();
        if (thatLen == 0) {
            return this;
        }

        if (string instanceof AsciiString) {
            AsciiString that = (AsciiString) string;
            if (isEmpty()) {
                return that;
            }

            byte[] newValue = new byte[thisLen + thatLen];
            System.arraycopy(value, arrayOffset(), newValue, 0, thisLen);
            System.arraycopy(that.value, that.arrayOffset(), newValue, thisLen, thatLen);
            return new AsciiString(newValue, false);
        }

        if (isEmpty()) {
            return new AsciiString(string);
        }

        byte[] newValue = new byte[thisLen + thatLen];
        System.arraycopy(value, arrayOffset(), newValue, 0, thisLen);
        for (int i = thisLen, j = 0; i < newValue.length; i++, j++) {
            newValue[i] = c2b(string.charAt(j));
        }

        return new AsciiString(newValue, false);
    }

    /**
     * Compares the specified string to this string to determine if the specified string is a suffix.
     *
     * @param suffix the suffix to look for.
     * @return {@code true} if the specified string is a suffix of this string, {@code false} otherwise.
     * @throws NullPointerException if {@code suffix} is {@code null}.
     */
    public boolean endsWith(CharSequence suffix) {
        int suffixLen = suffix.length();
        return regionMatches(length() - suffixLen, suffix, 0, suffixLen);
    }

    /**
     * Compares the specified string to this string ignoring the case of the characters and returns true if they are
     * equal.
     *
     * @param string the string to compare.
     * @return {@code true} if the specified string is equal to this string, {@code false} otherwise.
     */
    public boolean equalsIgnoreCase(CharSequence string) {
        if (string == this) {
            return true;
        }

        if (string == null) {
            return false;
        }

        final int thisLen = value.length;
        final int thatLen = string.length();
        if (thisLen != thatLen) {
            return false;
        }

        for (int i = 0, j = arrayOffset(); i < thisLen; i++, j++) {
            char c1 = b2c(value[j]);
            char c2 = string.charAt(i);
            if (c1 != c2 && toLowerCase(c1) != toLowerCase(c2)) {
                return false;
            }
        }
        return true;
    }

    /**
     * Copies the characters in this string to a character array.
     *
     * @return a character array containing the characters of this string.
     */
    public char[] toCharArray() {
        return toCharArray(0, length());
    }

    /**
     * Copies the characters in this string to a character array.
     *
     * @return a character array containing the characters of this string.
     */
    public char[] toCharArray(int start, int end) {
        int length = end - start;
        if (length == 0) {
            return EmptyArrays.EMPTY_CHARS;
        }

        if (start < 0 || length > length() - start) {
            throw new IndexOutOfBoundsException("expected: " + "0 <= start(" + start + ") <= srcIdx + length("
                            + length + ") <= srcLen(" + length() + ')');
        }

        final char[] buffer = new char[length];
        for (int i = 0, j = start + arrayOffset(); i < length; i++, j++) {
            buffer[i] = b2c(value[j]);
        }
        return buffer;
    }

    /**
     * Copied the content of this string to a character array.
     *
     * @param srcIdx the starting offset of characters to copy.
     * @param dst the destination character array.
     * @param dstIdx the starting offset in the destination byte array.
     * @param length the number of characters to copy.
     */
    public void copy(int srcIdx, char[] dst, int dstIdx, int length) {
        if (dst == null) {
            throw new NullPointerException("dst");
        }

        if (srcIdx < 0 || length > length() - srcIdx) {
            throw new IndexOutOfBoundsException("expected: " + "0 <= srcIdx(" + srcIdx + ") <= srcIdx + length("
                            + length + ") <= srcLen(" + length() + ')');
        }

        final int dstEnd = dstIdx + length;
        for (int i = dstIdx, j = srcIdx + arrayOffset(); i < dstEnd; i++, j++) {
            dst[i] = b2c(value[j]);
        }
    }

    @Override
    public AsciiString subSequence(int start) {
        return subSequence(start, length());
    }

    @Override
    public AsciiString subSequence(int start, int end) {
       return subSequence(start, end, true);
    }

    @Override
    public AsciiString subSequence(int start, int end, boolean copy) {
        return (AsciiString) super.subSequence(start, end, copy, DEFAULT_FACTORY);
    }

    /**
     * Searches in this string for the first index of the specified string. The search for the string starts at the
     * beginning and moves towards the end of this string.
     *
     * @param string the string to find.
     * @return the index of the first character of the specified string in this string, -1 if the specified string is
     *         not a substring.
     * @throws NullPointerException if {@code string} is {@code null}.
     */
    public int indexOf(CharSequence string) {
        return indexOf(string, 0);
    }

    /**
     * Searches in this string for the index of the specified string. The search for the string starts at the specified
     * offset and moves towards the end of this string.
     *
     * @param subString the string to find.
     * @param start the starting offset.
     * @return the index of the first character of the specified string in this string, -1 if the specified string is
     *         not a substring.
     * @throws NullPointerException if {@code subString} is {@code null}.
     */
    public int indexOf(CharSequence subString, int start) {
        if (start < 0) {
            start = 0;
        }

        final int thisLen = length();

        int subCount = subString.length();
        if (subCount <= 0) {
            return start < thisLen ? start : thisLen;
        }
        if (subCount > thisLen - start) {
            return -1;
        }

        final char firstChar = subString.charAt(0);
        if (firstChar > MAX_CHAR_VALUE) {
            return -1;
        }
        ByteProcessor IndexOfVisitor = new IndexOfProcessor((byte) firstChar);
        try {
            for (;;) {
                int i = forEachByte(start, thisLen - start, IndexOfVisitor);
                if (i == -1 || subCount + i > thisLen) {
                    return -1; // handles subCount > count || start >= count
                }
                int o1 = i, o2 = 0;
                while (++o2 < subCount && b2c(value[++o1 + arrayOffset()]) == subString.charAt(o2)) {
                    // Intentionally empty
                }
                if (o2 == subCount) {
                    return i;
                }
                start = i + 1;
            }
        } catch (Exception e) {
            PlatformDependent.throwException(e);
            return -1;
        }
    }

    /**
     * Searches in this string for the last index of the specified string. The search for the string starts at the end
     * and moves towards the beginning of this string.
     *
     * @param string the string to find.
     * @return the index of the first character of the specified string in this string, -1 if the specified string is
     *         not a substring.
     * @throws NullPointerException if {@code string} is {@code null}.
     */
    public int lastIndexOf(CharSequence string) {
        // Use count instead of count - 1 so lastIndexOf("") answers count
        return lastIndexOf(string, length());
    }

    /**
     * Searches in this string for the index of the specified string. The search for the string starts at the specified
     * offset and moves towards the beginning of this string.
     *
     * @param subString the string to find.
     * @param start the starting offset.
     * @return the index of the first character of the specified string in this string , -1 if the specified string is
     *         not a substring.
     * @throws NullPointerException if {@code subString} is {@code null}.
     */
    public int lastIndexOf(CharSequence subString, int start) {
        final int thisLen = length();
        final int subCount = subString.length();

        if (subCount > thisLen || start < 0) {
            return -1;
        }

        if (subCount <= 0) {
            return start < thisLen ? start : thisLen;
        }

        start = Math.min(start, thisLen - subCount);

        // count and subCount are both >= 1
        final char firstChar = subString.charAt(0);
        if (firstChar > MAX_CHAR_VALUE) {
            return -1;
        }
        ByteProcessor IndexOfVisitor = new IndexOfProcessor((byte) firstChar);
        try {
            for (;;) {
                int i = forEachByteDesc(start, thisLen - start, IndexOfVisitor);
                if (i == -1) {
                    return -1;
                }
                int o1 = i, o2 = 0;
                while (++o2 < subCount && b2c(value[++o1 + arrayOffset()]) == subString.charAt(o2)) {
                    // Intentionally empty
                }
                if (o2 == subCount) {
                    return i;
                }
                start = i - 1;
            }
        } catch (Exception e) {
            PlatformDependent.throwException(e);
            return -1;
        }
    }

    /**
     * Compares the specified string to this string and compares the specified range of characters to determine if they
     * are the same.
     *
     * @param thisStart the starting offset in this string.
     * @param string the string to compare.
     * @param start the starting offset in the specified string.
     * @param length the number of characters to compare.
     * @return {@code true} if the ranges of characters are equal, {@code false} otherwise
     * @throws NullPointerException if {@code string} is {@code null}.
     */
    public boolean regionMatches(int thisStart, CharSequence string, int start, int length) {
        if (string == null) {
            throw new NullPointerException("string");
        }

        if (start < 0 || string.length() - start < length) {
            return false;
        }

        final int thisLen = length();
        if (thisStart < 0 || thisLen - thisStart < length) {
            return false;
        }

        if (length <= 0) {
            return true;
        }

        final int thatEnd = start + length;
        for (int i = start, j = thisStart + arrayOffset(); i < thatEnd; i++, j++) {
            if (b2c(value[j]) != string.charAt(i)) {
                return false;
            }
        }
        return true;
    }

    /**
     * Compares the specified string to this string and compares the specified range of characters to determine if they
     * are the same. When ignoreCase is true, the case of the characters is ignored during the comparison.
     *
     * @param ignoreCase specifies if case should be ignored.
     * @param thisStart the starting offset in this string.
     * @param string the string to compare.
     * @param start the starting offset in the specified string.
     * @param length the number of characters to compare.
     * @return {@code true} if the ranges of characters are equal, {@code false} otherwise.
     * @throws NullPointerException if {@code string} is {@code null}.
     */
    public boolean regionMatches(boolean ignoreCase, int thisStart, CharSequence string, int start, int length) {
        if (!ignoreCase) {
            return regionMatches(thisStart, string, start, length);
        }

        if (string == null) {
            throw new NullPointerException("string");
        }

        final int thisLen = length();
        if (thisStart < 0 || length > thisLen - thisStart) {
            return false;
        }
        if (start < 0 || length > string.length() - start) {
            return false;
        }

        thisStart += arrayOffset();
        final int thisEnd = thisStart + length;
        while (thisStart < thisEnd) {
            char c1 = b2c(value[thisStart++]);
            char c2 = string.charAt(start++);
            if (c1 != c2 && toLowerCase(c1) != toLowerCase(c2)) {
                return false;
            }
        }
        return true;
    }

    /**
     * Copies this string replacing occurrences of the specified character with another character.
     *
     * @param oldChar the character to replace.
     * @param newChar the replacement character.
     * @return a new string with occurrences of oldChar replaced by newChar.
     */
    public AsciiString replace(char oldChar, char newChar) {
        if (oldChar > MAX_CHAR_VALUE) {
            return this;
        }

        final int index;
        final byte oldCharByte = c2b(oldChar);
        try {
            index = forEachByte(new IndexOfProcessor(oldCharByte));
        } catch (Exception e) {
            PlatformDependent.throwException(e);
            return this;
        }
        if (index == -1) {
            return this;
        }

        final byte newCharByte = c2b(newChar);
        byte[] buffer = new byte[length()];
        for (int i = 0, j = arrayOffset(); i < buffer.length; i++, j++) {
            byte b = value[j];
            if (b == oldCharByte) {
                b = newCharByte;
            }
            buffer[i] = b;
        }

        return new AsciiString(buffer, false);
    }

    /**
     * Compares the specified string to this string to determine if the specified string is a prefix.
     *
     * @param prefix the string to look for.
     * @return {@code true} if the specified string is a prefix of this string, {@code false} otherwise
     * @throws NullPointerException if {@code prefix} is {@code null}.
     */
    public boolean startsWith(CharSequence prefix) {
        return startsWith(prefix, 0);
    }

    /**
     * Compares the specified string to this string, starting at the specified offset, to determine if the specified
     * string is a prefix.
     *
     * @param prefix the string to look for.
     * @param start the starting offset.
     * @return {@code true} if the specified string occurs in this string at the specified offset, {@code false}
     *         otherwise.
     * @throws NullPointerException if {@code prefix} is {@code null}.
     */
    public boolean startsWith(CharSequence prefix, int start) {
        return regionMatches(start, prefix, 0, prefix.length());
    }

    /**
     * Converts the characters in this string to lowercase, using the default Locale.
     *
     * @return a new string containing the lowercase characters equivalent to the characters in this string.
     */
    public AsciiString toLowerCase() {
        boolean lowercased = true;
        int i, j;
        final int len = length() + arrayOffset();
        for (i = arrayOffset(); i < len; ++i) {
            byte b = value[i];
            if (b >= 'A' && b <= 'Z') {
                lowercased = false;
                break;
            }
        }

        // Check if this string does not contain any uppercase characters.
        if (lowercased) {
            return this;
        }

        final byte[] newValue = new byte[length()];
        for (i = 0, j = arrayOffset(); i < newValue.length; ++i, ++j) {
            newValue[i] = toLowerCase(value[j]);
        }

        return new AsciiString(newValue, false);
    }

    /**
     * Converts the characters in this string to uppercase, using the default Locale.
     *
     * @return a new string containing the uppercase characters equivalent to the characters in this string.
     */
    public AsciiString toUpperCase() {
        boolean uppercased = true;
        int i, j;
        final int len = length() + arrayOffset();
        for (i = arrayOffset(); i < len; ++i) {
            byte b = value[i];
            if (b >= 'a' && b <= 'z') {
                uppercased = false;
                break;
            }
        }

        // Check if this string does not contain any lowercase characters.
        if (uppercased) {
            return this;
        }

        final byte[] newValue = new byte[length()];
        for (i = 0, j = arrayOffset(); i < newValue.length; ++i, ++j) {
            newValue[i] = toUpperCase(value[j]);
        }

        return new AsciiString(newValue, false);
    }

    /**
     * Copies this string removing white space characters from the beginning and end of the string.
     *
     * @return a new string with characters {@code <= \\u0020} removed from the beginning and the end.
     */
    public AsciiString trim() {
        int start = arrayOffset(), last = arrayOffset() + length();
        int end = last;
        while (start <= end && value[start] <= ' ') {
            start++;
        }
        while (end >= start && value[end] <= ' ') {
            end--;
        }
        if (start == 0 && end == last) {
            return this;
        }
        return new AsciiString(value, start, end - start + 1, false);
    }

    /**
     * Compares a {@code CharSequence} to this {@code String} to determine if their contents are equal.
     *
     * @param cs the character sequence to compare to.
     * @return {@code true} if equal, otherwise {@code false}
     */
    public boolean contentEquals(CharSequence cs) {
        if (cs == null) {
            throw new NullPointerException();
        }

        int length1 = length();
        int length2 = cs.length();
        if (length1 != length2) {
            return false;
        } else if (length1 == 0) {
            return true; // since both are empty strings
        }

        return regionMatches(0, cs, 0, length2);
    }

    /**
     * Determines whether this string matches a given regular expression.
     *
     * @param expr the regular expression to be matched.
     * @return {@code true} if the expression matches, otherwise {@code false}.
     * @throws PatternSyntaxException if the syntax of the supplied regular expression is not valid.
     * @throws NullPointerException if {@code expr} is {@code null}.
     */
    public boolean matches(String expr) {
        return Pattern.matches(expr, this);
    }

    /**
     * Splits this string using the supplied regular expression {@code expr}. The parameter {@code max} controls the
     * behavior how many times the pattern is applied to the string.
     *
     * @param expr the regular expression used to divide the string.
     * @param max the number of entries in the resulting array.
     * @return an array of Strings created by separating the string along matches of the regular expression.
     * @throws NullPointerException if {@code expr} is {@code null}.
     * @throws PatternSyntaxException if the syntax of the supplied regular expression is not valid.
     * @see Pattern#split(CharSequence, int)
     */
    public AsciiString[] split(String expr, int max) {
        return toAsciiStringArray(Pattern.compile(expr).split(this, max));
    }

    private static AsciiString[] toAsciiStringArray(String[] jdkResult) {
        AsciiString[] res = new AsciiString[jdkResult.length];
        for (int i = 0; i < jdkResult.length; i++) {
            res[i] = new AsciiString(jdkResult[i]);
        }
        return res;
    }

    /**
     * Splits the specified {@link String} with the specified delimiter..
     */
    public AsciiString[] split(char delim) {
        final List<AsciiString> res = new ArrayList<AsciiString>();

        int start = 0;
        final int length = length();
        for (int i = start; i < length; i++) {
            if (charAt(i) == delim) {
                if (start == i) {
                    res.add(EMPTY_STRING);
                } else {
                    res.add(new AsciiString(value, start + arrayOffset(), i - start, false));
                }
                start = i + 1;
            }
        }

        if (start == 0) { // If no delimiter was found in the value
            res.add(this);
        } else {
            if (start != length) {
                // Add the last element if it's not empty.
                res.add(new AsciiString(value, start + arrayOffset(), length - start, false));
            } else {
                // Truncate trailing empty elements.
                for (int i = res.size() - 1; i >= 0; i--) {
                    if (res.get(i).isEmpty()) {
                        res.remove(i);
                    } else {
                        break;
                    }
                }
            }
        }

        return res.toArray(new AsciiString[res.size()]);
    }

    /**
     * Determines if this {@code String} contains the sequence of characters in the {@code CharSequence} passed.
     *
     * @param cs the character sequence to search for.
     * @return {@code true} if the sequence of characters are contained in this string, otherwise {@code false}.
     */
    public boolean contains(CharSequence cs) {
        if (cs == null) {
            throw new NullPointerException();
        }
        return indexOf(cs) >= 0;
    }
}


File: example/src/main/java/io/netty/example/http/upload/HttpUploadClient.java
/*
 * Copyright 2012 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */
package io.netty.example.http.upload;

import io.netty.bootstrap.Bootstrap;
import io.netty.channel.Channel;
import io.netty.channel.ChannelFuture;
import io.netty.channel.EventLoopGroup;
import io.netty.channel.nio.NioEventLoopGroup;
import io.netty.channel.socket.nio.NioSocketChannel;
import io.netty.handler.codec.http.DefaultHttpRequest;
import io.netty.handler.codec.http.HttpHeaderNames;
import io.netty.handler.codec.http.HttpHeaderValues;
import io.netty.handler.codec.http.HttpHeaders;
import io.netty.handler.codec.http.HttpMethod;
import io.netty.handler.codec.http.HttpRequest;
import io.netty.handler.codec.http.HttpVersion;
import io.netty.handler.codec.http.QueryStringEncoder;
import io.netty.handler.codec.http.cookie.ClientCookieEncoder;
import io.netty.handler.codec.http.cookie.DefaultCookie;
import io.netty.handler.codec.http.multipart.DefaultHttpDataFactory;
import io.netty.handler.codec.http.multipart.DiskAttribute;
import io.netty.handler.codec.http.multipart.DiskFileUpload;
import io.netty.handler.codec.http.multipart.HttpDataFactory;
import io.netty.handler.codec.http.multipart.HttpPostRequestEncoder;
import io.netty.handler.codec.http.multipart.InterfaceHttpData;
import io.netty.handler.ssl.SslContext;
import io.netty.handler.ssl.SslContextBuilder;
import io.netty.handler.ssl.util.InsecureTrustManagerFactory;

import java.io.File;
import java.io.FileNotFoundException;
import java.net.InetSocketAddress;
import java.net.URI;
import java.util.List;
import java.util.Map.Entry;

/**
 * This class is meant to be run against {@link HttpUploadServer}.
 */
public final class HttpUploadClient {

    static final String BASE_URL = System.getProperty("baseUrl", "http://127.0.0.1:8080/");
    static final String FILE = System.getProperty("file", "upload.txt");

    public static void main(String[] args) throws Exception {
        String postSimple, postFile, get;
        if (BASE_URL.endsWith("/")) {
            postSimple = BASE_URL + "formpost";
            postFile = BASE_URL + "formpostmultipart";
            get = BASE_URL + "formget";
        } else {
            postSimple = BASE_URL + "/formpost";
            postFile = BASE_URL + "/formpostmultipart";
            get = BASE_URL + "/formget";
        }

        URI uriSimple = new URI(postSimple);
        String scheme = uriSimple.getScheme() == null? "http" : uriSimple.getScheme();
        String host = uriSimple.getHost() == null? "127.0.0.1" : uriSimple.getHost();
        int port = uriSimple.getPort();
        if (port == -1) {
            if ("http".equalsIgnoreCase(scheme)) {
                port = 80;
            } else if ("https".equalsIgnoreCase(scheme)) {
                port = 443;
            }
        }

        if (!"http".equalsIgnoreCase(scheme) && !"https".equalsIgnoreCase(scheme)) {
            System.err.println("Only HTTP(S) is supported.");
            return;
        }

        final boolean ssl = "https".equalsIgnoreCase(scheme);
        final SslContext sslCtx;
        if (ssl) {
            sslCtx = SslContextBuilder.forClient()
                .trustManager(InsecureTrustManagerFactory.INSTANCE).build();
        } else {
            sslCtx = null;
        }

        URI uriFile = new URI(postFile);
        File file = new File(FILE);
        if (!file.canRead()) {
            throw new FileNotFoundException(FILE);
        }

        // Configure the client.
        EventLoopGroup group = new NioEventLoopGroup();

        // setup the factory: here using a mixed memory/disk based on size threshold
        HttpDataFactory factory = new DefaultHttpDataFactory(DefaultHttpDataFactory.MINSIZE); // Disk if MINSIZE exceed

        DiskFileUpload.deleteOnExitTemporaryFile = true; // should delete file on exit (in normal exit)
        DiskFileUpload.baseDirectory = null; // system temp directory
        DiskAttribute.deleteOnExitTemporaryFile = true; // should delete file on exit (in normal exit)
        DiskAttribute.baseDirectory = null; // system temp directory

        try {
            Bootstrap b = new Bootstrap();
            b.group(group).channel(NioSocketChannel.class).handler(new HttpUploadClientIntializer(sslCtx));

            // Simple Get form: no factory used (not usable)
            List<Entry<String, String>> headers = formget(b, host, port, get, uriSimple);
            if (headers == null) {
                factory.cleanAllHttpData();
                return;
            }

            // Simple Post form: factory used for big attributes
            List<InterfaceHttpData> bodylist = formpost(b, host, port, uriSimple, file, factory, headers);
            if (bodylist == null) {
                factory.cleanAllHttpData();
                return;
            }

            // Multipart Post form: factory used
            formpostmultipart(b, host, port, uriFile, factory, headers, bodylist);
        } finally {
            // Shut down executor threads to exit.
            group.shutdownGracefully();

            // Really clean all temporary files if they still exist
            factory.cleanAllHttpData();
        }
    }

    /**
     * Standard usage of HTTP API in Netty without file Upload (get is not able to achieve File upload
     * due to limitation on request size).
     *
     * @return the list of headers that will be used in every example after
     **/
    private static List<Entry<String, String>> formget(
            Bootstrap bootstrap, String host, int port, String get, URI uriSimple) throws Exception {
        // XXX /formget
        // No use of HttpPostRequestEncoder since not a POST
        Channel channel = bootstrap.connect(host, port).sync().channel();

        // Prepare the HTTP request.
        QueryStringEncoder encoder = new QueryStringEncoder(get);
        // add Form attribute
        encoder.addParam("getform", "GET");
        encoder.addParam("info", "first value");
        encoder.addParam("secondinfo", "secondvalue ���&");
        // not the big one since it is not compatible with GET size
        // encoder.addParam("thirdinfo", textArea);
        encoder.addParam("thirdinfo", "third value\r\ntest second line\r\n\r\nnew line\r\n");
        encoder.addParam("Send", "Send");

        URI uriGet = new URI(encoder.toString());
        HttpRequest request = new DefaultHttpRequest(HttpVersion.HTTP_1_1, HttpMethod.GET, uriGet.toASCIIString());
        HttpHeaders headers = request.headers();
        headers.set(HttpHeaderNames.HOST, host);
        headers.set(HttpHeaderNames.CONNECTION, HttpHeaderValues.CLOSE);
        headers.set(HttpHeaderNames.ACCEPT_ENCODING, HttpHeaderValues.GZIP + "," + HttpHeaderValues.DEFLATE);

        headers.set(HttpHeaderNames.ACCEPT_CHARSET, "ISO-8859-1,utf-8;q=0.7,*;q=0.7");
        headers.set(HttpHeaderNames.ACCEPT_LANGUAGE, "fr");
        headers.set(HttpHeaderNames.REFERER, uriSimple.toString());
        headers.set(HttpHeaderNames.USER_AGENT, "Netty Simple Http Client side");
        headers.set(HttpHeaderNames.ACCEPT, "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8");

        //connection will not close but needed
        // headers.set("Connection","keep-alive");

        headers.set(
                HttpHeaderNames.COOKIE, ClientCookieEncoder.STRICT.encode(
                        new DefaultCookie("my-cookie", "foo"),
                        new DefaultCookie("another-cookie", "bar"))
        );

        // send request
        List<Entry<String, String>> entries = headers.entriesConverted();
        channel.writeAndFlush(request);

        // Wait for the server to close the connection.
        channel.closeFuture().sync();

        return entries;
    }

    /**
     * Standard post without multipart but already support on Factory (memory management)
     *
     * @return the list of HttpData object (attribute and file) to be reused on next post
     */
    private static List<InterfaceHttpData> formpost(
            Bootstrap bootstrap,
            String host, int port, URI uriSimple, File file, HttpDataFactory factory,
            List<Entry<String, String>> headers) throws Exception {
        // XXX /formpost
        // Start the connection attempt.
        ChannelFuture future = bootstrap.connect(new InetSocketAddress(host, port));
        // Wait until the connection attempt succeeds or fails.
        Channel channel = future.sync().channel();

        // Prepare the HTTP request.
        HttpRequest request = new DefaultHttpRequest(HttpVersion.HTTP_1_1, HttpMethod.POST, uriSimple.toASCIIString());

        // Use the PostBody encoder
        HttpPostRequestEncoder bodyRequestEncoder =
                new HttpPostRequestEncoder(factory, request, false);  // false => not multipart

        // it is legal to add directly header or cookie into the request until finalize
        for (Entry<String, String> entry : headers) {
            request.headers().set(entry.getKey(), entry.getValue());
        }

        // add Form attribute
        bodyRequestEncoder.addBodyAttribute("getform", "POST");
        bodyRequestEncoder.addBodyAttribute("info", "first value");
        bodyRequestEncoder.addBodyAttribute("secondinfo", "secondvalue ���&");
        bodyRequestEncoder.addBodyAttribute("thirdinfo", textArea);
        bodyRequestEncoder.addBodyAttribute("fourthinfo", textAreaLong);
        bodyRequestEncoder.addBodyFileUpload("myfile", file, "application/x-zip-compressed", false);

        // finalize request
        request = bodyRequestEncoder.finalizeRequest();

        // Create the bodylist to be reused on the last version with Multipart support
        List<InterfaceHttpData> bodylist = bodyRequestEncoder.getBodyListAttributes();

        // send request
        channel.write(request);

        // test if request was chunked and if so, finish the write
        if (bodyRequestEncoder.isChunked()) { // could do either request.isChunked()
            // either do it through ChunkedWriteHandler
            channel.write(bodyRequestEncoder);
        }
        channel.flush();

        // Do not clear here since we will reuse the InterfaceHttpData on the next request
        // for the example (limit action on client side). Take this as a broadcast of the same
        // request on both Post actions.
        //
        // On standard program, it is clearly recommended to clean all files after each request
        // bodyRequestEncoder.cleanFiles();

        // Wait for the server to close the connection.
        channel.closeFuture().sync();
        return bodylist;
    }

    /**
     * Multipart example
     */
    private static void formpostmultipart(
            Bootstrap bootstrap, String host, int port, URI uriFile, HttpDataFactory factory,
            List<Entry<String, String>> headers, List<InterfaceHttpData> bodylist) throws Exception {
        // XXX /formpostmultipart
        // Start the connection attempt.
        ChannelFuture future = bootstrap.connect(new InetSocketAddress(host, port));
        // Wait until the connection attempt succeeds or fails.
        Channel channel = future.sync().channel();

        // Prepare the HTTP request.
        HttpRequest request = new DefaultHttpRequest(HttpVersion.HTTP_1_1, HttpMethod.POST, uriFile.toASCIIString());

        // Use the PostBody encoder
        HttpPostRequestEncoder bodyRequestEncoder =
                new HttpPostRequestEncoder(factory, request, true); // true => multipart

        // it is legal to add directly header or cookie into the request until finalize
        for (Entry<String, String> entry : headers) {
            request.headers().set(entry.getKey(), entry.getValue());
        }

        // add Form attribute from previous request in formpost()
        bodyRequestEncoder.setBodyHttpDatas(bodylist);

        // finalize request
        bodyRequestEncoder.finalizeRequest();

        // send request
        channel.write(request);

        // test if request was chunked and if so, finish the write
        if (bodyRequestEncoder.isChunked()) {
            channel.write(bodyRequestEncoder);
        }
        channel.flush();

        // Now no more use of file representation (and list of HttpData)
        bodyRequestEncoder.cleanFiles();

        // Wait for the server to close the connection.
        channel.closeFuture().sync();
    }

    // use to simulate a small TEXTAREA field in a form
    private static final String textArea = "short text";
    // use to simulate a big TEXTAREA field in a form
    private static final String textAreaLong =
            "lkjlkjlKJLKJLKJLKJLJlkj lklkj\r\n\r\nLKJJJJJJJJKKKKKKKKKKKKKKK ����&\r\n\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n" +
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\n";
}
