Refactoring Types: ['Extract Method']
search/common/io/stream/StreamInput.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.common.io.stream;

import org.apache.lucene.util.BytesRef;
import org.apache.lucene.util.CharsRefBuilder;
import org.elasticsearch.Version;
import org.elasticsearch.common.Nullable;
import org.elasticsearch.common.Strings;
import org.elasticsearch.common.bytes.BytesArray;
import org.elasticsearch.common.bytes.BytesReference;
import org.elasticsearch.common.text.StringAndBytesText;
import org.elasticsearch.common.text.Text;
import org.joda.time.DateTime;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.ObjectInputStream;
import java.util.*;

/**
 *
 */
public abstract class StreamInput extends InputStream {

    private Version version = Version.CURRENT;

    public Version getVersion() {
        return this.version;
    }

    public StreamInput setVersion(Version version) {
        this.version = version;
        return this;
    }

    /**
     * Reads and returns a single byte.
     */
    public abstract byte readByte() throws IOException;

    /**
     * Reads a specified number of bytes into an array at the specified offset.
     *
     * @param b      the array to read bytes into
     * @param offset the offset in the array to start storing bytes
     * @param len    the number of bytes to read
     */
    public abstract void readBytes(byte[] b, int offset, int len) throws IOException;

    /**
     * Reads a bytes reference from this stream, might hold an actual reference to the underlying
     * bytes of the stream.
     */
    public BytesReference readBytesReference() throws IOException {
        int length = readVInt();
        return readBytesReference(length);
    }

    /**
     * Reads a bytes reference from this stream, might hold an actual reference to the underlying
     * bytes of the stream.
     */
    public BytesReference readBytesReference(int length) throws IOException {
        if (length == 0) {
            return BytesArray.EMPTY;
        }
        byte[] bytes = new byte[length];
        readBytes(bytes, 0, length);
        return new BytesArray(bytes, 0, length);
    }

    public BytesRef readBytesRef() throws IOException {
        int length = readVInt();
        return readBytesRef(length);
    }

    public BytesRef readBytesRef(int length) throws IOException {
        if (length == 0) {
            return new BytesRef();
        }
        byte[] bytes = new byte[length];
        readBytes(bytes, 0, length);
        return new BytesRef(bytes, 0, length);
    }

    public void readFully(byte[] b) throws IOException {
        readBytes(b, 0, b.length);
    }

    public short readShort() throws IOException {
        return (short) (((readByte() & 0xFF) << 8) | (readByte() & 0xFF));
    }

    /**
     * Reads four bytes and returns an int.
     */
    public int readInt() throws IOException {
        return ((readByte() & 0xFF) << 24) | ((readByte() & 0xFF) << 16)
                | ((readByte() & 0xFF) << 8) | (readByte() & 0xFF);
    }

    /**
     * Reads an int stored in variable-length format.  Reads between one and
     * five bytes.  Smaller values take fewer bytes.  Negative numbers
     * will always use all 5 bytes and are therefore better serialized
     * using {@link #readInt}
     */
    public int readVInt() throws IOException {
        byte b = readByte();
        int i = b & 0x7F;
        if ((b & 0x80) == 0) {
            return i;
        }
        b = readByte();
        i |= (b & 0x7F) << 7;
        if ((b & 0x80) == 0) {
            return i;
        }
        b = readByte();
        i |= (b & 0x7F) << 14;
        if ((b & 0x80) == 0) {
            return i;
        }
        b = readByte();
        i |= (b & 0x7F) << 21;
        if ((b & 0x80) == 0) {
            return i;
        }
        b = readByte();
        assert (b & 0x80) == 0;
        return i | ((b & 0x7F) << 28);
    }

    /**
     * Reads eight bytes and returns a long.
     */
    public long readLong() throws IOException {
        return (((long) readInt()) << 32) | (readInt() & 0xFFFFFFFFL);
    }

    /**
     * Reads a long stored in variable-length format.  Reads between one and
     * nine bytes.  Smaller values take fewer bytes.  Negative numbers are not
     * supported.
     */
    public long readVLong() throws IOException {
        byte b = readByte();
        long i = b & 0x7FL;
        if ((b & 0x80) == 0) {
            return i;
        }
        b = readByte();
        i |= (b & 0x7FL) << 7;
        if ((b & 0x80) == 0) {
            return i;
        }
        b = readByte();
        i |= (b & 0x7FL) << 14;
        if ((b & 0x80) == 0) {
            return i;
        }
        b = readByte();
        i |= (b & 0x7FL) << 21;
        if ((b & 0x80) == 0) {
            return i;
        }
        b = readByte();
        i |= (b & 0x7FL) << 28;
        if ((b & 0x80) == 0) {
            return i;
        }
        b = readByte();
        i |= (b & 0x7FL) << 35;
        if ((b & 0x80) == 0) {
            return i;
        }
        b = readByte();
        i |= (b & 0x7FL) << 42;
        if ((b & 0x80) == 0) {
            return i;
        }
        b = readByte();
        i |= (b & 0x7FL) << 49;
        if ((b & 0x80) == 0) {
            return i;
        }
        b = readByte();
        assert (b & 0x80) == 0;
        return i | ((b & 0x7FL) << 56);
    }

    @Nullable
    public Text readOptionalText() throws IOException {
        int length = readInt();
        if (length == -1) {
            return null;
        }
        return new StringAndBytesText(readBytesReference(length));
    }

    public Text readText() throws IOException {
        // use StringAndBytes so we can cache the string if its ever converted to it
        int length = readInt();
        return new StringAndBytesText(readBytesReference(length));
    }

    @Nullable
    public String readOptionalString() throws IOException {
        if (readBoolean()) {
            return readString();
        }
        return null;
    }

    @Nullable
    public Integer readOptionalVInt() throws IOException {
        if (readBoolean()) {
            return readVInt();
        }
        return null;
    }

    private final CharsRefBuilder spare = new CharsRefBuilder();

    public String readString() throws IOException {
        final int charCount = readVInt();
        spare.clear();
        spare.grow(charCount);
        int c = 0;
        while (spare.length() < charCount) {
            c = readByte() & 0xff;
            switch (c >> 4) {
                case 0:
                case 1:
                case 2:
                case 3:
                case 4:
                case 5:
                case 6:
                case 7:
                    spare.append((char) c);
                    break;
                case 12:
                case 13:
                    spare.append((char) ((c & 0x1F) << 6 | readByte() & 0x3F));
                    break;
                case 14:
                    spare.append((char) ((c & 0x0F) << 12 | (readByte() & 0x3F) << 6 | (readByte() & 0x3F) << 0));
                    break;
            }
        }
        return spare.toString();
    }


    public final float readFloat() throws IOException {
        return Float.intBitsToFloat(readInt());
    }

    public final double readDouble() throws IOException {
        return Double.longBitsToDouble(readLong());
    }

    /**
     * Reads a boolean.
     */
    public final boolean readBoolean() throws IOException {
        return readByte() != 0;
    }

    @Nullable
    public final Boolean readOptionalBoolean() throws IOException {
        byte val = readByte();
        if (val == 2) {
            return null;
        }
        if (val == 1) {
            return true;
        }
        return false;
    }

    /**
     * Resets the stream.
     */
    @Override
    public abstract void reset() throws IOException;

    /**
     * Closes the stream to further operations.
     */
    @Override
    public abstract void close() throws IOException;

//    // IS
//
//    @Override public int read() throws IOException {
//        return readByte();
//    }
//
//    // Here, we assume that we always can read the full byte array
//
//    @Override public int read(byte[] b, int off, int len) throws IOException {
//        readBytes(b, off, len);
//        return len;
//    }

    public String[] readStringArray() throws IOException {
        int size = readVInt();
        if (size == 0) {
            return Strings.EMPTY_ARRAY;
        }
        String[] ret = new String[size];
        for (int i = 0; i < size; i++) {
            ret[i] = readString();
        }
        return ret;
    }

    @Nullable
    public Map<String, Object> readMap() throws IOException {
        return (Map<String, Object>) readGenericValue();
    }

    @SuppressWarnings({"unchecked"})
    @Nullable
    public Object readGenericValue() throws IOException {
        byte type = readByte();
        switch (type) {
            case -1:
                return null;
            case 0:
                return readString();
            case 1:
                return readInt();
            case 2:
                return readLong();
            case 3:
                return readFloat();
            case 4:
                return readDouble();
            case 5:
                return readBoolean();
            case 6:
                int bytesSize = readVInt();
                byte[] value = new byte[bytesSize];
                readBytes(value, 0, bytesSize);
                return value;
            case 7:
                int size = readVInt();
                List list = new ArrayList(size);
                for (int i = 0; i < size; i++) {
                    list.add(readGenericValue());
                }
                return list;
            case 8:
                int size8 = readVInt();
                Object[] list8 = new Object[size8];
                for (int i = 0; i < size8; i++) {
                    list8[i] = readGenericValue();
                }
                return list8;
            case 9:
                int size9 = readVInt();
                Map map9 = new LinkedHashMap(size9);
                for (int i = 0; i < size9; i++) {
                    map9.put(readString(), readGenericValue());
                }
                return map9;
            case 10:
                int size10 = readVInt();
                Map map10 = new HashMap(size10);
                for (int i = 0; i < size10; i++) {
                    map10.put(readString(), readGenericValue());
                }
                return map10;
            case 11:
                return readByte();
            case 12:
                return new Date(readLong());
            case 13:
                return new DateTime(readLong());
            case 14:
                return readBytesReference();
            case 15:
                return readText();
            case 16:
                return readShort();
            case 17:
                return readIntArray();
            case 18:
                return readLongArray();
            case 19:
                return readFloatArray();
            case 20:
                return readDoubleArray();
            case 21:
                return readBytesRef();
            default:
                throw new IOException("Can't read unknown type [" + type + "]");
        }
    }

    public int[] readIntArray() throws IOException {
        int length = readVInt();
        int[] values = new int[length];
        for (int i = 0; i < length; i++) {
            values[i] = readInt();
        }
        return values;
    }

    public long[] readLongArray() throws IOException {
        int length = readVInt();
        long[] values = new long[length];
        for (int i = 0; i < length; i++) {
            values[i] = readLong();
        }
        return values;
    }

    public float[] readFloatArray() throws IOException {
        int length = readVInt();
        float[] values = new float[length];
        for (int i = 0; i < length; i++) {
            values[i] = readFloat();
        }
        return values;
    }

    public double[] readDoubleArray() throws IOException {
        int length = readVInt();
        double[] values = new double[length];
        for (int i = 0; i < length; i++) {
            values[i] = readDouble();
        }
        return values;
    }

    public byte[] readByteArray() throws IOException {
        int length = readVInt();
        byte[] values = new byte[length];
        for (int i = 0; i < length; i++) {
            values[i] = readByte();
        }
        return values;
    }

    /**
     * Serializes a potential null value.
     */
    public <T extends Streamable> T readOptionalStreamable(T streamable) throws IOException {
        if (readBoolean()) {
            streamable.readFrom(this);
            return streamable;
        } else {
            return null;
        }
    }

    public <T extends Throwable> T readThrowable() throws IOException {
        try {
            ObjectInputStream oin = new ObjectInputStream(this);
            return (T) oin.readObject();
        } catch (ClassNotFoundException e) {
            throw new IOException("failed to deserialize exception", e);
        }
    }

    public static StreamInput wrap(BytesReference reference) {
        if (reference.hasArray() == false) {
            reference = reference.toBytesArray();
        }
        return wrap(reference.array(), reference.arrayOffset(), reference.length());
    }

    public static StreamInput wrap(byte[] bytes) {
        return wrap(bytes, 0, bytes.length);
    }

    public static StreamInput wrap(byte[] bytes, int offset, int length) {
        return new InputStreamStreamInput(new ByteArrayInputStream(bytes, offset, length));
    }
}


File: core/src/main/java/org/elasticsearch/common/io/stream/StreamOutput.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.common.io.stream;

import org.apache.lucene.util.BytesRef;
import org.apache.lucene.util.BytesRefBuilder;
import org.elasticsearch.Version;
import org.elasticsearch.common.Nullable;
import org.elasticsearch.common.bytes.BytesReference;
import org.elasticsearch.common.text.Text;
import org.joda.time.ReadableInstant;

import java.io.IOException;
import java.io.ObjectOutputStream;
import java.io.OutputStream;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 *
 */
public abstract class StreamOutput extends OutputStream {

    private Version version = Version.CURRENT;

    public Version getVersion() {
        return this.version;
    }

    public StreamOutput setVersion(Version version) {
        this.version = version;
        return this;
    }

    public long position() throws IOException {
        throw new UnsupportedOperationException();
    }

    public void seek(long position) throws IOException {
        throw new UnsupportedOperationException();
    }

    /**
     * Writes a single byte.
     */
    public abstract void writeByte(byte b) throws IOException;

    /**
     * Writes an array of bytes.
     *
     * @param b the bytes to write
     */
    public void writeBytes(byte[] b) throws IOException {
        writeBytes(b, 0, b.length);
    }

    /**
     * Writes an array of bytes.
     *
     * @param b      the bytes to write
     * @param length the number of bytes to write
     */
    public void writeBytes(byte[] b, int length) throws IOException {
        writeBytes(b, 0, length);
    }

    /**
     * Writes an array of bytes.
     *
     * @param b      the bytes to write
     * @param offset the offset in the byte array
     * @param length the number of bytes to write
     */
    public abstract void writeBytes(byte[] b, int offset, int length) throws IOException;

    /**
     * Writes an array of bytes.
     *
     * @param b the bytes to write
     */
    public void writeByteArray(byte[] b) throws IOException {
        writeVInt(b.length);
        writeBytes(b, 0, b.length);
    }

    /**
     * Writes the bytes reference, including a length header.
     */
    public void writeBytesReference(@Nullable BytesReference bytes) throws IOException {
        if (bytes == null) {
            writeVInt(0);
            return;
        }
        writeVInt(bytes.length());
        bytes.writeTo(this);
    }

    public void writeBytesRef(BytesRef bytes) throws IOException {
        if (bytes == null) {
            writeVInt(0);
            return;
        }
        writeVInt(bytes.length);
        write(bytes.bytes, bytes.offset, bytes.length);
    }

    public final void writeShort(short v) throws IOException {
        writeByte((byte) (v >> 8));
        writeByte((byte) v);
    }

    /**
     * Writes an int as four bytes.
     */
    public void writeInt(int i) throws IOException {
        writeByte((byte) (i >> 24));
        writeByte((byte) (i >> 16));
        writeByte((byte) (i >> 8));
        writeByte((byte) i);
    }

    /**
     * Writes an int in a variable-length format.  Writes between one and
     * five bytes.  Smaller values take fewer bytes.  Negative numbers
     * will always use all 5 bytes and are therefore better serialized
     * using {@link #writeInt}
     */
    public void writeVInt(int i) throws IOException {
        while ((i & ~0x7F) != 0) {
            writeByte((byte) ((i & 0x7f) | 0x80));
            i >>>= 7;
        }
        writeByte((byte) i);
    }

    /**
     * Writes a long as eight bytes.
     */
    public void writeLong(long i) throws IOException {
        writeInt((int) (i >> 32));
        writeInt((int) i);
    }

    /**
     * Writes an long in a variable-length format.  Writes between one and nine
     * bytes.  Smaller values take fewer bytes.  Negative numbers are not
     * supported.
     */
    public void writeVLong(long i) throws IOException {
        assert i >= 0;
        while ((i & ~0x7F) != 0) {
            writeByte((byte) ((i & 0x7f) | 0x80));
            i >>>= 7;
        }
        writeByte((byte) i);
    }

    public void writeOptionalString(@Nullable String str) throws IOException {
        if (str == null) {
            writeBoolean(false);
        } else {
            writeBoolean(true);
            writeString(str);
        }
    }

    public void writeOptionalVInt(@Nullable Integer integer) throws IOException {
        if (integer == null) {
            writeBoolean(false);
        } else {
            writeBoolean(true);
            writeVInt(integer);
        }
    }

    public void writeOptionalText(@Nullable Text text) throws IOException {
        if (text == null) {
            writeInt(-1);
        } else {
            writeText(text);
        }
    }

    private final BytesRefBuilder spare = new BytesRefBuilder();

    public void writeText(Text text) throws IOException {
        if (!text.hasBytes()) {
            final String string = text.string();
            spare.copyChars(string);
            writeInt(spare.length());
            write(spare.bytes(), 0, spare.length());
        } else {
            BytesReference bytes = text.bytes();
            writeInt(bytes.length());
            bytes.writeTo(this);
        }
    }

    public void writeString(String str) throws IOException {
        int charCount = str.length();
        writeVInt(charCount);
        int c;
        for (int i = 0; i < charCount; i++) {
            c = str.charAt(i);
            if (c <= 0x007F) {
                writeByte((byte) c);
            } else if (c > 0x07FF) {
                writeByte((byte) (0xE0 | c >> 12 & 0x0F));
                writeByte((byte) (0x80 | c >> 6 & 0x3F));
                writeByte((byte) (0x80 | c >> 0 & 0x3F));
            } else {
                writeByte((byte) (0xC0 | c >> 6 & 0x1F));
                writeByte((byte) (0x80 | c >> 0 & 0x3F));
            }
        }
    }

    public void writeFloat(float v) throws IOException {
        writeInt(Float.floatToIntBits(v));
    }

    public void writeDouble(double v) throws IOException {
        writeLong(Double.doubleToLongBits(v));
    }


    private static byte ZERO = 0;
    private static byte ONE = 1;
    private static byte TWO = 2;

    /**
     * Writes a boolean.
     */
    public void writeBoolean(boolean b) throws IOException {
        writeByte(b ? ONE : ZERO);
    }

    public void writeOptionalBoolean(@Nullable Boolean b) throws IOException {
        if (b == null) {
            writeByte(TWO);
        } else {
            writeByte(b ? ONE : ZERO);
        }
    }

    /**
     * Forces any buffered output to be written.
     */
    @Override
    public abstract void flush() throws IOException;

    /**
     * Closes this stream to further operations.
     */
    @Override
    public abstract void close() throws IOException;

    public abstract void reset() throws IOException;

    @Override
    public void write(int b) throws IOException {
        writeByte((byte) b);
    }

    @Override
    public void write(byte[] b, int off, int len) throws IOException {
        writeBytes(b, off, len);
    }

    public void writeStringArray(String[] array) throws IOException {
        writeVInt(array.length);
        for (String s : array) {
            writeString(s);
        }
    }

    /**
     * Writes a string array, for nullable string, writes it as 0 (empty string).
     */
    public void writeStringArrayNullable(@Nullable String[] array) throws IOException {
        if (array == null) {
            writeVInt(0);
        } else {
            writeVInt(array.length);
            for (String s : array) {
                writeString(s);
            }
        }
    }

    public void writeMap(@Nullable Map<String, Object> map) throws IOException {
        writeGenericValue(map);
    }

    public void writeGenericValue(@Nullable Object value) throws IOException {
        if (value == null) {
            writeByte((byte) -1);
            return;
        }
        Class type = value.getClass();
        if (type == String.class) {
            writeByte((byte) 0);
            writeString((String) value);
        } else if (type == Integer.class) {
            writeByte((byte) 1);
            writeInt((Integer) value);
        } else if (type == Long.class) {
            writeByte((byte) 2);
            writeLong((Long) value);
        } else if (type == Float.class) {
            writeByte((byte) 3);
            writeFloat((Float) value);
        } else if (type == Double.class) {
            writeByte((byte) 4);
            writeDouble((Double) value);
        } else if (type == Boolean.class) {
            writeByte((byte) 5);
            writeBoolean((Boolean) value);
        } else if (type == byte[].class) {
            writeByte((byte) 6);
            writeVInt(((byte[]) value).length);
            writeBytes(((byte[]) value));
        } else if (value instanceof List) {
            writeByte((byte) 7);
            List list = (List) value;
            writeVInt(list.size());
            for (Object o : list) {
                writeGenericValue(o);
            }
        } else if (value instanceof Object[]) {
            writeByte((byte) 8);
            Object[] list = (Object[]) value;
            writeVInt(list.length);
            for (Object o : list) {
                writeGenericValue(o);
            }
        } else if (value instanceof Map) {
            if (value instanceof LinkedHashMap) {
                writeByte((byte) 9);
            } else {
                writeByte((byte) 10);
            }
            Map<String, Object> map = (Map<String, Object>) value;
            writeVInt(map.size());
            for (Map.Entry<String, Object> entry : map.entrySet()) {
                writeString(entry.getKey());
                writeGenericValue(entry.getValue());
            }
        } else if (type == Byte.class) {
            writeByte((byte) 11);
            writeByte((Byte) value);
        } else if (type == Date.class) {
            writeByte((byte) 12);
            writeLong(((Date) value).getTime());
        } else if (value instanceof ReadableInstant) {
            writeByte((byte) 13);
            writeLong(((ReadableInstant) value).getMillis());
        } else if (value instanceof BytesReference) {
            writeByte((byte) 14);
            writeBytesReference((BytesReference) value);
        } else if (value instanceof Text) {
            writeByte((byte) 15);
            writeText((Text) value);
        } else if (type == Short.class) {
            writeByte((byte) 16);
            writeShort((Short) value);
        } else if (type == int[].class) {
            writeByte((byte) 17);
            writeIntArray((int[]) value);
        } else if (type == long[].class) {
            writeByte((byte) 18);
            writeLongArray((long[]) value);
        } else if (type == float[].class) {
            writeByte((byte) 19);
            writeFloatArray((float[]) value);
        } else if (type == double[].class) {
            writeByte((byte) 20);
            writeDoubleArray((double[]) value);
        } else if (value instanceof BytesRef) {
            writeByte((byte) 21);
            writeBytesRef((BytesRef) value);
        } else {
            throw new IOException("Can't write type [" + type + "]");
        }
    }

    public void writeIntArray(int[] value) throws IOException {
        writeVInt(value.length);
        for (int i=0; i<value.length; i++) {
            writeInt(value[i]);
        }
    }

    public void writeLongArray(long[] value) throws IOException {
        writeVInt(value.length);
        for (int i=0; i<value.length; i++) {
            writeLong(value[i]);
        }
    }

    public void writeFloatArray(float[] value) throws IOException {
        writeVInt(value.length);
        for (int i=0; i<value.length; i++) {
            writeFloat(value[i]);
        }
    }

    public void writeDoubleArray(double[] value) throws IOException {
        writeVInt(value.length);
        for (int i=0; i<value.length; i++) {
            writeDouble(value[i]);
        }
    }

    /**
     * Serializes a potential null value.
     */
    public void writeOptionalStreamable(@Nullable Streamable streamable) throws IOException {
        if (streamable != null) {
            writeBoolean(true);
            streamable.writeTo(this);
        } else {
            writeBoolean(false);
        }
    }

    public void writeThrowable(Throwable throwable) throws IOException {
        ObjectOutputStream out = new ObjectOutputStream(this);
        out.writeObject(throwable);
        out.flush();
    }
}


File: core/src/main/java/org/elasticsearch/index/query/FQueryFilterParser.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.index.query;

import org.apache.lucene.search.ConstantScoreQuery;
import org.apache.lucene.search.Query;
import org.elasticsearch.common.inject.Inject;
import org.elasticsearch.common.xcontent.XContentParser;

import java.io.IOException;

/**
 * The "fquery" filter is the same as the {@link QueryFilterParser} except that it allows also to
 * associate a name with the query filter.
 */
@Deprecated
public class FQueryFilterParser extends BaseQueryParserTemp {

    @Inject
    public FQueryFilterParser() {
    }

    @Override
    public String[] names() {
        return new String[]{QueryFilterBuilder.FQUERY_NAME};
    }

    @Override
    public Query parse(QueryParseContext parseContext) throws IOException, QueryParsingException {
        XContentParser parser = parseContext.parser();

        Query query = null;
        boolean queryFound = false;

        String queryName = null;
        String currentFieldName = null;
        XContentParser.Token token;
        while ((token = parser.nextToken()) != XContentParser.Token.END_OBJECT) {
            if (token == XContentParser.Token.FIELD_NAME) {
                currentFieldName = parser.currentName();
            } else if (parseContext.isDeprecatedSetting(currentFieldName)) {
                // skip
            } else if (token == XContentParser.Token.START_OBJECT) {
                if ("query".equals(currentFieldName)) {
                    queryFound = true;
                    query = parseContext.parseInnerQuery();
                } else {
                    throw new QueryParsingException(parseContext, "[fquery] query does not support [" + currentFieldName + "]");
                }
            } else if (token.isValue()) {
                if ("_name".equals(currentFieldName)) {
                    queryName = parser.text();
                } else {
                    throw new QueryParsingException(parseContext, "[fquery] query does not support [" + currentFieldName + "]");
                }
            }
        }
        if (!queryFound) {
            throw new QueryParsingException(parseContext, "[fquery] requires 'query' element");
        }
        if (query == null) {
            return null;
        }
        query = new ConstantScoreQuery(query);
        if (queryName != null) {
            parseContext.addNamedQuery(queryName, query);
        }
        return query;
    }

    @Override
    public QueryFilterBuilder getBuilderPrototype() {
        return QueryFilterBuilder.PROTOTYPE;
    }
}


File: core/src/main/java/org/elasticsearch/index/query/QueryBuilder.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.index.query;

import org.apache.lucene.search.Query;
import org.elasticsearch.action.support.ToXContentToBytes;
import org.apache.lucene.util.BytesRef;
import org.elasticsearch.common.lucene.BytesRefs;
import org.elasticsearch.common.io.stream.StreamInput;
import org.elasticsearch.common.io.stream.StreamOutput;
import org.elasticsearch.common.io.stream.Writeable;
import org.elasticsearch.common.xcontent.XContentBuilder;
import org.elasticsearch.common.xcontent.XContentType;

import java.io.IOException;

/**
 * Base class for all classes producing lucene queries.
 * Supports conversion to BytesReference and creation of lucene Query objects.
 */
public abstract class QueryBuilder<QB extends QueryBuilder> extends ToXContentToBytes implements Writeable<QB> {

    protected QueryBuilder() {
        super(XContentType.JSON);
    }

    @Override
    public XContentBuilder toXContent(XContentBuilder builder, Params params) throws IOException {
        builder.startObject();
        doXContent(builder, params);
        builder.endObject();
        return builder;
    }

    /**
     * @return a unique name this query is identified with
     */
    public abstract String queryId();

    /**
     * Converts this QueryBuilder to a lucene {@link Query}
     * @param parseContext additional information needed to construct the queries
     * @return the {@link Query}
     * @throws QueryParsingException
     * @throws IOException
     */
    //norelease to be made abstract once all query builders override toQuery providing their own specific implementation.
    public Query toQuery(QueryParseContext parseContext) throws QueryParsingException, IOException {
        return parseContext.indexQueryParserService().queryParser(queryId()).parse(parseContext);
    }

    /**
     * Validate the query.
     * @return a {@link QueryValidationException} containing error messages, {@code null} if query is valid.
     * e.g. if fields that are needed to create the lucene query are missing.
     */
    public QueryValidationException validate() {
        // default impl does not validate, subclasses should override.
        //norelease to be possibly made abstract once all queries support validation
        return null;
    }

    protected abstract void doXContent(XContentBuilder builder, Params params) throws IOException;

    /**
     * This helper method checks if the object passed in is a string, if so it
     * converts it to a {@link BytesRef}.
     * @param obj the input object
     * @return the same input object or a {@link BytesRef} representation if input was of type string
     */
    protected static Object convertToBytesRefIfString(Object obj) {
        if (obj instanceof String) {
            return BytesRefs.toBytesRef(obj);
        }
        return obj;
    }

    /**
     * This helper method checks if the object passed in is a {@link BytesRef}, if so it
     * converts it to a utf8 string.
     * @param obj the input object
     * @return the same input object or a utf8 string if input was of type {@link BytesRef}
     */
    protected static Object convertToStringIfBytesRef(Object obj) {
        if (obj instanceof BytesRef) {
            return ((BytesRef) obj).utf8ToString();
        }
        return obj;
    }

    //norelease remove this once all builders implement readFrom themselves
    @Override
    public QB readFrom(StreamInput in) throws IOException {
        return null;
    }

    //norelease remove this once all builders implement writeTo themselves
    @Override
    public void writeTo(StreamOutput out) throws IOException {
    }
}


File: core/src/main/java/org/elasticsearch/index/query/QueryFilterBuilder.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.index.query;

import org.elasticsearch.common.xcontent.XContentBuilder;

import java.io.IOException;

/**
 * A filter that simply wraps a query.
 * @deprecated Useless now that queries and filters are merged: pass the
 *             query as a filter directly.
 */
@Deprecated
public class QueryFilterBuilder extends QueryBuilder {

    public static final String NAME = "query";

    // this query builder creates query parsed by FQueryFilterParser in case queryName is set
    public static final String FQUERY_NAME = "fquery";

    private final QueryBuilder queryBuilder;

    private String queryName;

    static final QueryFilterBuilder PROTOTYPE = new QueryFilterBuilder(null);

    /**
     * A filter that simply wraps a query.
     *
     * @param queryBuilder The query to wrap as a filter
     */
    public QueryFilterBuilder(QueryBuilder queryBuilder) {
        this.queryBuilder = queryBuilder;
    }

    /**
     * Sets the query name for the filter that can be used when searching for matched_filters per hit.
     */
    public QueryFilterBuilder queryName(String queryName) {
        this.queryName = queryName;
        return this;
    }

    @Override
    protected void doXContent(XContentBuilder builder, Params params) throws IOException {
        if (queryName == null) {
            builder.field(NAME);
            queryBuilder.toXContent(builder, params);
        } else {
            builder.startObject(FQUERY_NAME);
            builder.field("query");
            queryBuilder.toXContent(builder, params);
            if (queryName != null) {
                builder.field("_name", queryName);
            }
            builder.endObject();
        }
    }

    @Override
    public String queryId() {
        return NAME;
    }
}


File: core/src/main/java/org/elasticsearch/indices/query/IndicesQueriesModule.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.indices.query;

import com.google.common.collect.Sets;
import org.elasticsearch.common.geo.ShapesAvailability;
import org.elasticsearch.common.inject.AbstractModule;
import org.elasticsearch.common.inject.multibindings.Multibinder;
import org.elasticsearch.index.query.*;
import org.elasticsearch.index.query.functionscore.FunctionScoreQueryParser;

import java.util.Set;

public class IndicesQueriesModule extends AbstractModule {

    private Set<Class<? extends QueryParser>> queryParsersClasses = Sets.newHashSet();

    public synchronized IndicesQueriesModule addQuery(Class<? extends QueryParser> queryParser) {
        queryParsersClasses.add(queryParser);
        return this;
    }

    @Override
    protected void configure() {
        bind(IndicesQueriesRegistry.class).asEagerSingleton();

        Multibinder<QueryParser> qpBinders = Multibinder.newSetBinder(binder(), QueryParser.class);
        for (Class<? extends QueryParser> queryParser : queryParsersClasses) {
            qpBinders.addBinding().to(queryParser).asEagerSingleton();
        }
        qpBinders.addBinding().to(MatchQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(MultiMatchQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(NestedQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(HasChildQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(HasParentQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(DisMaxQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(IdsQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(MatchAllQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(QueryStringQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(BoostingQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(BoolQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(TermQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(TermsQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(FuzzyQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(RegexpQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(RangeQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(PrefixQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(WildcardQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(FilteredQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(ConstantScoreQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(SpanTermQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(SpanNotQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(SpanWithinQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(SpanContainingQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(FieldMaskingSpanQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(SpanFirstQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(SpanNearQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(SpanOrQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(MoreLikeThisQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(WrapperQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(IndicesQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(CommonTermsQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(SpanMultiTermQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(FunctionScoreQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(SimpleQueryStringParser.class).asEagerSingleton();
        qpBinders.addBinding().to(TemplateQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(TypeQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(LimitQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(TermsQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(ScriptQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(GeoDistanceQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(GeoDistanceRangeQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(GeoBoundingBoxQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(GeohashCellQuery.Parser.class).asEagerSingleton();
        qpBinders.addBinding().to(GeoPolygonQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(QueryFilterParser.class).asEagerSingleton();
        qpBinders.addBinding().to(FQueryFilterParser.class).asEagerSingleton();
        qpBinders.addBinding().to(AndQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(OrQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(NotQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(ExistsQueryParser.class).asEagerSingleton();
        qpBinders.addBinding().to(MissingQueryParser.class).asEagerSingleton();

        if (ShapesAvailability.JTS_AVAILABLE) {
            qpBinders.addBinding().to(GeoShapeQueryParser.class).asEagerSingleton();
        }
    }
}


File: core/src/main/java/org/elasticsearch/indices/query/IndicesQueriesRegistry.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.indices.query;

import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Maps;

import org.elasticsearch.common.component.AbstractComponent;
import org.elasticsearch.common.inject.Inject;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.index.query.QueryParser;

import java.util.Map;
import java.util.Set;

public class IndicesQueriesRegistry extends AbstractComponent {

    private ImmutableMap<String, QueryParser> queryParsers;

    @Inject
    public IndicesQueriesRegistry(Settings settings, Set<QueryParser> injectedQueryParsers) {
        super(settings);
        Map<String, QueryParser> queryParsers = Maps.newHashMap();
        for (QueryParser queryParser : injectedQueryParsers) {
            for (String name : queryParser.names()) {
                queryParsers.put(name, queryParser);
            }
        }
        this.queryParsers = ImmutableMap.copyOf(queryParsers);
    }

    /**
     * Returns all the registered query parsers
     */
    public ImmutableMap<String, QueryParser> queryParsers() {
        return queryParsers;
    }
}

File: core/src/main/java/org/elasticsearch/transport/TransportModule.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.transport;

import com.google.common.base.Preconditions;
import org.elasticsearch.cluster.node.DiscoveryNode;
import org.elasticsearch.common.inject.AbstractModule;
import org.elasticsearch.common.logging.ESLogger;
import org.elasticsearch.common.logging.Loggers;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.transport.local.LocalTransport;
import org.elasticsearch.transport.netty.NettyTransport;

/**
 *
 */
public class TransportModule extends AbstractModule {

    public static final String TRANSPORT_TYPE_KEY = "transport.type";
    public static final String TRANSPORT_SERVICE_TYPE_KEY = "transport.service.type";

    private final ESLogger logger;
    private final Settings settings;

    private Class<? extends TransportService> configuredTransportService;
    private Class<? extends Transport> configuredTransport;
    private String configuredTransportServiceSource;
    private String configuredTransportSource;

    public TransportModule(Settings settings) {
        this.settings = settings;
        this.logger = Loggers.getLogger(getClass(), settings);
    }

    @Override
    protected void configure() {
        if (configuredTransportService != null) {
            logger.info("Using [{}] as transport service, overridden by [{}]", configuredTransportService.getName(), configuredTransportServiceSource);
            bind(TransportService.class).to(configuredTransportService).asEagerSingleton();
        } else {
            Class<? extends TransportService> defaultTransportService = TransportService.class;
            Class<? extends TransportService> transportService = settings.getAsClass(TRANSPORT_SERVICE_TYPE_KEY, defaultTransportService, "org.elasticsearch.transport.", "TransportService");
            if (!TransportService.class.equals(transportService)) {
                bind(TransportService.class).to(transportService).asEagerSingleton();
            } else {
                bind(TransportService.class).asEagerSingleton();
            }
        }

        if (configuredTransport != null) {
            logger.info("Using [{}] as transport, overridden by [{}]", configuredTransport.getName(), configuredTransportSource);
            bind(Transport.class).to(configuredTransport).asEagerSingleton();
        } else {
            Class<? extends Transport> defaultTransport = DiscoveryNode.localNode(settings) ? LocalTransport.class : NettyTransport.class;
            Class<? extends Transport> transport = settings.getAsClass(TRANSPORT_TYPE_KEY, defaultTransport, "org.elasticsearch.transport.", "Transport");
            bind(Transport.class).to(transport).asEagerSingleton();
        }
    }

    public void setTransportService(Class<? extends TransportService> transportService, String source) {
        Preconditions.checkNotNull(transportService, "Configured transport service may not be null");
        Preconditions.checkNotNull(source, "Plugin, that changes transport service may not be null");
        this.configuredTransportService = transportService;
        this.configuredTransportServiceSource = source;
    }

    public void setTransport(Class<? extends Transport> transport, String source) {
        Preconditions.checkNotNull(transport, "Configured transport may not be null");
        Preconditions.checkNotNull(source, "Plugin, that changes transport may not be null");
        this.configuredTransport = transport;
        this.configuredTransportSource = source;
    }
}

File: core/src/main/java/org/elasticsearch/transport/local/LocalTransport.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.transport.local;

import org.elasticsearch.ElasticsearchException;
import org.elasticsearch.Version;
import org.elasticsearch.cluster.node.DiscoveryNode;
import org.elasticsearch.common.Nullable;
import org.elasticsearch.common.component.AbstractLifecycleComponent;
import org.elasticsearch.common.component.Lifecycle;
import org.elasticsearch.common.inject.Inject;
import org.elasticsearch.common.io.ThrowableObjectInputStream;
import org.elasticsearch.common.io.stream.BytesStreamOutput;
import org.elasticsearch.common.io.stream.StreamInput;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.transport.BoundTransportAddress;
import org.elasticsearch.common.transport.LocalTransportAddress;
import org.elasticsearch.common.transport.TransportAddress;
import org.elasticsearch.common.util.concurrent.AbstractRunnable;
import org.elasticsearch.common.util.concurrent.EsExecutors;
import org.elasticsearch.threadpool.ThreadPool;
import org.elasticsearch.transport.*;
import org.elasticsearch.transport.support.TransportStatus;

import java.io.IOException;
import java.util.Collections;
import java.util.Map;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

import static org.elasticsearch.common.util.concurrent.ConcurrentCollections.newConcurrentMap;

/**
 *
 */
public class LocalTransport extends AbstractLifecycleComponent<Transport> implements Transport {

    public static final String LOCAL_TRANSPORT_THREAD_NAME_PREFIX = "local_transport";

    private final ThreadPool threadPool;
    private final ThreadPoolExecutor workers;
    private final Version version;
    private volatile TransportServiceAdapter transportServiceAdapter;
    private volatile BoundTransportAddress boundAddress;
    private volatile LocalTransportAddress localAddress;
    private final static ConcurrentMap<TransportAddress, LocalTransport> transports = newConcurrentMap();
    private static final AtomicLong transportAddressIdGenerator = new AtomicLong();
    private final ConcurrentMap<DiscoveryNode, LocalTransport> connectedNodes = newConcurrentMap();

    public static final String TRANSPORT_LOCAL_ADDRESS = "transport.local.address";
    public static final String TRANSPORT_LOCAL_WORKERS = "transport.local.workers";
    public static final String TRANSPORT_LOCAL_QUEUE = "transport.local.queue";

    @Inject
    public LocalTransport(Settings settings, ThreadPool threadPool, Version version) {
        super(settings);
        this.threadPool = threadPool;
        this.version = version;

        int workerCount = this.settings.getAsInt(TRANSPORT_LOCAL_WORKERS, EsExecutors.boundedNumberOfProcessors(settings));
        int queueSize = this.settings.getAsInt(TRANSPORT_LOCAL_QUEUE, -1);
        logger.debug("creating [{}] workers, queue_size [{}]", workerCount, queueSize);
        final ThreadFactory threadFactory = EsExecutors.daemonThreadFactory(this.settings, LOCAL_TRANSPORT_THREAD_NAME_PREFIX);
        this.workers = EsExecutors.newFixed(workerCount, queueSize, threadFactory);
    }

    @Override
    public TransportAddress[] addressesFromString(String address) {
        return new TransportAddress[]{new LocalTransportAddress(address)};
    }

    @Override
    public boolean addressSupported(Class<? extends TransportAddress> address) {
        return LocalTransportAddress.class.equals(address);
    }

    @Override
    protected void doStart() {
        String address = settings.get(TRANSPORT_LOCAL_ADDRESS);
        if (address == null) {
            address = Long.toString(transportAddressIdGenerator.incrementAndGet());
        }
        localAddress = new LocalTransportAddress(address);
        LocalTransport previous = transports.put(localAddress, this);
        if (previous != null) {
            throw new ElasticsearchException("local address [" + address + "] is already bound");
        }
        boundAddress = new BoundTransportAddress(localAddress, localAddress);
    }

    @Override
    protected void doStop() {
        transports.remove(localAddress);
        // now, go over all the transports connected to me, and raise disconnected event
        for (final LocalTransport targetTransport : transports.values()) {
            for (final Map.Entry<DiscoveryNode, LocalTransport> entry : targetTransport.connectedNodes.entrySet()) {
                if (entry.getValue() == this) {
                    targetTransport.disconnectFromNode(entry.getKey());
                }
            }
        }
    }

    @Override
    protected void doClose() {
        ThreadPool.terminate(workers, 10, TimeUnit.SECONDS);
    }

    @Override
    public void transportServiceAdapter(TransportServiceAdapter transportServiceAdapter) {
        this.transportServiceAdapter = transportServiceAdapter;
    }

    @Override
    public BoundTransportAddress boundAddress() {
        return boundAddress;
    }

    @Override
    public Map<String, BoundTransportAddress> profileBoundAddresses() {
        return Collections.EMPTY_MAP;
    }

    @Override
    public boolean nodeConnected(DiscoveryNode node) {
        return connectedNodes.containsKey(node);
    }

    @Override
    public void connectToNodeLight(DiscoveryNode node) throws ConnectTransportException {
        connectToNode(node);
    }

    @Override
    public void connectToNode(DiscoveryNode node) throws ConnectTransportException {
        synchronized (this) {
            if (connectedNodes.containsKey(node)) {
                return;
            }
            final LocalTransport targetTransport = transports.get(node.address());
            if (targetTransport == null) {
                throw new ConnectTransportException(node, "Failed to connect");
            }
            connectedNodes.put(node, targetTransport);
            transportServiceAdapter.raiseNodeConnected(node);
        }
    }

    @Override
    public void disconnectFromNode(DiscoveryNode node) {
        synchronized (this) {
            LocalTransport removed = connectedNodes.remove(node);
            if (removed != null) {
                transportServiceAdapter.raiseNodeDisconnected(node);
            }
        }
    }

    @Override
    public long serverOpen() {
        return 0;
    }

    @Override
    public void sendRequest(final DiscoveryNode node, final long requestId, final String action, final TransportRequest request, TransportRequestOptions options) throws IOException, TransportException {
        final Version version = Version.smallest(node.version(), this.version);

        try (BytesStreamOutput stream = new BytesStreamOutput()) {
            stream.setVersion(version);

            stream.writeLong(requestId);
            byte status = 0;
            status = TransportStatus.setRequest(status);
            stream.writeByte(status); // 0 for request, 1 for response.

            stream.writeString(action);
            request.writeTo(stream);

            stream.close();

            final LocalTransport targetTransport = connectedNodes.get(node);
            if (targetTransport == null) {
                throw new NodeNotConnectedException(node, "Node not connected");
            }

            final byte[] data = stream.bytes().toBytes();

            transportServiceAdapter.sent(data.length);
            transportServiceAdapter.onRequestSent(node, requestId, action, request, options);
            targetTransport.workers().execute(new Runnable() {
                @Override
                public void run() {
                    targetTransport.messageReceived(data, action, LocalTransport.this, version, requestId);
                }
            });
        }
    }

    ThreadPoolExecutor workers() {
        return this.workers;
    }

    protected void messageReceived(byte[] data, String action, LocalTransport sourceTransport, Version version, @Nullable final Long sendRequestId) {
        Transports.assertTransportThread();
        try {
            transportServiceAdapter.received(data.length);
            StreamInput stream = StreamInput.wrap(data);
            stream.setVersion(version);

            long requestId = stream.readLong();
            byte status = stream.readByte();
            boolean isRequest = TransportStatus.isRequest(status);

            if (isRequest) {
                handleRequest(stream, requestId, sourceTransport, version);
            } else {
                final TransportResponseHandler handler = transportServiceAdapter.onResponseReceived(requestId);
                // ignore if its null, the adapter logs it
                if (handler != null) {
                    if (TransportStatus.isError(status)) {
                        handlerResponseError(stream, handler);
                    } else {
                        handleResponse(stream, sourceTransport, handler);
                    }
                }
            }
        } catch (Throwable e) {
            if (sendRequestId != null) {
                TransportResponseHandler handler = transportServiceAdapter.onResponseReceived(sendRequestId);
                if (handler != null) {
                    handleException(handler, new RemoteTransportException(nodeName(), localAddress, action, e));
                }
            } else {
                logger.warn("Failed to receive message for action [" + action + "]", e);
            }
        }
    }

    private void handleRequest(StreamInput stream, long requestId, LocalTransport sourceTransport, Version version) throws Exception {
        final String action = stream.readString();
        transportServiceAdapter.onRequestReceived(requestId, action);
        final LocalTransportChannel transportChannel = new LocalTransportChannel(this, transportServiceAdapter, sourceTransport, action, requestId, version);
        try {
            final RequestHandlerRegistry reg = transportServiceAdapter.getRequestHandler(action);
            if (reg == null) {
                throw new ActionNotFoundTransportException("Action [" + action + "] not found");
            }
            final TransportRequest request = reg.newRequest();
            request.remoteAddress(sourceTransport.boundAddress.publishAddress());
            request.readFrom(stream);
            if (ThreadPool.Names.SAME.equals(reg.getExecutor())) {
                //noinspection unchecked
                reg.getHandler().messageReceived(request, transportChannel);
            } else {
                threadPool.executor(reg.getExecutor()).execute(new AbstractRunnable() {
                    @Override
                    protected void doRun() throws Exception {
                        //noinspection unchecked
                        reg.getHandler().messageReceived(request, transportChannel);
                    }

                    @Override
                    public boolean isForceExecution() {
                        return reg.isForceExecution();
                    }

                    @Override
                    public void onFailure(Throwable e) {
                        if (lifecycleState() == Lifecycle.State.STARTED) {
                            // we can only send a response transport is started....
                            try {
                                transportChannel.sendResponse(e);
                            } catch (Throwable e1) {
                                logger.warn("Failed to send error message back to client for action [" + action + "]", e1);
                                logger.warn("Actual Exception", e);
                            }
                        }
                    }
                });
            }
        } catch (Throwable e) {
            try {
                transportChannel.sendResponse(e);
            } catch (Throwable e1) {
                logger.warn("Failed to send error message back to client for action [" + action + "]", e);
                logger.warn("Actual Exception", e1);
            }
        }
    }

    protected void handleResponse(StreamInput buffer, LocalTransport sourceTransport, final TransportResponseHandler handler) {
        final TransportResponse response = handler.newInstance();
        response.remoteAddress(sourceTransport.boundAddress.publishAddress());
        try {
            response.readFrom(buffer);
        } catch (Throwable e) {
            handleException(handler, new TransportSerializationException("Failed to deserialize response of type [" + response.getClass().getName() + "]", e));
            return;
        }
        handleParsedResponse(response, handler);
    }

    protected void handleParsedResponse(final TransportResponse response, final TransportResponseHandler handler) {
        threadPool.executor(handler.executor()).execute(new Runnable() {
            @SuppressWarnings({"unchecked"})
            @Override
            public void run() {
                try {
                    handler.handleResponse(response);
                } catch (Throwable e) {
                    handleException(handler, new ResponseHandlerFailureTransportException(e));
                }
            }
        });
    }

    private void handlerResponseError(StreamInput buffer, final TransportResponseHandler handler) {
        Throwable error;
        try {
            ThrowableObjectInputStream ois = new ThrowableObjectInputStream(buffer, settings.getClassLoader());
            error = (Throwable) ois.readObject();
        } catch (Throwable e) {
            error = new TransportSerializationException("Failed to deserialize exception response from stream", e);
        }
        handleException(handler, error);
    }

    private void handleException(final TransportResponseHandler handler, Throwable error) {
        if (!(error instanceof RemoteTransportException)) {
            error = new RemoteTransportException("None remote transport exception", error);
        }
        final RemoteTransportException rtx = (RemoteTransportException) error;
        try {
            handler.handleException(rtx);
        } catch (Throwable t) {
            logger.error("failed to handle exception response [{}]", t, handler);
        }
    }
}


File: core/src/main/java/org/elasticsearch/transport/netty/MessageChannelHandler.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.transport.netty;

import org.elasticsearch.Version;
import org.elasticsearch.common.component.Lifecycle;
import org.elasticsearch.common.compress.Compressor;
import org.elasticsearch.common.compress.CompressorFactory;
import org.elasticsearch.common.compress.NotCompressedException;
import org.elasticsearch.common.io.ThrowableObjectInputStream;
import org.elasticsearch.common.io.stream.StreamInput;
import org.elasticsearch.common.logging.ESLogger;
import org.elasticsearch.common.transport.InetSocketTransportAddress;
import org.elasticsearch.common.util.concurrent.AbstractRunnable;
import org.elasticsearch.threadpool.ThreadPool;
import org.elasticsearch.transport.*;
import org.elasticsearch.transport.support.TransportStatus;
import org.jboss.netty.buffer.ChannelBuffer;
import org.jboss.netty.channel.*;

import java.io.IOException;
import java.net.InetSocketAddress;

/**
 * A handler (must be the last one!) that does size based frame decoding and forwards the actual message
 * to the relevant action.
 */
public class MessageChannelHandler extends SimpleChannelUpstreamHandler {

    protected final ESLogger logger;
    protected final ThreadPool threadPool;
    protected final TransportServiceAdapter transportServiceAdapter;
    protected final NettyTransport transport;
    protected final String profileName;

    public MessageChannelHandler(NettyTransport transport, ESLogger logger, String profileName) {
        this.threadPool = transport.threadPool();
        this.transportServiceAdapter = transport.transportServiceAdapter();
        this.transport = transport;
        this.logger = logger;
        this.profileName = profileName;
    }

    @Override
    public void writeComplete(ChannelHandlerContext ctx, WriteCompletionEvent e) throws Exception {
        transportServiceAdapter.sent(e.getWrittenAmount());
        super.writeComplete(ctx, e);
    }

    @Override
    public void messageReceived(ChannelHandlerContext ctx, MessageEvent e) throws Exception {
        Transports.assertTransportThread();
        Object m = e.getMessage();
        if (!(m instanceof ChannelBuffer)) {
            ctx.sendUpstream(e);
            return;
        }
        ChannelBuffer buffer = (ChannelBuffer) m;
        int size = buffer.getInt(buffer.readerIndex() - 4);
        transportServiceAdapter.received(size + 6);

        // we have additional bytes to read, outside of the header
        boolean hasMessageBytesToRead = (size - (NettyHeader.HEADER_SIZE - 6)) != 0;

        int markedReaderIndex = buffer.readerIndex();
        int expectedIndexReader = markedReaderIndex + size;

        // netty always copies a buffer, either in NioWorker in its read handler, where it copies to a fresh
        // buffer, or in the cumlation buffer, which is cleaned each time
        StreamInput streamIn = ChannelBufferStreamInputFactory.create(buffer, size);

        long requestId = buffer.readLong();
        byte status = buffer.readByte();
        Version version = Version.fromId(buffer.readInt());

        StreamInput wrappedStream;
        if (TransportStatus.isCompress(status) && hasMessageBytesToRead && buffer.readable()) {
            Compressor compressor;
            try {
                compressor = CompressorFactory.compressor(buffer);
            } catch (NotCompressedException ex) {
                int maxToRead = Math.min(buffer.readableBytes(), 10);
                int offset = buffer.readerIndex();
                StringBuilder sb = new StringBuilder("stream marked as compressed, but no compressor found, first [").append(maxToRead).append("] content bytes out of [").append(buffer.readableBytes()).append("] readable bytes with message size [").append(size).append("] ").append("] are [");
                for (int i = 0; i < maxToRead; i++) {
                    sb.append(buffer.getByte(offset + i)).append(",");
                }
                sb.append("]");
                throw new IllegalStateException(sb.toString());
            }
            wrappedStream = compressor.streamInput(streamIn);
        } else {
            wrappedStream = streamIn;
        }
        wrappedStream.setVersion(version);

        if (TransportStatus.isRequest(status)) {
            String action = handleRequest(ctx.getChannel(), wrappedStream, requestId, version);
            if (buffer.readerIndex() != expectedIndexReader) {
                if (buffer.readerIndex() < expectedIndexReader) {
                    logger.warn("Message not fully read (request) for requestId [{}], action [{}], readerIndex [{}] vs expected [{}]; resetting",
                                requestId, action, buffer.readerIndex(), expectedIndexReader);
                } else {
                    logger.warn("Message read past expected size (request) for requestId=[{}], action [{}], readerIndex [{}] vs expected [{}]; resetting",
                                requestId, action, buffer.readerIndex(), expectedIndexReader);
                }
                buffer.readerIndex(expectedIndexReader);
            }
        } else {
            TransportResponseHandler handler = transportServiceAdapter.onResponseReceived(requestId);
            // ignore if its null, the adapter logs it
            if (handler != null) {
                if (TransportStatus.isError(status)) {
                    handlerResponseError(wrappedStream, handler);
                } else {
                    handleResponse(ctx.getChannel(), wrappedStream, handler);
                }
            } else {
                // if its null, skip those bytes
                buffer.readerIndex(markedReaderIndex + size);
            }
            if (buffer.readerIndex() != expectedIndexReader) {
                if (buffer.readerIndex() < expectedIndexReader) {
                    logger.warn("Message not fully read (response) for [{}] handler {}, error [{}], resetting", requestId, handler, TransportStatus.isError(status));
                } else {
                    logger.warn("Message read past expected size (response) for [{}] handler {}, error [{}], resetting", requestId, handler, TransportStatus.isError(status));
                }
                buffer.readerIndex(expectedIndexReader);
            }
        }
        wrappedStream.close();
    }

    protected void handleResponse(Channel channel, StreamInput buffer, final TransportResponseHandler handler) {
        final TransportResponse response = handler.newInstance();
        response.remoteAddress(new InetSocketTransportAddress((InetSocketAddress) channel.getRemoteAddress()));
        response.remoteAddress();
        try {
            response.readFrom(buffer);
        } catch (Throwable e) {
            handleException(handler, new TransportSerializationException("Failed to deserialize response of type [" + response.getClass().getName() + "]", e));
            return;
        }
        try {
            if (ThreadPool.Names.SAME.equals(handler.executor())) {
                //noinspection unchecked
                handler.handleResponse(response);
            } else {
                threadPool.executor(handler.executor()).execute(new ResponseHandler(handler, response));
            }
        } catch (Throwable e) {
            handleException(handler, new ResponseHandlerFailureTransportException(e));
        }
    }

    private void handlerResponseError(StreamInput buffer, final TransportResponseHandler handler) {
        Throwable error;
        try {
            ThrowableObjectInputStream ois = new ThrowableObjectInputStream(buffer, transport.settings().getClassLoader());
            error = (Throwable) ois.readObject();
        } catch (Throwable e) {
            error = new TransportSerializationException("Failed to deserialize exception response from stream", e);
        }
        handleException(handler, error);
    }

    private void handleException(final TransportResponseHandler handler, Throwable error) {
        if (!(error instanceof RemoteTransportException)) {
            error = new RemoteTransportException(error.getMessage(), error);
        }
        final RemoteTransportException rtx = (RemoteTransportException) error;
        if (ThreadPool.Names.SAME.equals(handler.executor())) {
            try {
                handler.handleException(rtx);
            } catch (Throwable e) {
                logger.error("failed to handle exception response [{}]", e, handler);
            }
        } else {
            threadPool.executor(handler.executor()).execute(new Runnable() {
                @Override
                public void run() {
                    try {
                        handler.handleException(rtx);
                    } catch (Throwable e) {
                        logger.error("failed to handle exception response [{}]", e, handler);
                    }
                }
            });
        }
    }

    protected String handleRequest(Channel channel, StreamInput buffer, long requestId, Version version) throws IOException {
        final String action = buffer.readString();
        transportServiceAdapter.onRequestReceived(requestId, action);
        final NettyTransportChannel transportChannel = new NettyTransportChannel(transport, transportServiceAdapter, action, channel, requestId, version, profileName);
        try {
            final RequestHandlerRegistry reg = transportServiceAdapter.getRequestHandler(action);
            if (reg == null) {
                throw new ActionNotFoundTransportException(action);
            }
            final TransportRequest request = reg.newRequest();
            request.remoteAddress(new InetSocketTransportAddress((InetSocketAddress) channel.getRemoteAddress()));
            request.readFrom(buffer);
            if (ThreadPool.Names.SAME.equals(reg.getExecutor())) {
                //noinspection unchecked
                reg.getHandler().messageReceived(request, transportChannel);
            } else {
                threadPool.executor(reg.getExecutor()).execute(new RequestHandler(reg, request, transportChannel));
            }
        } catch (Throwable e) {
            try {
                transportChannel.sendResponse(e);
            } catch (IOException e1) {
                logger.warn("Failed to send error message back to client for action [" + action + "]", e);
                logger.warn("Actual Exception", e1);
            }
        }
        return action;
    }

    @Override
    public void exceptionCaught(ChannelHandlerContext ctx, ExceptionEvent e) throws Exception {
        transport.exceptionCaught(ctx, e);
    }

    class ResponseHandler implements Runnable {

        private final TransportResponseHandler handler;
        private final TransportResponse response;

        public ResponseHandler(TransportResponseHandler handler, TransportResponse response) {
            this.handler = handler;
            this.response = response;
        }

        @SuppressWarnings({"unchecked"})
        @Override
        public void run() {
            try {
                handler.handleResponse(response);
            } catch (Throwable e) {
                handleException(handler, new ResponseHandlerFailureTransportException(e));
            }
        }
    }

    class RequestHandler extends AbstractRunnable {
        private final RequestHandlerRegistry reg;
        private final TransportRequest request;
        private final NettyTransportChannel transportChannel;

        public RequestHandler(RequestHandlerRegistry reg, TransportRequest request, NettyTransportChannel transportChannel) {
            this.reg = reg;
            this.request = request;
            this.transportChannel = transportChannel;
        }

        @SuppressWarnings({"unchecked"})
        @Override
        protected void doRun() throws Exception {
            reg.getHandler().messageReceived(request, transportChannel);
        }

        @Override
        public boolean isForceExecution() {
            return reg.isForceExecution();
        }

        @Override
        public void onFailure(Throwable e) {
            if (transport.lifecycleState() == Lifecycle.State.STARTED) {
                // we can only send a response transport is started....
                try {
                    transportChannel.sendResponse(e);
                } catch (Throwable e1) {
                    logger.warn("Failed to send error message back to client for action [" + reg.getAction() + "]", e1);
                    logger.warn("Actual Exception", e);
                }
            }
        }
    }
}


File: core/src/main/java/org/elasticsearch/transport/netty/NettyTransport.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.transport.netty;

import com.google.common.base.Charsets;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import org.elasticsearch.*;
import org.elasticsearch.cluster.node.DiscoveryNode;
import org.elasticsearch.common.Booleans;
import org.elasticsearch.common.Strings;
import org.elasticsearch.common.bytes.ReleasablePagedBytesReference;
import org.elasticsearch.common.component.AbstractLifecycleComponent;
import org.elasticsearch.common.compress.CompressorFactory;
import org.elasticsearch.common.inject.Inject;
import org.elasticsearch.common.io.stream.ReleasableBytesStreamOutput;
import org.elasticsearch.common.io.stream.StreamOutput;
import org.elasticsearch.common.lease.Releasables;
import org.elasticsearch.common.math.MathUtils;
import org.elasticsearch.common.metrics.CounterMetric;
import org.elasticsearch.common.netty.NettyUtils;
import org.elasticsearch.common.netty.OpenChannelsHandler;
import org.elasticsearch.common.netty.ReleaseChannelFutureListener;
import org.elasticsearch.common.network.NetworkService;
import org.elasticsearch.common.network.NetworkUtils;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.transport.BoundTransportAddress;
import org.elasticsearch.common.transport.InetSocketTransportAddress;
import org.elasticsearch.common.transport.PortsRange;
import org.elasticsearch.common.transport.TransportAddress;
import org.elasticsearch.common.unit.ByteSizeValue;
import org.elasticsearch.common.unit.TimeValue;
import org.elasticsearch.common.util.BigArrays;
import org.elasticsearch.common.util.concurrent.EsExecutors;
import org.elasticsearch.common.util.concurrent.KeyedLock;
import org.elasticsearch.monitor.jvm.JvmInfo;
import org.elasticsearch.threadpool.ThreadPool;
import org.elasticsearch.transport.*;
import org.elasticsearch.transport.support.TransportStatus;
import org.jboss.netty.bootstrap.ClientBootstrap;
import org.jboss.netty.bootstrap.ServerBootstrap;
import org.jboss.netty.buffer.ChannelBuffer;
import org.jboss.netty.buffer.ChannelBuffers;
import org.jboss.netty.channel.*;
import org.jboss.netty.channel.socket.nio.NioClientSocketChannelFactory;
import org.jboss.netty.channel.socket.nio.NioServerSocketChannelFactory;
import org.jboss.netty.channel.socket.nio.NioWorkerPool;
import org.jboss.netty.channel.socket.oio.OioClientSocketChannelFactory;
import org.jboss.netty.channel.socket.oio.OioServerSocketChannelFactory;
import org.jboss.netty.util.HashedWheelTimer;

import java.io.IOException;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.SocketAddress;
import java.nio.channels.CancelledKeyException;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.locks.ReadWriteLock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

import static org.elasticsearch.common.network.NetworkService.TcpSettings.*;
import static org.elasticsearch.common.settings.Settings.settingsBuilder;
import static org.elasticsearch.common.transport.NetworkExceptionHelper.isCloseConnectionException;
import static org.elasticsearch.common.transport.NetworkExceptionHelper.isConnectException;
import static org.elasticsearch.common.util.concurrent.ConcurrentCollections.newConcurrentMap;
import static org.elasticsearch.common.util.concurrent.EsExecutors.daemonThreadFactory;

/**
 * There are 4 types of connections per node, low/med/high/ping. Low if for batch oriented APIs (like recovery or
 * batch) with high payload that will cause regular request. (like search or single index) to take
 * longer. Med is for the typical search / single doc index. And High for things like cluster state. Ping is reserved for
 * sending out ping requests to other nodes.
 */
public class NettyTransport extends AbstractLifecycleComponent<Transport> implements Transport {

    static {
        NettyUtils.setup();
    }

    public static final String HTTP_SERVER_WORKER_THREAD_NAME_PREFIX = "http_server_worker";
    public static final String HTTP_SERVER_BOSS_THREAD_NAME_PREFIX = "http_server_boss";
    public static final String TRANSPORT_CLIENT_WORKER_THREAD_NAME_PREFIX = "transport_client_worker";
    public static final String TRANSPORT_CLIENT_BOSS_THREAD_NAME_PREFIX = "transport_client_boss";

    public static final String WORKER_COUNT = "transport.netty.worker_count";
    public static final String CONNECTIONS_PER_NODE_RECOVERY = "transport.connections_per_node.recovery";
    public static final String CONNECTIONS_PER_NODE_BULK = "transport.connections_per_node.bulk";
    public static final String CONNECTIONS_PER_NODE_REG = "transport.connections_per_node.reg";
    public static final String CONNECTIONS_PER_NODE_STATE = "transport.connections_per_node.state";
    public static final String CONNECTIONS_PER_NODE_PING = "transport.connections_per_node.ping";
    public static final String PING_SCHEDULE = "transport.ping_schedule"; // the scheduled internal ping interval setting
    public static final TimeValue DEFAULT_PING_SCHEDULE = TimeValue.timeValueMillis(-1); // the default ping schedule, defaults to disabled (-1)
    public static final String DEFAULT_PORT_RANGE = "9300-9400";
    public static final String DEFAULT_PROFILE = "default";

    protected final NetworkService networkService;
    protected final Version version;

    protected final boolean blockingClient;
    protected final TimeValue connectTimeout;
    protected final ByteSizeValue maxCumulationBufferCapacity;
    protected final int maxCompositeBufferComponents;
    protected final boolean compress;
    protected final ReceiveBufferSizePredictorFactory receiveBufferSizePredictorFactory;
    protected final int workerCount;
    protected final ByteSizeValue receivePredictorMin;
    protected final ByteSizeValue receivePredictorMax;

    protected final int connectionsPerNodeRecovery;
    protected final int connectionsPerNodeBulk;
    protected final int connectionsPerNodeReg;
    protected final int connectionsPerNodeState;
    protected final int connectionsPerNodePing;

    private final TimeValue pingSchedule;

    protected final BigArrays bigArrays;
    protected final ThreadPool threadPool;
    protected volatile OpenChannelsHandler serverOpenChannels;
    protected volatile ClientBootstrap clientBootstrap;
    // node id to actual channel
    protected final ConcurrentMap<DiscoveryNode, NodeChannels> connectedNodes = newConcurrentMap();
    protected final Map<String, ServerBootstrap> serverBootstraps = newConcurrentMap();
    protected final Map<String, Channel> serverChannels = newConcurrentMap();
    protected final Map<String, BoundTransportAddress> profileBoundAddresses = newConcurrentMap();
    protected volatile TransportServiceAdapter transportServiceAdapter;
    protected volatile BoundTransportAddress boundAddress;
    protected final KeyedLock<String> connectionLock = new KeyedLock<>();

    // this lock is here to make sure we close this transport and disconnect all the client nodes
    // connections while no connect operations is going on... (this might help with 100% CPU when stopping the transport?)
    private final ReadWriteLock globalLock = new ReentrantReadWriteLock();

    // package visibility for tests
    final ScheduledPing scheduledPing;

    @Inject
    public NettyTransport(Settings settings, ThreadPool threadPool, NetworkService networkService, BigArrays bigArrays, Version version) {
        super(settings);
        this.threadPool = threadPool;
        this.networkService = networkService;
        this.bigArrays = bigArrays;
        this.version = version;

        if (settings.getAsBoolean("netty.epollBugWorkaround", false)) {
            System.setProperty("org.jboss.netty.epollBugWorkaround", "true");
        }

        this.workerCount = settings.getAsInt(WORKER_COUNT, EsExecutors.boundedNumberOfProcessors(settings) * 2);
        this.blockingClient = settings.getAsBoolean("transport.netty.transport.tcp.blocking_client", settings.getAsBoolean(TCP_BLOCKING_CLIENT, settings.getAsBoolean(TCP_BLOCKING, false)));
        this.connectTimeout = this.settings.getAsTime("transport.netty.connect_timeout", settings.getAsTime("transport.tcp.connect_timeout", settings.getAsTime(TCP_CONNECT_TIMEOUT, TCP_DEFAULT_CONNECT_TIMEOUT)));
        this.maxCumulationBufferCapacity = this.settings.getAsBytesSize("transport.netty.max_cumulation_buffer_capacity", null);
        this.maxCompositeBufferComponents = this.settings.getAsInt("transport.netty.max_composite_buffer_components", -1);
        this.compress = settings.getAsBoolean(TransportSettings.TRANSPORT_TCP_COMPRESS, false);

        this.connectionsPerNodeRecovery = this.settings.getAsInt("transport.netty.connections_per_node.recovery", settings.getAsInt(CONNECTIONS_PER_NODE_RECOVERY, 2));
        this.connectionsPerNodeBulk = this.settings.getAsInt("transport.netty.connections_per_node.bulk", settings.getAsInt(CONNECTIONS_PER_NODE_BULK, 3));
        this.connectionsPerNodeReg = this.settings.getAsInt("transport.netty.connections_per_node.reg", settings.getAsInt(CONNECTIONS_PER_NODE_REG, 6));
        this.connectionsPerNodeState = this.settings.getAsInt("transport.netty.connections_per_node.high", settings.getAsInt(CONNECTIONS_PER_NODE_STATE, 1));
        this.connectionsPerNodePing = this.settings.getAsInt("transport.netty.connections_per_node.ping", settings.getAsInt(CONNECTIONS_PER_NODE_PING, 1));

        // we want to have at least 1 for reg/state/ping
        if (this.connectionsPerNodeReg == 0) {
            throw new IllegalArgumentException("can't set [connection_per_node.reg] to 0");
        }
        if (this.connectionsPerNodePing == 0) {
            throw new IllegalArgumentException("can't set [connection_per_node.ping] to 0");
        }
        if (this.connectionsPerNodeState == 0) {
            throw new IllegalArgumentException("can't set [connection_per_node.state] to 0");
        }

        long defaultReceiverPredictor = 512 * 1024;
        if (JvmInfo.jvmInfo().getMem().getDirectMemoryMax().bytes() > 0) {
            // we can guess a better default...
            long l = (long) ((0.3 * JvmInfo.jvmInfo().getMem().getDirectMemoryMax().bytes()) / workerCount);
            defaultReceiverPredictor = Math.min(defaultReceiverPredictor, Math.max(l, 64 * 1024));
        }

        // See AdaptiveReceiveBufferSizePredictor#DEFAULT_XXX for default values in netty..., we can use higher ones for us, even fixed one
        this.receivePredictorMin = this.settings.getAsBytesSize("transport.netty.receive_predictor_min", this.settings.getAsBytesSize("transport.netty.receive_predictor_size", new ByteSizeValue(defaultReceiverPredictor)));
        this.receivePredictorMax = this.settings.getAsBytesSize("transport.netty.receive_predictor_max", this.settings.getAsBytesSize("transport.netty.receive_predictor_size", new ByteSizeValue(defaultReceiverPredictor)));
        if (receivePredictorMax.bytes() == receivePredictorMin.bytes()) {
            receiveBufferSizePredictorFactory = new FixedReceiveBufferSizePredictorFactory((int) receivePredictorMax.bytes());
        } else {
            receiveBufferSizePredictorFactory = new AdaptiveReceiveBufferSizePredictorFactory((int) receivePredictorMin.bytes(), (int) receivePredictorMin.bytes(), (int) receivePredictorMax.bytes());
        }

        this.scheduledPing = new ScheduledPing();
        this.pingSchedule = settings.getAsTime(PING_SCHEDULE, DEFAULT_PING_SCHEDULE);
        if (pingSchedule.millis() > 0) {
            threadPool.schedule(pingSchedule, ThreadPool.Names.GENERIC, scheduledPing);
        }
    }

    public Settings settings() {
        return this.settings;
    }

    @Override
    public void transportServiceAdapter(TransportServiceAdapter service) {
        this.transportServiceAdapter = service;
    }

    TransportServiceAdapter transportServiceAdapter() {
        return transportServiceAdapter;
    }

    ThreadPool threadPool() {
        return threadPool;
    }

    @Override
    protected void doStart() {
        boolean success = false;
        try {
            clientBootstrap = createClientBootstrap();
            if (settings.getAsBoolean("network.server", true)) {
                final OpenChannelsHandler openChannels = new OpenChannelsHandler(logger);
                this.serverOpenChannels = openChannels;

                // extract default profile first and create standard bootstrap
                Map<String, Settings> profiles = settings.getGroups("transport.profiles", true);
                if (!profiles.containsKey(DEFAULT_PROFILE)) {
                    profiles = Maps.newHashMap(profiles);
                    profiles.put(DEFAULT_PROFILE, Settings.EMPTY);
                }

                Settings fallbackSettings = createFallbackSettings();
                Settings defaultSettings = profiles.get(DEFAULT_PROFILE);

                // loop through all profiles and start them up, special handling for default one
                for (Map.Entry<String, Settings> entry : profiles.entrySet()) {
                    Settings profileSettings = entry.getValue();
                    String name = entry.getKey();

                    if (!Strings.hasLength(name)) {
                        logger.info("transport profile configured without a name. skipping profile with settings [{}]", profileSettings.toDelimitedString(','));
                        continue;
                    } else if (DEFAULT_PROFILE.equals(name)) {
                        profileSettings = settingsBuilder()
                                .put(profileSettings)
                                .put("port", profileSettings.get("port", this.settings.get("transport.tcp.port", DEFAULT_PORT_RANGE)))
                                .build();
                    } else if (profileSettings.get("port") == null) {
                        // if profile does not have a port, skip it
                        logger.info("No port configured for profile [{}], not binding", name);
                        continue;
                    }

                    // merge fallback settings with default settings with profile settings so we have complete settings with default values
                    Settings mergedSettings = settingsBuilder()
                            .put(fallbackSettings)
                            .put(defaultSettings)
                            .put(profileSettings)
                            .build();

                    createServerBootstrap(name, mergedSettings);
                    bindServerBootstrap(name, mergedSettings);
                }

                InetSocketAddress boundAddress = (InetSocketAddress) serverChannels.get(DEFAULT_PROFILE).getLocalAddress();
                int publishPort = settings.getAsInt("transport.netty.publish_port", settings.getAsInt("transport.publish_port", boundAddress.getPort()));
                String publishHost = settings.get("transport.netty.publish_host", settings.get("transport.publish_host", settings.get("transport.host")));
                InetSocketAddress publishAddress = createPublishAddress(publishHost, publishPort);
                this.boundAddress = new BoundTransportAddress(new InetSocketTransportAddress(boundAddress), new InetSocketTransportAddress(publishAddress));
            }
            success = true;
        } finally {
            if (success == false) {
                doStop();
            }
        }
    }

    @Override
    public Map<String, BoundTransportAddress> profileBoundAddresses() {
        return ImmutableMap.copyOf(profileBoundAddresses);
    }

    private InetSocketAddress createPublishAddress(String publishHost, int publishPort) {
        try {
            return new InetSocketAddress(networkService.resolvePublishHostAddress(publishHost), publishPort);
        } catch (Exception e) {
            throw new BindTransportException("Failed to resolve publish address", e);
        }
    }

    private ClientBootstrap createClientBootstrap() {

        if (blockingClient) {
            clientBootstrap = new ClientBootstrap(new OioClientSocketChannelFactory(Executors.newCachedThreadPool(daemonThreadFactory(settings, TRANSPORT_CLIENT_WORKER_THREAD_NAME_PREFIX))));
        } else {
            int bossCount = settings.getAsInt("transport.netty.boss_count", 1);
            clientBootstrap = new ClientBootstrap(new NioClientSocketChannelFactory(
                    Executors.newCachedThreadPool(daemonThreadFactory(settings, TRANSPORT_CLIENT_BOSS_THREAD_NAME_PREFIX)),
                    bossCount,
                    new NioWorkerPool(Executors.newCachedThreadPool(daemonThreadFactory(settings, TRANSPORT_CLIENT_WORKER_THREAD_NAME_PREFIX)), workerCount),
                    new HashedWheelTimer(daemonThreadFactory(settings, "transport_client_timer"))));
        }
        clientBootstrap.setPipelineFactory(configureClientChannelPipelineFactory());
        clientBootstrap.setOption("connectTimeoutMillis", connectTimeout.millis());

        String tcpNoDelay = settings.get("transport.netty.tcp_no_delay", settings.get(TCP_NO_DELAY, "true"));
        if (!"default".equals(tcpNoDelay)) {
            clientBootstrap.setOption("tcpNoDelay", Booleans.parseBoolean(tcpNoDelay, null));
        }

        String tcpKeepAlive = settings.get("transport.netty.tcp_keep_alive", settings.get(TCP_KEEP_ALIVE, "true"));
        if (!"default".equals(tcpKeepAlive)) {
            clientBootstrap.setOption("keepAlive", Booleans.parseBoolean(tcpKeepAlive, null));
        }

        ByteSizeValue tcpSendBufferSize = settings.getAsBytesSize("transport.netty.tcp_send_buffer_size", settings.getAsBytesSize(TCP_SEND_BUFFER_SIZE, TCP_DEFAULT_SEND_BUFFER_SIZE));
        if (tcpSendBufferSize != null && tcpSendBufferSize.bytes() > 0) {
            clientBootstrap.setOption("sendBufferSize", tcpSendBufferSize.bytes());
        }

        ByteSizeValue tcpReceiveBufferSize = settings.getAsBytesSize("transport.netty.tcp_receive_buffer_size", settings.getAsBytesSize(TCP_RECEIVE_BUFFER_SIZE, TCP_DEFAULT_RECEIVE_BUFFER_SIZE));
        if (tcpReceiveBufferSize != null && tcpReceiveBufferSize.bytes() > 0) {
            clientBootstrap.setOption("receiveBufferSize", tcpReceiveBufferSize.bytes());
        }

        clientBootstrap.setOption("receiveBufferSizePredictorFactory", receiveBufferSizePredictorFactory);

        boolean reuseAddress = settings.getAsBoolean("transport.netty.reuse_address", settings.getAsBoolean(TCP_REUSE_ADDRESS, NetworkUtils.defaultReuseAddress()));
        clientBootstrap.setOption("reuseAddress", reuseAddress);

        return clientBootstrap;
    }

    private Settings createFallbackSettings() {
        Settings.Builder fallbackSettingsBuilder = settingsBuilder();

        String fallbackBindHost = settings.get("transport.netty.bind_host", settings.get("transport.bind_host", settings.get("transport.host")));
        if (fallbackBindHost != null) {
            fallbackSettingsBuilder.put("bind_host", fallbackBindHost);
        }

        String fallbackPublishHost = settings.get("transport.netty.publish_host", settings.get("transport.publish_host", settings.get("transport.host")));
        if (fallbackPublishHost != null) {
            fallbackSettingsBuilder.put("publish_host", fallbackPublishHost);
        }

        String fallbackTcpNoDelay = settings.get("transport.netty.tcp_no_delay", settings.get(TCP_NO_DELAY, "true"));
        if (fallbackTcpNoDelay != null) {
            fallbackSettingsBuilder.put("tcp_no_delay", fallbackTcpNoDelay);
        }

        String fallbackTcpKeepAlive = settings.get("transport.netty.tcp_keep_alive", settings.get(TCP_KEEP_ALIVE, "true"));
        if (fallbackTcpKeepAlive != null) {
            fallbackSettingsBuilder.put("tcp_keep_alive", fallbackTcpKeepAlive);
        }

        boolean fallbackReuseAddress = settings.getAsBoolean("transport.netty.reuse_address", settings.getAsBoolean(TCP_REUSE_ADDRESS, NetworkUtils.defaultReuseAddress()));
        fallbackSettingsBuilder.put("reuse_address", fallbackReuseAddress);

        ByteSizeValue fallbackTcpSendBufferSize = settings.getAsBytesSize("transport.netty.tcp_send_buffer_size", settings.getAsBytesSize(TCP_SEND_BUFFER_SIZE, TCP_DEFAULT_SEND_BUFFER_SIZE));
        if (fallbackTcpSendBufferSize != null) {
            fallbackSettingsBuilder.put("tcp_send_buffer_size", fallbackTcpSendBufferSize);
        }

        ByteSizeValue fallbackTcpBufferSize = settings.getAsBytesSize("transport.netty.tcp_receive_buffer_size", settings.getAsBytesSize(TCP_RECEIVE_BUFFER_SIZE, TCP_DEFAULT_RECEIVE_BUFFER_SIZE));
        if (fallbackTcpBufferSize != null) {
            fallbackSettingsBuilder.put("tcp_receive_buffer_size", fallbackTcpBufferSize);
        }

        return fallbackSettingsBuilder.build();
    }

    private void bindServerBootstrap(final String name, final Settings settings) {
        // Bind and start to accept incoming connections.
        InetAddress hostAddressX;
        String bindHost = settings.get("bind_host");
        try {
            hostAddressX = networkService.resolveBindHostAddress(bindHost);
        } catch (IOException e) {
            throw new BindTransportException("Failed to resolve host [" + bindHost + "]", e);
        }
        final InetAddress hostAddress = hostAddressX;

        String port = settings.get("port");
        PortsRange portsRange = new PortsRange(port);
        final AtomicReference<Exception> lastException = new AtomicReference<>();
        boolean success = portsRange.iterate(new PortsRange.PortCallback() {
            @Override
            public boolean onPortNumber(int portNumber) {
                try {
                    serverChannels.put(name, serverBootstraps.get(name).bind(new InetSocketAddress(hostAddress, portNumber)));
                } catch (Exception e) {
                    lastException.set(e);
                    return false;
                }
                return true;
            }
        });
        if (!success) {
            throw new BindTransportException("Failed to bind to [" + port + "]", lastException.get());
        }

        if (!DEFAULT_PROFILE.equals(name)) {
            InetSocketAddress boundAddress = (InetSocketAddress) serverChannels.get(name).getLocalAddress();
            int publishPort = settings.getAsInt("publish_port", boundAddress.getPort());
            String publishHost = settings.get("publish_host", boundAddress.getHostString());
            InetSocketAddress publishAddress = createPublishAddress(publishHost, publishPort);
            profileBoundAddresses.put(name, new BoundTransportAddress(new InetSocketTransportAddress(boundAddress), new InetSocketTransportAddress(publishAddress)));
        }

        logger.debug("Bound profile [{}] to address [{}]", name, serverChannels.get(name).getLocalAddress());
    }

    private void createServerBootstrap(String name, Settings settings) {
        boolean blockingServer = settings.getAsBoolean("transport.tcp.blocking_server", this.settings.getAsBoolean(TCP_BLOCKING_SERVER, this.settings.getAsBoolean(TCP_BLOCKING, false)));
        String port = settings.get("port");
        String bindHost = settings.get("bind_host");
        String publishHost = settings.get("publish_host");
        String tcpNoDelay = settings.get("tcp_no_delay");
        String tcpKeepAlive = settings.get("tcp_keep_alive");
        boolean reuseAddress = settings.getAsBoolean("reuse_address", NetworkUtils.defaultReuseAddress());
        ByteSizeValue tcpSendBufferSize = settings.getAsBytesSize("tcp_send_buffer_size", TCP_DEFAULT_SEND_BUFFER_SIZE);
        ByteSizeValue tcpReceiveBufferSize = settings.getAsBytesSize("tcp_receive_buffer_size", TCP_DEFAULT_RECEIVE_BUFFER_SIZE);

        logger.debug("using profile[{}], worker_count[{}], port[{}], bind_host[{}], publish_host[{}], compress[{}], connect_timeout[{}], connections_per_node[{}/{}/{}/{}/{}], receive_predictor[{}->{}]",
                name, workerCount, port, bindHost, publishHost, compress, connectTimeout, connectionsPerNodeRecovery, connectionsPerNodeBulk, connectionsPerNodeReg, connectionsPerNodeState, connectionsPerNodePing, receivePredictorMin, receivePredictorMax);

        final ThreadFactory bossFactory = daemonThreadFactory(this.settings, HTTP_SERVER_BOSS_THREAD_NAME_PREFIX, name);
        final ThreadFactory workerFactory = daemonThreadFactory(this.settings, HTTP_SERVER_WORKER_THREAD_NAME_PREFIX, name);
        ServerBootstrap serverBootstrap;
        if (blockingServer) {
            serverBootstrap = new ServerBootstrap(new OioServerSocketChannelFactory(
                    Executors.newCachedThreadPool(bossFactory),
                    Executors.newCachedThreadPool(workerFactory)
            ));
        } else {
            serverBootstrap = new ServerBootstrap(new NioServerSocketChannelFactory(
                    Executors.newCachedThreadPool(bossFactory),
                    Executors.newCachedThreadPool(workerFactory),
                    workerCount));
        }
        serverBootstrap.setPipelineFactory(configureServerChannelPipelineFactory(name, settings));
        if (!"default".equals(tcpNoDelay)) {
            serverBootstrap.setOption("child.tcpNoDelay", Booleans.parseBoolean(tcpNoDelay, null));
        }
        if (!"default".equals(tcpKeepAlive)) {
            serverBootstrap.setOption("child.keepAlive", Booleans.parseBoolean(tcpKeepAlive, null));
        }
        if (tcpSendBufferSize != null && tcpSendBufferSize.bytes() > 0) {
            serverBootstrap.setOption("child.sendBufferSize", tcpSendBufferSize.bytes());
        }
        if (tcpReceiveBufferSize != null && tcpReceiveBufferSize.bytes() > 0) {
            serverBootstrap.setOption("child.receiveBufferSize", tcpReceiveBufferSize.bytes());
        }
        serverBootstrap.setOption("receiveBufferSizePredictorFactory", receiveBufferSizePredictorFactory);
        serverBootstrap.setOption("child.receiveBufferSizePredictorFactory", receiveBufferSizePredictorFactory);
        serverBootstrap.setOption("reuseAddress", reuseAddress);
        serverBootstrap.setOption("child.reuseAddress", reuseAddress);

        serverBootstraps.put(name, serverBootstrap);
    }

    @Override
    protected void doStop() {
        final CountDownLatch latch = new CountDownLatch(1);
        // make sure we run it on another thread than a possible IO handler thread
        threadPool.generic().execute(new Runnable() {
            @Override
            public void run() {
                globalLock.writeLock().lock();
                try {
                    for (Iterator<NodeChannels> it = connectedNodes.values().iterator(); it.hasNext(); ) {
                        NodeChannels nodeChannels = it.next();
                        it.remove();
                        nodeChannels.close();
                    }

                    Iterator<Map.Entry<String, Channel>> serverChannelIterator = serverChannels.entrySet().iterator();
                    while (serverChannelIterator.hasNext()) {
                        Map.Entry<String, Channel> serverChannelEntry = serverChannelIterator.next();
                        String name = serverChannelEntry.getKey();
                        Channel serverChannel = serverChannelEntry.getValue();
                        try {
                            serverChannel.close().awaitUninterruptibly();
                        } catch (Throwable t) {
                            logger.debug("Error closing serverChannel for profile [{}]", t, name);
                        }
                        serverChannelIterator.remove();
                    }

                    if (serverOpenChannels != null) {
                        serverOpenChannels.close();
                        serverOpenChannels = null;
                    }

                    Iterator<Map.Entry<String, ServerBootstrap>> serverBootstrapIterator = serverBootstraps.entrySet().iterator();
                    while (serverBootstrapIterator.hasNext()) {
                        Map.Entry<String, ServerBootstrap> serverBootstrapEntry = serverBootstrapIterator.next();
                        String name = serverBootstrapEntry.getKey();
                        ServerBootstrap serverBootstrap = serverBootstrapEntry.getValue();

                        try {
                            serverBootstrap.releaseExternalResources();
                        } catch (Throwable t) {
                            logger.debug("Error closing serverBootstrap for profile [{}]", t, name);
                        }

                        serverBootstrapIterator.remove();
                    }

                    for (Iterator<NodeChannels> it = connectedNodes.values().iterator(); it.hasNext(); ) {
                        NodeChannels nodeChannels = it.next();
                        it.remove();
                        nodeChannels.close();
                    }

                    if (clientBootstrap != null) {
                        clientBootstrap.releaseExternalResources();
                        clientBootstrap = null;
                    }
                } finally {
                    globalLock.writeLock().unlock();
                    latch.countDown();
                }
            }
        });

        try {
            latch.await(30, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            // ignore
        }
    }

    @Override
    protected void doClose() {
    }

    @Override
    public TransportAddress[] addressesFromString(String address) throws Exception {
        int index = address.indexOf('[');
        if (index != -1) {
            String host = address.substring(0, index);
            Set<String> ports = Strings.commaDelimitedListToSet(address.substring(index + 1, address.indexOf(']')));
            List<TransportAddress> addresses = Lists.newArrayList();
            for (String port : ports) {
                int[] iPorts = new PortsRange(port).ports();
                for (int iPort : iPorts) {
                    addresses.add(new InetSocketTransportAddress(host, iPort));
                }
            }
            return addresses.toArray(new TransportAddress[addresses.size()]);
        } else {
            index = address.lastIndexOf(':');
            if (index == -1) {
                List<TransportAddress> addresses = Lists.newArrayList();
                String defaultPort = settings.get("transport.profiles.default.port", settings.get("transport.netty.port", this.settings.get("transport.tcp.port", DEFAULT_PORT_RANGE)));
                int[] iPorts = new PortsRange(defaultPort).ports();
                for (int iPort : iPorts) {
                    addresses.add(new InetSocketTransportAddress(address, iPort));
                }
                return addresses.toArray(new TransportAddress[addresses.size()]);
            } else {
                String host = address.substring(0, index);
                int port = Integer.parseInt(address.substring(index + 1));
                return new TransportAddress[]{new InetSocketTransportAddress(host, port)};
            }
        }
    }

    @Override
    public boolean addressSupported(Class<? extends TransportAddress> address) {
        return InetSocketTransportAddress.class.equals(address);
    }

    @Override
    public BoundTransportAddress boundAddress() {
        return this.boundAddress;
    }

    protected void exceptionCaught(ChannelHandlerContext ctx, ExceptionEvent e) throws Exception {
        if (!lifecycle.started()) {
            // ignore
            return;
        }
        if (isCloseConnectionException(e.getCause())) {
            logger.trace("close connection exception caught on transport layer [{}], disconnecting from relevant node", e.getCause(), ctx.getChannel());
            // close the channel, which will cause a node to be disconnected if relevant
            ctx.getChannel().close();
            disconnectFromNodeChannel(ctx.getChannel(), e.getCause());
        } else if (isConnectException(e.getCause())) {
            logger.trace("connect exception caught on transport layer [{}]", e.getCause(), ctx.getChannel());
            // close the channel as safe measure, which will cause a node to be disconnected if relevant
            ctx.getChannel().close();
            disconnectFromNodeChannel(ctx.getChannel(), e.getCause());
        } else if (e.getCause() instanceof CancelledKeyException) {
            logger.trace("cancelled key exception caught on transport layer [{}], disconnecting from relevant node", e.getCause(), ctx.getChannel());
            // close the channel as safe measure, which will cause a node to be disconnected if relevant
            ctx.getChannel().close();
            disconnectFromNodeChannel(ctx.getChannel(), e.getCause());
        } else if (e.getCause() instanceof SizeHeaderFrameDecoder.HttpOnTransportException) {
            // in case we are able to return data, serialize the exception content and sent it back to the client
            if (ctx.getChannel().isOpen()) {
                ChannelBuffer buffer = ChannelBuffers.wrappedBuffer(e.getCause().getMessage().getBytes(Charsets.UTF_8));
                ChannelFuture channelFuture = ctx.getChannel().write(buffer);
                channelFuture.addListener(new ChannelFutureListener() {
                    @Override
                    public void operationComplete(ChannelFuture future) throws Exception {
                        future.getChannel().close();
                    }
                });
            }
        } else {
            logger.warn("exception caught on transport layer [{}], closing connection", e.getCause(), ctx.getChannel());
            // close the channel, which will cause a node to be disconnected if relevant
            ctx.getChannel().close();
            disconnectFromNodeChannel(ctx.getChannel(), e.getCause());
        }
    }

    TransportAddress wrapAddress(SocketAddress socketAddress) {
        return new InetSocketTransportAddress((InetSocketAddress) socketAddress);
    }

    @Override
    public long serverOpen() {
        OpenChannelsHandler channels = serverOpenChannels;
        return channels == null ? 0 : channels.numberOfOpenChannels();
    }

    @Override
    public void sendRequest(final DiscoveryNode node, final long requestId, final String action, final TransportRequest request, TransportRequestOptions options) throws IOException, TransportException {

        Channel targetChannel = nodeChannel(node, options);

        if (compress) {
            options.withCompress(true);
        }

        byte status = 0;
        status = TransportStatus.setRequest(status);

        ReleasableBytesStreamOutput bStream = new ReleasableBytesStreamOutput(bigArrays);
        boolean addedReleaseListener = false;
        try {
            bStream.skip(NettyHeader.HEADER_SIZE);
            StreamOutput stream = bStream;
            // only compress if asked, and, the request is not bytes, since then only
            // the header part is compressed, and the "body" can't be extracted as compressed
            if (options.compress() && (!(request instanceof BytesTransportRequest))) {
                status = TransportStatus.setCompress(status);
                stream = CompressorFactory.defaultCompressor().streamOutput(stream);
            }

            // we pick the smallest of the 2, to support both backward and forward compatibility
            // note, this is the only place we need to do this, since from here on, we use the serialized version
            // as the version to use also when the node receiving this request will send the response with
            Version version = Version.smallest(this.version, node.version());

            stream.setVersion(version);
            stream.writeString(action);

            ReleasablePagedBytesReference bytes;
            ChannelBuffer buffer;
            // it might be nice to somehow generalize this optimization, maybe a smart "paged" bytes output
            // that create paged channel buffers, but its tricky to know when to do it (where this option is
            // more explicit).
            if (request instanceof BytesTransportRequest) {
                BytesTransportRequest bRequest = (BytesTransportRequest) request;
                assert node.version().equals(bRequest.version());
                bRequest.writeThin(stream);
                stream.close();
                bytes = bStream.bytes();
                ChannelBuffer headerBuffer = bytes.toChannelBuffer();
                ChannelBuffer contentBuffer = bRequest.bytes().toChannelBuffer();
                buffer = ChannelBuffers.wrappedBuffer(NettyUtils.DEFAULT_GATHERING, headerBuffer, contentBuffer);
            } else {
                request.writeTo(stream);
                stream.close();
                bytes = bStream.bytes();
                buffer = bytes.toChannelBuffer();
            }
            NettyHeader.writeHeader(buffer, requestId, status, version);
            ChannelFuture future = targetChannel.write(buffer);
            ReleaseChannelFutureListener listener = new ReleaseChannelFutureListener(bytes);
            future.addListener(listener);
            addedReleaseListener = true;
            transportServiceAdapter.onRequestSent(node, requestId, action, request, options);
        } finally {
            if (!addedReleaseListener) {
                Releasables.close(bStream.bytes());
            }
        }
    }

    @Override
    public boolean nodeConnected(DiscoveryNode node) {
        return connectedNodes.containsKey(node);
    }

    @Override
    public void connectToNodeLight(DiscoveryNode node) throws ConnectTransportException {
        connectToNode(node, true);
    }

    @Override
    public void connectToNode(DiscoveryNode node) {
        connectToNode(node, false);
    }

    public void connectToNode(DiscoveryNode node, boolean light) {
        if (!lifecycle.started()) {
            throw new IllegalStateException("can't add nodes to a stopped transport");
        }
        if (node == null) {
            throw new ConnectTransportException(null, "can't connect to a null node");
        }
        globalLock.readLock().lock();
        try {
            connectionLock.acquire(node.id());
            try {
                if (!lifecycle.started()) {
                    throw new IllegalStateException("can't add nodes to a stopped transport");
                }
                NodeChannels nodeChannels = connectedNodes.get(node);
                if (nodeChannels != null) {
                    return;
                }
                try {
                    if (light) {
                        nodeChannels = connectToChannelsLight(node);
                    } else {
                        nodeChannels = new NodeChannels(new Channel[connectionsPerNodeRecovery], new Channel[connectionsPerNodeBulk], new Channel[connectionsPerNodeReg], new Channel[connectionsPerNodeState], new Channel[connectionsPerNodePing]);
                        try {
                            connectToChannels(nodeChannels, node);
                        } catch (Throwable e) {
                            logger.trace("failed to connect to [{}], cleaning dangling connections", e, node);
                            nodeChannels.close();
                            throw e;
                        }
                    }
                    // we acquire a connection lock, so no way there is an existing connection
                    nodeChannels.start();
                    connectedNodes.put(node, nodeChannels);
                    if (logger.isDebugEnabled()) {
                        logger.debug("connected to node [{}]", node);
                    }
                    transportServiceAdapter.raiseNodeConnected(node);
                } catch (ConnectTransportException e) {
                    throw e;
                } catch (Exception e) {
                    throw new ConnectTransportException(node, "general node connection failure", e);
                }
            } finally {
                connectionLock.release(node.id());
            }
        } finally {
            globalLock.readLock().unlock();
        }
    }

    protected NodeChannels connectToChannelsLight(DiscoveryNode node) {
        InetSocketAddress address = ((InetSocketTransportAddress) node.address()).address();
        ChannelFuture connect = clientBootstrap.connect(address);
        connect.awaitUninterruptibly((long) (connectTimeout.millis() * 1.5));
        if (!connect.isSuccess()) {
            throw new ConnectTransportException(node, "connect_timeout[" + connectTimeout + "]", connect.getCause());
        }
        Channel[] channels = new Channel[1];
        channels[0] = connect.getChannel();
        channels[0].getCloseFuture().addListener(new ChannelCloseListener(node));
        return new NodeChannels(channels, channels, channels, channels, channels);
    }

    protected void connectToChannels(NodeChannels nodeChannels, DiscoveryNode node) {
        ChannelFuture[] connectRecovery = new ChannelFuture[nodeChannels.recovery.length];
        ChannelFuture[] connectBulk = new ChannelFuture[nodeChannels.bulk.length];
        ChannelFuture[] connectReg = new ChannelFuture[nodeChannels.reg.length];
        ChannelFuture[] connectState = new ChannelFuture[nodeChannels.state.length];
        ChannelFuture[] connectPing = new ChannelFuture[nodeChannels.ping.length];
        InetSocketAddress address = ((InetSocketTransportAddress) node.address()).address();
        for (int i = 0; i < connectRecovery.length; i++) {
            connectRecovery[i] = clientBootstrap.connect(address);
        }
        for (int i = 0; i < connectBulk.length; i++) {
            connectBulk[i] = clientBootstrap.connect(address);
        }
        for (int i = 0; i < connectReg.length; i++) {
            connectReg[i] = clientBootstrap.connect(address);
        }
        for (int i = 0; i < connectState.length; i++) {
            connectState[i] = clientBootstrap.connect(address);
        }
        for (int i = 0; i < connectPing.length; i++) {
            connectPing[i] = clientBootstrap.connect(address);
        }

        try {
            for (int i = 0; i < connectRecovery.length; i++) {
                connectRecovery[i].awaitUninterruptibly((long) (connectTimeout.millis() * 1.5));
                if (!connectRecovery[i].isSuccess()) {
                    throw new ConnectTransportException(node, "connect_timeout[" + connectTimeout + "]", connectRecovery[i].getCause());
                }
                nodeChannels.recovery[i] = connectRecovery[i].getChannel();
                nodeChannels.recovery[i].getCloseFuture().addListener(new ChannelCloseListener(node));
            }

            for (int i = 0; i < connectBulk.length; i++) {
                connectBulk[i].awaitUninterruptibly((long) (connectTimeout.millis() * 1.5));
                if (!connectBulk[i].isSuccess()) {
                    throw new ConnectTransportException(node, "connect_timeout[" + connectTimeout + "]", connectBulk[i].getCause());
                }
                nodeChannels.bulk[i] = connectBulk[i].getChannel();
                nodeChannels.bulk[i].getCloseFuture().addListener(new ChannelCloseListener(node));
            }

            for (int i = 0; i < connectReg.length; i++) {
                connectReg[i].awaitUninterruptibly((long) (connectTimeout.millis() * 1.5));
                if (!connectReg[i].isSuccess()) {
                    throw new ConnectTransportException(node, "connect_timeout[" + connectTimeout + "]", connectReg[i].getCause());
                }
                nodeChannels.reg[i] = connectReg[i].getChannel();
                nodeChannels.reg[i].getCloseFuture().addListener(new ChannelCloseListener(node));
            }

            for (int i = 0; i < connectState.length; i++) {
                connectState[i].awaitUninterruptibly((long) (connectTimeout.millis() * 1.5));
                if (!connectState[i].isSuccess()) {
                    throw new ConnectTransportException(node, "connect_timeout[" + connectTimeout + "]", connectState[i].getCause());
                }
                nodeChannels.state[i] = connectState[i].getChannel();
                nodeChannels.state[i].getCloseFuture().addListener(new ChannelCloseListener(node));
            }

            for (int i = 0; i < connectPing.length; i++) {
                connectPing[i].awaitUninterruptibly((long) (connectTimeout.millis() * 1.5));
                if (!connectPing[i].isSuccess()) {
                    throw new ConnectTransportException(node, "connect_timeout[" + connectTimeout + "]", connectPing[i].getCause());
                }
                nodeChannels.ping[i] = connectPing[i].getChannel();
                nodeChannels.ping[i].getCloseFuture().addListener(new ChannelCloseListener(node));
            }

            if (nodeChannels.recovery.length == 0) {
                if (nodeChannels.bulk.length > 0) {
                    nodeChannels.recovery = nodeChannels.bulk;
                } else {
                    nodeChannels.recovery = nodeChannels.reg;
                }
            }
            if (nodeChannels.bulk.length == 0) {
                nodeChannels.bulk = nodeChannels.reg;
            }
        } catch (RuntimeException e) {
            // clean the futures
            for (ChannelFuture future : ImmutableList.<ChannelFuture>builder().add(connectRecovery).add(connectBulk).add(connectReg).add(connectState).add(connectPing).build()) {
                future.cancel();
                if (future.getChannel() != null && future.getChannel().isOpen()) {
                    try {
                        future.getChannel().close();
                    } catch (Exception e1) {
                        // ignore
                    }
                }
            }
            throw e;
        }
    }

    @Override
    public void disconnectFromNode(DiscoveryNode node) {
        connectionLock.acquire(node.id());
        try {
            NodeChannels nodeChannels = connectedNodes.remove(node);
            if (nodeChannels != null) {
                try {
                    logger.debug("disconnecting from [{}] due to explicit disconnect call", node);
                    nodeChannels.close();
                } finally {
                    logger.trace("disconnected from [{}] due to explicit disconnect call", node);
                    transportServiceAdapter.raiseNodeDisconnected(node);
                }
            }
        } finally {
            connectionLock.release(node.id());
        }
    }

    /**
     * Disconnects from a node, only if the relevant channel is found to be part of the node channels.
     */
    protected boolean disconnectFromNode(DiscoveryNode node, Channel channel, String reason) {
        // this might be called multiple times from all the node channels, so do a lightweight
        // check outside of the lock
        NodeChannels nodeChannels = connectedNodes.get(node);
        if (nodeChannels != null && nodeChannels.hasChannel(channel)) {
            connectionLock.acquire(node.id());
            try {
                nodeChannels = connectedNodes.get(node);
                // check again within the connection lock, if its still applicable to remove it
                if (nodeChannels != null && nodeChannels.hasChannel(channel)) {
                    connectedNodes.remove(node);
                    try {
                        logger.debug("disconnecting from [{}], {}", node, reason);
                        nodeChannels.close();
                    } finally {
                        logger.trace("disconnected from [{}], {}", node, reason);
                        transportServiceAdapter.raiseNodeDisconnected(node);
                    }
                    return true;
                }
            } finally {
                connectionLock.release(node.id());
            }
        }
        return false;
    }

    /**
     * Disconnects from a node if a channel is found as part of that nodes channels.
     */
    protected void disconnectFromNodeChannel(final Channel channel, final Throwable failure) {
        threadPool().generic().execute(new Runnable() {

            @Override
            public void run() {
                for (DiscoveryNode node : connectedNodes.keySet()) {
                    if (disconnectFromNode(node, channel, ExceptionsHelper.detailedMessage(failure))) {
                        // if we managed to find this channel and disconnect from it, then break, no need to check on
                        // the rest of the nodes
                        break;
                    }
                }
            }
        });
    }

    protected Channel nodeChannel(DiscoveryNode node, TransportRequestOptions options) throws ConnectTransportException {
        NodeChannels nodeChannels = connectedNodes.get(node);
        if (nodeChannels == null) {
            throw new NodeNotConnectedException(node, "Node not connected");
        }
        return nodeChannels.channel(options.type());
    }

    public ChannelPipelineFactory configureClientChannelPipelineFactory() {
        return new ClientChannelPipelineFactory(this);
    }

    protected static class ClientChannelPipelineFactory implements ChannelPipelineFactory {
        protected NettyTransport nettyTransport;

        public ClientChannelPipelineFactory(NettyTransport nettyTransport) {
            this.nettyTransport = nettyTransport;
        }

        @Override
        public ChannelPipeline getPipeline() throws Exception {
            ChannelPipeline channelPipeline = Channels.pipeline();
            SizeHeaderFrameDecoder sizeHeader = new SizeHeaderFrameDecoder();
            if (nettyTransport.maxCumulationBufferCapacity != null) {
                if (nettyTransport.maxCumulationBufferCapacity.bytes() > Integer.MAX_VALUE) {
                    sizeHeader.setMaxCumulationBufferCapacity(Integer.MAX_VALUE);
                } else {
                    sizeHeader.setMaxCumulationBufferCapacity((int) nettyTransport.maxCumulationBufferCapacity.bytes());
                }
            }
            if (nettyTransport.maxCompositeBufferComponents != -1) {
                sizeHeader.setMaxCumulationBufferComponents(nettyTransport.maxCompositeBufferComponents);
            }
            channelPipeline.addLast("size", sizeHeader);
            // using a dot as a prefix means, this cannot come from any settings parsed
            channelPipeline.addLast("dispatcher", new MessageChannelHandler(nettyTransport, nettyTransport.logger, ".client"));
            return channelPipeline;
        }
    }

    public ChannelPipelineFactory configureServerChannelPipelineFactory(String name, Settings settings) {
        return new ServerChannelPipelineFactory(this, name, settings);
    }

    protected static class ServerChannelPipelineFactory implements ChannelPipelineFactory {

        protected final NettyTransport nettyTransport;
        protected final String name;
        protected final Settings settings;

        public ServerChannelPipelineFactory(NettyTransport nettyTransport, String name, Settings settings) {
            this.nettyTransport = nettyTransport;
            this.name = name;
            this.settings = settings;
        }

        @Override
        public ChannelPipeline getPipeline() throws Exception {
            ChannelPipeline channelPipeline = Channels.pipeline();
            channelPipeline.addLast("openChannels", nettyTransport.serverOpenChannels);
            SizeHeaderFrameDecoder sizeHeader = new SizeHeaderFrameDecoder();
            if (nettyTransport.maxCumulationBufferCapacity != null) {
                if (nettyTransport.maxCumulationBufferCapacity.bytes() > Integer.MAX_VALUE) {
                    sizeHeader.setMaxCumulationBufferCapacity(Integer.MAX_VALUE);
                } else {
                    sizeHeader.setMaxCumulationBufferCapacity((int) nettyTransport.maxCumulationBufferCapacity.bytes());
                }
            }
            if (nettyTransport.maxCompositeBufferComponents != -1) {
                sizeHeader.setMaxCumulationBufferComponents(nettyTransport.maxCompositeBufferComponents);
            }
            channelPipeline.addLast("size", sizeHeader);
            channelPipeline.addLast("dispatcher", new MessageChannelHandler(nettyTransport, nettyTransport.logger, name));
            return channelPipeline;
        }
    }

    protected class ChannelCloseListener implements ChannelFutureListener {

        private final DiscoveryNode node;

        private ChannelCloseListener(DiscoveryNode node) {
            this.node = node;
        }

        @Override
        public void operationComplete(final ChannelFuture future) throws Exception {
            NodeChannels nodeChannels = connectedNodes.get(node);
            if (nodeChannels != null && nodeChannels.hasChannel(future.getChannel())) {
                threadPool().generic().execute(new Runnable() {
                    @Override
                    public void run() {
                        disconnectFromNode(node, future.getChannel(), "channel closed event");
                    }
                });
            }
        }
    }

    public static class NodeChannels {

        ImmutableList<Channel> allChannels = ImmutableList.of();
        private Channel[] recovery;
        private final AtomicInteger recoveryCounter = new AtomicInteger();
        private Channel[] bulk;
        private final AtomicInteger bulkCounter = new AtomicInteger();
        private Channel[] reg;
        private final AtomicInteger regCounter = new AtomicInteger();
        private Channel[] state;
        private final AtomicInteger stateCounter = new AtomicInteger();
        private Channel[] ping;
        private final AtomicInteger pingCounter = new AtomicInteger();

        public NodeChannels(Channel[] recovery, Channel[] bulk, Channel[] reg, Channel[] state, Channel[] ping) {
            this.recovery = recovery;
            this.bulk = bulk;
            this.reg = reg;
            this.state = state;
            this.ping = ping;
        }

        public void start() {
            this.allChannels = ImmutableList.<Channel>builder().add(recovery).add(bulk).add(reg).add(state).add(ping).build();
        }

        public boolean hasChannel(Channel channel) {
            for (Channel channel1 : allChannels) {
                if (channel.equals(channel1)) {
                    return true;
                }
            }
            return false;
        }

        public Channel channel(TransportRequestOptions.Type type) {
            if (type == TransportRequestOptions.Type.REG) {
                return reg[MathUtils.mod(regCounter.incrementAndGet(), reg.length)];
            } else if (type == TransportRequestOptions.Type.STATE) {
                return state[MathUtils.mod(stateCounter.incrementAndGet(), state.length)];
            } else if (type == TransportRequestOptions.Type.PING) {
                return ping[MathUtils.mod(pingCounter.incrementAndGet(), ping.length)];
            } else if (type == TransportRequestOptions.Type.BULK) {
                return bulk[MathUtils.mod(bulkCounter.incrementAndGet(), bulk.length)];
            } else if (type == TransportRequestOptions.Type.RECOVERY) {
                return recovery[MathUtils.mod(recoveryCounter.incrementAndGet(), recovery.length)];
            } else {
                throw new IllegalArgumentException("no type channel for [" + type + "]");
            }
        }

        public synchronized void close() {
            List<ChannelFuture> futures = new ArrayList<>();
            for (Channel channel : allChannels) {
                try {
                    if (channel != null && channel.isOpen()) {
                        futures.add(channel.close());
                    }
                } catch (Exception e) {
                    //ignore
                }
            }
            for (ChannelFuture future : futures) {
                future.awaitUninterruptibly();
            }
        }
    }

    class ScheduledPing implements Runnable {

        final CounterMetric successfulPings = new CounterMetric();
        final CounterMetric failedPings = new CounterMetric();

        @Override
        public void run() {
            if (lifecycle.stoppedOrClosed()) {
                return;
            }
            for (Map.Entry<DiscoveryNode, NodeChannels> entry : connectedNodes.entrySet()) {
                DiscoveryNode node = entry.getKey();
                NodeChannels channels = entry.getValue();
                for (Channel channel : channels.allChannels) {
                    try {
                        ChannelFuture future = channel.write(NettyHeader.pingHeader());
                        future.addListener(new ChannelFutureListener() {
                            @Override
                            public void operationComplete(ChannelFuture future) throws Exception {
                                successfulPings.inc();
                            }
                        });
                    } catch (Throwable t) {
                        if (channel.isOpen()) {
                            logger.debug("[{}] failed to send ping transport message", t, node);
                            failedPings.inc();
                        } else {
                            logger.trace("[{}] failed to send ping transport message (channel closed)", t, node);
                        }
                    }
                }
            }
            threadPool.schedule(pingSchedule, ThreadPool.Names.GENERIC, this);
        }
    }
}


File: core/src/test/java/org/elasticsearch/benchmark/transport/BenchmarkNettyLargeMessages.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.benchmark.transport;

import org.apache.lucene.util.BytesRef;
import org.elasticsearch.Version;
import org.elasticsearch.cluster.node.DiscoveryNode;
import org.elasticsearch.cluster.settings.DynamicSettings;
import org.elasticsearch.common.network.NetworkService;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.transport.InetSocketTransportAddress;
import org.elasticsearch.common.unit.ByteSizeUnit;
import org.elasticsearch.common.unit.ByteSizeValue;
import org.elasticsearch.common.util.BigArrays;
import org.elasticsearch.node.settings.NodeSettingsService;
import org.elasticsearch.threadpool.ThreadPool;
import org.elasticsearch.transport.*;
import org.elasticsearch.transport.netty.NettyTransport;

import java.util.concurrent.CountDownLatch;

import static org.elasticsearch.transport.TransportRequestOptions.options;

/**
 *
 */
public class BenchmarkNettyLargeMessages {

    public static void main(String[] args) throws InterruptedException {
        final ByteSizeValue payloadSize = new ByteSizeValue(10, ByteSizeUnit.MB);
        final int NUMBER_OF_ITERATIONS = 100000;
        final int NUMBER_OF_CLIENTS = 5;
        final byte[] payload = new byte[(int) payloadSize.bytes()];

        Settings settings = Settings.settingsBuilder()
                .build();

        NetworkService networkService = new NetworkService(settings);
        NodeSettingsService settingsService = new NodeSettingsService(settings);
        DynamicSettings dynamicSettings = new DynamicSettings();


        final ThreadPool threadPool = new ThreadPool("BenchmarkNettyLargeMessages");
        final TransportService transportServiceServer = new TransportService(
                new NettyTransport(settings, threadPool, networkService, BigArrays.NON_RECYCLING_INSTANCE, Version.CURRENT), threadPool
        ).start();
        final TransportService transportServiceClient = new TransportService(
                new NettyTransport(settings, threadPool, networkService, BigArrays.NON_RECYCLING_INSTANCE, Version.CURRENT), threadPool
        ).start();

        final DiscoveryNode bigNode = new DiscoveryNode("big", new InetSocketTransportAddress("localhost", 9300), Version.CURRENT);
//        final DiscoveryNode smallNode = new DiscoveryNode("small", new InetSocketTransportAddress("localhost", 9300));
        final DiscoveryNode smallNode = bigNode;

        transportServiceClient.connectToNode(bigNode);
        transportServiceClient.connectToNode(smallNode);

        transportServiceServer.registerRequestHandler("benchmark", BenchmarkMessageRequest.class, ThreadPool.Names.GENERIC, new TransportRequestHandler<BenchmarkMessageRequest>() {
            @Override
            public void messageReceived(BenchmarkMessageRequest request, TransportChannel channel) throws Exception {
                channel.sendResponse(new BenchmarkMessageResponse(request));
            }
        });

        final CountDownLatch latch = new CountDownLatch(NUMBER_OF_CLIENTS);
        for (int i = 0; i < NUMBER_OF_CLIENTS; i++) {
            new Thread(new Runnable() {
                @Override
                public void run() {
                    for (int i = 0; i < NUMBER_OF_ITERATIONS; i++) {
                        BenchmarkMessageRequest message = new BenchmarkMessageRequest(1, payload);
                        transportServiceClient.submitRequest(bigNode, "benchmark", message, options().withType(TransportRequestOptions.Type.BULK), new BaseTransportResponseHandler<BenchmarkMessageResponse>() {
                            @Override
                            public BenchmarkMessageResponse newInstance() {
                                return new BenchmarkMessageResponse();
                            }

                            @Override
                            public String executor() {
                                return ThreadPool.Names.SAME;
                            }

                            @Override
                            public void handleResponse(BenchmarkMessageResponse response) {
                            }

                            @Override
                            public void handleException(TransportException exp) {
                                exp.printStackTrace();
                            }
                        }).txGet();
                    }
                    latch.countDown();
                }
            }).start();
        }

        new Thread(new Runnable() {
            @Override
            public void run() {
                for (int i = 0; i < 1; i++) {
                    BenchmarkMessageRequest message = new BenchmarkMessageRequest(2, BytesRef.EMPTY_BYTES);
                    long start = System.currentTimeMillis();
                    transportServiceClient.submitRequest(smallNode, "benchmark", message, options().withType(TransportRequestOptions.Type.STATE), new BaseTransportResponseHandler<BenchmarkMessageResponse>() {
                        @Override
                        public BenchmarkMessageResponse newInstance() {
                            return new BenchmarkMessageResponse();
                        }

                        @Override
                        public String executor() {
                            return ThreadPool.Names.SAME;
                        }

                        @Override
                        public void handleResponse(BenchmarkMessageResponse response) {
                        }

                        @Override
                        public void handleException(TransportException exp) {
                            exp.printStackTrace();
                        }
                    }).txGet();
                    long took = System.currentTimeMillis() - start;
                    System.out.println("Took " + took + "ms");
                }
            }
        }).start();

        latch.await();
    }
}


File: core/src/test/java/org/elasticsearch/benchmark/transport/TransportBenchmark.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.benchmark.transport;

import org.elasticsearch.Version;
import org.elasticsearch.cluster.node.DiscoveryNode;
import org.elasticsearch.common.StopWatch;
import org.elasticsearch.common.network.NetworkService;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.unit.ByteSizeUnit;
import org.elasticsearch.common.unit.ByteSizeValue;
import org.elasticsearch.common.util.BigArrays;
import org.elasticsearch.threadpool.ThreadPool;
import org.elasticsearch.transport.*;
import org.elasticsearch.transport.local.LocalTransport;
import org.elasticsearch.transport.netty.NettyTransport;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicLong;

/**
 *
 */
public class TransportBenchmark {

    static enum Type {
        LOCAL {
            @Override
            public Transport newTransport(Settings settings, ThreadPool threadPool) {
                return new LocalTransport(settings, threadPool, Version.CURRENT);
            }
        },
        NETTY {
            @Override
            public Transport newTransport(Settings settings, ThreadPool threadPool) {
                return new NettyTransport(settings, threadPool, new NetworkService(Settings.EMPTY), BigArrays.NON_RECYCLING_INSTANCE, Version.CURRENT);
            }
        };

        public abstract Transport newTransport(Settings settings, ThreadPool threadPool);
    }

    public static void main(String[] args) {
        final String executor = ThreadPool.Names.GENERIC;
        final boolean waitForRequest = true;
        final ByteSizeValue payloadSize = new ByteSizeValue(100, ByteSizeUnit.BYTES);
        final int NUMBER_OF_CLIENTS = 10;
        final int NUMBER_OF_ITERATIONS = 100000;
        final byte[] payload = new byte[(int) payloadSize.bytes()];
        final AtomicLong idGenerator = new AtomicLong();
        final Type type = Type.NETTY;


        Settings settings = Settings.settingsBuilder()
                .build();

        final ThreadPool serverThreadPool = new ThreadPool("server");
        final TransportService serverTransportService = new TransportService(type.newTransport(settings, serverThreadPool), serverThreadPool).start();

        final ThreadPool clientThreadPool = new ThreadPool("client");
        final TransportService clientTransportService = new TransportService(type.newTransport(settings, clientThreadPool), clientThreadPool).start();

        final DiscoveryNode node = new DiscoveryNode("server", serverTransportService.boundAddress().publishAddress(), Version.CURRENT);

        serverTransportService.registerRequestHandler("benchmark", BenchmarkMessageRequest.class, executor, new TransportRequestHandler<BenchmarkMessageRequest>() {
            @Override
            public void messageReceived(BenchmarkMessageRequest request, TransportChannel channel) throws Exception {
                channel.sendResponse(new BenchmarkMessageResponse(request));
            }
        });

        clientTransportService.connectToNode(node);

        for (int i = 0; i < 10000; i++) {
            BenchmarkMessageRequest message = new BenchmarkMessageRequest(1, payload);
            clientTransportService.submitRequest(node, "benchmark", message, new BaseTransportResponseHandler<BenchmarkMessageResponse>() {
                @Override
                public BenchmarkMessageResponse newInstance() {
                    return new BenchmarkMessageResponse();
                }

                @Override
                public String executor() {
                    return ThreadPool.Names.SAME;
                }

                @Override
                public void handleResponse(BenchmarkMessageResponse response) {
                }

                @Override
                public void handleException(TransportException exp) {
                    exp.printStackTrace();
                }
            }).txGet();
        }


        Thread[] clients = new Thread[NUMBER_OF_CLIENTS];
        final CountDownLatch latch = new CountDownLatch(NUMBER_OF_CLIENTS * NUMBER_OF_ITERATIONS);
        for (int i = 0; i < NUMBER_OF_CLIENTS; i++) {
            clients[i] = new Thread(new Runnable() {
                @Override
                public void run() {
                    for (int j = 0; j < NUMBER_OF_ITERATIONS; j++) {
                        final long id = idGenerator.incrementAndGet();
                        BenchmarkMessageRequest request = new BenchmarkMessageRequest(id, payload);
                        BaseTransportResponseHandler<BenchmarkMessageResponse> handler = new BaseTransportResponseHandler<BenchmarkMessageResponse>() {
                            @Override
                            public BenchmarkMessageResponse newInstance() {
                                return new BenchmarkMessageResponse();
                            }

                            @Override
                            public String executor() {
                                return executor;
                            }

                            @Override
                            public void handleResponse(BenchmarkMessageResponse response) {
                                if (response.id() != id) {
                                    System.out.println("NO ID MATCH [" + response.id() + "] and [" + id + "]");
                                }
                                latch.countDown();
                            }

                            @Override
                            public void handleException(TransportException exp) {
                                exp.printStackTrace();
                                latch.countDown();
                            }
                        };

                        if (waitForRequest) {
                            clientTransportService.submitRequest(node, "benchmark", request, handler).txGet();
                        } else {
                            clientTransportService.sendRequest(node, "benchmark", request, handler);
                        }
                    }
                }
            });
        }

        StopWatch stopWatch = new StopWatch().start();
        for (int i = 0; i < NUMBER_OF_CLIENTS; i++) {
            clients[i].start();
        }

        try {
            latch.await();
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        stopWatch.stop();

        System.out.println("Ran [" + NUMBER_OF_CLIENTS + "], each with [" + NUMBER_OF_ITERATIONS + "] iterations, payload [" + payloadSize + "]: took [" + stopWatch.totalTime() + "], TPS: " + (NUMBER_OF_CLIENTS * NUMBER_OF_ITERATIONS) / stopWatch.totalTime().secondsFrac());

        clientTransportService.close();
        clientThreadPool.shutdownNow();

        serverTransportService.close();
        serverThreadPool.shutdownNow();
    }
}

File: core/src/test/java/org/elasticsearch/cluster/ClusterStateDiffPublishingTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.cluster;

import com.google.common.collect.ImmutableMap;
import org.elasticsearch.Version;
import org.elasticsearch.cluster.block.ClusterBlocks;
import org.elasticsearch.cluster.metadata.IndexMetaData;
import org.elasticsearch.cluster.metadata.MetaData;
import org.elasticsearch.cluster.node.DiscoveryNode;
import org.elasticsearch.cluster.node.DiscoveryNodes;
import org.elasticsearch.common.Nullable;
import org.elasticsearch.common.collect.ImmutableOpenMap;
import org.elasticsearch.common.collect.Tuple;
import org.elasticsearch.common.io.stream.StreamOutput;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.discovery.Discovery;
import org.elasticsearch.discovery.DiscoverySettings;
import org.elasticsearch.discovery.zen.DiscoveryNodesProvider;
import org.elasticsearch.discovery.zen.publish.PublishClusterStateAction;
import org.elasticsearch.node.service.NodeService;
import org.elasticsearch.node.settings.NodeSettingsService;
import org.elasticsearch.test.ElasticsearchTestCase;
import org.elasticsearch.test.junit.annotations.TestLogging;
import org.elasticsearch.test.transport.MockTransportService;
import org.elasticsearch.threadpool.ThreadPool;
import org.elasticsearch.transport.TransportConnectionListener;
import org.elasticsearch.transport.TransportService;
import org.elasticsearch.transport.local.LocalTransport;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

import static com.google.common.collect.Maps.newHashMap;
import static org.hamcrest.Matchers.*;

public class ClusterStateDiffPublishingTests extends ElasticsearchTestCase {

    protected ThreadPool threadPool;
    protected Map<String, MockNode> nodes = newHashMap();

    public static class MockNode {
        public final DiscoveryNode discoveryNode;
        public final MockTransportService service;
        public final PublishClusterStateAction action;
        public final MockDiscoveryNodesProvider nodesProvider;

        public MockNode(DiscoveryNode discoveryNode, MockTransportService service, PublishClusterStateAction action, MockDiscoveryNodesProvider nodesProvider) {
            this.discoveryNode = discoveryNode;
            this.service = service;
            this.action = action;
            this.nodesProvider = nodesProvider;
        }

        public void connectTo(DiscoveryNode node) {
            service.connectToNode(node);
            nodesProvider.addNode(node);
        }
    }

    public MockNode createMockNode(final String name, Settings settings, Version version) throws Exception {
        return createMockNode(name, settings, version, new PublishClusterStateAction.NewClusterStateListener() {
            @Override
            public void onNewClusterState(ClusterState clusterState, NewStateProcessed newStateProcessed) {
                logger.debug("Node [{}] onNewClusterState version [{}], uuid [{}]", name, clusterState.version(), clusterState.uuid());
                newStateProcessed.onNewClusterStateProcessed();
            }
        });
    }

    public MockNode createMockNode(String name, Settings settings, Version version, PublishClusterStateAction.NewClusterStateListener listener) throws Exception {
        MockTransportService service = buildTransportService(
                Settings.builder().put(settings).put("name", name, TransportService.SETTING_TRACE_LOG_INCLUDE, "", TransportService.SETTING_TRACE_LOG_EXCLUDE, "NOTHING").build(),
                version
        );
        DiscoveryNode discoveryNode = new DiscoveryNode(name, name, service.boundAddress().publishAddress(), ImmutableMap.<String, String>of(), version);
        MockDiscoveryNodesProvider nodesProvider = new MockDiscoveryNodesProvider(discoveryNode);
        PublishClusterStateAction action = buildPublishClusterStateAction(settings, service, nodesProvider, listener);
        MockNode node = new MockNode(discoveryNode, service, action, nodesProvider);
        nodesProvider.addNode(discoveryNode);
        final CountDownLatch latch = new CountDownLatch(nodes.size() * 2 + 1);
        TransportConnectionListener waitForConnection = new TransportConnectionListener() {
            @Override
            public void onNodeConnected(DiscoveryNode node) {
                latch.countDown();
            }

            @Override
            public void onNodeDisconnected(DiscoveryNode node) {
                fail("disconnect should not be called " + node);
            }
        };
        node.service.addConnectionListener(waitForConnection);
        for (MockNode curNode : nodes.values()) {
            curNode.service.addConnectionListener(waitForConnection);
            curNode.connectTo(node.discoveryNode);
            node.connectTo(curNode.discoveryNode);
        }
        node.connectTo(node.discoveryNode);
        assertThat("failed to wait for all nodes to connect", latch.await(5, TimeUnit.SECONDS), equalTo(true));
        for (MockNode curNode : nodes.values()) {
            curNode.service.removeConnectionListener(waitForConnection);
        }
        node.service.removeConnectionListener(waitForConnection);
        if (nodes.put(name, node) != null) {
            fail("Node with the name " + name + " already exist");
        }
        return node;
    }

    public MockTransportService service(String name) {
        MockNode node = nodes.get(name);
        if (node != null) {
            return node.service;
        }
        return null;
    }

    public PublishClusterStateAction action(String name) {
        MockNode node = nodes.get(name);
        if (node != null) {
            return node.action;
        }
        return null;
    }

    @Override
    @Before
    public void setUp() throws Exception {
        super.setUp();
        threadPool = new ThreadPool(getClass().getName());
    }

    @Override
    @After
    public void tearDown() throws Exception {
        super.tearDown();
        for (MockNode curNode : nodes.values()) {
            curNode.action.close();
            curNode.service.close();
        }
        terminate(threadPool);
    }

    protected MockTransportService buildTransportService(Settings settings, Version version) {
        MockTransportService transportService = new MockTransportService(settings, new LocalTransport(settings, threadPool, version), threadPool);
        transportService.start();
        return transportService;
    }

    protected PublishClusterStateAction buildPublishClusterStateAction(Settings settings, MockTransportService transportService, MockDiscoveryNodesProvider nodesProvider,
                                                                       PublishClusterStateAction.NewClusterStateListener listener) {
        DiscoverySettings discoverySettings = new DiscoverySettings(settings, new NodeSettingsService(settings));
        return new PublishClusterStateAction(settings, transportService, nodesProvider, listener, discoverySettings);
    }


    static class MockDiscoveryNodesProvider implements DiscoveryNodesProvider {

        private DiscoveryNodes discoveryNodes = DiscoveryNodes.EMPTY_NODES;

        public MockDiscoveryNodesProvider(DiscoveryNode localNode) {
            discoveryNodes = DiscoveryNodes.builder().put(localNode).localNodeId(localNode.id()).build();
        }

        public void addNode(DiscoveryNode node) {
            discoveryNodes = DiscoveryNodes.builder(discoveryNodes).put(node).build();
        }

        @Override
        public DiscoveryNodes nodes() {
            return discoveryNodes;
        }

        @Override
        public NodeService nodeService() {
            assert false;
            throw new UnsupportedOperationException("Shouldn't be here");
        }
    }


    @Test
    @TestLogging("cluster:DEBUG,discovery.zen.publish:DEBUG")
    public void testSimpleClusterStatePublishing() throws Exception {
        MockNewClusterStateListener mockListenerA = new MockNewClusterStateListener();
        MockNode nodeA = createMockNode("nodeA", Settings.EMPTY, Version.CURRENT, mockListenerA);

        MockNewClusterStateListener mockListenerB = new MockNewClusterStateListener();
        MockNode nodeB = createMockNode("nodeB", Settings.EMPTY, Version.CURRENT, mockListenerB);

        // Initial cluster state
        DiscoveryNodes discoveryNodes = DiscoveryNodes.builder().put(nodeA.discoveryNode).localNodeId(nodeA.discoveryNode.id()).build();
        ClusterState clusterState = ClusterState.builder(new ClusterName("test")).nodes(discoveryNodes).build();

        // cluster state update - add nodeB
        discoveryNodes = DiscoveryNodes.builder(discoveryNodes).put(nodeB.discoveryNode).build();
        ClusterState previousClusterState = clusterState;
        clusterState = ClusterState.builder(clusterState).nodes(discoveryNodes).incrementVersion().build();
        mockListenerB.add(new NewClusterStateExpectation() {
            @Override
            public void check(ClusterState clusterState, PublishClusterStateAction.NewClusterStateListener.NewStateProcessed newStateProcessed) {
                assertFalse(clusterState.wasReadFromDiff());
            }
        });
        publishStateDiffAndWait(nodeA.action, clusterState, previousClusterState);

        // cluster state update - add block
        previousClusterState = clusterState;
        clusterState = ClusterState.builder(clusterState).blocks(ClusterBlocks.builder().addGlobalBlock(MetaData.CLUSTER_READ_ONLY_BLOCK)).incrementVersion().build();
        mockListenerB.add(new NewClusterStateExpectation() {
            @Override
            public void check(ClusterState clusterState, PublishClusterStateAction.NewClusterStateListener.NewStateProcessed newStateProcessed) {
                assertTrue(clusterState.wasReadFromDiff());
                assertThat(clusterState.blocks().global().size(), equalTo(1));
            }
        });
        publishStateDiffAndWait(nodeA.action, clusterState, previousClusterState);

        // cluster state update - remove block
        previousClusterState = clusterState;
        clusterState = ClusterState.builder(clusterState).blocks(ClusterBlocks.EMPTY_CLUSTER_BLOCK).incrementVersion().build();
        mockListenerB.add(new NewClusterStateExpectation() {
            @Override
            public void check(ClusterState clusterState, PublishClusterStateAction.NewClusterStateListener.NewStateProcessed newStateProcessed) {
                assertTrue(clusterState.wasReadFromDiff());
                assertThat(clusterState.blocks().global().size(), equalTo(0));
            }
        });
        publishStateDiffAndWait(nodeA.action, clusterState, previousClusterState);

        // Adding new node - this node should get full cluster state while nodeB should still be getting diffs

        MockNewClusterStateListener mockListenerC = new MockNewClusterStateListener();
        MockNode nodeC = createMockNode("nodeC", Settings.EMPTY, Version.CURRENT, mockListenerC);

        // cluster state update 3 - register node C
        previousClusterState = clusterState;
        discoveryNodes = DiscoveryNodes.builder(discoveryNodes).put(nodeC.discoveryNode).build();
        clusterState = ClusterState.builder(clusterState).nodes(discoveryNodes).incrementVersion().build();
        mockListenerB.add(new NewClusterStateExpectation() {
            @Override
            public void check(ClusterState clusterState, PublishClusterStateAction.NewClusterStateListener.NewStateProcessed newStateProcessed) {
                assertTrue(clusterState.wasReadFromDiff());
                assertThat(clusterState.blocks().global().size(), equalTo(0));
            }
        });
        mockListenerC.add(new NewClusterStateExpectation() {
            @Override
            public void check(ClusterState clusterState, PublishClusterStateAction.NewClusterStateListener.NewStateProcessed newStateProcessed) {
                // First state
                assertFalse(clusterState.wasReadFromDiff());
            }
        });
        publishStateDiffAndWait(nodeA.action, clusterState, previousClusterState);

        // cluster state update 4 - update settings
        previousClusterState = clusterState;
        MetaData metaData = MetaData.builder(clusterState.metaData()).transientSettings(Settings.settingsBuilder().put("foo", "bar").build()).build();
        clusterState = ClusterState.builder(clusterState).metaData(metaData).incrementVersion().build();
        NewClusterStateExpectation expectation = new NewClusterStateExpectation() {
            @Override
            public void check(ClusterState clusterState, PublishClusterStateAction.NewClusterStateListener.NewStateProcessed newStateProcessed) {
                assertTrue(clusterState.wasReadFromDiff());
                assertThat(clusterState.blocks().global().size(), equalTo(0));
            }
        };
        mockListenerB.add(expectation);
        mockListenerC.add(expectation);
        publishStateDiffAndWait(nodeA.action, clusterState, previousClusterState);

        // cluster state update - skipping one version change - should request full cluster state
        previousClusterState = ClusterState.builder(clusterState).incrementVersion().build();
        clusterState = ClusterState.builder(clusterState).incrementVersion().build();
        expectation = new NewClusterStateExpectation() {
            @Override
            public void check(ClusterState clusterState, PublishClusterStateAction.NewClusterStateListener.NewStateProcessed newStateProcessed) {
                assertFalse(clusterState.wasReadFromDiff());
            }
        };
        mockListenerB.add(expectation);
        mockListenerC.add(expectation);
        publishStateDiffAndWait(nodeA.action, clusterState, previousClusterState);

        // cluster state update - skipping one version change - should request full cluster state
        previousClusterState = ClusterState.builder(clusterState).incrementVersion().build();
        clusterState = ClusterState.builder(clusterState).incrementVersion().build();
        expectation = new NewClusterStateExpectation() {
            @Override
            public void check(ClusterState clusterState, PublishClusterStateAction.NewClusterStateListener.NewStateProcessed newStateProcessed) {
                assertFalse(clusterState.wasReadFromDiff());
            }
        };
        mockListenerB.add(expectation);
        mockListenerC.add(expectation);
        publishStateDiffAndWait(nodeA.action, clusterState, previousClusterState);

        // node B becomes the master and sends a version of the cluster state that goes back
        discoveryNodes = DiscoveryNodes.builder(discoveryNodes)
                .put(nodeA.discoveryNode)
                .put(nodeB.discoveryNode)
                .put(nodeC.discoveryNode)
                .build();
        previousClusterState = ClusterState.builder(new ClusterName("test")).nodes(discoveryNodes).build();
        clusterState = ClusterState.builder(clusterState).nodes(discoveryNodes).incrementVersion().build();
        expectation = new NewClusterStateExpectation() {
            @Override
            public void check(ClusterState clusterState, PublishClusterStateAction.NewClusterStateListener.NewStateProcessed newStateProcessed) {
                assertFalse(clusterState.wasReadFromDiff());
            }
        };
        mockListenerA.add(expectation);
        mockListenerC.add(expectation);
        publishStateDiffAndWait(nodeB.action, clusterState, previousClusterState);
    }

    @Test
    @TestLogging("cluster:DEBUG,discovery.zen.publish:DEBUG")
    public void testUnexpectedDiffPublishing() throws Exception {

        MockNode nodeA = createMockNode("nodeA", Settings.EMPTY, Version.CURRENT, new PublishClusterStateAction.NewClusterStateListener() {
            @Override
            public void onNewClusterState(ClusterState clusterState, NewStateProcessed newStateProcessed) {
                fail("Shouldn't send cluster state to myself");
            }
        });

        MockNewClusterStateListener mockListenerB = new MockNewClusterStateListener();
        MockNode nodeB = createMockNode("nodeB", Settings.EMPTY, Version.CURRENT, mockListenerB);

        // Initial cluster state with both states - the second node still shouldn't get diff even though it's present in the previous cluster state
        DiscoveryNodes discoveryNodes = DiscoveryNodes.builder().put(nodeA.discoveryNode).put(nodeB.discoveryNode).localNodeId(nodeA.discoveryNode.id()).build();
        ClusterState previousClusterState = ClusterState.builder(new ClusterName("test")).nodes(discoveryNodes).build();
        ClusterState clusterState = ClusterState.builder(previousClusterState).incrementVersion().build();
        mockListenerB.add(new NewClusterStateExpectation() {
            @Override
            public void check(ClusterState clusterState, PublishClusterStateAction.NewClusterStateListener.NewStateProcessed newStateProcessed) {
                assertFalse(clusterState.wasReadFromDiff());
            }
        });
        publishStateDiffAndWait(nodeA.action, clusterState, previousClusterState);

        // cluster state update - add block
        previousClusterState = clusterState;
        clusterState = ClusterState.builder(clusterState).blocks(ClusterBlocks.builder().addGlobalBlock(MetaData.CLUSTER_READ_ONLY_BLOCK)).incrementVersion().build();
        mockListenerB.add(new NewClusterStateExpectation() {
            @Override
            public void check(ClusterState clusterState, PublishClusterStateAction.NewClusterStateListener.NewStateProcessed newStateProcessed) {
                assertTrue(clusterState.wasReadFromDiff());
            }
        });
        publishStateDiffAndWait(nodeA.action, clusterState, previousClusterState);
    }

    @Test
    @TestLogging("cluster:DEBUG,discovery.zen.publish:DEBUG")
    public void testDisablingDiffPublishing() throws Exception {
        Settings noDiffPublishingSettings = Settings.builder().put(DiscoverySettings.PUBLISH_DIFF_ENABLE, false).build();

        MockNode nodeA = createMockNode("nodeA", noDiffPublishingSettings, Version.CURRENT, new PublishClusterStateAction.NewClusterStateListener() {
            @Override
            public void onNewClusterState(ClusterState clusterState, NewStateProcessed newStateProcessed) {
                fail("Shouldn't send cluster state to myself");
            }
        });

        MockNode nodeB = createMockNode("nodeB", noDiffPublishingSettings, Version.CURRENT, new PublishClusterStateAction.NewClusterStateListener() {
            @Override
            public void onNewClusterState(ClusterState clusterState, NewStateProcessed newStateProcessed) {
                logger.debug("Got cluster state update, version [{}], guid [{}], from diff [{}]", clusterState.version(), clusterState.uuid(), clusterState.wasReadFromDiff());
                assertFalse(clusterState.wasReadFromDiff());
                newStateProcessed.onNewClusterStateProcessed();
            }
        });

        // Initial cluster state
        DiscoveryNodes discoveryNodes = DiscoveryNodes.builder().put(nodeA.discoveryNode).localNodeId(nodeA.discoveryNode.id()).build();
        ClusterState clusterState = ClusterState.builder(new ClusterName("test")).nodes(discoveryNodes).build();

        // cluster state update - add nodeB
        discoveryNodes = DiscoveryNodes.builder(discoveryNodes).put(nodeB.discoveryNode).build();
        ClusterState previousClusterState = clusterState;
        clusterState = ClusterState.builder(clusterState).nodes(discoveryNodes).incrementVersion().build();
        publishStateDiffAndWait(nodeA.action, clusterState, previousClusterState);

        // cluster state update - add block
        previousClusterState = clusterState;
        clusterState = ClusterState.builder(clusterState).blocks(ClusterBlocks.builder().addGlobalBlock(MetaData.CLUSTER_READ_ONLY_BLOCK)).incrementVersion().build();
        publishStateDiffAndWait(nodeA.action, clusterState, previousClusterState);
    }


    @Test
    @TestLogging("cluster:DEBUG,discovery.zen.publish:DEBUG")
    public void testSimultaneousClusterStatePublishing() throws Exception {
        int numberOfNodes = randomIntBetween(2, 10);
        int numberOfIterations = randomIntBetween(50, 200);
        Settings settings = Settings.builder().put(DiscoverySettings.PUBLISH_TIMEOUT, "100ms").put(DiscoverySettings.PUBLISH_DIFF_ENABLE, true).build();
        MockNode[] nodes = new MockNode[numberOfNodes];
        DiscoveryNodes.Builder discoveryNodesBuilder = DiscoveryNodes.builder();
        for (int i = 0; i < nodes.length; i++) {
            final String name = "node" + i;
            nodes[i] = createMockNode(name, settings, Version.CURRENT, new PublishClusterStateAction.NewClusterStateListener() {
                @Override
                public synchronized void onNewClusterState(ClusterState clusterState, NewStateProcessed newStateProcessed) {
                    assertProperMetaDataForVersion(clusterState.metaData(), clusterState.version());
                    if (randomInt(10) < 2) {
                        // Cause timeouts from time to time
                        try {
                            Thread.sleep(randomInt(110));
                        } catch (InterruptedException ex) {
                            Thread.currentThread().interrupt();
                        }
                    }
                    newStateProcessed.onNewClusterStateProcessed();
                }
            });
            discoveryNodesBuilder.put(nodes[i].discoveryNode);
        }

        AssertingAckListener[] listeners = new AssertingAckListener[numberOfIterations];
        DiscoveryNodes discoveryNodes = discoveryNodesBuilder.build();
        MetaData metaData = MetaData.EMPTY_META_DATA;
        ClusterState clusterState = ClusterState.builder(new ClusterName("test")).metaData(metaData).build();
        ClusterState previousState;
        for (int i = 0; i < numberOfIterations; i++) {
            previousState = clusterState;
            metaData = buildMetaDataForVersion(metaData, i + 1);
            clusterState = ClusterState.builder(clusterState).incrementVersion().metaData(metaData).nodes(discoveryNodes).build();
            listeners[i] = publishStateDiff(nodes[0].action, clusterState, previousState);
        }

        for (int i = 0; i < numberOfIterations; i++) {
            listeners[i].await(1, TimeUnit.SECONDS);
        }
    }

    @Test
    @TestLogging("cluster:DEBUG,discovery.zen.publish:DEBUG")
    public void testSerializationFailureDuringDiffPublishing() throws Exception {

        MockNode nodeA = createMockNode("nodeA", Settings.EMPTY, Version.CURRENT, new PublishClusterStateAction.NewClusterStateListener() {
            @Override
            public void onNewClusterState(ClusterState clusterState, NewStateProcessed newStateProcessed) {
                fail("Shouldn't send cluster state to myself");
            }
        });

        MockNewClusterStateListener mockListenerB = new MockNewClusterStateListener();
        MockNode nodeB = createMockNode("nodeB", Settings.EMPTY, Version.CURRENT, mockListenerB);

        // Initial cluster state with both states - the second node still shouldn't get diff even though it's present in the previous cluster state
        DiscoveryNodes discoveryNodes = DiscoveryNodes.builder().put(nodeA.discoveryNode).put(nodeB.discoveryNode).localNodeId(nodeA.discoveryNode.id()).build();
        ClusterState previousClusterState = ClusterState.builder(new ClusterName("test")).nodes(discoveryNodes).build();
        ClusterState clusterState = ClusterState.builder(previousClusterState).incrementVersion().build();
        mockListenerB.add(new NewClusterStateExpectation() {
            @Override
            public void check(ClusterState clusterState, PublishClusterStateAction.NewClusterStateListener.NewStateProcessed newStateProcessed) {
                assertFalse(clusterState.wasReadFromDiff());
            }
        });
        publishStateDiffAndWait(nodeA.action, clusterState, previousClusterState);

        // cluster state update - add block
        previousClusterState = clusterState;
        clusterState = ClusterState.builder(clusterState).blocks(ClusterBlocks.builder().addGlobalBlock(MetaData.CLUSTER_READ_ONLY_BLOCK)).incrementVersion().build();
        mockListenerB.add(new NewClusterStateExpectation() {
            @Override
            public void check(ClusterState clusterState, PublishClusterStateAction.NewClusterStateListener.NewStateProcessed newStateProcessed) {
                assertTrue(clusterState.wasReadFromDiff());
            }
        });

        ClusterState unserializableClusterState = new ClusterState(clusterState.version(), clusterState.uuid(), clusterState) {
            @Override
            public Diff<ClusterState> diff(ClusterState previousState) {
                return new Diff<ClusterState>() {
                    @Override
                    public ClusterState apply(ClusterState part) {
                        fail("this diff shouldn't be applied");
                        return part;
                    }

                    @Override
                    public void writeTo(StreamOutput out) throws IOException {
                        throw new IOException("Simulated failure of diff serialization");
                    }
                };
            }
        };
        List<Tuple<DiscoveryNode, Throwable>> errors = publishStateDiff(nodeA.action, unserializableClusterState, previousClusterState).awaitErrors(1, TimeUnit.SECONDS);
        assertThat(errors.size(), equalTo(1));
        assertThat(errors.get(0).v2().getMessage(), containsString("Simulated failure of diff serialization"));
    }

    private MetaData buildMetaDataForVersion(MetaData metaData, long version) {
        ImmutableOpenMap.Builder<String, IndexMetaData> indices = ImmutableOpenMap.builder(metaData.indices());
        indices.put("test" + version, IndexMetaData.builder("test" + version).settings(Settings.builder().put(IndexMetaData.SETTING_VERSION_CREATED, Version.CURRENT))
                .numberOfShards((int) version).numberOfReplicas(0).build());
        return MetaData.builder(metaData)
                .transientSettings(Settings.builder().put("test", version).build())
                .indices(indices.build())
                .build();
    }

    private void assertProperMetaDataForVersion(MetaData metaData, long version) {
        for (long i = 1; i <= version; i++) {
            assertThat(metaData.index("test" + i), notNullValue());
            assertThat(metaData.index("test" + i).numberOfShards(), equalTo((int) i));
        }
        assertThat(metaData.index("test" + (version + 1)), nullValue());
        assertThat(metaData.transientSettings().get("test"), equalTo(Long.toString(version)));
    }

    public void publishStateDiffAndWait(PublishClusterStateAction action, ClusterState state, ClusterState previousState) throws InterruptedException {
        publishStateDiff(action, state, previousState).await(1, TimeUnit.SECONDS);
    }

    public AssertingAckListener publishStateDiff(PublishClusterStateAction action, ClusterState state, ClusterState previousState) throws InterruptedException {
        AssertingAckListener assertingAckListener = new AssertingAckListener(state.nodes().getSize() - 1);
        ClusterChangedEvent changedEvent = new ClusterChangedEvent("test update", state, previousState);
        action.publish(changedEvent, assertingAckListener);
        return assertingAckListener;
    }

    public static class AssertingAckListener implements Discovery.AckListener {
        private final List<Tuple<DiscoveryNode, Throwable>> errors = new CopyOnWriteArrayList<>();
        private final AtomicBoolean timeoutOccured = new AtomicBoolean();
        private final CountDownLatch countDown;

        public AssertingAckListener(int nodeCount) {
            countDown = new CountDownLatch(nodeCount);
        }

        @Override
        public void onNodeAck(DiscoveryNode node, @Nullable Throwable t) {
            if (t != null) {
                errors.add(new Tuple<>(node, t));
            }
            countDown.countDown();
        }

        @Override
        public void onTimeout() {
            timeoutOccured.set(true);
            // Fast forward the counter - no reason to wait here
            long currentCount = countDown.getCount();
            for (long i = 0; i < currentCount; i++) {
                countDown.countDown();
            }
        }

        public void await(long timeout, TimeUnit unit) throws InterruptedException {
            assertThat(awaitErrors(timeout, unit), emptyIterable());
        }

        public List<Tuple<DiscoveryNode, Throwable>> awaitErrors(long timeout, TimeUnit unit) throws InterruptedException {
            countDown.await(timeout, unit);
            assertFalse(timeoutOccured.get());
            return errors;
        }

    }

    public interface NewClusterStateExpectation {
        void check(ClusterState clusterState, PublishClusterStateAction.NewClusterStateListener.NewStateProcessed newStateProcessed);
    }

    public static class MockNewClusterStateListener implements PublishClusterStateAction.NewClusterStateListener {
        CopyOnWriteArrayList<NewClusterStateExpectation> expectations = new CopyOnWriteArrayList();

        @Override
        public void onNewClusterState(ClusterState clusterState, NewStateProcessed newStateProcessed) {
            final NewClusterStateExpectation expectation;
            try {
                expectation = expectations.remove(0);
            } catch (ArrayIndexOutOfBoundsException ex) {
                fail("Unexpected cluster state update " + clusterState.prettyPrint());
                return;
            }
            expectation.check(clusterState, newStateProcessed);
            newStateProcessed.onNewClusterStateProcessed();
        }

        public void add(NewClusterStateExpectation expectation) {
            expectations.add(expectation);
        }
    }

    public static class DelegatingClusterState extends ClusterState {

        public DelegatingClusterState(ClusterState clusterState) {
            super(clusterState.version(), clusterState.uuid(), clusterState);
        }


    }

}


File: core/src/test/java/org/elasticsearch/common/io/streams/BytesStreamsTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.common.io.streams;

import org.apache.lucene.util.Constants;
import org.elasticsearch.common.io.stream.BytesStreamOutput;
import org.elasticsearch.common.io.stream.StreamInput;
import org.elasticsearch.common.lucene.BytesRefs;
import org.elasticsearch.common.util.BigArrays;
import org.elasticsearch.test.ElasticsearchTestCase;
import org.junit.Ignore;
import org.junit.Test;

import static org.hamcrest.Matchers.closeTo;
import static org.hamcrest.Matchers.equalTo;

/**
 * Tests for {@link BytesStreamOutput} paging behaviour.
 */
public class BytesStreamsTests extends ElasticsearchTestCase {

    @Test
    public void testEmpty() throws Exception {
        BytesStreamOutput out = new BytesStreamOutput();

        // test empty stream to array
        assertEquals(0, out.size());
        assertEquals(0, out.bytes().toBytes().length);

        out.close();
    }

    @Test
    public void testSingleByte() throws Exception {
        BytesStreamOutput out = new BytesStreamOutput();
        assertEquals(0, out.size());

        int expectedSize = 1;
        byte[] expectedData = randomizedByteArrayWithSize(expectedSize);

        // write single byte
        out.writeByte(expectedData[0]);
        assertEquals(expectedSize, out.size());
        assertArrayEquals(expectedData, out.bytes().toBytes());

        out.close();
    }

    @Test
    public void testSingleShortPage() throws Exception {
        BytesStreamOutput out = new BytesStreamOutput();

        int expectedSize = 10;
        byte[] expectedData = randomizedByteArrayWithSize(expectedSize);

        // write byte-by-byte
        for (int i = 0; i < expectedSize; i++) {
            out.writeByte(expectedData[i]);
        }

        assertEquals(expectedSize, out.size());
        assertArrayEquals(expectedData, out.bytes().toBytes());

        out.close();
    }

    @Test
    public void testIllegalBulkWrite() throws Exception {
        BytesStreamOutput out = new BytesStreamOutput();

        // bulk-write with wrong args
        try {
            out.writeBytes(new byte[]{}, 0, 1);
            fail("expected IllegalArgumentException: length > (size-offset)");
        }
        catch (IllegalArgumentException iax1) {
            // expected
        }

        out.close();
    }

    @Test
    public void testSingleShortPageBulkWrite() throws Exception {
        BytesStreamOutput out = new BytesStreamOutput();

        // first bulk-write empty array: should not change anything
        int expectedSize = 0;
        byte[] expectedData = randomizedByteArrayWithSize(expectedSize);
        out.writeBytes(expectedData);
        assertEquals(expectedSize, out.size());
        assertArrayEquals(expectedData, out.bytes().toBytes());

        // bulk-write again with actual bytes
        expectedSize = 10;
        expectedData = randomizedByteArrayWithSize(expectedSize);
        out.writeBytes(expectedData);
        assertEquals(expectedSize, out.size());
        assertArrayEquals(expectedData, out.bytes().toBytes());

        out.close();
    }

    @Test
    public void testSingleFullPageBulkWrite() throws Exception {
        BytesStreamOutput out = new BytesStreamOutput();

        int expectedSize = BigArrays.BYTE_PAGE_SIZE;
        byte[] expectedData = randomizedByteArrayWithSize(expectedSize);

        // write in bulk
        out.writeBytes(expectedData);

        assertEquals(expectedSize, out.size());
        assertArrayEquals(expectedData, out.bytes().toBytes());

        out.close();
    }

    @Test
    public void testSingleFullPageBulkWriteWithOffset() throws Exception {
        BytesStreamOutput out = new BytesStreamOutput();

        int initialOffset = 10;
        int additionalLength = BigArrays.BYTE_PAGE_SIZE;
        byte[] expectedData = randomizedByteArrayWithSize(initialOffset + additionalLength);

        // first create initial offset
        out.writeBytes(expectedData, 0, initialOffset);
        assertEquals(initialOffset, out.size());

        // now write the rest - more than fits into the remaining first page
        out.writeBytes(expectedData, initialOffset, additionalLength);
        assertEquals(expectedData.length, out.size());
        assertArrayEquals(expectedData, out.bytes().toBytes());

        out.close();
    }

    @Test
    public void testSingleFullPageBulkWriteWithOffsetCrossover() throws Exception {
        BytesStreamOutput out = new BytesStreamOutput();

        int initialOffset = 10;
        int additionalLength = BigArrays.BYTE_PAGE_SIZE * 2;
        byte[] expectedData = randomizedByteArrayWithSize(initialOffset + additionalLength);
        out.writeBytes(expectedData, 0, initialOffset);
        assertEquals(initialOffset, out.size());

        // now write the rest - more than fits into the remaining page + a full page after
        // that,
        // ie. we cross over into a third
        out.writeBytes(expectedData, initialOffset, additionalLength);
        assertEquals(expectedData.length, out.size());
        assertArrayEquals(expectedData, out.bytes().toBytes());

        out.close();
    }

    @Test
    public void testSingleFullPage() throws Exception {
        BytesStreamOutput out = new BytesStreamOutput();

        int expectedSize = BigArrays.BYTE_PAGE_SIZE;
        byte[] expectedData = randomizedByteArrayWithSize(expectedSize);

        // write byte-by-byte
        for (int i = 0; i < expectedSize; i++) {
            out.writeByte(expectedData[i]);
        }

        assertEquals(expectedSize, out.size());
        assertArrayEquals(expectedData, out.bytes().toBytes());

        out.close();
    }

    @Test
    public void testOneFullOneShortPage() throws Exception {
        BytesStreamOutput out = new BytesStreamOutput();

        int expectedSize = BigArrays.BYTE_PAGE_SIZE + 10;
        byte[] expectedData = randomizedByteArrayWithSize(expectedSize);

        // write byte-by-byte
        for (int i = 0; i < expectedSize; i++) {
            out.writeByte(expectedData[i]);
        }

        assertEquals(expectedSize, out.size());
        assertArrayEquals(expectedData, out.bytes().toBytes());

        out.close();
    }

    @Test
    public void testTwoFullOneShortPage() throws Exception {
        BytesStreamOutput out = new BytesStreamOutput();

        int expectedSize = (BigArrays.BYTE_PAGE_SIZE * 2) + 1;
        byte[] expectedData = randomizedByteArrayWithSize(expectedSize);

        // write byte-by-byte
        for (int i = 0; i < expectedSize; i++) {
            out.writeByte(expectedData[i]);
        }

        assertEquals(expectedSize, out.size());
        assertArrayEquals(expectedData, out.bytes().toBytes());

        out.close();
    }

    @Test
    public void testSeek() throws Exception {
        BytesStreamOutput out = new BytesStreamOutput();

        int position = 0;
        assertEquals(position, out.position());

        out.seek(position += 10);
        out.seek(position += BigArrays.BYTE_PAGE_SIZE);
        out.seek(position += BigArrays.BYTE_PAGE_SIZE + 10);
        out.seek(position += BigArrays.BYTE_PAGE_SIZE * 2);
        assertEquals(position, out.position());
        assertEquals(position, out.bytes().toBytes().length);

        out.close();
    }

    @Test
    public void testSkip() throws Exception {
        BytesStreamOutput out = new BytesStreamOutput();

        int position = 0;
        assertEquals(position, out.position());

        int forward = 100;
        out.skip(forward);
        assertEquals(position + forward, out.position());

        out.close();
    }

    @Test
    public void testSimpleStreams() throws Exception {
        assumeTrue("requires a 64-bit JRE ... ?!", Constants.JRE_IS_64BIT);
        BytesStreamOutput out = new BytesStreamOutput();
        out.writeBoolean(false);
        out.writeByte((byte) 1);
        out.writeShort((short) -1);
        out.writeInt(-1);
        out.writeVInt(2);
        out.writeLong(-3);
        out.writeVLong(4);
        out.writeFloat(1.1f);
        out.writeDouble(2.2);
        int[] intArray = {1, 2, 3};
        out.writeGenericValue(intArray);
        long[] longArray = {1, 2, 3};
        out.writeGenericValue(longArray);
        float[] floatArray = {1.1f, 2.2f, 3.3f};
        out.writeGenericValue(floatArray);
        double[] doubleArray = {1.1, 2.2, 3.3};
        out.writeGenericValue(doubleArray);
        out.writeString("hello");
        out.writeString("goodbye");
        out.writeGenericValue(BytesRefs.toBytesRef("bytesref"));
        StreamInput in = StreamInput.wrap(out.bytes().toBytes());
        assertThat(in.readBoolean(), equalTo(false));
        assertThat(in.readByte(), equalTo((byte)1));
        assertThat(in.readShort(), equalTo((short)-1));
        assertThat(in.readInt(), equalTo(-1));
        assertThat(in.readVInt(), equalTo(2));
        assertThat(in.readLong(), equalTo((long)-3));
        assertThat(in.readVLong(), equalTo((long)4));
        assertThat((double)in.readFloat(), closeTo(1.1, 0.0001));
        assertThat(in.readDouble(), closeTo(2.2, 0.0001));
        assertThat(in.readGenericValue(), equalTo((Object) intArray));
        assertThat(in.readGenericValue(), equalTo((Object)longArray));
        assertThat(in.readGenericValue(), equalTo((Object)floatArray));
        assertThat(in.readGenericValue(), equalTo((Object)doubleArray));
        assertThat(in.readString(), equalTo("hello"));
        assertThat(in.readString(), equalTo("goodbye"));
        assertThat(in.readGenericValue(), equalTo((Object)BytesRefs.toBytesRef("bytesref")));
        in.close();
        out.close();
    }

    // we ignore this test for now since all existing callers of BytesStreamOutput happily
    // call bytes() after close().
    @Ignore
    @Test
    public void testAccessAfterClose() throws Exception {
        BytesStreamOutput out = new BytesStreamOutput();

        // immediately close
        out.close();

        assertEquals(-1, out.size());
        assertEquals(-1, out.position());

        // writing a single byte must fail
        try {
            out.writeByte((byte)0);
            fail("expected IllegalStateException: stream closed");
        }
        catch (IllegalStateException iex1) {
            // expected
        }

        // writing in bulk must fail
        try {
            out.writeBytes(new byte[0], 0, 0);
            fail("expected IllegalStateException: stream closed");
        }
        catch (IllegalStateException iex1) {
            // expected
        }

        // toByteArray() must fail
        try {
            out.bytes().toBytes();
            fail("expected IllegalStateException: stream closed");
        }
        catch (IllegalStateException iex1) {
            // expected
        }

    }

    // create & fill byte[] with randomized data
    protected byte[] randomizedByteArrayWithSize(int size) {
        byte[] data = new byte[size];
        getRandom().nextBytes(data);
        return data;
    }
}


File: core/src/test/java/org/elasticsearch/discovery/ZenFaultDetectionTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.discovery;

import com.google.common.collect.ImmutableMap;
import org.elasticsearch.Version;
import org.elasticsearch.cluster.ClusterName;
import org.elasticsearch.cluster.ClusterState;
import org.elasticsearch.cluster.node.DiscoveryNode;
import org.elasticsearch.cluster.node.DiscoveryNodes;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.discovery.zen.fd.FaultDetection;
import org.elasticsearch.discovery.zen.fd.MasterFaultDetection;
import org.elasticsearch.discovery.zen.fd.NodesFaultDetection;
import org.elasticsearch.test.ElasticsearchTestCase;
import org.elasticsearch.test.cluster.NoopClusterService;
import org.elasticsearch.test.transport.MockTransportService;
import org.elasticsearch.threadpool.ThreadPool;
import org.elasticsearch.transport.TransportConnectionListener;
import org.elasticsearch.transport.local.LocalTransport;
import org.hamcrest.Matcher;
import org.hamcrest.Matchers;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import static org.hamcrest.Matchers.equalTo;

public class ZenFaultDetectionTests extends ElasticsearchTestCase {

    protected ThreadPool threadPool;

    protected static final Version version0 = Version.fromId(/*0*/99);
    protected DiscoveryNode nodeA;
    protected MockTransportService serviceA;

    protected static final Version version1 = Version.fromId(199);
    protected DiscoveryNode nodeB;
    protected MockTransportService serviceB;

    @Override
    @Before
    public void setUp() throws Exception {
        super.setUp();
        threadPool = new ThreadPool(getClass().getName());
        serviceA = build(Settings.builder().put("name", "TS_A").build(), version0);
        nodeA = new DiscoveryNode("TS_A", "TS_A", serviceA.boundAddress().publishAddress(), ImmutableMap.<String, String>of(), version0);
        serviceB = build(Settings.builder().put("name", "TS_B").build(), version1);
        nodeB = new DiscoveryNode("TS_B", "TS_B", serviceB.boundAddress().publishAddress(), ImmutableMap.<String, String>of(), version1);

        // wait till all nodes are properly connected and the event has been sent, so tests in this class
        // will not get this callback called on the connections done in this setup
        final CountDownLatch latch = new CountDownLatch(4);
        TransportConnectionListener waitForConnection = new TransportConnectionListener() {
            @Override
            public void onNodeConnected(DiscoveryNode node) {
                latch.countDown();
            }

            @Override
            public void onNodeDisconnected(DiscoveryNode node) {
                fail("disconnect should not be called " + node);
            }
        };
        serviceA.addConnectionListener(waitForConnection);
        serviceB.addConnectionListener(waitForConnection);

        serviceA.connectToNode(nodeB);
        serviceA.connectToNode(nodeA);
        serviceB.connectToNode(nodeA);
        serviceB.connectToNode(nodeB);

        assertThat("failed to wait for all nodes to connect", latch.await(5, TimeUnit.SECONDS), equalTo(true));
        serviceA.removeConnectionListener(waitForConnection);
        serviceB.removeConnectionListener(waitForConnection);
    }

    @Override
    @After
    public void tearDown() throws Exception {
        super.tearDown();
        serviceA.close();
        serviceB.close();
        terminate(threadPool);
    }

    protected MockTransportService build(Settings settings, Version version) {
        MockTransportService transportService = new MockTransportService(Settings.EMPTY, new LocalTransport(settings, threadPool, version), threadPool);
        transportService.start();
        return transportService;
    }

    private DiscoveryNodes buildNodesForA(boolean master) {
        DiscoveryNodes.Builder builder = DiscoveryNodes.builder();
        builder.put(nodeA);
        builder.put(nodeB);
        builder.localNodeId(nodeA.id());
        builder.masterNodeId(master ? nodeA.id() : nodeB.id());
        return builder.build();
    }

    private DiscoveryNodes buildNodesForB(boolean master) {
        DiscoveryNodes.Builder builder = DiscoveryNodes.builder();
        builder.put(nodeA);
        builder.put(nodeB);
        builder.localNodeId(nodeB.id());
        builder.masterNodeId(master ? nodeB.id() : nodeA.id());
        return builder.build();
    }

    @Test
    public void testNodesFaultDetectionConnectOnDisconnect() throws InterruptedException {
        Settings.Builder settings = Settings.builder();
        boolean shouldRetry = randomBoolean();
        // make sure we don't ping again after the initial ping
        settings.put(FaultDetection.SETTING_CONNECT_ON_NETWORK_DISCONNECT, shouldRetry)
                .put(FaultDetection.SETTING_PING_INTERVAL, "5m");
        ClusterState clusterState = ClusterState.builder(new ClusterName("test")).nodes(buildNodesForA(true)).build();
        NodesFaultDetection nodesFDA = new NodesFaultDetection(settings.build(), threadPool, serviceA, clusterState.getClusterName());
        nodesFDA.setLocalNode(nodeA);
        NodesFaultDetection nodesFDB = new NodesFaultDetection(settings.build(), threadPool, serviceB, clusterState.getClusterName());
        nodesFDB.setLocalNode(nodeB);
        final CountDownLatch pingSent = new CountDownLatch(1);
        nodesFDB.addListener(new NodesFaultDetection.Listener() {
            @Override
            public void onPingReceived(NodesFaultDetection.PingRequest pingRequest) {
                pingSent.countDown();
            }
        });
        nodesFDA.updateNodesAndPing(clusterState);

        // wait for the first ping to go out, so we will really respond to a disconnect event rather then
        // the ping failing
        pingSent.await(30, TimeUnit.SECONDS);

        final String[] failureReason = new String[1];
        final DiscoveryNode[] failureNode = new DiscoveryNode[1];
        final CountDownLatch notified = new CountDownLatch(1);
        nodesFDA.addListener(new NodesFaultDetection.Listener() {
            @Override
            public void onNodeFailure(DiscoveryNode node, String reason) {
                failureNode[0] = node;
                failureReason[0] = reason;
                notified.countDown();
            }
        });
        // will raise a disconnect on A
        serviceB.stop();
        notified.await(30, TimeUnit.SECONDS);

        assertEquals(nodeB, failureNode[0]);
        Matcher<String> matcher = Matchers.containsString("verified");
        if (!shouldRetry) {
            matcher = Matchers.not(matcher);
        }

        assertThat(failureReason[0], matcher);
    }

    @Test
    public void testMasterFaultDetectionConnectOnDisconnect() throws InterruptedException {

        Settings.Builder settings = Settings.builder();
        boolean shouldRetry = randomBoolean();
        // make sure we don't ping
        settings.put(FaultDetection.SETTING_CONNECT_ON_NETWORK_DISCONNECT, shouldRetry)
                .put(FaultDetection.SETTING_PING_INTERVAL, "5m");
        ClusterName clusterName = new ClusterName(randomAsciiOfLengthBetween(3, 20));
        final ClusterState state = ClusterState.builder(clusterName).nodes(buildNodesForA(false)).build();
        MasterFaultDetection masterFD = new MasterFaultDetection(settings.build(), threadPool, serviceA, clusterName,
                new NoopClusterService(state));
        masterFD.start(nodeB, "test");

        final String[] failureReason = new String[1];
        final DiscoveryNode[] failureNode = new DiscoveryNode[1];
        final CountDownLatch notified = new CountDownLatch(1);
        masterFD.addListener(new MasterFaultDetection.Listener() {

            @Override
            public void onMasterFailure(DiscoveryNode masterNode, String reason) {
                failureNode[0] = masterNode;
                failureReason[0] = reason;
                notified.countDown();
            }
        });
        // will raise a disconnect on A
        serviceB.stop();
        notified.await(30, TimeUnit.SECONDS);

        assertEquals(nodeB, failureNode[0]);
        Matcher<String> matcher = Matchers.containsString("verified");
        if (!shouldRetry) {
            matcher = Matchers.not(matcher);
        }

        assertThat(failureReason[0], matcher);
    }
}

File: core/src/test/java/org/elasticsearch/discovery/zen/ping/multicast/MulticastZenPingTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.discovery.zen.ping.multicast;

import org.elasticsearch.Version;
import org.elasticsearch.cluster.ClusterName;
import org.elasticsearch.cluster.node.DiscoveryNode;
import org.elasticsearch.cluster.node.DiscoveryNodes;
import org.elasticsearch.common.logging.Loggers;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.unit.TimeValue;
import org.elasticsearch.common.xcontent.XContentBuilder;
import org.elasticsearch.common.xcontent.XContentFactory;
import org.elasticsearch.discovery.zen.ping.PingContextProvider;
import org.elasticsearch.discovery.zen.ping.ZenPing;
import org.elasticsearch.node.service.NodeService;
import org.elasticsearch.test.ElasticsearchTestCase;
import org.elasticsearch.threadpool.ThreadPool;
import org.elasticsearch.transport.TransportService;
import org.elasticsearch.transport.local.LocalTransport;
import org.junit.Test;

import java.net.DatagramPacket;
import java.net.InetAddress;
import java.net.MulticastSocket;

import static org.hamcrest.Matchers.equalTo;

/**
 *
 */
public class MulticastZenPingTests extends ElasticsearchTestCase {

    private Settings buildRandomMulticast(Settings settings) {
        Settings.Builder builder = Settings.builder().put(settings);
        builder.put("discovery.zen.ping.multicast.group", "224.2.3." + randomIntBetween(0, 255));
        builder.put("discovery.zen.ping.multicast.port", randomIntBetween(55000, 56000));
        if (randomBoolean()) {
            builder.put("discovery.zen.ping.multicast.shared", randomBoolean());
        }
        return builder.build();
    }

    @Test
    public void testSimplePings() throws InterruptedException {
        Settings settings = Settings.EMPTY;
        settings = buildRandomMulticast(settings);

        ThreadPool threadPool = new ThreadPool("testSimplePings");
        final ClusterName clusterName = new ClusterName("test");
        final TransportService transportServiceA = new TransportService(new LocalTransport(settings, threadPool, Version.CURRENT), threadPool).start();
        final DiscoveryNode nodeA = new DiscoveryNode("A", transportServiceA.boundAddress().publishAddress(), Version.CURRENT);

        final TransportService transportServiceB = new TransportService(new LocalTransport(settings, threadPool, Version.CURRENT), threadPool).start();
        final DiscoveryNode nodeB = new DiscoveryNode("B", transportServiceB.boundAddress().publishAddress(), Version.CURRENT);

        MulticastZenPing zenPingA = new MulticastZenPing(threadPool, transportServiceA, clusterName, Version.CURRENT);
        zenPingA.setPingContextProvider(new PingContextProvider() {
            @Override
            public DiscoveryNodes nodes() {
                return DiscoveryNodes.builder().put(nodeA).localNodeId("A").build();
            }

            @Override
            public NodeService nodeService() {
                return null;
            }

            @Override
            public boolean nodeHasJoinedClusterOnce() {
                return false;
            }
        });
        zenPingA.start();

        MulticastZenPing zenPingB = new MulticastZenPing(threadPool, transportServiceB, clusterName, Version.CURRENT);
        zenPingB.setPingContextProvider(new PingContextProvider() {
            @Override
            public DiscoveryNodes nodes() {
                return DiscoveryNodes.builder().put(nodeB).localNodeId("B").build();
            }

            @Override
            public NodeService nodeService() {
                return null;
            }

            @Override
            public boolean nodeHasJoinedClusterOnce() {
                return true;
            }
        });
        zenPingB.start();

        try {
            logger.info("ping from A");
            ZenPing.PingResponse[] pingResponses = zenPingA.pingAndWait(TimeValue.timeValueSeconds(1));
            assertThat(pingResponses.length, equalTo(1));
            assertThat(pingResponses[0].node().id(), equalTo("B"));
            assertTrue(pingResponses[0].hasJoinedOnce());

            logger.info("ping from B");
            pingResponses = zenPingB.pingAndWait(TimeValue.timeValueSeconds(1));
            assertThat(pingResponses.length, equalTo(1));
            assertThat(pingResponses[0].node().id(), equalTo("A"));
            assertFalse(pingResponses[0].hasJoinedOnce());

        } finally {
            zenPingA.close();
            zenPingB.close();
            transportServiceA.close();
            transportServiceB.close();
            terminate(threadPool);
        }
    }

    @Test
    public void testExternalPing() throws Exception {
        Settings settings = Settings.EMPTY;
        settings = buildRandomMulticast(settings);

        final ThreadPool threadPool = new ThreadPool("testExternalPing");
        final ClusterName clusterName = new ClusterName("test");
        final TransportService transportServiceA = new TransportService(new LocalTransport(settings, threadPool, Version.CURRENT), threadPool).start();
        final DiscoveryNode nodeA = new DiscoveryNode("A", transportServiceA.boundAddress().publishAddress(), Version.CURRENT);

        MulticastZenPing zenPingA = new MulticastZenPing(threadPool, transportServiceA, clusterName, Version.CURRENT);
        zenPingA.setPingContextProvider(new PingContextProvider() {
            @Override
            public DiscoveryNodes nodes() {
                return DiscoveryNodes.builder().put(nodeA).localNodeId("A").build();
            }

            @Override
            public NodeService nodeService() {
                return null;
            }

            @Override
            public boolean nodeHasJoinedClusterOnce() {
                return false;
            }
        });
        zenPingA.start();

        MulticastSocket multicastSocket = null;
        try {
            Loggers.getLogger(MulticastZenPing.class).setLevel("TRACE");
            multicastSocket = new MulticastSocket(54328);
            multicastSocket.setReceiveBufferSize(2048);
            multicastSocket.setSendBufferSize(2048);
            multicastSocket.setSoTimeout(60000);

            DatagramPacket datagramPacket = new DatagramPacket(new byte[2048], 2048, InetAddress.getByName("224.2.2.4"), 54328);
            XContentBuilder builder = XContentFactory.jsonBuilder().startObject().startObject("request").field("cluster_name", "test").endObject().endObject();
            datagramPacket.setData(builder.bytes().toBytes());
            multicastSocket.send(datagramPacket);
            Thread.sleep(100);
        } finally {
            Loggers.getLogger(MulticastZenPing.class).setLevel("INFO");
            if (multicastSocket != null) multicastSocket.close();
            zenPingA.close();
            terminate(threadPool);
        }
    }
}


File: core/src/test/java/org/elasticsearch/discovery/zen/ping/unicast/UnicastZenPingTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.discovery.zen.ping.unicast;

import org.elasticsearch.Version;
import org.elasticsearch.cluster.ClusterName;
import org.elasticsearch.cluster.node.DiscoveryNode;
import org.elasticsearch.cluster.node.DiscoveryNodes;
import org.elasticsearch.common.network.NetworkService;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.transport.InetSocketTransportAddress;
import org.elasticsearch.common.unit.TimeValue;
import org.elasticsearch.common.util.BigArrays;
import org.elasticsearch.discovery.zen.elect.ElectMasterService;
import org.elasticsearch.discovery.zen.ping.PingContextProvider;
import org.elasticsearch.discovery.zen.ping.ZenPing;
import org.elasticsearch.node.service.NodeService;
import org.elasticsearch.test.ElasticsearchTestCase;
import org.elasticsearch.threadpool.ThreadPool;
import org.elasticsearch.transport.TransportService;
import org.elasticsearch.transport.netty.NettyTransport;
import org.apache.lucene.util.LuceneTestCase.Slow;
import org.junit.Test;

import static org.hamcrest.Matchers.equalTo;

/**
 *
 */
@Slow
public class UnicastZenPingTests extends ElasticsearchTestCase {

    @Test
    public void testSimplePings() throws InterruptedException {
        Settings settings = Settings.EMPTY;
        int startPort = 11000 + randomIntBetween(0, 1000);
        int endPort = startPort + 10;
        settings = Settings.builder().put(settings).put("transport.tcp.port", startPort + "-" + endPort).build();

        ThreadPool threadPool = new ThreadPool(getClass().getName());
        ClusterName clusterName = new ClusterName("test");
        NetworkService networkService = new NetworkService(settings);
        ElectMasterService electMasterService = new ElectMasterService(settings);

        NettyTransport transportA = new NettyTransport(settings, threadPool, networkService, BigArrays.NON_RECYCLING_INSTANCE, Version.CURRENT);
        final TransportService transportServiceA = new TransportService(transportA, threadPool).start();
        final DiscoveryNode nodeA = new DiscoveryNode("UZP_A", transportServiceA.boundAddress().publishAddress(), Version.CURRENT);

        InetSocketTransportAddress addressA = (InetSocketTransportAddress) transportA.boundAddress().publishAddress();

        NettyTransport transportB = new NettyTransport(settings, threadPool, networkService, BigArrays.NON_RECYCLING_INSTANCE, Version.CURRENT);
        final TransportService transportServiceB = new TransportService(transportB, threadPool).start();
        final DiscoveryNode nodeB = new DiscoveryNode("UZP_B", transportServiceA.boundAddress().publishAddress(), Version.CURRENT);

        InetSocketTransportAddress addressB = (InetSocketTransportAddress) transportB.boundAddress().publishAddress();

        Settings hostsSettings = Settings.settingsBuilder().putArray("discovery.zen.ping.unicast.hosts",
                addressA.address().getAddress().getHostAddress() + ":" + addressA.address().getPort(),
                addressB.address().getAddress().getHostAddress() + ":" + addressB.address().getPort())
                .build();

        UnicastZenPing zenPingA = new UnicastZenPing(hostsSettings, threadPool, transportServiceA, clusterName, Version.CURRENT, electMasterService, null);
        zenPingA.setPingContextProvider(new PingContextProvider() {
            @Override
            public DiscoveryNodes nodes() {
                return DiscoveryNodes.builder().put(nodeA).localNodeId("UZP_A").build();
            }

            @Override
            public NodeService nodeService() {
                return null;
            }

            @Override
            public boolean nodeHasJoinedClusterOnce() {
                return false;
            }
        });
        zenPingA.start();

        UnicastZenPing zenPingB = new UnicastZenPing(hostsSettings, threadPool, transportServiceB, clusterName, Version.CURRENT, electMasterService, null);
        zenPingB.setPingContextProvider(new PingContextProvider() {
            @Override
            public DiscoveryNodes nodes() {
                return DiscoveryNodes.builder().put(nodeB).localNodeId("UZP_B").build();
            }

            @Override
            public NodeService nodeService() {
                return null;
            }

            @Override
            public boolean nodeHasJoinedClusterOnce() {
                return true;
            }
        });
        zenPingB.start();

        try {
            logger.info("ping from UZP_A");
            ZenPing.PingResponse[] pingResponses = zenPingA.pingAndWait(TimeValue.timeValueSeconds(10));
            assertThat(pingResponses.length, equalTo(1));
            assertThat(pingResponses[0].node().id(), equalTo("UZP_B"));
            assertTrue(pingResponses[0].hasJoinedOnce());

            // ping again, this time from B,
            logger.info("ping from UZP_B");
            pingResponses = zenPingB.pingAndWait(TimeValue.timeValueSeconds(10));
            assertThat(pingResponses.length, equalTo(1));
            assertThat(pingResponses[0].node().id(), equalTo("UZP_A"));
            assertFalse(pingResponses[0].hasJoinedOnce());

        } finally {
            zenPingA.close();
            zenPingB.close();
            transportServiceA.close();
            transportServiceB.close();
            terminate(threadPool);
        }
    }
}


File: core/src/test/java/org/elasticsearch/index/query/BaseQueryTestCase.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.index.query;

import com.carrotsearch.randomizedtesting.annotations.Repeat;

import org.apache.lucene.search.Query;
import org.elasticsearch.Version;
import org.elasticsearch.action.admin.indices.mapping.put.PutMappingRequest;
import org.elasticsearch.cluster.ClusterService;
import org.elasticsearch.cluster.metadata.IndexMetaData;
import org.elasticsearch.cluster.metadata.MetaData;
import org.elasticsearch.common.compress.CompressedXContent;
import org.elasticsearch.common.inject.AbstractModule;
import org.elasticsearch.common.inject.Injector;
import org.elasticsearch.common.inject.ModulesBuilder;
import org.elasticsearch.common.inject.util.Providers;
import org.elasticsearch.common.io.stream.BytesStreamOutput;
import org.elasticsearch.common.io.stream.StreamInput;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.settings.SettingsModule;
import org.elasticsearch.common.xcontent.XContentFactory;
import org.elasticsearch.common.xcontent.XContentParser;
import org.elasticsearch.env.Environment;
import org.elasticsearch.env.EnvironmentModule;
import org.elasticsearch.index.Index;
import org.elasticsearch.index.IndexNameModule;
import org.elasticsearch.index.analysis.AnalysisModule;
import org.elasticsearch.index.cache.IndexCacheModule;
import org.elasticsearch.index.mapper.MapperService;
import org.elasticsearch.index.query.functionscore.FunctionScoreModule;
import org.elasticsearch.index.settings.IndexSettingsModule;
import org.elasticsearch.index.similarity.SimilarityModule;
import org.elasticsearch.indices.breaker.CircuitBreakerService;
import org.elasticsearch.indices.breaker.NoneCircuitBreakerService;
import org.elasticsearch.indices.query.IndicesQueriesModule;
import org.elasticsearch.script.ScriptModule;
import org.elasticsearch.search.internal.SearchContext;
import org.elasticsearch.test.ElasticsearchTestCase;
import org.elasticsearch.test.TestSearchContext;
import org.elasticsearch.threadpool.ThreadPool;
import org.elasticsearch.threadpool.ThreadPoolModule;
import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Ignore;
import org.junit.Test;

import java.io.IOException;

import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.instanceOf;
import static org.hamcrest.Matchers.is;

@Ignore
public abstract class BaseQueryTestCase<QB extends QueryBuilder<QB>> extends ElasticsearchTestCase {

    protected static final String DATE_FIELD_NAME = "age";
    protected static final String INT_FIELD_NAME = "price";
    protected static final String STRING_FIELD_NAME = "text";
    protected static final String DOUBLE_FIELD_NAME = "double";
    protected static final String BOOLEAN_FIELD_NAME = "boolean";

    private static Injector injector;
    private static IndexQueryParserService queryParserService;
    private static Index index;

    private static String[] currentTypes;

    protected static String[] getCurrentTypes() {
        return currentTypes;
    }

    /**
     * Setup for the whole base test class.
     * @throws IOException
     */
    @BeforeClass
    public static void init() throws IOException {
        Settings settings = Settings.settingsBuilder()
                .put("name", BaseQueryTestCase.class.toString())
                .put("path.home", createTempDir())
                .put(IndexMetaData.SETTING_VERSION_CREATED, Version.CURRENT)
                .build();

        index = new Index("test");
        injector = new ModulesBuilder().add(
                new EnvironmentModule(new Environment(settings)),
                new SettingsModule(settings),
                new ThreadPoolModule(new ThreadPool(settings)),
                new IndicesQueriesModule(),
                new ScriptModule(settings),
                new IndexSettingsModule(index, settings),
                new IndexCacheModule(settings),
                new AnalysisModule(settings),
                new SimilarityModule(settings),
                new IndexNameModule(index),
                new FunctionScoreModule(),
                new AbstractModule() {
                    @Override
                    protected void configure() {
                        bind(ClusterService.class).toProvider(Providers.of((ClusterService) null));
                        bind(CircuitBreakerService.class).to(NoneCircuitBreakerService.class);
                    }
                }
        ).createInjector();
        queryParserService = injector.getInstance(IndexQueryParserService.class);
        MapperService mapperService = queryParserService.mapperService;
        //create some random type with some default field, those types will stick around for all of the subclasses
        currentTypes = new String[randomIntBetween(0, 5)];
        for (int i = 0; i < currentTypes.length; i++) {
            String type = randomAsciiOfLengthBetween(1, 10);
            mapperService.merge(type, new CompressedXContent(PutMappingRequest.buildFromSimplifiedDef(type,
                    DATE_FIELD_NAME, "type=date",
                    INT_FIELD_NAME, "type=integer",
                    DOUBLE_FIELD_NAME, "type=double",
                    BOOLEAN_FIELD_NAME, "type=boolean",
                    STRING_FIELD_NAME, "type=string").string()), false);
            currentTypes[i] = type;
        }
    }

    @AfterClass
    public static void afterClass() throws Exception {
        terminate(injector.getInstance(ThreadPool.class));
        injector = null;
        index = null;
        queryParserService = null;
        currentTypes = null;
    }

    @Before
    public void beforeTest() {
        //set some random types to be queried as part the search request, before each test
        String[] types;
        if (currentTypes.length > 0 && randomBoolean()) {
            int numberOfQueryTypes = randomIntBetween(1, currentTypes.length);
            types = new String[numberOfQueryTypes];
            for (int i = 0; i < numberOfQueryTypes; i++) {
                types[i] = randomFrom(currentTypes);
            }
        } else {
            if (randomBoolean()) {
                types = new String[]{MetaData.ALL};
            } else {
                types = new String[0];
            }
        }
        //some query (e.g. range query) have a different behaviour depending on whether the current search context is set or not
        //which is why we randomly set the search context, which will internally also do QueryParseContext.setTypes(types)
        if (randomBoolean()) {
            QueryParseContext.setTypes(types);
        } else {
            TestSearchContext testSearchContext = new TestSearchContext();
            testSearchContext.setTypes(types);
            SearchContext.setCurrent(testSearchContext);
        }
    }

    @After
    public void afterTest() {
        QueryParseContext.removeTypes();
        SearchContext.removeCurrent();
    }

    /**
     * Create the query that is being tested
     */
    protected abstract QB createTestQueryBuilder();

    /**
     * Creates an empty builder of the type of query under test
     */
    protected abstract QB createEmptyQueryBuilder();

    /**
     * Generic test that creates new query from the test query and checks both for equality
     * and asserts equality on the two queries.
     */
    @Test
    @Repeat(iterations = 20)
    public void testFromXContent() throws IOException {
        QB testQuery = createTestQueryBuilder();
        QueryParseContext context = createContext();
        String contentString = testQuery.toString();
        XContentParser parser = XContentFactory.xContent(contentString).createParser(contentString);
        context.reset(parser);
        assertQueryHeader(parser, testQuery.queryId());

        QueryBuilder newQuery = queryParserService.queryParser(testQuery.queryId()).fromXContent(context);
        assertNotSame(newQuery, testQuery);
        assertEquals(newQuery, testQuery);
        assertEquals(newQuery.hashCode(), testQuery.hashCode());
    }

    /**
     * Test creates the {@link Query} from the {@link QueryBuilder} under test and delegates the
     * assertions being made on the result to the implementing subclass.
     */
    @Test
    @Repeat(iterations = 20)
    public void testToQuery() throws IOException {
        QB testQuery = createTestQueryBuilder();
        QueryParseContext context = createContext();
        context.setAllowUnmappedFields(true);

        Query expectedQuery = createExpectedQuery(testQuery, context);
        Query actualQuery = testQuery.toQuery(context);
        assertThat(actualQuery, instanceOf(expectedQuery.getClass()));
        assertThat(actualQuery, equalTo(expectedQuery));
        assertLuceneQuery(testQuery, actualQuery, context);
    }

    /**
     * Creates the expected lucene query given the current {@link QueryBuilder} and {@link QueryParseContext}.
     * The returned query will be compared with the result of {@link QueryBuilder#toQuery(QueryParseContext)} to test its behaviour.
     */
    protected abstract Query createExpectedQuery(QB queryBuilder, QueryParseContext context) throws IOException;

    /**
     * Run after default equality comparison between lucene expected query and result of {@link QueryBuilder#toQuery(QueryParseContext)}.
     * Can contain additional assertions that are query specific. Empty default implementation.
     */
    protected void assertLuceneQuery(QB queryBuilder, Query query, QueryParseContext context) {

    }

    /**
     * Test serialization and deserialization of the test query.
     */
    @Test
    @Repeat(iterations = 20)
    public void testSerialization() throws IOException {
        QB testQuery = createTestQueryBuilder();
        try (BytesStreamOutput output = new BytesStreamOutput()) {
            testQuery.writeTo(output);
            try (StreamInput in = StreamInput.wrap(output.bytes())) {
                QB deserializedQuery = createEmptyQueryBuilder().readFrom(in);
                assertEquals(deserializedQuery, testQuery);
                assertEquals(deserializedQuery.hashCode(), testQuery.hashCode());
                assertNotSame(deserializedQuery, testQuery);
            }
        }
    }

    /**
     * @return a new {@link QueryParseContext} based on the base test index and queryParserService
     */
    protected static QueryParseContext createContext() {
        return new QueryParseContext(index, queryParserService);
    }

    protected static void assertQueryHeader(XContentParser parser, String expectedParserName) throws IOException {
        assertThat(parser.nextToken(), is(XContentParser.Token.START_OBJECT));
        assertThat(parser.nextToken(), is(XContentParser.Token.FIELD_NAME));
        assertThat(parser.currentName(), is(expectedParserName));
        assertThat(parser.nextToken(), is(XContentParser.Token.START_OBJECT));
    }
}


File: core/src/test/java/org/elasticsearch/plugins/PluggableTransportModuleTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.elasticsearch.plugins;

import org.elasticsearch.Version;
import org.elasticsearch.cluster.node.DiscoveryNode;
import org.elasticsearch.common.inject.Inject;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.test.ElasticsearchIntegrationTest;
import org.elasticsearch.test.transport.AssertingLocalTransport;
import org.elasticsearch.threadpool.ThreadPool;
import org.elasticsearch.transport.*;
import org.junit.Test;

import java.io.IOException;
import java.util.concurrent.atomic.AtomicInteger;

import static org.elasticsearch.common.settings.Settings.settingsBuilder;
import static org.elasticsearch.test.ElasticsearchIntegrationTest.ClusterScope;
import static org.elasticsearch.test.ElasticsearchIntegrationTest.Scope;
import static org.hamcrest.Matchers.*;

/**
 *
 */
@ClusterScope(scope = Scope.SUITE, numDataNodes = 2)
public class PluggableTransportModuleTests extends ElasticsearchIntegrationTest {

    public static final AtomicInteger SENT_REQUEST_COUNTER = new AtomicInteger(0);

    @Override
    protected Settings nodeSettings(int nodeOrdinal) {
        return settingsBuilder()
                .put(super.nodeSettings(nodeOrdinal))
                .put("plugin.types", CountingSentRequestsPlugin.class.getName())
                .build();
    }

    @Override
    protected Settings transportClientSettings() {
        return settingsBuilder()
                .put("plugin.types", CountingSentRequestsPlugin.class.getName())
                .put(super.transportClientSettings())
                .build();
    }

    @Test
    public void testThatPluginFunctionalityIsLoadedWithoutConfiguration() throws Exception {
        for (Transport transport : internalCluster().getInstances(Transport.class)) {
            assertThat(transport, instanceOf(CountingAssertingLocalTransport.class));
        }

        int countBeforeRequest = SENT_REQUEST_COUNTER.get();
        internalCluster().clientNodeClient().admin().cluster().prepareHealth().get();
        int countAfterRequest = SENT_REQUEST_COUNTER.get();
        assertThat("Expected send request counter to be greather than zero", countAfterRequest, is(greaterThan(countBeforeRequest)));
    }

    public static class CountingSentRequestsPlugin extends AbstractPlugin {
        @Override
        public String name() {
            return "counting-pipelines-plugin";
        }

        @Override
        public String description() {
            return "counting-pipelines-plugin";
        }

        public void onModule(TransportModule transportModule) {
            transportModule.setTransport(CountingAssertingLocalTransport.class, this.name());
        }
    }

    public static final class CountingAssertingLocalTransport extends AssertingLocalTransport {

        @Inject
        public CountingAssertingLocalTransport(Settings settings, ThreadPool threadPool, Version version) {
            super(settings, threadPool, version);
        }

        @Override
        public void sendRequest(final DiscoveryNode node, final long requestId, final String action, final TransportRequest request, TransportRequestOptions options) throws IOException, TransportException {
            SENT_REQUEST_COUNTER.incrementAndGet();
            super.sendRequest(node, requestId, action, request, options);
        }
    }
}


File: core/src/test/java/org/elasticsearch/test/transport/AssertingLocalTransport.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.test.transport;

import org.elasticsearch.Version;
import org.elasticsearch.cluster.node.DiscoveryNode;
import org.elasticsearch.common.inject.Inject;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.test.ElasticsearchIntegrationTest;
import org.elasticsearch.test.VersionUtils;
import org.elasticsearch.test.hamcrest.ElasticsearchAssertions;
import org.elasticsearch.threadpool.ThreadPool;
import org.elasticsearch.transport.*;
import org.elasticsearch.transport.local.LocalTransport;

import java.io.IOException;
import java.util.Random;

/**
 *
 */
public class AssertingLocalTransport extends LocalTransport {

    public static final String ASSERTING_TRANSPORT_MIN_VERSION_KEY = "transport.asserting.version.min";
    public static final String ASSERTING_TRANSPORT_MAX_VERSION_KEY = "transport.asserting.version.max";
    private final Random random;
    private final Version minVersion;
    private final Version maxVersion;

    @Inject
    public AssertingLocalTransport(Settings settings, ThreadPool threadPool, Version version) {
        super(settings, threadPool, version);
        final long seed = settings.getAsLong(ElasticsearchIntegrationTest.SETTING_INDEX_SEED, 0l);
        random = new Random(seed);
        minVersion = settings.getAsVersion(ASSERTING_TRANSPORT_MIN_VERSION_KEY, Version.V_0_18_0);
        maxVersion = settings.getAsVersion(ASSERTING_TRANSPORT_MAX_VERSION_KEY, Version.CURRENT);
    }

    @Override
    protected void handleParsedResponse(final TransportResponse response, final TransportResponseHandler handler) {
        ElasticsearchAssertions.assertVersionSerializable(VersionUtils.randomVersionBetween(random, minVersion, maxVersion), response);
        super.handleParsedResponse(response, handler);
    }
    
    @Override
    public void sendRequest(final DiscoveryNode node, final long requestId, final String action, final TransportRequest request, TransportRequestOptions options) throws IOException, TransportException {
        ElasticsearchAssertions.assertVersionSerializable(VersionUtils.randomVersionBetween(random, minVersion, maxVersion), request);
        super.sendRequest(node, requestId, action, request, options);
    }
}


File: core/src/test/java/org/elasticsearch/transport/AbstractSimpleTransportTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.transport;

import com.google.common.collect.ImmutableMap;
import org.elasticsearch.Version;
import org.elasticsearch.cluster.node.DiscoveryNode;
import org.elasticsearch.common.io.stream.StreamInput;
import org.elasticsearch.common.io.stream.StreamOutput;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.transport.TransportAddress;
import org.elasticsearch.common.unit.TimeValue;
import org.elasticsearch.test.ElasticsearchTestCase;
import org.elasticsearch.test.junit.annotations.TestLogging;
import org.elasticsearch.test.transport.MockTransportService;
import org.elasticsearch.threadpool.ThreadPool;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.io.IOException;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

import static org.elasticsearch.transport.TransportRequestOptions.options;
import static org.hamcrest.Matchers.*;

/**
 *
 */
public abstract class AbstractSimpleTransportTests extends ElasticsearchTestCase {

    protected ThreadPool threadPool;

    protected static final Version version0 = Version.fromId(/*0*/99);
    protected DiscoveryNode nodeA;
    protected MockTransportService serviceA;

    protected static final Version version1 = Version.fromId(199);
    protected DiscoveryNode nodeB;
    protected MockTransportService serviceB;

    protected abstract MockTransportService build(Settings settings, Version version);

    @Override
    @Before
    public void setUp() throws Exception {
        super.setUp();
        threadPool = new ThreadPool(getClass().getName());
        serviceA = build(
                Settings.builder().put("name", "TS_A", TransportService.SETTING_TRACE_LOG_INCLUDE, "", TransportService.SETTING_TRACE_LOG_EXCLUDE, "NOTHING").build(),
                version0
        );
        nodeA = new DiscoveryNode("TS_A", "TS_A", serviceA.boundAddress().publishAddress(), ImmutableMap.<String, String>of(), version0);
        serviceB = build(
                Settings.builder().put("name", "TS_B", TransportService.SETTING_TRACE_LOG_INCLUDE, "", TransportService.SETTING_TRACE_LOG_EXCLUDE, "NOTHING").build(),
                version1
        );
        nodeB = new DiscoveryNode("TS_B", "TS_B", serviceB.boundAddress().publishAddress(), ImmutableMap.<String, String>of(), version1);

        // wait till all nodes are properly connected and the event has been sent, so tests in this class
        // will not get this callback called on the connections done in this setup
        final boolean useLocalNode = randomBoolean();
        final CountDownLatch latch = new CountDownLatch(useLocalNode ? 2 : 4);
        TransportConnectionListener waitForConnection = new TransportConnectionListener() {
            @Override
            public void onNodeConnected(DiscoveryNode node) {
                latch.countDown();
            }

            @Override
            public void onNodeDisconnected(DiscoveryNode node) {
                fail("disconnect should not be called " + node);
            }
        };
        serviceA.addConnectionListener(waitForConnection);
        serviceB.addConnectionListener(waitForConnection);

        if (useLocalNode) {
            logger.info("--> using local node optimization");
            serviceA.setLocalNode(nodeA);
            serviceB.setLocalNode(nodeB);
        } else {
            logger.info("--> actively connecting to local node");
            serviceA.connectToNode(nodeA);
            serviceB.connectToNode(nodeB);
        }

        serviceA.connectToNode(nodeB);
        serviceB.connectToNode(nodeA);

        assertThat("failed to wait for all nodes to connect", latch.await(5, TimeUnit.SECONDS), equalTo(true));
        serviceA.removeConnectionListener(waitForConnection);
        serviceB.removeConnectionListener(waitForConnection);
    }

    @Override
    @After
    public void tearDown() throws Exception {
        super.tearDown();
        serviceA.close();
        serviceB.close();
        terminate(threadPool);
    }

    @Test
    public void testHelloWorld() {
        serviceA.registerRequestHandler("sayHello", StringMessageRequest.class, ThreadPool.Names.GENERIC, new TransportRequestHandler<StringMessageRequest>() {
            @Override
            public void messageReceived(StringMessageRequest request, TransportChannel channel) {
                assertThat("moshe", equalTo(request.message));
                try {
                    channel.sendResponse(new StringMessageResponse("hello " + request.message));
                } catch (IOException e) {
                    e.printStackTrace();
                    assertThat(e.getMessage(), false, equalTo(true));
                }
            }
        });

        TransportFuture<StringMessageResponse> res = serviceB.submitRequest(nodeA, "sayHello",
                new StringMessageRequest("moshe"), new BaseTransportResponseHandler<StringMessageResponse>() {
                    @Override
                    public StringMessageResponse newInstance() {
                        return new StringMessageResponse();
                    }

                    @Override
                    public String executor() {
                        return ThreadPool.Names.GENERIC;
                    }

                    @Override
                    public void handleResponse(StringMessageResponse response) {
                        assertThat("hello moshe", equalTo(response.message));
                    }

                    @Override
                    public void handleException(TransportException exp) {
                        exp.printStackTrace();
                        assertThat("got exception instead of a response: " + exp.getMessage(), false, equalTo(true));
                    }
                });

        try {
            StringMessageResponse message = res.get();
            assertThat("hello moshe", equalTo(message.message));
        } catch (Exception e) {
            assertThat(e.getMessage(), false, equalTo(true));
        }

        res = serviceB.submitRequest(nodeA, "sayHello",
                new StringMessageRequest("moshe"), TransportRequestOptions.options().withCompress(true), new BaseTransportResponseHandler<StringMessageResponse>() {
                    @Override
                    public StringMessageResponse newInstance() {
                        return new StringMessageResponse();
                    }

                    @Override
                    public String executor() {
                        return ThreadPool.Names.GENERIC;
                    }

                    @Override
                    public void handleResponse(StringMessageResponse response) {
                        assertThat("hello moshe", equalTo(response.message));
                    }

                    @Override
                    public void handleException(TransportException exp) {
                        exp.printStackTrace();
                        assertThat("got exception instead of a response: " + exp.getMessage(), false, equalTo(true));
                    }
                });

        try {
            StringMessageResponse message = res.get();
            assertThat("hello moshe", equalTo(message.message));
        } catch (Exception e) {
            assertThat(e.getMessage(), false, equalTo(true));
        }

        serviceA.removeHandler("sayHello");
    }

    @Test
    public void testLocalNodeConnection() throws InterruptedException {
        assertTrue("serviceA is not connected to nodeA", serviceA.nodeConnected(nodeA));
        if (((TransportService) serviceA).getLocalNode() != null) {
            // this should be a noop
            serviceA.disconnectFromNode(nodeA);
        }
        final AtomicReference<Exception> exception = new AtomicReference<>();
        serviceA.registerRequestHandler("localNode", StringMessageRequest.class, ThreadPool.Names.GENERIC, new TransportRequestHandler<StringMessageRequest>() {
            @Override
            public void messageReceived(StringMessageRequest request, TransportChannel channel) {
                try {
                    channel.sendResponse(new StringMessageResponse(request.message));
                } catch (IOException e) {
                    exception.set(e);
                }
            }
        });
        final AtomicReference<String> responseString = new AtomicReference<>();
        final CountDownLatch responseLatch = new CountDownLatch(1);
        serviceA.sendRequest(nodeA, "localNode", new StringMessageRequest("test"), new TransportResponseHandler<StringMessageResponse>() {
            @Override
            public StringMessageResponse newInstance() {
                return new StringMessageResponse();
            }

            @Override
            public void handleResponse(StringMessageResponse response) {
                responseString.set(response.message);
                responseLatch.countDown();
            }

            @Override
            public void handleException(TransportException exp) {
                exception.set(exp);
                responseLatch.countDown();
            }

            @Override
            public String executor() {
                return ThreadPool.Names.GENERIC;
            }
        });
        responseLatch.await();
        assertNull(exception.get());
        assertThat(responseString.get(), equalTo("test"));
    }

    @Test
    public void testVoidMessageCompressed() {
        serviceA.registerRequestHandler("sayHello", TransportRequest.Empty.class, ThreadPool.Names.GENERIC, new TransportRequestHandler<TransportRequest.Empty>() {
            @Override
            public void messageReceived(TransportRequest.Empty request, TransportChannel channel) {
                try {
                    channel.sendResponse(TransportResponse.Empty.INSTANCE, TransportResponseOptions.options().withCompress(true));
                } catch (IOException e) {
                    e.printStackTrace();
                    assertThat(e.getMessage(), false, equalTo(true));
                }
            }
        });

        TransportFuture<TransportResponse.Empty> res = serviceB.submitRequest(nodeA, "sayHello",
                TransportRequest.Empty.INSTANCE, TransportRequestOptions.options().withCompress(true), new BaseTransportResponseHandler<TransportResponse.Empty>() {
                    @Override
                    public TransportResponse.Empty newInstance() {
                        return TransportResponse.Empty.INSTANCE;
                    }

                    @Override
                    public String executor() {
                        return ThreadPool.Names.GENERIC;
                    }

                    @Override
                    public void handleResponse(TransportResponse.Empty response) {
                    }

                    @Override
                    public void handleException(TransportException exp) {
                        exp.printStackTrace();
                        assertThat("got exception instead of a response: " + exp.getMessage(), false, equalTo(true));
                    }
                });

        try {
            TransportResponse.Empty message = res.get();
            assertThat(message, notNullValue());
        } catch (Exception e) {
            assertThat(e.getMessage(), false, equalTo(true));
        }

        serviceA.removeHandler("sayHello");
    }

    @Test
    public void testHelloWorldCompressed() {
        serviceA.registerRequestHandler("sayHello", StringMessageRequest.class, ThreadPool.Names.GENERIC, new TransportRequestHandler<StringMessageRequest>() {
            @Override
            public void messageReceived(StringMessageRequest request, TransportChannel channel) {
                assertThat("moshe", equalTo(request.message));
                try {
                    channel.sendResponse(new StringMessageResponse("hello " + request.message), TransportResponseOptions.options().withCompress(true));
                } catch (IOException e) {
                    e.printStackTrace();
                    assertThat(e.getMessage(), false, equalTo(true));
                }
            }
        });

        TransportFuture<StringMessageResponse> res = serviceB.submitRequest(nodeA, "sayHello",
                new StringMessageRequest("moshe"), TransportRequestOptions.options().withCompress(true), new BaseTransportResponseHandler<StringMessageResponse>() {
                    @Override
                    public StringMessageResponse newInstance() {
                        return new StringMessageResponse();
                    }

                    @Override
                    public String executor() {
                        return ThreadPool.Names.GENERIC;
                    }

                    @Override
                    public void handleResponse(StringMessageResponse response) {
                        assertThat("hello moshe", equalTo(response.message));
                    }

                    @Override
                    public void handleException(TransportException exp) {
                        exp.printStackTrace();
                        assertThat("got exception instead of a response: " + exp.getMessage(), false, equalTo(true));
                    }
                });

        try {
            StringMessageResponse message = res.get();
            assertThat("hello moshe", equalTo(message.message));
        } catch (Exception e) {
            assertThat(e.getMessage(), false, equalTo(true));
        }

        serviceA.removeHandler("sayHello");
    }

    @Test
    public void testErrorMessage() {
        serviceA.registerRequestHandler("sayHelloException", StringMessageRequest.class, ThreadPool.Names.GENERIC, new TransportRequestHandler<StringMessageRequest>() {
            @Override
            public void messageReceived(StringMessageRequest request, TransportChannel channel) throws Exception {
                assertThat("moshe", equalTo(request.message));
                throw new RuntimeException("bad message !!!");
            }
        });

        TransportFuture<StringMessageResponse> res = serviceB.submitRequest(nodeA, "sayHelloException",
                new StringMessageRequest("moshe"), new BaseTransportResponseHandler<StringMessageResponse>() {
                    @Override
                    public StringMessageResponse newInstance() {
                        return new StringMessageResponse();
                    }

                    @Override
                    public String executor() {
                        return ThreadPool.Names.GENERIC;
                    }

                    @Override
                    public void handleResponse(StringMessageResponse response) {
                        fail("got response instead of exception");
                    }

                    @Override
                    public void handleException(TransportException exp) {
                        assertThat("bad message !!!", equalTo(exp.getCause().getMessage()));
                    }
                });

        try {
            res.txGet();
            fail("exception should be thrown");
        } catch (Exception e) {
            assertThat(e.getCause().getMessage(), equalTo("bad message !!!"));
        }

        serviceA.removeHandler("sayHelloException");
    }

    @Test
    public void testDisconnectListener() throws Exception {
        final CountDownLatch latch = new CountDownLatch(1);
        TransportConnectionListener disconnectListener = new TransportConnectionListener() {
            @Override
            public void onNodeConnected(DiscoveryNode node) {
                fail("node connected should not be called, all connection have been done previously, node: " + node);
            }

            @Override
            public void onNodeDisconnected(DiscoveryNode node) {
                latch.countDown();
            }
        };
        serviceA.addConnectionListener(disconnectListener);
        serviceB.close();
        assertThat(latch.await(5, TimeUnit.SECONDS), equalTo(true));
    }

    @Test
    public void testNotifyOnShutdown() throws Exception {
        final CountDownLatch latch2 = new CountDownLatch(1);

        serviceA.registerRequestHandler("foobar", StringMessageRequest.class, ThreadPool.Names.GENERIC, new TransportRequestHandler<StringMessageRequest>() {
            @Override
            public void messageReceived(StringMessageRequest request, TransportChannel channel) {
                try {
                    latch2.await();
                    logger.info("Stop ServiceB now");
                    serviceB.stop();
                } catch (Exception e) {
                    fail(e.getMessage());
                }
            }
        });
        TransportFuture<TransportResponse.Empty> foobar = serviceB.submitRequest(nodeA, "foobar",
                new StringMessageRequest(""), options(), EmptyTransportResponseHandler.INSTANCE_SAME);
        latch2.countDown();
        try {
            foobar.txGet();
            fail("TransportException expected");
        } catch (TransportException ex) {

        }
        serviceA.removeHandler("sayHelloTimeoutDelayedResponse");
    }

    @Test
    public void testTimeoutSendExceptionWithNeverSendingBackResponse() throws Exception {
        serviceA.registerRequestHandler("sayHelloTimeoutNoResponse", StringMessageRequest.class, ThreadPool.Names.GENERIC, new TransportRequestHandler<StringMessageRequest>() {
            @Override
            public void messageReceived(StringMessageRequest request, TransportChannel channel) {
                assertThat("moshe", equalTo(request.message));
                // don't send back a response
//                try {
//                    channel.sendResponse(new StringMessage("hello " + request.message));
//                } catch (IOException e) {
//                    e.printStackTrace();
//                    assertThat(e.getMessage(), false, equalTo(true));
//                }
            }
        });

        TransportFuture<StringMessageResponse> res = serviceB.submitRequest(nodeA, "sayHelloTimeoutNoResponse",
                new StringMessageRequest("moshe"), options().withTimeout(100), new BaseTransportResponseHandler<StringMessageResponse>() {
                    @Override
                    public StringMessageResponse newInstance() {
                        return new StringMessageResponse();
                    }

                    @Override
                    public String executor() {
                        return ThreadPool.Names.GENERIC;
                    }

                    @Override
                    public void handleResponse(StringMessageResponse response) {
                        fail("got response instead of exception");
                    }

                    @Override
                    public void handleException(TransportException exp) {
                        assertThat(exp, instanceOf(ReceiveTimeoutTransportException.class));
                    }
                });

        try {
            StringMessageResponse message = res.txGet();
            fail("exception should be thrown");
        } catch (Exception e) {
            assertThat(e, instanceOf(ReceiveTimeoutTransportException.class));
        }

        serviceA.removeHandler("sayHelloTimeoutNoResponse");
    }

    @Test
    public void testTimeoutSendExceptionWithDelayedResponse() throws Exception {
        serviceA.registerRequestHandler("sayHelloTimeoutDelayedResponse", StringMessageRequest.class, ThreadPool.Names.GENERIC, new TransportRequestHandler<StringMessageRequest>() {
            @Override
            public void messageReceived(StringMessageRequest request, TransportChannel channel) {
                TimeValue sleep = TimeValue.parseTimeValue(request.message, null, "sleep");
                try {
                    Thread.sleep(sleep.millis());
                } catch (InterruptedException e) {
                    // ignore
                }
                try {
                    channel.sendResponse(new StringMessageResponse("hello " + request.message));
                } catch (IOException e) {
                    e.printStackTrace();
                    assertThat(e.getMessage(), false, equalTo(true));
                }
            }
        });
        final CountDownLatch latch = new CountDownLatch(1);
        TransportFuture<StringMessageResponse> res = serviceB.submitRequest(nodeA, "sayHelloTimeoutDelayedResponse",
                new StringMessageRequest("300ms"), options().withTimeout(100), new BaseTransportResponseHandler<StringMessageResponse>() {
                    @Override
                    public StringMessageResponse newInstance() {
                        return new StringMessageResponse();
                    }

                    @Override
                    public String executor() {
                        return ThreadPool.Names.GENERIC;
                    }

                    @Override
                    public void handleResponse(StringMessageResponse response) {
                        latch.countDown();
                        fail("got response instead of exception");
                    }

                    @Override
                    public void handleException(TransportException exp) {
                        latch.countDown();
                        assertThat(exp, instanceOf(ReceiveTimeoutTransportException.class));
                    }
                });

        try {
            StringMessageResponse message = res.txGet();
            fail("exception should be thrown");
        } catch (Exception e) {
            assertThat(e, instanceOf(ReceiveTimeoutTransportException.class));
        }
        latch.await();

        for (int i = 0; i < 10; i++) {
            final int counter = i;
            // now, try and send another request, this times, with a short timeout
            res = serviceB.submitRequest(nodeA, "sayHelloTimeoutDelayedResponse",
                    new StringMessageRequest(counter + "ms"), options().withTimeout(3000), new BaseTransportResponseHandler<StringMessageResponse>() {
                        @Override
                        public StringMessageResponse newInstance() {
                            return new StringMessageResponse();
                        }

                        @Override
                        public String executor() {
                            return ThreadPool.Names.GENERIC;
                        }

                        @Override
                        public void handleResponse(StringMessageResponse response) {
                            assertThat("hello " + counter + "ms", equalTo(response.message));
                        }

                        @Override
                        public void handleException(TransportException exp) {
                            exp.printStackTrace();
                            fail("got exception instead of a response for " + counter + ": " + exp.getDetailedMessage());
                        }
                    });

            StringMessageResponse message = res.txGet();
            assertThat(message.message, equalTo("hello " + counter + "ms"));
        }

        serviceA.removeHandler("sayHelloTimeoutDelayedResponse");
    }


    @Test
    @TestLogging(value = "test. transport.tracer:TRACE")
    public void testTracerLog() throws InterruptedException {
        TransportRequestHandler handler = new TransportRequestHandler<StringMessageRequest>() {
            @Override
            public void messageReceived(StringMessageRequest request, TransportChannel channel) throws Exception {
                channel.sendResponse(new StringMessageResponse(""));
            }
        };

        TransportRequestHandler handlerWithError = new TransportRequestHandler<StringMessageRequest>() {
            @Override
            public void messageReceived(StringMessageRequest request, TransportChannel channel) throws Exception {
                if (request.timeout() > 0) {
                    Thread.sleep(request.timeout);
                }
                channel.sendResponse(new RuntimeException(""));

            }
        };

        final Semaphore requestCompleted = new Semaphore(0);
        TransportResponseHandler noopResponseHandler = new BaseTransportResponseHandler<StringMessageResponse>() {

            @Override
            public StringMessageResponse newInstance() {
                return new StringMessageResponse();
            }

            @Override
            public void handleResponse(StringMessageResponse response) {
                requestCompleted.release();
            }

            @Override
            public void handleException(TransportException exp) {
                requestCompleted.release();
            }

            @Override
            public String executor() {
                return ThreadPool.Names.SAME;
            }
        };

        serviceA.registerRequestHandler("test", StringMessageRequest.class, ThreadPool.Names.SAME, handler);
        serviceA.registerRequestHandler("testError", StringMessageRequest.class, ThreadPool.Names.SAME, handlerWithError);
        serviceB.registerRequestHandler("test", StringMessageRequest.class, ThreadPool.Names.SAME, handler);
        serviceB.registerRequestHandler("testError", StringMessageRequest.class, ThreadPool.Names.SAME, handlerWithError);

        final Tracer tracer = new Tracer();
        serviceA.addTracer(tracer);
        serviceB.addTracer(tracer);

        tracer.reset(4);
        boolean timeout = randomBoolean();
        TransportRequestOptions options = timeout ? new TransportRequestOptions().withTimeout(1) : TransportRequestOptions.EMPTY;
        serviceA.sendRequest(nodeB, "test", new StringMessageRequest("", 10), options, noopResponseHandler);
        requestCompleted.acquire();
        tracer.expectedEvents.get().await();
        assertThat("didn't see request sent", tracer.sawRequestSent, equalTo(true));
        assertThat("didn't see request received", tracer.sawRequestReceived, equalTo(true));
        assertThat("didn't see response sent", tracer.sawResponseSent, equalTo(true));
        assertThat("didn't see response received", tracer.sawResponseReceived, equalTo(true));
        assertThat("saw error sent", tracer.sawErrorSent, equalTo(false));

        tracer.reset(4);
        serviceA.sendRequest(nodeB, "testError", new StringMessageRequest(""), noopResponseHandler);
        requestCompleted.acquire();
        tracer.expectedEvents.get().await();
        assertThat("didn't see request sent", tracer.sawRequestSent, equalTo(true));
        assertThat("didn't see request received", tracer.sawRequestReceived, equalTo(true));
        assertThat("saw response sent", tracer.sawResponseSent, equalTo(false));
        assertThat("didn't see response received", tracer.sawResponseReceived, equalTo(true));
        assertThat("didn't see error sent", tracer.sawErrorSent, equalTo(true));

        String includeSettings;
        String excludeSettings;
        if (randomBoolean()) {
            // sometimes leave include empty (default)
            includeSettings = randomBoolean() ? "*" : "";
            excludeSettings = "*Error";
        } else {
            includeSettings = "test";
            excludeSettings = "DOESN'T_MATCH";
        }

        serviceA.applySettings(Settings.builder()
                .put(TransportService.SETTING_TRACE_LOG_INCLUDE, includeSettings, TransportService.SETTING_TRACE_LOG_EXCLUDE, excludeSettings)
                .build());

        tracer.reset(4);
        serviceA.sendRequest(nodeB, "test", new StringMessageRequest(""), noopResponseHandler);
        requestCompleted.acquire();
        tracer.expectedEvents.get().await();
        assertThat("didn't see request sent", tracer.sawRequestSent, equalTo(true));
        assertThat("didn't see request received", tracer.sawRequestReceived, equalTo(true));
        assertThat("didn't see response sent", tracer.sawResponseSent, equalTo(true));
        assertThat("didn't see response received", tracer.sawResponseReceived, equalTo(true));
        assertThat("saw error sent", tracer.sawErrorSent, equalTo(false));

        tracer.reset(2);
        serviceA.sendRequest(nodeB, "testError", new StringMessageRequest(""), noopResponseHandler);
        requestCompleted.acquire();
        tracer.expectedEvents.get().await();
        assertThat("saw request sent", tracer.sawRequestSent, equalTo(false));
        assertThat("didn't see request received", tracer.sawRequestReceived, equalTo(true));
        assertThat("saw response sent", tracer.sawResponseSent, equalTo(false));
        assertThat("saw response received", tracer.sawResponseReceived, equalTo(false));
        assertThat("didn't see error sent", tracer.sawErrorSent, equalTo(true));
    }

    private static class Tracer extends MockTransportService.Tracer {
        public volatile boolean sawRequestSent;
        public volatile boolean sawRequestReceived;
        public volatile boolean sawResponseSent;
        public volatile boolean sawErrorSent;
        public volatile boolean sawResponseReceived;

        public AtomicReference<CountDownLatch> expectedEvents = new AtomicReference<>();


        @Override
        public void receivedRequest(long requestId, String action) {
            super.receivedRequest(requestId, action);
            sawRequestReceived = true;
            expectedEvents.get().countDown();
        }

        @Override
        public void requestSent(DiscoveryNode node, long requestId, String action, TransportRequestOptions options) {
            super.requestSent(node, requestId, action, options);
            sawRequestSent = true;
            expectedEvents.get().countDown();
        }

        @Override
        public void responseSent(long requestId, String action) {
            super.responseSent(requestId, action);
            sawResponseSent = true;
            expectedEvents.get().countDown();
        }

        @Override
        public void responseSent(long requestId, String action, Throwable t) {
            super.responseSent(requestId, action, t);
            sawErrorSent = true;
            expectedEvents.get().countDown();
        }

        @Override
        public void receivedResponse(long requestId, DiscoveryNode sourceNode, String action) {
            super.receivedResponse(requestId, sourceNode, action);
            sawResponseReceived = true;
            expectedEvents.get().countDown();
        }

        public void reset(int expectedCount) {
            sawRequestSent = false;
            sawRequestReceived = false;
            sawResponseSent = false;
            sawErrorSent = false;
            sawResponseReceived = false;
            expectedEvents.set(new CountDownLatch(expectedCount));
        }
    }


    static class StringMessageRequest extends TransportRequest {

        private String message;
        private long timeout;

        StringMessageRequest(String message, long timeout) {
            this.message = message;
            this.timeout = timeout;
        }

        StringMessageRequest() {
        }

        public StringMessageRequest(String message) {
            this(message, -1);
        }

        public long timeout() {
            return timeout;
        }

        @Override
        public void readFrom(StreamInput in) throws IOException {
            super.readFrom(in);
            message = in.readString();
            timeout = in.readLong();
        }

        @Override
        public void writeTo(StreamOutput out) throws IOException {
            super.writeTo(out);
            out.writeString(message);
            out.writeLong(timeout);
        }
    }

    static class StringMessageResponse extends TransportResponse {

        private String message;

        StringMessageResponse(String message) {
            this.message = message;
        }

        StringMessageResponse() {
        }

        @Override
        public void readFrom(StreamInput in) throws IOException {
            super.readFrom(in);
            message = in.readString();
        }

        @Override
        public void writeTo(StreamOutput out) throws IOException {
            super.writeTo(out);
            out.writeString(message);
        }
    }


    static class Version0Request extends TransportRequest {

        int value1;


        @Override
        public void readFrom(StreamInput in) throws IOException {
            super.readFrom(in);
            value1 = in.readInt();
        }

        @Override
        public void writeTo(StreamOutput out) throws IOException {
            super.writeTo(out);
            out.writeInt(value1);
        }
    }

    static class Version1Request extends Version0Request {

        int value2;

        @Override
        public void readFrom(StreamInput in) throws IOException {
            super.readFrom(in);
            if (in.getVersion().onOrAfter(version1)) {
                value2 = in.readInt();
            }
        }

        @Override
        public void writeTo(StreamOutput out) throws IOException {
            super.writeTo(out);
            if (out.getVersion().onOrAfter(version1)) {
                out.writeInt(value2);
            }
        }
    }

    static class Version0Response extends TransportResponse {

        int value1;

        @Override
        public void readFrom(StreamInput in) throws IOException {
            super.readFrom(in);
            value1 = in.readInt();
        }

        @Override
        public void writeTo(StreamOutput out) throws IOException {
            super.writeTo(out);
            out.writeInt(value1);
        }
    }

    static class Version1Response extends Version0Response {

        int value2;

        @Override
        public void readFrom(StreamInput in) throws IOException {
            super.readFrom(in);
            if (in.getVersion().onOrAfter(version1)) {
                value2 = in.readInt();
            }
        }

        @Override
        public void writeTo(StreamOutput out) throws IOException {
            super.writeTo(out);
            if (out.getVersion().onOrAfter(version1)) {
                out.writeInt(value2);
            }
        }
    }

    @Test
    public void testVersion_from0to1() throws Exception {
        serviceB.registerRequestHandler("/version", Version1Request.class, ThreadPool.Names.SAME, new TransportRequestHandler<Version1Request>() {
            @Override
            public void messageReceived(Version1Request request, TransportChannel channel) throws Exception {
                assertThat(request.value1, equalTo(1));
                assertThat(request.value2, equalTo(0)); // not set, coming from service A
                Version1Response response = new Version1Response();
                response.value1 = 1;
                response.value2 = 2;
                channel.sendResponse(response);
            }
        });

        Version0Request version0Request = new Version0Request();
        version0Request.value1 = 1;
        Version0Response version0Response = serviceA.submitRequest(nodeB, "/version", version0Request, new BaseTransportResponseHandler<Version0Response>() {
            @Override
            public Version0Response newInstance() {
                return new Version0Response();
            }

            @Override
            public void handleResponse(Version0Response response) {
                assertThat(response.value1, equalTo(1));
            }

            @Override
            public void handleException(TransportException exp) {
                exp.printStackTrace();
                fail();
            }

            @Override
            public String executor() {
                return ThreadPool.Names.SAME;
            }
        }).txGet();

        assertThat(version0Response.value1, equalTo(1));
    }

    @Test
    public void testVersion_from1to0() throws Exception {
        serviceA.registerRequestHandler("/version", Version0Request.class, ThreadPool.Names.SAME, new TransportRequestHandler<Version0Request>() {
            @Override
            public void messageReceived(Version0Request request, TransportChannel channel) throws Exception {
                assertThat(request.value1, equalTo(1));
                Version0Response response = new Version0Response();
                response.value1 = 1;
                channel.sendResponse(response);
            }
        });

        Version1Request version1Request = new Version1Request();
        version1Request.value1 = 1;
        version1Request.value2 = 2;
        Version1Response version1Response = serviceB.submitRequest(nodeA, "/version", version1Request, new BaseTransportResponseHandler<Version1Response>() {
            @Override
            public Version1Response newInstance() {
                return new Version1Response();
            }

            @Override
            public void handleResponse(Version1Response response) {
                assertThat(response.value1, equalTo(1));
                assertThat(response.value2, equalTo(0)); // initial values, cause its serialized from version 0
            }

            @Override
            public void handleException(TransportException exp) {
                exp.printStackTrace();
                fail();
            }

            @Override
            public String executor() {
                return ThreadPool.Names.SAME;
            }
        }).txGet();

        assertThat(version1Response.value1, equalTo(1));
        assertThat(version1Response.value2, equalTo(0));
    }

    @Test
    public void testVersion_from1to1() throws Exception {
        serviceB.registerRequestHandler("/version", Version1Request.class, ThreadPool.Names.SAME, new TransportRequestHandler<Version1Request>() {
            @Override
            public void messageReceived(Version1Request request, TransportChannel channel) throws Exception {
                assertThat(request.value1, equalTo(1));
                assertThat(request.value2, equalTo(2));
                Version1Response response = new Version1Response();
                response.value1 = 1;
                response.value2 = 2;
                channel.sendResponse(response);
            }
        });

        Version1Request version1Request = new Version1Request();
        version1Request.value1 = 1;
        version1Request.value2 = 2;
        Version1Response version1Response = serviceB.submitRequest(nodeB, "/version", version1Request, new BaseTransportResponseHandler<Version1Response>() {
            @Override
            public Version1Response newInstance() {
                return new Version1Response();
            }

            @Override
            public void handleResponse(Version1Response response) {
                assertThat(response.value1, equalTo(1));
                assertThat(response.value2, equalTo(2));
            }

            @Override
            public void handleException(TransportException exp) {
                exp.printStackTrace();
                fail();
            }

            @Override
            public String executor() {
                return ThreadPool.Names.SAME;
            }
        }).txGet();

        assertThat(version1Response.value1, equalTo(1));
        assertThat(version1Response.value2, equalTo(2));
    }

    @Test
    public void testVersion_from0to0() throws Exception {
        serviceA.registerRequestHandler("/version", Version0Request.class, ThreadPool.Names.SAME, new TransportRequestHandler<Version0Request>() {
            @Override
            public void messageReceived(Version0Request request, TransportChannel channel) throws Exception {
                assertThat(request.value1, equalTo(1));
                Version0Response response = new Version0Response();
                response.value1 = 1;
                channel.sendResponse(response);
            }
        });

        Version0Request version0Request = new Version0Request();
        version0Request.value1 = 1;
        Version0Response version0Response = serviceA.submitRequest(nodeA, "/version", version0Request, new BaseTransportResponseHandler<Version0Response>() {
            @Override
            public Version0Response newInstance() {
                return new Version0Response();
            }

            @Override
            public void handleResponse(Version0Response response) {
                assertThat(response.value1, equalTo(1));
            }

            @Override
            public void handleException(TransportException exp) {
                exp.printStackTrace();
                fail();
            }

            @Override
            public String executor() {
                return ThreadPool.Names.SAME;
            }
        }).txGet();

        assertThat(version0Response.value1, equalTo(1));
    }

    @Test
    public void testMockFailToSendNoConnectRule() {
        serviceA.registerRequestHandler("sayHello", StringMessageRequest.class, ThreadPool.Names.GENERIC, new TransportRequestHandler<StringMessageRequest>() {
            @Override
            public void messageReceived(StringMessageRequest request, TransportChannel channel) throws Exception {
                assertThat("moshe", equalTo(request.message));
                throw new RuntimeException("bad message !!!");
            }
        });

        serviceB.addFailToSendNoConnectRule(nodeA);

        TransportFuture<StringMessageResponse> res = serviceB.submitRequest(nodeA, "sayHello",
                new StringMessageRequest("moshe"), new BaseTransportResponseHandler<StringMessageResponse>() {
                    @Override
                    public StringMessageResponse newInstance() {
                        return new StringMessageResponse();
                    }

                    @Override
                    public String executor() {
                        return ThreadPool.Names.GENERIC;
                    }

                    @Override
                    public void handleResponse(StringMessageResponse response) {
                        fail("got response instead of exception");
                    }

                    @Override
                    public void handleException(TransportException exp) {
                        assertThat(exp.getCause().getMessage(), endsWith("DISCONNECT: simulated"));
                    }
                });

        try {
            res.txGet();
            fail("exception should be thrown");
        } catch (Exception e) {
            assertThat(e.getCause().getMessage(), endsWith("DISCONNECT: simulated"));
        }

        try {
            serviceB.connectToNode(nodeA);
            fail("exception should be thrown");
        } catch (ConnectTransportException e) {
            // all is well
        }

        try {
            serviceB.connectToNodeLight(nodeA);
            fail("exception should be thrown");
        } catch (ConnectTransportException e) {
            // all is well
        }

        serviceA.removeHandler("sayHello");
    }

    @Test
    public void testMockUnresponsiveRule() {
        serviceA.registerRequestHandler("sayHello", StringMessageRequest.class, ThreadPool.Names.GENERIC, new TransportRequestHandler<StringMessageRequest>() {
            @Override
            public void messageReceived(StringMessageRequest request, TransportChannel channel) throws Exception {
                assertThat("moshe", equalTo(request.message));
                throw new RuntimeException("bad message !!!");
            }
        });

        serviceB.addUnresponsiveRule(nodeA);

        TransportFuture<StringMessageResponse> res = serviceB.submitRequest(nodeA, "sayHello",
                new StringMessageRequest("moshe"), TransportRequestOptions.options().withTimeout(100), new BaseTransportResponseHandler<StringMessageResponse>() {
                    @Override
                    public StringMessageResponse newInstance() {
                        return new StringMessageResponse();
                    }

                    @Override
                    public String executor() {
                        return ThreadPool.Names.GENERIC;
                    }

                    @Override
                    public void handleResponse(StringMessageResponse response) {
                        fail("got response instead of exception");
                    }

                    @Override
                    public void handleException(TransportException exp) {
                        assertThat(exp, instanceOf(ReceiveTimeoutTransportException.class));
                    }
                });

        try {
            res.txGet();
            fail("exception should be thrown");
        } catch (Exception e) {
            assertThat(e, instanceOf(ReceiveTimeoutTransportException.class));
        }

        try {
            serviceB.connectToNode(nodeA);
            fail("exception should be thrown");
        } catch (ConnectTransportException e) {
            // all is well
        }

        try {
            serviceB.connectToNodeLight(nodeA);
            fail("exception should be thrown");
        } catch (ConnectTransportException e) {
            // all is well
        }

        serviceA.removeHandler("sayHello");
    }


    @Test
    public void testHostOnMessages() throws InterruptedException {
        final CountDownLatch latch = new CountDownLatch(2);
        final AtomicReference<TransportAddress> addressA = new AtomicReference<>();
        final AtomicReference<TransportAddress> addressB = new AtomicReference<>();
        serviceB.registerRequestHandler("action1", TestRequest.class, ThreadPool.Names.SAME, new TransportRequestHandler<TestRequest>() {
            @Override
            public void messageReceived(TestRequest request, TransportChannel channel) throws Exception {
                addressA.set(request.remoteAddress());
                channel.sendResponse(new TestResponse());
                latch.countDown();
            }
        });
        serviceA.sendRequest(nodeB, "action1", new TestRequest(), new TransportResponseHandler<TestResponse>() {
            @Override
            public TestResponse newInstance() {
                return new TestResponse();
            }

            @Override
            public void handleResponse(TestResponse response) {
                addressB.set(response.remoteAddress());
                latch.countDown();
            }

            @Override
            public void handleException(TransportException exp) {
                latch.countDown();
            }

            @Override
            public String executor() {
                return ThreadPool.Names.SAME;
            }
        });

        if (!latch.await(10, TimeUnit.SECONDS)) {
            fail("message round trip did not complete within a sensible time frame");
        }

        assertTrue(nodeA.address().sameHost(addressA.get()));
        assertTrue(nodeB.address().sameHost(addressB.get()));
    }

    private static class TestRequest extends TransportRequest {
    }

    private static class TestResponse extends TransportResponse {
    }
}


File: core/src/test/java/org/elasticsearch/transport/NettySizeHeaderFrameDecoderTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.transport;

import com.google.common.base.Charsets;
import org.elasticsearch.Version;
import org.elasticsearch.common.network.NetworkService;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.transport.InetSocketTransportAddress;
import org.elasticsearch.common.util.BigArrays;
import org.elasticsearch.indices.breaker.NoneCircuitBreakerService;
import org.elasticsearch.node.settings.NodeSettingsService;
import org.elasticsearch.test.ElasticsearchTestCase;
import org.elasticsearch.test.cache.recycler.MockBigArrays;
import org.elasticsearch.test.cache.recycler.MockPageCacheRecycler;
import org.elasticsearch.threadpool.ThreadPool;
import org.elasticsearch.transport.netty.NettyTransport;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.Socket;

import static org.elasticsearch.common.settings.Settings.settingsBuilder;
import static org.hamcrest.Matchers.is;

/**
 * This test checks, if a HTTP look-alike request (starting with a HTTP method and a space)
 * actually returns text response instead of just dropping the connection
 */
public class NettySizeHeaderFrameDecoderTests extends ElasticsearchTestCase {

    private final Settings settings = settingsBuilder().put("name", "foo").put("transport.host", "127.0.0.1").build();

    private ThreadPool threadPool;
    private NettyTransport nettyTransport;
    private int port;
    private String host;

    @Before
    public void startThreadPool() {
        threadPool = new ThreadPool(settings);
        threadPool.setNodeSettingsService(new NodeSettingsService(settings));
        NetworkService networkService = new NetworkService(settings);
        BigArrays bigArrays = new MockBigArrays(new MockPageCacheRecycler(settings, threadPool), new NoneCircuitBreakerService());
        nettyTransport = new NettyTransport(settings, threadPool, networkService, bigArrays, Version.CURRENT);
        nettyTransport.start();
        TransportService transportService = new TransportService(nettyTransport, threadPool);
        nettyTransport.transportServiceAdapter(transportService.createAdapter());

        InetSocketTransportAddress transportAddress = (InetSocketTransportAddress) nettyTransport.boundAddress().boundAddress();
        port = transportAddress.address().getPort();
        host = transportAddress.address().getHostString();

    }

    @After
    public void terminateThreadPool() throws InterruptedException {
        nettyTransport.stop();
        terminate(threadPool);
    }

    @Test
    public void testThatTextMessageIsReturnedOnHTTPLikeRequest() throws Exception {
        String randomMethod = randomFrom("GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH");
        String data = randomMethod + " / HTTP/1.1";

        try (Socket socket = new Socket(host, port)) {
            socket.getOutputStream().write(data.getBytes(Charsets.UTF_8));
            socket.getOutputStream().flush();

            try (BufferedReader reader = new BufferedReader(new InputStreamReader(socket.getInputStream(), Charsets.UTF_8))) {
                assertThat(reader.readLine(), is("This is not a HTTP port"));
            }
        }
    }

    @Test
    public void testThatNothingIsReturnedForOtherInvalidPackets() throws Exception {
        try (Socket socket = new Socket(host, port)) {
            socket.getOutputStream().write("FOOBAR".getBytes(Charsets.UTF_8));
            socket.getOutputStream().flush();

            // end of stream
            assertThat(socket.getInputStream().read(), is(-1));
        }
    }
}


File: core/src/test/java/org/elasticsearch/transport/local/SimpleLocalTransportTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.transport.local;

import org.elasticsearch.Version;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.test.transport.MockTransportService;
import org.elasticsearch.transport.AbstractSimpleTransportTests;

public class SimpleLocalTransportTests extends AbstractSimpleTransportTests {

    @Override
    protected MockTransportService build(Settings settings, Version version) {
        MockTransportService transportService = new MockTransportService(Settings.EMPTY, new LocalTransport(settings, threadPool, version), threadPool);
        transportService.start();
        return transportService;
    }
}

File: core/src/test/java/org/elasticsearch/transport/netty/NettyScheduledPingTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.elasticsearch.transport.netty;

import com.google.common.collect.ImmutableMap;
import org.elasticsearch.Version;
import org.elasticsearch.cluster.node.DiscoveryNode;
import org.elasticsearch.common.lease.Releasables;
import org.elasticsearch.common.network.NetworkService;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.util.BigArrays;
import org.elasticsearch.test.ElasticsearchTestCase;
import org.elasticsearch.test.transport.MockTransportService;
import org.elasticsearch.threadpool.ThreadPool;
import org.elasticsearch.transport.*;
import org.junit.Test;

import java.io.IOException;

import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.greaterThan;

/**
 */
public class NettyScheduledPingTests extends ElasticsearchTestCase {

    @Test
    public void testScheduledPing() throws Exception {
        ThreadPool threadPool = new ThreadPool(getClass().getName());

        int startPort = 11000 + randomIntBetween(0, 255);
        int endPort = startPort + 10;
        Settings settings = Settings.builder().put(NettyTransport.PING_SCHEDULE, "5ms").put("transport.tcp.port", startPort + "-" + endPort).build();

        final NettyTransport nettyA = new NettyTransport(settings, threadPool, new NetworkService(settings), BigArrays.NON_RECYCLING_INSTANCE, Version.CURRENT);
        MockTransportService serviceA = new MockTransportService(settings, nettyA, threadPool);
        serviceA.start();

        final NettyTransport nettyB = new NettyTransport(settings, threadPool, new NetworkService(settings), BigArrays.NON_RECYCLING_INSTANCE, Version.CURRENT);
        MockTransportService serviceB = new MockTransportService(settings, nettyB, threadPool);
        serviceB.start();

        DiscoveryNode nodeA = new DiscoveryNode("TS_A", "TS_A", serviceA.boundAddress().publishAddress(), ImmutableMap.<String, String>of(), Version.CURRENT);
        DiscoveryNode nodeB = new DiscoveryNode("TS_B", "TS_B", serviceB.boundAddress().publishAddress(), ImmutableMap.<String, String>of(), Version.CURRENT);

        serviceA.connectToNode(nodeB);
        serviceB.connectToNode(nodeA);

        assertBusy(new Runnable() {
            @Override
            public void run() {
                assertThat(nettyA.scheduledPing.successfulPings.count(), greaterThan(100l));
                assertThat(nettyB.scheduledPing.successfulPings.count(), greaterThan(100l));
            }
        });
        assertThat(nettyA.scheduledPing.failedPings.count(), equalTo(0l));
        assertThat(nettyB.scheduledPing.failedPings.count(), equalTo(0l));

        serviceA.registerRequestHandler("sayHello", TransportRequest.Empty.class, ThreadPool.Names.GENERIC, new TransportRequestHandler<TransportRequest.Empty>() {
            @Override
            public void messageReceived(TransportRequest.Empty request, TransportChannel channel) {
                try {
                    channel.sendResponse(TransportResponse.Empty.INSTANCE, TransportResponseOptions.options());
                } catch (IOException e) {
                    e.printStackTrace();
                    assertThat(e.getMessage(), false, equalTo(true));
                }
            }
        });

        // send some messages while ping requests are going around
        int rounds = scaledRandomIntBetween(100, 5000);
        for (int i = 0; i < rounds; i++) {
            serviceB.submitRequest(nodeA, "sayHello",
                    TransportRequest.Empty.INSTANCE, TransportRequestOptions.options().withCompress(randomBoolean()), new BaseTransportResponseHandler<TransportResponse.Empty>() {
                        @Override
                        public TransportResponse.Empty newInstance() {
                            return TransportResponse.Empty.INSTANCE;
                        }

                        @Override
                        public String executor() {
                            return ThreadPool.Names.GENERIC;
                        }

                        @Override
                        public void handleResponse(TransportResponse.Empty response) {
                        }

                        @Override
                        public void handleException(TransportException exp) {
                            exp.printStackTrace();
                            assertThat("got exception instead of a response: " + exp.getMessage(), false, equalTo(true));
                        }
                    }).txGet();
        }

        assertBusy(new Runnable() {
            @Override
            public void run() {
                assertThat(nettyA.scheduledPing.successfulPings.count(), greaterThan(200l));
                assertThat(nettyB.scheduledPing.successfulPings.count(), greaterThan(200l));
            }
        });
        assertThat(nettyA.scheduledPing.failedPings.count(), equalTo(0l));
        assertThat(nettyB.scheduledPing.failedPings.count(), equalTo(0l));

        Releasables.close(serviceA, serviceB);
        terminate(threadPool);
    }
}


File: core/src/test/java/org/elasticsearch/transport/netty/NettyTransportMultiPortTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.elasticsearch.transport.netty;

import com.carrotsearch.hppc.IntHashSet;
import com.google.common.base.Charsets;
import org.elasticsearch.Version;
import org.elasticsearch.cache.recycler.PageCacheRecycler;
import org.elasticsearch.common.component.Lifecycle;
import org.elasticsearch.common.network.NetworkService;
import org.elasticsearch.common.network.NetworkUtils;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.transport.InetSocketTransportAddress;
import org.elasticsearch.common.util.BigArrays;
import org.elasticsearch.indices.breaker.NoneCircuitBreakerService;
import org.elasticsearch.test.ElasticsearchTestCase;
import org.elasticsearch.test.junit.rule.RepeatOnExceptionRule;
import org.elasticsearch.test.cache.recycler.MockBigArrays;
import org.elasticsearch.threadpool.ThreadPool;
import org.elasticsearch.transport.BindTransportException;
import org.elasticsearch.transport.TransportService;
import org.junit.Rule;
import org.junit.Test;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Socket;

import static org.elasticsearch.common.settings.Settings.settingsBuilder;
import static org.hamcrest.Matchers.is;

public class NettyTransportMultiPortTests extends ElasticsearchTestCase {

    private static final int MAX_RETRIES = 10;

    @Rule
    public RepeatOnExceptionRule repeatOnBindExceptionRule = new RepeatOnExceptionRule(logger, MAX_RETRIES, BindTransportException.class);

    @Test
    public void testThatNettyCanBindToMultiplePorts() throws Exception {
        int[] ports = getRandomPorts(3);

        Settings settings = settingsBuilder()
                .put("network.host", "127.0.0.1")
                .put("transport.tcp.port", ports[0])
                .put("transport.profiles.default.port", ports[1])
                .put("transport.profiles.client1.port", ports[2])
                .build();

        ThreadPool threadPool = new ThreadPool("tst");
        try (NettyTransport ignored = startNettyTransport(settings, threadPool)) {
            assertConnectionRefused(ports[0]);
            assertPortIsBound(ports[1]);
            assertPortIsBound(ports[2]);
        } finally {
            terminate(threadPool);
        }
    }

    @Test
    public void testThatDefaultProfileInheritsFromStandardSettings() throws Exception {
        int[] ports = getRandomPorts(2);

        Settings settings = settingsBuilder()
                .put("network.host", "127.0.0.1")
                .put("transport.tcp.port", ports[0])
                .put("transport.profiles.client1.port", ports[1])
                .build();

        ThreadPool threadPool = new ThreadPool("tst");
        try (NettyTransport ignored = startNettyTransport(settings, threadPool)) {
            assertPortIsBound(ports[0]);
            assertPortIsBound(ports[1]);
        } finally {
            terminate(threadPool);
        }
    }

    @Test
    public void testThatProfileWithoutPortSettingsFails() throws Exception {
        int[] ports = getRandomPorts(1);

        Settings settings = settingsBuilder()
                .put("network.host", "127.0.0.1")
                .put("transport.tcp.port", ports[0])
                .put("transport.profiles.client1.whatever", "foo")
                .build();

        ThreadPool threadPool = new ThreadPool("tst");
        try (NettyTransport ignored = startNettyTransport(settings, threadPool)) {
            assertPortIsBound(ports[0]);
        } finally {
            terminate(threadPool);
        }
    }

    @Test
    public void testThatDefaultProfilePortOverridesGeneralConfiguration() throws Exception {
        int[] ports = getRandomPorts(3);

        Settings settings = settingsBuilder()
                .put("network.host", "127.0.0.1")
                .put("transport.tcp.port", ports[0])
                .put("transport.netty.port", ports[1])
                .put("transport.profiles.default.port", ports[2])
                .build();

        ThreadPool threadPool = new ThreadPool("tst");
        try (NettyTransport ignored = startNettyTransport(settings, threadPool)) {
            assertConnectionRefused(ports[0]);
            assertConnectionRefused(ports[1]);
            assertPortIsBound(ports[2]);
        } finally {
            terminate(threadPool);
        }
    }

    @Test
    public void testThatBindingOnDifferentHostsWorks() throws Exception {
        int[] ports = getRandomPorts(2);
        InetAddress firstNonLoopbackAddress = NetworkUtils.getFirstNonLoopbackAddress(NetworkUtils.StackType.IPv4);
        assumeTrue("No IP-v4 non-loopback address available - are you on a plane?", firstNonLoopbackAddress != null);
        Settings settings = settingsBuilder()
                .put("network.host", "127.0.0.1")
                .put("transport.tcp.port", ports[0])
                .put("transport.profiles.default.bind_host", "127.0.0.1")
                .put("transport.profiles.client1.bind_host", firstNonLoopbackAddress.getHostAddress())
                .put("transport.profiles.client1.port", ports[1])
                .build();

        ThreadPool threadPool = new ThreadPool("tst");
        try (NettyTransport ignored = startNettyTransport(settings, threadPool)) {
            assertPortIsBound("127.0.0.1", ports[0]);
            assertPortIsBound(firstNonLoopbackAddress.getHostAddress(), ports[1]);
            assertConnectionRefused(ports[1]);
        } finally {
            terminate(threadPool);
        }
    }

    @Test
    public void testThatProfileWithoutValidNameIsIgnored() throws Exception {
        int[] ports = getRandomPorts(3);

        Settings settings = settingsBuilder()
                .put("network.host", "127.0.0.1")
                .put("transport.tcp.port", ports[0])
                // mimics someone trying to define a profile for .local which is the profile for a node request to itself
                .put("transport.profiles." + TransportService.DIRECT_RESPONSE_PROFILE + ".port", ports[1])
                .put("transport.profiles..port", ports[2])
                .build();

        ThreadPool threadPool = new ThreadPool("tst");
        try (NettyTransport ignored = startNettyTransport(settings, threadPool)) {
            assertPortIsBound(ports[0]);
            assertConnectionRefused(ports[1]);
            assertConnectionRefused(ports[2]);
        } finally {
            terminate(threadPool);
        }
    }

    private int[] getRandomPorts(int numberOfPorts) {
        IntHashSet ports = new IntHashSet();

        for (int i = 0; i < numberOfPorts; i++) {
            int port = randomIntBetween(49152, 65535);
            while (ports.contains(port)) {
                port = randomIntBetween(49152, 65535);
            }
            ports.add(port);
        }

        return ports.toArray();
    }

    private NettyTransport startNettyTransport(Settings settings, ThreadPool threadPool) {
        BigArrays bigArrays = new MockBigArrays(new PageCacheRecycler(settings, threadPool), new NoneCircuitBreakerService());

        NettyTransport nettyTransport = new NettyTransport(settings, threadPool, new NetworkService(settings), bigArrays, Version.CURRENT);
        nettyTransport.start();

        assertThat(nettyTransport.lifecycleState(), is(Lifecycle.State.STARTED));
        return nettyTransport;
    }

    private void assertConnectionRefused(int port) throws Exception {
        try {
            trySocketConnection(new InetSocketTransportAddress("localhost", port).address());
            fail("Expected to get exception when connecting to port " + port);
        } catch (IOException e) {
            // expected
            logger.info("Got expected connection message {}", e.getMessage());
        }
    }

    private void assertPortIsBound(int port) throws Exception {
        assertPortIsBound("localhost", port);
    }

    private void assertPortIsBound(String host, int port) throws Exception {
        logger.info("Trying to connect to [{}]:[{}]", host, port);
        trySocketConnection(new InetSocketTransportAddress(host, port).address());
    }

    private void trySocketConnection(InetSocketAddress address) throws Exception {
        try (Socket socket = new Socket()) {
            logger.info("Connecting to {}", address);
            socket.connect(address, 500);

            assertThat(socket.isConnected(), is(true));
            try (OutputStream os = socket.getOutputStream()) {
                os.write("foo".getBytes(Charsets.UTF_8));
                os.flush();
            }
        }
    }
}


File: core/src/test/java/org/elasticsearch/transport/netty/NettyTransportTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.elasticsearch.transport.netty;

import org.elasticsearch.ElasticsearchException;
import org.elasticsearch.Version;
import org.elasticsearch.action.admin.cluster.health.ClusterHealthResponse;
import org.elasticsearch.action.admin.cluster.health.ClusterHealthStatus;
import org.elasticsearch.client.Client;
import org.elasticsearch.common.component.Lifecycle;
import org.elasticsearch.common.inject.Inject;
import org.elasticsearch.common.io.stream.StreamInput;
import org.elasticsearch.common.logging.ESLogger;
import org.elasticsearch.common.network.NetworkService;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.transport.InetSocketTransportAddress;
import org.elasticsearch.common.util.BigArrays;
import org.elasticsearch.common.util.concurrent.AbstractRunnable;
import org.elasticsearch.test.ElasticsearchIntegrationTest;
import org.elasticsearch.threadpool.ThreadPool;
import org.elasticsearch.transport.*;
import org.jboss.netty.channel.Channel;
import org.jboss.netty.channel.ChannelPipeline;
import org.jboss.netty.channel.ChannelPipelineFactory;
import org.junit.Test;

import java.io.IOException;
import java.net.InetSocketAddress;

import static org.elasticsearch.common.settings.Settings.settingsBuilder;
import static org.elasticsearch.test.ElasticsearchIntegrationTest.ClusterScope;
import static org.elasticsearch.test.ElasticsearchIntegrationTest.Scope;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.is;

/**
 *
 */
@ClusterScope(scope = Scope.TEST, numDataNodes = 1)
public class NettyTransportTests extends ElasticsearchIntegrationTest {

    // static so we can use it in anonymous classes
    private static String channelProfileName = null;

    @Override
    protected Settings nodeSettings(int nodeOrdinal) {
        return settingsBuilder().put(super.nodeSettings(nodeOrdinal))
                .put("node.mode", "network")
                .put(TransportModule.TRANSPORT_TYPE_KEY, ExceptionThrowingNettyTransport.class.getName()).build();
    }

    @Test
    public void testThatConnectionFailsAsIntended() throws Exception {
        Client transportClient = internalCluster().transportClient();
        ClusterHealthResponse clusterIndexHealths = transportClient.admin().cluster().prepareHealth().get();
        assertThat(clusterIndexHealths.getStatus(), is(ClusterHealthStatus.GREEN));

        try {
            transportClient.admin().cluster().prepareHealth().putHeader("ERROR", "MY MESSAGE").get();
            fail("Expected exception, but didnt happen");
        } catch (ElasticsearchException e) {
            assertThat(e.getMessage(), containsString("MY MESSAGE"));
            assertThat(channelProfileName, is(NettyTransport.DEFAULT_PROFILE));
        }
    }

    public static final class ExceptionThrowingNettyTransport extends NettyTransport {

        @Inject
        public ExceptionThrowingNettyTransport(Settings settings, ThreadPool threadPool, NetworkService networkService, BigArrays bigArrays, Version version) {
            super(settings, threadPool, networkService, bigArrays, version);
        }

        @Override
        public ChannelPipelineFactory configureServerChannelPipelineFactory(String name, Settings groupSettings) {
            return new ErrorPipelineFactory(this, name, groupSettings);
        }

        private static class ErrorPipelineFactory extends ServerChannelPipelineFactory {

            private final ESLogger logger;

            public ErrorPipelineFactory(ExceptionThrowingNettyTransport exceptionThrowingNettyTransport, String name, Settings groupSettings) {
                super(exceptionThrowingNettyTransport, name, groupSettings);
                this.logger = exceptionThrowingNettyTransport.logger;
            }

            @Override
            public ChannelPipeline getPipeline() throws Exception {
                ChannelPipeline pipeline = super.getPipeline();
                pipeline.replace("dispatcher", "dispatcher", new MessageChannelHandler(nettyTransport, logger, NettyTransport.DEFAULT_PROFILE) {

                    @Override
                    protected String handleRequest(Channel channel, StreamInput buffer, long requestId, Version version) throws IOException {
                        final String action = buffer.readString();

                        final NettyTransportChannel transportChannel = new NettyTransportChannel(transport, transportServiceAdapter, action, channel, requestId, version, name);
                        try {
                            final RequestHandlerRegistry reg = transportServiceAdapter.getRequestHandler(action);
                            if (reg == null) {
                                throw new ActionNotFoundTransportException(action);
                            }
                            final TransportRequest request = reg.newRequest();
                            request.remoteAddress(new InetSocketTransportAddress((InetSocketAddress) channel.getRemoteAddress()));
                            request.readFrom(buffer);
                            if (request.hasHeader("ERROR")) {
                                throw new ElasticsearchException((String) request.getHeader("ERROR"));
                            }
                            if (reg.getExecutor() == ThreadPool.Names.SAME) {
                                //noinspection unchecked
                                reg.getHandler().messageReceived(request, transportChannel);
                            } else {
                                threadPool.executor(reg.getExecutor()).execute(new RequestHandler(reg, request, transportChannel));
                            }
                        } catch (Throwable e) {
                            try {
                                transportChannel.sendResponse(e);
                            } catch (IOException e1) {
                                logger.warn("Failed to send error message back to client for action [" + action + "]", e);
                                logger.warn("Actual Exception", e1);
                            }
                        }
                        channelProfileName = transportChannel.getProfileName();
                        return action;
                    }

                    class RequestHandler extends AbstractRunnable {
                        private final RequestHandlerRegistry reg;
                        private final TransportRequest request;
                        private final NettyTransportChannel transportChannel;

                        public RequestHandler(RequestHandlerRegistry reg, TransportRequest request, NettyTransportChannel transportChannel) {
                            this.reg = reg;
                            this.request = request;
                            this.transportChannel = transportChannel;
                        }

                        @SuppressWarnings({"unchecked"})
                        @Override
                        protected void doRun() throws Exception {
                            reg.getHandler().messageReceived(request, transportChannel);
                        }

                        @Override
                        public boolean isForceExecution() {
                            return reg.isForceExecution();
                        }

                        @Override
                        public void onFailure(Throwable e) {
                            if (transport.lifecycleState() == Lifecycle.State.STARTED) {
                                // we can only send a response transport is started....
                                try {
                                    transportChannel.sendResponse(e);
                                } catch (Throwable e1) {
                                    logger.warn("Failed to send error message back to client for action [" + reg.getAction() + "]", e1);
                                    logger.warn("Actual Exception", e);
                                }
                            }                        }
                    }
                });
                return pipeline;
            }
        }
    }
}


File: core/src/test/java/org/elasticsearch/transport/netty/SimpleNettyTransportTests.java
/*
 * Licensed to Elasticsearch under one or more contributor
 * license agreements. See the NOTICE file distributed with
 * this work for additional information regarding copyright
 * ownership. Elasticsearch licenses this file to you under
 * the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.transport.netty;

import org.apache.lucene.util.LuceneTestCase.Slow;
import org.elasticsearch.Version;
import org.elasticsearch.cluster.node.DiscoveryNode;
import org.elasticsearch.common.network.NetworkService;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.transport.InetSocketTransportAddress;
import org.elasticsearch.common.util.BigArrays;
import org.elasticsearch.test.transport.MockTransportService;
import org.elasticsearch.transport.AbstractSimpleTransportTests;
import org.elasticsearch.transport.ConnectTransportException;
import org.junit.Test;

@Slow
public class SimpleNettyTransportTests extends AbstractSimpleTransportTests {

    @Override
    protected MockTransportService build(Settings settings, Version version) {
        int startPort = 11000 + randomIntBetween(0, 255);
        int endPort = startPort + 10;
        settings = Settings.builder().put(settings).put("transport.tcp.port", startPort + "-" + endPort).build();
        MockTransportService transportService = new MockTransportService(settings, new NettyTransport(settings, threadPool, new NetworkService(settings), BigArrays.NON_RECYCLING_INSTANCE, version), threadPool);
        transportService.start();
        return transportService;
    }

    @Test(expected = ConnectTransportException.class)
    public void testConnectException() {
        serviceA.connectToNode(new DiscoveryNode("C", new InetSocketTransportAddress("localhost", 9876), Version.CURRENT));
    }
}