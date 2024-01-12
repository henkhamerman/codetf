Refactoring Types: ['Extract Superclass']
/java/org/geoserver/wfs/response/OGRWrapper.java
/* (c) 2014 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.wfs.response;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.logging.Level;
import java.util.logging.Logger;

import org.apache.commons.io.FileUtils;
import org.apache.commons.io.IOUtils;
import org.geotools.util.logging.Logging;
import org.opengis.referencing.crs.CoordinateReferenceSystem;

/**
 * Helper used to invoke ogr2ogr
 * 
 * @author Andrea Aime - OpenGeo
 * 
 */
public class OGRWrapper {

    private static final Logger LOGGER = Logging.getLogger(OGRWrapper.class);

    private String ogrExecutable;
    private String gdalData;

    public OGRWrapper(String ogrExecutable, String gdalData) {
        this.ogrExecutable = ogrExecutable;
        this.gdalData = gdalData;
    }

    /**
     * Performs the conversion, returns the name of the (main) output file 
     */
    public File convert(File inputData, File outputDirectory, String typeName,
            OgrFormat format, CoordinateReferenceSystem crs) throws IOException, InterruptedException {
        // build the command line
        List<String> cmd = new ArrayList<String>();
        cmd.add(ogrExecutable);
        cmd.add("-f");
        cmd.add(format.ogrFormat);
        File crsFile = null;
        if (crs != null) {
            // we don't use an EPSG code since there is no guarantee we'll be able to reverse
            // engineer one. Using WKT also ensures the EPSG params such as the TOWGS84 ones are
            // not lost in the conversion
            // We also write to a file because some operating systems cannot take arguments with
            // quotes and spaces inside (and/or ProcessBuilder is not good enough to escape them)
            crsFile = File.createTempFile("gdal_srs", "wkt", inputData.getParentFile());
            cmd.add("-a_srs");
            String s = crs.toWKT();
            s = s.replaceAll("\n\r", "").replaceAll("  ", "");
            FileUtils.writeStringToFile(crsFile, s);
            cmd.add(crsFile.getAbsolutePath());
        }
        if (format.options != null) {
            for (String option : format.options) {
                cmd.add(option);
            }
        }
        String outFileName = typeName;
        if (format.fileExtension != null)
            outFileName += format.fileExtension;
        cmd.add(new File(outputDirectory, outFileName).getAbsolutePath());
        cmd.add(inputData.getAbsolutePath());

        StringBuilder sb = new StringBuilder();
        int exitCode = run(cmd, sb);
        if(crsFile != null) {
            crsFile.delete();
        }

        if (exitCode != 0)
            throw new IOException("ogr2ogr did not terminate successfully, exit code " + exitCode
                    + ". Was trying to run: " + cmd + "\nResulted in:\n" + sb);
        
        // csv output is a directory, handle that case gracefully
        File output = new File(outputDirectory, outFileName);
        if(output.isDirectory()) {
            output = new File(output, outFileName);
        }
        return output;
    }

    /**
     * Returns a list of the ogr2ogr supported formats
     * 
     * @return
     */
    public Set<String> getSupportedFormats() {
        try {
            // this one works up to ogr2ogr 1.7
            List<String> commands = new ArrayList<String>();
            commands.add(ogrExecutable);
            commands.add("--help");
            
            Set<String> formats = new HashSet<String>();
            addFormats(commands, formats);
            
            // this one is required starting with ogr2ogr 1.8
            commands = new ArrayList<String>();
            commands.add(ogrExecutable);
            commands.add("--long-usage");
            addFormats(commands, formats);

            return formats;
        } catch (Exception e) {
            LOGGER.log(Level.SEVERE,
                    "Could not get the list of output formats supported by ogr2ogr", e);
            return Collections.emptySet();
        }
    }

    private void addFormats(List<String> commands, Set<String> formats) throws IOException,
            InterruptedException {
        StringBuilder sb = new StringBuilder();
        // can't trust the exit code, --help exits with -1 on my pc
        run(commands, sb);
        
        String[] lines = sb.toString().split("\n");
        for (String line : lines) {
            if (line.matches("\\s*-f \".*")) {
                String format = line.substring(line.indexOf('"') + 1, line.lastIndexOf('"'));
                formats.add(format);
            }
        }
    }

    /**
     * Returns true if ogr2ogr is available, that is, if executing
     * "ogr2ogr --version" returns 0 as the exit code
     * 
     * @return
     */
    public boolean isAvailable() {
        List<String> commands = new ArrayList<String>();
        commands.add(ogrExecutable);
        commands.add("--version");

        try {
            return run(commands, null) == 0;
        } catch(Exception e) {
            LOGGER.log(Level.SEVERE, "Ogr2Ogr is not available", e);
            return false;
        }
    }

    /**
     * Runs the specified command appending the output to the string builder and
     * returning the exit code
     * 
     * @param cmd
     * @param sb
     * @return
     * @throws IOException
     * @throws InterruptedException
     */
    int run(List<String> cmd, StringBuilder sb) throws IOException, InterruptedException {
        // run the process and grab the output for error reporting purposes
        ProcessBuilder builder = new ProcessBuilder(cmd);
        if(gdalData != null)
            builder.environment().put("GDAL_DATA", gdalData);
        builder.redirectErrorStream(true);
        Process p = builder.start();
        BufferedReader reader = new BufferedReader(new InputStreamReader(p.getInputStream()));
        String line = null;
        while ((line = reader.readLine()) != null) {
            if (sb != null) {
                sb.append("\n");
                sb.append(line);
            }
        }
        return p.waitFor();
    }
}


File: src/extension/ogr/ogr-wfs/src/main/java/org/geoserver/wfs/response/Ogr2OgrConfigurator.java
/* (c) 2014 - 2015 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.wfs.response;

import java.io.InputStream;
import java.util.Set;
import java.util.logging.Level;
import java.util.logging.Logger;

import org.geoserver.config.util.SecureXStream;
import org.geoserver.platform.GeoServerExtensions;
import org.geoserver.platform.GeoServerResourceLoader;
import org.geoserver.platform.resource.Resource;
import org.geoserver.platform.resource.Resource.Type;
import org.geoserver.platform.resource.ResourceListener;
import org.geoserver.platform.resource.ResourceNotification;
import org.geotools.util.logging.Logging;
import org.springframework.context.ApplicationListener;
import org.springframework.context.event.ContextClosedEvent;

import com.thoughtworks.xstream.XStream;

/**
 * Loads the ogr2ogr.xml configuration file and configures the output format accordingly.
 *
 * <p>Also keeps tabs on the configuration file, reloading the file as needed.
 * @author Administrator
 *
 */
public class Ogr2OgrConfigurator implements ApplicationListener<ContextClosedEvent> {
    private static final Logger LOGGER = Logging.getLogger(Ogr2OgrConfigurator.class);

    public Ogr2OgrOutputFormat of;

    OGRWrapper wrapper;

    Resource configFile;

    // ConfigurationPoller
    private ResourceListener listener = new ResourceListener() {
        public void changed(ResourceNotification notify) {
            loadConfiguration();
        }
    };

    public Ogr2OgrConfigurator(Ogr2OgrOutputFormat format) {
        this.of = format;

        GeoServerResourceLoader loader = GeoServerExtensions.bean(GeoServerResourceLoader.class);
        configFile = loader.get("ogr2ogr.xml");
        loadConfiguration();
        configFile.addListener( listener );
    }

    public void loadConfiguration() {
        // start with the default configuration, override if we can load the file
        OgrConfiguration configuration = OgrConfiguration.DEFAULT;
        try {
            if (configFile.getType() == Type.RESOURCE) {
                InputStream in = configFile.in();
                try {
                    XStream xstream = buildXStream();
                    configuration = (OgrConfiguration) xstream.fromXML( in);
                }
                finally {
                    in.close();
                }
            }
        } catch (Exception e) {
            LOGGER.log(Level.SEVERE, "Error reading the ogr2ogr.xml configuration file", e);
        }

        if (configuration == null) {
            LOGGER.log(Level.INFO,
                            "Could not find/load the ogr2ogr.xml configuration file, using internal defaults");
        }

        // let's load the configuration
        OGRWrapper wrapper = new OGRWrapper(configuration.ogr2ogrLocation, configuration.gdalData);
        Set<String> supported = wrapper.getSupportedFormats();
        of.setOgrExecutable(configuration.ogr2ogrLocation);
        of.setGdalData(configuration.gdalData);
        of.clearFormats();
        for (OgrFormat format : configuration.formats) {
            if (supported.contains(format.ogrFormat)) {
                of.addFormat(format);
            } else {
                LOGGER.severe("Skipping '" + format.formatName + "' as its OGR format '"
                        + format.ogrFormat + "' is not among the ones supported by "
                        + configuration.ogr2ogrLocation);
            }
        }
    }

    /**
     * Builds and configures the XStream used for de-serializing the configuration
     * @return
     */
    static XStream buildXStream() {
        XStream xstream = new SecureXStream();
        xstream.alias("OgrConfiguration", OgrConfiguration.class);
        xstream.alias("Format", OgrFormat.class);
        xstream.allowTypes(new Class[] { OgrConfiguration.class, OgrFormat.class });
        xstream.addImplicitCollection(OgrFormat.class, "options", "option", String.class);
        return xstream;
    }

    /**
     * Kill all threads on web app context shutdown to avoid permgen leaks
     */
    public void onApplicationEvent(ContextClosedEvent event) {
        if( configFile != null ){
            configFile.removeListener(listener);
        }
    }

}


File: src/extension/ogr/ogr-wfs/src/main/java/org/geoserver/wfs/response/Ogr2OgrOutputFormat.java
/* (c) 2014 - 2015 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.wfs.response;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Level;
import java.util.zip.ZipOutputStream;

import org.geoserver.config.GeoServer;
import org.geoserver.data.util.IOUtils;
import org.geoserver.platform.Operation;
import org.geoserver.platform.ServiceException;
import org.geoserver.wfs.WFSException;
import org.geoserver.wfs.WFSGetFeatureOutputFormat;
import org.geoserver.wfs.request.FeatureCollectionResponse;
import org.geoserver.wfs.request.GetFeatureRequest;
import org.geoserver.wfs.request.Query;
import org.geotools.data.DataStore;
import org.geotools.data.shapefile.ShapefileDataStore;
import org.geotools.data.simple.SimpleFeatureCollection;
import org.geotools.data.simple.SimpleFeatureStore;
import org.geotools.data.store.EmptyFeatureCollection;
import org.geotools.feature.simple.SimpleFeatureTypeBuilder;
import org.geotools.gml.producer.FeatureTransformer;
import org.opengis.feature.simple.SimpleFeatureType;
import org.opengis.feature.type.AttributeDescriptor;
import org.opengis.feature.type.GeometryDescriptor;
import org.opengis.feature.type.GeometryType;
import org.opengis.referencing.crs.CoordinateReferenceSystem;

import com.vividsolutions.jts.geom.LineString;
import com.vividsolutions.jts.geom.LinearRing;
import com.vividsolutions.jts.geom.MultiLineString;
import com.vividsolutions.jts.geom.MultiPoint;
import com.vividsolutions.jts.geom.MultiPolygon;
import com.vividsolutions.jts.geom.Point;
import com.vividsolutions.jts.geom.Polygon;

public class Ogr2OgrOutputFormat extends WFSGetFeatureOutputFormat {
    
    /**
     * The types of geometries a shapefile can handle
     */
    private static final Set<Class> SHAPEFILE_GEOM_TYPES = new HashSet<Class>() {
        {
            add(Point.class);
            add(LineString.class);
            add(LinearRing.class);
            add(Polygon.class);
            add(MultiPoint.class);
            add(MultiLineString.class);
            add(MultiPolygon.class);
        }
    };
    
    /**
     * The fs path to ogr2ogr. If null, we'll assume ogr2ogr is in the PATH and
     * that we can execute it just by running ogr2ogr
     */
    String ogrPath = null;

    /**
     * The full path to ogr2ogr
     */
    String ogrExecutable = "ogr2ogr";
    
    /**
     * The GDAL_DATA folder
     */
    String gdalData = null;

    /**
     * The output formats we can generate using ogr2ogr. Using a concurrent
     * one so that it can be reconfigured while the output format is working
     */
    static Map<String, OgrFormat> formats = new ConcurrentHashMap<String, OgrFormat>();

    public Ogr2OgrOutputFormat(GeoServer gs) {
        // initialize with the key set of formats, so that it will change as
        // we register new formats
        super(gs, formats.keySet());
    }

    /**
     * Returns the ogr2ogr executable full path
     * 
     * @return
     */
    public String getOgrExecutable() {
        return ogrExecutable;
    }

    /**
     * Sets the ogr2ogr executable full path. The default value is simply
     * "ogr2ogr", which will work if ogr2ogr is in the path
     * 
     * @param ogrExecutable
     */
    public void setOgrExecutable(String ogrExecutable) {
        this.ogrExecutable = ogrExecutable;
    }
    
    /**
     * Returns the location of the gdal data folder (required to set the output srs)
     * @return
     */
    public String getGdalData() {
        return gdalData;
    }

    /**
     * Sets the location of the gdal data folder (requierd to set the output srs)
     * @param gdalData
     */
    public void setGdalData(String gdalData) {
        this.gdalData = gdalData;
    }

    /**
     * @see WFSGetFeatureOutputFormat#getMimeType(Object, Operation)
     */
    public String getMimeType(Object value, Operation operation) throws ServiceException {
        GetFeatureRequest request = GetFeatureRequest.adapt(operation.getParameters()[0]);
        String outputFormat = request.getOutputFormat();
        String mimeType = "";
        OgrFormat format = formats.get(outputFormat);
        if (format == null) {
            throw new WFSException("Unknown output format " + outputFormat);
        } else if (format.singleFile && request.getQueries().size() <= 1) {
            if (format.mimeType != null) {
                mimeType = format.mimeType;
            } else {
                // use a default binary blob
                mimeType = "application/octet-stream";
            }
        } else {
            mimeType = "application/zip";
        }
        return mimeType;
    }
    
    @Override
    public boolean canHandle(Operation operation) {
        // we can't handle anything if the ogr2ogr configuration failed
        if(formats.size() == 0) {
            return false;
        } else {
            return super.canHandle(operation);
        }
    }

    @Override
    public String getPreferredDisposition(Object value, Operation operation) {
        return DISPOSITION_ATTACH;
    }
    
    @Override
    public String getAttachmentFileName(Object value, Operation operation) {
        GetFeatureRequest request = GetFeatureRequest.adapt(operation.getParameters()[0]);
        String outputFormat = request.getOutputFormat();
        
        OgrFormat format = formats.get(outputFormat);
        List<Query> queries = request.getQueries();
        if (format == null) {
            throw new WFSException("Unknown output format " + outputFormat);
        } else if (!format.singleFile || queries.size() > 1) {
            String outputFileName = queries.get(0).getTypeNames().get(0).getLocalPart();
            return outputFileName + ".zip";
        } else {
            return null;
        }
    }
    
    /**
     * Adds a ogr format among the supported ones
     * 
     * @param parameters
     */
    public void addFormat(OgrFormat parameters) {
        formats.put(parameters.formatName, parameters);
    }

    /**
     * Get a list of supported ogr format
     *
     * @return
     */
    public List<OgrFormat> getFormats() {
        return new ArrayList<OgrFormat>(formats.values());
    }

    /**
     * Programmatically removes all formats
     * 
     * @param parameters
     */
    public void clearFormats() {
        formats.clear();
    }

    /**
     * Writes out the data to an OGR known format (GML/shapefile) to disk and
     * then ogr2ogr each generated file into the destination format. Finally,
     * zips up all the resulting files.
     */
    @Override
    protected void write(FeatureCollectionResponse featureCollection, OutputStream output, 
        Operation getFeature) throws IOException ,ServiceException {

        // figure out which output format we're going to generate
        GetFeatureRequest request = GetFeatureRequest.adapt(getFeature.getParameters()[0]);
        String outputFormat = request.getOutputFormat();

        OgrFormat format = formats.get(outputFormat);
        if (format == null)
            throw new WFSException("Unknown output format " + outputFormat);

        // create the first temp directory, used for dumping gs generated
        // content
        File tempGS = org.geoserver.data.util.IOUtils.createTempDirectory("ogrtmpin");
        File tempOGR = org.geoserver.data.util.IOUtils.createTempDirectory("ogrtmpout");

        // build the ogr wrapper used to run the ogr2ogr commands
        OGRWrapper wrapper = new OGRWrapper(ogrExecutable, gdalData);

        // actually export each feature collection
        try {
            Iterator outputFeatureCollections = featureCollection.getFeature().iterator();
            SimpleFeatureCollection curCollection;

            File outputFile = null;
            while (outputFeatureCollections.hasNext()) {
                curCollection = (SimpleFeatureCollection) outputFeatureCollections
                        .next();
                
                // write out the gml
                File intermediate = writeToDisk(tempGS, curCollection);

                // convert with ogr2ogr
                final SimpleFeatureType schema = curCollection.getSchema();
                final CoordinateReferenceSystem crs = schema.getCoordinateReferenceSystem();
                outputFile = wrapper.convert(intermediate, tempOGR, schema.getTypeName(), format, crs);

                // wipe out the input dir contents
                IOUtils.emptyDirectory(tempGS);
            }
            
            // was is a single file output?
            if(format.singleFile && featureCollection.getFeature().size() == 1) {
                FileInputStream fis = null;
                try {
                    fis = new FileInputStream(outputFile);
                    org.apache.commons.io.IOUtils.copy(fis, output);
                } finally {
                    if(fis != null) {
                        fis.close();
                    }
                }
            } else {
                // scan the output directory and zip it all
                ZipOutputStream zipOut = null;
                try {
                    zipOut = new ZipOutputStream(output);
                    IOUtils.zipDirectory(tempOGR, zipOut, null);
                    zipOut.finish();
                } finally {
                    org.apache.commons.io.IOUtils.closeQuietly(zipOut);
                }
            }

            // delete the input and output directories
            IOUtils.delete(tempGS);
            IOUtils.delete(tempOGR);
        } catch (Exception e) {
            throw new ServiceException("Exception occurred during output generation", e);
        }
    }
    
    /**
     * Writes to disk using shapefile if the feature type allows for it, GML otherwise
     * @param tempDir
     * @param curCollection
     * @return
     */
    private File writeToDisk(File tempDir,
            SimpleFeatureCollection curCollection) throws Exception {
        // ogr2ogr cannot handle empty gml collections, but it can handle empty
        // shapefiles
        final SimpleFeatureType originalSchema = curCollection.getSchema();
        if(curCollection.isEmpty()) {
            if(isShapefileCompatible(originalSchema)) {
                return writeShapefile(tempDir, curCollection);
            } else {
                SimpleFeatureType simplifiedShema = buildShapefileCompatible(originalSchema);
                return writeShapefile(tempDir, new EmptyFeatureCollection(simplifiedShema));
            }
        }
        
        // create the temp file for this output
        File outFile = new File(tempDir, originalSchema.getTypeName() + ".gml");

        // write out
        OutputStream os = null;
        try {
            os = new FileOutputStream(outFile);

            // let's invoke the transformer
            FeatureTransformer ft = new FeatureTransformer();
            ft.setNumDecimals(16);
            ft.getFeatureNamespaces().declarePrefix("gs",
                    originalSchema.getName().getNamespaceURI());
            ft.transform(curCollection, os);
        } finally {
            os.close();
        }

        return outFile;
    }
    
    private SimpleFeatureType buildShapefileCompatible(SimpleFeatureType originalSchema) {
        SimpleFeatureTypeBuilder tb = new SimpleFeatureTypeBuilder();
        tb.setName(originalSchema.getName());
        // add the fake geometry
        tb.add("the_geom", Point.class, originalSchema.getCoordinateReferenceSystem());
        // preserve all othr attributes
        for (AttributeDescriptor at : originalSchema.getAttributeDescriptors()) {
            if(!(at instanceof GeometryDescriptor)) {
                tb.add(at);
            }
        }
        return tb.buildFeatureType();
    }

    /**
     * Returns true if the schema has just one geometry and the geom type is known
     * @param schema
     * @return
     */
    private boolean isShapefileCompatible(SimpleFeatureType schema) {
        GeometryType gt = null;
        for (AttributeDescriptor at : schema.getAttributeDescriptors()) {
            if(at instanceof GeometryDescriptor) {
                if(gt == null)
                    gt = ((GeometryDescriptor) at).getType();
                else
                    // more than one geometry 
                    return false;
            }
        } 
        
        return gt != null && SHAPEFILE_GEOM_TYPES.contains(gt.getBinding()); 
    }
    
    private File writeShapefile(File tempDir,
            SimpleFeatureCollection collection) {
        SimpleFeatureType schema = collection.getSchema();

        SimpleFeatureStore fstore = null;
        DataStore dstore = null;
        File file = null;
        try {
            file = new File(tempDir, schema.getTypeName() + ".shp");
            dstore = new ShapefileDataStore(file.toURL());
            dstore.createSchema(schema);
            
            fstore = (SimpleFeatureStore) dstore.getFeatureSource(schema.getTypeName());
            fstore.addFeatures(collection);
        } catch (IOException ioe) {
            LOGGER.log(Level.WARNING,
                "Error while writing featuretype '" + schema.getTypeName() + "' to shapefile.", ioe);
            throw new ServiceException(ioe);
        } finally {
            if(dstore != null) {
                dstore.dispose();
            }
        }
        
        return file; 
    }
    
    @Override
    public List<String> getCapabilitiesElementNames() {
        return getAllCapabilitiesElementNames();
    }

}


File: src/extension/ogr/ogr-wfs/src/main/java/org/geoserver/wfs/response/OgrConfiguration.java
/* (c) 2014 - 2015 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.wfs.response;

import com.thoughtworks.xstream.XStream;

/**
 * Represents the ogr2ogr output format configuration as a whole.
 * Only used for XStream driven de-serialization
 * @author Andrea Aime - OpenGeo

 */
public class OgrConfiguration {
    public static final OgrConfiguration DEFAULT;
    static {
        DEFAULT = new OgrConfiguration();
        // assume it's in the classpath and GDAL_DATA is properly set in the enviroment
        DEFAULT.ogr2ogrLocation = "ogr2ogr";
        // add some default formats
        DEFAULT.formats = new OgrFormat[] {
                new OgrFormat("MapInfo File", "OGR-TAB", ".tab", false, null),
                new OgrFormat("MapInfo File", "OGR-MIF", ".mif", false, null, "-dsco", "FORMAT=MIF"),
                new OgrFormat("CSV", "OGR-CSV", ".csv", true, "text/csv", OgrType.TEXT),
                new OgrFormat("KML", "OGR-KML", ".kml", true, "application/vnd.google-earth.kml", OgrType.XML),
        };
    }

    public String ogr2ogrLocation;
    public String gdalData;
    public OgrFormat[] formats;

    public static void main(String[] args) {
        // generates the default configuration xml and prints it to the output
        XStream xstream = Ogr2OgrConfigurator.buildXStream();
        System.out.println(xstream.toXML(OgrConfiguration.DEFAULT));
    }
}


File: src/extension/ogr/ogr-wfs/src/main/java/org/geoserver/wfs/response/OgrFormat.java
/* (c) 2014 - 2015 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.wfs.response;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Parameters defining an output format generated using ogr2ogr from either a GML or a shapefile
 * dump
 *
 * @author Andrea Aime - OpenGeo
 *
 */
public class OgrFormat {
    /**
     * The -f parameter
     */
    public String ogrFormat;

    /**
     * The GeoServer output format name
     */
    public String formatName;

    /**
     * The extension of the generated file, if any (shall include a dot, example, ".tab")
     */
    public String fileExtension;

    /**
     * The options that will be added to the command line
     */
    public List<String> options;

    /**
     * The type of format, used to instantiate the correct converter
     */
    public OgrType type;

    /**
     * If the output is a single file that can be streamed back. In that case we also need to know the mime type
     */
    public boolean singleFile;

    /**
     * The mime type of the single file output
     */
    public String mimeType;

    public OgrFormat(String ogrFormat, String formatName, String fileExtension, boolean singleFile,
            String mimeType, OgrType type, String... options) {
        this.ogrFormat = ogrFormat;
        this.formatName = formatName;
        this.fileExtension = fileExtension;
        this.singleFile = singleFile;
        this.mimeType = mimeType;
        this.type = type;
        if (options != null) {
            this.options = new ArrayList<String>(Arrays.asList(options));
        }
        if (type == null) {
            this.type = OgrType.BINARY;
        }
    }

    public OgrFormat(String ogrFormat, String formatName, String fileExtension, boolean singleFile,
            String mimeType, String... options) {
        this(ogrFormat, formatName, fileExtension, singleFile, mimeType, OgrType.BINARY, options);
    }

}


File: src/extension/ogr/ogr-wfs/src/test/java/org/geoserver/wfs/response/OGRWrapperTest.java
/* (c) 2014 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.wfs.response;

import static org.junit.Assert.*;

import java.util.Set;

import org.junit.Assume;
import org.junit.Before;
import org.junit.Test;

public class OGRWrapperTest {

    private OGRWrapper ogr;

    @Before
    public void setUp() throws Exception {
        Assume.assumeTrue(Ogr2OgrTestUtil.isOgrAvailable());
        ogr = new OGRWrapper(Ogr2OgrTestUtil.getOgr2Ogr(), Ogr2OgrTestUtil.getGdalData());
    }
    
    @Test
    public void testAvaialable() {
        // kind of a smoke test, since ogr2ogrtestutil uses the same command!
        ogr.isAvailable();
    }
    
    @Test
    public void testFormats() {
        Set<String> formats = ogr.getSupportedFormats();
        // well, we can't know which formats ogr was complied with, but at least there will be one, right?
        assertTrue(formats.size() > 0);
        
        // these work on my machine, with fwtools 2.2.8
        //assertTrue(formats.contains("KML"));
        //assertTrue(formats.contains("CSV"));
        //assertTrue(formats.contains("ESRI Shapefile"));
        //assertTrue(formats.contains("MapInfo File"));
    }
}


File: src/extension/ogr/ogr-wfs/src/test/java/org/geoserver/wfs/response/Ogr2OgrFormatTest.java
/* (c) 2014 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.wfs.response;

import static org.junit.Assert.*;

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import javax.xml.transform.OutputKeys;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;

import net.opengis.wfs.FeatureCollectionType;
import net.opengis.wfs.GetFeatureType;
import net.opengis.wfs.WfsFactory;

import org.geoserver.config.impl.GeoServerImpl;
import org.geoserver.platform.Operation;
import org.geoserver.platform.Service;
import org.geotools.data.DataStore;
import org.geotools.data.property.PropertyDataStore;
import org.geotools.feature.FeatureCollection;
import org.geotools.util.Version;
import org.junit.Assume;
import org.junit.Before;
import org.junit.Test;
import org.opengis.filter.Filter;
import org.w3c.dom.Document;
import org.xml.sax.SAXException;

public class Ogr2OgrFormatTest {

    DataStore dataStore;

    Ogr2OgrOutputFormat ogr;

    Operation op;

    FeatureCollectionType fct;

    GetFeatureType gft;

    @Before
    public void setUp() throws Exception {
        // check if we can run the tests
        Assume.assumeTrue(Ogr2OgrTestUtil.isOgrAvailable());
        
        // the data source we'll use for the tests
        dataStore = new PropertyDataStore(new File("./src/test/java/org/geoserver/wfs/response"));

        // the output format (and let's add a few output formats to play with
        ogr = new Ogr2OgrOutputFormat(new GeoServerImpl());
        ogr.addFormat(new OgrFormat("KML", "OGR-KML", ".kml", true, "application/vnd.google-earth.kml"));
        ogr.addFormat(new OgrFormat("KML", "OGR-KML-ZIP", ".kml", false, "application/vnd.google-earth.kml"));
        ogr.addFormat(new OgrFormat("CSV", "OGR-CSV", ".csv", true, "text/csv"));
        ogr.addFormat(new OgrFormat("SHP", "OGR-SHP", ".shp", false, null));
        ogr.addFormat(new OgrFormat("MapInfo File", "OGR-MIF", ".mif", false, null, "-dsco", "FORMAT=MIF"));
        
        ogr.setOgrExecutable(Ogr2OgrTestUtil.getOgr2Ogr());
        ogr.setGdalData(Ogr2OgrTestUtil.getGdalData());

        // the EMF objects used to talk with the output format
        gft = WfsFactory.eINSTANCE.createGetFeatureType();
        fct = WfsFactory.eINSTANCE.createFeatureCollectionType();
        op = new Operation("GetFeature", new Service("WFS", null, new Version("1.0.0"), 
                Arrays.asList("GetFeature")), null, new Object[] { gft });
    }

    @Test
    public void testCanHandle() {
        gft.setOutputFormat("OGR-KML");
        assertTrue(ogr.canHandle(op));
        gft.setOutputFormat("OGR-CSV");
        assertTrue(ogr.canHandle(op));
        gft.setOutputFormat("RANDOM_FORMAT");
        assertTrue(ogr.canHandle(op));
    }

    @Test
    public void testContentTypeZip() {
        gft.setOutputFormat("OGR-SHP");
        assertEquals("application/zip", ogr.getMimeType(null, op));
    }
    
    @Test
    public void testContentTypeKml() {
        gft.setOutputFormat("OGR-KML");
        assertEquals("application/vnd.google-earth.kml", ogr.getMimeType(null, op));
    }

    @Test
    public void testSimpleKML() throws Exception {
        // prepare input
        FeatureCollection fc = dataStore.getFeatureSource("Buildings").getFeatures();
        fct.getFeature().add(fc);

        // write out
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        gft.setOutputFormat("OGR-KML");
        ogr.write(fct, bos, op);

        // parse the kml to check it's really xml... 
        Document dom = dom(new ByteArrayInputStream(bos.toByteArray()));
        // print(dom);

        // some very light assumptions on the contents, since we
        // cannot control how ogr encodes the kml... let's just assess
        // it's kml with the proper number of features
        assertEquals("kml", dom.getDocumentElement().getTagName());
        assertEquals(2, dom.getElementsByTagName("Placemark").getLength());
    }
    
    @Test
    public void testZippedKML() throws Exception {
        // prepare input
        FeatureCollection fc = dataStore.getFeatureSource("Buildings").getFeatures();
        fct.getFeature().add(fc);

        // write out
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        gft.setOutputFormat("OGR-KML-ZIP");
        ogr.write(fct, bos, op);
        
        // unzip the result
        ZipInputStream zis = new ZipInputStream(new ByteArrayInputStream(bos.toByteArray()));
        Document dom = null;
        ZipEntry entry = zis.getNextEntry(); 
        assertEquals("Buildings.kml", entry.getName());
        dom = dom(zis);
        
        // some very light assumptions on the contents, since we
        // cannot control how ogr encodes the kml... let's just assess
        // it's kml with the proper number of features
        assertEquals("kml", dom.getDocumentElement().getTagName());
        assertEquals(2, dom.getElementsByTagName("Placemark").getLength());
    }
    
    @Test
    public void testEmptyKML() throws Exception {
        // prepare input
        FeatureCollection fc = dataStore.getFeatureSource("Buildings").getFeatures(Filter.EXCLUDE);
        fct.getFeature().add(fc);

        // write out
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        gft.setOutputFormat("OGR-KML");
        ogr.write(fct, bos, op);

        // parse the kml to check it's really xml... 
        Document dom = dom(new ByteArrayInputStream(bos.toByteArray()));
        // print(dom);

        // some very light assumptions on the contents, since we
        // cannot control how ogr encodes the kml... let's just assess
        // it's kml with the proper number of features
        assertEquals("kml", dom.getDocumentElement().getTagName());
        assertEquals(0, dom.getElementsByTagName("Placemark").getLength());
    }
    
    @Test
    public void testSimpleCSV() throws Exception {
        // prepare input
        FeatureCollection fc = dataStore.getFeatureSource("Buildings").getFeatures();
        fct.getFeature().add(fc);

        // write out
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        gft.setOutputFormat("OGR-CSV");
        ogr.write(fct, bos, op);

        // read back
        String csv = read(new ByteArrayInputStream(bos.toByteArray()));
        
        // couple simple checks
        String[] lines = csv.split("\n");
        // headers and the two lines
        assertEquals(3, lines.length);
        assertTrue(csv.contains("123 Main Street"));
    }
    
    @Test
    public void testSimpleMIF() throws Exception {
        // prepare input
        FeatureCollection fc = dataStore.getFeatureSource("Buildings").getFeatures();
        fct.getFeature().add(fc);

        // write out
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        gft.setOutputFormat("OGR-MIF");
        ogr.write(fct, bos, op);

        // read back
        ZipInputStream zis = new ZipInputStream(new ByteArrayInputStream(bos.toByteArray()));
        
        // we should get two files at least, a .mif and a .mid
        Set<String> fileNames = new HashSet<String>();
        ZipEntry entry = null;
        while((entry = zis.getNextEntry()) != null) {
            fileNames.add(entry.getName());
        }
        assertTrue(fileNames.contains("Buildings.mif"));
        assertTrue(fileNames.contains("Buildings.mid"));
    }
    
    @Test
    public void testGeometrylessCSV() throws Exception {
        // prepare input
        FeatureCollection fc = dataStore.getFeatureSource("Geometryless").getFeatures();
        fct.getFeature().add(fc);

        // write out
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        gft.setOutputFormat("OGR-CSV");
        ogr.write(fct, bos, op);

        // read back
        String csv = read(new ByteArrayInputStream(bos.toByteArray()));
        
        // couple simple checks
        String[] lines = csv.split("\n");
        // headers and the feature lines
        assertEquals(4, lines.length);
        // let's see if one of the expected lines is there
        assertTrue(csv.contains("Alessia"));
    }
    
    @Test
    public void testAllTypesKML() throws Exception {
        // prepare input
        FeatureCollection fc = dataStore.getFeatureSource("AllTypes").getFeatures();
        fct.getFeature().add(fc);

        // write out
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        gft.setOutputFormat("OGR-KML");
        ogr.write(fct, bos, op);

        // read back
        Document dom = dom(new ByteArrayInputStream(bos.toByteArray()));
        // print(dom);

        // some very light assumptions on the contents, since we
        // cannot control how ogr encodes the kml... let's just assess
        // it's kml with the proper number of features
        assertEquals("kml", dom.getDocumentElement().getTagName());
        assertEquals(6, dom.getElementsByTagName("Placemark").getLength());
    }

    /**
     * Utility method to print out a dom.
     */
    protected void print(Document dom) throws Exception {
        TransformerFactory txFactory = TransformerFactory.newInstance();
        try {
            txFactory.setAttribute("{http://xml.apache.org/xalan}indent-number", new Integer(2));
        } catch (Exception e) {
            // some
        }

        Transformer tx = txFactory.newTransformer();
        tx.setOutputProperty(OutputKeys.METHOD, "xml");
        tx.setOutputProperty(OutputKeys.INDENT, "yes");

        tx.transform(new DOMSource(dom), new StreamResult(new OutputStreamWriter(System.out,
                "utf-8")));
    }
    
    protected String read(InputStream is) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(is));
        String line = null;
        StringBuilder sb = new StringBuilder();
        while((line = br.readLine()) != null) {
            sb.append(line);
            sb.append("\n");
        }
        return sb.toString();
    }

    /**
     * Parses a stream into a dom.
     * 
     * @param input
     * @param skipDTD
     *            If true, will skip loading and validating against the
     *            associated DTD
     */
    protected Document dom(InputStream input) throws ParserConfigurationException, SAXException,
            IOException {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        factory.setValidating(false);

        DocumentBuilder builder = factory.newDocumentBuilder();
        return builder.parse(input);
    }

}


File: src/extension/ogr/ogr-wfs/src/test/java/org/geoserver/wfs/response/Ogr2OgrTestUtil.java
/* (c) 2014 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.wfs.response;

import java.io.File;
import java.io.FileInputStream;
import java.util.Properties;
import java.util.logging.Level;
import java.util.logging.Logger;

import org.geotools.util.logging.Logging;

public class Ogr2OgrTestUtil {
    private static Logger LOGGER = Logging.getLogger(Ogr2OgrTestUtil.class);

    private static Boolean IS_OGR_AVAILABLE;
    private static String OGR2OGR;
    private static String GDAL_DATA;

    public static boolean isOgrAvailable() {

        // check this just once
        if (IS_OGR_AVAILABLE == null) {
            try {
                File props = new File("./src/test/resources/ogr2ogr.properties");
                Properties p = new Properties();
                p.load(new FileInputStream(props));
                
                OGR2OGR = p.getProperty("ogr2ogr");
                // assume it's in the path if the property file hasn't been configured
                if(OGR2OGR == null)
                    OGR2OGR = "ogr2ogr";
                GDAL_DATA = p.getProperty("gdalData");
                
                OGRWrapper ogr = new OGRWrapper(OGR2OGR, GDAL_DATA);
                IS_OGR_AVAILABLE = ogr.isAvailable();
            } catch (Exception e) {
                IS_OGR_AVAILABLE = false;
                e.printStackTrace();
                LOGGER.log(Level.SEVERE,
                        "Disabling ogr2ogr output format tests, as ogr2ogr lookup failed", e);
            }
        }

        return IS_OGR_AVAILABLE;
    }
    
    public static String getOgr2Ogr() {
        if(isOgrAvailable())
            return OGR2OGR;
        else
            return null;
    }
    
    public static String getGdalData() {
        if(isOgrAvailable())
            return GDAL_DATA;
        else
            return null;
    }
    
    
}


File: src/extension/ogr/ogr-wps/src/main/java/org/geoserver/wps/ogr/Ogr2OgrPPIOFactory.java
/* (c) 2015 Open Source Geospatial Foundation - all rights reserved
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */

package org.geoserver.wps.ogr;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import net.opengis.wfs.GetFeatureType;
import net.opengis.wfs.WfsFactory;

import org.geoserver.platform.Operation;
import org.geoserver.platform.Service;
import org.geoserver.wfs.response.Ogr2OgrOutputFormat;
import org.geoserver.wfs.response.OgrFormat;
import org.geoserver.wps.ppio.PPIOFactory;
import org.geoserver.wps.ppio.ProcessParameterIO;
import org.geotools.util.Version;

/**
 * Factory to create an output PPIO for each OGR format managed by ogr2ogr libraries.
 */

public class Ogr2OgrPPIOFactory implements PPIOFactory {

    private Ogr2OgrOutputFormat ogr2OgrOutputFormat;

    public Ogr2OgrPPIOFactory(Ogr2OgrOutputFormat ogr2OgrOutputFormat) {
        this.ogr2OgrOutputFormat = ogr2OgrOutputFormat;
    }

    /**
     * This allow to instantiate the right type of PPIO subclass, {@link org.geoserver.wps.ppio.BinaryPPIO} for binary,
     * {@link org.geoserver.wps.ppio.CDataPPIO} for text, {@link org.geoserver.wps.ppio.XMLPPIO} for xml to serve the format as a process parameter
     * output.
     */
    @Override
    public List<ProcessParameterIO> getProcessParameterIO() {
        List<ProcessParameterIO> ogrParams = new ArrayList<ProcessParameterIO>();
        for (OgrFormat of : this.ogr2OgrOutputFormat.getFormats()) {
            ProcessParameterIO ppio = null;
            GetFeatureType gft = WfsFactory.eINSTANCE.createGetFeatureType();
            gft.setOutputFormat(of.formatName);
            Operation operation = new Operation("GetFeature", new Service("WFS", null, new Version(
                    "1.1.0"), Arrays.asList("GetFeature")), null, new Object[] { gft });
            // String computedMimeType = of.mimeType;
            // if (computedMimeType == null || computedMimeType.isEmpty()) {
            String computedMimeType = ogr2OgrOutputFormat.getMimeType(null, operation);
            if (of.formatName != null && !of.formatName.isEmpty()) {
                computedMimeType = computedMimeType + "; subtype=" + of.formatName;
            }
            // }
            if (of.type == null) {
                // Binary is default type
                ppio = new OgrBinaryPPIO(computedMimeType, of.fileExtension, ogr2OgrOutputFormat,
                        operation);
            } else {
                switch (of.type) {
                case BINARY:
                    ppio = new OgrBinaryPPIO(computedMimeType, of.fileExtension,
                            ogr2OgrOutputFormat, operation);
                    break;
                case TEXT:
                    ppio = new OgrCDataPPIO(computedMimeType, of.fileExtension,
                            ogr2OgrOutputFormat, operation);
                    break;
                case XML:
                    ppio = new OgrXMLPPIO(computedMimeType, of.fileExtension, ogr2OgrOutputFormat,
                            operation);
                    break;
                default:
                    break;
                }
            }
            if (ppio != null) {
                ogrParams.add(ppio);
            }
        }
        return ogrParams;
    }
}


File: src/extension/ogr/ogr-wps/src/test/java/org/geoserver/wps/ogr/WPSOgrTest.java
/* (c) 2015 Open Source Geospatial Foundation - all rights reserved
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.wps.ogr;

import static junit.framework.Assert.assertEquals;
import static org.custommonkey.xmlunit.XMLAssert.assertXpathExists;
import static org.junit.Assert.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

import org.custommonkey.xmlunit.SimpleNamespaceContext;
import org.custommonkey.xmlunit.XMLUnit;
import org.custommonkey.xmlunit.XpathEngine;
import org.geoserver.platform.GeoServerExtensions;
import org.geoserver.platform.GeoServerResourceLoader;
import org.geoserver.wfs.response.Ogr2OgrConfigurator;
import org.geoserver.wfs.response.Ogr2OgrTestUtil;
import org.geoserver.wfs.response.OgrConfiguration;
import org.geoserver.wfs.response.OgrFormat;
import org.geoserver.wps.WPSTestSupport;
import org.junit.Assume;
import org.junit.Before;
import org.junit.Test;
import org.w3c.dom.Document;

import com.mockrunner.mock.web.MockHttpServletResponse;
import com.thoughtworks.xstream.XStream;

public class WPSOgrTest extends WPSTestSupport {

    @Before
    public void setUp() throws Exception {
        Assume.assumeTrue(Ogr2OgrTestUtil.isOgrAvailable());
    }

    private File loadConfiguration() throws Exception {
        String ogrConfigruationName = "ogr2ogr.xml";
        GeoServerResourceLoader loader = GeoServerExtensions.bean(GeoServerResourceLoader.class);

        XStream xstream = buildXStream();
        ClassLoader classLoader = getClass().getClassLoader();
        File file = new File(classLoader.getResource(ogrConfigruationName).getFile());
        OgrConfiguration ogrConfiguration = (OgrConfiguration) xstream.fromXML(file);
        ogrConfiguration.ogr2ogrLocation = Ogr2OgrTestUtil.getOgr2Ogr();
        ogrConfiguration.gdalData = Ogr2OgrTestUtil.getGdalData();

        File configuration = loader.createFile(ogrConfigruationName);
        xstream.toXML(ogrConfiguration, new FileOutputStream(configuration));

        Ogr2OgrConfigurator configurator = applicationContext.getBean(Ogr2OgrConfigurator.class);
        configurator.loadConfiguration();

        return configuration;
    }

    @Test
    public void testConfigurationLoad() throws Exception {
        File configuration = null;
        try {
            configuration = loadConfiguration();
            Ogr2OgrConfigurator configurator = applicationContext
                    .getBean(Ogr2OgrConfigurator.class);
            configurator.loadConfiguration();
            List<String> formatNames = new ArrayList<>();
            for (OgrFormat f : configurator.of.getFormats()) {
                formatNames.add(f.formatName);
            }
            assertTrue(formatNames.contains("OGR-TAB"));
            assertTrue(formatNames.contains("OGR-MIF"));
            assertTrue(formatNames.contains("OGR-CSV"));
            assertTrue(formatNames.contains("OGR-KML"));
        } catch (IOException e) {
            System.err.println(e.getStackTrace());
        } finally {
            if (configuration != null) {
                configuration.delete();
            }
        }
    }

    @Test
    public void testDescribeProcess() throws Exception {
        OgrConfiguration.DEFAULT.ogr2ogrLocation = Ogr2OgrTestUtil.getOgr2Ogr();
        OgrConfiguration.DEFAULT.gdalData = Ogr2OgrTestUtil.getGdalData();
        Ogr2OgrConfigurator configurator = applicationContext.getBean(Ogr2OgrConfigurator.class);
        configurator.loadConfiguration();
        Document d = getAsDOM(root()
                + "service=wps&request=describeprocess&identifier=gs:BufferFeatureCollection");
        String base = "/wps:ProcessDescriptions/ProcessDescription/ProcessOutputs";
        for (OgrFormat f : OgrConfiguration.DEFAULT.formats) {
            if (f.mimeType != null) {
                assertXpathExists(base + "/Output[1]/ComplexOutput/Supported/Format[MimeType='"
                        + f.mimeType + "; subtype=" + f.formatName + "']", d);
            }
        }
    }

    @Test
    public void testOGRKMLOutputExecuteRaw() throws Exception {
        File configuration = null;
        try {
            configuration = loadConfiguration();
            Ogr2OgrConfigurator configurator = applicationContext
                    .getBean(Ogr2OgrConfigurator.class);
            configurator.loadConfiguration();
            MockHttpServletResponse r = postAsServletResponse("wps",
                    getWpsRawXML("application/vnd.google-earth.kml; subtype=OGR-KML"));
            assertEquals("application/vnd.google-earth.kml; subtype=OGR-KML", r.getContentType());
            assertTrue(r.getOutputStreamContent().length() > 0);

        } catch (IOException e) {
            System.err.println(e.getStackTrace());
        } finally {
            if (configuration != null) {
                configuration.delete();
            }
        }
    }

    @Test
    public void testOGRKMLOutputExecuteDocument() throws Exception {
        File configuration = null;
        try {
            configuration = loadConfiguration();
            Ogr2OgrConfigurator configurator = applicationContext
                    .getBean(Ogr2OgrConfigurator.class);
            configurator.loadConfiguration();
            Document d = postAsDOM("wps",
                    getWpsDocumentXML("application/vnd.google-earth.kml; subtype=OGR-KML"));
            Map<String, String> m = new HashMap<String, String>();
            m.put("kml", "http://www.opengis.net/kml/2.2");
            org.custommonkey.xmlunit.NamespaceContext ctx = new SimpleNamespaceContext(m);
            XpathEngine engine = XMLUnit.newXpathEngine();
            engine.setNamespaceContext(ctx);
            assertEquals(1, engine.getMatchingNodes("//kml:kml/kml:Document/kml:Schema", d)
                    .getLength());
        } catch (IOException e) {
            System.err.println(e.getStackTrace());
        } finally {
            if (configuration != null) {
                configuration.delete();
            }
        }
    }

    @Test
    public void testOGRCSVOutputExecuteDocument() throws Exception {
        File configuration = null;
        try {
            configuration = loadConfiguration();
            Ogr2OgrConfigurator configurator = applicationContext
                    .getBean(Ogr2OgrConfigurator.class);
            configurator.loadConfiguration();
            MockHttpServletResponse r = postAsServletResponse("wps",
                    getWpsRawXML("text/csv; subtype=OGR-CSV"));
            assertEquals("text/csv; subtype=OGR-CSV", r.getContentType());
            assertTrue(r.getOutputStreamContent().length() > 0);
            assertTrue(r.getOutputStreamContent().contains("WKT,gml_id,STATE_NAME"));
        } catch (IOException e) {
            System.err.println(e.getStackTrace());
        } finally {
            if (configuration != null) {
                configuration.delete();
            }
        }
    }

    @Test
    public void testOGRBinaryOutputExecuteDocument() throws Exception {
        File configuration = null;
        try {
            configuration = loadConfiguration();
            Ogr2OgrConfigurator configurator = applicationContext
                    .getBean(Ogr2OgrConfigurator.class);
            configurator.loadConfiguration();
            MockHttpServletResponse r = postAsServletResponse("wps",
                    getWpsRawXML("application/zip; subtype=OGR-TAB"));
            assertEquals("application/zip; subtype=OGR-TAB", r.getContentType());
            ByteArrayInputStream bis = getBinaryInputStream(r);
            ZipInputStream zis = new ZipInputStream(bis);
            ZipEntry entry = null;
            boolean found = false;
            while ((entry = zis.getNextEntry()) != null) {
                final String name = entry.getName();
                zis.closeEntry();
                if (name.equals("feature.tab")) {
                    found = true;
                    break;
                }
            }
            zis.close();
            assertTrue(found);
        } catch (IOException e) {
            System.err.println(e.getStackTrace());
        } finally {
            if (configuration != null) {
                configuration.delete();
            }
        }
    }

    private String getWpsRawXML(String ouputMime) throws Exception {
        String xml = "<wps:Execute service='WPS' version='1.0.0' xmlns:wps='http://www.opengis.net/wps/1.0.0' "
                + "xmlns:ows='http://www.opengis.net/ows/1.1'>"
                + "<ows:Identifier>gs:BufferFeatureCollection</ows:Identifier>"
                + "<wps:DataInputs>"
                + "<wps:Input>"
                + "<ows:Identifier>features</ows:Identifier>"
                + "<wps:Data>"
                + "<wps:ComplexData mimeType=\"application/json\"><![CDATA["
                + readFileIntoString("states-FeatureCollection.json")
                + "]]></wps:ComplexData>"
                + "</wps:Data>"
                + "</wps:Input>"
                + "<wps:Input>"
                + "<ows:Identifier>distance</ows:Identifier>"
                + "<wps:Data>"
                + "<wps:LiteralData>10</wps:LiteralData>"
                + "</wps:Data>"
                + "</wps:Input>"
                + "</wps:DataInputs>"
                + "<wps:ResponseForm>"
                + "<wps:RawDataOutput mimeType=\""
                + ouputMime
                + "\">"
                + "<ows:Identifier>result</ows:Identifier>"
                + "</wps:RawDataOutput>" + "</wps:ResponseForm>" + "</wps:Execute>";
        return xml;
    }

    private String getWpsDocumentXML(String ouputMime) throws Exception {
        String xml = "<wps:Execute service='WPS' version='1.0.0' xmlns:wps='http://www.opengis.net/wps/1.0.0' "
                + "xmlns:ows='http://www.opengis.net/ows/1.1'>"
                + "<ows:Identifier>gs:BufferFeatureCollection</ows:Identifier>"
                + "<wps:DataInputs>"
                + "<wps:Input>"
                + "<ows:Identifier>features</ows:Identifier>"
                + "<wps:Data>"
                + "<wps:ComplexData mimeType=\"application/json\"><![CDATA["
                + readFileIntoString("states-FeatureCollection.json")
                + "]]></wps:ComplexData>"
                + "</wps:Data>"
                + "</wps:Input>"
                + "<wps:Input>"
                + "<ows:Identifier>distance</ows:Identifier>"
                + "<wps:Data>"
                + "<wps:LiteralData>10</wps:LiteralData>"
                + "</wps:Data>"
                + "</wps:Input>"
                + "</wps:DataInputs>"
                + "<wps:ResponseForm>"
                + "<wps:ResponseDocument>"
                + "<wps:Output mimeType=\""
                + ouputMime
                + "\">"
                + "<ows:Identifier>result</ows:Identifier>"
                + "</wps:Output>"
                + "</wps:ResponseDocument>" + "</wps:ResponseForm>" + "</wps:Execute>";
        return xml;
    }

    private static XStream buildXStream() {
        XStream xstream = new XStream();
        xstream.alias("OgrConfiguration", OgrConfiguration.class);
        xstream.alias("Format", OgrFormat.class);
        xstream.addImplicitCollection(OgrFormat.class, "options", "option", String.class);
        return xstream;
    }


}
