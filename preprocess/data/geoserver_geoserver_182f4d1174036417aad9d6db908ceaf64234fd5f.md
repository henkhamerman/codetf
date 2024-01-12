Refactoring Types: ['Pull Up Method']
c/main/java/org/geoserver/importer/Directory.java
/* (c) 2014 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.importer;

import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FilenameFilter;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.NoSuchElementException;
import java.util.Set;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.zip.ZipOutputStream;

import org.apache.commons.fileupload.FileItem;
import org.apache.commons.io.FilenameUtils;
import org.geoserver.data.util.IOUtils;
import org.geotools.util.logging.Logging;
import org.geoserver.importer.job.ProgressMonitor;

import com.google.common.base.Predicate;
import com.google.common.collect.Iterables;

public class Directory extends FileData {

    private static final Logger LOGGER = Logging.getLogger(Directory.class);
    
    private static final long serialVersionUID = 1L;

    /**
     * list of files contained in directory
     */
    protected List<FileData> files = new ArrayList<FileData>();

    /**
     * flag controlling whether file look up should recurse into sub directories.
     */
    boolean recursive;
    String name;

    public Directory(File file) {
        this(file, true);
    }

    public Directory(File file, boolean recursive) {
        super(file);
        this.recursive = recursive;
    }

    public static Directory createNew(File parent) throws IOException {
        File directory = File.createTempFile("tmp", "", parent);
        if (!directory.delete() || !directory.mkdir()) throw new IOException("Error creating temp directory at " + directory.getAbsolutePath());
        return new Directory(directory);
    }

    public static Directory createFromArchive(File archive) throws IOException {
        VFSWorker vfs = new VFSWorker();
        if (!vfs.canHandle(archive)) {
            throw new IOException(archive.getPath() + " is not a recognizable  format");
        }

        String basename = FilenameUtils.getBaseName(archive.getName());
        File dir = new File(archive.getParentFile(), basename);
        int i = 0;
        while (dir.exists()) {
            dir = new File(archive.getParentFile(), basename + i++);
        }
        vfs.extractTo(archive, dir);
        return new Directory(dir);
    }

    public File getFile() {
        return file;
    }

    public List<FileData> getFiles() {
        return files;
    }

    public void unpack(File file) throws IOException {
        //if the file is an archive, unpack it
        VFSWorker vfs = new VFSWorker();
        if (vfs.canHandle(file)) {
            LOGGER.fine("unpacking " + file.getAbsolutePath() + " to " + this.file.getAbsolutePath());
            vfs.extractTo(file, this.file);

            LOGGER.fine("deleting " + file.getAbsolutePath());
            if (!file.delete()) {
                throw new IOException("unable to delete file");
            }
        }
    }
    
    public File child(String name) {
        if (name == null) {
            //create random
            try {
                return File.createTempFile("child", "tmp", file);
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        }

        return new File(this.file,name);
    }

    public void setName(String name) {
        this.name = name;
    }

    @Override
    public String getName() {
        return this.name != null ? this.name : file.getName();
    }

    @Override
    public void prepare(ProgressMonitor m) throws IOException {
        files = new ArrayList<FileData>();

        //recursively search for spatial files, maintain a queue of directories to recurse into
        LinkedList<File> q = new LinkedList<File>();
        q.add(file);

        while(!q.isEmpty()) {
            File dir = q.poll();

            if (m.isCanceled()){
                return;
            }
            m.setTask("Scanning " + dir.getPath());

            //get all the regular (non directory) files
            Set<File> all = new LinkedHashSet<File>(Arrays.asList(dir.listFiles(new FilenameFilter() {
                public boolean accept(File dir, String name) {
                    return !new File(dir, name).isDirectory();
                }
            })));

            //scan all the files looking for spatial ones
            for (File f : dir.listFiles()) {
                if (f.isHidden()) {
                    all.remove(f);
                    continue;
                }
                if (f.isDirectory()) {
                    if (!recursive && !f.equals(file)) {
                        //skip it
                        continue;
                    }
                    // @hacky - ignore __MACOSX
                    // this could probably be dealt with in a better way elsewhere
                    // like by having Directory ignore the contents since they
                    // are all hidden files anyway
                    if (!"__MACOSX".equals(f.getName())) {
                        Directory d = new Directory(f);
                        d.prepare(m);

                        files.add(d);
                    }
                    //q.push(f);
                    continue;
                }

                //special case for .aux files, they are metadata but get picked up as readable 
                // by the erdas imagine reader...just ignore them for now 
                if ("aux".equalsIgnoreCase(FilenameUtils.getExtension(f.getName()))) {
                    continue;
                }

                //determine if this is a spatial format or not
                DataFormat format = DataFormat.lookup(f);

                if (format != null) {
                    SpatialFile sf = newSpatialFile(f, format);
                    
                    //gather up the related files
                    sf.prepare(m);

                    files.add(sf);

                    all.removeAll(sf.allFiles());
                }
            }

            //take any left overs and add them as unspatial/unrecognized
            for (File f : all) {
                files.add(new ASpatialFile(f));
            }
        }

        format = format();
//        //process ignored for files that should be grouped with the spatial files
//        for (DataFile df : files) {
//            SpatialFile sf = (SpatialFile) df;
//            String base = FilenameUtils.getBaseName(sf.getFile().getName());
//            for (Iterator<File> i = ignored.iterator(); i.hasNext(); ) {
//                File f = i.next();
//                if (base.equals(FilenameUtils.getBaseName(f.getName()))) {
//                    //.prj file?
//                    if ("prj".equalsIgnoreCase(FilenameUtils.getExtension(f.getName()))) {
//                        sf.setPrjFile(f);
//                    }
//                    else {
//                        sf.getSuppFiles().add(f);
//                    }
//                    i.remove();
//                }
//            }
//        }
//        
//        //take any left overs and add them as unspatial/unrecognized
//        for (File f : ignored) {
//            files.add(new ASpatialFile(f));
//        }
//        
//        return files;
//        
//        for (DataFile f : files()) {
//            f.prepare();
//        }
    }

    /**
     * Creates a new spatial file.
     * 
     * @param f The raw file.
     * @param format The spatial format of the file.
     */
    protected SpatialFile newSpatialFile(File f, DataFormat format) {
        SpatialFile sf = new SpatialFile(f);
        sf.setFormat(format);
        return sf;
    }

    public List<Directory> flatten() {
        List<Directory> flat = new ArrayList<Directory>();

        LinkedList<Directory> q = new LinkedList<Directory>();
        q.addLast(this);
        while(!q.isEmpty()) {
            Directory dir = q.removeFirst();
            flat.add(dir);

            for (Iterator<FileData> it = dir.getFiles().iterator(); it.hasNext(); ) {
                FileData f = it.next();
                if (f instanceof Directory) {
                    Directory d = (Directory) f;
                    it.remove();
                    q.addLast(d);
                }
            }
        }

        return flat;
    }

//    public List<DataFile> files() throws IOException {
//        LinkedList<DataFile> files = new LinkedList<DataFile>();
//        
//        LinkedList<File> ignored = new LinkedList<File>();
//
//        LinkedList<File> q = new LinkedList<File>();
//        q.add(file);
//
//        while(!q.isEmpty()) {
//            File f = q.poll();
//
//            if (f.isDirectory()) {
//                q.addAll(Arrays.asList(f.listFiles()));
//                continue;
//            }
//
//            //determine if this is a spatial format or not
//            DataFormat format = DataFormat.lookup(f);
//
//            if (format != null) {
//                SpatialFile file = new SpatialFile(f);
//                file.setFormat(format);
//                files.add(file);
//            }
//            else {
//                ignored.add(f);
//            }
//        }
//        
//        //process ignored for files that should be grouped with the spatial files
//        for (DataFile df : files) {
//            SpatialFile sf = (SpatialFile) df;
//            String base = FilenameUtils.getBaseName(sf.getFile().getName());
//            for (Iterator<File> i = ignored.iterator(); i.hasNext(); ) {
//                File f = i.next();
//                if (base.equals(FilenameUtils.getBaseName(f.getName()))) {
//                    //.prj file?
//                    if ("prj".equalsIgnoreCase(FilenameUtils.getExtension(f.getName()))) {
//                        sf.setPrjFile(f);
//                    }
//                    else {
//                        sf.getSuppFiles().add(f);
//                    }
//                    i.remove();
//                }
//            }
//        }
//        
//        //take any left overs and add them as unspatial/unrecognized
//        for (File f : ignored) {
//            files.add(new ASpatialFile(f));
//        }
//        
//        return files;
//    }

    /**
     * Returns the data format of the files in the directory iff all the files are of the same 
     * format, if they are not this returns null.
     */
    public DataFormat format() throws IOException {
        if (files.isEmpty()) {
            LOGGER.warning("no files recognized");
            return null;
        }

        FileData file = files.get(0);
        DataFormat format = file.getFormat();
        for (int i = 1; i < files.size(); i++) {
            FileData other = files.get(i);
            if (format != null && !format.equals(other.getFormat())) {
                logFormatMismatch();
                return null;
            }
            if (format == null && other.getFormat() != null) {
                logFormatMismatch();
                return null;
            }
        }

        return format;
    }

    private void logFormatMismatch() {
        StringBuilder buf = new StringBuilder("all files are not the same format:\n");
        for (int i = 0; i < files.size(); i++) {
            FileData f = files.get(i);
            String format = "not recognized";
            if (f.getFormat() != null) {
                format = f.getName();
            }
            buf.append(f.getFile().getName()).append(" : ").append(format).append('\n');
        }
        LOGGER.warning(buf.toString());
    }

    public Directory filter(List<FileData> files) {
        Filtered f = new Filtered(file, files);
        f.setFormat(getFormat());
        return f;
    }

    @Override
    public String toString() {
        return file.getPath();
    }

    public void accept(String childName, InputStream in) throws IOException {
        File dest = child(childName);
        
        IOUtils.copy(in, dest);

        try {
            unpack(dest);
        } catch (IOException ioe) {
            // problably should delete on error
            LOGGER.warning("Possible invalid file uploaded to " + dest.getAbsolutePath());
            throw ioe;
        }
    }

    public void accept(FileItem item) throws Exception {
        File dest = child(item.getName());
        item.write(dest);

        try {
            unpack(dest);
        } 
        catch (IOException e) {
            // problably should delete on error
            LOGGER.warning("Possible invalid file uploaded to " + dest.getAbsolutePath());
            throw e;
        }
    }
    
    public void archive(File output) throws IOException {
        File archiveDir = output.getAbsoluteFile().getParentFile();
        String outputName = output.getName().replace(".zip","");
        int id = 0;
        while (output.exists()) {
            output = new File(archiveDir, outputName + id + ".zip");
            id++;
        }
        ZipOutputStream zout = new ZipOutputStream(new BufferedOutputStream(new FileOutputStream(output)));
        Exception error = null;

        // don't call zout.close in finally block, if an error occurs and the zip
        // file is empty by chance, the second error will mask the first
        try {
            IOUtils.zipDirectory(file, zout, null);
        } catch (Exception ex) {
            error = ex;
            try {
                zout.close();
            } catch (Exception ex2) {
                // nothing, we're totally aborting
            }
            output.delete();
            if (ex instanceof IOException) throw (IOException) ex;
            throw (IOException) new IOException("Error archiving").initCause(ex);
        } 
        
        // if we get here, the zip is properly written
        try {
            zout.close();
        } finally {
            cleanup();
        }
    }

    @Override
    public void cleanup() throws IOException {
        File[] files = file.listFiles();
        if (files != null) {
            for (File f: files) {
                if (f.isDirectory()) {
                    new Directory(f).cleanup();
                } else {
                    if (LOGGER.isLoggable(Level.FINE)) {
                        LOGGER.fine("Deleting file " + f.getAbsolutePath());
                    }
                    if (!f.delete()) {
                        throw new IOException("unable to delete " + f);
                    }
                }
            }
        }
        super.cleanup();
    }

    @Override
    public FileData part(final String name) {
        List<FileData> files = this.files;
        if (this instanceof Filtered) {
            files = ((Filtered)this).filter;
        }

        try {
            return Iterables.find(files, new Predicate<FileData>() {
                @Override
                public boolean apply(FileData input) {
                    return name.equals(input.getName());
                }
            });
        }
        catch(NoSuchElementException e) {
            return null;
        }
    }

    static class Filtered extends Directory {

        List<FileData> filter;

        public Filtered(File file, List<FileData> filter) {
            super(file);
            this.filter = filter;
        }

        @Override
        public void prepare(ProgressMonitor m) throws IOException {
            super.prepare(m);

            files.retainAll(filter);
            format = format();
        }
    }
}


File: src/extension/importer/core/src/main/java/org/geoserver/importer/Importer.java
/* (c) 2014 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.importer;

import java.io.File;
import java.io.IOException;
import java.sql.Connection;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Level;
import java.util.logging.Logger;

import org.geoserver.catalog.Catalog;
import org.geoserver.catalog.CatalogBuilder;
import org.geoserver.catalog.CoverageInfo;
import org.geoserver.catalog.CoverageStoreInfo;
import org.geoserver.catalog.DataStoreInfo;
import org.geoserver.catalog.FeatureTypeInfo;
import org.geoserver.catalog.LayerInfo;
import org.geoserver.catalog.NamespaceInfo;
import org.geoserver.catalog.ProjectionPolicy;
import org.geoserver.catalog.ResourceInfo;
import org.geoserver.catalog.StoreInfo;
import org.geoserver.catalog.StyleInfo;
import org.geoserver.catalog.WorkspaceInfo;
import org.geoserver.config.util.XStreamPersister;
import org.geoserver.config.util.XStreamPersister.CRSConverter;
import org.geoserver.config.util.XStreamPersisterFactory;
import org.geoserver.importer.ImportTask.State;
import org.geoserver.importer.job.Job;
import org.geoserver.importer.job.JobQueue;
import org.geoserver.importer.job.ProgressMonitor;
import org.geoserver.importer.job.Task;
import org.geoserver.importer.mosaic.Mosaic;
import org.geoserver.importer.transform.RasterTransformChain;
import org.geoserver.importer.transform.ReprojectTransform;
import org.geoserver.importer.transform.TransformChain;
import org.geoserver.importer.transform.VectorTransformChain;
import org.geoserver.platform.ContextLoadedEvent;
import org.geoserver.platform.GeoServerExtensions;
import org.geotools.data.DataStore;
import org.geotools.data.DefaultTransaction;
import org.geotools.data.FeatureReader;
import org.geotools.data.FeatureStore;
import org.geotools.data.FeatureWriter;
import org.geotools.data.Transaction;
import org.geotools.data.directory.DirectoryDataStore;
import org.geotools.data.shapefile.ShapefileDataStore;
import org.geotools.feature.simple.SimpleFeatureTypeBuilder;
import org.geotools.geometry.GeneralEnvelope;
import org.geotools.geometry.jts.ReferencedEnvelope;
import org.geotools.jdbc.JDBCDataStore;
import org.geotools.referencing.CRS;
import org.geotools.util.logging.Logging;
import org.opengis.feature.simple.SimpleFeature;
import org.opengis.feature.simple.SimpleFeatureType;
import org.opengis.feature.type.FeatureType;
import org.opengis.filter.Filter;
import org.opengis.referencing.crs.CoordinateReferenceSystem;
import org.springframework.beans.factory.DisposableBean;
import org.springframework.context.ApplicationEvent;
import org.springframework.context.ApplicationListener;

import com.google.common.base.Predicate;
import com.google.common.collect.Iterables;
import com.google.common.collect.Iterators;
import com.thoughtworks.xstream.XStream;
import com.vividsolutions.jts.geom.Geometry;

/**
 * Primary controller/facade of the import subsystem.
 * 
 * @author Justin Deoliveira, OpenGeo
 *
 */
public class Importer implements DisposableBean, ApplicationListener {

    static Logger LOGGER = Logging.getLogger(Importer.class);

    /** catalog */
    Catalog catalog;

    /** import context storage */
    ImportStore contextStore;

    /** style generator */
    StyleGenerator styleGen;

    /** job queue */
    JobQueue jobs = new JobQueue();
    
    ConcurrentHashMap<Long,ImportTask> currentlyProcessing = new ConcurrentHashMap<Long, ImportTask>();

    public Importer(Catalog catalog) {
        this.catalog = catalog;
        this.styleGen = new StyleGenerator(catalog);
    }

    /**
     * Returns the style generator.
     */
    public StyleGenerator getStyleGenerator() {
        return styleGen;
    }

    ImportStore createContextStore() {
        // check the spring context for an import store
        ImportStore store = null;

        String name = GeoServerExtensions.getProperty("org.geoserver.importer.store");
        if (name == null) {
            //backward compatability check
            name = GeoServerExtensions.getProperty("org.opengeo.importer.store");
        }

        if (name != null) {
            for (ImportStore bean : GeoServerExtensions.extensions(ImportStore.class)) {
                if (name.equals(bean.getName())) {
                    store = bean;
                    break;
                }
            }

            if (store == null) {
                LOGGER.warning("Invalid value for import store, no such store " + name);
            }
        }

        if (store == null) {
            store = new MemoryImportStore();
        }

        LOGGER.info("Enabling import store: " + store.getName());
        return store;
    }

    public ImportStore getStore() {
        return contextStore;
    }

    public ImportTask getCurrentlyProcessingTask(long contextId) {
        return currentlyProcessing.get(new Long(contextId));
    }

    @Override
    public void onApplicationEvent(ApplicationEvent event) {
        // load the context store here to avoid circular dependency on creation of the importer
        if (event instanceof ContextLoadedEvent) {
            contextStore = createContextStore();
            contextStore.init();
        }
    }

    public Catalog getCatalog() {
        return catalog;
    }

    public ImportContext getContext(long id) {
        ImportContext context = contextStore.get(id);
        return context != null ? reattach(context) : null;
    }

    public ImportContext reattach(ImportContext context) {
        //reload store and workspace objects from catalog so they are "attached" with 
        // the proper references to the catalog initialized
        context.reattach(catalog);
        for (ImportTask task : context.getTasks()) {
            StoreInfo store = task.getStore();
            if (store != null && store.getId() != null) {
                task.setStore(catalog.getStore(store.getId(), StoreInfo.class));
                //((StoreInfoImpl) task.getStore()).setCatalog(catalog); // @todo remove if the above sets catalog
            }
            if (task.getLayer() != null) {
                LayerInfo l = task.getLayer();
                if (l.getDefaultStyle() != null && l.getDefaultStyle().getId() != null) {
                    l.setDefaultStyle(catalog.getStyle(l.getDefaultStyle().getId()));
                }
                if (l.getResource() != null) {
                    ResourceInfo r = l.getResource();
                    r.setCatalog(catalog);

                    if (r.getStore() == null && resourceMatchesStore(r, store)) {
                        r.setStore(store);
                    }

                }
            }

        }
        return context;
    }


    public Iterator<ImportContext> getContexts() {
        return contextStore.allNonCompleteImports();
    }

    public Iterator<ImportContext> getContextsByUser(String user) {
        return contextStore.importsByUser(user);
    }
    
    public Iterator<ImportContext> getAllContexts() {
        return contextStore.iterator();
    }
    
    public Iterator<ImportContext> getAllContextsByUpdated() {
        try {
            return contextStore.iterator("updated");
        }
        catch(UnsupportedOperationException e) {
            //fallback
            TreeSet sorted = new TreeSet<ImportContext>(new Comparator<ImportContext>() {
                @Override
                public int compare(ImportContext o1, ImportContext o2) {
                    Date d1 = o1.getUpdated();
                    Date d2 = o2.getUpdated();
                    return -1 * d1.compareTo(d2);
                }
            });
            Iterators.addAll(sorted, contextStore.iterator());
            return sorted.iterator();
        }
    }

    public ImportContext createContext(ImportData data, WorkspaceInfo targetWorkspace) throws IOException {
        return createContext(data, targetWorkspace, null);
    }

    public ImportContext createContext(ImportData data, StoreInfo targetStore) throws IOException {
        return createContext(data, null, targetStore); 
    }

    public ImportContext createContext(ImportData data) throws IOException {
        return createContext(data, null, null); 
    }
    
    /**
     * Create a context with the provided optional id.
     * The provided id must be higher than the current mark.
     * @param id optional id to use
     * @return Created ImportContext
     * @throws IOException
     * @throws IllegalArgumentException if the provided id is invalid
     */
    public ImportContext createContext(Long id) throws IOException, IllegalArgumentException {
        ImportContext context = new ImportContext();
        if (id != null) {
            Long retval = contextStore.advanceId(id);
            assert retval >= id;
            context.setId(retval);
            contextStore.save(context);
        } else {
            contextStore.add(context);
        }
        return context;
    }
    
    public ImportContext createContext(ImportData data, WorkspaceInfo targetWorkspace, 
        StoreInfo targetStore) throws IOException {
        return createContext(data, targetWorkspace, targetStore, null);
    }

    public ImportContext createContext(ImportData data, WorkspaceInfo targetWorkspace, 
            StoreInfo targetStore, ProgressMonitor monitor) throws IOException {

        ImportContext context = new ImportContext();
        context.setProgress(monitor);
        context.setData(data);

        if (targetWorkspace == null && targetStore != null) {
            targetWorkspace = targetStore.getWorkspace();
        }
        if (targetWorkspace == null) {
            targetWorkspace = catalog.getDefaultWorkspace();
        }
        context.setTargetWorkspace(targetWorkspace);
        context.setTargetStore(targetStore);

        init(context);
        if (!context.progress().isCanceled()) {
            contextStore.add(context);
        }
        //JD: don't think we really need to maintain these, and they aren't persisted
        //else {
        //    context.setState(ImportContext.State.CANCELLED);
        //}
        return context;
    }

    public Long createContextAsync(final ImportData data, final WorkspaceInfo targetWorkspace, 
        final StoreInfo targetStore) throws IOException {
        return jobs.submit(new Job<ImportContext>() {
            @Override
            protected ImportContext call(ProgressMonitor monitor) throws Exception {
                return createContext(data, targetWorkspace, targetStore, monitor);
            }

            @Override
            public String toString() {
                return "Processing data " + data.toString();
            }
        });
    }

    public void init(ImportContext context) throws IOException {
        init(context, true);
    }
    
    public void init(ImportContext context, boolean prepData) throws IOException {
        context.reattach(catalog);

        ImportData data = context.getData();
        if (data != null) {
            addTasks(context, data, prepData); 
        }
    }

    public List<ImportTask> update(ImportContext context, ImportData data) throws IOException {
        List<ImportTask> tasks = addTasks(context, data, true);
        
        //prep(context);
        changed(context);

        return tasks;
    }

    List<ImportTask> addTasks(ImportContext context, ImportData data, boolean prepData) throws IOException {
        if (data == null) {
            return Collections.emptyList();
        }

        if (prepData) {
            data.prepare(context.progress());
        }

        if (data instanceof FileData) {
            if (data instanceof Mosaic) {
                return initForMosaic(context, (Mosaic)data);
            }
            else if (data instanceof Directory) {
                return initForDirectory(context, (Directory)data);
            }
            else {
                return initForFile(context, (FileData)data);
            }
        }
        else if (data instanceof Table) {
        }
        else if (data instanceof Database) {
            return initForDatabase(context, (Database)data);
        }

        throw new IllegalStateException();
        /*for (ImportTask t : tasks) {
            context.addTask(t);
        }
        prep(context, prepData);
        return tasks;*/
    }

    /**
     * Initializes the import for a mosaic.
     * <p>
     * Mosaics only support direct import (context.targetStore must be null) and 
     * </p>
     */
    List<ImportTask> initForMosaic(ImportContext context, Mosaic mosaic) throws IOException {

        if (context.getTargetStore() != null) {
            throw new IllegalArgumentException("ingest not supported for mosaics");
        }

        return createTasks(mosaic, context);
        //tasks.add(createTask(mosaic, context, context.getTargetStore()));
    }

    List<ImportTask> initForDirectory(ImportContext context, Directory data) throws IOException {
        List<ImportTask> tasks = new ArrayList<ImportTask>();

        //flatten out the directory into itself and all sub directories and process in order
        for (Directory dir : data.flatten()) {
            //ignore empty directories
            if (dir.getFiles().isEmpty()) continue;

            //group the contents of the directory by format
            Map<DataFormat,List<FileData>> map = new HashMap<DataFormat,List<FileData>>();
            for (FileData f : dir.getFiles()) {
                DataFormat format = f.getFormat();
                List<FileData> files = map.get(format);
                if (files == null) {
                    files = new ArrayList<FileData>();
                    map.put(format, files);
                }
                files.add(f);
            }
    
            //handle case of importing a single file that we don't know the format of, in this
            // case rather than ignore it we wnat to rpocess it and ssets its state to "NO_FORMAT"
            boolean skipNoFormat = !(map.size() == 1 && map.containsKey(null));
            
            // if no target store specified group the directory into pieces that can be 
            // processed as a single task
            StoreInfo targetStore = context.getTargetStore();
            if (targetStore == null) {
    
                //create a task for each "format" if that format can handle a directory
                for (DataFormat format: new ArrayList<DataFormat>(map.keySet())) {
                    if (format != null && format.canRead(dir)) {
                        List<FileData> files = map.get(format);
                        if (files.size() == 1) {
                            //use the file directly
                            //createTasks(files.get(0), format, context, null));
                            tasks.addAll(createTasks(files.get(0), format, context));
                        }
                        else {
                            tasks.addAll(createTasks(dir.filter(files), format, context));
                            //tasks.addAll(createTasks(dir.filter(files), format, context, null));
                        }
                        
                        map.remove(format);
                    }
                }
    
                //handle the left overs, each file gets its own task
                for (List<FileData> files : map.values()) {
                    for (FileData file : files) {
                        //tasks.add(createTask(file, context, null));
                        tasks.addAll(createTasks(file, file.getFormat(), context, skipNoFormat));
                    }
                }

            }
            else {
                for (FileData file : dir.getFiles()) {
                    tasks.addAll(createTasks(file, file.getFormat(), context, skipNoFormat));
                }
            }
        }

        return tasks;
    }

    List<ImportTask>  initForFile(ImportContext context, FileData file) throws IOException {
        return createTasks(file, context);
    }

    List<ImportTask>  initForDatabase(ImportContext context, Database db) throws IOException {
        //JD: we use check for direct vs non-direct in order to determine if there should be 
        // one task with many items, or one task per table... can;t think of the use case for
        //many tasks

        //tasks.add(createTask(db, context, targetStore));
        return createTasks(db, context);
    }
    
    List<ImportTask> createTasks(ImportData data, ImportContext context) throws IOException {
        return createTasks(data, data.getFormat(), context);
    }
    

    List<ImportTask> createTasks(ImportData data, DataFormat format, ImportContext context) 
        throws IOException {
        return createTasks(data, format, context, true);
    }

    List<ImportTask> createTasks(ImportData data, DataFormat format, ImportContext context, 
        boolean skipNoFormat) throws IOException {

        List<ImportTask> tasks = new ArrayList<ImportTask>();

        boolean direct = false;

        StoreInfo targetStore = context.getTargetStore();
        if (targetStore == null) {
            //direct import, use the format to create a store
            direct = true;

            if (format != null) {
                targetStore = format.createStore(data, context.getTargetWorkspace(), catalog);    
            }
            
            if (targetStore == null) {
                //format unable to create store, switch to indirect import and use 
                // default store from catalog
                targetStore = lookupDefaultStore();

                direct = targetStore == null;
            }
        }

        if (format != null) {
            // create the set of tasks by having the format list the avialable items
            // from the input data
            for (ImportTask t : format.list(data, catalog, context.progress())) {
                //initialize transform chain based on vector vs raster
                t.setTransform(format instanceof VectorFormat 
                        ? new VectorTransformChain() : new RasterTransformChain());
                t.setDirect(direct);
                t.setStore(targetStore);

                prep(t);
                tasks.add(t);
            }
        }
        else if (!skipNoFormat) {
            ImportTask t = new ImportTask(data);
            t.setDirect(direct);
            t.setStore(targetStore);
            prep(t);
            tasks.add(t);
        }

        for (ImportTask t : tasks) {
            context.addTask(t);
        }
        return tasks;
    }

    boolean prep(ImportTask task) {
        if (task.getState() == ImportTask.State.COMPLETE) {
            return true;
        }

        //check the format
        DataFormat format = task.getData().getFormat();
        if (format == null) {
            task.setState(State.NO_FORMAT);
            return false;
        }

        
        //check the target
        if (task.getStore() == null) {
            task.setError(new Exception("No target store for task"));
            task.setState(State.ERROR);
            return false;
        }

        //check for a mismatch between store and format
        if (!formatMatchesStore(format, task.getStore())) {
            String msg = task.getStore() instanceof DataStoreInfo ? 
                    "Unable to import raster data into vector store" : 
                    "Unable to import vector data into raster store";

            task.setError(new Exception(msg));
            task.setState(State.BAD_FORMAT);
            return false;
        }

        if (task.getLayer() == null || task.getLayer().getResource() == null) {
            task.setError(new Exception("Task has no layer configuration"));
            task.setState(State.ERROR);
            return false;
        }

        LayerInfo l = task.getLayer();
        ResourceInfo r = l.getResource();
        
        //initialize resource references
        r.setStore(task.getStore());
        r.setNamespace(
            catalog.getNamespaceByPrefix(task.getStore().getWorkspace().getName()));

        //style
        //assign a default style to the layer if not already done
        if (l.getDefaultStyle() == null) {
            try {
                StyleInfo style = null;
                if (r instanceof FeatureTypeInfo) {
                    //since this resource is still detached from the catalog we can't call
                    // through to get it's underlying resource, so we depend on the "native"
                    // type provided from the format
                    FeatureType featureType =
                        (FeatureType) task.getMetadata().get(FeatureType.class);
                    if (featureType != null) {
                        style = styleGen.createStyle((FeatureTypeInfo) r, featureType);
                    } else {
                        throw new RuntimeException("Unable to compute style");
                    }

                }
                else if (r instanceof CoverageInfo) {
                    style = styleGen.createStyle((CoverageInfo) r);
                }
                else {
                    throw new RuntimeException("Unknown resource type :"
                            + r.getClass());
                }
                l.setDefaultStyle(style);
            }
            catch(Exception e) {
                task.setError(e);
                task.setState(ImportTask.State.ERROR);
                return false;
            }
        }
        
        //srs
        if (r.getSRS() == null) {
            task.setState(ImportTask.State.NO_CRS);
            return false;
        }
        else if (task.getState() == ImportTask.State.NO_CRS) {
            //changed after setting srs manually, compute the lat long bounding box
            try {
                computeLatLonBoundingBox(task, false);
            }
            catch(Exception e) {
                LOGGER.log(Level.WARNING, "Error computing lat long bounding box", e);
                task.setState(ImportTask.State.ERROR);
                task.setError(e);
                return false;
            }

            //also since this resource has no native crs set the project policy to force declared
            task.getLayer().getResource().setProjectionPolicy(ProjectionPolicy.FORCE_DECLARED);
        }
        else {
            task.getLayer().getResource().setProjectionPolicy(ProjectionPolicy.NONE);
        }

        //bounds
        if (r.getNativeBoundingBox() == null) {
            task.setState(ImportTask.State.NO_BOUNDS);
            return false;
        }
        
        task.setState(ImportTask.State.READY);
        return true;
    }

    boolean formatMatchesStore(DataFormat format, StoreInfo store) {
        if (format instanceof VectorFormat) {
            return store instanceof DataStoreInfo;
        }
        if (format instanceof GridFormat) {
            return store instanceof CoverageStoreInfo;
        }
        return false;
    }

    boolean resourceMatchesStore(ResourceInfo resource, StoreInfo store) {
        if (resource instanceof FeatureTypeInfo) {
            return store instanceof DataStoreInfo;
        }
        if (resource instanceof CoverageInfo) {
            return store instanceof CoverageStoreInfo;
        }
        return false;
    }

    public void run(ImportContext context) throws IOException {
        run(context, ImportFilter.ALL);
    }

    public void run(ImportContext context, ImportFilter filter) throws IOException {
        run(context, filter, null);
    }
    
    public void run(ImportContext context, ImportFilter filter, ProgressMonitor monitor) throws IOException {
        context.setProgress(monitor);
        context.setState(ImportContext.State.RUNNING);
        
        if (LOGGER.isLoggable(Level.FINE)) {
            LOGGER.fine("Running import " + context.getId());
        }
        
        for (ImportTask task : context.getTasks()) {
            if (!filter.include(task)) {
                continue;
            }
            if (!task.readyForImport()) {
                continue;
            }

            if (context.progress().isCanceled()) {
                break;
            }
            run(task);
        }

        context.updated();
        contextStore.save(context);

        if (context.isArchive() && context.getState() == ImportContext.State.COMPLETE) {
            boolean canArchive = !Iterables.any(context.getTasks(), new Predicate<ImportTask>() {
                @Override
                public boolean apply(ImportTask input) {
                    return input.isDirect();
                }
            });

            if (canArchive) {
                Directory directory = null;
                if (context.getData() instanceof Directory) {
                    directory = (Directory) context.getData();
                } else if ( context.getData() instanceof SpatialFile ) {
                    directory = new Directory( ((SpatialFile) context.getData()).getFile().getParentFile() );
                }
                if (directory != null) {
                    if (LOGGER.isLoggable(Level.FINE)) {
                        LOGGER.fine("Archiving directory " + directory.getFile().getAbsolutePath());
                    }       
                    try {
                        directory.archive(getArchiveFile(context));
                    } catch (Exception ioe) {
                        ioe.printStackTrace();
                        // this is not a critical operation, so don't make the whole thing fail
                        LOGGER.log(Level.WARNING, "Error archiving", ioe);
                    }
                }
            }

        }
    }

    void run(ImportTask task) throws IOException {
        if (task.getState() == ImportTask.State.COMPLETE) {
            return;
        }
        task.setState(ImportTask.State.RUNNING);

        if (task.isDirect()) {
            //direct import, simply add configured store and layers to catalog
            doDirectImport(task);
        }
        else {
            //indirect import, read data from the source and into the target datastore 
            doIndirectImport(task);
        }

    }
    
    public File getArchiveFile(ImportContext context) throws IOException {
        //String archiveName = "import-" + task.getContext().getId() + "-" + task.getId() + "-" + task.getData().getName() + ".zip";
        String archiveName = "import-" + context.getId() + ".zip";
        File dir = getCatalog().getResourceLoader().findOrCreateDirectory("uploads","archives");
        return new File(dir, archiveName);
    }
    
    public void changed(ImportContext context) {
        context.updated();
        contextStore.save(context);
    }

    public void changed(ImportTask task)  {
        prep(task);
        changed(task.getContext());
    }

    public Long runAsync(final ImportContext context, final ImportFilter filter) {
        return jobs.submit(new Job<ImportContext>() {
            @Override
            protected ImportContext call(ProgressMonitor monitor) throws Exception {
                run(context, filter, monitor);
                return context;
            }

            @Override
            public String toString() {
                return "Processing import " + context.getId();
            }
        });
    }

    public Task<ImportContext> getTask(Long job) {
        return (Task<ImportContext>) jobs.getTask(job);
    }

    public List<Task<ImportContext>> getTasks() {
        return (List) jobs.getTasks();
    }

    /* 
     * an import that involves consuming a data source directly
     */
    void doDirectImport(ImportTask task) throws IOException {
        //TODO: this needs to be transactional in case of errors along the way

        //add the store, may have been added in a previous iteration of this task
        if (task.getStore().getId() == null) {
            StoreInfo store = task.getStore();

            //ensure a unique name
            store.setName(findUniqueStoreName(task.getStore()));
            
            //ensure a namespace connection parameter set matching workspace/namespace
            if (!store.getConnectionParameters().containsKey("namespace")) {
                WorkspaceInfo ws = task.getContext().getTargetWorkspace();
                if (ws == null && task.getContext().getTargetStore() != null) {
                    ws = task.getContext().getTargetStore().getWorkspace();
                }
                if (ws != null) {
                    NamespaceInfo ns = catalog.getNamespaceByPrefix(ws.getName());
                    if (ns != null) {
                        store.getConnectionParameters().put("namespace", ns.getURI());
                    }
                }
            }
            catalog.add(task.getStore());
        }

        task.setState(ImportTask.State.RUNNING);

        try {
            //set up transform chain
            TransformChain tx = task.getTransform();
            
            //apply pre transform
            if (!doPreTransform(task, task.getData(), tx)) {
                return;
            }

            addToCatalog(task);

            //apply pre transform
            if (!doPostTransform(task, task.getData(), tx)) {
                return;
            }

            task.setState(ImportTask.State.COMPLETE);
        }
        catch(Exception e) {
            LOGGER.log(Level.WARNING, "Task failed during import: " + task, e);
            task.setState(ImportTask.State.ERROR);
            task.setError(e);
        }

    }

    /* 
     * an import that involves reading from the datastore and writing into a specified target store
     */
    void doIndirectImport(ImportTask task) throws IOException {
        if (!task.getStore().isEnabled()) {
            task.getStore().setEnabled(true);
        }

        if (task.progress().isCanceled()){
            return;
        }

        task.setState(ImportTask.State.RUNNING);

        //setup transform chain
        TransformChain tx = task.getTransform();

        //pre transform
        if (!doPreTransform(task, task.getData(), tx)) {
            return;
        }

        boolean canceled = false;
        DataFormat format = task.getData().getFormat();
        if (format instanceof VectorFormat) {
            try {
                currentlyProcessing.put(task.getContext().getId(), task);
                loadIntoDataStore(task, (DataStoreInfo)task.getStore(), (VectorFormat) format, 
                    (VectorTransformChain) tx);
                canceled = task.progress().isCanceled();

                FeatureTypeInfo featureType = (FeatureTypeInfo) task.getLayer().getResource();
                featureType.getAttributes().clear();

                if (!canceled) {
                    if (task.getUpdateMode() == UpdateMode.CREATE) {
                        addToCatalog(task);
                    }
    
                    // verify that the newly created featuretype's resource
                    // has bounding boxes computed - this might be required
                    // for csv or other uploads that have a geometry that is
                    // the result of a transform. there may be another way...
                    FeatureTypeInfo resource = getCatalog().getResourceByName(
                            featureType.getQualifiedName(), FeatureTypeInfo.class);
                    if (resource.getNativeBoundingBox().isEmpty()
                            || resource.getMetadata().get("recalculate-bounds") != null) {
                        // force computation
                        CatalogBuilder cb = new CatalogBuilder(getCatalog());
                        ReferencedEnvelope nativeBounds = cb.getNativeBounds(resource);
                        resource.setNativeBoundingBox(nativeBounds);
                        resource.setLatLonBoundingBox(cb.getLatLonBounds(nativeBounds,
                                resource.getCRS()));
                        getCatalog().save(resource);
                    }
                }
            }
            catch(Exception e) {
                LOGGER.log(Level.SEVERE, "Error occured during import", e);
                task.setError(e);
                task.setState(ImportTask.State.ERROR);
                return;
            } finally {
                currentlyProcessing.remove(task.getContext().getId());
            }
        }
        else {
            throw new UnsupportedOperationException("Indirect raster import not yet supported");
        }

        if (!canceled && !doPostTransform(task, task.getData(), tx)) {
            return;
        }

        task.setState(canceled ? ImportTask.State.CANCELED : ImportTask.State.COMPLETE);

    }

    boolean doPreTransform(ImportTask task, ImportData data, TransformChain tx) {
        try {
            tx.pre(task, data);
        } 
        catch (Exception e) {
            LOGGER.log(Level.SEVERE, "Error occured during pre transform", e);
            task.setError(e);
            task.setState(ImportTask.State.ERROR);
            return false;
        }
        return true;
    }

    boolean doPostTransform(ImportTask task, ImportData data, TransformChain tx) {
        try {
            tx.post(task, data);
        } 
        catch (Exception e) {
            LOGGER.log(Level.SEVERE, "Error occured during post transform", e);
            task.setError(e);
            task.setState(ImportTask.State.ERROR);
            return false;
        }
        return true;
    }

    void loadIntoDataStore(ImportTask task, DataStoreInfo store, VectorFormat format, 
        VectorTransformChain tx) throws Exception {

        ImportData data = task.getData();
        FeatureReader reader = null;
        FeatureWriter writer = null;
        // using this exception to throw at the end
        Exception error = null;
        try {
            reader = format.read(data, task);

            SimpleFeatureType featureType = (SimpleFeatureType) reader.getFeatureType();
            final String featureTypeName = featureType.getName().getLocalPart();
    
            DataStore dataStore = (DataStore) store.getDataStore(null);
            FeatureDataConverter featureDataConverter = FeatureDataConverter.DEFAULT;
            if (isShapefileDataStore(dataStore)) {
                featureDataConverter = FeatureDataConverter.TO_SHAPEFILE;
            }
            else if (isOracleDataStore(dataStore)) {
                featureDataConverter = FeatureDataConverter.TO_ORACLE;
            }
            else if (isPostGISDataStore(dataStore)) {
                featureDataConverter = FeatureDataConverter.TO_POSTGIS;
            }
            
            featureType = featureDataConverter.convertType(featureType, format, data, task);
            UpdateMode updateMode = task.getUpdateMode();
            final String uniquifiedFeatureTypeName;
            if (updateMode == UpdateMode.CREATE) {
                //find a unique type name in the target store
                uniquifiedFeatureTypeName = findUniqueNativeFeatureTypeName(featureType, store);
                task.setOriginalLayerName(featureTypeName);
    
                if (!uniquifiedFeatureTypeName.equals(featureTypeName)) {
                    //update the metadata
                    task.getLayer().getResource().setName(uniquifiedFeatureTypeName);
                    task.getLayer().getResource().setNativeName(uniquifiedFeatureTypeName);
                    
                    //retype
                    SimpleFeatureTypeBuilder typeBuilder = new SimpleFeatureTypeBuilder();
                    typeBuilder.setName(uniquifiedFeatureTypeName);
                    typeBuilder.addAll(featureType.getAttributeDescriptors());
                    featureType = typeBuilder.buildFeatureType();
                }
    
                // @todo HACK remove this at some point when timezone issues are fixed
                // this will force postgis to create timezone w/ timestamp fields
                if (dataStore instanceof JDBCDataStore) {
                    JDBCDataStore ds = (JDBCDataStore) dataStore;
                    // sniff for postgis (h2 is used in tests and will cause failure if this occurs)
                    if (ds.getSqlTypeNameToClassMappings().containsKey("timestamptz")) {
                        ds.getSqlTypeToSqlTypeNameOverrides().put(java.sql.Types.TIMESTAMP, "timestamptz");
                    }
                }
    
                //apply the feature type transform
                featureType = tx.inline(task, dataStore, featureType);
    
                dataStore.createSchema(featureType);
            } else {
                // @todo what to do if featureType transform is present?
                
                // @todo implement me - need to specify attribute used for id
                if (updateMode == UpdateMode.UPDATE) {
                    throw new UnsupportedOperationException("updateMode UPDATE is not supported yet");
                }
                uniquifiedFeatureTypeName = featureTypeName;
            }
                
            Transaction transaction = new DefaultTransaction();
            
            if (updateMode == UpdateMode.REPLACE) {
                
                FeatureStore fs = (FeatureStore) dataStore.getFeatureSource(featureTypeName);
                fs.setTransaction(transaction);
                fs.removeFeatures(Filter.INCLUDE);
            }
            
            //start writing features
            // @todo ability to collect transformation errors for use in a dry-run (auto-rollback)
            
            ProgressMonitor monitor = task.progress();
            
            // @todo need better way to communicate to client
            int skipped = 0;
            int cnt = 0;
            // metrics
            long startTime = System.currentTimeMillis();
            task.clearMessages();
            
            task.setTotalToProcess(format.getFeatureCount(task.getData(), task));
            
            LOGGER.info("begining import");
            try {
                writer = dataStore.getFeatureWriterAppend(uniquifiedFeatureTypeName, transaction);
                
                while(reader.hasNext()) {
                    if (monitor.isCanceled()){
                        break;
                    }
                    SimpleFeature feature = (SimpleFeature) reader.next();
                    SimpleFeature next = (SimpleFeature) writer.next();
    
                    //(JD) TODO: some formats will rearrange the geometry type (like shapefile) which
                    // makes the goemetry the first attribute reagardless, so blindly copying over
                    // attributes won't work unless the source type also  has the geometry as the 
                    // first attribute in the schema
                    featureDataConverter.convert(feature, next);
                    
                    // @hack #45678 - mask empty geometry or postgis will complain
                    Geometry geom = (Geometry) next.getDefaultGeometry();
                    if (geom != null && geom.isEmpty()) {
                        next.setDefaultGeometry(null);
                    }
                    
                    //apply the feature transform
                    next = tx.inline(task, dataStore, feature, next);
                    
                    if (next == null) {
                        skipped++;
                    } else {
                        writer.write();
                    }
                    task.setNumberProcessed(++cnt);
                }
                transaction.commit();
                if (skipped > 0) {
                    task.addMessage(Level.WARNING,skipped + " features were skipped.");
                }
                LOGGER.info("load to target took " + (System.currentTimeMillis() - startTime));
            } 
            catch (Exception e) {
                error = e;
            } 
            // no finally block, there is too much to do
            
            if (error != null || monitor.isCanceled()) {
                // all sub exceptions in this catch block should be logged, not thrown
                // as the triggering exception will be thrown
    
                //failure, rollback transaction
                try {
                    transaction.rollback();
                } catch (Exception e1) {
                    LOGGER.log(Level.WARNING, "Error rolling back transaction",e1);
                }
    
                //attempt to drop the type that was created as well
                try {
                    dropSchema(dataStore,featureTypeName);
                } catch(Exception e1) {
                    LOGGER.log(Level.WARNING, "Error dropping schema in rollback",e1);
                }
            }
    
            // try to cleanup, but if an error occurs here and one hasn't already been set, set the error
            try {
                transaction.close();
            } catch (Exception e) {
                if (error != null) {
                    error = e;
                }
                LOGGER.log(Level.WARNING, "Error closing transaction",e);
            }
    
            // @revisit - when this gets disposed, any following uses seem to
            // have a problem where later users of the dataStore get an NPE 
            // since the dataStore gets cached by the ResourcePool but is in a 
            // closed state???
            
            // do this last in case we have to drop the schema
    //        try {
    //            dataStore.dispose();
    //        } catch (Exception e) {
    //            LOGGER.log(Level.WARNING, "Error closing dataStore",e);
    //        }
        } finally {
            if (writer != null) {
                try {
                    writer.close();
                } catch (Exception e) {
                    if (error != null) {
                        error = e;
                    }
                    LOGGER.log(Level.WARNING, "Error closing writer",e);
                }
            }
            try {    
                if(reader != null) {
                    format.dispose(reader, task);
                    // @hack catch _all_ Exceptions here - occassionally closing a shapefile
                    // seems to result in an IllegalArgumentException related to not
                    // holding the lock...
                }
            } catch (Exception e) {
                LOGGER.log(Level.WARNING, "Error closing reader",e);
            }
        }
        
        // finally, throw any error
        if (error != null) {
            throw error;
        }
    }

    StoreInfo lookupDefaultStore() {
        WorkspaceInfo ws = catalog.getDefaultWorkspace();
        if (ws == null) {
            return null;
        }

        return catalog.getDefaultDataStore(ws);
    }

    void addToCatalog(ImportTask task) throws IOException {
        LayerInfo layer = task.getLayer();
        ResourceInfo resource = layer.getResource();
        resource.setStore(task.getStore());

        //add the resource
        String name = findUniqueResourceName(resource);
        resource.setName(name); 

        //JD: not setting a native name, it should actually already be set by this point and we 
        // don't want to blindly set it to the same name as the resource name, which might have 
        // changed to deal with name clashes
        //resource.setNativeName(name);
        resource.setEnabled(true);
        catalog.add(resource);

        //add the layer (and style)
        if (layer.getDefaultStyle().getId() == null) {
            catalog.add(layer.getDefaultStyle());
        }

        layer.setEnabled(true);
        catalog.add(layer);
    }

    String findUniqueStoreName(StoreInfo store) {
        WorkspaceInfo workspace = store.getWorkspace();

        //TODO: put an upper limit on how many times to try
        String name = store.getName();
        if (catalog.getStoreByName(workspace, store.getName(), StoreInfo.class) != null) {
            int i = 0;
            name += i;
            while (catalog.getStoreByName(workspace, name, StoreInfo.class) != null) {
                name = name.replaceAll(i + "$", String.valueOf(i+1));
                i++;
            }
        }

        return name;
    }
    
    String findUniqueResourceName(ResourceInfo resource) 
        throws IOException {

        //TODO: put an upper limit on how many times to try
        StoreInfo store = resource.getStore();
        NamespaceInfo ns = catalog.getNamespaceByPrefix(store.getWorkspace().getName());
        
        String name = resource.getName();

        // make sure the name conforms to a legal layer name
        if (!Character.isLetter(name.charAt(0))) {
            name = "a_" + name;
        }

        // strip out any non-word characters
        name = name.replaceAll("\\W", "_");

        if (catalog.getResourceByName(ns, name, ResourceInfo.class) != null) {
            int i = 0;
            name += i;
            while (catalog.getResourceByName(ns, name, ResourceInfo.class) != null) {
                name = name.replaceAll(i + "$", String.valueOf(i+1));
                i++;
            }
        }

        return name;
    }

    String findUniqueNativeFeatureTypeName(FeatureType featureType, DataStoreInfo store) throws IOException {
        return findUniqueNativeFeatureTypeName(featureType.getName().getLocalPart(), store);
    }

    private String findUniqueNativeFeatureTypeName(String name, DataStoreInfo store) throws IOException {
        DataStore dataStore = (DataStore) store.getDataStore(null);

        //hack for oracle, all names must be upper case
        //TODO: abstract this into FeatureConverter
        if (isOracleDataStore(dataStore)) {
            name = name.toUpperCase();
        }

        //TODO: put an upper limit on how many times to try
        List<String> names = Arrays.asList(dataStore.getTypeNames());
        if (names.contains(name)) {
            int i = 0;
            name += i;
            while(names.contains(name)) {
                name = name.replaceAll(i + "$", String.valueOf(i+1));
                i++;
            }
        }

        return name;
    }

    boolean isShapefileDataStore(DataStore dataStore) {
        return dataStore instanceof ShapefileDataStore || dataStore instanceof DirectoryDataStore;
    }

    boolean isOracleDataStore(DataStore dataStore) {
        return dataStore instanceof JDBCDataStore && "org.geotools.data.oracle.OracleDialect"
            .equals(((JDBCDataStore)dataStore).getSQLDialect().getClass().getName());
    }

    boolean isPostGISDataStore(DataStore dataStore) {
        return dataStore instanceof JDBCDataStore && ((JDBCDataStore)dataStore).getSQLDialect()
            .getClass().getName().startsWith("org.geotools.data.postgis");
    }

    /*
     * computes the lat/lon bounding box from the native bounding box and srs, optionally overriding
     * the value already set.
     */
    boolean computeLatLonBoundingBox(ImportTask task, boolean force) throws Exception {
        ResourceInfo r = task.getLayer().getResource();
        if (force || r.getLatLonBoundingBox() == null && r.getNativeBoundingBox() != null) {
            CoordinateReferenceSystem nativeCRS = CRS.decode(r.getSRS());
            ReferencedEnvelope nativeBbox = 
                new ReferencedEnvelope(r.getNativeBoundingBox(), nativeCRS);
            r.setLatLonBoundingBox(nativeBbox.transform(CRS.decode("EPSG:4326"), true));
            return true;
        }
        return false;
    }

    //file location methods
    public File getImportRoot() {
        try {
            return catalog.getResourceLoader().findOrCreateDirectory("imports");
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    public File getUploadRoot() {
        try {
            return catalog.getResourceLoader().findOrCreateDirectory("uploads");
        }
        catch(IOException e) {
            throw new RuntimeException(e);
        }
    }

    public void destroy() throws Exception {
        jobs.shutdown();
        contextStore.destroy();
    }

    public void delete(ImportContext importContext) throws IOException {
        delete(importContext, false);
    }
    
    public void delete(ImportContext importContext, boolean purge) throws IOException {
        if (purge) {
            importContext.delete();    
        }
        
        contextStore.remove(importContext);
    }

    private void dropSchema(DataStore ds, String featureTypeName) throws Exception {
        // @todo this needs implementation in geotools
        SimpleFeatureType schema = ds.getSchema(featureTypeName);
        if (schema != null) {
            try {
                ds.removeSchema(featureTypeName);
            } catch(Exception e) {
                LOGGER.warning("Unable to dropSchema " + featureTypeName + " from datastore " + ds.getClass());
            }
        } else {
            LOGGER.warning("Unable to dropSchema " + featureTypeName + " as it does not appear to exist in dataStore");
        }
    }

    public XStreamPersister createXStreamPersisterXML() {
        return initXStreamPersister(new XStreamPersisterFactory().createXMLPersister());
    }

    public XStreamPersister createXStreamPersisterJSON() {
        return initXStreamPersister(new XStreamPersisterFactory().createJSONPersister());
    }

    public XStreamPersister initXStreamPersister(XStreamPersister xp) {
        xp.setCatalog(catalog);
        //xp.setReferenceByName(true);
        
        XStream xs = xp.getXStream();

        //ImportContext
        xs.alias("import", ImportContext.class);

        //ImportTask
        xs.alias("task", ImportTask.class);
        xs.omitField(ImportTask.class, "context");

        //ImportItem
        //xs.alias("item", ImportItem.class);
        //xs.omitField(ImportItem.class, "task");

        //DataFormat
        xs.alias("dataStoreFormat", DataStoreFormat.class);

        //ImportData
        xs.alias("spatialFile", SpatialFile.class);
        xs.alias("database", org.geoserver.importer.Database.class);
        xs.alias("table", Table.class);
        xs.omitField(Table.class, "db");

        xs.alias("vectorTransformChain", VectorTransformChain.class);
        xs.registerLocalConverter(ReprojectTransform.class, "source", new CRSConverter());
        xs.registerLocalConverter(ReprojectTransform.class, "target", new CRSConverter());

        xs.registerLocalConverter( ReferencedEnvelope.class, "crs", new CRSConverter() );
        xs.registerLocalConverter( GeneralEnvelope.class, "crs", new CRSConverter() );
        
        return xp;
    }

}


File: src/extension/importer/core/src/main/java/org/geoserver/importer/transform/AbstractInlineVectorTransform.java
/* (c) 2014 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.importer.transform;

import org.geotools.data.DataStore;
import org.geoserver.importer.ImportTask;
import org.opengis.feature.simple.SimpleFeature;
import org.opengis.feature.simple.SimpleFeatureType;

/**
 * Convenience base class to make creating inline vector transforms easier
 * 
 */
public abstract class AbstractInlineVectorTransform extends AbstractVectorTransform implements
        InlineVectorTransform {

    /** serialVersionUID */
    private static final long serialVersionUID = 1L;

    @Override
    public SimpleFeatureType apply(ImportTask task, DataStore dataStore,
            SimpleFeatureType featureType) throws Exception {
        return featureType;
    }

    @Override
    public SimpleFeature apply(ImportTask task, DataStore dataStore, SimpleFeature oldFeature,
            SimpleFeature feature) throws Exception {
        return feature;
    }

}


File: src/extension/importer/core/src/main/java/org/geoserver/importer/transform/AttributeRemapTransform.java
/* (c) 2014 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.importer.transform;

import org.geotools.data.DataStore;
import org.geotools.feature.AttributeTypeBuilder;
import org.geotools.feature.simple.SimpleFeatureTypeBuilder;
import org.geoserver.importer.ImportTask;
import org.opengis.feature.simple.SimpleFeature;
import org.opengis.feature.simple.SimpleFeatureType;
import org.opengis.feature.type.AttributeDescriptor;

/**
 * Attribute that maps an attribute from one type to another.
 * 
 * @author Justin Deoliveira, OpenGeo
 */
public class AttributeRemapTransform extends AbstractVectorTransform implements InlineVectorTransform {
    
    private static final long serialVersionUID = 1L;

    /** field to remap */
    protected String field;

    /** type to remap to */
    protected Class type;
    
    public AttributeRemapTransform(String field, Class type) {
        this.field = field;
        this.type = type;
    }
    
    protected AttributeRemapTransform() {
        
    }

    public String getField() {
        return field;
    }

    public void setField(String field) {
        this.field = field;
    }

    public Class getType() {
        return type;
    }

    public void setType(Class type) {
        this.type = type;
    }

    public SimpleFeatureType apply(ImportTask task, DataStore dataStore,
            SimpleFeatureType featureType) throws Exception {
        //remap the type
        SimpleFeatureTypeBuilder builder = new SimpleFeatureTypeBuilder();
        builder.init(featureType);

        int index = featureType.indexOf(field);
        if (index < 0) {
            throw new Exception("FeatureType " + featureType.getName() + " does not have attribute named '" + field + "'");
        }
        
        //remap the attribute to type date and ensure schema ordering is the same
        //@todo improve FeatureTypeBuilder to support this directly
        AttributeDescriptor existing = builder.remove(field);
        AttributeTypeBuilder attBuilder = new AttributeTypeBuilder();
        attBuilder.init(existing);
        attBuilder.setBinding(type);
        builder.add(index, attBuilder.buildDescriptor(field));

        return builder.buildFeatureType();
    }

    public SimpleFeature apply(ImportTask task, DataStore dataStore, SimpleFeature oldFeature, 
        SimpleFeature feature) throws Exception {
        return feature;
    }

}


File: src/extension/importer/core/src/main/java/org/geoserver/importer/transform/AttributesToPointGeometryTransform.java
/* (c) 2014 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.importer.transform;

import org.geotools.data.DataStore;
import org.geotools.feature.simple.SimpleFeatureTypeBuilder;
import org.geoserver.importer.ImportTask;
import org.opengis.feature.simple.SimpleFeature;
import org.opengis.feature.simple.SimpleFeatureType;
import org.opengis.feature.type.GeometryDescriptor;

import com.vividsolutions.jts.geom.Coordinate;
import com.vividsolutions.jts.geom.GeometryFactory;
import com.vividsolutions.jts.geom.Point;

public class AttributesToPointGeometryTransform extends AbstractVectorTransform implements
        InlineVectorTransform {

    /** serialVersionUID */
    private static final long serialVersionUID = 1L;

    private static final String POINT_NAME = "location";

    private final String latField;

    private final String lngField;

    private final String pointFieldName;

    private final GeometryFactory geometryFactory;

    public AttributesToPointGeometryTransform(String latField, String lngField) {
        this(latField, lngField, AttributesToPointGeometryTransform.POINT_NAME);
    }

    public AttributesToPointGeometryTransform(String latField, String lngField,
            String pointFieldName) {
        this.latField = latField;
        this.lngField = lngField;
        this.pointFieldName = pointFieldName;
        geometryFactory = new GeometryFactory();
    }

    @Override
    public SimpleFeatureType apply(ImportTask task, DataStore dataStore,
            SimpleFeatureType featureType) throws Exception {
        SimpleFeatureTypeBuilder builder = new SimpleFeatureTypeBuilder();
        builder.init(featureType);

        int latIndex = featureType.indexOf(latField);
        int lngIndex = featureType.indexOf(lngField);
        if (latIndex < 0 || lngIndex < 0) {
            throw new Exception("FeatureType " + featureType.getName()
                    + " does not have lat lng fields named '" + latField + "'" + " and " + "'"
                    + lngField + "'");
        }

        GeometryDescriptor geometryDescriptor = featureType.getGeometryDescriptor();
        if (geometryDescriptor != null) {
            builder.remove(geometryDescriptor.getLocalName());
        }
        builder.remove(latField);
        builder.remove(lngField);
        builder.add(pointFieldName, Point.class);

        return builder.buildFeatureType();
    }

    @Override
    public SimpleFeature apply(ImportTask task, DataStore dataStore, SimpleFeature oldFeature,
            SimpleFeature feature) throws Exception {
        Object latObject = oldFeature.getAttribute(latField);
        Object lngObject = oldFeature.getAttribute(lngField);
        Double lat = asDouble(latObject);
        Double lng = asDouble(lngObject);
        if (lat == null || lng == null) {
            feature.setDefaultGeometry(null);
        } else {
            Coordinate coordinate = new Coordinate(lng, lat);
            Point point = geometryFactory.createPoint(coordinate);
            feature.setAttribute(pointFieldName, point);
        }
        return feature;
    }

    private Double asDouble(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof Double) {
            return (Double) value;
        }
        try {
            return Double.parseDouble(value.toString());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    public String getLatField() {
        return latField;
    }

    public String getLngField() {
        return lngField;
    }

}


File: src/extension/importer/core/src/main/java/org/geoserver/importer/transform/CreateIndexTransform.java
/* (c) 2014 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.importer.transform;

import java.sql.Connection;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.logging.Level;
import org.geoserver.catalog.DataStoreInfo;
import org.geotools.data.DataAccess;
import org.geotools.data.Transaction;
import org.geotools.jdbc.JDBCDataStore;
import org.geoserver.importer.ImportData;
import org.geoserver.importer.ImportTask;

/**
 *
 * @author Ian Schneider <ischneider@opengeo.org>
 */
public class CreateIndexTransform extends AbstractVectorTransform implements PostVectorTransform {
    
    private static final long serialVersionUID = 1L;
    
    private String field;
    
    public CreateIndexTransform(String field) {
        this.field = field;
    }

    public String getField() {
        return field;
    }

    public void setField(String field) {
        this.field = field;
    }
    
    public void apply(ImportTask task, ImportData data) throws Exception {
        DataStoreInfo storeInfo = (DataStoreInfo) task.getStore();
        DataAccess store = storeInfo.getDataStore(null);
        if (store instanceof JDBCDataStore) {
            createIndex( task, (JDBCDataStore) store);
        } else {
            task.addMessage(Level.WARNING, "Cannot create index on non database target. Not a big deal.");
        }
    }
    
    private void createIndex(ImportTask item, JDBCDataStore store) throws Exception {
        Connection conn = null;
        Statement stmt = null;
        Exception error = null;
        String sql = null;
        try {
            conn = store.getConnection(Transaction.AUTO_COMMIT);
            stmt = conn.createStatement();
            String tableName = item.getLayer().getResource().getNativeName();
            String indexName = "\"" + tableName + "_" + field + "\"";
            sql = "CREATE INDEX " + indexName + " ON \"" + tableName + "\" (\"" + field + "\")";
            stmt.execute(sql);
        } catch (SQLException sqle) {
            error = sqle;
        } finally {
            store.closeSafe(stmt);
            store.closeSafe(conn);
        }
        if (error != null) {
            throw new Exception("Error creating index, SQL was : " + sql,error);
        }
    }
    
}


File: src/extension/importer/core/src/main/java/org/geoserver/importer/transform/KMLPlacemarkTransform.java
/* (c) 2014 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.importer.transform;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;

import org.apache.commons.lang.StringUtils;
import org.geotools.data.DataStore;
import org.geotools.feature.simple.SimpleFeatureBuilder;
import org.geotools.feature.simple.SimpleFeatureTypeBuilder;
import org.geotools.kml.Folder;
import org.geoserver.importer.FeatureDataConverter;
import org.geoserver.importer.ImportTask;
import org.geoserver.importer.format.KMLFileFormat;
import org.opengis.feature.simple.SimpleFeature;
import org.opengis.feature.simple.SimpleFeatureType;
import org.opengis.feature.type.AttributeDescriptor;

import com.vividsolutions.jts.geom.Geometry;

public class KMLPlacemarkTransform extends AbstractVectorTransform implements InlineVectorTransform {

    /** serialVersionUID */
    private static final long serialVersionUID = 1L;

    public SimpleFeatureType convertFeatureType(SimpleFeatureType oldFeatureType) {
        SimpleFeatureTypeBuilder ftb = new SimpleFeatureTypeBuilder();
        ftb.add("Geometry", Geometry.class);
        ftb.setDefaultGeometry("Geometry");
        List<AttributeDescriptor> attributeDescriptors = oldFeatureType.getAttributeDescriptors();
        for (AttributeDescriptor attributeDescriptor : attributeDescriptors) {
            String localName = attributeDescriptor.getLocalName();
            if (!"Geometry".equals(localName)) {
                ftb.add(attributeDescriptor);
            }
        }
        ftb.setName(oldFeatureType.getName());
        ftb.setDescription(oldFeatureType.getDescription());
        ftb.setCRS(KMLFileFormat.KML_CRS);
        ftb.setSRS(KMLFileFormat.KML_SRS);
        // remove style attribute for now
        if (oldFeatureType.getDescriptor("Style") != null) {
            ftb.remove("Style");
        }
        ftb.add("Folder", String.class);
        SimpleFeatureType ft = ftb.buildFeatureType();
        return ft;
    }

    public SimpleFeature convertFeature(SimpleFeature old, SimpleFeatureType targetFeatureType) {
        SimpleFeatureBuilder fb = new SimpleFeatureBuilder(targetFeatureType);
        SimpleFeature newFeature = fb.buildFeature(old.getID());
        FeatureDataConverter.DEFAULT.convert(old, newFeature);
        Map<Object, Object> userData = old.getUserData();
        Object folderObject = userData.get("Folder");
        if (folderObject != null) {
            String serializedFolders = serializeFolders(folderObject);
            newFeature.setAttribute("Folder", serializedFolders);
        }
        @SuppressWarnings("unchecked")
        Map<String, String> untypedExtendedData = (Map<String, String>) userData
                .get("UntypedExtendedData");
        if (untypedExtendedData != null) {
            for (Entry<String, String> entry : untypedExtendedData.entrySet()) {
                if (targetFeatureType.getDescriptor(entry.getKey()) != null) {
                    newFeature.setAttribute(entry.getKey(), entry.getValue());
                }
            }
        }
        return newFeature;
    }

    private String serializeFolders(Object folderObject) {
        @SuppressWarnings("unchecked")
        List<Folder> folders = (List<Folder>) folderObject;
        List<String> folderNames = new ArrayList<String>(folders.size());
        for (Folder folder : folders) {
            String name = folder.getName();
            if (!StringUtils.isEmpty(name)) {
                folderNames.add(name);
            }
        }
        String serializedFolders = StringUtils.join(folderNames.toArray(), " -> ");
        return serializedFolders;
    }

    @Override
    public SimpleFeatureType apply(ImportTask task, DataStore dataStore,
            SimpleFeatureType featureType) throws Exception {
        return convertFeatureType(featureType);
    }

    @Override
    public SimpleFeature apply(ImportTask task, DataStore dataStore, SimpleFeature oldFeature,
            SimpleFeature feature) throws Exception {
        SimpleFeatureType targetFeatureType = feature.getFeatureType();
        SimpleFeature newFeature = convertFeature(oldFeature, targetFeatureType);
        feature.setAttributes(newFeature.getAttributes());
        return feature;
    }
}


File: src/extension/importer/core/src/main/java/org/geoserver/importer/transform/RasterTransformChain.java
/* (c) 2014 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.importer.transform;

import org.geoserver.importer.ImportData;
import org.geoserver.importer.ImportTask;

/**
 * @todo implement me
 * @author Ian Schneider <ischneider@opengeo.org>
 */
public class RasterTransformChain extends TransformChain<RasterTransform> {

    @Override
    public void pre(ImportTask task, ImportData data) throws Exception {
        if (transforms.size() > 0) {
            throw new RuntimeException("Not implemented");
        }
    }

    @Override
    public void post(ImportTask task, ImportData data) throws Exception {
    }
    
}


File: src/extension/importer/core/src/main/java/org/geoserver/importer/transform/ReprojectTransform.java
/* (c) 2014 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.importer.transform;

import org.geoserver.catalog.ResourceInfo;
import org.geotools.data.DataStore;
import org.geotools.feature.simple.SimpleFeatureTypeBuilder;
import org.geotools.geometry.jts.JTS;
import org.geotools.referencing.CRS;
import org.geoserver.importer.ImportTask;
import org.opengis.feature.simple.SimpleFeature;
import org.opengis.feature.simple.SimpleFeatureType;
import org.opengis.referencing.crs.CoordinateReferenceSystem;
import org.opengis.referencing.operation.MathTransform;

import com.vividsolutions.jts.geom.Geometry;

public class ReprojectTransform extends AbstractVectorTransform implements InlineVectorTransform {
    
    private static final long serialVersionUID = 1L;

    CoordinateReferenceSystem source, target;
    transient MathTransform transform;

    public CoordinateReferenceSystem getSource() {
        return source;
    }

    public void setSource(CoordinateReferenceSystem source) {
        this.source = source;
    }

    public CoordinateReferenceSystem getTarget() {
        return target;
    }

    public void setTarget(CoordinateReferenceSystem target) {
        this.target = target;
    }

    public ReprojectTransform(CoordinateReferenceSystem target) {
        this(null, target);
    }

    public ReprojectTransform(CoordinateReferenceSystem source, CoordinateReferenceSystem target) {
        this.source = source;
        this.target = target;
    }

    public SimpleFeatureType apply(ImportTask task, DataStore dataStore,
            SimpleFeatureType featureType) throws Exception {

        //update the layer metadata
        ResourceInfo r = task.getLayer().getResource();
        r.setNativeCRS(target);
        r.setSRS(CRS.lookupIdentifier(target, true));
        if (r.getNativeBoundingBox() != null) {
            r.setNativeBoundingBox(r.getNativeBoundingBox().transform(target, true));
        }
        //retype the schema
        return SimpleFeatureTypeBuilder.retype(featureType, target);
    }

    public SimpleFeature apply(ImportTask task, DataStore dataStore, SimpleFeature oldFeature, SimpleFeature feature)
            throws Exception {
        if (transform == null) {
            //compute the reprojection transform
            CoordinateReferenceSystem source = this.source;
            if (source == null) {
                //try to determine source crs from data
                source = oldFeature.getType().getCoordinateReferenceSystem();
            }

            if (source == null) {
                throw new IllegalStateException("Unable to determine source projection");
            }

            transform = CRS.findMathTransform(source, target, true);
        }

        Geometry g = (Geometry) oldFeature.getDefaultGeometry();
        if (g != null) {
            feature.setDefaultGeometry(JTS.transform(g, transform));
        }
        return feature;
    }
}


File: src/extension/importer/core/src/main/java/org/geoserver/importer/transform/TransformChain.java
/* (c) 2014 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.importer.transform;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Iterator;
import java.util.List;
import org.geoserver.importer.ImportData;
import org.geoserver.importer.ImportTask;

/**
 * Chain of transformations to apply during the import process.
 *  
 * @author Justin Deoliveira, OpenGeo
 * 
 * @see {@link VectorTransformChain}
 */
public abstract class TransformChain<T extends ImportTransform> implements Serializable {

    protected List<T> transforms;
    
    public TransformChain() {
        this(new ArrayList<T>(3));
    }

    public TransformChain(List<T> transforms) {
        this.transforms = transforms;
    }

    public TransformChain(T... transforms) {
        this.transforms = new ArrayList(Arrays.asList(transforms));
    }

    public List<T> getTransforms() {
        return transforms;
    }

    public <X extends T> void add(X tx) {
        transforms.add(tx);
    }

    public <X extends T> boolean remove(X tx) {
        return transforms.remove(tx);
    }

    public <X extends T> X get(Class<X> type) {
        for (T tx : transforms) {
            if (type.equals(tx.getClass())) {
                return (X) tx;
            }
        }
        return null;
    }

    public <X extends T> List<X> getAll(Class<X> type) {
        List<X> list = new ArrayList<X>();
        for (T tx : transforms) {
            if (type.isAssignableFrom(tx.getClass())) {
                list.add((X) tx);
            }
        }
        return list;
    }

    public <X extends T> void removeAll(Class<X> type) {
        for (Iterator<T> it = transforms.iterator(); it.hasNext(); ) {
            if (type.isAssignableFrom(it.next().getClass())) {
                it.remove();
            }
        }
    }
    
    public abstract void pre(ImportTask task, ImportData data) throws Exception;
    public abstract void post(ImportTask task, ImportData data) throws Exception;

    private Object readResolve() {
        if (transforms == null) {
            transforms = new ArrayList();
        }
        return this;
    }
}


File: src/extension/importer/core/src/main/java/org/geoserver/importer/transform/VectorTransformChain.java
/* (c) 2014 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.importer.transform;

import java.util.ArrayList;
import java.util.List;
import java.util.logging.Level;
import java.util.logging.Logger;

import org.geotools.data.DataStore;
import org.geotools.util.logging.Logging;
import org.geoserver.importer.ImportData;
import org.geoserver.importer.ImportTask;
import org.opengis.feature.simple.SimpleFeature;
import org.opengis.feature.simple.SimpleFeatureType;

/**
 * Transform chain for vectors.
 * 
 * @author Justin Deoliveira, OpenGeo
 */
public class VectorTransformChain extends TransformChain<VectorTransform> {

    static Logger LOGGER = Logging.getLogger(VectorTransformChain.class);

    public VectorTransformChain(List<VectorTransform> transforms) {
        super(transforms);
    }

    public VectorTransformChain(VectorTransform... transforms) {
        super(transforms);
    }
    
    public void pre(ImportTask item, ImportData data) throws Exception {
        for (PreVectorTransform tx : filter(transforms, PreVectorTransform.class)) {
            try {
                tx.apply(item, data);
            } catch (Exception e) {
                error(tx, e);
            }
        }
    }

    public SimpleFeatureType inline(ImportTask task, DataStore dataStore, SimpleFeatureType featureType) 
        throws Exception {
        
        for (InlineVectorTransform tx : filter(transforms, InlineVectorTransform.class)) {
            try {
                tx.init();
                featureType = tx.apply(task, dataStore, featureType);
            } catch (Exception e) {
                error(tx, e);
            }
        }
        
        return featureType;
    }

    public SimpleFeature inline(ImportTask task, DataStore dataStore, SimpleFeature oldFeature, 
        SimpleFeature feature) throws Exception {
        
        for (InlineVectorTransform tx : filter(transforms, InlineVectorTransform.class)) {
            try {
                feature = tx.apply(task, dataStore, oldFeature, feature);
                if (feature == null) {
                    break;
                }
            } catch (Exception e) {
                error(tx, e);
            }
        }
        
        return feature;
    }

    public void post(ImportTask task, ImportData data) throws Exception {
        for (PostVectorTransform tx : filter(transforms, PostVectorTransform.class)) {
            try {
                tx.apply(task, data);
            } catch (Exception e) {
                error(tx, e);
            }
        }
    }

    <T> List<T> filter(List<VectorTransform> transforms, Class<T> type) {
        List<T> filtered = new ArrayList<T>();
        for (VectorTransform tx : transforms) {
            if (type.isInstance(tx)) {
                filtered.add((T) tx);
            }
        }
        return filtered;
    }

    void error(VectorTransform tx, Exception e) throws Exception {
        if (tx.stopOnError(e)) {
            throw e;
        }
        else {
            //log and continue
            LOGGER.log(Level.WARNING, "Transform " + tx + " failed", e);
        }
    }
}


File: src/extension/importer/rest/src/main/java/org/geoserver/importer/rest/ImportJSONReader.java
/* (c) 2014 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.importer.rest;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;

import net.sf.json.JSONArray;
import net.sf.json.JSONObject;

import org.apache.commons.io.IOUtils;
import org.geoserver.catalog.CatalogFactory;
import org.geoserver.catalog.DataStoreInfo;
import org.geoserver.catalog.LayerInfo;
import org.geoserver.catalog.ResourceInfo;
import org.geoserver.catalog.StoreInfo;
import org.geoserver.catalog.StyleInfo;
import org.geoserver.catalog.WorkspaceInfo;
import org.geoserver.config.util.XStreamPersister;
import org.geotools.geometry.jts.ReferencedEnvelope;
import org.geotools.referencing.CRS;
import org.geoserver.importer.Archive;
import org.geoserver.importer.Database;
import org.geoserver.importer.Directory;
import org.geoserver.importer.FileData;
import org.geoserver.importer.ImportContext;
import org.geoserver.importer.ImportData;
import org.geoserver.importer.ImportTask;
import org.geoserver.importer.Importer;
import org.geoserver.importer.UpdateMode;
import org.geoserver.importer.ImportContext.State;
import org.geoserver.importer.ValidationException;
import org.geoserver.importer.mosaic.Mosaic;
import org.geoserver.importer.mosaic.TimeMode;
import org.geoserver.importer.transform.AttributeRemapTransform;
import org.geoserver.importer.transform.AttributesToPointGeometryTransform;
import org.geoserver.importer.transform.CreateIndexTransform;
import org.geoserver.importer.transform.DateFormatTransform;
import org.geoserver.importer.transform.ImportTransform;
import org.geoserver.importer.transform.IntegerFieldToDateTransform;
import org.geoserver.importer.transform.RasterTransformChain;
import org.geoserver.importer.transform.ReprojectTransform;
import org.geoserver.importer.transform.TransformChain;
import org.geoserver.importer.transform.VectorTransformChain;
import org.opengis.referencing.crs.CoordinateReferenceSystem;

public class ImportJSONReader {

    Importer importer;
    JSONObject json;

    public ImportJSONReader(Importer importer, String in) throws IOException {
        this(importer, new ByteArrayInputStream(in.getBytes()));
    }

    public ImportJSONReader(Importer importer, InputStream in) throws IOException {
        this.importer = importer;
        json = parse(in);
    }

    public ImportJSONReader(Importer importer, JSONObject obj) {
        this.importer = importer;
        json = obj;
    }

    public JSONObject object() {
        return json;
    }

    public ImportContext context() throws IOException {
        ImportContext context = null;
        if (json.has("import")) {
            context = new ImportContext();
            
            json = json.getJSONObject("import");
            if (json.has("id")) {
                context.setId(json.getLong("id"));
            }
            if (json.has("state")) {
                context.setState(State.valueOf(json.getString("state")));
            }
            if (json.has("user")) {
                context.setUser(json.getString("user"));
            }
            if (json.has("archive")) {
                context.setArchive(json.getBoolean("archive"));
            }
            if (json.has("targetWorkspace")) {
                context.setTargetWorkspace(
                    fromJSON(json.getJSONObject("targetWorkspace"), WorkspaceInfo.class));
            }
            if (json.has("targetStore")) {
                context.setTargetStore(
                    fromJSON(json.getJSONObject("targetStore"), StoreInfo.class));
            }
            if (json.has("data")) {
                context.setData(data(json.getJSONObject("data")));
            }
        }
        return context;
    }

    public LayerInfo layer() throws IOException {
        return layer(json);
    }

    LayerInfo layer(JSONObject json) throws IOException {
        CatalogFactory f = importer.getCatalog().getFactory();

        if (json.has("layer")) {
            json = json.getJSONObject("layer");
        }

        //TODO: what about coverages?
        ResourceInfo r = f.createFeatureType();
        if (json.has("name")) {
            r.setName(json.getString("name"));
        }
        if (json.has("nativeName")) {
            r.setNativeName(json.getString("nativeName"));
        }
        if (json.has("srs")) {
            r.setSRS(json.getString("srs"));
            try {
                r.setNativeCRS(CRS.decode(json.getString("srs")));
            }
            catch(Exception e) {
                //should fail later
            }
            
        }
        if (json.has("bbox")) {
            r.setNativeBoundingBox(bbox(json.getJSONObject("bbox")));
        }
        if (json.has("title")) {
            r.setTitle(json.getString("title"));
        }
        if (json.has("abstract")) {
            r.setAbstract(json.getString("abstract"));
        }
        if (json.has("description")) {
            r.setDescription(json.getString("description"));
        }

        LayerInfo l = f.createLayer();
        l.setResource(r);
        //l.setName(); don't need to this, layer.name just forwards to name of underlying resource
        
        if (json.has("style")) {
            JSONObject sobj = new JSONObject();
            sobj.put("defaultStyle", json.get("style"));

            JSONObject lobj = new JSONObject();
            lobj.put("layer", sobj);

            LayerInfo tmp = fromJSON(lobj, LayerInfo.class);
            if (tmp.getDefaultStyle() != null) {
                l.setDefaultStyle(tmp.getDefaultStyle());
            }
            else {
                sobj = new JSONObject();
                sobj.put("style", json.get("style"));
                
                l.setDefaultStyle(fromJSON(sobj, StyleInfo.class));
            }

        }
        return l;
    }

    public ImportTask task() throws IOException {

        if (json.has("task")) {
            json =  json.getJSONObject("task");
        }

        ImportTask task = new ImportTask();

        if (json.has("id")) {
            task.setId(json.getInt("id"));
        }
        if (json.has("updateMode")) {
            task.setUpdateMode(UpdateMode.valueOf(json.getString("updateMode").toUpperCase()));
        } else {
            // if it hasn't been specified by the request, set this to null
            // or else it's possible to overwrite an existing setting
            task.setUpdateMode(null);
        }

        JSONObject data = null;
        if (json.has("data")) {
            data = json.getJSONObject("data");
        }
        else if (json.has("source")) { // backward compatible check for source
            data = json.getJSONObject("source");
        }

        if (data != null) {
            // we only support updating the charset
            if (data.has("charset")) {
                if (task.getData() == null) {
                    task.setData(new ImportData.TransferObject());
                }
                task.getData().setCharsetEncoding(data.getString("charset"));
            }
        }
        if (json.has("target")) {
            task.setStore(fromJSON(json.getJSONObject("target"), StoreInfo.class));
        }

        LayerInfo layer = null; 
        if (json.has("layer")) {
            layer = layer(json.getJSONObject("layer"));
        } else {
            layer = importer.getCatalog().getFactory().createLayer();
        }
        task.setLayer(layer);

        if (json.has("transformChain")) {
            task.setTransform(transformChain(json.getJSONObject("transformChain")));
        }

        return task;
    }

    TransformChain transformChain(JSONObject json) throws IOException {
        String type = json.getString("type");
        TransformChain chain = null;
        if ("vector".equalsIgnoreCase(type) || "VectorTransformChain".equalsIgnoreCase(type)) {
            chain = new VectorTransformChain();
        } else if ("raster".equalsIgnoreCase(type) || "RasterTransformChain".equalsIgnoreCase(type)) {
            chain = new RasterTransformChain();
        } else {
            throw new IOException("Unable to parse transformChain of type " + type);
        }
        JSONArray transforms = json.getJSONArray("transforms");
        for (int i = 0; i < transforms.size(); i++) {
            chain.add(transform(transforms.getJSONObject(i)));
        }
        return chain;
    }

    public ImportTransform transform() throws IOException {
        return transform(json);
    }

    ImportTransform transform(JSONObject json) throws IOException {
        ImportTransform transform;
        String type = json.getString("type");
        if ("DateFormatTransform".equalsIgnoreCase(type)) {
            transform = new DateFormatTransform(json.getString("field"), json.optString("format", null));
        } else if ("IntegerFieldToDateTransform".equalsIgnoreCase(type)) {
            transform = new IntegerFieldToDateTransform(json.getString("field"));
        } else if ("CreateIndexTransform".equalsIgnoreCase(type)) {
            transform = new CreateIndexTransform(json.getString("field"));
        } else if ("AttributeRemapTransform".equalsIgnoreCase(type)) {
            Class clazz;
            try {
                clazz = Class.forName( json.getString("target") );
            } catch (ClassNotFoundException cnfe) {
                throw new ValidationException("unable to locate target class " + json.getString("target"));
            }
            transform = new AttributeRemapTransform(json.getString("field"), clazz);
        } else if ("AttributesToPointGeometryTransform".equalsIgnoreCase(type)) {
            String latField = json.getString("latField");
            String lngField = json.getString("lngField");
            transform = new AttributesToPointGeometryTransform(latField, lngField);
        } else if ("ReprojectTransform".equalsIgnoreCase(type)){
            CoordinateReferenceSystem source = json.has("source") ? crs(json.getString("source")) : null;
            CoordinateReferenceSystem target = json.has("target") ? crs(json.getString("target")) : null;

            try {
                transform = new ReprojectTransform(source, target);
            } 
            catch(Exception e) {
                throw new ValidationException("Error parsing reproject transform", e);
            }
        } else {
            throw new ValidationException("Invalid transform type '" + type + "'");
        }
        return transform;
    }

    public ImportData data() throws IOException {
        return data(json);
    }

    ImportData data(JSONObject json) throws IOException {
        String type = json.getString("type");
        if (type == null) {
            throw new IOException("Data object must specify 'type' property");
        }

        if ("file".equalsIgnoreCase(type)) {
            return file(json);
        }
        else if("directory".equalsIgnoreCase(type)) {
            return directory(json);
        }
        else if("mosaic".equalsIgnoreCase(type)) {
            return mosaic(json);
        }
        else if("archive".equalsIgnoreCase(type)) {
            return archive(json);
        }
        else if ("database".equalsIgnoreCase(type)) {
            return database(json);
        }
        else {
            throw new IllegalArgumentException("Unknown data type: " + type);
        }
    }

    FileData file(JSONObject json) throws IOException {
        if (json.has("file")) {
            //TODO: find out if spatial or not
            String file = json.getString("file");
            return FileData.createFromFile(new File(file));
            //return new FileData(new File(file));
        }
        else {
            //TODO: create a temp file
            return new FileData((File)null);
        }
    }

    Mosaic mosaic(JSONObject json) throws IOException {
        Mosaic m = new Mosaic(json.has("location") ?  new File(json.getString("location")) : 
            Directory.createNew(importer.getUploadRoot()).getFile());
        if (json.has("name")) {
            m.setName(json.getString("name"));
        }
        if (json.containsKey("time")) {
            JSONObject time = json.getJSONObject("time");
            if (!time.containsKey("mode")) {
                throw new IllegalArgumentException("time object must specific mode property as " +
                    "one of " + TimeMode.values());
            }

            m.setTimeMode(TimeMode.valueOf(time.getString("mode").toUpperCase()));
            m.getTimeHandler().init(time);
        }
        return m;
    }

    Archive archive(JSONObject json) throws IOException {
        throw new UnsupportedOperationException("TODO: implement");
    }

    public Directory directory() throws IOException {
        return directory(json);
    }

    Directory directory(JSONObject json) throws IOException {
        if (json.has("location")) {
            return new Directory(new File(json.getString("location")));
        }
        else {
            return Directory.createNew(importer.getUploadRoot());
        }
    }

    Database database(JSONObject json) throws IOException {
        throw new UnsupportedOperationException("TODO: implement");
    }
    
    ReferencedEnvelope bbox(JSONObject json) {
        CoordinateReferenceSystem crs = null;
        if (json.has("crs")) {
            crs = (CoordinateReferenceSystem) 
                new XStreamPersister.CRSConverter().fromString(json.getString("crs"));
        }

        return new ReferencedEnvelope(json.getDouble("minx"), json.getDouble("maxx"), 
            json.getDouble("miny"), json.getDouble("maxy"), crs);
    }

    CoordinateReferenceSystem crs(String srs) {
        try {
            return CRS.decode(srs);
        } catch (Exception e) {
            throw new RuntimeException("Failing parsing srs: " + srs, e);
        }
    }

    JSONObject parse(InputStream in) throws IOException {
        ByteArrayOutputStream bout = new ByteArrayOutputStream();
        IOUtils.copy(in, bout);
        return JSONObject.fromObject(new String(bout.toByteArray()));
    }

    Object read(InputStream in) throws IOException {
        Object result = null;
        JSONObject json = parse(in);
        // @hack - this should return a ImportTask
        if (json.containsKey("target")) {
            result = fromJSON(json.getJSONObject("target"), DataStoreInfo.class);
        }
        return result;
    }

    <T> T fromJSON(JSONObject json, Class<T> clazz) throws IOException {
        XStreamPersister xp = importer.createXStreamPersisterJSON();
        return (T) xp.load(new ByteArrayInputStream(json.toString().getBytes()), clazz);
    }

    <T> T fromJSON(Class<T> clazz) throws IOException {
        return fromJSON(json, clazz);
    }
}


File: src/extension/importer/rest/src/main/java/org/geoserver/importer/rest/ImportJSONWriter.java
/* (c) 2014 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.importer.rest;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.text.SimpleDateFormat;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.TimeZone;
import java.util.logging.LogRecord;

import net.sf.json.JSONArray;
import net.sf.json.JSONObject;
import net.sf.json.JSONSerializer;
import net.sf.json.util.JSONBuilder;

import org.geoserver.catalog.CoverageStoreInfo;
import org.geoserver.catalog.DataStoreInfo;
import org.geoserver.catalog.FeatureTypeInfo;
import org.geoserver.catalog.LayerInfo;
import org.geoserver.catalog.ResourceInfo;
import org.geoserver.catalog.StoreInfo;
import org.geoserver.catalog.StyleInfo;
import org.geoserver.config.util.XStreamPersister;
import org.geoserver.config.util.XStreamPersister.Callback;
import org.geoserver.config.util.XStreamPersisterFactory;
import org.geoserver.rest.PageInfo;
import org.geoserver.rest.RestletException;
import org.geotools.geometry.jts.ReferencedEnvelope;
import org.geotools.referencing.CRS;
import org.geoserver.importer.Database;
import org.geoserver.importer.Directory;
import org.geoserver.importer.FileData;
import org.geoserver.importer.ImportContext;
import org.geoserver.importer.ImportData;
import org.geoserver.importer.ImportTask;
import org.geoserver.importer.Importer;
import org.geoserver.importer.SpatialFile;
import org.geoserver.importer.Table;
import org.geoserver.importer.mosaic.Granule;
import org.geoserver.importer.mosaic.Mosaic;
import org.geoserver.importer.transform.AttributeRemapTransform;
import org.geoserver.importer.transform.AttributesToPointGeometryTransform;
import org.geoserver.importer.transform.CreateIndexTransform;
import org.geoserver.importer.transform.DateFormatTransform;
import org.geoserver.importer.transform.ImportTransform;
import org.geoserver.importer.transform.IntegerFieldToDateTransform;
import org.geoserver.importer.transform.ReprojectTransform;
import org.geoserver.importer.transform.TransformChain;
import org.geoserver.importer.transform.VectorTransformChain;
import org.opengis.referencing.crs.CoordinateReferenceSystem;
import org.restlet.data.Status;

import com.thoughtworks.xstream.converters.MarshallingContext;
import com.thoughtworks.xstream.io.HierarchicalStreamWriter;
import org.geoserver.catalog.AttributeTypeInfo;

/**
 * Utility class for reading/writing import/tasks/etc... to/from JSON.
 * 
 * @author Justin Deoliveira, OpenGeo
 */
public class ImportJSONWriter {

    static final SimpleDateFormat DATE_FORMAT = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSZ");
    static {
        DATE_FORMAT.setTimeZone(TimeZone.getTimeZone("GMT"));
    }

    Importer importer;
    PageInfo page;
    FlushableJSONBuilder json;

    public ImportJSONWriter(Importer importer, PageInfo page) {
        this(importer, page, new ByteArrayOutputStream());
    }

    public ImportJSONWriter(Importer importer, PageInfo page, OutputStream out) {
        this(importer, page, new OutputStreamWriter(out));
    }

    public ImportJSONWriter(Importer importer, PageInfo page, Writer w) {
        this.importer = importer;
        this.page = page;
        this.json = new FlushableJSONBuilder(w);
    }

    public void contexts(Iterator<ImportContext> contexts, int expand) throws IOException {
        json.object().key("imports").array();
        while (contexts.hasNext()) {
            ImportContext context = contexts.next();
            context(context, false, expand);
        }
        json.endArray().endObject();
        json.flush();
    }

    public void context(ImportContext context, boolean top, int expand) throws IOException {
        if (top) {
            json.object().key("import");
        }

        json.object();
        json.key("id").value(context.getId());
        json.key("href").value(page.rootURI(pathTo(context)));
        json.key("state").value(context.getState());
        
        if (expand > 0) {
            json.key("archive").value(context.isArchive());
            if (context.getTargetWorkspace() != null) {
                json.key("targetWorkspace").value(toJSON(context.getTargetWorkspace()));
            }
            if (context.getTargetStore() != null) {
                json.key("targetStore");
                store(context.getTargetStore(), null, false, expand-1);
                //value(toJSON(context.getTargetStore()));
            }
    
            if (context.getData() != null) {
                json.key("data");
                data(context.getData(), context, expand-1);
            }
            tasks(context.getTasks(), false, expand-1);
        }

        json.endObject();

        if (top) {
            json.endObject();
        }
        json.flush();
    }

    public void tasks(List<ImportTask> tasks, boolean top, int expand) throws IOException {

        if (top) {
            json.object();
        }

        json.key("tasks").array();
        for (ImportTask task : tasks) {
            task(task, false, expand);
        }
        json.endArray();
        
        if (top) {
            json.endObject();
        }
        json.flush();
    }

    public void task(ImportTask task, boolean top, int expand) throws IOException {

        long id = task.getId();
        String href = page.rootURI(pathTo(task));
        if (top) {
            json.object().key("task");
        }
        json.object();
        json.key("id").value(id);
        json.key("href").value(href);
        json.key("state").value(task.getState());

        if (expand > 0) {
            json.key("updateMode").value(task.getUpdateMode().name());
    
            //data (used to be source)
            ImportData data = task.getData();
            if (data != null) {
                json.key("data");
                data(data, task, expand-1);
            }

            //target
            StoreInfo store = task.getStore();
            if (store != null) {
                json.key("target");
                store(store, task, false, expand-1);
            }

            json.key("progress").value(href + "/progress");

            LayerInfo layer = task.getLayer();
            if (layer != null) {
                // @todo don't know why catalog isn't set here, thought this was set during load from BDBImportStore
                layer.getResource().setCatalog(importer.getCatalog());

                json.key("layer");
                layer(task, false, expand-1);
            }

            if (task.getError() != null) {
                json.key("errorMessage").value(concatErrorMessages(task.getError()));
            }

            transformChain(task, false, expand-1);
            messages(task.getMessages());
        }
        
        json.endObject();
        if (top) {
            json.endObject();
        }

        json.flush();
    }

    void store(StoreInfo store, ImportTask task, boolean top, int expand) throws IOException {
            
        String type = store instanceof DataStoreInfo ? "dataStore" : 
                      store instanceof CoverageStoreInfo ? "coverageStore" : "store";

        json.object();
        if (task != null) {
            json.key("href").value(page.rootURI(pathTo(task) + "/target"));
        }

        if (expand > 0) {
            JSONObject obj = toJSON(store);
            json.key(type).value(obj.get(type));
        }
        else {
            json.key(type).object()
                .key("name").value(store.getName())
                .key("type").value(store.getType())
                .endObject();
        }

        json.endObject();
        json.flush();
    }

    void layer(ImportTask task, boolean top, int expand) throws IOException {

        if (top) {
            json.object().key("layer");
        }

        LayerInfo layer = task.getLayer();
        ResourceInfo r = layer.getResource();

        json.object()
            .key("name").value(layer.getName())
            .key("href").value(page.rootURI(pathTo(task) + "/layer"));
        
        if (expand > 0) {
            if (r.getTitle() != null) {
                json.key("title").value(r.getTitle());
            }
            if (r.getAbstract() != null) {
                json.key("abstract").value(r.getAbstract());
            }
            if (r.getDescription() != null) {
                json.key("description").value(r.getDescription());
            }
            json.key("originalName").value(task.getOriginalLayerName());
            if (r != null) {
                json.key("nativeName").value(r.getNativeName());
    
                if (r.getSRS() != null) {
                    json.key("srs").value(r.getSRS());
                }
                if (r.getNativeBoundingBox() != null) {
                    json.key("bbox");
                    bbox(json, r.getNativeBoundingBox());
                }
            }
            if (r instanceof FeatureTypeInfo) {
                featureType((FeatureTypeInfo) r);
            }
            StyleInfo s = layer.getDefaultStyle();
            if (s != null) {
                style(s, task, false, expand-1);
            }
        }

        json.endObject();
        if (top) {
            json.endObject();
        }
        json.flush();
    }

    void featureType(FeatureTypeInfo featureTypeInfo) throws IOException {
        json.key("attributes").array();
        List<AttributeTypeInfo> attributes = featureTypeInfo.attributes();
        for (int i = 0; i < attributes.size(); i++) {
            AttributeTypeInfo att = attributes.get(i);
            json.object();
            json.key("name").value(att.getName());
            json.key("binding").value(att.getBinding().getName());
            json.endObject();
        }
        json.endArray();
    }

    void style(StyleInfo style, ImportTask task, boolean top, int expand) throws IOException {
        
        if (top) {
            json.object();
        }

        String href = page.rootURI(pathTo(task) + "/layer/style");

        json.key("style");
        if (expand > 0) {
            JSONObject obj = toJSON(style).getJSONObject("style");
            obj.put("href", href);
            json.value(obj);
        }
        else {
            json.object();
            json.key("name").value(style.getName());
            json.key("href").value(href);
            json.endObject();
        }
        
        if (top) {
            json.endObject();
        }
    }

    void transformChain(ImportTask task, boolean top, int expand) throws IOException {

        if (top) {
            json.object();
        }

        TransformChain<? extends ImportTransform> txChain = task.getTransform();

        json.key("transformChain").object();
        json.key("type").value(txChain instanceof VectorTransformChain ? "vector" : "raster");

        json.key("transforms").array();

        if (txChain != null) {
            for (int i = 0; i < txChain.getTransforms().size(); i++) {
                transform(txChain.getTransforms().get(i), i, task, false, expand);
            }
        }

        json.endArray();
        json.endObject();

        if (top) {
            json.endObject();
        }
        
        json.flush();
    }

    public void transform(ImportTransform transform, int index, ImportTask task, boolean top, 
        int expand) throws IOException {
        json.object();
        json.key("type").value(transform.getClass().getSimpleName());
        json.key("href").value(page.rootURI(pathTo(task)+"/transform/" + index));
        if (expand > 0) {
            if (transform instanceof DateFormatTransform) {
                DateFormatTransform df = (DateFormatTransform) transform;
                json.key("field").value(df.getField());
                if (df.getDatePattern() != null) {
                    json.key("format").value(df.getDatePattern().dateFormat().toPattern());
                }
    
            } else if (transform instanceof IntegerFieldToDateTransform) {
                IntegerFieldToDateTransform df = (IntegerFieldToDateTransform) transform;
                json.key("field").value(df.getField());
            } else if (transform instanceof CreateIndexTransform) {
                CreateIndexTransform df = (CreateIndexTransform) transform;
                json.key("field").value(df.getField());
            } else if (transform instanceof AttributeRemapTransform) {
                AttributeRemapTransform art = (AttributeRemapTransform) transform;
                json.key("field").value(art.getField());
                json.key("target").value(art.getType().getName());
            } else if (transform.getClass() == AttributesToPointGeometryTransform.class) {
                AttributesToPointGeometryTransform atpgt = (AttributesToPointGeometryTransform) transform;
                json.key("latField").value(atpgt.getLatField());
                json.key("lngField").value(atpgt.getLngField());
            } else if (transform.getClass() == ReprojectTransform.class) {
                ReprojectTransform rt = (ReprojectTransform) transform;
                json.key("source").value(srs(rt.getSource()));
                json.key("target").value(srs(rt.getTarget()));
            } else {
                throw new IOException("Serializaiton of " + transform.getClass() + " not implemented");
            }
        }
        json.endObject();
        json.flush();
    }

    void bbox(JSONBuilder json, ReferencedEnvelope bbox) {
        json.object()
            .key("minx").value(bbox.getMinX())
            .key("miny").value(bbox.getMinY())
            .key("maxx").value(bbox.getMaxX())
            .key("maxy").value(bbox.getMaxY());

        CoordinateReferenceSystem crs = bbox.getCoordinateReferenceSystem(); 
        if (crs != null) {
            json.key("crs").value(crs.toWKT());
        }

        json.endObject();
    }

    public void data(ImportData data, Object parent, int expand) throws IOException {
        if (data instanceof FileData) {
            if (data instanceof Directory) {
                if (data instanceof Mosaic) {
                    mosaic((Mosaic) data, parent ,expand);
                }
                else {
                    directory((Directory) data, parent, expand);
                }
            } else {
                file((FileData) data, parent, expand, false);
            }
        } else if (data instanceof Database) {
            database((Database) data, parent, expand);
        } else if (data instanceof Table) {
            table((Table)data, parent, expand);
        }
        json.flush();
    }

    public void file(FileData data, Object parent, int expand, boolean href) throws IOException {
        
        json.object();
        
        json.key("type").value("file");
        json.key("format").value(data.getFormat() != null ? data.getFormat().getName() : null);
        if (href) {
            json.key("href").value(page.rootURI(pathTo(data, parent)));
        }
        
        if (expand > 0) {
            json.key("location").value(data.getFile().getParentFile().getPath());
            if (data.getCharsetEncoding() != null) {
                json.key("charset").value(data.getCharsetEncoding());
            }
            fileContents(data, parent, expand);
            message(data);
        }
        else {
            json.key("file").value(data.getFile().getName());
        }

        json.endObject();
        json.flush();
    }

    void fileContents(FileData data, Object parent, int expand) throws IOException {
        //TODO: we should probably url encode to handle spaces and other chars
        String filename = data.getFile().getName();
        json.key("file").value(filename);
        json.key("href").value(page.rootURI(pathTo(data, parent)+"/files/"+filename));
        if (expand > 0) {
            if (data instanceof SpatialFile) {
                SpatialFile sf = (SpatialFile) data;
                json.key("prj").value(sf.getPrjFile() != null ? sf.getPrjFile().getName() : null);
                json.key("other").array();
                for (File supp : ((SpatialFile) data).getSuppFiles()) {
                    json.value(supp.getName());
                }
                json.endArray();
    
                if (sf instanceof Granule) {
                    Granule g = (Granule) sf;
                    if (g.getTimestamp() != null) {
                        json.key("timestamp").value(DATE_FORMAT.format(g.getTimestamp()));
                    }
                }
            }
        }
    }


    public void mosaic(Mosaic data, Object parent, int expand) 
        throws IOException {
        directory(data, "mosaic", parent, expand);
    }

    public void directory(Directory data, Object parent, int expand) throws IOException {
        directory(data, "directory", parent, expand);
    }

    public void directory(Directory data, String typeName, Object parent, int expand) 
        throws IOException {

        json.object();
        json.key("type").value(typeName);
        if (data.getFormat() != null) {
            json.key("format").value(data.getFormat().getName());
        }

        json.key("location").value(data.getFile().getPath());
        json.key("href").value(page.rootURI(pathTo(data, parent)));

        if (expand > 0) {
            if (data.getCharsetEncoding() != null) {
                json.key("charset").value(data.getCharsetEncoding());
            }

            json.key("files");
            files(data, parent, false, expand-1);
            message(data);
        }
        json.endObject();
        json.flush();
    }

    public void files(Directory data, Object parent, boolean top, int expand) throws IOException {

        if (top) {
            json.object().key("files");
        }
        json.array();
        for (FileData file : data.getFiles()) {
            json.object();
            fileContents(file, parent, expand-1);
            json.endObject();
        }
        json.endArray();
        if (top) {
            json.endObject();
        }
        json.flush();
    }

    public void database(Database data, Object parent, int expand) throws IOException {
        json.object();
        json.key("type").value("database");
        json.key("format").value(data.getFormat() != null ? data.getFormat().getName() : null);
        json.key("href").value(page.rootURI(pathTo(data, parent)));

        if (expand > 0) {
            json.key("parameters").object();
            for (Map.Entry e : data.getParameters().entrySet()) {
                json.key((String) e.getKey()).value(e.getValue());
            }
    
            json.endObject();
            
            json.key("tables").array();
            for (Table t : data.getTables()) {
                json.value(t.getName());
            }
    
            message(data);
            json.endArray();
        }

        json.endObject();
    }

    void table(Table data, Object parent, int expand) throws IOException {
        json.object();
        json.key("type").value("table");
        json.key("name").value(data.getName());
        json.key("format").value(data.getFormat() != null ? data.getFormat().getName() : null);
        json.key("href").value(page.rootURI(pathTo(data, parent)));
        json.endObject();
    }

    void message(ImportData data) throws IOException {
        if (data.getMessage() != null) {
            json.key("message").value(data.getMessage());
        }
    }

    void messages(List<LogRecord> records) {
        if (!records.isEmpty()) {
            json.key("messages");
            json.array();
            for (int i = 0; i < records.size(); i++) {
                LogRecord record = records.get(i);
                json.object();
                json.key("level").value(record.getLevel().toString());
                json.key("message").value(record.getMessage());
                json.endObject();
            }
            json.endArray();
        }
    }

    String concatErrorMessages(Throwable ex) {
        StringBuilder buf = new StringBuilder();
        while (ex != null) {
            if (buf.length() > 0) {
                buf.append('\n');
            }
            if (ex.getMessage() != null) {
                buf.append(ex.getMessage());
            }
            ex = ex.getCause();
        }
        return buf.toString();
    }

    FlushableJSONBuilder builder(OutputStream out) {
        return new FlushableJSONBuilder(new OutputStreamWriter(out));
    }

    JSONObject toJSON(Object o) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        toJSON(o, out);
        return (JSONObject) JSONSerializer.toJSON(new String(out.toByteArray()));
    }

    void toJSON(Object o, OutputStream out) throws IOException {
        toJSON(o, out, null);
    }
    
    void toJSON(Object o, OutputStream out, Callback callback) throws IOException {
        XStreamPersister xp = persister();
        if (callback != null) {
            xp.setCallback(callback);
        }
        xp.save(o, out);
        out.flush();
    }

    XStreamPersister persister() {
        XStreamPersister xp = 
            importer.initXStreamPersister(new XStreamPersisterFactory().createJSONPersister());
        
        xp.setReferenceByName(true);
        xp.setExcludeIds();

        //xp.setCatalog(importer.getCatalog());
        xp.setHideFeatureTypeAttributes();
        // @todo this is copy-and-paste from org.geoserver.catalog.rest.FeatureTypeResource
        xp.setCallback(new XStreamPersister.Callback() {

            @Override
            protected void postEncodeFeatureType(FeatureTypeInfo ft,
                    HierarchicalStreamWriter writer, MarshallingContext context) {
                try {
                    writer.startNode("attributes");
                    context.convertAnother(ft.attributes());
                    writer.endNode();
                } catch (IOException e) {
                    throw new RuntimeException("Could not get native attributes", e);
                }
            }
        });
        return xp;
    }

    String srs(CoordinateReferenceSystem crs) {
        return CRS.toSRS(crs);
    }

    static String pathTo(ImportContext context) {
        return "/imports/" + context.getId();
    }

    static String pathTo(ImportTask task) {
        return pathTo(task.getContext()) +  "/tasks/" + task.getId();
    }

    String pathTo(Object parent) {
        if (parent instanceof ImportContext) {
            return pathTo((ImportContext)parent);
        }
        else if (parent instanceof ImportTask) {
            return pathTo((ImportTask)parent);
        }
        else {
            throw new IllegalArgumentException("Don't recognize: " + parent);
        }
    }

    String pathTo(ImportData data, Object parent) {
        return pathTo(parent) + "/data";
    }

    static RestletException badRequest(String error) {
        JSONObject errorResponse = new JSONObject();
        JSONArray errors = new JSONArray();
        errors.add(error);
        errorResponse.put("errors", errors);
        
        JSONRepresentation rep = new JSONRepresentation(errorResponse);
        return new RestletException(rep, Status.CLIENT_ERROR_BAD_REQUEST);
    }

    public static class FlushableJSONBuilder extends JSONBuilder {

        public FlushableJSONBuilder(Writer w) {
            super(w);
        }

        public void flush() throws IOException {
            writer.flush();
        }
    }
}


File: src/main/src/main/java/org/geoserver/catalog/CatalogBuilder.java
/* (c) 2014 Open Source Geospatial Foundation - all rights reserved
 * (c) 2001 - 2013 OpenPlans
 * This code is licensed under the GPL 2.0 license, available at the root
 * application directory.
 */
package org.geoserver.catalog;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.logging.Level;
import java.util.logging.Logger;

import javax.measure.unit.Unit;
import javax.media.jai.PlanarImage;

import org.geoserver.catalog.impl.FeatureTypeInfoImpl;
import org.geoserver.catalog.impl.ModificationProxy;
import org.geoserver.catalog.impl.ResourceInfoImpl;
import org.geoserver.catalog.impl.StoreInfoImpl;
import org.geoserver.catalog.impl.StyleInfoImpl;
import org.geoserver.catalog.impl.WMSStoreInfoImpl;
import org.geoserver.data.util.CoverageStoreUtils;
import org.geoserver.data.util.CoverageUtils;
import org.geoserver.ows.util.OwsUtils;
import org.geotools.coverage.Category;
import org.geotools.coverage.GridSampleDimension;
import org.geotools.coverage.grid.GridCoverage2D;
import org.geotools.coverage.grid.GridEnvelope2D;
import org.geotools.coverage.grid.GridGeometry2D;
import org.geotools.coverage.grid.io.AbstractGridFormat;
import org.geotools.coverage.grid.io.GridCoverage2DReader;
import org.geotools.data.FeatureSource;
import org.geotools.data.ows.CRSEnvelope;
import org.geotools.data.ows.Layer;
import org.geotools.factory.GeoTools;
import org.geotools.feature.FeatureTypes;
import org.geotools.gce.imagemosaic.ImageMosaicFormat;
import org.geotools.geometry.GeneralEnvelope;
import org.geotools.geometry.jts.ReferencedEnvelope;
import org.geotools.referencing.CRS;
import org.geotools.referencing.CRS.AxisOrder;
import org.geotools.referencing.crs.DefaultGeographicCRS;
import org.geotools.resources.image.ImageUtilities;
import org.geotools.util.NumberRange;
import org.geotools.util.Version;
import org.geotools.util.logging.Logging;
import org.opengis.coverage.grid.Format;
import org.opengis.coverage.grid.GridEnvelope;
import org.opengis.feature.type.AttributeDescriptor;
import org.opengis.feature.type.FeatureType;
import org.opengis.feature.type.GeometryDescriptor;
import org.opengis.feature.type.Name;
import org.opengis.feature.type.PropertyDescriptor;
import org.opengis.metadata.Identifier;
import org.opengis.parameter.ParameterValueGroup;
import org.opengis.referencing.FactoryException;
import org.opengis.referencing.crs.CoordinateReferenceSystem;
import org.opengis.referencing.crs.GeographicCRS;
import org.opengis.referencing.datum.PixelInCell;
import org.opengis.referencing.operation.MathTransform;

import com.vividsolutions.jts.geom.LineString;
import com.vividsolutions.jts.geom.MultiLineString;
import com.vividsolutions.jts.geom.MultiPoint;
import com.vividsolutions.jts.geom.MultiPolygon;
import com.vividsolutions.jts.geom.Point;
import com.vividsolutions.jts.geom.Polygon;

/**
 * Builder class which provides convenience methods for interacting with the catalog.
 * <p>
 * Warning: this class is stateful, and is not meant to be accessed by multiple threads and should
 * not be an member variable of another class.
 * </p>
 * 
 * @author Justin Deoliveira, OpenGEO
 * 
 */
public class CatalogBuilder {

    static final Logger LOGGER = Logging.getLogger(CatalogBuilder.class);

    /**
     * the catalog
     */
    Catalog catalog;

    /**
     * the current workspace
     */
    WorkspaceInfo workspace;

    /**
     * the current store
     */
    StoreInfo store;

    public CatalogBuilder(Catalog catalog) {
        this.catalog = catalog;
    }

    /**
     * Sets the workspace to be used when creating store objects.
     */
    public void setWorkspace(WorkspaceInfo workspace) {
        this.workspace = workspace;
    }

    /**
     * Sets the store to be used when creating resource objects.
     */
    public void setStore(StoreInfo store) {
        this.store = store;
    }

    /**
     * Updates a workspace with the properties of another.
     * 
     * @param original
     *            The workspace being updated.
     * @param update
     *            The workspace containing the new values.
     */
    public void updateWorkspace(WorkspaceInfo original, WorkspaceInfo update) {
        update(original, update, WorkspaceInfo.class);
    }

    /**
     * Updates a namespace with the properties of another.
     * 
     * @param original
     *            The namespace being updated.
     * @param update
     *            The namespace containing the new values.
     */
    public void updateNamespace(NamespaceInfo original, NamespaceInfo update) {
        update(original, update, NamespaceInfo.class);
    }

    /**
     * Updates a datastore with the properties of another.
     * 
     * @param original
     *            The datastore being updated.
     * @param update
     *            The datastore containing the new values.
     */
    public void updateDataStore(DataStoreInfo original, DataStoreInfo update) {
        update(original, update, DataStoreInfo.class);
    }

    /**
     * Updates a wms store with the properties of another.
     * 
     * @param original
     *            The wms store being updated.
     * @param update
     *            The wms store containing the new values.
     */
    public void updateWMSStore(WMSStoreInfo original, WMSStoreInfo update) {
        update(original, update, WMSStoreInfo.class);
    }

    /**
     * Updates a coveragestore with the properties of another.
     * 
     * @param original
     *            The coveragestore being updated.
     * @param update
     *            The coveragestore containing the new values.
     */
    public void updateCoverageStore(CoverageStoreInfo original, CoverageStoreInfo update) {
        update(original, update, CoverageStoreInfo.class);
    }

    /**
     * Updates a feature type with the properties of another.
     * 
     * @param original
     *            The feature type being updated.
     * @param update
     *            The feature type containing the new values.
     */
    public void updateFeatureType(FeatureTypeInfo original, FeatureTypeInfo update) {
        update(original, update, FeatureTypeInfo.class);
    }

    /**
     * Updates a coverage with the properties of another.
     * 
     * @param original
     *            The coverage being updated.
     * @param update
     *            The coverage containing the new values.
     */
    public void updateCoverage(CoverageInfo original, CoverageInfo update) {
        update(original, update, CoverageInfo.class);
    }

    /**
     * Updates a WMS layer with the properties of another.
     * 
     * @param original
     *            The wms layer being updated.
     * @param update
     *            The wms layer containing the new values.
     */
    public void updateWMSLayer(WMSLayerInfo original, WMSLayerInfo update) {
        update(original, update, WMSLayerInfo.class);
    }

    /**
     * Updates a layer with the properties of another.
     * 
     * @param original
     *            The layer being updated.
     * @param update
     *            The layer containing the new values.
     */
    public void updateLayer(LayerInfo original, LayerInfo update) {
        update(original, update, LayerInfo.class);
    }

    /**
     * Updates a layer group with the properties of another.
     * 
     * @param original
     *            The layer group being updated.
     * @param update
     *            The layer group containing the new values.
     */
    public void updateLayerGroup(LayerGroupInfo original, LayerGroupInfo update) {
        update(original, update, LayerGroupInfo.class);
    }

    /**
     * Updates a style with the properties of another.
     * 
     * @param original
     *            The style being updated.
     * @param update
     *            The style containing the new values.
     */
    public void updateStyle(StyleInfo original, StyleInfo update) {
        update(original, update, StyleInfo.class);
    }

    /**
     * Update method which uses reflection to grab property values from one object and set them on
     * another.
     * <p>
     * Null values from the <tt>update</tt> object are ignored.
     * </p>
     */
    <T> void update(T original, T update, Class<T> clazz) {
        OwsUtils.copy(update, original, clazz);
    }

    /**
     * Builds a new data store.
     */
    public DataStoreInfo buildDataStore(String name) {
        DataStoreInfo info = catalog.getFactory().createDataStore();
        buildStore(info, name);

        return info;
    }

    /**
     * Builds a new coverage store.
     */
    public CoverageStoreInfo buildCoverageStore(String name) {
        CoverageStoreInfo info = catalog.getFactory().createCoverageStore();
        buildStore(info, name);

        return info;
    }

    /**
     * Builds a new WMS store
     */
    public WMSStoreInfo buildWMSStore(String name) throws IOException {
        WMSStoreInfo info = catalog.getFactory().createWebMapServer();
        buildStore(info, name);
        info.setType("WMS");
        info.setMaxConnections(WMSStoreInfoImpl.DEFAULT_MAX_CONNECTIONS);
        info.setConnectTimeout(WMSStoreInfoImpl.DEFAULT_CONNECT_TIMEOUT);
        info.setReadTimeout(WMSStoreInfoImpl.DEFAULT_READ_TIMEOUT);

        return info;
    }

    /**
     * Builds a store.
     * <p>
     * The workspace of the resulting store is {@link #workspace} if set, else the default workspace
     * from the catalog.
     * </p>
     */
    void buildStore(StoreInfo info, String name) {

        info.setName(name);
        info.setEnabled(true);

        // set workspace, falling back on default if none specified
        if (workspace != null) {
            info.setWorkspace(workspace);
        } else {
            info.setWorkspace(catalog.getDefaultWorkspace());
        }
    }

    /**
     * Builds a {@link FeatureTypeInfo} from the current datastore and the specified type name
     * <p>
     * The resulting object is not added to the catalog, it must be done by the calling code after
     * the fact.
     * </p>
     */
    public FeatureTypeInfo buildFeatureType(Name typeName) throws Exception {
        if (store == null || !(store instanceof DataStoreInfo)) {
            throw new IllegalStateException("Data store not set.");
        }

        DataStoreInfo dstore = (DataStoreInfo) store;
        return buildFeatureType(dstore.getDataStore(null).getFeatureSource(typeName));
    }

    /**
     * Builds a feature type from a geotools feature source. The resulting {@link FeatureTypeInfo}
     * will still miss the bounds and might miss the SRS. Use {@link #lookupSRS(FeatureTypeInfo,
     * true)} and {@link #setupBounds(FeatureTypeInfo)} if you want to force them in (and spend time
     * accordingly)
     * <p>
     * The resulting object is not added to the catalog, it must be done by the calling code after
     * the fact.
     * </p>
     */
    public FeatureTypeInfo buildFeatureType(FeatureSource featureSource) {
        if (store == null || !(store instanceof DataStoreInfo)) {
            throw new IllegalStateException("Data store not set.");
        }

        FeatureType featureType = featureSource.getSchema();

        FeatureTypeInfo ftinfo = catalog.getFactory().createFeatureType();
        ftinfo.setStore(store);
        ftinfo.setEnabled(true);

        // naming
        Name name = featureSource.getName();
        if (name == null) {
            name = featureType.getName();
        }
        ftinfo.setNativeName(name.getLocalPart());
        ftinfo.setName(name.getLocalPart());

        WorkspaceInfo workspace = store.getWorkspace();
        NamespaceInfo namespace = catalog.getNamespaceByPrefix(workspace.getName());
        if (namespace == null) {
            namespace = catalog.getDefaultNamespace();
        }

        ftinfo.setNamespace(namespace);

        CoordinateReferenceSystem crs = featureType.getCoordinateReferenceSystem();
        if (crs == null && featureType.getGeometryDescriptor() != null) {
            crs = featureType.getGeometryDescriptor().getCoordinateReferenceSystem();
        }
        ftinfo.setNativeCRS(crs);

        // srs look and set (by default we just use fast lookup)
        try {
            lookupSRS(ftinfo, false);
        } catch (Exception e) {
            LOGGER.log(Level.WARNING, "SRS lookup failed", e);
        }
        setupProjectionPolicy(ftinfo);

        // fill in metadata, first check if the datastore itself can provide some metadata for us
        try {
            setupMetadata(ftinfo, featureSource);
        } catch (IOException e) {
            LOGGER.log(Level.WARNING, "Metadata lookup failed", e);
        }
        
        return ftinfo;
    }

    /**
     * Sets the projection policy for a resource based on the following rules:
     * <ul>
     * <li>If getSRS() returns a non null value it is set to {@Link
     * ProjectionPolicy#FORCE_DECLARED}
     * <li>If getSRS() returns a null value it is set to {@link ProjectionPolicy#NONE}
     * </ul>
     * 
     * TODO: make this method smarter, and compare the native crs to figure out if prejection
     * actually needs to be done, and sync it up with setting proj policy on coverage layers.
     */
    public void setupProjectionPolicy(ResourceInfo rinfo) {
        if (rinfo.getSRS() != null) {
            rinfo.setProjectionPolicy(ProjectionPolicy.FORCE_DECLARED);
        } else {
            rinfo.setProjectionPolicy(ProjectionPolicy.NONE);
        }
    }

    /**
     * Computes the native bounds for a {@link FeatureTypeInfo} explicitly providing the feature
     *  source.
     * <p>
     * This method calls through to {@link #doSetupBounds(ResourceInfo, Object)}.
     * </p>
     */
    public void setupBounds(FeatureTypeInfo ftinfo, FeatureSource featureSource) throws IOException {
        doSetupBounds(ftinfo, featureSource);
    }

    /**
     * Computes the native bounds for a {@link CoverageInfo} explicitly providing the coverage 
     *  reader.
     * <p>
     * This method calls through to {@link #doSetupBounds(ResourceInfo, Object)}.
     * </p>
     */
    public void setupBounds(CoverageInfo cinfo, GridCoverage2DReader coverageReader) 
        throws IOException {
        doSetupBounds(cinfo, coverageReader);
    }

    /**
     * Given a {@link ResourceInfo} this method:
     * <ul>
     * <li>computes, if missing, the native bounds (warning, this might be very expensive, cases in
     * which this case take minutes are not uncommon if the data set is made of million of features)
     * </li>
     * <li>updates, if possible, the geographic bounds accordingly by re-projecting the native
     * bounds into WGS84</li>
     * 
     * @param ftinfo
     * @throws IOException
     *             if computing the native bounds fails or if a transformation error occurs during
     *             the geographic bounds computation
     */
    public void setupBounds(ResourceInfo rinfo) throws IOException {
        doSetupBounds(rinfo, null);
    }

    /*
     * Helper method for setupBounds() methods which can optionally take a "data" object rather
     * than access it through the catalog. This allows for this method to be called for info objects
     * that might not be part of the catalog.
     */
    void doSetupBounds(ResourceInfo rinfo, Object data) throws IOException {
        // setup the native bbox if needed
        if (rinfo.getNativeBoundingBox() == null) {
            ReferencedEnvelope bounds = getNativeBounds(rinfo, data);
            rinfo.setNativeBoundingBox(bounds);
        }

        // setup the geographic bbox if missing and we have enough info
        rinfo.setLatLonBoundingBox(getLatLonBounds(rinfo.getNativeBoundingBox(), rinfo.getCRS()));
    }

    /**
     * Fills in metadata on the {@link FeatureTypeInfo} from an underlying feature source.
     */
    public void setupMetadata(FeatureTypeInfo ftinfo, FeatureSource featureSource) 
        throws IOException {

        org.geotools.data.ResourceInfo rinfo = null;
        try {
            rinfo = featureSource.getInfo();
        }
        catch(Exception ignore) {
            if (LOGGER.isLoggable(Level.FINE)) {
                LOGGER.log(Level.FINE, "Unable to get resource info from feature source", ignore);
            }
        }

        if (ftinfo.getTitle() == null) {
            ftinfo.setTitle(rinfo != null ? rinfo.getTitle() : ftinfo.getName());
        }
        if (rinfo != null && ftinfo.getDescription() == null) {
            ftinfo.setDescription(rinfo.getDescription());
        }
        if (rinfo != null && (ftinfo.getKeywords() == null || ftinfo.getKeywords().isEmpty())) {
            if (rinfo.getKeywords() != null) {
                if (ftinfo.getKeywords() == null) {
                    ((FeatureTypeInfoImpl)ftinfo).setKeywords(new ArrayList());
                }
                for (String kw : rinfo.getKeywords()) {
                    if (kw == null || "".equals(kw.trim())) {
                        LOGGER.fine("Empty keyword ignored");
                        continue;
                    }
                    ftinfo.getKeywords().add(new Keyword(kw));
                }
            }
        }
    }

    /**
     * Computes the geographic bounds of a {@link ResourceInfo} by reprojecting the available native
     * bounds
     * 
     * @param rinfo
     * @return the geographic bounds, or null if the native bounds are not available
     * @throws IOException
     */
    public ReferencedEnvelope getLatLonBounds(ReferencedEnvelope nativeBounds,
            CoordinateReferenceSystem declaredCRS) throws IOException {
        if (nativeBounds != null && declaredCRS != null) {
            // make sure we use the declared CRS, not the native one, the may differ
            if (!CRS.equalsIgnoreMetadata(DefaultGeographicCRS.WGS84, declaredCRS)) {
                // transform
                try {
                    ReferencedEnvelope bounds = new ReferencedEnvelope(nativeBounds, declaredCRS);
                    return bounds.transform(DefaultGeographicCRS.WGS84, true);
                } catch (Exception e) {
                    throw (IOException) new IOException("transform error").initCause(e);
                }
            } else {
                return new ReferencedEnvelope(nativeBounds, DefaultGeographicCRS.WGS84);
            }
        }
        return null;
    }

    /**
     * Computes the native bounds of a {@link ResourceInfo} taking into account the nature of the
     * data and the reprojection policy in act
     * 
     * @param rinfo
     * @return the native bounds, or null if the could not be computed
     * @throws IOException
     */
    public ReferencedEnvelope getNativeBounds(ResourceInfo rinfo) throws IOException {
        return getNativeBounds(rinfo, null);
    }

    /*
     * Helper method for getNativeBounds() methods which can optionally take a "data" object rather
     * than access it through the catalog. This allows for this method to be called for info objects
     * that might not be part of the catalog.
     */
    ReferencedEnvelope getNativeBounds(ResourceInfo rinfo, Object data) throws IOException {
        ReferencedEnvelope bounds = null;
        if (rinfo instanceof FeatureTypeInfo) {
            FeatureTypeInfo ftinfo = (FeatureTypeInfo) rinfo;

            // bounds
            if (data instanceof FeatureSource) {
                bounds = ((FeatureSource)data).getBounds();
            }
            else {
                bounds = ftinfo.getFeatureSource(null, null).getBounds();
            }

            // fix the native bounds if necessary, some datastores do
            // not build a proper referenced envelope
            CoordinateReferenceSystem crs = ftinfo.getNativeCRS();
            if (bounds != null && bounds.getCoordinateReferenceSystem() == null && crs != null) {
                bounds = new ReferencedEnvelope(bounds, crs);
            }

            if (bounds != null) {
                // expansion factor if the bounds are empty or one dimensional
                double expandBy = 1; // 1 meter
                if (bounds.getCoordinateReferenceSystem() instanceof GeographicCRS) {
                    expandBy = 0.0001;
                }
                if (bounds.getWidth() == 0 || bounds.getHeight() == 0) {
                    bounds.expandBy(expandBy);
                }
            }

        } else if (rinfo instanceof CoverageInfo) {
            // the coverage bounds computation path is a bit more linear, the
            // readers always return the bounds and in the proper CRS (afaik)
            CoverageInfo cinfo = (CoverageInfo) rinfo;            
            GridCoverage2DReader reader = null;
            if (data instanceof GridCoverage2DReader) {
                reader = (GridCoverage2DReader) data;
            }
            else {
                reader = (GridCoverage2DReader) 
                    cinfo.getGridCoverageReader(null, GeoTools.getDefaultHints());
            }

            // get  bounds
            bounds = new ReferencedEnvelope(reader.getOriginalEnvelope());
           
        } else if(rinfo instanceof WMSLayerInfo) {
            // the logic to compute the native bounds is pretty convoluted,
            // let's rebuild the layer info
            WMSLayerInfo rebuilt = buildWMSLayer(rinfo.getStore(), rinfo.getNativeName());
            bounds = rebuilt.getNativeBoundingBox();
        }

        // apply the bounds, taking into account the reprojection policy if need be
        if (rinfo.getProjectionPolicy() == ProjectionPolicy.REPROJECT_TO_DECLARED && bounds != null) {
            try {
                bounds = bounds.transform(rinfo.getCRS(), true);
            } catch (Exception e) {
                throw (IOException) new IOException("transform error").initCause(e);
            }
        }

        return bounds;
    }

    /**
     * Looks up and sets the SRS based on the feature type info native
     * {@link CoordinateReferenceSystem}
     * 
     * @param ftinfo
     * @param extensive
     *            if true an extenstive lookup will be performed (more accurate, but might take
     *            various seconds)
     * @throws IOException
     */
    public void lookupSRS(FeatureTypeInfo ftinfo, boolean extensive) throws IOException {
        lookupSRS(ftinfo, null, extensive);
    }

    /**
     * Looks up and sets the SRS based on the feature type info native 
     * {@link CoordinateReferenceSystem}, obtained from an optional feature source.
     * 
     * @param ftinfo
     * @param data A feature source (possibily null)
     * @param extensive
     *            if true an extenstive lookup will be performed (more accurate, but might take
     *            various seconds)
     * @throws IOException
     */
    public void lookupSRS(FeatureTypeInfo ftinfo, FeatureSource data, boolean extensive) 
            throws IOException {
        CoordinateReferenceSystem crs = ftinfo.getNativeCRS();
        if (crs == null) {
            if (data != null) {
                crs = data.getSchema().getCoordinateReferenceSystem();
            }
            else {
                crs = ftinfo.getFeatureType().getCoordinateReferenceSystem();
            }
        }
        if (crs != null) {
            try {
                Integer code = CRS.lookupEpsgCode(crs, extensive);
                if (code != null)
                    ftinfo.setSRS("EPSG:" + code);
            } catch (FactoryException e) {
                throw (IOException) new IOException().initCause(e);
            }
        }
    }

    /**
     * Initializes basic resource info.
     */
    private void initResourceInfo(ResourceInfo resInfo) throws Exception {
    	// set the name
    	if (resInfo.getNativeName() == null && resInfo.getName() != null) {
    		resInfo.setNativeName(resInfo.getName());
    	}
    	if (resInfo.getNativeName() != null && resInfo.getName() == null) {
    		resInfo.setName(resInfo.getNativeName());
    	}
    }

    /**
     * Initializes a feature type object setting any info that has not been set.
     */
    public void initFeatureType(FeatureTypeInfo featureType) throws Exception {
        if (featureType.getCatalog() == null) {
            featureType.setCatalog(catalog);
        }

        initResourceInfo(featureType);

        // setup the srs if missing
        if (featureType.getSRS() == null) {
            lookupSRS(featureType, true);
        }
        if (featureType.getProjectionPolicy() == null) {
            setupProjectionPolicy(featureType);
        }

        // deal with bounding boxes as possible
        CoordinateReferenceSystem crs = featureType.getCRS();
        if (featureType.getLatLonBoundingBox() == null
                && featureType.getNativeBoundingBox() == null) {
            // both missing, we compute them
            setupBounds(featureType);
        } else if (featureType.getLatLonBoundingBox() == null) {
            // native available but geographic to be computed
            setupBounds(featureType);
        } else if (featureType.getNativeBoundingBox() == null && crs != null) {
            // we know the geographic and we can reproject back to native
            ReferencedEnvelope boundsLatLon = featureType.getLatLonBoundingBox();
            featureType.setNativeBoundingBox(boundsLatLon.transform(crs, true));
        }
    }

    /**
     * Initializes a wms layer object setting any info that has not been set.
     */
    public void initWMSLayer(WMSLayerInfo wmsLayer) throws Exception {
        wmsLayer.setCatalog(catalog);

        initResourceInfo(wmsLayer);
        OwsUtils.resolveCollections(wmsLayer);

        // get a fully initialized version we can copy from
        WMSLayerInfo full = buildWMSLayer(store, wmsLayer.getNativeName());

        // setup the srs if missing
        if (wmsLayer.getSRS() == null) {
            wmsLayer.setSRS(full.getSRS());
        }
        if (wmsLayer.getNativeCRS() == null) {
            wmsLayer.setNativeCRS(full.getNativeCRS());
        }
        if (wmsLayer.getProjectionPolicy() == null) {
            wmsLayer.setProjectionPolicy(full.getProjectionPolicy());
        }

        // deal with bounding boxes as possible
        if (wmsLayer.getLatLonBoundingBox() == null
                && wmsLayer.getNativeBoundingBox() == null) {
            // both missing, we copy them
            wmsLayer.setLatLonBoundingBox(full.getLatLonBoundingBox());
            wmsLayer.setNativeBoundingBox(full.getNativeBoundingBox());
        } else if (wmsLayer.getLatLonBoundingBox() == null) {
            // native available but geographic to be computed
            setupBounds(wmsLayer);
        } else if (wmsLayer.getNativeBoundingBox() == null && wmsLayer.getNativeCRS() != null) {
            // we know the geographic and we can reproject back to native
            ReferencedEnvelope boundsLatLon = wmsLayer.getLatLonBoundingBox();
            wmsLayer.setNativeBoundingBox(boundsLatLon.transform(wmsLayer.getNativeCRS(), true));
        }

        //fill in missing metadata
        if (wmsLayer.getTitle() == null) {
            wmsLayer.setTitle(full.getTitle());
        }
        if (wmsLayer.getDescription() == null) {
            wmsLayer.setDescription(full.getDescription());
        }
        if (wmsLayer.getAbstract() == null) {
            wmsLayer.setAbstract(full.getAbstract());
        }
        if (wmsLayer.getKeywords().isEmpty()) {
            wmsLayer.getKeywords().addAll(full.getKeywords());
        }
    }

    /**
     * Initialize a coverage object and set any unset info.
     */
    public void initCoverage(CoverageInfo cinfo) throws Exception {
        initCoverage(cinfo, null);
    }
    
    /**
     * Initialize a coverage object and set any unset info.
     */
    public void initCoverage(CoverageInfo cinfo, final String coverageName) throws Exception {
    	CoverageStoreInfo csinfo = (CoverageStoreInfo) store;
        GridCoverage2DReader reader = (GridCoverage2DReader) catalog
            	.getResourcePool().getGridCoverageReader(cinfo, GeoTools.getDefaultHints());
        if(coverageName != null) {
            reader = SingleGridCoverage2DReader.wrap(reader, coverageName);
        }
        
        initResourceInfo(cinfo);

        if (reader == null)
            throw new Exception("Unable to acquire a reader for this coverage with format: "
                    + csinfo.getFormat().getName());

        if (cinfo.getNativeCRS() == null) {
        	cinfo.setNativeCRS(reader.getCoordinateReferenceSystem());
        }

        CoordinateReferenceSystem nativeCRS = cinfo.getNativeCRS();

        if (cinfo.getSRS() == null) {
        	cinfo.setSRS(nativeCRS.getIdentifiers().toArray()[0].toString());
        }

        if (cinfo.getProjectionPolicy() == null) {
            if (nativeCRS != null && !nativeCRS.getIdentifiers().isEmpty()) {
                cinfo.setProjectionPolicy(ProjectionPolicy.REPROJECT_TO_DECLARED);
            }
            if (nativeCRS == null) {
                cinfo.setProjectionPolicy(ProjectionPolicy.FORCE_DECLARED);
            }
        }

    	if (cinfo.getLatLonBoundingBox() == null
    			&& cinfo.getNativeBoundingBox() == null) {
    		GeneralEnvelope envelope = reader.getOriginalEnvelope();

    		cinfo.setNativeBoundingBox(new ReferencedEnvelope(envelope));
    		cinfo.setLatLonBoundingBox(new ReferencedEnvelope(CoverageStoreUtils.getWGS84LonLatEnvelope(envelope)));
    	} else if (cinfo.getLatLonBoundingBox() == null) {
    		setupBounds(cinfo);
    	} else if (cinfo.getNativeBoundingBox() == null && cinfo.getNativeCRS() != null) {
    		ReferencedEnvelope boundsLatLon = cinfo.getLatLonBoundingBox();
    		cinfo.setNativeBoundingBox(boundsLatLon.transform(cinfo.getNativeCRS(), true));
    	}

        if (cinfo.getGrid() == null) {
            GridEnvelope originalRange = reader.getOriginalGridRange();
            cinfo.setGrid(new GridGeometry2D(originalRange, reader.getOriginalGridToWorld(PixelInCell.CELL_CENTER), nativeCRS));
        }
    }
    
    /**
     * Builds the default coverage contained in the current store
     * 
     * @return
     * @throws Exception
     */
    public CoverageInfo buildCoverage() throws Exception {
        return buildCoverage(null);
    }

    /**
     * Builds the default coverage contained in the current store
     * 
     * @return
     * @throws Exception
     */
    public CoverageInfo buildCoverage(String coverageName) throws Exception {
        if (store == null || !(store instanceof CoverageStoreInfo)) {
            throw new IllegalStateException("Coverage store not set.");
        }

        CoverageStoreInfo csinfo = (CoverageStoreInfo) store;
        GridCoverage2DReader reader = (GridCoverage2DReader) catalog
                .getResourcePool().getGridCoverageReader(csinfo, GeoTools.getDefaultHints());

        if (reader == null)
            throw new Exception("Unable to acquire a reader for this coverage with format: "
                    + csinfo.getFormat().getName());

        return buildCoverage(reader, coverageName, null);
    }

    /**
     * Builds a coverage from a geotools grid coverage reader.
     * @param customParameters 
     */
    public CoverageInfo buildCoverage(GridCoverage2DReader reader, Map customParameters) throws Exception {
        return buildCoverage(reader, null, customParameters);
    }
    
    /**
     * Builds a coverage from a geotools grid coverage reader.
     * @param customParameters 
     */
    public CoverageInfo buildCoverage(GridCoverage2DReader reader, String coverageName, Map customParameters) throws Exception {
        if (store == null || !(store instanceof CoverageStoreInfo)) {
            throw new IllegalStateException("Coverage store not set.");
        }
        
        // if we are dealing with a multicoverage reader, wrap to simplify code
        if (coverageName != null) {
            reader = SingleGridCoverage2DReader.wrap(reader, coverageName);
        }

        CoverageStoreInfo csinfo = (CoverageStoreInfo) store;
        CoverageInfo cinfo = catalog.getFactory().createCoverage();

        cinfo.setStore(csinfo);
        cinfo.setEnabled(true);

        WorkspaceInfo workspace = store.getWorkspace();
        NamespaceInfo namespace = catalog.getNamespaceByPrefix(workspace.getName());
        if (namespace == null) {
            namespace = catalog.getDefaultNamespace();
        }
        cinfo.setNamespace(namespace);

        GeneralEnvelope envelope = reader.getOriginalEnvelope();
        CoordinateReferenceSystem nativeCRS = envelope.getCoordinateReferenceSystem();
        cinfo.setNativeCRS(nativeCRS);

        // mind the default projection policy, Coverages do not have a flexible
        // handling as feature types, they do reproject if the native srs is set,
        // force if missing
        if (nativeCRS != null && !nativeCRS.getIdentifiers().isEmpty()) {
            cinfo.setSRS(nativeCRS.getIdentifiers().toArray()[0].toString());
            cinfo.setProjectionPolicy(ProjectionPolicy.REPROJECT_TO_DECLARED);
        }
        if (nativeCRS == null) {
            cinfo.setProjectionPolicy(ProjectionPolicy.FORCE_DECLARED);
        }

        
        cinfo.setNativeBoundingBox(new ReferencedEnvelope(envelope));
        cinfo.setLatLonBoundingBox(new ReferencedEnvelope(CoverageStoreUtils.getWGS84LonLatEnvelope(envelope)));

        GridEnvelope originalRange = reader.getOriginalGridRange();
        cinfo.setGrid(new GridGeometry2D(originalRange, reader.getOriginalGridToWorld(PixelInCell.CELL_CENTER), nativeCRS));

        // /////////////////////////////////////////////////////////////////////
        //
        // Now reading a fake small GridCoverage just to retrieve meta
        // information about bands:
        //
        // - calculating a new envelope which is just 5x5 pixels
        // - if it's a mosaic, limit the number of tiles we're going to read to one 
        //   (with time and elevation there might be hundreds of superimposed tiles)
        // - reading the GridCoverage subset
        //
        // /////////////////////////////////////////////////////////////////////
        Format format = csinfo.getFormat();
        final GridCoverage2D gc;

        final ParameterValueGroup readParams = format.getReadParameters();
        final Map parameters = CoverageUtils.getParametersKVP(readParams);
        final int minX = originalRange.getLow(0);
        final int minY = originalRange.getLow(1);
        final int width = originalRange.getSpan(0);
        final int height = originalRange.getSpan(1);
        final int maxX = minX + (width <= 5 ? width : 5);
        final int maxY = minY + (height <= 5 ? height : 5);

        // we have to be sure that we are working against a valid grid range.
        final GridEnvelope2D testRange = new GridEnvelope2D(minX, minY, maxX, maxY);

        // build the corresponding envelope
        final MathTransform gridToWorldCorner = reader.getOriginalGridToWorld(PixelInCell.CELL_CORNER);
        final GeneralEnvelope testEnvelope = CRS.transform(gridToWorldCorner, new GeneralEnvelope(testRange.getBounds()));
        testEnvelope.setCoordinateReferenceSystem(nativeCRS);

        if (customParameters != null) {
        	parameters.putAll(customParameters);
        }

        // make sure mosaics with many superimposed tiles won't blow up with 
        // a "too many open files" exception
        String maxAllowedTiles = ImageMosaicFormat.MAX_ALLOWED_TILES.getName().toString();
        if (parameters.keySet().contains(maxAllowedTiles)) {
            parameters.put(maxAllowedTiles, 1);
        }

        // Since the read sample image won't be greater than 5x5 pixels and we are limiting the
        // number of granules to 1, we may do direct read instead of using JAI
        String useJaiImageRead = ImageMosaicFormat.USE_JAI_IMAGEREAD.getName().toString();
        if (parameters.keySet().contains(useJaiImageRead)) {
            parameters.put(useJaiImageRead, false);
        }

        parameters.put(AbstractGridFormat.READ_GRIDGEOMETRY2D.getName().toString(), new GridGeometry2D(testRange, testEnvelope));

        // try to read this coverage
        gc = (GridCoverage2D) reader.read(CoverageUtils.getParameters(readParams, parameters, true));
        if (gc == null) {
            throw new Exception("Unable to acquire test coverage for format:" + format.getName());
        }

        // remove read grid geometry since it is request specific
        parameters.remove(AbstractGridFormat.READ_GRIDGEOMETRY2D.getName().toString());

        cinfo.getDimensions().addAll(getCoverageDimensions(gc.getSampleDimensions()));
        String name = gc.getName().toString();
        cinfo.setName(name);
        cinfo.setNativeCoverageName(coverageName);
        cinfo.setTitle(name);
        cinfo.setDescription(new StringBuilder("Generated from ").append(format.getName()).toString());

        // keywords
        cinfo.getKeywords().add(new Keyword("WCS"));
        cinfo.getKeywords().add(new Keyword(format.getName()));
        cinfo.getKeywords().add(new Keyword(name));

        // native format name
        cinfo.setNativeFormat(format.getName());
        cinfo.getMetadata().put("dirName", new StringBuilder(store.getName()).append("_").append(name).toString());

        // request SRS's
        if ((gc.getCoordinateReferenceSystem2D().getIdentifiers() != null)
                && !gc.getCoordinateReferenceSystem2D().getIdentifiers().isEmpty()) {
            cinfo.getRequestSRS().add(((Identifier) gc.getCoordinateReferenceSystem2D().getIdentifiers().toArray()[0]).toString());
        }

        // response SRS's
        if ((gc.getCoordinateReferenceSystem2D().getIdentifiers() != null)
                && !gc.getCoordinateReferenceSystem2D().getIdentifiers().isEmpty()) {
            cinfo.getResponseSRS().add(((Identifier) gc.getCoordinateReferenceSystem2D().getIdentifiers().toArray()[0]).toString());
        }

        // supported formats
        final List formats = CoverageStoreUtils.listDataFormats();
        for (Iterator i = formats.iterator(); i.hasNext();) {
            final Format fTmp = (Format) i.next();
            final String fName = fTmp.getName();

            if (fName.equalsIgnoreCase("WorldImage")) {
                // TODO check if coverage can encode Format
                cinfo.getSupportedFormats().add("GIF");
                cinfo.getSupportedFormats().add("PNG");
                cinfo.getSupportedFormats().add("JPEG");
                cinfo.getSupportedFormats().add("TIFF");
            } else if (fName.toLowerCase().startsWith("geotiff")) {
                // TODO check if coverage can encode Format
                cinfo.getSupportedFormats().add("GEOTIFF");
            } else {
                // TODO check if coverage can encode Format
                cinfo.getSupportedFormats().add(fName);
            }
        }

        // interpolation methods
        cinfo.setDefaultInterpolationMethod("nearest neighbor");
        cinfo.getInterpolationMethods().add("nearest neighbor");
        cinfo.getInterpolationMethods().add("bilinear");
        cinfo.getInterpolationMethods().add("bicubic");

        // read parameters (get the params again since we altered the map to optimize the 
        // coverage read)
        cinfo.getParameters().putAll(CoverageUtils.getParametersKVP(readParams));

        /// dispose coverage 
        gc.dispose(true);
        if(gc.getRenderedImage() instanceof PlanarImage) {
            ImageUtilities.disposePlanarImageChain((PlanarImage) gc.getRenderedImage());
        }

        return cinfo;
    }

    List<CoverageDimensionInfo> getCoverageDimensions(GridSampleDimension[] sampleDimensions) {

        final int length = sampleDimensions.length;
        List<CoverageDimensionInfo> dims = new ArrayList<CoverageDimensionInfo>();

        for (int i = 0; i < length; i++) {
            CoverageDimensionInfo dim = catalog.getFactory().createCoverageDimension();
            GridSampleDimension sd = sampleDimensions[i];
            String name = sd.getDescription().toString(Locale.getDefault());
            dim.setName(name);

            StringBuilder label = new StringBuilder("GridSampleDimension".intern());
            final Unit uom = sd.getUnits();

            String uName = name.toUpperCase();
            if (uom != null) {
                label.append("(".intern());
                parseUOM(label, uom);
                label.append(")".intern());
                dim.setUnit(uom.toString());
            } else if(uName.startsWith("RED") || uName.startsWith("GREEN") || uName.startsWith("BLUE")) {
                // radiance in SI
                dim.setUnit("W.m-2.Sr-1");
            }
            
            dim.setDimensionType(sd.getSampleDimensionType());

            label.append("[".intern());
            label.append(sd.getMinimumValue());
            label.append(",".intern());
            label.append(sd.getMaximumValue());
            label.append("]".intern());

            dim.setDescription(label.toString());

            if (sd.getRange() != null) {
                dim.setRange(sd.getRange());    
            }
            else {
                dim.setRange(NumberRange.create(sd.getMinimumValue(), sd.getMaximumValue()));
            }
            
            final List<Category> categories = sd.getCategories();
            if (categories != null) {
                for (Category cat : categories) {

                    if ((cat != null) && cat.getName().toString().equalsIgnoreCase("no data")) {
                        double min = cat.getRange().getMinimum();
                        double max = cat.getRange().getMaximum();

                        dim.getNullValues().add(min);
                        if (min != max) {
                            dim.getNullValues().add(max);
                        }
                    }
                }
            }
            
            dims.add(dim);
        }

        return dims;
    }
    
    public WMSLayerInfo buildWMSLayer(String layerName) throws IOException {
        return buildWMSLayer(this.store, layerName);
    }

    WMSLayerInfo buildWMSLayer(StoreInfo store, String layerName) throws IOException {
        if (store == null || !(store instanceof WMSStoreInfo)) {
            throw new IllegalStateException("WMS store not set.");
        }

        WMSLayerInfo wli = catalog.getFactory().createWMSLayer();

        wli.setName(layerName);
        wli.setNativeName(layerName);

        wli.setStore(store);
        wli.setEnabled(true);

        WorkspaceInfo workspace = store.getWorkspace();
        NamespaceInfo namespace = catalog.getNamespaceByPrefix(workspace.getName());
        if (namespace == null) {
            namespace = catalog.getDefaultNamespace();
        }
        wli.setNamespace(namespace);

        Layer layer = wli.getWMSLayer(null);

        // try to get the native SRS -> we use the bounding boxes, GeoServer will publish all of the
        // supported SRS in the root, if we use getSRS() we'll get them all
        for (String srs : layer.getBoundingBoxes().keySet()) {
            try {
                CoordinateReferenceSystem crs = CRS.decode(srs);
                wli.setSRS(srs);
                wli.setNativeCRS(crs);
            } catch (Exception e) {
                LOGGER.log(Level.INFO, "Skipping " + srs
                        + " definition, it was not recognized by the referencing subsystem");
            }
        }
        
        // fall back on WGS84 if necessary, and handle well known WMS CRS codes
        String srs = wli.getSRS();
        try {
            if (srs == null || srs.equals("CRS:84")) {
                wli.setSRS("EPSG:4326");
                srs = "EPSG:4326";
                wli.setNativeCRS(CRS.decode("EPSG:4326"));
            } else if(srs.equals("CRS:83")) {
                wli.setSRS("EPSG:4269");
                srs = "EPSG:4269";
                wli.setNativeCRS(CRS.decode("EPSG:4269"));
            } else if(srs.equals("CRS:27")) {
                wli.setSRS("EPSG:4267");
                srs = "EPSG:4267";
                wli.setNativeCRS(CRS.decode("EPSG:4267"));
            }
        } catch(Exception e) {
            throw (IOException) new IOException("Failed to compute the layer declared SRS code").initCause(e);
        }
        wli.setProjectionPolicy(ProjectionPolicy.FORCE_DECLARED);

        // try to grab the envelope
        GeneralEnvelope envelope = layer.getEnvelope(wli.getNativeCRS());
        if (envelope != null) {
            ReferencedEnvelope re = new ReferencedEnvelope(envelope.getMinimum(0), envelope
                    .getMaximum(0), envelope.getMinimum(1), envelope.getMaximum(1), wli
                    .getNativeCRS());
            wli.setNativeBoundingBox(re);
        }
        CRSEnvelope llbbox = layer.getLatLonBoundingBox();
        if (llbbox != null) {
            ReferencedEnvelope re = new ReferencedEnvelope(llbbox.getMinX(), llbbox.getMaxX(),
                    llbbox.getMinY(), llbbox.getMaxY(), DefaultGeographicCRS.WGS84);
            wli.setLatLonBoundingBox(re);
        } else if (wli.getNativeBoundingBox() != null) {
            try {
                wli.setLatLonBoundingBox(wli.getNativeBoundingBox().transform(
                        DefaultGeographicCRS.WGS84, true));
            } catch (Exception e) {
                LOGGER.log(Level.INFO, "Could not transform native bbox into a lat/lon one", e);
            }
        }

        // reflect all the metadata that we can grab
        wli.setAbstract(layer.get_abstract());
        wli.setDescription(layer.get_abstract());
        wli.setTitle(layer.getTitle());
        if (layer.getKeywords() != null) {
            for (String kw : layer.getKeywords()) {
                if(kw != null){
                    wli.getKeywords().add(new Keyword(kw));
                }
            }
        }

        // strip off the prefix if we're cascading from a server that does add them
        String published = wli.getName();
        if (published.contains(":")) {
            wli.setName(published.substring(published.lastIndexOf(':') + 1));
        }

        return wli;
    }
    
    private boolean axisFlipped(Version version, String srsName) {
        if(version.compareTo(new Version("1.3.0")) < 0) {
            // aah, sheer simplicity
            return false;
        } else {
            // gah, hell gates breaking loose
            if(srsName.startsWith("EPSG:")) {
                try {
                    String epsgNative =  "urn:x-ogc:def:crs:EPSG:".concat(srsName.substring(5));
                    return CRS.getAxisOrder(CRS.decode(epsgNative)) == AxisOrder.NORTH_EAST;
                } catch(Exception e) {
                    LOGGER.log(Level.WARNING, "Failed to determine axis order for " 
                            + srsName + ", assuming east/north", e);
                    return false;
                }
            } else {
                // CRS or AUTO, none of them is flipped so far
                return false;
            }
        }
    }

    void parseUOM(StringBuilder label, Unit uom) {
        String uomString = uom.toString();
        uomString = uomString.replaceAll("\u00B2", "^2");
        uomString = uomString.replaceAll("\u00B3", "^3");
        uomString = uomString.replaceAll("\u212B", "A");
        uomString = uomString.replaceAll("�", "");
        label.append(uomString);
    }

    /**
     * Builds a layer for a feature type.
     * <p>
     * The resulting object is not added to the catalog, it must be done by the calling code after
     * the fact.
     * </p>
     */
    public LayerInfo buildLayer(FeatureTypeInfo featureType) throws IOException {
        // also create a layer for the feautre type
        LayerInfo layer = buildLayer((ResourceInfo) featureType);

        StyleInfo style = getDefaultStyle(featureType);
        layer.setDefaultStyle(style);

        return layer;
    }

    /**
     * Builds a layer for a coverage.
     * <p>
     * The resulting object is not added to the catalog, it must be done by the calling code after
     * the fact.
     * </p>
     */
    public LayerInfo buildLayer(CoverageInfo coverage) throws IOException {
        LayerInfo layer = buildLayer((ResourceInfo) coverage);

        layer.setDefaultStyle(getDefaultStyle(coverage));

        return layer;
    }

    /**
     * Builds a layer wrapping a WMS layer resource
     * <p>
     * The resulting object is not added to the catalog, it must be done by the calling code after
     * the fact.
     * </p>
     */
    public LayerInfo buildLayer(WMSLayerInfo wms) throws IOException {
        LayerInfo layer = buildLayer((ResourceInfo) wms);
        
        layer.setDefaultStyle(getDefaultStyle(wms));
        
        return layer;
    }

    /**
     * Returns the default style for the specified resource, or null if the layer is vector and
     * geometryless
     * 
     * @param resource
     * @return
     * @throws IOException
     */
    public StyleInfo getDefaultStyle(ResourceInfo resource) throws IOException {
        // raster wise, only one style
        if (resource instanceof CoverageInfo || resource instanceof WMSLayerInfo)
            return catalog.getStyleByName(StyleInfo.DEFAULT_RASTER);

        // for vectors we depend on the the nature of the default geometry
        String styleName;
        FeatureTypeInfo featureType = (FeatureTypeInfo) resource;
        if (featureType.getFeatureType() == null) {
            return null;
        }
        GeometryDescriptor gd = featureType.getFeatureType().getGeometryDescriptor();
        if (gd == null) {
            return null;
        }

        Class gtype = gd.getType().getBinding();
        if (Point.class.isAssignableFrom(gtype) || MultiPoint.class.isAssignableFrom(gtype)) {
            styleName = StyleInfo.DEFAULT_POINT;
        } else if (LineString.class.isAssignableFrom(gtype)
                || MultiLineString.class.isAssignableFrom(gtype)) {
            styleName = StyleInfo.DEFAULT_LINE;
        } else if (Polygon.class.isAssignableFrom(gtype)
                || MultiPolygon.class.isAssignableFrom(gtype)) {
            styleName = StyleInfo.DEFAULT_POLYGON;
        } else {
            // fall back to point
            styleName = StyleInfo.DEFAULT_POINT;
        }

        return catalog.getStyleByName(styleName);
    }

    public LayerInfo buildLayer(ResourceInfo resource) {
        LayerInfo layer = catalog.getFactory().createLayer();
        layer.setResource(resource);
        layer.setName(resource.getName());
        layer.setEnabled(true);

        // setup the layer type
        if (layer.getResource() instanceof FeatureTypeInfo) {
            layer.setType(PublishedType.VECTOR);
        } else if (layer.getResource() instanceof CoverageInfo) {
            layer.setType(PublishedType.RASTER);
        } else if (layer.getResource() instanceof WMSLayerInfo) {
            layer.setType(PublishedType.WMS);
        }

        return layer;
    }

    /**
     * Calculates the bounds of a layer group specifying a particular crs.
     */
    public void calculateLayerGroupBounds(LayerGroupInfo layerGroup, CoordinateReferenceSystem crs)
            throws Exception {
        LayerGroupHelper helper = new LayerGroupHelper(layerGroup);
        helper.calculateBounds(crs);
    }

    /**
     * Calculates the bounds of a layer group by aggregating the bounds of each layer.
     */
    public void calculateLayerGroupBounds(LayerGroupInfo layerGroup) throws Exception {
        LayerGroupHelper helper = new LayerGroupHelper(layerGroup);
        helper.calculateBounds();
    }

    //
    // remove methods
    //

    /**
     * Removes a workspace from the catalog.
     * <p>
     * The <tt>recursive</tt> flag controls whether objects linked to the workspace such as stores
     * should also be deleted.
     * </p>
     */
    public void removeWorkspace(WorkspaceInfo workspace, boolean recursive) {
        if (recursive) {
            workspace.accept(new CascadeDeleteVisitor(catalog));
        } else {
            catalog.remove(workspace);
        }
    }

    /**
     * Removes a store from the catalog.
     * <p>
     * The <tt>recursive</tt> flag controls whether objects linked to the store such as resources
     * should also be deleted.
     * </p>
     */
    public void removeStore(StoreInfo store, boolean recursive) {
        if (recursive) {
            store.accept(new CascadeDeleteVisitor(catalog));
        } else {
            catalog.remove(store);
        }
    }

    /**
     * Removes a resource from the catalog.
     * <p>
     * The <tt>recursive</tt> flag controls whether objects linked to the resource such as layers
     * should also be deleted.
     * </p>
     */
    public void removeResource(ResourceInfo resource, boolean recursive) {
        if (recursive) {
            resource.accept(new CascadeDeleteVisitor(catalog));
        } else {
            catalog.remove(resource);
        }
    }

    /**
     * Reattaches a serialized {@link StoreInfo} to the catalog
     */
    public void attach(StoreInfo storeInfo) {
        storeInfo = ModificationProxy.unwrap(storeInfo);
        ((StoreInfoImpl) storeInfo).setCatalog(catalog);
    }

    /**
     * Reattaches a serialized {@link ResourceInfo} to the catalog
     */
    public void attach(ResourceInfo resourceInfo) {
        resourceInfo = ModificationProxy.unwrap(resourceInfo);
        ((ResourceInfoImpl) resourceInfo).setCatalog(catalog);
    }

    /**
     * Reattaches a serialized {@link LayerInfo} to the catalog
     */
    public void attach(LayerInfo layerInfo) {
        attach(layerInfo.getResource());
    }

    /**
     * Reattaches a serialized {@link MapInfo} to the catalog
     */
    public void attach(MapInfo mapInfo) {
        // hmmm... mapInfo has a list of layers inside? Not names?
        for (LayerInfo layer : mapInfo.getLayers()) {
            attach(layer);
        }
    }

    /**
     * Reattaches a serialized {@link LayerGroupInfo} to the catalog
     */
    public void attach(LayerGroupInfo groupInfo) {
        if (groupInfo.getRootLayer() != null) {
            attach(groupInfo.getRootLayer());
        }
        
        if (groupInfo.getRootLayerStyle() != null) {
            attach(groupInfo.getRootLayerStyle());            
        }
        
        for (PublishedInfo p : groupInfo.getLayers()) {
            if (p instanceof LayerInfo) {
                attach((LayerInfo) p);
            } else {
                attach((LayerGroupInfo) p);                
            }
        }
        
        for (StyleInfo style : groupInfo.getStyles()) {
            if (style != null)
                attach(style);
        }
    }

    /**
     * Reattaches a serialized {@link StyleInfo} to the catalog
     */
    public void attach(StyleInfo styleInfo) {
        styleInfo = ModificationProxy.unwrap(styleInfo);
        ((StyleInfoImpl) styleInfo).setCatalog(catalog);
    }

    /**
     * Reattaches a serialized {@link NamespaceInfo} to the catalog
     */
    public void attach(NamespaceInfo nsInfo) {
        // nothing to do
    }

    /**
     * Reattaches a serialized {@link WorkspaceInfo} to the catalog
     */
    public void attach(WorkspaceInfo wsInfo) {
        // nothing to do
    }
    
    /**
     * Extracts the AttributeTypeInfo by copying them from the specified feature type.
     * @param ft The schema to be harvested
     * @param info The optional feature type info from which all the attributes belong to
     * @return
     */
    public List<AttributeTypeInfo> getAttributes(FeatureType ft, FeatureTypeInfo info) {
        List<AttributeTypeInfo> attributes = new ArrayList<AttributeTypeInfo>();
        for (PropertyDescriptor pd : ft.getDescriptors()) {
            AttributeTypeInfo att = catalog.getFactory().createAttribute();
            att.setFeatureType(info);
            att.setName(pd.getName().getLocalPart());
            att.setMinOccurs(pd.getMinOccurs());
            att.setMaxOccurs(pd.getMaxOccurs());
            att.setNillable(pd.isNillable());
            att.setBinding(pd.getType().getBinding());
            int length = FeatureTypes.getFieldLength((AttributeDescriptor) pd);
            if(length > 0) {
                att.setLength(length);
            }
            attributes.add(att);
        }
        
        return attributes;
    }
}
