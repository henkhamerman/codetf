Refactoring Types: ['Extract Method']
eeplearning4j/translate/CaffeModelToJavaClass.java
package org.deeplearning4j.translate;

import org.deeplearning4j.caffe.Caffe.*;
import com.google.protobuf.CodedInputStream;
import org.springframework.core.io.ClassPathResource;

import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;

/**
 * Created by jeffreytang on 7/9/15.
 */
public class CaffeModelToJavaClass {

    public static NetParameter readCaffeModel(String caffeModelPath, int sizeLimitMb) throws IOException {
        InputStream is = new FileInputStream(caffeModelPath);
        CodedInputStream codeStream = CodedInputStream.newInstance(is);
        // Increase the limit when loading bigger caffemodels size
        int oldLimit = codeStream.setSizeLimit(sizeLimitMb * 1024 * 1024);
        return NetParameter.parseFrom(codeStream);
    }
}


File: dl4j-caffe/src/test/java/org/deeplearning4j/translate/CaffeTest.java
package org.deeplearning4j.translate;

import org.deeplearning4j.caffe.Caffe.NetParameter;
import org.springframework.core.io.ClassPathResource;
import org.junit.Test;
import static org.junit.Assert.*;

import java.io.IOException;
import java.nio.file.Paths;

/**
 * Created by jeffreytang on 7/11/15.
 */
public class CaffeTest {

    @Test
    public void testCaffeModelToJavaClass() throws Exception {
        // caffemodel downloaded from https://gist.github.com/mavenlin/d802a5849de39225bcc6
        String imagenetCaffeModelPath = new ClassPathResource("nin_imagenet_conv.caffemodel").getURL().getFile();

        NetParameter net = CaffeModelToJavaClass.readCaffeModel(imagenetCaffeModelPath, 1000);
        assertEquals(net.getName(), "CaffeNet");
        assertEquals(net.getLayersCount(), 31);
        assertEquals(net.getLayers(0).getName(), "data");
        assertEquals(net.getLayers(30).getName(), "loss");
        assertEquals(net.getLayers(15).getBlobs(0).getData(0), -0.008252043f, 1e-1);

    }

}
