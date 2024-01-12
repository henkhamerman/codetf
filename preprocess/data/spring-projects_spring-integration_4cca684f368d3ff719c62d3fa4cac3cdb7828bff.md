Refactoring Types: ['Move Class']
c/main/java/org/springframework/integration/codec/kryo/PojoCodec.java
/*
 * Copyright 2015 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.integration.codec.kryo;

import java.util.Collections;
import java.util.List;

import org.springframework.util.CollectionUtils;

import com.esotericsoftware.kryo.Kryo;
import com.esotericsoftware.kryo.io.Input;
import com.esotericsoftware.kryo.io.Output;

/**
 * Kryo Codec that can encode and decode arbitrary types. Classes and associated
 * {@link com.esotericsoftware.kryo.Serializer}s may be registered via
 * {@link KryoRegistrar}s.
 *
 * @author David Turanski
 * @since 4.2
 */
public class PojoCodec extends AbstractKryoCodec {

	private final CompositeKryoRegistrar kryoRegistrar;

	private final boolean useReferences;

	public PojoCodec() {
		this.kryoRegistrar = null;
		this.useReferences = true;
	}

	/**
	 * Create an instance with a single KryoRegistrar.
	 * @param kryoRegistrar the registrar.
	 */
	public PojoCodec(KryoRegistrar kryoRegistrar) {
		this(kryoRegistrar != null ? Collections.singletonList(kryoRegistrar) : null, true);
	}

	/**
	 * Create an instance with zero to many KryoRegistrars.
	 * @param kryoRegistrars a list KryoRegistrars.
	 */
	public PojoCodec(List<KryoRegistrar> kryoRegistrars) {
		this.kryoRegistrar = CollectionUtils.isEmpty(kryoRegistrars) ? null :
				new CompositeKryoRegistrar(kryoRegistrars);
		this.useReferences = true;
	}

	/**
	 * Create an instance with a single KryoRegistrar.
	 * @param kryoRegistrar the registrar.
	 * @param useReferences set to false if references are not required (if the object graph is known to be acyclical).
	 * The default is 'true' which is less performant but more flexible.
	 */
	public PojoCodec(KryoRegistrar kryoRegistrar, boolean useReferences) {
		this(kryoRegistrar != null ? Collections.singletonList(kryoRegistrar) : null, useReferences);
	}

	/**
	 * Create an instance with zero to many KryoRegistrars.
	 * @param kryoRegistrars a list KryoRegistrars.
	 * @param useReferences set to false if references are not required (if the object graph is known to be acyclical).
	 * The default is 'true' which is less performant but more flexible.
	 */
	public PojoCodec(List<KryoRegistrar> kryoRegistrars, boolean useReferences) {
		this.kryoRegistrar = CollectionUtils.isEmpty(kryoRegistrars) ? null :
				new CompositeKryoRegistrar(kryoRegistrars);
		this.useReferences = useReferences;
	}

	@Override
	protected void doEncode(Kryo kryo, Object object, Output output) {
		kryo.writeObject(output, object);
	}

	@Override
	protected <T> T doDecode(Kryo kryo, Input input, Class<T> type) {
		return kryo.readObject(input, type);
	}

	@Override
	protected void configureKryoInstance(Kryo kryo) {
		if (this.kryoRegistrar != null) {
			this.kryoRegistrar.registerTypes(kryo);
		}
		kryo.setReferences(this.useReferences);
	}

}


File: spring-integration-test/src/main/java/org/springframework/integration/test/rule/Log4jLevelAdjuster.java
/*
 * Copyright 2015 the original author or authors.
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
package org.springframework.integration.test.rule;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.log4j.Level;
import org.apache.log4j.LogManager;
import org.junit.rules.MethodRule;
import org.junit.runners.model.FrameworkMethod;
import org.junit.runners.model.Statement;

/**
 * A JUnit method &#064;Rule that changes the logger level for a set of classes
 * or packages
 * while a test method is running. Useful for performance or scalability tests
 * where we don't want to generate a large log in a tight inner loop, or
 * enabling debug logging for a test case.
 *
 * @author Dave Syer
 * @author Gary Russell
 *
 */
public class Log4jLevelAdjuster implements MethodRule {

	private static final Log logger = LogFactory.getLog(Log4jLevelAdjuster.class);

	private final Class<?>[] classes;

	private final Level level;

	private final String[] categories;

	public Log4jLevelAdjuster(Level level, Class<?>... classes) {
		this.level = level;
		this.classes = classes;
		this.categories = new String[0];
	}

	public Log4jLevelAdjuster(Level level, String... categories) {
		this.level = level;
		this.classes = new Class[0];
		this.categories = categories;
	}

	@Override
	public Statement apply(final Statement base, FrameworkMethod method, Object target) {
		return new Statement() {
			@Override
			public void evaluate() throws Throwable {
				logger.debug("Overriding log level setting for: " + Arrays.asList(classes));
				Map<Class<?>, Level> oldLevels = new HashMap<Class<?>, Level>();
				for (Class<?> cls : classes) {
					oldLevels.put(cls, LogManager.getLogger(cls).getEffectiveLevel());
					LogManager.getLogger(cls).setLevel(level);
				}
				Map<String, Level> oldCatLevels = new HashMap<String, Level>();
				for (String category : categories) {
					oldCatLevels.put(category, LogManager.getLogger(category).getEffectiveLevel());
					LogManager.getLogger(category).setLevel(level);
				}
				try {
					base.evaluate();
				}
				finally {
					logger.debug("Restoring log level setting for: " + Arrays.asList(classes) + " and "
							+ Arrays.asList(categories));
					// raw Class type used to avoid http://bugs.sun.com/view_bug.do?bug_id=6682380
					for (@SuppressWarnings("rawtypes") Class cls : classes) {
						LogManager.getLogger(cls).setLevel(oldLevels.get(cls));
					}
					for (String category : categories) {
						LogManager.getLogger(category).setLevel(oldCatLevels.get(category));
					}
				}
			}
		};
	}

}
