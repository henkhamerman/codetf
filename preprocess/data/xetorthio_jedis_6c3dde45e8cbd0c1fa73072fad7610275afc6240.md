Refactoring Types: ['Move Class']
s/jedis/BinaryJedis.java
package redis.clients.jedis;

import static redis.clients.jedis.Protocol.toByteArray;

import java.io.Closeable;
import java.net.URI;
import java.util.AbstractMap;
import java.util.AbstractSet;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import redis.clients.jedis.BinaryClient.LIST_POSITION;
import redis.clients.jedis.exceptions.InvalidURIException;
import redis.clients.jedis.exceptions.JedisDataException;
import redis.clients.jedis.exceptions.JedisException;
import redis.clients.jedis.params.set.SetParams;
import redis.clients.util.JedisByteHashMap;
import redis.clients.util.JedisURIHelper;
import redis.clients.util.SafeEncoder;

public class BinaryJedis implements BasicCommands, BinaryJedisCommands, MultiKeyBinaryCommands,
    AdvancedBinaryJedisCommands, BinaryScriptingCommands, Closeable {
  protected Client client = null;
  protected Transaction transaction = null;
  protected Pipeline pipeline = null;

  public BinaryJedis() {
    client = new Client();
  }

  public BinaryJedis(final String host) {
    URI uri = URI.create(host);
    if (uri.getScheme() != null && uri.getScheme().equals("redis")) {
      initializeClientFromURI(uri);
    } else {
      client = new Client(host);
    }
  }

  public BinaryJedis(final String host, final int port) {
    client = new Client(host, port);
  }

  public BinaryJedis(final String host, final int port, final int timeout) {
    client = new Client(host, port);
    client.setConnectionTimeout(timeout);
    client.setSoTimeout(timeout);
  }

  public BinaryJedis(final String host, final int port, final int connectionTimeout,
      final int soTimeout) {
    client = new Client(host, port);
    client.setConnectionTimeout(connectionTimeout);
    client.setSoTimeout(soTimeout);
  }

  public BinaryJedis(final JedisShardInfo shardInfo) {
    client = new Client(shardInfo.getHost(), shardInfo.getPort());
    client.setConnectionTimeout(shardInfo.getConnectionTimeout());
    client.setSoTimeout(shardInfo.getSoTimeout());
    client.setPassword(shardInfo.getPassword());
    client.setDb(shardInfo.getDb());
  }

  public BinaryJedis(URI uri) {
    initializeClientFromURI(uri);
  }

  public BinaryJedis(final URI uri, final int timeout) {
    initializeClientFromURI(uri);
    client.setConnectionTimeout(timeout);
    client.setSoTimeout(timeout);
  }

  public BinaryJedis(final URI uri, final int connectionTimeout, final int soTimeout) {
    initializeClientFromURI(uri);
    client.setConnectionTimeout(connectionTimeout);
    client.setSoTimeout(soTimeout);
  }

  private void initializeClientFromURI(URI uri) {
    if (!JedisURIHelper.isValid(uri)) {
      throw new InvalidURIException(String.format(
        "Cannot open Redis connection due invalid URI. %s", uri.toString()));
    }

    client = new Client(uri.getHost(), uri.getPort());

    String password = JedisURIHelper.getPassword(uri);
    if (password != null) {
      client.auth(password);
      client.getStatusCodeReply();
    }

    int dbIndex = JedisURIHelper.getDBIndex(uri);
    if (dbIndex > 0) {
      client.select(dbIndex);
      client.getStatusCodeReply();
      client.setDb(dbIndex);
    }
  }

  @Override
  public String ping() {
    checkIsInMultiOrPipeline();
    client.ping();
    return client.getStatusCodeReply();
  }

  /**
   * Set the string value as value of the key. The string can't be longer than 1073741824 bytes (1
   * GB).
   * <p>
   * Time complexity: O(1)
   * @param key
   * @param value
   * @return Status code reply
   */
  @Override
  public String set(final byte[] key, final byte[] value) {
    checkIsInMultiOrPipeline();
    client.set(key, value);
    return client.getStatusCodeReply();
  }

  /**
   * Set the string value as value of the key. The string can't be longer than 1073741824 bytes (1
   * GB).
   * @param key
   * @param value
   * @param params
   * @return Status code reply
   */
  public String set(final byte[] key, final byte[] value, final SetParams params) {
    checkIsInMultiOrPipeline();
    client.set(key, value, params);
    return client.getStatusCodeReply();
  }

  /**
   * Get the value of the specified key. If the key does not exist the special value 'nil' is
   * returned. If the value stored at key is not a string an error is returned because GET can only
   * handle string values.
   * <p>
   * Time complexity: O(1)
   * @param key
   * @return Bulk reply
   */
  @Override
  public byte[] get(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.get(key);
    return client.getBinaryBulkReply();
  }

  /**
   * Ask the server to silently close the connection.
   */
  @Override
  public String quit() {
    checkIsInMultiOrPipeline();
    client.quit();
    String quitReturn = client.getStatusCodeReply();
    client.disconnect();
    return quitReturn;
  }

  /**
   * Test if the specified key exists. The command returns "1" if the key exists, otherwise "0" is
   * returned. Note that even keys set with an empty string as value will return "1". Time
   * complexity: O(1)
   * @param key
   * @return Integer reply, "1" if the key exists, otherwise "0"
   */
  @Override
  public Boolean exists(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.exists(key);
    return client.getIntegerReply() == 1;
  }

  /**
   * Remove the specified keys. If a given key does not exist no operation is performed for this
   * key. The command returns the number of keys removed. Time complexity: O(1)
   * @param keys
   * @return Integer reply, specifically: an integer greater than 0 if one or more keys were removed
   *         0 if none of the specified key existed
   */
  @Override
  public Long del(final byte[]... keys) {
    checkIsInMultiOrPipeline();
    client.del(keys);
    return client.getIntegerReply();
  }

  @Override
  public Long del(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.del(key);
    return client.getIntegerReply();
  }

  /**
   * Return the type of the value stored at key in form of a string. The type can be one of "none",
   * "string", "list", "set". "none" is returned if the key does not exist. Time complexity: O(1)
   * @param key
   * @return Status code reply, specifically: "none" if the key does not exist "string" if the key
   *         contains a String value "list" if the key contains a List value "set" if the key
   *         contains a Set value "zset" if the key contains a Sorted Set value "hash" if the key
   *         contains a Hash value
   */
  @Override
  public String type(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.type(key);
    return client.getStatusCodeReply();
  }

  /**
   * Delete all the keys of the currently selected DB. This command never fails.
   * @return Status code reply
   */
  @Override
  public String flushDB() {
    checkIsInMultiOrPipeline();
    client.flushDB();
    return client.getStatusCodeReply();
  }

  /**
   * Returns all the keys matching the glob-style pattern as space separated strings. For example if
   * you have in the database the keys "foo" and "foobar" the command "KEYS foo*" will return
   * "foo foobar".
   * <p>
   * Note that while the time complexity for this operation is O(n) the constant times are pretty
   * low. For example Redis running on an entry level laptop can scan a 1 million keys database in
   * 40 milliseconds. <b>Still it's better to consider this one of the slow commands that may ruin
   * the DB performance if not used with care.</b>
   * <p>
   * In other words this command is intended only for debugging and special operations like creating
   * a script to change the DB schema. Don't use it in your normal code. Use Redis Sets in order to
   * group together a subset of objects.
   * <p>
   * Glob style patterns examples:
   * <ul>
   * <li>h?llo will match hello hallo hhllo
   * <li>h*llo will match hllo heeeello
   * <li>h[ae]llo will match hello and hallo, but not hillo
   * </ul>
   * <p>
   * Use \ to escape special chars if you want to match them verbatim.
   * <p>
   * Time complexity: O(n) (with n being the number of keys in the DB, and assuming keys and pattern
   * of limited length)
   * @param pattern
   * @return Multi bulk reply
   */
  @Override
  public Set<byte[]> keys(final byte[] pattern) {
    checkIsInMultiOrPipeline();
    client.keys(pattern);
    return SetFromList.of(client.getBinaryMultiBulkReply());
  }

  /**
   * Return a randomly selected key from the currently selected DB.
   * <p>
   * Time complexity: O(1)
   * @return Singe line reply, specifically the randomly selected key or an empty string is the
   *         database is empty
   */
  @Override
  public byte[] randomBinaryKey() {
    checkIsInMultiOrPipeline();
    client.randomKey();
    return client.getBinaryBulkReply();
  }

  /**
   * Atomically renames the key oldkey to newkey. If the source and destination name are the same an
   * error is returned. If newkey already exists it is overwritten.
   * <p>
   * Time complexity: O(1)
   * @param oldkey
   * @param newkey
   * @return Status code repy
   */
  @Override
  public String rename(final byte[] oldkey, final byte[] newkey) {
    checkIsInMultiOrPipeline();
    client.rename(oldkey, newkey);
    return client.getStatusCodeReply();
  }

  /**
   * Rename oldkey into newkey but fails if the destination key newkey already exists.
   * <p>
   * Time complexity: O(1)
   * @param oldkey
   * @param newkey
   * @return Integer reply, specifically: 1 if the key was renamed 0 if the target key already exist
   */
  @Override
  public Long renamenx(final byte[] oldkey, final byte[] newkey) {
    checkIsInMultiOrPipeline();
    client.renamenx(oldkey, newkey);
    return client.getIntegerReply();
  }

  /**
   * Return the number of keys in the currently selected database.
   * @return Integer reply
   */
  @Override
  public Long dbSize() {
    checkIsInMultiOrPipeline();
    client.dbSize();
    return client.getIntegerReply();
  }

  /**
   * Set a timeout on the specified key. After the timeout the key will be automatically deleted by
   * the server. A key with an associated timeout is said to be volatile in Redis terminology.
   * <p>
   * Voltile keys are stored on disk like the other keys, the timeout is persistent too like all the
   * other aspects of the dataset. Saving a dataset containing expires and stopping the server does
   * not stop the flow of time as Redis stores on disk the time when the key will no longer be
   * available as Unix time, and not the remaining seconds.
   * <p>
   * Since Redis 2.1.3 you can update the value of the timeout of a key already having an expire
   * set. It is also possible to undo the expire at all turning the key into a normal key using the
   * {@link #persist(byte[]) PERSIST} command.
   * <p>
   * Time complexity: O(1)
   * @see <a href="http://redis.io/commands/expire">Expire Command</a>
   * @param key
   * @param seconds
   * @return Integer reply, specifically: 1: the timeout was set. 0: the timeout was not set since
   *         the key already has an associated timeout (this may happen only in Redis versions &lt;
   *         2.1.3, Redis &gt;= 2.1.3 will happily update the timeout), or the key does not exist.
   */
  @Override
  public Long expire(final byte[] key, final int seconds) {
    checkIsInMultiOrPipeline();
    client.expire(key, seconds);
    return client.getIntegerReply();
  }

  /**
   * EXPIREAT works exctly like {@link #expire(byte[], int) EXPIRE} but instead to get the number of
   * seconds representing the Time To Live of the key as a second argument (that is a relative way
   * of specifing the TTL), it takes an absolute one in the form of a UNIX timestamp (Number of
   * seconds elapsed since 1 Gen 1970).
   * <p>
   * EXPIREAT was introduced in order to implement the Append Only File persistence mode so that
   * EXPIRE commands are automatically translated into EXPIREAT commands for the append only file.
   * Of course EXPIREAT can also used by programmers that need a way to simply specify that a given
   * key should expire at a given time in the future.
   * <p>
   * Since Redis 2.1.3 you can update the value of the timeout of a key already having an expire
   * set. It is also possible to undo the expire at all turning the key into a normal key using the
   * {@link #persist(byte[]) PERSIST} command.
   * <p>
   * Time complexity: O(1)
   * @see <a href="http://redis.io/commands/expire">Expire Command</a>
   * @param key
   * @param unixTime
   * @return Integer reply, specifically: 1: the timeout was set. 0: the timeout was not set since
   *         the key already has an associated timeout (this may happen only in Redis versions &lt;
   *         2.1.3, Redis &gt;= 2.1.3 will happily update the timeout), or the key does not exist.
   */
  @Override
  public Long expireAt(final byte[] key, final long unixTime) {
    checkIsInMultiOrPipeline();
    client.expireAt(key, unixTime);
    return client.getIntegerReply();
  }

  /**
   * The TTL command returns the remaining time to live in seconds of a key that has an
   * {@link #expire(byte[], int) EXPIRE} set. This introspection capability allows a Redis client to
   * check how many seconds a given key will continue to be part of the dataset.
   * @param key
   * @return Integer reply, returns the remaining time to live in seconds of a key that has an
   *         EXPIRE. If the Key does not exists or does not have an associated expire, -1 is
   *         returned.
   */
  @Override
  public Long ttl(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.ttl(key);
    return client.getIntegerReply();
  }

  /**
   * Select the DB with having the specified zero-based numeric index. For default every new client
   * connection is automatically selected to DB 0.
   * @param index
   * @return Status code reply
   */
  @Override
  public String select(final int index) {
    checkIsInMultiOrPipeline();
    client.select(index);
    String statusCodeReply = client.getStatusCodeReply();
    client.setDb(index);

    return statusCodeReply;
  }

  /**
   * Move the specified key from the currently selected DB to the specified destination DB. Note
   * that this command returns 1 only if the key was successfully moved, and 0 if the target key was
   * already there or if the source key was not found at all, so it is possible to use MOVE as a
   * locking primitive.
   * @param key
   * @param dbIndex
   * @return Integer reply, specifically: 1 if the key was moved 0 if the key was not moved because
   *         already present on the target DB or was not found in the current DB.
   */
  @Override
  public Long move(final byte[] key, final int dbIndex) {
    checkIsInMultiOrPipeline();
    client.move(key, dbIndex);
    return client.getIntegerReply();
  }

  /**
   * Delete all the keys of all the existing databases, not just the currently selected one. This
   * command never fails.
   * @return Status code reply
   */
  @Override
  public String flushAll() {
    checkIsInMultiOrPipeline();
    client.flushAll();
    return client.getStatusCodeReply();
  }

  /**
   * GETSET is an atomic set this value and return the old value command. Set key to the string
   * value and return the old value stored at key. The string can't be longer than 1073741824 bytes
   * (1 GB).
   * <p>
   * Time complexity: O(1)
   * @param key
   * @param value
   * @return Bulk reply
   */
  @Override
  public byte[] getSet(final byte[] key, final byte[] value) {
    checkIsInMultiOrPipeline();
    client.getSet(key, value);
    return client.getBinaryBulkReply();
  }

  /**
   * Get the values of all the specified keys. If one or more keys dont exist or is not of type
   * String, a 'nil' value is returned instead of the value of the specified key, but the operation
   * never fails.
   * <p>
   * Time complexity: O(1) for every key
   * @param keys
   * @return Multi bulk reply
   */
  @Override
  public List<byte[]> mget(final byte[]... keys) {
    checkIsInMultiOrPipeline();
    client.mget(keys);
    return client.getBinaryMultiBulkReply();
  }

  /**
   * SETNX works exactly like {@link #set(byte[], byte[]) SET} with the only difference that if the
   * key already exists no operation is performed. SETNX actually means "SET if Not eXists".
   * <p>
   * Time complexity: O(1)
   * @param key
   * @param value
   * @return Integer reply, specifically: 1 if the key was set 0 if the key was not set
   */
  @Override
  public Long setnx(final byte[] key, final byte[] value) {
    checkIsInMultiOrPipeline();
    client.setnx(key, value);
    return client.getIntegerReply();
  }

  /**
   * The command is exactly equivalent to the following group of commands:
   * {@link #set(byte[], byte[]) SET} + {@link #expire(byte[], int) EXPIRE}. The operation is
   * atomic.
   * <p>
   * Time complexity: O(1)
   * @param key
   * @param seconds
   * @param value
   * @return Status code reply
   */
  @Override
  public String setex(final byte[] key, final int seconds, final byte[] value) {
    checkIsInMultiOrPipeline();
    client.setex(key, seconds, value);
    return client.getStatusCodeReply();
  }

  /**
   * Set the the respective keys to the respective values. MSET will replace old values with new
   * values, while {@link #msetnx(byte[]...) MSETNX} will not perform any operation at all even if
   * just a single key already exists.
   * <p>
   * Because of this semantic MSETNX can be used in order to set different keys representing
   * different fields of an unique logic object in a way that ensures that either all the fields or
   * none at all are set.
   * <p>
   * Both MSET and MSETNX are atomic operations. This means that for instance if the keys A and B
   * are modified, another client talking to Redis can either see the changes to both A and B at
   * once, or no modification at all.
   * @see #msetnx(byte[]...)
   * @param keysvalues
   * @return Status code reply Basically +OK as MSET can't fail
   */
  @Override
  public String mset(final byte[]... keysvalues) {
    checkIsInMultiOrPipeline();
    client.mset(keysvalues);
    return client.getStatusCodeReply();
  }

  /**
   * Set the the respective keys to the respective values. {@link #mset(byte[]...) MSET} will
   * replace old values with new values, while MSETNX will not perform any operation at all even if
   * just a single key already exists.
   * <p>
   * Because of this semantic MSETNX can be used in order to set different keys representing
   * different fields of an unique logic object in a way that ensures that either all the fields or
   * none at all are set.
   * <p>
   * Both MSET and MSETNX are atomic operations. This means that for instance if the keys A and B
   * are modified, another client talking to Redis can either see the changes to both A and B at
   * once, or no modification at all.
   * @see #mset(byte[]...)
   * @param keysvalues
   * @return Integer reply, specifically: 1 if the all the keys were set 0 if no key was set (at
   *         least one key already existed)
   */
  @Override
  public Long msetnx(final byte[]... keysvalues) {
    checkIsInMultiOrPipeline();
    client.msetnx(keysvalues);
    return client.getIntegerReply();
  }

  /**
   * DECRBY work just like {@link #decr(byte[]) INCR} but instead to decrement by 1 the decrement is
   * integer.
   * <p>
   * INCR commands are limited to 64 bit signed integers.
   * <p>
   * Note: this is actually a string operation, that is, in Redis there are not "integer" types.
   * Simply the string stored at the key is parsed as a base 10 64 bit signed integer, incremented,
   * and then converted back as a string.
   * <p>
   * Time complexity: O(1)
   * @see #incr(byte[])
   * @see #decr(byte[])
   * @see #incrBy(byte[], long)
   * @param key
   * @param integer
   * @return Integer reply, this commands will reply with the new value of key after the increment.
   */
  @Override
  public Long decrBy(final byte[] key, final long integer) {
    checkIsInMultiOrPipeline();
    client.decrBy(key, integer);
    return client.getIntegerReply();
  }

  /**
   * Decrement the number stored at key by one. If the key does not exist or contains a value of a
   * wrong type, set the key to the value of "0" before to perform the decrement operation.
   * <p>
   * INCR commands are limited to 64 bit signed integers.
   * <p>
   * Note: this is actually a string operation, that is, in Redis there are not "integer" types.
   * Simply the string stored at the key is parsed as a base 10 64 bit signed integer, incremented,
   * and then converted back as a string.
   * <p>
   * Time complexity: O(1)
   * @see #incr(byte[])
   * @see #incrBy(byte[], long)
   * @see #decrBy(byte[], long)
   * @param key
   * @return Integer reply, this commands will reply with the new value of key after the increment.
   */
  @Override
  public Long decr(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.decr(key);
    return client.getIntegerReply();
  }

  /**
   * INCRBY work just like {@link #incr(byte[]) INCR} but instead to increment by 1 the increment is
   * integer.
   * <p>
   * INCR commands are limited to 64 bit signed integers.
   * <p>
   * Note: this is actually a string operation, that is, in Redis there are not "integer" types.
   * Simply the string stored at the key is parsed as a base 10 64 bit signed integer, incremented,
   * and then converted back as a string.
   * <p>
   * Time complexity: O(1)
   * @see #incr(byte[])
   * @see #decr(byte[])
   * @see #decrBy(byte[], long)
   * @param key
   * @param integer
   * @return Integer reply, this commands will reply with the new value of key after the increment.
   */
  @Override
  public Long incrBy(final byte[] key, final long integer) {
    checkIsInMultiOrPipeline();
    client.incrBy(key, integer);
    return client.getIntegerReply();
  }

  /**
   * INCRBYFLOAT work just like {@link #incrBy(byte[], long)} INCRBY} but increments by floats
   * instead of integers.
   * <p>
   * INCRBYFLOAT commands are limited to double precision floating point values.
   * <p>
   * Note: this is actually a string operation, that is, in Redis there are not "double" types.
   * Simply the string stored at the key is parsed as a base double precision floating point value,
   * incremented, and then converted back as a string. There is no DECRYBYFLOAT but providing a
   * negative value will work as expected.
   * <p>
   * Time complexity: O(1)
   * @see #incr(byte[])
   * @see #decr(byte[])
   * @see #decrBy(byte[], long)
   * @param key the key to increment
   * @param integer the value to increment by
   * @return Integer reply, this commands will reply with the new value of key after the increment.
   */
  @Override
  public Double incrByFloat(final byte[] key, final double integer) {
    checkIsInMultiOrPipeline();
    client.incrByFloat(key, integer);
    String dval = client.getBulkReply();
    return (dval != null ? new Double(dval) : null);
  }

  /**
   * Increment the number stored at key by one. If the key does not exist or contains a value of a
   * wrong type, set the key to the value of "0" before to perform the increment operation.
   * <p>
   * INCR commands are limited to 64 bit signed integers.
   * <p>
   * Note: this is actually a string operation, that is, in Redis there are not "integer" types.
   * Simply the string stored at the key is parsed as a base 10 64 bit signed integer, incremented,
   * and then converted back as a string.
   * <p>
   * Time complexity: O(1)
   * @see #incrBy(byte[], long)
   * @see #decr(byte[])
   * @see #decrBy(byte[], long)
   * @param key
   * @return Integer reply, this commands will reply with the new value of key after the increment.
   */
  @Override
  public Long incr(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.incr(key);
    return client.getIntegerReply();
  }

  /**
   * If the key already exists and is a string, this command appends the provided value at the end
   * of the string. If the key does not exist it is created and set as an empty string, so APPEND
   * will be very similar to SET in this special case.
   * <p>
   * Time complexity: O(1). The amortized time complexity is O(1) assuming the appended value is
   * small and the already present value is of any size, since the dynamic string library used by
   * Redis will double the free space available on every reallocation.
   * @param key
   * @param value
   * @return Integer reply, specifically the total length of the string after the append operation.
   */
  @Override
  public Long append(final byte[] key, final byte[] value) {
    checkIsInMultiOrPipeline();
    client.append(key, value);
    return client.getIntegerReply();
  }

  /**
   * Return a subset of the string from offset start to offset end (both offsets are inclusive).
   * Negative offsets can be used in order to provide an offset starting from the end of the string.
   * So -1 means the last char, -2 the penultimate and so forth.
   * <p>
   * The function handles out of range requests without raising an error, but just limiting the
   * resulting range to the actual length of the string.
   * <p>
   * Time complexity: O(start+n) (with start being the start index and n the total length of the
   * requested range). Note that the lookup part of this command is O(1) so for small strings this
   * is actually an O(1) command.
   * @param key
   * @param start
   * @param end
   * @return Bulk reply
   */
  @Override
  public byte[] substr(final byte[] key, final int start, final int end) {
    checkIsInMultiOrPipeline();
    client.substr(key, start, end);
    return client.getBinaryBulkReply();
  }

  /**
   * Set the specified hash field to the specified value.
   * <p>
   * If key does not exist, a new key holding a hash is created.
   * <p>
   * <b>Time complexity:</b> O(1)
   * @param key
   * @param field
   * @param value
   * @return If the field already exists, and the HSET just produced an update of the value, 0 is
   *         returned, otherwise if a new field is created 1 is returned.
   */
  @Override
  public Long hset(final byte[] key, final byte[] field, final byte[] value) {
    checkIsInMultiOrPipeline();
    client.hset(key, field, value);
    return client.getIntegerReply();
  }

  /**
   * If key holds a hash, retrieve the value associated to the specified field.
   * <p>
   * If the field is not found or the key does not exist, a special 'nil' value is returned.
   * <p>
   * <b>Time complexity:</b> O(1)
   * @param key
   * @param field
   * @return Bulk reply
   */
  @Override
  public byte[] hget(final byte[] key, final byte[] field) {
    checkIsInMultiOrPipeline();
    client.hget(key, field);
    return client.getBinaryBulkReply();
  }

  /**
   * Set the specified hash field to the specified value if the field not exists. <b>Time
   * complexity:</b> O(1)
   * @param key
   * @param field
   * @param value
   * @return If the field already exists, 0 is returned, otherwise if a new field is created 1 is
   *         returned.
   */
  @Override
  public Long hsetnx(final byte[] key, final byte[] field, final byte[] value) {
    checkIsInMultiOrPipeline();
    client.hsetnx(key, field, value);
    return client.getIntegerReply();
  }

  /**
   * Set the respective fields to the respective values. HMSET replaces old values with new values.
   * <p>
   * If key does not exist, a new key holding a hash is created.
   * <p>
   * <b>Time complexity:</b> O(N) (with N being the number of fields)
   * @param key
   * @param hash
   * @return Always OK because HMSET can't fail
   */
  @Override
  public String hmset(final byte[] key, final Map<byte[], byte[]> hash) {
    checkIsInMultiOrPipeline();
    client.hmset(key, hash);
    return client.getStatusCodeReply();
  }

  /**
   * Retrieve the values associated to the specified fields.
   * <p>
   * If some of the specified fields do not exist, nil values are returned. Non existing keys are
   * considered like empty hashes.
   * <p>
   * <b>Time complexity:</b> O(N) (with N being the number of fields)
   * @param key
   * @param fields
   * @return Multi Bulk Reply specifically a list of all the values associated with the specified
   *         fields, in the same order of the request.
   */
  @Override
  public List<byte[]> hmget(final byte[] key, final byte[]... fields) {
    checkIsInMultiOrPipeline();
    client.hmget(key, fields);
    return client.getBinaryMultiBulkReply();
  }

  /**
   * Increment the number stored at field in the hash at key by value. If key does not exist, a new
   * key holding a hash is created. If field does not exist or holds a string, the value is set to 0
   * before applying the operation. Since the value argument is signed you can use this command to
   * perform both increments and decrements.
   * <p>
   * The range of values supported by HINCRBY is limited to 64 bit signed integers.
   * <p>
   * <b>Time complexity:</b> O(1)
   * @param key
   * @param field
   * @param value
   * @return Integer reply The new value at field after the increment operation.
   */
  @Override
  public Long hincrBy(final byte[] key, final byte[] field, final long value) {
    checkIsInMultiOrPipeline();
    client.hincrBy(key, field, value);
    return client.getIntegerReply();
  }

  /**
   * Increment the number stored at field in the hash at key by a double precision floating point
   * value. If key does not exist, a new key holding a hash is created. If field does not exist or
   * holds a string, the value is set to 0 before applying the operation. Since the value argument
   * is signed you can use this command to perform both increments and decrements.
   * <p>
   * The range of values supported by HINCRBYFLOAT is limited to double precision floating point
   * values.
   * <p>
   * <b>Time complexity:</b> O(1)
   * @param key
   * @param field
   * @param value
   * @return Double precision floating point reply The new value at field after the increment
   *         operation.
   */
  @Override
  public Double hincrByFloat(final byte[] key, final byte[] field, final double value) {
    checkIsInMultiOrPipeline();
    client.hincrByFloat(key, field, value);
    final String dval = client.getBulkReply();
    return (dval != null ? new Double(dval) : null);
  }

  /**
   * Test for existence of a specified field in a hash. <b>Time complexity:</b> O(1)
   * @param key
   * @param field
   * @return Return 1 if the hash stored at key contains the specified field. Return 0 if the key is
   *         not found or the field is not present.
   */
  @Override
  public Boolean hexists(final byte[] key, final byte[] field) {
    checkIsInMultiOrPipeline();
    client.hexists(key, field);
    return client.getIntegerReply() == 1;
  }

  /**
   * Remove the specified field from an hash stored at key.
   * <p>
   * <b>Time complexity:</b> O(1)
   * @param key
   * @param fields
   * @return If the field was present in the hash it is deleted and 1 is returned, otherwise 0 is
   *         returned and no operation is performed.
   */
  @Override
  public Long hdel(final byte[] key, final byte[]... fields) {
    checkIsInMultiOrPipeline();
    client.hdel(key, fields);
    return client.getIntegerReply();
  }

  /**
   * Return the number of items in a hash.
   * <p>
   * <b>Time complexity:</b> O(1)
   * @param key
   * @return The number of entries (fields) contained in the hash stored at key. If the specified
   *         key does not exist, 0 is returned assuming an empty hash.
   */
  @Override
  public Long hlen(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.hlen(key);
    return client.getIntegerReply();
  }

  /**
   * Return all the fields in a hash.
   * <p>
   * <b>Time complexity:</b> O(N), where N is the total number of entries
   * @param key
   * @return All the fields names contained into a hash.
   */
  @Override
  public Set<byte[]> hkeys(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.hkeys(key);
    return SetFromList.of(client.getBinaryMultiBulkReply());
  }

  /**
   * Return all the values in a hash.
   * <p>
   * <b>Time complexity:</b> O(N), where N is the total number of entries
   * @param key
   * @return All the fields values contained into a hash.
   */
  @Override
  public List<byte[]> hvals(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.hvals(key);
    return client.getBinaryMultiBulkReply();
  }

  /**
   * Return all the fields and associated values in a hash.
   * <p>
   * <b>Time complexity:</b> O(N), where N is the total number of entries
   * @param key
   * @return All the fields and values contained into a hash.
   */
  @Override
  public Map<byte[], byte[]> hgetAll(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.hgetAll(key);
    final List<byte[]> flatHash = client.getBinaryMultiBulkReply();
    final Map<byte[], byte[]> hash = new JedisByteHashMap();
    final Iterator<byte[]> iterator = flatHash.iterator();
    while (iterator.hasNext()) {
      hash.put(iterator.next(), iterator.next());
    }

    return hash;
  }

  /**
   * Add the string value to the head (LPUSH) or tail (RPUSH) of the list stored at key. If the key
   * does not exist an empty list is created just before the append operation. If the key exists but
   * is not a List an error is returned.
   * <p>
   * Time complexity: O(1)
   * @see BinaryJedis#rpush(byte[], byte[]...)
   * @param key
   * @param strings
   * @return Integer reply, specifically, the number of elements inside the list after the push
   *         operation.
   */
  @Override
  public Long rpush(final byte[] key, final byte[]... strings) {
    checkIsInMultiOrPipeline();
    client.rpush(key, strings);
    return client.getIntegerReply();
  }

  /**
   * Add the string value to the head (LPUSH) or tail (RPUSH) of the list stored at key. If the key
   * does not exist an empty list is created just before the append operation. If the key exists but
   * is not a List an error is returned.
   * <p>
   * Time complexity: O(1)
   * @see BinaryJedis#rpush(byte[], byte[]...)
   * @param key
   * @param strings
   * @return Integer reply, specifically, the number of elements inside the list after the push
   *         operation.
   */
  @Override
  public Long lpush(final byte[] key, final byte[]... strings) {
    checkIsInMultiOrPipeline();
    client.lpush(key, strings);
    return client.getIntegerReply();
  }

  /**
   * Return the length of the list stored at the specified key. If the key does not exist zero is
   * returned (the same behaviour as for empty lists). If the value stored at key is not a list an
   * error is returned.
   * <p>
   * Time complexity: O(1)
   * @param key
   * @return The length of the list.
   */
  @Override
  public Long llen(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.llen(key);
    return client.getIntegerReply();
  }

  /**
   * Return the specified elements of the list stored at the specified key. Start and end are
   * zero-based indexes. 0 is the first element of the list (the list head), 1 the next element and
   * so on.
   * <p>
   * For example LRANGE foobar 0 2 will return the first three elements of the list.
   * <p>
   * start and end can also be negative numbers indicating offsets from the end of the list. For
   * example -1 is the last element of the list, -2 the penultimate element and so on.
   * <p>
   * <b>Consistency with range functions in various programming languages</b>
   * <p>
   * Note that if you have a list of numbers from 0 to 100, LRANGE 0 10 will return 11 elements,
   * that is, rightmost item is included. This may or may not be consistent with behavior of
   * range-related functions in your programming language of choice (think Ruby's Range.new,
   * Array#slice or Python's range() function).
   * <p>
   * LRANGE behavior is consistent with one of Tcl.
   * <p>
   * <b>Out-of-range indexes</b>
   * <p>
   * Indexes out of range will not produce an error: if start is over the end of the list, or start
   * &gt; end, an empty list is returned. If end is over the end of the list Redis will threat it
   * just like the last element of the list.
   * <p>
   * Time complexity: O(start+n) (with n being the length of the range and start being the start
   * offset)
   * @param key
   * @param start
   * @param end
   * @return Multi bulk reply, specifically a list of elements in the specified range.
   */
  @Override
  public List<byte[]> lrange(final byte[] key, final long start, final long end) {
    checkIsInMultiOrPipeline();
    client.lrange(key, start, end);
    return client.getBinaryMultiBulkReply();
  }

  /**
   * Trim an existing list so that it will contain only the specified range of elements specified.
   * Start and end are zero-based indexes. 0 is the first element of the list (the list head), 1 the
   * next element and so on.
   * <p>
   * For example LTRIM foobar 0 2 will modify the list stored at foobar key so that only the first
   * three elements of the list will remain.
   * <p>
   * start and end can also be negative numbers indicating offsets from the end of the list. For
   * example -1 is the last element of the list, -2 the penultimate element and so on.
   * <p>
   * Indexes out of range will not produce an error: if start is over the end of the list, or start
   * &gt; end, an empty list is left as value. If end over the end of the list Redis will threat it
   * just like the last element of the list.
   * <p>
   * Hint: the obvious use of LTRIM is together with LPUSH/RPUSH. For example:
   * <p>
   * {@code lpush("mylist", "someelement"); ltrim("mylist", 0, 99); * }
   * <p>
   * The above two commands will push elements in the list taking care that the list will not grow
   * without limits. This is very useful when using Redis to store logs for example. It is important
   * to note that when used in this way LTRIM is an O(1) operation because in the average case just
   * one element is removed from the tail of the list.
   * <p>
   * Time complexity: O(n) (with n being len of list - len of range)
   * @param key
   * @param start
   * @param end
   * @return Status code reply
   */
  @Override
  public String ltrim(final byte[] key, final long start, final long end) {
    checkIsInMultiOrPipeline();
    client.ltrim(key, start, end);
    return client.getStatusCodeReply();
  }

  /**
   * Return the specified element of the list stored at the specified key. 0 is the first element, 1
   * the second and so on. Negative indexes are supported, for example -1 is the last element, -2
   * the penultimate and so on.
   * <p>
   * If the value stored at key is not of list type an error is returned. If the index is out of
   * range a 'nil' reply is returned.
   * <p>
   * Note that even if the average time complexity is O(n) asking for the first or the last element
   * of the list is O(1).
   * <p>
   * Time complexity: O(n) (with n being the length of the list)
   * @param key
   * @param index
   * @return Bulk reply, specifically the requested element
   */
  @Override
  public byte[] lindex(final byte[] key, final long index) {
    checkIsInMultiOrPipeline();
    client.lindex(key, index);
    return client.getBinaryBulkReply();
  }

  /**
   * Set a new value as the element at index position of the List at key.
   * <p>
   * Out of range indexes will generate an error.
   * <p>
   * Similarly to other list commands accepting indexes, the index can be negative to access
   * elements starting from the end of the list. So -1 is the last element, -2 is the penultimate,
   * and so forth.
   * <p>
   * <b>Time complexity:</b>
   * <p>
   * O(N) (with N being the length of the list), setting the first or last elements of the list is
   * O(1).
   * @see #lindex(byte[], long)
   * @param key
   * @param index
   * @param value
   * @return Status code reply
   */
  @Override
  public String lset(final byte[] key, final long index, final byte[] value) {
    checkIsInMultiOrPipeline();
    client.lset(key, index, value);
    return client.getStatusCodeReply();
  }

  /**
   * Remove the first count occurrences of the value element from the list. If count is zero all the
   * elements are removed. If count is negative elements are removed from tail to head, instead to
   * go from head to tail that is the normal behaviour. So for example LREM with count -2 and hello
   * as value to remove against the list (a,b,c,hello,x,hello,hello) will have the list
   * (a,b,c,hello,x). The number of removed elements is returned as an integer, see below for more
   * information about the returned value. Note that non existing keys are considered like empty
   * lists by LREM, so LREM against non existing keys will always return 0.
   * <p>
   * Time complexity: O(N) (with N being the length of the list)
   * @param key
   * @param count
   * @param value
   * @return Integer Reply, specifically: The number of removed elements if the operation succeeded
   */
  @Override
  public Long lrem(final byte[] key, final long count, final byte[] value) {
    checkIsInMultiOrPipeline();
    client.lrem(key, count, value);
    return client.getIntegerReply();
  }

  /**
   * Atomically return and remove the first (LPOP) or last (RPOP) element of the list. For example
   * if the list contains the elements "a","b","c" LPOP will return "a" and the list will become
   * "b","c".
   * <p>
   * If the key does not exist or the list is already empty the special value 'nil' is returned.
   * @see #rpop(byte[])
   * @param key
   * @return Bulk reply
   */
  @Override
  public byte[] lpop(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.lpop(key);
    return client.getBinaryBulkReply();
  }

  /**
   * Atomically return and remove the first (LPOP) or last (RPOP) element of the list. For example
   * if the list contains the elements "a","b","c" LPOP will return "a" and the list will become
   * "b","c".
   * <p>
   * If the key does not exist or the list is already empty the special value 'nil' is returned.
   * @see #lpop(byte[])
   * @param key
   * @return Bulk reply
   */
  @Override
  public byte[] rpop(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.rpop(key);
    return client.getBinaryBulkReply();
  }

  /**
   * Atomically return and remove the last (tail) element of the srckey list, and push the element
   * as the first (head) element of the dstkey list. For example if the source list contains the
   * elements "a","b","c" and the destination list contains the elements "foo","bar" after an
   * RPOPLPUSH command the content of the two lists will be "a","b" and "c","foo","bar".
   * <p>
   * If the key does not exist or the list is already empty the special value 'nil' is returned. If
   * the srckey and dstkey are the same the operation is equivalent to removing the last element
   * from the list and pusing it as first element of the list, so it's a "list rotation" command.
   * <p>
   * Time complexity: O(1)
   * @param srckey
   * @param dstkey
   * @return Bulk reply
   */
  @Override
  public byte[] rpoplpush(final byte[] srckey, final byte[] dstkey) {
    checkIsInMultiOrPipeline();
    client.rpoplpush(srckey, dstkey);
    return client.getBinaryBulkReply();
  }

  /**
   * Add the specified member to the set value stored at key. If member is already a member of the
   * set no operation is performed. If key does not exist a new set with the specified member as
   * sole member is created. If the key exists but does not hold a set value an error is returned.
   * <p>
   * Time complexity O(1)
   * @param key
   * @param members
   * @return Integer reply, specifically: 1 if the new element was added 0 if the element was
   *         already a member of the set
   */
  @Override
  public Long sadd(final byte[] key, final byte[]... members) {
    checkIsInMultiOrPipeline();
    client.sadd(key, members);
    return client.getIntegerReply();
  }

  /**
   * Return all the members (elements) of the set value stored at key. This is just syntax glue for
   * {@link #sinter(byte[]...)} SINTER}.
   * <p>
   * Time complexity O(N)
   * @param key the key of the set
   * @return Multi bulk reply
   */
  @Override
  public Set<byte[]> smembers(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.smembers(key);
    return SetFromList.of(client.getBinaryMultiBulkReply());
  }

  /**
   * Remove the specified member from the set value stored at key. If member was not a member of the
   * set no operation is performed. If key does not hold a set value an error is returned.
   * <p>
   * Time complexity O(1)
   * @param key the key of the set
   * @param member the set member to remove
   * @return Integer reply, specifically: 1 if the new element was removed 0 if the new element was
   *         not a member of the set
   */
  @Override
  public Long srem(final byte[] key, final byte[]... member) {
    checkIsInMultiOrPipeline();
    client.srem(key, member);
    return client.getIntegerReply();
  }

  /**
   * Remove a random element from a Set returning it as return value. If the Set is empty or the key
   * does not exist, a nil object is returned.
   * <p>
   * The {@link #srandmember(byte[])} command does a similar work but the returned element is not
   * removed from the Set.
   * <p>
   * Time complexity O(1)
   * @param key
   * @return Bulk reply
   */
  @Override
  public byte[] spop(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.spop(key);
    return client.getBinaryBulkReply();
  }

  @Override
  public Set<byte[]> spop(final byte[] key, final long count) {
    checkIsInMultiOrPipeline();
    client.spop(key, count);
    return SetFromList.of(client.getBinaryMultiBulkReply());
  }

  /**
   * Move the specified member from the set at srckey to the set at dstkey. This operation is
   * atomic, in every given moment the element will appear to be in the source or destination set
   * for accessing clients.
   * <p>
   * If the source set does not exist or does not contain the specified element no operation is
   * performed and zero is returned, otherwise the element is removed from the source set and added
   * to the destination set. On success one is returned, even if the element was already present in
   * the destination set.
   * <p>
   * An error is raised if the source or destination keys contain a non Set value.
   * <p>
   * Time complexity O(1)
   * @param srckey
   * @param dstkey
   * @param member
   * @return Integer reply, specifically: 1 if the element was moved 0 if the element was not found
   *         on the first set and no operation was performed
   */
  @Override
  public Long smove(final byte[] srckey, final byte[] dstkey, final byte[] member) {
    checkIsInMultiOrPipeline();
    client.smove(srckey, dstkey, member);
    return client.getIntegerReply();
  }

  /**
   * Return the set cardinality (number of elements). If the key does not exist 0 is returned, like
   * for empty sets.
   * @param key
   * @return Integer reply, specifically: the cardinality (number of elements) of the set as an
   *         integer.
   */
  @Override
  public Long scard(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.scard(key);
    return client.getIntegerReply();
  }

  /**
   * Return 1 if member is a member of the set stored at key, otherwise 0 is returned.
   * <p>
   * Time complexity O(1)
   * @param key
   * @param member
   * @return Integer reply, specifically: 1 if the element is a member of the set 0 if the element
   *         is not a member of the set OR if the key does not exist
   */
  @Override
  public Boolean sismember(final byte[] key, final byte[] member) {
    checkIsInMultiOrPipeline();
    client.sismember(key, member);
    return client.getIntegerReply() == 1;
  }

  /**
   * Return the members of a set resulting from the intersection of all the sets hold at the
   * specified keys. Like in {@link #lrange(byte[], long, long)} LRANGE} the result is sent to the
   * client as a multi-bulk reply (see the protocol specification for more information). If just a
   * single key is specified, then this command produces the same result as
   * {@link #smembers(byte[]) SMEMBERS}. Actually SMEMBERS is just syntax sugar for SINTER.
   * <p>
   * Non existing keys are considered like empty sets, so if one of the keys is missing an empty set
   * is returned (since the intersection with an empty set always is an empty set).
   * <p>
   * Time complexity O(N*M) worst case where N is the cardinality of the smallest set and M the
   * number of sets
   * @param keys
   * @return Multi bulk reply, specifically the list of common elements.
   */
  @Override
  public Set<byte[]> sinter(final byte[]... keys) {
    checkIsInMultiOrPipeline();
    client.sinter(keys);
    return SetFromList.of(client.getBinaryMultiBulkReply());
  }

  /**
   * This commnad works exactly like {@link #sinter(byte[]...) SINTER} but instead of being returned
   * the resulting set is sotred as dstkey.
   * <p>
   * Time complexity O(N*M) worst case where N is the cardinality of the smallest set and M the
   * number of sets
   * @param dstkey
   * @param keys
   * @return Status code reply
   */
  @Override
  public Long sinterstore(final byte[] dstkey, final byte[]... keys) {
    checkIsInMultiOrPipeline();
    client.sinterstore(dstkey, keys);
    return client.getIntegerReply();
  }

  /**
   * Return the members of a set resulting from the union of all the sets hold at the specified
   * keys. Like in {@link #lrange(byte[], long, long)} LRANGE} the result is sent to the client as a
   * multi-bulk reply (see the protocol specification for more information). If just a single key is
   * specified, then this command produces the same result as {@link #smembers(byte[]) SMEMBERS}.
   * <p>
   * Non existing keys are considered like empty sets.
   * <p>
   * Time complexity O(N) where N is the total number of elements in all the provided sets
   * @param keys
   * @return Multi bulk reply, specifically the list of common elements.
   */
  @Override
  public Set<byte[]> sunion(final byte[]... keys) {
    checkIsInMultiOrPipeline();
    client.sunion(keys);
    return SetFromList.of(client.getBinaryMultiBulkReply());
  }

  /**
   * This command works exactly like {@link #sunion(byte[]...) SUNION} but instead of being returned
   * the resulting set is stored as dstkey. Any existing value in dstkey will be over-written.
   * <p>
   * Time complexity O(N) where N is the total number of elements in all the provided sets
   * @param dstkey
   * @param keys
   * @return Status code reply
   */
  @Override
  public Long sunionstore(final byte[] dstkey, final byte[]... keys) {
    checkIsInMultiOrPipeline();
    client.sunionstore(dstkey, keys);
    return client.getIntegerReply();
  }

  /**
   * Return the difference between the Set stored at key1 and all the Sets key2, ..., keyN
   * <p>
   * <b>Example:</b>
   * 
   * <pre>
   * key1 = [x, a, b, c]
   * key2 = [c]
   * key3 = [a, d]
   * SDIFF key1,key2,key3 =&gt; [x, b]
   * </pre>
   * 
   * Non existing keys are considered like empty sets.
   * <p>
   * <b>Time complexity:</b>
   * <p>
   * O(N) with N being the total number of elements of all the sets
   * @param keys
   * @return Return the members of a set resulting from the difference between the first set
   *         provided and all the successive sets.
   */
  @Override
  public Set<byte[]> sdiff(final byte[]... keys) {
    checkIsInMultiOrPipeline();
    client.sdiff(keys);
    return SetFromList.of(client.getBinaryMultiBulkReply());
  }

  /**
   * This command works exactly like {@link #sdiff(byte[]...) SDIFF} but instead of being returned
   * the resulting set is stored in dstkey.
   * @param dstkey
   * @param keys
   * @return Status code reply
   */
  @Override
  public Long sdiffstore(final byte[] dstkey, final byte[]... keys) {
    checkIsInMultiOrPipeline();
    client.sdiffstore(dstkey, keys);
    return client.getIntegerReply();
  }

  /**
   * Return a random element from a Set, without removing the element. If the Set is empty or the
   * key does not exist, a nil object is returned.
   * <p>
   * The SPOP command does a similar work but the returned element is popped (removed) from the Set.
   * <p>
   * Time complexity O(1)
   * @param key
   * @return Bulk reply
   */
  @Override
  public byte[] srandmember(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.srandmember(key);
    return client.getBinaryBulkReply();
  }

  @Override
  public List<byte[]> srandmember(final byte[] key, final int count) {
    checkIsInMultiOrPipeline();
    client.srandmember(key, count);
    return client.getBinaryMultiBulkReply();
  }

  /**
   * Add the specified member having the specifeid score to the sorted set stored at key. If member
   * is already a member of the sorted set the score is updated, and the element reinserted in the
   * right position to ensure sorting. If key does not exist a new sorted set with the specified
   * member as sole member is crated. If the key exists but does not hold a sorted set value an
   * error is returned.
   * <p>
   * The score value can be the string representation of a double precision floating point number.
   * <p>
   * Time complexity O(log(N)) with N being the number of elements in the sorted set
   * @param key
   * @param score
   * @param member
   * @return Integer reply, specifically: 1 if the new element was added 0 if the element was
   *         already a member of the sorted set and the score was updated
   */
  @Override
  public Long zadd(final byte[] key, final double score, final byte[] member) {
    checkIsInMultiOrPipeline();
    client.zadd(key, score, member);
    return client.getIntegerReply();
  }

  @Override
  public Long zadd(final byte[] key, final Map<byte[], Double> scoreMembers) {
    checkIsInMultiOrPipeline();
    client.zaddBinary(key, scoreMembers);
    return client.getIntegerReply();
  }

  @Override
  public Set<byte[]> zrange(final byte[] key, final long start, final long end) {
    checkIsInMultiOrPipeline();
    client.zrange(key, start, end);
    return SetFromList.of(client.getBinaryMultiBulkReply());
  }

  /**
   * Remove the specified member from the sorted set value stored at key. If member was not a member
   * of the set no operation is performed. If key does not not hold a set value an error is
   * returned.
   * <p>
   * Time complexity O(log(N)) with N being the number of elements in the sorted set
   * @param key
   * @param members
   * @return Integer reply, specifically: 1 if the new element was removed 0 if the new element was
   *         not a member of the set
   */
  @Override
  public Long zrem(final byte[] key, final byte[]... members) {
    checkIsInMultiOrPipeline();
    client.zrem(key, members);
    return client.getIntegerReply();
  }

  /**
   * If member already exists in the sorted set adds the increment to its score and updates the
   * position of the element in the sorted set accordingly. If member does not already exist in the
   * sorted set it is added with increment as score (that is, like if the previous score was
   * virtually zero). If key does not exist a new sorted set with the specified member as sole
   * member is crated. If the key exists but does not hold a sorted set value an error is returned.
   * <p>
   * The score value can be the string representation of a double precision floating point number.
   * It's possible to provide a negative value to perform a decrement.
   * <p>
   * For an introduction to sorted sets check the Introduction to Redis data types page.
   * <p>
   * Time complexity O(log(N)) with N being the number of elements in the sorted set
   * @param key
   * @param score
   * @param member
   * @return The new score
   */
  @Override
  public Double zincrby(final byte[] key, final double score, final byte[] member) {
    checkIsInMultiOrPipeline();
    client.zincrby(key, score, member);
    String newscore = client.getBulkReply();
    return Double.valueOf(newscore);
  }

  /**
   * Return the rank (or index) or member in the sorted set at key, with scores being ordered from
   * low to high.
   * <p>
   * When the given member does not exist in the sorted set, the special value 'nil' is returned.
   * The returned rank (or index) of the member is 0-based for both commands.
   * <p>
   * <b>Time complexity:</b>
   * <p>
   * O(log(N))
   * @see #zrevrank(byte[], byte[])
   * @param key
   * @param member
   * @return Integer reply or a nil bulk reply, specifically: the rank of the element as an integer
   *         reply if the element exists. A nil bulk reply if there is no such element.
   */
  @Override
  public Long zrank(final byte[] key, final byte[] member) {
    checkIsInMultiOrPipeline();
    client.zrank(key, member);
    return client.getIntegerReply();
  }

  /**
   * Return the rank (or index) or member in the sorted set at key, with scores being ordered from
   * high to low.
   * <p>
   * When the given member does not exist in the sorted set, the special value 'nil' is returned.
   * The returned rank (or index) of the member is 0-based for both commands.
   * <p>
   * <b>Time complexity:</b>
   * <p>
   * O(log(N))
   * @see #zrank(byte[], byte[])
   * @param key
   * @param member
   * @return Integer reply or a nil bulk reply, specifically: the rank of the element as an integer
   *         reply if the element exists. A nil bulk reply if there is no such element.
   */
  @Override
  public Long zrevrank(final byte[] key, final byte[] member) {
    checkIsInMultiOrPipeline();
    client.zrevrank(key, member);
    return client.getIntegerReply();
  }

  @Override
  public Set<byte[]> zrevrange(final byte[] key, final long start, final long end) {
    checkIsInMultiOrPipeline();
    client.zrevrange(key, start, end);
    return SetFromList.of(client.getBinaryMultiBulkReply());
  }

  @Override
  public Set<Tuple> zrangeWithScores(final byte[] key, final long start, final long end) {
    checkIsInMultiOrPipeline();
    client.zrangeWithScores(key, start, end);
    return getBinaryTupledSet();
  }

  @Override
  public Set<Tuple> zrevrangeWithScores(final byte[] key, final long start, final long end) {
    checkIsInMultiOrPipeline();
    client.zrevrangeWithScores(key, start, end);
    return getBinaryTupledSet();
  }

  /**
   * Return the sorted set cardinality (number of elements). If the key does not exist 0 is
   * returned, like for empty sorted sets.
   * <p>
   * Time complexity O(1)
   * @param key
   * @return the cardinality (number of elements) of the set as an integer.
   */
  @Override
  public Long zcard(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.zcard(key);
    return client.getIntegerReply();
  }

  /**
   * Return the score of the specified element of the sorted set at key. If the specified element
   * does not exist in the sorted set, or the key does not exist at all, a special 'nil' value is
   * returned.
   * <p>
   * <b>Time complexity:</b> O(1)
   * @param key
   * @param member
   * @return the score
   */
  @Override
  public Double zscore(final byte[] key, final byte[] member) {
    checkIsInMultiOrPipeline();
    client.zscore(key, member);
    final String score = client.getBulkReply();
    return (score != null ? new Double(score) : null);
  }

  public Transaction multi() {
    client.multi();
    client.getOne(); // expected OK
    transaction = new Transaction(client);
    return transaction;
  }

  protected void checkIsInMultiOrPipeline() {
    if (client.isInMulti()) {
      throw new JedisDataException(
          "Cannot use Jedis when in Multi. Please use Transation or reset jedis state.");
    } else if (pipeline != null && pipeline.hasPipelinedResponse()) {
      throw new JedisDataException(
          "Cannot use Jedis when in Pipeline. Please use Pipeline or reset jedis state .");
    }
  }

  public void connect() {
    client.connect();
  }

  public void disconnect() {
    client.disconnect();
  }

  public void resetState() {
    if (client.isConnected()) {
      if (transaction != null) {
        transaction.clear();
      }

      if (pipeline != null) {
        pipeline.clear();
      }

      if (client.isInWatch()) {
        unwatch();
      }

      client.resetState();
    }

    transaction = null;
    pipeline = null;
  }

  @Override
  public String watch(final byte[]... keys) {
    client.watch(keys);
    return client.getStatusCodeReply();
  }

  @Override
  public String unwatch() {
    client.unwatch();
    return client.getStatusCodeReply();
  }

  @Override
  public void close() {
    client.close();
  }

  /**
   * Sort a Set or a List.
   * <p>
   * Sort the elements contained in the List, Set, or Sorted Set value at key. By default sorting is
   * numeric with elements being compared as double precision floating point numbers. This is the
   * simplest form of SORT.
   * @see #sort(byte[], byte[])
   * @see #sort(byte[], SortingParams)
   * @see #sort(byte[], SortingParams, byte[])
   * @param key
   * @return Assuming the Set/List at key contains a list of numbers, the return value will be the
   *         list of numbers ordered from the smallest to the biggest number.
   */
  @Override
  public List<byte[]> sort(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.sort(key);
    return client.getBinaryMultiBulkReply();
  }

  /**
   * Sort a Set or a List accordingly to the specified parameters.
   * <p>
   * <b>examples:</b>
   * <p>
   * Given are the following sets and key/values:
   * 
   * <pre>
   * x = [1, 2, 3]
   * y = [a, b, c]
   * 
   * k1 = z
   * k2 = y
   * k3 = x
   * 
   * w1 = 9
   * w2 = 8
   * w3 = 7
   * </pre>
   * 
   * Sort Order:
   * 
   * <pre>
   * sort(x) or sort(x, sp.asc())
   * -&gt; [1, 2, 3]
   * 
   * sort(x, sp.desc())
   * -&gt; [3, 2, 1]
   * 
   * sort(y)
   * -&gt; [c, a, b]
   * 
   * sort(y, sp.alpha())
   * -&gt; [a, b, c]
   * 
   * sort(y, sp.alpha().desc())
   * -&gt; [c, a, b]
   * </pre>
   * 
   * Limit (e.g. for Pagination):
   * 
   * <pre>
   * sort(x, sp.limit(0, 2))
   * -&gt; [1, 2]
   * 
   * sort(y, sp.alpha().desc().limit(1, 2))
   * -&gt; [b, a]
   * </pre>
   * 
   * Sorting by external keys:
   * 
   * <pre>
   * sort(x, sb.by(w*))
   * -&gt; [3, 2, 1]
   * 
   * sort(x, sb.by(w*).desc())
   * -&gt; [1, 2, 3]
   * </pre>
   * 
   * Getting external keys:
   * 
   * <pre>
   * sort(x, sp.by(w*).get(k*))
   * -&gt; [x, y, z]
   * 
   * sort(x, sp.by(w*).get(#).get(k*))
   * -&gt; [3, x, 2, y, 1, z]
   * </pre>
   * @see #sort(byte[])
   * @see #sort(byte[], SortingParams, byte[])
   * @param key
   * @param sortingParameters
   * @return a list of sorted elements.
   */
  @Override
  public List<byte[]> sort(final byte[] key, final SortingParams sortingParameters) {
    checkIsInMultiOrPipeline();
    client.sort(key, sortingParameters);
    return client.getBinaryMultiBulkReply();
  }

  /**
   * BLPOP (and BRPOP) is a blocking list pop primitive. You can see this commands as blocking
   * versions of LPOP and RPOP able to block if the specified keys don't exist or contain empty
   * lists.
   * <p>
   * The following is a description of the exact semantic. We describe BLPOP but the two commands
   * are identical, the only difference is that BLPOP pops the element from the left (head) of the
   * list, and BRPOP pops from the right (tail).
   * <p>
   * <b>Non blocking behavior</b>
   * <p>
   * When BLPOP is called, if at least one of the specified keys contain a non empty list, an
   * element is popped from the head of the list and returned to the caller together with the name
   * of the key (BLPOP returns a two elements array, the first element is the key, the second the
   * popped value).
   * <p>
   * Keys are scanned from left to right, so for instance if you issue BLPOP list1 list2 list3 0
   * against a dataset where list1 does not exist but list2 and list3 contain non empty lists, BLPOP
   * guarantees to return an element from the list stored at list2 (since it is the first non empty
   * list starting from the left).
   * <p>
   * <b>Blocking behavior</b>
   * <p>
   * If none of the specified keys exist or contain non empty lists, BLPOP blocks until some other
   * client performs a LPUSH or an RPUSH operation against one of the lists.
   * <p>
   * Once new data is present on one of the lists, the client finally returns with the name of the
   * key unblocking it and the popped value.
   * <p>
   * When blocking, if a non-zero timeout is specified, the client will unblock returning a nil
   * special value if the specified amount of seconds passed without a push operation against at
   * least one of the specified keys.
   * <p>
   * The timeout argument is interpreted as an integer value. A timeout of zero means instead to
   * block forever.
   * <p>
   * <b>Multiple clients blocking for the same keys</b>
   * <p>
   * Multiple clients can block for the same key. They are put into a queue, so the first to be
   * served will be the one that started to wait earlier, in a first-blpopping first-served fashion.
   * <p>
   * <b>blocking POP inside a MULTI/EXEC transaction</b>
   * <p>
   * BLPOP and BRPOP can be used with pipelining (sending multiple commands and reading the replies
   * in batch), but it does not make sense to use BLPOP or BRPOP inside a MULTI/EXEC block (a Redis
   * transaction).
   * <p>
   * The behavior of BLPOP inside MULTI/EXEC when the list is empty is to return a multi-bulk nil
   * reply, exactly what happens when the timeout is reached. If you like science fiction, think at
   * it like if inside MULTI/EXEC the time will flow at infinite speed :)
   * <p>
   * Time complexity: O(1)
   * @see #brpop(int, byte[]...)
   * @param timeout
   * @param keys
   * @return BLPOP returns a two-elements array via a multi bulk reply in order to return both the
   *         unblocking key and the popped value.
   *         <p>
   *         When a non-zero timeout is specified, and the BLPOP operation timed out, the return
   *         value is a nil multi bulk reply. Most client values will return false or nil
   *         accordingly to the programming language used.
   */
  @Override
  public List<byte[]> blpop(final int timeout, final byte[]... keys) {
    return blpop(getArgsAddTimeout(timeout, keys));
  }

  private byte[][] getArgsAddTimeout(int timeout, byte[][] keys) {
    int size = keys.length;
    final byte[][] args = new byte[size + 1][];
    for (int at = 0; at != size; ++at) {
      args[at] = keys[at];
    }
    args[size] = Protocol.toByteArray(timeout);
    return args;
  }

  /**
   * Sort a Set or a List accordingly to the specified parameters and store the result at dstkey.
   * @see #sort(byte[], SortingParams)
   * @see #sort(byte[])
   * @see #sort(byte[], byte[])
   * @param key
   * @param sortingParameters
   * @param dstkey
   * @return The number of elements of the list at dstkey.
   */
  @Override
  public Long sort(final byte[] key, final SortingParams sortingParameters, final byte[] dstkey) {
    checkIsInMultiOrPipeline();
    client.sort(key, sortingParameters, dstkey);
    return client.getIntegerReply();
  }

  /**
   * Sort a Set or a List and Store the Result at dstkey.
   * <p>
   * Sort the elements contained in the List, Set, or Sorted Set value at key and store the result
   * at dstkey. By default sorting is numeric with elements being compared as double precision
   * floating point numbers. This is the simplest form of SORT.
   * @see #sort(byte[])
   * @see #sort(byte[], SortingParams)
   * @see #sort(byte[], SortingParams, byte[])
   * @param key
   * @param dstkey
   * @return The number of elements of the list at dstkey.
   */
  @Override
  public Long sort(final byte[] key, final byte[] dstkey) {
    checkIsInMultiOrPipeline();
    client.sort(key, dstkey);
    return client.getIntegerReply();
  }

  /**
   * BLPOP (and BRPOP) is a blocking list pop primitive. You can see this commands as blocking
   * versions of LPOP and RPOP able to block if the specified keys don't exist or contain empty
   * lists.
   * <p>
   * The following is a description of the exact semantic. We describe BLPOP but the two commands
   * are identical, the only difference is that BLPOP pops the element from the left (head) of the
   * list, and BRPOP pops from the right (tail).
   * <p>
   * <b>Non blocking behavior</b>
   * <p>
   * When BLPOP is called, if at least one of the specified keys contain a non empty list, an
   * element is popped from the head of the list and returned to the caller together with the name
   * of the key (BLPOP returns a two elements array, the first element is the key, the second the
   * popped value).
   * <p>
   * Keys are scanned from left to right, so for instance if you issue BLPOP list1 list2 list3 0
   * against a dataset where list1 does not exist but list2 and list3 contain non empty lists, BLPOP
   * guarantees to return an element from the list stored at list2 (since it is the first non empty
   * list starting from the left).
   * <p>
   * <b>Blocking behavior</b>
   * <p>
   * If none of the specified keys exist or contain non empty lists, BLPOP blocks until some other
   * client performs a LPUSH or an RPUSH operation against one of the lists.
   * <p>
   * Once new data is present on one of the lists, the client finally returns with the name of the
   * key unblocking it and the popped value.
   * <p>
   * When blocking, if a non-zero timeout is specified, the client will unblock returning a nil
   * special value if the specified amount of seconds passed without a push operation against at
   * least one of the specified keys.
   * <p>
   * The timeout argument is interpreted as an integer value. A timeout of zero means instead to
   * block forever.
   * <p>
   * <b>Multiple clients blocking for the same keys</b>
   * <p>
   * Multiple clients can block for the same key. They are put into a queue, so the first to be
   * served will be the one that started to wait earlier, in a first-blpopping first-served fashion.
   * <p>
   * <b>blocking POP inside a MULTI/EXEC transaction</b>
   * <p>
   * BLPOP and BRPOP can be used with pipelining (sending multiple commands and reading the replies
   * in batch), but it does not make sense to use BLPOP or BRPOP inside a MULTI/EXEC block (a Redis
   * transaction).
   * <p>
   * The behavior of BLPOP inside MULTI/EXEC when the list is empty is to return a multi-bulk nil
   * reply, exactly what happens when the timeout is reached. If you like science fiction, think at
   * it like if inside MULTI/EXEC the time will flow at infinite speed :)
   * <p>
   * Time complexity: O(1)
   * @see #blpop(int, byte[]...)
   * @param timeout
   * @param keys
   * @return BLPOP returns a two-elements array via a multi bulk reply in order to return both the
   *         unblocking key and the popped value.
   *         <p>
   *         When a non-zero timeout is specified, and the BLPOP operation timed out, the return
   *         value is a nil multi bulk reply. Most client values will return false or nil
   *         accordingly to the programming language used.
   */
  @Override
  public List<byte[]> brpop(final int timeout, final byte[]... keys) {
    return brpop(getArgsAddTimeout(timeout, keys));
  }

  @Override
  public List<byte[]> blpop(byte[]... args) {
    checkIsInMultiOrPipeline();
    client.blpop(args);
    client.setTimeoutInfinite();
    try {
      return client.getBinaryMultiBulkReply();
    } finally {
      client.rollbackTimeout();
    }
  }

  @Override
  public List<byte[]> brpop(byte[]... args) {
    checkIsInMultiOrPipeline();
    client.brpop(args);
    client.setTimeoutInfinite();
    try {
      return client.getBinaryMultiBulkReply();
    } finally {
      client.rollbackTimeout();
    }
  }

  /**
   * Request for authentication in a password protected Redis server. A Redis server can be
   * instructed to require a password before to allow clients to issue commands. This is done using
   * the requirepass directive in the Redis configuration file. If the password given by the client
   * is correct the server replies with an OK status code reply and starts accepting commands from
   * the client. Otherwise an error is returned and the clients needs to try a new password. Note
   * that for the high performance nature of Redis it is possible to try a lot of passwords in
   * parallel in very short time, so make sure to generate a strong and very long password so that
   * this attack is infeasible.
   * @param password
   * @return Status code reply
   */
  @Override
  public String auth(final String password) {
    checkIsInMultiOrPipeline();
    client.auth(password);
    return client.getStatusCodeReply();
  }

  public Pipeline pipelined() {
    pipeline = new Pipeline();
    pipeline.setClient(client);
    return pipeline;
  }

  @Override
  public Long zcount(final byte[] key, final double min, final double max) {
    return zcount(key, toByteArray(min), toByteArray(max));
  }

  @Override
  public Long zcount(final byte[] key, final byte[] min, final byte[] max) {
    checkIsInMultiOrPipeline();
    client.zcount(key, min, max);
    return client.getIntegerReply();
  }

  /**
   * Return the all the elements in the sorted set at key with a score between min and max
   * (including elements with score equal to min or max).
   * <p>
   * The elements having the same score are returned sorted lexicographically as ASCII strings (this
   * follows from a property of Redis sorted sets and does not involve further computation).
   * <p>
   * Using the optional {@link #zrangeByScore(byte[], double, double, int, int) LIMIT} it's possible
   * to get only a range of the matching elements in an SQL-alike way. Note that if offset is large
   * the commands needs to traverse the list for offset elements and this adds up to the O(M)
   * figure.
   * <p>
   * The {@link #zcount(byte[], double, double) ZCOUNT} command is similar to
   * {@link #zrangeByScore(byte[], double, double) ZRANGEBYSCORE} but instead of returning the
   * actual elements in the specified interval, it just returns the number of matching elements.
   * <p>
   * <b>Exclusive intervals and infinity</b>
   * <p>
   * min and max can be -inf and +inf, so that you are not required to know what's the greatest or
   * smallest element in order to take, for instance, elements "up to a given value".
   * <p>
   * Also while the interval is for default closed (inclusive) it's possible to specify open
   * intervals prefixing the score with a "(" character, so for instance:
   * <p>
   * {@code ZRANGEBYSCORE zset (1.3 5}
   * <p>
   * Will return all the values with score &gt; 1.3 and &lt;= 5, while for instance:
   * <p>
   * {@code ZRANGEBYSCORE zset (5 (10}
   * <p>
   * Will return all the values with score &gt; 5 and &lt; 10 (5 and 10 excluded).
   * <p>
   * <b>Time complexity:</b>
   * <p>
   * O(log(N))+O(M) with N being the number of elements in the sorted set and M the number of
   * elements returned by the command, so if M is constant (for instance you always ask for the
   * first ten elements with LIMIT) you can consider it O(log(N))
   * @see #zrangeByScore(byte[], double, double)
   * @see #zrangeByScore(byte[], double, double, int, int)
   * @see #zrangeByScoreWithScores(byte[], double, double)
   * @see #zrangeByScoreWithScores(byte[], double, double, int, int)
   * @see #zcount(byte[], double, double)
   * @param key
   * @param min
   * @param max
   * @return Multi bulk reply specifically a list of elements in the specified score range.
   */
  @Override
  public Set<byte[]> zrangeByScore(final byte[] key, final double min, final double max) {
    return zrangeByScore(key, toByteArray(min), toByteArray(max));
  }

  @Override
  public Set<byte[]> zrangeByScore(final byte[] key, final byte[] min, final byte[] max) {
    checkIsInMultiOrPipeline();
    client.zrangeByScore(key, min, max);
    return SetFromList.of(client.getBinaryMultiBulkReply());
  }

  /**
   * Return the all the elements in the sorted set at key with a score between min and max
   * (including elements with score equal to min or max).
   * <p>
   * The elements having the same score are returned sorted lexicographically as ASCII strings (this
   * follows from a property of Redis sorted sets and does not involve further computation).
   * <p>
   * Using the optional {@link #zrangeByScore(byte[], double, double, int, int) LIMIT} it's possible
   * to get only a range of the matching elements in an SQL-alike way. Note that if offset is large
   * the commands needs to traverse the list for offset elements and this adds up to the O(M)
   * figure.
   * <p>
   * The {@link #zcount(byte[], double, double) ZCOUNT} command is similar to
   * {@link #zrangeByScore(byte[], double, double) ZRANGEBYSCORE} but instead of returning the
   * actual elements in the specified interval, it just returns the number of matching elements.
   * <p>
   * <b>Exclusive intervals and infinity</b>
   * <p>
   * min and max can be -inf and +inf, so that you are not required to know what's the greatest or
   * smallest element in order to take, for instance, elements "up to a given value".
   * <p>
   * Also while the interval is for default closed (inclusive) it's possible to specify open
   * intervals prefixing the score with a "(" character, so for instance:
   * <p>
   * {@code ZRANGEBYSCORE zset (1.3 5}
   * <p>
   * Will return all the values with score &gt; 1.3 and &lt;= 5, while for instance:
   * <p>
   * {@code ZRANGEBYSCORE zset (5 (10}
   * <p>
   * Will return all the values with score &gt; 5 and &lt; 10 (5 and 10 excluded).
   * <p>
   * <b>Time complexity:</b>
   * <p>
   * O(log(N))+O(M) with N being the number of elements in the sorted set and M the number of
   * elements returned by the command, so if M is constant (for instance you always ask for the
   * first ten elements with LIMIT) you can consider it O(log(N))
   * @see #zrangeByScore(byte[], double, double)
   * @see #zrangeByScore(byte[], double, double, int, int)
   * @see #zrangeByScoreWithScores(byte[], double, double)
   * @see #zrangeByScoreWithScores(byte[], double, double, int, int)
   * @see #zcount(byte[], double, double)
   * @param key
   * @param min
   * @param max
   * @return Multi bulk reply specifically a list of elements in the specified score range.
   */
  @Override
  public Set<byte[]> zrangeByScore(final byte[] key, final double min, final double max,
      final int offset, final int count) {
    return zrangeByScore(key, toByteArray(min), toByteArray(max), offset, count);
  }

  @Override
  public Set<byte[]> zrangeByScore(final byte[] key, final byte[] min, final byte[] max,
      final int offset, final int count) {
    checkIsInMultiOrPipeline();
    client.zrangeByScore(key, min, max, offset, count);
    return SetFromList.of(client.getBinaryMultiBulkReply());
  }

  /**
   * Return the all the elements in the sorted set at key with a score between min and max
   * (including elements with score equal to min or max).
   * <p>
   * The elements having the same score are returned sorted lexicographically as ASCII strings (this
   * follows from a property of Redis sorted sets and does not involve further computation).
   * <p>
   * Using the optional {@link #zrangeByScore(byte[], double, double, int, int) LIMIT} it's possible
   * to get only a range of the matching elements in an SQL-alike way. Note that if offset is large
   * the commands needs to traverse the list for offset elements and this adds up to the O(M)
   * figure.
   * <p>
   * The {@link #zcount(byte[], double, double) ZCOUNT} command is similar to
   * {@link #zrangeByScore(byte[], double, double) ZRANGEBYSCORE} but instead of returning the
   * actual elements in the specified interval, it just returns the number of matching elements.
   * <p>
   * <b>Exclusive intervals and infinity</b>
   * <p>
   * min and max can be -inf and +inf, so that you are not required to know what's the greatest or
   * smallest element in order to take, for instance, elements "up to a given value".
   * <p>
   * Also while the interval is for default closed (inclusive) it's possible to specify open
   * intervals prefixing the score with a "(" character, so for instance:
   * <p>
   * {@code ZRANGEBYSCORE zset (1.3 5}
   * <p>
   * Will return all the values with score &gt; 1.3 and &lt;= 5, while for instance:
   * <p>
   * {@code ZRANGEBYSCORE zset (5 (10}
   * <p>
   * Will return all the values with score &gt; 5 and &lt; 10 (5 and 10 excluded).
   * <p>
   * <b>Time complexity:</b>
   * <p>
   * O(log(N))+O(M) with N being the number of elements in the sorted set and M the number of
   * elements returned by the command, so if M is constant (for instance you always ask for the
   * first ten elements with LIMIT) you can consider it O(log(N))
   * @see #zrangeByScore(byte[], double, double)
   * @see #zrangeByScore(byte[], double, double, int, int)
   * @see #zrangeByScoreWithScores(byte[], double, double)
   * @see #zrangeByScoreWithScores(byte[], double, double, int, int)
   * @see #zcount(byte[], double, double)
   * @param key
   * @param min
   * @param max
   * @return Multi bulk reply specifically a list of elements in the specified score range.
   */
  @Override
  public Set<Tuple> zrangeByScoreWithScores(final byte[] key, final double min, final double max) {
    return zrangeByScoreWithScores(key, toByteArray(min), toByteArray(max));
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(final byte[] key, final byte[] min, final byte[] max) {
    checkIsInMultiOrPipeline();
    client.zrangeByScoreWithScores(key, min, max);
    return getBinaryTupledSet();
  }

  /**
   * Return the all the elements in the sorted set at key with a score between min and max
   * (including elements with score equal to min or max).
   * <p>
   * The elements having the same score are returned sorted lexicographically as ASCII strings (this
   * follows from a property of Redis sorted sets and does not involve further computation).
   * <p>
   * Using the optional {@link #zrangeByScore(byte[], double, double, int, int) LIMIT} it's possible
   * to get only a range of the matching elements in an SQL-alike way. Note that if offset is large
   * the commands needs to traverse the list for offset elements and this adds up to the O(M)
   * figure.
   * <p>
   * The {@link #zcount(byte[], double, double) ZCOUNT} command is similar to
   * {@link #zrangeByScore(byte[], double, double) ZRANGEBYSCORE} but instead of returning the
   * actual elements in the specified interval, it just returns the number of matching elements.
   * <p>
   * <b>Exclusive intervals and infinity</b>
   * <p>
   * min and max can be -inf and +inf, so that you are not required to know what's the greatest or
   * smallest element in order to take, for instance, elements "up to a given value".
   * <p>
   * Also while the interval is for default closed (inclusive) it's possible to specify open
   * intervals prefixing the score with a "(" character, so for instance:
   * <p>
   * {@code ZRANGEBYSCORE zset (1.3 5}
   * <p>
   * Will return all the values with score &gt; 1.3 and &lt;= 5, while for instance:
   * <p>
   * {@code ZRANGEBYSCORE zset (5 (10}
   * <p>
   * Will return all the values with score &gt; 5 and &lt; 10 (5 and 10 excluded).
   * <p>
   * <b>Time complexity:</b>
   * <p>
   * O(log(N))+O(M) with N being the number of elements in the sorted set and M the number of
   * elements returned by the command, so if M is constant (for instance you always ask for the
   * first ten elements with LIMIT) you can consider it O(log(N))
   * @see #zrangeByScore(byte[], double, double)
   * @see #zrangeByScore(byte[], double, double, int, int)
   * @see #zrangeByScoreWithScores(byte[], double, double)
   * @see #zrangeByScoreWithScores(byte[], double, double, int, int)
   * @see #zcount(byte[], double, double)
   * @param key
   * @param min
   * @param max
   * @return Multi bulk reply specifically a list of elements in the specified score range.
   */
  @Override
  public Set<Tuple> zrangeByScoreWithScores(final byte[] key, final double min, final double max,
      final int offset, final int count) {
    return zrangeByScoreWithScores(key, toByteArray(min), toByteArray(max), offset, count);
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(final byte[] key, final byte[] min, final byte[] max,
      final int offset, final int count) {
    checkIsInMultiOrPipeline();
    client.zrangeByScoreWithScores(key, min, max, offset, count);
    return getBinaryTupledSet();
  }

  private Set<Tuple> getBinaryTupledSet() {
    checkIsInMultiOrPipeline();
    List<byte[]> membersWithScores = client.getBinaryMultiBulkReply();
    if (membersWithScores.size() == 0) {
      return Collections.emptySet();
    }
    Set<Tuple> set = new LinkedHashSet<Tuple>(membersWithScores.size() / 2, 1.0f);
    Iterator<byte[]> iterator = membersWithScores.iterator();
    while (iterator.hasNext()) {
      set.add(new Tuple(iterator.next(), Double.valueOf(SafeEncoder.encode(iterator.next()))));
    }
    return set;
  }

  @Override
  public Set<byte[]> zrevrangeByScore(final byte[] key, final double max, final double min) {
    return zrevrangeByScore(key, toByteArray(max), toByteArray(min));
  }

  @Override
  public Set<byte[]> zrevrangeByScore(final byte[] key, final byte[] max, final byte[] min) {
    checkIsInMultiOrPipeline();
    client.zrevrangeByScore(key, max, min);
    return SetFromList.of(client.getBinaryMultiBulkReply());
  }

  @Override
  public Set<byte[]> zrevrangeByScore(final byte[] key, final double max, final double min,
      final int offset, final int count) {
    return zrevrangeByScore(key, toByteArray(max), toByteArray(min), offset, count);
  }

  @Override
  public Set<byte[]> zrevrangeByScore(final byte[] key, final byte[] max, final byte[] min,
      final int offset, final int count) {
    checkIsInMultiOrPipeline();
    client.zrevrangeByScore(key, max, min, offset, count);
    return SetFromList.of(client.getBinaryMultiBulkReply());
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(final byte[] key, final double max, final double min) {
    return zrevrangeByScoreWithScores(key, toByteArray(max), toByteArray(min));
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(final byte[] key, final double max,
      final double min, final int offset, final int count) {
    return zrevrangeByScoreWithScores(key, toByteArray(max), toByteArray(min), offset, count);
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(final byte[] key, final byte[] max, final byte[] min) {
    checkIsInMultiOrPipeline();
    client.zrevrangeByScoreWithScores(key, max, min);
    return getBinaryTupledSet();
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(final byte[] key, final byte[] max,
      final byte[] min, final int offset, final int count) {
    checkIsInMultiOrPipeline();
    client.zrevrangeByScoreWithScores(key, max, min, offset, count);
    return getBinaryTupledSet();
  }

  /**
   * Remove all elements in the sorted set at key with rank between start and end. Start and end are
   * 0-based with rank 0 being the element with the lowest score. Both start and end can be negative
   * numbers, where they indicate offsets starting at the element with the highest rank. For
   * example: -1 is the element with the highest score, -2 the element with the second highest score
   * and so forth.
   * <p>
   * <b>Time complexity:</b> O(log(N))+O(M) with N being the number of elements in the sorted set
   * and M the number of elements removed by the operation
   */
  @Override
  public Long zremrangeByRank(final byte[] key, final long start, final long end) {
    checkIsInMultiOrPipeline();
    client.zremrangeByRank(key, start, end);
    return client.getIntegerReply();
  }

  /**
   * Remove all the elements in the sorted set at key with a score between min and max (including
   * elements with score equal to min or max).
   * <p>
   * <b>Time complexity:</b>
   * <p>
   * O(log(N))+O(M) with N being the number of elements in the sorted set and M the number of
   * elements removed by the operation
   * @param key
   * @param start
   * @param end
   * @return Integer reply, specifically the number of elements removed.
   */
  @Override
  public Long zremrangeByScore(final byte[] key, final double start, final double end) {
    return zremrangeByScore(key, toByteArray(start), toByteArray(end));
  }

  @Override
  public Long zremrangeByScore(final byte[] key, final byte[] start, final byte[] end) {
    checkIsInMultiOrPipeline();
    client.zremrangeByScore(key, start, end);
    return client.getIntegerReply();
  }

  /**
   * Creates a union or intersection of N sorted sets given by keys k1 through kN, and stores it at
   * dstkey. It is mandatory to provide the number of input keys N, before passing the input keys
   * and the other (optional) arguments.
   * <p>
   * As the terms imply, the {@link #zinterstore(byte[], byte[]...)} ZINTERSTORE} command requires
   * an element to be present in each of the given inputs to be inserted in the result. The {@link
   * #zunionstore(byte[], byte[]...)} command inserts all elements across all inputs.
   * <p>
   * Using the WEIGHTS option, it is possible to add weight to each input sorted set. This means
   * that the score of each element in the sorted set is first multiplied by this weight before
   * being passed to the aggregation. When this option is not given, all weights default to 1.
   * <p>
   * With the AGGREGATE option, it's possible to specify how the results of the union or
   * intersection are aggregated. This option defaults to SUM, where the score of an element is
   * summed across the inputs where it exists. When this option is set to be either MIN or MAX, the
   * resulting set will contain the minimum or maximum score of an element across the inputs where
   * it exists.
   * <p>
   * <b>Time complexity:</b> O(N) + O(M log(M)) with N being the sum of the sizes of the input
   * sorted sets, and M being the number of elements in the resulting sorted set
   * @see #zunionstore(byte[], byte[]...)
   * @see #zunionstore(byte[], ZParams, byte[]...)
   * @see #zinterstore(byte[], byte[]...)
   * @see #zinterstore(byte[], ZParams, byte[]...)
   * @param dstkey
   * @param sets
   * @return Integer reply, specifically the number of elements in the sorted set at dstkey
   */
  @Override
  public Long zunionstore(final byte[] dstkey, final byte[]... sets) {
    checkIsInMultiOrPipeline();
    client.zunionstore(dstkey, sets);
    return client.getIntegerReply();
  }

  /**
   * Creates a union or intersection of N sorted sets given by keys k1 through kN, and stores it at
   * dstkey. It is mandatory to provide the number of input keys N, before passing the input keys
   * and the other (optional) arguments.
   * <p>
   * As the terms imply, the {@link #zinterstore(byte[], byte[]...) ZINTERSTORE} command requires an
   * element to be present in each of the given inputs to be inserted in the result. The {@link
   * #zunionstore(byte[], byte[]...) ZUNIONSTORE} command inserts all elements across all inputs.
   * <p>
   * Using the WEIGHTS option, it is possible to add weight to each input sorted set. This means
   * that the score of each element in the sorted set is first multiplied by this weight before
   * being passed to the aggregation. When this option is not given, all weights default to 1.
   * <p>
   * With the AGGREGATE option, it's possible to specify how the results of the union or
   * intersection are aggregated. This option defaults to SUM, where the score of an element is
   * summed across the inputs where it exists. When this option is set to be either MIN or MAX, the
   * resulting set will contain the minimum or maximum score of an element across the inputs where
   * it exists.
   * <p>
   * <b>Time complexity:</b> O(N) + O(M log(M)) with N being the sum of the sizes of the input
   * sorted sets, and M being the number of elements in the resulting sorted set
   * @see #zunionstore(byte[], byte[]...)
   * @see #zunionstore(byte[], ZParams, byte[]...)
   * @see #zinterstore(byte[], byte[]...)
   * @see #zinterstore(byte[], ZParams, byte[]...)
   * @param dstkey
   * @param sets
   * @param params
   * @return Integer reply, specifically the number of elements in the sorted set at dstkey
   */
  @Override
  public Long zunionstore(final byte[] dstkey, final ZParams params, final byte[]... sets) {
    checkIsInMultiOrPipeline();
    client.zunionstore(dstkey, params, sets);
    return client.getIntegerReply();
  }

  /**
   * Creates a union or intersection of N sorted sets given by keys k1 through kN, and stores it at
   * dstkey. It is mandatory to provide the number of input keys N, before passing the input keys
   * and the other (optional) arguments.
   * <p>
   * As the terms imply, the {@link #zinterstore(byte[], byte[]...) ZINTERSTORE} command requires an
   * element to be present in each of the given inputs to be inserted in the result. The {@link
   * #zunionstore(byte[], byte[]...) ZUNIONSTORE} command inserts all elements across all inputs.
   * <p>
   * Using the WEIGHTS option, it is possible to add weight to each input sorted set. This means
   * that the score of each element in the sorted set is first multiplied by this weight before
   * being passed to the aggregation. When this option is not given, all weights default to 1.
   * <p>
   * With the AGGREGATE option, it's possible to specify how the results of the union or
   * intersection are aggregated. This option defaults to SUM, where the score of an element is
   * summed across the inputs where it exists. When this option is set to be either MIN or MAX, the
   * resulting set will contain the minimum or maximum score of an element across the inputs where
   * it exists.
   * <p>
   * <b>Time complexity:</b> O(N) + O(M log(M)) with N being the sum of the sizes of the input
   * sorted sets, and M being the number of elements in the resulting sorted set
   * @see #zunionstore(byte[], byte[]...)
   * @see #zunionstore(byte[], ZParams, byte[]...)
   * @see #zinterstore(byte[], byte[]...)
   * @see #zinterstore(byte[], ZParams, byte[]...)
   * @param dstkey
   * @param sets
   * @return Integer reply, specifically the number of elements in the sorted set at dstkey
   */
  @Override
  public Long zinterstore(final byte[] dstkey, final byte[]... sets) {
    checkIsInMultiOrPipeline();
    client.zinterstore(dstkey, sets);
    return client.getIntegerReply();
  }

  /**
   * Creates a union or intersection of N sorted sets given by keys k1 through kN, and stores it at
   * dstkey. It is mandatory to provide the number of input keys N, before passing the input keys
   * and the other (optional) arguments.
   * <p>
   * As the terms imply, the {@link #zinterstore(byte[], byte[]...) ZINTERSTORE} command requires an
   * element to be present in each of the given inputs to be inserted in the result. The {@link
   * #zunionstore(byte[], byte[]...) ZUNIONSTORE} command inserts all elements across all inputs.
   * <p>
   * Using the WEIGHTS option, it is possible to add weight to each input sorted set. This means
   * that the score of each element in the sorted set is first multiplied by this weight before
   * being passed to the aggregation. When this option is not given, all weights default to 1.
   * <p>
   * With the AGGREGATE option, it's possible to specify how the results of the union or
   * intersection are aggregated. This option defaults to SUM, where the score of an element is
   * summed across the inputs where it exists. When this option is set to be either MIN or MAX, the
   * resulting set will contain the minimum or maximum score of an element across the inputs where
   * it exists.
   * <p>
   * <b>Time complexity:</b> O(N) + O(M log(M)) with N being the sum of the sizes of the input
   * sorted sets, and M being the number of elements in the resulting sorted set
   * @see #zunionstore(byte[], byte[]...)
   * @see #zunionstore(byte[], ZParams, byte[]...)
   * @see #zinterstore(byte[], byte[]...)
   * @see #zinterstore(byte[], ZParams, byte[]...)
   * @param dstkey
   * @param sets
   * @param params
   * @return Integer reply, specifically the number of elements in the sorted set at dstkey
   */
  @Override
  public Long zinterstore(final byte[] dstkey, final ZParams params, final byte[]... sets) {
    checkIsInMultiOrPipeline();
    client.zinterstore(dstkey, params, sets);
    return client.getIntegerReply();
  }

  @Override
  public Long zlexcount(final byte[] key, final byte[] min, final byte[] max) {
    checkIsInMultiOrPipeline();
    client.zlexcount(key, min, max);
    return client.getIntegerReply();
  }

  @Override
  public Set<byte[]> zrangeByLex(final byte[] key, final byte[] min, final byte[] max) {
    checkIsInMultiOrPipeline();
    client.zrangeByLex(key, min, max);
    return SetFromList.of(client.getBinaryMultiBulkReply());
  }

  @Override
  public Set<byte[]> zrangeByLex(final byte[] key, final byte[] min, final byte[] max,
      final int offset, final int count) {
    checkIsInMultiOrPipeline();
    client.zrangeByLex(key, min, max, offset, count);
    return SetFromList.of(client.getBinaryMultiBulkReply());
  }

  @Override
  public Set<byte[]> zrevrangeByLex(byte[] key, byte[] max, byte[] min) {
    checkIsInMultiOrPipeline();
    client.zrevrangeByLex(key, max, min);
    return SetFromList.of(client.getBinaryMultiBulkReply());
  }

  @Override
  public Set<byte[]> zrevrangeByLex(byte[] key, byte[] max, byte[] min, int offset, int count) {
    checkIsInMultiOrPipeline();
    client.zrevrangeByLex(key, max, min, offset, count);
    return SetFromList.of(client.getBinaryMultiBulkReply());
  }

  @Override
  public Long zremrangeByLex(final byte[] key, final byte[] min, final byte[] max) {
    checkIsInMultiOrPipeline();
    client.zremrangeByLex(key, min, max);
    return client.getIntegerReply();
  }

  /**
   * Synchronously save the DB on disk.
   * <p>
   * Save the whole dataset on disk (this means that all the databases are saved, as well as keys
   * with an EXPIRE set (the expire is preserved). The server hangs while the saving is not
   * completed, no connection is served in the meanwhile. An OK code is returned when the DB was
   * fully stored in disk.
   * <p>
   * The background variant of this command is {@link #bgsave() BGSAVE} that is able to perform the
   * saving in the background while the server continues serving other clients.
   * <p>
   * @return Status code reply
   */
  @Override
  public String save() {
    client.save();
    return client.getStatusCodeReply();
  }

  /**
   * Asynchronously save the DB on disk.
   * <p>
   * Save the DB in background. The OK code is immediately returned. Redis forks, the parent
   * continues to server the clients, the child saves the DB on disk then exit. A client my be able
   * to check if the operation succeeded using the LASTSAVE command.
   * @return Status code reply
   */
  @Override
  public String bgsave() {
    client.bgsave();
    return client.getStatusCodeReply();
  }

  /**
   * Rewrite the append only file in background when it gets too big. Please for detailed
   * information about the Redis Append Only File check the <a
   * href="http://redis.io/topics/persistence#append-only-file">Append Only File Howto</a>.
   * <p>
   * BGREWRITEAOF rewrites the Append Only File in background when it gets too big. The Redis Append
   * Only File is a Journal, so every operation modifying the dataset is logged in the Append Only
   * File (and replayed at startup). This means that the Append Only File always grows. In order to
   * rebuild its content the BGREWRITEAOF creates a new version of the append only file starting
   * directly form the dataset in memory in order to guarantee the generation of the minimal number
   * of commands needed to rebuild the database.
   * <p>
   * @return Status code reply
   */
  @Override
  public String bgrewriteaof() {
    client.bgrewriteaof();
    return client.getStatusCodeReply();
  }

  /**
   * Return the UNIX time stamp of the last successfully saving of the dataset on disk.
   * <p>
   * Return the UNIX TIME of the last DB save executed with success. A client may check if a
   * {@link #bgsave() BGSAVE} command succeeded reading the LASTSAVE value, then issuing a BGSAVE
   * command and checking at regular intervals every N seconds if LASTSAVE changed.
   * @return Integer reply, specifically an UNIX time stamp.
   */
  @Override
  public Long lastsave() {
    client.lastsave();
    return client.getIntegerReply();
  }

  /**
   * Synchronously save the DB on disk, then shutdown the server.
   * <p>
   * Stop all the clients, save the DB, then quit the server. This commands makes sure that the DB
   * is switched off without the lost of any data. This is not guaranteed if the client uses simply
   * {@link #save() SAVE} and then {@link #quit() QUIT} because other clients may alter the DB data
   * between the two commands.
   * @return Status code reply on error. On success nothing is returned since the server quits and
   *         the connection is closed.
   */
  @Override
  public String shutdown() {
    client.shutdown();
    String status;
    try {
      status = client.getStatusCodeReply();
    } catch (JedisException ex) {
      status = null;
    }
    return status;
  }

  /**
   * Provide information and statistics about the server.
   * <p>
   * The info command returns different information and statistics about the server in an format
   * that's simple to parse by computers and easy to read by humans.
   * <p>
   * <b>Format of the returned String:</b>
   * <p>
   * All the fields are in the form field:value
   * 
   * <pre>
   * edis_version:0.07
   * connected_clients:1
   * connected_slaves:0
   * used_memory:3187
   * changes_since_last_save:0
   * last_save_time:1237655729
   * total_connections_received:1
   * total_commands_processed:1
   * uptime_in_seconds:25
   * uptime_in_days:0
   * </pre>
   * 
   * <b>Notes</b>
   * <p>
   * used_memory is returned in bytes, and is the total number of bytes allocated by the program
   * using malloc.
   * <p>
   * uptime_in_days is redundant since the uptime in seconds contains already the full uptime
   * information, this field is only mainly present for humans.
   * <p>
   * changes_since_last_save does not refer to the number of key changes, but to the number of
   * operations that produced some kind of change in the dataset.
   * <p>
   * @return Bulk reply
   */
  @Override
  public String info() {
    client.info();
    return client.getBulkReply();
  }

  @Override
  public String info(final String section) {
    client.info(section);
    return client.getBulkReply();
  }

  /**
   * Dump all the received requests in real time.
   * <p>
   * MONITOR is a debugging command that outputs the whole sequence of commands received by the
   * Redis server. is very handy in order to understand what is happening into the database. This
   * command is used directly via telnet.
   * @param jedisMonitor
   */
  public void monitor(final JedisMonitor jedisMonitor) {
    client.monitor();
    client.getStatusCodeReply();
    jedisMonitor.proceed(client);
  }

  /**
   * Change the replication settings.
   * <p>
   * The SLAVEOF command can change the replication settings of a slave on the fly. If a Redis
   * server is arleady acting as slave, the command SLAVEOF NO ONE will turn off the replicaiton
   * turning the Redis server into a MASTER. In the proper form SLAVEOF hostname port will make the
   * server a slave of the specific server listening at the specified hostname and port.
   * <p>
   * If a server is already a slave of some master, SLAVEOF hostname port will stop the replication
   * against the old server and start the synchrnonization against the new one discarding the old
   * dataset.
   * <p>
   * The form SLAVEOF no one will stop replication turning the server into a MASTER but will not
   * discard the replication. So if the old master stop working it is possible to turn the slave
   * into a master and set the application to use the new master in read/write. Later when the other
   * Redis server will be fixed it can be configured in order to work as slave.
   * <p>
   * @param host
   * @param port
   * @return Status code reply
   */
  @Override
  public String slaveof(final String host, final int port) {
    client.slaveof(host, port);
    return client.getStatusCodeReply();
  }

  @Override
  public String slaveofNoOne() {
    client.slaveofNoOne();
    return client.getStatusCodeReply();
  }

  /**
   * Retrieve the configuration of a running Redis server. Not all the configuration parameters are
   * supported.
   * <p>
   * CONFIG GET returns the current configuration parameters. This sub command only accepts a single
   * argument, that is glob style pattern. All the configuration parameters matching this parameter
   * are reported as a list of key-value pairs.
   * <p>
   * <b>Example:</b>
   * 
   * <pre>
   * $ redis-cli config get '*'
   * 1. "dbfilename"
   * 2. "dump.rdb"
   * 3. "requirepass"
   * 4. (nil)
   * 5. "masterauth"
   * 6. (nil)
   * 7. "maxmemory"
   * 8. "0\n"
   * 9. "appendfsync"
   * 10. "everysec"
   * 11. "save"
   * 12. "3600 1 300 100 60 10000"
   * 
   * $ redis-cli config get 'm*'
   * 1. "masterauth"
   * 2. (nil)
   * 3. "maxmemory"
   * 4. "0\n"
   * </pre>
   * @param pattern
   * @return Bulk reply.
   */
  @Override
  public List<byte[]> configGet(final byte[] pattern) {
    client.configGet(pattern);
    return client.getBinaryMultiBulkReply();
  }

  /**
   * Reset the stats returned by INFO
   * @return
   */
  @Override
  public String configResetStat() {
    client.configResetStat();
    return client.getStatusCodeReply();
  }

  /**
   * Alter the configuration of a running Redis server. Not all the configuration parameters are
   * supported.
   * <p>
   * The list of configuration parameters supported by CONFIG SET can be obtained issuing a
   * {@link #configGet(byte[]) CONFIG GET *} command.
   * <p>
   * The configuration set using CONFIG SET is immediately loaded by the Redis server that will
   * start acting as specified starting from the next command.
   * <p>
   * <b>Parameters value format</b>
   * <p>
   * The value of the configuration parameter is the same as the one of the same parameter in the
   * Redis configuration file, with the following exceptions:
   * <p>
   * <ul>
   * <li>The save paramter is a list of space-separated integers. Every pair of integers specify the
   * time and number of changes limit to trigger a save. For instance the command CONFIG SET save
   * "3600 10 60 10000" will configure the server to issue a background saving of the RDB file every
   * 3600 seconds if there are at least 10 changes in the dataset, and every 60 seconds if there are
   * at least 10000 changes. To completely disable automatic snapshots just set the parameter as an
   * empty string.
   * <li>All the integer parameters representing memory are returned and accepted only using bytes
   * as unit.
   * </ul>
   * @param parameter
   * @param value
   * @return Status code reply
   */
  @Override
  public byte[] configSet(final byte[] parameter, final byte[] value) {
    client.configSet(parameter, value);
    return client.getBinaryBulkReply();
  }

  public boolean isConnected() {
    return client.isConnected();
  }

  @Override
  public Long strlen(final byte[] key) {
    client.strlen(key);
    return client.getIntegerReply();
  }

  public void sync() {
    client.sync();
  }

  @Override
  public Long lpushx(final byte[] key, final byte[]... string) {
    client.lpushx(key, string);
    return client.getIntegerReply();
  }

  /**
   * Undo a {@link #expire(byte[], int) expire} at turning the expire key into a normal key.
   * <p>
   * Time complexity: O(1)
   * @param key
   * @return Integer reply, specifically: 1: the key is now persist. 0: the key is not persist (only
   *         happens when key not set).
   */
  @Override
  public Long persist(final byte[] key) {
    client.persist(key);
    return client.getIntegerReply();
  }

  @Override
  public Long rpushx(final byte[] key, final byte[]... string) {
    client.rpushx(key, string);
    return client.getIntegerReply();
  }

  @Override
  public byte[] echo(final byte[] string) {
    client.echo(string);
    return client.getBinaryBulkReply();
  }

  @Override
  public Long linsert(final byte[] key, final LIST_POSITION where, final byte[] pivot,
      final byte[] value) {
    client.linsert(key, where, pivot, value);
    return client.getIntegerReply();
  }

  @Override
  public String debug(final DebugParams params) {
    client.debug(params);
    return client.getStatusCodeReply();
  }

  public Client getClient() {
    return client;
  }

  /**
   * Pop a value from a list, push it to another list and return it; or block until one is available
   * @param source
   * @param destination
   * @param timeout
   * @return the element
   */
  @Override
  public byte[] brpoplpush(byte[] source, byte[] destination, int timeout) {
    client.brpoplpush(source, destination, timeout);
    client.setTimeoutInfinite();
    try {
      return client.getBinaryBulkReply();
    } finally {
      client.rollbackTimeout();
    }
  }

  /**
   * Sets or clears the bit at offset in the string value stored at key
   * @param key
   * @param offset
   * @param value
   * @return
   */
  @Override
  public Boolean setbit(byte[] key, long offset, boolean value) {
    client.setbit(key, offset, value);
    return client.getIntegerReply() == 1;
  }

  @Override
  public Boolean setbit(byte[] key, long offset, byte[] value) {
    client.setbit(key, offset, value);
    return client.getIntegerReply() == 1;
  }

  /**
   * Returns the bit value at offset in the string value stored at key
   * @param key
   * @param offset
   * @return
   */
  @Override
  public Boolean getbit(byte[] key, long offset) {
    client.getbit(key, offset);
    return client.getIntegerReply() == 1;
  }

  public Long bitpos(final byte[] key, final boolean value) {
    return bitpos(key, value, new BitPosParams());
  }

  public Long bitpos(final byte[] key, final boolean value, final BitPosParams params) {
    client.bitpos(key, value, params);
    return client.getIntegerReply();
  }

  @Override
  public Long setrange(byte[] key, long offset, byte[] value) {
    client.setrange(key, offset, value);
    return client.getIntegerReply();
  }

  @Override
  public byte[] getrange(byte[] key, long startOffset, long endOffset) {
    client.getrange(key, startOffset, endOffset);
    return client.getBinaryBulkReply();
  }

  @Override
  public Long publish(byte[] channel, byte[] message) {
    client.publish(channel, message);
    return client.getIntegerReply();
  }

  @Override
  public void subscribe(BinaryJedisPubSub jedisPubSub, byte[]... channels) {
    client.setTimeoutInfinite();
    try {
      jedisPubSub.proceed(client, channels);
    } finally {
      client.rollbackTimeout();
    }
  }

  @Override
  public void psubscribe(BinaryJedisPubSub jedisPubSub, byte[]... patterns) {
    client.setTimeoutInfinite();
    try {
      jedisPubSub.proceedWithPatterns(client, patterns);
    } finally {
      client.rollbackTimeout();
    }
  }

  @Override
  public int getDB() {
    return client.getDB();
  }

  /**
   * Evaluates scripts using the Lua interpreter built into Redis starting from version 2.6.0.
   * <p>
   * @return Script result
   */
  @Override
  public Object eval(byte[] script, List<byte[]> keys, List<byte[]> args) {
    return eval(script, toByteArray(keys.size()), getParamsWithBinary(keys, args));
  }

  protected static byte[][] getParamsWithBinary(List<byte[]> keys, List<byte[]> args) {
    final int keyCount = keys.size();
    final int argCount = args.size();
    byte[][] params = new byte[keyCount + argCount][];

    for (int i = 0; i < keyCount; i++)
      params[i] = keys.get(i);

    for (int i = 0; i < argCount; i++)
      params[keyCount + i] = args.get(i);

    return params;
  }

  @Override
  public Object eval(byte[] script, byte[] keyCount, byte[]... params) {
    client.setTimeoutInfinite();
    try {
      client.eval(script, keyCount, params);
      return client.getOne();
    } finally {
      client.rollbackTimeout();
    }
  }

  @Override
  public Object eval(byte[] script, int keyCount, byte[]... params) {
    return eval(script, toByteArray(keyCount), params);
  }

  @Override
  public Object eval(byte[] script) {
    return eval(script, 0);
  }

  @Override
  public Object evalsha(byte[] sha1) {
    return evalsha(sha1, 1);
  }

  @Override
  public Object evalsha(byte[] sha1, List<byte[]> keys, List<byte[]> args) {
    return evalsha(sha1, keys.size(), getParamsWithBinary(keys, args));
  }

  @Override
  public Object evalsha(byte[] sha1, int keyCount, byte[]... params) {
    client.setTimeoutInfinite();
    try {
      client.evalsha(sha1, keyCount, params);
      return client.getOne();
    } finally {
      client.rollbackTimeout();
    }
  }

  @Override
  public String scriptFlush() {
    client.scriptFlush();
    return client.getStatusCodeReply();
  }

  public Long scriptExists(byte[] sha1) {
    byte[][] a = new byte[1][];
    a[0] = sha1;
    return scriptExists(a).get(0);
  }

  @Override
  public List<Long> scriptExists(byte[]... sha1) {
    client.scriptExists(sha1);
    return client.getIntegerMultiBulkReply();
  }

  @Override
  public byte[] scriptLoad(byte[] script) {
    client.scriptLoad(script);
    return client.getBinaryBulkReply();
  }

  @Override
  public String scriptKill() {
    client.scriptKill();
    return client.getStatusCodeReply();
  }

  @Override
  public String slowlogReset() {
    client.slowlogReset();
    return client.getBulkReply();
  }

  @Override
  public Long slowlogLen() {
    client.slowlogLen();
    return client.getIntegerReply();
  }

  @Override
  public List<byte[]> slowlogGetBinary() {
    client.slowlogGet();
    return client.getBinaryMultiBulkReply();
  }

  @Override
  public List<byte[]> slowlogGetBinary(long entries) {
    client.slowlogGet(entries);
    return client.getBinaryMultiBulkReply();
  }

  @Override
  public Long objectRefcount(byte[] key) {
    client.objectRefcount(key);
    return client.getIntegerReply();
  }

  @Override
  public byte[] objectEncoding(byte[] key) {
    client.objectEncoding(key);
    return client.getBinaryBulkReply();
  }

  @Override
  public Long objectIdletime(byte[] key) {
    client.objectIdletime(key);
    return client.getIntegerReply();
  }

  @Override
  public Long bitcount(final byte[] key) {
    client.bitcount(key);
    return client.getIntegerReply();
  }

  @Override
  public Long bitcount(final byte[] key, long start, long end) {
    client.bitcount(key, start, end);
    return client.getIntegerReply();
  }

  @Override
  public Long bitop(BitOP op, final byte[] destKey, byte[]... srcKeys) {
    client.bitop(op, destKey, srcKeys);
    return client.getIntegerReply();
  }

  public byte[] dump(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.dump(key);
    return client.getBinaryBulkReply();
  }

  public String restore(final byte[] key, final int ttl, final byte[] serializedValue) {
    checkIsInMultiOrPipeline();
    client.restore(key, ttl, serializedValue);
    return client.getStatusCodeReply();
  }

  @Override
  public Long pexpire(final byte[] key, final long milliseconds) {
    checkIsInMultiOrPipeline();
    client.pexpire(key, milliseconds);
    return client.getIntegerReply();
  }

  @Override
  public Long pexpireAt(final byte[] key, final long millisecondsTimestamp) {
    checkIsInMultiOrPipeline();
    client.pexpireAt(key, millisecondsTimestamp);
    return client.getIntegerReply();
  }

  public Long pttl(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.pttl(key);
    return client.getIntegerReply();
  }

  /**
   * PSETEX works exactly like {@link #setex(byte[], int, byte[])} with the sole difference that the
   * expire time is specified in milliseconds instead of seconds. Time complexity: O(1)
   * @param key
   * @param milliseconds
   * @param value
   * @return Status code reply
   */
  public String psetex(final byte[] key, final long milliseconds, final byte[] value) {
    checkIsInMultiOrPipeline();
    client.psetex(key, milliseconds, value);
    return client.getStatusCodeReply();
  }

  public String clientKill(final byte[] client) {
    checkIsInMultiOrPipeline();
    this.client.clientKill(client);
    return this.client.getStatusCodeReply();
  }

  public String clientGetname() {
    checkIsInMultiOrPipeline();
    client.clientGetname();
    return client.getBulkReply();
  }

  public String clientList() {
    checkIsInMultiOrPipeline();
    client.clientList();
    return client.getBulkReply();
  }

  public String clientSetname(final byte[] name) {
    checkIsInMultiOrPipeline();
    client.clientSetname(name);
    return client.getBulkReply();
  }

  public List<String> time() {
    checkIsInMultiOrPipeline();
    client.time();
    return client.getMultiBulkReply();
  }

  public String migrate(final byte[] host, final int port, final byte[] key,
      final int destinationDb, final int timeout) {
    checkIsInMultiOrPipeline();
    client.migrate(host, port, key, destinationDb, timeout);
    return client.getStatusCodeReply();
  }

  /**
   * Syncrhonous replication of Redis as described here: http://antirez.com/news/66 Since Java
   * Object class has implemented "wait" method, we cannot use it, so I had to change the name of
   * the method. Sorry :S
   */
  @Override
  public Long waitReplicas(int replicas, long timeout) {
    checkIsInMultiOrPipeline();
    client.waitReplicas(replicas, timeout);
    return client.getIntegerReply();
  }

  @Override
  public Long pfadd(final byte[] key, final byte[]... elements) {
    checkIsInMultiOrPipeline();
    client.pfadd(key, elements);
    return client.getIntegerReply();
  }

  @Override
  public long pfcount(final byte[] key) {
    checkIsInMultiOrPipeline();
    client.pfcount(key);
    return client.getIntegerReply();
  }

  @Override
  public String pfmerge(final byte[] destkey, final byte[]... sourcekeys) {
    checkIsInMultiOrPipeline();
    client.pfmerge(destkey, sourcekeys);
    return client.getStatusCodeReply();
  }

  @Override
  public Long pfcount(byte[]... keys) {
    checkIsInMultiOrPipeline();
    client.pfcount(keys);
    return client.getIntegerReply();
  }

  public ScanResult<byte[]> scan(final byte[] cursor) {
    return scan(cursor, new ScanParams());
  }

  public ScanResult<byte[]> scan(final byte[] cursor, final ScanParams params) {
    checkIsInMultiOrPipeline();
    client.scan(cursor, params);
    List<Object> result = client.getObjectMultiBulkReply();
    byte[] newcursor = (byte[]) result.get(0);
    List<byte[]> rawResults = (List<byte[]>) result.get(1);
    return new ScanResult<byte[]>(newcursor, rawResults);
  }

  public ScanResult<Map.Entry<byte[], byte[]>> hscan(final byte[] key, final byte[] cursor) {
    return hscan(key, cursor, new ScanParams());
  }

  public ScanResult<Map.Entry<byte[], byte[]>> hscan(final byte[] key, final byte[] cursor,
      final ScanParams params) {
    checkIsInMultiOrPipeline();
    client.hscan(key, cursor, params);
    List<Object> result = client.getObjectMultiBulkReply();
    byte[] newcursor = (byte[]) result.get(0);
    List<Map.Entry<byte[], byte[]>> results = new ArrayList<Map.Entry<byte[], byte[]>>();
    List<byte[]> rawResults = (List<byte[]>) result.get(1);
    Iterator<byte[]> iterator = rawResults.iterator();
    while (iterator.hasNext()) {
      results.add(new AbstractMap.SimpleEntry<byte[], byte[]>(iterator.next(), iterator.next()));
    }
    return new ScanResult<Map.Entry<byte[], byte[]>>(newcursor, results);
  }

  public ScanResult<byte[]> sscan(final byte[] key, final byte[] cursor) {
    return sscan(key, cursor, new ScanParams());
  }

  public ScanResult<byte[]> sscan(final byte[] key, final byte[] cursor, final ScanParams params) {
    checkIsInMultiOrPipeline();
    client.sscan(key, cursor, params);
    List<Object> result = client.getObjectMultiBulkReply();
    byte[] newcursor = (byte[]) result.get(0);
    List<byte[]> rawResults = (List<byte[]>) result.get(1);
    return new ScanResult<byte[]>(newcursor, rawResults);
  }

  public ScanResult<Tuple> zscan(final byte[] key, final byte[] cursor) {
    return zscan(key, cursor, new ScanParams());
  }

  public ScanResult<Tuple> zscan(final byte[] key, final byte[] cursor, final ScanParams params) {
    checkIsInMultiOrPipeline();
    client.zscan(key, cursor, params);
    List<Object> result = client.getObjectMultiBulkReply();
    byte[] newcursor = (byte[]) result.get(0);
    List<Tuple> results = new ArrayList<Tuple>();
    List<byte[]> rawResults = (List<byte[]>) result.get(1);
    Iterator<byte[]> iterator = rawResults.iterator();
    while (iterator.hasNext()) {
      results.add(new Tuple(iterator.next(), Double.valueOf(SafeEncoder.encode(iterator.next()))));
    }
    return new ScanResult<Tuple>(newcursor, results);
  }

  /**
   * A decorator to implement Set from List. Assume that given List do not contains duplicated
   * values. The resulting set displays the same ordering, concurrency, and performance
   * characteristics as the backing list. This class should be used only for Redis commands which
   * return Set result.
   * @param <E>
   */
  protected static class SetFromList<E> extends AbstractSet<E> {
    private final List<E> list;

    private SetFromList(List<E> list) {
      if (list == null) {
        throw new NullPointerException("list");
      }
      this.list = list;
    }

    @Override
    public void clear() {
      list.clear();
    }

    @Override
    public int size() {
      return list.size();
    }

    @Override
    public boolean isEmpty() {
      return list.isEmpty();
    }

    @Override
    public boolean contains(Object o) {
      return list.contains(o);
    }

    @Override
    public boolean remove(Object o) {
      return list.remove(o);
    }

    @Override
    public boolean add(E e) {
      return !contains(e) && list.add(e);
    }

    @Override
    public Iterator<E> iterator() {
      return list.iterator();
    }

    @Override
    public Object[] toArray() {
      return list.toArray();
    }

    @Override
    public <T> T[] toArray(T[] a) {
      return list.toArray(a);
    }

    public String toString() {
      return list.toString();
    }

    public int hashCode() {
      return list.hashCode();
    }

    public boolean equals(Object o) {
      if (o == this) {
        return true;
      }

      if (!(o instanceof Set)) {
        return false;
      }

      Collection<?> c = (Collection<?>) o;
      if (c.size() != size()) {
        return false;
      }

      return containsAll(c);
    }

    @Override
    public boolean containsAll(Collection<?> c) {
      return list.containsAll(c);
    }

    @Override
    public boolean removeAll(Collection<?> c) {
      return list.removeAll(c);
    }

    @Override
    public boolean retainAll(Collection<?> c) {
      return list.retainAll(c);
    }

    protected static <E> SetFromList<E> of(List<E> list) {
      return new SetFromList<E>(list);
    }
  }
}


File: src/main/java/redis/clients/jedis/BinaryJedisCluster.java
package redis.clients.jedis;

import redis.clients.jedis.params.set.SetParams;
import redis.clients.util.KeyMergeUtil;
import redis.clients.util.SafeEncoder;

import java.io.Closeable;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.apache.commons.pool2.impl.GenericObjectPoolConfig;

public class BinaryJedisCluster implements BinaryJedisClusterCommands,
    MultiKeyBinaryJedisClusterCommands, JedisClusterBinaryScriptingCommands, Closeable {

  public static final short HASHSLOTS = 16384;
  protected static final int DEFAULT_TIMEOUT = 2000;
  protected static final int DEFAULT_MAX_REDIRECTIONS = 5;

  protected int maxRedirections;

  protected JedisClusterConnectionHandler connectionHandler;

  public BinaryJedisCluster(Set<HostAndPort> nodes, int timeout) {
    this(nodes, timeout, DEFAULT_MAX_REDIRECTIONS, new GenericObjectPoolConfig());
  }

  public BinaryJedisCluster(Set<HostAndPort> nodes) {
    this(nodes, DEFAULT_TIMEOUT);
  }

  public BinaryJedisCluster(Set<HostAndPort> jedisClusterNode, int timeout, int maxRedirections,
      final GenericObjectPoolConfig poolConfig) {
    this.connectionHandler = new JedisSlotBasedConnectionHandler(jedisClusterNode, poolConfig,
        timeout);
    this.maxRedirections = maxRedirections;
  }

  public BinaryJedisCluster(Set<HostAndPort> jedisClusterNode, int connectionTimeout,
      int soTimeout, int maxRedirections, final GenericObjectPoolConfig poolConfig) {
    this.connectionHandler = new JedisSlotBasedConnectionHandler(jedisClusterNode, poolConfig,
        connectionTimeout, soTimeout);
    this.maxRedirections = maxRedirections;
  }

  @Override
  public void close() {
    if (connectionHandler != null) {
      for (JedisPool pool : connectionHandler.getNodes().values()) {
        try {
          if (pool != null) {
            pool.destroy();
          }
        } catch (Exception e) {
          // pass
        }
      }
    }
  }

  public Map<String, JedisPool> getClusterNodes() {
    return connectionHandler.getNodes();
  }

  @Override
  public String set(final byte[] key, final byte[] value) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.set(key, value);
      }
    }.runBinary(key);
  }

  @Override
  public String set(final byte[] key, final byte[] value, final SetParams params) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.set(key, value, params);
      }
    }.runBinary(key);
  }

  @Override
  public byte[] get(final byte[] key) {
    return new JedisClusterCommand<byte[]>(connectionHandler, maxRedirections) {
      @Override
      public byte[] execute(Jedis connection) {
        return connection.get(key);
      }
    }.runBinary(key);
  }

  @Override
  public Boolean exists(final byte[] key) {
    return new JedisClusterCommand<Boolean>(connectionHandler, maxRedirections) {
      @Override
      public Boolean execute(Jedis connection) {
        return connection.exists(key);
      }
    }.runBinary(key);
  }

  @Override
  public Long persist(final byte[] key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.persist(key);
      }
    }.runBinary(key);
  }

  @Override
  public String type(final byte[] key) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.type(key);
      }
    }.runBinary(key);
  }

  @Override
  public Long expire(final byte[] key, final int seconds) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.expire(key, seconds);
      }
    }.runBinary(key);
  }

  @Override
  public Long pexpire(final byte[] key, final long milliseconds) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.pexpire(key, milliseconds);
      }
    }.runBinary(key);
  }

  @Override
  public Long expireAt(final byte[] key, final long unixTime) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.expireAt(key, unixTime);
      }
    }.runBinary(key);
  }

  @Override
  public Long pexpireAt(final byte[] key, final long millisecondsTimestamp) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.pexpire(key, millisecondsTimestamp);
      }
    }.runBinary(key);
  }

  @Override
  public Long ttl(final byte[] key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.ttl(key);
      }
    }.runBinary(key);
  }

  @Override
  public Boolean setbit(final byte[] key, final long offset, final boolean value) {
    return new JedisClusterCommand<Boolean>(connectionHandler, maxRedirections) {
      @Override
      public Boolean execute(Jedis connection) {
        return connection.setbit(key, offset, value);
      }
    }.runBinary(key);
  }

  @Override
  public Boolean setbit(final byte[] key, final long offset, final byte[] value) {
    return new JedisClusterCommand<Boolean>(connectionHandler, maxRedirections) {
      @Override
      public Boolean execute(Jedis connection) {
        return connection.setbit(key, offset, value);
      }
    }.runBinary(key);
  }

  @Override
  public Boolean getbit(final byte[] key, final long offset) {
    return new JedisClusterCommand<Boolean>(connectionHandler, maxRedirections) {
      @Override
      public Boolean execute(Jedis connection) {
        return connection.getbit(key, offset);
      }
    }.runBinary(key);
  }

  @Override
  public Long setrange(final byte[] key, final long offset, final byte[] value) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.setrange(key, offset, value);
      }
    }.runBinary(key);
  }

  @Override
  public byte[] getrange(final byte[] key, final long startOffset, final long endOffset) {
    return new JedisClusterCommand<byte[]>(connectionHandler, maxRedirections) {
      @Override
      public byte[] execute(Jedis connection) {
        return connection.getrange(key, startOffset, endOffset);
      }
    }.runBinary(key);
  }

  @Override
  public byte[] getSet(final byte[] key, final byte[] value) {
    return new JedisClusterCommand<byte[]>(connectionHandler, maxRedirections) {
      @Override
      public byte[] execute(Jedis connection) {
        return connection.getSet(key, value);
      }
    }.runBinary(key);
  }

  @Override
  public Long setnx(final byte[] key, final byte[] value) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.setnx(key, value);
      }
    }.runBinary(key);
  }

  @Override
  public String setex(final byte[] key, final int seconds, final byte[] value) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.setex(key, seconds, value);
      }
    }.runBinary(key);
  }

  @Override
  public Long decrBy(final byte[] key, final long integer) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.decrBy(key, integer);
      }
    }.runBinary(key);
  }

  @Override
  public Long decr(final byte[] key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.decr(key);
      }
    }.runBinary(key);
  }

  @Override
  public Long incrBy(final byte[] key, final long integer) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.incrBy(key, integer);
      }
    }.runBinary(key);
  }

  @Override
  public Double incrByFloat(final byte[] key, final double value) {
    return new JedisClusterCommand<Double>(connectionHandler, maxRedirections) {
      @Override
      public Double execute(Jedis connection) {
        return connection.incrByFloat(key, value);
      }
    }.runBinary(key);
  }

  @Override
  public Long incr(final byte[] key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.incr(key);
      }
    }.runBinary(key);
  }

  @Override
  public Long append(final byte[] key, final byte[] value) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.append(key, value);
      }
    }.runBinary(key);
  }

  @Override
  public byte[] substr(final byte[] key, final int start, final int end) {
    return new JedisClusterCommand<byte[]>(connectionHandler, maxRedirections) {
      @Override
      public byte[] execute(Jedis connection) {
        return connection.substr(key, start, end);
      }
    }.runBinary(key);
  }

  @Override
  public Long hset(final byte[] key, final byte[] field, final byte[] value) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.hset(key, field, value);
      }
    }.runBinary(key);
  }

  @Override
  public byte[] hget(final byte[] key, final byte[] field) {
    return new JedisClusterCommand<byte[]>(connectionHandler, maxRedirections) {
      @Override
      public byte[] execute(Jedis connection) {
        return connection.hget(key, field);
      }
    }.runBinary(key);
  }

  @Override
  public Long hsetnx(final byte[] key, final byte[] field, final byte[] value) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.hsetnx(key, field, value);
      }
    }.runBinary(key);
  }

  @Override
  public String hmset(final byte[] key, final Map<byte[], byte[]> hash) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.hmset(key, hash);
      }
    }.runBinary(key);
  }

  @Override
  public List<byte[]> hmget(final byte[] key, final byte[]... fields) {
    return new JedisClusterCommand<List<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public List<byte[]> execute(Jedis connection) {
        return connection.hmget(key, fields);
      }
    }.runBinary(key);
  }

  @Override
  public Long hincrBy(final byte[] key, final byte[] field, final long value) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.hincrBy(key, field, value);
      }
    }.runBinary(key);
  }

  @Override
  public Double hincrByFloat(final byte[] key, final byte[] field, final double value) {
    return new JedisClusterCommand<Double>(connectionHandler, maxRedirections) {
      @Override
      public Double execute(Jedis connection) {
        return connection.hincrByFloat(key, field, value);
      }
    }.runBinary(key);
  }

  @Override
  public Boolean hexists(final byte[] key, final byte[] field) {
    return new JedisClusterCommand<Boolean>(connectionHandler, maxRedirections) {
      @Override
      public Boolean execute(Jedis connection) {
        return connection.hexists(key, field);
      }
    }.runBinary(key);
  }

  @Override
  public Long hdel(final byte[] key, final byte[]... field) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.hdel(key, field);
      }
    }.runBinary(key);
  }

  @Override
  public Long hlen(final byte[] key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.hlen(key);
      }
    }.runBinary(key);
  }

  @Override
  public Set<byte[]> hkeys(final byte[] key) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.hkeys(key);
      }
    }.runBinary(key);
  }

  @Override
  public Collection<byte[]> hvals(final byte[] key) {
    return new JedisClusterCommand<Collection<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Collection<byte[]> execute(Jedis connection) {
        return connection.hvals(key);
      }
    }.runBinary(key);
  }

  @Override
  public Map<byte[], byte[]> hgetAll(final byte[] key) {
    return new JedisClusterCommand<Map<byte[], byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Map<byte[], byte[]> execute(Jedis connection) {
        return connection.hgetAll(key);
      }
    }.runBinary(key);
  }

  @Override
  public Long rpush(final byte[] key, final byte[]... args) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.rpush(key, args);
      }
    }.runBinary(key);
  }

  @Override
  public Long lpush(final byte[] key, final byte[]... args) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.lpush(key, args);
      }
    }.runBinary(key);
  }

  @Override
  public Long llen(final byte[] key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.llen(key);
      }
    }.runBinary(key);
  }

  @Override
  public List<byte[]> lrange(final byte[] key, final long start, final long end) {
    return new JedisClusterCommand<List<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public List<byte[]> execute(Jedis connection) {
        return connection.lrange(key, start, end);
      }
    }.runBinary(key);
  }

  @Override
  public String ltrim(final byte[] key, final long start, final long end) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.ltrim(key, start, end);
      }
    }.runBinary(key);
  }

  @Override
  public byte[] lindex(final byte[] key, final long index) {
    return new JedisClusterCommand<byte[]>(connectionHandler, maxRedirections) {
      @Override
      public byte[] execute(Jedis connection) {
        return connection.lindex(key, index);
      }
    }.runBinary(key);
  }

  @Override
  public String lset(final byte[] key, final long index, final byte[] value) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.lset(key, index, value);
      }
    }.runBinary(key);
  }

  @Override
  public Long lrem(final byte[] key, final long count, final byte[] value) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.lrem(key, count, value);
      }
    }.runBinary(key);
  }

  @Override
  public byte[] lpop(final byte[] key) {
    return new JedisClusterCommand<byte[]>(connectionHandler, maxRedirections) {
      @Override
      public byte[] execute(Jedis connection) {
        return connection.lpop(key);
      }
    }.runBinary(key);
  }

  @Override
  public byte[] rpop(final byte[] key) {
    return new JedisClusterCommand<byte[]>(connectionHandler, maxRedirections) {
      @Override
      public byte[] execute(Jedis connection) {
        return connection.rpop(key);
      }
    }.runBinary(key);
  }

  @Override
  public Long sadd(final byte[] key, final byte[]... member) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.sadd(key, member);
      }
    }.runBinary(key);
  }

  @Override
  public Set<byte[]> smembers(final byte[] key) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.smembers(key);
      }
    }.runBinary(key);
  }

  @Override
  public Long srem(final byte[] key, final byte[]... member) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.srem(key, member);
      }
    }.runBinary(key);
  }

  @Override
  public byte[] spop(final byte[] key) {
    return new JedisClusterCommand<byte[]>(connectionHandler, maxRedirections) {
      @Override
      public byte[] execute(Jedis connection) {
        return connection.spop(key);
      }
    }.runBinary(key);
  }

  @Override
  public Set<byte[]> spop(final byte[] key, final long count) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.spop(key, count);
      }
    }.runBinary(key);
  }

  @Override
  public Long scard(final byte[] key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.scard(key);
      }
    }.runBinary(key);
  }

  @Override
  public Boolean sismember(final byte[] key, final byte[] member) {
    return new JedisClusterCommand<Boolean>(connectionHandler, maxRedirections) {
      @Override
      public Boolean execute(Jedis connection) {
        return connection.sismember(key, member);
      }
    }.runBinary(key);
  }

  @Override
  public byte[] srandmember(final byte[] key) {
    return new JedisClusterCommand<byte[]>(connectionHandler, maxRedirections) {
      @Override
      public byte[] execute(Jedis connection) {
        return connection.srandmember(key);
      }
    }.runBinary(key);
  }

  @Override
  public Long strlen(final byte[] key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.strlen(key);
      }
    }.runBinary(key);
  }

  @Override
  public Long zadd(final byte[] key, final double score, final byte[] member) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zadd(key, score, member);
      }
    }.runBinary(key);
  }

  @Override
  public Long zadd(final byte[] key, final Map<byte[], Double> scoreMembers) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zadd(key, scoreMembers);
      }
    }.runBinary(key);
  }

  @Override
  public Set<byte[]> zrange(final byte[] key, final long start, final long end) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.zrange(key, start, end);
      }
    }.runBinary(key);
  }

  @Override
  public Long zrem(final byte[] key, final byte[]... member) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zrem(key, member);
      }
    }.runBinary(key);
  }

  @Override
  public Double zincrby(final byte[] key, final double score, final byte[] member) {
    return new JedisClusterCommand<Double>(connectionHandler, maxRedirections) {
      @Override
      public Double execute(Jedis connection) {
        return connection.zincrby(key, score, member);
      }
    }.runBinary(key);
  }

  @Override
  public Long zrank(final byte[] key, final byte[] member) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zrank(key, member);
      }
    }.runBinary(key);
  }

  @Override
  public Long zrevrank(final byte[] key, final byte[] member) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zrevrank(key, member);
      }
    }.runBinary(key);
  }

  @Override
  public Set<byte[]> zrevrange(final byte[] key, final long start, final long end) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.zrevrange(key, start, end);
      }
    }.runBinary(key);
  }

  @Override
  public Set<Tuple> zrangeWithScores(final byte[] key, final long start, final long end) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrangeWithScores(key, start, end);
      }
    }.runBinary(key);
  }

  @Override
  public Set<Tuple> zrevrangeWithScores(final byte[] key, final long start, final long end) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrevrangeWithScores(key, start, end);
      }
    }.runBinary(key);
  }

  @Override
  public Long zcard(final byte[] key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zcard(key);
      }
    }.runBinary(key);
  }

  @Override
  public Double zscore(final byte[] key, final byte[] member) {
    return new JedisClusterCommand<Double>(connectionHandler, maxRedirections) {
      @Override
      public Double execute(Jedis connection) {
        return connection.zscore(key, member);
      }
    }.runBinary(key);
  }

  @Override
  public List<byte[]> sort(final byte[] key) {
    return new JedisClusterCommand<List<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public List<byte[]> execute(Jedis connection) {
        return connection.sort(key);
      }
    }.runBinary(key);
  }

  @Override
  public List<byte[]> sort(final byte[] key, final SortingParams sortingParameters) {
    return new JedisClusterCommand<List<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public List<byte[]> execute(Jedis connection) {
        return connection.sort(key, sortingParameters);
      }
    }.runBinary(key);
  }

  @Override
  public Long zcount(final byte[] key, final double min, final double max) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zcount(key, min, max);
      }
    }.runBinary(key);
  }

  @Override
  public Long zcount(final byte[] key, final byte[] min, final byte[] max) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zcount(key, min, max);
      }
    }.runBinary(key);
  }

  @Override
  public Set<byte[]> zrangeByScore(final byte[] key, final double min, final double max) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.zrangeByScore(key, min, max);
      }
    }.runBinary(key);
  }

  @Override
  public Set<byte[]> zrangeByScore(final byte[] key, final byte[] min, final byte[] max) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.zrangeByScore(key, min, max);
      }
    }.runBinary(key);
  }

  @Override
  public Set<byte[]> zrevrangeByScore(final byte[] key, final double max, final double min) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.zrevrangeByScore(key, max, min);
      }
    }.runBinary(key);
  }

  @Override
  public Set<byte[]> zrangeByScore(final byte[] key, final double min, final double max,
      final int offset, final int count) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.zrangeByScore(key, min, max, offset, count);
      }
    }.runBinary(key);
  }

  @Override
  public Set<byte[]> zrevrangeByScore(final byte[] key, final byte[] max, final byte[] min) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.zrevrangeByScore(key, max, min);
      }
    }.runBinary(key);
  }

  @Override
  public Set<byte[]> zrangeByScore(final byte[] key, final byte[] min, final byte[] max,
      final int offset, final int count) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.zrangeByScore(key, min, max, offset, count);
      }
    }.runBinary(key);
  }

  @Override
  public Set<byte[]> zrevrangeByScore(final byte[] key, final double max, final double min,
      final int offset, final int count) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.zrevrangeByScore(key, max, min, offset, count);
      }
    }.runBinary(key);
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(final byte[] key, final double min, final double max) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrangeByScoreWithScores(key, min, max);
      }
    }.runBinary(key);
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(final byte[] key, final double max, final double min) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrevrangeByScoreWithScores(key, max, min);
      }
    }.runBinary(key);
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(final byte[] key, final double min, final double max,
      final int offset, final int count) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrangeByScoreWithScores(key, min, max, offset, count);
      }
    }.runBinary(key);
  }

  @Override
  public Set<byte[]> zrevrangeByScore(final byte[] key, final byte[] max, final byte[] min,
      final int offset, final int count) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.zrevrangeByScore(key, max, min, offset, count);
      }
    }.runBinary(key);
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(final byte[] key, final byte[] min, final byte[] max) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrangeByScoreWithScores(key, min, max);
      }
    }.runBinary(key);
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(final byte[] key, final byte[] max, final byte[] min) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrevrangeByScoreWithScores(key, max, min);
      }
    }.runBinary(key);
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(final byte[] key, final byte[] min, final byte[] max,
      final int offset, final int count) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrangeByScoreWithScores(key, min, max, offset, count);
      }
    }.runBinary(key);
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(final byte[] key, final double max,
      final double min, final int offset, final int count) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrevrangeByScoreWithScores(key, max, min, offset, count);
      }
    }.runBinary(key);
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(final byte[] key, final byte[] max,
      final byte[] min, final int offset, final int count) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrevrangeByScoreWithScores(key, max, min, offset, count);
      }
    }.runBinary(key);
  }

  @Override
  public Long zremrangeByRank(final byte[] key, final long start, final long end) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zremrangeByRank(key, start, end);
      }
    }.runBinary(key);
  }

  @Override
  public Long zremrangeByScore(final byte[] key, final double start, final double end) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zremrangeByScore(key, start, end);
      }
    }.runBinary(key);
  }

  @Override
  public Long zremrangeByScore(final byte[] key, final byte[] start, final byte[] end) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zremrangeByScore(key, start, end);
      }
    }.runBinary(key);
  }

  @Override
  public Long linsert(final byte[] key, final Client.LIST_POSITION where, final byte[] pivot,
      final byte[] value) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.linsert(key, where, pivot, value);
      }
    }.runBinary(key);
  }

  @Override
  public Long lpushx(final byte[] key, final byte[]... arg) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.lpushx(key, arg);
      }
    }.runBinary(key);
  }

  @Override
  public Long rpushx(final byte[] key, final byte[]... arg) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.rpushx(key, arg);
      }
    }.runBinary(key);
  }

  @Override
  public Long del(final byte[] key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.del(key);
      }
    }.runBinary(key);
  }

  @Override
  public byte[] echo(final byte[] arg) {
    // note that it'll be run from arbitary node
    return new JedisClusterCommand<byte[]>(connectionHandler, maxRedirections) {
      @Override
      public byte[] execute(Jedis connection) {
        return connection.echo(arg);
      }
    }.runBinary(arg);
  }

  @Override
  public Long bitcount(final byte[] key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.bitcount(key);
      }
    }.runBinary(key);
  }

  @Override
  public Long bitcount(final byte[] key, final long start, final long end) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.bitcount(key, start, end);
      }
    }.runBinary(key);
  }

  @Override
  public Long pfadd(final byte[] key, final byte[]... elements) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.pfadd(key, elements);
      }
    }.runBinary(key);
  }

  @Override
  public long pfcount(final byte[] key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.pfcount(key);
      }
    }.runBinary(key);
  }

  @Override
  public List<byte[]> srandmember(final byte[] key, final int count) {
    return new JedisClusterCommand<List<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public List<byte[]> execute(Jedis connection) {
        return connection.srandmember(key, count);
      }
    }.runBinary(key);
  }

  @Override
  public Long zlexcount(final byte[] key, final byte[] min, final byte[] max) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zlexcount(key, min, max);
      }
    }.runBinary(key);
  }

  @Override
  public Set<byte[]> zrangeByLex(final byte[] key, final byte[] min, final byte[] max) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.zrangeByLex(key, min, max);
      }
    }.runBinary(key);
  }

  @Override
  public Set<byte[]> zrangeByLex(final byte[] key, final byte[] min, final byte[] max,
      final int offset, final int count) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.zrangeByLex(key, min, max, offset, count);
      }
    }.runBinary(key);
  }

  @Override
  public Set<byte[]> zrevrangeByLex(final byte[] key, final byte[] max, final byte[] min) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.zrangeByLex(key, max, min);
      }
    }.runBinary(key);
  }

  @Override
  public Set<byte[]> zrevrangeByLex(final byte[] key, final byte[] max, final byte[] min,
      final int offset, final int count) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.zrevrangeByLex(key, max, min, offset, count);
      }
    }.runBinary(key);
  }

  @Override
  public Long zremrangeByLex(final byte[] key, final byte[] min, final byte[] max) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zremrangeByLex(key, min, max);
      }
    }.runBinary(key);
  }

  @Override
  public Object eval(final byte[] script, final byte[] keyCount, final byte[]... params) {
    return new JedisClusterCommand<Object>(connectionHandler, maxRedirections) {
      @Override
      public Object execute(Jedis connection) {
        return connection.eval(script, keyCount, params);
      }
    }.runBinary(Integer.parseInt(SafeEncoder.encode(keyCount)), params);
  }

  @Override
  public Object eval(final byte[] script, final int keyCount, final byte[]... params) {
    return new JedisClusterCommand<Object>(connectionHandler, maxRedirections) {
      @Override
      public Object execute(Jedis connection) {
        return connection.eval(script, keyCount, params);
      }
    }.runBinary(keyCount, params);
  }

  @Override
  public Object eval(final byte[] script, final List<byte[]> keys, final List<byte[]> args) {
    return new JedisClusterCommand<Object>(connectionHandler, maxRedirections) {
      @Override
      public Object execute(Jedis connection) {
        return connection.eval(script, keys, args);
      }
    }.runBinary(keys.size(), keys.toArray(new byte[keys.size()][]));
  }

  @Override
  public Object eval(final byte[] script, byte[] key) {
    return new JedisClusterCommand<Object>(connectionHandler, maxRedirections) {
      @Override
      public Object execute(Jedis connection) {
        return connection.eval(script);
      }
    }.runBinary(key);
  }

  @Override
  public Object evalsha(final byte[] script, byte[] key) {
    return new JedisClusterCommand<Object>(connectionHandler, maxRedirections) {
      @Override
      public Object execute(Jedis connection) {
        return connection.evalsha(script);
      }
    }.runBinary(key);
  }

  @Override
  public Object evalsha(final byte[] sha1, final List<byte[]> keys, final List<byte[]> args) {
    return new JedisClusterCommand<Object>(connectionHandler, maxRedirections) {
      @Override
      public Object execute(Jedis connection) {
        return connection.evalsha(sha1, keys, args);
      }
    }.runBinary(keys.size(), keys.toArray(new byte[keys.size()][]));
  }

  @Override
  public Object evalsha(final byte[] sha1, final int keyCount, final byte[]... params) {
    return new JedisClusterCommand<Object>(connectionHandler, maxRedirections) {
      @Override
      public Object execute(Jedis connection) {
        return connection.evalsha(sha1, keyCount, params);
      }
    }.runBinary(keyCount, params);
  }

  @Override
  public List<Long> scriptExists(final byte[] key, final byte[][] sha1) {
    return new JedisClusterCommand<List<Long>>(connectionHandler, maxRedirections) {
      @Override
      public List<Long> execute(Jedis connection) {
        return connection.scriptExists(sha1);
      }
    }.runBinary(key);
  }

  @Override
  public byte[] scriptLoad(final byte[] script, final byte[] key) {
    return new JedisClusterCommand<byte[]>(connectionHandler, maxRedirections) {
      @Override
      public byte[] execute(Jedis connection) {
        return connection.scriptLoad(script);
      }
    }.runBinary(key);
  }

  @Override
  public String scriptFlush(final byte[] key) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.scriptFlush();
      }
    }.runBinary(key);
  }

  @Override
  public String scriptKill(byte[] key) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.scriptKill();
      }
    }.runBinary(key);
  }

  @Override
  public Long del(final byte[]... keys) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.del(keys);
      }
    }.runBinary(keys.length, keys);
  }

  @Override
  public List<byte[]> blpop(final int timeout, final byte[]... keys) {
    return new JedisClusterCommand<List<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public List<byte[]> execute(Jedis connection) {
        return connection.blpop(timeout, keys);
      }
    }.runBinary(keys.length, keys);
  }

  @Override
  public List<byte[]> brpop(final int timeout, final byte[]... keys) {
    return new JedisClusterCommand<List<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public List<byte[]> execute(Jedis connection) {
        return connection.brpop(timeout, keys);
      }
    }.runBinary(keys.length, keys);
  }

  @Override
  public List<byte[]> mget(final byte[]... keys) {
    return new JedisClusterCommand<List<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public List<byte[]> execute(Jedis connection) {
        return connection.mget(keys);
      }
    }.runBinary(keys.length, keys);
  }

  @Override
  public String mset(final byte[]... keysvalues) {
    byte[][] keys = new byte[keysvalues.length / 2][];

    for (int keyIdx = 0; keyIdx < keys.length; keyIdx++) {
      keys[keyIdx] = keysvalues[keyIdx * 2];
    }

    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.mset(keysvalues);
      }
    }.runBinary(keys.length, keys);
  }

  @Override
  public Long msetnx(final byte[]... keysvalues) {
    byte[][] keys = new byte[keysvalues.length / 2][];

    for (int keyIdx = 0; keyIdx < keys.length; keyIdx++) {
      keys[keyIdx] = keysvalues[keyIdx * 2];
    }

    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.msetnx(keysvalues);
      }
    }.runBinary(keys.length, keys);
  }

  @Override
  public String rename(final byte[] oldkey, final byte[] newkey) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.rename(oldkey, newkey);
      }
    }.runBinary(2, oldkey, newkey);
  }

  @Override
  public Long renamenx(final byte[] oldkey, final byte[] newkey) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.renamenx(oldkey, newkey);
      }
    }.runBinary(2, oldkey, newkey);
  }

  @Override
  public byte[] rpoplpush(final byte[] srckey, final byte[] dstkey) {
    return new JedisClusterCommand<byte[]>(connectionHandler, maxRedirections) {
      @Override
      public byte[] execute(Jedis connection) {
        return connection.rpoplpush(srckey, dstkey);
      }
    }.runBinary(2, srckey, dstkey);
  }

  @Override
  public Set<byte[]> sdiff(final byte[]... keys) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.sdiff(keys);
      }
    }.runBinary(keys.length, keys);
  }

  @Override
  public Long sdiffstore(final byte[] dstkey, final byte[]... keys) {
    byte[][] wholeKeys = KeyMergeUtil.merge(dstkey, keys);

    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.sdiffstore(dstkey, keys);
      }
    }.runBinary(wholeKeys.length, wholeKeys);
  }

  @Override
  public Set<byte[]> sinter(final byte[]... keys) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.sinter(keys);
      }
    }.runBinary(keys.length, keys);
  }

  @Override
  public Long sinterstore(final byte[] dstkey, final byte[]... keys) {
    byte[][] wholeKeys = KeyMergeUtil.merge(dstkey, keys);

    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.sinterstore(dstkey, keys);
      }
    }.runBinary(wholeKeys.length, wholeKeys);
  }

  @Override
  public Long smove(final byte[] srckey, final byte[] dstkey, final byte[] member) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.smove(srckey, dstkey, member);
      }
    }.runBinary(2, srckey, dstkey);
  }

  @Override
  public Long sort(final byte[] key, final SortingParams sortingParameters, final byte[] dstkey) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.sort(key, sortingParameters, dstkey);
      }
    }.runBinary(2, key, dstkey);
  }

  @Override
  public Long sort(final byte[] key, final byte[] dstkey) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.sort(key, dstkey);
      }
    }.runBinary(2, key, dstkey);
  }

  @Override
  public Set<byte[]> sunion(final byte[]... keys) {
    return new JedisClusterCommand<Set<byte[]>>(connectionHandler, maxRedirections) {
      @Override
      public Set<byte[]> execute(Jedis connection) {
        return connection.sunion(keys);
      }
    }.runBinary(keys.length, keys);
  }

  @Override
  public Long sunionstore(final byte[] dstkey, final byte[]... keys) {
    byte[][] wholeKeys = KeyMergeUtil.merge(dstkey, keys);

    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.sunionstore(dstkey, keys);
      }
    }.runBinary(wholeKeys.length, wholeKeys);
  }

  @Override
  public Long zinterstore(final byte[] dstkey, final byte[]... sets) {
    byte[][] wholeKeys = KeyMergeUtil.merge(dstkey, sets);

    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zinterstore(dstkey, sets);
      }
    }.runBinary(wholeKeys.length, wholeKeys);
  }

  @Override
  public Long zinterstore(final byte[] dstkey, final ZParams params, final byte[]... sets) {
    byte[][] wholeKeys = KeyMergeUtil.merge(dstkey, sets);

    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zinterstore(dstkey, params, sets);
      }
    }.runBinary(wholeKeys.length, wholeKeys);
  }

  @Override
  public Long zunionstore(final byte[] dstkey, final byte[]... sets) {
    byte[][] wholeKeys = KeyMergeUtil.merge(dstkey, sets);

    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zunionstore(dstkey, sets);
      }
    }.runBinary(wholeKeys.length, wholeKeys);
  }

  @Override
  public Long zunionstore(final byte[] dstkey, final ZParams params, final byte[]... sets) {
    byte[][] wholeKeys = KeyMergeUtil.merge(dstkey, sets);

    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zunionstore(dstkey, params, sets);
      }
    }.runBinary(wholeKeys.length, wholeKeys);
  }

  @Override
  public byte[] brpoplpush(final byte[] source, final byte[] destination, final int timeout) {
    return new JedisClusterCommand<byte[]>(connectionHandler, maxRedirections) {
      @Override
      public byte[] execute(Jedis connection) {
        return connection.brpoplpush(source, destination, timeout);
      }
    }.runBinary(2, source, destination);
  }

  @Override
  public Long publish(final byte[] channel, final byte[] message) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.publish(channel, message);
      }
    }.runWithAnyNode();
  }

  @Override
  public void subscribe(final BinaryJedisPubSub jedisPubSub, final byte[]... channels) {
    new JedisClusterCommand<Integer>(connectionHandler, maxRedirections) {
      @Override
      public Integer execute(Jedis connection) {
        connection.subscribe(jedisPubSub, channels);
        return 0;
      }
    }.runWithAnyNode();
  }

  @Override
  public void psubscribe(final BinaryJedisPubSub jedisPubSub, final byte[]... patterns) {
    new JedisClusterCommand<Integer>(connectionHandler, maxRedirections) {
      @Override
      public Integer execute(Jedis connection) {
        connection.subscribe(jedisPubSub, patterns);
        return 0;
      }
    }.runWithAnyNode();
  }

  @Override
  public Long bitop(final BitOP op, final byte[] destKey, final byte[]... srcKeys) {
    byte[][] wholeKeys = KeyMergeUtil.merge(destKey, srcKeys);

    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.bitop(op, destKey, srcKeys);
      }
    }.runBinary(wholeKeys.length, wholeKeys);
  }

  @Override
  public String pfmerge(final byte[] destkey, final byte[]... sourcekeys) {
    byte[][] wholeKeys = KeyMergeUtil.merge(destkey, sourcekeys);

    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.pfmerge(destkey, sourcekeys);
      }
    }.runBinary(wholeKeys.length, wholeKeys);
  }

  @Override
  public Long pfcount(final byte[]... keys) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.pfcount(keys);
      }
    }.runBinary(keys.length, keys);
  }

}


File: src/main/java/redis/clients/jedis/BinaryShardedJedis.java
package redis.clients.jedis;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

import redis.clients.jedis.BinaryClient.LIST_POSITION;
import redis.clients.jedis.exceptions.JedisConnectionException;
import redis.clients.jedis.params.set.SetParams;
import redis.clients.util.Hashing;
import redis.clients.util.Sharded;

public class BinaryShardedJedis extends Sharded<Jedis, JedisShardInfo> implements
    BinaryJedisCommands {
  public BinaryShardedJedis(List<JedisShardInfo> shards) {
    super(shards);
  }

  public BinaryShardedJedis(List<JedisShardInfo> shards, Hashing algo) {
    super(shards, algo);
  }

  public BinaryShardedJedis(List<JedisShardInfo> shards, Pattern keyTagPattern) {
    super(shards, keyTagPattern);
  }

  public BinaryShardedJedis(List<JedisShardInfo> shards, Hashing algo, Pattern keyTagPattern) {
    super(shards, algo, keyTagPattern);
  }

  public void disconnect() {
    for (Jedis jedis : getAllShards()) {
      try {
        jedis.quit();
      } catch (JedisConnectionException e) {
        // ignore the exception node, so that all other normal nodes can release all connections.
      }
      try {
        jedis.disconnect();
      } catch (JedisConnectionException e) {
        // ignore the exception node, so that all other normal nodes can release all connections.
      }
    }
  }

  protected Jedis create(JedisShardInfo shard) {
    return new Jedis(shard);
  }

  @Override
  public String set(byte[] key, byte[] value) {
    Jedis j = getShard(key);
    return j.set(key, value);
  }

  @Override
  public String set(byte[] key, byte[] value, SetParams params) {
    Jedis j = getShard(key);
    return j.set(key, value, params);
  }

  @Override
  public byte[] get(byte[] key) {
    Jedis j = getShard(key);
    return j.get(key);
  }

  @Override
  public Boolean exists(byte[] key) {
    Jedis j = getShard(key);
    return j.exists(key);
  }

  @Override
  public String type(byte[] key) {
    Jedis j = getShard(key);
    return j.type(key);
  }

  @Override
  public Long expire(byte[] key, int seconds) {
    Jedis j = getShard(key);
    return j.expire(key, seconds);
  }

  @Override
  public Long pexpire(byte[] key, final long milliseconds) {
    Jedis j = getShard(key);
    return j.pexpire(key, milliseconds);
  }

  @Override
  public Long expireAt(byte[] key, long unixTime) {
    Jedis j = getShard(key);
    return j.expireAt(key, unixTime);
  }

  @Override
  public Long pexpireAt(byte[] key, long millisecondsTimestamp) {
    Jedis j = getShard(key);
    return j.pexpireAt(key, millisecondsTimestamp);
  }

  @Override
  public Long ttl(byte[] key) {
    Jedis j = getShard(key);
    return j.ttl(key);
  }

  @Override
  public byte[] getSet(byte[] key, byte[] value) {
    Jedis j = getShard(key);
    return j.getSet(key, value);
  }

  @Override
  public Long setnx(byte[] key, byte[] value) {
    Jedis j = getShard(key);
    return j.setnx(key, value);
  }

  @Override
  public String setex(byte[] key, int seconds, byte[] value) {
    Jedis j = getShard(key);
    return j.setex(key, seconds, value);
  }

  @Override
  public Long decrBy(byte[] key, long integer) {
    Jedis j = getShard(key);
    return j.decrBy(key, integer);
  }

  @Override
  public Long decr(byte[] key) {
    Jedis j = getShard(key);
    return j.decr(key);
  }

  @Override
  public Long del(byte[] key) {
    Jedis j = getShard(key);
    return j.del(key);
  }

  @Override
  public Long incrBy(byte[] key, long integer) {
    Jedis j = getShard(key);
    return j.incrBy(key, integer);
  }

  @Override
  public Double incrByFloat(byte[] key, double integer) {
    Jedis j = getShard(key);
    return j.incrByFloat(key, integer);
  }

  @Override
  public Long incr(byte[] key) {
    Jedis j = getShard(key);
    return j.incr(key);
  }

  @Override
  public Long append(byte[] key, byte[] value) {
    Jedis j = getShard(key);
    return j.append(key, value);
  }

  @Override
  public byte[] substr(byte[] key, int start, int end) {
    Jedis j = getShard(key);
    return j.substr(key, start, end);
  }

  @Override
  public Long hset(byte[] key, byte[] field, byte[] value) {
    Jedis j = getShard(key);
    return j.hset(key, field, value);
  }

  @Override
  public byte[] hget(byte[] key, byte[] field) {
    Jedis j = getShard(key);
    return j.hget(key, field);
  }

  @Override
  public Long hsetnx(byte[] key, byte[] field, byte[] value) {
    Jedis j = getShard(key);
    return j.hsetnx(key, field, value);
  }

  @Override
  public String hmset(byte[] key, Map<byte[], byte[]> hash) {
    Jedis j = getShard(key);
    return j.hmset(key, hash);
  }

  @Override
  public List<byte[]> hmget(byte[] key, byte[]... fields) {
    Jedis j = getShard(key);
    return j.hmget(key, fields);
  }

  @Override
  public Long hincrBy(byte[] key, byte[] field, long value) {
    Jedis j = getShard(key);
    return j.hincrBy(key, field, value);
  }

  @Override
  public Double hincrByFloat(byte[] key, byte[] field, double value) {
    Jedis j = getShard(key);
    return j.hincrByFloat(key, field, value);
  }

  @Override
  public Boolean hexists(byte[] key, byte[] field) {
    Jedis j = getShard(key);
    return j.hexists(key, field);
  }

  @Override
  public Long hdel(byte[] key, byte[]... fields) {
    Jedis j = getShard(key);
    return j.hdel(key, fields);
  }

  @Override
  public Long hlen(byte[] key) {
    Jedis j = getShard(key);
    return j.hlen(key);
  }

  @Override
  public Set<byte[]> hkeys(byte[] key) {
    Jedis j = getShard(key);
    return j.hkeys(key);
  }

  @Override
  public Collection<byte[]> hvals(byte[] key) {
    Jedis j = getShard(key);
    return j.hvals(key);
  }

  @Override
  public Map<byte[], byte[]> hgetAll(byte[] key) {
    Jedis j = getShard(key);
    return j.hgetAll(key);
  }

  @Override
  public Long rpush(byte[] key, byte[]... strings) {
    Jedis j = getShard(key);
    return j.rpush(key, strings);
  }

  @Override
  public Long lpush(byte[] key, byte[]... strings) {
    Jedis j = getShard(key);
    return j.lpush(key, strings);
  }

  @Override
  public Long strlen(final byte[] key) {
    Jedis j = getShard(key);
    return j.strlen(key);
  }

  @Override
  public Long lpushx(byte[] key, byte[]... string) {
    Jedis j = getShard(key);
    return j.lpushx(key, string);
  }

  @Override
  public Long persist(final byte[] key) {
    Jedis j = getShard(key);
    return j.persist(key);
  }

  @Override
  public Long rpushx(byte[] key, byte[]... string) {
    Jedis j = getShard(key);
    return j.rpushx(key, string);
  }

  @Override
  public Long llen(byte[] key) {
    Jedis j = getShard(key);
    return j.llen(key);
  }

  @Override
  public List<byte[]> lrange(byte[] key, long start, long end) {
    Jedis j = getShard(key);
    return j.lrange(key, start, end);
  }

  @Override
  public String ltrim(byte[] key, long start, long end) {
    Jedis j = getShard(key);
    return j.ltrim(key, start, end);
  }

  @Override
  public byte[] lindex(byte[] key, long index) {
    Jedis j = getShard(key);
    return j.lindex(key, index);
  }

  @Override
  public String lset(byte[] key, long index, byte[] value) {
    Jedis j = getShard(key);
    return j.lset(key, index, value);
  }

  @Override
  public Long lrem(byte[] key, long count, byte[] value) {
    Jedis j = getShard(key);
    return j.lrem(key, count, value);
  }

  @Override
  public byte[] lpop(byte[] key) {
    Jedis j = getShard(key);
    return j.lpop(key);
  }

  @Override
  public byte[] rpop(byte[] key) {
    Jedis j = getShard(key);
    return j.rpop(key);
  }

  @Override
  public Long sadd(byte[] key, byte[]... members) {
    Jedis j = getShard(key);
    return j.sadd(key, members);
  }

  @Override
  public Set<byte[]> smembers(byte[] key) {
    Jedis j = getShard(key);
    return j.smembers(key);
  }

  @Override
  public Long srem(byte[] key, byte[]... members) {
    Jedis j = getShard(key);
    return j.srem(key, members);
  }

  @Override
  public byte[] spop(byte[] key) {
    Jedis j = getShard(key);
    return j.spop(key);
  }

  @Override
  public Set<byte[]> spop(byte[] key, long count) {
    Jedis j = getShard(key);
    return j.spop(key, count);
  }

  @Override
  public Long scard(byte[] key) {
    Jedis j = getShard(key);
    return j.scard(key);
  }

  @Override
  public Boolean sismember(byte[] key, byte[] member) {
    Jedis j = getShard(key);
    return j.sismember(key, member);
  }

  @Override
  public byte[] srandmember(byte[] key) {
    Jedis j = getShard(key);
    return j.srandmember(key);
  }

  @Override
  public List srandmember(byte[] key, int count) {
    Jedis j = getShard(key);
    return j.srandmember(key, count);
  }

  @Override
  public Long zadd(byte[] key, double score, byte[] member) {
    Jedis j = getShard(key);
    return j.zadd(key, score, member);
  }

  @Override
  public Long zadd(byte[] key, Map<byte[], Double> scoreMembers) {
    Jedis j = getShard(key);
    return j.zadd(key, scoreMembers);
  }

  @Override
  public Set<byte[]> zrange(byte[] key, long start, long end) {
    Jedis j = getShard(key);
    return j.zrange(key, start, end);
  }

  @Override
  public Long zrem(byte[] key, byte[]... members) {
    Jedis j = getShard(key);
    return j.zrem(key, members);
  }

  @Override
  public Double zincrby(byte[] key, double score, byte[] member) {
    Jedis j = getShard(key);
    return j.zincrby(key, score, member);
  }

  @Override
  public Long zrank(byte[] key, byte[] member) {
    Jedis j = getShard(key);
    return j.zrank(key, member);
  }

  @Override
  public Long zrevrank(byte[] key, byte[] member) {
    Jedis j = getShard(key);
    return j.zrevrank(key, member);
  }

  @Override
  public Set<byte[]> zrevrange(byte[] key, long start, long end) {
    Jedis j = getShard(key);
    return j.zrevrange(key, start, end);
  }

  @Override
  public Set<Tuple> zrangeWithScores(byte[] key, long start, long end) {
    Jedis j = getShard(key);
    return j.zrangeWithScores(key, start, end);
  }

  @Override
  public Set<Tuple> zrevrangeWithScores(byte[] key, long start, long end) {
    Jedis j = getShard(key);
    return j.zrevrangeWithScores(key, start, end);
  }

  @Override
  public Long zcard(byte[] key) {
    Jedis j = getShard(key);
    return j.zcard(key);
  }

  @Override
  public Double zscore(byte[] key, byte[] member) {
    Jedis j = getShard(key);
    return j.zscore(key, member);
  }

  @Override
  public List<byte[]> sort(byte[] key) {
    Jedis j = getShard(key);
    return j.sort(key);
  }

  @Override
  public List<byte[]> sort(byte[] key, SortingParams sortingParameters) {
    Jedis j = getShard(key);
    return j.sort(key, sortingParameters);
  }

  @Override
  public Long zcount(byte[] key, double min, double max) {
    Jedis j = getShard(key);
    return j.zcount(key, min, max);
  }

  @Override
  public Long zcount(byte[] key, byte[] min, byte[] max) {
    Jedis j = getShard(key);
    return j.zcount(key, min, max);
  }

  @Override
  public Set<byte[]> zrangeByScore(byte[] key, double min, double max) {
    Jedis j = getShard(key);
    return j.zrangeByScore(key, min, max);
  }

  @Override
  public Set<byte[]> zrangeByScore(byte[] key, double min, double max, int offset, int count) {
    Jedis j = getShard(key);
    return j.zrangeByScore(key, min, max, offset, count);
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(byte[] key, double min, double max) {
    Jedis j = getShard(key);
    return j.zrangeByScoreWithScores(key, min, max);
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(byte[] key, double min, double max, int offset,
      int count) {
    Jedis j = getShard(key);
    return j.zrangeByScoreWithScores(key, min, max, offset, count);
  }

  @Override
  public Set<byte[]> zrangeByScore(byte[] key, byte[] min, byte[] max) {
    Jedis j = getShard(key);
    return j.zrangeByScore(key, min, max);
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(byte[] key, byte[] min, byte[] max) {
    Jedis j = getShard(key);
    return j.zrangeByScoreWithScores(key, min, max);
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(byte[] key, byte[] min, byte[] max, int offset,
      int count) {
    Jedis j = getShard(key);
    return j.zrangeByScoreWithScores(key, min, max, offset, count);
  }

  @Override
  public Set<byte[]> zrangeByScore(byte[] key, byte[] min, byte[] max, int offset, int count) {
    Jedis j = getShard(key);
    return j.zrangeByScore(key, min, max, offset, count);
  }

  @Override
  public Set<byte[]> zrevrangeByScore(byte[] key, double max, double min) {
    Jedis j = getShard(key);
    return j.zrevrangeByScore(key, max, min);
  }

  @Override
  public Set<byte[]> zrevrangeByScore(byte[] key, double max, double min, int offset, int count) {
    Jedis j = getShard(key);
    return j.zrevrangeByScore(key, max, min, offset, count);
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(byte[] key, double max, double min) {
    Jedis j = getShard(key);
    return j.zrevrangeByScoreWithScores(key, max, min);
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(byte[] key, double max, double min, int offset,
      int count) {
    Jedis j = getShard(key);
    return j.zrevrangeByScoreWithScores(key, max, min, offset, count);
  }

  @Override
  public Set<byte[]> zrevrangeByScore(byte[] key, byte[] max, byte[] min) {
    Jedis j = getShard(key);
    return j.zrevrangeByScore(key, max, min);
  }

  @Override
  public Set<byte[]> zrevrangeByScore(byte[] key, byte[] max, byte[] min, int offset, int count) {
    Jedis j = getShard(key);
    return j.zrevrangeByScore(key, max, min, offset, count);
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(byte[] key, byte[] max, byte[] min) {
    Jedis j = getShard(key);
    return j.zrevrangeByScoreWithScores(key, max, min);
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(byte[] key, byte[] max, byte[] min, int offset,
      int count) {
    Jedis j = getShard(key);
    return j.zrevrangeByScoreWithScores(key, max, min, offset, count);
  }

  @Override
  public Long zremrangeByRank(byte[] key, long start, long end) {
    Jedis j = getShard(key);
    return j.zremrangeByRank(key, start, end);
  }

  @Override
  public Long zremrangeByScore(byte[] key, double start, double end) {
    Jedis j = getShard(key);
    return j.zremrangeByScore(key, start, end);
  }

  @Override
  public Long zremrangeByScore(byte[] key, byte[] start, byte[] end) {
    Jedis j = getShard(key);
    return j.zremrangeByScore(key, start, end);
  }

  @Override
  public Long zlexcount(final byte[] key, final byte[] min, final byte[] max) {
    Jedis j = getShard(key);
    return j.zlexcount(key, min, max);
  }

  @Override
  public Set<byte[]> zrangeByLex(final byte[] key, final byte[] min, final byte[] max) {
    Jedis j = getShard(key);
    return j.zrangeByLex(key, min, max);
  }

  @Override
  public Set<byte[]> zrangeByLex(final byte[] key, final byte[] min, final byte[] max,
      final int offset, final int count) {
    Jedis j = getShard(key);
    return j.zrangeByLex(key, min, max, offset, count);
  }

  @Override
  public Set<byte[]> zrevrangeByLex(byte[] key, byte[] max, byte[] min) {
    Jedis j = getShard(key);
    return j.zrevrangeByLex(key, max, min);
  }

  @Override
  public Set<byte[]> zrevrangeByLex(byte[] key, byte[] max, byte[] min, int offset, int count) {
    Jedis j = getShard(key);
    return j.zrevrangeByLex(key, max, min, offset, count);
  }

  @Override
  public Long zremrangeByLex(final byte[] key, final byte[] min, final byte[] max) {
    Jedis j = getShard(key);
    return j.zremrangeByLex(key, min, max);
  }

  @Override
  public Long linsert(byte[] key, LIST_POSITION where, byte[] pivot, byte[] value) {
    Jedis j = getShard(key);
    return j.linsert(key, where, pivot, value);
  }

  public ShardedJedisPipeline pipelined() {
    ShardedJedisPipeline pipeline = new ShardedJedisPipeline();
    pipeline.setShardedJedis(this);
    return pipeline;
  }

  public Long objectRefcount(byte[] key) {
    Jedis j = getShard(key);
    return j.objectRefcount(key);
  }

  public byte[] objectEncoding(byte[] key) {
    Jedis j = getShard(key);
    return j.objectEncoding(key);
  }

  public Long objectIdletime(byte[] key) {
    Jedis j = getShard(key);
    return j.objectIdletime(key);
  }

  @Override
  public Boolean setbit(byte[] key, long offset, boolean value) {
    Jedis j = getShard(key);
    return j.setbit(key, offset, value);
  }

  @Override
  public Boolean setbit(byte[] key, long offset, byte[] value) {
    Jedis j = getShard(key);
    return j.setbit(key, offset, value);
  }

  @Override
  public Boolean getbit(byte[] key, long offset) {
    Jedis j = getShard(key);
    return j.getbit(key, offset);
  }

  @Override
  public Long setrange(byte[] key, long offset, byte[] value) {
    Jedis j = getShard(key);
    return j.setrange(key, offset, value);
  }

  @Override
  public byte[] getrange(byte[] key, long startOffset, long endOffset) {
    Jedis j = getShard(key);
    return j.getrange(key, startOffset, endOffset);
  }

  @Override
  public Long move(byte[] key, int dbIndex) {
    Jedis j = getShard(key);
    return j.move(key, dbIndex);
  }

  @Override
  public byte[] echo(byte[] arg) {
    Jedis j = getShard(arg);
    return j.echo(arg);
  }

  public List<byte[]> brpop(byte[] arg) {
    Jedis j = getShard(arg);
    return j.brpop(arg);
  }

  public List<byte[]> blpop(byte[] arg) {
    Jedis j = getShard(arg);
    return j.blpop(arg);
  }

  @Override
  public Long bitcount(byte[] key) {
    Jedis j = getShard(key);
    return j.bitcount(key);
  }

  @Override
  public Long bitcount(byte[] key, long start, long end) {
    Jedis j = getShard(key);
    return j.bitcount(key, start, end);
  }

  @Override
  public Long pfadd(final byte[] key, final byte[]... elements) {
    Jedis j = getShard(key);
    return j.pfadd(key, elements);
  }

  @Override
  public long pfcount(final byte[] key) {
    Jedis j = getShard(key);
    return j.pfcount(key);
  }

}


File: src/main/java/redis/clients/jedis/Client.java
package redis.clients.jedis;

import static redis.clients.jedis.Protocol.toByteArray;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;

import redis.clients.jedis.JedisCluster.Reset;
import redis.clients.jedis.params.set.SetParams;
import redis.clients.util.SafeEncoder;

public class Client extends BinaryClient implements Commands {

  public Client() {
    super();
  }

  public Client(final String host) {
    super(host);
  }

  public Client(final String host, final int port) {
    super(host, port);
  }

  @Override
  public void set(final String key, final String value) {
    set(SafeEncoder.encode(key), SafeEncoder.encode(value));
  }

  @Override
  public void set(final String key, final String value, final SetParams params) {
    set(SafeEncoder.encode(key), SafeEncoder.encode(value), params);
  }

  @Override
  public void get(final String key) {
    get(SafeEncoder.encode(key));
  }

  @Override
  public void exists(final String key) {
    exists(SafeEncoder.encode(key));
  }

  @Override
  public void del(final String... keys) {
    final byte[][] bkeys = new byte[keys.length][];
    for (int i = 0; i < keys.length; i++) {
      bkeys[i] = SafeEncoder.encode(keys[i]);
    }
    del(bkeys);
  }

  @Override
  public void type(final String key) {
    type(SafeEncoder.encode(key));
  }

  @Override
  public void keys(final String pattern) {
    keys(SafeEncoder.encode(pattern));
  }

  @Override
  public void rename(final String oldkey, final String newkey) {
    rename(SafeEncoder.encode(oldkey), SafeEncoder.encode(newkey));
  }

  @Override
  public void renamenx(final String oldkey, final String newkey) {
    renamenx(SafeEncoder.encode(oldkey), SafeEncoder.encode(newkey));
  }

  @Override
  public void expire(final String key, final int seconds) {
    expire(SafeEncoder.encode(key), seconds);
  }

  @Override
  public void expireAt(final String key, final long unixTime) {
    expireAt(SafeEncoder.encode(key), unixTime);
  }

  @Override
  public void ttl(final String key) {
    ttl(SafeEncoder.encode(key));
  }

  @Override
  public void move(final String key, final int dbIndex) {
    move(SafeEncoder.encode(key), dbIndex);
  }

  @Override
  public void getSet(final String key, final String value) {
    getSet(SafeEncoder.encode(key), SafeEncoder.encode(value));
  }

  @Override
  public void mget(final String... keys) {
    final byte[][] bkeys = new byte[keys.length][];
    for (int i = 0; i < bkeys.length; i++) {
      bkeys[i] = SafeEncoder.encode(keys[i]);
    }
    mget(bkeys);
  }

  @Override
  public void setnx(final String key, final String value) {
    setnx(SafeEncoder.encode(key), SafeEncoder.encode(value));
  }

  @Override
  public void setex(final String key, final int seconds, final String value) {
    setex(SafeEncoder.encode(key), seconds, SafeEncoder.encode(value));
  }

  @Override
  public void mset(final String... keysvalues) {
    final byte[][] bkeysvalues = new byte[keysvalues.length][];
    for (int i = 0; i < keysvalues.length; i++) {
      bkeysvalues[i] = SafeEncoder.encode(keysvalues[i]);
    }
    mset(bkeysvalues);
  }

  @Override
  public void msetnx(final String... keysvalues) {
    final byte[][] bkeysvalues = new byte[keysvalues.length][];
    for (int i = 0; i < keysvalues.length; i++) {
      bkeysvalues[i] = SafeEncoder.encode(keysvalues[i]);
    }
    msetnx(bkeysvalues);
  }

  @Override
  public void decrBy(final String key, final long integer) {
    decrBy(SafeEncoder.encode(key), integer);
  }

  @Override
  public void decr(final String key) {
    decr(SafeEncoder.encode(key));
  }

  @Override
  public void incrBy(final String key, final long integer) {
    incrBy(SafeEncoder.encode(key), integer);
  }

  @Override
  public void incr(final String key) {
    incr(SafeEncoder.encode(key));
  }

  @Override
  public void append(final String key, final String value) {
    append(SafeEncoder.encode(key), SafeEncoder.encode(value));
  }

  @Override
  public void substr(final String key, final int start, final int end) {
    substr(SafeEncoder.encode(key), start, end);
  }

  @Override
  public void hset(final String key, final String field, final String value) {
    hset(SafeEncoder.encode(key), SafeEncoder.encode(field), SafeEncoder.encode(value));
  }

  @Override
  public void hget(final String key, final String field) {
    hget(SafeEncoder.encode(key), SafeEncoder.encode(field));
  }

  @Override
  public void hsetnx(final String key, final String field, final String value) {
    hsetnx(SafeEncoder.encode(key), SafeEncoder.encode(field), SafeEncoder.encode(value));
  }

  @Override
  public void hmset(final String key, final Map<String, String> hash) {
    final Map<byte[], byte[]> bhash = new HashMap<byte[], byte[]>(hash.size());
    for (final Entry<String, String> entry : hash.entrySet()) {
      bhash.put(SafeEncoder.encode(entry.getKey()), SafeEncoder.encode(entry.getValue()));
    }
    hmset(SafeEncoder.encode(key), bhash);
  }

  @Override
  public void hmget(final String key, final String... fields) {
    final byte[][] bfields = new byte[fields.length][];
    for (int i = 0; i < bfields.length; i++) {
      bfields[i] = SafeEncoder.encode(fields[i]);
    }
    hmget(SafeEncoder.encode(key), bfields);
  }

  @Override
  public void hincrBy(final String key, final String field, final long value) {
    hincrBy(SafeEncoder.encode(key), SafeEncoder.encode(field), value);
  }

  @Override
  public void hexists(final String key, final String field) {
    hexists(SafeEncoder.encode(key), SafeEncoder.encode(field));
  }

  @Override
  public void hdel(final String key, final String... fields) {
    hdel(SafeEncoder.encode(key), SafeEncoder.encodeMany(fields));
  }

  @Override
  public void hlen(final String key) {
    hlen(SafeEncoder.encode(key));
  }

  @Override
  public void hkeys(final String key) {
    hkeys(SafeEncoder.encode(key));
  }

  @Override
  public void hvals(final String key) {
    hvals(SafeEncoder.encode(key));
  }

  @Override
  public void hgetAll(final String key) {
    hgetAll(SafeEncoder.encode(key));
  }

  @Override
  public void rpush(final String key, final String... string) {
    rpush(SafeEncoder.encode(key), SafeEncoder.encodeMany(string));
  }

  @Override
  public void lpush(final String key, final String... string) {
    lpush(SafeEncoder.encode(key), SafeEncoder.encodeMany(string));
  }

  @Override
  public void llen(final String key) {
    llen(SafeEncoder.encode(key));
  }

  @Override
  public void lrange(final String key, final long start, final long end) {
    lrange(SafeEncoder.encode(key), start, end);
  }

  @Override
  public void ltrim(final String key, final long start, final long end) {
    ltrim(SafeEncoder.encode(key), start, end);
  }

  @Override
  public void lindex(final String key, final long index) {
    lindex(SafeEncoder.encode(key), index);
  }

  @Override
  public void lset(final String key, final long index, final String value) {
    lset(SafeEncoder.encode(key), index, SafeEncoder.encode(value));
  }

  @Override
  public void lrem(final String key, long count, final String value) {
    lrem(SafeEncoder.encode(key), count, SafeEncoder.encode(value));
  }

  @Override
  public void lpop(final String key) {
    lpop(SafeEncoder.encode(key));
  }

  @Override
  public void rpop(final String key) {
    rpop(SafeEncoder.encode(key));
  }

  @Override
  public void rpoplpush(final String srckey, final String dstkey) {
    rpoplpush(SafeEncoder.encode(srckey), SafeEncoder.encode(dstkey));
  }

  @Override
  public void sadd(final String key, final String... members) {
    sadd(SafeEncoder.encode(key), SafeEncoder.encodeMany(members));
  }

  @Override
  public void smembers(final String key) {
    smembers(SafeEncoder.encode(key));
  }

  @Override
  public void srem(final String key, final String... members) {
    srem(SafeEncoder.encode(key), SafeEncoder.encodeMany(members));
  }

  @Override
  public void spop(final String key) {
    spop(SafeEncoder.encode(key));
  }

  @Override
  public void spop(final String key, final long count) {
    spop(SafeEncoder.encode(key), count);
  }

  @Override
  public void smove(final String srckey, final String dstkey, final String member) {
    smove(SafeEncoder.encode(srckey), SafeEncoder.encode(dstkey), SafeEncoder.encode(member));
  }

  @Override
  public void scard(final String key) {
    scard(SafeEncoder.encode(key));
  }

  @Override
  public void sismember(final String key, final String member) {
    sismember(SafeEncoder.encode(key), SafeEncoder.encode(member));
  }

  @Override
  public void sinter(final String... keys) {
    final byte[][] bkeys = new byte[keys.length][];
    for (int i = 0; i < bkeys.length; i++) {
      bkeys[i] = SafeEncoder.encode(keys[i]);
    }
    sinter(bkeys);
  }

  @Override
  public void sinterstore(final String dstkey, final String... keys) {
    final byte[][] bkeys = new byte[keys.length][];
    for (int i = 0; i < bkeys.length; i++) {
      bkeys[i] = SafeEncoder.encode(keys[i]);
    }
    sinterstore(SafeEncoder.encode(dstkey), bkeys);
  }

  @Override
  public void sunion(final String... keys) {
    final byte[][] bkeys = new byte[keys.length][];
    for (int i = 0; i < bkeys.length; i++) {
      bkeys[i] = SafeEncoder.encode(keys[i]);
    }
    sunion(bkeys);
  }

  @Override
  public void sunionstore(final String dstkey, final String... keys) {
    final byte[][] bkeys = new byte[keys.length][];
    for (int i = 0; i < bkeys.length; i++) {
      bkeys[i] = SafeEncoder.encode(keys[i]);
    }
    sunionstore(SafeEncoder.encode(dstkey), bkeys);
  }

  @Override
  public void sdiff(final String... keys) {
    final byte[][] bkeys = new byte[keys.length][];
    for (int i = 0; i < bkeys.length; i++) {
      bkeys[i] = SafeEncoder.encode(keys[i]);
    }
    sdiff(bkeys);
  }

  @Override
  public void sdiffstore(final String dstkey, final String... keys) {
    final byte[][] bkeys = new byte[keys.length][];
    for (int i = 0; i < bkeys.length; i++) {
      bkeys[i] = SafeEncoder.encode(keys[i]);
    }
    sdiffstore(SafeEncoder.encode(dstkey), bkeys);
  }

  @Override
  public void srandmember(final String key) {
    srandmember(SafeEncoder.encode(key));
  }

  @Override
  public void zadd(final String key, final double score, final String member) {
    zadd(SafeEncoder.encode(key), score, SafeEncoder.encode(member));
  }

  @Override
  public void zrange(final String key, final long start, final long end) {
    zrange(SafeEncoder.encode(key), start, end);
  }

  @Override
  public void zrem(final String key, final String... members) {
    zrem(SafeEncoder.encode(key), SafeEncoder.encodeMany(members));
  }

  @Override
  public void zincrby(final String key, final double score, final String member) {
    zincrby(SafeEncoder.encode(key), score, SafeEncoder.encode(member));
  }

  @Override
  public void zrank(final String key, final String member) {
    zrank(SafeEncoder.encode(key), SafeEncoder.encode(member));
  }

  @Override
  public void zrevrank(final String key, final String member) {
    zrevrank(SafeEncoder.encode(key), SafeEncoder.encode(member));
  }

  @Override
  public void zrevrange(final String key, final long start, final long end) {
    zrevrange(SafeEncoder.encode(key), start, end);
  }

  @Override
  public void zrangeWithScores(final String key, final long start, final long end) {
    zrangeWithScores(SafeEncoder.encode(key), start, end);
  }

  @Override
  public void zrevrangeWithScores(final String key, final long start, final long end) {
    zrevrangeWithScores(SafeEncoder.encode(key), start, end);
  }

  @Override
  public void zcard(final String key) {
    zcard(SafeEncoder.encode(key));
  }

  @Override
  public void zscore(final String key, final String member) {
    zscore(SafeEncoder.encode(key), SafeEncoder.encode(member));
  }

  @Override
  public void watch(final String... keys) {
    final byte[][] bargs = new byte[keys.length][];
    for (int i = 0; i < bargs.length; i++) {
      bargs[i] = SafeEncoder.encode(keys[i]);
    }
    watch(bargs);
  }

  @Override
  public void sort(final String key) {
    sort(SafeEncoder.encode(key));
  }

  @Override
  public void sort(final String key, final SortingParams sortingParameters) {
    sort(SafeEncoder.encode(key), sortingParameters);
  }

  @Override
  public void blpop(final String[] args) {
    final byte[][] bargs = new byte[args.length][];
    for (int i = 0; i < bargs.length; i++) {
      bargs[i] = SafeEncoder.encode(args[i]);
    }
    blpop(bargs);
  }

  public void blpop(final int timeout, final String... keys) {
    final int size = keys.length + 1;
    List<String> args = new ArrayList<String>(size);
    for (String arg : keys) {
      args.add(arg);
    }
    args.add(String.valueOf(timeout));
    blpop(args.toArray(new String[size]));
  }

  @Override
  public void sort(final String key, final SortingParams sortingParameters, final String dstkey) {
    sort(SafeEncoder.encode(key), sortingParameters, SafeEncoder.encode(dstkey));
  }

  @Override
  public void sort(final String key, final String dstkey) {
    sort(SafeEncoder.encode(key), SafeEncoder.encode(dstkey));
  }

  @Override
  public void brpop(final String[] args) {
    final byte[][] bargs = new byte[args.length][];
    for (int i = 0; i < bargs.length; i++) {
      bargs[i] = SafeEncoder.encode(args[i]);
    }
    brpop(bargs);
  }

  public void brpop(final int timeout, final String... keys) {
    final int size = keys.length + 1;
    List<String> args = new ArrayList<String>(size);
    for (String arg : keys) {
      args.add(arg);
    }
    args.add(String.valueOf(timeout));
    brpop(args.toArray(new String[size]));
  }

  @Override
  public void zcount(final String key, final double min, final double max) {
    zcount(SafeEncoder.encode(key), toByteArray(min), toByteArray(max));
  }

  @Override
  public void zcount(final String key, final String min, final String max) {
    zcount(SafeEncoder.encode(key), SafeEncoder.encode(min), SafeEncoder.encode(max));
  }

  @Override
  public void zrangeByScore(final String key, final double min, final double max) {
    zrangeByScore(SafeEncoder.encode(key), toByteArray(min), toByteArray(max));
  }

  @Override
  public void zrangeByScore(final String key, final String min, final String max) {
    zrangeByScore(SafeEncoder.encode(key), SafeEncoder.encode(min), SafeEncoder.encode(max));
  }

  @Override
  public void zrangeByScore(final String key, final double min, final double max, final int offset,
      int count) {
    zrangeByScore(SafeEncoder.encode(key), toByteArray(min), toByteArray(max), offset, count);
  }

  @Override
  public void zrangeByScoreWithScores(final String key, final double min, final double max) {
    zrangeByScoreWithScores(SafeEncoder.encode(key), toByteArray(min), toByteArray(max));
  }

  @Override
  public void zrangeByScoreWithScores(final String key, final double min, final double max,
      final int offset, final int count) {
    zrangeByScoreWithScores(SafeEncoder.encode(key), toByteArray(min), toByteArray(max), offset,
      count);
  }

  @Override
  public void zrevrangeByScore(final String key, final double max, final double min) {
    zrevrangeByScore(SafeEncoder.encode(key), toByteArray(max), toByteArray(min));
  }

  public void zrangeByScore(final String key, final String min, final String max, final int offset,
      int count) {
    zrangeByScore(SafeEncoder.encode(key), SafeEncoder.encode(min), SafeEncoder.encode(max),
      offset, count);
  }

  @Override
  public void zrangeByScoreWithScores(final String key, final String min, final String max) {
    zrangeByScoreWithScores(SafeEncoder.encode(key), SafeEncoder.encode(min),
      SafeEncoder.encode(max));
  }

  @Override
  public void zrangeByScoreWithScores(final String key, final String min, final String max,
      final int offset, final int count) {
    zrangeByScoreWithScores(SafeEncoder.encode(key), SafeEncoder.encode(min),
      SafeEncoder.encode(max), offset, count);
  }

  @Override
  public void zrevrangeByScore(final String key, final String max, final String min) {
    zrevrangeByScore(SafeEncoder.encode(key), SafeEncoder.encode(max), SafeEncoder.encode(min));
  }

  @Override
  public void zrevrangeByScore(final String key, final double max, final double min,
      final int offset, int count) {
    zrevrangeByScore(SafeEncoder.encode(key), toByteArray(max), toByteArray(min), offset, count);
  }

  public void zrevrangeByScore(final String key, final String max, final String min,
      final int offset, int count) {
    zrevrangeByScore(SafeEncoder.encode(key), SafeEncoder.encode(max), SafeEncoder.encode(min),
      offset, count);
  }

  @Override
  public void zrevrangeByScoreWithScores(final String key, final double max, final double min) {
    zrevrangeByScoreWithScores(SafeEncoder.encode(key), toByteArray(max), toByteArray(min));
  }

  @Override
  public void zrevrangeByScoreWithScores(final String key, final String max, final String min) {
    zrevrangeByScoreWithScores(SafeEncoder.encode(key), SafeEncoder.encode(max),
      SafeEncoder.encode(min));
  }

  @Override
  public void zrevrangeByScoreWithScores(final String key, final double max, final double min,
      final int offset, final int count) {
    zrevrangeByScoreWithScores(SafeEncoder.encode(key), toByteArray(max), toByteArray(min), offset,
      count);
  }

  @Override
  public void zrevrangeByScoreWithScores(final String key, final String max, final String min,
      final int offset, final int count) {
    zrevrangeByScoreWithScores(SafeEncoder.encode(key), SafeEncoder.encode(max),
      SafeEncoder.encode(min), offset, count);
  }

  @Override
  public void zremrangeByRank(final String key, final long start, final long end) {
    zremrangeByRank(SafeEncoder.encode(key), start, end);
  }

  @Override
  public void zremrangeByScore(final String key, final double start, final double end) {
    zremrangeByScore(SafeEncoder.encode(key), toByteArray(start), toByteArray(end));
  }

  @Override
  public void zremrangeByScore(final String key, final String start, final String end) {
    zremrangeByScore(SafeEncoder.encode(key), SafeEncoder.encode(start), SafeEncoder.encode(end));
  }

  @Override
  public void zunionstore(final String dstkey, final String... sets) {
    final byte[][] bsets = new byte[sets.length][];
    for (int i = 0; i < bsets.length; i++) {
      bsets[i] = SafeEncoder.encode(sets[i]);
    }
    zunionstore(SafeEncoder.encode(dstkey), bsets);
  }

  @Override
  public void zunionstore(final String dstkey, final ZParams params, final String... sets) {
    final byte[][] bsets = new byte[sets.length][];
    for (int i = 0; i < bsets.length; i++) {
      bsets[i] = SafeEncoder.encode(sets[i]);
    }
    zunionstore(SafeEncoder.encode(dstkey), params, bsets);
  }

  @Override
  public void zinterstore(final String dstkey, final String... sets) {
    final byte[][] bsets = new byte[sets.length][];
    for (int i = 0; i < bsets.length; i++) {
      bsets[i] = SafeEncoder.encode(sets[i]);
    }
    zinterstore(SafeEncoder.encode(dstkey), bsets);
  }

  @Override
  public void zinterstore(final String dstkey, final ZParams params, final String... sets) {
    final byte[][] bsets = new byte[sets.length][];
    for (int i = 0; i < bsets.length; i++) {
      bsets[i] = SafeEncoder.encode(sets[i]);
    }
    zinterstore(SafeEncoder.encode(dstkey), params, bsets);
  }

  public void zlexcount(final String key, final String min, final String max) {
    zlexcount(SafeEncoder.encode(key), SafeEncoder.encode(min), SafeEncoder.encode(max));
  }

  public void zrangeByLex(final String key, final String min, final String max) {
    zrangeByLex(SafeEncoder.encode(key), SafeEncoder.encode(min), SafeEncoder.encode(max));
  }

  public void zrangeByLex(final String key, final String min, final String max, final int offset,
      final int count) {
    zrangeByLex(SafeEncoder.encode(key), SafeEncoder.encode(min), SafeEncoder.encode(max), offset,
      count);
  }

  public void zrevrangeByLex(String key, String max, String min) {
    zrevrangeByLex(SafeEncoder.encode(key), SafeEncoder.encode(max), SafeEncoder.encode(min));
  }

  public void zrevrangeByLex(String key, String max, String min, int offset, int count) {
    zrevrangeByLex(SafeEncoder.encode(key), SafeEncoder.encode(max), SafeEncoder.encode(min),
      offset, count);
  }

  public void zremrangeByLex(final String key, final String min, final String max) {
    zremrangeByLex(SafeEncoder.encode(key), SafeEncoder.encode(min), SafeEncoder.encode(max));
  }

  @Override
  public void strlen(final String key) {
    strlen(SafeEncoder.encode(key));
  }

  @Override
  public void lpushx(final String key, final String... string) {
    lpushx(SafeEncoder.encode(key), getByteParams(string));
  }

  @Override
  public void persist(final String key) {
    persist(SafeEncoder.encode(key));
  }

  @Override
  public void rpushx(final String key, final String... string) {
    rpushx(SafeEncoder.encode(key), getByteParams(string));
  }

  @Override
  public void echo(final String string) {
    echo(SafeEncoder.encode(string));
  }

  @Override
  public void linsert(final String key, final LIST_POSITION where, final String pivot,
      final String value) {
    linsert(SafeEncoder.encode(key), where, SafeEncoder.encode(pivot), SafeEncoder.encode(value));
  }

  @Override
  public void brpoplpush(String source, String destination, int timeout) {
    brpoplpush(SafeEncoder.encode(source), SafeEncoder.encode(destination), timeout);
  }

  @Override
  public void setbit(final String key, final long offset, final boolean value) {
    setbit(SafeEncoder.encode(key), offset, value);
  }

  @Override
  public void setbit(final String key, final long offset, final String value) {
    setbit(SafeEncoder.encode(key), offset, SafeEncoder.encode(value));
  }

  @Override
  public void getbit(String key, long offset) {
    getbit(SafeEncoder.encode(key), offset);
  }

  public void bitpos(final String key, final boolean value, final BitPosParams params) {
    bitpos(SafeEncoder.encode(key), value, params);
  }

  @Override
  public void setrange(String key, long offset, String value) {
    setrange(SafeEncoder.encode(key), offset, SafeEncoder.encode(value));
  }

  @Override
  public void getrange(String key, long startOffset, long endOffset) {
    getrange(SafeEncoder.encode(key), startOffset, endOffset);
  }

  public void publish(final String channel, final String message) {
    publish(SafeEncoder.encode(channel), SafeEncoder.encode(message));
  }

  public void unsubscribe(final String... channels) {
    final byte[][] cs = new byte[channels.length][];
    for (int i = 0; i < cs.length; i++) {
      cs[i] = SafeEncoder.encode(channels[i]);
    }
    unsubscribe(cs);
  }

  public void psubscribe(final String... patterns) {
    final byte[][] ps = new byte[patterns.length][];
    for (int i = 0; i < ps.length; i++) {
      ps[i] = SafeEncoder.encode(patterns[i]);
    }
    psubscribe(ps);
  }

  public void punsubscribe(final String... patterns) {
    final byte[][] ps = new byte[patterns.length][];
    for (int i = 0; i < ps.length; i++) {
      ps[i] = SafeEncoder.encode(patterns[i]);
    }
    punsubscribe(ps);
  }

  public void subscribe(final String... channels) {
    final byte[][] cs = new byte[channels.length][];
    for (int i = 0; i < cs.length; i++) {
      cs[i] = SafeEncoder.encode(channels[i]);
    }
    subscribe(cs);
  }

  public void pubsubChannels(String pattern) {
    pubsub(Protocol.PUBSUB_CHANNELS, pattern);
  }

  public void pubsubNumPat() {
    pubsub(Protocol.PUBSUB_NUM_PAT);
  }

  public void pubsubNumSub(String... channels) {
    pubsub(Protocol.PUBSUB_NUMSUB, channels);
  }

  @Override
  public void configSet(String parameter, String value) {
    configSet(SafeEncoder.encode(parameter), SafeEncoder.encode(value));
  }

  @Override
  public void configGet(String pattern) {
    configGet(SafeEncoder.encode(pattern));
  }

  private byte[][] getByteParams(String... params) {
    byte[][] p = new byte[params.length][];
    for (int i = 0; i < params.length; i++)
      p[i] = SafeEncoder.encode(params[i]);

    return p;
  }

  public void eval(String script, int keyCount, String... params) {
    eval(SafeEncoder.encode(script), toByteArray(keyCount), getByteParams(params));
  }

  public void evalsha(String sha1, int keyCount, String... params) {
    evalsha(SafeEncoder.encode(sha1), toByteArray(keyCount), getByteParams(params));
  }

  public void scriptExists(String... sha1) {
    final byte[][] bsha1 = new byte[sha1.length][];
    for (int i = 0; i < bsha1.length; i++) {
      bsha1[i] = SafeEncoder.encode(sha1[i]);
    }
    scriptExists(bsha1);
  }

  public void scriptLoad(String script) {
    scriptLoad(SafeEncoder.encode(script));
  }

  @Override
  public void zadd(String key, Map<String, Double> scoreMembers) {

    HashMap<byte[], Double> binaryScoreMembers = new HashMap<byte[], Double>();

    for (Map.Entry<String, Double> entry : scoreMembers.entrySet()) {

      binaryScoreMembers.put(SafeEncoder.encode(entry.getKey()), entry.getValue());
    }

    zaddBinary(SafeEncoder.encode(key), binaryScoreMembers);
  }

  @Override
  public void objectRefcount(String key) {
    objectRefcount(SafeEncoder.encode(key));
  }

  @Override
  public void objectIdletime(String key) {
    objectIdletime(SafeEncoder.encode(key));
  }

  @Override
  public void objectEncoding(String key) {
    objectEncoding(SafeEncoder.encode(key));
  }

  @Override
  public void bitcount(final String key) {
    bitcount(SafeEncoder.encode(key));
  }

  @Override
  public void bitcount(final String key, long start, long end) {
    bitcount(SafeEncoder.encode(key), start, end);
  }

  @Override
  public void bitop(BitOP op, final String destKey, String... srcKeys) {
    bitop(op, SafeEncoder.encode(destKey), getByteParams(srcKeys));
  }

  public void sentinel(final String... args) {
    final byte[][] arg = new byte[args.length][];
    for (int i = 0; i < arg.length; i++) {
      arg[i] = SafeEncoder.encode(args[i]);
    }
    sentinel(arg);
  }

  public void dump(final String key) {
    dump(SafeEncoder.encode(key));
  }

  public void restore(final String key, final int ttl, final byte[] serializedValue) {
    restore(SafeEncoder.encode(key), ttl, serializedValue);
  }

  public void pexpire(final String key, final long milliseconds) {
    pexpire(SafeEncoder.encode(key), milliseconds);
  }

  public void pexpireAt(final String key, final long millisecondsTimestamp) {
    pexpireAt(SafeEncoder.encode(key), millisecondsTimestamp);
  }

  public void pttl(final String key) {
    pttl(SafeEncoder.encode(key));
  }

  @Override
  public void incrByFloat(final String key, final double increment) {
    incrByFloat(SafeEncoder.encode(key), increment);
  }

  public void psetex(final String key, final long milliseconds, final String value) {
    psetex(SafeEncoder.encode(key), milliseconds, SafeEncoder.encode(value));
  }

  public void srandmember(final String key, final int count) {
    srandmember(SafeEncoder.encode(key), count);
  }

  public void clientKill(final String client) {
    clientKill(SafeEncoder.encode(client));
  }

  public void clientSetname(final String name) {
    clientSetname(SafeEncoder.encode(name));
  }

  public void migrate(final String host, final int port, final String key, final int destinationDb,
      final int timeout) {
    migrate(SafeEncoder.encode(host), port, SafeEncoder.encode(key), destinationDb, timeout);
  }

  @Override
  public void hincrByFloat(final String key, final String field, double increment) {
    hincrByFloat(SafeEncoder.encode(key), SafeEncoder.encode(field), increment);
  }

  @Override
  public void scan(final String cursor, final ScanParams params) {
    scan(SafeEncoder.encode(cursor), params);
  }

  @Override
  public void hscan(final String key, final String cursor, final ScanParams params) {
    hscan(SafeEncoder.encode(key), SafeEncoder.encode(cursor), params);
  }

  @Override
  public void sscan(final String key, final String cursor, final ScanParams params) {
    sscan(SafeEncoder.encode(key), SafeEncoder.encode(cursor), params);
  }

  @Override
  public void zscan(final String key, final String cursor, final ScanParams params) {
    zscan(SafeEncoder.encode(key), SafeEncoder.encode(cursor), params);
  }

  public void cluster(final String subcommand, final int... args) {
    final byte[][] arg = new byte[args.length + 1][];
    for (int i = 1; i < arg.length; i++) {
      arg[i] = toByteArray(args[i - 1]);
    }
    arg[0] = SafeEncoder.encode(subcommand);
    cluster(arg);
  }

  public void pubsub(final String subcommand, final String... args) {
    final byte[][] arg = new byte[args.length + 1][];
    for (int i = 1; i < arg.length; i++) {
      arg[i] = SafeEncoder.encode(args[i - 1]);
    }
    arg[0] = SafeEncoder.encode(subcommand);
    pubsub(arg);
  }

  public void cluster(final String subcommand, final String... args) {
    final byte[][] arg = new byte[args.length + 1][];
    for (int i = 1; i < arg.length; i++) {
      arg[i] = SafeEncoder.encode(args[i - 1]);
    }
    arg[0] = SafeEncoder.encode(subcommand);
    cluster(arg);
  }

  public void cluster(final String subcommand) {
    final byte[][] arg = new byte[1][];
    arg[0] = SafeEncoder.encode(subcommand);
    cluster(arg);
  }

  public void clusterNodes() {
    cluster(Protocol.CLUSTER_NODES);
  }

  public void clusterMeet(final String ip, final int port) {
    cluster(Protocol.CLUSTER_MEET, ip, String.valueOf(port));
  }

  public void clusterReset(Reset resetType) {
    cluster(Protocol.CLUSTER_RESET, resetType.toString());
  }

  public void clusterAddSlots(final int... slots) {
    cluster(Protocol.CLUSTER_ADDSLOTS, slots);
  }

  public void clusterDelSlots(final int... slots) {
    cluster(Protocol.CLUSTER_DELSLOTS, slots);
  }

  public void clusterInfo() {
    cluster(Protocol.CLUSTER_INFO);
  }

  public void clusterGetKeysInSlot(final int slot, final int count) {
    final int[] args = new int[] { slot, count };
    cluster(Protocol.CLUSTER_GETKEYSINSLOT, args);
  }

  public void clusterSetSlotNode(final int slot, final String nodeId) {
    cluster(Protocol.CLUSTER_SETSLOT, String.valueOf(slot), Protocol.CLUSTER_SETSLOT_NODE, nodeId);
  }

  public void clusterSetSlotMigrating(final int slot, final String nodeId) {
    cluster(Protocol.CLUSTER_SETSLOT, String.valueOf(slot), Protocol.CLUSTER_SETSLOT_MIGRATING,
      nodeId);
  }

  public void clusterSetSlotImporting(final int slot, final String nodeId) {
    cluster(Protocol.CLUSTER_SETSLOT, String.valueOf(slot), Protocol.CLUSTER_SETSLOT_IMPORTING,
      nodeId);
  }

  public void pfadd(String key, final String... elements) {
    pfadd(SafeEncoder.encode(key), SafeEncoder.encodeMany(elements));
  }

  public void pfcount(final String key) {
    pfcount(SafeEncoder.encode(key));
  }

  public void pfcount(final String... keys) {
    pfcount(SafeEncoder.encodeMany(keys));
  }

  public void pfmerge(final String destkey, final String... sourcekeys) {
    pfmerge(SafeEncoder.encode(destkey), SafeEncoder.encodeMany(sourcekeys));
  }

  public void clusterSetSlotStable(final int slot) {
    cluster(Protocol.CLUSTER_SETSLOT, String.valueOf(slot), Protocol.CLUSTER_SETSLOT_STABLE);
  }

  public void clusterForget(final String nodeId) {
    cluster(Protocol.CLUSTER_FORGET, nodeId);
  }

  public void clusterFlushSlots() {
    cluster(Protocol.CLUSTER_FLUSHSLOT);
  }

  public void clusterKeySlot(final String key) {
    cluster(Protocol.CLUSTER_KEYSLOT, key);
  }

  public void clusterCountKeysInSlot(final int slot) {
    cluster(Protocol.CLUSTER_COUNTKEYINSLOT, String.valueOf(slot));
  }

  public void clusterSaveConfig() {
    cluster(Protocol.CLUSTER_SAVECONFIG);
  }

  public void clusterReplicate(final String nodeId) {
    cluster(Protocol.CLUSTER_REPLICATE, nodeId);
  }

  public void clusterSlaves(final String nodeId) {
    cluster(Protocol.CLUSTER_SLAVES, nodeId);
  }

  public void clusterFailover() {
    cluster(Protocol.CLUSTER_FAILOVER);
  }

  public void clusterSlots() {
    cluster(Protocol.CLUSTER_SLOTS);
  }

}


File: src/main/java/redis/clients/jedis/Connection.java
package redis.clients.jedis;

import java.io.Closeable;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.SocketException;
import java.util.ArrayList;
import java.util.List;

import redis.clients.jedis.exceptions.JedisConnectionException;
import redis.clients.jedis.exceptions.JedisDataException;
import redis.clients.util.IOUtils;
import redis.clients.util.RedisInputStream;
import redis.clients.util.RedisOutputStream;
import redis.clients.util.SafeEncoder;

public class Connection implements Closeable {

  private static final byte[][] EMPTY_ARGS = new byte[0][];

  private String host = Protocol.DEFAULT_HOST;
  private int port = Protocol.DEFAULT_PORT;
  private Socket socket;
  private RedisOutputStream outputStream;
  private RedisInputStream inputStream;
  private int connectionTimeout = Protocol.DEFAULT_TIMEOUT;
  private int soTimeout = Protocol.DEFAULT_TIMEOUT;
  private boolean broken = false;

  public Connection() {
  }

  public Connection(final String host) {
    this.host = host;
  }

  public Connection(final String host, final int port) {
    this.host = host;
    this.port = port;
  }

  public Socket getSocket() {
    return socket;
  }

  public int getConnectionTimeout() {
    return connectionTimeout;
  }

  public int getSoTimeout() {
    return soTimeout;
  }

  public void setConnectionTimeout(int connectionTimeout) {
    this.connectionTimeout = connectionTimeout;
  }

  public void setSoTimeout(int soTimeout) {
    this.soTimeout = soTimeout;
  }

  public void setTimeoutInfinite() {
    try {
      if (!isConnected()) {
        connect();
      }
      socket.setSoTimeout(0);
    } catch (SocketException ex) {
      broken = true;
      throw new JedisConnectionException(ex);
    }
  }

  public void rollbackTimeout() {
    try {
      socket.setSoTimeout(soTimeout);
    } catch (SocketException ex) {
      broken = true;
      throw new JedisConnectionException(ex);
    }
  }

  protected Connection sendCommand(final ProtocolCommand cmd, final String... args) {
    final byte[][] bargs = new byte[args.length][];
    for (int i = 0; i < args.length; i++) {
      bargs[i] = SafeEncoder.encode(args[i]);
    }
    return sendCommand(cmd, bargs);
  }

  protected Connection sendCommand(final ProtocolCommand cmd) {
    return sendCommand(cmd, EMPTY_ARGS);
  }

  protected Connection sendCommand(final ProtocolCommand cmd, final byte[]... args) {
    try {
      connect();
      Protocol.sendCommand(outputStream, cmd, args);
      return this;
    } catch (JedisConnectionException ex) {
      /*
       * When client send request which formed by invalid protocol, Redis send back error message
       * before close connection. We try to read it to provide reason of failure.
       */
      try {
        String errorMessage = Protocol.readErrorLineIfPossible(inputStream);
        if (errorMessage != null && errorMessage.length() > 0) {
          ex = new JedisConnectionException(errorMessage, ex.getCause());
        }
      } catch (Exception e) {
        /*
         * Catch any IOException or JedisConnectionException occurred from InputStream#read and just
         * ignore. This approach is safe because reading error message is optional and connection
         * will eventually be closed.
         */
      }
      // Any other exceptions related to connection?
      broken = true;
      throw ex;
    }
  }

  public String getHost() {
    return host;
  }

  public void setHost(final String host) {
    this.host = host;
  }

  public int getPort() {
    return port;
  }

  public void setPort(final int port) {
    this.port = port;
  }

  public void connect() {
    if (!isConnected()) {
      try {
        socket = new Socket();
        // ->@wjw_add
        socket.setReuseAddress(true);
        socket.setKeepAlive(true); // Will monitor the TCP connection is
        // valid
        socket.setTcpNoDelay(true); // Socket buffer Whetherclosed, to
        // ensure timely delivery of data
        socket.setSoLinger(true, 0); // Control calls close () method,
        // the underlying socket is closed
        // immediately
        // <-@wjw_add

        socket.connect(new InetSocketAddress(host, port), connectionTimeout);
        socket.setSoTimeout(soTimeout);
        outputStream = new RedisOutputStream(socket.getOutputStream());
        inputStream = new RedisInputStream(socket.getInputStream());
      } catch (IOException ex) {
        broken = true;
        throw new JedisConnectionException(ex);
      }
    }
  }

  @Override
  public void close() {
    disconnect();
  }

  public void disconnect() {
    if (isConnected()) {
      try {
        outputStream.flush();
        socket.close();
      } catch (IOException ex) {
        broken = true;
        throw new JedisConnectionException(ex);
      } finally {
        IOUtils.closeQuietly(socket);
      }
    }
  }

  public boolean isConnected() {
    return socket != null && socket.isBound() && !socket.isClosed() && socket.isConnected()
        && !socket.isInputShutdown() && !socket.isOutputShutdown();
  }

  public String getStatusCodeReply() {
    flush();
    final byte[] resp = (byte[]) readProtocolWithCheckingBroken();
    if (null == resp) {
      return null;
    } else {
      return SafeEncoder.encode(resp);
    }
  }

  public String getBulkReply() {
    final byte[] result = getBinaryBulkReply();
    if (null != result) {
      return SafeEncoder.encode(result);
    } else {
      return null;
    }
  }

  public byte[] getBinaryBulkReply() {
    flush();
    return (byte[]) readProtocolWithCheckingBroken();
  }

  public Long getIntegerReply() {
    flush();
    return (Long) readProtocolWithCheckingBroken();
  }

  public List<String> getMultiBulkReply() {
    return BuilderFactory.STRING_LIST.build(getBinaryMultiBulkReply());
  }

  @SuppressWarnings("unchecked")
  public List<byte[]> getBinaryMultiBulkReply() {
    flush();
    return (List<byte[]>) readProtocolWithCheckingBroken();
  }

  @SuppressWarnings("unchecked")
  public List<Object> getRawObjectMultiBulkReply() {
    return (List<Object>) readProtocolWithCheckingBroken();
  }

  public List<Object> getObjectMultiBulkReply() {
    flush();
    return getRawObjectMultiBulkReply();
  }

  @SuppressWarnings("unchecked")
  public List<Long> getIntegerMultiBulkReply() {
    flush();
    return (List<Long>) readProtocolWithCheckingBroken();
  }

  public Object getOne() {
    flush();
    return readProtocolWithCheckingBroken();
  }

  public boolean isBroken() {
    return broken;
  }

  protected void flush() {
    try {
      outputStream.flush();
    } catch (IOException ex) {
      broken = true;
      throw new JedisConnectionException(ex);
    }
  }

  protected Object readProtocolWithCheckingBroken() {
    try {
      return Protocol.read(inputStream);
    } catch (JedisConnectionException exc) {
      broken = true;
      throw exc;
    }
  }

  public List<Object> getMany(final int count) {
    flush();
    final List<Object> responses = new ArrayList<Object>(count);
    for (int i = 0; i < count; i++) {
      try {
        responses.add(readProtocolWithCheckingBroken());
      } catch (JedisDataException e) {
        responses.add(e);
      }
    }
    return responses;
  }
}


File: src/main/java/redis/clients/jedis/Jedis.java
package redis.clients.jedis;

import java.net.URI;
import java.util.AbstractMap;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;

import redis.clients.jedis.BinaryClient.LIST_POSITION;
import redis.clients.jedis.JedisCluster.Reset;
import redis.clients.jedis.params.set.SetParams;
import redis.clients.util.SafeEncoder;
import redis.clients.util.Slowlog;

public class Jedis extends BinaryJedis implements JedisCommands, MultiKeyCommands,
    AdvancedJedisCommands, ScriptingCommands, BasicCommands, ClusterCommands, SentinelCommands {

  protected JedisPoolAbstract dataSource = null;

  public Jedis() {
    super();
  }

  public Jedis(final String host) {
    super(host);
  }

  public Jedis(final String host, final int port) {
    super(host, port);
  }

  public Jedis(final String host, final int port, final int timeout) {
    super(host, port, timeout);
  }

  public Jedis(final String host, final int port, final int connectionTimeout, final int soTimeout) {
    super(host, port, connectionTimeout, soTimeout);
  }

  public Jedis(JedisShardInfo shardInfo) {
    super(shardInfo);
  }

  public Jedis(URI uri) {
    super(uri);
  }

  public Jedis(final URI uri, final int timeout) {
    super(uri, timeout);
  }

  public Jedis(final URI uri, final int connectionTimeout, final int soTimeout) {
    super(uri, connectionTimeout, soTimeout);
  }

  /**
   * Set the string value as value of the key. The string can't be longer than 1073741824 bytes (1
   * GB).
   * <p>
   * Time complexity: O(1)
   * @param key
   * @param value
   * @return Status code reply
   */
  @Override
  public String set(final String key, String value) {
    checkIsInMultiOrPipeline();
    client.set(key, value);
    return client.getStatusCodeReply();
  }

  /**
   * Set the string value as value of the key. The string can't be longer than 1073741824 bytes (1
   * GB).
   * @param key
   * @param value
   * @param params NX|XX, NX -- Only set the key if it does not already exist. XX -- Only set the
   *          key if it already exist. EX|PX, expire time units: EX = seconds; PX = milliseconds
   * @return Status code reply
   */
  public String set(final String key, final String value, final SetParams params) {
    checkIsInMultiOrPipeline();
    client.set(key, value, params);
    return client.getStatusCodeReply();
  }

  /**
   * Get the value of the specified key. If the key does not exist null is returned. If the value
   * stored at key is not a string an error is returned because GET can only handle string values.
   * <p>
   * Time complexity: O(1)
   * @param key
   * @return Bulk reply
   */
  @Override
  public String get(final String key) {
    checkIsInMultiOrPipeline();
    client.sendCommand(Protocol.Command.GET, key);
    return client.getBulkReply();
  }

  /**
   * Test if the specified key exists. The command returns "1" if the key exists, otherwise "0" is
   * returned. Note that even keys set with an empty string as value will return "1". Time
   * complexity: O(1)
   * @param key
   * @return Boolean reply, true if the key exists, otherwise false
   */
  @Override
  public Boolean exists(final String key) {
    checkIsInMultiOrPipeline();
    client.exists(key);
    return client.getIntegerReply() == 1;
  }

  /**
   * Remove the specified keys. If a given key does not exist no operation is performed for this
   * key. The command returns the number of keys removed. Time complexity: O(1)
   * @param keys
   * @return Integer reply, specifically: an integer greater than 0 if one or more keys were removed
   *         0 if none of the specified key existed
   */
  @Override
  public Long del(final String... keys) {
    checkIsInMultiOrPipeline();
    client.del(keys);
    return client.getIntegerReply();
  }

  @Override
  public Long del(String key) {
    client.del(key);
    return client.getIntegerReply();
  }

  /**
   * Return the type of the value stored at key in form of a string. The type can be one of "none",
   * "string", "list", "set". "none" is returned if the key does not exist. Time complexity: O(1)
   * @param key
   * @return Status code reply, specifically: "none" if the key does not exist "string" if the key
   *         contains a String value "list" if the key contains a List value "set" if the key
   *         contains a Set value "zset" if the key contains a Sorted Set value "hash" if the key
   *         contains a Hash value
   */
  @Override
  public String type(final String key) {
    checkIsInMultiOrPipeline();
    client.type(key);
    return client.getStatusCodeReply();
  }

  /**
   * Returns all the keys matching the glob-style pattern as space separated strings. For example if
   * you have in the database the keys "foo" and "foobar" the command "KEYS foo*" will return
   * "foo foobar".
   * <p>
   * Note that while the time complexity for this operation is O(n) the constant times are pretty
   * low. For example Redis running on an entry level laptop can scan a 1 million keys database in
   * 40 milliseconds. <b>Still it's better to consider this one of the slow commands that may ruin
   * the DB performance if not used with care.</b>
   * <p>
   * In other words this command is intended only for debugging and special operations like creating
   * a script to change the DB schema. Don't use it in your normal code. Use Redis Sets in order to
   * group together a subset of objects.
   * <p>
   * Glob style patterns examples:
   * <ul>
   * <li>h?llo will match hello hallo hhllo
   * <li>h*llo will match hllo heeeello
   * <li>h[ae]llo will match hello and hallo, but not hillo
   * </ul>
   * <p>
   * Use \ to escape special chars if you want to match them verbatim.
   * <p>
   * Time complexity: O(n) (with n being the number of keys in the DB, and assuming keys and pattern
   * of limited length)
   * @param pattern
   * @return Multi bulk reply
   */
  @Override
  public Set<String> keys(final String pattern) {
    checkIsInMultiOrPipeline();
    client.keys(pattern);
    return BuilderFactory.STRING_SET.build(client.getBinaryMultiBulkReply());
  }

  /**
   * Return a randomly selected key from the currently selected DB.
   * <p>
   * Time complexity: O(1)
   * @return Singe line reply, specifically the randomly selected key or an empty string is the
   *         database is empty
   */
  @Override
  public String randomKey() {
    checkIsInMultiOrPipeline();
    client.randomKey();
    return client.getBulkReply();
  }

  /**
   * Atomically renames the key oldkey to newkey. If the source and destination name are the same an
   * error is returned. If newkey already exists it is overwritten.
   * <p>
   * Time complexity: O(1)
   * @param oldkey
   * @param newkey
   * @return Status code repy
   */
  @Override
  public String rename(final String oldkey, final String newkey) {
    checkIsInMultiOrPipeline();
    client.rename(oldkey, newkey);
    return client.getStatusCodeReply();
  }

  /**
   * Rename oldkey into newkey but fails if the destination key newkey already exists.
   * <p>
   * Time complexity: O(1)
   * @param oldkey
   * @param newkey
   * @return Integer reply, specifically: 1 if the key was renamed 0 if the target key already exist
   */
  @Override
  public Long renamenx(final String oldkey, final String newkey) {
    checkIsInMultiOrPipeline();
    client.renamenx(oldkey, newkey);
    return client.getIntegerReply();
  }

  /**
   * Set a timeout on the specified key. After the timeout the key will be automatically deleted by
   * the server. A key with an associated timeout is said to be volatile in Redis terminology.
   * <p>
   * Voltile keys are stored on disk like the other keys, the timeout is persistent too like all the
   * other aspects of the dataset. Saving a dataset containing expires and stopping the server does
   * not stop the flow of time as Redis stores on disk the time when the key will no longer be
   * available as Unix time, and not the remaining seconds.
   * <p>
   * Since Redis 2.1.3 you can update the value of the timeout of a key already having an expire
   * set. It is also possible to undo the expire at all turning the key into a normal key using the
   * {@link #persist(String) PERSIST} command.
   * <p>
   * Time complexity: O(1)
   * @see <a href="http://redis.io/commands/expire">Expire Command</a>
   * @param key
   * @param seconds
   * @return Integer reply, specifically: 1: the timeout was set. 0: the timeout was not set since
   *         the key already has an associated timeout (this may happen only in Redis versions &lt;
   *         2.1.3, Redis &gt;= 2.1.3 will happily update the timeout), or the key does not exist.
   */
  @Override
  public Long expire(final String key, final int seconds) {
    checkIsInMultiOrPipeline();
    client.expire(key, seconds);
    return client.getIntegerReply();
  }

  /**
   * EXPIREAT works exctly like {@link #expire(String, int) EXPIRE} but instead to get the number of
   * seconds representing the Time To Live of the key as a second argument (that is a relative way
   * of specifing the TTL), it takes an absolute one in the form of a UNIX timestamp (Number of
   * seconds elapsed since 1 Gen 1970).
   * <p>
   * EXPIREAT was introduced in order to implement the Append Only File persistence mode so that
   * EXPIRE commands are automatically translated into EXPIREAT commands for the append only file.
   * Of course EXPIREAT can also used by programmers that need a way to simply specify that a given
   * key should expire at a given time in the future.
   * <p>
   * Since Redis 2.1.3 you can update the value of the timeout of a key already having an expire
   * set. It is also possible to undo the expire at all turning the key into a normal key using the
   * {@link #persist(String) PERSIST} command.
   * <p>
   * Time complexity: O(1)
   * @see <a href="http://redis.io/commands/expire">Expire Command</a>
   * @param key
   * @param unixTime
   * @return Integer reply, specifically: 1: the timeout was set. 0: the timeout was not set since
   *         the key already has an associated timeout (this may happen only in Redis versions &lt;
   *         2.1.3, Redis &gt;= 2.1.3 will happily update the timeout), or the key does not exist.
   */
  @Override
  public Long expireAt(final String key, final long unixTime) {
    checkIsInMultiOrPipeline();
    client.expireAt(key, unixTime);
    return client.getIntegerReply();
  }

  /**
   * The TTL command returns the remaining time to live in seconds of a key that has an
   * {@link #expire(String, int) EXPIRE} set. This introspection capability allows a Redis client to
   * check how many seconds a given key will continue to be part of the dataset.
   * @param key
   * @return Integer reply, returns the remaining time to live in seconds of a key that has an
   *         EXPIRE. In Redis 2.6 or older, if the Key does not exists or does not have an
   *         associated expire, -1 is returned. In Redis 2.8 or newer, if the Key does not have an
   *         associated expire, -1 is returned or if the Key does not exists, -2 is returned.
   */
  @Override
  public Long ttl(final String key) {
    checkIsInMultiOrPipeline();
    client.ttl(key);
    return client.getIntegerReply();
  }

  /**
   * Move the specified key from the currently selected DB to the specified destination DB. Note
   * that this command returns 1 only if the key was successfully moved, and 0 if the target key was
   * already there or if the source key was not found at all, so it is possible to use MOVE as a
   * locking primitive.
   * @param key
   * @param dbIndex
   * @return Integer reply, specifically: 1 if the key was moved 0 if the key was not moved because
   *         already present on the target DB or was not found in the current DB.
   */
  @Override
  public Long move(final String key, final int dbIndex) {
    checkIsInMultiOrPipeline();
    client.move(key, dbIndex);
    return client.getIntegerReply();
  }

  /**
   * GETSET is an atomic set this value and return the old value command. Set key to the string
   * value and return the old value stored at key. The string can't be longer than 1073741824 bytes
   * (1 GB).
   * <p>
   * Time complexity: O(1)
   * @param key
   * @param value
   * @return Bulk reply
   */
  @Override
  public String getSet(final String key, final String value) {
    checkIsInMultiOrPipeline();
    client.getSet(key, value);
    return client.getBulkReply();
  }

  /**
   * Get the values of all the specified keys. If one or more keys dont exist or is not of type
   * String, a 'nil' value is returned instead of the value of the specified key, but the operation
   * never fails.
   * <p>
   * Time complexity: O(1) for every key
   * @param keys
   * @return Multi bulk reply
   */
  @Override
  public List<String> mget(final String... keys) {
    checkIsInMultiOrPipeline();
    client.mget(keys);
    return client.getMultiBulkReply();
  }

  /**
   * SETNX works exactly like {@link #set(String, String) SET} with the only difference that if the
   * key already exists no operation is performed. SETNX actually means "SET if Not eXists".
   * <p>
   * Time complexity: O(1)
   * @param key
   * @param value
   * @return Integer reply, specifically: 1 if the key was set 0 if the key was not set
   */
  @Override
  public Long setnx(final String key, final String value) {
    checkIsInMultiOrPipeline();
    client.setnx(key, value);
    return client.getIntegerReply();
  }

  /**
   * The command is exactly equivalent to the following group of commands:
   * {@link #set(String, String) SET} + {@link #expire(String, int) EXPIRE}. The operation is
   * atomic.
   * <p>
   * Time complexity: O(1)
   * @param key
   * @param seconds
   * @param value
   * @return Status code reply
   */
  @Override
  public String setex(final String key, final int seconds, final String value) {
    checkIsInMultiOrPipeline();
    client.setex(key, seconds, value);
    return client.getStatusCodeReply();
  }

  /**
   * Set the the respective keys to the respective values. MSET will replace old values with new
   * values, while {@link #msetnx(String...) MSETNX} will not perform any operation at all even if
   * just a single key already exists.
   * <p>
   * Because of this semantic MSETNX can be used in order to set different keys representing
   * different fields of an unique logic object in a way that ensures that either all the fields or
   * none at all are set.
   * <p>
   * Both MSET and MSETNX are atomic operations. This means that for instance if the keys A and B
   * are modified, another client talking to Redis can either see the changes to both A and B at
   * once, or no modification at all.
   * @see #msetnx(String...)
   * @param keysvalues
   * @return Status code reply Basically +OK as MSET can't fail
   */
  @Override
  public String mset(final String... keysvalues) {
    checkIsInMultiOrPipeline();
    client.mset(keysvalues);
    return client.getStatusCodeReply();
  }

  /**
   * Set the the respective keys to the respective values. {@link #mset(String...) MSET} will
   * replace old values with new values, while MSETNX will not perform any operation at all even if
   * just a single key already exists.
   * <p>
   * Because of this semantic MSETNX can be used in order to set different keys representing
   * different fields of an unique logic object in a way that ensures that either all the fields or
   * none at all are set.
   * <p>
   * Both MSET and MSETNX are atomic operations. This means that for instance if the keys A and B
   * are modified, another client talking to Redis can either see the changes to both A and B at
   * once, or no modification at all.
   * @see #mset(String...)
   * @param keysvalues
   * @return Integer reply, specifically: 1 if the all the keys were set 0 if no key was set (at
   *         least one key already existed)
   */
  @Override
  public Long msetnx(final String... keysvalues) {
    checkIsInMultiOrPipeline();
    client.msetnx(keysvalues);
    return client.getIntegerReply();
  }

  /**
   * IDECRBY work just like {@link #decr(String) INCR} but instead to decrement by 1 the decrement
   * is integer.
   * <p>
   * INCR commands are limited to 64 bit signed integers.
   * <p>
   * Note: this is actually a string operation, that is, in Redis there are not "integer" types.
   * Simply the string stored at the key is parsed as a base 10 64 bit signed integer, incremented,
   * and then converted back as a string.
   * <p>
   * Time complexity: O(1)
   * @see #incr(String)
   * @see #decr(String)
   * @see #incrBy(String, long)
   * @param key
   * @param integer
   * @return Integer reply, this commands will reply with the new value of key after the increment.
   */
  @Override
  public Long decrBy(final String key, final long integer) {
    checkIsInMultiOrPipeline();
    client.decrBy(key, integer);
    return client.getIntegerReply();
  }

  /**
   * Decrement the number stored at key by one. If the key does not exist or contains a value of a
   * wrong type, set the key to the value of "0" before to perform the decrement operation.
   * <p>
   * INCR commands are limited to 64 bit signed integers.
   * <p>
   * Note: this is actually a string operation, that is, in Redis there are not "integer" types.
   * Simply the string stored at the key is parsed as a base 10 64 bit signed integer, incremented,
   * and then converted back as a string.
   * <p>
   * Time complexity: O(1)
   * @see #incr(String)
   * @see #incrBy(String, long)
   * @see #decrBy(String, long)
   * @param key
   * @return Integer reply, this commands will reply with the new value of key after the increment.
   */
  @Override
  public Long decr(final String key) {
    checkIsInMultiOrPipeline();
    client.decr(key);
    return client.getIntegerReply();
  }

  /**
   * INCRBY work just like {@link #incr(String) INCR} but instead to increment by 1 the increment is
   * integer.
   * <p>
   * INCR commands are limited to 64 bit signed integers.
   * <p>
   * Note: this is actually a string operation, that is, in Redis there are not "integer" types.
   * Simply the string stored at the key is parsed as a base 10 64 bit signed integer, incremented,
   * and then converted back as a string.
   * <p>
   * Time complexity: O(1)
   * @see #incr(String)
   * @see #decr(String)
   * @see #decrBy(String, long)
   * @param key
   * @param integer
   * @return Integer reply, this commands will reply with the new value of key after the increment.
   */
  @Override
  public Long incrBy(final String key, final long integer) {
    checkIsInMultiOrPipeline();
    client.incrBy(key, integer);
    return client.getIntegerReply();
  }

  /**
   * INCRBYFLOAT
   * <p>
   * INCRBYFLOAT commands are limited to double precision floating point values.
   * <p>
   * Note: this is actually a string operation, that is, in Redis there are not "double" types.
   * Simply the string stored at the key is parsed as a base double precision floating point value,
   * incremented, and then converted back as a string. There is no DECRYBYFLOAT but providing a
   * negative value will work as expected.
   * <p>
   * Time complexity: O(1)
   * @param key
   * @param value
   * @return Double reply, this commands will reply with the new value of key after the increment.
   */
  @Override
  public Double incrByFloat(final String key, final double value) {
    checkIsInMultiOrPipeline();
    client.incrByFloat(key, value);
    String dval = client.getBulkReply();
    return (dval != null ? new Double(dval) : null);
  }

  /**
   * Increment the number stored at key by one. If the key does not exist or contains a value of a
   * wrong type, set the key to the value of "0" before to perform the increment operation.
   * <p>
   * INCR commands are limited to 64 bit signed integers.
   * <p>
   * Note: this is actually a string operation, that is, in Redis there are not "integer" types.
   * Simply the string stored at the key is parsed as a base 10 64 bit signed integer, incremented,
   * and then converted back as a string.
   * <p>
   * Time complexity: O(1)
   * @see #incrBy(String, long)
   * @see #decr(String)
   * @see #decrBy(String, long)
   * @param key
   * @return Integer reply, this commands will reply with the new value of key after the increment.
   */
  @Override
  public Long incr(final String key) {
    checkIsInMultiOrPipeline();
    client.incr(key);
    return client.getIntegerReply();
  }

  /**
   * If the key already exists and is a string, this command appends the provided value at the end
   * of the string. If the key does not exist it is created and set as an empty string, so APPEND
   * will be very similar to SET in this special case.
   * <p>
   * Time complexity: O(1). The amortized time complexity is O(1) assuming the appended value is
   * small and the already present value is of any size, since the dynamic string library used by
   * Redis will double the free space available on every reallocation.
   * @param key
   * @param value
   * @return Integer reply, specifically the total length of the string after the append operation.
   */
  @Override
  public Long append(final String key, final String value) {
    checkIsInMultiOrPipeline();
    client.append(key, value);
    return client.getIntegerReply();
  }

  /**
   * Return a subset of the string from offset start to offset end (both offsets are inclusive).
   * Negative offsets can be used in order to provide an offset starting from the end of the string.
   * So -1 means the last char, -2 the penultimate and so forth.
   * <p>
   * The function handles out of range requests without raising an error, but just limiting the
   * resulting range to the actual length of the string.
   * <p>
   * Time complexity: O(start+n) (with start being the start index and n the total length of the
   * requested range). Note that the lookup part of this command is O(1) so for small strings this
   * is actually an O(1) command.
   * @param key
   * @param start
   * @param end
   * @return Bulk reply
   */
  @Override
  public String substr(final String key, final int start, final int end) {
    checkIsInMultiOrPipeline();
    client.substr(key, start, end);
    return client.getBulkReply();
  }

  /**
   * Set the specified hash field to the specified value.
   * <p>
   * If key does not exist, a new key holding a hash is created.
   * <p>
   * <b>Time complexity:</b> O(1)
   * @param key
   * @param field
   * @param value
   * @return If the field already exists, and the HSET just produced an update of the value, 0 is
   *         returned, otherwise if a new field is created 1 is returned.
   */
  @Override
  public Long hset(final String key, final String field, final String value) {
    checkIsInMultiOrPipeline();
    client.hset(key, field, value);
    return client.getIntegerReply();
  }

  /**
   * If key holds a hash, retrieve the value associated to the specified field.
   * <p>
   * If the field is not found or the key does not exist, a special 'nil' value is returned.
   * <p>
   * <b>Time complexity:</b> O(1)
   * @param key
   * @param field
   * @return Bulk reply
   */
  @Override
  public String hget(final String key, final String field) {
    checkIsInMultiOrPipeline();
    client.hget(key, field);
    return client.getBulkReply();
  }

  /**
   * Set the specified hash field to the specified value if the field not exists. <b>Time
   * complexity:</b> O(1)
   * @param key
   * @param field
   * @param value
   * @return If the field already exists, 0 is returned, otherwise if a new field is created 1 is
   *         returned.
   */
  @Override
  public Long hsetnx(final String key, final String field, final String value) {
    checkIsInMultiOrPipeline();
    client.hsetnx(key, field, value);
    return client.getIntegerReply();
  }

  /**
   * Set the respective fields to the respective values. HMSET replaces old values with new values.
   * <p>
   * If key does not exist, a new key holding a hash is created.
   * <p>
   * <b>Time complexity:</b> O(N) (with N being the number of fields)
   * @param key
   * @param hash
   * @return Return OK or Exception if hash is empty
   */
  @Override
  public String hmset(final String key, final Map<String, String> hash) {
    checkIsInMultiOrPipeline();
    client.hmset(key, hash);
    return client.getStatusCodeReply();
  }

  /**
   * Retrieve the values associated to the specified fields.
   * <p>
   * If some of the specified fields do not exist, nil values are returned. Non existing keys are
   * considered like empty hashes.
   * <p>
   * <b>Time complexity:</b> O(N) (with N being the number of fields)
   * @param key
   * @param fields
   * @return Multi Bulk Reply specifically a list of all the values associated with the specified
   *         fields, in the same order of the request.
   */
  @Override
  public List<String> hmget(final String key, final String... fields) {
    checkIsInMultiOrPipeline();
    client.hmget(key, fields);
    return client.getMultiBulkReply();
  }

  /**
   * Increment the number stored at field in the hash at key by value. If key does not exist, a new
   * key holding a hash is created. If field does not exist or holds a string, the value is set to 0
   * before applying the operation. Since the value argument is signed you can use this command to
   * perform both increments and decrements.
   * <p>
   * The range of values supported by HINCRBY is limited to 64 bit signed integers.
   * <p>
   * <b>Time complexity:</b> O(1)
   * @param key
   * @param field
   * @param value
   * @return Integer reply The new value at field after the increment operation.
   */
  @Override
  public Long hincrBy(final String key, final String field, final long value) {
    checkIsInMultiOrPipeline();
    client.hincrBy(key, field, value);
    return client.getIntegerReply();
  }

  /**
   * Increment the number stored at field in the hash at key by a double precision floating point
   * value. If key does not exist, a new key holding a hash is created. If field does not exist or
   * holds a string, the value is set to 0 before applying the operation. Since the value argument
   * is signed you can use this command to perform both increments and decrements.
   * <p>
   * The range of values supported by HINCRBYFLOAT is limited to double precision floating point
   * values.
   * <p>
   * <b>Time complexity:</b> O(1)
   * @param key
   * @param field
   * @param value
   * @return Double precision floating point reply The new value at field after the increment
   *         operation.
   */
  @Override
  public Double hincrByFloat(final String key, final String field, final double value) {
    checkIsInMultiOrPipeline();
    client.hincrByFloat(key, field, value);
    final String dval = client.getBulkReply();
    return (dval != null ? new Double(dval) : null);
  }

  /**
   * Test for existence of a specified field in a hash. <b>Time complexity:</b> O(1)
   * @param key
   * @param field
   * @return Return 1 if the hash stored at key contains the specified field. Return 0 if the key is
   *         not found or the field is not present.
   */
  @Override
  public Boolean hexists(final String key, final String field) {
    checkIsInMultiOrPipeline();
    client.hexists(key, field);
    return client.getIntegerReply() == 1;
  }

  /**
   * Remove the specified field from an hash stored at key.
   * <p>
   * <b>Time complexity:</b> O(1)
   * @param key
   * @param fields
   * @return If the field was present in the hash it is deleted and 1 is returned, otherwise 0 is
   *         returned and no operation is performed.
   */
  @Override
  public Long hdel(final String key, final String... fields) {
    checkIsInMultiOrPipeline();
    client.hdel(key, fields);
    return client.getIntegerReply();
  }

  /**
   * Return the number of items in a hash.
   * <p>
   * <b>Time complexity:</b> O(1)
   * @param key
   * @return The number of entries (fields) contained in the hash stored at key. If the specified
   *         key does not exist, 0 is returned assuming an empty hash.
   */
  @Override
  public Long hlen(final String key) {
    checkIsInMultiOrPipeline();
    client.hlen(key);
    return client.getIntegerReply();
  }

  /**
   * Return all the fields in a hash.
   * <p>
   * <b>Time complexity:</b> O(N), where N is the total number of entries
   * @param key
   * @return All the fields names contained into a hash.
   */
  @Override
  public Set<String> hkeys(final String key) {
    checkIsInMultiOrPipeline();
    client.hkeys(key);
    return BuilderFactory.STRING_SET.build(client.getBinaryMultiBulkReply());
  }

  /**
   * Return all the values in a hash.
   * <p>
   * <b>Time complexity:</b> O(N), where N is the total number of entries
   * @param key
   * @return All the fields values contained into a hash.
   */
  @Override
  public List<String> hvals(final String key) {
    checkIsInMultiOrPipeline();
    client.hvals(key);
    final List<String> lresult = client.getMultiBulkReply();
    return lresult;
  }

  /**
   * Return all the fields and associated values in a hash.
   * <p>
   * <b>Time complexity:</b> O(N), where N is the total number of entries
   * @param key
   * @return All the fields and values contained into a hash.
   */
  @Override
  public Map<String, String> hgetAll(final String key) {
    checkIsInMultiOrPipeline();
    client.hgetAll(key);
    return BuilderFactory.STRING_MAP.build(client.getBinaryMultiBulkReply());
  }

  /**
   * Add the string value to the head (LPUSH) or tail (RPUSH) of the list stored at key. If the key
   * does not exist an empty list is created just before the append operation. If the key exists but
   * is not a List an error is returned.
   * <p>
   * Time complexity: O(1)
   * @param key
   * @param strings
   * @return Integer reply, specifically, the number of elements inside the list after the push
   *         operation.
   */
  @Override
  public Long rpush(final String key, final String... strings) {
    checkIsInMultiOrPipeline();
    client.rpush(key, strings);
    return client.getIntegerReply();
  }

  /**
   * Add the string value to the head (LPUSH) or tail (RPUSH) of the list stored at key. If the key
   * does not exist an empty list is created just before the append operation. If the key exists but
   * is not a List an error is returned.
   * <p>
   * Time complexity: O(1)
   * @param key
   * @param strings
   * @return Integer reply, specifically, the number of elements inside the list after the push
   *         operation.
   */
  @Override
  public Long lpush(final String key, final String... strings) {
    checkIsInMultiOrPipeline();
    client.lpush(key, strings);
    return client.getIntegerReply();
  }

  /**
   * Return the length of the list stored at the specified key. If the key does not exist zero is
   * returned (the same behaviour as for empty lists). If the value stored at key is not a list an
   * error is returned.
   * <p>
   * Time complexity: O(1)
   * @param key
   * @return The length of the list.
   */
  @Override
  public Long llen(final String key) {
    checkIsInMultiOrPipeline();
    client.llen(key);
    return client.getIntegerReply();
  }

  /**
   * Return the specified elements of the list stored at the specified key. Start and end are
   * zero-based indexes. 0 is the first element of the list (the list head), 1 the next element and
   * so on.
   * <p>
   * For example LRANGE foobar 0 2 will return the first three elements of the list.
   * <p>
   * start and end can also be negative numbers indicating offsets from the end of the list. For
   * example -1 is the last element of the list, -2 the penultimate element and so on.
   * <p>
   * <b>Consistency with range functions in various programming languages</b>
   * <p>
   * Note that if you have a list of numbers from 0 to 100, LRANGE 0 10 will return 11 elements,
   * that is, rightmost item is included. This may or may not be consistent with behavior of
   * range-related functions in your programming language of choice (think Ruby's Range.new,
   * Array#slice or Python's range() function).
   * <p>
   * LRANGE behavior is consistent with one of Tcl.
   * <p>
   * <b>Out-of-range indexes</b>
   * <p>
   * Indexes out of range will not produce an error: if start is over the end of the list, or start
   * &gt; end, an empty list is returned. If end is over the end of the list Redis will threat it
   * just like the last element of the list.
   * <p>
   * Time complexity: O(start+n) (with n being the length of the range and start being the start
   * offset)
   * @param key
   * @param start
   * @param end
   * @return Multi bulk reply, specifically a list of elements in the specified range.
   */
  @Override
  public List<String> lrange(final String key, final long start, final long end) {
    checkIsInMultiOrPipeline();
    client.lrange(key, start, end);
    return client.getMultiBulkReply();
  }

  /**
   * Trim an existing list so that it will contain only the specified range of elements specified.
   * Start and end are zero-based indexes. 0 is the first element of the list (the list head), 1 the
   * next element and so on.
   * <p>
   * For example LTRIM foobar 0 2 will modify the list stored at foobar key so that only the first
   * three elements of the list will remain.
   * <p>
   * start and end can also be negative numbers indicating offsets from the end of the list. For
   * example -1 is the last element of the list, -2 the penultimate element and so on.
   * <p>
   * Indexes out of range will not produce an error: if start is over the end of the list, or start
   * &gt; end, an empty list is left as value. If end over the end of the list Redis will threat it
   * just like the last element of the list.
   * <p>
   * Hint: the obvious use of LTRIM is together with LPUSH/RPUSH. For example:
   * <p>
   * {@code lpush("mylist", "someelement"); ltrim("mylist", 0, 99); * }
   * <p>
   * The above two commands will push elements in the list taking care that the list will not grow
   * without limits. This is very useful when using Redis to store logs for example. It is important
   * to note that when used in this way LTRIM is an O(1) operation because in the average case just
   * one element is removed from the tail of the list.
   * <p>
   * Time complexity: O(n) (with n being len of list - len of range)
   * @param key
   * @param start
   * @param end
   * @return Status code reply
   */
  @Override
  public String ltrim(final String key, final long start, final long end) {
    checkIsInMultiOrPipeline();
    client.ltrim(key, start, end);
    return client.getStatusCodeReply();
  }

  /**
   * Return the specified element of the list stored at the specified key. 0 is the first element, 1
   * the second and so on. Negative indexes are supported, for example -1 is the last element, -2
   * the penultimate and so on.
   * <p>
   * If the value stored at key is not of list type an error is returned. If the index is out of
   * range a 'nil' reply is returned.
   * <p>
   * Note that even if the average time complexity is O(n) asking for the first or the last element
   * of the list is O(1).
   * <p>
   * Time complexity: O(n) (with n being the length of the list)
   * @param key
   * @param index
   * @return Bulk reply, specifically the requested element
   */
  @Override
  public String lindex(final String key, final long index) {
    checkIsInMultiOrPipeline();
    client.lindex(key, index);
    return client.getBulkReply();
  }

  /**
   * Set a new value as the element at index position of the List at key.
   * <p>
   * Out of range indexes will generate an error.
   * <p>
   * Similarly to other list commands accepting indexes, the index can be negative to access
   * elements starting from the end of the list. So -1 is the last element, -2 is the penultimate,
   * and so forth.
   * <p>
   * <b>Time complexity:</b>
   * <p>
   * O(N) (with N being the length of the list), setting the first or last elements of the list is
   * O(1).
   * @see #lindex(String, long)
   * @param key
   * @param index
   * @param value
   * @return Status code reply
   */
  @Override
  public String lset(final String key, final long index, final String value) {
    checkIsInMultiOrPipeline();
    client.lset(key, index, value);
    return client.getStatusCodeReply();
  }

  /**
   * Remove the first count occurrences of the value element from the list. If count is zero all the
   * elements are removed. If count is negative elements are removed from tail to head, instead to
   * go from head to tail that is the normal behaviour. So for example LREM with count -2 and hello
   * as value to remove against the list (a,b,c,hello,x,hello,hello) will lave the list
   * (a,b,c,hello,x). The number of removed elements is returned as an integer, see below for more
   * information about the returned value. Note that non existing keys are considered like empty
   * lists by LREM, so LREM against non existing keys will always return 0.
   * <p>
   * Time complexity: O(N) (with N being the length of the list)
   * @param key
   * @param count
   * @param value
   * @return Integer Reply, specifically: The number of removed elements if the operation succeeded
   */
  @Override
  public Long lrem(final String key, final long count, final String value) {
    checkIsInMultiOrPipeline();
    client.lrem(key, count, value);
    return client.getIntegerReply();
  }

  /**
   * Atomically return and remove the first (LPOP) or last (RPOP) element of the list. For example
   * if the list contains the elements "a","b","c" LPOP will return "a" and the list will become
   * "b","c".
   * <p>
   * If the key does not exist or the list is already empty the special value 'nil' is returned.
   * @see #rpop(String)
   * @param key
   * @return Bulk reply
   */
  @Override
  public String lpop(final String key) {
    checkIsInMultiOrPipeline();
    client.lpop(key);
    return client.getBulkReply();
  }

  /**
   * Atomically return and remove the first (LPOP) or last (RPOP) element of the list. For example
   * if the list contains the elements "a","b","c" RPOP will return "c" and the list will become
   * "a","b".
   * <p>
   * If the key does not exist or the list is already empty the special value 'nil' is returned.
   * @see #lpop(String)
   * @param key
   * @return Bulk reply
   */
  @Override
  public String rpop(final String key) {
    checkIsInMultiOrPipeline();
    client.rpop(key);
    return client.getBulkReply();
  }

  /**
   * Atomically return and remove the last (tail) element of the srckey list, and push the element
   * as the first (head) element of the dstkey list. For example if the source list contains the
   * elements "a","b","c" and the destination list contains the elements "foo","bar" after an
   * RPOPLPUSH command the content of the two lists will be "a","b" and "c","foo","bar".
   * <p>
   * If the key does not exist or the list is already empty the special value 'nil' is returned. If
   * the srckey and dstkey are the same the operation is equivalent to removing the last element
   * from the list and pusing it as first element of the list, so it's a "list rotation" command.
   * <p>
   * Time complexity: O(1)
   * @param srckey
   * @param dstkey
   * @return Bulk reply
   */
  @Override
  public String rpoplpush(final String srckey, final String dstkey) {
    checkIsInMultiOrPipeline();
    client.rpoplpush(srckey, dstkey);
    return client.getBulkReply();
  }

  /**
   * Add the specified member to the set value stored at key. If member is already a member of the
   * set no operation is performed. If key does not exist a new set with the specified member as
   * sole member is created. If the key exists but does not hold a set value an error is returned.
   * <p>
   * Time complexity O(1)
   * @param key
   * @param members
   * @return Integer reply, specifically: 1 if the new element was added 0 if the element was
   *         already a member of the set
   */
  @Override
  public Long sadd(final String key, final String... members) {
    checkIsInMultiOrPipeline();
    client.sadd(key, members);
    return client.getIntegerReply();
  }

  /**
   * Return all the members (elements) of the set value stored at key. This is just syntax glue for
   * {@link #sinter(String...) SINTER}.
   * <p>
   * Time complexity O(N)
   * @param key
   * @return Multi bulk reply
   */
  @Override
  public Set<String> smembers(final String key) {
    checkIsInMultiOrPipeline();
    client.smembers(key);
    final List<String> members = client.getMultiBulkReply();
    if (members == null) {
      return null;
    }
    return SetFromList.of(members);
  }

  /**
   * Remove the specified member from the set value stored at key. If member was not a member of the
   * set no operation is performed. If key does not hold a set value an error is returned.
   * <p>
   * Time complexity O(1)
   * @param key
   * @param members
   * @return Integer reply, specifically: 1 if the new element was removed 0 if the new element was
   *         not a member of the set
   */
  @Override
  public Long srem(final String key, final String... members) {
    checkIsInMultiOrPipeline();
    client.srem(key, members);
    return client.getIntegerReply();
  }

  /**
   * Remove a random element from a Set returning it as return value. If the Set is empty or the key
   * does not exist, a nil object is returned.
   * <p>
   * The {@link #srandmember(String)} command does a similar work but the returned element is not
   * removed from the Set.
   * <p>
   * Time complexity O(1)
   * @param key
   * @return Bulk reply
   */
  @Override
  public String spop(final String key) {
    checkIsInMultiOrPipeline();
    client.spop(key);
    return client.getBulkReply();
  }

  @Override
  public Set<String> spop(final String key, final long count) {
    checkIsInMultiOrPipeline();
    client.spop(key, count);
    final List<String> members = client.getMultiBulkReply();
    if (members == null) {
      return null;
    }
    return SetFromList.of(members);
  }

  /**
   * Move the specifided member from the set at srckey to the set at dstkey. This operation is
   * atomic, in every given moment the element will appear to be in the source or destination set
   * for accessing clients.
   * <p>
   * If the source set does not exist or does not contain the specified element no operation is
   * performed and zero is returned, otherwise the element is removed from the source set and added
   * to the destination set. On success one is returned, even if the element was already present in
   * the destination set.
   * <p>
   * An error is raised if the source or destination keys contain a non Set value.
   * <p>
   * Time complexity O(1)
   * @param srckey
   * @param dstkey
   * @param member
   * @return Integer reply, specifically: 1 if the element was moved 0 if the element was not found
   *         on the first set and no operation was performed
   */
  @Override
  public Long smove(final String srckey, final String dstkey, final String member) {
    checkIsInMultiOrPipeline();
    client.smove(srckey, dstkey, member);
    return client.getIntegerReply();
  }

  /**
   * Return the set cardinality (number of elements). If the key does not exist 0 is returned, like
   * for empty sets.
   * @param key
   * @return Integer reply, specifically: the cardinality (number of elements) of the set as an
   *         integer.
   */
  @Override
  public Long scard(final String key) {
    checkIsInMultiOrPipeline();
    client.scard(key);
    return client.getIntegerReply();
  }

  /**
   * Return 1 if member is a member of the set stored at key, otherwise 0 is returned.
   * <p>
   * Time complexity O(1)
   * @param key
   * @param member
   * @return Integer reply, specifically: 1 if the element is a member of the set 0 if the element
   *         is not a member of the set OR if the key does not exist
   */
  @Override
  public Boolean sismember(final String key, final String member) {
    checkIsInMultiOrPipeline();
    client.sismember(key, member);
    return client.getIntegerReply() == 1;
  }

  /**
   * Return the members of a set resulting from the intersection of all the sets hold at the
   * specified keys. Like in {@link #lrange(String, long, long) LRANGE} the result is sent to the
   * client as a multi-bulk reply (see the protocol specification for more information). If just a
   * single key is specified, then this command produces the same result as
   * {@link #smembers(String) SMEMBERS}. Actually SMEMBERS is just syntax sugar for SINTER.
   * <p>
   * Non existing keys are considered like empty sets, so if one of the keys is missing an empty set
   * is returned (since the intersection with an empty set always is an empty set).
   * <p>
   * Time complexity O(N*M) worst case where N is the cardinality of the smallest set and M the
   * number of sets
   * @param keys
   * @return Multi bulk reply, specifically the list of common elements.
   */
  @Override
  public Set<String> sinter(final String... keys) {
    checkIsInMultiOrPipeline();
    client.sinter(keys);
    final List<String> members = client.getMultiBulkReply();
    if (members == null) {
      return null;
    }
    return SetFromList.of(members);
  }

  /**
   * This commnad works exactly like {@link #sinter(String...) SINTER} but instead of being returned
   * the resulting set is sotred as dstkey.
   * <p>
   * Time complexity O(N*M) worst case where N is the cardinality of the smallest set and M the
   * number of sets
   * @param dstkey
   * @param keys
   * @return Status code reply
   */
  @Override
  public Long sinterstore(final String dstkey, final String... keys) {
    checkIsInMultiOrPipeline();
    client.sinterstore(dstkey, keys);
    return client.getIntegerReply();
  }

  /**
   * Return the members of a set resulting from the union of all the sets hold at the specified
   * keys. Like in {@link #lrange(String, long, long) LRANGE} the result is sent to the client as a
   * multi-bulk reply (see the protocol specification for more information). If just a single key is
   * specified, then this command produces the same result as {@link #smembers(String) SMEMBERS}.
   * <p>
   * Non existing keys are considered like empty sets.
   * <p>
   * Time complexity O(N) where N is the total number of elements in all the provided sets
   * @param keys
   * @return Multi bulk reply, specifically the list of common elements.
   */
  @Override
  public Set<String> sunion(final String... keys) {
    checkIsInMultiOrPipeline();
    client.sunion(keys);
    final List<String> members = client.getMultiBulkReply();
    if (members == null) {
      return null;
    }
    return SetFromList.of(members);
  }

  /**
   * This command works exactly like {@link #sunion(String...) SUNION} but instead of being returned
   * the resulting set is stored as dstkey. Any existing value in dstkey will be over-written.
   * <p>
   * Time complexity O(N) where N is the total number of elements in all the provided sets
   * @param dstkey
   * @param keys
   * @return Status code reply
   */
  @Override
  public Long sunionstore(final String dstkey, final String... keys) {
    checkIsInMultiOrPipeline();
    client.sunionstore(dstkey, keys);
    return client.getIntegerReply();
  }

  /**
   * Return the difference between the Set stored at key1 and all the Sets key2, ..., keyN
   * <p>
   * <b>Example:</b>
   * 
   * <pre>
   * key1 = [x, a, b, c]
   * key2 = [c]
   * key3 = [a, d]
   * SDIFF key1,key2,key3 =&gt; [x, b]
   * </pre>
   * 
   * Non existing keys are considered like empty sets.
   * <p>
   * <b>Time complexity:</b>
   * <p>
   * O(N) with N being the total number of elements of all the sets
   * @param keys
   * @return Return the members of a set resulting from the difference between the first set
   *         provided and all the successive sets.
   */
  @Override
  public Set<String> sdiff(final String... keys) {
    checkIsInMultiOrPipeline();
    client.sdiff(keys);
    return BuilderFactory.STRING_SET.build(client.getBinaryMultiBulkReply());
  }

  /**
   * This command works exactly like {@link #sdiff(String...) SDIFF} but instead of being returned
   * the resulting set is stored in dstkey.
   * @param dstkey
   * @param keys
   * @return Status code reply
   */
  @Override
  public Long sdiffstore(final String dstkey, final String... keys) {
    checkIsInMultiOrPipeline();
    client.sdiffstore(dstkey, keys);
    return client.getIntegerReply();
  }

  /**
   * Return a random element from a Set, without removing the element. If the Set is empty or the
   * key does not exist, a nil object is returned.
   * <p>
   * The SPOP command does a similar work but the returned element is popped (removed) from the Set.
   * <p>
   * Time complexity O(1)
   * @param key
   * @return Bulk reply
   */
  @Override
  public String srandmember(final String key) {
    checkIsInMultiOrPipeline();
    client.srandmember(key);
    return client.getBulkReply();
  }

  @Override
  public List<String> srandmember(final String key, final int count) {
    checkIsInMultiOrPipeline();
    client.srandmember(key, count);
    return client.getMultiBulkReply();
  }

  /**
   * Add the specified member having the specifeid score to the sorted set stored at key. If member
   * is already a member of the sorted set the score is updated, and the element reinserted in the
   * right position to ensure sorting. If key does not exist a new sorted set with the specified
   * member as sole member is crated. If the key exists but does not hold a sorted set value an
   * error is returned.
   * <p>
   * The score value can be the string representation of a double precision floating point number.
   * <p>
   * Time complexity O(log(N)) with N being the number of elements in the sorted set
   * @param key
   * @param score
   * @param member
   * @return Integer reply, specifically: 1 if the new element was added 0 if the element was
   *         already a member of the sorted set and the score was updated
   */
  @Override
  public Long zadd(final String key, final double score, final String member) {
    checkIsInMultiOrPipeline();
    client.zadd(key, score, member);
    return client.getIntegerReply();
  }

  @Override
  public Long zadd(final String key, final Map<String, Double> scoreMembers) {
    checkIsInMultiOrPipeline();
    client.zadd(key, scoreMembers);
    return client.getIntegerReply();
  }

  @Override
  public Set<String> zrange(final String key, final long start, final long end) {
    checkIsInMultiOrPipeline();
    client.zrange(key, start, end);
    final List<String> members = client.getMultiBulkReply();
    if (members == null) {
      return null;
    }
    return SetFromList.of(members);
  }

  /**
   * Remove the specified member from the sorted set value stored at key. If member was not a member
   * of the set no operation is performed. If key does not not hold a set value an error is
   * returned.
   * <p>
   * Time complexity O(log(N)) with N being the number of elements in the sorted set
   * @param key
   * @param members
   * @return Integer reply, specifically: 1 if the new element was removed 0 if the new element was
   *         not a member of the set
   */
  @Override
  public Long zrem(final String key, final String... members) {
    checkIsInMultiOrPipeline();
    client.zrem(key, members);
    return client.getIntegerReply();
  }

  /**
   * If member already exists in the sorted set adds the increment to its score and updates the
   * position of the element in the sorted set accordingly. If member does not already exist in the
   * sorted set it is added with increment as score (that is, like if the previous score was
   * virtually zero). If key does not exist a new sorted set with the specified member as sole
   * member is crated. If the key exists but does not hold a sorted set value an error is returned.
   * <p>
   * The score value can be the string representation of a double precision floating point number.
   * It's possible to provide a negative value to perform a decrement.
   * <p>
   * For an introduction to sorted sets check the Introduction to Redis data types page.
   * <p>
   * Time complexity O(log(N)) with N being the number of elements in the sorted set
   * @param key
   * @param score
   * @param member
   * @return The new score
   */
  @Override
  public Double zincrby(final String key, final double score, final String member) {
    checkIsInMultiOrPipeline();
    client.zincrby(key, score, member);
    String newscore = client.getBulkReply();
    return Double.valueOf(newscore);
  }

  /**
   * Return the rank (or index) or member in the sorted set at key, with scores being ordered from
   * low to high.
   * <p>
   * When the given member does not exist in the sorted set, the special value 'nil' is returned.
   * The returned rank (or index) of the member is 0-based for both commands.
   * <p>
   * <b>Time complexity:</b>
   * <p>
   * O(log(N))
   * @see #zrevrank(String, String)
   * @param key
   * @param member
   * @return Integer reply or a nil bulk reply, specifically: the rank of the element as an integer
   *         reply if the element exists. A nil bulk reply if there is no such element.
   */
  @Override
  public Long zrank(final String key, final String member) {
    checkIsInMultiOrPipeline();
    client.zrank(key, member);
    return client.getIntegerReply();
  }

  /**
   * Return the rank (or index) or member in the sorted set at key, with scores being ordered from
   * high to low.
   * <p>
   * When the given member does not exist in the sorted set, the special value 'nil' is returned.
   * The returned rank (or index) of the member is 0-based for both commands.
   * <p>
   * <b>Time complexity:</b>
   * <p>
   * O(log(N))
   * @see #zrank(String, String)
   * @param key
   * @param member
   * @return Integer reply or a nil bulk reply, specifically: the rank of the element as an integer
   *         reply if the element exists. A nil bulk reply if there is no such element.
   */
  @Override
  public Long zrevrank(final String key, final String member) {
    checkIsInMultiOrPipeline();
    client.zrevrank(key, member);
    return client.getIntegerReply();
  }

  @Override
  public Set<String> zrevrange(final String key, final long start, final long end) {
    checkIsInMultiOrPipeline();
    client.zrevrange(key, start, end);
    final List<String> members = client.getMultiBulkReply();
    if (members == null) {
      return null;
    }
    return SetFromList.of(members);
  }

  @Override
  public Set<Tuple> zrangeWithScores(final String key, final long start, final long end) {
    checkIsInMultiOrPipeline();
    client.zrangeWithScores(key, start, end);
    return getTupledSet();
  }

  @Override
  public Set<Tuple> zrevrangeWithScores(final String key, final long start, final long end) {
    checkIsInMultiOrPipeline();
    client.zrevrangeWithScores(key, start, end);
    return getTupledSet();
  }

  /**
   * Return the sorted set cardinality (number of elements). If the key does not exist 0 is
   * returned, like for empty sorted sets.
   * <p>
   * Time complexity O(1)
   * @param key
   * @return the cardinality (number of elements) of the set as an integer.
   */
  @Override
  public Long zcard(final String key) {
    checkIsInMultiOrPipeline();
    client.zcard(key);
    return client.getIntegerReply();
  }

  /**
   * Return the score of the specified element of the sorted set at key. If the specified element
   * does not exist in the sorted set, or the key does not exist at all, a special 'nil' value is
   * returned.
   * <p>
   * <b>Time complexity:</b> O(1)
   * @param key
   * @param member
   * @return the score
   */
  @Override
  public Double zscore(final String key, final String member) {
    checkIsInMultiOrPipeline();
    client.zscore(key, member);
    final String score = client.getBulkReply();
    return (score != null ? new Double(score) : null);
  }

  @Override
  public String watch(final String... keys) {
    client.watch(keys);
    return client.getStatusCodeReply();
  }

  /**
   * Sort a Set or a List.
   * <p>
   * Sort the elements contained in the List, Set, or Sorted Set value at key. By default sorting is
   * numeric with elements being compared as double precision floating point numbers. This is the
   * simplest form of SORT.
   * @see #sort(String, String)
   * @see #sort(String, SortingParams)
   * @see #sort(String, SortingParams, String)
   * @param key
   * @return Assuming the Set/List at key contains a list of numbers, the return value will be the
   *         list of numbers ordered from the smallest to the biggest number.
   */
  @Override
  public List<String> sort(final String key) {
    checkIsInMultiOrPipeline();
    client.sort(key);
    return client.getMultiBulkReply();
  }

  /**
   * Sort a Set or a List accordingly to the specified parameters.
   * <p>
   * <b>examples:</b>
   * <p>
   * Given are the following sets and key/values:
   * 
   * <pre>
   * x = [1, 2, 3]
   * y = [a, b, c]
   * 
   * k1 = z
   * k2 = y
   * k3 = x
   * 
   * w1 = 9
   * w2 = 8
   * w3 = 7
   * </pre>
   * 
   * Sort Order:
   * 
   * <pre>
   * sort(x) or sort(x, sp.asc())
   * -&gt; [1, 2, 3]
   * 
   * sort(x, sp.desc())
   * -&gt; [3, 2, 1]
   * 
   * sort(y)
   * -&gt; [c, a, b]
   * 
   * sort(y, sp.alpha())
   * -&gt; [a, b, c]
   * 
   * sort(y, sp.alpha().desc())
   * -&gt; [c, a, b]
   * </pre>
   * 
   * Limit (e.g. for Pagination):
   * 
   * <pre>
   * sort(x, sp.limit(0, 2))
   * -&gt; [1, 2]
   * 
   * sort(y, sp.alpha().desc().limit(1, 2))
   * -&gt; [b, a]
   * </pre>
   * 
   * Sorting by external keys:
   * 
   * <pre>
   * sort(x, sb.by(w*))
   * -&gt; [3, 2, 1]
   * 
   * sort(x, sb.by(w*).desc())
   * -&gt; [1, 2, 3]
   * </pre>
   * 
   * Getting external keys:
   * 
   * <pre>
   * sort(x, sp.by(w*).get(k*))
   * -&gt; [x, y, z]
   * 
   * sort(x, sp.by(w*).get(#).get(k*))
   * -&gt; [3, x, 2, y, 1, z]
   * </pre>
   * @see #sort(String)
   * @see #sort(String, SortingParams, String)
   * @param key
   * @param sortingParameters
   * @return a list of sorted elements.
   */
  @Override
  public List<String> sort(final String key, final SortingParams sortingParameters) {
    checkIsInMultiOrPipeline();
    client.sort(key, sortingParameters);
    return client.getMultiBulkReply();
  }

  /**
   * BLPOP (and BRPOP) is a blocking list pop primitive. You can see this commands as blocking
   * versions of LPOP and RPOP able to block if the specified keys don't exist or contain empty
   * lists.
   * <p>
   * The following is a description of the exact semantic. We describe BLPOP but the two commands
   * are identical, the only difference is that BLPOP pops the element from the left (head) of the
   * list, and BRPOP pops from the right (tail).
   * <p>
   * <b>Non blocking behavior</b>
   * <p>
   * When BLPOP is called, if at least one of the specified keys contain a non empty list, an
   * element is popped from the head of the list and returned to the caller together with the name
   * of the key (BLPOP returns a two elements array, the first element is the key, the second the
   * popped value).
   * <p>
   * Keys are scanned from left to right, so for instance if you issue BLPOP list1 list2 list3 0
   * against a dataset where list1 does not exist but list2 and list3 contain non empty lists, BLPOP
   * guarantees to return an element from the list stored at list2 (since it is the first non empty
   * list starting from the left).
   * <p>
   * <b>Blocking behavior</b>
   * <p>
   * If none of the specified keys exist or contain non empty lists, BLPOP blocks until some other
   * client performs a LPUSH or an RPUSH operation against one of the lists.
   * <p>
   * Once new data is present on one of the lists, the client finally returns with the name of the
   * key unblocking it and the popped value.
   * <p>
   * When blocking, if a non-zero timeout is specified, the client will unblock returning a nil
   * special value if the specified amount of seconds passed without a push operation against at
   * least one of the specified keys.
   * <p>
   * The timeout argument is interpreted as an integer value. A timeout of zero means instead to
   * block forever.
   * <p>
   * <b>Multiple clients blocking for the same keys</b>
   * <p>
   * Multiple clients can block for the same key. They are put into a queue, so the first to be
   * served will be the one that started to wait earlier, in a first-blpopping first-served fashion.
   * <p>
   * <b>blocking POP inside a MULTI/EXEC transaction</b>
   * <p>
   * BLPOP and BRPOP can be used with pipelining (sending multiple commands and reading the replies
   * in batch), but it does not make sense to use BLPOP or BRPOP inside a MULTI/EXEC block (a Redis
   * transaction).
   * <p>
   * The behavior of BLPOP inside MULTI/EXEC when the list is empty is to return a multi-bulk nil
   * reply, exactly what happens when the timeout is reached. If you like science fiction, think at
   * it like if inside MULTI/EXEC the time will flow at infinite speed :)
   * <p>
   * Time complexity: O(1)
   * @see #brpop(int, String...)
   * @param timeout
   * @param keys
   * @return BLPOP returns a two-elements array via a multi bulk reply in order to return both the
   *         unblocking key and the popped value.
   *         <p>
   *         When a non-zero timeout is specified, and the BLPOP operation timed out, the return
   *         value is a nil multi bulk reply. Most client values will return false or nil
   *         accordingly to the programming language used.
   */
  @Override
  public List<String> blpop(final int timeout, final String... keys) {
    return blpop(getArgsAddTimeout(timeout, keys));
  }

  private String[] getArgsAddTimeout(int timeout, String[] keys) {
    final int keyCount = keys.length;
    final String[] args = new String[keyCount + 1];
    for (int at = 0; at != keyCount; ++at) {
      args[at] = keys[at];
    }

    args[keyCount] = String.valueOf(timeout);
    return args;
  }

  @Override
  public List<String> blpop(String... args) {
    checkIsInMultiOrPipeline();
    client.blpop(args);
    client.setTimeoutInfinite();
    try {
      return client.getMultiBulkReply();
    } finally {
      client.rollbackTimeout();
    }
  }

  @Override
  public List<String> brpop(String... args) {
    checkIsInMultiOrPipeline();
    client.brpop(args);
    client.setTimeoutInfinite();
    try {
      return client.getMultiBulkReply();
    } finally {
      client.rollbackTimeout();
    }
  }

  /**
   * Sort a Set or a List accordingly to the specified parameters and store the result at dstkey.
   * @see #sort(String, SortingParams)
   * @see #sort(String)
   * @see #sort(String, String)
   * @param key
   * @param sortingParameters
   * @param dstkey
   * @return The number of elements of the list at dstkey.
   */
  @Override
  public Long sort(final String key, final SortingParams sortingParameters, final String dstkey) {
    checkIsInMultiOrPipeline();
    client.sort(key, sortingParameters, dstkey);
    return client.getIntegerReply();
  }

  /**
   * Sort a Set or a List and Store the Result at dstkey.
   * <p>
   * Sort the elements contained in the List, Set, or Sorted Set value at key and store the result
   * at dstkey. By default sorting is numeric with elements being compared as double precision
   * floating point numbers. This is the simplest form of SORT.
   * @see #sort(String)
   * @see #sort(String, SortingParams)
   * @see #sort(String, SortingParams, String)
   * @param key
   * @param dstkey
   * @return The number of elements of the list at dstkey.
   */
  @Override
  public Long sort(final String key, final String dstkey) {
    checkIsInMultiOrPipeline();
    client.sort(key, dstkey);
    return client.getIntegerReply();
  }

  /**
   * BLPOP (and BRPOP) is a blocking list pop primitive. You can see this commands as blocking
   * versions of LPOP and RPOP able to block if the specified keys don't exist or contain empty
   * lists.
   * <p>
   * The following is a description of the exact semantic. We describe BLPOP but the two commands
   * are identical, the only difference is that BLPOP pops the element from the left (head) of the
   * list, and BRPOP pops from the right (tail).
   * <p>
   * <b>Non blocking behavior</b>
   * <p>
   * When BLPOP is called, if at least one of the specified keys contain a non empty list, an
   * element is popped from the head of the list and returned to the caller together with the name
   * of the key (BLPOP returns a two elements array, the first element is the key, the second the
   * popped value).
   * <p>
   * Keys are scanned from left to right, so for instance if you issue BLPOP list1 list2 list3 0
   * against a dataset where list1 does not exist but list2 and list3 contain non empty lists, BLPOP
   * guarantees to return an element from the list stored at list2 (since it is the first non empty
   * list starting from the left).
   * <p>
   * <b>Blocking behavior</b>
   * <p>
   * If none of the specified keys exist or contain non empty lists, BLPOP blocks until some other
   * client performs a LPUSH or an RPUSH operation against one of the lists.
   * <p>
   * Once new data is present on one of the lists, the client finally returns with the name of the
   * key unblocking it and the popped value.
   * <p>
   * When blocking, if a non-zero timeout is specified, the client will unblock returning a nil
   * special value if the specified amount of seconds passed without a push operation against at
   * least one of the specified keys.
   * <p>
   * The timeout argument is interpreted as an integer value. A timeout of zero means instead to
   * block forever.
   * <p>
   * <b>Multiple clients blocking for the same keys</b>
   * <p>
   * Multiple clients can block for the same key. They are put into a queue, so the first to be
   * served will be the one that started to wait earlier, in a first-blpopping first-served fashion.
   * <p>
   * <b>blocking POP inside a MULTI/EXEC transaction</b>
   * <p>
   * BLPOP and BRPOP can be used with pipelining (sending multiple commands and reading the replies
   * in batch), but it does not make sense to use BLPOP or BRPOP inside a MULTI/EXEC block (a Redis
   * transaction).
   * <p>
   * The behavior of BLPOP inside MULTI/EXEC when the list is empty is to return a multi-bulk nil
   * reply, exactly what happens when the timeout is reached. If you like science fiction, think at
   * it like if inside MULTI/EXEC the time will flow at infinite speed :)
   * <p>
   * Time complexity: O(1)
   * @see #blpop(int, String...)
   * @param timeout
   * @param keys
   * @return BLPOP returns a two-elements array via a multi bulk reply in order to return both the
   *         unblocking key and the popped value.
   *         <p>
   *         When a non-zero timeout is specified, and the BLPOP operation timed out, the return
   *         value is a nil multi bulk reply. Most client values will return false or nil
   *         accordingly to the programming language used.
   */
  @Override
  public List<String> brpop(final int timeout, final String... keys) {
    return brpop(getArgsAddTimeout(timeout, keys));
  }

  @Override
  public Long zcount(final String key, final double min, final double max) {
    checkIsInMultiOrPipeline();
    client.zcount(key, min, max);
    return client.getIntegerReply();
  }

  @Override
  public Long zcount(final String key, final String min, final String max) {
    checkIsInMultiOrPipeline();
    client.zcount(key, min, max);
    return client.getIntegerReply();
  }

  /**
   * Return the all the elements in the sorted set at key with a score between min and max
   * (including elements with score equal to min or max).
   * <p>
   * The elements having the same score are returned sorted lexicographically as ASCII strings (this
   * follows from a property of Redis sorted sets and does not involve further computation).
   * <p>
   * Using the optional {@link #zrangeByScore(String, double, double, int, int) LIMIT} it's possible
   * to get only a range of the matching elements in an SQL-alike way. Note that if offset is large
   * the commands needs to traverse the list for offset elements and this adds up to the O(M)
   * figure.
   * <p>
   * The {@link #zcount(String, double, double) ZCOUNT} command is similar to
   * {@link #zrangeByScore(String, double, double) ZRANGEBYSCORE} but instead of returning the
   * actual elements in the specified interval, it just returns the number of matching elements.
   * <p>
   * <b>Exclusive intervals and infinity</b>
   * <p>
   * min and max can be -inf and +inf, so that you are not required to know what's the greatest or
   * smallest element in order to take, for instance, elements "up to a given value".
   * <p>
   * Also while the interval is for default closed (inclusive) it's possible to specify open
   * intervals prefixing the score with a "(" character, so for instance:
   * <p>
   * {@code ZRANGEBYSCORE zset (1.3 5}
   * <p>
   * Will return all the values with score &gt; 1.3 and &lt;= 5, while for instance:
   * <p>
   * {@code ZRANGEBYSCORE zset (5 (10}
   * <p>
   * Will return all the values with score &gt; 5 and &lt; 10 (5 and 10 excluded).
   * <p>
   * <b>Time complexity:</b>
   * <p>
   * O(log(N))+O(M) with N being the number of elements in the sorted set and M the number of
   * elements returned by the command, so if M is constant (for instance you always ask for the
   * first ten elements with LIMIT) you can consider it O(log(N))
   * @see #zrangeByScore(String, double, double)
   * @see #zrangeByScore(String, double, double, int, int)
   * @see #zrangeByScoreWithScores(String, double, double)
   * @see #zrangeByScoreWithScores(String, String, String)
   * @see #zrangeByScoreWithScores(String, double, double, int, int)
   * @see #zcount(String, double, double)
   * @param key
   * @param min a double or Double.MIN_VALUE for "-inf"
   * @param max a double or Double.MAX_VALUE for "+inf"
   * @return Multi bulk reply specifically a list of elements in the specified score range.
   */
  @Override
  public Set<String> zrangeByScore(final String key, final double min, final double max) {
    checkIsInMultiOrPipeline();
    client.zrangeByScore(key, min, max);
    final List<String> members = client.getMultiBulkReply();
    if (members == null) {
      return null;
    }
    return SetFromList.of(members);
  }

  @Override
  public Set<String> zrangeByScore(final String key, final String min, final String max) {
    checkIsInMultiOrPipeline();
    client.zrangeByScore(key, min, max);
    final List<String> members = client.getMultiBulkReply();
    if (members == null) {
      return null;
    }
    return SetFromList.of(members);
  }

  /**
   * Return the all the elements in the sorted set at key with a score between min and max
   * (including elements with score equal to min or max).
   * <p>
   * The elements having the same score are returned sorted lexicographically as ASCII strings (this
   * follows from a property of Redis sorted sets and does not involve further computation).
   * <p>
   * Using the optional {@link #zrangeByScore(String, double, double, int, int) LIMIT} it's possible
   * to get only a range of the matching elements in an SQL-alike way. Note that if offset is large
   * the commands needs to traverse the list for offset elements and this adds up to the O(M)
   * figure.
   * <p>
   * The {@link #zcount(String, double, double) ZCOUNT} command is similar to
   * {@link #zrangeByScore(String, double, double) ZRANGEBYSCORE} but instead of returning the
   * actual elements in the specified interval, it just returns the number of matching elements.
   * <p>
   * <b>Exclusive intervals and infinity</b>
   * <p>
   * min and max can be -inf and +inf, so that you are not required to know what's the greatest or
   * smallest element in order to take, for instance, elements "up to a given value".
   * <p>
   * Also while the interval is for default closed (inclusive) it's possible to specify open
   * intervals prefixing the score with a "(" character, so for instance:
   * <p>
   * {@code ZRANGEBYSCORE zset (1.3 5}
   * <p>
   * Will return all the values with score &gt; 1.3 and &lt;= 5, while for instance:
   * <p>
   * {@code ZRANGEBYSCORE zset (5 (10}
   * <p>
   * Will return all the values with score &gt; 5 and &lt; 10 (5 and 10 excluded).
   * <p>
   * <b>Time complexity:</b>
   * <p>
   * O(log(N))+O(M) with N being the number of elements in the sorted set and M the number of
   * elements returned by the command, so if M is constant (for instance you always ask for the
   * first ten elements with LIMIT) you can consider it O(log(N))
   * @see #zrangeByScore(String, double, double)
   * @see #zrangeByScore(String, double, double, int, int)
   * @see #zrangeByScoreWithScores(String, double, double)
   * @see #zrangeByScoreWithScores(String, double, double, int, int)
   * @see #zcount(String, double, double)
   * @param key
   * @param min
   * @param max
   * @return Multi bulk reply specifically a list of elements in the specified score range.
   */
  @Override
  public Set<String> zrangeByScore(final String key, final double min, final double max,
      final int offset, final int count) {
    checkIsInMultiOrPipeline();
    client.zrangeByScore(key, min, max, offset, count);
    final List<String> members = client.getMultiBulkReply();
    if (members == null) {
      return null;
    }
    return SetFromList.of(members);
  }

  @Override
  public Set<String> zrangeByScore(final String key, final String min, final String max,
      final int offset, final int count) {
    checkIsInMultiOrPipeline();
    client.zrangeByScore(key, min, max, offset, count);
    final List<String> members = client.getMultiBulkReply();
    if (members == null) {
      return null;
    }
    return SetFromList.of(members);
  }

  /**
   * Return the all the elements in the sorted set at key with a score between min and max
   * (including elements with score equal to min or max).
   * <p>
   * The elements having the same score are returned sorted lexicographically as ASCII strings (this
   * follows from a property of Redis sorted sets and does not involve further computation).
   * <p>
   * Using the optional {@link #zrangeByScore(String, double, double, int, int) LIMIT} it's possible
   * to get only a range of the matching elements in an SQL-alike way. Note that if offset is large
   * the commands needs to traverse the list for offset elements and this adds up to the O(M)
   * figure.
   * <p>
   * The {@link #zcount(String, double, double) ZCOUNT} command is similar to
   * {@link #zrangeByScore(String, double, double) ZRANGEBYSCORE} but instead of returning the
   * actual elements in the specified interval, it just returns the number of matching elements.
   * <p>
   * <b>Exclusive intervals and infinity</b>
   * <p>
   * min and max can be -inf and +inf, so that you are not required to know what's the greatest or
   * smallest element in order to take, for instance, elements "up to a given value".
   * <p>
   * Also while the interval is for default closed (inclusive) it's possible to specify open
   * intervals prefixing the score with a "(" character, so for instance:
   * <p>
   * {@code ZRANGEBYSCORE zset (1.3 5}
   * <p>
   * Will return all the values with score &gt; 1.3 and &lt;= 5, while for instance:
   * <p>
   * {@code ZRANGEBYSCORE zset (5 (10}
   * <p>
   * Will return all the values with score &gt; 5 and &lt; 10 (5 and 10 excluded).
   * <p>
   * <b>Time complexity:</b>
   * <p>
   * O(log(N))+O(M) with N being the number of elements in the sorted set and M the number of
   * elements returned by the command, so if M is constant (for instance you always ask for the
   * first ten elements with LIMIT) you can consider it O(log(N))
   * @see #zrangeByScore(String, double, double)
   * @see #zrangeByScore(String, double, double, int, int)
   * @see #zrangeByScoreWithScores(String, double, double)
   * @see #zrangeByScoreWithScores(String, double, double, int, int)
   * @see #zcount(String, double, double)
   * @param key
   * @param min
   * @param max
   * @return Multi bulk reply specifically a list of elements in the specified score range.
   */
  @Override
  public Set<Tuple> zrangeByScoreWithScores(final String key, final double min, final double max) {
    checkIsInMultiOrPipeline();
    client.zrangeByScoreWithScores(key, min, max);
    return getTupledSet();
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(final String key, final String min, final String max) {
    checkIsInMultiOrPipeline();
    client.zrangeByScoreWithScores(key, min, max);
    return getTupledSet();
  }

  /**
   * Return the all the elements in the sorted set at key with a score between min and max
   * (including elements with score equal to min or max).
   * <p>
   * The elements having the same score are returned sorted lexicographically as ASCII strings (this
   * follows from a property of Redis sorted sets and does not involve further computation).
   * <p>
   * Using the optional {@link #zrangeByScore(String, double, double, int, int) LIMIT} it's possible
   * to get only a range of the matching elements in an SQL-alike way. Note that if offset is large
   * the commands needs to traverse the list for offset elements and this adds up to the O(M)
   * figure.
   * <p>
   * The {@link #zcount(String, double, double) ZCOUNT} command is similar to
   * {@link #zrangeByScore(String, double, double) ZRANGEBYSCORE} but instead of returning the
   * actual elements in the specified interval, it just returns the number of matching elements.
   * <p>
   * <b>Exclusive intervals and infinity</b>
   * <p>
   * min and max can be -inf and +inf, so that you are not required to know what's the greatest or
   * smallest element in order to take, for instance, elements "up to a given value".
   * <p>
   * Also while the interval is for default closed (inclusive) it's possible to specify open
   * intervals prefixing the score with a "(" character, so for instance:
   * <p>
   * {@code ZRANGEBYSCORE zset (1.3 5}
   * <p>
   * Will return all the values with score &gt; 1.3 and &lt;= 5, while for instance:
   * <p>
   * {@code ZRANGEBYSCORE zset (5 (10}
   * <p>
   * Will return all the values with score &gt; 5 and &lt; 10 (5 and 10 excluded).
   * <p>
   * <b>Time complexity:</b>
   * <p>
   * O(log(N))+O(M) with N being the number of elements in the sorted set and M the number of
   * elements returned by the command, so if M is constant (for instance you always ask for the
   * first ten elements with LIMIT) you can consider it O(log(N))
   * @see #zrangeByScore(String, double, double)
   * @see #zrangeByScore(String, double, double, int, int)
   * @see #zrangeByScoreWithScores(String, double, double)
   * @see #zrangeByScoreWithScores(String, double, double, int, int)
   * @see #zcount(String, double, double)
   * @param key
   * @param min
   * @param max
   * @return Multi bulk reply specifically a list of elements in the specified score range.
   */
  @Override
  public Set<Tuple> zrangeByScoreWithScores(final String key, final double min, final double max,
      final int offset, final int count) {
    checkIsInMultiOrPipeline();
    client.zrangeByScoreWithScores(key, min, max, offset, count);
    return getTupledSet();
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(final String key, final String min, final String max,
      final int offset, final int count) {
    checkIsInMultiOrPipeline();
    client.zrangeByScoreWithScores(key, min, max, offset, count);
    return getTupledSet();
  }

  private Set<Tuple> getTupledSet() {
    checkIsInMultiOrPipeline();
    List<String> membersWithScores = client.getMultiBulkReply();
    if (membersWithScores == null) {
      return null;
    }
    if (membersWithScores.size() == 0) {
      return Collections.emptySet();
    }
    Set<Tuple> set = new LinkedHashSet<Tuple>(membersWithScores.size() / 2, 1.0f);
    Iterator<String> iterator = membersWithScores.iterator();
    while (iterator.hasNext()) {
      set.add(new Tuple(iterator.next(), Double.valueOf(iterator.next())));
    }
    return set;
  }

  @Override
  public Set<String> zrevrangeByScore(final String key, final double max, final double min) {
    checkIsInMultiOrPipeline();
    client.zrevrangeByScore(key, max, min);
    final List<String> members = client.getMultiBulkReply();
    if (members == null) {
      return null;
    }
    return SetFromList.of(members);
  }

  @Override
  public Set<String> zrevrangeByScore(final String key, final String max, final String min) {
    checkIsInMultiOrPipeline();
    client.zrevrangeByScore(key, max, min);
    final List<String> members = client.getMultiBulkReply();
    if (members == null) {
      return null;
    }
    return SetFromList.of(members);
  }

  @Override
  public Set<String> zrevrangeByScore(final String key, final double max, final double min,
      final int offset, final int count) {
    checkIsInMultiOrPipeline();
    client.zrevrangeByScore(key, max, min, offset, count);
    final List<String> members = client.getMultiBulkReply();
    if (members == null) {
      return null;
    }
    return SetFromList.of(members);
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(final String key, final double max, final double min) {
    checkIsInMultiOrPipeline();
    client.zrevrangeByScoreWithScores(key, max, min);
    return getTupledSet();
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(final String key, final double max,
      final double min, final int offset, final int count) {
    checkIsInMultiOrPipeline();
    client.zrevrangeByScoreWithScores(key, max, min, offset, count);
    return getTupledSet();
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(final String key, final String max,
      final String min, final int offset, final int count) {
    checkIsInMultiOrPipeline();
    client.zrevrangeByScoreWithScores(key, max, min, offset, count);
    return getTupledSet();
  }

  @Override
  public Set<String> zrevrangeByScore(final String key, final String max, final String min,
      final int offset, final int count) {
    checkIsInMultiOrPipeline();
    client.zrevrangeByScore(key, max, min, offset, count);
    final List<String> members = client.getMultiBulkReply();
    if (members == null) {
      return null;
    }
    return SetFromList.of(members);
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(final String key, final String max, final String min) {
    checkIsInMultiOrPipeline();
    client.zrevrangeByScoreWithScores(key, max, min);
    return getTupledSet();
  }

  /**
   * Remove all elements in the sorted set at key with rank between start and end. Start and end are
   * 0-based with rank 0 being the element with the lowest score. Both start and end can be negative
   * numbers, where they indicate offsets starting at the element with the highest rank. For
   * example: -1 is the element with the highest score, -2 the element with the second highest score
   * and so forth.
   * <p>
   * <b>Time complexity:</b> O(log(N))+O(M) with N being the number of elements in the sorted set
   * and M the number of elements removed by the operation
   */
  @Override
  public Long zremrangeByRank(final String key, final long start, final long end) {
    checkIsInMultiOrPipeline();
    client.zremrangeByRank(key, start, end);
    return client.getIntegerReply();
  }

  /**
   * Remove all the elements in the sorted set at key with a score between min and max (including
   * elements with score equal to min or max).
   * <p>
   * <b>Time complexity:</b>
   * <p>
   * O(log(N))+O(M) with N being the number of elements in the sorted set and M the number of
   * elements removed by the operation
   * @param key
   * @param start
   * @param end
   * @return Integer reply, specifically the number of elements removed.
   */
  @Override
  public Long zremrangeByScore(final String key, final double start, final double end) {
    checkIsInMultiOrPipeline();
    client.zremrangeByScore(key, start, end);
    return client.getIntegerReply();
  }

  @Override
  public Long zremrangeByScore(final String key, final String start, final String end) {
    checkIsInMultiOrPipeline();
    client.zremrangeByScore(key, start, end);
    return client.getIntegerReply();
  }

  /**
   * Creates a union or intersection of N sorted sets given by keys k1 through kN, and stores it at
   * dstkey. It is mandatory to provide the number of input keys N, before passing the input keys
   * and the other (optional) arguments.
   * <p>
   * As the terms imply, the {@link #zinterstore(String, String...) ZINTERSTORE} command requires an
   * element to be present in each of the given inputs to be inserted in the result. The
   * {@link #zunionstore(String, String...) ZUNIONSTORE} command inserts all elements across all
   * inputs.
   * <p>
   * Using the WEIGHTS option, it is possible to add weight to each input sorted set. This means
   * that the score of each element in the sorted set is first multiplied by this weight before
   * being passed to the aggregation. When this option is not given, all weights default to 1.
   * <p>
   * With the AGGREGATE option, it's possible to specify how the results of the union or
   * intersection are aggregated. This option defaults to SUM, where the score of an element is
   * summed across the inputs where it exists. When this option is set to be either MIN or MAX, the
   * resulting set will contain the minimum or maximum score of an element across the inputs where
   * it exists.
   * <p>
   * <b>Time complexity:</b> O(N) + O(M log(M)) with N being the sum of the sizes of the input
   * sorted sets, and M being the number of elements in the resulting sorted set
   * @see #zunionstore(String, String...)
   * @see #zunionstore(String, ZParams, String...)
   * @see #zinterstore(String, String...)
   * @see #zinterstore(String, ZParams, String...)
   * @param dstkey
   * @param sets
   * @return Integer reply, specifically the number of elements in the sorted set at dstkey
   */
  @Override
  public Long zunionstore(final String dstkey, final String... sets) {
    checkIsInMultiOrPipeline();
    client.zunionstore(dstkey, sets);
    return client.getIntegerReply();
  }

  /**
   * Creates a union or intersection of N sorted sets given by keys k1 through kN, and stores it at
   * dstkey. It is mandatory to provide the number of input keys N, before passing the input keys
   * and the other (optional) arguments.
   * <p>
   * As the terms imply, the {@link #zinterstore(String, String...) ZINTERSTORE} command requires an
   * element to be present in each of the given inputs to be inserted in the result. The
   * {@link #zunionstore(String, String...) ZUNIONSTORE} command inserts all elements across all
   * inputs.
   * <p>
   * Using the WEIGHTS option, it is possible to add weight to each input sorted set. This means
   * that the score of each element in the sorted set is first multiplied by this weight before
   * being passed to the aggregation. When this option is not given, all weights default to 1.
   * <p>
   * With the AGGREGATE option, it's possible to specify how the results of the union or
   * intersection are aggregated. This option defaults to SUM, where the score of an element is
   * summed across the inputs where it exists. When this option is set to be either MIN or MAX, the
   * resulting set will contain the minimum or maximum score of an element across the inputs where
   * it exists.
   * <p>
   * <b>Time complexity:</b> O(N) + O(M log(M)) with N being the sum of the sizes of the input
   * sorted sets, and M being the number of elements in the resulting sorted set
   * @see #zunionstore(String, String...)
   * @see #zunionstore(String, ZParams, String...)
   * @see #zinterstore(String, String...)
   * @see #zinterstore(String, ZParams, String...)
   * @param dstkey
   * @param sets
   * @param params
   * @return Integer reply, specifically the number of elements in the sorted set at dstkey
   */
  @Override
  public Long zunionstore(final String dstkey, final ZParams params, final String... sets) {
    checkIsInMultiOrPipeline();
    client.zunionstore(dstkey, params, sets);
    return client.getIntegerReply();
  }

  /**
   * Creates a union or intersection of N sorted sets given by keys k1 through kN, and stores it at
   * dstkey. It is mandatory to provide the number of input keys N, before passing the input keys
   * and the other (optional) arguments.
   * <p>
   * As the terms imply, the {@link #zinterstore(String, String...) ZINTERSTORE} command requires an
   * element to be present in each of the given inputs to be inserted in the result. The
   * {@link #zunionstore(String, String...) ZUNIONSTORE} command inserts all elements across all
   * inputs.
   * <p>
   * Using the WEIGHTS option, it is possible to add weight to each input sorted set. This means
   * that the score of each element in the sorted set is first multiplied by this weight before
   * being passed to the aggregation. When this option is not given, all weights default to 1.
   * <p>
   * With the AGGREGATE option, it's possible to specify how the results of the union or
   * intersection are aggregated. This option defaults to SUM, where the score of an element is
   * summed across the inputs where it exists. When this option is set to be either MIN or MAX, the
   * resulting set will contain the minimum or maximum score of an element across the inputs where
   * it exists.
   * <p>
   * <b>Time complexity:</b> O(N) + O(M log(M)) with N being the sum of the sizes of the input
   * sorted sets, and M being the number of elements in the resulting sorted set
   * @see #zunionstore(String, String...)
   * @see #zunionstore(String, ZParams, String...)
   * @see #zinterstore(String, String...)
   * @see #zinterstore(String, ZParams, String...)
   * @param dstkey
   * @param sets
   * @return Integer reply, specifically the number of elements in the sorted set at dstkey
   */
  @Override
  public Long zinterstore(final String dstkey, final String... sets) {
    checkIsInMultiOrPipeline();
    client.zinterstore(dstkey, sets);
    return client.getIntegerReply();
  }

  /**
   * Creates a union or intersection of N sorted sets given by keys k1 through kN, and stores it at
   * dstkey. It is mandatory to provide the number of input keys N, before passing the input keys
   * and the other (optional) arguments.
   * <p>
   * As the terms imply, the {@link #zinterstore(String, String...) ZINTERSTORE} command requires an
   * element to be present in each of the given inputs to be inserted in the result. The
   * {@link #zunionstore(String, String...) ZUNIONSTORE} command inserts all elements across all
   * inputs.
   * <p>
   * Using the WEIGHTS option, it is possible to add weight to each input sorted set. This means
   * that the score of each element in the sorted set is first multiplied by this weight before
   * being passed to the aggregation. When this option is not given, all weights default to 1.
   * <p>
   * With the AGGREGATE option, it's possible to specify how the results of the union or
   * intersection are aggregated. This option defaults to SUM, where the score of an element is
   * summed across the inputs where it exists. When this option is set to be either MIN or MAX, the
   * resulting set will contain the minimum or maximum score of an element across the inputs where
   * it exists.
   * <p>
   * <b>Time complexity:</b> O(N) + O(M log(M)) with N being the sum of the sizes of the input
   * sorted sets, and M being the number of elements in the resulting sorted set
   * @see #zunionstore(String, String...)
   * @see #zunionstore(String, ZParams, String...)
   * @see #zinterstore(String, String...)
   * @see #zinterstore(String, ZParams, String...)
   * @param dstkey
   * @param sets
   * @param params
   * @return Integer reply, specifically the number of elements in the sorted set at dstkey
   */
  @Override
  public Long zinterstore(final String dstkey, final ZParams params, final String... sets) {
    checkIsInMultiOrPipeline();
    client.zinterstore(dstkey, params, sets);
    return client.getIntegerReply();
  }

  @Override
  public Long zlexcount(final String key, final String min, final String max) {
    checkIsInMultiOrPipeline();
    client.zlexcount(key, min, max);
    return client.getIntegerReply();
  }

  @Override
  public Set<String> zrangeByLex(final String key, final String min, final String max) {
    checkIsInMultiOrPipeline();
    client.zrangeByLex(key, min, max);
    final List<String> members = client.getMultiBulkReply();
    if (members == null) {
      return null;
    }
    return SetFromList.of(members);
  }

  @Override
  public Set<String> zrangeByLex(final String key, final String min, final String max,
      final int offset, final int count) {
    checkIsInMultiOrPipeline();
    client.zrangeByLex(key, min, max, offset, count);
    final List<String> members = client.getMultiBulkReply();
    if (members == null) {
      return null;
    }
    return SetFromList.of(members);
  }

  @Override
  public Set<String> zrevrangeByLex(String key, String max, String min) {
    checkIsInMultiOrPipeline();
    client.zrevrangeByLex(key, max, min);
    final List<String> members = client.getMultiBulkReply();
    if (members == null) {
      return null;
    }
    return SetFromList.of(members);
  }

  @Override
  public Set<String> zrevrangeByLex(String key, String max, String min, int offset, int count) {
    checkIsInMultiOrPipeline();
    client.zrevrangeByLex(key, max, min, offset, count);
    final List<String> members = client.getMultiBulkReply();
    if (members == null) {
      return null;
    }
    return SetFromList.of(members);
  }

  @Override
  public Long zremrangeByLex(final String key, final String min, final String max) {
    checkIsInMultiOrPipeline();
    client.zremrangeByLex(key, min, max);
    return client.getIntegerReply();
  }

  @Override
  public Long strlen(final String key) {
    client.strlen(key);
    return client.getIntegerReply();
  }

  @Override
  public Long lpushx(final String key, final String... string) {
    client.lpushx(key, string);
    return client.getIntegerReply();
  }

  /**
   * Undo a {@link #expire(String, int) expire} at turning the expire key into a normal key.
   * <p>
   * Time complexity: O(1)
   * @param key
   * @return Integer reply, specifically: 1: the key is now persist. 0: the key is not persist (only
   *         happens when key not set).
   */
  @Override
  public Long persist(final String key) {
    client.persist(key);
    return client.getIntegerReply();
  }

  @Override
  public Long rpushx(final String key, final String... string) {
    client.rpushx(key, string);
    return client.getIntegerReply();
  }

  @Override
  public String echo(final String string) {
    client.echo(string);
    return client.getBulkReply();
  }

  @Override
  public Long linsert(final String key, final LIST_POSITION where, final String pivot,
      final String value) {
    client.linsert(key, where, pivot, value);
    return client.getIntegerReply();
  }

  /**
   * Pop a value from a list, push it to another list and return it; or block until one is available
   * @param source
   * @param destination
   * @param timeout
   * @return the element
   */
  @Override
  public String brpoplpush(String source, String destination, int timeout) {
    client.brpoplpush(source, destination, timeout);
    client.setTimeoutInfinite();
    try {
      return client.getBulkReply();
    } finally {
      client.rollbackTimeout();
    }
  }

  /**
   * Sets or clears the bit at offset in the string value stored at key
   * @param key
   * @param offset
   * @param value
   * @return
   */
  @Override
  public Boolean setbit(String key, long offset, boolean value) {
    client.setbit(key, offset, value);
    return client.getIntegerReply() == 1;
  }

  @Override
  public Boolean setbit(String key, long offset, String value) {
    client.setbit(key, offset, value);
    return client.getIntegerReply() == 1;
  }

  /**
   * Returns the bit value at offset in the string value stored at key
   * @param key
   * @param offset
   * @return
   */
  @Override
  public Boolean getbit(String key, long offset) {
    client.getbit(key, offset);
    return client.getIntegerReply() == 1;
  }

  @Override
  public Long setrange(String key, long offset, String value) {
    client.setrange(key, offset, value);
    return client.getIntegerReply();
  }

  @Override
  public String getrange(String key, long startOffset, long endOffset) {
    client.getrange(key, startOffset, endOffset);
    return client.getBulkReply();
  }

  @Override
  public Long bitpos(final String key, final boolean value) {
    return bitpos(key, value, new BitPosParams());
  }

  @Override
  public Long bitpos(final String key, final boolean value, final BitPosParams params) {
    client.bitpos(key, value, params);
    return client.getIntegerReply();
  }

  /**
   * Retrieve the configuration of a running Redis server. Not all the configuration parameters are
   * supported.
   * <p>
   * CONFIG GET returns the current configuration parameters. This sub command only accepts a single
   * argument, that is glob style pattern. All the configuration parameters matching this parameter
   * are reported as a list of key-value pairs.
   * <p>
   * <b>Example:</b>
   * 
   * <pre>
   * $ redis-cli config get '*'
   * 1. "dbfilename"
   * 2. "dump.rdb"
   * 3. "requirepass"
   * 4. (nil)
   * 5. "masterauth"
   * 6. (nil)
   * 7. "maxmemory"
   * 8. "0\n"
   * 9. "appendfsync"
   * 10. "everysec"
   * 11. "save"
   * 12. "3600 1 300 100 60 10000"
   * 
   * $ redis-cli config get 'm*'
   * 1. "masterauth"
   * 2. (nil)
   * 3. "maxmemory"
   * 4. "0\n"
   * </pre>
   * @param pattern
   * @return Bulk reply.
   */
  @Override
  public List<String> configGet(final String pattern) {
    client.configGet(pattern);
    return client.getMultiBulkReply();
  }

  /**
   * Alter the configuration of a running Redis server. Not all the configuration parameters are
   * supported.
   * <p>
   * The list of configuration parameters supported by CONFIG SET can be obtained issuing a
   * {@link #configGet(String) CONFIG GET *} command.
   * <p>
   * The configuration set using CONFIG SET is immediately loaded by the Redis server that will
   * start acting as specified starting from the next command.
   * <p>
   * <b>Parameters value format</b>
   * <p>
   * The value of the configuration parameter is the same as the one of the same parameter in the
   * Redis configuration file, with the following exceptions:
   * <p>
   * <ul>
   * <li>The save paramter is a list of space-separated integers. Every pair of integers specify the
   * time and number of changes limit to trigger a save. For instance the command CONFIG SET save
   * "3600 10 60 10000" will configure the server to issue a background saving of the RDB file every
   * 3600 seconds if there are at least 10 changes in the dataset, and every 60 seconds if there are
   * at least 10000 changes. To completely disable automatic snapshots just set the parameter as an
   * empty string.
   * <li>All the integer parameters representing memory are returned and accepted only using bytes
   * as unit.
   * </ul>
   * @param parameter
   * @param value
   * @return Status code reply
   */
  @Override
  public String configSet(final String parameter, final String value) {
    client.configSet(parameter, value);
    return client.getStatusCodeReply();
  }

  @Override
  public Object eval(String script, int keyCount, String... params) {
    client.setTimeoutInfinite();
    try {
      client.eval(script, keyCount, params);
      return getEvalResult();
    } finally {
      client.rollbackTimeout();
    }
  }

  @Override
  public void subscribe(final JedisPubSub jedisPubSub, final String... channels) {
    client.setTimeoutInfinite();
    try {
      jedisPubSub.proceed(client, channels);
    } finally {
      client.rollbackTimeout();
    }
  }

  @Override
  public Long publish(final String channel, final String message) {
    checkIsInMultiOrPipeline();
    connect();
    client.publish(channel, message);
    return client.getIntegerReply();
  }

  @Override
  public void psubscribe(final JedisPubSub jedisPubSub, final String... patterns) {
    checkIsInMultiOrPipeline();
    client.setTimeoutInfinite();
    try {
      jedisPubSub.proceedWithPatterns(client, patterns);
    } finally {
      client.rollbackTimeout();
    }
  }

  protected static String[] getParams(List<String> keys, List<String> args) {
    int keyCount = keys.size();
    int argCount = args.size();

    String[] params = new String[keyCount + args.size()];

    for (int i = 0; i < keyCount; i++)
      params[i] = keys.get(i);

    for (int i = 0; i < argCount; i++)
      params[keyCount + i] = args.get(i);

    return params;
  }

  @Override
  public Object eval(String script, List<String> keys, List<String> args) {
    return eval(script, keys.size(), getParams(keys, args));
  }

  @Override
  public Object eval(String script) {
    return eval(script, 0);
  }

  @Override
  public Object evalsha(String script) {
    return evalsha(script, 0);
  }

  private Object getEvalResult() {
    return evalResult(client.getOne());
  }

  private Object evalResult(Object result) {
    if (result instanceof byte[]) return SafeEncoder.encode((byte[]) result);

    if (result instanceof List<?>) {
      List<?> list = (List<?>) result;
      List<Object> listResult = new ArrayList<Object>(list.size());
      for (Object bin : list) {
        listResult.add(evalResult(bin));
      }

      return listResult;
    }

    return result;
  }

  @Override
  public Object evalsha(String sha1, List<String> keys, List<String> args) {
    return evalsha(sha1, keys.size(), getParams(keys, args));
  }

  @Override
  public Object evalsha(String sha1, int keyCount, String... params) {
    checkIsInMultiOrPipeline();
    client.evalsha(sha1, keyCount, params);
    return getEvalResult();
  }

  @Override
  public Boolean scriptExists(String sha1) {
    String[] a = new String[1];
    a[0] = sha1;
    return scriptExists(a).get(0);
  }

  @Override
  public List<Boolean> scriptExists(String... sha1) {
    client.scriptExists(sha1);
    List<Long> result = client.getIntegerMultiBulkReply();
    List<Boolean> exists = new ArrayList<Boolean>();

    for (Long value : result)
      exists.add(value == 1);

    return exists;
  }

  @Override
  public String scriptLoad(String script) {
    client.scriptLoad(script);
    return client.getBulkReply();
  }

  @Override
  public List<Slowlog> slowlogGet() {
    client.slowlogGet();
    return Slowlog.from(client.getObjectMultiBulkReply());
  }

  @Override
  public List<Slowlog> slowlogGet(long entries) {
    client.slowlogGet(entries);
    return Slowlog.from(client.getObjectMultiBulkReply());
  }

  @Override
  public Long objectRefcount(String string) {
    client.objectRefcount(string);
    return client.getIntegerReply();
  }

  @Override
  public String objectEncoding(String string) {
    client.objectEncoding(string);
    return client.getBulkReply();
  }

  @Override
  public Long objectIdletime(String string) {
    client.objectIdletime(string);
    return client.getIntegerReply();
  }

  @Override
  public Long bitcount(final String key) {
    client.bitcount(key);
    return client.getIntegerReply();
  }

  @Override
  public Long bitcount(final String key, long start, long end) {
    client.bitcount(key, start, end);
    return client.getIntegerReply();
  }

  @Override
  public Long bitop(BitOP op, final String destKey, String... srcKeys) {
    client.bitop(op, destKey, srcKeys);
    return client.getIntegerReply();
  }

  /**
   * <pre>
   * redis 127.0.0.1:26381&gt; sentinel masters
   * 1)  1) "name"
   *     2) "mymaster"
   *     3) "ip"
   *     4) "127.0.0.1"
   *     5) "port"
   *     6) "6379"
   *     7) "runid"
   *     8) "93d4d4e6e9c06d0eea36e27f31924ac26576081d"
   *     9) "flags"
   *    10) "master"
   *    11) "pending-commands"
   *    12) "0"
   *    13) "last-ok-ping-reply"
   *    14) "423"
   *    15) "last-ping-reply"
   *    16) "423"
   *    17) "info-refresh"
   *    18) "6107"
   *    19) "num-slaves"
   *    20) "1"
   *    21) "num-other-sentinels"
   *    22) "2"
   *    23) "quorum"
   *    24) "2"
   * 
   * </pre>
   * @return
   */
  @Override
  @SuppressWarnings("rawtypes")
  public List<Map<String, String>> sentinelMasters() {
    client.sentinel(Protocol.SENTINEL_MASTERS);
    final List<Object> reply = client.getObjectMultiBulkReply();

    final List<Map<String, String>> masters = new ArrayList<Map<String, String>>();
    for (Object obj : reply) {
      masters.add(BuilderFactory.STRING_MAP.build((List) obj));
    }
    return masters;
  }

  /**
   * <pre>
   * redis 127.0.0.1:26381&gt; sentinel get-master-addr-by-name mymaster
   * 1) "127.0.0.1"
   * 2) "6379"
   * </pre>
   * @param masterName
   * @return two elements list of strings : host and port.
   */
  @Override
  public List<String> sentinelGetMasterAddrByName(String masterName) {
    client.sentinel(Protocol.SENTINEL_GET_MASTER_ADDR_BY_NAME, masterName);
    final List<Object> reply = client.getObjectMultiBulkReply();
    return BuilderFactory.STRING_LIST.build(reply);
  }

  /**
   * <pre>
   * redis 127.0.0.1:26381&gt; sentinel reset mymaster
   * (integer) 1
   * </pre>
   * @param pattern
   * @return
   */
  @Override
  public Long sentinelReset(String pattern) {
    client.sentinel(Protocol.SENTINEL_RESET, pattern);
    return client.getIntegerReply();
  }

  /**
   * <pre>
   * redis 127.0.0.1:26381&gt; sentinel slaves mymaster
   * 1)  1) "name"
   *     2) "127.0.0.1:6380"
   *     3) "ip"
   *     4) "127.0.0.1"
   *     5) "port"
   *     6) "6380"
   *     7) "runid"
   *     8) "d7f6c0ca7572df9d2f33713df0dbf8c72da7c039"
   *     9) "flags"
   *    10) "slave"
   *    11) "pending-commands"
   *    12) "0"
   *    13) "last-ok-ping-reply"
   *    14) "47"
   *    15) "last-ping-reply"
   *    16) "47"
   *    17) "info-refresh"
   *    18) "657"
   *    19) "master-link-down-time"
   *    20) "0"
   *    21) "master-link-status"
   *    22) "ok"
   *    23) "master-host"
   *    24) "localhost"
   *    25) "master-port"
   *    26) "6379"
   *    27) "slave-priority"
   *    28) "100"
   * </pre>
   * @param masterName
   * @return
   */
  @Override
  @SuppressWarnings("rawtypes")
  public List<Map<String, String>> sentinelSlaves(String masterName) {
    client.sentinel(Protocol.SENTINEL_SLAVES, masterName);
    final List<Object> reply = client.getObjectMultiBulkReply();

    final List<Map<String, String>> slaves = new ArrayList<Map<String, String>>();
    for (Object obj : reply) {
      slaves.add(BuilderFactory.STRING_MAP.build((List) obj));
    }
    return slaves;
  }

  @Override
  public String sentinelFailover(String masterName) {
    client.sentinel(Protocol.SENTINEL_FAILOVER, masterName);
    return client.getStatusCodeReply();
  }

  @Override
  public String sentinelMonitor(String masterName, String ip, int port, int quorum) {
    client.sentinel(Protocol.SENTINEL_MONITOR, masterName, ip, String.valueOf(port),
      String.valueOf(quorum));
    return client.getStatusCodeReply();
  }

  @Override
  public String sentinelRemove(String masterName) {
    client.sentinel(Protocol.SENTINEL_REMOVE, masterName);
    return client.getStatusCodeReply();
  }

  @Override
  public String sentinelSet(String masterName, Map<String, String> parameterMap) {
    int index = 0;
    int paramsLength = parameterMap.size() * 2 + 2;
    String[] params = new String[paramsLength];

    params[index++] = Protocol.SENTINEL_SET;
    params[index++] = masterName;
    for (Entry<String, String> entry : parameterMap.entrySet()) {
      params[index++] = entry.getKey();
      params[index++] = entry.getValue();
    }

    client.sentinel(params);
    return client.getStatusCodeReply();
  }

  public byte[] dump(final String key) {
    checkIsInMultiOrPipeline();
    client.dump(key);
    return client.getBinaryBulkReply();
  }

  public String restore(final String key, final int ttl, final byte[] serializedValue) {
    checkIsInMultiOrPipeline();
    client.restore(key, ttl, serializedValue);
    return client.getStatusCodeReply();
  }

  @Override
  public Long pexpire(final String key, final long milliseconds) {
    checkIsInMultiOrPipeline();
    client.pexpire(key, milliseconds);
    return client.getIntegerReply();
  }

  @Override
  public Long pexpireAt(final String key, final long millisecondsTimestamp) {
    checkIsInMultiOrPipeline();
    client.pexpireAt(key, millisecondsTimestamp);
    return client.getIntegerReply();
  }

  @Override
  public Long pttl(final String key) {
    checkIsInMultiOrPipeline();
    client.pttl(key);
    return client.getIntegerReply();
  }

  /**
   * PSETEX works exactly like {@link #setex(String, int, String)} with the sole difference that the
   * expire time is specified in milliseconds instead of seconds. Time complexity: O(1)
   * @param key
   * @param milliseconds
   * @param value
   * @return Status code reply
   */

  @Override
  public String psetex(final String key, final long milliseconds, final String value) {
    checkIsInMultiOrPipeline();
    client.psetex(key, milliseconds, value);
    return client.getStatusCodeReply();
  }

  public String clientKill(final String client) {
    checkIsInMultiOrPipeline();
    this.client.clientKill(client);
    return this.client.getStatusCodeReply();
  }

  public String clientSetname(final String name) {
    checkIsInMultiOrPipeline();
    client.clientSetname(name);
    return client.getStatusCodeReply();
  }

  public String migrate(final String host, final int port, final String key,
      final int destinationDb, final int timeout) {
    checkIsInMultiOrPipeline();
    client.migrate(host, port, key, destinationDb, timeout);
    return client.getStatusCodeReply();
  }

  @Override
  public ScanResult<String> scan(final String cursor) {
    return scan(cursor, new ScanParams());
  }

  @Override
  public ScanResult<String> scan(final String cursor, final ScanParams params) {
    checkIsInMultiOrPipeline();
    client.scan(cursor, params);
    List<Object> result = client.getObjectMultiBulkReply();
    String newcursor = new String((byte[]) result.get(0));
    List<String> results = new ArrayList<String>();
    List<byte[]> rawResults = (List<byte[]>) result.get(1);
    for (byte[] bs : rawResults) {
      results.add(SafeEncoder.encode(bs));
    }
    return new ScanResult<String>(newcursor, results);
  }

  @Override
  public ScanResult<Map.Entry<String, String>> hscan(final String key, final String cursor) {
    return hscan(key, cursor, new ScanParams());
  }

  @Override
  public ScanResult<Map.Entry<String, String>> hscan(final String key, final String cursor,
      final ScanParams params) {
    checkIsInMultiOrPipeline();
    client.hscan(key, cursor, params);
    List<Object> result = client.getObjectMultiBulkReply();
    String newcursor = new String((byte[]) result.get(0));
    List<Map.Entry<String, String>> results = new ArrayList<Map.Entry<String, String>>();
    List<byte[]> rawResults = (List<byte[]>) result.get(1);
    Iterator<byte[]> iterator = rawResults.iterator();
    while (iterator.hasNext()) {
      results.add(new AbstractMap.SimpleEntry<String, String>(SafeEncoder.encode(iterator.next()),
          SafeEncoder.encode(iterator.next())));
    }
    return new ScanResult<Map.Entry<String, String>>(newcursor, results);
  }

  @Override
  public ScanResult<String> sscan(final String key, final String cursor) {
    return sscan(key, cursor, new ScanParams());
  }

  @Override
  public ScanResult<String> sscan(final String key, final String cursor, final ScanParams params) {
    checkIsInMultiOrPipeline();
    client.sscan(key, cursor, params);
    List<Object> result = client.getObjectMultiBulkReply();
    String newcursor = new String((byte[]) result.get(0));
    List<String> results = new ArrayList<String>();
    List<byte[]> rawResults = (List<byte[]>) result.get(1);
    for (byte[] bs : rawResults) {
      results.add(SafeEncoder.encode(bs));
    }
    return new ScanResult<String>(newcursor, results);
  }

  @Override
  public ScanResult<Tuple> zscan(final String key, final String cursor) {
    return zscan(key, cursor, new ScanParams());
  }

  @Override
  public ScanResult<Tuple> zscan(final String key, final String cursor, final ScanParams params) {
    checkIsInMultiOrPipeline();
    client.zscan(key, cursor, params);
    List<Object> result = client.getObjectMultiBulkReply();
    String newcursor = new String((byte[]) result.get(0));
    List<Tuple> results = new ArrayList<Tuple>();
    List<byte[]> rawResults = (List<byte[]>) result.get(1);
    Iterator<byte[]> iterator = rawResults.iterator();
    while (iterator.hasNext()) {
      results.add(new Tuple(SafeEncoder.encode(iterator.next()), Double.valueOf(SafeEncoder
          .encode(iterator.next()))));
    }
    return new ScanResult<Tuple>(newcursor, results);
  }

  @Override
  public String clusterNodes() {
    checkIsInMultiOrPipeline();
    client.clusterNodes();
    return client.getBulkReply();
  }

  @Override
  public String readonly() {
    client.readonly();
    return client.getStatusCodeReply();
  }

  @Override
  public String clusterMeet(final String ip, final int port) {
    checkIsInMultiOrPipeline();
    client.clusterMeet(ip, port);
    return client.getStatusCodeReply();
  }

  @Override
  public String clusterReset(final Reset resetType) {
    checkIsInMultiOrPipeline();
    client.clusterReset(resetType);
    return client.getStatusCodeReply();
  }

  @Override
  public String clusterAddSlots(final int... slots) {
    checkIsInMultiOrPipeline();
    client.clusterAddSlots(slots);
    return client.getStatusCodeReply();
  }

  @Override
  public String clusterDelSlots(final int... slots) {
    checkIsInMultiOrPipeline();
    client.clusterDelSlots(slots);
    return client.getStatusCodeReply();
  }

  @Override
  public String clusterInfo() {
    checkIsInMultiOrPipeline();
    client.clusterInfo();
    return client.getStatusCodeReply();
  }

  @Override
  public List<String> clusterGetKeysInSlot(final int slot, final int count) {
    checkIsInMultiOrPipeline();
    client.clusterGetKeysInSlot(slot, count);
    return client.getMultiBulkReply();
  }

  @Override
  public String clusterSetSlotNode(final int slot, final String nodeId) {
    checkIsInMultiOrPipeline();
    client.clusterSetSlotNode(slot, nodeId);
    return client.getStatusCodeReply();
  }

  @Override
  public String clusterSetSlotMigrating(final int slot, final String nodeId) {
    checkIsInMultiOrPipeline();
    client.clusterSetSlotMigrating(slot, nodeId);
    return client.getStatusCodeReply();
  }

  @Override
  public String clusterSetSlotImporting(final int slot, final String nodeId) {
    checkIsInMultiOrPipeline();
    client.clusterSetSlotImporting(slot, nodeId);
    return client.getStatusCodeReply();
  }

  @Override
  public String clusterSetSlotStable(final int slot) {
    checkIsInMultiOrPipeline();
    client.clusterSetSlotStable(slot);
    return client.getStatusCodeReply();
  }

  @Override
  public String clusterForget(final String nodeId) {
    checkIsInMultiOrPipeline();
    client.clusterForget(nodeId);
    return client.getStatusCodeReply();
  }

  @Override
  public String clusterFlushSlots() {
    checkIsInMultiOrPipeline();
    client.clusterFlushSlots();
    return client.getStatusCodeReply();
  }

  @Override
  public Long clusterKeySlot(final String key) {
    checkIsInMultiOrPipeline();
    client.clusterKeySlot(key);
    return client.getIntegerReply();
  }

  @Override
  public Long clusterCountKeysInSlot(final int slot) {
    checkIsInMultiOrPipeline();
    client.clusterCountKeysInSlot(slot);
    return client.getIntegerReply();
  }

  @Override
  public String clusterSaveConfig() {
    checkIsInMultiOrPipeline();
    client.clusterSaveConfig();
    return client.getStatusCodeReply();
  }

  @Override
  public String clusterReplicate(final String nodeId) {
    checkIsInMultiOrPipeline();
    client.clusterReplicate(nodeId);
    return client.getStatusCodeReply();
  }

  @Override
  public List<String> clusterSlaves(final String nodeId) {
    checkIsInMultiOrPipeline();
    client.clusterSlaves(nodeId);
    return client.getMultiBulkReply();
  }

  @Override
  public String clusterFailover() {
    checkIsInMultiOrPipeline();
    client.clusterFailover();
    return client.getStatusCodeReply();
  }

  @Override
  public List<Object> clusterSlots() {
    checkIsInMultiOrPipeline();
    client.clusterSlots();
    return client.getObjectMultiBulkReply();
  }

  public String asking() {
    checkIsInMultiOrPipeline();
    client.asking();
    return client.getStatusCodeReply();
  }

  public List<String> pubsubChannels(String pattern) {
    checkIsInMultiOrPipeline();
    client.pubsubChannels(pattern);
    return client.getMultiBulkReply();
  }

  public Long pubsubNumPat() {
    checkIsInMultiOrPipeline();
    client.pubsubNumPat();
    return client.getIntegerReply();
  }

  public Map<String, String> pubsubNumSub(String... channels) {
    checkIsInMultiOrPipeline();
    client.pubsubNumSub(channels);
    return BuilderFactory.PUBSUB_NUMSUB_MAP.build(client.getBinaryMultiBulkReply());
  }

  @Override
  public void close() {
    if (dataSource != null) {
      if (client.isBroken()) {
        this.dataSource.returnBrokenResource(this);
      } else {
        this.dataSource.returnResource(this);
      }
    } else {
      client.close();
    }
  }

  public void setDataSource(JedisPoolAbstract jedisPool) {
    this.dataSource = jedisPool;
  }

  @Override
  public Long pfadd(final String key, final String... elements) {
    checkIsInMultiOrPipeline();
    client.pfadd(key, elements);
    return client.getIntegerReply();
  }

  @Override
  public long pfcount(final String key) {
    checkIsInMultiOrPipeline();
    client.pfcount(key);
    return client.getIntegerReply();
  }

  @Override
  public long pfcount(String... keys) {
    checkIsInMultiOrPipeline();
    client.pfcount(keys);
    return client.getIntegerReply();
  }

  @Override
  public String pfmerge(final String destkey, final String... sourcekeys) {
    checkIsInMultiOrPipeline();
    client.pfmerge(destkey, sourcekeys);
    return client.getStatusCodeReply();
  }

  @Override
  public List<String> blpop(int timeout, String key) {
    return blpop(key, String.valueOf(timeout));
  }

  @Override
  public List<String> brpop(int timeout, String key) {
    return brpop(key, String.valueOf(timeout));
  }

}


File: src/main/java/redis/clients/jedis/JedisCluster.java
package redis.clients.jedis;

import redis.clients.jedis.BinaryClient.LIST_POSITION;
import redis.clients.util.KeyMergeUtil;

import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;

import org.apache.commons.pool2.impl.GenericObjectPoolConfig;

import redis.clients.jedis.params.set.SetParams;

public class JedisCluster extends BinaryJedisCluster implements JedisClusterCommands,
    MultiKeyJedisClusterCommands, JedisClusterScriptingCommands {
  public static enum Reset {
    SOFT, HARD
  }

  public JedisCluster(Set<HostAndPort> nodes) {
    this(nodes, DEFAULT_TIMEOUT);
  }

  public JedisCluster(Set<HostAndPort> nodes, int timeout) {
    this(nodes, timeout, DEFAULT_MAX_REDIRECTIONS);
  }

  public JedisCluster(Set<HostAndPort> nodes, int timeout, int maxRedirections) {
    this(nodes, timeout, maxRedirections, new GenericObjectPoolConfig());
  }

  public JedisCluster(Set<HostAndPort> nodes, final GenericObjectPoolConfig poolConfig) {
    this(nodes, DEFAULT_TIMEOUT, DEFAULT_MAX_REDIRECTIONS, poolConfig);
  }

  public JedisCluster(Set<HostAndPort> nodes, int timeout, final GenericObjectPoolConfig poolConfig) {
    this(nodes, timeout, DEFAULT_MAX_REDIRECTIONS, poolConfig);
  }

  public JedisCluster(Set<HostAndPort> jedisClusterNode, int timeout, int maxRedirections,
      final GenericObjectPoolConfig poolConfig) {
    super(jedisClusterNode, timeout, maxRedirections, poolConfig);
  }

  public JedisCluster(Set<HostAndPort> jedisClusterNode, int connectionTimeout, int soTimeout,
      int maxRedirections, final GenericObjectPoolConfig poolConfig) {
    super(jedisClusterNode, connectionTimeout, soTimeout, maxRedirections, poolConfig);
  }

  @Override
  public String set(final String key, final String value) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.set(key, value);
      }
    }.run(key);
  }

  @Override
  public String set(final String key, final String value, final SetParams params) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.set(key, value, params);
      }
    }.run(key);
  }

  @Override
  public String get(final String key) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.get(key);
      }
    }.run(key);
  }

  @Override
  public Boolean exists(final String key) {
    return new JedisClusterCommand<Boolean>(connectionHandler, maxRedirections) {
      @Override
      public Boolean execute(Jedis connection) {
        return connection.exists(key);
      }
    }.run(key);
  }

  @Override
  public Long persist(final String key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.persist(key);
      }
    }.run(key);
  }

  @Override
  public String type(final String key) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.type(key);
      }
    }.run(key);
  }

  @Override
  public Long expire(final String key, final int seconds) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.expire(key, seconds);
      }
    }.run(key);
  }

  @Override
  public Long pexpire(final String key, final long milliseconds) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.pexpire(key, milliseconds);
      }
    }.run(key);
  }

  @Override
  public Long expireAt(final String key, final long unixTime) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.expireAt(key, unixTime);
      }
    }.run(key);
  }

  @Override
  public Long pexpireAt(final String key, final long millisecondsTimestamp) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.pexpireAt(key, millisecondsTimestamp);
      }
    }.run(key);
  }

  @Override
  public Long ttl(final String key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.ttl(key);
      }
    }.run(key);
  }

  @Override
  public Boolean setbit(final String key, final long offset, final boolean value) {
    return new JedisClusterCommand<Boolean>(connectionHandler, maxRedirections) {
      @Override
      public Boolean execute(Jedis connection) {
        return connection.setbit(key, offset, value);
      }
    }.run(key);
  }

  @Override
  public Boolean setbit(final String key, final long offset, final String value) {
    return new JedisClusterCommand<Boolean>(connectionHandler, maxRedirections) {
      @Override
      public Boolean execute(Jedis connection) {
        return connection.setbit(key, offset, value);
      }
    }.run(key);
  }

  @Override
  public Boolean getbit(final String key, final long offset) {
    return new JedisClusterCommand<Boolean>(connectionHandler, maxRedirections) {
      @Override
      public Boolean execute(Jedis connection) {
        return connection.getbit(key, offset);
      }
    }.run(key);
  }

  @Override
  public Long setrange(final String key, final long offset, final String value) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.setrange(key, offset, value);
      }
    }.run(key);
  }

  @Override
  public String getrange(final String key, final long startOffset, final long endOffset) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.getrange(key, startOffset, endOffset);
      }
    }.run(key);
  }

  @Override
  public String getSet(final String key, final String value) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.getSet(key, value);
      }
    }.run(key);
  }

  @Override
  public Long setnx(final String key, final String value) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.setnx(key, value);
      }
    }.run(key);
  }

  @Override
  public String setex(final String key, final int seconds, final String value) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.setex(key, seconds, value);
      }
    }.run(key);
  }

  @Override
  public Long decrBy(final String key, final long integer) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.decrBy(key, integer);
      }
    }.run(key);
  }

  @Override
  public Long decr(final String key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.decr(key);
      }
    }.run(key);
  }

  @Override
  public Long incrBy(final String key, final long integer) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.incrBy(key, integer);
      }
    }.run(key);
  }

  @Override
  public Double incrByFloat(final String key, final double value) {
    return new JedisClusterCommand<Double>(connectionHandler, maxRedirections) {
      @Override
      public Double execute(Jedis connection) {
        return connection.incrByFloat(key, value);
      }
    }.run(key);
  }

  @Override
  public Long incr(final String key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.incr(key);
      }
    }.run(key);
  }

  @Override
  public Long append(final String key, final String value) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.append(key, value);
      }
    }.run(key);
  }

  @Override
  public String substr(final String key, final int start, final int end) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.substr(key, start, end);
      }
    }.run(key);
  }

  @Override
  public Long hset(final String key, final String field, final String value) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.hset(key, field, value);
      }
    }.run(key);
  }

  @Override
  public String hget(final String key, final String field) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.hget(key, field);
      }
    }.run(key);
  }

  @Override
  public Long hsetnx(final String key, final String field, final String value) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.hsetnx(key, field, value);
      }
    }.run(key);
  }

  @Override
  public String hmset(final String key, final Map<String, String> hash) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.hmset(key, hash);
      }
    }.run(key);
  }

  @Override
  public List<String> hmget(final String key, final String... fields) {
    return new JedisClusterCommand<List<String>>(connectionHandler, maxRedirections) {
      @Override
      public List<String> execute(Jedis connection) {
        return connection.hmget(key, fields);
      }
    }.run(key);
  }

  @Override
  public Long hincrBy(final String key, final String field, final long value) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.hincrBy(key, field, value);
      }
    }.run(key);
  }

  @Override
  public Boolean hexists(final String key, final String field) {
    return new JedisClusterCommand<Boolean>(connectionHandler, maxRedirections) {
      @Override
      public Boolean execute(Jedis connection) {
        return connection.hexists(key, field);
      }
    }.run(key);
  }

  @Override
  public Long hdel(final String key, final String... field) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.hdel(key, field);
      }
    }.run(key);
  }

  @Override
  public Long hlen(final String key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.hlen(key);
      }
    }.run(key);
  }

  @Override
  public Set<String> hkeys(final String key) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.hkeys(key);
      }
    }.run(key);
  }

  @Override
  public List<String> hvals(final String key) {
    return new JedisClusterCommand<List<String>>(connectionHandler, maxRedirections) {
      @Override
      public List<String> execute(Jedis connection) {
        return connection.hvals(key);
      }
    }.run(key);
  }

  @Override
  public Map<String, String> hgetAll(final String key) {
    return new JedisClusterCommand<Map<String, String>>(connectionHandler, maxRedirections) {
      @Override
      public Map<String, String> execute(Jedis connection) {
        return connection.hgetAll(key);
      }
    }.run(key);
  }

  @Override
  public Long rpush(final String key, final String... string) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.rpush(key, string);
      }
    }.run(key);
  }

  @Override
  public Long lpush(final String key, final String... string) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.lpush(key, string);
      }
    }.run(key);
  }

  @Override
  public Long llen(final String key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.llen(key);
      }
    }.run(key);
  }

  @Override
  public List<String> lrange(final String key, final long start, final long end) {
    return new JedisClusterCommand<List<String>>(connectionHandler, maxRedirections) {
      @Override
      public List<String> execute(Jedis connection) {
        return connection.lrange(key, start, end);
      }
    }.run(key);
  }

  @Override
  public String ltrim(final String key, final long start, final long end) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.ltrim(key, start, end);
      }
    }.run(key);
  }

  @Override
  public String lindex(final String key, final long index) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.lindex(key, index);
      }
    }.run(key);
  }

  @Override
  public String lset(final String key, final long index, final String value) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.lset(key, index, value);
      }
    }.run(key);
  }

  @Override
  public Long lrem(final String key, final long count, final String value) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.lrem(key, count, value);
      }
    }.run(key);
  }

  @Override
  public String lpop(final String key) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.lpop(key);
      }
    }.run(key);
  }

  @Override
  public String rpop(final String key) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.rpop(key);
      }
    }.run(key);
  }

  @Override
  public Long sadd(final String key, final String... member) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.sadd(key, member);
      }
    }.run(key);
  }

  @Override
  public Set<String> smembers(final String key) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.smembers(key);
      }
    }.run(key);
  }

  @Override
  public Long srem(final String key, final String... member) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.srem(key, member);
      }
    }.run(key);
  }

  @Override
  public String spop(final String key) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.spop(key);
      }
    }.run(key);
  }

  @Override
  public Set<String> spop(final String key, final long count) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.spop(key, count);
      }
    }.run(key);
  }

  @Override
  public Long scard(final String key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.scard(key);
      }
    }.run(key);
  }

  @Override
  public Boolean sismember(final String key, final String member) {
    return new JedisClusterCommand<Boolean>(connectionHandler, maxRedirections) {
      @Override
      public Boolean execute(Jedis connection) {
        return connection.sismember(key, member);
      }
    }.run(key);
  }

  @Override
  public String srandmember(final String key) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.srandmember(key);
      }
    }.run(key);
  }

  @Override
  public List<String> srandmember(final String key, final int count) {
    return new JedisClusterCommand<List<String>>(connectionHandler, maxRedirections) {
      @Override
      public List<String> execute(Jedis connection) {
        return connection.srandmember(key, count);
      }
    }.run(key);
  }

  @Override
  public Long strlen(final String key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.strlen(key);
      }
    }.run(key);
  }

  @Override
  public Long zadd(final String key, final double score, final String member) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zadd(key, score, member);
      }
    }.run(key);
  }

  @Override
  public Long zadd(final String key, final Map<String, Double> scoreMembers) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zadd(key, scoreMembers);
      }
    }.run(key);
  }

  @Override
  public Set<String> zrange(final String key, final long start, final long end) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.zrange(key, start, end);
      }
    }.run(key);
  }

  @Override
  public Long zrem(final String key, final String... member) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zrem(key, member);
      }
    }.run(key);
  }

  @Override
  public Double zincrby(final String key, final double score, final String member) {
    return new JedisClusterCommand<Double>(connectionHandler, maxRedirections) {
      @Override
      public Double execute(Jedis connection) {
        return connection.zincrby(key, score, member);
      }
    }.run(key);
  }

  @Override
  public Long zrank(final String key, final String member) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zrank(key, member);
      }
    }.run(key);
  }

  @Override
  public Long zrevrank(final String key, final String member) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zrevrank(key, member);
      }
    }.run(key);
  }

  @Override
  public Set<String> zrevrange(final String key, final long start, final long end) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.zrevrange(key, start, end);
      }
    }.run(key);
  }

  @Override
  public Set<Tuple> zrangeWithScores(final String key, final long start, final long end) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrangeWithScores(key, start, end);
      }
    }.run(key);
  }

  @Override
  public Set<Tuple> zrevrangeWithScores(final String key, final long start, final long end) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrevrangeWithScores(key, start, end);
      }
    }.run(key);
  }

  @Override
  public Long zcard(final String key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zcard(key);
      }
    }.run(key);
  }

  @Override
  public Double zscore(final String key, final String member) {
    return new JedisClusterCommand<Double>(connectionHandler, maxRedirections) {
      @Override
      public Double execute(Jedis connection) {
        return connection.zscore(key, member);
      }
    }.run(key);
  }

  @Override
  public List<String> sort(final String key) {
    return new JedisClusterCommand<List<String>>(connectionHandler, maxRedirections) {
      @Override
      public List<String> execute(Jedis connection) {
        return connection.sort(key);
      }
    }.run(key);
  }

  @Override
  public List<String> sort(final String key, final SortingParams sortingParameters) {
    return new JedisClusterCommand<List<String>>(connectionHandler, maxRedirections) {
      @Override
      public List<String> execute(Jedis connection) {
        return connection.sort(key, sortingParameters);
      }
    }.run(key);
  }

  @Override
  public Long zcount(final String key, final double min, final double max) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zcount(key, min, max);
      }
    }.run(key);
  }

  @Override
  public Long zcount(final String key, final String min, final String max) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zcount(key, min, max);
      }
    }.run(key);
  }

  @Override
  public Set<String> zrangeByScore(final String key, final double min, final double max) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.zrangeByScore(key, min, max);
      }
    }.run(key);
  }

  @Override
  public Set<String> zrangeByScore(final String key, final String min, final String max) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.zrangeByScore(key, min, max);
      }
    }.run(key);
  }

  @Override
  public Set<String> zrevrangeByScore(final String key, final double max, final double min) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.zrevrangeByScore(key, max, min);
      }
    }.run(key);
  }

  @Override
  public Set<String> zrangeByScore(final String key, final double min, final double max,
      final int offset, final int count) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.zrangeByScore(key, min, max, offset, count);
      }
    }.run(key);
  }

  @Override
  public Set<String> zrevrangeByScore(final String key, final String max, final String min) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.zrevrangeByScore(key, max, min);
      }
    }.run(key);
  }

  @Override
  public Set<String> zrangeByScore(final String key, final String min, final String max,
      final int offset, final int count) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.zrangeByScore(key, min, max, offset, count);
      }
    }.run(key);
  }

  @Override
  public Set<String> zrevrangeByScore(final String key, final double max, final double min,
      final int offset, final int count) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.zrevrangeByScore(key, max, min, offset, count);
      }
    }.run(key);
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(final String key, final double min, final double max) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrangeByScoreWithScores(key, min, max);
      }
    }.run(key);
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(final String key, final double max, final double min) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrevrangeByScoreWithScores(key, max, min);
      }
    }.run(key);
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(final String key, final double min, final double max,
      final int offset, final int count) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrangeByScoreWithScores(key, min, max, offset, count);
      }
    }.run(key);
  }

  @Override
  public Set<String> zrevrangeByScore(final String key, final String max, final String min,
      final int offset, final int count) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.zrevrangeByScore(key, max, min, offset, count);
      }
    }.run(key);
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(final String key, final String min, final String max) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrangeByScoreWithScores(key, min, max);
      }
    }.run(key);
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(final String key, final String max, final String min) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrevrangeByScoreWithScores(key, max, min);
      }
    }.run(key);
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(final String key, final String min, final String max,
      final int offset, final int count) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrangeByScoreWithScores(key, min, max, offset, count);
      }
    }.run(key);
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(final String key, final double max,
      final double min, final int offset, final int count) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrevrangeByScoreWithScores(key, max, min, offset, count);
      }
    }.run(key);
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(final String key, final String max,
      final String min, final int offset, final int count) {
    return new JedisClusterCommand<Set<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public Set<Tuple> execute(Jedis connection) {
        return connection.zrevrangeByScoreWithScores(key, max, min, offset, count);
      }
    }.run(key);
  }

  @Override
  public Long zremrangeByRank(final String key, final long start, final long end) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zremrangeByRank(key, start, end);
      }
    }.run(key);
  }

  @Override
  public Long zremrangeByScore(final String key, final double start, final double end) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zremrangeByScore(key, start, end);
      }
    }.run(key);
  }

  @Override
  public Long zremrangeByScore(final String key, final String start, final String end) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zremrangeByScore(key, start, end);
      }
    }.run(key);
  }

  @Override
  public Long zlexcount(final String key, final String min, final String max) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zlexcount(key, min, max);
      }
    }.run(key);
  }

  @Override
  public Set<String> zrangeByLex(final String key, final String min, final String max) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.zrangeByLex(key, min, max);
      }
    }.run(key);
  }

  @Override
  public Set<String> zrangeByLex(final String key, final String min, final String max,
      final int offset, final int count) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.zrangeByLex(key, min, max, offset, count);
      }
    }.run(key);
  }

  @Override
  public Set<String> zrevrangeByLex(final String key, final String max, final String min) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.zrevrangeByLex(key, max, min);
      }
    }.run(key);
  }

  @Override
  public Set<String> zrevrangeByLex(final String key, final String max, final String min,
      final int offset, final int count) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.zrevrangeByLex(key, max, min, offset, count);
      }
    }.run(key);
  }

  @Override
  public Long zremrangeByLex(final String key, final String min, final String max) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zremrangeByLex(key, min, max);
      }
    }.run(key);
  }

  @Override
  public Long linsert(final String key, final LIST_POSITION where, final String pivot,
      final String value) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.linsert(key, where, pivot, value);
      }
    }.run(key);
  }

  @Override
  public Long lpushx(final String key, final String... string) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.lpushx(key, string);
      }
    }.run(key);
  }

  @Override
  public Long rpushx(final String key, final String... string) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.rpushx(key, string);
      }
    }.run(key);
  }

  @Override
  public Long del(final String key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.del(key);
      }
    }.run(key);
  }

  @Override
  public String echo(final String string) {
    // note that it'll be run from arbitary node
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.echo(string);
      }
    }.run(string);
  }

  @Override
  public Long bitcount(final String key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.bitcount(key);
      }
    }.run(key);
  }

  @Override
  public Long bitcount(final String key, final long start, final long end) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.bitcount(key, start, end);
      }
    }.run(key);
  }

  @Override
  public ScanResult<Entry<String, String>> hscan(final String key, final String cursor) {
    return new JedisClusterCommand<ScanResult<Entry<String, String>>>(connectionHandler,
        maxRedirections) {
      @Override
      public ScanResult<Entry<String, String>> execute(Jedis connection) {
        return connection.hscan(key, cursor);
      }
    }.run(key);
  }

  @Override
  public ScanResult<String> sscan(final String key, final String cursor) {
    return new JedisClusterCommand<ScanResult<String>>(connectionHandler, maxRedirections) {
      @Override
      public ScanResult<String> execute(Jedis connection) {
        return connection.sscan(key, cursor);
      }
    }.run(key);
  }

  @Override
  public ScanResult<Tuple> zscan(final String key, final String cursor) {
    return new JedisClusterCommand<ScanResult<Tuple>>(connectionHandler, maxRedirections) {
      @Override
      public ScanResult<Tuple> execute(Jedis connection) {
        return connection.zscan(key, cursor);
      }
    }.run(key);
  }

  @Override
  public Long pfadd(final String key, final String... elements) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.pfadd(key, elements);
      }
    }.run(key);
  }

  @Override
  public long pfcount(final String key) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.pfcount(key);
      }
    }.run(key);
  }

  @Override
  public List<String> blpop(final int timeout, final String key) {
    return new JedisClusterCommand<List<String>>(connectionHandler, maxRedirections) {
      @Override
      public List<String> execute(Jedis connection) {
        return connection.blpop(timeout, key);
      }
    }.run(key);
  }

  @Override
  public List<String> brpop(final int timeout, final String key) {
    return new JedisClusterCommand<List<String>>(connectionHandler, maxRedirections) {
      @Override
      public List<String> execute(Jedis connection) {
        return connection.brpop(timeout, key);
      }
    }.run(key);
  }

  @Override
  public Long del(final String... keys) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.del(keys);
      }
    }.run(keys.length, keys);
  }

  @Override
  public List<String> blpop(final int timeout, final String... keys) {
    return new JedisClusterCommand<List<String>>(connectionHandler, maxRedirections) {
      @Override
      public List<String> execute(Jedis connection) {
        return connection.blpop(timeout, keys);
      }
    }.run(keys.length, keys);

  }

  @Override
  public List<String> brpop(final int timeout, final String... keys) {
    return new JedisClusterCommand<List<String>>(connectionHandler, maxRedirections) {
      @Override
      public List<String> execute(Jedis connection) {
        return connection.brpop(timeout, keys);
      }
    }.run(keys.length, keys);
  }

  @Override
  public List<String> mget(final String... keys) {
    return new JedisClusterCommand<List<String>>(connectionHandler, maxRedirections) {
      @Override
      public List<String> execute(Jedis connection) {
        return connection.mget(keys);
      }
    }.run(keys.length, keys);
  }

  @Override
  public String mset(final String... keysvalues) {
    String[] keys = new String[keysvalues.length / 2];

    for (int keyIdx = 0; keyIdx < keys.length; keyIdx++) {
      keys[keyIdx] = keysvalues[keyIdx * 2];
    }

    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.mset(keysvalues);
      }
    }.run(keys.length, keys);
  }

  @Override
  public Long msetnx(final String... keysvalues) {
    String[] keys = new String[keysvalues.length / 2];

    for (int keyIdx = 0; keyIdx < keys.length; keyIdx++) {
      keys[keyIdx] = keysvalues[keyIdx * 2];
    }

    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.msetnx(keysvalues);
      }
    }.run(keys.length, keys);
  }

  @Override
  public String rename(final String oldkey, final String newkey) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.rename(oldkey, newkey);
      }
    }.run(2, oldkey, newkey);
  }

  @Override
  public Long renamenx(final String oldkey, final String newkey) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.renamenx(oldkey, newkey);
      }
    }.run(2, oldkey, newkey);
  }

  @Override
  public String rpoplpush(final String srckey, final String dstkey) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.rpoplpush(srckey, dstkey);
      }
    }.run(2, srckey, dstkey);
  }

  @Override
  public Set<String> sdiff(final String... keys) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.sdiff(keys);
      }
    }.run(keys.length, keys);
  }

  @Override
  public Long sdiffstore(final String dstkey, final String... keys) {
    String[] mergedKeys = KeyMergeUtil.merge(dstkey, keys);

    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.sdiffstore(dstkey, keys);
      }
    }.run(mergedKeys.length, mergedKeys);
  }

  @Override
  public Set<String> sinter(final String... keys) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.sinter(keys);
      }
    }.run(keys.length, keys);
  }

  @Override
  public Long sinterstore(final String dstkey, final String... keys) {
    String[] mergedKeys = KeyMergeUtil.merge(dstkey, keys);

    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.sinterstore(dstkey, keys);
      }
    }.run(mergedKeys.length, mergedKeys);
  }

  @Override
  public Long smove(final String srckey, final String dstkey, final String member) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.smove(srckey, dstkey, member);
      }
    }.run(2, srckey, dstkey);
  }

  @Override
  public Long sort(final String key, final SortingParams sortingParameters, final String dstkey) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.sort(key, sortingParameters, dstkey);
      }
    }.run(2, key, dstkey);
  }

  @Override
  public Long sort(final String key, final String dstkey) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.sort(key, dstkey);
      }
    }.run(2, key, dstkey);
  }

  @Override
  public Set<String> sunion(final String... keys) {
    return new JedisClusterCommand<Set<String>>(connectionHandler, maxRedirections) {
      @Override
      public Set<String> execute(Jedis connection) {
        return connection.sunion(keys);
      }
    }.run(keys.length, keys);
  }

  @Override
  public Long sunionstore(final String dstkey, final String... keys) {
    String[] wholeKeys = KeyMergeUtil.merge(dstkey, keys);

    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.sunionstore(dstkey, keys);
      }
    }.run(wholeKeys.length, wholeKeys);
  }

  @Override
  public Long zinterstore(final String dstkey, final String... sets) {
    String[] wholeKeys = KeyMergeUtil.merge(dstkey, sets);

    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zinterstore(dstkey, sets);
      }
    }.run(wholeKeys.length, wholeKeys);
  }

  @Override
  public Long zinterstore(final String dstkey, final ZParams params, final String... sets) {
    String[] mergedKeys = KeyMergeUtil.merge(dstkey, sets);

    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zinterstore(dstkey, params, sets);
      }
    }.run(mergedKeys.length, mergedKeys);
  }

  @Override
  public Long zunionstore(final String dstkey, final String... sets) {
    String[] mergedKeys = KeyMergeUtil.merge(dstkey, sets);

    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zunionstore(dstkey, sets);
      }
    }.run(mergedKeys.length, mergedKeys);
  }

  @Override
  public Long zunionstore(final String dstkey, final ZParams params, final String... sets) {
    String[] mergedKeys = KeyMergeUtil.merge(dstkey, sets);

    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.zunionstore(dstkey, params, sets);
      }
    }.run(mergedKeys.length, mergedKeys);
  }

  @Override
  public String brpoplpush(final String source, final String destination, final int timeout) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.brpoplpush(source, destination, timeout);
      }
    }.run(2, source, destination);
  }

  @Override
  public Long publish(final String channel, final String message) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.publish(channel, message);
      }
    }.runWithAnyNode();
  }

  @Override
  public void subscribe(final JedisPubSub jedisPubSub, final String... channels) {
    new JedisClusterCommand<Integer>(connectionHandler, maxRedirections) {
      @Override
      public Integer execute(Jedis connection) {
        connection.subscribe(jedisPubSub, channels);
        return 0;
      }
    }.runWithAnyNode();
  }

  @Override
  public void psubscribe(final JedisPubSub jedisPubSub, final String... patterns) {
    new JedisClusterCommand<Integer>(connectionHandler, maxRedirections) {
      @Override
      public Integer execute(Jedis connection) {
        connection.subscribe(jedisPubSub, patterns);
        return 0;
      }
    }.runWithAnyNode();
  }

  @Override
  public Long bitop(final BitOP op, final String destKey, final String... srcKeys) {
    String[] mergedKeys = KeyMergeUtil.merge(destKey, srcKeys);

    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.bitop(op, destKey, srcKeys);
      }
    }.run(mergedKeys.length, mergedKeys);
  }

  @Override
  public String pfmerge(final String destkey, final String... sourcekeys) {
    String[] mergedKeys = KeyMergeUtil.merge(destkey, sourcekeys);

    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.pfmerge(destkey, sourcekeys);
      }
    }.run(mergedKeys.length, mergedKeys);
  }

  @Override
  public long pfcount(final String... keys) {
    return new JedisClusterCommand<Long>(connectionHandler, maxRedirections) {
      @Override
      public Long execute(Jedis connection) {
        return connection.pfcount(keys);
      }
    }.run(keys.length, keys);
  }

  @Override
  public Object eval(final String script, final int keyCount, final String... params) {
    return new JedisClusterCommand<Object>(connectionHandler, maxRedirections) {
      @Override
      public Object execute(Jedis connection) {
        return connection.eval(script, keyCount, params);
      }
    }.run(keyCount, params);
  }

  @Override
  public Object eval(final String script, final String key) {
    return new JedisClusterCommand<Object>(connectionHandler, maxRedirections) {
      @Override
      public Object execute(Jedis connection) {
        return connection.eval(script);
      }
    }.run(key);
  }

  @Override
  public Object eval(final String script, final List<String> keys, final List<String> args) {
    return new JedisClusterCommand<Object>(connectionHandler, maxRedirections) {
      @Override
      public Object execute(Jedis connection) {
        return connection.eval(script, keys, args);
      }
    }.run(keys.size(), keys.toArray(new String[keys.size()]));
  }

  @Override
  public Object evalsha(final String sha1, final int keyCount, final String... params) {
    return new JedisClusterCommand<Object>(connectionHandler, maxRedirections) {
      @Override
      public Object execute(Jedis connection) {
        return connection.evalsha(sha1, keyCount, params);
      }
    }.run(keyCount, params);
  }

  @Override
  public Object evalsha(final String sha1, final List<String> keys, final List<String> args) {
    return new JedisClusterCommand<Object>(connectionHandler, maxRedirections) {
      @Override
      public Object execute(Jedis connection) {
        return connection.evalsha(sha1, keys, args);
      }
    }.run(keys.size(), keys.toArray(new String[keys.size()]));
  }

  @Override
  public Object evalsha(final String script, final String key) {
    return new JedisClusterCommand<Object>(connectionHandler, maxRedirections) {
      @Override
      public Object execute(Jedis connection) {
        return connection.evalsha(script);
      }
    }.run(key);
  }

  @Override
  public Boolean scriptExists(final String sha1, final String key) {
    return new JedisClusterCommand<Boolean>(connectionHandler, maxRedirections) {
      @Override
      public Boolean execute(Jedis connection) {
        return connection.scriptExists(sha1);
      }
    }.run(key);
  }

  @Override
  public List<Boolean> scriptExists(final String key, final String... sha1) {
    return new JedisClusterCommand<List<Boolean>>(connectionHandler, maxRedirections) {
      @Override
      public List<Boolean> execute(Jedis connection) {
        return connection.scriptExists(sha1);
      }
    }.run(key);
  }

  @Override
  public String scriptLoad(final String script, final String key) {
    return new JedisClusterCommand<String>(connectionHandler, maxRedirections) {
      @Override
      public String execute(Jedis connection) {
        return connection.scriptLoad(script);
      }
    }.run(key);
  }
}


File: src/main/java/redis/clients/jedis/MultiKeyPipelineBase.java
package redis.clients.jedis;

import java.util.List;
import java.util.Map;
import java.util.Set;

public abstract class MultiKeyPipelineBase extends PipelineBase implements
    MultiKeyBinaryRedisPipeline, MultiKeyCommandsPipeline, ClusterPipeline,
    BinaryScriptingCommandsPipeline, ScriptingCommandsPipeline {

  protected Client client = null;

  public Response<List<String>> brpop(String... args) {
    client.brpop(args);
    return getResponse(BuilderFactory.STRING_LIST);
  }

  public Response<List<String>> brpop(int timeout, String... keys) {
    client.brpop(timeout, keys);
    return getResponse(BuilderFactory.STRING_LIST);
  }

  public Response<List<String>> blpop(String... args) {
    client.blpop(args);
    return getResponse(BuilderFactory.STRING_LIST);
  }

  public Response<List<String>> blpop(int timeout, String... keys) {
    client.blpop(timeout, keys);
    return getResponse(BuilderFactory.STRING_LIST);
  }

  public Response<Map<String, String>> blpopMap(int timeout, String... keys) {
    client.blpop(timeout, keys);
    return getResponse(BuilderFactory.STRING_MAP);
  }

  public Response<List<byte[]>> brpop(byte[]... args) {
    client.brpop(args);
    return getResponse(BuilderFactory.BYTE_ARRAY_LIST);
  }

  public Response<List<String>> brpop(int timeout, byte[]... keys) {
    client.brpop(timeout, keys);
    return getResponse(BuilderFactory.STRING_LIST);
  }

  public Response<Map<String, String>> brpopMap(int timeout, String... keys) {
    client.blpop(timeout, keys);
    return getResponse(BuilderFactory.STRING_MAP);
  }

  public Response<List<byte[]>> blpop(byte[]... args) {
    client.blpop(args);
    return getResponse(BuilderFactory.BYTE_ARRAY_LIST);
  }

  public Response<List<String>> blpop(int timeout, byte[]... keys) {
    client.blpop(timeout, keys);
    return getResponse(BuilderFactory.STRING_LIST);
  }

  public Response<Long> del(String... keys) {
    client.del(keys);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> del(byte[]... keys) {
    client.del(keys);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Set<String>> keys(String pattern) {
    getClient(pattern).keys(pattern);
    return getResponse(BuilderFactory.STRING_SET);
  }

  public Response<Set<byte[]>> keys(byte[] pattern) {
    getClient(pattern).keys(pattern);
    return getResponse(BuilderFactory.BYTE_ARRAY_ZSET);
  }

  public Response<List<String>> mget(String... keys) {
    client.mget(keys);
    return getResponse(BuilderFactory.STRING_LIST);
  }

  public Response<List<byte[]>> mget(byte[]... keys) {
    client.mget(keys);
    return getResponse(BuilderFactory.BYTE_ARRAY_LIST);
  }

  public Response<String> mset(String... keysvalues) {
    client.mset(keysvalues);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> mset(byte[]... keysvalues) {
    client.mset(keysvalues);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<Long> msetnx(String... keysvalues) {
    client.msetnx(keysvalues);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> msetnx(byte[]... keysvalues) {
    client.msetnx(keysvalues);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<String> rename(String oldkey, String newkey) {
    client.rename(oldkey, newkey);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> rename(byte[] oldkey, byte[] newkey) {
    client.rename(oldkey, newkey);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<Long> renamenx(String oldkey, String newkey) {
    client.renamenx(oldkey, newkey);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> renamenx(byte[] oldkey, byte[] newkey) {
    client.renamenx(oldkey, newkey);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<String> rpoplpush(String srckey, String dstkey) {
    client.rpoplpush(srckey, dstkey);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<byte[]> rpoplpush(byte[] srckey, byte[] dstkey) {
    client.rpoplpush(srckey, dstkey);
    return getResponse(BuilderFactory.BYTE_ARRAY);
  }

  public Response<Set<String>> sdiff(String... keys) {
    client.sdiff(keys);
    return getResponse(BuilderFactory.STRING_SET);
  }

  public Response<Set<byte[]>> sdiff(byte[]... keys) {
    client.sdiff(keys);
    return getResponse(BuilderFactory.BYTE_ARRAY_ZSET);
  }

  public Response<Long> sdiffstore(String dstkey, String... keys) {
    client.sdiffstore(dstkey, keys);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> sdiffstore(byte[] dstkey, byte[]... keys) {
    client.sdiffstore(dstkey, keys);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Set<String>> sinter(String... keys) {
    client.sinter(keys);
    return getResponse(BuilderFactory.STRING_SET);
  }

  public Response<Set<byte[]>> sinter(byte[]... keys) {
    client.sinter(keys);
    return getResponse(BuilderFactory.BYTE_ARRAY_ZSET);
  }

  public Response<Long> sinterstore(String dstkey, String... keys) {
    client.sinterstore(dstkey, keys);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> sinterstore(byte[] dstkey, byte[]... keys) {
    client.sinterstore(dstkey, keys);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> smove(String srckey, String dstkey, String member) {
    client.smove(srckey, dstkey, member);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> smove(byte[] srckey, byte[] dstkey, byte[] member) {
    client.smove(srckey, dstkey, member);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> sort(String key, SortingParams sortingParameters, String dstkey) {
    client.sort(key, sortingParameters, dstkey);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> sort(byte[] key, SortingParams sortingParameters, byte[] dstkey) {
    client.sort(key, sortingParameters, dstkey);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> sort(String key, String dstkey) {
    client.sort(key, dstkey);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> sort(byte[] key, byte[] dstkey) {
    client.sort(key, dstkey);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Set<String>> sunion(String... keys) {
    client.sunion(keys);
    return getResponse(BuilderFactory.STRING_SET);
  }

  public Response<Set<byte[]>> sunion(byte[]... keys) {
    client.sunion(keys);
    return getResponse(BuilderFactory.BYTE_ARRAY_ZSET);
  }

  public Response<Long> sunionstore(String dstkey, String... keys) {
    client.sunionstore(dstkey, keys);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> sunionstore(byte[] dstkey, byte[]... keys) {
    client.sunionstore(dstkey, keys);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<String> watch(String... keys) {
    client.watch(keys);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> watch(byte[]... keys) {
    client.watch(keys);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<Long> zinterstore(String dstkey, String... sets) {
    client.zinterstore(dstkey, sets);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> zinterstore(byte[] dstkey, byte[]... sets) {
    client.zinterstore(dstkey, sets);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> zinterstore(String dstkey, ZParams params, String... sets) {
    client.zinterstore(dstkey, params, sets);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> zinterstore(byte[] dstkey, ZParams params, byte[]... sets) {
    client.zinterstore(dstkey, params, sets);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> zunionstore(String dstkey, String... sets) {
    client.zunionstore(dstkey, sets);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> zunionstore(byte[] dstkey, byte[]... sets) {
    client.zunionstore(dstkey, sets);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> zunionstore(String dstkey, ZParams params, String... sets) {
    client.zunionstore(dstkey, params, sets);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> zunionstore(byte[] dstkey, ZParams params, byte[]... sets) {
    client.zunionstore(dstkey, params, sets);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<String> bgrewriteaof() {
    client.bgrewriteaof();
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> bgsave() {
    client.bgsave();
    return getResponse(BuilderFactory.STRING);
  }

  public Response<List<String>> configGet(String pattern) {
    client.configGet(pattern);
    return getResponse(BuilderFactory.STRING_LIST);
  }

  public Response<String> configSet(String parameter, String value) {
    client.configSet(parameter, value);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> brpoplpush(String source, String destination, int timeout) {
    client.brpoplpush(source, destination, timeout);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<byte[]> brpoplpush(byte[] source, byte[] destination, int timeout) {
    client.brpoplpush(source, destination, timeout);
    return getResponse(BuilderFactory.BYTE_ARRAY);
  }

  public Response<String> configResetStat() {
    client.configResetStat();
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> save() {
    client.save();
    return getResponse(BuilderFactory.STRING);
  }

  public Response<Long> lastsave() {
    client.lastsave();
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> publish(String channel, String message) {
    client.publish(channel, message);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> publish(byte[] channel, byte[] message) {
    client.publish(channel, message);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<String> randomKey() {
    client.randomKey();
    return getResponse(BuilderFactory.STRING);
  }

  public Response<byte[]> randomKeyBinary() {
    client.randomKey();
    return getResponse(BuilderFactory.BYTE_ARRAY);
  }

  public Response<String> flushDB() {
    client.flushDB();
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> flushAll() {
    client.flushAll();
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> info() {
    client.info();
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> info(final String section) {
    client.info(section);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<Long> dbSize() {
    client.dbSize();
    return getResponse(BuilderFactory.LONG);
  }

  public Response<String> shutdown() {
    client.shutdown();
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> ping() {
    client.ping();
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> select(int index) {
    client.select(index);
    Response<String> response = getResponse(BuilderFactory.STRING);
    client.setDb(index);

    return response;
  }

  public Response<Long> bitop(BitOP op, byte[] destKey, byte[]... srcKeys) {
    client.bitop(op, destKey, srcKeys);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> bitop(BitOP op, String destKey, String... srcKeys) {
    client.bitop(op, destKey, srcKeys);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<String> clusterNodes() {
    client.clusterNodes();
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> clusterMeet(final String ip, final int port) {
    client.clusterMeet(ip, port);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> clusterAddSlots(final int... slots) {
    client.clusterAddSlots(slots);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> clusterDelSlots(final int... slots) {
    client.clusterDelSlots(slots);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> clusterInfo() {
    client.clusterInfo();
    return getResponse(BuilderFactory.STRING);
  }

  public Response<List<String>> clusterGetKeysInSlot(final int slot, final int count) {
    client.clusterGetKeysInSlot(slot, count);
    return getResponse(BuilderFactory.STRING_LIST);
  }

  public Response<String> clusterSetSlotNode(final int slot, final String nodeId) {
    client.clusterSetSlotNode(slot, nodeId);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> clusterSetSlotMigrating(final int slot, final String nodeId) {
    client.clusterSetSlotMigrating(slot, nodeId);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> clusterSetSlotImporting(final int slot, final String nodeId) {
    client.clusterSetSlotImporting(slot, nodeId);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<Object> eval(String script) {
    return this.eval(script, 0, new String[0]);
  }

  public Response<Object> eval(String script, List<String> keys, List<String> args) {
    String[] argv = Jedis.getParams(keys, args);
    return this.eval(script, keys.size(), argv);
  }

  public Response<Object> eval(String script, int keyCount, String... params) {
    getClient(script).eval(script, keyCount, params);
    return getResponse(BuilderFactory.EVAL_RESULT);
  }

  public Response<Object> evalsha(String script) {
    return this.evalsha(script, 0, new String[0]);
  }

  public Response<Object> evalsha(String sha1, List<String> keys, List<String> args) {
    String[] argv = Jedis.getParams(keys, args);
    return this.evalsha(sha1, keys.size(), argv);
  }

  public Response<Object> evalsha(String sha1, int keyCount, String... params) {
    getClient(sha1).evalsha(sha1, keyCount, params);
    return getResponse(BuilderFactory.EVAL_RESULT);
  }

  public Response<Object> eval(byte[] script) {
    return this.eval(script, 0);
  }

  public Response<Object> eval(byte[] script, byte[] keyCount, byte[]... params) {
    getClient(script).eval(script, keyCount, params);
    return getResponse(BuilderFactory.EVAL_BINARY_RESULT);
  }

  public Response<Object> eval(byte[] script, List<byte[]> keys, List<byte[]> args) {
    byte[][] argv = BinaryJedis.getParamsWithBinary(keys, args);
    return this.eval(script, keys.size(), argv);
  }

  public Response<Object> eval(byte[] script, int keyCount, byte[]... params) {
    getClient(script).eval(script, keyCount, params);
    return getResponse(BuilderFactory.EVAL_BINARY_RESULT);
  }

  public Response<Object> evalsha(byte[] sha1) {
    return this.evalsha(sha1, 0);
  }

  public Response<Object> evalsha(byte[] sha1, List<byte[]> keys, List<byte[]> args) {
    byte[][] argv = BinaryJedis.getParamsWithBinary(keys, args);
    return this.evalsha(sha1, keys.size(), argv);
  }

  public Response<Object> evalsha(byte[] sha1, int keyCount, byte[]... params) {
    getClient(sha1).evalsha(sha1, keyCount, params);
    return getResponse(BuilderFactory.EVAL_BINARY_RESULT);
  }

  @Override
  public Response<Long> pfcount(String... keys) {
    client.pfcount(keys);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> pfcount(final byte[]... keys) {
    client.pfcount(keys);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<String> pfmerge(byte[] destkey, byte[]... sourcekeys) {
    client.pfmerge(destkey, sourcekeys);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<String> pfmerge(String destkey, String... sourcekeys) {
    client.pfmerge(destkey, sourcekeys);
    return getResponse(BuilderFactory.STRING);
  }

}


File: src/main/java/redis/clients/jedis/PipelineBase.java
package redis.clients.jedis;

import static redis.clients.jedis.Protocol.toByteArray;

import java.util.List;
import java.util.Map;
import java.util.Set;

import redis.clients.jedis.BinaryClient.LIST_POSITION;
import redis.clients.jedis.params.set.SetParams;

public abstract class PipelineBase extends Queable implements BinaryRedisPipeline, RedisPipeline {

  protected abstract Client getClient(String key);

  protected abstract Client getClient(byte[] key);

  @Override
  public Response<Long> append(String key, String value) {
    getClient(key).append(key, value);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> append(byte[] key, byte[] value) {
    getClient(key).append(key, value);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<List<String>> blpop(String key) {
    String[] temp = new String[1];
    temp[0] = key;
    getClient(key).blpop(temp);
    return getResponse(BuilderFactory.STRING_LIST);
  }

  @Override
  public Response<List<String>> brpop(String key) {
    String[] temp = new String[1];
    temp[0] = key;
    getClient(key).brpop(temp);
    return getResponse(BuilderFactory.STRING_LIST);
  }

  @Override
  public Response<List<byte[]>> blpop(byte[] key) {
    byte[][] temp = new byte[1][];
    temp[0] = key;
    getClient(key).blpop(temp);
    return getResponse(BuilderFactory.BYTE_ARRAY_LIST);
  }

  @Override
  public Response<List<byte[]>> brpop(byte[] key) {
    byte[][] temp = new byte[1][];
    temp[0] = key;
    getClient(key).brpop(temp);
    return getResponse(BuilderFactory.BYTE_ARRAY_LIST);
  }

  @Override
  public Response<Long> decr(String key) {
    getClient(key).decr(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> decr(byte[] key) {
    getClient(key).decr(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> decrBy(String key, long integer) {
    getClient(key).decrBy(key, integer);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> decrBy(byte[] key, long integer) {
    getClient(key).decrBy(key, integer);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> del(String key) {
    getClient(key).del(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> del(byte[] key) {
    getClient(key).del(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<String> echo(String string) {
    getClient(string).echo(string);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<byte[]> echo(byte[] string) {
    getClient(string).echo(string);
    return getResponse(BuilderFactory.BYTE_ARRAY);
  }

  @Override
  public Response<Boolean> exists(String key) {
    getClient(key).exists(key);
    return getResponse(BuilderFactory.BOOLEAN);
  }

  @Override
  public Response<Boolean> exists(byte[] key) {
    getClient(key).exists(key);
    return getResponse(BuilderFactory.BOOLEAN);
  }

  @Override
  public Response<Long> expire(String key, int seconds) {
    getClient(key).expire(key, seconds);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> expire(byte[] key, int seconds) {
    getClient(key).expire(key, seconds);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> expireAt(String key, long unixTime) {
    getClient(key).expireAt(key, unixTime);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> expireAt(byte[] key, long unixTime) {
    getClient(key).expireAt(key, unixTime);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<String> get(String key) {
    getClient(key).get(key);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<byte[]> get(byte[] key) {
    getClient(key).get(key);
    return getResponse(BuilderFactory.BYTE_ARRAY);
  }

  @Override
  public Response<Boolean> getbit(String key, long offset) {
    getClient(key).getbit(key, offset);
    return getResponse(BuilderFactory.BOOLEAN);
  }

  @Override
  public Response<Boolean> getbit(byte[] key, long offset) {
    getClient(key).getbit(key, offset);
    return getResponse(BuilderFactory.BOOLEAN);
  }

  public Response<Long> bitpos(final String key, final boolean value) {
    return bitpos(key, value, new BitPosParams());
  }

  public Response<Long> bitpos(final String key, final boolean value, final BitPosParams params) {
    getClient(key).bitpos(key, value, params);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> bitpos(final byte[] key, final boolean value) {
    return bitpos(key, value, new BitPosParams());
  }

  public Response<Long> bitpos(final byte[] key, final boolean value, final BitPosParams params) {
    getClient(key).bitpos(key, value, params);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<String> getrange(String key, long startOffset, long endOffset) {
    getClient(key).getrange(key, startOffset, endOffset);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<String> getSet(String key, String value) {
    getClient(key).getSet(key, value);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<byte[]> getSet(byte[] key, byte[] value) {
    getClient(key).getSet(key, value);
    return getResponse(BuilderFactory.BYTE_ARRAY);
  }

  @Override
  public Response<byte[]> getrange(byte[] key, long startOffset, long endOffset) {
    getClient(key).getrange(key, startOffset, endOffset);
    return getResponse(BuilderFactory.BYTE_ARRAY);
  }

  @Override
  public Response<Long> hdel(String key, String... field) {
    getClient(key).hdel(key, field);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> hdel(byte[] key, byte[]... field) {
    getClient(key).hdel(key, field);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Boolean> hexists(String key, String field) {
    getClient(key).hexists(key, field);
    return getResponse(BuilderFactory.BOOLEAN);
  }

  @Override
  public Response<Boolean> hexists(byte[] key, byte[] field) {
    getClient(key).hexists(key, field);
    return getResponse(BuilderFactory.BOOLEAN);
  }

  @Override
  public Response<String> hget(String key, String field) {
    getClient(key).hget(key, field);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<byte[]> hget(byte[] key, byte[] field) {
    getClient(key).hget(key, field);
    return getResponse(BuilderFactory.BYTE_ARRAY);
  }

  @Override
  public Response<Map<String, String>> hgetAll(String key) {
    getClient(key).hgetAll(key);
    return getResponse(BuilderFactory.STRING_MAP);
  }

  @Override
  public Response<Map<byte[], byte[]>> hgetAll(byte[] key) {
    getClient(key).hgetAll(key);
    return getResponse(BuilderFactory.BYTE_ARRAY_MAP);
  }

  @Override
  public Response<Long> hincrBy(String key, String field, long value) {
    getClient(key).hincrBy(key, field, value);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> hincrBy(byte[] key, byte[] field, long value) {
    getClient(key).hincrBy(key, field, value);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Set<String>> hkeys(String key) {
    getClient(key).hkeys(key);
    return getResponse(BuilderFactory.STRING_SET);
  }

  @Override
  public Response<Set<byte[]>> hkeys(byte[] key) {
    getClient(key).hkeys(key);
    return getResponse(BuilderFactory.BYTE_ARRAY_ZSET);
  }

  @Override
  public Response<Long> hlen(String key) {
    getClient(key).hlen(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> hlen(byte[] key) {
    getClient(key).hlen(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<List<String>> hmget(String key, String... fields) {
    getClient(key).hmget(key, fields);
    return getResponse(BuilderFactory.STRING_LIST);
  }

  @Override
  public Response<List<byte[]>> hmget(byte[] key, byte[]... fields) {
    getClient(key).hmget(key, fields);
    return getResponse(BuilderFactory.BYTE_ARRAY_LIST);
  }

  @Override
  public Response<String> hmset(String key, Map<String, String> hash) {
    getClient(key).hmset(key, hash);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<String> hmset(byte[] key, Map<byte[], byte[]> hash) {
    getClient(key).hmset(key, hash);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<Long> hset(String key, String field, String value) {
    getClient(key).hset(key, field, value);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> hset(byte[] key, byte[] field, byte[] value) {
    getClient(key).hset(key, field, value);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> hsetnx(String key, String field, String value) {
    getClient(key).hsetnx(key, field, value);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> hsetnx(byte[] key, byte[] field, byte[] value) {
    getClient(key).hsetnx(key, field, value);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<List<String>> hvals(String key) {
    getClient(key).hvals(key);
    return getResponse(BuilderFactory.STRING_LIST);
  }

  @Override
  public Response<List<byte[]>> hvals(byte[] key) {
    getClient(key).hvals(key);
    return getResponse(BuilderFactory.BYTE_ARRAY_LIST);
  }

  @Override
  public Response<Long> incr(String key) {
    getClient(key).incr(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> incr(byte[] key) {
    getClient(key).incr(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> incrBy(String key, long integer) {
    getClient(key).incrBy(key, integer);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> incrBy(byte[] key, long integer) {
    getClient(key).incrBy(key, integer);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<String> lindex(String key, long index) {
    getClient(key).lindex(key, index);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<byte[]> lindex(byte[] key, long index) {
    getClient(key).lindex(key, index);
    return getResponse(BuilderFactory.BYTE_ARRAY);
  }

  @Override
  public Response<Long> linsert(String key, LIST_POSITION where, String pivot, String value) {
    getClient(key).linsert(key, where, pivot, value);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> linsert(byte[] key, LIST_POSITION where, byte[] pivot, byte[] value) {
    getClient(key).linsert(key, where, pivot, value);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> llen(String key) {
    getClient(key).llen(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> llen(byte[] key) {
    getClient(key).llen(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<String> lpop(String key) {
    getClient(key).lpop(key);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<byte[]> lpop(byte[] key) {
    getClient(key).lpop(key);
    return getResponse(BuilderFactory.BYTE_ARRAY);
  }

  @Override
  public Response<Long> lpush(String key, String... string) {
    getClient(key).lpush(key, string);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> lpush(byte[] key, byte[]... string) {
    getClient(key).lpush(key, string);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> lpushx(String key, String... string) {
    getClient(key).lpushx(key, string);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> lpushx(byte[] key, byte[]... bytes) {
    getClient(key).lpushx(key, bytes);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<List<String>> lrange(String key, long start, long end) {
    getClient(key).lrange(key, start, end);
    return getResponse(BuilderFactory.STRING_LIST);
  }

  @Override
  public Response<List<byte[]>> lrange(byte[] key, long start, long end) {
    getClient(key).lrange(key, start, end);
    return getResponse(BuilderFactory.BYTE_ARRAY_LIST);
  }

  @Override
  public Response<Long> lrem(String key, long count, String value) {
    getClient(key).lrem(key, count, value);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> lrem(byte[] key, long count, byte[] value) {
    getClient(key).lrem(key, count, value);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<String> lset(String key, long index, String value) {
    getClient(key).lset(key, index, value);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<String> lset(byte[] key, long index, byte[] value) {
    getClient(key).lset(key, index, value);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<String> ltrim(String key, long start, long end) {
    getClient(key).ltrim(key, start, end);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<String> ltrim(byte[] key, long start, long end) {
    getClient(key).ltrim(key, start, end);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<Long> move(String key, int dbIndex) {
    getClient(key).move(key, dbIndex);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> move(byte[] key, int dbIndex) {
    getClient(key).move(key, dbIndex);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> persist(String key) {
    getClient(key).persist(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> persist(byte[] key) {
    getClient(key).persist(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<String> rpop(String key) {
    getClient(key).rpop(key);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<byte[]> rpop(byte[] key) {
    getClient(key).rpop(key);
    return getResponse(BuilderFactory.BYTE_ARRAY);
  }

  @Override
  public Response<Long> rpush(String key, String... string) {
    getClient(key).rpush(key, string);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> rpush(byte[] key, byte[]... string) {
    getClient(key).rpush(key, string);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> rpushx(String key, String... string) {
    getClient(key).rpushx(key, string);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> rpushx(byte[] key, byte[]... string) {
    getClient(key).rpushx(key, string);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> sadd(String key, String... member) {
    getClient(key).sadd(key, member);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> sadd(byte[] key, byte[]... member) {
    getClient(key).sadd(key, member);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> scard(String key) {
    getClient(key).scard(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> scard(byte[] key) {
    getClient(key).scard(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<String> set(String key, String value) {
    getClient(key).set(key, value);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<String> set(byte[] key, byte[] value) {
    getClient(key).set(key, value);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> set(String key, String value, SetParams params) {
    getClient(key).set(key, value, params);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> set(byte[] key, byte[] value, SetParams params) {
    getClient(key).set(key, value, params);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<Boolean> setbit(String key, long offset, boolean value) {
    getClient(key).setbit(key, offset, value);
    return getResponse(BuilderFactory.BOOLEAN);
  }

  @Override
  public Response<Boolean> setbit(byte[] key, long offset, byte[] value) {
    getClient(key).setbit(key, offset, value);
    return getResponse(BuilderFactory.BOOLEAN);
  }

  @Override
  public Response<String> setex(String key, int seconds, String value) {
    getClient(key).setex(key, seconds, value);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<String> setex(byte[] key, int seconds, byte[] value) {
    getClient(key).setex(key, seconds, value);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<Long> setnx(String key, String value) {
    getClient(key).setnx(key, value);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> setnx(byte[] key, byte[] value) {
    getClient(key).setnx(key, value);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> setrange(String key, long offset, String value) {
    getClient(key).setrange(key, offset, value);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> setrange(byte[] key, long offset, byte[] value) {
    getClient(key).setrange(key, offset, value);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Boolean> sismember(String key, String member) {
    getClient(key).sismember(key, member);
    return getResponse(BuilderFactory.BOOLEAN);
  }

  @Override
  public Response<Boolean> sismember(byte[] key, byte[] member) {
    getClient(key).sismember(key, member);
    return getResponse(BuilderFactory.BOOLEAN);
  }

  @Override
  public Response<Set<String>> smembers(String key) {
    getClient(key).smembers(key);
    return getResponse(BuilderFactory.STRING_SET);
  }

  @Override
  public Response<Set<byte[]>> smembers(byte[] key) {
    getClient(key).smembers(key);
    return getResponse(BuilderFactory.BYTE_ARRAY_ZSET);
  }

  @Override
  public Response<List<String>> sort(String key) {
    getClient(key).sort(key);
    return getResponse(BuilderFactory.STRING_LIST);
  }

  @Override
  public Response<List<byte[]>> sort(byte[] key) {
    getClient(key).sort(key);
    return getResponse(BuilderFactory.BYTE_ARRAY_LIST);
  }

  @Override
  public Response<List<String>> sort(String key, SortingParams sortingParameters) {
    getClient(key).sort(key, sortingParameters);
    return getResponse(BuilderFactory.STRING_LIST);
  }

  @Override
  public Response<List<byte[]>> sort(byte[] key, SortingParams sortingParameters) {
    getClient(key).sort(key, sortingParameters);
    return getResponse(BuilderFactory.BYTE_ARRAY_LIST);
  }

  @Override
  public Response<String> spop(String key) {
    getClient(key).spop(key);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<Set<String>> spop(String key, long count) {
    getClient(key).spop(key, count);
    return getResponse(BuilderFactory.STRING_SET);
  }

  @Override
  public Response<byte[]> spop(byte[] key) {
    getClient(key).spop(key);
    return getResponse(BuilderFactory.BYTE_ARRAY);
  }

  @Override
  public Response<Set<byte[]>> spop(byte[] key, long count) {
    getClient(key).spop(key, count);
    return getResponse(BuilderFactory.BYTE_ARRAY_ZSET);
  }

  @Override
  public Response<String> srandmember(String key) {
    getClient(key).srandmember(key);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<List<String>> srandmember(String key, int count) {
    getClient(key).srandmember(key, count);
    return getResponse(BuilderFactory.STRING_LIST);
  }

  @Override
  public Response<byte[]> srandmember(byte[] key) {
    getClient(key).srandmember(key);
    return getResponse(BuilderFactory.BYTE_ARRAY);
  }

  public Response<List<byte[]>> srandmember(byte[] key, int count) {
    getClient(key).srandmember(key, count);
    return getResponse(BuilderFactory.BYTE_ARRAY_LIST);
  }

  @Override
  public Response<Long> srem(String key, String... member) {
    getClient(key).srem(key, member);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> srem(byte[] key, byte[]... member) {
    getClient(key).srem(key, member);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> strlen(String key) {
    getClient(key).strlen(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> strlen(byte[] key) {
    getClient(key).strlen(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<String> substr(String key, int start, int end) {
    getClient(key).substr(key, start, end);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<String> substr(byte[] key, int start, int end) {
    getClient(key).substr(key, start, end);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<Long> ttl(String key) {
    getClient(key).ttl(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> ttl(byte[] key) {
    getClient(key).ttl(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<String> type(String key) {
    getClient(key).type(key);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<String> type(byte[] key) {
    getClient(key).type(key);
    return getResponse(BuilderFactory.STRING);
  }

  @Override
  public Response<Long> zadd(String key, double score, String member) {
    getClient(key).zadd(key, score, member);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> zadd(String key, Map<String, Double> scoreMembers) {
    getClient(key).zadd(key, scoreMembers);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> zadd(byte[] key, double score, byte[] member) {
    getClient(key).zadd(key, score, member);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> zcard(String key) {
    getClient(key).zcard(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> zcard(byte[] key) {
    getClient(key).zcard(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> zcount(String key, double min, double max) {
    getClient(key).zcount(key, min, max);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> zcount(String key, String min, String max) {
    getClient(key).zcount(key, min, max);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> zcount(byte[] key, double min, double max) {
    getClient(key).zcount(key, toByteArray(min), toByteArray(max));
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> zcount(byte[] key, byte[] min, byte[] max) {
    getClient(key).zcount(key, min, max);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Double> zincrby(String key, double score, String member) {
    getClient(key).zincrby(key, score, member);
    return getResponse(BuilderFactory.DOUBLE);
  }

  @Override
  public Response<Double> zincrby(byte[] key, double score, byte[] member) {
    getClient(key).zincrby(key, score, member);
    return getResponse(BuilderFactory.DOUBLE);
  }

  @Override
  public Response<Set<String>> zrange(String key, long start, long end) {
    getClient(key).zrange(key, start, end);
    return getResponse(BuilderFactory.STRING_ZSET);
  }

  @Override
  public Response<Set<byte[]>> zrange(byte[] key, long start, long end) {
    getClient(key).zrange(key, start, end);
    return getResponse(BuilderFactory.BYTE_ARRAY_ZSET);
  }

  @Override
  public Response<Set<String>> zrangeByScore(String key, double min, double max) {
    getClient(key).zrangeByScore(key, min, max);
    return getResponse(BuilderFactory.STRING_ZSET);
  }

  @Override
  public Response<Set<byte[]>> zrangeByScore(byte[] key, double min, double max) {
    return zrangeByScore(key, toByteArray(min), toByteArray(max));
  }

  @Override
  public Response<Set<String>> zrangeByScore(String key, String min, String max) {
    getClient(key).zrangeByScore(key, min, max);
    return getResponse(BuilderFactory.STRING_ZSET);
  }

  @Override
  public Response<Set<byte[]>> zrangeByScore(byte[] key, byte[] min, byte[] max) {
    getClient(key).zrangeByScore(key, min, max);
    return getResponse(BuilderFactory.BYTE_ARRAY_ZSET);
  }

  @Override
  public Response<Set<String>> zrangeByScore(String key, double min, double max, int offset,
      int count) {
    getClient(key).zrangeByScore(key, min, max, offset, count);
    return getResponse(BuilderFactory.STRING_ZSET);
  }

  public Response<Set<String>> zrangeByScore(String key, String min, String max, int offset,
      int count) {
    getClient(key).zrangeByScore(key, min, max, offset, count);
    return getResponse(BuilderFactory.STRING_ZSET);
  }

  @Override
  public Response<Set<byte[]>> zrangeByScore(byte[] key, double min, double max, int offset,
      int count) {
    return zrangeByScore(key, toByteArray(min), toByteArray(max), offset, count);
  }

  @Override
  public Response<Set<byte[]>> zrangeByScore(byte[] key, byte[] min, byte[] max, int offset,
      int count) {
    getClient(key).zrangeByScore(key, min, max, offset, count);
    return getResponse(BuilderFactory.BYTE_ARRAY_ZSET);
  }

  @Override
  public Response<Set<Tuple>> zrangeByScoreWithScores(String key, double min, double max) {
    getClient(key).zrangeByScoreWithScores(key, min, max);
    return getResponse(BuilderFactory.TUPLE_ZSET);
  }

  public Response<Set<Tuple>> zrangeByScoreWithScores(String key, String min, String max) {
    getClient(key).zrangeByScoreWithScores(key, min, max);
    return getResponse(BuilderFactory.TUPLE_ZSET);
  }

  @Override
  public Response<Set<Tuple>> zrangeByScoreWithScores(byte[] key, double min, double max) {
    return zrangeByScoreWithScores(key, toByteArray(min), toByteArray(max));
  }

  @Override
  public Response<Set<Tuple>> zrangeByScoreWithScores(byte[] key, byte[] min, byte[] max) {
    getClient(key).zrangeByScoreWithScores(key, min, max);
    return getResponse(BuilderFactory.TUPLE_ZSET_BINARY);
  }

  @Override
  public Response<Set<Tuple>> zrangeByScoreWithScores(String key, double min, double max,
      int offset, int count) {
    getClient(key).zrangeByScoreWithScores(key, min, max, offset, count);
    return getResponse(BuilderFactory.TUPLE_ZSET);
  }

  public Response<Set<Tuple>> zrangeByScoreWithScores(String key, String min, String max,
      int offset, int count) {
    getClient(key).zrangeByScoreWithScores(key, min, max, offset, count);
    return getResponse(BuilderFactory.TUPLE_ZSET);
  }

  @Override
  public Response<Set<Tuple>> zrangeByScoreWithScores(byte[] key, double min, double max,
      int offset, int count) {
    getClient(key).zrangeByScoreWithScores(key, toByteArray(min), toByteArray(max), offset, count);
    return getResponse(BuilderFactory.TUPLE_ZSET_BINARY);
  }

  @Override
  public Response<Set<Tuple>> zrangeByScoreWithScores(byte[] key, byte[] min, byte[] max,
      int offset, int count) {
    getClient(key).zrangeByScoreWithScores(key, min, max, offset, count);
    return getResponse(BuilderFactory.TUPLE_ZSET_BINARY);
  }

  @Override
  public Response<Set<String>> zrevrangeByScore(String key, double max, double min) {
    getClient(key).zrevrangeByScore(key, max, min);
    return getResponse(BuilderFactory.STRING_ZSET);
  }

  @Override
  public Response<Set<byte[]>> zrevrangeByScore(byte[] key, double max, double min) {
    getClient(key).zrevrangeByScore(key, toByteArray(max), toByteArray(min));
    return getResponse(BuilderFactory.BYTE_ARRAY_ZSET);
  }

  @Override
  public Response<Set<String>> zrevrangeByScore(String key, String max, String min) {
    getClient(key).zrevrangeByScore(key, max, min);
    return getResponse(BuilderFactory.STRING_ZSET);
  }

  @Override
  public Response<Set<byte[]>> zrevrangeByScore(byte[] key, byte[] max, byte[] min) {
    getClient(key).zrevrangeByScore(key, max, min);
    return getResponse(BuilderFactory.BYTE_ARRAY_ZSET);
  }

  @Override
  public Response<Set<String>> zrevrangeByScore(String key, double max, double min, int offset,
      int count) {
    getClient(key).zrevrangeByScore(key, max, min, offset, count);
    return getResponse(BuilderFactory.STRING_ZSET);
  }

  public Response<Set<String>> zrevrangeByScore(String key, String max, String min, int offset,
      int count) {
    getClient(key).zrevrangeByScore(key, max, min, offset, count);
    return getResponse(BuilderFactory.STRING_ZSET);
  }

  @Override
  public Response<Set<byte[]>> zrevrangeByScore(byte[] key, double max, double min, int offset,
      int count) {
    getClient(key).zrevrangeByScore(key, toByteArray(max), toByteArray(min), offset, count);
    return getResponse(BuilderFactory.BYTE_ARRAY_ZSET);
  }

  @Override
  public Response<Set<byte[]>> zrevrangeByScore(byte[] key, byte[] max, byte[] min, int offset,
      int count) {
    getClient(key).zrevrangeByScore(key, max, min, offset, count);
    return getResponse(BuilderFactory.BYTE_ARRAY_ZSET);
  }

  @Override
  public Response<Set<Tuple>> zrevrangeByScoreWithScores(String key, double max, double min) {
    getClient(key).zrevrangeByScoreWithScores(key, max, min);
    return getResponse(BuilderFactory.TUPLE_ZSET);
  }

  public Response<Set<Tuple>> zrevrangeByScoreWithScores(String key, String max, String min) {
    getClient(key).zrevrangeByScoreWithScores(key, max, min);
    return getResponse(BuilderFactory.TUPLE_ZSET);
  }

  @Override
  public Response<Set<Tuple>> zrevrangeByScoreWithScores(byte[] key, double max, double min) {
    getClient(key).zrevrangeByScoreWithScores(key, toByteArray(max), toByteArray(min));
    return getResponse(BuilderFactory.TUPLE_ZSET_BINARY);
  }

  @Override
  public Response<Set<Tuple>> zrevrangeByScoreWithScores(byte[] key, byte[] max, byte[] min) {
    getClient(key).zrevrangeByScoreWithScores(key, max, min);
    return getResponse(BuilderFactory.TUPLE_ZSET_BINARY);
  }

  @Override
  public Response<Set<Tuple>> zrevrangeByScoreWithScores(String key, double max, double min,
      int offset, int count) {
    getClient(key).zrevrangeByScoreWithScores(key, max, min, offset, count);
    return getResponse(BuilderFactory.TUPLE_ZSET);
  }

  public Response<Set<Tuple>> zrevrangeByScoreWithScores(String key, String max, String min,
      int offset, int count) {
    getClient(key).zrevrangeByScoreWithScores(key, max, min, offset, count);
    return getResponse(BuilderFactory.TUPLE_ZSET);
  }

  @Override
  public Response<Set<Tuple>> zrevrangeByScoreWithScores(byte[] key, double max, double min,
      int offset, int count) {
    getClient(key).zrevrangeByScoreWithScores(key, toByteArray(max), toByteArray(min), offset,
      count);
    return getResponse(BuilderFactory.TUPLE_ZSET_BINARY);
  }

  @Override
  public Response<Set<Tuple>> zrevrangeByScoreWithScores(byte[] key, byte[] max, byte[] min,
      int offset, int count) {
    getClient(key).zrevrangeByScoreWithScores(key, max, min, offset, count);
    return getResponse(BuilderFactory.TUPLE_ZSET_BINARY);
  }

  @Override
  public Response<Set<Tuple>> zrangeWithScores(String key, long start, long end) {
    getClient(key).zrangeWithScores(key, start, end);
    return getResponse(BuilderFactory.TUPLE_ZSET);
  }

  @Override
  public Response<Set<Tuple>> zrangeWithScores(byte[] key, long start, long end) {
    getClient(key).zrangeWithScores(key, start, end);
    return getResponse(BuilderFactory.TUPLE_ZSET_BINARY);
  }

  @Override
  public Response<Long> zrank(String key, String member) {
    getClient(key).zrank(key, member);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> zrank(byte[] key, byte[] member) {
    getClient(key).zrank(key, member);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> zrem(String key, String... member) {
    getClient(key).zrem(key, member);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> zrem(byte[] key, byte[]... member) {
    getClient(key).zrem(key, member);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> zremrangeByRank(String key, long start, long end) {
    getClient(key).zremrangeByRank(key, start, end);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> zremrangeByRank(byte[] key, long start, long end) {
    getClient(key).zremrangeByRank(key, start, end);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> zremrangeByScore(String key, double start, double end) {
    getClient(key).zremrangeByScore(key, start, end);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> zremrangeByScore(String key, String start, String end) {
    getClient(key).zremrangeByScore(key, start, end);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> zremrangeByScore(byte[] key, double start, double end) {
    getClient(key).zremrangeByScore(key, toByteArray(start), toByteArray(end));
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> zremrangeByScore(byte[] key, byte[] start, byte[] end) {
    getClient(key).zremrangeByScore(key, start, end);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Set<String>> zrevrange(String key, long start, long end) {
    getClient(key).zrevrange(key, start, end);
    return getResponse(BuilderFactory.STRING_ZSET);
  }

  @Override
  public Response<Set<byte[]>> zrevrange(byte[] key, long start, long end) {
    getClient(key).zrevrange(key, start, end);
    return getResponse(BuilderFactory.BYTE_ARRAY_ZSET);
  }

  @Override
  public Response<Set<Tuple>> zrevrangeWithScores(String key, long start, long end) {
    getClient(key).zrevrangeWithScores(key, start, end);
    return getResponse(BuilderFactory.TUPLE_ZSET);
  }

  @Override
  public Response<Set<Tuple>> zrevrangeWithScores(byte[] key, long start, long end) {
    getClient(key).zrevrangeWithScores(key, start, end);
    return getResponse(BuilderFactory.TUPLE_ZSET);
  }

  @Override
  public Response<Long> zrevrank(String key, String member) {
    getClient(key).zrevrank(key, member);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> zrevrank(byte[] key, byte[] member) {
    getClient(key).zrevrank(key, member);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Double> zscore(String key, String member) {
    getClient(key).zscore(key, member);
    return getResponse(BuilderFactory.DOUBLE);
  }

  @Override
  public Response<Double> zscore(byte[] key, byte[] member) {
    getClient(key).zscore(key, member);
    return getResponse(BuilderFactory.DOUBLE);
  }

  @Override
  public Response<Long> zlexcount(final byte[] key, final byte[] min, final byte[] max) {
    getClient(key).zlexcount(key, min, max);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> zlexcount(final String key, final String min, final String max) {
    getClient(key).zlexcount(key, min, max);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Set<byte[]>> zrangeByLex(final byte[] key, final byte[] min, final byte[] max) {
    getClient(key).zrangeByLex(key, min, max);
    return getResponse(BuilderFactory.BYTE_ARRAY_ZSET);
  }

  @Override
  public Response<Set<String>> zrangeByLex(final String key, final String min, final String max) {
    getClient(key).zrangeByLex(key, min, max);
    return getResponse(BuilderFactory.STRING_ZSET);
  }

  @Override
  public Response<Set<byte[]>> zrangeByLex(final byte[] key, final byte[] min, final byte[] max,
      final int offset, final int count) {
    getClient(key).zrangeByLex(key, min, max, offset, count);
    return getResponse(BuilderFactory.BYTE_ARRAY_ZSET);
  }

  @Override
  public Response<Set<String>> zrangeByLex(final String key, final String min, final String max,
      final int offset, final int count) {
    getClient(key).zrangeByLex(key, min, max, offset, count);
    return getResponse(BuilderFactory.STRING_ZSET);
  }

  @Override
  public Response<Set<byte[]>> zrevrangeByLex(final byte[] key, final byte[] max, final byte[] min) {
    getClient(key).zrevrangeByLex(key, max, min);
    return getResponse(BuilderFactory.BYTE_ARRAY_ZSET);
  }

  @Override
  public Response<Set<String>> zrevrangeByLex(final String key, final String max, final String min) {
    getClient(key).zrevrangeByLex(key, max, min);
    return getResponse(BuilderFactory.STRING_ZSET);
  }

  @Override
  public Response<Set<byte[]>> zrevrangeByLex(final byte[] key, final byte[] max, final byte[] min,
      final int offset, final int count) {
    getClient(key).zrevrangeByLex(key, max, min, offset, count);
    return getResponse(BuilderFactory.BYTE_ARRAY_ZSET);
  }

  @Override
  public Response<Set<String>> zrevrangeByLex(final String key, final String max, final String min,
      final int offset, final int count) {
    getClient(key).zrevrangeByLex(key, max, min, offset, count);
    return getResponse(BuilderFactory.STRING_ZSET);
  }

  @Override
  public Response<Long> zremrangeByLex(final byte[] key, final byte[] min, final byte[] max) {
    getClient(key).zremrangeByLex(key, min, max);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> zremrangeByLex(final String key, final String min, final String max) {
    getClient(key).zremrangeByLex(key, min, max);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> bitcount(String key) {
    getClient(key).bitcount(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> bitcount(String key, long start, long end) {
    getClient(key).bitcount(key, start, end);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> bitcount(byte[] key) {
    getClient(key).bitcount(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> bitcount(byte[] key, long start, long end) {
    getClient(key).bitcount(key, start, end);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<byte[]> dump(String key) {
    getClient(key).dump(key);
    return getResponse(BuilderFactory.BYTE_ARRAY);
  }

  public Response<byte[]> dump(byte[] key) {
    getClient(key).dump(key);
    return getResponse(BuilderFactory.BYTE_ARRAY);
  }

  public Response<String> migrate(String host, int port, String key, int destinationDb, int timeout) {
    getClient(key).migrate(host, port, key, destinationDb, timeout);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> migrate(byte[] host, int port, byte[] key, int destinationDb, int timeout) {
    getClient(key).migrate(host, port, key, destinationDb, timeout);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<Long> objectRefcount(String key) {
    getClient(key).objectRefcount(key);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> objectRefcount(byte[] key) {
    getClient(key).objectRefcount(key);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<String> objectEncoding(String key) {
    getClient(key).objectEncoding(key);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<byte[]> objectEncoding(byte[] key) {
    getClient(key).objectEncoding(key);
    return getResponse(BuilderFactory.BYTE_ARRAY);
  }

  public Response<Long> objectIdletime(String key) {
    getClient(key).objectIdletime(key);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> objectIdletime(byte[] key) {
    getClient(key).objectIdletime(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> pexpire(String key, long milliseconds) {
    getClient(key).pexpire(key, milliseconds);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> pexpire(byte[] key, long milliseconds) {
    getClient(key).pexpire(key, milliseconds);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> pexpireAt(String key, long millisecondsTimestamp) {
    getClient(key).pexpireAt(key, millisecondsTimestamp);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> pexpireAt(byte[] key, long millisecondsTimestamp) {
    getClient(key).pexpireAt(key, millisecondsTimestamp);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> pttl(String key) {
    getClient(key).pttl(key);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<Long> pttl(byte[] key) {
    getClient(key).pttl(key);
    return getResponse(BuilderFactory.LONG);
  }

  public Response<String> restore(String key, int ttl, byte[] serializedValue) {
    getClient(key).restore(key, ttl, serializedValue);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> restore(byte[] key, int ttl, byte[] serializedValue) {
    getClient(key).restore(key, ttl, serializedValue);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<Double> incrByFloat(String key, double increment) {
    getClient(key).incrByFloat(key, increment);
    return getResponse(BuilderFactory.DOUBLE);
  }

  public Response<Double> incrByFloat(byte[] key, double increment) {
    getClient(key).incrByFloat(key, increment);
    return getResponse(BuilderFactory.DOUBLE);
  }

  public Response<String> psetex(String key, long milliseconds, String value) {
    getClient(key).psetex(key, milliseconds, value);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<String> psetex(byte[] key, long milliseconds, byte[] value) {
    getClient(key).psetex(key, milliseconds, value);
    return getResponse(BuilderFactory.STRING);
  }

  public Response<Double> hincrByFloat(String key, String field, double increment) {
    getClient(key).hincrByFloat(key, field, increment);
    return getResponse(BuilderFactory.DOUBLE);
  }

  public Response<Double> hincrByFloat(byte[] key, byte[] field, double increment) {
    getClient(key).hincrByFloat(key, field, increment);
    return getResponse(BuilderFactory.DOUBLE);
  }

  @Override
  public Response<Long> pfadd(byte[] key, byte[]... elements) {
    getClient(key).pfadd(key, elements);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> pfcount(byte[] key) {
    getClient(key).pfcount(key);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> pfadd(String key, String... elements) {
    getClient(key).pfadd(key, elements);
    return getResponse(BuilderFactory.LONG);
  }

  @Override
  public Response<Long> pfcount(String key) {
    getClient(key).pfcount(key);
    return getResponse(BuilderFactory.LONG);
  }

}


File: src/main/java/redis/clients/jedis/Protocol.java
package redis.clients.jedis;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import redis.clients.jedis.exceptions.JedisAskDataException;
import redis.clients.jedis.exceptions.JedisClusterException;
import redis.clients.jedis.exceptions.JedisConnectionException;
import redis.clients.jedis.exceptions.JedisDataException;
import redis.clients.jedis.exceptions.JedisMovedDataException;
import redis.clients.util.RedisInputStream;
import redis.clients.util.RedisOutputStream;
import redis.clients.util.SafeEncoder;

public final class Protocol {

  private static final String ASK_RESPONSE = "ASK";
  private static final String MOVED_RESPONSE = "MOVED";
  private static final String CLUSTERDOWN_RESPONSE = "CLUSTERDOWN";
  public static final String DEFAULT_HOST = "localhost";
  public static final int DEFAULT_PORT = 6379;
  public static final int DEFAULT_SENTINEL_PORT = 26379;
  public static final int DEFAULT_TIMEOUT = 2000;
  public static final int DEFAULT_DATABASE = 0;

  public static final String CHARSET = "UTF-8";

  public static final byte DOLLAR_BYTE = '$';
  public static final byte ASTERISK_BYTE = '*';
  public static final byte PLUS_BYTE = '+';
  public static final byte MINUS_BYTE = '-';
  public static final byte COLON_BYTE = ':';

  public static final String SENTINEL_MASTERS = "masters";
  public static final String SENTINEL_GET_MASTER_ADDR_BY_NAME = "get-master-addr-by-name";
  public static final String SENTINEL_RESET = "reset";
  public static final String SENTINEL_SLAVES = "slaves";
  public static final String SENTINEL_FAILOVER = "failover";
  public static final String SENTINEL_MONITOR = "monitor";
  public static final String SENTINEL_REMOVE = "remove";
  public static final String SENTINEL_SET = "set";

  public static final String CLUSTER_NODES = "nodes";
  public static final String CLUSTER_MEET = "meet";
  public static final String CLUSTER_RESET = "reset";
  public static final String CLUSTER_ADDSLOTS = "addslots";
  public static final String CLUSTER_DELSLOTS = "delslots";
  public static final String CLUSTER_INFO = "info";
  public static final String CLUSTER_GETKEYSINSLOT = "getkeysinslot";
  public static final String CLUSTER_SETSLOT = "setslot";
  public static final String CLUSTER_SETSLOT_NODE = "node";
  public static final String CLUSTER_SETSLOT_MIGRATING = "migrating";
  public static final String CLUSTER_SETSLOT_IMPORTING = "importing";
  public static final String CLUSTER_SETSLOT_STABLE = "stable";
  public static final String CLUSTER_FORGET = "forget";
  public static final String CLUSTER_FLUSHSLOT = "flushslots";
  public static final String CLUSTER_KEYSLOT = "keyslot";
  public static final String CLUSTER_COUNTKEYINSLOT = "countkeysinslot";
  public static final String CLUSTER_SAVECONFIG = "saveconfig";
  public static final String CLUSTER_REPLICATE = "replicate";
  public static final String CLUSTER_SLAVES = "slaves";
  public static final String CLUSTER_FAILOVER = "failover";
  public static final String CLUSTER_SLOTS = "slots";
  public static final String PUBSUB_CHANNELS = "channels";
  public static final String PUBSUB_NUMSUB = "numsub";
  public static final String PUBSUB_NUM_PAT = "numpat";

  public static final byte[] BYTES_TRUE = toByteArray(1);
  public static final byte[] BYTES_FALSE = toByteArray(0);

  private Protocol() {
    // this prevent the class from instantiation
  }

  public static void sendCommand(final RedisOutputStream os, final ProtocolCommand command,
      final byte[]... args) {
    sendCommand(os, command.getRaw(), args);
  }

  private static void sendCommand(final RedisOutputStream os, final byte[] command,
      final byte[]... args) {
    try {
      os.write(ASTERISK_BYTE);
      os.writeIntCrLf(args.length + 1);
      os.write(DOLLAR_BYTE);
      os.writeIntCrLf(command.length);
      os.write(command);
      os.writeCrLf();

      for (final byte[] arg : args) {
        os.write(DOLLAR_BYTE);
        os.writeIntCrLf(arg.length);
        os.write(arg);
        os.writeCrLf();
      }
    } catch (IOException e) {
      throw new JedisConnectionException(e);
    }
  }

  private static void processError(final RedisInputStream is) {
    String message = is.readLine();
    // TODO: I'm not sure if this is the best way to do this.
    // Maybe Read only first 5 bytes instead?
    if (message.startsWith(MOVED_RESPONSE)) {
      String[] movedInfo = parseTargetHostAndSlot(message);
      throw new JedisMovedDataException(message, new HostAndPort(movedInfo[1],
          Integer.valueOf(movedInfo[2])), Integer.valueOf(movedInfo[0]));
    } else if (message.startsWith(ASK_RESPONSE)) {
      String[] askInfo = parseTargetHostAndSlot(message);
      throw new JedisAskDataException(message, new HostAndPort(askInfo[1],
          Integer.valueOf(askInfo[2])), Integer.valueOf(askInfo[0]));
    } else if (message.startsWith(CLUSTERDOWN_RESPONSE)) {
      throw new JedisClusterException(message);
    }
    throw new JedisDataException(message);
  }

  public static String readErrorLineIfPossible(RedisInputStream is) {
    final byte b = is.readByte();
    // if buffer contains other type of response, just ignore.
    if (b != MINUS_BYTE) {
      return null;
    }
    return is.readLine();
  }

  private static String[] parseTargetHostAndSlot(String clusterRedirectResponse) {
    String[] response = new String[3];
    String[] messageInfo = clusterRedirectResponse.split(" ");
    String[] targetHostAndPort = messageInfo[2].split(":");
    response[0] = messageInfo[1];
    response[1] = targetHostAndPort[0];
    response[2] = targetHostAndPort[1];
    return response;
  }

  private static Object process(final RedisInputStream is) {

    final byte b = is.readByte();
    if (b == PLUS_BYTE) {
      return processStatusCodeReply(is);
    } else if (b == DOLLAR_BYTE) {
      return processBulkReply(is);
    } else if (b == ASTERISK_BYTE) {
      return processMultiBulkReply(is);
    } else if (b == COLON_BYTE) {
      return processInteger(is);
    } else if (b == MINUS_BYTE) {
      processError(is);
      return null;
    } else {
      throw new JedisConnectionException("Unknown reply: " + (char) b);
    }
  }

  private static byte[] processStatusCodeReply(final RedisInputStream is) {
    return is.readLineBytes();
  }

  private static byte[] processBulkReply(final RedisInputStream is) {
    final int len = is.readIntCrLf();
    if (len == -1) {
      return null;
    }

    final byte[] read = new byte[len];
    int offset = 0;
    while (offset < len) {
      final int size = is.read(read, offset, (len - offset));
      if (size == -1) throw new JedisConnectionException(
          "It seems like server has closed the connection.");
      offset += size;
    }

    // read 2 more bytes for the command delimiter
    is.readByte();
    is.readByte();

    return read;
  }

  private static Long processInteger(final RedisInputStream is) {
    return is.readLongCrLf();
  }

  private static List<Object> processMultiBulkReply(final RedisInputStream is) {
    final int num = is.readIntCrLf();
    if (num == -1) {
      return null;
    }
    final List<Object> ret = new ArrayList<Object>(num);
    for (int i = 0; i < num; i++) {
      try {
        ret.add(process(is));
      } catch (JedisDataException e) {
        ret.add(e);
      }
    }
    return ret;
  }

  public static Object read(final RedisInputStream is) {
    return process(is);
  }

  public static final byte[] toByteArray(final boolean value) {
    return value ? BYTES_TRUE : BYTES_FALSE;
  }

  public static final byte[] toByteArray(final int value) {
    return SafeEncoder.encode(String.valueOf(value));
  }

  public static final byte[] toByteArray(final long value) {
    return SafeEncoder.encode(String.valueOf(value));
  }

  public static final byte[] toByteArray(final double value) {
    return SafeEncoder.encode(String.valueOf(value));
  }

  public static enum Command implements ProtocolCommand {
    PING, SET, GET, QUIT, EXISTS, DEL, TYPE, FLUSHDB, KEYS, RANDOMKEY, RENAME, RENAMENX, RENAMEX, DBSIZE, EXPIRE, EXPIREAT, TTL, SELECT, MOVE, FLUSHALL, GETSET, MGET, SETNX, SETEX, MSET, MSETNX, DECRBY, DECR, INCRBY, INCR, APPEND, SUBSTR, HSET, HGET, HSETNX, HMSET, HMGET, HINCRBY, HEXISTS, HDEL, HLEN, HKEYS, HVALS, HGETALL, RPUSH, LPUSH, LLEN, LRANGE, LTRIM, LINDEX, LSET, LREM, LPOP, RPOP, RPOPLPUSH, SADD, SMEMBERS, SREM, SPOP, SMOVE, SCARD, SISMEMBER, SINTER, SINTERSTORE, SUNION, SUNIONSTORE, SDIFF, SDIFFSTORE, SRANDMEMBER, ZADD, ZRANGE, ZREM, ZINCRBY, ZRANK, ZREVRANK, ZREVRANGE, ZCARD, ZSCORE, MULTI, DISCARD, EXEC, WATCH, UNWATCH, SORT, BLPOP, BRPOP, AUTH, SUBSCRIBE, PUBLISH, UNSUBSCRIBE, PSUBSCRIBE, PUNSUBSCRIBE, PUBSUB, ZCOUNT, ZRANGEBYSCORE, ZREVRANGEBYSCORE, ZREMRANGEBYRANK, ZREMRANGEBYSCORE, ZUNIONSTORE, ZINTERSTORE, ZLEXCOUNT, ZRANGEBYLEX, ZREVRANGEBYLEX, ZREMRANGEBYLEX, SAVE, BGSAVE, BGREWRITEAOF, LASTSAVE, SHUTDOWN, INFO, MONITOR, SLAVEOF, CONFIG, STRLEN, SYNC, LPUSHX, PERSIST, RPUSHX, ECHO, LINSERT, DEBUG, BRPOPLPUSH, SETBIT, GETBIT, BITPOS, SETRANGE, GETRANGE, EVAL, EVALSHA, SCRIPT, SLOWLOG, OBJECT, BITCOUNT, BITOP, SENTINEL, DUMP, RESTORE, PEXPIRE, PEXPIREAT, PTTL, INCRBYFLOAT, PSETEX, CLIENT, TIME, MIGRATE, HINCRBYFLOAT, SCAN, HSCAN, SSCAN, ZSCAN, WAIT, CLUSTER, ASKING, PFADD, PFCOUNT, PFMERGE, READONLY;

    private final byte[] raw;

    Command() {
      raw = SafeEncoder.encode(this.name());
    }

    @Override
    public byte[] getRaw() {
      return raw;
    }
  }

  public static enum Keyword {
    AGGREGATE, ALPHA, ASC, BY, DESC, GET, LIMIT, MESSAGE, NO, NOSORT, PMESSAGE, PSUBSCRIBE, PUNSUBSCRIBE, OK, ONE, QUEUED, SET, STORE, SUBSCRIBE, UNSUBSCRIBE, WEIGHTS, WITHSCORES, RESETSTAT, RESET, FLUSH, EXISTS, LOAD, KILL, LEN, REFCOUNT, ENCODING, IDLETIME, AND, OR, XOR, NOT, GETNAME, SETNAME, LIST, MATCH, COUNT;
    public final byte[] raw;

    Keyword() {
      raw = SafeEncoder.encode(this.name().toLowerCase());
    }
  }
}


File: src/main/java/redis/clients/jedis/ShardedJedis.java
package redis.clients.jedis;

import java.io.Closeable;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;
import java.util.regex.Pattern;

import redis.clients.jedis.BinaryClient.LIST_POSITION;
import redis.clients.jedis.params.set.SetParams;
import redis.clients.util.Hashing;

public class ShardedJedis extends BinaryShardedJedis implements JedisCommands, Closeable {

  protected ShardedJedisPool dataSource = null;

  public ShardedJedis(List<JedisShardInfo> shards) {
    super(shards);
  }

  public ShardedJedis(List<JedisShardInfo> shards, Hashing algo) {
    super(shards, algo);
  }

  public ShardedJedis(List<JedisShardInfo> shards, Pattern keyTagPattern) {
    super(shards, keyTagPattern);
  }

  public ShardedJedis(List<JedisShardInfo> shards, Hashing algo, Pattern keyTagPattern) {
    super(shards, algo, keyTagPattern);
  }

  @Override
  public String set(String key, String value) {
    Jedis j = getShard(key);
    return j.set(key, value);
  }

  @Override
  public String set(String key, String value, SetParams params) {
    Jedis j = getShard(key);
    return j.set(key, value, params);
  }

  @Override
  public String get(String key) {
    Jedis j = getShard(key);
    return j.get(key);
  }

  @Override
  public String echo(String string) {
    Jedis j = getShard(string);
    return j.echo(string);
  }

  @Override
  public Boolean exists(String key) {
    Jedis j = getShard(key);
    return j.exists(key);
  }

  @Override
  public String type(String key) {
    Jedis j = getShard(key);
    return j.type(key);
  }

  @Override
  public Long expire(String key, int seconds) {
    Jedis j = getShard(key);
    return j.expire(key, seconds);
  }

  @Override
  public Long pexpire(final String key, final long milliseconds) {
    Jedis j = getShard(key);
    return j.pexpire(key, milliseconds);
  }

  @Override
  public Long expireAt(String key, long unixTime) {
    Jedis j = getShard(key);
    return j.expireAt(key, unixTime);
  }

  @Override
  public Long pexpireAt(String key, long millisecondsTimestamp) {
    Jedis j = getShard(key);
    return j.pexpireAt(key, millisecondsTimestamp);
  }

  @Override
  public Long ttl(String key) {
    Jedis j = getShard(key);
    return j.ttl(key);
  }

  @Override
  public Long pttl(String key) {
    Jedis j = getShard(key);
    return j.pttl(key);
  }

  @Override
  public Boolean setbit(String key, long offset, boolean value) {
    Jedis j = getShard(key);
    return j.setbit(key, offset, value);
  }

  @Override
  public Boolean setbit(String key, long offset, String value) {
    Jedis j = getShard(key);
    return j.setbit(key, offset, value);
  }

  @Override
  public Boolean getbit(String key, long offset) {
    Jedis j = getShard(key);
    return j.getbit(key, offset);
  }

  @Override
  public Long setrange(String key, long offset, String value) {
    Jedis j = getShard(key);
    return j.setrange(key, offset, value);
  }

  @Override
  public String getrange(String key, long startOffset, long endOffset) {
    Jedis j = getShard(key);
    return j.getrange(key, startOffset, endOffset);
  }

  @Override
  public String getSet(String key, String value) {
    Jedis j = getShard(key);
    return j.getSet(key, value);
  }

  @Override
  public Long setnx(String key, String value) {
    Jedis j = getShard(key);
    return j.setnx(key, value);
  }

  @Override
  public String setex(String key, int seconds, String value) {
    Jedis j = getShard(key);
    return j.setex(key, seconds, value);
  }

  @Override
  public String psetex(String key, long milliseconds, String value) {
    Jedis j = getShard(key);
    return j.psetex(key, milliseconds, value);
  }

  public List<String> blpop(String arg) {
    Jedis j = getShard(arg);
    return j.blpop(arg);
  }

  @Override
  public List<String> blpop(int timeout, String key) {
    Jedis j = getShard(key);
    return j.blpop(timeout, key);
  }

  public List<String> brpop(String arg) {
    Jedis j = getShard(arg);
    return j.brpop(arg);
  }

  @Override
  public List<String> brpop(int timeout, String key) {
    Jedis j = getShard(key);
    return j.brpop(timeout, key);
  }

  @Override
  public Long decrBy(String key, long integer) {
    Jedis j = getShard(key);
    return j.decrBy(key, integer);
  }

  @Override
  public Long decr(String key) {
    Jedis j = getShard(key);
    return j.decr(key);
  }

  @Override
  public Long incrBy(String key, long integer) {
    Jedis j = getShard(key);
    return j.incrBy(key, integer);
  }

  @Override
  public Double incrByFloat(String key, double integer) {
    Jedis j = getShard(key);
    return j.incrByFloat(key, integer);
  }

  @Override
  public Long incr(String key) {
    Jedis j = getShard(key);
    return j.incr(key);
  }

  @Override
  public Long append(String key, String value) {
    Jedis j = getShard(key);
    return j.append(key, value);
  }

  @Override
  public String substr(String key, int start, int end) {
    Jedis j = getShard(key);
    return j.substr(key, start, end);
  }

  @Override
  public Long hset(String key, String field, String value) {
    Jedis j = getShard(key);
    return j.hset(key, field, value);
  }

  @Override
  public String hget(String key, String field) {
    Jedis j = getShard(key);
    return j.hget(key, field);
  }

  @Override
  public Long hsetnx(String key, String field, String value) {
    Jedis j = getShard(key);
    return j.hsetnx(key, field, value);
  }

  @Override
  public String hmset(String key, Map<String, String> hash) {
    Jedis j = getShard(key);
    return j.hmset(key, hash);
  }

  @Override
  public List<String> hmget(String key, String... fields) {
    Jedis j = getShard(key);
    return j.hmget(key, fields);
  }

  @Override
  public Long hincrBy(String key, String field, long value) {
    Jedis j = getShard(key);
    return j.hincrBy(key, field, value);
  }

  @Override
  public Double hincrByFloat(String key, String field, double value) {
    Jedis j = getShard(key);
    return j.hincrByFloat(key, field, value);
  }

  @Override
  public Boolean hexists(String key, String field) {
    Jedis j = getShard(key);
    return j.hexists(key, field);
  }

  @Override
  public Long del(String key) {
    Jedis j = getShard(key);
    return j.del(key);
  }

  @Override
  public Long hdel(String key, String... fields) {
    Jedis j = getShard(key);
    return j.hdel(key, fields);
  }

  @Override
  public Long hlen(String key) {
    Jedis j = getShard(key);
    return j.hlen(key);
  }

  @Override
  public Set<String> hkeys(String key) {
    Jedis j = getShard(key);
    return j.hkeys(key);
  }

  @Override
  public List<String> hvals(String key) {
    Jedis j = getShard(key);
    return j.hvals(key);
  }

  @Override
  public Map<String, String> hgetAll(String key) {
    Jedis j = getShard(key);
    return j.hgetAll(key);
  }

  @Override
  public Long rpush(String key, String... strings) {
    Jedis j = getShard(key);
    return j.rpush(key, strings);
  }

  @Override
  public Long lpush(String key, String... strings) {
    Jedis j = getShard(key);
    return j.lpush(key, strings);
  }

  @Override
  public Long lpushx(String key, String... string) {
    Jedis j = getShard(key);
    return j.lpushx(key, string);
  }

  @Override
  public Long strlen(final String key) {
    Jedis j = getShard(key);
    return j.strlen(key);
  }

  @Override
  public Long move(String key, int dbIndex) {
    Jedis j = getShard(key);
    return j.move(key, dbIndex);
  }

  @Override
  public Long rpushx(String key, String... string) {
    Jedis j = getShard(key);
    return j.rpushx(key, string);
  }

  @Override
  public Long persist(final String key) {
    Jedis j = getShard(key);
    return j.persist(key);
  }

  @Override
  public Long llen(String key) {
    Jedis j = getShard(key);
    return j.llen(key);
  }

  @Override
  public List<String> lrange(String key, long start, long end) {
    Jedis j = getShard(key);
    return j.lrange(key, start, end);
  }

  @Override
  public String ltrim(String key, long start, long end) {
    Jedis j = getShard(key);
    return j.ltrim(key, start, end);
  }

  @Override
  public String lindex(String key, long index) {
    Jedis j = getShard(key);
    return j.lindex(key, index);
  }

  @Override
  public String lset(String key, long index, String value) {
    Jedis j = getShard(key);
    return j.lset(key, index, value);
  }

  @Override
  public Long lrem(String key, long count, String value) {
    Jedis j = getShard(key);
    return j.lrem(key, count, value);
  }

  @Override
  public String lpop(String key) {
    Jedis j = getShard(key);
    return j.lpop(key);
  }

  @Override
  public String rpop(String key) {
    Jedis j = getShard(key);
    return j.rpop(key);
  }

  @Override
  public Long sadd(String key, String... members) {
    Jedis j = getShard(key);
    return j.sadd(key, members);
  }

  @Override
  public Set<String> smembers(String key) {
    Jedis j = getShard(key);
    return j.smembers(key);
  }

  @Override
  public Long srem(String key, String... members) {
    Jedis j = getShard(key);
    return j.srem(key, members);
  }

  @Override
  public String spop(String key) {
    Jedis j = getShard(key);
    return j.spop(key);
  }

  @Override
  public Set<String> spop(String key, long count) {
    Jedis j = getShard(key);
    return j.spop(key, count);
  }

  @Override
  public Long scard(String key) {
    Jedis j = getShard(key);
    return j.scard(key);
  }

  @Override
  public Boolean sismember(String key, String member) {
    Jedis j = getShard(key);
    return j.sismember(key, member);
  }

  @Override
  public String srandmember(String key) {
    Jedis j = getShard(key);
    return j.srandmember(key);
  }

  @Override
  public List<String> srandmember(String key, int count) {
    Jedis j = getShard(key);
    return j.srandmember(key, count);
  }

  @Override
  public Long zadd(String key, double score, String member) {
    Jedis j = getShard(key);
    return j.zadd(key, score, member);
  }

  @Override
  public Long zadd(String key, Map<String, Double> scoreMembers) {
    Jedis j = getShard(key);
    return j.zadd(key, scoreMembers);
  }

  @Override
  public Set<String> zrange(String key, long start, long end) {
    Jedis j = getShard(key);
    return j.zrange(key, start, end);
  }

  @Override
  public Long zrem(String key, String... members) {
    Jedis j = getShard(key);
    return j.zrem(key, members);
  }

  @Override
  public Double zincrby(String key, double score, String member) {
    Jedis j = getShard(key);
    return j.zincrby(key, score, member);
  }

  @Override
  public Long zrank(String key, String member) {
    Jedis j = getShard(key);
    return j.zrank(key, member);
  }

  @Override
  public Long zrevrank(String key, String member) {
    Jedis j = getShard(key);
    return j.zrevrank(key, member);
  }

  @Override
  public Set<String> zrevrange(String key, long start, long end) {
    Jedis j = getShard(key);
    return j.zrevrange(key, start, end);
  }

  @Override
  public Set<Tuple> zrangeWithScores(String key, long start, long end) {
    Jedis j = getShard(key);
    return j.zrangeWithScores(key, start, end);
  }

  @Override
  public Set<Tuple> zrevrangeWithScores(String key, long start, long end) {
    Jedis j = getShard(key);
    return j.zrevrangeWithScores(key, start, end);
  }

  @Override
  public Long zcard(String key) {
    Jedis j = getShard(key);
    return j.zcard(key);
  }

  @Override
  public Double zscore(String key, String member) {
    Jedis j = getShard(key);
    return j.zscore(key, member);
  }

  @Override
  public List<String> sort(String key) {
    Jedis j = getShard(key);
    return j.sort(key);
  }

  @Override
  public List<String> sort(String key, SortingParams sortingParameters) {
    Jedis j = getShard(key);
    return j.sort(key, sortingParameters);
  }

  @Override
  public Long zcount(String key, double min, double max) {
    Jedis j = getShard(key);
    return j.zcount(key, min, max);
  }

  @Override
  public Long zcount(String key, String min, String max) {
    Jedis j = getShard(key);
    return j.zcount(key, min, max);
  }

  @Override
  public Set<String> zrangeByScore(String key, double min, double max) {
    Jedis j = getShard(key);
    return j.zrangeByScore(key, min, max);
  }

  @Override
  public Set<String> zrevrangeByScore(String key, double max, double min) {
    Jedis j = getShard(key);
    return j.zrevrangeByScore(key, max, min);
  }

  @Override
  public Set<String> zrangeByScore(String key, double min, double max, int offset, int count) {
    Jedis j = getShard(key);
    return j.zrangeByScore(key, min, max, offset, count);
  }

  @Override
  public Set<String> zrevrangeByScore(String key, double max, double min, int offset, int count) {
    Jedis j = getShard(key);
    return j.zrevrangeByScore(key, max, min, offset, count);
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(String key, double min, double max) {
    Jedis j = getShard(key);
    return j.zrangeByScoreWithScores(key, min, max);
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(String key, double max, double min) {
    Jedis j = getShard(key);
    return j.zrevrangeByScoreWithScores(key, max, min);
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(String key, double min, double max, int offset,
      int count) {
    Jedis j = getShard(key);
    return j.zrangeByScoreWithScores(key, min, max, offset, count);
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(String key, double max, double min, int offset,
      int count) {
    Jedis j = getShard(key);
    return j.zrevrangeByScoreWithScores(key, max, min, offset, count);
  }

  @Override
  public Set<String> zrangeByScore(String key, String min, String max) {
    Jedis j = getShard(key);
    return j.zrangeByScore(key, min, max);
  }

  @Override
  public Set<String> zrevrangeByScore(String key, String max, String min) {
    Jedis j = getShard(key);
    return j.zrevrangeByScore(key, max, min);
  }

  @Override
  public Set<String> zrangeByScore(String key, String min, String max, int offset, int count) {
    Jedis j = getShard(key);
    return j.zrangeByScore(key, min, max, offset, count);
  }

  @Override
  public Set<String> zrevrangeByScore(String key, String max, String min, int offset, int count) {
    Jedis j = getShard(key);
    return j.zrevrangeByScore(key, max, min, offset, count);
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(String key, String min, String max) {
    Jedis j = getShard(key);
    return j.zrangeByScoreWithScores(key, min, max);
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(String key, String max, String min) {
    Jedis j = getShard(key);
    return j.zrevrangeByScoreWithScores(key, max, min);
  }

  @Override
  public Set<Tuple> zrangeByScoreWithScores(String key, String min, String max, int offset,
      int count) {
    Jedis j = getShard(key);
    return j.zrangeByScoreWithScores(key, min, max, offset, count);
  }

  @Override
  public Set<Tuple> zrevrangeByScoreWithScores(String key, String max, String min, int offset,
      int count) {
    Jedis j = getShard(key);
    return j.zrevrangeByScoreWithScores(key, max, min, offset, count);
  }

  @Override
  public Long zremrangeByRank(String key, long start, long end) {
    Jedis j = getShard(key);
    return j.zremrangeByRank(key, start, end);
  }

  @Override
  public Long zremrangeByScore(String key, double start, double end) {
    Jedis j = getShard(key);
    return j.zremrangeByScore(key, start, end);
  }

  @Override
  public Long zremrangeByScore(String key, String start, String end) {
    Jedis j = getShard(key);
    return j.zremrangeByScore(key, start, end);
  }

  @Override
  public Long zlexcount(final String key, final String min, final String max) {
    return getShard(key).zlexcount(key, min, max);
  }

  @Override
  public Set<String> zrangeByLex(final String key, final String min, final String max) {
    return getShard(key).zrangeByLex(key, min, max);
  }

  @Override
  public Set<String> zrangeByLex(final String key, final String min, final String max,
      final int offset, final int count) {
    return getShard(key).zrangeByLex(key, min, max, offset, count);
  }

  @Override
  public Set<String> zrevrangeByLex(String key, String max, String min) {
    return getShard(key).zrevrangeByLex(key, max, min);
  }

  @Override
  public Set<String> zrevrangeByLex(String key, String max, String min, int offset, int count) {
    return getShard(key).zrevrangeByLex(key, max, min, offset, count);
  }

  @Override
  public Long zremrangeByLex(final String key, final String min, final String max) {
    return getShard(key).zremrangeByLex(key, min, max);
  }

  @Override
  public Long linsert(String key, LIST_POSITION where, String pivot, String value) {
    Jedis j = getShard(key);
    return j.linsert(key, where, pivot, value);
  }

  @Override
  public Long bitcount(final String key) {
    Jedis j = getShard(key);
    return j.bitcount(key);
  }

  @Override
  public Long bitcount(final String key, long start, long end) {
    Jedis j = getShard(key);
    return j.bitcount(key, start, end);
  }

  @Override
  public Long bitpos(String key, boolean value) {
    Jedis j = getShard(key);
    return j.bitpos(key, value);
  }

  @Override
  public Long bitpos(String key, boolean value, BitPosParams params) {
    Jedis j = getShard(key);
    return j.bitpos(key, value, params);
  }

  @Override
  public ScanResult<Entry<String, String>> hscan(String key, final String cursor) {
    Jedis j = getShard(key);
    return j.hscan(key, cursor);
  }

  @Override
  public ScanResult<Entry<String, String>> hscan(String key, String cursor, ScanParams params) {
    Jedis j = getShard(key);
    return j.hscan(key, cursor, params);
  }

  @Override
  public ScanResult<String> sscan(String key, final String cursor) {
    Jedis j = getShard(key);
    return j.sscan(key, cursor);
  }

  @Override
  public ScanResult<Tuple> zscan(String key, final String cursor) {
    Jedis j = getShard(key);
    return j.zscan(key, cursor);
  }

  @Override
  public ScanResult<Tuple> zscan(String key, String cursor, ScanParams params) {
    Jedis j = getShard(key);
    return j.zscan(key, cursor, params);
  }

  @Override
  public ScanResult<String> sscan(String key, String cursor, ScanParams params) {
    Jedis j = getShard(key);
    return j.sscan(key, cursor, params);
  }

  @Override
  public void close() {
    if (dataSource != null) {
      boolean broken = false;

      for (Jedis jedis : getAllShards()) {
        if (jedis.getClient().isBroken()) {
          broken = true;
          break;
        }
      }

      if (broken) {
        dataSource.returnBrokenResource(this);
      } else {
        dataSource.returnResource(this);
      }

    } else {
      disconnect();
    }
  }

  public void setDataSource(ShardedJedisPool shardedJedisPool) {
    this.dataSource = shardedJedisPool;
  }

  public void resetState() {
    for (Jedis jedis : getAllShards()) {
      jedis.resetState();
    }
  }

  @Override
  public Long pfadd(String key, String... elements) {
    Jedis j = getShard(key);
    return j.pfadd(key, elements);
  }

  @Override
  public long pfcount(String key) {
    Jedis j = getShard(key);
    return j.pfcount(key);
  }

}


File: src/test/java/redis/clients/jedis/tests/ConnectionTest.java
package redis.clients.jedis.tests;

import org.junit.After;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;

import redis.clients.jedis.Connection;
import redis.clients.jedis.Protocol.Command;
import redis.clients.jedis.ProtocolCommand;
import redis.clients.jedis.exceptions.JedisConnectionException;

public class ConnectionTest extends Assert {
  private Connection client;

  @Before
  public void setUp() throws Exception {
    client = new Connection();
  }

  @After
  public void tearDown() throws Exception {
    client.disconnect();
  }

  @Test(expected = JedisConnectionException.class)
  public void checkUnkownHost() {
    client.setHost("someunknownhost");
    client.connect();
  }

  @Test(expected = JedisConnectionException.class)
  public void checkWrongPort() {
    client.setHost("localhost");
    client.setPort(55665);
    client.connect();
  }

  @Test
  public void connectIfNotConnectedWhenSettingTimeoutInfinite() {
    client.setHost("localhost");
    client.setPort(6379);
    client.setTimeoutInfinite();
  }

  @Test
  public void checkCloseable() {
    client.setHost("localhost");
    client.setPort(6379);
    client.connect();
    client.close();
  }

  @Test
  public void getErrorAfterConnectionReset() throws Exception {
    class TestConnection extends Connection {
      public TestConnection() {
        super("localhost", 6379);
      }

      @Override
      protected Connection sendCommand(ProtocolCommand cmd, byte[]... args) {
        return super.sendCommand(cmd, args);
      }
    }

    TestConnection conn = new TestConnection();

    try {
      conn.sendCommand(Command.HMSET, new byte[1024 * 1024 + 1][0]);
      fail("Should throw exception");
    } catch (JedisConnectionException jce) {
      assertEquals("ERR Protocol error: invalid multibulk length", jce.getMessage());
    }
  }
}
