Refactoring Types: ['Move Attribute']
j/core/AlertMessage.java
/*
 * Copyright 2011 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.core;

import java.util.Date;
import java.util.HashSet;
import java.util.Set;

/**
 * Alerts are signed messages that are broadcast on the peer-to-peer network if they match a hard-coded signing key.
 * The private keys are held by a small group of core Bitcoin developers, and alerts may be broadcast in the event of
 * an available upgrade or a serious network problem. Alerts have an expiration time, data that specifies what
 * set of software versions it matches and the ability to cancel them by broadcasting another type of alert.<p>
 *
 * The right course of action on receiving an alert is usually to either ensure a human will see it (display on screen,
 * log, email), or if you decide to use alerts for notifications that are specific to your app in some way, to parse it.
 * For example, you could treat it as an upgrade notification specific to your app. Satoshi designed alerts to ensure
 * that software upgrades could be distributed independently of a hard-coded website, in order to allow everything to
 * be purely peer-to-peer. You don't have to use this of course, and indeed it often makes more sense not to.<p>
 *     
 * Before doing anything with an alert, you should check {@link AlertMessage#isSignatureValid()}.
 */
public class AlertMessage extends Message {
    private byte[] content;
    private byte[] signature;

    // See the getters for documentation of what each field means.
    private long version = 1;
    private Date relayUntil;
    private Date expiration;
    private long id;
    private long cancel;
    private Set<Long> cancelSet;
    private long minVer, maxVer;
    private Set<String> matchingSubVers;
    private long priority;
    private String comment, statusBar, reserved;

    // Chosen arbitrarily to avoid memory blowups.
    private static final long MAX_SET_SIZE = 100;

    public AlertMessage(NetworkParameters params, byte[] payloadBytes) throws ProtocolException {
        super(params, payloadBytes, 0);
    }

    @Override
    public String toString() {
        return "ALERT: " + getStatusBar();
    }

    @Override
    void parse() throws ProtocolException {
        // Alerts are formatted in two levels. The top level contains two byte arrays: a signature, and a serialized
        // data structure containing the actual alert data.
        int startPos = cursor;
        content = readByteArray();
        signature = readByteArray();
        // Now we need to parse out the contents of the embedded structure. Rewind back to the start of the message.
        cursor = startPos;
        readVarInt();  // Skip the length field on the content array.
        // We're inside the embedded structure.
        version = readUint32();
        // Read the timestamps. Bitcoin uses seconds since the epoch.
        relayUntil = new Date(readUint64().longValue() * 1000);
        expiration = new Date(readUint64().longValue() * 1000);
        id = readUint32();
        cancel = readUint32();
        // Sets are serialized as <len><item><item><item>....
        long cancelSetSize = readVarInt();
        if (cancelSetSize < 0 || cancelSetSize > MAX_SET_SIZE) {
            throw new ProtocolException("Bad cancel set size: " + cancelSetSize);
        }
        // Using a hashset here is very inefficient given that this will normally be only one item. But Java doesn't
        // make it easy to do better. What we really want is just an array-backed set.
        cancelSet = new HashSet<Long>((int)cancelSetSize);
        for (long i = 0; i < cancelSetSize; i++) {
            cancelSet.add(readUint32());
        }
        minVer = readUint32();
        maxVer = readUint32();
        // Read the subver matching set.
        long subverSetSize = readVarInt();
        if (subverSetSize < 0 || subverSetSize > MAX_SET_SIZE) {
            throw new ProtocolException("Bad subver set size: " + subverSetSize);
        }
        matchingSubVers = new HashSet<String>((int)subverSetSize);
        for (long i = 0; i < subverSetSize; i++) {
            matchingSubVers.add(readStr());
        }
        priority = readUint32();
        comment = readStr();
        statusBar = readStr();
        reserved = readStr();

        length = cursor - offset;
    }

    /**
     * Returns true if the digital signature attached to the message verifies. Don't do anything with the alert if it
     * doesn't verify, because that would allow arbitrary attackers to spam your users.
     */
    public boolean isSignatureValid() {
        return ECKey.verify(Utils.doubleDigest(content), signature, params.getAlertSigningKey());
    }

    @Override
    protected void parseLite() throws ProtocolException {
        // Do nothing, lazy parsing isn't useful for alerts.
    }

    /////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    //  Field accessors.

    /**
     * The time at which the alert should stop being broadcast across the network. Note that you can still receive
     * the alert after this time from other nodes if the alert still applies to them or to you.
     */
    public Date getRelayUntil() {
        return relayUntil;
    }

    public void setRelayUntil(Date relayUntil) {
        this.relayUntil = relayUntil;
    }

    /**
     * The time at which the alert ceases to be relevant. It should not be presented to the user or app administrator
     * after this time.
     */
    public Date getExpiration() {
        return expiration;
    }

    public void setExpiration(Date expiration) {
        this.expiration = expiration;
    }

    /**
     * The numeric identifier of this alert. Each alert should have a unique ID, but the signer can choose any number.
     * If an alert is broadcast with a cancel field higher than this ID, this alert is considered cancelled.
     * @return uint32
     */
    public long getId() {
        return id;
    }

    public void setId(long id) {
        this.id = id;
    }

    /**
     * A marker that results in any alerts with an ID lower than this value to be considered cancelled.
     * @return uint32
     */
    public long getCancel() {
        return cancel;
    }

    public void setCancel(long cancel) {
        this.cancel = cancel;
    }

    /**
     * The inclusive lower bound on software versions that are considered for the purposes of this alert. The Satoshi
     * client compares this against a protocol version field, but as long as the subVer field is used to restrict it your
     * alerts could use any version numbers.
     * @return uint32
     */
    public long getMinVer() {
        return minVer;
    }

    public void setMinVer(long minVer) {
        this.minVer = minVer;
    }

    /**
     * The inclusive upper bound on software versions considered for the purposes of this alert. The Satoshi
     * client compares this against a protocol version field, but as long as the subVer field is used to restrict it your
     * alerts could use any version numbers.
     * @return
     */
    public long getMaxVer() {
        return maxVer;
    }

    public void setMaxVer(long maxVer) {
        this.maxVer = maxVer;
    }

    /**
     * Provides an integer ordering amongst simultaneously active alerts.
     * @return uint32
     */
    public long getPriority() {
        return priority;
    }

    public void setPriority(long priority) {
        this.priority = priority;
    }

    /**
     * This field is unused. It is presumably intended for the author of the alert to provide a justification for it
     * visible to protocol developers but not users.
     */
    public String getComment() {
        return comment;
    }

    public void setComment(String comment) {
        this.comment = comment;
    }

    /**
     * A string that is intended to display in the status bar of the official GUI client. It contains the user-visible
     * message. English only.
     */
    public String getStatusBar() {
        return statusBar;
    }

    public void setStatusBar(String statusBar) {
        this.statusBar = statusBar;
    }

    /**
     * This field is never used.
     */
    public String getReserved() {
        return reserved;
    }

    public void setReserved(String reserved) {
        this.reserved = reserved;
    }
    
    public long getVersion() {
        return version;
    }
}


File: core/src/main/java/org/bitcoinj/core/Base58.java
/**
 * Copyright 2011 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.core;

import java.io.UnsupportedEncodingException;
import java.math.BigInteger;
import java.util.Arrays;

/**
 * <p>Base58 is a way to encode Bitcoin addresses as numbers and letters. Note that this is not the same base58 as used by
 * Flickr, which you may see reference to around the internet.</p>
 *
 * <p>You may instead wish to work with {@link VersionedChecksummedBytes}, which adds support for testing the prefix
 * and suffix bytes commonly found in addresses.</p>
 *
 * <p>Satoshi says: why base-58 instead of standard base-64 encoding?<p>
 *
 * <ul>
 * <li>Don't want 0OIl characters that look the same in some fonts and
 *     could be used to create visually identical looking account numbers.</li>
 * <li>A string with non-alphanumeric characters is not as easily accepted as an account number.</li>
 * <li>E-mail usually won't line-break if there's no punctuation to break at.</li>
 * <li>Doubleclicking selects the whole number as one word if it's all alphanumeric.</li>
 * </ul>
 */
public class Base58 {
    public static final char[] ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz".toCharArray();

    private static final int[] INDEXES = new int[128];
    static {
        for (int i = 0; i < INDEXES.length; i++) {
            INDEXES[i] = -1;
        }
        for (int i = 0; i < ALPHABET.length; i++) {
            INDEXES[ALPHABET[i]] = i;
        }
    }

    /** Encodes the given bytes in base58. No checksum is appended. */
    public static String encode(byte[] input) {
        if (input.length == 0) {
            return "";
        }       
        input = copyOfRange(input, 0, input.length);
        // Count leading zeroes.
        int zeroCount = 0;
        while (zeroCount < input.length && input[zeroCount] == 0) {
            ++zeroCount;
        }
        // The actual encoding.
        byte[] temp = new byte[input.length * 2];
        int j = temp.length;

        int startAt = zeroCount;
        while (startAt < input.length) {
            byte mod = divmod58(input, startAt);
            if (input[startAt] == 0) {
                ++startAt;
            }
            temp[--j] = (byte) ALPHABET[mod];
        }

        // Strip extra '1' if there are some after decoding.
        while (j < temp.length && temp[j] == ALPHABET[0]) {
            ++j;
        }
        // Add as many leading '1' as there were leading zeros.
        while (--zeroCount >= 0) {
            temp[--j] = (byte) ALPHABET[0];
        }

        byte[] output = copyOfRange(temp, j, temp.length);
        try {
            return new String(output, "US-ASCII");
        } catch (UnsupportedEncodingException e) {
            throw new RuntimeException(e);  // Cannot happen.
        }
    }

    public static byte[] decode(String input) throws AddressFormatException {
        if (input.length() == 0) {
            return new byte[0];
        }
        byte[] input58 = new byte[input.length()];
        // Transform the String to a base58 byte sequence
        for (int i = 0; i < input.length(); ++i) {
            char c = input.charAt(i);

            int digit58 = -1;
            if (c >= 0 && c < 128) {
                digit58 = INDEXES[c];
            }
            if (digit58 < 0) {
                throw new AddressFormatException("Illegal character " + c + " at " + i);
            }

            input58[i] = (byte) digit58;
        }
        // Count leading zeroes
        int zeroCount = 0;
        while (zeroCount < input58.length && input58[zeroCount] == 0) {
            ++zeroCount;
        }
        // The encoding
        byte[] temp = new byte[input.length()];
        int j = temp.length;

        int startAt = zeroCount;
        while (startAt < input58.length) {
            byte mod = divmod256(input58, startAt);
            if (input58[startAt] == 0) {
                ++startAt;
            }

            temp[--j] = mod;
        }
        // Do no add extra leading zeroes, move j to first non null byte.
        while (j < temp.length && temp[j] == 0) {
            ++j;
        }

        return copyOfRange(temp, j - zeroCount, temp.length);
    }
    
    public static BigInteger decodeToBigInteger(String input) throws AddressFormatException {
        return new BigInteger(1, decode(input));
    }

    /**
     * Uses the checksum in the last 4 bytes of the decoded data to verify the rest are correct. The checksum is
     * removed from the returned data.
     *
     * @throws AddressFormatException if the input is not base 58 or the checksum does not validate.
     */
    public static byte[] decodeChecked(String input) throws AddressFormatException {
        byte tmp [] = decode(input);
        if (tmp.length < 4)
            throw new AddressFormatException("Input too short");
        byte[] bytes = copyOfRange(tmp, 0, tmp.length - 4);
        byte[] checksum = copyOfRange(tmp, tmp.length - 4, tmp.length);
        
        tmp = Utils.doubleDigest(bytes);
        byte[] hash = copyOfRange(tmp, 0, 4);
        if (!Arrays.equals(checksum, hash)) 
            throw new AddressFormatException("Checksum does not validate");
        
        return bytes;
    }
    
    //
    // number -> number / 58, returns number % 58
    //
    private static byte divmod58(byte[] number, int startAt) {
        int remainder = 0;
        for (int i = startAt; i < number.length; i++) {
            int digit256 = (int) number[i] & 0xFF;
            int temp = remainder * 256 + digit256;

            number[i] = (byte) (temp / 58);

            remainder = temp % 58;
        }

        return (byte) remainder;
    }

    //
    // number -> number / 256, returns number % 256
    //
    private static byte divmod256(byte[] number58, int startAt) {
        int remainder = 0;
        for (int i = startAt; i < number58.length; i++) {
            int digit58 = (int) number58[i] & 0xFF;
            int temp = remainder * 58 + digit58;

            number58[i] = (byte) (temp / 256);

            remainder = temp % 256;
        }

        return (byte) remainder;
    }

    private static byte[] copyOfRange(byte[] source, int from, int to) {
        byte[] range = new byte[to - from];
        System.arraycopy(source, from, range, 0, range.length);

        return range;
    }
}


File: core/src/main/java/org/bitcoinj/core/BitcoinSerializer.java
/**
 * Copyright 2011 Google Inc.
 * Copyright 2014 Andreas Schildbach
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.core;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.OutputStream;
import java.io.UnsupportedEncodingException;
import java.nio.BufferUnderflowException;
import java.nio.ByteBuffer;
import java.util.HashMap;
import java.util.Map;

import static org.bitcoinj.core.Utils.*;

/**
 * <p>Methods to serialize and de-serialize messages to the Bitcoin network format as defined in
 * <a href="https://en.bitcoin.it/wiki/Protocol_specification">the protocol specification</a>.</p>
 *
 * <p>To be able to serialize and deserialize new Message subclasses the following criteria needs to be met.</p>
 *
 * <ul>
 * <li>The proper Class instance needs to be mapped to its message name in the names variable below</li>
 * <li>There needs to be a constructor matching: NetworkParameters params, byte[] payload</li>
 * <li>Message.bitcoinSerializeToStream() needs to be properly subclassed</li>
 * </ul>
 */
public class BitcoinSerializer {
    private static final Logger log = LoggerFactory.getLogger(BitcoinSerializer.class);
    private static final int COMMAND_LEN = 12;

    private NetworkParameters params;
    private boolean parseLazy = false;
    private boolean parseRetain = false;

    private static Map<Class<? extends Message>, String> names = new HashMap<Class<? extends Message>, String>();

    static {
        names.put(VersionMessage.class, "version");
        names.put(InventoryMessage.class, "inv");
        names.put(Block.class, "block");
        names.put(GetDataMessage.class, "getdata");
        names.put(Transaction.class, "tx");
        names.put(AddressMessage.class, "addr");
        names.put(Ping.class, "ping");
        names.put(Pong.class, "pong");
        names.put(VersionAck.class, "verack");
        names.put(GetBlocksMessage.class, "getblocks");
        names.put(GetHeadersMessage.class, "getheaders");
        names.put(GetAddrMessage.class, "getaddr");
        names.put(HeadersMessage.class, "headers");
        names.put(BloomFilter.class, "filterload");
        names.put(FilteredBlock.class, "merkleblock");
        names.put(NotFoundMessage.class, "notfound");
        names.put(MemoryPoolMessage.class, "mempool");
        names.put(RejectMessage.class, "reject");
        names.put(GetUTXOsMessage.class, "getutxos");
        names.put(UTXOsMessage.class, "utxos");
    }

    /**
     * Constructs a BitcoinSerializer with the given behavior.
     *
     * @param params           networkParams used to create Messages instances and termining packetMagic
     */
    public BitcoinSerializer(NetworkParameters params) {
        this(params, false, false);
    }

    /**
     * Constructs a BitcoinSerializer with the given behavior.
     *
     * @param params           networkParams used to create Messages instances and termining packetMagic
     * @param parseLazy        deserialize messages in lazy mode.
     * @param parseRetain      retain the backing byte array of a message for fast reserialization.
     */
    public BitcoinSerializer(NetworkParameters params, boolean parseLazy, boolean parseRetain) {
        this.params = params;
        this.parseLazy = parseLazy;
        this.parseRetain = parseRetain;
    }

    /**
     * Writes message to to the output stream.
     */
    public void serialize(String name, byte[] message, OutputStream out) throws IOException {
        byte[] header = new byte[4 + COMMAND_LEN + 4 + 4 /* checksum */];
        uint32ToByteArrayBE(params.getPacketMagic(), header, 0);

        // The header array is initialized to zero by Java so we don't have to worry about
        // NULL terminating the string here.
        for (int i = 0; i < name.length() && i < COMMAND_LEN; i++) {
            header[4 + i] = (byte) (name.codePointAt(i) & 0xFF);
        }

        Utils.uint32ToByteArrayLE(message.length, header, 4 + COMMAND_LEN);

        byte[] hash = doubleDigest(message);
        System.arraycopy(hash, 0, header, 4 + COMMAND_LEN + 4, 4);
        out.write(header);
        out.write(message);

        if (log.isDebugEnabled())
            log.debug("Sending {} message: {}", name, HEX.encode(header) + HEX.encode(message));
    }

    /**
     * Writes message to to the output stream.
     */
    public void serialize(Message message, OutputStream out) throws IOException {
        String name = names.get(message.getClass());
        if (name == null) {
            throw new Error("BitcoinSerializer doesn't currently know how to serialize " + message.getClass());
        }
        serialize(name, message.bitcoinSerialize(), out);
    }

    /**
     * Reads a message from the given ByteBuffer and returns it.
     */
    public Message deserialize(ByteBuffer in) throws ProtocolException, IOException {
        // A Bitcoin protocol message has the following format.
        //
        //   - 4 byte magic number: 0xfabfb5da for the testnet or
        //                          0xf9beb4d9 for production
        //   - 12 byte command in ASCII
        //   - 4 byte payload size
        //   - 4 byte checksum
        //   - Payload data
        //
        // The checksum is the first 4 bytes of a SHA256 hash of the message payload. It isn't
        // present for all messages, notably, the first one on a connection.
        //
        // Satoshi's implementation ignores garbage before the magic header bytes. We have to do the same because
        // sometimes it sends us stuff that isn't part of any message.
        seekPastMagicBytes(in);
        BitcoinPacketHeader header = new BitcoinPacketHeader(in);
        // Now try to read the whole message.
        return deserializePayload(header, in);
    }

    /**
     * Deserializes only the header in case packet meta data is needed before decoding
     * the payload. This method assumes you have already called seekPastMagicBytes()
     */
    public BitcoinPacketHeader deserializeHeader(ByteBuffer in) throws ProtocolException, IOException {
        return new BitcoinPacketHeader(in);
    }

    /**
     * Deserialize payload only.  You must provide a header, typically obtained by calling
     * {@link BitcoinSerializer#deserializeHeader}.
     */
    public Message deserializePayload(BitcoinPacketHeader header, ByteBuffer in) throws ProtocolException, BufferUnderflowException {
        byte[] payloadBytes = new byte[header.size];
        in.get(payloadBytes, 0, header.size);

        // Verify the checksum.
        byte[] hash;
        hash = doubleDigest(payloadBytes);
        if (header.checksum[0] != hash[0] || header.checksum[1] != hash[1] ||
                header.checksum[2] != hash[2] || header.checksum[3] != hash[3]) {
            throw new ProtocolException("Checksum failed to verify, actual " +
                    HEX.encode(hash) +
                    " vs " + HEX.encode(header.checksum));
        }

        if (log.isDebugEnabled()) {
            log.debug("Received {} byte '{}' message: {}", header.size, header.command,
                    HEX.encode(payloadBytes));
        }

        try {
            return makeMessage(header.command, header.size, payloadBytes, hash, header.checksum);
        } catch (Exception e) {
            throw new ProtocolException("Error deserializing message " + HEX.encode(payloadBytes) + "\n", e);
        }
    }

    private Message makeMessage(String command, int length, byte[] payloadBytes, byte[] hash, byte[] checksum) throws ProtocolException {
        // We use an if ladder rather than reflection because reflection is very slow on Android.
        Message message;
        if (command.equals("version")) {
            return new VersionMessage(params, payloadBytes);
        } else if (command.equals("inv")) {
            message = new InventoryMessage(params, payloadBytes, parseLazy, parseRetain, length);
        } else if (command.equals("block")) {
            message = new Block(params, payloadBytes, parseLazy, parseRetain, length);
        } else if (command.equals("merkleblock")) {
            message = new FilteredBlock(params, payloadBytes);
        } else if (command.equals("getdata")) {
            message = new GetDataMessage(params, payloadBytes, parseLazy, parseRetain, length);
        } else if (command.equals("getblocks")) {
            message = new GetBlocksMessage(params, payloadBytes);
        } else if (command.equals("getheaders")) {
            message = new GetHeadersMessage(params, payloadBytes);
        } else if (command.equals("tx")) {
            Transaction tx = new Transaction(params, payloadBytes, null, parseLazy, parseRetain, length);
            if (hash != null)
                tx.setHash(new Sha256Hash(Utils.reverseBytes(hash)));
            message = tx;
        } else if (command.equals("addr")) {
            message = new AddressMessage(params, payloadBytes, parseLazy, parseRetain, length);
        } else if (command.equals("ping")) {
            message = new Ping(params, payloadBytes);
        } else if (command.equals("pong")) {
            message = new Pong(params, payloadBytes);
        } else if (command.equals("verack")) {
            return new VersionAck(params, payloadBytes);
        } else if (command.equals("headers")) {
            return new HeadersMessage(params, payloadBytes);
        } else if (command.equals("alert")) {
            return new AlertMessage(params, payloadBytes);
        } else if (command.equals("filterload")) {
            return new BloomFilter(params, payloadBytes);
        } else if (command.equals("notfound")) {
            return new NotFoundMessage(params, payloadBytes);
        } else if (command.equals("mempool")) {
            return new MemoryPoolMessage();
        } else if (command.equals("reject")) {
            return new RejectMessage(params, payloadBytes);
        } else if (command.equals("utxos")) {
            return new UTXOsMessage(params, payloadBytes);
        } else if (command.equals("getutxos")) {
            return new GetUTXOsMessage(params, payloadBytes);
        } else {
            log.warn("No support for deserializing message with name {}", command);
            return new UnknownMessage(params, command, payloadBytes);
        }
        if (checksum != null)
            message.setChecksum(checksum);
        return message;
    }

    public void seekPastMagicBytes(ByteBuffer in) throws BufferUnderflowException {
        int magicCursor = 3;  // Which byte of the magic we're looking for currently.
        while (true) {
            byte b = in.get();
            // We're looking for a run of bytes that is the same as the packet magic but we want to ignore partial
            // magics that aren't complete. So we keep track of where we're up to with magicCursor.
            byte expectedByte = (byte)(0xFF & params.getPacketMagic() >>> (magicCursor * 8));
            if (b == expectedByte) {
                magicCursor--;
                if (magicCursor < 0) {
                    // We found the magic sequence.
                    return;
                } else {
                    // We still have further to go to find the next message.
                }
            } else {
                magicCursor = 3;
            }
        }
    }

    /**
     * Whether the serializer will produce lazy parse mode Messages
     */
    public boolean isParseLazyMode() {
        return parseLazy;
    }

    /**
     * Whether the serializer will produce cached mode Messages
     */
    public boolean isParseRetainMode() {
        return parseRetain;
    }


    public static class BitcoinPacketHeader {
        /** The largest number of bytes that a header can represent */
        public static final int HEADER_LENGTH = COMMAND_LEN + 4 + 4;

        public final byte[] header;
        public final String command;
        public final int size;
        public final byte[] checksum;

        public BitcoinPacketHeader(ByteBuffer in) throws ProtocolException, BufferUnderflowException {
            header = new byte[HEADER_LENGTH];
            in.get(header, 0, header.length);

            int cursor = 0;

            // The command is a NULL terminated string, unless the command fills all twelve bytes
            // in which case the termination is implicit.
            for (; header[cursor] != 0 && cursor < COMMAND_LEN; cursor++) ;
            byte[] commandBytes = new byte[cursor];
            System.arraycopy(header, 0, commandBytes, 0, cursor);
            try {
                command = new String(commandBytes, "US-ASCII");
            } catch (UnsupportedEncodingException e) {
                throw new RuntimeException(e);  // Cannot happen.
            }
            cursor = COMMAND_LEN;

            size = (int) readUint32(header, cursor);
            cursor += 4;

            if (size > Message.MAX_SIZE)
                throw new ProtocolException("Message size too large: " + size);

            // Old clients don't send the checksum.
            checksum = new byte[4];
            // Note that the size read above includes the checksum bytes.
            System.arraycopy(header, cursor, checksum, 0, 4);
            cursor += 4;
        }
    }
}


File: core/src/main/java/org/bitcoinj/core/Block.java
/**
 * Copyright 2011 Google Inc.
 * Copyright 2014 Andreas Schildbach
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.core;

import org.bitcoinj.script.Script;
import org.bitcoinj.script.ScriptBuilder;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Preconditions;
import com.google.common.collect.ImmutableList;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.annotation.Nullable;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.OutputStream;
import java.math.BigInteger;
import java.util.ArrayList;
import java.util.Date;
import java.util.LinkedList;
import java.util.List;

import static org.bitcoinj.core.Coin.FIFTY_COINS;
import static org.bitcoinj.core.Utils.doubleDigest;
import static org.bitcoinj.core.Utils.doubleDigestTwoBuffers;

/**
 * <p>A block is a group of transactions, and is one of the fundamental data structures of the Bitcoin system.
 * It records a set of {@link Transaction}s together with some data that links it into a place in the global block
 * chain, and proves that a difficult calculation was done over its contents. See
 * <a href="http://www.bitcoin.org/bitcoin.pdf">the Bitcoin technical paper</a> for
 * more detail on blocks. <p/>
 *
 * To get a block, you can either build one from the raw bytes you can get from another implementation, or request one
 * specifically using {@link Peer#getBlock(Sha256Hash)}, or grab one from a downloaded {@link BlockChain}.
 */
public class Block extends Message {
    private static final Logger log = LoggerFactory.getLogger(Block.class);
    private static final long serialVersionUID = 2738848929966035281L;

    /** How many bytes are required to represent a block header WITHOUT the trailing 00 length byte. */
    public static final int HEADER_SIZE = 80;

    static final long ALLOWED_TIME_DRIFT = 2 * 60 * 60; // Same value as official client.

    /**
     * A constant shared by the entire network: how large in bytes a block is allowed to be. One day we may have to
     * upgrade everyone to change this, so Bitcoin can continue to grow. For now it exists as an anti-DoS measure to
     * avoid somebody creating a titanically huge but valid block and forcing everyone to download/store it forever.
     */
    public static final int MAX_BLOCK_SIZE = 1 * 1000 * 1000;
    /**
     * A "sigop" is a signature verification operation. Because they're expensive we also impose a separate limit on
     * the number in a block to prevent somebody mining a huge block that has way more sigops than normal, so is very
     * expensive/slow to verify.
     */
    public static final int MAX_BLOCK_SIGOPS = MAX_BLOCK_SIZE / 50;

    /** A value for difficultyTarget (nBits) that allows half of all possible hash solutions. Used in unit testing. */
    public static final long EASIEST_DIFFICULTY_TARGET = 0x207fFFFFL;

    // Fields defined as part of the protocol format.
    private long version;
    private Sha256Hash prevBlockHash;
    private Sha256Hash merkleRoot;
    private long time;
    private long difficultyTarget; // "nBits"
    private long nonce;

    // TODO: Get rid of all the direct accesses to this field. It's a long-since unnecessary holdover from the Dalvik days.
    /** If null, it means this object holds only the headers. */
    @Nullable List<Transaction> transactions;

    /** Stores the hash of the block. If null, getHash() will recalculate it. */
    private transient Sha256Hash hash;

    private transient boolean headerParsed;
    private transient boolean transactionsParsed;

    private transient boolean headerBytesValid;
    private transient boolean transactionBytesValid;
    
    // Blocks can be encoded in a way that will use more bytes than is optimal (due to VarInts having multiple encodings)
    // MAX_BLOCK_SIZE must be compared to the optimal encoding, not the actual encoding, so when parsing, we keep track
    // of the size of the ideal encoding in addition to the actual message size (which Message needs)
    private transient int optimalEncodingMessageSize;

    /** Special case constructor, used for the genesis node, cloneAsHeader and unit tests. */
    Block(NetworkParameters params) {
        super(params);
        // Set up a few basic things. We are not complete after this though.
        version = 1;
        difficultyTarget = 0x1d07fff8L;
        time = System.currentTimeMillis() / 1000;
        prevBlockHash = Sha256Hash.ZERO_HASH;

        length = 80;
    }

    /** Constructs a block object from the Bitcoin wire format. */
    public Block(NetworkParameters params, byte[] payloadBytes) throws ProtocolException {
        super(params, payloadBytes, 0, false, false, payloadBytes.length);
    }

    /**
     * Contruct a block object from the Bitcoin wire format.
     * @param params NetworkParameters object.
     * @param parseLazy Whether to perform a full parse immediately or delay until a read is requested.
     * @param parseRetain Whether to retain the backing byte array for quick reserialization.  
     * If true and the backing byte array is invalidated due to modification of a field then 
     * the cached bytes may be repopulated and retained if the message is serialized again in the future.
     * @param length The length of message if known.  Usually this is provided when deserializing of the wire
     * as the length will be provided as part of the header.  If unknown then set to Message.UNKNOWN_LENGTH
     * @throws ProtocolException
     */
    public Block(NetworkParameters params, byte[] payloadBytes, boolean parseLazy, boolean parseRetain, int length)
            throws ProtocolException {
        super(params, payloadBytes, 0, parseLazy, parseRetain, length);
    }


    /**
     * Construct a block initialized with all the given fields.
     * @param params Which network the block is for.
     * @param version This should usually be set to 1 or 2, depending on if the height is in the coinbase input.
     * @param prevBlockHash Reference to previous block in the chain or {@link Sha256Hash#ZERO_HASH} if genesis.
     * @param merkleRoot The root of the merkle tree formed by the transactions.
     * @param time UNIX time when the block was mined.
     * @param difficultyTarget Number which this block hashes lower than.
     * @param nonce Arbitrary number to make the block hash lower than the target.
     * @param transactions List of transactions including the coinbase.
     */
    public Block(NetworkParameters params, long version, Sha256Hash prevBlockHash, Sha256Hash merkleRoot, long time,
                 long difficultyTarget, long nonce, List<Transaction> transactions) {
        super(params);
        this.version = version;
        this.prevBlockHash = prevBlockHash;
        this.merkleRoot = merkleRoot;
        this.time = time;
        this.difficultyTarget = difficultyTarget;
        this.nonce = nonce;
        this.transactions = new LinkedList<Transaction>();
        this.transactions.addAll(transactions);
    }


    /**
     * <p>A utility method that calculates how much new Bitcoin would be created by the block at the given height.
     * The inflation of Bitcoin is predictable and drops roughly every 4 years (210,000 blocks). At the dawn of
     * the system it was 50 coins per block, in late 2012 it went to 25 coins per block, and so on. The size of
     * a coinbase transaction is inflation plus fees.</p>
     *
     * <p>The half-life is controlled by {@link org.bitcoinj.core.NetworkParameters#getSubsidyDecreaseBlockCount()}.
     * </p>
     */
    public Coin getBlockInflation(int height) {
        return FIFTY_COINS.shiftRight(height / params.getSubsidyDecreaseBlockCount());
    }

    private void readObject(ObjectInputStream ois) throws ClassNotFoundException, IOException {
        ois.defaultReadObject();
        // This code is not actually necessary, as transient fields are initialized to the default value which is in
        // this case null. However it clears out a FindBugs warning and makes it explicit what we're doing.
        hash = null;
    }

    protected void parseHeader() throws ProtocolException {
        if (headerParsed)
            return;

        cursor = offset;
        version = readUint32();
        prevBlockHash = readHash();
        merkleRoot = readHash();
        time = readUint32();
        difficultyTarget = readUint32();
        nonce = readUint32();

        hash = new Sha256Hash(Utils.reverseBytes(Utils.doubleDigest(payload, offset, cursor)));

        headerParsed = true;
        headerBytesValid = parseRetain;
    }

    protected void parseTransactions() throws ProtocolException {
        if (transactionsParsed)
            return;

        cursor = offset + HEADER_SIZE;
        optimalEncodingMessageSize = HEADER_SIZE;
        if (payload.length == cursor) {
            // This message is just a header, it has no transactions.
            transactionsParsed = true;
            transactionBytesValid = false;
            return;
        }

        int numTransactions = (int) readVarInt();
        optimalEncodingMessageSize += VarInt.sizeOf(numTransactions);
        transactions = new ArrayList<Transaction>(numTransactions);
        for (int i = 0; i < numTransactions; i++) {
            Transaction tx = new Transaction(params, payload, cursor, this, parseLazy, parseRetain, UNKNOWN_LENGTH);
            // Label the transaction as coming from the P2P network, so code that cares where we first saw it knows.
            tx.getConfidence().setSource(TransactionConfidence.Source.NETWORK);
            transactions.add(tx);
            cursor += tx.getMessageSize();
            optimalEncodingMessageSize += tx.getOptimalEncodingMessageSize();
        }
        // No need to set length here. If length was not provided then it should be set at the end of parseLight().
        // If this is a genuine lazy parse then length must have been provided to the constructor.
        transactionsParsed = true;
        transactionBytesValid = parseRetain;
    }

    @Override
    void parse() throws ProtocolException {
        parseHeader();
        parseTransactions();
        length = cursor - offset;
    }
    
    public int getOptimalEncodingMessageSize() {
        if (optimalEncodingMessageSize != 0)
            return optimalEncodingMessageSize;
        maybeParseTransactions();
        if (optimalEncodingMessageSize != 0)
            return optimalEncodingMessageSize;
        optimalEncodingMessageSize = bitcoinSerialize().length;
        return optimalEncodingMessageSize;
    }

    @Override
    protected void parseLite() throws ProtocolException {
        // Ignore the header since it has fixed length. If length is not provided we will have to
        // invoke a light parse of transactions to calculate the length.
        if (length == UNKNOWN_LENGTH) {
            Preconditions.checkState(parseLazy,
                    "Performing lite parse of block transaction as block was initialised from byte array " +
                    "without providing length.  This should never need to happen.");
            parseTransactions();
            length = cursor - offset;
        } else {
            transactionBytesValid = !transactionsParsed || parseRetain && length > HEADER_SIZE;
        }
        headerBytesValid = !headerParsed || parseRetain && length >= HEADER_SIZE;
    }

    /*
     * Block uses some special handling for lazy parsing and retention of cached bytes. Parsing and serializing the
     * block header and the transaction list are both non-trivial so there are good efficiency gains to be had by
     * separating them. There are many cases where a user may need to access or change one or the other but not both.
     *
     * With this in mind we ignore the inherited checkParse() and unCache() methods and implement a separate version
     * of them for both header and transactions.
     *
     * Serializing methods are also handled in their own way. Whilst they deal with separate parts of the block structure
     * there are some interdependencies. For example altering a tx requires invalidating the Merkle root and therefore
     * the cached header bytes.
     */
    private void maybeParseHeader() {
        if (headerParsed || payload == null)
            return;
        try {
            parseHeader();
            if (!(headerBytesValid || transactionBytesValid))
                payload = null;
        } catch (ProtocolException e) {
            throw new LazyParseException(
                    "ProtocolException caught during lazy parse.  For safe access to fields call ensureParsed before attempting read or write access",
                    e);
        }
    }

    private void maybeParseTransactions() {
        if (transactionsParsed || payload == null)
            return;
        try {
            parseTransactions();
            if (!parseRetain) {
                transactionBytesValid = false;
                if (headerParsed)
                    payload = null;
            }
        } catch (ProtocolException e) {
            throw new LazyParseException(
                    "ProtocolException caught during lazy parse.  For safe access to fields call ensureParsed before attempting read or write access",
                    e);
        }
    }

    /**
     * Ensure the object is parsed if needed. This should be called in every getter before returning a value. If the
     * lazy parse flag is not set this is a method returns immediately.
     */
    @Override
    protected void maybeParse() {
        throw new LazyParseException(
                "checkParse() should never be called on a Block.  Instead use checkParseHeader() and checkParseTransactions()");
    }

    /**
     * In lazy parsing mode access to getters and setters may throw an unchecked LazyParseException.  If guaranteed
     * safe access is required this method will force parsing to occur immediately thus ensuring LazyParseExeption will
     * never be thrown from this Message. If the Message contains child messages (e.g. a Block containing Transaction
     * messages) this will not force child messages to parse.
     *
     * This method ensures parsing of both headers and transactions.
     *
     * @throws ProtocolException
     */
    @Override
    public void ensureParsed() throws ProtocolException {
        try {
            maybeParseHeader();
            maybeParseTransactions();
        } catch (LazyParseException e) {
            if (e.getCause() instanceof ProtocolException)
                throw (ProtocolException) e.getCause();
            throw new ProtocolException(e);
        }
    }

    /**
     * In lazy parsing mode access to getters and setters may throw an unchecked LazyParseException.  If guaranteed
     * safe access is required this method will force parsing to occur immediately thus ensuring LazyParseExeption
     * will never be thrown from this Message. If the Message contains child messages (e.g. a Block containing
     * Transaction messages) this will not force child messages to parse.
     *
     * This method ensures parsing of headers only.
     *
     * @throws ProtocolException
     */
    public void ensureParsedHeader() throws ProtocolException {
        try {
            maybeParseHeader();
        } catch (LazyParseException e) {
            if (e.getCause() instanceof ProtocolException)
                throw (ProtocolException) e.getCause();
            throw new ProtocolException(e);
        }
    }

    /**
     * In lazy parsing mode access to getters and setters may throw an unchecked LazyParseException.  If guaranteed
     * safe access is required this method will force parsing to occur immediately thus ensuring LazyParseExeption will
     * never be thrown from this Message. If the Message contains child messages (e.g. a Block containing Transaction
     * messages) this will not force child messages to parse.
     *
     * This method ensures parsing of transactions only.
     *
     * @throws ProtocolException
     */
    public void ensureParsedTransactions() throws ProtocolException {
        try {
            maybeParseTransactions();
        } catch (LazyParseException e) {
            if (e.getCause() instanceof ProtocolException)
                throw (ProtocolException) e.getCause();
            throw new ProtocolException(e);
        }
    }

    // default for testing
    void writeHeader(OutputStream stream) throws IOException {
        // try for cached write first
        if (headerBytesValid && payload != null && payload.length >= offset + HEADER_SIZE) {
            stream.write(payload, offset, HEADER_SIZE);
            return;
        }
        // fall back to manual write
        maybeParseHeader();
        Utils.uint32ToByteStreamLE(version, stream);
        stream.write(Utils.reverseBytes(prevBlockHash.getBytes()));
        stream.write(Utils.reverseBytes(getMerkleRoot().getBytes()));
        Utils.uint32ToByteStreamLE(time, stream);
        Utils.uint32ToByteStreamLE(difficultyTarget, stream);
        Utils.uint32ToByteStreamLE(nonce, stream);
    }

    private void writeTransactions(OutputStream stream) throws IOException {
        // check for no transaction conditions first
        // must be a more efficient way to do this but I'm tired atm.
        if (transactions == null && transactionsParsed) {
            return;
        }

        // confirmed we must have transactions either cached or as objects.
        if (transactionBytesValid && payload != null && payload.length >= offset + length) {
            stream.write(payload, offset + HEADER_SIZE, length - HEADER_SIZE);
            return;
        }

        if (transactions != null) {
            stream.write(new VarInt(transactions.size()).encode());
            for (Transaction tx : transactions) {
                tx.bitcoinSerialize(stream);
            }
        }
    }

    /**
     * Special handling to check if we have a valid byte array for both header
     * and transactions
     *
     * @throws IOException
     */
    @Override
    public byte[] bitcoinSerialize() {
        // we have completely cached byte array.
        if (headerBytesValid && transactionBytesValid) {
            Preconditions.checkNotNull(payload, "Bytes should never be null if headerBytesValid && transactionBytesValid");
            if (length == payload.length) {
                return payload;
            } else {
                // byte array is offset so copy out the correct range.
                byte[] buf = new byte[length];
                System.arraycopy(payload, offset, buf, 0, length);
                return buf;
            }
        }

        // At least one of the two cacheable components is invalid
        // so fall back to stream write since we can't be sure of the length.
        ByteArrayOutputStream stream = new UnsafeByteArrayOutputStream(length == UNKNOWN_LENGTH ? HEADER_SIZE + guessTransactionsLength() : length);
        try {
            writeHeader(stream);
            writeTransactions(stream);
        } catch (IOException e) {
            // Cannot happen, we are serializing to a memory stream.
        }
        return stream.toByteArray();
    }

    @Override
    protected void bitcoinSerializeToStream(OutputStream stream) throws IOException {
        writeHeader(stream);
        // We may only have enough data to write the header.
        writeTransactions(stream);
    }

    /**
     * Provides a reasonable guess at the byte length of the transactions part of the block.
     * The returned value will be accurate in 99% of cases and in those cases where not will probably slightly
     * oversize.
     *
     * This is used to preallocate the underlying byte array for a ByteArrayOutputStream.  If the size is under the
     * real value the only penalty is resizing of the underlying byte array.
     */
    private int guessTransactionsLength() {
        if (transactionBytesValid)
            return payload.length - HEADER_SIZE;
        if (transactions == null)
            return 0;
        int len = VarInt.sizeOf(transactions.size());
        for (Transaction tx : transactions) {
            // 255 is just a guess at an average tx length
            len += tx.length == UNKNOWN_LENGTH ? 255 : tx.length;
        }
        return len;
    }

    @Override
    protected void unCache() {
        // Since we have alternate uncache methods to use internally this will only ever be called by a child
        // transaction so we only need to invalidate that part of the cache.
        unCacheTransactions();
    }

    private void unCacheHeader() {
        maybeParseHeader();
        headerBytesValid = false;
        if (!transactionBytesValid)
            payload = null;
        hash = null;
        checksum = null;
    }

    private void unCacheTransactions() {
        maybeParseTransactions();
        transactionBytesValid = false;
        if (!headerBytesValid)
            payload = null;
        // Current implementation has to uncache headers as well as any change to a tx will alter the merkle root. In
        // future we can go more granular and cache merkle root separately so rest of the header does not need to be
        // rewritten.
        unCacheHeader();
        // Clear merkleRoot last as it may end up being parsed during unCacheHeader().
        merkleRoot = null;
    }

    /**
     * Calculates the block hash by serializing the block and hashing the
     * resulting bytes.
     */
    private Sha256Hash calculateHash() {
        try {
            ByteArrayOutputStream bos = new UnsafeByteArrayOutputStream(HEADER_SIZE);
            writeHeader(bos);
            return new Sha256Hash(Utils.reverseBytes(doubleDigest(bos.toByteArray())));
        } catch (IOException e) {
            throw new RuntimeException(e); // Cannot happen.
        }
    }

    /**
     * Returns the hash of the block (which for a valid, solved block should be below the target) in the form seen on
     * the block explorer. If you call this on block 1 in the mainnet chain
     * you will get "00000000839a8e6886ab5951d76f411475428afc90947ee320161bbf18eb6048".
     */
    public String getHashAsString() {
        return getHash().toString();
    }

    /**
     * Returns the hash of the block (which for a valid, solved block should be
     * below the target). Big endian.
     */
    @Override
    public Sha256Hash getHash() {
        if (hash == null)
            hash = calculateHash();
        return hash;
    }

    /**
     * The number that is one greater than the largest representable SHA-256
     * hash.
     */
    static private BigInteger LARGEST_HASH = BigInteger.ONE.shiftLeft(256);

    /**
     * Returns the work represented by this block.<p>
     *
     * Work is defined as the number of tries needed to solve a block in the
     * average case. Consider a difficulty target that covers 5% of all possible
     * hash values. Then the work of the block will be 20. As the target gets
     * lower, the amount of work goes up.
     */
    public BigInteger getWork() throws VerificationException {
        BigInteger target = getDifficultyTargetAsInteger();
        return LARGEST_HASH.divide(target.add(BigInteger.ONE));
    }

    /** Returns a copy of the block, but without any transactions. */
    public Block cloneAsHeader() {
        maybeParseHeader();
        Block block = new Block(params);
        copyBitcoinHeaderTo(block);
        return block;
    }

    /** Copy the block without transactions into the provided empty block. */
    protected final void copyBitcoinHeaderTo(final Block block) {
        block.nonce = nonce;
        block.prevBlockHash = prevBlockHash;
        block.merkleRoot = getMerkleRoot();
        block.version = version;
        block.time = time;
        block.difficultyTarget = difficultyTarget;
        block.transactions = null;
        block.hash = getHash();
    }

    /**
     * Returns a multi-line string containing a description of the contents of
     * the block. Use for debugging purposes only.
     */
    @Override
    public String toString() {
        StringBuilder s = new StringBuilder("v");
        s.append(version);
        s.append(" block: \n");
        s.append("   previous block: ");
        s.append(getPrevBlockHash());
        s.append("\n");
        s.append("   merkle root: ");
        s.append(getMerkleRoot());
        s.append("\n");
        s.append("   time: [");
        s.append(time);
        s.append("] ");
        s.append(Utils.dateTimeFormat(time * 1000));
        s.append("\n");
        s.append("   difficulty target (nBits): ");
        s.append(difficultyTarget);
        s.append("\n");
        s.append("   nonce: ");
        s.append(nonce);
        s.append("\n");
        if (transactions != null && transactions.size() > 0) {
            s.append("   with ").append(transactions.size()).append(" transaction(s):\n");
            for (Transaction tx : transactions) {
                s.append(tx.toString());
            }
        }
        return s.toString();
    }

    /**
     * <p>Finds a value of nonce that makes the blocks hash lower than the difficulty target. This is called mining, but
     * solve() is far too slow to do real mining with. It exists only for unit testing purposes.
     *
     * <p>This can loop forever if a solution cannot be found solely by incrementing nonce. It doesn't change
     * extraNonce.</p>
     */
    public void solve() {
        maybeParseHeader();
        while (true) {
            try {
                // Is our proof of work valid yet?
                if (checkProofOfWork(false))
                    return;
                // No, so increment the nonce and try again.
                setNonce(getNonce() + 1);
            } catch (VerificationException e) {
                throw new RuntimeException(e); // Cannot happen.
            }
        }
    }

    /**
     * Returns the difficulty target as a 256 bit value that can be compared to a SHA-256 hash. Inside a block the
     * target is represented using a compact form. If this form decodes to a value that is out of bounds, an exception
     * is thrown.
     */
    public BigInteger getDifficultyTargetAsInteger() throws VerificationException {
        maybeParseHeader();
        BigInteger target = Utils.decodeCompactBits(difficultyTarget);
        if (target.signum() <= 0 || target.compareTo(params.maxTarget) > 0)
            throw new VerificationException("Difficulty target is bad: " + target.toString());
        return target;
    }

    /** Returns true if the hash of the block is OK (lower than difficulty target). */
    protected boolean checkProofOfWork(boolean throwException) throws VerificationException {
        // This part is key - it is what proves the block was as difficult to make as it claims
        // to be. Note however that in the context of this function, the block can claim to be
        // as difficult as it wants to be .... if somebody was able to take control of our network
        // connection and fork us onto a different chain, they could send us valid blocks with
        // ridiculously easy difficulty and this function would accept them.
        //
        // To prevent this attack from being possible, elsewhere we check that the difficultyTarget
        // field is of the right value. This requires us to have the preceeding blocks.
        BigInteger target = getDifficultyTargetAsInteger();

        BigInteger h = getHash().toBigInteger();
        if (h.compareTo(target) > 0) {
            // Proof of work check failed!
            if (throwException)
                throw new VerificationException("Hash is higher than target: " + getHashAsString() + " vs "
                        + target.toString(16));
            else
                return false;
        }
        return true;
    }

    private void checkTimestamp() throws VerificationException {
        maybeParseHeader();
        // Allow injection of a fake clock to allow unit testing.
        long currentTime = Utils.currentTimeSeconds();
        if (time > currentTime + ALLOWED_TIME_DRIFT)
            throw new VerificationException(String.format("Block too far in future: %d vs %d", time, currentTime + ALLOWED_TIME_DRIFT));
    }

    private void checkSigOps() throws VerificationException {
        // Check there aren't too many signature verifications in the block. This is an anti-DoS measure, see the
        // comments for MAX_BLOCK_SIGOPS.
        int sigOps = 0;
        for (Transaction tx : transactions) {
            sigOps += tx.getSigOpCount();
        }
        if (sigOps > MAX_BLOCK_SIGOPS)
            throw new VerificationException("Block had too many Signature Operations");
    }

    private void checkMerkleRoot() throws VerificationException {
        Sha256Hash calculatedRoot = calculateMerkleRoot();
        if (!calculatedRoot.equals(merkleRoot)) {
            log.error("Merkle tree did not verify");
            throw new VerificationException("Merkle hashes do not match: " + calculatedRoot + " vs " + merkleRoot);
        }
    }

    private Sha256Hash calculateMerkleRoot() {
        List<byte[]> tree = buildMerkleTree();
        return new Sha256Hash(tree.get(tree.size() - 1));
    }

    private List<byte[]> buildMerkleTree() {
        // The Merkle root is based on a tree of hashes calculated from the transactions:
        //
        //     root
        //      / \
        //   A      B
        //  / \    / \
        // t1 t2 t3 t4
        //
        // The tree is represented as a list: t1,t2,t3,t4,A,B,root where each
        // entry is a hash.
        //
        // The hashing algorithm is double SHA-256. The leaves are a hash of the serialized contents of the transaction.
        // The interior nodes are hashes of the concenation of the two child hashes.
        //
        // This structure allows the creation of proof that a transaction was included into a block without having to
        // provide the full block contents. Instead, you can provide only a Merkle branch. For example to prove tx2 was
        // in a block you can just provide tx2, the hash(tx1) and B. Now the other party has everything they need to
        // derive the root, which can be checked against the block header. These proofs aren't used right now but
        // will be helpful later when we want to download partial block contents.
        //
        // Note that if the number of transactions is not even the last tx is repeated to make it so (see
        // tx3 above). A tree with 5 transactions would look like this:
        //
        //         root
        //        /     \
        //       1        5
        //     /   \     / \
        //    2     3    4  4
        //  / \   / \   / \
        // t1 t2 t3 t4 t5 t5
        maybeParseTransactions();
        ArrayList<byte[]> tree = new ArrayList<byte[]>();
        // Start by adding all the hashes of the transactions as leaves of the tree.
        for (Transaction t : transactions) {
            tree.add(t.getHash().getBytes());
        }
        int levelOffset = 0; // Offset in the list where the currently processed level starts.
        // Step through each level, stopping when we reach the root (levelSize == 1).
        for (int levelSize = transactions.size(); levelSize > 1; levelSize = (levelSize + 1) / 2) {
            // For each pair of nodes on that level:
            for (int left = 0; left < levelSize; left += 2) {
                // The right hand node can be the same as the left hand, in the case where we don't have enough
                // transactions.
                int right = Math.min(left + 1, levelSize - 1);
                byte[] leftBytes = Utils.reverseBytes(tree.get(levelOffset + left));
                byte[] rightBytes = Utils.reverseBytes(tree.get(levelOffset + right));
                tree.add(Utils.reverseBytes(doubleDigestTwoBuffers(leftBytes, 0, 32, rightBytes, 0, 32)));
            }
            // Move to the next level.
            levelOffset += levelSize;
        }
        return tree;
    }

    private void checkTransactions() throws VerificationException {
        // The first transaction in a block must always be a coinbase transaction.
        if (!transactions.get(0).isCoinBase())
            throw new VerificationException("First tx is not coinbase");
        // The rest must not be.
        for (int i = 1; i < transactions.size(); i++) {
            if (transactions.get(i).isCoinBase())
                throw new VerificationException("TX " + i + " is coinbase when it should not be.");
        }
    }

    /**
     * Checks the block data to ensure it follows the rules laid out in the network parameters. Specifically,
     * throws an exception if the proof of work is invalid, or if the timestamp is too far from what it should be.
     * This is <b>not</b> everything that is required for a block to be valid, only what is checkable independent
     * of the chain and without a transaction index.
     *
     * @throws VerificationException
     */
    public void verifyHeader() throws VerificationException {
        // Prove that this block is OK. It might seem that we can just ignore most of these checks given that the
        // network is also verifying the blocks, but we cannot as it'd open us to a variety of obscure attacks.
        //
        // Firstly we need to ensure this block does in fact represent real work done. If the difficulty is high
        // enough, it's probably been done by the network.
        maybeParseHeader();
        checkProofOfWork(true);
        checkTimestamp();
    }

    /**
     * Checks the block contents
     *
     * @throws VerificationException
     */
    public void verifyTransactions() throws VerificationException {
        // Now we need to check that the body of the block actually matches the headers. The network won't generate
        // an invalid block, but if we didn't validate this then an untrusted man-in-the-middle could obtain the next
        // valid block from the network and simply replace the transactions in it with their own fictional
        // transactions that reference spent or non-existant inputs.
        if (transactions.isEmpty())
            throw new VerificationException("Block had no transactions");
        maybeParseTransactions();
        if (this.getOptimalEncodingMessageSize() > MAX_BLOCK_SIZE)
            throw new VerificationException("Block larger than MAX_BLOCK_SIZE");
        checkTransactions();
        checkMerkleRoot();
        checkSigOps();
        for (Transaction transaction : transactions)
            transaction.verify();
        }

    /**
     * Verifies both the header and that the transactions hash to the merkle root.
     */
    public void verify() throws VerificationException {
        verifyHeader();
        verifyTransactions();
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Block other = (Block) o;
        return getHash().equals(other.getHash());
    }

    @Override
    public int hashCode() {
        return getHash().hashCode();
    }

    /**
     * Returns the merkle root in big endian form, calculating it from transactions if necessary.
     */
    public Sha256Hash getMerkleRoot() {
        maybeParseHeader();
        if (merkleRoot == null) {

            //TODO check if this is really necessary.
            unCacheHeader();

            merkleRoot = calculateMerkleRoot();
        }
        return merkleRoot;
    }

    /** Exists only for unit testing. */
    void setMerkleRoot(Sha256Hash value) {
        unCacheHeader();
        merkleRoot = value;
        hash = null;
    }

    /** Adds a transaction to this block. The nonce and merkle root are invalid after this. */
    public void addTransaction(Transaction t) {
        addTransaction(t, true);
    }

    /** Adds a transaction to this block, with or without checking the sanity of doing so */
    void addTransaction(Transaction t, boolean runSanityChecks) {
        unCacheTransactions();
        if (transactions == null) {
            transactions = new ArrayList<Transaction>();
        }
        t.setParent(this);
        if (runSanityChecks && transactions.size() == 0 && !t.isCoinBase())
            throw new RuntimeException("Attempted to add a non-coinbase transaction as the first transaction: " + t);
        else if (runSanityChecks && transactions.size() > 0 && t.isCoinBase())
            throw new RuntimeException("Attempted to add a coinbase transaction when there already is one: " + t);
        transactions.add(t);
        adjustLength(transactions.size(), t.length);
        // Force a recalculation next time the values are needed.
        merkleRoot = null;
        hash = null;
    }

    /** Returns the version of the block data structure as defined by the Bitcoin protocol. */
    public long getVersion() {
        maybeParseHeader();
        return version;
    }

    /**
     * Returns the hash of the previous block in the chain, as defined by the block header.
     */
    public Sha256Hash getPrevBlockHash() {
        maybeParseHeader();
        return prevBlockHash;
    }

    void setPrevBlockHash(Sha256Hash prevBlockHash) {
        unCacheHeader();
        this.prevBlockHash = prevBlockHash;
        this.hash = null;
    }

    /**
     * Returns the time at which the block was solved and broadcast, according to the clock of the solving node. This
     * is measured in seconds since the UNIX epoch (midnight Jan 1st 1970).
     */
    public long getTimeSeconds() {
        maybeParseHeader();
        return time;
    }

    /**
     * Returns the time at which the block was solved and broadcast, according to the clock of the solving node.
     */
    public Date getTime() {
        return new Date(getTimeSeconds()*1000);
    }

    public void setTime(long time) {
        unCacheHeader();
        this.time = time;
        this.hash = null;
    }

    /**
     * Returns the difficulty of the proof of work that this block should meet encoded <b>in compact form</b>. The {@link
     * BlockChain} verifies that this is not too easy by looking at the length of the chain when the block is added.
     * To find the actual value the hash should be compared against, use
     * {@link org.bitcoinj.core.Block#getDifficultyTargetAsInteger()}. Note that this is <b>not</b> the same as
     * the difficulty value reported by the Bitcoin "getdifficulty" RPC that you may see on various block explorers.
     * That number is the result of applying a formula to the underlying difficulty to normalize the minimum to 1.
     * Calculating the difficulty that way is currently unsupported.
     */
    public long getDifficultyTarget() {
        maybeParseHeader();
        return difficultyTarget;
    }

    /** Sets the difficulty target in compact form. */
    public void setDifficultyTarget(long compactForm) {
        unCacheHeader();
        this.difficultyTarget = compactForm;
        this.hash = null;
    }

    /**
     * Returns the nonce, an arbitrary value that exists only to make the hash of the block header fall below the
     * difficulty target.
     */
    public long getNonce() {
        maybeParseHeader();
        return nonce;
    }

    /** Sets the nonce and clears any cached data. */
    public void setNonce(long nonce) {
        unCacheHeader();
        this.nonce = nonce;
        this.hash = null;
    }

    /** Returns an immutable list of transactions held in this block, or null if this object represents just a header. */
    public @Nullable List<Transaction> getTransactions() {
        maybeParseTransactions();
        if (transactions == null)
            return null;
        else
            return ImmutableList.copyOf(transactions);
    }

    // ///////////////////////////////////////////////////////////////////////////////////////////////
    // Unit testing related methods.

    // Used to make transactions unique.
    static private int txCounter;

    /** Adds a coinbase transaction to the block. This exists for unit tests. */
    @VisibleForTesting
    void addCoinbaseTransaction(byte[] pubKeyTo, Coin value) {
        unCacheTransactions();
        transactions = new ArrayList<Transaction>();
        Transaction coinbase = new Transaction(params);
        // A real coinbase transaction has some stuff in the scriptSig like the extraNonce and difficulty. The
        // transactions are distinguished by every TX output going to a different key.
        //
        // Here we will do things a bit differently so a new address isn't needed every time. We'll put a simple
        // counter in the scriptSig so every transaction has a different hash.
        coinbase.addInput(new TransactionInput(params, coinbase,
                new ScriptBuilder().data(new byte[]{(byte) txCounter, (byte) (txCounter++ >> 8)}).build().getProgram()));
        coinbase.addOutput(new TransactionOutput(params, coinbase, value,
                ScriptBuilder.createOutputScript(ECKey.fromPublicOnly(pubKeyTo)).getProgram()));
        transactions.add(coinbase);
        coinbase.setParent(this);
        coinbase.length = coinbase.bitcoinSerialize().length;
        adjustLength(transactions.size(), coinbase.length);
    }

    static final byte[] EMPTY_BYTES = new byte[32];

    // It's pretty weak to have this around at runtime: fix later.
    private static final byte[] pubkeyForTesting = new ECKey().getPubKey();

    /**
     * Returns a solved block that builds on top of this one. This exists for unit tests.
     */
    @VisibleForTesting
    public Block createNextBlock(Address to, long time) {
        return createNextBlock(to, null, time, pubkeyForTesting, FIFTY_COINS);
    }

    /**
     * Returns a solved block that builds on top of this one. This exists for unit tests.
     * In this variant you can specify a public key (pubkey) for use in generating coinbase blocks.
     */
    Block createNextBlock(@Nullable Address to, @Nullable TransactionOutPoint prevOut, long time,
                          byte[] pubKey, Coin coinbaseValue) {
        Block b = new Block(params);
        b.setDifficultyTarget(difficultyTarget);
        b.addCoinbaseTransaction(pubKey, coinbaseValue);

        if (to != null) {
            // Add a transaction paying 50 coins to the "to" address.
            Transaction t = new Transaction(params);
            t.addOutput(new TransactionOutput(params, t, FIFTY_COINS, to));
            // The input does not really need to be a valid signature, as long as it has the right general form.
            TransactionInput input;
            if (prevOut == null) {
                input = new TransactionInput(params, t, Script.createInputScript(EMPTY_BYTES, EMPTY_BYTES));
                // Importantly the outpoint hash cannot be zero as that's how we detect a coinbase transaction in isolation
                // but it must be unique to avoid 'different' transactions looking the same.
                byte[] counter = new byte[32];
                counter[0] = (byte) txCounter;
                counter[1] = (byte) (txCounter++ >> 8);
                input.getOutpoint().setHash(new Sha256Hash(counter));
            } else {
                input = new TransactionInput(params, t, Script.createInputScript(EMPTY_BYTES, EMPTY_BYTES), prevOut);
            }
            t.addInput(input);
            b.addTransaction(t);
        }

        b.setPrevBlockHash(getHash());
        // Don't let timestamp go backwards
        if (getTimeSeconds() >= time)
            b.setTime(getTimeSeconds() + 1);
        else
            b.setTime(time);
        b.solve();
        try {
            b.verifyHeader();
        } catch (VerificationException e) {
            throw new RuntimeException(e); // Cannot happen.
        }
        return b;
    }

    @VisibleForTesting
    public Block createNextBlock(@Nullable Address to, TransactionOutPoint prevOut) {
        return createNextBlock(to, prevOut, getTimeSeconds() + 5, pubkeyForTesting, FIFTY_COINS);
    }

    @VisibleForTesting
    public Block createNextBlock(@Nullable Address to, Coin value) {
        return createNextBlock(to, null, getTimeSeconds() + 5, pubkeyForTesting, value);
    }

    @VisibleForTesting
    public Block createNextBlock(@Nullable Address to) {
        return createNextBlock(to, FIFTY_COINS);
    }

    @VisibleForTesting
    public Block createNextBlockWithCoinbase(byte[] pubKey, Coin coinbaseValue) {
        return createNextBlock(null, null, Utils.currentTimeSeconds(), pubKey, coinbaseValue);
    }

    /**
     * Create a block sending 50BTC as a coinbase transaction to the public key specified.
     * This method is intended for test use only.
     */
    @VisibleForTesting
    Block createNextBlockWithCoinbase(byte[] pubKey) {
        return createNextBlock(null, null, Utils.currentTimeSeconds(), pubKey, FIFTY_COINS);
    }

    @VisibleForTesting
    boolean isParsedHeader() {
        return headerParsed;
    }

    @VisibleForTesting
    boolean isParsedTransactions() {
        return transactionsParsed;
    }

    @VisibleForTesting
    boolean isHeaderBytesValid() {
        return headerBytesValid;
    }

    @VisibleForTesting
    boolean isTransactionBytesValid() {
        return transactionBytesValid;
    }
}


File: core/src/main/java/org/bitcoinj/core/CheckpointManager.java
/**
 * Copyright 2013 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.core;

import org.bitcoinj.store.BlockStore;
import org.bitcoinj.store.BlockStoreException;
import org.bitcoinj.store.FullPrunedBlockStore;
import com.google.common.base.Charsets;
import com.google.common.hash.HashCode;
import com.google.common.hash.Hasher;
import com.google.common.hash.Hashing;
import com.google.common.io.BaseEncoding;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.DataInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.security.DigestInputStream;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Map;
import java.util.TreeMap;

import static com.google.common.base.Preconditions.*;

/**
 * <p>Vends hard-coded {@link StoredBlock}s for blocks throughout the chain. Checkpoints serve two purposes:</p>
 * <ol>
 *    <li>They act as a safety mechanism against huge re-orgs that could rewrite large chunks of history, thus
 *    constraining the block chain to be a consensus mechanism only for recent parts of the timeline.</li>
 *    <li>They allow synchronization to the head of the chain for new wallets/users much faster than syncing all
 *    headers from the genesis block.</li>
 * </ol>
 *
 * <p>Checkpoints are used by the SPV {@link BlockChain} to initialize fresh
 * {@link org.bitcoinj.store.SPVBlockStore}s. They are not used by fully validating mode, which instead has a
 * different concept of checkpoints that are used to hard-code the validity of blocks that violate BIP30 (duplicate
 * coinbase transactions). Those "checkpoints" can be found in NetworkParameters.</p>
 *
 * <p>The file format consists of the string "CHECKPOINTS 1", followed by a uint32 containing the number of signatures
 * to read. The value may not be larger than 256 (so it could have been a byte but isn't for historical reasons).
 * If the number of signatures is larger than zero, each 65 byte ECDSA secp256k1 signature then follows. The signatures
 * sign the hash of all bytes that follow the last signature.</p>
 *
 * <p>After the signatures come an int32 containing the number of checkpoints in the file. Then each checkpoint follows
 * one after the other. A checkpoint is 12 bytes for the total work done field, 4 bytes for the height, 80 bytes
 * for the block header and then 1 zero byte at the end (i.e. number of transactions in the block: always zero).</p>
 */
public class CheckpointManager {
    private static final Logger log = LoggerFactory.getLogger(CheckpointManager.class);

    private static final String BINARY_MAGIC = "CHECKPOINTS 1";
    private static final String TEXTUAL_MAGIC = "TXT CHECKPOINTS 1";
    private static final int MAX_SIGNATURES = 256;

    // Map of block header time to data.
    protected final TreeMap<Long, StoredBlock> checkpoints = new TreeMap<Long, StoredBlock>();

    protected final NetworkParameters params;
    protected final Sha256Hash dataHash;

    public static final BaseEncoding BASE64 = BaseEncoding.base64().omitPadding();

    public CheckpointManager(NetworkParameters params, InputStream inputStream) throws IOException {
        this.params = checkNotNull(params);
        checkNotNull(inputStream);
        inputStream = new BufferedInputStream(inputStream);
        inputStream.mark(1);
        int first = inputStream.read();
        inputStream.reset();
        if (first == BINARY_MAGIC.charAt(0))
            dataHash = readBinary(inputStream);
        else if (first == TEXTUAL_MAGIC.charAt(0))
            dataHash = readTextual(inputStream);
        else
            throw new IOException("Unsupported format.");
    }

    private Sha256Hash readBinary(InputStream inputStream) throws IOException {
        DataInputStream dis = null;
        try {
            MessageDigest digest = Utils.newSha256Digest();
            DigestInputStream digestInputStream = new DigestInputStream(inputStream, digest);
            dis = new DataInputStream(digestInputStream);
            digestInputStream.on(false);
            byte[] header = new byte[BINARY_MAGIC.length()];
            dis.readFully(header);
            if (!Arrays.equals(header, BINARY_MAGIC.getBytes("US-ASCII")))
                throw new IOException("Header bytes did not match expected version");
            int numSignatures = checkPositionIndex(dis.readInt(), MAX_SIGNATURES, "Num signatures out of range");
            for (int i = 0; i < numSignatures; i++) {
                byte[] sig = new byte[65];
                dis.readFully(sig);
                // TODO: Do something with the signature here.
            }
            digestInputStream.on(true);
            int numCheckpoints = dis.readInt();
            checkState(numCheckpoints > 0);
            final int size = StoredBlock.COMPACT_SERIALIZED_SIZE;
            ByteBuffer buffer = ByteBuffer.allocate(size);
            for (int i = 0; i < numCheckpoints; i++) {
                if (dis.read(buffer.array(), 0, size) < size)
                    throw new IOException("Incomplete read whilst loading checkpoints.");
                StoredBlock block = StoredBlock.deserializeCompact(params, buffer);
                buffer.position(0);
                checkpoints.put(block.getHeader().getTimeSeconds(), block);
            }
            Sha256Hash dataHash = new Sha256Hash(digest.digest());
            log.info("Read {} checkpoints, hash is {}", checkpoints.size(), dataHash);
            return dataHash;
        } catch (ProtocolException e) {
            throw new IOException(e);
        } finally {
            if (dis != null) dis.close();
            inputStream.close();
        }
    }

    private Sha256Hash readTextual(InputStream inputStream) throws IOException {
        Hasher hasher = Hashing.sha256().newHasher();
        BufferedReader reader = null;
        try {
            reader = new BufferedReader(new InputStreamReader(inputStream, Charsets.US_ASCII));
            String magic = reader.readLine();
            if (!TEXTUAL_MAGIC.equals(magic))
                throw new IOException("unexpected magic: " + magic);
            int numSigs = Integer.parseInt(reader.readLine());
            for (int i = 0; i < numSigs; i++)
                reader.readLine(); // Skip sigs for now.
            int numCheckpoints = Integer.parseInt(reader.readLine());
            checkState(numCheckpoints > 0);
            // Hash numCheckpoints in a way compatible to the binary format.
            hasher.putBytes(ByteBuffer.allocate(4).order(ByteOrder.BIG_ENDIAN).putInt(numCheckpoints).array());
            final int size = StoredBlock.COMPACT_SERIALIZED_SIZE;
            ByteBuffer buffer = ByteBuffer.allocate(size);
            for (int i = 0; i < numCheckpoints; i++) {
                byte[] bytes = BASE64.decode(reader.readLine());
                hasher.putBytes(bytes);
                buffer.position(0);
                buffer.put(bytes);
                buffer.position(0);
                StoredBlock block = StoredBlock.deserializeCompact(params, buffer);
                checkpoints.put(block.getHeader().getTimeSeconds(), block);
            }
            HashCode hash = hasher.hash();
            log.info("Read {} checkpoints, hash is {}", checkpoints.size(), hash);
            return new Sha256Hash(hash.asBytes());
        } finally {
            if (reader != null) reader.close();
        }
    }

    /**
     * Returns a {@link StoredBlock} representing the last checkpoint before the given time, for example, normally
     * you would want to know the checkpoint before the earliest wallet birthday.
     */
    public StoredBlock getCheckpointBefore(long time) {
        try {
            checkArgument(time > params.getGenesisBlock().getTimeSeconds());
            // This is thread safe because the map never changes after creation.
            Map.Entry<Long, StoredBlock> entry = checkpoints.floorEntry(time);
            if (entry != null) return entry.getValue();
            Block genesis = params.getGenesisBlock().cloneAsHeader();
            return new StoredBlock(genesis, genesis.getWork(), 0);
        } catch (VerificationException e) {
            throw new RuntimeException(e);  // Cannot happen.
        }
    }

    /** Returns the number of checkpoints that were loaded. */
    public int numCheckpoints() {
        return checkpoints.size();
    }

    /** Returns a hash of the concatenated checkpoint data. */
    public Sha256Hash getDataHash() {
        return dataHash;
    }

    /**
     * <p>Convenience method that creates a CheckpointManager, loads the given data, gets the checkpoint for the given
     * time, then inserts it into the store and sets that to be the chain head. Useful when you have just created
     * a new store from scratch and want to use configure it all in one go.</p>
     *
     * <p>Note that time is adjusted backwards by a week to account for possible clock drift in the block headers.</p>
     */
    public static void checkpoint(NetworkParameters params, InputStream checkpoints, BlockStore store, long time)
            throws IOException, BlockStoreException {
        checkNotNull(params);
        checkNotNull(store);
        checkArgument(!(store instanceof FullPrunedBlockStore), "You cannot use checkpointing with a full store.");

        time -= 86400 * 7;

        checkArgument(time > 0);
        log.info("Attempting to initialize a new block store with a checkpoint for time {}", time);

        BufferedInputStream stream = new BufferedInputStream(checkpoints);
        CheckpointManager manager = new CheckpointManager(params, stream);
        StoredBlock checkpoint = manager.getCheckpointBefore(time);
        store.put(checkpoint);
        store.setChainHead(checkpoint);
    }
}


File: core/src/main/java/org/bitcoinj/core/PartialMerkleTree.java
/**
 * Copyright 2012 The Bitcoin Developers
 * Copyright 2012 Matt Corallo
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.core;

import java.io.IOException;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import static org.bitcoinj.core.Utils.*;

/**
 * <p>A data structure that contains proofs of block inclusion for one or more transactions, in an efficient manner.</p>
 *
 * <p>The encoding works as follows: we traverse the tree in depth-first order, storing a bit for each traversed node,
 * signifying whether the node is the parent of at least one matched leaf txid (or a matched txid itself). In case we
 * are at the leaf level, or this bit is 0, its merkle node hash is stored, and its children are not explored further.
 * Otherwise, no hash is stored, but we recurse into both (or the only) child branch. During decoding, the same
 * depth-first traversal is performed, consuming bits and hashes as they were written during encoding.</p>
 *
 * <p>The serialization is fixed and provides a hard guarantee about the encoded size,
 * <tt>SIZE <= 10 + ceil(32.25*N)</tt> where N represents the number of leaf nodes of the partial tree. N itself
 * is bounded by:</p>
 *
 * <p>
 * N <= total_transactions<br>
 * N <= 1 + matched_transactions*tree_height
 * </p>
 *
 * <p><pre>The serialization format:
 *  - uint32     total_transactions (4 bytes)
 *  - varint     number of hashes   (1-3 bytes)
 *  - uint256[]  hashes in depth-first order (<= 32*N bytes)
 *  - varint     number of bytes of flag bits (1-3 bytes)
 *  - byte[]     flag bits, packed per 8 in a byte, least significant bit first (<= 2*N-1 bits)
 * The size constraints follow from this.</pre></p>
 */
public class PartialMerkleTree extends Message {
    // the total number of transactions in the block
    private int transactionCount;

    // node-is-parent-of-matched-txid bits
    private byte[] matchedChildBits;

    // txids and internal hashes
    private List<Sha256Hash> hashes;
    
    public PartialMerkleTree(NetworkParameters params, byte[] payloadBytes, int offset) throws ProtocolException {
        super(params, payloadBytes, offset);
    }

    /**
     * Constructs a new PMT with the given bit set (little endian) and the raw list of hashes including internal hashes,
     * taking ownership of the list.
     */
    public PartialMerkleTree(NetworkParameters params, byte[] bits, List<Sha256Hash> hashes, int origTxCount) {
        super(params);
        this.matchedChildBits = bits;
        this.hashes = hashes;
        this.transactionCount = origTxCount;
    }

    /**
     * Calculates a PMT given the list of leaf hashes and which leaves need to be included. The relevant interior hashes
     * are calculated and a new PMT returned.
     */
    public static PartialMerkleTree buildFromLeaves(NetworkParameters params, byte[] includeBits, List<Sha256Hash> allLeafHashes) {
        // Calculate height of the tree.
        int height = 0;
        while (getTreeWidth(allLeafHashes.size(), height) > 1)
            height++;
        List<Boolean> bitList = new ArrayList<Boolean>();
        List<Sha256Hash> hashes = new ArrayList<Sha256Hash>();
        traverseAndBuild(height, 0, allLeafHashes, includeBits, bitList, hashes);
        byte[] bits = new byte[(int)Math.ceil(bitList.size() / 8.0)];
        for (int i = 0; i < bitList.size(); i++)
            if (bitList.get(i))
                Utils.setBitLE(bits, i);
        return new PartialMerkleTree(params, bits, hashes, allLeafHashes.size());
    }

    @Override
    public void bitcoinSerializeToStream(OutputStream stream) throws IOException {
        uint32ToByteStreamLE(transactionCount, stream);

        stream.write(new VarInt(hashes.size()).encode());
        for (Sha256Hash hash : hashes)
            stream.write(reverseBytes(hash.getBytes()));

        stream.write(new VarInt(matchedChildBits.length).encode());
        stream.write(matchedChildBits);
    }

    @Override
    void parse() throws ProtocolException {
        transactionCount = (int)readUint32();

        int nHashes = (int) readVarInt();
        hashes = new ArrayList<Sha256Hash>(nHashes);
        for (int i = 0; i < nHashes; i++)
            hashes.add(readHash());

        int nFlagBytes = (int) readVarInt();
        matchedChildBits = readBytes(nFlagBytes);

        length = cursor - offset;
    }

    // Based on CPartialMerkleTree::TraverseAndBuild in Bitcoin Core.
    private static void traverseAndBuild(int height, int pos, List<Sha256Hash> allLeafHashes, byte[] includeBits,
                                         List<Boolean> matchedChildBits, List<Sha256Hash> resultHashes) {
        boolean parentOfMatch = false;
        // Is this node a parent of at least one matched hash?
        for (int p = pos << height; p < (pos+1) << height && p < allLeafHashes.size(); p++) {
            if (Utils.checkBitLE(includeBits, p)) {
                parentOfMatch = true;
                break;
            }
        }
        // Store as a flag bit.
        matchedChildBits.add(parentOfMatch);
        if (height == 0 || !parentOfMatch) {
            // If at height 0, or nothing interesting below, store hash and stop.
            resultHashes.add(calcHash(height, pos, allLeafHashes));
        } else {
            // Otherwise descend into the subtrees.
            int h = height - 1;
            int p = pos * 2;
            traverseAndBuild(h, p, allLeafHashes, includeBits, matchedChildBits, resultHashes);
            if (p + 1 < getTreeWidth(allLeafHashes.size(), h))
                traverseAndBuild(h, p + 1, allLeafHashes, includeBits, matchedChildBits, resultHashes);
        }
    }

    private static Sha256Hash calcHash(int height, int pos, List<Sha256Hash> hashes) {
        if (height == 0) {
            // Hash at height 0 is just the regular tx hash itself.
            return hashes.get(pos);
        }
        int h = height - 1;
        int p = pos * 2;
        Sha256Hash left = calcHash(h, p, hashes);
        // Calculate right hash if not beyond the end of the array - copy left hash otherwise.
        Sha256Hash right;
        if (p + 1 < getTreeWidth(hashes.size(), h)) {
            right = calcHash(h, p + 1, hashes);
        } else {
            right = left;
        }
        return combineLeftRight(left.getBytes(), right.getBytes());
    }

    @Override
    protected void parseLite() {
        
    }
    
    // helper function to efficiently calculate the number of nodes at given height in the merkle tree
    private static int getTreeWidth(int transactionCount, int height) {
        return (transactionCount + (1 << height) - 1) >> height;
    }
    
    private static class ValuesUsed {
        public int bitsUsed = 0, hashesUsed = 0;
    }
    
    // recursive function that traverses tree nodes, consuming the bits and hashes produced by TraverseAndBuild.
    // it returns the hash of the respective node.
    private Sha256Hash recursiveExtractHashes(int height, int pos, ValuesUsed used, List<Sha256Hash> matchedHashes) throws VerificationException {
        if (used.bitsUsed >= matchedChildBits.length*8) {
            // overflowed the bits array - failure
            throw new VerificationException("PartialMerkleTree overflowed its bits array");
        }
        boolean parentOfMatch = checkBitLE(matchedChildBits, used.bitsUsed++);
        if (height == 0 || !parentOfMatch) {
            // if at height 0, or nothing interesting below, use stored hash and do not descend
            if (used.hashesUsed >= hashes.size()) {
                // overflowed the hash array - failure
                throw new VerificationException("PartialMerkleTree overflowed its hash array");
            }
            Sha256Hash hash = hashes.get(used.hashesUsed++);
            if (height == 0 && parentOfMatch) // in case of height 0, we have a matched txid
                matchedHashes.add(hash);
            return hash;
        } else {
            // otherwise, descend into the subtrees to extract matched txids and hashes
            byte[] left = recursiveExtractHashes(height - 1, pos * 2, used, matchedHashes).getBytes(), right;
            if (pos * 2 + 1 < getTreeWidth(transactionCount, height-1)) {
                right = recursiveExtractHashes(height - 1, pos * 2 + 1, used, matchedHashes).getBytes();
                if (Arrays.equals(right, left))
                    throw new VerificationException("Invalid merkle tree with duplicated left/right branches");
            } else {
                right = left;
            }
            // and combine them before returning
            return combineLeftRight(left, right);
        }
    }

    private static Sha256Hash combineLeftRight(byte[] left, byte[] right) {
        return new Sha256Hash(reverseBytes(doubleDigestTwoBuffers(
                reverseBytes(left), 0, 32,
                reverseBytes(right), 0, 32)));
    }

    /**
     * Extracts tx hashes that are in this merkle tree
     * and returns the merkle root of this tree.
     * 
     * The returned root should be checked against the
     * merkle root contained in the block header for security.
     * 
     * @param matchedHashesOut A list which will contain the matched txn (will be cleared).
     * @return the merkle root of this merkle tree
     * @throws ProtocolException if this partial merkle tree is invalid
     */
    public Sha256Hash getTxnHashAndMerkleRoot(List<Sha256Hash> matchedHashesOut) throws VerificationException {
        matchedHashesOut.clear();
        
        // An empty set will not work
        if (transactionCount == 0)
            throw new VerificationException("Got a CPartialMerkleTree with 0 transactions");
        // check for excessively high numbers of transactions
        if (transactionCount > Block.MAX_BLOCK_SIZE / 60) // 60 is the lower bound for the size of a serialized CTransaction
            throw new VerificationException("Got a CPartialMerkleTree with more transactions than is possible");
        // there can never be more hashes provided than one for every txid
        if (hashes.size() > transactionCount)
            throw new VerificationException("Got a CPartialMerkleTree with more hashes than transactions");
        // there must be at least one bit per node in the partial tree, and at least one node per hash
        if (matchedChildBits.length*8 < hashes.size())
            throw new VerificationException("Got a CPartialMerkleTree with fewer matched bits than hashes");
        // calculate height of tree
        int height = 0;
        while (getTreeWidth(transactionCount, height) > 1)
            height++;
        // traverse the partial tree
        ValuesUsed used = new ValuesUsed();
        Sha256Hash merkleRoot = recursiveExtractHashes(height, 0, used, matchedHashesOut);
        // verify that all bits were consumed (except for the padding caused by serializing it as a byte sequence)
        if ((used.bitsUsed+7)/8 != matchedChildBits.length ||
                // verify that all hashes were consumed
                used.hashesUsed != hashes.size())
            throw new VerificationException("Got a CPartialMerkleTree that didn't need all the data it provided");
        
        return merkleRoot;
    }

    public int getTransactionCount() {
        return transactionCount;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        PartialMerkleTree tree = (PartialMerkleTree) o;

        if (transactionCount != tree.transactionCount) return false;
        if (!hashes.equals(tree.hashes)) return false;
        if (!Arrays.equals(matchedChildBits, tree.matchedChildBits)) return false;

        return true;
    }

    @Override
    public int hashCode() {
        int result = transactionCount;
        result = 31 * result + Arrays.hashCode(matchedChildBits);
        result = 31 * result + hashes.hashCode();
        return result;
    }

    @Override
    public String toString() {
        return "PartialMerkleTree{" +
                "transactionCount=" + transactionCount +
                ", matchedChildBits=" + Arrays.toString(matchedChildBits) +
                ", hashes=" + hashes +
                '}';
    }
}


File: core/src/main/java/org/bitcoinj/core/Sha256Hash.java
/**
 * Copyright 2011 Google Inc.
 * Copyright 2014 Andreas Schildbach
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.core;

import com.google.common.io.ByteStreams;
import com.google.common.primitives.*;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.Serializable;
import java.math.BigInteger;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;

import static com.google.common.base.Preconditions.checkArgument;

/**
 * A Sha256Hash just wraps a byte[] so that equals and hashcode work correctly, allowing it to be used as keys in a
 * map. It also checks that the length is correct and provides a bit more type safety.
 */
public class Sha256Hash implements Serializable, Comparable<Sha256Hash> {
    private final byte[] bytes;
    public static final Sha256Hash ZERO_HASH = new Sha256Hash(new byte[32]);

    /**
     * Creates a Sha256Hash by wrapping the given byte array. It must be 32 bytes long. Takes ownership!
     */
    public Sha256Hash(byte[] rawHashBytes) {
        checkArgument(rawHashBytes.length == 32);
        this.bytes = rawHashBytes;
    }

    /**
     * Creates a Sha256Hash by decoding the given hex string. It must be 64 characters long.
     */
    public Sha256Hash(String hexString) {
        checkArgument(hexString.length() == 64);
        this.bytes = Utils.HEX.decode(hexString);
    }

    /** Use Sha256Hash.hash(byte[]) instead: this old name is ambiguous */
    @Deprecated
    public static Sha256Hash create(byte[] contents) {
        return hash(contents);
    }

    /**
     * Calculates the (one-time) hash of contents and returns it.
     */
    public static Sha256Hash hash(byte[] contents) {
        return new Sha256Hash(Utils.singleDigest(contents));
    }

    /** Use hashTwice(byte[]) instead: this old name is ambiguous. */
    @Deprecated
    public static Sha256Hash createDouble(byte[] contents) {
        return hashTwice(contents);
    }

    /**
     * Calculates the hash of the hash of the contents. This is a standard operation in Bitcoin.
     */
    public static Sha256Hash hashTwice(byte[] contents) {
        return new Sha256Hash(Utils.doubleDigest(contents));
    }

    /**
     * Returns a hash of the given files contents. Reads the file fully into memory before hashing so only use with
     * small files.
     * @throws IOException
     */
    public static Sha256Hash hashFileContents(File f) throws IOException {
        FileInputStream in = new FileInputStream(f);
        try {
            return hash(ByteStreams.toByteArray(in));
        } finally {
            in.close();
        }
    }

    @Override
    public boolean equals(Object o) {
        return this == o || o != null && getClass() == o.getClass() && Arrays.equals(bytes, ((Sha256Hash)o).bytes);
    }

    /**
     * Returns the last four bytes of the wrapped hash. This should be unique enough to be a suitable hash code even for
     * blocks, where the goal is to try and get the first bytes to be zeros (i.e. the value as a big integer lower
     * than the target value).
     */
    @Override
    public int hashCode() {
        // Use the last 4 bytes, not the first 4 which are often zeros in Bitcoin.
        return Ints.fromBytes(bytes[28], bytes[29], bytes[30], bytes[31]);
    }

    @Override
    public String toString() {
        return Utils.HEX.encode(bytes);
    }

    /**
     * Returns the bytes interpreted as a positive integer.
     */
    public BigInteger toBigInteger() {
        return new BigInteger(1, bytes);
    }

    /**
     * Returns the internal byte array, without defensively copying. Therefore do NOT modify the returned array.
     */
    public byte[] getBytes() {
        return bytes;
    }

    @Override
    public int compareTo(Sha256Hash o) {
        return this.hashCode() - o.hashCode();
    }
}


File: core/src/main/java/org/bitcoinj/core/Transaction.java
/**
 * Copyright 2011 Google Inc.
 * Copyright 2014 Andreas Schildbach
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.core;

import org.bitcoinj.core.TransactionConfidence.ConfidenceType;
import org.bitcoinj.crypto.TransactionSignature;
import org.bitcoinj.script.Script;
import org.bitcoinj.script.ScriptBuilder;
import org.bitcoinj.script.ScriptOpCodes;
import org.bitcoinj.utils.ExchangeRate;
import org.bitcoinj.wallet.WalletTransaction.Pool;
import com.google.common.collect.ImmutableMap;
import com.google.common.primitives.Ints;
import com.google.common.primitives.Longs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.annotation.Nullable;
import java.io.*;
import java.util.*;

import static org.bitcoinj.core.Utils.*;
import static com.google.common.base.Preconditions.checkState;

/**
 * <p>A transaction represents the movement of coins from some addresses to some other addresses. It can also represent
 * the minting of new coins. A Transaction object corresponds to the equivalent in the Bitcoin C++ implementation.</p>
 *
 * <p>Transactions are the fundamental atoms of Bitcoin and have many powerful features. Read
 * <a href="http://code.google.com/p/bitcoinj/wiki/WorkingWithTransactions">"Working with transactions"</a> in the
 * documentation to learn more about how to use this class.</p>
 *
 * <p>All Bitcoin transactions are at risk of being reversed, though the risk is much less than with traditional payment
 * systems. Transactions have <i>confidence levels</i>, which help you decide whether to trust a transaction or not.
 * Whether to trust a transaction is something that needs to be decided on a case by case basis - a rule that makes 
 * sense for selling MP3s might not make sense for selling cars, or accepting payments from a family member. If you
 * are building a wallet, how to present confidence to your users is something to consider carefully.</p>
 */
public class Transaction extends ChildMessage implements Serializable {
    /**
     * A comparator that can be used to sort transactions by their updateTime field. The ordering goes from most recent
     * into the past.
     */
    public static final Comparator<Transaction> SORT_TX_BY_UPDATE_TIME = new Comparator<Transaction>() {
        @Override
        public int compare(final Transaction tx1, final Transaction tx2) {
            final long time1 = tx1.getUpdateTime().getTime();
            final long time2 = tx2.getUpdateTime().getTime();
            final int updateTimeComparison = -(Longs.compare(time1, time2));
            //If time1==time2, compare by tx hash to make comparator consistent with equals
            return updateTimeComparison != 0 ? updateTimeComparison : tx1.getHash().compareTo(tx2.getHash());
        }
    };
    /** A comparator that can be used to sort transactions by their chain height. */
    public static final Comparator<Transaction> SORT_TX_BY_HEIGHT = new Comparator<Transaction>() {
        @Override
        public int compare(final Transaction tx1, final Transaction tx2) {
            final int height1 = tx1.getConfidence().getAppearedAtChainHeight();
            final int height2 = tx2.getConfidence().getAppearedAtChainHeight();
            final int heightComparison = -(Ints.compare(height1, height2));
            //If height1==height2, compare by tx hash to make comparator consistent with equals
            return heightComparison != 0 ? heightComparison : tx1.getHash().compareTo(tx2.getHash());            
        }
    };
    private static final Logger log = LoggerFactory.getLogger(Transaction.class);
    private static final long serialVersionUID = -8567546957352643140L;

    /** Threshold for lockTime: below this value it is interpreted as block number, otherwise as timestamp. **/
    public static final int LOCKTIME_THRESHOLD = 500000000; // Tue Nov  5 00:53:20 1985 UTC

    /** How many bytes a transaction can be before it won't be relayed anymore. Currently 100kb. */
    public static final int MAX_STANDARD_TX_SIZE = 100000;

    /**
     * If fee is lower than this value (in satoshis), a default reference client will treat it as if there were no fee.
     * Currently this is 1000 satoshis.
     */
    public static final Coin REFERENCE_DEFAULT_MIN_TX_FEE = Coin.valueOf(1000);

    /**
     * Any standard (ie pay-to-address) output smaller than this value (in satoshis) will most likely be rejected by the network.
     * This is calculated by assuming a standard output will be 34 bytes, and then using the formula used in
     * {@link TransactionOutput#getMinNonDustValue(Coin)}. Currently it's 546 satoshis.
     */
    public static final Coin MIN_NONDUST_OUTPUT = Coin.valueOf(546);

    // These are serialized in both bitcoin and java serialization.
    private long version;
    private ArrayList<TransactionInput> inputs;
    private ArrayList<TransactionOutput> outputs;

    private long lockTime;

    // This is either the time the transaction was broadcast as measured from the local clock, or the time from the
    // block in which it was included. Note that this can be changed by re-orgs so the wallet may update this field.
    // Old serialized transactions don't have this field, thus null is valid. It is used for returning an ordered
    // list of transactions from a wallet, which is helpful for presenting to users.
    private Date updatedAt;

    // This is an in memory helper only.
    private transient Sha256Hash hash;

    // Data about how confirmed this tx is. Serialized, may be null. 
    @Nullable private TransactionConfidence confidence;

    // Records a map of which blocks the transaction has appeared in (keys) to an index within that block (values).
    // The "index" is not a real index, instead the values are only meaningful relative to each other. For example,
    // consider two transactions that appear in the same block, t1 and t2, where t2 spends an output of t1. Both
    // will have the same block hash as a key in their appearsInHashes, but the counter would be 1 and 2 respectively
    // regardless of where they actually appeared in the block.
    //
    // If this transaction is not stored in the wallet, appearsInHashes is null.
    private Map<Sha256Hash, Integer> appearsInHashes;

    // Transactions can be encoded in a way that will use more bytes than is optimal
    // (due to VarInts having multiple encodings)
    // MAX_BLOCK_SIZE must be compared to the optimal encoding, not the actual encoding, so when parsing, we keep track
    // of the size of the ideal encoding in addition to the actual message size (which Message needs) so that Blocks
    // can properly keep track of optimal encoded size
    private transient int optimalEncodingMessageSize;

    /**
     * This enum describes the underlying reason the transaction was created. It's useful for rendering wallet GUIs
     * more appropriately.
     */
    public enum Purpose {
        /** Used when the purpose of a transaction is genuinely unknown. */
        UNKNOWN,
        /** Transaction created to satisfy a user payment request. */
        USER_PAYMENT,
        /** Transaction automatically created and broadcast in order to reallocate money from old to new keys. */
        KEY_ROTATION,
        /** Transaction that uses up pledges to an assurance contract */
        ASSURANCE_CONTRACT_CLAIM,
        /** Transaction that makes a pledge to an assurance contract. */
        ASSURANCE_CONTRACT_PLEDGE,
        /** Send-to-self transaction that exists just to create an output of the right size we can pledge. */
        ASSURANCE_CONTRACT_STUB
        // In future: de/refragmentation, privacy boosting/mixing, child-pays-for-parent fees, etc.
    }

    private Purpose purpose = Purpose.UNKNOWN;

    /**
     * This field can be used by applications to record the exchange rate that was valid when the transaction happened.
     * It's optional.
     */
    @Nullable
    private ExchangeRate exchangeRate;

    /**
     * This field can be used to record the memo of the payment request that initiated the transaction. It's optional.
     */
    @Nullable
    private String memo;

    public Transaction(NetworkParameters params) {
        super(params);
        version = 1;
        inputs = new ArrayList<TransactionInput>();
        outputs = new ArrayList<TransactionOutput>();
        // We don't initialize appearsIn deliberately as it's only useful for transactions stored in the wallet.
        length = 8; // 8 for std fields
    }

    /**
     * Creates a transaction from the given serialized bytes, eg, from a block or a tx network message.
     */
    public Transaction(NetworkParameters params, byte[] payloadBytes) throws ProtocolException {
        super(params, payloadBytes, 0);
    }

    /**
     * Creates a transaction by reading payload starting from offset bytes in. Length of a transaction is fixed.
     */
    public Transaction(NetworkParameters params, byte[] payload, int offset) throws ProtocolException {
        super(params, payload, offset);
        // inputs/outputs will be created in parse()
    }

    /**
     * Creates a transaction by reading payload starting from offset bytes in. Length of a transaction is fixed.
     * @param params NetworkParameters object.
     * @param payload Bitcoin protocol formatted byte array containing message content.
     * @param offset The location of the first payload byte within the array.
     * @param parseLazy Whether to perform a full parse immediately or delay until a read is requested.
     * @param parseRetain Whether to retain the backing byte array for quick reserialization.  
     * If true and the backing byte array is invalidated due to modification of a field then 
     * the cached bytes may be repopulated and retained if the message is serialized again in the future.
     * @param length The length of message if known.  Usually this is provided when deserializing of the wire
     * as the length will be provided as part of the header.  If unknown then set to Message.UNKNOWN_LENGTH
     * @throws ProtocolException
     */
    public Transaction(NetworkParameters params, byte[] payload, int offset, @Nullable Message parent, boolean parseLazy, boolean parseRetain, int length)
            throws ProtocolException {
        super(params, payload, offset, parent, parseLazy, parseRetain, length);
    }

    /**
     * Creates a transaction by reading payload starting from offset bytes in. Length of a transaction is fixed.
     */
    public Transaction(NetworkParameters params, byte[] payload, @Nullable Message parent, boolean parseLazy, boolean parseRetain, int length)
            throws ProtocolException {
        super(params, payload, 0, parent, parseLazy, parseRetain, length);
    }

    /**
     * Returns the transaction hash as you see them in the block explorer.
     */
    @Override
    public Sha256Hash getHash() {
        if (hash == null) {
            byte[] bits = bitcoinSerialize();
            hash = new Sha256Hash(reverseBytes(doubleDigest(bits)));
        }
        return hash;
    }

    /**
     * Used by BitcoinSerializer.  The serializer has to calculate a hash for checksumming so to
     * avoid wasting the considerable effort a set method is provided so the serializer can set it.
     *
     * No verification is performed on this hash.
     */
    void setHash(Sha256Hash hash) {
        this.hash = hash;
    }

    public String getHashAsString() {
        return getHash().toString();
    }

    /**
     * Calculates the sum of the outputs that are sending coins to a key in the wallet. The flag controls whether to
     * include spent outputs or not.
     */
    Coin getValueSentToMe(TransactionBag transactionBag, boolean includeSpent) {
        maybeParse();
        // This is tested in WalletTest.
        Coin v = Coin.ZERO;
        for (TransactionOutput o : outputs) {
            if (!o.isMineOrWatched(transactionBag)) continue;
            if (!includeSpent && !o.isAvailableForSpending()) continue;
            v = v.add(o.getValue());
        }
        return v;
    }

    /*
     * If isSpent - check that all my outputs spent, otherwise check that there at least
     * one unspent.
     */
    boolean isConsistent(TransactionBag transactionBag, boolean isSpent) {
        boolean isActuallySpent = true;
        for (TransactionOutput o : outputs) {
            if (o.isAvailableForSpending()) {
                if (o.isMineOrWatched(transactionBag)) isActuallySpent = false;
                if (o.getSpentBy() != null) {
                    log.error("isAvailableForSpending != spentBy");
                    return false;
                }
            } else {
                if (o.getSpentBy() == null) {
                    log.error("isAvailableForSpending != spentBy");
                    return false;
                }
            }
        }
        return isActuallySpent == isSpent;
    }

    /**
     * Calculates the sum of the outputs that are sending coins to a key in the wallet.
     */
    public Coin getValueSentToMe(TransactionBag transactionBag) {
        return getValueSentToMe(transactionBag, true);
    }

    /**
     * Returns a map of block [hashes] which contain the transaction mapped to relativity counters, or null if this
     * transaction doesn't have that data because it's not stored in the wallet or because it has never appeared in a
     * block.
     */
    @Nullable
    public Map<Sha256Hash, Integer> getAppearsInHashes() {
        return appearsInHashes != null ? ImmutableMap.copyOf(appearsInHashes) : null;
    }

    /**
     * Convenience wrapper around getConfidence().getConfidenceType()
     * @return true if this transaction hasn't been seen in any block yet.
     */
    public boolean isPending() {
        return getConfidence().getConfidenceType() == TransactionConfidence.ConfidenceType.PENDING;
    }

    /**
     * <p>Puts the given block in the internal set of blocks in which this transaction appears. This is
     * used by the wallet to ensure transactions that appear on side chains are recorded properly even though the
     * block stores do not save the transaction data at all.</p>
     *
     * <p>If there is a re-org this will be called once for each block that was previously seen, to update which block
     * is the best chain. The best chain block is guaranteed to be called last. So this must be idempotent.</p>
     *
     * <p>Sets updatedAt to be the earliest valid block time where this tx was seen.</p>
     * 
     * @param block     The {@link StoredBlock} in which the transaction has appeared.
     * @param bestChain whether to set the updatedAt timestamp from the block header (only if not already set)
     * @param relativityOffset A number that disambiguates the order of transactions within a block.
     */
    public void setBlockAppearance(StoredBlock block, boolean bestChain, int relativityOffset) {
        long blockTime = block.getHeader().getTimeSeconds() * 1000;
        if (bestChain && (updatedAt == null || updatedAt.getTime() == 0 || updatedAt.getTime() > blockTime)) {
            updatedAt = new Date(blockTime);
        }

        addBlockAppearance(block.getHeader().getHash(), relativityOffset);

        if (bestChain) {
            TransactionConfidence transactionConfidence = getConfidence();
            // This sets type to BUILDING and depth to one.
            transactionConfidence.setAppearedAtChainHeight(block.getHeight());
        }
    }

    public void addBlockAppearance(final Sha256Hash blockHash, int relativityOffset) {
        if (appearsInHashes == null) {
            // TODO: This could be a lot more memory efficient as we'll typically only store one element.
            appearsInHashes = new TreeMap<Sha256Hash, Integer>();
        }
        appearsInHashes.put(blockHash, relativityOffset);
    }

    /**
     * Calculates the sum of the inputs that are spending coins with keys in the wallet. This requires the
     * transactions sending coins to those keys to be in the wallet. This method will not attempt to download the
     * blocks containing the input transactions if the key is in the wallet but the transactions are not.
     *
     * @return sum of the inputs that are spending coins with keys in the wallet
     */
    public Coin getValueSentFromMe(TransactionBag wallet) throws ScriptException {
        maybeParse();
        // This is tested in WalletTest.
        Coin v = Coin.ZERO;
        for (TransactionInput input : inputs) {
            // This input is taking value from a transaction in our wallet. To discover the value,
            // we must find the connected transaction.
            TransactionOutput connected = input.getConnectedOutput(wallet.getTransactionPool(Pool.UNSPENT));
            if (connected == null)
                connected = input.getConnectedOutput(wallet.getTransactionPool(Pool.SPENT));
            if (connected == null)
                connected = input.getConnectedOutput(wallet.getTransactionPool(Pool.PENDING));
            if (connected == null)
                continue;
            // The connected output may be the change to the sender of a previous input sent to this wallet. In this
            // case we ignore it.
            if (!connected.isMineOrWatched(wallet))
                continue;
            v = v.add(connected.getValue());
        }
        return v;
    }

    @Nullable private Coin cachedValue;
    @Nullable private TransactionBag cachedForBag;

    /**
     * Returns the difference of {@link Transaction#getValueSentToMe(TransactionBag)} and {@link Transaction#getValueSentFromMe(TransactionBag)}.
     */
    public Coin getValue(TransactionBag wallet) throws ScriptException {
        // FIXME: TEMP PERF HACK FOR ANDROID - this crap can go away once we have a real payments API.
        boolean isAndroid = Utils.isAndroidRuntime();
        if (isAndroid && cachedValue != null && cachedForBag == wallet)
            return cachedValue;
        Coin result = getValueSentToMe(wallet).subtract(getValueSentFromMe(wallet));
        if (isAndroid) {
            cachedValue = result;
            cachedForBag = wallet;
        }
        return result;
    }

    /**
     * The transaction fee is the difference of the value of all inputs and the value of all outputs. Currently, the fee
     * can only be determined for transactions created by us.
     * 
     * @return fee, or null if it cannot be determined
     */
    public Coin getFee() {
        Coin fee = Coin.ZERO;
        for (TransactionInput input : inputs) {
            if (input.getValue() == null)
                return null;
            fee = fee.add(input.getValue());
        }
        for (TransactionOutput output : outputs) {
            fee = fee.subtract(output.getValue());
        }
        return fee;
    }

    /**
     * Returns true if any of the outputs is marked as spent.
     */
    public boolean isAnyOutputSpent() {
        maybeParse();
        for (TransactionOutput output : outputs) {
            if (!output.isAvailableForSpending())
                return true;
        }
        return false;
    }

    /**
     * Returns false if this transaction has at least one output that is owned by the given wallet and unspent, true
     * otherwise.
     */
    public boolean isEveryOwnedOutputSpent(TransactionBag transactionBag) {
        maybeParse();
        for (TransactionOutput output : outputs) {
            if (output.isAvailableForSpending() && output.isMineOrWatched(transactionBag))
                return false;
        }
        return true;
    }

    /**
     * Returns the earliest time at which the transaction was seen (broadcast or included into the chain),
     * or the epoch if that information isn't available.
     */
    public Date getUpdateTime() {
        if (updatedAt == null) {
            // Older wallets did not store this field. Set to the epoch.
            updatedAt = new Date(0);
        }
        return updatedAt;
    }

    public void setUpdateTime(Date updatedAt) {
        this.updatedAt = updatedAt;
    }

    /**
     * These constants are a part of a scriptSig signature on the inputs. They define the details of how a
     * transaction can be redeemed, specifically, they control how the hash of the transaction is calculated.
     * <p/>
     * In the official client, this enum also has another flag, SIGHASH_ANYONECANPAY. In this implementation,
     * that's kept separate. Only SIGHASH_ALL is actually used in the official client today. The other flags
     * exist to allow for distributed contracts.
     */
    public enum SigHash {
        ALL,         // 1
        NONE,        // 2
        SINGLE,      // 3
    }
    public static final byte SIGHASH_ANYONECANPAY_VALUE = (byte) 0x80;

    @Override
    protected void unCache() {
        super.unCache();
        hash = null;
    }

    @Override
    protected void parseLite() throws ProtocolException {

        //skip this if the length has been provided i.e. the tx is not part of a block
        if (parseLazy && length == UNKNOWN_LENGTH) {
            //If length hasn't been provided this tx is probably contained within a block.
            //In parseRetain mode the block needs to know how long the transaction is
            //unfortunately this requires a fairly deep (though not total) parse.
            //This is due to the fact that transactions in the block's list do not include a
            //size header and inputs/outputs are also variable length due the contained
            //script so each must be instantiated so the scriptlength varint can be read
            //to calculate total length of the transaction.
            //We will still persist will this semi-light parsing because getting the lengths
            //of the various components gains us the ability to cache the backing bytearrays
            //so that only those subcomponents that have changed will need to be reserialized.

            //parse();
            //parsed = true;
            length = calcLength(payload, offset);
            cursor = offset + length;
        }
    }

    protected static int calcLength(byte[] buf, int offset) {
        VarInt varint;
        // jump past version (uint32)
        int cursor = offset + 4;

        int i;
        long scriptLen;

        varint = new VarInt(buf, cursor);
        long txInCount = varint.value;
        cursor += varint.getOriginalSizeInBytes();

        for (i = 0; i < txInCount; i++) {
            // 36 = length of previous_outpoint
            cursor += 36;
            varint = new VarInt(buf, cursor);
            scriptLen = varint.value;
            // 4 = length of sequence field (unint32)
            cursor += scriptLen + 4 + varint.getOriginalSizeInBytes();
        }

        varint = new VarInt(buf, cursor);
        long txOutCount = varint.value;
        cursor += varint.getOriginalSizeInBytes();

        for (i = 0; i < txOutCount; i++) {
            // 8 = length of tx value field (uint64)
            cursor += 8;
            varint = new VarInt(buf, cursor);
            scriptLen = varint.value;
            cursor += scriptLen + varint.getOriginalSizeInBytes();
        }
        // 4 = length of lock_time field (uint32)
        return cursor - offset + 4;
    }

    @Override
    void parse() throws ProtocolException {

        if (parsed)
            return;

        cursor = offset;

        version = readUint32();
        optimalEncodingMessageSize = 4;

        // First come the inputs.
        long numInputs = readVarInt();
        optimalEncodingMessageSize += VarInt.sizeOf(numInputs);
        inputs = new ArrayList<TransactionInput>((int) numInputs);
        for (long i = 0; i < numInputs; i++) {
            TransactionInput input = new TransactionInput(params, this, payload, cursor, parseLazy, parseRetain);
            inputs.add(input);
            long scriptLen = readVarInt(TransactionOutPoint.MESSAGE_LENGTH);
            optimalEncodingMessageSize += TransactionOutPoint.MESSAGE_LENGTH + VarInt.sizeOf(scriptLen) + scriptLen + 4;
            cursor += scriptLen + 4;
        }
        // Now the outputs
        long numOutputs = readVarInt();
        optimalEncodingMessageSize += VarInt.sizeOf(numOutputs);
        outputs = new ArrayList<TransactionOutput>((int) numOutputs);
        for (long i = 0; i < numOutputs; i++) {
            TransactionOutput output = new TransactionOutput(params, this, payload, cursor, parseLazy, parseRetain);
            outputs.add(output);
            long scriptLen = readVarInt(8);
            optimalEncodingMessageSize += 8 + VarInt.sizeOf(scriptLen) + scriptLen;
            cursor += scriptLen;
        }
        lockTime = readUint32();
        optimalEncodingMessageSize += 4;
        length = cursor - offset;
    }

    public int getOptimalEncodingMessageSize() {
        if (optimalEncodingMessageSize != 0)
            return optimalEncodingMessageSize;
        maybeParse();
        if (optimalEncodingMessageSize != 0)
            return optimalEncodingMessageSize;
        optimalEncodingMessageSize = getMessageSize();
        return optimalEncodingMessageSize;
    }

    /**
     * A coinbase transaction is one that creates a new coin. They are the first transaction in each block and their
     * value is determined by a formula that all implementations of Bitcoin share. In 2011 the value of a coinbase
     * transaction is 50 coins, but in future it will be less. A coinbase transaction is defined not only by its
     * position in a block but by the data in the inputs.
     */
    public boolean isCoinBase() {
        maybeParse();
        return inputs.size() == 1 && inputs.get(0).isCoinBase();
    }

    /**
     * A transaction is mature if it is either a building coinbase tx that is as deep or deeper than the required coinbase depth, or a non-coinbase tx.
     */
    public boolean isMature() {
        if (!isCoinBase())
            return true;

        if (getConfidence().getConfidenceType() != ConfidenceType.BUILDING)
            return false;

        return getConfidence().getDepthInBlocks() >= params.getSpendableCoinbaseDepth();
    }

    @Override
    public String toString() {
        return toString(null);
    }

    /**
     * A human readable version of the transaction useful for debugging. The format is not guaranteed to be stable.
     * @param chain If provided, will be used to estimate lock times (if set). Can be null.
     */
    public String toString(@Nullable AbstractBlockChain chain) {
        // Basic info about the tx.
        StringBuilder s = new StringBuilder();
        s.append(String.format("  %s: %s%n", getHashAsString(), getConfidence()));
        if (isTimeLocked()) {
            String time;
            if (lockTime < LOCKTIME_THRESHOLD) {
                time = "block " + lockTime;
                if (chain != null) {
                    time = time + " (estimated to be reached at " +
                            chain.estimateBlockTime((int)lockTime).toString() + ")";
                }
            } else {
                time = new Date(lockTime*1000).toString();
            }
            s.append(String.format("  time locked until %s%n", time));
        }
        if (inputs.size() == 0) {
            s.append(String.format("  INCOMPLETE: No inputs!%n"));
            return s.toString();
        }
        if (isCoinBase()) {
            String script;
            String script2;
            try {
                script = inputs.get(0).getScriptSig().toString();
                script2 = outputs.get(0).getScriptPubKey().toString();
            } catch (ScriptException e) {
                script = "???";
                script2 = "???";
            }
            s.append("     == COINBASE TXN (scriptSig " + script + ")  (scriptPubKey " + script2 + ")\n");
            return s.toString();
        }
        for (TransactionInput in : inputs) {
            s.append("     ");
            s.append("in   ");

            try {
                Script scriptSig = in.getScriptSig();
                s.append(scriptSig);
                if (in.getValue() != null)
                    s.append(" ").append(in.getValue().toFriendlyString());
                s.append("\n          ");
                s.append("outpoint:");
                final TransactionOutPoint outpoint = in.getOutpoint();
                s.append(outpoint.toString());
                final TransactionOutput connectedOutput = outpoint.getConnectedOutput();
                if (connectedOutput != null) {
                    Script scriptPubKey = connectedOutput.getScriptPubKey();
                    if (scriptPubKey.isSentToAddress() || scriptPubKey.isPayToScriptHash()) {
                        s.append(" hash160:");
                        s.append(Utils.HEX.encode(scriptPubKey.getPubKeyHash()));
                    }
                }
            } catch (Exception e) {
                s.append("[exception: ").append(e.getMessage()).append("]");
            }
            s.append(String.format("%n"));
        }
        for (TransactionOutput out : outputs) {
            s.append("     ");
            s.append("out  ");
            try {
                Script scriptPubKey = out.getScriptPubKey();
                s.append(scriptPubKey);
                s.append(" ");
                s.append(out.getValue().toFriendlyString());
                if (!out.isAvailableForSpending()) {
                    s.append(" Spent");
                }
                if (out.getSpentBy() != null) {
                    s.append(" by ");
                    s.append(out.getSpentBy().getParentTransaction().getHashAsString());
                }
            } catch (Exception e) {
                s.append("[exception: ").append(e.getMessage()).append("]");
            }
            s.append(String.format("%n"));
        }
        Coin fee = getFee();
        if (fee != null)
            s.append("     fee  ").append(fee.toFriendlyString()).append(String.format("%n"));
        return s.toString();
    }

    /**
     * Removes all the inputs from this transaction.
     * Note that this also invalidates the length attribute
     */
    public void clearInputs() {
        unCache();
        for (TransactionInput input : inputs) {
            input.setParent(null);
        }
        inputs.clear();
        // You wanted to reserialize, right?
        this.length = this.bitcoinSerialize().length;
    }

    /**
     * Adds an input to this transaction that imports value from the given output. Note that this input is NOT
     * complete and after every input is added with addInput() and every output is added with addOutput(),
     * signInputs() must be called to finalize the transaction and finish the inputs off. Otherwise it won't be
     * accepted by the network. Returns the newly created input.
     */
    public TransactionInput addInput(TransactionOutput from) {
        return addInput(new TransactionInput(params, this, from));
    }

    /** Adds an input directly, with no checking that it's valid. Returns the new input. */
    public TransactionInput addInput(TransactionInput input) {
        unCache();
        input.setParent(this);
        inputs.add(input);
        adjustLength(inputs.size(), input.length);
        return input;
    }

    /** Adds an input directly, with no checking that it's valid. Returns the new input. */
    public TransactionInput addInput(Sha256Hash spendTxHash, long outputIndex, Script script) {
        return addInput(new TransactionInput(params, this, script.getProgram(), new TransactionOutPoint(params, outputIndex, spendTxHash)));
    }

    /**
     * Adds a new and fully signed input for the given parameters. Note that this method is <b>not</b> thread safe
     * and requires external synchronization. Please refer to general documentation on Bitcoin scripting and contracts
     * to understand the values of sigHash and anyoneCanPay: otherwise you can use the other form of this method
     * that sets them to typical defaults.
     *
     * @throws ScriptException if the scriptPubKey is not a pay to address or pay to pubkey script.
     */
    public TransactionInput addSignedInput(TransactionOutPoint prevOut, Script scriptPubKey, ECKey sigKey,
                                           SigHash sigHash, boolean anyoneCanPay) throws ScriptException {
        // Verify the API user didn't try to do operations out of order.
        checkState(!outputs.isEmpty(), "Attempting to sign tx without outputs.");
        TransactionInput input = new TransactionInput(params, this, new byte[]{}, prevOut);
        addInput(input);
        Sha256Hash hash = hashForSignature(inputs.size() - 1, scriptPubKey, sigHash, anyoneCanPay);
        ECKey.ECDSASignature ecSig = sigKey.sign(hash);
        TransactionSignature txSig = new TransactionSignature(ecSig, sigHash, anyoneCanPay);
        if (scriptPubKey.isSentToRawPubKey())
            input.setScriptSig(ScriptBuilder.createInputScript(txSig));
        else if (scriptPubKey.isSentToAddress())
            input.setScriptSig(ScriptBuilder.createInputScript(txSig, sigKey));
        else
            throw new ScriptException("Don't know how to sign for this kind of scriptPubKey: " + scriptPubKey);
        return input;
    }

    /**
     * Same as {@link #addSignedInput(TransactionOutPoint, org.bitcoinj.script.Script, ECKey, org.bitcoinj.core.Transaction.SigHash, boolean)}
     * but defaults to {@link SigHash#ALL} and "false" for the anyoneCanPay flag. This is normally what you want.
     */
    public TransactionInput addSignedInput(TransactionOutPoint prevOut, Script scriptPubKey, ECKey sigKey) throws ScriptException {
        return addSignedInput(prevOut, scriptPubKey, sigKey, SigHash.ALL, false);
    }

    /**
     * Adds an input that points to the given output and contains a valid signature for it, calculated using the
     * signing key.
     */
    public TransactionInput addSignedInput(TransactionOutput output, ECKey signingKey) {
        return addSignedInput(output.getOutPointFor(), output.getScriptPubKey(), signingKey);
    }

    /**
     * Adds an input that points to the given output and contains a valid signature for it, calculated using the
     * signing key.
     */
    public TransactionInput addSignedInput(TransactionOutput output, ECKey signingKey, SigHash sigHash, boolean anyoneCanPay) {
        return addSignedInput(output.getOutPointFor(), output.getScriptPubKey(), signingKey, sigHash, anyoneCanPay);
    }

    /**
     * Removes all the inputs from this transaction.
     * Note that this also invalidates the length attribute
     */
    public void clearOutputs() {
        unCache();
        for (TransactionOutput output : outputs) {
            output.setParent(null);
        }
        outputs.clear();
        // You wanted to reserialize, right?
        this.length = this.bitcoinSerialize().length;
    }

    /**
     * Adds the given output to this transaction. The output must be completely initialized. Returns the given output.
     */
    public TransactionOutput addOutput(TransactionOutput to) {
        unCache();
        to.setParent(this);
        outputs.add(to);
        adjustLength(outputs.size(), to.length);
        return to;
    }

    /**
     * Creates an output based on the given address and value, adds it to this transaction, and returns the new output.
     */
    public TransactionOutput addOutput(Coin value, Address address) {
        return addOutput(new TransactionOutput(params, this, value, address));
    }

    /**
     * Creates an output that pays to the given pubkey directly (no address) with the given value, adds it to this
     * transaction, and returns the new output.
     */
    public TransactionOutput addOutput(Coin value, ECKey pubkey) {
        return addOutput(new TransactionOutput(params, this, value, pubkey));
    }

    /**
     * Creates an output that pays to the given script. The address and key forms are specialisations of this method,
     * you won't normally need to use it unless you're doing unusual things.
     */
    public TransactionOutput addOutput(Coin value, Script script) {
        return addOutput(new TransactionOutput(params, this, value, script.getProgram()));
    }


    /**
     * Calculates a signature that is valid for being inserted into the input at the given position. This is simply
     * a wrapper around calling {@link Transaction#hashForSignature(int, byte[], org.bitcoinj.core.Transaction.SigHash, boolean)}
     * followed by {@link ECKey#sign(Sha256Hash)} and then returning a new {@link TransactionSignature}. The key
     * must be usable for signing as-is: if the key is encrypted it must be decrypted first external to this method.
     *
     * @param inputIndex Which input to calculate the signature for, as an index.
     * @param key The private key used to calculate the signature.
     * @param redeemScript Byte-exact contents of the scriptPubKey that is being satisified, or the P2SH redeem script.
     * @param hashType Signing mode, see the enum for documentation.
     * @param anyoneCanPay Signing mode, see the SigHash enum for documentation.
     * @return A newly calculated signature object that wraps the r, s and sighash components.
     */
    public synchronized TransactionSignature calculateSignature(int inputIndex, ECKey key,
                                                                byte[] redeemScript,
                                                                SigHash hashType, boolean anyoneCanPay) {
        Sha256Hash hash = hashForSignature(inputIndex, redeemScript, hashType, anyoneCanPay);
        return new TransactionSignature(key.sign(hash), hashType, anyoneCanPay);
    }

    /**
     * Calculates a signature that is valid for being inserted into the input at the given position. This is simply
     * a wrapper around calling {@link Transaction#hashForSignature(int, byte[], org.bitcoinj.core.Transaction.SigHash, boolean)}
     * followed by {@link ECKey#sign(Sha256Hash)} and then returning a new {@link TransactionSignature}.
     *
     * @param inputIndex Which input to calculate the signature for, as an index.
     * @param key The private key used to calculate the signature.
     * @param redeemScript The scriptPubKey that is being satisified, or the P2SH redeem script.
     * @param hashType Signing mode, see the enum for documentation.
     * @param anyoneCanPay Signing mode, see the SigHash enum for documentation.
     * @return A newly calculated signature object that wraps the r, s and sighash components.
     */
    public synchronized  TransactionSignature calculateSignature(int inputIndex, ECKey key,
                                                                 Script redeemScript,
                                                                 SigHash hashType, boolean anyoneCanPay) {
        Sha256Hash hash = hashForSignature(inputIndex, redeemScript.getProgram(), hashType, anyoneCanPay);
        return new TransactionSignature(key.sign(hash), hashType, anyoneCanPay);
    }

    /**
     * <p>Calculates a signature hash, that is, a hash of a simplified form of the transaction. How exactly the transaction
     * is simplified is specified by the type and anyoneCanPay parameters.</p>
     *
     * <p>This is a low level API and when using the regular {@link Wallet} class you don't have to call this yourself.
     * When working with more complex transaction types and contracts, it can be necessary. When signing a P2SH output
     * the redeemScript should be the script encoded into the scriptSig field, for normal transactions, it's the
     * scriptPubKey of the output you're signing for.</p>
     *
     * @param inputIndex input the signature is being calculated for. Tx signatures are always relative to an input.
     * @param redeemScript the bytes that should be in the given input during signing.
     * @param type Should be SigHash.ALL
     * @param anyoneCanPay should be false.
     */
    public synchronized Sha256Hash hashForSignature(int inputIndex, byte[] redeemScript,
                                                    SigHash type, boolean anyoneCanPay) {
        byte sigHashType = (byte) TransactionSignature.calcSigHashValue(type, anyoneCanPay);
        return hashForSignature(inputIndex, redeemScript, sigHashType);
    }

    /**
     * <p>Calculates a signature hash, that is, a hash of a simplified form of the transaction. How exactly the transaction
     * is simplified is specified by the type and anyoneCanPay parameters.</p>
     *
     * <p>This is a low level API and when using the regular {@link Wallet} class you don't have to call this yourself.
     * When working with more complex transaction types and contracts, it can be necessary. When signing a P2SH output
     * the redeemScript should be the script encoded into the scriptSig field, for normal transactions, it's the
     * scriptPubKey of the output you're signing for.</p>
     *
     * @param inputIndex input the signature is being calculated for. Tx signatures are always relative to an input.
     * @param redeemScript the script that should be in the given input during signing.
     * @param type Should be SigHash.ALL
     * @param anyoneCanPay should be false.
     */
    public synchronized Sha256Hash hashForSignature(int inputIndex, Script redeemScript,
                                                    SigHash type, boolean anyoneCanPay) {
        int sigHash = TransactionSignature.calcSigHashValue(type, anyoneCanPay);
        return hashForSignature(inputIndex, redeemScript.getProgram(), (byte) sigHash);
    }

    /**
     * This is required for signatures which use a sigHashType which cannot be represented using SigHash and anyoneCanPay
     * See transaction c99c49da4c38af669dea436d3e73780dfdb6c1ecf9958baa52960e8baee30e73, which has sigHashType 0
     */
    public synchronized Sha256Hash hashForSignature(int inputIndex, byte[] connectedScript, byte sigHashType) {
        // The SIGHASH flags are used in the design of contracts, please see this page for a further understanding of
        // the purposes of the code in this method:
        //
        //   https://en.bitcoin.it/wiki/Contracts

        try {
            // Store all the input scripts and clear them in preparation for signing. If we're signing a fresh
            // transaction that step isn't very helpful, but it doesn't add much cost relative to the actual
            // EC math so we'll do it anyway.
            //
            // Also store the input sequence numbers in case we are clearing them with SigHash.NONE/SINGLE
            byte[][] inputScripts = new byte[inputs.size()][];
            long[] inputSequenceNumbers = new long[inputs.size()];
            for (int i = 0; i < inputs.size(); i++) {
                inputScripts[i] = inputs.get(i).getScriptBytes();
                inputSequenceNumbers[i] = inputs.get(i).getSequenceNumber();
                inputs.get(i).setScriptBytes(TransactionInput.EMPTY_ARRAY);
            }

            // This step has no purpose beyond being synchronized with the reference clients bugs. OP_CODESEPARATOR
            // is a legacy holdover from a previous, broken design of executing scripts that shipped in Bitcoin 0.1.
            // It was seriously flawed and would have let anyone take anyone elses money. Later versions switched to
            // the design we use today where scripts are executed independently but share a stack. This left the
            // OP_CODESEPARATOR instruction having no purpose as it was only meant to be used internally, not actually
            // ever put into scripts. Deleting OP_CODESEPARATOR is a step that should never be required but if we don't
            // do it, we could split off the main chain.
            connectedScript = Script.removeAllInstancesOfOp(connectedScript, ScriptOpCodes.OP_CODESEPARATOR);

            // Set the input to the script of its output. Satoshi does this but the step has no obvious purpose as
            // the signature covers the hash of the prevout transaction which obviously includes the output script
            // already. Perhaps it felt safer to him in some way, or is another leftover from how the code was written.
            TransactionInput input = inputs.get(inputIndex);
            input.setScriptBytes(connectedScript);

            ArrayList<TransactionOutput> outputs = this.outputs;
            if ((sigHashType & 0x1f) == (SigHash.NONE.ordinal() + 1)) {
                // SIGHASH_NONE means no outputs are signed at all - the signature is effectively for a "blank cheque".
                this.outputs = new ArrayList<TransactionOutput>(0);
                // The signature isn't broken by new versions of the transaction issued by other parties.
                for (int i = 0; i < inputs.size(); i++)
                    if (i != inputIndex)
                        inputs.get(i).setSequenceNumber(0);
            } else if ((sigHashType & 0x1f) == (SigHash.SINGLE.ordinal() + 1)) {
                // SIGHASH_SINGLE means only sign the output at the same index as the input (ie, my output).
                if (inputIndex >= this.outputs.size()) {
                    // The input index is beyond the number of outputs, it's a buggy signature made by a broken
                    // Bitcoin implementation. The reference client also contains a bug in handling this case:
                    // any transaction output that is signed in this case will result in both the signed output
                    // and any future outputs to this public key being steal-able by anyone who has
                    // the resulting signature and the public key (both of which are part of the signed tx input).
                    // Put the transaction back to how we found it.
                    //
                    // TODO: Only allow this to happen if we are checking a signature, not signing a transactions
                    for (int i = 0; i < inputs.size(); i++) {
                        inputs.get(i).setScriptBytes(inputScripts[i]);
                        inputs.get(i).setSequenceNumber(inputSequenceNumbers[i]);
                    }
                    this.outputs = outputs;
                    // Satoshis bug is that SignatureHash was supposed to return a hash and on this codepath it
                    // actually returns the constant "1" to indicate an error, which is never checked for. Oops.
                    return new Sha256Hash("0100000000000000000000000000000000000000000000000000000000000000");
                }
                // In SIGHASH_SINGLE the outputs after the matching input index are deleted, and the outputs before
                // that position are "nulled out". Unintuitively, the value in a "null" transaction is set to -1.
                this.outputs = new ArrayList<TransactionOutput>(this.outputs.subList(0, inputIndex + 1));
                for (int i = 0; i < inputIndex; i++)
                    this.outputs.set(i, new TransactionOutput(params, this, Coin.NEGATIVE_SATOSHI, new byte[] {}));
                // The signature isn't broken by new versions of the transaction issued by other parties.
                for (int i = 0; i < inputs.size(); i++)
                    if (i != inputIndex)
                        inputs.get(i).setSequenceNumber(0);
            }

            ArrayList<TransactionInput> inputs = this.inputs;
            if ((sigHashType & SIGHASH_ANYONECANPAY_VALUE) == SIGHASH_ANYONECANPAY_VALUE) {
                // SIGHASH_ANYONECANPAY means the signature in the input is not broken by changes/additions/removals
                // of other inputs. For example, this is useful for building assurance contracts.
                this.inputs = new ArrayList<TransactionInput>();
                this.inputs.add(input);
            }

            ByteArrayOutputStream bos = new UnsafeByteArrayOutputStream(length == UNKNOWN_LENGTH ? 256 : length + 4);
            bitcoinSerialize(bos);
            // We also have to write a hash type (sigHashType is actually an unsigned char)
            uint32ToByteStreamLE(0x000000ff & sigHashType, bos);
            // Note that this is NOT reversed to ensure it will be signed correctly. If it were to be printed out
            // however then we would expect that it is IS reversed.
            Sha256Hash hash = new Sha256Hash(doubleDigest(bos.toByteArray()));
            bos.close();

            // Put the transaction back to how we found it.
            this.inputs = inputs;
            for (int i = 0; i < inputs.size(); i++) {
                inputs.get(i).setScriptBytes(inputScripts[i]);
                inputs.get(i).setSequenceNumber(inputSequenceNumbers[i]);
            }
            this.outputs = outputs;
            return hash;
        } catch (IOException e) {
            throw new RuntimeException(e);  // Cannot happen.
        }
    }

    @Override
    protected void bitcoinSerializeToStream(OutputStream stream) throws IOException {
        uint32ToByteStreamLE(version, stream);
        stream.write(new VarInt(inputs.size()).encode());
        for (TransactionInput in : inputs)
            in.bitcoinSerialize(stream);
        stream.write(new VarInt(outputs.size()).encode());
        for (TransactionOutput out : outputs)
            out.bitcoinSerialize(stream);
        uint32ToByteStreamLE(lockTime, stream);
    }


    /**
     * Transactions can have an associated lock time, specified either as a block height or in seconds since the
     * UNIX epoch. A transaction is not allowed to be confirmed by miners until the lock time is reached, and
     * since Bitcoin 0.8+ a transaction that did not end its lock period (non final) is considered to be non
     * standard and won't be relayed or included in the memory pool either.
     */
    public long getLockTime() {
        maybeParse();
        return lockTime;
    }

    /**
     * Transactions can have an associated lock time, specified either as a block height or in seconds since the
     * UNIX epoch. A transaction is not allowed to be confirmed by miners until the lock time is reached, and
     * since Bitcoin 0.8+ a transaction that did not end its lock period (non final) is considered to be non
     * standard and won't be relayed or included in the memory pool either.
     */
    public void setLockTime(long lockTime) {
        unCache();
        boolean seqNumSet = false;
        for (TransactionInput input : inputs) {
            if (input.getSequenceNumber() != TransactionInput.NO_SEQUENCE) {
                seqNumSet = true;
                break;
            }
        }
        if (!seqNumSet || inputs.isEmpty()) {
            // At least one input must have a non-default sequence number for lock times to have any effect.
            // For instance one of them can be set to zero to make this feature work.
            log.warn("You are setting the lock time on a transaction but none of the inputs have non-default sequence numbers. This will not do what you expect!");
        }
        this.lockTime = lockTime;
    }

    /**
     * @return the version
     */
    public long getVersion() {
        maybeParse();
        return version;
    }

    /** Returns an unmodifiable view of all inputs. */
    public List<TransactionInput> getInputs() {
        maybeParse();
        return Collections.unmodifiableList(inputs);
    }

    /** Returns an unmodifiable view of all outputs. */
    public List<TransactionOutput> getOutputs() {
        maybeParse();
        return Collections.unmodifiableList(outputs);
    }

    /**
     * <p>Returns the list of transacion outputs, whether spent or unspent, that match a wallet by address or that are
     * watched by a wallet, i.e., transaction outputs whose script's address is controlled by the wallet and transaction
     * outputs whose script is watched by the wallet.</p>
     *
     * @param transactionBag The wallet that controls addresses and watches scripts.
     * @return linked list of outputs relevant to the wallet in this transaction
     */
    public List<TransactionOutput> getWalletOutputs(TransactionBag transactionBag){
        maybeParse();
        List<TransactionOutput> walletOutputs = new LinkedList<TransactionOutput>();
        for (TransactionOutput o : outputs) {
            if (!o.isMineOrWatched(transactionBag)) continue;
            walletOutputs.add(o);
        }

        return walletOutputs;
    }

    /** Randomly re-orders the transaction outputs: good for privacy */
    public void shuffleOutputs() {
        maybeParse();
        Collections.shuffle(outputs);
    }

    /** Same as getInputs().get(index). */
    public TransactionInput getInput(long index) {
        maybeParse();
        return inputs.get((int)index);
    }

    /** Same as getOutputs().get(index) */
    public TransactionOutput getOutput(long index) {
        maybeParse();
        return outputs.get((int)index);
    }

    /**
     * Returns the confidence object for this transaction from the {@link org.bitcoinj.core.TxConfidenceTable}
     * referenced by the implicit {@link Context}.
     */
    public TransactionConfidence getConfidence() {
        return getConfidence(Context.get());
    }

    /**
     * Returns the confidence object for this transaction from the {@link org.bitcoinj.core.TxConfidenceTable}
     * referenced by the given {@link Context}.
     */
    public TransactionConfidence getConfidence(Context context) {
        return getConfidence(context.getConfidenceTable());
    }

    /**
     * Returns the confidence object for this transaction from the {@link org.bitcoinj.core.TxConfidenceTable}
     */
    public TransactionConfidence getConfidence(TxConfidenceTable table) {
        if (confidence == null)
            confidence = table.getOrCreate(getHash()) ;
        return confidence;
    }

    /** Check if the transaction has a known confidence */
    public boolean hasConfidence() {
        return getConfidence().getConfidenceType() != TransactionConfidence.ConfidenceType.UNKNOWN;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Transaction other = (Transaction) o;
        return getHash().equals(other.getHash());
    }

    @Override
    public int hashCode() {
        return getHash().hashCode();
    }

    /**
     * Ensure object is fully parsed before invoking java serialization.  The backing byte array
     * is transient so if the object has parseLazy = true and hasn't invoked checkParse yet
     * then data will be lost during serialization.
     */
    private void writeObject(ObjectOutputStream out) throws IOException {
        maybeParse();
        out.defaultWriteObject();
    }

    /**
     * Gets the count of regular SigOps in this transactions
     */
    public int getSigOpCount() throws ScriptException {
        maybeParse();
        int sigOps = 0;
        for (TransactionInput input : inputs)
            sigOps += Script.getSigOpCount(input.getScriptBytes());
        for (TransactionOutput output : outputs)
            sigOps += Script.getSigOpCount(output.getScriptBytes());
        return sigOps;
    }

    /**
     * <p>Checks the transaction contents for sanity, in ways that can be done in a standalone manner.
     * Does <b>not</b> perform all checks on a transaction such as whether the inputs are already spent.
     * Specifically this method verifies:</p>
     *
     * <ul>
     *     <li>That there is at least one input and output.</li>
     *     <li>That the serialized size is not larger than the max block size.</li>
     *     <li>That no outputs have negative value.</li>
     *     <li>That the outputs do not sum to larger than the max allowed quantity of coin in the system.</li>
     *     <li>If the tx is a coinbase tx, the coinbase scriptSig size is within range. Otherwise that there are no
     *     coinbase inputs in the tx.</li>
     * </ul>
     *
     * @throws VerificationException
     */
    public void verify() throws VerificationException {
        maybeParse();
        if (inputs.size() == 0 || outputs.size() == 0)
            throw new VerificationException.EmptyInputsOrOutputs();
        if (this.getMessageSize() > Block.MAX_BLOCK_SIZE)
            throw new VerificationException.LargerThanMaxBlockSize();

        Coin valueOut = Coin.ZERO;
        HashSet<TransactionOutPoint> outpoints = new HashSet<TransactionOutPoint>();
        for (TransactionInput input : inputs) {
            if (outpoints.contains(input.getOutpoint()))
                throw new VerificationException.DuplicatedOutPoint();
            outpoints.add(input.getOutpoint());
        }
        try {
            for (TransactionOutput output : outputs) {
                if (output.getValue().signum() < 0)    // getValue() can throw IllegalStateException
                    throw new VerificationException.NegativeValueOutput();
                valueOut = valueOut.add(output.getValue());
                // Duplicate the MAX_MONEY check from Coin.add() in case someone accidentally removes it.
                if (valueOut.compareTo(NetworkParameters.MAX_MONEY) > 0)
                    throw new IllegalArgumentException();
            }
        } catch (IllegalStateException e) {
            throw new VerificationException.ExcessiveValue();
        } catch (IllegalArgumentException e) {
            throw new VerificationException.ExcessiveValue();
        }

        if (isCoinBase()) {
            if (inputs.get(0).getScriptBytes().length < 2 || inputs.get(0).getScriptBytes().length > 100)
                throw new VerificationException.CoinbaseScriptSizeOutOfRange();
        } else {
            for (TransactionInput input : inputs)
                if (input.isCoinBase())
                    throw new VerificationException.UnexpectedCoinbaseInput();
        }
    }

    /**
     * <p>A transaction is time locked if at least one of its inputs is non-final and it has a lock time</p>
     *
     * <p>To check if this transaction is final at a given height and time, see {@link Transaction#isFinal(int, long)}
     * </p>
     */
    public boolean isTimeLocked() {
        if (getLockTime() == 0)
            return false;
        for (TransactionInput input : getInputs())
            if (input.hasSequence())
                return true;
        return false;
    }

    /**
     * <p>Returns true if this transaction is considered finalized and can be placed in a block. Non-finalized
     * transactions won't be included by miners and can be replaced with newer versions using sequence numbers.
     * This is useful in certain types of <a href="http://en.bitcoin.it/wiki/Contracts">contracts</a>, such as
     * micropayment channels.</p>
     *
     * <p>Note that currently the replacement feature is disabled in the Satoshi client and will need to be
     * re-activated before this functionality is useful.</p>
     */
    public boolean isFinal(int height, long blockTimeSeconds) {
        long time = getLockTime();
        if (time < (time < LOCKTIME_THRESHOLD ? height : blockTimeSeconds))
            return true;
        if (!isTimeLocked())
            return true;
        return false;
    }

    /**
     * Returns either the lock time as a date, if it was specified in seconds, or an estimate based on the time in
     * the current head block if it was specified as a block time.
     */
    public Date estimateLockTime(AbstractBlockChain chain) {
        if (lockTime < LOCKTIME_THRESHOLD)
            return chain.estimateBlockTime((int)getLockTime());
        else
            return new Date(getLockTime()*1000);
    }

    /**
     * Returns the purpose for which this transaction was created. See the javadoc for {@link Purpose} for more
     * information on the point of this field and what it can be.
     */
    public Purpose getPurpose() {
        return purpose;
    }

    /**
     * Marks the transaction as being created for the given purpose. See the javadoc for {@link Purpose} for more
     * information on the point of this field and what it can be.
     */
    public void setPurpose(Purpose purpose) {
        this.purpose = purpose;
    }

    /**
     * Getter for {@link #exchangeRate}.
     */
    @Nullable
    public ExchangeRate getExchangeRate() {
        return exchangeRate;
    }

    /**
     * Setter for {@link #exchangeRate}.
     */
    public void setExchangeRate(ExchangeRate exchangeRate) {
        this.exchangeRate = exchangeRate;
    }

    /**
     * Returns the transaction {@link #memo}.
     */
    public String getMemo() {
        return memo;
    }

    /**
     * Set the transaction {@link #memo}. It can be used to record the memo of the payment request that initiated the
     * transaction.
     */
    public void setMemo(String memo) {
        this.memo = memo;
    }
}


File: core/src/main/java/org/bitcoinj/core/Utils.java
/**
 * Copyright 2011 Google Inc.
 * Copyright 2014 Andreas Schildbach
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.core;

import com.google.common.base.Charsets;
import com.google.common.base.Joiner;
import com.google.common.collect.Lists;
import com.google.common.collect.Ordering;
import com.google.common.io.BaseEncoding;
import com.google.common.io.Resources;
import com.google.common.primitives.Ints;
import com.google.common.primitives.UnsignedLongs;
import org.spongycastle.crypto.digests.RIPEMD160Digest;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.math.BigInteger;
import java.net.URL;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.text.DateFormat;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.TimeUnit;

import static com.google.common.base.Preconditions.checkArgument;
import static com.google.common.util.concurrent.Uninterruptibles.sleepUninterruptibly;

/**
 * A collection of various utility methods that are helpful for working with the Bitcoin protocol.
 * To enable debug logging from the library, run with -Dbitcoinj.logging=true on your command line.
 */
public class Utils {
    private static final MessageDigest digest = newSha256Digest();

    /** The string that prefixes all text messages signed using Bitcoin keys. */
    public static final String BITCOIN_SIGNED_MESSAGE_HEADER = "Bitcoin Signed Message:\n";
    public static final byte[] BITCOIN_SIGNED_MESSAGE_HEADER_BYTES = BITCOIN_SIGNED_MESSAGE_HEADER.getBytes(Charsets.UTF_8);

    private static BlockingQueue<Boolean> mockSleepQueue;

    /**
     * Returns a new SHA-256 MessageDigest instance.
     *
     * This is a convenience method which wraps the checked
     * exception that can never occur with a RuntimeException.
     *
     * @return a new SHA-256 MessageDigest instance
     */
    public static MessageDigest newSha256Digest() {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);  // Can't happen.
        }
    }

    /**
     * The regular {@link java.math.BigInteger#toByteArray()} method isn't quite what we often need: it appends a
     * leading zero to indicate that the number is positive and may need padding.
     *
     * @param b the integer to format into a byte array
     * @param numBytes the desired size of the resulting byte array
     * @return numBytes byte long array.
     */
    public static byte[] bigIntegerToBytes(BigInteger b, int numBytes) {
        if (b == null) {
            return null;
        }
        byte[] bytes = new byte[numBytes];
        byte[] biBytes = b.toByteArray();
        int start = (biBytes.length == numBytes + 1) ? 1 : 0;
        int length = Math.min(biBytes.length, numBytes);
        System.arraycopy(biBytes, start, bytes, numBytes - length, length);
        return bytes;        
    }

    public static void uint32ToByteArrayBE(long val, byte[] out, int offset) {
        out[offset + 0] = (byte) (0xFF & (val >> 24));
        out[offset + 1] = (byte) (0xFF & (val >> 16));
        out[offset + 2] = (byte) (0xFF & (val >> 8));
        out[offset + 3] = (byte) (0xFF & (val >> 0));
    }

    public static void uint32ToByteArrayLE(long val, byte[] out, int offset) {
        out[offset + 0] = (byte) (0xFF & (val >> 0));
        out[offset + 1] = (byte) (0xFF & (val >> 8));
        out[offset + 2] = (byte) (0xFF & (val >> 16));
        out[offset + 3] = (byte) (0xFF & (val >> 24));
    }

    public static void uint64ToByteArrayLE(long val, byte[] out, int offset) {
        out[offset + 0] = (byte) (0xFF & (val >> 0));
        out[offset + 1] = (byte) (0xFF & (val >> 8));
        out[offset + 2] = (byte) (0xFF & (val >> 16));
        out[offset + 3] = (byte) (0xFF & (val >> 24));
        out[offset + 4] = (byte) (0xFF & (val >> 32));
        out[offset + 5] = (byte) (0xFF & (val >> 40));
        out[offset + 6] = (byte) (0xFF & (val >> 48));
        out[offset + 7] = (byte) (0xFF & (val >> 56));
    }

    public static void uint32ToByteStreamLE(long val, OutputStream stream) throws IOException {
        stream.write((int) (0xFF & (val >> 0)));
        stream.write((int) (0xFF & (val >> 8)));
        stream.write((int) (0xFF & (val >> 16)));
        stream.write((int) (0xFF & (val >> 24)));
    }
    
    public static void int64ToByteStreamLE(long val, OutputStream stream) throws IOException {
        stream.write((int) (0xFF & (val >> 0)));
        stream.write((int) (0xFF & (val >> 8)));
        stream.write((int) (0xFF & (val >> 16)));
        stream.write((int) (0xFF & (val >> 24)));
        stream.write((int) (0xFF & (val >> 32)));
        stream.write((int) (0xFF & (val >> 40)));
        stream.write((int) (0xFF & (val >> 48)));
        stream.write((int) (0xFF & (val >> 56)));
    }

    public static void uint64ToByteStreamLE(BigInteger val, OutputStream stream) throws IOException {
        byte[] bytes = val.toByteArray();
        if (bytes.length > 8) {
            throw new RuntimeException("Input too large to encode into a uint64");
        }
        bytes = reverseBytes(bytes);
        stream.write(bytes);
        if (bytes.length < 8) {
            for (int i = 0; i < 8 - bytes.length; i++)
                stream.write(0);
        }
    }

    /**
     * Calculates the SHA-256 hash of the given bytes,
     * and then hashes the resulting hash again.
     *
     * @param input the bytes to hash
     * @return the double-hash (in big-endian order)
     */
    public static byte[] doubleDigest(byte[] input) {
        return doubleDigest(input, 0, input.length);
    }

    /**
     * Calculates the SHA-256 hash of the given byte range,
     * and then hashes the resulting hash again.
     *
     * @param input the array containing the bytes to hash
     * @param offset the offset within the array of the bytes to hash
     * @param length the number of bytes to hash
     * @return the double-hash (in big-endian order)
     */
    public static byte[] doubleDigest(byte[] input, int offset, int length) {
        synchronized (digest) {
            digest.reset();
            digest.update(input, offset, length);
            byte[] first = digest.digest();
            return digest.digest(first);
        }
    }

    /**
     * Calculates the SHA-256 hash of the given bytes.
     *
     * @param input the bytes to hash
     * @return the hash (in big-endian order)
     */
    public static byte[] singleDigest(byte[] input) {
        return singleDigest(input, 0, input.length);
    }

    /**
     * Calculates the SHA-256 hash of the given byte range.
     *
     * @param input the array containing the bytes to hash
     * @param offset the offset within the array of the bytes to hash
     * @param length the number of bytes to hash
     * @return the hash (in big-endian order)
     */
    public static byte[] singleDigest(byte[] input, int offset, int length) {
        MessageDigest digest = newSha256Digest();
        digest.update(input, offset, length);
        return digest.digest();
    }

    /**
     * Calculates SHA256(SHA256(byte range 1 + byte range 2)).
     */
    public static byte[] doubleDigestTwoBuffers(byte[] input1, int offset1, int length1,
                                                byte[] input2, int offset2, int length2) {
        synchronized (digest) {
            digest.reset();
            digest.update(input1, offset1, length1);
            digest.update(input2, offset2, length2);
            byte[] first = digest.digest();
            return digest.digest(first);
        }
    }

    /**
     * Work around lack of unsigned types in Java.
     */
    public static boolean isLessThanUnsigned(long n1, long n2) {
        return UnsignedLongs.compare(n1, n2) < 0;
    }

    /**
     * Work around lack of unsigned types in Java.
     */
    public static boolean isLessThanOrEqualToUnsigned(long n1, long n2) {
        return UnsignedLongs.compare(n1, n2) <= 0;
    }

    /**
     * Hex encoding used throughout the framework. Use with HEX.encode(byte[]) or HEX.decode(CharSequence).
     */
    public static final BaseEncoding HEX = BaseEncoding.base16().lowerCase();

    /**
     * Returns a copy of the given byte array in reverse order.
     */
    public static byte[] reverseBytes(byte[] bytes) {
        // We could use the XOR trick here but it's easier to understand if we don't. If we find this is really a
        // performance issue the matter can be revisited.
        byte[] buf = new byte[bytes.length];
        for (int i = 0; i < bytes.length; i++)
            buf[i] = bytes[bytes.length - 1 - i];
        return buf;
    }
    
    /**
     * Returns a copy of the given byte array with the bytes of each double-word (4 bytes) reversed.
     * 
     * @param bytes length must be divisible by 4.
     * @param trimLength trim output to this length.  If positive, must be divisible by 4.
     */
    public static byte[] reverseDwordBytes(byte[] bytes, int trimLength) {
        checkArgument(bytes.length % 4 == 0);
        checkArgument(trimLength < 0 || trimLength % 4 == 0);
        
        byte[] rev = new byte[trimLength >= 0 && bytes.length > trimLength ? trimLength : bytes.length];
        
        for (int i = 0; i < rev.length; i += 4) {
            System.arraycopy(bytes, i, rev, i , 4);
            for (int j = 0; j < 4; j++) {
                rev[i + j] = bytes[i + 3 - j];
            }
        }
        return rev;
}

    public static long readUint32(byte[] bytes, int offset) {
        return ((bytes[offset++] & 0xFFL) << 0) |
                ((bytes[offset++] & 0xFFL) << 8) |
                ((bytes[offset++] & 0xFFL) << 16) |
                ((bytes[offset] & 0xFFL) << 24);
    }
    
    public static long readInt64(byte[] bytes, int offset) {
        return ((bytes[offset++] & 0xFFL) << 0) |
               ((bytes[offset++] & 0xFFL) << 8) |
               ((bytes[offset++] & 0xFFL) << 16) |
               ((bytes[offset++] & 0xFFL) << 24) |
               ((bytes[offset++] & 0xFFL) << 32) |
               ((bytes[offset++] & 0xFFL) << 40) |
               ((bytes[offset++] & 0xFFL) << 48) |
               ((bytes[offset] & 0xFFL) << 56);
    }

    public static long readUint32BE(byte[] bytes, int offset) {
        return ((bytes[offset + 0] & 0xFFL) << 24) |
                ((bytes[offset + 1] & 0xFFL) << 16) |
                ((bytes[offset + 2] & 0xFFL) << 8) |
                ((bytes[offset + 3] & 0xFFL) << 0);
    }

    public static int readUint16BE(byte[] bytes, int offset) {
        return ((bytes[offset] & 0xff) << 8) | bytes[offset + 1] & 0xff;
    }

    /**
     * Calculates RIPEMD160(SHA256(input)). This is used in Address calculations.
     */
    public static byte[] sha256hash160(byte[] input) {
        byte[] sha256 = singleDigest(input);
        RIPEMD160Digest digest = new RIPEMD160Digest();
        digest.update(sha256, 0, sha256.length);
        byte[] out = new byte[20];
        digest.doFinal(out, 0);
        return out;
    }

    /**
     * MPI encoded numbers are produced by the OpenSSL BN_bn2mpi function. They consist of
     * a 4 byte big endian length field, followed by the stated number of bytes representing
     * the number in big endian format (with a sign bit).
     * @param hasLength can be set to false if the given array is missing the 4 byte length field
     */
    public static BigInteger decodeMPI(byte[] mpi, boolean hasLength) {
        byte[] buf;
        if (hasLength) {
            int length = (int) readUint32BE(mpi, 0);
            buf = new byte[length];
            System.arraycopy(mpi, 4, buf, 0, length);
        } else
            buf = mpi;
        if (buf.length == 0)
            return BigInteger.ZERO;
        boolean isNegative = (buf[0] & 0x80) == 0x80;
        if (isNegative)
            buf[0] &= 0x7f;
        BigInteger result = new BigInteger(buf);
        return isNegative ? result.negate() : result;
    }
    
    /**
     * MPI encoded numbers are produced by the OpenSSL BN_bn2mpi function. They consist of
     * a 4 byte big endian length field, followed by the stated number of bytes representing
     * the number in big endian format (with a sign bit).
     * @param includeLength indicates whether the 4 byte length field should be included
     */
    public static byte[] encodeMPI(BigInteger value, boolean includeLength) {
        if (value.equals(BigInteger.ZERO)) {
            if (!includeLength)
                return new byte[] {};
            else
                return new byte[] {0x00, 0x00, 0x00, 0x00};
        }
        boolean isNegative = value.signum() < 0;
        if (isNegative)
            value = value.negate();
        byte[] array = value.toByteArray();
        int length = array.length;
        if ((array[0] & 0x80) == 0x80)
            length++;
        if (includeLength) {
            byte[] result = new byte[length + 4];
            System.arraycopy(array, 0, result, length - array.length + 3, array.length);
            uint32ToByteArrayBE(length, result, 0);
            if (isNegative)
                result[4] |= 0x80;
            return result;
        } else {
            byte[] result;
            if (length != array.length) {
                result = new byte[length];
                System.arraycopy(array, 0, result, 1, array.length);
            }else
                result = array;
            if (isNegative)
                result[0] |= 0x80;
            return result;
        }
    }

    /**
     * <p>The "compact" format is a representation of a whole number N using an unsigned 32 bit number similar to a
     * floating point format. The most significant 8 bits are the unsigned exponent of base 256. This exponent can
     * be thought of as "number of bytes of N". The lower 23 bits are the mantissa. Bit number 24 (0x800000) represents
     * the sign of N. Therefore, N = (-1^sign) * mantissa * 256^(exponent-3).</p>
     *
     * <p>Satoshi's original implementation used BN_bn2mpi() and BN_mpi2bn(). MPI uses the most significant bit of the
     * first byte as sign. Thus 0x1234560000 is compact 0x05123456 and 0xc0de000000 is compact 0x0600c0de. Compact
     * 0x05c0de00 would be -0x40de000000.</p>
     *
     * <p>Bitcoin only uses this "compact" format for encoding difficulty targets, which are unsigned 256bit quantities.
     * Thus, all the complexities of the sign bit and using base 256 are probably an implementation accident.</p>
     */
    public static BigInteger decodeCompactBits(long compact) {
        int size = ((int) (compact >> 24)) & 0xFF;
        byte[] bytes = new byte[4 + size];
        bytes[3] = (byte) size;
        if (size >= 1) bytes[4] = (byte) ((compact >> 16) & 0xFF);
        if (size >= 2) bytes[5] = (byte) ((compact >> 8) & 0xFF);
        if (size >= 3) bytes[6] = (byte) ((compact >> 0) & 0xFF);
        return decodeMPI(bytes, true);
    }

    /**
     * @see Utils#decodeCompactBits(long)
     */
    public static long encodeCompactBits(BigInteger value) {
        long result;
        int size = value.toByteArray().length;
        if (size <= 3)
            result = value.longValue() << 8 * (3 - size);
        else
            result = value.shiftRight(8 * (size - 3)).longValue();
        // The 0x00800000 bit denotes the sign.
        // Thus, if it is already set, divide the mantissa by 256 and increase the exponent.
        if ((result & 0x00800000L) != 0) {
            result >>= 8;
            size++;
        }
        result |= size << 24;
        result |= value.signum() == -1 ? 0x00800000 : 0;
        return result;
    }

    /**
     * If non-null, overrides the return value of now().
     */
    public static volatile Date mockTime;

    /**
     * Advances (or rewinds) the mock clock by the given number of seconds.
     */
    public static Date rollMockClock(int seconds) {
        return rollMockClockMillis(seconds * 1000);
    }

    /**
     * Advances (or rewinds) the mock clock by the given number of milliseconds.
     */
    public static Date rollMockClockMillis(long millis) {
        if (mockTime == null)
            throw new IllegalStateException("You need to use setMockClock() first.");
        mockTime = new Date(mockTime.getTime() + millis);
        return mockTime;
    }

    /**
     * Sets the mock clock to the current time.
     */
    public static void setMockClock() {
        mockTime = new Date();
    }

    /**
     * Sets the mock clock to the given time (in seconds).
     */
    public static void setMockClock(long mockClockSeconds) {
        mockTime = new Date(mockClockSeconds * 1000);
    }

    /**
     * Returns the current time, or a mocked out equivalent.
     */
    public static Date now() {
        if (mockTime != null)
            return mockTime;
        else
            return new Date();
    }

    // TODO: Replace usages of this where the result is / 1000 with currentTimeSeconds.
    /** Returns the current time in milliseconds since the epoch, or a mocked out equivalent. */
    public static long currentTimeMillis() {
        if (mockTime != null)
            return mockTime.getTime();
        else
            return System.currentTimeMillis();
    }

    public static long currentTimeSeconds() {
        return currentTimeMillis() / 1000;
    }

    private static final TimeZone UTC = TimeZone.getTimeZone("UTC");

    /**
     * Formats a given date+time value to an ISO 8601 string.
     * @param dateTime value to format, as a Date
     */
    public static String dateTimeFormat(Date dateTime) {
        DateFormat iso8601 = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US);
        iso8601.setTimeZone(UTC);
        return iso8601.format(dateTime);
    }

    /**
     * Formats a given date+time value to an ISO 8601 string.
     * @param dateTime value to format, unix time (ms)
     */
    public static String dateTimeFormat(long dateTime) {
        DateFormat iso8601 = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US);
        iso8601.setTimeZone(UTC);
        return iso8601.format(dateTime);
    }

    public static byte[] copyOf(byte[] in, int length) {
        byte[] out = new byte[length];
        System.arraycopy(in, 0, out, 0, Math.min(length, in.length));
        return out;
    }

    /**
     * Creates a copy of bytes and appends b to the end of it
     */
    public static byte[] appendByte(byte[] bytes, byte b) {
        byte[] result = Arrays.copyOf(bytes, bytes.length + 1);
        result[result.length - 1] = b;
        return result;
    }

    /**
     * Attempts to parse the given string as arbitrary-length hex or base58 and then return the results, or null if
     * neither parse was successful.
     */
    public static byte[] parseAsHexOrBase58(String data) {
        try {
            return HEX.decode(data);
        } catch (Exception e) {
            // Didn't decode as hex, try base58.
            try {
                return Base58.decodeChecked(data);
            } catch (AddressFormatException e1) {
                return null;
            }
        }
    }

    public static boolean isWindows() {
        return System.getProperty("os.name").toLowerCase().contains("win");
    }

    /**
     * <p>Given a textual message, returns a byte buffer formatted as follows:</p>
     *
     * <tt><p>[24] "Bitcoin Signed Message:\n" [message.length as a varint] message</p></tt>
     */
    public static byte[] formatMessageForSigning(String message) {
        try {
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            bos.write(BITCOIN_SIGNED_MESSAGE_HEADER_BYTES.length);
            bos.write(BITCOIN_SIGNED_MESSAGE_HEADER_BYTES);
            byte[] messageBytes = message.getBytes(Charsets.UTF_8);
            VarInt size = new VarInt(messageBytes.length);
            bos.write(size.encode());
            bos.write(messageBytes);
            return bos.toByteArray();
        } catch (IOException e) {
            throw new RuntimeException(e);  // Cannot happen.
        }
    }
    
    // 00000001, 00000010, 00000100, 00001000, ...
    private static final int bitMask[] = {0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80};
    
    /** Checks if the given bit is set in data, using little endian (not the same as Java native big endian) */
    public static boolean checkBitLE(byte[] data, int index) {
        return (data[index >>> 3] & bitMask[7 & index]) != 0;
    }
    
    /** Sets the given bit in data to one, using little endian (not the same as Java native big endian) */
    public static void setBitLE(byte[] data, int index) {
        data[index >>> 3] |= bitMask[7 & index];
    }

    /** Sleep for a span of time, or mock sleep if enabled */
    public static void sleep(long millis) {
        if (mockSleepQueue == null) {
            sleepUninterruptibly(millis, TimeUnit.MILLISECONDS);
        } else {
            try {
                boolean isMultiPass = mockSleepQueue.take();
                rollMockClockMillis(millis);
                if (isMultiPass)
                    mockSleepQueue.offer(true);
            } catch (InterruptedException e) {
                // Ignored.
            }
        }
    }

    /** Enable or disable mock sleep.  If enabled, set mock time to current time. */
    public static void setMockSleep(boolean isEnable) {
        if (isEnable) {
            mockSleepQueue = new ArrayBlockingQueue<Boolean>(1);
            mockTime = new Date(System.currentTimeMillis());
        } else {
            mockSleepQueue = null;
        }
    }

    /** Let sleeping thread pass the synchronization point.  */
    public static void passMockSleep() {
        mockSleepQueue.offer(false);
    }

    /** Let the sleeping thread pass the synchronization point any number of times. */
    public static void finishMockSleep() {
        if (mockSleepQueue != null) {
            mockSleepQueue.offer(true);
        }
    }

    private static int isAndroid = -1;
    public static boolean isAndroidRuntime() {
        if (isAndroid == -1) {
            final String runtime = System.getProperty("java.runtime.name");
            isAndroid = (runtime != null && runtime.equals("Android Runtime")) ? 1 : 0;
        }
        return isAndroid == 1;
    }

    private static class Pair implements Comparable<Pair> {
        int item, count;
        public Pair(int item, int count) { this.count = count; this.item = item; }
        @Override public int compareTo(Pair o) { return -Ints.compare(count, o.count); }
    }

    public static int maxOfMostFreq(int... items) {
        // Java 6 sucks.
        ArrayList<Integer> list = new ArrayList<Integer>(items.length);
        for (int item : items) list.add(item);
        return maxOfMostFreq(list);
    }

    public static int maxOfMostFreq(List<Integer> items) {
        if (items.isEmpty())
            return 0;
        // This would be much easier in a functional language (or in Java 8).
        items = Ordering.natural().reverse().sortedCopy(items);
        LinkedList<Pair> pairs = Lists.newLinkedList();
        pairs.add(new Pair(items.get(0), 0));
        for (int item : items) {
            Pair pair = pairs.getLast();
            if (pair.item != item)
                pairs.add((pair = new Pair(item, 0)));
            pair.count++;
        }
        // pairs now contains a uniqified list of the sorted inputs, with counts for how often that item appeared.
        // Now sort by how frequently they occur, and pick the max of the most frequent.
        Collections.sort(pairs);
        int maxCount = pairs.getFirst().count;
        int maxItem = pairs.getFirst().item;
        for (Pair pair : pairs) {
            if (pair.count != maxCount)
                break;
            maxItem = Math.max(maxItem, pair.item);
        }
        return maxItem;
    }

    /**
     * Reads and joins together with LF char (\n) all the lines from given file. It's assumed that file is in UTF-8.
     */
    public static String getResourceAsString(URL url) throws IOException {
        List<String> lines = Resources.readLines(url, Charsets.UTF_8);
        return Joiner.on('\n').join(lines);
    }

    // Can't use Closeable here because it's Java 7 only and Android devices only got that with KitKat.
    public static InputStream closeUnchecked(InputStream stream) {
        try {
            stream.close();
            return stream;
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    public static OutputStream closeUnchecked(OutputStream stream) {
        try {
            stream.close();
            return stream;
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }
}


File: core/src/main/java/org/bitcoinj/core/VersionedChecksummedBytes.java
/**
 * Copyright 2011 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.core;

import static com.google.common.base.Preconditions.checkArgument;

import java.io.Serializable;
import java.util.Arrays;

import com.google.common.base.Objects;
import com.google.common.primitives.UnsignedBytes;

/**
 * <p>In Bitcoin the following format is often used to represent some type of key:</p>
 * <p/>
 * <pre>[one version byte] [data bytes] [4 checksum bytes]</pre>
 * <p/>
 * <p>and the result is then Base58 encoded. This format is used for addresses, and private keys exported using the
 * dumpprivkey command.</p>
 */
public class VersionedChecksummedBytes implements Serializable, Cloneable, Comparable<VersionedChecksummedBytes> {
    protected final int version;
    protected byte[] bytes;

    protected VersionedChecksummedBytes(String encoded) throws AddressFormatException {
        byte[] versionAndDataBytes = Base58.decodeChecked(encoded);
        byte versionByte = versionAndDataBytes[0];
        version = versionByte & 0xFF;
        bytes = new byte[versionAndDataBytes.length - 1];
        System.arraycopy(versionAndDataBytes, 1, bytes, 0, versionAndDataBytes.length - 1);
    }

    protected VersionedChecksummedBytes(int version, byte[] bytes) {
        checkArgument(version >= 0 && version < 256);
        this.version = version;
        this.bytes = bytes;
    }

    /**
     * Returns the base-58 encoded String representation of this
     * object, including version and checksum bytes.
     */
    @Override
    public String toString() {
        // A stringified buffer is:
        //   1 byte version + data bytes + 4 bytes check code (a truncated hash)
        byte[] addressBytes = new byte[1 + bytes.length + 4];
        addressBytes[0] = (byte) version;
        System.arraycopy(bytes, 0, addressBytes, 1, bytes.length);
        byte[] checksum = Utils.doubleDigest(addressBytes, 0, bytes.length + 1);
        System.arraycopy(checksum, 0, addressBytes, bytes.length + 1, 4);
        return Base58.encode(addressBytes);
    }

    @Override
    public int hashCode() {
        return Objects.hashCode(version, Arrays.hashCode(bytes));
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        VersionedChecksummedBytes other = (VersionedChecksummedBytes) o;
        return this.version == other.version
                && Arrays.equals(this.bytes, other.bytes);
    }

    /**
     * {@inheritDoc}
     *
     * This implementation narrows the return type to <code>VersionedChecksummedBytes</code>
     * and allows subclasses to throw <code>CloneNotSupportedException</code> even though it
     * is never thrown by this implementation.
     */
    @Override
    public VersionedChecksummedBytes clone() throws CloneNotSupportedException {
        return (VersionedChecksummedBytes) super.clone();
    }

    /**
     * {@inheritDoc}
     *
     * This implementation uses an optimized Google Guava method to compare <code>bytes</code>.
     */
    @Override
    public int compareTo(VersionedChecksummedBytes o) {
        int versionCompare = Integer.valueOf(this.version).compareTo(Integer.valueOf(o.version));  // JDK 6 way
        if (versionCompare == 0) {
            // Would there be a performance benefit to caching the comparator?
            return UnsignedBytes.lexicographicalComparator().compare(this.bytes, o.bytes);
        } else {
            return versionCompare;
        }
    }

    /**
     * Returns the "version" or "header" byte: the first byte of the data. This is used to disambiguate what the
     * contents apply to, for example, which network the key or address is valid on.
     *
     * @return A positive number between 0 and 255.
     */
    public int getVersion() {
        return version;
    }
}


File: core/src/main/java/org/bitcoinj/crypto/BIP38PrivateKey.java
/*
 * Copyright 2014 Andreas Schildbach
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.crypto;

import org.bitcoinj.core.*;
import com.google.common.base.Charsets;
import com.google.common.base.Objects;
import com.google.common.primitives.Bytes;
import com.lambdaworks.crypto.SCrypt;

import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;
import java.math.BigInteger;
import java.security.GeneralSecurityException;
import java.text.Normalizer;
import java.util.Arrays;

import static com.google.common.base.Preconditions.checkState;

/**
 * Implementation of <a href="https://github.com/bitcoin/bips/blob/master/bip-0038.mediawiki">BIP 38</a>
 * passphrase-protected private keys. Currently, only decryption is supported.
 */
public class BIP38PrivateKey extends VersionedChecksummedBytes {

    public final NetworkParameters params;
    public final boolean ecMultiply;
    public final boolean compressed;
    public final boolean hasLotAndSequence;
    public final byte[] addressHash;
    public final byte[] content;

    public static final class BadPassphraseException extends Exception {
    }

    public BIP38PrivateKey(NetworkParameters params, String encoded) throws AddressFormatException {
        super(encoded);
        this.params = params;
        if (version != 0x01)
            throw new AddressFormatException("Mismatched version number: " + version);
        if (bytes.length != 38)
            throw new AddressFormatException("Wrong number of bytes, excluding version byte: " + bytes.length);
        hasLotAndSequence = (bytes[1] & 0x04) != 0; // bit 2
        compressed = (bytes[1] & 0x20) != 0; // bit 5
        if ((bytes[1] & 0x01) != 0) // bit 0
            throw new AddressFormatException("Bit 0x01 reserved for future use.");
        if ((bytes[1] & 0x02) != 0) // bit 1
            throw new AddressFormatException("Bit 0x02 reserved for future use.");
        if ((bytes[1] & 0x08) != 0) // bit 3
            throw new AddressFormatException("Bit 0x08 reserved for future use.");
        if ((bytes[1] & 0x10) != 0) // bit 4
            throw new AddressFormatException("Bit 0x10 reserved for future use.");
        final int byte0 = bytes[0] & 0xff;
        if (byte0 == 0x42) {
            // Non-EC-multiplied key
            if ((bytes[1] & 0xc0) != 0xc0) // bits 6+7
                throw new AddressFormatException("Bits 0x40 and 0x80 must be set for non-EC-multiplied keys.");
            ecMultiply = false;
            if (hasLotAndSequence)
                throw new AddressFormatException("Non-EC-multiplied keys cannot have lot/sequence.");
        } else if (byte0 == 0x43) {
            // EC-multiplied key
            if ((bytes[1] & 0xc0) != 0x00) // bits 6+7
                throw new AddressFormatException("Bits 0x40 and 0x80 must be cleared for EC-multiplied keys.");
            ecMultiply = true;
        } else {
            throw new AddressFormatException("Second byte must by 0x42 or 0x43.");
        }
        addressHash = Arrays.copyOfRange(bytes, 2, 6);
        content = Arrays.copyOfRange(bytes, 6, 38);
    }

    public ECKey decrypt(String passphrase) throws BadPassphraseException {
        String normalizedPassphrase = Normalizer.normalize(passphrase, Normalizer.Form.NFC);
        ECKey key = ecMultiply ? decryptEC(normalizedPassphrase) : decryptNoEC(normalizedPassphrase);
        Sha256Hash hash = Sha256Hash.hashTwice(key.toAddress(params).toString().getBytes(Charsets.US_ASCII));
        byte[] actualAddressHash = Arrays.copyOfRange(hash.getBytes(), 0, 4);
        if (!Arrays.equals(actualAddressHash, addressHash))
            throw new BadPassphraseException();
        return key;
    }

    private ECKey decryptNoEC(String normalizedPassphrase) {
        try {
            byte[] derived = SCrypt.scrypt(normalizedPassphrase.getBytes(Charsets.UTF_8), addressHash, 16384, 8, 8, 64);
            byte[] key = Arrays.copyOfRange(derived, 32, 64);
            SecretKeySpec keyspec = new SecretKeySpec(key, "AES");

            DRMWorkaround.maybeDisableExportControls();
            Cipher cipher = Cipher.getInstance("AES/ECB/NoPadding");

            cipher.init(Cipher.DECRYPT_MODE, keyspec);
            byte[] decrypted = cipher.doFinal(content, 0, 32);
            for (int i = 0; i < 32; i++)
                decrypted[i] ^= derived[i];
            return ECKey.fromPrivate(decrypted, compressed);
        } catch (GeneralSecurityException x) {
            throw new RuntimeException(x);
        }
    }

    private ECKey decryptEC(String normalizedPassphrase) {
        try {
            byte[] ownerEntropy = Arrays.copyOfRange(content, 0, 8);
            byte[] ownerSalt = hasLotAndSequence ? Arrays.copyOfRange(ownerEntropy, 0, 4) : ownerEntropy;

            byte[] passFactorBytes = SCrypt.scrypt(normalizedPassphrase.getBytes(Charsets.UTF_8), ownerSalt, 16384, 8, 8, 32);
            if (hasLotAndSequence) {
                byte[] hashBytes = Bytes.concat(passFactorBytes, ownerEntropy);
                checkState(hashBytes.length == 40);
                passFactorBytes = Utils.doubleDigest(hashBytes);
            }
            BigInteger passFactor = new BigInteger(1, passFactorBytes);
            ECKey k = ECKey.fromPrivate(passFactor, true);

            byte[] salt = Bytes.concat(addressHash, ownerEntropy);
            checkState(salt.length == 12);
            byte[] derived = SCrypt.scrypt(k.getPubKey(), salt, 1024, 1, 1, 64);
            byte[] aeskey = Arrays.copyOfRange(derived, 32, 64);

            SecretKeySpec keyspec = new SecretKeySpec(aeskey, "AES");
            Cipher cipher = Cipher.getInstance("AES/ECB/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, keyspec);

            byte[] encrypted2 = Arrays.copyOfRange(content, 16, 32);
            byte[] decrypted2 = cipher.doFinal(encrypted2);
            checkState(decrypted2.length == 16);
            for (int i = 0; i < 16; i++)
                decrypted2[i] ^= derived[i + 16];

            byte[] encrypted1 = Bytes.concat(Arrays.copyOfRange(content, 8, 16), Arrays.copyOfRange(decrypted2, 0, 8));
            byte[] decrypted1 = cipher.doFinal(encrypted1);
            checkState(decrypted1.length == 16);
            for (int i = 0; i < 16; i++)
                decrypted1[i] ^= derived[i];

            byte[] seed = Bytes.concat(decrypted1, Arrays.copyOfRange(decrypted2, 8, 16));
            checkState(seed.length == 24);
            BigInteger seedFactor = new BigInteger(1, Utils.doubleDigest(seed));
            checkState(passFactor.signum() >= 0);
            checkState(seedFactor.signum() >= 0);
            BigInteger priv = passFactor.multiply(seedFactor).mod(ECKey.CURVE.getN());

            return ECKey.fromPrivate(priv, compressed);
        } catch (GeneralSecurityException x) {
            throw new RuntimeException(x);
        }
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        BIP38PrivateKey other = (BIP38PrivateKey) o;

        return super.equals(other)
                && Objects.equal(this.params, other.params);
    }

    @Override
    public int hashCode() {
        return Objects.hashCode(super.hashCode(), params);
    }
}


File: core/src/main/java/org/bitcoinj/crypto/DeterministicKey.java
/**
 * Copyright 2013 Matija Mazi.
 * Copyright 2014 Andreas Schildbach
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.bitcoinj.crypto;

import org.bitcoinj.core.*;
import com.google.common.base.Objects;
import com.google.common.base.Objects.ToStringHelper;
import com.google.common.collect.ImmutableList;
import org.spongycastle.crypto.params.KeyParameter;
import org.spongycastle.math.ec.ECPoint;

import javax.annotation.Nullable;
import java.math.BigInteger;
import java.nio.ByteBuffer;
import java.util.Arrays;
import java.util.Comparator;

import static org.bitcoinj.core.Utils.HEX;
import static com.google.common.base.Preconditions.*;

/**
 * A deterministic key is a node in a {@link DeterministicHierarchy}. As per
 * <a href="https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki">the BIP 32 specification</a> it is a pair
 * (key, chaincode). If you know its path in the tree and its chain code you can derive more keys from this. To obtain
 * one of these, you can call {@link HDKeyDerivation#createMasterPrivateKey(byte[])}.
 */
public class DeterministicKey extends ECKey {

    /** Sorts deterministic keys in the order of their child number. That's <i>usually</i> the order used to derive them. */
    public static final Comparator<ECKey> CHILDNUM_ORDER = new Comparator<ECKey>() {
        @Override
        public int compare(ECKey k1, ECKey k2) {
            ChildNumber cn1 = ((DeterministicKey) k1).getChildNumber();
            ChildNumber cn2 = ((DeterministicKey) k2).getChildNumber();
            return cn1.compareTo(cn2);
        }
    };

    private static final long serialVersionUID = 1L;

    private final DeterministicKey parent;
    private final ImmutableList<ChildNumber> childNumberPath;
    private final int depth;
    private int parentFingerprint; // 0 if this key is root node of key hierarchy

    /** 32 bytes */
    private final byte[] chainCode;

    /** Constructs a key from its components. This is not normally something you should use. */
    public DeterministicKey(ImmutableList<ChildNumber> childNumberPath,
                            byte[] chainCode,
                            LazyECPoint publicAsPoint,
                            @Nullable BigInteger priv,
                            @Nullable DeterministicKey parent) {
        super(priv, compressPoint(checkNotNull(publicAsPoint)));
        checkArgument(chainCode.length == 32);
        this.parent = parent;
        this.childNumberPath = checkNotNull(childNumberPath);
        this.chainCode = Arrays.copyOf(chainCode, chainCode.length);
        this.depth = this.childNumberPath.size();
        this.parentFingerprint = (parent != null) ? parent.getFingerprint() : 0;
    }

    public DeterministicKey(ImmutableList<ChildNumber> childNumberPath,
                            byte[] chainCode,
                            ECPoint publicAsPoint,
                            @Nullable BigInteger priv,
                            @Nullable DeterministicKey parent) {
        this(childNumberPath, chainCode, new LazyECPoint(publicAsPoint), priv, parent);
    }

    /** Constructs a key from its components. This is not normally something you should use. */
    public DeterministicKey(ImmutableList<ChildNumber> childNumberPath,
                            byte[] chainCode,
                            BigInteger priv,
                            @Nullable DeterministicKey parent) {
        super(priv, compressPoint(ECKey.publicPointFromPrivate(priv)));
        checkArgument(chainCode.length == 32);
        this.parent = parent;
        this.childNumberPath = checkNotNull(childNumberPath);
        this.chainCode = Arrays.copyOf(chainCode, chainCode.length);
        this.depth = this.childNumberPath.size();
        this.parentFingerprint = (parent != null) ? parent.getFingerprint() : 0;
    }

    /** Constructs a key from its components. This is not normally something you should use. */
    public DeterministicKey(ImmutableList<ChildNumber> childNumberPath,
                            byte[] chainCode,
                            KeyCrypter crypter,
                            LazyECPoint pub,
                            EncryptedData priv,
                            @Nullable DeterministicKey parent) {
        this(childNumberPath, chainCode, pub, null, parent);
        this.encryptedPrivateKey = checkNotNull(priv);
        this.keyCrypter = checkNotNull(crypter);
    }

    /**
     * Return the fingerprint of this key's parent as an int value, or zero if this key is the
     * root node of the key hierarchy.  Raise an exception if the arguments are inconsistent.
     * This method exists to avoid code repetition in the constructors.
     */
    private int ascertainParentFingerprint(DeterministicKey parentKey, int parentFingerprint)
    throws IllegalArgumentException {
        if (parentFingerprint != 0) {
            if (parent != null)
                checkArgument(parent.getFingerprint() == parentFingerprint,
                              "parent fingerprint mismatch",
                              Integer.toHexString(parent.getFingerprint()), Integer.toHexString(parentFingerprint));
            return parentFingerprint;
        } else return 0;
    }

    /**
     * Constructs a key from its components, including its public key data and possibly-redundant
     * information about its parent key.  Invoked when deserializing, but otherwise not something that
     * you normally should use.
     */
    private DeterministicKey(ImmutableList<ChildNumber> childNumberPath,
                            byte[] chainCode,
                            LazyECPoint publicAsPoint,
                            @Nullable DeterministicKey parent,
                            int depth,
                            int parentFingerprint) {
        super(null, compressPoint(checkNotNull(publicAsPoint)));
        checkArgument(chainCode.length == 32);
        this.parent = parent;
        this.childNumberPath = checkNotNull(childNumberPath);
        this.chainCode = Arrays.copyOf(chainCode, chainCode.length);
        this.depth = depth;
        this.parentFingerprint = ascertainParentFingerprint(parent, parentFingerprint);
    }

    /**
     * Constructs a key from its components, including its private key data and possibly-redundant
     * information about its parent key.  Invoked when deserializing, but otherwise not something that
     * you normally should use.
     */
    private DeterministicKey(ImmutableList<ChildNumber> childNumberPath,
                            byte[] chainCode,
                            BigInteger priv,
                            @Nullable DeterministicKey parent,
                            int depth,
                            int parentFingerprint) {
        super(priv, compressPoint(ECKey.publicPointFromPrivate(priv)));
        checkArgument(chainCode.length == 32);
        this.parent = parent;
        this.childNumberPath = checkNotNull(childNumberPath);
        this.chainCode = Arrays.copyOf(chainCode, chainCode.length);
        this.depth = depth;
        this.parentFingerprint = ascertainParentFingerprint(parent, parentFingerprint);
    }

    
    /** Clones the key */
    public DeterministicKey(DeterministicKey keyToClone, DeterministicKey newParent) {
        super(keyToClone.priv, keyToClone.pub.get());
        this.parent = newParent;
        this.childNumberPath = keyToClone.childNumberPath;
        this.chainCode = keyToClone.chainCode;
        this.encryptedPrivateKey = keyToClone.encryptedPrivateKey;
        this.depth = this.childNumberPath.size();
        this.parentFingerprint = this.parent.getFingerprint();
    }

    /**
     * Returns the path through some {@link DeterministicHierarchy} which reaches this keys position in the tree.
     * A path can be written as 1/2/1 which means the first child of the root, the second child of that node, then
     * the first child of that node.
     */
    public ImmutableList<ChildNumber> getPath() {
        return childNumberPath;
    }

    /**
     * Returns the path of this key as a human readable string starting with M to indicate the master key.
     */
    public String getPathAsString() {
        return HDUtils.formatPath(getPath());
    }

    /**
     * Return this key's depth in the hierarchy, where the root node is at depth zero.
     * This may be different than the number of segments in the path if this key was
     * deserialized without access to its parent.
     */
    public int getDepth() {
        return depth;
    }

    /** Returns the last element of the path returned by {@link DeterministicKey#getPath()} */
    public ChildNumber getChildNumber() {
        return childNumberPath.size() == 0 ? ChildNumber.ZERO : childNumberPath.get(childNumberPath.size() - 1);
    }

    /**
     * Returns the chain code associated with this key. See the specification to learn more about chain codes.
     */
    public byte[] getChainCode() {
        return chainCode;
    }

    /**
     * Returns RIPE-MD160(SHA256(pub key bytes)).
     */
    public byte[] getIdentifier() {
        return Utils.sha256hash160(getPubKey());
    }

    /** Returns the first 32 bits of the result of {@link #getIdentifier()}. */
    public int getFingerprint() {
        // TODO: why is this different than armory's fingerprint? BIP 32: "The first 32 bits of the identifier are called the fingerprint."
        return ByteBuffer.wrap(Arrays.copyOfRange(getIdentifier(), 0, 4)).getInt();
    }

    @Nullable
    public DeterministicKey getParent() {
        return parent;
    }

    /**
     * Return the fingerprint of the key from which this key was derived, if this is a
     * child key, or else an array of four zero-value bytes.
     */
    public int getParentFingerprint() {
        return parentFingerprint;
    }

    /**
     * Returns private key bytes, padded with zeros to 33 bytes.
     * @throws java.lang.IllegalStateException if the private key bytes are missing.
     */
    public byte[] getPrivKeyBytes33() {
        byte[] bytes33 = new byte[33];
        byte[] priv = getPrivKeyBytes();
        System.arraycopy(priv, 0, bytes33, 33 - priv.length, priv.length);
        return bytes33;
    }

    /**
     * Returns the same key with the private bytes removed. May return the same instance. The purpose of this is to save
     * memory: the private key can always be very efficiently rederived from a parent that a private key, so storing
     * all the private keys in RAM is a poor tradeoff especially on constrained devices. This means that the returned
     * key may still be usable for signing and so on, so don't expect it to be a true pubkey-only object! If you want
     * that then you should follow this call with a call to {@link #dropParent()}.
     */
    public DeterministicKey dropPrivateBytes() {
        if (isPubKeyOnly())
            return this;
        else
            return new DeterministicKey(getPath(), getChainCode(), pub, null, parent);
    }

    /**
     * <p>Returns the same key with the parent pointer removed (it still knows its own path and the parent fingerprint).</p>
     *
     * <p>If this key doesn't have private key bytes stored/cached itself, but could rederive them from the parent, then
     * the new key returned by this method won't be able to do that. Thus, using dropPrivateBytes().dropParent() on a
     * regular DeterministicKey will yield a new DeterministicKey that cannot sign or do other things involving the
     * private key at all.</p>
     */
    public DeterministicKey dropParent() {
        DeterministicKey key = new DeterministicKey(getPath(), getChainCode(), pub, priv, null);
        key.parentFingerprint = parentFingerprint;
        return key;
    }

    static byte[] addChecksum(byte[] input) {
        int inputLength = input.length;
        byte[] checksummed = new byte[inputLength + 4];
        System.arraycopy(input, 0, checksummed, 0, inputLength);
        byte[] checksum = Utils.doubleDigest(input);
        System.arraycopy(checksum, 0, checksummed, inputLength, 4);
        return checksummed;
    }

    @Override
    public DeterministicKey encrypt(KeyCrypter keyCrypter, KeyParameter aesKey) throws KeyCrypterException {
        throw new UnsupportedOperationException("Must supply a new parent for encryption");
    }

    public DeterministicKey encrypt(KeyCrypter keyCrypter, KeyParameter aesKey, @Nullable DeterministicKey newParent) throws KeyCrypterException {
        // Same as the parent code, except we construct a DeterministicKey instead of an ECKey.
        checkNotNull(keyCrypter);
        if (newParent != null)
            checkArgument(newParent.isEncrypted());
        final byte[] privKeyBytes = getPrivKeyBytes();
        checkState(privKeyBytes != null, "Private key is not available");
        EncryptedData encryptedPrivateKey = keyCrypter.encrypt(privKeyBytes, aesKey);
        DeterministicKey key = new DeterministicKey(childNumberPath, chainCode, keyCrypter, pub, encryptedPrivateKey, newParent);
        if (newParent == null)
            key.setCreationTimeSeconds(getCreationTimeSeconds());
        return key;
    }

    /**
     * A deterministic key is considered to be 'public key only' if it hasn't got a private key part and it cannot be
     * rederived. If the hierarchy is encrypted this returns true.
     */
    @Override
    public boolean isPubKeyOnly() {
        return super.isPubKeyOnly() && (parent == null || parent.isPubKeyOnly());
    }

    /** {@inheritDoc} */
    @Override
    public boolean hasPrivKey() {
        return findOrDerivePrivateKey() != null;
    }

    @Nullable
    @Override
    public byte[] getSecretBytes() {
        return priv != null ? getPrivKeyBytes() : null;
    }

    /**
     * A deterministic key is considered to be encrypted if it has access to encrypted private key bytes, OR if its
     * parent does. The reason is because the parent would be encrypted under the same key and this key knows how to
     * rederive its own private key bytes from the parent, if needed.
     */
    @Override
    public boolean isEncrypted() {
        return priv == null && (super.isEncrypted() || (parent != null && parent.isEncrypted()));
    }

    /**
     * Returns this keys {@link org.bitcoinj.crypto.KeyCrypter} <b>or</b> the keycrypter of its parent key.
     */
    @Override @Nullable
    public KeyCrypter getKeyCrypter() {
        if (keyCrypter != null)
            return keyCrypter;
        else if (parent != null)
            return parent.getKeyCrypter();
        else
            return null;
    }

    @Override
    public ECDSASignature sign(Sha256Hash input, @Nullable KeyParameter aesKey) throws KeyCrypterException {
        if (isEncrypted()) {
            // If the key is encrypted, ECKey.sign will decrypt it first before rerunning sign. Decryption walks the
            // key heirarchy to find the private key (see below), so, we can just run the inherited method.
            return super.sign(input, aesKey);
        } else {
            // If it's not encrypted, derive the private via the parents.
            final BigInteger privateKey = findOrDerivePrivateKey();
            if (privateKey == null) {
                // This key is a part of a public-key only heirarchy and cannot be used for signing
                throw new MissingPrivateKeyException();
            }
            return super.doSign(input, privateKey);
        }
    }

    @Override
    public DeterministicKey decrypt(KeyCrypter keyCrypter, KeyParameter aesKey) throws KeyCrypterException {
        checkNotNull(keyCrypter);
        // Check that the keyCrypter matches the one used to encrypt the keys, if set.
        if (this.keyCrypter != null && !this.keyCrypter.equals(keyCrypter))
            throw new KeyCrypterException("The keyCrypter being used to decrypt the key is different to the one that was used to encrypt it");
        BigInteger privKey = findOrDeriveEncryptedPrivateKey(keyCrypter, aesKey);
        DeterministicKey key = new DeterministicKey(childNumberPath, chainCode, privKey, parent);
        if (!Arrays.equals(key.getPubKey(), getPubKey()))
            throw new KeyCrypterException("Provided AES key is wrong");
        if (parent == null)
            key.setCreationTimeSeconds(getCreationTimeSeconds());
        return key;
    }

    @Override
    public DeterministicKey decrypt(KeyParameter aesKey) throws KeyCrypterException {
        return (DeterministicKey) super.decrypt(aesKey);
    }

    // For when a key is encrypted, either decrypt our encrypted private key bytes, or work up the tree asking parents
    // to decrypt and re-derive.
    private BigInteger findOrDeriveEncryptedPrivateKey(KeyCrypter keyCrypter, KeyParameter aesKey) {
        if (encryptedPrivateKey != null)
            return new BigInteger(1, keyCrypter.decrypt(encryptedPrivateKey, aesKey));
        // Otherwise we don't have it, but maybe we can figure it out from our parents. Walk up the tree looking for
        // the first key that has some encrypted private key data.
        DeterministicKey cursor = parent;
        while (cursor != null) {
            if (cursor.encryptedPrivateKey != null) break;
            cursor = cursor.parent;
        }
        if (cursor == null)
            throw new KeyCrypterException("Neither this key nor its parents have an encrypted private key");
        byte[] parentalPrivateKeyBytes = keyCrypter.decrypt(cursor.encryptedPrivateKey, aesKey);
        return derivePrivateKeyDownwards(cursor, parentalPrivateKeyBytes);
    }

    @Nullable
    private BigInteger findOrDerivePrivateKey() {
        DeterministicKey cursor = this;
        while (cursor != null) {
            if (cursor.priv != null) break;
            cursor = cursor.parent;
        }
        if (cursor == null)
            return null;
        return derivePrivateKeyDownwards(cursor, cursor.priv.toByteArray());
    }

    private BigInteger derivePrivateKeyDownwards(DeterministicKey cursor, byte[] parentalPrivateKeyBytes) {
        DeterministicKey downCursor = new DeterministicKey(cursor.childNumberPath, cursor.chainCode,
                cursor.pub, new BigInteger(1, parentalPrivateKeyBytes), cursor.parent);
        // Now we have to rederive the keys along the path back to ourselves. That path can be found by just truncating
        // our path with the length of the parents path.
        ImmutableList<ChildNumber> path = childNumberPath.subList(cursor.getPath().size(), childNumberPath.size());
        for (ChildNumber num : path) {
            downCursor = HDKeyDerivation.deriveChildKey(downCursor, num);
        }
        // downCursor is now the same key as us, but with private key bytes.
        checkState(downCursor.pub.equals(pub));
        return checkNotNull(downCursor.priv);
    }

    /**
     * Derives a child at the given index using hardened derivation.  Note: <code>index</code> is
     * not the "i" value.  If you want the softened derivation, then use instead
     * <code>HDKeyDerivation.deriveChildKey(this, new ChildNumber(child, false))</code>.
     */
    public DeterministicKey derive(int child) {
        return HDKeyDerivation.deriveChildKey(this, new ChildNumber(child, true));
    }

    /**
     * Returns the private key of this deterministic key. Even if this object isn't storing the private key,
     * it can be re-derived by walking up to the parents if necessary and this is what will happen.
     * @throws java.lang.IllegalStateException if the parents are encrypted or a watching chain.
     */
    @Override
    public BigInteger getPrivKey() {
        final BigInteger key = findOrDerivePrivateKey();
        checkState(key != null, "Private key bytes not available");
        return key;
    }

    public byte[] serializePublic(NetworkParameters params) {
        return serialize(params, true);
    }

    public byte[] serializePrivate(NetworkParameters params) {
        return serialize(params, false);
    }

    private byte[] serialize(NetworkParameters params, boolean pub) {
        ByteBuffer ser = ByteBuffer.allocate(78);
        ser.putInt(pub ? params.getBip32HeaderPub() : params.getBip32HeaderPriv());
        ser.put((byte) getDepth());
        ser.putInt(getParentFingerprint());
        ser.putInt(getChildNumber().i());
        ser.put(getChainCode());
        ser.put(pub ? getPubKey() : getPrivKeyBytes33());
        checkState(ser.position() == 78);
        return ser.array();
    }

    public String serializePubB58(NetworkParameters params) {
        return toBase58(serialize(params, true));
    }

    public String serializePrivB58(NetworkParameters params) {
        return toBase58(serialize(params, false));
    }

    static String toBase58(byte[] ser) {
        return Base58.encode(addChecksum(ser));
    }

    /** Deserialize a base-58-encoded HD Key with no parent */
    public static DeterministicKey deserializeB58(String base58, NetworkParameters params) {
        return deserializeB58(null, base58, params);
    }

    /**
      * Deserialize a base-58-encoded HD Key.
      *  @param parent The parent node in the given key's deterministic hierarchy.
      */
    public static DeterministicKey deserializeB58(@Nullable DeterministicKey parent, String base58, NetworkParameters params) {
        try {
            return deserialize(params, Base58.decodeChecked(base58), parent);
        } catch (AddressFormatException e) {
            throw new IllegalArgumentException(e);
        }
    }

    /**
      * Deserialize an HD Key with no parent
      */
    public static DeterministicKey deserialize(NetworkParameters params, byte[] serializedKey) {
        return deserialize(params, serializedKey, null);
    }

    /**
      * Deserialize an HD Key.
     * @param parent The parent node in the given key's deterministic hierarchy.
     */
    public static DeterministicKey deserialize(NetworkParameters params, byte[] serializedKey, @Nullable DeterministicKey parent) {
        ByteBuffer buffer = ByteBuffer.wrap(serializedKey);
        int header = buffer.getInt();
        if (header != params.getBip32HeaderPriv() && header != params.getBip32HeaderPub())
            throw new IllegalArgumentException("Unknown header bytes: " + toBase58(serializedKey).substring(0, 4));
        boolean pub = header == params.getBip32HeaderPub();
        int depth = buffer.get() & 0xFF; // convert signed byte to positive int since depth cannot be negative
        final int parentFingerprint = buffer.getInt();
        final int i = buffer.getInt();
        final ChildNumber childNumber = new ChildNumber(i);
        ImmutableList<ChildNumber> path;
        if (parent != null) {
            if (parentFingerprint == 0)
                throw new IllegalArgumentException("Parent was provided but this key doesn't have one");
            if (parent.getFingerprint() != parentFingerprint)
                throw new IllegalArgumentException("Parent fingerprints don't match");
            path = HDUtils.append(parent.getPath(), childNumber);
            if (path.size() != depth)
                throw new IllegalArgumentException("Depth does not match");
        } else {
            if (depth >= 1)
                // We have been given a key that is not a root key, yet we lack the object representing the parent.
                // This can happen when deserializing an account key for a watching wallet.  In this case, we assume that
                // the client wants to conceal the key's position in the hierarchy.  The path is truncated at the
                // parent's node.
                path = ImmutableList.of(childNumber);
            else path = ImmutableList.of();
        }
        byte[] chainCode = new byte[32];
        buffer.get(chainCode);
        byte[] data = new byte[33];
        buffer.get(data);
        checkArgument(!buffer.hasRemaining(), "Found unexpected data in key");
        if (pub) {
            return new DeterministicKey(path, chainCode, new LazyECPoint(ECKey.CURVE.getCurve(), data), parent, depth, parentFingerprint);
        } else {
            return new DeterministicKey(path, chainCode, new BigInteger(1, data), parent, depth, parentFingerprint);
        }
    }

    /**
     * The creation time of a deterministic key is equal to that of its parent, unless this key is the root of a tree
     * in which case the time is stored alongside the key as per normal, see {@link org.bitcoinj.core.ECKey#getCreationTimeSeconds()}.
     */
    @Override
    public long getCreationTimeSeconds() {
        if (parent != null)
            return parent.getCreationTimeSeconds();
        else
            return super.getCreationTimeSeconds();
    }

    /**
     * The creation time of a deterministic key is equal to that of its parent, unless this key is the root of a tree.
     * Thus, setting the creation time on a leaf is forbidden.
     */
    @Override
    public void setCreationTimeSeconds(long newCreationTimeSeconds) {
        if (parent != null)
            throw new IllegalStateException("Creation time can only be set on root keys.");
        else
            super.setCreationTimeSeconds(newCreationTimeSeconds);
    }

    /**
     * Verifies equality of all fields but NOT the parent pointer (thus the same key derived in two separate heirarchy
     * objects will equal each other.
     */
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        DeterministicKey other = (DeterministicKey) o;

        return super.equals(other)
                && Arrays.equals(this.chainCode, other.chainCode)
                && Objects.equal(this.childNumberPath, other.childNumberPath);
    }

    @Override
    public int hashCode() {
        int result = super.hashCode();
        result = 31 * result + childNumberPath.hashCode();
        result = 31 * result + Arrays.hashCode(chainCode);
        return result;
    }

    @Override
    public String toString() {
        final ToStringHelper helper = Objects.toStringHelper(this).omitNullValues();
        helper.add("pub", Utils.HEX.encode(pub.getEncoded()));
        helper.add("chainCode", HEX.encode(chainCode));
        helper.add("path", getPathAsString());
        if (creationTimeSeconds > 0)
            helper.add("creationTimeSeconds", creationTimeSeconds);
        helper.add("isEncrypted", isEncrypted());
        helper.add("isPubKeyOnly", isPubKeyOnly());
        return helper.toString();
    }

    @Override
    public void formatKeyWithAddress(boolean includePrivateKeys, StringBuilder builder, NetworkParameters params) {
        final Address address = toAddress(params);
        builder.append("  addr:");
        builder.append(address.toString());
        builder.append("  hash160:");
        builder.append(Utils.HEX.encode(getPubKeyHash()));
        builder.append("  (");
        builder.append(getPathAsString());
        builder.append(")");
        builder.append("\n");
        if (includePrivateKeys) {
            builder.append("  ");
            builder.append(toStringWithPrivate(params));
            builder.append("\n");
        }
    }
}


File: core/src/main/java/org/bitcoinj/crypto/MnemonicCode.java
/*
 * Copyright 2013 Ken Sedgwick
 * Copyright 2014 Andreas Schildbach
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.crypto;

import org.bitcoinj.core.Utils;
import com.google.common.base.Joiner;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import static org.bitcoinj.core.Utils.HEX;

/**
 * A MnemonicCode object may be used to convert between binary seed values and
 * lists of words per <a href="https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki">the BIP 39
 * specification</a>
 */

public class MnemonicCode {
    private static final Logger log = LoggerFactory.getLogger(MnemonicCode.class);

    private ArrayList<String> wordList;

    private static final String BIP39_ENGLISH_RESOURCE_NAME = "mnemonic/wordlist/english.txt";
    private static String BIP39_ENGLISH_SHA256 = "ad90bf3beb7b0eb7e5acd74727dc0da96e0a280a258354e7293fb7e211ac03db";

    /** UNIX time for when the BIP39 standard was finalised. This can be used as a default seed birthday. */
    public static long BIP39_STANDARDISATION_TIME_SECS = 1381276800;

    private static final int PBKDF2_ROUNDS = 2048;

    public static MnemonicCode INSTANCE;

    static {
        try {
            INSTANCE = new MnemonicCode();
        } catch (FileNotFoundException e) {
            // We expect failure on Android. The developer has to set INSTANCE themselves.
            if (!Utils.isAndroidRuntime())
                log.error("Could not find word list", e);
        } catch (IOException e) {
            log.error("Failed to load word list", e);
        }
    }

    /** Initialise from the included word list. Won't work on Android. */
    public MnemonicCode() throws IOException {
        this(openDefaultWords(), BIP39_ENGLISH_SHA256);
    }

    private static InputStream openDefaultWords() throws IOException {
        InputStream stream = MnemonicCode.class.getResourceAsStream(BIP39_ENGLISH_RESOURCE_NAME);
        if (stream == null)
            throw new FileNotFoundException(BIP39_ENGLISH_RESOURCE_NAME);
        return stream;
    }

    /**
     * Creates an MnemonicCode object, initializing with words read from the supplied input stream.  If a wordListDigest
     * is supplied the digest of the words will be checked.
     */
    public MnemonicCode(InputStream wordstream, String wordListDigest) throws IOException, IllegalArgumentException {
        BufferedReader br = new BufferedReader(new InputStreamReader(wordstream, "UTF-8"));
        this.wordList = new ArrayList<String>(2048);
        MessageDigest md = Utils.newSha256Digest();
        String word;
        while ((word = br.readLine()) != null) {
            md.update(word.getBytes());
            this.wordList.add(word);
        }
        br.close();

        if (this.wordList.size() != 2048)
            throw new IllegalArgumentException("input stream did not contain 2048 words");

        // If a wordListDigest is supplied check to make sure it matches.
        if (wordListDigest != null) {
            byte[] digest = md.digest();
            String hexdigest = HEX.encode(digest);
            if (!hexdigest.equals(wordListDigest))
                throw new IllegalArgumentException("wordlist digest mismatch");
        }
    }

    /**
     * Gets the word list this code uses.
     */
    public List<String> getWordList() {
        return wordList;
    }

    /**
     * Convert mnemonic word list to seed.
     */
    public static byte[] toSeed(List<String> words, String passphrase) {

        // To create binary seed from mnemonic, we use PBKDF2 function
        // with mnemonic sentence (in UTF-8) used as a password and
        // string "mnemonic" + passphrase (again in UTF-8) used as a
        // salt. Iteration count is set to 4096 and HMAC-SHA512 is
        // used as a pseudo-random function. Desired length of the
        // derived key is 512 bits (= 64 bytes).
        //
        String pass = Joiner.on(' ').join(words);
        String salt = "mnemonic" + passphrase;

        long start = System.currentTimeMillis();
        byte[] seed = PBKDF2SHA512.derive(pass, salt, PBKDF2_ROUNDS, 64);
        log.info("PBKDF2 took {}ms", System.currentTimeMillis() - start);
        return seed;
    }

    /**
     * Convert mnemonic word list to original entropy value.
     */
    public byte[] toEntropy(List<String> words) throws MnemonicException.MnemonicLengthException, MnemonicException.MnemonicWordException, MnemonicException.MnemonicChecksumException {
        if (words.size() % 3 > 0)
            throw new MnemonicException.MnemonicLengthException("Word list size must be multiple of three words.");

        if (words.size() == 0)
            throw new MnemonicException.MnemonicLengthException("Word list is empty.");

        // Look up all the words in the list and construct the
        // concatenation of the original entropy and the checksum.
        //
        int concatLenBits = words.size() * 11;
        boolean[] concatBits = new boolean[concatLenBits];
        int wordindex = 0;
        for (String word : words) {
            // Find the words index in the wordlist.
            int ndx = Collections.binarySearch(this.wordList, word);
            if (ndx < 0)
                throw new MnemonicException.MnemonicWordException(word);

            // Set the next 11 bits to the value of the index.
            for (int ii = 0; ii < 11; ++ii)
                concatBits[(wordindex * 11) + ii] = (ndx & (1 << (10 - ii))) != 0;
            ++wordindex;
        }        

        int checksumLengthBits = concatLenBits / 33;
        int entropyLengthBits = concatLenBits - checksumLengthBits;

        // Extract original entropy as bytes.
        byte[] entropy = new byte[entropyLengthBits / 8];
        for (int ii = 0; ii < entropy.length; ++ii)
            for (int jj = 0; jj < 8; ++jj)
                if (concatBits[(ii * 8) + jj])
                    entropy[ii] |= 1 << (7 - jj);

        // Take the digest of the entropy.
        byte[] hash = Utils.singleDigest(entropy);
        boolean[] hashBits = bytesToBits(hash);

        // Check all the checksum bits.
        for (int i = 0; i < checksumLengthBits; ++i)
            if (concatBits[entropyLengthBits + i] != hashBits[i])
                throw new MnemonicException.MnemonicChecksumException();

        return entropy;
    }

    /**
     * Convert entropy data to mnemonic word list.
     */
    public List<String> toMnemonic(byte[] entropy) throws MnemonicException.MnemonicLengthException {
        if (entropy.length % 4 > 0)
            throw new MnemonicException.MnemonicLengthException("Entropy length not multiple of 32 bits.");

        if (entropy.length == 0)
            throw new MnemonicException.MnemonicLengthException("Entropy is empty.");

        // We take initial entropy of ENT bits and compute its
        // checksum by taking first ENT / 32 bits of its SHA256 hash.

        byte[] hash = Utils.singleDigest(entropy);
        boolean[] hashBits = bytesToBits(hash);
        
        boolean[] entropyBits = bytesToBits(entropy);
        int checksumLengthBits = entropyBits.length / 32;

        // We append these bits to the end of the initial entropy. 
        boolean[] concatBits = new boolean[entropyBits.length + checksumLengthBits];
        System.arraycopy(entropyBits, 0, concatBits, 0, entropyBits.length);
        System.arraycopy(hashBits, 0, concatBits, entropyBits.length, checksumLengthBits);

        // Next we take these concatenated bits and split them into
        // groups of 11 bits. Each group encodes number from 0-2047
        // which is a position in a wordlist.  We convert numbers into
        // words and use joined words as mnemonic sentence.

        ArrayList<String> words = new ArrayList<String>();
        int nwords = concatBits.length / 11;
        for (int i = 0; i < nwords; ++i) {
            int index = 0;
            for (int j = 0; j < 11; ++j) {
                index <<= 1;
                if (concatBits[(i * 11) + j])
                    index |= 0x1;
            }
            words.add(this.wordList.get(index));
        }
            
        return words;        
    }

    /**
     * Check to see if a mnemonic word list is valid.
     */
    public void check(List<String> words) throws MnemonicException {
        toEntropy(words);
    }

    private static boolean[] bytesToBits(byte[] data) {
        boolean[] bits = new boolean[data.length * 8];
        for (int i = 0; i < data.length; ++i)
            for (int j = 0; j < 8; ++j)
                bits[(i * 8) + j] = (data[i] & (1 << (7 - j))) != 0;
        return bits;
    }
}


File: core/src/main/java/org/bitcoinj/net/discovery/HttpDiscovery.java
/**
 * Copyright 2014 Mike Hearn
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.bitcoinj.net.discovery;

import com.google.common.annotations.*;
import com.google.protobuf.*;
import com.squareup.okhttp.*;
import org.bitcoin.crawler.*;
import org.bitcoinj.core.*;
import org.slf4j.*;

import javax.annotation.*;
import java.io.*;
import java.net.*;
import java.security.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.zip.*;

import static com.google.common.base.Preconditions.*;

/**
 * A class that knows how to read signed sets of seeds over HTTP, using a simple protobuf based protocol. See the
 * peerseeds.proto file for the definition, with a gzipped delimited SignedPeerSeeds being the root of the data.
 * This is not currently in use by the Bitcoin community, but rather, is here for experimentation.
 */
public class HttpDiscovery implements PeerDiscovery {
    private static final Logger log = LoggerFactory.getLogger(HttpDiscovery.class);

    public static class Details {
        @Nullable public final ECKey pubkey;
        public final URI uri;

        public Details(@Nullable ECKey pubkey, URI uri) {
            this.pubkey = pubkey;
            this.uri = uri;
        }
    }

    private final Details details;
    private final NetworkParameters params;
    private final OkHttpClient client;

    /**
     * Constructs a discovery object that will read data from the given HTTP[S] URI and, if a public key is provided,
     * will check the signature using that key.
     */
    public HttpDiscovery(NetworkParameters params, URI uri, @Nullable ECKey pubkey) {
        this(params, new Details(pubkey, uri));
    }

    /**
     * Constructs a discovery object that will read data from the given HTTP[S] URI and, if a public key is provided,
     * will check the signature using that key.
     */
    public HttpDiscovery(NetworkParameters params, Details details) {
        this(params, details, new OkHttpClient());
    }

    public HttpDiscovery(NetworkParameters params, Details details,  OkHttpClient client) {
        checkArgument(details.uri.getScheme().startsWith("http"));
        this.details = details;
        this.params = params;
        this.client = client;
    }

    @Override
    public InetSocketAddress[] getPeers(long timeoutValue, TimeUnit timeoutUnit) throws PeerDiscoveryException {
        try {
            log.info("Requesting seeds from {}", details.uri);
            Response response = client.newCall(new Request.Builder().url(details.uri.toURL()).build()).execute();
            if (!response.isSuccessful())
                throw new PeerDiscoveryException("HTTP request failed: " + response.code() + " " + response.message());
            InputStream stream = response.body().byteStream();
            GZIPInputStream zip = new GZIPInputStream(stream);
            PeerSeedProtos.SignedPeerSeeds proto = PeerSeedProtos.SignedPeerSeeds.parseDelimitedFrom(zip);
            stream.close();
            return protoToAddrs(proto);
        } catch (PeerDiscoveryException e1) {
            throw e1;
        } catch (Exception e) {
            throw new PeerDiscoveryException(e);
        }
    }

    @VisibleForTesting
    public InetSocketAddress[] protoToAddrs(PeerSeedProtos.SignedPeerSeeds proto) throws PeerDiscoveryException, InvalidProtocolBufferException, SignatureException {
        if (details.pubkey != null) {
            if (!Arrays.equals(proto.getPubkey().toByteArray(), details.pubkey.getPubKey()))
                throw new PeerDiscoveryException("Public key mismatch");
            byte[] hash = Utils.singleDigest(proto.getPeerSeeds().toByteArray());
            details.pubkey.verifyOrThrow(hash, proto.getSignature().toByteArray());
        }
        PeerSeedProtos.PeerSeeds seeds = PeerSeedProtos.PeerSeeds.parseFrom(proto.getPeerSeeds());
        if (seeds.getTimestamp() < Utils.currentTimeSeconds() - (60 * 60 * 24))
            throw new PeerDiscoveryException("Seed data is more than one day old: replay attack?");
        if (!seeds.getNet().equals(params.getPaymentProtocolId()))
            throw new PeerDiscoveryException("Network mismatch");
        InetSocketAddress[] results = new InetSocketAddress[seeds.getSeedCount()];
        int i = 0;
        for (PeerSeedProtos.PeerSeedData data : seeds.getSeedList())
            results[i++] = new InetSocketAddress(data.getIpAddress(), data.getPort());
        return results;
    }

    @Override
    public void shutdown() {
    }
}


File: core/src/main/java/org/bitcoinj/script/Script.java
/**
 * Copyright 2011 Google Inc.
 * Copyright 2012 Matt Corallo.
 * Copyright 2014 Andreas Schildbach
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.script;

import org.bitcoinj.core.*;
import org.bitcoinj.crypto.TransactionSignature;
import com.google.common.collect.Lists;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.spongycastle.crypto.digests.RIPEMD160Digest;

import javax.annotation.Nullable;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.math.BigInteger;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.*;

import static org.bitcoinj.script.ScriptOpCodes.*;
import static com.google.common.base.Preconditions.*;

// TODO: Redesign this entire API to be more type safe and organised.

/**
 * <p>Programs embedded inside transactions that control redemption of payments.</p>
 *
 * <p>Bitcoin transactions don't specify what they do directly. Instead <a href="https://en.bitcoin.it/wiki/Script">a
 * small binary stack language</a> is used to define programs that when evaluated return whether the transaction
 * "accepts" or rejects the other transactions connected to it.</p>
 *
 * <p>In SPV mode, scripts are not run, because that would require all transactions to be available and lightweight
 * clients don't have that data. In full mode, this class is used to run the interpreted language. It also has
 * static methods for building scripts.</p>
 */
public class Script {

    /** Enumeration to encapsulate the type of this script. */
    public enum ScriptType {
        // Do NOT change the ordering of the following definitions because their ordinals are stored in databases.
        NO_TYPE,
        P2PKH,
        PUB_KEY,
        P2SH
    };

    /** Flags to pass to {@link Script#correctlySpends(Transaction, long, Script, Set)}. */
    public enum VerifyFlag {
        P2SH, // Enable BIP16-style subscript evaluation.
        NULLDUMMY // Verify dummy stack item consumed by CHECKMULTISIG is of zero-length.
    }
    public static final EnumSet<VerifyFlag> ALL_VERIFY_FLAGS = EnumSet.allOf(VerifyFlag.class);

    private static final Logger log = LoggerFactory.getLogger(Script.class);
    public static final long MAX_SCRIPT_ELEMENT_SIZE = 520;  // bytes
    public static final int SIG_SIZE = 75;
    /** Max number of sigops allowed in a standard p2sh redeem script */
    public static final int MAX_P2SH_SIGOPS = 15;

    // The program is a set of chunks where each element is either [opcode] or [data, data, data ...]
    protected List<ScriptChunk> chunks;
    // Unfortunately, scripts are not ever re-serialized or canonicalized when used in signature hashing. Thus we
    // must preserve the exact bytes that we read off the wire, along with the parsed form.
    protected byte[] program;

    // Creation time of the associated keys in seconds since the epoch.
    private long creationTimeSeconds;

    /** Creates an empty script that serializes to nothing. */
    private Script() {
        chunks = Lists.newArrayList();
    }

    // Used from ScriptBuilder.
    Script(List<ScriptChunk> chunks) {
        this.chunks = Collections.unmodifiableList(new ArrayList<ScriptChunk>(chunks));
        creationTimeSeconds = Utils.currentTimeSeconds();
    }

    /**
     * Construct a Script that copies and wraps the programBytes array. The array is parsed and checked for syntactic
     * validity.
     * @param programBytes Array of program bytes from a transaction.
     */
    public Script(byte[] programBytes) throws ScriptException {
        program = programBytes;
        parse(programBytes);
        creationTimeSeconds = 0;
    }

    public Script(byte[] programBytes, long creationTimeSeconds) throws ScriptException {
        program = programBytes;
        parse(programBytes);
        this.creationTimeSeconds = creationTimeSeconds;
    }

    public long getCreationTimeSeconds() {
        return creationTimeSeconds;
    }

    public void setCreationTimeSeconds(long creationTimeSeconds) {
        this.creationTimeSeconds = creationTimeSeconds;
    }

    /**
     * Returns the program opcodes as a string, for example "[1234] DUP HASH160"
     */
    @Override
    public String toString() {
        StringBuilder buf = new StringBuilder();
        for (ScriptChunk chunk : chunks)
            buf.append(chunk).append(' ');
        if (buf.length() > 0)
            buf.setLength(buf.length() - 1);
        return buf.toString();
    }

    /** Returns the serialized program as a newly created byte array. */
    public byte[] getProgram() {
        try {
            // Don't round-trip as Satoshi's code doesn't and it would introduce a mismatch.
            if (program != null)
                return Arrays.copyOf(program, program.length);
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            for (ScriptChunk chunk : chunks) {
                chunk.write(bos);
            }
            program = bos.toByteArray();
            return program;
        } catch (IOException e) {
            throw new RuntimeException(e);  // Cannot happen.
        }
    }

    /** Returns an immutable list of the scripts parsed form. Each chunk is either an opcode or data element. */
    public List<ScriptChunk> getChunks() {
        return Collections.unmodifiableList(chunks);
    }

    private static final ScriptChunk STANDARD_TRANSACTION_SCRIPT_CHUNKS[];

    static {
        STANDARD_TRANSACTION_SCRIPT_CHUNKS = new ScriptChunk[] {
            new ScriptChunk(ScriptOpCodes.OP_DUP, null, 0),
            new ScriptChunk(ScriptOpCodes.OP_HASH160, null, 1),
            new ScriptChunk(ScriptOpCodes.OP_EQUALVERIFY, null, 23),
            new ScriptChunk(ScriptOpCodes.OP_CHECKSIG, null, 24),
        };
    }

    /**
     * <p>To run a script, first we parse it which breaks it up into chunks representing pushes of data or logical
     * opcodes. Then we can run the parsed chunks.</p>
     *
     * <p>The reason for this split, instead of just interpreting directly, is to make it easier
     * to reach into a programs structure and pull out bits of data without having to run it.
     * This is necessary to render the to/from addresses of transactions in a user interface.
     * The official client does something similar.</p>
     */
    private void parse(byte[] program) throws ScriptException {
        chunks = new ArrayList<ScriptChunk>(5);   // Common size.
        ByteArrayInputStream bis = new ByteArrayInputStream(program);
        int initialSize = bis.available();
        while (bis.available() > 0) {
            int startLocationInProgram = initialSize - bis.available();
            int opcode = bis.read();

            long dataToRead = -1;
            if (opcode >= 0 && opcode < OP_PUSHDATA1) {
                // Read some bytes of data, where how many is the opcode value itself.
                dataToRead = opcode;
            } else if (opcode == OP_PUSHDATA1) {
                if (bis.available() < 1) throw new ScriptException("Unexpected end of script");
                dataToRead = bis.read();
            } else if (opcode == OP_PUSHDATA2) {
                // Read a short, then read that many bytes of data.
                if (bis.available() < 2) throw new ScriptException("Unexpected end of script");
                dataToRead = bis.read() | (bis.read() << 8);
            } else if (opcode == OP_PUSHDATA4) {
                // Read a uint32, then read that many bytes of data.
                // Though this is allowed, because its value cannot be > 520, it should never actually be used
                if (bis.available() < 4) throw new ScriptException("Unexpected end of script");
                dataToRead = ((long)bis.read()) | (((long)bis.read()) << 8) | (((long)bis.read()) << 16) | (((long)bis.read()) << 24);
            }

            ScriptChunk chunk;
            if (dataToRead == -1) {
                chunk = new ScriptChunk(opcode, null, startLocationInProgram);
            } else {
                if (dataToRead > bis.available())
                    throw new ScriptException("Push of data element that is larger than remaining data");
                byte[] data = new byte[(int)dataToRead];
                checkState(dataToRead == 0 || bis.read(data, 0, (int)dataToRead) == dataToRead);
                chunk = new ScriptChunk(opcode, data, startLocationInProgram);
            }
            // Save some memory by eliminating redundant copies of the same chunk objects.
            for (ScriptChunk c : STANDARD_TRANSACTION_SCRIPT_CHUNKS) {
                if (c.equals(chunk)) chunk = c;
            }
            chunks.add(chunk);
        }
    }

    /**
     * Returns true if this script is of the form <pubkey> OP_CHECKSIG. This form was originally intended for transactions
     * where the peers talked to each other directly via TCP/IP, but has fallen out of favor with time due to that mode
     * of operation being susceptible to man-in-the-middle attacks. It is still used in coinbase outputs and can be
     * useful more exotic types of transaction, but today most payments are to addresses.
     */
    public boolean isSentToRawPubKey() {
        return chunks.size() == 2 && chunks.get(1).equalsOpCode(OP_CHECKSIG) &&
               !chunks.get(0).isOpCode() && chunks.get(0).data.length > 1;
    }

    /**
     * Returns true if this script is of the form DUP HASH160 <pubkey hash> EQUALVERIFY CHECKSIG, ie, payment to an
     * address like 1VayNert3x1KzbpzMGt2qdqrAThiRovi8. This form was originally intended for the case where you wish
     * to send somebody money with a written code because their node is offline, but over time has become the standard
     * way to make payments due to the short and recognizable base58 form addresses come in.
     */
    public boolean isSentToAddress() {
        return chunks.size() == 5 &&
               chunks.get(0).equalsOpCode(OP_DUP) &&
               chunks.get(1).equalsOpCode(OP_HASH160) &&
               chunks.get(2).data.length == Address.LENGTH &&
               chunks.get(3).equalsOpCode(OP_EQUALVERIFY) &&
               chunks.get(4).equalsOpCode(OP_CHECKSIG);
    }

    /**
     * An alias for isPayToScriptHash.
     */
    @Deprecated
    public boolean isSentToP2SH() {
        return isPayToScriptHash();
    }

    /**
     * <p>If a program matches the standard template DUP HASH160 &lt;pubkey hash&gt; EQUALVERIFY CHECKSIG
     * then this function retrieves the third element.
     * In this case, this is useful for fetching the destination address of a transaction.</p>
     * 
     * <p>If a program matches the standard template HASH160 &lt;script hash&gt; EQUAL
     * then this function retrieves the second element.
     * In this case, this is useful for fetching the hash of the redeem script of a transaction.</p>
     * 
     * <p>Otherwise it throws a ScriptException.</p>
     *
     */
    public byte[] getPubKeyHash() throws ScriptException {
        if (isSentToAddress())
            return chunks.get(2).data;
        else if (isPayToScriptHash())
            return chunks.get(1).data;
        else
            throw new ScriptException("Script not in the standard scriptPubKey form");
    }

    /**
     * Returns the public key in this script. If a script contains two constants and nothing else, it is assumed to
     * be a scriptSig (input) for a pay-to-address output and the second constant is returned (the first is the
     * signature). If a script contains a constant and an OP_CHECKSIG opcode, the constant is returned as it is
     * assumed to be a direct pay-to-key scriptPubKey (output) and the first constant is the public key.
     *
     * @throws ScriptException if the script is none of the named forms.
     */
    public byte[] getPubKey() throws ScriptException {
        if (chunks.size() != 2) {
            throw new ScriptException("Script not of right size, expecting 2 but got " + chunks.size());
        }
        final ScriptChunk chunk0 = chunks.get(0);
        final byte[] chunk0data = chunk0.data;
        final ScriptChunk chunk1 = chunks.get(1);
        final byte[] chunk1data = chunk1.data;
        if (chunk0data != null && chunk0data.length > 2 && chunk1data != null && chunk1data.length > 2) {
            // If we have two large constants assume the input to a pay-to-address output.
            return chunk1data;
        } else if (chunk1.equalsOpCode(OP_CHECKSIG) && chunk0data != null && chunk0data.length > 2) {
            // A large constant followed by an OP_CHECKSIG is the key.
            return chunk0data;
        } else {
            throw new ScriptException("Script did not match expected form: " + toString());
        }
    }

    /**
     * For 2-element [input] scripts assumes that the paid-to-address can be derived from the public key.
     * The concept of a "from address" isn't well defined in Bitcoin and you should not assume the sender of a
     * transaction can actually receive coins on it. This method may be removed in future.
     */
    @Deprecated
    public Address getFromAddress(NetworkParameters params) throws ScriptException {
        return new Address(params, Utils.sha256hash160(getPubKey()));
    }

    /**
     * Gets the destination address from this script, if it's in the required form (see getPubKey).
     */
    public Address getToAddress(NetworkParameters params) throws ScriptException {
        return getToAddress(params, false);
    }

    /**
     * Gets the destination address from this script, if it's in the required form (see getPubKey).
     * 
     * @param forcePayToPubKey
     *            If true, allow payToPubKey to be casted to the corresponding address. This is useful if you prefer
     *            showing addresses rather than pubkeys.
     */
    public Address getToAddress(NetworkParameters params, boolean forcePayToPubKey) throws ScriptException {
        if (isSentToAddress())
            return new Address(params, getPubKeyHash());
        else if (isPayToScriptHash())
            return Address.fromP2SHScript(params, this);
        else if (forcePayToPubKey && isSentToRawPubKey())
            return ECKey.fromPublicOnly(getPubKey()).toAddress(params);
        else
            throw new ScriptException("Cannot cast this script to a pay-to-address type");
    }

    ////////////////////// Interface for writing scripts from scratch ////////////////////////////////

    /**
     * Writes out the given byte buffer to the output stream with the correct opcode prefix
     * To write an integer call writeBytes(out, Utils.reverseBytes(Utils.encodeMPI(val, false)));
     */
    public static void writeBytes(OutputStream os, byte[] buf) throws IOException {
        if (buf.length < OP_PUSHDATA1) {
            os.write(buf.length);
            os.write(buf);
        } else if (buf.length < 256) {
            os.write(OP_PUSHDATA1);
            os.write(buf.length);
            os.write(buf);
        } else if (buf.length < 65536) {
            os.write(OP_PUSHDATA2);
            os.write(0xFF & (buf.length));
            os.write(0xFF & (buf.length >> 8));
            os.write(buf);
        } else {
            throw new RuntimeException("Unimplemented");
        }
    }

    /** Creates a program that requires at least N of the given keys to sign, using OP_CHECKMULTISIG. */
    public static byte[] createMultiSigOutputScript(int threshold, List<ECKey> pubkeys) {
        checkArgument(threshold > 0);
        checkArgument(threshold <= pubkeys.size());
        checkArgument(pubkeys.size() <= 16);  // That's the max we can represent with a single opcode.
        if (pubkeys.size() > 3) {
            log.warn("Creating a multi-signature output that is non-standard: {} pubkeys, should be <= 3", pubkeys.size());
        }
        try {
            ByteArrayOutputStream bits = new ByteArrayOutputStream();
            bits.write(encodeToOpN(threshold));
            for (ECKey key : pubkeys) {
                writeBytes(bits, key.getPubKey());
            }
            bits.write(encodeToOpN(pubkeys.size()));
            bits.write(OP_CHECKMULTISIG);
            return bits.toByteArray();
        } catch (IOException e) {
            throw new RuntimeException(e);  // Cannot happen.
        }
    }

    public static byte[] createInputScript(byte[] signature, byte[] pubkey) {
        try {
            // TODO: Do this by creating a Script *first* then having the script reassemble itself into bytes.
            ByteArrayOutputStream bits = new UnsafeByteArrayOutputStream(signature.length + pubkey.length + 2);
            writeBytes(bits, signature);
            writeBytes(bits, pubkey);
            return bits.toByteArray();
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    public static byte[] createInputScript(byte[] signature) {
        try {
            // TODO: Do this by creating a Script *first* then having the script reassemble itself into bytes.
            ByteArrayOutputStream bits = new UnsafeByteArrayOutputStream(signature.length + 2);
            writeBytes(bits, signature);
            return bits.toByteArray();
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    /**
     * Creates an incomplete scriptSig that, once filled with signatures, can redeem output containing this scriptPubKey.
     * Instead of the signatures resulting script has OP_0.
     * Having incomplete input script allows to pass around partially signed tx.
     * It is expected that this program later on will be updated with proper signatures.
     */
    public Script createEmptyInputScript(@Nullable ECKey key, @Nullable Script redeemScript) {
        if (isSentToAddress()) {
            checkArgument(key != null, "Key required to create pay-to-address input script");
            return ScriptBuilder.createInputScript(null, key);
        } else if (isSentToRawPubKey()) {
            return ScriptBuilder.createInputScript(null);
        } else if (isPayToScriptHash()) {
            checkArgument(redeemScript != null, "Redeem script required to create P2SH input script");
            return ScriptBuilder.createP2SHMultiSigInputScript(null, redeemScript);
        } else {
            throw new ScriptException("Do not understand script type: " + this);
        }
    }

    /**
     * Returns a copy of the given scriptSig with the signature inserted in the given position.
     */
    public Script getScriptSigWithSignature(Script scriptSig, byte[] sigBytes, int index) {
        int sigsPrefixCount = 0;
        int sigsSuffixCount = 0;
        if (isPayToScriptHash()) {
            sigsPrefixCount = 1; // OP_0 <sig>* <redeemScript>
            sigsSuffixCount = 1;
        } else if (isSentToMultiSig()) {
            sigsPrefixCount = 1; // OP_0 <sig>*
        } else if (isSentToAddress()) {
            sigsSuffixCount = 1; // <sig> <pubkey>
        }
        return ScriptBuilder.updateScriptWithSignature(scriptSig, sigBytes, index, sigsPrefixCount, sigsSuffixCount);
    }


    /**
     * Returns the index where a signature by the key should be inserted.  Only applicable to
     * a P2SH scriptSig.
     */
    public int getSigInsertionIndex(Sha256Hash hash, ECKey signingKey) {
        // Iterate over existing signatures, skipping the initial OP_0, the final redeem script
        // and any placeholder OP_0 sigs.
        List<ScriptChunk> existingChunks = chunks.subList(1, chunks.size() - 1);
        ScriptChunk redeemScriptChunk = chunks.get(chunks.size() - 1);
        checkNotNull(redeemScriptChunk.data);
        Script redeemScript = new Script(redeemScriptChunk.data);

        int sigCount = 0;
        int myIndex = redeemScript.findKeyInRedeem(signingKey);
        for (ScriptChunk chunk : existingChunks) {
            if (chunk.opcode == OP_0) {
                // OP_0, skip
            } else {
                checkNotNull(chunk.data);
                if (myIndex < redeemScript.findSigInRedeem(chunk.data, hash))
                    return sigCount;
                sigCount++;
            }
        }
        return sigCount;
    }

    private int findKeyInRedeem(ECKey key) {
        checkArgument(chunks.get(0).isOpCode()); // P2SH scriptSig
        int numKeys = Script.decodeFromOpN(chunks.get(chunks.size() - 2).opcode);
        for (int i = 0 ; i < numKeys ; i++) {
            if (Arrays.equals(chunks.get(1 + i).data, key.getPubKey())) {
                return i;
            }
        }

        throw new IllegalStateException("Could not find matching key " + key.toString() + " in script " + this);
    }

    /**
     * Returns a list of the keys required by this script, assuming a multi-sig script.
     *
     * @throws ScriptException if the script type is not understood or is pay to address or is P2SH (run this method on the "Redeem script" instead).
     */
    public List<ECKey> getPubKeys() {
        if (!isSentToMultiSig())
            throw new ScriptException("Only usable for multisig scripts.");

        ArrayList<ECKey> result = Lists.newArrayList();
        int numKeys = Script.decodeFromOpN(chunks.get(chunks.size() - 2).opcode);
        for (int i = 0 ; i < numKeys ; i++)
            result.add(ECKey.fromPublicOnly(chunks.get(1 + i).data));
        return result;
    }

    private int findSigInRedeem(byte[] signatureBytes, Sha256Hash hash) {
        checkArgument(chunks.get(0).isOpCode()); // P2SH scriptSig
        int numKeys = Script.decodeFromOpN(chunks.get(chunks.size() - 2).opcode);
        TransactionSignature signature = TransactionSignature.decodeFromBitcoin(signatureBytes, true);
        for (int i = 0 ; i < numKeys ; i++) {
            if (ECKey.fromPublicOnly(chunks.get(i + 1).data).verify(hash, signature)) {
                return i;
            }
        }

        throw new IllegalStateException("Could not find matching key for signature on " + hash.toString() + " sig " + Utils.HEX.encode(signatureBytes));
    }



    ////////////////////// Interface used during verification of transactions/blocks ////////////////////////////////

    private static int getSigOpCount(List<ScriptChunk> chunks, boolean accurate) throws ScriptException {
        int sigOps = 0;
        int lastOpCode = OP_INVALIDOPCODE;
        for (ScriptChunk chunk : chunks) {
            if (chunk.isOpCode()) {
                switch (chunk.opcode) {
                case OP_CHECKSIG:
                case OP_CHECKSIGVERIFY:
                    sigOps++;
                    break;
                case OP_CHECKMULTISIG:
                case OP_CHECKMULTISIGVERIFY:
                    if (accurate && lastOpCode >= OP_1 && lastOpCode <= OP_16)
                        sigOps += decodeFromOpN(lastOpCode);
                    else
                        sigOps += 20;
                    break;
                default:
                    break;
                }
                lastOpCode = chunk.opcode;
            }
        }
        return sigOps;
    }

    static int decodeFromOpN(int opcode) {
        checkArgument((opcode == OP_0 || opcode == OP_1NEGATE) || (opcode >= OP_1 && opcode <= OP_16), "decodeFromOpN called on non OP_N opcode");
        if (opcode == OP_0)
            return 0;
        else if (opcode == OP_1NEGATE)
            return -1;
        else
            return opcode + 1 - OP_1;
    }

    static int encodeToOpN(int value) {
        checkArgument(value >= -1 && value <= 16, "encodeToOpN called for " + value + " which we cannot encode in an opcode.");
        if (value == 0)
            return OP_0;
        else if (value == -1)
            return OP_1NEGATE;
        else
            return value - 1 + OP_1;
    }

    /**
     * Gets the count of regular SigOps in the script program (counting multisig ops as 20)
     */
    public static int getSigOpCount(byte[] program) throws ScriptException {
        Script script = new Script();
        try {
            script.parse(program);
        } catch (ScriptException e) {
            // Ignore errors and count up to the parse-able length
        }
        return getSigOpCount(script.chunks, false);
    }
    
    /**
     * Gets the count of P2SH Sig Ops in the Script scriptSig
     */
    public static long getP2SHSigOpCount(byte[] scriptSig) throws ScriptException {
        Script script = new Script();
        try {
            script.parse(scriptSig);
        } catch (ScriptException e) {
            // Ignore errors and count up to the parse-able length
        }
        for (int i = script.chunks.size() - 1; i >= 0; i--)
            if (!script.chunks.get(i).isOpCode()) {
                Script subScript =  new Script();
                subScript.parse(script.chunks.get(i).data);
                return getSigOpCount(subScript.chunks, true);
            }
        return 0;
    }

    /**
     * Returns number of signatures required to satisfy this script.
     */
    public int getNumberOfSignaturesRequiredToSpend() {
        if (isSentToMultiSig()) {
            // for N of M CHECKMULTISIG script we will need N signatures to spend
            ScriptChunk nChunk = chunks.get(0);
            return Script.decodeFromOpN(nChunk.opcode);
        } else if (isSentToAddress() || isSentToRawPubKey()) {
            // pay-to-address and pay-to-pubkey require single sig
            return 1;
        } else if (isPayToScriptHash()) {
            throw new IllegalStateException("For P2SH number of signatures depends on redeem script");
        } else {
            throw new IllegalStateException("Unsupported script type");
        }
    }

    /**
     * Returns number of bytes required to spend this script. It accepts optional ECKey and redeemScript that may
     * be required for certain types of script to estimate target size.
     */
    public int getNumberOfBytesRequiredToSpend(@Nullable ECKey pubKey, @Nullable Script redeemScript) {
        if (isPayToScriptHash()) {
            // scriptSig: <sig> [sig] [sig...] <redeemscript>
            checkArgument(redeemScript != null, "P2SH script requires redeemScript to be spent");
            return redeemScript.getNumberOfSignaturesRequiredToSpend() * SIG_SIZE + redeemScript.getProgram().length;
        } else if (isSentToMultiSig()) {
            // scriptSig: OP_0 <sig> [sig] [sig...]
            return getNumberOfSignaturesRequiredToSpend() * SIG_SIZE + 1;
        } else if (isSentToRawPubKey()) {
            // scriptSig: <sig>
            return SIG_SIZE;
        } else if (isSentToAddress()) {
            // scriptSig: <sig> <pubkey>
            int uncompressedPubKeySize = 65;
            return SIG_SIZE + (pubKey != null ? pubKey.getPubKey().length : uncompressedPubKeySize);
        } else {
            throw new IllegalStateException("Unsupported script type");
        }
    }

    /**
     * <p>Whether or not this is a scriptPubKey representing a pay-to-script-hash output. In such outputs, the logic that
     * controls reclamation is not actually in the output at all. Instead there's just a hash, and it's up to the
     * spending input to provide a program matching that hash. This rule is "soft enforced" by the network as it does
     * not exist in Satoshis original implementation. It means blocks containing P2SH transactions that don't match
     * correctly are considered valid, but won't be mined upon, so they'll be rapidly re-orgd out of the chain. This
     * logic is defined by <a href="https://github.com/bitcoin/bips/blob/master/bip-0016.mediawiki">BIP 16</a>.</p>
     *
     * <p>bitcoinj does not support creation of P2SH transactions today. The goal of P2SH is to allow short addresses
     * even for complex scripts (eg, multi-sig outputs) so they are convenient to work with in things like QRcodes or
     * with copy/paste, and also to minimize the size of the unspent output set (which improves performance of the
     * Bitcoin system).</p>
     */
    public boolean isPayToScriptHash() {
        // We have to check against the serialized form because BIP16 defines a P2SH output using an exact byte
        // template, not the logical program structure. Thus you can have two programs that look identical when
        // printed out but one is a P2SH script and the other isn't! :(
        byte[] program = getProgram();
        return program.length == 23 &&
               (program[0] & 0xff) == OP_HASH160 &&
               (program[1] & 0xff) == 0x14 &&
               (program[22] & 0xff) == OP_EQUAL;
    }

    /**
     * Returns whether this script matches the format used for multisig outputs: [n] [keys...] [m] CHECKMULTISIG
     */
    public boolean isSentToMultiSig() {
        if (chunks.size() < 4) return false;
        ScriptChunk chunk = chunks.get(chunks.size() - 1);
        // Must end in OP_CHECKMULTISIG[VERIFY].
        if (!chunk.isOpCode()) return false;
        if (!(chunk.equalsOpCode(OP_CHECKMULTISIG) || chunk.equalsOpCode(OP_CHECKMULTISIGVERIFY))) return false;
        try {
            // Second to last chunk must be an OP_N opcode and there should be that many data chunks (keys).
            ScriptChunk m = chunks.get(chunks.size() - 2);
            if (!m.isOpCode()) return false;
            int numKeys = decodeFromOpN(m.opcode);
            if (numKeys < 1 || chunks.size() != 3 + numKeys) return false;
            for (int i = 1; i < chunks.size() - 2; i++) {
                if (chunks.get(i).isOpCode()) return false;
            }
            // First chunk must be an OP_N opcode too.
            if (decodeFromOpN(chunks.get(0).opcode) < 1) return false;
        } catch (IllegalStateException e) {
            return false;   // Not an OP_N opcode.
        }
        return true;
    }

    private static boolean equalsRange(byte[] a, int start, byte[] b) {
        if (start + b.length > a.length)
            return false;
        for (int i = 0; i < b.length; i++)
            if (a[i + start] != b[i])
                return false;
        return true;
    }
    
    /**
     * Returns the script bytes of inputScript with all instances of the specified script object removed
     */
    public static byte[] removeAllInstancesOf(byte[] inputScript, byte[] chunkToRemove) {
        // We usually don't end up removing anything
        UnsafeByteArrayOutputStream bos = new UnsafeByteArrayOutputStream(inputScript.length);

        int cursor = 0;
        while (cursor < inputScript.length) {
            boolean skip = equalsRange(inputScript, cursor, chunkToRemove);
            
            int opcode = inputScript[cursor++] & 0xFF;
            int additionalBytes = 0;
            if (opcode >= 0 && opcode < OP_PUSHDATA1) {
                additionalBytes = opcode;
            } else if (opcode == OP_PUSHDATA1) {
                additionalBytes = (0xFF & inputScript[cursor]) + 1;
            } else if (opcode == OP_PUSHDATA2) {
                additionalBytes = ((0xFF & inputScript[cursor]) |
                                  ((0xFF & inputScript[cursor+1]) << 8)) + 2;
            } else if (opcode == OP_PUSHDATA4) {
                additionalBytes = ((0xFF & inputScript[cursor]) |
                                  ((0xFF & inputScript[cursor+1]) << 8) |
                                  ((0xFF & inputScript[cursor+1]) << 16) |
                                  ((0xFF & inputScript[cursor+1]) << 24)) + 4;
            }
            if (!skip) {
                try {
                    bos.write(opcode);
                    bos.write(Arrays.copyOfRange(inputScript, cursor, cursor + additionalBytes));
                } catch (IOException e) {
                    throw new RuntimeException(e);
                }
            }
            cursor += additionalBytes;
        }
        return bos.toByteArray();
    }
    
    /**
     * Returns the script bytes of inputScript with all instances of the given op code removed
     */
    public static byte[] removeAllInstancesOfOp(byte[] inputScript, int opCode) {
        return removeAllInstancesOf(inputScript, new byte[] {(byte)opCode});
    }
    
    ////////////////////// Script verification and helpers ////////////////////////////////
    
    private static boolean castToBool(byte[] data) {
        for (int i = 0; i < data.length; i++)
        {
            // "Can be negative zero" -reference client (see OpenSSL's BN_bn2mpi)
            if (data[i] != 0)
                return !(i == data.length - 1 && (data[i] & 0xFF) == 0x80);
        }
        return false;
    }
    
    private static BigInteger castToBigInteger(byte[] chunk) throws ScriptException {
        if (chunk.length > 4)
            throw new ScriptException("Script attempted to use an integer larger than 4 bytes");
        return Utils.decodeMPI(Utils.reverseBytes(chunk), false);
    }

    public boolean isOpReturn() {
        return chunks.size() == 2 && chunks.get(0).equalsOpCode(OP_RETURN);
    }

    /**
     * Exposes the script interpreter. Normally you should not use this directly, instead use
     * {@link org.bitcoinj.core.TransactionInput#verify(org.bitcoinj.core.TransactionOutput)} or
     * {@link org.bitcoinj.script.Script#correctlySpends(org.bitcoinj.core.Transaction, long, Script)}. This method
     * is useful if you need more precise control or access to the final state of the stack. This interface is very
     * likely to change in future.
     */
    public static void executeScript(@Nullable Transaction txContainingThis, long index,
                                     Script script, LinkedList<byte[]> stack, boolean enforceNullDummy) throws ScriptException {
        int opCount = 0;
        int lastCodeSepLocation = 0;
        
        LinkedList<byte[]> altstack = new LinkedList<byte[]>();
        LinkedList<Boolean> ifStack = new LinkedList<Boolean>();
        
        for (ScriptChunk chunk : script.chunks) {
            boolean shouldExecute = !ifStack.contains(false);
            
            if (!chunk.isOpCode()) {
                if (chunk.data.length > MAX_SCRIPT_ELEMENT_SIZE)
                    throw new ScriptException("Attempted to push a data string larger than 520 bytes");
                
                if (!shouldExecute)
                    continue;
                
                stack.add(chunk.data);
            } else {
                int opcode = chunk.opcode;
                if (opcode > OP_16) {
                    opCount++;
                    if (opCount > 201)
                        throw new ScriptException("More script operations than is allowed");
                }
                
                if (opcode == OP_VERIF || opcode == OP_VERNOTIF)
                    throw new ScriptException("Script included OP_VERIF or OP_VERNOTIF");
                
                if (opcode == OP_CAT || opcode == OP_SUBSTR || opcode == OP_LEFT || opcode == OP_RIGHT ||
                    opcode == OP_INVERT || opcode == OP_AND || opcode == OP_OR || opcode == OP_XOR ||
                    opcode == OP_2MUL || opcode == OP_2DIV || opcode == OP_MUL || opcode == OP_DIV ||
                    opcode == OP_MOD || opcode == OP_LSHIFT || opcode == OP_RSHIFT)
                    throw new ScriptException("Script included a disabled Script Op.");
                
                switch (opcode) {
                case OP_IF:
                    if (!shouldExecute) {
                        ifStack.add(false);
                        continue;
                    }
                    if (stack.size() < 1)
                        throw new ScriptException("Attempted OP_IF on an empty stack");
                    ifStack.add(castToBool(stack.pollLast()));
                    continue;
                case OP_NOTIF:
                    if (!shouldExecute) {
                        ifStack.add(false);
                        continue;
                    }
                    if (stack.size() < 1)
                        throw new ScriptException("Attempted OP_NOTIF on an empty stack");
                    ifStack.add(!castToBool(stack.pollLast()));
                    continue;
                case OP_ELSE:
                    if (ifStack.isEmpty())
                        throw new ScriptException("Attempted OP_ELSE without OP_IF/NOTIF");
                    ifStack.add(!ifStack.pollLast());
                    continue;
                case OP_ENDIF:
                    if (ifStack.isEmpty())
                        throw new ScriptException("Attempted OP_ENDIF without OP_IF/NOTIF");
                    ifStack.pollLast();
                    continue;
                }
                
                if (!shouldExecute)
                    continue;
                
                switch(opcode) {
                // OP_0 is no opcode
                case OP_1NEGATE:
                    stack.add(Utils.reverseBytes(Utils.encodeMPI(BigInteger.ONE.negate(), false)));
                    break;
                case OP_1:
                case OP_2:
                case OP_3:
                case OP_4:
                case OP_5:
                case OP_6:
                case OP_7:
                case OP_8:
                case OP_9:
                case OP_10:
                case OP_11:
                case OP_12:
                case OP_13:
                case OP_14:
                case OP_15:
                case OP_16:
                    stack.add(Utils.reverseBytes(Utils.encodeMPI(BigInteger.valueOf(decodeFromOpN(opcode)), false)));
                    break;
                case OP_NOP:
                    break;
                case OP_VERIFY:
                    if (stack.size() < 1)
                        throw new ScriptException("Attempted OP_VERIFY on an empty stack");
                    if (!castToBool(stack.pollLast()))
                        throw new ScriptException("OP_VERIFY failed");
                    break;
                case OP_RETURN:
                    throw new ScriptException("Script called OP_RETURN");
                case OP_TOALTSTACK:
                    if (stack.size() < 1)
                        throw new ScriptException("Attempted OP_TOALTSTACK on an empty stack");
                    altstack.add(stack.pollLast());
                    break;
                case OP_FROMALTSTACK:
                    if (altstack.size() < 1)
                        throw new ScriptException("Attempted OP_TOALTSTACK on an empty altstack");
                    stack.add(altstack.pollLast());
                    break;
                case OP_2DROP:
                    if (stack.size() < 2)
                        throw new ScriptException("Attempted OP_2DROP on a stack with size < 2");
                    stack.pollLast();
                    stack.pollLast();
                    break;
                case OP_2DUP:
                    if (stack.size() < 2)
                        throw new ScriptException("Attempted OP_2DUP on a stack with size < 2");
                    Iterator<byte[]> it2DUP = stack.descendingIterator();
                    byte[] OP2DUPtmpChunk2 = it2DUP.next();
                    stack.add(it2DUP.next());
                    stack.add(OP2DUPtmpChunk2);
                    break;
                case OP_3DUP:
                    if (stack.size() < 3)
                        throw new ScriptException("Attempted OP_3DUP on a stack with size < 3");
                    Iterator<byte[]> it3DUP = stack.descendingIterator();
                    byte[] OP3DUPtmpChunk3 = it3DUP.next();
                    byte[] OP3DUPtmpChunk2 = it3DUP.next();
                    stack.add(it3DUP.next());
                    stack.add(OP3DUPtmpChunk2);
                    stack.add(OP3DUPtmpChunk3);
                    break;
                case OP_2OVER:
                    if (stack.size() < 4)
                        throw new ScriptException("Attempted OP_2OVER on a stack with size < 4");
                    Iterator<byte[]> it2OVER = stack.descendingIterator();
                    it2OVER.next();
                    it2OVER.next();
                    byte[] OP2OVERtmpChunk2 = it2OVER.next();
                    stack.add(it2OVER.next());
                    stack.add(OP2OVERtmpChunk2);
                    break;
                case OP_2ROT:
                    if (stack.size() < 6)
                        throw new ScriptException("Attempted OP_2ROT on a stack with size < 6");
                    byte[] OP2ROTtmpChunk6 = stack.pollLast();
                    byte[] OP2ROTtmpChunk5 = stack.pollLast();
                    byte[] OP2ROTtmpChunk4 = stack.pollLast();
                    byte[] OP2ROTtmpChunk3 = stack.pollLast();
                    byte[] OP2ROTtmpChunk2 = stack.pollLast();
                    byte[] OP2ROTtmpChunk1 = stack.pollLast();
                    stack.add(OP2ROTtmpChunk3);
                    stack.add(OP2ROTtmpChunk4);
                    stack.add(OP2ROTtmpChunk5);
                    stack.add(OP2ROTtmpChunk6);
                    stack.add(OP2ROTtmpChunk1);
                    stack.add(OP2ROTtmpChunk2);
                    break;
                case OP_2SWAP:
                    if (stack.size() < 4)
                        throw new ScriptException("Attempted OP_2SWAP on a stack with size < 4");
                    byte[] OP2SWAPtmpChunk4 = stack.pollLast();
                    byte[] OP2SWAPtmpChunk3 = stack.pollLast();
                    byte[] OP2SWAPtmpChunk2 = stack.pollLast();
                    byte[] OP2SWAPtmpChunk1 = stack.pollLast();
                    stack.add(OP2SWAPtmpChunk3);
                    stack.add(OP2SWAPtmpChunk4);
                    stack.add(OP2SWAPtmpChunk1);
                    stack.add(OP2SWAPtmpChunk2);
                    break;
                case OP_IFDUP:
                    if (stack.size() < 1)
                        throw new ScriptException("Attempted OP_IFDUP on an empty stack");
                    if (castToBool(stack.getLast()))
                        stack.add(stack.getLast());
                    break;
                case OP_DEPTH:
                    stack.add(Utils.reverseBytes(Utils.encodeMPI(BigInteger.valueOf(stack.size()), false)));
                    break;
                case OP_DROP:
                    if (stack.size() < 1)
                        throw new ScriptException("Attempted OP_DROP on an empty stack");
                    stack.pollLast();
                    break;
                case OP_DUP:
                    if (stack.size() < 1)
                        throw new ScriptException("Attempted OP_DUP on an empty stack");
                    stack.add(stack.getLast());
                    break;
                case OP_NIP:
                    if (stack.size() < 2)
                        throw new ScriptException("Attempted OP_NIP on a stack with size < 2");
                    byte[] OPNIPtmpChunk = stack.pollLast();
                    stack.pollLast();
                    stack.add(OPNIPtmpChunk);
                    break;
                case OP_OVER:
                    if (stack.size() < 2)
                        throw new ScriptException("Attempted OP_OVER on a stack with size < 2");
                    Iterator<byte[]> itOVER = stack.descendingIterator();
                    itOVER.next();
                    stack.add(itOVER.next());
                    break;
                case OP_PICK:
                case OP_ROLL:
                    if (stack.size() < 1)
                        throw new ScriptException("Attempted OP_PICK/OP_ROLL on an empty stack");
                    long val = castToBigInteger(stack.pollLast()).longValue();
                    if (val < 0 || val >= stack.size())
                        throw new ScriptException("OP_PICK/OP_ROLL attempted to get data deeper than stack size");
                    Iterator<byte[]> itPICK = stack.descendingIterator();
                    for (long i = 0; i < val; i++)
                        itPICK.next();
                    byte[] OPROLLtmpChunk = itPICK.next();
                    if (opcode == OP_ROLL)
                        itPICK.remove();
                    stack.add(OPROLLtmpChunk);
                    break;
                case OP_ROT:
                    if (stack.size() < 3)
                        throw new ScriptException("Attempted OP_ROT on a stack with size < 3");
                    byte[] OPROTtmpChunk3 = stack.pollLast();
                    byte[] OPROTtmpChunk2 = stack.pollLast();
                    byte[] OPROTtmpChunk1 = stack.pollLast();
                    stack.add(OPROTtmpChunk2);
                    stack.add(OPROTtmpChunk3);
                    stack.add(OPROTtmpChunk1);
                    break;
                case OP_SWAP:
                case OP_TUCK:
                    if (stack.size() < 2)
                        throw new ScriptException("Attempted OP_SWAP on a stack with size < 2");
                    byte[] OPSWAPtmpChunk2 = stack.pollLast();
                    byte[] OPSWAPtmpChunk1 = stack.pollLast();
                    stack.add(OPSWAPtmpChunk2);
                    stack.add(OPSWAPtmpChunk1);
                    if (opcode == OP_TUCK)
                        stack.add(OPSWAPtmpChunk2);
                    break;
                case OP_CAT:
                case OP_SUBSTR:
                case OP_LEFT:
                case OP_RIGHT:
                    throw new ScriptException("Attempted to use disabled Script Op.");
                case OP_SIZE:
                    if (stack.size() < 1)
                        throw new ScriptException("Attempted OP_SIZE on an empty stack");
                    stack.add(Utils.reverseBytes(Utils.encodeMPI(BigInteger.valueOf(stack.getLast().length), false)));
                    break;
                case OP_INVERT:
                case OP_AND:
                case OP_OR:
                case OP_XOR:
                    throw new ScriptException("Attempted to use disabled Script Op.");
                case OP_EQUAL:
                    if (stack.size() < 2)
                        throw new ScriptException("Attempted OP_EQUALVERIFY on a stack with size < 2");
                    stack.add(Arrays.equals(stack.pollLast(), stack.pollLast()) ? new byte[] {1} : new byte[] {0});
                    break;
                case OP_EQUALVERIFY:
                    if (stack.size() < 2)
                        throw new ScriptException("Attempted OP_EQUALVERIFY on a stack with size < 2");
                    if (!Arrays.equals(stack.pollLast(), stack.pollLast()))
                        throw new ScriptException("OP_EQUALVERIFY: non-equal data");
                    break;
                case OP_1ADD:
                case OP_1SUB:
                case OP_NEGATE:
                case OP_ABS:
                case OP_NOT:
                case OP_0NOTEQUAL:
                    if (stack.size() < 1)
                        throw new ScriptException("Attempted a numeric op on an empty stack");
                    BigInteger numericOPnum = castToBigInteger(stack.pollLast());
                                        
                    switch (opcode) {
                    case OP_1ADD:
                        numericOPnum = numericOPnum.add(BigInteger.ONE);
                        break;
                    case OP_1SUB:
                        numericOPnum = numericOPnum.subtract(BigInteger.ONE);
                        break;
                    case OP_NEGATE:
                        numericOPnum = numericOPnum.negate();
                        break;
                    case OP_ABS:
                        if (numericOPnum.signum() < 0)
                            numericOPnum = numericOPnum.negate();
                        break;
                    case OP_NOT:
                        if (numericOPnum.equals(BigInteger.ZERO))
                            numericOPnum = BigInteger.ONE;
                        else
                            numericOPnum = BigInteger.ZERO;
                        break;
                    case OP_0NOTEQUAL:
                        if (numericOPnum.equals(BigInteger.ZERO))
                            numericOPnum = BigInteger.ZERO;
                        else
                            numericOPnum = BigInteger.ONE;
                        break;
                    default:
                        throw new AssertionError("Unreachable");
                    }
                    
                    stack.add(Utils.reverseBytes(Utils.encodeMPI(numericOPnum, false)));
                    break;
                case OP_2MUL:
                case OP_2DIV:
                    throw new ScriptException("Attempted to use disabled Script Op.");
                case OP_ADD:
                case OP_SUB:
                case OP_BOOLAND:
                case OP_BOOLOR:
                case OP_NUMEQUAL:
                case OP_NUMNOTEQUAL:
                case OP_LESSTHAN:
                case OP_GREATERTHAN:
                case OP_LESSTHANOREQUAL:
                case OP_GREATERTHANOREQUAL:
                case OP_MIN:
                case OP_MAX:
                    if (stack.size() < 2)
                        throw new ScriptException("Attempted a numeric op on a stack with size < 2");
                    BigInteger numericOPnum2 = castToBigInteger(stack.pollLast());
                    BigInteger numericOPnum1 = castToBigInteger(stack.pollLast());

                    BigInteger numericOPresult;
                    switch (opcode) {
                    case OP_ADD:
                        numericOPresult = numericOPnum1.add(numericOPnum2);
                        break;
                    case OP_SUB:
                        numericOPresult = numericOPnum1.subtract(numericOPnum2);
                        break;
                    case OP_BOOLAND:
                        if (!numericOPnum1.equals(BigInteger.ZERO) && !numericOPnum2.equals(BigInteger.ZERO))
                            numericOPresult = BigInteger.ONE;
                        else
                            numericOPresult = BigInteger.ZERO;
                        break;
                    case OP_BOOLOR:
                        if (!numericOPnum1.equals(BigInteger.ZERO) || !numericOPnum2.equals(BigInteger.ZERO))
                            numericOPresult = BigInteger.ONE;
                        else
                            numericOPresult = BigInteger.ZERO;
                        break;
                    case OP_NUMEQUAL:
                        if (numericOPnum1.equals(numericOPnum2))
                            numericOPresult = BigInteger.ONE;
                        else
                            numericOPresult = BigInteger.ZERO;
                        break;
                    case OP_NUMNOTEQUAL:
                        if (!numericOPnum1.equals(numericOPnum2))
                            numericOPresult = BigInteger.ONE;
                        else
                            numericOPresult = BigInteger.ZERO;
                        break;
                    case OP_LESSTHAN:
                        if (numericOPnum1.compareTo(numericOPnum2) < 0)
                            numericOPresult = BigInteger.ONE;
                        else
                            numericOPresult = BigInteger.ZERO;
                        break;
                    case OP_GREATERTHAN:
                        if (numericOPnum1.compareTo(numericOPnum2) > 0)
                            numericOPresult = BigInteger.ONE;
                        else
                            numericOPresult = BigInteger.ZERO;
                        break;
                    case OP_LESSTHANOREQUAL:
                        if (numericOPnum1.compareTo(numericOPnum2) <= 0)
                            numericOPresult = BigInteger.ONE;
                        else
                            numericOPresult = BigInteger.ZERO;
                        break;
                    case OP_GREATERTHANOREQUAL:
                        if (numericOPnum1.compareTo(numericOPnum2) >= 0)
                            numericOPresult = BigInteger.ONE;
                        else
                            numericOPresult = BigInteger.ZERO;
                        break;
                    case OP_MIN:
                        if (numericOPnum1.compareTo(numericOPnum2) < 0)
                            numericOPresult = numericOPnum1;
                        else
                            numericOPresult = numericOPnum2;
                        break;
                    case OP_MAX:
                        if (numericOPnum1.compareTo(numericOPnum2) > 0)
                            numericOPresult = numericOPnum1;
                        else
                            numericOPresult = numericOPnum2;
                        break;
                    default:
                        throw new RuntimeException("Opcode switched at runtime?");
                    }
                    
                    stack.add(Utils.reverseBytes(Utils.encodeMPI(numericOPresult, false)));
                    break;
                case OP_MUL:
                case OP_DIV:
                case OP_MOD:
                case OP_LSHIFT:
                case OP_RSHIFT:
                    throw new ScriptException("Attempted to use disabled Script Op.");
                case OP_NUMEQUALVERIFY:
                    if (stack.size() < 2)
                        throw new ScriptException("Attempted OP_NUMEQUALVERIFY on a stack with size < 2");
                    BigInteger OPNUMEQUALVERIFYnum2 = castToBigInteger(stack.pollLast());
                    BigInteger OPNUMEQUALVERIFYnum1 = castToBigInteger(stack.pollLast());
                    
                    if (!OPNUMEQUALVERIFYnum1.equals(OPNUMEQUALVERIFYnum2))
                        throw new ScriptException("OP_NUMEQUALVERIFY failed");
                    break;
                case OP_WITHIN:
                    if (stack.size() < 3)
                        throw new ScriptException("Attempted OP_WITHIN on a stack with size < 3");
                    BigInteger OPWITHINnum3 = castToBigInteger(stack.pollLast());
                    BigInteger OPWITHINnum2 = castToBigInteger(stack.pollLast());
                    BigInteger OPWITHINnum1 = castToBigInteger(stack.pollLast());
                    if (OPWITHINnum2.compareTo(OPWITHINnum1) <= 0 && OPWITHINnum1.compareTo(OPWITHINnum3) < 0)
                        stack.add(Utils.reverseBytes(Utils.encodeMPI(BigInteger.ONE, false)));
                    else
                        stack.add(Utils.reverseBytes(Utils.encodeMPI(BigInteger.ZERO, false)));
                    break;
                case OP_RIPEMD160:
                    if (stack.size() < 1)
                        throw new ScriptException("Attempted OP_RIPEMD160 on an empty stack");
                    RIPEMD160Digest digest = new RIPEMD160Digest();
                    byte[] dataToHash = stack.pollLast();
                    digest.update(dataToHash, 0, dataToHash.length);
                    byte[] ripmemdHash = new byte[20];
                    digest.doFinal(ripmemdHash, 0);
                    stack.add(ripmemdHash);
                    break;
                case OP_SHA1:
                    if (stack.size() < 1)
                        throw new ScriptException("Attempted OP_SHA1 on an empty stack");
                    try {
                        stack.add(MessageDigest.getInstance("SHA-1").digest(stack.pollLast()));
                    } catch (NoSuchAlgorithmException e) {
                        throw new RuntimeException(e);  // Cannot happen.
                    }
                    break;
                case OP_SHA256:
                    if (stack.size() < 1)
                        throw new ScriptException("Attempted OP_SHA256 on an empty stack");
                    stack.add(Utils.singleDigest(stack.pollLast()));
                    break;
                case OP_HASH160:
                    if (stack.size() < 1)
                        throw new ScriptException("Attempted OP_HASH160 on an empty stack");
                    stack.add(Utils.sha256hash160(stack.pollLast()));
                    break;
                case OP_HASH256:
                    if (stack.size() < 1)
                        throw new ScriptException("Attempted OP_SHA256 on an empty stack");
                    stack.add(Utils.doubleDigest(stack.pollLast()));
                    break;
                case OP_CODESEPARATOR:
                    lastCodeSepLocation = chunk.getStartLocationInProgram() + 1;
                    break;
                case OP_CHECKSIG:
                case OP_CHECKSIGVERIFY:
                    if (txContainingThis == null)
                        throw new IllegalStateException("Script attempted signature check but no tx was provided");
                    executeCheckSig(txContainingThis, (int) index, script, stack, lastCodeSepLocation, opcode);
                    break;
                case OP_CHECKMULTISIG:
                case OP_CHECKMULTISIGVERIFY:
                    if (txContainingThis == null)
                        throw new IllegalStateException("Script attempted signature check but no tx was provided");
                    opCount = executeMultiSig(txContainingThis, (int) index, script, stack, opCount, lastCodeSepLocation, opcode, enforceNullDummy);
                    break;
                case OP_NOP1:
                case OP_NOP2:
                case OP_NOP3:
                case OP_NOP4:
                case OP_NOP5:
                case OP_NOP6:
                case OP_NOP7:
                case OP_NOP8:
                case OP_NOP9:
                case OP_NOP10:
                    break;
                    
                default:
                    throw new ScriptException("Script used a reserved opcode " + opcode);
                }
            }
            
            if (stack.size() + altstack.size() > 1000 || stack.size() + altstack.size() < 0)
                throw new ScriptException("Stack size exceeded range");
        }
        
        if (!ifStack.isEmpty())
            throw new ScriptException("OP_IF/OP_NOTIF without OP_ENDIF");
    }

    private static void executeCheckSig(Transaction txContainingThis, int index, Script script, LinkedList<byte[]> stack,
                                        int lastCodeSepLocation, int opcode) throws ScriptException {
        if (stack.size() < 2)
            throw new ScriptException("Attempted OP_CHECKSIG(VERIFY) on a stack with size < 2");
        byte[] pubKey = stack.pollLast();
        byte[] sigBytes = stack.pollLast();

        byte[] prog = script.getProgram();
        byte[] connectedScript = Arrays.copyOfRange(prog, lastCodeSepLocation, prog.length);

        UnsafeByteArrayOutputStream outStream = new UnsafeByteArrayOutputStream(sigBytes.length + 1);
        try {
            writeBytes(outStream, sigBytes);
        } catch (IOException e) {
            throw new RuntimeException(e); // Cannot happen
        }
        connectedScript = removeAllInstancesOf(connectedScript, outStream.toByteArray());

        // TODO: Use int for indexes everywhere, we can't have that many inputs/outputs
        boolean sigValid = false;
        try {
            TransactionSignature sig  = TransactionSignature.decodeFromBitcoin(sigBytes, false);
            Sha256Hash hash = txContainingThis.hashForSignature(index, connectedScript, (byte) sig.sighashFlags);
            sigValid = ECKey.verify(hash.getBytes(), sig, pubKey);
        } catch (Exception e1) {
            // There is (at least) one exception that could be hit here (EOFException, if the sig is too short)
            // Because I can't verify there aren't more, we use a very generic Exception catch

            // This RuntimeException occurs when signing as we run partial/invalid scripts to see if they need more
            // signing work to be done inside LocalTransactionSigner.signInputs.
            if (!e1.getMessage().contains("Reached past end of ASN.1 stream"))
                log.warn("Signature checking failed! {}", e1.toString());
        }

        if (opcode == OP_CHECKSIG)
            stack.add(sigValid ? new byte[] {1} : new byte[] {0});
        else if (opcode == OP_CHECKSIGVERIFY)
            if (!sigValid)
                throw new ScriptException("Script failed OP_CHECKSIGVERIFY");
    }

    private static int executeMultiSig(Transaction txContainingThis, int index, Script script, LinkedList<byte[]> stack,
                                       int opCount, int lastCodeSepLocation, int opcode, boolean enforceNullDummy) throws ScriptException {
        if (stack.size() < 2)
            throw new ScriptException("Attempted OP_CHECKMULTISIG(VERIFY) on a stack with size < 2");
        int pubKeyCount = castToBigInteger(stack.pollLast()).intValue();
        if (pubKeyCount < 0 || pubKeyCount > 20)
            throw new ScriptException("OP_CHECKMULTISIG(VERIFY) with pubkey count out of range");
        opCount += pubKeyCount;
        if (opCount > 201)
            throw new ScriptException("Total op count > 201 during OP_CHECKMULTISIG(VERIFY)");
        if (stack.size() < pubKeyCount + 1)
            throw new ScriptException("Attempted OP_CHECKMULTISIG(VERIFY) on a stack with size < num_of_pubkeys + 2");

        LinkedList<byte[]> pubkeys = new LinkedList<byte[]>();
        for (int i = 0; i < pubKeyCount; i++) {
            byte[] pubKey = stack.pollLast();
            pubkeys.add(pubKey);
        }

        int sigCount = castToBigInteger(stack.pollLast()).intValue();
        if (sigCount < 0 || sigCount > pubKeyCount)
            throw new ScriptException("OP_CHECKMULTISIG(VERIFY) with sig count out of range");
        if (stack.size() < sigCount + 1)
            throw new ScriptException("Attempted OP_CHECKMULTISIG(VERIFY) on a stack with size < num_of_pubkeys + num_of_signatures + 3");

        LinkedList<byte[]> sigs = new LinkedList<byte[]>();
        for (int i = 0; i < sigCount; i++) {
            byte[] sig = stack.pollLast();
            sigs.add(sig);
        }

        byte[] prog = script.getProgram();
        byte[] connectedScript = Arrays.copyOfRange(prog, lastCodeSepLocation, prog.length);

        for (byte[] sig : sigs) {
            UnsafeByteArrayOutputStream outStream = new UnsafeByteArrayOutputStream(sig.length + 1);
            try {
                writeBytes(outStream, sig);
            } catch (IOException e) {
                throw new RuntimeException(e); // Cannot happen
            }
            connectedScript = removeAllInstancesOf(connectedScript, outStream.toByteArray());
        }

        boolean valid = true;
        while (sigs.size() > 0) {
            byte[] pubKey = pubkeys.pollFirst();
            // We could reasonably move this out of the loop, but because signature verification is significantly
            // more expensive than hashing, its not a big deal.
            try {
                TransactionSignature sig = TransactionSignature.decodeFromBitcoin(sigs.getFirst(), false);
                Sha256Hash hash = txContainingThis.hashForSignature(index, connectedScript, (byte) sig.sighashFlags);
                if (ECKey.verify(hash.getBytes(), sig, pubKey))
                    sigs.pollFirst();
            } catch (Exception e) {
                // There is (at least) one exception that could be hit here (EOFException, if the sig is too short)
                // Because I can't verify there aren't more, we use a very generic Exception catch
            }

            if (sigs.size() > pubkeys.size()) {
                valid = false;
                break;
            }
        }

        // We uselessly remove a stack object to emulate a reference client bug.
        byte[] nullDummy = stack.pollLast();
        if (enforceNullDummy && nullDummy.length > 0)
            throw new ScriptException("OP_CHECKMULTISIG(VERIFY) with non-null nulldummy: " + Arrays.toString(nullDummy));

        if (opcode == OP_CHECKMULTISIG) {
            stack.add(valid ? new byte[] {1} : new byte[] {0});
        } else if (opcode == OP_CHECKMULTISIGVERIFY) {
            if (!valid)
                throw new ScriptException("Script failed OP_CHECKMULTISIGVERIFY");
        }
        return opCount;
    }

    /**
     * Verifies that this script (interpreted as a scriptSig) correctly spends the given scriptPubKey, enabling all
     * validation rules.
     * @param txContainingThis The transaction in which this input scriptSig resides.
     *                         Accessing txContainingThis from another thread while this method runs results in undefined behavior.
     * @param scriptSigIndex The index in txContainingThis of the scriptSig (note: NOT the index of the scriptPubKey).
     * @param scriptPubKey The connected scriptPubKey containing the conditions needed to claim the value.
     */
    public void correctlySpends(Transaction txContainingThis, long scriptSigIndex, Script scriptPubKey)
            throws ScriptException {
        correctlySpends(txContainingThis, scriptSigIndex, scriptPubKey, ALL_VERIFY_FLAGS);
    }

    /**
     * Verifies that this script (interpreted as a scriptSig) correctly spends the given scriptPubKey.
     * @param txContainingThis The transaction in which this input scriptSig resides.
     *                         Accessing txContainingThis from another thread while this method runs results in undefined behavior.
     * @param scriptSigIndex The index in txContainingThis of the scriptSig (note: NOT the index of the scriptPubKey).
     * @param scriptPubKey The connected scriptPubKey containing the conditions needed to claim the value.
     * @param verifyFlags Each flag enables one validation rule. If in doubt, use {@link #correctlySpends(Transaction, long, Script)}
     *                    which sets all flags.
     */
    public void correctlySpends(Transaction txContainingThis, long scriptSigIndex, Script scriptPubKey,
                                Set<VerifyFlag> verifyFlags) throws ScriptException {
        // Clone the transaction because executing the script involves editing it, and if we die, we'll leave
        // the tx half broken (also it's not so thread safe to work on it directly.
        try {
            txContainingThis = new Transaction(txContainingThis.getParams(), txContainingThis.bitcoinSerialize());
        } catch (ProtocolException e) {
            throw new RuntimeException(e);   // Should not happen unless we were given a totally broken transaction.
        }
        if (getProgram().length > 10000 || scriptPubKey.getProgram().length > 10000)
            throw new ScriptException("Script larger than 10,000 bytes");
        
        LinkedList<byte[]> stack = new LinkedList<byte[]>();
        LinkedList<byte[]> p2shStack = null;
        
        executeScript(txContainingThis, scriptSigIndex, this, stack, verifyFlags.contains(VerifyFlag.NULLDUMMY));
        if (verifyFlags.contains(VerifyFlag.P2SH))
            p2shStack = new LinkedList<byte[]>(stack);
        executeScript(txContainingThis, scriptSigIndex, scriptPubKey, stack, verifyFlags.contains(VerifyFlag.NULLDUMMY));
        
        if (stack.size() == 0)
            throw new ScriptException("Stack empty at end of script execution.");
        
        if (!castToBool(stack.pollLast()))
            throw new ScriptException("Script resulted in a non-true stack: " + stack);

        // P2SH is pay to script hash. It means that the scriptPubKey has a special form which is a valid
        // program but it has "useless" form that if evaluated as a normal program always returns true.
        // Instead, miners recognize it as special based on its template - it provides a hash of the real scriptPubKey
        // and that must be provided by the input. The goal of this bizarre arrangement is twofold:
        //
        // (1) You can sum up a large, complex script (like a CHECKMULTISIG script) with an address that's the same
        //     size as a regular address. This means it doesn't overload scannable QR codes/NFC tags or become
        //     un-wieldy to copy/paste.
        // (2) It allows the working set to be smaller: nodes perform best when they can store as many unspent outputs
        //     in RAM as possible, so if the outputs are made smaller and the inputs get bigger, then it's better for
        //     overall scalability and performance.

        // TODO: Check if we can take out enforceP2SH if there's a checkpoint at the enforcement block.
        if (verifyFlags.contains(VerifyFlag.P2SH) && scriptPubKey.isPayToScriptHash()) {
            for (ScriptChunk chunk : chunks)
                if (chunk.isOpCode() && chunk.opcode > OP_16)
                    throw new ScriptException("Attempted to spend a P2SH scriptPubKey with a script that contained script ops");
            
            byte[] scriptPubKeyBytes = p2shStack.pollLast();
            Script scriptPubKeyP2SH = new Script(scriptPubKeyBytes);
            
            executeScript(txContainingThis, scriptSigIndex, scriptPubKeyP2SH, p2shStack, verifyFlags.contains(VerifyFlag.NULLDUMMY));
            
            if (p2shStack.size() == 0)
                throw new ScriptException("P2SH stack empty at end of script execution.");
            
            if (!castToBool(p2shStack.pollLast()))
                throw new ScriptException("P2SH script execution resulted in a non-true stack");
        }
    }

    // Utility that doesn't copy for internal use
    private byte[] getQuickProgram() {
        if (program != null)
            return program;
        return getProgram();
    }

    /**
     * Get the {@link org.bitcoinj.script.Script.ScriptType}.
     * @return The script type.
     */
    public ScriptType getScriptType() {
        ScriptType type = ScriptType.NO_TYPE;
        if (isSentToAddress()) {
            type = ScriptType.P2PKH;
        } else if (isSentToRawPubKey()) {
            type = ScriptType.PUB_KEY;
        } else if (isPayToScriptHash()) {
            type = ScriptType.P2SH;
        }
        return type;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Script other = (Script) o;
        return Arrays.equals(getQuickProgram(), other.getQuickProgram());
    }

    @Override
    public int hashCode() {
        byte[] bytes = getQuickProgram();
        return Arrays.hashCode(bytes);
    }
}


File: core/src/test/java/org/bitcoinj/protocols/channels/ChannelConnectionTest.java
/*
 * Copyright 2013 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.protocols.channels;

import org.bitcoinj.core.*;
import org.bitcoinj.store.WalletProtobufSerializer;
import org.bitcoinj.testing.TestWithWallet;
import org.bitcoinj.utils.Threading;
import org.bitcoinj.wallet.WalletFiles;
import com.google.common.util.concurrent.Futures;
import com.google.common.util.concurrent.ListenableFuture;
import com.google.common.util.concurrent.SettableFuture;
import com.google.protobuf.ByteString;
import org.bitcoin.paymentchannel.Protos;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.spongycastle.crypto.params.KeyParameter;

import javax.annotation.Nullable;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.net.InetSocketAddress;
import java.net.SocketAddress;
import java.util.Arrays;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.bitcoinj.core.Coin.*;
import static org.bitcoinj.protocols.channels.PaymentChannelCloseException.CloseReason;
import static org.bitcoinj.testing.FakeTxBuilder.createFakeBlock;
import static org.bitcoin.paymentchannel.Protos.TwoWayChannelMessage.MessageType;
import static org.junit.Assert.*;

public class ChannelConnectionTest extends TestWithWallet {
    private static final int CLIENT_MAJOR_VERSION = 1;
    private Wallet serverWallet;
    private AtomicBoolean fail;
    private BlockingQueue<Transaction> broadcasts;
    private TransactionBroadcaster mockBroadcaster;
    private Semaphore broadcastTxPause;

    private static final TransactionBroadcaster failBroadcaster = new TransactionBroadcaster() {
        @Override
        public TransactionBroadcast broadcastTransaction(Transaction tx) {
            fail();
            return null;
        }
    };

    @Override
    @Before
    public void setUp() throws Exception {
        super.setUp();
        Utils.setMockClock(); // Use mock clock
        sendMoneyToWallet(COIN, AbstractBlockChain.NewBlockType.BEST_CHAIN);
        sendMoneyToWallet(COIN, AbstractBlockChain.NewBlockType.BEST_CHAIN);
        wallet.addExtension(new StoredPaymentChannelClientStates(wallet, failBroadcaster));
        Context context = new Context(params, 3);  // Shorter event horizon for unit tests.
        serverWallet = new Wallet(context);
        serverWallet.addExtension(new StoredPaymentChannelServerStates(serverWallet, failBroadcaster));
        serverWallet.freshReceiveKey();
        // Use an atomic boolean to indicate failure because fail()/assert*() dont work in network threads
        fail = new AtomicBoolean(false);

        // Set up a way to monitor broadcast transactions. When you expect a broadcast, you must release a permit
        // to the broadcastTxPause semaphore so state can be queried in between.
        broadcasts = new LinkedBlockingQueue<Transaction>();
        broadcastTxPause = new Semaphore(0);
        mockBroadcaster = new TransactionBroadcaster() {
            @Override
            public TransactionBroadcast broadcastTransaction(Transaction tx) {
                broadcastTxPause.acquireUninterruptibly();
                SettableFuture<Transaction> future = SettableFuture.create();
                future.set(tx);
                broadcasts.add(tx);
                return TransactionBroadcast.createMockBroadcast(tx, future);
            }
        };

        // Because there are no separate threads in the tests here (we call back into client/server in server/client
        // handlers), we have lots of lock cycles. A normal user shouldn't have this issue as they are probably not both
        // client+server running in the same thread.
        Threading.warnOnLockCycles();

        ECKey.FAKE_SIGNATURES = true;
    }

    @After
    @Override
    public void tearDown() throws Exception {
        super.tearDown();
        ECKey.FAKE_SIGNATURES = false;
    }

    @After
    public void checkFail() {
        assertFalse(fail.get());
        Threading.throwOnLockCycles();
    }

    @Test
    public void testSimpleChannel() throws Exception {
        exectuteSimpleChannelTest(null);
    }

    @Test
    public void testEncryptedClientWallet() throws Exception {
        // Encrypt the client wallet
        String mySecretPw = "MySecret";
        wallet.encrypt(mySecretPw);

        KeyParameter userKeySetup = wallet.getKeyCrypter().deriveKey(mySecretPw);
        exectuteSimpleChannelTest(userKeySetup);
    }

    public void exectuteSimpleChannelTest(KeyParameter userKeySetup) throws Exception {
        // Test with network code and without any issues. We'll broadcast two txns: multisig contract and settle transaction.
        final SettableFuture<ListenableFuture<PaymentChannelServerState>> serverCloseFuture = SettableFuture.create();
        final SettableFuture<Sha256Hash> channelOpenFuture = SettableFuture.create();
        final BlockingQueue<ChannelTestUtils.UpdatePair> q = new LinkedBlockingQueue<ChannelTestUtils.UpdatePair>();
        final PaymentChannelServerListener server = new PaymentChannelServerListener(mockBroadcaster, serverWallet, 30, COIN,
                new PaymentChannelServerListener.HandlerFactory() {
                    @Nullable
                    @Override
                    public ServerConnectionEventHandler onNewConnection(SocketAddress clientAddress) {
                        return new ServerConnectionEventHandler() {
                            @Override
                            public void channelOpen(Sha256Hash channelId) {
                                channelOpenFuture.set(channelId);
                            }

                            @Override
                            public ListenableFuture<ByteString> paymentIncrease(Coin by, Coin to, ByteString info) {
                                q.add(new ChannelTestUtils.UpdatePair(to, info));
                                return Futures.immediateFuture(info);
                            }

                            @Override
                            public void channelClosed(CloseReason reason) {
                                serverCloseFuture.set(null);
                            }
                        };
                    }
                });
        server.bindAndStart(4243);

        PaymentChannelClientConnection client = new PaymentChannelClientConnection(
                new InetSocketAddress("localhost", 4243), 30, wallet, myKey, COIN, "", PaymentChannelClient.DEFAULT_TIME_WINDOW, userKeySetup);

        // Wait for the multi-sig tx to be transmitted.
        broadcastTxPause.release();
        Transaction broadcastMultiSig = broadcasts.take();
        // Wait for the channel to finish opening.
        client.getChannelOpenFuture().get();
        assertEquals(broadcastMultiSig.getHash(), channelOpenFuture.get());
        assertEquals(Transaction.REFERENCE_DEFAULT_MIN_TX_FEE, client.state().getValueSpent());

        // Set up an autosave listener to make sure the server is saving the wallet after each payment increase.
        final CountDownLatch latch = new CountDownLatch(3);  // Expect 3 calls.
        File tempFile = File.createTempFile("channel_connection_test", ".wallet");
        tempFile.deleteOnExit();
        serverWallet.autosaveToFile(tempFile, 0, TimeUnit.SECONDS, new WalletFiles.Listener() {
            @Override
            public void onBeforeAutoSave(File tempFile) {
                latch.countDown();
            }

            @Override
            public void onAfterAutoSave(File newlySavedFile) {
            }
        });

        Thread.sleep(1250); // No timeouts once the channel is open
        Coin amount = client.state().getValueSpent();
        q.take().assertPair(amount, null);
        for (String info : new String[] {null, "one", "two"} ) {
            final ByteString bytes = (info==null) ? null :ByteString.copyFromUtf8(info);
            final PaymentIncrementAck ack = client.incrementPayment(CENT, bytes, userKeySetup).get();
            if (info != null) {
                final ByteString ackInfo = ack.getInfo();
                assertNotNull("Ack info is null", ackInfo);
                assertEquals("Ack info differs ", info, ackInfo.toStringUtf8());
            }
            amount = amount.add(CENT);
            q.take().assertPair(amount, bytes);
        }
        latch.await();

        StoredPaymentChannelServerStates channels = (StoredPaymentChannelServerStates)serverWallet.getExtensions().get(StoredPaymentChannelServerStates.EXTENSION_ID);
        StoredServerChannel storedServerChannel = channels.getChannel(broadcastMultiSig.getHash());
        PaymentChannelServerState serverState = storedServerChannel.getOrCreateState(serverWallet, mockBroadcaster);

        // Check that you can call settle multiple times with no exceptions.
        client.settle();
        client.settle();

        broadcastTxPause.release();
        Transaction settleTx = broadcasts.take();
        assertEquals(PaymentChannelServerState.State.CLOSED, serverState.getState());
        if (!serverState.getBestValueToMe().equals(amount) || !serverState.getFeePaid().equals(Coin.ZERO))
            fail();
        assertTrue(channels.mapChannels.isEmpty());

        // Send the settle TX to the client wallet.
        sendMoneyToWallet(settleTx, AbstractBlockChain.NewBlockType.BEST_CHAIN);
        assertEquals(PaymentChannelClientState.State.CLOSED, client.state().getState());

        server.close();
        server.close();

        // Now confirm the settle TX and see if the channel deletes itself from the wallet.
        assertEquals(1, StoredPaymentChannelClientStates.getFromWallet(wallet).mapChannels.size());
        wallet.notifyNewBestBlock(createFakeBlock(blockStore).storedBlock);
        assertEquals(1, StoredPaymentChannelClientStates.getFromWallet(wallet).mapChannels.size());
        wallet.notifyNewBestBlock(createFakeBlock(blockStore).storedBlock);
        assertEquals(0, StoredPaymentChannelClientStates.getFromWallet(wallet).mapChannels.size());
    }

    @Test
    public void testServerErrorHandling() throws Exception {
        // Gives the server crap and checks proper error responses are sent.
        ChannelTestUtils.RecordingPair pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
        PaymentChannelClient client = new PaymentChannelClient(wallet, myKey, COIN, Sha256Hash.ZERO_HASH, pair.clientRecorder);
        PaymentChannelServer server = pair.server;
        server.connectionOpen();
        client.connectionOpen();

        // Make sure we get back a BAD_TRANSACTION if we send a bogus refund transaction.
        server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.CLIENT_VERSION));
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.SERVER_VERSION));
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.INITIATE));
        Protos.TwoWayChannelMessage msg = pair.clientRecorder.checkNextMsg(MessageType.PROVIDE_REFUND);
        server.receiveMessage(Protos.TwoWayChannelMessage.newBuilder()
                .setType(MessageType.PROVIDE_REFUND)
                .setProvideRefund(
                        Protos.ProvideRefund.newBuilder(msg.getProvideRefund())
                                .setMultisigKey(ByteString.EMPTY)
                                .setTx(ByteString.EMPTY)
                ).build());
        final Protos.TwoWayChannelMessage errorMsg = pair.serverRecorder.checkNextMsg(MessageType.ERROR);
        assertEquals(Protos.Error.ErrorCode.BAD_TRANSACTION, errorMsg.getError().getCode());

        // Make sure the server closes the socket on CLOSE
        pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
        client = new PaymentChannelClient(wallet, myKey, COIN, Sha256Hash.ZERO_HASH, pair.clientRecorder);
        server = pair.server;
        server.connectionOpen();
        client.connectionOpen();
        server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.CLIENT_VERSION));
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.SERVER_VERSION));
        client.settle();
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.INITIATE));
        server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.CLOSE));
        assertEquals(CloseReason.CLIENT_REQUESTED_CLOSE, pair.serverRecorder.q.take());


        // Make sure the server closes the socket on ERROR
        pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
        client = new PaymentChannelClient(wallet, myKey, COIN, Sha256Hash.ZERO_HASH, pair.clientRecorder);
        server = pair.server;
        server.connectionOpen();
        client.connectionOpen();
        server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.CLIENT_VERSION));
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.SERVER_VERSION));
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.INITIATE));
        server.receiveMessage(Protos.TwoWayChannelMessage.newBuilder()
                .setType(MessageType.ERROR)
                .setError(Protos.Error.newBuilder().setCode(Protos.Error.ErrorCode.TIMEOUT))
                .build());
        assertEquals(CloseReason.REMOTE_SENT_ERROR, pair.serverRecorder.q.take());
    }

    @Test
    public void testChannelResume() throws Exception {
        // Tests various aspects of channel resuming.
        Utils.setMockClock();

        final Sha256Hash someServerId = Sha256Hash.hash(new byte[]{});

        // Open up a normal channel.
        ChannelTestUtils.RecordingPair pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
        pair.server.connectionOpen();
        PaymentChannelClient client = new PaymentChannelClient(wallet, myKey, COIN, someServerId, pair.clientRecorder);
        PaymentChannelServer server = pair.server;
        client.connectionOpen();
        server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.CLIENT_VERSION));
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.SERVER_VERSION));
        final Protos.TwoWayChannelMessage initiateMsg = pair.serverRecorder.checkNextMsg(MessageType.INITIATE);
        Coin minPayment = Coin.valueOf(initiateMsg.getInitiate().getMinPayment());
        client.receiveMessage(initiateMsg);
        server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.PROVIDE_REFUND));
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.RETURN_REFUND));
        broadcastTxPause.release();
        server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.PROVIDE_CONTRACT));
        broadcasts.take();
        pair.serverRecorder.checkTotalPayment(Transaction.REFERENCE_DEFAULT_MIN_TX_FEE);
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.CHANNEL_OPEN));
        Sha256Hash contractHash = (Sha256Hash) pair.serverRecorder.q.take();
        pair.clientRecorder.checkInitiated();
        assertNull(pair.serverRecorder.q.poll());
        assertNull(pair.clientRecorder.q.poll());
        assertEquals(minPayment, client.state().getValueSpent());
        // Send a bitcent.
        Coin amount = minPayment.add(CENT);
        client.incrementPayment(CENT);
        server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.UPDATE_PAYMENT));
        assertEquals(amount, ((ChannelTestUtils.UpdatePair)pair.serverRecorder.q.take()).amount);
        server.close();
        server.connectionClosed();
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.PAYMENT_ACK));
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.CLOSE));
        client.connectionClosed();
        assertFalse(client.connectionOpen);

        // There is now an inactive open channel worth COIN-CENT + minPayment with id Sha256.create(new byte[] {})
        StoredPaymentChannelClientStates clientStoredChannels =
                (StoredPaymentChannelClientStates) wallet.getExtensions().get(StoredPaymentChannelClientStates.EXTENSION_ID);
        assertEquals(1, clientStoredChannels.mapChannels.size());
        assertFalse(clientStoredChannels.mapChannels.values().iterator().next().active);

        // Check that server-side won't attempt to reopen a nonexistent channel (it will tell the client to re-initiate
        // instead).
        pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
        pair.server.connectionOpen();
        pair.server.receiveMessage(Protos.TwoWayChannelMessage.newBuilder()
                .setType(MessageType.CLIENT_VERSION)
                .setClientVersion(Protos.ClientVersion.newBuilder()
                        .setPreviousChannelContractHash(ByteString.copyFrom(Utils.singleDigest(new byte[]{0x03})))
                        .setMajor(CLIENT_MAJOR_VERSION).setMinor(42))
                .build());
        pair.serverRecorder.checkNextMsg(MessageType.SERVER_VERSION);
        pair.serverRecorder.checkNextMsg(MessageType.INITIATE);

        // Now reopen/resume the channel after round-tripping the wallets.
        wallet = roundTripClientWallet(wallet);
        serverWallet = roundTripServerWallet(serverWallet);
        clientStoredChannels =
                (StoredPaymentChannelClientStates) wallet.getExtensions().get(StoredPaymentChannelClientStates.EXTENSION_ID);

        pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
        client = new PaymentChannelClient(wallet, myKey, COIN, someServerId, pair.clientRecorder);
        server = pair.server;
        client.connectionOpen();
        server.connectionOpen();
        // Check the contract hash is sent on the wire correctly.
        final Protos.TwoWayChannelMessage clientVersionMsg = pair.clientRecorder.checkNextMsg(MessageType.CLIENT_VERSION);
        assertTrue(clientVersionMsg.getClientVersion().hasPreviousChannelContractHash());
        assertEquals(contractHash, new Sha256Hash(clientVersionMsg.getClientVersion().getPreviousChannelContractHash().toByteArray()));
        server.receiveMessage(clientVersionMsg);
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.SERVER_VERSION));
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.CHANNEL_OPEN));
        assertEquals(contractHash, pair.serverRecorder.q.take());
        pair.clientRecorder.checkOpened();
        assertNull(pair.serverRecorder.q.poll());
        assertNull(pair.clientRecorder.q.poll());
        // Send another bitcent and check 2 were received in total.
        client.incrementPayment(CENT);
        amount = amount.add(CENT);
        server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.UPDATE_PAYMENT));
        pair.serverRecorder.checkTotalPayment(amount);
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.PAYMENT_ACK));

        PaymentChannelClient openClient = client;
        ChannelTestUtils.RecordingPair openPair = pair;

        // Now open up a new client with the same id and make sure the server disconnects the previous client.
        pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
        client = new PaymentChannelClient(wallet, myKey, COIN, someServerId, pair.clientRecorder);
        server = pair.server;
        client.connectionOpen();
        server.connectionOpen();
        // Check that no prev contract hash is sent on the wire the client notices it's already in use by another
        // client attached to the same wallet and refuses to resume.
        {
            Protos.TwoWayChannelMessage msg = pair.clientRecorder.checkNextMsg(MessageType.CLIENT_VERSION);
            assertFalse(msg.getClientVersion().hasPreviousChannelContractHash());
        }
        // Make sure the server allows two simultaneous opens. It will close the first and allow resumption of the second.
        pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
        client = new PaymentChannelClient(wallet, myKey, COIN, someServerId, pair.clientRecorder);
        server = pair.server;
        client.connectionOpen();
        server.connectionOpen();
        // Swap out the clients version message for a custom one that tries to resume ...
        pair.clientRecorder.getNextMsg();
        server.receiveMessage(Protos.TwoWayChannelMessage.newBuilder()
                .setType(MessageType.CLIENT_VERSION)
                .setClientVersion(Protos.ClientVersion.newBuilder()
                        .setPreviousChannelContractHash(ByteString.copyFrom(contractHash.getBytes()))
                        .setMajor(CLIENT_MAJOR_VERSION).setMinor(42))
                .build());
        // We get the usual resume sequence.
        pair.serverRecorder.checkNextMsg(MessageType.SERVER_VERSION);
        pair.serverRecorder.checkNextMsg(MessageType.CHANNEL_OPEN);
        // Verify the previous one was closed.
        openPair.serverRecorder.checkNextMsg(MessageType.CLOSE);

        assertTrue(clientStoredChannels.getChannel(someServerId, contractHash).active);

        // And finally close the first channel too.
        openClient.connectionClosed();
        assertFalse(clientStoredChannels.getChannel(someServerId, contractHash).active);

        // Now roll the mock clock and recreate the client object so that it removes the channels and announces refunds.
        assertEquals(86640, clientStoredChannels.getSecondsUntilExpiry(someServerId));
        Utils.rollMockClock(60 * 60 * 24 + 60 * 5);   // Client announces refund 5 minutes after expire time
        StoredPaymentChannelClientStates newClientStates = new StoredPaymentChannelClientStates(wallet, mockBroadcaster);
        newClientStates.deserializeWalletExtension(wallet, clientStoredChannels.serializeWalletExtension());
        broadcastTxPause.release();
        assertTrue(broadcasts.take().getOutput(0).getScriptPubKey().isSentToMultiSig());
        broadcastTxPause.release();
        assertEquals(TransactionConfidence.Source.SELF, broadcasts.take().getConfidence().getSource());
        assertTrue(broadcasts.isEmpty());
        assertTrue(newClientStates.mapChannels.isEmpty());
        // Server also knows it's too late.
        StoredPaymentChannelServerStates serverStoredChannels = new StoredPaymentChannelServerStates(serverWallet, mockBroadcaster);
        Thread.sleep(2000);   // TODO: Fix this stupid hack.
        assertTrue(serverStoredChannels.mapChannels.isEmpty());
    }

    private static Wallet roundTripClientWallet(Wallet wallet) throws Exception {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        new WalletProtobufSerializer().writeWallet(wallet, bos);
        org.bitcoinj.wallet.Protos.Wallet proto = WalletProtobufSerializer.parseToProto(new ByteArrayInputStream(bos.toByteArray()));
        StoredPaymentChannelClientStates state = new StoredPaymentChannelClientStates(null, failBroadcaster);
        return new WalletProtobufSerializer().readWallet(wallet.getParams(), new WalletExtension[] { state }, proto);
    }

    private static Wallet roundTripServerWallet(Wallet wallet) throws Exception {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        new WalletProtobufSerializer().writeWallet(wallet, bos);
        StoredPaymentChannelServerStates state = new StoredPaymentChannelServerStates(null, failBroadcaster);
        org.bitcoinj.wallet.Protos.Wallet proto = WalletProtobufSerializer.parseToProto(new ByteArrayInputStream(bos.toByteArray()));
        return new WalletProtobufSerializer().readWallet(wallet.getParams(), new WalletExtension[] { state }, proto);
    }

    @Test
    public void testBadResumeHash() throws InterruptedException {
        // Check that server-side will reject incorrectly formatted hashes. If anything goes wrong with session resume,
        // then the server will start the opening of a new channel automatically, so we expect to see INITIATE here.
        ChannelTestUtils.RecordingPair srv =
                ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
        srv.server.connectionOpen();
        srv.server.receiveMessage(Protos.TwoWayChannelMessage.newBuilder()
                .setType(MessageType.CLIENT_VERSION)
                .setClientVersion(Protos.ClientVersion.newBuilder()
                        .setPreviousChannelContractHash(ByteString.copyFrom(new byte[]{0x00, 0x01}))
                        .setMajor(CLIENT_MAJOR_VERSION).setMinor(42))
                .build());

        srv.serverRecorder.checkNextMsg(MessageType.SERVER_VERSION);
        srv.serverRecorder.checkNextMsg(MessageType.INITIATE);
        assertTrue(srv.serverRecorder.q.isEmpty());
    }

    @Test
    public void testClientUnknownVersion() throws Exception {
        // Tests client rejects unknown version
        ChannelTestUtils.RecordingPair pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
        PaymentChannelClient client = new PaymentChannelClient(wallet, myKey, COIN, Sha256Hash.ZERO_HASH, pair.clientRecorder);
        client.connectionOpen();
        pair.clientRecorder.checkNextMsg(MessageType.CLIENT_VERSION);
        client.receiveMessage(Protos.TwoWayChannelMessage.newBuilder()
                .setServerVersion(Protos.ServerVersion.newBuilder().setMajor(-1))
                .setType(MessageType.SERVER_VERSION).build());
        pair.clientRecorder.checkNextMsg(MessageType.ERROR);
        assertEquals(CloseReason.NO_ACCEPTABLE_VERSION, pair.clientRecorder.q.take());
        // Double-check that we cant do anything that requires an open channel
        try {
            client.incrementPayment(Coin.SATOSHI);
            fail();
        } catch (IllegalStateException e) { }
    }

    @Test
    public void testClientTimeWindowUnacceptable() throws Exception {
        // Tests that clients reject too large time windows
        ChannelTestUtils.RecordingPair pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster, 100);
        PaymentChannelServer server = pair.server;
        PaymentChannelClient client = new PaymentChannelClient(wallet, myKey, COIN, Sha256Hash.ZERO_HASH, pair.clientRecorder);
        client.connectionOpen();
        server.connectionOpen();
        server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.CLIENT_VERSION));
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.SERVER_VERSION));
        client.receiveMessage(Protos.TwoWayChannelMessage.newBuilder()
                .setInitiate(Protos.Initiate.newBuilder().setExpireTimeSecs(Utils.currentTimeSeconds() + 60 * 60 * 48)
                        .setMinAcceptedChannelSize(100)
                        .setMultisigKey(ByteString.copyFrom(new ECKey().getPubKey()))
                        .setMinPayment(Transaction.MIN_NONDUST_OUTPUT.value))
                .setType(MessageType.INITIATE).build());

        pair.clientRecorder.checkNextMsg(MessageType.ERROR);
        assertEquals(CloseReason.TIME_WINDOW_UNACCEPTABLE, pair.clientRecorder.q.take());
        // Double-check that we cant do anything that requires an open channel
        try {
            client.incrementPayment(Coin.SATOSHI);
            fail();
        } catch (IllegalStateException e) { }
    }

    @Test
    public void testValuesAreRespected() throws Exception {
        ChannelTestUtils.RecordingPair pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
        PaymentChannelServer server = pair.server;
        PaymentChannelClient client = new PaymentChannelClient(wallet, myKey, COIN, Sha256Hash.ZERO_HASH, pair.clientRecorder);
        client.connectionOpen();
        server.connectionOpen();
        server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.CLIENT_VERSION));
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.SERVER_VERSION));
        client.receiveMessage(Protos.TwoWayChannelMessage.newBuilder()
                .setInitiate(Protos.Initiate.newBuilder().setExpireTimeSecs(Utils.currentTimeSeconds())
                        .setMinAcceptedChannelSize(COIN.add(SATOSHI).value)
                        .setMultisigKey(ByteString.copyFrom(new ECKey().getPubKey()))
                        .setMinPayment(Transaction.MIN_NONDUST_OUTPUT.value))
                .setType(MessageType.INITIATE).build());
        pair.clientRecorder.checkNextMsg(MessageType.ERROR);
        assertEquals(CloseReason.SERVER_REQUESTED_TOO_MUCH_VALUE, pair.clientRecorder.q.take());
        // Double-check that we cant do anything that requires an open channel
        try {
            client.incrementPayment(Coin.SATOSHI);
            fail();
        } catch (IllegalStateException e) { }

        // Now check that if the server has a lower min size than what we are willing to spend, we do actually open
        // a channel of that size.
        sendMoneyToWallet(COIN.multiply(10), AbstractBlockChain.NewBlockType.BEST_CHAIN);

        pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
        server = pair.server;
        final Coin myValue = COIN.multiply(10);
        client = new PaymentChannelClient(wallet, myKey, myValue, Sha256Hash.ZERO_HASH, pair.clientRecorder);
        client.connectionOpen();
        server.connectionOpen();
        server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.CLIENT_VERSION));
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.SERVER_VERSION));
        client.receiveMessage(Protos.TwoWayChannelMessage.newBuilder()
                .setInitiate(Protos.Initiate.newBuilder().setExpireTimeSecs(Utils.currentTimeSeconds())
                        .setMinAcceptedChannelSize(COIN.add(SATOSHI).value)
                        .setMultisigKey(ByteString.copyFrom(new ECKey().getPubKey()))
                        .setMinPayment(Transaction.REFERENCE_DEFAULT_MIN_TX_FEE.value))
                .setType(MessageType.INITIATE).build());
        final Protos.TwoWayChannelMessage provideRefund = pair.clientRecorder.checkNextMsg(MessageType.PROVIDE_REFUND);
        Transaction refund = new Transaction(params, provideRefund.getProvideRefund().getTx().toByteArray());
        assertEquals(myValue, refund.getOutput(0).getValue());
    }

    @Test
    public void testEmptyWallet() throws Exception {
        Wallet emptyWallet = new Wallet(params);
        emptyWallet.freshReceiveKey();
        ChannelTestUtils.RecordingPair pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
        PaymentChannelServer server = pair.server;
        PaymentChannelClient client = new PaymentChannelClient(emptyWallet, myKey, COIN, Sha256Hash.ZERO_HASH, pair.clientRecorder);
        client.connectionOpen();
        server.connectionOpen();
        server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.CLIENT_VERSION));
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.SERVER_VERSION));
        try {
            client.receiveMessage(Protos.TwoWayChannelMessage.newBuilder()
                    .setInitiate(Protos.Initiate.newBuilder().setExpireTimeSecs(Utils.currentTimeSeconds())
                            .setMinAcceptedChannelSize(CENT.value)
                            .setMultisigKey(ByteString.copyFrom(new ECKey().getPubKey()))
                            .setMinPayment(Transaction.REFERENCE_DEFAULT_MIN_TX_FEE.value))
                    .setType(MessageType.INITIATE).build());
            fail();
        } catch (InsufficientMoneyException expected) {
            // This should be thrown.
        }
    }

    @Test
    public void testClientRefusesNonCanonicalKey() throws Exception {
        ChannelTestUtils.RecordingPair pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
        PaymentChannelServer server = pair.server;
        PaymentChannelClient client = new PaymentChannelClient(wallet, myKey, COIN, Sha256Hash.ZERO_HASH, pair.clientRecorder);
        client.connectionOpen();
        server.connectionOpen();
        server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.CLIENT_VERSION));
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.SERVER_VERSION));
        Protos.TwoWayChannelMessage.Builder initiateMsg = Protos.TwoWayChannelMessage.newBuilder(pair.serverRecorder.checkNextMsg(MessageType.INITIATE));
        ByteString brokenKey = initiateMsg.getInitiate().getMultisigKey();
        brokenKey = ByteString.copyFrom(Arrays.copyOf(brokenKey.toByteArray(), brokenKey.size() + 1));
        initiateMsg.getInitiateBuilder().setMultisigKey(brokenKey);
        client.receiveMessage(initiateMsg.build());
        pair.clientRecorder.checkNextMsg(MessageType.ERROR);
        assertEquals(CloseReason.REMOTE_SENT_INVALID_MESSAGE, pair.clientRecorder.q.take());
    }

    @Test
    public void testClientResumeNothing() throws Exception {
        ChannelTestUtils.RecordingPair pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
        PaymentChannelServer server = pair.server;
        PaymentChannelClient client = new PaymentChannelClient(wallet, myKey, COIN, Sha256Hash.ZERO_HASH, pair.clientRecorder);
        client.connectionOpen();
        server.connectionOpen();
        server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.CLIENT_VERSION));
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.SERVER_VERSION));
        client.receiveMessage(Protos.TwoWayChannelMessage.newBuilder()
                .setType(MessageType.CHANNEL_OPEN).build());
        pair.clientRecorder.checkNextMsg(MessageType.ERROR);
        assertEquals(CloseReason.REMOTE_SENT_INVALID_MESSAGE, pair.clientRecorder.q.take());
    }

    @Test
    public void testClientRandomMessage() throws Exception {
        ChannelTestUtils.RecordingPair pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
        PaymentChannelClient client = new PaymentChannelClient(wallet, myKey, COIN, Sha256Hash.ZERO_HASH, pair.clientRecorder);

        client.connectionOpen();
        pair.clientRecorder.checkNextMsg(MessageType.CLIENT_VERSION);
        // Send a CLIENT_VERSION back to the client - ?!?!!
        client.receiveMessage(Protos.TwoWayChannelMessage.newBuilder()
                .setType(MessageType.CLIENT_VERSION).build());
        Protos.TwoWayChannelMessage error = pair.clientRecorder.checkNextMsg(MessageType.ERROR);
        assertEquals(Protos.Error.ErrorCode.SYNTAX_ERROR, error.getError().getCode());
        assertEquals(CloseReason.REMOTE_SENT_INVALID_MESSAGE, pair.clientRecorder.q.take());
   }

    @Test
    public void testDontResumeEmptyChannels() throws Exception {
        // Check that if the client has an empty channel that's being kept around in case we need to broadcast the
        // refund, we don't accidentally try to resume it).

        // Open up a normal channel.
        Sha256Hash someServerId = Sha256Hash.ZERO_HASH;
        ChannelTestUtils.RecordingPair pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
        pair.server.connectionOpen();
        PaymentChannelClient client = new PaymentChannelClient(wallet, myKey, COIN, someServerId, pair.clientRecorder);
        PaymentChannelServer server = pair.server;
        client.connectionOpen();
        server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.CLIENT_VERSION));
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.SERVER_VERSION));
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.INITIATE));
        server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.PROVIDE_REFUND));
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.RETURN_REFUND));
        broadcastTxPause.release();
        server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.PROVIDE_CONTRACT));
        broadcasts.take();
        pair.serverRecorder.checkTotalPayment(Transaction.REFERENCE_DEFAULT_MIN_TX_FEE);
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.CHANNEL_OPEN));
        Sha256Hash contractHash = (Sha256Hash) pair.serverRecorder.q.take();
        pair.clientRecorder.checkInitiated();
        assertNull(pair.serverRecorder.q.poll());
        assertNull(pair.clientRecorder.q.poll());
        // Send the whole channel at once. The server will broadcast the final contract and settle the channel for us.
        client.incrementPayment(client.state().getValueRefunded());
        broadcastTxPause.release();
        server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.UPDATE_PAYMENT));
        broadcasts.take();
        // The channel is now empty.
        assertEquals(Coin.ZERO, client.state().getValueRefunded());
        pair.serverRecorder.q.take();  // Take the Coin.
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.PAYMENT_ACK));
        client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.CLOSE));
        assertEquals(CloseReason.SERVER_REQUESTED_CLOSE, pair.clientRecorder.q.take());
        client.connectionClosed();

        // Now try opening a new channel with the same server ID and verify the client asks for a new channel.
        client = new PaymentChannelClient(wallet, myKey, COIN, someServerId, pair.clientRecorder);
        client.connectionOpen();
        Protos.TwoWayChannelMessage msg = pair.clientRecorder.checkNextMsg(MessageType.CLIENT_VERSION);
        assertFalse(msg.getClientVersion().hasPreviousChannelContractHash());
    }

    @Test
    public void repeatedChannels() throws Exception {
        // Ensures we're selecting channels correctly. Covers a bug in which we'd always try and fail to resume
        // the first channel due to lack of proper closing behaviour.
        // Open up a normal channel, but don't spend all of it, then settle it.
        {
            Sha256Hash someServerId = Sha256Hash.ZERO_HASH;
            ChannelTestUtils.RecordingPair pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
            pair.server.connectionOpen();
            PaymentChannelClient client = new PaymentChannelClient(wallet, myKey, COIN, someServerId, pair.clientRecorder);
            PaymentChannelServer server = pair.server;
            client.connectionOpen();
            server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.CLIENT_VERSION));
            client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.SERVER_VERSION));
            client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.INITIATE));
            server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.PROVIDE_REFUND));
            client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.RETURN_REFUND));
            broadcastTxPause.release();
            server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.PROVIDE_CONTRACT));
            broadcasts.take();
            pair.serverRecorder.checkTotalPayment(Transaction.REFERENCE_DEFAULT_MIN_TX_FEE);
            client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.CHANNEL_OPEN));
            Sha256Hash contractHash = (Sha256Hash) pair.serverRecorder.q.take();
            pair.clientRecorder.checkInitiated();
            assertNull(pair.serverRecorder.q.poll());
            assertNull(pair.clientRecorder.q.poll());
            for (int i = 0; i < 3; i++) {
                ListenableFuture<PaymentIncrementAck> future = client.incrementPayment(CENT);
                server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.UPDATE_PAYMENT));
                pair.serverRecorder.q.take();
                final Protos.TwoWayChannelMessage msg = pair.serverRecorder.checkNextMsg(MessageType.PAYMENT_ACK);
                final Protos.PaymentAck paymentAck = msg.getPaymentAck();
                assertTrue("No PaymentAck.Info", paymentAck.hasInfo());
                assertEquals("Wrong PaymentAck info", ByteString.copyFromUtf8(CENT.toPlainString()), paymentAck.getInfo());
                client.receiveMessage(msg);
                assertTrue(future.isDone());
                final PaymentIncrementAck paymentIncrementAck = future.get();
                assertEquals("Wrong value returned from increasePayment", CENT, paymentIncrementAck.getValue());
                assertEquals("Wrong info returned from increasePayment", ByteString.copyFromUtf8(CENT.toPlainString()), paymentIncrementAck.getInfo());
            }

            // Settle it and verify it's considered to be settled.
            broadcastTxPause.release();
            client.settle();
            server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.CLOSE));
            Transaction settlement1 = broadcasts.take();
            // Server sends back the settle TX it just broadcast.
            final Protos.TwoWayChannelMessage closeMsg = pair.serverRecorder.checkNextMsg(MessageType.CLOSE);
            final Transaction settlement2 = new Transaction(params, closeMsg.getSettlement().getTx().toByteArray());
            assertEquals(settlement1, settlement2);
            client.receiveMessage(closeMsg);
            assertNotNull(wallet.getTransaction(settlement2.getHash()));   // Close TX entered the wallet.
            sendMoneyToWallet(settlement1, AbstractBlockChain.NewBlockType.BEST_CHAIN);
            client.connectionClosed();
            server.connectionClosed();
        }
        // Now open a second channel and don't spend all of it/don't settle it.
        {
            Sha256Hash someServerId = Sha256Hash.ZERO_HASH;
            ChannelTestUtils.RecordingPair pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
            pair.server.connectionOpen();
            PaymentChannelClient client = new PaymentChannelClient(wallet, myKey, COIN, someServerId, pair.clientRecorder);
            PaymentChannelServer server = pair.server;
            client.connectionOpen();
            final Protos.TwoWayChannelMessage msg = pair.clientRecorder.checkNextMsg(MessageType.CLIENT_VERSION);
            assertFalse(msg.getClientVersion().hasPreviousChannelContractHash());
            server.receiveMessage(msg);
            client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.SERVER_VERSION));
            client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.INITIATE));
            server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.PROVIDE_REFUND));
            client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.RETURN_REFUND));
            broadcastTxPause.release();
            server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.PROVIDE_CONTRACT));
            broadcasts.take();
            pair.serverRecorder.checkTotalPayment(Transaction.REFERENCE_DEFAULT_MIN_TX_FEE);
            client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.CHANNEL_OPEN));
            Sha256Hash contractHash = (Sha256Hash) pair.serverRecorder.q.take();
            pair.clientRecorder.checkInitiated();
            assertNull(pair.serverRecorder.q.poll());
            assertNull(pair.clientRecorder.q.poll());
            client.incrementPayment(CENT);
            server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.UPDATE_PAYMENT));
            client.connectionClosed();
            server.connectionClosed();
        }
        // Now connect again and check we resume the second channel.
        {
            Sha256Hash someServerId = Sha256Hash.ZERO_HASH;
            ChannelTestUtils.RecordingPair pair = ChannelTestUtils.makeRecorders(serverWallet, mockBroadcaster);
            pair.server.connectionOpen();
            PaymentChannelClient client = new PaymentChannelClient(wallet, myKey, COIN, someServerId, pair.clientRecorder);
            PaymentChannelServer server = pair.server;
            client.connectionOpen();
            server.receiveMessage(pair.clientRecorder.checkNextMsg(MessageType.CLIENT_VERSION));
            client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.SERVER_VERSION));
            client.receiveMessage(pair.serverRecorder.checkNextMsg(MessageType.CHANNEL_OPEN));
        }
        assertEquals(2, StoredPaymentChannelClientStates.getFromWallet(wallet).mapChannels.size());
    }
}


File: core/src/test/java/org/bitcoinj/wallet/DeterministicKeyChainTest.java
/**
 * Copyright 2013 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.wallet;

import org.bitcoinj.core.*;
import org.bitcoinj.crypto.*;
import org.bitcoinj.params.MainNetParams;
import org.bitcoinj.params.UnitTestParams;
import org.bitcoinj.store.UnreadableWalletException;
import org.bitcoinj.utils.BriefLogFormatter;
import org.bitcoinj.utils.Threading;

import com.google.common.collect.ImmutableList;
import com.google.common.collect.Lists;
import org.junit.Before;
import org.junit.Test;
import org.spongycastle.crypto.params.KeyParameter;

import java.io.IOException;
import java.security.SecureRandom;
import java.util.List;

import static com.google.common.base.Preconditions.checkNotNull;
import static org.junit.Assert.*;

public class DeterministicKeyChainTest {
    private DeterministicKeyChain chain;
    private final byte[] ENTROPY = Utils.singleDigest("don't use a string seed like this in real life".getBytes());

    @Before
    public void setup() {
        BriefLogFormatter.init();
        // You should use a random seed instead. The secs constant comes from the unit test file, so we can compare
        // serialized data properly.
        long secs = 1389353062L;
        chain = new DeterministicKeyChain(ENTROPY, "", secs);
        chain.setLookaheadSize(10);
        assertEquals(secs, checkNotNull(chain.getSeed()).getCreationTimeSeconds());
    }

    @Test
    public void derive() throws Exception {
        ECKey key1 = chain.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertFalse(key1.isPubKeyOnly());
        ECKey key2 = chain.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertFalse(key2.isPubKeyOnly());

        final Address address = new Address(UnitTestParams.get(), "n1bQNoEx8uhmCzzA5JPG6sFdtsUQhwiQJV");
        assertEquals(address, key1.toAddress(UnitTestParams.get()));
        assertEquals("mnHUcqUVvrfi5kAaXJDQzBb9HsWs78b42R", key2.toAddress(UnitTestParams.get()).toString());
        assertEquals(key1, chain.findKeyFromPubHash(address.getHash160()));
        assertEquals(key2, chain.findKeyFromPubKey(key2.getPubKey()));

        key1.sign(Sha256Hash.ZERO_HASH);
        assertFalse(key1.isPubKeyOnly());

        ECKey key3 = chain.getKey(KeyChain.KeyPurpose.CHANGE);
        assertFalse(key3.isPubKeyOnly());
        assertEquals("mqumHgVDqNzuXNrszBmi7A2UpmwaPMx4HQ", key3.toAddress(UnitTestParams.get()).toString());
        key3.sign(Sha256Hash.ZERO_HASH);
        assertFalse(key3.isPubKeyOnly());
    }

    @Test
    public void getKeys() throws Exception {
        chain.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        chain.getKey(KeyChain.KeyPurpose.CHANGE);
        chain.maybeLookAhead();
        assertEquals(2, chain.getKeys(false).size());
    }

    @Test
    public void deriveAccountOne() throws Exception {
        long secs = 1389353062L;
        DeterministicKeyChain chain1 = new AccountOneChain(ENTROPY, "", secs);
        ECKey key1 = chain1.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        ECKey key2 = chain1.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);

        final Address address = new Address(UnitTestParams.get(), "n2nHHRHs7TiZScTuVhZUkzZfTfVgGYwy6X");
        assertEquals(address, key1.toAddress(UnitTestParams.get()));
        assertEquals("mnp2j9za5zMuz44vNxrJCXXhZsCdh89QXn", key2.toAddress(UnitTestParams.get()).toString());
        assertEquals(key1, chain1.findKeyFromPubHash(address.getHash160()));
        assertEquals(key2, chain1.findKeyFromPubKey(key2.getPubKey()));

        key1.sign(Sha256Hash.ZERO_HASH);

        ECKey key3 = chain1.getKey(KeyChain.KeyPurpose.CHANGE);
        assertEquals("mpjRhk13rvV7vmnszcUQVYVQzy4HLTPTQU", key3.toAddress(UnitTestParams.get()).toString());
        key3.sign(Sha256Hash.ZERO_HASH);
    }

    static class AccountOneChain extends DeterministicKeyChain {
        public AccountOneChain(byte[] entropy, String s, long secs) {
            super(entropy, s, secs);
        }

        public AccountOneChain(KeyCrypter crypter, DeterministicSeed seed) {
            super(seed, crypter);
        }

        @Override
        protected ImmutableList<ChildNumber> getAccountPath() {
            return ImmutableList.of(ChildNumber.ONE);
        }
    }

    @Test
    public void serializeAccountOne() throws Exception {
        long secs = 1389353062L;
        DeterministicKeyChain chain1 = new AccountOneChain(ENTROPY, "", secs);
        ECKey key1 = chain1.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);

        final Address address = new Address(UnitTestParams.get(), "n2nHHRHs7TiZScTuVhZUkzZfTfVgGYwy6X");
        assertEquals(address, key1.toAddress(UnitTestParams.get()));

        DeterministicKey watching = chain1.getWatchingKey();

        List<Protos.Key> keys = chain1.serializeToProtobuf();
        KeyChainFactory factory = new KeyChainFactory() {
            @Override
            public DeterministicKeyChain makeKeyChain(Protos.Key key, Protos.Key firstSubKey, DeterministicSeed seed, KeyCrypter crypter, boolean isMarried) {
                return new AccountOneChain(crypter, seed);
            }

            @Override
            public DeterministicKeyChain makeWatchingKeyChain(Protos.Key key, Protos.Key firstSubKey, DeterministicKey accountKey, boolean isFollowingKey, boolean isMarried) {
                throw new UnsupportedOperationException();
            }
        };

        chain1 = DeterministicKeyChain.fromProtobuf(keys, null, factory).get(0);

        ECKey key2 = chain1.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertEquals("mnp2j9za5zMuz44vNxrJCXXhZsCdh89QXn", key2.toAddress(UnitTestParams.get()).toString());
        assertEquals(key1, chain1.findKeyFromPubHash(address.getHash160()));
        assertEquals(key2, chain1.findKeyFromPubKey(key2.getPubKey()));

        key1.sign(Sha256Hash.ZERO_HASH);

        ECKey key3 = chain1.getKey(KeyChain.KeyPurpose.CHANGE);
        assertEquals("mpjRhk13rvV7vmnszcUQVYVQzy4HLTPTQU", key3.toAddress(UnitTestParams.get()).toString());
        key3.sign(Sha256Hash.ZERO_HASH);

        assertEquals(watching, chain1.getWatchingKey());
    }

    @Test
    public void signMessage() throws Exception {
        ECKey key = chain.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        key.verifyMessage("test", key.signMessage("test"));
    }

    @Test
    public void events() throws Exception {
        // Check that we get the right events at the right time.
        final List<List<ECKey>> listenerKeys = Lists.newArrayList();
        long secs = 1389353062L;
        chain = new DeterministicKeyChain(ENTROPY, "", secs);
        chain.addEventListener(new AbstractKeyChainEventListener() {
            @Override
            public void onKeysAdded(List<ECKey> keys) {
                listenerKeys.add(keys);
            }
        }, Threading.SAME_THREAD);
        assertEquals(0, listenerKeys.size());
        chain.setLookaheadSize(5);
        assertEquals(0, listenerKeys.size());
        ECKey key = chain.getKey(KeyChain.KeyPurpose.CHANGE);
        assertEquals(1, listenerKeys.size());  // 1 event
        final List<ECKey> firstEvent = listenerKeys.get(0);
        assertEquals(1, firstEvent.size());
        assertTrue(firstEvent.contains(key));   // order is not specified.
        listenerKeys.clear();

        chain.maybeLookAhead();
        final List<ECKey> secondEvent = listenerKeys.get(0);
        assertEquals(12, secondEvent.size());  // (5 lookahead keys, +1 lookahead threshold) * 2 chains
        listenerKeys.clear();

        chain.getKey(KeyChain.KeyPurpose.CHANGE);
        // At this point we've entered the threshold zone so more keys won't immediately trigger more generations.
        assertEquals(0, listenerKeys.size());  // 1 event
        final int lookaheadThreshold = chain.getLookaheadThreshold() + chain.getLookaheadSize();
        for (int i = 0; i < lookaheadThreshold; i++)
            chain.getKey(KeyChain.KeyPurpose.CHANGE);
        assertEquals(1, listenerKeys.size());  // 1 event
        assertEquals(1, listenerKeys.get(0).size());  // 1 key.
    }

    @Test
    public void random() {
        // Can't test much here but verify the constructor worked and the class is functional. The other tests rely on
        // a fixed seed to be deterministic.
        chain = new DeterministicKeyChain(new SecureRandom(), 384);
        chain.setLookaheadSize(10);
        chain.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS).sign(Sha256Hash.ZERO_HASH);
        chain.getKey(KeyChain.KeyPurpose.CHANGE).sign(Sha256Hash.ZERO_HASH);
    }

    @Test
    public void serializeUnencrypted() throws UnreadableWalletException {
        chain.maybeLookAhead();
        DeterministicKey key1 = chain.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        DeterministicKey key2 = chain.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        DeterministicKey key3 = chain.getKey(KeyChain.KeyPurpose.CHANGE);
        List<Protos.Key> keys = chain.serializeToProtobuf();
        // 1 mnemonic/seed, 1 master key, 1 account key, 2 internal keys, 3 derived, 20 lookahead and 5 lookahead threshold.
        int numItems =
                1  // mnemonic/seed
              + 1  // master key
              + 1  // account key
              + 2  // ext/int parent keys
              + (chain.getLookaheadSize() + chain.getLookaheadThreshold()) * 2   // lookahead zone on each chain
        ;
        assertEquals(numItems, keys.size());

        // Get another key that will be lost during round-tripping, to ensure we can derive it again.
        DeterministicKey key4 = chain.getKey(KeyChain.KeyPurpose.CHANGE);

        final String EXPECTED_SERIALIZATION = checkSerialization(keys, "deterministic-wallet-serialization.txt");

        // Round trip the data back and forth to check it is preserved.
        int oldLookaheadSize = chain.getLookaheadSize();
        chain = DeterministicKeyChain.fromProtobuf(keys, null).get(0);
        assertEquals(EXPECTED_SERIALIZATION, protoToString(chain.serializeToProtobuf()));
        assertEquals(key1, chain.findKeyFromPubHash(key1.getPubKeyHash()));
        assertEquals(key2, chain.findKeyFromPubHash(key2.getPubKeyHash()));
        assertEquals(key3, chain.findKeyFromPubHash(key3.getPubKeyHash()));
        assertEquals(key4, chain.getKey(KeyChain.KeyPurpose.CHANGE));
        key1.sign(Sha256Hash.ZERO_HASH);
        key2.sign(Sha256Hash.ZERO_HASH);
        key3.sign(Sha256Hash.ZERO_HASH);
        key4.sign(Sha256Hash.ZERO_HASH);
        assertEquals(oldLookaheadSize, chain.getLookaheadSize());
    }

    @Test(expected = IllegalStateException.class)
    public void notEncrypted() {
        chain.toDecrypted("fail");
    }

    @Test(expected = IllegalStateException.class)
    public void encryptTwice() {
        chain = chain.toEncrypted("once");
        chain = chain.toEncrypted("twice");
    }

    private void checkEncryptedKeyChain(DeterministicKeyChain encChain, DeterministicKey key1) {
        // Check we can look keys up and extend the chain without the AES key being provided.
        DeterministicKey encKey1 = encChain.findKeyFromPubKey(key1.getPubKey());
        DeterministicKey encKey2 = encChain.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertFalse(key1.isEncrypted());
        assertTrue(encKey1.isEncrypted());
        assertEquals(encKey1.getPubKeyPoint(), key1.getPubKeyPoint());
        final KeyParameter aesKey = checkNotNull(encChain.getKeyCrypter()).deriveKey("open secret");
        encKey1.sign(Sha256Hash.ZERO_HASH, aesKey);
        encKey2.sign(Sha256Hash.ZERO_HASH, aesKey);
        assertTrue(encChain.checkAESKey(aesKey));
        assertFalse(encChain.checkPassword("access denied"));
        assertTrue(encChain.checkPassword("open secret"));
    }

    @Test
    public void encryption() throws UnreadableWalletException {
        DeterministicKey key1 = chain.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        DeterministicKeyChain encChain = chain.toEncrypted("open secret");
        DeterministicKey encKey1 = encChain.findKeyFromPubKey(key1.getPubKey());
        checkEncryptedKeyChain(encChain, key1);

        // Round-trip to ensure de/serialization works and that we can store two chains and they both deserialize.
        List<Protos.Key> serialized = encChain.serializeToProtobuf();
        List<Protos.Key> doubled = Lists.newArrayListWithExpectedSize(serialized.size() * 2);
        doubled.addAll(serialized);
        doubled.addAll(serialized);
        final List<DeterministicKeyChain> chains = DeterministicKeyChain.fromProtobuf(doubled, encChain.getKeyCrypter());
        assertEquals(2, chains.size());
        encChain = chains.get(0);
        checkEncryptedKeyChain(encChain, chain.findKeyFromPubKey(key1.getPubKey()));
        encChain = chains.get(1);
        checkEncryptedKeyChain(encChain, chain.findKeyFromPubKey(key1.getPubKey()));

        DeterministicKey encKey2 = encChain.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        // Decrypt and check the keys match.
        DeterministicKeyChain decChain = encChain.toDecrypted("open secret");
        DeterministicKey decKey1 = decChain.findKeyFromPubHash(encKey1.getPubKeyHash());
        DeterministicKey decKey2 = decChain.findKeyFromPubHash(encKey2.getPubKeyHash());
        assertEquals(decKey1.getPubKeyPoint(), encKey1.getPubKeyPoint());
        assertEquals(decKey2.getPubKeyPoint(), encKey2.getPubKeyPoint());
        assertFalse(decKey1.isEncrypted());
        assertFalse(decKey2.isEncrypted());
        assertNotEquals(encKey1.getParent(), decKey1.getParent());   // parts of a different hierarchy
        // Check we can once again derive keys from the decrypted chain.
        decChain.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS).sign(Sha256Hash.ZERO_HASH);
        decChain.getKey(KeyChain.KeyPurpose.CHANGE).sign(Sha256Hash.ZERO_HASH);
    }

    @Test
    public void watchingChain() throws UnreadableWalletException {
        Utils.setMockClock();
        DeterministicKey key1 = chain.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        DeterministicKey key2 = chain.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        DeterministicKey key3 = chain.getKey(KeyChain.KeyPurpose.CHANGE);
        DeterministicKey key4 = chain.getKey(KeyChain.KeyPurpose.CHANGE);

        NetworkParameters params = MainNetParams.get();
        DeterministicKey watchingKey = chain.getWatchingKey();
        final String pub58 = watchingKey.serializePubB58(params);
        assertEquals("xpub69KR9epSNBM59KLuasxMU5CyKytMJjBP5HEZ5p8YoGUCpM6cM9hqxB9DDPCpUUtqmw5duTckvPfwpoWGQUFPmRLpxs5jYiTf2u6xRMcdhDf", pub58);
        watchingKey = DeterministicKey.deserializeB58(null, pub58, params);
        watchingKey.setCreationTimeSeconds(100000);
        chain = DeterministicKeyChain.watch(watchingKey);
        assertEquals(DeterministicHierarchy.BIP32_STANDARDISATION_TIME_SECS, chain.getEarliestKeyCreationTime());
        chain.setLookaheadSize(10);
        chain.maybeLookAhead();

        assertEquals(key1.getPubKeyPoint(), chain.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS).getPubKeyPoint());
        assertEquals(key2.getPubKeyPoint(), chain.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS).getPubKeyPoint());
        final DeterministicKey key = chain.getKey(KeyChain.KeyPurpose.CHANGE);
        assertEquals(key3.getPubKeyPoint(), key.getPubKeyPoint());
        try {
            // Can't sign with a key from a watching chain.
            key.sign(Sha256Hash.ZERO_HASH);
            fail();
        } catch (ECKey.MissingPrivateKeyException e) {
            // Ignored.
        }
        // Test we can serialize and deserialize a watching chain OK.
        List<Protos.Key> serialization = chain.serializeToProtobuf();
        checkSerialization(serialization, "watching-wallet-serialization.txt");
        chain = DeterministicKeyChain.fromProtobuf(serialization, null).get(0);
        final DeterministicKey rekey4 = chain.getKey(KeyChain.KeyPurpose.CHANGE);
        assertEquals(key4.getPubKeyPoint(), rekey4.getPubKeyPoint());
    }

    @Test(expected = IllegalStateException.class)
    public void watchingCannotEncrypt() throws Exception {
        final DeterministicKey accountKey = chain.getKeyByPath(DeterministicKeyChain.ACCOUNT_ZERO_PATH);
        chain = DeterministicKeyChain.watch(accountKey.dropPrivateBytes().dropParent());
        chain = chain.toEncrypted("this doesn't make any sense");
    }

    @Test
    public void bloom1() {
        DeterministicKey key2 = chain.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        DeterministicKey key1 = chain.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);

        int numEntries =
                (((chain.getLookaheadSize() + chain.getLookaheadThreshold()) * 2)   // * 2 because of internal/external
              + chain.numLeafKeysIssued()
              + 4  // one root key + one account key + two chain keys (internal/external)
                ) * 2;  // because the filter contains keys and key hashes.
        assertEquals(numEntries, chain.numBloomFilterEntries());
        BloomFilter filter = chain.getFilter(numEntries, 0.001, 1);
        assertTrue(filter.contains(key1.getPubKey()));
        assertTrue(filter.contains(key1.getPubKeyHash()));
        assertTrue(filter.contains(key2.getPubKey()));
        assertTrue(filter.contains(key2.getPubKeyHash()));

        // The lookahead zone is tested in bloom2 and via KeyChainGroupTest.bloom
    }

    @Test
    public void bloom2() throws Exception {
        // Verify that if when we watch a key, the filter contains at least 100 keys.
        DeterministicKey[] keys = new DeterministicKey[100];
        for (int i = 0; i < keys.length; i++)
            keys[i] = chain.getKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        chain = DeterministicKeyChain.watch(chain.getWatchingKey().dropPrivateBytes().dropParent());
        int e = chain.numBloomFilterEntries();
        BloomFilter filter = chain.getFilter(e, 0.001, 1);
        for (DeterministicKey key : keys)
            assertTrue("key " + key, filter.contains(key.getPubKeyHash()));
    }

    private String protoToString(List<Protos.Key> keys) {
        StringBuilder sb = new StringBuilder();
        for (Protos.Key key : keys) {
            sb.append(key.toString());
            sb.append("\n");
        }
        return sb.toString().trim();
    }

    private String checkSerialization(List<Protos.Key> keys, String filename) {
        try {
            String sb = protoToString(keys);
            String expected = Utils.getResourceAsString(getClass().getResource(filename));
            assertEquals(expected, sb);
            return expected;
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }
}


File: core/src/test/java/org/bitcoinj/wallet/KeyChainGroupTest.java
/**
 * Copyright 2014 Mike Hearn
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.wallet;

import org.bitcoinj.core.*;
import org.bitcoinj.crypto.*;
import org.bitcoinj.params.MainNetParams;
import org.bitcoinj.utils.BriefLogFormatter;
import org.bitcoinj.utils.Threading;
import com.google.common.collect.ImmutableList;
import org.junit.Before;
import org.junit.Test;
import org.spongycastle.crypto.params.KeyParameter;
import org.spongycastle.util.Arrays;

import java.math.BigInteger;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

import static com.google.common.base.Preconditions.checkNotNull;
import static org.junit.Assert.*;

public class KeyChainGroupTest {
    // Number of initial keys in this tests HD wallet, including interior keys.
    private static final int INITIAL_KEYS = 4;
    private static final int LOOKAHEAD_SIZE = 5;
    private static final NetworkParameters params = MainNetParams.get();
    private static final String XPUB = "xpub68KFnj3bqUx1s7mHejLDBPywCAKdJEu1b49uniEEn2WSbHmZ7xbLqFTjJbtx1LUcAt1DwhoqWHmo2s5WMJp6wi38CiF2hYD49qVViKVvAoi";
    private KeyChainGroup group;
    private DeterministicKey watchingAccountKey;

    @Before
    public void setup() {
        BriefLogFormatter.init();
        Utils.setMockClock();
        group = new KeyChainGroup(params);
        group.setLookaheadSize(LOOKAHEAD_SIZE);   // Don't want slow tests.
        group.getActiveKeyChain();  // Force create a chain.

        watchingAccountKey = DeterministicKey.deserializeB58(null, XPUB, params);
    }

    private KeyChainGroup createMarriedKeyChainGroup() {
        KeyChainGroup group = new KeyChainGroup(params);
        DeterministicKeyChain chain = createMarriedKeyChain();
        group.addAndActivateHDChain(chain);
        group.setLookaheadSize(LOOKAHEAD_SIZE);
        group.getActiveKeyChain();
        return group;
    }

    private MarriedKeyChain createMarriedKeyChain() {
        byte[] entropy = Utils.singleDigest("don't use a seed like this in real life".getBytes());
        DeterministicSeed seed = new DeterministicSeed(entropy, "", MnemonicCode.BIP39_STANDARDISATION_TIME_SECS);
        MarriedKeyChain chain = MarriedKeyChain.builder()
                .seed(seed)
                .followingKeys(watchingAccountKey)
                .threshold(2).build();
        return chain;
    }

    @Test
    public void freshCurrentKeys() throws Exception {
        int numKeys = ((group.getLookaheadSize() + group.getLookaheadThreshold()) * 2)   // * 2 because of internal/external
                + 1  // keys issued
                + group.getActiveKeyChain().getAccountPath().size() + 2  /* account key + int/ext parent keys */;
        assertEquals(numKeys, group.numKeys());
        assertEquals(2 * numKeys, group.getBloomFilterElementCount());
        ECKey r1 = group.currentKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertEquals(numKeys, group.numKeys());
        assertEquals(2 * numKeys, group.getBloomFilterElementCount());

        ECKey i1 = new ECKey();
        group.importKeys(i1);
        numKeys++;
        assertEquals(numKeys, group.numKeys());
        assertEquals(2 * numKeys, group.getBloomFilterElementCount());

        ECKey r2 = group.currentKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertEquals(r1, r2);
        ECKey c1 = group.currentKey(KeyChain.KeyPurpose.CHANGE);
        assertNotEquals(r1, c1);
        ECKey r3 = group.freshKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertNotEquals(r1, r3);
        ECKey c2 = group.freshKey(KeyChain.KeyPurpose.CHANGE);
        assertNotEquals(r3, c2);
        // Current key has not moved and will not under marked as used.
        ECKey r4 = group.currentKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertEquals(r2, r4);
        ECKey c3 = group.currentKey(KeyChain.KeyPurpose.CHANGE);
        assertEquals(c1, c3);
        // Mark as used. Current key is now different.
        group.markPubKeyAsUsed(r4.getPubKey());
        ECKey r5 = group.currentKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertNotEquals(r4, r5);
    }

    @Test
    public void freshCurrentKeysForMarriedKeychain() throws Exception {
        group = createMarriedKeyChainGroup();

        try {
            group.freshKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
            fail();
        } catch (UnsupportedOperationException e) {
        }

        try {
            group.currentKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
            fail();
        } catch (UnsupportedOperationException e) {
        }
    }

    @Test
    public void imports() throws Exception {
        ECKey key1 = new ECKey();
        int numKeys = group.numKeys();
        assertFalse(group.removeImportedKey(key1));
        assertEquals(1, group.importKeys(ImmutableList.of(key1)));
        assertEquals(numKeys + 1, group.numKeys());   // Lookahead is triggered by requesting a key, so none yet.
        group.removeImportedKey(key1);
        assertEquals(numKeys, group.numKeys());
    }

    @Test
    public void findKey() throws Exception {
        ECKey a = group.freshKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        ECKey b = group.freshKey(KeyChain.KeyPurpose.CHANGE);
        ECKey c = new ECKey();
        ECKey d = new ECKey();   // Not imported.
        group.importKeys(c);
        assertTrue(group.hasKey(a));
        assertTrue(group.hasKey(b));
        assertTrue(group.hasKey(c));
        assertFalse(group.hasKey(d));
        ECKey result = group.findKeyFromPubKey(a.getPubKey());
        assertEquals(a, result);
        result = group.findKeyFromPubKey(b.getPubKey());
        assertEquals(b, result);
        result = group.findKeyFromPubHash(a.getPubKeyHash());
        assertEquals(a, result);
        result = group.findKeyFromPubHash(b.getPubKeyHash());
        assertEquals(b, result);
        result = group.findKeyFromPubKey(c.getPubKey());
        assertEquals(c, result);
        result = group.findKeyFromPubHash(c.getPubKeyHash());
        assertEquals(c, result);
        assertNull(group.findKeyFromPubKey(d.getPubKey()));
        assertNull(group.findKeyFromPubHash(d.getPubKeyHash()));
    }

    @Test
    public void currentP2SHAddress() throws Exception {
        group = createMarriedKeyChainGroup();
        Address a1 = group.currentAddress(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertTrue(a1.isP2SHAddress());
        Address a2 = group.currentAddress(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertEquals(a1, a2);
        Address a3 = group.currentAddress(KeyChain.KeyPurpose.CHANGE);
        assertNotEquals(a2, a3);
    }

    @Test
    public void freshAddress() throws Exception {
        group = createMarriedKeyChainGroup();
        Address a1 = group.freshAddress(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        Address a2 = group.freshAddress(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertTrue(a1.isP2SHAddress());
        assertNotEquals(a1, a2);
        group.getBloomFilterElementCount();
        assertEquals(((group.getLookaheadSize() + group.getLookaheadThreshold()) * 2)   // * 2 because of internal/external
                + (2 - group.getLookaheadThreshold())  // keys issued
                + group.getActiveKeyChain().getAccountPath().size() + 3  /* master, account, int, ext */, group.numKeys());

        Address a3 = group.currentAddress(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertEquals(a2, a3);
    }

    @Test
    public void findRedeemData() throws Exception {
        group = createMarriedKeyChainGroup();

        // test script hash that we don't have
        assertNull(group.findRedeemDataFromScriptHash(new ECKey().getPubKey()));

        // test our script hash
        Address address = group.currentAddress(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        RedeemData redeemData = group.findRedeemDataFromScriptHash(address.getHash160());
        assertNotNull(redeemData);
        assertNotNull(redeemData.redeemScript);
        assertEquals(2, redeemData.keys.size());
    }

    // Check encryption with and without a basic keychain.

    @Test
    public void encryptionWithoutImported() throws Exception {
        encryption(false);
    }

    @Test
    public void encryptionWithImported() throws Exception {
        encryption(true);
    }

    public void encryption(boolean withImported) throws Exception {
        Utils.rollMockClock(0);
        long now = Utils.currentTimeSeconds();
        ECKey a = group.freshKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertEquals(now, group.getEarliestKeyCreationTime());
        Utils.rollMockClock(-86400);
        long yesterday = Utils.currentTimeSeconds();
        ECKey b = new ECKey();

        assertFalse(group.isEncrypted());
        try {
            group.checkPassword("foo");   // Cannot check password of an unencrypted group.
            fail();
        } catch (IllegalStateException e) {
        }
        if (withImported) {
            assertEquals(now, group.getEarliestKeyCreationTime());
            group.importKeys(b);
            assertEquals(yesterday, group.getEarliestKeyCreationTime());
        }
        KeyCrypterScrypt scrypt = new KeyCrypterScrypt(2);
        final KeyParameter aesKey = scrypt.deriveKey("password");
        group.encrypt(scrypt, aesKey);
        assertTrue(group.isEncrypted());
        assertTrue(group.checkPassword("password"));
        assertFalse(group.checkPassword("wrong password"));
        final ECKey ea = group.findKeyFromPubKey(a.getPubKey());
        assertTrue(checkNotNull(ea).isEncrypted());
        if (withImported) {
            assertTrue(checkNotNull(group.findKeyFromPubKey(b.getPubKey())).isEncrypted());
            assertEquals(yesterday, group.getEarliestKeyCreationTime());
        } else {
            assertEquals(now, group.getEarliestKeyCreationTime());
        }
        try {
            ea.sign(Sha256Hash.ZERO_HASH);
            fail();
        } catch (ECKey.KeyIsEncryptedException e) {
            // Ignored.
        }
        if (withImported) {
            ECKey c = new ECKey();
            try {
                group.importKeys(c);
                fail();
            } catch (KeyCrypterException e) {
            }
            group.importKeysAndEncrypt(ImmutableList.of(c), aesKey);
            ECKey ec = group.findKeyFromPubKey(c.getPubKey());
            try {
                group.importKeysAndEncrypt(ImmutableList.of(ec), aesKey);
                fail();
            } catch (IllegalArgumentException e) {
            }
        }

        try {
            group.decrypt(scrypt.deriveKey("WRONG PASSWORD"));
            fail();
        } catch (KeyCrypterException e) {
        }

        group.decrypt(aesKey);
        assertFalse(group.isEncrypted());
        assertFalse(checkNotNull(group.findKeyFromPubKey(a.getPubKey())).isEncrypted());
        if (withImported) {
            assertFalse(checkNotNull(group.findKeyFromPubKey(b.getPubKey())).isEncrypted());
            assertEquals(yesterday, group.getEarliestKeyCreationTime());
        } else {
            assertEquals(now, group.getEarliestKeyCreationTime());
        }
    }

    @Test
    public void encryptionWhilstEmpty() throws Exception {
        group = new KeyChainGroup(params);
        group.setLookaheadSize(5);
        KeyCrypterScrypt scrypt = new KeyCrypterScrypt(2);
        final KeyParameter aesKey = scrypt.deriveKey("password");
        group.encrypt(scrypt, aesKey);
        assertTrue(group.freshKey(KeyChain.KeyPurpose.RECEIVE_FUNDS).isEncrypted());
        final ECKey key = group.currentKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        group.decrypt(aesKey);
        assertFalse(checkNotNull(group.findKeyFromPubKey(key.getPubKey())).isEncrypted());
    }

    @Test
    public void bloom() throws Exception {
        ECKey key1 = group.freshKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        ECKey key2 = new ECKey();
        BloomFilter filter = group.getBloomFilter(group.getBloomFilterElementCount(), 0.001, (long)(Math.random() * Long.MAX_VALUE));
        assertTrue(filter.contains(key1.getPubKeyHash()));
        assertTrue(filter.contains(key1.getPubKey()));
        assertFalse(filter.contains(key2.getPubKey()));
        // Check that the filter contains the lookahead buffer and threshold zone.
        for (int i = 0; i < LOOKAHEAD_SIZE + group.getLookaheadThreshold(); i++) {
            ECKey k = group.freshKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
            assertTrue(filter.contains(k.getPubKeyHash()));
        }
        // We ran ahead of the lookahead buffer.
        assertFalse(filter.contains(group.freshKey(KeyChain.KeyPurpose.RECEIVE_FUNDS).getPubKey()));
        group.importKeys(key2);
        filter = group.getBloomFilter(group.getBloomFilterElementCount(), 0.001, (long) (Math.random() * Long.MAX_VALUE));
        assertTrue(filter.contains(key1.getPubKeyHash()));
        assertTrue(filter.contains(key1.getPubKey()));
        assertTrue(filter.contains(key2.getPubKey()));
    }

    @Test
    public void findRedeemScriptFromPubHash() throws Exception {
        group = createMarriedKeyChainGroup();
        Address address = group.freshAddress(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertTrue(group.findRedeemDataFromScriptHash(address.getHash160()) != null);
        group.getBloomFilterElementCount();
        KeyChainGroup group2 = createMarriedKeyChainGroup();
        group2.freshAddress(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        group2.getBloomFilterElementCount();  // Force lookahead.
        // test address from lookahead zone and lookahead threshold zone
        for (int i = 0; i < group.getLookaheadSize() + group.getLookaheadThreshold(); i++) {
            address = group.freshAddress(KeyChain.KeyPurpose.RECEIVE_FUNDS);
            assertTrue(group2.findRedeemDataFromScriptHash(address.getHash160()) != null);
        }
        assertFalse(group2.findRedeemDataFromScriptHash(group.freshAddress(KeyChain.KeyPurpose.RECEIVE_FUNDS).getHash160()) != null);
    }

    @Test
    public void bloomFilterForMarriedChains() throws Exception {
        group = createMarriedKeyChainGroup();
        int bufferSize = group.getLookaheadSize() + group.getLookaheadThreshold();
        int expected = bufferSize * 2 /* chains */ * 2 /* elements */;
        assertEquals(expected, group.getBloomFilterElementCount());
        Address address1 = group.freshAddress(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertEquals(expected, group.getBloomFilterElementCount());
        BloomFilter filter = group.getBloomFilter(expected + 2, 0.001, (long)(Math.random() * Long.MAX_VALUE));
        assertTrue(filter.contains(address1.getHash160()));

        Address address2 = group.freshAddress(KeyChain.KeyPurpose.CHANGE);
        assertTrue(filter.contains(address2.getHash160()));

        // Check that the filter contains the lookahead buffer.
        for (int i = 0; i < bufferSize - 1 /* issued address */; i++) {
            Address address = group.freshAddress(KeyChain.KeyPurpose.RECEIVE_FUNDS);
            assertTrue("key " + i, filter.contains(address.getHash160()));
        }
        // We ran ahead of the lookahead buffer.
        assertFalse(filter.contains(group.freshAddress(KeyChain.KeyPurpose.RECEIVE_FUNDS).getHash160()));
    }

    @Test
    public void earliestKeyTime() throws Exception {
        long now = Utils.currentTimeSeconds();   // mock
        long yesterday = now - 86400;
        assertEquals(now, group.getEarliestKeyCreationTime());
        Utils.rollMockClock(10000);
        group.freshKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        Utils.rollMockClock(10000);
        group.freshKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        // Check that all keys are assumed to be created at the same instant the seed is.
        assertEquals(now, group.getEarliestKeyCreationTime());
        ECKey key = new ECKey();
        key.setCreationTimeSeconds(yesterday);
        group.importKeys(key);
        assertEquals(yesterday, group.getEarliestKeyCreationTime());
    }

    @Test
    public void events() throws Exception {
        // Check that events are registered with the right chains and that if a chain is added, it gets the event
        // listeners attached properly even post-hoc.
        final AtomicReference<ECKey> ran = new AtomicReference<ECKey>(null);
        final KeyChainEventListener listener = new KeyChainEventListener() {
            @Override
            public void onKeysAdded(List<ECKey> keys) {
                ran.set(keys.get(0));
            }
        };
        group.addEventListener(listener, Threading.SAME_THREAD);
        ECKey key = group.freshKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertEquals(key, ran.getAndSet(null));
        ECKey key2 = new ECKey();
        group.importKeys(key2);
        assertEquals(key2, ran.getAndSet(null));
        group.removeEventListener(listener);
        ECKey key3 = new ECKey();
        group.importKeys(key3);
        assertNull(ran.get());
    }

    @Test
    public void serialization() throws Exception {
        int initialKeys = INITIAL_KEYS + group.getActiveKeyChain().getAccountPath().size() - 1;
        assertEquals(initialKeys + 1 /* for the seed */, group.serializeToProtobuf().size());
        group = KeyChainGroup.fromProtobufUnencrypted(params, group.serializeToProtobuf());
        group.freshKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        DeterministicKey key1 = group.freshKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        DeterministicKey key2 = group.freshKey(KeyChain.KeyPurpose.CHANGE);
        group.getBloomFilterElementCount();
        List<Protos.Key> protoKeys1 = group.serializeToProtobuf();
        assertEquals(initialKeys + ((LOOKAHEAD_SIZE + 1) * 2) + 1 /* for the seed */ + 1, protoKeys1.size());
        group.importKeys(new ECKey());
        List<Protos.Key> protoKeys2 = group.serializeToProtobuf();
        assertEquals(initialKeys + ((LOOKAHEAD_SIZE + 1) * 2) + 1 /* for the seed */ + 2, protoKeys2.size());

        group = KeyChainGroup.fromProtobufUnencrypted(params, protoKeys1);
        assertEquals(initialKeys + ((LOOKAHEAD_SIZE + 1)  * 2)  + 1 /* for the seed */ + 1, protoKeys1.size());
        assertTrue(group.hasKey(key1));
        assertTrue(group.hasKey(key2));
        assertEquals(key2, group.currentKey(KeyChain.KeyPurpose.CHANGE));
        assertEquals(key1, group.currentKey(KeyChain.KeyPurpose.RECEIVE_FUNDS));
        group = KeyChainGroup.fromProtobufUnencrypted(params, protoKeys2);
        assertEquals(initialKeys + ((LOOKAHEAD_SIZE + 1) * 2) + 1 /* for the seed */ + 2, protoKeys2.size());
        assertTrue(group.hasKey(key1));
        assertTrue(group.hasKey(key2));

        KeyCrypterScrypt scrypt = new KeyCrypterScrypt(2);
        final KeyParameter aesKey = scrypt.deriveKey("password");
        group.encrypt(scrypt, aesKey);
        List<Protos.Key> protoKeys3 = group.serializeToProtobuf();
        group = KeyChainGroup.fromProtobufEncrypted(params, protoKeys3, scrypt);
        assertTrue(group.isEncrypted());
        assertTrue(group.checkPassword("password"));
        group.decrypt(aesKey);

        // No need for extensive contents testing here, as that's done in the keychain class tests.
    }

    @Test
    public void serializeWatching() throws Exception {
        group = new KeyChainGroup(params, watchingAccountKey);
        group.setLookaheadSize(LOOKAHEAD_SIZE);
        group.freshKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        group.freshKey(KeyChain.KeyPurpose.CHANGE);
        group.getBloomFilterElementCount();  // Force lookahead.
        List<Protos.Key> protoKeys1 = group.serializeToProtobuf();
        assertEquals(3 + (group.getLookaheadSize() + group.getLookaheadThreshold() + 1) * 2, protoKeys1.size());
        group = KeyChainGroup.fromProtobufUnencrypted(params, protoKeys1);
        assertEquals(3 + (group.getLookaheadSize() + group.getLookaheadThreshold() + 1) * 2, group.serializeToProtobuf().size());
    }

    @Test
    public void serializeMarried() throws Exception {
        group = createMarriedKeyChainGroup();
        Address address1 = group.currentAddress(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertTrue(group.isMarried());
        assertEquals(2, group.getActiveKeyChain().getSigsRequiredToSpend());

        List<Protos.Key> protoKeys = group.serializeToProtobuf();
        KeyChainGroup group2 = KeyChainGroup.fromProtobufUnencrypted(params, protoKeys);
        assertTrue(group2.isMarried());
        assertEquals(2, group.getActiveKeyChain().getSigsRequiredToSpend());
        Address address2 = group2.currentAddress(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertEquals(address1, address2);
    }

    @Test
    public void addFollowingAccounts() throws Exception {
        assertFalse(group.isMarried());
        group.addAndActivateHDChain(createMarriedKeyChain());
        assertTrue(group.isMarried());
    }

    @Test
    public void constructFromSeed() throws Exception {
        ECKey key1 = group.freshKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        final DeterministicSeed seed = checkNotNull(group.getActiveKeyChain().getSeed());
        KeyChainGroup group2 = new KeyChainGroup(params, seed);
        group2.setLookaheadSize(5);
        ECKey key2 = group2.freshKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertEquals(key1, key2);
    }

    @Test(expected = DeterministicUpgradeRequiredException.class)
    public void deterministicUpgradeRequired() throws Exception {
        // Check that if we try to use HD features in a KCG that only has random keys, we get an exception.
        group = new KeyChainGroup(params);
        group.importKeys(new ECKey(), new ECKey());
        assertTrue(group.isDeterministicUpgradeRequired());
        group.freshKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);   // throws
    }

    @Test
    public void deterministicUpgradeUnencrypted() throws Exception {
        // Check that a group that contains only random keys has its HD chain created using the private key bytes of
        // the oldest random key, so upgrading the same wallet twice gives the same outcome.
        group = new KeyChainGroup(params);
        group.setLookaheadSize(LOOKAHEAD_SIZE);   // Don't want slow tests.
        ECKey key1 = new ECKey();
        Utils.rollMockClock(86400);
        ECKey key2 = new ECKey();
        group.importKeys(key2, key1);

        List<Protos.Key> protobufs = group.serializeToProtobuf();
        group.upgradeToDeterministic(0, null);
        assertFalse(group.isDeterministicUpgradeRequired());
        DeterministicKey dkey1 = group.freshKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        DeterministicSeed seed1 = group.getActiveKeyChain().getSeed();
        assertNotNull(seed1);

        group = KeyChainGroup.fromProtobufUnencrypted(params, protobufs);
        group.upgradeToDeterministic(0, null);  // Should give same result as last time.
        DeterministicKey dkey2 = group.freshKey(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        DeterministicSeed seed2 = group.getActiveKeyChain().getSeed();
        assertEquals(seed1, seed2);
        assertEquals(dkey1, dkey2);

        // Check we used the right (oldest) key despite backwards import order.
        byte[] truncatedBytes = Arrays.copyOfRange(key1.getSecretBytes(), 0, 16);
        assertArrayEquals(seed1.getEntropyBytes(), truncatedBytes);
    }

    @Test
    public void deterministicUpgradeRotating() throws Exception {
        group = new KeyChainGroup(params);
        group.setLookaheadSize(LOOKAHEAD_SIZE);   // Don't want slow tests.
        long now = Utils.currentTimeSeconds();
        ECKey key1 = new ECKey();
        Utils.rollMockClock(86400);
        ECKey key2 = new ECKey();
        Utils.rollMockClock(86400);
        ECKey key3 = new ECKey();
        group.importKeys(key2, key1, key3);
        group.upgradeToDeterministic(now + 10, null);
        DeterministicSeed seed = group.getActiveKeyChain().getSeed();
        assertNotNull(seed);
        // Check we used the right key: oldest non rotating.
        byte[] truncatedBytes = Arrays.copyOfRange(key2.getSecretBytes(), 0, 16);
        assertArrayEquals(seed.getEntropyBytes(), truncatedBytes);
    }

    @Test
    public void deterministicUpgradeEncrypted() throws Exception {
        group = new KeyChainGroup(params);
        final ECKey key = new ECKey();
        group.importKeys(key);
        final KeyCrypterScrypt crypter = new KeyCrypterScrypt();
        final KeyParameter aesKey = crypter.deriveKey("abc");
        assertTrue(group.isDeterministicUpgradeRequired());
        group.encrypt(crypter, aesKey);
        assertTrue(group.isDeterministicUpgradeRequired());
        try {
            group.upgradeToDeterministic(0, null);
            fail();
        } catch (DeterministicUpgradeRequiresPassword e) {
            // Expected.
        }
        group.upgradeToDeterministic(0, aesKey);
        assertFalse(group.isDeterministicUpgradeRequired());
        final DeterministicSeed deterministicSeed = group.getActiveKeyChain().getSeed();
        assertNotNull(deterministicSeed);
        assertTrue(deterministicSeed.isEncrypted());
        byte[] entropy = checkNotNull(group.getActiveKeyChain().toDecrypted(aesKey).getSeed()).getEntropyBytes();
        // Check we used the right key: oldest non rotating.
        byte[] truncatedBytes = Arrays.copyOfRange(key.getSecretBytes(), 0, 16);
        assertArrayEquals(entropy, truncatedBytes);
    }

    @Test
    public void markAsUsed() throws Exception {
        Address addr1 = group.currentAddress(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        Address addr2 = group.currentAddress(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertEquals(addr1, addr2);
        group.markPubKeyHashAsUsed(addr1.getHash160());
        Address addr3 = group.currentAddress(KeyChain.KeyPurpose.RECEIVE_FUNDS);
        assertNotEquals(addr2, addr3);
    }

    @Test
    public void isNotWatching() {
        group = new KeyChainGroup(params);
        final ECKey key = ECKey.fromPrivate(BigInteger.TEN);
        group.importKeys(key);
        assertFalse(group.isWatching());
    }

    @Test
    public void isWatching() {
        group = new KeyChainGroup(
                params,
                DeterministicKey
                        .deserializeB58(
                                "xpub69bjfJ91ikC5ghsqsVDHNq2dRGaV2HHVx7Y9LXi27LN9BWWAXPTQr4u8U3wAtap8bLdHdkqPpAcZmhMS5SnrMQC4ccaoBccFhh315P4UYzo",
                                params));
        final ECKey watchingKey = ECKey.fromPublicOnly(new ECKey().getPubKeyPoint());
        group.importKeys(watchingKey);
        assertTrue(group.isWatching());
    }

    @Test(expected = IllegalStateException.class)
    public void isWatchingNoKeys() {
        group = new KeyChainGroup(params);
        group.isWatching();
    }

    @Test(expected = IllegalStateException.class)
    public void isWatchingMixedKeys() {
        group = new KeyChainGroup(
                params,
                DeterministicKey
                        .deserializeB58(
                                "xpub69bjfJ91ikC5ghsqsVDHNq2dRGaV2HHVx7Y9LXi27LN9BWWAXPTQr4u8U3wAtap8bLdHdkqPpAcZmhMS5SnrMQC4ccaoBccFhh315P4UYzo",
                                params));
        final ECKey key = ECKey.fromPrivate(BigInteger.TEN);
        group.importKeys(key);
        group.isWatching();
    }
}


File: tools/src/main/java/org/bitcoinj/tools/BuildCheckpoints.java
/*
 * Copyright 2013 Google Inc.
 * Copyright 2014 Andreas Schildbach
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.bitcoinj.tools;

import org.bitcoinj.core.*;
import org.bitcoinj.params.MainNetParams;
import org.bitcoinj.store.BlockStore;
import org.bitcoinj.store.MemoryBlockStore;
import org.bitcoinj.utils.BriefLogFormatter;
import org.bitcoinj.utils.Threading;
import com.google.common.base.Charsets;

import java.io.DataOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.net.InetAddress;
import java.nio.ByteBuffer;
import java.security.DigestOutputStream;
import java.security.MessageDigest;
import java.util.Date;
import java.util.TreeMap;

import static com.google.common.base.Preconditions.checkState;

/**
 * Downloads and verifies a full chain from your local peer, emitting checkpoints at each difficulty transition period
 * to a file which is then signed with your key.
 */
public class BuildCheckpoints {

    private static final NetworkParameters PARAMS = MainNetParams.get();
    private static final File PLAIN_CHECKPOINTS_FILE = new File("checkpoints");
    private static final File TEXTUAL_CHECKPOINTS_FILE = new File("checkpoints.txt");

    public static void main(String[] args) throws Exception {
        BriefLogFormatter.initWithSilentBitcoinJ();

        // Sorted map of block height to StoredBlock object.
        final TreeMap<Integer, StoredBlock> checkpoints = new TreeMap<Integer, StoredBlock>();

        // Configure bitcoinj to fetch only headers, not save them to disk, connect to a local fully synced/validated
        // node and to save block headers that are on interval boundaries, as long as they are <1 month old.
        final BlockStore store = new MemoryBlockStore(PARAMS);
        final BlockChain chain = new BlockChain(PARAMS, store);
        final PeerGroup peerGroup = new PeerGroup(PARAMS, chain);
        final InetAddress peerAddress = InetAddress.getLocalHost();
        System.out.println("Connecting to " + peerAddress + "...");
        peerGroup.addAddress(peerAddress);
        long now = new Date().getTime() / 1000;
        peerGroup.setFastCatchupTimeSecs(now);

        final long oneMonthAgo = now - (86400 * 30);

        chain.addListener(new AbstractBlockChainListener() {
            @Override
            public void notifyNewBestBlock(StoredBlock block) throws VerificationException {
                int height = block.getHeight();
                if (height % PARAMS.getInterval() == 0 && block.getHeader().getTimeSeconds() <= oneMonthAgo) {
                    System.out.println(String.format("Checkpointing block %s at height %d",
                            block.getHeader().getHash(), block.getHeight()));
                    checkpoints.put(height, block);
                }
            }
        }, Threading.SAME_THREAD);

        peerGroup.start();
        peerGroup.downloadBlockChain();

        checkState(checkpoints.size() > 0);

        // Write checkpoint data out.
        writeBinaryCheckpoints(checkpoints, PLAIN_CHECKPOINTS_FILE);
        writeTextualCheckpoints(checkpoints, TEXTUAL_CHECKPOINTS_FILE);

        peerGroup.stop();
        store.close();

        // Sanity check the created files.
        sanityCheck(PLAIN_CHECKPOINTS_FILE, checkpoints.size());
        sanityCheck(TEXTUAL_CHECKPOINTS_FILE, checkpoints.size());
    }

    private static void writeBinaryCheckpoints(TreeMap<Integer, StoredBlock> checkpoints, File file) throws Exception {
        final FileOutputStream fileOutputStream = new FileOutputStream(file, false);
        MessageDigest digest = Utils.newSha256Digest();
        final DigestOutputStream digestOutputStream = new DigestOutputStream(fileOutputStream, digest);
        digestOutputStream.on(false);
        final DataOutputStream dataOutputStream = new DataOutputStream(digestOutputStream);
        dataOutputStream.writeBytes("CHECKPOINTS 1");
        dataOutputStream.writeInt(0);  // Number of signatures to read. Do this later.
        digestOutputStream.on(true);
        dataOutputStream.writeInt(checkpoints.size());
        ByteBuffer buffer = ByteBuffer.allocate(StoredBlock.COMPACT_SERIALIZED_SIZE);
        for (StoredBlock block : checkpoints.values()) {
            block.serializeCompact(buffer);
            dataOutputStream.write(buffer.array());
            buffer.position(0);
        }
        dataOutputStream.close();
        Sha256Hash checkpointsHash = new Sha256Hash(digest.digest());
        System.out.println("Hash of checkpoints data is " + checkpointsHash);
        digestOutputStream.close();
        fileOutputStream.close();
        System.out.println("Checkpoints written to '" + file.getCanonicalPath() + "'.");
    }

    private static void writeTextualCheckpoints(TreeMap<Integer, StoredBlock> checkpoints, File file) throws IOException {
        PrintWriter writer = new PrintWriter(new OutputStreamWriter(new FileOutputStream(file), Charsets.US_ASCII));
        writer.println("TXT CHECKPOINTS 1");
        writer.println("0"); // Number of signatures to read. Do this later.
        writer.println(checkpoints.size());
        ByteBuffer buffer = ByteBuffer.allocate(StoredBlock.COMPACT_SERIALIZED_SIZE);
        for (StoredBlock block : checkpoints.values()) {
            block.serializeCompact(buffer);
            writer.println(CheckpointManager.BASE64.encode(buffer.array()));
            buffer.position(0);
        }
        writer.close();
        System.out.println("Checkpoints written to '" + file.getCanonicalPath() + "'.");
    }

    private static void sanityCheck(File file, int expectedSize) throws IOException {
        CheckpointManager manager = new CheckpointManager(PARAMS, new FileInputStream(file));
        checkState(manager.numCheckpoints() == expectedSize);

        if (PARAMS.getId().equals(NetworkParameters.ID_MAINNET)) {
            StoredBlock test = manager.getCheckpointBefore(1390500000); // Thu Jan 23 19:00:00 CET 2014
            checkState(test.getHeight() == 280224);
            checkState(test.getHeader().getHashAsString()
                    .equals("00000000000000000b5d59a15f831e1c45cb688a4db6b0a60054d49a9997fa34"));
        } else if (PARAMS.getId().equals(NetworkParameters.ID_TESTNET)) {
            StoredBlock test = manager.getCheckpointBefore(1390500000); // Thu Jan 23 19:00:00 CET 2014
            checkState(test.getHeight() == 167328);
            checkState(test.getHeader().getHashAsString()
                    .equals("0000000000035ae7d5025c2538067fe7adb1cf5d5d9c31b024137d9090ed13a9"));
        }
    }
}
