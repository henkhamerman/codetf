Refactoring Types: ['Move Attribute']
e/drill/common/exceptions/UserException.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.common.exceptions;

import org.apache.drill.exec.proto.CoordinationProtos;
import org.apache.drill.exec.proto.CoordinationProtos.DrillbitEndpoint;
import org.apache.drill.exec.proto.UserBitShared.DrillPBError;

/**
 * Base class for all user exception. The goal is to separate out common error conditions where we can give users
 * useful feedback.
 * <p>Throwing a user exception will guarantee it's message will be displayed to the user, along with any context
 * information added to the exception at various levels while being sent to the client.
 * <p>A specific class of user exceptions are system exception. They represent system level errors that don't display
 * any specific error message to the user apart from "A system error has occurend" along with informations to retrieve
 * the details of the exception from the logs.
 * <p>Although system exception should only display a generic message to the user, for now they will display the root
 * error message, until all user errors are properly sent from the server side.
 * <p>Any thrown exception that is not wrapped inside a user exception will automatically be converted to a system
 * exception before being sent to the client.
 *
 * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType
 */
public class UserException extends DrillRuntimeException {
  private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(UserException.class);

  public static final String MEMORY_ERROR_MSG = "One or more nodes ran out of memory while executing the query.";

  /**
   * Creates a RESOURCE error with a prebuilt message for out of memory exceptions
   *
   * @param cause exception that will be wrapped inside a memory error
   * @return resource error builder
   */
  public static Builder memoryError(final Throwable cause) {
    return UserException.resourceError(cause)
      .message(MEMORY_ERROR_MSG);
  }

  /**
   * Creates a RESOURCE error with a prebuilt message for out of memory exceptions
   *
   * @return resource error builder
   */
  public static Builder memoryError() {
    return memoryError(null);
  }

  /**
   * Wraps the passed exception inside a system error.
   * <p>The cause message will be used unless {@link Builder#message(String, Object...)} is called.
   * <p>If the wrapped exception is, or wraps, a user exception it will be returned by {@link Builder#build()} instead
   * of creating a new exception. Any added context will be added to the user exception as well.
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#SYSTEM
   *
   * @param cause exception we want the user exception to wrap. If cause is, or wrap, a user exception it will be
   *              returned by the builder instead of creating a new user exception
   * @return user exception builder
   *
   * @deprecated This method should never need to be used explicitly, unless you are passing the exception to the
   *             Rpc layer or UserResultListener.submitFailed()
   */
  @Deprecated
  public static Builder systemError(final Throwable cause) {
    return new Builder(DrillPBError.ErrorType.SYSTEM, cause);
  }

  /**
   * Creates a new user exception builder.
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#CONNECTION
   * @return user exception builder
   */
  public static Builder connectionError() {
    return connectionError(null);
  }

  /**
   * Wraps the passed exception inside a connection error.
   * <p>The cause message will be used unless {@link Builder#message(String, Object...)} is called.
   * <p>If the wrapped exception is, or wraps, a user exception it will be returned by {@link Builder#build()} instead
   * of creating a new exception. Any added context will be added to the user exception as well.
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#CONNECTION
   *
   * @param cause exception we want the user exception to wrap. If cause is, or wrap, a user exception it will be
   *              returned by the builder instead of creating a new user exception
   * @return user exception builder
   */
  public static Builder connectionError(final Throwable cause) {
    return new Builder(DrillPBError.ErrorType.CONNECTION, cause);
  }

  /**
   * Creates a new user exception builder.
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#DATA_READ
   * @return user exception builder
   */
  public static Builder dataReadError() {
    return dataReadError(null);
  }

  /**
   * Wraps the passed exception inside a data read error.
   * <p>The cause message will be used unless {@link Builder#message(String, Object...)} is called.
   * <p>If the wrapped exception is, or wraps, a user exception it will be returned by {@link Builder#build()} instead
   * of creating a new exception. Any added context will be added to the user exception as well.
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#DATA_READ
   *
   * @param cause exception we want the user exception to wrap. If cause is, or wrap, a user exception it will be
   *              returned by the builder instead of creating a new user exception
   * @return user exception builder
   */
  public static Builder dataReadError(final Throwable cause) {
    return new Builder(DrillPBError.ErrorType.DATA_READ, cause);
  }

  /**
   * Creates a new user exception builder .
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#DATA_WRITE
   * @return user exception builder
   */
  public static Builder dataWriteError() {
    return dataWriteError(null);
  }

  /**
   * Wraps the passed exception inside a data write error.
   * <p>The cause message will be used unless {@link Builder#message(String, Object...)} is called.
   * <p>If the wrapped exception is, or wraps, a user exception it will be returned by {@link Builder#build()} instead
   * of creating a new exception. Any added context will be added to the user exception as well.
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#DATA_WRITE
   *
   * @param cause exception we want the user exception to wrap. If cause is, or wrap, a user exception it will be
   *              returned by the builder instead of creating a new user exception
   * @return user exception builder
   */
  public static Builder dataWriteError(final Throwable cause) {
    return new Builder(DrillPBError.ErrorType.DATA_WRITE, cause);
  }

  /**
   * Creates a new user exception builder .
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#FUNCTION
   * @return user exception builder
   */
  public static Builder functionError() {
    return functionError(null);
  }

  /**
   * Wraps the passed exception inside a function error.
   * <p>The cause message will be used unless {@link Builder#message(String, Object...)} is called.
   * <p>If the wrapped exception is, or wraps, a user exception it will be returned by {@link Builder#build()} instead
   * of creating a new exception. Any added context will be added to the user exception as well.
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#FUNCTION
   *
   * @param cause exception we want the user exception to wrap. If cause is, or wrap, a user exception it will be
   *              returned by the builder instead of creating a new user exception
   * @return user exception builder
   */
  public static Builder functionError(final Throwable cause) {
    return new Builder(DrillPBError.ErrorType.FUNCTION, cause);
  }

  /**
   * Creates a new user exception builder .
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#PARSE
   * @return user exception builder
   */
  public static Builder parseError() {
    return parseError(null);
  }

  /**
   * Wraps the passed exception inside a system error.
   * <p>The cause message will be used unless {@link Builder#message(String, Object...)} is called.
   * <p>If the wrapped exception is, or wraps, a user exception it will be returned by {@link Builder#build()} instead
   * of creating a new exception. Any added context will be added to the user exception as well.
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#PARSE
   *
   * @param cause exception we want the user exception to wrap. If cause is, or wrap, a user exception it will be
   *              returned by the builder instead of creating a new user exception
   * @return user exception builder
   */
  public static Builder parseError(final Throwable cause) {
    return new Builder(DrillPBError.ErrorType.PARSE, cause);
  }

  /**
   * Creates a new user exception builder .
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#VALIDATION
   * @return user exception builder
   */
  public static Builder validationError() {
    return validationError(null);
  }

  /**
   * wraps the passed exception inside a system error.
   * <p>the cause message will be used unless {@link Builder#message(String, Object...)} is called.
   * <p>if the wrapped exception is, or wraps, a user exception it will be returned by {@link Builder#build()} instead
   * of creating a new exception. Any added context will be added to the user exception as well.
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#VALIDATION
   *
   * @param cause exception we want the user exception to wrap. If cause is, or wrap, a user exception it will be
   *              returned by the builder instead of creating a new user exception
   * @return user exception builder
   */
  public static Builder validationError(Throwable cause) {
    return new Builder(DrillPBError.ErrorType.VALIDATION, cause);
  }

  /**
   * creates a new user exception builder .
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#PERMISSION
   * @return user exception builder
   */
  public static Builder permissionError() {
    return permissionError(null);
  }

  /**
   * Wraps the passed exception inside a system error.
   * <p>The cause message will be used unless {@link Builder#message(String, Object...)} is called.
   * <p>If the wrapped exception is, or wraps, a user exception it will be returned by {@link Builder#build()} instead
   * of creating a new exception. Any added context will be added to the user exception as well.
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#PERMISSION
   *
   * @param cause exception we want the user exception to wrap. If cause is, or wrap, a user exception it will be
   *              returned by the builder instead of creating a new user exception
   * @return user exception builder
   */
  public static Builder permissionError(final Throwable cause) {
    return new Builder(DrillPBError.ErrorType.PERMISSION, cause);
  }

  /**
   * Creates a new user exception builder .
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#PLAN
   * @return user exception builder
   */
  public static Builder planError() {
    return planError(null);
  }

  /**
   * Wraps the passed exception inside a system error.
   * <p>The cause message will be used unless {@link Builder#message(String, Object...)} is called.
   * <p>If the wrapped exception is, or wraps, a user exception it will be returned by {@link Builder#build()} instead
   * of creating a new exception. Any added context will be added to the user exception as well.
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#PLAN
   *
   * @param cause exception we want the user exception to wrap. If cause is, or wrap, a user exception it will be
   *              returned by the builder instead of creating a new user exception
   * @return user exception builder
   */
  public static Builder planError(final Throwable cause) {
    return new Builder(DrillPBError.ErrorType.PLAN, cause);
  }

  /**
   * Creates a new user exception builder .
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#RESOURCE
   * @return user exception builder
   */
  public static Builder resourceError() {
    return resourceError(null);
  }

  /**
   * Wraps the passed exception inside a system error.
   * <p>The cause message will be used unless {@link Builder#message(String, Object...)} is called.
   * <p>If the wrapped exception is, or wraps, a user exception it will be returned by {@link Builder#build()} instead
   * of creating a new exception. Any added context will be added to the user exception as well.
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#RESOURCE
   *
   * @param cause exception we want the user exception to wrap. If cause is, or wrap, a user exception it will be
   *              returned by the builder instead of creating a new user exception
   * @return user exception builder
   */
  public static Builder resourceError(final Throwable cause) {
    return new Builder(DrillPBError.ErrorType.RESOURCE, cause);
  }

  /**
   * Creates a new user exception builder .
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#UNSUPPORTED_OPERATION
   * @return user exception builder
   */
  public static Builder unsupportedError() {
    return unsupportedError(null);
  }

  /**
   * Wraps the passed exception inside a system error.
   * <p>The cause message will be used unless {@link Builder#message(String, Object...)} is called.
   * <p>If the wrapped exception is, or wraps, a user exception it will be returned by {@link Builder#build()} instead
   * of creating a new exception. Any added context will be added to the user exception as well.
   *
   * @see org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType#UNSUPPORTED_OPERATION
   *
   * @param cause exception we want the user exception to wrap. If cause is, or wrap, a user exception it will be
   *              returned by the builder instead of creating a new user exception
   * @return user exception builder
   */
  public static Builder unsupportedError(final Throwable cause) {
    return new Builder(DrillPBError.ErrorType.UNSUPPORTED_OPERATION, cause);
  }

  /**
   * Builder class for DrillUserException. You can wrap an existing exception, in this case it will first check if
   * this exception is, or wraps, a DrillUserException. If it does then the builder will use the user exception as it is
   * (it will ignore the message passed to the constructor) and will add any additional context information to the
   * exception's context
   */
  public static class Builder {

    private final Throwable cause;
    private final DrillPBError.ErrorType errorType;
    private final UserException uex;
    private final UserExceptionContext context;

    private String message;

    /**
     * Wraps an existing exception inside a user exception.
     *
     * @param errorType user exception type that should be created if the passed exception isn't,
     *                  or doesn't wrap a user exception
     * @param cause exception to wrap inside a user exception. Can be null
     */
    private Builder(final DrillPBError.ErrorType errorType, final Throwable cause) {
      this.cause = cause;

      //TODO handle the improbable case where cause is a SYSTEM exception ?
      uex = ErrorHelper.findWrappedUserException(cause);
      if (uex != null) {
        this.errorType = null;
        this.context = uex.context;
      } else {
        // we will create a new user exception
        this.errorType = errorType;
        this.context = new UserExceptionContext();
        this.message = cause != null ? cause.getMessage() : null;
      }
    }

    /**
     * sets or replaces the error message.
     * <p>This will be ignored if this builder is wrapping a user exception
     *
     * @see String#format(String, Object...)
     *
     * @param format format string
     * @param args Arguments referenced by the format specifiers in the format string
     * @return this builder
     */
    public Builder message(final String format, final Object... args) {
      // we can't replace the message of a user exception
      if (uex == null && format != null) {
        this.message = String.format(format, args);
      }
      return this;
    }

    /**
     * add DrillbitEndpoint identity to the context.
     * <p>if the context already has a drillbitEndpoint identity, the new identity will be ignored
     *
     * @param endpoint drillbit endpoint identity
     */
    public Builder addIdentity(final CoordinationProtos.DrillbitEndpoint endpoint) {
      context.add(endpoint);
      return this;
    }

    /**
     * add a string line to the bottom of the context
     * @param value string line
     * @return this builder
     */
    public Builder addContext(final String value) {
      context.add(value);
      return this;
    }

    /**
     * add a string value to the bottom of the context
     *
     * @param name context name
     * @param value context value
     * @return this builder
     */
    public Builder addContext(final String name, final String value) {
      context.add(name, value);
      return this;
    }

    /**
     * add a long value to the bottom of the context
     *
     * @param name context name
     * @param value context value
     * @return this builder
     */
    public Builder addContext(final String name, final long value) {
      context.add(name, value);
      return this;
    }

    /**
     * add a double value to the bottom of the context
     *
     * @param name context name
     * @param value context value
     * @return this builder
     */
    public Builder addContext(final String name, final double value) {
      context.add(name, value);
      return this;
    }

    /**
     * pushes a string value to the top of the context
     *
     * @param value context value
     * @return this builder
     */
    public Builder pushContext(final String value) {
      context.push(value);
      return this;
    }

    /**
     * pushes a string value to the top of the context
     *
     * @param name context name
     * @param value context value
     * @return this builder
     */
    public Builder pushContext(final String name, final String value) {
      context.push(name, value);
      return this;
    }

    /**
     * pushes a long value to the top of the context
     *
     * @param name context name
     * @param value context value
     * @return this builder
     */
    public Builder pushContext(final String name, final long value) {
      context.push(name, value);
      return this;
    }

    /**
     * pushes a double value to the top of the context
     *
     * @param name context name
     * @param value context value
     * @return this builder
     */
    public Builder pushContext(final String name, final double value) {
      context.push(name, value);
      return this;
    }

    /**
     * builds a user exception or returns the wrapped one.
     *
     * @return user exception
     */
    public UserException build() {

      if (uex != null) {
        return uex;
      }

      boolean isSystemError = errorType == DrillPBError.ErrorType.SYSTEM;

      // make sure system errors use the root error message and display the root cause class name
      if (isSystemError) {
        message = ErrorHelper.getRootMessage(cause);
      }

      final UserException newException = new UserException(this);

      // since we just created a new exception, we should log it for later reference. If this is a system error, this is
      // an issue that the Drill admin should pay attention to and we should log as ERROR. However, if this is a user
      // mistake or data read issue, the system admin should not be concerned about these and thus we'll log this
      // as an INFO message.
      if (isSystemError) {
        logger.error(newException.getMessage(), newException);
      } else {
        logger.info("User Error Occurred", newException);
      }

      return newException;
    }
  }

  private final DrillPBError.ErrorType errorType;

  private final UserExceptionContext context;

  protected UserException(final DrillPBError.ErrorType errorType, final String message, final Throwable cause) {
    super(message, cause);

    this.errorType = errorType;
    this.context = new UserExceptionContext();
  }

  private UserException(final Builder builder) {
    super(builder.message, builder.cause);
    this.errorType = builder.errorType;
    this.context = builder.context;
  }

  /**
   * generates the message that will be displayed to the client without the stack trace.
   *
   * @return non verbose error message
   */
  @Override
  public String getMessage() {
    return generateMessage(true);
  }

  public String getMessage(boolean includeErrorIdAndIdentity) {
    return generateMessage(includeErrorIdAndIdentity);
  }

  /**
   *
   * @return the error message that was passed to the builder
   */
  public String getOriginalMessage() {
    return super.getMessage();
  }

  /**
   * generates the message that will be displayed to the client. The message also contains the stack trace.
   *
   * @return verbose error message
   */
  public String getVerboseMessage() {
    return getVerboseMessage(true);
  }

  public String getVerboseMessage(boolean includeErrorIdAndIdentity) {
    return generateMessage(includeErrorIdAndIdentity) + "\n\n" + ErrorHelper.buildCausesMessage(getCause());
  }

  /**
   * returns or creates a DrillPBError object corresponding to this user exception.
   *
   * @param verbose should the error object contain the verbose error message ?
   * @return protobuf error object
   */
  public DrillPBError getOrCreatePBError(final boolean verbose) {
    final String message = verbose ? getVerboseMessage() : getMessage();

    final DrillPBError.Builder builder = DrillPBError.newBuilder();
    builder.setErrorType(errorType);
    builder.setErrorId(context.getErrorId());
    if (context.getEndpoint() != null) {
      builder.setEndpoint(context.getEndpoint());
    }
    builder.setMessage(message);

    if (getCause() != null) {
      // some unit tests use this information to make sure a specific exception was thrown in the server
      builder.setException(ErrorHelper.getWrapper(getCause()));
    }
    return builder.build();
  }

  public String getErrorId() {
    return context.getErrorId();
  }

  public String getErrorLocation() {
    DrillbitEndpoint ep = context.getEndpoint();
    if (ep != null) {
      return ep.getAddress() + ":" + ep.getUserPort();
    } else {
      return null;
    }
  }
  /**
   * Generates a user error message that has the following structure:
   * ERROR TYPE: ERROR_MESSAGE
   * CONTEXT
   * [ERROR_ID on DRILLBIT_IP:DRILLBIT_USER_PORT]
   *
   * @return generated user error message
   */
  private String generateMessage(boolean includeErrorIdAndIdentity) {
    return errorType + " ERROR: " + super.getMessage() + "\n\n" +
        context.generateContextMessage(includeErrorIdAndIdentity);
  }

}


File: common/src/test/java/org/apache/drill/common/exceptions/TestUserException.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.common.exceptions;

import org.apache.drill.exec.proto.UserBitShared.DrillPBError;
import org.apache.drill.exec.proto.UserBitShared.DrillPBError.ErrorType;
import org.junit.Assert;
import org.junit.Test;

/**
 * Test various use cases when creating user exceptions
 */
public class TestUserException {

  private Exception wrap(UserException uex, int numWraps) {
    Exception ex = uex;
    for (int i = 0; i < numWraps; i++) {
      ex = new Exception("wrap #" + (i+1), ex);
    }

    return ex;
  }

  // make sure system exceptions are created properly
  @Test
  public void testBuildSystemException() {
    String message = "This is an exception";
    UserException uex = UserException.systemError(new Exception(new RuntimeException(message))).build();

    Assert.assertTrue(uex.getOriginalMessage().contains(message));
    Assert.assertTrue(uex.getOriginalMessage().contains("RuntimeException"));

    DrillPBError error = uex.getOrCreatePBError(true);

    Assert.assertEquals(ErrorType.SYSTEM, error.getErrorType());
  }

  @Test
  public void testBuildUserExceptionWithMessage() {
    String message = "Test message";

    UserException uex = UserException.dataWriteError().message(message).build();
    DrillPBError error = uex.getOrCreatePBError(false);

    Assert.assertEquals(ErrorType.DATA_WRITE, error.getErrorType());
    Assert.assertEquals(message, uex.getOriginalMessage());
  }

  @Test
  public void testBuildUserExceptionWithCause() {
    String message = "Test message";

    UserException uex = UserException.dataWriteError(new RuntimeException(message)).build();
    DrillPBError error = uex.getOrCreatePBError(false);

    // cause message should be used
    Assert.assertEquals(ErrorType.DATA_WRITE, error.getErrorType());
    Assert.assertEquals(message, uex.getOriginalMessage());
  }

  @Test
  public void testBuildUserExceptionWithCauseAndMessage() {
    String messageA = "Test message A";
    String messageB = "Test message B";

    UserException uex = UserException.dataWriteError(new RuntimeException(messageA)).message(messageB).build();
    DrillPBError error = uex.getOrCreatePBError(false);

    // passed message should override the cause message
    Assert.assertEquals(ErrorType.DATA_WRITE, error.getErrorType());
    Assert.assertFalse(error.getMessage().contains(messageA)); // messageA should not be part of the context
    Assert.assertEquals(messageB, uex.getOriginalMessage());
  }

  @Test
  public void testBuildUserExceptionWithUserExceptionCauseAndMessage() {
    String messageA = "Test message A";
    String messageB = "Test message B";

    UserException original = UserException.connectionError().message(messageA).build();
    UserException uex = UserException.dataWriteError(wrap(original, 5)).message(messageB).build();

    //builder should return the unwrapped original user exception and not build a new one
    Assert.assertEquals(original, uex);

    DrillPBError error = uex.getOrCreatePBError(false);
    Assert.assertEquals(messageA, uex.getOriginalMessage());
    Assert.assertFalse(error.getMessage().contains(messageB)); // messageB should not be part of the context
  }

  @Test
  public void testBuildUserExceptionWithFormattedMessage() {
    String format = "This is test #%d";

    UserException uex = UserException.connectionError().message(format, 5).build();
    DrillPBError error = uex.getOrCreatePBError(false);

    Assert.assertEquals(ErrorType.CONNECTION, error.getErrorType());
    Assert.assertEquals(String.format(format, 5), uex.getOriginalMessage());
  }

  // make sure wrapped user exceptions are retrieved properly when calling ErrorHelper.wrap()
  @Test
  public void testWrapUserException() {
    UserException uex = UserException.dataReadError().message("this is a data read exception").build();

    Exception wrapped = wrap(uex, 3);
    Assert.assertEquals(uex, UserException.systemError(wrapped).build());
  }

}


File: contrib/storage-hive/core/src/main/java/org/apache/drill/exec/store/hive/HiveRecordReader.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.store.hive;

import java.io.IOException;
import java.math.BigDecimal;
import java.sql.Date;
import java.sql.Timestamp;
import java.util.List;
import java.util.Map;
import java.util.Properties;

import org.apache.drill.common.exceptions.DrillRuntimeException;
import org.apache.drill.common.exceptions.ExecutionSetupException;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.common.expression.SchemaPath;
import org.apache.drill.common.types.TypeProtos;
import org.apache.drill.common.types.TypeProtos.DataMode;
import org.apache.drill.common.types.TypeProtos.MinorType;
import org.apache.drill.common.types.TypeProtos.MajorType;
import org.apache.drill.exec.exception.SchemaChangeException;
import org.apache.drill.exec.expr.TypeHelper;
import org.apache.drill.exec.expr.holders.Decimal18Holder;
import org.apache.drill.exec.expr.holders.Decimal28SparseHolder;
import org.apache.drill.exec.expr.holders.Decimal38SparseHolder;
import org.apache.drill.exec.expr.holders.Decimal9Holder;
import org.apache.drill.exec.ops.FragmentContext;
import org.apache.drill.exec.ops.OperatorContext;
import org.apache.drill.exec.physical.impl.OutputMutator;
import org.apache.drill.exec.planner.physical.PlannerSettings;
import org.apache.drill.exec.record.MaterializedField;
import org.apache.drill.exec.rpc.ProtobufLengthDecoder;
import org.apache.drill.exec.store.AbstractRecordReader;
import org.apache.drill.exec.util.DecimalUtility;
import org.apache.drill.exec.vector.AllocationHelper;
import org.apache.drill.exec.vector.BigIntVector;
import org.apache.drill.exec.vector.BitVector;
import org.apache.drill.exec.vector.DateVector;
import org.apache.drill.exec.vector.Decimal18Vector;
import org.apache.drill.exec.vector.Decimal28SparseVector;
import org.apache.drill.exec.vector.Decimal38SparseVector;
import org.apache.drill.exec.vector.Decimal9Vector;
import org.apache.drill.exec.vector.Float4Vector;
import org.apache.drill.exec.vector.Float8Vector;
import org.apache.drill.exec.vector.IntVector;
import org.apache.drill.exec.vector.SmallIntVector;
import org.apache.drill.exec.vector.TimeStampVector;
import org.apache.drill.exec.vector.TinyIntVector;
import org.apache.drill.exec.vector.ValueVector;
import org.apache.drill.exec.vector.VarBinaryVector;
import org.apache.drill.exec.vector.VarCharVector;
import org.apache.drill.exec.work.ExecErrorConstants;
import org.apache.hadoop.hive.common.type.HiveDecimal;
import org.apache.hadoop.hive.metastore.MetaStoreUtils;
import org.apache.hadoop.hive.metastore.api.FieldSchema;
import org.apache.hadoop.hive.metastore.api.Partition;
import org.apache.hadoop.hive.metastore.api.Table;
import org.apache.hadoop.hive.serde2.ColumnProjectionUtils;
import org.apache.hadoop.hive.serde2.SerDe;
import org.apache.hadoop.hive.serde2.SerDeException;
import org.apache.hadoop.hive.serde2.objectinspector.ObjectInspector;
import org.apache.hadoop.hive.serde2.objectinspector.ObjectInspector.Category;
import org.apache.hadoop.hive.serde2.objectinspector.PrimitiveObjectInspector.PrimitiveCategory;
import org.apache.hadoop.hive.serde2.objectinspector.StructObjectInspector;
import org.apache.hadoop.hive.serde2.typeinfo.DecimalTypeInfo;
import org.apache.hadoop.hive.serde2.typeinfo.HiveDecimalUtils;
import org.apache.hadoop.hive.serde2.typeinfo.PrimitiveTypeInfo;
import org.apache.hadoop.hive.serde2.typeinfo.StructTypeInfo;
import org.apache.hadoop.hive.serde2.typeinfo.TypeInfo;
import org.apache.hadoop.hive.serde2.typeinfo.TypeInfoUtils;
import org.apache.hadoop.io.Writable;
import org.apache.hadoop.mapred.InputFormat;
import org.apache.hadoop.mapred.InputSplit;
import org.apache.hadoop.mapred.JobConf;
import org.apache.hadoop.mapred.Reporter;
import org.joda.time.DateTime;
import org.joda.time.DateTimeZone;

import com.google.common.collect.Lists;

public class HiveRecordReader extends AbstractRecordReader {

  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(HiveRecordReader.class);

  protected Table table;
  protected Partition partition;
  protected InputSplit inputSplit;
  protected FragmentContext context;
  protected List<String> selectedColumnNames;
  protected List<TypeInfo> selectedColumnTypes = Lists.newArrayList();
  protected List<ObjectInspector> selectedColumnObjInspectors = Lists.newArrayList();
  protected List<HiveFieldConverter> selectedColumnFieldConverters = Lists.newArrayList();
  protected List<String> selectedPartitionNames = Lists.newArrayList();
  protected List<TypeInfo> selectedPartitionTypes = Lists.newArrayList();
  protected List<Object> selectedPartitionValues = Lists.newArrayList();
  protected List<String> tableColumns; // all columns in table (not including partition columns)
  protected SerDe serde;
  protected StructObjectInspector sInspector;
  protected Object key, value;
  protected org.apache.hadoop.mapred.RecordReader reader;
  protected List<ValueVector> vectors = Lists.newArrayList();
  protected List<ValueVector> pVectors = Lists.newArrayList();
  protected Object redoRecord;
  protected boolean empty;
  private Map<String, String> hiveConfigOverride;
  private FragmentContext fragmentContext;
  private OperatorContext operatorContext;


  protected static final int TARGET_RECORD_COUNT = 4000;
  protected static final int FIELD_SIZE = 50;

  public HiveRecordReader(Table table, Partition partition, InputSplit inputSplit, List<SchemaPath> projectedColumns,
      FragmentContext context, Map<String, String> hiveConfigOverride) throws ExecutionSetupException {
    this.table = table;
    this.partition = partition;
    this.inputSplit = inputSplit;
    this.context = context;
    this.empty = (inputSplit == null && partition == null);
    this.hiveConfigOverride = hiveConfigOverride;
    this.fragmentContext=context;
    setColumns(projectedColumns);
    init();
  }

  private void init() throws ExecutionSetupException {
    Properties properties;
    JobConf job = new JobConf();
    if (partition != null) {
      properties = MetaStoreUtils.getPartitionMetadata(partition, table);

      // SerDe expects properties from Table, but above call doesn't add Table properties.
      // Include Table properties in final list in order to not to break SerDes that depend on
      // Table properties. For example AvroSerDe gets the schema from properties (passed as second argument)
      for (Map.Entry<String, String> entry : table.getParameters().entrySet()) {
        if (entry.getKey() != null && entry.getKey() != null) {
          properties.put(entry.getKey(), entry.getValue());
        }
      }
    } else {
      properties = MetaStoreUtils.getTableMetadata(table);
    }
    for (Object obj : properties.keySet()) {
      job.set((String) obj, (String) properties.get(obj));
    }
    for(Map.Entry<String, String> entry : hiveConfigOverride.entrySet()) {
      job.set(entry.getKey(), entry.getValue());
    }
    InputFormat format;
    String sLib = (partition == null) ? table.getSd().getSerdeInfo().getSerializationLib() : partition.getSd().getSerdeInfo().getSerializationLib();
    String inputFormatName = (partition == null) ? table.getSd().getInputFormat() : partition.getSd().getInputFormat();
    try {
      format = (InputFormat) Class.forName(inputFormatName).getConstructor().newInstance();
      Class c = Class.forName(sLib);
      serde = (SerDe) c.getConstructor().newInstance();
      serde.initialize(job, properties);
    } catch (ReflectiveOperationException | SerDeException e) {
      throw new ExecutionSetupException("Unable to instantiate InputFormat", e);
    }
    job.setInputFormat(format.getClass());

    List<FieldSchema> partitionKeys = table.getPartitionKeys();
    List<String> partitionNames = Lists.newArrayList();
    for (FieldSchema field : partitionKeys) {
      partitionNames.add(field.getName());
    }

    try {
      ObjectInspector oi = serde.getObjectInspector();
      if (oi.getCategory() != ObjectInspector.Category.STRUCT) {
        throw new UnsupportedOperationException(String.format("%s category not supported", oi.getCategory()));
      }
      sInspector = (StructObjectInspector) oi;
      StructTypeInfo sTypeInfo = (StructTypeInfo) TypeInfoUtils.getTypeInfoFromObjectInspector(sInspector);
      List<Integer> columnIds = Lists.newArrayList();
      if (isStarQuery()) {
        selectedColumnNames = sTypeInfo.getAllStructFieldNames();
        tableColumns = selectedColumnNames;
        for(int i=0; i<selectedColumnNames.size(); i++) {
          columnIds.add(i);
        }
      } else {
        tableColumns = sTypeInfo.getAllStructFieldNames();
        selectedColumnNames = Lists.newArrayList();
        for (SchemaPath field : getColumns()) {
          String columnName = field.getRootSegment().getPath();
          if (!tableColumns.contains(columnName)) {
            if (partitionNames.contains(columnName)) {
              selectedPartitionNames.add(columnName);
            } else {
              throw new ExecutionSetupException(String.format("Column %s does not exist", columnName));
            }
          } else {
            columnIds.add(tableColumns.indexOf(columnName));
            selectedColumnNames.add(columnName);
          }
        }
      }
      ColumnProjectionUtils.appendReadColumns(job, columnIds, selectedColumnNames);

      for (String columnName : selectedColumnNames) {
        ObjectInspector fieldOI = sInspector.getStructFieldRef(columnName).getFieldObjectInspector();
        TypeInfo typeInfo = TypeInfoUtils.getTypeInfoFromTypeString(fieldOI.getTypeName());

        selectedColumnObjInspectors.add(fieldOI);
        selectedColumnTypes.add(typeInfo);
        selectedColumnFieldConverters.add(HiveFieldConverter.create(typeInfo, fragmentContext));
      }

      if (isStarQuery()) {
        selectedPartitionNames = partitionNames;
      }

      for (int i = 0; i < table.getPartitionKeys().size(); i++) {
        FieldSchema field = table.getPartitionKeys().get(i);
        if (selectedPartitionNames.contains(field.getName())) {
          TypeInfo pType = TypeInfoUtils.getTypeInfoFromTypeString(field.getType());
          selectedPartitionTypes.add(pType);

          if (partition != null) {
            selectedPartitionValues.add(convertPartitionType(pType, partition.getValues().get(i)));
          }
        }
      }
    } catch (Exception e) {
      throw new ExecutionSetupException("Failure while initializing HiveRecordReader: " + e.getMessage(), e);
    }

    if (!empty) {
      try {
        reader = format.getRecordReader(inputSplit, job, Reporter.NULL);
      } catch (IOException e) {
        throw new ExecutionSetupException("Failed to get o.a.hadoop.mapred.RecordReader from Hive InputFormat", e);
      }
      key = reader.createKey();
      value = reader.createValue();
    }
  }

  @Override
  public void setup(OperatorContext context, OutputMutator output) throws ExecutionSetupException {
    this.operatorContext = context;
    try {
      for (int i = 0; i < selectedColumnNames.size(); i++) {
        MajorType type = getMajorTypeFromHiveTypeInfo(selectedColumnTypes.get(i), true);
        MaterializedField field = MaterializedField.create(SchemaPath.getSimplePath(selectedColumnNames.get(i)), type);
        Class vvClass = TypeHelper.getValueVectorClass(type.getMinorType(), type.getMode());
        vectors.add(output.addField(field, vvClass));
      }

      for (int i = 0; i < selectedPartitionNames.size(); i++) {
        MajorType type = getMajorTypeFromHiveTypeInfo(selectedPartitionTypes.get(i), false);
        MaterializedField field = MaterializedField.create(SchemaPath.getSimplePath(selectedPartitionNames.get(i)), type);
        Class vvClass = TypeHelper.getValueVectorClass(field.getType().getMinorType(), field.getDataMode());
        pVectors.add(output.addField(field, vvClass));
      }
    } catch(SchemaChangeException e) {
      throw new ExecutionSetupException(e);
    }
  }

  @Override
  public int next() {
    for (ValueVector vv : vectors) {
      AllocationHelper.allocateNew(vv, TARGET_RECORD_COUNT);
    }
    if (empty) {
      setValueCountAndPopulatePartitionVectors(0);
      return 0;
    }

    try {
      int recordCount = 0;

      if (redoRecord != null) {
        // Try writing the record that didn't fit into the last RecordBatch
        Object deSerializedValue = serde.deserialize((Writable) redoRecord);
        boolean status = readHiveRecordAndInsertIntoRecordBatch(deSerializedValue, recordCount);
        if (!status) {
          throw new DrillRuntimeException("Current record is too big to fit into allocated ValueVector buffer");
        }
        redoRecord = null;
        recordCount++;
      }

      while (recordCount < TARGET_RECORD_COUNT && reader.next(key, value)) {
        Object deSerializedValue = serde.deserialize((Writable) value);
        boolean status = readHiveRecordAndInsertIntoRecordBatch(deSerializedValue, recordCount);
        if (!status) {
          redoRecord = value;
          setValueCountAndPopulatePartitionVectors(recordCount);
          return recordCount;
        }
        recordCount++;
      }

      setValueCountAndPopulatePartitionVectors(recordCount);
      return recordCount;
    } catch (IOException | SerDeException e) {
      throw new DrillRuntimeException(e);
    }
  }

  private boolean readHiveRecordAndInsertIntoRecordBatch(Object deSerializedValue, int outputRecordIndex) {
    boolean success;
    for (int i = 0; i < selectedColumnNames.size(); i++) {
      String columnName = selectedColumnNames.get(i);
      Object hiveValue = sInspector.getStructFieldData(deSerializedValue, sInspector.getStructFieldRef(columnName));

      if (hiveValue != null) {
        selectedColumnFieldConverters.get(i).setSafeValue(selectedColumnObjInspectors.get(i), hiveValue,
            vectors.get(i), outputRecordIndex);
      }
    }

    return true;
  }

  private void setValueCountAndPopulatePartitionVectors(int recordCount) {
    for (ValueVector v : vectors) {
      v.getMutator().setValueCount(recordCount);
    }

    if (partition != null) {
      populatePartitionVectors(recordCount);
    }
  }

  @Override
  public void cleanup() {
    try {
      if (reader != null) {
        reader.close();
        reader = null;
      }
    } catch (Exception e) {
      logger.warn("Failure while closing Hive Record reader.", e);
    }
  }

  private MinorType getMinorTypeFromHivePrimitiveTypeInfo(PrimitiveTypeInfo primitiveTypeInfo) {
    switch(primitiveTypeInfo.getPrimitiveCategory()) {
      case BINARY:
        return TypeProtos.MinorType.VARBINARY;
      case BOOLEAN:
        return MinorType.BIT;
      case DECIMAL: {

        if (context.getOptions().getOption(PlannerSettings.ENABLE_DECIMAL_DATA_TYPE_KEY).bool_val == false) {
          throw UserException.unsupportedError()
              .message(ExecErrorConstants.DECIMAL_DISABLE_ERR_MSG)
              .build();
        }
        DecimalTypeInfo decimalTypeInfo = (DecimalTypeInfo) primitiveTypeInfo;
        return DecimalUtility.getDecimalDataType(decimalTypeInfo.precision());
      }
      case DOUBLE:
        return MinorType.FLOAT8;
      case FLOAT:
        return MinorType.FLOAT4;
      // TODO (DRILL-2470)
      // Byte and short (tinyint and smallint in SQL types) are currently read as integers
      // as these smaller integer types are not fully supported in Drill today.
      case SHORT:
      case BYTE:
      case INT:
        return MinorType.INT;
      case LONG:
        return MinorType.BIGINT;
      case STRING:
      case VARCHAR:
        return MinorType.VARCHAR;
      case TIMESTAMP:
        return MinorType.TIMESTAMP;
      case DATE:
        return MinorType.DATE;
    }

    throwUnsupportedHiveDataTypeError(primitiveTypeInfo.getPrimitiveCategory().toString());
    return null;
  }

  public MajorType getMajorTypeFromHiveTypeInfo(TypeInfo typeInfo, boolean nullable) {
    switch (typeInfo.getCategory()) {
      case PRIMITIVE: {
        PrimitiveTypeInfo primitiveTypeInfo = (PrimitiveTypeInfo) typeInfo;
        MinorType minorType = getMinorTypeFromHivePrimitiveTypeInfo(primitiveTypeInfo);
        MajorType.Builder typeBuilder = MajorType.newBuilder().setMinorType(minorType)
            .setMode((nullable ? DataMode.OPTIONAL : DataMode.REQUIRED));

        if (primitiveTypeInfo.getPrimitiveCategory() == PrimitiveCategory.DECIMAL) {
          DecimalTypeInfo decimalTypeInfo = (DecimalTypeInfo) primitiveTypeInfo;
          typeBuilder.setPrecision(decimalTypeInfo.precision())
              .setScale(decimalTypeInfo.scale()).build();
        }

        return typeBuilder.build();
      }

      case LIST:
      case MAP:
      case STRUCT:
      case UNION:
      default:
        throwUnsupportedHiveDataTypeError(typeInfo.getCategory().toString());
    }

    return null;
  }

  protected void populatePartitionVectors(int recordCount) {
    for (int i = 0; i < pVectors.size(); i++) {
      int size = 50;
      ValueVector vector = pVectors.get(i);
      Object val = selectedPartitionValues.get(i);
      PrimitiveCategory pCat = ((PrimitiveTypeInfo)selectedPartitionTypes.get(i)).getPrimitiveCategory();
      if (pCat == PrimitiveCategory.BINARY || pCat == PrimitiveCategory.STRING || pCat == PrimitiveCategory.VARCHAR) {
        size = ((byte[]) selectedPartitionValues.get(i)).length;
      }

      AllocationHelper.allocateNew(vector, recordCount);

      switch(pCat) {
        case BINARY: {
          VarBinaryVector v = (VarBinaryVector) vector;
          byte[] value = (byte[]) val;
          for (int j = 0; j < recordCount; j++) {
            v.getMutator().setSafe(j, value);
          }
          break;
        }
        case BOOLEAN: {
          BitVector v = (BitVector) vector;
          Boolean value = (Boolean) val;
          for (int j = 0; j < recordCount; j++) {
            v.getMutator().set(j, value ? 1 : 0);
          }
          break;
        }
        case DOUBLE: {
          Float8Vector v = (Float8Vector) vector;
          double value = (double) val;
          for (int j = 0; j < recordCount; j++) {
            v.getMutator().setSafe(j, value);
          }
          break;
        }
        case FLOAT: {
          Float4Vector v = (Float4Vector) vector;
          float value = (float) val;
          for (int j = 0; j < recordCount; j++) {
            v.getMutator().setSafe(j, value);
          }
          break;
        }
        case BYTE:
        case SHORT:
        case INT: {
          IntVector v = (IntVector) vector;
          int value = (int) val;
          for (int j = 0; j < recordCount; j++) {
            v.getMutator().setSafe(j, value);
          }
          break;
        }
        case LONG: {
          BigIntVector v = (BigIntVector) vector;
          long value = (long) val;
          for (int j = 0; j < recordCount; j++) {
            v.getMutator().setSafe(j, value);
          }
          break;
        }
        case VARCHAR:
        case STRING: {
          VarCharVector v = (VarCharVector) vector;
          byte[] value = (byte[]) val;
          for (int j = 0; j < recordCount; j++) {
            v.getMutator().setSafe(j, value);
          }
          break;
        }
        case TIMESTAMP: {
          TimeStampVector v = (TimeStampVector) vector;
          DateTime ts = new DateTime(((Timestamp) val).getTime()).withZoneRetainFields(DateTimeZone.UTC);
          long value = ts.getMillis();
          for (int j = 0; j < recordCount; j++) {
            v.getMutator().setSafe(j, value);
          }
          break;
        }
        case DATE: {
          DateVector v = (DateVector) vector;
          DateTime date = new DateTime(((Date)val).getTime()).withZoneRetainFields(DateTimeZone.UTC);
          long value = date.getMillis();
          for (int j = 0; j < recordCount; j++) {
            v.getMutator().setSafe(j, value);
          }
          break;
        }
        case DECIMAL: {
          populateDecimalPartitionVector((DecimalTypeInfo)selectedPartitionTypes.get(i), vector,
              ((HiveDecimal)val).bigDecimalValue(), recordCount);
          break;
        }
        default:
          throwUnsupportedHiveDataTypeError(pCat.toString());
      }
      vector.getMutator().setValueCount(recordCount);
    }
  }

  private void populateDecimalPartitionVector(DecimalTypeInfo typeInfo, ValueVector vector, BigDecimal bigDecimal,
      int recordCount) {
    int precision = typeInfo.precision();
    int scale = typeInfo.scale();
    if (precision <= 9) {
      Decimal9Holder holder = new Decimal9Holder();
      holder.scale = scale;
      holder.precision = precision;
      holder.value = DecimalUtility.getDecimal9FromBigDecimal(bigDecimal, scale, precision);
      Decimal9Vector v = (Decimal9Vector) vector;
      for (int j = 0; j < recordCount; j++) {
        v.getMutator().setSafe(j, holder);
      }
    } else if (precision <= 18) {
      Decimal18Holder holder = new Decimal18Holder();
      holder.scale = scale;
      holder.precision = precision;
      holder.value = DecimalUtility.getDecimal18FromBigDecimal(bigDecimal, scale, precision);
      Decimal18Vector v = (Decimal18Vector) vector;
      for (int j = 0; j < recordCount; j++) {
        v.getMutator().setSafe(j, holder);
      }
    } else if (precision <= 28) {
      Decimal28SparseHolder holder = new Decimal28SparseHolder();
      holder.scale = scale;
      holder.precision = precision;
      holder.buffer = fragmentContext.getManagedBuffer(
          Decimal28SparseHolder.nDecimalDigits * DecimalUtility.integerSize);
      holder.start = 0;
      DecimalUtility.getSparseFromBigDecimal(bigDecimal, holder.buffer, 0, scale, precision,
          Decimal28SparseHolder.nDecimalDigits);
      Decimal28SparseVector v = (Decimal28SparseVector) vector;
      for (int j = 0; j < recordCount; j++) {
        v.getMutator().setSafe(j, holder);
      }
    } else {
      Decimal38SparseHolder holder = new Decimal38SparseHolder();
      holder.scale = scale;
      holder.precision = precision;
      holder.buffer = fragmentContext.getManagedBuffer(
          Decimal38SparseHolder.nDecimalDigits * DecimalUtility.integerSize);
      holder.start = 0;
      DecimalUtility.getSparseFromBigDecimal(bigDecimal, holder.buffer, 0, scale, precision,
          Decimal38SparseHolder.nDecimalDigits);
      Decimal38SparseVector v = (Decimal38SparseVector) vector;
      for (int j = 0; j < recordCount; j++) {
        v.getMutator().setSafe(j, holder);
      }
    }
  }

  /** Partition value is received in string format. Convert it into appropriate object based on the type. */
  private Object convertPartitionType(TypeInfo typeInfo, String value) {
    if (typeInfo.getCategory() != Category.PRIMITIVE) {
      // In Hive only primitive types are allowed as partition column types.
      throw new DrillRuntimeException("Non-Primitive types are not allowed as partition column type in Hive, " +
          "but received one: " + typeInfo.getCategory());
    }

    PrimitiveCategory pCat = ((PrimitiveTypeInfo) typeInfo).getPrimitiveCategory();
    switch (pCat) {
      case BINARY:
        return value.getBytes();
      case BOOLEAN:
        return Boolean.parseBoolean(value);
      case DECIMAL: {
        DecimalTypeInfo decimalTypeInfo = (DecimalTypeInfo) typeInfo;
        return HiveDecimalUtils.enforcePrecisionScale(HiveDecimal.create(value),
            decimalTypeInfo.precision(), decimalTypeInfo.scale());
      }
      case DOUBLE:
        return Double.parseDouble(value);
      case FLOAT:
        return Float.parseFloat(value);
      case BYTE:
      case SHORT:
      case INT:
        return Integer.parseInt(value);
      case LONG:
        return Long.parseLong(value);
      case STRING:
      case VARCHAR:
        return value.getBytes();
      case TIMESTAMP:
        return Timestamp.valueOf(value);
      case DATE:
        return Date.valueOf(value);
    }

    throwUnsupportedHiveDataTypeError(pCat.toString());
    return null;
  }

  public static void throwUnsupportedHiveDataTypeError(String unsupportedType) {
    StringBuilder errMsg = new StringBuilder();
    errMsg.append(String.format("Unsupported Hive data type %s. ", unsupportedType));
    errMsg.append(System.getProperty("line.separator"));
    errMsg.append("Following Hive data types are supported in Drill for querying: ");
    errMsg.append(
        "BOOLEAN, BYTE, SHORT, INT, LONG, FLOAT, DOUBLE, DATE, TIMESTAMP, BINARY, DECIMAL, STRING, and VARCHAR");

    throw new RuntimeException(errMsg.toString());
  }
}


File: exec/java-exec/src/main/codegen/templates/ListWriters.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

<@pp.dropOutputFile />

<#list ["Single", "Repeated"] as mode>
<@pp.changeOutputFile name="/org/apache/drill/exec/vector/complex/impl/${mode}ListWriter.java" />


<#include "/@includes/license.ftl" />

package org.apache.drill.exec.vector.complex.impl;
<#if mode == "Single">
  <#assign containerClass = "AbstractContainerVector" />
  <#assign index = "idx()">
<#else>
  <#assign containerClass = "RepeatedListVector" />
  <#assign index = "currentChildIndex">
</#if>


<#include "/@includes/vv_imports.ftl" />

/* This class is generated using freemarker and the ListWriters.java template */
@SuppressWarnings("unused")
public class ${mode}ListWriter extends AbstractFieldWriter{
  
  static enum Mode { INIT, IN_MAP, IN_LIST <#list vv.types as type><#list type.minor as minor>, IN_${minor.class?upper_case}</#list></#list> }

  private final String name;
  protected final ${containerClass} container;
  private Mode mode = Mode.INIT;
  private FieldWriter writer;
  protected RepeatedValueVector innerVector;
  
  <#if mode == "Repeated">private int currentChildIndex = 0;</#if>
  public ${mode}ListWriter(String name, ${containerClass} container, FieldWriter parent){
    super(parent);
    this.name = name;
    this.container = container;
  }

  public ${mode}ListWriter(${containerClass} container, FieldWriter parent){
    super(parent);
    this.name = null;
    this.container = container;
  }

  public void allocate(){
    if(writer != null){
      writer.allocate();
    }
    
    <#if mode == "Repeated">
    container.allocateNew();
    </#if>
  }
  
  public void clear(){
    writer.clear();
  }

  public int getValueCapacity() {
    return innerVector==null ? 0:innerVector.getValueCapacity();
  }

  public void setValueCount(int count){
    if(innerVector != null) innerVector.getMutator().setValueCount(count);
  }
  
  public MapWriter map(){
    switch(mode){
    case INIT:
      int vectorCount = container.size();
      RepeatedMapVector vector = container.addOrGet(name, RepeatedMapVector.TYPE, RepeatedMapVector.class);
      innerVector = vector;
      writer = new RepeatedMapWriter(vector, this);
      if(vectorCount != container.size()) writer.allocate();
      writer.setPosition(${index});
      mode = Mode.IN_MAP;
      return writer;
    case IN_MAP:
      return writer;
    }

  throw UserException.unsupportedError().message(getUnsupportedErrorMsg("MAP", mode.name())).build();

  }
  
  public ListWriter list(){
    switch(mode){
    case INIT:
      int vectorCount = container.size();
      RepeatedListVector vector = container.addOrGet(name, RepeatedListVector.TYPE, RepeatedListVector.class);
      innerVector = vector;
      writer = new RepeatedListWriter(null, vector, this);
      if(vectorCount != container.size()) writer.allocate();
      writer.setPosition(${index});
      mode = Mode.IN_LIST;
      return writer;
    case IN_LIST:
      return writer;
    }

  throw UserException.unsupportedError().message(getUnsupportedErrorMsg("LIST", mode.name())).build();

  }
  
  <#list vv.types as type><#list type.minor as minor>
  <#assign lowerName = minor.class?uncap_first />
  <#assign upperName = minor.class?upper_case />
  <#assign capName = minor.class?cap_first />
  <#if lowerName == "int" ><#assign lowerName = "integer" /></#if>
  
  private static final MajorType ${upperName}_TYPE = Types.repeated(MinorType.${upperName});
  
  public ${capName}Writer ${lowerName}(){
    switch(mode){
    case INIT:
      int vectorCount = container.size();
      Repeated${capName}Vector vector = container.addOrGet(name, ${upperName}_TYPE, Repeated${capName}Vector.class);   
      innerVector = vector;
      writer = new Repeated${capName}WriterImpl(vector, this);
      if(vectorCount != container.size()) writer.allocate();
      writer.setPosition(${index});
      mode = Mode.IN_${upperName};
      return writer;
    case IN_${upperName}:
      return writer;
    }

  throw UserException.unsupportedError().message(getUnsupportedErrorMsg("${upperName}", mode.name())).build();

  }
  </#list></#list>

  public MaterializedField getField() {
    return container.getField();
  }

  <#if mode == "Repeated">
  
  public void start(){
    
    final RepeatedListVector list = (RepeatedListVector) container;
    final RepeatedListVector.RepeatedMutator mutator = list.getMutator();
    
    // make sure that the current vector can support the end position of this list.
    if(container.getValueCapacity() <= idx()){
      mutator.setValueCount(idx()+1);
    }
    
    // update the repeated vector to state that there is current+1 objects.
    RepeatedListHolder h = new RepeatedListHolder();
    list.getAccessor().get(idx(), h);
    if(h.start >= h.end){
      mutator.startNewValue(idx());  
    }
    currentChildIndex = container.getMutator().add(idx());
    if(writer != null){
      writer.setPosition(currentChildIndex);  
    }
  }
  
  
  
  public void end(){
    // noop, we initialize state at start rather than end.
  }
  <#else>
  
  
  public void setPosition(int index){
    super.setPosition(index);
    if(writer != null) writer.setPosition(index);
  }
  
  public void start(){
    // noop
  }
  
  public void end(){
    // noop
  }
  </#if>

  private String getUnsupportedErrorMsg(String expected, String found ){
    String f = found.substring(3);
    return String.format("In a list of type %s, encountered a value of type %s. "+
      "Drill does not support lists of different types.",
       f, expected
    );
  }

  }
</#list>




File: exec/java-exec/src/main/java/org/apache/drill/exec/client/PrintingResultsListener.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.client;

import io.netty.buffer.DrillBuf;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import org.apache.drill.common.config.DrillConfig;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.client.QuerySubmitter.Format;
import org.apache.drill.exec.exception.SchemaChangeException;
import org.apache.drill.exec.memory.BufferAllocator;
import org.apache.drill.exec.memory.TopLevelAllocator;
import org.apache.drill.exec.proto.UserBitShared.QueryData;
import org.apache.drill.exec.proto.UserBitShared.QueryId;
import org.apache.drill.exec.proto.UserBitShared.QueryResult.QueryState;
import org.apache.drill.exec.record.RecordBatchLoader;
import org.apache.drill.exec.rpc.user.ConnectionThrottle;
import org.apache.drill.exec.rpc.user.QueryDataBatch;
import org.apache.drill.exec.rpc.user.UserResultsListener;
import org.apache.drill.exec.util.VectorUtil;

import com.google.common.base.Stopwatch;

public class PrintingResultsListener implements UserResultsListener {
  AtomicInteger count = new AtomicInteger();
  private CountDownLatch latch = new CountDownLatch(1);
  RecordBatchLoader loader;
  Format format;
  int    columnWidth;
  BufferAllocator allocator;
  volatile UserException exception;
  QueryId queryId;
  Stopwatch w = new Stopwatch();

  public PrintingResultsListener(DrillConfig config, Format format, int columnWidth) {
    this.allocator = new TopLevelAllocator(config);
    loader = new RecordBatchLoader(allocator);
    this.format = format;
    this.columnWidth = columnWidth;
  }

  @Override
  public void submissionFailed(UserException ex) {
    exception = ex;
    System.out.println("Exception (no rows returned): " + ex + ".  Returned in " + w.elapsed(TimeUnit.MILLISECONDS)
        + "ms.");
    latch.countDown();
  }

  @Override
  public void queryCompleted(QueryState state) {
    allocator.close();
    latch.countDown();
    System.out.println("Total rows returned : " + count.get() + ".  Returned in " + w.elapsed(TimeUnit.MILLISECONDS)
        + "ms.");
  }

  @Override
  public void dataArrived(QueryDataBatch result, ConnectionThrottle throttle) {
    final QueryData header = result.getHeader();
    final DrillBuf data = result.getData();

    if (data != null) {
      count.addAndGet(header.getRowCount());
      try {
        loader.load(header.getDef(), data);
        // TODO:  Clean:  DRILL-2933:  That load(...) no longer throws
        // SchemaChangeException, so check/clean catch clause below.
      } catch (SchemaChangeException e) {
        submissionFailed(UserException.systemError(e).build());
      }

      switch(format) {
        case TABLE:
          VectorUtil.showVectorAccessibleContent(loader, columnWidth);
          break;
        case TSV:
          VectorUtil.showVectorAccessibleContent(loader, "\t");
          break;
        case CSV:
          VectorUtil.showVectorAccessibleContent(loader, ",");
          break;
      }
      loader.clear();
    }

    result.release();
  }

  public int await() throws Exception {
    latch.await();
    if (exception != null) {
      throw exception;
    }
    return count.get();
  }

  public QueryId getQueryId() {
    return queryId;
  }

  @Override
  public void queryIdArrived(QueryId queryId) {
    w.start();
    this.queryId = queryId;
  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/expr/fn/impl/AggregateErrorFunctions.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.expr.fn.impl;

import org.apache.drill.exec.expr.DrillAggFunc;
import org.apache.drill.exec.expr.annotations.FunctionTemplate;
import org.apache.drill.exec.expr.annotations.Output;
import org.apache.drill.exec.expr.annotations.Param;
import org.apache.drill.exec.expr.annotations.Workspace;
import org.apache.drill.exec.expr.holders.BigIntHolder;
import org.apache.drill.exec.expr.holders.BitHolder;
import org.apache.drill.exec.expr.holders.NullableBitHolder;
import org.apache.drill.exec.expr.holders.NullableVarCharHolder;
import org.apache.drill.exec.expr.holders.VarCharHolder;

/*
 * TODO: For a handful of functions this approach of using function binding to detect that it is an invalid function is okay.
 * However moving forward we should introduce a validation phase after we learn the data types and before we try
 * to perform function resolution. Otherwise with implicit cast we will try to bind to an existing function.
 */
public class AggregateErrorFunctions {

  @FunctionTemplate(names = {"sum", "max", "avg", "stddev_pop", "stddev_samp", "stddev", "var_pop",
      "var_samp", "variance"}, scope = FunctionTemplate.FunctionScope.POINT_AGGREGATE)
  public static class BitAggregateErrorFunctions implements DrillAggFunc {

    @Param BitHolder in;
    @Workspace BigIntHolder value;
    @Output BigIntHolder out;

    public void setup() {
      if (true) {
        throw org.apache.drill.common.exceptions.UserException
            .unsupportedError()
            .message("Only COUNT aggregate function supported for Boolean type")
            .build();
      }
    }

    @Override
    public void add() {
    }

    @Override
    public void output() {
    }

    @Override
    public void reset() {
    }

  }

  @FunctionTemplate(names = {"sum", "max", "avg", "stddev_pop", "stddev_samp", "stddev", "var_pop",
      "var_samp", "variance"}, scope = FunctionTemplate.FunctionScope.POINT_AGGREGATE)
  public static class NullableBitAggregateErrorFunctions implements DrillAggFunc {

    @Param NullableBitHolder in;
    @Workspace BigIntHolder value;
    @Output BigIntHolder out;

    public void setup() {
      if (true) {
        throw org.apache.drill.common.exceptions.UserException
            .unsupportedError()
            .message("Only COUNT aggregate function supported for Boolean type")
            .build();
      }
    }

    @Override
    public void add() {
    }

    @Override
    public void output() {
    }

    @Override
    public void reset() {
    }
  }


  @FunctionTemplate(names = {"sum", "avg", "stddev_pop", "stddev_samp", "stddev", "var_pop", "var_samp", "variance"},
      scope = FunctionTemplate.FunctionScope.POINT_AGGREGATE)
  public static class VarCharAggregateErrorFunctions implements DrillAggFunc {

    @Param VarCharHolder in;
    @Workspace BigIntHolder value;
    @Output BigIntHolder out;

    public void setup() {
      if (true) {
        throw org.apache.drill.common.exceptions.UserException
            .unsupportedError()
            .message("Only COUNT, MIN and MAX aggregate functions supported for VarChar type")
            .build();
      }
    }

    @Override
    public void add() {
    }

    @Override
    public void output() {
    }

    @Override
    public void reset() {
    }

  }

  @FunctionTemplate(names = {"sum", "avg", "stddev_pop", "stddev_samp", "stddev", "var_pop", "var_samp", "variance"},
      scope = FunctionTemplate.FunctionScope.POINT_AGGREGATE)
  public static class NullableVarCharAggregateErrorFunctions implements DrillAggFunc {

    @Param NullableVarCharHolder in;
    @Workspace BigIntHolder value;
    @Output BigIntHolder out;

    public void setup() {
      if (true) {
        throw org.apache.drill.common.exceptions.UserException
            .unsupportedError()
            .message("Only COUNT, MIN and MAX aggregate functions supported for VarChar type")
            .build();
      }
    }

    @Override
    public void add() {
    }

    @Override
    public void output() {
    }

    @Override
    public void reset() {
    }
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/ops/FragmentContext.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.ops;

import io.netty.buffer.DrillBuf;

import java.io.IOException;
import java.util.List;
import java.util.Map;

import org.apache.calcite.schema.SchemaPlus;

import org.apache.drill.common.config.DrillConfig;
import org.apache.drill.common.exceptions.ExecutionSetupException;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.ExecConstants;
import org.apache.drill.exec.exception.ClassTransformationException;
import org.apache.drill.exec.expr.ClassGenerator;
import org.apache.drill.exec.expr.CodeGenerator;
import org.apache.drill.exec.expr.fn.FunctionImplementationRegistry;
import org.apache.drill.exec.memory.BufferAllocator;
import org.apache.drill.exec.memory.OutOfMemoryException;
import org.apache.drill.exec.physical.base.PhysicalOperator;
import org.apache.drill.exec.memory.OutOfMemoryRuntimeException;
import org.apache.drill.exec.planner.physical.PlannerSettings;
import org.apache.drill.exec.proto.BitControl.PlanFragment;
import org.apache.drill.exec.proto.CoordinationProtos.DrillbitEndpoint;
import org.apache.drill.exec.proto.ExecProtos.FragmentHandle;
import org.apache.drill.exec.proto.GeneralRPCProtos.Ack;
import org.apache.drill.exec.rpc.RpcException;
import org.apache.drill.exec.rpc.RpcOutcomeListener;
import org.apache.drill.exec.rpc.control.ControlTunnel;
import org.apache.drill.exec.rpc.user.UserServer.UserClientConnection;
import org.apache.drill.exec.server.DrillbitContext;
import org.apache.drill.exec.server.options.FragmentOptionManager;
import org.apache.drill.exec.server.options.OptionList;
import org.apache.drill.exec.server.options.OptionManager;
import org.apache.drill.exec.store.PartitionExplorer;
import org.apache.drill.exec.store.SchemaConfig;
import org.apache.drill.exec.testing.ExecutionControls;
import org.apache.drill.exec.util.ImpersonationUtil;
import org.apache.drill.exec.work.batch.IncomingBuffers;

import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Preconditions;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;

/**
 * Contextual objects required for execution of a particular fragment.
 */
public class FragmentContext implements AutoCloseable, UdfUtilities {
  private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(FragmentContext.class);

  private final Map<DrillbitEndpoint, AccountingDataTunnel> tunnels = Maps.newHashMap();
  private final List<OperatorContextImpl> contexts = Lists.newLinkedList();

  private final DrillbitContext context;
  private final UserClientConnection connection; // is null if this context is for non-root fragment
  private final QueryContext queryContext; // is null if this context is for non-root fragment
  private final FragmentStats stats;
  private final FunctionImplementationRegistry funcRegistry;
  private final BufferAllocator allocator;
  private final PlanFragment fragment;
  private final ContextInformation contextInformation;
  private IncomingBuffers buffers;
  private final OptionManager fragmentOptions;
  private final BufferManager bufferManager;
  private ExecutorState executorState;
  private final ExecutionControls executionControls;

  private final SendingAccountor sendingAccountor = new SendingAccountor();
  private final Consumer<RpcException> exceptionConsumer = new Consumer<RpcException>() {
    @Override
    public void accept(final RpcException e) {
      fail(e);
    }

    @Override
    public void interrupt(final InterruptedException e) {
      if (shouldContinue()) {
        logger.error("Received an unexpected interrupt while waiting for the data send to complete.", e);
        fail(e);
      }
    }
  };

  private final RpcOutcomeListener<Ack> statusHandler = new StatusHandler(exceptionConsumer, sendingAccountor);
  private final AccountingUserConnection accountingUserConnection;

  /**
   * Create a FragmentContext instance for non-root fragment.
   *
   * @param dbContext DrillbitContext.
   * @param fragment Fragment implementation.
   * @param funcRegistry FunctionImplementationRegistry.
   * @throws ExecutionSetupException
   */
  public FragmentContext(final DrillbitContext dbContext, final PlanFragment fragment,
      final FunctionImplementationRegistry funcRegistry) throws ExecutionSetupException {
    this(dbContext, fragment, null, null, funcRegistry);
  }

  /**
   * Create a FragmentContext instance for root fragment.
   *
   * @param dbContext DrillbitContext.
   * @param fragment Fragment implementation.
   * @param queryContext QueryContext.
   * @param connection UserClientConnection.
   * @param funcRegistry FunctionImplementationRegistry.
   * @throws ExecutionSetupException
   */
  public FragmentContext(final DrillbitContext dbContext, final PlanFragment fragment, final QueryContext queryContext,
      final UserClientConnection connection, final FunctionImplementationRegistry funcRegistry)
    throws ExecutionSetupException {
    this.context = dbContext;
    this.queryContext = queryContext;
    this.connection = connection;
    this.accountingUserConnection = new AccountingUserConnection(connection, sendingAccountor, statusHandler);
    this.fragment = fragment;
    this.funcRegistry = funcRegistry;
    contextInformation = new ContextInformation(fragment.getCredentials(), fragment.getContext());

    logger.debug("Getting initial memory allocation of {}", fragment.getMemInitial());
    logger.debug("Fragment max allocation: {}", fragment.getMemMax());

    final OptionList list;
    if (!fragment.hasOptionsJson() || fragment.getOptionsJson().isEmpty()) {
      list = new OptionList();
    } else {
      try {
        list = dbContext.getConfig().getMapper().readValue(fragment.getOptionsJson(), OptionList.class);
      } catch (final Exception e) {
        throw new ExecutionSetupException("Failure while reading plan options.", e);
      }
    }
    fragmentOptions = new FragmentOptionManager(context.getOptionManager(), list);

    executionControls = new ExecutionControls(fragmentOptions, dbContext.getEndpoint());

    // Add the fragment context to the root allocator.
    // The QueryManager will call the root allocator to recalculate all the memory limits for all the fragments
    try {
      allocator = context.getAllocator().getChildAllocator(this, fragment.getMemInitial(), fragment.getMemMax(), true);
      Preconditions.checkNotNull(allocator, "Unable to acuqire allocator");
    } catch(final OutOfMemoryException | OutOfMemoryRuntimeException e) {
      throw UserException.memoryError(e)
        .addContext("Fragment", getHandle().getMajorFragmentId() + ":" + getHandle().getMinorFragmentId())
        .build();
    } catch(final Throwable e) {
      throw new ExecutionSetupException("Failure while getting memory allocator for fragment.", e);
    }

    stats = new FragmentStats(allocator, dbContext.getMetrics(), fragment.getAssignment());
    bufferManager = new BufferManager(this.allocator, this);
  }

  /**
   * TODO: Remove this constructor when removing the SimpleRootExec (DRILL-2097). This is kept only to avoid modifying
   * the long list of test files.
   */
  public FragmentContext(DrillbitContext dbContext, PlanFragment fragment, UserClientConnection connection,
      FunctionImplementationRegistry funcRegistry) throws ExecutionSetupException {
    this(dbContext, fragment, null, connection, funcRegistry);
  }

  public OptionManager getOptions() {
    return fragmentOptions;
  }

  public void setBuffers(final IncomingBuffers buffers) {
    Preconditions.checkArgument(this.buffers == null, "Can only set buffers once.");
    this.buffers = buffers;
  }

  public void setExecutorState(final ExecutorState executorState) {
    Preconditions.checkArgument(this.executorState == null, "ExecutorState can only be set once.");
    this.executorState = executorState;
  }

  public void fail(final Throwable cause) {
    executorState.fail(cause);
  }

  /**
   * Tells individual operations whether they should continue. In some cases, an external event (typically cancellation)
   * will mean that the fragment should prematurely exit execution. Long running operations should check this every so
   * often so that Drill is responsive to cancellation operations.
   *
   * @return false if the action should terminate immediately, true if everything is okay.
   */
  public boolean shouldContinue() {
    return executorState.shouldContinue();
  }

  public DrillbitContext getDrillbitContext() {
    return context;
  }

  public SchemaPlus getRootSchema() {
    if (queryContext == null) {
      fail(new UnsupportedOperationException("Schema tree can only be created in root fragment. " +
          "This is a non-root fragment."));
      return null;
    }

    final boolean isImpersonationEnabled = isImpersonationEnabled();
    // If impersonation is enabled, we want to view the schema as query user and suppress authorization errors. As for
    // InfoSchema purpose we want to show tables the user has permissions to list or query. If  impersonation is
    // disabled view the schema as Drillbit process user and throw authorization errors to client.
    SchemaConfig schemaConfig = SchemaConfig
        .newBuilder(
            isImpersonationEnabled ? queryContext.getQueryUserName() : ImpersonationUtil.getProcessUserName(),
            queryContext)
        .setIgnoreAuthErrors(isImpersonationEnabled)
        .build();

    return queryContext.getRootSchema(schemaConfig);
  }

  /**
   * Get this node's identity.
   * @return A DrillbitEndpoint object.
   */
  public DrillbitEndpoint getIdentity() {
    return context.getEndpoint();
  }

  public FragmentStats getStats() {
    return stats;
  }

  @Override
  public ContextInformation getContextInformation() {
    return contextInformation;
  }

  public DrillbitEndpoint getForemanEndpoint() {
    return fragment.getForeman();
  }

  /**
   * The FragmentHandle for this Fragment
   * @return FragmentHandle
   */
  public FragmentHandle getHandle() {
    return fragment.getHandle();
  }

  private String getFragIdString() {
    final FragmentHandle handle = getHandle();
    final String frag = handle != null ? handle.getMajorFragmentId() + ":" + handle.getMinorFragmentId() : "0:0";
    return frag;
  }



  /**
   * Get this fragment's allocator.
   * @return the allocator
   */
  @Deprecated
  public BufferAllocator getAllocator() {
    if (allocator == null) {
      logger.debug("Fragment: " + getFragIdString() + " Allocator is NULL");
    }
    return allocator;
  }

  public BufferAllocator getNewChildAllocator(final long initialReservation,
                                              final long maximumReservation,
                                              final boolean applyFragmentLimit) throws OutOfMemoryException {
    return allocator.getChildAllocator(this, initialReservation, maximumReservation, applyFragmentLimit);
  }

  public <T> T getImplementationClass(final ClassGenerator<T> cg)
      throws ClassTransformationException, IOException {
    return getImplementationClass(cg.getCodeGenerator());
  }

  public <T> T getImplementationClass(final CodeGenerator<T> cg)
      throws ClassTransformationException, IOException {
    return context.getCompiler().getImplementationClass(cg);
  }

  public <T> List<T> getImplementationClass(final ClassGenerator<T> cg, final int instanceCount) throws ClassTransformationException, IOException {
    return getImplementationClass(cg.getCodeGenerator(), instanceCount);
  }

  public <T> List<T> getImplementationClass(final CodeGenerator<T> cg, final int instanceCount) throws ClassTransformationException, IOException {
    return context.getCompiler().getImplementationClass(cg, instanceCount);
  }

  public AccountingUserConnection getUserDataTunnel() {
    Preconditions.checkState(connection != null, "Only Root fragment can get UserDataTunnel");
    return accountingUserConnection;
  }

  public ControlTunnel getControlTunnel(final DrillbitEndpoint endpoint) {
    return context.getController().getTunnel(endpoint);
  }

  public AccountingDataTunnel getDataTunnel(final DrillbitEndpoint endpoint) {
    AccountingDataTunnel tunnel = tunnels.get(endpoint);
    if (tunnel == null) {
      tunnel = new AccountingDataTunnel(context.getDataConnectionsPool().getTunnel(endpoint), sendingAccountor, statusHandler);
      tunnels.put(endpoint, tunnel);
    }
    return tunnel;
  }

  public IncomingBuffers getBuffers() {
    return buffers;
  }

  public OperatorContext newOperatorContext(PhysicalOperator popConfig, OperatorStats stats, boolean applyFragmentLimit)
      throws OutOfMemoryException {
    OperatorContextImpl context = new OperatorContextImpl(popConfig, this, stats, applyFragmentLimit);
    contexts.add(context);
    return context;
  }

  public OperatorContext newOperatorContext(PhysicalOperator popConfig, boolean applyFragmentLimit)
      throws OutOfMemoryException {
    OperatorContextImpl context = new OperatorContextImpl(popConfig, this, applyFragmentLimit);
    contexts.add(context);
    return context;
  }

  @VisibleForTesting
  @Deprecated
  public Throwable getFailureCause() {
    return executorState.getFailureCause();
  }

  @VisibleForTesting
  @Deprecated
  public boolean isFailed() {
    return executorState.isFailed();
  }

  public FunctionImplementationRegistry getFunctionRegistry() {
    return funcRegistry;
  }

  public DrillConfig getConfig() {
    return context.getConfig();
  }

  public void setFragmentLimit(final long limit) {
    allocator.setFragmentLimit(limit);
  }

  public ExecutionControls getExecutionControls() {
    return executionControls;
  }

  public String getQueryUserName() {
    return fragment.getCredentials().getUserName();
  }

  public boolean isImpersonationEnabled() {
    // TODO(DRILL-2097): Until SimpleRootExec tests are removed, we need to consider impersonation disabled if there is
    // no config
    if (getConfig() == null) {
      return false;
    }

    return getConfig().getBoolean(ExecConstants.IMPERSONATION_ENABLED);
  }

  @Override
  public void close() {
    waitForSendComplete();

    // close operator context
    for (OperatorContextImpl opContext : contexts) {
      suppressingClose(opContext);
    }

    suppressingClose(bufferManager);
    suppressingClose(buffers);
    suppressingClose(allocator);
  }

  private void suppressingClose(final AutoCloseable closeable) {
    try {
      if (closeable != null) {
        closeable.close();
      }
    } catch (final Exception e) {
      fail(e);
    }
  }

  public DrillBuf replace(final DrillBuf old, final int newSize) {
    return bufferManager.replace(old, newSize);
  }

  @Override
  public DrillBuf getManagedBuffer() {
    return bufferManager.getManagedBuffer();
  }

  public DrillBuf getManagedBuffer(final int size) {
    return bufferManager.getManagedBuffer(size);
  }

  @Override
  public PartitionExplorer getPartitionExplorer() {
    throw new UnsupportedOperationException(String.format("The partition explorer interface can only be used " +
        "in functions that can be evaluated at planning time. Make sure that the %s configuration " +
        "option is set to true.", PlannerSettings.CONSTANT_FOLDING.getOptionName()));
  }

  /**
   * Wait for ack that all outgoing batches have been sent
   */
  public void waitForSendComplete() {
    sendingAccountor.waitForSendComplete();
  }

  public interface ExecutorState {
    /**
     * Whether execution should continue.
     *
     * @return false if execution should stop.
     */
    public boolean shouldContinue();

    /**
     * Inform the executor if a exception occurs and fragment should be failed.
     *
     * @param t
     *          The exception that occurred.
     */
    public void fail(final Throwable t);

    @VisibleForTesting
    @Deprecated
    public boolean isFailed();

    @VisibleForTesting
    @Deprecated
    public Throwable getFailureCause();

  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/ops/ViewExpansionContext.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.ops;

import com.carrotsearch.hppc.ObjectIntOpenHashMap;
import com.google.common.base.Preconditions;
import org.apache.calcite.schema.SchemaPlus;
import org.apache.drill.common.exceptions.UserException;
import org.apache.calcite.plan.RelOptTable;
import org.apache.calcite.plan.RelOptTable.ToRelContext;

import static org.apache.drill.exec.ExecConstants.IMPERSONATION_MAX_CHAINED_USER_HOPS;

/**
 * Contains context information about view expansion(s) in a query. Part of {@link org.apache.drill.exec.ops
 * .QueryContext}. Before expanding a view into its definition, as part of the
 * {@link org.apache.drill.exec.planner.logical.DrillViewTable#toRel(ToRelContext, RelOptTable)}, first a
 * {@link ViewExpansionToken} is requested from ViewExpansionContext through {@link #reserveViewExpansionToken(String)}.
 * Once view expansion is complete, a token is released through {@link ViewExpansionToken#release()}. A view definition
 * itself may contain zero or more views for expanding those nested views also a token is obtained.
 *
 * Ex:
 *   Following are the available view tables: { "view_1", "view_2", "view_3", "view_4" }. Corresponding owners are
 *   {"view1Owner", "view2Owner", "view3Owner", "view4Owner"}.
 *   Definition of "view4" : "SELECT field4 FROM view3"
 *   Definition of "view3" : "SELECT field4, field3 FROM view2"
 *   Definition of "view2" : "SELECT field4, field3, field2 FROM view1"
 *   Definition of "view1" : "SELECT field4, field3, field2, field1 FROM someTable"
 *
 *   Query is: "SELECT * FROM view4".
 *   Steps:
 *     1. "view4" comes for expanding it into its definition
 *     2. A token "view4Token" is requested through {@link #reserveViewExpansionToken(String view4Owner)}
 *     3. "view4" is called for expansion. As part of it
 *       3.1 "view3" comes for expansion
 *       3.2 A token "view3Token" is requested through {@link #reserveViewExpansionToken(String view3Owner)}
 *       3.3 "view3" is called for expansion. As part of it
 *           3.3.1 "view2" comes for expansion
 *           3.3.2 A token "view2Token" is requested through {@link #reserveViewExpansionToken(String view2Owner)}
 *           3.3.3 "view2" is called for expansion. As part of it
 *                 3.3.3.1 "view1" comes for expansion
 *                 3.3.3.2 A token "view1Token" is requested through {@link #reserveViewExpansionToken(String view1Owner)}
 *                 3.3.3.3 "view1" is called for expansion
 *                 3.3.3.4 "view1" expansion is complete
 *                 3.3.3.5 Token "view1Token" is released
 *           3.3.4 "view2" expansion is complete
 *           3.3.5 Token "view2Token" is released
 *       3.4 "view3" expansion is complete
 *       3.5 Token "view3Token" is released
 *    4. "view4" expansion is complete
 *    5. Token "view4Token" is released.
 *
 */
public class ViewExpansionContext {
  private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(ViewExpansionContext.class);

  private final QueryContext queryContext;
  private final int maxChainedUserHops;
  private final String queryUser;
  private final ObjectIntOpenHashMap<String> userTokens = new ObjectIntOpenHashMap<>();

  public ViewExpansionContext(QueryContext queryContext) {
    this.queryContext = queryContext;
    this.maxChainedUserHops =
        queryContext.getConfig().getInt(IMPERSONATION_MAX_CHAINED_USER_HOPS);
    this.queryUser = queryContext.getQueryUserName();
  }

  public boolean isImpersonationEnabled() {
    return queryContext.isImpersonationEnabled();
  }

  /**
   * Reserve a token for expansion of view owned by given user name. If it can't issue any more tokens,
   * throws {@link UserException}.
   *
   * @param viewOwner Name of the user who owns the view.
   * @return An instance of {@link org.apache.drill.exec.ops.ViewExpansionContext.ViewExpansionToken} which must be
   *         released when done using the token.
   */
  public ViewExpansionToken reserveViewExpansionToken(String viewOwner) {
    int totalTokens = 1;
    if (!viewOwner.equals(queryUser)) {
      // We want to track the tokens only if the "viewOwner" is not same as the "queryUser".
      if (userTokens.containsKey(viewOwner)) {
        // If the user already exists, we don't need to validate the limit on maximum user hops in chained impersonation
        // as the limit is for number of unique users.
        totalTokens += userTokens.get(viewOwner);
      } else {
        // Make sure we are not exceeding the limit of maximum number impersonation user hops in chained impersonation.
        if (userTokens.size() == maxChainedUserHops) {
          final String errMsg =
              String.format("Cannot issue token for view expansion as issuing the token exceeds the " +
                  "maximum allowed number of user hops (%d) in chained impersonation.", maxChainedUserHops);
          logger.error(errMsg);
          throw UserException.permissionError().message(errMsg).build();
        }
      }

      userTokens.put(viewOwner, totalTokens);

      logger.debug("Issued view expansion token for user '{}'", viewOwner);
    }

    return new ViewExpansionToken(viewOwner);
  }

  private void releaseViewExpansionToken(ViewExpansionToken token) {
    final String viewOwner = token.viewOwner;

    if (viewOwner.equals(queryUser)) {
      // If the token owner and queryUser are same, no need to track the token release.
      return;
    }

    Preconditions.checkState(userTokens.containsKey(token.viewOwner),
        "Given user doesn't exist in User Token store. Make sure token for this user is obtained first.");

    final int userTokenCount = userTokens.get(viewOwner);
    if (userTokenCount == 1) {
      // Remove the user from collection, when there are no more tokens issued to the user.
      userTokens.remove(viewOwner);
    } else {
      userTokens.put(viewOwner, userTokenCount - 1);
    }
    logger.debug("Released view expansion token issued for user '{}'", viewOwner);
  }

  /**
   * Represents token issued to a view owner for expanding the view.
   */
  public class ViewExpansionToken {
    private final String viewOwner;

    private boolean released;

    ViewExpansionToken(String viewOwner) {
      this.viewOwner = viewOwner;
    }

    /**
     * Get schema tree for view owner who owns this token.
     * @return Root of schema tree.
     */
    public SchemaPlus getSchemaTree() {
      Preconditions.checkState(!released, "Trying to use released token.");
      return queryContext.getRootSchema(viewOwner);
    }

    /**
     * Release the token. Once released all method calls (except release) cause {@link java.lang.IllegalStateException}.
     */
    public void release() {
      if (!released) {
        released = true;
        releaseViewExpansionToken(this);
      }
    }
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/physical/impl/ScanBatch.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.physical.impl;

import io.netty.buffer.DrillBuf;

import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

import org.apache.drill.common.exceptions.ExecutionSetupException;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.common.expression.SchemaPath;
import org.apache.drill.common.types.TypeProtos.MinorType;
import org.apache.drill.common.types.Types;
import org.apache.drill.exec.ExecConstants;
import org.apache.drill.exec.exception.SchemaChangeException;
import org.apache.drill.exec.expr.TypeHelper;
import org.apache.drill.exec.memory.OutOfMemoryException;
import org.apache.drill.exec.memory.OutOfMemoryRuntimeException;
import org.apache.drill.exec.ops.FragmentContext;
import org.apache.drill.exec.ops.OperatorContext;
import org.apache.drill.exec.physical.base.PhysicalOperator;
import org.apache.drill.exec.record.BatchSchema;
import org.apache.drill.exec.record.BatchSchema.SelectionVectorMode;
import org.apache.drill.exec.record.CloseableRecordBatch;
import org.apache.drill.exec.record.MaterializedField;
import org.apache.drill.exec.record.TypedFieldId;
import org.apache.drill.exec.record.VectorContainer;
import org.apache.drill.exec.record.VectorWrapper;
import org.apache.drill.exec.record.WritableBatch;
import org.apache.drill.exec.record.selection.SelectionVector2;
import org.apache.drill.exec.record.selection.SelectionVector4;
import org.apache.drill.exec.server.options.OptionValue;
import org.apache.drill.exec.store.RecordReader;
import org.apache.drill.exec.testing.ControlsInjector;
import org.apache.drill.exec.testing.ControlsInjectorFactory;
import org.apache.drill.exec.vector.AllocationHelper;
import org.apache.drill.exec.vector.NullableVarCharVector;
import org.apache.drill.exec.vector.SchemaChangeCallBack;
import org.apache.drill.exec.vector.ValueVector;

import com.google.common.collect.Lists;
import com.google.common.collect.Maps;

/**
 * Record batch used for a particular scan. Operators against one or more
 */
public class ScanBatch implements CloseableRecordBatch {
  private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(ScanBatch.class);
  private static final ControlsInjector injector = ControlsInjectorFactory.getInjector(ScanBatch.class);

  private final Map<MaterializedField.Key, ValueVector> fieldVectorMap = Maps.newHashMap();

  private final VectorContainer container = new VectorContainer();
  private int recordCount;
  private final FragmentContext context;
  private final OperatorContext oContext;
  private Iterator<RecordReader> readers;
  private RecordReader currentReader;
  private BatchSchema schema;
  private final Mutator mutator = new Mutator();
  private Iterator<String[]> partitionColumns;
  private String[] partitionValues;
  private List<ValueVector> partitionVectors;
  private List<Integer> selectedPartitionColumns;
  private String partitionColumnDesignator;
  private boolean done = false;
  private SchemaChangeCallBack callBack = new SchemaChangeCallBack();

  public ScanBatch(PhysicalOperator subScanConfig, FragmentContext context, OperatorContext oContext,
                   Iterator<RecordReader> readers, List<String[]> partitionColumns, List<Integer> selectedPartitionColumns) throws ExecutionSetupException {
    this.context = context;
    this.readers = readers;
    if (!readers.hasNext()) {
      throw new ExecutionSetupException("A scan batch must contain at least one reader.");
    }
    this.currentReader = readers.next();
    this.oContext = oContext;

    boolean setup = false;
    try {
      oContext.getStats().startProcessing();
      this.currentReader.setup(oContext, mutator);
      setup = true;
    } finally {
      // if we had an exception during setup, make sure to release existing data.
      if (!setup) {
        currentReader.cleanup();
      }
      oContext.getStats().stopProcessing();
    }
    this.partitionColumns = partitionColumns.iterator();
    this.partitionValues = this.partitionColumns.hasNext() ? this.partitionColumns.next() : null;
    this.selectedPartitionColumns = selectedPartitionColumns;

    // TODO Remove null check after DRILL-2097 is resolved. That JIRA refers to test cases that do not initialize
    // options; so labelValue = null.
    final OptionValue labelValue = context.getOptions().getOption(ExecConstants.FILESYSTEM_PARTITION_COLUMN_LABEL);
    this.partitionColumnDesignator = labelValue == null ? "dir" : labelValue.string_val;

    addPartitionVectors();
  }

  public ScanBatch(PhysicalOperator subScanConfig, FragmentContext context, Iterator<RecordReader> readers) throws ExecutionSetupException {
    this(subScanConfig, context,
        context.newOperatorContext(subScanConfig, false /* ScanBatch is not subject to fragment memory limit */),
        readers, Collections.<String[]> emptyList(), Collections.<Integer> emptyList());
  }

  public FragmentContext getContext() {
    return context;
  }

  public OperatorContext getOperatorContext() {
    return oContext;
  }

  @Override
  public BatchSchema getSchema() {
    return schema;
  }

  @Override
  public int getRecordCount() {
    return recordCount;
  }

  @Override
  public void kill(boolean sendUpstream) {
    if (sendUpstream) {
      done = true;
    } else {
      releaseAssets();
    }
  }

  private void releaseAssets() {
    container.zeroVectors();
  }

  @Override
  public IterOutcome next() {
    if (done) {
      return IterOutcome.NONE;
    }
    oContext.getStats().startProcessing();
    try {
      try {
        injector.injectChecked(context.getExecutionControls(), "next-allocate", OutOfMemoryException.class);

        currentReader.allocate(fieldVectorMap);
      } catch (OutOfMemoryException | OutOfMemoryRuntimeException e) {
        logger.debug("Caught Out of Memory Exception", e);
        for (ValueVector v : fieldVectorMap.values()) {
          v.clear();
        }
        return IterOutcome.OUT_OF_MEMORY;
      }
      while ((recordCount = currentReader.next()) == 0) {
        try {
          if (!readers.hasNext()) {
            currentReader.cleanup();
            releaseAssets();
            done = true;
            if (mutator.isNewSchema()) {
              container.buildSchema(SelectionVectorMode.NONE);
              schema = container.getSchema();
            }
            return IterOutcome.NONE;
          }

          currentReader.cleanup();
          currentReader = readers.next();
          partitionValues = partitionColumns.hasNext() ? partitionColumns.next() : null;
          currentReader.setup(oContext, mutator);
          try {
            currentReader.allocate(fieldVectorMap);
          } catch (OutOfMemoryException e) {
            logger.debug("Caught OutOfMemoryException");
            for (ValueVector v : fieldVectorMap.values()) {
              v.clear();
            }
            return IterOutcome.OUT_OF_MEMORY;
          }
          addPartitionVectors();

        } catch (ExecutionSetupException e) {
          this.context.fail(e);
          releaseAssets();
          return IterOutcome.STOP;
        }
      }

      populatePartitionVectors();

      // this is a slight misuse of this metric but it will allow Readers to report how many records they generated.
      final boolean isNewSchema = mutator.isNewSchema();
      oContext.getStats().batchReceived(0, getRecordCount(), isNewSchema);

      if (isNewSchema) {
        container.buildSchema(SelectionVectorMode.NONE);
        schema = container.getSchema();
        return IterOutcome.OK_NEW_SCHEMA;
      } else {
        return IterOutcome.OK;
      }
    } catch (OutOfMemoryRuntimeException ex) {
      context.fail(UserException.memoryError(ex).build());
      return IterOutcome.STOP;
    } catch (Exception ex) {
      logger.debug("Failed to read the batch. Stopping...", ex);
      context.fail(ex);
      return IterOutcome.STOP;
    } finally {
      oContext.getStats().stopProcessing();
    }
  }

  private void addPartitionVectors() throws ExecutionSetupException{
    try {
      if (partitionVectors != null) {
        for (ValueVector v : partitionVectors) {
          v.clear();
        }
      }
      partitionVectors = Lists.newArrayList();
      for (int i : selectedPartitionColumns) {
        MaterializedField field = MaterializedField.create(SchemaPath.getSimplePath(partitionColumnDesignator + i), Types.optional(MinorType.VARCHAR));
        ValueVector v = mutator.addField(field, NullableVarCharVector.class);
        partitionVectors.add(v);
      }
    } catch(SchemaChangeException e) {
      throw new ExecutionSetupException(e);
    }
  }

  private void populatePartitionVectors() {
    for (int index = 0; index < selectedPartitionColumns.size(); index++) {
      int i = selectedPartitionColumns.get(index);
      NullableVarCharVector v = (NullableVarCharVector) partitionVectors.get(index);
      if (partitionValues.length > i) {
        String val = partitionValues[i];
        AllocationHelper.allocate(v, recordCount, val.length());
        byte[] bytes = val.getBytes();
        for (int j = 0; j < recordCount; j++) {
          v.getMutator().setSafe(j, bytes, 0, bytes.length);
        }
        v.getMutator().setValueCount(recordCount);
      } else {
        AllocationHelper.allocate(v, recordCount, 0);
        v.getMutator().setValueCount(recordCount);
      }
    }
  }

  @Override
  public SelectionVector2 getSelectionVector2() {
    throw new UnsupportedOperationException();
  }

  @Override
  public SelectionVector4 getSelectionVector4() {
    throw new UnsupportedOperationException();
  }

  @Override
  public TypedFieldId getValueVectorId(SchemaPath path) {
    return container.getValueVectorId(path);
  }

  @Override
  public VectorWrapper<?> getValueAccessorById(Class<?> clazz, int... ids) {
    return container.getValueAccessorById(clazz, ids);
  }



  private class Mutator implements OutputMutator {

    boolean schemaChange = true;

    @SuppressWarnings("unchecked")
    @Override
    public <T extends ValueVector> T addField(MaterializedField field, Class<T> clazz) throws SchemaChangeException {
      // Check if the field exists
      ValueVector v = fieldVectorMap.get(field.key());

      if (v == null || v.getClass() != clazz) {
        // Field does not exist add it to the map and the output container
        v = TypeHelper.getNewVector(field, oContext.getAllocator(), callBack);
        if (!clazz.isAssignableFrom(v.getClass())) {
          throw new SchemaChangeException(String.format("The class that was provided %s does not correspond to the expected vector type of %s.", clazz.getSimpleName(), v.getClass().getSimpleName()));
        }

        ValueVector old = fieldVectorMap.put(field.key(), v);
        if(old != null){
          old.clear();
          container.remove(old);
        }

        container.add(v);
        // Adding new vectors to the container mark that the schema has changed
        schemaChange = true;
      }

      return (T) v;
    }

    @Override
    public void allocate(int recordCount) {
      for (ValueVector v : fieldVectorMap.values()) {
        AllocationHelper.allocate(v, recordCount, 50, 10);
      }
    }

    @Override
    public boolean isNewSchema() {
      // Check if top level schema has changed, second condition checks if one of the deeper map schema has changed
      if (schemaChange || callBack.getSchemaChange()) {
        schemaChange = false;
        return true;
      }
      return false;
    }

    @Override
    public DrillBuf getManagedBuffer() {
      return oContext.getManagedBuffer();
    }
  }

  @Override
  public Iterator<VectorWrapper<?>> iterator() {
    return container.iterator();
  }

  @Override
  public WritableBatch getWritableBatch() {
    return WritableBatch.get(this);
  }

  public void close() {
    container.clear();
    for (ValueVector v : partitionVectors) {
      v.clear();
    }
    fieldVectorMap.clear();
    currentReader.cleanup();
  }

  @Override
  public VectorContainer getOutgoingContainer() {
    throw new UnsupportedOperationException(String.format(" You should not call getOutgoingContainer() for class %s", this.getClass().getCanonicalName()));
  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/physical/impl/aggregate/HashAggBatch.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.physical.impl.aggregate;

import java.io.IOException;

import org.apache.drill.common.exceptions.ExecutionSetupException;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.common.expression.ErrorCollector;
import org.apache.drill.common.expression.ErrorCollectorImpl;
import org.apache.drill.common.expression.LogicalExpression;
import org.apache.drill.common.logical.data.NamedExpression;
import org.apache.drill.exec.ExecConstants;
import org.apache.drill.exec.compile.sig.GeneratorMapping;
import org.apache.drill.exec.compile.sig.MappingSet;
import org.apache.drill.exec.exception.ClassTransformationException;
import org.apache.drill.exec.exception.SchemaChangeException;
import org.apache.drill.exec.expr.ClassGenerator;
import org.apache.drill.exec.expr.ClassGenerator.HoldingContainer;
import org.apache.drill.exec.expr.CodeGenerator;
import org.apache.drill.exec.expr.ExpressionTreeMaterializer;
import org.apache.drill.exec.expr.TypeHelper;
import org.apache.drill.exec.expr.ValueVectorWriteExpression;
import org.apache.drill.exec.ops.FragmentContext;
import org.apache.drill.exec.physical.config.HashAggregate;
import org.apache.drill.exec.physical.impl.aggregate.HashAggregator.AggOutcome;
import org.apache.drill.exec.physical.impl.common.HashTable;
import org.apache.drill.exec.physical.impl.common.HashTableConfig;
import org.apache.drill.exec.record.AbstractRecordBatch;
import org.apache.drill.exec.record.BatchSchema.SelectionVectorMode;
import org.apache.drill.exec.record.MaterializedField;
import org.apache.drill.exec.record.RecordBatch;
import org.apache.drill.exec.record.TypedFieldId;
import org.apache.drill.exec.record.VectorWrapper;
import org.apache.drill.exec.record.selection.SelectionVector2;
import org.apache.drill.exec.record.selection.SelectionVector4;
import org.apache.drill.exec.vector.AllocationHelper;
import org.apache.drill.exec.vector.ValueVector;

import com.sun.codemodel.JExpr;
import com.sun.codemodel.JVar;

public class HashAggBatch extends AbstractRecordBatch<HashAggregate> {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(HashAggBatch.class);

  private HashAggregator aggregator;
  private final RecordBatch incoming;
  private LogicalExpression[] aggrExprs;
  private TypedFieldId[] groupByOutFieldIds;
  private TypedFieldId[] aggrOutFieldIds;      // field ids for the outgoing batch

  private final GeneratorMapping UPDATE_AGGR_INSIDE =
      GeneratorMapping.create("setupInterior" /* setup method */, "updateAggrValuesInternal" /* eval method */,
          "resetValues" /* reset */, "cleanup" /* cleanup */);

  private final GeneratorMapping UPDATE_AGGR_OUTSIDE =
      GeneratorMapping.create("setupInterior" /* setup method */, "outputRecordValues" /* eval method */,
          "resetValues" /* reset */, "cleanup" /* cleanup */);

  private final MappingSet UpdateAggrValuesMapping =
      new MappingSet("incomingRowIdx" /* read index */, "outRowIdx" /* write index */,
          "htRowIdx" /* workspace index */, "incoming" /* read container */, "outgoing" /* write container */,
          "aggrValuesContainer" /* workspace container */, UPDATE_AGGR_INSIDE, UPDATE_AGGR_OUTSIDE, UPDATE_AGGR_INSIDE);


  public HashAggBatch(HashAggregate popConfig, RecordBatch incoming, FragmentContext context) throws ExecutionSetupException {
    super(popConfig, context);
    this.incoming = incoming;
  }

  @Override
  public int getRecordCount() {
    if (state == BatchState.DONE) {
      return 0;
    }
    return aggregator.getOutputCount();
  }

  @Override
  public void buildSchema() throws SchemaChangeException {
    IterOutcome outcome = next(incoming);
    switch (outcome) {
      case NONE:
        state = BatchState.DONE;
        container.buildSchema(SelectionVectorMode.NONE);
        return;
      case OUT_OF_MEMORY:
        state = BatchState.OUT_OF_MEMORY;
        return;
      case STOP:
        state = BatchState.STOP;
        return;
    }

    if (!createAggregator()) {
      state = BatchState.DONE;
    }
    for (VectorWrapper w : container) {
      AllocationHelper.allocatePrecomputedChildCount(w.getValueVector(), 0, 0, 0);
    }
  }

  @Override
  public IterOutcome innerNext() {

    if (aggregator.allFlushed()) {
      return IterOutcome.NONE;
    }

    if (aggregator.buildComplete() && !aggregator.allFlushed()) {
      // aggregation is complete and not all records have been output yet
      return aggregator.outputCurrentBatch();
    }

    logger.debug("Starting aggregator doWork; incoming record count = {} ", incoming.getRecordCount());

    AggOutcome out = aggregator.doWork();
    logger.debug("Aggregator response {}, records {}", out, aggregator.getOutputCount());
    switch (out) {
    case CLEANUP_AND_RETURN:
      container.zeroVectors();
      aggregator.cleanup();
      state = BatchState.DONE;
      // fall through
    case RETURN_OUTCOME:
      return aggregator.getOutcome();
    case UPDATE_AGGREGATOR:
      context.fail(UserException.unsupportedError()
        .message("Hash aggregate does not support schema changes").build());
      close();
      killIncoming(false);
      return IterOutcome.STOP;
    default:
      throw new IllegalStateException(String.format("Unknown state %s.", out));
    }
  }

  /**
   * Creates a new Aggregator based on the current schema. If setup fails, this method is responsible for cleaning up
   * and informing the context of the failure state, as well is informing the upstream operators.
   *
   * @return true if the aggregator was setup successfully. false if there was a failure.
   */
  private boolean createAggregator() {
    logger.debug("Creating new aggregator.");
    try {
      stats.startSetup();
      this.aggregator = createAggregatorInternal();
      return true;
    } catch (SchemaChangeException | ClassTransformationException | IOException ex) {
      context.fail(ex);
      container.clear();
      incoming.kill(false);
      return false;
    } finally {
      stats.stopSetup();
    }
  }

  private HashAggregator createAggregatorInternal() throws SchemaChangeException, ClassTransformationException,
      IOException {
    CodeGenerator<HashAggregator> top =
        CodeGenerator.get(HashAggregator.TEMPLATE_DEFINITION, context.getFunctionRegistry());
    ClassGenerator<HashAggregator> cg = top.getRoot();
    ClassGenerator<HashAggregator> cgInner = cg.getInnerGenerator("BatchHolder");

    container.clear();

    int numGroupByExprs = (popConfig.getGroupByExprs() != null) ? popConfig.getGroupByExprs().length : 0;
    int numAggrExprs = (popConfig.getAggrExprs() != null) ? popConfig.getAggrExprs().length : 0;
    aggrExprs = new LogicalExpression[numAggrExprs];
    groupByOutFieldIds = new TypedFieldId[numGroupByExprs];
    aggrOutFieldIds = new TypedFieldId[numAggrExprs];

    ErrorCollector collector = new ErrorCollectorImpl();

    int i;

    for (i = 0; i < numGroupByExprs; i++) {
      NamedExpression ne = popConfig.getGroupByExprs()[i];
      final LogicalExpression expr =
          ExpressionTreeMaterializer.materialize(ne.getExpr(), incoming, collector, context.getFunctionRegistry());
      if (expr == null) {
        continue;
      }

      final MaterializedField outputField = MaterializedField.create(ne.getRef(), expr.getMajorType());
      ValueVector vv = TypeHelper.getNewVector(outputField, oContext.getAllocator());

      // add this group-by vector to the output container
      groupByOutFieldIds[i] = container.add(vv);
    }

    for (i = 0; i < numAggrExprs; i++) {
      NamedExpression ne = popConfig.getAggrExprs()[i];
      final LogicalExpression expr =
          ExpressionTreeMaterializer.materialize(ne.getExpr(), incoming, collector, context.getFunctionRegistry());

      if (collector.hasErrors()) {
        throw new SchemaChangeException("Failure while materializing expression. " + collector.toErrorString());
      }

      if (expr == null) {
        continue;
      }

      final MaterializedField outputField = MaterializedField.create(ne.getRef(), expr.getMajorType());
      ValueVector vv = TypeHelper.getNewVector(outputField, oContext.getAllocator());
      aggrOutFieldIds[i] = container.add(vv);

      aggrExprs[i] = new ValueVectorWriteExpression(aggrOutFieldIds[i], expr, true);
    }

    setupUpdateAggrValues(cgInner);
    setupGetIndex(cg);
    cg.getBlock("resetValues")._return(JExpr.TRUE);

    container.buildSchema(SelectionVectorMode.NONE);
    HashAggregator agg = context.getImplementationClass(top);

    HashTableConfig htConfig =
        new HashTableConfig(context.getOptions().getOption(ExecConstants.MIN_HASH_TABLE_SIZE_KEY).num_val.intValue(),
            HashTable.DEFAULT_LOAD_FACTOR, popConfig.getGroupByExprs(), null /* no probe exprs */);

    agg.setup(popConfig, htConfig, context, this.stats,
        oContext.getAllocator(), incoming, this,
        aggrExprs,
        cgInner.getWorkspaceTypes(),
        groupByOutFieldIds,
        this.container);

    return agg;
  }

  private void setupUpdateAggrValues(ClassGenerator<HashAggregator> cg) {
    cg.setMappingSet(UpdateAggrValuesMapping);

    for (LogicalExpression aggr : aggrExprs) {
      HoldingContainer hc = cg.addExpr(aggr);
    }
  }

  private void setupGetIndex(ClassGenerator<HashAggregator> cg) {
    switch (incoming.getSchema().getSelectionVectorMode()) {
    case FOUR_BYTE: {
      JVar var = cg.declareClassField("sv4_", cg.getModel()._ref(SelectionVector4.class));
      cg.getBlock("doSetup").assign(var, JExpr.direct("incoming").invoke("getSelectionVector4"));
      cg.getBlock("getVectorIndex")._return(var.invoke("get").arg(JExpr.direct("recordIndex")));
      return;
    }
    case NONE: {
      cg.getBlock("getVectorIndex")._return(JExpr.direct("recordIndex"));
      return;
    }
    case TWO_BYTE: {
      JVar var = cg.declareClassField("sv2_", cg.getModel()._ref(SelectionVector2.class));
      cg.getBlock("doSetup").assign(var, JExpr.direct("incoming").invoke("getSelectionVector2"));
      cg.getBlock("getVectorIndex")._return(var.invoke("getIndex").arg(JExpr.direct("recordIndex")));
      return;
    }

    }

  }

  @Override
  public void close() {
    if (aggregator != null) {
      aggregator.cleanup();
    }
    super.close();
  }

  @Override
  protected void killIncoming(boolean sendUpstream) {
    incoming.kill(sendUpstream);
  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/physical/impl/aggregate/StreamingAggBatch.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.physical.impl.aggregate;

import java.io.IOException;

import org.apache.drill.common.exceptions.DrillRuntimeException;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.common.expression.ErrorCollector;
import org.apache.drill.common.expression.ErrorCollectorImpl;
import org.apache.drill.common.expression.LogicalExpression;
import org.apache.drill.common.logical.data.NamedExpression;
import org.apache.drill.common.types.TypeProtos;
import org.apache.drill.exec.compile.sig.GeneratorMapping;
import org.apache.drill.exec.compile.sig.MappingSet;
import org.apache.drill.exec.exception.ClassTransformationException;
import org.apache.drill.exec.exception.SchemaChangeException;
import org.apache.drill.exec.expr.ClassGenerator;
import org.apache.drill.exec.expr.ClassGenerator.HoldingContainer;
import org.apache.drill.exec.expr.CodeGenerator;
import org.apache.drill.exec.expr.ExpressionTreeMaterializer;
import org.apache.drill.exec.expr.HoldingContainerExpression;
import org.apache.drill.exec.expr.TypeHelper;
import org.apache.drill.exec.expr.ValueVectorWriteExpression;
import org.apache.drill.exec.expr.fn.FunctionGenerationHelper;
import org.apache.drill.exec.memory.OutOfMemoryException;
import org.apache.drill.exec.ops.FragmentContext;
import org.apache.drill.exec.physical.config.StreamingAggregate;
import org.apache.drill.exec.physical.impl.aggregate.StreamingAggregator.AggOutcome;
import org.apache.drill.exec.record.AbstractRecordBatch;
import org.apache.drill.exec.record.BatchSchema.SelectionVectorMode;
import org.apache.drill.exec.record.MaterializedField;
import org.apache.drill.exec.record.RecordBatch;
import org.apache.drill.exec.record.TypedFieldId;
import org.apache.drill.exec.record.VectorWrapper;
import org.apache.drill.exec.record.selection.SelectionVector2;
import org.apache.drill.exec.record.selection.SelectionVector4;
import org.apache.drill.exec.vector.AllocationHelper;
import org.apache.drill.exec.vector.FixedWidthVector;
import org.apache.drill.exec.vector.ValueVector;

import com.sun.codemodel.JExpr;
import com.sun.codemodel.JVar;

public class StreamingAggBatch extends AbstractRecordBatch<StreamingAggregate> {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(StreamingAggBatch.class);

  private StreamingAggregator aggregator;
  private final RecordBatch incoming;
  private boolean done = false;
  private boolean first = true;
  private int recordCount = 0;

  /*
   * DRILL-2277, DRILL-2411: For straight aggregates without a group by clause we need to perform special handling when
   * the incoming batch is empty. In the case of the empty input into the streaming aggregate we need
   * to return a single batch with one row. For count we need to return 0 and for all other aggregate
   * functions like sum, avg etc we need to return an explicit row with NULL. Since we correctly allocate the type of
   * the outgoing vectors (required for count and nullable for other aggregate functions) all we really need to do
   * is simply set the record count to be 1 in such cases. For nullable vectors we don't need to do anything because
   * if we don't set anything the output will be NULL, however for required vectors we explicitly zero out the vector
   * since we don't zero it out while allocating it.
   *
   * We maintain some state to remember that we have done such special handling.
   */
  private boolean specialBatchSent = false;
  private static final int SPECIAL_BATCH_COUNT = 1;

  public StreamingAggBatch(StreamingAggregate popConfig, RecordBatch incoming, FragmentContext context) throws OutOfMemoryException {
    super(popConfig, context);
    this.incoming = incoming;
  }

  @Override
  public int getRecordCount() {
    if (done || aggregator == null) {
      return 0;
    }
    return recordCount;
  }

  @Override
  public void buildSchema() throws SchemaChangeException {
    IterOutcome outcome = next(incoming);
    switch (outcome) {
      case NONE:
        state = BatchState.DONE;
        container.buildSchema(SelectionVectorMode.NONE);
        return;
      case OUT_OF_MEMORY:
        state = BatchState.OUT_OF_MEMORY;
        return;
      case STOP:
        state = BatchState.STOP;
        return;
    }

    if (!createAggregator()) {
      state = BatchState.DONE;
    }
    for (VectorWrapper w : container) {
      w.getValueVector().allocateNew();
    }
  }

  @Override
  public IterOutcome innerNext() {

    // if a special batch has been sent, we have no data in the incoming so exit early
    if (specialBatchSent) {
      return IterOutcome.NONE;
    }

    // this is only called on the first batch. Beyond this, the aggregator manages batches.
    if (aggregator == null || first) {
      IterOutcome outcome;
      if (first && incoming.getRecordCount() > 0) {
        first = false;
        outcome = IterOutcome.OK_NEW_SCHEMA;
      } else {
        outcome = next(incoming);
      }
      logger.debug("Next outcome of {}", outcome);
      switch (outcome) {
      case NONE:
        if (first && popConfig.getKeys().length == 0) {
          // if we have a straight aggregate and empty input batch, we need to handle it in a different way
          constructSpecialBatch();
          first = false;
          // set state to indicate the fact that we have sent a special batch and input is empty
          specialBatchSent = true;
          return IterOutcome.OK;
        }
      case OUT_OF_MEMORY:
      case NOT_YET:
      case STOP:
        return outcome;
      case OK_NEW_SCHEMA:
        if (!createAggregator()) {
          done = true;
          return IterOutcome.STOP;
        }
        break;
      case OK:
        break;
      default:
        throw new IllegalStateException(String.format("unknown outcome %s", outcome));
      }
    }

    AggOutcome out = aggregator.doWork();
    recordCount = aggregator.getOutputCount();
    logger.debug("Aggregator response {}, records {}", out, aggregator.getOutputCount());
    switch (out) {
    case CLEANUP_AND_RETURN:
      if (!first) {
        container.zeroVectors();
      }
      done = true;
      // fall through
    case RETURN_OUTCOME:
      IterOutcome outcome = aggregator.getOutcome();
      if (outcome == IterOutcome.NONE && first) {
        first = false;
        done = true;
        return IterOutcome.OK_NEW_SCHEMA;
      } else if (outcome == IterOutcome.OK && first) {
        outcome = IterOutcome.OK_NEW_SCHEMA;
      } else if (outcome != IterOutcome.OUT_OF_MEMORY) {
        first = false;
      }
      return outcome;
    case UPDATE_AGGREGATOR:
      context.fail(UserException.unsupportedError()
        .message("Streaming aggregate does not support schema changes")
        .build());
      close();
      killIncoming(false);
      return IterOutcome.STOP;
    default:
      throw new IllegalStateException(String.format("Unknown state %s.", out));
    }
  }


  /**
   * Method is invoked when we have a straight aggregate (no group by expression) and our input is empty.
   * In this case we construct an outgoing batch with record count as 1. For the nullable vectors we don't set anything
   * as we want the output to be NULL. For the required vectors (only for count()) we set the value to be zero since
   * we don't zero out our buffers initially while allocating them.
   */
  private void constructSpecialBatch() {
    int exprIndex = 0;
    for (VectorWrapper vw: container) {
      ValueVector vv = vw.getValueVector();
      AllocationHelper.allocateNew(vv, SPECIAL_BATCH_COUNT);
      vv.getMutator().setValueCount(SPECIAL_BATCH_COUNT);
      if (vv.getField().getType().getMode() == TypeProtos.DataMode.REQUIRED) {
        if (vv instanceof FixedWidthVector) {
          /*
           * The only case we should have a required vector in the aggregate is for count function whose output is
           * always a FixedWidthVector (BigIntVector). Zero out the vector.
           */
          ((FixedWidthVector) vv).zeroVector();
        } else {
          /*
           * If we are in this else block it means that we have a required vector which is of variable length. We
           * should not be here, raising an error since we have set the record count to be 1 and not cleared the
           * buffer
           */
          throw new DrillRuntimeException("FixedWidth vectors is the expected output vector type. " +
              "Corresponding expression: " + popConfig.getExprs()[exprIndex].toString());
        }
      }
      exprIndex++;
    }
    container.setRecordCount(SPECIAL_BATCH_COUNT);
    recordCount = SPECIAL_BATCH_COUNT;
  }

  /**
   * Creates a new Aggregator based on the current schema. If setup fails, this method is responsible for cleaning up
   * and informing the context of the failure state, as well is informing the upstream operators.
   *
   * @return true if the aggregator was setup successfully. false if there was a failure.
   */
  private boolean createAggregator() {
    logger.debug("Creating new aggregator.");
    try {
      stats.startSetup();
      this.aggregator = createAggregatorInternal();
      return true;
    } catch (SchemaChangeException | ClassTransformationException | IOException ex) {
      context.fail(ex);
      container.clear();
      incoming.kill(false);
      return false;
    } finally {
      stats.stopSetup();
    }
  }

  private StreamingAggregator createAggregatorInternal() throws SchemaChangeException, ClassTransformationException, IOException{
    ClassGenerator<StreamingAggregator> cg = CodeGenerator.getRoot(StreamingAggTemplate.TEMPLATE_DEFINITION, context.getFunctionRegistry());
    container.clear();

    LogicalExpression[] keyExprs = new LogicalExpression[popConfig.getKeys().length];
    LogicalExpression[] valueExprs = new LogicalExpression[popConfig.getExprs().length];
    TypedFieldId[] keyOutputIds = new TypedFieldId[popConfig.getKeys().length];

    ErrorCollector collector = new ErrorCollectorImpl();

    for (int i =0; i < keyExprs.length; i++) {
      NamedExpression ne = popConfig.getKeys()[i];
      final LogicalExpression expr = ExpressionTreeMaterializer.materialize(ne.getExpr(), incoming, collector,context.getFunctionRegistry() );
      if (expr == null) {
        continue;
      }
      keyExprs[i] = expr;
      final MaterializedField outputField = MaterializedField.create(ne.getRef(), expr.getMajorType());
      ValueVector vector = TypeHelper.getNewVector(outputField, oContext.getAllocator());
      keyOutputIds[i] = container.add(vector);
    }

    for (int i =0; i < valueExprs.length; i++) {
      NamedExpression ne = popConfig.getExprs()[i];
      final LogicalExpression expr = ExpressionTreeMaterializer.materialize(ne.getExpr(), incoming, collector, context.getFunctionRegistry());
      if (expr == null) {
        continue;
      }

      final MaterializedField outputField = MaterializedField.create(ne.getRef(), expr.getMajorType());
      ValueVector vector = TypeHelper.getNewVector(outputField, oContext.getAllocator());
      TypedFieldId id = container.add(vector);
      valueExprs[i] = new ValueVectorWriteExpression(id, expr, true);
    }

    if (collector.hasErrors()) {
      throw new SchemaChangeException("Failure while materializing expression. " + collector.toErrorString());
    }

    setupIsSame(cg, keyExprs);
    setupIsSameApart(cg, keyExprs);
    addRecordValues(cg, valueExprs);
    outputRecordKeys(cg, keyOutputIds, keyExprs);
    outputRecordKeysPrev(cg, keyOutputIds, keyExprs);

    cg.getBlock("resetValues")._return(JExpr.TRUE);
    getIndex(cg);

    container.buildSchema(SelectionVectorMode.NONE);
    StreamingAggregator agg = context.getImplementationClass(cg);
    agg.setup(context, incoming, this);
    return agg;
  }

  private final GeneratorMapping IS_SAME = GeneratorMapping.create("setupInterior", "isSame", null, null);
  private final MappingSet IS_SAME_I1 = new MappingSet("index1", null, IS_SAME, IS_SAME);
  private final MappingSet IS_SAME_I2 = new MappingSet("index2", null, IS_SAME, IS_SAME);

  private void setupIsSame(ClassGenerator<StreamingAggregator> cg, LogicalExpression[] keyExprs) {
    cg.setMappingSet(IS_SAME_I1);
    for (LogicalExpression expr : keyExprs) {
      // first, we rewrite the evaluation stack for each side of the comparison.
      cg.setMappingSet(IS_SAME_I1);
      HoldingContainer first = cg.addExpr(expr, false);
      cg.setMappingSet(IS_SAME_I2);
      HoldingContainer second = cg.addExpr(expr, false);

      LogicalExpression fh =
          FunctionGenerationHelper
          .getOrderingComparatorNullsHigh(first, second, context.getFunctionRegistry());
      HoldingContainer out = cg.addExpr(fh, false);
      cg.getEvalBlock()._if(out.getValue().ne(JExpr.lit(0)))._then()._return(JExpr.FALSE);
    }
    cg.getEvalBlock()._return(JExpr.TRUE);
  }

  private final GeneratorMapping IS_SAME_PREV_INTERNAL_BATCH_READ = GeneratorMapping.create("isSamePrev", "isSamePrev", null, null); // the internal batch changes each time so we need to redo setup.
  private final GeneratorMapping IS_SAME_PREV = GeneratorMapping.create("setupInterior", "isSamePrev", null, null);
  private final MappingSet ISA_B1 = new MappingSet("b1Index", null, "b1", null, IS_SAME_PREV_INTERNAL_BATCH_READ, IS_SAME_PREV_INTERNAL_BATCH_READ);
  private final MappingSet ISA_B2 = new MappingSet("b2Index", null, "incoming", null, IS_SAME_PREV, IS_SAME_PREV);

  private void setupIsSameApart(ClassGenerator<StreamingAggregator> cg, LogicalExpression[] keyExprs) {
    cg.setMappingSet(ISA_B1);
    for (LogicalExpression expr : keyExprs) {
      // first, we rewrite the evaluation stack for each side of the comparison.
      cg.setMappingSet(ISA_B1);
      HoldingContainer first = cg.addExpr(expr, false);
      cg.setMappingSet(ISA_B2);
      HoldingContainer second = cg.addExpr(expr, false);

      LogicalExpression fh =
          FunctionGenerationHelper
          .getOrderingComparatorNullsHigh(first, second, context.getFunctionRegistry());
      HoldingContainer out = cg.addExpr(fh, false);
      cg.getEvalBlock()._if(out.getValue().ne(JExpr.lit(0)))._then()._return(JExpr.FALSE);
    }
    cg.getEvalBlock()._return(JExpr.TRUE);
  }

  private final GeneratorMapping EVAL_INSIDE = GeneratorMapping.create("setupInterior", "addRecord", null, null);
  private final GeneratorMapping EVAL_OUTSIDE = GeneratorMapping.create("setupInterior", "outputRecordValues", "resetValues", "cleanup");
  private final MappingSet EVAL = new MappingSet("index", "outIndex", "incoming", "outgoing", EVAL_INSIDE, EVAL_OUTSIDE, EVAL_INSIDE);

  private void addRecordValues(ClassGenerator<StreamingAggregator> cg, LogicalExpression[] valueExprs) {
    cg.setMappingSet(EVAL);
    for (LogicalExpression ex : valueExprs) {
      HoldingContainer hc = cg.addExpr(ex);
    }
  }

  private final MappingSet RECORD_KEYS = new MappingSet(GeneratorMapping.create("setupInterior", "outputRecordKeys", null, null));

  private void outputRecordKeys(ClassGenerator<StreamingAggregator> cg, TypedFieldId[] keyOutputIds, LogicalExpression[] keyExprs) {
    cg.setMappingSet(RECORD_KEYS);
    for (int i =0; i < keyExprs.length; i++) {
      HoldingContainer hc = cg.addExpr(new ValueVectorWriteExpression(keyOutputIds[i], keyExprs[i], true));
    }
  }

  private final GeneratorMapping PREVIOUS_KEYS_OUT = GeneratorMapping.create("setupInterior", "outputRecordKeysPrev", null, null);
  private final MappingSet RECORD_KEYS_PREV_OUT = new MappingSet("previousIndex", "outIndex", "previous", "outgoing", PREVIOUS_KEYS_OUT, PREVIOUS_KEYS_OUT);

  private final GeneratorMapping PREVIOUS_KEYS = GeneratorMapping.create("outputRecordKeysPrev", "outputRecordKeysPrev", null, null);
  private final MappingSet RECORD_KEYS_PREV = new MappingSet("previousIndex", "outIndex", "previous", null, PREVIOUS_KEYS, PREVIOUS_KEYS);

  private void outputRecordKeysPrev(ClassGenerator<StreamingAggregator> cg, TypedFieldId[] keyOutputIds, LogicalExpression[] keyExprs) {
    cg.setMappingSet(RECORD_KEYS_PREV);

    for (int i =0; i < keyExprs.length; i++) {
      // IMPORTANT: there is an implicit assertion here that the TypedFieldIds for the previous batch and the current batch are the same.  This is possible because InternalBatch guarantees this.
      logger.debug("Writing out expr {}", keyExprs[i]);
      cg.rotateBlock();
      cg.setMappingSet(RECORD_KEYS_PREV);
      HoldingContainer innerExpression = cg.addExpr(keyExprs[i], false);
      cg.setMappingSet(RECORD_KEYS_PREV_OUT);
      HoldingContainer outerExpression = cg.addExpr(new ValueVectorWriteExpression(keyOutputIds[i], new HoldingContainerExpression(innerExpression), true), false);

    }
  }

  private void getIndex(ClassGenerator<StreamingAggregator> g) {
    switch (incoming.getSchema().getSelectionVectorMode()) {
    case FOUR_BYTE: {
      JVar var = g.declareClassField("sv4_", g.getModel()._ref(SelectionVector4.class));
      g.getBlock("setupInterior").assign(var, JExpr.direct("incoming").invoke("getSelectionVector4"));
      g.getBlock("getVectorIndex")._return(var.invoke("get").arg(JExpr.direct("recordIndex")));;
      return;
    }
    case NONE: {
      g.getBlock("getVectorIndex")._return(JExpr.direct("recordIndex"));;
      return;
    }
    case TWO_BYTE: {
      JVar var = g.declareClassField("sv2_", g.getModel()._ref(SelectionVector2.class));
      g.getBlock("setupInterior").assign(var, JExpr.direct("incoming").invoke("getSelectionVector2"));
      g.getBlock("getVectorIndex")._return(var.invoke("getIndex").arg(JExpr.direct("recordIndex")));;
      return;
    }

    default:
      throw new IllegalStateException();
    }
  }

  @Override
  public void close() {
    super.close();
  }

  @Override
  protected void killIncoming(boolean sendUpstream) {
    incoming.kill(sendUpstream);
  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/physical/impl/flatten/FlattenRecordBatch.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.physical.impl.flatten;

import java.io.IOException;
import java.util.List;

import com.carrotsearch.hppc.IntOpenHashSet;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.common.expression.ErrorCollector;
import org.apache.drill.common.expression.ErrorCollectorImpl;
import org.apache.drill.common.expression.FieldReference;
import org.apache.drill.common.expression.LogicalExpression;
import org.apache.drill.common.expression.PathSegment;
import org.apache.drill.common.logical.data.NamedExpression;
import org.apache.drill.exec.exception.ClassTransformationException;
import org.apache.drill.exec.exception.SchemaChangeException;
import org.apache.drill.exec.expr.ClassGenerator;
import org.apache.drill.exec.expr.ClassGenerator.HoldingContainer;
import org.apache.drill.exec.expr.CodeGenerator;
import org.apache.drill.exec.expr.DrillFuncHolderExpr;
import org.apache.drill.exec.expr.ExpressionTreeMaterializer;
import org.apache.drill.exec.expr.TypeHelper;
import org.apache.drill.exec.expr.ValueVectorReadExpression;
import org.apache.drill.exec.expr.ValueVectorWriteExpression;
import org.apache.drill.exec.expr.fn.DrillComplexWriterFuncHolder;
import org.apache.drill.exec.memory.OutOfMemoryException;
import org.apache.drill.exec.ops.FragmentContext;
import org.apache.drill.exec.physical.config.FlattenPOP;
import org.apache.drill.exec.record.AbstractSingleRecordBatch;
import org.apache.drill.exec.record.BatchSchema.SelectionVectorMode;
import org.apache.drill.exec.record.MaterializedField;
import org.apache.drill.exec.record.RecordBatch;
import org.apache.drill.exec.record.TransferPair;
import org.apache.drill.exec.record.TypedFieldId;
import org.apache.drill.exec.record.VectorContainer;
import org.apache.drill.exec.record.VectorWrapper;
import org.apache.drill.exec.vector.complex.RepeatedValueVector;
import org.apache.drill.exec.vector.ValueVector;
import org.apache.drill.exec.vector.complex.RepeatedMapVector;
import org.apache.drill.exec.vector.complex.writer.BaseWriter.ComplexWriter;

import com.google.common.collect.Lists;
import com.sun.codemodel.JExpr;

// TODO - handle the case where a user tries to flatten a scalar, should just act as a project all of the columns exactly
// as they come in
public class FlattenRecordBatch extends AbstractSingleRecordBatch<FlattenPOP> {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(FlattenRecordBatch.class);

  private Flattener flattener;
  private List<ValueVector> allocationVectors;
  private List<ComplexWriter> complexWriters;
  private boolean hasRemainder = false;
  private int remainderIndex = 0;
  private int recordCount;
  // the buildSchema method is always called first by a short circuit path to return schema information to the client
  // this information is not entirely accurate as Drill determines schema on the fly, so here it needs to have modified
  // behavior for that call to setup the schema for the flatten operation
  private boolean fastSchemaCalled;

  private static final String EMPTY_STRING = "";

  private class ClassifierResult {
    public boolean isStar = false;
    public List<String> outputNames;
    public String prefix = "";

    private void clear() {
      isStar = false;
      prefix = "";
      if (outputNames != null) {
        outputNames.clear();
      }

      // note:  don't clear the internal maps since they have cumulative data..
    }
  }

  public FlattenRecordBatch(FlattenPOP pop, RecordBatch incoming, FragmentContext context) throws OutOfMemoryException {
    super(pop, context, incoming);
    fastSchemaCalled = false;
  }

  @Override
  public int getRecordCount() {
    return recordCount;
  }


  @Override
  protected void killIncoming(boolean sendUpstream) {
    super.killIncoming(sendUpstream);
    hasRemainder = false;
  }


  @Override
  public IterOutcome innerNext() {
    if (hasRemainder) {
      handleRemainder();
      return IterOutcome.OK;
    }
    return super.innerNext();
  }

  @Override
  public VectorContainer getOutgoingContainer() {
    return this.container;
  }

  private void setFlattenVector() {
    try {
      final TypedFieldId typedFieldId = incoming.getValueVectorId(popConfig.getColumn());
      final MaterializedField field = incoming.getSchema().getColumn(typedFieldId.getFieldIds()[0]);
      final RepeatedValueVector vector = RepeatedValueVector.class.cast(incoming.getValueAccessorById(
          field.getValueClass(), typedFieldId.getFieldIds()).getValueVector());
      flattener.setFlattenField(vector);
    } catch (Exception ex) {
      throw UserException.unsupportedError(ex).message("Trying to flatten a non-repeated field.").build();
    }
  }

  @Override
  protected IterOutcome doWork() {
    int incomingRecordCount = incoming.getRecordCount();

    if (!doAlloc()) {
      outOfMemory = true;
      return IterOutcome.OUT_OF_MEMORY;
    }

    // we call this in setupSchema, but we also need to call it here so we have a reference to the appropriate vector
    // inside of the the flattener for the current batch
    setFlattenVector();

    int childCount = incomingRecordCount == 0 ? 0 : flattener.getFlattenField().getAccessor().getInnerValueCount();
    int outputRecords = flattener.flattenRecords(0, incomingRecordCount, 0);
    // TODO - change this to be based on the repeated vector length
    if (outputRecords < childCount) {
      setValueCount(outputRecords);
      hasRemainder = true;
      remainderIndex = outputRecords;
      this.recordCount = remainderIndex;
    } else {
      setValueCount(outputRecords);
      flattener.resetGroupIndex();
      for(VectorWrapper<?> v: incoming) {
        v.clear();
      }
      this.recordCount = outputRecords;
    }
    // In case of complex writer expression, vectors would be added to batch run-time.
    // We have to re-build the schema.
    if (complexWriters != null) {
      container.buildSchema(SelectionVectorMode.NONE);
    }

    return IterOutcome.OK;
  }

  private void handleRemainder() {
    int remainingRecordCount = flattener.getFlattenField().getAccessor().getInnerValueCount() - remainderIndex;
    if (!doAlloc()) {
      outOfMemory = true;
      return;
    }

    int projRecords = flattener.flattenRecords(remainderIndex, remainingRecordCount, 0);
    if (projRecords < remainingRecordCount) {
      setValueCount(projRecords);
      this.recordCount = projRecords;
      remainderIndex += projRecords;
    } else {
      setValueCount(remainingRecordCount);
      hasRemainder = false;
      remainderIndex = 0;
      for (VectorWrapper<?> v : incoming) {
        v.clear();
      }
      flattener.resetGroupIndex();
      this.recordCount = remainingRecordCount;
    }
    // In case of complex writer expression, vectors would be added to batch run-time.
    // We have to re-build the schema.
    if (complexWriters != null) {
      container.buildSchema(SelectionVectorMode.NONE);
    }
  }

  public void addComplexWriter(ComplexWriter writer) {
    complexWriters.add(writer);
  }

  private boolean doAlloc() {
    //Allocate vv in the allocationVectors.
    for (ValueVector v : this.allocationVectors) {
      if (!v.allocateNewSafe()) {
        return false;
      }
    }

    //Allocate vv for complexWriters.
    if (complexWriters == null) {
      return true;
    }

    for (ComplexWriter writer : complexWriters) {
      writer.allocate();
    }

    return true;
  }

  private void setValueCount(int count) {
    for (ValueVector v : allocationVectors) {
      ValueVector.Mutator m = v.getMutator();
      m.setValueCount(count);
    }

    if (complexWriters == null) {
      return;
    }

    for (ComplexWriter writer : complexWriters) {
      writer.setValueCount(count);
    }
  }

  private FieldReference getRef(NamedExpression e) {
    FieldReference ref = e.getRef();
    PathSegment seg = ref.getRootSegment();

    return ref;
  }

  /**
   * The data layout is the same for the actual data within a repeated field, as it is in a scalar vector for
   * the same sql type. For example, a repeated int vector has a vector of offsets into a regular int vector to
   * represent the lists. As the data layout for the actual values in the same in the repeated vector as in the
   * scalar vector of the same type, we can avoid making individual copies for the column being flattened, and just
   * use vector copies between the inner vector of the repeated field to the resulting scalar vector from the flatten
   * operation. This is completed after we determine how many records will fit (as we will hit either a batch end, or
   * the end of one of the other vectors while we are copying the data of the other vectors alongside each new flattened
   * value coming out of the repeated field.)
   */
  private TransferPair getFlattenFieldTransferPair(FieldReference reference) {
    final TypedFieldId fieldId = incoming.getValueVectorId(popConfig.getColumn());
    final Class vectorClass = incoming.getSchema().getColumn(fieldId.getFieldIds()[0]).getValueClass();
    final ValueVector flattenField = incoming.getValueAccessorById(vectorClass, fieldId.getFieldIds()).getValueVector();

    TransferPair tp = null;
    if (flattenField instanceof RepeatedMapVector) {
      tp = ((RepeatedMapVector)flattenField).getTransferPairToSingleMap(reference);
    } else {
      final ValueVector vvIn = RepeatedValueVector.class.cast(flattenField).getDataVector();
      // vvIn may be null because of fast schema return for repeated list vectors
      if (vvIn != null) {
        tp = vvIn.getTransferPair(reference);
      }
    }
    return tp;
  }

  @Override
  protected boolean setupNewSchema() throws SchemaChangeException {
    this.allocationVectors = Lists.newArrayList();
    container.clear();
    final List<NamedExpression> exprs = getExpressionList();
    final ErrorCollector collector = new ErrorCollectorImpl();
    final List<TransferPair> transfers = Lists.newArrayList();

    final ClassGenerator<Flattener> cg = CodeGenerator.getRoot(Flattener.TEMPLATE_DEFINITION, context.getFunctionRegistry());
    final IntOpenHashSet transferFieldIds = new IntOpenHashSet();

    final NamedExpression flattenExpr = new NamedExpression(popConfig.getColumn(), new FieldReference(popConfig.getColumn()));
    final ValueVectorReadExpression vectorRead = (ValueVectorReadExpression)ExpressionTreeMaterializer.materialize(flattenExpr.getExpr(), incoming, collector, context.getFunctionRegistry(), true);
    final TransferPair tp = getFlattenFieldTransferPair(flattenExpr.getRef());

    if (tp != null) {
      transfers.add(tp);
      container.add(tp.getTo());
      transferFieldIds.add(vectorRead.getFieldId().getFieldIds()[0]);
    }

    logger.debug("Added transfer for project expression.");

    ClassifierResult result = new ClassifierResult();

    for (int i = 0; i < exprs.size(); i++) {
      final NamedExpression namedExpression = exprs.get(i);
      result.clear();

      String outputName = getRef(namedExpression).getRootSegment().getPath();
      if (result != null && result.outputNames != null && result.outputNames.size() > 0) {
        for (int j = 0; j < result.outputNames.size(); j++) {
          if (!result.outputNames.get(j).equals(EMPTY_STRING)) {
            outputName = result.outputNames.get(j);
            break;
          }
        }
      }

      final LogicalExpression expr = ExpressionTreeMaterializer.materialize(namedExpression.getExpr(), incoming, collector, context.getFunctionRegistry(), true);
      final MaterializedField outputField = MaterializedField.create(outputName, expr.getMajorType());
      if (collector.hasErrors()) {
        throw new SchemaChangeException(String.format("Failure while trying to materialize incoming schema.  Errors:\n %s.", collector.toErrorString()));
      }
      if (expr instanceof DrillFuncHolderExpr &&
          ((DrillFuncHolderExpr) expr).isComplexWriterFuncHolder())  {
        // Need to process ComplexWriter function evaluation.
        // Lazy initialization of the list of complex writers, if not done yet.
        if (complexWriters == null) {
          complexWriters = Lists.newArrayList();
        }

        // The reference name will be passed to ComplexWriter, used as the name of the output vector from the writer.
        ((DrillComplexWriterFuncHolder) ((DrillFuncHolderExpr) expr).getHolder()).setReference(namedExpression.getRef());
        cg.addExpr(expr);
      } else{
        // need to do evaluation.
        ValueVector vector = TypeHelper.getNewVector(outputField, oContext.getAllocator());
        allocationVectors.add(vector);
        TypedFieldId fid = container.add(vector);
        ValueVectorWriteExpression write = new ValueVectorWriteExpression(fid, expr, true);
        HoldingContainer hc = cg.addExpr(write);

        logger.debug("Added eval for project expression.");
      }
    }

    cg.rotateBlock();
    cg.getEvalBlock()._return(JExpr.TRUE);

    container.buildSchema(SelectionVectorMode.NONE);

    try {
      this.flattener = context.getImplementationClass(cg.getCodeGenerator());
      flattener.setup(context, incoming, this, transfers);
    } catch (ClassTransformationException | IOException e) {
      throw new SchemaChangeException("Failure while attempting to load generated class", e);
    }
    return true;
  }

  private List<NamedExpression> getExpressionList() {

    List<NamedExpression> exprs = Lists.newArrayList();
    for (MaterializedField field : incoming.getSchema()) {
      if (field.getPath().equals(popConfig.getColumn())) {
        continue;
      }
      exprs.add(new NamedExpression(field.getPath(), new FieldReference(field.getPath())));
    }
    return exprs;
  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/physical/impl/xsort/ExternalSortBatch.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.physical.impl.xsort;

import io.netty.buffer.DrillBuf;

import java.io.IOException;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;
import java.util.concurrent.TimeUnit;

import org.apache.drill.common.config.DrillConfig;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.common.expression.ErrorCollector;
import org.apache.drill.common.expression.ErrorCollectorImpl;
import org.apache.drill.common.expression.LogicalExpression;
import org.apache.drill.common.logical.data.Order.Ordering;
import org.apache.drill.exec.ExecConstants;
import org.apache.drill.exec.compile.sig.GeneratorMapping;
import org.apache.drill.exec.compile.sig.MappingSet;
import org.apache.drill.exec.exception.ClassTransformationException;
import org.apache.drill.exec.exception.SchemaChangeException;
import org.apache.drill.exec.expr.ClassGenerator;
import org.apache.drill.exec.expr.ClassGenerator.HoldingContainer;
import org.apache.drill.exec.expr.CodeGenerator;
import org.apache.drill.exec.expr.ExpressionTreeMaterializer;
import org.apache.drill.exec.expr.TypeHelper;
import org.apache.drill.exec.expr.fn.FunctionGenerationHelper;
import org.apache.drill.exec.memory.BufferAllocator;
import org.apache.drill.exec.memory.OutOfMemoryException;
import org.apache.drill.exec.memory.OutOfMemoryRuntimeException;
import org.apache.drill.exec.ops.FragmentContext;
import org.apache.drill.exec.physical.config.ExternalSort;
import org.apache.drill.exec.physical.impl.sort.RecordBatchData;
import org.apache.drill.exec.physical.impl.sort.SortRecordBatchBuilder;
import org.apache.drill.exec.proto.ExecProtos.FragmentHandle;
import org.apache.drill.exec.proto.helper.QueryIdHelper;
import org.apache.drill.exec.record.AbstractRecordBatch;
import org.apache.drill.exec.record.BatchSchema;
import org.apache.drill.exec.record.BatchSchema.SelectionVectorMode;
import org.apache.drill.exec.record.MaterializedField;
import org.apache.drill.exec.record.RecordBatch;
import org.apache.drill.exec.record.VectorAccessible;
import org.apache.drill.exec.record.VectorContainer;
import org.apache.drill.exec.record.VectorWrapper;
import org.apache.drill.exec.record.WritableBatch;
import org.apache.drill.exec.record.selection.SelectionVector2;
import org.apache.drill.exec.record.selection.SelectionVector4;
import org.apache.drill.exec.testing.ControlsInjector;
import org.apache.drill.exec.testing.ControlsInjectorFactory;
import org.apache.drill.exec.vector.CopyUtil;
import org.apache.drill.exec.vector.ValueVector;
import org.apache.drill.exec.vector.complex.AbstractContainerVector;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.FileSystem;
import org.apache.calcite.rel.RelFieldCollation.Direction;

import com.google.common.base.Joiner;
import com.google.common.base.Stopwatch;
import com.google.common.collect.Iterators;
import com.google.common.collect.Lists;
import com.sun.codemodel.JConditional;
import com.sun.codemodel.JExpr;

public class ExternalSortBatch extends AbstractRecordBatch<ExternalSort> {
  private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(ExternalSortBatch.class);
  private static final ControlsInjector injector = ControlsInjectorFactory.getInjector(ExternalSortBatch.class);

  private static final long MAX_SORT_BYTES = 1L * 1024 * 1024 * 1024;
  private static final GeneratorMapping COPIER_MAPPING = new GeneratorMapping("doSetup", "doCopy", null, null);
  private static final MappingSet MAIN_MAPPING = new MappingSet( (String) null, null, ClassGenerator.DEFAULT_SCALAR_MAP, ClassGenerator.DEFAULT_SCALAR_MAP);
  private static final MappingSet LEFT_MAPPING = new MappingSet("leftIndex", null, ClassGenerator.DEFAULT_SCALAR_MAP, ClassGenerator.DEFAULT_SCALAR_MAP);
  private static final MappingSet RIGHT_MAPPING = new MappingSet("rightIndex", null, ClassGenerator.DEFAULT_SCALAR_MAP, ClassGenerator.DEFAULT_SCALAR_MAP);
  private static final MappingSet COPIER_MAPPING_SET = new MappingSet(COPIER_MAPPING, COPIER_MAPPING);

  private final int SPILL_BATCH_GROUP_SIZE;
  private final int SPILL_THRESHOLD;
  private final List<String> SPILL_DIRECTORIES;
  private final Iterator<String> dirs;
  private final RecordBatch incoming;
  private final BufferAllocator copierAllocator;

  private BatchSchema schema;
  private SingleBatchSorter sorter;
  private SortRecordBatchBuilder builder;
  private MSorter mSorter;
  private PriorityQueueCopier copier;
  private LinkedList<BatchGroup> batchGroups = Lists.newLinkedList();
  private LinkedList<BatchGroup> spilledBatchGroups = Lists.newLinkedList();
  private SelectionVector4 sv4;
  private FileSystem fs;
  private int spillCount = 0;
  private int batchesSinceLastSpill = 0;
  private boolean first = true;
  private long totalSizeInMemory = 0;
  private long highWaterMark = Long.MAX_VALUE;
  private int targetRecordCount;
  private final String fileName;
  private int firstSpillBatchCount = 0;

  public static final String INTERRUPTION_AFTER_SORT = "after-sort";
  public static final String INTERRUPTION_AFTER_SETUP = "after-setup";


  public ExternalSortBatch(ExternalSort popConfig, FragmentContext context, RecordBatch incoming) throws OutOfMemoryException {
    super(popConfig, context, true);
    this.incoming = incoming;
    DrillConfig config = context.getConfig();
    Configuration conf = new Configuration();
    conf.set("fs.default.name", config.getString(ExecConstants.EXTERNAL_SORT_SPILL_FILESYSTEM));
    try {
      this.fs = FileSystem.get(conf);
    } catch (IOException e) {
      throw new RuntimeException(e);
    }
    SPILL_BATCH_GROUP_SIZE = config.getInt(ExecConstants.EXTERNAL_SORT_SPILL_GROUP_SIZE);
    SPILL_THRESHOLD = config.getInt(ExecConstants.EXTERNAL_SORT_SPILL_THRESHOLD);
    SPILL_DIRECTORIES = config.getStringList(ExecConstants.EXTERNAL_SORT_SPILL_DIRS);
    dirs = Iterators.cycle(Lists.newArrayList(SPILL_DIRECTORIES));
    copierAllocator = oContext.getAllocator().getChildAllocator(
        context, PriorityQueueCopier.initialAllocation, PriorityQueueCopier.maxAllocation, true);
    FragmentHandle handle = context.getHandle();
    fileName = String.format("%s/major_fragment_%s/minor_fragment_%s/operator_%s", QueryIdHelper.getQueryId(handle.getQueryId()),
        handle.getMajorFragmentId(), handle.getMinorFragmentId(), popConfig.getOperatorId());
  }

  @Override
  public int getRecordCount() {
    if (sv4 != null) {
      return sv4.getCount();
    }
    return container.getRecordCount();
  }

  @Override
  public SelectionVector4 getSelectionVector4() {
    return sv4;
  }

  @Override
  public void close() {
    try {
      if (batchGroups != null) {
        for (BatchGroup group: batchGroups) {
          try {
            group.cleanup();
          } catch (IOException e) {
            throw new RuntimeException(e);
          }
        }
      }
    } finally {
      if (builder != null) {
        builder.clear();
        builder.close();
      }
      if (sv4 != null) {
        sv4.clear();
      }
      if (copier != null) {
        copier.cleanup();
      }
      copierAllocator.close();
      super.close();

      if(mSorter != null) {
        mSorter.clear();
      }
    }
  }

  @Override
  public void buildSchema() throws SchemaChangeException {
    IterOutcome outcome = next(incoming);
    switch (outcome) {
      case OK:
      case OK_NEW_SCHEMA:
        for (VectorWrapper w : incoming) {
          ValueVector v = container.addOrGet(w.getField());
          if (v instanceof AbstractContainerVector) {
            w.getValueVector().makeTransferPair(v); // Can we remove this hack?
            v.clear();
          }
          v.allocateNew(); // Can we remove this? - SVR fails with NPE (TODO)
        }
        container.buildSchema(SelectionVectorMode.NONE);
        container.setRecordCount(0);
        break;
      case STOP:
        state = BatchState.STOP;
        break;
      case OUT_OF_MEMORY:
        state = BatchState.OUT_OF_MEMORY;
        break;
      case NONE:
        state = BatchState.DONE;
        break;
    }
  }

  @Override
  public IterOutcome innerNext() {
    if (schema != null) {
      if (spillCount == 0) {
        return (getSelectionVector4().next()) ? IterOutcome.OK : IterOutcome.NONE;
      } else {
        Stopwatch w = new Stopwatch();
        w.start();
        int count = copier.next(targetRecordCount);
        if (count > 0) {
          long t = w.elapsed(TimeUnit.MICROSECONDS);
          logger.debug("Took {} us to merge {} records", t, count);
          container.setRecordCount(count);
          return IterOutcome.OK;
        } else {
          logger.debug("copier returned 0 records");
          return IterOutcome.NONE;
        }
      }
    }

    int totalCount = 0;

    try{
      container.clear();
      outer: while (true) {
        Stopwatch watch = new Stopwatch();
        watch.start();
        IterOutcome upstream;
        if (first) {
          upstream = IterOutcome.OK_NEW_SCHEMA;
        } else {
          upstream = next(incoming);
        }
        if (upstream == IterOutcome.OK && sorter == null) {
          upstream = IterOutcome.OK_NEW_SCHEMA;
        }
//        logger.debug("Took {} us to get next", watch.elapsed(TimeUnit.MICROSECONDS));
        switch (upstream) {
        case NONE:
          if (first) {
            return upstream;
          }
          break outer;
        case NOT_YET:
          throw new UnsupportedOperationException();
        case STOP:
          return upstream;
        case OK_NEW_SCHEMA:
          // only change in the case that the schema truly changes.  Artificial schema changes are ignored.
          if (!incoming.getSchema().equals(schema)) {
            if (schema != null) {
              throw new SchemaChangeException();
            }
            this.schema = incoming.getSchema();
            this.sorter = createNewSorter(context, incoming);
          }
          // fall through.
        case OK:
          if (first) {
            first = false;
          }
          if (incoming.getRecordCount() == 0) {
            for (VectorWrapper w : incoming) {
              w.clear();
            }
            break;
          }
          totalSizeInMemory += getBufferSize(incoming);
          SelectionVector2 sv2;
          if (incoming.getSchema().getSelectionVectorMode() == BatchSchema.SelectionVectorMode.TWO_BYTE) {
            sv2 = incoming.getSelectionVector2();
            if (sv2.getBuffer(false).isRootBuffer()) {
              oContext.getAllocator().takeOwnership(sv2.getBuffer(false));
            }
          } else {
            try {
              sv2 = newSV2();
            } catch(InterruptedException e) {
              return IterOutcome.STOP;
            } catch (OutOfMemoryException e) {
              throw new OutOfMemoryRuntimeException(e);
            }
          }
          int count = sv2.getCount();
          totalCount += count;
          sorter.setup(context, sv2, incoming);
          Stopwatch w = new Stopwatch();
          w.start();
          sorter.sort(sv2);
//          logger.debug("Took {} us to sort {} records", w.elapsed(TimeUnit.MICROSECONDS), count);
          RecordBatchData rbd = new RecordBatchData(incoming);
          boolean success = false;
          try {
            if (incoming.getSchema().getSelectionVectorMode() == SelectionVectorMode.NONE) {
              rbd.setSv2(sv2);
            }
            batchGroups.add(new BatchGroup(rbd.getContainer(), rbd.getSv2()));
            batchesSinceLastSpill++;
            if (// We have spilled at least once and the current memory used is more than the 75% of peak memory used.
                (spillCount > 0 && totalSizeInMemory > .75 * highWaterMark) ||
                // If we haven't spilled so far, do we have enough memory for MSorter if this turns out to be the last incoming batch?
                (spillCount == 0 && !hasMemoryForInMemorySort(totalCount)) ||
                // current memory used is more than 95% of memory usage limit of this operator
                (totalSizeInMemory > .95 * popConfig.getMaxAllocation()) ||
                // current memory used is more than 95% of memory usage limit of this fragment
                (totalSizeInMemory > .95 * oContext.getAllocator().getFragmentLimit()) ||
                // Number of incoming batches (BatchGroups) exceed the limit and number of incoming batches accumulated
                // since the last spill exceed the defined limit
                (batchGroups.size() > SPILL_THRESHOLD && batchesSinceLastSpill >= SPILL_BATCH_GROUP_SIZE)) {

              if (firstSpillBatchCount == 0) {
                firstSpillBatchCount = batchGroups.size();
              }

              if (spilledBatchGroups.size() > firstSpillBatchCount / 2) {
                logger.info("Merging spills");
                spilledBatchGroups.addFirst(mergeAndSpill(spilledBatchGroups));
              }
              spilledBatchGroups.add(mergeAndSpill(batchGroups));
              batchesSinceLastSpill = 0;
            }
            long t = w.elapsed(TimeUnit.MICROSECONDS);
//          logger.debug("Took {} us to sort {} records", t, count);
            success = true;
          } finally {
            if (!success) {
              rbd.clear();
            }
          }
          break;
        case OUT_OF_MEMORY:
          logger.debug("received OUT_OF_MEMORY, trying to spill");
          highWaterMark = totalSizeInMemory;
          if (batchesSinceLastSpill > 2) {
            spilledBatchGroups.add(mergeAndSpill(batchGroups));
            batchesSinceLastSpill = 0;
          } else {
            logger.debug("not enough batches to spill, sending OUT_OF_MEMORY downstream");
            return IterOutcome.OUT_OF_MEMORY;
          }
          break;
        default:
          throw new UnsupportedOperationException();
        }
      }

      if (totalCount == 0) {
        return IterOutcome.NONE;
      }
      if (spillCount == 0) {
        Stopwatch watch = new Stopwatch();
        watch.start();

        if (builder != null) {
          builder.clear();
          builder.close();
        }
        builder = new SortRecordBatchBuilder(oContext.getAllocator(), MAX_SORT_BYTES);

        for (BatchGroup group : batchGroups) {
          RecordBatchData rbd = new RecordBatchData(group.getContainer());
          rbd.setSv2(group.getSv2());
          builder.add(rbd);
        }

        builder.build(context, container);
        sv4 = builder.getSv4();
        mSorter = createNewMSorter();
        mSorter.setup(context, oContext.getAllocator(), getSelectionVector4(), this.container);

        // For testing memory-leak purpose, inject exception after mSorter finishes setup
        injector.injectUnchecked(context.getExecutionControls(), INTERRUPTION_AFTER_SETUP);
        mSorter.sort(this.container);

        // sort may have prematurely exited due to should continue returning false.
        if (!context.shouldContinue()) {
          return IterOutcome.STOP;
        }

        // For testing memory-leak purpose, inject exception after mSorter finishes sorting
        injector.injectUnchecked(context.getExecutionControls(), INTERRUPTION_AFTER_SORT);
        sv4 = mSorter.getSV4();

        long t = watch.elapsed(TimeUnit.MICROSECONDS);
//        logger.debug("Took {} us to sort {} records", t, sv4.getTotalCount());
        container.buildSchema(SelectionVectorMode.FOUR_BYTE);
      } else {
        spilledBatchGroups.add(mergeAndSpill(batchGroups));
        batchGroups.addAll(spilledBatchGroups);
        logger.warn("Starting to merge. {} batch groups. Current allocated memory: {}", batchGroups.size(), oContext.getAllocator().getAllocatedMemory());
        VectorContainer hyperBatch = constructHyperBatch(batchGroups);
        createCopier(hyperBatch, batchGroups, container);

        int estimatedRecordSize = 0;
        for (VectorWrapper w : batchGroups.get(0)) {
          try {
            estimatedRecordSize += TypeHelper.getSize(w.getField().getType());
          } catch (UnsupportedOperationException e) {
            estimatedRecordSize += 50;
          }
        }
        targetRecordCount = Math.min(MAX_BATCH_SIZE, Math.max(1, 250 * 1000 / estimatedRecordSize));
        int count = copier.next(targetRecordCount);
        container.buildSchema(SelectionVectorMode.NONE);
        container.setRecordCount(count);
      }

      return IterOutcome.OK_NEW_SCHEMA;

    } catch (SchemaChangeException ex) {
      kill(false);
      context.fail(UserException.unsupportedError(ex)
        .message("Sort doesn't currently support sorts with changing schemas").build());
      return IterOutcome.STOP;
    } catch(ClassTransformationException | IOException ex) {
      kill(false);
      context.fail(ex);
      return IterOutcome.STOP;
    } catch (UnsupportedOperationException e) {
      throw new RuntimeException(e);
    }
  }

  private boolean hasMemoryForInMemorySort(int currentRecordCount) {
    long currentlyAvailable =  popConfig.getMaxAllocation() - oContext.getAllocator().getAllocatedMemory();

    long neededForInMemorySort = SortRecordBatchBuilder.memoryNeeded(currentRecordCount) +
        MSortTemplate.memoryNeeded(currentRecordCount);

    return currentlyAvailable > neededForInMemorySort;
  }

  public BatchGroup mergeAndSpill(LinkedList<BatchGroup> batchGroups) throws SchemaChangeException {
    logger.debug("Copier allocator current allocation {}", copierAllocator.getAllocatedMemory());
    VectorContainer outputContainer = new VectorContainer();
    List<BatchGroup> batchGroupList = Lists.newArrayList();
    int batchCount = batchGroups.size();
    for (int i = 0; i < batchCount / 2; i++) {
      if (batchGroups.size() == 0) {
        break;
      }
      BatchGroup batch = batchGroups.pollLast();
      batchGroupList.add(batch);
      long bufferSize = getBufferSize(batch);
      totalSizeInMemory -= bufferSize;
    }
    if (batchGroupList.size() == 0) {
      return null;
    }
    int estimatedRecordSize = 0;
    for (VectorWrapper w : batchGroupList.get(0)) {
      try {
        estimatedRecordSize += TypeHelper.getSize(w.getField().getType());
      } catch (UnsupportedOperationException e) {
        estimatedRecordSize += 50;
      }
    }
    int targetRecordCount = Math.max(1, 250 * 1000 / estimatedRecordSize);
    VectorContainer hyperBatch = constructHyperBatch(batchGroupList);
    createCopier(hyperBatch, batchGroupList, outputContainer);

    int count = copier.next(targetRecordCount);
    assert count > 0;

    VectorContainer c1 = VectorContainer.getTransferClone(outputContainer);
    c1.buildSchema(BatchSchema.SelectionVectorMode.NONE);
    c1.setRecordCount(count);

    String outputFile = Joiner.on("/").join(dirs.next(), fileName, spillCount++);
    BatchGroup newGroup = new BatchGroup(c1, fs, outputFile, oContext.getAllocator());

    logger.info("Merging and spilling to {}", outputFile);
    try {
      while ((count = copier.next(targetRecordCount)) > 0) {
        outputContainer.buildSchema(BatchSchema.SelectionVectorMode.NONE);
        outputContainer.setRecordCount(count);
        newGroup.addBatch(outputContainer);
      }
      newGroup.closeOutputStream();
      for (BatchGroup group : batchGroupList) {
        group.cleanup();
      }
      hyperBatch.clear();
    } catch (IOException e) {
      throw new RuntimeException(e);
    }
    takeOwnership(c1);
    totalSizeInMemory += getBufferSize(c1);
    logger.info("Completed spilling to {}", outputFile);
    return newGroup;
  }

  private void takeOwnership(VectorAccessible batch) {
    for (VectorWrapper w : batch) {
      DrillBuf[] bufs = w.getValueVector().getBuffers(false);
      for (DrillBuf buf : bufs) {
        if (buf.isRootBuffer()) {
          oContext.getAllocator().takeOwnership(buf);
        }
      }
    }
  }

  private long getBufferSize(VectorAccessible batch) {
    long size = 0;
    for (VectorWrapper w : batch) {
      DrillBuf[] bufs = w.getValueVector().getBuffers(false);
      for (DrillBuf buf : bufs) {
        if (buf.isRootBuffer()) {
          size += buf.capacity();
        }
      }
    }
    return size;
  }

  private SelectionVector2 newSV2() throws OutOfMemoryException, InterruptedException {
    SelectionVector2 sv2 = new SelectionVector2(oContext.getAllocator());
    if (!sv2.allocateNew(incoming.getRecordCount())) {
      try {
        spilledBatchGroups.addFirst(mergeAndSpill(batchGroups));
      } catch (SchemaChangeException e) {
        throw new RuntimeException();
      }
      batchesSinceLastSpill = 0;
      int waitTime = 1;
      while (true) {
        try {
          Thread.sleep(waitTime * 1000);
        } catch(final InterruptedException e) {
          if (!context.shouldContinue()) {
            throw e;
          }
        }
        waitTime *= 2;
        if (sv2.allocateNew(incoming.getRecordCount())) {
          break;
        }
        if (waitTime >= 32) {
          throw new OutOfMemoryException("Unable to allocate sv2 buffer after repeated attempts");
        }
      }
    }
    for (int i = 0; i < incoming.getRecordCount(); i++) {
      sv2.setIndex(i, (char) i);
    }
    sv2.setRecordCount(incoming.getRecordCount());
    return sv2;
  }

  private VectorContainer constructHyperBatch(List<BatchGroup> batchGroupList) {
    VectorContainer cont = new VectorContainer();
    for (MaterializedField field : schema) {
      ValueVector[] vectors = new ValueVector[batchGroupList.size()];
      int i = 0;
      for (BatchGroup group : batchGroupList) {
        vectors[i++] = group.getValueAccessorById(
            field.getValueClass(),
            group.getValueVectorId(field.getPath()).getFieldIds())
            .getValueVector();
      }
      cont.add(vectors);
    }
    cont.buildSchema(BatchSchema.SelectionVectorMode.FOUR_BYTE);
    return cont;
  }

  private MSorter createNewMSorter() throws ClassTransformationException, IOException, SchemaChangeException {
    return createNewMSorter(this.context, this.popConfig.getOrderings(), this, MAIN_MAPPING, LEFT_MAPPING, RIGHT_MAPPING);
  }

  private MSorter createNewMSorter(FragmentContext context, List<Ordering> orderings, VectorAccessible batch, MappingSet mainMapping, MappingSet leftMapping, MappingSet rightMapping)
          throws ClassTransformationException, IOException, SchemaChangeException{
    CodeGenerator<MSorter> cg = CodeGenerator.get(MSorter.TEMPLATE_DEFINITION, context.getFunctionRegistry());
    ClassGenerator<MSorter> g = cg.getRoot();
    g.setMappingSet(mainMapping);

    for (Ordering od : orderings) {
      // first, we rewrite the evaluation stack for each side of the comparison.
      ErrorCollector collector = new ErrorCollectorImpl();
      final LogicalExpression expr = ExpressionTreeMaterializer.materialize(od.getExpr(), batch, collector, context.getFunctionRegistry());
      if (collector.hasErrors()) {
        throw new SchemaChangeException("Failure while materializing expression. " + collector.toErrorString());
      }
      g.setMappingSet(leftMapping);
      HoldingContainer left = g.addExpr(expr, false);
      g.setMappingSet(rightMapping);
      HoldingContainer right = g.addExpr(expr, false);
      g.setMappingSet(mainMapping);

      // next we wrap the two comparison sides and add the expression block for the comparison.
      LogicalExpression fh =
          FunctionGenerationHelper.getOrderingComparator(od.nullsSortHigh(), left, right,
                                                         context.getFunctionRegistry());
      HoldingContainer out = g.addExpr(fh, false);
      JConditional jc = g.getEvalBlock()._if(out.getValue().ne(JExpr.lit(0)));

      if (od.getDirection() == Direction.ASCENDING) {
        jc._then()._return(out.getValue());
      }else{
        jc._then()._return(out.getValue().minus());
      }
      g.rotateBlock();
    }

    g.rotateBlock();
    g.getEvalBlock()._return(JExpr.lit(0));

    return context.getImplementationClass(cg);


  }

  public SingleBatchSorter createNewSorter(FragmentContext context, VectorAccessible batch)
          throws ClassTransformationException, IOException, SchemaChangeException{
    CodeGenerator<SingleBatchSorter> cg = CodeGenerator.get(SingleBatchSorter.TEMPLATE_DEFINITION, context.getFunctionRegistry());
    ClassGenerator<SingleBatchSorter> g = cg.getRoot();

    generateComparisons(g, batch);

    return context.getImplementationClass(cg);
  }

  private void generateComparisons(ClassGenerator g, VectorAccessible batch) throws SchemaChangeException {
    g.setMappingSet(MAIN_MAPPING);

    for (Ordering od : popConfig.getOrderings()) {
      // first, we rewrite the evaluation stack for each side of the comparison.
      ErrorCollector collector = new ErrorCollectorImpl();
      final LogicalExpression expr = ExpressionTreeMaterializer.materialize(od.getExpr(), batch, collector,context.getFunctionRegistry());
      if (collector.hasErrors()) {
        throw new SchemaChangeException("Failure while materializing expression. " + collector.toErrorString());
      }
      g.setMappingSet(LEFT_MAPPING);
      HoldingContainer left = g.addExpr(expr, false);
      g.setMappingSet(RIGHT_MAPPING);
      HoldingContainer right = g.addExpr(expr, false);
      g.setMappingSet(MAIN_MAPPING);

      // next we wrap the two comparison sides and add the expression block for the comparison.
      LogicalExpression fh =
          FunctionGenerationHelper.getOrderingComparator(od.nullsSortHigh(), left, right,
                                                         context.getFunctionRegistry());
      HoldingContainer out = g.addExpr(fh, false);
      JConditional jc = g.getEvalBlock()._if(out.getValue().ne(JExpr.lit(0)));

      if (od.getDirection() == Direction.ASCENDING) {
        jc._then()._return(out.getValue());
      }else{
        jc._then()._return(out.getValue().minus());
      }
      g.rotateBlock();
    }

    g.rotateBlock();
    g.getEvalBlock()._return(JExpr.lit(0));
  }

  private void createCopier(VectorAccessible batch, List<BatchGroup> batchGroupList, VectorContainer outputContainer) throws SchemaChangeException {
    try {
      if (copier == null) {
        CodeGenerator<PriorityQueueCopier> cg = CodeGenerator.get(PriorityQueueCopier.TEMPLATE_DEFINITION, context.getFunctionRegistry());
        ClassGenerator<PriorityQueueCopier> g = cg.getRoot();

        generateComparisons(g, batch);

        g.setMappingSet(COPIER_MAPPING_SET);
        CopyUtil.generateCopies(g, batch, true);
        g.setMappingSet(MAIN_MAPPING);
        copier = context.getImplementationClass(cg);
      } else {
        copier.cleanup();
      }

      for (VectorWrapper<?> i : batch) {
        ValueVector v = TypeHelper.getNewVector(i.getField(), copierAllocator);
        outputContainer.add(v);
      }
      copier.setup(context, copierAllocator, batch, batchGroupList, outputContainer);
    } catch (ClassTransformationException e) {
      throw new RuntimeException(e);
    } catch (IOException e) {
      throw new RuntimeException(e);
    }
  }


  @Override
  public WritableBatch getWritableBatch() {
    throw new UnsupportedOperationException("A sort batch is not writable.");
  }

  @Override
  protected void killIncoming(boolean sendUpstream) {
    incoming.kill(sendUpstream);
  }

  private String getFileName(int spill) {
     /*
     * From the context, get the query id, major fragment id, minor fragment id. This will be used as the file name to
     * which we will dump the incoming buffer data
     */
    FragmentHandle handle = context.getHandle();

    String qid = QueryIdHelper.getQueryId(handle.getQueryId());

    int majorFragmentId = handle.getMajorFragmentId();
    int minorFragmentId = handle.getMinorFragmentId();

    String fileName = String.format("%s//%s//major_fragment_%s//minor_fragment_%s//operator_%s//%s", dirs.next(), qid, majorFragmentId, minorFragmentId, popConfig.getOperatorId(), spill);

    return fileName;
  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/logical/DrillOptiq.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.planner.logical;

import java.math.BigDecimal;
import java.util.GregorianCalendar;
import java.util.List;

import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.common.expression.ExpressionPosition;
import org.apache.drill.common.expression.FieldReference;
import org.apache.drill.common.expression.FunctionCallFactory;
import org.apache.drill.common.expression.IfExpression;
import org.apache.drill.common.expression.IfExpression.IfCondition;
import org.apache.drill.common.expression.LogicalExpression;
import org.apache.drill.common.expression.NullExpression;
import org.apache.drill.common.expression.SchemaPath;
import org.apache.drill.common.expression.TypedNullConstant;
import org.apache.drill.common.expression.ValueExpressions;
import org.apache.drill.common.expression.ValueExpressions.QuotedString;
import org.apache.drill.common.types.TypeProtos;
import org.apache.drill.common.types.TypeProtos.MajorType;
import org.apache.drill.common.types.TypeProtos.MinorType;
import org.apache.drill.common.types.Types;
import org.apache.drill.exec.planner.StarColumnHelper;
import org.apache.calcite.rel.RelNode;
import org.apache.calcite.rel.type.RelDataTypeField;
import org.apache.calcite.rex.RexCall;
import org.apache.calcite.rex.RexCorrelVariable;
import org.apache.calcite.rex.RexDynamicParam;
import org.apache.calcite.rex.RexFieldAccess;
import org.apache.calcite.rex.RexInputRef;
import org.apache.calcite.rex.RexLiteral;
import org.apache.calcite.rex.RexLocalRef;
import org.apache.calcite.rex.RexNode;
import org.apache.calcite.rex.RexOver;
import org.apache.calcite.rex.RexRangeRef;
import org.apache.calcite.rex.RexVisitorImpl;
import org.apache.calcite.sql.SqlSyntax;
import org.apache.calcite.sql.fun.SqlStdOperatorTable;
import org.apache.calcite.util.NlsString;

import com.google.common.collect.Lists;
import org.apache.drill.exec.planner.physical.PlannerSettings;
import org.apache.drill.exec.work.ExecErrorConstants;

/**
 * Utilities for Drill's planner.
 */
public class DrillOptiq {
  public static final String UNSUPPORTED_REX_NODE_ERROR = "Cannot convert RexNode to equivalent Drill expression. ";
  private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(DrillOptiq.class);

  /**
   * Converts a tree of {@link RexNode} operators into a scalar expression in Drill syntax.
   */
  public static LogicalExpression toDrill(DrillParseContext context, RelNode input, RexNode expr) {
    final RexToDrill visitor = new RexToDrill(context, input);
    return expr.accept(visitor);
  }

  private static class RexToDrill extends RexVisitorImpl<LogicalExpression> {
    private final RelNode input;
    private final DrillParseContext context;

    RexToDrill(DrillParseContext context, RelNode input) {
      super(true);
      this.context = context;
      this.input = input;
    }

    @Override
    public LogicalExpression visitInputRef(RexInputRef inputRef) {
      final int index = inputRef.getIndex();
      final RelDataTypeField field = input.getRowType().getFieldList().get(index);
      return FieldReference.getWithQuotedRef(field.getName());
    }

    @Override
    public LogicalExpression visitCall(RexCall call) {
//      logger.debug("RexCall {}, {}", call);
      final SqlSyntax syntax = call.getOperator().getSyntax();
      switch (syntax) {
      case BINARY:
        logger.debug("Binary");
        final String funcName = call.getOperator().getName().toLowerCase();
        return doFunction(call, funcName);
      case FUNCTION:
      case FUNCTION_ID:
        logger.debug("Function");
        return getDrillFunctionFromOptiqCall(call);
      case POSTFIX:
        logger.debug("Postfix");
        switch(call.getKind()){
        case IS_NOT_NULL:
        case IS_NOT_TRUE:
        case IS_NOT_FALSE:
        case IS_NULL:
        case IS_TRUE:
        case IS_FALSE:
        case OTHER:
          return FunctionCallFactory.createExpression(call.getOperator().getName().toLowerCase(),
              ExpressionPosition.UNKNOWN, call.getOperands().get(0).accept(this));
        }
        throw new AssertionError("todo: implement syntax " + syntax + "(" + call + ")");
      case PREFIX:
        logger.debug("Prefix");
        LogicalExpression arg = call.getOperands().get(0).accept(this);
        switch(call.getKind()){
        case NOT:
          return FunctionCallFactory.createExpression(call.getOperator().getName().toLowerCase(),
            ExpressionPosition.UNKNOWN, arg);
        }
        throw new AssertionError("todo: implement syntax " + syntax + "(" + call + ")");
      case SPECIAL:
        logger.debug("Special");
        switch(call.getKind()){
        case CAST:
          return getDrillCastFunctionFromOptiq(call);
        case LIKE:
        case SIMILAR:
          return getDrillFunctionFromOptiqCall(call);
        case CASE:
          List<LogicalExpression> caseArgs = Lists.newArrayList();
          for(RexNode r : call.getOperands()){
            caseArgs.add(r.accept(this));
          }

          caseArgs = Lists.reverse(caseArgs);
          // number of arguements are always going to be odd, because
          // Optiq adds "null" for the missing else expression at the end
          assert caseArgs.size()%2 == 1;
          LogicalExpression elseExpression = caseArgs.get(0);
          for (int i=1; i<caseArgs.size(); i=i+2) {
            elseExpression = IfExpression.newBuilder()
              .setElse(elseExpression)
              .setIfCondition(new IfCondition(caseArgs.get(i + 1), caseArgs.get(i))).build();
          }
          return elseExpression;
        }

        if (call.getOperator() == SqlStdOperatorTable.ITEM) {
          SchemaPath left = (SchemaPath) call.getOperands().get(0).accept(this);

          // Convert expr of item[*, 'abc'] into column expression 'abc'
          String rootSegName = left.getRootSegment().getPath();
          if (StarColumnHelper.isStarColumn(rootSegName)) {
            rootSegName = rootSegName.substring(0, rootSegName.indexOf("*"));
            final RexLiteral literal = (RexLiteral) call.getOperands().get(1);
            return SchemaPath.getSimplePath(rootSegName + literal.getValue2().toString());
          }

          final RexLiteral literal = (RexLiteral) call.getOperands().get(1);
          switch(literal.getTypeName()){
          case DECIMAL:
          case INTEGER:
            return left.getChild(((BigDecimal)literal.getValue()).intValue());
          case CHAR:
            return left.getChild(literal.getValue2().toString());
          default:
            // fall through
          }
        }

        if (call.getOperator() == SqlStdOperatorTable.DATETIME_PLUS) {
          return doFunction(call, "+");
        }

        // fall through
      default:
        throw new AssertionError("todo: implement syntax " + syntax + "(" + call + ")");
      }
    }

    private LogicalExpression doFunction(RexCall call, String funcName) {
      List<LogicalExpression> args = Lists.newArrayList();
      for(RexNode r : call.getOperands()){
        args.add(r.accept(this));
      }

      if (FunctionCallFactory.isBooleanOperator(funcName)) {
        LogicalExpression func = FunctionCallFactory.createBooleanOperator(funcName, args);
        return func;
      } else {
        args = Lists.reverse(args);
        LogicalExpression lastArg = args.get(0);
        for(int i = 1; i < args.size(); i++){
          lastArg = FunctionCallFactory.createExpression(funcName, Lists.newArrayList(args.get(i), lastArg));
        }

        return lastArg;
      }

    }
    private LogicalExpression doUnknown(RexNode o){
      // raise an error
      throw UserException.planError().message(UNSUPPORTED_REX_NODE_ERROR +
              "RexNode Class: %s, RexNode Digest: %s", o.getClass().getName(), o.toString()).build();
    }
    @Override
    public LogicalExpression visitLocalRef(RexLocalRef localRef) {
      return doUnknown(localRef);
    }

    @Override
    public LogicalExpression visitOver(RexOver over) {
      return doUnknown(over);
    }

    @Override
    public LogicalExpression visitCorrelVariable(RexCorrelVariable correlVariable) {
      return doUnknown(correlVariable);
    }

    @Override
    public LogicalExpression visitDynamicParam(RexDynamicParam dynamicParam) {
      return doUnknown(dynamicParam);
    }

    @Override
    public LogicalExpression visitRangeRef(RexRangeRef rangeRef) {
      return doUnknown(rangeRef);
    }

    @Override
    public LogicalExpression visitFieldAccess(RexFieldAccess fieldAccess) {
      return super.visitFieldAccess(fieldAccess);
    }


    private LogicalExpression getDrillCastFunctionFromOptiq(RexCall call){
      LogicalExpression arg = call.getOperands().get(0).accept(this);
      MajorType castType = null;

      switch(call.getType().getSqlTypeName().getName()){
      case "VARCHAR":
      case "CHAR":
        castType = Types.required(MinorType.VARCHAR).toBuilder().setWidth(call.getType().getPrecision()).build();
        break;

      case "INTEGER": castType = Types.required(MinorType.INT); break;
      case "FLOAT": castType = Types.required(MinorType.FLOAT4); break;
      case "DOUBLE": castType = Types.required(MinorType.FLOAT8); break;
      case "DECIMAL":
        if (context.getPlannerSettings().getOptions().
            getOption(PlannerSettings.ENABLE_DECIMAL_DATA_TYPE_KEY).bool_val == false ) {
          throw UserException
              .unsupportedError()
              .message(ExecErrorConstants.DECIMAL_DISABLE_ERR_MSG)
              .build();
        }

        int precision = call.getType().getPrecision();
        int scale = call.getType().getScale();

        if (precision <= 9) {
          castType = TypeProtos.MajorType.newBuilder().setMinorType(MinorType.DECIMAL9).setPrecision(precision).setScale(scale).build();
        } else if (precision <= 18) {
          castType = TypeProtos.MajorType.newBuilder().setMinorType(MinorType.DECIMAL18).setPrecision(precision).setScale(scale).build();
        } else if (precision <= 28) {
          // Inject a cast to SPARSE before casting to the dense type.
          castType = TypeProtos.MajorType.newBuilder().setMinorType(MinorType.DECIMAL28SPARSE).setPrecision(precision).setScale(scale).build();
        } else if (precision <= 38) {
          castType = TypeProtos.MajorType.newBuilder().setMinorType(MinorType.DECIMAL38SPARSE).setPrecision(precision).setScale(scale).build();
        } else {
          throw new UnsupportedOperationException("Only Decimal types with precision range 0 - 38 is supported");
        }
        break;

        case "INTERVAL_YEAR_MONTH": castType = Types.required(MinorType.INTERVALYEAR); break;
        case "INTERVAL_DAY_TIME": castType = Types.required(MinorType.INTERVALDAY); break;
        case "BOOLEAN": castType = Types.required(MinorType.BIT); break;
        case "ANY": return arg; // Type will be same as argument.
        default: castType = Types.required(MinorType.valueOf(call.getType().getSqlTypeName().getName()));
      }
      return FunctionCallFactory.createCast(castType, ExpressionPosition.UNKNOWN, arg);
    }

    private LogicalExpression getDrillFunctionFromOptiqCall(RexCall call) {
      List<LogicalExpression> args = Lists.newArrayList();
      for(RexNode n : call.getOperands()){
        args.add(n.accept(this));
      }
      String functionName = call.getOperator().getName().toLowerCase();

      // TODO: once we have more function rewrites and a patter emerges from different rewrites, factor this out in a better fashion
      /* Rewrite extract functions in the following manner
       * extract(year, date '2008-2-23') ---> extractYear(date '2008-2-23')
       */
      if (functionName.equals("extract")) {

        // Assert that the first argument to extract is a QuotedString
        assert args.get(0) instanceof ValueExpressions.QuotedString;

        // Get the unit of time to be extracted
        String timeUnitStr = ((ValueExpressions.QuotedString)args.get(0)).value;

        switch (timeUnitStr){
          case ("YEAR"):
          case ("MONTH"):
          case ("DAY"):
          case ("HOUR"):
          case ("MINUTE"):
          case ("SECOND"):
            String functionPostfix = timeUnitStr.substring(0, 1).toUpperCase() + timeUnitStr.substring(1).toLowerCase();
            functionName += functionPostfix;
            return FunctionCallFactory.createExpression(functionName, args.subList(1, 2));
          default:
            throw new UnsupportedOperationException("extract function supports the following time units: YEAR, MONTH, DAY, HOUR, MINUTE, SECOND");
        }
      } else if (functionName.equals("trim")) {
        String trimFunc = null;
        List<LogicalExpression> trimArgs = Lists.newArrayList();

        assert args.get(0) instanceof ValueExpressions.QuotedString;
        switch (((ValueExpressions.QuotedString)args.get(0)).value.toUpperCase()) {
        case "LEADING":
          trimFunc = "ltrim";
          break;
        case "TRAILING":
          trimFunc = "rtrim";
          break;
        case "BOTH":
          trimFunc = "btrim";
          break;
        default:
          assert 1 == 0;
        }

        trimArgs.add(args.get(2));
        trimArgs.add(args.get(1));

        return FunctionCallFactory.createExpression(trimFunc, trimArgs);
      } else if (functionName.equals("ltrim") || functionName.equals("rtrim") || functionName.equals("btrim")) {
        if (args.size() == 1) {
          args.add(ValueExpressions.getChar(" "));
        }
        return FunctionCallFactory.createExpression(functionName, args);
      } else if (functionName.equals("date_part")) {
        // Rewrite DATE_PART functions as extract functions
        // assert that the function has exactly two arguments
        assert args.size() == 2;

        /* Based on the first input to the date_part function we rewrite the function as the
         * appropriate extract function. For example
         * date_part('year', date '2008-2-23') ------> extractYear(date '2008-2-23')
         */
        assert args.get(0) instanceof QuotedString;

        QuotedString extractString = (QuotedString) args.get(0);
        String functionPostfix = extractString.value.substring(0, 1).toUpperCase() + extractString.value.substring(1).toLowerCase();
        return FunctionCallFactory.createExpression("extract" + functionPostfix, args.subList(1, 2));
      } else if (functionName.equals("concat")) {

        // Cast arguments to VARCHAR
        List<LogicalExpression> concatArgs = Lists.newArrayList();
        concatArgs.add(args.get(0));
        concatArgs.add(args.get(1));

        LogicalExpression first = FunctionCallFactory.createExpression(functionName, concatArgs);

        for (int i = 2; i < args.size(); i++) {
          concatArgs = Lists.newArrayList();
          concatArgs.add(first);
          concatArgs.add(args.get(i));
          first = FunctionCallFactory.createExpression(functionName, concatArgs);
        }

        return first;
      } else if (functionName.equals("length")) {

          if (args.size() == 2) {

              // Second argument should always be a literal specifying the encoding format
              assert args.get(1) instanceof ValueExpressions.QuotedString;

              String encodingType = ((ValueExpressions.QuotedString) args.get(1)).value;
              functionName += encodingType.substring(0, 1).toUpperCase() + encodingType.substring(1).toLowerCase();

              return FunctionCallFactory.createExpression(functionName, args.subList(0, 1));
          }
      } else if ((functionName.equals("convert_from") || functionName.equals("convert_to"))
                    && args.get(1) instanceof QuotedString) {
        return FunctionCallFactory.createConvert(functionName, ((QuotedString)args.get(1)).value, args.get(0), ExpressionPosition.UNKNOWN);
      } else if ((functionName.equalsIgnoreCase("rpad")) || functionName.equalsIgnoreCase("lpad")) {
        // If we have only two arguments for rpad/lpad append a default QuotedExpression as an argument which will be used to pad the string
        if (args.size() == 2) {
          String spaceFill = " ";
          LogicalExpression fill = ValueExpressions.getChar(spaceFill);
          args.add(fill);
        }
      }

      return FunctionCallFactory.createExpression(functionName, args);
    }

    @Override
    public LogicalExpression visitLiteral(RexLiteral literal) {
      switch(literal.getType().getSqlTypeName()){
      case BIGINT:
        if (isLiteralNull(literal)) {
          return createNullExpr(MinorType.BIGINT);
        }
        long l = (((BigDecimal) literal.getValue()).setScale(0, BigDecimal.ROUND_HALF_UP)).longValue();
        return ValueExpressions.getBigInt(l);
      case BOOLEAN:
        if (isLiteralNull(literal)) {
          return createNullExpr(MinorType.BIT);
        }
        return ValueExpressions.getBit(((Boolean) literal.getValue()));
      case CHAR:
        if (isLiteralNull(literal)) {
          return createNullExpr(MinorType.VARCHAR);
        }
        return ValueExpressions.getChar(((NlsString)literal.getValue()).getValue());
      case DOUBLE:
        if (isLiteralNull(literal)){
          return createNullExpr(MinorType.FLOAT8);
        }
        double d = ((BigDecimal) literal.getValue()).doubleValue();
        return ValueExpressions.getFloat8(d);
      case FLOAT:
        if (isLiteralNull(literal)) {
          return createNullExpr(MinorType.FLOAT4);
        }
        float f = ((BigDecimal) literal.getValue()).floatValue();
        return ValueExpressions.getFloat4(f);
      case INTEGER:
        if (isLiteralNull(literal)) {
          return createNullExpr(MinorType.INT);
        }
        int a = (((BigDecimal) literal.getValue()).setScale(0, BigDecimal.ROUND_HALF_UP)).intValue();
        return ValueExpressions.getInt(a);

      case DECIMAL:
        /* TODO: Enable using Decimal literals once we have more functions implemented for Decimal
         * For now continue using Double instead of decimals

        int precision = ((BigDecimal) literal.getValue()).precision();
        if (precision <= 9) {
            return ValueExpressions.getDecimal9((BigDecimal)literal.getValue());
        } else if (precision <= 18) {
            return ValueExpressions.getDecimal18((BigDecimal)literal.getValue());
        } else if (precision <= 28) {
            return ValueExpressions.getDecimal28((BigDecimal)literal.getValue());
        } else if (precision <= 38) {
            return ValueExpressions.getDecimal38((BigDecimal)literal.getValue());
        } */
        if (isLiteralNull(literal)) {
          return createNullExpr(MinorType.FLOAT8);
        }
        double dbl = ((BigDecimal) literal.getValue()).doubleValue();
        logger.warn("Converting exact decimal into approximate decimal.  Should be fixed once decimal is implemented.");
        return ValueExpressions.getFloat8(dbl);
      case VARCHAR:
        if (isLiteralNull(literal)) {
          return createNullExpr(MinorType.VARCHAR);
        }
        return ValueExpressions.getChar(((NlsString)literal.getValue()).getValue());
      case SYMBOL:
        if (isLiteralNull(literal)) {
          return createNullExpr(MinorType.VARCHAR);
        }
        return ValueExpressions.getChar(literal.getValue().toString());
      case DATE:
        if (isLiteralNull(literal)) {
          return createNullExpr(MinorType.DATE);
        }
        return (ValueExpressions.getDate((GregorianCalendar)literal.getValue()));
      case TIME:
        if (isLiteralNull(literal)) {
          return createNullExpr(MinorType.TIME);
        }
        return (ValueExpressions.getTime((GregorianCalendar)literal.getValue()));
      case TIMESTAMP:
        if (isLiteralNull(literal)) {
          return createNullExpr(MinorType.TIMESTAMP);
        }
        return (ValueExpressions.getTimeStamp((GregorianCalendar) literal.getValue()));
      case INTERVAL_YEAR_MONTH:
        if (isLiteralNull(literal)) {
          return createNullExpr(MinorType.INTERVALYEAR);
        }
        return (ValueExpressions.getIntervalYear(((BigDecimal) (literal.getValue())).intValue()));
      case INTERVAL_DAY_TIME:
        if (isLiteralNull(literal)) {
          return createNullExpr(MinorType.INTERVALDAY);
        }
        return (ValueExpressions.getIntervalDay(((BigDecimal) (literal.getValue())).longValue()));
      case NULL:
        return NullExpression.INSTANCE;
      case ANY:
        if (isLiteralNull(literal)) {
          return NullExpression.INSTANCE;
        }
      default:
        throw new UnsupportedOperationException(String.format("Unable to convert the value of %s and type %s to a Drill constant expression.", literal, literal.getType().getSqlTypeName()));
      }
    }
  }

  private static final TypedNullConstant createNullExpr(MinorType type) {
    return new TypedNullConstant(Types.optional(type));
  }

  public static boolean isLiteralNull(RexLiteral literal) {
    return literal.getTypeName().getName().equals("NULL");
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/sql/DrillSqlWorker.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.planner.sql;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import org.apache.calcite.config.Lex;
import org.apache.calcite.rel.rules.ProjectToWindowRule;
import org.apache.calcite.tools.FrameworkConfig;
import org.apache.calcite.tools.Frameworks;
import org.apache.calcite.tools.Planner;
import org.apache.calcite.tools.RelConversionException;
import org.apache.calcite.tools.RuleSet;
import org.apache.calcite.tools.ValidationException;

import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.ops.QueryContext;
import org.apache.drill.exec.physical.PhysicalPlan;
import org.apache.drill.exec.planner.cost.DrillCostBase;
import org.apache.drill.exec.planner.logical.DrillConstExecutor;
import org.apache.drill.exec.planner.logical.DrillRuleSets;
import org.apache.drill.exec.planner.physical.DrillDistributionTraitDef;
import org.apache.drill.exec.planner.physical.PlannerSettings;
import org.apache.drill.exec.planner.sql.handlers.AbstractSqlHandler;
import org.apache.drill.exec.planner.sql.handlers.DefaultSqlHandler;
import org.apache.drill.exec.planner.sql.handlers.ExplainHandler;
import org.apache.drill.exec.planner.sql.handlers.SetOptionHandler;
import org.apache.drill.exec.planner.sql.handlers.SqlHandlerConfig;
import org.apache.drill.exec.planner.sql.parser.DrillSqlCall;
import org.apache.drill.exec.planner.sql.parser.SqlCreateTable;
import org.apache.drill.exec.planner.sql.parser.impl.DrillParserWithCompoundIdConverter;
import org.apache.drill.exec.planner.types.DrillRelDataTypeSystem;
import org.apache.drill.exec.store.StoragePluginRegistry;
import org.apache.drill.exec.testing.ControlsInjector;
import org.apache.drill.exec.testing.ControlsInjectorFactory;
import org.apache.drill.exec.util.Pointer;
import org.apache.drill.exec.work.foreman.ForemanSetupException;
import org.apache.calcite.rel.RelCollationTraitDef;
import org.apache.calcite.rel.rules.ReduceExpressionsRule;
import org.apache.calcite.plan.ConventionTraitDef;
import org.apache.calcite.plan.RelOptCostFactory;
import org.apache.calcite.plan.RelTraitDef;
import org.apache.calcite.plan.hep.HepPlanner;
import org.apache.calcite.plan.hep.HepProgramBuilder;
import org.apache.calcite.sql.SqlNode;
import org.apache.calcite.sql.parser.SqlParseException;
import org.apache.calcite.sql.parser.SqlParser;
import org.apache.drill.exec.work.foreman.SqlUnsupportedException;
import org.apache.hadoop.security.AccessControlException;

public class DrillSqlWorker {
//  private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(DrillSqlWorker.class);
  private static final ControlsInjector injector = ControlsInjectorFactory.getInjector(DrillSqlWorker.class);

  private final Planner planner;
  private final HepPlanner hepPlanner;
  public final static int LOGICAL_RULES = 0;
  public final static int PHYSICAL_MEM_RULES = 1;
  public final static int LOGICAL_CONVERT_RULES = 2;

  private final QueryContext context;

  public DrillSqlWorker(QueryContext context) {
    final List<RelTraitDef> traitDefs = new ArrayList<RelTraitDef>();

    traitDefs.add(ConventionTraitDef.INSTANCE);
    traitDefs.add(DrillDistributionTraitDef.INSTANCE);
    traitDefs.add(RelCollationTraitDef.INSTANCE);
    this.context = context;
    RelOptCostFactory costFactory = (context.getPlannerSettings().useDefaultCosting()) ?
        null : new DrillCostBase.DrillCostFactory() ;
    int idMaxLength = (int)context.getPlannerSettings().getIdentifierMaxLength();

    FrameworkConfig config = Frameworks.newConfigBuilder() //
        .parserConfig(SqlParser.configBuilder()
            .setLex(Lex.MYSQL)
            .setIdentifierMaxLength(idMaxLength)
            .setParserFactory(DrillParserWithCompoundIdConverter.FACTORY)
            .build()) //
        .defaultSchema(context.getNewDefaultSchema()) //
        .operatorTable(context.getDrillOperatorTable()) //
        .traitDefs(traitDefs) //
        .convertletTable(new DrillConvertletTable()) //
        .context(context.getPlannerSettings()) //
        .ruleSets(getRules(context)) //
        .costFactory(costFactory) //
        .executor(new DrillConstExecutor(context.getFunctionRegistry(), context, context.getPlannerSettings()))
        .typeSystem(DrillRelDataTypeSystem.DRILL_REL_DATATYPE_SYSTEM) //
        .build();
    this.planner = Frameworks.getPlanner(config);
    HepProgramBuilder builder = new HepProgramBuilder();
    builder.addRuleClass(ReduceExpressionsRule.class);
    builder.addRuleClass(ProjectToWindowRule.class);
    this.hepPlanner = new HepPlanner(builder.build());
    hepPlanner.addRule(ReduceExpressionsRule.CALC_INSTANCE);
    hepPlanner.addRule(ProjectToWindowRule.PROJECT);
  }

  private RuleSet[] getRules(QueryContext context) {
    StoragePluginRegistry storagePluginRegistry = context.getStorage();
    RuleSet drillLogicalRules = DrillRuleSets.mergedRuleSets(
        DrillRuleSets.getDrillBasicRules(context),
        DrillRuleSets.getJoinPermRules(context),
        DrillRuleSets.getDrillUserConfigurableLogicalRules(context));
    RuleSet drillPhysicalMem = DrillRuleSets.mergedRuleSets(
        DrillRuleSets.getPhysicalRules(context),
        storagePluginRegistry.getStoragePluginRuleSet());

    // Following is used in LOPT join OPT.
    RuleSet logicalConvertRules = DrillRuleSets.mergedRuleSets(
        DrillRuleSets.getDrillBasicRules(context),
        DrillRuleSets.getDrillUserConfigurableLogicalRules(context));

    RuleSet[] allRules = new RuleSet[] {drillLogicalRules, drillPhysicalMem, logicalConvertRules};

    return allRules;
  }

  public PhysicalPlan getPlan(String sql) throws SqlParseException, ValidationException, ForemanSetupException{
    return getPlan(sql, null);
  }

  public PhysicalPlan getPlan(String sql, Pointer<String> textPlan) throws ForemanSetupException {
    final PlannerSettings ps = this.context.getPlannerSettings();

    SqlNode sqlNode;
    try {
      injector.injectChecked(context.getExecutionControls(), "sql-parsing", ForemanSetupException.class);
      sqlNode = planner.parse(sql);
    } catch (SqlParseException e) {
      throw UserException.parseError(e).build();
    }

    AbstractSqlHandler handler;
    SqlHandlerConfig config = new SqlHandlerConfig(hepPlanner, planner, context);

    // TODO: make this use path scanning or something similar.
    switch(sqlNode.getKind()){
    case EXPLAIN:
      handler = new ExplainHandler(config);
      break;
    case SET_OPTION:
      handler = new SetOptionHandler(context);
      break;
    case OTHER:
      if(sqlNode instanceof SqlCreateTable) {
        handler = ((DrillSqlCall)sqlNode).getSqlHandler(config, textPlan);
        break;
      }

      if (sqlNode instanceof DrillSqlCall) {
        handler = ((DrillSqlCall)sqlNode).getSqlHandler(config);
        break;
      }
      // fallthrough
    default:
      handler = new DefaultSqlHandler(config, textPlan);
    }

    try {
      return handler.getPlan(sqlNode);
    } catch(ValidationException e) {
      String errorMessage = e.getCause() != null ? e.getCause().getMessage() : e.getMessage();
      throw UserException.parseError(e).message(errorMessage).build();
    } catch (AccessControlException e) {
      throw UserException.permissionError(e).build();
    } catch(SqlUnsupportedException e) {
      throw UserException.unsupportedError(e)
          .build();
    } catch (IOException | RelConversionException e) {
      throw new QueryInputException("Failure handling SQL.", e);
    }
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/sql/SchemaUtilites.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.planner.sql;

import com.google.common.base.Joiner;
import com.google.common.base.Strings;
import com.google.common.collect.Lists;
import org.apache.calcite.schema.SchemaPlus;
import org.apache.calcite.tools.ValidationException;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.store.AbstractSchema;

import java.util.Collections;
import java.util.List;

public class SchemaUtilites {
  public static final Joiner SCHEMA_PATH_JOINER = Joiner.on(".").skipNulls();

  /**
   * Search and return schema with given schemaPath. First search in schema tree starting from defaultSchema,
   * if not found search starting from rootSchema. Root schema tree is derived from the defaultSchema reference.
   *
   * @param defaultSchema Reference to the default schema in complete schema tree.
   * @param schemaPath Schema path to search.
   * @return SchemaPlus object.
   */
  public static SchemaPlus findSchema(final SchemaPlus defaultSchema, final List<String> schemaPath) {
    if (schemaPath.size() == 0) {
      return defaultSchema;
    }

    SchemaPlus schema;
    if ((schema = searchSchemaTree(defaultSchema, schemaPath)) != null) {
      return schema;
    }

    SchemaPlus rootSchema = defaultSchema;
    while(rootSchema.getParentSchema() != null) {
      rootSchema = rootSchema.getParentSchema();
    }

    if (rootSchema != defaultSchema &&
        (schema = searchSchemaTree(rootSchema, schemaPath)) != null) {
      return schema;
    }

    return null;
  }

  /**
   * Same utility as {@link #findSchema(SchemaPlus, List)} except the search schema path given here is complete path
   * instead of list. Use "." separator to divided the schema into nested schema names.
   * @param defaultSchema
   * @param schemaPath
   * @return
   * @throws ValidationException
   */
  public static SchemaPlus findSchema(final SchemaPlus defaultSchema, final String schemaPath) {
    final List<String> schemaPathAsList = Lists.newArrayList(schemaPath.split("\\."));
    return findSchema(defaultSchema, schemaPathAsList);
  }

  /** Utility method to search for schema path starting from the given <i>schema</i> reference */
  private static SchemaPlus searchSchemaTree(SchemaPlus schema, final List<String> schemaPath) {
    for (String schemaName : schemaPath) {
      schema = schema.getSubSchema(schemaName);
      if (schema == null) {
        return null;
      }
    }
    return schema;
  }

  /**
   * Returns true if the given <i>schema</i> is root schema. False otherwise.
   * @param schema
   * @return
   */
  public static boolean isRootSchema(SchemaPlus schema) {
    return schema.getParentSchema() == null;
  }

  /**
   * Unwrap given <i>SchemaPlus</i> instance as Drill schema instance (<i>AbstractSchema</i>). Once unwrapped, return
   * default schema from <i>AbstractSchema</i>. If the given schema is not an instance of <i>AbstractSchema</i> a
   * {@link UserException} is thrown.
   */
  public static AbstractSchema unwrapAsDrillSchemaInstance(SchemaPlus schemaPlus)  {
    try {
      return schemaPlus.unwrap(AbstractSchema.class).getDefaultSchema();
    } catch (ClassCastException e) {
      throw UserException.validationError(e)
          .message("Schema [%s] is not a Drill schema.", getSchemaPath(schemaPlus))
          .build();
    }
  }

  /** Utility method to get the schema path for given schema instance. */
  public static String getSchemaPath(SchemaPlus schema) {
    return SCHEMA_PATH_JOINER.join(getSchemaPathAsList(schema));
  }

  /** Utility method to get the schema path as list for given schema instance. */
  public static List<String> getSchemaPathAsList(SchemaPlus schema) {
    if (isRootSchema(schema)) {
      return Collections.EMPTY_LIST;
    }

    List<String> path = Lists.newArrayListWithCapacity(5);
    while(schema != null) {
      final String name = schema.getName();
      if (!Strings.isNullOrEmpty(name)) {
        path.add(schema.getName());
      }
      schema = schema.getParentSchema();
    }

    return Lists.reverse(path);
  }

  /** Utility method to throw {@link UserException} with context information */
  public static void throwSchemaNotFoundException(final SchemaPlus defaultSchema, final String givenSchemaPath) {
    throw UserException.validationError()
        .message("Schema [%s] is not valid with respect to either root schema or current default schema.",
            givenSchemaPath)
        .addContext("Current default schema: ",
            isRootSchema(defaultSchema) ? "No default schema selected" : getSchemaPath(defaultSchema))
        .build();
  }

  /**
   * Given reference to default schema in schema tree, search for schema with given <i>schemaPath</i>. Once a schema is
   * found resolve it into a mutable <i>AbstractDrillSchema</i> instance. A {@link UserException} is throws when:
   *   1. No schema for given <i>schemaPath</i> is found,
   *   2. Schema found for given <i>schemaPath</i> is a root schema
   *   3. Resolved schema is not a mutable schema.
   * @param defaultSchema
   * @param schemaPath
   * @return
   */
  public static AbstractSchema resolveToMutableDrillSchema(final SchemaPlus defaultSchema, List<String> schemaPath) {
    final SchemaPlus schema = findSchema(defaultSchema, schemaPath);

    if (schema == null) {
      throwSchemaNotFoundException(defaultSchema, SCHEMA_PATH_JOINER.join(schemaPath));
    }

    if (isRootSchema(schema)) {
      throw UserException.parseError()
          .message("Root schema is immutable. Creating or dropping tables/views is not allowed in root schema." +
              "Select a schema using 'USE schema' command.")
          .build();
    }

    final AbstractSchema drillSchema = unwrapAsDrillSchemaInstance(schema);
    if (!drillSchema.isMutable()) {
      throw UserException.parseError()
          .message("Unable to create or drop tables/views. Schema [%s] is immutable.", getSchemaPath(schema))
          .build();
    }

    return drillSchema;
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/sql/handlers/CreateTableHandler.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.planner.sql.handlers;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import com.google.common.collect.ImmutableList;
import com.google.common.collect.Lists;
import org.apache.calcite.plan.RelOptCluster;
import org.apache.calcite.rel.RelNode;
import org.apache.calcite.rel.type.RelDataType;
import org.apache.calcite.rel.type.RelDataTypeField;
import org.apache.calcite.rex.RexBuilder;
import org.apache.calcite.rex.RexInputRef;
import org.apache.calcite.rex.RexNode;
import org.apache.calcite.rex.RexUtil;
import org.apache.calcite.sql.SqlNode;
import org.apache.calcite.tools.RelConversionException;
import org.apache.calcite.tools.ValidationException;

import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.physical.PhysicalPlan;
import org.apache.drill.exec.physical.base.PhysicalOperator;
import org.apache.drill.exec.planner.logical.DrillRel;
import org.apache.drill.exec.planner.logical.DrillScreenRel;
import org.apache.drill.exec.planner.logical.DrillWriterRel;
import org.apache.drill.exec.planner.physical.Prel;
import org.apache.drill.exec.planner.physical.ProjectAllowDupPrel;
import org.apache.drill.exec.planner.physical.ProjectPrel;
import org.apache.drill.exec.planner.physical.WriterPrel;
import org.apache.drill.exec.planner.physical.visitor.BasePrelVisitor;
import org.apache.drill.exec.planner.sql.DrillSqlOperator;
import org.apache.drill.exec.planner.sql.SchemaUtilites;
import org.apache.drill.exec.planner.sql.parser.SqlCreateTable;
import org.apache.drill.exec.store.AbstractSchema;
import org.apache.drill.exec.util.Pointer;
import org.apache.drill.exec.work.foreman.ForemanSetupException;
import org.apache.drill.exec.work.foreman.SqlUnsupportedException;

public class CreateTableHandler extends DefaultSqlHandler {
  public CreateTableHandler(SqlHandlerConfig config, Pointer<String> textPlan) {
    super(config, textPlan);
  }

  @Override
  public PhysicalPlan getPlan(SqlNode sqlNode) throws ValidationException, RelConversionException, IOException, ForemanSetupException {
    SqlCreateTable sqlCreateTable = unwrap(sqlNode, SqlCreateTable.class);
    final String newTblName = sqlCreateTable.getName();

    final ConvertedRelNode convertedRelNode = validateAndConvert(sqlCreateTable.getQuery());
    final RelDataType validatedRowType = convertedRelNode.getValidatedRowType();
    final RelNode queryRelNode = convertedRelNode.getConvertedNode();


    final RelNode newTblRelNode =
        SqlHandlerUtil.resolveNewTableRel(false, sqlCreateTable.getFieldNames(), validatedRowType, queryRelNode);


    final AbstractSchema drillSchema =
        SchemaUtilites.resolveToMutableDrillSchema(context.getNewDefaultSchema(), sqlCreateTable.getSchemaPath());
    final String schemaPath = drillSchema.getFullSchemaName();

    if (SqlHandlerUtil.getTableFromSchema(drillSchema, newTblName) != null) {
      throw UserException.validationError()
          .message("A table or view with given name [%s] already exists in schema [%s]", newTblName, schemaPath)
          .build();
    }

    final RelNode newTblRelNodeWithPCol = SqlHandlerUtil.qualifyPartitionCol(newTblRelNode, sqlCreateTable.getPartitionColumns());

    log("Optiq Logical", newTblRelNodeWithPCol);

    // Convert the query to Drill Logical plan and insert a writer operator on top.
    DrillRel drel = convertToDrel(newTblRelNodeWithPCol, drillSchema, newTblName, sqlCreateTable.getPartitionColumns(), newTblRelNode.getRowType());
    log("Drill Logical", drel);
    Prel prel = convertToPrel(drel, newTblRelNode.getRowType(), sqlCreateTable.getPartitionColumns());
    log("Drill Physical", prel);
    PhysicalOperator pop = convertToPop(prel);
    PhysicalPlan plan = convertToPlan(pop);
    log("Drill Plan", plan);

    return plan;
  }

  private DrillRel convertToDrel(RelNode relNode, AbstractSchema schema, String tableName, List<String> partitionColumns, RelDataType queryRowType)
      throws RelConversionException, SqlUnsupportedException {

    final DrillRel convertedRelNode = convertToDrel(relNode);

    DrillWriterRel writerRel = new DrillWriterRel(convertedRelNode.getCluster(), convertedRelNode.getTraitSet(),
        convertedRelNode, schema.createNewTable(tableName, partitionColumns));
    return new DrillScreenRel(writerRel.getCluster(), writerRel.getTraitSet(), writerRel);
  }

  private Prel convertToPrel(RelNode drel, RelDataType inputRowType, List<String> partitionColumns)
      throws RelConversionException, SqlUnsupportedException {
    Prel prel = convertToPrel(drel);

    prel = prel.accept(new ProjectForWriterVisitor(inputRowType, partitionColumns), null);

    return prel;
  }

  /**
   * A PrelVisitor which will insert a project under Writer.
   *
   * For CTAS : create table t1 partition by (con_A) select * from T1;
   *   A Project with Item expr will be inserted, in addition to *.  We need insert another Project to remove
   *   this additional expression.
   *
   * In addition, to make execution's implementation easier,  a special field is added to Project :
   *     PARTITION_COLUMN_IDENTIFIER = newPartitionValue(Partition_colA)
   *                                    || newPartitionValue(Partition_colB)
   *                                    || ...
   *                                    || newPartitionValue(Partition_colN).
   */
  private class ProjectForWriterVisitor extends BasePrelVisitor<Prel, Void, RuntimeException> {

    private final RelDataType queryRowType;
    private final List<String> partitionColumns;

    ProjectForWriterVisitor(RelDataType queryRowType, List<String> partitionColumns) {
      this.queryRowType = queryRowType;
      this.partitionColumns = partitionColumns;
    }

    @Override
    public Prel visitPrel(Prel prel, Void value) throws RuntimeException {
      List<RelNode> children = Lists.newArrayList();
      for(Prel child : prel){
        child = child.accept(this, null);
        children.add(child);
      }

      return (Prel) prel.copy(prel.getTraitSet(), children);

    }

    @Override
    public Prel visitWriter(WriterPrel prel, Void value) throws RuntimeException {

      final Prel child = ((Prel)prel.getInput()).accept(this, null);

      final RelDataType childRowType = child.getRowType();

      final RelOptCluster cluster = prel.getCluster();

      final List<RexNode> exprs = Lists.newArrayListWithExpectedSize(queryRowType.getFieldCount() + 1);
      final List<String> fieldnames = new ArrayList<String>(queryRowType.getFieldNames());

      for (final RelDataTypeField field : queryRowType.getFieldList()) {
        exprs.add(RexInputRef.of(field.getIndex(), queryRowType));
      }

      // No partition columns.
      if (partitionColumns.size() == 0) {
        final ProjectPrel projectUnderWriter = new ProjectAllowDupPrel(cluster,
            cluster.getPlanner().emptyTraitSet().plus(Prel.DRILL_PHYSICAL), child, exprs, queryRowType);

        return (Prel) prel.copy(projectUnderWriter.getTraitSet(),
            Collections.singletonList( (RelNode) projectUnderWriter));
      } else {
        // find list of partiiton columns.
        final List<RexNode> partitionColumnExprs = Lists.newArrayListWithExpectedSize(partitionColumns.size());
        for (final String colName : partitionColumns) {
          final RelDataTypeField field = childRowType.getField(colName, false, false);

          if (field == null) {
            throw UserException.validationError()
                .message("Partition column %s is not in the SELECT list of CTAS!", colName)
                .build();
          }

          partitionColumnExprs.add(RexInputRef.of(field.getIndex(), childRowType));
        }

        // Add partition column comparator to Project's field name list.
        fieldnames.add(WriterPrel.PARTITION_COMPARATOR_FIELD);

        // Add partition column comparator to Project's expression list.
        final RexNode partionColComp = createPartitionColComparator(prel.getCluster().getRexBuilder(), partitionColumnExprs);
        exprs.add(partionColComp);


        final RelDataType rowTypeWithPCComp = RexUtil.createStructType(cluster.getTypeFactory(), exprs, fieldnames);

        final ProjectPrel projectUnderWriter = new ProjectAllowDupPrel(cluster,
            cluster.getPlanner().emptyTraitSet().plus(Prel.DRILL_PHYSICAL), child, exprs, rowTypeWithPCComp);

        return (Prel) prel.copy(projectUnderWriter.getTraitSet(),
            Collections.singletonList( (RelNode) projectUnderWriter));
      }
    }

  }

  private RexNode createPartitionColComparator(final RexBuilder rexBuilder, List<RexNode> inputs) {
    final DrillSqlOperator op = new DrillSqlOperator(WriterPrel.PARTITION_COMPARATOR_FUNC, 1, true);

    final List<RexNode> compFuncs = Lists.newArrayListWithExpectedSize(inputs.size());

    for (final RexNode input : inputs) {
      compFuncs.add(rexBuilder.makeCall(op, ImmutableList.of(input)));
    }

    return RexUtil.composeDisjunction(rexBuilder, compFuncs, false);
  }

}

File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/sql/handlers/DefaultSqlHandler.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.planner.sql.handlers;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

import org.apache.calcite.plan.RelOptPlanner;
import org.apache.calcite.plan.RelOptUtil;
import org.apache.calcite.plan.RelTraitSet;
import org.apache.calcite.plan.hep.HepPlanner;
import org.apache.calcite.rel.RelNode;
import org.apache.calcite.plan.hep.HepMatchOrder;
import org.apache.calcite.plan.hep.HepProgram;
import org.apache.calcite.plan.hep.HepProgramBuilder;
import org.apache.calcite.rel.RelShuttleImpl;
import org.apache.calcite.rel.core.Join;
import org.apache.calcite.rel.core.RelFactories;
import org.apache.calcite.rel.core.TableFunctionScan;
import org.apache.calcite.rel.core.TableScan;
import org.apache.calcite.rel.logical.LogicalValues;
import org.apache.calcite.rel.metadata.CachingRelMetadataProvider;
import org.apache.calcite.rel.metadata.ChainedRelMetadataProvider;
import org.apache.calcite.rel.metadata.RelMetadataProvider;
import org.apache.calcite.rel.rules.JoinToMultiJoinRule;
import org.apache.calcite.rel.rules.LoptOptimizeJoinRule;
import org.apache.calcite.rel.rules.ProjectRemoveRule;
import org.apache.calcite.rel.type.RelDataType;
import org.apache.calcite.rex.RexBuilder;
import org.apache.calcite.rex.RexNode;
import org.apache.calcite.rex.RexUtil;
import org.apache.calcite.sql.SqlExplainLevel;
import org.apache.calcite.sql.SqlNode;
import org.apache.calcite.sql.TypedSqlNode;
import org.apache.calcite.sql.validate.SqlValidatorUtil;
import org.apache.calcite.tools.Planner;
import org.apache.calcite.tools.RelConversionException;
import org.apache.calcite.tools.ValidationException;
import org.apache.drill.common.JSONOptions;
import org.apache.drill.common.logical.PlanProperties;
import org.apache.drill.common.logical.PlanProperties.Generator.ResultMode;
import org.apache.drill.common.logical.PlanProperties.PlanPropertiesBuilder;
import org.apache.drill.common.logical.PlanProperties.PlanType;
import org.apache.drill.exec.ExecConstants;
import org.apache.drill.exec.ops.QueryContext;
import org.apache.drill.exec.physical.PhysicalPlan;
import org.apache.drill.exec.physical.base.AbstractPhysicalVisitor;
import org.apache.drill.exec.physical.base.PhysicalOperator;
import org.apache.drill.exec.physical.impl.join.JoinUtils;
import org.apache.drill.exec.planner.cost.DrillDefaultRelMetadataProvider;
import org.apache.drill.exec.planner.logical.DrillJoinRel;
import org.apache.drill.exec.planner.logical.DrillProjectRel;
import org.apache.drill.exec.planner.logical.DrillRel;
import org.apache.drill.exec.planner.logical.DrillRelFactories;
import org.apache.drill.exec.planner.logical.DrillScreenRel;
import org.apache.drill.exec.planner.logical.DrillStoreRel;
import org.apache.drill.exec.planner.logical.PreProcessLogicalRel;
import org.apache.drill.exec.planner.physical.DrillDistributionTrait;
import org.apache.drill.exec.planner.physical.PhysicalPlanCreator;
import org.apache.drill.exec.planner.physical.PlannerSettings;
import org.apache.drill.exec.planner.physical.Prel;
import org.apache.drill.exec.planner.physical.explain.PrelSequencer;
import org.apache.drill.exec.planner.physical.visitor.ComplexToJsonPrelVisitor;
import org.apache.drill.exec.planner.physical.visitor.ExcessiveExchangeIdentifier;
import org.apache.drill.exec.planner.physical.visitor.FinalColumnReorderer;
import org.apache.drill.exec.planner.physical.visitor.InsertLocalExchangeVisitor;
import org.apache.drill.exec.planner.physical.visitor.JoinPrelRenameVisitor;
import org.apache.drill.exec.planner.physical.visitor.MemoryEstimationVisitor;
import org.apache.drill.exec.planner.physical.visitor.RelUniqifier;
import org.apache.drill.exec.planner.physical.visitor.RewriteProjectToFlatten;
import org.apache.drill.exec.planner.physical.visitor.SelectionVectorPrelVisitor;
import org.apache.drill.exec.planner.physical.visitor.SplitUpComplexExpressions;
import org.apache.drill.exec.planner.physical.visitor.StarColumnConverter;
import org.apache.drill.exec.planner.physical.visitor.SwapHashJoinVisitor;
import org.apache.drill.exec.planner.sql.DrillSqlWorker;
import org.apache.drill.exec.planner.sql.parser.UnsupportedOperatorsVisitor;
import org.apache.drill.exec.server.options.OptionManager;
import org.apache.drill.exec.server.options.OptionValue;
import org.apache.drill.exec.util.Pointer;
import org.apache.drill.exec.work.foreman.ForemanSetupException;
import org.apache.drill.exec.work.foreman.SqlUnsupportedException;
import org.apache.drill.exec.work.foreman.UnsupportedRelOperatorException;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.google.common.base.Preconditions;
import com.google.common.collect.Lists;

public class DefaultSqlHandler extends AbstractSqlHandler {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(DefaultSqlHandler.class);

  protected final SqlHandlerConfig config;
  protected final QueryContext context;
  protected final HepPlanner hepPlanner;
  protected final Planner planner;
  private Pointer<String> textPlan;
  private final long targetSliceSize;

  public DefaultSqlHandler(SqlHandlerConfig config) {
    this(config, null);
  }

  public DefaultSqlHandler(SqlHandlerConfig config, Pointer<String> textPlan) {
    super();
    this.planner = config.getPlanner();
    this.context = config.getContext();
    this.hepPlanner = config.getHepPlanner();
    this.config = config;
    this.textPlan = textPlan;
    targetSliceSize = context.getOptions().getOption(ExecConstants.SLICE_TARGET).num_val;
  }

  protected void log(String name, RelNode node) {
    if (logger.isDebugEnabled()) {
      logger.debug(name + " : \n" + RelOptUtil.toString(node, SqlExplainLevel.ALL_ATTRIBUTES));
    }
  }

  protected void log(String name, Prel node) {
    String plan = PrelSequencer.printWithIds(node, SqlExplainLevel.ALL_ATTRIBUTES);
    if(textPlan != null){
      textPlan.value = plan;
    }

    if (logger.isDebugEnabled()) {
      logger.debug(name + " : \n" + plan);
    }
  }

  protected void log(String name, PhysicalPlan plan) throws JsonProcessingException {
    if (logger.isDebugEnabled()) {
      String planText = plan.unparse(context.getConfig().getMapper().writer());
      logger.debug(name + " : \n" + planText);
    }
  }


  @Override
  public PhysicalPlan getPlan(SqlNode sqlNode) throws ValidationException, RelConversionException, IOException, ForemanSetupException {
    final ConvertedRelNode convertedRelNode = validateAndConvert(sqlNode);
    final RelDataType validatedRowType = convertedRelNode.getValidatedRowType();
    final RelNode queryRelNode = convertedRelNode.getConvertedNode();

    log("Optiq Logical", queryRelNode);
    DrillRel drel = convertToDrel(queryRelNode, validatedRowType);

    log("Drill Logical", drel);
    Prel prel = convertToPrel(drel);
    log("Drill Physical", prel);
    PhysicalOperator pop = convertToPop(prel);
    PhysicalPlan plan = convertToPlan(pop);
    log("Drill Plan", plan);
    return plan;
  }


  /**
   * Rewrite the parse tree. Used before validating the parse tree. Useful if a particular statement needs to converted
   * into another statement.
   *
   * @param node
   * @return Rewritten sql parse tree
   * @throws RelConversionException
   */
  protected SqlNode rewrite(SqlNode node) throws RelConversionException, ForemanSetupException {
    return node;
  }

  protected ConvertedRelNode validateAndConvert(SqlNode sqlNode) throws ForemanSetupException, RelConversionException, ValidationException {
    final SqlNode rewrittenSqlNode = rewrite(sqlNode);
    final TypedSqlNode validatedTypedSqlNode = validateNode(rewrittenSqlNode);
    final SqlNode validated = validatedTypedSqlNode.getSqlNode();

    RelNode rel = convertToRel(validated);
    rel = preprocessNode(rel);

    return new ConvertedRelNode(rel, validatedTypedSqlNode.getType());
  }

  /**
   *  Given a relNode tree for SELECT statement, convert to Drill Logical RelNode tree.
   * @param relNode
   * @return
   * @throws SqlUnsupportedException
   * @throws RelConversionException
   */
  protected DrillRel convertToDrel(RelNode relNode) throws SqlUnsupportedException, RelConversionException {
    try {
      final DrillRel convertedRelNode;

      if (! context.getPlannerSettings().isHepJoinOptEnabled()) {
        convertedRelNode = (DrillRel) logicalPlanningVolcano(relNode);
      } else {
        convertedRelNode = (DrillRel) logicalPlanningVolcanoAndLopt(relNode);
      }

      if (convertedRelNode instanceof DrillStoreRel) {
        throw new UnsupportedOperationException();
      } else {

        // If the query contains a limit 0 clause, disable distributed mode since it is overkill for determining schema.
        if (FindLimit0Visitor.containsLimit0(convertedRelNode)) {
          context.getPlannerSettings().forceSingleMode();
        }

        return convertedRelNode;
      }
    } catch (RelOptPlanner.CannotPlanException ex) {
      logger.error(ex.getMessage());

      if(JoinUtils.checkCartesianJoin(relNode, new ArrayList<Integer>(), new ArrayList<Integer>())) {
        throw new UnsupportedRelOperatorException("This query cannot be planned possibly due to either a cartesian join or an inequality join");
      } else {
        throw ex;
      }
    }
  }

  /**
   * Return Drill Logical RelNode tree for a SELECT statement, when it is executed / explained directly.
   *
   * @param relNode : root RelNode corresponds to Calcite Logical RelNode.
   * @param validatedRowType : the rowType for the final field names. A rename project may be placed on top of the root.
   * @return
   * @throws RelConversionException
   * @throws SqlUnsupportedException
   */
  protected DrillRel convertToDrel(RelNode relNode, RelDataType validatedRowType) throws RelConversionException, SqlUnsupportedException {
    final DrillRel convertedRelNode = convertToDrel(relNode);

    // Put a non-trivial topProject to ensure the final output field name is preserved, when necessary.
    DrillRel topPreservedNameProj = addRenamedProject((DrillRel) convertedRelNode, validatedRowType);
    return new DrillScreenRel(topPreservedNameProj.getCluster(), topPreservedNameProj.getTraitSet(),
        topPreservedNameProj);
  }


  protected Prel convertToPrel(RelNode drel) throws RelConversionException, SqlUnsupportedException {
    Preconditions.checkArgument(drel.getConvention() == DrillRel.DRILL_LOGICAL);
    RelTraitSet traits = drel.getTraitSet().plus(Prel.DRILL_PHYSICAL).plus(DrillDistributionTrait.SINGLETON);
    Prel phyRelNode;
    try {
      phyRelNode = (Prel) planner.transform(DrillSqlWorker.PHYSICAL_MEM_RULES, traits, drel);
    } catch (RelOptPlanner.CannotPlanException ex) {
      logger.error(ex.getMessage());

      if(JoinUtils.checkCartesianJoin(drel, new ArrayList<Integer>(), new ArrayList<Integer>())) {
        throw new UnsupportedRelOperatorException("This query cannot be planned possibly due to either a cartesian join or an inequality join");
      } else {
        throw ex;
      }
    }

    OptionManager queryOptions = context.getOptions();

    if (context.getPlannerSettings().isMemoryEstimationEnabled()
      && !MemoryEstimationVisitor.enoughMemory(phyRelNode, queryOptions, context.getActiveEndpoints().size())) {
      log("Not enough memory for this plan", phyRelNode);
      logger.debug("Re-planning without hash operations.");

      queryOptions.setOption(OptionValue.createBoolean(OptionValue.OptionType.QUERY, PlannerSettings.HASHJOIN.getOptionName(), false));
      queryOptions.setOption(OptionValue.createBoolean(OptionValue.OptionType.QUERY, PlannerSettings.HASHAGG.getOptionName(), false));

      try {
        phyRelNode = (Prel) planner.transform(DrillSqlWorker.PHYSICAL_MEM_RULES, traits, drel);
      } catch (RelOptPlanner.CannotPlanException ex) {
        logger.error(ex.getMessage());

        if(JoinUtils.checkCartesianJoin(drel, new ArrayList<Integer>(), new ArrayList<Integer>())) {
          throw new UnsupportedRelOperatorException("This query cannot be planned possibly due to either a cartesian join or an inequality join");
        } else {
          throw ex;
        }
      }
    }

    /*  The order of the following transformation is important */

    /*
     * 0.) For select * from join query, we need insert project on top of scan and a top project just
     * under screen operator. The project on top of scan will rename from * to T1*, while the top project
     * will rename T1* to *, before it output the final result. Only the top project will allow
     * duplicate columns, since user could "explicitly" ask for duplicate columns ( select *, col, *).
     * The rest of projects will remove the duplicate column when we generate POP in json format.
     */
    phyRelNode = StarColumnConverter.insertRenameProject(phyRelNode);

    /*
     * 1.)
     * Join might cause naming conflicts from its left and right child.
     * In such case, we have to insert Project to rename the conflicting names.
     */
    phyRelNode = JoinPrelRenameVisitor.insertRenameProject(phyRelNode);

    /*
     * 1.1) Swap left / right for INNER hash join, if left's row count is < (1 + margin) right's row count.
     * We want to have smaller dataset on the right side, since hash table builds on right side.
     */
    if (context.getPlannerSettings().isHashJoinSwapEnabled()) {
      phyRelNode = SwapHashJoinVisitor.swapHashJoin(phyRelNode, new Double(context.getPlannerSettings().getHashJoinSwapMarginFactor()));
    }

    /*
     * 1.2) Break up all expressions with complex outputs into their own project operations
     */
    phyRelNode = ((Prel) phyRelNode).accept(new SplitUpComplexExpressions(planner.getTypeFactory(), context.getDrillOperatorTable(), context.getPlannerSettings().functionImplementationRegistry), null);

    /*
     * 1.3) Projections that contain reference to flatten are rewritten as Flatten operators followed by Project
     */
    phyRelNode = ((Prel) phyRelNode).accept(new RewriteProjectToFlatten(planner.getTypeFactory(), context.getDrillOperatorTable()), null);

    /*
     * 2.)
     * Since our operators work via names rather than indices, we have to make to reorder any
     * output before we return data to the user as we may have accidentally shuffled things.
     * This adds a trivial project to reorder columns prior to output.
     */
    phyRelNode = FinalColumnReorderer.addFinalColumnOrdering(phyRelNode);

    /*
     * 3.)
     * If two fragments are both estimated to be parallelization one, remove the exchange
     * separating them
     */
    phyRelNode = ExcessiveExchangeIdentifier.removeExcessiveEchanges(phyRelNode, targetSliceSize);


    /* 4.)
     * Add ProducerConsumer after each scan if the option is set
     * Use the configured queueSize
     */
    /* DRILL-1617 Disabling ProducerConsumer as it produces incorrect results
    if (context.getOptions().getOption(PlannerSettings.PRODUCER_CONSUMER.getOptionName()).bool_val) {
      long queueSize = context.getOptions().getOption(PlannerSettings.PRODUCER_CONSUMER_QUEUE_SIZE.getOptionName()).num_val;
      phyRelNode = ProducerConsumerPrelVisitor.addProducerConsumerToScans(phyRelNode, (int) queueSize);
    }
    */


    /* 5.)
     * if the client does not support complex types (Map, Repeated)
     * insert a project which which would convert
     */
    if (!context.getSession().isSupportComplexTypes()) {
      logger.debug("Client does not support complex types, add ComplexToJson operator.");
      phyRelNode = ComplexToJsonPrelVisitor.addComplexToJsonPrel(phyRelNode);
    }


    /* 6.)
     * Insert LocalExchange (mux and/or demux) nodes
     */
    phyRelNode = InsertLocalExchangeVisitor.insertLocalExchanges(phyRelNode, queryOptions);


    /* 7.)
     * Next, we add any required selection vector removers given the supported encodings of each
     * operator. This will ultimately move to a new trait but we're managing here for now to avoid
     * introducing new issues in planning before the next release
     */
    phyRelNode = SelectionVectorPrelVisitor.addSelectionRemoversWhereNecessary(phyRelNode);

    /* 8.)
     * Finally, Make sure that the no rels are repeats.
     * This could happen in the case of querying the same table twice as Optiq may canonicalize these.
     */
    phyRelNode = RelUniqifier.uniqifyGraph(phyRelNode);

    return phyRelNode;
  }

  protected PhysicalOperator convertToPop(Prel prel) throws IOException {
    PhysicalPlanCreator creator = new PhysicalPlanCreator(context, PrelSequencer.getIdMap(prel));
    PhysicalOperator op = prel.getPhysicalOperator(creator);
    return op;
  }

  protected PhysicalPlan convertToPlan(PhysicalOperator op) {
    PlanPropertiesBuilder propsBuilder = PlanProperties.builder();
    propsBuilder.type(PlanType.APACHE_DRILL_PHYSICAL);
    propsBuilder.version(1);
    propsBuilder.options(new JSONOptions(context.getOptions().getOptionList()));
    propsBuilder.resultMode(ResultMode.EXEC);
    propsBuilder.generator(this.getClass().getSimpleName(), "");
    return new PhysicalPlan(propsBuilder.build(), getPops(op));
  }

  public static List<PhysicalOperator> getPops(PhysicalOperator root) {
    List<PhysicalOperator> ops = Lists.newArrayList();
    PopCollector c = new PopCollector();
    root.accept(c, ops);
    return ops;
  }

  private static class PopCollector extends
      AbstractPhysicalVisitor<Void, Collection<PhysicalOperator>, RuntimeException> {

    @Override
    public Void visitOp(PhysicalOperator op, Collection<PhysicalOperator> collection) throws RuntimeException {
      collection.add(op);
      for (PhysicalOperator o : op) {
        o.accept(this, collection);
      }
      return null;
    }

  }

  private TypedSqlNode validateNode(SqlNode sqlNode) throws ValidationException, RelConversionException, ForemanSetupException {
    TypedSqlNode typedSqlNode = planner.validateAndGetType(sqlNode);

    SqlNode sqlNodeValidated = typedSqlNode.getSqlNode();

    // Check if the unsupported functionality is used
    UnsupportedOperatorsVisitor visitor = UnsupportedOperatorsVisitor.createVisitor(context);
    try {
      sqlNodeValidated.accept(visitor);
    } catch (UnsupportedOperationException ex) {
      // If the exception due to the unsupported functionalities
      visitor.convertException();

      // If it is not, let this exception move forward to higher logic
      throw ex;
    }

    return typedSqlNode;
  }

  private RelNode convertToRel(SqlNode node) throws RelConversionException {
    RelNode convertedNode = planner.convert(node);
    hepPlanner.setRoot(convertedNode);
    RelNode rel = hepPlanner.findBestExp();

    return rel;
  }

  private RelNode preprocessNode(RelNode rel) throws SqlUnsupportedException {
    /*
     * Traverse the tree to do the following pre-processing tasks: 1. replace the convert_from, convert_to function to
     * actual implementations Eg: convert_from(EXPR, 'JSON') be converted to convert_fromjson(EXPR); TODO: Ideally all
     * function rewrites would move here instead of DrillOptiq.
     *
     * 2. see where the tree contains unsupported functions; throw SqlUnsupportedException if there is any.
     */

    PreProcessLogicalRel visitor = PreProcessLogicalRel.createVisitor(planner.getTypeFactory(),
        context.getDrillOperatorTable());
    try {
      rel = rel.accept(visitor);
    } catch (UnsupportedOperationException ex) {
      visitor.convertException();
      throw ex;
    }

    return rel;
  }

  private DrillRel addRenamedProject(DrillRel rel, RelDataType validatedRowType) {
    RelDataType t = rel.getRowType();

    RexBuilder b = rel.getCluster().getRexBuilder();
    List<RexNode> projections = Lists.newArrayList();
    int projectCount = t.getFieldList().size();

    for (int i =0; i < projectCount; i++) {
      projections.add(b.makeInputRef(rel, i));
    }

    final List<String> fieldNames2 = SqlValidatorUtil.uniquify(validatedRowType.getFieldNames(), SqlValidatorUtil.F_SUGGESTER2);

    RelDataType newRowType = RexUtil.createStructType(rel.getCluster().getTypeFactory(), projections, fieldNames2);

    DrillProjectRel topProj = DrillProjectRel.create(rel.getCluster(), rel.getTraitSet(), rel, projections, newRowType);

    if (ProjectRemoveRule.isTrivial(topProj, true)) {
      return rel;
    } else{
      return topProj;
    }
  }


  private RelNode logicalPlanningVolcano(RelNode relNode) throws RelConversionException, SqlUnsupportedException {
    return planner.transform(DrillSqlWorker.LOGICAL_RULES, relNode.getTraitSet().plus(DrillRel.DRILL_LOGICAL), relNode);
  }

  /**
   * Do logical planning using both VolcanoPlanner and LOPT HepPlanner.
   * @param relNode
   * @return
   * @throws RelConversionException
   * @throws SqlUnsupportedException
   */
  private RelNode logicalPlanningVolcanoAndLopt(RelNode relNode) throws RelConversionException, SqlUnsupportedException {

    final RelNode convertedRelNode = planner.transform(DrillSqlWorker.LOGICAL_CONVERT_RULES, relNode.getTraitSet().plus(DrillRel.DRILL_LOGICAL), relNode);
    log("VolCalciteRel", convertedRelNode);

    final RelNode loptNode = getLoptJoinOrderTree(
        convertedRelNode,
        DrillJoinRel.class,
        DrillRelFactories.DRILL_LOGICAL_JOIN_FACTORY,
        DrillRelFactories.DRILL_LOGICAL_FILTER_FACTORY,
        DrillRelFactories.DRILL_LOGICAL_PROJECT_FACTORY);

    log("HepCalciteRel", loptNode);

    return loptNode;
  }


  /**
   * Appy Join Order Optimizations using Hep Planner.
   */
  private RelNode getLoptJoinOrderTree(RelNode root,
                                      Class<? extends Join> joinClass,
                                             RelFactories.JoinFactory joinFactory,
                                             RelFactories.FilterFactory filterFactory,
                                             RelFactories.ProjectFactory projectFactory) {
    final HepProgramBuilder hepPgmBldr = new HepProgramBuilder()
        .addMatchOrder(HepMatchOrder.BOTTOM_UP)
        .addRuleInstance(new JoinToMultiJoinRule(joinClass))
        .addRuleInstance(new LoptOptimizeJoinRule(joinFactory, projectFactory, filterFactory))
        .addRuleInstance(ProjectRemoveRule.INSTANCE);
        // .addRuleInstance(new ProjectMergeRule(true, projectFactory));

        // .addRuleInstance(DrillMergeProjectRule.getInstance(true, projectFactory, this.context.getFunctionRegistry()));


    final HepProgram hepPgm = hepPgmBldr.build();
    final HepPlanner hepPlanner = new HepPlanner(hepPgm);

    final List<RelMetadataProvider> list = Lists.newArrayList();
    list.add(DrillDefaultRelMetadataProvider.INSTANCE);
    hepPlanner.registerMetadataProviders(list);
    final RelMetadataProvider cachingMetaDataProvider = new CachingRelMetadataProvider(ChainedRelMetadataProvider.of(list), hepPlanner);

    // Modify RelMetaProvider for every RelNode in the SQL operator Rel tree.
    root.accept(new MetaDataProviderModifier(cachingMetaDataProvider));

    hepPlanner.setRoot(root);

    RelNode calciteOptimizedPlan = hepPlanner.findBestExp();

    return calciteOptimizedPlan;
  }


  public static class MetaDataProviderModifier extends RelShuttleImpl {
    private final RelMetadataProvider metadataProvider;

    public MetaDataProviderModifier(RelMetadataProvider metadataProvider) {
      this.metadataProvider = metadataProvider;
    }

    @Override
    public RelNode visit(TableScan scan) {
      scan.getCluster().setMetadataProvider(metadataProvider);
      return super.visit(scan);
    }

    @Override
    public RelNode visit(TableFunctionScan scan) {
      scan.getCluster().setMetadataProvider(metadataProvider);
      return super.visit(scan);
    }

    @Override
    public RelNode visit(LogicalValues values) {
      values.getCluster().setMetadataProvider(metadataProvider);
      return super.visit(values);
    }

    @Override
    protected RelNode visitChild(RelNode parent, int i, RelNode child) {
      child.accept(this);
      parent.getCluster().setMetadataProvider(metadataProvider);
      return parent;
    }
  }

  protected class ConvertedRelNode {
    private final RelNode relNode;
    private final RelDataType validatedRowType;

    public ConvertedRelNode(RelNode relNode, RelDataType validatedRowType) {
      this.relNode = relNode;
      this.validatedRowType = validatedRowType;
    }

    public RelNode getConvertedNode() {
      return this.relNode;
    }

    public RelDataType getValidatedRowType() {
      return this.validatedRowType;
    }
  }


}


File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/sql/handlers/DescribeTableHandler.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.drill.exec.planner.sql.handlers;

import java.util.List;

import org.apache.calcite.schema.SchemaPlus;
import org.apache.calcite.tools.RelConversionException;

import static org.apache.drill.exec.store.ischema.InfoSchemaConstants.*;

import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.planner.sql.SchemaUtilites;
import org.apache.drill.exec.planner.sql.parser.DrillParserUtil;
import org.apache.drill.exec.planner.sql.parser.SqlDescribeTable;
import org.apache.drill.exec.work.foreman.ForemanSetupException;
import org.apache.calcite.sql.SqlIdentifier;
import org.apache.calcite.sql.SqlLiteral;
import org.apache.calcite.sql.SqlNode;
import org.apache.calcite.sql.SqlNodeList;
import org.apache.calcite.sql.SqlSelect;
import org.apache.calcite.sql.fun.SqlStdOperatorTable;
import org.apache.calcite.sql.parser.SqlParserPos;
import org.apache.calcite.util.Util;

import com.google.common.collect.ImmutableList;

import static org.apache.drill.exec.planner.sql.parser.DrillParserUtil.CHARSET;

public class DescribeTableHandler extends DefaultSqlHandler {

  public DescribeTableHandler(SqlHandlerConfig config) { super(config); }

  /** Rewrite the parse tree as SELECT ... FROM INFORMATION_SCHEMA.COLUMNS ... */
  @Override
  public SqlNode rewrite(SqlNode sqlNode) throws RelConversionException, ForemanSetupException {
    SqlDescribeTable node = unwrap(sqlNode, SqlDescribeTable.class);

    try {
      List<SqlNode> selectList =
          ImmutableList.of((SqlNode) new SqlIdentifier(COLS_COL_COLUMN_NAME, SqlParserPos.ZERO),
                                     new SqlIdentifier(COLS_COL_DATA_TYPE, SqlParserPos.ZERO),
                                     new SqlIdentifier(COLS_COL_IS_NULLABLE, SqlParserPos.ZERO));

      SqlNode fromClause = new SqlIdentifier(
          ImmutableList.of(IS_SCHEMA_NAME, TAB_COLUMNS), null, SqlParserPos.ZERO, null);

      final SqlIdentifier table = node.getTable();
      final SchemaPlus defaultSchema = context.getNewDefaultSchema();
      final List<String> schemaPathGivenInCmd = Util.skipLast(table.names);
      final SchemaPlus schema = SchemaUtilites.findSchema(defaultSchema, schemaPathGivenInCmd);

      if (schema == null) {
        SchemaUtilites.throwSchemaNotFoundException(defaultSchema,
            SchemaUtilites.SCHEMA_PATH_JOINER.join(schemaPathGivenInCmd));
      }

      if (SchemaUtilites.isRootSchema(schema)) {
        throw UserException.validationError()
            .message("No schema selected.")
            .build();
      }

      final String tableName = Util.last(table.names);

      // find resolved schema path
      final String schemaPath = SchemaUtilites.unwrapAsDrillSchemaInstance(schema).getFullSchemaName();

      if (schema.getTable(tableName) == null) {
        throw UserException.validationError()
            .message("Unknown table [%s] in schema [%s]", tableName, schemaPath)
            .build();
      }

      SqlNode schemaCondition = null;
      if (!SchemaUtilites.isRootSchema(schema)) {
        schemaCondition = DrillParserUtil.createCondition(
            new SqlIdentifier(SHRD_COL_TABLE_SCHEMA, SqlParserPos.ZERO),
            SqlStdOperatorTable.EQUALS,
            SqlLiteral.createCharString(schemaPath, CHARSET, SqlParserPos.ZERO)
        );
      }

      SqlNode where = DrillParserUtil.createCondition(
          new SqlIdentifier(SHRD_COL_TABLE_NAME, SqlParserPos.ZERO),
          SqlStdOperatorTable.EQUALS,
          SqlLiteral.createCharString(tableName, CHARSET, SqlParserPos.ZERO));

      where = DrillParserUtil.createCondition(schemaCondition, SqlStdOperatorTable.AND, where);

      SqlNode columnFilter = null;
      if (node.getColumn() != null) {
        columnFilter =
            DrillParserUtil.createCondition(
                new SqlIdentifier(COLS_COL_COLUMN_NAME, SqlParserPos.ZERO),
                SqlStdOperatorTable.EQUALS,
                SqlLiteral.createCharString(node.getColumn().toString(), CHARSET, SqlParserPos.ZERO));
      } else if (node.getColumnQualifier() != null) {
        columnFilter =
            DrillParserUtil.createCondition(
                new SqlIdentifier(COLS_COL_COLUMN_NAME, SqlParserPos.ZERO),
                SqlStdOperatorTable.LIKE, node.getColumnQualifier());
      }

      where = DrillParserUtil.createCondition(where, SqlStdOperatorTable.AND, columnFilter);

      return new SqlSelect(SqlParserPos.ZERO, null, new SqlNodeList(selectList, SqlParserPos.ZERO),
          fromClause, where, null, null, null, null, null, null);
    } catch (Exception ex) {
      throw UserException.planError(ex)
          .message("Error while rewriting DESCRIBE query: %d", ex.getMessage())
          .build();
    }
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/sql/handlers/ExplainHandler.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.planner.sql.handlers;

import java.io.IOException;

import org.apache.calcite.rel.type.RelDataType;
import org.apache.calcite.tools.RelConversionException;
import org.apache.calcite.tools.ValidationException;

import org.apache.drill.common.logical.LogicalPlan;
import org.apache.drill.common.logical.PlanProperties.Generator.ResultMode;
import org.apache.drill.exec.ops.QueryContext;
import org.apache.drill.exec.physical.PhysicalPlan;
import org.apache.drill.exec.physical.base.PhysicalOperator;
import org.apache.drill.exec.planner.logical.DrillImplementor;
import org.apache.drill.exec.planner.logical.DrillParseContext;
import org.apache.drill.exec.planner.logical.DrillRel;
import org.apache.drill.exec.planner.physical.Prel;
import org.apache.drill.exec.planner.physical.explain.PrelSequencer;
import org.apache.drill.exec.planner.sql.DirectPlan;
import org.apache.drill.exec.work.foreman.ForemanSetupException;
import org.apache.calcite.rel.RelNode;
import org.apache.calcite.plan.RelOptUtil;
import org.apache.calcite.sql.SqlExplain;
import org.apache.calcite.sql.SqlExplainLevel;
import org.apache.calcite.sql.SqlLiteral;
import org.apache.calcite.sql.SqlNode;

public class ExplainHandler extends DefaultSqlHandler {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(ExplainHandler.class);

  private ResultMode mode;
  private SqlExplainLevel level = SqlExplainLevel.ALL_ATTRIBUTES;
  public ExplainHandler(SqlHandlerConfig config) {
    super(config);
  }

  @Override
  public PhysicalPlan getPlan(SqlNode sqlNode) throws ValidationException, RelConversionException, IOException, ForemanSetupException {
    final ConvertedRelNode convertedRelNode = validateAndConvert(sqlNode);
    final RelDataType validatedRowType = convertedRelNode.getValidatedRowType();
    final RelNode queryRelNode = convertedRelNode.getConvertedNode();

    log("Optiq Logical", queryRelNode);
    DrillRel drel = convertToDrel(queryRelNode, validatedRowType);
    log("Drill Logical", drel);

    if (mode == ResultMode.LOGICAL) {
      LogicalExplain logicalResult = new LogicalExplain(drel, level, context);
      return DirectPlan.createDirectPlan(context, logicalResult);
    }

    Prel prel = convertToPrel(drel);
    log("Drill Physical", prel);
    PhysicalOperator pop = convertToPop(prel);
    PhysicalPlan plan = convertToPlan(pop);
    log("Drill Plan", plan);
    PhysicalExplain physicalResult = new PhysicalExplain(prel, plan, level, context);
    return DirectPlan.createDirectPlan(context, physicalResult);
  }

  @Override
  public SqlNode rewrite(SqlNode sqlNode) throws RelConversionException, ForemanSetupException {
    SqlExplain node = unwrap(sqlNode, SqlExplain.class);
    SqlLiteral op = node.operand(2);
    SqlExplain.Depth depth = (SqlExplain.Depth) op.getValue();
    if (node.getDetailLevel() != null) {
      level = node.getDetailLevel();
    }
    switch (depth) {
    case LOGICAL:
      mode = ResultMode.LOGICAL;
      break;
    case PHYSICAL:
      mode = ResultMode.PHYSICAL;
      break;
    default:
      throw new UnsupportedOperationException("Unknown depth " + depth);
    }

    return node.operand(0);
  }


  public static class LogicalExplain{
    public String text;
    public String json;

    public LogicalExplain(RelNode node, SqlExplainLevel level, QueryContext context) {
      this.text = RelOptUtil.toString(node, level);
      DrillImplementor implementor = new DrillImplementor(new DrillParseContext(context.getPlannerSettings()), ResultMode.LOGICAL);
      implementor.go( (DrillRel) node);
      LogicalPlan plan = implementor.getPlan();
      this.json = plan.unparse(context.getConfig());
    }
  }

  public static class PhysicalExplain{
    public String text;
    public String json;

    public PhysicalExplain(RelNode node, PhysicalPlan plan, SqlExplainLevel level, QueryContext context) {
      this.text = PrelSequencer.printWithIds((Prel) node, level);
      this.json = plan.unparse(context.getConfig().getMapper().writer());
    }
  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/sql/handlers/ShowFileHandler.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.planner.sql.handlers;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import org.apache.calcite.schema.SchemaPlus;
import org.apache.calcite.tools.RelConversionException;
import org.apache.calcite.tools.ValidationException;

import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.physical.PhysicalPlan;
import org.apache.drill.exec.planner.sql.DirectPlan;
import org.apache.drill.exec.planner.sql.SchemaUtilites;
import org.apache.drill.exec.planner.sql.parser.SqlShowFiles;
import org.apache.drill.exec.store.AbstractSchema;
import org.apache.drill.exec.store.dfs.WorkspaceSchemaFactory.WorkspaceSchema;
import org.apache.drill.exec.store.dfs.DrillFileSystem;
import org.apache.hadoop.fs.FileStatus;
import org.apache.hadoop.fs.Path;
import org.apache.calcite.sql.SqlIdentifier;
import org.apache.calcite.sql.SqlNode;


public class ShowFileHandler extends DefaultSqlHandler {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(SetOptionHandler.class);

  public ShowFileHandler(SqlHandlerConfig config) {
    super(config);
  }

  @Override
  public PhysicalPlan getPlan(SqlNode sqlNode) throws ValidationException, RelConversionException, IOException {

    SqlIdentifier from = ((SqlShowFiles) sqlNode).getDb();

    DrillFileSystem fs = null;
    String defaultLocation = null;
    String fromDir = "./";

    SchemaPlus defaultSchema = context.getNewDefaultSchema();
    SchemaPlus drillSchema = defaultSchema;

    // Show files can be used without from clause, in which case we display the files in the default schema
    if (from != null) {
      // We are not sure if the full from clause is just the schema or includes table name,
      // first try to see if the full path specified is a schema
      drillSchema = SchemaUtilites.findSchema(defaultSchema, from.names);
      if (drillSchema == null) {
        // Entire from clause is not a schema, try to obtain the schema without the last part of the specified clause.
        drillSchema = SchemaUtilites.findSchema(defaultSchema, from.names.subList(0, from.names.size() - 1));
        fromDir = fromDir + from.names.get((from.names.size() - 1));
      }

      if (drillSchema == null) {
        throw UserException.validationError()
            .message("Invalid FROM/IN clause [%s]", from.toString())
            .build();
      }
    }

    WorkspaceSchema wsSchema;
    try {
       wsSchema = (WorkspaceSchema) drillSchema.unwrap(AbstractSchema.class).getDefaultSchema();
    } catch (ClassCastException e) {
      throw UserException.validationError()
          .message("SHOW FILES is supported in workspace type schema only. Schema [%s] is not a workspace schema.",
              SchemaUtilites.getSchemaPath(drillSchema))
          .build();
    }

    // Get the file system object
    fs = wsSchema.getFS();

    // Get the default path
    defaultLocation = wsSchema.getDefaultLocation();

    List<ShowFilesCommandResult> rows = new ArrayList<>();

    for (FileStatus fileStatus : fs.list(false, new Path(defaultLocation, fromDir))) {
      ShowFilesCommandResult result = new ShowFilesCommandResult(fileStatus.getPath().getName(), fileStatus.isDir(),
                                                                 !fileStatus.isDir(), fileStatus.getLen(),
                                                                 fileStatus.getOwner(), fileStatus.getGroup(),
                                                                 fileStatus.getPermission().toString(),
                                                                 fileStatus.getAccessTime(), fileStatus.getModificationTime());
      rows.add(result);
    }
    return DirectPlan.createDirectPlan(context.getCurrentEndpoint(), rows.iterator(), ShowFilesCommandResult.class);
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/sql/handlers/ShowTablesHandler.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.drill.exec.planner.sql.handlers;

import static org.apache.drill.exec.planner.sql.parser.DrillParserUtil.CHARSET;

import java.util.List;

import org.apache.calcite.schema.SchemaPlus;
import org.apache.calcite.tools.RelConversionException;

import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.planner.sql.SchemaUtilites;
import org.apache.drill.exec.planner.sql.parser.DrillParserUtil;
import org.apache.drill.exec.planner.sql.parser.SqlShowTables;
import org.apache.drill.exec.store.AbstractSchema;
import static org.apache.drill.exec.store.ischema.InfoSchemaConstants.*;
import org.apache.drill.exec.work.foreman.ForemanSetupException;
import org.apache.calcite.sql.SqlIdentifier;
import org.apache.calcite.sql.SqlLiteral;
import org.apache.calcite.sql.SqlNode;
import org.apache.calcite.sql.SqlNodeList;
import org.apache.calcite.sql.SqlSelect;
import org.apache.calcite.sql.fun.SqlStdOperatorTable;
import org.apache.calcite.sql.parser.SqlParserPos;

import com.google.common.collect.ImmutableList;
import com.google.common.collect.Lists;

public class ShowTablesHandler extends DefaultSqlHandler {

  public ShowTablesHandler(SqlHandlerConfig config) { super(config); }

  /** Rewrite the parse tree as SELECT ... FROM INFORMATION_SCHEMA.`TABLES` ... */
  @Override
  public SqlNode rewrite(SqlNode sqlNode) throws RelConversionException, ForemanSetupException {
    SqlShowTables node = unwrap(sqlNode, SqlShowTables.class);
    List<SqlNode> selectList = Lists.newArrayList();
    SqlNode fromClause;
    SqlNode where;

    // create select columns
    selectList.add(new SqlIdentifier(SHRD_COL_TABLE_SCHEMA, SqlParserPos.ZERO));
    selectList.add(new SqlIdentifier(SHRD_COL_TABLE_NAME, SqlParserPos.ZERO));

    fromClause = new SqlIdentifier(ImmutableList.of(IS_SCHEMA_NAME, TAB_TABLES), SqlParserPos.ZERO);

    final SqlIdentifier db = node.getDb();
    String tableSchema;
    if (db != null) {
      tableSchema = db.toString();
    } else {
      // If no schema is given in SHOW TABLES command, list tables from current schema
      SchemaPlus schema = context.getNewDefaultSchema();

      if (SchemaUtilites.isRootSchema(schema)) {
        // If the default schema is a root schema, throw an error to select a default schema
        throw UserException.validationError()
            .message("No default schema selected. Select a schema using 'USE schema' command")
            .build();
      }

      final AbstractSchema drillSchema = SchemaUtilites.unwrapAsDrillSchemaInstance(schema);
      tableSchema = drillSchema.getFullSchemaName();
    }

    where = DrillParserUtil.createCondition(
        new SqlIdentifier(SHRD_COL_TABLE_SCHEMA, SqlParserPos.ZERO),
        SqlStdOperatorTable.EQUALS,
        SqlLiteral.createCharString(tableSchema, CHARSET, SqlParserPos.ZERO));

    SqlNode filter = null;
    final SqlNode likePattern = node.getLikePattern();
    if (likePattern != null) {
      filter = DrillParserUtil.createCondition(
          new SqlIdentifier(SHRD_COL_TABLE_NAME, SqlParserPos.ZERO),
          SqlStdOperatorTable.LIKE,
          likePattern);
    } else if (node.getWhereClause() != null) {
      filter = node.getWhereClause();
    }

    where = DrillParserUtil.createCondition(where, SqlStdOperatorTable.AND, filter);

    return new SqlSelect(SqlParserPos.ZERO, null, new SqlNodeList(selectList, SqlParserPos.ZERO),
        fromClause, where, null, null, null, null, null, null);
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/sql/handlers/SqlHandlerUtil.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.planner.sql.handlers;

import com.google.common.collect.Lists;
import com.google.common.collect.Sets;
import org.apache.calcite.rel.type.RelDataTypeField;
import org.apache.calcite.rex.RexBuilder;
import org.apache.calcite.rex.RexInputRef;
import org.apache.calcite.rex.RexLiteral;
import org.apache.calcite.rex.RexNode;
import org.apache.calcite.schema.Table;
import org.apache.calcite.sql.SqlNodeList;
import org.apache.calcite.sql.SqlWriter;
import org.apache.calcite.sql.TypedSqlNode;
import org.apache.calcite.sql.fun.SqlStdOperatorTable;
import org.apache.calcite.tools.Planner;
import org.apache.calcite.tools.RelConversionException;
import org.apache.drill.common.exceptions.DrillException;
import org.apache.drill.common.exceptions.DrillRuntimeException;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.planner.StarColumnHelper;
import org.apache.drill.exec.planner.common.DrillRelOptUtil;
import org.apache.drill.exec.planner.sql.DirectPlan;
import org.apache.drill.exec.planner.types.DrillFixedRelDataTypeImpl;
import org.apache.drill.exec.store.AbstractSchema;

import org.apache.calcite.tools.ValidationException;
import org.apache.calcite.rel.RelNode;
import org.apache.calcite.plan.RelOptUtil;
import org.apache.calcite.rel.type.RelDataType;
import org.apache.calcite.sql.SqlNode;
import org.apache.drill.exec.store.ischema.Records;

import java.util.AbstractList;
import java.util.HashSet;
import java.util.List;

public class SqlHandlerUtil {

  /**
   * Resolve final RelNode of the new table (or view) for given table field list and new table definition.
   *
   * @param isNewTableView Is the new table created a view? This doesn't affect the functionality, but it helps format
   *                       better error messages.
   * @param tableFieldNames List of fields specified in new table/view field list. These are the fields given just after
   *                        new table name.
   *                        Ex. CREATE TABLE newTblName(col1, medianOfCol2, avgOfCol3) AS
   *                        SELECT col1, median(col2), avg(col3) FROM sourcetbl GROUP BY col1;
   * @throws ValidationException If table's fields list and field list specified in table definition are not valid.
   * @throws RelConversionException If failed to convert the table definition into a RelNode.
   */
  public static RelNode resolveNewTableRel(boolean isNewTableView, List<String> tableFieldNames,
      RelDataType validatedRowtype, RelNode queryRelNode) throws ValidationException, RelConversionException {


//    TypedSqlNode validatedSqlNodeWithType = planner.validateAndGetType(newTableQueryDef);

    // Get the row type of view definition query.
    // Reason for getting the row type from validated SqlNode than RelNode is because SqlNode -> RelNode involves
    // renaming duplicate fields which is not desired when creating a view or table.
    // For ex: SELECT region_id, region_id FROM cp.`region.json` LIMIT 1 returns
    //  +------------+------------+
    //  | region_id  | region_id0 |
    //  +------------+------------+
    //  | 0          | 0          |
    //  +------------+------------+
    // which is not desired when creating new views or tables.
//    final RelDataType queryRowType = validatedRowtype;

    if (tableFieldNames.size() > 0) {
      // Field count should match.
      if (tableFieldNames.size() != validatedRowtype.getFieldCount()) {
        final String tblType = isNewTableView ? "view" : "table";
        throw UserException.validationError()
            .message("%s's field list and the %s's query field list have different counts.", tblType, tblType)
            .build();
      }

      // CTAS's query field list shouldn't have "*" when table's field list is specified.
      for (String field : validatedRowtype.getFieldNames()) {
        if (field.equals("*")) {
          final String tblType = isNewTableView ? "view" : "table";
          throw UserException.validationError()
              .message("%s's query field list has a '*', which is invalid when %s's field list is specified.",
                  tblType, tblType)
              .build();
        }
      }

      // validate the given field names to make sure there are no duplicates
      ensureNoDuplicateColumnNames(tableFieldNames);

      // CTAS statement has table field list (ex. below), add a project rel to rename the query fields.
      // Ex. CREATE TABLE tblname(col1, medianOfCol2, avgOfCol3) AS
      //        SELECT col1, median(col2), avg(col3) FROM sourcetbl GROUP BY col1 ;
      // Similary for CREATE VIEW.

      return DrillRelOptUtil.createRename(queryRelNode, tableFieldNames);
    }

    // As the column names of the view are derived from SELECT query, make sure the query has no duplicate column names
    ensureNoDuplicateColumnNames(validatedRowtype.getFieldNames());

    return queryRelNode;
  }

  private static void ensureNoDuplicateColumnNames(List<String> fieldNames) throws ValidationException {
    final HashSet<String> fieldHashSet = Sets.newHashSetWithExpectedSize(fieldNames.size());
    for(String field : fieldNames) {
      if (fieldHashSet.contains(field.toLowerCase())) {
        throw new ValidationException(String.format("Duplicate column name [%s]", field));
      }
      fieldHashSet.add(field.toLowerCase());
    }
  }

  /**
   *  Resolve the partition columns specified in "PARTITION BY" clause of CTAS statement.
   *
   *  A partition column is resolved, either (1) the same column appear in the select list of CTAS
   *  or (2) CTAS has a * in select list.
   *
   *  In the second case, a PROJECT with ITEM expression would be created and returned.
   *  Throw validation error if a partition column is not resolved correctly.
   *
   * @param input : the RelNode represents the select statement in CTAS.
   * @param partitionColumns : the list of partition columns.
   * @return : 1) the original RelNode input, if all partition columns are in select list of CTAS
   *           2) a New Project, if a partition column is resolved to * column in select list
   *           3) validation error, if partition column is not resolved.
   */
  public static RelNode qualifyPartitionCol(RelNode input, List<String> partitionColumns) {

    final RelDataType inputRowType = input.getRowType();

    final List<RexNode> colRefStarExprs = Lists.newArrayList();
    final List<String> colRefStarNames = Lists.newArrayList();
    final RexBuilder builder = input.getCluster().getRexBuilder();
    final int originalFieldSize = inputRowType.getFieldCount();

    for (final String col : partitionColumns) {
      final RelDataTypeField field = inputRowType.getField(col, false, false);

      if (field == null) {
        throw UserException.validationError()
            .message("Partition column %s is not in the SELECT list of CTAS!", col)
            .build();
      } else {
        if (field.getName().startsWith(StarColumnHelper.STAR_COLUMN)) {
          colRefStarNames.add(col);

          final List<RexNode> operands = Lists.newArrayList();
          operands.add(new RexInputRef(field.getIndex(), field.getType()));
          operands.add(builder.makeLiteral(col));
          final RexNode item = builder.makeCall(SqlStdOperatorTable.ITEM, operands);
          colRefStarExprs.add(item);
        }
      }
    }

    if (colRefStarExprs.isEmpty()) {
      return input;
    } else {
      final List<String> names =
          new AbstractList<String>() {
            @Override
            public String get(int index) {
              if (index < originalFieldSize) {
                return inputRowType.getFieldNames().get(index);
              } else {
                return colRefStarNames.get(index - originalFieldSize);
              }
            }

            @Override
            public int size() {
              return originalFieldSize + colRefStarExprs.size();
            }
          };

      final List<RexNode> refs =
          new AbstractList<RexNode>() {
            public int size() {
              return originalFieldSize + colRefStarExprs.size();
            }

            public RexNode get(int index) {
              if (index < originalFieldSize) {
                return RexInputRef.of(index, inputRowType.getFieldList());
              } else {
                return colRefStarExprs.get(index - originalFieldSize);
              }
            }
          };

      return RelOptUtil.createProject(input, refs, names, false);
    }
  }

  public static Table getTableFromSchema(AbstractSchema drillSchema, String tblName) {
    try {
      return drillSchema.getTable(tblName);
    } catch (Exception e) {
      // TODO: Move to better exception types.
      throw new DrillRuntimeException(
          String.format("Failure while trying to check if a table or view with given name [%s] already exists " +
              "in schema [%s]: %s", tblName, drillSchema.getFullSchemaName(), e.getMessage()), e);
    }
  }

  public static void unparseSqlNodeList(SqlWriter writer, int leftPrec, int rightPrec, SqlNodeList fieldList) {
    writer.keyword("(");
    fieldList.get(0).unparse(writer, leftPrec, rightPrec);
    for (int i = 1; i<fieldList.size(); i++) {
      writer.keyword(",");
      fieldList.get(i).unparse(writer, leftPrec, rightPrec);
    }
    writer.keyword(")");
  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/planner/sql/handlers/ViewHandler.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.planner.sql.handlers;

import java.io.IOException;

import org.apache.calcite.rel.type.RelDataType;
import org.apache.calcite.schema.Schema;
import org.apache.calcite.schema.SchemaPlus;
import org.apache.calcite.schema.Table;
import org.apache.calcite.tools.RelConversionException;
import org.apache.calcite.tools.ValidationException;

import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.dotdrill.View;
import org.apache.drill.exec.ops.QueryContext;
import org.apache.drill.exec.physical.PhysicalPlan;
import org.apache.drill.exec.planner.sql.DirectPlan;
import org.apache.drill.exec.planner.sql.SchemaUtilites;
import org.apache.drill.exec.planner.sql.parser.SqlCreateView;
import org.apache.drill.exec.planner.sql.parser.SqlDropView;
import org.apache.drill.exec.store.AbstractSchema;
import org.apache.drill.exec.work.foreman.ForemanSetupException;
import org.apache.calcite.rel.RelNode;
import org.apache.calcite.sql.SqlNode;

public abstract class ViewHandler extends DefaultSqlHandler {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(ViewHandler.class);

  protected QueryContext context;

  public ViewHandler(SqlHandlerConfig config) {
    super(config);
    this.context = config.getContext();
  }

  /** Handler for Create View DDL command */
  public static class CreateView extends ViewHandler {

    public CreateView(SqlHandlerConfig config) {
      super(config);
    }

    @Override
    public PhysicalPlan getPlan(SqlNode sqlNode) throws ValidationException, RelConversionException, IOException, ForemanSetupException {
      SqlCreateView createView = unwrap(sqlNode, SqlCreateView.class);

      final String newViewName = createView.getName();

      // Store the viewSql as view def SqlNode is modified as part of the resolving the new table definition below.
      final String viewSql = createView.getQuery().toString();

      final ConvertedRelNode convertedRelNode = validateAndConvert(createView.getQuery());
      final RelDataType validatedRowType = convertedRelNode.getValidatedRowType();
      final RelNode queryRelNode = convertedRelNode.getConvertedNode();

      final RelNode newViewRelNode = SqlHandlerUtil.resolveNewTableRel(true, createView.getFieldNames(), validatedRowType, queryRelNode);

      final SchemaPlus defaultSchema = context.getNewDefaultSchema();
      final AbstractSchema drillSchema = SchemaUtilites.resolveToMutableDrillSchema(defaultSchema, createView.getSchemaPath());

      final String schemaPath = drillSchema.getFullSchemaName();
      final View view = new View(newViewName, viewSql, newViewRelNode.getRowType(),
          SchemaUtilites.getSchemaPathAsList(defaultSchema));

      final Table existingTable = SqlHandlerUtil.getTableFromSchema(drillSchema, newViewName);

      if (existingTable != null) {
        if (existingTable.getJdbcTableType() != Schema.TableType.VIEW) {
          // existing table is not a view
          throw UserException.validationError()
              .message("A non-view table with given name [%s] already exists in schema [%s]",
                  newViewName, schemaPath)
              .build();
        }

        if (existingTable.getJdbcTableType() == Schema.TableType.VIEW && !createView.getReplace()) {
          // existing table is a view and create view has no "REPLACE" clause
          throw UserException.validationError()
              .message("A view with given name [%s] already exists in schema [%s]",
                  newViewName, schemaPath)
              .build();
        }
      }

      final boolean replaced = drillSchema.createView(view);
      final String summary = String.format("View '%s' %s successfully in '%s' schema",
          createView.getName(), replaced ? "replaced" : "created", schemaPath);

      return DirectPlan.createDirectPlan(context, true, summary);
    }
  }

  /** Handler for Drop View DDL command. */
  public static class DropView extends ViewHandler {
    public DropView(SqlHandlerConfig config) {
      super(config);
    }

    @Override
    public PhysicalPlan getPlan(SqlNode sqlNode) throws ValidationException, RelConversionException, IOException, ForemanSetupException {
      SqlDropView dropView = unwrap(sqlNode, SqlDropView.class);
      final String viewToDrop = dropView.getName();
      final AbstractSchema drillSchema =
          SchemaUtilites.resolveToMutableDrillSchema(context.getNewDefaultSchema(), dropView.getSchemaPath());

      final String schemaPath = drillSchema.getFullSchemaName();

      final Table existingTable = SqlHandlerUtil.getTableFromSchema(drillSchema, viewToDrop);
      if (existingTable != null && existingTable.getJdbcTableType() != Schema.TableType.VIEW) {
        throw UserException.validationError()
            .message("[%s] is not a VIEW in schema [%s]", viewToDrop, schemaPath)
            .build();
      } else if (existingTable == null) {
        throw UserException.validationError()
            .message("Unknown view [%s] in schema [%s].", viewToDrop, schemaPath)
            .build();
      }

      drillSchema.dropView(viewToDrop);

      return DirectPlan.createDirectPlan(context, true,
          String.format("View [%s] deleted successfully from schema [%s].", viewToDrop, schemaPath));
    }
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/record/AbstractRecordBatch.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.record;

import java.util.Iterator;

import org.apache.drill.common.exceptions.DrillRuntimeException;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.common.expression.SchemaPath;
import org.apache.drill.exec.exception.SchemaChangeException;
import org.apache.drill.exec.memory.OutOfMemoryException;
import org.apache.drill.exec.ops.FragmentContext;
import org.apache.drill.exec.ops.OperatorContext;
import org.apache.drill.exec.ops.OperatorStats;
import org.apache.drill.exec.physical.base.PhysicalOperator;
import org.apache.drill.exec.record.selection.SelectionVector2;
import org.apache.drill.exec.record.selection.SelectionVector4;

public abstract class AbstractRecordBatch<T extends PhysicalOperator> implements CloseableRecordBatch {
  final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(this.getClass());

  protected final VectorContainer container;
  protected final T popConfig;
  protected final FragmentContext context;
  protected final OperatorContext oContext;
  protected final OperatorStats stats;

  protected BatchState state;

  protected AbstractRecordBatch(final T popConfig, final FragmentContext context) throws OutOfMemoryException {
    this(popConfig, context, true, context.newOperatorContext(popConfig, true));
  }

  protected AbstractRecordBatch(final T popConfig, final FragmentContext context, final boolean buildSchema) throws OutOfMemoryException {
    this(popConfig, context, buildSchema, context.newOperatorContext(popConfig, true));
  }

  protected AbstractRecordBatch(final T popConfig, final FragmentContext context, final boolean buildSchema,
      final OperatorContext oContext) throws OutOfMemoryException {
    super();
    this.context = context;
    this.popConfig = popConfig;
    this.oContext = oContext;
    stats = oContext.getStats();
    container = new VectorContainer(this.oContext);
    if (buildSchema) {
      state = BatchState.BUILD_SCHEMA;
    } else {
      state = BatchState.FIRST;
    }
  }

  protected static enum BatchState {
    BUILD_SCHEMA, // Need to build schema and return
    FIRST, // This is still the first data batch
    NOT_FIRST, // The first data batch has already been returned
    STOP, // The query most likely failed, we need to propagate STOP to the root
    OUT_OF_MEMORY, // Out of Memory while building the Schema...Ouch!
    DONE // All work is done, no more data to be sent
  }

  @Override
  public Iterator<VectorWrapper<?>> iterator() {
    return container.iterator();
  }

  @Override
  public FragmentContext getContext() {
    return context;
  }

  public PhysicalOperator getPopConfig() {
    return popConfig;
  }

  public final IterOutcome next(final RecordBatch b) {
    if(!context.shouldContinue()) {
      return IterOutcome.STOP;
    }
    return next(0, b);
  }

  public final IterOutcome next(final int inputIndex, final RecordBatch b){
    IterOutcome next = null;
    stats.stopProcessing();
    try{
      if (!context.shouldContinue()) {
        return IterOutcome.STOP;
      }
      next = b.next();
    }finally{
      stats.startProcessing();
    }

    switch(next){
    case OK_NEW_SCHEMA:
      stats.batchReceived(inputIndex, b.getRecordCount(), true);
      break;
    case OK:
      stats.batchReceived(inputIndex, b.getRecordCount(), false);
      break;
    }

    return next;
  }

  public final IterOutcome next() {
    try {
      stats.startProcessing();
      switch (state) {
        case BUILD_SCHEMA: {
          buildSchema();
          switch (state) {
            case DONE:
              return IterOutcome.NONE;
            case OUT_OF_MEMORY:
              // because we don't support schema changes, it is safe to fail the query right away
              context.fail(UserException.memoryError().build());
              // FALL-THROUGH
            case STOP:
              return IterOutcome.STOP;
            default:
              state = BatchState.FIRST;
              return IterOutcome.OK_NEW_SCHEMA;
          }
        }
        case DONE: {
          return IterOutcome.NONE;
        }
        default:
          return innerNext();
      }
    } catch (final SchemaChangeException e) {
      throw new DrillRuntimeException(e);
    } finally {
      stats.stopProcessing();
    }
  }

  public abstract IterOutcome innerNext();

  @Override
  public BatchSchema getSchema() {
    if (container.hasSchema()) {
      return container.getSchema();
    } else {
      return null;
    }
  }

  protected void buildSchema() throws SchemaChangeException {
  }

  @Override
  public void kill(final boolean sendUpstream) {
    killIncoming(sendUpstream);
  }

  protected abstract void killIncoming(boolean sendUpstream);

  public void close(){
    container.clear();
  }


  @Override
  public SelectionVector2 getSelectionVector2() {
    throw new UnsupportedOperationException();
  }

  @Override
  public SelectionVector4 getSelectionVector4() {
    throw new UnsupportedOperationException();
  }

  @Override
  public TypedFieldId getValueVectorId(final SchemaPath path) {
    return container.getValueVectorId(path);
  }

  @Override
  public VectorWrapper<?> getValueAccessorById(final Class<?> clazz, final int... ids) {
    return container.getValueAccessorById(clazz, ids);
  }


  @Override
  public WritableBatch getWritableBatch() {
//    logger.debug("Getting writable batch.");
    final WritableBatch batch = WritableBatch.get(this);
    return batch;

  }

  @Override
  public VectorContainer getOutgoingContainer() {
    throw new UnsupportedOperationException(String.format(" You should not call getOutgoingContainer() for class %s", this.getClass().getCanonicalName()));
  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/rpc/BasicServer.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.rpc;

import io.netty.bootstrap.ServerBootstrap;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufAllocator;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.ChannelInitializer;
import io.netty.channel.ChannelOption;
import io.netty.channel.ChannelPipeline;
import io.netty.channel.EventLoopGroup;
import io.netty.channel.socket.SocketChannel;
import io.netty.handler.timeout.ReadTimeoutHandler;

import java.io.IOException;
import java.net.BindException;
import java.util.concurrent.ExecutionException;

import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.exception.DrillbitStartupException;
import org.apache.drill.exec.memory.BufferAllocator;
import org.apache.drill.exec.proto.GeneralRPCProtos.RpcMode;

import com.google.protobuf.Internal.EnumLite;
import com.google.protobuf.MessageLite;
import com.google.protobuf.Parser;

/**
 * A server is bound to a port and is responsible for responding to various type of requests. In some cases, the inbound
 * requests will generate more than one outbound request.
 */
public abstract class BasicServer<T extends EnumLite, C extends RemoteConnection> extends RpcBus<T, C> {
  final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(this.getClass());

  protected static final String TIMEOUT_HANDLER = "timeout-handler";

  private ServerBootstrap b;
  private volatile boolean connect = false;
  private final EventLoopGroup eventLoopGroup;

  public BasicServer(final RpcConfig rpcMapping, ByteBufAllocator alloc, EventLoopGroup eventLoopGroup) {
    super(rpcMapping);
    this.eventLoopGroup = eventLoopGroup;

    b = new ServerBootstrap()
        .channel(TransportCheck.getServerSocketChannel())
        .option(ChannelOption.SO_BACKLOG, 1000)
        .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, 30*1000)
        .option(ChannelOption.TCP_NODELAY, true)
        .option(ChannelOption.SO_REUSEADDR, true)
        .option(ChannelOption.SO_RCVBUF, 1 << 17)
        .option(ChannelOption.SO_SNDBUF, 1 << 17)
        .group(eventLoopGroup) //
        .childOption(ChannelOption.ALLOCATOR, alloc)

        // .handler(new LoggingHandler(LogLevel.INFO))

        .childHandler(new ChannelInitializer<SocketChannel>() {
          @Override
          protected void initChannel(SocketChannel ch) throws Exception {
//            logger.debug("Starting initialization of server connection.");
            C connection = initRemoteConnection(ch);
            ch.closeFuture().addListener(getCloseHandler(ch, connection));

            final ChannelPipeline pipe = ch.pipeline();
            pipe.addLast("protocol-decoder", getDecoder(connection.getAllocator(), getOutOfMemoryHandler()));
            pipe.addLast("message-decoder", new RpcDecoder("s-" + rpcConfig.getName()));
            pipe.addLast("protocol-encoder", new RpcEncoder("s-" + rpcConfig.getName()));
            pipe.addLast("handshake-handler", getHandshakeHandler(connection));

            if (rpcMapping.hasTimeout()) {
              pipe.addLast(TIMEOUT_HANDLER,
                  new LogggingReadTimeoutHandler(connection, rpcMapping.getTimeout()));
            }

            pipe.addLast("message-handler", new InboundHandler(connection));
            pipe.addLast("exception-handler", new RpcExceptionHandler(connection));

            connect = true;
//            logger.debug("Server connection initialization completed.");
          }
        });

//     if(TransportCheck.SUPPORTS_EPOLL){
//       b.option(EpollChannelOption.SO_REUSEPORT, true); //
//     }
  }

  private class LogggingReadTimeoutHandler<C extends RemoteConnection> extends ReadTimeoutHandler {

    private final C connection;
    private final int timeoutSeconds;
    public LogggingReadTimeoutHandler(C connection, int timeoutSeconds) {
      super(timeoutSeconds);
      this.connection = connection;
      this.timeoutSeconds = timeoutSeconds;
    }

    @Override
    protected void readTimedOut(ChannelHandlerContext ctx) throws Exception {
      logger.info("RPC connection {} timed out.  Timeout was set to {} seconds. Closing connection.", connection.getName(),
          timeoutSeconds);
      super.readTimedOut(ctx);
    }

  }

  public OutOfMemoryHandler getOutOfMemoryHandler() {
    return OutOfMemoryHandler.DEFAULT_INSTANCE;
  }

  protected void removeTimeoutHandler() {

  }

  public abstract ProtobufLengthDecoder getDecoder(BufferAllocator allocator, OutOfMemoryHandler outOfMemoryHandler);

  @Override
  public boolean isClient() {
    return false;
  }

  protected abstract ServerHandshakeHandler<?> getHandshakeHandler(C connection);

  protected static abstract class ServerHandshakeHandler<T extends MessageLite> extends AbstractHandshakeHandler<T> {

    public ServerHandshakeHandler(EnumLite handshakeType, Parser<T> parser) {
      super(handshakeType, parser);
    }

    @Override
    protected void consumeHandshake(ChannelHandlerContext ctx, T inbound) throws Exception {
      OutboundRpcMessage msg = new OutboundRpcMessage(RpcMode.RESPONSE, this.handshakeType, coordinationId,
          getHandshakeResponse(inbound));
      ctx.writeAndFlush(msg);
    }

    public abstract MessageLite getHandshakeResponse(T inbound) throws Exception;

  }

  @Override
  protected MessageLite getResponseDefaultInstance(int rpcType) throws RpcException {
    return null;
  }

  @Override
  protected Response handle(C connection, int rpcType, ByteBuf pBody, ByteBuf dBody) throws RpcException {
    return null;
  }

  @Override
  public <SEND extends MessageLite, RECEIVE extends MessageLite> DrillRpcFuture<RECEIVE> send(C connection, T rpcType,
      SEND protobufBody, Class<RECEIVE> clazz, ByteBuf... dataBodies) {
    return super.send(connection, rpcType, protobufBody, clazz, dataBodies);
  }

  @Override
  public <SEND extends MessageLite, RECEIVE extends MessageLite> void send(RpcOutcomeListener<RECEIVE> listener,
      C connection, T rpcType, SEND protobufBody, Class<RECEIVE> clazz, ByteBuf... dataBodies) {
    super.send(listener, connection, rpcType, protobufBody, clazz, dataBodies);
  }

  @Override
  public C initRemoteConnection(SocketChannel channel) {
    local = channel.localAddress();
    remote = channel.remoteAddress();
    return null;
  }

  public int bind(final int initialPort, boolean allowPortHunting) throws DrillbitStartupException {
    int port = initialPort - 1;
    while (true) {
      try {
        b.bind(++port).sync();
        break;
      } catch (Exception e) {
        // TODO(DRILL-3026):  Revisit:  Exception is not (always) BindException.
        // One case is "java.io.IOException: bind() failed: Address already in
        // use".
        if (e instanceof BindException && allowPortHunting) {
          continue;
        }
        final UserException bindException =
            UserException
              .resourceError( e )
              .addContext( "Server type", getClass().getSimpleName() )
              .message( "Drillbit could not bind to port %s.", port )
              .build();
        throw bindException;
      }
    }

    connect = !connect;
    logger.debug("Server of type {} started on port {}.", getClass().getSimpleName(), port);
    return port;
  }

  @Override
  public void close() throws IOException {
    try {
      eventLoopGroup.shutdownGracefully().get();
    } catch (final InterruptedException | ExecutionException e) {
      logger.warn("Failure while shutting down {}. ", this.getClass().getName(), e);

      // Preserve evidence that the interruption occurred so that code higher up on the call stack can learn of the
      // interruption and respond to it if it wants to.
      Thread.currentThread().interrupt();
    }
  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/rpc/RpcBus.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.rpc;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufInputStream;
import io.netty.channel.Channel;
import io.netty.channel.ChannelFuture;
import io.netty.channel.ChannelFutureListener;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.socket.SocketChannel;
import io.netty.handler.codec.MessageToMessageDecoder;
import io.netty.util.concurrent.GenericFutureListener;

import java.io.Closeable;
import java.net.SocketAddress;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.TimeUnit;

import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.proto.GeneralRPCProtos.RpcMode;
import org.apache.drill.exec.proto.UserBitShared.DrillPBError;

import com.google.common.base.Preconditions;
import com.google.common.base.Stopwatch;
import com.google.protobuf.Internal.EnumLite;
import com.google.protobuf.InvalidProtocolBufferException;
import com.google.protobuf.MessageLite;
import com.google.protobuf.Parser;

/**
 * The Rpc Bus deals with incoming and outgoing communication and is used on both the server and the client side of a
 * system.
 *
 * @param <T>
 */
public abstract class RpcBus<T extends EnumLite, C extends RemoteConnection> implements Closeable {
  final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(this.getClass());

  protected final CoordinationQueue queue = new CoordinationQueue(16, 16);

  protected abstract MessageLite getResponseDefaultInstance(int rpcType) throws RpcException;

  protected void handle(C connection, int rpcType, ByteBuf pBody, ByteBuf dBody, ResponseSender sender) throws RpcException{
    sender.send(handle(connection, rpcType, pBody, dBody));
  }

  protected abstract Response handle(C connection, int rpcType, ByteBuf pBody, ByteBuf dBody) throws RpcException;

  public abstract boolean isClient();

  protected final RpcConfig rpcConfig;

  protected volatile SocketAddress local;
  protected volatile SocketAddress remote;


  public RpcBus(RpcConfig rpcConfig) {
    this.rpcConfig = rpcConfig;
  }

  protected void setAddresses(SocketAddress remote, SocketAddress local){
    this.remote = remote;
    this.local = local;
  }

  <SEND extends MessageLite, RECEIVE extends MessageLite> DrillRpcFuture<RECEIVE> send(C connection, T rpcType,
      SEND protobufBody, Class<RECEIVE> clazz, ByteBuf... dataBodies) {
    DrillRpcFutureImpl<RECEIVE> rpcFuture = new DrillRpcFutureImpl<RECEIVE>();
    this.send(rpcFuture, connection, rpcType, protobufBody, clazz, dataBodies);
    return rpcFuture;
  }

  public <SEND extends MessageLite, RECEIVE extends MessageLite> void send(RpcOutcomeListener<RECEIVE> listener, C connection, T rpcType,
      SEND protobufBody, Class<RECEIVE> clazz, ByteBuf... dataBodies) {
    send(listener, connection, rpcType, protobufBody, clazz, false, dataBodies);
  }

  public <SEND extends MessageLite, RECEIVE extends MessageLite> void send(RpcOutcomeListener<RECEIVE> listener, C connection, T rpcType,
      SEND protobufBody, Class<RECEIVE> clazz, boolean allowInEventLoop, ByteBuf... dataBodies) {

    Preconditions
        .checkArgument(
            allowInEventLoop || !connection.inEventLoop(),
            "You attempted to send while inside the rpc event thread.  This isn't allowed because sending will block if the channel is backed up.");

    ByteBuf pBuffer = null;
    boolean completed = false;

    try {

      if (!allowInEventLoop && !connection.blockOnNotWritable(listener)) {
        // if we're in not in the event loop and we're interrupted while blocking, skip sending this message.
        return;
      }

      assert !Arrays.asList(dataBodies).contains(null);
      assert rpcConfig.checkSend(rpcType, protobufBody.getClass(), clazz);

      Preconditions.checkNotNull(protobufBody);
      ChannelListenerWithCoordinationId futureListener = queue.get(listener, clazz, connection);
      OutboundRpcMessage m = new OutboundRpcMessage(RpcMode.REQUEST, rpcType, futureListener.getCoordinationId(), protobufBody, dataBodies);
      ChannelFuture channelFuture = connection.getChannel().writeAndFlush(m);
      channelFuture.addListener(futureListener);
      channelFuture.addListener(ChannelFutureListener.FIRE_EXCEPTION_ON_FAILURE);
      completed = true;
    } catch (Exception | AssertionError e) {
      listener.failed(new RpcException("Failure sending message.", e));
    } finally {
      if (!completed) {
        if (pBuffer != null) {
          pBuffer.release();
        }
        if (dataBodies != null) {
          for (ByteBuf b : dataBodies) {
            b.release();
          }

        }
      }
      ;
    }
  }

  public abstract C initRemoteConnection(SocketChannel channel);

  public class ChannelClosedHandler implements GenericFutureListener<ChannelFuture> {

    final C clientConnection;
    private final Channel channel;

    public ChannelClosedHandler(C clientConnection, Channel channel) {
      this.channel = channel;
      this.clientConnection = clientConnection;
    }

    @Override
    public void operationComplete(ChannelFuture future) throws Exception {
      String msg;
      if(local!=null) {
        msg = String.format("Channel closed %s <--> %s.", local, remote);
      }else{
        msg = String.format("Channel closed %s <--> %s.", future.channel().localAddress(), future.channel().remoteAddress());
      }

      if (RpcBus.this.isClient()) {
        if(local != null) {
          logger.info(String.format(msg));
        }
      } else {
        queue.channelClosed(new ChannelClosedException(msg));
      }

      clientConnection.close();
    }

  }

  protected GenericFutureListener<ChannelFuture> getCloseHandler(SocketChannel channel, C clientConnection) {
    return new ChannelClosedHandler(clientConnection, channel);
  }

  private class ResponseSenderImpl implements ResponseSender {

    RemoteConnection connection;
    int coordinationId;

    public ResponseSenderImpl(RemoteConnection connection, int coordinationId) {
      super();
      this.connection = connection;
      this.coordinationId = coordinationId;
    }

    public void send(Response r) {
      assert rpcConfig.checkResponseSend(r.rpcType, r.pBody.getClass());
      OutboundRpcMessage outMessage = new OutboundRpcMessage(RpcMode.RESPONSE, r.rpcType, coordinationId,
          r.pBody, r.dBodies);
      if (RpcConstants.EXTRA_DEBUGGING) {
        logger.debug("Adding message to outbound buffer. {}", outMessage);
      }
      logger.debug("Sending response with Sender {}", System.identityHashCode(this));
      connection.getChannel().writeAndFlush(outMessage);
    }

  }

  private static final OutboundRpcMessage PONG = new OutboundRpcMessage(RpcMode.PONG, 0, 0, Acks.OK);

  protected class InboundHandler extends MessageToMessageDecoder<InboundRpcMessage> {


    private final C connection;
    public InboundHandler(C connection) {
      super();
      this.connection = connection;
    }

    @Override
    protected void decode(final ChannelHandlerContext ctx, final InboundRpcMessage msg, final List<Object> output) throws Exception {
      if (!ctx.channel().isOpen()) {
        return;
      }
      if (RpcConstants.EXTRA_DEBUGGING) {
        logger.debug("Received message {}", msg);
      }
      final Channel channel = connection.getChannel();
      final Stopwatch watch = new Stopwatch().start();

      try{

        switch (msg.mode) {
        case REQUEST: {
          // handle message and ack.

          try {
            ResponseSender sender = new ResponseSenderImpl(connection, msg.coordinationId);
            handle(connection, msg.rpcType, msg.pBody, msg.dBody, sender);
          } catch (UserRpcException e) {
            UserException uex = UserException.systemError(e).addIdentity(e.getEndpoint()).build();

            logger.error("Unexpected Error while handling request message", e);

            OutboundRpcMessage outMessage = new OutboundRpcMessage(
                RpcMode.RESPONSE_FAILURE,
                0,
                msg.coordinationId,
                uex.getOrCreatePBError(false)
                );

            if (RpcConstants.EXTRA_DEBUGGING) {
              logger.debug("Adding message to outbound buffer. {}", outMessage);
            }

            channel.writeAndFlush(outMessage);
          }
          break;
        }

        case RESPONSE:
          try {
            MessageLite m = getResponseDefaultInstance(msg.rpcType);
            assert rpcConfig.checkReceive(msg.rpcType, m.getClass());
            RpcOutcome<?> rpcFuture = queue.getFuture(msg.rpcType, msg.coordinationId, m.getClass());
            Parser<?> parser = m.getParserForType();
            Object value = parser.parseFrom(new ByteBufInputStream(msg.pBody, msg.pBody.readableBytes()));
            rpcFuture.set(value, msg.dBody);
            if (RpcConstants.EXTRA_DEBUGGING) {
              logger.debug("Updated rpc future {} with value {}", rpcFuture, value);
            }
          } catch (Exception ex) {
            logger.error("Failure while handling response.", ex);
            throw ex;
          }
          break;

        case RESPONSE_FAILURE:
          DrillPBError failure = DrillPBError.parseFrom(new ByteBufInputStream(msg.pBody, msg.pBody.readableBytes()));
          queue.updateFailedFuture(msg.coordinationId, failure);
          if (RpcConstants.EXTRA_DEBUGGING) {
            logger.debug("Updated rpc future with coordinationId {} with failure ", msg.coordinationId, failure);
          }
          break;

        case PING:
          connection.getChannel().writeAndFlush(PONG);
          break;

        case PONG:
          // noop.
          break;

        default:
          throw new UnsupportedOperationException();
        }
      } finally {
        long time = watch.elapsed(TimeUnit.MILLISECONDS);
        long delayThreshold = Integer.parseInt(System.getProperty("drill.exec.rpcDelayWarning", "500"));
        if (time > delayThreshold) {
          logger.warn(String.format(
              "Message of mode %s of rpc type %d took longer than %dms.  Actual duration was %dms.",
              msg.mode, msg.rpcType, delayThreshold, time));
        }
        msg.release();
      }
    }
  }

  public static <T> T get(ByteBuf pBody, Parser<T> parser) throws RpcException{
    try {
      ByteBufInputStream is = new ByteBufInputStream(pBody);
      return parser.parseFrom(is);
    } catch (InvalidProtocolBufferException e) {
      throw new RpcException(String.format("Failure while decoding message with parser of type. %s", parser.getClass().getCanonicalName()), e);
    }
  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/rpc/user/QueryResultHandler.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.rpc.user;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.DrillBuf;
import io.netty.channel.ChannelFuture;
import io.netty.util.concurrent.Future;
import io.netty.util.concurrent.GenericFutureListener;

import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.atomic.AtomicBoolean;

import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.common.exceptions.UserRemoteException;
import org.apache.drill.exec.proto.UserBitShared.QueryData;
import org.apache.drill.exec.proto.UserBitShared.QueryId;
import org.apache.drill.exec.proto.UserBitShared.QueryResult;
import org.apache.drill.exec.proto.UserBitShared.QueryResult.QueryState;
import org.apache.drill.exec.proto.helper.QueryIdHelper;
import org.apache.drill.exec.rpc.BaseRpcOutcomeListener;
import org.apache.drill.exec.rpc.RemoteConnection;
import org.apache.drill.exec.rpc.RpcBus;
import org.apache.drill.exec.rpc.RpcException;
import org.apache.drill.exec.rpc.RpcOutcomeListener;

import com.google.common.collect.Maps;
import com.google.common.collect.Queues;

/**
 * Encapsulates the future management of query submissions.  This entails a
 * potential race condition.  Normal ordering is:
 * <ul>
 *   <li>1.  Submit query to be executed. </li>
 *   <li>2.  Receive QueryHandle for buffer management. </li>
 *   <li>3.  Start receiving results batches for query. </li>
 * </ul>
 * However, 3 could potentially occur before 2.   Because of that, we need to
 * handle this case and then do a switcheroo.
 */
public class QueryResultHandler {
  private static final org.slf4j.Logger logger =
      org.slf4j.LoggerFactory.getLogger(QueryResultHandler.class);

  /**
   * Current listener for results, for each active query.
   * <p>
   *   Concurrency:  Access by SubmissionLister for query-ID message vs.
   *   access by batchArrived is not otherwise synchronized.
   * </p>
   */
  private final ConcurrentMap<QueryId, UserResultsListener> queryIdToResultsListenersMap =
      Maps.newConcurrentMap();

  public RpcOutcomeListener<QueryId> getWrappedListener(RemoteConnection connection,
      UserResultsListener resultsListener) {
    return new SubmissionListener(connection, resultsListener);
  }

  /**
   * Maps internal low-level API protocol to {@link UserResultsListener}-level API protocol.
   * handles data result messages
   */
  public void resultArrived( ByteBuf pBody ) throws RpcException {
    final QueryResult queryResult = RpcBus.get( pBody, QueryResult.PARSER );

    final QueryId queryId = queryResult.getQueryId();
    final QueryState queryState = queryResult.getQueryState();

    logger.debug( "resultArrived: queryState: {}, queryId = {}", queryState, queryId );

    assert queryResult.hasQueryState() : "received query result without QueryState";

    final boolean isFailureResult = QueryState.FAILED == queryState;
    // CANCELED queries are handled the same way as COMPLETED
    final boolean isTerminalResult;
    switch ( queryState ) {
      case PENDING:
        isTerminalResult = false;
        break;
      case FAILED:
      case CANCELED:
      case COMPLETED:
        isTerminalResult = true;
        break;
      default:
        logger.error( "Unexpected/unhandled QueryState " + queryState
          + " (for query " + queryId +  ")" );
        isTerminalResult = false;
        break;
    }

    assert isFailureResult || queryResult.getErrorCount() == 0
      : "Error count for the query batch is non-zero but QueryState != FAILED";

    UserResultsListener resultsListener = newUserResultsListener(queryId);

    try {
      if (isFailureResult) {
        // Failure case--pass on via submissionFailed(...).

        resultsListener.submissionFailed(new UserRemoteException(queryResult.getError(0)));
        // Note: Listener is removed in finally below.
      } else if (isTerminalResult) {
        // A successful completion/canceled case--pass on via resultArrived

        try {
          resultsListener.queryCompleted(queryState);
        } catch ( Exception e ) {
          resultsListener.submissionFailed(UserException.systemError(e).build());
        }
      } else {
        logger.warn("queryState {} was ignored", queryState);
      }
    } finally {
      if ( isTerminalResult ) {
        // TODO:  What exactly are we checking for?  How should we really check
        // for it?
        if ( (! ( resultsListener instanceof BufferingResultsListener )
          || ((BufferingResultsListener) resultsListener).output != null ) ) {
          queryIdToResultsListenersMap.remove( queryId, resultsListener );
        }
      }
    }
  }

  /**
   * Maps internal low-level API protocol to {@link UserResultsListener}-level API protocol.
   * handles query data messages
   */
  public void batchArrived( ConnectionThrottle throttle,
                            ByteBuf pBody, ByteBuf dBody ) throws RpcException {
    final QueryData queryData = RpcBus.get( pBody, QueryData.PARSER );
    // Current batch coming in.
    final QueryDataBatch batch = new QueryDataBatch( queryData, (DrillBuf) dBody );

    final QueryId queryId = queryData.getQueryId();

    logger.debug( "batchArrived: queryId = {}", queryId );
    logger.trace( "batchArrived: batch = {}", batch );

    UserResultsListener resultsListener = newUserResultsListener(queryId);

    // A data case--pass on via dataArrived

    try {
      resultsListener.dataArrived(batch, throttle);
      // That releases batch if successful.
    } catch ( Exception e ) {
      batch.release();
      resultsListener.submissionFailed(UserException.systemError(e).build());
    }
  }

  /**
   * Return {@link UserResultsListener} associated with queryId. Will create a new {@link BufferingResultsListener}
   * if no listener found.
   * @param queryId queryId we are getting the listener for
   * @return {@link UserResultsListener} associated with queryId
   */
  private UserResultsListener newUserResultsListener(QueryId queryId) {
    UserResultsListener resultsListener = queryIdToResultsListenersMap.get( queryId );
    logger.trace( "For QueryId [{}], retrieved results listener {}", queryId, resultsListener );
    if ( null == resultsListener ) {
      // WHO?? didn't get query ID response and set submission listener yet,
      // so install a buffering listener for now

      BufferingResultsListener bl = new BufferingResultsListener();
      resultsListener = queryIdToResultsListenersMap.putIfAbsent( queryId, bl );
      // If we had a successful insertion, use that reference.  Otherwise, just
      // throw away the new buffering listener.
      if ( null == resultsListener ) {
        resultsListener = bl;
      }
      // TODO:  Is there a more direct way to detect a Query ID in whatever state this string comparison detects?
      if ( queryId.toString().isEmpty() ) {
        failAll();
      }
    }
    return resultsListener;
  }

  private void failAll() {
    for (UserResultsListener l : queryIdToResultsListenersMap.values()) {
      l.submissionFailed(UserException.systemError(new RpcException("Received result without QueryId")).build());
    }
  }

  private static class BufferingResultsListener implements UserResultsListener {

    private ConcurrentLinkedQueue<QueryDataBatch> results = Queues.newConcurrentLinkedQueue();
    private volatile UserException ex;
    private volatile QueryState queryState;
    private volatile UserResultsListener output;
    private volatile ConnectionThrottle throttle;

    public boolean transferTo(UserResultsListener l) {
      synchronized (this) {
        output = l;
        for (QueryDataBatch r : results) {
          l.dataArrived(r, throttle);
        }
        if (ex != null) {
          l.submissionFailed(ex);
          return true;
        } else if (queryState != null) {
          l.queryCompleted(queryState);
          return true;
        }

        return false;
      }
    }

    @Override
    public void queryCompleted(QueryState state) {
      assert queryState == null;
      this.queryState = state;
      synchronized (this) {
        if (output != null) {
          output.queryCompleted(state);
        }
      }
    }

    @Override
    public void dataArrived(QueryDataBatch result, ConnectionThrottle throttle) {
      this.throttle = throttle;

      synchronized (this) {
        if (output == null) {
          this.results.add(result);
        } else {
          output.dataArrived(result, throttle);
        }
      }
    }

    @Override
    public void submissionFailed(UserException ex) {
      assert queryState == null;
      // there is one case when submissionFailed() is called even though the query didn't fail on the server side
      // it happens when UserResultsListener.batchArrived() throws an exception that will be passed to
      // submissionFailed() by QueryResultHandler.dataArrived()
      queryState = QueryState.FAILED;
      synchronized (this) {
        if (output == null) {
          this.ex = ex;
        } else{
          output.submissionFailed(ex);
        }
      }
    }

    @Override
    public void queryIdArrived(QueryId queryId) {
    }

  }


  private class SubmissionListener extends BaseRpcOutcomeListener<QueryId> {
    private final UserResultsListener resultsListener;
    private final RemoteConnection connection;
    private final ChannelFuture closeFuture;
    private final ChannelClosedListener closeListener;
    private final AtomicBoolean isTerminal = new AtomicBoolean(false);

    public SubmissionListener(RemoteConnection connection, UserResultsListener resultsListener) {
      super();
      this.resultsListener = resultsListener;
      this.connection = connection;
      this.closeFuture = connection.getChannel().closeFuture();
      this.closeListener = new ChannelClosedListener();
      closeFuture.addListener(closeListener);
    }

    private class ChannelClosedListener implements GenericFutureListener<Future<Void>> {

      @Override
      public void operationComplete(Future<Void> future) throws Exception {
        resultsListener.submissionFailed(UserException.connectionError()
            .message("Connection %s closed unexpectedly.", connection.getName())
            .build());
      }

    }

    @Override
    public void failed(RpcException ex) {
      if (!isTerminal.compareAndSet(false, true)) {
        return;
      }

      closeFuture.removeListener(closeListener);
      resultsListener.submissionFailed(UserException.systemError(ex).build());

    }

    @Override
    public void success(QueryId queryId, ByteBuf buf) {
      if (!isTerminal.compareAndSet(false, true)) {
        return;
      }

      closeFuture.removeListener(closeListener);
      resultsListener.queryIdArrived(queryId);
      if (logger.isDebugEnabled()) {
        logger.debug("Received QueryId {} successfully. Adding results listener {}.",
          QueryIdHelper.getQueryId(queryId), resultsListener);
      }
      UserResultsListener oldListener =
          queryIdToResultsListenersMap.putIfAbsent(queryId, resultsListener);

      // We need to deal with the situation where we already received results by
      // the time we got the query id back.  In that case, we'll need to
      // transfer the buffering listener over, grabbing a lock against reception
      // of additional results during the transition.
      if (oldListener != null) {
        logger.debug("Unable to place user results listener, buffering listener was already in place.");
        if (oldListener instanceof BufferingResultsListener) {
          boolean all = ((BufferingResultsListener) oldListener).transferTo(this.resultsListener);
          // simply remove the buffering listener if we already have the last response.
          if (all) {
            queryIdToResultsListenersMap.remove(queryId);
          } else {
            boolean replaced = queryIdToResultsListenersMap.replace(queryId, oldListener, resultsListener);
            if (!replaced) {
              throw new IllegalStateException(); // TODO: Say what the problem is!
            }
          }
        } else {
          throw new IllegalStateException("Trying to replace a non-buffering User Results listener.");
        }
      }
    }

    @Override
    public void interrupted(final InterruptedException ex) {
      logger.warn("Interrupted while waiting for query results from Drillbit", ex);

      if (!isTerminal.compareAndSet(false, true)) {
        return;
      }

      closeFuture.removeListener(closeListener);

      // Throw an interrupted UserException?
      resultsListener.submissionFailed(UserException.systemError(ex).build());
    }
  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/store/AbstractSchema.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.store;

import java.io.IOException;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Set;

import org.apache.calcite.linq4j.tree.DefaultExpression;
import org.apache.calcite.linq4j.tree.Expression;
import org.apache.calcite.schema.Function;
import org.apache.calcite.schema.Schema;
import org.apache.calcite.schema.SchemaPlus;
import org.apache.calcite.schema.Table;

import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.common.expression.SchemaPath;
import org.apache.drill.exec.dotdrill.View;
import org.apache.drill.exec.planner.logical.CreateTableEntry;

import com.google.common.base.Joiner;
import com.google.common.collect.Lists;

public abstract class AbstractSchema implements Schema, SchemaPartitionExplorer {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(AbstractSchema.class);

  protected final List<String> schemaPath;
  protected final String name;
  private static final Expression EXPRESSION = new DefaultExpression(Object.class);

  public AbstractSchema(List<String> parentSchemaPath, String name) {
    schemaPath = Lists.newArrayList();
    schemaPath.addAll(parentSchemaPath);
    schemaPath.add(name);
    this.name = name;
  }

  @Override
  public Iterable<String> getSubPartitions(String table,
                                           List<String> partitionColumns,
                                           List<String> partitionValues
                                          ) throws PartitionNotFoundException {
    throw new UnsupportedOperationException(
        String.format("Schema of type: %s " +
                      "does not support retrieving sub-partition information.",
                      this.getClass().getSimpleName()));
  }

  public String getName() {
    return name;
  }

  public List<String> getSchemaPath() {
    return schemaPath;
  }

  public String getFullSchemaName() {
    return Joiner.on(".").join(schemaPath);
  }

  public abstract String getTypeName();

  /**
   * The schema can be a top level schema which doesn't have its own tables, but refers
   * to one of the default sub schemas for table look up.
   *
   * Default implementation returns itself.
   *
   * Ex. "dfs" schema refers to the tables in "default" workspace when querying for
   * tables in "dfs" schema.
   *
   * @return Return the default schema where tables are created or retrieved from.
   */
  public AbstractSchema getDefaultSchema() {
    return this;
  }

  /**
   * Create a new view given definition.
   * @param view View info including name, definition etc.
   * @return Returns true if an existing view is replaced with the given view. False otherwise.
   * @throws IOException
   */
  public boolean createView(View view) throws IOException {
    throw UserException.unsupportedError()
        .message("Creating new view is not supported in schema [%s]", getSchemaPath())
        .build();
  }

  /**
   * Drop the view with given name.
   *
   * @param viewName
   * @throws IOException
   */
  public void dropView(String viewName) throws IOException {
    throw UserException.unsupportedError()
        .message("Dropping a view is supported in schema [%s]", getSchemaPath())
        .build();
  }

  /**
   *
   * @param tableName : new table name.
   * @param partitionColumns : list of partition columns. Empty list if there is no partition columns.
   * @return
   */
  public CreateTableEntry createNewTable(String tableName, List<String> partitionColumns) {
    throw UserException.unsupportedError()
        .message("Creating new tables is not supported in schema [%s]", getSchemaPath())
        .build();
  }

  /**
   * Reports whether to show items from this schema in INFORMATION_SCHEMA
   * tables.
   * (Controls ... TODO:  Doc.:  Mention what this typically controls or
   * affects.)
   * <p>
   *   This base implementation returns {@code true}.
   * </p>
   */
  public boolean showInInformationSchema() {
    return true;
  }

  @Override
  public Collection<Function> getFunctions(String name) {
    return Collections.emptyList();
  }

  @Override
  public Set<String> getFunctionNames() {
    return Collections.emptySet();
  }

  @Override
  public AbstractSchema getSubSchema(String name) {
    return null;
  }

  @Override
  public Set<String> getSubSchemaNames() {
    return Collections.emptySet();
  }

  @Override
  public boolean isMutable() {
    return false;
  }

  @Override
  public Table getTable(String name){
    return null;
  }

  @Override
  public Set<String> getTableNames() {
    return Collections.emptySet();
  }

  @Override
  public Expression getExpression(SchemaPlus parentSchema, String name) {
    return EXPRESSION;
  }

  @Override
  public boolean contentsHaveChangedSince(long lastCheck, long now) {
    return true;
  }


}


File: exec/java-exec/src/main/java/org/apache/drill/exec/store/TimedRunnable.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.store;

import java.io.IOException;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import org.apache.drill.common.concurrent.ExtendedLatch;
import org.apache.drill.common.exceptions.UserException;
import org.slf4j.Logger;

import com.google.common.base.Stopwatch;
import com.google.common.collect.Lists;

/**
 * Class used to allow parallel executions of tasks in a simplified way. Also maintains and reports timings of task completion.
 * TODO: look at switching to fork join.
 * @param <V> The time value that will be returned when the task is executed.
 */
public abstract class TimedRunnable<V> implements Runnable {

  private static long TIMEOUT_PER_RUNNABLE_IN_MSECS = 15000;

  private volatile Exception e;
  private volatile long threadStart;
  private volatile long timeNanos;
  private volatile V value;

  @Override
  public final void run() {
    long start = System.nanoTime();
    threadStart=start;
    try{
      value = runInner();
    }catch(Exception e){
      this.e = e;
    }finally{
      timeNanos = System.nanoTime() - start;
    }
  }

  protected abstract V runInner() throws Exception ;
  protected abstract IOException convertToIOException(Exception e);

  public long getThreadStart(){
    return threadStart;
  }
  public long getTimeSpentNanos(){
    return timeNanos;
  }

  public final V getValue() throws IOException {
    if(e != null){
      if(e instanceof IOException){
        throw (IOException) e;
      }else{
        throw convertToIOException(e);
      }
    }

    return value;
  }

  private static class LatchedRunnable implements Runnable {
    final CountDownLatch latch;
    final Runnable runnable;

    public LatchedRunnable(CountDownLatch latch, Runnable runnable){
      this.latch = latch;
      this.runnable = runnable;
    }

    @Override
    public void run() {
      try{
        runnable.run();
      }finally{
        latch.countDown();
      }
    }
  }

  /**
   * Execute the list of runnables with the given parallelization.  At end, return values and report completion time
   * stats to provided logger. Each runnable is allowed a certain timeout. If the timeout exceeds, existing/pending
   * tasks will be cancelled and a {@link UserException} is thrown.
   * @param activity Name of activity for reporting in logger.
   * @param logger The logger to use to report results.
   * @param runnables List of runnables that should be executed and timed.  If this list has one item, task will be
   *                  completed in-thread. Runnable must handle {@link InterruptedException}s.
   * @param parallelism  The number of threads that should be run to complete this task.
   * @return The list of outcome objects.
   * @throws IOException All exceptions are coerced to IOException since this was build for storage system tasks initially.
   */
  public static <V> List<V> run(final String activity, final Logger logger, final List<TimedRunnable<V>> runnables, int parallelism) throws IOException {
    Stopwatch watch = new Stopwatch().start();
    long timedRunnableStart=System.nanoTime();
    if(runnables.size() == 1){
      parallelism = 1;
      runnables.get(0).run();
    }else{
      parallelism = Math.min(parallelism,  runnables.size());
      final ExtendedLatch latch = new ExtendedLatch(runnables.size());
      final ExecutorService threadPool = Executors.newFixedThreadPool(parallelism);
      try{
        for(TimedRunnable<V> runnable : runnables){
          threadPool.submit(new LatchedRunnable(latch, runnable));
        }

        final long timeout = (long)Math.ceil((TIMEOUT_PER_RUNNABLE_IN_MSECS * runnables.size())/parallelism);
        if (!latch.awaitUninterruptibly(timeout)) {
          // Issue a shutdown request. This will cause existing threads to interrupt and pending threads to cancel.
          // It is highly important that the task Runnables are handling interrupts correctly.
          threadPool.shutdownNow();

          try {
            // Wait for 5s for currently running threads to terminate. Above call (threadPool.shutdownNow()) interrupts
            // any running threads. If the runnables are handling the interrupts properly they should be able to
            // wrap up and terminate. If not waiting for 5s here gives a chance to identify and log any potential
            // thread leaks.
            threadPool.awaitTermination(5, TimeUnit.SECONDS);
          } catch (final InterruptedException e) {
            logger.warn("Interrupted while waiting for pending threads in activity '{}' to terminate.", activity);
          }

          final String errMsg = String.format("Waited for %dms, but tasks for '%s' are not complete. " +
              "Total runnable size %d, parallelism %d.", timeout, activity, runnables.size(), parallelism);
          logger.error(errMsg);
          throw UserException.resourceError()
              .message(errMsg)
              .build();
        }
      } finally {
        if (!threadPool.isShutdown()) {
          threadPool.shutdown();
        }
      }
    }

    List<V> values = Lists.newArrayList();
    long sum = 0;
    long max = 0;
    long count = 0;
    // measure thread creation times
    long earliestStart=Long.MAX_VALUE;
    long latestStart=0;
    long totalStart=0;
    IOException excep = null;
    for(final TimedRunnable<V> reader : runnables){
      try{
        values.add(reader.getValue());
        sum += reader.getTimeSpentNanos();
        count++;
        max = Math.max(max, reader.getTimeSpentNanos());
        earliestStart=Math.min(earliestStart, reader.getThreadStart() - timedRunnableStart);
        latestStart=Math.max(latestStart, reader.getThreadStart()-timedRunnableStart);
        totalStart+=latestStart=Math.max(latestStart, reader.getThreadStart()-timedRunnableStart);
      }catch(IOException e){
        if(excep == null){
          excep = e;
        }else{
          excep.addSuppressed(e);
        }
      }
    }

    if(logger.isInfoEnabled()){
      double avg = (sum/1000.0/1000.0)/(count*1.0d);
      double avgStart = (totalStart/1000.0)/(count*1.0d);

      logger.info(
          String.format("%s: Executed %d out of %d using %d threads. "
              + "Time: %dms total, %fms avg, %dms max.",
              activity, count, runnables.size(), parallelism, watch.elapsed(TimeUnit.MILLISECONDS), avg, max/1000/1000));
      logger.info(
              String.format("%s: Executed %d out of %d using %d threads. "
                              + "Earliest start: %f \u03BCs, Latest start: %f \u03BCs, Average start: %f \u03BCs .",
                      activity, count, runnables.size(), parallelism, earliestStart/1000.0, latestStart/1000.0, avgStart));
    }

    if(excep != null) {
      throw excep;
    }

    return values;

  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/store/dfs/WorkspaceSchemaFactory.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.store.dfs;

import java.io.IOException;
import java.io.OutputStream;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;

import com.google.common.base.Strings;
import com.google.common.collect.ImmutableList;
import org.apache.calcite.schema.Table;

import org.apache.drill.common.config.DrillConfig;
import org.apache.drill.common.exceptions.ExecutionSetupException;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.common.expression.SchemaPath;
import org.apache.drill.exec.ExecConstants;
import org.apache.drill.exec.dotdrill.DotDrillFile;
import org.apache.drill.exec.dotdrill.DotDrillType;
import org.apache.drill.exec.dotdrill.DotDrillUtil;
import org.apache.drill.exec.dotdrill.View;
import org.apache.drill.exec.planner.logical.CreateTableEntry;
import org.apache.drill.exec.planner.logical.DrillTable;
import org.apache.drill.exec.planner.logical.DrillViewTable;
import org.apache.drill.exec.planner.logical.DynamicDrillTable;
import org.apache.drill.exec.planner.logical.FileSystemCreateTableEntry;
import org.apache.drill.exec.planner.sql.ExpandingConcurrentMap;
import org.apache.drill.exec.store.AbstractSchema;
import org.apache.drill.exec.store.PartitionNotFoundException;
import org.apache.drill.exec.store.SchemaConfig;
import org.apache.drill.exec.util.ImpersonationUtil;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.FileStatus;
import org.apache.hadoop.fs.Path;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.common.base.Joiner;
import com.google.common.collect.Lists;
import com.google.common.collect.Sets;
import org.apache.hadoop.fs.permission.FsPermission;
import org.apache.hadoop.security.AccessControlException;

public class WorkspaceSchemaFactory {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(WorkspaceSchemaFactory.class);

  private final List<FormatMatcher> fileMatchers;
  private final List<FormatMatcher> dirMatchers;

  private final WorkspaceConfig config;
  private final Configuration fsConf;
  private final DrillConfig drillConfig;
  private final String storageEngineName;
  private final String schemaName;
  private final FileSystemPlugin plugin;
  private final ObjectMapper mapper;

  public WorkspaceSchemaFactory(DrillConfig drillConfig, FileSystemPlugin plugin, String schemaName,
      String storageEngineName, WorkspaceConfig config, List<FormatMatcher> formatMatchers)
    throws ExecutionSetupException, IOException {
    this.fsConf = plugin.getFsConf();
    this.plugin = plugin;
    this.drillConfig = drillConfig;
    this.config = config;
    this.mapper = drillConfig.getMapper();
    this.fileMatchers = Lists.newArrayList();
    this.dirMatchers = Lists.newArrayList();
    this.storageEngineName = storageEngineName;
    this.schemaName = schemaName;

    for (FormatMatcher m : formatMatchers) {
      if (m.supportDirectoryReads()) {
        dirMatchers.add(m);
      }
      fileMatchers.add(m);
    }

    // NOTE: Add fallback format matcher if given in the configuration. Make sure fileMatchers is an order-preserving list.
    final String defaultInputFormat = config.getDefaultInputFormat();
    if (!Strings.isNullOrEmpty(defaultInputFormat)) {
      final FormatPlugin formatPlugin = plugin.getFormatPlugin(defaultInputFormat);
      if (formatPlugin == null) {
        final String message = String.format("Unable to find default input format[%s] for workspace[%s.%s]",
            defaultInputFormat, storageEngineName, schemaName);
        throw new ExecutionSetupException(message);
      }
      final FormatMatcher fallbackMatcher = new BasicFormatMatcher(formatPlugin,
          ImmutableList.of(Pattern.compile(".*")), ImmutableList.<MagicString>of());
      fileMatchers.add(fallbackMatcher);
    }
  }

  private Path getViewPath(String name) {
    return DotDrillType.VIEW.getPath(config.getLocation(), name);
  }

  public WorkspaceSchema createSchema(List<String> parentSchemaPath, SchemaConfig schemaConfig) throws  IOException {
    return new WorkspaceSchema(parentSchemaPath, schemaName, schemaConfig);
  }

  public class WorkspaceSchema extends AbstractSchema implements ExpandingConcurrentMap.MapValueFactory<String, DrillTable> {
    private final ExpandingConcurrentMap<String, DrillTable> tables = new ExpandingConcurrentMap<>(this);
    private final SchemaConfig schemaConfig;
    private final DrillFileSystem fs;

    public WorkspaceSchema(List<String> parentSchemaPath, String wsName, SchemaConfig schemaConfig) throws IOException {
      super(parentSchemaPath, wsName);
      this.schemaConfig = schemaConfig;
      this.fs = ImpersonationUtil.createFileSystem(schemaConfig.getUserName(), fsConf);
    }

    @Override
    public boolean createView(View view) throws IOException {
      Path viewPath = getViewPath(view.getName());
      boolean replaced = fs.exists(viewPath);
      final FsPermission viewPerms =
          new FsPermission(schemaConfig.getOption(ExecConstants.NEW_VIEW_DEFAULT_PERMS_KEY).string_val);
      try (OutputStream stream = DrillFileSystem.create(fs, viewPath, viewPerms)) {
        mapper.writeValue(stream, view);
      }
      return replaced;
    }

    @Override
    public Iterable<String> getSubPartitions(String table,
                                             List<String> partitionColumns,
                                             List<String> partitionValues
    ) throws PartitionNotFoundException {

      List<FileStatus> fileStatuses;
      try {
        fileStatuses = getFS().list(false, new Path(getDefaultLocation(), table));
      } catch (IOException e) {
        throw new PartitionNotFoundException("Error finding partitions for table " + table, e);
      }
      return new SubDirectoryList(fileStatuses);
    }

    @Override
    public void dropView(String viewName) throws IOException {
      fs.delete(getViewPath(viewName), false);
    }

    private Set<String> getViews() {
      Set<String> viewSet = Sets.newHashSet();
      // Look for files with ".view.drill" extension.
      List<DotDrillFile> files;
      try {
        files = DotDrillUtil.getDotDrills(fs, new Path(config.getLocation()), DotDrillType.VIEW);
        for(DotDrillFile f : files) {
          viewSet.add(f.getBaseName());
        }
      } catch (UnsupportedOperationException e) {
        logger.debug("The filesystem for this workspace does not support this operation.", e);
      } catch (AccessControlException e) {
        if (!schemaConfig.getIgnoreAuthErrors()) {
          logger.debug(e.getMessage());
          throw UserException
              .permissionError(e)
              .message("Not authorized to list view tables in schema [%s]", getFullSchemaName())
              .build();
        }
      } catch (Exception e) {
        logger.warn("Failure while trying to list .view.drill files in workspace [{}]", getFullSchemaName(), e);
      }

      return viewSet;
    }

    @Override
    public Set<String> getTableNames() {
      return Sets.union(tables.keySet(), getViews());
    }

    private View getView(DotDrillFile f) throws IOException{
      assert f.getType() == DotDrillType.VIEW;
      return f.getView(drillConfig);
    }

    @Override
    public Table getTable(String name) {
      // first check existing tables.
      if(tables.alreadyContainsKey(name)) {
        return tables.get(name);
      }

      // then look for files that start with this name and end in .drill.
      List<DotDrillFile> files = Collections.EMPTY_LIST;
      try {
        try {
          files = DotDrillUtil.getDotDrills(fs, new Path(config.getLocation()), name, DotDrillType.VIEW);
        } catch(AccessControlException e) {
          if (!schemaConfig.getIgnoreAuthErrors()) {
            logger.debug(e.getMessage());
            throw UserException
                .permissionError(e)
                .message("Not authorized to list or query tables in schema [%s]", getFullSchemaName())
                .build();
          }
        } catch(IOException e) {
          logger.warn("Failure while trying to list view tables in workspace [{}]", name, getFullSchemaName(), e);
        }

        for(DotDrillFile f : files) {
          switch(f.getType()) {
          case VIEW:
            try {
              return new DrillViewTable(getView(f), f.getOwner(), schemaConfig.getViewExpansionContext());
            } catch (AccessControlException e) {
              if (!schemaConfig.getIgnoreAuthErrors()) {
                logger.debug(e.getMessage());
                throw UserException
                    .permissionError(e)
                    .message("Not authorized to read view [%s] in schema [%s]", name, getFullSchemaName())
                    .build();
              }
            } catch (IOException e) {
              logger.warn("Failure while trying to load {}.view.drill file in workspace [{}]", name, getFullSchemaName(), e);
            }
          }
        }
      } catch (UnsupportedOperationException e) {
        logger.debug("The filesystem for this workspace does not support this operation.", e);
      }

      return tables.get(name);
    }

    @Override
    public boolean isMutable() {
      return config.isWritable();
    }

    public DrillFileSystem getFS() {
      return fs;
    }

    public String getDefaultLocation() {
      return config.getLocation();
    }

    @Override
    public CreateTableEntry createNewTable(String tableName, List<String> partitonColumns) {
      String storage = schemaConfig.getOption(ExecConstants.OUTPUT_FORMAT_OPTION).string_val;
      FormatPlugin formatPlugin = plugin.getFormatPlugin(storage);
      if (formatPlugin == null) {
        throw new UnsupportedOperationException(
          String.format("Unsupported format '%s' in workspace '%s'", config.getDefaultInputFormat(),
              Joiner.on(".").join(getSchemaPath())));
      }

      return new FileSystemCreateTableEntry(
          (FileSystemConfig) plugin.getConfig(),
          formatPlugin,
          config.getLocation() + Path.SEPARATOR + tableName,
          partitonColumns);
    }

    @Override
    public String getTypeName() {
      return FileSystemConfig.NAME;
    }

    @Override
    public DrillTable create(String key) {
      try {

        FileSelection fileSelection = FileSelection.create(fs, config.getLocation(), key);
        if (fileSelection == null) {
          return null;
        }

        if (fileSelection.containsDirectories(fs)) {
          for (FormatMatcher m : dirMatchers) {
            try {
              Object selection = m.isReadable(fs, fileSelection);
              if (selection != null) {
                return new DynamicDrillTable(plugin, storageEngineName, schemaConfig.getUserName(), selection);
              }
            } catch (IOException e) {
              logger.debug("File read failed.", e);
            }
          }
          fileSelection = fileSelection.minusDirectories(fs);
        }

        for (FormatMatcher m : fileMatchers) {
          Object selection = m.isReadable(fs, fileSelection);
          if (selection != null) {
            return new DynamicDrillTable(plugin, storageEngineName, schemaConfig.getUserName(), selection);
          }
        }
        return null;

      } catch (AccessControlException e) {
        if (!schemaConfig.getIgnoreAuthErrors()) {
          logger.debug(e.getMessage());
          throw UserException
              .permissionError(e)
              .message("Not authorized to read table [%s] in schema [%s]", key, getFullSchemaName())
              .build();
        }
      } catch (IOException e) {
        logger.debug("Failed to create DrillTable with root {} and name {}", config.getLocation(), key, e);
      }

      return null;
    }

    @Override
    public void destroy(DrillTable value) {
    }
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/store/easy/json/JSONRecordReader.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.store.easy.json;

import java.io.IOException;
import java.io.InputStream;
import java.util.List;

import org.apache.drill.common.exceptions.ExecutionSetupException;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.common.expression.SchemaPath;
import org.apache.drill.exec.ExecConstants;
import org.apache.drill.exec.memory.OutOfMemoryException;
import org.apache.drill.exec.ops.FragmentContext;
import org.apache.drill.exec.ops.OperatorContext;
import org.apache.drill.exec.physical.impl.OutputMutator;
import org.apache.drill.exec.store.AbstractRecordReader;
import org.apache.drill.exec.store.dfs.DrillFileSystem;
import org.apache.drill.exec.store.easy.json.JsonProcessor.ReadState;
import org.apache.drill.exec.store.easy.json.reader.CountingJsonReader;
import org.apache.drill.exec.vector.BaseValueVector;
import org.apache.drill.exec.vector.complex.fn.JsonReader;
import org.apache.drill.exec.vector.complex.impl.VectorContainerWriter;
import org.apache.hadoop.fs.Path;

import com.fasterxml.jackson.core.JsonParseException;
import com.fasterxml.jackson.databind.JsonNode;
import com.google.common.base.Preconditions;
import com.google.common.collect.ImmutableList;

public class JSONRecordReader extends AbstractRecordReader {
  private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(JSONRecordReader.class);

  private VectorContainerWriter writer;

  // Data we're consuming
  private Path hadoopPath;
  private JsonNode embeddedContent;
  private InputStream stream;
  private final DrillFileSystem fileSystem;
  private JsonProcessor jsonReader;
  private int recordCount;
  private long runningRecordCount = 0;
  private final FragmentContext fragmentContext;
  private OperatorContext operatorContext;
  private final boolean enableAllTextMode;
  private final boolean readNumbersAsDouble;

  /**
   * Create a JSON Record Reader that uses a file based input stream.
   * @param fragmentContext
   * @param inputPath
   * @param fileSystem
   * @param columns
   * @throws OutOfMemoryException
   */
  public JSONRecordReader(final FragmentContext fragmentContext, final String inputPath, final DrillFileSystem fileSystem,
      final List<SchemaPath> columns) throws OutOfMemoryException {
    this(fragmentContext, inputPath, null, fileSystem, columns);
  }

  /**
   * Create a new JSON Record Reader that uses a in memory materialized JSON stream.
   * @param fragmentContext
   * @param embeddedContent
   * @param fileSystem
   * @param columns
   * @throws OutOfMemoryException
   */
  public JSONRecordReader(final FragmentContext fragmentContext, final JsonNode embeddedContent, final DrillFileSystem fileSystem,
      final List<SchemaPath> columns) throws OutOfMemoryException {
    this(fragmentContext, null, embeddedContent, fileSystem, columns);
  }

  private JSONRecordReader(final FragmentContext fragmentContext, final String inputPath, final JsonNode embeddedContent, final DrillFileSystem fileSystem,
                          final List<SchemaPath> columns) throws OutOfMemoryException {

    Preconditions.checkArgument(
        (inputPath == null && embeddedContent != null) ||
        (inputPath != null && embeddedContent == null),
        "One of inputPath or embeddedContent must be set but not both."
        );

    if(inputPath != null){
      this.hadoopPath = new Path(inputPath);
    }else{
      this.embeddedContent = embeddedContent;
    }

    this.fileSystem = fileSystem;
    this.fragmentContext = fragmentContext;

    // only enable all text mode if we aren't using embedded content mode.
    this.enableAllTextMode = embeddedContent == null && fragmentContext.getOptions().getOption(ExecConstants.JSON_READER_ALL_TEXT_MODE_VALIDATOR);
    this.readNumbersAsDouble = fragmentContext.getOptions().getOption(ExecConstants.JSON_READ_NUMBERS_AS_DOUBLE).bool_val;
    setColumns(columns);
  }

  @Override
  public void setup(final OperatorContext context, final OutputMutator output) throws ExecutionSetupException {
    this.operatorContext = context;
    try{
      if (hadoopPath != null) {
        this.stream = fileSystem.openPossiblyCompressedStream(hadoopPath);
      }

      this.writer = new VectorContainerWriter(output);
      if (isSkipQuery()) {
        this.jsonReader = new CountingJsonReader(fragmentContext.getManagedBuffer());
      } else {
        this.jsonReader = new JsonReader(fragmentContext.getManagedBuffer(), ImmutableList.copyOf(getColumns()), enableAllTextMode, true, readNumbersAsDouble);
      }
      setupParser();
    }catch(final Exception e){
      handleAndRaise("Failure reading JSON file", e);
    }
  }

  private void setupParser() throws IOException{
    if(hadoopPath != null){
      jsonReader.setSource(stream);
    }else{
      jsonReader.setSource(embeddedContent);
    }
  }

  protected void handleAndRaise(String suffix, Exception e) throws UserException {

    String message = e.getMessage();
    int columnNr = -1;

    if (e instanceof JsonParseException) {
      final JsonParseException ex = (JsonParseException) e;
      message = ex.getOriginalMessage();
      columnNr = ex.getLocation().getColumnNr();
    }

    UserException.Builder exceptionBuilder = UserException.dataReadError(e)
            .message("%s - %s", suffix, message);
    if (columnNr > 0) {
      exceptionBuilder.pushContext("Column ", columnNr);
    }
    exceptionBuilder.pushContext("Record ", currentRecordNumberInFile())
            .pushContext("File ", hadoopPath.toUri().getPath());

    throw exceptionBuilder.build();
  }

  private long currentRecordNumberInFile() {
    return runningRecordCount + recordCount + 1;
  }

  @Override
  public int next() {
    writer.allocate();
    writer.reset();

    recordCount = 0;
    ReadState write = null;
//    Stopwatch p = new Stopwatch().start();
    try{
      outside: while(recordCount < BaseValueVector.INITIAL_VALUE_ALLOCATION){
        writer.setPosition(recordCount);
        write = jsonReader.write(writer);

        if(write == ReadState.WRITE_SUCCEED){
//          logger.debug("Wrote record.");
          recordCount++;
        }else{
//          logger.debug("Exiting.");
          break outside;
        }

      }

      jsonReader.ensureAtLeastOneField(writer);

      writer.setValueCount(recordCount);
//      p.stop();
//      System.out.println(String.format("Wrote %d records in %dms.", recordCount, p.elapsed(TimeUnit.MILLISECONDS)));

      updateRunningCount();

      return recordCount;

    } catch (final Exception e) {
      handleAndRaise("Error parsing JSON", e);
    }
    // this is never reached
    return 0;
  }

  private void updateRunningCount() {
    runningRecordCount += recordCount;
  }

  @Override
  public void cleanup() {
    try {
      if(stream != null){
        stream.close();
      }
    } catch (final IOException e) {
      logger.warn("Failure while closing stream.", e);
    }
  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/store/easy/text/compliant/TextReader.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.store.easy.text.compliant;

import io.netty.buffer.DrillBuf;

import java.io.IOException;

import org.apache.drill.common.exceptions.UserException;

import com.univocity.parsers.common.TextParsingException;
import com.univocity.parsers.csv.CsvParserSettings;

/*******************************************************************************
 * Portions Copyright 2014 uniVocity Software Pty Ltd
 ******************************************************************************/

/**
 * A byte-based Text parser implementation. Builds heavily upon the uniVocity parsers. Customized for UTF8 parsing and
 * DrillBuf support.
 */
final class TextReader {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(TextReader.class);

  private static final byte NULL_BYTE = (byte) '\0';

  private final TextParsingContext context;

  private final long recordsToRead;
  private final TextParsingSettings settings;

  private final TextInput input;
  private final TextOutput output;
  private final DrillBuf workBuf;

  private byte ch;

  // index of the field within this record
  private int fieldIndex;

  /** Behavior settings **/
  private final boolean ignoreTrailingWhitespace;
  private final boolean ignoreLeadingWhitespace;
  private final boolean parseUnescapedQuotes;

  /** Key Characters **/
  private final byte comment;
  private final byte delimiter;
  private final byte quote;
  private final byte quoteEscape;
  private final byte newLine;

  /**
   * The CsvParser supports all settings provided by {@link CsvParserSettings}, and requires this configuration to be
   * properly initialized.
   * @param settings  the parser configuration
   * @param input  input stream
   * @param output  interface to produce output record batch
   * @param workBuf  working buffer to handle whitespaces
   */
  public TextReader(TextParsingSettings settings, TextInput input, TextOutput output, DrillBuf workBuf) {
    this.context = new TextParsingContext(input, output);
    this.workBuf = workBuf;
    this.settings = settings;

    this.recordsToRead = settings.getNumberOfRecordsToRead() == -1 ? Long.MAX_VALUE : settings.getNumberOfRecordsToRead();

    this.ignoreTrailingWhitespace = settings.isIgnoreTrailingWhitespaces();
    this.ignoreLeadingWhitespace = settings.isIgnoreLeadingWhitespaces();
    this.parseUnescapedQuotes = settings.isParseUnescapedQuotes();
    this.delimiter = settings.getDelimiter();
    this.quote = settings.getQuote();
    this.quoteEscape = settings.getQuoteEscape();
    this.newLine = settings.getNormalizedNewLine();
    this.comment = settings.getComment();

    this.input = input;
    this.output = output;

  }

  public TextOutput getOutput(){
    return output;
  }

  /* Check if the given byte is a white space. As per the univocity text reader
   * any ASCII <= ' ' is considered a white space. However since byte in JAVA is signed
   * we have an additional check to make sure its not negative
   */
  static final boolean isWhite(byte b){
    return b <= ' ' && b > -1;
  }

  // Inform the output interface to indicate we are starting a new record batch
  public void resetForNextBatch(){
    output.startBatch();
  }

  public long getPos(){
    return input.getPos();
  }

  /**
   * Function encapsulates parsing an entire record, delegates parsing of the
   * fields to parseField() function.
   * We mark the start of the record and if there are any failures encountered (OOM for eg)
   * then we reset the input stream to the marked position
   * @return  true if parsing this record was successful; false otherwise
   * @throws IOException
   */
  private boolean parseRecord() throws IOException {
    final byte newLine = this.newLine;
    final TextInput input = this.input;

    input.mark();

    fieldIndex = 0;
    if (isWhite(ch) && ignoreLeadingWhitespace) {
      skipWhitespace();
    }

    int fieldsWritten = 0;
    try{
      boolean earlyTerm = false;
      while (ch != newLine) {
        earlyTerm = !parseField();
        fieldsWritten++;
        if (ch != newLine) {
          ch = input.nextChar();
          if (ch == newLine) {
            output.endEmptyField();
            break;
          }
        }
        if(earlyTerm){
          if(ch != newLine){
            input.skipLines(1);
          }
          break;
        }
      }
    }catch(StreamFinishedPseudoException e){
      // if we've written part of a field or all of a field, we should send this row.
      if(fieldsWritten == 0 && !output.rowHasData()){
        throw e;
      }
    }

    output.finishRecord();
    return true;
  }

  /**
   * Function parses an individual field and ignores any white spaces encountered
   * by not appending it to the output vector
   * @throws IOException
   */
  private void parseValueIgnore() throws IOException {
    final byte newLine = this.newLine;
    final byte delimiter = this.delimiter;
    final TextOutput output = this.output;
    final TextInput input = this.input;

    byte ch = this.ch;
    while (ch != delimiter && ch != newLine) {
      output.appendIgnoringWhitespace(ch);
//      fieldSize++;
      ch = input.nextChar();
    }
    this.ch = ch;
  }

  /**
   * Function parses an individual field and appends all characters till the delimeter (or newline)
   * to the output, including white spaces
   * @throws IOException
   */
  private void parseValueAll() throws IOException {
    final byte newLine = this.newLine;
    final byte delimiter = this.delimiter;
    final TextOutput output = this.output;
    final TextInput input = this.input;

    byte ch = this.ch;
    while (ch != delimiter && ch != newLine) {
      output.append(ch);
      ch = input.nextChar();
    }
    this.ch = ch;
  }

  /**
   * Function simply delegates the parsing of a single field to the actual implementation based on parsing config
   * @throws IOException
   */
  private void parseValue() throws IOException {
    if (ignoreTrailingWhitespace) {
      parseValueIgnore();
    }else{
      parseValueAll();
    }
  }

  /**
   * Recursive function invoked when a quote is encountered. Function also
   * handles the case when there are non-white space characters in the field
   * after the quoted value.
   * @param prev  previous byte read
   * @throws IOException
   */
  private void parseQuotedValue(byte prev) throws IOException {
    final byte newLine = this.newLine;
    final byte delimiter = this.delimiter;
    final TextOutput output = this.output;
    final TextInput input = this.input;
    final byte quote = this.quote;

    ch = input.nextChar();

    while (!(prev == quote && (ch == delimiter || ch == newLine || isWhite(ch)))) {
      if (ch != quote) {
        if (prev == quote) { // unescaped quote detected
          if (parseUnescapedQuotes) {
            output.append(quote);
            output.append(ch);
            parseQuotedValue(ch);
            break;
          } else {
            throw new TextParsingException(
                context,
                "Unescaped quote character '"
                    + quote
                    + "' inside quoted value of CSV field. To allow unescaped quotes, set 'parseUnescapedQuotes' to 'true' in the CSV parser settings. Cannot parse CSV input.");
          }
        }
        output.append(ch);
        prev = ch;
      } else if (prev == quoteEscape) {
        output.append(quote);
        prev = NULL_BYTE;
      } else {
        prev = ch;
      }
      ch = input.nextChar();
    }

    // handles whitespaces after quoted value: whitespaces are ignored. Content after whitespaces may be parsed if
    // 'parseUnescapedQuotes' is enabled.
    if (ch != newLine && ch <= ' ') {
      final DrillBuf workBuf = this.workBuf;
      workBuf.resetWriterIndex();
      do {
        // saves whitespaces after value
        workBuf.writeByte(ch);
        ch = input.nextChar();
        // found a new line, go to next record.
        if (ch == newLine) {
          return;
        }
      } while (ch <= ' ');

      // there's more stuff after the quoted value, not only empty spaces.
      if (!(ch == delimiter || ch == newLine) && parseUnescapedQuotes) {

        output.append(quote);
        for(int i =0; i < workBuf.writerIndex(); i++){
          output.append(workBuf.getByte(i));
        }
        // the next character is not the escape character, put it there
        if (ch != quoteEscape) {
          output.append(ch);
        }
        // sets this character as the previous character (may be escaping)
        // calls recursively to keep parsing potentially quoted content
        parseQuotedValue(ch);
      }
    }

    if (!(ch == delimiter || ch == newLine)) {
      throw new TextParsingException(context, "Unexpected character '" + ch
          + "' following quoted value of CSV field. Expecting '" + delimiter + "'. Cannot parse CSV input.");
    }
  }

  /**
   * Captures the entirety of parsing a single field and based on the input delegates to the appropriate function
   * @return
   * @throws IOException
   */
  private final boolean parseField() throws IOException {

    output.startField(fieldIndex++);

    if (isWhite(ch) && ignoreLeadingWhitespace) {
      skipWhitespace();
    }

    if (ch == delimiter) {
      return output.endEmptyField();
    } else {
      if (ch == quote) {
        parseQuotedValue(NULL_BYTE);
      } else {
        parseValue();
      }

      return output.endField();
    }

  }

  /**
   * Helper function to skip white spaces occurring at the current input stream.
   * @throws IOException
   */
  private void skipWhitespace() throws IOException {
    final byte delimiter = this.delimiter;
    final byte newLine = this.newLine;
    final TextInput input = this.input;

    while (isWhite(ch) && ch != delimiter && ch != newLine) {
      ch = input.nextChar();
    }
  }

  /**
   * Starting point for the reader. Sets up the input interface.
   * @throws IOException
   */
  public final void start() throws IOException {
    context.stopped = false;
    input.start();
  }


  /**
   * Parses the next record from the input. Will skip the line if its a comment,
   * this is required when the file contains headers
   * @throws IOException
   */
  public final boolean parseNext() throws IOException {
    try {
      while (!context.stopped) {
        ch = input.nextChar();
        if (ch == comment) {
          input.skipLines(1);
          continue;
        }
        break;
      }
      final long initialLineNumber = input.lineCount();
      boolean success = parseRecord();
      if (initialLineNumber + 1 < input.lineCount()) {
        throw new TextParsingException(context, "Cannot use newline character within quoted string");
      }

      if(success){
        if (recordsToRead > 0 && context.currentRecord() >= recordsToRead) {
          context.stop();
        }
        return true;
      }else{
        return false;
      }

    } catch (StreamFinishedPseudoException ex) {
      stopParsing();
      return false;
    } catch (Exception ex) {
      try {
        throw handleException(ex);
      } finally {
        stopParsing();
      }
    }
  }

  private void stopParsing(){

  }

  private String displayLineSeparators(String str, boolean addNewLine) {
    if (addNewLine) {
      if (str.contains("\r\n")) {
        str = str.replaceAll("\\r\\n", "[\\\\r\\\\n]\r\n\t");
      } else if (str.contains("\n")) {
        str = str.replaceAll("\\n", "[\\\\n]\n\t");
      } else {
        str = str.replaceAll("\\r", "[\\\\r]\r\t");
      }
    } else {
      str = str.replaceAll("\\n", "\\\\n");
      str = str.replaceAll("\\r", "\\\\r");
    }
    return str;
  }

  /**
   * Helper method to handle exceptions caught while processing text files and generate better error messages associated with
   * the exception.
   * @param ex  Exception raised
   * @return
   * @throws IOException
   */
  private TextParsingException handleException(Exception ex) throws IOException {

    if (ex instanceof TextParsingException) {
      throw (TextParsingException) ex;
    }

    if (ex instanceof ArrayIndexOutOfBoundsException) {
      ex = UserException
          .dataReadError(ex)
          .message(
              "Drill failed to read your text file.  Drill supports up to %d columns in a text file.  Your file appears to have more than that.",
              RepeatedVarCharOutput.MAXIMUM_NUMBER_COLUMNS)
          .build();
    }

    String message = null;
    String tmp = input.getStringSinceMarkForError();
    char[] chars = tmp.toCharArray();
    if (chars != null) {
      int length = chars.length;
      if (length > settings.getMaxCharsPerColumn()) {
        message = "Length of parsed input (" + length
            + ") exceeds the maximum number of characters defined in your parser settings ("
            + settings.getMaxCharsPerColumn() + "). ";
      }

      if (tmp.contains("\n") || tmp.contains("\r")) {
        tmp = displayLineSeparators(tmp, true);
        String lineSeparator = displayLineSeparators(settings.getLineSeparatorString(), false);
        message += "\nIdentified line separator characters in the parsed content. This may be the cause of the error. The line separator in your parser settings is set to '"
            + lineSeparator + "'. Parsed content:\n\t" + tmp;
      }

      int nullCharacterCount = 0;
      // ensuring the StringBuilder won't grow over Integer.MAX_VALUE to avoid OutOfMemoryError
      int maxLength = length > Integer.MAX_VALUE / 2 ? Integer.MAX_VALUE / 2 - 1 : length;
      StringBuilder s = new StringBuilder(maxLength);
      for (int i = 0; i < maxLength; i++) {
        if (chars[i] == '\0') {
          s.append('\\');
          s.append('0');
          nullCharacterCount++;
        } else {
          s.append(chars[i]);
        }
      }
      tmp = s.toString();

      if (nullCharacterCount > 0) {
        message += "\nIdentified "
            + nullCharacterCount
            + " null characters ('\0') on parsed content. This may indicate the data is corrupt or its encoding is invalid. Parsed content:\n\t"
            + tmp;
      }

    }

    throw new TextParsingException(context, message, ex);
  }

  /**
   * Finish the processing of a batch, indicates to the output
   * interface to wrap up the batch
   */
  public void finishBatch(){
    output.finishBatch();
//    System.out.println(String.format("line %d, cnt %d", input.getLineCount(), output.getRecordCount()));
  }

  /**
   * Invoked once there are no more records and we are done with the
   * current record reader to clean up state.
   * @throws IOException
   */
  public void close() throws IOException{
    input.close();
  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/store/parquet/ParquetReaderUtility.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.store.parquet;

import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.planner.physical.PlannerSettings;
import org.apache.drill.exec.server.options.OptionManager;
import org.apache.drill.exec.work.ExecErrorConstants;

/*
 * Utility class where we can capture common logic between the two parquet readers
 */
public class ParquetReaderUtility {
  public static void checkDecimalTypeEnabled(OptionManager options) {
    if (options.getOption(PlannerSettings.ENABLE_DECIMAL_DATA_TYPE_KEY).bool_val == false) {
      throw UserException
          .unsupportedError()
          .message(ExecErrorConstants.DECIMAL_DISABLE_ERR_MSG)
          .build();
    }
  }

  public static int getIntFromLEBytes(byte[] input, int start) {
    int out = 0;
    int shiftOrder = 0;
    for (int i = start; i < start + 4; i++) {
      out |= (((input[i]) & 0xFF) << shiftOrder);
      shiftOrder += 8;
    }
    return out;
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/vector/complex/fn/JsonReader.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.vector.complex.fn;

import io.netty.buffer.DrillBuf;

import java.io.IOException;
import java.io.InputStream;
import java.util.List;

import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.common.expression.PathSegment;
import org.apache.drill.common.expression.SchemaPath;
import org.apache.drill.exec.physical.base.GroupScan;
import org.apache.drill.exec.store.easy.json.JsonProcessor;
import org.apache.drill.exec.store.easy.json.reader.BaseJsonProcessor;
import org.apache.drill.exec.vector.complex.fn.VectorOutput.ListVectorOutput;
import org.apache.drill.exec.vector.complex.fn.VectorOutput.MapVectorOutput;
import org.apache.drill.exec.vector.complex.writer.BaseWriter;
import org.apache.drill.exec.vector.complex.writer.BaseWriter.ComplexWriter;
import org.apache.drill.exec.vector.complex.writer.BaseWriter.ListWriter;
import org.apache.drill.exec.vector.complex.writer.BaseWriter.MapWriter;

import com.fasterxml.jackson.core.JsonParseException;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.JsonToken;
import com.fasterxml.jackson.databind.JsonNode;
import com.google.common.base.Charsets;
import com.google.common.base.Preconditions;

public class JsonReader extends BaseJsonProcessor {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(JsonReader.class);
  public final static int MAX_RECORD_SIZE = 128 * 1024;

  private final WorkingBuffer workingBuffer;
  private final List<SchemaPath> columns;
  private final boolean allTextMode;
  private boolean atLeastOneWrite = false;
  private final MapVectorOutput mapOutput;
  private final ListVectorOutput listOutput;
  private final boolean extended = true;
  private final boolean readNumbersAsDouble;

  /**
   * Describes whether or not this reader can unwrap a single root array record and treat it like a set of distinct records.
   */
  private final boolean skipOuterList;

  /**
   * Whether the reader is currently in a situation where we are unwrapping an outer list.
   */
  private boolean inOuterList;
  /**
   * The name of the current field being parsed. For Error messages.
   */
  private String currentFieldName;

  private FieldSelection selection;

  public JsonReader(DrillBuf managedBuf, boolean allTextMode, boolean skipOuterList, boolean readNumbersAsDouble) {
    this(managedBuf, GroupScan.ALL_COLUMNS, allTextMode, skipOuterList, readNumbersAsDouble);
  }

  public JsonReader(DrillBuf managedBuf, List<SchemaPath> columns, boolean allTextMode, boolean skipOuterList, boolean readNumbersAsDouble) {
    super(managedBuf);
    assert Preconditions.checkNotNull(columns).size() > 0 : "json record reader requires at least a column";
    this.selection = FieldSelection.getFieldSelection(columns);
    this.workingBuffer = new WorkingBuffer(managedBuf);
    this.skipOuterList = skipOuterList;
    this.allTextMode = allTextMode;
    this.columns = columns;
    this.mapOutput = new MapVectorOutput(workingBuffer);
    this.listOutput = new ListVectorOutput(workingBuffer);
    this.currentFieldName="<none>";
    this.readNumbersAsDouble = readNumbersAsDouble;
  }

  @Override
  public void ensureAtLeastOneField(ComplexWriter writer) {
    if (!atLeastOneWrite) {
      // if we had no columns, create one empty one so we can return some data for count purposes.
      SchemaPath sp = columns.get(0);
      PathSegment root = sp.getRootSegment();
      BaseWriter.MapWriter fieldWriter = writer.rootAsMap();
      while (root.getChild() != null && !root.getChild().isArray()) {
        fieldWriter = fieldWriter.map(root.getNameSegment().getPath());
        root = root.getChild();
      }
      fieldWriter.integer(root.getNameSegment().getPath());
    }
  }

  public void setSource(int start, int end, DrillBuf buf) throws IOException {
    setSource(DrillBufInputStream.getStream(start, end, buf));
  }


  @Override
  public void setSource(InputStream is) throws IOException {
    super.setSource(is);
    mapOutput.setParser(parser);
    listOutput.setParser(parser);
  }

  @Override
  public void setSource(JsonNode node) {
    super.setSource(node);
    mapOutput.setParser(parser);
    listOutput.setParser(parser);
  }

  public void setSource(String data) throws IOException {
    setSource(data.getBytes(Charsets.UTF_8));
  }

  public void setSource(byte[] bytes) throws IOException {
    setSource(new SeekableBAIS(bytes));
  }

  @Override
  public ReadState write(ComplexWriter writer) throws IOException {
    JsonToken t = parser.nextToken();

    while (!parser.hasCurrentToken() && !parser.isClosed()) {
      t = parser.nextToken();
    }

    if (parser.isClosed()) {
      return ReadState.END_OF_STREAM;
    }

    ReadState readState = writeToVector(writer, t);

    switch (readState) {
    case END_OF_STREAM:
      break;
    case WRITE_SUCCEED:
      break;
    default:
      throw
        getExceptionWithContext(
          UserException.dataReadError(), currentFieldName, null)
          .message("Failure while reading JSON. (Got an invalid read state %s )", readState.toString())
          .build();
    }

    return readState;
  }

  private void confirmLast() throws IOException{
    parser.nextToken();
    if(!parser.isClosed()){
      throw
        getExceptionWithContext(
          UserException.dataReadError(), currentFieldName, null)
        .message("Drill attempted to unwrap a toplevel list "
          + "in your document.  However, it appears that there is trailing content after this top level list.  Drill only "
          + "supports querying a set of distinct maps or a single json array with multiple inner maps.")
        .build();
    }
  }

  private ReadState writeToVector(ComplexWriter writer, JsonToken t) throws IOException {
    switch (t) {
    case START_OBJECT:
      writeDataSwitch(writer.rootAsMap());
      break;
    case START_ARRAY:
      if(inOuterList){
        throw
          getExceptionWithContext(
            UserException.dataReadError(), currentFieldName, null)
          .message("The top level of your document must either be a single array of maps or a set "
            + "of white space delimited maps.")
          .build();
      }

      if(skipOuterList){
        t = parser.nextToken();
        if(t == JsonToken.START_OBJECT){
          inOuterList = true;
          writeDataSwitch(writer.rootAsMap());
        }else{
          throw
            getExceptionWithContext(
              UserException.dataReadError(), currentFieldName, null)
            .message("The top level of your document must either be a single array of maps or a set "
              + "of white space delimited maps.")
            .build();
        }

      }else{
        writeDataSwitch(writer.rootAsList());
      }
      break;
    case END_ARRAY:

      if(inOuterList){
        confirmLast();
        return ReadState.END_OF_STREAM;
      }else{
        throw
          getExceptionWithContext(
            UserException.dataReadError(), currentFieldName, null)
          .message("Failure while parsing JSON.  Ran across unexpected %s.", JsonToken.END_ARRAY)
          .build();
      }

    case NOT_AVAILABLE:
      return ReadState.END_OF_STREAM;
    default:
      throw
        getExceptionWithContext(
          UserException.dataReadError(), currentFieldName, null)
          .message("Failure while parsing JSON.  Found token of [%s].  Drill currently only supports parsing "
              + "json strings that contain either lists or maps.  The root object cannot be a scalar.", t)
          .build();
    }

    return ReadState.WRITE_SUCCEED;

  }

  private void writeDataSwitch(MapWriter w) throws IOException {
    if (this.allTextMode) {
      writeDataAllText(w, this.selection, true);
    } else {
      writeData(w, this.selection, true);
    }
  }

  private void writeDataSwitch(ListWriter w) throws IOException {
    if (this.allTextMode) {
      writeDataAllText(w);
    } else {
      writeData(w);
    }
  }

  private void consumeEntireNextValue() throws IOException {
    switch (parser.nextToken()) {
    case START_ARRAY:
    case START_OBJECT:
      parser.skipChildren();
      return;
    default:
      // hit a single value, do nothing as the token was already read
      // in the switch statement
      return;
    }
  }

  /**
   *
   * @param map
   * @param selection
   * @param moveForward
   *          Whether or not we should start with using the current token or the next token. If moveForward = true, we
   *          should start with the next token and ignore the current one.
   * @throws IOException
   */
  private void writeData(MapWriter map, FieldSelection selection, boolean moveForward) throws IOException {
    //
    map.start();
    outside: while (true) {

      JsonToken t;
      if(moveForward){
        t = parser.nextToken();
      }else{
        t = parser.getCurrentToken();
        moveForward = true;
      }

      if (t == JsonToken.NOT_AVAILABLE || t == JsonToken.END_OBJECT) {
        return;
      }

      assert t == JsonToken.FIELD_NAME : String.format("Expected FIELD_NAME but got %s.", t.name());

      final String fieldName = parser.getText();
      this.currentFieldName = fieldName;
      FieldSelection childSelection = selection.getChild(fieldName);
      if (childSelection.isNeverValid()) {
        consumeEntireNextValue();
        continue outside;
      }

      switch (parser.nextToken()) {
      case START_ARRAY:
        writeData(map.list(fieldName));
        break;
      case START_OBJECT:
        if (!writeMapDataIfTyped(map, fieldName)) {
          writeData(map.map(fieldName), childSelection, false);
        }
        break;
      case END_OBJECT:
        break outside;

      case VALUE_FALSE: {
        map.bit(fieldName).writeBit(0);
        atLeastOneWrite = true;
        break;
      }
      case VALUE_TRUE: {
        map.bit(fieldName).writeBit(1);
        atLeastOneWrite = true;
        break;
      }
      case VALUE_NULL:
        // do nothing as we don't have a type.
        break;
      case VALUE_NUMBER_FLOAT:
        map.float8(fieldName).writeFloat8(parser.getDoubleValue());
        atLeastOneWrite = true;
        break;
      case VALUE_NUMBER_INT:
        if (this.readNumbersAsDouble) {
          map.float8(fieldName).writeFloat8(parser.getDoubleValue());
        }
        else {
          map.bigInt(fieldName).writeBigInt(parser.getLongValue());
        }
        atLeastOneWrite = true;
        break;
      case VALUE_STRING:
        handleString(parser, map, fieldName);
        atLeastOneWrite = true;
        break;

      default:
        throw
          getExceptionWithContext(
            UserException.dataReadError(), currentFieldName, null)
          .message("Unexpected token %s", parser.getCurrentToken())
          .build();
      }

    }
    map.end();

  }

  private void writeDataAllText(MapWriter map, FieldSelection selection, boolean moveForward) throws IOException {
    //
    map.start();
    outside: while (true) {


      JsonToken t;

      if(moveForward){
        t = parser.nextToken();
      }else{
        t = parser.getCurrentToken();
        moveForward = true;
      }

      if (t == JsonToken.NOT_AVAILABLE || t == JsonToken.END_OBJECT) {
        return;
      }

      assert t == JsonToken.FIELD_NAME : String.format("Expected FIELD_NAME but got %s.", t.name());

      final String fieldName = parser.getText();
      this.currentFieldName = fieldName;
      FieldSelection childSelection = selection.getChild(fieldName);
      if (childSelection.isNeverValid()) {
        consumeEntireNextValue();
        continue outside;
      }

      switch (parser.nextToken()) {
      case START_ARRAY:
        writeDataAllText(map.list(fieldName));
        break;
      case START_OBJECT:
        if (!writeMapDataIfTyped(map, fieldName)) {
          writeDataAllText(map.map(fieldName), childSelection, false);
        }
        break;
      case END_OBJECT:
        break outside;

      case VALUE_EMBEDDED_OBJECT:
      case VALUE_FALSE:
      case VALUE_TRUE:
      case VALUE_NUMBER_FLOAT:
      case VALUE_NUMBER_INT:
      case VALUE_STRING:
        handleString(parser, map, fieldName);
        atLeastOneWrite = true;
        break;
      case VALUE_NULL:
        // do nothing as we don't have a type.
        break;

      default:
        throw
          getExceptionWithContext(
            UserException.dataReadError(), currentFieldName, null)
          .message("Unexpected token %s", parser.getCurrentToken())
          .build();
      }
    }
    map.end();

  }

  /**
   * Will attempt to take the current value and consume it as an extended value (if extended mode is enabled).  Whether extended is enable or disabled, will consume the next token in the stream.
   * @param writer
   * @param fieldName
   * @return
   * @throws IOException
   */
  private boolean writeMapDataIfTyped(MapWriter writer, String fieldName) throws IOException {
    if (extended) {
      atLeastOneWrite = true;
      return mapOutput.run(writer, fieldName);
    } else {
      parser.nextToken();
      return false;
    }
  }

  /**
   * Will attempt to take the current value and consume it as an extended value (if extended mode is enabled).  Whether extended is enable or disabled, will consume the next token in the stream.
   * @param writer
   * @return
   * @throws IOException
   */
  private boolean writeListDataIfTyped(ListWriter writer) throws IOException {
    if (extended) {
      atLeastOneWrite = true;
      return listOutput.run(writer);
    } else {
      parser.nextToken();
      return false;
    }
  }

  private void handleString(JsonParser parser, MapWriter writer, String fieldName) throws IOException {
    writer.varChar(fieldName).writeVarChar(0, workingBuffer.prepareVarCharHolder(parser.getText()),
        workingBuffer.getBuf());
  }

  private void handleString(JsonParser parser, ListWriter writer) throws IOException {
    writer.varChar().writeVarChar(0, workingBuffer.prepareVarCharHolder(parser.getText()), workingBuffer.getBuf());
  }

  private void writeData(ListWriter list) throws IOException {
    list.start();
    outside: while (true) {
      try {
      switch (parser.nextToken()) {
      case START_ARRAY:
        writeData(list.list());
        break;
      case START_OBJECT:
        if (!writeListDataIfTyped(list)) {
          writeData(list.map(), FieldSelection.ALL_VALID, false);
        }
        break;
      case END_ARRAY:
      case END_OBJECT:
        break outside;

      case VALUE_EMBEDDED_OBJECT:
      case VALUE_FALSE: {
        list.bit().writeBit(0);
        atLeastOneWrite = true;
        break;
      }
      case VALUE_TRUE: {
        list.bit().writeBit(1);
        atLeastOneWrite = true;
        break;
      }
      case VALUE_NULL:
        throw UserException.unsupportedError()
          .message("Null values are not supported in lists by default. " +
            "Please set `store.json.all_text_mode` to true to read lists containing nulls. " +
            "Be advised that this will treat JSON null values as a string containing the word 'null'.")
          .build();
      case VALUE_NUMBER_FLOAT:
        list.float8().writeFloat8(parser.getDoubleValue());
        atLeastOneWrite = true;
        break;
      case VALUE_NUMBER_INT:
        if (this.readNumbersAsDouble) {
          list.float8().writeFloat8(parser.getDoubleValue());
        }
        else {
          list.bigInt().writeBigInt(parser.getLongValue());
        }
        atLeastOneWrite = true;
        break;
      case VALUE_STRING:
        handleString(parser, list);
        atLeastOneWrite = true;
        break;
      default:
        throw UserException.dataReadError()
          .message("Unexpected token %s", parser.getCurrentToken())
          .build();
    }
    } catch (Exception e) {
      throw getExceptionWithContext(e, this.currentFieldName, null).build();
    }
    }
    list.end();

  }

  private void writeDataAllText(ListWriter list) throws IOException {
    list.start();
    outside: while (true) {

      switch (parser.nextToken()) {
      case START_ARRAY:
        writeDataAllText(list.list());
        break;
      case START_OBJECT:
        if (!writeListDataIfTyped(list)) {
          writeDataAllText(list.map(), FieldSelection.ALL_VALID, false);
        }
        break;
      case END_ARRAY:
      case END_OBJECT:
        break outside;

      case VALUE_EMBEDDED_OBJECT:
      case VALUE_FALSE:
      case VALUE_TRUE:
      case VALUE_NULL:
      case VALUE_NUMBER_FLOAT:
      case VALUE_NUMBER_INT:
      case VALUE_STRING:
        handleString(parser, list);
        atLeastOneWrite = true;
        break;
      default:
        throw
          getExceptionWithContext(
            UserException.dataReadError(), currentFieldName, null)
          .message("Unexpected token %s", parser.getCurrentToken())
          .build();
      }
    }
    list.end();

  }

  public DrillBuf getWorkBuf() {
    return workingBuffer.getBuf();
  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/work/foreman/Foreman.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.work.foreman;

import io.netty.buffer.ByteBuf;
import io.netty.channel.ChannelFuture;
import io.netty.util.concurrent.Future;
import io.netty.util.concurrent.GenericFutureListener;

import java.io.IOException;
import java.util.Collection;
import java.util.Date;
import java.util.LinkedList;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import org.apache.drill.common.EventProcessor;
import org.apache.drill.common.concurrent.ExtendedLatch;
import org.apache.drill.common.config.DrillConfig;
import org.apache.drill.common.exceptions.ExecutionSetupException;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.common.logical.LogicalPlan;
import org.apache.drill.common.logical.PlanProperties.Generator.ResultMode;
import org.apache.drill.exec.ExecConstants;
import org.apache.drill.exec.coord.ClusterCoordinator;
import org.apache.drill.exec.coord.DistributedSemaphore;
import org.apache.drill.exec.coord.DistributedSemaphore.DistributedLease;
import org.apache.drill.exec.exception.OptimizerException;
import org.apache.drill.exec.memory.OutOfMemoryException;
import org.apache.drill.exec.memory.OutOfMemoryRuntimeException;
import org.apache.drill.exec.ops.FragmentContext;
import org.apache.drill.exec.ops.QueryContext;
import org.apache.drill.exec.opt.BasicOptimizer;
import org.apache.drill.exec.physical.PhysicalPlan;
import org.apache.drill.exec.physical.base.FragmentRoot;
import org.apache.drill.exec.physical.base.PhysicalOperator;
import org.apache.drill.exec.physical.config.ExternalSort;
import org.apache.drill.exec.planner.fragment.Fragment;
import org.apache.drill.exec.planner.fragment.MakeFragmentsVisitor;
import org.apache.drill.exec.planner.fragment.SimpleParallelizer;
import org.apache.drill.exec.planner.sql.DirectPlan;
import org.apache.drill.exec.planner.sql.DrillSqlWorker;
import org.apache.drill.exec.proto.BitControl.InitializeFragments;
import org.apache.drill.exec.proto.BitControl.PlanFragment;
import org.apache.drill.exec.proto.CoordinationProtos.DrillbitEndpoint;
import org.apache.drill.exec.proto.ExecProtos.FragmentHandle;
import org.apache.drill.exec.proto.GeneralRPCProtos.Ack;
import org.apache.drill.exec.proto.UserBitShared.QueryId;
import org.apache.drill.exec.proto.UserBitShared.QueryResult;
import org.apache.drill.exec.proto.UserBitShared.QueryResult.QueryState;
import org.apache.drill.exec.proto.UserProtos.RunQuery;
import org.apache.drill.exec.proto.helper.QueryIdHelper;
import org.apache.drill.exec.rpc.BaseRpcOutcomeListener;
import org.apache.drill.exec.rpc.RpcException;
import org.apache.drill.exec.rpc.control.Controller;
import org.apache.drill.exec.rpc.user.UserServer.UserClientConnection;
import org.apache.drill.exec.server.DrillbitContext;
import org.apache.drill.exec.server.options.OptionManager;
import org.apache.drill.exec.testing.ControlsInjector;
import org.apache.drill.exec.testing.ControlsInjectorFactory;
import org.apache.drill.exec.util.Pointer;
import org.apache.drill.exec.work.EndpointListener;
import org.apache.drill.exec.work.QueryWorkUnit;
import org.apache.drill.exec.work.WorkManager.WorkerBee;
import org.apache.drill.exec.work.batch.IncomingBuffers;
import org.apache.drill.exec.work.fragment.FragmentExecutor;
import org.apache.drill.exec.work.fragment.RootFragmentManager;
import org.codehaus.jackson.map.ObjectMapper;

import com.google.common.base.Preconditions;
import com.google.common.collect.ArrayListMultimap;
import com.google.common.collect.Multimap;
import com.google.common.collect.Sets;

/**
 * Foreman manages all the fragments (local and remote) for a single query where this
 * is the driving/root node.
 *
 * The flow is as follows:
 * - Foreman is submitted as a runnable.
 * - Runnable does query planning.
 * - state changes from PENDING to RUNNING
 * - Runnable sends out starting fragments
 * - Status listener are activated
 * - The Runnable's run() completes, but the Foreman stays around
 * - Foreman listens for state change messages.
 * - state change messages can drive the state to FAILED or CANCELED, in which case
 *   messages are sent to running fragments to terminate
 * - when all fragments complete, state change messages drive the state to COMPLETED
 */
public class Foreman implements Runnable {
  private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(Foreman.class);
  private static final org.slf4j.Logger queryLogger = org.slf4j.LoggerFactory.getLogger("query.logger");
  private static final ControlsInjector injector = ControlsInjectorFactory.getInjector(Foreman.class);

  private static final ObjectMapper MAPPER = new ObjectMapper();
  private static final long RPC_WAIT_IN_MSECS_PER_FRAGMENT = 5000;

  private final QueryId queryId;
  private final RunQuery queryRequest;
  private final QueryContext queryContext;
  private final QueryManager queryManager; // handles lower-level details of query execution
  private final WorkerBee bee; // provides an interface to submit tasks
  private final DrillbitContext drillbitContext;
  private final UserClientConnection initiatingClient; // used to send responses
  private volatile QueryState state;
  private boolean resume = false;

  private volatile DistributedLease lease; // used to limit the number of concurrent queries

  private FragmentExecutor rootRunner; // root Fragment

  private final ExtendedLatch acceptExternalEvents = new ExtendedLatch(); // gates acceptance of external events
  private final StateListener stateListener = new StateListener(); // source of external events
  private final ResponseSendListener responseListener = new ResponseSendListener();
  private final StateSwitch stateSwitch = new StateSwitch();
  private final ForemanResult foremanResult = new ForemanResult();
  private final ConnectionClosedListener closeListener = new ConnectionClosedListener();
  private final ChannelFuture closeFuture;

  private String queryText;

  /**
   * Constructor. Sets up the Foreman, but does not initiate any execution.
   *
   * @param bee used to submit additional work
   * @param drillbitContext
   * @param connection
   * @param queryId the id for the query
   * @param queryRequest the query to execute
   */
  public Foreman(final WorkerBee bee, final DrillbitContext drillbitContext,
      final UserClientConnection connection, final QueryId queryId, final RunQuery queryRequest) {
    this.bee = bee;
    this.queryId = queryId;
    this.queryRequest = queryRequest;
    this.drillbitContext = drillbitContext;

    initiatingClient = connection;
    this.closeFuture = initiatingClient.getChannel().closeFuture();
    closeFuture.addListener(closeListener);

    queryContext = new QueryContext(connection.getSession(), drillbitContext);
    queryManager = new QueryManager(queryId, queryRequest, drillbitContext.getPersistentStoreProvider(),
        stateListener, this); // TODO reference escapes before ctor is complete via stateListener, this

    recordNewState(QueryState.PENDING);
  }

  private class ConnectionClosedListener implements GenericFutureListener<Future<Void>> {
    @Override
    public void operationComplete(Future<Void> future) throws Exception {
      cancel();
    }
  }

  /**
   * Get the QueryContext created for the query.
   *
   * @return the QueryContext
   */
  public QueryContext getQueryContext() {
    return queryContext;
  }

  /**
   * Get the QueryManager created for the query.
   *
   * @return the QueryManager
   */
  public QueryManager getQueryManager() {
    return queryManager;
  }

  /**
   * Cancel the query. Asynchronous -- it may take some time for all remote fragments to be
   * terminated.
   */
  public void cancel() {
    // Note this can be called from outside of run() on another thread, or after run() completes
    stateListener.moveToState(QueryState.CANCELLATION_REQUESTED, null);
  }

  /**
   * Resume the query. Regardless of the current state, this method sends a resume signal to all fragments.
   * This method can be called multiple times.
   */
  public void resume() {
    resume = true;
    // resume all pauses through query context
    queryContext.getExecutionControls().unpauseAll();
    // resume all pauses through all fragment contexts
    queryManager.unpauseExecutingFragments(drillbitContext);
  }

  /**
   * Called by execution pool to do query setup, and kick off remote execution.
   *
   * <p>Note that completion of this function is not the end of the Foreman's role
   * in the query's lifecycle.
   */
  @Override
  public void run() {
    // rename the thread we're using for debugging purposes
    final Thread currentThread = Thread.currentThread();
    final String originalName = currentThread.getName();
    currentThread.setName(QueryIdHelper.getQueryId(queryId) + ":foreman");

    // track how long the query takes
    queryManager.markStartTime();

    try {
      injector.injectChecked(queryContext.getExecutionControls(), "run-try-beginning", ForemanException.class);
      queryText = queryRequest.getPlan();

      // convert a run query request into action
      switch (queryRequest.getType()) {
      case LOGICAL:
        parseAndRunLogicalPlan(queryRequest.getPlan());
        break;
      case PHYSICAL:
        parseAndRunPhysicalPlan(queryRequest.getPlan());
        break;
      case SQL:
        runSQL(queryRequest.getPlan());
        break;
      default:
        throw new IllegalStateException();
      }
      injector.injectChecked(queryContext.getExecutionControls(), "run-try-end", ForemanException.class);
    } catch (final OutOfMemoryException | OutOfMemoryRuntimeException e) {
      moveToState(QueryState.FAILED, UserException.memoryError(e).build());
    } catch (final ForemanException e) {
      moveToState(QueryState.FAILED, e);
    } catch (AssertionError | Exception ex) {
      moveToState(QueryState.FAILED,
          new ForemanException("Unexpected exception during fragment initialization: " + ex.getMessage(), ex));
    } catch (final OutOfMemoryError e) {
      if ("Direct buffer memory".equals(e.getMessage())) {
        moveToState(QueryState.FAILED,
            UserException.resourceError(e)
                .message("One or more nodes ran out of memory while executing the query.")
                .build());
      } else {
        /*
         * FragmentExecutors use a DrillbitStatusListener to watch out for the death of their query's Foreman. So, if we
         * die here, they should get notified about that, and cancel themselves; we don't have to attempt to notify
         * them, which might not work under these conditions.
         */
        System.out.println("Node ran out of Heap memory, exiting.");
        e.printStackTrace();
        System.out.flush();
        System.exit(-1);
      }

    } finally {
      /*
       * Begin accepting external events.
       *
       * Doing this here in the finally clause will guarantee that it occurs. Otherwise, if there
       * is an exception anywhere during setup, it wouldn't occur, and any events that are generated
       * as a result of any partial setup that was done (such as the FragmentSubmitListener,
       * the ResponseSendListener, or an external call to cancel()), will hang the thread that makes the
       * event delivery call.
       *
       * If we do throw an exception during setup, and have already moved to QueryState.FAILED, we just need to
       * make sure that we can't make things any worse as those events are delivered, but allow
       * any necessary remaining cleanup to proceed.
       *
       * Note that cancellations cannot be simulated before this point, i.e. pauses can be injected, because Foreman
       * would wait on the cancelling thread to signal a resume and the cancelling thread would wait on the Foreman
       * to accept events.
       */
      acceptExternalEvents.countDown();

      // If we received the resume signal before fragments are setup, the first call does not actually resume the
      // fragments. Since setup is done, all fragments must have been delivered to remote nodes. Now we can resume.
      if(resume) {
        resume();
      }
      injector.injectPause(queryContext.getExecutionControls(), "foreman-ready", logger);

      // restore the thread's original name
      currentThread.setName(originalName);
    }

    /*
     * Note that despite the run() completing, the Foreman continues to exist, and receives
     * events (indirectly, through the QueryManager's use of stateListener), about fragment
     * completions. It won't go away until everything is completed, failed, or cancelled.
     */
  }

  private void releaseLease() {
    while (lease != null) {
      try {
        lease.close();
        lease = null;
      } catch (final InterruptedException e) {
        // if we end up here, the while loop will try again
      } catch (final Exception e) {
        logger.warn("Failure while releasing lease.", e);
        break;
      }
    }
  }

  private void parseAndRunLogicalPlan(final String json) throws ExecutionSetupException {
    LogicalPlan logicalPlan;
    try {
      logicalPlan = drillbitContext.getPlanReader().readLogicalPlan(json);
    } catch (final IOException e) {
      throw new ForemanException("Failure parsing logical plan.", e);
    }

    if (logicalPlan.getProperties().resultMode == ResultMode.LOGICAL) {
      throw new ForemanException(
          "Failure running plan.  You requested a result mode of LOGICAL and submitted a logical plan.  In this case you're output mode must be PHYSICAL or EXEC.");
    }

    log(logicalPlan);

    final PhysicalPlan physicalPlan = convert(logicalPlan);

    if (logicalPlan.getProperties().resultMode == ResultMode.PHYSICAL) {
      returnPhysical(physicalPlan);
      return;
    }

    log(physicalPlan);
    runPhysicalPlan(physicalPlan);
  }

  private void log(final LogicalPlan plan) {
    if (logger.isDebugEnabled()) {
      logger.debug("Logical {}", plan.unparse(queryContext.getConfig()));
    }
  }

  private void log(final PhysicalPlan plan) {
    if (logger.isDebugEnabled()) {
      try {
        final String planText = queryContext.getConfig().getMapper().writeValueAsString(plan);
        logger.debug("Physical {}", planText);
      } catch (final IOException e) {
        logger.warn("Error while attempting to log physical plan.", e);
      }
    }
  }

  private void returnPhysical(final PhysicalPlan plan) throws ExecutionSetupException {
    final String jsonPlan = plan.unparse(queryContext.getConfig().getMapper().writer());
    runPhysicalPlan(DirectPlan.createDirectPlan(queryContext, new PhysicalFromLogicalExplain(jsonPlan)));
  }

  public static class PhysicalFromLogicalExplain {
    public final String json;

    public PhysicalFromLogicalExplain(final String json) {
      this.json = json;
    }
  }

  private void parseAndRunPhysicalPlan(final String json) throws ExecutionSetupException {
    try {
      final PhysicalPlan plan = drillbitContext.getPlanReader().readPhysicalPlan(json);
      runPhysicalPlan(plan);
    } catch (final IOException e) {
      throw new ForemanSetupException("Failure while parsing physical plan.", e);
    }
  }

  private void runPhysicalPlan(final PhysicalPlan plan) throws ExecutionSetupException {
    validatePlan(plan);
    setupSortMemoryAllocations(plan);
    acquireQuerySemaphore(plan);

    final QueryWorkUnit work = getQueryWorkUnit(plan);
    final List<PlanFragment> planFragments = work.getFragments();
    final PlanFragment rootPlanFragment = work.getRootFragment();
    assert queryId == rootPlanFragment.getHandle().getQueryId();

    drillbitContext.getWorkBus().addFragmentStatusListener(queryId, queryManager.getFragmentStatusListener());
    drillbitContext.getClusterCoordinator().addDrillbitStatusListener(queryManager.getDrillbitStatusListener());

    logger.debug("Submitting fragments to run.");

    // set up the root fragment first so we'll have incoming buffers available.
    setupRootFragment(rootPlanFragment, work.getRootOperator());

    setupNonRootFragments(planFragments);
    drillbitContext.getAllocator().resetFragmentLimits(); // TODO a global effect for this query?!?

    moveToState(QueryState.RUNNING, null);
    logger.debug("Fragments running.");
  }

  private static void validatePlan(final PhysicalPlan plan) throws ForemanSetupException {
    if (plan.getProperties().resultMode != ResultMode.EXEC) {
      throw new ForemanSetupException(String.format(
          "Failure running plan.  You requested a result mode of %s and a physical plan can only be output as EXEC",
          plan.getProperties().resultMode));
    }
  }

  private void setupSortMemoryAllocations(final PhysicalPlan plan) {
    // look for external sorts
    final List<ExternalSort> sortList = new LinkedList<>();
    for (final PhysicalOperator op : plan.getSortedOperators()) {
      if (op instanceof ExternalSort) {
        sortList.add((ExternalSort) op);
      }
    }

    // if there are any sorts, compute the maximum allocation, and set it on them
    if (sortList.size() > 0) {
      final OptionManager optionManager = queryContext.getOptions();
      final long maxWidthPerNode = optionManager.getOption(ExecConstants.MAX_WIDTH_PER_NODE_KEY).num_val;
      long maxAllocPerNode = Math.min(DrillConfig.getMaxDirectMemory(),
          queryContext.getConfig().getLong(ExecConstants.TOP_LEVEL_MAX_ALLOC));
      maxAllocPerNode = Math.min(maxAllocPerNode,
          optionManager.getOption(ExecConstants.MAX_QUERY_MEMORY_PER_NODE_KEY).num_val);
      final long maxSortAlloc = maxAllocPerNode / (sortList.size() * maxWidthPerNode);
      logger.debug("Max sort alloc: {}", maxSortAlloc);

      for(final ExternalSort externalSort : sortList) {
        externalSort.setMaxAllocation(maxSortAlloc);
      }
    }
  }

  /**
   * This limits the number of "small" and "large" queries that a Drill cluster will run
   * simultaneously, if queueing is enabled. If the query is unable to run, this will block
   * until it can. Beware that this is called under run(), and so will consume a Thread
   * while it waits for the required distributed semaphore.
   *
   * @param plan the query plan
   * @throws ForemanSetupException
   */
  private void acquireQuerySemaphore(final PhysicalPlan plan) throws ForemanSetupException {
    final OptionManager optionManager = queryContext.getOptions();
    final boolean queuingEnabled = optionManager.getOption(ExecConstants.ENABLE_QUEUE);
    if (queuingEnabled) {
      final long queueThreshold = optionManager.getOption(ExecConstants.QUEUE_THRESHOLD_SIZE);
      double totalCost = 0;
      for (final PhysicalOperator ops : plan.getSortedOperators()) {
        totalCost += ops.getCost();
      }

      final long queueTimeout = optionManager.getOption(ExecConstants.QUEUE_TIMEOUT);
      final String queueName;

      try {
        @SuppressWarnings("resource")
        final ClusterCoordinator clusterCoordinator = drillbitContext.getClusterCoordinator();
        final DistributedSemaphore distributedSemaphore;

        // get the appropriate semaphore
        if (totalCost > queueThreshold) {
          final int largeQueue = (int) optionManager.getOption(ExecConstants.LARGE_QUEUE_SIZE);
          distributedSemaphore = clusterCoordinator.getSemaphore("query.large", largeQueue);
          queueName = "large";
        } else {
          final int smallQueue = (int) optionManager.getOption(ExecConstants.SMALL_QUEUE_SIZE);
          distributedSemaphore = clusterCoordinator.getSemaphore("query.small", smallQueue);
          queueName = "small";
        }


        lease = distributedSemaphore.acquire(queueTimeout, TimeUnit.MILLISECONDS);
      } catch (final Exception e) {
        throw new ForemanSetupException("Unable to acquire slot for query.", e);
      }

      if (lease == null) {
        throw UserException
            .resourceError()
            .message(
                "Unable to acquire queue resources for query within timeout.  Timeout for %s queue was set at %d seconds.",
                queueName, queueTimeout / 1000)
            .build();
      }

    }
  }

  Exception getCurrentException() {
    return foremanResult.getException();
  }

  private QueryWorkUnit getQueryWorkUnit(final PhysicalPlan plan) throws ExecutionSetupException {
    final PhysicalOperator rootOperator = plan.getSortedOperators(false).iterator().next();
    final Fragment rootFragment = rootOperator.accept(MakeFragmentsVisitor.INSTANCE, null);
    final SimpleParallelizer parallelizer = new SimpleParallelizer(queryContext);
    final QueryWorkUnit queryWorkUnit = parallelizer.getFragments(
        queryContext.getOptions().getOptionList(), queryContext.getCurrentEndpoint(),
        queryId, queryContext.getActiveEndpoints(), drillbitContext.getPlanReader(), rootFragment,
        initiatingClient.getSession(), queryContext.getQueryContextInfo());

    if (logger.isTraceEnabled()) {
      final StringBuilder sb = new StringBuilder();
      sb.append("PlanFragments for query ");
      sb.append(queryId);
      sb.append('\n');

      final List<PlanFragment> planFragments = queryWorkUnit.getFragments();
      final int fragmentCount = planFragments.size();
      int fragmentIndex = 0;
      for(final PlanFragment planFragment : planFragments) {
        final FragmentHandle fragmentHandle = planFragment.getHandle();
        sb.append("PlanFragment(");
        sb.append(++fragmentIndex);
        sb.append('/');
        sb.append(fragmentCount);
        sb.append(") major_fragment_id ");
        sb.append(fragmentHandle.getMajorFragmentId());
        sb.append(" minor_fragment_id ");
        sb.append(fragmentHandle.getMinorFragmentId());
        sb.append('\n');

        final DrillbitEndpoint endpointAssignment = planFragment.getAssignment();
        sb.append("  DrillbitEndpoint address ");
        sb.append(endpointAssignment.getAddress());
        sb.append('\n');

        String jsonString = "<<malformed JSON>>";
        sb.append("  fragment_json: ");
        final ObjectMapper objectMapper = new ObjectMapper();
        try
        {
          final Object json = objectMapper.readValue(planFragment.getFragmentJson(), Object.class);
          jsonString = objectMapper.defaultPrettyPrintingWriter().writeValueAsString(json);
        } catch(final Exception e) {
          // we've already set jsonString to a fallback value
        }
        sb.append(jsonString);

        logger.trace(sb.toString());
      }
    }

    return queryWorkUnit;
  }

  /**
   * Manages the end-state processing for Foreman.
   *
   * End-state processing is tricky, because even if a query appears to succeed, but
   * we then encounter a problem during cleanup, we still want to mark the query as
   * failed. So we have to construct the successful result we would send, and then
   * clean up before we send that result, possibly changing that result if we encounter
   * a problem during cleanup. We only send the result when there is nothing left to
   * do, so it will account for any possible problems.
   *
   * The idea here is to make close()ing the ForemanResult do the final cleanup and
   * sending. Closing the result must be the last thing that is done by Foreman.
   */
  private class ForemanResult implements AutoCloseable {
    private QueryState resultState = null;
    private volatile Exception resultException = null;
    private boolean isClosed = false;

    /**
     * Set up the result for a COMPLETED or CANCELED state.
     *
     * <p>Note that before sending this result, we execute cleanup steps that could
     * result in this result still being changed to a FAILED state.
     *
     * @param queryState one of COMPLETED or CANCELED
     */
    public void setCompleted(final QueryState queryState) {
      Preconditions.checkArgument((queryState == QueryState.COMPLETED) || (queryState == QueryState.CANCELED));
      Preconditions.checkState(!isClosed);
      Preconditions.checkState(resultState == null);

      resultState = queryState;
    }

    /**
     * Set up the result for a FAILED state.
     *
     * <p>Failures that occur during cleanup processing will be added as suppressed
     * exceptions.
     *
     * @param exception the exception that led to the FAILED state
     */
    public void setFailed(final Exception exception) {
      Preconditions.checkArgument(exception != null);
      Preconditions.checkState(!isClosed);
      Preconditions.checkState(resultState == null);

      resultState = QueryState.FAILED;
      resultException = exception;
    }

    /**
     * Ignore the current status and force the given failure as current status.
     * NOTE: Used only for testing purposes. Shouldn't be used in production.
     */
    public void setForceFailure(final Exception exception) {
      Preconditions.checkArgument(exception != null);
      Preconditions.checkState(!isClosed);

      resultState = QueryState.FAILED;
      resultException = exception;
    }

    /**
     * Add an exception to the result. All exceptions after the first become suppressed
     * exceptions hanging off the first.
     *
     * @param exception the exception to add
     */
    private void addException(final Exception exception) {
      Preconditions.checkNotNull(exception);

      if (resultException == null) {
        resultException = exception;
      } else {
        resultException.addSuppressed(exception);
      }
    }

    /**
     * Expose the current exception (if it exists). This is useful for secondary reporting to the query profile.
     *
     * @return the current Foreman result exception or null.
     */
    public Exception getException() {
      return resultException;
    }

    /**
     * Close the given resource, catching and adding any caught exceptions via {@link #addException(Exception)}. If an
     * exception is caught, it will change the result state to FAILED, regardless of what its current value.
     *
     * @param autoCloseable
     *          the resource to close
     */
    private void suppressingClose(final AutoCloseable autoCloseable) {
      Preconditions.checkState(!isClosed);
      Preconditions.checkState(resultState != null);

      if (autoCloseable == null) {
        return;
      }

      try {
        autoCloseable.close();
      } catch(final Exception e) {
        /*
         * Even if the query completed successfully, we'll still report failure if we have
         * problems cleaning up.
         */
        resultState = QueryState.FAILED;
        addException(e);
      }
    }

    private void logQuerySummary() {
      try {
        LoggedQuery q = new LoggedQuery(
            QueryIdHelper.getQueryId(queryId),
            queryContext.getQueryContextInfo().getDefaultSchemaName(),
            queryText,
            new Date(queryContext.getQueryContextInfo().getQueryStartTime()),
            new Date(System.currentTimeMillis()),
            state,
            queryContext.getSession().getCredentials().getUserName());
        queryLogger.info(MAPPER.writeValueAsString(q));
      } catch (Exception e) {
        logger.error("Failure while recording query information to query log.", e);
      }
    }

    @Override
    public void close() {
      Preconditions.checkState(!isClosed);
      Preconditions.checkState(resultState != null);

      logger.info("foreman cleaning up.");
      injector.injectPause(queryContext.getExecutionControls(), "foreman-cleanup", logger);

      // remove the channel disconnected listener (doesn't throw)
      closeFuture.removeListener(closeListener);

      // log the query summary
      logQuerySummary();

      // These are straight forward removals from maps, so they won't throw.
      drillbitContext.getWorkBus().removeFragmentStatusListener(queryId);
      drillbitContext.getClusterCoordinator().removeDrillbitStatusListener(queryManager.getDrillbitStatusListener());

      suppressingClose(queryContext);

      /*
       * We do our best to write the latest state, but even that could fail. If it does, we can't write
       * the (possibly newly failing) state, so we continue on anyway.
       *
       * We only need to do this if the resultState differs from the last recorded state
       */
      if (resultState != state) {
        suppressingClose(new AutoCloseable() {
          @Override
          public void close() throws Exception {
            recordNewState(resultState);
          }
        });
      }

      /*
       * Construct the response based on the latest resultState. The builder shouldn't fail.
       */
      final QueryResult.Builder resultBuilder = QueryResult.newBuilder()
          .setQueryId(queryId)
          .setQueryState(resultState);
      final UserException uex;
      if (resultException != null) {
        final boolean verbose = queryContext.getOptions().getOption(ExecConstants.ENABLE_VERBOSE_ERRORS_KEY).bool_val;
        uex = UserException.systemError(resultException).addIdentity(queryContext.getCurrentEndpoint()).build();
        resultBuilder.addError(uex.getOrCreatePBError(verbose));
      } else {
        uex = null;
      }

      // we store the final result here so we can capture any error/errorId in the profile for later debugging.
      queryManager.writeFinalProfile(uex);

      /*
       * If sending the result fails, we don't really have any way to modify the result we tried to send;
       * it is possible it got sent but the result came from a later part of the code path. It is also
       * possible the connection has gone away, so this is irrelevant because there's nowhere to
       * send anything to.
       */
      try {
        // send whatever result we ended up with
        initiatingClient.sendResult(responseListener, resultBuilder.build(), true);
      } catch(final Exception e) {
        addException(e);
        logger.warn("Exception sending result to client", resultException);
      }

      // Remove the Foreman from the running query list.
      bee.retireForeman(Foreman.this);

      try {
        releaseLease();
      } finally {
        isClosed = true;
      }
    }
  }

  private static class StateEvent {
    final QueryState newState;
    final Exception exception;

    StateEvent(final QueryState newState, final Exception exception) {
      this.newState = newState;
      this.exception = exception;
    }
  }

  private class StateSwitch extends EventProcessor<StateEvent> {
    public void moveToState(final QueryState newState, final Exception exception) {
      sendEvent(new StateEvent(newState, exception));
    }

    @Override
    protected void processEvent(final StateEvent event) {
      final QueryState newState = event.newState;
      final Exception exception = event.exception;

      // TODO Auto-generated method stub
      logger.info("State change requested.  {} --> {}", state, newState,
          exception);
      switch (state) {
      case PENDING:
        if (newState == QueryState.RUNNING) {
          recordNewState(QueryState.RUNNING);
          return;
        }

        //$FALL-THROUGH$

      case RUNNING: {
        /*
         * For cases that cancel executing fragments, we have to record the new
         * state first, because the cancellation of the local root fragment will
         * cause this to be called recursively.
         */
        switch (newState) {
        case CANCELLATION_REQUESTED: {
          assert exception == null;
          queryManager.markEndTime();
          recordNewState(QueryState.CANCELLATION_REQUESTED);
          queryManager.cancelExecutingFragments(drillbitContext);
          foremanResult.setCompleted(QueryState.CANCELED);
          /*
           * We don't close the foremanResult until we've gotten
           * acknowledgements, which happens below in the case for current state
           * == CANCELLATION_REQUESTED.
           */
          return;
        }

        case COMPLETED: {
          assert exception == null;
          queryManager.markEndTime();
          recordNewState(QueryState.COMPLETED);
          foremanResult.setCompleted(QueryState.COMPLETED);
          foremanResult.close();
          return;
        }

        case FAILED: {
          assert exception != null;
          queryManager.markEndTime();
          recordNewState(QueryState.FAILED);
          queryManager.cancelExecutingFragments(drillbitContext);
          foremanResult.setFailed(exception);
          foremanResult.close();
          return;
        }

        default:
          throw new IllegalStateException("illegal transition from RUNNING to "
              + newState);
        }
      }

      case CANCELLATION_REQUESTED:
        if ((newState == QueryState.CANCELED)
            || (newState == QueryState.COMPLETED)
            || (newState == QueryState.FAILED)) {

          if (drillbitContext.getConfig().getBoolean(ExecConstants.RETURN_ERROR_FOR_FAILURE_IN_CANCELLED_FRAGMENTS)) {
            if (newState == QueryState.FAILED) {
              assert exception != null;
              recordNewState(QueryState.FAILED);
              foremanResult.setForceFailure(exception);
            }
          }
          /*
           * These amount to a completion of the cancellation requests' cleanup;
           * now we can clean up and send the result.
           */
          foremanResult.close();
        }
        return;

      case CANCELED:
      case COMPLETED:
      case FAILED:
        logger
            .warn(
                "Dropping request to move to {} state as query is already at {} state (which is terminal).",
                newState, state);
        return;
      }

      throw new IllegalStateException(String.format(
          "Failure trying to change states: %s --> %s", state.name(),
          newState.name()));
    }
  }

  /**
   * Tells the foreman to move to a new state.
   *
   * @param newState the state to move to
   * @param exception if not null, the exception that drove this state transition (usually a failure)
   */
  private void moveToState(final QueryState newState, final Exception exception) {
    stateSwitch.moveToState(newState, exception);
  }

  private void recordNewState(final QueryState newState) {
    state = newState;
    queryManager.updateEphemeralState(newState);
  }

  private void runSQL(final String sql) throws ExecutionSetupException {
    final DrillSqlWorker sqlWorker = new DrillSqlWorker(queryContext);
    final Pointer<String> textPlan = new Pointer<>();
    final PhysicalPlan plan = sqlWorker.getPlan(sql, textPlan);
    queryManager.setPlanText(textPlan.value);
    runPhysicalPlan(plan);
  }

  private PhysicalPlan convert(final LogicalPlan plan) throws OptimizerException {
    if (logger.isDebugEnabled()) {
      logger.debug("Converting logical plan {}.", plan.toJsonStringSafe(queryContext.getConfig()));
    }
    return new BasicOptimizer(queryContext, initiatingClient).optimize(
        new BasicOptimizer.BasicOptimizationContext(queryContext), plan);
  }

  public QueryId getQueryId() {
    return queryId;
  }

  /**
   * Set up the root fragment (which will run locally), and submit it for execution.
   *
   * @param rootFragment
   * @param rootOperator
   * @throws ExecutionSetupException
   */
  private void setupRootFragment(final PlanFragment rootFragment, final FragmentRoot rootOperator)
      throws ExecutionSetupException {
    @SuppressWarnings("resource")
    final FragmentContext rootContext = new FragmentContext(drillbitContext, rootFragment, queryContext,
        initiatingClient, drillbitContext.getFunctionImplementationRegistry());
    @SuppressWarnings("resource")
    final IncomingBuffers buffers = new IncomingBuffers(rootFragment, rootContext);
    rootContext.setBuffers(buffers);

    queryManager.addFragmentStatusTracker(rootFragment, true);

    rootRunner = new FragmentExecutor(rootContext, rootFragment,
        queryManager.newRootStatusHandler(rootContext, drillbitContext),
        rootOperator);
    final RootFragmentManager fragmentManager = new RootFragmentManager(rootFragment.getHandle(), buffers, rootRunner);

    if (buffers.isDone()) {
      // if we don't have to wait for any incoming data, start the fragment runner.
      bee.addFragmentRunner(fragmentManager.getRunnable());
    } else {
      // if we do, record the fragment manager in the workBus.
      // TODO aren't we managing our own work? What does this do? It looks like this will never get run
      drillbitContext.getWorkBus().addFragmentManager(fragmentManager);
    }
  }

  /**
   * Set up the non-root fragments for execution. Some may be local, and some may be remote.
   * Messages are sent immediately, so they may start returning data even before we complete this.
   *
   * @param fragments the fragments
   * @throws ForemanException
   */
  private void setupNonRootFragments(final Collection<PlanFragment> fragments) throws ForemanException {
    /*
     * We will send a single message to each endpoint, regardless of how many fragments will be
     * executed there. We need to start up the intermediate fragments first so that they will be
     * ready once the leaf fragments start producing data. To satisfy both of these, we will
     * make a pass through the fragments and put them into these two maps according to their
     * leaf/intermediate state, as well as their target drillbit.
     */
    final Multimap<DrillbitEndpoint, PlanFragment> leafFragmentMap = ArrayListMultimap.create();
    final Multimap<DrillbitEndpoint, PlanFragment> intFragmentMap = ArrayListMultimap.create();

    // record all fragments for status purposes.
    for (final PlanFragment planFragment : fragments) {
      logger.trace("Tracking intermediate remote node {} with data {}",
                   planFragment.getAssignment(), planFragment.getFragmentJson());
      queryManager.addFragmentStatusTracker(planFragment, false);
      if (planFragment.getLeafFragment()) {
        leafFragmentMap.put(planFragment.getAssignment(), planFragment);
      } else {
        intFragmentMap.put(planFragment.getAssignment(), planFragment);
      }
    }

    /*
     * We need to wait for the intermediates to be sent so that they'll be set up by the time
     * the leaves start producing data. We'll use this latch to wait for the responses.
     *
     * However, in order not to hang the process if any of the RPC requests fails, we always
     * count down (see FragmentSubmitFailures), but we count the number of failures so that we'll
     * know if any submissions did fail.
     */
    final int numIntFragments = intFragmentMap.keySet().size();
    final ExtendedLatch endpointLatch = new ExtendedLatch(numIntFragments);
    final FragmentSubmitFailures fragmentSubmitFailures = new FragmentSubmitFailures();

    // send remote intermediate fragments
    for (final DrillbitEndpoint ep : intFragmentMap.keySet()) {
      sendRemoteFragments(ep, intFragmentMap.get(ep), endpointLatch, fragmentSubmitFailures);
    }

    final long timeout = RPC_WAIT_IN_MSECS_PER_FRAGMENT * numIntFragments;
    if(numIntFragments > 0 && !endpointLatch.awaitUninterruptibly(timeout)){
      long numberRemaining = endpointLatch.getCount();
      throw UserException.connectionError()
          .message(
              "Exceeded timeout (%d) while waiting send intermediate work fragments to remote nodes. " +
                  "Sent %d and only heard response back from %d nodes.",
              timeout, numIntFragments, numIntFragments - numberRemaining)
          .build();
    }

    // if any of the intermediate fragment submissions failed, fail the query
    final List<FragmentSubmitFailures.SubmissionException> submissionExceptions = fragmentSubmitFailures.submissionExceptions;
    if (submissionExceptions.size() > 0) {
      Set<DrillbitEndpoint> endpoints = Sets.newHashSet();
      StringBuilder sb = new StringBuilder();
      boolean first = true;

      for (FragmentSubmitFailures.SubmissionException e : fragmentSubmitFailures.submissionExceptions) {
        DrillbitEndpoint endpoint = e.drillbitEndpoint;
        if (endpoints.add(endpoint)) {
          if (first) {
            first = false;
          } else {
            sb.append(", ");
          }
          sb.append(endpoint.getAddress());
        }
      }
      throw UserException.connectionError(submissionExceptions.get(0).rpcException)
          .message("Error setting up remote intermediate fragment execution")
          .addContext("Nodes with failures", sb.toString())
          .build();
    }

    injector.injectChecked(queryContext.getExecutionControls(), "send-fragments", ForemanException.class);
    /*
     * Send the remote (leaf) fragments; we don't wait for these. Any problems will come in through
     * the regular sendListener event delivery.
     */
    for (final DrillbitEndpoint ep : leafFragmentMap.keySet()) {
      sendRemoteFragments(ep, leafFragmentMap.get(ep), null, null);
    }
  }

  /**
   * Send all the remote fragments belonging to a single target drillbit in one request.
   *
   * @param assignment the drillbit assigned to these fragments
   * @param fragments the set of fragments
   * @param latch the countdown latch used to track the requests to all endpoints
   * @param fragmentSubmitFailures the submission failure counter used to track the requests to all endpoints
   */
  private void sendRemoteFragments(final DrillbitEndpoint assignment, final Collection<PlanFragment> fragments,
      final CountDownLatch latch, final FragmentSubmitFailures fragmentSubmitFailures) {
    @SuppressWarnings("resource")
    final Controller controller = drillbitContext.getController();
    final InitializeFragments.Builder fb = InitializeFragments.newBuilder();
    for(final PlanFragment planFragment : fragments) {
      fb.addFragment(planFragment);
    }
    final InitializeFragments initFrags = fb.build();

    logger.debug("Sending remote fragments to \nNode:\n{} \n\nData:\n{}", assignment, initFrags);
    final FragmentSubmitListener listener =
        new FragmentSubmitListener(assignment, initFrags, latch, fragmentSubmitFailures);
    controller.getTunnel(assignment).sendFragments(listener, initFrags);
  }

  public QueryState getState() {
    return state;
  }

  /**
   * Used by {@link FragmentSubmitListener} to track the number of submission failures.
   */
  private static class FragmentSubmitFailures {
    static class SubmissionException {
      final DrillbitEndpoint drillbitEndpoint;
      final RpcException rpcException;

      SubmissionException(@SuppressWarnings("unused") final DrillbitEndpoint drillbitEndpoint,
          final RpcException rpcException) {
        this.drillbitEndpoint = drillbitEndpoint;
        this.rpcException = rpcException;
      }
    }

    final List<SubmissionException> submissionExceptions = new LinkedList<>();

    void addFailure(final DrillbitEndpoint drillbitEndpoint, final RpcException rpcException) {
      submissionExceptions.add(new SubmissionException(drillbitEndpoint, rpcException));
    }
  }

  private class FragmentSubmitListener extends EndpointListener<Ack, InitializeFragments> {
    private final CountDownLatch latch;
    private final FragmentSubmitFailures fragmentSubmitFailures;

    /**
     * Constructor.
     *
     * @param endpoint the endpoint for the submission
     * @param value the initialize fragments message
     * @param latch the latch to count down when the status is known; may be null
     * @param fragmentSubmitFailures the counter to use for failures; must be non-null iff latch is non-null
     */
    public FragmentSubmitListener(final DrillbitEndpoint endpoint, final InitializeFragments value,
        final CountDownLatch latch, final FragmentSubmitFailures fragmentSubmitFailures) {
      super(endpoint, value);
      Preconditions.checkState((latch == null) == (fragmentSubmitFailures == null));
      this.latch = latch;
      this.fragmentSubmitFailures = fragmentSubmitFailures;
    }

    @Override
    public void success(final Ack ack, final ByteBuf byteBuf) {
      if (latch != null) {
        latch.countDown();
      }
    }

    @Override
    public void failed(final RpcException ex) {
      if (latch != null) {
        fragmentSubmitFailures.addFailure(endpoint, ex);
        latch.countDown();
      } else {
        // since this won't be waited on, we can wait to deliver this event once the Foreman is ready
        logger.debug("Failure while sending fragment.  Stopping query.", ex);
        stateListener.moveToState(QueryState.FAILED, ex);
      }
    }

    @Override
    public void interrupted(final InterruptedException e) {
      // Foreman shouldn't get interrupted while waiting for the RPC outcome of fragment submission.
      // Consider the interrupt as failure.
      final String errMsg = "Interrupted while waiting for the RPC outcome of fragment submission.";
      logger.error(errMsg, e);
      failed(new RpcException(errMsg, e));
    }
  }

  /**
   * Provides gated access to state transitions.
   *
   * <p>The StateListener waits on a latch before delivery state transitions to the Foreman. The
   * latch will be tripped when the Foreman is sufficiently set up that it can receive and process
   * external events from other threads.
   */
  public class StateListener {
    /**
     * Move the Foreman to the specified new state.
     *
     * @param newState the state to move to
     * @param ex if moving to a failure state, the exception that led to the failure; used for reporting
     *   to the user
     */
    public void moveToState(final QueryState newState, final Exception ex) {
      acceptExternalEvents.awaitUninterruptibly();

      Foreman.this.moveToState(newState, ex);
    }
  }

  /**
   * Listens for the status of the RPC response sent to the user for the query.
   */
  private class ResponseSendListener extends BaseRpcOutcomeListener<Ack> {
    @Override
    public void failed(final RpcException ex) {
      logger.info("Failure while trying communicate query result to initiating client. " +
              "This would happen if a client is disconnected before response notice can be sent.", ex);
      stateListener.moveToState(QueryState.FAILED, ex);
    }

    @Override
    public void interrupted(final InterruptedException e) {
      logger.warn("Interrupted while waiting for RPC outcome of sending final query result to initiating client.");
      stateListener.moveToState(QueryState.FAILED, e);
    }
  }
}


File: exec/java-exec/src/main/java/org/apache/drill/exec/work/fragment/FragmentExecutor.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.work.fragment;

import java.io.IOException;
import java.security.PrivilegedExceptionAction;
import java.util.Set;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

import org.apache.drill.common.DeferredException;
import org.apache.drill.common.concurrent.ExtendedLatch;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.exec.coord.ClusterCoordinator;
import org.apache.drill.exec.memory.OutOfMemoryRuntimeException;
import org.apache.drill.exec.ops.FragmentContext;
import org.apache.drill.exec.ops.FragmentContext.ExecutorState;
import org.apache.drill.exec.physical.base.FragmentRoot;
import org.apache.drill.exec.physical.impl.ImplCreator;
import org.apache.drill.exec.physical.impl.RootExec;
import org.apache.drill.exec.proto.BitControl.FragmentStatus;
import org.apache.drill.exec.proto.BitControl.PlanFragment;
import org.apache.drill.exec.proto.CoordinationProtos;
import org.apache.drill.exec.proto.CoordinationProtos.DrillbitEndpoint;
import org.apache.drill.exec.proto.ExecProtos.FragmentHandle;
import org.apache.drill.exec.proto.UserBitShared.FragmentState;
import org.apache.drill.exec.proto.helper.QueryIdHelper;
import org.apache.drill.exec.server.DrillbitContext;
import org.apache.drill.exec.testing.ControlsInjector;
import org.apache.drill.exec.testing.ControlsInjectorFactory;
import org.apache.drill.exec.util.ImpersonationUtil;
import org.apache.drill.exec.work.foreman.DrillbitStatusListener;
import org.apache.hadoop.security.UserGroupInformation;

/**
 * Responsible for running a single fragment on a single Drillbit. Listens/responds to status request
 * and cancellation messages.
 */
public class FragmentExecutor implements Runnable {
  private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(FragmentExecutor.class);
  private static final ControlsInjector injector = ControlsInjectorFactory.getInjector(FragmentExecutor.class);

  private final AtomicBoolean hasCloseoutThread = new AtomicBoolean(false);
  private final String fragmentName;
  private final FragmentContext fragmentContext;
  private final StatusReporter listener;
  private final DeferredException deferredException = new DeferredException();
  private final PlanFragment fragment;
  private final FragmentRoot rootOperator;

  private volatile RootExec root;
  private final AtomicReference<FragmentState> fragmentState = new AtomicReference<>(FragmentState.AWAITING_ALLOCATION);
  private final ExtendedLatch acceptExternalEvents = new ExtendedLatch();

  // Thread that is currently executing the Fragment. Value is null if the fragment hasn't started running or finished
  private final AtomicReference<Thread> myThreadRef = new AtomicReference<>(null);

  /**
   * Create a FragmentExecutor where we need to parse and materialize the root operator.
   *
   * @param context
   * @param fragment
   * @param listener
   * @param rootOperator
   */
  public FragmentExecutor(final FragmentContext context, final PlanFragment fragment,
      final StatusReporter listener) {
    this(context, fragment, listener, null);
  }

  /**
   * Create a FragmentExecutor where we already have a root operator in memory.
   *
   * @param context
   * @param fragment
   * @param listener
   * @param rootOperator
   */
  public FragmentExecutor(final FragmentContext context, final PlanFragment fragment,
      final StatusReporter listener, final FragmentRoot rootOperator) {
    this.fragmentContext = context;
    this.listener = listener;
    this.fragment = fragment;
    this.rootOperator = rootOperator;
    this.fragmentName = QueryIdHelper.getQueryIdentifier(context.getHandle());

    context.setExecutorState(new ExecutorStateImpl());
  }

  @Override
  public String toString() {
    final StringBuilder builder = new StringBuilder();
    builder.append("FragmentExecutor [fragmentContext=");
    builder.append(fragmentContext);
    builder.append(", fragmentState=");
    builder.append(fragmentState);
    builder.append("]");
    return builder.toString();
  }

  /**
   * Returns the current fragment status if the fragment is running. Otherwise, returns no status.
   *
   * @return FragmentStatus or null.
   */
  public FragmentStatus getStatus() {
    /*
     * If the query is not in a running state, the operator tree is still being constructed and
     * there is no reason to poll for intermediate results.
     *
     * Previously the call to get the operator stats with the AbstractStatusReporter was happening
     * before this check. This caused a concurrent modification exception as the list of operator
     * stats is iterated over while collecting info, and added to while building the operator tree.
     */
    if (fragmentState.get() != FragmentState.RUNNING) {
      return null;
    }

    return AbstractStatusReporter
        .getBuilder(fragmentContext, FragmentState.RUNNING, null)
        .build();
  }

  /**
   * Cancel the execution of this fragment is in an appropriate state. Messages come from external.
   * NOTE that this will be called from threads *other* than the one running this runnable(),
   * so we need to be careful about the state transitions that can result.
   */
  public void cancel() {
    final boolean thisIsOnlyThread = this.hasCloseoutThread.compareAndSet(false, true);

    if (!thisIsOnlyThread) {
      acceptExternalEvents.awaitUninterruptibly();

      /*
       * We set the cancel requested flag but the actual cancellation is managed by the run() loop, if called.
       */
      updateState(FragmentState.CANCELLATION_REQUESTED);

      /*
       * Interrupt the thread so that it exits from any blocking operation it could be executing currently. We
       * synchronize here to ensure we don't accidentally create a race condition where we interrupt the close out
       * procedure of the main thread.
       */
      synchronized (myThreadRef) {
        final Thread myThread = myThreadRef.get();
        if (myThread != null) {
          logger.debug("Interrupting fragment thread {}", myThread.getName());
          myThread.interrupt();
        }
      }
    } else {
      updateState(FragmentState.CANCELLATION_REQUESTED);
      cleanup(FragmentState.FINISHED);
    }

  }

  private void cleanup(FragmentState state) {

    closeOutResources();

    updateState(state);
    // send the final state of the fragment. only the main execution thread can send the final state and it can
    // only be sent once.
    sendFinalState();

  }

  /**
   * Resume all the pauses within the current context. Note that this method will be called from threads *other* than
   * the one running this runnable(). Also, this method can be called multiple times.
   */
  public synchronized void unpause() {
    fragmentContext.getExecutionControls().unpauseAll();
  }

  /**
   * Inform this fragment that one of its downstream partners no longer needs additional records. This is most commonly
   * called in the case that a limit query is executed.
   *
   * @param handle The downstream FragmentHandle of the Fragment that needs no more records from this Fragment.
   */
  public void receivingFragmentFinished(final FragmentHandle handle) {
    acceptExternalEvents.awaitUninterruptibly();
    if (root != null) {
      logger.info("Applying request for early sender termination for {} -> {}.",
          QueryIdHelper.getFragmentId(this.getContext().getHandle()), QueryIdHelper.getFragmentId(handle));
      root.receivingFragmentFinished(handle);
    } else {
      logger.warn("Dropping request for early fragment termination for path {} -> {} as no root exec exists.",
          QueryIdHelper.getFragmentId(this.getContext().getHandle()), QueryIdHelper.getFragmentId(handle));
    }
  }

  @Override
  public void run() {
    // if a cancel thread has already entered this executor, we have not reason to continue.
    if (!hasCloseoutThread.compareAndSet(false, true)) {
      return;
    }

    final Thread myThread = Thread.currentThread();
    myThreadRef.set(myThread);
    final String originalThreadName = myThread.getName();
    final FragmentHandle fragmentHandle = fragmentContext.getHandle();
    final DrillbitContext drillbitContext = fragmentContext.getDrillbitContext();
    final ClusterCoordinator clusterCoordinator = drillbitContext.getClusterCoordinator();
    final DrillbitStatusListener drillbitStatusListener = new FragmentDrillbitStatusListener();
    final String newThreadName = QueryIdHelper.getExecutorThreadName(fragmentHandle);

    try {

      myThread.setName(newThreadName);

      // if we didn't get the root operator when the executor was created, create it now.
      final FragmentRoot rootOperator = this.rootOperator != null ? this.rootOperator :
          drillbitContext.getPlanReader().readFragmentOperator(fragment.getFragmentJson());

          root = ImplCreator.getExec(fragmentContext, rootOperator);
          if (root == null) {
            return;
          }

      clusterCoordinator.addDrillbitStatusListener(drillbitStatusListener);
      updateState(FragmentState.RUNNING);

      acceptExternalEvents.countDown();

      final DrillbitEndpoint endpoint = drillbitContext.getEndpoint();
      logger.debug("Starting fragment {}:{} on {}:{}",
          fragmentHandle.getMajorFragmentId(), fragmentHandle.getMinorFragmentId(),
          endpoint.getAddress(), endpoint.getUserPort());

      final UserGroupInformation queryUserUgi = fragmentContext.isImpersonationEnabled() ?
          ImpersonationUtil.createProxyUgi(fragmentContext.getQueryUserName()) :
          ImpersonationUtil.getProcessUserUGI();

      queryUserUgi.doAs(new PrivilegedExceptionAction<Void>() {
        public Void run() throws Exception {
          injector.injectChecked(fragmentContext.getExecutionControls(), "fragment-execution", IOException.class);
          /*
           * Run the query until root.next returns false OR we no longer need to continue.
           */
          while (shouldContinue() && root.next()) {
            // loop
          }

          return null;
        }
      });

    } catch (OutOfMemoryError | OutOfMemoryRuntimeException e) {
      if (!(e instanceof OutOfMemoryError) || "Direct buffer memory".equals(e.getMessage())) {
        fail(UserException.memoryError(e).build());
      } else {
        // we have a heap out of memory error. The JVM in unstable, exit.
        System.err.println("Node ran out of Heap memory, exiting.");
        e.printStackTrace(System.err);
        System.err.flush();
        System.exit(-2);

      }
    } catch (AssertionError | Exception e) {
      fail(e);
    } finally {

      // no longer allow this thread to be interrupted. We synchronize here to make sure that cancel can't set an
      // interruption after we have moved beyond this block.
      synchronized (myThreadRef) {
        myThreadRef.set(null);
        Thread.interrupted();
      }

      // We need to sure we countDown at least once. We'll do it here to guarantee that.
      acceptExternalEvents.countDown();

      // here we could be in FAILED, RUNNING, or CANCELLATION_REQUESTED
      cleanup(FragmentState.FINISHED);

      clusterCoordinator.removeDrillbitStatusListener(drillbitStatusListener);

      myThread.setName(originalThreadName);

    }
  }

  /**
   * Utility method to check where we are in a no terminal state.
   *
   * @return Whether or not execution should continue.
   */
  private boolean shouldContinue() {
    return !isCompleted() && FragmentState.CANCELLATION_REQUESTED != fragmentState.get();
  }

  /**
   * Returns true if the fragment is in a terminal state
   *
   * @return Whether this state is in a terminal state.
   */
  private boolean isCompleted() {
    return isTerminal(fragmentState.get());
  }

  private void sendFinalState() {
    final FragmentState outcome = fragmentState.get();
    if (outcome == FragmentState.FAILED) {
      final FragmentHandle handle = getContext().getHandle();
      final UserException uex = UserException.systemError(deferredException.getAndClear())
          .addIdentity(getContext().getIdentity())
          .addContext("Fragment", handle.getMajorFragmentId() + ":" + handle.getMinorFragmentId())
          .build();
      listener.fail(fragmentContext.getHandle(), uex);
    } else {
      listener.stateChanged(fragmentContext.getHandle(), outcome);
    }
  }


  private void closeOutResources() {

    // first close the operators and release all memory.
    try {
      // Say executor was cancelled before setup. Now when executor actually runs, root is not initialized, but this
      // method is called in finally. So root can be null.
      if (root != null) {
        root.close();
      }
    } catch (final Exception e) {
      fail(e);
    }

    // then close the fragment context.
    fragmentContext.close();

  }

  private void warnStateChange(final FragmentState current, final FragmentState target) {
    logger.warn("Ignoring unexpected state transition {} => {}.", current.name(), target.name());
  }

  private void errorStateChange(final FragmentState current, final FragmentState target) {
    final String msg = "Invalid state transition %s => %s.";
    throw new StateTransitionException(String.format(msg, current.name(), target.name()));
  }

  private synchronized boolean updateState(FragmentState target) {
    final FragmentHandle handle = fragmentContext.getHandle();
    final FragmentState current = fragmentState.get();
    logger.info(fragmentName + ": State change requested from {} --> {} for ", current, target);
    switch (target) {
    case CANCELLATION_REQUESTED:
      switch (current) {
      case SENDING:
      case AWAITING_ALLOCATION:
      case RUNNING:
        fragmentState.set(target);
        listener.stateChanged(handle, target);
        return true;

      default:
        warnStateChange(current, target);
        return false;
      }

    case FINISHED:
      if(current == FragmentState.CANCELLATION_REQUESTED){
        target = FragmentState.CANCELLED;
      } else if (current == FragmentState.FAILED) {
        target = FragmentState.FAILED;
      }
      // fall-through
    case FAILED:
      if(!isTerminal(current)){
        fragmentState.set(target);
        // don't notify listener until we finalize this terminal state.
        return true;
      } else if (current == FragmentState.FAILED) {
        // no warn since we can call fail multiple times.
        return false;
      } else if (current == FragmentState.CANCELLED && target == FragmentState.FAILED) {
        fragmentState.set(FragmentState.FAILED);
        return true;
      }else{
        warnStateChange(current, target);
        return false;
      }

    case RUNNING:
      if(current == FragmentState.AWAITING_ALLOCATION){
        fragmentState.set(target);
        listener.stateChanged(handle, target);
        return true;
      }else{
        errorStateChange(current, target);
      }

      // these should never be requested.
    case CANCELLED:
    case SENDING:
    case AWAITING_ALLOCATION:
    default:
      errorStateChange(current, target);
    }

    // errorStateChange() throw should mean this is never executed
    throw new IllegalStateException();
  }

  private boolean isTerminal(final FragmentState state) {
    return state == FragmentState.CANCELLED
        || state == FragmentState.FAILED
        || state == FragmentState.FINISHED;
  }

  /**
   * Capture an exception and add store it. Update state to failed status (if not already there). Does not immediately
   * report status back to Foreman. Only the original thread can return status to the Foreman.
   *
   * @param excep
   *          The failure that occurred.
   */
  private void fail(final Throwable excep) {
    deferredException.addThrowable(excep);
    updateState(FragmentState.FAILED);
  }

  public FragmentContext getContext() {
    return fragmentContext;
  }

  private class ExecutorStateImpl implements ExecutorState {
    public boolean shouldContinue() {
      return FragmentExecutor.this.shouldContinue();
    }

    public void fail(final Throwable t) {
      FragmentExecutor.this.fail(t);
    }

    public boolean isFailed() {
      return fragmentState.get() == FragmentState.FAILED;
    }
    public Throwable getFailureCause(){
      return deferredException.getException();
    }
  }

  private class FragmentDrillbitStatusListener implements DrillbitStatusListener {
    @Override
    public void drillbitRegistered(final Set<CoordinationProtos.DrillbitEndpoint> registeredDrillbits) {
    }

    @Override
    public void drillbitUnregistered(final Set<CoordinationProtos.DrillbitEndpoint> unregisteredDrillbits) {
      // if the defunct Drillbit was running our Foreman, then cancel the query
      final DrillbitEndpoint foremanEndpoint = FragmentExecutor.this.fragmentContext.getForemanEndpoint();
      if (unregisteredDrillbits.contains(foremanEndpoint)) {
        logger.warn("Foreman {} no longer active.  Cancelling fragment {}.",
                    foremanEndpoint.getAddress(),
                    QueryIdHelper.getQueryIdentifier(fragmentContext.getHandle()));
        FragmentExecutor.this.cancel();
      }
    }
  }
}


File: exec/java-exec/src/test/java/org/apache/drill/exec/store/parquet/ParquetResultListener.java
/*******************************************************************************
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 ******************************************************************************/
package org.apache.drill.exec.store.parquet;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.io.UnsupportedEncodingException;
import java.util.Arrays;
import java.util.HashMap;

import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.common.types.TypeProtos;
import org.apache.drill.exec.exception.SchemaChangeException;
import org.apache.drill.exec.memory.BufferAllocator;
import org.apache.drill.exec.proto.UserBitShared;
import org.apache.drill.exec.proto.UserBitShared.QueryResult.QueryState;
import org.apache.drill.exec.record.RecordBatchLoader;
import org.apache.drill.exec.record.VectorWrapper;
import org.apache.drill.exec.rpc.RpcException;
import org.apache.drill.exec.rpc.user.ConnectionThrottle;
import org.apache.drill.exec.rpc.user.QueryDataBatch;
import org.apache.drill.exec.rpc.user.UserResultsListener;
import org.apache.drill.exec.vector.ValueVector;

import com.google.common.base.Strings;
import com.google.common.util.concurrent.SettableFuture;

public class ParquetResultListener implements UserResultsListener {
  private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(ParquetResultListener.class);

  private final SettableFuture<Void> future = SettableFuture.create();
  int count = 0;
  int totalRecords;

  private boolean testValues;
  private final BufferAllocator allocator;

  int batchCounter = 1;
  private final HashMap<String, Integer> valuesChecked = new HashMap<>();
  private final ParquetTestProperties props;

  ParquetResultListener(BufferAllocator allocator, ParquetTestProperties props,
      int numberOfTimesRead, boolean testValues) {
    this.allocator = allocator;
    this.props = props;
    this.totalRecords = props.recordsPerRowGroup * props.numberRowGroups * numberOfTimesRead;
    this.testValues = testValues;
  }

  @Override
  public void submissionFailed(UserException ex) {
    logger.error("Submission failed.", ex);
    future.setException(ex);
  }

  @Override
  public void queryCompleted(QueryState state) {
    checkLastChunk();
  }

  private <T> void assertField(ValueVector valueVector, int index,
      TypeProtos.MinorType expectedMinorType, Object value, String name) {
    assertField(valueVector, index, expectedMinorType, value, name, 0);
  }

  @SuppressWarnings("unchecked")
  private <T> void assertField(ValueVector valueVector, int index,
      TypeProtos.MinorType expectedMinorType, T value, String name, int parentFieldId) {

    if (expectedMinorType == TypeProtos.MinorType.MAP) {
      return;
    }

    final T val;
    try {
      val = (T) valueVector.getAccessor().getObject(index);
    } catch (Throwable ex) {
      throw ex;
    }

    if (val instanceof byte[]) {
      assertTrue(Arrays.equals((byte[]) value, (byte[]) val));
    } else {
      assertEquals(value, val);
    }
  }

  @Override
  synchronized public void dataArrived(QueryDataBatch result, ConnectionThrottle throttle) {
    logger.debug("result arrived in test batch listener.");
    int columnValCounter = 0;
    FieldInfo currentField;
    count += result.getHeader().getRowCount();
    boolean schemaChanged = false;
    final RecordBatchLoader batchLoader = new RecordBatchLoader(allocator);
    try {
      schemaChanged = batchLoader.load(result.getHeader().getDef(), result.getData());
      // TODO:  Clean:  DRILL-2933:  That load(...) no longer throws
      // SchemaChangeException, so check/clean catch clause below.
    } catch (SchemaChangeException e) {
      throw new RuntimeException(e);
    }

    // used to make sure each vector in the batch has the same number of records
    int valueCount = batchLoader.getRecordCount();

    // print headers.
    if (schemaChanged) {
    } // do not believe any change is needed for when the schema changes, with the current mock scan use case

    for (final VectorWrapper vw : batchLoader) {
      final ValueVector vv = vw.getValueVector();
      currentField = props.fields.get(vv.getField().getPath().getRootSegment().getPath());
      if (!valuesChecked.containsKey(vv.getField().getPath().getRootSegment().getPath())) {
        valuesChecked.put(vv.getField().getPath().getRootSegment().getPath(), 0);
        columnValCounter = 0;
      } else {
        columnValCounter = valuesChecked.get(vv.getField().getPath().getRootSegment().getPath());
      }
      printColumnMajor(vv);

      if (testValues) {
        for (int j = 0; j < vv.getAccessor().getValueCount(); j++) {
          assertField(vv, j, currentField.type,
              currentField.values[columnValCounter % 3], currentField.name + "/");
          columnValCounter++;
        }
      } else {
        columnValCounter += vv.getAccessor().getValueCount();
      }

      valuesChecked.remove(vv.getField().getPath().getRootSegment().getPath());
      assertEquals("Mismatched value count for vectors in the same batch.", valueCount, vv.getAccessor().getValueCount());
      valuesChecked.put(vv.getField().getPath().getRootSegment().getPath(), columnValCounter);
    }

    if (ParquetRecordReaderTest.VERBOSE_DEBUG){
      printRowMajor(batchLoader);
    }
    batchCounter++;

    batchLoader.clear();
    result.release();
  }

  private void checkLastChunk() {
    int recordsInBatch = -1;
    // ensure the right number of columns was returned, especially important to ensure selective column read is working
    if (testValues) {
      assertEquals( "Unexpected number of output columns from parquet scan.", props.fields.keySet().size(), valuesChecked.keySet().size() );
    }
    for (final String s : valuesChecked.keySet()) {
      try {
        if (recordsInBatch == -1 ){
          recordsInBatch = valuesChecked.get(s);
        } else {
          assertEquals("Mismatched record counts in vectors.", recordsInBatch, valuesChecked.get(s).intValue());
        }
        assertEquals("Record count incorrect for column: " + s, totalRecords, (long) valuesChecked.get(s));
      } catch (AssertionError e) {
        submissionFailed(UserException.systemError(e).build());
      }
    }

    assertTrue(valuesChecked.keySet().size() > 0);
    future.set(null);
  }

  public void printColumnMajor(ValueVector vv) {
    if (ParquetRecordReaderTest.VERBOSE_DEBUG){
      System.out.println("\n" + vv.getField().getAsSchemaPath().getRootSegment().getPath());
    }
    for (int j = 0; j < vv.getAccessor().getValueCount(); j++) {
      if (ParquetRecordReaderTest.VERBOSE_DEBUG){
        Object o = vv.getAccessor().getObject(j);
        if (o instanceof byte[]) {
          try {
            o = new String((byte[])o, "UTF-8");
          } catch (UnsupportedEncodingException e) {
            throw new RuntimeException(e);
          }
        }
        System.out.print(Strings.padStart(o + "", 20, ' ') + " ");
        System.out.print(", " + (j % 25 == 0 ? "\n batch:" + batchCounter + " v:" + j + " - " : ""));
      }
    }
    if (ParquetRecordReaderTest.VERBOSE_DEBUG) {
      System.out.println("\n" + vv.getAccessor().getValueCount());
    }
  }

  public void printRowMajor(RecordBatchLoader batchLoader) {
    for (int i = 0; i < batchLoader.getRecordCount(); i++) {
      if (i % 50 == 0) {
        System.out.println();
        for (VectorWrapper vw : batchLoader) {
          ValueVector v = vw.getValueVector();
          System.out.print(Strings.padStart(v.getField().getAsSchemaPath().getRootSegment().getPath(), 20, ' ') + " ");

        }
        System.out.println();
        System.out.println();
      }

      for (final VectorWrapper vw : batchLoader) {
        final ValueVector v = vw.getValueVector();
        Object o = v.getAccessor().getObject(i);
        if (o instanceof byte[]) {
          try {
            // TODO - in the dictionary read error test there is some data that does not look correct
            // the output of our reader matches the values of the parquet-mr cat/head tools (no full comparison was made,
            // but from a quick check of a few values it looked consistent
            // this might have gotten corrupted by pig somehow, or maybe this is just how the data is supposed ot look
            // TODO - check this!!
//              for (int k = 0; k < ((byte[])o).length; k++ ) {
//                // check that the value at each position is a valid single character ascii value.
//
//                if (((byte[])o)[k] > 128) {
//                  System.out.println("batch: " + batchCounter + " record: " + recordCount);
//                }
//              }
            o = new String((byte[])o, "UTF-8");
          } catch (UnsupportedEncodingException e) {
            throw new RuntimeException(e);
          }
        }
        System.out.print(Strings.padStart(o + "", 20, ' ') + " ");
      }
      System.out.println();
    }
  }

  public void getResults() throws RpcException {
    try {
      future.get();
    } catch(Throwable t) {
      throw RpcException.mapException(t);
    }
  }

  @Override
  public void queryIdArrived(UserBitShared.QueryId queryId) {
  }
}
