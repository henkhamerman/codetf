Refactoring Types: ['Move Method', 'Move Attribute']
rackspacecloud/blueflood/cache/MetadataCacheIntegrationTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.cache;

import com.google.common.base.Supplier;
import com.google.common.collect.HashBasedTable;
import com.google.common.collect.Maps;
import com.google.common.collect.Table;
import com.google.common.collect.Tables;
import com.rackspacecloud.blueflood.io.AstyanaxMetadataIO;
import com.rackspacecloud.blueflood.io.MetadataIO;
import com.rackspacecloud.blueflood.service.Configuration;
import com.rackspacecloud.blueflood.service.CoreConfig;
import com.rackspacecloud.blueflood.types.Locator;
import com.rackspacecloud.blueflood.io.IntegrationTestBase;
import com.rackspacecloud.blueflood.types.MetricMetadata;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.junit.Assert;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;
import com.rackspacecloud.blueflood.utils.InMemoryMetadataIO;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.TimeUnit;

@RunWith(Parameterized.class)
public class MetadataCacheIntegrationTest extends IntegrationTestBase {

    private final MetadataIO io;
    
    public MetadataCacheIntegrationTest(MetadataIO io) {
        this.io = io;
    }

    @Override
    public void setUp() throws Exception {
        super.setUp();
        
        // equivalent of database truncate.
        if (io instanceof InMemoryMetadataIO) {
            ((InMemoryMetadataIO)io).backingTable.clear();
        }
    }
    
    @Test
    public void testPut() throws Exception {
        assertNumberOfRows("metrics_metadata", 0);
        
        MetadataCache cache = MetadataCache.createLoadingCacheInstance(new TimeValue(5, TimeUnit.MINUTES), 1);
        cache.setIO(io);
        Locator loc1 = Locator.createLocatorFromPathComponents("acOne", "ent", "chk", "mz", "met");
        Locator loc2 = Locator.createLocatorFromPathComponents("acTwo", "ent", "chk", "mz", "met");
        cache.put(loc1, "metaA", "some string");
        cache.put(loc1, "metaB", "fooz");
        cache.put(loc1, "metaC", "some other string");

        if (io instanceof AstyanaxMetadataIO)
            assertNumberOfRows("metrics_metadata", 1);
        else
            Assert.assertEquals(1, io.getNumberOfRowsTest());
        
        cache.put(loc2, "metaA", "hello");
        
        if (io instanceof AstyanaxMetadataIO)
            assertNumberOfRows("metrics_metadata", 2);
        else
            Assert.assertEquals(2, io.getNumberOfRowsTest());
    }


    @Test
    public void testGetNull() throws Exception {
        Locator loc1 = Locator.createLocatorFromPathComponents("acOne", "ent", "chk", "mz", "met");
        MetadataCache cache1 = MetadataCache.createLoadingCacheInstance(new TimeValue(5, TimeUnit.MINUTES), 1);
        cache1.setIO(io);
        Assert.assertNull(cache1.get(loc1, "foo"));
        Assert.assertNull(cache1.get(loc1, "foo"));
    }

    @Test
    public void testCollisions() throws Exception {
        Locator loc1 = Locator.createLocatorFromPathComponents("ac76PeGPSR", "entZ4MYd1W", "chJ0fvB5Ao", "mzord", "truncated"); // put unit of bytes
        Locator loc2 = Locator.createLocatorFromPathComponents("acTmPLSgfv", "enLctkAMeN", "chQwBe5YiE", "mzdfw", "cert_end_in"); // put type of I

        MetadataCache cache = MetadataCache.getInstance();
        cache.setIO(io);

        cache.put(loc1, MetricMetadata.UNIT.name().toLowerCase(), "foo");
        String str = cache.get(loc2, MetricMetadata.TYPE.name().toLowerCase(), String.class);
        Assert.assertEquals(str, null); // This catches a bug where the hashCode of these two cache keys is identical. (loc2 type == loc1 unit)
    }

    @Test
    public void testGet() throws Exception {
        Locator loc1 = Locator.createLocatorFromPathComponents("acOne", "ent", "chk", "mz", "met");
        MetadataCache cache1 = MetadataCache.createLoadingCacheInstance(new TimeValue(5, TimeUnit.MINUTES), 1);
        MetadataCache cache2 = MetadataCache.createLoadingCacheInstance(new TimeValue(5, TimeUnit.MINUTES), 1);
        
        cache1.setIO(io);
        cache2.setIO(io);
        
        // put in one, read in both.
        Class<String> expectedClass = String.class;
        String expected = "expected";

        String key = "metaA";
        cache1.put(loc1, key, expected);
        Assert.assertEquals(expected, cache1.get(loc1, key, expectedClass));
        Assert.assertEquals(expected, cache2.get(loc1, key, expectedClass));
        
        // update in one verify can only new value there.
        expected = "different expected";
        Assert.assertFalse(expected.equals(cache1.get(loc1, key, expectedClass)));
        cache1.put(loc1, key, expected);
        Assert.assertEquals(expected, cache1.get(loc1, key, expectedClass));
        
        // cache2 has old value that is unexpired. invalidate and read new value.
        Assert.assertFalse(expected.equals(cache2.get(loc1, key, expectedClass)));
        cache2.invalidate(loc1, key);
        Assert.assertEquals(expected, cache2.get(loc1, key, expectedClass));
        
        // re-read on invalidate.
        cache1.invalidate(loc1, key);
        Assert.assertFalse(cache1.containsKey(loc1, key));
        Assert.assertEquals(expected, cache1.get(loc1, key));
    }

    @Test
    public void testPutsAreNotDuplicative() throws Exception {
        Locator loc1 = Locator.createLocatorFromPathComponents("acOne", "ent", "chk", "mz", "met");
        MetadataCache cache1 = MetadataCache.createLoadingCacheInstance(new TimeValue(5, TimeUnit.MINUTES), 1);
        cache1.setIO(io);
        String key = "metaA";
        String v1 = new String("Hello");
        String v2 = new String("Hello");
        
        Assert.assertTrue(v1 != v2);
        Assert.assertEquals(v1, v2);
        Assert.assertTrue(cache1.put(loc1, key, v1));
        Assert.assertFalse(cache1.put(loc1, key, v2));
    }

    @Test
    public void testExpiration() throws Exception {
        Locator loc1 = Locator.createLocatorFromPathComponents("acOne", "ent.chk.mz.met");

        MetadataCache cache1 = MetadataCache.createLoadingCacheInstance(new TimeValue(5, TimeUnit.MINUTES), 1);
        MetadataCache cache2 = MetadataCache.createLoadingCacheInstance(new TimeValue(3, TimeUnit.SECONDS), 1);
        
        cache1.setIO(io);
        cache2.setIO(io);
        
        // update in 1, should read out of both.
        Class<String> expectedClass = String.class;
        String expected = "Hello";
        String key = "metaA";
        cache1.put(loc1, key, expected);
        Assert.assertEquals(expected, cache1.get(loc1, key, expectedClass));
        Assert.assertEquals(expected, cache2.get(loc1, key, expectedClass));
        
        // update cache1, but not cache2.
        expected = "Hello2";
        Assert.assertFalse(expected.equals(cache1.get(loc1, key, expectedClass)));
        cache1.put(loc1, key, expected);
        Assert.assertEquals(expected, cache1.get(loc1, key, expectedClass));
        // verify that 2 has old value.
        Assert.assertFalse(expected.equals(cache2.get(loc1, key, expectedClass)));
        
        // wait for expiration, then verify that new value is picked up.
        Thread.sleep(4000);
        Assert.assertEquals(expected, cache2.get(loc1, key, expectedClass));
    }

    @Test
    public void testTypedGet() throws Exception {
        MetadataCache cache = MetadataCache.createLoadingCacheInstance(new TimeValue(5, TimeUnit.MINUTES), 1);
        cache.setIO(io);
        Locator loc1 = Locator.createLocatorFromPathComponents("acOne", "ent", "chk", "mz", "met");
        String expectedString = "expected";
        
        cache.put(loc1, "str", expectedString);

        Assert.assertEquals(expectedString, cache.get(loc1, "str", String.class));
    }
    
    @Test
    public void testIOReplacement() throws Exception {
        
        // create the replacement IO.
        final MetadataIO mapIO = new InMemoryMetadataIO();
        final MetadataIO astIO = new AstyanaxMetadataIO();
        
        final MetadataCache cache = MetadataCache.createLoadingCacheInstance();
        cache.setIO(astIO);
        
        // DO NOT SET USING LOCAL IO INSTANCE!!!!
        
        // put an get a value with the old IO
        Locator loc = Locator.createLocatorFromPathComponents("io_replacment", "a", "b", "c");
        Assert.assertNull(cache.get(loc, "foo"));
        cache.put(loc, "foo", "bar");
        Assert.assertNotNull(cache.get(loc, "foo"));
        Assert.assertEquals("bar", cache.get(loc, "foo"));
        
        // replace the IO, ensure there is nothing there, do a put and get, verify they are different than from before.
        cache.setIO(mapIO);
        Assert.assertNull(cache.get(loc, "foo"));
        cache.put(loc, "foo", "baz");
        Assert.assertNotNull(cache.get(loc, "foo"));
        Assert.assertEquals("baz", cache.get(loc, "foo"));
        
        // put the old IO back. this should result in the old value being read from the cache.
        cache.setIO(astIO);
        Assert.assertEquals("bar", cache.get(loc, "foo"));
    }
    
    @Test
    public void testPersistence() throws Exception {
        MetadataCache cache0 = MetadataCache.createLoadingCacheInstance();
        cache0.setIO(new InMemoryMetadataIO());
        
        Locator l0 = Locator.createLocatorFromPathComponents("1", "a", "b");
        Locator l1 = Locator.createLocatorFromPathComponents("1", "c", "d");
        cache0.put(l0, "foo" , "l0_foo");
        cache0.put(l0, "bar", "l0_bar");
        cache0.put(l1, "zee", "zzzzz");
        
        File f = File.createTempFile("metadatacache_persistence", "txt");
        f.deleteOnExit();
        DataOutputStream out = new DataOutputStream(new FileOutputStream(f, false));
        
        cache0.save(out);
        out.close();
        
        MetadataCache cache1 = MetadataCache.createLoadingCacheInstance();
        cache1.setIO(new InMemoryMetadataIO());
        
        // verify nothing is in the cache.
        Assert.assertNull(cache1.get(l0, "foo"));
        Assert.assertNull(cache1.get(l0, "bar"));
        Assert.assertNull(cache1.get(l1, "zee"));
        
        // now load it.
        DataInputStream in = new DataInputStream(new FileInputStream(f));
        cache1.load(in);
        
        Assert.assertEquals("l0_foo", cache1.get(l0, "foo"));
        Assert.assertEquals("l0_bar", cache1.get(l0, "bar"));
        Assert.assertEquals("zzzzz", cache1.get(l1, "zee"));
    }
    

    @Parameterized.Parameters
    public static Collection<Object[]> getIOs() {
        List<Object[]> ios = new ArrayList<Object[]>();
        ios.add(new Object[] { new AstyanaxMetadataIO() });
        ios.add(new Object[] { new InMemoryMetadataIO() });
        return ios;
    }
}


File: blueflood-core/src/integration-test/java/com/rackspacecloud/blueflood/io/AstyanaxReaderIntegrationTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io;

import com.netflix.astyanax.serializers.AbstractSerializer;
import com.netflix.astyanax.serializers.BooleanSerializer;
import com.netflix.astyanax.serializers.StringSerializer;
import com.rackspacecloud.blueflood.cache.MetadataCache;
import com.rackspacecloud.blueflood.outputs.formats.MetricData;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.types.*;
import org.junit.Assert;
import org.junit.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class AstyanaxReaderIntegrationTest extends IntegrationTestBase {
    
    @Test
    public void testCanReadNumeric() throws Exception {
        Metric metric = writeMetric("long_metric", 74L);
        AstyanaxReader reader = AstyanaxReader.getInstance();

        final Locator locator = metric.getLocator();
        MetricData res = reader.getDatapointsForRange(locator, new Range(metric.getCollectionTime() - 100000,
                metric.getCollectionTime() + 100000), Granularity.FULL);
        int numPoints = res.getData().getPoints().size();
        Assert.assertTrue(numPoints > 0);

        // Test that the RangeBuilder is end-inclusive on the timestamp.
        res = reader.getDatapointsForRange(locator, new Range(metric.getCollectionTime() - 100000,
                metric.getCollectionTime()), Granularity.FULL);
        Assert.assertEquals(numPoints, res.getData().getPoints().size());
    }

    @Test
    public void testCanReadString() throws Exception {
        Metric metric = writeMetric("string_metric", "version 1.0.43342346");
        final Locator locator = metric.getLocator();

        AstyanaxReader reader = AstyanaxReader.getInstance();
        MetricData res = reader.getDatapointsForRange(locator, new Range(metric.getCollectionTime() - 100000,
                metric.getCollectionTime() + 100000), Granularity.FULL);
        Assert.assertTrue(res.getData().getPoints().size() > 0);
    }

    @Test
    public void testCanReadMetadata() throws Exception {
        Locator loc1 = Locator.createLocatorFromPathComponents("acOne", "ent", "ch", "mz", "met");
        AstyanaxWriter writer = AstyanaxWriter.getInstance();
        AstyanaxReader reader = AstyanaxReader.getInstance();
        writer.writeMetadataValue(loc1, "foo", "bar");
        Assert.assertEquals("bar", reader.getMetadataValues(loc1).get("foo").toString());
    }

    @Test
    public void testBatchedReads() throws Exception {
        // Write metrics and also persist their types.
        List<Locator> locatorList = new ArrayList<Locator>();
        Metric metric = writeMetric("string_metric", "version 1.0.43342346");
        MetadataCache.getInstance().put(metric.getLocator(), MetricMetadata.TYPE.name().toLowerCase(), DataType.STRING.toString());
        locatorList.add(metric.getLocator());

        metric = writeMetric("int_metric", 45);
        MetadataCache.getInstance().put(metric.getLocator(), MetricMetadata.TYPE.name().toLowerCase(), DataType.NUMERIC.toString());
        locatorList.add(metric.getLocator());

        metric = writeMetric("long_metric", 67L);
        MetadataCache.getInstance().put(metric.getLocator(), MetricMetadata.TYPE.name().toLowerCase(), DataType.NUMERIC.toString());
        locatorList.add(metric.getLocator());

        // Test batch reads
        AstyanaxReader reader = AstyanaxReader.getInstance();
        Map<Locator, MetricData> results = reader.getDatapointsForRange(locatorList, new Range(metric.getCollectionTime() - 100000,
                metric.getCollectionTime() + 100000), Granularity.FULL);

        Assert.assertEquals(locatorList.size(), results.size());

        for (Locator locator : locatorList) {
            MetricData metrics = results.get(locator);
            Assert.assertEquals(1, metrics.getData().getPoints().size());
        }
    }

    @Test
    public void testCanRetrieveNumericMetricsEvenIfNoMetaDataStored() throws Exception {
        // Write metrics and also persist their types.
        List<Locator> locatorList = new ArrayList<Locator>();
        Metric metric = writeMetric("string_metric", "version 1.0.43342346");
        MetadataCache.getInstance().put(metric.getLocator(), MetricMetadata.TYPE.name().toLowerCase(), DataType.STRING.toString());
        locatorList.add(metric.getLocator());

        metric = writeMetric("int_metric", 45);
        locatorList.add(metric.getLocator());

        metric = writeMetric("long_metric", 67L);
        locatorList.add(metric.getLocator());

        // Test batch reads
        AstyanaxReader reader = AstyanaxReader.getInstance();
        Map<Locator, MetricData> results = reader.getDatapointsForRange(locatorList, new Range(metric.getCollectionTime() - 100000,
                metric.getCollectionTime() + 100000), Granularity.FULL);

        Assert.assertEquals(locatorList.size(), results.size());

        for (Locator locator : locatorList) {
            MetricData metrics = results.get(locator);
            Assert.assertEquals(1, metrics.getData().getPoints().size());
        }
    }

    @Test
    public void test_StringMetrics_WithoutMetadata_NotRetrieved() throws Exception {
        List<Locator> locatorList = new ArrayList<Locator>();
        Metric metric = writeMetric("string_metric_1", "version 1.0.43342346");
        locatorList.add(metric.getLocator());

        // Test batch reads
        AstyanaxReader reader = AstyanaxReader.getInstance();
        Map<Locator, MetricData> results = reader.getDatapointsForRange(locatorList, new Range(metric.getCollectionTime() - 100000,
                metric.getCollectionTime() + 100000), Granularity.FULL);

        Assert.assertEquals(1, results.size());
        Assert.assertTrue(results.get(metric.getLocator()).getData().isEmpty());
    }

    @Test
    public void testNullRollupType_DoesNotReturn_StringOrBooleanSerializers() {
        AstyanaxReader reader = AstyanaxReader.getInstance();

        AbstractSerializer serializer = reader.serializerFor(null, DataType.INT, Granularity.MIN_5);

        Assert.assertTrue(serializer != null);
        Assert.assertFalse(serializer instanceof StringSerializer);
        Assert.assertFalse(serializer instanceof BooleanSerializer);
    }

    @Test
    public void testNullDataType_DoesNotReturn_StringOrBooleanSerializers() {
        AstyanaxReader reader = AstyanaxReader.getInstance();

        AbstractSerializer serializer = reader.serializerFor(null, null, Granularity.MIN_5);

        Assert.assertTrue(serializer != null);
        Assert.assertFalse(serializer instanceof StringSerializer);
        Assert.assertFalse(serializer instanceof BooleanSerializer);
    }
}


File: blueflood-core/src/integration-test/java/com/rackspacecloud/blueflood/io/AstyanaxWriterIntegrationTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io;

import com.rackspacecloud.blueflood.types.Locator;
import org.junit.Test;

public class AstyanaxWriterIntegrationTest extends IntegrationTestBase {

    @Test
    public void testEnsureStringMetricsDoNotEndUpInNumericSpace() throws Exception {
        assertNumberOfRows("metrics_string", 0);
        assertNumberOfRows("metrics_full", 0);
        assertNumberOfRows("metrics_locator", 0);

        writeMetric("string_metric", "This is a string test");
        
        assertNumberOfRows("metrics_string", 1);
        assertNumberOfRows("metrics_full", 0);
        assertNumberOfRows("metrics_locator", 0);
    }

    @Test
    public void testEnsureNumericMetricsDoNotEndUpInStringSpaces() throws Exception {
        assertNumberOfRows("metrics_string", 0);
        assertNumberOfRows("metrics_full", 0);
        assertNumberOfRows("metrics_locator", 0);

        writeMetric("long_metric", 64L);
        
        assertNumberOfRows("metrics_string", 0);
        assertNumberOfRows("metrics_full", 1);
        assertNumberOfRows("metrics_locator", 1);
    }

    @Test
    public void testMetadataGetsWritten() throws Exception {
        assertNumberOfRows("metrics_metadata", 0);

        Locator loc1 = Locator.createLocatorFromPathComponents("acONE", "entityId", "checkId", "mz", "metric");
        Locator loc2 = Locator.createLocatorFromPathComponents("acTWO", "entityId", "checkId", "mz", "metric");
        AstyanaxWriter writer = AstyanaxWriter.getInstance();

        // multiple cols on a single locator should produce a single row.
//        writer.writeMetadataValue(loc1, "a", new byte[]{1,2,3,4,5});
//        writer.writeMetadataValue(loc1, "b", new byte[]{6,7,8,9,0});
//        writer.writeMetadataValue(loc1, "c", new byte[]{11,22,33,44,55,66});
//        writer.writeMetadataValue(loc1, "d", new byte[]{-1,-2,-3,-4});
//        writer.writeMetadataValue(loc1, "e", new byte[]{1,2,3,4,5});
//        writer.writeMetadataValue(loc1, "f", new byte[]{1,2,3,4,5,6,7,8,9,0});
        writer.writeMetadataValue(loc1, "a", "Some1String");
        writer.writeMetadataValue(loc1, "b", "Some2String");
        writer.writeMetadataValue(loc1, "c", "Some3String");
        writer.writeMetadataValue(loc1, "d", "Some4String");
        writer.writeMetadataValue(loc1, "e", "Some5String");
        writer.writeMetadataValue(loc1, "f", "Some6String");

        assertNumberOfRows("metrics_metadata", 1);

        // new locator means new row.
        writer.writeMetadataValue(loc2, "a", "strrrrring");
        assertNumberOfRows("metrics_metadata", 2);
    }
}


File: blueflood-core/src/integration-test/java/com/rackspacecloud/blueflood/service/MetricsIntegrationTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.google.common.collect.Lists;
import com.netflix.astyanax.MutationBatch;
import com.netflix.astyanax.connectionpool.exceptions.ConnectionException;
import com.netflix.astyanax.model.ColumnFamily;
import com.rackspacecloud.blueflood.io.AstyanaxReader;
import com.rackspacecloud.blueflood.io.AstyanaxWriter;
import com.rackspacecloud.blueflood.io.CassandraModel;
import com.rackspacecloud.blueflood.io.IntegrationTestBase;
import com.rackspacecloud.blueflood.outputs.formats.MetricData;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.types.*;
import com.rackspacecloud.blueflood.utils.TimeValue;
import com.rackspacecloud.blueflood.utils.Util;
import org.junit.Assert;
import org.junit.Test;
import org.mockito.internal.util.reflection.Whitebox;

import java.io.IOException;
import java.util.*;
import java.util.concurrent.TimeUnit;

/**
 * Some of these tests here were horribly contrived to mimic behavior in Writer. The problem with this approach is that
 * when logic in Writer changes, these tests can break unless the logic is changed here too. */
public class MetricsIntegrationTest extends IntegrationTestBase {

    private static boolean areStringMetricsDropped = Configuration.getInstance().getBooleanProperty(CoreConfig.STRING_METRICS_DROPPED);
    // returns a collection all checks that were written at some point.
    // this was a lot cooler back when the slot changed with time.
    private Collection<Locator> writeLocatorsOnly(int hours) throws Exception {
        // duplicate the logic from Writer.writeFull() that inserts locator rows.
        final String tenantId = "ac" + randString(8);
        final List<Locator> locators = new ArrayList<Locator>();
        for (int i = 0; i < hours; i++) {
            locators.add(Locator.createLocatorFromPathComponents(tenantId, "test:locator:inserts:" + i));
        }

        AstyanaxTester at = new AstyanaxTester();
        MutationBatch mb = at.createMutationBatch();

        for (Locator locator : locators) {
            int shard = Util.computeShard(locator.toString());
            mb.withRow(at.getLocatorCF(), (long)shard)
                    .putColumn(locator, "", 100000);
        }
        mb.execute();

        return locators;
    }

    private void writeFullData(
            Locator locator,
            long baseMillis, 
            int hours,
            AstyanaxWriter writer) throws Exception {
        // insert something every minute for 48h
        for (int i = 0; i < 60 * hours; i++) {
            final long curMillis = baseMillis + i * 60000;
            List<Metric> metrics = new ArrayList<Metric>();
            metrics.add(getRandomIntMetric(locator, curMillis));
            writer.insertFull(metrics);
        }
    }

    @Test
    public void testLocatorsWritten() throws Exception {
        Collection<Locator> locators = writeLocatorsOnly(48);
        AstyanaxReader r = AstyanaxReader.getInstance();

        Set<String> actualLocators = new HashSet<String>();
        for (Locator locator : locators) {
            for (Locator databaseLocator : r.getLocatorsToRollup(Util.computeShard(locator.toString()))) {
                actualLocators.add(databaseLocator.toString());
            }
        }
        Assert.assertEquals(48, actualLocators.size());
    }

    @Test
    public void testRollupGenerationSimple() throws Exception {
        AstyanaxWriter writer = AstyanaxWriter.getInstance();
        AstyanaxReader reader = AstyanaxReader.getInstance();
        final long baseMillis = 1333635148000L; // some point during 5 April 2012.
        int hours = 48;
        final String acctId = "ac" + IntegrationTestBase.randString(8);
        final String metricName = "fooService,barServer," + randString(8);
        final long endMillis = baseMillis + (1000 * 60 * 60 * hours);
        final Locator locator = Locator.createLocatorFromPathComponents(acctId, metricName);

        writeFullData(locator, baseMillis, hours, writer);

        // FULL -> 5m
        ArrayList<SingleRollupWriteContext> writes = new ArrayList<SingleRollupWriteContext>();
        for (Range range : Range.getRangesToRollup(Granularity.FULL, baseMillis, endMillis)) {
            // each range should produce one average
            Points<SimpleNumber> input = reader.getDataToRoll(SimpleNumber.class, locator, range, CassandraModel.CF_METRICS_FULL);
            BasicRollup basicRollup = BasicRollup.buildRollupFromRawSamples(input);
            HistogramRollup histogramRollup = HistogramRollup.buildRollupFromRawSamples(input);

            writes.add(new SingleRollupWriteContext(basicRollup,
                    locator,
                    Granularity.FULL.coarser(),
                    CassandraModel.getColumnFamily(BasicRollup.class, Granularity.FULL.coarser()),
                    range.start));
            writes.add(new SingleRollupWriteContext(histogramRollup,
                    locator,
                    Granularity.FULL.MIN_5,
                    CassandraModel.getColumnFamily(HistogramRollup.class, Granularity.MIN_5),
                    range.start));
        }
        writer.insertRollups(writes);

        // 5m -> 20m
        writes.clear();

        for (Range range : Range.getRangesToRollup(Granularity.MIN_5, baseMillis, endMillis)) {
            Points<BasicRollup> input = reader.getDataToRoll(BasicRollup.class, locator, range,
                    CassandraModel.getColumnFamily(BasicRollup.class, Granularity.MIN_5));
            BasicRollup basicRollup = BasicRollup.buildRollupFromRollups(input);
            writes.add(new SingleRollupWriteContext(basicRollup,
                    locator,
                    Granularity.MIN_5.coarser(),
                    CassandraModel.getColumnFamily(BasicRollup.class, Granularity.MIN_5.coarser()),
                    range.start));

            Points<HistogramRollup> histInput = reader.getDataToRoll(HistogramRollup.class, locator, range,
                    CassandraModel.getColumnFamily(HistogramRollup.class, Granularity.MIN_5));
            HistogramRollup histogramRollup = HistogramRollup.buildRollupFromRollups(histInput);
            writes.add(new SingleRollupWriteContext(histogramRollup,
                    locator,
                    Granularity.MIN_20,
                    CassandraModel.getColumnFamily(HistogramRollup.class, Granularity.MIN_20),
                    range.start));
        }
        writer.insertRollups(writes);

        // 20m -> 60m
        writes.clear();
        for (Range range : Range.getRangesToRollup(Granularity.MIN_20, baseMillis, endMillis)) {
            Points<BasicRollup> input = reader.getDataToRoll(BasicRollup.class, locator, range,
                    CassandraModel.getColumnFamily(BasicRollup.class, Granularity.MIN_20));
            BasicRollup basicRollup = BasicRollup.buildRollupFromRollups(input);
            writes.add(new SingleRollupWriteContext(basicRollup,
                    locator,
                    Granularity.MIN_20.coarser(),
                    CassandraModel.getColumnFamily(BasicRollup.class, Granularity.MIN_20.coarser()),
                    range.start));

            Points<HistogramRollup> histInput = reader.getDataToRoll(HistogramRollup.class, locator, range,
                    CassandraModel.getColumnFamily(HistogramRollup.class, Granularity.MIN_5));
            HistogramRollup histogramRollup = HistogramRollup.buildRollupFromRollups(histInput);
            writes.add(new SingleRollupWriteContext(histogramRollup,
                    locator,
                    Granularity.MIN_60,
                    CassandraModel.getColumnFamily(HistogramRollup.class, Granularity.MIN_60),
                    range.start));
        }
        writer.insertRollups(writes);

        // 60m -> 240m
        writes.clear();
        for (Range range : Range.getRangesToRollup(Granularity.MIN_60, baseMillis, endMillis)) {
            Points<BasicRollup> input = reader.getDataToRoll(BasicRollup.class, locator, range,
                    CassandraModel.getColumnFamily(BasicRollup.class, Granularity.MIN_60));

            BasicRollup basicRollup = BasicRollup.buildRollupFromRollups(input);
            writes.add(new SingleRollupWriteContext(basicRollup,
                    locator,
                    Granularity.MIN_60.coarser(),
                    CassandraModel.getColumnFamily(BasicRollup.class, Granularity.MIN_60.coarser()),
                    range.start));

            Points<HistogramRollup> histInput = reader.getDataToRoll(HistogramRollup.class, locator, range,
                    CassandraModel.getColumnFamily(HistogramRollup.class, Granularity.MIN_5));
            HistogramRollup histogramRollup = HistogramRollup.buildRollupFromRollups(histInput);
            writes.add(new SingleRollupWriteContext(histogramRollup,
                    locator,
                    Granularity.MIN_240,
                    CassandraModel.getColumnFamily(HistogramRollup.class, Granularity.MIN_240),
                    range.start));
        }
        writer.insertRollups(writes);

        // 240m -> 1440m
        writes.clear();
        for (Range range : Range.getRangesToRollup(Granularity.MIN_240, baseMillis, endMillis)) {
            Points<BasicRollup> input = reader.getDataToRoll(BasicRollup.class, locator, range,
                    CassandraModel.getColumnFamily(BasicRollup.class, Granularity.MIN_240));
            BasicRollup basicRollup = BasicRollup.buildRollupFromRollups(input);
            writes.add(new SingleRollupWriteContext(basicRollup,
                    locator,
                    Granularity.MIN_240.coarser(),
                    CassandraModel.getColumnFamily(BasicRollup.class, Granularity.MIN_240.coarser()),
                    range.start));

            Points<HistogramRollup> histInput = reader.getDataToRoll(HistogramRollup.class, locator, range,
                    CassandraModel.getColumnFamily(HistogramRollup.class, Granularity.MIN_5));
            HistogramRollup histogramRollup = HistogramRollup.buildRollupFromRollups(histInput);
            writes.add(new SingleRollupWriteContext(histogramRollup,
                    locator,
                    Granularity.MIN_1440,
                    CassandraModel.getColumnFamily(HistogramRollup.class, Granularity.MIN_1440),
                    range.start));
        }
        writer.insertRollups(writes);

        // verify the number of points in 48h worth of rollups. 
        Range range = new Range(Granularity.MIN_1440.snapMillis(baseMillis), Granularity.MIN_1440.snapMillis(endMillis + Granularity.MIN_1440.milliseconds()));
        Points<BasicRollup> input = reader.getDataToRoll(BasicRollup.class, locator, range,
                CassandraModel.getColumnFamily(BasicRollup.class, Granularity.MIN_1440));
        BasicRollup basicRollup = BasicRollup.buildRollupFromRollups(input);
        Assert.assertEquals(60 * hours, basicRollup.getCount());

        Points<HistogramRollup> histInput = reader.getDataToRoll(HistogramRollup.class, locator, range,
                CassandraModel.getColumnFamily(HistogramRollup.class, Granularity.MIN_1440));
        HistogramRollup histogramRollup = HistogramRollup.buildRollupFromRollups(histInput);
        Assert.assertTrue(histogramRollup.getBins().size() > 0);
        Assert.assertTrue("Number of bins is " + histogramRollup.getBins().size(),
                histogramRollup.getBins().size() <= HistogramRollup.MAX_BIN_SIZE);
    }

    @Test
    public void testSimpleInsertAndGet() throws Exception {
        AstyanaxWriter writer = AstyanaxWriter.getInstance();
        AstyanaxReader reader = AstyanaxReader.getInstance();
        final long baseMillis = 1333635148000L; // some point during 5 April 2012.
        long lastMillis = baseMillis + (300 * 1000); // 300 seconds.
        final String acctId = "ac" + IntegrationTestBase.randString(8);
        final String metricName = "fooService,barServer," + randString(8);

        final Locator locator  = Locator.createLocatorFromPathComponents(acctId, metricName);

        Set<Long> expectedTimestamps = new HashSet<Long>();
        // insert something every 30s for 5 mins.
        for (int i = 0; i < 10; i++) {
            final long curMillis = baseMillis + (i * 30000); // 30 seconds later.
            expectedTimestamps.add(curMillis);
            List<Metric> metrics = new ArrayList<Metric>();
            metrics.add(getRandomIntMetric(locator, curMillis));
            writer.insertFull(metrics);
        }
        
        Set<Long> actualTimestamps = new HashSet<Long>();
        // get back the cols that were written from start to stop.

        Points<SimpleNumber> points = reader.getDataToRoll(SimpleNumber.class, locator, new Range(baseMillis, lastMillis),
                CassandraModel.getColumnFamily(BasicRollup.class, Granularity.FULL));
        actualTimestamps = points.getPoints().keySet();
        Assert.assertEquals(expectedTimestamps, actualTimestamps);
    }

    @Test
    //In this test, string metrics are configured to be always dropped. So they are not persisted at all.
    public void testStringMetricsIfSoConfiguredAreAlwaysDropped() throws Exception {
        Whitebox.setInternalState(AstyanaxWriter.getInstance(), "areStringMetricsDropped", true);

        AstyanaxWriter writer = AstyanaxWriter.getInstance();
        AstyanaxReader reader = AstyanaxReader.getInstance();
        final long baseMillis = 1333635148000L; // some point during 5 April 2012.
        long lastMillis = baseMillis + (300 * 1000); // 300 seconds.
        final String acctId = "ac" + IntegrationTestBase.randString(8);
        final String metricName = "fooService,barServer," + randString(8);

        final Locator locator  = Locator.createLocatorFromPathComponents(acctId, metricName);

        Set<Long> expectedTimestamps = new HashSet<Long>();
        // insert something every 30s for 5 mins.
        for (int i = 0; i < 10; i++) {
            final long curMillis = baseMillis + (i * 30000); // 30 seconds later.

            expectedTimestamps.add(curMillis);
            List<Metric> metrics = new ArrayList<Metric>();
            metrics.add(makeMetric(locator,curMillis,getRandomStringMetricValue()));
            writer.insertFull(metrics);
        }

        Set<Long> actualTimestamps = new HashSet<Long>();
        // get back the cols that were written from start to stop.

        MetricData data = reader.getDatapointsForRange(locator, new Range(baseMillis, lastMillis),Granularity.FULL);
        actualTimestamps = data.getData().getPoints().keySet();

        Assert.assertTrue(actualTimestamps.size() == 0);
    }

    @Test
    //In this test, string metrics are configured to be always dropped. So they are not persisted at all.
    public void testStringMetricsIfSoConfiguredAreNotDroppedForKeptTenantIds() throws Exception {
        Whitebox.setInternalState(AstyanaxWriter.getInstance(), "areStringMetricsDropped", true);

        AstyanaxWriter writer = AstyanaxWriter.getInstance();
        AstyanaxReader reader = AstyanaxReader.getInstance();
        final long baseMillis = 1333635148000L; // some point during 5 April 2012.
        long lastMillis = baseMillis + (300 * 1000); // 300 seconds.
        final String acctId = "ac" + IntegrationTestBase.randString(8);
        final String metricName = "fooService,barServer," + randString(8);

        final Locator locator  = Locator.createLocatorFromPathComponents(acctId, metricName);
        HashSet<String> keptTenants = new HashSet<String>();
        keptTenants.add(locator.getTenantId());

        Whitebox.setInternalState(AstyanaxWriter.getInstance(), "keptTenantIdsSet",keptTenants);

        Set<Long> expectedTimestamps = new HashSet<Long>();
        // insert something every 30s for 5 mins.
        for (int i = 0; i < 10; i++) {
            final long curMillis = baseMillis + (i * 30000); // 30 seconds later.

            expectedTimestamps.add(curMillis);
            List<Metric> metrics = new ArrayList<Metric>();
            metrics.add(makeMetric(locator,curMillis,getRandomStringMetricValue()));
            writer.insertFull(metrics);
        }

        Set<Long> actualTimestamps = new HashSet<Long>();
        // get back the cols that were written from start to stop.

        MetricData data = reader.getDatapointsForRange(locator, new Range(baseMillis, lastMillis),Granularity.FULL);
        actualTimestamps = data.getData().getPoints().keySet();

        Assert.assertEquals(expectedTimestamps, actualTimestamps);
    }

    @Test
    //In this test, string metrics are not configured to be dropped so they are persisted.
    public void testStringMetricsIfSoConfiguredArePersistedAsExpected() throws Exception {
        Whitebox.setInternalState(AstyanaxWriter.getInstance(), "areStringMetricsDropped", false);

        AstyanaxWriter writer = AstyanaxWriter.getInstance();
        AstyanaxReader reader = AstyanaxReader.getInstance();
        final long baseMillis = 1333635148000L; // some point during 5 April 2012.
        long lastMillis = baseMillis + (300 * 1000); // 300 seconds.
        final String acctId = "ac" + IntegrationTestBase.randString(8);
        final String metricName = "fooService,barServer," + randString(8);

        final Locator locator  = Locator.createLocatorFromPathComponents(acctId, metricName);

        Set<Long> expectedTimestamps = new HashSet<Long>();
        // insert something every 30s for 5 mins.
        for (int i = 0; i < 10; i++) {
            final long curMillis = baseMillis + (i * 30000); // 30 seconds later.

            expectedTimestamps.add(curMillis);
            List<Metric> metrics = new ArrayList<Metric>();
            metrics.add(makeMetric(locator,curMillis,getRandomStringMetricValue()));
            writer.insertFull(metrics);
        }

        Set<Long> actualTimestamps = new HashSet<Long>();
        // get back the cols that were written from start to stop.

        MetricData data = reader.getDatapointsForRange(locator, new Range(baseMillis, lastMillis),Granularity.FULL);
        actualTimestamps = data.getData().getPoints().keySet();

        Assert.assertEquals(expectedTimestamps, actualTimestamps);
    }

    @Test
    //In this test, we attempt to persist the same value of String Metric every single time. Only the first one is persisted.
    public void testStringMetricsWithSameValueAreNotPersisted() throws Exception {
        Whitebox.setInternalState(AstyanaxWriter.getInstance(), "areStringMetricsDropped", false);

        AstyanaxWriter writer = AstyanaxWriter.getInstance();
        AstyanaxReader reader = AstyanaxReader.getInstance();
        final long baseMillis = 1333635148000L; // some point during 5 April 2012.
        long lastMillis = baseMillis + (300 * 1000); // 300 seconds.
        final String acctId = "ac" + IntegrationTestBase.randString(8);
        final String metricName = "fooService,barServer," + randString(8);

        final Locator locator  = Locator.createLocatorFromPathComponents(acctId, metricName);
        String sameValue = getRandomStringMetricValue();
        Set<Long> expectedTimestamps = new HashSet<Long>();
        // insert something every 30s for 5 mins.
        //value remains the same
        for (int i = 0; i < 10; i++) {
            final long curMillis = baseMillis + (i * 30000); // 30 seconds later.

            expectedTimestamps.add(curMillis);
            List<Metric> metrics = new ArrayList<Metric>();
            metrics.add(makeMetric(locator,curMillis,sameValue));
            writer.insertFull(metrics);
        }

        Set<Long> actualTimestamps = new HashSet<Long>();
        // get back the cols that were written from start to stop.

        MetricData data = reader.getDatapointsForRange(locator, new Range(baseMillis, lastMillis),Granularity.FULL);
        actualTimestamps = data.getData().getPoints().keySet();

        Assert.assertTrue(actualTimestamps.size() == 1);
        for(long ts : actualTimestamps) {
            Assert.assertEquals(ts, baseMillis);
            break;
        }
    }

    @Test
    //In this case, we alternate between two values for a string metric. But since the string metric does not have the same value in two
    //consecutive writes, it's always persisted.
    public void testStringMetricsWithDifferentValuesArePersisted() throws Exception {
        AstyanaxWriter writer = AstyanaxWriter.getInstance();
        AstyanaxReader reader = AstyanaxReader.getInstance();
        final long baseMillis = 1333635148000L; // some point during 5 April 2012.
        long lastMillis = baseMillis + (300 * 1000); // 300 seconds.
        final String acctId = "ac" + IntegrationTestBase.randString(8);
        final String metricName = "fooService,barServer," + randString(8);

        final Locator locator  = Locator.createLocatorFromPathComponents(acctId, metricName);
        String firstValue = getRandomStringMetricValue();
        String secondValue = getRandomStringMetricValue();

        Set<Long> expectedTimestamps = new HashSet<Long>();
        // insert something every 30s for 5 mins.
        //string metric value is alternated.
        for (int i = 0; i < 10; i++) {
            final long curMillis = baseMillis + (i * 30000); // 30 seconds later.
            String value = null;
            if (i % 2 == 0) {
                value = firstValue;
            }
            else {
                value = secondValue;
            }
            expectedTimestamps.add(curMillis);
            List<Metric> metrics = new ArrayList<Metric>();
            metrics.add(makeMetric(locator, curMillis, value));
            writer.insertFull(metrics);
        }

        Set<Long> actualTimestamps = new HashSet<Long>();
        // get back the cols that were written from start to stop.

        MetricData data = reader.getDatapointsForRange(locator, new Range(baseMillis, lastMillis),Granularity.FULL);
        actualTimestamps = data.getData().getPoints().keySet();
        Assert.assertEquals(expectedTimestamps, actualTimestamps);
    }

    @Test
    //Numeric value is always persisted.
    public void testNumericMetricsAreAlwaysPersisted() throws Exception {
        AstyanaxWriter writer = AstyanaxWriter.getInstance();
        AstyanaxReader reader = AstyanaxReader.getInstance();
        final long baseMillis = 1333635148000L; // some point during 5 April 2012.
        long lastMillis = baseMillis + (300 * 1000); // 300 seconds.
        final String acctId = "ac" + IntegrationTestBase.randString(8);
        final String metricName = "fooService,barServer," + randString(8);

        final Locator locator  = Locator.createLocatorFromPathComponents(acctId, metricName);
        int sameValue = getRandomIntMetricValue();
        Set<Long> expectedTimestamps = new HashSet<Long>();
        // insert something every 30s for 5 mins.
        //value of numeric metric remains the same, still it is always persisted
        for (int i = 0; i < 10; i++) {
            final long curMillis = baseMillis + (i * 30000); // 30 seconds later.
            expectedTimestamps.add(curMillis);
            List<Metric> metrics = new ArrayList<Metric>();
            metrics.add(makeMetric(locator, curMillis,sameValue));
            writer.insertFull(metrics);
        }

        Set<Long> actualTimestamps = new HashSet<Long>();
        // get back the cols that were written from start to stop.

        Points<SimpleNumber> points = reader.getDataToRoll(SimpleNumber.class, locator, new Range(baseMillis, lastMillis),
                CassandraModel.getColumnFamily(BasicRollup.class, Granularity.FULL));
        actualTimestamps = points.getPoints().keySet();
        Assert.assertEquals(expectedTimestamps, actualTimestamps);
    }

    @Test
    //In this test, the same value is sent, and the metric is not persisted except for the first time.
    public void testBooleanMetricsWithSameValueAreNotPersisted() throws Exception {
        AstyanaxWriter writer = AstyanaxWriter.getInstance();
        AstyanaxReader reader = AstyanaxReader.getInstance();
        final long baseMillis = 1333635148000L; // some point during 5 April 2012.
        long lastMillis = baseMillis + (300 * 1000); // 300 seconds.
        final String acctId = "ac" + IntegrationTestBase.randString(8);
        final String metricName = "fooService,barServer," + randString(8);

        final Locator locator  = Locator.createLocatorFromPathComponents(acctId, metricName);
        boolean sameValue = true;
        Set<Long> expectedTimestamps = new HashSet<Long>();
        // insert something every 30s for 5 mins.
        for (int i = 0; i < 10; i++) {
            final long curMillis = baseMillis + (i * 30000); // 30 seconds later.
            expectedTimestamps.add(curMillis);
            List<Metric> metrics = new ArrayList<Metric>();
            metrics.add(makeMetric(locator,curMillis,sameValue));
            writer.insertFull(metrics);
        }

        Set<Long> actualTimestamps = new HashSet<Long>();
        // get back the cols that were written from start to stop.

        MetricData data = reader.getDatapointsForRange(locator, new Range(baseMillis, lastMillis),Granularity.FULL);
        actualTimestamps = data.getData().getPoints().keySet();

        Assert.assertTrue(actualTimestamps.size() == 1);
        for(long ts : actualTimestamps) {
            Assert.assertEquals(ts, baseMillis);
            break;
        }
    }

    @Test
    //In this test, we alternately persist true and false. All the boolean metrics are persisted.
    public void testBooleanMetricsWithDifferentValuesArePersisted() throws Exception {
        AstyanaxWriter writer = AstyanaxWriter.getInstance();
        AstyanaxReader reader = AstyanaxReader.getInstance();
        final long baseMillis = 1333635148000L; // some point during 5 April 2012.
        long lastMillis = baseMillis + (300 * 1000); // 300 seconds.
        final String acctId = "ac" + IntegrationTestBase.randString(8);
        final String metricName = "fooService,barServer," + randString(8);

        final Locator locator  = Locator.createLocatorFromPathComponents(acctId, metricName);

        Set<Long> expectedTimestamps = new HashSet<Long>();
        // insert something every 30s for 5 mins.
        for (int i = 0; i < 10; i++) {
            final long curMillis = baseMillis + (i * 30000); // 30 seconds later.
            boolean value;
            if (i % 2 == 0) {
                value = true;
            }
            else {
                value = false;
            }
            expectedTimestamps.add(curMillis);
            List<Metric> metrics = new ArrayList<Metric>();
            metrics.add(makeMetric(locator, curMillis, value));
            writer.insertFull(metrics);
        }

        Set<Long> actualTimestamps = new HashSet<Long>();
        // get back the cols that were written from start to stop.

        MetricData data = reader.getDatapointsForRange(locator, new Range(baseMillis, lastMillis),Granularity.FULL);
        actualTimestamps = data.getData().getPoints().keySet();
        Assert.assertEquals(expectedTimestamps, actualTimestamps);
    }

    @Test
    public void testConsecutiveWriteAndRead() throws ConnectionException, IOException {
        AstyanaxWriter writer = AstyanaxWriter.getInstance();
        AstyanaxReader reader = AstyanaxReader.getInstance();
        final long baseMillis = 1333635148000L;

        final Locator locator = Locator.createLocatorFromPathComponents("ac0001",
                "fooService,fooServer," + randString(8));

        final List<Metric> metrics = new ArrayList<Metric>();
        for (int i = 0; i < 100; i++) {
            final Metric metric = new Metric(locator, i, baseMillis + (i * 1000),
                    new TimeValue(1, TimeUnit.DAYS), "unknown");
            metrics.add(metric);
            writer.insertFull(metrics);
            metrics.clear();
        }

        int count = 0;
            ColumnFamily<Locator, Long> CF_metrics_full = CassandraModel.getColumnFamily(BasicRollup.class, Granularity.FULL);
        Points<SimpleNumber> points = reader.getDataToRoll(SimpleNumber.class, locator,
                new Range(baseMillis, baseMillis + 500000), CF_metrics_full);
        for (Map.Entry<Long, Points.Point<SimpleNumber>> data : points.getPoints().entrySet()) {
            Points.Point<SimpleNumber> point = data.getValue();
            Assert.assertEquals(count, point.getData().getValue());
            count++;
        }
    }

    @Test
    public void testShardStateWriteRead() throws Exception {
        final Collection<Integer> shards = Lists.newArrayList(0, 1, 2, 3, 4, 5, 6, 7, 8, 9);
        AstyanaxWriter writer = AstyanaxWriter.getInstance();

        // Simulate active or running state for all the slots for all granularities.
        for (int shard : shards) {
            Map<Granularity, Map<Integer, UpdateStamp>> allUpdates = new HashMap<Granularity, Map<Integer, UpdateStamp>>();
            for (Granularity granularity : Granularity.rollupGranularities()) {
                Map<Integer, UpdateStamp> updates = new HashMap<Integer, UpdateStamp>();
                for (int slot = 0; slot < granularity.numSlots(); slot++) {
                    updates.put(slot, new UpdateStamp(System.currentTimeMillis() - 10000, UpdateStamp.State.Active,
                            true));
                }
                allUpdates.put(granularity, updates);
            }
            writer.persistShardState(shard, allUpdates);
        }

        // Now simulate rolled up state for all the slots for all granularities.
        for (int shard : shards) {
            Map<Granularity, Map<Integer, UpdateStamp>> allUpdates = new HashMap<Granularity, Map<Integer, UpdateStamp>>();
            for (Granularity granularity : Granularity.rollupGranularities()) {
                Map<Integer, UpdateStamp> updates = new HashMap<Integer, UpdateStamp>();
                for (int slot = 0; slot < granularity.numSlots(); slot++) {
                    updates.put(slot, new UpdateStamp(System.currentTimeMillis(), UpdateStamp.State.Rolled,
                            true));
                }
                allUpdates.put(granularity, updates);
            }
            writer.persistShardState(shard, allUpdates);
        }

        // Now we would have the longest row for each shard because we filled all the slots.
        // Now test whether getShardState returns all the slots
        AstyanaxReader reader = AstyanaxReader.getInstance();
        ScheduleContext ctx = new ScheduleContext(System.currentTimeMillis(), shards);
        ShardStateManager shardStateManager = ctx.getShardStateManager();

        for (Integer shard : shards) {
            Collection<SlotState> slotStates = reader.getShardState(shard);
            for (SlotState slotState : slotStates) {
                shardStateManager.updateSlotOnRead(shard, slotState);
            }

            for (Granularity granularity : Granularity.rollupGranularities()) {
                ShardStateManager.SlotStateManager slotStateManager = shardStateManager.getSlotStateManager(shard, granularity);
                Assert.assertEquals(granularity.numSlots(), slotStateManager.getSlotStamps().size());
            }
        }
    }

    @Test
    public void testUpdateStampCoaelescing() throws Exception {
        final int shard = 24;
        final int slot = 16;
        AstyanaxWriter writer = AstyanaxWriter.getInstance();
        Map<Granularity, Map<Integer, UpdateStamp>> updates = new HashMap<Granularity, Map<Integer, UpdateStamp>>();
        Map<Integer, UpdateStamp> slotUpdates = new HashMap<Integer, UpdateStamp>();
        updates.put(Granularity.MIN_5, slotUpdates);
        
        long time = 1234;
        slotUpdates.put(slot, new UpdateStamp(time++, UpdateStamp.State.Active, true));
        writer.persistShardState(shard, updates);
        
        slotUpdates.put(slot, new UpdateStamp(time++, UpdateStamp.State.Rolled, true));
        writer.persistShardState(shard, updates);
        
        AstyanaxReader reader = AstyanaxReader.getInstance();
        ScheduleContext ctx = new ScheduleContext(System.currentTimeMillis(), Lists.newArrayList(shard));

        Collection<SlotState> slotStates = reader.getShardState(shard);
        for (SlotState slotState : slotStates) {
            ctx.getShardStateManager().updateSlotOnRead(shard, slotState);
        }

        ShardStateManager shardStateManager = ctx.getShardStateManager();
        ShardStateManager.SlotStateManager slotStateManager = shardStateManager.getSlotStateManager(shard, Granularity.MIN_5);

        Assert.assertNotNull(slotStateManager.getSlotStamps());
        Assert.assertEquals(UpdateStamp.State.Active, slotStateManager.getSlotStamps().get(slot).getState());
    }
}


File: blueflood-core/src/integration-test/java/com/rackspacecloud/blueflood/service/PreaggregatedMetricsIntegrationTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.google.common.collect.Lists;
import com.netflix.astyanax.model.ColumnFamily;
import com.rackspacecloud.blueflood.io.*;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.types.IMetric;
import com.rackspacecloud.blueflood.types.Locator;
import com.rackspacecloud.blueflood.types.Points;
import com.rackspacecloud.blueflood.types.PreaggregatedMetric;
import com.rackspacecloud.blueflood.types.Range;
import com.rackspacecloud.blueflood.types.TimerRollup;
import com.rackspacecloud.blueflood.utils.TimeValue;
import junit.framework.Assert;
import org.junit.Before;
import org.junit.Test;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

// todo: need an easy way to run this. It will require some plumbing changes to the project.
public class PreaggregatedMetricsIntegrationTest extends IntegrationTestBase {
    
    private TimerRollup simple;
    private static final TimeValue ttl = new TimeValue(24, TimeUnit.HOURS);
    private AstyanaxWriter writer = AstyanaxWriter.getInstance();
    private AstyanaxReader reader = AstyanaxReader.getInstance();
    private static final AtomicLong timestamp = new AtomicLong(10);
    
    @Before
    public void createFixtures() throws Exception {
        simple = new TimerRollup()
            .withSampleCount(1)
            .withSum(100d)
            .withCountPS(101d)
            .withAverage(102L)
            .withVariance(103d)
            .withMinValue(104)
            .withMaxValue(105)
            .withCount(106);
        simple.setPercentile("98th", 107);
        simple.setPercentile("99th", 110);
    }
    
    private static Points<TimerRollup> getTimerDataToRoll(AstyanaxReader reader, Locator locator, Range range, Granularity gran) throws IOException {
        ColumnFamily<Locator, Long> cf = CassandraModel.getColumnFamily(TimerRollup.class, gran);
        return reader.getDataToRoll(TimerRollup.class, locator, range, cf);
    }
    
    @Test
    public void testFullReadWrite() throws Exception {
        long ts = timestamp.incrementAndGet();
        Locator locator = Locator.createLocatorFromPathComponents("12345", "test", "full", "read", "put");
        IMetric metric = new PreaggregatedMetric(ts, locator, ttl, simple);

        writer.insertMetrics(Lists.newArrayList(metric), CassandraModel.CF_METRICS_PREAGGREGATED_FULL);
        
        Points<TimerRollup> points = PreaggregatedMetricsIntegrationTest.getTimerDataToRoll(reader, locator, new Range(ts, ts+1), Granularity.FULL);

        Assert.assertEquals(1, points.getPoints().size());
        Assert.assertEquals(metric.getMetricValue(), points.getPoints().get(ts).getData());
    }
    
    @Test
    public void testHigherGranReadWrite() throws Exception {
        final long ts = timestamp.incrementAndGet();
        final long rollupTs = ts + 100;
        Locator locator = Locator.createLocatorFromPathComponents("12345", "test", "rollup", "read", "put");
        IMetric metric = new PreaggregatedMetric(ts, locator, ttl, simple);
        
        writer.insertMetrics(Lists.newArrayList(metric), CassandraModel.CF_METRICS_PREAGGREGATED_FULL);
        
        // read the raw data.
        Points<TimerRollup> points = PreaggregatedMetricsIntegrationTest.getTimerDataToRoll(reader, locator, new Range(ts, ts+1), Granularity.FULL);
        Assert.assertEquals(1, points.getPoints().size());
        
        // create the rollup
        final TimerRollup rollup = TimerRollup.buildRollupFromTimerRollups(points);
        // should be the same as simple
        Assert.assertEquals(simple, rollup);
        
        // assemble it into points, but give it a new timestamp.
        points = new Points<TimerRollup>() {{
            add(new Point<TimerRollup>(rollupTs, rollup));
        }};
        List<IMetric> toWrite = toIMetricsList(locator, points);
        writer.insertMetrics(toWrite, CassandraModel.CF_METRICS_PREAGGREGATED_5M);
        
        // we should be able to read that now.
        Points<TimerRollup> rollups5m = reader.getDataToRoll(TimerRollup.class, locator, new Range(rollupTs, rollupTs+1), CassandraModel.CF_METRICS_PREAGGREGATED_5M);
        
        Assert.assertEquals(1, rollups5m.getPoints().size());
        
        TimerRollup rollup5m = rollups5m.getPoints().values().iterator().next().getData();
        // rollups should be identical since one is just a coarse rollup of the other.
        Assert.assertEquals(rollup, rollup5m);
    }
    
    @Test
    public void testTtlWorks() throws Exception {
        final long ts = timestamp.incrementAndGet();
        Locator locator = Locator.createLocatorFromPathComponents("12345", "test", "ttl");
        IMetric metric = new PreaggregatedMetric(ts, locator, new TimeValue(2, TimeUnit.SECONDS), simple);
        
        // put it
        writer.insertMetrics(Lists.newArrayList(metric), CassandraModel.CF_METRICS_PREAGGREGATED_FULL);
        
        // read it quickly.
        Points<TimerRollup> points = PreaggregatedMetricsIntegrationTest.getTimerDataToRoll(reader, locator, new Range(ts, ts+1), Granularity.FULL);
        Assert.assertEquals(1, points.getPoints().size());
        
        // let it time out.
        Thread.sleep(2000);
        
        // ensure it is gone.
        points = PreaggregatedMetricsIntegrationTest.getTimerDataToRoll(reader, locator, new Range(ts, ts+1), Granularity.FULL);
        Assert.assertEquals(0, points.getPoints().size());
    }
    
    private static List<IMetric> toIMetricsList(Locator locator, Points<TimerRollup> points) {
        List<IMetric> list = new ArrayList<IMetric>();
        for (Map.Entry<Long, Points.Point<TimerRollup>> entry : points.getPoints().entrySet()) {
            PreaggregatedMetric metric = new PreaggregatedMetric(entry.getKey(), locator, ttl, entry.getValue().getData());
            list.add(metric);
        }
        return list;
    }
    
}


File: blueflood-core/src/integration-test/java/com/rackspacecloud/blueflood/service/RollupRunnableIntegrationTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.rackspacecloud.blueflood.cache.MetadataCache;
import com.rackspacecloud.blueflood.concurrent.ThreadPoolBuilder;
import com.rackspacecloud.blueflood.io.*;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.types.*;
import com.rackspacecloud.blueflood.types.RollupType;
import com.rackspacecloud.blueflood.utils.TimeValue;
import junit.framework.Assert;
import org.junit.Test;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.concurrent.TimeUnit;

public class RollupRunnableIntegrationTest extends IntegrationTestBase {
    
    // gentle reader: remember, all column families are truncated between tests.
    
    private AstyanaxWriter writer = AstyanaxWriter.getInstance();
    private AstyanaxReader reader = AstyanaxReader.getInstance();
    
    private final Locator counterLocator = Locator.createLocatorFromPathComponents("runnabletest", "counter");
    private final Locator gaugeLocator = Locator.createLocatorFromPathComponents("runnabletest", "gauge");
    private final Locator timerLocator = Locator.createLocatorFromPathComponents("runnabletest", "timer");
    private final Locator setLocator = Locator.createLocatorFromPathComponents("runnabletest", "set");
    private final Locator normalLocator = Locator.createLocatorFromPathComponents("runnabletest", "just_some_data");
    
    private final Range range = new Range(0, 5 * 60 * 1000);
    
    private MetadataCache cache;

    @Override
    public void setUp() throws Exception {
        super.setUp(); // clears the schema.
        
        final TimeValue ttl = new TimeValue(24, TimeUnit.HOURS);
        
        // cache needs to be populated so rollups knows which serializer to use.
        cache = MetadataCache.createLoadingCacheInstance(ttl, 2);
        String cacheKey = MetricMetadata.ROLLUP_TYPE.name().toLowerCase();
        cache.put(counterLocator, cacheKey, RollupType.COUNTER.name());
        cache.put(gaugeLocator, cacheKey, RollupType.GAUGE.name());
        cache.put(timerLocator, cacheKey, RollupType.TIMER.name());
        cache.put(setLocator, cacheKey, RollupType.SET.name());
        // do not put normalLocator in the cache. it will constitute a miss.
        
        // put some full resolution data.
        Collection<IMetric> preaggregatedMetrics = new ArrayList<IMetric>();
        Collection<IMetric> normalMetrics = new ArrayList<IMetric>();
        
        for (int i = 0; i < 5; i++) {
            long time = i * 30000;
            IMetric metric;
            
            CounterRollup counter = new CounterRollup()
                    .withCount(i)
                    .withRate(i * i)
                    .withSampleCount(1);
            metric = new PreaggregatedMetric(time, counterLocator, ttl, counter);
            preaggregatedMetrics.add(metric);

            GaugeRollup gauge = new GaugeRollup()
                    .withLatest(time, i);
            metric = new PreaggregatedMetric(time, gaugeLocator, ttl, gauge);
            preaggregatedMetrics.add(metric);
            
            TimerRollup timer = new TimerRollup()
                    .withCount(5 * i + 1)
                    .withMaxValue(100 - i)
                    .withMinValue(100 - i - i)
                    .withAverage(i / 2)
                    .withCountPS((double)i).withSum(Double.valueOf(2 * i))
                    .withVariance((double) i / 2d);
            metric = new PreaggregatedMetric(time, timerLocator, ttl, timer);
            preaggregatedMetrics.add(metric);
            
            SetRollup rollup = new SetRollup().withObject(i);
            metric = new PreaggregatedMetric(time, setLocator, ttl, rollup);
            preaggregatedMetrics.add(metric);
            
            metric = new Metric(normalLocator, i, time, ttl, "centipawns");
            normalMetrics.add(metric);
        }
        
        writer.insertMetrics(preaggregatedMetrics, CassandraModel.CF_METRICS_PREAGGREGATED_FULL);
        writer.insertMetrics(normalMetrics, CassandraModel.CF_METRICS_FULL);
         
    }
    
    @Test
    public void testNormalMetrics() throws IOException {
        // full res has 5 samples.
        Assert.assertEquals(5, reader.getDataToRoll(SimpleNumber.class,
                                                    normalLocator,
                                                    range, 
                                                    CassandraModel.CF_METRICS_FULL).getPoints().size());
        
        // assert nothing in 5m for this locator.
        Assert.assertEquals(0, reader.getDataToRoll(BasicRollup.class,
                                                    normalLocator,
                                                    range, 
                                                    CassandraModel.CF_METRICS_5M).getPoints().size());
        
        RollupExecutionContext rec = new RollupExecutionContext(Thread.currentThread());
        SingleRollupReadContext rc = new SingleRollupReadContext(normalLocator, range, Granularity.MIN_5);
        RollupBatchWriter batchWriter = new RollupBatchWriter(new ThreadPoolBuilder().build(), rec);
        RollupRunnable rr = new RollupRunnable(rec, rc, batchWriter);
        rr.run();

        while (!rec.doneReading() && !rec.doneWriting()) {
            batchWriter.drainBatch();
            try {
                Thread.sleep(1000l);
            } catch (InterruptedException e) {
            }
        }

        // assert something in 5m for this locator.
        Assert.assertEquals(1, reader.getDataToRoll(BasicRollup.class,
                                                    normalLocator,
                                                    range,
                                                    CassandraModel.CF_METRICS_5M).getPoints().size());
    }
    
    @Test
    public void testCounterRollup() throws IOException {
        testRolledupMetric(counterLocator, CounterRollup.class, CounterRollup.class);
    }
    
    @Test
    public void testGaugeRollup() throws IOException {
        testRolledupMetric(gaugeLocator, GaugeRollup.class, GaugeRollup.class);
    }
    
    @Test
    public void testTimerRollup() throws IOException {
        testRolledupMetric(timerLocator, TimerRollup.class, TimerRollup.class);
    }
    
    @Test
    public void testSetRollup() throws IOException {
        testRolledupMetric(setLocator, SetRollup.class, SetRollup.class);
    }
    
    private void testRolledupMetric(Locator locator, Class fullResClass, Class rollupClass) throws IOException { 
        // full res has 5 samples.
        Assert.assertEquals(5, reader.getDataToRoll(fullResClass,
                                                    locator,
                                                    range, 
                                                    CassandraModel.CF_METRICS_PREAGGREGATED_FULL).getPoints().size());
        
        // assert nothing in 5m for this locator.
        Assert.assertEquals(0, reader.getDataToRoll(rollupClass,
                                                    locator,
                                                    range, 
                                                    CassandraModel.CF_METRICS_PREAGGREGATED_5M).getPoints().size());
        
        RollupExecutionContext rec = new RollupExecutionContext(Thread.currentThread());
        SingleRollupReadContext rc = new SingleRollupReadContext(locator, range, Granularity.MIN_5);
        RollupBatchWriter batchWriter = new RollupBatchWriter(new ThreadPoolBuilder().build(), rec);
        RollupRunnable rr = new RollupRunnable(rec, rc, batchWriter);
        rr.run();
        
        // assert something in 5m for this locator.
        while (!rec.doneReading() && !rec.doneWriting()) {
            batchWriter.drainBatch();
            try {
                Thread.sleep(1000l);
            } catch (InterruptedException e) {
            }
        }
        Assert.assertEquals(1, reader.getDataToRoll(rollupClass,
                                                    locator,
                                                    range,
                                                    CassandraModel.CF_METRICS_PREAGGREGATED_5M).getPoints().size());
    }
}


File: blueflood-core/src/integration-test/java/com/rackspacecloud/blueflood/service/RollupThreadpoolIntegrationTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.codahale.metrics.MetricRegistry;
import com.codahale.metrics.Timer;
import com.rackspacecloud.blueflood.io.AstyanaxReader;
import com.rackspacecloud.blueflood.io.AstyanaxWriter;
import com.rackspacecloud.blueflood.io.IntegrationTestBase;
import com.rackspacecloud.blueflood.types.Locator;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.rackspacecloud.blueflood.utils.Util;
import org.junit.Assert;
import org.junit.Test;

// this test used to measure rollups that were refused, but we don't care anymore. Not it makes sure that all rollups
// get executed.
public class RollupThreadpoolIntegrationTest extends IntegrationTestBase {
    private static final Integer threadsInRollupPool = 2;

    static {
        // run this test with a configuration so that threadpool queue size is artificially constrained smaller.
        System.setProperty("MAX_ROLLUP_READ_THREADS", threadsInRollupPool.toString());
        System.setProperty("MAX_ROLLUP_WRITE_THREADS", threadsInRollupPool.toString());
    }

    @Test
    // remember: this tests behavior, not performance.
    public void testManyLocators() throws Exception {
        Assert.assertEquals(Configuration.getInstance().getIntegerProperty(CoreConfig.MAX_ROLLUP_READ_THREADS), threadsInRollupPool.intValue());
        int shardToTest = 0;

        // I want to see what happens when RollupService.rollupExecutors gets too much work. It should never reject
        // work.
        long time = 1234;

        // now we need to put data that will generate an enormous amount of locators.
        AstyanaxWriter writer = AstyanaxWriter.getInstance();

        final int NUM_LOCATORS = 5000;
        int locatorCount = 0;
        while (locatorCount < NUM_LOCATORS) {
            // generate 100 random metrics.
            writer.insertFull(makeRandomIntMetrics(100));
            locatorCount += 100;
        }

        // lets see how many locators this generated. We want it to be a lot.

        int locatorsForTestShard = 0;
        for (Locator locator : AstyanaxReader.getInstance().getLocatorsToRollup(shardToTest)) {
            locatorsForTestShard++;
        }

        // Make sure number of locators for test shard is greater than number of rollup threads.
        // This is required so that rollups would be rejected for some locators.
        Assert.assertTrue(threadsInRollupPool < locatorsForTestShard);

        // great. now lets schedule those puppies.
        ScheduleContext ctx = new ScheduleContext(time, Util.parseShards(String.valueOf(shardToTest)));
        RollupService rollupService = new RollupService(ctx);
        rollupService.setKeepingServerTime(false);

        // indicate arrival (which we forced using Writer).
        ctx.update(time, shardToTest);

        // move time forward
        time += 500000;
        ctx.setCurrentTimeMillis(time);

        // start the rollups.
        Thread rollupThread = new Thread(rollupService, "rollup service test");
        rollupThread.start();

        Class.forName("com.rackspacecloud.blueflood.service.SingleRollupReadContext"); // Static initializer for the metric

        MetricRegistry registry = Metrics.getRegistry();
        Timer rollupsTimer = registry.getTimers().get(MetricRegistry.name(RollupService.class, "Rollup Execution Timer"));
//        Timer rollupsTimer = (Timer)registry.allMetrics().get(new MetricName("com.rackspacecloud.blueflood.service", "RollupService", "Rollup Execution Timer"));

        Assert.assertNotNull(rollupsTimer);

        // wait up to 120s for those rollups to finish.
        long start = System.currentTimeMillis();
        while (true) {
            try { Thread.currentThread().sleep(1000); } catch (Exception ex) { }
            if (rollupsTimer.getCount() >= locatorsForTestShard)
                break;
            Assert.assertTrue(String.format("rollups:%d", rollupsTimer.getCount()), System.currentTimeMillis() - start < 120000);
        }

        // make sure there were some that were delayed. If not, we need to increase NUM_LOCATORS.
        Assert.assertTrue(rollupsTimer.getCount() > 0);
    }
}


File: blueflood-core/src/integration-test/java/com/rackspacecloud/blueflood/service/ScheduleContextIntegrationTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import org.apache.curator.framework.recipes.locks.InterProcessMutex;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;
import org.mockito.internal.util.reflection.Whitebox;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collection;
import java.util.HashSet;
import java.util.Map;

public class ScheduleContextIntegrationTest {
    private static final Logger log = LoggerFactory.getLogger("tests");
    private ScheduleContext context;
    private ShardStateManager shardStateManager;
    private Collection<Integer> manageShards = new HashSet<Integer>();

    @Before
    public void setUp() {
        manageShards.add(1);
        manageShards.add(5);
        manageShards.add(7);
        manageShards.add(11);
        context = new ScheduleContext(1234, manageShards, Configuration.getInstance().getStringProperty(CoreConfig.ZOOKEEPER_CLUSTER));
        shardStateManager = context.getShardStateManager();
    }

    @Test
    public void testSetShardAddition() throws Exception {
        Assert.assertArrayEquals(manageShards.toArray(), shardStateManager.getManagedShards().toArray());
        manageShards.add(2);
        context.addShard(2);
        Assert.assertArrayEquals(manageShards.toArray(), shardStateManager.getManagedShards().toArray());
        final ZKBasedShardLockManager lockManager = (ZKBasedShardLockManager) Whitebox.getInternalState(context,
                "lockManager");

        Map<Integer, InterProcessMutex> lockObjects = (Map<Integer, InterProcessMutex>) Whitebox.getInternalState
                (lockManager, "locks");

        Assert.assertTrue(lockObjects.get(2) != null);  // assert that we have a lock object for shard "2"
    }

    @Test
    public void testSetShardDeletion() {
        Assert.assertArrayEquals(manageShards.toArray(), shardStateManager.getManagedShards().toArray());
        manageShards.remove(1);
        context.removeShard(1);
        Assert.assertArrayEquals(manageShards.toArray(), shardStateManager.getManagedShards().toArray());
        final ZKBasedShardLockManager lockManager = (ZKBasedShardLockManager) Whitebox.getInternalState(context,
                "lockManager");

        Map<Integer, InterProcessMutex> lockObjects = (Map<Integer, InterProcessMutex>) Whitebox.getInternalState
                (lockManager, "locks");

        Assert.assertTrue(lockObjects.get(1) == null);  // assert that we don't have a lock object for shard "1"
    }
}

File: blueflood-core/src/integration-test/java/com/rackspacecloud/blueflood/service/ShardStateIntegrationTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.rackspacecloud.blueflood.io.AstyanaxShardStateIO;
import com.rackspacecloud.blueflood.io.IntegrationTestBase;
import com.rackspacecloud.blueflood.io.ShardStateIO;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.rollup.SlotKey;
import com.rackspacecloud.blueflood.utils.Util;
import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;
import org.junit.After;
import org.junit.Assert;
import org.junit.Ignore;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;

import java.io.IOException;
import java.util.*;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

@Ignore
@RunWith(Parameterized.class)
public class ShardStateIntegrationTest extends IntegrationTestBase {
    
    private ShardStateIO io;
    
    public ShardStateIntegrationTest(ShardStateIO io) {
        this.io = io;    
    }

    @Test
    public void testSingleShardManager() {
        long time = 1234000L;
        Collection<Integer> shards = Lists.newArrayList(1, 2, 3, 4);
        ScheduleContext ctx = new ScheduleContext(time, shards);
        ShardStateWorker pull = new ShardStatePuller(shards, ctx.getShardStateManager(), this.io);
        ShardStateWorker push = new ShardStatePusher(shards, ctx.getShardStateManager(), this.io);
        
        for (long t = time; t < time + 10000000; t += 1000) {
            ctx.update(t + 0, 1);
            ctx.update(t + 2000, 2);
            ctx.update(t + 4000, 3);
            ctx.update(t + 6000, 4);
        }
        
        time += 10000000 + 7;
        ctx.setCurrentTimeMillis(time);
        push.performOperation();
        pull.performOperation();
        
        // the numbers we're testing against are the number of slots per granularity in 10000 seconds.
        for (Granularity g : Granularity.rollupGranularities()) {
            for (int shard : shards) {
                if (g == Granularity.MIN_5)
                    Assert.assertEquals(34, ctx.getSlotStamps(g, shard).size());
                else if (g == Granularity.MIN_20)
                    Assert.assertEquals(9, ctx.getSlotStamps(g, shard).size());
                else if (g == Granularity.MIN_60)
                    Assert.assertEquals(4, ctx.getSlotStamps(g, shard).size());
                else if (g == Granularity.MIN_240)
                    Assert.assertEquals(1, ctx.getSlotStamps(g, shard).size());
                else if (g == Granularity.MIN_1440)
                    Assert.assertEquals(1, ctx.getSlotStamps(g, shard).size());
            }
        }
    }

    @Test
    public void testRollupFailureForDelayedMetrics() {
        long time = 1234000L;
        Collection<Integer> managedShards = Lists.newArrayList(0);
        ScheduleContext ingestionCtx = new ScheduleContext(time, managedShards);
        ScheduleContext rollupCtx = new ScheduleContext(time, managedShards);
        // Shard workers for rollup ctx
        ShardStateWorker rollupPuller = new ShardStatePuller(managedShards, rollupCtx.getShardStateManager(), this.io);
        ShardStateWorker rollupPusher = new ShardStatePusher(managedShards, rollupCtx.getShardStateManager(), this.io);

        // Shard workers for ingest ctx
        ShardStateWorker ingestPuller = new ShardStatePuller(managedShards, ingestionCtx.getShardStateManager(), this.io);
        ShardStateWorker ingestPusher = new ShardStatePusher(managedShards, ingestionCtx.getShardStateManager(), this.io);

        ingestionCtx.update(time + 30000, 0);
        ingestPusher.performOperation(); // Shard state is persisted on ingestion host

        rollupPuller.performOperation(); // Shard state is read on rollup host
        rollupCtx.setCurrentTimeMillis(time + 600000);
        rollupCtx.scheduleSlotsOlderThan(300000);
        Assert.assertEquals(1, rollupCtx.getScheduledCount());

        // Simulate the hierarchical scheduling of slots
        int count = 0;
        while (rollupCtx.getScheduledCount() > 0) {
            SlotKey slot = rollupCtx.getNextScheduled();
            rollupCtx.clearFromRunning(slot);
            rollupCtx.scheduleSlotsOlderThan(300000);
            count += 1;
        }
        Assert.assertEquals(5, count); // 5 rollup grans should have been scheduled by now
        rollupPusher.performOperation();

        // Delayed metric is received on ingestion host
        ingestPuller.performOperation();
        ingestionCtx.update(time, 0);
        ingestPusher.performOperation();

        rollupPuller.performOperation();
        rollupCtx.scheduleSlotsOlderThan(300000);
        Assert.assertEquals(1, rollupCtx.getScheduledCount());

        // Simulate the hierarchical scheduling of slots
        count = 0;
        while (rollupCtx.getScheduledCount() > 0) {
            SlotKey slot = rollupCtx.getNextScheduled();
            rollupCtx.clearFromRunning(slot);
            rollupCtx.scheduleSlotsOlderThan(300000);
            count += 1;
        }
        Assert.assertEquals(5, count); // 5 rollup grans should have been scheduled by now
    }

    @Test
    public void testSetAllCoarserSlotsDirtyForFinerSlot() {
        // Tests that the correct coarser slots are set dirty for a finer slot which was seen out-of-order.
        // Prior to a bug fix, clearFromRunning would throw NPE because we were looking up coarser slots
        // based on the timestamp on the finer slot's UpdateStamp, not based on the relative courser slot from the finer slot
        long time = 1386823200000L;
        final Collection<Integer> shards = Lists.newArrayList(123);
        ScheduleContext ctxA = new ScheduleContext(time, shards);

        ctxA.update(time, 123);
        ShardStateManager.SlotStateManager slotStateManager20 = ctxA.getShardStateManager().getSlotStateManager(123, Granularity.MIN_20);

        UpdateStamp stamp  = slotStateManager20.getSlotStamps().get(518);
        stamp.setTimestamp(time + 3600000L); // add one hour
        ctxA.clearFromRunning(SlotKey.of(Granularity.MIN_20, 518, 123));
    }

    @Test
    public void testConcurrentShardManagers() {
        long time = 1234000L;
        // notice how they share shard 5.
        final int commonShard = 5;
        final Collection<Integer> shardsA = Lists.newArrayList(1, 2, 3, 4, commonShard);
        final Collection<Integer> shardsB = Lists.newArrayList(11, 22, 33, 44, commonShard);
        Collection<Integer> allShards = new ArrayList<Integer>() {{
            for (int i : Iterables.concat(shardsA, shardsB))
                add(i);
        }};
        
        ScheduleContext ctxA = new ScheduleContext(time, shardsA);
        ScheduleContext ctxB = new ScheduleContext(time, shardsB);

        ShardStateWorker pushA = new ShardStatePusher(allShards, ctxA.getShardStateManager(), this.io);
        ShardStateWorker pullA = new ShardStatePuller(allShards, ctxA.getShardStateManager(), this.io);
        ShardStateWorker pushB = new ShardStatePusher(allShards, ctxB.getShardStateManager(), this.io);
        ShardStateWorker pullB = new ShardStatePuller(allShards, ctxB.getShardStateManager(), this.io);
        
        // send a few updates to all contexts.
        for (ScheduleContext ctx : new ScheduleContext[] { ctxA, ctxB }) {
            for (long t = time; t < time + 10000000; t += 1000) {
                ctx.update(t + 0, 1);
                ctx.update(t + 1000, 11);
                ctx.update(t + 2000, 2);
                ctx.update(t + 3000, 22);
                ctx.update(t + 4000, 3);
                ctx.update(t + 5000, 33);
                ctx.update(t + 6000, 4);
                ctx.update(t + 7000, 44);            
            }
        }
        
        time += 10000000 + 7;
        ctxA.setCurrentTimeMillis(time);
        ctxB.setCurrentTimeMillis(time);
        
        // simulate a poll() cylce for each.
        pushA.performOperation();
        pushB.performOperation();
        pullA.performOperation();
        pullB.performOperation();
        
        // states should be the same.
        for (Granularity g : Granularity.rollupGranularities()) {
            for (int shard : allShards)
                Assert.assertEquals(ctxA.getSlotStamps(g, shard), ctxB.getSlotStamps(g, shard));
        }
        
        time += 300000; // this pushes us forward at least one slot.
        
        // now do this: update ctxA, do 2 push/pull cycles on each state.  they should sill be the same.
        ctxA.update(time,  1);
        ctxA.update(time, 11);
        ctxA.update(time, 2);
        ctxA.update(time, 22);
        ctxA.setCurrentTimeMillis(time);
        ctxB.setCurrentTimeMillis(time);
        
        // states should not be the same in some places.
        Assert.assertFalse(ctxA.getSlotStamps(Granularity.MIN_5, 1).equals(ctxB.getSlotStamps(Granularity.MIN_5, 1)));
        Assert.assertFalse(ctxA.getSlotStamps(Granularity.MIN_5, 11).equals(ctxB.getSlotStamps(Granularity.MIN_5, 11)));
        Assert.assertTrue(ctxA.getSlotStamps(Granularity.MIN_5, 3).equals(ctxB.getSlotStamps(Granularity.MIN_5, 3)));
        Assert.assertTrue(ctxA.getSlotStamps(Granularity.MIN_5, 33).equals(ctxB.getSlotStamps(Granularity.MIN_5, 33)));
        
        // this is where the syncing should happen. Order is important for a valid test.  A contains the updates, so
        // I want to put that one first.  B contains old data and it gets written second.  Part of what I'm verifying
        // is that B doesn't overwrite A with data that is obviously old.
        
        // A pushes updated data
        pushA.performOperation();
        // B tries to push old data (should not overwrite what A just did)
        pushB.performOperation();
        // B pulls new data (should get updates from A).
        pullB.performOperation();
        
        // we didn't do a pull on A because if things are broken, it would have pulled the crap data written by B and
        // given the false impression that all timestamps are the same.
        
        // states should have synced up and be the same again.
        for (Granularity g : Granularity.rollupGranularities()) {
            Assert.assertEquals(ctxA.getSlotStamps(g, commonShard), ctxB.getSlotStamps(g, commonShard));
        }
    }

    @Test
    // this test illustrates how loading shard state clobbered the knowledge that a shard,slot had already been 
    // rolled up.
    public void testUpdateClobbering() {
        long time = 1234L;
        final Collection<Integer> shardsA = Lists.newArrayList(1);
        final Collection<Integer> shardsB = Lists.newArrayList(2);
        Collection<Integer> allShards = new ArrayList<Integer>() {{
            for (int i : Iterables.concat(shardsA, shardsB)) add(i);
        }};
        
        ScheduleContext ctxA = new ScheduleContext(time, shardsA);
        ShardStateWorker pushA = new ShardStatePusher(allShards, ctxA.getShardStateManager(), this.io);
        ShardStateWorker pullA = new ShardStatePuller(allShards, ctxA.getShardStateManager(), this.io);
        
        // update.
        time += 1000;
        ctxA.setCurrentTimeMillis(time);
        ctxA.update(time, 1);
        
        // persist.
        pushA.performOperation();
        
        // time goes on.
        time += 600000;
        ctxA.setCurrentTimeMillis(time);
        
        // should be ready to schedule.
        ctxA.scheduleSlotsOlderThan(300000);
        Assert.assertEquals(1, ctxA.getScheduledCount());
        
        // simulate slots getting run.
        int count = 0;
        while (ctxA.getScheduledCount() > 0) {
            SlotKey slot = ctxA.getNextScheduled();
            ctxA.clearFromRunning(slot);
            ctxA.scheduleSlotsOlderThan(300000);
            count += 1;
        }
        Assert.assertEquals(5, count);
        // verify that scheduling doesn't find anything else.
        ctxA.scheduleSlotsOlderThan(300000);
        Assert.assertEquals(0, ctxA.getScheduledCount());
        
        // reloading under these circumstances (no updates) should not affect the schedule.
        pullA.performOperation();
        ctxA.scheduleSlotsOlderThan(300000);
        Assert.assertEquals(0, ctxA.getScheduledCount());
    }

    @Test
    public void testShardOperationsConcurrency() throws InterruptedException {
        final long tryFor = 15000;
        final AtomicLong time = new AtomicLong(1234L);
        final Collection<Integer> shards = Collections.unmodifiableCollection(Util.parseShards("ALL"));
        final ScheduleContext ctx = new ScheduleContext(time.get(), shards);
        final CountDownLatch latch = new CountDownLatch(2);
        final Throwable[] errBucket = new Throwable[2];
        Thread pushPull = new Thread() { public void run() {
            ShardStateWorker push = new ShardStatePusher(shards, ctx.getShardStateManager(), ShardStateIntegrationTest.this.io);
            ShardStateWorker pull = new ShardStatePuller(shards, ctx.getShardStateManager(), ShardStateIntegrationTest.this.io);
            
            push.setPeriod(1);
            pull.setPeriod(1);
            long startTime = System.currentTimeMillis();
            while (System.currentTimeMillis() - startTime < tryFor) {
                try {
                    push.performOperation();
                    pull.performOperation();
                } catch (Throwable th) {
                    th.printStackTrace();
                    errBucket[0] = th;
                    break;
                }
            }
            latch.countDown();
        }};
        Thread updateIterator = new Thread() { public void run() {
            long start = System.currentTimeMillis();
            outer: while (System.currentTimeMillis() - start < tryFor) {
                for (int shard : shards) {
                    time.set(time.get() + 30000);
                    ctx.setCurrentTimeMillis(time.get());
                    try {
                        ctx.update(time.get(), shard);
                    } catch (Throwable th) {
                        th.printStackTrace();
                        errBucket[1] = th;
                        break outer;
                    }
                }
            }
            latch.countDown();
        }};

        pushPull.start();
        updateIterator.start();
        latch.await(tryFor + 2000, TimeUnit.MILLISECONDS);
        Assert.assertNull(errBucket[0]);
        Assert.assertNull(errBucket[1]);
    }


    @Test
    public void testConvergenceForMultipleIngestors() throws InterruptedException {
        final long tryFor = 1000;
        final AtomicLong time = new AtomicLong(1234L);
        final Collection<Integer> shards = Collections.unmodifiableCollection(Util.parseShards("ALL"));
        final List<ScheduleContext> ctxs = Lists.newArrayList(new ScheduleContext(time.get(), shards), new ScheduleContext(time.get(), shards));
        final List<ShardStateWorker> workers = Lists.newArrayList(new ShardStatePusher(shards, ctxs.get(0).getShardStateManager(), ShardStateIntegrationTest.this.io),
                new ShardStatePuller(shards, ctxs.get(0).getShardStateManager(), ShardStateIntegrationTest.this.io),
                new ShardStatePusher(shards, ctxs.get(1).getShardStateManager(), ShardStateIntegrationTest.this.io),
                new ShardStatePuller(shards, ctxs.get(1).getShardStateManager(), ShardStateIntegrationTest.this.io));
        final CountDownLatch latch = new CountDownLatch(1);
        final AtomicBoolean err = new AtomicBoolean(false);

        Thread updateIterator = new Thread() { public void run() {
            long start = System.currentTimeMillis();
            Random rand = new Random();
            outer: while (System.currentTimeMillis() - start < tryFor) {
                for (int shard : shards) {
                    time.set(time.get() + 30000);
                    ScheduleContext ctx = ctxs.get(rand.nextInt(2));
                    try {
                        ctx.update(time.get(), shard);
                    } catch (Throwable th) {
                        th.printStackTrace();
                        err.set(true);
                        break outer;
                    }
                }
            }
            latch.countDown();
        }};

        updateIterator.start();
        latch.await();

        workers.get(0).performOperation();
        workers.get(3).performOperation();
        workers.get(2).performOperation();
        workers.get(1).performOperation();
        workers.get(0).performOperation();
        workers.get(3).performOperation();
        workers.get(2).performOperation();
        workers.get(1).performOperation();

        Assert.assertFalse(err.get());

        for (Granularity gran : Granularity.rollupGranularities()) {
            for (int shard : shards) {
                Assert.assertEquals(ctxs.get(0).getSlotStamps(gran, shard).size(), ctxs.get(1).getSlotStamps(gran, shard).size());
                for (Map.Entry<Integer, UpdateStamp> entry : ctxs.get(0).getSlotStamps(gran, shard).entrySet()) {
                    Assert.assertEquals(entry.getValue(), ctxs.get(1).getSlotStamps(gran, shard).get(entry.getKey()));
                }
            }
        }
    }

    @Test
    public void testSlotStateConvergence() throws InterruptedException {
        int shard = 0;
        long time = 1234000L;
        long metricTimeUpdate1 = time + 30000;
        long metricsTimeUpdate2 = time + 60000;
        Collection<Integer> shards = Lists.newArrayList(shard);
        List<ShardStateWorker> allWorkers = new ArrayList<ShardStateWorker>(6);

        // Ingestor 1
        ScheduleContext ctxIngestor1 = new ScheduleContext(time, shards);
        ShardStatePuller pullerIngestor1 = new ShardStatePuller(shards, ctxIngestor1.getShardStateManager(), this.io);
        ShardStatePusher pusherIngestor1 = new ShardStatePusher(shards, ctxIngestor1.getShardStateManager(), this.io);
        allWorkers.add(pullerIngestor1);
        allWorkers.add(pusherIngestor1);

        // Ingestor 2
        ScheduleContext ctxIngestor2 = new ScheduleContext(time, shards);
        ShardStatePuller pullerIngestor2 = new ShardStatePuller(shards, ctxIngestor2.getShardStateManager(), this.io);
        ShardStatePusher pusherIngestor2 = new ShardStatePusher(shards, ctxIngestor2.getShardStateManager(), this.io);
        allWorkers.add(pullerIngestor2);
        allWorkers.add(pusherIngestor2);

        // Rollup slave
        ScheduleContext ctxRollup = new ScheduleContext(time, shards);
        ShardStatePuller pullerRollup = new ShardStatePuller(shards, ctxRollup.getShardStateManager(), this.io);
        ShardStatePusher pusherRollup = new ShardStatePusher(shards, ctxRollup.getShardStateManager(), this.io);
        allWorkers.add(pullerRollup);
        allWorkers.add(pusherRollup);

        // Updates for same shard come for same slot on different ingestion contexts
        ctxIngestor1.update(metricTimeUpdate1, shard);
        ctxIngestor2.update(metricsTimeUpdate2, shard);

        makeWorkersSyncState(allWorkers);

        // After the sync, the higher timestamp should have "won" and ACTIVE slots should have converged on both the ingestion contexts
        for (Granularity gran : Granularity.rollupGranularities())
            Assert.assertEquals(ctxIngestor1.getSlotStamps(gran, shard), ctxIngestor2.getSlotStamps(gran, shard));

        ctxRollup.setCurrentTimeMillis(time + 600000L);
        ctxRollup.scheduleSlotsOlderThan(300000L);
        Assert.assertEquals(1, ctxRollup.getScheduledCount());

        // Simulate the hierarchical scheduling of slots
        int count = 0;
        while (ctxRollup.getScheduledCount() > 0) {
            SlotKey slot = ctxRollup.getNextScheduled();
            ctxRollup.clearFromRunning(slot);
            ctxRollup.scheduleSlotsOlderThan(300000L);
            count += 1;
        }
        Assert.assertEquals(5, count); // 5 rollup grans should have been scheduled by now

        makeWorkersSyncState(allWorkers);

        // By this point of time, all contexts should have got the ROLLED state
        for (Granularity gran : Granularity.rollupGranularities()) { // Check to see if shard states are indeed matching
            Assert.assertEquals(ctxIngestor1.getSlotStamps(gran, shard), ctxIngestor2.getSlotStamps(gran, shard));
            Assert.assertEquals(ctxRollup.getSlotStamps(gran, shard), ctxIngestor2.getSlotStamps(gran, shard));
        }

        Map<Integer, UpdateStamp> slotStamps;
        // Test for specific state of ROLLED. Because we have already tested that slot states are same across, it also means ROLLED has been stamped on ingestor1 and ingestor2
        for (Granularity gran : Granularity.rollupGranularities()) {
            int slot = 0;
            if (gran == Granularity.MIN_5) slot = 4;
            if (gran == Granularity.MIN_20) slot = 1;
            slotStamps = ctxRollup.getSlotStamps(gran, shard);
            Assert.assertEquals(slotStamps.get(slot).getState(), UpdateStamp.State.Rolled);
            Assert.assertEquals(slotStamps.get(slot).getTimestamp(), metricsTimeUpdate2);
        }

        // Delayed metric test
        long delayedMetricTimestamp = time + 45000; // Notice that this is lesser than the last time we rolled the slot
        ctxIngestor1.update(delayedMetricTimestamp, shard);

        makeWorkersSyncState(allWorkers);

        // Shard state will be the same throughout and will be marked as ACTIVE
        for (Granularity gran : Granularity.rollupGranularities()) {
            Assert.assertEquals(ctxIngestor1.getSlotStamps(gran, shard), ctxIngestor2.getSlotStamps(gran, shard));
            Assert.assertEquals(ctxRollup.getSlotStamps(gran, shard), ctxIngestor2.getSlotStamps(gran, shard));
        }

        for (Granularity gran : Granularity.rollupGranularities()) {
            int slot = 0;
            if (gran == Granularity.MIN_5) slot = 4;
            if (gran == Granularity.MIN_20) slot = 1;
            slotStamps = ctxRollup.getSlotStamps(gran, shard);
            Assert.assertEquals(slotStamps.get(slot).getState(), UpdateStamp.State.Active);
            Assert.assertEquals(slotStamps.get(slot).getTimestamp(), delayedMetricTimestamp);
        }

        // Scheduling the slot for rollup will and following the same process as we did before will mark the state as ROLLED again, but notice that it will have the timestamp of delayed metric
        ctxRollup.scheduleSlotsOlderThan(300000);
        Assert.assertEquals(1, ctxRollup.getScheduledCount());

        // Simulate the hierarchical scheduling of slots
        count = 0;
        while (ctxRollup.getScheduledCount() > 0) {
            SlotKey slot = ctxRollup.getNextScheduled();
            ctxRollup.clearFromRunning(slot);
            ctxRollup.scheduleSlotsOlderThan(300000);
            count += 1;
        }
        Assert.assertEquals(5, count); // 5 rollup grans should have been scheduled by now

        makeWorkersSyncState(allWorkers);

        for (Granularity gran : Granularity.rollupGranularities()) {
            Assert.assertEquals(ctxIngestor1.getSlotStamps(gran, shard), ctxIngestor2.getSlotStamps(gran, shard));
            Assert.assertEquals(ctxRollup.getSlotStamps(gran, shard), ctxIngestor2.getSlotStamps(gran, shard));
        }

        for (Granularity gran : Granularity.rollupGranularities()) {
            int slot = 0;
            if (gran == Granularity.MIN_5) slot = 4;
            if (gran == Granularity.MIN_20) slot = 1;
            slotStamps = ctxRollup.getSlotStamps(gran, shard);
            Assert.assertEquals(slotStamps.get(slot).getState(), UpdateStamp.State.Rolled);
            Assert.assertEquals(slotStamps.get(slot).getTimestamp(), delayedMetricTimestamp);
        }
    }

    @After
    public void cleanupShardStateIO () {
        if (this.io instanceof InMemoryShardStateIO) {
            ((InMemoryShardStateIO) this.io).cleanUp();
        }
    }

    private void makeWorkersSyncState(List<ShardStateWorker> workers) {
        // All states should be synced after 2 attempts, irrespective of operation ordering which is proved by shuffling of orders
        for (int i=0; i<=2; i++) {
            for (ShardStateWorker worker : workers) {
                worker.performOperation();
            }
        }
    }
    
    @Parameterized.Parameters
    public static Collection<Object[]> getDifferentShardStateIOInstances() {
        List<Object[]> instances = new ArrayList<Object[]>();
        instances.add(new Object[] { new AstyanaxShardStateIO() });
        instances.add(new Object[] { new InMemoryShardStateIO() });
        return instances;
    }
    
    private static class InMemoryShardStateIO implements ShardStateIO {
        
        private Map<Integer, Map<Granularity, Map<Integer, UpdateStamp>>> map = new HashMap<Integer, Map<Granularity, Map<Integer, UpdateStamp>>>();
        
        @Override
        public Collection<SlotState> getShardState(int shard) throws IOException {
            Map<Granularity, Map<Integer, UpdateStamp>> updates = map.get(shard);
            if (updates == null) {
                return new ArrayList<SlotState>();
            } else {
                List<SlotState> states = new ArrayList<SlotState>();
                for (Map.Entry<Granularity, Map<Integer, UpdateStamp>> e0 : updates.entrySet()) {
                    for (Map.Entry<Integer, UpdateStamp> e1 : e0.getValue().entrySet()) {
                        SlotState state = new SlotState(e0.getKey(), e1.getKey(), e1.getValue().getState());
                        state.withTimestamp(e1.getValue().getTimestamp());
                        states.add(state);
                    }
                }
                return states;
            }
        }

        @Override
        public void putShardState(int shard, Map<Granularity, Map<Integer, UpdateStamp>> slotTimes) throws IOException {
            map.put(shard, slotTimes);
        }

        public void cleanUp() {
            map.clear();
        }
    }
}


File: blueflood-core/src/integration-test/java/com/rackspacecloud/blueflood/utils/RollupTestUtils.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.utils;

import com.netflix.astyanax.model.ColumnFamily;
import com.rackspacecloud.blueflood.io.AstyanaxIO;
import com.rackspacecloud.blueflood.io.AstyanaxReader;
import com.rackspacecloud.blueflood.io.AstyanaxWriter;
import com.rackspacecloud.blueflood.io.CassandraModel;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.service.SingleRollupWriteContext;
import com.rackspacecloud.blueflood.types.*;
import org.apache.cassandra.thrift.Cassandra;

import java.util.ArrayList;

public class RollupTestUtils {
    public static void generateRollups(Locator locator, long from, long to, Granularity destGranularity) throws Exception {
        if (destGranularity == Granularity.FULL) {
            throw new Exception("Can't roll up to FULL");
        }

        ColumnFamily<Locator, Long> destCF = CassandraModel.getColumnFamily(BasicRollup.class, destGranularity);
        ArrayList<SingleRollupWriteContext> writeContexts = new ArrayList<SingleRollupWriteContext>();
        for (Range range : Range.rangesForInterval(destGranularity, from, to)) {
            Points<SimpleNumber> input = AstyanaxReader.getInstance().getDataToRoll(SimpleNumber.class, locator, range, CassandraModel.CF_METRICS_FULL);
            Rollup basicRollup = BasicRollup.buildRollupFromRawSamples(input);
            writeContexts.add(new SingleRollupWriteContext(basicRollup, locator, destGranularity, destCF, range.getStart()));
        }


        AstyanaxWriter.getInstance().insertRollups(writeContexts);
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/cache/AbstractJmxCache.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.cache;

import com.codahale.metrics.Gauge;
import com.codahale.metrics.JmxAttributeGauge;
import com.codahale.metrics.MetricRegistry;
import com.google.common.cache.CacheStats;
import com.rackspacecloud.blueflood.utils.Metrics;

import javax.management.ObjectName;

public abstract class AbstractJmxCache implements  CacheStatsMBean {

    private Gauge hitCount;
    private Gauge hitRate;
    private Gauge loadCount;
    private Gauge missRate;
    private Gauge requestCount;
    private Gauge totalLoadTime;

    public abstract CacheStats getStats();
    
    public long getHitCount() {
        return getStats().hitCount();
    }

    public double getHitRate() {
        return getStats().hitRate();
    }

    public long getMissCount() {
        return getStats().missCount();
    }

    public double getMissRate() {
        return getStats().missRate();
    }

    public long getLoadCount() {
        return getStats().loadCount();
    }

    public long getRequestCount() {
        return getStats().requestCount();
    }

    public long getTotalLoadTime() {
        return getStats().totalLoadTime();
    }

    public void instantiateYammerMetrics(Class klass, String scope, ObjectName nameObj) {
        String name = MetricRegistry.name(klass);
        if (scope != null) {
            name = MetricRegistry.name(name, scope);
        }
        MetricRegistry reg = Metrics.getRegistry();
        hitCount = reg.register(MetricRegistry.name(name, "Hit Count"),
                new JmxAttributeGauge(nameObj, "HitCount"));
        hitRate = reg.register(MetricRegistry.name(name, "Hit Rate"),
                new JmxAttributeGauge(nameObj, "HitRate"));
        loadCount = reg.register(MetricRegistry.name(name, "Load Count"),
                new JmxAttributeGauge(nameObj, "LoadCount"));
        missRate = reg.register(MetricRegistry.name(name, "Miss Rate"),
                new JmxAttributeGauge(nameObj, "MissRate"));
        requestCount = reg.register(MetricRegistry.name(name, "Request Count"),
                new JmxAttributeGauge(nameObj, "RequestCount"));
        totalLoadTime = reg.register(MetricRegistry.name(name, "Total Load Time"),
                new JmxAttributeGauge(nameObj, "TotalLoadTime"));
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/cache/CacheStatsMBean.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.cache;

public interface CacheStatsMBean {
    public long getHitCount();
    public double getHitRate();
    public long getMissCount();
    public double getMissRate();
    public long getLoadCount();
    public long getRequestCount();
    public long getTotalLoadTime();
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/cache/MetadataCache.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.cache;


import com.codahale.metrics.*;
import com.codahale.metrics.Timer;
import com.google.common.cache.CacheBuilder;
import com.google.common.cache.CacheLoader;
import com.google.common.cache.CacheStats;
import com.google.common.collect.HashBasedTable;
import com.google.common.collect.Table;
import com.rackspacecloud.blueflood.concurrent.ThreadPoolBuilder;
import com.rackspacecloud.blueflood.exceptions.CacheException;
import com.rackspacecloud.blueflood.io.AstyanaxMetadataIO;
import com.rackspacecloud.blueflood.io.MetadataIO;
import com.rackspacecloud.blueflood.service.Configuration;
import com.rackspacecloud.blueflood.service.CoreConfig;
import com.rackspacecloud.blueflood.types.Locator;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.management.InstanceAlreadyExistsException;
import javax.management.MBeanServer;
import javax.management.ObjectName;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.lang.management.ManagementFactory;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.*;
import java.util.concurrent.*;

public class MetadataCache extends AbstractJmxCache implements MetadataCacheMBean {
    // todo: give each cache a name.

    private final com.google.common.cache.LoadingCache<CacheKey, String> cache;
    private static final String NULL = "null".intern();
    private static final Logger log = LoggerFactory.getLogger(MetadataCache.class);
    private static final TimeValue defaultExpiration = new TimeValue(Configuration.getInstance().getIntegerProperty(
            CoreConfig.META_CACHE_RETENTION_IN_MINUTES), TimeUnit.MINUTES);
    private static final int defaultConcurrency = Configuration.getInstance().getIntegerProperty(
            CoreConfig.META_CACHE_MAX_CONCURRENCY);
    private final Boolean batchedReads;
    private final Boolean batchedWrites;

    // Specific to batched meta reads

    private static final Integer batchedReadsThreshold = Configuration.getInstance().getIntegerProperty(
            CoreConfig.META_CACHE_BATCHED_READS_THRESHOLD);
    private static final Integer batchedReadsTimerConfig = Configuration.getInstance().getIntegerProperty(
            CoreConfig.META_CACHE_BATCHED_READS_TIMER_MS);
    private static final TimeValue batchedReadsInterval = new TimeValue(batchedReadsTimerConfig, TimeUnit.MILLISECONDS);
    private static final Integer batchedReadsPipelineLimit = Configuration.getInstance().getIntegerProperty(
            CoreConfig.META_CACHE_BATCHED_READS_PIPELINE_DEPTH);

    private final java.util.Timer batchedReadsTimer = new java.util.Timer("MetadataBatchedReads");
    private final ThreadPoolExecutor readThreadPoolExecutor;
    private final Set<Locator> outstandingMetaReads;
    private final Queue<Locator> metaReads; // Guarantees FIFO reads
    private static final Timer batchedReadsTimerMetric = Metrics.timer(MetadataCache.class, "Metadata batched reads timer");

    // Specific to batched meta writes

    private static final Integer batchedWritesThreshold = Configuration.getInstance().getIntegerProperty(
            CoreConfig.META_CACHE_BATCHED_WRITES_THRESHOLD);
    private static final Integer batchedWritesTimerConfig = Configuration.getInstance().getIntegerProperty(
            CoreConfig.META_CACHE_BATCHED_WRITES_TIMER_MS);
    private static final TimeValue batchedWritesInterval = new TimeValue(batchedWritesTimerConfig, TimeUnit.MILLISECONDS);
    private static final Integer batchedWritesPipelineLimit = Configuration.getInstance().getIntegerProperty(
            CoreConfig.META_CACHE_BATCHED_WRITES_PIPELINE_DEPTH);

    private final java.util.Timer batchedWritesTimer = new java.util.Timer("MetadataBatchedWrites");
    private final ThreadPoolExecutor writeThreadPoolExecutor;
    private final Set<CacheKey> outstandingMetaWrites;
    private final Queue<CacheKey> metaWrites; // Guarantees FIFO writes
    private static final Timer batchedWritesTimerMetric = Metrics.timer(MetadataCache.class, "Metadata batched writes timer");

    private static final MetadataCache INSTANCE = new MetadataCache(defaultExpiration, defaultConcurrency);
    private MetadataIO io = new AstyanaxMetadataIO();
    private static Timer cacheSaveTimer = Metrics.timer(MetadataCache.class, "Persistence Save");
    private static Timer cacheLoadTimer = Metrics.timer(MetadataCache.class, "Persistence Load");
    private static final Meter updatedMetricMeter = Metrics.meter(MetadataCache.class, "Received updated metric");
    private static final Histogram totalMetadataSize = Metrics.histogram(MetadataCache.class, "Metadata row size");
    private static final Timer cacheGetTimer = Metrics.timer(MetadataCache.class, "Metadata get timer");
    private static final Timer cachePutTimer = Metrics.timer(MetadataCache.class, "Metadata put timer");
    private final Gauge cacheSizeGauge = new Gauge<Long>() {
        @Override
        public Long getValue() {
            return cache.size();
        }
    };

    private MetadataCache(TimeValue expiration, int concurrency) {
        try {
            final MBeanServer mbs = ManagementFactory.getPlatformMBeanServer();
            final String name = String.format(MetadataCache.class.getPackage().getName() + ":type=%s,name=Stats", MetadataCache.class.getSimpleName());
            final ObjectName nameObj = new ObjectName(name);
            mbs.registerMBean(this, nameObj);
            instantiateYammerMetrics(MetadataCache.class, "metadata", nameObj);
        } catch (InstanceAlreadyExistsException doNotCare) {
            log.debug(doNotCare.getMessage());
        } catch (Exception ex) {
            log.error("Unable to register mbean for " + getClass().getName(), ex);
        }

        CacheLoader<CacheKey, String> loader = new CacheLoader<CacheKey, String>() {
            @Override
            public String load(CacheKey key) throws Exception {
                return MetadataCache.this.databaseLoad(key.locator, key.keyString);
            }
        };
        cache = CacheBuilder.newBuilder()
                .expireAfterWrite(expiration.getValue(), expiration.getUnit())
                .concurrencyLevel(concurrency)
                .recordStats()
                .build(loader);
        try {
            Metrics.getRegistry().register(MetricRegistry.name(MetadataCache.class, "Cache Size"), this.cacheSizeGauge);
        } catch (Exception e) {
            // pass
        }
        this.outstandingMetaReads = new ConcurrentSkipListSet<Locator>();
        this.metaReads = new ConcurrentLinkedQueue<Locator>();
        this.readThreadPoolExecutor = new ThreadPoolBuilder().withCorePoolSize(batchedReadsPipelineLimit)
                .withMaxPoolSize(batchedReadsPipelineLimit)
                .withBoundedQueue(Configuration.getInstance()
                        .getIntegerProperty(CoreConfig.META_CACHE_BATCHED_READS_QUEUE_SIZE))
                .withName("MetaBatchedReadsThreadPool").build();

        this.batchedReads = Configuration.getInstance().getBooleanProperty(
                CoreConfig.META_CACHE_BATCHED_READS);
        this.batchedWrites = Configuration.getInstance().getBooleanProperty(
                CoreConfig.META_CACHE_BATCHED_WRITES);
        if (batchedReads) {
            this.batchedReadsTimer.schedule(new TimerTask() {
                @Override
                public void run() {
                    fetchMeta(true);
                }
            }, 0, this.batchedReadsInterval.toMillis());
        }
        this.outstandingMetaWrites = new ConcurrentSkipListSet<CacheKey>();
        this.writeThreadPoolExecutor = new ThreadPoolBuilder().withCorePoolSize(batchedWritesPipelineLimit)
                .withMaxPoolSize(batchedWritesPipelineLimit)
                .withBoundedQueue(Configuration.getInstance()
                        .getIntegerProperty(CoreConfig.META_CACHE_BATCHED_WRITES_QUEUE_SIZE))
                .withName("MetaBatchedWritesThreadPool").build();
        this.metaWrites = new ConcurrentLinkedQueue<CacheKey>();

        if (batchedWrites) {
            this.batchedWritesTimer.schedule(new TimerTask() {
                @Override
                public void run() {
                    flushMeta(true);
                }
            }, 0, this.batchedWritesInterval.toMillis());
        }
    }
    
    public void setIO(MetadataIO io) {
        this.io = io;
        cache.invalidateAll();
    }

    public static MetadataCache getInstance() {
        return INSTANCE;
    }

    public static MetadataCache createLoadingCacheInstance() {
        return new MetadataCache(defaultExpiration, defaultConcurrency);
    }

    public static MetadataCache createLoadingCacheInstance(TimeValue expiration, int concurrency) {
        return new MetadataCache(expiration, concurrency);
    }
    
    public void save(DataOutputStream out) throws IOException {
        
        Timer.Context ctx = cacheSaveTimer.time();
        try {
        // convert to a table. this avoids us writing out the locator over and over.
            Map<CacheKey, String> map = new HashMap<CacheKey, String>(cache.asMap());
            Table<Locator, String, String> table = HashBasedTable.create();
            for (Map.Entry<CacheKey, String> entry : map.entrySet()) {
                table.put(entry.getKey().locator, entry.getKey().keyString, entry.getValue());
            }
            
            Set<Locator> rowKeys = table.rowKeySet();
            out.writeInt(rowKeys.size());
            
            for (Locator locator : rowKeys) {
                out.writeUTF(locator.toString());
                
                // how many key/value pairs are there?
                Map<String, String> pairs = table.row(locator);
                out.writeInt(pairs.size());
                for (Map.Entry<String, String> entry : pairs.entrySet()) {
                    out.writeUTF(entry.getKey());
                    out.writeUTF(entry.getValue());
                }
            }
        } finally {
            ctx.stop();
        }
    }
    
    public void load(DataInputStream in) throws IOException {
        Timer.Context ctx = cacheLoadTimer.time();
        try {
            int numLocators = in.readInt();
            for (int locIndex = 0; locIndex < numLocators; locIndex++) {
                Locator locator = Locator.createLocatorFromDbKey(in.readUTF());
                int numPairs = in.readInt();
                for (int pairIndex = 0; pairIndex < numPairs; pairIndex++) {
                    cache.put(new CacheKey(locator, in.readUTF()), in.readUTF());
                }
            }
        } finally {
            ctx.stop();
        }
    }

    public boolean containsKey(Locator locator, String key) {
        return cache.getIfPresent(new CacheKey(locator, key)) != null;
    }

    public String get(Locator locator, String key) throws CacheException {
        if (!batchedReads) {
            return getImmediately(locator, key);
        }

        String val = cache.getIfPresent(new CacheKey(locator, key));

        if (val == null) {
            databaseLazyLoad(locator); // loads all meta for the locator (optimized to prevent duplicate reads)
        }

        return val;
    }

    public String getImmediately(Locator locator, String key) throws CacheException {
        Timer.Context cacheGetTimerContext = cacheGetTimer.time();
        try {
            CacheKey cacheKey = new CacheKey(locator, key);
            String result = cache.get(cacheKey);
            if (result.equals(NULL)) {
                return null;
            } else {
                return result;
            }
        } catch (ExecutionException ex) {
            throw new CacheException(ex);
        } finally {
            cacheGetTimerContext.stop();
        }
    }

    public <T> T get(Locator locator, String key, Class<T> type) throws CacheException {
        try {
            String val = get(locator, key);
            if (val == null) {
                return null;
            }
            return (T) val;
        } catch (ClassCastException ex) {
            throw new CacheException(ex);
        }
    }

    // todo: synchronization?
    // returns true if updated.
    public boolean put(Locator locator, String key, String value) throws CacheException {
        if (value == null) return false;

        Timer.Context cachePutTimerContext = MetadataCache.cachePutTimer.time();
        boolean dbWrite = false;
        try {
            CacheKey cacheKey = new CacheKey(locator, key);
            String oldValue = cache.getIfPresent(cacheKey);
            // don't care if oldValue == EMPTY.
            // always put new value in the cache. it keeps reads from happening.
            cache.put(cacheKey, value);
            if (oldValue == null || !oldValue.equals(value)) {
                dbWrite = true;
            }

            if (dbWrite) {
                updatedMetricMeter.mark();
                if (!batchedWrites) {
                    databasePut(locator, key, value);
                } else {
                    databaseLazyWrite(locator, key);
                }
            }

            return dbWrite;
        } finally {
            cachePutTimerContext.stop();
        }
    }

    public void invalidate(Locator locator, String key) {
        cache.invalidate(new CacheKey(locator, key));
    }

    private void databasePut(Locator locator, String key, String value) throws CacheException {
        try {
            io.put(locator, key, value);
        } catch (IOException ex) {
            throw new CacheException(ex);
        }
    }

    // implements the CacheLoader interface.
    private String databaseLoad(Locator locator, String key) throws CacheException {
        try {
            CacheKey cacheKey = new CacheKey(locator, key);
            Map<String, String> metadata = io.getAllValues(locator);
            if (metadata == null || metadata.isEmpty()) {
                cache.put(cacheKey, NULL);
                return NULL;
            }

            int metadataRowSize = 0;
            // prepopulate all other metadata other than the key we called the method with
            for (Map.Entry<String, String> meta : metadata.entrySet()) {
                metadataRowSize += meta.getKey().getBytes().length + locator.toString().getBytes().length;
                if (meta.getValue() != null)
                    metadataRowSize += meta.getValue().getBytes().length;
                if (meta.getKey().equals(key)) continue;
                CacheKey metaKey = new CacheKey(locator, meta.getKey());
                cache.put(metaKey, meta.getValue());
            }
            totalMetadataSize.update(metadataRowSize);

            String value = metadata.get(key);

            if (value == null) {
                cache.put(cacheKey, NULL);
                value = NULL;
            }

            return value;
        } catch (IOException ex) {
            throw new CacheException(ex);
        }
    }

    private void databaseLazyLoad(Locator locator) {
        boolean isPresent = outstandingMetaReads.contains(locator);

        if (!isPresent) {
            metaReads.add(locator);
            outstandingMetaReads.add(locator);
        }

        // Kickoff fetch meta if necessary
        if (metaReads.size() > batchedReadsThreshold) {
            fetchMeta(false);
        }
    }

    private void databaseLazyWrite(Locator locator, String metaKey) {
        CacheKey compoundKey = new CacheKey(locator, metaKey);
        if (outstandingMetaWrites.contains(compoundKey)) {
            return; // already queued up to write.
        }

        outstandingMetaWrites.add(compoundKey);
        metaWrites.add(compoundKey);

        if (metaWrites.size() > batchedWritesThreshold) {
            flushMeta(false);
        }

        return;
    }

    private void fetchMeta(boolean forced) { // Only one thread should ever call into this.
        synchronized (metaReads) {
            if (!forced && metaReads.size() < batchedReadsThreshold) {
                return;
            }

            while (!metaReads.isEmpty()) {
                Set<Locator> batch = new HashSet<Locator>();

                for (int i = 0; !metaReads.isEmpty() && i < batchedReadsThreshold; i++) {
                    batch.add(metaReads.poll()); // poll() is a destructive read (removes the head from the queue).
                }

                readThreadPoolExecutor.submit(new BatchedMetaReadsRunnable(batch));
            }
        }
    }

    private void flushMeta(boolean forced) { // Only one thread should ever call into this.
        synchronized (metaWrites) {
            if (!forced && metaWrites.size() < batchedWritesThreshold) {
                return;
            }

            while (!metaWrites.isEmpty()) {
                Table<Locator, String, String> metaBatch = HashBasedTable.create();

                for (int i = 0; !metaWrites.isEmpty() && i < batchedWritesThreshold; i++) {
                    CacheKey compoundKey = metaWrites.poll(); // destructive read.
                    Locator locator = compoundKey.locator();
                    String metaKey = compoundKey.keyString();
                    String metaVal = cache.getIfPresent(compoundKey);
                    if (metaVal != null) {
                        metaBatch.put(locator, metaKey, metaVal);
                    }
                }

                writeThreadPoolExecutor.submit(new BatchedMetaWritesRunnable(metaBatch));
            }
        }
    }

    private final class CacheKey implements Comparable<CacheKey> {
        private final Locator locator;
        private final String keyString;
        private final int hashCode;

        CacheKey(Locator locator, String keyString) {
            this.locator = locator;
            this.keyString = keyString;
            hashCode = (locator.toString() + "," + keyString).hashCode();
        }

        @Override
        public int hashCode() {
            return hashCode;
        }

        public Locator locator() {
            return locator;
        }

        public String keyString() {
            return keyString;
        }

        @Override
        public boolean equals(Object obj) {
            if (!(obj instanceof CacheKey)) return false;
            CacheKey other = (CacheKey)obj;
            // kind of a cop-out.
            return (locator().equals(other.locator) && keyString().equals(other.keyString()));
        }

        @Override
        public String toString() {
            return locator.toString() + "," + keyString;
        }

        @Override
        public int compareTo(CacheKey o) {
            return this.toString().compareTo(o.toString());
        }
    }

    @Override
    public CacheStats getStats() {
        return cache.stats();
    }

    private class BatchedMetaReadsRunnable implements Runnable {
        private final Set<Locator> locators;

        public BatchedMetaReadsRunnable(Set<Locator> locators) {
            this.locators = locators;
        }

        @Override
        public void run() {
            Timer.Context ctx = batchedReadsTimerMetric.time();
            try {
                Table<Locator, String, String> metaTable = io.getAllValues(locators);
                int metadataRowSize = 0;

                for (Locator locator : metaTable.rowKeySet()) {
                    Map<String, String> metaMapForLocator = metaTable.row(locator);

                    for (Map.Entry<String, String> meta : metaMapForLocator.entrySet()) {
                        CacheKey metaKey = new CacheKey(locator, meta.getKey());
                        String existing = cache.getIfPresent(metaKey);

                        if (existing == null) {
                            cache.put(metaKey, meta.getValue());
                        }

                        boolean differs = existing != null && !existing.equals(meta.getValue());
                        if (differs) {
                            log.warn("Meta " + meta.getKey() + " changed from " + existing + " to " + meta.getValue()
                                    + " for locator " + locator); // delayed audit log.
                            // In this case, do not update the cache. DB has stale data.
                            continue;
                        }

                        metadataRowSize += meta.getKey().getBytes().length + locator.toString().getBytes().length;
                        metadataRowSize += meta.getValue().getBytes().length;
                    }

                    // Got the meta for locator. Remove this from the place holder.
                    outstandingMetaReads.remove(locator);
                }

                totalMetadataSize.update(metadataRowSize);
                // Kickoff fetch meta if necessary
                if (metaReads.size() > batchedReadsThreshold) {
                    fetchMeta(false);
                }
            } catch (Exception ex) {
                // Queue up the locators again (at the end)!
                for (Locator locator : locators) {
                    metaReads.add(locator);
                }
                log.error("Exception reading metadata from db (batched reads)", ex);
            } finally {
                ctx.stop();
            }
        }
    }

    private class BatchedMetaWritesRunnable implements Runnable {
        private final Table<Locator, String, String> metaToWrite;

        public BatchedMetaWritesRunnable(Table<Locator, String, String> metaToWrite) {
            this.metaToWrite = metaToWrite;
        }

        @Override
        public void run() {
            Timer.Context ctx = batchedWritesTimerMetric.time();
            try {
                io.putAll(metaToWrite);
            } catch (Exception ex) {
                log.error("Exception writing metadata to db (batched writes)", ex);
                // Queue up writes at the end.
                for (Locator locator : metaToWrite.rowKeySet()) {
                    Map<String, String> metaMapForLocator = metaToWrite.row(locator);

                    for (Map.Entry<String, String> meta : metaMapForLocator.entrySet()) {
                        CacheKey compoundKey = new CacheKey(locator, meta.getKey());
                        metaWrites.add(compoundKey);
                        // This is fine. We always read the latest value from the real cache. So we'll pull the latest
                        // value to write.
                    }
                }
            } finally {
                ctx.stop();
            }
        }
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/cache/MetadataCacheMBean.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.cache;

public interface MetadataCacheMBean extends CacheStatsMBean {
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/concurrent/ThreadPoolBuilder.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.concurrent;

import com.google.common.util.concurrent.ThreadFactoryBuilder;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

public class ThreadPoolBuilder {
    private static final Logger log = LoggerFactory.getLogger(ThreadPoolBuilder.class);
    /** Used to ensure that the thread pools have unique name. */
    private static final ConcurrentHashMap<String, AtomicInteger> nameMap = new ConcurrentHashMap<String, AtomicInteger>();
    private static final String DEFAULT_NAME = "Threadpool";
    private int corePoolSize = 10;
    private int maxPoolSize = 10;
    private int queueSize = 0;
    private TimeValue keepAliveTime = new TimeValue(30, TimeUnit.SECONDS);
    
    private RejectedExecutionHandler rejectedHandler = new ThreadPoolExecutor.CallerRunsPolicy();
    private Thread.UncaughtExceptionHandler exceptionHandler = new Thread.UncaughtExceptionHandler() {
        public void uncaughtException(Thread t, Throwable e) {
            log.error(e.getMessage(), e);
        }
    };

    private String threadNameFormat = null;
    private String poolName = null;

    public ThreadPoolBuilder() {
        withName(DEFAULT_NAME);
    }

    public ThreadPoolBuilder withCorePoolSize(int size) {
        this.corePoolSize = size;
        return this;
    }

    public ThreadPoolBuilder withMaxPoolSize(int size) {
        this.maxPoolSize = size;
        return this;
    }

    public ThreadPoolBuilder withSynchronousQueue() {
        this.queueSize = 0;
        return this;
    }

    public ThreadPoolBuilder withUnboundedQueue() {
        this.queueSize = -1;
        return this;
    }

    public ThreadPoolBuilder withBoundedQueue(int size) {
        this.queueSize = size;
        return this;
    }
    
    public ThreadPoolBuilder withKeepAliveTime(TimeValue time) {
        this.keepAliveTime = time;
        return this;
    }

    public ThreadPoolBuilder withRejectedHandler(RejectedExecutionHandler rejectedHandler) {
        this.rejectedHandler = rejectedHandler;
        return this;
    }

    /**
     * Set the threadpool name. Used to generate metric names and thread names.
     */
    public ThreadPoolBuilder withName(String name) {
        // ensure we've got a spot to put the thread id.
        if (!name.contains("%d")) {
            name = name + "-%d";
        }
        nameMap.putIfAbsent(name, new AtomicInteger(0));
        int id = nameMap.get(name).incrementAndGet();
        this.poolName = String.format(name, id);
        if (id > 1) {
            this.threadNameFormat = name.replace("%d", id + "-%d");
        } else {
            this.threadNameFormat = name;
        }
        return this;
    }

    public ThreadPoolBuilder withExceptionHandler(Thread.UncaughtExceptionHandler exceptionHandler) {
        this.exceptionHandler = exceptionHandler;
        return this;
    }

    public ThreadPoolExecutor build() {
        BlockingQueue<Runnable> workQueue;
        switch (this.queueSize) {
            case 0: workQueue = new SynchronousQueue<Runnable>();
                break;
            case -1: workQueue = new LinkedBlockingQueue<Runnable>();
                break;
            default: workQueue = new ArrayBlockingQueue<Runnable>(queueSize);
                break;
        };

        ThreadPoolExecutor executor = new ThreadPoolExecutor(
                corePoolSize, maxPoolSize,
                keepAliveTime.getValue(), keepAliveTime.getUnit(),
                workQueue,
                new ThreadFactoryBuilder().setNameFormat(threadNameFormat).setPriority(Thread.NORM_PRIORITY).setUncaughtExceptionHandler(exceptionHandler).build(),
                rejectedHandler);
        InstrumentedThreadPoolExecutor.instrument(executor, poolName);
        return executor;
    }
}

File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/eventemitter/RollupEvent.java
/*
* Copyright 2013 Rackspace
*
*    Licensed under the Apache License, Version 2.0 (the "License");
*    you may not use this file except in compliance with the License.
*    You may obtain a copy of the License at
*
*        http://www.apache.org/licenses/LICENSE-2.0
*
*    Unless required by applicable law or agreed to in writing, software
*    distributed under the License is distributed on an "AS IS" BASIS,
*    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
*    See the License for the specific language governing permissions and
*    limitations under the License.
*/

package com.rackspacecloud.blueflood.eventemitter;

import com.rackspacecloud.blueflood.types.Locator;
import com.rackspacecloud.blueflood.types.Rollup;

public class RollupEvent {
    private final Locator locator;
    private final Rollup rollup;
    private String unit;
    private final String granularityName;
    //Rollup slot in millis
    private final long timestamp;

    public RollupEvent(Locator loc, Rollup rollup, String unit, String gran, long ts) {
        this.locator = loc;
        this.rollup = rollup;
        this.unit = unit;
        this.granularityName = gran;
        this.timestamp = ts;
    }

    public Rollup getRollup() {
        return rollup;
    }

    public Locator getLocator() {
        return locator;
    }

    public String getUnit() {
        return unit;
    }

    public String getGranularityName() {
        return granularityName;
    }

    public long getTimestamp() {
        return timestamp;
    }

    public void setUnit(String unit) {
        this.unit = unit;
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/eventemitter/RollupEventEmitter.java
/*
* Copyright 2013 Rackspace
*
*    Licensed under the Apache License, Version 2.0 (the "License");
*    you may not use this file except in compliance with the License.
*    You may obtain a copy of the License at
*
*        http://www.apache.org/licenses/LICENSE-2.0
*
*    Unless required by applicable law or agreed to in writing, software
*    distributed under the License is distributed on an "AS IS" BASIS,
*    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
*    See the License for the specific language governing permissions and
*    limitations under the License.
*/

package com.rackspacecloud.blueflood.eventemitter;

import com.google.common.base.Function;
import com.google.common.collect.Lists;
import com.rackspacecloud.blueflood.concurrent.ThreadPoolBuilder;
import com.rackspacecloud.blueflood.io.DiscoveryIO;
import com.rackspacecloud.blueflood.types.BasicRollup;
import com.rackspacecloud.blueflood.utils.QueryDiscoveryModuleLoader;
import com.rackspacecloud.blueflood.utils.Util;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Arrays;
import java.util.concurrent.*;

public class RollupEventEmitter extends Emitter<RollupEvent> {
    private static final Logger log = LoggerFactory.getLogger(QueryDiscoveryModuleLoader.class);
    private static final int numberOfWorkers = 5;
    public static final String ROLLUP_EVENT_NAME = "rollup".intern();
    private static ThreadPoolExecutor eventExecutors;
    private static final RollupEventEmitter instance = new RollupEventEmitter();

    private RollupEventEmitter() {
        eventExecutors = new ThreadPoolBuilder()
                .withName("RollupEventEmitter ThreadPool")
                .withCorePoolSize(numberOfWorkers)
                .withMaxPoolSize(numberOfWorkers)
                .withUnboundedQueue()
                .build();
    }

    public static RollupEventEmitter getInstance() { return instance; }

    @Override
    public Future emit(final String event, final RollupEvent... eventPayload) {
        //TODO: This hack will go away after Kafka Serializer is made generic
        Future emitFuture = null;
        if(eventPayload[0].getRollup() instanceof BasicRollup && super.hasListeners(ROLLUP_EVENT_NAME)) {
            emitFuture = eventExecutors.submit(new Callable() {
                @Override
                public Future call() {
                    if (Util.shouldUseESForUnits()) {
                        QueryDiscoveryModuleLoader.loadDiscoveryModule();
                        final DiscoveryIO discoveryIO = QueryDiscoveryModuleLoader.getDiscoveryInstance();
                        // TODO: Sync for now, but we will have to make it async eventually
                        Lists.transform(Arrays.asList(eventPayload), new Function<RollupEvent, RollupEvent>() {
                            @Override
                            public RollupEvent apply(RollupEvent event) {
                                String unit;
                                try {
                                    unit = discoveryIO.search(event.getLocator().getTenantId(), event.getLocator().getMetricName()).get(0).getUnit();
                                } catch (Exception e) {
                                    log.warn("Exception encountered while getting units out of ES : %s", e.getMessage());
                                    unit = Util.UNKNOWN;
                                }
                                event.setUnit(unit);
                                return event;
                            }
                        });
                    }
                    return RollupEventEmitter.super.emit(event, eventPayload);
                }
            });
        }
        return emitFuture;
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/exceptions/CacheException.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.exceptions;

// todo: consider just dropping this for IOException.
public class CacheException extends Exception {
    public CacheException(Throwable cause) {
        super(cause);
    }
    
    public CacheException(String wha) {
        super(wha);
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/exceptions/GranularityException.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.exceptions;

public class GranularityException extends Exception {

    public GranularityException(String message) {
        super(message);
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/exceptions/IncomingMetricException.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.exceptions;

public abstract class IncomingMetricException extends Exception {
    public IncomingMetricException(String message) {
        super(message);
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/exceptions/IncomingTypeException.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.exceptions;

import com.rackspacecloud.blueflood.exceptions.IncomingMetricException;
import com.rackspacecloud.blueflood.types.Locator;

public class IncomingTypeException extends IncomingMetricException {
    private final Locator locator;
    private final String oldType;
    private final String newType;
    
    public IncomingTypeException(Locator locator, String oldType, String newType) {
        super(String.format("Detected type change for %s %s->%s", locator.toString(), oldType, newType));
        this.locator = locator;
        this.oldType = oldType;
        this.newType = newType;
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/exceptions/IncomingUnitException.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.exceptions;

import com.rackspacecloud.blueflood.exceptions.IncomingMetricException;
import com.rackspacecloud.blueflood.types.Locator;

public class IncomingUnitException extends IncomingMetricException {
    private final Locator locator;
    private final String oldUnit;
    private final String newUnit;

    public IncomingUnitException(Locator locator, String oldUnit, String newUnit) {
        super(String.format("Detected unit change for %s %s->%s", locator.toString(), oldUnit, newUnit));
        this.locator = locator;
        this.oldUnit = oldUnit;
        this.newUnit = newUnit;
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/exceptions/InvalidRequestException.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.exceptions;

public class InvalidRequestException extends Exception {

    public InvalidRequestException(String message) {
        super(message);
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/exceptions/SerializationException.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.exceptions;

import java.io.IOException;

public class SerializationException extends IOException {
    public SerializationException(String message) {
        super(message);
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/exceptions/UnexpectedStringSerializationException.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.exceptions;

public class UnexpectedStringSerializationException extends SerializationException {
    public UnexpectedStringSerializationException(String message) {
        super(message);
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/inputs/formats/JSONMetricsContainer.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.inputs.formats;

import com.rackspacecloud.blueflood.types.Locator;
import com.rackspacecloud.blueflood.types.Metric;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.codehaus.jackson.annotate.JsonIgnore;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

public class JSONMetricsContainer {
    private final String tenantId;
    private final List<JSONMetric> jsonMetrics;

    public JSONMetricsContainer(String tenantId, List<JSONMetric> metrics) {
        this.tenantId = tenantId;
        this.jsonMetrics = metrics;
    }

    public boolean isValid() {
        // Validate that any ScopedJSONMetric is actually scoped to a tenant.
        for (JSONMetric jsonMetric : this.jsonMetrics) {
            if (!jsonMetric.isValid()) {
                return false;
            }
        }
        return true;
    }

    public List<Metric> toMetrics() {
        if (jsonMetrics == null || jsonMetrics.isEmpty()) {
            return null;
        }

        final List<Metric> metrics = new ArrayList<Metric>();
        for (JSONMetric jsonMetric : jsonMetrics) {
            Locator locator;
            if (jsonMetric instanceof ScopedJSONMetric) {
                ScopedJSONMetric scopedMetric = (ScopedJSONMetric)jsonMetric;
                locator = Locator.createLocatorFromPathComponents(scopedMetric.getTenantId(), jsonMetric.getMetricName());
            } else {
                locator = Locator.createLocatorFromPathComponents(tenantId, jsonMetric.getMetricName());
            }

            if (jsonMetric.getMetricValue() != null) {
                final Metric metric = new Metric(locator, jsonMetric.getMetricValue(), jsonMetric.getCollectionTime(),
                        new TimeValue(jsonMetric.getTtlInSeconds(), TimeUnit.SECONDS), jsonMetric.getUnit());
                metrics.add(metric);
            }
        }

        return metrics;
    }

    // Jackson compatible class. Jackson uses reflection to call these methods and so they have to match JSON keys.
    public static class JSONMetric {
        private String metricName;
        private Object metricValue;
        private long collectionTime;
        private int ttlInSeconds;
        private String unit;

        public String getMetricName() {
            return metricName;
        }

        public void setMetricName(String metricName) {
            this.metricName = metricName;
        }

        public String getUnit() {
            return unit;
        }

        public void setUnit(String unit) {
            this.unit = unit;
        }

        public Object getMetricValue() {
            return metricValue;
        }

        public void setMetricValue(Object metricValue) {
            this.metricValue = metricValue;
        }

        public long getCollectionTime() {
            return collectionTime;
        }

        public void setCollectionTime(long collectionTime) {
            this.collectionTime = collectionTime;
        }

        public int getTtlInSeconds() {
            return this.ttlInSeconds;
        }

        public void setTtlInSeconds(int ttlInSeconds) {
            this.ttlInSeconds = ttlInSeconds;
        }

        @JsonIgnore
        public boolean isValid() {
            return true;
        }
    }

    public static class ScopedJSONMetric extends JSONMetric {
        private String tenantId;

        public String getTenantId() { return tenantId; }

        public void setTenantId(String tenantId) { this.tenantId = tenantId; }

        @JsonIgnore
        public boolean isValid() {
            return (tenantId != null && super.isValid());
        }
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/io/AstyanaxIO.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io;

import com.netflix.astyanax.AstyanaxContext;
import com.netflix.astyanax.Keyspace;
import com.netflix.astyanax.connectionpool.NodeDiscoveryType;
import com.netflix.astyanax.connectionpool.impl.ConnectionPoolConfigurationImpl;
import com.netflix.astyanax.connectionpool.impl.ConnectionPoolType;
import com.netflix.astyanax.impl.AstyanaxConfigurationImpl;
import com.netflix.astyanax.retry.RetryNTimes;
import com.netflix.astyanax.serializers.AbstractSerializer;
import com.netflix.astyanax.serializers.BooleanSerializer;
import com.netflix.astyanax.serializers.StringSerializer;
import com.netflix.astyanax.thrift.ThriftFamilyFactory;
import com.rackspacecloud.blueflood.io.serializers.NumericSerializer;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.service.Configuration;
import com.rackspacecloud.blueflood.service.CoreConfig;
import com.rackspacecloud.blueflood.types.DataType;
import com.rackspacecloud.blueflood.types.RollupType;

import java.util.*;

public class AstyanaxIO {
    private static final AstyanaxContext<Keyspace> context;
    private static final Keyspace keyspace;
    protected static final Configuration config = Configuration.getInstance();

    static {
        context = createPreferredHostContext();
        context.start();
        keyspace = context.getEntity();
    }

    protected AstyanaxIO() {
    }

    private static AstyanaxContext<Keyspace> createCustomHostContext(AstyanaxConfigurationImpl configuration,
            ConnectionPoolConfigurationImpl connectionPoolConfiguration) {
        return new AstyanaxContext.Builder()
                .forCluster(CassandraModel.CLUSTER)
                .forKeyspace(CassandraModel.KEYSPACE)
                .withAstyanaxConfiguration(configuration)
                .withConnectionPoolConfiguration(connectionPoolConfiguration)
                .withConnectionPoolMonitor(new InstrumentedConnectionPoolMonitor())
                .buildKeyspace(ThriftFamilyFactory.getInstance());
    }

    private static AstyanaxContext<Keyspace> createPreferredHostContext() {
        return createCustomHostContext(createPreferredAstyanaxConfiguration(), createPreferredConnectionPoolConfiguration());
    }

    private static AstyanaxConfigurationImpl createPreferredAstyanaxConfiguration() {
        AstyanaxConfigurationImpl astyconfig = new AstyanaxConfigurationImpl()
                .setDiscoveryType(NodeDiscoveryType.NONE)
                .setConnectionPoolType(ConnectionPoolType.ROUND_ROBIN);

        int numRetries = config.getIntegerProperty(CoreConfig.CASSANDRA_MAX_RETRIES);
        if (numRetries > 0) {
            astyconfig.setRetryPolicy(new RetryNTimes(numRetries));
        }

        return astyconfig;
    }

    private static ConnectionPoolConfigurationImpl createPreferredConnectionPoolConfiguration() {
        int port = config.getIntegerProperty(CoreConfig.DEFAULT_CASSANDRA_PORT);
        Set<String> uniqueHosts = new HashSet<String>();
        Collections.addAll(uniqueHosts, config.getStringProperty(CoreConfig.CASSANDRA_HOSTS).split(","));
        int numHosts = uniqueHosts.size();
        int maxConns = config.getIntegerProperty(CoreConfig.MAX_CASSANDRA_CONNECTIONS);
        int timeout = config.getIntegerProperty(CoreConfig.CASSANDRA_REQUEST_TIMEOUT);

        int connsPerHost = maxConns / numHosts + (maxConns % numHosts == 0 ? 0 : 1);
        // This timeout effectively results in waiting a maximum of (timeoutWhenExhausted / numHosts) on each Host
        int timeoutWhenExhausted = config.getIntegerProperty(CoreConfig.MAX_TIMEOUT_WHEN_EXHAUSTED);
        timeoutWhenExhausted = Math.max(timeoutWhenExhausted, 1 * numHosts); // Minimum of 1ms per host

        final ConnectionPoolConfigurationImpl connectionPoolConfiguration = new ConnectionPoolConfigurationImpl("MyConnectionPool")
                .setPort(port)
                .setSocketTimeout(timeout)
                .setInitConnsPerHost(connsPerHost)
                .setMaxConnsPerHost(connsPerHost)
                .setMaxBlockedThreadsPerHost(5)
                .setMaxTimeoutWhenExhausted(timeoutWhenExhausted)
                .setInitConnsPerHost(connsPerHost / 2)
                .setSeeds(config.getStringProperty(CoreConfig.CASSANDRA_HOSTS));
        return connectionPoolConfiguration;
    }

    protected static Keyspace getKeyspace() {
        return keyspace;
    }

    protected AbstractSerializer serializerFor(RollupType rollupType, DataType dataType, Granularity gran) {
        if (rollupType == null) {
            rollupType = RollupType.BF_BASIC;
        }

        if (dataType == null) {
            dataType = DataType.NUMERIC;
        }

        if (dataType.equals(DataType.STRING)) {
            return StringSerializer.get();
        } else if (dataType.equals(DataType.BOOLEAN)) {
            return BooleanSerializer.get();
        } else {
            return NumericSerializer.serializerFor(RollupType.classOf(rollupType, gran));
        }
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/io/AstyanaxReader.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io;

import com.codahale.metrics.Timer;
import com.google.common.collect.ArrayListMultimap;
import com.google.common.collect.HashBasedTable;
import com.google.common.collect.ListMultimap;
import com.google.common.collect.Table;
import com.netflix.astyanax.Keyspace;
import com.netflix.astyanax.connectionpool.OperationResult;
import com.netflix.astyanax.connectionpool.exceptions.ConnectionException;
import com.netflix.astyanax.connectionpool.exceptions.NotFoundException;
import com.netflix.astyanax.model.*;
import com.netflix.astyanax.query.RowQuery;
import com.netflix.astyanax.serializers.AbstractSerializer;
import com.netflix.astyanax.serializers.BooleanSerializer;
import com.netflix.astyanax.serializers.StringSerializer;
import com.netflix.astyanax.shallows.EmptyColumnList;
import com.netflix.astyanax.util.RangeBuilder;
import com.rackspacecloud.blueflood.cache.MetadataCache;
import com.rackspacecloud.blueflood.exceptions.CacheException;
import com.rackspacecloud.blueflood.io.serializers.NumericSerializer;
import com.rackspacecloud.blueflood.io.serializers.StringMetadataSerializer;
import com.rackspacecloud.blueflood.outputs.formats.MetricData;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.service.SlotState;
import com.rackspacecloud.blueflood.types.*;
import com.rackspacecloud.blueflood.utils.Util;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.*;

public class AstyanaxReader extends AstyanaxIO {
    private static final Logger log = LoggerFactory.getLogger(AstyanaxReader.class);
    private static final MetadataCache metaCache = MetadataCache.getInstance();
    private static final AstyanaxReader INSTANCE = new AstyanaxReader();
    private static final String rollupTypeCacheKey = MetricMetadata.ROLLUP_TYPE.toString().toLowerCase();
    private static final String dataTypeCacheKey = MetricMetadata.TYPE.toString().toLowerCase();

    private static final Keyspace keyspace = getKeyspace();

    public static AstyanaxReader getInstance() {
        return INSTANCE;
    }

    /**
     * Method that returns all metadata for a given locator as a map.
     *
     * @param locator  locator name
     * @return Map of metadata for that locator
     * @throws RuntimeException(com.netflix.astyanax.connectionpool.exceptions.ConnectionException)
     */
    public Map<String, String> getMetadataValues(Locator locator) {
        Timer.Context ctx = Instrumentation.getReadTimerContext(CassandraModel.CF_METRIC_METADATA);
        try {
            final ColumnList<String> results = keyspace.prepareQuery(CassandraModel.CF_METRIC_METADATA)
                    .getKey(locator)
                    .execute().getResult();
            return new HashMap<String, String>(){{
                for (Column<String> result : results) {
                    put(result.getName(), result.getValue(StringMetadataSerializer.get()));
                }
            }};
        } catch (NotFoundException ex) {
            Instrumentation.markNotFound(CassandraModel.CF_METRIC_METADATA);
            return null;
        } catch (ConnectionException e) {
            log.error("Error reading metadata value", e);
            Instrumentation.markReadError(e);
            throw new RuntimeException(e);
        } finally {
            ctx.stop();
        }
    }

    public Table<Locator, String, String> getMetadataValues(Set<Locator> locators) {
        ColumnFamily CF = CassandraModel.CF_METRIC_METADATA;
        boolean isBatch = locators.size() > 1;
        Table<Locator, String, String> metaTable = HashBasedTable.create();

        Timer.Context ctx = isBatch ? Instrumentation.getBatchReadTimerContext(CF) : Instrumentation.getReadTimerContext(CF);
        try {
            // We don't paginate this call. So we should make sure the number of reads is tolerable.
            // TODO: Think about paginating this call.
            OperationResult<Rows<Locator, String>> query = keyspace
                    .prepareQuery(CF)
                    .getKeySlice(locators)
                    .execute();

            for (Row<Locator, String> row : query.getResult()) {
                ColumnList<String> columns = row.getColumns();
                for (Column<String> column : columns) {
                    String metaValue = column.getValue(StringMetadataSerializer.get());
                    String metaKey = column.getName();
                    metaTable.put(row.getKey(), metaKey, metaValue);
                }
            }
        } catch (ConnectionException e) {
            if (e instanceof NotFoundException) { // TODO: Not really sure what happens when one of the keys is not found.
                Instrumentation.markNotFound(CF);
            } else {
                if (isBatch) { Instrumentation.markBatchReadError(e); }
                else { Instrumentation.markReadError(e); }
            }
            log.warn((isBatch ? "Batch " : "") + " read query failed for column family " + CF.getName(), e);
        } finally {
            ctx.stop();
        }

        return metaTable;
    }

    /**
     * Method that makes the actual cassandra call to get the most recent string value for a locator
     *
     * @param locator  locator name
     * @return String most recent string value for metric.
     * @throws RuntimeException(com.netflix.astyanax.connectionpool.exceptions.ConnectionException)
     */
    public String getLastStringValue(Locator locator) {
        Timer.Context ctx = Instrumentation.getReadTimerContext(CassandraModel.CF_METRICS_STRING);

        try {
            ColumnList<Long> query = keyspace
                    .prepareQuery(CassandraModel.CF_METRICS_STRING)
                    .getKey(locator)
                    .withColumnRange(new RangeBuilder().setReversed(true).setLimit(1).build())
                    .execute()
                    .getResult();

            return query.isEmpty() ? null : query.getColumnByIndex(0).getStringValue();
        } catch (ConnectionException e) {
            if (e instanceof NotFoundException) {
                Instrumentation.markNotFound(CassandraModel.CF_METRICS_STRING);
            } else {
                Instrumentation.markReadError(e);
            }
            log.warn("Could not get previous string metric value for locator " +
                    locator, e);
            throw new RuntimeException(e);
        } finally {
            ctx.stop();
        }
    }

    /**
     * Returns the recently seen locators, i.e. those that should be rolled up, for a given shard.
     * 'Should' means:
     *  1) A locator is capable of rollup (it is not a string/boolean metric).
     *  2) A locator has had new data in the past {@link com.rackspacecloud.blueflood.io.AstyanaxWriter.LOCATOR_TTL} seconds.
     *
     * @param shard Number of the shard you want the recent locators for. 0-127 inclusive.
     * @return Collection of locators
     * @throws RuntimeException(com.netflix.astyanax.connectionpool.exceptions.ConnectionException)
     */
    public Collection<Locator> getLocatorsToRollup(long shard) {
        Timer.Context ctx = Instrumentation.getReadTimerContext(CassandraModel.CF_METRICS_LOCATOR);
        try {
            RowQuery<Long, Locator> query = keyspace
                    .prepareQuery(CassandraModel.CF_METRICS_LOCATOR)
                    .getKey(shard);
            return query.execute().getResult().getColumnNames();
        } catch (NotFoundException e) {
            Instrumentation.markNotFound(CassandraModel.CF_METRICS_LOCATOR);
            return Collections.emptySet();
        } catch (ConnectionException e) {
            Instrumentation.markReadError(e);
            log.error("Error reading locators", e);
            throw new RuntimeException("Error reading locators", e);
        } finally {
            ctx.stop();
        }
    }

    /**
     * Gets all ShardStates for a given shard.
     *
     * @param shard Shard to retrieve all SlotState objects for.
     */
    public Collection<SlotState> getShardState(int shard) {
        Timer.Context ctx = Instrumentation.getReadTimerContext(CassandraModel.CF_METRICS_STATE);
        final Collection<SlotState> slotStates = new LinkedList<SlotState>();
        try {
            ColumnList<SlotState> columns = keyspace.prepareQuery(CassandraModel.CF_METRICS_STATE)
                    .getKey((long)shard)
                    .execute()
                    .getResult();

            for (Column<SlotState> column : columns) {
                slotStates.add(column.getName().withTimestamp(column.getLongValue()));
            }
        } catch (ConnectionException e) {
            Instrumentation.markReadError(e);
            log.error("Error getting shard state for shard " + shard, e);
            throw new RuntimeException(e);
        } finally {
            ctx.stop();
        }
        return slotStates;
    }

    private ColumnList<Long> getColumnsFromDB(final Locator locator, ColumnFamily<Locator, Long> srcCF, Range range) {
        List<Locator> locators = new LinkedList<Locator>(){{ add(locator); }};
        ColumnList<Long> columns = getColumnsFromDB(locators, srcCF, range).get(locator);
        return columns == null ? new EmptyColumnList<Long>() : columns;
    }

    private Map<Locator, ColumnList<Long>> getColumnsFromDB(List<Locator> locators, ColumnFamily<Locator, Long> CF,
                                                            Range range) {
        if (range.getStart() > range.getStop()) {
            throw new RuntimeException(String.format("Invalid rollup range: ", range.toString()));
        }
        boolean isBatch = locators.size() != 1;

        final Map<Locator, ColumnList<Long>> columns = new HashMap<Locator, ColumnList<Long>>();
        final RangeBuilder rangeBuilder = new RangeBuilder().setStart(range.getStart()).setEnd(range.getStop());

        Timer.Context ctx = isBatch ? Instrumentation.getBatchReadTimerContext(CF) : Instrumentation.getReadTimerContext(CF);
        try {
            // We don't paginate this call. So we should make sure the number of reads is tolerable.
            // TODO: Think about paginating this call.
            OperationResult<Rows<Locator, Long>> query = keyspace
                    .prepareQuery(CF)
                    .getKeySlice(locators)
                    .withColumnRange(rangeBuilder.build())
                    .execute();

            for (Row<Locator, Long> row : query.getResult()) {
                columns.put(row.getKey(), row.getColumns());
            }
        } catch (ConnectionException e) {
            if (e instanceof NotFoundException) { // TODO: Not really sure what happens when one of the keys is not found.
                Instrumentation.markNotFound(CF);
            } else {
                if (isBatch) { Instrumentation.markBatchReadError(e); }
                else { Instrumentation.markReadError(e); }
            }
            log.warn((isBatch ? "Batch " : "") + " read query failed for column family " + CF.getName(), e);
        } finally {
            ctx.stop();
        }

        return columns;
    }

    // todo: this could be the basis for every rollup read method.
    // todo: A better interface may be to pass the serializer in instead of the class type.
    public <T extends Rollup> Points<T> getDataToRoll(Class<T> type, Locator locator, Range range, ColumnFamily<Locator, Long> cf) throws IOException {
        AbstractSerializer serializer = NumericSerializer.serializerFor(type);
        // special cases. :( the problem here is that the normal full res serializer returns Number instances instead of
        // SimpleNumber instances.
        // todo: this logic will only become more complicated. It needs to be in its own method and the serializer needs
        // to be known before we ever get to this method (see above comment).
        if (cf == CassandraModel.CF_METRICS_FULL) {
            serializer = NumericSerializer.simpleNumberSerializer;
        } else if ( cf == CassandraModel.CF_METRICS_PREAGGREGATED_FULL) {
            // consider a method for this.  getSerializer(CF, TYPE);
            if (type.equals(TimerRollup.class)) {
                serializer = NumericSerializer.timerRollupInstance;
            } else if (type.equals(SetRollup.class)) {
                serializer = NumericSerializer.setRollupInstance;
            } else if (type.equals(GaugeRollup.class)) {
                serializer = NumericSerializer.gaugeRollupInstance;
            } else if (type.equals(CounterRollup.class)) {
                serializer = NumericSerializer.CounterRollupInstance;
            } else {
                serializer = NumericSerializer.simpleNumberSerializer;
            }
        }
        
        ColumnList<Long> cols = getColumnsFromDB(locator, cf, range);
        Points<T> points = new Points<T>();
        try {
            for (Column<Long> col : cols) {
                points.add(new Points.Point<T>(col.getName(), (T)col.getValue(serializer)));
            }
        } catch (RuntimeException ex) {
            log.error("Problem deserializing data for " + locator + " (" + range + ") from " + cf.getName(), ex);
            throw new IOException(ex);
        }
        return points;
    }

    public static String getUnitString(Locator locator) {
        String unitString = Util.UNKNOWN;
        // Only grab units from cassandra, if we have to
        if (!Util.shouldUseESForUnits()) {
            try {
                unitString = metaCache.get(locator, MetricMetadata.UNIT.name().toLowerCase(), String.class);
            } catch (CacheException ex) {
                log.warn("Cache exception reading unitString from MetadataCache: ", ex);
            }
            if (unitString == null) {
                unitString = Util.UNKNOWN;
            }
        }

        return unitString;
    }

    public static String getType(Locator locator) {
        String type = null;
        try {
            type = metaCache.get(locator, MetricMetadata.TYPE.name().toLowerCase(), String.class);
        } catch (CacheException ex) {
            log.warn("Cache exception reading type from MetadataCache. ", ex);
        }
        if (type == null) {
            type = Util.UNKNOWN;
        }
        return type;
    }

    public MetricData getDatapointsForRange(Locator locator, Range range, Granularity gran) {
        try {
            Object type = metaCache.get(locator, dataTypeCacheKey);
            RollupType rollupType = RollupType.fromString(metaCache.get(locator, rollupTypeCacheKey));

            if (rollupType == null) {
                rollupType = RollupType.BF_BASIC;
            }
            if (type == null) {
                return getNumericOrStringRollupDataForRange(locator, range, gran, rollupType);
            }

            DataType metricType = new DataType((String) type);
            if (!DataType.isKnownMetricType(metricType)) {
                return getNumericOrStringRollupDataForRange(locator, range, gran, rollupType);
            }

            if (metricType.equals(DataType.STRING)) {
                gran = Granularity.FULL;
                return getStringMetricDataForRange(locator, range, gran);
            } else if (metricType.equals(DataType.BOOLEAN)) {
                gran = Granularity.FULL;
                return getBooleanMetricDataForRange(locator, range, gran);
            } else {
                return getNumericMetricDataForRange(locator, range, gran, rollupType, metricType);
            }

        } catch (CacheException e) {
            log.warn("Caught exception trying to find metric type from meta cache for locator " + locator.toString(), e);
            return getNumericOrStringRollupDataForRange(locator, range, gran, RollupType.BF_BASIC);
        }
    }

    // TODO: This should be the only method all output handlers call. We should be able to deprecate
    // other individual metric fetch methods once this gets in.
    public Map<Locator, MetricData> getDatapointsForRange(List<Locator> locators, Range range, Granularity gran) {
        ListMultimap<ColumnFamily, Locator> locatorsByCF =
                 ArrayListMultimap.create();
        Map<Locator, MetricData> results = new HashMap<Locator, MetricData>();

        for (Locator locator : locators) {
            try {
                RollupType rollupType = RollupType.fromString((String)
                            metaCache.get(locator, MetricMetadata.ROLLUP_TYPE.name().toLowerCase()));
                DataType dataType = getDataType(locator, MetricMetadata.TYPE.name().toLowerCase());
                ColumnFamily cf = CassandraModel.getColumnFamily(rollupType, dataType, gran);
                List<Locator> locs = locatorsByCF.get(cf);
                locs.add(locator);
            } catch (Exception e) {
                // pass for now. need metric to figure this stuff out.
            }
        }

         for (ColumnFamily CF : locatorsByCF.keySet()) {
            List<Locator> locs = locatorsByCF.get(CF);
            Map<Locator, ColumnList<Long>> metrics = getColumnsFromDB(locs, CF, range);
            // transform columns to MetricData
            for (Locator loc : metrics.keySet()) {
                MetricData data = transformColumnsToMetricData(loc, metrics.get(loc), gran);
                if (data != null && data.getData() != null) {
                    results.put(loc, data);
                }
            }
        }

        return results;
    }


    public MetricData getHistogramsForRange(Locator locator, Range range, Granularity granularity) throws IOException {
        if (!granularity.isCoarser(Granularity.FULL)) {
            throw new RuntimeException("Histograms are not available for granularity " + granularity.toString());
        }

        ColumnFamily cf = CassandraModel.getColumnFamily(HistogramRollup.class, granularity);
        Points<HistogramRollup> histogramRollupPoints = getDataToRoll(HistogramRollup.class, locator, range, cf);
        return new MetricData(histogramRollupPoints, getUnitString(locator), MetricData.Type.HISTOGRAM);
    }

    // Used for string metrics
    private MetricData getStringMetricDataForRange(Locator locator, Range range, Granularity gran) {
        Points<String> points = new Points<String>();
        ColumnList<Long> results = getColumnsFromDB(locator, CassandraModel.CF_METRICS_STRING, range);

        for (Column<Long> column : results) {
            try {
                points.add(new Points.Point<String>(column.getName(), column.getValue(StringSerializer.get())));
            } catch (RuntimeException ex) {
                log.error("Problem deserializing String data for " + locator + " (" + range + ") from " +
                        CassandraModel.CF_METRICS_STRING.getName(), ex);
            }
        }

        return new MetricData(points, getUnitString(locator), MetricData.Type.STRING);
    }

    private MetricData getBooleanMetricDataForRange(Locator locator, Range range, Granularity gran) {
        Points<Boolean> points = new Points<Boolean>();
        ColumnList<Long> results = getColumnsFromDB(locator, CassandraModel.CF_METRICS_STRING, range);

        for (Column<Long> column : results) {
            try {
                points.add(new Points.Point<Boolean>(column.getName(), column.getValue(BooleanSerializer.get())));
            } catch (RuntimeException ex) {
                log.error("Problem deserializing Boolean data for " + locator + " (" + range + ") from " +
                        CassandraModel.CF_METRICS_STRING.getName(), ex);
            }
        }

        return new MetricData(points, getUnitString(locator), MetricData.Type.BOOLEAN);
    }

    // todo: replace this with methods that pertain to type (which can be used to derive a serializer).
    private MetricData getNumericMetricDataForRange(Locator locator, Range range, Granularity gran, RollupType rollupType, DataType dataType) {
        ColumnFamily<Locator, Long> CF = CassandraModel.getColumnFamily(rollupType, dataType, gran);

        Points points = new Points();
        ColumnList<Long> results = getColumnsFromDB(locator, CF, range);
        
        // todo: this will not work when we cannot derive data type from granularity. we will need to know what kind of
        // data we are asking for and use a specific reader method.
        AbstractSerializer serializer = NumericSerializer.serializerFor(RollupType.classOf(rollupType, gran));

        for (Column<Long> column : results) {
            try {
                points.add(pointFromColumn(column, serializer));
            } catch (RuntimeException ex) {
                log.error("Problem deserializing data for " + locator + " (" + range + ") from " + CF.getName(), ex);
            }
        }

        return new MetricData(points, getUnitString(locator), MetricData.Type.NUMBER);
    }

    // gets called when we DO NOT know what the data type is (numeric, string, etc.)
    private MetricData getNumericOrStringRollupDataForRange(Locator locator, Range range, Granularity gran, RollupType rollupType) {
        Instrumentation.markScanAllColumnFamilies();

        final MetricData metricData = getNumericMetricDataForRange(locator, range, gran, rollupType, DataType.NUMERIC);

        if (metricData.getData().getPoints().size() > 0) {
            return metricData;
        }

        return getStringMetricDataForRange(locator, range, gran);
    }

    private MetricData transformColumnsToMetricData(Locator locator, ColumnList<Long> columns,
                                                                       Granularity gran) {
        try {
            RollupType rollupType = RollupType.fromString(metaCache.get(locator, rollupTypeCacheKey));
            DataType dataType = getDataType(locator, dataTypeCacheKey);
            String unit = getUnitString(locator);
            MetricData.Type outputType = MetricData.Type.from(rollupType, dataType);
            Points points = getPointsFromColumns(columns, rollupType, dataType, gran);
            MetricData data = new MetricData(points, unit, outputType);
            return data;
        } catch (Exception e) {
            return null;
        }
    }

    private DataType getDataType(Locator locator, String dataTypeCacheKey) throws CacheException{
        String meta = metaCache.get(locator, dataTypeCacheKey);
        if (meta != null) {
            return new DataType(meta);
        }
        return DataType.NUMERIC;
    }

    private Points getPointsFromColumns(ColumnList<Long> columnList, RollupType rollupType,
                                        DataType dataType, Granularity gran) {
        Points points = new Points();

        AbstractSerializer serializer = serializerFor(rollupType, dataType, gran);
        for (Column<Long> column : columnList) {
            points.add(pointFromColumn(column, serializer));
        }

        return points;
    }

    private Points.Point pointFromColumn(Column<Long> column, AbstractSerializer serializer) {
        if (serializer instanceof NumericSerializer.RawSerializer)
            return new Points.Point(column.getName(), new SimpleNumber(column.getValue(serializer)));
        else
            // this works for EVERYTHING except SimpleNumber.
        return new Points.Point(column.getName(), column.getValue(serializer));
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/io/AstyanaxRowCounterFunction.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io;
import com.google.common.base.Function;
import com.netflix.astyanax.model.Row;

import java.util.concurrent.atomic.AtomicLong;

// todo: This belongs in the test code. IntegrationTestBase depends on it though. So we have to wait until
// IntegrationTestBase is moved back into the test section of the repository.
/**
 * Simple function to counter the number of rows
 *
 * @author elandau
 *
 * @param <K>
 * @param <C>
 */
// Copy-pasted from astyanax 1.56.37, it doesn't exist in 1.56.32 which we use.
public class AstyanaxRowCounterFunction<K,C> implements Function<Row<K,C>, Boolean> {

    private final AtomicLong counter = new AtomicLong(0);

    @Override
    public Boolean apply(Row<K,C> input) {
        counter.incrementAndGet();
        return true;
    }

    public long getCount() {
        return counter.get();
    }

    public void reset() {
        counter.set(0);
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/io/AstyanaxWriter.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io;

import com.codahale.metrics.Gauge;
import com.codahale.metrics.Timer;
import com.codahale.metrics.MetricRegistry;
import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import com.google.common.collect.LinkedListMultimap;
import com.google.common.collect.Multimap;
import com.google.common.collect.Table;
import com.netflix.astyanax.ColumnListMutation;
import com.netflix.astyanax.Keyspace;
import com.netflix.astyanax.MutationBatch;
import com.netflix.astyanax.connectionpool.exceptions.ConnectionException;
import com.netflix.astyanax.model.ColumnFamily;
import com.netflix.astyanax.serializers.AbstractSerializer;
import com.rackspacecloud.blueflood.cache.SafetyTtlProvider;
import com.rackspacecloud.blueflood.cache.TenantTtlProvider;
import com.rackspacecloud.blueflood.io.serializers.NumericSerializer;
import com.rackspacecloud.blueflood.io.serializers.StringMetadataSerializer;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.service.*;
import com.rackspacecloud.blueflood.types.*;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.rackspacecloud.blueflood.utils.TimeValue;
import com.rackspacecloud.blueflood.utils.Util;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.TimeUnit;

public class AstyanaxWriter extends AstyanaxIO {
    private static final Logger log = LoggerFactory.getLogger(AstyanaxWriter.class);
    private static final AstyanaxWriter instance = new AstyanaxWriter();
    private static final Keyspace keyspace = getKeyspace();

    private static final TimeValue STRING_TTL = new TimeValue(730, TimeUnit.DAYS); // 2 years
    private static final int LOCATOR_TTL = 604800;  // in seconds (7 days)

    private static final String INSERT_ROLLUP_BATCH = "Rollup Batch Insert".intern();
    private boolean areStringMetricsDropped = Configuration.getInstance().getBooleanProperty(CoreConfig.STRING_METRICS_DROPPED);
    private List<String> tenantIdsKept = Configuration.getInstance().getListProperty(CoreConfig.TENANTIDS_TO_KEEP);
    private Set<String> keptTenantIdsSet = new HashSet<String>(tenantIdsKept);

    public static AstyanaxWriter getInstance() {
        return instance;
    }

    // todo: should be some other impl.
    private static TenantTtlProvider TTL_PROVIDER = SafetyTtlProvider.getInstance();
    

    // this collection is used to reduce the number of locators that get written.  Simply, if a locator has been
    // seen within the last 10 minutes, don't bother.
    private static final Cache<String, Boolean> insertedLocators = CacheBuilder.newBuilder().expireAfterAccess(10,
            TimeUnit.MINUTES).concurrencyLevel(16).build();

    static {
        Metrics.getRegistry().register(MetricRegistry.name(AstyanaxWriter.class, "Current Locators Count"),
                new Gauge<Long>() {
                    @Override
                    public Long getValue() {
                        return insertedLocators.size();
                    }
                });
    }

    private boolean shouldPersistStringMetric(Metric metric) {
        String tenantId = metric.getLocator().getTenantId();

        if(areStringMetricsDropped && !keptTenantIdsSet.contains(tenantId) ) {
            return false;
        }
        else {
            String currentValue = String.valueOf(metric.getMetricValue());
            final String lastValue = AstyanaxReader.getInstance().getLastStringValue(metric.getLocator());

            return lastValue == null || !currentValue.equals(lastValue);
        }
    }

    private boolean shouldPersist(Metric metric) {
        boolean shouldPersistMetric = true;
        try {
            final DataType metricType = metric.getDataType();
            if (metricType.equals(DataType.STRING) || metricType.equals(DataType.BOOLEAN)) {
                shouldPersistMetric = shouldPersistStringMetric(metric);
            }
        } catch (Exception e) {
            // If we hit any exception, just persist the metric
            shouldPersistMetric = true;
        }

        return shouldPersistMetric;
    }

    // insert a full resolution chunk of data. I've assumed that there will not be a lot of overlap (these will all be
    // single column updates).
    public void insertFull(Collection<Metric> metrics) throws ConnectionException {
        Timer.Context ctx = Instrumentation.getWriteTimerContext(CassandraModel.CF_METRICS_FULL);

        try {
            MutationBatch mutationBatch = keyspace.prepareMutationBatch();
            for (Metric metric: metrics) {
                final Locator locator = metric.getLocator();

                final boolean isString = metric.isString();
                final boolean isBoolean = metric.isBoolean();

                if (!shouldPersist(metric)) {
                    log.trace("Metric shouldn't be persisted, skipping insert", metric.getLocator().toString());
                    continue;
                }

                // key = shard
                // col = locator (acct + entity + check + dimension.metric)
                // value = <nothing>
                // do not do it for string or boolean metrics though.
                if (!AstyanaxWriter.isLocatorCurrent(locator)) {
                    if (!isString && !isBoolean && mutationBatch != null)
                        insertLocator(locator, mutationBatch);
                    AstyanaxWriter.setLocatorCurrent(locator);
                }

                insertMetric(metric, mutationBatch);
                Instrumentation.markFullResMetricWritten();
            }
            // insert it
            try {
                mutationBatch.execute();
            } catch (ConnectionException e) {
                Instrumentation.markWriteError(e);
                log.error("Connection exception during insertFull", e);
                throw e;
            }
        } finally {
            ctx.stop();
        }
    }

    // numeric only!
    private final void insertLocator(Locator locator, MutationBatch mutationBatch) {
        mutationBatch.withRow(CassandraModel.CF_METRICS_LOCATOR, (long) Util.getShard(locator.toString()))
                .putEmptyColumn(locator, LOCATOR_TTL);
    }

    private void insertMetric(Metric metric, MutationBatch mutationBatch) {
        final boolean isString = metric.isString();
        final boolean isBoolean = metric.isBoolean();

        if (isString || isBoolean) {
            metric.setTtl(STRING_TTL);
            String persist;
            if (isString) {
                persist = (String) metric.getMetricValue();
            } else { //boolean
                persist = String.valueOf(metric.getMetricValue());
            }
            mutationBatch.withRow(CassandraModel.CF_METRICS_STRING, metric.getLocator())
                    .putColumn(metric.getCollectionTime(), persist, metric.getTtlInSeconds());
        } else {
            try {
                mutationBatch.withRow(CassandraModel.CF_METRICS_FULL, metric.getLocator())
                        .putColumn(metric.getCollectionTime(),
                                metric.getMetricValue(),
                                NumericSerializer.serializerFor(Object.class),
                                metric.getTtlInSeconds());
            } catch (RuntimeException e) {
                log.error("Error serializing full resolution data", e);
            }
        }
    }

    public void writeMetadataValue(Locator locator, String metaKey, String metaValue) throws ConnectionException {
        Timer.Context ctx = Instrumentation.getWriteTimerContext(CassandraModel.CF_METRIC_METADATA);
        try {
            keyspace.prepareColumnMutation(CassandraModel.CF_METRIC_METADATA, locator, metaKey)
                    .putValue(metaValue, StringMetadataSerializer.get(), null)
                    .execute();
        } catch (ConnectionException e) {
            Instrumentation.markWriteError(e);
            log.error("Error writing Metadata Value", e);
            throw e;
        } finally {
            ctx.stop();
        }
    }

    public void writeMetadata(Table<Locator, String, String> metaTable) throws ConnectionException {
        ColumnFamily cf = CassandraModel.CF_METRIC_METADATA;
        Timer.Context ctx = Instrumentation.getBatchWriteTimerContext(cf);
        MutationBatch batch = keyspace.prepareMutationBatch();

        try {
            for (Locator locator : metaTable.rowKeySet()) {
                Map<String, String> metaRow = metaTable.row(locator);
                ColumnListMutation<String> mutation = batch.withRow(cf, locator);

                for (Map.Entry<String, String> meta : metaRow.entrySet()) {
                    mutation.putColumn(meta.getKey(), meta.getValue(), StringMetadataSerializer.get(), null);
                }
            }
            try {
                batch.execute();
            } catch (ConnectionException e) {
                Instrumentation.markWriteError(e);
                log.error("Connection exception persisting metadata", e);
                throw e;
            }
        } finally {
            ctx.stop();
        }
    }
    
    private static Multimap<Locator, IMetric> asMultimap(Collection<IMetric> metrics) {
        Multimap<Locator, IMetric> map = LinkedListMultimap.create();
        for (IMetric metric: metrics)
            map.put(metric.getLocator(), metric);
        return map;
    }
    
    // generic IMetric insertion. All other metric insertion methods could use this one.
    public void insertMetrics(Collection<IMetric> metrics, ColumnFamily cf) throws ConnectionException {
        Timer.Context ctx = Instrumentation.getWriteTimerContext(cf);
        Multimap<Locator, IMetric> map = asMultimap(metrics);
        MutationBatch batch = keyspace.prepareMutationBatch();
        try {
            for (Locator locator : map.keySet()) {
                ColumnListMutation<Long> mutation = batch.withRow(cf, locator);
                
                // we want to insert a locator only for non-string, non-boolean metrics. If there happen to be string or
                // boolean metrics mixed in with numeric metrics, we still want to insert a locator.  If all metrics
                // are boolean or string, we DO NOT want to insert a locator.
                boolean locatorInsertOk = false;
                
                for (IMetric metric : map.get(locator)) {
                    
                    boolean shouldPersist = true;
                    // todo: MetricsPersistenceOptimizerFactory interface needs to be retooled to accept IMetric
                    if (metric instanceof Metric) {
                        final boolean isString = DataType.isStringMetric(metric.getMetricValue());
                        final boolean isBoolean = DataType.isBooleanMetric(metric.getMetricValue());
                        
                        
                        if (!isString && !isBoolean)
                            locatorInsertOk = true;
                        shouldPersist = shouldPersist((Metric)metric);
                    } else {
                        locatorInsertOk = true;
                    }
                    
                    if (shouldPersist) {
                        mutation.putColumn(
                                metric.getCollectionTime(),
                                metric.getMetricValue(),
                                (AbstractSerializer) (NumericSerializer.serializerFor(metric.getMetricValue().getClass())),
                                metric.getTtlInSeconds());
                    }
                }
                
                if (!AstyanaxWriter.isLocatorCurrent(locator)) {
                    if (locatorInsertOk)
                        insertLocator(locator, batch);
                    AstyanaxWriter.setLocatorCurrent(locator);
                }
            }
            try {
                batch.execute();
            } catch (ConnectionException e) {
                Instrumentation.markWriteError(e);
                log.error("Connection exception persisting data", e);
                throw e;
            }
        } finally {
            ctx.stop();
        }
    }

    public void persistShardState(int shard, Map<Granularity, Map<Integer, UpdateStamp>> updates) throws ConnectionException {
        Timer.Context ctx = Instrumentation.getWriteTimerContext(CassandraModel.CF_METRICS_STATE);
        try {
            MutationBatch mutationBatch = keyspace.prepareMutationBatch();
            ColumnListMutation<SlotState> mutation = mutationBatch.withRow(CassandraModel.CF_METRICS_STATE, (long)shard);
            for (Map.Entry<Granularity, Map<Integer, UpdateStamp>> granEntry : updates.entrySet()) {
                Granularity g = granEntry.getKey();
                for (Map.Entry<Integer, UpdateStamp> entry : granEntry.getValue().entrySet()) {
                    // granularity,slot,state
                    SlotState slotState = new SlotState(g, entry.getKey(), entry.getValue().getState());
                    mutation.putColumn(slotState, entry.getValue().getTimestamp());
                    /*
                      Note: we used to set the timestamp of the column to entry.getValue().getTimestamp() * 1000 over here.
                      This block of code is dangerous. Consider you are getting out of order metrics M1 and M2, with collection times T1 and T2 with T2>T1, belonging to same slot
                      Assume M2 arrives first. The slot gets marked active and rolled up and the state is set as Rolled. Now, assume M1 arrives. We update the slot state to active,
                      set the slot timestamp to T1, and while persisting we set it, we set the column timestamp to be T1*1000, but because the T1 < T2, the new slot state will never
                      get reflected.
                     */
                }
            }
            if (!mutationBatch.isEmpty())
                try {
                    mutationBatch.execute();
                } catch (ConnectionException e) {
                    Instrumentation.markWriteError(e);
                    log.error("Error persisting shard state", e);
                    throw e;
                }
        } finally {
            ctx.stop();
        }
    }

    public static boolean isLocatorCurrent(Locator loc) {
        return insertedLocators.getIfPresent(loc.toString()) != null;
    }

    private static void setLocatorCurrent(Locator loc) {
        insertedLocators.put(loc.toString(), Boolean.TRUE);
    }

    public void insertRollups(ArrayList<SingleRollupWriteContext> writeContexts) throws ConnectionException {
        if (writeContexts.size() == 0) {
            return;
        }
        Timer.Context ctx = Instrumentation.getBatchWriteTimerContext(writeContexts.get(0).getDestinationCF());
        MutationBatch mb = keyspace.prepareMutationBatch();
        for (SingleRollupWriteContext writeContext : writeContexts) {
            Rollup rollup = writeContext.getRollup();
            int ttl;
            try {
                ttl = (int)TTL_PROVIDER.getTTL(
                    writeContext.getLocator().getTenantId(),
                    writeContext.getGranularity(),
                    writeContext.getRollup().getRollupType()).toSeconds();
            } catch (Exception ex) {
                log.warn(ex.getMessage(), ex);
                ttl = (int)SafetyTtlProvider.getInstance().getSafeTTL(
                        writeContext.getGranularity(),
                        writeContext.getRollup().getRollupType()).toSeconds();
            }
            AbstractSerializer serializer = NumericSerializer.serializerFor(rollup.getClass());
            try {
                mb.withRow(writeContext.getDestinationCF(), writeContext.getLocator())
                        .putColumn(writeContext.getTimestamp(),
                                rollup,
                                serializer,
                                ttl);
            } catch (RuntimeException ex) {
                // let's not let stupidness prevent the rest of this put.
                log.warn(String.format("Cannot save %s", writeContext.getLocator().toString()), ex);
            }
        }
        try {
            mb.execute();
        } catch (ConnectionException e) {
            Instrumentation.markWriteError(e);
            log.error("Error writing rollup batch", e);
            throw e;
        } finally {
            ctx.stop();
        }
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/io/Constants.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io;

import com.rackspacecloud.blueflood.utils.MetricHelper;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.jboss.netty.util.CharsetUtil;

import java.nio.charset.Charset;
import java.util.concurrent.TimeUnit;

public class Constants {
    
    public static final int VERSION_FIELD_OFFSET = 0;

    public static final byte VERSION_1_FULL_RES = 0;
    public static final byte VERSION_1_ROLLUP = 0;
    public static final byte VERSION_1_HISTOGRAM = 0;
    public static final byte VERSION_1_TIMER = 0;
    public static final byte VERSION_2_TIMER = 1;

    public static final byte VERSION_1_COUNTER_ROLLUP = 0;
    public static final byte VERSION_1_SET_ROLLUP = VERSION_1_ROLLUP; // don't change this.

    public static final int DOUBLE = (int) MetricHelper.Type.DOUBLE;
    public static final int I32 = (int) MetricHelper.Type.INT32;
    public static final int I64 = (int) MetricHelper.Type.INT64;
    public static final int STR = (int) MetricHelper.Type.STRING;
 
    public static final byte B_DOUBLE = (byte)DOUBLE;
    public static final byte B_I32 = (byte)I32;
    public static final byte B_I64 = (byte)I64;
    public static final byte B_STR = (byte)STR;

    public static final byte AVERAGE = 0;
    public static final byte VARIANCE = 1;
    public static final byte MIN = 2;
    public static final byte MAX = 3;

    public static final TimeValue STRING_SAFETY_TTL = new TimeValue(365, TimeUnit.DAYS);

    public static final int NUMBER_OF_SHARDS = 128;
    
    public static final int DEFAULT_SAMPLE_INTERVAL = 30; // seconds.

    // ensure that some yahoo did not set FullResSerializer.CUR_VERSION to an invalid value (for backwards compatibility
    // with old unversioned serializations).
    static {
        if (VERSION_1_FULL_RES == DOUBLE || VERSION_1_FULL_RES == I32 || VERSION_1_FULL_RES == I64 || VERSION_1_FULL_RES == STR)
            throw new RuntimeException("Invalid FullResSerializer.CUR_VERSION. Please increment until this exception does not happen.");
    }

    public static final Charset DEFAULT_CHARSET = CharsetUtil.UTF_8;

    private Constants() {}
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/io/Instrumentation.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io;

import com.codahale.metrics.Meter;
import com.codahale.metrics.MetricRegistry;
import com.codahale.metrics.Timer;
import com.netflix.astyanax.connectionpool.exceptions.ConnectionException;
import com.netflix.astyanax.connectionpool.exceptions.PoolTimeoutException;
import com.netflix.astyanax.model.ColumnFamily;
import com.rackspacecloud.blueflood.utils.Metrics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.management.MBeanServer;
import javax.management.ObjectName;
import java.lang.management.ManagementFactory;

public class Instrumentation implements InstrumentationMBean {
    private static final Logger log = LoggerFactory.getLogger(Instrumentation.class);
    private static ReadTimers readTimers = new ReadTimers();
    private static WriteTimers writeTimers = new WriteTimers();
    private static final Meter writeErrMeter;
    private static final Meter readErrMeter;
    private static final Meter batchReadErrMeter;

    // One-off meters
    private static final Meter scanAllColumnFamiliesMeter;
    private static final Meter allPoolsExhaustedException;
    private static final Meter fullResMetricWritten;

    static {
        Class kls = Instrumentation.class;
        writeErrMeter = Metrics.meter(kls, "writes", "Cassandra Write Errors");
        readErrMeter = Metrics.meter(kls, "reads", "Cassandra Read Errors");
        batchReadErrMeter = Metrics.meter(kls, "reads", "Batch Cassandra Read Errors");
        scanAllColumnFamiliesMeter = Metrics.meter(kls, "Scan all ColumnFamilies");
        allPoolsExhaustedException = Metrics.meter(kls, "All Pools Exhausted");
        fullResMetricWritten = Metrics.meter(kls, "Full Resolution Metrics Written");
            try {
                final MBeanServer mbs = ManagementFactory.getPlatformMBeanServer();
                final String name = String.format("com.rackspacecloud.blueflood.io:type=%s", Instrumentation.class.getSimpleName());
                final ObjectName nameObj = new ObjectName(name);
                mbs.registerMBean(new Instrumentation() { }, nameObj);
            } catch (Exception exc) {
                log.error("Unable to register mbean for " + Instrumentation.class.getSimpleName(), exc);
            }
    }

    private Instrumentation() {/* Used for JMX exposure */}

    public static Timer.Context getReadTimerContext(ColumnFamily queryCF) {
        return readTimers.getTimerContext(queryCF, false);
    }

    public static Timer.Context getBatchReadTimerContext(ColumnFamily queryCF) {
        return readTimers.getTimerContext(queryCF, true);
    }

    public static Timer.Context getWriteTimerContext(ColumnFamily queryCF) {
        return writeTimers.getTimerContext(queryCF, false);
    }

    public static Timer.Context getBatchWriteTimerContext(ColumnFamily queryCF) {
        return writeTimers.getTimerContext(queryCF, true);
    }

    // Most error tracking is done in InstrumentedConnectionPoolMonitor
    // However, some issues can't be properly tracked using that alone.
    // For example, there is no good way to differentiate (in the connectionpoolmonitor)
    // a PoolTimeoutException indicating that Astyanax has to look in another host-specific-pool
    // to find a connection from one indicating Astyanax already looked in every pool and is
    // going to bubble up the exception to our reader/writer
    private static void markReadError() {
        readErrMeter.mark();
    }

    public static void markBatchReadError(ConnectionException e) {
        batchReadErrMeter.mark();
        if (e instanceof PoolTimeoutException) {
            allPoolsExhaustedException.mark();
        }
    }

    public static void markReadError(ConnectionException e) {
        markReadError();
        if (e instanceof PoolTimeoutException) {
            allPoolsExhaustedException.mark();
        }
    }

    private static void markWriteError() {
        writeErrMeter.mark();
    }

    public static void markWriteError(ConnectionException e) {
        markWriteError();
        if (e instanceof PoolTimeoutException) {
            allPoolsExhaustedException.mark();
        }
    }

    private static class ReadTimers {
        public Timer.Context getTimerContext(ColumnFamily queryCF, boolean batch) {
            final String metricName = (batch ? MetricRegistry.name("batched-", queryCF.getName()) : queryCF.getName());

            final Timer timer = Metrics.timer(Instrumentation.class, "reads", metricName);
            return timer.time();
        }
    }

    private static class WriteTimers {
        public Timer.Context getTimerContext(ColumnFamily queryCF, boolean batch) {
            final String metricName = (batch ? MetricRegistry.name("batched", queryCF.getName()) : queryCF.getName());

            final Timer timer = Metrics.timer(Instrumentation.class, "writes", metricName);
            return timer.time();
        }
    }

    public static void markNotFound(ColumnFamily CF) {
        final Meter meter = Metrics.meter(Instrumentation.class, "reads", "Not Found", CF.getName());
        meter.mark();

    }

    public static void markScanAllColumnFamilies() {
        scanAllColumnFamiliesMeter.mark();
    }

    public static void markFullResMetricWritten() {
        fullResMetricWritten.mark();
    }
}

interface InstrumentationMBean {}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/io/InstrumentedConnectionPoolMonitor.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io;

import com.codahale.metrics.*;
import com.netflix.astyanax.connectionpool.ConnectionPoolMonitor;
import com.netflix.astyanax.connectionpool.Host;
import com.netflix.astyanax.connectionpool.HostConnectionPool;
import com.netflix.astyanax.connectionpool.HostStats;
import com.netflix.astyanax.connectionpool.exceptions.*;
import com.rackspacecloud.blueflood.utils.Metrics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class InstrumentedConnectionPoolMonitor implements ConnectionPoolMonitor {

    private static final Logger log = LoggerFactory.getLogger(InstrumentedConnectionPoolMonitor.class);
    private Meter operationFailureMeter  = new Meter();
    private Meter operationSuccessMeter  = new Meter();
    private Meter operationFailoverMeter = new Meter();
    private Meter notFoundMeter          = new Meter();

    private Meter connectionCreateMeter  = new Meter();
    private Meter connectionClosedMeter  = new Meter();
    private Meter connectionBorrowMeter  = new Meter();
    private Meter connectionReturnMeter  = new Meter();

    private Meter connectionCreateFailureMeter = new Meter();

    private Meter hostAddedMeter         = new Meter();
    private Meter hostRemovedMeter       = new Meter();
    private Meter hostDownMeter          = new Meter();
    private Meter hostReactivatedMeter   = new Meter();

    private Meter poolExhaustedMeter     = new Meter();
    private Meter operationTimeoutMeter  = new Meter();
    private Meter socketTimeoutMeter     = new Meter();
    private Meter noHostsMeter           = new Meter();

    private Meter unknownErrorMeter      = new Meter();
    private Meter badRequestMeter        = new Meter();
    private Meter interruptedMeter       = new Meter();
    private Meter transportErrorMeter    = new Meter();

    private Gauge<Long> busyConnections = new Gauge<Long>() {
        @Override
        public Long getValue() {
            return getNumBusyConnections();
        }
    };

    public InstrumentedConnectionPoolMonitor() {
        Metrics.getRegistry().registerAll(new ConnectionPoolMonitorStats());
    }

    private class ConnectionPoolMonitorStats implements MetricSet {
        @Override
        public Map<String, Metric> getMetrics() {
            Map<String, Metric> map = new HashMap<String, Metric>();
            Class kls = InstrumentedConnectionPoolMonitor.class; // readability

            map.put(MetricRegistry.name(kls, "Operation Result Failure"), operationFailureMeter);
            map.put(MetricRegistry.name(kls, "Operation Result Success"), operationSuccessMeter);
            map.put(MetricRegistry.name(kls, "Operation Result Failover"), operationFailoverMeter);
            map.put(MetricRegistry.name(kls, "Operation Result Not Found"), notFoundMeter);

            map.put(MetricRegistry.name(kls, "Connection Created"), connectionCreateMeter);
            map.put(MetricRegistry.name(kls, "Connection Closed"), connectionClosedMeter);
            map.put(MetricRegistry.name(kls, "Connection Borrowed"), connectionBorrowMeter);
            map.put(MetricRegistry.name(kls, "Connection Returned"), connectionReturnMeter);

            map.put(MetricRegistry.name(kls, "Connection Creation Failure"), connectionCreateFailureMeter);

            map.put(MetricRegistry.name(kls, "Host Added"), hostAddedMeter);
            map.put(MetricRegistry.name(kls, "Host Removed"), hostRemovedMeter);
            map.put(MetricRegistry.name(kls, "Host Down"), hostDownMeter);
            map.put(MetricRegistry.name(kls, "Host Reactivated"), hostReactivatedMeter);

            map.put(MetricRegistry.name(kls, "Exceptions Pool Exhausted"), poolExhaustedMeter);
            map.put(MetricRegistry.name(kls, "Exceptions Operation Timeout"), operationTimeoutMeter);
            map.put(MetricRegistry.name(kls, "Exceptions Socket Timeout"), socketTimeoutMeter);
            map.put(MetricRegistry.name(kls, "Exceptions No Hosts"), noHostsMeter);

            map.put(MetricRegistry.name(kls, "Exceptions Unknown Error"), unknownErrorMeter);
            map.put(MetricRegistry.name(kls, "Exceptions Bad Request"), badRequestMeter);
            map.put(MetricRegistry.name(kls, "Exceptions Interrupted"), interruptedMeter);
            map.put(MetricRegistry.name(kls, "Exceptions Transport Error"), transportErrorMeter);

            map.put(MetricRegistry.name(kls, "Busy Connections"), busyConnections);
            return Collections.unmodifiableMap(map);
        }
    }


    private void trackError(Host host, Exception reason) {
        if (reason instanceof PoolTimeoutException) {
            this.poolExhaustedMeter.mark();
        }
        else if (reason instanceof TimeoutException) {
            this.socketTimeoutMeter.mark();
        }
        else if (reason instanceof OperationTimeoutException) {
            this.operationTimeoutMeter.mark();
        }
        else if (reason instanceof BadRequestException) {
            this.badRequestMeter.mark();
        }
        else if (reason instanceof NoAvailableHostsException) {
            this.noHostsMeter.mark();
        }
        else if (reason instanceof InterruptedOperationException) {
            this.interruptedMeter.mark();
        }
        else if (reason instanceof HostDownException) {
            this.hostDownMeter.mark();
        }
        else if (reason instanceof TransportException) {
            this.transportErrorMeter.mark();
        }
        else {
            log.error(reason.toString(), reason);
            this.unknownErrorMeter.mark();
        }
    }

    @Override
    public void incOperationFailure(Host host, Exception reason) {
        if (reason instanceof NotFoundException) {
            this.notFoundMeter.mark();
            return;
        }

        this.operationFailureMeter.mark();
        trackError(host, reason);
    }

    public long getOperationFailureCount() {
        return this.operationFailureMeter.getCount();
    }

    @Override
    public void incOperationSuccess(Host host, long latency) {
        this.operationSuccessMeter.mark();
    }

    public long getOperationSuccessCount() {
        return this.operationSuccessMeter.getCount();
    }

    @Override
    public void incConnectionCreated(Host host) {
        this.connectionCreateMeter.mark();
    }

    public long getConnectionCreatedCount() {
        return this.connectionCreateMeter.getCount();
    }

    @Override
    public void incConnectionClosed(Host host, Exception reason) {
        this.connectionClosedMeter.mark();
    }

    public long getConnectionClosedCount() {
        return this.connectionClosedMeter.getCount();
    }

    @Override
    public void incConnectionCreateFailed(Host host, Exception reason) {
        this.connectionCreateFailureMeter.mark();
    }

    public long getConnectionCreateFailedCount() {
        return this.connectionCreateFailureMeter.getCount();
    }

    @Override
    public void incConnectionBorrowed(Host host, long delay) {
        this.connectionBorrowMeter.mark();
    }

    public long getConnectionBorrowedCount() {
        return this.connectionBorrowMeter.getCount();
    }

    @Override
    public void incConnectionReturned(Host host) {
        this.connectionReturnMeter.mark();
    }

    public long getConnectionReturnedCount() {
        return this.connectionReturnMeter.getCount();
    }

    public long getPoolExhaustedTimeoutCount() {
        return this.poolExhaustedMeter.getCount();
    }

    @Override
    public long getSocketTimeoutCount() {
        return this.socketTimeoutMeter.getCount();
    }

    public long getOperationTimeoutCount() {
        return this.operationTimeoutMeter.getCount();
    }

    @Override
    public void incFailover(Host host, Exception reason) {
        this.operationFailoverMeter.mark();
        trackError(host, reason);
    }

    @Override
    public long getFailoverCount() {
        return this.operationFailoverMeter.getCount();
    }

    @Override
    public void onHostAdded(Host host, HostConnectionPool<?> pool) {
        log.info("AddHost: " + host.getHostName());
        this.hostAddedMeter.mark();
    }

    @Override
    public long getHostAddedCount() {
        return this.hostAddedMeter.getCount();
    }

    @Override
    public void onHostRemoved(Host host) {
        log.info("RemoveHost: " + host.getHostName());
        this.hostRemovedMeter.mark();
    }

    @Override
    public long getHostRemovedCount() {
        return this.hostRemovedMeter.getCount();
    }

    @Override
    public void onHostDown(Host host, Exception reason) {
        log.info("Host down: " + host.getIpAddress() + " because ", reason);
        this.hostDownMeter.mark();
    }

    @Override
    public long getHostDownCount() {
        return this.hostDownMeter.getCount();
    }

    @Override
    public void onHostReactivated(Host host, HostConnectionPool<?> pool) {
        log.info("Reactivating " + host.getHostName());
        this.hostReactivatedMeter.mark();
    }

    public long getHostReactivatedCount() {
        return this.hostReactivatedMeter.getCount();
    }

    @Override
    public long getNoHostCount() {
        return this.noHostsMeter.getCount();
    }

    @Override
    public long getUnknownErrorCount() {
        return this.unknownErrorMeter.getCount();
    }

    @Override
    public long getInterruptedCount() {
        return this.interruptedMeter.getCount();
    }

    public long getTransportErrorCount() {
        return this.transportErrorMeter.getCount();
    }

    @Override
    public long getBadRequestCount() {
        return this.badRequestMeter.getCount();
    }

    public long getNumBusyConnections() {
        return this.connectionBorrowMeter.getCount() - this.connectionReturnMeter.getCount();
    }

    public long getNumOpenConnections() {
        return this.connectionCreateMeter.getCount() - this.connectionClosedMeter.getCount();
    }

    @Override
    public long notFoundCount() {
        return this.notFoundMeter.getCount();
    }

    @Override
    public long getHostCount() {
        return getHostAddedCount() - getHostRemovedCount();
    }

    public long getHostActiveCount() {
        return hostAddedMeter.getCount() - hostRemovedMeter.getCount() + hostReactivatedMeter.getCount() - hostDownMeter.getCount();
    }

    public String toString() {
        // Build the complete status string
        return new StringBuilder()
                .append("InstrumentedConnectionPoolMonitor(")
                .append("Connections[" )
                .append( "open="       ).append(getNumOpenConnections())
                .append(",busy="       ).append(getNumBusyConnections())
                .append(",create="     ).append(connectionCreateMeter.getCount())
                .append(",close="      ).append(connectionClosedMeter.getCount())
                .append(",failed="     ).append(connectionCreateFailureMeter.getCount())
                .append(",borrow="     ).append(connectionBorrowMeter.getCount())
                .append(",return=").append(connectionReturnMeter.getCount())
                .append("], Operations[")
                .append("success=").append(operationSuccessMeter.getCount())
                .append(",failure=").append(operationFailureMeter.getCount())
                .append(",optimeout=").append(operationTimeoutMeter.getCount())
                .append(",timeout=").append(socketTimeoutMeter.getCount())
                .append(",failover=").append(operationFailoverMeter.getCount())
                .append(",nohosts=").append(noHostsMeter.getCount())
                .append(",unknown=").append(unknownErrorMeter.getCount())
                .append(",interrupted=").append(interruptedMeter.getCount())
                .append(",exhausted="  ).append(poolExhaustedMeter.getCount())
                .append(",transport="  ).append(transportErrorMeter.getCount())
                .append("], Hosts[")
                .append("add=").append(hostAddedMeter.getCount())
                .append(",remove=").append(hostRemovedMeter.getCount())
                .append(",down=").append(hostDownMeter.getCount())
                .append(",reactivate=").append(hostReactivatedMeter.getCount())
                .append(",active=").append(getHostActiveCount())
                .append("])").toString();
    }

    @Override
    public Map<Host, HostStats> getHostStats() {
        throw new UnsupportedOperationException("Not supported");
    }
}



File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/io/IntegrationTestBase.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io;

import com.google.common.cache.Cache;
import com.netflix.astyanax.MutationBatch;
import com.netflix.astyanax.connectionpool.exceptions.ConnectionException;
import com.netflix.astyanax.model.ColumnFamily;
import com.netflix.astyanax.recipes.reader.AllRowsReader;
import com.netflix.astyanax.serializers.StringSerializer;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.service.SingleRollupWriteContext;
import com.rackspacecloud.blueflood.types.*;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.junit.After;
import org.junit.AfterClass;
import org.junit.Assert;
import org.junit.Before;
import org.mockito.internal.util.reflection.Whitebox;

import java.lang.reflect.Method;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

// todo: This was moved into a source repo becuase tests in core and cm-specific depend on it.
// We need to figure out the right maven codes to add blueflood-core test-jar stuff as a test dependency to cm-specific.
public class IntegrationTestBase {

    public static class AstyanaxTester extends AstyanaxIO {
        // This is kind of gross and has serious room for improvement.
        protected void truncate(String cf) {
            int tries = 3;
            while (tries-- > 0) {
                try {
                    getKeyspace().truncateColumnFamily(cf);
                } catch (ConnectionException ex) {
                    System.err.println("Connection problem, yo. remaining tries: " + tries + " " + ex.getMessage());
                    try { Thread.sleep(1000L); } catch (Exception ewww) {}
                }
            }
        }

        protected final void assertNumberOfRows(String cf, long rows) throws Exception {
            ColumnFamily<String, String> columnFamily = ColumnFamily.newColumnFamily(cf, StringSerializer.get(), StringSerializer.get());
            AstyanaxRowCounterFunction<String, String> rowCounter = new AstyanaxRowCounterFunction<String, String>();
            boolean result = new AllRowsReader.Builder<String, String>(getKeyspace(), columnFamily)
                    .withColumnRange(null, null, false, 0)
                    .forEachRow(rowCounter)
                    .build()
                    .call();
            Assert.assertEquals(rows, rowCounter.getCount());
        }

        public ColumnFamily<Locator, Long> getStringCF() {
            return CassandraModel.CF_METRICS_STRING;
        }

        public ColumnFamily<Locator, Long> getFullCF() {
            return CassandraModel.CF_METRICS_FULL;
        }

        public ColumnFamily<Long, Locator> getLocatorCF() {
            return CassandraModel.CF_METRICS_LOCATOR;
        }

        public MutationBatch createMutationBatch() {
            return getKeyspace().prepareMutationBatch();
        }
    }

    private static final char[] STRING_SEEDS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890_".toCharArray();
    private static final Random rand = new Random(System.currentTimeMillis());
    protected static final ConcurrentHashMap<Locator, String> locatorToUnitMap = new ConcurrentHashMap<Locator, String>();

    protected final void assertNumberOfRows(String cf, int rows) throws Exception {
        new AstyanaxTester().assertNumberOfRows(cf, rows);
    }

    @Before
    public void setUp() throws Exception {
        // really short lived connections for tests!
        AstyanaxTester truncator = new AstyanaxTester();
        for (ColumnFamily cf : CassandraModel.getAllColumnFamilies())
            truncator.truncate(cf.getName());
    }
    
    @After
    public void clearInterruptedThreads() throws Exception {
        // clear all interrupts! Why do we do this? The best I can come up with is that the test harness (junit) is
        // interrupting threads. One test in particular is very bad about this: RollupRunnableIntegrationTest.
        // Nothing in that test looks particularly condemnable other than the use of Metrics timers in the rollup
        // itself.  Anyway... this should clear up the travis build failures.
        //
        // Debugging this was an exceptional pain in the neck.  It turns out that there can be a fair amount of time
        // between when a thread is interrupted and an InterruptedException gets thrown. Minutes in our case. This is
        // because the AstyanaxWriter singleton keeps its threadpools between test invocations.
        //
        // The semantics of Thread.interrupt() are such that calling it only sets an interrupt flag to true, but doesn't
        // really interrupt the thread.  Subsequent calls to Thread.sleep() end up throwing the exception because the
        // thread is in an interrupted state.
        Method clearInterruptPrivate = Thread.class.getDeclaredMethod("isInterrupted", boolean.class);
        clearInterruptPrivate.setAccessible(true);
        for (Thread thread : Thread.getAllStackTraces().keySet()) {
            if (thread.isInterrupted()) {
                System.out.println(String.format("Clearing interrupted thread: " + thread.getName()));
                clearInterruptPrivate.invoke(thread, true);
            }
        }
    }

    @After
    public void tearDown() throws Exception {
        // meh
    }

    protected Metric writeMetric(String name, Object value) throws Exception {
        final List<Metric> metrics = new ArrayList<Metric>();
        final Locator locator = Locator.createLocatorFromPathComponents("acctId", name);
        Metric metric = new Metric(locator, value, System.currentTimeMillis(),
                new TimeValue(1, TimeUnit.DAYS), "unknown");
        metrics.add(metric);
        AstyanaxWriter.getInstance().insertFull(metrics);
        Cache<String, Boolean> insertedLocators = (Cache<String, Boolean>) Whitebox.getInternalState(AstyanaxWriter.getInstance(), "insertedLocators");
        insertedLocators.invalidateAll();

        return metric;
    }

    protected List<Metric> makeRandomIntMetrics(int count) {
        final String tenantId = "ac" + randString(8);
        List<Metric> metrics = new ArrayList<Metric>();
        final long now = System.currentTimeMillis();

        for (int i = 0; i < count; i++) {
            final Locator locator = Locator.createLocatorFromPathComponents(tenantId, "met" + randString(8));
            metrics.add(getRandomIntMetric(locator, now - 10000000));
        }

        return metrics;
    }

    protected static String randString(int length) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < length; i++)
            sb.append(STRING_SEEDS[rand.nextInt(STRING_SEEDS.length)]);
        return sb.toString();
    }

    protected int getRandomIntMetricValue() {
        return rand.nextInt();
    }

    protected String getRandomStringMetricValue() {
        return "str" + String.valueOf(getRandomIntMetricValue());
    }

    protected Metric getRandomIntMetric(final Locator locator, long timestamp) {
        locatorToUnitMap.putIfAbsent(locator, UNIT_ENUM.values()[new Random().nextInt(UNIT_ENUM.values().length)].unit);
        return new Metric(locator, getRandomIntMetricValue(), timestamp, new TimeValue(1, TimeUnit.DAYS), locatorToUnitMap.get(locator));
    }

    protected Metric getRandomStringmetric(final Locator locator, long timestamp) {
        locatorToUnitMap.putIfAbsent(locator, UNIT_ENUM.UNKNOWN.unit);
        return new Metric(locator, getRandomStringMetricValue(), timestamp, new TimeValue(1, TimeUnit.DAYS), locatorToUnitMap.get(locator));
    }

    protected static <T> Metric makeMetric(final Locator locator, long timestamp, T value) {
        return new Metric(locator, value, timestamp, new TimeValue(1, TimeUnit.DAYS), "unknown");
    }

    private enum UNIT_ENUM {
        SECS("seconds"),
        MSECS("milliseconds"),
        BYTES("bytes"),
        KILOBYTES("kilobytes"),
        UNKNOWN("unknown");

        private String unit;

        private UNIT_ENUM(String unitValue) {
            this.unit = unitValue;
        }

        private String getUnit() {
            return unit;
        }
    }

    protected void generateRollups(Locator locator, long from, long to, Granularity destGranularity) throws Exception {
        if (destGranularity == Granularity.FULL) {
            throw new Exception("Can't roll up to FULL");
        }

        ColumnFamily<Locator, Long> destCF;
        ArrayList<SingleRollupWriteContext> writeContexts = new ArrayList<SingleRollupWriteContext>();
        for (Range range : Range.rangesForInterval(destGranularity, from, to)) {
            destCF = CassandraModel.getColumnFamily(BasicRollup.class, destGranularity);
            Points<SimpleNumber> input = AstyanaxReader.getInstance().getDataToRoll(SimpleNumber.class, locator, range,
                    CassandraModel.CF_METRICS_FULL);
            BasicRollup basicRollup = BasicRollup.buildRollupFromRawSamples(input);
            writeContexts.add(new SingleRollupWriteContext(basicRollup, locator, destGranularity, destCF, range.start));

            destCF = CassandraModel.getColumnFamily(HistogramRollup.class, destGranularity);
            HistogramRollup histogramRollup = HistogramRollup.buildRollupFromRawSamples(input);
            writeContexts.add(new SingleRollupWriteContext(histogramRollup, locator, destGranularity, destCF, range.start));
        }

        AstyanaxWriter.getInstance().insertRollups(writeContexts);
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/io/serializers/HistogramSerializer.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io.serializers;

import com.bigml.histogram.Bin;
import com.bigml.histogram.SimpleTarget;
import com.google.protobuf.CodedInputStream;
import com.google.protobuf.CodedOutputStream;
import com.netflix.astyanax.serializers.AbstractSerializer;
import com.rackspacecloud.blueflood.exceptions.SerializationException;
import com.rackspacecloud.blueflood.io.Constants;
import com.rackspacecloud.blueflood.types.HistogramRollup;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.Collection;

public class HistogramSerializer extends AbstractSerializer<HistogramRollup> {
    private static final HistogramSerializer INSTANCE = new HistogramSerializer();

    public static HistogramSerializer get() {
        return INSTANCE;
    }

    @Override
    public ByteBuffer toByteBuffer(HistogramRollup histogramRollup) {
        final Collection<Bin<SimpleTarget>> bins = filterZeroCountBins(histogramRollup.getBins());
        byte[] buf = new byte[computeSizeOfHistogramRollupOnDisk(bins)];
        try {
            serializeBins(bins, buf);
            return ByteBuffer.wrap(buf);
        } catch (Exception ex) {
            throw new RuntimeException(ex);
        }
    }

    @Override
    public HistogramRollup fromByteBuffer(ByteBuffer byteBuffer) {
        CodedInputStream in = CodedInputStream.newInstance(byteBuffer.array());

        try {
            byte version = in.readRawByte();
            switch (version) {
                case Constants.VERSION_1_HISTOGRAM:
                    return deserializeV1Histogram(in);
                default:
                    throw new SerializationException("Unexpected serialization version");
            }
        } catch (IOException ex) {
            throw new RuntimeException(ex) ;
        }
    }

    private HistogramRollup deserializeV1Histogram(CodedInputStream in) throws IOException {
        final Collection<Bin<SimpleTarget>> bins = new ArrayList<Bin<SimpleTarget>>();

        while (!in.isAtEnd()) {
            long count = in.readRawVarint64();
            double mean = in.readDouble();
            Bin<SimpleTarget> bin = new Bin<SimpleTarget>(mean, count, SimpleTarget.TARGET);
            bins.add(bin);
        }

        return new HistogramRollup(bins);
    }

    private void serializeBins(Collection<Bin<SimpleTarget>> bins, byte[] buf) throws IOException {
        CodedOutputStream protobufOut = CodedOutputStream.newInstance(buf);

        protobufOut.writeRawByte(Constants.VERSION_1_HISTOGRAM);

        for (Bin<SimpleTarget> bin : bins) {
            protobufOut.writeRawVarint64((long) bin.getCount());
            protobufOut.writeDoubleNoTag(bin.getMean());
        }
    }

    private int computeSizeOfHistogramRollupOnDisk(Collection<Bin<SimpleTarget>> bins) {
        int size = 1; // for version

        for (Bin<SimpleTarget> bin : bins) {
            size += CodedOutputStream.computeDoubleSizeNoTag((bin.getMean()));
            size += CodedOutputStream.computeRawVarint64Size((long) bin.getCount());
        }

        return size;
    }

    private Collection<Bin<SimpleTarget>> filterZeroCountBins(Collection<Bin<SimpleTarget>> bins) {
        Collection<Bin<SimpleTarget>> filtered = new ArrayList<Bin<SimpleTarget>>();
        for (Bin<SimpleTarget> bin : bins) {
            if (bin.getCount() > 0)  {
                filtered.add(bin);
            }
        }

        return filtered;
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/io/serializers/LocatorSerializer.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io.serializers;

import com.rackspacecloud.blueflood.types.Locator;
import com.google.common.base.Charsets;
import com.netflix.astyanax.serializers.AbstractSerializer;
import com.netflix.astyanax.serializers.StringSerializer;

import java.nio.ByteBuffer;
import java.nio.charset.Charset;

public class LocatorSerializer extends AbstractSerializer<Locator>{
    private static final LocatorSerializer instance = new LocatorSerializer();
    private static final Charset charset = Charsets.UTF_8;


    public static LocatorSerializer get() {
        return instance;
    }

    @Override
    public ByteBuffer toByteBuffer(Locator locator) {
        return StringSerializer.get().toByteBuffer(locator.toString());
    }

    @Override
    public Locator fromByteBuffer(ByteBuffer byteBuffer) {
        if (byteBuffer == null) {
            return null;
        }
        return Locator.createLocatorFromDbKey(charset.decode(byteBuffer).toString());
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/io/serializers/NumericSerializer.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io.serializers;

import com.codahale.metrics.Histogram;
import com.google.common.annotations.VisibleForTesting;
import com.google.protobuf.CodedInputStream;
import com.google.protobuf.CodedOutputStream;
import com.netflix.astyanax.serializers.AbstractSerializer;
import com.rackspacecloud.blueflood.exceptions.SerializationException;
import com.rackspacecloud.blueflood.exceptions.UnexpectedStringSerializationException;
import com.rackspacecloud.blueflood.io.Constants;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.rackspacecloud.blueflood.types.AbstractRollupStat;
import com.rackspacecloud.blueflood.types.CounterRollup;
import com.rackspacecloud.blueflood.types.GaugeRollup;
import com.rackspacecloud.blueflood.types.HistogramRollup;
import com.rackspacecloud.blueflood.types.BasicRollup;
import com.rackspacecloud.blueflood.types.SimpleNumber;
import com.rackspacecloud.blueflood.types.SetRollup;
import com.rackspacecloud.blueflood.types.TimerRollup;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.lang.reflect.Field;
import java.nio.ByteBuffer;
import java.util.Map;

import static com.rackspacecloud.blueflood.io.Constants.*;

public class NumericSerializer {
    // NumericSerializer can be used with Rollup and full resolution metrics.
    
    private static final boolean DUMP_BAD_BUFFERS = System.getProperty("DUMP_BAD_BUFFERS") != null;

    public static final AbstractSerializer<SimpleNumber> simpleNumberSerializer = new SimpleNumberSerializer();
    private static AbstractSerializer<Object> fullInstance = new RawSerializer();
    private static AbstractSerializer<BasicRollup> basicRollupInstance = new BasicRollupSerializer();
    public static AbstractSerializer<TimerRollup> timerRollupInstance = new TimerRollupSerializer();
    public static AbstractSerializer<SetRollup> setRollupInstance = new SetRollupSerializer();
    public static AbstractSerializer<GaugeRollup> gaugeRollupInstance = new GaugeRollupSerializer();
    public static AbstractSerializer<CounterRollup> CounterRollupInstance = new CounterRollupSerializer();
    
    private static Histogram fullResSize = Metrics.histogram(NumericSerializer.class, "Full Resolution Metric Size");
    private static Histogram rollupSize = Metrics.histogram(NumericSerializer.class, "Rollup Metric Size");
    private static Histogram CounterRollupSize = Metrics.histogram(NumericSerializer.class, "Counter Gauge Metric Size");
    private static Histogram SetRollupSize = Metrics.histogram(NumericSerializer.class, "Set Metric Size");
    private static Histogram timerRollupSize = Metrics.histogram(NumericSerializer.class, "Timer Metric Size");

    static class Type {
        static final byte B_ROLLUP = (byte)'r';
        static final byte B_FLOAT_AS_DOUBLE = (byte)'f';
        static final byte B_ROLLUP_STAT = (byte)'t';
        static final byte B_COUNTER = (byte)'C';
        static final byte B_TIMER = (byte)'T';
        static final byte B_SET = (byte)'S';
        static final byte B_GAUGE = (byte)'G';
    }
    
    /** return a serializer for a specific type */
    public static <T> AbstractSerializer<T> serializerFor(Class<T> type) {
        if (type == null)
            throw new RuntimeException("serializable type cannot be null",
                    new SerializationException("serializable type cannot be null"));
        else if (type.equals(String.class))
            throw new RuntimeException("We don't serialize strings anymore",
                    new SerializationException("We don't serialize strings anymore"));
        
        if (type.equals(BasicRollup.class))
            return (AbstractSerializer<T>) basicRollupInstance;
        else if (type.equals(TimerRollup.class))
            return (AbstractSerializer<T>)timerRollupInstance;
        else if (type.equals(HistogramRollup.class))
            return (AbstractSerializer<T>) HistogramSerializer.get();
        else if (type.equals(CounterRollup.class))
            return (AbstractSerializer<T>) CounterRollupInstance;
        else if (type.equals(GaugeRollup.class))
            return (AbstractSerializer<T>)gaugeRollupInstance;
        else if (type.equals(SetRollup.class))
            return (AbstractSerializer<T>)setRollupInstance;
        else if (type.equals(SimpleNumber.class))
            return (AbstractSerializer<T>)fullInstance;
        else if (type.equals(Integer.class))
            return (AbstractSerializer<T>)fullInstance;
        else if (type.equals(Long.class))
            return (AbstractSerializer<T>)fullInstance;
        else if (type.equals(Double.class))
            return (AbstractSerializer<T>)fullInstance;
        else if (type.equals(Float.class))
                return (AbstractSerializer<T>)fullInstance;
        else if (type.equals(byte[].class))
            return (AbstractSerializer<T>)fullInstance;
        else if (type.equals(Object.class))
            return (AbstractSerializer<T>)fullInstance;
        else
            return (AbstractSerializer<T>)fullInstance;   
    }

    private static void serializeRollup(BasicRollup basicRollup, byte[] buf) throws IOException {
        rollupSize.update(buf.length);
        CodedOutputStream protobufOut = CodedOutputStream.newInstance(buf);
        serializeRollup(basicRollup, protobufOut);
    }
    
    private static void serializeRollup(BasicRollup basicRollup, CodedOutputStream protobufOut) throws IOException {
        protobufOut.writeRawByte(Constants.VERSION_1_ROLLUP);
        protobufOut.writeRawVarint64(basicRollup.getCount());          // stat count

        if (basicRollup.getCount() > 0) {
            putRollupStat(basicRollup.getAverage(), protobufOut);
            putRollupStat(basicRollup.getVariance(), protobufOut);
            putRollupStat(basicRollup.getMinValue(), protobufOut);
            putRollupStat(basicRollup.getMaxValue(), protobufOut);
        }
    }

    private static void putRollupStat(AbstractRollupStat stat, CodedOutputStream protobufOut) throws IOException {
        protobufOut.writeRawByte(stat.getStatType());   // stat type
        protobufOut.writeRawByte(stat.isFloatingPoint() ? Constants.B_DOUBLE : Constants.B_I64);

        if (stat.isFloatingPoint()) {
            protobufOut.writeDoubleNoTag(stat.toDouble());
        } else {
            protobufOut.writeRawVarint64(stat.toLong());
        }
    }
    
    // put out a number prefaced only by a type.
    private static void putUnversionedDoubleOrLong(Number number, CodedOutputStream out) throws IOException {
        if (number instanceof Double) {
            out.writeRawByte(Constants.B_DOUBLE);
            out.writeDoubleNoTag(number.doubleValue());
        } else {
            out.writeRawByte(Constants.B_I64);
            out.writeRawVarint64(number.longValue());
        }
    }
    
    // read out a type-specified number.
    public static Number getUnversionedDoubleOrLong(CodedInputStream in) throws IOException {
        byte type = in.readRawByte();
        if (type == Constants.B_DOUBLE)
            return in.readDouble();
        else
            return in.readRawVarint64();
    }

    private static void serializeFullResMetric(Object o, byte[] buf) throws IOException {
        CodedOutputStream protobufOut = CodedOutputStream.newInstance(buf);
        byte type = typeOf(o);
        fullResSize.update(sizeOf(o, type));
        protobufOut.writeRawByte(Constants.VERSION_1_FULL_RES);

        switch (type) {
            case Constants.B_I32:
                protobufOut.writeRawByte(type);
                protobufOut.writeRawVarint32((Integer) o);
                break;
            case Constants.B_I64:
                protobufOut.writeRawByte(type);
                protobufOut.writeRawVarint64((Long) o);
                break;
            case Constants.B_DOUBLE:
                protobufOut.writeRawByte(type);
                protobufOut.writeDoubleNoTag((Double) o);
                break;
            case Type.B_FLOAT_AS_DOUBLE:
                protobufOut.writeRawByte(Constants.B_DOUBLE);
                protobufOut.writeDoubleNoTag(((Float) o).doubleValue());
                break;
            default:
                throw new SerializationException(String.format("Cannot serialize %s", o.getClass().getName()));
        }
    }

    private static int sizeOf(Object o, byte type) 
      throws IOException {
        return sizeOf(o, type, VERSION_2_TIMER);
    }

    private static int sizeOf(Object o, byte type, byte timerVersion) 
      throws IOException {
        int sz = 0;
        switch (type) {
            case Constants.B_I32:
                sz += 1 + 1; // version + type.
                sz += CodedOutputStream.computeRawVarint32Size((Integer)o);
                break;
            case Constants.B_I64:
                sz += 1 + 1; // version + type.
                sz += CodedOutputStream.computeRawVarint64Size((Long)o);
                break;
            case Constants.B_DOUBLE:
                sz += 1 + 1; // version + type.
                sz += CodedOutputStream.computeDoubleSizeNoTag((Double)o);
                break;
            case Type.B_FLOAT_AS_DOUBLE:
                sz += 1 + 1; // version + type.
                sz += CodedOutputStream.computeDoubleSizeNoTag(((Float)o).doubleValue());
                break;
            case Type.B_ROLLUP:
                sz += 1; // version
                BasicRollup basicRollup = (BasicRollup)o;
                sz += CodedOutputStream.computeRawVarint64Size(basicRollup.getCount());
                if (basicRollup.getCount() > 0) {
                    sz += sizeOf(basicRollup.getAverage(), Type.B_ROLLUP_STAT);
                    sz += sizeOf(basicRollup.getVariance(), Type.B_ROLLUP_STAT);
                    sz += sizeOf(basicRollup.getMinValue(), Type.B_ROLLUP_STAT);
                    sz += sizeOf(basicRollup.getMaxValue(), Type.B_ROLLUP_STAT);
                }
                break;
            case Type.B_SET:
                sz += 1; // version
                SetRollup setRollup = (SetRollup)o;
                sz += CodedOutputStream.computeRawVarint32Size(setRollup.getCount());
                for (Integer i : setRollup.getHashes()) {
                    sz += CodedOutputStream.computeRawVarint32Size(i);
                }
                break;
            case Type.B_ROLLUP_STAT:
                sz = 1 + 1; // type + isFP.
                AbstractRollupStat stat = (AbstractRollupStat)o;
                sz += stat.isFloatingPoint() ?
                        CodedOutputStream.computeDoubleSizeNoTag(stat.toDouble()) :
                        CodedOutputStream.computeRawVarint64Size(stat.toLong());
                return sz;
            case Type.B_TIMER:
                sz += 1; // version
                TimerRollup rollup = (TimerRollup)o;
                if (timerVersion == VERSION_1_TIMER) {
                    sz += CodedOutputStream.computeRawVarint64Size((long) rollup.getSum());
                } else if (timerVersion == VERSION_2_TIMER) {

                    sz += CodedOutputStream.computeDoubleSizeNoTag(rollup.getSum());
                } else {
                    throw new SerializationException(String.format("Unexpected serialization version: %d", (int)timerVersion));                    
                }
                sz += CodedOutputStream.computeRawVarint64Size(rollup.getCount());
                sz += CodedOutputStream.computeDoubleSizeNoTag(rollup.getRate());
                sz += CodedOutputStream.computeRawVarint32Size(rollup.getSampleCount());
                sz += sizeOf(rollup.getAverage(), Type.B_ROLLUP_STAT);
                sz += sizeOf(rollup.getMaxValue(), Type.B_ROLLUP_STAT);
                sz += sizeOf(rollup.getMinValue(), Type.B_ROLLUP_STAT);
                sz += sizeOf(rollup.getVariance(), Type.B_ROLLUP_STAT);
                
                Map<String, TimerRollup.Percentile> percentiles = rollup.getPercentiles();
                sz += CodedOutputStream.computeRawVarint32Size(rollup.getPercentiles().size());
                for (Map.Entry<String, TimerRollup.Percentile> entry : percentiles.entrySet()) {
                    sz += CodedOutputStream.computeStringSizeNoTag(entry.getKey());
                    Number[] pctComponents = new Number[] {
                            entry.getValue().getMean(),
                    };
                    for (Number num : pctComponents) {
                        sz += 1; // type.
                        if (num instanceof Long || num instanceof Integer) {
                            sz += CodedOutputStream.computeRawVarint64Size(num.longValue());
                        } else if (num instanceof Double || num instanceof Float) {
                            sz += CodedOutputStream.computeDoubleSizeNoTag(num.doubleValue());
                        }
                    }
                }
                return sz;
                
            case Type.B_GAUGE:
                // just like rollup up until a point.
                sz += sizeOf(o, Type.B_ROLLUP);
                
                // here's where it gets different.
                GaugeRollup gauge = (GaugeRollup)o;
                sz += CodedOutputStream.computeRawVarint64Size(gauge.getTimestamp());
                sz += 1; // type of latest value.
                if (gauge.getLatestNumericValue() instanceof Long || gauge.getLatestNumericValue() instanceof Integer)
                    sz += CodedOutputStream.computeRawVarint64Size(gauge.getLatestNumericValue().longValue());
                else if (gauge.getLatestNumericValue() instanceof Double || gauge.getLatestNumericValue() instanceof Float)
                    sz += CodedOutputStream.computeDoubleSizeNoTag(gauge.getLatestNumericValue().doubleValue());
                return sz;
                
            case Type.B_COUNTER:
                CounterRollup counter = (CounterRollup)o;
                sz += 1; // version + rollup type.
                sz += 1; // numeric type.
                if (counter.getCount() instanceof Long || counter.getCount() instanceof Integer)
                    sz += CodedOutputStream.computeRawVarint64Size(counter.getCount().longValue());
                else if (counter.getCount() instanceof Double || counter.getCount() instanceof Float)
                    sz += CodedOutputStream.computeDoubleSizeNoTag(counter.getCount().doubleValue());
                sz += CodedOutputStream.computeDoubleSizeNoTag(counter.getRate());
                sz += CodedOutputStream.computeRawVarint32Size(counter.getSampleCount());
                return sz;
            default:
                throw new IOException("Unexpected type: " + type);
        }
        return sz;
    }
    
    private static void serializeCounterRollup(CounterRollup rollup, byte[] buf) throws IOException {
        CodedOutputStream out = CodedOutputStream.newInstance(buf);
        CounterRollupSize.update(buf.length);
        out.writeRawByte(Constants.VERSION_1_COUNTER_ROLLUP);
        putUnversionedDoubleOrLong(rollup.getCount(), out);
        out.writeDoubleNoTag(rollup.getRate());
        out.writeRawVarint32(rollup.getSampleCount());
    }
    
    private static CounterRollup deserializeV1CounterRollup(CodedInputStream in) throws IOException {
        Number value = getUnversionedDoubleOrLong(in);
        double rate = in.readDouble();
        int sampleCount = in.readRawVarint32();
        return new CounterRollup().withCount(value.longValue()).withRate(rate).withSampleCount(sampleCount);
    }
    
    private static void serializeSetRollup(SetRollup rollup, byte[] buf) throws IOException {
        CodedOutputStream out = CodedOutputStream.newInstance(buf);
        SetRollupSize.update(buf.length);
        out.writeRawByte(Constants.VERSION_1_SET_ROLLUP);
        out.writeRawVarint32(rollup.getCount());
        for (Integer i : rollup.getHashes()) {
            out.writeRawVarint32(i);
        }
    }
    
    private static SetRollup deserializeV1SetRollup(CodedInputStream in) throws IOException {
        int count = in.readRawVarint32();
        SetRollup rollup = new SetRollup();
        while (count-- > 0) {
            rollup = rollup.withObject(in.readRawVarint32());
        }
        return rollup;
    }

    private static void serializeTimer(TimerRollup rollup, byte[] buf, byte timerVersion) throws IOException {
        CodedOutputStream out = CodedOutputStream.newInstance(buf);
        timerRollupSize.update(buf.length);
        out.writeRawByte(timerVersion);
        
        // sum, count, countps, avg, max, min, var
        if (timerVersion == VERSION_1_TIMER) {
            out.writeRawVarint64((long)rollup.getSum());
        } else if (timerVersion == VERSION_2_TIMER) {
            out.writeDoubleNoTag(rollup.getSum());
        } else {
            throw new SerializationException(String.format("Unexpected serialization version: %d", (int)timerVersion));                    
        }

        out.writeRawVarint64(rollup.getCount());
        out.writeDoubleNoTag(rollup.getRate());
        out.writeRawVarint32(rollup.getSampleCount());
        putRollupStat(rollup.getAverage(), out);
        putRollupStat(rollup.getMaxValue(), out);
        putRollupStat(rollup.getMinValue(), out);
        putRollupStat(rollup.getVariance(), out);
        
        // percentiles.
        Map<String, TimerRollup.Percentile> percentiles = rollup.getPercentiles();
        out.writeRawVarint32(percentiles.size());
        for (Map.Entry<String, TimerRollup.Percentile> entry : percentiles.entrySet()) {
            out.writeStringNoTag(entry.getKey());
            putUnversionedDoubleOrLong(entry.getValue().getMean(), out);
        }
    }
    
    private static TimerRollup deserializeTimer(CodedInputStream in, byte timerVersion) throws IOException {
        // note: type and version have already been read.
        final double sum;
        if (timerVersion == VERSION_1_TIMER) {
             sum = in.readRawVarint64();
        } else if (timerVersion == VERSION_2_TIMER) {
             sum = in.readDouble();
        } else {
            throw new SerializationException(String.format("Unexpected serialization version: %d", (int)timerVersion));                    
        }


        final long count = in.readRawVarint64();
        final double countPs = in.readDouble();
        final int sampleCount = in.readRawVarint32();
        
        BasicRollup statBucket = new BasicRollup();
        
        byte statType;
        AbstractRollupStat stat;
        
        // average
        statType = in.readRawByte();
        stat = getStatFromRollup(statType, statBucket);
        setStat(stat, in);
        // max
        statType = in.readRawByte();
        stat = getStatFromRollup(statType, statBucket);
        setStat(stat, in);
        // min
        statType = in.readRawByte();
        stat = getStatFromRollup(statType, statBucket);
        setStat(stat, in);
        // var
        statType = in.readRawByte();
        stat = getStatFromRollup(statType, statBucket);
        setStat(stat, in);
        
        TimerRollup rollup = new TimerRollup()
                .withSum(sum)
                .withCount(count)
                .withCountPS(countPs)
                .withSampleCount(sampleCount)
                .withAverage(statBucket.getAverage())
                .withMaxValue(statBucket.getMaxValue())
                .withMinValue(statBucket.getMinValue())
                .withVariance(statBucket.getVariance());
        
        int numPercentiles = in.readRawVarint32();
        for (int i = 0; i < numPercentiles; i++) {
            String name = in.readString();
            Number mean = getUnversionedDoubleOrLong(in);
            rollup.setPercentile(name, mean);
        }
        
        return rollup;
    }
    
    private static void serializeGauge(GaugeRollup rollup, byte[] buf) throws IOException {
        rollupSize.update(buf.length);
        CodedOutputStream protobufOut = CodedOutputStream.newInstance(buf);
        serializeRollup(rollup, protobufOut);
        protobufOut.writeRawVarint64(rollup.getTimestamp());
        putUnversionedDoubleOrLong(rollup.getLatestNumericValue(), protobufOut);
    }
    
    private static GaugeRollup deserializeV1Gauge(CodedInputStream in) throws IOException {
        BasicRollup basic = deserializeV1Rollup(in);
        long timestamp = in.readRawVarint64();
        Number lastValue = getUnversionedDoubleOrLong(in);
        return GaugeRollup.fromBasicRollup(basic, timestamp, lastValue);
    }
    
    private static byte typeOf(Object o) throws IOException {
        if (o instanceof Integer)
            return Constants.B_I32;
        else if (o instanceof Long)
            return Constants.B_I64;
        else if (o instanceof Double)
            return Constants.B_DOUBLE;
        else if (o instanceof Float)
            return Type.B_FLOAT_AS_DOUBLE;
        else if (o instanceof AbstractRollupStat)
            return Type.B_ROLLUP_STAT;
        else if (o instanceof TimerRollup)
            return Type.B_TIMER;
        else if (o instanceof GaugeRollup)
            return Type.B_GAUGE;
        else if (o instanceof SetRollup)
            return Type.B_SET;
        else if (o instanceof BasicRollup)
            return Type.B_ROLLUP;
        else if (o instanceof CounterRollup)
            return Type.B_COUNTER;
        else
            throw new SerializationException("Unexpected type: " + o.getClass().getName());
    }

    private static BasicRollup deserializeV1Rollup(CodedInputStream in) throws IOException {
        final BasicRollup basicRollup = new BasicRollup();
        final long count = in.readRawVarint64();
        basicRollup.setCount(count);

        if (count <= 0) {
            return basicRollup;
        }

        for (int i = 0; i < BasicRollup.NUM_STATS; i++) {
            byte statType = in.readRawByte();
            AbstractRollupStat stat = getStatFromRollup(statType, basicRollup);
            if (stat == null) {
                throw new IOException("V1 BasicRollup: Unable to determine stat of type " + (int)statType);
            }
            setStat(stat, in);
        }
        return basicRollup;
    }
    
    // todo: this should return an instance instead of populate one, but will require some refatoring of 
    // deserializeV1Rollup().
    private static void setStat(AbstractRollupStat stat, CodedInputStream in) throws IOException {
        byte metricValueType = in.readRawByte();
        switch (metricValueType) {
            case Constants.I64:
                stat.setLongValue(in.readRawVarint64());
                break;
            case Constants.B_DOUBLE:
                stat.setDoubleValue(in.readDouble());
                break;
            default:
                throw new IOException("Unsupported metric value type " + (int)metricValueType);
        }
    }
    
    private static Object deserializeSimpleMetric(CodedInputStream in) throws IOException {
        byte metricValueType = in.readRawByte() /* type field */;
        switch (metricValueType) {
            case Constants.I32:
                return in.readRawVarint32();
            case Constants.I64:
                return in.readRawVarint64();
            case Constants.DOUBLE:
                return in.readDouble();
            case Constants.STR:
                throw new UnexpectedStringSerializationException("We don't rollup strings");
            default:
                throw new SerializationException(String.format("Unexpected raw metric type=%s for full res " +
                    "metric", (char)metricValueType));
        }
    }
    
    // handy utility to dump bad buffers when they are encountered. e.g. during serialization debugging.
    private static void dumpBufferUnsafe(CodedInputStream in) {
        if (DUMP_BAD_BUFFERS) {
            try {
                Field bufferField = in.getClass().getDeclaredField("buffer");
                bufferField.setAccessible(true);
                byte[] buffer = (byte[])bufferField.get(in);
                OutputStream out = new FileOutputStream(File.createTempFile(String.format("bf_bad_buffer_%d_%d", System.currentTimeMillis(), System.nanoTime()), ".bin"));
                out.write(buffer);
                out.close();
            } catch (Throwable th) {
                // ignore.
            }
        }
    }

    private static AbstractRollupStat getStatFromRollup(byte statType, BasicRollup basicRollup) {
        switch (statType) {
            case Constants.AVERAGE:
                return basicRollup.getAverage();
            case Constants.VARIANCE:
                return basicRollup.getVariance();
            case Constants.MIN:
                return basicRollup.getMinValue();
            case Constants.MAX:
                return basicRollup.getMaxValue();
            default:
                return null;
        }
    }
    
    public static class RawSerializer extends AbstractSerializer<Object> {
        @Override
        public ByteBuffer toByteBuffer(Object o) {
            try {
                byte type = typeOf(o);
                byte[] buf = new byte[sizeOf(o, type)];
    
                serializeFullResMetric(o, buf);
                
                ByteBuffer out = ByteBuffer.wrap(buf);
                return out;
    
            } catch(IOException e) {
                throw new RuntimeException(e);
            }
        }

        @Override
        public Object fromByteBuffer(ByteBuffer byteBuffer) {
            CodedInputStream in = CodedInputStream.newInstance(byteBuffer.array());
            try {
                byte version = in.readRawByte();
                if (version != VERSION_1_FULL_RES && version != VERSION_1_ROLLUP) {
                    throw new SerializationException(String.format("Unexpected serialization version: %d",
                            (int)version));
                }
                return deserializeSimpleMetric(in);
            } catch (Exception e) {
                throw new RuntimeException("Deserialization Failure", e);
            }
        }
    }
    
    // composes a raw serializer.
    private static class SimpleNumberSerializer extends AbstractSerializer<SimpleNumber> {
        private static final RawSerializer rawSerde = new RawSerializer();
        
        @Override
        public ByteBuffer toByteBuffer(SimpleNumber obj) {
            return rawSerde.toByteBuffer(obj);
        }

        @Override
        public SimpleNumber fromByteBuffer(ByteBuffer byteBuffer) {
            return new SimpleNumber(rawSerde.fromByteBuffer(byteBuffer));
        }
    }
    
    private static class BasicRollupSerializer extends AbstractSerializer<BasicRollup> {
        @Override
        public ByteBuffer toByteBuffer(BasicRollup o) {
            try {
                byte type = typeOf(o);
                byte[] buf = new byte[sizeOf(o, type)];
                serializeRollup(o, buf);
                return ByteBuffer.wrap(buf);
            } catch(IOException e) {
                throw new RuntimeException(e);
            }
        }

        @Override
        public BasicRollup fromByteBuffer(ByteBuffer byteBuffer) {
            CodedInputStream in = CodedInputStream.newInstance(byteBuffer.array());
            try {
                byte version = in.readRawByte();
                if (version != VERSION_1_FULL_RES && version != VERSION_1_ROLLUP) {
                    throw new SerializationException(String.format("Unexpected serialization version: %d",
                            (int)version));
                }
                return deserializeV1Rollup(in);
            } catch (Exception e) {
                throw new RuntimeException("Deserialization Failure", e);
            }
        }
    }
    
    public static class TimerRollupSerializer extends AbstractSerializer<TimerRollup> {
        @Override
        public ByteBuffer toByteBuffer(TimerRollup o) {
            try {
                byte type = typeOf(o);
                byte[] buf = new byte[sizeOf(o, type, VERSION_2_TIMER)];
                serializeTimer(o, buf, VERSION_2_TIMER);
                return ByteBuffer.wrap(buf);
            } catch (IOException ex) {
                throw new RuntimeException(ex);
            }
        }

        @VisibleForTesting
        public ByteBuffer toByteBufferWithV1Serialization(TimerRollup o) {
            try {
                byte type = typeOf(o);
                byte[] buf = new byte[sizeOf(o, type, VERSION_1_TIMER)];
                serializeTimer(o, buf, VERSION_1_TIMER);
                return ByteBuffer.wrap(buf);
            } catch (IOException ex) {
                throw new RuntimeException(ex);
            }
        }

        @Override
        public TimerRollup fromByteBuffer(ByteBuffer byteBuffer) {
            CodedInputStream in = CodedInputStream.newInstance(byteBuffer.array());
            try {
                byte version = in.readRawByte();
                return deserializeTimer(in, version);
            } catch (Exception ex) {
                throw new RuntimeException(ex);
            }
        }
    }
    
    public static class SetRollupSerializer extends AbstractSerializer<SetRollup> {
        
        @Override
        public ByteBuffer toByteBuffer(SetRollup obj) {
            try {
                byte type = typeOf(obj);
                byte[] buf = new byte[sizeOf(obj, type)];
                serializeSetRollup(obj, buf);
                return ByteBuffer.wrap(buf);
            } catch (IOException ex) {
                throw new RuntimeException(ex);
            }
        }

        @Override
        public SetRollup fromByteBuffer(ByteBuffer byteBuffer) {
            CodedInputStream in = CodedInputStream.newInstance(byteBuffer.array());
            try {
                byte version = in.readRawByte();
                if (version != VERSION_1_SET_ROLLUP)
                    throw new SerializationException(String.format("Unexpected serialization version: %d", (int)version));
                return deserializeV1SetRollup(in);
            } catch (Exception ex) {
                throw new RuntimeException(ex);
            }
        }
    }
    
    public static class GaugeRollupSerializer extends AbstractSerializer<GaugeRollup> {
        @Override
        public ByteBuffer toByteBuffer(GaugeRollup o) {
            try {
                byte type = typeOf(o);
                byte[] buf = new byte[sizeOf(o, type)];
                serializeGauge(o, buf);
                return ByteBuffer.wrap(buf);
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        }

        @Override
        public GaugeRollup fromByteBuffer(ByteBuffer byteBuffer) {
            CodedInputStream in = CodedInputStream.newInstance(byteBuffer.array());
            try {
                byte version = in.readRawByte();
                if (version != VERSION_1_ROLLUP)
                    throw new SerializationException(String.format("Unexpected serialization version: %d", (int)version));
                return deserializeV1Gauge(in);
            } catch (Exception e) {
                throw new RuntimeException("Deserialization Failure", e);
            }
        }
    }
    
    // for now let's try to get away with a single serializer for all single value rollups. We'll still encode specific
    // types so we can differentiate.
    public static class CounterRollupSerializer extends AbstractSerializer<CounterRollup> {
        @Override
        public ByteBuffer toByteBuffer(CounterRollup obj) {
            try {
                byte type = typeOf(obj);
                byte[] buf = new byte[sizeOf(obj, type)];
                serializeCounterRollup(obj, buf);
                return ByteBuffer.wrap(buf);
            } catch (IOException ex) {
                throw new RuntimeException(ex);
            }
        }

        @Override
        public CounterRollup fromByteBuffer(ByteBuffer byteBuffer) {
            CodedInputStream in = CodedInputStream.newInstance(byteBuffer.array());
            try {
                byte version = in.readRawByte();
                if (version != VERSION_1_COUNTER_ROLLUP)
                    throw new SerializationException(String.format("Unexpected serialization version: %d", (int)version));
                return deserializeV1CounterRollup(in);
            } catch (Exception ex) {
                throw new RuntimeException(ex);
            }
        }
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/io/serializers/SlotStateSerializer.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io.serializers;

import com.netflix.astyanax.serializers.AbstractSerializer;
import com.netflix.astyanax.serializers.StringSerializer;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.service.SlotState;
import com.rackspacecloud.blueflood.service.UpdateStamp;

import java.nio.ByteBuffer;

public class SlotStateSerializer extends AbstractSerializer<SlotState> {
    private static final SlotStateSerializer INSTANCE = new SlotStateSerializer();

    public static SlotStateSerializer get() {
        return INSTANCE;
    }

    @Override
    public ByteBuffer toByteBuffer(SlotState state) {
        Granularity gran = state.getGranularity();
        String stringRep = new StringBuilder().append(gran == null ? "null" : gran.name())
                .append(",").append(state.getSlot())
                .append(",").append(state == null ? "null" : state.getState().code())
                .toString();

        return StringSerializer.get().toByteBuffer(stringRep);
    }

    @Override
    public SlotState fromByteBuffer(ByteBuffer byteBuffer) {
        String stringRep = StringSerializer.get().fromByteBuffer(byteBuffer);
        Granularity g = granularityFromStateCol(stringRep);
        Integer slot = slotFromStateCol(stringRep);
        UpdateStamp.State state = stateFromCode(stateCodeFromStateCol(stringRep));

        return new SlotState(g, slot, state);
    }

    protected static Granularity granularityFromStateCol(String s) {
        String field = s.split(",", -1)[0];
        for (Granularity g : Granularity.granularities())
            if (g.name().startsWith(field))
                return g;
        return null;
    }

    protected static int slotFromStateCol(String s) { return Integer.parseInt(s.split(",", -1)[1]); }
    protected static String stateCodeFromStateCol(String s) { return s.split(",", -1)[2]; }

    protected static UpdateStamp.State stateFromCode(String stateCode) {
        if (stateCode.equals(UpdateStamp.State.Rolled.code())) {
            return UpdateStamp.State.Rolled;
        } else {
            return UpdateStamp.State.Active;
        }
    }

}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/io/serializers/StringMetadataSerializer.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io.serializers;

import com.google.protobuf.CodedInputStream;
import com.google.protobuf.CodedOutputStream;
import com.netflix.astyanax.serializers.AbstractSerializer;

import java.io.IOException;
import java.nio.ByteBuffer;

public class StringMetadataSerializer extends AbstractSerializer<String> {
    private static final StringMetadataSerializer INSTANCE = new StringMetadataSerializer();
    private static final byte STRING = 4; // History: this used to support multiple types.
    // However, we never actually used that functionality, and it duplicated a lot of logic
    // as is contained in NumericSerializer, without actually being in a compatible [de]serialization format.
    // TODO: re-add non-str functionality in a way that does not involve as much code duplication and format incompatibility

    public static StringMetadataSerializer get() {
        return INSTANCE;
    }

    @Override
    public ByteBuffer toByteBuffer(String o) {
        try {
            byte[] buf = new byte[computeBufLength(o)];
            CodedOutputStream out = CodedOutputStream.newInstance(buf);
            writeToOutputStream(o, out);
            return ByteBuffer.wrap(buf);
        } catch (IOException e) {
            throw new RuntimeException("Serialization problems", e);
        }
    }

    // writes object to CodedOutputStream.
    private static void writeToOutputStream(Object obj, CodedOutputStream out) throws IOException {
        out.writeRawByte(STRING);
        out.writeStringNoTag((String)obj);
    }

    // figure out how much space it will take to encode an object. this makes it so that we only allocate one buffer
    // during encode.
    private static int computeBufLength(String obj) throws IOException {
        return 1 + CodedOutputStream.computeStringSizeNoTag(obj); // 1 for type
    }

    @Override
    public String fromByteBuffer(ByteBuffer byteBuffer) {
        CodedInputStream is = CodedInputStream.newInstance(byteBuffer.array());
        try {
            byte type = is.readRawByte();
            if (type == STRING) {
                return is.readString();
            } else {
                throw new IOException("Unexpected first byte. Expected '4' (string). Got '" + type + "'.");
            }
        } catch (IOException e) {
            throw new RuntimeException("IOException during deserialization", e);
        }
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/outputs/formats/MetricData.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.formats;

import com.rackspacecloud.blueflood.types.DataType;
import com.rackspacecloud.blueflood.types.Points;
import com.rackspacecloud.blueflood.types.RollupType;

public class MetricData {
    private final Points data;
    private String unit;
    private final Type type;

    public MetricData(Points points, String unit, Type type) {
        this.data = points;
        this.unit = unit;
        this.type = type;
    }

    public Points getData() {
        return data;
    }

    public String getUnit() {
        return unit;
    }

    public String getType() {
        return type.toString();
    }

    public void setUnit(String unit) { this.unit = unit; }

    public enum Type {
        NUMBER("number"),
        BOOLEAN("boolean"),
        STRING("string"),
        HISTOGRAM("histogram");

        private Type(String s) {
            this.name = s;
        }

        private String name;

        @Override
        public String toString() {
            return name;
        }

        public static Type from(RollupType rollupType, DataType dataType) {
            // We no longer store datatype metadata for Numeric datatypes
            if (dataType == null) {
                return NUMBER;
            }

            if (rollupType == null) {
                rollupType = RollupType.BF_BASIC;
            }

            if (dataType.equals(DataType.STRING)) {
                return STRING;
            } else if (dataType.equals(DataType.BOOLEAN)) {
                return BOOLEAN;
            } else {
                if (rollupType == RollupType.BF_HISTOGRAMS) {
                    return HISTOGRAM;
                }

                return NUMBER;
            }
        }
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/outputs/handlers/MetricDataQueryInterface.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.handlers;

import com.rackspacecloud.blueflood.types.Resolution;

public interface MetricDataQueryInterface<T> {
    public T GetDataByPoints(String tenantId, String metric, long from, long to, int points) throws Exception;

    public T GetDataByResolution(String tenantId, String metric, long from, long to, Resolution resolution) throws Exception;
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/outputs/handlers/RollupHandler.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.handlers;

import com.codahale.metrics.Histogram;
import com.codahale.metrics.Meter;
import com.codahale.metrics.Timer;
import com.google.common.util.concurrent.Futures;
import com.google.common.util.concurrent.ListenableFuture;
import com.google.common.util.concurrent.ListeningExecutorService;
import com.google.common.util.concurrent.MoreExecutors;
import com.rackspacecloud.blueflood.concurrent.ThreadPoolBuilder;
import com.rackspacecloud.blueflood.io.AstyanaxReader;
import com.rackspacecloud.blueflood.io.DiscoveryIO;
import com.rackspacecloud.blueflood.io.SearchResult;
import com.rackspacecloud.blueflood.outputs.formats.MetricData;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.service.Configuration;
import com.rackspacecloud.blueflood.service.CoreConfig;
import com.rackspacecloud.blueflood.types.*;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.rackspacecloud.blueflood.utils.QueryDiscoveryModuleLoader;
import com.rackspacecloud.blueflood.utils.TimeValue;
import com.rackspacecloud.blueflood.utils.Util;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.*;

public class RollupHandler {
    private static final Logger log = LoggerFactory.getLogger(RollupHandler.class);

    protected final Meter rollupsByPointsMeter = Metrics.meter(RollupHandler.class, "BF-API", "Get rollups by points");
    protected final Meter rollupsByGranularityMeter = Metrics.meter(RollupHandler.class, "BF-API", "Get rollups by gran");
    protected final Meter rollupsRepairEntireRange = Metrics.meter(RollupHandler.class, "BF-API", "Rollups repaired - entire range");
    protected final Meter rollupsRepairedLeft = Metrics.meter(RollupHandler.class, "BF-API", "Rollups repaired - left");
    protected final Meter rollupsRepairedRight = Metrics.meter(RollupHandler.class, "BF-API", "Rollups repaired - right");
    protected final Meter rollupsRepairEntireRangeEmpty = Metrics.meter(RollupHandler.class, "BF-API", "Rollups repaired - entire range - no data");
    protected final Meter rollupsRepairedLeftEmpty = Metrics.meter(RollupHandler.class, "BF-API", "Rollups repaired - left - no data");
    protected final Meter rollupsRepairedRightEmpty = Metrics.meter(RollupHandler.class, "BF-API", "Rollups repaired - right - no data");
    protected static final Timer metricsFetchTimer = Metrics.timer(RollupHandler.class, "Get metrics from db");
    protected static final Timer metricsFetchTimerMPlot = Metrics.timer(RollupHandler.class, "Get metrics from db - mplot");
    protected static final Timer rollupsCalcOnReadTimer = Metrics.timer(RollupHandler.class, "Rollups calculation on read");
    protected static final Timer rollupsCalcOnReadTimerMPlot = Metrics.timer(RollupHandler.class, "Rollups calculation on read - mplot");
    protected final Histogram numFullPointsReturned = Metrics.histogram(RollupHandler.class, "Full res points returned");
    protected final Histogram numRollupPointsReturned = Metrics.histogram(RollupHandler.class, "Rollup points returned");
    protected final Histogram numHistogramPointsReturned = Metrics.histogram(RollupHandler.class, "Histogram points returned");
    private static final Meter exceededQueryTimeout = Metrics.meter(RollupHandler.class, "Batched Metrics Query Duration Exceeded Timeout");
    private static final Histogram queriesSizeHist = Metrics.histogram(RollupHandler.class, "Total queries");

    private static final boolean ROLLUP_REPAIR = Configuration.getInstance().getBooleanProperty(CoreConfig.REPAIR_ROLLUPS_ON_READ);
    private ExecutorService ESUnitExecutor = null;
    private ListeningExecutorService rollupsOnReadExecutor = null;
    /*
      Timeout for rollups on read applicable only when operations are done async. for sync rollups on read
      it will be the astyanax operation timeout.
      TODO: Hard-coded for now, make configurable if need be
     */
    private TimeValue rollupOnReadTimeout = new TimeValue(10, TimeUnit.SECONDS);

    public RollupHandler() {
        if (Util.shouldUseESForUnits()) {
            // The number of threads getting used for ES_UNIT_THREADS, should at least be equal netty worker threads
            int ESthreadCount = Configuration.getInstance().getIntegerProperty(CoreConfig.ES_UNIT_THREADS);
            ESUnitExecutor = new ThreadPoolBuilder().withUnboundedQueue()
                    .withCorePoolSize(ESthreadCount)
                    .withMaxPoolSize(ESthreadCount).withName("Rolluphandler ES executors").build();
        }
        if (!Configuration.getInstance().getBooleanProperty(CoreConfig.TURN_OFF_RR_MPLOT)) {
            ThreadPoolExecutor rollupsOnReadExecutors = new ThreadPoolBuilder().withUnboundedQueue()
                    .withCorePoolSize(Configuration.getInstance().getIntegerProperty(CoreConfig.ROLLUP_ON_READ_THREADS))
                    .withMaxPoolSize(Configuration.getInstance().getIntegerProperty(CoreConfig.ROLLUP_ON_READ_THREADS))
                    .withName("Rollups on Read Executors").build();
            rollupsOnReadExecutor = MoreExecutors.listeningDecorator(rollupsOnReadExecutors);
        }
    }

    private enum plotTimers {
        SPLOT_TIMER(metricsFetchTimer),
        MPLOT_TIMER(metricsFetchTimerMPlot);
        private Timer timer;

        private plotTimers(Timer timer) {
            this.timer = timer;
        }
    }

    private enum rollupsOnReadTimers {
        RR_SPLOT_TIMER(rollupsCalcOnReadTimer),
        RR_MPLOT_TIMER(rollupsCalcOnReadTimerMPlot);
        private Timer timer;

        private rollupsOnReadTimers (Timer timer) {
            this.timer = timer;
        }
    }

    public Map<Locator, MetricData> getRollupByGranularity(
            final String tenantId,
            final List<String> metrics,
            final long from,
            final long to,
            final Granularity g) {

        final Timer.Context ctx = metrics.size() == 1 ? plotTimers.SPLOT_TIMER.timer.time() : plotTimers.MPLOT_TIMER.timer.time();
        Future<List<SearchResult>> unitsFuture = null;
        List<SearchResult> units = null;
        List<Locator> locators = new ArrayList<Locator>();

        for (String metric : metrics) {
            locators.add(Locator.createLocatorFromPathComponents(tenantId, metric));
        }

        queriesSizeHist.update(locators.size());

        if (Util.shouldUseESForUnits()) {
             unitsFuture = ESUnitExecutor.submit(new Callable() {

                 @Override
                 public List<SearchResult> call() throws Exception {
                     DiscoveryIO discoveryIO = QueryDiscoveryModuleLoader.getDiscoveryInstance();
                     if (discoveryIO == null) {
                         log.warn("USE_ES_FOR_UNITS has been set to true, but no discovery module found." +
                                 " Please check your config");
                         return null;
                     }
                     return discoveryIO.search(tenantId, metrics);
                 }
             });
        }
        final Map<Locator,MetricData> metricDataMap = AstyanaxReader.getInstance().getDatapointsForRange(
                locators,
                new Range(g.snapMillis(from), to),
                g);

        if (unitsFuture != null) {
            try {
                units = unitsFuture.get();
                for (SearchResult searchResult : units) {
                    Locator locator = Locator.createLocatorFromPathComponents(searchResult.getTenantId(), searchResult.getMetricName());
                    if (metricDataMap.containsKey(locator))
                        metricDataMap.get(locator).setUnit(searchResult.getUnit());
                }
            } catch (Exception e) {
                log.warn("Exception encountered while getting units from ES, unit will be set to unknown in query results");
                log.debug(e.getMessage(), e);
            }
        }

        if (locators.size() == 1) {
            for (final Map.Entry<Locator, MetricData> metricData : metricDataMap.entrySet()) {
                Timer.Context context = rollupsOnReadTimers.RR_SPLOT_TIMER.timer.time();
                repairMetrics(metricData.getKey(), metricData.getValue(), from, to, g);
                context.stop();
            }
        } else if (locators.size() > 1 && Configuration.getInstance().getBooleanProperty(CoreConfig.TURN_OFF_RR_MPLOT) == false) {
            Timer.Context context = rollupsOnReadTimers.RR_MPLOT_TIMER.timer.time();
            ArrayList<ListenableFuture<Boolean>> futures = new ArrayList<ListenableFuture<Boolean>>();
            for (final Map.Entry<Locator, MetricData> metricData : metricDataMap.entrySet()) {
                futures.add(
                        rollupsOnReadExecutor.submit(new Callable<Boolean>() {
                            @Override
                            public Boolean call() {
                                return repairMetrics(metricData.getKey(), metricData.getValue(), from, to, g);
                            }
                        }));
            }
            ListenableFuture<List<Boolean>> aggregateFuture = Futures.allAsList(futures);
            try {
                aggregateFuture.get(rollupOnReadTimeout.getValue(), rollupOnReadTimeout.getUnit());
            } catch (Exception e) {
                aggregateFuture.cancel(true);
                exceededQueryTimeout.mark();
                log.warn(String.format("Exception encountered while doing rollups on read, incomplete rollups will be returned. %s", e.getMessage()));
            }
            context.stop();
        }
        ctx.stop();
        return metricDataMap;
    }

    private Boolean repairMetrics (Locator locator, MetricData metricData, final long from,
                                   final long to,
                                   final Granularity g) {
        boolean isRollable = metricData.getType().equals(MetricData.Type.NUMBER.toString())
                || metricData.getType().equals(MetricData.Type.HISTOGRAM.toString());
        Boolean retValue = false;

        // if Granularity is FULL, we are missing raw data - can't generate that
        if (ROLLUP_REPAIR && isRollable && g != Granularity.FULL && metricData != null) {
            if (metricData.getData().isEmpty()) { // data completely missing for range. complete repair.
                rollupsRepairEntireRange.mark();
                List<Points.Point> repairedPoints = repairRollupsOnRead(locator, g, from, to);
                for (Points.Point repairedPoint : repairedPoints) {
                    metricData.getData().add(repairedPoint);
                }

                if (repairedPoints.isEmpty()) {
                    rollupsRepairEntireRangeEmpty.mark();
                }
            } else {
                long actualStart = minTime(metricData.getData());
                long actualEnd = maxTime(metricData.getData());

                // If the returned start is greater than 'from', we are missing a portion of data.
                if (actualStart > from) {
                    rollupsRepairedLeft.mark();
                    List<Points.Point> repairedLeft = repairRollupsOnRead(locator, g, from, actualStart);
                    for (Points.Point repairedPoint : repairedLeft) {
                        metricData.getData().add(repairedPoint);
                    }

                    if (repairedLeft.isEmpty()) {
                        rollupsRepairedLeftEmpty.mark();
                    }
                }

                // If the returned end timestamp is less than 'to', we are missing a portion of data.
                if (actualEnd + g.milliseconds() <= to) {
                    rollupsRepairedRight.mark();
                    List<Points.Point> repairedRight = repairRollupsOnRead(locator, g, actualEnd + g.milliseconds(), to);
                    for (Points.Point repairedPoint : repairedRight) {
                        metricData.getData().add(repairedPoint);
                    }

                    if (repairedRight.isEmpty()) {
                        rollupsRepairedRightEmpty.mark();
                    }
                }
            }
            retValue = true;
        }

        if (g == Granularity.FULL) {
            numFullPointsReturned.update(metricData.getData().getPoints().size());
        } else {
            numRollupPointsReturned.update(metricData.getData().getPoints().size());
        }
        return retValue;
    }

    private List<Points.Point> repairRollupsOnRead(Locator locator, Granularity g, long from, long to) {
        List<Points.Point> repairedPoints = new ArrayList<Points.Point>();

        Iterable<Range> ranges = Range.rangesForInterval(g, g.snapMillis(from), to);
        for (Range r : ranges) {
            try {
                MetricData data = AstyanaxReader.getInstance().getDatapointsForRange(locator, r, Granularity.FULL);
                Points dataToRoll = data.getData();
                if (dataToRoll.isEmpty()) {
                    continue;
                }
                Rollup rollup = RollupHandler.rollupFromPoints(dataToRoll);

                if (rollup.hasData()) {
                    repairedPoints.add(new Points.Point(r.getStart(), rollup));
                }
            } catch (IOException ex) {
                log.error("Exception computing rollups during read: ", ex);
            }
        }

        return repairedPoints;
    }

    private static long minTime(Points<?> points) {
        long min = Long.MAX_VALUE;
        for (long time : points.getPoints().keySet())
            min = Math.min(min, time);
        return min;
    }

    private static long maxTime(Points<?> points) {
        long max = Long.MIN_VALUE;
        for (long time : points.getPoints().keySet())
            max = Math.max(max, time);
        return max;
    }

    // note: similar thing happening in RollupRunnable.getRollupComputer(), but we don't have access to RollupType here.
    private static Rollup rollupFromPoints(Points points) throws IOException {
        Class rollupTypeClass = points.getDataClass();
        if (rollupTypeClass.equals(SimpleNumber.class)) {
            return Rollup.BasicFromRaw.compute(points);
        } else if (rollupTypeClass.equals(CounterRollup.class)) {
            return Rollup.CounterFromCounter.compute(points);
        } else if (rollupTypeClass.equals(SetRollup.class)) {
            return Rollup.SetFromSet.compute(points);
        } else if (rollupTypeClass.equals(TimerRollup.class)) {
            return Rollup.TimerFromTimer.compute(points);
        } else if (rollupTypeClass.equals(GaugeRollup.class)) {
            return Rollup.GaugeFromGauge.compute(points);
        } else {
            throw new IOException(String.format("Unexpected rollup type: %s", rollupTypeClass.getSimpleName()));
        }
    }

    // TODO Add the multi search for historgrams
    protected MetricData getHistogramsByGranularity(String tenantId,
                                                   String metricName,
                                                   long from,
                                                   long to,
                                                   Granularity g) throws IOException {
        if (!g.isCoarser(Granularity.FULL)) {
            throw new IOException("Histograms are not available for this granularity");
        }

        final Timer.Context ctx = metricsFetchTimer.time();
        final Locator locator = Locator.createLocatorFromPathComponents(tenantId, metricName);

        MetricData data;
        try {
            data = AstyanaxReader.getInstance().getHistogramsForRange(locator, new Range(g.snapMillis(from), to), g);
            numHistogramPointsReturned.update(data.getData().getPoints().size());
        } finally {
            ctx.stop();
        }

        return data;
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/outputs/serializers/RollupEventSerializer.java
/*
* Copyright 2013 Rackspace
*
*    Licensed under the Apache License, Version 2.0 (the "License");
*    you may not use this file except in compliance with the License.
*    You may obtain a copy of the License at
*
*        http://www.apache.org/licenses/LICENSE-2.0
*
*    Unless required by applicable law or agreed to in writing, software
*    distributed under the License is distributed on an "AS IS" BASIS,
*    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
*    See the License for the specific language governing permissions and
*    limitations under the License.
*/

package com.rackspacecloud.blueflood.outputs.serializers;

import com.rackspacecloud.blueflood.eventemitter.RollupEvent;
import com.rackspacecloud.blueflood.io.Constants;
import com.rackspacecloud.blueflood.outputs.serializers.helpers.RollupSerializationHelper;
import org.codehaus.jackson.node.JsonNodeFactory;
import org.codehaus.jackson.node.ObjectNode;

import java.io.IOException;

public class RollupEventSerializer {

    public static ObjectNode serializeRollupEvent(RollupEvent rollupPayload) throws IOException {
        //Metadata Node
        ObjectNode metaNode = JsonNodeFactory.instance.objectNode();
        metaNode.put("type", rollupPayload.getRollup().getRollupType().toString());
        metaNode.put("unit", rollupPayload.getUnit());

        //Create and fill up root node
        ObjectNode rootNode = JsonNodeFactory.instance.objectNode();
        rootNode.put("tenantId", rollupPayload.getLocator().getTenantId());
        rootNode.put("metricName", rollupPayload.getLocator().getMetricName());
        rootNode.put("gran", rollupPayload.getGranularityName());
        rootNode.put("rollup", RollupSerializationHelper.rollupToJson(rollupPayload.getRollup()));
        rootNode.put("timestamp", rollupPayload.getTimestamp());
        rootNode.put("metadata", metaNode);

        return rootNode;
    }

    public byte[] toBytes(RollupEvent event) throws IOException {
        return serializeRollupEvent(event).toString().getBytes(Constants.DEFAULT_CHARSET);
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/outputs/serializers/helpers/RollupSerializationHelper.java
/*
* Copyright 2013 Rackspace
*
*    Licensed under the Apache License, Version 2.0 (the "License");
*    you may not use this file except in compliance with the License.
*    You may obtain a copy of the License at
*
*        http://www.apache.org/licenses/LICENSE-2.0
*
*    Unless required by applicable law or agreed to in writing, software
*    distributed under the License is distributed on an "AS IS" BASIS,
*    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
*    See the License for the specific language governing permissions and
*    limitations under the License.
*/

package com.rackspacecloud.blueflood.outputs.serializers.helpers;

import com.bigml.histogram.Bin;
import com.bigml.histogram.SimpleTarget;
import com.rackspacecloud.blueflood.types.*;
import org.codehaus.jackson.node.ArrayNode;
import org.codehaus.jackson.node.JsonNodeFactory;
import org.codehaus.jackson.node.ObjectNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOError;
import java.io.IOException;
import java.util.Collection;

public class RollupSerializationHelper {
    private static final Logger log = LoggerFactory.getLogger(RollupSerializationHelper.class);

    public static ObjectNode rollupToJson(Rollup rollup) {
        if (rollup instanceof CounterRollup)
            return handleCounterRollup((CounterRollup)rollup);
        else if (rollup instanceof TimerRollup)
            return handleTimerRollup((TimerRollup)rollup);
        else if (rollup instanceof SetRollup)
            return handleSetRollup((SetRollup)rollup);
        else if (rollup instanceof GaugeRollup)
            return handleGaugeRollup((GaugeRollup)rollup);
        else if (rollup instanceof BasicRollup)
            return handleBasicRollup((BasicRollup)rollup, JsonNodeFactory.instance.objectNode());
        else if (rollup instanceof HistogramRollup)
            return handleHistogramRollup((HistogramRollup)rollup);
        else {
            log.error("Error encountered while serializing the rollup "+rollup);
            throw new IOError(new IOException("Cannot serialize the Rollup : "+rollup));
        }
    }

    private static ObjectNode handleHistogramRollup(HistogramRollup rollup) {
        ObjectNode rollupNode =  JsonNodeFactory.instance.objectNode();
        ArrayNode binArray = JsonNodeFactory.instance.arrayNode();
        Collection<Bin<SimpleTarget>> bins = rollup.getBins();
        for (Bin<SimpleTarget> bin : bins) {
            ObjectNode binNode = JsonNodeFactory.instance.objectNode();
            binNode.put("count", bin.getCount());
            binNode.put("mean", bin.getMean());
            binArray.add(binNode);
        }
        rollupNode.put("bins", binArray);
        rollupNode.put("binCount", rollup.getCount());
        return rollupNode;
    }

    private static ObjectNode handleBasicRollup(IBasicRollup rollup, ObjectNode rollupNode) {
        long count = rollup.getCount();
        rollupNode.put("count", count);
        if (count == 0) {
            rollupNode.putNull("max");
            rollupNode.putNull("min");
            rollupNode.putNull("mean");
            rollupNode.putNull("var");
        } else {
            rollupNode.put("max", rollup.getMaxValue().isFloatingPoint() ? rollup.getMaxValue().toDouble() : rollup.getMaxValue().toLong());
            rollupNode.put("min", rollup.getMinValue().isFloatingPoint() ? rollup.getMinValue().toDouble() : rollup.getMinValue().toLong());
            rollupNode.put("mean", rollup.getAverage().isFloatingPoint() ? rollup.getAverage().toDouble() : rollup.getAverage().toLong());
            rollupNode.put("var", rollup.getVariance().isFloatingPoint() ? rollup.getVariance().toDouble() : rollup.getVariance().toLong());
        }
        return rollupNode;
    }

    private static ObjectNode handleGaugeRollup(GaugeRollup rollup) {
        ObjectNode rollupNode = JsonNodeFactory.instance.objectNode();
        SimpleNumber rollupValue = rollup.getLatestValue();
        rollupNode.put("latestVal", rollupValue.getDataType() == (SimpleNumber.Type.DOUBLE) ? rollupValue.getValue().doubleValue() : rollupValue.getValue().longValue());
        return handleBasicRollup(rollup, rollupNode);
    }

    private static ObjectNode handleSetRollup(SetRollup rollup) {
        ObjectNode rollupNode = JsonNodeFactory.instance.objectNode();
        rollupNode.put("count", rollup.getCount());
        return rollupNode;
    }

    private static ObjectNode handleTimerRollup(TimerRollup rollup) {
        ObjectNode rollupNode = JsonNodeFactory.instance.objectNode();
        rollupNode.put("sum", rollup.getSum());
        rollupNode.put("rate", rollup.getRate());
        rollupNode.put("sampleCount", rollup.getSampleCount());
        return handleBasicRollup(rollup, rollupNode);
    }

    private static ObjectNode handleCounterRollup(CounterRollup rollup) {
        ObjectNode rollupNode = JsonNodeFactory.instance.objectNode();
        rollupNode.put("count", (rollup.getCount() instanceof Float || rollup.getCount() instanceof Double) ? rollup.getCount().doubleValue() : rollup.getCount().longValue());
        rollupNode.put("sampleCount", rollup.getSampleCount());
        rollupNode.put("rate", rollup.getRate());
        return rollupNode;
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/rollup/Granularity.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.rollup;

import com.rackspacecloud.blueflood.cache.ConfigTtlProvider;
import com.rackspacecloud.blueflood.cache.SafetyTtlProvider;
import com.rackspacecloud.blueflood.exceptions.GranularityException;
import com.rackspacecloud.blueflood.service.Configuration;
import com.rackspacecloud.blueflood.service.CoreConfig;
import com.rackspacecloud.blueflood.types.Range;
import com.rackspacecloud.blueflood.types.RollupType;

import java.util.Calendar;

/**
 * 1440m    [ not enough space to show the relationship, but there would be 6 units of the 240m ranges in 1 1440m range.
 * 240m     [                                               |                                               |        ...
 * 60m      [           |           |           |           |           |           |           |           |        ...
 * 20m      [   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |...
 * 5m       [||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||...
 * full     [ granularity to the second, but ranges are partitioned the same as in 5m.                               ...
 */
public final class Granularity {
    private static final int GET_BY_POINTS_ASSUME_INTERVAL = Configuration.getInstance().getIntegerProperty(CoreConfig.GET_BY_POINTS_ASSUME_INTERVAL);
    private static final String GET_BY_POINTS_SELECTION_ALGORITHM = Configuration.getInstance().getStringProperty(CoreConfig.GET_BY_POINTS_GRANULARITY_SELECTION);
    private static int INDEX_COUNTER = 0;
    private static final int BASE_SLOTS_PER_GRANULARITY = 4032; // needs to be a multiple of the GCF of 4, 12, 48, 288.
    public static final int MILLISECONDS_IN_SLOT = 300000;
    private static final int SECS_PER_DAY = 86400;
    
    public static final Granularity FULL = new Granularity("metrics_full", 300000, BASE_SLOTS_PER_GRANULARITY, "full");
    public static final Granularity MIN_5 = new Granularity("metrics_5m", 300000, BASE_SLOTS_PER_GRANULARITY, "5m");
    public static final Granularity MIN_20 = new Granularity("metrics_20m", 1200000, (BASE_SLOTS_PER_GRANULARITY / 4), "20m");
    public static final Granularity MIN_60 = new Granularity("metrics_60m", 3600000, (BASE_SLOTS_PER_GRANULARITY / 12), "60m");
    public static final Granularity MIN_240 = new Granularity("metrics_240m", 14400000, (BASE_SLOTS_PER_GRANULARITY / 48), "240m");
    public static final Granularity MIN_1440 = new Granularity("metrics_1440m", 86400000, (BASE_SLOTS_PER_GRANULARITY / 288), "1440m");

    private static final Granularity[] granularities = new Granularity[] { FULL, MIN_5, MIN_20, MIN_60, MIN_240, MIN_1440 }; // order is important.

    public static final Granularity LAST = MIN_1440;

    private static final Granularity[] rollupGranularities = new Granularity[] { MIN_5, MIN_20, MIN_60, MIN_240, MIN_1440 }; // order is important.
    
    public static final int MAX_NUM_SLOTS = FULL.numSlots() + MIN_5.numSlots() + MIN_20.numSlots() + MIN_60.numSlots() + MIN_240.numSlots() + MIN_1440.numSlots();

    private static SafetyTtlProvider SAFETY_TTL_PROVIDER;

    // simple counter for all instances, since there will be very few.
    private final int index;
    
    // name of column family where rollups are kept.
    private final String cf;
    
    // like cf, but shorter.
    private final String shortName;
    
    // number of milliseconds in one slot of this rollup.
    private final int milliseconds;
    
    // number of slots for this granularity.  This number decreases as granularity is more coarse.  Also, the number of
    // minutes indicated by a single slot increases as the number of slots goes down.
    private final int numSlots;
    
    private Granularity(String cf, int milliseconds, int numSlots, String shortName) {
        index = INDEX_COUNTER++;
        this.cf = cf;
        this.milliseconds = milliseconds;
        this.numSlots = numSlots;
        this.shortName = shortName;
    }
    
    // name->column_family
    public String name() { return cf; }
    
    // name->tenant ttl key.
    public String shortName() { return shortName; }
    
    /** @return the number of seconds in one slot range. */
    public int milliseconds() { return milliseconds; }
    
    public int numSlots() { return numSlots; }
    
    // returns the next coarser granularity.
    // FULL -> 5m -> 20m -> 60m -> 240m -> 1440m -> explosion.
    public Granularity coarser() throws GranularityException {
        if (this == LAST) throw new GranularityException("Nothing coarser than " + name());
        return granularities[index + 1];
    }
    
    // opposite of coarser().
    public Granularity finer() throws GranularityException {
        if (this == FULL) throw new GranularityException("Nothing finer than " + name());
        return granularities[index - 1];
    }

    public boolean isCoarser(Granularity other) {
        return indexOf(this) > indexOf(other);
    }

    private int indexOf(Granularity gran) {
        for (int i = 0; i < granularities.length; i++) {
            if (gran == granularities[i]) {
                return i;
            }
        }

        throw new RuntimeException("Granularity " + gran.toString() + " not present in granularities list.");
    }

    /**
     * Gets the floor multiple of number of milliseconds in this granularity
     * @param millis
     * @return
     */
    public long snapMillis(long millis) {
        if (this == FULL) return millis;
        else return (millis / milliseconds) * milliseconds;
    }

    /**
     * At full granularity, a slot is 300 continuous seconds.  The duration of a single slot goes up (way up) as
     * granularity is lost.  At the same time the number of slots decreases.
     * @param millis
     * @return
     */
    public int slot(long millis) {
        // the actual slot is 
        int fullSlot = millisToSlot(millis);
        return (numSlots * fullSlot) / BASE_SLOTS_PER_GRANULARITY;
    }

    /**
     * returns the slot for the current granularity based on a supplied slot from the granularity one resolution finer
     * i.e, slot 144 for a 5m is == slot 36 of 20m (because 144 / (20m/5m)), slot 12 at 60m, slot 3 at 240m, etc
     * @param finerSlot
     * @return
     */
    public int slotFromFinerSlot(int finerSlot) throws GranularityException {
        return (finerSlot * numSlots()) / this.finer().numSlots();
    }

    /**
     * We need to derive ranges (actual times) from slots (which are fixed integers that wrap) when we discover a late
     * slot. These ranges can be derived from a reference point (which is usually something like now).
     * @param slot
     * @param referenceMillis
     * @return
     */
    public Range deriveRange(int slot, long referenceMillis) {
        // referenceMillis refers to the current time in reference to the range we want to generate from the supplied 
        // slot. This implies that the range we wish to return is before slot(reference).  allow for slot wrapping.
        referenceMillis = snapMillis(referenceMillis);
        int refSlot = slot(referenceMillis);
        int slotDiff = slot > refSlot ? (numSlots() - slot + refSlot) : (refSlot - slot);
        long rangeStart = referenceMillis - slotDiff * milliseconds();
        return new Range(rangeStart, rangeStart + milliseconds() - 1);
    }

    /**
     * Return granularity that maps most closely to requested number of points based on
     * provided selection algorithm
     *
     * @param from beginning of interval (millis)
     * @param to end of interval (millis)
     * @param points count of desired data points
     * @return
     */
    public static Granularity granularityFromPointsInInterval(String tenantid, long from, long to, int points) {
        if (from >= to) {
            throw new RuntimeException("Invalid interval specified for fromPointsInInterval");
        }

        double requestedDuration = to - from;

        if (GET_BY_POINTS_SELECTION_ALGORITHM.startsWith("GEOMETRIC"))
            return granularityFromPointsGeometric(tenantid, from, to, requestedDuration, points);
        else if (GET_BY_POINTS_SELECTION_ALGORITHM.startsWith("LINEAR"))
            return granularityFromPointsLinear(requestedDuration, points);
        else if (GET_BY_POINTS_SELECTION_ALGORITHM.startsWith("LESSTHANEQUAL"))
            return granularityFromPointsLessThanEqual(requestedDuration, points);

        return granularityFromPointsGeometric(tenantid, from, to, requestedDuration, points);
    }

    /**
     * Find the granularity in the interval that will yield a number of data points that are
     * closest to the requested points but <= requested points.
     *
     * @param requestedDuration
     * @param points
     * @return
     */
    private static Granularity granularityFromPointsLessThanEqual(double requestedDuration, int points) {
        Granularity gran = granularityFromPointsLinear(requestedDuration, points);

        if (requestedDuration / gran.milliseconds() > points) {
            try {
                gran = gran.coarser();
            } catch (GranularityException e) { /* do nothing, already at 1440m */ }
        }

        return gran;
    }

    /**
     * Find the granularity in the interval that will yield a number of data points that are close to $points
     * in terms of linear distance.
     *
     * @param requestedDuration
     * @param points
     * @return
     */
    private static Granularity granularityFromPointsLinear(double requestedDuration, int points) {
        int closest = Integer.MAX_VALUE;
        int diff = 0;
        Granularity gran = null;

        for (Granularity g : Granularity.granularities()) {
            if (g == Granularity.FULL)
                diff = (int)Math.abs(points - (requestedDuration / GET_BY_POINTS_ASSUME_INTERVAL));
            else
                diff = (int)Math.abs(points - (requestedDuration /g.milliseconds()));
            if (diff < closest) {
                closest = diff;
                gran = g;
            } else {
                break;
            }
        }

        return gran;
    }

    /**
     *
     * Look for the granularity that would generate the density of data points closest to the value desired. For
     * example, if 500 points were requested, it is better to return 1000 points (2x more than were requested)
     * than it is to return 100 points (5x less than were requested). Our objective is to generate reasonable
     * looking graphs.
     *
     * @param requestedDuration (milliseconds)
     */
    private static Granularity granularityFromPointsGeometric(String tenantid, long from, long to, double requestedDuration, int requestedPoints) {
        double minimumPositivePointRatio = Double.MAX_VALUE;
        Granularity gran = null;
        if (SAFETY_TTL_PROVIDER == null) {
            SAFETY_TTL_PROVIDER = SafetyTtlProvider.getInstance();
        }

        for (Granularity g : Granularity.granularities()) {
            long ttl = SAFETY_TTL_PROVIDER.getFinalTTL(tenantid, g);

            if (from < Calendar.getInstance().getTimeInMillis() - ttl) {
                continue;
            }

            // FULL resolution is tricky because we don't know the period of check in question. Assume the minimum
            // period and go from there.
            long period = (g == Granularity.FULL) ? GET_BY_POINTS_ASSUME_INTERVAL : g.milliseconds();
            double providablePoints = requestedDuration / period;
            double positiveRatio;

            // Generate a ratio >= 1 of either (points requested / points provided by this granularity) or the inverse.
            // Think of it as an "absolute ratio". Our goal is to minimize this ratio.
            if (providablePoints > requestedPoints) {
                positiveRatio = providablePoints / requestedPoints;
            } else {
                positiveRatio = requestedPoints / providablePoints;
            }

            if (positiveRatio < minimumPositivePointRatio) {
                minimumPositivePointRatio = positiveRatio;
                gran = g;
            } else {
                break;
            }
        }

        if (gran == null) {
            gran = Granularity.LAST;
        }

        return gran;
    }

    /** calculate the full/5m slot based on 4032 slots of 300000 milliseconds per slot. */
    static int millisToSlot(long millis) {
        return (int)((millis % (BASE_SLOTS_PER_GRANULARITY * MILLISECONDS_IN_SLOT)) / MILLISECONDS_IN_SLOT);
    }

    @Override
    public int hashCode() {
        return name().hashCode();
    }

    @Override
    public boolean equals(Object obj) {
        if (!(obj instanceof Granularity)) return false;
        else return obj == this;
    }

    public static Granularity[] granularities() { return granularities; }

    public static Granularity[] rollupGranularities() { return rollupGranularities; }
    
    public static Granularity fromString(String s) {
        for (Granularity g : granularities)
            if (g.name().equals(s) || g.shortName().equals(s))
                return g;
        return null;
    }

    @Override
    public String toString() {
        return name();
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/BluefloodServiceStarter.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.rackspacecloud.blueflood.io.AstyanaxShardStateIO;
import com.rackspacecloud.blueflood.cache.MetadataCache;
import com.rackspacecloud.blueflood.io.IMetricsWriter;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.rackspacecloud.blueflood.utils.RestartGauge;
import com.rackspacecloud.blueflood.utils.Util;
import org.apache.log4j.PropertyConfigurator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.TimeUnit;

public class BluefloodServiceStarter {
    private static final Logger log = LoggerFactory.getLogger(BluefloodServiceStarter.class);

    public static void validateCassandraHosts() {
        String hosts = Configuration.getInstance().getStringProperty(CoreConfig.CASSANDRA_HOSTS);
        if (!(hosts.length() >= 3)) {
            log.error("No cassandra hosts found in configuration option 'CASSANDRA_HOSTS'");
            System.exit(-1);
        }
        for (String host : hosts.split(",")) {
            if (!host.matches("[\\d\\w\\.]+:\\d+")) {
                log.error("Invalid Cassandra host found in Configuration option 'CASSANDRA_HOSTS' -- Should be of the form <hostname>:<port>");
                System.exit(-1);
            }
        }
    }

    private static void startShardStateServices(ScheduleContext context) {
        Configuration config = Configuration.getInstance();
        if (config.getBooleanProperty(CoreConfig.INGEST_MODE) || config.getBooleanProperty(CoreConfig.ROLLUP_MODE)) {
            // these threads are responsible for sending/receiving schedule context state to/from the database.
            final Collection<Integer> allShards = Collections.unmodifiableCollection(Util.parseShards("ALL"));

            try {
                final AstyanaxShardStateIO io = new AstyanaxShardStateIO();
                final ShardStatePusher shardStatePusher = new ShardStatePusher(allShards,
                        context.getShardStateManager(),
                        io);
                final ShardStatePuller shardStatePuller = new ShardStatePuller(allShards,
                        context.getShardStateManager(),
                        io);

                final Thread shardPush = new Thread(shardStatePusher, "Shard state writer");
                final Thread shardPull = new Thread(shardStatePuller, "Shard state reader");

                shardPull.start();
                shardPush.start();

                log.info("Shard push and pull services started");
            } catch (NumberFormatException ex) {
                log.error("Shard services not started. Probably misconfiguration", ex);
            }
        } else {
            log.info("Shard push and pull services not required");
        }
    }

    private static void startIngestServices(ScheduleContext context) {
        // start up ingestion services.
        Configuration config = Configuration.getInstance();
        if (config.getBooleanProperty(CoreConfig.INGEST_MODE)) {
            List<String> modules = config.getListProperty(CoreConfig.INGESTION_MODULES);
            if (modules.isEmpty()) {
                log.error("Ingestion mode is enabled, however no ingestion modules are enabled!");
                System.exit(1);
            }
            ClassLoader classLoader = IngestionService.class.getClassLoader();
            final List<IngestionService> ingestionServices = new ArrayList<IngestionService>();
            Integer services_started = 0;
            for (String module : modules) {
                log.info("Loading ingestion service module " + module);
                try {
                    ClassLoader loader = IMetricsWriter.class.getClassLoader();
                    Class writerImpl = loader.loadClass(config.getStringProperty(CoreConfig.IMETRICS_WRITER));
                    IMetricsWriter writer = (IMetricsWriter) writerImpl.newInstance();

                    Class serviceClass = classLoader.loadClass(module);
                    IngestionService service = (IngestionService) serviceClass.newInstance();
                    log.info("Starting ingestion service module " + module + " with writer: " + writerImpl.getSimpleName());
                    ingestionServices.add(service);
                    service.startService(context, writer);
                    log.info("Successfully started ingestion service module " + module + " with writer: " + writerImpl.getSimpleName());
                    services_started++;
                } catch (InstantiationException e) {
                    log.error("Unable to create instance of ingestion service class for: " + module, e);
                    System.exit(1);
                } catch (IllegalAccessException e) {
                    log.error("Error starting ingestion service: " + module, e);
                    System.exit(1);
                } catch (ClassNotFoundException e) {
                    log.error("Unable to locate ingestion service module: " + module, e);
                    System.exit(1);
                } catch (RuntimeException e) {
                    log.error("Error starting ingestion service: " + module, e);
                    System.exit(1);
                } catch (Throwable e) {
                    log.error("Error starting ingestion service: " + module, e);
                    System.exit(1);
                }
            }
            log.info("Started " + services_started + " ingestion services");
        } else {
            log.info("HTTP ingestion service not required");
        }
    }

    private static void startQueryServices() {
        // start up query services.
        Configuration config = Configuration.getInstance();
        if (config.getBooleanProperty(CoreConfig.QUERY_MODE)) {
            List<String> modules = config.getListProperty(CoreConfig.QUERY_MODULES);
            if (modules.isEmpty()) {
                log.error("Query mode is enabled, however no query modules are enabled!");
                System.exit(1);
            }
            ClassLoader classLoader = QueryService.class.getClassLoader();
            final List<QueryService> queryServices = new ArrayList<QueryService>();
            Integer services_started = 0;
            for (String module : modules) {
                log.info("Loading query service module " + module);
                try {
                    Class serviceClass = classLoader.loadClass(module);
                    QueryService service = (QueryService) serviceClass.newInstance();
                    queryServices.add(service);
                    log.info("Starting query service module " + module);
                    service.startService();
                    log.info("Successfully started query service module " + module);
                    services_started++;
                } catch (InstantiationException e) {
                    log.error("Unable to create instance of query service class for: " + module, e);
                    System.exit(1);
                } catch (IllegalAccessException e) {
                    log.error("Error starting query service: " + module, e);
                    System.exit(1);
                } catch (ClassNotFoundException e) {
                    log.error("Unable to locate query service module: " + module, e);
                    System.exit(1);
                } catch (RuntimeException e) {
                    log.error("Error starting query service: " + module, e);
                    System.exit(1);
                } catch (Throwable e) {
                    log.error("Error starting query service: " + module, e);
                    System.exit(1);
                }
            }
            log.info("Started " + services_started + " query services");
        } else {
            log.info("Query service not required");
        }
    }

    private static void startRollupService(final ScheduleContext context) {
        Timer serverTimeUpdate = new java.util.Timer("Server Time Syncer", true);

        if (Configuration.getInstance().getBooleanProperty(CoreConfig.ROLLUP_MODE)) {
            // configure the rollup service. this is a daemonish thread that decides when to rollup ranges of data on
            // in the data cluster.
            final RollupService rollupService = new RollupService(context);
            Thread rollupThread = new Thread(rollupService, "BasicRollup conductor");

            // todo: this happens no matter what.
            // todo: at some point, it makes sense to extract the keeping-server-time and setting-server-time methods
            // out of RollupService.  It's a historical artifact at this point.

            serverTimeUpdate.schedule(new TimerTask() {
                @Override
                public void run() {
                    if (rollupService.getKeepingServerTime()) {
                        context.setCurrentTimeMillis(System.currentTimeMillis());
                    }
                }
            }, 100, 500);

            rollupThread.start();

        } else {
            serverTimeUpdate.schedule(new TimerTask() {
                @Override
                public void run() {
                    context.setCurrentTimeMillis(System.currentTimeMillis());
                }
            }, 100, 500);
        }
    }

    private static void startEventListenerModules() {
        Configuration config = Configuration.getInstance();
        List<String> modules = config.getListProperty(CoreConfig.EVENT_LISTENER_MODULES);
        if (!modules.isEmpty()) {
            log.info("Starting event listener modules");
            ClassLoader classLoader = EventListenerService.class.getClassLoader();
            for (String module : modules) {
                log.info("Loading event listener module " + module);
                try {
                    Class serviceClass = classLoader.loadClass(module);
                    EventListenerService service = (EventListenerService) serviceClass.newInstance();
                    log.info("Starting event listener module " + module);
                    service.startService();
                    log.info("Successfully started event listener module " + module);
                } catch (InstantiationException e) {
                    log.error("Unable to create instance of event listener class for: " + module, e);
                } catch (IllegalAccessException e) {
                    log.error("Error starting event listener: " + module, e);
                } catch (ClassNotFoundException e) {
                    log.error("Unable to locate event listener module: " + module, e);
                } catch (RuntimeException e) {
                    log.error("Error starting event listener: " + module, e);
                } catch (Throwable e) {
                    log.error("Error starting event listener: " + module, e);
                }
            }
        } else {
            log.info("No event listener modules configured.");
        }
    }

    public static void main(String args[]) {
        // load configuration.
        Configuration config = Configuration.getInstance();

        // if log4j configuration references an actual file, periodically reload it to catch changes.
        String log4jConfig = System.getProperty("log4j.configuration");
        if (log4jConfig != null && log4jConfig.startsWith("file:")) {
            PropertyConfigurator.configureAndWatch(log4jConfig.substring("file:".length()), 5000);
        }

        // check that we have cassandra hosts
        validateCassandraHosts();
        
        // possibly load the metadata cache
        boolean usePersistedCache = Configuration.getInstance().getBooleanProperty(CoreConfig.METADATA_CACHE_PERSISTENCE_ENABLED);
        if (usePersistedCache) {
            String path = Configuration.getInstance().getStringProperty(CoreConfig.METADATA_CACHE_PERSISTENCE_PATH);
            final File cacheLocation = new File(path);
            if (cacheLocation.exists()) {
                try {
                    DataInputStream in = new DataInputStream(new FileInputStream(cacheLocation));
                    MetadataCache.getInstance().load(in);
                    in.close();
                } catch (IOException ex) {
                    log.error(ex.getMessage(), ex);
                }
            } else {
                log.info("Wanted to load metadata cache, but it did not exist: " + path);
            }
            
            Timer cachePersistenceTimer = new Timer("Metadata-Cache-Persistence");
            int savePeriodMins = Configuration.getInstance().getIntegerProperty(CoreConfig.METADATA_CACHE_PERSISTENCE_PERIOD_MINS);
            cachePersistenceTimer.schedule(new TimerTask() {
                        @Override
                        public void run() {
                            try {
                                DataOutputStream out = new DataOutputStream(new FileOutputStream(cacheLocation, false));
                                MetadataCache.getInstance().save(out);
                                out.close();
                            } catch (IOException ex) {
                                log.error(ex.getMessage(), ex);
                            }
                        }
                    }, 
                    TimeUnit.MINUTES.toMillis(savePeriodMins),
                    TimeUnit.MINUTES.toMillis(savePeriodMins));
        }

        // has the side-effect of causing static initialization of Metrics, starting instrumentation reporting.
        new RestartGauge(Metrics.getRegistry(), RollupService.class);

        final Collection<Integer> shards = Collections.unmodifiableCollection(
                Util.parseShards(config.getStringProperty(CoreConfig.SHARDS)));
        final String zkCluster = config.getStringProperty(CoreConfig.ZOOKEEPER_CLUSTER);
        final ScheduleContext rollupContext = "NONE".equals(zkCluster) ?
                new ScheduleContext(System.currentTimeMillis(), shards) :
                new ScheduleContext(System.currentTimeMillis(), shards, zkCluster);

        log.info("Starting blueflood services");
        startShardStateServices(rollupContext);
        startIngestServices(rollupContext);
        startQueryServices();
        startRollupService(rollupContext);
        startEventListenerModules();
        log.info("All blueflood services started");
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/ConfigDefaults.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

/**
 * Interface to be used on default config classes
 */
public interface ConfigDefaults {
    public String getDefaultValue();
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/Configuration.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.google.common.annotations.VisibleForTesting;
import com.google.common.collect.Lists;

import java.io.IOException;
import java.io.InputStream;
import java.net.URL;
import java.util.*;

/**
 * java/conf/bf-dev.con has an exhaustive description of each configuration option.
 *
 */
public class Configuration {
    private static final Properties defaultProps = new Properties();
    private static Properties props;
    private static final Configuration INSTANCE = new Configuration();

    public static Configuration getInstance() {
        return INSTANCE;
    }

    private Configuration() {
        try {
            init();
        } catch (IOException ex) {
            throw new RuntimeException(ex);
        }
    }

    public void loadDefaults(ConfigDefaults[] configDefaults) {
        for (ConfigDefaults configDefault : configDefaults) {
            defaultProps.setProperty(configDefault.toString(), configDefault.getDefaultValue());
        }
    }

    public void init() throws IOException {
        props = new Properties(defaultProps);
        // load the configuration.
        String configStr = System.getProperty("blueflood.config");
        if (configStr != null) {
            URL configUrl = new URL(configStr);
            props.load(configUrl.openStream());
        }
    }

    public Map<Object,Object> getProperties() {
        return Collections.unmodifiableMap(props);
    }

    public String getStringProperty(Enum<? extends ConfigDefaults> name) {
        return getStringProperty(name.toString());
    }
    public String getStringProperty(String name) {
        if (System.getProperty(name) != null && !props.containsKey("original." + name)) {
            if (props.containsKey(name))
                props.put("original." + name, props.get(name));
            props.put(name, System.getProperty(name));
        }
        return props.getProperty(name);
    }

    public int getIntegerProperty(Enum<? extends ConfigDefaults> name) {
        return getIntegerProperty(name.toString());
    }
    public int getIntegerProperty(String name) {
        return Integer.parseInt(getStringProperty(name));
    }

    public float getFloatProperty(Enum<? extends ConfigDefaults> name) {
        return getFloatProperty(name.toString());
    }
    public float getFloatProperty(String name) {
        return Float.parseFloat(getStringProperty(name));
    }

    public long getLongProperty(Enum<? extends ConfigDefaults> name) {
        return getLongProperty(name.toString());
    }
    public long getLongProperty(String name) {
        return Long.parseLong(getStringProperty(name));
    }

    public boolean getBooleanProperty(Enum<? extends ConfigDefaults> name) {
        return getBooleanProperty(name.toString());
    }

    public boolean getBooleanProperty(String name) {
        return "true".equalsIgnoreCase(getStringProperty(name));
    }

    public List<String> getListProperty(Enum<? extends ConfigDefaults> name) {
        return getListProperty(name.toString());
    }
    public List<String> getListProperty(String name) {
        List<String> list = Lists.newArrayList(getStringProperty(name).split("\\s*,\\s*"));
        list.removeAll(Arrays.asList("", null));
        return list;
    }

    @VisibleForTesting
    public void setProperty(String name, String val) {
      props.setProperty(name, val);
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/CoreConfig.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

/**
 * Default config values for blueflood-core. Also to be used for getting config key names.
 */
public enum CoreConfig implements ConfigDefaults {
    CASSANDRA_HOSTS("127.0.0.1:19180"),
    DEFAULT_CASSANDRA_PORT("19180"),
    // This number is only accurate if MAX_CASSANDRA_CONNECTIONS is evenly divisible by number of hosts
    MAX_CASSANDRA_CONNECTIONS("75"),

    ROLLUP_KEYSPACE("DATA"),
    CLUSTER_NAME("Test Cluster"),

    INGESTION_MODULES(""),
    QUERY_MODULES(""),
    DISCOVERY_MODULES(""),
    EVENT_LISTENER_MODULES(""),

    MAX_LOCATOR_FETCH_THREADS("2"),
    MAX_ROLLUP_READ_THREADS("20"),
    MAX_ROLLUP_WRITE_THREADS("5"),

    DISCOVERY_WRITER_MIN_THREADS("5"),
    DISCOVERY_WRITER_MAX_THREADS("10"),

    // Maximum threads that would access the cache concurrently
    META_CACHE_MAX_CONCURRENCY("50"),

    // Setting this to true will enable batched meta reads and writes from db (lazy loads and writes)
    META_CACHE_BATCHED_READS("false"),
    META_CACHE_BATCHED_WRITES("false"),

    META_CACHE_BATCHED_READS_THRESHOLD("100"), // how many rows to read at a time? (batch size)
    META_CACHE_BATCHED_READS_TIMER_MS("10"),  // how often to read? (batch timer) (read faster than writes)
    META_CACHE_BATCHED_READS_PIPELINE_DEPTH("10"), // how many outstanding batches? (1 thread per batch).
    META_CACHE_BATCHED_READS_QUEUE_SIZE("1000"),

    META_CACHE_BATCHED_WRITES_THRESHOLD("100"),  // how many meta columns to write at a time? (batch size)
    META_CACHE_BATCHED_WRITES_TIMER_MS("20"),   // how often to write? (batch timer)
    META_CACHE_BATCHED_WRITES_PIPELINE_DEPTH("10"), // how many outstanding batches? (1 thread per batch).
    META_CACHE_BATCHED_WRITES_QUEUE_SIZE("1000"),

    // Maximum timeout waiting on exhausted connection pools in milliseconds.
    // Maps directly to Astyanax's ConnectionPoolConfiguration.setMaxTimeoutWhenExhausted
    MAX_TIMEOUT_WHEN_EXHAUSTED("2000"),
    SCHEDULE_POLL_PERIOD("60000"),

    // Config refresh interval (If a new config is pushed out, we need to pick up the changes)
    // time is in milliseconds
    CONFIG_REFRESH_PERIOD("10000"),

    // this is a special string, or a comma list of integers. e.g.: "1,2,3,4"
    // valid shards are 0..127
    SHARDS("ALL"),

    // thread sleep times between shard push/pulls.
    SHARD_PUSH_PERIOD("2000"),
    SHARD_PULL_PERIOD("20000"),

    // blueflood uses zookeeper to acquire locks before working on shards
    ZOOKEEPER_CLUSTER("127.0.0.1:22181"),

    // 20 min
    SHARD_LOCK_HOLD_PERIOD_MS("1200000"),
    // 1 min
    SHARD_LOCK_DISINTERESTED_PERIOD_MS("60000"),
    // 2 min
    SHARD_LOCK_SCAVENGE_INTERVAL_MS("120000"),
    MAX_ZK_LOCKS_TO_ACQUIRE_PER_CYCLE("1"),

    INTERNAL_API_CLUSTER("127.0.0.1:50020,127.0.0.1:50020"),

    RIEMANN_HOST(""), //string: address of riemann server where events should be sent.
    RIEMANN_PORT("5555"),
    RIEMANN_PREFIX(""), //string: prefix metric names with this. useful for telling metrics from backfiller vs normal BF instance. (RIEMANN_LOCALHOST and RIEMANN_TAGS are better though)
    RIEMANN_LOCALHOST(""), //string: name of the server blueflood is running on.
    RIEMANN_TAGS(""), //comma-delimited list of strings: tags to append to metric events. ex- blueflood,ingest
    RIEMANN_SEPARATOR(""), //string: separator between metric name components. if set to "|" would result in: prefix|metric_name|rate_5m
    RIEMANN_TTL(""), //float: number of seconds until metric TTLs out of riemann's index

    GRAPHITE_HOST(""),
    GRAPHITE_PORT("2003"),
    GRAPHITE_PREFIX("unconfiguredNode.metrics."),

    INGEST_MODE("true"),
    ROLLUP_MODE("true"),
    QUERY_MODE("true"),

    METRICS_BATCH_WRITER_THREADS("50"),

    METRIC_BATCH_SIZE("100"),

    CASSANDRA_REQUEST_TIMEOUT("10000"),
    // set <= 0 to not retry
    CASSANDRA_MAX_RETRIES("5"),

    // v1.0 defaults to ','. This configuration option provides backwards compatibility.
    // Using legacy separators is deprecated as of 2.0 and will be removed in 3.0
    USE_LEGACY_METRIC_SEPARATOR("false"),

    ROLLUP_BATCH_MIN_SIZE("5"),
    ROLLUP_BATCH_MAX_SIZE("100"),

    ENABLE_HISTOGRAMS("false"),

    // Assume, for calculating granularity for GetByPoints queries, that data is sent at this interval.
    GET_BY_POINTS_ASSUME_INTERVAL("30000"),

    // Rollups repair on read
    REPAIR_ROLLUPS_ON_READ("true"),

    // valid options are: GEOMETRIC, LINEAR, and LESSTHANEQUAL
    GET_BY_POINTS_GRANULARITY_SELECTION("GEOMETRIC"),

    IMETRICS_WRITER("com.rackspacecloud.blueflood.io.AstyanaxMetricsWriter"),

    METADATA_CACHE_PERSISTENCE_ENABLED("false"),
    METADATA_CACHE_PERSISTENCE_PATH("/dev/null"),
    METADATA_CACHE_PERSISTENCE_PERIOD_MINS("10"),
    META_CACHE_RETENTION_IN_MINUTES("10"),
    
    // how long we typically wait to schedule a rollup.
    ROLLUP_DELAY_MILLIS("300000"),
    STRING_METRICS_DROPPED("false"),
    TENANTIDS_TO_KEEP(""),

    USE_ES_FOR_UNITS("false"),
    // Should at least be equal to the number of the netty worker threads, if http module is getting loaded
    ES_UNIT_THREADS("50"),
    ROLLUP_ON_READ_THREADS("50"),
    TURN_OFF_RR_MPLOT("false");

    static {
        Configuration.getInstance().loadDefaults(CoreConfig.values());
    }
    private String defaultValue;
    private CoreConfig(String value) {
        this.defaultValue = value;
    }
    public String getDefaultValue() {
        return defaultValue;
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/EventListenerService.java
/*
* Copyright 2013 Rackspace
*
*    Licensed under the Apache License, Version 2.0 (the "License");
*    you may not use this file except in compliance with the License.
*    You may obtain a copy of the License at
*
*        http://www.apache.org/licenses/LICENSE-2.0
*
*    Unless required by applicable law or agreed to in writing, software
*    distributed under the License is distributed on an "AS IS" BASIS,
*    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
*    See the License for the specific language governing permissions and
*    limitations under the License.
*/

package com.rackspacecloud.blueflood.service;

public interface EventListenerService {
    public void startService();
    public void stopService();
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/HistogramRollupRunnable.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.codahale.metrics.Timer;
import com.netflix.astyanax.model.ColumnFamily;
import com.rackspacecloud.blueflood.exceptions.GranularityException;
import com.rackspacecloud.blueflood.io.AstyanaxReader;
import com.rackspacecloud.blueflood.io.CassandraModel;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.types.*;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.codahale.metrics.MetricRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class HistogramRollupRunnable extends RollupRunnable {
    private static final Logger log = LoggerFactory.getLogger(HistogramRollupRunnable.class);

    private static final Timer calcTimer = Metrics.getRegistry().timer(MetricRegistry.name(RollupRunnable.class, "Read And Calculate Histogram"));

    public HistogramRollupRunnable(RollupExecutionContext executionContext,
                                   SingleRollupReadContext singleRollupReadContext,
                                   RollupBatchWriter rollupBatchWriter) {
        super(executionContext, singleRollupReadContext, rollupBatchWriter);
    }

    public void run() {
        singleRollupReadContext.getWaitHist().update(System.currentTimeMillis() - startWait);
        Granularity dstGran = singleRollupReadContext.getRollupGranularity();
        Granularity srcGran;
        try {
            singleRollupReadContext.getRollupGranularity().finer();
        } catch (GranularityException ex) {
            executionContext.decrementReadCounter();
            return; // no work to be done.
        }

        if (dstGran.isCoarser(Granularity.MIN_5)) {
            srcGran = Granularity.MIN_5;
        } else {
            srcGran = Granularity.FULL;
        }

        if (log.isDebugEnabled()) {
            log.debug("Executing histogram rollup from {} for {} {}", new Object[] {
                    srcGran.shortName(),
                    singleRollupReadContext.getRange().toString(),
                    singleRollupReadContext.getLocator()});
        }

        Timer.Context timerContext = singleRollupReadContext.getExecuteTimer().time();
        try {
            // Read data and compute rollup
            Points<HistogramRollup> input;
            Rollup rollup = null;
            ColumnFamily<Locator, Long> srcCF;
            ColumnFamily<Locator, Long> dstCF = CassandraModel.getColumnFamily(HistogramRollup.class, dstGran);
            RollupType rollupType = RollupType.fromString((String) rollupTypeCache.get(singleRollupReadContext.getLocator(),
                    MetricMetadata.ROLLUP_TYPE.name().toLowerCase()));

            if (rollupType != RollupType.BF_BASIC) { // Do not compute histogram for statsd metrics.
                executionContext.decrementReadCounter();
                timerContext.stop();
                return;
            }

            if (srcGran == Granularity.MIN_5) {
                srcCF = CassandraModel.CF_METRICS_FULL;
            } else {
                // Coarser histograms are always computed from 5 MIN histograms for error minimization
                srcCF = CassandraModel.CF_METRICS_HIST_5M;
            }

            Timer.Context calcrollupContext = calcTimer.time();
            try {
                input = AstyanaxReader.getInstance().getDataToRoll(
                            HistogramRollup.class,
                            singleRollupReadContext.getLocator(),
                            singleRollupReadContext.getRange(),
                            srcCF);

                // next, compute the rollup.
                rollup =  RollupRunnable.getRollupComputer(RollupType.BF_HISTOGRAMS, srcGran).compute(input);
            } finally {
                calcrollupContext.stop();
            }

            if (rollup != null) {
                rollupBatchWriter.enqueueRollupForWrite(new SingleRollupWriteContext(rollup, singleRollupReadContext, dstCF));
            }
            RollupService.lastRollupTime.set(System.currentTimeMillis());
        } catch (Throwable th) {
            log.error("Histogram rollup failed; Locator : ", singleRollupReadContext.getLocator()
                    + ", Source Granularity: " + srcGran.name());
        } finally {
            executionContext.decrementReadCounter();
            timerContext.stop();
        }
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/IncomingMetricMetadataAnalyzer.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.codahale.metrics.Timer;
import com.google.common.annotations.VisibleForTesting;
import com.rackspacecloud.blueflood.exceptions.CacheException;
import com.rackspacecloud.blueflood.cache.MetadataCache;
import com.rackspacecloud.blueflood.exceptions.IncomingMetricException;
import com.rackspacecloud.blueflood.exceptions.IncomingTypeException;
import com.rackspacecloud.blueflood.exceptions.IncomingUnitException;
import com.rackspacecloud.blueflood.types.*;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.rackspacecloud.blueflood.utils.Util;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

public class IncomingMetricMetadataAnalyzer {
    private static final Logger log = LoggerFactory.getLogger(IncomingMetricMetadataAnalyzer.class);
    private static Timer scanMetricsTimer = Metrics.timer(IncomingMetricMetadataAnalyzer.class, "Scan meta for metrics");
    private static Timer checkMetaTimer = Metrics.timer(IncomingMetricMetadataAnalyzer.class, "Check meta");
    private static Configuration config = Configuration.getInstance();
    private static boolean USE_ES_FOR_UNITS = false;
    private static boolean ES_MODULE_FOUND = false;

    private final MetadataCache cache;
    
    public IncomingMetricMetadataAnalyzer(MetadataCache cache) {
        this.cache = cache;
        USE_ES_FOR_UNITS = config.getBooleanProperty(CoreConfig.USE_ES_FOR_UNITS);
        ES_MODULE_FOUND = config.getListProperty(CoreConfig.DISCOVERY_MODULES).contains(Util.ElasticIOPath);
    }
    
    public Collection<IncomingMetricException> scanMetrics(Collection<IMetric> metrics) {
        List<IncomingMetricException> problems = new ArrayList<IncomingMetricException>();

        Timer.Context ctx = scanMetricsTimer.time();
        for (IMetric metric : metrics) {
            try {
                if (metric instanceof Metric) {
                    Collection<IncomingMetricException> metricProblems = checkMetric((Metric) metric);
                    if (metricProblems != null) {
                        problems.addAll(metricProblems);
                    }
                }
            } catch (CacheException ex) {
                log.warn(ex.getMessage(), ex);
            }
        }
        ctx.stop();

        return problems;
    }

    private IncomingMetricException checkMeta(Locator locator, String key, String incoming) throws CacheException {
        Timer.Context ctx = checkMetaTimer.time();
        try {
            String existing = cache.get(locator, key, String.class);

            // always update the cache. it is smart enough to avoid needless writes.
            cache.put(locator, key, incoming);

            boolean differs = existing != null && !incoming.equals(existing);
            if (differs) {
                if (key.equals(MetricMetadata.UNIT.name().toLowerCase())) {
                    return new IncomingUnitException(locator, existing, incoming);
                } else {
                    return new IncomingTypeException(locator, existing, incoming);
                }
            }
        } finally {
            ctx.stop();
        }

        return null;
    }

    private Collection<IncomingMetricException> checkMetric(Metric metric) throws CacheException {
        if (metric == null) {
            return null;
        }

        List<IncomingMetricException> problems = new ArrayList<IncomingMetricException>();
        IncomingMetricException typeProblem = null;

        if (metric.getDataType() != DataType.NUMERIC) {
            typeProblem = checkMeta(metric.getLocator(), MetricMetadata.TYPE.name().toLowerCase(),
                    metric.getDataType().toString());
        }

        if (typeProblem != null) {
            problems.add(typeProblem);
        }

        if (!USE_ES_FOR_UNITS || !ES_MODULE_FOUND) {
            if (USE_ES_FOR_UNITS && !ES_MODULE_FOUND) {
                log.warn("USE_ES_FOR_UNITS config found but ES discovery module not found in the config, will use the metadata cache for units");
            }
            IncomingMetricException unitProblem = checkMeta(metric.getLocator(), MetricMetadata.UNIT.name().toLowerCase(),
                    metric.getUnit());
            if (unitProblem != null) {
                problems.add(unitProblem);
            }
        }
        return problems;
    }

    @VisibleForTesting
    public static void setEsForUnits(boolean setEsForUnits) {
        USE_ES_FOR_UNITS = setEsForUnits;
    }

    @VisibleForTesting
    public static void setEsModuleFoundForUnits(boolean setEsModuleFound) {
        ES_MODULE_FOUND = setEsModuleFound;
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/IngestionContext.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

public interface IngestionContext {
    /**
     * Marks a slot dirty. This is only called on a subset of hoist environments where Blueflood runs.
     * @param millis current timestamp.
     * @param shard shard to be updated. value within [0, 128).
     */
    public void update(long millis, int shard);
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/IngestionService.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.rackspacecloud.blueflood.io.IMetricsWriter;

public interface IngestionService {
    public void startService(ScheduleContext context, IMetricsWriter writer);
}



File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/LocatorFetchRunnable.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.codahale.metrics.Timer;
import com.rackspacecloud.blueflood.io.AstyanaxReader;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.rollup.SlotKey;
import com.rackspacecloud.blueflood.types.Locator;
import com.rackspacecloud.blueflood.types.Range;
import com.rackspacecloud.blueflood.utils.Metrics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadPoolExecutor;

/**
 * fetches locators for a given slot and feeds a worker queue with rollup work. When those are all done notifies the
 * RollupService that slot can be removed from running.
  */
class LocatorFetchRunnable implements Runnable {
    private static final Logger log = LoggerFactory.getLogger(LocatorFetchRunnable.class);
    private static final int LOCATOR_WAIT_FOR_ALL_SECS = 1000;
    
    private final ThreadPoolExecutor rollupReadExecutor;
    private final ThreadPoolExecutor rollupWriteExecutor;
    private final SlotKey parentSlotKey;
    private final ScheduleContext scheduleCtx;
    private final long serverTime;
    private static final Timer rollupLocatorExecuteTimer = Metrics.timer(RollupService.class, "Locate and Schedule Rollups for Slot");
    private static final boolean enableHistograms = Configuration.getInstance().
            getBooleanProperty(CoreConfig.ENABLE_HISTOGRAMS);

    LocatorFetchRunnable(ScheduleContext scheduleCtx, SlotKey destSlotKey, ThreadPoolExecutor rollupReadExecutor, ThreadPoolExecutor rollupWriteExecutor) {
        this.rollupReadExecutor = rollupReadExecutor;
        this.rollupWriteExecutor = rollupWriteExecutor;
        this.parentSlotKey = destSlotKey;
        this.scheduleCtx = scheduleCtx;
        this.serverTime = scheduleCtx.getCurrentTimeMillis();
    }
    
    public void run() {
        final Timer.Context timerCtx = rollupLocatorExecuteTimer.time();
        final Granularity gran = parentSlotKey.getGranularity();
        final int parentSlot = parentSlotKey.getSlot();
        final int shard = parentSlotKey.getShard();
        final Range parentRange = gran.deriveRange(parentSlot, serverTime);

        try {
            gran.finer();
        } catch (Exception ex) {
            log.error("No finer granularity available than " + gran);
            return;
        }

        if (log.isTraceEnabled())
            log.trace("Getting locators for {} {} @ {}", new Object[]{parentSlotKey, parentRange.toString(), scheduleCtx.getCurrentTimeMillis()});
        // todo: I can see this set becoming a memory hog.  There might be a better way of doing this.
        long waitStart = System.currentTimeMillis();
        int rollCount = 0;

        final RollupExecutionContext executionContext = new RollupExecutionContext(Thread.currentThread());
        final RollupBatchWriter rollupBatchWriter = new RollupBatchWriter(rollupWriteExecutor, executionContext);
        Set<Locator> locators = new HashSet<Locator>();

        try {
            locators.addAll(AstyanaxReader.getInstance().getLocatorsToRollup(shard));
        } catch (RuntimeException e) {
            executionContext.markUnsuccessful(e);
            log.error("Failed reading locators for slot: " + parentSlot, e);
        }
        for (Locator locator : locators) {
            if (log.isTraceEnabled())
                log.trace("Rolling up (check,metric,dimension) {} for (gran,slot,shard) {}", locator, parentSlotKey);
            try {
                executionContext.incrementReadCounter();
                final SingleRollupReadContext singleRollupReadContext = new SingleRollupReadContext(locator, parentRange, gran);
                rollupReadExecutor.execute(new RollupRunnable(executionContext, singleRollupReadContext, rollupBatchWriter));
                rollCount += 1;
            } catch (Throwable any) {
                // continue on, but log the problem so that we can fix things later.
                executionContext.markUnsuccessful(any);
                executionContext.decrementReadCounter();
                log.error(any.getMessage(), any);
                log.error("BasicRollup failed for {} at {}", parentSlotKey, serverTime);
            }

            if (enableHistograms) {
                // Also, compute histograms. Histograms for > 5 MIN granularity are always computed from 5 MIN histograms.
                try {
                    executionContext.incrementReadCounter();
                    final SingleRollupReadContext singleRollupReadContext = new SingleRollupReadContext(locator,
                            parentRange, gran);
                    rollupReadExecutor.execute(new HistogramRollupRunnable(executionContext, singleRollupReadContext,
                            rollupBatchWriter));
                    rollCount += 1;
                } catch (RejectedExecutionException ex) {
                    executionContext.markUnsuccessful(ex); // We should ideally only recompute the failed locators alone.
                    executionContext.decrementReadCounter();
                    log.error("Histogram rollup rejected for {} at {}", parentSlotKey, serverTime);
                    log.error("Exception: ", ex);
                } catch (Exception ex) { // do not retrigger rollups when they fail. histograms are fine to be lost.
                    executionContext.decrementReadCounter();
                    log.error("Histogram rollup rejected for {} at {}", parentSlotKey, serverTime);
                    log.error("Exception: ", ex);
                }
            }
        }
        
        // now wait until ctx is drained. someone needs to be notified.
        log.debug("Waiting for rollups to finish for " + parentSlotKey);
        while (!executionContext.doneReading() || !executionContext.doneWriting()) {
            if (executionContext.doneReading()) {
                rollupBatchWriter.drainBatch(); // gets any remaining rollups enqueued for put. should be no-op after being called once
            }
            try {
                Thread.currentThread().sleep(LOCATOR_WAIT_FOR_ALL_SECS * 1000);
            } catch (InterruptedException ex) {
                if (log.isTraceEnabled())
                    log.trace("Woken wile waiting for rollups to coalesce for {} {}", parentSlotKey);
            } finally {
                String verb = executionContext.doneReading() ? "writing" : "reading";
                log.debug("Still waiting for rollups to finish {} for {} {}", new Object[] {verb, parentSlotKey, System.currentTimeMillis() - waitStart });
            }
        }
        if (log.isDebugEnabled())
            log.debug("Finished {} rollups for (gran,slot,shard) {} in {}", new Object[] {rollCount, parentSlotKey, System.currentTimeMillis() - waitStart});

        if (executionContext.wasSuccessful()) {
            this.scheduleCtx.clearFromRunning(parentSlotKey);
        } else {
            log.error("Performing BasicRollups for {} failed", parentSlotKey);
            this.scheduleCtx.pushBackToScheduled(parentSlotKey, false);
        }

        timerCtx.stop();
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/NoOpShardLockManager.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;


public class NoOpShardLockManager implements ShardLockManager {
    
    public void addShard(int shard) {}
    
    public void removeShard(int shard) {}

    public boolean canWork(int shard) {
        return true;
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/QueryService.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

public interface QueryService {
    public void startService();
}



File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/RollupBatchWriteRunnable.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.codahale.metrics.Histogram;
import com.codahale.metrics.Timer;
import com.netflix.astyanax.connectionpool.exceptions.ConnectionException;
import com.rackspacecloud.blueflood.io.AstyanaxWriter;
import com.rackspacecloud.blueflood.utils.Metrics;

import java.util.ArrayList;

public class RollupBatchWriteRunnable  implements Runnable {
    private final RollupExecutionContext executionContext;
    private final ArrayList<SingleRollupWriteContext> writeContexts;
    private static final Histogram rollupsPerBatch = Metrics.histogram(RollupService.class, "Rollups Per Batch");
    private static final Timer batchWriteTimer = Metrics.timer(RollupService.class, "Rollup Batch Write");

    public RollupBatchWriteRunnable(ArrayList<SingleRollupWriteContext> writeContexts, RollupExecutionContext executionContext) {
        this.writeContexts = writeContexts;
        this.executionContext = executionContext;
    }

    @Override
    public void run() {
        Timer.Context ctx = batchWriteTimer.time();
        try {
            AstyanaxWriter.getInstance().insertRollups(writeContexts);
        } catch (ConnectionException e) {
            executionContext.markUnsuccessful(e);
        }
        executionContext.decrementWriteCounter(writeContexts.size());
        rollupsPerBatch.update(writeContexts.size());
        RollupService.lastRollupTime.set(System.currentTimeMillis());
        ctx.stop();
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/RollupBatchWriter.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.NoSuchElementException;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.ThreadPoolExecutor;

// Batches rollup writes
public class RollupBatchWriter {
    private final Logger log = LoggerFactory.getLogger(RollupBatchWriter.class);
    private final ThreadPoolExecutor executor;
    private final RollupExecutionContext context;
    private final ConcurrentLinkedQueue<SingleRollupWriteContext> rollupQueue = new ConcurrentLinkedQueue<SingleRollupWriteContext>();
    private static final int ROLLUP_BATCH_MIN_SIZE = Configuration.getInstance().getIntegerProperty(CoreConfig.ROLLUP_BATCH_MIN_SIZE);
    private static final int ROLLUP_BATCH_MAX_SIZE = Configuration.getInstance().getIntegerProperty(CoreConfig.ROLLUP_BATCH_MAX_SIZE);

    public RollupBatchWriter(ThreadPoolExecutor executor, RollupExecutionContext context) {
        this.executor = executor;
        this.context = context;
    }


    public void enqueueRollupForWrite(SingleRollupWriteContext rollupWriteContext) {
        rollupQueue.add(rollupWriteContext);
        context.incrementWriteCounter();
        // enqueue MIN_SIZE batches only if the threadpool is unsaturated. else, enqueue when we have >= MAX_SIZE pending
        if (rollupQueue.size() >= ROLLUP_BATCH_MIN_SIZE) {
            if (executor.getActiveCount() < executor.getPoolSize() || rollupQueue.size() >= ROLLUP_BATCH_MAX_SIZE) {
                drainBatch();
            }
        }
    }

    public synchronized void drainBatch() {
        ArrayList<SingleRollupWriteContext> writeContexts = new ArrayList<SingleRollupWriteContext>();
        SingleRollupWriteContext ctx;
        try {
            for (int i=0; i<=ROLLUP_BATCH_MAX_SIZE; i++) {
                writeContexts.add(rollupQueue.remove());
            }
        } catch (NoSuchElementException e) {
            // pass
        }
        if (writeContexts.size() > 0) {
            executor.execute(new RollupBatchWriteRunnable(writeContexts, context));
        }
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/RollupRunnable.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.codahale.metrics.Meter;
import com.codahale.metrics.Timer;
import com.netflix.astyanax.model.ColumnFamily;
import com.rackspacecloud.blueflood.cache.MetadataCache;
import com.rackspacecloud.blueflood.exceptions.GranularityException;
import com.rackspacecloud.blueflood.io.AstyanaxReader;
import com.rackspacecloud.blueflood.io.CassandraModel;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.types.*;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import com.rackspacecloud.blueflood.eventemitter.RollupEventEmitter;
import com.rackspacecloud.blueflood.eventemitter.RollupEvent;

import java.util.HashMap;
import java.util.concurrent.TimeUnit;

/** rolls up data into one data point, inserts that data point. */
public class RollupRunnable implements Runnable {
    private static final Logger log = LoggerFactory.getLogger(RollupRunnable.class);

    private static final Timer writeTimer = Metrics.timer(RollupRunnable.class, "Write Rollup");
    protected final SingleRollupReadContext singleRollupReadContext;
    protected static final MetadataCache rollupTypeCache = MetadataCache.createLoadingCacheInstance(
            new TimeValue(48, TimeUnit.HOURS), // todo: need a good default expiration here.
            Configuration.getInstance().getIntegerProperty(CoreConfig.MAX_ROLLUP_READ_THREADS));

    protected final RollupExecutionContext executionContext;
    protected final RollupBatchWriter rollupBatchWriter;
    protected final long startWait;

    private static final Timer calcTimer = Metrics.timer(RollupRunnable.class, "Read And Calculate Rollup");
    private static final Meter noPointsToCalculateRollup = Metrics.meter(RollupRunnable.class, "No points to calculate rollup");
    private static HashMap<Granularity, Meter> granToMeters = new HashMap<Granularity, Meter>();

    static {
        for (Granularity rollupGranularity : Granularity.rollupGranularities()) {
            granToMeters.put(rollupGranularity, Metrics.meter(RollupRunnable.class, String.format("%s Rollup", rollupGranularity.shortName())));
        }
    }

    public RollupRunnable(RollupExecutionContext executionContext, SingleRollupReadContext singleRollupReadContext, RollupBatchWriter rollupBatchWriter) {
        this.executionContext = executionContext;
        this.singleRollupReadContext = singleRollupReadContext;
        this.rollupBatchWriter = rollupBatchWriter;
        startWait = System.currentTimeMillis();
    }
    
    public void run() {
        // done waiting.
        singleRollupReadContext.getWaitHist().update(System.currentTimeMillis() - startWait);

        Granularity srcGran;
        try {
            srcGran = singleRollupReadContext.getRollupGranularity().finer();
        } catch (GranularityException ex) {
            executionContext.decrementReadCounter();
            return; // no work to be done.
        }

        if (log.isDebugEnabled()) {
            log.trace("Executing rollup from {} for {} {}", new Object[] {
                    srcGran.shortName(),
                    singleRollupReadContext.getRange().toString(),
                    singleRollupReadContext.getLocator()});
        }

        // start timing this action.
        Timer.Context timerContext = singleRollupReadContext.getExecuteTimer().time();

        try {
            Timer.Context calcrollupContext = calcTimer.time();
            granToMeters.get(srcGran.coarser()).mark();

            // Read data and compute rollup
            Points input;
            Rollup rollup = null;
            RollupType rollupType = RollupType.fromString((String) rollupTypeCache.get(
                    singleRollupReadContext.getLocator(), MetricMetadata.ROLLUP_TYPE.name().toLowerCase()));
            Class<? extends Rollup> rollupClass = RollupType.classOf(rollupType, srcGran.coarser());
            ColumnFamily<Locator, Long> srcCF = CassandraModel.getColumnFamily(rollupClass, srcGran);
            ColumnFamily<Locator, Long> dstCF = CassandraModel.getColumnFamily(rollupClass, srcGran.coarser());

            try {
                // first, get the points.
                input = AstyanaxReader.getInstance().getDataToRoll(rollupClass,
                        singleRollupReadContext.getLocator(), singleRollupReadContext.getRange(), srcCF);

                if (input.isEmpty()) {
                    noPointsToCalculateRollup.mark();
                    return;
                }

                // next, compute the rollup.
                rollup =  RollupRunnable.getRollupComputer(rollupType, srcGran).compute(input);
            } finally {
                calcrollupContext.stop();
            }
            // now enqueue the new rollup for writing.
            rollupBatchWriter.enqueueRollupForWrite(new SingleRollupWriteContext(rollup, singleRollupReadContext, dstCF));

            RollupService.lastRollupTime.set(System.currentTimeMillis());
            //Emit a rollup event to eventemitter
            RollupEventEmitter.getInstance().emit(RollupEventEmitter.ROLLUP_EVENT_NAME,
                    new RollupEvent(singleRollupReadContext.getLocator(), rollup,
                            AstyanaxReader.getUnitString(singleRollupReadContext.getLocator()),
                            singleRollupReadContext.getRollupGranularity().name(),
                            singleRollupReadContext.getRange().getStart()));
        } catch (Exception e) {
            log.error("Rollup failed; Locator: {}, Source Granularity: {}, For period: {}", new Object[] {
                    singleRollupReadContext.getLocator(),
                    singleRollupReadContext.getRange().toString(),
                    srcGran.name(),
                    e});
        } finally {
            executionContext.decrementReadCounter();
            timerContext.stop();
        }
    }

    // dertmine which DataType to use for serialization.
    public static Rollup.Type getRollupComputer(RollupType srcType, Granularity srcGran) {
        switch (srcType) {
            case COUNTER:
                return Rollup.CounterFromCounter;
            case TIMER:
                return Rollup.TimerFromTimer;
            case GAUGE:
                return Rollup.GaugeFromGauge;
            case BF_HISTOGRAMS:
                return srcGran == Granularity.FULL ? Rollup.HistogramFromRaw : Rollup.HistogramFromHistogram;
            case BF_BASIC:
                return srcGran == Granularity.FULL ? Rollup.BasicFromRaw : Rollup.BasicFromBasic;
            case SET:
                return Rollup.SetFromSet;
            default:
                break;
        }
        throw new IllegalArgumentException(String.format("Cannot compute rollups for %s from %s", srcType.name(), srcGran.shortName()));
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/RollupService.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.codahale.metrics.*;
import com.codahale.metrics.Timer;
import com.rackspacecloud.blueflood.concurrent.InstrumentedThreadPoolExecutor;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.rollup.SlotKey;
import com.rackspacecloud.blueflood.tools.jmx.JmxBooleanGauge;
import com.rackspacecloud.blueflood.utils.Metrics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.management.MBeanServer;
import javax.management.ObjectName;
import java.lang.management.ManagementFactory;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

public class RollupService implements Runnable, RollupServiceMBean {
    private static final Logger log = LoggerFactory.getLogger(RollupService.class);
    private final long rollupDelayMillis;

    private final ScheduleContext context;
    private final ShardStateManager shardStateManager;
    private final Timer polltimer = Metrics.timer(RollupService.class, "Poll Timer");
    private final Meter rejectedSlotChecks = Metrics.meter(RollupService.class, "Rejected Slot Checks");
    private final ThreadPoolExecutor locatorFetchExecutors;
    private final ThreadPoolExecutor rollupReadExecutors;
    private final ThreadPoolExecutor rollupWriteExecutors;
    private long pollerPeriod = Configuration.getInstance().getIntegerProperty(CoreConfig.SCHEDULE_POLL_PERIOD);
    private final long configRefreshInterval = Configuration.getInstance().getIntegerProperty(CoreConfig.CONFIG_REFRESH_PERIOD);
    private transient Thread thread;

    private long lastSlotCheckFinishedAt = 0L;

    private boolean active = true;
    private boolean keepingServerTime = true;

    private Gauge activeGauge;
    private Gauge inflightRollupGauge;
    private Gauge pollerPeriodGauge;
    private Gauge serverTimeGauge;
    private Gauge rollupConcurrencyGauge;
    private Gauge scheduledSlotCheckGauge;
    private Gauge secondsSinceLastSlotCheckGauge;
    private Gauge queuedRollupGauge;
    private Gauge slotCheckConcurrencyGauge;
    private Gauge recentlyScheduledShardGauge;
    private Gauge managedShardGauge;

    protected static final AtomicLong lastRollupTime = new AtomicLong(System.currentTimeMillis());
    private static final Gauge<Long> timeSinceLastRollupGauge;

    static {
        timeSinceLastRollupGauge = new Gauge<Long>() {
            @Override
            public Long getValue() {
                return System.currentTimeMillis() - lastRollupTime.get();
            }
        };
        Metrics.getRegistry().register(MetricRegistry.name(RollupService.class, "Milliseconds Since Last Rollup"), timeSinceLastRollupGauge);
    }

    public RollupService(ScheduleContext context) {
        this.context = context;
        this.shardStateManager = context.getShardStateManager();

        try {
            final MBeanServer mbs = ManagementFactory.getPlatformMBeanServer();
            final String name = String.format("com.rackspacecloud.blueflood.service:type=%s", getClass().getSimpleName());
            final ObjectName nameObj = new ObjectName(name);
            mbs.registerMBean(this, nameObj);

            MetricRegistry reg = Metrics.getRegistry();
            activeGauge = reg.register(MetricRegistry.name(RollupService.class, "Active"),
                    new JmxBooleanGauge(nameObj, "Active"));
            inflightRollupGauge = reg.register(MetricRegistry.name(RollupService.class, "In Flight Rollup Count"),
                    new JmxAttributeGauge(nameObj, "InFlightRollupCount"));

            pollerPeriodGauge = reg.register(MetricRegistry.name(RollupService.class, "Poller Period"),
                    new JmxAttributeGauge(nameObj, "PollerPeriod"));
            queuedRollupGauge = reg.register(MetricRegistry.name(RollupService.class, "Queued Rollup Count"),
                    new JmxAttributeGauge(nameObj, "QueuedRollupCount"));
            rollupConcurrencyGauge = reg.register(MetricRegistry.name(RollupService.class, "Rollup Concurrency"),
                    new JmxAttributeGauge(nameObj, "RollupConcurrency"));
            scheduledSlotCheckGauge = reg.register(MetricRegistry.name(RollupService.class, "Scheduled Slot Check"),
                    new JmxAttributeGauge(nameObj, "ScheduledSlotCheckCount"));
            secondsSinceLastSlotCheckGauge = reg.register(MetricRegistry.name(RollupService.class, "Seconds Since Last Slot Check"),
                    new JmxAttributeGauge(nameObj, "SecondsSinceLastSlotCheck"));
            serverTimeGauge = reg.register(MetricRegistry.name(RollupService.class, "Server Time"),
                    new JmxAttributeGauge(nameObj, "ServerTime"));
            slotCheckConcurrencyGauge = reg.register(MetricRegistry.name(RollupService.class, "Slot Check Concurrency"),
                    new JmxAttributeGauge(nameObj, "SlotCheckConcurrency"));

            recentlyScheduledShardGauge = reg.register(MetricRegistry.name(RollupService.class, "Recently Scheduled Shards"),
                    new Gauge<Integer>() {
                        @Override
                        public Integer getValue() {
                            return getRecentlyScheduledShards().size();
                        }
                    });

            managedShardGauge = reg.register(MetricRegistry.name(RollupService.class, "Managed Shards"),
                    new Gauge<Integer>() {
                        @Override
                        public Integer getValue() {
                            return getManagedShards().size();
                        }
                    });

        } catch (Exception exc) {
            log.error("Unable to register mbean for " + getClass().getSimpleName(), exc);
        }

        // NOTE: higher locatorFetchConcurrency means that the queue used in rollupReadExecutors needs to be correspondingly
        // higher.
        Configuration config = Configuration.getInstance();
        rollupDelayMillis = config.getLongProperty("ROLLUP_DELAY_MILLIS");
        final int locatorFetchConcurrency = config.getIntegerProperty(CoreConfig.MAX_LOCATOR_FETCH_THREADS);
        locatorFetchExecutors = new ThreadPoolExecutor(
            locatorFetchConcurrency, locatorFetchConcurrency,
            30, TimeUnit.SECONDS,
            new ArrayBlockingQueue<Runnable>(locatorFetchConcurrency * 5),
            Executors.defaultThreadFactory(),
            new RejectedExecutionHandler() {
                public void rejectedExecution(Runnable r, ThreadPoolExecutor executor) {
                    // in this case, we want to throw a RejectedExecutionException so that the slot can be removed
                    // from the running queue.
                    throw new RejectedExecutionException("Threadpool is saturated. unable to service this slot.");
                }
            }
        ) {
            @Override
            protected void afterExecute(Runnable r, Throwable t) {
                lastSlotCheckFinishedAt = RollupService.this.context.getCurrentTimeMillis();
                super.afterExecute(r, t);
            }
        };
        InstrumentedThreadPoolExecutor.instrument(locatorFetchExecutors, "LocatorFetchThreadPool");

        // unbounded work queue.
        final BlockingQueue<Runnable> rollupReadQueue = new LinkedBlockingQueue<Runnable>();

        rollupReadExecutors = new ThreadPoolExecutor(
            // "RollupReadsThreadpool",
            config.getIntegerProperty(CoreConfig.MAX_ROLLUP_READ_THREADS),
            config.getIntegerProperty(CoreConfig.MAX_ROLLUP_READ_THREADS),
            30, TimeUnit.SECONDS,
            rollupReadQueue,
            Executors.defaultThreadFactory(),
            new ThreadPoolExecutor.AbortPolicy()
        );
        final BlockingQueue<Runnable> rollupWriteQueue = new LinkedBlockingQueue<Runnable>();
        rollupWriteExecutors = new ThreadPoolExecutor(
                // "RollupWritesThreadpool",
                config.getIntegerProperty(CoreConfig.MAX_ROLLUP_WRITE_THREADS),
                config.getIntegerProperty(CoreConfig.MAX_ROLLUP_WRITE_THREADS),
                30, TimeUnit.SECONDS,
                rollupWriteQueue,
                Executors.defaultThreadFactory(),
                new ThreadPoolExecutor.AbortPolicy()
        );
        InstrumentedThreadPoolExecutor.instrument(rollupReadExecutors, "RollupReadsThreadpool");
        InstrumentedThreadPoolExecutor.instrument(rollupWriteExecutors, "RollupWritesThreadpool");
    }

    public void forcePoll() {
        thread.interrupt();
    }

    final void poll() {
        Timer.Context timer = polltimer.time();
        // schedule for rollup anything that has not been updated in ROLLUP_DELAY_SECS
        context.scheduleSlotsOlderThan(rollupDelayMillis);
        timer.stop();
    }

    public void run() {
        thread = Thread.currentThread();

        while (true) {
            long startRun = System.currentTimeMillis();

            poll();

            // if there are schedules slots, run what we can.
            boolean rejected = false;
            while (context.hasScheduled() && !rejected && active) {
                final SlotKey slotKey = context.getNextScheduled();
                if (slotKey == null) { continue; }
                try {
                    log.debug("Scheduling slotKey {} @ {}", slotKey, context.getCurrentTimeMillis());
                    locatorFetchExecutors.execute(new LocatorFetchRunnable(context, slotKey, rollupReadExecutors, rollupWriteExecutors));
                } catch (RejectedExecutionException ex) {
                    // puts it back at the top of the list of scheduled slots.  When this happens it means that
                    // there is too much rollup work to do. if the CPU cores are not tapped out, it means you don't
                    // have enough threads allocated to processing rollups or slot checks.
                    rejectedSlotChecks.mark();
                    context.pushBackToScheduled(slotKey, true);
                    rejected = true;
                }
            }
            long endRun = System.currentTimeMillis();
            if (endRun - startRun > pollerPeriod)
                log.error("It took longer than {} to poll for rollups.", pollerPeriod);
            else
                try {
                    thread.sleep(Math.max(0, pollerPeriod - endRun + startRun));
                } catch (Exception ex) {
                    log.debug("RollupService poller woke up");
                }
        }
    }

    //
    // JMX exposure
    //


    // set the server time in millis.
    public synchronized void setServerTime(long millis) {
        log.info("Manually setting server time to {}  {}", millis, new java.util.Date(millis));
        context.setCurrentTimeMillis(millis);
    }

    // get the server time in seconds.
    public synchronized long getServerTime() { return context.getCurrentTimeMillis(); }

    public synchronized void setKeepingServerTime(boolean b) { keepingServerTime = b; }

    public synchronized boolean getKeepingServerTime() { return keepingServerTime; }

    public synchronized void setPollerPeriod(long l) {
        // todo: alter the design so that you don't have to keep a thread reference around. one way to do this is to
        // override the function in the caller (where the thread is accessible).
        pollerPeriod = l;
        if (thread != null)
            thread.interrupt();
    }

    public synchronized long getPollerPeriod() { return pollerPeriod; }

    public synchronized int getScheduledSlotCheckCount() { return context.getScheduledCount(); }

    public synchronized int getSecondsSinceLastSlotCheck() {
        return (int)((context.getCurrentTimeMillis() - lastSlotCheckFinishedAt) / 1000);
    }

    public synchronized int getSlotCheckConcurrency() {
        return locatorFetchExecutors.getMaximumPoolSize();
    }

    public synchronized void setSlotCheckConcurrency(int i) {
        locatorFetchExecutors.setCorePoolSize(i);
        locatorFetchExecutors.setMaximumPoolSize(i);
    }

    public synchronized int getRollupConcurrency() {
        return rollupReadExecutors.getMaximumPoolSize();
    }

    public synchronized void setRollupConcurrency(int i) {
        rollupReadExecutors.setCorePoolSize(i);
        rollupReadExecutors.setMaximumPoolSize(i);
    }

    public synchronized int getQueuedRollupCount() { return rollupReadExecutors.getQueue().size(); }
    public synchronized int getInFlightRollupCount() { return rollupReadExecutors.getActiveCount(); }

    public synchronized boolean getActive() { return active; }

    public synchronized void setActive(boolean b) {
        active = b;
        if (active && thread != null)
            thread.interrupt();
    }

    /**
     * Add a shard to be managed (via JMX)
     *
     * @param shard shard to be added
     */
    public void addShard(Integer shard) {
        if (!shardStateManager.getManagedShards().contains(shard))
            context.addShard(shard);
    }

    /**
     * Remove a shard from being managed (via JMX)
     *
     * @param shard shard to be removed
     */
    public void removeShard(Integer shard) {
        if (shardStateManager.getManagedShards().contains(shard))
            context.removeShard(shard);
    }

    /**
     * Get list of managed shards (via JMX)
     *
     * @return list of managed shards (unmodifiable collection)
     */
    public Collection<Integer> getManagedShards() {
        return new TreeSet<Integer>(shardStateManager.getManagedShards());
    }

    public synchronized Collection<Integer> getRecentlyScheduledShards() {
        // note: already sorted when it comes from the context.
        return context.getRecentlyScheduledShards();
    }

    public synchronized Collection<String> getOldestUnrolledSlotPerGranularity(int shard) {
        final Set<String> results = new HashSet<String>();

        for (Granularity g : Granularity.rollupGranularities()) {
            final Map<Integer, UpdateStamp> stateTimestamps = context.getSlotStamps(g, shard);
            if (stateTimestamps == null || stateTimestamps.isEmpty()) {
                continue;
            }

            // Iterate through the map of slot to UpdateStamp and find the oldest one
            SlotState minSlot = new SlotState().withTimestamp(System.currentTimeMillis());
            boolean add = false;
            for (Map.Entry<Integer, UpdateStamp> entry : stateTimestamps.entrySet()) {
                final UpdateStamp stamp = entry.getValue();
                if (stamp.getState() != UpdateStamp.State.Rolled && stamp.getTimestamp() < minSlot.getTimestamp()) {
                    minSlot = new SlotState(g, entry.getKey(), stamp.getState()).withTimestamp(stamp.getTimestamp());
                    add = true;
                }
            }

            if (add) {
                results.add(minSlot.toString());
            }
        }

        return results;
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/RollupServiceMBean.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import java.util.Collection;

public interface RollupServiceMBean {
    void setKeepingServerTime(boolean b);
    boolean getKeepingServerTime();
    void setServerTime(long seconds);
    long getServerTime();
    void setPollerPeriod(long l);
    long getPollerPeriod();
    public int getScheduledSlotCheckCount();
    public void forcePoll();
    
    public int getSecondsSinceLastSlotCheck();
    public int getQueuedRollupCount();
    public int getSlotCheckConcurrency();
    public void setSlotCheckConcurrency(int i);
    
    public int getInFlightRollupCount();
    public int getRollupConcurrency();
    public void setRollupConcurrency(int i);
    
    public boolean getActive();
    public void setActive(boolean b);

    /* shard management methods  */
    public void addShard(final Integer shard);
    public void removeShard(final Integer shard);
    public Collection<Integer> getManagedShards();
    
    public Collection<Integer> getRecentlyScheduledShards();

    public Collection<String> getOldestUnrolledSlotPerGranularity(int shard);
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/ScheduleContext.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.codahale.metrics.Meter;
import com.codahale.metrics.Timer;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Ticker;
import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import com.rackspacecloud.blueflood.io.Constants;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.rollup.SlotKey;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.management.MBeanServer;
import javax.management.ObjectName;
import java.lang.management.ManagementFactory;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.TimeUnit;

// keeps track of dirty slots in memory. Operations must be threadsafe.
// todo: explore using ReadWrite locks (might not make a difference).

/**
 * Each node is responsible for sharded slots (time ranges) of rollups.  This class keeps track of the execution of
 * those rollups and the states they are in.  
 * 
 * When synchronizing multiple collections, do it in this order: scheduled -> running.
 */
public class ScheduleContext implements IngestionContext, ScheduleContextMBean {
    private static final Logger log = LoggerFactory.getLogger(ScheduleContext.class);
    private final Timer markSlotDirtyTimer = Metrics.timer(ScheduleContext.class, "Slot Mark Dirty Duration");

    private final ShardStateManager shardStateManager;
    private transient long scheduleTime = 0L;
    
    // these shards have been scheduled in the last 10 minutes.
    private final Cache<Integer, Long> recentlyScheduledShards = CacheBuilder.newBuilder()
            .maximumSize(Constants.NUMBER_OF_SHARDS)
            .expireAfterWrite(10, TimeUnit.MINUTES)
            .build();

    // state
    //
    private final Meter shardOwnershipChanged = Metrics.meter(ScheduleContext.class, "Shard Change Before Running");

    // these are all the slots that are scheduled to run in no particular order. the collection is synchronized to 
    // control updates.
    private final Set<SlotKey> scheduledSlots = new HashSet<SlotKey>();
    
    // same information as scheduledSlots, but order is preserved.  The ordered property is only needed for getting the
    // the next scheduled slot, but most operations are concerned with if a slot is scheduled or not.  When you update
    // one, you must update the other.
    private final List<SlotKey> orderedScheduledSlots = new ArrayList<SlotKey>();
    
    // slots that are running are not scheduled.
    private final Map<SlotKey, Long> runningSlots = new HashMap<SlotKey, Long>();

    // shard lock manager
    private final ShardLockManager lockManager;

    public ScheduleContext(long currentTimeMillis, Collection<Integer> managedShards) {
        this.scheduleTime = currentTimeMillis;
        this.shardStateManager = new ShardStateManager(managedShards, asMillisecondsSinceEpochTicker());
        this.lockManager = new NoOpShardLockManager();
        registerMBean();
    }

    public ScheduleContext(long currentTimeMillis, Collection<Integer> managedShards, String zookeeperCluster) {
        this.scheduleTime = currentTimeMillis;
        this.shardStateManager = new ShardStateManager(managedShards, asMillisecondsSinceEpochTicker());
        ZKBasedShardLockManager lockManager = new ZKBasedShardLockManager(zookeeperCluster, new HashSet<Integer>(shardStateManager.getManagedShards()));
        lockManager.init(new TimeValue(5, TimeUnit.SECONDS));
        this.lockManager = lockManager;
        registerMBean();
    }

    public void setCurrentTimeMillis(long millis){ scheduleTime = millis; }
    public long getCurrentTimeMillis() { return scheduleTime; }

    public ShardStateManager getShardStateManager() {
        return this.shardStateManager;
    }

    /**
     * {@inheritDoc}
     */
    public void update(long millis, int shard) {
        // there are two update paths. for managed shards, we must guard the scheduled and running collections.  but
        // for unmanaged shards, we just let the update happen uncontested.
        final Timer.Context dirtyTimerCtx = markSlotDirtyTimer.time();
        try {
            if (log.isTraceEnabled()) {
                log.trace("Updating {} to {}", shard, millis);
            }
            boolean isManaged = shardStateManager.contains(shard);
            for (Granularity g : Granularity.rollupGranularities()) {
                ShardStateManager.SlotStateManager slotStateManager = shardStateManager.getSlotStateManager(shard, g);
                int slot = g.slot(millis);

                if (isManaged) {
                    synchronized (scheduledSlots) { //put
                        SlotKey key = SlotKey.of(g, slot, shard);
                        if (scheduledSlots.remove(key) && log.isDebugEnabled()) {
                            log.debug("descheduled {}.", key);// don't worry about orderedScheduledSlots
                        }
                    }
                }
                slotStateManager.createOrUpdateForSlotAndMillisecond(slot, millis);
            }
        } finally {
            dirtyTimerCtx.stop();
        }
    }

    // iterates over all active slots, scheduling those that haven't been updated in maxAgeMillis.
    // only one thread should be calling in this puppy.
    void scheduleSlotsOlderThan(long maxAgeMillis) {
        long now = scheduleTime;
        ArrayList<Integer> shardKeys = new ArrayList<Integer>(shardStateManager.getManagedShards());
        Collections.shuffle(shardKeys);

        for (int shard : shardKeys) {
            for (Granularity g : Granularity.rollupGranularities()) {
                // sync on map since we do not want anything added to or taken from it while we iterate.
                synchronized (scheduledSlots) { // read
                    synchronized (runningSlots) { // read
                        List<Integer> slotsToWorkOn = shardStateManager.getSlotStateManager(shard, g).getSlotsOlderThan(now, maxAgeMillis);
                        if (slotsToWorkOn.size() == 0) {
                            continue;
                        }
                        if (!canWorkOnShard(shard)) {
                            continue;
                        }

                        for (Integer slot : slotsToWorkOn) {
                            SlotKey slotKey = SlotKey.of(g, slot, shard);
                            if (areChildKeysOrSelfKeyScheduledOrRunning(slotKey)) {
                                continue;
                            }
                            SlotKey key = SlotKey.of(g, slot, shard);
                            scheduledSlots.add(key);
                            orderedScheduledSlots.add(key);
                            recentlyScheduledShards.put(shard, scheduleTime);
                        }
                    }
                }
            }
        }
    }

    private boolean areChildKeysOrSelfKeyScheduledOrRunning(SlotKey slotKey) {
        // if any ineligible (children and self) keys are running or scheduled to run, we shouldn't work on this.
        Collection<SlotKey> ineligibleKeys = slotKey.getChildrenKeys();

        if (runningSlots.keySet().contains(slotKey) || scheduledSlots.contains(slotKey)) {
            return true;
        }

        // if any ineligible keys are running or scheduled to run, do not schedule this key.
        for (SlotKey childrenKey : ineligibleKeys) {
            if (runningSlots.keySet().contains(childrenKey) || scheduledSlots.contains(childrenKey)) {
                return true;
            }
        }

        return false;
    }

    private boolean canWorkOnShard(int shard) {
        boolean canWork = lockManager.canWork(shard);
        if (!canWork) {
            if (log.isTraceEnabled())
                log.trace("Skipping shard " + shard + " as lock could not be acquired");
        }
        return canWork;
    }
    
    // returns the next scheduled key. It has a few side effects: 1) it resets update tracking for that slot, 2) it adds
    // the key to the set of running rollups.
    @VisibleForTesting SlotKey getNextScheduled() {
        synchronized (scheduledSlots) {
            if (scheduledSlots.size() == 0)
                return null;
            synchronized (runningSlots) {
                SlotKey key = orderedScheduledSlots.remove(0);
                int slot = key.getSlot();
                Granularity gran = key.getGranularity();
                int shard = key.getShard();
                // notice how we change the state, but the timestamp remained the same. this is important.  When the
                // state is evaluated (i.e., in Reader.getShardState()) we need to realize that when timstamps are the
                // same (this will happen), that a remove always wins during the coalesce.
                scheduledSlots.remove(key);

                if (canWorkOnShard(shard)) {
                    UpdateStamp stamp = shardStateManager.getSlotStateManager(shard, gran).getAndSetState(slot, UpdateStamp.State.Running);
                    runningSlots.put(key, stamp.getTimestamp());
                    return key;
                } else {
                    shardOwnershipChanged.mark();
                    return null;
                }
            }
        }
    }
    
    void pushBackToScheduled(SlotKey key, boolean rescheduleImmediately) {
        synchronized (scheduledSlots) {
            synchronized (runningSlots) {
                int slot = key.getSlot();
                Granularity gran = key.getGranularity();
                int shard = key.getShard();
                // no need to set dirty/clean here.
                shardStateManager.getSlotStateManager(shard, gran).getAndSetState(slot, UpdateStamp.State.Active);
                scheduledSlots.add(key);
                if (rescheduleImmediately) {
                    orderedScheduledSlots.add(0, key);
                } else {
                    orderedScheduledSlots.add(key);
                }
            }
        }
    }
    
    // remove rom the list of running slots.
    void clearFromRunning(SlotKey slotKey) {
        synchronized (runningSlots) {
            runningSlots.remove(slotKey);
            UpdateStamp stamp = shardStateManager.getUpdateStamp(slotKey);
            shardStateManager.setAllCoarserSlotsDirtyForSlot(slotKey);
            // Update the stamp to Rolled state if and only if the current state is running.
            // If the current state is active, it means we received a delayed put which toggled the status to Active.
            if (stamp.getState() == UpdateStamp.State.Running) {
                stamp.setState(UpdateStamp.State.Rolled);
                // Note: Rollup state will be updated to the last ACTIVE timestamp which caused rollup process to kick in.
                stamp.setDirty(true);
            }
        }
    }

    // true if anything is scheduled.
    boolean hasScheduled() {
        return getScheduledCount() > 0;
    }
    
    // returns the number of scheduled rollups.
    int getScheduledCount() {
        synchronized (scheduledSlots) {
            return scheduledSlots.size();
        }
    }

    public Map<Integer, UpdateStamp> getSlotStamps(Granularity gran, int shard) {
        return shardStateManager.getSlotStateManager(shard, gran).getSlotStamps();
    }

    // precondition: shard is unmanaged.
    void addShard(int shard) {
        shardStateManager.add(shard);
        lockManager.addShard(shard);    
    }
    
    // precondition: shard is managed.
    void removeShard(int shard) {
        shardStateManager.remove(shard);
        lockManager.removeShard(shard);
    }

    Set<Integer> getRecentlyScheduledShards() {
        // Collections.unmodifiableSet(...) upsets JMX.
        return new TreeSet<Integer>(recentlyScheduledShards.asMap().keySet());
    }

    // Normal ticker behavior is to return nanoseconds elapsed since VM started.
    // This returns milliseconds since the epoch based upon ScheduleContext's internal representation of time (scheduleTime).
    public Ticker asMillisecondsSinceEpochTicker() {
        return new Ticker() {
            @Override
            public long read() {
                return ScheduleContext.this.getCurrentTimeMillis();
            }
        };
    }

    @Override
    public Collection<String> getMetricsState(int shard, String gran, int slot) {
        final List<String> results = new ArrayList<String>();
        Granularity granularity = Granularity.fromString(gran);

        if (granularity == null)
            return results;

        final Map<Integer, UpdateStamp> stateTimestamps = this.getSlotStamps(granularity, shard);

        if (stateTimestamps == null)
            return results;

        final UpdateStamp stamp = stateTimestamps.get(slot);
        if (stamp != null) {
            results.add(new SlotState(granularity, slot, stamp.getState()).withTimestamp(stamp.getTimestamp()).toString());
        }

        return results;
    }

    private void registerMBean() {
        try {
            final MBeanServer mbs = ManagementFactory.getPlatformMBeanServer();
            final String name = String.format("com.rackspacecloud.blueflood.io:type=%s", ScheduleContext.class.getSimpleName());
            final ObjectName nameObj = new ObjectName(name);
            mbs.registerMBean(this, nameObj);
        } catch (Exception exc) {
            log.error("Unable to register mbean for " + ScheduleContext.class.getSimpleName(), exc);
        }
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/ShardLockManager.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

public interface ShardLockManager {
    public boolean canWork(int shard);
    public void addShard(int shard);
    public void removeShard(int shard);
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/ShardStateManager.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.codahale.metrics.Histogram;
import com.codahale.metrics.Meter;
import com.google.common.base.Ticker;
import com.rackspacecloud.blueflood.exceptions.GranularityException;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.rollup.SlotKey;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.rackspacecloud.blueflood.utils.Util;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

public class ShardStateManager {
    private static final Logger log = LoggerFactory.getLogger(ShardStateManager.class);
    private static final Set<Integer> ALL_SHARDS = new HashSet<Integer>(Util.parseShards("ALL"));
    final Set<Integer> shards; // Managed shards
    final Map<Integer, ShardToGranularityMap> shardToGranularityStates = new HashMap<Integer, ShardToGranularityMap>();
    private final Ticker serverTimeMillisecondTicker;

    private static final Histogram timeSinceUpdate = Metrics.histogram(RollupService.class, "Shard Slot Time Elapsed scheduleSlotsOlderThan");
    // todo: CM_SPECIFIC verify changing metric class name doesn't break things.
    private static final Meter updateStampMeter = Metrics.meter(ShardStateManager.class, "Shard Slot Update Meter");
    private final Meter parentBeforeChild = Metrics.meter(RollupService.class, "Parent slot executed before child");
    private static final Map<Granularity, Meter> granToReRollMeters = new HashMap<Granularity, Meter>();
    static {
        for (Granularity rollupGranularity : Granularity.rollupGranularities()) {
            granToReRollMeters.put(rollupGranularity, Metrics.meter(RollupService.class, String.format("%s Re-rolling up because of delayed metrics", rollupGranularity.shortName())));
        }
    }

    protected ShardStateManager(Collection<Integer> shards, Ticker ticker) {
        this.shards = new HashSet<Integer>(shards);
        for (Integer shard : ALL_SHARDS) { // Why not just do this for managed shards?
            shardToGranularityStates.put(shard, new ShardToGranularityMap(shard));
        }
        this.serverTimeMillisecondTicker = ticker;
    }

    protected Collection<Integer> getManagedShards() {
        return Collections.unmodifiableCollection(this.shards);
    }

    protected Boolean contains(int shard) {
        return shards.size() != 0 && shards.contains(shard);
    }

    protected void add(int shard) {
        if (contains(shard))
            return;
        shards.add(shard);
    }

    protected void remove(int shard) {
        if (!contains(shard))
            return;
        this.shards.remove(shard);
    }

    public SlotStateManager getSlotStateManager(int shard, Granularity granularity) {
        return shardToGranularityStates.get(shard).granularityToSlots.get(granularity);
    }

    protected UpdateStamp getUpdateStamp(SlotKey slotKey) {
        return this.getSlotStateManager(slotKey.getShard(), slotKey.getGranularity())
                .slotToUpdateStampMap.get(slotKey.getSlot());
    }

    // Side effect: mark dirty slots as clean
    protected Map<Granularity, Map<Integer, UpdateStamp>> getDirtySlotsToPersist(int shard) {
        Map<Granularity, Map<Integer, UpdateStamp>> slotTimes = new HashMap<Granularity, Map<Integer, UpdateStamp>>();
        int numUpdates = 0;
        for (Granularity gran : Granularity.rollupGranularities()) {
            Map<Integer, UpdateStamp> dirty = getSlotStateManager(shard, gran).getDirtySlotStampsAndMarkClean();
            slotTimes.put(gran, dirty);

            if (dirty.size() > 0) {
                numUpdates += dirty.size();
            }
        }
        if (numUpdates > 0) {
            // for updates that come by way of scribe, you'll typically see 5 as the number of updates (one for
            // each granularity).  On rollup slaves the situation is a bit different. You'll see only the slot
            // of the granularity just written to marked dirty (so 1).
            log.debug("Found {} dirty slots for shard {}", new Object[]{numUpdates, shard});
            return slotTimes;
        }
        return null;
    }

    public void updateSlotOnRead(int shard, SlotState slotState) {
        getSlotStateManager(shard, slotState.getGranularity()).updateSlotOnRead(slotState);
    }

    public void setAllCoarserSlotsDirtyForSlot(SlotKey slotKey) {
        boolean done = false;
        Granularity coarserGran = slotKey.getGranularity();
        int coarserSlot = slotKey.getSlot();

        while (!done) {
            try {
                coarserGran = coarserGran.coarser();
                coarserSlot = coarserGran.slotFromFinerSlot(coarserSlot);
                ConcurrentMap<Integer, UpdateStamp> updateStampsBySlotMap = getSlotStateManager(slotKey.getShard(), coarserGran).slotToUpdateStampMap;
                UpdateStamp coarseSlotStamp = updateStampsBySlotMap.get(coarserSlot);

                if (coarseSlotStamp == null) {
                    log.debug("No stamp for coarser slot: {}; supplied slot: {}",
                            SlotKey.of(coarserGran, coarserSlot, slotKey.getShard()),
                            slotKey);
                    updateStampsBySlotMap.putIfAbsent(coarserSlot,
                            new UpdateStamp(serverTimeMillisecondTicker.read(), UpdateStamp.State.Active, true));
                    continue;
                }

                UpdateStamp.State coarseSlotState = coarseSlotStamp.getState();
                if (coarseSlotState != UpdateStamp.State.Active) {
                    parentBeforeChild.mark();
                    log.debug("Coarser slot not in active state when finer slot {} just got rolled up. Marking coarser slot {} dirty.",
                            slotKey, SlotKey.of(coarserGran, coarserSlot, slotKey.getShard()));
                    coarseSlotStamp.setState(UpdateStamp.State.Active);
                    coarseSlotStamp.setDirty(true);
                    coarseSlotStamp.setTimestamp(serverTimeMillisecondTicker.read());
                }
            } catch (GranularityException ex) {
                done = true;
            }
        }
    }

    private class ShardToGranularityMap {
        final int shard;
        final Map<Granularity, SlotStateManager> granularityToSlots = new HashMap<Granularity, SlotStateManager>();

        protected ShardToGranularityMap(int shard) {
            this.shard = shard;

            for (Granularity granularity : Granularity.rollupGranularities()) {
                granularityToSlots.put(granularity, new SlotStateManager(shard, granularity));
            }
        }
    }

    protected class SlotStateManager {
        private final int shard;
        final Granularity granularity;
        final ConcurrentMap<Integer, UpdateStamp> slotToUpdateStampMap;

        protected SlotStateManager(int shard, Granularity granularity) {
            this.shard = shard;
            this.granularity = granularity;
            slotToUpdateStampMap = new ConcurrentHashMap<Integer, UpdateStamp>(granularity.numSlots());
        }
        /**
          Imagine metrics are flowing in from multiple ingestor nodes. The ingestion path updates schedule context while writing metrics to cassandra.(See BatchWriter)
          We cannot make any ordering guarantees on the metrics. So every metric that comes in updates the slot state to its collection time.

          This state gets pushed in cassandra by ShardStatePusher and read on the rollup slave. Rollup slave is going to update its state to ACTIVE as long as the timestamp does not match.
          Rollup slave shard map can be in 3 states: 1) Active 2) Rolled 3) Running.
          Every ACTIVE update is taken for Rolled and Running states, but if the shard map is already in an ACTIVE state, then the update happens only if the timestamp of update coming in
          if greater than what we have.
          On Rollup slave it means eventually when it rolls up data for the ACTIVE slot, it will be marked with the collection time belonging to a metric which was generated later.

          For a case of multiple ingestors, it means eventually higher timestamp will win, and will be updated even if that ingestor did not receive metric with that timestamp and will stop
          triggering the state to ACTIVE on rollup host. After this convergence is reached the last rollup time match with the last active times on all ingestor nodes.
         */
        protected void updateSlotOnRead(SlotState slotState) {
            final int slot = slotState.getSlot();
            final long timestamp = slotState.getTimestamp();
            UpdateStamp.State state = slotState.getState();
            UpdateStamp stamp = slotToUpdateStampMap.get(slot);
            if (stamp == null) {
                // haven't seen this slot before, take the update. This happens when a blueflood service is just started.
                slotToUpdateStampMap.put(slot, new UpdateStamp(timestamp, state, false));
            } else if (stamp.getTimestamp() != timestamp && state.equals(UpdateStamp.State.Active)) {
                // 1) new update coming in. We can be in 3 states 1) Active 2) Rolled 3) Running. Apply the update in all cases except when we are already active and
                //    the triggering timestamp we have is greater or the stamp in memory is yet to be persisted i.e still dirty
                if (!(stamp.getState().equals(UpdateStamp.State.Active) && (stamp.getTimestamp() > timestamp || stamp.isDirty()))) {
                    // If the shard state we have is ROLLED, and the snapped millis for the last rollup time and the current update is same, then its a re-roll
                    if (stamp.getState().equals(UpdateStamp.State.Rolled) && granularity.snapMillis(stamp.getTimestamp()) == granularity.snapMillis(timestamp))
                        granToReRollMeters.get(granularity).mark();

                    slotToUpdateStampMap.put(slot, new UpdateStamp(timestamp, state, false));
                } else {
                    stamp.setDirty(true); // This is crucial for convergence, we need to superimpose a higher timestamp which can be done only if we set it to dirty
                }
            } else if (stamp.getTimestamp() == timestamp && state.equals(UpdateStamp.State.Rolled)) {
                // 2) if current value is same but value being applied is a remove, remove wins.
                stamp.setState(UpdateStamp.State.Rolled);
            }
        }

        protected void createOrUpdateForSlotAndMillisecond(int slot, long millis) {
            if (slotToUpdateStampMap.containsKey(slot)) {
                UpdateStamp stamp = slotToUpdateStampMap.get(slot);
                stamp.setTimestamp(millis);
                // Only if we are managing the shard and rolling it up, we should emit a metric here, otherwise, it will be emitted by the rollup context which is responsible for rolling up the shard
                if (getManagedShards().contains(shard) && Configuration.getInstance().getBooleanProperty(CoreConfig.ROLLUP_MODE)) {
                    if (stamp.getState().equals(UpdateStamp.State.Rolled) && granularity.snapMillis(stamp.getTimestamp()) == granularity.snapMillis(millis))
                        granToReRollMeters.get(granularity).mark();
                }
                stamp.setState(UpdateStamp.State.Active);
                stamp.setDirty(true);
            } else {
                slotToUpdateStampMap.put(slot, new UpdateStamp(millis, UpdateStamp.State.Active, true));
            }
            updateStampMeter.mark();
        }

        protected Map<Integer, UpdateStamp> getDirtySlotStampsAndMarkClean() {
            HashMap<Integer, UpdateStamp> dirtySlots = new HashMap<Integer, UpdateStamp>();
            for (Map.Entry<Integer, UpdateStamp> entry : slotToUpdateStampMap.entrySet()) {
                if (entry.getValue().isDirty()) {
                    dirtySlots.put(entry.getKey(), entry.getValue());
                    entry.getValue().setDirty(false);
                }
            }
            return dirtySlots;
        }

        protected UpdateStamp getAndSetState(int slot, UpdateStamp.State state) {
            UpdateStamp stamp = slotToUpdateStampMap.get(slot);
            stamp.setState(state);
            return stamp;
        }

        // gets a snapshot of the last updates
        protected Map<Integer, UpdateStamp> getSlotStamps() {
            // essentially a copy on read map.
            return Collections.unmodifiableMap(slotToUpdateStampMap);
        }

        protected List<Integer> getSlotsOlderThan(long now, long maxAgeMillis) {
            List<Integer> outputKeys = new ArrayList<Integer>();
            for (Map.Entry<Integer, UpdateStamp> entry : slotToUpdateStampMap.entrySet()) {
                final UpdateStamp update = entry.getValue();
                final long timeElapsed = now - update.getTimestamp();
                timeSinceUpdate.update(timeElapsed);
                if (update.getState() == UpdateStamp.State.Rolled) {
                    continue;
                }
                if (timeElapsed <= maxAgeMillis) {
                    continue;
                }
                outputKeys.add(entry.getKey());
            }
            return outputKeys;
        }
    }
}




File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/ShardStatePuller.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.codahale.metrics.Timer;
import com.rackspacecloud.blueflood.io.AstyanaxShardStateIO;
import com.rackspacecloud.blueflood.io.ShardStateIO;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collection;
import java.util.concurrent.TimeUnit;

public class ShardStatePuller extends ShardStateWorker {
    private static final Logger log = LoggerFactory.getLogger(ShardStatePuller.class);
    

    public ShardStatePuller(Collection<Integer> allShards, ShardStateManager stateManager, ShardStateIO io) {
        super(allShards, stateManager, new TimeValue(Configuration.getInstance().getIntegerProperty(CoreConfig.SHARD_PULL_PERIOD), TimeUnit.MILLISECONDS), io);
    }

    public void performOperation() {
        Timer.Context ctx = timer.time();
        for (int shard : shardStateManager.getManagedShards()) {

            try {
                Collection<SlotState> slotStates = getIO().getShardState(shard);
                for (SlotState slotState : slotStates) {
                    shardStateManager.updateSlotOnRead(shard, slotState);
                }

            } catch (Exception ex) {
                log.error("Could not read shard state from the database. " + ex.getMessage(), ex);
            }
        }
        ctx.stop();
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/ShardStatePusher.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.codahale.metrics.Timer;
import com.rackspacecloud.blueflood.io.AstyanaxShardStateIO;
import com.rackspacecloud.blueflood.io.ShardStateIO;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.Collection;
import java.util.Map;
import java.util.concurrent.TimeUnit;

public class ShardStatePusher extends ShardStateWorker {
    private static final Logger log = LoggerFactory.getLogger(ShardStatePusher.class);
    
    public ShardStatePusher(final Collection<Integer> allShards, ShardStateManager stateManager, ShardStateIO io) {
        super(allShards, stateManager, new TimeValue(Configuration.getInstance().getIntegerProperty(CoreConfig.SHARD_PUSH_PERIOD), TimeUnit.MILLISECONDS), io);
    }

    public void performOperation() {
        Timer.Context ctx = timer.time();
        try {
            for (int shard : allShards) {
                Map<Granularity, Map<Integer, UpdateStamp>> slotTimes = shardStateManager.getDirtySlotsToPersist(shard);
                if (slotTimes != null) {
                    try {
                        getIO().putShardState(shard, slotTimes);
                    } catch (IOException ex) {
                        log.error("Could not put shard state to the database (shard " + shard + "). " + ex.getMessage(), ex);
                    }
                }
            }
        } catch (RuntimeException ex) {
            log.error("Could not put shard states to the database. " + ex.getMessage(), ex);
        } finally {
            ctx.stop();
        }
    }
    
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/ShardStateWorker.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.codahale.metrics.*;
import com.rackspacecloud.blueflood.io.ShardStateIO;
import com.rackspacecloud.blueflood.tools.jmx.JmxBooleanGauge;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.management.MBeanServer;
import javax.management.ObjectName;
import java.lang.management.ManagementFactory;
import java.util.Collection;
import java.util.Collections;

/**
 * Base class for pushing/pulling shard state. Todo: just bring the two child classes inside this one.
 */
abstract class ShardStateWorker implements Runnable, ShardStateWorkerMBean {
    private static final Logger log = LoggerFactory.getLogger(ShardStateWorker.class);
    
    protected final Collection<Integer> allShards;
    protected final ShardStateManager shardStateManager;
    protected final Timer timer = Metrics.timer(getClass(), "Stats");
    
    private long lastOp = 0L;
    private boolean active = true;
    private Object activePollBarrier = new Object();

    private long periodMs = 1000L;
    
    private final Counter errors;
    private Gauge activeGauge;
    private Gauge periodGauge;
    
    private final ShardStateIO io;

    ShardStateWorker(Collection<Integer> allShards, ShardStateManager shardStateManager, TimeValue period, ShardStateIO io) {
        this.shardStateManager = shardStateManager;
        this.allShards = Collections.unmodifiableCollection(allShards);
        this.periodMs = period.toMillis();
        this.io = io;
        
        try {
            final MBeanServer mbs = ManagementFactory.getPlatformMBeanServer();
            String name = String.format("com.rackspacecloud.blueflood.service:type=%s", getClass().getSimpleName());
            final ObjectName nameObj = new ObjectName(name);
            mbs.registerMBean(this, nameObj);
            activeGauge = Metrics.getRegistry().register(MetricRegistry.name(getClass(), "Active"),
                    new JmxBooleanGauge(nameObj, "Active"));

            periodGauge = Metrics.getRegistry().register(MetricRegistry.name(getClass(), "Period"),
                    new JmxAttributeGauge(nameObj, "Period"));

        } catch (Exception exc) {
            // not critical (as in tests), but we want it logged.
            log.error("Unable to register mbean for " + getClass().getSimpleName());
            log.debug(exc.getMessage(), exc);
        }
        
        errors = Metrics.counter(getClass(), "Poll Errors");
    }    
    
    final public void run() {
        while (true) {
            try {
                if (active) {
                    // push.
                    long now = System.currentTimeMillis();
                    if ((now - lastOp) > periodMs) {
                        performOperation();
                        lastOp = now;
                    } else {
                        try { Thread.currentThread().sleep(100); } catch (Exception ex) {};
                    }
                } else {
                    try {
                        synchronized (activePollBarrier) {
                            activePollBarrier.wait();
                        }
                    } catch (InterruptedException ex) {
                        log.debug("Shard state worker woken up.");
                    }
                }
            } catch (Throwable th) {
                log.error(th.getMessage(), th);
                errors.inc();
            }
        }
    }
    
    public ShardStateIO getIO() { return io; }
    
    abstract void performOperation();
   
    //
    // JMX methods
    //

    public synchronized void force() {
        try {
            performOperation();
        }
        catch (Exception ex) {
            log.error(ex.getMessage(), ex);
        }
    }

    public synchronized void setActive(boolean b) { 
        active = b;
        if (active) {
            synchronized (activePollBarrier) {
                activePollBarrier.notify();
            }
        }
    }
    public synchronized boolean getActive() { return this.active; }

    public synchronized void setPeriod(long period) { this.periodMs = period; }
    public synchronized long getPeriod() { return this.periodMs; }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/ShardStateWorkerMBean.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.rackspacecloud.blueflood.utils.TimeValue;

import java.util.concurrent.TimeUnit;

public interface ShardStateWorkerMBean {
    public void setActive(boolean b);
    public boolean getActive();
    
    public void force();
    
    public void setPeriod(long period);
    public long getPeriod();
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/SingleRollupReadContext.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.codahale.metrics.Histogram;
import com.codahale.metrics.Timer;
import com.netflix.astyanax.model.ColumnFamily;
import com.rackspacecloud.blueflood.types.Locator;
import com.rackspacecloud.blueflood.types.Range;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.types.Locator;
import com.rackspacecloud.blueflood.types.Range;

import java.util.concurrent.TimeUnit;

/**
 * This class keeps track of what is happening in an rollup for a specific metric.
 */
public class SingleRollupReadContext {
    private final Locator locator;
    private final Range range;
    private static final Timer executeTimer = Metrics.timer(RollupService.class, "Rollup Execution Timer");
    private static final Histogram waitHist = Metrics.histogram(RollupService.class, "Rollup Wait Histogram");
    
    // documenting that this represents the DESTINATION granularity, not the SOURCE granularity.
    private final Granularity rollupGranularity;

    public SingleRollupReadContext(Locator locator, Range rangeToRead, Granularity rollupGranularity) {
        this.locator = locator;
        this.range = rangeToRead;
        this.rollupGranularity = rollupGranularity;
    }
    
    Timer getExecuteTimer() {
        return executeTimer;
    }

    Histogram getWaitHist() {
        return waitHist;
    }

    Granularity getRollupGranularity() {
        return this.rollupGranularity;
    }

    Range getRange() {
        return this.range;
    }

    Locator getLocator() {
        return this.locator;
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/SingleRollupWriteContext.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.netflix.astyanax.model.ColumnFamily;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.types.Locator;
import com.rackspacecloud.blueflood.types.Rollup;
import com.rackspacecloud.blueflood.types.RollupType;

public class SingleRollupWriteContext {
    private final Rollup rollup;
    private final Locator locator;
    private final Long timestamp;
    private final ColumnFamily<Locator, Long> destinationCF;
    private final Granularity granularity;

    // public only for tests
    public SingleRollupWriteContext(Rollup rollup, Locator locator, Granularity granularity, ColumnFamily<Locator, Long> destCf, Long timestamp) {
        this.rollup = rollup;
        this.locator = locator;
        this.granularity = granularity;
        this.destinationCF = destCf;
        this.timestamp = timestamp;
    }

    public SingleRollupWriteContext(Rollup rollup, SingleRollupReadContext singleRollupReadContext, ColumnFamily<Locator, Long> dstCF) {
        this(rollup, singleRollupReadContext.getLocator(), singleRollupReadContext.getRollupGranularity(), dstCF, singleRollupReadContext.getRange().getStart());
    }

    public Rollup getRollup() {
        return rollup;
    }

    public Locator getLocator() {
        return locator;
    }

    public Long getTimestamp() {
        return timestamp;
    }

    public ColumnFamily<Locator, Long> getDestinationCF() {
        return destinationCF;
    }
    
    public Granularity getGranularity() { return granularity; }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/SlotState.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.rackspacecloud.blueflood.rollup.Granularity;

public class SlotState {
    private Granularity granularity;
    private Integer slot;
    private UpdateStamp.State state;
    private Long timestamp = null;

    public SlotState(Granularity g, int slot, UpdateStamp.State state) {
        this.granularity = g;
        this.slot = slot;
        this.state = state;
    }

    public SlotState() {
        this.granularity = null;
        this.slot = null;
        this.state = null;
    }

    /**
     * Set the timestamp
     * @param timestamp in milliseconds
     * @return
     */
    public SlotState withTimestamp(long timestamp) {
        this.timestamp = timestamp;
        return this;
    }

    public String toString() {
        return new StringBuilder().append(granularity == null ? "null" : granularity.name())
                .append(",").append(slot)
                .append(",").append(state == null ? "null" : state.code())
                .append(": ").append(getTimestamp() == null ? "" : getTimestamp())
                .toString();
    }

    public boolean equals(Object other) {
        if (!(other instanceof SlotState)) {
            return false;
        }
        SlotState that = (SlotState) other;
        return this.toString().equals(that.toString());
    }

    public Granularity getGranularity() {
        return granularity;
    }

    public int getSlot() {
        return slot;
    }

    public UpdateStamp.State getState() {
        return state;
    }

    public Long getTimestamp() {
        return timestamp;
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/UpdateStamp.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

/**
 * This class basically serves to annotate a timestamp to indicate if it marks an update or a remove action.
 */
public class UpdateStamp {
    private long timestamp;
    private State state;
    private boolean dirty;
    
    public UpdateStamp(long timestamp, State state, boolean dirty) {
        setTimestamp(timestamp);
        setState(state);
        setDirty(dirty);
    }
    
    public void setDirty(boolean b) { dirty = b; }
    public void setTimestamp(long timestamp) { this.timestamp = timestamp; }
    public void setState(State state) { this.state = state; }
    
    public boolean isDirty() { return dirty; }
    public long getTimestamp() { return timestamp; }
    public State getState() { return state; }
    
    public int hashCode() {
        return (timestamp + state.code).hashCode();
    }
    
    public boolean equals(Object o) {
        if (!(o instanceof UpdateStamp)) return false;
        UpdateStamp other = (UpdateStamp)o;
        return other.timestamp == timestamp && other.state == state;
    }
    
    public String toString() { return timestamp + "," + state.code; }
    
    public enum State {
        // in the database, there are only two states we care about: Active and Rolled.  Running is a ephemeral state
        // during runtime.  It degrades to Active during a save restore (indicating it is not finished and should,
        // therefore, not be considered rolled.
        Active("A"), Running("A"), Rolled("X");
        private final String code;
        private State(String code) {
            this.code = code;
        }
        public String code() { return code; }
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/ZKBasedShardLockManager.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.codahale.metrics.Gauge;
import com.codahale.metrics.JmxAttributeGauge;
import com.codahale.metrics.Meter;
import com.codahale.metrics.MetricRegistry;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Ticker;
import com.rackspacecloud.blueflood.concurrent.InstrumentedThreadPoolExecutor;
import com.rackspacecloud.blueflood.concurrent.ThreadPoolBuilder;
import com.rackspacecloud.blueflood.io.Constants;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.apache.curator.RetryPolicy;
import org.apache.curator.framework.CuratorFramework;
import org.apache.curator.framework.CuratorFrameworkFactory;
import org.apache.curator.framework.imps.CuratorFrameworkState;
import org.apache.curator.framework.recipes.locks.InterProcessMutex;
import org.apache.curator.framework.state.ConnectionState;
import org.apache.curator.framework.state.ConnectionStateListener;
import org.apache.curator.retry.ExponentialBackoffRetry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.management.MBeanServer;
import javax.management.ObjectName;
import java.lang.management.ManagementFactory;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Random;
import java.util.Set;
import java.util.SortedSet;
import java.util.TreeSet;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.Callable;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.FutureTask;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

class ZKBasedShardLockManager implements ConnectionStateListener, ShardLockManager, ZKBasedShardLockManagerMBean {
    private static final Logger log = LoggerFactory.getLogger(ZKBasedShardLockManager.class);
    private static final AtomicInteger UNIQUE_IDENTIFIER = new AtomicInteger(0);

    private final Random rand = new Random(System.currentTimeMillis());
    /** Unique identifier for this object, used to identify the MBean. */
    private final int id = UNIQUE_IDENTIFIER.getAndIncrement();
    /** Zookeeper client. */
    private final CuratorFramework client;
    private final String ZK_NAMESPACE = "locks/blueflood";
    private final String LOCK_QUALIFIER = "/shards";
    private final long ZK_SESSION_TIMEOUT_MS = new TimeValue(120L, TimeUnit.SECONDS).toMillis();
    private final long ZK_CONN_TIMEOUT_MS = new TimeValue(5L, TimeUnit.SECONDS).toMillis();
    private final long ZK_RETRY_INTERVAL = new TimeValue(50L, TimeUnit.MILLISECONDS).toMillis();
    private final int ZK_MAX_RETRIES = 2;
    private final TimeValue ZK_LOCK_TIMEOUT = new TimeValue(1L, TimeUnit.SECONDS);
    private final ConcurrentHashMap<Integer, Lock> locks; // shard to lock objects
    private final TimeValue shardLockScavengeInterval;
    private final int defaultMaxLocksToAcquirePerCycle;
    private final Ticker ticker = Ticker.systemTicker();

    // modifiable properties.
    private TimeValue minLockHoldTime;
    private TimeValue lockDisinterestedTime;

    /** true if we're connected to zookeeper. */
    private volatile boolean connected = false;
    private volatile long lastScavengedAt = System.currentTimeMillis();

    /** Thread that performs the locking & releasing. */
    private final ThreadPoolExecutor lockWorker;

    private final ScheduledThreadPoolExecutor scavengerWorker = new ScheduledThreadPoolExecutor(1, new ThreadFactory() {
        @Override
        public Thread newThread(Runnable r) {
            Thread t = new Thread(r, "ZK Lock Worker " + id);
            t.setDaemon(true);
            return t;
        }
    });

    private final Meter lockAcquisitionFailure = Metrics.meter(ZKBasedShardLockManager.class, "Lock acquisition failures");
    private final com.codahale.metrics.Timer lockAcquisitionTimer = Metrics.timer(ZKBasedShardLockManager.class, "Lock acquisition timer");
    private final Meter lockErrors = Metrics.meter(ZKBasedShardLockManager.class, "Lock errors");

    ZKBasedShardLockManager(String zookeeperCluster, Set<Integer> managedShards) {
        try {
            final MBeanServer mbs = ManagementFactory.getPlatformMBeanServer();
            final String name = String.format("com.rackspacecloud.blueflood.service:type=%s", getClass().getSimpleName() + (id == 0 ? "" : id));
            final ObjectName nameObj = new ObjectName(name);
            mbs.registerMBean(this, nameObj);
            registerMetrics(nameObj, Metrics.getRegistry());
        } catch (Exception exc) {
            log.error("Unable to register mbean for " + getClass().getSimpleName(), exc);
        }

        this.locks = new ConcurrentHashMap<Integer, Lock>();
        RetryPolicy policy = new ExponentialBackoffRetry((int)ZK_RETRY_INTERVAL, ZK_MAX_RETRIES);

        this.client = CuratorFrameworkFactory.
                builder().namespace(ZK_NAMESPACE)
                .connectString(zookeeperCluster)
                .sessionTimeoutMs((int) ZK_SESSION_TIMEOUT_MS)
                .connectionTimeoutMs((int) ZK_CONN_TIMEOUT_MS)
                .retryPolicy(policy).build();
        this.client.getConnectionStateListenable().addListener(this);  // register our listener
        this.client.start();

        Configuration config = Configuration.getInstance();
        for (int shard : managedShards) {
            addShard(shard);
        }
        this.minLockHoldTime = new TimeValue(config.getLongProperty(CoreConfig.SHARD_LOCK_HOLD_PERIOD_MS), TimeUnit.MILLISECONDS);
        this.lockDisinterestedTime = new TimeValue(config.getLongProperty(CoreConfig.SHARD_LOCK_DISINTERESTED_PERIOD_MS), TimeUnit.MILLISECONDS);
        this.shardLockScavengeInterval = new TimeValue(config.getLongProperty(CoreConfig.SHARD_LOCK_SCAVENGE_INTERVAL_MS),
                TimeUnit.MILLISECONDS);
        this.defaultMaxLocksToAcquirePerCycle = config.getIntegerProperty(CoreConfig.MAX_ZK_LOCKS_TO_ACQUIRE_PER_CYCLE);
        this.lockWorker = new ThreadPoolBuilder()
                .withCorePoolSize(1)
                .withMaxPoolSize(1)
                .withKeepAliveTime(new TimeValue(Long.MAX_VALUE, TimeUnit.DAYS))
                .withBoundedQueue(1000)
                .withName("ZkThreadPool")
                .build();
        InstrumentedThreadPoolExecutor.instrument(lockWorker, "ZkThreadPool");
    }

    /**
     * Registers the different zookeeper metrics.
     */
    private void registerMetrics(final ObjectName nameObj, MetricRegistry reg) {
        reg.register(MetricRegistry.name(ZKBasedShardLockManager.class, "Lock Disinterested Time Millis"),
                new JmxAttributeGauge(nameObj, "LockDisinterestedTimeMillis"));
        reg.register(MetricRegistry.name(ZKBasedShardLockManager.class, "Min Lock Hold Time Millis"),
                new JmxAttributeGauge(nameObj, "MinLockHoldTimeMillis"));
        reg.register(MetricRegistry.name(ZKBasedShardLockManager.class, "Seconds Since Last Scavenge"),
                new JmxAttributeGauge(nameObj, "SecondsSinceLastScavenge"));

        reg.register(MetricRegistry.name(ZKBasedShardLockManager.class, "Zk Connection Status"),
                new JmxAttributeGauge(nameObj, "ZkConnectionStatus") {
                    @Override
                    public Object getValue() {
                        Object val = super.getValue();
                        if (val.equals("connected")) {
                            return 1;
                        }
                        return 0;
                    }
                });
        reg.register(MetricRegistry.name(ZKBasedShardLockManager.class, "Held Shards"),
                new Gauge<Integer>() {
                    @Override
                    public Integer getValue() {
                        return getHeldShards().size();
                    }
                });

        reg.register(MetricRegistry.name(ZKBasedShardLockManager.class, "Unheld Shards"),
                new Gauge<Integer>() {
                    @Override
                    public Integer getValue() {
                        return getUnheldShards().size();
                    }
                });
        reg.register(MetricRegistry.name(ZKBasedShardLockManager.class, "Error Shards"),
                new Gauge<Integer>() {
                    @Override
                    public Integer getValue() {
                        return getErrorShards().size();
                    }
                });
    }

    /**
     * Initialize the ZKBasedShardLockManager.
     * @param zkWaitTime Time to wait until zookeeper is up.
     */
    public void init(TimeValue zkWaitTime) {
        waitForZKConnections(zkWaitTime.toSeconds());
        prefetchLocks();
        scheduleScavenger();
    }

    /**
     * Waits until the zookeeper connection is available.
     * @param waitTimeSeconds
     */
    @VisibleForTesting boolean waitForZKConnections(long waitTimeSeconds) {
        for (int i = 0; i < waitTimeSeconds; i++) {
            if (connected) {
                return connected;
            }
            log.debug("Waiting for connect");
            try { Thread.sleep(1000); } catch (InterruptedException ex) {}
        }
        return connected;
    }

    /**
     * Only called from {@link #init(TimeValue)}.
     *
     * Try to achieve each lock. This will give us a good initial state where each lock is either held or unheld.
     * The purpose is to avoid a situation at startup where a node assumes it can schedule anything (until a lock
     * is held).
     */
    @VisibleForTesting void prefetchLocks() {

        if (!connected) {
            log.warn("Cannot connect to Zookeeper; will not perform initial lock acquisition");
            for (Lock lock : locks.values()) {
                lock.connectionLost();
            }
        } else {
            log.info("Pre-fetching zookeeper locks for shards");
            boolean isManagingAllShards = locks.size() >= Constants.NUMBER_OF_SHARDS;
            int maxLocksToPrefetch = moreThanHalf();

            if (isManagingAllShards) {
                maxLocksToPrefetch = Constants.NUMBER_OF_SHARDS;
            }

            List<Integer> shards = new ArrayList<Integer>(locks.keySet());
            Collections.shuffle(shards);

            int locksObtained = 0;
            for (int shard : shards) {
                try {
                    log.debug("Initial lock attempt for shard={}", shard);
                    final Lock lock = locks.get(shard);
                    lockWorker.submit(lock.acquirer()).get();

                    if (lock.isHeld() && ++locksObtained >= maxLocksToPrefetch) {
                        break;
                    }
                } catch (InterruptedException ex) {
                    log.warn("Thread exception while acquiring initial locks: " + ex.getMessage(), ex);
                } catch (ExecutionException ex) {
                    log.error("Problem acquiring lock " + shard + " " + ex.getCause().getMessage(), ex.getCause());
                }
            }
            log.info("Finished pre-fetching zookeeper locks");
        }
    }

    public void scheduleScavenger() {
        scavengerWorker.scheduleAtFixedRate(new Runnable() {
            @Override
            public void run() {
                scavengeLocks();
            }
        }, 30, shardLockScavengeInterval.toSeconds(), TimeUnit.SECONDS);
    }

    /**
     * Determines whether a given shard can be worked on by this blueflood instance.
     */
    public boolean canWork(int shard) {
        return locks.containsKey(shard) && locks.get(shard).canWork();
    }

    private String getLockId(int shard) {
        return  LOCK_QUALIFIER + "/" + shard;
    }

    // This is called when connection to zookeeper is lost
    private void handleZookeeperConnectionFailed() {
        // It is okay for us to proceed with the work we already scheduled (either running or in scheduled queue)
        // for slots. We would duplicate work just for those slots which is fine.
        log.info("Force release all locks as zookeeper connection is lost");
        for (Lock lock : locks.values()) {
            lock.connectionLost();
        }
    }

    private void scavengeLocks() {
        log.debug("Starting scavengeLocks()");
        try {
            int locksAcquiredThisCycle = 0;
            int maxLocksToAcquirePerCycle = defaultMaxLocksToAcquirePerCycle;
            final Integer[] shards = locks.keySet().toArray(new Integer[]{});

            // Linear scan to figure out how many locks are held.
            int locksHeld = 0;
            for (int shard : shards) {
                if (locks.get(shard).isHeld()) {
                    locksHeld++;
                }
            }
            log.debug("Currently holding {} locks.", locksHeld);

            // if the number of locks held is less than 50% of the number of managed shards,
            // be aggressive and acquire more locks
            if (locksHeld <= moreThanHalf()) {
                maxLocksToAcquirePerCycle = moreThanHalf();
            }
            // shouldAttempt

            for (int shard : shards) {
                boolean shouldAttempt = locksAcquiredThisCycle < maxLocksToAcquirePerCycle;
                boolean isAcquired = locks.get(shard).performMaintenance(shouldAttempt);
                if (isAcquired) {
                    locksAcquiredThisCycle++;
                }
            }
            lastScavengedAt = nowMillis();
        } catch (RuntimeException e) {
            log.error("Error while scavengeLocks()", e);
        } finally {
            log.debug("Finishing scavengeLocks().");
        }
    }

    public void stateChanged(CuratorFramework curatorFramework, ConnectionState connectionState) {
        log.info("Connection to Zookeeper toggled to state " + connectionState.toString());
        connected = connectionState == ConnectionState.CONNECTED || connectionState == ConnectionState.RECONNECTED;
        if (connectionState == ConnectionState.LOST) {
            log.error("Connection to Zookeeper toggled to state " + connectionState.toString());
            this.handleZookeeperConnectionFailed();
        } else if (connectionState == ConnectionState.RECONNECTED) {
            log.info("Reconnected to zookeeper, forcing lock scavenge");
            forceLockScavenge();
        } else {
            log.info("Connection to Zookeeper toggled to state " + connectionState.toString());
        }
    }

    public synchronized void addShard(int shard) {
        if (locks.containsKey(shard)) {
            return;
        }
        this.locks.put(shard, new Lock(shard));
    }

    public synchronized void removeShard(int shard) {
        Lock lock = locks.remove(shard);
        if (lock != null) {
            lock.release();
        }
    }

    public boolean isConnected() {
        return connected && isCuratorStarted() && client.getZookeeperClient().isConnected();
    }

    /** Unsafe method for testing. */
    @VisibleForTesting
    void waitForQuiesceUnsafe() {
        while (lockWorker.getActiveCount() != 0 || lockWorker.getQueue().size() != 0) {
            if (log.isTraceEnabled())
                log.trace("Waiting for quiesce");
            try { Thread.sleep(100); } catch (InterruptedException ignore) {}
        }
        // this time out needs to be longer than ZK_LOCK_TIMEOUT for valid tests.
        try { Thread.sleep(2000); } catch (InterruptedException ignore) {}
    }

    @VisibleForTesting
    boolean holdsLockUnsafe(int shard) {
        return locks.containsKey(shard) && locks.get(shard).isHeldZk();
    }

    @VisibleForTesting
    boolean releaseLockUnsafe(int shard) throws Exception {
        return lockWorker.submit(locks.get(shard).releaser()).get();
    }

    @VisibleForTesting
    void shutdownUnsafe() throws Exception {
        for (Lock lock : locks.values()) {
            lockWorker.submit(lock.releaser()).get();
        }
        client.close();
    }

    @VisibleForTesting
    Lock getLockUnsafe(int shard) {
        return locks.get(shard);
    }

    //
    // private methods
    //

    private long nowMillis() {
        return ticker.read() / 1000000;
    }

    private int moreThanHalf() {
        return locks.size() / 2 + 1;
    }

    private boolean isCuratorStarted() {
        return client.getState() == CuratorFrameworkState.STARTED;
    }

    //
    // JMX
    //

    public synchronized Collection<Integer> getHeldShards() {
        SortedSet<Integer> held = new TreeSet<Integer>();
        for (Lock lock : locks.values()) {
            if (lock.isHeld()) {
                held.add(lock.getShard());
            }
        }
        return held;
    }

    public synchronized Collection<Integer> getUnheldShards() {
        SortedSet<Integer> unheld = new TreeSet<Integer>();
        for (Lock lock : locks.values()) {
            if (lock.isUnheld()) {
                unheld.add(lock.getShard());
            }
        }
        return unheld;
    }

    public synchronized Collection<Integer> getErrorShards() {
        SortedSet<Integer> errorShards = new TreeSet<Integer>();
        for (Lock lock : locks.values()) {
            if (lock.getLockState() == LockState.ERROR) {
                errorShards.add(lock.getShard());
            }
        }
        return errorShards;
    }

    public synchronized void forceLockScavenge() {
        scavengeLocks();
    }

    public synchronized String getZkConnectionStatus() {
        if (!isCuratorStarted())
            return "not started";
        else if (client.getZookeeperClient().isConnected())
            return "connected";
        else
            return "not connected";
    }

    public synchronized boolean release(int shard) {
        if (locks.containsKey(shard)) {
            try {
                return lockWorker.submit(locks.get(shard).releaser()).get();
            } catch (InterruptedException ex) {
                log.error("Thread is interrupted:"+ ex.getMessage(), ex);
                return false;
            } catch (ExecutionException ex) {
                log.error("Release error: " + ex.getCause().getMessage(), ex.getCause());
                return false;
            }
        }
        return false;
    }

    public synchronized boolean acquire(int shard) {
        if (locks.containsKey(shard)) {
            try {
                return lockWorker.submit(locks.get(shard).acquirer()).get();
            } catch (InterruptedException ex) {
                log.error("Thread is interrupted: "+ ex.getMessage(), ex);
                return false;
            } catch (ExecutionException ex) {
                log.error("Acquire error: " + ex.getCause().getMessage(), ex.getCause());
                return false;
            }
        }
        return false;
    }

    public synchronized long getMinLockHoldTimeMillis() { return minLockHoldTime.toMillis(); }
    public synchronized void setMinLockHoldTimeMillis(long millis) { minLockHoldTime = new TimeValue(millis, TimeUnit.MILLISECONDS); }
    public synchronized long getLockDisinterestedTimeMillis() { return lockDisinterestedTime.toMillis(); }
    public synchronized void setLockDisinterestedTimeMillis(long millis) { lockDisinterestedTime = new TimeValue(millis, TimeUnit.MILLISECONDS); }
    public synchronized long getSecondsSinceLastScavenge() { return ((nowMillis() - lastScavengedAt) / 1000); }

    //
    // Helper classes
    //


    enum LockState {
        /** Locks in UNKNOWN state will be attemped to be acquired. */
        UNKNOWN,
        /** Lock is acquired by the current blueflood instance. No other blueflood server will have this lock. */
        ACQUIRED,
        /** Attempted to acquire, but failed. Lock is already held by another instance. */
        ACQUIRE_FAILED,
        /** Error state. normally means that the connection is lost. */
        ERROR,
        /** The lock was voluntarily released. Will not attempt to acquire this lock during this time. */
        DISINTERESTED
    }

    class Lock {
        private final int shard;
        private LockState state = LockState.UNKNOWN;
        /** mutex. is non-null unless disconnected from zookeeper. */
        private InterProcessMutex mutex = null;
        private long stateChanged = nowMillis();
        private boolean isAcquiring = false;
        private boolean isReleasing = false;

        Lock(int shard) {
            this.shard = shard;
            checkMutex();
        }

        @Override public String toString() {
            return String.format("shard=%d state=%s isAcquiring=%s isReleasing=%s", shard, state, isAcquiring, isReleasing);
        }

        synchronized void checkMutex() {
            if (mutex == null) {
                mutex = new InterProcessMutex(client, getLockId(shard));
            }
        }

        int getShard() { return shard; }
        boolean isHeld() { return mutex != null && state == LockState.ACQUIRED; }
        boolean isUnheld() { return mutex != null && state == LockState.ACQUIRE_FAILED; }

        boolean isHeldZk() {
            return mutex != null && mutex.isAcquiredInThisProcess();
        }

        /**
         * Performs the maintenance of the lock.
         *
         * <ul>
         *     <li>Move the lock state to {@link LockState#UNKNOWN} if necessary.</li>
         *     <li>Attempt to hold the locks in UNKNOWN state.</li>
         *     <li>Attempt to release the locks that were held for too long.</li>
         * </ul>
         *
         * @param shouldAttempt <code>true</code> if the lock should be attempted to be acquired.
         *
         * @return true if the lock was newly acquired during this cycle. otherwise false.
         */
        boolean performMaintenance(boolean shouldAttempt) {
            updateLockState();

            long now = nowMillis();
            // determine if we should acquire or release.
            if (state == LockState.UNKNOWN && shouldAttempt) {
                acquire();
                return isHeld();
            } else if (state == LockState.ACQUIRED && now - stateChanged > minLockHoldTime.toMillis()) {
                // Lock was held for too long - maybe release to trigger re-balancing.
                float chance = (float)(now - stateChanged - minLockHoldTime.toMillis()) / (float)(Math.max(1, minLockHoldTime.toMillis()));
                float r = rand.nextFloat();
                if (log.isTraceEnabled()) {
                    log.trace(String.format("Will release %s if, %f < %f", shard, r, chance));
                }
                if (r < chance) {
                    release();
                }
            } else if (state == LockState.ERROR && now - stateChanged > minLockHoldTime.toMillis()) {
                log.error("Lock state hasn't toggled from ERROR for " + minLockHoldTime.toString()
                        + "; Client connection status: " + connected);
            }
            return false;
        }

        /**
         * Sees if we should change our lock status to "UNKNOWN". Only locks in UNKNOWN state will periodically
         * be attempted to be acquired.
         */
        synchronized void updateLockState() {
            boolean toUnk = false;
            long now = nowMillis();

            if (state == LockState.DISINTERESTED && now - stateChanged > lockDisinterestedTime.toMillis()) {
                // Lock was voluntarily released long time ago. Attempt to acquire the lock again.
                toUnk = true;
            } else if (state == LockState.ERROR && connected) {
                // Reconnected to Zookeeper.
                toUnk = true;
            } else if (state == LockState.ACQUIRE_FAILED && now - stateChanged > lockDisinterestedTime.toMillis()) {
                // acquisition attempt has failed before long time ago. Attempt to acquire the lock again.
                toUnk = true;
            }

            if (toUnk) {
                setState(LockState.UNKNOWN);
            }
        }

        synchronized LockState getLockState() {
            return state;
        }

        /**
         * Note: locks in error state returns true, because multiple workers working on the same shard is ok.
         */
        synchronized boolean canWork() {
            return state == LockState.ACQUIRED || state == LockState.ERROR;
        }

        synchronized void connectionLost() {
            setState(LockState.ERROR);
            mutex = null;
        }

        synchronized void setState(LockState newState) {
            state = newState;
            stateChanged = nowMillis();
        }

        synchronized void acquire() {
            if (isAcquiring || isReleasing) return;
            isAcquiring = true;
            try {
                log.debug("Acquiring lock for " + shard);
                lockWorker.execute(new FutureTask<Boolean>(acquirer()));
            } catch (RejectedExecutionException ex) {
                log.warn(String.format("Rejected lock execution: active:%d queue:%d shard:%d", lockWorker.getActiveCount(), lockWorker.getQueue().size(), shard));
            }
        }

        synchronized void release() {
            if (isAcquiring || isReleasing) return;
            isReleasing = true;
            try {
                log.debug("Releasing lock for " + shard);
                lockWorker.execute(new FutureTask<Boolean>(releaser()));
            } catch (RejectedExecutionException ex) {
                log.warn(String.format("Rejected lock execution: active:%d queue:%d shard:%d", lockWorker.getActiveCount(), lockWorker.getQueue().size(), shard));
            }
        }

        /**
         * Attempt to acquire a lock.
         * @return <code>true</code> if the lock is in acquired state (already acquired lock will return true).
         */
        synchronized Callable<Boolean> acquirer() {
            return new Callable<Boolean>() {
                public Boolean call() throws Exception {
                    com.codahale.metrics.Timer.Context ctx = lockAcquisitionTimer.time();
                    try {
                        checkMutex();
                        if (!connected || mutex == null) {
                            setState(LockState.ERROR);
                            return false;
                        } else if (state == LockState.ACQUIRED) {
                            return true;
                        } else if (state == LockState.ACQUIRE_FAILED) {
                            return false;
                        } else {
                            log.debug("Trying ZK lock for shard={}", shard);
                            if (mutex.isAcquiredInThisProcess()) {
                                if (log.isTraceEnabled()) {
                                    log.trace("Lock already acquired for shard={}", shard);
                                }
                                return true;
                            } else {
                                try {
                                    boolean acquired = mutex.acquire(ZK_LOCK_TIMEOUT.getValue(), ZK_LOCK_TIMEOUT.getUnit());
                                    if (acquired) {
                                        setState(LockState.ACQUIRED);
                                        log.debug("Acquired ZK lock for shard={}", shard);
                                    } else {
                                        setState(LockState.ACQUIRE_FAILED);
                                        lockAcquisitionFailure.mark();
                                        log.debug("Acquire ZK failed for shard={}", shard);
                                    }
                                    return acquired;
                                } catch (RuntimeException ex) {
                                    log.debug("Exception on ZK acquire for shard={}", shard);
                                    log.warn(ex.getMessage(), ex);
                                    lockErrors.mark();
                                    setState(LockState.ERROR);
                                    return false;
                                }
                            }
                        }
                    } finally {
                        isAcquiring = false;
                        ctx.stop();
                    }
                }
            };
        }

        /**
         * Attempt to release the lock.
         * @return <code>true</code> if the lock is released by this logic. (Already released lock will return false).
         */
        synchronized Callable<Boolean> releaser() {
            return new Callable<Boolean>() {
                public Boolean call() throws Exception {
                    try {
                        checkMutex();
                        if (!connected || mutex == null) {
                            setState(LockState.ERROR);
                            return true;
                        } else if (state != LockState.ACQUIRED) {
                            return false;
                        } else if (mutex.isAcquiredInThisProcess()) {
                            log.debug("Releasing lock for shard={}.", shard);
                            mutex.release();
                            setState(LockState.DISINTERESTED);
                            return true;
                        } else {
                            log.error("Held lock not held by this process? shard={}.", shard);
                            setState(LockState.UNKNOWN);
                            return true;
                        }
                    } finally {
                        isReleasing = false;
                    }
                }
            };
        }
    }
}

File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/service/ZKBasedShardLockManagerMBean.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import java.util.Collection;

public interface ZKBasedShardLockManagerMBean {
    public Collection<Integer> getHeldShards();
    public Collection<Integer> getUnheldShards();
    public Collection<Integer> getErrorShards();
    
    public long getMinLockHoldTimeMillis();
    public void setMinLockHoldTimeMillis(long millis);
    
    public long getLockDisinterestedTimeMillis();
    public void setLockDisinterestedTimeMillis(long millis);
    
    public void forceLockScavenge();
    public long getSecondsSinceLastScavenge();
    public String getZkConnectionStatus();
    
    public boolean release(int shard);
    public boolean acquire(int shard);
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/tools/jmx/FetchAttributesCallable.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.tools.jmx;

import javax.management.JMX;
import javax.management.MBeanServerConnection;
import javax.management.ObjectName;
import javax.management.remote.JMXConnector;
import javax.management.remote.JMXConnectorFactory;
import javax.management.remote.JMXServiceURL;
import java.lang.reflect.Method;
import java.text.DecimalFormat;
import java.text.Format;
import java.util.concurrent.Callable;

public class FetchAttributesCallable implements Callable<String[]> {
    public static Format DECIMAL_FORMAT = new DecimalFormat("0.00");
    
    private final HostAndPort hostInfo;
    private final ObjectName objectName;
    private final String[] attributes;
    
    public FetchAttributesCallable(HostAndPort hostInfo, ObjectName objectName, String[] attributes) {
        this.hostInfo = hostInfo;
        this.objectName = objectName;
        this.attributes = attributes;
    }
    
    
    public String[] call() throws Exception {
        JMXConnector connector = null;
        String[] values = new String[attributes.length];
        try {
            JMXServiceURL url = new JMXServiceURL(String.format("service:jmx:rmi:///jndi/rmi://%s:%d/jmxrmi", hostInfo.getHost(), hostInfo.getPort()));
            connector = JMXConnectorFactory.connect(url);
            MBeanServerConnection connection = connector.getMBeanServerConnection();    
            Class mbeanClass = Class.forName(
                (String)connection.getMBeanInfo(objectName).getDescriptor().getFieldValue("interfaceClassName"));
            Object handle = JMX.newMBeanProxy(connection, objectName, mbeanClass, true);
            
            for (int i = 0; i < attributes.length; i++) {
                Method attrMethod = mbeanClass.getMethod("get" + attributes[i]);
                values[i] = asString(attrMethod.invoke(handle));
            }
            return values;
        } finally {
            if (connector != null)
                connector.close();
        }
    }
    
    private static String asString(Object obj) {
        if (obj == null)
            return "";
        else if (obj instanceof Double || obj instanceof Float)
            return DECIMAL_FORMAT.format(obj);
        else
            return obj.toString();
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/tools/jmx/HostAndPort.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.tools.jmx;

public class HostAndPort {
    private final String host;
    private final int port;
    
    private HostAndPort(String host, int port) {
        this.host = host;
        this.port = port;
    }

    public String getHost() {
        return host;
    }

    public int getPort() {
        return port;
    }
    
    public static HostAndPort fromString(String s) {
        String[] parts = s.split(":", -1);
        return new HostAndPort(parts[0], Integer.parseInt(parts[1]));
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/tools/jmx/JmxBooleanGauge.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.tools.jmx;

import com.codahale.metrics.JmxAttributeGauge;

import javax.management.ObjectName;

// JmxGauge does not handle booleans. This will typecast boolean to 0 or 1.
public class JmxBooleanGauge extends JmxAttributeGauge {

    public JmxBooleanGauge(ObjectName objectName, String attribute) {
        super(objectName, attribute);
    }

    @Override
    public Object getValue() {
        Object value = super.getValue();
        if (value.equals(true)) {
            return 1;
        }
        return 0;
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/tools/jmx/OutputFormatter.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.tools.jmx;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;

public class OutputFormatter implements Comparable<OutputFormatter> {
    private static final String GAP = "  ";
    
    private final String host;
    private final String[] results;
    
    public OutputFormatter(HostAndPort hostInfo, String[] results) {
        this.host = hostInfo.getHost();
        this.results = results;
    }

    public int compareTo(OutputFormatter o) {
        return host.compareTo(o.host);
    }

    // compute the maximum width for each field across a collection of formatters.
    public static int [] computeMaximums(String[] headers, OutputFormatter... outputs) {
        int[] max = new int[headers.length];
        for (int i = 0; i < headers.length; i++) 
            max[i] = headers[i].length();
        for (OutputFormatter output : outputs) {
            max[0] = Math.max(output.host.length(), max[0]);
            for (int i = 1; i < headers.length; i++)
                max[i] = Math.max(output.results[i-1].length(), max[i]);
        }
        return max;
    }
    
    // formats a header row after maximums have been established.
    public static String formatHeader(int[] maximums, String[] headers) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < headers.length; i++)
            sb = sb.append(formatIn(headers[i], maximums[i], false)).append(GAP);
        return sb.toString();
    }
    
    // formats results and sets formattedStrings.
    public static String[] format(int[] maximums, OutputFormatter... outputs) {
        String[] formattedStrings = new String[outputs.length];
        int pos = 0;
        for (OutputFormatter output : outputs) {
            StringBuilder sb = new StringBuilder();
            sb = sb.append(formatIn(output.host, maximums[0], false));
            for (int i = 0; i < output.results.length; i++)
                sb = sb.append(GAP).append(formatIn(output.results[i], maximums[i+1], true));
            formattedStrings[pos++] = sb.toString();
        }
        return formattedStrings;
    }
    
    private static String formatIn(String s, int spaces, boolean rightAlign) {
        while (s.length() < spaces) {
            if (rightAlign)
                s = " " + s;
            else
                s += " ";
        }
        return s;
    }
    
    public static Collection<OutputFormatter> sort(Collection<OutputFormatter> src) {
        List<OutputFormatter> sortedList = new ArrayList<OutputFormatter>(src);
        Collections.sort(sortedList);
        return sortedList;
    }
    
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/tools/ops/GetPoints.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.tools.ops;

import com.rackspacecloud.blueflood.io.AstyanaxReader;
import com.rackspacecloud.blueflood.outputs.formats.MetricData;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.types.Locator;

import com.rackspacecloud.blueflood.types.Points;
import com.rackspacecloud.blueflood.types.Range;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.apache.commons.cli.*;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * Usage:
 *
 * $JAVA -cp $CLASSPATH GetPoints -tenantId ${tenantId} -metric ${metName} -from ${startTime} \
 *  -to ${endTime} -resolution ${res}
 *
 * tenantId - Tenant ID
 * metric - Name of the metric
 * from - Start time for the range for which you want metrics (specified as milli-seconds since epoch)
 * to - End time for the range for which you want metrics (specified as milli-seconds since epoch)
 * resolution - Resolution of data at which you want the points (one of full, 5m, 20m, 60m, 240m, 1440m)
 */
public class GetPoints {
    private static final TimeValue DEFAULT_RANGE = new TimeValue(7, TimeUnit.DAYS);
    private static final Options cliOptions = new Options();
    private static final GnuParser parser = new GnuParser();
    private static final HelpFormatter helpFormatter = new HelpFormatter();
    private static final String TENANT_ID = "tenantId";
    private static final String METRIC = "metric";
    private static final String FROM = "from";
    private static final String TO = "to";
    private static final String RES = "resolution";

    static {
        cliOptions.addOption(OptionBuilder.isRequired().hasArg(true).withDescription("Tenant ID").create(TENANT_ID));
        cliOptions.addOption(OptionBuilder.isRequired().hasArg(true).withDescription("Metric name").create(METRIC));
        cliOptions.addOption(OptionBuilder.isRequired(false).hasArg(true)
                .withDescription("Start timestamp (millis since epoch)").create(FROM));
        cliOptions.addOption(OptionBuilder.isRequired(false).hasArg(true)
                .withDescription("End timestamp (millis since epoch)").create(TO));
        cliOptions.addOption(OptionBuilder.isRequired(false).hasArg(true)
                .withDescription("Resolution to use: one of 'full, '5m', '30m', '60m', '240m', '1440m'")
                .create(RES));
    }

    public static void main(String args[]) {
        Map<String, Object> options = parseOptions(args);

        Locator locator = Locator.createLocatorFromPathComponents(
                (String) options.get(TENANT_ID),
                (String) options.get(METRIC));

        AstyanaxReader reader = AstyanaxReader.getInstance();

        Long from = (Long) options.get(FROM);
        Long to = (Long) options.get(TO);

        if (from == null || to == null) {
            System.out.println("Either start time or end time is null.");
            to = System.currentTimeMillis();
            from = to - DEFAULT_RANGE.toMillis();
            System.out.println("Using range: " + from + " - " + to);
        }

        if (from >= to) {
            System.err.println("End time " + to + " has to be greater than start time " + from);
            System.exit(2);
        }

        Granularity gran = Granularity.FULL;
        String res = (String) options.get("resolution");
        try {
            gran = Granularity.fromString(res.toLowerCase());
        } catch (Exception ex) {
            System.out.println("Exception mapping resolution to Granularity. Using FULL resolution instead.");
            gran = Granularity.FULL;
        } finally {
            if (gran == null) {
                gran = Granularity.FULL;
            }
        }

        System.out.println("Locator: " + locator + ", from: " + from + ", to: "
                + to + ", resolution: " + gran.shortName());

        MetricData data = reader.getDatapointsForRange(locator, new Range(from, to), gran);
        Map<Long, Points.Point> points = data.getData().getPoints();
        for (Map.Entry<Long, Points.Point> item : points.entrySet()) {
            String output = String.format("Timestamp: %d, Data: %s, Unit: %s", item.getKey(), item.getValue().getData().toString(), data.getUnit());
            System.out.println(output);
        }
    }

    private static Map<String, Object> parseOptions(String[] args) {
        CommandLine line;
        final Map<String, Object> options = new HashMap<String, Object>();
        long now = System.currentTimeMillis();
        options.put(TO, now);
        options.put(FROM, now - DEFAULT_RANGE.toMillis());
        options.put(RES, "full");

        try {
            line = parser.parse(cliOptions, args);

            if (line.hasOption(TENANT_ID)) {
                options.put(TENANT_ID, line.getOptionValue(TENANT_ID));
            }

            if (line.hasOption(METRIC)) {
                options.put(METRIC, line.getOptionValue(METRIC));
            }

            if (line.hasOption(FROM)) {
                options.put(FROM, new Long(line.getOptionValue(FROM)));
            }

            if (line.hasOption(TO)) {
                options.put(TO, new Long(line.getOptionValue(TO)));
            }

            if (line.hasOption(RES)) {
                options.put(RES, line.getOptionValue(RES).toLowerCase());
            }
        } catch (ParseException ex) {
            System.err.println("Parse exception " + ex.getMessage());
            helpFormatter.printHelp("GetPoints", cliOptions);
            System.exit(2);
        }

        return options;
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/types/AbstractRollupStat.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import com.rackspacecloud.blueflood.utils.Util;

public abstract class AbstractRollupStat {
    private long longValue;
    private double doubleValue;
    private boolean isFloatingPoint;

    public AbstractRollupStat() {
        this.longValue = 0;
        this.doubleValue = 0;
        this.isFloatingPoint = false;
    }

    public boolean isFloatingPoint() {
        return this.isFloatingPoint;
    }

    public double toDouble() {
        return this.doubleValue;
    }

    public long toLong() {
        return this.longValue;
    }

    @Override
    public boolean equals(Object otherObject) {
        if (!(otherObject instanceof AbstractRollupStat)) {
            return false;
        }

        AbstractRollupStat other = (AbstractRollupStat)otherObject;

        if (this.isFloatingPoint != other.isFloatingPoint()) {
            return false;
        }

        if (this.isFloatingPoint) {
            return this.toDouble() == other.toDouble();
        } else {
            return this.toLong() == other.toLong();
        }
    }

    public void setLongValue(long value) {
        this.isFloatingPoint = false;
        this.longValue = value;
    }

    public void setDoubleValue(double value) {
        this.isFloatingPoint = true;
        this.doubleValue = value;
    }
    
    abstract void handleFullResMetric(Object o) throws RuntimeException;
    abstract void handleRollupMetric(IBasicRollup basicRollup) throws RuntimeException;
    abstract public byte getStatType();
    
    public String toString() {
        if (isFloatingPoint)
            return Util.DECIMAL_FORMAT.format(doubleValue);
        else
            return Long.toString(longValue);
    }
    
    public static void set(AbstractRollupStat stat, Number value) {
        if (value instanceof Long)
            stat.setLongValue(value.longValue());
        else if (value instanceof Double)
            stat.setDoubleValue(value.doubleValue());
        else if (value instanceof Integer)
            stat.setLongValue(value.longValue());
        else if (value instanceof Float)
            stat.setDoubleValue(value.doubleValue());
        else
            throw new ClassCastException(String.format("%s cannot be set to AbstractRollupState.value", value.getClass().getName()));
    }
}

File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/types/AppMetricLocator.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

public class AppMetricLocator extends Locator {
    private static final String incomingDelim = ".";
    private static final String persistDelim = ",";
    private static final int MAX_FIELDS = 4;

    private String service;
    private String host;
    private String instance;
    private String metricName;

    public static AppMetricLocator createFromServicePrimitives(String service, String host, String instance,
                                                               String metricName) {
        return new AppMetricLocator(service, host, instance, metricName);
    }

    public static AppMetricLocator createFromDBKey(String locator) {
        return new AppMetricLocator(locator);
    }

    private AppMetricLocator(String locator) {
        if (!isValidDBKey(locator, persistDelim)) {
            throw new IllegalArgumentException("Expected delimiter " + "'" + persistDelim + "' " + "but got " +
                    locator);
        }

        String[] tokens = locator.split(persistDelim);
        this.service = tokens[0];
        this.host = tokens[1];
        this.instance = tokens[2];
        this.metricName = tokens[3];
        setStringRep(this.buildStringRep());
    }

    private AppMetricLocator(String service, String host, String instance, String metricName) {
        this.service = service;
        this.host = host;
        this.instance = instance;
        this.metricName = metricName;
        setStringRep(this.buildStringRep());
    }

    public String getService() {
        return service;
    }

    public String getHost() {
        return host;
    }

    public String getInstanceId() {
        return instance;
    }

    public String getMetricName() {
        return metricName;
    }

    private String buildStringRep() {
        return String.format("%s,%s,%s,%s", this.service, this.host, this.instance, this.metricName);
    }

    public boolean equals(Locator other) {
        return other.toString().equals(toString());
    }

    public String getDBKey() {
        return toString();
    }
}

File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/types/Average.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import com.rackspacecloud.blueflood.io.Constants;

/**
 * I implemented this on a transatlantic flight, in a benadryl-induced haze.
 * <p/>
 * The goal was to end up with an Average class that 1) didn't need to know much about its type ahead of time (lest we
 * store type in the locator, but that would have other implications), 2) avoided potentially large summations.
 */
public class Average extends AbstractRollupStat {
    private long longRemainder = 0;
    private long count = 0;

    public Average() {
        super();

    }

    @SuppressWarnings("unused") // used by Jackson
    public Average(long value) {
        this();
        this.setLongValue(value);
    }

    @SuppressWarnings("unused") // used by Jackson
    public Average(double value) {
        this();
        this.setDoubleValue(value);
    }

    public Average(int count, Object value) {
        this();

        if (value instanceof Long)
            setLongValue((Long)value);
        else if (value instanceof Integer)
            setLongValue(((Integer)value).longValue());
        else if (value instanceof Double)
            setDoubleValue((Double)value);
        else if (value instanceof Float)
            setDoubleValue(((Float)value).doubleValue());
        else
            throw new RuntimeException(String.format("Unexpected type: %s", value.getClass().getName()));
        this.count = count;
    }

    //
    // long methods.
    //

    public void add(Long input) {
        count++;
        final long longAvgUntilNow = toLong();

        // accuracy could be improved by using summation+division until either count or sum reached a certain level.
        setLongValue(toLong() + ((input + longRemainder - longAvgUntilNow) / count));
        longRemainder = (input + longRemainder - longAvgUntilNow) % count;
    }

    public void addBatch(Long input, long dataPoints) {
        for (long i = 0; i < dataPoints; i++) {
            add(input);
        }
    }

    //
    // double methods.
    //

    public void add(Double input) {
        this.setDoubleValue(toDouble() + ((input - toDouble()) / ++count));
    }

    public void addBatch(Double input, long dataPoints) {
        // if my maths were better, I would know the decay function that would give me the right value.
        for (long i = 0; i < dataPoints; i++) {
            add(input);
        }
    }

    //
    // common methods
    //

    @Override
    void handleFullResMetric(Object number) throws RuntimeException {
        if (number instanceof Long)
            add((Long) number);
        else if (number instanceof Double)
            add((Double)number);
        else if (number instanceof Integer)
            add(((Integer) number).longValue());
        else throw new RuntimeException("Unexpected type to average: " + number.getClass().getName());
    }

    @Override
    void handleRollupMetric(IBasicRollup basicRollup) throws RuntimeException {
        AbstractRollupStat other = basicRollup.getAverage();
        if (isFloatingPoint() || other.isFloatingPoint())
            addBatch(other.toDouble(), basicRollup.getCount());
        else
            addBatch(other.toLong(), basicRollup.getCount());
    }

    @Override
    public byte getStatType() {
        return Constants.AVERAGE;
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/types/BasicRollup.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.Map;


public class BasicRollup implements Rollup, IBasicRollup {
    private static final Logger log = LoggerFactory.getLogger(BasicRollup.class);
    public static final int NUM_STATS = 4;
    
    private Average average;
    private Variance variance;
    private MinValue minValue;
    private MaxValue maxValue;
    private long count;

    public BasicRollup() {
        this.average = new Average();
        this.variance = new Variance();
        this.minValue = new MinValue();
        this.maxValue = new MaxValue();
        this.count = 0;
    }

    @Override
    public boolean equals(Object other) {
        if (!(other instanceof BasicRollup)) {
            return false;
        }

        BasicRollup otherBasicRollup = (BasicRollup)other;

        return (this.count == otherBasicRollup.getCount())
                && average.equals(otherBasicRollup.getAverage())
                && variance.equals(otherBasicRollup.getVariance())
                && minValue.equals(otherBasicRollup.getMinValue())
                && maxValue.equals(otherBasicRollup.getMaxValue());
    }

    public Average getAverage() {
        return this.average;
    }

    public Variance getVariance() {
        return this.variance;
    }

    public MinValue getMinValue() {
        return this.minValue;
    }

    public MaxValue getMaxValue() {
        return this.maxValue;
    }

    public long getCount() {
        return this.count;
    }

    public String toString() {
        return String.format("cnt:%d, avg:%s, var:%s, min:%s, max:%s", count, average, variance, minValue, maxValue);
    }
    
    // setters
    // should I have made these chainable like TimerRollup?
    
    public void setCount(long count) {
        this.count = count;
    }
    
    public void setMin(MinValue min) {
        this.minValue = min;
    }
    
    public void setMin(Number min) {
        AbstractRollupStat.set(this.minValue, min);
    }
    
    public void setMax(MaxValue max) {
        this.maxValue = max;
    }
    
    public void setMax(Number max) {
        AbstractRollupStat.set(this.maxValue, max);
    }
    
    public void setVariance(Variance var) {
        this.variance = var;
    }
    
    public void setVariance(Number var) {
        AbstractRollupStat.set(this.variance, var);
    }

    public void setAverage(Average avg) {
        this.average = avg;
    }
    
    public void setAverage(Number avg) {
        AbstractRollupStat.set(this.average, avg);
    }
    
    // merge simple numbers with this rollup.
    protected void computeFromSimpleMetrics(Points<SimpleNumber> input) throws IOException {
        if (input == null) {
            throw new IOException("Null input to create rollup from");
        }

        if (input.isEmpty()) {
            return;
        }

        Map<Long, Points.Point<SimpleNumber>> points = input.getPoints();
        for (Map.Entry<Long, Points.Point<SimpleNumber>> item : points.entrySet()) {
            this.count += 1;
            SimpleNumber numericMetric = item.getValue().getData();
            average.handleFullResMetric(numericMetric.getValue());
            variance.handleFullResMetric(numericMetric.getValue());
            minValue.handleFullResMetric(numericMetric.getValue());
            maxValue.handleFullResMetric(numericMetric.getValue());
        }
    }
    
    // allows incrementally updating this rollup. This isn't part of the public API, so is declared unsafe.
    public void computeFromSimpleMetricsUnsafe(Points<SimpleNumber> input) throws IOException {
        computeFromSimpleMetrics(input);
    }

    // merge rollups into this rollup.
    protected void computeFromRollups(Points<IBasicRollup> input) throws IOException {
        if (input == null) {
            throw new IOException("Null input to create rollup from");
        }

        if (input.isEmpty()) {
            return;
        }

        // See this and get mind blown:
        // http://stackoverflow.com/questions/18907262/bounded-wildcard-related-compiler-error
        Map<Long, ? extends Points.Point<? extends IBasicRollup>> points = input.getPoints();

        for (Map.Entry<Long, ? extends Points.Point<? extends IBasicRollup>> item : points.entrySet()) {
            IBasicRollup rollup = item.getValue().getData();
            if (!(rollup instanceof BasicRollup)) {
                throw new IOException("Cannot create BasicRollup from type " + rollup.getClass().getName());
            }
            BasicRollup basicRollup = (BasicRollup) rollup;
            this.count += basicRollup.getCount();
            average.handleRollupMetric(basicRollup);
            variance.handleRollupMetric(basicRollup);
            minValue.handleRollupMetric(basicRollup);
            maxValue.handleRollupMetric(basicRollup);
        }
    }
    
    // allows merging with this rollup with another rollup. This is declared unsafe because it isn't part of the 
    // rollup API.
    public void computeFromRollupsUnsafe(Points<IBasicRollup> input) throws IOException {
        computeFromRollups(input);
    }

    public static BasicRollup buildRollupFromRawSamples(Points<SimpleNumber> input) throws IOException {
        final BasicRollup basicRollup = new BasicRollup();
        basicRollup.computeFromSimpleMetrics(input);

        return basicRollup;
    }

    public static BasicRollup buildRollupFromRollups(Points<BasicRollup> input) throws IOException {
        final BasicRollup basicRollup = new BasicRollup();
        basicRollup.computeFromRollups(recast(input, IBasicRollup.class));
        return basicRollup;
    }
    
    // yay generics?
    public static <T extends IBasicRollup> Points<T> recast(Points<? extends BasicRollup> points, Class<T> type) {
        Points<T> newPoints = new Points<T>();
        for (Map.Entry<Long, ? extends Points.Point<? extends BasicRollup>> entry : points.getPoints().entrySet())
            newPoints.add(new Points.Point<T>(entry.getKey(), (T)entry.getValue().getData()));
        return newPoints;
    }

    @Override
    public Boolean hasData() {
        return getCount() > 0;
    }

    @Override
    public RollupType getRollupType() {
        return RollupType.BF_BASIC;
    }
}

File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/types/HistogramRollup.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import com.bigml.histogram.*;

import java.io.IOException;
import java.util.Collection;
import java.util.HashMap;
import java.util.Map;

public class HistogramRollup implements Rollup {
    private final Histogram<SimpleTarget> histogram;
    public static Integer MAX_BIN_SIZE = 64;

    private HistogramRollup(int bins) {
        if (bins > MAX_BIN_SIZE) {
            bins = MAX_BIN_SIZE;
        } else if (bins <= 0) {
            bins = 1;
        }
        this.histogram = new Histogram<SimpleTarget>(bins);
    }

    public HistogramRollup(Collection<Bin<SimpleTarget>> bins) {
        this.histogram = new Histogram(bins.size());
        for (Bin<SimpleTarget> bin : bins) {
            this.histogram.insertBin(bin);
        }
    }

    private void computeFromRollups(Points<HistogramRollup> input) throws IOException {
        if (input == null) {
            throw new IOException("Null input to create rollup from");
        }

        if (input.isEmpty()) {
            return;
        }

        Map<Long, Points.Point<HistogramRollup>> points = input.getPoints();

        for (Map.Entry<Long, Points.Point<HistogramRollup>> item : points.entrySet()) {
            HistogramRollup rollup = item.getValue().getData();
            try {
                histogram.merge(rollup.histogram);
            } catch (MixedInsertException ex) {
                throw new IOException(ex);
            }
        }
    }

    private void computeFromSimpleMetrics(Points<SimpleNumber> input) throws IOException {
        try {
            for (Map.Entry<Long, Points.Point<SimpleNumber>> item : input.getPoints().entrySet()) {
                histogram.insert(toDouble(item.getValue().getData().getValue()));
            }
        } catch (MixedInsertException ex) {
            throw new IOException(ex);
        }
    }

    public static HistogramRollup buildRollupFromRawSamples(Points<SimpleNumber> input) throws IOException {
        int number_of_bins = getIdealNumberOfBins(input);
        final HistogramRollup histogramRollup = new HistogramRollup(number_of_bins);
        histogramRollup.computeFromSimpleMetrics(input);

        return histogramRollup;
    }

    public static HistogramRollup buildRollupFromRollups(Points<HistogramRollup> input) throws IOException {
        final HistogramRollup histogramRollup = new HistogramRollup(MAX_BIN_SIZE);
        histogramRollup.computeFromRollups(input);

        return histogramRollup;
    }

    public int getMaxBins() {
        return histogram.getMaxBins();
    }

    public long getCount() {
        return (long)histogram.getBins().size();
    }

    public Collection<Bin<SimpleTarget>> getBins() {
        return histogram.getBins();
    }

    public HashMap<Double, Double> getPercentile(Double... percentileLimit) {
        return histogram.percentiles(percentileLimit);
    }

    public static double getVariance(Points<SimpleNumber> input) {
        final Variance variance = new Variance();
        for (Map.Entry<Long, Points.Point<SimpleNumber>> item : input.getPoints().entrySet()) {
            variance.handleFullResMetric(item.getValue().getData().getValue());
        }

        return variance.toDouble();
    }

    public static int getIdealNumberOfBins(Points<SimpleNumber> input) {
        // Scott's rule
        return Math.abs((int) Math.floor(3.5 * (Math.sqrt(getVariance(input))/Math.cbrt(input.getPoints().size()))));
    }

    private double toDouble(Object val) throws RuntimeException {
        if (val instanceof Integer) {
            return new Double((Integer) val);
        } else if (val instanceof Long) {
            return new Double((Long) val);
        } else if (val instanceof Double) {
            return (Double) val;
        } else {
            throw new RuntimeException("Unsupported data type for histogram");
        }
    }

    @Override
    public Boolean hasData() {
        throw new RuntimeException("Unsupported operation for histogram");
    }

    @Override
    public RollupType getRollupType() {
        return RollupType.BF_HISTOGRAMS;
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/types/IBasicRollup.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

public interface IBasicRollup {
    public AbstractRollupStat getAverage();
    public AbstractRollupStat getVariance();
    public AbstractRollupStat getMinValue();
    public AbstractRollupStat getMaxValue();
    public long getCount();
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/types/Locator.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import com.rackspacecloud.blueflood.service.Configuration;
import com.rackspacecloud.blueflood.service.CoreConfig;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class Locator implements Comparable<Locator> {
    private static final String metricTokenSeparator;
    private static final String metricTokenSeparatorRegex;
    private static final Logger log = LoggerFactory.getLogger(Locator.class);
    private String stringRep = null;
    private String tenantId = null;
    private String metricName = null;

    static {
        metricTokenSeparator = (Configuration.getInstance().getBooleanProperty(CoreConfig.USE_LEGACY_METRIC_SEPARATOR) ? "," : ".");
        // ugh.
        metricTokenSeparatorRegex = (Configuration.getInstance().getBooleanProperty(CoreConfig.USE_LEGACY_METRIC_SEPARATOR) ? "," : "\\.");
        if (metricTokenSeparator.equals(",")) {
            log.warn("Deprecation warning! Use of 'USE_LEGACY_METRIC_SEPARATOR' is deprecated and will be removed in v3.0");
        }
    }

    public Locator() {
        // Left empty
    }

    private Locator(String fullyQualifiedMetricName) throws IllegalArgumentException {
        setStringRep(fullyQualifiedMetricName);
    }

    protected void setStringRep(String rep) throws IllegalArgumentException {
        // todo: null check and throw IllegalArgumentException?
        this.stringRep = rep;
        tenantId = this.stringRep.split(metricTokenSeparatorRegex)[0];
        metricName = this.stringRep.substring(this.stringRep.indexOf(metricTokenSeparator)+1);
    }

    protected boolean isValidDBKey(String dbKey, String delim) {
        return dbKey.contains(delim);
    }

    @Override
    public int hashCode() {
        return stringRep == null ? 0 : stringRep.hashCode();
    }

    @Override
    public boolean equals(Object obj) {
        return obj != null && obj instanceof Locator && obj.hashCode() == this.hashCode();
    }

    public String toString() {
        return stringRep;
    }

    public String getTenantId() {
        return this.tenantId;
    }

    public String getMetricName() {
        return this.metricName;
    }

    public boolean equals(Locator other) {
        return stringRep.equals(other.toString());
    }

    public static Locator createLocatorFromPathComponents(String tenantId, String... parts) throws IllegalArgumentException {
        return new Locator(tenantId + metricTokenSeparator + StringUtils.join(parts, metricTokenSeparator));
    }

    public static Locator createLocatorFromDbKey(String fullyQualifiedMetricName) throws IllegalArgumentException {
        return new Locator(fullyQualifiedMetricName);
    }

    @Override
    public int compareTo(Locator o) {
        return stringRep.compareTo(o.toString());
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/types/MaxValue.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import com.rackspacecloud.blueflood.io.Constants;

public class MaxValue extends AbstractRollupStat {
    private boolean init;

    public MaxValue() {
        super();

        this.init = true;
        this.setDoubleValue(0.0);
        this.setLongValue(0);
    }

    @SuppressWarnings("unused") // used by Jackson
    public MaxValue(long value) {
        this();
        this.setLongValue(value);
    }

    @SuppressWarnings("unused") // used by Jackson
    public MaxValue(double value) {
        this();
        this.setDoubleValue(value);
    }

    @Override
    void handleFullResMetric(Object o) throws RuntimeException {
        if (o instanceof Double) {
            if (init) {
                this.setDoubleValue((Double)o);
                this.init = false;
                return;
            }

            if (!this.isFloatingPoint()) {
                if ((double)this.toLong() < (Double)o) {
                    this.setDoubleValue((Double)o);
                }
            } else {
                this.setDoubleValue(Math.max(this.toDouble(), (Double)o));
            }
        } else if (o instanceof Long || o instanceof Integer) {
            Long val;
            if (o instanceof Integer) {
                val = ((Integer)o).longValue();
            } else {
                val = (Long)o;
            }

            if (init) {
                this.setLongValue(val);
                this.init = false;
                return;
            }

            if (this.isFloatingPoint()) {
                double doubleValOther = val.doubleValue();
                if (this.toDouble()< doubleValOther) {
                    this.setLongValue(val);
                }
            } else {
                this.setLongValue(Math.max(this.toLong(), val));
            }
        } else {
            throw new RuntimeException("Unsuppored type " + o.getClass().getName() +" for min");
        }
    }

    @Override
    void handleRollupMetric(IBasicRollup basicRollup) throws RuntimeException {
        AbstractRollupStat other = basicRollup.getMaxValue();

        if (init) {
            if (other.isFloatingPoint()) {
                this.setDoubleValue(other.toDouble());
            } else {
                this.setLongValue(other.toLong());
            }

            this.init = false;
            return;
        }

        if (this.isFloatingPoint() && !other.isFloatingPoint()) {
            if (this.toDouble() < (double)other.toDouble()) {
                this.setLongValue(other.toLong());
            }
        } else if (!this.isFloatingPoint() && other.isFloatingPoint()) {
            if ((double)this.toLong() < other.toDouble()) {
                this.setDoubleValue(other.toDouble());
            }
        } else if (!this.isFloatingPoint() && !other.isFloatingPoint()) {
            this.setLongValue(Math.max(this.toLong(), other.toLong()));
        } else {
            this.setDoubleValue(Math.max(this.toDouble(), other.toDouble()));
        }
    }

    @Override
    public byte getStatType() {
        return Constants.MAX;
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/types/Metric.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;


import com.rackspacecloud.blueflood.exceptions.InvalidDataException;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.math.BigInteger;

public class Metric implements IMetric {
    private static final Logger log = LoggerFactory.getLogger(Metric.class);

    private final Locator locator;
    private Object metricValue;
    private final long collectionTime;
    private int ttlInSeconds;
    private DataType dataType;
    private final String unit;
    private static BigDecimal DOUBLE_MAX = new BigDecimal(Double.MAX_VALUE);

    public Metric(Locator locator, Object metricValue, long collectionTime, TimeValue ttl, String unit) {
        this.locator = locator;
        this.metricValue = metricValue;
        // I dislike throwing errors in constructors, but there is no other way without resorting to a json schema.
        if (collectionTime < 0) {
            throw new InvalidDataException("collection time must be greater than zero");
        }
        this.collectionTime = collectionTime;
        this.dataType = DataType.getMetricType(metricValue);
        this.unit = unit;

        // TODO: Until we start handling BigInteger throughout, let's try to cast it to double if the int value is less
        // than Double.MAX_VALUE

        if (metricValue instanceof BigInteger) {
            BigDecimal maybeDouble = new BigDecimal((BigInteger) metricValue);
            if (maybeDouble.compareTo(DOUBLE_MAX) > 0) {
                log.warn("BigInteger metric value " + ((BigInteger)metricValue).toString() + " for metric "
                        + locator.toString() + " is bigger than Double.MAX_VALUE");
                throw new RuntimeException("BigInteger cannot be force cast to double as it exceeds Double.MAX_VALUE");
            }
            this.dataType = DataType.NUMERIC;
            this.metricValue = ((BigInteger) metricValue).doubleValue();
        }

        setTtl(ttl);
    }

    public Locator getLocator() {
        return locator;
    }

    public Object getMetricValue() {
        return metricValue;
    }

    public DataType getDataType() {
        return dataType;
    }

    public int getTtlInSeconds() {
        return ttlInSeconds;
    }

    public long getCollectionTime() {
        return collectionTime;
    }

    public String getUnit() {
        return unit;
    }

    public boolean isNumeric() {
        return DataType.isNumericMetric(metricValue);
    }

    public boolean isString() {
        return DataType.isStringMetric(metricValue);
    }

    public boolean isBoolean() {
        return DataType.isBooleanMetric(metricValue);
    }

    public void setTtl(TimeValue ttl) {
        if (!isValidTTL(ttl.toSeconds())) {
            throw new InvalidDataException("TTL supplied for metric is invalid. Required: 0 < ttl < " + Integer.MAX_VALUE +
                    ", provided: " + ttl.toSeconds());
        }

        ttlInSeconds = (int) ttl.toSeconds();
    }

    public void setTtlInSeconds(int ttlInSeconds) {
        if (!isValidTTL(ttlInSeconds)) {
            throw new InvalidDataException("TTL supplied for metric is invalid. Required: 0 < ttl < " + Integer.MAX_VALUE +
                    ", provided: " + ttlInSeconds);
        }

        this.ttlInSeconds = ttlInSeconds;
    }
    
    public RollupType getRollupType() {
        return RollupType.BF_BASIC;
    }

    @Override
    public String toString() {
        return String.format("%s:%s:%s:%s:%s", locator.toString(), metricValue, dataType, ttlInSeconds, unit == null ? "" : unit.toString());
    }

    private boolean isValidTTL(long ttlInSeconds) {
        return (ttlInSeconds < Integer.MAX_VALUE && ttlInSeconds > 0);
    }

    @Override
    public boolean equals(Object o) {
        if (!(o instanceof Metric)) {
            return false;
        }
        Metric other = (Metric) o;
        if (locator.equals(other.getLocator()) &&
                collectionTime == other.getCollectionTime() &&
                ttlInSeconds == other.getTtlInSeconds() &&
                dataType.equals(other.getDataType()) &&
                unit.equals(other.getUnit())) {
            return true;
        }
        return false;
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/types/MetricMetadata.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

public enum MetricMetadata {
    TYPE (0),
    UNIT (1),
    ROLLUP_TYPE (2);

    private final int value;
    MetricMetadata(int value) {
        this.value = value;
    }
    public int value() { return value; }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/types/MetricsCollection.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import com.google.common.collect.Lists;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

public class MetricsCollection {
    private final List<IMetric> metrics;

    public MetricsCollection() {
        this.metrics = new ArrayList<IMetric>();
    }

    public void add(Collection<IMetric> other) {
        metrics.addAll(other);
    }

    public Collection<IMetric> toMetrics() {
        return metrics;
    }

    public int size() {
        return metrics.size();
    }

    public List<List<IMetric>> splitMetricsIntoBatches(int sizePerBatch) {
        if (sizePerBatch <= 0) {
            sizePerBatch = metrics.size();
        }
        return Lists.partition(metrics, sizePerBatch);
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/types/MinValue.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import com.rackspacecloud.blueflood.io.Constants;

public class MinValue extends AbstractRollupStat {
    private boolean init;

    public MinValue() {
        super();

        this.init = true;
        this.setDoubleValue(0.0d);
        this.setLongValue(0);
    }

    @SuppressWarnings("unused") // used by Jackson
    public MinValue(long value) {
        this();
        this.setLongValue(value);
    }

    @SuppressWarnings("unused") // used by Jackson
    public MinValue(double value) {
        this();
        this.setDoubleValue(value);
    }

    @Override
    void handleFullResMetric(Object o) throws RuntimeException {
        if (o instanceof Double) {
            if (init) {
                this.setDoubleValue((Double)o);
                this.init = false;
                return;
            }

            if (!this.isFloatingPoint()) {
                if ((double)this.toLong() > (Double)o) {
                    this.setDoubleValue((Double)o);
                }
            } else {
                this.setDoubleValue(Math.min(this.toDouble(), (Double)o));
            }
        } else if (o instanceof Long || o instanceof Integer) {
            Long val;
            if (o instanceof Integer) {
                val = ((Integer)o).longValue();
            } else {
                val = (Long)o;
            }

            if (init) {
                this.setLongValue(val);
                this.init = false;
                return;
            }

            if (this.isFloatingPoint()) {
                double doubleValOther = val.doubleValue();
                if (this.toDouble()> doubleValOther) {
                    this.setLongValue(val);
                }
            } else {
                this.setLongValue(Math.min(this.toLong(), val));
            }
        } else {
            throw new RuntimeException("Unsuppored type " + o.getClass().getName() +" for min");
        }
    }

    @Override
    void handleRollupMetric(IBasicRollup basicRollup) throws RuntimeException {
        AbstractRollupStat other = basicRollup.getMinValue();

        if (init) {
            if (other.isFloatingPoint()) {
                this.setDoubleValue(other.toDouble());
            } else {
                this.setLongValue(other.toLong());
            }

            init = false;
            return;
        }

        if (this.isFloatingPoint() && !other.isFloatingPoint()) {
            if (this.toDouble() > (double)other.toLong()) {
                this.setLongValue(other.toLong());
            }
        } else if (!this.isFloatingPoint() && other.isFloatingPoint()) {
            if ((double)this.toLong()> other.toDouble()) {
                this.setDoubleValue(other.toDouble());
            }
        } else if (!this.isFloatingPoint() && !other.isFloatingPoint()) {
            this.setLongValue(Math.min(this.toLong(), other.toLong()));
        } else {
            this.setDoubleValue(Math.min(this.toDouble(), other.toDouble()));
        }
    }

    @Override
    public byte getStatType() {
        return Constants.MIN;
    }
}

File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/types/Points.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import java.util.Map;
import java.util.TreeMap;

public class Points<T> {
    private Map<Long, Point<T>> points; // Map of timestamp to Point

    public Points() {
        this.points = new TreeMap<Long, Point<T>>();
    }

    public void add(Point<T> point) {
        points.put(point.getTimestamp(), point);
    }

    public Map<Long, Point<T>> getPoints() {
        return points;
    }

    public boolean isEmpty() {
        return points.isEmpty();
    }
    
    public Class getDataClass() {
        if (points.size() == 0)
            throw new IllegalStateException("");
        return points.values().iterator().next().data.getClass();
    }

    public static class Point<T> {
        private final T data;
        private final long timestamp;

        public Point(long timestamp, T data) {
            this.timestamp = timestamp;
            this.data = data;
        }

        public long getTimestamp() {
            return timestamp;
        }

        public T getData() {
            return data;
        }

        @Override
        public int hashCode() {
            return (int)(timestamp ^ (timestamp >>> 32)) ^ data.hashCode();
        }

        @Override
        public boolean equals(Object obj) {
            if (obj == null || !(obj instanceof Point))
                return false;
            try {
                Point<T> other = (Point<T>)obj;
                return other.getTimestamp() == this.getTimestamp()
                        && other.getData().equals(this.getData());
            } catch (ClassCastException ex) {
                // not a Point<T>, but a Point<X> instead?
                return false;
            }
        }
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/types/PreaggregatedMetric.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import com.rackspacecloud.blueflood.utils.TimeValue;

import java.util.concurrent.TimeUnit;

/** It's like a rollup already. */
public class PreaggregatedMetric implements IMetric {
    private final long collectionTime;
    private final Locator locator;
    private TimeValue ttl;
    private final Rollup value;
    private final RollupType type;
    
    public PreaggregatedMetric(long collectionTime, Locator locator, TimeValue ttl, Rollup value) {
        this.collectionTime = collectionTime;
        this.locator = locator;
        this.ttl = ttl;
        this.value = value;
        this.type = RollupType.fromRollup(value);
    }

    @Override
    public RollupType getRollupType() {
        return type;
    }

    public Locator getLocator() { return locator; }
    public long getCollectionTime() { return collectionTime; }
    public int getTtlInSeconds() { return (int)ttl.toSeconds(); }
    public Rollup getMetricValue() { return value; }
    public void setTtlInSeconds(int seconds) { ttl = new TimeValue(seconds, TimeUnit.SECONDS); }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/types/Range.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import com.rackspacecloud.blueflood.exceptions.GranularityException;
import com.rackspacecloud.blueflood.rollup.Granularity;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

// typed pair tuple.
public class Range {

    public final long start;
    public final long stop;

    public Range(long l, long r) {
        if (l >= r) {
            throw new IllegalArgumentException("start cannot be greater than end");
        }
        start = l;
        stop = r;
    }

    public long getStart() {
        return start;
    }

    public long getStop() {
        return stop;
    }

    @Override
    public int hashCode() {
        return (int)(start * 3 + stop * 7);
    }

    @Override
    public boolean equals(Object obj) {
        if (!(obj instanceof Range))
            return false;
        else {
            Range other = (Range)obj;
            return other.start == start && other.stop == stop;
        }
    }

    @Override
    public String toString() {
        return String.format("%d:%d (%d)", start, stop, stop-start);
    }
    
    /**
     * given a start and stop time, return an iterator over ranges in *this* granularity that should be rolled up into
     * single points in the next coarser granularity.
     * 
     * Here is an example:  Given start/end (s,e), we need to return all the ranges in Y that correspond to rollup 
     * periods A,B,C.  This involves returning ranges prior to (s) and after (e) that map to parts of (A) and (C) in
     * the coarser rollup.
     * 
     * X [       A      |       B      |       C      |       D      ]
     * Y [    |    | s  |    |    |    |  e |    |    |    |    |    ]\
     * 
     * @param startMillis
     * @param stopMillis
     * @return
     */
    public static Iterable<Range> getRangesToRollup(Granularity g, final long startMillis,
                                                    final long stopMillis) throws GranularityException {
        final long snappedStartMillis = g.coarser().snapMillis(startMillis);
        final long snappedStopMillis = g.coarser().snapMillis(stopMillis + g.coarser().milliseconds());

        return new IntervalRangeIterator(g, snappedStartMillis, snappedStopMillis);
    }

    /**
     * Returns a mapping of ranges in the coarser granularity to the sub-ranges in finer granularity
     *
     * Here is an example: Given start/end (s,e), we need to return mapping between ranges in Y that will be mapped to
     * a single range in X. From the example above, it will be mapping from A to all the sub-ranges in Y that get rolled
     * to a single point in A
     * @param g Coarser Granularity
     * @param range Range to be mapped
     * @return
     * @throws GranularityException
     */
    public static Map<Range, Iterable<Range>> mapFinerRanges(Granularity g, Range range) throws GranularityException {

        if(range.getStart() >= range.getStop())
            throw new IllegalArgumentException("start cannot be greater than end. Start: " + range.getStart() + " Stop:" + range.getStop());

        final long snappedStartMillis = g.snapMillis(range.getStart());
        final long snappedStopMillis = g.snapMillis(range.getStop() + g.milliseconds());
        HashMap<Range, Iterable<Range>> rangeMap = new HashMap<Range, Iterable<Range>>();
        long tempStartMillis = snappedStartMillis;
        int numberOfMillis = g.milliseconds();

        while (tempStartMillis <= (snappedStopMillis - numberOfMillis)) {
            Range slotRange = new Range(tempStartMillis, tempStartMillis + numberOfMillis);
            rangeMap.put(slotRange, new IntervalRangeIterator(g.finer(), slotRange.start, slotRange.stop));
            tempStartMillis = tempStartMillis + numberOfMillis;
        }

        return rangeMap;
    }

    /** return the Ranges for an interval at this granularity
     * @param from start time
     * @param to end time
     * @return Range[]
     */
    public static Iterable<Range> rangesForInterval(Granularity g, final long from, final long to) {
        if (g == Granularity.FULL) {
            return Arrays.asList(new Range(from, to));
        }

        final long snappedStartMillis = g.snapMillis(from);
        final long snappedStopMillis = g.snapMillis(to + g.milliseconds());

        return new IntervalRangeIterator(g, snappedStartMillis, snappedStopMillis);
    }

    /** iterate over Ranges in an interval at a Granularity */
    private static class IntervalRangeIterator implements Iterable<Range> {

        final Granularity granularity;
        final long start;
        final long stop;

        IntervalRangeIterator(Granularity g, long start, long stop) {
            granularity = g;
            this.start = start;
            this.stop = Math.min(stop, System.currentTimeMillis());
        }

        public Iterator<Range> iterator() {
            return new Iterator<Range>() {
                long pos = start;
                public boolean hasNext() {
                    return pos < stop;
                }

                public Range next() {
                    Range res = null;
                    if (pos + granularity.milliseconds() > stop) {
                        res = new Range(pos, stop - 1);
                        pos = stop;
                    } else {
                        long end = granularity.snapMillis(pos + granularity.milliseconds()) - 1;
                        res = new Range(pos, end);
                        pos = end + 1;
                    }
                    return res;
                }

                public void remove() { throw new RuntimeException("Not supported"); }
            };
        };
    }
}

File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/types/Resolution.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

public enum Resolution {
    FULL(0),
    MIN5(1),
    MIN20(2),
    MIN60(3),
    MIN240(4),
    MIN1440(5);

    private final int value;

    private Resolution(int value) {
        this.value = value;
    }

    public int getValue() {
        return value;
    }

    public static Resolution fromString(String name) {
        return Resolution.valueOf(name.toUpperCase());
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/types/Rollup.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import java.io.IOException;

public interface Rollup {
    
    // todo: these classes and instance can be moved into a static Computations holder.
    
    public abstract static class Type<I extends Rollup, O extends Rollup> {
        public abstract O compute(Points<I> input) throws IOException;
    }
    
    public static final Type<SimpleNumber, BasicRollup> BasicFromRaw = new Type<SimpleNumber, BasicRollup>() {
        @Override
        public BasicRollup compute(Points<SimpleNumber> input) throws IOException {
            return BasicRollup.buildRollupFromRawSamples(input);
        }
    };
    
    public static final Type<BasicRollup, BasicRollup> BasicFromBasic = new Type<BasicRollup, BasicRollup>() {
        @Override
        public BasicRollup compute(Points<BasicRollup> input) throws IOException {
            return BasicRollup.buildRollupFromRollups(input);
        }
    };
    
    public static final Type<SimpleNumber, HistogramRollup> HistogramFromRaw = new Type<SimpleNumber, HistogramRollup>() {
        @Override
        public HistogramRollup compute(Points<SimpleNumber> input) throws IOException {
            return HistogramRollup.buildRollupFromRawSamples(input);
        }
    };
    
    public static final Type<HistogramRollup, HistogramRollup> HistogramFromHistogram = new Type<HistogramRollup, HistogramRollup>() {
        @Override
        public HistogramRollup compute(Points<HistogramRollup> input) throws IOException {
            return HistogramRollup.buildRollupFromRollups(input);
        }
    };
    
    public static final Type<TimerRollup, TimerRollup> TimerFromTimer = new Type<TimerRollup, TimerRollup>() {
        @Override
        public TimerRollup compute(Points<TimerRollup> input) throws IOException {
            return TimerRollup.buildRollupFromTimerRollups(input);
        }
    };
    
    public static final Type<SimpleNumber, CounterRollup> CounterFromRaw = new Type<SimpleNumber, CounterRollup>() {
        @Override
        public CounterRollup compute(Points<SimpleNumber> input) throws IOException {
            return CounterRollup.buildRollupFromRawSamples(input);
        }
    };
    
    public static final Type<CounterRollup, CounterRollup> CounterFromCounter = new Type<CounterRollup, CounterRollup>() {
        @Override
        public CounterRollup compute(Points<CounterRollup> input) throws IOException {
            return CounterRollup.buildRollupFromCounterRollups(input);
        }
    };
    
    public static final Type<SimpleNumber, GaugeRollup> GaugeFromRaw = new Type<SimpleNumber, GaugeRollup>() {
        @Override
        public GaugeRollup compute(Points<SimpleNumber> input) throws IOException {
            return GaugeRollup.buildFromRawSamples(input);
        }
    };
    
    public static final Type<GaugeRollup, GaugeRollup> GaugeFromGauge = new Type<GaugeRollup, GaugeRollup>() {
        @Override
        public GaugeRollup compute(Points<GaugeRollup> input) throws IOException {
            return GaugeRollup.buildFromGaugeRollups(input);
        }
    };
    
    public static final Type<SetRollup, SetRollup> SetFromSet = new Type<SetRollup, SetRollup>() {
        @Override
        public SetRollup compute(Points<SetRollup> input) throws IOException {
            return SetRollup.buildRollupFromSetRollups(input);
        }
    };

    // Tells whether or not data exists
    public Boolean hasData();
    public RollupType getRollupType();
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/types/SimpleNumber.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

public class SimpleNumber implements Rollup {
    private final Number value;
    private final Type type;

    @Override
    public Boolean hasData() {
        return true; // value cannot be null, therefore this is always true.
    }

    public enum Type {
        INTEGER,
        LONG,
        DOUBLE
    }

    public SimpleNumber(Object value) {
        if (value == null)
            throw new NullPointerException("value cannot be null");
        if (value instanceof Integer) {
            this.type = Type.INTEGER;
            this.value = (Number)value;
        } else if (value instanceof Long) {
            this.type = Type.LONG;
            this.value = (Number)value;
        } else if (value instanceof Double) {
            this.type = Type.DOUBLE;
            this.value = (Number)value;
        } else if (value instanceof SimpleNumber) {
            this.type = ((SimpleNumber)value).type;
            this.value = ((SimpleNumber)value).value;
        } else {
            throw new IllegalArgumentException("Unexpected argument type " + value.getClass() + ", expected number.");
        }
    }

    public Number getValue() {
        return value;
    }

    public Type getDataType() {
        return type;
    }

    public String toString() {
        switch (type) {
            case INTEGER:
                return String.format("%d (int)", value.intValue());
            case LONG:
                return String.format("%d (long)", value.longValue());
            case DOUBLE:
                return String.format("%s (double)", value.toString());
            default:
                return super.toString();
        }
    }

    @Override
    public RollupType getRollupType() {
        return RollupType.NOT_A_ROLLUP;
    }

    @Override
    public int hashCode() {
        return value.hashCode();
    }

    @Override
    public boolean equals(Object obj) {
        if (obj == null || !(obj instanceof SimpleNumber))
            return false;
        SimpleNumber other = (SimpleNumber)obj;
        return other.value == this.value || other.value.equals(this.value);
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/types/Variance.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import com.rackspacecloud.blueflood.io.Constants;

import java.util.ArrayList;
import java.util.List;

public class Variance extends AbstractRollupStat {
    private long count = 0;

    // These are required for welford algorithm which works on raw samples
    private double mean;
    private double M2;
    private double populationVariance; // variance we are actually interested in

    // These are requied for rollup variance calculation
    private List<IBasicRollup> basicRollupList;

    private boolean isRollup;
    
    private boolean needsCompute = false;

    public Variance() {
        super();

        this.mean = 0;
        this.M2 = 0;
        this.populationVariance = 0;
        this.basicRollupList = new ArrayList<IBasicRollup>();
        this.isRollup = false;
    }

    @SuppressWarnings("unused") // used by Jackson
    public Variance(double value) {
        this.populationVariance = value;
        this.setDoubleValue(value);
    }

    @Override
    public boolean equals(Object otherObject) {
        compute();
        return super.equals(otherObject);
    }

    @Override
    public boolean isFloatingPoint() {
        return true;
    }

    @Override
    void handleFullResMetric(Object o) throws RuntimeException {
        // Welford algorithm (one pass)
        double input = getDoubleValue(o);
        double delta = input - mean;
        this.count++;
        this.mean = this.mean + (delta/this.count);
        this.M2 = this.M2 + delta * (input - mean);
        this.populationVariance = this.M2/(this.count);
        this.setDoubleValue(this.populationVariance);
    }

    @Override
    void handleRollupMetric(IBasicRollup basicRollup) throws RuntimeException {
        this.needsCompute = true;
        this.isRollup = true;
        basicRollupList.add(basicRollup); // we need all the rollup metrics before computing the final variance.
    }
    
    public String toString() {
        compute();
        return super.toString();
    }

    private synchronized void compute() {
        if (!needsCompute)
            return;
        needsCompute = false;
        double grandMean = 0.0;
        long totalSampleSize = 0L;

        if (this.isRollup) {
            double sum1 = 0;
            double sum2 = 0;

            // first pass to compute grand mean over all windows
            for (IBasicRollup basicRollup : basicRollupList) {
                AbstractRollupStat avg = basicRollup.getAverage();
                totalSampleSize += basicRollup.getCount();

                double avgVal;
                if (!avg.isFloatingPoint()) {
                    avgVal = (double) avg.toLong();
                } else {
                    avgVal = avg.toDouble();
                }

                grandMean += basicRollup.getCount() * avgVal;
            }

            if (totalSampleSize != 0) {
                grandMean = grandMean/totalSampleSize;
            } else {
                this.setDoubleValue(0.0); // no samples found
                return;
            }

            // With grand mean known, compute overall variance using
            // standard textbook variance estimation over windows with varying sample sizes.
            // The formula is exact and its precision depends on variance over a single window
            // which is computed using Welford. Except for numerical instability problems, Welford
            // is almost exact.
            for (IBasicRollup basicRollup : basicRollupList) {
                AbstractRollupStat var = basicRollup.getVariance();
                AbstractRollupStat avg = basicRollup.getAverage();
                sum1 += basicRollup.getCount() * var.toDouble();

                double avgVal;
                if (!avg.isFloatingPoint()) {
                    avgVal = (double) avg.toLong();
                } else {
                    avgVal = avg.toDouble();
                }

                sum2 += basicRollup.getCount() * Math.pow((avgVal - grandMean), 2);
            }

            this.setDoubleValue((sum1 + sum2) / totalSampleSize);
        }
    }

    @Override
    public double toDouble() {
        if (needsCompute)
            compute();
        return super.toDouble();
    }

    private double getDoubleValue(Object number) {
        double val = 0;
        if (number instanceof Integer) {
            val = ((Integer) number).doubleValue();
        } else if (number instanceof Long) {
            val = ((Long) number).doubleValue();
        } else if (number instanceof Double) {
            val = (Double)number;
        }

        return val;
    }

    @Override
    public long toLong() {
        throw new IllegalStateException("No long value for variances");    
    }

    @Override
    public byte getStatType() {
        return Constants.VARIANCE;
    }
}

File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/utils/AtomicCountingSet.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.utils;

import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.atomic.AtomicInteger;

public class AtomicCountingSet<T> {
    private ConcurrentMap<T, AtomicInteger> keyedCounter;

    public AtomicCountingSet() {
        this.keyedCounter = new ConcurrentHashMap<T, AtomicInteger>();
    }

    public void increment(T key) {
        AtomicInteger count = keyedCounter.get(key);

        if (count != null) {
            count.incrementAndGet();
        } else {
            count = keyedCounter.putIfAbsent(key, new AtomicInteger(1));
            if (count != null) {         // if we don't get back null, some other thread squeezed in
                count.incrementAndGet();
            }
        }
    }

    public void decrement(T key) {
        AtomicInteger count = keyedCounter.get(key);

        if (count != null) {
            count.decrementAndGet();
            keyedCounter.remove(key, 0);   // remove only if the value is zero
        }
    }

    public boolean contains(T key) {
         return keyedCounter.containsKey(key) && (keyedCounter.get(key).get() > 0);
    }

    public int getCount(T key) {
        AtomicInteger count = keyedCounter.get(key);
        return (count == null) ? 0 : count.get();
    }
    
    public Set<T> asSet() {
        return keyedCounter.keySet();
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/utils/MetricHelper.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.utils;

public class MetricHelper {

    public class Type {
        public final static char STRING = 's';
        public final static char INT32 = 'i';
        public final static char UINT32 = 'I';
        public final static char INT64 = 'l';
        public final static char UINT64 = 'L';
        public final static char DOUBLE = 'n';
        public final static char BOOLEAN = 'b';
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/utils/Metrics.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.utils;


import com.codahale.metrics.*;
import com.codahale.metrics.riemann.Riemann;
import com.codahale.metrics.riemann.RiemannReporter;
import com.codahale.metrics.graphite.Graphite;
import com.codahale.metrics.graphite.GraphiteReporter;
import com.codahale.metrics.jvm.BufferPoolMetricSet;
import com.codahale.metrics.jvm.GarbageCollectorMetricSet;
import com.codahale.metrics.jvm.MemoryUsageGaugeSet;
import com.codahale.metrics.jvm.ThreadStatesGaugeSet;
import com.codahale.metrics.log4j.InstrumentedAppender;
import com.rackspacecloud.blueflood.service.Configuration;
import com.rackspacecloud.blueflood.service.CoreConfig;
import org.apache.log4j.LogManager;

import javax.management.MBeanServer;
import java.io.IOException;
import java.lang.management.ManagementFactory;
import java.net.InetSocketAddress;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

public class Metrics {
    private static final MetricRegistry registry = new MetricRegistry();
    private static final GraphiteReporter reporter;
    private static final RiemannReporter reporter1;
    private static final JmxReporter reporter2;
    private static final String JVM_PREFIX = "jvm";

    static {
        Configuration config = Configuration.getInstance();

        // register jvm metrics
        MBeanServer mbs = ManagementFactory.getPlatformMBeanServer();
        if (!System.getProperty("java.version").split("\\.")[1].equals("6")) {
            // if not running 1.6
            registry.registerAll(new PrefixedMetricSet(new BufferPoolMetricSet(mbs), JVM_PREFIX, "buffer-pool"));
        }
        registry.registerAll(new PrefixedMetricSet(new GarbageCollectorMetricSet(), JVM_PREFIX, "gc"));
        registry.registerAll(new PrefixedMetricSet(new MemoryUsageGaugeSet(), JVM_PREFIX, "memory"));
        registry.registerAll(new PrefixedMetricSet(new ThreadStatesGaugeSet(), JVM_PREFIX, "thread-states"));

        // instrument log4j
        InstrumentedAppender appender = new InstrumentedAppender(registry);
        appender.activateOptions();
        LogManager.getRootLogger().addAppender(appender);

        if (!config.getStringProperty(CoreConfig.RIEMANN_HOST).equals("")) {
            RiemannReporter tmpreporter;
            try {
                Riemann riemann = new Riemann(config.getStringProperty(CoreConfig.RIEMANN_HOST), config.getIntegerProperty(CoreConfig.RIEMANN_PORT));

                RiemannReporter.Builder builder = RiemannReporter
                        .forRegistry(registry)
                        .convertDurationsTo(TimeUnit.MILLISECONDS)
                        .convertRatesTo(TimeUnit.SECONDS);
                if (!config.getStringProperty(CoreConfig.RIEMANN_SEPARATOR).isEmpty()) {
                    builder.useSeparator(config.getStringProperty(CoreConfig.RIEMANN_SEPARATOR));
                }
                if (!config.getStringProperty(CoreConfig.RIEMANN_TTL).isEmpty()) {
                    builder.withTtl(config.getFloatProperty(CoreConfig.RIEMANN_TTL));
                }
                if (!config.getStringProperty(CoreConfig.RIEMANN_LOCALHOST).isEmpty()) {
                    builder.localHost(config.getStringProperty(CoreConfig.RIEMANN_LOCALHOST));
                }
                if (!config.getStringProperty(CoreConfig.RIEMANN_PREFIX).isEmpty()) {
                    builder.prefixedWith(config.getStringProperty(CoreConfig.RIEMANN_PREFIX));
                }
                if (!config.getStringProperty(CoreConfig.RIEMANN_TAGS).isEmpty()) {
                    builder.tags(config.getListProperty(CoreConfig.RIEMANN_TAGS));
                }
                tmpreporter = builder.build(riemann);

                tmpreporter.start(30l, TimeUnit.SECONDS);
            } catch (IOException e) {
                tmpreporter = null;
            }
            reporter1 = tmpreporter;
        } else {
            reporter1 = null;
        }

        if (!config.getStringProperty(CoreConfig.GRAPHITE_HOST).equals("")) {
            Graphite graphite = new Graphite(new InetSocketAddress(config.getStringProperty(CoreConfig.GRAPHITE_HOST), config.getIntegerProperty(CoreConfig.GRAPHITE_PORT)));

            reporter = GraphiteReporter
                    .forRegistry(registry)
                    .convertDurationsTo(TimeUnit.MILLISECONDS)
                    .convertRatesTo(TimeUnit.SECONDS)
                    .prefixedWith(config.getStringProperty(CoreConfig.GRAPHITE_PREFIX))
                    .build(graphite);

            reporter.start(30l, TimeUnit.SECONDS);
        } else {
            reporter = null;
        }

        reporter2 = JmxReporter
                .forRegistry(registry)
                .convertDurationsTo(TimeUnit.MILLISECONDS)
                .convertRatesTo(TimeUnit.SECONDS)
                .build();
        reporter2.start();
    }

    static class PrefixedMetricSet implements MetricSet {
        private final Map<String, Metric> metricMap;

        PrefixedMetricSet(final MetricSet metricSet, final String prefix1, final String prefix2) {
            metricMap = Collections.unmodifiableMap(new HashMap<String, Metric>(){{
                for (Map.Entry<String, Metric> stringMetricEntry : metricSet.getMetrics().entrySet()) {
                    put(MetricRegistry.name(prefix1, prefix2, stringMetricEntry.getKey()), stringMetricEntry.getValue());
                }
            }});
        }

        @Override
        public Map<String, Metric> getMetrics() {
            return metricMap;
        }
    }

    public static MetricRegistry getRegistry() {
        return registry;
    }

    public static Meter meter(Class kls, String... names) {
        return getRegistry().meter(MetricRegistry.name(kls, names));
    }

    public static Timer timer(Class kls, String... names) {
        return getRegistry().timer(MetricRegistry.name(kls, names));
    }

    public static Histogram histogram(Class kls, String... names) {
        return getRegistry().histogram(MetricRegistry.name(kls, names));
    }

    public static Counter counter(Class kls, String... names) {
        return getRegistry().counter(MetricRegistry.name(kls, names));
    }
}


File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/utils/RestartGauge.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.utils;

import com.codahale.metrics.Gauge;
import com.codahale.metrics.MetricRegistry;

public class RestartGauge implements Gauge<Integer> {
    boolean sentVal = false;

    @Override
    public Integer getValue() {
        // Sends a value of 1 for the first flush after service restart and Gauge instantiation, then zero.
        if (!sentVal){
            sentVal = true;
            return 1;
        }
        return 0;
    }

    public RestartGauge(MetricRegistry registry, Class klass) {
        registry.register(MetricRegistry.name(klass, "Restart"), this);
    }
}

File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/utils/TimeValue.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.utils;

import java.util.concurrent.TimeUnit;

public class TimeValue {
    private final TimeUnit unit;
    private final long value;

    public TimeValue(long value, TimeUnit unit) {
        this.value = value;
        this.unit = unit;
    }

    public long getValue() {
        return this.value;
    }

    public TimeUnit getUnit() {
        return this.unit;
    }

    public long toDays() {
        return this.unit.toDays(this.value);
    }

    public long toHours() {
        return this.unit.toHours(this.value);
    }

    public long toMinutes() {
        return this.unit.toMinutes(this.value);
    }

    public long toSeconds() {
        return this.unit.toSeconds(this.value);
    }

    public long toMillis() {
        return this.unit.toMillis(this.value);
    }

    public long toMicros() {
        return this.unit.toMicros(this.value);
    }

    public String toString() {
        return String.format("%s %s", String.valueOf(this.getValue()), unit.name());
    }

    public boolean equals(TimeValue other) {
        if (other == null) return false;

        return other.getValue() == this.getValue() && other.getUnit().equals(this.getUnit());
    }
}

File: blueflood-core/src/main/java/com/rackspacecloud/blueflood/utils/Util.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.utils;

import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import com.rackspacecloud.blueflood.io.Constants;
import com.rackspacecloud.blueflood.service.Configuration;
import com.rackspacecloud.blueflood.service.CoreConfig;
import org.apache.commons.codec.digest.DigestUtils;

import java.text.DecimalFormat;
import java.text.Format;
import java.util.ArrayList;
import java.util.Collection;
import java.util.concurrent.TimeUnit;

public class Util {
    public static final String DEFAULT_DIMENSION = "default";
    public static final Format DECIMAL_FORMAT = new DecimalFormat("0.00");
    private static final Cache<String, Integer> shardCache = CacheBuilder.newBuilder().expireAfterAccess(10,
            TimeUnit.MINUTES).concurrencyLevel(30).build();

    public static Integer getShard(String s) {
        Integer shard = shardCache.getIfPresent(s);
        if (shard == null) {
            shard = computeShard(s);
            shardCache.put(s, shard);
        }
        return shard;
    }

    public static int computeShard(String s) {
        return (int)Long.parseLong(DigestUtils.md5Hex(s).substring(30), 16) % Constants.NUMBER_OF_SHARDS;
    }
    
    public static Collection<Integer> parseShards(String s) {
        ArrayList<Integer> list = new ArrayList<Integer>();
        if ("ALL".equalsIgnoreCase(s)) {
            for (int i = 0; i < Constants.NUMBER_OF_SHARDS; i++)
                list.add(i);
        } else if ("NONE".equalsIgnoreCase(s)) {
            return list;
        } else {
            for (String part : s.split(",", -1)) {
                int i = Integer.parseInt(part.trim());
                if (i >= Constants.NUMBER_OF_SHARDS || i < 0)
                    throw new NumberFormatException("Invalid shard identifier: " + part.trim());
                list.add(i);
            }
        }
        return list;
    }

    public static String getDimensionFromKey(String persistedMetric) {
       return persistedMetric.split("\\.", -1)[0];
    }

    public static String getMetricFromKey(String persistedMetric) {
        return persistedMetric.split("\\.", 2)[1];
    }
    
    public static double safeDiv(double numerator, double denominator) {
        if (denominator == 0)
            return 0d;
        else
            return numerator / denominator;
    }

    public static String ElasticIOPath = "com.rackspacecloud.blueflood.io.ElasticIO".intern();

    public static String UNKNOWN = "unknown".intern();

    public static boolean shouldUseESForUnits() {
        return Configuration.getInstance().getBooleanProperty(CoreConfig.USE_ES_FOR_UNITS) &&
                Configuration.getInstance().getListProperty(CoreConfig.DISCOVERY_MODULES).contains(ElasticIOPath);
    }
}


File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/cache/ConfigTtlProviderTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.cache;

import com.rackspacecloud.blueflood.exceptions.ConfigException;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.service.Configuration;
import com.rackspacecloud.blueflood.service.TtlConfig;
import com.rackspacecloud.blueflood.types.RollupType;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.junit.Assert;
import org.junit.Test;

import java.util.concurrent.TimeUnit;

public class ConfigTtlProviderTest {
    @Test
    public void testConfigTtl() throws Exception {
        final ConfigTtlProvider ttlProvider = ConfigTtlProvider.getInstance();
        final Configuration config = Configuration.getInstance();

        Assert.assertTrue(new TimeValue(config.getIntegerProperty(TtlConfig.RAW_METRICS_TTL), TimeUnit.DAYS).equals(
                ttlProvider.getTTL("acFoo", Granularity.FULL, RollupType.BF_BASIC)));

        // Ask for an invalid combination of granularity and rollup type
        try {
            Assert.assertNull(ttlProvider.getTTL("acBar", Granularity.FULL, RollupType.BF_HISTOGRAMS));
        } catch (ConfigException ex) {
            // pass
        } catch (Exception ex) {
            Assert.fail("Should have thrown a ConfigException.");
        }
    }

    @Test
    public void testConfigTtlForStrings() throws Exception {
        final ConfigTtlProvider ttlProvider = ConfigTtlProvider.getInstance();
        final Configuration config = Configuration.getInstance();

        Assert.assertTrue(new TimeValue(config.getIntegerProperty(TtlConfig.STRING_METRICS_TTL), TimeUnit.DAYS).equals(
                ttlProvider.getTTLForStrings("acFoo")));
    }
}

File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/eventemitter/RollupEventEmitterTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.eventemitter;

import com.rackspacecloud.blueflood.concurrent.ThreadPoolBuilder;
import junit.framework.Assert;
import org.junit.Test;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.*;

public class RollupEventEmitterTest {
    String testEventName = "test";
    List<RollupEvent> store = Collections.synchronizedList(new ArrayList<RollupEvent>());
    Emitter<RollupEvent> emitter = new Emitter<RollupEvent>();

    @Test
    public void testEmitter() throws Exception {
        EventListener elistener = new EventListener();
        //Test subscription
        emitter.on(testEventName, elistener);
        Assert.assertTrue(emitter.listeners(testEventName).contains(elistener));
        //Test concurrent emission
        ThreadPoolExecutor executors = new ThreadPoolBuilder()
                .withCorePoolSize(2)
                .withMaxPoolSize(3)
                .build();
        final RollupEvent obj1 = new RollupEvent(null, null, "payload1", "gran", 0);
        final RollupEvent obj2 = new RollupEvent(null, null, "payload2", "gran", 0);
        final CountDownLatch startLatch = new CountDownLatch(1);
        Future<Object> f1 = executors.submit(new Callable<Object>() {
            @Override
            public Object call() throws Exception {
                startLatch.await();
                emitter.emit(testEventName, obj1);
                return null;
            }
        });
        Future<Object> f2 = executors.submit(new Callable<Object>() {
            @Override
            public Object call() throws Exception {
                startLatch.await();
                emitter.emit(testEventName, obj2);
                return null;
            }
        });
        Thread.sleep(1000);
        //Assert that store is empty before testing emission
        Assert.assertTrue(store.isEmpty());
        startLatch.countDown();
        f1.get();
        f2.get();
        Assert.assertEquals(store.size(),2);
        Assert.assertTrue(store.contains(obj1));
        Assert.assertTrue(store.contains(obj2));
        //Test unsubscription
        emitter.off(testEventName, elistener);
        Assert.assertFalse(emitter.listeners(testEventName).contains(elistener));
        //Clear the store and check if it is not getting filled again
        store.clear();
        emitter.emit(testEventName, new RollupEvent(null, null, "payload3", "gran", 0));
        Assert.assertTrue(store.isEmpty());
    }

    @Test
    public void testOnce() {
        EventListener eventListener = new EventListener();
        //Test once
        emitter.once(testEventName, eventListener);
        emitter.emit(testEventName, new RollupEvent(null, null, "payload1", "gran", 0));
        Assert.assertEquals(store.size(), 1);
        store.clear();
        emitter.emit(testEventName, new RollupEvent(null, null, "payload1", "gran", 0));
        Assert.assertEquals(store.size(), 0);
    }

    private class EventListener implements Emitter.Listener<RollupEvent> {
        @Override
        public void call(RollupEvent... rollupEventObjects) {
            store.addAll(Arrays.asList(rollupEventObjects));
        }
    }
}


File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/io/serializers/CounterRollupSerializationTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io.serializers;

import com.rackspacecloud.blueflood.io.Constants;
import com.rackspacecloud.blueflood.io.serializers.NumericSerializer;
import com.rackspacecloud.blueflood.types.CounterRollup;
import junit.framework.Assert;
import org.apache.commons.codec.binary.Base64;
import org.junit.Test;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.ByteBuffer;

public class CounterRollupSerializationTest {

    @Test
    public void testCounterV1RoundTrip() throws IOException {
        CounterRollup c0 = new CounterRollup().withCount(7442245).withSampleCount(1);
        CounterRollup c1 = new CounterRollup().withCount(34454722343L).withSampleCount(10);
        
        if (System.getProperty("GENERATE_COUNTER_SERIALIZATION") != null) {
            OutputStream os = new FileOutputStream("src/test/resources/serializations/counter_version_" + Constants.VERSION_1_COUNTER_ROLLUP + ".bin", false);
            os.write(Base64.encodeBase64(new NumericSerializer.CounterRollupSerializer().toByteBuffer(c0).array()));
            os.write("\n".getBytes());
            os.write(Base64.encodeBase64(new NumericSerializer.CounterRollupSerializer().toByteBuffer(c1).array()));
            os.write("\n".getBytes());
            os.close();
        }
        
        Assert.assertTrue(new File("src/test/resources/serializations").exists());
                
        int count = 0;
        int version = 0;
        final int maxVersion = Constants.VERSION_1_COUNTER_ROLLUP;
        while (version <= maxVersion) {
            BufferedReader reader = new BufferedReader(new FileReader("src/test/resources/serializations/counter_version_" + version + ".bin"));
            
            ByteBuffer bb = ByteBuffer.wrap(Base64.decodeBase64(reader.readLine().getBytes()));
            CounterRollup cc0 = NumericSerializer.serializerFor(CounterRollup.class).fromByteBuffer(bb);
            Assert.assertEquals(c0, cc0);
            
            bb = ByteBuffer.wrap(Base64.decodeBase64(reader.readLine().getBytes()));
            CounterRollup cc1 = NumericSerializer.serializerFor(CounterRollup.class).fromByteBuffer(bb);
            Assert.assertEquals(c1, cc1);
            
            Assert.assertFalse(cc0.equals(cc1));
            version++;
            count++;
        }
        
        Assert.assertTrue(count > 0);
    }
}


File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/io/serializers/HistogramSerializationTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io.serializers;

import com.bigml.histogram.Bin;
import com.bigml.histogram.SimpleTarget;
import com.rackspacecloud.blueflood.io.Constants;
import com.rackspacecloud.blueflood.types.*;
import org.apache.commons.codec.binary.Base64;
import org.junit.Assert;
import org.junit.Test;

import java.io.*;
import java.nio.ByteBuffer;
import java.util.Collection;
import java.util.Map;
import java.util.TreeMap;

public class HistogramSerializationTest {
    private static HistogramRollup histogramRollup;

    static {
        Points<SimpleNumber> points = new Points<SimpleNumber>();
        long startTime = 12345678L;
        for (double val : TestData.DOUBLE_SRC) {
            points.add(new Points.Point<SimpleNumber>(startTime++, new SimpleNumber(val)));
        }

        try {
             histogramRollup = HistogramRollup.buildRollupFromRawSamples(points);
        } catch (Exception ex) {
            Assert.fail("Test data generation failed");
        }
    }

    @Test
    public void testSerializationDeserializationVersion1() throws Exception {
        if (System.getProperty("GENERATE_HIST_SERIALIZATION") != null) {
            OutputStream os = new FileOutputStream("src/test/resources/serializations/histogram_version_" +
                    Constants.VERSION_1_HISTOGRAM + ".bin", false);

            os.write(Base64.encodeBase64(HistogramSerializer.get().toByteBuffer(histogramRollup).array()));
            os.write("\n".getBytes());
            os.close();
        }

        Assert.assertTrue(new File("src/test/resources/serializations").exists());

        // ensure we can read historical serializations.
        int version = 0;
        int maxVersion = Constants.VERSION_1_HISTOGRAM;
        while (version <= maxVersion) {
            BufferedReader reader = new BufferedReader(new FileReader("src/test/resources/serializations/histogram_version_" + version + ".bin"));
            ByteBuffer bb = ByteBuffer.wrap(Base64.decodeBase64(reader.readLine().getBytes()));
            HistogramRollup histogramRollupDes = HistogramSerializer.get().fromByteBuffer(bb);
            Assert.assertTrue(areHistogramsEqual(histogramRollup, histogramRollupDes));
            version++;
        }
    }

    @Test
    public void testBadSerializationVersion() {
        byte[] buf = new byte[] {99, 99};  // hopefully we won't have 99 different serialization versions.
        try {
            HistogramSerializer.get().fromByteBuffer(ByteBuffer.wrap(buf));
            Assert.fail(String.format("Should have errored out. Such a version doesn't exist for histogram."));
        } catch (RuntimeException ex) {
            Assert.assertTrue(ex.getCause().getMessage().startsWith("Unexpected serialization version"));
        }
    }

    private boolean areHistogramsEqual(HistogramRollup first, HistogramRollup second) {
        final TreeMap<Double, Double> firstBinsAsOrderedMap = getNonZeroBinsAsMap(first);
        final TreeMap<Double, Double> secondBinsAsOrderedMap = getNonZeroBinsAsMap(second);

        if (firstBinsAsOrderedMap.size() != secondBinsAsOrderedMap.size()) {
            return false;
        }

        for (Map.Entry<Double, Double> firstBin: firstBinsAsOrderedMap.entrySet()) {
            Double val = secondBinsAsOrderedMap.get(firstBin.getKey());
            if (val == null || !firstBin.getValue().equals(val)) {
                return false;
            }
        }

        return true;
    }

    private TreeMap<Double, Double> getNonZeroBinsAsMap(HistogramRollup histogramRollup) {
        Collection<Bin<SimpleTarget>> bins = histogramRollup.getBins();

        final TreeMap<Double, Double> binsMap = new TreeMap<Double, Double>();
        for (Bin<SimpleTarget> bin : bins) {
            if (bin.getCount() > 0) {
                binsMap.put(bin.getMean(), bin.getCount());
            }
        }

        return binsMap;
    }
}


File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/io/serializers/SerializationTest.java
    /*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io.serializers;

import com.netflix.astyanax.model.ColumnFamily;
import com.netflix.astyanax.serializers.AbstractSerializer;
import com.rackspacecloud.blueflood.exceptions.SerializationException;
import com.rackspacecloud.blueflood.exceptions.UnexpectedStringSerializationException;
import com.rackspacecloud.blueflood.io.Constants;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.types.BasicRollup;
import com.rackspacecloud.blueflood.types.CounterRollup;
import com.rackspacecloud.blueflood.types.GaugeRollup;
import com.rackspacecloud.blueflood.types.Locator;
import com.rackspacecloud.blueflood.types.Points;
import com.rackspacecloud.blueflood.types.SetRollup;
import com.rackspacecloud.blueflood.types.SimpleNumber;
import com.rackspacecloud.blueflood.types.TimerRollup;
import com.rackspacecloud.blueflood.utils.MetricHelper;
import com.google.common.collect.Sets;
import org.apache.commons.codec.binary.Base64;
import org.junit.Assert;
import org.junit.Test;

import java.io.*;
import java.lang.reflect.Field;
import java.nio.ByteBuffer;
import java.util.HashSet;
import java.util.Set;

public class SerializationTest {
    
    private final static Object[] toSerializeFull = new Object[] {
        32342341,
        3423523122452312341L,
        6345232.6234262d,
        "This is a test string."
    };
    
    private static final Class[] SERIALIZABLE_TYPES = new Class[] {
            BasicRollup.class,
            SimpleNumber.class,
            Object.class,
            Integer.class,
            Long.class,
            TimerRollup.class,
            //HistogramRollup.class, // todo: not implemented yet.
            CounterRollup.class,
            SetRollup.class,
            GaugeRollup.class
    };
    
    private final static BasicRollup[] TO_SERIALIZE_BASIC_ROLLUP = new BasicRollup[4];

    static {
        // double
        for (int i = 0; i < 2; i++) {
            Points<SimpleNumber> input = new Points<SimpleNumber>();
            int timeOffset = 0;
            for (double val = 0.0; val < 10.0; val++) {
                input.add(new Points.Point<SimpleNumber>(123456789L + timeOffset++, new SimpleNumber(val * (i+1))));
            }

            try {
                TO_SERIALIZE_BASIC_ROLLUP[i] = BasicRollup.buildRollupFromRawSamples(input);
            } catch (IOException ex) {
                Assert.fail("Test data generation failed");
            }
        }

        // long
        for (int i = 0; i < 2; i++) {
            Points<SimpleNumber> input = new Points<SimpleNumber>();
            int timeOffset = 0;
            for (long val = 0; val < 10; val++) {
                input.add(new Points.Point<SimpleNumber>(123456789L + timeOffset++, new SimpleNumber(val * (i+1))));
            }
            try {
                TO_SERIALIZE_BASIC_ROLLUP[2 + i] = BasicRollup.buildRollupFromRawSamples(input);
            } catch (Exception e) {
                Assert.fail("Test data generation failed");
            }
        }
    }
    
    @Test
    public void testBadSerializationVersion() {
        byte[] buf = new byte[] {99, 99};  // hopefully we won't have 99 different serialization versions.
        for (Class type : SERIALIZABLE_TYPES) {
            try {
                Object o = NumericSerializer.serializerFor(type).fromByteBuffer(ByteBuffer.wrap(buf));
                Assert.fail(String.format("Should have errored out %s", type.getName()));
            } catch (RuntimeException ex) {
                Assert.assertTrue(ex.getCause().getMessage().startsWith("Unexpected serialization version"));
            }
        }
    }
    
    @Test(expected = SerializationException.class)
    public void testVersion2FullDeserializeBadType() throws Throwable {
        byte[] buf = new byte[] { 0, 2 };
        try {
            NumericSerializer.serializerFor(Object.class).fromByteBuffer(ByteBuffer.wrap(buf));
        } catch (RuntimeException e) {
            throw e.getCause();
        }
    }

    @Test
    public void testFullResSerializationAndDeserialization() throws IOException {
        // if the GENERATE_SERIALIZATION flag is set, save everything.
        if (System.getProperty("GENERATE_FULL_RES_SERIALIZATION") != null) {
            OutputStream os = new FileOutputStream("src/test/resources/serializations/full_version_" + Constants.VERSION_1_FULL_RES + ".bin", false);
            for (Object o : toSerializeFull) {
                // encode as base64 to make reading the file easier.
                os.write(Base64.encodeBase64(NumericSerializer.serializerFor(Object.class).toByteBuffer(o).array()));
                os.write("\n".getBytes());
            }
            os.close();
        }
        
        Assert.assertTrue(new File("src/test/resources/serializations").exists());
        
        // ensure we can read historical serializations.
        int version = 0; // versions before this are illegal.
        int maxVersion = Constants.VERSION_1_FULL_RES;
        while (version <= maxVersion) {
            BufferedReader reader = new BufferedReader(new FileReader("src/test/resources/serializations/full_version_" + version + ".bin"));
            for (int i = 0; i < toSerializeFull.length; i++)
                try {
                    // we used to allow deserializing strings, but we don't anymore.
                    // catch that error and assert it happens only when expected.
                    ByteBuffer byteBuffer = ByteBuffer.wrap(Base64.decodeBase64(reader.readLine().getBytes()));
                    Assert.assertEquals(
                            String.format("broken at version %d", version),
                            NumericSerializer.serializerFor(Object.class).fromByteBuffer(byteBuffer),
                            toSerializeFull[i]);
                } catch (RuntimeException ex) {
                    Assert.assertEquals(ex.getCause().getClass(), UnexpectedStringSerializationException.class);
                    Assert.assertEquals(3, i);
                    Assert.assertTrue(toSerializeFull[i] instanceof String);
                }
            version += 1;
        }
        
        // ensure that current round-tripping isn't broken.
        for (Object o : toSerializeFull) {
            // skip the string (we used to allow this).
            if (o instanceof String) continue; // we don't serialize those any more.
            ByteBuffer serialized = NumericSerializer.serializerFor(Object.class).toByteBuffer(o);
            Assert.assertEquals(o, NumericSerializer.serializerFor(Object.class).fromByteBuffer(serialized));
        }
    }

    @Test
    public void testRollupSerializationAndDeserialization() throws IOException {
        // works the same way as testFullResSerializationAndDeserialization
        
        if (System.getProperty("GENERATE_ROLLUP_SERIALIZATION") != null) {
            OutputStream os = new FileOutputStream("src/test/resources/serializations/rollup_version_" + Constants.VERSION_1_ROLLUP + ".bin", false);
            for (BasicRollup basicRollup : TO_SERIALIZE_BASIC_ROLLUP) {
                ByteBuffer bb = NumericSerializer.serializerFor(BasicRollup.class).toByteBuffer(basicRollup);
                os.write(Base64.encodeBase64(bb.array()));
                os.write("\n".getBytes());
            }
            os.close();
        }
        
        Assert.assertTrue(new File("src/test/resources/serializations").exists());
        
        // ensure we can read historical serializations.
        int version = 0;
        int maxVersion = Constants.VERSION_1_ROLLUP;
        while (version <= maxVersion) {
            BufferedReader reader = new BufferedReader(new FileReader("src/test/resources/serializations/rollup_version_" + version + ".bin"));
            for (int i = 0; i < TO_SERIALIZE_BASIC_ROLLUP.length; i++) {
                for (Granularity g : Granularity.rollupGranularities()) {
                    ByteBuffer bb = ByteBuffer.wrap(Base64.decodeBase64(reader.readLine().getBytes()));
                    BasicRollup basicRollup = (BasicRollup) NumericSerializer.serializerFor(BasicRollup.class).fromByteBuffer(bb);
                    Assert.assertTrue(String.format("Deserialization for rollup broken at %d", version),
                            TO_SERIALIZE_BASIC_ROLLUP[i].equals(basicRollup));
                }
                version += 1;
            }
        }
        
        // current round tripping.
        for (BasicRollup basicRollup : TO_SERIALIZE_BASIC_ROLLUP) {
            for (Granularity g : Granularity.rollupGranularities()) {
                ByteBuffer bb = NumericSerializer.serializerFor(BasicRollup.class).toByteBuffer(basicRollup);
                Assert.assertTrue(basicRollup.equals(NumericSerializer.serializerFor(BasicRollup.class).fromByteBuffer(bb)));
            }
        }
    }

    @Test
    public void testFullResRoundTrip() throws IOException {
        // tests serialization of all types that should be handled, including granularity variations.
        Object[] inputs = {
            7565,
            323234234235223321L,
            213432.53323d,
            42332.0234375f,
            TO_SERIALIZE_BASIC_ROLLUP[0],
            TO_SERIALIZE_BASIC_ROLLUP[1],
            TO_SERIALIZE_BASIC_ROLLUP[2],
            TO_SERIALIZE_BASIC_ROLLUP[3]
        };
        
        Object[] expected = {
            7565,
            323234234235223321L,
            213432.53323d,
            42332.0234375d, // notice that serialization converts to a double.
            TO_SERIALIZE_BASIC_ROLLUP[0],
            TO_SERIALIZE_BASIC_ROLLUP[1],
            TO_SERIALIZE_BASIC_ROLLUP[2],
            TO_SERIALIZE_BASIC_ROLLUP[3]
        };
        
        for (Class type : SERIALIZABLE_TYPES) {
            for (int i = 0; i < inputs.length; i++) {
                try {
                    Object dst = NumericSerializer.serializerFor(type).fromByteBuffer(NumericSerializer.serializerFor(type).toByteBuffer(inputs[i]));
                    Assert.assertEquals(String.format("busted at %s %d", type.getName(), i), expected[i], dst);
                } catch (ClassCastException ex) {
                    // these are expected because of the various types.
                    // todo: this test could be made better by
                    //       1) having one iteration to verify that we can serialize for matched types.
                    //       2) having various other tests that verify that serialization breaks in expected ways when
                    //          types are mismatched
                    continue;
                } catch (RuntimeException ex) {
                    if (ex.getCause() == null) throw ex;
                    Assert.assertTrue(ex.getCause().getClass().getName(), ex.getCause() instanceof SerializationException);
                    if (inputs[i] instanceof BasicRollup)
                        Assert.assertFalse(type.equals(BasicRollup.class));
                    else
                        Assert.assertTrue(type.equals(BasicRollup.class));
                } catch (Throwable unexpected) {
                    unexpected.printStackTrace();
                    Assert.fail(String.format("Unexpected error at %s %d", type.getName(), i));
                }
            }
        }
    }

    @Test
    public void testSerializerOverAndOver() throws IOException {
        byte[] buf;
        int expectedBufferSize = 0;
        for (int i = 0; i < 10000000; i++) {
            buf = NumericSerializer.serializerFor(Long.class).toByteBuffer(Long.MAX_VALUE).array();
            Assert.assertFalse(buf.length == 0);
            if (expectedBufferSize == 0)
                expectedBufferSize = buf.length;
            else
              Assert.assertEquals(buf.length, expectedBufferSize);
        }
    }
    
    @Test(expected = SerializationException.class)
    public void testSerializeStringFails() throws Throwable {
        try {
            NumericSerializer.serializerFor(String.class).toByteBuffer("words");
        } catch (RuntimeException e) {
            throw e.getCause();
        }
    }
    
    @Test(expected = UnexpectedStringSerializationException.class)
    public void testDeserializeStringDoesNotFail() throws Throwable {
        // this is what a string looked like previously.
        try {
            String serialized = "AHMWVGhpcyBpcyBhIHRlc3Qgc3RyaW5nLg==";
            ByteBuffer bb = ByteBuffer.wrap(Base64.decodeBase64(serialized.getBytes()));
            NumericSerializer.serializerFor(SimpleNumber.class).fromByteBuffer(bb);
        } catch (RuntimeException ex) {
            throw ex.getCause();
        }
    }
    
    // this was allowed for a brief while. it would represent a regression now.
    @Test(expected = SerializationException.class)
    public void testCannotRoundtripStringWithNullType() throws Throwable {
        try {
            String expected = "this is a string";
            ColumnFamily<Locator, Long> CF = null;
            ByteBuffer bb = NumericSerializer.serializerFor((Class) null).toByteBuffer(expected);
            String actual = (String)NumericSerializer.serializerFor((Class) null).fromByteBuffer(bb);
            Assert.assertEquals(expected, actual);
        } catch (RuntimeException ex) {
            throw ex.getCause();
        }
    }
    
    @Test(expected = SerializationException.class)
    public void testCannotRoundtripBytesWillNullType() throws Throwable {
        try {
            byte[] expected = new byte[] {1,2,3,4,5};
            ColumnFamily<Locator, Long> CF = null;
            ByteBuffer bb = NumericSerializer.serializerFor((Class) null).toByteBuffer(expected);
            byte[] actual = (byte[])NumericSerializer.serializerFor((Class) null).fromByteBuffer(bb);
            Assert.assertArrayEquals(expected, actual);
        } catch (RuntimeException ex) {
            throw ex.getCause();
        }
    }
    
    @Test(expected = SerializationException.class)
    public void testCannotRoundtripBytes() throws Throwable {
        try {
            byte[] expected = new byte[] {1,2,3,4,5};
            AbstractSerializer ser = NumericSerializer.serializerFor(SimpleNumber.class);
            byte[] actual = (byte[])ser.fromByteBuffer(ser.toByteBuffer(expected));
            Assert.assertArrayEquals(expected, actual);
        } catch (RuntimeException ex) {
            throw ex.getCause();
        }
    }
  
    @Test
    public void testForConstantCollisions() throws Exception {
        // make sure we're not sharing any constants with MetricHelper.DataType
        Set<Character> metricHelperTypes = new HashSet<Character>();
        for (Field f : MetricHelper.Type.class.getFields())
            if (f.getType().equals(char.class))
                metricHelperTypes.add(((Character)f.get(MetricHelper.Type.class)));
        Assert.assertEquals(7, metricHelperTypes.size());
        
        Set<Character> serializerTypes = new HashSet<Character>();
        for (Field f : NumericSerializer.Type.class.getDeclaredFields())
            if (f.getType().equals(byte.class))
                serializerTypes.add((char)((Byte)f.get(MetricHelper.Type.class)).byteValue());
        Assert.assertEquals(7, serializerTypes.size());

        // intersection should be zero.
        Assert.assertEquals(0, Sets.intersection(metricHelperTypes, serializerTypes).size());
        
        // so that I know Sets.intersection is not making a fool of me.
        serializerTypes.add(metricHelperTypes.iterator().next());
        Assert.assertEquals(1, Sets.intersection(metricHelperTypes, serializerTypes).size());
    }
  
    @Test
    public void testRollupSerializationLargeCounts() throws IOException {
        Points<BasicRollup> rollupGroup = new Points<BasicRollup>();
        BasicRollup startingRollup = new BasicRollup();
        startingRollup.setCount(500);
        rollupGroup.add(new Points.Point<BasicRollup>(123456789L, startingRollup));
        
        for (int rollupCount = 0; rollupCount < 500; rollupCount++) {
            Points<SimpleNumber> input = new Points<SimpleNumber>();
            for (int fullResCount = 0; fullResCount < 500; fullResCount++) {
                input.add(new Points.Point<SimpleNumber>(123456789L + fullResCount, new SimpleNumber(fullResCount + fullResCount * 3)));
            }
            BasicRollup basicRollup = BasicRollup.buildRollupFromRawSamples(input);
            Points<BasicRollup> rollups = new Points<BasicRollup>();
            rollups.add(new Points.Point<BasicRollup>(123456789L , basicRollup));
            BasicRollup groupRollup = BasicRollup.buildRollupFromRollups(rollups);
            rollupGroup.add(new Points.Point<BasicRollup>(123456789L, groupRollup));
        }
        
        BasicRollup r = BasicRollup.buildRollupFromRollups(rollupGroup);

        // serialization was broken.
        ByteBuffer bb = NumericSerializer.serializerFor(BasicRollup.class).toByteBuffer(r);
        Assert.assertEquals(r, NumericSerializer.serializerFor(BasicRollup.class).fromByteBuffer(bb));
    }

    @Test
    public void testLocatorDeserializer() throws UnsupportedEncodingException {
        String locatorString = "ac76PeGPSR.entZ4MYd1W.chJ0fvB5Ao.mzord.truncated";
        ByteBuffer bb = ByteBuffer.wrap(locatorString.getBytes("UTF-8"));
        Locator locatorFromString = Locator.createLocatorFromDbKey(locatorString);
        Locator locatorDeserialized = LocatorSerializer.get().fromByteBuffer(bb);
        Assert.assertEquals("Locator did not match after deserialization",
                locatorFromString.toString(), locatorDeserialized.toString());
    }
}

File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/io/serializers/SlotStateSerializerTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io.serializers;

import com.netflix.astyanax.serializers.StringSerializer;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.service.SlotState;
import com.rackspacecloud.blueflood.service.UpdateStamp;
import org.junit.Assert;
import org.junit.Test;

import java.nio.ByteBuffer;

public class SlotStateSerializerTest {
    @Test
    public void testGranularityFromStateCol() {
        Granularity myGranularity = SlotStateSerializer.granularityFromStateCol("metrics_full,1,okay");
        Assert.assertNotNull(myGranularity);
        Assert.assertEquals(myGranularity, Granularity.FULL);

        myGranularity = SlotStateSerializer.granularityFromStateCol("FULL");
        Assert.assertNull(myGranularity);
    }

    @Test
    public void testToFromByteBuffer() {
        ByteBuffer origBuff = StringSerializer.get().toByteBuffer("metrics_full,1,X");
        Assert.assertNotNull(origBuff);

        SlotState state = SlotStateSerializer.get().fromByteBuffer(origBuff.duplicate());
        Assert.assertEquals(state.getGranularity(), Granularity.FULL);
        Assert.assertEquals(state.getSlot(), 1);
        Assert.assertEquals(state.getState(), UpdateStamp.State.Rolled);

        ByteBuffer newBuff = SlotStateSerializer.get().toByteBuffer(state);
        Assert.assertEquals(origBuff, newBuff);
    }

    @Test
    public void testSlotFromStateCol() {
        Assert.assertEquals(1, SlotStateSerializer.slotFromStateCol("metrics_full,1,okay"));
    }

    @Test
    public void testStateFromStateCol() {
        Assert.assertEquals("okay", SlotStateSerializer.stateCodeFromStateCol("metrics_full,1,okay"));
    }

    @Test
    public void testStateFromStateCode() {
        Assert.assertEquals(UpdateStamp.State.Active, SlotStateSerializer.stateFromCode("foo"));
        Assert.assertEquals(UpdateStamp.State.Active, SlotStateSerializer.stateFromCode("A"));
        Assert.assertEquals(UpdateStamp.State.Rolled, SlotStateSerializer.stateFromCode("X"));
    }
}


File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/io/serializers/StringMetadataSerializerTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io.serializers;

import org.junit.Test;

import java.io.IOException;
import java.nio.ByteBuffer;

import static org.junit.Assert.assertEquals;

public class StringMetadataSerializerTest {

    @Test
    public void testString() throws IOException {
        String[] values = {
            "abcdefg",
            "\u1234 \u0086 \uabcd \u5432",
            "ĆĐÈ¿ΔΞ€"
        };
        testRoundTrip(values);
    }

    private void testRoundTrip(String... strings) throws IOException {
        for (String str : strings) {
            byte[] buf = StringMetadataSerializer.get().toByteBuffer(str).array();
            ByteBuffer bb = ByteBuffer.wrap(buf);
                assertEquals(str, StringMetadataSerializer.get().fromByteBuffer(bb));
        }
    }
}

File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/io/serializers/TimerSerializationTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io.serializers;

import com.rackspacecloud.blueflood.io.Constants;
import com.rackspacecloud.blueflood.types.TimerRollup;
import org.apache.commons.codec.binary.Base64;
import org.junit.Assert;
import org.junit.Test;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.ByteBuffer;

public class TimerSerializationTest {

    @Test
    public void testV1RoundTrip() throws IOException {
        // build up a Timer
        TimerRollup r0 = new TimerRollup()
                .withSum(Double.valueOf(42))
                .withCountPS(23.32d)
                .withAverage(56)
                .withVariance(853.3245d)
                .withMinValue(2)
                .withMaxValue(987)
                .withCount(345);
        r0.setPercentile("foo", 741.32d);
        r0.setPercentile("bar", 0.0323d);

        if (System.getProperty("GENERATE_TIMER_SERIALIZATION") != null) {
            OutputStream os = new FileOutputStream("src/test/resources/serializations/timer_version_" + Constants.VERSION_1_TIMER + ".bin", false);
            //The V1 serialization is artificially constructed for the purposes of this test and should no longer be used.
            os.write(Base64.encodeBase64(new NumericSerializer.TimerRollupSerializer().toByteBufferWithV1Serialization(r0).array()));
            os.write("\n".getBytes());
            os.close();
        }

        Assert.assertTrue(new File("src/test/resources/serializations").exists());

        int version = 0;

        BufferedReader reader = new BufferedReader(new FileReader("src/test/resources/serializations/timer_version_" + version + ".bin"));
        ByteBuffer bb = ByteBuffer.wrap(Base64.decodeBase64(reader.readLine().getBytes()));
        TimerRollup r1 = new NumericSerializer.TimerRollupSerializer().fromByteBuffer(bb);
        Assert.assertEquals(r0, r1);
    }

    @Test
    public void testV2RoundTrip() throws IOException {
        // build up a Timer
        TimerRollup r0 = new TimerRollup()
                .withSum(Double.valueOf(42))
                .withCountPS(23.32d)
                .withAverage(56)
                .withVariance(853.3245d)
                .withMinValue(2)
                .withMaxValue(987)
                .withCount(345);
        r0.setPercentile("foo", 741.32d);
        r0.setPercentile("bar", 0.0323d);

        if (System.getProperty("GENERATE_TIMER_SERIALIZATION") != null) {
            OutputStream os = new FileOutputStream("src/test/resources/serializations/timer_version_" + Constants.VERSION_2_TIMER + ".bin", false);
            os.write(Base64.encodeBase64(new NumericSerializer.TimerRollupSerializer().toByteBuffer(r0).array()));
            os.write("\n".getBytes());
            os.close();
        }

        Assert.assertTrue(new File("src/test/resources/serializations").exists());

        // ensure historical reads work.
        int version = 0;
        int maxVersion = Constants.VERSION_2_TIMER;

        int count = 0;
        while (version <= maxVersion) {
            BufferedReader reader = new BufferedReader(new FileReader("src/test/resources/serializations/timer_version_" + version + ".bin"));
            ByteBuffer bb = ByteBuffer.wrap(Base64.decodeBase64(reader.readLine().getBytes()));
            TimerRollup r1 = new NumericSerializer.TimerRollupSerializer().fromByteBuffer(bb);
            Assert.assertEquals(r0, r1);
            count++;
            version++;
        }

        Assert.assertTrue("Nothing was tested", count > 0);
    }
}

File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/outputs/serializers/RollupEventSerializerTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.serializers;

import com.rackspacecloud.blueflood.outputs.serializers.helpers.RollupSerializationHelper;
import com.rackspacecloud.blueflood.types.*;
import junit.framework.Assert;
import org.codehaus.jackson.node.ArrayNode;
import org.codehaus.jackson.node.ObjectNode;
import org.junit.Test;

import java.io.IOError;
import java.io.IOException;

public class RollupEventSerializerTest {
    @Test
    public void testBasicRollupSerialization() {
        BasicRollup rollup = new BasicRollup();
        rollup.setCount(20);
        rollup.setAverage(10);
        rollup.setMax(20);
        rollup.setMin(5);
        rollup.setVariance(12);
        //Get the JSON object node from Rollup
        ObjectNode resultNode = RollupSerializationHelper.rollupToJson(rollup);
        Assert.assertEquals(resultNode.get("max").asLong(), rollup.getMaxValue().toLong());
        Assert.assertEquals(resultNode.get("min").asLong(), rollup.getMinValue().toLong());
        Assert.assertEquals(resultNode.get("mean").asLong(), rollup.getAverage().toLong());
        Assert.assertEquals(resultNode.get("var").asDouble(), rollup.getVariance().toDouble());
        Assert.assertEquals(resultNode.get("count").asLong(), rollup.getCount());
    }

    @Test
    public void testTimerRollupSerialization() {
        TimerRollup rollup = new TimerRollup();
        rollup.withCount(20);
        rollup.withAverage(10);
        rollup.withMaxValue(20);
        rollup.withMinValue(5);
        rollup.withVariance(12);
        rollup.withSum(Double.valueOf(10));
        rollup.withCountPS(30);
        //Get the JSON object node from Rollup
        ObjectNode resultNode = RollupSerializationHelper.rollupToJson(rollup);
        Assert.assertEquals(resultNode.get("max").asLong(), rollup.getMaxValue().toLong());
        Assert.assertEquals(resultNode.get("min").asLong(), rollup.getMinValue().toLong());
        Assert.assertEquals(resultNode.get("mean").asLong(), rollup.getAverage().toLong());
        Assert.assertEquals(resultNode.get("var").asDouble(), rollup.getVariance().toDouble());
        Assert.assertEquals(resultNode.get("count").asLong(), rollup.getCount());
        Assert.assertEquals(resultNode.get("sum").asDouble(), rollup.getSum());
        Assert.assertEquals(resultNode.get("rate").asDouble(), rollup.getRate());
    }

    @Test
    public void testHistgramRollupSerialization() throws IOException {
        Points<SimpleNumber> points = new Points<SimpleNumber>();
        long startTime = 12345678L;
        //Count = 3.0, Mean = 2.0
        points.add(new Points.Point<SimpleNumber>(startTime++, new SimpleNumber(1.0)));
        points.add(new Points.Point<SimpleNumber>(startTime++, new SimpleNumber(2.0)));
        points.add(new Points.Point<SimpleNumber>(startTime++, new SimpleNumber(3.0)));
        HistogramRollup histogramRollup = HistogramRollup.buildRollupFromRawSamples(points);
        ObjectNode resultNode = RollupSerializationHelper.rollupToJson(histogramRollup);
        ArrayNode node = (ArrayNode)resultNode.get("bins");
        Assert.assertEquals(node.get(0).get("count").asDouble(), 3.0);
        Assert.assertEquals(node.get(0).get("mean").asDouble(), 2.0);
    }

    @Test
    public void testSetRollupSerialization() {
        final SetRollup rollup0 = new SetRollup()
                .withObject(10)
                .withObject(20)
                .withObject(30);
        ObjectNode resultNode = RollupSerializationHelper.rollupToJson(rollup0);
        Assert.assertEquals(resultNode.get("count").asInt(), 3);
    }

    @Test
    public void testGaugeRollupSerialization() {
        final GaugeRollup rollup = new GaugeRollup()
                .withLatest(0, 1234);
        rollup.setMin(1);
        rollup.setMax(2);
        rollup.setCount(1);
        rollup.setVariance(23);
        rollup.setAverage(4);
        ObjectNode resultNode = RollupSerializationHelper.rollupToJson(rollup);
        Assert.assertEquals(resultNode.get("max").asLong(), rollup.getMaxValue().toLong());
        Assert.assertEquals(resultNode.get("min").asLong(), rollup.getMinValue().toLong());
        Assert.assertEquals(resultNode.get("mean").asLong(), rollup.getAverage().toLong());
        Assert.assertEquals(resultNode.get("var").asDouble(), rollup.getVariance().toDouble());
        Assert.assertEquals(resultNode.get("count").asLong(), rollup.getCount());
        Assert.assertEquals(resultNode.get("latestVal").asLong(), rollup.getLatestNumericValue().longValue());
    }

    //Passing an unknown rollup type will throw IOError
    @Test(expected = IOError.class)
    public void testExceptionOnInvalid() {
        class TestRollup implements Rollup{
            @Override
            public Boolean hasData() {
                return null;
            }

            @Override
            public RollupType getRollupType() {
                return null;
            }
        };
        RollupSerializationHelper.rollupToJson(new TestRollup());
    }

    @Test
    public void testNullValuesOnZeroCount() {
        BasicRollup rollup = new BasicRollup();
        rollup.setCount(0);
        //Get the JSON object node from Rollup
        ObjectNode resultNode = RollupSerializationHelper.rollupToJson(rollup);
        Assert.assertTrue(resultNode.get("max").isNull());
        Assert.assertTrue(resultNode.get("min").isNull());
        Assert.assertTrue(resultNode.get("mean").isNull());
        Assert.assertTrue(resultNode.get("var").isNull());
        Assert.assertEquals(resultNode.get("count").asLong(), 0);
    }
}


File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/rollup/GranularityTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.rollup;

import com.rackspacecloud.blueflood.exceptions.GranularityException;
import com.rackspacecloud.blueflood.types.Average;
import com.rackspacecloud.blueflood.types.Range;
import org.junit.Assert;
import org.junit.Test;

import java.util.Calendar;
import java.util.HashMap;
import java.util.Map;

public class GranularityTest {

    final long fromBaseMillis = Calendar.getInstance().getTimeInMillis();
    final long toBaseMillis = fromBaseMillis+ 604800000;
    final long milliSecondsInADay = 86400 * 1000;

    //An old timestamp that signifies ttld out data.
    // 619200000 is 8 days, just 1 day more than 7 days ie ttl limit of full gran
    final long oldFromBaseMillis_FullGran = fromBaseMillis - (8 * milliSecondsInADay);
    // 15 days old from toTimeStamp.
    final long oldToBaseMillis_FullGran = oldFromBaseMillis_FullGran + (7 * milliSecondsInADay);

    // A 16 days old time stamp beyond the ttl of 5m granularity
    final long oldFromBaseMillis_5m = fromBaseMillis - (16 * milliSecondsInADay);
    final long oldToBaseMillis_5m = oldFromBaseMillis_5m + (7 * milliSecondsInADay);

    // A 30 days old time stamp beyond the ttl of 20m granularity
    final long oldFromBaseMillis_20m = fromBaseMillis - (30 * milliSecondsInADay);
    final long oldToBaseMillis_20m = oldFromBaseMillis_20m + (7 * milliSecondsInADay);

    // A 160 days old time stamp beyond the ttl of 60m granularity
    final long oldFromBaseMillis_60m = fromBaseMillis - (160 * milliSecondsInADay);
    final long oldToBaseMillis_60m = oldFromBaseMillis_60m + (7 * milliSecondsInADay);

    //A 400 day old time stamp beyond the ttl of 240m granularity
    final long oldFromBaseMillis_240m = fromBaseMillis - (400 * milliSecondsInADay);
    final long oldToBaseMillis_240m = oldFromBaseMillis_240m + (7 * milliSecondsInADay);


    @Test
    public void testFromPointsInInterval_1WeekInterval_OldAndNew() throws Exception {
        Assert.assertEquals(Granularity.FULL.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, toBaseMillis, 86400).name());

        // The timestamp is too old for full data, so it goes to the next granularity ie 5m
        Assert.assertEquals(Granularity.MIN_5.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",oldFromBaseMillis_FullGran, oldToBaseMillis_FullGran, 86400).name());

        Assert.assertEquals(Granularity.MIN_5.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, toBaseMillis, 1152).name());

        //The timestamp is too old for 5m. So it goes to the next granularity ie 20m
        Assert.assertEquals(Granularity.MIN_20.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",oldFromBaseMillis_5m, oldToBaseMillis_5m, 1152).name());


        Assert.assertEquals(Granularity.MIN_20.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, toBaseMillis, 576).name());

        //The timestamp is too old for 20m. So it goes to the next granularity ie 60m
        Assert.assertEquals(Granularity.MIN_60.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",oldFromBaseMillis_20m, oldToBaseMillis_20m, 576).name());


        Assert.assertEquals(Granularity.MIN_60.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, toBaseMillis, 96).name());

        //The timestamp is too old for 60m. So it goes to the next granularity ie 240m
        Assert.assertEquals(Granularity.MIN_240.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",oldFromBaseMillis_60m, oldToBaseMillis_60m, 96).name());


        Assert.assertEquals(Granularity.MIN_240.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, toBaseMillis, 24).name());

        //The timestamp is too old for 240m. So it goes to the next granularity ie 1440m
        Assert.assertEquals(Granularity.MIN_1440.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",oldFromBaseMillis_240m, oldToBaseMillis_240m, 24).name());


        Assert.assertEquals(Granularity.MIN_1440.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, toBaseMillis, 1).name());
    }

    @Test
    public void testFromPointsInterval_ADayInterval() throws Exception {
        Assert.assertEquals(Granularity.FULL.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, fromBaseMillis+86400000, 86400).name());
        Assert.assertEquals(Granularity.MIN_5.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, fromBaseMillis+86400000, 288).name());
        Assert.assertEquals(Granularity.MIN_20.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, fromBaseMillis+86400000, 72).name());
        Assert.assertEquals(Granularity.MIN_60.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, fromBaseMillis+86400000, 24).name());
        Assert.assertEquals(Granularity.MIN_240.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, fromBaseMillis+86400000, 6).name());
        Assert.assertEquals(Granularity.MIN_1440.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, fromBaseMillis+86400000, 1).name());
    }

    @Test
    public void testFromPointsInInterval_LessThanADayInterval() throws Exception {
        Assert.assertEquals(Granularity.FULL.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, fromBaseMillis+43200000, 800).name());
        Assert.assertEquals(Granularity.MIN_5.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, fromBaseMillis+43200000, 288).name()); // 144 5m points vs 1440 full points.
        Assert.assertEquals(Granularity.MIN_5.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, fromBaseMillis+43200000, 144).name());
        Assert.assertEquals(Granularity.MIN_20.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, fromBaseMillis+43200000, 35).name());
        Assert.assertEquals(Granularity.MIN_60.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, fromBaseMillis+43200000, 11).name());
        Assert.assertEquals(Granularity.MIN_240.name(), Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, fromBaseMillis+43200000, 3).name());
    }

    @Test
    public void testRangesForInterval() throws Exception {
        Assert.assertEquals(1, countIterable(Range.rangesForInterval(Granularity.FULL, 0, 86399000)));
        Assert.assertEquals(288, countIterable(Range.rangesForInterval(Granularity.MIN_5, 0, 86399000)));
        Assert.assertEquals(72, countIterable(Range.rangesForInterval(Granularity.MIN_20, 0, 86399000)));
        Assert.assertEquals(24, countIterable(Range.rangesForInterval(Granularity.MIN_60, 0, 86399000)));
        Assert.assertEquals(6, countIterable(Range.rangesForInterval(Granularity.MIN_240, 0, 86399000)));
        Assert.assertEquals(1, countIterable(Range.rangesForInterval(Granularity.MIN_1440, 0, 86399000)));
        // The following test case was added after a production issue in which the call to rangesForInterval never
        // terminated.
        Assert.assertEquals(7, countIterable(Range.rangesForInterval(Granularity.MIN_240, System.currentTimeMillis() - (24 * 60 * 60 * 1000), System.currentTimeMillis())));
    }

    private int countIterable(Iterable<Range> ir) {
        int count = 0;
        for (Range r: ir) {
            count ++;
        }
        return count;
    }

    @Test
    public void testForCloseness() {
        int desiredPoints = 10;
        long start = Calendar.getInstance().getTimeInMillis();
        // 10000000ms == 166.67 min.  166/20 is 8 points. 166/5 is 33 points.  The old algorithm returned the latter, which is too many.
        // 1000000ms == 16.67 min. 16/20 is 0, 16/5 is 3 points, 16/full = 32 points.
        // is too many.
        Assert.assertEquals(Granularity.MIN_20, Granularity.granularityFromPointsInInterval("TENANTID1234",start, start + 10000000, desiredPoints));
        Assert.assertEquals(Granularity.MIN_5, Granularity.granularityFromPointsInInterval("TENANTID1234",start, start + 1000000, desiredPoints));
      
        // Test edge cases using a 100000000 millisecond swath. For reference 100k secs generates:
        // 3333.33 full res points (at 30s per check)
        // 333.33 5min points
        // 83.33 20min points
        // 27.78 60min points
        // 6.94 240min points
        // 1.15 1440min points
        // To compute the boundaries used below, solve the parallel equation for x (I suggest Wolfram Alpha):
        //    1/a * x = higher_res_point_count
        //      a * x = lower_res_point_count
        Map<Integer, Granularity> expectedGranularities = new HashMap<Integer, Granularity>() {{
            // Request sub 30 second periods
            put(5000, Granularity.FULL);

            // Edge between FULL and MIN_5 (boundary is ~1054.09 points)
            put(1055, Granularity.FULL);
            put(1054, Granularity.MIN_5);

            // Edge between MIN_5 and MIN_20 (boundary is ~166.66 points)
            put(167, Granularity.MIN_5);
            put(166, Granularity.MIN_20);

            // Edge between MIN_20 and MIN_60 (boundary is ~48.11 points)
            put(49, Granularity.MIN_20);
            put(48, Granularity.MIN_60);

            // Edge between MIN_60 and MIN_240 (boundary is ~13.89 points)
            put(14, Granularity.MIN_60);
            put(13, Granularity.MIN_240);

            // Edge between MIN_240 and MIN_1440 (boundary is ~2.83 points)
            put(3, Granularity.MIN_240);
            put(2, Granularity.MIN_1440);

            put(1, Granularity.MIN_1440); // Request > 1 day periods
        }};
        
        for (Map.Entry<Integer, Granularity> entry : expectedGranularities.entrySet()) {
            Granularity actual = Granularity.granularityFromPointsInInterval("TENANTID1234",start, start+100000000, entry.getKey());
            Assert.assertEquals(
                    String.format("%d points", entry.getKey()),
                    entry.getValue(), 
                    actual);
        }
    }

    @Test
    public void testCommonPointRequests() {
        long HOUR = 3600000;
        long DAY = 24 * HOUR;

        // 300 points covering 1 hour -> FULL (120 points)
        Assert.assertEquals(Granularity.FULL, Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, fromBaseMillis+HOUR, 300));

        // 300 points covering 8 hours -> MIN_5 (96 points - 8 hours is actually a really unfortunate interval)
        Assert.assertEquals(Granularity.MIN_5, Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, fromBaseMillis+(8 * HOUR), 300));

        // 300 points covering 12 hours -> MIN_5 (144 points)
        Assert.assertEquals(Granularity.MIN_5, Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, fromBaseMillis+(12 * HOUR), 300));

        // 300 points covering 1 day -> MIN_5 (288 points)
        Assert.assertEquals(Granularity.MIN_5, Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, fromBaseMillis+DAY, 300));

        // 300 points covering 1 week -> MIN_20 (504 points)
        Assert.assertEquals(Granularity.MIN_20, Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, fromBaseMillis+(7 * DAY), 300));

        // 300 points covering 1 month -> MIN_240 (180 points)
        Assert.assertEquals(Granularity.MIN_240, Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis, fromBaseMillis+(30 * DAY), 300));
    }

    @Test(expected = GranularityException.class)
    public void testTooCoarse() throws Exception {
        Granularity g = Granularity.FULL;
        Granularity[] granularities = Granularity.granularities();

        int count = 1;
        while (true) {
            g = g.coarser();
            Assert.assertEquals(granularities[count++], g);
        }
    }

    @Test(expected = GranularityException.class)
    public void testTooFine() throws Exception {
        Granularity g = Granularity.MIN_1440;
        Granularity[] granularities = Granularity.granularities();

        int count = granularities.length - 2;

        while (true) {
            g = g.finer();
            Assert.assertEquals(granularities[count--], g);
        }
    }
    
    @Test(expected = RuntimeException.class)
    public void testToBeforeFromInterval() {
        Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis+10000000, fromBaseMillis+0, 100);
    }
    
    @Test
    public void testGranularityEqualityAndFromString() {
        for (Granularity g : Granularity.granularities()) {
            Assert.assertTrue(g == Granularity.fromString(g.name()));
            Assert.assertTrue(g.equals(Granularity.fromString(g.name())));
            Assert.assertFalse(g.equals(new Object()));
            // throw this one in too.
            Assert.assertEquals(g.name(), g.toString());
        }
        Assert.assertNull(Granularity.fromString("nonexistant granularity"));
    }

    @Test
    public void testEquals() {
        Granularity gran1 = Granularity.MIN_5;
        Granularity gran2 = Granularity.MIN_5;
        Granularity gran3 = Granularity.MIN_1440;
        Average avg = new Average(1, 2.0);

        Assert.assertEquals(gran2, gran1);
        Assert.assertFalse(gran1.equals(gran3));
        Assert.assertFalse(gran1.equals(avg));
    }

    @Test
    public void testFromString() {
        Granularity gran;
        String s;

        s = "metrics_full";
        gran = Granularity.fromString(s);
        Assert.assertTrue(gran.equals(Granularity.FULL));

        s = "metrics_5m";
        gran = Granularity.fromString(s);
        Assert.assertTrue(gran.equals(Granularity.MIN_5));

        s = "metrics_20m";
        gran = Granularity.fromString(s);
        Assert.assertTrue(gran.equals(Granularity.MIN_20));

        s = "metrics_60m";
        gran = Granularity.fromString(s);
        Assert.assertTrue(gran.equals(Granularity.MIN_60));

        s = "metrics_240m";
        gran = Granularity.fromString(s);
        Assert.assertTrue(gran.equals(Granularity.MIN_240));

        s = "metrics_1440m";
        gran = Granularity.fromString(s);
        Assert.assertTrue(gran.equals(Granularity.MIN_1440));

        s = "metrics_1990m";
        gran = Granularity.fromString(s);
        Assert.assertNull(gran);
    }

    @Test
    public void testBadGranularityFromPointsInterval() {
        try {
            Granularity.granularityFromPointsInInterval("TENANTID1234",fromBaseMillis+2, fromBaseMillis+1, 3);
            Assert.fail("Should not have worked");
        }
        catch (RuntimeException e) {
            Assert.assertEquals("Invalid interval specified for fromPointsInInterval", e.getMessage());
        }
    }

    @Test
    public void testIsCoarser() {
        Assert.assertTrue(!Granularity.FULL.isCoarser(Granularity.MIN_5));
        Assert.assertTrue(!Granularity.MIN_5.isCoarser(Granularity.MIN_20));
        Assert.assertTrue(!Granularity.MIN_20.isCoarser(Granularity.MIN_60));
        Assert.assertTrue(!Granularity.MIN_60.isCoarser(Granularity.MIN_240));
        Assert.assertTrue(!Granularity.MIN_240.isCoarser(Granularity.MIN_1440));

        Assert.assertTrue(Granularity.MIN_5.isCoarser(Granularity.FULL));
        Assert.assertTrue(Granularity.MIN_20.isCoarser(Granularity.MIN_5));
        Assert.assertTrue(Granularity.MIN_60.isCoarser(Granularity.MIN_20));
        Assert.assertTrue(Granularity.MIN_240.isCoarser(Granularity.MIN_60));
        Assert.assertTrue(Granularity.MIN_1440.isCoarser(Granularity.MIN_240));
    }
}


File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/rollup/RangeTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.rollup;

import com.rackspacecloud.blueflood.exceptions.GranularityException;
import com.rackspacecloud.blueflood.types.Average;
import com.rackspacecloud.blueflood.types.Range;
import org.junit.Assert;
import org.junit.Test;

import java.util.Iterator;

public class RangeTest {

    @Test
    public void testGetStartAndStop() {
        Range myRange = new Range(1, 2);

        Assert.assertEquals(1, myRange.getStart());
        Assert.assertEquals(2, myRange.getStop());
    }

    @Test
    public void testEquals() {
        Range myRange = new Range(1, 2);
        Range myRange2 = new Range(1, 2);
        Range myRange3 = new Range(2, 3);
        Average avg = new Average(1, 2.0);

        Assert.assertFalse(myRange.equals(avg));
        Assert.assertFalse(myRange.equals(myRange3));
        Assert.assertTrue(myRange.equals(myRange2));
    }

    @Test
    public void testToString() {
        Range myRange = new Range(1, 3);

        Assert.assertEquals("1:3 (2)", myRange.toString());
    }

    @Test
    public void testIntervalRangeIteratorRemoveNotSupported() {
        Iterable<Range> myRanges = Range.rangesForInterval(Granularity.MIN_20, 1200000, 1200000);
        Iterator<Range> myRangeIterator = myRanges.iterator();

        Assert.assertTrue(myRangeIterator.hasNext());

        if(myRangeIterator.hasNext()) {
            try {
                myRangeIterator.remove();
                Assert.fail("Never should have gotten here");
            }
            catch (RuntimeException e) {
                Assert.assertEquals("Not supported", e.getMessage());
            }
        }
    }

    @Test
    public void testBadIntervalRangeIterator() {
        try {
            Iterable<Range> myRanges = Range.getRangesToRollup(Granularity.MIN_1440, 1, 300000);
            Assert.fail("Never should have gotten here");
        }
        catch (GranularityException e) {
            Assert.assertEquals("Nothing coarser than metrics_1440m", e.getMessage());
        }

    }
}


File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/rollup/SlotTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.rollup;

import com.rackspacecloud.blueflood.exceptions.GranularityException;
import com.rackspacecloud.blueflood.types.Range;
import org.junit.Assert;
import org.junit.Test;

import java.util.HashSet;
import java.util.Map;
import java.util.Set;

public class SlotTest {
    @Test
    public void testRangeIteratorFullAnd5m() throws Exception {
        Set<Range> expectedRanges = new HashSet<Range>();
        expectedRanges.add(new Range(0, 299999));
        expectedRanges.add(new Range(300000, 599999));
        expectedRanges.add(new Range(600000, 899999));
        expectedRanges.add(new Range(900000, 1199999));
        
        // FULL and 5m have the same rollup semantics.
        for (Granularity g : new Granularity[] { Granularity.FULL, Granularity.MIN_5}) {
            Set<Range> actualRanges = new HashSet<Range>();
            for (Range time : Range.getRangesToRollup(g, 200000, 1000000)) {
                actualRanges.add(time);
                verifySingleSlot(time, g);
            }
            Assert.assertEquals(expectedRanges, actualRanges);
        }
    }
    
    @Test
    public void testRangeIterator20m() throws Exception {
        Set<Range> expectedRanges = makeRanges(Granularity.MIN_20, 3600000, 33);
        Set<Range> actualRanges = new HashSet<Range>();
        int baseMillis = 6500000;
        int hrs = 10;
        int endMillis = baseMillis + 3600000 * hrs;
        for (Range time : Range.getRangesToRollup(Granularity.MIN_20, baseMillis, endMillis)) {
            actualRanges.add(time);
            verifySingleSlot(time, Granularity.MIN_20);
        }
        Assert.assertEquals(expectedRanges, actualRanges);
    }

    @Test
    public void testRangeMapper60m() throws Exception {
        int baseMillis = 6500000;
        int hrs = 10;
        int endMillis = baseMillis + 3600000 * hrs;
        //Map of every 60m(coarser gran) in this time range, mapped to iterable of 20m sub-ranges that get rolled up
        Map<Range, Iterable<Range>> retMap = Range.mapFinerRanges(Granularity.MIN_60, new Range(baseMillis, endMillis));
        Assert.assertEquals(retMap.entrySet().size(), 11);
        for(Map.Entry<Range,Iterable<Range>> entry : retMap.entrySet()) {
            Range coarserSubRange = entry.getKey();
            int iterValCount = 0;
            Iterable<Range> subranges = entry.getValue();
            for (Range subrange : subranges) {
                if(iterValCount == 0) {
                    //Start point of coarser range is equal to start point of 1st 20m sub-range
                    Assert.assertEquals(coarserSubRange.getStart(), subrange.getStart());
                }
                iterValCount++;
                if(iterValCount == 3) {
                    Assert.assertEquals(coarserSubRange.getStop() - 1, subrange.getStop());
                }
            }
            //Every 60m range gets divided into 3 20m sub-ranges
            Assert.assertEquals(iterValCount, 3);
        }
    }
    
    @Test
    public void testRangeIterator60m() throws Exception {
        Set<Range> expectedRanges = makeRanges(Granularity.MIN_60, 1334577600000L, 72);
        Set<Range> actualRanges = new HashSet<Range>();
        long baseMillis = 1334582854000L; // nearly Mon Apr 16 06:26:52 PDT 2012
        int hrs = 70;
        long endMillis = baseMillis + 3600000 * hrs;
        for (Range time : Range.getRangesToRollup(Granularity.MIN_60, baseMillis, endMillis)) {
            actualRanges.add(time);
            verifySingleSlot(time, Granularity.MIN_60);
        }
        Assert.assertEquals(expectedRanges, actualRanges);
    }
    
    @Test
    public void testRangeIterator240m() throws Exception {
        Set<Range> expectedRanges = makeRanges(Granularity.MIN_240, 1334534400000L, 66);
        Set<Range> actualRanges = new HashSet<Range>();
        long baseMillis = 1334582854000L; // nearly Mon Apr 16 06:26:52 PDT 2012
        int hrs = 240; // 10 days.
        long endMillis = baseMillis + 3500000 * hrs; // todo: should be 3600000?
        for (Range time : Range.getRangesToRollup(Granularity.MIN_240, baseMillis, endMillis)) {
            actualRanges.add(time);
            verifySingleSlot(time, Granularity.MIN_240);    
        }
        Assert.assertEquals(expectedRanges, actualRanges);
    } 
    
    // there is no testRangeIterator1440m because range iteration isn't defined for that granularity because there
    // is no granularity that is more coarse.
    
    // ensure that every point of time within a given range is in the same slot as the beginning of the range.
    private void verifySingleSlot(Range r, Granularity g) {
        int init = g.slot(r.start);
        for (long time = r.start; time <= r.stop; time += 1000)
            Assert.assertEquals(init, g.slot(time));
    }
    
    // create a collection of consecutive ranges.
    private static Set<Range> makeRanges(Granularity g, long startMillis, int count) {
        Set<Range> set = new HashSet<Range>();
        long millis = startMillis;
        for (int i = 0; i < count; i++) {
            long end = millis + g.milliseconds();
            set.add(new Range(millis, end - 1));
            millis = end;
        }
        return set;
    }
    
    @Test
    public void testSlotCalculationsRawAnd5m() {
        final long now = 1331650343000L;
        final long slot = 3634;
        Assert.assertEquals(slot, Granularity.millisToSlot(now));
        
        // 5 mins now should be in the next slot.
        Assert.assertEquals(slot + 1, Granularity.millisToSlot(now + Granularity.MILLISECONDS_IN_SLOT));
        Assert.assertEquals(slot + 1, Granularity.FULL.slot(now + Granularity.MILLISECONDS_IN_SLOT));
        Assert.assertEquals(slot + 1, Granularity.MIN_5.slot(now + Granularity.MILLISECONDS_IN_SLOT));
        
        // should repeat after however many seconds are in NUMBER_OF_SLOTS * MILLISECONDS_PER_SLOT
        Assert.assertEquals(slot, Granularity.millisToSlot(now + (Granularity.FULL.numSlots() * Granularity.MILLISECONDS_IN_SLOT)));
        Assert.assertEquals(slot, Granularity.FULL.slot(now + (Granularity.FULL.numSlots() * Granularity.MILLISECONDS_IN_SLOT)));
        Assert.assertEquals(slot, Granularity.MIN_5.slot(now + (Granularity.FULL.numSlots() * Granularity.MILLISECONDS_IN_SLOT)));
        
        // test the very end of the cycle.
        long endOfCycle = now + ((Granularity.FULL.numSlots() - slot - 1) * Granularity.MILLISECONDS_IN_SLOT); // basically the number of secs to get to slot == 4095
        Assert.assertEquals(Granularity.FULL.numSlots() - 1, Granularity.millisToSlot(endOfCycle));
        Assert.assertEquals(Granularity.FULL.numSlots() - 1, Granularity.FULL.slot(endOfCycle));
        Assert.assertEquals(Granularity.MIN_5.numSlots() - 1, Granularity.MIN_5.slot(endOfCycle));
        
        // adding 300s (one slot) should wrap back around to zero.
        Assert.assertEquals(0, Granularity.millisToSlot(endOfCycle + Granularity.MILLISECONDS_IN_SLOT));
        Assert.assertEquals(0, Granularity.FULL.slot(endOfCycle + Granularity.MILLISECONDS_IN_SLOT));
        Assert.assertEquals(0, Granularity.MIN_5.slot(endOfCycle + Granularity.MILLISECONDS_IN_SLOT));
    }

    @Test
    public void testSlotRelationships() {
        final long now = 1331650343000L;
        final long slot = 3634;
        Assert.assertEquals(slot, Granularity.FULL.slot(now));
        Assert.assertEquals(slot, Granularity.MIN_5.slot(now));
     
        Assert.assertEquals(Granularity.FULL.numSlots(), Granularity.MIN_5.numSlots());
        Assert.assertEquals(Granularity.FULL.numSlots() / 4, Granularity.MIN_20.numSlots());
        Assert.assertEquals(Granularity.FULL.numSlots() / 12, Granularity.MIN_60.numSlots());
        Assert.assertEquals(Granularity.FULL.numSlots() / 48, Granularity.MIN_240.numSlots());
        Assert.assertEquals(Granularity.FULL.numSlots() / 288, Granularity.MIN_1440.numSlots());
        
        // make sure there are no remainders for the minute ratios
        Assert.assertTrue(Granularity.FULL.numSlots() % 4 == 0);
        Assert.assertTrue(Granularity.FULL.numSlots() % 12 == 0);
        Assert.assertTrue(Granularity.FULL.numSlots() % 48 == 0);
        Assert.assertTrue(Granularity.FULL.numSlots() % 288 == 0);
    } 

    @Test
    public void testStaticSameAsFull() {
        final long baseMillis = 1333635148000L; // some point during 5 April 2012.
        final long endMillis = baseMillis + (1000 * 60 * 60 * 48); // +48hrs
        Assert.assertEquals(Granularity.millisToSlot(baseMillis), Granularity.FULL.slot(baseMillis));
        Assert.assertEquals(Granularity.millisToSlot(endMillis), Granularity.FULL.slot(endMillis));
        
    }
    
    @Test
    // make sure the same kind of tests still pass at coarser granularities.
    public void testCoarseSlotCalculations() {
        final long now = 1334582854000L;
        Granularity[] granularities = new Granularity[] {Granularity.MIN_20, Granularity.MIN_60, Granularity.MIN_240, Granularity.MIN_1440};
        int[] initialSlots = new int[] {328, 109, 27, 4};
        
        for (int i = 0; i < initialSlots.length; i++) {
            final long slot = initialSlots[i];
            final Granularity gran = granularities[i]; 
            
            Assert.assertEquals(slot, gran.slot(now));
            
            // next slot should increment by 1.
            Assert.assertEquals(slot + 1, gran.slot(now + gran.milliseconds()));
            
            // should repeat.
            Assert.assertEquals(slot, gran.slot(now + gran.milliseconds() * gran.numSlots()));
            
            // very end of cycle.
            long endOfCycle = now + (gran.numSlots() - slot - 1) * gran.milliseconds();
            Assert.assertEquals(gran.numSlots() - 1, gran.slot(endOfCycle));
            
            // adding seconds() should wrap back to zero.
            Assert.assertEquals(0, gran.slot(endOfCycle + gran.milliseconds()));
        }
    }

    @Test(expected=GranularityException.class)
    public void testSlotFromFinerSlotThrowsAtFull() throws Throwable {
        try {
            Granularity.FULL.slotFromFinerSlot(123);
        } catch (RuntimeException e) {
            throw e.getCause();
        }
    }

    @Test
    public void testSlotFromFinerSlot() {
        // i.e, slot 144 for a 5m is == slot 36 of 20m ( 144 / (20/5)), slot 12 at 60m, slot 3 at 240m, etc
        try {
            Assert.assertEquals(256, Granularity.MIN_5.slotFromFinerSlot(256));

            Assert.assertEquals(35, Granularity.MIN_20.slotFromFinerSlot(143));
            Assert.assertEquals(36, Granularity.MIN_20.slotFromFinerSlot(144));
            Assert.assertEquals(36, Granularity.MIN_20.slotFromFinerSlot(145));
            Assert.assertEquals(36, Granularity.MIN_20.slotFromFinerSlot(146));
            Assert.assertEquals(36, Granularity.MIN_20.slotFromFinerSlot(147));
            Assert.assertEquals(37, Granularity.MIN_20.slotFromFinerSlot(148));

            Assert.assertEquals(12, Granularity.MIN_60.slotFromFinerSlot(36));
            Assert.assertEquals(3, Granularity.MIN_240.slotFromFinerSlot(12));
            Assert.assertEquals(2, Granularity.MIN_1440.slotFromFinerSlot(13));
        } catch (GranularityException e) {
            Assert.assertNull("GranularityException seen on non-full-res Granularity", e);
        }
    }

    
    @Test
    public void testRangeDerivation() {
        for (Granularity gran : Granularity.granularities()) {
            long now = 1334582854000L;
            int nowSlot = gran.slot(now);
            now = gran.snapMillis(now);
            Range nowRange = new Range(now, now + gran.milliseconds() - 1);
            Assert.assertEquals(nowRange, gran.deriveRange(nowSlot, now));
            
            Range prevRange = gran.deriveRange(nowSlot - 1, now);
            Assert.assertEquals(gran.milliseconds(), nowRange.start - prevRange.start);
            
            // incrementing nowSlot forces us to test slot wrapping.
            Range wayBeforeRange = gran.deriveRange(nowSlot + 1, now);
            Assert.assertEquals(gran.numSlots() - 1, (nowRange.start - wayBeforeRange.start) / gran.milliseconds());
        }
    }
}


File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/rollup/UtilTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.rollup;

import com.rackspacecloud.blueflood.io.Constants;
import com.rackspacecloud.blueflood.utils.Util;
import org.junit.Assert;
import org.junit.Test;

import java.util.Random;

public class UtilTest {
    private static final Random rand = new Random();
    
    private static String randomString(int length) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < length; i++)
            sb = sb.append((char)(rand.nextInt(94)+32));
        return sb.toString();
    }
    
    @Test
    public void testComputeShard() {
        for (int i = 0; i < 10000; i++) {
            int shard = Util.computeShard(randomString(rand.nextInt(100) + 1));
            Assert.assertTrue(shard >= 0);
            Assert.assertTrue(shard < Constants.NUMBER_OF_SHARDS);
        }
    }
    
    @Test
    public void testParseShards() {
        Assert.assertEquals(128, Util.parseShards("ALL").size());
        Assert.assertEquals(0, Util.parseShards("NONE").size());
        Assert.assertEquals(5, Util.parseShards("1,9,4,23,0").size());
        
        try {
            Util.parseShards("1,x,23");
            Assert.assertTrue("Should not have gotten here.", false);
        } catch (NumberFormatException expected) {}
        
        try {
            Util.parseShards("EIGHTY");
            Assert.assertTrue("Should not have gotten here.", false);
        } catch (NumberFormatException expected) {}
        
        try {
            Util.parseShards("1,2,3,4,0,-1");
            Assert.assertTrue("Should not have gotten here.", false);
        } catch (NumberFormatException expected) {}

        boolean exception = false;
        try {
            Util.parseShards("" + (Constants.NUMBER_OF_SHARDS + 1));
        } catch (NumberFormatException expected) {
            exception = true;
            Assert.assertEquals("Invalid shard identifier: 129", expected.getMessage());
        }

        Assert.assertEquals(true, exception);
    }

    @Test
    public void testGetDimensionFromKey() {
        Assert.assertEquals("mzORD", Util.getDimensionFromKey("mzORD.blah"));
        Assert.assertEquals("dim0", Util.getDimensionFromKey("dim0.blah"));
    }

    @Test
    public void testGetMetricFromKey() {
        Assert.assertEquals("blah.sawtooth", Util.getMetricFromKey("mzGRD.blah.sawtooth"));
        Assert.assertEquals("blah", Util.getMetricFromKey("mzGRD.blah"));
        Assert.assertEquals("sawtooth", Util.getMetricFromKey("dim0.sawtooth"));
    }
}


File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/service/AtomicCountingSetTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;


import com.rackspacecloud.blueflood.utils.AtomicCountingSet;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;

import java.util.concurrent.*;

public class AtomicCountingSetTest {
    private AtomicCountingSet<Integer> testSet;

    @Before
    public void setUp() {
        testSet = new AtomicCountingSet<Integer>();
    }

    @Test
    public void testSimultaneousPut() throws Exception {
        ExecutorService executorService = Executors.newCachedThreadPool();

        final CountDownLatch startLatch = new CountDownLatch(1);
        Future<Void> f1 = executorService.submit
                (
                        new Callable<Void>()
                        {
                            @Override
                            public Void call() throws Exception
                            {
                                startLatch.await();
                                for (int i = 0; i < 1000; i++) {
                                    testSet.increment(1);
                                }
                                return null;
                            }
                        }
                );

        Future<Void> f2 = executorService.submit
                (
                        new Callable<Void>()
                        {
                            @Override
                            public Void call() throws Exception
                            {
                                startLatch.await();
                                for (int i = 0; i < 1000; i++) {
                                    testSet.increment(1);
                                }
                                return null;
                            }
                        }
                );

        startLatch.countDown();
        f1.get();
        f2.get();

        Assert.assertEquals(2000, testSet.getCount(1));
    }

    @Test
    public void testSimultaneousPutAndRemove() throws Exception {
        ExecutorService executorService = Executors.newCachedThreadPool();

        final CountDownLatch startLatch = new CountDownLatch(1);
        testSet.increment(1);
        Future<Void> f1 = executorService.submit
                (
                        new Callable<Void>()
                        {
                            @Override
                            public Void call() throws Exception
                            {
                                startLatch.await();
                                for (int i = 0; i < 1000; i++) {
                                    testSet.increment(1);
                                }
                                return null;
                            }
                        }
                );

        Future<Void> f2 = executorService.submit
                (
                        new Callable<Void>()
                        {
                            @Override
                            public Void call() throws Exception
                            {
                                startLatch.await();
                                for (int i = 0; i < 1000; i++) {
                                    testSet.decrement(1);
                                }
                                return null;
                            }
                        }
                );

        startLatch.countDown();
        f1.get();
        f2.get();

        // Data should be consistent now
        Assert.assertEquals(1, testSet.getCount(1));
    }

    // We are not interested in seeing if the data is consistent. We only want to know if there is no concurrent
    // modification exception thrown
    @Test
    public void testSimultaneousPutAndContains() throws Exception {
        ExecutorService executorService = Executors.newCachedThreadPool();

        final CountDownLatch startLatch = new CountDownLatch(1);

        Future<Void> f1 = executorService.submit
                (
                        new Callable<Void>()
                        {
                            @Override
                            public Void call() throws Exception
                            {
                                startLatch.await();
                                for (int i = 0; i < 1000; i++) {
                                    testSet.increment(1);
                                }
                                return null;
                            }
                        }
                );

        Future<Void> f2 = executorService.submit
                (
                        new Callable<Void>()
                        {
                            @Override
                            public Void call() throws Exception
                            {
                                startLatch.await();
                                for (int i = 0; i < 1000; i++) {
                                    testSet.contains(1);
                                }
                                return null;
                            }
                        }
                );

        startLatch.countDown();
        f1.get();
        f2.get();

        // Now the data should be consistent. Let's check
        Assert.assertTrue(testSet.contains(1));
    }

    @Test
    public void testContains() throws Exception {
        ExecutorService executorService = Executors.newCachedThreadPool();

        final CountDownLatch startLatch = new CountDownLatch(1);

        testSet.increment(1);

        Future<Void> f1 = executorService.submit
                (
                        new Callable<Void>()
                        {
                            @Override
                            public Void call() throws Exception
                            {
                                testSet.decrement(1);
                                startLatch.countDown();
                                return null;
                            }
                        }
                );

        Future<Void> f2 = executorService.submit
                (
                        new Callable<Void>()
                        {
                            @Override
                            public Void call() throws Exception
                            {
                                startLatch.await();
                                Assert.assertTrue(!testSet.contains(1));
                                return null;
                            }
                        }
                );

        f1.get();
        f2.get();
    }
}

File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/service/ConfigurationTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import org.junit.Assert;
import org.junit.Test;

import java.io.File;
import java.io.IOException;
import java.util.Arrays;
import java.util.Map;

public class ConfigurationTest {

    @Test
    public void testConfiguration() {
        Configuration config = Configuration.getInstance();
        Map<Object, Object> properties = config.getProperties();

        Assert.assertNotNull(properties);

        Assert.assertEquals("127.0.0.1:19180", config.getStringProperty(CoreConfig.CASSANDRA_HOSTS));
        System.setProperty("CASSANDRA_HOSTS", "127.0.0.2");
        Assert.assertEquals("127.0.0.2", config.getStringProperty(CoreConfig.CASSANDRA_HOSTS));

        Assert.assertEquals(60000, config.getIntegerProperty(CoreConfig.SCHEDULE_POLL_PERIOD));

    }

    @Test
    public void testInitWithBluefloodConfig() throws IOException {
        Configuration config = Configuration.getInstance();
        Assert.assertNull(config.getStringProperty("TEST_PROPERTY"));
        Assert.assertEquals("ALL", config.getStringProperty(CoreConfig.SHARDS));

        String configPath = new File("src/test/resources/bf-override-config.properties").getAbsolutePath();
        System.setProperty("blueflood.config", "file://" + configPath);
        config.init();

        Assert.assertEquals("foo", config.getStringProperty("TEST_PROPERTY"));
        Assert.assertEquals("NONE", config.getStringProperty(CoreConfig.SHARDS));
    }

    @Test
    public void testGetListProperty() {
        Configuration config = Configuration.getInstance();
        Assert.assertEquals(config.getStringProperty(CoreConfig.QUERY_MODULES), "");
        Assert.assertTrue(config.getListProperty(CoreConfig.QUERY_MODULES).isEmpty());
        System.setProperty("QUERY_MODULES", "a");
        Assert.assertEquals(config.getListProperty(CoreConfig.QUERY_MODULES).size(), 1);
        System.setProperty("QUERY_MODULES", "a,b , c");
        Assert.assertEquals(Arrays.asList("a","b","c"), config.getListProperty(CoreConfig.QUERY_MODULES));
    }

    @Test
    public void testBooleanProperty() {
        Configuration config = Configuration.getInstance();
        Assert.assertEquals(config.getStringProperty("foo"), null);
        Assert.assertFalse(config.getBooleanProperty("foo"));
        System.setProperty("foo", "TRUE");
        Assert.assertTrue(config.getBooleanProperty("foo"));
    }
}


File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/service/RollupExecutionContextTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import org.junit.Assert;
import org.junit.Test;

public class RollupExecutionContextTest {

    @Test
    public void testExecutionContext() {
        Thread myThread = new Thread();

        RollupExecutionContext myRollupContext = new RollupExecutionContext(myThread);

        // validate read behavior
        Assert.assertTrue(myRollupContext.doneReading());
        myRollupContext.incrementReadCounter();
        Assert.assertFalse(myRollupContext.doneReading());
        myRollupContext.decrementReadCounter();
        Assert.assertTrue(myRollupContext.doneReading());

        // validate put behavior
        Assert.assertTrue(myRollupContext.doneWriting());
        myRollupContext.incrementWriteCounter();
        myRollupContext.incrementWriteCounter();
        Assert.assertFalse(myRollupContext.doneWriting());
        myRollupContext.decrementWriteCounter(2);
        Assert.assertTrue(myRollupContext.doneWriting());
    }
}


File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/service/ScheduleContextTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.rollup.SlotKey;
import com.rackspacecloud.blueflood.utils.Util;
import com.rackspacecloud.blueflood.utils.TimeValue;
import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import com.google.common.collect.Lists;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;
import org.mockito.internal.util.reflection.Whitebox;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

public class ScheduleContextTest {
    private static final Logger log = LoggerFactory.getLogger("tests");
    private static List<Integer> ringShards;
    private static final TimeValue MULTI_THREAD_SOFT_TIMEOUT = new TimeValue(60000L, TimeUnit.MILLISECONDS);;

    @Before
    public void setUp() {
         ringShards = new ArrayList<Integer>() {{ add(0); }};
    }

    @Test
    public void testSimpleUpdateAndSchedule() {
        long clock = 1234000L;
        ScheduleContext ctx = new ScheduleContext(clock, ringShards);
        Collection<SlotKey> scheduled = new ArrayList<SlotKey>();
        Collection<SlotKey> expected = new ArrayList<SlotKey>();

        ctx.setCurrentTimeMillis(clock); // +0m
        ctx.update(clock, ringShards.get(0));
        ctx.scheduleSlotsOlderThan(300000);
        Assert.assertFalse(ctx.hasScheduled());

        clock += 300000; // +5m
        ctx.setCurrentTimeMillis(clock);
        ctx.update(clock, ringShards.get(0));
        ctx.scheduleSlotsOlderThan(300000);
        // at +5m nothing should be scheduled.
        Assert.assertFalse(ctx.hasScheduled());

        clock += 300000; // +10m
        ctx.setCurrentTimeMillis(clock);
        ctx.update(clock, ringShards.get(0));
        ctx.scheduleSlotsOlderThan(300000);
        // at this point, metrics_full,4 should be scheduled, but not metrics_5m,4 even though it is older than 300s.
        // metrics_5m,4 cannot be scheduled because one of its children is scheduled.  once the child is removed and
        // scheduling is re-ran, it should appear though.  The next few lines test those assumptions.

        expected.add(SlotKey.parse("metrics_5m,4,0"));
        while (ctx.hasScheduled())
            scheduled.add(ctx.getNextScheduled());
        Assert.assertEquals(expected, scheduled);
        ctx.clearFromRunning(SlotKey.parse("metrics_5m,4,0"));

        // now, time doesn't change, but we re-evaluate slots that can be scheduled.
        ctx.scheduleSlotsOlderThan(300000);
        Assert.assertFalse(ctx.hasScheduled());
        expected.clear();
        scheduled.clear();

        // technically, we're one second away from when metrics_full,5 and metrics_5m,5 can be scheduled.
        ctx.scheduleSlotsOlderThan(300000);
        Assert.assertFalse(ctx.hasScheduled());

        clock += 1000; // 1s
        ctx.setCurrentTimeMillis(clock);
        ctx.update(clock, ringShards.get(0));
        ctx.scheduleSlotsOlderThan(300000);
        Assert.assertTrue(ctx.hasScheduled());
        Assert.assertEquals(ctx.getNextScheduled(), SlotKey.parse("metrics_5m,5,0"));
        Assert.assertFalse(ctx.hasScheduled());
        ctx.clearFromRunning(SlotKey.parse("metrics_5m,5,0"));
        ctx.scheduleSlotsOlderThan(300000);
        Assert.assertFalse(ctx.hasScheduled());


        clock += 3600000; // 1h
        ctx.setCurrentTimeMillis(clock);
        ctx.scheduleSlotsOlderThan(300000);
        Assert.assertTrue(ctx.hasScheduled());
        Assert.assertEquals(ctx.getNextScheduled(), SlotKey.parse("metrics_5m,6,0"));
        Assert.assertFalse(ctx.hasScheduled());
        ctx.clearFromRunning(SlotKey.parse("metrics_5m,6,0"));

        // time doesn't change, but now that all the 5m slots have been scheduled, we should start seeing coarser slots
        // available for scheduling.
        ctx.scheduleSlotsOlderThan(300000);
        Assert.assertTrue(ctx.hasScheduled());
        Assert.assertEquals(ctx.getNextScheduled(), SlotKey.parse("metrics_20m,1,0"));
        Assert.assertFalse(ctx.hasScheduled());
        ctx.clearFromRunning(SlotKey.parse("metrics_20m,1,0"));

        // let's finish this off...
        ctx.scheduleSlotsOlderThan(300000);
        Assert.assertTrue(ctx.hasScheduled());
        Assert.assertEquals(SlotKey.parse("metrics_60m,0,0"), ctx.getNextScheduled());
        Assert.assertFalse(ctx.hasScheduled());
        ctx.clearFromRunning(SlotKey.parse("metrics_60m,0,0"));

        ctx.scheduleSlotsOlderThan(300000);
        Assert.assertTrue(ctx.hasScheduled());
        Assert.assertEquals(SlotKey.parse("metrics_240m,0,0"), ctx.getNextScheduled());
        Assert.assertFalse(ctx.hasScheduled());
        ctx.clearFromRunning(SlotKey.parse("metrics_240m,0,0"));

        ctx.scheduleSlotsOlderThan(300000);
        Assert.assertTrue(ctx.hasScheduled());
        Assert.assertEquals(SlotKey.parse("metrics_1440m,0,0"), ctx.getNextScheduled());
        Assert.assertFalse(ctx.hasScheduled());
        ctx.clearFromRunning(SlotKey.parse("metrics_1440m,0,0"));

        ctx.scheduleSlotsOlderThan(300000);
        Assert.assertFalse(ctx.hasScheduled());
    }

    @Test
    public void test48HoursSequential() {
        long clock = 1234000L;
        ScheduleContext ctx = new ScheduleContext(clock, ringShards);
        int count = 0;

        // every 30s for 48 hrs.
        for (int i = 0; i < 48 * 60 * 60; i += 30) {
            clock += 30000;
            ctx.setCurrentTimeMillis(clock);
            ctx.update(clock, ringShards.get(0));
        }
        ctx.scheduleSlotsOlderThan(300000);

        // 5m should include slots 4 through 578.
        String prefix = "metrics_5m,";
        for (int i = 4; i <= 578; i++) {
            count++;
            SlotKey key = ctx.getNextScheduled();
            Assert.assertNotNull(key);
            Assert.assertEquals(Granularity.MIN_5, key.getGranularity());
            ctx.clearFromRunning(key);
        }
        ctx.scheduleSlotsOlderThan(300000);

        // 20m 1:143
        prefix = "metrics_20m,";
        for (int i = 1; i <= 143; i++) {
            count++;
            SlotKey key = ctx.getNextScheduled();
            Assert.assertNotNull(key);
            Assert.assertEquals(Granularity.MIN_20, key.getGranularity());
            ctx.clearFromRunning(key);
        }
        ctx.scheduleSlotsOlderThan(300000);

        // 60m 0:47
        prefix = "metrics_60m,";
        for (int i = 0; i <= 47; i++) {
            count++;
            SlotKey key = ctx.getNextScheduled();
            Assert.assertNotNull(key);
            Assert.assertEquals(Granularity.MIN_60, key.getGranularity());
            ctx.clearFromRunning(key);
        }
        ctx.scheduleSlotsOlderThan(300000);

        // 240m 0:11
        prefix = "metrics_240m,";
        for (int i = 0; i <= 11; i++) {
            count++;
            SlotKey key = ctx.getNextScheduled();
            Assert.assertNotNull(key);
            Assert.assertEquals(Granularity.MIN_240, key.getGranularity());
            ctx.clearFromRunning(key);
        }
        ctx.scheduleSlotsOlderThan(300000);

        // 1440m 0:1
        prefix = "metrics_1440m,";
        for (int i = 0; i <= 1; i++) {
            count++;
            SlotKey key = ctx.getNextScheduled();
            Assert.assertNotNull(key);
            Assert.assertEquals(Granularity.MIN_1440, key.getGranularity());
            ctx.clearFromRunning(key);
        }

        // I don't really need to test this here, but it's useful to know where the number in test48HoursInterlaced
        // comes from.
        Assert.assertEquals(575 + 143 + 48 + 12 + 2, count);
        Assert.assertFalse(ctx.hasScheduled());
    }

    // roughly the same test as test48HoursSequential, but we pull slots out in a different order. the count, and thus
    // the state, should should be the same at the end though. This mimics more closely what will happen in production
    // but will be hard to see.  A good example here is that metrics_240m,0 is scheduled right AFTER metrics_60m,3
    // (and naturally after metrics_60m,{0..2}).
    @Test
    public void test48HoursInterlaced() {
        long clock = 1234000L;
        ScheduleContext ctx = new ScheduleContext(clock, ringShards);

        int count = 0;
        // every 30s for 48 hrs.
        for (int i = 0; i < 48 * 60 * 60; i+= 30) {
            ctx.update(clock, ringShards.get(0));
            clock += 30000;
            ctx.setCurrentTimeMillis(clock);
            ctx.scheduleSlotsOlderThan(300000);
            while (ctx.hasScheduled()) {
                count++;
                SlotKey key = ctx.getNextScheduled();
                ctx.clearFromRunning(key);
            }
        }
        Assert.assertEquals(575 + 143 + 48 + 12 + 2, count);
    }

    // my purpose is to run constantly and hope for no deadlocks.
    // handy: ps auxww | grep java | grep bundle | awk '{if (NR==1) {print $2}}' | xargs kill -3
    // this test takes about 20s on my machine.
    @Test
    public void testMultithreadedness() {
        final AtomicLong clock = new AtomicLong(1234L);
        final ScheduleContext ctx = new ScheduleContext(clock.get(), ringShards);
        final CountDownLatch latch = new CountDownLatch(3);
        final AtomicInteger updateCount = new AtomicInteger(0);
        final AtomicInteger scheduleCount = new AtomicInteger(0);
        final AtomicInteger executionCount = new AtomicInteger(0);

        // 70 days of simulation.
        final int days = 35;
        final int shard = ringShards.get(0);
        final Thread update = new Thread("Update") { public void run() {
            int count = 0;
            long time = clock.get();  // saves a bit of lock contention.
            for (int i = 0; i < days * 24 * 60 * 60; i += 30) {
                if (latch.getCount() == 0) {
                    break;
                }
                time += 30000;
                clock.set(time);
                ctx.setCurrentTimeMillis(time);
                ctx.update(time, shard);
                count++;
            }
            updateCount.set(count);
            latch.countDown();
        }};

        final Thread schedule = new Thread("Scheduler") { public void run() {
            int count = 0;
            while (update.isAlive()) {
                ctx.scheduleSlotsOlderThan(300000);
                count++;
                // we sleep here because scheduling needs to happen periodically, not continually.  If there were no
                // sleep here the update thread gets starved and has a hard time completing.
                try { sleep(100L); } catch (Exception ex) {}
            }
            scheduleCount.set(count);
            latch.countDown();
        }};

        Thread consume = new Thread("Runner") { public void run() {
            int count = 0;
            while (update.isAlive()) {
                while (ctx.hasScheduled()) {
                    SlotKey key = ctx.getNextScheduled();
                    ctx.clearFromRunning(key);
                    count++;
                }
            }
            executionCount.set(count);
            latch.countDown();
        }};

        final AtomicBoolean softTimeoutReached = new AtomicBoolean(false);
        Timer timer = new Timer("Soft timeout");
        timer.schedule(new TimerTask() {
            @Override
            public void run() {
                while (latch.getCount() > 0) {
                    softTimeoutReached.set(true);
                    latch.countDown();
                }
            }
        }, MULTI_THREAD_SOFT_TIMEOUT.toMillis());

        update.start();
        schedule.start();
        consume.start();

        try {
            latch.await();
        } catch (InterruptedException ex) {
            throw new RuntimeException(ex);
        }

        Assert.assertTrue(updateCount.get() > 0);
        Assert.assertTrue(scheduleCount.get() > 0);
        Assert.assertTrue(executionCount.get() > 0);
        Assert.assertFalse("Soft timeout was reached; deadlock or thread starvation suspected", softTimeoutReached.get());
    }

    @Test
    public void testScheduleYourShardsOnly() {
        long time = 1234000;
        Collection<Integer> shardsA = Lists.newArrayList(0, 1);
        Collection<Integer> shardsB = Lists.newArrayList(2,3,4);
        ScheduleContext ctxA = new ScheduleContext(time, shardsA); // 327,345,444,467,504,543, 32,426,476,571
        ScheduleContext ctxB = new ScheduleContext(time, shardsB); // 184,320,456,526, 435,499, 20,96,107,236,429
        Collection<Integer> allShards = Lists.newArrayList(0,1,2,3,4);

        time += 1000;
        for (int shard : allShards) {
            ctxA.update(time, shard);
            ctxB.update(time, shard);
        }

        time += 500000;
        ctxA.setCurrentTimeMillis(time);
        ctxB.setCurrentTimeMillis(time);
        ctxA.scheduleSlotsOlderThan(300000);
        ctxB.scheduleSlotsOlderThan(300000);

        Assert.assertTrue(ctxA.hasScheduled());
        while (ctxA.hasScheduled()) {
            int nextScheduledShard = ctxA.getNextScheduled().getShard();
            Assert.assertTrue(shardsA.contains(nextScheduledShard));
            Assert.assertFalse(shardsB.contains(nextScheduledShard));
        }
        Assert.assertTrue(ctxB.hasScheduled());
        while (ctxB.hasScheduled()) {
            int nextScheduledShard = ctxB.getNextScheduled().getShard();
            Assert.assertTrue(shardsB.contains(nextScheduledShard));
            Assert.assertFalse(shardsA.contains(nextScheduledShard));
        }
    }
    
    @Test
    public void testRecentlyScheduledShards() {
        long now = 1234000;
        ScheduleContext ctx = new ScheduleContext(now, Util.parseShards("ALL"));
        // change the cache with one that expires after 1 sec.
        Cache<Integer, Long> expiresQuickly = CacheBuilder.newBuilder().expireAfterWrite(2, TimeUnit.SECONDS).build();
        Whitebox.setInternalState(ctx, "recentlyScheduledShards", expiresQuickly);
        Assert.assertEquals(0, ctx.getScheduledCount());
        
        // update, set time into future, poll (forced scheduling).
        int shard = 2;
        now += 1000;
        ctx.update(now, shard);
        now += 300001;
        ctx.setCurrentTimeMillis(now);
        ctx.scheduleSlotsOlderThan(300000);
        
        // shard should be recently scheduled.
        Assert.assertTrue(ctx.getRecentlyScheduledShards().contains(shard));
        
        // wait for expiration, then verify absence.
        try { Thread.sleep(2100); } catch (Exception ex) {}
        Assert.assertFalse(ctx.getRecentlyScheduledShards().contains(shard));
    }
}


File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/service/SlotStateTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.netflix.astyanax.serializers.StringSerializer;
import com.rackspacecloud.blueflood.io.serializers.SlotStateSerializer;
import com.rackspacecloud.blueflood.rollup.Granularity;
import org.junit.Assert;
import org.junit.Test;

public class SlotStateTest {
    private final long time = 123456;
    private final String s1 = "metrics_full,1,A";
    private final String s2 = "metrics_60m,1,A";
    private final String s3 = "metrics_full,1,X";

    private final SlotState ss1 = new SlotState(Granularity.FULL, 1, UpdateStamp.State.Active);
    private final SlotState ss2 = new SlotState(Granularity.MIN_60, 1, UpdateStamp.State.Running).withTimestamp(time);
    private final SlotState ss3 = new SlotState(Granularity.FULL, 1, UpdateStamp.State.Rolled).withTimestamp(time);

    @Test
    public void testStringConversion() {
        // verify active and running are the same string rep.
        // verify that toString includes timestamp...
        Assert.assertEquals(s1 + ": ", ss1.toString()); // ...unless it wasn't specified
        Assert.assertEquals(s2 + ": " + time, ss2.toString());
        Assert.assertEquals(s3 + ": " + time, ss3.toString());
    }

    @Test
    public void testEquality() {
        // verify that equality works with and without timestamp
        Assert.assertEquals(ss1, fromString(s1));
        Assert.assertEquals(ss2, fromString(s2).withTimestamp(time));
        // verify that Active and Running are considered equal
        Assert.assertEquals(new SlotState(Granularity.FULL, 1, UpdateStamp.State.Active),
                new SlotState(Granularity.FULL, 1, UpdateStamp.State.Running));
        // ... but that they are not equal to Rolled
        Assert.assertNotSame(new SlotState(Granularity.FULL, 1, UpdateStamp.State.Active),
                new SlotState(Granularity.FULL, 1, UpdateStamp.State.Rolled));
        // verify that inequality works
        SlotState timestampedState = fromString(s1).withTimestamp(time);
        Assert.assertNotSame(timestampedState, fromString(s1));
    }

    @Test
    public void testGranularity() {
        Assert.assertEquals(Granularity.FULL, fromString(s1).getGranularity());
        Assert.assertNull(fromString("FULL,1,X").getGranularity());
    }

    private SlotState fromString(String string) {
        SlotStateSerializer slotSer = SlotStateSerializer.get();
        StringSerializer stringSer = StringSerializer.get();
        return slotSer.fromByteBuffer(stringSer.toByteBuffer(string));
    }
}


File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/service/ZKBasedShardLockManagerIntegrationTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.rackspacecloud.blueflood.utils.ZookeeperTestServer;
import org.apache.curator.framework.CuratorFramework;
import org.apache.curator.framework.state.ConnectionState;
import org.junit.After;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;
import org.mockito.internal.util.reflection.Whitebox;

import java.util.Collection;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

public class ZKBasedShardLockManagerIntegrationTest {
    private Set<Integer> manageShards = null;
    private ZKBasedShardLockManager lockManager;
    private ZookeeperTestServer zkTestServer;

    @Before
    public void setUp() throws Exception {
        zkTestServer = new ZookeeperTestServer();
        zkTestServer.connect();
        manageShards = new HashSet<Integer>();
        manageShards.add(1);
        lockManager = new ZKBasedShardLockManager(zkTestServer.getZkConnect(), manageShards);
        Assert.assertTrue("Zookeeper connection is needed.", lockManager.waitForZKConnections(10));
        lockManager.prefetchLocks();
    }

    @After
    public void tearDown() throws Exception {
        lockManager.shutdownUnsafe();
        zkTestServer.shutdown();
    }

    @Test
    public void testAddShard() throws Exception {
        final int shard = 20;

        // internal lock object should not be present.
        Assert.assertNull(lockManager.getLockUnsafe(shard));

        // after adding, it should be present.
        lockManager.addShard(shard);
        Assert.assertNotNull(lockManager.getLockUnsafe(shard));  // assert that we have a lock object for shard "20"

        // but we cannot do work until the lock is acquired.
        Assert.assertFalse(lockManager.canWork(shard));

        // let the lock be acquired.
        lockManager.forceLockScavenge(); // lock will attempt.
        lockManager.waitForQuiesceUnsafe();

        // verify can work and lock is held.
        Assert.assertTrue(lockManager.canWork(shard));
        Assert.assertTrue(lockManager.holdsLockUnsafe(shard));

        lockManager.releaseLockUnsafe(shard);
    }

    @Test
    public void testRemoveShard() {
        final int shard = 1;
        Assert.assertTrue(lockManager.getLockUnsafe(shard) != null);  // assert that we have a lock object for shard "20"
        Assert.assertTrue(lockManager.canWork(shard));
        Assert.assertTrue(lockManager.holdsLockUnsafe(shard));

        // remove the shard, should also remove the lock.
        lockManager.removeShard(1);
        lockManager.waitForQuiesceUnsafe();

        Assert.assertFalse(lockManager.holdsLockUnsafe(shard));
        Assert.assertFalse(lockManager.canWork(shard));

        Assert.assertNull(lockManager.getLockUnsafe(shard)); // assert that we don't have a lock object for shard "1"
    }

    @Test
    public void testHappyCaseLockAcquireAndRelease() throws Exception {
        final Integer shard = 1;
        Assert.assertTrue(lockManager.canWork(shard));

        // Check if lock is acquired
        Assert.assertTrue(lockManager.holdsLockUnsafe(shard));
        Assert.assertTrue(lockManager.releaseLockUnsafe(shard));

        // Check we don't hold the lock
        Assert.assertFalse(lockManager.canWork(shard));
        Assert.assertFalse(lockManager.holdsLockUnsafe(shard));

        lockManager.releaseLockUnsafe(shard);
    }

    @Test
    public void testZKConnectionLoss() throws Exception {
        final Integer shard = 1;
        Assert.assertTrue(lockManager.canWork(shard));
        lockManager.waitForQuiesceUnsafe();

        // Check if lock is acquired
        Assert.assertTrue(lockManager.holdsLockUnsafe(shard));

        // simulate connection loss
        lockManager.stateChanged((CuratorFramework)Whitebox.getInternalState(lockManager, "client"), ConnectionState.LOST);

        // Check we don't hold the lock, but we should still be able to work.
        Assert.assertFalse(lockManager.holdsLockUnsafe(shard)); // lock is technically lost.

        // Check that no locks are held
        Collection<Integer> heldLocks = lockManager.getHeldShards();
        Assert.assertTrue(heldLocks.isEmpty());

        // Check all locks are in state LockState.ERROR
        Map<Integer, ZKBasedShardLockManager.Lock> locks = (Map<Integer, ZKBasedShardLockManager.Lock>) Whitebox.getInternalState(lockManager, "locks");
        for (Map.Entry<Integer, ZKBasedShardLockManager.Lock> lockEntry : locks.entrySet()) {
            Assert.assertTrue(lockEntry.getValue().getLockState() == ZKBasedShardLockManager.LockState.ERROR);
        }

        // but we can still do work.
        for (Map.Entry<Integer, ZKBasedShardLockManager.Lock> lockEntry : locks.entrySet()) {
            Assert.assertTrue(lockManager.canWork(shard));
        }

        // Simulate connection re-establishment
        lockManager.stateChanged((CuratorFramework)Whitebox.getInternalState(lockManager, "client"), ConnectionState.RECONNECTED);

        // Force lock scavenge
        lockManager.forceLockScavenge();

        // Check all locks state. They could be UNKNOWN or ACQUIRED (ultra-fast ZK).
        for (Map.Entry<Integer, ZKBasedShardLockManager.Lock> lockEntry : locks.entrySet()) {
            Assert.assertTrue(lockEntry.getValue().getLockState() == ZKBasedShardLockManager.LockState.UNKNOWN
                    || lockEntry.getValue().getLockState() == ZKBasedShardLockManager.LockState.ACQUIRED);
        }

        lockManager.releaseLockUnsafe(shard);
    }

    @Test
    public void testDuelingManagers() throws Exception {
        final int shard = 1;
        ZKBasedShardLockManager otherManager = new ZKBasedShardLockManager(zkTestServer.getZkConnect(), manageShards);
        Assert.assertTrue("Zookeeper connection is needed.", otherManager.waitForZKConnections(10));
        otherManager.prefetchLocks();
        otherManager.waitForQuiesceUnsafe();

        // first manager.
        Assert.assertTrue(lockManager.canWork(shard));
        lockManager.waitForQuiesceUnsafe();
        Assert.assertTrue(lockManager.holdsLockUnsafe(shard));

        // second manager could not acquire lock.
        Assert.assertFalse(otherManager.canWork(shard));
        Assert.assertFalse(otherManager.holdsLockUnsafe(shard));
        Assert.assertFalse(otherManager.canWork(shard));

        // force first manager to give up the lock.
        lockManager.setMinLockHoldTimeMillis(0);
        lockManager.setLockDisinterestedTimeMillis(300000);
        lockManager.forceLockScavenge();
        lockManager.waitForQuiesceUnsafe();
        Assert.assertFalse(lockManager.canWork(shard));
        Assert.assertFalse(lockManager.holdsLockUnsafe(shard));

        // see if second manager picks it up.
        otherManager.setLockDisinterestedTimeMillis(0);
        otherManager.forceLockScavenge();
        otherManager.waitForQuiesceUnsafe();
        Assert.assertTrue(otherManager.canWork(shard));
        Assert.assertTrue(otherManager.holdsLockUnsafe(shard));

        otherManager.shutdownUnsafe();
    }

    @Test
    public void testConviction() throws Exception {
        for (int shard : manageShards) {
            Assert.assertTrue(lockManager.canWork(shard));
            Assert.assertTrue(lockManager.holdsLockUnsafe(shard));
        }

        // force locks to be dropped.
        lockManager.setMinLockHoldTimeMillis(0);
        lockManager.forceLockScavenge();
        lockManager.waitForQuiesceUnsafe();

        // should not be able to work.
        for (int shard : manageShards) {
            Assert.assertFalse(lockManager.holdsLockUnsafe(shard));
            Assert.assertFalse(lockManager.canWork(shard));
        }

        // see if locks are picked back up.
        lockManager.setMinLockHoldTimeMillis(10000);
        lockManager.setLockDisinterestedTimeMillis(0);
        lockManager.forceLockScavenge();
        lockManager.waitForQuiesceUnsafe();
        for (int shard : manageShards) {
            Assert.assertTrue(lockManager.canWork(shard));
            Assert.assertTrue(lockManager.holdsLockUnsafe(shard));
        }
    }
}


File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/types/AverageTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import org.junit.Assert;
import org.junit.Test;

import java.io.IOException;

public class AverageTest {
    private static final double UNACCEPTABLE_DIFFERENCE = 0.000000001d;
    
    private static long[] LONG_SRC = new long[]{
        3,456,6,34,5,8,345,56,354,345,647,89,567,354,234,36,675,8,8,456,345,36,745,56,6786,795,687,456,345,346,
        456,332,435,346,34535665576L,4,346,4356,4,547,3456,345,37,568,3456,3426,3475,35,745,86,3456,346,3457,376,
        34,634,653,7,54687,4576,346,23,65,346347,457,45,75,67,3456,4356,345,73,445745,67457645,74,5754,6745,7457,
        457,3456,34,634,65,3456,347,4567,45,86756,865,7856,8745,66,345,634,5634,643,56,457,4567,54,7654,67,436534,56,346,
        34,53465,456,75467,4567,4576,45764357645L,673465,3456,3457,4567,45674567345634654L,756456,745674356345L,645367456L
    };
    
    @Test    
    public void testLongAverage() {
        Average avg = new Average();
        avg.add(2L);
        avg.add(4L);
        avg.add(4L);
        Assert.assertEquals(3L, avg.toLong());
    }
    
    @Test
    public void testDoubleAverage() {
        Average avg = new Average();
        avg.add(2.0D);
        avg.add(4.0D);
        avg.add(4.0D);
        Assert.assertEquals(3.3333333333333335D, avg.toDouble(), 0);
        
        // this a double, so average will be off due to rounding.
        Assert.assertEquals(3.3333333333333335D, avg.toDouble(), 0);
    }
   
    @Test
    public void testDoubleAveragingApproaches() {
        // standard average.
        double sum = 0;
        for (double d : TestData.DOUBLE_SRC) 
            sum += d;
        // avg = sum / src.length;
        
        // now compute using tugger. only possibility of overflow is in count.
        double average = 0;
        long count = 0;
        for (double v : TestData.DOUBLE_SRC)
            average += (v - average) / ++count;
        
        assert Math.abs(average - sum/TestData.DOUBLE_SRC.length) < 0.000001; // close enough?
        
    }
        
    @Test
    public void testLongAveragingApproaches() {
        // standard average.
        long sum = 0;
        for (long l : LONG_SRC)
            sum += l;
        // avg = sum / src.length;
       
        // now compute using mean+remainder method.
        // this approach is good to use if you're worried about overflow.  It's problem is that it is computationally
        // expensive.
        long mean = 0, remainder = 0;
        for (long v : LONG_SRC) {
            mean += v / LONG_SRC.length;
            remainder += v % LONG_SRC.length;
            mean += remainder / LONG_SRC.length;
            remainder %= LONG_SRC.length;
        }
        assert mean == sum/LONG_SRC.length;  
        
        // but what if we don't know src.length ahead of time?
        long rmean = 0, count = 0;
        remainder = 0;
        for (long v : LONG_SRC) {
            ++count;
            rmean += (v + remainder - rmean) / count;
            remainder = (v + remainder - rmean) % count;
        }
        Assert.assertTrue((double) Math.abs(rmean - mean) / (double) mean < UNACCEPTABLE_DIFFERENCE); // should be really close to the true mean.
    }
    
    @Test
    public void testFloatingRollup() {
        Average baseline = new Average();
        for (int i = 0; i < 1234; i++) 
            baseline.add(7d);
        for (int i = 0; i < 2565; i++)
            baseline.add(11d);
        for (int i = 0; i < 767; i++)
            baseline.add(17d);
        
        Average rollup = new Average();
        rollup.addBatch(7d, 1234);
        rollup.addBatch(11d, 2565);
        rollup.addBatch(17d, 767);
        
        Assert.assertTrue(Math.abs(rollup.toDouble() - baseline.toDouble()) < UNACCEPTABLE_DIFFERENCE);
    }
    
    @Test
    public void testLongRollup() {
        Average baseline = new Average();
        for (int i = 0; i < 1234; i++) 
            baseline.add(7L);
        for (int i = 0; i < 2565; i++)
            baseline.add(11L);
        for (int i = 0; i < 767; i++)
            baseline.add(17L);
        
        Average rollup = new Average();
        rollup.addBatch(7L, 1234);
        rollup.addBatch(11L, 2565);
        rollup.addBatch(17L, 767);
        
        Assert.assertEquals(baseline.toLong(), rollup.toLong());
    }

    @Test
    public void testAddRollup() throws IOException{
        Average avg = new Average(1, new Double(3.0));
        Points<SimpleNumber> data = new Points<SimpleNumber>();
        data.add(new Points.Point<SimpleNumber>(123456789L, new SimpleNumber(0.0)));
        data.add(new Points.Point<SimpleNumber>(123456770L, new SimpleNumber(0.0)));
        BasicRollup basicRollup = BasicRollup.buildRollupFromRawSamples(data);

        Assert.assertEquals(3.0, avg.toDouble(), 0);
        avg.handleRollupMetric(basicRollup);
        Assert.assertEquals(1.0, avg.toDouble(), 0);

        avg = new Average(1, new Long(3));
        Assert.assertEquals(3, avg.toLong());
        data =  new Points<SimpleNumber>();
        data.add(new Points.Point<SimpleNumber>(123456789L, new SimpleNumber(0)));
        data.add(new Points.Point<SimpleNumber>(123456770L, new SimpleNumber(0)));
        basicRollup = BasicRollup.buildRollupFromRawSamples(data);
        avg.handleRollupMetric(basicRollup);
        Assert.assertEquals(1, avg.toLong());
    }

    @Test
    public void testConstructorUnsupportedVariableType() {
       boolean failed = false;
       try {
           Average avg = new Average(1, new String("test"));
           Assert.fail();
       }
       catch (RuntimeException e) {
           Assert.assertEquals("Unexpected type: java.lang.String", e.getMessage());
           failed = true;
       }

       Assert.assertEquals(true, failed);
    }
}

File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/types/HistogramRollupTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import com.bigml.histogram.Bin;
import com.bigml.histogram.SimpleTarget;
import org.junit.Assert;
import org.junit.Test;

import java.util.*;

public class HistogramRollupTest {

    @Test
    public void testSimpleHistogramFromRawSamples() throws Exception {
        Points<SimpleNumber> points = new Points<SimpleNumber>();
        long startTime = 12345678L;

        for (double val : TestData.DOUBLE_SRC) {
            points.add(new Points.Point<SimpleNumber>(startTime++, new SimpleNumber(val)));
        }

        HistogramRollup histogramRollup = HistogramRollup.buildRollupFromRawSamples(points);
        Assert.assertTrue(histogramRollup.getBins().size() <= HistogramRollup.MAX_BIN_SIZE);

        double count = 0;
        for (Bin<SimpleTarget> bin :histogramRollup.getBins()) {
            count += bin.getCount();
        }

        Assert.assertEquals(TestData.DOUBLE_SRC.length, (int) count);
    }

    @Test
    public void testMergeHistogramRollups() throws Exception {
        long startTime = 12345678L;
        int sampleSize = 10;
        Random rand = new Random();

        List<Points<SimpleNumber>> pointsList = new ArrayList<Points<SimpleNumber>>();
        Points<SimpleNumber> points = new Points<SimpleNumber>();
        pointsList.add(points);

        for (int i = 0; i < TestData.DOUBLE_SRC.length; i++) {
            if (i > 0 && (i % sampleSize) == 0) {
                points = new Points<SimpleNumber>();
                pointsList.add(points);
            }

            points.add(new Points.Point<SimpleNumber>(startTime + i, new SimpleNumber(TestData.DOUBLE_SRC[i])));
        }

        List<HistogramRollup> histogramRollups = new ArrayList<HistogramRollup>();
        for (Points<SimpleNumber> item : pointsList) {
            HistogramRollup histogramRollup = HistogramRollup.buildRollupFromRawSamples(item);
            histogramRollups.add(histogramRollup);
        }

        // Assert that there is more than 1 histogram rollup to test merging.
        Assert.assertTrue(histogramRollups.size() > 1);

        int first = rand.nextInt(histogramRollups.size());
        int second = rand.nextInt(histogramRollups.size());
        while (second == first) {
            second = rand.nextInt(histogramRollups.size());
        }

        Points<HistogramRollup> rollups = new Points<HistogramRollup>();
        rollups.add(new Points.Point<HistogramRollup>(startTime, histogramRollups.get(first)));
        rollups.add(new Points.Point<HistogramRollup>(startTime + 1, histogramRollups.get(second)));
        HistogramRollup merged = HistogramRollup.buildRollupFromRollups(rollups);

        Assert.assertTrue(merged.getBins().size() <= histogramRollups.get(first).getBins().size() +
                histogramRollups.get(second).getBins().size());
    }
}


File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/types/MaxValueTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import com.rackspacecloud.blueflood.rollup.Granularity;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;

import java.io.IOException;

public class MaxValueTest {
    private MaxValue max;

    @Before
    public void setUp() {
        max = new MaxValue();
    }

    @Test
    public void testMaxValueForDoubleMetrics() throws IOException {
        for (double val : TestData.DOUBLE_SRC) {
            max.handleFullResMetric(val);
        }
        Assert.assertTrue(max.isFloatingPoint());
        Assert.assertEquals(90.48232472545334, max.toDouble(), 0);
    }

    @Test
    public void testMaxValueForLongMetrics() throws IOException {
        for (long val : TestData.LONG_SRC) {
            max.handleFullResMetric(val);
        }
        Assert.assertTrue(!max.isFloatingPoint());
        Assert.assertEquals(94730802834L, max.toLong());
    }

    @Test
    public void testMaxValueWithMixedTypes() throws IOException {
        max.handleFullResMetric(6L);    // long
        max.handleFullResMetric(6.0);   // double
        max.handleFullResMetric(1);     // integer
        max.handleFullResMetric(99.0);  // double

        // The max value in the input set is 99.0 which is of type double
        Assert.assertTrue(max.isFloatingPoint());
        // Assert that indeed 99.0 is the maximum value
        Assert.assertEquals(99.0, max.toDouble(), 0);
    }

    @Test
    public void testRollupMax() throws IOException {
        BasicRollup basicRollup1 = new BasicRollup();
        BasicRollup basicRollup2 = new BasicRollup();
        BasicRollup basicRollup3 = new BasicRollup();
        BasicRollup basicRollup4 = new BasicRollup();

        BasicRollup netBasicRollup;

        Points<SimpleNumber> input = new Points<SimpleNumber>();
        input.add(new Points.Point<SimpleNumber>(123456789L, new SimpleNumber(5L)));
        input.add(new Points.Point<SimpleNumber>(123456790L, new SimpleNumber(1L)));
        input.add(new Points.Point<SimpleNumber>(123456791L, new SimpleNumber(7L)));
        basicRollup1 = BasicRollup.buildRollupFromRawSamples(input);

        input = new Points<SimpleNumber>();
        input.add(new Points.Point<SimpleNumber>(123456789L, new SimpleNumber(9L)));
        input.add(new Points.Point<SimpleNumber>(123456790L, new SimpleNumber(0L)));
        input.add(new Points.Point<SimpleNumber>(123456791L, new SimpleNumber(1L)));
        basicRollup2 = BasicRollup.buildRollupFromRawSamples(input);

        input = new Points<SimpleNumber>();
        input.add(new Points.Point<SimpleNumber>(123456789L, new SimpleNumber(2.14d)));
        input.add(new Points.Point<SimpleNumber>(123456790L, new SimpleNumber(1.14d)));
        basicRollup3 = BasicRollup.buildRollupFromRawSamples(input);

        input = new Points<SimpleNumber>();
        input.add(new Points.Point<SimpleNumber>(123456789L, new SimpleNumber(3.14d)));
        input.add(new Points.Point<SimpleNumber>(123456790L, new SimpleNumber(5.67d)));
        basicRollup4 = BasicRollup.buildRollupFromRawSamples(input);

        // handle homegenous metric types and see if we get the right max

        // type long
        Points<BasicRollup> rollups = new Points<BasicRollup>();
        rollups.add(new Points.Point<BasicRollup>(123456789L, basicRollup1));
        rollups.add(new Points.Point<BasicRollup>(123456790L, basicRollup2));
        netBasicRollup = BasicRollup.buildRollupFromRollups(rollups);

        MaxValue max = netBasicRollup.getMaxValue();
        Assert.assertTrue(!max.isFloatingPoint());
        Assert.assertEquals(9L, max.toLong());

        // type double
        rollups = new Points<BasicRollup>();
        rollups.add(new Points.Point<BasicRollup>(123456789L, basicRollup3));
        rollups.add(new Points.Point<BasicRollup>(123456790L, basicRollup4));
        netBasicRollup = BasicRollup.buildRollupFromRollups(rollups);

        max = netBasicRollup.getMaxValue();
        Assert.assertTrue(max.isFloatingPoint());
        Assert.assertEquals(5.67d, max.toDouble(), 0);

        // handle heterogenous metric types and see if we get the right max
        rollups = new Points<BasicRollup>();
        rollups.add(new Points.Point<BasicRollup>(123456789L, basicRollup2));
        rollups.add(new Points.Point<BasicRollup>(123456790L, basicRollup3));
        netBasicRollup = BasicRollup.buildRollupFromRollups(rollups);

        max = netBasicRollup.getMaxValue();
        Assert.assertTrue(!max.isFloatingPoint());
        Assert.assertEquals(9L, max.toLong());
    }
}

File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/types/MetricTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import com.rackspacecloud.blueflood.utils.TimeValue;
import org.junit.Assert;
import org.junit.Test;

import java.util.concurrent.TimeUnit;

import static org.junit.Assert.fail;

public class MetricTest {

    @Test
    public void testMetricType() {
        Locator locator = Locator.createLocatorFromPathComponents("tenantId", "metricName");

        Metric metric = new Metric(locator, "Foo", System.currentTimeMillis(), new TimeValue(5, TimeUnit.HOURS), "Unknown");
        Assert.assertEquals("S", metric.getDataType().toString());
        Assert.assertTrue(metric.getDataType().equals(DataType.STRING));
        Assert.assertTrue("Metric should be string", metric.isString());
        Assert.assertTrue(DataType.isKnownMetricType(metric.getDataType()));

        metric = new Metric(locator, 1234567L, System.currentTimeMillis(), new TimeValue(5, TimeUnit.HOURS), "Unknown");
        Assert.assertEquals("N", metric.getDataType().toString());
        Assert.assertTrue(metric.getDataType().equals(DataType.NUMERIC));
        Assert.assertTrue("Metric should be numeric", metric.isNumeric());
        Assert.assertTrue(DataType.isKnownMetricType(metric.getDataType()));

        metric = new Metric(locator, 1234567.678, System.currentTimeMillis(), new TimeValue(5, TimeUnit.HOURS), "Unknown");
        Assert.assertEquals("N", metric.getDataType().toString());
        Assert.assertTrue(metric.getDataType().equals(DataType.NUMERIC));
        Assert.assertTrue("Metric should be numeric", metric.isNumeric());
        Assert.assertTrue(DataType.isKnownMetricType(metric.getDataType()));

        metric = new Metric(locator, 1234567, System.currentTimeMillis(), new TimeValue(5, TimeUnit.HOURS), "Unknown");
        Assert.assertEquals("N", metric.getDataType().toString());
        Assert.assertTrue(metric.getDataType().equals(DataType.NUMERIC));
        Assert.assertTrue("Metric should be numeric", metric.isNumeric());
        Assert.assertTrue(DataType.isKnownMetricType(metric.getDataType()));

        metric = new Metric(locator, false, System.currentTimeMillis(), new TimeValue(5, TimeUnit.HOURS), "Unknown");
        Assert.assertEquals("B", metric.getDataType().toString());
        Assert.assertTrue(metric.getDataType().equals(DataType.BOOLEAN));
        Assert.assertTrue("Metric should be boolean", metric.isBoolean());
        Assert.assertTrue(DataType.isKnownMetricType(metric.getDataType()));

        DataType failType = new DataType("X");
        Assert.assertFalse(DataType.isKnownMetricType(failType));
    }

    @Test
    public void testTTL() {
        Locator locator = Locator.createLocatorFromPathComponents("tenantId", "metricName");
        Metric metric = new Metric(locator, "Foo", System.currentTimeMillis(), new TimeValue(5, TimeUnit.HOURS), "Unknown");

        try {
            metric.setTtl(new TimeValue(Long.MAX_VALUE, TimeUnit.SECONDS));
            fail();
        } catch (Exception e) {
            Assert.assertTrue(e instanceof RuntimeException);
        }
    }

    @Test
    public void testMetricValueTypeDetectors() {
        Object metricValueBool = false;

        Assert.assertTrue(DataType.isBooleanMetric(metricValueBool));
        Assert.assertTrue(!DataType.isNumericMetric(metricValueBool));
        Assert.assertTrue(!DataType.isStringMetric(metricValueBool));

        Object metricValueNum = 1234567L;

        Assert.assertTrue(!DataType.isBooleanMetric(metricValueNum));
        Assert.assertTrue(DataType.isNumericMetric(metricValueNum));
        Assert.assertTrue(!DataType.isStringMetric(metricValueNum));

        Object metricValueStr = "Foo";

        Assert.assertTrue(!DataType.isBooleanMetric(metricValueStr));
        Assert.assertTrue(!DataType.isNumericMetric(metricValueStr));
        Assert.assertTrue(DataType.isStringMetric(metricValueStr));
    }
    
    @Test
    public void testGenericStatSet() {
        Average average = new Average(10, 30);
        AbstractRollupStat.set(average, 50);
        Assert.assertFalse(average.isFloatingPoint());
        
        // set as float (should get cast to double).
        AbstractRollupStat.set(average, 45f);
        // isFloatingPoint should have flipped.
        Assert.assertTrue(average.isFloatingPoint());
    }
}


File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/types/MinValueTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;

import java.io.IOException;

public class MinValueTest {
    private MinValue min;

    @Before
    public void setUp() {
        min = new MinValue();
    }

    @Test
    public void testMinValueForDoubleMetrics() throws IOException {
        for (double val : TestData.DOUBLE_SRC) {
            min.handleFullResMetric(val);
        }
        Assert.assertTrue(min.isFloatingPoint());
        Assert.assertEquals(0.0, min.toDouble(), 0);
    }

    @Test
    public void testMinValueForLongMetrics() throws IOException {
        for (long val : TestData.LONG_SRC) {
            min.handleFullResMetric(val);
        }
        Assert.assertTrue(!min.isFloatingPoint());
        Assert.assertEquals(12L, min.toLong());
    }

    @Test
    public void testMinValueWithMixedTypes() throws IOException {
        min.handleFullResMetric(6L);    // long
        min.handleFullResMetric(6.0);   // double
        min.handleFullResMetric(1);     // integer
        min.handleFullResMetric(99.0);  // double

        // The minimum value in the input set is 1 which is of type Long
        Assert.assertTrue(!min.isFloatingPoint());
        // Assert that indeed 1 is the minimum value
        Assert.assertEquals(1, min.toLong());
    }

    @Test
    public void testRollupMin() throws IOException {
        BasicRollup basicRollup1 = new BasicRollup();
        BasicRollup basicRollup2 = new BasicRollup();
        BasicRollup basicRollup3 = new BasicRollup();
        BasicRollup basicRollup4 = new BasicRollup();

        BasicRollup netBasicRollup;

        Points<SimpleNumber> input = new Points<SimpleNumber>();
        input.add(new Points.Point<SimpleNumber>(123456789L, new SimpleNumber(5L)));
        input.add(new Points.Point<SimpleNumber>(123456790L, new SimpleNumber(1L)));
        input.add(new Points.Point<SimpleNumber>(123456791L, new SimpleNumber(7L)));
        basicRollup1 = BasicRollup.buildRollupFromRawSamples(input);

        input = new Points<SimpleNumber>();
        input.add(new Points.Point<SimpleNumber>(123456789L, new SimpleNumber(9L)));
        input.add(new Points.Point<SimpleNumber>(123456790L, new SimpleNumber(0L)));
        input.add(new Points.Point<SimpleNumber>(123456791L, new SimpleNumber(1L)));
        basicRollup2 = BasicRollup.buildRollupFromRawSamples(input);

        Points<BasicRollup> rollups = new Points<BasicRollup>();
        BasicRollup temp = new BasicRollup();
        temp.getMinValue().setDoubleValue(2.14);
        rollups.add(new Points.Point<BasicRollup>(123456789L, temp));
        temp.getMinValue().setDoubleValue(1.14);
        rollups.add(new Points.Point<BasicRollup>(123456790L, temp));
        basicRollup3 = BasicRollup.buildRollupFromRollups(rollups);

        rollups = new Points<BasicRollup>();
        temp = new BasicRollup();
        temp.getMinValue().setDoubleValue(3.14);
        rollups.add(new Points.Point<BasicRollup>(123456789L, temp));
        temp.getMinValue().setDoubleValue(5.67);
        rollups.add(new Points.Point<BasicRollup>(123456790L, temp));
        basicRollup4 = BasicRollup.buildRollupFromRollups(rollups);

        // handle homegenous metric types and see if we get the right min

        // type long
        rollups = new Points<BasicRollup>();
        rollups.add(new Points.Point<BasicRollup>(123456789L, basicRollup1));
        rollups.add(new Points.Point<BasicRollup>(123456790L, basicRollup2));
        netBasicRollup = BasicRollup.buildRollupFromRollups(rollups);

        MinValue min = netBasicRollup.getMinValue();
        Assert.assertTrue(!min.isFloatingPoint());
        Assert.assertEquals(0L, min.toLong());

        // type double
        rollups = new Points<BasicRollup>();
        rollups.add(new Points.Point<BasicRollup>(123456789L, basicRollup3));
        rollups.add(new Points.Point<BasicRollup>(123456790L, basicRollup4));
        netBasicRollup = BasicRollup.buildRollupFromRollups(rollups);

        min = netBasicRollup.getMinValue();
        Assert.assertTrue(min.isFloatingPoint());
        Assert.assertEquals(1.14d, min.toDouble(), 0);

        // handle heterogenous metric types and see if we get the right min
        rollups = new Points<BasicRollup>();
        rollups.add(new Points.Point<BasicRollup>(123456789L, basicRollup2));
        rollups.add(new Points.Point<BasicRollup>(123456790L, basicRollup3));
        netBasicRollup = BasicRollup.buildRollupFromRollups(rollups);

        min = netBasicRollup.getMinValue();
        Assert.assertTrue(!min.isFloatingPoint());
        Assert.assertEquals(0L, min.toLong());
    }
}

File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/types/SimpleNumberTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import org.junit.Assert;
import org.junit.Test;

public class SimpleNumberTest {
    @Test
    public void testSimpleNumberWithVariousTypes() {
        Object testValue = new Integer(4);
        SimpleNumber simpleNumber = new SimpleNumber(testValue);
        Assert.assertEquals(testValue, simpleNumber.getValue());

        testValue = new Double(5.0);
        simpleNumber = new SimpleNumber(testValue);
        Assert.assertEquals(testValue, simpleNumber.getValue());

        testValue = new Long(5L);
        simpleNumber = new SimpleNumber(testValue);
        Assert.assertEquals(testValue, simpleNumber.getValue());

        // make sure primitives work too
        testValue = 4;
        simpleNumber = new SimpleNumber(testValue);
        Assert.assertEquals(testValue, simpleNumber.getValue());
    }

}


File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/types/TestData.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

public class TestData {
    public static double[] DOUBLE_SRC = new double[]{
            34.35127496305467,1.6297592048475056,25.95193036484187,51.88399281273119,59.749697415438874,
            34.3524838198138,71.21824331609369,90.48232472545334,28.817589136395604,1.7289259766330447,
            0.0,2.3264083805840965,28.365153399079148,52.755777861131406,62.00253840347595,
            74.99831363612256,38.68719328434047,15.126647226438775,31.584178915833075,80.21418471951392,
            53.60928771432326,0.12466336825047719,10.467816019160646,7.800240407084718,21.424348218211403,
            6.394552472683012,19.148986991876264,7.598718790192102,70.30279138077479,2.71305763607908,
            48.48284663157681,24.797052760599815,35.43562082409461,8.484969317745922,43.55488003153072,
            12.50148445454442,33.777082969206454,21.016714137842666,70.03797074035487,18.33947969839176,
            38.59057608715806,52.424583030685035,32.72209615294738,25.488615948827068,52.15048910841228,
            9.995536230373975,69.44877788948843,22.323403696528143,20.13784665268544,10.985379102474601,
            22.61137325117517,55.42191583996447,1.1417246917182027,17.9639283491758,52.388760729856564,
            41.88604561234169,54.44240540615532,14.957334217909759,69.09714966674099,4.772630418607564,
            28.83933064086059,56.92546368650749,0.9637247105211963,3.8069545779936442,0.14060186475583603,
            7.886870892277215,7.108601018241192,24.410529593230205,19.327478005874152,16.50470921281051,
            21.550769577887657,1.7642866952922873,55.07447189006772,57.123465723498605,10.851733006988633,
            60.104696026333805,2.8843780875904312,6.773105818763301,35.17503427394974,47.97561513913516,
            33.36060635062417,46.46300916330942,44.56036803146305,5.977610130344117,43.54949712567326,
            1.4180415942814577,45.945791758794115,54.43981785347247,30.911433072833322,82.45747267678144,
            7.382686310026541,1.3106811310712574,62.20333021633387,30.603638684728587,7.432820883420275,
            18.667638744061538,4.530083990116902,23.394560941778387,66.92549890398803,44.95856716096983,
            18.685493086523586,1.2066778658055222,1.8558620938758548,1.1967372131142282,44.903386569263894,
            52.63916179985974,0.48110137406239595,26.67541509388795,29.424570271250598,3.0765458411621367,
            23.01426148043091,57.95187459465202,10.254376467648061,0.6155160531401506,0.3179647698528931,
            3.750569964666618,2.1572270560404125,1.954844149456163,42.97451034961871,81.12678962510779,
            13.629066870665827,61.42130888518986,1.172370437525282,0.0
    };

    protected static long[] LONG_SRC = new long[] {
            32204L, 94730802834L, 12L, 18905L, 64465464L
    };
}


File: blueflood-core/src/test/java/com/rackspacecloud/blueflood/types/VarianceTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.types;

import org.apache.commons.lang.ArrayUtils;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class VarianceTest {
    private Variance variance = null;
    private static final double ERROR_TOLERANCE = 0.01;   // in %

    public static double[] DOUBLE_SRC_REALLY_HIGH = new double[]{Long.MAX_VALUE, Long.MAX_VALUE - 1, Long.MAX_VALUE};

    public static double[] ZEROS = new double[] {0, 0, 0, 0};

    @Before
    public void setUp() {
        variance = new Variance();
    }

    @Test
    public void testFullResMetricVariance() {

        // Our implementation for variance (welford one pass)
        for (double val : TestData.DOUBLE_SRC) {
            variance.handleFullResMetric(val);
        }

        Results result = new Results();
        result.expectedVariance = computeRawVariance(TestData.DOUBLE_SRC);
        result.computedVariance = variance.toDouble();


        double delta = (result.computedVariance - result.expectedVariance);

        double errorPercent = 0.0;
        if (delta != 0) {
            errorPercent = delta/result.expectedVariance * 100;
        }
        Assert.assertTrue(Math.abs(errorPercent) < ERROR_TOLERANCE);
    }

    @Test
    public void testFullResMetricVarianceForZeros() {
        // Our implementation for variance (welford one pass)
        for (double val : ZEROS) {
            variance.handleFullResMetric(val);
        }

        Results result = new Results();
        result.expectedVariance = computeRawVariance(ZEROS);
        result.computedVariance = variance.toDouble();


        double delta = (result.computedVariance - result.expectedVariance);

        double errorPercent = 0.0;
        if (delta != 0) {
            errorPercent = delta/result.expectedVariance * 100;
        }
        Assert.assertTrue(Math.abs(errorPercent) < ERROR_TOLERANCE);
    }

    @Test
    public void testFullResMetricVarianceForOneSample() {
        variance.handleFullResMetric(3.14);
        Assert.assertEquals(0.0, variance.toDouble(), 0);
    }

    @Test
    public void testFullResMetricVarianceNumericalStability() {
        // Our implementation for variance (welford one pass)
        for (double val : DOUBLE_SRC_REALLY_HIGH) {
            variance.handleFullResMetric(val);
        }

        Results result = new Results();
        result.expectedVariance = computeRawVariance(DOUBLE_SRC_REALLY_HIGH);
        result.computedVariance = variance.toDouble();


        double delta = (result.computedVariance - result.expectedVariance);

        double errorPercent = 0.0;
        if (delta != 0) {
            errorPercent = delta/result.expectedVariance * 100;
        }
        Assert.assertTrue(Math.abs(errorPercent) < ERROR_TOLERANCE);
    }

    @Test
    public void testRollupVariance() throws IOException {
        int size = TestData.DOUBLE_SRC.length;

        int GROUPS = 4;

        // split the input samples into 4 groups
        int windowSize = size/GROUPS;
        double[][] input = new double[GROUPS][windowSize]; // 4 groups of 31 samples each

        int count = 0; int i = 0; int j = 0;
        for (double val : TestData.DOUBLE_SRC) {
            input[i][j] = val;
            j++; count++;

            if (count % windowSize == 0) {
                i++;
                j = 0;
            }
        }

        // Compute variance for the 4 groups [simulate 5 MIN rollups from raw points]
        List<BasicRollup> basicRollups = new ArrayList<BasicRollup>();
        List<Results> resultsList = new ArrayList<Results>();
        for (i = 0; i < GROUPS; i++) {
            Results r = new Results();

            Points<SimpleNumber> inputSlice = new Points<SimpleNumber>();
            int timeOffset = 0;
            for (double val : input[i]) {
                inputSlice.add(new Points.Point<SimpleNumber>(123456789L + timeOffset++, new SimpleNumber(val)));
            }

            BasicRollup basicRollup = BasicRollup.buildRollupFromRawSamples(inputSlice);

            r.expectedVariance = computeRawVariance(input[i]);
            r.computedVariance = basicRollup.getVariance().toDouble();
            r.expectedAverage = computeRawAverage(input[i]);
            r.computedAverage = basicRollup.getAverage().toDouble();
            basicRollups.add(basicRollup);
            resultsList.add(r);
        }

        // First check if individual rollup variances and averages are close to raw variance & average for the window
        // of samples
        for (i = 0; i < GROUPS; i++) {
            Results result = resultsList.get(i);

            assertWithinErrorPercent(result.computedAverage, result.expectedAverage);
            assertWithinErrorPercent(result.computedVariance, result.expectedVariance);
        }

        // Now compute net variance using rollup versions [simulate 10 min rollups by aggregating two 5 min rollups]
        Points<BasicRollup> inputData = new Points<BasicRollup>();
        inputData.add(new Points.Point<BasicRollup>(123456789L, basicRollups.get(0)));
        inputData.add(new Points.Point<BasicRollup>(123456790L, basicRollups.get(1)));
        BasicRollup basicRollup10min_0 = BasicRollup.buildRollupFromRollups(inputData);
        assertWithinErrorPercent(basicRollup10min_0.getAverage().toDouble(),
                computeRawAverage(ArrayUtils.addAll(input[0], input[1])));
        assertWithinErrorPercent(basicRollup10min_0.getVariance().toDouble(),
                computeRawVariance(ArrayUtils.addAll(input[0], input[1])));

        inputData = new Points<BasicRollup>();
        inputData.add(new Points.Point<BasicRollup>(123456789L, basicRollups.get(2)));
        inputData.add(new Points.Point<BasicRollup>(123456790L, basicRollups.get(3)));
        BasicRollup basicRollup10min_1 = BasicRollup.buildRollupFromRollups(inputData);
        assertWithinErrorPercent(basicRollup10min_1.getAverage().toDouble(),
                computeRawAverage(ArrayUtils.addAll(input[2], input[3])));
        assertWithinErrorPercent(basicRollup10min_1.getVariance().toDouble(),
                computeRawVariance(ArrayUtils.addAll(input[2], input[3])));

        // Simulate 20 min rollups by aggregating two 10 min rollups
        inputData = new Points<BasicRollup>();
        inputData.add(new Points.Point<BasicRollup>(123456789L, basicRollup10min_0));
        inputData.add(new Points.Point<BasicRollup>(123456790L, basicRollup10min_1));
        BasicRollup basicRollup20min_0 = BasicRollup.buildRollupFromRollups(inputData);

        assertWithinErrorPercent(basicRollup20min_0.getAverage().toDouble(),
                computeRawAverage(TestData.DOUBLE_SRC));
        assertWithinErrorPercent(basicRollup20min_0.getVariance().toDouble(),
                computeRawVariance(TestData.DOUBLE_SRC));
    }

    private double computeRawVariance(double[] input) {
        // calculate average
        double avg = computeRawAverage(input);

        // calculate variance
        double sum = 0;
        for (double val: input) {
            sum += Math.pow((val - avg), 2);
        }
        return  sum/input.length;
    }

    private double computeRawAverage(double[] input) {
        // calculate mean
        double avg = 0;
        for (double val : input) {
            avg += val;
        }
        avg /= input.length;

        return avg;
    }

    private class Results {
        public double expectedVariance;
        public double computedVariance;
        public double expectedAverage;
        public double computedAverage;
    }

    private void assertWithinErrorPercent(double computed, double expected) {
        double errorPercentVar = 0.0;
        double deltaVar = computed - expected;
        if (deltaVar != 0) {
            errorPercentVar = deltaVar/expected * 100;
        }
        Assert.assertTrue(Math.abs(errorPercentVar) < ERROR_TOLERANCE);
    }
}


File: blueflood-elasticsearch/src/main/java/com/rackspacecloud/blueflood/io/ElasticIO.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.io;

import com.codahale.metrics.Histogram;
import com.codahale.metrics.Meter;
import com.google.common.annotations.VisibleForTesting;
import com.google.common.collect.Lists;
import com.rackspacecloud.blueflood.service.Configuration;
import com.rackspacecloud.blueflood.service.ElasticClientManager;
import com.rackspacecloud.blueflood.service.ElasticIOConfig;
import com.rackspacecloud.blueflood.service.RemoteElasticSearchServer;
import com.rackspacecloud.blueflood.types.IMetric;
import com.rackspacecloud.blueflood.types.Locator;
import com.rackspacecloud.blueflood.types.Metric;
import com.rackspacecloud.blueflood.utils.GlobPattern;
import com.rackspacecloud.blueflood.utils.Metrics;

import com.codahale.metrics.Timer;
import org.elasticsearch.action.bulk.BulkRequestBuilder;
import org.elasticsearch.action.index.IndexRequestBuilder;
import org.elasticsearch.action.search.SearchResponse;
import org.elasticsearch.client.Client;
import org.elasticsearch.common.xcontent.XContentBuilder;
import org.elasticsearch.common.xcontent.XContentFactory;
import org.elasticsearch.index.query.BoolQueryBuilder;
import org.elasticsearch.index.query.QueryBuilder;
import org.elasticsearch.search.SearchHit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.*;

import static com.rackspacecloud.blueflood.io.ElasticIO.ESFieldLabel.*;
import static org.elasticsearch.index.query.QueryBuilders.*;

public class ElasticIO implements DiscoveryIO {
    public static String INDEX_NAME_WRITE = Configuration.getInstance().getStringProperty(ElasticIOConfig.ELASTICSEARCH_INDEX_NAME_WRITE);
    public static String INDEX_NAME_READ = Configuration.getInstance().getStringProperty(ElasticIOConfig.ELASTICSEARCH_INDEX_NAME_READ);
    
    static enum ESFieldLabel {
        metric_name,
        tenantId,
        unit
    }
    
    private static final Logger log = LoggerFactory.getLogger(DiscoveryIO.class);;
    private static final String ES_TYPE = "metrics";
    private Client client;
    
    // todo: these should be instances per client.
    private final Timer searchTimer = Metrics.timer(ElasticIO.class, "Search Duration");
    private final Timer writeTimer = Metrics.timer(ElasticIO.class, "Write Duration");
    private final Histogram batchHistogram = Metrics.histogram(ElasticIO.class, "Batch Sizes");
    private Meter classCastExceptionMeter = Metrics.meter(ElasticIO.class, "Failed Cast to IMetric");
    private Histogram queryBatchHistogram = Metrics.histogram(ElasticIO.class, "Query Batch Size");

    public ElasticIO() {
        this(RemoteElasticSearchServer.getInstance());
    }

    public ElasticIO(Client client) {
        this.client = client;
    }

    public ElasticIO(ElasticClientManager manager) {
        this(manager.getClient());
    }

    private static SearchResult convertHitToMetricDiscoveryResult(SearchHit hit) {
        Map<String, Object> source = hit.getSource();
        String metricName = (String)source.get(metric_name.toString());
        String tenantId = (String)source.get(ESFieldLabel.tenantId.toString());
        String unit = (String)source.get(ESFieldLabel.unit.toString());
        SearchResult result = new SearchResult(tenantId, metricName, unit);

        return result;
    }

    public void insertDiscovery(List<IMetric> batch) throws IOException {
        batchHistogram.update(batch.size());
        if (batch.size() == 0) {
            return;
        }
        
        // TODO: check bulk insert result and retry
        Timer.Context ctx = writeTimer.time();
        try {
            BulkRequestBuilder bulk = client.prepareBulk();
            for (Object obj : batch) {
                if (!(obj instanceof IMetric)) {
                    classCastExceptionMeter.mark();
                    continue;
                }

                IMetric metric = (IMetric)obj;
                Locator locator = metric.getLocator();
                Discovery md = new Discovery(locator.getTenantId(), locator.getMetricName());

                Map<String, Object> info = new HashMap<String, Object>();


                if (obj instanceof  Metric && getUnit((Metric)metric) != null) { // metric units may be null
                    info.put(unit.toString(), getUnit((Metric)metric));
                }

                md.withAnnotation(info);
                bulk.add(createSingleRequest(md));
            }
            bulk.execute().actionGet();
        } finally {
            ctx.stop();
        }
    }

    private static String getUnit(Metric metric) {
        return metric.getUnit();
    }

    private IndexRequestBuilder createSingleRequest(Discovery md) throws IOException {
        if (md.getMetricName() == null) {
            throw new IllegalArgumentException("trying to insert metric discovery without a metricName");
        }
        return client.prepareIndex(INDEX_NAME_WRITE, ES_TYPE)
                .setId(md.getDocumentId())
                .setSource(md.createSourceContent())
                .setCreate(true)
                .setRouting(md.getTenantId());
    }

    @VisibleForTesting
    public void setINDEX_NAME_WRITE (String indexNameWrite) {
        INDEX_NAME_WRITE = indexNameWrite;
    }

    @VisibleForTesting
    public void setINDEX_NAME_READ (String indexNameRead) {
        INDEX_NAME_READ = indexNameRead;
    }
    
    public List<SearchResult> search(String tenant, String query) throws Exception {
        return search(tenant, Arrays.asList(query));
    }

    public List<SearchResult> search(String tenant, List<String> queries) throws Exception {
        List<SearchResult> results = new ArrayList<SearchResult>();
        Timer.Context multiSearchCtx = searchTimer.time();
        queryBatchHistogram.update(queries.size());
        BoolQueryBuilder bqb = boolQuery();
        QueryBuilder qb;

        for (String query : queries) {
            GlobPattern pattern = new GlobPattern(query);
            if (!pattern.hasWildcard()) {
                qb = termQuery(metric_name.name(), query);
            } else {
                qb = regexpQuery(metric_name.name(), pattern.compiled().toString());
            }
            bqb.should(boolQuery()
                     .must(termQuery(tenantId.toString(), tenant))
                     .must(qb)
            );
        }

        SearchResponse response = client.prepareSearch(INDEX_NAME_READ)
                .setRouting(tenant)
                .setSize(100000)
                .setVersion(true)
                .setQuery(bqb)
                .execute()
                .actionGet();
        multiSearchCtx.stop();
        for (SearchHit hit : response.getHits().getHits()) {
            SearchResult result = convertHitToMetricDiscoveryResult(hit);
            results.add(result);
        }
        return dedupResults(results);
    }

    private List<SearchResult> dedupResults(List<SearchResult> results) {
        HashMap<String, SearchResult> dedupedResults = new HashMap<String, SearchResult>();
        for (SearchResult result : results)
            dedupedResults.put(result.getMetricName(), result);
        return Lists.newArrayList(dedupedResults.values());
    }

    public static class Discovery {
        private Map<String, Object> annotation = new HashMap<String, Object>();
        private final String metricName;
        private final String tenantId;

        public Discovery(String tenantId, String metricName) {
            this.tenantId = tenantId;
            this.metricName = metricName;
        }
        public Map<String, Object> getAnnotation() {
            return annotation;
        }

        public String getTenantId() {
            return tenantId;
        }

        public String getMetricName() {
            return metricName;
        }

        public String getDocumentId() {
            return tenantId + ":" + metricName;
        }

        @Override
        public String toString() {
            return "ElasticMetricDiscovery [tenantId=" + tenantId + ", metricName=" + metricName + ", annotation="
                    + annotation.toString() + "]";
        }

        public Discovery withAnnotation(Map<String, Object> annotation) {
            this.annotation = annotation;
            return this;
        }

        private XContentBuilder createSourceContent() throws IOException {
            XContentBuilder json;

            json = XContentFactory.jsonBuilder().startObject()
                    .field(ESFieldLabel.tenantId.toString(), tenantId)
                    .field(metric_name.toString(), metricName);


            for (Map.Entry<String, Object> entry : annotation.entrySet()) {
                json = json.field(entry.getKey(), entry.getValue());
            }
            json = json.endObject();
            return json;
        }
    }

    @VisibleForTesting
    public void setClient(Client client) {
        this.client = client;
    }
}


File: blueflood-elasticsearch/src/main/java/com/rackspacecloud/blueflood/service/ElasticClientManager.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import org.elasticsearch.client.Client;

public interface ElasticClientManager {

    public Client getClient();

}


File: blueflood-elasticsearch/src/main/java/com/rackspacecloud/blueflood/service/ElasticIOConfig.java
/**
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

public enum ElasticIOConfig implements ConfigDefaults {
    ELASTICSEARCH_HOSTS("127.0.0.1:9300"),
    ELASTICSEARCH_CLUSTERNAME("elasticsearch"),
    ELASTICSEARCH_INDEX_NAME_WRITE("metric_metadata"),
    ELASTICSEARCH_INDEX_NAME_READ("metric_metadata");

    static {
        Configuration.getInstance().loadDefaults(ElasticIOConfig.values());
    }
    private String defaultValue;
    private ElasticIOConfig(String value) {
        this.defaultValue = value;
    }
    public String getDefaultValue() {
        return defaultValue;
    }
}


File: blueflood-elasticsearch/src/main/java/com/rackspacecloud/blueflood/service/RemoteElasticSearchServer.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import org.elasticsearch.client.Client;
import org.elasticsearch.client.transport.TransportClient;
import org.elasticsearch.common.settings.ImmutableSettings;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.transport.InetSocketTransportAddress;

import java.util.List;


public class RemoteElasticSearchServer implements ElasticClientManager {
    private static final RemoteElasticSearchServer INSTANCE = new RemoteElasticSearchServer();

    public static RemoteElasticSearchServer getInstance() {
        return INSTANCE;
    }

    private Client client;

    private RemoteElasticSearchServer() {
        Configuration config = Configuration.getInstance();
        List<String> hosts = config.getListProperty(ElasticIOConfig.ELASTICSEARCH_HOSTS);
        String clusterName = config.getStringProperty(ElasticIOConfig.ELASTICSEARCH_CLUSTERNAME);
        Settings settings = ImmutableSettings.settingsBuilder()
                .put("cluster.name", clusterName)
                .build();
        TransportClient tc = new TransportClient(settings);
        for (String host : hosts) {
            String[] parts = host.split(":");
            String address = parts[0];
            Integer port = Integer.parseInt(parts[1]);
            tc.addTransportAddress(new InetSocketTransportAddress(address, port));
        }
        client = tc;
    }

    public Client getClient() {
        return client;
    }
}


File: blueflood-elasticsearch/src/test/java/com/rackspacecloud/blueflood/service/ElasticIOTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.github.tlrx.elasticsearch.test.EsSetup;
import com.rackspacecloud.blueflood.io.ElasticIO;
import com.rackspacecloud.blueflood.io.SearchResult;
import com.rackspacecloud.blueflood.types.*;
import com.rackspacecloud.blueflood.utils.TimeValue;
import junit.framework.Assert;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

public class ElasticIOTest {
    private static final int NUM_PARENT_ELEMENTS = 30;
    private static final List<String> CHILD_ELEMENTS = Arrays.asList("A", "B", "C");
    private static final int NUM_GRANDCHILD_ELEMENTS = 3;
    private static final int NUM_DOCS = NUM_PARENT_ELEMENTS * CHILD_ELEMENTS.size() * NUM_GRANDCHILD_ELEMENTS;
    private static final String TENANT_A = "ratanasv";
    private static final String TENANT_B = "someotherguy";
    private static final String TENANT_C = "someothergal";
    private static final String UNIT = "horse length";
    private static final Map<String, List<Locator>> locatorMap = new HashMap<String, List<Locator>>();
    private ElasticIO elasticIO;
    private EsSetup esSetup;

    private static SearchResult createExpectedResult(String tenantId, int x, String y, int z, String unit) {
        Locator locator = createTestLocator(tenantId, x, y, z);
        return new SearchResult(tenantId, locator.getMetricName(), unit);
    }
    private static Locator createTestLocator(String tenantId, int x, String y, int z) {
        String xs = (x < 10 ? "0" : "") + String.valueOf(x);
        return Locator.createLocatorFromPathComponents(
                tenantId, "one", "two", "three" + xs,
                "four" + y,
                "five" + String.valueOf(z));
    }

    private static List<Locator> createComplexTestLocators(String tenantId) {
        Locator locator;
        List<Locator> locators = new ArrayList<Locator>();
        locatorMap.put(tenantId, locators);
        for (int x = 0; x < NUM_PARENT_ELEMENTS; x++) {
            for (String y : CHILD_ELEMENTS) {
                for (int z = 0; z < NUM_GRANDCHILD_ELEMENTS; z++) {
                    locator = createTestLocator(tenantId, x, y, z);
                    locators.add(locator);
                }
            }
        }
        return locators;
    }

    private static List<IMetric> createTestMetrics(String tenantId) {
        Metric metric;
        List<IMetric> metrics = new ArrayList<IMetric>();
        List<Locator> locators = createComplexTestLocators(tenantId);
        for (Locator locator : locators) {
            metric = new Metric(locator, "blarg", 0, new TimeValue(1, TimeUnit.DAYS), UNIT);
            metrics.add(metric);
        }
        return metrics;
    }

    private static List<IMetric> createTestMetricsFromInterface(String tenantId) {
        IMetric metric;
        List<IMetric> metrics = new ArrayList<IMetric>();
        CounterRollup counter = new CounterRollup();

        List<Locator> locators = createComplexTestLocators(tenantId);
        for (Locator locator : locators) {
            metric = new PreaggregatedMetric(0, locator, new TimeValue(1, TimeUnit.DAYS), counter);
            metrics.add(metric);
        }
        return metrics;
    }

    @Before
    public void setup() throws IOException {
        esSetup = new EsSetup();
        esSetup.execute(EsSetup.deleteAll());
        esSetup.execute(EsSetup.createIndex(ElasticIO.INDEX_NAME_WRITE)
                .withSettings(EsSetup.fromClassPath("index_settings.json"))
                .withMapping("metrics", EsSetup.fromClassPath("metrics_mapping.json")));
        elasticIO = new ElasticIO(esSetup.client());

        elasticIO.insertDiscovery(createTestMetrics(TENANT_A));
        elasticIO.insertDiscovery(createTestMetrics(TENANT_B));
        elasticIO.insertDiscovery(createTestMetricsFromInterface(TENANT_C));

        esSetup.client().admin().indices().prepareRefresh().execute().actionGet();
    }

    @After
    public void tearDown() {
        esSetup.terminate();
    }

    @Test
    public void testNoCrossTenantResults() throws Exception {
        List<SearchResult> results = elasticIO.search(TENANT_A, "*");
        Assert.assertEquals(NUM_DOCS, results.size());
        for (SearchResult result : results) {
            Assert.assertNotNull(result.getTenantId());
            Assert.assertNotSame(TENANT_B, result.getTenantId());
        }
    }

    @Test
    public void testWildCard() throws Exception {
        testWildcard(TENANT_A, UNIT);
    }

    @Test
    public void testWildcardForPreaggregatedMetric() throws Exception {
        testWildcard(TENANT_C, null);
    }

    @Test
    public void testBatchQueryWithNoWildCards() throws Exception {
        String tenantId = TENANT_A;
        String query1 = "one.two.three00.fourA.five1";
        String query2 = "one.two.three01.fourA.five2";
        List<SearchResult> results;
        ArrayList<String> queries = new ArrayList<String>();
        queries.add(query1);
        queries.add(query2);
        results = elasticIO.search(tenantId, queries);
        Assert.assertEquals(results.size(), 2); //we searched for 2 unique metrics
        results.contains(new SearchResult(TENANT_A, query1, UNIT));
        results.contains(new SearchResult(TENANT_A, query2, UNIT));
    }

    @Test
    public void testBatchQueryWithWildCards() throws Exception {
        String tenantId = TENANT_A;
        String query1 = "one.two.three00.fourA.*";
        String query2 = "one.two.*.fourA.five2";
        List<SearchResult> results;
        ArrayList<String> queries = new ArrayList<String>();
        queries.add(query1);
        queries.add(query2);
        results = elasticIO.search(tenantId, queries);
        // query1 will return 3 results, query2 will return 30 results, but we get back 32 because of intersection
        Assert.assertEquals(results.size(), 32);
    }

    @Test
    public void testBatchQueryWithWildCards2() throws Exception {
        String tenantId = TENANT_A;
        String query1 = "*.two.three00.fourA.five1";
        String query2 = "*.two.three01.fourA.five2";
        List<SearchResult> results;
        ArrayList<String> queries = new ArrayList<String>();
        queries.add(query1);
        queries.add(query2);
        results = elasticIO.search(tenantId, queries);
        Assert.assertEquals(results.size(), 2);
    }

    public void testWildcard(String tenantId, String unit) throws Exception {
        SearchResult entry;
        List<SearchResult> results;
        results = elasticIO.search(tenantId, "one.two.*");
        List<Locator> locators = locatorMap.get(tenantId);
        Assert.assertEquals(locators.size(), results.size());
        for (Locator locator : locators) {
            entry =  new SearchResult(tenantId, locator.getMetricName(), unit);
            Assert.assertTrue((results.contains(entry)));
        }

        results = elasticIO.search(tenantId, "*.fourA.*");
        Assert.assertEquals(NUM_PARENT_ELEMENTS * NUM_GRANDCHILD_ELEMENTS, results.size());
        for (int x = 0; x < NUM_PARENT_ELEMENTS; x++) {
            for (int z = 0; z < NUM_GRANDCHILD_ELEMENTS; z++) {
                entry = createExpectedResult(tenantId, x, "A", z, unit);
                Assert.assertTrue(results.contains(entry));
            }
        }

        results = elasticIO.search(tenantId, "*.three1*.four*.five2");
        Assert.assertEquals(10 * CHILD_ELEMENTS.size(), results.size());
        for (int x = 10; x < 20; x++) {
            for (String y : CHILD_ELEMENTS) {
                entry = createExpectedResult(tenantId, x, y, 2, unit);
                Assert.assertTrue(results.contains(entry));
            }
        }
    }

    @Test
    public void testGlobMatching() throws Exception {
        List<SearchResult> results = elasticIO.search(TENANT_A, "one.two.{three00,three01}.fourA.five0");
        Assert.assertEquals(results.size(), 2);
        results.contains(new SearchResult(TENANT_A, "one.two.three00.fourA.five0", UNIT));
        results.contains(new SearchResult(TENANT_A, "one.two.three01.fourA.five0", UNIT));
    }

    @Test
    public void testGlobMatching2() throws Exception {
        List<SearchResult> results = elasticIO.search(TENANT_A, "one.two.three0?.fourA.five0");
        List<SearchResult> results2 = elasticIO.search(TENANT_A, "one.two.three0[0-9].fourA.five0");
        Assert.assertEquals(10, results.size());
        for (SearchResult result : results) {
            Assert.assertTrue(result.getMetricName().startsWith("one.two.three"));
            Assert.assertEquals(result.getTenantId(), TENANT_A);
            results2.contains(result);
        }
    }

    @Test
    public void testGlobMatching3() throws Exception {
        List<SearchResult> results = elasticIO.search(TENANT_A, "one.two.three0[01].fourA.five0");
        Assert.assertEquals(2, results.size());
        for (SearchResult result : results) {
            Assert.assertTrue(result.getMetricName().equals("one.two.three00.fourA.five0") || result.getMetricName().equals("one.two.three01.fourA.five0"));
        }
    }

    @Test
    public void testDeDupMetrics() throws Exception {
        // New index name and the locator to be written to it
        String ES_DUP = ElasticIO.INDEX_NAME_WRITE + "_2";
        Locator testLocator = createTestLocator(TENANT_A, 0, "A", 0);
        // Metric is aleady there in old
        List<SearchResult> results = elasticIO.search(TENANT_A, testLocator.getMetricName());
        Assert.assertEquals(results.size(), 1);
        Assert.assertEquals(results.get(0).getMetricName(), testLocator.getMetricName());
        // Actually create the new index
        esSetup.execute(EsSetup.createIndex(ES_DUP)
                .withMapping("metrics", EsSetup.fromClassPath("metrics_mapping_v1.json")));
        // Insert metric into the new index
        elasticIO.setINDEX_NAME_WRITE(ES_DUP);
        ArrayList metricList = new ArrayList();
        metricList.add(new Metric(createTestLocator(TENANT_A, 0, "A", 0), "blarg", 0, new TimeValue(1, TimeUnit.DAYS), UNIT));
        elasticIO.insertDiscovery(metricList);
        esSetup.client().admin().indices().prepareRefresh().execute().actionGet();
        // Set up aliases
        esSetup.client().admin().indices().prepareAliases().addAlias(ES_DUP, "metric_metadata_read")
                .addAlias(ElasticIO.INDEX_NAME_WRITE, "metric_metadata_read").execute().actionGet();
        elasticIO.setINDEX_NAME_READ("metric_metadata_read");
        results = elasticIO.search(TENANT_A, testLocator.getMetricName());
        // Should just be one result
        Assert.assertEquals(results.size(), 1);
        Assert.assertEquals(results.get(0).getMetricName(), testLocator.getMetricName());
    }
}


File: blueflood-http/src/integration-test/java/com/rackspacecloud/blueflood/http/HttpClientVendor.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.http;

import org.apache.http.client.params.ClientPNames;
import org.apache.http.conn.ClientConnectionManager;
import org.apache.http.impl.client.DefaultHttpClient;
import org.apache.http.impl.conn.PoolingClientConnectionManager;
import org.apache.http.params.CoreConnectionPNames;

public class HttpClientVendor {
    private DefaultHttpClient client;

    public HttpClientVendor() {
        client = new DefaultHttpClient(buildConnectionManager(20));
        client.getParams().setBooleanParameter(ClientPNames.HANDLE_REDIRECTS, true);
        client.getParams().setIntParameter(CoreConnectionPNames.CONNECTION_TIMEOUT, 5000);
        client.getParams().setIntParameter(CoreConnectionPNames.SO_TIMEOUT, 30000);

        // Wait this long for an available connection. Setting this correctly is important in order to avoid
        // connectionpool timeouts.
        client.getParams().setLongParameter(ClientPNames.CONN_MANAGER_TIMEOUT, 5000);
    }
    
    public DefaultHttpClient getClient() {
        return client;
    }

    private ClientConnectionManager buildConnectionManager(int concurrency) {
        final PoolingClientConnectionManager connectionManager = new PoolingClientConnectionManager();
        connectionManager.setDefaultMaxPerRoute(concurrency);
        connectionManager.setMaxTotal(concurrency);
        return connectionManager;
    }

    public void shutdown() {
        if (client != null) {
            client.getConnectionManager().shutdown();
        }
    }
}


File: blueflood-http/src/integration-test/java/com/rackspacecloud/blueflood/outputs/handlers/HttpRollupHandlerIntegrationTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.handlers;

import com.rackspacecloud.blueflood.cache.MetadataCache;
import com.rackspacecloud.blueflood.http.HttpClientVendor;
import com.rackspacecloud.blueflood.io.*;
import com.rackspacecloud.blueflood.outputs.formats.MetricData;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.service.*;
import com.rackspacecloud.blueflood.types.*;
import org.apache.http.HttpEntity;
import org.apache.http.HttpResponse;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.client.utils.URIBuilder;
import org.apache.http.entity.ContentType;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.DefaultHttpClient;
import org.json.simple.JSONArray;
import org.junit.*;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.*;

public class HttpRollupHandlerIntegrationTest extends IntegrationTestBase {
    // A timestamp 2 days ago
    private final long baseMillis = Calendar.getInstance().getTimeInMillis() - 172800000;
    private final String tenantId = "ac" + IntegrationTestBase.randString(8);
    private final String metricName = "met_" + IntegrationTestBase.randString(8);
    private final String strMetricName = "strMet_" + IntegrationTestBase.randString(8);
    final Locator[] locators = new Locator[] {
            Locator.createLocatorFromPathComponents(tenantId, metricName),
            Locator.createLocatorFromPathComponents(tenantId, strMetricName)
    };
    private static int queryPort = 20000;
    private static HttpQueryService httpQueryService;
    private static HttpClientVendor vendor;
    private static DefaultHttpClient client;

    private HttpRollupsQueryHandler httpHandler;
    private final Map<Locator, Map<Granularity, Integer>> locatorToPoints = new HashMap<Locator, Map<Granularity,Integer>>();

    @BeforeClass
    public static void setUpHttp() {
        queryPort = Configuration.getInstance().getIntegerProperty(HttpConfig.HTTP_METRIC_DATA_QUERY_PORT);
        httpQueryService = new HttpQueryService();
        httpQueryService.startService();
        vendor = new HttpClientVendor();
        client = vendor.getClient();
    }

    @Before
    public void setUp() throws Exception {
        super.setUp();
        AstyanaxWriter writer = AstyanaxWriter.getInstance();
        IncomingMetricMetadataAnalyzer analyzer = new IncomingMetricMetadataAnalyzer(MetadataCache.getInstance());

        // insert something every 1m for 24h
        for (int i = 0; i < 1440; i++) {
            final long curMillis = baseMillis + (i * 60000);
            final List<Metric> metrics = new ArrayList<Metric>();
            final Metric metric = getRandomIntMetric(locators[0], curMillis);
            final Metric stringMetric = getRandomStringmetric(locators[1], curMillis);
            metrics.add(metric);
            metrics.add(stringMetric);

            analyzer.scanMetrics(new ArrayList<IMetric>(metrics));
            writer.insertFull(metrics);
        }

        httpHandler = new HttpRollupsQueryHandler();

        // generate every level of rollup for the raw data
        Granularity g = Granularity.FULL;
        while (g != Granularity.MIN_1440) {
            g = g.coarser();
            for (Locator locator : locators) {
                generateRollups(locator, baseMillis, baseMillis + 86400000, g);
            }
        }

        final Map<Granularity, Integer> answerForNumericMetric = new HashMap<Granularity, Integer>();
        answerForNumericMetric.put(Granularity.FULL, 1440);
        answerForNumericMetric.put(Granularity.MIN_5, 289);
        answerForNumericMetric.put(Granularity.MIN_20, 73);
        answerForNumericMetric.put(Granularity.MIN_60, 25);
        answerForNumericMetric.put(Granularity.MIN_240, 7);
        answerForNumericMetric.put(Granularity.MIN_1440, 2);

        final Map<Granularity, Integer> answerForStringMetric = new HashMap<Granularity, Integer>();
        answerForStringMetric.put(Granularity.FULL, 1440);
        answerForStringMetric.put(Granularity.MIN_5, 1440);
        answerForStringMetric.put(Granularity.MIN_20, 1440);
        answerForStringMetric.put(Granularity.MIN_60, 1440);
        answerForStringMetric.put(Granularity.MIN_240, 1440);
        answerForStringMetric.put(Granularity.MIN_1440, 1440);

        locatorToPoints.put(locators[0], answerForNumericMetric);
        locatorToPoints.put(locators[1], answerForStringMetric);
    }

    @Test
    public void testGetPoints() throws Exception {
        testGetRollupByPoints();
        testGetRollupByResolution();
        testHttpRequestForPoints();
        testHttpRequestForHistograms();
    }

    private void testGetRollupByPoints() throws Exception {
        final Map<Granularity, Integer> points = new HashMap<Granularity, Integer>();
        points.put(Granularity.FULL, 1600);
        points.put(Granularity.MIN_5, 287);
        points.put(Granularity.MIN_20, 71);
        points.put(Granularity.MIN_60, 23);
        points.put(Granularity.MIN_240, 5);
        points.put(Granularity.MIN_1440, 1);

        testHTTPRollupHandlerGetByPoints(locatorToPoints, points, baseMillis, baseMillis + 86400000);
    }

    private void testGetRollupByResolution() throws Exception {
        for (Locator locator : locators) {
            for (Resolution resolution : Resolution.values()) {
                Granularity g = Granularity.granularities()[resolution.getValue()];
                testHTTPHandlersGetByResolution(locator, resolution, baseMillis, baseMillis + 86400000,
                        locatorToPoints.get(locator).get(g));
            }
        }
    }

    private void testHTTPRollupHandlerGetByPoints(Map<Locator, Map<Granularity, Integer>> answers, Map<Granularity, Integer> points,
                                                   long from, long to) throws Exception {
        for (Locator locator : locators) {
            for (Granularity g2 : Granularity.granularities()) {
                MetricData data = httpHandler.GetDataByPoints(
                        locator.getTenantId(),
                        locator.getMetricName(),
                        baseMillis,
                        baseMillis + 86400000,
                        points.get(g2));
                Assert.assertEquals((int) answers.get(locator).get(g2), data.getData().getPoints().size());
		// Disabling test that fail on ES
                // Assert.assertEquals(locatorToUnitMap.get(locator), data.getUnit());
            }
        }
    }

    private void testHTTPHandlersGetByResolution(Locator locator, Resolution resolution, long from, long to,
                                                 int expectedPoints) throws Exception {
        Assert.assertEquals(expectedPoints, getNumberOfPointsViaHTTPHandler(httpHandler, locator,
                from, to, resolution));
    }

    private int getNumberOfPointsViaHTTPHandler(HttpRollupsQueryHandler handler,
                                               Locator locator, long from, long to, Resolution resolution)
            throws Exception {
        final MetricData values = handler.GetDataByResolution(locator.getTenantId(),
                locator.getMetricName(), from, to, resolution);
        return values.getData().getPoints().size();
    }

    private void testHttpRequestForPoints() throws Exception {
        testHappyCaseHTTPRequest();
        testBadRequest();
        testBadMethod();
        testHappyCaseMultiFetchHTTPRequest();
    }

    private void testHappyCaseHTTPRequest() throws Exception {
        HttpGet get = new HttpGet(getMetricsQueryURI());
        HttpResponse response = client.execute(get);
        Assert.assertEquals(200, response.getStatusLine().getStatusCode());
    }

    private void testHttpRequestForHistograms() throws Exception {
        HttpGet get = new HttpGet(getHistQueryURI());
        HttpResponse response = client.execute(get);
        Assert.assertEquals(200, response.getStatusLine().getStatusCode());
    }

    private void testBadRequest() throws Exception {
        HttpGet get = new HttpGet(getInvalidMetricsQueryURI());
        HttpResponse response = client.execute(get);
        Assert.assertEquals(400, response.getStatusLine().getStatusCode());
    }

    private void testBadMethod() throws Exception {
        HttpPost post = new HttpPost(getMetricsQueryURI());
        HttpResponse response = client.execute(post);
        Assert.assertEquals(405, response.getStatusLine().getStatusCode());
    }

    private void testHappyCaseMultiFetchHTTPRequest() throws Exception {
        HttpPost post = new HttpPost(getBatchMetricsQueryURI());
        JSONArray metricsToGet = new JSONArray();
        for (Locator locator : locators) {
            metricsToGet.add(locator.toString());
        }
        HttpEntity entity = new StringEntity(metricsToGet.toString(), ContentType.APPLICATION_JSON);
        post.setEntity(entity);
        HttpResponse response = client.execute(post);
        Assert.assertEquals(200, response.getStatusLine().getStatusCode());
    }

    private URI getMetricsQueryURI() throws URISyntaxException {
        URIBuilder builder = new URIBuilder().setScheme("http").setHost("127.0.0.1")
                .setPort(queryPort).setPath("/v2.0/" + tenantId + "/views/" + metricName)
                .setParameter("from", String.valueOf(baseMillis))
                .setParameter("to", String.valueOf(baseMillis + 86400000))
                .setParameter("resolution", "full");
        return builder.build();
    }

    private URI getHistQueryURI() throws URISyntaxException {
        URIBuilder builder = new URIBuilder().setScheme("http").setHost("127.0.0.1")
                .setPort(queryPort).setPath("/v2.0/" + tenantId + "/views/histograms/" + metricName)
                .setParameter("from", String.valueOf(baseMillis))
                .setParameter("to", String.valueOf(baseMillis + 86400000))
                .setParameter("resolution", "full");
        return builder.build();
    }

    private URI getBatchMetricsQueryURI() throws Exception {
        URIBuilder builder = new URIBuilder().setScheme("http").setHost("127.0.0.1")
                .setPort(queryPort).setPath("/v2.0/" + tenantId + "/views")
                .setParameter("from", String.valueOf(baseMillis))
                .setParameter("to", String.valueOf(baseMillis + 86400000))
                .setParameter("resolution", "full");
        return builder.build();
    }

    private URI getInvalidMetricsQueryURI() throws URISyntaxException {
        URIBuilder builder = new URIBuilder().setScheme("http").setHost("127.0.0.1")
                .setPort(queryPort).setPath("/v2.0/" + tenantId + "/views/" + metricName)
                .setParameter("from", String.valueOf(baseMillis))
                .setParameter("resolution", "full");  // Misses parameter 'to'
        return builder.build();
    }

    @AfterClass
    public static void shutdown() {
        vendor.shutdown();
        httpQueryService.stopService();
    }
}


File: blueflood-http/src/integration-test/java/com/rackspacecloud/blueflood/outputs/handlers/HttpRollupHandlerWithESIntegrationTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.handlers;

import com.github.tlrx.elasticsearch.test.EsSetup;
import com.rackspacecloud.blueflood.cache.MetadataCache;
import com.rackspacecloud.blueflood.http.HttpClientVendor;
import com.rackspacecloud.blueflood.io.*;
import com.rackspacecloud.blueflood.outputs.formats.MetricData;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.service.*;
import com.rackspacecloud.blueflood.types.*;
import com.rackspacecloud.blueflood.utils.QueryDiscoveryModuleLoader;
import com.rackspacecloud.blueflood.utils.Util;
import org.apache.http.HttpResponse;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.utils.URIBuilder;
import org.apache.http.impl.client.DefaultHttpClient;
import org.junit.*;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.*;

public class HttpRollupHandlerWithESIntegrationTest extends IntegrationTestBase {
    //A time stamp 2 days ago
    private final long baseMillis = Calendar.getInstance().getTimeInMillis() - 172800000;
    private final String tenantId = "ac" + IntegrationTestBase.randString(8);
    private final String metricName = "met_" + IntegrationTestBase.randString(8);
    private final Locator locator = Locator.createLocatorFromPathComponents(tenantId, metricName);
    private static int queryPort;
    private Map<Granularity, Integer> granToPoints = new HashMap<Granularity,Integer>();
    private HttpRollupsQueryHandler httpHandler;
    private static ElasticIO elasticIO;
    private static EsSetup esSetup;
    private static HttpQueryService httpQueryService;
    private static HttpClientVendor vendor;
    private static DefaultHttpClient client;

    @BeforeClass
    public static void setUpHttp() {
        Configuration.getInstance().setProperty(CoreConfig.DISCOVERY_MODULES.name(),
                "com.rackspacecloud.blueflood.io.ElasticIO");
        Configuration.getInstance().setProperty(CoreConfig.USE_ES_FOR_UNITS.name(), "true");
        queryPort = Configuration.getInstance().getIntegerProperty(HttpConfig.HTTP_METRIC_DATA_QUERY_PORT);
        httpQueryService = new HttpQueryService();
        httpQueryService.startService();
        vendor = new HttpClientVendor();
        client = vendor.getClient();

        esSetup = new EsSetup();
        esSetup.execute(EsSetup.deleteAll());
        esSetup.execute(EsSetup.createIndex(ElasticIO.INDEX_NAME_WRITE)
                .withSettings(EsSetup.fromClassPath("index_settings.json"))
                .withMapping("metrics", EsSetup.fromClassPath("metrics_mapping.json")));
        elasticIO = new ElasticIO(esSetup.client());
    }

    @Before
    public void setup() throws Exception {
        super.setUp();
        AstyanaxWriter writer = AstyanaxWriter.getInstance();
        IncomingMetricMetadataAnalyzer analyzer = new IncomingMetricMetadataAnalyzer(MetadataCache.getInstance());

        final List<Metric> metrics = new ArrayList<Metric>();
        for (int i = 0; i < 1440; i++) {
            final long curMillis = baseMillis + i * 60000;
            final Metric metric = getRandomIntMetric(locator, curMillis);
            metrics.add(metric);
        }

        elasticIO.insertDiscovery(new ArrayList<IMetric>(metrics));
        esSetup.client().admin().indices().prepareRefresh().execute().actionGet();

        analyzer.scanMetrics(new ArrayList<IMetric>(metrics));
        writer.insertFull(metrics);

        httpHandler = new HttpRollupsQueryHandler();
        ((ElasticIO)QueryDiscoveryModuleLoader.getDiscoveryInstance()).setClient(esSetup.client());

        // generate every level of rollup for the raw data
        Granularity g = Granularity.FULL;
        while (g != Granularity.MIN_1440) {
            g = g.coarser();
            generateRollups(locator, baseMillis, baseMillis + 86400000, g);
        }

        granToPoints.put(Granularity.FULL, 1440);
        granToPoints.put(Granularity.MIN_5, 289);
        granToPoints.put(Granularity.MIN_20, 73);
        granToPoints.put(Granularity.MIN_60, 25);
        granToPoints.put(Granularity.MIN_240, 7);
        granToPoints.put(Granularity.MIN_1440, 2);
    }

    @Test
    public void testOldMetricDataFetching() throws Exception {
        final Map<Granularity, Integer> points = new HashMap<Granularity, Integer>();
        //long currentTimeStamp = Calendar.getInstance().getTimeInMillis();
        long millisInADay = 86400 * 1000;

        points.put(Granularity.FULL, 1600);
        points.put(Granularity.MIN_5, 400);
        points.put(Granularity.MIN_20, 71);
        points.put(Granularity.MIN_60, 23);
        points.put(Granularity.MIN_240, 5);
        points.put(Granularity.MIN_1440, 1);
        long[] old_timestamps = new long[] {baseMillis - 6 * millisInADay, baseMillis - 12 * millisInADay, baseMillis - 30 * millisInADay, baseMillis - (160* millisInADay), baseMillis - (400*millisInADay)};

        int i = 0;
        for (Granularity gran : Granularity.granularities()) {
            if (gran == Granularity.LAST) {
                break;
            }

            long from = old_timestamps[i];
            long to = baseMillis+(2 * millisInADay);

            MetricData data = httpHandler.GetDataByPoints(
                    locator.getTenantId(),
                    locator.getMetricName(),
                    from,
                    to,
                    points.get(gran));

            //The from timestamps are manufactured such that they are always before
            //the data corresponding to the granularity 'gran' has expired, it will return points for a granularity coarser
            //than 'gran'. Therefore the points returned will always be slightly less
            //than the points asked for.
            Assert.assertTrue((int) granToPoints.get(gran) > data.getData().getPoints().size());
            Assert.assertEquals(locatorToUnitMap.get(locator), data.getUnit());

            i++;
        }
        Assert.assertFalse(MetadataCache.getInstance().containsKey(locator, MetricMetadata.UNIT.name()));
    }

    @Test
    public void testMetricDataFetching() throws Exception {
        final Map<Granularity, Integer> points = new HashMap<Granularity, Integer>();
        points.put(Granularity.FULL, 1600);
        points.put(Granularity.MIN_5, 287);
        points.put(Granularity.MIN_20, 71);
        points.put(Granularity.MIN_60, 23);
        points.put(Granularity.MIN_240, 5);
        points.put(Granularity.MIN_1440, 1);
        for (Granularity gran : Granularity.granularities()) {
            MetricData data = httpHandler.GetDataByPoints(
                    locator.getTenantId(),
                    locator.getMetricName(),
                    baseMillis,
                    baseMillis + 86400000,
                    points.get(gran));
            Assert.assertEquals((int) granToPoints.get(gran), data.getData().getPoints().size());
            Assert.assertEquals(locatorToUnitMap.get(locator), data.getUnit());
        }
        Assert.assertFalse(MetadataCache.getInstance().containsKey(locator, MetricMetadata.UNIT.name()));
    }

    @Test
    public void testUnknownUnit() throws Exception {
        Locator loc = Locator.createLocatorFromPathComponents("unknown", "unit");
        MetricData data = httpHandler.GetDataByPoints(
                loc.getTenantId(),
                loc.getMetricName(),
                baseMillis,
                baseMillis + 86400000,
                1600);
        Assert.assertEquals(data.getData().getPoints().size(), 0);
        Assert.assertEquals(data.getUnit(), Util.UNKNOWN);
    }

    @Test
    public void TestHttpHappyCase() throws Exception {
        HttpGet get = new HttpGet(getMetricsQueryURI());
        HttpResponse response = client.execute(get);
        Assert.assertEquals(200, response.getStatusLine().getStatusCode());
    }

    private URI getMetricsQueryURI() throws URISyntaxException {
        URIBuilder builder = new URIBuilder().setScheme("http").setHost("127.0.0.1")
                .setPort(queryPort).setPath("/v2.0/" + tenantId + "/views/" + metricName)
                .setParameter("from", String.valueOf(baseMillis))
                .setParameter("to", String.valueOf(baseMillis + 86400000))
                .setParameter("resolution", "full");
        return builder.build();
    }

    @AfterClass
    public static void tearDownClass() throws Exception{
        Configuration.getInstance().setProperty(CoreConfig.DISCOVERY_MODULES.name(), "");
        Configuration.getInstance().setProperty(CoreConfig.USE_ES_FOR_UNITS.name(), "false");
        esSetup.terminate();
        httpQueryService.stopService();
    }
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/http/DefaultHandler.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.http;

import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.handler.codec.http.HttpRequest;
import org.jboss.netty.handler.codec.http.HttpResponseStatus;

public class DefaultHandler implements HttpRequestHandler {

    @Override
    public void handle(ChannelHandlerContext ctx, HttpRequest request) {
        HttpResponder.respond(ctx, request, HttpResponseStatus.OK);
    }
}

File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/http/HTTPRequestWithDecodedQueryParams.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.http;

import org.jboss.netty.buffer.ChannelBuffer;
import org.jboss.netty.handler.codec.http.*;

import java.util.List;
import java.util.Map;
import java.util.Set;


public class HTTPRequestWithDecodedQueryParams implements HttpRequest {
    private Map<String, List<String>> queryParams;
    private DefaultHttpRequest request;

    private HTTPRequestWithDecodedQueryParams(DefaultHttpRequest request, Map<String, List<String>> queryParams) {
        this.request = request;
        this.queryParams = queryParams;
    }

    public static HTTPRequestWithDecodedQueryParams createHttpRequestWithDecodedQueryParams(DefaultHttpRequest request) {
        final QueryStringDecoder decoder = new QueryStringDecoder(request.getUri());
        request.setUri(decoder.getPath());
        return new HTTPRequestWithDecodedQueryParams(request, decoder.getParameters());
    }

    public Map<String, List<String>> getQueryParams() {
        return queryParams;
    }

    @Override
    public HttpMethod getMethod() {
        return request.getMethod();
    }

    @Override
    public void setMethod(HttpMethod method) {
        request.setMethod(method);
    }

    @Override
    public String getUri() {
        return request.getUri();
    }

    @Override
    public void setUri(String uri) {
        request.setUri(uri);
    }

    @Override
    public String getHeader(String name) {
        return request.getHeader(name);
    }

    @Override
    public List<String> getHeaders(String name) {
        return request.getHeaders(name);
    }

    @Override
    public List<Map.Entry<String, String>> getHeaders() {
        return request.getHeaders();
    }

    @Override
    public boolean containsHeader(String name) {
        return request.containsHeader(name);
    }

    @Override
    public Set<String> getHeaderNames() {
        return request.getHeaderNames();
    }

    @Override
    public HttpVersion getProtocolVersion() {
        return request.getProtocolVersion();
    }

    @Override
    public void setProtocolVersion(HttpVersion version) {
        request.setProtocolVersion(version);
    }

    @Override
    public ChannelBuffer getContent() {
        return request.getContent();
    }

    @Override
    public void setContent(ChannelBuffer content) {
        request.setContent(content);
    }

    @Override
    public void addHeader(String name, Object value) {
        request.addHeader(name, value);
    }

    @Override
    public void setHeader(String name, Object value) {
        request.addHeader(name, value);
    }

    @Override
    public void setHeader(String name, Iterable<?> values) {
        request.setHeader(name, values);
    }

    @Override
    public void removeHeader(String name) {
        request.removeHeader(name);
    }

    @Override
    public void clearHeaders() {
        request.clearHeaders();
    }

    @Deprecated
    public long getContentLength() {
        return request.getContentLength();
    }

    @Deprecated
    public long getContentLength(long defaultValue) {
        return request.getContentLength(defaultValue);
    }

    @Override
    public boolean isChunked() {
        return request.isChunked();
    }

    @Override
    public void setChunked(boolean chunked) {
        request.setChunked(chunked);
    }

    @Deprecated
    public boolean isKeepAlive() {
        return request.isKeepAlive();
    }
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/http/HttpRequestHandler.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.http;

import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.handler.codec.http.HttpRequest;

public interface HttpRequestHandler {
    public void handle(ChannelHandlerContext ctx, HttpRequest request);
}

File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/http/HttpResponder.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.http;

import org.jboss.netty.channel.ChannelFuture;
import org.jboss.netty.channel.ChannelFutureListener;
import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.handler.codec.http.DefaultHttpResponse;
import org.jboss.netty.handler.codec.http.HttpRequest;
import org.jboss.netty.handler.codec.http.HttpResponse;
import org.jboss.netty.handler.codec.http.HttpResponseStatus;

import static org.jboss.netty.handler.codec.http.HttpHeaders.isKeepAlive;
import static org.jboss.netty.handler.codec.http.HttpHeaders.setContentLength;
import static org.jboss.netty.handler.codec.http.HttpVersion.HTTP_1_1;

public class HttpResponder {
    public static void respond(ChannelHandlerContext ctx, HttpRequest req, HttpResponseStatus status) {
        respond(ctx, req, new DefaultHttpResponse(HTTP_1_1, status));
    }

    public static void respond(ChannelHandlerContext ctx, HttpRequest req, HttpResponse res) {
        if (res.getContent() != null) {
            setContentLength(res, res.getContent().readableBytes());
        }

        // Send the response and close the connection if necessary.
        ChannelFuture f = ctx.getChannel().write(res);
        if (req == null || !isKeepAlive(req)) {
            f.addListener(ChannelFutureListener.CLOSE);
        }
    }
}

File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/http/NoRouteHandler.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.http;

import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.handler.codec.http.HttpRequest;
import org.jboss.netty.handler.codec.http.HttpResponseStatus;

public class NoRouteHandler implements HttpRequestHandler {

    @Override
    public void handle(ChannelHandlerContext context, HttpRequest request) {
        HttpResponder.respond(context, request, HttpResponseStatus.NOT_FOUND);
    }
}

File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/http/QueryStringDecoderAndRouter.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.http;

import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.channel.ExceptionEvent;
import org.jboss.netty.channel.MessageEvent;
import org.jboss.netty.channel.SimpleChannelUpstreamHandler;
import org.jboss.netty.handler.codec.frame.TooLongFrameException;
import org.jboss.netty.handler.codec.http.DefaultHttpRequest;
import org.jboss.netty.handler.codec.http.HttpResponseStatus;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class QueryStringDecoderAndRouter extends SimpleChannelUpstreamHandler {
    private static final Logger log = LoggerFactory.getLogger(QueryStringDecoderAndRouter.class);
    private final RouteMatcher router;

    public QueryStringDecoderAndRouter(RouteMatcher router) {
        this.router = router;
    }

    @Override
    public void messageReceived(ChannelHandlerContext ctx, MessageEvent e) throws Exception {
        Object msg = e.getMessage();
        if (msg instanceof DefaultHttpRequest) {
            final DefaultHttpRequest request = (DefaultHttpRequest) msg;
            router.route(ctx, HTTPRequestWithDecodedQueryParams.createHttpRequestWithDecodedQueryParams(request));
        } else {
            log.error("Ignoring non HTTP message {}, from {}", e.getMessage(), e.getRemoteAddress());
            throw new Exception("Non-HTTP message from " + e.getRemoteAddress());
        }
    }

    @Override
    public void exceptionCaught(ChannelHandlerContext ctx, ExceptionEvent e) {
        if (e.getCause() instanceof IllegalArgumentException) {
            if ("empty text".equals(e.getCause().getMessage())) {
                // pass. we ignore these because this is what happens when a connection is closed with prejudice by us.
                // netty tries to finish reading the buffer to create a message to send through the pipeline.
            } else {
                log.error(e.getCause().getMessage(), e.getCause());
            }
        } else if (e.getCause() instanceof TooLongFrameException) {
            // todo: meter these so we observe DOS conditions.
            log.warn(String.format("Long frame from %s", ctx.getChannel().getRemoteAddress()));
            HttpResponder.respond(ctx, null, HttpResponseStatus.BAD_REQUEST);
        } else {
            log.warn("Exception event received: ", e.getCause());
        }
    }
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/http/RouteMatcher.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.http;

import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.handler.codec.http.HttpMethod;
import org.jboss.netty.handler.codec.http.HttpRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class RouteMatcher {
    private final Map<Pattern, PatternRouteBinding> getBindings;
    private final Map<Pattern, PatternRouteBinding> putBindings;
    private final Map<Pattern, PatternRouteBinding> postBindings;
    private final Map<Pattern, PatternRouteBinding> deleteBindings;
    private final Map<Pattern, PatternRouteBinding> headBindings;
    private final Map<Pattern, PatternRouteBinding> optionsBindings;
    private final Map<Pattern, PatternRouteBinding> traceBindings;
    private final Map<Pattern, PatternRouteBinding> connectBindings;
    private final Map<Pattern, PatternRouteBinding> patchBindings;
    private HttpRequestHandler noRouteHandler;
    private HttpRequestHandler unsupportedMethodHandler;
    private HttpRequestHandler unsupportedVerbsHandler;
    private Map<Pattern, Set<String>> supportedMethodsForURLs;
    private List<Pattern> knownPatterns;

    private final Set<String> implementedVerbs;
    private static final Logger log = LoggerFactory.getLogger(RouteMatcher.class);

    public RouteMatcher() {
        this.getBindings = new HashMap<Pattern, PatternRouteBinding>();
        this.putBindings = new HashMap<Pattern, PatternRouteBinding>();
        this.postBindings = new HashMap<Pattern, PatternRouteBinding>();
        this.deleteBindings = new HashMap<Pattern, PatternRouteBinding>();
        this.headBindings = new HashMap<Pattern, PatternRouteBinding>();
        this.optionsBindings = new HashMap<Pattern, PatternRouteBinding>();
        this.connectBindings = new HashMap<Pattern, PatternRouteBinding>();
        this.patchBindings = new HashMap<Pattern, PatternRouteBinding>();
        this.traceBindings = new HashMap<Pattern, PatternRouteBinding>();
        this.implementedVerbs = new HashSet<String>();
        this.noRouteHandler = new NoRouteHandler();
        this.unsupportedMethodHandler = new UnsupportedMethodHandler(this);
        this.unsupportedVerbsHandler = new UnsupportedVerbsHandler();
        this.supportedMethodsForURLs = new HashMap<Pattern, Set<String>>();
        this.knownPatterns = new ArrayList<Pattern>();
    }

    public RouteMatcher withNoRouteHandler(HttpRequestHandler noRouteHandler) {
        this.noRouteHandler = noRouteHandler;

        return this;
    }

    public void route(ChannelHandlerContext context, HttpRequest request) {
        final String method = request.getMethod().getName();
        final String URI = request.getUri();

        // Method not implemented for any resource. So return 501.
        if (method == null || !implementedVerbs.contains(method)) {
            route(context, request, unsupportedVerbsHandler);
            return;
        }

        final Pattern pattern = getMatchingPatternForURL(URI);

        // No methods registered for this pattern i.e. URL isn't registered. Return 404.
        if (pattern == null) {
            route(context, request, noRouteHandler);
            return;
        }

        final Set<String> supportedMethods = getSupportedMethods(pattern);
        if (supportedMethods == null) {
            log.warn("No supported methods registered for a known pattern " + pattern);
            route(context, request, noRouteHandler);
            return;
        }

        // The method requested is not available for the resource. Return 405.
        if (!supportedMethods.contains(method)) {
            route(context, request, unsupportedMethodHandler);
            return;
        }

        PatternRouteBinding binding = null;
        if (method.equals(HttpMethod.GET.getName())) {
            binding = getBindings.get(pattern);
        } else if (method.equals(HttpMethod.PUT.getName())) {
            binding = putBindings.get(pattern);
        } else if (method.equals(HttpMethod.POST.getName())) {
            binding = postBindings.get(pattern);
        } else if (method.equals(HttpMethod.DELETE.getName())) {
            binding = deleteBindings.get(pattern);
        } else if (method.equals(HttpMethod.PATCH.getName())) {
            binding = deleteBindings.get(pattern);
        } else if (method.equals(HttpMethod.OPTIONS.getName())) {
            binding = optionsBindings.get(pattern);
         } else if (method.equals(HttpMethod.HEAD.getName())) {
            binding = headBindings.get(pattern);
        } else if (method.equals(HttpMethod.TRACE.getName())) {
            binding = traceBindings.get(pattern);
        } else if (method.equals(HttpMethod.CONNECT.getName())) {
            binding = connectBindings.get(pattern);
        }

        if (binding != null) {
            request = updateRequestHeaders(request, binding);
            route(context, request, binding.handler);
        } else {
            throw new RuntimeException("Cannot find a valid binding for URL " + URI);
        }
    }

    public void get(String pattern, HttpRequestHandler handler) {
        addBinding(pattern, HttpMethod.GET.getName(), handler, getBindings);
    }

    public void put(String pattern, HttpRequestHandler handler) {
        addBinding(pattern, HttpMethod.PUT.getName(), handler, putBindings);
    }

    public void post(String pattern, HttpRequestHandler handler) {
        addBinding(pattern, HttpMethod.POST.getName(), handler, postBindings);
    }

    public void delete(String pattern, HttpRequestHandler handler) {
        addBinding(pattern, HttpMethod.DELETE.getName(), handler, deleteBindings);
    }

    public void head(String pattern, HttpRequestHandler handler) {
        addBinding(pattern, HttpMethod.HEAD.getName(), handler, headBindings);
    }

    public void options(String pattern, HttpRequestHandler handler) {
        addBinding(pattern, HttpMethod.OPTIONS.getName(), handler, optionsBindings);
    }

    public void connect(String pattern, HttpRequestHandler handler) {
        addBinding(pattern, HttpMethod.CONNECT.getName(), handler, connectBindings);
    }

    public void patch(String pattern, HttpRequestHandler handler) {
        addBinding(pattern, HttpMethod.PATCH.getName(), handler, patchBindings);
    }

    public Set<String> getSupportedMethodsForURL(String URL) {
        final Pattern pattern = getMatchingPatternForURL(URL);
        return getSupportedMethods(pattern);
    }

    private HttpRequest updateRequestHeaders(HttpRequest request, PatternRouteBinding binding) {
        Matcher m = binding.pattern.matcher(request.getUri());
        if (m.matches()) {
            Map<String, String> headers = new HashMap<String, String>(m.groupCount());
            if (binding.paramsPositionMap != null) {
                for (String header : binding.paramsPositionMap.keySet()) {
                    headers.put(header, m.group(binding.paramsPositionMap.get(header)));
                }
            } else {
                for (int i = 0; i < m.groupCount(); i++) {
                    headers.put("param" + i, m.group(i + 1));
                }
            }

            for (Map.Entry<String, String> header : headers.entrySet()) {
                request.addHeader(header.getKey(), header.getValue());
            }
        }

        return request;
    }

    private void route(ChannelHandlerContext context, HttpRequest request, HttpRequestHandler handler) {
        if (handler == null) {
            handler = unsupportedVerbsHandler;
        }
        handler.handle(context, request);
    }

    private Pattern getMatchingPatternForURL(String URL) {
        for (Pattern pattern : knownPatterns) {
            if (pattern.matcher(URL).matches()) {
                return pattern;
            }
        }

        return null;
    }

    private Set<String> getSupportedMethods(Pattern pattern) {
        if (pattern == null) {
            return null;
        }

        return supportedMethodsForURLs.get(pattern);
    }

    private void addBinding(String URLPattern, String method, HttpRequestHandler handler,
                            Map<Pattern, PatternRouteBinding> bindings) {
        if (method == null || URLPattern == null || URLPattern.isEmpty() || method.isEmpty()) {
            return;
        }

        if (!method.isEmpty() && !URLPattern.isEmpty()) {
            implementedVerbs.add(method);
        }

        final PatternRouteBinding routeBinding = getPatternRouteBinding(URLPattern, handler);
        knownPatterns.add(routeBinding.pattern);

        Set<String> supportedMethods = supportedMethodsForURLs.get(routeBinding.pattern);

        if (supportedMethods == null) {
            supportedMethods = new HashSet<String>();
        }

        supportedMethods.add(method);
        supportedMethodsForURLs.put(routeBinding.pattern, supportedMethods);
        bindings.put(routeBinding.pattern, routeBinding);
    }

    private PatternRouteBinding getPatternRouteBinding(String URLPattern, HttpRequestHandler handler) {
        // We need to search for any :<token name> tokens in the String and replace them with named capture groups
        Matcher m =  Pattern.compile(":([A-Za-z][A-Za-z0-9_]*)").matcher(URLPattern);

        StringBuffer sb = new StringBuffer();
        Map<String, Integer> groups = new HashMap<String, Integer>();
        int pos = 1;  // group 0 is the whole expression
        while (m.find()) {
            String group = m.group().substring(1);
            if (groups.containsKey(group)) {
                throw new IllegalArgumentException("Cannot use identifier " + group + " more than once in pattern string");
            }
            m.appendReplacement(sb, "([^/]+)");
            groups.put(group, pos++);
        }
        m.appendTail(sb);

        final String regex = sb.toString();
        final Pattern pattern = Pattern.compile(regex);

        return new PatternRouteBinding(pattern, groups, handler);
    }

    private class PatternRouteBinding {
        final HttpRequestHandler handler;
        // TODO: Java 7 has named groups so you don't have to maintain this map explicitly.
        final Map<String, Integer> paramsPositionMap;
        final Pattern pattern;

        private PatternRouteBinding(Pattern pattern, Map<String, Integer> params, HttpRequestHandler handler) {
            this.pattern = pattern;
            this.paramsPositionMap = params;
            this.handler = handler;
        }
    }
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/http/UnsupportedMethodHandler.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.http;

import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.handler.codec.http.*;

import java.util.Set;

public class UnsupportedMethodHandler implements HttpRequestHandler {
    private final RouteMatcher routeMatcher;
    private final HttpResponse response;

    public UnsupportedMethodHandler(RouteMatcher router) {
        this.routeMatcher = router;
        this.response = new DefaultHttpResponse(HttpVersion.HTTP_1_1, HttpResponseStatus.METHOD_NOT_ALLOWED);
    }

    @Override
    public void handle(ChannelHandlerContext context, HttpRequest request) {
        final Set<String> supportedMethods = routeMatcher.getSupportedMethodsForURL(request.getUri());

        StringBuilder result = new StringBuilder();
        for(String string : supportedMethods) {
            result.append(string);
            result.append(",");
        }
        final String methodsAllowed =  result.length() > 0 ? result.substring(0, result.length() - 1): "";
        response.setHeader("Allow", methodsAllowed);
        HttpResponder.respond(context, request, response);
    }
}

File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/http/UnsupportedVerbsHandler.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.http;

import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.handler.codec.http.HttpRequest;
import org.jboss.netty.handler.codec.http.HttpResponseStatus;

public class UnsupportedVerbsHandler implements HttpRequestHandler {

    @Override
    public void handle(ChannelHandlerContext ctx, HttpRequest request) {
        HttpResponder.respond(ctx, request, HttpResponseStatus.NOT_IMPLEMENTED);
    }
}

File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/inputs/handlers/HttpMetricsIngestionHandler.java
/*
 * Copyright 2013-2015 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.inputs.handlers;

import com.codahale.metrics.Counter;
import com.codahale.metrics.Timer;
import com.google.common.util.concurrent.ListenableFuture;
import com.rackspacecloud.blueflood.cache.ConfigTtlProvider;
import com.rackspacecloud.blueflood.exceptions.InvalidDataException;
import com.rackspacecloud.blueflood.http.HttpRequestHandler;
import com.rackspacecloud.blueflood.http.HttpResponder;
import com.rackspacecloud.blueflood.inputs.formats.JSONMetricsContainer;
import com.rackspacecloud.blueflood.io.Constants;
import com.rackspacecloud.blueflood.types.IMetric;
import com.rackspacecloud.blueflood.types.Metric;
import com.rackspacecloud.blueflood.types.MetricsCollection;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.codehaus.jackson.JsonParseException;
import org.codehaus.jackson.map.JsonMappingException;
import org.codehaus.jackson.map.ObjectMapper;
import org.codehaus.jackson.map.type.TypeFactory;
import org.jboss.netty.buffer.ChannelBuffers;
import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.handler.codec.http.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeoutException;

public class HttpMetricsIngestionHandler implements HttpRequestHandler {
    private static final Logger log = LoggerFactory.getLogger(HttpMetricsIngestionHandler.class);
    private static final Counter requestCount = Metrics.counter(HttpMetricsIngestionHandler.class, "HTTP Request Count");


    protected final ObjectMapper mapper;
    protected final TypeFactory typeFactory;
    private final HttpMetricsIngestionServer.Processor processor;
    private final TimeValue timeout;

    // Metrics
    private static final Timer jsonTimer = Metrics.timer(HttpMetricsIngestionHandler.class, "HTTP Ingestion json processing timer");
    private static final Timer persistingTimer = Metrics.timer(HttpMetricsIngestionHandler.class, "HTTP Ingestion persisting timer");
    private static final Timer sendResponseTimer = Metrics.timer(HttpMetricsIngestionHandler.class, "HTTP Ingestion response sending timer");


    public HttpMetricsIngestionHandler(HttpMetricsIngestionServer.Processor processor, TimeValue timeout) {
        this.mapper = new ObjectMapper();
        this.typeFactory = TypeFactory.defaultInstance();
        this.timeout = timeout;
        this.processor = processor;
    }

    protected JSONMetricsContainer createContainer(String body, String tenantId) throws JsonParseException, JsonMappingException, IOException {
        List<JSONMetricsContainer.JSONMetric> jsonMetrics =
                mapper.readValue(
                        body,
                        typeFactory.constructCollectionType(List.class,
                                JSONMetricsContainer.JSONMetric.class)
                );
        return new JSONMetricsContainer(tenantId, jsonMetrics);
    }

    @Override
    public void handle(ChannelHandlerContext ctx, HttpRequest request) {
        try {
            requestCount.inc();
            final String tenantId = request.getHeader("tenantId");
            JSONMetricsContainer jsonMetricsContainer = null;
            final Timer.Context jsonTimerContext = jsonTimer.time();

            final String body = request.getContent().toString(Constants.DEFAULT_CHARSET);
            try {
                jsonMetricsContainer = createContainer(body, tenantId);
                if (!jsonMetricsContainer.isValid()) {
                    throw new IOException("Invalid JSONMetricsContainer");
                }
            } catch (JsonParseException e) {
                log.warn("Exception parsing content", e);
                sendResponse(ctx, request, "Cannot parse content", HttpResponseStatus.BAD_REQUEST);
                return;
            } catch (JsonMappingException e) {
                log.warn("Exception parsing content", e);
                sendResponse(ctx, request, "Cannot parse content", HttpResponseStatus.BAD_REQUEST);
                return;
            } catch (IOException e) {
                log.warn("IO Exception parsing content", e);
                sendResponse(ctx, request, "Cannot parse content", HttpResponseStatus.BAD_REQUEST);
                return;
            } catch (Exception e) {
                log.warn("Other exception while trying to parse content", e);
                sendResponse(ctx, request, "Failed parsing content", HttpResponseStatus.INTERNAL_SERVER_ERROR);
                return;
            }

            if (jsonMetricsContainer == null) {
                log.warn(ctx.getChannel().getRemoteAddress() + " No valid metrics");
                sendResponse(ctx, request, "No valid metrics", HttpResponseStatus.BAD_REQUEST);
                return;
            }

            List<Metric> containerMetrics;
            try {
                containerMetrics = jsonMetricsContainer.toMetrics();
                forceTTLsIfConfigured(containerMetrics);
            } catch (InvalidDataException ex) {
                // todo: we should measure these. if they spike, we track down the bad client.
                // this is strictly a client problem. Someting wasn't right (data out of range, etc.)
                log.warn(ctx.getChannel().getRemoteAddress() + " " + ex.getMessage());
                sendResponse(ctx, request, "Invalid data " + ex.getMessage(), HttpResponseStatus.BAD_REQUEST);
                return;
            } catch (Exception e) {
                // todo: when you see these in logs, go and fix them (throw InvalidDataExceptions) so they can be reduced
                // to single-line log statements.
                log.warn("Exception converting JSON container to metric objects", e);
                // This could happen if clients send BigIntegers as metric values. BF doesn't handle them. So let's send a
                // BAD REQUEST message until we start handling BigIntegers.
                sendResponse(ctx, request, "Error converting JSON payload to metric objects",
                        HttpResponseStatus.BAD_REQUEST);
                return;
            } finally {
                jsonTimerContext.stop();
            }

            if (containerMetrics == null || containerMetrics.isEmpty()) {
                log.warn(ctx.getChannel().getRemoteAddress() + " No valid metrics");
                sendResponse(ctx, request, "No valid metrics", HttpResponseStatus.BAD_REQUEST);
            }

            final MetricsCollection collection = new MetricsCollection();
            collection.add(new ArrayList<IMetric>(containerMetrics));
            final Timer.Context persistingTimerContext = persistingTimer.time();
            try {
                ListenableFuture<List<Boolean>> futures = processor.apply(collection);
                List<Boolean> persisteds = futures.get(timeout.getValue(), timeout.getUnit());
                for (Boolean persisted : persisteds) {
                    if (!persisted) {
                        sendResponse(ctx, request, null, HttpResponseStatus.INTERNAL_SERVER_ERROR);
                        return;
                    }
                }
                sendResponse(ctx, request, null, HttpResponseStatus.OK);
            } catch (TimeoutException e) {
                sendResponse(ctx, request, "Timed out persisting metrics", HttpResponseStatus.ACCEPTED);
            } catch (Exception e) {
                log.error("Exception persisting metrics", e);
                sendResponse(ctx, request, "Error persisting metrics", HttpResponseStatus.INTERNAL_SERVER_ERROR);
            } finally {
                persistingTimerContext.stop();
            }
        } finally {
            requestCount.dec();
        }
    }

    private void forceTTLsIfConfigured(List<Metric> containerMetrics) {
        ConfigTtlProvider configTtlProvider = ConfigTtlProvider.getInstance();

        if(configTtlProvider.areTTLsForced()) {
            for(Metric m : containerMetrics) {
                m.setTtl(configTtlProvider.getConfigTTLForIngestion());
            }
        }
    }

    public static void sendResponse(ChannelHandlerContext channel, HttpRequest request, String messageBody, HttpResponseStatus status) {
        HttpResponse response = new DefaultHttpResponse(HttpVersion.HTTP_1_1, status);
        final Timer.Context sendResponseTimerContext = sendResponseTimer.time();

        try {
            if (messageBody != null && !messageBody.isEmpty()) {
                response.setContent(ChannelBuffers.copiedBuffer(messageBody, Constants.DEFAULT_CHARSET));
            }
            HttpResponder.respond(channel, request, response);
        } finally {
            sendResponseTimerContext.stop();
        }
    }
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/inputs/handlers/HttpMetricsIngestionServer.java
/*
 * Copyright 2013-2015 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.inputs.handlers;

import com.codahale.metrics.Counter;
import com.google.common.util.concurrent.ListenableFuture;
import com.rackspacecloud.blueflood.cache.MetadataCache;
import com.rackspacecloud.blueflood.concurrent.ThreadPoolBuilder;
import com.rackspacecloud.blueflood.http.DefaultHandler;
import com.rackspacecloud.blueflood.http.QueryStringDecoderAndRouter;
import com.rackspacecloud.blueflood.http.RouteMatcher;
import com.rackspacecloud.blueflood.inputs.processors.DiscoveryWriter;
import com.rackspacecloud.blueflood.inputs.processors.BatchWriter;
import com.rackspacecloud.blueflood.inputs.processors.RollupTypeCacher;
import com.rackspacecloud.blueflood.inputs.processors.TypeAndUnitProcessor;
import com.rackspacecloud.blueflood.io.IMetricsWriter;
import com.rackspacecloud.blueflood.service.*;
import com.rackspacecloud.blueflood.types.IMetric;
import com.rackspacecloud.blueflood.types.MetricsCollection;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.jboss.netty.bootstrap.ServerBootstrap;
import org.jboss.netty.channel.ChannelFutureListener;
import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.channel.ChannelPipeline;
import org.jboss.netty.channel.ChannelPipelineFactory;
import org.jboss.netty.channel.ExceptionEvent;
import org.jboss.netty.channel.socket.nio.NioServerSocketChannelFactory;
import org.jboss.netty.handler.codec.http.DefaultHttpResponse;
import org.jboss.netty.handler.codec.http.HttpChunkAggregator;
import org.jboss.netty.handler.codec.http.HttpContentDecompressor;
import org.jboss.netty.handler.codec.http.HttpRequestDecoder;
import org.jboss.netty.handler.codec.http.HttpResponseDecoder;
import org.jboss.netty.handler.codec.http.HttpResponseEncoder;
import org.jboss.netty.handler.codec.http.HttpResponseStatus;
import org.jboss.netty.handler.codec.http.HttpVersion;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.InetSocketAddress;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import static org.jboss.netty.channel.Channels.pipeline;

public class HttpMetricsIngestionServer {
    private static final Logger log = LoggerFactory.getLogger(HttpMetricsIngestionServer.class);
    private static TimeValue DEFAULT_TIMEOUT = new TimeValue(5, TimeUnit.SECONDS);
    private int httpIngestPort;
    private String httpIngestHost;
    private Processor processor;

    private TimeValue timeout;
    private static int MAX_CONTENT_LENGTH = 1048576; // 1 MB
    
    public HttpMetricsIngestionServer(ScheduleContext context, IMetricsWriter writer) {
        this.httpIngestPort = Configuration.getInstance().getIntegerProperty(HttpConfig.HTTP_INGESTION_PORT);
        this.httpIngestHost = Configuration.getInstance().getStringProperty(HttpConfig.HTTP_INGESTION_HOST);
        int acceptThreads = Configuration.getInstance().getIntegerProperty(HttpConfig.MAX_WRITE_ACCEPT_THREADS);
        int workerThreads = Configuration.getInstance().getIntegerProperty(HttpConfig.MAX_WRITE_WORKER_THREADS);
        this.timeout = DEFAULT_TIMEOUT; //TODO: make configurable
        this.processor = new Processor(context, writer, timeout);

        RouteMatcher router = new RouteMatcher();
        router.get("/v1.0", new DefaultHandler());
        router.post("/v1.0/multitenant/experimental/metrics", new HttpMultitenantMetricsIngestionHandler(processor, timeout));
        router.post("/v1.0/:tenantId/experimental/metrics", new HttpMetricsIngestionHandler(processor, timeout));
        router.post("/v1.0/:tenantId/experimental/metrics/statsd", new HttpStatsDIngestionHandler(processor, timeout));

        router.get("/v2.0", new DefaultHandler());
        router.post("/v2.0/:tenantId/ingest/multi", new HttpMultitenantMetricsIngestionHandler(processor, timeout));
        router.post("/v2.0/:tenantId/ingest", new HttpMetricsIngestionHandler(processor, timeout));
        router.post("/v2.0/:tenantId/ingest/aggregated", new HttpStatsDIngestionHandler(processor, timeout));

        log.info("Starting metrics listener HTTP server on port {}", httpIngestPort);
        ServerBootstrap server = new ServerBootstrap(
                new NioServerSocketChannelFactory(
                        Executors.newFixedThreadPool(acceptThreads),
                        Executors.newFixedThreadPool(workerThreads)));

        server.setPipelineFactory(new MetricsHttpServerPipelineFactory(router));
        server.bind(new InetSocketAddress(httpIngestHost, httpIngestPort));
    }

    private class MetricsHttpServerPipelineFactory implements ChannelPipelineFactory {
        private RouteMatcher router;

        public MetricsHttpServerPipelineFactory(RouteMatcher router) {
            this.router = router;
        }

        @Override
        public ChannelPipeline getPipeline() throws Exception {
            final ChannelPipeline pipeline = pipeline();

            pipeline.addLast("decoder", new HttpRequestDecoder() {
                
                // if something bad happens during the decode, assume the client send bad data. return a 400.
                @Override
                public void exceptionCaught(ChannelHandlerContext ctx, ExceptionEvent e) throws Exception {
                    ctx.getChannel().write(
                            new DefaultHttpResponse(HttpVersion.HTTP_1_1,HttpResponseStatus.BAD_REQUEST))
                            .addListener(ChannelFutureListener.CLOSE);
                }
            });
            pipeline.addLast("chunkaggregator", new HttpChunkAggregator(MAX_CONTENT_LENGTH));
            pipeline.addLast("inflater", new HttpContentDecompressor());
            pipeline.addLast("encoder", new HttpResponseEncoder());
            pipeline.addLast("encoder2", new HttpResponseDecoder());
            pipeline.addLast("handler", new QueryStringDecoderAndRouter(router));

            return pipeline;
        }
    }
    static class Processor {
        private static int BATCH_SIZE = Configuration.getInstance().getIntegerProperty(CoreConfig.METRIC_BATCH_SIZE);
        private static int WRITE_THREADS = 
            Configuration.getInstance().getIntegerProperty(CoreConfig.METRICS_BATCH_WRITER_THREADS); // metrics will be batched into this many partitions.

        private final TypeAndUnitProcessor typeAndUnitProcessor;
        private final RollupTypeCacher rollupTypeCacher;
        private final DiscoveryWriter discoveryWriter;
        private final BatchWriter batchWriter;
        private IncomingMetricMetadataAnalyzer metricMetadataAnalyzer =
            new IncomingMetricMetadataAnalyzer(MetadataCache.getInstance());
        private int HTTP_MAX_TYPE_UNIT_PROCESSOR_THREADS = 
            Configuration.getInstance().getIntegerProperty(HttpConfig.HTTP_MAX_TYPE_UNIT_PROCESSOR_THREADS);
        private final Counter bufferedMetrics = Metrics.counter(HttpMetricsIngestionHandler.class, "Buffered Metrics");
        private final TimeValue timeout;

        Processor(ScheduleContext context, IMetricsWriter writer, TimeValue timeout) {
            this.timeout = timeout;

            typeAndUnitProcessor = new TypeAndUnitProcessor(
                new ThreadPoolBuilder()
                    .withName("Metric type and unit processing")
                    .withCorePoolSize(HTTP_MAX_TYPE_UNIT_PROCESSOR_THREADS)
                    .withMaxPoolSize(HTTP_MAX_TYPE_UNIT_PROCESSOR_THREADS)
                    .build(),
                    metricMetadataAnalyzer);
            typeAndUnitProcessor.withLogger(log);

            batchWriter = new BatchWriter(
                    new ThreadPoolBuilder()
                            .withName("Metric Batch Writing")
                            .withCorePoolSize(WRITE_THREADS)
                            .withMaxPoolSize(WRITE_THREADS)
                            .withSynchronousQueue()
                            .build(),
                    writer,
                    timeout,
                    bufferedMetrics,
                    context
            );
            batchWriter.withLogger(log);

            discoveryWriter =
            new DiscoveryWriter(new ThreadPoolBuilder()
                .withName("Metric Discovery Writing")
                .withCorePoolSize(Configuration.getInstance().getIntegerProperty(CoreConfig.DISCOVERY_WRITER_MIN_THREADS))
                .withMaxPoolSize(Configuration.getInstance().getIntegerProperty(CoreConfig.DISCOVERY_WRITER_MAX_THREADS))
                .withUnboundedQueue()
                .build());
            discoveryWriter.withLogger(log);

            // RollupRunnable keeps a static one of these. It would be nice if we could register it and share.
            MetadataCache rollupTypeCache = MetadataCache.createLoadingCacheInstance(
                    new TimeValue(48, TimeUnit.HOURS),
                    Configuration.getInstance().getIntegerProperty(CoreConfig.MAX_ROLLUP_READ_THREADS));
            rollupTypeCacher = new RollupTypeCacher(
                    new ThreadPoolBuilder().withName("Rollup type persistence").build(),
                    rollupTypeCache);
            rollupTypeCacher.withLogger(log);
    
        }

        ListenableFuture<List<Boolean>> apply(MetricsCollection collection) throws Exception {
            typeAndUnitProcessor.apply(collection);
            rollupTypeCacher.apply(collection);
            List<List<IMetric>> batches = collection.splitMetricsIntoBatches(BATCH_SIZE);
            discoveryWriter.apply(batches);
            return batchWriter.apply(batches);
        }
    }
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/inputs/handlers/HttpStatsDIngestionHandler.java
/*
 * Copyright 2014-2015 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.inputs.handlers;

import com.codahale.metrics.Counter;
import com.codahale.metrics.Timer;
import com.google.common.util.concurrent.ListenableFuture;
import com.google.gson.Gson;
import com.google.gson.JsonParseException;
import com.netflix.astyanax.connectionpool.exceptions.ConnectionException;
import com.rackspacecloud.blueflood.concurrent.FunctionWithThreadPool;
import com.rackspacecloud.blueflood.http.HttpRequestHandler;
import com.rackspacecloud.blueflood.inputs.handlers.wrappers.Bundle;
import com.rackspacecloud.blueflood.io.AstyanaxWriter;
import com.rackspacecloud.blueflood.io.CassandraModel;
import com.rackspacecloud.blueflood.io.Constants;
import com.rackspacecloud.blueflood.types.IMetric;
import com.rackspacecloud.blueflood.types.MetricsCollection;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.rackspacecloud.blueflood.utils.TimeValue;
import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.handler.codec.http.HttpRequest;
import org.jboss.netty.handler.codec.http.HttpResponseStatus;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collection;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeoutException;

public class HttpStatsDIngestionHandler implements HttpRequestHandler {
    
    private static final Logger log = LoggerFactory.getLogger(HttpStatsDIngestionHandler.class);
    
    private static final Timer handlerTimer = Metrics.timer(HttpStatsDIngestionHandler.class, "HTTP statsd metrics ingestion timer");
    private static final Counter requestCount = Metrics.counter(HttpStatsDIngestionHandler.class, "HTTP Request Count");
    
    private final HttpMetricsIngestionServer.Processor processor;
    private final TimeValue timeout;
    
    public HttpStatsDIngestionHandler(HttpMetricsIngestionServer.Processor processor, TimeValue timeout) {
        this.processor = processor;
        this.timeout = timeout;
    }
    
    // our own stuff.
    @Override
    public void handle(ChannelHandlerContext ctx, HttpRequest request) {
        
        final Timer.Context timerContext = handlerTimer.time();
        
        // this is all JSON.
        final String body = request.getContent().toString(Constants.DEFAULT_CHARSET);
        try {
            // block until things get ingested.
            requestCount.inc();
            MetricsCollection collection = new MetricsCollection();
            collection.add(PreaggregateConversions.buildMetricsCollection(createBundle(body)));
            ListenableFuture<List<Boolean>> futures = processor.apply(collection);
            List<Boolean> persisteds = futures.get(timeout.getValue(), timeout.getUnit());
            for (Boolean persisted : persisteds) {
                if (!persisted) {
                    HttpMetricsIngestionHandler.sendResponse(ctx, request, null, HttpResponseStatus.INTERNAL_SERVER_ERROR);
                    return;
                }
            }
            HttpMetricsIngestionHandler.sendResponse(ctx, request, null, HttpResponseStatus.OK);

        } catch (JsonParseException ex) {
            log.debug(String.format("BAD JSON: %s", body));
            log.error(ex.getMessage(), ex);
            HttpMetricsIngestionHandler.sendResponse(ctx, request, ex.getMessage(), HttpResponseStatus.BAD_REQUEST);
        } catch (ConnectionException ex) {
            log.error(ex.getMessage(), ex);
            HttpMetricsIngestionHandler.sendResponse(ctx, request, "Internal error saving data", HttpResponseStatus.INTERNAL_SERVER_ERROR);
        } catch (TimeoutException ex) {
            HttpMetricsIngestionHandler.sendResponse(ctx, request, "Timed out persisting metrics", HttpResponseStatus.ACCEPTED);
        } catch (Exception ex) {
            log.debug(String.format("BAD JSON: %s", body));
            log.error("Other exception while trying to parse content", ex);
            HttpMetricsIngestionHandler.sendResponse(ctx, request, "Failed parsing content", HttpResponseStatus.INTERNAL_SERVER_ERROR);
        } finally {
            requestCount.dec();
            timerContext.stop();
        }
    }
    
    public static Bundle createBundle(String json) {
        Bundle bundle = new Gson().fromJson(json, Bundle.class);
        return bundle;
    }

    public static class WriteMetrics extends FunctionWithThreadPool<Collection<IMetric>, ListenableFuture<Boolean>> {
        private final AstyanaxWriter writer;
        
        public WriteMetrics(ThreadPoolExecutor executor, AstyanaxWriter writer) {
            super(executor);
            this.writer = writer;
        }

        @Override
        public ListenableFuture<Boolean> apply(final Collection<IMetric> input) throws Exception {
            return this.getThreadPool().submit(new Callable<Boolean>() {
                @Override
                public Boolean call() throws Exception {
                    writer.insertMetrics(input, CassandraModel.CF_METRICS_PREAGGREGATED_FULL);
                    return true;
                }
            });
        }
    }
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/outputs/handlers/HttpHistogramQueryHandler.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.handlers;

import com.codahale.metrics.Meter;
import com.codahale.metrics.Timer;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import com.rackspacecloud.blueflood.exceptions.InvalidRequestException;
import com.rackspacecloud.blueflood.exceptions.SerializationException;
import com.rackspacecloud.blueflood.http.HTTPRequestWithDecodedQueryParams;
import com.rackspacecloud.blueflood.http.HttpRequestHandler;
import com.rackspacecloud.blueflood.http.HttpResponder;
import com.rackspacecloud.blueflood.io.Constants;
import com.rackspacecloud.blueflood.outputs.serializers.JSONHistogramOutputSerializer;
import com.rackspacecloud.blueflood.outputs.utils.PlotRequestParser;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.types.Resolution;
import com.rackspacecloud.blueflood.outputs.utils.RollupsQueryParams;
import com.rackspacecloud.blueflood.utils.Metrics;
import org.jboss.netty.buffer.ChannelBuffers;
import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.handler.codec.http.*;
import org.json.simple.JSONObject;

import java.io.IOException;

public class HttpHistogramQueryHandler extends RollupHandler implements HttpRequestHandler {
    private final JSONHistogramOutputSerializer serializer;
    private final Gson gson;           // thread-safe
    private final JsonParser parser;   // thread-safe

    private static final Timer histFetchTimer = Metrics.timer(HttpRollupsQueryHandler.class,
            "Handle HTTP request for histograms");
    private static final Meter histByPointsMeter = Metrics.meter(RollupHandler.class, "Get histograms by points",
            "BF-API");
    private static final Meter histByGranularityMeter = Metrics.meter(RollupHandler.class, "Get histograms by gran",
            "BF-API");

    public HttpHistogramQueryHandler() {
        this.gson = new GsonBuilder().setPrettyPrinting().serializeNulls().create();
        this.parser = new JsonParser();
        this.serializer = new JSONHistogramOutputSerializer();
    }

    private JSONObject GetHistogramByPoints(String tenantId,
                                       String metric,
                                       long from,
                                       long to,
                                       int points) throws IOException, SerializationException {
        histByPointsMeter.mark();
        Granularity g = Granularity.granularityFromPointsInInterval(tenantId,from, to, points);
        return serializer.transformHistogram(getHistogramsByGranularity(tenantId, metric, from, to, g));
    }

    private JSONObject GetHistogramByResolution(String tenantId,
                                            String metric,
                                            long from,
                                            long to,
                                            Resolution resolution) throws IOException, SerializationException {
        histByGranularityMeter.mark();
        if (resolution == null || resolution == Resolution.FULL) {
            resolution = Resolution.MIN5;
        }
        Granularity g = Granularity.granularities()[resolution.getValue()];
        return serializer.transformHistogram(getHistogramsByGranularity(tenantId, metric, from, to, g));
    }

    @Override
    public void handle(ChannelHandlerContext ctx, HttpRequest request) {
        final String tenantId = request.getHeader("tenantId");
        final String metricName = request.getHeader("metricName");

        if (!(request instanceof HTTPRequestWithDecodedQueryParams)) {
            sendResponse(ctx, request, "Missing query params: from, to, points",
                    HttpResponseStatus.BAD_REQUEST);
            return;
        }

        HTTPRequestWithDecodedQueryParams requestWithParams = (HTTPRequestWithDecodedQueryParams) request;
        final Timer.Context histFetchTimerContext = histFetchTimer.time();

        try {
            RollupsQueryParams params = PlotRequestParser.parseParams(requestWithParams.getQueryParams());

            JSONObject metricData;
            if (params.isGetByPoints()) {
                metricData = GetHistogramByPoints(tenantId, metricName, params.getRange().getStart(),
                        params.getRange().getStop(), params.getPoints());
            } else if (params.isGetByResolution()) {
                metricData = GetHistogramByResolution(tenantId, metricName, params.getRange().getStart(),
                        params.getRange().getStop(), params.getResolution());
            } else {
                throw new InvalidRequestException("Invalid rollups query. Neither points nor resolution specified.");
            }
            final JsonElement element = parser.parse(metricData.toString());
            final String jsonStringRep = gson.toJson(element);
            sendResponse(ctx, request, jsonStringRep, HttpResponseStatus.OK);
        } catch (InvalidRequestException e) {
            sendResponse(ctx, request, e.getMessage(), HttpResponseStatus.BAD_REQUEST);
        } catch (SerializationException e) {
            sendResponse(ctx, request, e.getMessage(), HttpResponseStatus.INTERNAL_SERVER_ERROR);
        } catch (Exception e) {
            sendResponse(ctx, request, e.getMessage(), HttpResponseStatus.INTERNAL_SERVER_ERROR);
        } finally {
            histFetchTimerContext.stop();
        }
    }

    private void sendResponse(ChannelHandlerContext channel, HttpRequest request, String messageBody,
                              HttpResponseStatus status) {
        HttpResponse response = new DefaultHttpResponse(HttpVersion.HTTP_1_1, status);

        if (messageBody != null && !messageBody.isEmpty()) {
            response.setContent(ChannelBuffers.copiedBuffer(messageBody, Constants.DEFAULT_CHARSET));
        }
        HttpResponder.respond(channel, request, response);
    }
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/outputs/handlers/HttpMetricDataQueryServer.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.handlers;

import com.google.common.annotations.VisibleForTesting;
import com.rackspacecloud.blueflood.http.DefaultHandler;
import com.rackspacecloud.blueflood.http.QueryStringDecoderAndRouter;
import com.rackspacecloud.blueflood.http.RouteMatcher;
import com.rackspacecloud.blueflood.service.Configuration;
import com.rackspacecloud.blueflood.service.HttpConfig;
import org.jboss.netty.bootstrap.ServerBootstrap;
import org.jboss.netty.channel.ChannelPipeline;
import org.jboss.netty.channel.ChannelPipelineFactory;
import org.jboss.netty.channel.socket.nio.NioServerSocketChannelFactory;
import org.jboss.netty.handler.codec.http.HttpRequestDecoder;
import org.jboss.netty.handler.codec.http.HttpResponseEncoder;
import org.jboss.netty.channel.ServerChannel;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.InetSocketAddress;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import static org.jboss.netty.channel.Channels.pipeline;

public class HttpMetricDataQueryServer {
    private static final Logger log = LoggerFactory.getLogger(HttpMetricDataQueryServer.class);
    private final int httpQueryPort;
    private final String httpQueryHost;
    private ServerChannel serverChannel;

    public HttpMetricDataQueryServer() {
        this.httpQueryPort = Configuration.getInstance().getIntegerProperty(HttpConfig.HTTP_METRIC_DATA_QUERY_PORT);
        this.httpQueryHost = Configuration.getInstance().getStringProperty(HttpConfig.HTTP_QUERY_HOST);
        int acceptThreads = Configuration.getInstance().getIntegerProperty(HttpConfig.MAX_READ_ACCEPT_THREADS);
        int workerThreads = Configuration.getInstance().getIntegerProperty(HttpConfig.MAX_READ_WORKER_THREADS);

        RouteMatcher router = new RouteMatcher();
        router.get("/v1.0", new DefaultHandler());
        router.get("/v1.0/:tenantId/experimental/views/metric_data/:metricName", new HttpRollupsQueryHandler());
        router.post("/v1.0/:tenantId/experimental/views/metric_data", new HttpMultiRollupsQueryHandler());
        router.get("/v1.0/:tenantId/experimental/views/histograms/:metricName", new HttpHistogramQueryHandler());

        router.get("/v2.0", new DefaultHandler());
        router.get("/v2.0/:tenantId/views/:metricName", new HttpRollupsQueryHandler());
        router.post("/v2.0/:tenantId/views", new HttpMultiRollupsQueryHandler());
        router.get("/v2.0/:tenantId/views/histograms/:metricName", new HttpHistogramQueryHandler());
        router.get("/v2.0/:tenantId/metrics/search", new HttpMetricsIndexHandler());

        log.info("Starting metric data query server (HTTP) on port {}", this.httpQueryPort);
        ServerBootstrap server = new ServerBootstrap(
                    new NioServerSocketChannelFactory(
                            Executors.newFixedThreadPool(acceptThreads),
                            Executors.newFixedThreadPool(workerThreads)));
        server.setPipelineFactory(new MetricsHttpServerPipelineFactory(router));
        serverChannel =  (ServerChannel) server.bind(new InetSocketAddress(httpQueryHost, httpQueryPort));
    }

    private class MetricsHttpServerPipelineFactory implements ChannelPipelineFactory {
        private RouteMatcher router;

        public MetricsHttpServerPipelineFactory(RouteMatcher router) {
            this.router = router;
        }

        @Override
        public ChannelPipeline getPipeline() throws Exception {
            final ChannelPipeline pipeline = pipeline();

            pipeline.addLast("decoder", new HttpRequestDecoder());
            pipeline.addLast("encoder", new HttpResponseEncoder());
            pipeline.addLast("handler", new QueryStringDecoderAndRouter(router));

            return pipeline;
        }
    }

    @VisibleForTesting
    public void stopServer() {
        try {
            serverChannel.close().await(5, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            // Pass
        }
    }
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/outputs/handlers/HttpMultiRollupsQueryHandler.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.handlers;

import com.google.gson.*;
import com.rackspacecloud.blueflood.concurrent.ThreadPoolBuilder;
import com.rackspacecloud.blueflood.exceptions.InvalidRequestException;
import com.rackspacecloud.blueflood.exceptions.SerializationException;
import com.rackspacecloud.blueflood.http.HTTPRequestWithDecodedQueryParams;
import com.rackspacecloud.blueflood.http.HttpRequestHandler;
import com.rackspacecloud.blueflood.http.HttpResponder;
import com.rackspacecloud.blueflood.io.Constants;
import com.rackspacecloud.blueflood.outputs.formats.MetricData;
import com.rackspacecloud.blueflood.outputs.serializers.BatchedMetricsJSONOutputSerializer;
import com.rackspacecloud.blueflood.outputs.serializers.BatchedMetricsOutputSerializer;
import com.rackspacecloud.blueflood.outputs.utils.PlotRequestParser;
import com.rackspacecloud.blueflood.service.Configuration;
import com.rackspacecloud.blueflood.service.HttpConfig;
import com.rackspacecloud.blueflood.types.Locator;
import com.rackspacecloud.blueflood.outputs.utils.RollupsQueryParams;
import com.rackspacecloud.blueflood.utils.TimeValue;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.codahale.metrics.Timer;
import org.jboss.netty.buffer.ChannelBuffers;
import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.handler.codec.http.*;
import org.json.simple.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

public class HttpMultiRollupsQueryHandler extends RollupHandler implements HttpRequestHandler {
    private static final Logger log = LoggerFactory.getLogger(HttpMultiRollupsQueryHandler.class);
    private final BatchedMetricsOutputSerializer<JSONObject> serializer;
    private final Gson gson;           // thread-safe
    private final JsonParser parser;   // thread-safe
    private final Timer httpBatchMetricsFetchTimer = Metrics.timer(HttpMultiRollupsQueryHandler.class,
            "Handle HTTP batch request for metrics");
    private final ThreadPoolExecutor executor;
    private final int maxMetricsPerRequest;

    public HttpMultiRollupsQueryHandler() {
        Configuration config = Configuration.getInstance();
        int maxThreadsToUse = config.getIntegerProperty(HttpConfig.MAX_READ_WORKER_THREADS);
        int maxQueueSize = config.getIntegerProperty(HttpConfig.MAX_BATCH_READ_REQUESTS_TO_QUEUE);
        this.maxMetricsPerRequest = config.getIntegerProperty(HttpConfig.MAX_METRICS_PER_BATCH_QUERY);
        this.serializer = new BatchedMetricsJSONOutputSerializer();
        this.gson = new GsonBuilder().setPrettyPrinting().serializeNulls().create();
        this.parser = new JsonParser();
        this.executor = new ThreadPoolBuilder().withCorePoolSize(maxThreadsToUse).withMaxPoolSize(maxThreadsToUse)
                .withName("HTTP-BatchMetricsFetch").withBoundedQueue(maxQueueSize).build();
    }

    @Override
    public void handle(ChannelHandlerContext ctx, HttpRequest request) {
        final String tenantId = request.getHeader("tenantId");

        if (!(request instanceof HTTPRequestWithDecodedQueryParams)) {
            sendResponse(ctx, request, "Missing query params: from, to, points",
                    HttpResponseStatus.BAD_REQUEST);
            return;
        }

        final String body = request.getContent().toString(Constants.DEFAULT_CHARSET);

        if (body == null || body.isEmpty()) {
            sendResponse(ctx, request, "Invalid body. Expected JSON array of metrics.",
                    HttpResponseStatus.BAD_REQUEST);
            return;
        }

        List<String> locators = new ArrayList<String>();
        try {
            locators.addAll(getLocatorsFromJSONBody(tenantId, body));
        } catch (Exception ex) {
            log.debug(ex.getMessage(), ex);
            sendResponse(ctx, request, ex.getMessage(), HttpResponseStatus.BAD_REQUEST);
            return;
        }

        if (locators.size() > maxMetricsPerRequest) {
            sendResponse(ctx, request, "Too many metrics fetch in a single call. Max limit is " + maxMetricsPerRequest
                    + ".", HttpResponseStatus.BAD_REQUEST);
            return;
        }

        HTTPRequestWithDecodedQueryParams requestWithParams = (HTTPRequestWithDecodedQueryParams) request;
        final Timer.Context httpBatchMetricsFetchTimerContext = httpBatchMetricsFetchTimer.time();
        try {
            RollupsQueryParams params = PlotRequestParser.parseParams(requestWithParams.getQueryParams());
            Map<Locator, MetricData> results = getRollupByGranularity(tenantId, locators, params.getRange().getStart(), params.getRange().getStop(), params.getGranularity(tenantId));
            JSONObject metrics = serializer.transformRollupData(results, params.getStats());
            final JsonElement element = parser.parse(metrics.toString());
            final String jsonStringRep = gson.toJson(element);
            sendResponse(ctx, request, jsonStringRep, HttpResponseStatus.OK);
        } catch (InvalidRequestException e) {
            log.debug(e.getMessage());
            sendResponse(ctx, request, e.getMessage(), HttpResponseStatus.BAD_REQUEST);
        } catch (SerializationException e) {
            log.debug(e.getMessage(), e);
            sendResponse(ctx, request, e.getMessage(), HttpResponseStatus.INTERNAL_SERVER_ERROR);
        } catch (Exception e) {
            log.error(e.getMessage(), e);
            sendResponse(ctx, request, e.getMessage(), HttpResponseStatus.INTERNAL_SERVER_ERROR);
        } finally {
            httpBatchMetricsFetchTimerContext.stop();
        }
    }

    private List<String> getLocatorsFromJSONBody(String tenantId, String body) {
        JsonElement element = gson.fromJson(body, JsonElement.class);
        JsonArray metrics = element.getAsJsonArray();
        final List<String> locators = new ArrayList<String>();

        Iterator<JsonElement> it = metrics.iterator();
        while (it.hasNext()) {
            JsonElement metricElement = it.next();
            locators.add( metricElement.getAsString());
        }

        return locators;
    }

    private void sendResponse(ChannelHandlerContext channel, HttpRequest request, String messageBody,
                              HttpResponseStatus status) {
        HttpResponse response = new DefaultHttpResponse(HttpVersion.HTTP_1_1, status);

        if (messageBody != null && !messageBody.isEmpty()) {
            response.setContent(ChannelBuffers.copiedBuffer(messageBody, Constants.DEFAULT_CHARSET));
        }
        HttpResponder.respond(channel, request, response);
    }
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/outputs/handlers/HttpRollupsQueryHandler.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.handlers;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import com.rackspacecloud.blueflood.exceptions.InvalidRequestException;
import com.rackspacecloud.blueflood.exceptions.SerializationException;
import com.rackspacecloud.blueflood.http.HTTPRequestWithDecodedQueryParams;
import com.rackspacecloud.blueflood.http.HttpRequestHandler;
import com.rackspacecloud.blueflood.http.HttpResponder;
import com.rackspacecloud.blueflood.io.Constants;
import com.rackspacecloud.blueflood.outputs.formats.MetricData;
import com.rackspacecloud.blueflood.outputs.serializers.BasicRollupsOutputSerializer;
import com.rackspacecloud.blueflood.outputs.serializers.JSONBasicRollupsOutputSerializer;
import com.rackspacecloud.blueflood.outputs.serializers.BasicRollupsOutputSerializer.MetricStat;
import com.rackspacecloud.blueflood.outputs.utils.PlotRequestParser;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.types.Locator;
import com.rackspacecloud.blueflood.types.Resolution;
import com.rackspacecloud.blueflood.outputs.utils.RollupsQueryParams;
import com.rackspacecloud.blueflood.utils.Metrics;
import com.codahale.metrics.Timer;
import org.jboss.netty.buffer.ChannelBuffers;
import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.handler.codec.http.*;
import org.json.simple.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.TimeUnit;

public class HttpRollupsQueryHandler extends RollupHandler
            implements MetricDataQueryInterface<MetricData>, HttpRequestHandler {
    private static final Logger log = LoggerFactory.getLogger(HttpRollupsQueryHandler.class);
    
    private final BasicRollupsOutputSerializer<JSONObject> serializer;
    private final Gson gson;           // thread-safe
    private final JsonParser parser;   // thread-safe
    private final Timer httpMetricsFetchTimer = Metrics.timer(HttpRollupsQueryHandler.class,
            "Handle HTTP request for metrics");

    public HttpRollupsQueryHandler() {
        this.serializer = new JSONBasicRollupsOutputSerializer();
        this.gson = new GsonBuilder().setPrettyPrinting().serializeNulls().create();
        this.parser = new JsonParser();
    }

    private JSONObject GetDataByPoints(String tenantId,
                                      String metric,
                                      long from,
                                      long to,
                                      int points,
                                      Set<MetricStat> stats) throws SerializationException {
        return serializer.transformRollupData(GetDataByPoints(tenantId, metric, from, to, points), stats);
    }

    private JSONObject GetDataByResolution(String tenantId,
                                      String metric,
                                      long from,
                                      long to,
                                      Resolution resolution,
                                      Set<MetricStat> stats) throws SerializationException {
        return serializer.transformRollupData(GetDataByResolution(tenantId, metric, from, to, resolution), stats);
    }

    @Override
    public MetricData GetDataByPoints(String tenantId,
                                      String metric,
                                      long from,
                                      long to,
                                      int points) throws SerializationException {
        rollupsByPointsMeter.mark();
        Granularity g = Granularity.granularityFromPointsInInterval(tenantId, from, to, points);
        return getRollupByGranularity(tenantId, Arrays.asList(metric), from, to, g).get(Locator.createLocatorFromPathComponents(tenantId, metric));
    }

    @Override
    public MetricData GetDataByResolution(String tenantId,
                                          String metric,
                                          long from,
                                          long to,
                                          Resolution resolution) throws SerializationException {
        rollupsByGranularityMeter.mark();
        if (resolution == null) {
            resolution = Resolution.FULL;
        }
        Granularity g = Granularity.granularities()[resolution.getValue()];
        return getRollupByGranularity(tenantId, Arrays.asList(metric), from, to, g).get(Locator.createLocatorFromPathComponents(tenantId, metric));
    }

    @Override
    public void handle(ChannelHandlerContext ctx, HttpRequest request) {
        final String tenantId = request.getHeader("tenantId");
        final String metricName = request.getHeader("metricName");

        if (!(request instanceof HTTPRequestWithDecodedQueryParams)) {
            sendResponse(ctx, request, "Missing query params: from, to, points",
                    HttpResponseStatus.BAD_REQUEST);
            return;
        }

        HTTPRequestWithDecodedQueryParams requestWithParams = (HTTPRequestWithDecodedQueryParams) request;

        final Timer.Context httpMetricsFetchTimerContext = httpMetricsFetchTimer.time();
        try {
            RollupsQueryParams params = PlotRequestParser.parseParams(requestWithParams.getQueryParams());

            JSONObject metricData;
            if (params.isGetByPoints()) {
                metricData = GetDataByPoints(tenantId, metricName, params.getRange().getStart(),
                        params.getRange().getStop(), params.getPoints(), params.getStats());
            } else if (params.isGetByResolution()) {
                metricData = GetDataByResolution(tenantId, metricName, params.getRange().getStart(),
                        params.getRange().getStop(), params.getResolution(), params.getStats());
            } else {
                throw new InvalidRequestException("Invalid rollups query. Neither points nor resolution specified.");
            }

            final JsonElement element = parser.parse(metricData.toString());
            final String jsonStringRep = gson.toJson(element);
            sendResponse(ctx, request, jsonStringRep, HttpResponseStatus.OK);
        } catch (InvalidRequestException e) {
            // let's not log the full exception, just the message.
            log.warn(e.getMessage());
            sendResponse(ctx, request, e.getMessage(), HttpResponseStatus.BAD_REQUEST);
        } catch (SerializationException e) {
            log.error(e.getMessage(), e);
            sendResponse(ctx, request, e.getMessage(), HttpResponseStatus.INTERNAL_SERVER_ERROR);
        } catch (Exception e) {
            log.error(e.getMessage(), e);
            sendResponse(ctx, request, e.getMessage(), HttpResponseStatus.INTERNAL_SERVER_ERROR);
        } finally {
            httpMetricsFetchTimerContext.stop();
        }
    }

    private void sendResponse(ChannelHandlerContext channel, HttpRequest request, String messageBody,
                             HttpResponseStatus status) {
        HttpResponse response = new DefaultHttpResponse(HttpVersion.HTTP_1_1, status);

        if (messageBody != null && !messageBody.isEmpty()) {
            response.setContent(ChannelBuffers.copiedBuffer(messageBody, Constants.DEFAULT_CHARSET));
        }
        HttpResponder.respond(channel, request, response);
    }
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/outputs/serializers/BasicRollupsOutputSerializer.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.serializers;

import com.rackspacecloud.blueflood.exceptions.SerializationException;
import com.rackspacecloud.blueflood.outputs.formats.MetricData;
import com.rackspacecloud.blueflood.types.BasicRollup;
import com.rackspacecloud.blueflood.types.CounterRollup;
import com.rackspacecloud.blueflood.types.GaugeRollup;
import com.rackspacecloud.blueflood.types.Rollup;
import com.rackspacecloud.blueflood.types.SetRollup;
import com.rackspacecloud.blueflood.types.TimerRollup;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public interface BasicRollupsOutputSerializer<T> {
    public T transformRollupData(MetricData metricData, Set<MetricStat> filterStats) throws SerializationException;

    public static enum MetricStat {
        AVERAGE("average") {
            @Override
            Object convertRollupToObject(Rollup rollup) throws Exception {
                if (rollup instanceof BasicRollup)
                    return ((BasicRollup) rollup).getAverage();
                else if (rollup instanceof TimerRollup)
                    return ((TimerRollup) rollup).getAverage();
                else
                    // counters, sets
                    throw new Exception(String.format("average not supported for this type: %s", rollup.getClass().getSimpleName()));
            }

            @Override
            Object convertRawSampleToObject(Object rawSample) {
                return rawSample;
            }
        },
        VARIANCE("variance") {
            @Override
            Object convertRollupToObject(Rollup rollup) throws Exception {
                if (rollup instanceof BasicRollup)
                    return ((BasicRollup) rollup).getVariance();
                else if (rollup instanceof TimerRollup)
                    return ((TimerRollup) rollup).getVariance();
                else
                    // counters, sets.
                    throw new Exception(String.format("variance not supported for this type: %s", rollup.getClass().getSimpleName()));
            }

            @Override
            Object convertRawSampleToObject(Object rawSample) {
                return 0;
            }
        },
        MIN("min") {
            @Override
            Object convertRollupToObject(Rollup rollup) throws Exception {
                if (rollup instanceof BasicRollup)
                    return ((BasicRollup) rollup).getMinValue();
                else if (rollup instanceof TimerRollup)
                    return ((TimerRollup) rollup).getMinValue();
                else
                    // counters, sets.
                    throw new Exception(String.format("min not supported for this type: %s", rollup.getClass().getSimpleName()));
            }

            @Override
            Object convertRawSampleToObject(Object rawSample) {
                return rawSample;
            }
        },
        MAX("max") {
            @Override
            Object convertRollupToObject(Rollup rollup) throws Exception {
                if (rollup instanceof BasicRollup)
                    return ((BasicRollup) rollup).getMaxValue();
                else if (rollup instanceof TimerRollup)
                    return ((TimerRollup) rollup).getMaxValue();
                else
                    // counters, sets.
                    throw new Exception(String.format("min not supported for this type: %s", rollup.getClass().getSimpleName()));
            }

            @Override
            Object convertRawSampleToObject(Object rawSample) {
                return rawSample;
            }
        },
        NUM_POINTS("numPoints") {
            @Override
            Object convertRollupToObject(Rollup rollup) throws Exception {
                if (rollup instanceof BasicRollup)
                    return ((BasicRollup) rollup).getCount();
                else if (rollup instanceof TimerRollup)
                    return ((TimerRollup) rollup).getCount();
                else if (rollup instanceof CounterRollup)
                    return ((CounterRollup) rollup).getCount();
                else if (rollup instanceof SetRollup)
                    return ((SetRollup) rollup).getCount();
                else
                    // gauge.
                    throw new Exception(String.format("numPoints not supported for this type: %s", rollup.getClass().getSimpleName()));
            }

            @Override
            Object convertRawSampleToObject(Object rawSample) {
                return 1;
            }
        },
        LATEST("latest") {
            @Override
            Object convertRollupToObject(Rollup rollup) throws Exception {
                if (rollup instanceof GaugeRollup)
                    return ((GaugeRollup) rollup).getLatestValue().getValue();
                else
                    // every other type.
                    throw new Exception(String.format("latest value not supported for this type: %s", rollup.getClass().getSimpleName()));
            }

            @Override
            Object convertRawSampleToObject(Object rawSample) {
                return rawSample;
            }
        },
        RATE("rate") {
            @Override
            Object convertRollupToObject(Rollup rollup) throws Exception {
                if (rollup instanceof TimerRollup)
                    return ((TimerRollup) rollup).getRate();
                else if (rollup instanceof CounterRollup)
                    return ((CounterRollup) rollup).getRate();
                else
                    // gauge, set, basic
                    throw new Exception(String.format("rate not supported for this type: %s", rollup.getClass().getSimpleName()));
            }

            @Override
            Object convertRawSampleToObject(Object rawSample) {
                return rawSample;
            }
        },
        SUM("sum") {
            @Override
            Object convertRollupToObject(Rollup rollup) throws Exception {
                if (rollup instanceof TimerRollup)
                    return ((TimerRollup) rollup).getSum();
                else if (rollup instanceof CounterRollup)
                    return ((CounterRollup) rollup).getCount();
                else
                    // every other type.
                    throw new Exception(String.format("sum not supported for this type: %s", rollup.getClass().getSimpleName()));
            }

            @Override
            Object convertRawSampleToObject(Object rawSample) {
                return rawSample;
            }
        },
        PERCENTILE("percentiles") {
            @Override
            Object convertRollupToObject(Rollup rollup) throws Exception {
                if (rollup instanceof TimerRollup)
                    return ((TimerRollup) rollup).getPercentiles();
                else
                    // every other type.
                    throw new Exception(String.format("percentiles supported for this type: %s", rollup.getClass().getSimpleName()));
            }

            @Override
            Object convertRawSampleToObject(Object rawSample) {
                return rawSample;
            }
        }
        ;
        
        private MetricStat(String s) {
            this.stringRep = s;
        }
        private String stringRep;
        private static final Map<String, MetricStat> stringToEnum = new HashMap<String, MetricStat>();
        static {
            for (MetricStat ms : values()) {
                stringToEnum.put(ms.toString().toLowerCase(), ms);
            }
        }
        public static MetricStat fromString(String s) {
            return stringToEnum.get(s.toLowerCase());
        }
        public static Set<MetricStat> fromStringList(List<String> statList) {
            Set<MetricStat> set = new HashSet<MetricStat>();
            for (String stat : statList ) {
                MetricStat metricStat = fromString(stat);
                if (metricStat != null) {
                    set.add(fromString(stat));
                }
            }
            return set;
        }
        @Override
        public String toString() {
            return this.stringRep;
        }
        abstract Object convertRollupToObject(Rollup rollup) throws Exception;
        abstract Object convertRawSampleToObject(Object rawSample);
    }
}



File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/outputs/serializers/BatchedMetricsJSONOutputSerializer.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.serializers;


import com.rackspacecloud.blueflood.exceptions.SerializationException;
import com.rackspacecloud.blueflood.outputs.formats.MetricData;
import com.rackspacecloud.blueflood.types.Locator;
import com.rackspacecloud.blueflood.utils.Util;
import org.json.simple.JSONArray;
import org.json.simple.JSONObject;

import java.util.Map;
import java.util.Set;

public class BatchedMetricsJSONOutputSerializer extends JSONBasicRollupsOutputSerializer
        implements BatchedMetricsOutputSerializer<JSONObject> {

    @Override
    public JSONObject transformRollupData(Map<Locator, MetricData> metricData, Set<MetricStat> filterStats)
            throws SerializationException {
        final JSONObject globalJSON = new JSONObject();
        final JSONArray metricsArray = new JSONArray();

        for (Map.Entry<Locator, MetricData> one : metricData.entrySet()) {
            final JSONObject singleMetricJSON = new JSONObject();
            singleMetricJSON.put("metric", one.getKey().getMetricName());
            singleMetricJSON.put("unit", one.getValue().getUnit() == null ? Util.UNKNOWN : one.getValue().getUnit());
            singleMetricJSON.put("type", one.getValue().getType());
            JSONArray values = transformDataToJSONArray(one.getValue(), filterStats);
            singleMetricJSON.put("data", values);
            metricsArray.add(singleMetricJSON);
        }

        globalJSON.put("metrics", metricsArray);
        return globalJSON;
    }
}



File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/outputs/serializers/BatchedMetricsOutputSerializer.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.serializers;

import com.rackspacecloud.blueflood.exceptions.SerializationException;
import com.rackspacecloud.blueflood.outputs.formats.MetricData;
import com.rackspacecloud.blueflood.types.Locator;

import java.util.Map;
import java.util.Set;

public interface BatchedMetricsOutputSerializer<T> extends BasicRollupsOutputSerializer<T> {
    public T transformRollupData(Map<Locator, MetricData> metricData, Set<MetricStat> filterStats)
            throws SerializationException;
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/outputs/serializers/FakeMetricDataGenerator.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.serializers;

import com.bigml.histogram.Bin;
import com.bigml.histogram.SimpleTarget;
import com.bigml.histogram.Target;
import com.rackspacecloud.blueflood.types.BasicRollup;
import com.rackspacecloud.blueflood.types.CounterRollup;
import com.rackspacecloud.blueflood.types.GaugeRollup;
import com.rackspacecloud.blueflood.types.HistogramRollup;
import com.rackspacecloud.blueflood.types.Points;
import com.rackspacecloud.blueflood.types.SetRollup;
import com.rackspacecloud.blueflood.types.SimpleNumber;
import com.rackspacecloud.blueflood.types.TimerRollup;

import java.util.ArrayList;
import java.util.Collection;

public class FakeMetricDataGenerator {
    public static Points<SimpleNumber> generateFakeFullResPoints() {
        Points<SimpleNumber> points = new Points<SimpleNumber>();

        long baseTime = 1234567L;
        for (int count = 0; count < 5; count++) {
            Points.Point<SimpleNumber> point = new Points.Point<SimpleNumber>(baseTime + (count*1000), new SimpleNumber((long) count));
            points.add(point);
        }

        return points;
    }

    public static Points<BasicRollup> generateFakeRollupPoints() {
        Points<BasicRollup> points = new Points<BasicRollup>();

        long baseTime = 1234567L;
        for (int count = 0; count < 5; count++) {
            final BasicRollup basicRollup = new BasicRollup();
            basicRollup.setCount(count * 100);
            basicRollup.getAverage().setLongValue(count);
            Points.Point<BasicRollup> point = new Points.Point<BasicRollup>(baseTime + (count*1000), basicRollup);
            points.add(point);
        }

        return points;
    }

    public static Points<String> generateFakeStringPoints() {
        Points<String> points = new Points<String>();
        long startTime = 1234567L;
        for (int i =0; i < 5; i++) {
            long timeNow = startTime + i*1000;
            Points.Point<String> point = new Points.Point<String>(timeNow, String.valueOf(timeNow));
            points.add(point);
        }
        return points;
    }

    public static Points<HistogramRollup> generateFakeHistogramRollupPoints() {
        Points<HistogramRollup> points = new Points<HistogramRollup>();
        long startTime = 1234567L;
        for (int i =0; i < 5; i++) {
            long timeNow = startTime + i*1000;
            Points.Point<HistogramRollup> point = new Points.Point<HistogramRollup>(timeNow,
                    new HistogramRollup(getBins()));
            points.add(point);
        }
        return points;
    }

    private static Collection<Bin<SimpleTarget>> getBins() {
        Collection<Bin<SimpleTarget>> bins = new ArrayList<Bin<SimpleTarget>>();
        for (int i = 1; i < 3; i++) {
            bins.add(new Bin(55.55 + i, (double) i, SimpleTarget.TARGET));
        }
        return bins;
    }
    
    public static Points<CounterRollup> generateFakeCounterRollupPoints() {
        Points<CounterRollup> points = new Points<CounterRollup>();
        long startTime = 1234567L;
        for (int i = 0; i < 5; i++) {
            long timeNow = startTime + i*1000;
            Points.Point<CounterRollup> point = new Points.Point<CounterRollup>(timeNow, new CounterRollup()
                    .withCount(i + 1000)
                    .withRate((double) i)
                    .withSampleCount(1));
            points.add(point);
        }
        return points;
    }
    
    public static Points<SetRollup> generateFakeSetRollupPoints() {
        Points<SetRollup> points = new Points<SetRollup>();
        long startTime = 1234567L;
        for (int i = 0; i < 5; i++) {
            long timeNow = startTime + i*1000;
            Points.Point<SetRollup> point = new Points.Point<SetRollup>(timeNow, new SetRollup()
                    .withObject(i)
                    .withObject(i % 2)
                    .withObject(i / 2));
            points.add(point);
        }
        return points;
    }
    
    public static Points<GaugeRollup> generateFakeGaugeRollups() {
        Points<GaugeRollup> points = new Points<GaugeRollup>();
        long startTime = 1234567L;
        for (int i = 0; i < 5; i++) {
            long timeNow = startTime + i*1000;
            Points.Point<GaugeRollup> point = new Points.Point<GaugeRollup>(timeNow, new GaugeRollup()
                .withLatest(timeNow, i));
            points.add(point);
        }
        return points;
    }
    
    public static Points<TimerRollup> generateFakeTimerRollups() {
        Points<TimerRollup> points = new Points<TimerRollup>();
        long startTime = 1234567L;
        for (int i = 0; i < 5; i++) {
            long timeNow = startTime + i*1000;
            TimerRollup rollup = new TimerRollup()
                .withAverage(i)
                .withCount(i)
                .withCountPS(i*0.1d)
                .withMaxValue(i)
                .withMinValue(i)
                .withSum(Double.valueOf(i+i))
                .withVariance(i);
            rollup.setPercentile("50", i);
            rollup.setPercentile("99", i * 2 + 1);
            Points.Point<TimerRollup> point = new Points.Point<TimerRollup>(timeNow, rollup);
            points.add(point);
        }
        return points;
    }
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/outputs/serializers/JSONBasicRollupsOutputSerializer.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.serializers;

import com.rackspacecloud.blueflood.exceptions.SerializationException;
import com.rackspacecloud.blueflood.outputs.formats.MetricData;
import com.rackspacecloud.blueflood.outputs.utils.PlotRequestParser;
import com.rackspacecloud.blueflood.types.BasicRollup;
import com.rackspacecloud.blueflood.types.CounterRollup;
import com.rackspacecloud.blueflood.types.GaugeRollup;
import com.rackspacecloud.blueflood.types.Points;
import com.rackspacecloud.blueflood.types.Rollup;
import com.rackspacecloud.blueflood.types.SetRollup;
import com.rackspacecloud.blueflood.types.SimpleNumber;
import com.rackspacecloud.blueflood.types.TimerRollup;
import com.rackspacecloud.blueflood.utils.Util;
import org.json.simple.JSONArray;
import org.json.simple.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.Set;

public class JSONBasicRollupsOutputSerializer implements BasicRollupsOutputSerializer<JSONObject> {
    private static final Logger log = LoggerFactory.getLogger(JSONBasicRollupsOutputSerializer.class);
    
    @Override
    public JSONObject transformRollupData(MetricData metricData, Set<MetricStat> filterStats)
            throws SerializationException {
        final JSONObject globalJSON = new JSONObject();
        final JSONObject metaObject = new JSONObject();
        
        // if no stats were entered, figure out what type we are dealing with and select out default stats. 
        if (metricData.getData().getPoints().size() > 0 && filterStats == PlotRequestParser.DEFAULT_STATS) {
            Class dataClass = metricData.getData().getDataClass();
            if (dataClass.equals(BasicRollup.class))
                filterStats = PlotRequestParser.DEFAULT_BASIC;
            else if (dataClass.equals(GaugeRollup.class))
                filterStats = PlotRequestParser.DEFAULT_GAUGE;
            else if (dataClass.equals(CounterRollup.class))
                filterStats = PlotRequestParser.DEFAULT_COUNTER;
            else if (dataClass.equals(SetRollup.class))
                filterStats = PlotRequestParser.DEFAULT_SET;
            else if (dataClass.equals(TimerRollup.class))
                filterStats = PlotRequestParser.DEFAULT_TIMER;
            // else, I got nothing.
        }

        final JSONArray valuesArray = transformDataToJSONArray(metricData, filterStats);

        metaObject.put("count", valuesArray.size());
        metaObject.put("limit", null);
        metaObject.put("marker", null);
        metaObject.put("next_href", null);
        globalJSON.put("values", valuesArray);
        globalJSON.put("metadata", metaObject);
        globalJSON.put("unit", metricData.getUnit() == null ? Util.UNKNOWN : metricData.getUnit());

        return globalJSON;
    }

    protected JSONArray transformDataToJSONArray(MetricData metricData, Set<MetricStat> filterStats)
            throws SerializationException {
        Points points = metricData.getData();
        final JSONArray data = new JSONArray();
        final Set<Map.Entry<Long, Points.Point>> dataPoints = points.getPoints().entrySet();
        for (Map.Entry<Long, Points.Point> point : dataPoints) {
            data.add(toJSON(point.getKey(), point.getValue(), metricData.getUnit(), filterStats));
        }

        return data;
    }

    private JSONObject toJSON(long timestamp, Points.Point point, String unit, Set<MetricStat> filterStats)
            throws SerializationException {
        final JSONObject  object = new JSONObject();
        object.put("timestamp", timestamp);

        JSONObject filterStatsObject = null;
        long numPoints = 1;
        
        
        
        // todo: adding getCount() to Rollup interface will simplify this block.
        // because of inheritance, GaugeRollup needs to come before BasicRollup. sorry.
        if (point.getData() instanceof GaugeRollup) {
            GaugeRollup rollup = (GaugeRollup)point.getData();
            numPoints += rollup.getCount();
            filterStatsObject = getFilteredStatsForRollup(rollup, filterStats);
        } else if (point.getData() instanceof BasicRollup) {
            numPoints = ((BasicRollup) point.getData()).getCount();
            filterStatsObject = getFilteredStatsForRollup((BasicRollup) point.getData(), filterStats);
        } else if (point.getData() instanceof SimpleNumber) {
            numPoints = 1;
            filterStatsObject = getFilteredStatsForFullRes(point.getData(), filterStats);
        } else if (point.getData() instanceof String) {
            numPoints = 1;
            filterStatsObject = getFilteredStatsForString((String) point.getData());
        } else if (point.getData() instanceof Boolean) {
            numPoints = 1;
            filterStatsObject = getFilteredStatsForBoolean((Boolean) point.getData());
        } else if (point.getData() instanceof SetRollup) {
            SetRollup rollup = (SetRollup)point.getData();
            numPoints += rollup.getCount();
            filterStatsObject = getFilteredStatsForRollup(rollup, filterStats);
        } else if (point.getData() instanceof TimerRollup) {
            TimerRollup rollup = (TimerRollup)point.getData();
            numPoints += rollup.getCount();
            filterStatsObject = getFilteredStatsForRollup(rollup, filterStats);
        } else if (point.getData() instanceof CounterRollup) {
            CounterRollup rollup = (CounterRollup)point.getData();
            numPoints += rollup.getCount().longValue();
            filterStatsObject = getFilteredStatsForRollup(rollup, filterStats);
        } else {
            String errString =
              String.format("Unsupported datatype for Point %s",
                point.getData().getClass());
            log.error(errString);
            throw new SerializationException(errString);
        }

        // Set all filtered stats to null if numPoints is 0
        if (numPoints == 0) {
            final Set<Map.Entry<String, Object>> statsSet = filterStatsObject.entrySet();

            for (Map.Entry<String, Object> stat : statsSet) {
                if (!stat.getKey().equals("numPoints")) {
                    stat.setValue(null);
                }
            }
        }

        // Add filtered stats to main object
        final Set<Map.Entry<String, Object>> statsSet = filterStatsObject.entrySet();
        for (Map.Entry<String, Object> stat : statsSet) {
            object.put(stat.getKey(), stat.getValue());
        }

        return object;
    }

    private JSONObject getFilteredStatsForRollup(Rollup rollup, Set<MetricStat> filterStats) {
        final JSONObject filteredObject = new JSONObject();
        for (MetricStat stat : filterStats) {
            try {
                Object filteredValue = stat.convertRollupToObject(rollup);
                if (filteredValue instanceof Map && stat == MetricStat.PERCENTILE) {
                    for (Map.Entry entry : ((Map<?,?>)filteredValue).entrySet()) {
                        TimerRollup.Percentile pct = (TimerRollup.Percentile)entry.getValue();
                        filteredObject.put(String.format("pct_%s", entry.getKey().toString()), pct.getMean());
                    }
                } else {
                    filteredObject.put(stat.toString(), filteredValue);
                }
            } catch (Exception ex) {
                log.warn(ex.getMessage(), ex);
            }
        }
        return filteredObject;
    }
    
    private JSONObject getFilteredStatsForFullRes(Object rawSample, Set<MetricStat> filterStats) {
        final JSONObject filteredObject = new JSONObject();
        if (rawSample instanceof String || rawSample instanceof Boolean) {
            filteredObject.put("value", rawSample);
        } else {
            for (MetricStat stat : filterStats) {
                filteredObject.put(stat.toString(), stat.convertRawSampleToObject(((SimpleNumber) rawSample).getValue()));
            }
        }
        return filteredObject;
    }

    private JSONObject getFilteredStatsForString(String value) {
        final JSONObject filteredObject = new JSONObject();
        filteredObject.put("value", value);

        return filteredObject;
    }

    private JSONObject getFilteredStatsForBoolean(Boolean value) {
        final JSONObject filteredObject = new JSONObject();
        filteredObject.put("value", value);

        return filteredObject;
    }
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/outputs/serializers/JSONHistogramOutputSerializer.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.serializers;


import com.bigml.histogram.Bin;
import com.bigml.histogram.SimpleTarget;
import com.rackspacecloud.blueflood.exceptions.SerializationException;
import com.rackspacecloud.blueflood.outputs.formats.MetricData;
import com.rackspacecloud.blueflood.types.HistogramRollup;
import com.rackspacecloud.blueflood.types.Points;
import org.json.simple.JSONArray;
import org.json.simple.JSONObject;

import java.util.Map;
import java.util.Set;

public class JSONHistogramOutputSerializer {

    public JSONObject transformHistogram(MetricData data) throws SerializationException {
        final JSONObject globalJSON = new JSONObject();
        final JSONObject metaObject = new JSONObject();

        final JSONArray valuesArray = transformDataToJSONArray(data);

        metaObject.put("count", valuesArray.size());
        metaObject.put("limit", null);
        metaObject.put("marker", null);
        metaObject.put("next_href", null);
        globalJSON.put("values", valuesArray);
        globalJSON.put("metadata", metaObject);

        return globalJSON;
    }

    private JSONArray transformDataToJSONArray(MetricData metricData) throws SerializationException {
        Points points = metricData.getData();
        final JSONArray data = new JSONArray();
        final Set<Map.Entry<Long, Points.Point>> dataPoints = points.getPoints().entrySet();
        for (Map.Entry<Long, Points.Point> point : dataPoints) {
            data.add(toJSON(point.getKey(), point.getValue(), metricData.getUnit()));
        }

        return data;
    }

    private JSONObject toJSON(long timestamp, Points.Point point, String unit) throws SerializationException {
        final JSONObject object = new JSONObject();
        object.put("timestamp", timestamp);

        if (!(point.getData() instanceof HistogramRollup)) {
            throw new SerializationException("Unsupported type. HistogramRollup expected.");
        }

        HistogramRollup histogramRollup = (HistogramRollup) point.getData();

        final JSONArray hist = new JSONArray();
        for (Bin<SimpleTarget> bin : histogramRollup.getBins()) {
            final JSONObject obj = new JSONObject();
            obj.put("mean", bin.getMean());
            obj.put("count", bin.getCount());
            hist.add(obj);
        }
        object.put("histogram", hist);

        return object;
    }
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/outputs/utils/PlotRequestParser.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.utils;

import com.rackspacecloud.blueflood.exceptions.InvalidRequestException;
import com.rackspacecloud.blueflood.outputs.serializers.BasicRollupsOutputSerializer;
import com.rackspacecloud.blueflood.types.Resolution;

import java.util.*;

public class PlotRequestParser {
    public static final Set<BasicRollupsOutputSerializer.MetricStat> DEFAULT_STATS = new HashSet<BasicRollupsOutputSerializer.MetricStat>();
    public static final Set<BasicRollupsOutputSerializer.MetricStat> DEFAULT_BASIC;
    public static final Set<BasicRollupsOutputSerializer.MetricStat> DEFAULT_COUNTER;
    public static final Set<BasicRollupsOutputSerializer.MetricStat> DEFAULT_GAUGE;
    public static final Set<BasicRollupsOutputSerializer.MetricStat> DEFAULT_SET;
    public static final Set<BasicRollupsOutputSerializer.MetricStat> DEFAULT_TIMER;
    
    static {
        // EnumSet is so crappy for making me do this instead of using an anonymous subclass.
        DEFAULT_BASIC = EnumSet.noneOf(BasicRollupsOutputSerializer.MetricStat.class);
        DEFAULT_COUNTER = EnumSet.noneOf(BasicRollupsOutputSerializer.MetricStat.class);
        DEFAULT_GAUGE = EnumSet.noneOf(BasicRollupsOutputSerializer.MetricStat.class);
        DEFAULT_SET = EnumSet.noneOf(BasicRollupsOutputSerializer.MetricStat.class);
        DEFAULT_TIMER = EnumSet.noneOf(BasicRollupsOutputSerializer.MetricStat.class);
        
        DEFAULT_BASIC.add(BasicRollupsOutputSerializer.MetricStat.AVERAGE);
        DEFAULT_BASIC.add(BasicRollupsOutputSerializer.MetricStat.NUM_POINTS);
        
        DEFAULT_COUNTER.add(BasicRollupsOutputSerializer.MetricStat.NUM_POINTS);
        DEFAULT_COUNTER.add(BasicRollupsOutputSerializer.MetricStat.SUM);

        DEFAULT_GAUGE.add(BasicRollupsOutputSerializer.MetricStat.NUM_POINTS);
        DEFAULT_GAUGE.add(BasicRollupsOutputSerializer.MetricStat.LATEST);
        
        DEFAULT_SET.add(BasicRollupsOutputSerializer.MetricStat.NUM_POINTS);
        
        DEFAULT_TIMER.add(BasicRollupsOutputSerializer.MetricStat.RATE);
        DEFAULT_TIMER.add(BasicRollupsOutputSerializer.MetricStat.NUM_POINTS);
        DEFAULT_TIMER.add(BasicRollupsOutputSerializer.MetricStat.AVERAGE);
        
        DEFAULT_STATS.add(BasicRollupsOutputSerializer.MetricStat.AVERAGE);
        DEFAULT_STATS.add(BasicRollupsOutputSerializer.MetricStat.NUM_POINTS);
    } 

    public static RollupsQueryParams parseParams(Map<String, List<String>> params) throws InvalidRequestException {
        if (params == null || params.isEmpty()) {
            throw new InvalidRequestException("No query parameters present.");
        }

        List<String> points = params.get("points");
        List<String> res = params.get("resolution");
        List<String> from = params.get("from");
        List<String> to = params.get("to");
        List<String> select = params.get("select");

        if (points == null && res == null) {
            throw new InvalidRequestException("Either 'points' or 'resolution' is required.");
        }

        if (points != null && points.size() != 1) {
            throw new InvalidRequestException("Invalid parameter: points=" + points);
        } else if (res != null && res.size() != 1) {
            throw new InvalidRequestException("Invalid parameter: resolution=" + res);
        } else if (from == null || from.size() != 1) {
            throw new InvalidRequestException("Invalid parameter: from=" + from);
        } else if (to == null || to.size() != 1) {
            throw new InvalidRequestException("Invalid parameter: to="+ to);
        }

        long fromTime = Long.parseLong(from.get(0));
        long toTime = Long.parseLong(to.get(0));

        if (toTime <= fromTime) {
            throw new InvalidRequestException("paramter 'to' must be greater than 'from'");
        }

        Set<BasicRollupsOutputSerializer.MetricStat> stats = getStatsToFilter(select);

        if (points != null) {
            try {
                return new RollupsQueryParams(fromTime, toTime, Integer.parseInt(points.get(0)), stats);
            } catch (NumberFormatException ex) {
                throw new InvalidRequestException("'points' param must be a valid integer");
            }
        } else {
            return new RollupsQueryParams(fromTime, toTime, Resolution.fromString(res.get(0)), stats);
        }
    }

    public static Set<BasicRollupsOutputSerializer.MetricStat> getStatsToFilter(List<String> select) {
        if (select == null || select.isEmpty()) {
            return DEFAULT_STATS;
        } else {
            Set<BasicRollupsOutputSerializer.MetricStat> filters = new HashSet<BasicRollupsOutputSerializer.MetricStat>();
            // handle case when someone does select=average,min instead of select=average&select=min
            for (String stat : select) {
                if (stat.contains(",")) {
                    List<String> nestedStats = Arrays.asList(stat.split(","));
                    filters.addAll(BasicRollupsOutputSerializer.MetricStat.fromStringList(nestedStats));
                } else {
                    BasicRollupsOutputSerializer.MetricStat possibleStat = BasicRollupsOutputSerializer.MetricStat.fromString(stat);
                    if (possibleStat != null)
                        filters.add(possibleStat);
                }
            }
            return filters;
        }
    }
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/outputs/utils/RollupsQueryParams.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.utils;

import com.rackspacecloud.blueflood.outputs.serializers.BasicRollupsOutputSerializer;
import com.rackspacecloud.blueflood.rollup.Granularity;
import com.rackspacecloud.blueflood.types.Range;
import com.rackspacecloud.blueflood.types.Resolution;

import java.util.Set;

public class RollupsQueryParams {
    private int points;
    private Resolution resolution;
    private final Range range;
    private final Set<BasicRollupsOutputSerializer.MetricStat> stats;
    private boolean isPoints = false;

    private RollupsQueryParams(long from, long to, Set<BasicRollupsOutputSerializer.MetricStat> stats) {
        if (from >= to) {
            throw new IllegalArgumentException("'from' timestamp has to be strictly less than 'to'.");
        }
        this.stats = stats;
        this.range = new Range(from, to);
        this.points = 0;
        this.resolution = Resolution.FULL;
    }

    public RollupsQueryParams(long from, long to, int points, Set<BasicRollupsOutputSerializer.MetricStat> stats) {
        this(from, to, stats);
        this.isPoints = true;
        this.points = points;
    }

    public RollupsQueryParams(long from, long to, Resolution resolution, Set<BasicRollupsOutputSerializer.MetricStat> stats) {
        this(from, to, stats);
        this.resolution = resolution;
        this.isPoints = false;
    }

    public boolean isGetByPoints() {
        return isPoints;
    }

    public boolean isGetByResolution() {
        return !isPoints;
    }

    public Granularity getGranularity(String tenantId) {
        if (isPoints) {
            return Granularity.granularityFromPointsInInterval(tenantId, range.getStart(), range.getStop(), points);
        } else {
            return Granularity.granularities()[resolution.getValue()];
        }
    }

    public Range getRange() {
        return range;
    }

    public int getPoints() {
        return points;
    }

    public Resolution getResolution() {
        return resolution;
    }

    public Set<BasicRollupsOutputSerializer.MetricStat> getStats() {
        return stats;
    }
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/service/HttpConfig.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

/**
 * Default config values for blueflood-http. Also to be used for getting config key names.
 */
public enum HttpConfig implements ConfigDefaults {
    // blueflood can receive metric over HTTP
    HTTP_INGESTION_PORT("19000"),

    // interface to which the ingestion server will bind
    HTTP_INGESTION_HOST("localhost"),

    // blueflood can output metrics over HTTP
    HTTP_METRIC_DATA_QUERY_PORT("20000"),

    // interface to which the query server will bind
    HTTP_QUERY_HOST("localhost"),

    // Maximum number of metrics allowed to be fetched per batch query
    MAX_METRICS_PER_BATCH_QUERY("100"),

    // Maximum number of ACCEPT threads for HTTP output
    MAX_READ_ACCEPT_THREADS("10"),

    /*
      Maximum number of WORKER threads for HTTP output (is included in connections calculations)
      CoreConfig.ES_UNIT_THREADS should also be adjusted corresponding to the changes in this config
      if CoreConfig,.USE_ES_FOR_UNITS is set to true, so that the ES_UNIT threads do not become a
      bottleneck for the netty threads
     */
    MAX_READ_WORKER_THREADS("50"),

    // Maximum number of ACCEPT threads for HTTP input server
    MAX_WRITE_ACCEPT_THREADS("10"),

    // Maximum number of WORKER threads for HTTP output (must be included in connections calculations)
    MAX_WRITE_WORKER_THREADS("50"),

    // Maximum number of batch requests that can be queued
    MAX_BATCH_READ_REQUESTS_TO_QUEUE("10"),

    // Maximum number of threads in type and unit processor threadpool
    HTTP_MAX_TYPE_UNIT_PROCESSOR_THREADS("10");

    static {
        Configuration.getInstance().loadDefaults(HttpConfig.values());
    }
    private String defaultValue;
    private HttpConfig(String value) {
        this.defaultValue = value;
    }
    public String getDefaultValue() {
        return defaultValue;
    }
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/service/HttpIngestionService.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.rackspacecloud.blueflood.inputs.handlers.HttpMetricsIngestionServer;
import com.rackspacecloud.blueflood.io.IMetricsWriter;

/**
 * HTTP Ingestion Service.
 */
public class HttpIngestionService implements IngestionService {
    private HttpMetricsIngestionServer server;
    public void startService(ScheduleContext context, IMetricsWriter writer) {
        server = new HttpMetricsIngestionServer(context, writer);
    }
}


File: blueflood-http/src/main/java/com/rackspacecloud/blueflood/service/HttpQueryService.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import com.google.common.annotations.VisibleForTesting;
import com.rackspacecloud.blueflood.outputs.handlers.HttpMetricDataQueryServer;

import java.io.IOException;

/**
 * HTTP Query Service.
 */
public class HttpQueryService implements QueryService {
    private HttpMetricDataQueryServer server;
    public void startService() {
        server = new HttpMetricDataQueryServer();
    }

    @VisibleForTesting
    public void stopService() { server.stopServer();}
}


File: blueflood-http/src/test/java/com/rackspacecloud/blueflood/http/HttpRequestWithDecodedQueryParamsTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.http;

import org.jboss.netty.handler.codec.http.DefaultHttpRequest;
import org.jboss.netty.handler.codec.http.HttpMethod;
import org.jboss.netty.handler.codec.http.HttpVersion;
import org.junit.Assert;
import org.junit.Test;

import java.util.List;
import java.util.Map;

public class HttpRequestWithDecodedQueryParamsTest {

    @Test
    public void testQueryParamsDecode() {
        final DefaultHttpRequest defaultRequest = new DefaultHttpRequest(HttpVersion.HTTP_1_1, HttpMethod.GET,
                "http://localhost/v1.0/ac98760XYZ/experimental/metric_views/metXYZ?from=12345&to=56789&points=100"
                + "&foo=x,y,z&foo=p");
        final HTTPRequestWithDecodedQueryParams requestWithParams =
                HTTPRequestWithDecodedQueryParams.createHttpRequestWithDecodedQueryParams(defaultRequest);

        Map<String, List<String>> queryParams = requestWithParams.getQueryParams();
        Assert.assertEquals(4, queryParams.size());
        final String fromParam = queryParams.get("from").get(0);
        final String toParam = queryParams.get("to").get(0);
        final String pointsParam = queryParams.get("points").get(0);
        List<String> fooParams = queryParams.get("foo");

        Assert.assertEquals(12345, Integer.parseInt(fromParam));
        Assert.assertEquals(56789, Integer.parseInt(toParam));
        Assert.assertEquals(100, Integer.parseInt(pointsParam));
        Assert.assertEquals(2, fooParams.size());

        for (String fooParam : fooParams) {
            Assert.assertTrue(fooParam.equals("x,y,z") || fooParam.equals("p"));
        }
    }
}


File: blueflood-http/src/test/java/com/rackspacecloud/blueflood/http/RouteMatcherTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.http;

import org.jboss.netty.channel.Channel;
import org.jboss.netty.channel.ChannelFuture;
import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.channel.MessageEvent;
import org.jboss.netty.handler.codec.http.DefaultHttpRequest;
import org.jboss.netty.handler.codec.http.HttpMethod;
import org.jboss.netty.handler.codec.http.HttpRequest;
import org.jboss.netty.handler.codec.http.HttpVersion;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;

import java.net.SocketAddress;

public class RouteMatcherTest {
    private RouteMatcher routeMatcher;
    private boolean testRouteHandlerCalled = false;

    @Before
    public void setup() {
        testRouteHandlerCalled = false;
        routeMatcher = new RouteMatcher().withNoRouteHandler(new TestRouteHandler());
    }

    @Test
    public void testNoRouteHandler() throws Exception {
        final HttpRequestHandler dummyHandler = new HttpRequestHandler() {
            @Override
            public void handle(ChannelHandlerContext ctx, HttpRequest request) {
                // pass
            }
        };

        routeMatcher.get("/", dummyHandler);
        routeMatcher.get("/blah", dummyHandler);

        routeMatcher.route(null, new DefaultHttpRequest(HttpVersion.HTTP_1_1, HttpMethod.GET, "/chat"));
        Assert.assertTrue(testRouteHandlerCalled);
    }

    @Test
    public void testValidRouteHandler() throws Exception {
        RouteMatcher router = new RouteMatcher();
        router.get("/", new TestRouteHandler());
        router.route(null, new DefaultHttpRequest(HttpVersion.HTTP_1_1, HttpMethod.GET, "/"));
        Assert.assertTrue(testRouteHandlerCalled);
    }

    @Test
    public void testValidRoutePatterns() throws Exception {
        HttpRequest modifiedReq = testPattern("/metrics/:metricId", "/metrics/foo");
        Assert.assertTrue(testRouteHandlerCalled);
        Assert.assertEquals(1, modifiedReq.getHeaders().size());
        Assert.assertEquals("metricId", modifiedReq.getHeaders().get(0).getKey());
        Assert.assertEquals("foo", modifiedReq.getHeaders().get(0).getValue());
        testRouteHandlerCalled = false;

        modifiedReq = testPattern("/tenants/:tenantId/entities/:entityId", "/tenants/acFoo/entities/enBar");
        Assert.assertTrue(testRouteHandlerCalled);
        Assert.assertEquals(2, modifiedReq.getHeaders().size());
        Assert.assertTrue(modifiedReq.getHeader("tenantId").equals("acFoo"));
        Assert.assertTrue(modifiedReq.getHeader("entityId").equals("enBar"));
        testRouteHandlerCalled = false;

        modifiedReq = testPattern("/tenants/:tenantId/entities/:entityId/checks/:checkId/metrics/:metricId/plot",
                "/tenants/acFoo/entities/enBar/checks/chFoo/metrics/myMetric/plot");
        Assert.assertTrue(testRouteHandlerCalled);
        Assert.assertEquals(4, modifiedReq.getHeaders().size());
        Assert.assertTrue(modifiedReq.getHeader("tenantId").equals("acFoo"));
        Assert.assertTrue(modifiedReq.getHeader("entityId").equals("enBar"));
        Assert.assertTrue(modifiedReq.getHeader("entityId").equals("enBar"));
        Assert.assertTrue(modifiedReq.getHeader("checkId").equals("chFoo"));
        Assert.assertTrue(modifiedReq.getHeader("metricId").equals("myMetric"));
        testRouteHandlerCalled = false;

        modifiedReq = testPattern("/software/:name/:version", "/software/blueflood/v0.1");
        Assert.assertTrue(testRouteHandlerCalled);
        Assert.assertEquals(2, modifiedReq.getHeaders().size());
        Assert.assertTrue(modifiedReq.getHeader("name").equals("blueflood"));
        Assert.assertTrue(modifiedReq.getHeader("version").equals("v0.1"));
        testRouteHandlerCalled = false;

        // trailing slash
        modifiedReq = testPattern("/software/:name/:version/", "/software/blueflood/v0.1/");
        Assert.assertTrue(testRouteHandlerCalled);
        Assert.assertEquals(2, modifiedReq.getHeaders().size());
        Assert.assertTrue(modifiedReq.getHeader("name").equals("blueflood"));
        Assert.assertTrue(modifiedReq.getHeader("version").equals("v0.1"));
        testRouteHandlerCalled = false;

        modifiedReq = testPattern("/:name/:version","/blueflood/v0.1");
        Assert.assertTrue(testRouteHandlerCalled);
        Assert.assertEquals(2, modifiedReq.getHeaders().size());
        Assert.assertTrue(modifiedReq.getHeader("name").equals("blueflood"));
        Assert.assertTrue(modifiedReq.getHeader("version").equals("v0.1"));
        testRouteHandlerCalled = false;
    }

    private HttpRequest testPattern(String pattern, String URI) throws Exception {
        RouteMatcher router = new RouteMatcher();
        final TestRouteHandler handler = new TestRouteHandler();
        // Register handler for pattern
        router.get(pattern, handler);
        // See if handler is called when URI matching pattern is received
        router.route(null, new DefaultHttpRequest(HttpVersion.HTTP_1_1, HttpMethod.GET, URI));

        // Return modified request (headers might be updated with paramsPositionMap from URI)
        return handler.getRequest();
    }

    private class TestRouteHandler implements HttpRequestHandler {
        private HttpRequest request = null;

        @Override
        public void handle(ChannelHandlerContext ctx, HttpRequest req) {
            request = req;
            testRouteHandlerCalled = true;
        }

        public HttpRequest getRequest() {
            return request;
        }
    }

    private class TestMessageEvent implements MessageEvent {
        Object message;

        public TestMessageEvent(HttpRequest fakeRequest) {
            this.message = fakeRequest;
        }

        @Override
        public Object getMessage() {
            return this.message;
        }

        @Override
        public SocketAddress getRemoteAddress() {
            return null;  //To change body of implemented methods use File | Settings | File Templates.
        }

        @Override
        public Channel getChannel() {
            return null;  //To change body of implemented methods use File | Settings | File Templates.
        }

        @Override
        public ChannelFuture getFuture() {
            return null;  //To change body of implemented methods use File | Settings | File Templates.
        }
    }
}

File: blueflood-http/src/test/java/com/rackspacecloud/blueflood/inputs/formats/JSONMetricsContainerTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.inputs.formats;

import com.rackspacecloud.blueflood.types.Metric;
import org.codehaus.jackson.map.ObjectMapper;
import org.codehaus.jackson.map.type.TypeFactory;
import org.junit.Assert;
import org.junit.Test;

import java.io.StringWriter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public class JSONMetricsContainerTest {
    private static final ObjectMapper mapper = new ObjectMapper();
    private static final StringWriter writer = new StringWriter();
    private final TypeFactory typeFactory = TypeFactory.defaultInstance();

    @Test
    public void testJSONMetricsContainerConstruction() throws Exception {
        // This part tests Jackson JSON mapper
        List<JSONMetricsContainer.JSONMetric> jsonMetrics =
                mapper.readValue(
                        generateJSONMetricsData(),
                        typeFactory.constructCollectionType(List.class,
                                JSONMetricsContainer.JSONMetric.class)
                );
        // Construct the JSONMetricsContainter from JSON metric objects
        JSONMetricsContainer jsonMetricsContainer = new JSONMetricsContainer("ac1", jsonMetrics);

        List<Metric> metricsCollection = jsonMetricsContainer.toMetrics();

        Assert.assertTrue(metricsCollection.size() == 2);
        Assert.assertEquals("ac1.mzord.duration", metricsCollection.get(0).getLocator().toString());
        Assert.assertEquals(Long.MAX_VALUE, metricsCollection.get(0).getMetricValue());
        Assert.assertEquals(1234566, metricsCollection.get(0).getTtlInSeconds());
        Assert.assertEquals(1234567890L, metricsCollection.get(0).getCollectionTime());
        Assert.assertEquals("milliseconds", metricsCollection.get(0).getUnit());
        Assert.assertEquals("N", metricsCollection.get(0).getDataType().toString());

        Assert.assertEquals("ac1.mzord.status", metricsCollection.get(1).getLocator().toString());
        Assert.assertEquals("Website is up", metricsCollection.get(1).getMetricValue());
        Assert.assertEquals("unknown", metricsCollection.get(1).getUnit());
        Assert.assertEquals("S", metricsCollection.get(1).getDataType().toString());
    }

    @Test
    public void testBigIntHandling() {
        String jsonBody = "[{\"collectionTime\":1401302372775,\"ttlInSeconds\":172800,\"metricValue\":18446744073709000000,\"metricName\":\"used\",\"unit\":\"unknown\"}]";

        JSONMetricsContainer container = null;
        try {
            List<JSONMetricsContainer.JSONMetric> jsonMetrics =
                mapper.readValue(
                        jsonBody,
                        typeFactory.constructCollectionType(List.class,
                                JSONMetricsContainer.JSONMetric.class)
                );
            container = new JSONMetricsContainer("786659", jsonMetrics);
        } catch (Exception e) {
            Assert.fail("Jackson failed to parse a big int");
        }

        try {
            List<Metric> metrics = container.toMetrics();
        } catch (Exception ex) {
            Assert.fail();
        }
    }

    public static List<Map<String, Object>> generateMetricsData() throws Exception {
        List<Map<String, Object>> metricsList = new ArrayList<Map<String, Object>>();

        // Long metric value
        Map<String, Object> testMetric = new TreeMap<String, Object>();
        testMetric.put("metricName", "mzord.duration");
        testMetric.put("ttlInSeconds", 1234566);
        testMetric.put("unit", "milliseconds");
        testMetric.put("metricValue", Long.MAX_VALUE);
        testMetric.put("collectionTime", 1234567890L);
        metricsList.add(testMetric);

        // String metric value
        testMetric = new TreeMap<String, Object>();
        testMetric.put("metricName", "mzord.status");
        testMetric.put("ttlInSeconds", 1234566);
        testMetric.put("unit", "unknown");
        testMetric.put("metricValue", "Website is up");
        testMetric.put("collectionTime", 1234567890L);
        metricsList.add(testMetric);

        // null metric value. This shouldn't be in the final list of metrics because we ignore null valued metrics.
        testMetric = new TreeMap<String, Object>();
        testMetric.put("metricName", "mzord.hipster");
        testMetric.put("ttlInSeconds", 1234566);
        testMetric.put("unit", "unknown");
        testMetric.put("metricValue", null);
        testMetric.put("collectionTime", 1234567890L);
        metricsList.add(testMetric);
        return metricsList;
    }

    public static String generateJSONMetricsData() throws Exception {
        mapper.writeValue(writer, generateMetricsData());
        final String jsonString = writer.toString();

        return jsonString;
    }

    public static String generateMultitenantJSONMetricsData() throws Exception {
        List<Map<String, Object>> dataOut = new ArrayList<Map<String, Object>>();
        for (Map<String, Object> stringObjectMap : generateMetricsData()) {
            stringObjectMap.put("tenantId", "tenantOne");
            dataOut.add(stringObjectMap);
        }
        for (Map<String, Object> stringObjectMap : generateMetricsData()) {
            stringObjectMap.put("tenantId", "tenantTwo");
            dataOut.add(stringObjectMap);
        }

        return mapper.writeValueAsString(dataOut);
    }
}


File: blueflood-http/src/test/java/com/rackspacecloud/blueflood/outputs/serializers/BatchedMetricsJSONOutputSerializerTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.serializers;

import com.rackspacecloud.blueflood.outputs.formats.MetricData;
import com.rackspacecloud.blueflood.types.Locator;
import org.json.simple.JSONArray;
import org.json.simple.JSONObject;
import org.junit.Assert;
import org.junit.Test;

import java.util.*;

public class BatchedMetricsJSONOutputSerializerTest {
    private final Set<BasicRollupsOutputSerializer.MetricStat> filterStats;
    private static final String tenantId = "879890";

    public BatchedMetricsJSONOutputSerializerTest() {
        filterStats = new HashSet<BasicRollupsOutputSerializer.MetricStat>();
        filterStats.add(BasicRollupsOutputSerializer.MetricStat.AVERAGE);
        filterStats.add(BasicRollupsOutputSerializer.MetricStat.MIN);
        filterStats.add(BasicRollupsOutputSerializer.MetricStat.MAX);
        filterStats.add(BasicRollupsOutputSerializer.MetricStat.NUM_POINTS);
    }

    @Test
    public void testBatchedMetricsSerialization() throws Exception {
        final BatchedMetricsJSONOutputSerializer serializer = new BatchedMetricsJSONOutputSerializer();

        final Map<Locator, MetricData> metrics = new HashMap<Locator, MetricData>();
        for (int i = 0; i < 2; i++) {
            final MetricData metricData = new MetricData(FakeMetricDataGenerator.generateFakeRollupPoints(), "unknown",
                    MetricData.Type.NUMBER);

            metrics.put(Locator.createLocatorFromPathComponents(tenantId, String.valueOf(i)), metricData);
        }

        JSONObject jsonMetrics = serializer.transformRollupData(metrics, filterStats);

        Assert.assertTrue(jsonMetrics.get("metrics") != null);
        JSONArray jsonMetricsArray = (JSONArray) jsonMetrics.get("metrics");

        Iterator<JSONObject> metricsObjects = jsonMetricsArray.iterator();
        Assert.assertTrue(metricsObjects.hasNext());

        while (metricsObjects.hasNext()) {
            JSONObject singleMetricObject = metricsObjects.next();
            Assert.assertTrue(singleMetricObject.get("unit").equals("unknown"));
            Assert.assertTrue(singleMetricObject.get("type").equals("number"));
            JSONArray data = (JSONArray) singleMetricObject.get("data");
            Assert.assertTrue(data != null);
        }
    }
}


File: blueflood-http/src/test/java/com/rackspacecloud/blueflood/outputs/serializers/JSONBasicRollupOutputSerializerTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.serializers;

import com.google.common.collect.Collections2;
import com.google.common.collect.Sets;
import com.rackspacecloud.blueflood.outputs.formats.MetricData;
import com.rackspacecloud.blueflood.outputs.serializers.BasicRollupsOutputSerializer.MetricStat;
import com.rackspacecloud.blueflood.outputs.utils.PlotRequestParser;
import com.rackspacecloud.blueflood.types.BasicRollup;
import com.rackspacecloud.blueflood.types.CounterRollup;
import com.rackspacecloud.blueflood.types.Points;
import com.rackspacecloud.blueflood.exceptions.SerializationException;
import com.rackspacecloud.blueflood.types.SimpleNumber;
import org.json.simple.JSONArray;
import org.json.simple.JSONObject;
import org.junit.Assert;
import org.junit.Test;

import java.util.HashSet;
import java.util.Set;

public class JSONBasicRollupOutputSerializerTest {
    private final Set<MetricStat> filterStats;

    public JSONBasicRollupOutputSerializerTest() {
        filterStats = new HashSet<MetricStat>();
        filterStats.add(MetricStat.AVERAGE);
        filterStats.add(MetricStat.MIN);
        filterStats.add(MetricStat.MAX);
    }

    @Test
    public void testTransformRollupDataAtFullRes() throws Exception {
        final JSONBasicRollupsOutputSerializer serializer = new JSONBasicRollupsOutputSerializer();
        final MetricData metricData = new MetricData(FakeMetricDataGenerator.generateFakeFullResPoints(), "unknown",
                MetricData.Type.NUMBER);

        JSONObject metricDataJSON = serializer.transformRollupData(metricData, filterStats);

        final JSONArray data = (JSONArray) metricDataJSON.get("values");

        // Assert that we have some data to test
        Assert.assertTrue(data.size() > 0);

        for (int i = 0; i < data.size(); i++) {
            final JSONObject dataJSON = (JSONObject) data.get(i);
            final Points.Point<SimpleNumber> point = (Points.Point<SimpleNumber>) metricData.getData().getPoints().get(dataJSON.get("timestamp"));

            Assert.assertEquals(point.getData().getValue(), dataJSON.get("average"));
            Assert.assertEquals(point.getData().getValue(), dataJSON.get("min"));
            Assert.assertEquals(point.getData().getValue(), dataJSON.get("max"));

            // Assert that variance isn't present
            Assert.assertNull(dataJSON.get("variance"));

            // Assert numPoints isn't present
            Assert.assertNull(dataJSON.get("numPoints"));
        }
    }


    @Test
    public void testTransformRollupDataForCoarserGran() throws Exception {
        final JSONBasicRollupsOutputSerializer serializer = new JSONBasicRollupsOutputSerializer();
        final MetricData metricData = new MetricData(FakeMetricDataGenerator.generateFakeRollupPoints(), "unknown",
                MetricData.Type.NUMBER);
        Set<MetricStat> filters = new HashSet<MetricStat>();
        filters.add(MetricStat.AVERAGE);
        filters.add(MetricStat.MIN);
        filters.add(MetricStat.MAX);
        filters.add(MetricStat.NUM_POINTS);

        JSONObject metricDataJSON = serializer.transformRollupData(metricData, filters);
        final JSONArray data = (JSONArray) metricDataJSON.get("values");

        // Assert that we have some data to test
        Assert.assertTrue(data.size() > 0);

        for (int i = 0; i < data.size(); i++) {
            final JSONObject dataJSON = (JSONObject) data.get(i);
            final Points.Point point = (Points.Point) metricData.getData().getPoints().get(dataJSON.get("timestamp"));

            long numPoints = ((BasicRollup) point.getData()).getCount();
            Assert.assertEquals(numPoints, dataJSON.get("numPoints"));

            if (numPoints == 0) {
                Assert.assertNull(dataJSON.get("average"));
                Assert.assertNull(dataJSON.get("min"));
                Assert.assertNull(dataJSON.get("max"));
            } else {
                Assert.assertEquals(((BasicRollup) point.getData()).getAverage(), dataJSON.get("average"));
                Assert.assertEquals(((BasicRollup) point.getData()).getMaxValue(), dataJSON.get("max"));
                Assert.assertEquals(((BasicRollup) point.getData()).getMinValue(), dataJSON.get("min"));
            }

            // Assert that variance isn't present
            Assert.assertNull(dataJSON.get("variance"));
        }
    }

    @Test
    public void testTransformRollupDataString() throws SerializationException{
        final JSONBasicRollupsOutputSerializer serializer = new JSONBasicRollupsOutputSerializer();
        final MetricData metricData = new MetricData(FakeMetricDataGenerator.generateFakeStringPoints(), "unknown",
                MetricData.Type.STRING);

        JSONObject metricDataJSON = serializer.transformRollupData(metricData, filterStats);

        final JSONArray data = (JSONArray) metricDataJSON.get("values");

        // Assert that we have some data to test
        Assert.assertTrue(data.size() > 0);

        for (int i = 0; i < data.size(); i++ ) {
            final JSONObject dataJSON = (JSONObject) data.get(i);
            final Points.Point point = (Points.Point) metricData.getData().getPoints().get(dataJSON.get("timestamp"));

            Assert.assertEquals(point.getData(), dataJSON.get("value"));

            Assert.assertNull(dataJSON.get("average"));
            Assert.assertNull(dataJSON.get("min"));
            Assert.assertNull(dataJSON.get("max"));
            Assert.assertNull(dataJSON.get("variance"));
        }
    }
    
    @Test
    public void testCounters() throws Exception {
        final JSONBasicRollupsOutputSerializer serializer = new JSONBasicRollupsOutputSerializer();
        final MetricData metricData = new MetricData(
                FakeMetricDataGenerator.generateFakeCounterRollupPoints(), 
                "unknown", 
                MetricData.Type.NUMBER);
        JSONObject metricDataJSON = serializer.transformRollupData(metricData, PlotRequestParser.DEFAULT_COUNTER);
        final JSONArray data = (JSONArray)metricDataJSON.get("values");
        
        Assert.assertEquals(5, data.size());
        for (int i = 0; i < data.size(); i++) {
            final JSONObject dataJSON = (JSONObject)data.get(i);
            
            Assert.assertNotNull(dataJSON.get("numPoints"));
            Assert.assertEquals((long) (i + 1000), dataJSON.get("numPoints"));

            Assert.assertNotNull(dataJSON.get("sum"));
            Assert.assertEquals((long) (i + 1000), dataJSON.get("sum"));

            Assert.assertNull(dataJSON.get("rate"));
        }
    }
    
    @Test
    public void testGauges() throws Exception {
        final JSONBasicRollupsOutputSerializer serializer = new JSONBasicRollupsOutputSerializer();
        final MetricData metricData = new MetricData(
                FakeMetricDataGenerator.generateFakeGaugeRollups(),
                "unknown",
                MetricData.Type.NUMBER);
        JSONObject metricDataJSON = serializer.transformRollupData(metricData, PlotRequestParser.DEFAULT_GAUGE);
        final JSONArray data = (JSONArray)metricDataJSON.get("values");
        
        Assert.assertEquals(5, data.size());
        for (int i = 0; i < data.size(); i++) {
            final JSONObject dataJSON = (JSONObject)data.get(i);
            
            Assert.assertNotNull(dataJSON.get("numPoints"));
            Assert.assertEquals(1L, dataJSON.get("numPoints"));
            Assert.assertNotNull("latest");
            Assert.assertEquals(i, dataJSON.get("latest"));
            
            // other fields were filtered out.
            Assert.assertNull(dataJSON.get(MetricStat.AVERAGE.toString()));
            Assert.assertNull(dataJSON.get(MetricStat.VARIANCE.toString()));
            Assert.assertNull(dataJSON.get(MetricStat.MIN.toString()));
            Assert.assertNull(dataJSON.get(MetricStat.MAX.toString()));
        }
    }
    
    @Test
    public void testSets() throws Exception {
        final JSONBasicRollupsOutputSerializer serializer = new JSONBasicRollupsOutputSerializer();
        final MetricData metricData = new MetricData(
                FakeMetricDataGenerator.generateFakeSetRollupPoints(),
                "unknown",
                MetricData.Type.NUMBER);
        JSONObject metricDataJSON = serializer.transformRollupData(metricData, PlotRequestParser.DEFAULT_SET);
        final JSONArray data = (JSONArray)metricDataJSON.get("values");
        
        Assert.assertEquals(5, data.size());
        for (int i = 0; i < data.size(); i++) {
            final JSONObject dataJSON = (JSONObject)data.get(i);
            
            Assert.assertNotNull(dataJSON.get("numPoints"));
            Assert.assertEquals(Sets.newHashSet(i, i % 2, i / 2).size(), dataJSON.get("numPoints"));
        }
    }
    
    @Test
    public void setTimers() throws Exception {
        final JSONBasicRollupsOutputSerializer serializer = new JSONBasicRollupsOutputSerializer();
        final MetricData metricData = new MetricData(
                FakeMetricDataGenerator.generateFakeTimerRollups(),
                "unknown",
                MetricData.Type.NUMBER);
        
        JSONObject metricDataJSON = serializer.transformRollupData(metricData, PlotRequestParser.DEFAULT_TIMER);
        final JSONArray data = (JSONArray)metricDataJSON.get("values");
        
        Assert.assertEquals(5, data.size());
        for (int i = 0; i < data.size(); i++) {
            final JSONObject dataJSON = (JSONObject)data.get(i);
            
            Assert.assertNotNull(dataJSON.get("numPoints"));
            Assert.assertNotNull(dataJSON.get("average"));
            Assert.assertNotNull(dataJSON.get("rate"));
            
            // bah. I'm too lazy to check equals.
        }
    }
    
    
}


File: blueflood-http/src/test/java/com/rackspacecloud/blueflood/outputs/serializers/JSONHistogramOutputSerializerTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.serializers;

import com.rackspacecloud.blueflood.exceptions.SerializationException;
import com.rackspacecloud.blueflood.outputs.formats.MetricData;
import com.rackspacecloud.blueflood.types.Points;
import org.json.simple.JSONArray;
import org.json.simple.JSONObject;
import org.junit.Assert;
import org.junit.Test;

public class JSONHistogramOutputSerializerTest {

    @Test
    public void testHistogramRollupsSerialization() throws SerializationException {
        final JSONHistogramOutputSerializer serializer = new JSONHistogramOutputSerializer();
        final MetricData metricData = new MetricData(FakeMetricDataGenerator.generateFakeHistogramRollupPoints(), "unknown",
                MetricData.Type.HISTOGRAM);

        JSONObject metricDataJSON = serializer.transformHistogram(metricData);

        final JSONArray data = (JSONArray) metricDataJSON.get("values");

        for (int i = 0; i < data.size(); i++ ) {
            final JSONObject dataJSON = (JSONObject) data.get(i);
            final Points.Point point = (Points.Point) metricData.getData().getPoints().get(dataJSON.get("timestamp"));

            JSONArray hist = (JSONArray) dataJSON.get("histogram");
            Assert.assertNotNull(hist);

            for (int j = 0; j < hist.size(); j++) {
                JSONObject bin = (JSONObject) hist.get(j);
                Assert.assertNotNull(bin.get("count"));
                Assert.assertNotNull(bin.get("mean"));
            }
        }
    }
}


File: blueflood-kafka/src/main/java/com/rackspacecloud/blueflood/outputs/handlers/KafkaService.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.handlers;

import com.rackspacecloud.blueflood.concurrent.ThreadPoolBuilder;
import com.rackspacecloud.blueflood.eventemitter.Emitter;
import com.rackspacecloud.blueflood.eventemitter.RollupEvent;
import com.rackspacecloud.blueflood.eventemitter.RollupEventEmitter;
import com.rackspacecloud.blueflood.outputs.handlers.helpers.KafkaProducerWork;
import com.rackspacecloud.blueflood.service.EventListenerService;
import com.rackspacecloud.blueflood.service.KafkaConfig;
import org.slf4j.LoggerFactory;
import org.slf4j.Logger;
import java.util.ArrayList;
import java.util.Random;
import java.util.concurrent.*;
import kafka.javaapi.producer.Producer;
import kafka.producer.ProducerConfig;

public class KafkaService implements Emitter.Listener<RollupEvent>, EventListenerService {
    private static final Logger log = LoggerFactory.getLogger(KafkaService.class);
    private ArrayList<Producer> producerList = new ArrayList<Producer>();
    private ThreadPoolExecutor kafkaExecutors;
    //Switch to tell if ThreadPool and Kafka Producers were instantiated properly
    private boolean ready = false;
    private static final Integer DEFAULT_KAFKA_PRODUCERS = 5;
    private Integer numberOfProducers;
    private final RollupEventEmitter eventEmitter = RollupEventEmitter.getInstance();
    private final String eventName = RollupEventEmitter.ROLLUP_EVENT_NAME;
    private Random rand = new Random();

    private void init() throws Exception {
        try {
            KafkaConfig config = new KafkaConfig();
            if(config.getBooleanProperty("blueflood.enable.kafka.service")) {
                numberOfProducers = config.getIntegerProperty("blueflood.producer.count") != null ? config.getIntegerProperty("blueflood.producer.count") : DEFAULT_KAFKA_PRODUCERS;
                kafkaExecutors = new ThreadPoolBuilder()
                        .withCorePoolSize(numberOfProducers)
                        .withMaxPoolSize(numberOfProducers)
                        .withUnboundedQueue()
                        .build();
                for(int i=0;i<numberOfProducers;i++) {
                    Producer producer = new Producer(new ProducerConfig(config.getKafkaProperties()));
                    producerList.add(producer);
                }
                ready = true;
            }
        } catch (Exception e) {
            //Takes care of case wherein, initialization threw an exception after thread pool was created
            if(kafkaExecutors != null && !kafkaExecutors.isShutdown()) {
              kafkaExecutors.shutdownNow();
            }
            throw e;
        }
    }

    @Override
    public synchronized void startService() {
        if (!ready) {
            try {
                init();
                if (ready) {
                    //Register with the event emitter
                    eventEmitter.on(eventName, this);
                    log.debug("Listening to event: " + eventName);
                }
            } catch (Exception e) {
                log.error("Could not start Kafka Producer due to errors during initialization phase", e);
            }
            return;
        }
        log.debug("Kafka Production already started for the event: " + eventName);
    }

    @Override
    public synchronized void stopService() {
        //Check to see of the kafka production was already stopped
        if (!eventEmitter.listeners(eventName).contains(this)) {
            log.debug("Kafka Production is already shutdown");
            return;
        }
        //Check if there is some pending work and try to wait for it to complete
        if (!kafkaExecutors.isTerminating() || !kafkaExecutors.isShutdown()) {
            log.debug("Shutting down after terminating all work");
            //Stop the executors
            kafkaExecutors.shutdown();
            //Wait for certain time to terminate thread pool safely.
            try {
                kafkaExecutors.awaitTermination(10,TimeUnit.SECONDS);
            } catch (InterruptedException e) {
                log.debug("Thread interrupted while waiting for safe termination of thread pool executor");
                //Stop the kafka executors abruptly. TODO : Think about the consequences?
                kafkaExecutors.shutdownNow();
            }
        }
        //Un-subscribe from event emitter
        eventEmitter.off(this.eventName, this);
        //Not really required, but considers an impossible case of someone calling loadAndStart on 'stopped' KafkaService instance
        ready = false;
        log.debug("Stopped listening to event: " + this.eventName);
    }

    @Override
    public void call(RollupEvent... rollupPayload) {
        kafkaExecutors.execute(new KafkaProducerWork(producerList.get(rand.nextInt(numberOfProducers)), rollupPayload));
    }

    //Used only for tests
    public ThreadPoolExecutor getKafkaExecutorsUnsafe() {
        return kafkaExecutors;
    }

    //Used only for tests
    public ArrayList<Producer> getProducerListUnsafe() {
        return producerList;
    }
}


File: blueflood-kafka/src/main/java/com/rackspacecloud/blueflood/outputs/handlers/helpers/KafkaProducerWork.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.handlers.helpers;

import com.rackspacecloud.blueflood.eventemitter.RollupEvent;
import kafka.javaapi.producer.Producer;
import kafka.producer.KeyedMessage;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;

public class KafkaProducerWork implements Runnable {
    private static final Logger log = LoggerFactory.getLogger(KafkaProducerWork.class);
    private RollupEvent[] rollupEventObjects;
    private Producer producer;

    public KafkaProducerWork(Producer producer, RollupEvent... objects) {
        this.rollupEventObjects = objects;
        this.producer = producer;
    }

    @Override
    public void run() {
        //TODO : Generalize this later to work for any event and not just rollup
        ArrayList<KeyedMessage<String, RollupEvent>> messages = new ArrayList<KeyedMessage<String, RollupEvent>>();
        for (RollupEvent rollupEvent : rollupEventObjects) {
            messages.add(new KeyedMessage<String, RollupEvent>(rollupEvent.getGranularityName(), rollupEvent));
        }
        log.debug("Sending messages to producer "+producer.toString());
        try {
            producer.send(messages);
        } catch (Exception e) {
            log.error("Error encountered while sending messages using Kafka Producer", e);
        }
    }
 }



File: blueflood-kafka/src/main/java/com/rackspacecloud/blueflood/outputs/serializers/KafkaRollupSerializer.java
/*
* Copyright 2013 Rackspace
*
*    Licensed under the Apache License, Version 2.0 (the "License");
*    you may not use this file except in compliance with the License.
*    You may obtain a copy of the License at
*
*        http://www.apache.org/licenses/LICENSE-2.0
*
*    Unless required by applicable law or agreed to in writing, software
*    distributed under the License is distributed on an "AS IS" BASIS,
*    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
*    See the License for the specific language governing permissions and
*    limitations under the License.
*/

package com.rackspacecloud.blueflood.outputs.serializers;

import com.rackspacecloud.blueflood.eventemitter.RollupEvent;
import com.rackspacecloud.blueflood.io.Constants;
import kafka.serializer.Decoder;
import kafka.serializer.Encoder;
import kafka.utils.VerifiableProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOError;

public class KafkaRollupSerializer implements Encoder<RollupEvent>, Decoder<RollupEvent> {
    private static final Logger log = LoggerFactory.getLogger(KafkaRollupSerializer.class);

    //When custom serializer is loaded by the kafka producer, it expects this constructor
    public KafkaRollupSerializer(VerifiableProperties properties) {

    }

    @Override
    public RollupEvent fromBytes(byte[] bytes) {
        //TODO :  Decide on requirements of consumer side and change accordingly
        return null;
    }

    @Override
    public byte[] toBytes(RollupEvent rollupPayload) {
        try {
            return RollupEventSerializer.serializeRollupEvent(rollupPayload).toString().getBytes(Constants.DEFAULT_CHARSET);
        } catch (Exception e) {
            log.error("Error encountered while serializing RollupEvent JSON to bytes: ", e);
            throw new IOError(e);
        }
    }
}


File: blueflood-kafka/src/main/java/com/rackspacecloud/blueflood/service/KafkaConfig.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.net.URL;
import java.util.Properties;

public class KafkaConfig {
    private static final Logger log = LoggerFactory.getLogger(KafkaConfig.class);
    private Properties props = new Properties();

    public KafkaConfig() {
        try {
            init();
        } catch (IOException ex) {
            log.error("Error encountered while loading the Kafka Config", ex);
            throw new RuntimeException(ex);
        }
    }

    private void init() throws IOException {
        //Load the configuration
        String configStr = System.getProperty("kafka.config");
        if (configStr != null) {
            URL configUrl = new URL(configStr);
            props.load(configUrl.openStream());
        }
    }

    public Properties getKafkaProperties() {
        return props;
    }

    public String getStringProperty(String name) {
        return props.getProperty(name);
    }

    public Integer getIntegerProperty(String propertyName) {
        return Integer.parseInt(getStringProperty(propertyName));
    }

    public boolean getBooleanProperty(String name) {
        return getStringProperty(name).equalsIgnoreCase("true");
    }
}


File: blueflood-kafka/src/main/java/com/rackspacecloud/blueflood/utils/KafkaGraphiteReporter.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.utils;

import com.rackspacecloud.blueflood.service.Configuration;
import com.rackspacecloud.blueflood.service.CoreConfig;
import com.yammer.metrics.Metrics;
import com.yammer.metrics.reporting.GraphiteReporter;
import kafka.metrics.KafkaMetricsReporter;
import kafka.utils.VerifiableProperties;
import org.apache.log4j.Logger;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

public class KafkaGraphiteReporter implements KafkaMetricsReporter, KafkaGraphiteReporterMBean {
    private static final Logger log = Logger.getLogger(KafkaGraphiteReporter.class);
    GraphiteReporter reporter;
    Configuration config = Configuration.getInstance();
    boolean initialized = false;
    boolean running = false;

    @Override
    public void init(VerifiableProperties props) {
        if (!initialized && !config.getStringProperty(CoreConfig.GRAPHITE_HOST).equals("")) {
            try {
                reporter = new GraphiteReporter(
                        Metrics.defaultRegistry(),
                        config.getStringProperty(CoreConfig.GRAPHITE_HOST),
                        config.getIntegerProperty(CoreConfig.GRAPHITE_PORT),
                        config.getStringProperty(CoreConfig.GRAPHITE_PREFIX + "kafka.")
                );
            } catch (IOException e) {
                log.error("Unable to initialize GraphiteReporter", e);
            }
            initialized = true;
            startReporter(30);
        }
    }


    @Override
    public void startReporter(long pollingInterval) {
        if (initialized && !running) {
            reporter.start(pollingInterval, TimeUnit.SECONDS);
            running = true;
            log.info(String.format("Started Kafka Graphite metrics reporter with polling period %d seconds", pollingInterval));
        }
    }

    @Override
    public void stopReporter() {
        if (initialized && running) {
            reporter.shutdown();
            running = false;
            log.info("Stopped Kafka Graphite metrics reporter");
        }
    }

    @Override
    public String getMBeanName() {
        final String name = String.format("com.rackspacecloud.blueflood.kafkagraphitemetricreporter:type=%s", getClass().getSimpleName());
        return name;
    }
}


File: blueflood-kafka/src/main/java/com/rackspacecloud/blueflood/utils/KafkaGraphiteReporterMBean.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.utils;

import kafka.metrics.KafkaMetricsReporterMBean;

public interface KafkaGraphiteReporterMBean extends KafkaMetricsReporterMBean {
}


File: blueflood-kafka/src/test/java/com/rackspacecloud/blueflood/outputs/handlers/KafkaServiceTest.java
/*
 * Copyright 2013 Rackspace
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

package com.rackspacecloud.blueflood.outputs.handlers;

import com.rackspacecloud.blueflood.eventemitter.RollupEvent;
import com.rackspacecloud.blueflood.eventemitter.RollupEventEmitter;
import com.rackspacecloud.blueflood.types.BasicRollup;
import junit.framework.Assert;
import kafka.javaapi.producer.Producer;
import kafka.producer.KeyedMessage;
import org.junit.Test;

import java.util.ArrayList;

import static org.mockito.Mockito.*;

public class KafkaServiceTest {
    String eventName = "rollup";
    RollupEvent rollupEvent = new RollupEvent(null, new BasicRollup(), "payload", "metrics_1440m", 0);

    @Test
    public void testKafkaService() throws Exception {

        KafkaService kafkaService = new KafkaService();
        KafkaService kafkaServiceSpy = spy(kafkaService);
        //Create a mock producer object and add it to the producer list
        Producer mockProducer = mock(Producer.class);
        ArrayList<Producer> producerList = kafkaServiceSpy.getProducerListUnsafe();
        producerList.clear();
        producerList.add(mockProducer);

        //Start KafkaProduction and test whether listener object was added
        kafkaServiceSpy.startService();
        Assert.assertTrue(RollupEventEmitter.getInstance().listeners(eventName).contains(kafkaServiceSpy));

        //Emit an event.
        RollupEventEmitter.getInstance().emit(eventName, rollupEvent);
        //Verify that the call method was called atleast once
        verify(kafkaServiceSpy, timeout(1000).atLeastOnce()).call(rollupEvent);

        //Test whether executor got the task
        Assert.assertEquals(kafkaServiceSpy.getKafkaExecutorsUnsafe().getTaskCount(), 1);
        //Verify that there were interactions with the mock producer
        verify(mockProducer, timeout(1000)).send(anyListOf(KeyedMessage.class));

        //Stop Kafka Production and test whether the listener object was removed
        kafkaServiceSpy.stopService();
        Assert.assertFalse(RollupEventEmitter.getInstance().listeners(eventName).contains(kafkaServiceSpy));

        //Reset mocks, emit event and check if methods are not called
        reset(kafkaServiceSpy, mockProducer);
        RollupEventEmitter.getInstance().emit(eventName, rollupEvent);
        verifyZeroInteractions(kafkaServiceSpy);
        verifyZeroInteractions(mockProducer);
    }
}
