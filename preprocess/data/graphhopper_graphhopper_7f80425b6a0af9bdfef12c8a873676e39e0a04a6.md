Refactoring Types: ['Move Method', 'Move Attribute']
r.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper;

import com.graphhopper.reader.DataReader;
import com.graphhopper.reader.OSMReader;
import com.graphhopper.reader.dem.CGIARProvider;
import com.graphhopper.reader.dem.ElevationProvider;
import com.graphhopper.reader.dem.SRTMProvider;
import com.graphhopper.routing.*;
import com.graphhopper.routing.ch.PrepareContractionHierarchies;
import com.graphhopper.routing.util.*;
import com.graphhopper.storage.*;
import com.graphhopper.storage.index.*;
import com.graphhopper.util.*;
import com.graphhopper.util.shapes.GHPoint;

import java.io.File;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.atomic.AtomicLong;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Easy to use access point to configure import and (offline) routing.
 * <p/>
 * @author Peter Karich
 * @see GraphHopperAPI
 */
public class GraphHopper implements GraphHopperAPI
{
    private final Logger logger = LoggerFactory.getLogger(getClass());
    // for graph:
    private GraphStorage graph;
    private EncodingManager encodingManager;
    private int defaultSegmentSize = -1;
    private String ghLocation = "";
    private DAType dataAccessType = DAType.RAM_STORE;
    private boolean sortGraph = false;
    boolean removeZipped = true;
    private boolean elevation = false;
    private LockFactory lockFactory = new NativeFSLockFactory();
    private final String fileLockName = "gh.lock";
    private boolean allowWrites = true;
    boolean enableInstructions = true;
    private boolean fullyLoaded = false;
    // for routing
    private double defaultWeightLimit = Double.MAX_VALUE;
    private boolean simplifyResponse = true;
    private TraversalMode traversalMode = TraversalMode.NODE_BASED;
    private RoutingAlgorithmFactory algoFactory;
    // for index
    private LocationIndex locationIndex;
    private int preciseIndexResolution = 300;
    private int maxRegionSearch = 4;
    // for prepare
    private int minNetworkSize = 200;
    private int minOneWayNetworkSize = 0;
    // for CH prepare    
    private boolean doPrepare = true;
    private boolean chEnabled = true;
    private String chWeightingStr = "fastest";
    private int periodicUpdates = -1;
    private int lazyUpdates = -1;
    private int neighborUpdates = -1;
    private double logMessages = -1;
    // for OSM import
    private String osmFile;
    private double osmReaderWayPointMaxDistance = 1;
    private int workerThreads = -1;
    private boolean calcPoints = true;
    // utils    
    private final TranslationMap trMap = new TranslationMap().doImport();
    private ElevationProvider eleProvider = ElevationProvider.NOOP;
    private final AtomicLong visitedSum = new AtomicLong(0);

    public GraphHopper()
    {
    }

    /**
     * For testing only
     */
    protected GraphHopper loadGraph( GraphStorage g )
    {
        this.graph = g;
        fullyLoaded = true;
        initLocationIndex();
        return this;
    }

    /**
     * Specify which vehicles can be read by this GraphHopper instance. An encoding manager defines
     * how data from every vehicle is written (und read) into edges of the graph.
     */
    public GraphHopper setEncodingManager( EncodingManager em )
    {
        ensureNotLoaded();
        this.encodingManager = em;
        if (em.needsTurnCostsSupport())
            traversalMode = TraversalMode.EDGE_BASED_2DIR;

        return this;
    }

    FlagEncoder getDefaultVehicle()
    {
        if (encodingManager == null)
        {
            throw new IllegalStateException("No encoding manager specified or loaded");
        }

        return encodingManager.fetchEdgeEncoders().get(0);
    }

    public EncodingManager getEncodingManager()
    {
        return encodingManager;
    }

    public GraphHopper setElevationProvider( ElevationProvider eleProvider )
    {
        if (eleProvider == null || eleProvider == ElevationProvider.NOOP)
            setElevation(false);
        else
            setElevation(true);
        this.eleProvider = eleProvider;
        return this;
    }

    /**
     * Threads for data reading.
     */
    protected int getWorkerThreads()
    {
        return workerThreads;
    }

    /**
     * Return maximum distance (in meter) to reduce points via douglas peucker while OSM import.
     */
    protected double getWayPointMaxDistance()
    {
        return osmReaderWayPointMaxDistance;
    }

    /**
     * This parameter specifies how to reduce points via douglas peucker while OSM import. Higher
     * value means more details, unit is meter. Default is 1. Disable via 0.
     */
    public GraphHopper setWayPointMaxDistance( double wayPointMaxDistance )
    {
        this.osmReaderWayPointMaxDistance = wayPointMaxDistance;
        return this;
    }

    /**
     * Sets the default traversal mode used for the algorithms and preparation.
     */
    public GraphHopper setTraversalMode( TraversalMode traversalMode )
    {
        this.traversalMode = traversalMode;
        return this;
    }

    public TraversalMode getTraversalMode()
    {
        return traversalMode;
    }

    /**
     * Configures the underlying storage and response to be used on a well equipped server. Result
     * also optimized for usage in the web module i.e. try reduce network IO.
     */
    public GraphHopper forServer()
    {
        setSimplifyResponse(true);
        return setInMemory();
    }

    /**
     * Configures the underlying storage to be used on a Desktop computer or within another Java
     * application with enough RAM but no network latency.
     */
    public GraphHopper forDesktop()
    {
        setSimplifyResponse(false);
        return setInMemory();
    }

    /**
     * Configures the underlying storage to be used on a less powerful machine like Android or
     * Raspberry Pi with only few MB of RAM.
     */
    public GraphHopper forMobile()
    {
        setSimplifyResponse(false);
        return setMemoryMapped();
    }

    /**
     * Precise location resolution index means also more space (disc/RAM) could be consumed and
     * probably slower query times, which would be e.g. not suitable for Android. The resolution
     * specifies the tile width (in meter).
     */
    public GraphHopper setPreciseIndexResolution( int precision )
    {
        ensureNotLoaded();
        preciseIndexResolution = precision;
        return this;
    }

    public void setMinNetworkSize( int minNetworkSize, int minOneWayNetworkSize )
    {
        this.minNetworkSize = minNetworkSize;
        this.minOneWayNetworkSize = minOneWayNetworkSize;
    }

    /**
     * This method call results in an in-memory graph.
     */
    public GraphHopper setInMemory()
    {
        ensureNotLoaded();
        dataAccessType = DAType.RAM_STORE;
        return this;
    }

    /**
     * Only valid option for in-memory graph and if you e.g. want to disable store on flush for unit
     * tests. Specify storeOnFlush to true if you want that existing data will be loaded FROM disc
     * and all in-memory data will be flushed TO disc after flush is called e.g. while OSM import.
     * <p/>
     * @param storeOnFlush true by default
     */
    public GraphHopper setStoreOnFlush( boolean storeOnFlush )
    {
        ensureNotLoaded();
        if (storeOnFlush)
            dataAccessType = DAType.RAM_STORE;
        else
            dataAccessType = DAType.RAM;
        return this;
    }

    /**
     * Enable memory mapped configuration if not enough memory is available on the target platform.
     */
    public GraphHopper setMemoryMapped()
    {
        ensureNotLoaded();
        dataAccessType = DAType.MMAP;
        return this;
    }

    /**
     * Not yet stable enough to offer it for everyone
     */
    private GraphHopper setUnsafeMemory()
    {
        ensureNotLoaded();
        dataAccessType = DAType.UNSAFE_STORE;
        return this;
    }

    /**
     * Enables the use of contraction hierarchies to reduce query times. Enabled by default.
     * <p/>
     * @param weighting can be "fastest", "shortest" or your own weight-calculation type.
     * @see #setCHEnable(boolean)
     */
    public GraphHopper setCHWeighting( String weighting )
    {
        ensureNotLoaded();
        chWeightingStr = weighting;
        return this;
    }

    public String getCHWeighting()
    {
        return chWeightingStr;
    }

    /**
     * Disables the "CH-preparation" preparation only. Use only if you know what you do. To disable
     * the full usage of CH use setCHEnable(false) instead.
     */
    public GraphHopper setDoPrepare( boolean doPrepare )
    {
        this.doPrepare = doPrepare;
        return this;
    }

    /**
     * Enables or disables contraction hierarchies (CH). This speed-up mode is enabled by default.
     * Disabling CH is only recommended for short routes or in combination with
     * setDefaultWeightLimit and called flexibility mode
     * <p/>
     * @see #setDefaultWeightLimit(double)
     */
    public GraphHopper setCHEnable( boolean enable )
    {
        ensureNotLoaded();
        algoFactory = null;
        chEnabled = enable;
        return this;
    }

    /**
     * This methods stops the algorithm from searching further if the resulting path would go over
     * specified weight, important if CH is disabled. The unit is defined by the used weighting
     * created from createWeighting, e.g. distance for shortest or seconds for the standard
     * FastestWeighting implementation.
     */
    public void setDefaultWeightLimit( double defaultWeightLimit )
    {
        this.defaultWeightLimit = defaultWeightLimit;
    }

    public boolean isCHEnabled()
    {
        return chEnabled;
    }

    /**
     * @return true if storing and fetching elevation data is enabled. Default is false
     */
    public boolean hasElevation()
    {
        return elevation;
    }

    /**
     * Enable storing and fetching elevation data. Default is false
     */
    public GraphHopper setElevation( boolean includeElevation )
    {
        this.elevation = includeElevation;
        return this;
    }

    /**
     * This method specifies if the import should include way names to be able to return
     * instructions for a route.
     */
    public GraphHopper setEnableInstructions( boolean b )
    {
        ensureNotLoaded();
        enableInstructions = b;
        return this;
    }

    /**
     * This methods enables gps point calculation. If disabled only distance will be calculated.
     */
    public GraphHopper setEnableCalcPoints( boolean b )
    {
        calcPoints = b;
        return this;
    }

    /**
     * This method specifies if the returned path should be simplified or not, via douglas-peucker
     * or similar algorithm.
     */
    private GraphHopper setSimplifyResponse( boolean doSimplify )
    {
        this.simplifyResponse = doSimplify;
        return this;
    }

    /**
     * Sets the graphhopper folder.
     */
    public GraphHopper setGraphHopperLocation( String ghLocation )
    {
        ensureNotLoaded();
        if (ghLocation == null)
            throw new IllegalArgumentException("graphhopper location cannot be null");

        this.ghLocation = ghLocation;
        return this;
    }

    public String getGraphHopperLocation()
    {
        return ghLocation;
    }

    /**
     * This file can be an osm xml (.osm), a compressed xml (.osm.zip or .osm.gz) or a protobuf file
     * (.pbf).
     */
    public GraphHopper setOSMFile( String osmFileStr )
    {
        ensureNotLoaded();
        if (Helper.isEmpty(osmFileStr))
            throw new IllegalArgumentException("OSM file cannot be empty.");

        osmFile = osmFileStr;
        return this;
    }

    public String getOSMFile()
    {
        return osmFile;
    }

    /**
     * The underlying graph used in algorithms.
     * <p/>
     * @throws IllegalStateException if graph is not instantiated.
     */
    public GraphStorage getGraph()
    {
        if (graph == null)
            throw new IllegalStateException("Graph not initialized");

        return graph;
    }

    public void setGraph( GraphStorage graph )
    {
        this.graph = graph;
    }

    protected void setLocationIndex( LocationIndex locationIndex )
    {
        this.locationIndex = locationIndex;
    }

    /**
     * The location index created from the graph.
     * <p/>
     * @throws IllegalStateException if index is not initialized
     */
    public LocationIndex getLocationIndex()
    {
        if (locationIndex == null)
            throw new IllegalStateException("Location index not initialized");

        return locationIndex;
    }

    /**
     * Sorts the graph which requires more RAM while import. See #12
     */
    public GraphHopper setSortGraph( boolean sortGraph )
    {
        ensureNotLoaded();
        this.sortGraph = sortGraph;
        return this;
    }

    /**
     * Specifies if it is allowed for GraphHopper to write. E.g. for read only filesystems it is not
     * possible to create a lock file and so we can avoid write locks.
     */
    public GraphHopper setAllowWrites( boolean allowWrites )
    {
        this.allowWrites = allowWrites;
        return this;
    }

    public boolean isAllowWrites()
    {
        return allowWrites;
    }

    public TranslationMap getTranslationMap()
    {
        return trMap;
    }

    /**
     * Reads configuration from a CmdArgs object. Which can be manually filled, or via main(String[]
     * args) ala CmdArgs.read(args) or via configuration file ala
     * CmdArgs.readFromConfig("config.properties", "graphhopper.config")
     */
    public GraphHopper init( CmdArgs args )
    {
        args = CmdArgs.readFromConfigAndMerge(args, "config", "graphhopper.config");
        String tmpOsmFile = args.get("osmreader.osm", "");
        if (!Helper.isEmpty(tmpOsmFile))
            osmFile = tmpOsmFile;

        String graphHopperFolder = args.get("graph.location", "");
        if (Helper.isEmpty(graphHopperFolder) && Helper.isEmpty(ghLocation))
        {
            if (Helper.isEmpty(osmFile))
                throw new IllegalArgumentException("You need to specify an OSM file.");

            graphHopperFolder = Helper.pruneFileEnd(osmFile) + "-gh";
        }

        // graph
        setGraphHopperLocation(graphHopperFolder);
        defaultSegmentSize = args.getInt("graph.dataaccess.segmentSize", defaultSegmentSize);

        String graphDATypeStr = args.get("graph.dataaccess", "RAM_STORE");
        dataAccessType = DAType.fromString(graphDATypeStr);

        sortGraph = args.getBool("graph.doSort", sortGraph);
        removeZipped = args.getBool("graph.removeZipped", removeZipped);
        int bytesForFlags = args.getInt("graph.bytesForFlags", 4);
        if (args.get("graph.locktype", "native").equals("simple"))
            lockFactory = new SimpleFSLockFactory();
        else
            lockFactory = new NativeFSLockFactory();

        // elevation
        String eleProviderStr = args.get("graph.elevation.provider", "noop").toLowerCase();
        boolean eleCalcMean = args.getBool("graph.elevation.calcmean", false);
        String cacheDirStr = args.get("graph.elevation.cachedir", "");
        String baseURL = args.get("graph.elevation.baseurl", "");
        DAType elevationDAType = DAType.fromString(args.get("graph.elevation.dataaccess", "MMAP"));
        ElevationProvider tmpProvider = ElevationProvider.NOOP;
        if (eleProviderStr.equalsIgnoreCase("srtm"))
        {
            tmpProvider = new SRTMProvider();
        } else if (eleProviderStr.equalsIgnoreCase("cgiar"))
        {
            CGIARProvider cgiarProvider = new CGIARProvider();
            cgiarProvider.setAutoRemoveTemporaryFiles(args.getBool("graph.elevation.cgiar.clear", true));
            tmpProvider = cgiarProvider;
        }

        tmpProvider.setCalcMean(eleCalcMean);
        tmpProvider.setCacheDir(new File(cacheDirStr));
        if (!baseURL.isEmpty())
            tmpProvider.setBaseURL(baseURL);
        tmpProvider.setDAType(elevationDAType);
        setElevationProvider(tmpProvider);

        // optimizable prepare
        minNetworkSize = args.getInt("prepare.minNetworkSize", minNetworkSize);
        minOneWayNetworkSize = args.getInt("prepare.minOneWayNetworkSize", minOneWayNetworkSize);

        // prepare CH
        doPrepare = args.getBool("prepare.doPrepare", doPrepare);
        String tmpCHWeighting = args.get("prepare.chWeighting", "fastest");
        chEnabled = "fastest".equals(tmpCHWeighting) || "shortest".equals(tmpCHWeighting);
        if (chEnabled)
            setCHWeighting(tmpCHWeighting);

        periodicUpdates = args.getInt("prepare.updates.periodic", periodicUpdates);
        lazyUpdates = args.getInt("prepare.updates.lazy", lazyUpdates);
        neighborUpdates = args.getInt("prepare.updates.neighbor", neighborUpdates);
        logMessages = args.getDouble("prepare.logmessages", logMessages);

        // osm import
        osmReaderWayPointMaxDistance = args.getDouble("osmreader.wayPointMaxDistance", osmReaderWayPointMaxDistance);
        String flagEncoders = args.get("graph.flagEncoders", "");
        if (!flagEncoders.isEmpty())
            setEncodingManager(new EncodingManager(flagEncoders, bytesForFlags));

        workerThreads = args.getInt("osmreader.workerThreads", workerThreads);
        enableInstructions = args.getBool("osmreader.instructions", enableInstructions);

        // index
        preciseIndexResolution = args.getInt("index.highResolution", preciseIndexResolution);
        maxRegionSearch = args.getInt("index.maxRegionSearch", maxRegionSearch);

        // routing
        defaultWeightLimit = args.getDouble("routing.defaultWeightLimit", defaultWeightLimit);
        return this;
    }

    private void printInfo()
    {
        logger.info("version " + Constants.VERSION + "|" + Constants.BUILD_DATE + " (" + Constants.getVersions() + ")");
        if (graph != null)
            logger.info("graph " + graph.toString() + ", details:" + graph.toDetailsString());
    }

    /**
     * Imports provided data from disc and creates graph. Depending on the settings the resulting
     * graph will be stored to disc so on a second call this method will only load the graph from
     * disc which is usually a lot faster.
     */
    public GraphHopper importOrLoad()
    {
        if (!load(ghLocation))
        {
            printInfo();
            process(ghLocation);
        } else
        {
            printInfo();
        }
        return this;
    }

    /**
     * Creates the graph from OSM data.
     */
    private GraphHopper process( String graphHopperLocation )
    {
        setGraphHopperLocation(graphHopperLocation);
        Lock lock = null;
        try
        {
            if (graph.getDirectory().getDefaultType().isStoring())
            {
                lockFactory.setLockDir(new File(graphHopperLocation));
                lock = lockFactory.create(fileLockName, true);
                if (!lock.tryLock())
                    throw new RuntimeException("To avoid multiple writers we need to obtain a write lock but it failed. In " + graphHopperLocation, lock.getObtainFailedReason());
            }

            try
            {
                importData();
                graph.getProperties().put("osmreader.import.date", formatDateTime(new Date()));
            } catch (IOException ex)
            {
                throw new RuntimeException("Cannot parse OSM file " + getOSMFile(), ex);
            }
            cleanUp();
            optimize();
            postProcessing();
            flush();
        } finally
        {
            if (lock != null)
                lock.release();
        }
        return this;
    }

    protected DataReader importData() throws IOException
    {
        ensureWriteAccess();
        if (graph == null)
            throw new IllegalStateException("Load graph before importing OSM data");

        if (osmFile == null)
            throw new IllegalStateException("Couldn't load from existing folder: " + ghLocation
                    + " but also cannot import from OSM file as it wasn't specified!");

        encodingManager.setEnableInstructions(enableInstructions);
        DataReader reader = createReader(graph);
        logger.info("using " + graph.toString() + ", memory:" + Helper.getMemInfo());
        reader.readGraph();
        return reader;
    }

    protected DataReader createReader( GraphStorage tmpGraph )
    {
        return initOSMReader(new OSMReader(tmpGraph));
    }

    protected OSMReader initOSMReader( OSMReader reader )
    {
        if (osmFile == null)
            throw new IllegalArgumentException("No OSM file specified");

        logger.info("start creating graph from " + osmFile);
        File osmTmpFile = new File(osmFile);
        return reader.setOSMFile(osmTmpFile).
                setElevationProvider(eleProvider).
                setWorkerThreads(workerThreads).
                setEncodingManager(encodingManager).
                setWayPointMaxDistance(osmReaderWayPointMaxDistance);
    }

    /**
     * Opens existing graph.
     * <p/>
     * @param graphHopperFolder is the folder containing graphhopper files (which can be compressed
     * too)
     */
    @Override
    public boolean load( String graphHopperFolder )
    {
        if (Helper.isEmpty(graphHopperFolder))
            throw new IllegalStateException("graphHopperLocation is not specified. call init before");

        if (fullyLoaded)
            throw new IllegalStateException("graph is already successfully loaded");

        if (graphHopperFolder.endsWith("-gh"))
        {
            // do nothing  
        } else if (graphHopperFolder.endsWith(".osm") || graphHopperFolder.endsWith(".xml"))
        {
            throw new IllegalArgumentException("To import an osm file you need to use importOrLoad");
        } else if (!graphHopperFolder.contains("."))
        {
            if (new File(graphHopperFolder + "-gh").exists())
                graphHopperFolder += "-gh";
        } else
        {
            File compressed = new File(graphHopperFolder + ".ghz");
            if (compressed.exists() && !compressed.isDirectory())
            {
                try
                {
                    new Unzipper().unzip(compressed.getAbsolutePath(), graphHopperFolder, removeZipped);
                } catch (IOException ex)
                {
                    throw new RuntimeException("Couldn't extract file " + compressed.getAbsolutePath()
                            + " to " + graphHopperFolder, ex);
                }
            }
        }

        setGraphHopperLocation(graphHopperFolder);

        if (encodingManager == null)
            setEncodingManager(EncodingManager.create(ghLocation));

        if (!allowWrites && dataAccessType.isMMap())
            dataAccessType = DAType.MMAP_RO;

        GHDirectory dir = new GHDirectory(ghLocation, dataAccessType);
        if (chEnabled)
            graph = new LevelGraphStorage(dir, encodingManager, hasElevation());
        else if (encodingManager.needsTurnCostsSupport())
            graph = new GraphHopperStorage(dir, encodingManager, hasElevation(), new TurnCostExtension());
        else
            graph = new GraphHopperStorage(dir, encodingManager, hasElevation());

        graph.setSegmentSize(defaultSegmentSize);

        Lock lock = null;
        try
        {
            // create locks only if writes are allowed, if they are not allowed a lock cannot be created 
            // (e.g. on a read only filesystem locks would fail)
            if (graph.getDirectory().getDefaultType().isStoring() && isAllowWrites())
            {
                lockFactory.setLockDir(new File(ghLocation));
                lock = lockFactory.create(fileLockName, false);
                if (!lock.tryLock())
                    throw new RuntimeException("To avoid reading partial data we need to obtain the read lock but it failed. In " + ghLocation, lock.getObtainFailedReason());
            }

            if (!graph.loadExisting())
                return false;

            postProcessing();
            fullyLoaded = true;
            return true;
        } finally
        {
            if (lock != null)
                lock.release();
        }
    }

    public RoutingAlgorithmFactory getAlgorithmFactory()
    {
        if (algoFactory == null)
            this.algoFactory = new RoutingAlgorithmFactorySimple();

        return algoFactory;
    }

    public void setAlgorithmFactory( RoutingAlgorithmFactory algoFactory )
    {
        this.algoFactory = algoFactory;
    }

    /**
     * Sets EncodingManager, does the preparation and creates the locationIndex
     */
    protected void postProcessing()
    {
        initLocationIndex();
        if (chEnabled)
            algoFactory = createPrepare();
        else
            algoFactory = new RoutingAlgorithmFactorySimple();

        if (!isPrepared())
            prepare();
    }

    private boolean isPrepared()
    {
        return "true".equals(graph.getProperties().get("prepare.done"));
    }

    protected RoutingAlgorithmFactory createPrepare()
    {
        FlagEncoder defaultVehicle = getDefaultVehicle();
        Weighting weighting = createWeighting(new WeightingMap(chWeightingStr), defaultVehicle);
        PrepareContractionHierarchies tmpPrepareCH = new PrepareContractionHierarchies(new GHDirectory("", DAType.RAM_INT),
                (LevelGraph) graph, defaultVehicle, weighting, traversalMode);
        tmpPrepareCH.setPeriodicUpdates(periodicUpdates).
                setLazyUpdates(lazyUpdates).
                setNeighborUpdates(neighborUpdates).
                setLogMessages(logMessages);

        return tmpPrepareCH;
    }

    /**
     * Based on the weightingParameters and the specified vehicle a Weighting instance can be
     * created. Note that all URL parameters are available in the weightingParameters as String if
     * you use the GraphHopper Web module.
     * <p/>
     * @param weightingMap all parameters influencing the weighting. E.g. parameters coming via
     * GHRequest.getHints or directly via "&api.xy=" from the URL of the web UI
     * @param encoder the required vehicle
     * @return the weighting to be used for route calculation
     * @see WeightingMap
     */
    public Weighting createWeighting( WeightingMap weightingMap, FlagEncoder encoder )
    {
        String weighting = weightingMap.getWeighting();
        Weighting result;

        if ("shortest".equalsIgnoreCase(weighting))
        {
            result = new ShortestWeighting();
        } else if ("fastest".equalsIgnoreCase(weighting) || weighting.isEmpty())
        {
            if (encoder.supports(PriorityWeighting.class))
                result = new PriorityWeighting(encoder);
            else
                result = new FastestWeighting(encoder);
        } else
        {
            throw new UnsupportedOperationException("weighting " + weighting + " not supported");
        }
        return result;
    }

    /**
     * Potentially wraps the specified weighting into a TurnWeighting instance.
     */
    public Weighting createTurnWeighting( Weighting weighting, Graph graph, FlagEncoder encoder )
    {
        if (encoder.supports(TurnWeighting.class))
            return new TurnWeighting(weighting, encoder, (TurnCostExtension) graph.getExtension());
        return weighting;
    }

    @Override
    public GHResponse route( GHRequest request )
    {
        GHResponse response = new GHResponse();
        List<Path> paths = getPaths(request, response);
        if (response.hasErrors())
            return response;

        boolean tmpEnableInstructions = request.getHints().getBool("instructions", enableInstructions);
        boolean tmpCalcPoints = request.getHints().getBool("calcPoints", calcPoints);
        double wayPointMaxDistance = request.getHints().getDouble("wayPointMaxDistance", 1d);
        Locale locale = request.getLocale();
        DouglasPeucker peucker = new DouglasPeucker().setMaxDistance(wayPointMaxDistance);

        new PathMerger().
                setCalcPoints(tmpCalcPoints).
                setDouglasPeucker(peucker).
                setEnableInstructions(tmpEnableInstructions).
                setSimplifyResponse(simplifyResponse && wayPointMaxDistance > 0).
                doWork(response, paths, trMap.getWithFallBack(locale));
        return response;
    }

    protected List<Path> getPaths( GHRequest request, GHResponse rsp )
    {
        if (graph == null || !fullyLoaded)
            throw new IllegalStateException("Call load or importOrLoad before routing");

        if (graph.isClosed())
            throw new IllegalStateException("You need to create a new GraphHopper instance as it is already closed");

        String vehicle = request.getVehicle();
        if (vehicle.isEmpty())
            vehicle = getDefaultVehicle().toString();

        if (!encodingManager.supports(vehicle))
        {
            rsp.addError(new IllegalArgumentException("Vehicle " + vehicle + " unsupported. "
                    + "Supported are: " + getEncodingManager()));
            return Collections.emptyList();
        }

        TraversalMode tMode;
        String tModeStr = request.getHints().get("traversal_mode", traversalMode.toString());
        try
        {
            tMode = TraversalMode.fromString(tModeStr);
        } catch (Exception ex)
        {
            rsp.addError(ex);
            return Collections.emptyList();
        }

        List<GHPoint> points = request.getPoints();
        if (points.size() < 2)
        {
            rsp.addError(new IllegalStateException("At least 2 points has to be specified, but was:" + points.size()));
            return Collections.emptyList();
        }

        visitedSum.set(0);

        FlagEncoder encoder = encodingManager.getEncoder(vehicle);
        EdgeFilter edgeFilter = new DefaultEdgeFilter(encoder);

        StopWatch sw = new StopWatch().start();
        List<QueryResult> qResults = new ArrayList<QueryResult>(points.size());
        for (int placeIndex = 0; placeIndex < points.size(); placeIndex++)
        {
            GHPoint point = points.get(placeIndex);
            QueryResult res = locationIndex.findClosest(point.lat, point.lon, edgeFilter);
            if (!res.isValid())
                rsp.addError(new IllegalArgumentException("Cannot find point " + placeIndex + ": " + point));

            qResults.add(res);
        }

        if (rsp.hasErrors())
            return Collections.emptyList();

        String debug = "idLookup:" + sw.stop().getSeconds() + "s";

        QueryGraph queryGraph;
        RoutingAlgorithmFactory tmpAlgoFactory = getAlgorithmFactory();
        if (chEnabled && !vehicle.equalsIgnoreCase(getDefaultVehicle().toString()))
        {
            // fall back to normal traversing
            tmpAlgoFactory = new RoutingAlgorithmFactorySimple();
            queryGraph = new QueryGraph(graph.getBaseGraph());
        } else
        {
            queryGraph = new QueryGraph(graph);
        }

        queryGraph.lookup(qResults);

        List<Path> paths = new ArrayList<Path>(points.size() - 1);
        QueryResult fromQResult = qResults.get(0);
        Weighting weighting = createWeighting(request.getHints(), encoder);
        weighting = createTurnWeighting(weighting, queryGraph, encoder);

        double weightLimit = request.getHints().getDouble("defaultWeightLimit", defaultWeightLimit);
        String algoStr = request.getAlgorithm().isEmpty() ? AlgorithmOptions.DIJKSTRA_BI : request.getAlgorithm();
        AlgorithmOptions algoOpts = AlgorithmOptions.start().
                algorithm(algoStr).traversalMode(tMode).flagEncoder(encoder).weighting(weighting).
                build();

        for (int placeIndex = 1; placeIndex < points.size(); placeIndex++)
        {
            QueryResult toQResult = qResults.get(placeIndex);
            sw = new StopWatch().start();
            RoutingAlgorithm algo = tmpAlgoFactory.createAlgo(queryGraph, algoOpts);
            algo.setWeightLimit(weightLimit);
            debug += ", algoInit:" + sw.stop().getSeconds() + "s";

            sw = new StopWatch().start();
            Path path = algo.calcPath(fromQResult.getClosestNode(), toQResult.getClosestNode());
            if (path.getTime() < 0)
                throw new RuntimeException("Time was negative. Please report as bug and include:" + request);

            paths.add(path);
            debug += ", " + algo.getName() + "-routing:" + sw.stop().getSeconds() + "s, " + path.getDebugInfo();

            visitedSum.addAndGet(algo.getVisitedNodes());
            fromQResult = toQResult;
        }

        if (rsp.hasErrors())
            return Collections.emptyList();

        if (points.size() - 1 != paths.size())
            throw new RuntimeException("There should be exactly one more places than paths. places:" + points.size() + ", paths:" + paths.size());

        rsp.setDebugInfo(debug);
        return paths;
    }

    protected LocationIndex createLocationIndex( Directory dir )
    {
        LocationIndexTree tmpIndex = new LocationIndexTree(graph.getBaseGraph(), dir);
        tmpIndex.setResolution(preciseIndexResolution);
        tmpIndex.setMaxRegionSearch(maxRegionSearch);
        if (!tmpIndex.loadExisting())
        {
            ensureWriteAccess();
            tmpIndex.prepareIndex();
        }

        return tmpIndex;
    }

    /**
     * Initializes the location index after the import is done.
     */
    protected void initLocationIndex()
    {
        if (locationIndex != null)
            throw new IllegalStateException("Cannot initialize locationIndex twice!");

        locationIndex = createLocationIndex(graph.getDirectory());
    }

    protected void optimize()
    {
        logger.info("optimizing ... (" + Helper.getMemInfo() + ")");
        graph.optimize();
        logger.info("finished optimize (" + Helper.getMemInfo() + ")");

        // Later: move this into the GraphStorage.optimize method
        // Or: Doing it after preparation to optimize shortcuts too. But not possible yet #12
        if (sortGraph)
        {
            if (graph instanceof LevelGraph && isPrepared())
                throw new IllegalArgumentException("Sorting prepared LevelGraph is not possible yet. See #12");

            GraphStorage newGraph = GHUtility.newStorage(graph);
            GHUtility.sortDFS(graph, newGraph);
            logger.info("graph sorted (" + Helper.getMemInfo() + ")");
            graph = newGraph;
        }
    }

    protected void prepare()
    {
        boolean tmpPrepare = doPrepare && algoFactory instanceof PrepareContractionHierarchies;
        if (tmpPrepare)
        {
            ensureWriteAccess();
            logger.info("calling prepare.doWork for " + getDefaultVehicle() + " ... (" + Helper.getMemInfo() + ")");
            ((PrepareContractionHierarchies) algoFactory).doWork();
            graph.getProperties().put("prepare.date", formatDateTime(new Date()));
        }
        graph.getProperties().put("prepare.done", tmpPrepare);
    }

    protected void cleanUp()
    {
        int prevNodeCount = graph.getNodes();
        PrepareRoutingSubnetworks preparation = new PrepareRoutingSubnetworks(graph, encodingManager);
        preparation.setMinNetworkSize(minNetworkSize);
        preparation.setMinOneWayNetworkSize(minOneWayNetworkSize);
        logger.info("start finding subnetworks, " + Helper.getMemInfo());
        preparation.doWork();
        int currNodeCount = graph.getNodes();        
        int remainingSubnetworks = preparation.findSubnetworks().size();
        logger.info("edges: " + graph.getAllEdges().getCount() + ", nodes " + currNodeCount
                + ", there were " + preparation.getSubNetworks()
                + " subnetworks. removed them => " + (prevNodeCount - currNodeCount)
                + " less nodes. Remaining subnetworks:" + remainingSubnetworks);
    }

    protected void flush()
    {
        logger.info("flushing graph " + graph.toString() + ", details:" + graph.toDetailsString() + ", "
                + Helper.getMemInfo() + ")");
        graph.flush();
        fullyLoaded = true;
    }

    /**
     * Releases all associated resources like memory or files. But it does not remove them. To
     * remove the files created in graphhopperLocation you have to call clean().
     */
    public void close()
    {
        if (graph != null)
            graph.close();

        if (locationIndex != null)
            locationIndex.close();

        try
        {
            lockFactory.forceRemove(fileLockName, true);
        } catch (Exception ex)
        {
            // silently fail e.g. on Windows where we cannot remove an unreleased native lock
        }
    }

    /**
     * Removes the on-disc routing files. Call only after calling close or before importOrLoad or
     * load
     */
    public void clean()
    {
        if (getGraphHopperLocation().isEmpty())
            throw new IllegalStateException("Cannot clean GraphHopper without specified graphHopperLocation");

        File folder = new File(getGraphHopperLocation());
        Helper.removeDir(folder);
    }

    // make sure this is identical to buildDate used in pom.xml
    // <maven.build.timestamp.format>yyyy-MM-dd'T'HH:mm:ssZ</maven.build.timestamp.format>
    private String formatDateTime( Date date )
    {
        return new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssZ").format(date);
    }

    protected void ensureNotLoaded()
    {
        if (fullyLoaded)
            throw new IllegalStateException("No configuration changes are possible after loading the graph");
    }

    protected void ensureWriteAccess()
    {
        if (!allowWrites)
            throw new IllegalStateException("Writes are not allowed!");
    }

    /**
     * Returns the current sum of the visited nodes while routing. Mainly for statistic and
     * debugging purposes.
     */
    long getVisitedSum()
    {
        return visitedSum.get();
    }
}


File: core/src/main/java/com/graphhopper/reader/OSMReader.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.reader;

import static com.graphhopper.util.Helper.nf;

import gnu.trove.list.TLongList;
import gnu.trove.list.array.TLongArrayList;
import gnu.trove.map.TIntLongMap;
import gnu.trove.map.TLongLongMap;
import gnu.trove.map.hash.TIntLongHashMap;
import gnu.trove.map.hash.TLongLongHashMap;
import gnu.trove.set.TLongSet;
import gnu.trove.set.hash.TLongHashSet;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

import javax.xml.stream.XMLStreamException;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.graphhopper.coll.GHLongIntBTree;
import com.graphhopper.coll.LongIntMap;
import com.graphhopper.reader.OSMTurnRelation.TurnCostTableEntry;
import com.graphhopper.reader.dem.ElevationProvider;
import com.graphhopper.routing.util.*;
import com.graphhopper.storage.*;
import com.graphhopper.util.*;
import com.graphhopper.util.shapes.GHPoint;
import gnu.trove.map.TLongObjectMap;
import gnu.trove.map.hash.TLongObjectHashMap;

import java.util.*;

/**
 * This class parses an OSM xml or pbf file and creates a graph from it. It does so in a two phase
 * parsing processes in order to reduce memory usage compared to a single parsing processing.
 * <p/>
 * 1. a) Reads ways from OSM file and stores all associated node ids in osmNodeIdToIndexMap. If a
 * node occurs once it is a pillar node and if more it is a tower node, otherwise
 * osmNodeIdToIndexMap returns EMPTY.
 * <p/>
 * 1. b) Reads relations from OSM file. In case that the relation is a route relation, it stores
 * specific relation attributes required for routing into osmWayIdToRouteWeigthMap for all the ways
 * of the relation.
 * <p/>
 * 2.a) Reads nodes from OSM file and stores lat+lon information either into the intermediate
 * datastructure for the pillar nodes (pillarLats/pillarLons) or, if a tower node, directly into the
 * graphStorage via setLatitude/setLongitude. It can also happen that a pillar node needs to be
 * transformed into a tower node e.g. via barriers or different speed values for one way.
 * <p/>
 * 2.b) Reads ways OSM file and creates edges while calculating the speed etc from the OSM tags.
 * When creating an edge the pillar node information from the intermediate datastructure will be
 * stored in the way geometry of that edge.
 * <p/>
 * @author Peter Karich
 */
public class OSMReader implements DataReader
{
    protected static final int EMPTY = -1;
    // pillar node is >= 3
    protected static final int PILLAR_NODE = 1;
    // tower node is <= -3
    protected static final int TOWER_NODE = -2;
    private static final Logger logger = LoggerFactory.getLogger(OSMReader.class);
    private long locations;
    private long skippedLocations;
    private final GraphStorage graphStorage;
    private final NodeAccess nodeAccess;
    private EncodingManager encodingManager = null;
    private int workerThreads = -1;
    protected long zeroCounter = 0;
    // Using the correct Map<Long, Integer> is hard. We need a memory efficient and fast solution for big data sets!
    //
    // very slow: new SparseLongLongArray
    // only append and update possible (no unordered storage like with this doubleParse): new OSMIDMap
    // same here: not applicable as ways introduces the nodes in 'wrong' order: new OSMIDSegmentedMap
    // memory overhead due to open addressing and full rehash:
    //        nodeOsmIdToIndexMap = new BigLongIntMap(expectedNodes, EMPTY);
    // smaller memory overhead for bigger data sets because of avoiding a "rehash"
    // remember how many times a node was used to identify tower nodes
    private LongIntMap osmNodeIdToInternalNodeMap;
    private TLongLongHashMap osmNodeIdToNodeFlagsMap;
    private TLongLongHashMap osmWayIdToRouteWeightMap;
    // stores osm way ids used by relations to identify which edge ids needs to be mapped later
    private TLongHashSet osmWayIdSet = new TLongHashSet();
    private TIntLongMap edgeIdToOsmWayIdMap;
    private final TLongList barrierNodeIds = new TLongArrayList();
    protected PillarInfo pillarInfo;
    private final DistanceCalc distCalc = Helper.DIST_EARTH;
    private final DistanceCalc3D distCalc3D = Helper.DIST_3D;
    private final DouglasPeucker simplifyAlgo = new DouglasPeucker();
    private boolean doSimplify = true;
    private int nextTowerId = 0;
    private int nextPillarId = 0;
    // negative but increasing to avoid clash with custom created OSM files
    private long newUniqueOsmId = -Long.MAX_VALUE;
    private ElevationProvider eleProvider = ElevationProvider.NOOP;
    private boolean exitOnlyPillarNodeException = true;
    private File osmFile;
    private Map<FlagEncoder, EdgeExplorer> outExplorerMap = new HashMap<FlagEncoder, EdgeExplorer>();
    private Map<FlagEncoder, EdgeExplorer> inExplorerMap = new HashMap<FlagEncoder, EdgeExplorer>();

    public OSMReader( GraphStorage storage )
    {
        this.graphStorage = storage;
        this.nodeAccess = graphStorage.getNodeAccess();

        osmNodeIdToInternalNodeMap = new GHLongIntBTree(200);
        osmNodeIdToNodeFlagsMap = new TLongLongHashMap(200, .5f, 0, 0);
        osmWayIdToRouteWeightMap = new TLongLongHashMap(200, .5f, 0, 0);
        pillarInfo = new PillarInfo(nodeAccess.is3D(), graphStorage.getDirectory());
    }

    @Override
    public void readGraph() throws IOException
    {
        if (encodingManager == null)
            throw new IllegalStateException("Encoding manager was not set.");

        if (osmFile == null)
            throw new IllegalStateException("No OSM file specified");

        if (!osmFile.exists())
            throw new IllegalStateException("Your specified OSM file does not exist:" + osmFile.getAbsolutePath());

        StopWatch sw1 = new StopWatch().start();
        preProcess(osmFile);
        sw1.stop();

        StopWatch sw2 = new StopWatch().start();
        writeOsm2Graph(osmFile);
        sw2.stop();

        logger.info("time(pass1): " + (int) sw1.getSeconds() + " pass2: " + (int) sw2.getSeconds() + " total:"
                + ((int) (sw1.getSeconds() + sw2.getSeconds())));
    }

    /**
     * Preprocessing of OSM file to select nodes which are used for highways. This allows a more
     * compact graph data structure.
     */
    void preProcess( File osmFile )
    {
        OSMInputFile in = null;
        try
        {
            in = new OSMInputFile(osmFile).setWorkerThreads(workerThreads).open();

            long tmpWayCounter = 1;
            long tmpRelationCounter = 1;
            OSMElement item;
            while ((item = in.getNext()) != null)
            {
                if (item.isType(OSMElement.WAY))
                {
                    final OSMWay way = (OSMWay) item;
                    boolean valid = filterWay(way);
                    if (valid)
                    {
                        TLongList wayNodes = way.getNodes();
                        int s = wayNodes.size();
                        for (int index = 0; index < s; index++)
                        {
                            prepareHighwayNode(wayNodes.get(index));
                        }

                        if (++tmpWayCounter % 5000000 == 0)
                        {
                            logger.info(nf(tmpWayCounter) + " (preprocess), osmIdMap:" + nf(getNodeMap().getSize()) + " ("
                                    + getNodeMap().getMemoryUsage() + "MB) " + Helper.getMemInfo());
                        }
                    }
                }
                if (item.isType(OSMElement.RELATION))
                {
                    final OSMRelation relation = (OSMRelation) item;
                    if (!relation.isMetaRelation() && relation.hasTag("type", "route"))
                        prepareWaysWithRelationInfo(relation);

                    if (relation.hasTag("type", "restriction"))
                        prepareRestrictionRelation(relation);

                    if (++tmpRelationCounter % 50000 == 0)
                    {
                        logger.info(nf(tmpRelationCounter) + " (preprocess), osmWayMap:" + nf(getRelFlagsMap().size())
                                + " " + Helper.getMemInfo());
                    }

                }
            }
        } catch (Exception ex)
        {
            throw new RuntimeException("Problem while parsing file", ex);
        } finally
        {
            Helper.close(in);
        }
    }

    private void prepareRestrictionRelation( OSMRelation relation )
    {
        OSMTurnRelation turnRelation = createTurnRelation(relation);
        if (turnRelation != null)
        {
            getOsmWayIdSet().add(turnRelation.getOsmIdFrom());
            getOsmWayIdSet().add(turnRelation.getOsmIdTo());
        }
    }

    /**
     * @return all required osmWayIds to process e.g. relations.
     */
    private TLongSet getOsmWayIdSet()
    {
        return osmWayIdSet;
    }

    private TIntLongMap getEdgeIdToOsmWayIdMap()
    {
        if (edgeIdToOsmWayIdMap == null)
            edgeIdToOsmWayIdMap = new TIntLongHashMap(getOsmWayIdSet().size(), 0.5f, -1, -1);

        return edgeIdToOsmWayIdMap;
    }

    /**
     * Filter ways but do not analyze properties wayNodes will be filled with participating node
     * ids.
     * <p/>
     * @return true the current xml entry is a way entry and has nodes
     */
    boolean filterWay( OSMWay item )
    {
        // ignore broken geometry
        if (item.getNodes().size() < 2)
            return false;

        // ignore multipolygon geometry
        if (!item.hasTags())
            return false;

        return encodingManager.acceptWay(item) > 0;
    }

    /**
     * Creates the edges and nodes files from the specified osm file.
     */
    private void writeOsm2Graph( File osmFile )
    {
        int tmp = (int) Math.max(getNodeMap().getSize() / 50, 100);
        logger.info("creating graph. Found nodes (pillar+tower):" + nf(getNodeMap().getSize()) + ", " + Helper.getMemInfo());
        graphStorage.create(tmp);
        long wayStart = -1;
        long relationStart = -1;
        long counter = 1;
        OSMInputFile in = null;
        try
        {
            in = new OSMInputFile(osmFile).setWorkerThreads(workerThreads).open();
            LongIntMap nodeFilter = getNodeMap();

            OSMElement item;
            while ((item = in.getNext()) != null)
            {
                switch (item.getType())
                {
                    case OSMElement.NODE:
                        if (nodeFilter.get(item.getId()) != -1)
                        {
                            processNode((OSMNode) item);
                        }
                        break;

                    case OSMElement.WAY:
                        if (wayStart < 0)
                        {
                            logger.info(nf(counter) + ", now parsing ways");
                            wayStart = counter;
                        }
                        processWay((OSMWay) item);
                        break;
                    case OSMElement.RELATION:
                        if (relationStart < 0)
                        {
                            logger.info(nf(counter) + ", now parsing relations");
                            relationStart = counter;
                        }
                        processRelation((OSMRelation) item);
                        break;
                }
                if (++counter % 100000000 == 0)
                {
                    logger.info(nf(counter) + ", locs:" + nf(locations) + " (" + skippedLocations + ") " + Helper.getMemInfo());
                }
            }

            // logger.info("storage nodes:" + storage.nodes() + " vs. graph nodes:" + storage.getGraph().nodes());
        } catch (Exception ex)
        {
            throw new RuntimeException("Couldn't process file " + osmFile + ", error: " + ex.getMessage(), ex);
        } finally
        {
            Helper.close(in);
        }

        finishedReading();
        if (graphStorage.getNodes() == 0)
            throw new IllegalStateException("osm must not be empty. read " + counter + " lines and " + locations + " locations");
    }

    /**
     * Process properties, encode flags and create edges for the way.
     */
    void processWay( OSMWay way )
    {
        if (way.getNodes().size() < 2)
            return;

        // ignore multipolygon geometry
        if (!way.hasTags())
            return;

        long wayOsmId = way.getId();

        long includeWay = encodingManager.acceptWay(way);
        if (includeWay == 0)
            return;

        long relationFlags = getRelFlagsMap().get(way.getId());

        // TODO move this after we have created the edge and know the coordinates => encodingManager.applyWayTags
        // estimate length of the track e.g. for ferry speed calculation
        TLongList osmNodeIds = way.getNodes();
        if (osmNodeIds.size() > 1)
        {
            int first = getNodeMap().get(osmNodeIds.get(0));
            int last = getNodeMap().get(osmNodeIds.get(osmNodeIds.size() - 1));
            double firstLat = getTmpLatitude(first), firstLon = getTmpLongitude(first);
            double lastLat = getTmpLatitude(last), lastLon = getTmpLongitude(last);
            if (!Double.isNaN(firstLat) && !Double.isNaN(firstLon) && !Double.isNaN(lastLat) && !Double.isNaN(lastLon))
            {
                double estimatedDist = distCalc.calcDist(firstLat, firstLon, lastLat, lastLon);
                way.setTag("estimated_distance", estimatedDist);
                way.setTag("estimated_center", new GHPoint((firstLat + lastLat) / 2, (firstLon + lastLon) / 2));
            }
        }

        long wayFlags = encodingManager.handleWayTags(way, includeWay, relationFlags);
        if (wayFlags == 0)
            return;

        List<EdgeIteratorState> createdEdges = new ArrayList<EdgeIteratorState>();
        // look for barriers along the way
        final int size = osmNodeIds.size();
        int lastBarrier = -1;
        for (int i = 0; i < size; i++)
        {
            long nodeId = osmNodeIds.get(i);
            long nodeFlags = getNodeFlagsMap().get(nodeId);
            // barrier was spotted and way is otherwise passable for that mode of travel
            if (nodeFlags > 0)
            {
                if ((nodeFlags & wayFlags) > 0)
                {
                    // remove barrier to avoid duplicates
                    getNodeFlagsMap().put(nodeId, 0);

                    // create shadow node copy for zero length edge
                    long newNodeId = addBarrierNode(nodeId);
                    if (i > 0)
                    {
                        // start at beginning of array if there was no previous barrier
                        if (lastBarrier < 0)
                            lastBarrier = 0;

                        // add way up to barrier shadow node
                        long transfer[] = osmNodeIds.toArray(lastBarrier, i - lastBarrier + 1);
                        transfer[transfer.length - 1] = newNodeId;
                        TLongList partIds = new TLongArrayList(transfer);
                        createdEdges.addAll(addOSMWay(partIds, wayFlags, wayOsmId));

                        // create zero length edge for barrier
                        createdEdges.addAll(addBarrierEdge(newNodeId, nodeId, wayFlags, nodeFlags, wayOsmId));
                    } else
                    {
                        // run edge from real first node to shadow node
                        createdEdges.addAll(addBarrierEdge(nodeId, newNodeId, wayFlags, nodeFlags, wayOsmId));

                        // exchange first node for created barrier node
                        osmNodeIds.set(0, newNodeId);
                    }
                    // remember barrier for processing the way behind it
                    lastBarrier = i;
                }
            }
        }

        // just add remainder of way to graph if barrier was not the last node
        if (lastBarrier >= 0)
        {
            if (lastBarrier < size - 1)
            {
                long transfer[] = osmNodeIds.toArray(lastBarrier, size - lastBarrier);
                TLongList partNodeIds = new TLongArrayList(transfer);
                createdEdges.addAll(addOSMWay(partNodeIds, wayFlags, wayOsmId));
            }
        } else
        {
            // no barriers - simply add the whole way
            createdEdges.addAll(addOSMWay(way.getNodes(), wayFlags, wayOsmId));
        }

        for (EdgeIteratorState edge : createdEdges)
        {
            encodingManager.applyWayTags(way, edge);
        }
    }

    public void processRelation( OSMRelation relation ) throws XMLStreamException
    {
        if (relation.hasTag("type", "restriction"))
        {
            OSMTurnRelation turnRelation = createTurnRelation(relation);
            if (turnRelation != null)
            {
                GraphExtension extendedStorage = graphStorage.getExtension();
                if (extendedStorage instanceof TurnCostExtension)
                {
                    TurnCostExtension tcs = (TurnCostExtension) extendedStorage;
                    Collection<TurnCostTableEntry> entries = analyzeTurnRelation(turnRelation);
                    for (TurnCostTableEntry entry : entries)
                    {
                        tcs.addTurnInfo(entry.edgeFrom, entry.nodeVia, entry.edgeTo, entry.flags);
                    }
                }
            }
        }
    }

    public Collection<TurnCostTableEntry> analyzeTurnRelation( OSMTurnRelation turnRelation )
    {
        TLongObjectMap<TurnCostTableEntry> entries = new TLongObjectHashMap<OSMTurnRelation.TurnCostTableEntry>();

        for (FlagEncoder encoder : encodingManager.fetchEdgeEncoders())
        {
            for (TurnCostTableEntry entry : analyzeTurnRelation(encoder, turnRelation))
            {
                TurnCostTableEntry oldEntry = entries.get(entry.getItemId());
                if (oldEntry != null)
                {
                    // merging different encoders
                    oldEntry.flags |= entry.flags;
                } else
                {
                    entries.put(entry.getItemId(), entry);
                }
            }
        }

        return entries.valueCollection();
    }

    public Collection<TurnCostTableEntry> analyzeTurnRelation( FlagEncoder encoder, OSMTurnRelation turnRelation )
    {
        if (!encoder.supports(TurnWeighting.class))
            return Collections.emptyList();

        EdgeExplorer edgeOutExplorer = outExplorerMap.get(encoder);
        EdgeExplorer edgeInExplorer = inExplorerMap.get(encoder);

        if (edgeOutExplorer == null || edgeInExplorer == null)
        {
            edgeOutExplorer = getGraphStorage().createEdgeExplorer(new DefaultEdgeFilter(encoder, false, true));
            outExplorerMap.put(encoder, edgeOutExplorer);

            edgeInExplorer = getGraphStorage().createEdgeExplorer(new DefaultEdgeFilter(encoder, true, false));
            inExplorerMap.put(encoder, edgeInExplorer);
        }
        return turnRelation.getRestrictionAsEntries(encoder, edgeOutExplorer, edgeInExplorer, this);
    }

    /**
     * @return OSM way ID from specified edgeId. Only previously stored OSM-way-IDs are returned in
     * order to reduce memory overhead.
     */
    public long getOsmIdOfInternalEdge( int edgeId )
    {
        return getEdgeIdToOsmWayIdMap().get(edgeId);
    }

    public int getInternalNodeIdOfOsmNode( long nodeOsmId )
    {
        int id = getNodeMap().get(nodeOsmId);
        if (id < TOWER_NODE)
            return -id - 3;

        return EMPTY;
    }

    // TODO remove this ugly stuff via better preparsing phase! E.g. putting every tags etc into a helper file!
    double getTmpLatitude( int id )
    {
        if (id == EMPTY)
            return Double.NaN;
        if (id < TOWER_NODE)
        {
            // tower node
            id = -id - 3;
            return nodeAccess.getLatitude(id);
        } else if (id > -TOWER_NODE)
        {
            // pillar node
            id = id - 3;
            return pillarInfo.getLatitude(id);
        } else
            // e.g. if id is not handled from preparse (e.g. was ignored via isInBounds)
            return Double.NaN;
    }

    double getTmpLongitude( int id )
    {
        if (id == EMPTY)
            return Double.NaN;
        if (id < TOWER_NODE)
        {
            // tower node
            id = -id - 3;
            return nodeAccess.getLongitude(id);
        } else if (id > -TOWER_NODE)
        {
            // pillar node
            id = id - 3;
            return pillarInfo.getLon(id);
        } else
            // e.g. if id is not handled from preparse (e.g. was ignored via isInBounds)
            return Double.NaN;
    }

    private void processNode( OSMNode node )
    {
        if (isInBounds(node))
        {
            addNode(node);

            // analyze node tags for barriers
            if (node.hasTags())
            {
                long nodeFlags = encodingManager.handleNodeTags(node);
                if (nodeFlags != 0)
                    getNodeFlagsMap().put(node.getId(), nodeFlags);
            }

            locations++;
        } else
        {
            skippedLocations++;
        }
    }

    boolean addNode( OSMNode node )
    {
        int nodeType = getNodeMap().get(node.getId());
        if (nodeType == EMPTY)
            return false;

        double lat = node.getLat();
        double lon = node.getLon();
        double ele = getElevation(node);
        if (nodeType == TOWER_NODE)
        {
            addTowerNode(node.getId(), lat, lon, ele);
        } else if (nodeType == PILLAR_NODE)
        {
            pillarInfo.setNode(nextPillarId, lat, lon, ele);
            getNodeMap().put(node.getId(), nextPillarId + 3);
            nextPillarId++;
        }
        return true;
    }

    protected double getElevation( OSMNode node )
    {
        return eleProvider.getEle(node.getLat(), node.getLon());
    }

    void prepareWaysWithRelationInfo( OSMRelation osmRelation )
    {
        // is there at least one tag interesting for the registed encoders?
        if (encodingManager.handleRelationTags(osmRelation, 0) == 0)
            return;

        int size = osmRelation.getMembers().size();
        for (int index = 0; index < size; index++)
        {
            OSMRelation.Member member = osmRelation.getMembers().get(index);
            if (member.type() != OSMRelation.Member.WAY)
                continue;

            long osmId = member.ref();
            long oldRelationFlags = getRelFlagsMap().get(osmId);

            // Check if our new relation data is better comparated to the the last one
            long newRelationFlags = encodingManager.handleRelationTags(osmRelation, oldRelationFlags);
            if (oldRelationFlags != newRelationFlags)
                getRelFlagsMap().put(osmId, newRelationFlags);
        }
    }

    void prepareHighwayNode( long osmId )
    {
        int tmpIndex = getNodeMap().get(osmId);
        if (tmpIndex == EMPTY)
        {
            // osmId is used exactly once
            getNodeMap().put(osmId, PILLAR_NODE);
        } else if (tmpIndex > EMPTY)
        {
            // mark node as tower node as it occured at least twice times
            getNodeMap().put(osmId, TOWER_NODE);
        } else
        {
            // tmpIndex is already negative (already tower node)
        }
    }

    int addTowerNode( long osmId, double lat, double lon, double ele )
    {
        if (nodeAccess.is3D())
            nodeAccess.setNode(nextTowerId, lat, lon, ele);
        else
            nodeAccess.setNode(nextTowerId, lat, lon);

        int id = -(nextTowerId + 3);
        getNodeMap().put(osmId, id);
        nextTowerId++;
        return id;
    }

    /**
     * This method creates from an OSM way (via the osm ids) one or more edges in the graph.
     */
    Collection<EdgeIteratorState> addOSMWay( final TLongList osmNodeIds, final long flags, final long wayOsmId )
    {
        PointList pointList = new PointList(osmNodeIds.size(), nodeAccess.is3D());
        List<EdgeIteratorState> newEdges = new ArrayList<EdgeIteratorState>(5);
        int firstNode = -1;
        int lastIndex = osmNodeIds.size() - 1;
        int lastInBoundsPillarNode = -1;
        try
        {
            for (int i = 0; i < osmNodeIds.size(); i++)
            {
                long osmId = osmNodeIds.get(i);
                int tmpNode = getNodeMap().get(osmId);
                if (tmpNode == EMPTY)
                    continue;

                // skip osmIds with no associated pillar or tower id (e.g. !OSMReader.isBounds)
                if (tmpNode == TOWER_NODE)
                    continue;

                if (tmpNode == PILLAR_NODE)
                {
                    // In some cases no node information is saved for the specified osmId.
                    // ie. a way references a <node> which does not exist in the current file.
                    // => if the node before was a pillar node then convert into to tower node (as it is also end-standing).
                    if (!pointList.isEmpty() && lastInBoundsPillarNode > -TOWER_NODE)
                    {
                        // transform the pillar node to a tower node
                        tmpNode = lastInBoundsPillarNode;
                        tmpNode = handlePillarNode(tmpNode, osmId, null, true);
                        tmpNode = -tmpNode - 3;
                        if (pointList.getSize() > 1 && firstNode >= 0)
                        {
                            // TOWER node
                            newEdges.add(addEdge(firstNode, tmpNode, pointList, flags, wayOsmId));
                            pointList.clear();
                            pointList.add(nodeAccess, tmpNode);
                        }
                        firstNode = tmpNode;
                        lastInBoundsPillarNode = -1;
                    }
                    continue;
                }

                if (tmpNode <= -TOWER_NODE && tmpNode >= TOWER_NODE)
                    throw new AssertionError("Mapped index not in correct bounds " + tmpNode + ", " + osmId);

                if (tmpNode > -TOWER_NODE)
                {
                    boolean convertToTowerNode = i == 0 || i == lastIndex;
                    if (!convertToTowerNode)
                    {
                        lastInBoundsPillarNode = tmpNode;
                    }

                    // PILLAR node, but convert to towerNode if end-standing
                    tmpNode = handlePillarNode(tmpNode, osmId, pointList, convertToTowerNode);
                }

                if (tmpNode < TOWER_NODE)
                {
                    // TOWER node
                    tmpNode = -tmpNode - 3;
                    pointList.add(nodeAccess, tmpNode);
                    if (firstNode >= 0)
                    {
                        newEdges.add(addEdge(firstNode, tmpNode, pointList, flags, wayOsmId));
                        pointList.clear();
                        pointList.add(nodeAccess, tmpNode);
                    }
                    firstNode = tmpNode;
                }
            }
        } catch (RuntimeException ex)
        {
            logger.error("Couldn't properly add edge with osm ids:" + osmNodeIds, ex);
            if (exitOnlyPillarNodeException)
                throw ex;
        }
        return newEdges;
    }

    EdgeIteratorState addEdge( int fromIndex, int toIndex, PointList pointList, long flags, long wayOsmId )
    {
        // sanity checks
        if (fromIndex < 0 || toIndex < 0)
            throw new AssertionError("to or from index is invalid for this edge " + fromIndex + "->" + toIndex + ", points:" + pointList);
        if (pointList.getDimension() != nodeAccess.getDimension())
            throw new AssertionError("Dimension does not match for pointList vs. nodeAccess " + pointList.getDimension() + " <-> " + nodeAccess.getDimension());

        double towerNodeDistance = 0;
        double prevLat = pointList.getLatitude(0);
        double prevLon = pointList.getLongitude(0);
        double prevEle = pointList.is3D() ? pointList.getElevation(0) : Double.NaN;
        double lat, lon, ele = Double.NaN;
        PointList pillarNodes = new PointList(pointList.getSize() - 2, nodeAccess.is3D());
        int nodes = pointList.getSize();
        for (int i = 1; i < nodes; i++)
        {
            // we could save some lines if we would use pointList.calcDistance(distCalc);
            lat = pointList.getLatitude(i);
            lon = pointList.getLongitude(i);
            if (pointList.is3D())
            {
                ele = pointList.getElevation(i);
                towerNodeDistance += distCalc3D.calcDist(prevLat, prevLon, prevEle, lat, lon, ele);
                prevEle = ele;
            } else
                towerNodeDistance += distCalc.calcDist(prevLat, prevLon, lat, lon);
            prevLat = lat;
            prevLon = lon;
            if (nodes > 2 && i < nodes - 1)
            {
                if (pillarNodes.is3D())
                    pillarNodes.add(lat, lon, ele);
                else
                    pillarNodes.add(lat, lon);
            }
        }
        if (towerNodeDistance == 0)
        {
            // As investigation shows often two paths should have crossed via one identical point 
            // but end up in two very close points.
            zeroCounter++;
            towerNodeDistance = 0.0001;
        }

        EdgeIteratorState iter = graphStorage.edge(fromIndex, toIndex).setDistance(towerNodeDistance).setFlags(flags);
        if (nodes > 2)
        {
            if (doSimplify)
                simplifyAlgo.simplify(pillarNodes);

            iter.setWayGeometry(pillarNodes);
        }
        storeOsmWayID(iter.getEdge(), wayOsmId);
        return iter;
    }

    /**
     * Stores only osmWayIds which are required for relations
     */
    private void storeOsmWayID( int edgeId, long osmWayId )
    {
        if (getOsmWayIdSet().contains(osmWayId))
        {
            getEdgeIdToOsmWayIdMap().put(edgeId, osmWayId);
        }
    }

    /**
     * @return converted tower node
     */
    private int handlePillarNode( int tmpNode, long osmId, PointList pointList, boolean convertToTowerNode )
    {
        tmpNode = tmpNode - 3;
        double lat = pillarInfo.getLatitude(tmpNode);
        double lon = pillarInfo.getLongitude(tmpNode);
        double ele = pillarInfo.getElevation(tmpNode);
        if (lat == Double.MAX_VALUE || lon == Double.MAX_VALUE)
            throw new RuntimeException("Conversion pillarNode to towerNode already happended!? "
                    + "osmId:" + osmId + " pillarIndex:" + tmpNode);

        if (convertToTowerNode)
        {
            // convert pillarNode type to towerNode, make pillar values invalid
            pillarInfo.setNode(tmpNode, Double.MAX_VALUE, Double.MAX_VALUE, Double.MAX_VALUE);
            tmpNode = addTowerNode(osmId, lat, lon, ele);
        } else
        {
            if (pointList.is3D())
                pointList.add(lat, lon, ele);
            else
                pointList.add(lat, lon);
        }

        return (int) tmpNode;
    }

    protected void finishedReading()
    {
        printInfo("way");
        pillarInfo.clear();
        eleProvider.release();
        osmNodeIdToInternalNodeMap = null;
        osmNodeIdToNodeFlagsMap = null;
        osmWayIdToRouteWeightMap = null;
        osmWayIdSet = null;
        edgeIdToOsmWayIdMap = null;
    }

    /**
     * Create a copy of the barrier node
     */
    long addBarrierNode( long nodeId )
    {
        OSMNode newNode;
        int graphIndex = getNodeMap().get(nodeId);
        if (graphIndex < TOWER_NODE)
        {
            graphIndex = -graphIndex - 3;
            newNode = new OSMNode(createNewNodeId(), nodeAccess, graphIndex);
        } else
        {
            graphIndex = graphIndex - 3;
            newNode = new OSMNode(createNewNodeId(), pillarInfo, graphIndex);
        }

        final long id = newNode.getId();
        prepareHighwayNode(id);
        addNode(newNode);
        return id;
    }

    private long createNewNodeId()
    {
        return newUniqueOsmId++;
    }

    /**
     * Add a zero length edge with reduced routing options to the graph.
     */
    Collection<EdgeIteratorState> addBarrierEdge( long fromId, long toId, long flags, long nodeFlags, long wayOsmId )
    {
        // clear barred directions from routing flags
        flags &= ~nodeFlags;
        // add edge
        barrierNodeIds.clear();
        barrierNodeIds.add(fromId);
        barrierNodeIds.add(toId);
        return addOSMWay(barrierNodeIds, flags, wayOsmId);
    }

    /**
     * Creates an OSM turn relation out of an unspecified OSM relation
     * <p/>
     * @return the OSM turn relation, <code>null</code>, if unsupported turn relation
     */
    OSMTurnRelation createTurnRelation( OSMRelation relation )
    {
        OSMTurnRelation.Type type = OSMTurnRelation.Type.getRestrictionType(relation.getTag("restriction"));
        if (type != OSMTurnRelation.Type.UNSUPPORTED)
        {
            long fromWayID = -1;
            long viaNodeID = -1;
            long toWayID = -1;

            for (OSMRelation.Member member : relation.getMembers())
            {
                if (OSMElement.WAY == member.type())
                {
                    if ("from".equals(member.role()))
                    {
                        fromWayID = member.ref();
                    } else if ("to".equals(member.role()))
                    {
                        toWayID = member.ref();
                    }
                } else if (OSMElement.NODE == member.type() && "via".equals(member.role()))
                {
                    viaNodeID = member.ref();
                }
            }
            if (fromWayID >= 0 && toWayID >= 0 && viaNodeID >= 0)
            {
                return new OSMTurnRelation(fromWayID, viaNodeID, toWayID, type);
            }
        }
        return null;
    }

    /**
     * Filter method, override in subclass
     */
    boolean isInBounds( OSMNode node )
    {
        return true;
    }

    /**
     * Maps OSM IDs (long) to internal node IDs (int)
     */
    protected LongIntMap getNodeMap()
    {
        return osmNodeIdToInternalNodeMap;
    }

    protected TLongLongMap getNodeFlagsMap()
    {
        return osmNodeIdToNodeFlagsMap;
    }

    TLongLongHashMap getRelFlagsMap()
    {
        return osmWayIdToRouteWeightMap;
    }

    /**
     * Specify the type of the path calculation (car, bike, ...).
     */
    public OSMReader setEncodingManager( EncodingManager em )
    {
        this.encodingManager = em;
        return this;
    }

    public OSMReader setWayPointMaxDistance( double maxDist )
    {
        doSimplify = maxDist > 0;
        simplifyAlgo.setMaxDistance(maxDist);
        return this;
    }

    public OSMReader setWorkerThreads( int numOfWorkers )
    {
        this.workerThreads = numOfWorkers;
        return this;
    }

    public OSMReader setElevationProvider( ElevationProvider eleProvider )
    {
        if (eleProvider == null)
            throw new IllegalStateException("Use the NOOP elevation provider instead of null or don't call setElevationProvider");

        if (!nodeAccess.is3D() && ElevationProvider.NOOP != eleProvider)
            throw new IllegalStateException("Make sure you graph accepts 3D data");

        this.eleProvider = eleProvider;
        return this;
    }

    public OSMReader setOSMFile( File osmFile )
    {
        this.osmFile = osmFile;
        return this;
    }

    private void printInfo( String str )
    {
        logger.info("finished " + str + " processing." + " nodes: " + graphStorage.getNodes()
                + ", osmIdMap.size:" + getNodeMap().getSize() + ", osmIdMap:" + getNodeMap().getMemoryUsage() + "MB"
                + ", nodeFlagsMap.size:" + getNodeFlagsMap().size() + ", relFlagsMap.size:" + getRelFlagsMap().size()
                + ", zeroCounter:" + zeroCounter
                + " " + Helper.getMemInfo());
    }

    @Override
    public String toString()
    {
        return getClass().getSimpleName();
    }

    public GraphStorage getGraphStorage()
    {
        return graphStorage;
    }
}


File: core/src/main/java/com/graphhopper/routing/ch/PrepareContractionHierarchies.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing.ch;

import com.graphhopper.coll.GHTreeMapComposed;
import com.graphhopper.routing.*;
import com.graphhopper.routing.util.AbstractAlgoPreparation;
import com.graphhopper.routing.util.DefaultEdgeFilter;
import com.graphhopper.routing.util.LevelEdgeFilter;
import com.graphhopper.routing.util.FlagEncoder;
import com.graphhopper.routing.util.Weighting;
import com.graphhopper.routing.util.*;
import com.graphhopper.storage.*;
import com.graphhopper.util.*;

import java.util.*;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * This class prepares the graph for a bidirectional algorithm supporting contraction hierarchies
 * ie. an algorithm returned by createAlgo.
 * <p/>
 * There are several description of contraction hierarchies available. The following is one of the
 * more detailed: http://web.cs.du.edu/~sturtevant/papers/highlevelpathfinding.pdf
 * <p/>
 * The only difference is that we use two skipped edges instead of one skipped node for faster
 * unpacking.
 * <p/>
 * @author Peter Karich
 */
public class PrepareContractionHierarchies extends AbstractAlgoPreparation implements RoutingAlgorithmFactory
{
    private final Logger logger = LoggerFactory.getLogger(getClass());
    private final PreparationWeighting prepareWeighting;
    private final FlagEncoder prepareFlagEncoder;
    private final TraversalMode traversalMode;
    private EdgeSkipExplorer vehicleInExplorer;
    private EdgeSkipExplorer vehicleOutExplorer;
    private EdgeSkipExplorer vehicleAllExplorer;
    private EdgeSkipExplorer vehicleAllTmpExplorer;
    private EdgeSkipExplorer calcPrioAllExplorer;
    private final LevelEdgeFilter levelFilter;
    private int maxLevel;
    private final LevelGraph prepareGraph;

    // the most important nodes comes last
    private GHTreeMapComposed sortedNodes;
    private int oldPriorities[];
    private final DataAccess originalEdges;
    private final Map<Shortcut, Shortcut> shortcuts = new HashMap<Shortcut, Shortcut>();
    private IgnoreNodeFilter ignoreNodeFilter;
    private DijkstraOneToMany prepareAlgo;
    private long counter;
    private int newShortcuts;
    private long dijkstraCount;
    private double meanDegree;
    private final Random rand = new Random(123);
    private StopWatch dijkstraSW = new StopWatch();
    private final StopWatch allSW = new StopWatch();
    private int periodicUpdatesPercentage = 20;
    private int lastNodesLazyUpdatePercentage = 10;
    private int neighborUpdatePercentage = 20;
    private int initialCollectionSize = 5000;
    private double nodesContractedPercentage = 100;
    private double logMessagesPercentage = 20;

    public PrepareContractionHierarchies( Directory dir, LevelGraph g, FlagEncoder encoder, Weighting weighting, TraversalMode traversalMode )
    {
        this.prepareGraph = g;
        this.traversalMode = traversalMode;
        this.prepareFlagEncoder = encoder;
        long scFwdDir = encoder.setAccess(0, true, false);
        levelFilter = new LevelEdgeFilter(prepareGraph);

        // shortcuts store weight in flags where we assume bit 1 and 2 are used for access restriction
        if ((scFwdDir & PrepareEncoder.getScFwdDir()) == 0)
            throw new IllegalArgumentException("Enabling the speed-up mode is currently only supported for the first vehicle.");

        prepareWeighting = new PreparationWeighting(weighting);
        originalEdges = dir.find("original_edges");
        originalEdges.create(1000);
    }

    /**
     * The higher the values are the longer the preparation takes but the less shortcuts are
     * produced.
     * <p/>
     * @param periodicUpdates specifies how often periodic updates will happen. Use something less
     * than 10.
     */
    public PrepareContractionHierarchies setPeriodicUpdates( int periodicUpdates )
    {
        if (periodicUpdates < 0)
            return this;
        if (periodicUpdates > 100)
            throw new IllegalArgumentException("periodicUpdates has to be in [0, 100], to disable it use 0");

        this.periodicUpdatesPercentage = periodicUpdates;
        return this;
    }

    /**
     * @param lazyUpdates specifies when lazy updates will happen, measured relative to all existing
     * nodes. 100 means always.
     */
    public PrepareContractionHierarchies setLazyUpdates( int lazyUpdates )
    {
        if (lazyUpdates < 0)
            return this;

        if (lazyUpdates > 100)
            throw new IllegalArgumentException("lazyUpdates has to be in [0, 100], to disable it use 0");

        this.lastNodesLazyUpdatePercentage = lazyUpdates;
        return this;
    }

    /**
     * @param neighborUpdates specifies how often neighbor updates will happen. 100 means always.
     */
    public PrepareContractionHierarchies setNeighborUpdates( int neighborUpdates )
    {
        if (neighborUpdates < 0)
            return this;

        if (neighborUpdates > 100)
            throw new IllegalArgumentException("neighborUpdates has to be in [0, 100], to disable it use 0");

        this.neighborUpdatePercentage = neighborUpdates;
        return this;
    }

    /**
     * Specifies how often a log message should be printed. Specify something around 20 (20% of the
     * start nodes).
     */
    public PrepareContractionHierarchies setLogMessages( double logMessages )
    {
        if (logMessages >= 0)
            this.logMessagesPercentage = logMessages;
        return this;
    }

    /**
     * Define how many nodes (percentage) should be contracted. Less nodes means slower query but
     * faster contraction duration. Not yet ready for prime time.
     */
    void setNodesContracted( double nodesContracted )
    {
        if (nodesContracted > 100)
            throw new IllegalArgumentException("setNodesContracted can be 100% maximum");

        this.nodesContractedPercentage = nodesContracted;
    }

    /**
     * While creating an algorithm out of this preparation class 10 000 nodes are assumed which can
     * be too high for your mobile application. E.g. A 500km query only traverses roughly 2000
     * nodes.
     */
    public void setInitialCollectionSize( int initialCollectionSize )
    {
        this.initialCollectionSize = initialCollectionSize;
    }

    @Override
    public void doWork()
    {
        if (prepareFlagEncoder == null)
            throw new IllegalStateException("No vehicle encoder set.");

        if (prepareWeighting == null)
            throw new IllegalStateException("No weight calculation set.");

        allSW.start();
        super.doWork();

        initFromGraph();
        if (!prepareEdges())
            return;

        if (!prepareNodes())
            return;

        contractNodes();
    }

    boolean prepareEdges()
    {
        EdgeIterator iter = prepareGraph.getAllEdges();
        int c = 0;
        while (iter.next())
        {
            c++;
            setOrigEdgeCount(iter.getEdge(), 1);
        }
        return c > 0;
    }

    boolean prepareNodes()
    {
        int nodes = prepareGraph.getNodes();
        for (int node = 0; node < nodes; node++)
        {
            prepareGraph.setLevel(node, maxLevel);
        }

        for (int node = 0; node < nodes; node++)
        {
            int priority = oldPriorities[node] = calculatePriority(node);
            sortedNodes.insert(node, priority);
        }

        if (sortedNodes.isEmpty())
            return false;

        return true;
    }

    void contractNodes()
    {
        meanDegree = prepareGraph.getAllEdges().getCount() / prepareGraph.getNodes();
        int level = 1;
        counter = 0;
        int initSize = sortedNodes.getSize();
        long logSize = Math.round(Math.max(10, sortedNodes.getSize() / 100 * logMessagesPercentage));
        if (logMessagesPercentage == 0)
            logSize = Integer.MAX_VALUE;

        // preparation takes longer but queries are slightly faster with preparation
        // => enable it but call not so often
        boolean periodicUpdate = true;
        StopWatch periodSW = new StopWatch();
        int updateCounter = 0;
        long periodicUpdatesCount = Math.round(Math.max(10, sortedNodes.getSize() / 100d * periodicUpdatesPercentage));
        if (periodicUpdatesPercentage == 0)
            periodicUpdate = false;

        // disable as preparation is slower and query time does not benefit
        long lastNodesLazyUpdates = lastNodesLazyUpdatePercentage == 0
                ? 0L
                : Math.round(sortedNodes.getSize() / 100d * lastNodesLazyUpdatePercentage);

        // according to paper "Polynomial-time Construction of Contraction Hierarchies for Multi-criteria Objectives" by Funke and Storandt
        // we don't need to wait for all nodes to be contracted
        long nodesToAvoidContract = Math.round((100 - nodesContractedPercentage) / 100 * sortedNodes.getSize());
        StopWatch lazySW = new StopWatch();

        // Recompute priority of uncontracted neighbors.
        // Without neighborupdates preparation is faster but we need them
        // to slightly improve query time. Also if not applied too often it decreases the shortcut number.
        boolean neighborUpdate = true;
        if (neighborUpdatePercentage == 0)
            neighborUpdate = false;

        StopWatch neighborSW = new StopWatch();
        LevelGraphStorage levelGraphCast = ((LevelGraphStorage) prepareGraph);
        while (!sortedNodes.isEmpty())
        {
            // periodically update priorities of ALL nodes            
            if (periodicUpdate && counter > 0 && counter % periodicUpdatesCount == 0)
            {
                periodSW.start();
                sortedNodes.clear();
                int len = prepareGraph.getNodes();
                for (int node = 0; node < len; node++)
                {
                    if (prepareGraph.getLevel(node) != maxLevel)
                        continue;

                    int priority = oldPriorities[node] = calculatePriority(node);
                    sortedNodes.insert(node, priority);
                }
                periodSW.stop();
                updateCounter++;
                if (sortedNodes.isEmpty())
                    throw new IllegalStateException("Cannot prepare as no unprepared nodes where found. Called preparation twice?");
            }

            if (counter % logSize == 0)
            {
                logger.info(Helper.nf(counter) + ", updates:" + updateCounter
                        + ", nodes: " + Helper.nf(sortedNodes.getSize())
                        + ", shortcuts:" + Helper.nf(newShortcuts)
                        + ", dijkstras:" + Helper.nf(dijkstraCount)
                        + ", t(dijk):" + (int) dijkstraSW.getSeconds()
                        + ", t(period):" + (int) periodSW.getSeconds()
                        + ", t(lazy):" + (int) lazySW.getSeconds()
                        + ", t(neighbor):" + (int) neighborSW.getSeconds()
                        + ", meanDegree:" + (long) meanDegree
                        + ", algo:" + prepareAlgo.getMemoryUsageAsString()
                        + ", " + Helper.getMemInfo());
                dijkstraSW = new StopWatch();
                periodSW = new StopWatch();
                lazySW = new StopWatch();
                neighborSW = new StopWatch();
            }

            counter++;
            int polledNode = sortedNodes.pollKey();
            if (sortedNodes.getSize() < lastNodesLazyUpdates)
            {
                lazySW.start();
                int priority = oldPriorities[polledNode] = calculatePriority(polledNode);
                if (!sortedNodes.isEmpty() && priority > sortedNodes.peekValue())
                {
                    // current node got more important => insert as new value and contract it later
                    sortedNodes.insert(polledNode, priority);
                    lazySW.stop();
                    continue;
                }
                lazySW.stop();
            }

            // contract!            
            newShortcuts += addShortcuts(polledNode);
            prepareGraph.setLevel(polledNode, level);
            level++;

            if (sortedNodes.getSize() < nodesToAvoidContract)
                // skipped nodes are already set to maxLevel
                break;

            EdgeSkipIterator iter = vehicleAllExplorer.setBaseNode(polledNode);
            while (iter.next())
            {
                int nn = iter.getAdjNode();
                if (prepareGraph.getLevel(nn) != maxLevel)
                    continue;

                if (neighborUpdate && rand.nextInt(100) < neighborUpdatePercentage)
                {
                    neighborSW.start();
                    int oldPrio = oldPriorities[nn];
                    int priority = oldPriorities[nn] = calculatePriority(nn);
                    if (priority != oldPrio)
                        sortedNodes.update(nn, oldPrio, priority);

                    neighborSW.stop();
                }

                levelGraphCast.disconnect(vehicleAllTmpExplorer, iter);
            }
        }

        // Preparation works only once so we can release temporary data.
        // The preparation object itself has to be intact to create the algorithm.
        close();
        logger.info("took:" + (int) allSW.stop().getSeconds()
                + ", new shortcuts: " + newShortcuts
                + ", " + prepareWeighting
                + ", " + prepareFlagEncoder
                + ", dijkstras:" + dijkstraCount
                + ", t(dijk):" + (int) dijkstraSW.getSeconds()
                + ", t(period):" + (int) periodSW.getSeconds()
                + ", t(lazy):" + (int) lazySW.getSeconds()
                + ", t(neighbor):" + (int) neighborSW.getSeconds()
                + ", meanDegree:" + (long) meanDegree
                + ", initSize:" + initSize
                + ", periodic:" + periodicUpdatesPercentage
                + ", lazy:" + lastNodesLazyUpdatePercentage
                + ", neighbor:" + neighborUpdatePercentage
                + ", " + Helper.getMemInfo());
    }

    public void close()
    {
        prepareAlgo.close();
        originalEdges.close();
        sortedNodes = null;
        oldPriorities = null;
    }

    AddShortcutHandler addScHandler = new AddShortcutHandler();
    CalcShortcutHandler calcScHandler = new CalcShortcutHandler();

    interface ShortcutHandler
    {
        void foundShortcut( int u_fromNode, int w_toNode,
                            double existingDirectWeight, double distance,
                            EdgeIterator outgoingEdges,
                            int skippedEdge1, int incomingEdgeOrigCount );

        int getNode();
    }

    class CalcShortcutHandler implements ShortcutHandler
    {
        int node;
        int originalEdgesCount;
        int shortcuts;

        public CalcShortcutHandler setNode( int n )
        {
            node = n;
            originalEdgesCount = 0;
            shortcuts = 0;
            return this;
        }

        @Override
        public int getNode()
        {
            return node;
        }

        @Override
        public void foundShortcut( int u_fromNode, int w_toNode,
                                   double existingDirectWeight, double distance,
                                   EdgeIterator outgoingEdges,
                                   int skippedEdge1, int incomingEdgeOrigCount )
        {
            shortcuts++;
            originalEdgesCount += incomingEdgeOrigCount + getOrigEdgeCount(outgoingEdges.getEdge());
        }
    }

    class AddShortcutHandler implements ShortcutHandler
    {
        int node;

        public AddShortcutHandler()
        {
        }

        @Override
        public int getNode()
        {
            return node;
        }

        public AddShortcutHandler setNode( int n )
        {
            shortcuts.clear();
            node = n;
            return this;
        }

        @Override
        public void foundShortcut( int u_fromNode, int w_toNode,
                                   double existingDirectWeight, double existingDistSum,
                                   EdgeIterator outgoingEdges,
                                   int skippedEdge1, int incomingEdgeOrigCount )
        {
            // FOUND shortcut 
            // but be sure that it is the only shortcut in the collection 
            // and also in the graph for u->w. If existing AND identical weight => update setProperties.
            // Hint: shortcuts are always one-way due to distinct level of every node but we don't
            // know yet the levels so we need to determine the correct direction or if both directions
            Shortcut sc = new Shortcut(u_fromNode, w_toNode, existingDirectWeight, existingDistSum);
            if (shortcuts.containsKey(sc))
                return;

            Shortcut tmpSc = new Shortcut(w_toNode, u_fromNode, existingDirectWeight, existingDistSum);
            Shortcut tmpRetSc = shortcuts.get(tmpSc);
            if (tmpRetSc != null)
            {
                // overwrite flags only if skipped edges are identical
                if (tmpRetSc.skippedEdge2 == skippedEdge1 && tmpRetSc.skippedEdge1 == outgoingEdges.getEdge())
                {
                    tmpRetSc.flags = PrepareEncoder.getScDirMask();
                    return;
                }
            }

            shortcuts.put(sc, sc);
            sc.skippedEdge1 = skippedEdge1;
            sc.skippedEdge2 = outgoingEdges.getEdge();
            sc.originalEdges = incomingEdgeOrigCount + getOrigEdgeCount(outgoingEdges.getEdge());
        }
    }

    Set<Shortcut> testFindShortcuts( int node )
    {
        findShortcuts(addScHandler.setNode(node));
        return shortcuts.keySet();
    }

    /**
     * Calculates the priority of adjNode v without changing the graph. Warning: the calculated
     * priority must NOT depend on priority(v) and therefor findShortcuts should also not depend on
     * the priority(v). Otherwise updating the priority before contracting in contractNodes() could
     * lead to a slowishor even endless loop.
     */
    int calculatePriority( int v )
    {
        // set of shortcuts that would be added if adjNode v would be contracted next.
        findShortcuts(calcScHandler.setNode(v));

//        System.out.println(v + "\t " + tmpShortcuts);
        // # huge influence: the bigger the less shortcuts gets created and the faster is the preparation
        //
        // every adjNode has an 'original edge' number associated. initially it is r=1
        // when a new shortcut is introduced then r of the associated edges is summed up:
        // r(u,w)=r(u,v)+r(v,w) now we can define
        // originalEdgesCount = σ(v) := sum_{ (u,w) ∈ shortcuts(v) } of r(u, w)
        int originalEdgesCount = calcScHandler.originalEdgesCount;
//        for (Shortcut sc : tmpShortcuts) {
//            originalEdgesCount += sc.originalEdges;
//        }

        // # lowest influence on preparation speed or shortcut creation count 
        // (but according to paper should speed up queries)
        //
        // number of already contracted neighbors of v
        int contractedNeighbors = 0;
        int degree = 0;
        EdgeSkipIterator iter = calcPrioAllExplorer.setBaseNode(v);
        while (iter.next())
        {
            degree++;
            if (iter.isShortcut())
                contractedNeighbors++;
        }

        // from shortcuts we can compute the edgeDifference
        // # low influence: with it the shortcut creation is slightly faster
        //
        // |shortcuts(v)| − |{(u, v) | v uncontracted}| − |{(v, w) | v uncontracted}|        
        // meanDegree is used instead of outDegree+inDegree as if one adjNode is in both directions
        // only one bucket memory is used. Additionally one shortcut could also stand for two directions.
        int edgeDifference = calcScHandler.shortcuts - degree;

        // according to the paper do a simple linear combination of the properties to get the priority.
        // this is the current optimum for unterfranken:
        return 10 * edgeDifference + originalEdgesCount + contractedNeighbors;
    }

    /**
     * Finds shortcuts, does not change the underlying graph.
     */
    void findShortcuts( ShortcutHandler sch )
    {
        long tmpDegreeCounter = 0;
        EdgeIterator incomingEdges = vehicleInExplorer.setBaseNode(sch.getNode());
        // collect outgoing nodes (goal-nodes) only once
        while (incomingEdges.next())
        {
            int u_fromNode = incomingEdges.getAdjNode();
            // accept only uncontracted nodes
            if (prepareGraph.getLevel(u_fromNode) != maxLevel)
                continue;

            double v_u_dist = incomingEdges.getDistance();
            double v_u_weight = prepareWeighting.calcWeight(incomingEdges, true, EdgeIterator.NO_EDGE);
            int skippedEdge1 = incomingEdges.getEdge();
            int incomingEdgeOrigCount = getOrigEdgeCount(skippedEdge1);
            // collect outgoing nodes (goal-nodes) only once
            EdgeIterator outgoingEdges = vehicleOutExplorer.setBaseNode(sch.getNode());
            // force fresh maps etc as this cannot be determined by from node alone (e.g. same from node but different avoidNode)
            prepareAlgo.clear();
            tmpDegreeCounter++;
            while (outgoingEdges.next())
            {
                int w_toNode = outgoingEdges.getAdjNode();
                // add only uncontracted nodes
                if (prepareGraph.getLevel(w_toNode) != maxLevel || u_fromNode == w_toNode)
                    continue;

                // Limit weight as ferries or forbidden edges can increase local search too much.
                // If we decrease the correct weight we only explore less and introduce more shortcuts.
                // I.e. no change to accuracy is made.
                double existingDirectWeight = v_u_weight + prepareWeighting.calcWeight(outgoingEdges, false, incomingEdges.getEdge());
                if (Double.isNaN(existingDirectWeight))
                    throw new IllegalStateException("Weighting should never return NaN values"
                            + ", in:" + getCoords(incomingEdges, prepareGraph) + ", out:" + getCoords(outgoingEdges, prepareGraph)
                            + ", dist:" + outgoingEdges.getDistance() + ", speed:" + prepareFlagEncoder.getSpeed(outgoingEdges.getFlags()));

                if (Double.isInfinite(existingDirectWeight))
                    continue;

                double existingDistSum = v_u_dist + outgoingEdges.getDistance();
                prepareAlgo.setWeightLimit(existingDirectWeight);
                prepareAlgo.setLimitVisitedNodes((int) meanDegree * 100)
                        .setEdgeFilter(ignoreNodeFilter.setAvoidNode(sch.getNode()));

                dijkstraSW.start();
                dijkstraCount++;
                int endNode = prepareAlgo.findEndNode(u_fromNode, w_toNode);
                dijkstraSW.stop();

                // compare end node as the limit could force dijkstra to finish earlier
                if (endNode == w_toNode && prepareAlgo.getWeight(endNode) <= existingDirectWeight)
                    // FOUND witness path, so do not add shortcut                
                    continue;

                sch.foundShortcut(u_fromNode, w_toNode,
                        existingDirectWeight, existingDistSum,
                        outgoingEdges,
                        skippedEdge1, incomingEdgeOrigCount);
            }
        }
        if (sch instanceof AddShortcutHandler)
        {
            // sliding mean value when using "*2" => slower changes
            meanDegree = (meanDegree * 2 + tmpDegreeCounter) / 3;
            // meanDegree = (meanDegree + tmpDegreeCounter) / 2;
        }
    }

    /**
     * Introduces the necessary shortcuts for adjNode v in the graph.
     */
    int addShortcuts( int v )
    {
        shortcuts.clear();
        findShortcuts(addScHandler.setNode(v));
        int tmpNewShortcuts = 0;
        NEXT_SC:
        for (Shortcut sc : shortcuts.keySet())
        {
            boolean updatedInGraph = false;
            // check if we need to update some existing shortcut in the graph
            EdgeSkipIterator iter = vehicleOutExplorer.setBaseNode(sc.from);
            while (iter.next())
            {
                if (iter.isShortcut() && iter.getAdjNode() == sc.to
                        && PrepareEncoder.canBeOverwritten(iter.getFlags(), sc.flags))
                {
                    if (sc.weight >= prepareWeighting.calcWeight(iter, false, EdgeIterator.NO_EDGE))
                        continue NEXT_SC;

                    if (iter.getEdge() == sc.skippedEdge1 || iter.getEdge() == sc.skippedEdge2)
                    {
                        throw new IllegalStateException("Shortcut cannot update itself! " + iter.getEdge()
                                + ", skipEdge1:" + sc.skippedEdge1 + ", skipEdge2:" + sc.skippedEdge2
                                + ", edge " + iter + ":" + getCoords(iter, prepareGraph)
                                + ", sc:" + sc
                                + ", skippedEdge1: " + getCoords(prepareGraph.getEdgeProps(sc.skippedEdge1, sc.from), prepareGraph)
                                + ", skippedEdge2: " + getCoords(prepareGraph.getEdgeProps(sc.skippedEdge2, sc.to), prepareGraph)
                                + ", neighbors:" + GHUtility.getNeighbors(iter));
                    }

                    // note: flags overwrite weight => call first
                    iter.setFlags(sc.flags);
                    iter.setWeight(sc.weight);
                    iter.setDistance(sc.dist);
                    iter.setSkippedEdges(sc.skippedEdge1, sc.skippedEdge2);
                    setOrigEdgeCount(iter.getEdge(), sc.originalEdges);
                    updatedInGraph = true;
                    break;
                }
            }

            if (!updatedInGraph)
            {
                EdgeSkipIterState edgeState = prepareGraph.shortcut(sc.from, sc.to);
                // note: flags overwrite weight => call first
                edgeState.setFlags(sc.flags);
                edgeState.setWeight(sc.weight);
                edgeState.setDistance(sc.dist);
                edgeState.setSkippedEdges(sc.skippedEdge1, sc.skippedEdge2);
                setOrigEdgeCount(edgeState.getEdge(), sc.originalEdges);
                tmpNewShortcuts++;
            }
        }
        return tmpNewShortcuts;
    }

    String getCoords( EdgeIteratorState e, Graph g )
    {
        NodeAccess na = g.getNodeAccess();
        int base = e.getBaseNode();
        int adj = e.getAdjNode();
        return base + "->" + adj + " (" + e.getEdge() + "); "
                + na.getLat(base) + "," + na.getLon(base) + " -> " + na.getLat(adj) + "," + na.getLon(adj);
    }

    PrepareContractionHierarchies initFromGraph()
    {
        vehicleInExplorer = prepareGraph.createEdgeExplorer(new DefaultEdgeFilter(prepareFlagEncoder, true, false));
        vehicleOutExplorer = prepareGraph.createEdgeExplorer(new DefaultEdgeFilter(prepareFlagEncoder, false, true));
        final EdgeFilter allFilter = new DefaultEdgeFilter(prepareFlagEncoder, true, true);

        // filter by vehicle and level number
        final EdgeFilter accessWithLevelFilter = new LevelEdgeFilter(prepareGraph)
        {
            @Override
            public final boolean accept( EdgeIteratorState edgeState )
            {
                if (!super.accept(edgeState))
                    return false;

                return allFilter.accept(edgeState);
            }
        };

        maxLevel = prepareGraph.getNodes() + 1;
        ignoreNodeFilter = new IgnoreNodeFilter(prepareGraph, maxLevel);
        vehicleAllExplorer = prepareGraph.createEdgeExplorer(allFilter);
        vehicleAllTmpExplorer = prepareGraph.createEdgeExplorer(allFilter);
        calcPrioAllExplorer = prepareGraph.createEdgeExplorer(accessWithLevelFilter);

        // Use an alternative to PriorityQueue as it has some advantages: 
        //   1. Gets automatically smaller if less entries are stored => less total RAM used. 
        //      Important because Graph is increasing until the end.
        //   2. is slightly faster
        //   but we need the additional oldPriorities array to keep the old value which is necessary for the update method
        sortedNodes = new GHTreeMapComposed();
        oldPriorities = new int[prepareGraph.getNodes()];
        prepareAlgo = new DijkstraOneToMany(prepareGraph, prepareFlagEncoder, prepareWeighting, traversalMode);
        return this;
    }

    public int getShortcuts()
    {
        return newShortcuts;
    }

    static class IgnoreNodeFilter implements EdgeFilter
    {
        int avoidNode;
        int maxLevel;
        LevelGraph graph;

        public IgnoreNodeFilter( LevelGraph g, int maxLevel )
        {
            this.graph = g;
            this.maxLevel = maxLevel;
        }

        public IgnoreNodeFilter setAvoidNode( int node )
        {
            this.avoidNode = node;
            return this;
        }

        @Override
        public final boolean accept( EdgeIteratorState iter )
        {
            // ignore if it is skipNode or adjNode is already contracted
            int node = iter.getAdjNode();
            return avoidNode != node && graph.getLevel(node) == maxLevel;
        }
    }

    private void setOrigEdgeCount( int index, int value )
    {
        long tmp = (long) index * 4;
        originalEdges.ensureCapacity(tmp + 4);
        originalEdges.setInt(tmp, value);
    }

    private int getOrigEdgeCount( int index )
    {
        // TODO possible memory usage improvement: avoid storing the value 1 for normal edges (does not change)!
        long tmp = (long) index * 4;
        originalEdges.ensureCapacity(tmp + 4);
        return originalEdges.getInt(tmp);
    }

    @Override
    public RoutingAlgorithm createAlgo( Graph graph, AlgorithmOptions opts )
    {
        AbstractBidirAlgo algo;
        if (AlgorithmOptions.ASTAR_BI.equals(opts.getAlgorithm()))
        {
            AStarBidirection astarBi = new AStarBidirection(graph, prepareFlagEncoder, prepareWeighting, traversalMode)
            {
                @Override
                protected void initCollections( int nodes )
                {
                    // algorithm with CH does not need that much memory pre allocated
                    super.initCollections(Math.min(initialCollectionSize, nodes));
                }

                @Override
                protected boolean finished()
                {
                    // we need to finish BOTH searches for CH!
                    if (finishedFrom && finishedTo)
                        return true;

                    // changed finish condition for CH
                    return currFrom.weight >= bestPath.getWeight() && currTo.weight >= bestPath.getWeight();
                }

                @Override
                protected boolean isWeightLimitExceeded()
                {
                    return currFrom.weight > weightLimit && currTo.weight > weightLimit;
                }

                @Override
                protected Path createAndInitPath()
                {
                    bestPath = new Path4CH(graph, graph.getBaseGraph(), flagEncoder);
                    return bestPath;
                }

                @Override
                public String getName()
                {
                    return "astarbiCH";
                }

                @Override

                public String toString()
                {
                    return getName() + "|" + prepareWeighting;
                }
            };
            algo = astarBi;
        } else if (AlgorithmOptions.DIJKSTRA_BI.equals(opts.getAlgorithm()))
        {
            algo = new DijkstraBidirectionRef(graph, prepareFlagEncoder, prepareWeighting, traversalMode)
            {
                @Override
                protected void initCollections( int nodes )
                {
                    // algorithm with CH does not need that much memory pre allocated
                    super.initCollections(Math.min(initialCollectionSize, nodes));
                }

                @Override
                public boolean finished()
                {
                    // we need to finish BOTH searches for CH!
                    if (finishedFrom && finishedTo)
                        return true;

                    // changed also the final finish condition for CH                
                    return currFrom.weight >= bestPath.getWeight() && currTo.weight >= bestPath.getWeight();
                }

                @Override
                protected boolean isWeightLimitExceeded()
                {
                    return currFrom.weight > weightLimit && currTo.weight > weightLimit;
                }

                @Override
                protected Path createAndInitPath()
                {
                    bestPath = new Path4CH(graph, graph.getBaseGraph(), flagEncoder);
                    return bestPath;
                }

                @Override
                public String getName()
                {
                    return "dijkstrabiCH";
                }

                @Override
                public String toString()
                {
                    return getName() + "|" + prepareWeighting;
                }
            };
        } else
        {
            throw new UnsupportedOperationException("Algorithm " + opts.getAlgorithm() + " not supported for Contraction Hierarchies");
        }

        algo.setEdgeFilter(levelFilter);
        return algo;
    }

    private static class PriorityNode implements Comparable<PriorityNode>
    {
        int node;
        int priority;

        public PriorityNode( int node, int priority )
        {
            this.node = node;
            this.priority = priority;
        }

        @Override
        public String toString()
        {
            return node + " (" + priority + ")";
        }

        @Override
        public int compareTo( PriorityNode o )
        {
            return priority - o.priority;
        }
    }

    class Shortcut
    {
        int from;
        int to;
        int skippedEdge1;
        int skippedEdge2;
        double dist;
        double weight;
        int originalEdges;
        long flags = PrepareEncoder.getScFwdDir();

        public Shortcut( int from, int to, double weight, double dist )
        {
            this.from = from;
            this.to = to;
            this.weight = weight;
            this.dist = dist;
        }

        @Override
        public int hashCode()
        {
            int hash = 5;
            hash = 23 * hash + from;
            hash = 23 * hash + to;
            return 23 * hash
                    + (int) (Double.doubleToLongBits(this.weight) ^ (Double.doubleToLongBits(this.weight) >>> 32));
        }

        @Override
        public boolean equals( Object obj )
        {
            if (obj == null || getClass() != obj.getClass())
                return false;

            final Shortcut other = (Shortcut) obj;
            if (this.from != other.from || this.to != other.to)
                return false;

            return Double.doubleToLongBits(this.weight) == Double.doubleToLongBits(other.weight);
        }

        @Override
        public String toString()
        {
            String str;
            if (flags == PrepareEncoder.getScDirMask())
                str = from + "<->";
            else
                str = from + "->";

            return str + to + ", weight:" + weight + " (" + skippedEdge1 + "," + skippedEdge2 + ")";
        }
    }

    @Override
    public String toString()
    {
        return "PREPARE|CH|dijkstrabi";
    }
}


File: core/src/main/java/com/graphhopper/routing/util/LevelEdgeFilter.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing.util;

import com.graphhopper.storage.LevelGraph;
import com.graphhopper.util.EdgeIteratorState;
import com.graphhopper.util.EdgeSkipIterState;
import com.graphhopper.util.EdgeSkipIterator;

/**
 * Only certain nodes are accepted and therefor the others are ignored.
 * <p/>
 * @author Peter Karich
 */
public class LevelEdgeFilter implements EdgeFilter
{
    private final LevelGraph graph;
    private final int maxNodes;

    public LevelEdgeFilter( LevelGraph g )
    {
        graph = g;
        maxNodes = g.getNodes();
    }

    @Override
    public boolean accept( EdgeIteratorState edgeIterState )
    {
        int base = edgeIterState.getBaseNode();
        int adj = edgeIterState.getAdjNode();
        // always accept virtual edges, see #288
        if (base >= maxNodes || adj >= maxNodes)
            return true;

        // minor performance improvement: shortcuts in wrong direction are disconnected, so no need to exclude them
        if (((EdgeSkipIterState) edgeIterState).isShortcut())
            return true;

        return graph.getLevel(base) <= graph.getLevel(adj);
    }
}


File: core/src/main/java/com/graphhopper/routing/util/PrepareRoutingSubnetworks.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing.util;

import com.graphhopper.coll.GHBitSet;
import com.graphhopper.coll.GHBitSetImpl;
import com.graphhopper.storage.GraphStorage;
import com.graphhopper.util.*;

import java.util.*;
import java.util.Map.Entry;
import java.util.concurrent.atomic.AtomicInteger;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import gnu.trove.list.array.TIntArrayList;

/**
 * Removes nodes which are not part of the largest network. Ie. mostly nodes with no edges at all
 * but also small subnetworks which are nearly always bugs in OSM data or indicate otherwise
 * disconnected areas e.g. via barriers - see #86.
 * <p/>
 * @author Peter Karich
 */
public class PrepareRoutingSubnetworks
{
    private final Logger logger = LoggerFactory.getLogger(getClass());
    private final GraphStorage g;
    private final EdgeFilter edgeFilter;
    private int minNetworkSize = 200;
    private int minOneWayNetworkSize = 0;
    private int subNetworks = -1;
    private final AtomicInteger maxEdgesPerNode = new AtomicInteger(0);
    private FlagEncoder singleEncoder;

    public PrepareRoutingSubnetworks( GraphStorage g, EncodingManager em )
    {
        this.g = g;
        List<FlagEncoder> encoders = em.fetchEdgeEncoders();
        if (encoders.size() > 1)
            edgeFilter = EdgeFilter.ALL_EDGES;
        else
            edgeFilter = new DefaultEdgeFilter(singleEncoder = encoders.get(0));
    }

    public PrepareRoutingSubnetworks setMinNetworkSize( int minNetworkSize )
    {
        this.minNetworkSize = minNetworkSize;
        return this;
    }

    public PrepareRoutingSubnetworks setMinOneWayNetworkSize( int minOnewayNetworkSize )
    {
        this.minOneWayNetworkSize = minOnewayNetworkSize;
        return this;
    }

    public void doWork()
    {
        int del = removeZeroDegreeNodes();
        Map<Integer, Integer> map = findSubnetworks();
        keepLargeNetworks(map);

        int unvisitedDeadEnds = -1;
        if (minOneWayNetworkSize > 0 && singleEncoder != null)
            unvisitedDeadEnds = removeDeadEndUnvisitedNetworks(singleEncoder);

        logger.info("optimize to remove subnetworks (" + map.size() + "), zero-degree-nodes (" + del + "), "
                + "unvisited-dead-end-nodes(" + unvisitedDeadEnds + "), "
                + "maxEdges/node (" + maxEdgesPerNode.get() + ")");
        g.optimize();
        subNetworks = map.size();
    }

    public int getSubNetworks()
    {
        return subNetworks;
    }

    public Map<Integer, Integer> findSubnetworks()
    {
        return findSubnetworks(g.createEdgeExplorer(edgeFilter));
    }

    private Map<Integer, Integer> findSubnetworks( final EdgeExplorer explorer )
    {
        final Map<Integer, Integer> map = new HashMap<Integer, Integer>();
        final AtomicInteger integ = new AtomicInteger(0);
        int locs = g.getNodes();
        final GHBitSet bs = new GHBitSetImpl(locs);
        for (int start = 0; start < locs; start++)
        {
            if (g.isNodeRemoved(start) || bs.contains(start))
                continue;

            if (start == 1599634)
            {
                locs = g.getNodes();
            }

            new BreadthFirstSearch()
            {
                int tmpCounter = 0;

                @Override
                protected GHBitSet createBitSet()
                {
                    return bs;
                }

                @Override
                protected final boolean goFurther( int nodeId )
                {
                    if (tmpCounter > maxEdgesPerNode.get())
                        maxEdgesPerNode.set(tmpCounter);

                    tmpCounter = 0;
                    integ.incrementAndGet();
                    return true;
                }

                @Override
                protected final boolean checkAdjacent( EdgeIteratorState iter )
                {
                    tmpCounter++;
                    return true;
                }

            }.start(explorer, start);
            map.put(start, integ.get());
            integ.set(0);
        }
        return map;
    }

    /**
     * Deletes all but the largest subnetworks.
     */
    void keepLargeNetworks( Map<Integer, Integer> map )
    {
        if (map.size() <= 1)
            return;

        int biggestStart = -1;
        int maxCount = -1;
        int allRemoved = 0;
        GHBitSetImpl bs = new GHBitSetImpl(g.getNodes());
        for (Entry<Integer, Integer> e : map.entrySet())
        {
            if (biggestStart < 0)
            {
                biggestStart = e.getKey();
                maxCount = e.getValue();
                continue;
            }

            int removed;
            if (maxCount < e.getValue())
            {
                // new biggest area found. remove old
                removed = removeNetwork(biggestStart, maxCount, bs);

                biggestStart = e.getKey();
                maxCount = e.getValue();
            } else
            {
                removed = removeNetwork(e.getKey(), e.getValue(), bs);
            }

            allRemoved += removed;
            if (removed > g.getNodes() / 3)
                throw new IllegalStateException("Too many nodes were removed: " + removed + ", all nodes:" + g.getNodes() + ", all removed:" + allRemoved);
        }

        if (allRemoved > g.getNodes() / 2)
            throw new IllegalStateException("Too many total nodes were removed: " + allRemoved + ", all nodes:" + g.getNodes());
    }

    /**
     * Deletes the complete subnetwork reachable through start
     */
    int removeNetwork( int start, int entries, final GHBitSet bs )
    {
        if (entries >= minNetworkSize)
        {
            // logger.info("did not remove large network (" + entries + ")");
            return 0;
        }

        final AtomicInteger removed = new AtomicInteger(0);
        EdgeExplorer explorer = g.createEdgeExplorer(edgeFilter);
        new BreadthFirstSearch()
        {
            @Override
            protected GHBitSet createBitSet()
            {
                return bs;
            }

            @Override
            protected boolean goFurther( int nodeId )
            {
                g.markNodeRemoved(nodeId);
                removed.incrementAndGet();
                return super.goFurther(nodeId);
            }
        }.start(explorer, start);

        if (entries != removed.get())
            throw new IllegalStateException("Did not expect " + removed.get() + " removed nodes; "
                    + " Expected:" + entries + ", all nodes:" + g.getNodes() + "; "
                    + " Neighbours:" + toString(explorer.setBaseNode(start)) + "; "
                    + " Start:" + start + "  (" + g.getNodeAccess().getLat(start) + "," + g.getNodeAccess().getLon(start) + ")");

        return removed.get();
    }

    String toString( EdgeIterator iter )
    {
        String str = "";
        while (iter.next())
        {
            int adjNode = iter.getAdjNode();
            str += adjNode + " (" + g.getNodeAccess().getLat(adjNode) + "," + g.getNodeAccess().getLon(adjNode) + "), ";
            str += "speed  (fwd:" + singleEncoder.getSpeed(iter.getFlags()) + ", rev:" + singleEncoder.getReverseSpeed(iter.getFlags()) + "), ";
            str += "access (fwd:" + singleEncoder.isForward(iter.getFlags()) + ", rev:" + singleEncoder.isBackward(iter.getFlags()) + "), ";
            str += "distance:" + iter.getDistance();
            str += ";\n ";
        }
        return str;
    }

    /**
     * To avoid large processing and a large HashMap remove nodes with no edges up front
     * <p/>
     * @return removed nodes
     */
    int removeZeroDegreeNodes()
    {
        int removed = 0;
        int locs = g.getNodes();
        EdgeExplorer explorer = g.createEdgeExplorer();
        for (int start = 0; start < locs; start++)
        {
            EdgeIterator iter = explorer.setBaseNode(start);
            if (!iter.next())
            {
                removed++;
                g.markNodeRemoved(start);
            }
        }
        return removed;
    }

    /**
     * Clean small networks that will be never be visited by this explorer See #86 for example,
     * small areas like parking lots are sometimes connected to the whole network through a one-way
     * road. This is clearly an error - but is causes the routing to fail when a point gets
     * connected to this small area. This routine removes all these points from the graph.
     * <p/>
     * @return number of removed nodes
     */
    public int removeDeadEndUnvisitedNetworks( final FlagEncoder encoder )
    {
        // Partition g into strongly connected components using Tarjan's algorithm.
        final EdgeFilter filter = new DefaultEdgeFilter(encoder, false, true);
        List<TIntArrayList> components = new TarjansStronglyConnectedComponentsAlgorithm(g, filter).findComponents();

        // remove components less than minimum size
        int removedNodes = 0;
        for (TIntArrayList component : components)
        {
            if (component.size() < minOneWayNetworkSize)
            {
                for (int i = 0; i < component.size(); i++)
                {
                    g.markNodeRemoved(component.get(i));
                    removedNodes++;
                }
            }
        }
        return removedNodes;
    }
}


File: core/src/main/java/com/graphhopper/routing/util/TarjansStronglyConnectedComponentsAlgorithm.java
package com.graphhopper.routing.util;

import com.graphhopper.coll.GHBitSetImpl;
import com.graphhopper.storage.GraphStorage;
import com.graphhopper.util.EdgeIterator;
import gnu.trove.list.array.TIntArrayList;
import gnu.trove.stack.array.TIntArrayStack;

import java.util.ArrayList;
import java.util.List;
import java.util.Stack;

/**
 * Implementation of Tarjan's algorithm using an explicit stack.
 * (The traditional recursive approach runs into stack overflow pretty quickly.)
 * <p/>
 * Used for finding strongly connected components to detect dead-ends.
 * <p/>
 * http://en.wikipedia.org/wiki/Tarjan's_strongly_connected_components_algorithm
 */
public class TarjansStronglyConnectedComponentsAlgorithm
{

    private final GraphStorage g;
    private final TIntArrayStack nodeStack;
    private final GHBitSetImpl onStack;
    private final int[] nodeIndex;
    private final int[] nodeLowLink;
    private final ArrayList<TIntArrayList> components = new ArrayList<TIntArrayList>();

    private int index = 1;
    private final EdgeFilter edgeFilter;

    public TarjansStronglyConnectedComponentsAlgorithm( final GraphStorage g, final EdgeFilter edgeFilter )
    {
        this.g = g;
        this.nodeStack = new TIntArrayStack();
        this.onStack = new GHBitSetImpl(g.getNodes());
        this.nodeIndex = new int[g.getNodes()];
        this.nodeLowLink = new int[g.getNodes()];
        this.edgeFilter = edgeFilter;
    }

    /**
     * Find and return list of all strongly connected components in g.
     */
    public List<TIntArrayList> findComponents()
    {

        int nodes = g.getNodes();
        for (int start = 0; start < nodes; start++)
        {
            if (nodeIndex[start] == 0 && !g.isNodeRemoved(start))
            {
                strongConnect(start);
            }
        }

        return components;
    }

    // Find all components reachable from firstNode, add them to 'components'
    private void strongConnect( int firstNode )
    {
        final Stack<TarjanState> stateStack = new Stack<TarjanState>();
        stateStack.push(TarjanState.startState(firstNode));

        // nextState label is equivalent to the function entry point in the recursive Tarjan's algorithm.
        nextState:

        while (!stateStack.empty())
        {
            TarjanState state = stateStack.pop();
            final int start = state.start;
            final EdgeIterator iter;

            if (state.isStart())
            {
                // We're traversing a new node 'start'.  Set the depth index for this node to the smallest unused index.
                nodeIndex[start] = index;
                nodeLowLink[start] = index;
                index++;
                nodeStack.push(start);
                onStack.set(start);

                iter = g.createEdgeExplorer(edgeFilter).setBaseNode(start);

            } else
            { // if (state.isResume()) {

                // We're resuming iteration over the next child of 'start', set lowLink as appropriate.
                iter = state.iter;

                int prevConnectedId = iter.getAdjNode();
                nodeLowLink[start] = Math.min(nodeLowLink[start], nodeLowLink[prevConnectedId]);
            }

            // Each element (excluding the first) in the current component should be able to find
            // a successor with a lower nodeLowLink.
            while (iter.next())
            {
                int connectedId = iter.getAdjNode();
                if (nodeIndex[connectedId] == 0)
                {
                    // Push resume and start states onto state stack to continue our DFS through the graph after the jump.
                    // Ideally we'd just call strongConnectIterative(connectedId);
                    stateStack.push(TarjanState.resumeState(start, iter));
                    stateStack.push(TarjanState.startState(connectedId));
                    continue nextState;
                } else if (onStack.contains(connectedId))
                {
                    nodeLowLink[start] = Math.min(nodeLowLink[start], nodeIndex[connectedId]);
                }
            }

            // If nodeLowLink == nodeIndex, then we are the first element in a component.
            // Add all nodes higher up on nodeStack to this component.
            if (nodeIndex[start] == nodeLowLink[start])
            {
                TIntArrayList component = new TIntArrayList();
                int node;
                while ((node = nodeStack.pop()) != start)
                {
                    component.add(node);
                    onStack.clear(node);
                }
                component.add(start);
                onStack.clear(start);

                components.add(component);
            }
        }
    }

    // Internal stack state of algorithm, used to avoid recursive function calls and hitting stack overflow exceptions.
    // State is either 'start' for new nodes or 'resume' for partially traversed nodes.
    private static class TarjanState
    {
        final int start;
        final EdgeIterator iter;

        // Iterator only present in 'resume' state.
        boolean isStart()
        {
            return iter == null;
        }

        private TarjanState( final int start, final EdgeIterator iter )
        {
            this.start = start;
            this.iter = iter;
        }

        public static TarjanState startState( int start )
        {
            return new TarjanState(start, null);
        }

        public static TarjanState resumeState( int start, EdgeIterator iter )
        {
            return new TarjanState(start, iter);
        }
    }
}


File: core/src/main/java/com/graphhopper/routing/util/TestAlgoCollector.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing.util;

import com.graphhopper.GHResponse;
import com.graphhopper.routing.*;
import com.graphhopper.storage.Graph;
import com.graphhopper.storage.TurnCostExtension;
import com.graphhopper.storage.index.LocationIndex;
import com.graphhopper.storage.index.QueryResult;
import com.graphhopper.util.*;
import com.graphhopper.util.shapes.GHPoint;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * @author Peter Karich
 */
public class TestAlgoCollector
{
    private final String name;
    private final DistanceCalc distCalc = Helper.DIST_EARTH;
    private final TranslationMap trMap = new TranslationMap().doImport();
    public final List<String> errors = new ArrayList<String>();

    public TestAlgoCollector( String name )
    {
        this.name = name;
    }

    public TestAlgoCollector assertDistance( AlgoHelperEntry algoEntry, List<QueryResult> queryList,
                                             OneRun oneRun )
    {
        List<Path> viaPaths = new ArrayList<Path>();
        QueryGraph queryGraph = new QueryGraph(algoEntry.getQueryGraph());
        queryGraph.lookup(queryList);
        AlgorithmOptions opts = algoEntry.opts;
        FlagEncoder encoder = opts.getFlagEncoder();
        if (encoder.supports(TurnWeighting.class))
            algoEntry.setAlgorithmOptions(AlgorithmOptions.start(opts).weighting(new TurnWeighting(opts.getWeighting(), opts.getFlagEncoder(), (TurnCostExtension) queryGraph.getExtension())).build());

        for (int i = 0; i < queryList.size() - 1; i++)
        {
            Path path = algoEntry.createAlgo(queryGraph).
                    calcPath(queryList.get(i).getClosestNode(), queryList.get(i + 1).getClosestNode());
            // System.out.println(path.calcInstructions().createGPX("temp", 0, "GMT"));
            viaPaths.add(path);
        }

        PathMerger pathMerger = new PathMerger().
                setCalcPoints(true).
                setSimplifyResponse(false).
                setEnableInstructions(true);
        GHResponse rsp = new GHResponse();
        pathMerger.doWork(rsp, viaPaths, trMap.getWithFallBack(Locale.US));

        if (rsp.hasErrors())
        {
            errors.add(algoEntry + " response contains errors. Expected distance: " + rsp.getDistance()
                    + ", expected points: " + oneRun + ". " + queryList + ", errors:" + rsp.getErrors());
            return this;
        }

        PointList pointList = rsp.getPoints();
        double tmpDist = pointList.calcDistance(distCalc);
        if (Math.abs(rsp.getDistance() - tmpDist) > 2)
        {
            errors.add(algoEntry + " path.getDistance was  " + rsp.getDistance()
                    + "\t pointList.calcDistance was " + tmpDist + "\t (expected points " + oneRun.getLocs()
                    + ", expected distance " + oneRun.getDistance() + ") " + queryList);
        }

        if (Math.abs(rsp.getDistance() - oneRun.getDistance()) > 2)
        {
            errors.add(algoEntry + " returns path not matching the expected distance of " + oneRun.getDistance()
                    + "\t Returned was " + rsp.getDistance() + "\t (expected points " + oneRun.getLocs()
                    + ", was " + pointList.getSize() + ") " + queryList);
        }

        // There are real world instances where A-B-C is identical to A-C (in meter precision).
        if (Math.abs(pointList.getSize() - oneRun.getLocs()) > 1)
        {
            errors.add(algoEntry + " returns path not matching the expected points of " + oneRun.getLocs()
                    + "\t Returned was " + pointList.getSize() + "\t (expected distance " + oneRun.getDistance()
                    + ", was " + rsp.getDistance() + ") " + queryList);
        }
        return this;
    }

    void queryIndex( Graph g, LocationIndex idx, double lat, double lon, double expectedDist )
    {
        QueryResult res = idx.findClosest(lat, lon, EdgeFilter.ALL_EDGES);
        if (!res.isValid())
        {
            errors.add("node not found for " + lat + "," + lon);
            return;
        }

        GHPoint found = res.getSnappedPoint();
        double dist = distCalc.calcDist(lat, lon, found.lat, found.lon);
        if (Math.abs(dist - expectedDist) > .1)
        {
            errors.add("queried lat,lon=" + (float) lat + "," + (float) lon
                    + " (found: " + (float) found.lat + "," + (float) found.lon + ")"
                    + "\n   expected distance:" + expectedDist + ", but was:" + dist);
        }
    }

    @Override
    public String toString()
    {
        String str = "";
        str += "FOUND " + errors.size() + " ERRORS.\n";
        for (String s : errors)
        {
            str += s + ".\n";
        }
        return str;
    }

    void printSummary()
    {
        if (errors.size() > 0)
        {
            System.out.println("\n-------------------------------\n");
            System.out.println(toString());
        } else
        {
            System.out.println("SUCCESS for " + name + "!");
        }
    }

    public static class AlgoHelperEntry
    {
        private Graph queryGraph;
        private final LocationIndex idx;
        private AlgorithmOptions opts;

        public AlgoHelperEntry( Graph g, AlgorithmOptions opts, LocationIndex idx )
        {
            this.queryGraph = g;
            this.opts = opts;
            this.idx = idx;
        }

        public Graph getQueryGraph()
        {
            return queryGraph;
        }

        public void setQueryGraph( Graph queryGraph )
        {
            this.queryGraph = queryGraph;
        }

        public void setAlgorithmOptions( AlgorithmOptions opts )
        {
            this.opts = opts;
        }

        public LocationIndex getIdx()
        {
            return idx;
        }

        public RoutingAlgorithm createAlgo( Graph qGraph )
        {
            return new RoutingAlgorithmFactorySimple().createAlgo(qGraph, opts);
        }

        @Override
        public String toString()
        {
            return opts.getAlgorithm();
        }
    }

    public static class OneRun
    {
        private final List<AssumptionPerPath> assumptions = new ArrayList<AssumptionPerPath>();

        public OneRun()
        {
        }

        public OneRun( double fromLat, double fromLon, double toLat, double toLon, double dist, int locs )
        {
            add(fromLat, fromLon, 0, 0);
            add(toLat, toLon, dist, locs);
        }

        public OneRun add( double lat, double lon, double dist, int locs )
        {
            assumptions.add(new AssumptionPerPath(lat, lon, dist, locs));
            return this;
        }

        public int getLocs()
        {
            int sum = 0;
            for (AssumptionPerPath as : assumptions)
            {
                sum += as.locs;
            }
            return sum;
        }

        public void setLocs( int index, int locs )
        {
            assumptions.get(index).locs = locs;
        }

        public double getDistance()
        {
            double sum = 0;
            for (AssumptionPerPath as : assumptions)
            {
                sum += as.distance;
            }
            return sum;
        }

        public void setDistance( int index, double dist )
        {
            assumptions.get(index).distance = dist;
        }

        public List<QueryResult> getList( LocationIndex idx, EdgeFilter edgeFilter )
        {
            List<QueryResult> qr = new ArrayList<QueryResult>();
            for (AssumptionPerPath p : assumptions)
            {
                qr.add(idx.findClosest(p.lat, p.lon, edgeFilter));
            }
            return qr;
        }

        @Override
        public String toString()
        {
            return assumptions.toString();
        }
    }

    static class AssumptionPerPath
    {
        double lat, lon;
        int locs;
        double distance;

        public AssumptionPerPath( double lat, double lon, double distance, int locs )
        {
            this.lat = lat;
            this.lon = lon;
            this.locs = locs;
            this.distance = distance;
        }

        @Override
        public String toString()
        {
            return lat + ", " + lon + ", locs:" + locs + ", dist:" + distance;
        }
    }
}


File: core/src/main/java/com/graphhopper/storage/BaseGraph.java
/*
 *  Licensed to Peter Karich under one or more contributor license
 *  agreements. See the NOTICE file distributed with this work for
 *  additional information regarding copyright ownership.
 *
 *  Peter Karich licenses this file to you under the Apache License,
 *  Version 2.0 (the "License"); you may not use this file except
 *  in compliance with the License. You may obtain a copy of the
 *  License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.storage;

import com.graphhopper.routing.util.AllEdgesIterator;
import com.graphhopper.routing.util.AllEdgesSkipIterator;
import com.graphhopper.routing.util.EdgeFilter;
import com.graphhopper.util.EdgeExplorer;
import com.graphhopper.util.EdgeIteratorState;
import com.graphhopper.util.EdgeSkipIterator;
import com.graphhopper.util.PointList;
import com.graphhopper.util.shapes.BBox;

/**
 * @author Peter Karich
 */
class BaseGraph implements Graph
{
    private final LevelGraph lg;

    BaseGraph( LevelGraph lg )
    {
        this.lg = lg;
    }

    @Override
    public Graph getBaseGraph()
    {
        return this;
    }

    @Override
    public int getNodes()
    {
        return lg.getNodes();
    }

    @Override
    public NodeAccess getNodeAccess()
    {
        return lg.getNodeAccess();
    }

    @Override
    public BBox getBounds()
    {
        return lg.getBounds();
    }

    @Override
    public EdgeIteratorState edge( int a, int b )
    {
        return lg.edge(a, b);
    }

    @Override
    public EdgeIteratorState edge( int a, int b, double distance, boolean bothDirections )
    {
        return lg.edge(a, b, distance, bothDirections);
    }

    @Override
    public EdgeIteratorState getEdgeProps( int edgeId, int adjNode )
    {
        if (lg.isShortcut(edgeId))
            throw new IllegalStateException("Do not fetch shortcuts from BaseGraph use the LevelGraph instead");

        return lg.getEdgeProps(edgeId, adjNode);
    }

    @Override
    public AllEdgesIterator getAllEdges()
    {
        final AllEdgesSkipIterator tmpIter = lg.getAllEdges();
        return new AllEdgesIterator()
        {
            @Override
            public int getCount()
            {
                return tmpIter.getCount();
            }

            @Override
            public boolean next()
            {
                while (tmpIter.next())
                {
                    if (!tmpIter.isShortcut())
                    {
                        return true;
                    }
                }
                return false;
            }

            @Override
            public int getEdge()
            {
                return tmpIter.getEdge();
            }

            @Override
            public int getBaseNode()
            {
                return tmpIter.getBaseNode();
            }

            @Override
            public int getAdjNode()
            {
                return tmpIter.getAdjNode();
            }

            @Override
            public PointList fetchWayGeometry( int type )
            {
                return tmpIter.fetchWayGeometry(type);
            }

            @Override
            public EdgeIteratorState setWayGeometry( PointList list )
            {
                return tmpIter.setWayGeometry(list);
            }

            @Override
            public double getDistance()
            {
                return tmpIter.getDistance();
            }

            @Override
            public EdgeIteratorState setDistance( double dist )
            {
                return tmpIter.setDistance(dist);
            }

            @Override
            public long getFlags()
            {
                return tmpIter.getFlags();
            }

            @Override
            public EdgeIteratorState setFlags( long flags )
            {
                return tmpIter.setFlags(flags);
            }

            @Override
            public String getName()
            {
                return tmpIter.getName();
            }

            @Override
            public EdgeIteratorState setName( String name )
            {
                return tmpIter.setName(name);
            }

            @Override
            public int getAdditionalField()
            {
                return tmpIter.getAdditionalField();
            }

            @Override
            public EdgeIteratorState setAdditionalField( int value )
            {
                return tmpIter.setAdditionalField(value);
            }

            @Override
            public EdgeIteratorState copyPropertiesTo( EdgeIteratorState edge )
            {
                return tmpIter.copyPropertiesTo(edge);
            }

            @Override
            public EdgeIteratorState detach( boolean reverse )
            {
                return tmpIter.detach(reverse);
            }
        };
    }

    @Override
    public EdgeExplorer createEdgeExplorer( final EdgeFilter filter )
    {
        if (filter == EdgeFilter.ALL_EDGES)
            return createEdgeExplorer();

        return lg.createEdgeExplorer(new EdgeFilter()
        {
            @Override
            public boolean accept( EdgeIteratorState edgeIterState )
            {
                if (((EdgeSkipIterator) edgeIterState).isShortcut())
                    return false;

                return filter.accept(edgeIterState);
            }
        });
    }

    private final static EdgeFilter NO_SHORTCUTS = new EdgeFilter()
    {
        @Override
        public boolean accept( EdgeIteratorState edgeIterState )
        {
            return !((EdgeSkipIterator) edgeIterState).isShortcut();
        }
    };

    @Override
    public EdgeExplorer createEdgeExplorer()
    {
        return lg.createEdgeExplorer(NO_SHORTCUTS);
    }

    @Override
    public Graph copyTo( Graph g )
    {
        throw new UnsupportedOperationException("Not supported yet.");
    }

    @Override
    public GraphExtension getExtension()
    {
        return lg.getExtension();
    }
}


File: core/src/main/java/com/graphhopper/storage/GHNodeAccess.java
/*
 *  Licensed to Peter Karich under one or more contributor license
 *  agreements. See the NOTICE file distributed with this work for
 *  additional information regarding copyright ownership.
 *
 *  Peter Karich licenses this file to you under the Apache License,
 *  Version 2.0 (the "License"); you may not use this file except
 *  in compliance with the License. You may obtain a copy of the
 *  License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.storage;

import com.graphhopper.util.Helper;

/**
 * A helper class for GraphHopperStorage for its node access.
 * <p/>
 * @author Peter Karich
 */
class GHNodeAccess implements NodeAccess
{
    private final GraphHopperStorage that;
    private final boolean elevation;

    public GHNodeAccess( GraphHopperStorage that, boolean withElevation )
    {
        this.that = that;
        this.elevation = withElevation;
    }

    @Override
    public void ensureNode( int nodeId )
    {
        that.ensureNodeIndex(nodeId);
    }

    @Override
    public final void setNode( int nodeId, double lat, double lon )
    {
        setNode(nodeId, lat, lon, Double.NaN);
    }

    @Override
    public final void setNode( int nodeId, double lat, double lon, double ele )
    {
        that.ensureNodeIndex(nodeId);
        long tmp = (long) nodeId * that.nodeEntryBytes;
        that.nodes.setInt(tmp + that.N_LAT, Helper.degreeToInt(lat));
        that.nodes.setInt(tmp + that.N_LON, Helper.degreeToInt(lon));

        if (is3D())
        {
            // meter precision is sufficient for now
            that.nodes.setInt(tmp + that.N_ELE, Helper.eleToInt(ele));
            that.bounds.update(lat, lon, ele);

        } else
        {
            that.bounds.update(lat, lon);
        }

        // set the default value for the additional field of this node
        if (that.extStorage.isRequireNodeField())
            that.nodes.setInt(tmp + that.N_ADDITIONAL, that.extStorage.getDefaultNodeFieldValue());
    }

    @Override
    public final double getLatitude( int nodeId )
    {
        return Helper.intToDegree(that.nodes.getInt((long) nodeId * that.nodeEntryBytes + that.N_LAT));
    }

    @Override
    public final double getLongitude( int nodeId )
    {
        return Helper.intToDegree(that.nodes.getInt((long) nodeId * that.nodeEntryBytes + that.N_LON));
    }

    @Override
    public final double getElevation( int nodeId )
    {
        if (!elevation)
            throw new IllegalStateException("Cannot access elevation - 3D is not enabled");

        return Helper.intToEle(that.nodes.getInt((long) nodeId * that.nodeEntryBytes + that.N_ELE));
    }

    @Override
    public final double getEle( int nodeId )
    {
        return getElevation(nodeId);
    }

    @Override
    public final double getLat( int nodeId )
    {
        return getLatitude(nodeId);
    }

    @Override
    public final double getLon( int nodeId )
    {
        return getLongitude(nodeId);
    }

    @Override
    public final void setAdditionalNodeField( int index, int additionalValue )
    {
        if (that.extStorage.isRequireNodeField() && that.N_ADDITIONAL >= 0)
        {
            that.ensureNodeIndex(index);
            long tmp = (long) index * that.nodeEntryBytes;
            that.nodes.setInt(tmp + that.N_ADDITIONAL, additionalValue);
        } else
        {
            throw new AssertionError("This graph does not provide an additional node field");
        }
    }

    @Override
    public final int getAdditionalNodeField( int index )
    {
        if (that.extStorage.isRequireNodeField() && that.N_ADDITIONAL >= 0)
            return that.nodes.getInt((long) index * that.nodeEntryBytes + that.N_ADDITIONAL);
        else
            throw new AssertionError("This graph does not provide an additional node field");
    }

    @Override
    public final boolean is3D()
    {
        return elevation;
    }

    @Override
    public int getDimension()
    {
        if (elevation)
            return 3;
        return 2;
    }
}


File: core/src/main/java/com/graphhopper/storage/Graph.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.storage;

import com.graphhopper.routing.util.EdgeFilter;
import com.graphhopper.routing.util.AllEdgesIterator;
import com.graphhopper.util.EdgeExplorer;
import com.graphhopper.util.EdgeIteratorState;
import com.graphhopper.util.shapes.BBox;

/**
 * An interface to represent a (geo) graph - suited for efficient storage as it can be requested via
 * indices called node IDs. To get the lat,lon point you need to set up a Location2IDIndex instance.
 * <p/>
 * @author Peter Karich
 */
public interface Graph
{
    /**
     * @return a graph which behaves like an unprepared graph and e.g. the normal unidirectional
     * Dijkstra or any graph traversal algorithm can be executed.
     */
    Graph getBaseGraph();

    /**
     * @return the number of created locations - via setNode() or edge()
     */
    int getNodes();

    /**
     * Creates a node explorer to access node properties.
     */
    NodeAccess getNodeAccess();

    /**
     * Returns the implicit bounds of this graph calculated from the lat,lon input of setNode
     */
    BBox getBounds();

    /**
     * Creates an edge between the nodes a and b. To set distance or access use the returned edge
     * and e.g. edgeState.setDistance
     * <p/>
     * @param a the index of the starting (tower) node of the edge
     * @param b the index of the ending (tower) node of the edge
     * @return the newly created edge
     */
    EdgeIteratorState edge( int a, int b );

    /**
     * Use edge(a,b).setDistance().setFlags instead
     */
    EdgeIteratorState edge( int a, int b, double distance, boolean bothDirections );

    /**
     * Returns a wrapper over the specified edgeId.
     * <p/>
     * @param adjNode is the node that will be returned via adjNode(). If adjNode is
     * Integer.MIN_VALUE then the edge with undefined values for adjNode and baseNode will be
     * returned.
     * @return an edge iterator state
     * @throws IllegalStateException if edgeId is not valid
     */
    EdgeIteratorState getEdgeProps( int edgeId, int adjNode );

    /**
     * @return all edges in this graph, where baseNode will be the smaller node.
     */
    AllEdgesIterator getAllEdges();

    /**
     * Returns an iterator which makes it possible to traverse all edges of the specified node if
     * the filter accepts the edge. Reduce calling this method as much as possible, e.g. create it
     * before a for loop!
     * <p/>
     * @see Graph#createEdgeExplorer()
     */
    EdgeExplorer createEdgeExplorer( EdgeFilter filter );

    /**
     * Returns all the edges reachable from the specified index. Same behaviour as
     * graph.getEdges(index, EdgeFilter.ALL_EDGES);
     * <p/>
     * @return all edges regardless of the vehicle type or direction.
     */
    EdgeExplorer createEdgeExplorer();

    /**
     * Copy this Graph into the specified Graph g.
     * <p/>
     * @return the specified GraphStorage g
     */
    Graph copyTo( Graph g );

    /**
     * @return the graph extension like a TurnCostExtension
     */
    GraphExtension getExtension();
}


File: core/src/main/java/com/graphhopper/storage/GraphBuilder.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 *
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.storage;

import com.graphhopper.routing.util.EncodingManager;

/**
 * For now this is just a helper class to quickly create a GraphStorage.
 * <p/>
 * @author Peter Karich
 */
public class GraphBuilder
{
    private final EncodingManager encodingManager;
    private String location;
    private boolean mmap;
    private boolean store;
    private boolean level;
    private boolean elevation;
    private long byteCapacity = 100;

    public GraphBuilder( EncodingManager encodingManager )
    {
        this.encodingManager = encodingManager;
    }

    /**
     * If true builder will create a LevelGraph
     * <p/>
     * @see LevelGraph
     */
    public GraphBuilder setLevelGraph( boolean level )
    {
        this.level = level;
        return this;
    }

    public GraphBuilder setLocation( String location )
    {
        this.location = location;
        return this;
    }

    public GraphBuilder setStore( boolean store )
    {
        this.store = store;
        return this;
    }

    public GraphBuilder setMmap( boolean mmap )
    {
        this.mmap = mmap;
        return this;
    }

    public GraphBuilder setExpectedSize( byte cap )
    {
        this.byteCapacity = cap;
        return this;
    }

    public GraphBuilder set3D( boolean withElevation )
    {
        this.elevation = withElevation;
        return this;
    }

    public boolean hasElevation()
    {
        return elevation;
    }

    public LevelGraphStorage levelGraphBuild()
    {
        return (LevelGraphStorage) setLevelGraph(true).build();
    }

    /**
     * Creates a LevelGraphStorage
     */
    public LevelGraphStorage levelGraphCreate()
    {
        return (LevelGraphStorage) setLevelGraph(true).create();
    }

    /**
     * Default graph is a GraphStorage with an in memory directory and disabled storing on flush.
     * Afterwards you'll need to call GraphStorage.create to have a useable object. Better use
     * create.
     */
    public GraphStorage build()
    {
        Directory dir;
        if (mmap)
            dir = new MMapDirectory(location);
        else
            dir = new RAMDirectory(location, store);

        GraphStorage graph;
        if (level)
            graph = new LevelGraphStorage(dir, encodingManager, elevation);
        else
        {
            if (encodingManager.needsTurnCostsSupport())
                graph = new GraphHopperStorage(dir, encodingManager, elevation, new TurnCostExtension());
            else
                graph = new GraphHopperStorage(dir, encodingManager, elevation);
        }

        return graph;
    }

    /**
     * Default graph is a GraphStorage with an in memory directory and disabled storing on flush.
     */
    public GraphStorage create()
    {
        return build().create(byteCapacity);
    }

    /**
     * @throws IllegalStateException if not loadable.
     */
    public GraphStorage load()
    {
        GraphStorage gs = build();
        if (!gs.loadExisting())
        {
            throw new IllegalStateException("Cannot load graph " + location);
        }
        return gs;
    }
}


File: core/src/main/java/com/graphhopper/storage/GraphExtension.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.storage;

/**
 * If you need custom storages, like turn cost tables, or osmid tables for your graph you implement
 * this interface and put it in any graph storage you want.
 */
public interface GraphExtension extends Storable<GraphExtension>
{
    /**
     * @return true, if and only if, if an additional field at the graphs node storage is required
     */
    boolean isRequireNodeField();

    /**
     * @return true, if and only if, if an additional field at the graphs edge storage is required
     */
    boolean isRequireEdgeField();

    /**
     * @return the default field value which will be set for default when creating nodes
     */
    int getDefaultNodeFieldValue();

    /**
     * @return the default field value which will be set for default when creating edges
     */
    int getDefaultEdgeFieldValue();

    /**
     * initializes the extended storage by giving the graph storage
     */
    void init( GraphStorage graph );

    /**
     * sets the segment size in all additional data storages
     */
    void setSegmentSize( int bytes );

    /**
     * creates a copy of this extended storage
     */
    GraphExtension copyTo( GraphExtension extStorage );

    /**
     * default implementation defines no additional fields or any logic. there's like nothing , like
     * the default behavior.
     */
    public class NoExtendedStorage implements GraphExtension
    {

        @Override
        public boolean isRequireNodeField()
        {
            return false;
        }

        @Override
        public boolean isRequireEdgeField()
        {
            return false;
        }

        @Override
        public int getDefaultNodeFieldValue()
        {
            return 0;
        }

        @Override
        public int getDefaultEdgeFieldValue()
        {
            return 0;
        }

        @Override
        public void init( GraphStorage grap )
        {
            // noop
        }

        @Override
        public GraphExtension create( long byteCount )
        {
            // noop
            return this;
        }

        @Override
        public boolean loadExisting()
        {
            // noop
            return true;
        }

        @Override
        public void setSegmentSize( int bytes )
        {
            // noop
        }

        @Override
        public void flush()
        {
            // noop
        }

        @Override
        public void close()
        {
            // noop
        }

        @Override
        public long getCapacity()
        {
            return 0;
        }

        @Override
        public GraphExtension copyTo( GraphExtension extStorage )
        {
            // noop
            return extStorage;
        }

        @Override
        public String toString()
        {
            return "NoExt";
        }

        @Override
        public boolean isClosed()
        {
            return false;
        }
    }
}


File: core/src/main/java/com/graphhopper/storage/GraphHopperStorage.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.storage;

import com.graphhopper.coll.GHBitSet;
import com.graphhopper.coll.GHBitSetImpl;
import com.graphhopper.coll.SparseIntIntArray;
import com.graphhopper.routing.util.AllEdgesIterator;
import com.graphhopper.routing.util.EdgeFilter;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.search.NameIndex;
import com.graphhopper.util.BitUtil;
import com.graphhopper.util.EdgeExplorer;
import com.graphhopper.util.EdgeIterator;
import com.graphhopper.util.EdgeIteratorState;
import com.graphhopper.util.GHUtility;
import com.graphhopper.util.Helper;
import com.graphhopper.util.PointList;
import com.graphhopper.util.shapes.BBox;

import static com.graphhopper.util.Helper.nf;

import java.io.UnsupportedEncodingException;

/**
 * The main implementation which handles nodes and edges file format. It can be used with different
 * Directory implementations like RAMDirectory for fast access or via MMapDirectory for
 * virtual-memory and not thread safe usage.
 * <p/>
 * Note: A RAM DataAccess Object is thread-safe in itself but if used in this Graph implementation
 * it is not write thread safe.
 * <p/>
 * Life cycle: (1) object creation, (2) configuration via setters & getters, (3) create or
 * loadExisting, (4) usage, (5) flush, (6) close
 * <p/>
 * @author Peter Karich
 * @see GraphBuilder Use the GraphBuilder class to create a (Level)GraphStorage easier.
 * @see LevelGraphStorage
 */
public class GraphHopperStorage implements GraphStorage
{
    private static final int NO_NODE = -1;
    // Emergency stop. to detect if something went wrong with our storage system and to prevent us from an infinit loop.
    // Road networks typically do not have nodes with plenty of edges!
    private static final int MAX_EDGES = 1000;
    // distance of around +-1000 000 meter are ok
    private static final double INT_DIST_FACTOR = 1000d;
    private final Directory dir;
    // edge memory layout:
    protected int E_NODEA, E_NODEB, E_LINKA, E_LINKB, E_DIST, E_FLAGS, E_GEO, E_NAME, E_ADDITIONAL;
    /**
     * Specifies how many entries (integers) are used per edge.
     */
    protected int edgeEntryBytes;
    protected final DataAccess edges;
    /**
     * interval [0,n)
     */
    protected int edgeCount;
    // node memory layout:
    protected int N_EDGE_REF, N_LAT, N_LON, N_ELE, N_ADDITIONAL;
    /**
     * Specifies how many entries (integers) are used per node
     */
    protected int nodeEntryBytes;
    protected final DataAccess nodes;
    /**
     * interval [0,n)
     */
    private int nodeCount;
    final BBox bounds;
    // remove markers are not yet persistent!
    private GHBitSet removedNodes;
    private int edgeEntryIndex, nodeEntryIndex;
    // length | nodeA | nextNode | ... | nodeB
    // as we use integer index in 'egdes' area => 'geometry' area is limited to 2GB (currently ~311M for world wide)
    private final DataAccess wayGeometry;
    private int maxGeoRef;
    private boolean initialized = false;
    private EncodingManager encodingManager;
    private final NameIndex nameIndex;
    private final StorableProperties properties;
    private final BitUtil bitUtil;
    private boolean flagsSizeIsLong;
    final GraphExtension extStorage;
    private final NodeAccess nodeAccess;

    public GraphHopperStorage( Directory dir, EncodingManager encodingManager, boolean withElevation )
    {
        this(dir, encodingManager, withElevation, new GraphExtension.NoExtendedStorage());
    }

    public GraphHopperStorage( Directory dir, EncodingManager encodingManager, boolean withElevation,
                               GraphExtension extendedStorage )
    {
        if (encodingManager == null)
            throw new IllegalArgumentException("EncodingManager cannot be null in GraphHopperStorage since 0.4. "
                    + "If you need to parse EncodingManager configuration from existing graph use EncodingManager.create");

        this.encodingManager = encodingManager;
        this.extStorage = extendedStorage;
        this.dir = dir;
        this.bitUtil = BitUtil.get(dir.getByteOrder());
        this.nodes = dir.find("nodes");
        this.edges = dir.find("edges");
        this.wayGeometry = dir.find("geometry");
        this.nameIndex = new NameIndex(dir);
        this.properties = new StorableProperties(dir);
        this.bounds = BBox.createInverse(withElevation);
        this.nodeAccess = new GHNodeAccess(this, withElevation);
        extendedStorage.init(this);
    }

    @Override
    public Graph getBaseGraph()
    {
        return this;
    }

    void checkInit()
    {
        if (initialized)
            throw new IllegalStateException("You cannot configure this GraphStorage "
                    + "after calling create or loadExisting. Calling one of the methods twice is also not allowed.");
    }

    protected final int nextEdgeEntryIndex( int sizeInBytes )
    {
        int tmp = edgeEntryIndex;
        edgeEntryIndex += sizeInBytes;
        return tmp;
    }

    protected final int nextNodeEntryIndex( int sizeInBytes )
    {
        int tmp = nodeEntryIndex;
        nodeEntryIndex += sizeInBytes;
        return tmp;
    }

    protected final void initNodeAndEdgeEntrySize()
    {
        nodeEntryBytes = nodeEntryIndex;
        edgeEntryBytes = edgeEntryIndex;
    }

    /**
     * @return the directory where this graph is stored.
     */
    @Override
    public Directory getDirectory()
    {
        return dir;
    }

    @Override
    public void setSegmentSize( int bytes )
    {
        checkInit();
        nodes.setSegmentSize(bytes);
        edges.setSegmentSize(bytes);
        wayGeometry.setSegmentSize(bytes);
        nameIndex.setSegmentSize(bytes);
        extStorage.setSegmentSize(bytes);
    }

    /**
     * After configuring this storage you need to create it explicitly.
     */
    @Override
    public GraphStorage create( long byteCount )
    {
        checkInit();
        if (encodingManager == null)
            throw new IllegalStateException("EncodingManager can only be null if you call loadExisting");

        long initSize = Math.max(byteCount, 100);
        nodes.create(initSize);
        edges.create(initSize);
        wayGeometry.create(initSize);
        nameIndex.create(1000);
        properties.create(100);
        extStorage.create(initSize);

        properties.put("graph.bytesForFlags", encodingManager.getBytesForFlags());
        properties.put("graph.flagEncoders", encodingManager.toDetailsString());

        properties.put("graph.byteOrder", dir.getByteOrder());
        properties.put("graph.dimension", nodeAccess.getDimension());
        properties.putCurrentVersions();
        initStorage();
        // 0 stands for no separate geoRef
        maxGeoRef = 4;

        initNodeRefs(0, nodes.getCapacity());
        return this;
    }

    @Override
    public int getNodes()
    {
        return nodeCount;
    }

    @Override
    public NodeAccess getNodeAccess()
    {
        return nodeAccess;
    }

    /**
     * Translates double distance to integer in order to save it in a DataAccess object
     */
    private int distToInt( double distance )
    {
        int integ = (int) (distance * INT_DIST_FACTOR);
        if (integ < 0)
            throw new IllegalArgumentException("Distance cannot be empty: "
                    + distance + ", maybe overflow issue? integer: " + integ);

        // Due to rounding errors e.g. when getting the distance from another DataAccess object
        // the following exception is not a good idea: 
        // Allow integ to be 0 only if distance is 0
        // if (integ == 0 && distance > 0)
        //    throw new IllegalStateException("Distance wasn't 0 but converted integer was: " + 
        //            distance + ", integer: " + integ);
        return integ;
    }

    /**
     * returns distance (already translated from integer to double)
     */
    private double getDist( long pointer )
    {
        int val = edges.getInt(pointer + E_DIST);
        if (val == Integer.MAX_VALUE)
            return Double.POSITIVE_INFINITY;

        return val / INT_DIST_FACTOR;
    }

    @Override
    public BBox getBounds()
    {
        return bounds;
    }

    /**
     * Check if byte capacity of DataAcess nodes object is sufficient to include node index, else
     * extend byte capacity
     */
    final void ensureNodeIndex( int nodeIndex )
    {
        if (!initialized)
            throw new AssertionError("The graph has not yet been initialized.");

        if (nodeIndex < nodeCount)
            return;

        long oldNodes = nodeCount;
        nodeCount = nodeIndex + 1;
        boolean capacityIncreased = nodes.ensureCapacity((long) nodeCount * nodeEntryBytes);
        if (capacityIncreased)
        {
            long newBytesCapacity = nodes.getCapacity();
            initNodeRefs(oldNodes * nodeEntryBytes, newBytesCapacity);
            if (removedNodes != null)
                getRemovedNodes().ensureCapacity((int) (newBytesCapacity / nodeEntryBytes));
        }

    }

    /**
     * Initializes the node area with the empty edge value and default additional value.
     */
    private void initNodeRefs( long oldCapacity, long newCapacity )
    {
        for (long pointer = oldCapacity + N_EDGE_REF; pointer < newCapacity; pointer += nodeEntryBytes)
        {
            nodes.setInt(pointer, EdgeIterator.NO_EDGE);
        }
        if (extStorage.isRequireNodeField())
        {
            for (long pointer = oldCapacity + N_ADDITIONAL; pointer < newCapacity; pointer += nodeEntryBytes)
            {
                nodes.setInt(pointer, extStorage.getDefaultNodeFieldValue());
            }
        }
    }

    private void ensureEdgeIndex( int edgeIndex )
    {
        edges.ensureCapacity(((long) edgeIndex + 1) * edgeEntryBytes);
    }

    private void ensureGeometry( long bytePos, int byteLength )
    {
        wayGeometry.ensureCapacity(bytePos + byteLength);
    }

    @Override
    public EdgeIteratorState edge( int a, int b, double distance, boolean bothDirection )
    {
        return edge(a, b).setDistance(distance).setFlags(encodingManager.flagsDefault(true, bothDirection));
    }

    /**
     * Create edge between nodes a and b
     * <p/>
     * @return EdgeIteratorState of newly created edge
     */
    @Override
    public EdgeIteratorState edge( int a, int b )
    {
        ensureNodeIndex(Math.max(a, b));
        int edge = internalEdgeAdd(a, b);
        EdgeIterable iter = new EdgeIterable(EdgeFilter.ALL_EDGES);
        iter.setBaseNode(a);
        iter.setEdgeId(edge);
        if (extStorage.isRequireEdgeField())
        {
            iter.setAdditionalField(extStorage.getDefaultEdgeFieldValue());
        }
        iter.next();
        return iter;
    }

    private int nextGeoRef( int arrayLength )
    {
        int tmp = maxGeoRef;
        // one more integer to store also the size itself
        maxGeoRef += arrayLength + 1;
        return tmp;
    }

    /**
     * Write new edge between nodes fromNodeId, and toNodeId both to nodes index and edges index
     */
    int internalEdgeAdd( int fromNodeId, int toNodeId )
    {
        int newEdgeId = nextEdge();
        writeEdge(newEdgeId, fromNodeId, toNodeId, EdgeIterator.NO_EDGE, EdgeIterator.NO_EDGE);
        connectNewEdge(fromNodeId, newEdgeId);
        if (fromNodeId != toNodeId)
            connectNewEdge(toNodeId, newEdgeId);

        return newEdgeId;
    }

    // for test only
    void setEdgeCount( int cnt )
    {
        edgeCount = cnt;
    }

    /**
     * Determine next free edgeId and ensure byte capacity to store edge
     * <p/>
     * @return next free edgeId
     */
    private int nextEdge()
    {
        int nextEdge = edgeCount;
        edgeCount++;
        if (edgeCount < 0)
            throw new IllegalStateException("too many edges. new edge id would be negative. " + toString());

        ensureEdgeIndex(edgeCount);
        return nextEdge;
    }

    private void connectNewEdge( int fromNode, int newOrExistingEdge )
    {
        long nodePointer = (long) fromNode * nodeEntryBytes;
        int edge = nodes.getInt(nodePointer + N_EDGE_REF);
        if (edge > EdgeIterator.NO_EDGE)
        {
            long edgePointer = (long) newOrExistingEdge * edgeEntryBytes;
            int otherNode = getOtherNode(fromNode, edgePointer);
            long lastLink = getLinkPosInEdgeArea(fromNode, otherNode, edgePointer);
            edges.setInt(lastLink, edge);
        }

        nodes.setInt(nodePointer + N_EDGE_REF, newOrExistingEdge);
    }

    private long writeEdge( int edge, int nodeThis, int nodeOther, int nextEdge, int nextEdgeOther )
    {
        if (nodeThis > nodeOther)
        {
            int tmp = nodeThis;
            nodeThis = nodeOther;
            nodeOther = tmp;

            tmp = nextEdge;
            nextEdge = nextEdgeOther;
            nextEdgeOther = tmp;
        }

        if (edge < 0 || edge == EdgeIterator.NO_EDGE)
            throw new IllegalStateException("Cannot write edge with illegal ID:" + edge
                    + "; nodeThis:" + nodeThis + ", nodeOther:" + nodeOther);

        long edgePointer = (long) edge * edgeEntryBytes;
        edges.setInt(edgePointer + E_NODEA, nodeThis);
        edges.setInt(edgePointer + E_NODEB, nodeOther);
        edges.setInt(edgePointer + E_LINKA, nextEdge);
        edges.setInt(edgePointer + E_LINKB, nextEdgeOther);
        return edgePointer;
    }

    protected final long getLinkPosInEdgeArea( int nodeThis, int nodeOther, long edgePointer )
    {
        return nodeThis <= nodeOther ? edgePointer + E_LINKA : edgePointer + E_LINKB;
    }

    public String getDebugInfo( int node, int area )
    {
        String str = "--- node " + node + " ---";
        int min = Math.max(0, node - area / 2);
        int max = Math.min(nodeCount, node + area / 2);
        long nodePointer = (long) node * nodeEntryBytes;
        for (int i = min; i < max; i++)
        {
            str += "\n" + i + ": ";
            for (int j = 0; j < nodeEntryBytes; j += 4)
            {
                if (j > 0)
                {
                    str += ",\t";
                }
                str += nodes.getInt(nodePointer + j);
            }
        }
        int edge = nodes.getInt(nodePointer);
        str += "\n--- edges " + edge + " ---";
        int otherNode;
        for (int i = 0; i < 1000; i++)
        {
            str += "\n";
            if (edge == EdgeIterator.NO_EDGE)
                break;

            str += edge + ": ";
            long edgePointer = (long) edge * edgeEntryBytes;
            for (int j = 0; j < edgeEntryBytes; j += 4)
            {
                if (j > 0)
                {
                    str += ",\t";
                }
                str += edges.getInt(edgePointer + j);
            }

            otherNode = getOtherNode(node, edgePointer);
            long lastLink = getLinkPosInEdgeArea(node, otherNode, edgePointer);
            edge = edges.getInt(lastLink);
        }
        return str;
    }

    private int getOtherNode( int nodeThis, long edgePointer )
    {
        int nodeA = edges.getInt(edgePointer + E_NODEA);
        if (nodeA == nodeThis)
        // return b
        {
            return edges.getInt(edgePointer + E_NODEB);
        }
        // return a
        return nodeA;
    }

    @Override
    public AllEdgesIterator getAllEdges()
    {
        return new AllEdgeIterator();
    }

    @Override
    public EncodingManager getEncodingManager()
    {
        return encodingManager;
    }

    @Override
    public StorableProperties getProperties()
    {
        return properties;
    }

    /**
     * Include all edges of this storage in the iterator.
     */
    protected class AllEdgeIterator implements AllEdgesIterator
    {
        protected long edgePointer = -edgeEntryBytes;
        private final long maxEdges = (long) edgeCount * edgeEntryBytes;
        private int nodeA;
        private int nodeB;
        private boolean reverse = false;

        public AllEdgeIterator()
        {
        }

        @Override
        public int getCount()
        {
            return edgeCount;
        }

        @Override
        public boolean next()
        {
            do
            {
                edgePointer += edgeEntryBytes;
                nodeA = edges.getInt(edgePointer + E_NODEA);
                nodeB = edges.getInt(edgePointer + E_NODEB);
                reverse = getBaseNode() > getAdjNode();
                // some edges are deleted and have a negative node
            } while (nodeA == NO_NODE && edgePointer < maxEdges);
            return edgePointer < maxEdges;
        }

        @Override
        public int getBaseNode()
        {
            return nodeA;
        }

        @Override
        public int getAdjNode()
        {
            return nodeB;
        }

        @Override
        public double getDistance()
        {
            return getDist(edgePointer);
        }

        @Override
        public EdgeIteratorState setDistance( double dist )
        {
            edges.setInt(edgePointer + E_DIST, distToInt(dist));
            return this;
        }

        @Override
        public long getFlags()
        {
            return GraphHopperStorage.this.getFlags(edgePointer, reverse);
        }

        @Override
        public int getAdditionalField()
        {
            return edges.getInt(edgePointer + E_ADDITIONAL);
        }

        @Override
        public EdgeIteratorState setAdditionalField( int value )
        {
            GraphHopperStorage.this.setAdditionalEdgeField(edgePointer, value);
            return this;
        }

        @Override
        public EdgeIteratorState setFlags( long flags )
        {
            GraphHopperStorage.this.setFlags(edgePointer, reverse, flags);
            return this;
        }

        @Override
        public EdgeIteratorState copyPropertiesTo( EdgeIteratorState edge )
        {
            return GraphHopperStorage.this.copyProperties(this, edge);
        }

        @Override
        public int getEdge()
        {
            return (int) (edgePointer / edgeEntryBytes);
        }

        @Override
        public EdgeIteratorState setWayGeometry( PointList pillarNodes )
        {
            GraphHopperStorage.this.setWayGeometry(pillarNodes, edgePointer, reverse);
            return this;
        }

        @Override
        public PointList fetchWayGeometry( int type )
        {
            return GraphHopperStorage.this.fetchWayGeometry(edgePointer, reverse,
                    type, getBaseNode(), getAdjNode());
        }

        @Override
        public String getName()
        {
            int nameIndexRef = edges.getInt(edgePointer + E_NAME);
            return nameIndex.get(nameIndexRef);
        }

        @Override
        public EdgeIteratorState setName( String name )
        {
            long nameIndexRef = nameIndex.put(name);
            if (nameIndexRef < 0)
                throw new IllegalStateException("Too many names are stored, currently limited to int pointer");

            edges.setInt(edgePointer + E_NAME, (int) nameIndexRef);
            return this;
        }

        @Override
        public EdgeIteratorState detach( boolean reverseArg )
        {
            if (edgePointer < 0)
                throw new IllegalStateException("call next before detaching");
            AllEdgeIterator iter = new AllEdgeIterator();
            iter.nodeA = nodeA;
            iter.nodeB = nodeB;
            iter.edgePointer = edgePointer;
            if (reverseArg)
            {
                iter.reverse = !this.reverse;
                iter.nodeA = nodeB;
                iter.nodeB = nodeA;
            }
            return iter;
        }

        @Override
        public String toString()
        {
            return getEdge() + " " + getBaseNode() + "-" + getAdjNode();
        }
    }

    @Override
    public EdgeIteratorState getEdgeProps( int edgeId, int adjNode )
    {
        if (edgeId <= EdgeIterator.NO_EDGE || edgeId >= edgeCount)
            throw new IllegalStateException("edgeId " + edgeId + " out of bounds [0," + nf(edgeCount) + "]");

        if (adjNode < 0 && adjNode != Integer.MIN_VALUE)
            throw new IllegalStateException("adjNode " + adjNode + " out of bounds [0," + nf(nodeCount) + "]");

        long edgePointer = (long) edgeId * edgeEntryBytes;
        int nodeA = edges.getInt(edgePointer + E_NODEA);
        if (nodeA == NO_NODE)
            throw new IllegalStateException("edgeId " + edgeId + " is invalid - already removed!");

        int nodeB = edges.getInt(edgePointer + E_NODEB);
        SingleEdge edge;
        if (adjNode == nodeB || adjNode == Integer.MIN_VALUE)
        {
            edge = createSingleEdge(edgeId, nodeA);
            edge.reverse = false;
            edge.adjNode = nodeB;
            return edge;
        } else if (adjNode == nodeA)
        {
            edge = createSingleEdge(edgeId, nodeB);
            edge.adjNode = nodeA;
            edge.reverse = true;
            return edge;
        }
        // if edgeId exists but adjacent nodes do not match
        return null;
    }

    protected SingleEdge createSingleEdge( int edgeId, int nodeId )
    {
        return new SingleEdge(edgeId, nodeId);
    }

    private long getFlags( long edgePointer, boolean reverse )
    {
        int low = edges.getInt(edgePointer + E_FLAGS);
        long res = low;
        if (flagsSizeIsLong)
        {
            int high = edges.getInt(edgePointer + E_FLAGS + 4);
            res = bitUtil.combineIntsToLong(low, high);
        }
        if (reverse)
            return reverseFlags(edgePointer, res);
        return res;
    }

    long reverseFlags( long edgePointer, long flags )
    {
        return encodingManager.reverseFlags(flags);
    }

    private void setFlags( long edgePointer, boolean reverse, long flags )
    {
        if (reverse)
            flags = reverseFlags(edgePointer, flags);

        edges.setInt(edgePointer + E_FLAGS, bitUtil.getIntLow(flags));

        if (flagsSizeIsLong)
            edges.setInt(edgePointer + E_FLAGS + 4, bitUtil.getIntHigh(flags));
    }

    protected class SingleEdge extends EdgeIterable
    {
        public SingleEdge( int edgeId, int nodeId )
        {
            super(EdgeFilter.ALL_EDGES);
            setBaseNode(nodeId);
            setEdgeId(edgeId);
            nextEdge = EdgeIterable.NO_EDGE;
        }
    }

    @Override
    public EdgeExplorer createEdgeExplorer( EdgeFilter filter )
    {
        return new EdgeIterable(filter);
    }

    @Override
    public EdgeExplorer createEdgeExplorer()
    {
        return createEdgeExplorer(EdgeFilter.ALL_EDGES);
    }

    protected class EdgeIterable implements EdgeExplorer, EdgeIterator
    {
        final EdgeFilter filter;
        int baseNode;
        int adjNode;
        int edgeId;
        long edgePointer;
        int nextEdge;
        boolean reverse;

        public EdgeIterable( EdgeFilter filter )
        {
            if (filter == null)
                throw new IllegalArgumentException("Instead null filter use EdgeFilter.ALL_EDGES");

            this.filter = filter;
        }

        protected void setEdgeId( int edgeId )
        {
            this.nextEdge = this.edgeId = edgeId;
            this.edgePointer = (long) nextEdge * edgeEntryBytes;
        }

        @Override
        public EdgeIterator setBaseNode( int baseNode )
        {
            int edge = nodes.getInt((long) baseNode * nodeEntryBytes + N_EDGE_REF);
            setEdgeId(edge);
            this.baseNode = baseNode;
            return this;
        }

        @Override
        public final int getBaseNode()
        {
            return baseNode;
        }

        @Override
        public final int getAdjNode()
        {
            return adjNode;
        }

        @Override
        public final boolean next()
        {
            int i = 0;
            boolean foundNext = false;
            for (; i < MAX_EDGES; i++)
            {
                if (nextEdge == EdgeIterator.NO_EDGE)
                    break;

                edgePointer = (long) nextEdge * edgeEntryBytes;
                edgeId = nextEdge;
                adjNode = getOtherNode(baseNode, edgePointer);
                reverse = baseNode > adjNode;

                // position to next edge                
                nextEdge = edges.getInt(getLinkPosInEdgeArea(baseNode, adjNode, edgePointer));
                if (nextEdge == edgeId)
                    throw new AssertionError("endless loop detected for " + baseNode + ", " + adjNode
                            + ", " + edgePointer + ", " + edgeId);

                foundNext = filter.accept(this);
                if (foundNext)
                    break;
            }

            if (i > MAX_EDGES)
                throw new IllegalStateException("something went wrong: no end of edge-list found");

            return foundNext;
        }

        private long getEdgePointer()
        {
            return edgePointer;
        }

        @Override
        public final double getDistance()
        {
            return getDist(edgePointer);
        }

        @Override
        public final EdgeIteratorState setDistance( double dist )
        {
            edges.setInt(edgePointer + E_DIST, distToInt(dist));
            return this;
        }

        @Override
        public long getFlags()
        {
            return GraphHopperStorage.this.getFlags(edgePointer, reverse);
        }

        @Override
        public final EdgeIteratorState setFlags( long fl )
        {
            GraphHopperStorage.this.setFlags(edgePointer, reverse, fl);
            return this;
        }

        @Override
        public int getAdditionalField()
        {
            return edges.getInt(edgePointer + E_ADDITIONAL);
        }

        @Override
        public EdgeIteratorState setAdditionalField( int value )
        {
            GraphHopperStorage.this.setAdditionalEdgeField(edgePointer, value);
            return null;
        }

        @Override
        public EdgeIteratorState setWayGeometry( PointList pillarNodes )
        {
            GraphHopperStorage.this.setWayGeometry(pillarNodes, edgePointer, reverse);
            return this;
        }

        @Override
        public PointList fetchWayGeometry( int mode )
        {
            return GraphHopperStorage.this.fetchWayGeometry(edgePointer, reverse, mode, getBaseNode(), getAdjNode());
        }

        @Override
        public final int getEdge()
        {
            return edgeId;
        }

        @Override
        public String getName()
        {
            int nameIndexRef = edges.getInt(edgePointer + E_NAME);
            return nameIndex.get(nameIndexRef);
        }

        @Override
        public EdgeIteratorState setName( String name )
        {
            long nameIndexRef = nameIndex.put(name);
            if (nameIndexRef < 0)
                throw new IllegalStateException("Too many names are stored, currently limited to int pointer");

            edges.setInt(edgePointer + E_NAME, (int) nameIndexRef);
            return this;
        }

        @Override
        public EdgeIteratorState detach( boolean reverseArg )
        {
            if (edgeId == nextEdge)
                throw new IllegalStateException("call next before detaching");

            EdgeIterable iter = new EdgeIterable(filter);
            iter.setBaseNode(baseNode);
            iter.setEdgeId(edgeId);
            iter.next();
            if (reverseArg)
            {
                iter.reverse = !this.reverse;
                iter.adjNode = baseNode;
                iter.baseNode = adjNode;
            }
            return iter;
        }

        @Override
        public final String toString()
        {
            return getEdge() + " " + getBaseNode() + "-" + getAdjNode();
        }

        @Override
        public EdgeIteratorState copyPropertiesTo( EdgeIteratorState edge )
        {
            return GraphHopperStorage.this.copyProperties(this, edge);
        }
    }

    /**
     * @return to
     */
    EdgeIteratorState copyProperties( EdgeIteratorState from, EdgeIteratorState to )
    {
        to.setDistance(from.getDistance()).
                setName(from.getName()).
                setFlags(from.getFlags()).
                setWayGeometry(from.fetchWayGeometry(0));

        if (E_ADDITIONAL >= 0)
            to.setAdditionalField(from.getAdditionalField());
        return to;
    }

    public void setAdditionalEdgeField( long edgePointer, int value )
    {
        if (extStorage.isRequireEdgeField() && E_ADDITIONAL >= 0)
            edges.setInt(edgePointer + E_ADDITIONAL, value);
        else
            throw new AssertionError("This graph does not support an additional edge field.");
    }

    private void setWayGeometry( PointList pillarNodes, long edgePointer, boolean reverse )
    {
        if (pillarNodes != null && !pillarNodes.isEmpty())
        {
            if (pillarNodes.getDimension() != nodeAccess.getDimension())
                throw new IllegalArgumentException("Cannot use pointlist which is " + pillarNodes.getDimension()
                        + "D for graph which is " + nodeAccess.getDimension() + "D");

            int len = pillarNodes.getSize();
            int dim = nodeAccess.getDimension();
            int tmpRef = nextGeoRef(len * dim);
            edges.setInt(edgePointer + E_GEO, tmpRef);
            long geoRef = (long) tmpRef * 4;
            byte[] bytes = new byte[len * dim * 4 + 4];
            ensureGeometry(geoRef, bytes.length);
            bitUtil.fromInt(bytes, len, 0);
            if (reverse)
                pillarNodes.reverse();

            int tmpOffset = 4;
            boolean is3D = nodeAccess.is3D();
            for (int i = 0; i < len; i++)
            {
                double lat = pillarNodes.getLatitude(i);
                bitUtil.fromInt(bytes, Helper.degreeToInt(lat), tmpOffset);
                tmpOffset += 4;
                bitUtil.fromInt(bytes, Helper.degreeToInt(pillarNodes.getLongitude(i)), tmpOffset);
                tmpOffset += 4;

                if (is3D)
                {
                    bitUtil.fromInt(bytes, Helper.eleToInt(pillarNodes.getElevation(i)), tmpOffset);
                    tmpOffset += 4;
                }
            }

            wayGeometry.setBytes(geoRef, bytes, bytes.length);
        } else
        {
            edges.setInt(edgePointer + E_GEO, 0);
        }
    }

    private PointList fetchWayGeometry( long edgePointer, boolean reverse, int mode, int baseNode, int adjNode )
    {
        long geoRef = edges.getInt(edgePointer + E_GEO);
        int count = 0;
        byte[] bytes = null;
        if (geoRef > 0)
        {
            geoRef *= 4;
            count = wayGeometry.getInt(geoRef);

            geoRef += 4;
            bytes = new byte[count * nodeAccess.getDimension() * 4];
            wayGeometry.getBytes(geoRef, bytes, bytes.length);
        } else if (mode == 0)
            return PointList.EMPTY;

        PointList pillarNodes = new PointList(count + mode, nodeAccess.is3D());
        if (reverse)
        {
            if ((mode & 2) != 0)
                pillarNodes.add(nodeAccess, adjNode);
        } else
        {
            if ((mode & 1) != 0)
                pillarNodes.add(nodeAccess, baseNode);
        }

        int index = 0;
        for (int i = 0; i < count; i++)
        {
            double lat = Helper.intToDegree(bitUtil.toInt(bytes, index));
            index += 4;
            double lon = Helper.intToDegree(bitUtil.toInt(bytes, index));
            index += 4;
            if (nodeAccess.is3D())
            {
                pillarNodes.add(lat, lon, Helper.intToEle(bitUtil.toInt(bytes, index)));
                index += 4;
            } else
            {
                pillarNodes.add(lat, lon);
            }
        }

        if (reverse)
        {
            if ((mode & 1) != 0)
                pillarNodes.add(nodeAccess, baseNode);
            pillarNodes.reverse();
        } else
        {
            if ((mode & 2) != 0)
                pillarNodes.add(nodeAccess, adjNode);
        }

        return pillarNodes;
    }

    @Override
    public Graph copyTo( Graph g )
    {
        if (g.getClass().equals(getClass()))
        {
            return _copyTo((GraphHopperStorage) g);
        } else
        {
            return GHUtility.copyTo(this, g);
        }
    }

    Graph _copyTo( GraphHopperStorage clonedG )
    {
        if (clonedG.edgeEntryBytes != edgeEntryBytes)
            throw new IllegalStateException("edgeEntryBytes cannot be different for cloned graph. "
                    + "Cloned: " + clonedG.edgeEntryBytes + " vs " + edgeEntryBytes);

        if (clonedG.nodeEntryBytes != nodeEntryBytes)
            throw new IllegalStateException("nodeEntryBytes cannot be different for cloned graph. "
                    + "Cloned: " + clonedG.nodeEntryBytes + " vs " + nodeEntryBytes);

        if (clonedG.nodeAccess.getDimension() != nodeAccess.getDimension())
            throw new IllegalStateException("dimension cannot be different for cloned graph. "
                    + "Cloned: " + clonedG.nodeAccess.getDimension() + " vs " + nodeAccess.getDimension());

        // nodes
        setNodesHeader();
        nodes.copyTo(clonedG.nodes);
        clonedG.loadNodesHeader();

        // edges
        setEdgesHeader();
        edges.copyTo(clonedG.edges);
        clonedG.loadEdgesHeader();

        // name
        nameIndex.copyTo(clonedG.nameIndex);

        // geometry
        setWayGeometryHeader();
        wayGeometry.copyTo(clonedG.wayGeometry);
        clonedG.loadWayGeometryHeader();

        // extStorage
        extStorage.copyTo(clonedG.extStorage);

        properties.copyTo(clonedG.properties);

        if (removedNodes == null)
            clonedG.removedNodes = null;
        else
            clonedG.removedNodes = removedNodes.copyTo(new GHBitSetImpl());

        clonedG.encodingManager = encodingManager;
        initialized = true;
        return clonedG;
    }

    private GHBitSet getRemovedNodes()
    {
        if (removedNodes == null)
            removedNodes = new GHBitSetImpl((int) (nodes.getCapacity() / 4));

        return removedNodes;
    }

    @Override
    public void markNodeRemoved( int index )
    {
        getRemovedNodes().add(index);
    }

    @Override
    public boolean isNodeRemoved( int index )
    {
        return getRemovedNodes().contains(index);
    }

    @Override
    public void optimize()
    {
        int delNodes = getRemovedNodes().getCardinality();
        if (delNodes <= 0)
            return;

        // Deletes only nodes.
        // It reduces the fragmentation of the node space but introduces new unused edges.
        inPlaceNodeRemove(delNodes);

        // Reduce memory usage
        trimToSize();
    }

    private void trimToSize()
    {
        long nodeCap = (long) nodeCount * nodeEntryBytes;
        nodes.trimTo(nodeCap);
//        long edgeCap = (long) (edgeCount + 1) * edgeEntrySize;
//        edges.trimTo(edgeCap * 4);
    }

    /**
     * This method disconnects the specified edge from the list of edges of the specified node. It
     * does not release the freed space to be reused.
     * <p/>
     * @param edgeToUpdatePointer if it is negative then the nextEdgeId will be saved to refToEdges
     * of nodes
     */
    long internalEdgeDisconnect( int edgeToRemove, long edgeToUpdatePointer, int baseNode, int adjNode )
    {
        long edgeToRemovePointer = (long) edgeToRemove * edgeEntryBytes;
        // an edge is shared across the two nodes even if the edge is not in both directions
        // so we need to know two edge-pointers pointing to the edge before edgeToRemovePointer
        int nextEdgeId = edges.getInt(getLinkPosInEdgeArea(baseNode, adjNode, edgeToRemovePointer));
        if (edgeToUpdatePointer < 0)
        {
            nodes.setInt((long) baseNode * nodeEntryBytes, nextEdgeId);
        } else
        {
            // adjNode is different for the edge we want to update with the new link
            long link = edges.getInt(edgeToUpdatePointer + E_NODEA) == baseNode
                    ? edgeToUpdatePointer + E_LINKA : edgeToUpdatePointer + E_LINKB;
            edges.setInt(link, nextEdgeId);
        }
        return edgeToRemovePointer;
    }

    private void invalidateEdge( long edgePointer )
    {
        edges.setInt(edgePointer + E_NODEA, NO_NODE);
    }

    /**
     * This methods disconnects all edges from removed nodes. It does no edge compaction. Then it
     * moves the last nodes into the deleted nodes, where it needs to update the node ids in every
     * edge.
     */
    private void inPlaceNodeRemove( int removeNodeCount )
    {
        // Prepare edge-update of nodes which are connected to deleted nodes        
        int toMoveNodes = getNodes();
        int itemsToMove = 0;

        // sorted map when we access it via keyAt and valueAt - see below!
        final SparseIntIntArray oldToNewMap = new SparseIntIntArray(removeNodeCount);
        GHBitSet toRemoveSet = new GHBitSetImpl(removeNodeCount);
        removedNodes.copyTo(toRemoveSet);

        EdgeExplorer delExplorer = createEdgeExplorer(EdgeFilter.ALL_EDGES);
        // create map of old node ids pointing to new ids        
        for (int removeNode = removedNodes.next(0);
                removeNode >= 0;
                removeNode = removedNodes.next(removeNode + 1))
        {
            EdgeIterator delEdgesIter = delExplorer.setBaseNode(removeNode);
            while (delEdgesIter.next())
            {
                toRemoveSet.add(delEdgesIter.getAdjNode());
            }

            toMoveNodes--;
            for (; toMoveNodes >= 0; toMoveNodes--)
            {
                if (!removedNodes.contains(toMoveNodes))
                    break;
            }

            if (toMoveNodes >= removeNode)
                oldToNewMap.put(toMoveNodes, removeNode);

            itemsToMove++;
        }

        EdgeIterable adjNodesToDelIter = (EdgeIterable) createEdgeExplorer();
        // now similar process to disconnectEdges but only for specific nodes
        // all deleted nodes could be connected to existing. remove the connections
        for (int removeNode = toRemoveSet.next(0);
                removeNode >= 0;
                removeNode = toRemoveSet.next(removeNode + 1))
        {
            // remove all edges connected to the deleted nodes
            adjNodesToDelIter.setBaseNode(removeNode);
            long prev = EdgeIterator.NO_EDGE;
            while (adjNodesToDelIter.next())
            {
                int nodeId = adjNodesToDelIter.getAdjNode();
                // already invalidated
                if (nodeId != NO_NODE && removedNodes.contains(nodeId))
                {
                    int edgeToRemove = adjNodesToDelIter.getEdge();
                    long edgeToRemovePointer = (long) edgeToRemove * edgeEntryBytes;
                    internalEdgeDisconnect(edgeToRemove, prev, removeNode, nodeId);
                    invalidateEdge(edgeToRemovePointer);
                } else
                {
                    prev = adjNodesToDelIter.getEdgePointer();
                }
            }
        }

        GHBitSet toMoveSet = new GHBitSetImpl(removeNodeCount * 3);
        EdgeExplorer movedEdgeExplorer = createEdgeExplorer();
        // marks connected nodes to rewrite the edges
        for (int i = 0; i < itemsToMove; i++)
        {
            int oldI = oldToNewMap.keyAt(i);
            EdgeIterator movedEdgeIter = movedEdgeExplorer.setBaseNode(oldI);
            while (movedEdgeIter.next())
            {
                int nodeId = movedEdgeIter.getAdjNode();
                if (nodeId == NO_NODE)
                    continue;

                if (removedNodes.contains(nodeId))
                    throw new IllegalStateException("shouldn't happen the edge to the node "
                            + nodeId + " should be already deleted. " + oldI);

                toMoveSet.add(nodeId);
            }
        }

        // move nodes into deleted nodes
        for (int i = 0; i < itemsToMove; i++)
        {
            int oldI = oldToNewMap.keyAt(i);
            int newI = oldToNewMap.valueAt(i);
            long newOffset = (long) newI * nodeEntryBytes;
            long oldOffset = (long) oldI * nodeEntryBytes;
            for (long j = 0; j < nodeEntryBytes; j += 4)
            {
                nodes.setInt(newOffset + j, nodes.getInt(oldOffset + j));
            }
        }

        // *rewrites* all edges connected to moved nodes
        // go through all edges and pick the necessary <- this is easier to implement than
        // a more efficient (?) breadth-first search
        EdgeIterator iter = getAllEdges();
        while (iter.next())
        {
            int nodeA = iter.getBaseNode();
            int nodeB = iter.getAdjNode();
            if (!toMoveSet.contains(nodeA) && !toMoveSet.contains(nodeB))
                continue;

            // now overwrite exiting edge with new node ids 
            // also flags and links could have changed due to different node order
            int updatedA = oldToNewMap.get(nodeA);
            if (updatedA < 0)
                updatedA = nodeA;

            int updatedB = oldToNewMap.get(nodeB);
            if (updatedB < 0)
                updatedB = nodeB;

            int edge = iter.getEdge();
            long edgePointer = (long) edge * edgeEntryBytes;
            int linkA = edges.getInt(getLinkPosInEdgeArea(nodeA, nodeB, edgePointer));
            int linkB = edges.getInt(getLinkPosInEdgeArea(nodeB, nodeA, edgePointer));
            long flags = getFlags(edgePointer, false);
            writeEdge(edge, updatedA, updatedB, linkA, linkB);
            setFlags(edgePointer, updatedA > updatedB, flags);
            if (updatedA < updatedB != nodeA < nodeB)
                setWayGeometry(fetchWayGeometry(edgePointer, true, 0, -1, -1), edgePointer, false);
        }

        if (removeNodeCount >= nodeCount)
            throw new IllegalStateException("graph is empty after in-place removal but was " + removeNodeCount);

        // we do not remove the invalid edges => edgeCount stays the same!
        nodeCount -= removeNodeCount;

        EdgeExplorer explorer = createEdgeExplorer();
        // health check
        if (isTestingEnabled())
        {
            iter = getAllEdges();
            while (iter.next())
            {
                int base = iter.getBaseNode();
                int adj = iter.getAdjNode();
                String str = iter.getEdge()
                        + ", r.contains(" + base + "):" + removedNodes.contains(base)
                        + ", r.contains(" + adj + "):" + removedNodes.contains(adj)
                        + ", tr.contains(" + base + "):" + toRemoveSet.contains(base)
                        + ", tr.contains(" + adj + "):" + toRemoveSet.contains(adj)
                        + ", base:" + base + ", adj:" + adj + ", nodeCount:" + nodeCount;
                if (adj >= nodeCount)
                    throw new RuntimeException("Adj.node problem with edge " + str);

                if (base >= nodeCount)
                    throw new RuntimeException("Base node problem with edge " + str);

                try
                {
                    explorer.setBaseNode(adj).toString();
                } catch (Exception ex)
                {
                    org.slf4j.LoggerFactory.getLogger(getClass()).error("adj:" + adj);
                }
                try
                {
                    explorer.setBaseNode(base).toString();
                } catch (Exception ex)
                {
                    org.slf4j.LoggerFactory.getLogger(getClass()).error("base:" + base);
                }
            }
            // access last node -> no error
            explorer.setBaseNode(nodeCount - 1).toString();
        }
        removedNodes = null;
    }

    private static boolean isTestingEnabled()
    {
        boolean enableIfAssert = false;
        assert (enableIfAssert = true) : true;
        return enableIfAssert;
    }

    @Override
    public boolean loadExisting()
    {
        checkInit();
        if (nodes.loadExisting())
        {
            String acceptStr = "";
            if (properties.loadExisting())
            {
                properties.checkVersions(false);
                // check encoding for compatiblity
                acceptStr = properties.get("graph.flagEncoders");

            } else
                throw new IllegalStateException("cannot load properties. corrupt file or directory? " + dir);

            if (encodingManager == null)
            {
                if (acceptStr.isEmpty())
                    throw new IllegalStateException("No EncodingManager was configured. And no one was found in the graph: "
                            + dir.getLocation());

                int bytesForFlags = 4;
                if ("8".equals(properties.get("graph.bytesForFlags")))
                    bytesForFlags = 8;
                encodingManager = new EncodingManager(acceptStr, bytesForFlags);
            } else if (!acceptStr.isEmpty() && !encodingManager.toDetailsString().equalsIgnoreCase(acceptStr))
            {
                throw new IllegalStateException("Encoding does not match:\nGraphhopper config: " + encodingManager.toDetailsString()
                        + "\nGraph: " + acceptStr + ", dir:" + dir.getLocation());
            }

            String dim = properties.get("graph.dimension");
            if (!dim.equalsIgnoreCase("" + nodeAccess.getDimension()))
                throw new IllegalStateException("Configured dimension (" + dim + ") is not equal to dimension of loaded graph (" + nodeAccess.getDimension() + ")");

            String byteOrder = properties.get("graph.byteOrder");
            if (!byteOrder.equalsIgnoreCase("" + dir.getByteOrder()))
                throw new IllegalStateException("Configured byteOrder (" + dim + ") is not equal to byteOrder of loaded graph (" + dir.getByteOrder() + ")");

            if (!edges.loadExisting())
                throw new IllegalStateException("Cannot load nodes. corrupt file or directory? " + dir);

            if (!wayGeometry.loadExisting())
                throw new IllegalStateException("Cannot load geometry. corrupt file or directory? " + dir);

            if (!nameIndex.loadExisting())
                throw new IllegalStateException("Cannot load name index. corrupt file or directory? " + dir);

            if (!extStorage.loadExisting())
                throw new IllegalStateException("Cannot load extended storage. corrupt file or directory? " + dir);

            // first define header indices of this storage
            initStorage();

            // now load some properties from stored data
            loadNodesHeader();
            loadEdgesHeader();
            loadWayGeometryHeader();
            return true;
        }
        return false;
    }

    protected void initStorage()
    {
        edgeEntryIndex = 0;
        nodeEntryIndex = 0;
        E_NODEA = nextEdgeEntryIndex(4);
        E_NODEB = nextEdgeEntryIndex(4);
        E_LINKA = nextEdgeEntryIndex(4);
        E_LINKB = nextEdgeEntryIndex(4);
        E_DIST = nextEdgeEntryIndex(4);
        this.flagsSizeIsLong = encodingManager.getBytesForFlags() == 8;
        E_FLAGS = nextEdgeEntryIndex(encodingManager.getBytesForFlags());
        E_GEO = nextEdgeEntryIndex(4);
        E_NAME = nextEdgeEntryIndex(4);
        if (extStorage.isRequireEdgeField())
            E_ADDITIONAL = nextEdgeEntryIndex(4);
        else
            E_ADDITIONAL = -1;

        N_EDGE_REF = nextNodeEntryIndex(4);
        N_LAT = nextNodeEntryIndex(4);
        N_LON = nextNodeEntryIndex(4);
        if (nodeAccess.is3D())
            N_ELE = nextNodeEntryIndex(4);
        else
            N_ELE = -1;

        if (extStorage.isRequireNodeField())
            N_ADDITIONAL = nextNodeEntryIndex(4);
        else
            N_ADDITIONAL = -1;

        initNodeAndEdgeEntrySize();
        initialized = true;
    }

    protected int loadNodesHeader()
    {
        int hash = nodes.getHeader(0);
        if (hash != stringHashCode(getClass().getName()))
            throw new IllegalStateException("Cannot load the graph when using instance of "
                    + getClass().getName() + " and location: " + dir);

        nodeEntryBytes = nodes.getHeader(1 * 4);
        nodeCount = nodes.getHeader(2 * 4);
        bounds.minLon = Helper.intToDegree(nodes.getHeader(3 * 4));
        bounds.maxLon = Helper.intToDegree(nodes.getHeader(4 * 4));
        bounds.minLat = Helper.intToDegree(nodes.getHeader(5 * 4));
        bounds.maxLat = Helper.intToDegree(nodes.getHeader(6 * 4));

        if (bounds.hasElevation())
        {
            bounds.minEle = Helper.intToEle(nodes.getHeader(7 * 4));
            bounds.maxEle = Helper.intToEle(nodes.getHeader(8 * 4));
        }

        return 7;
    }

    protected int setNodesHeader()
    {
        nodes.setHeader(0, stringHashCode(getClass().getName()));
        nodes.setHeader(1 * 4, nodeEntryBytes);
        nodes.setHeader(2 * 4, nodeCount);
        nodes.setHeader(3 * 4, Helper.degreeToInt(bounds.minLon));
        nodes.setHeader(4 * 4, Helper.degreeToInt(bounds.maxLon));
        nodes.setHeader(5 * 4, Helper.degreeToInt(bounds.minLat));
        nodes.setHeader(6 * 4, Helper.degreeToInt(bounds.maxLat));
        if (bounds.hasElevation())
        {
            nodes.setHeader(7 * 4, Helper.eleToInt(bounds.minEle));
            nodes.setHeader(8 * 4, Helper.eleToInt(bounds.maxEle));
        }

        return 7;
    }

    protected int loadEdgesHeader()
    {
        edgeEntryBytes = edges.getHeader(0 * 4);
        edgeCount = edges.getHeader(1 * 4);
        return 4;
    }

    protected int setEdgesHeader()
    {
        edges.setHeader(0, edgeEntryBytes);
        edges.setHeader(1 * 4, edgeCount);
        edges.setHeader(2 * 4, encodingManager.hashCode());
        edges.setHeader(3 * 4, extStorage.hashCode());
        return 4;
    }

    protected int loadWayGeometryHeader()
    {
        maxGeoRef = wayGeometry.getHeader(0);
        return 1;
    }

    protected int setWayGeometryHeader()
    {
        wayGeometry.setHeader(0, maxGeoRef);
        return 1;
    }

    @Override
    public void flush()
    {
        setNodesHeader();
        setEdgesHeader();
        setWayGeometryHeader();

        properties.flush();
        wayGeometry.flush();
        nameIndex.flush();
        edges.flush();
        nodes.flush();
        extStorage.flush();
    }

    @Override
    public void close()
    {
        properties.close();
        wayGeometry.close();
        nameIndex.close();
        edges.close();
        nodes.close();
        extStorage.close();
    }

    @Override
    public boolean isClosed()
    {
        return nodes.isClosed();
    }

    @Override
    public GraphExtension getExtension()
    {
        return extStorage;
    }

    @Override
    public long getCapacity()
    {
        return edges.getCapacity() + nodes.getCapacity() + nameIndex.getCapacity() + wayGeometry.getCapacity()
                + properties.getCapacity() + extStorage.getCapacity();
    }

    @Override
    public String toDetailsString()
    {
        return "edges:" + nf(edgeCount) + "(" + edges.getCapacity() / Helper.MB + "), "
                + "nodes:" + nf(nodeCount) + "(" + nodes.getCapacity() / Helper.MB + "), "
                + "name: /(" + nameIndex.getCapacity() / Helper.MB + "), "
                + "geo:" + nf(maxGeoRef) + "(" + wayGeometry.getCapacity() / Helper.MB + "), "
                + "bounds:" + bounds;
    }

    // workaround for graphhopper-ios https://github.com/google/j2objc/issues/423
    private int stringHashCode( String str )
    {
        try
        {
            return java.util.Arrays.hashCode(str.getBytes("UTF-8"));
        } catch (UnsupportedEncodingException ex)
        {
            throw new UnsupportedOperationException(ex);
        }
    }

    @Override
    public String toString()
    {
        return getClass().getSimpleName()
                + "|" + encodingManager
                + "|" + getDirectory().getDefaultType()
                + "|" + nodeAccess.getDimension() + "D"
                + ((extStorage == null) ? "" : "|" + extStorage)
                + "|" + getProperties().versionsToString();
    }
}


File: core/src/main/java/com/graphhopper/storage/GraphStorage.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.storage;

import com.graphhopper.routing.util.EncodingManager;

public interface GraphStorage extends Graph, Storable<GraphStorage>
{
    Directory getDirectory();

    EncodingManager getEncodingManager();

    void setSegmentSize( int bytes );

    String toDetailsString();

    StorableProperties getProperties();

    /**
     * Schedule the deletion of the specified node until an optimize() call happens
     */
    void markNodeRemoved( int index );

    /**
     * Checks if the specified node is marked as removed.
     */
    boolean isNodeRemoved( int index );

    /**
     * Performs optimization routines like deletion or node rearrangements.
     */
    void optimize();
}


File: core/src/main/java/com/graphhopper/storage/TurnCostExtension.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.storage;

import com.graphhopper.util.EdgeIterator;

/**
 * Holds turn cost tables for each node. The additional field of a node will be used to point
 * towards the first entry within a node cost table to identify turn restrictions, or later, turn
 * getCosts.
 * <p/>
 * @author Karl Hübner
 * @author Peter Karich
 */
public class TurnCostExtension implements GraphExtension
{
    /* pointer for no cost entry */
    private final int NO_TURN_ENTRY = -1;
    private final long EMPTY_FLAGS = 0L;

    /*
     * items in turn cost tables: edge from, edge to, getCosts, pointer to next
     * cost entry of same node
     */
    private final int TC_FROM, TC_TO, TC_FLAGS, TC_NEXT;

    private DataAccess turnCosts;
    private int turnCostsEntryIndex = -4;
    private int turnCostsEntryBytes;
    private int turnCostsCount;

    private GraphStorage graph;
    private NodeAccess nodeAccess;

    public TurnCostExtension()
    {
        TC_FROM = nextTurnCostEntryIndex();
        TC_TO = nextTurnCostEntryIndex();
        TC_FLAGS = nextTurnCostEntryIndex();
        TC_NEXT = nextTurnCostEntryIndex();
        turnCostsEntryBytes = turnCostsEntryIndex + 4;
        turnCostsCount = 0;
    }

    @Override
    public void init( GraphStorage graph )
    {
        if (turnCostsCount > 0)
            throw new AssertionError("The turn cost storage must be initialized only once.");

        this.graph = graph;
        this.nodeAccess = graph.getNodeAccess();
        this.turnCosts = this.graph.getDirectory().find("turn_costs");
    }

    private int nextTurnCostEntryIndex()
    {
        turnCostsEntryIndex += 4;
        return turnCostsEntryIndex;
    }

    @Override
    public void setSegmentSize( int bytes )
    {
        turnCosts.setSegmentSize(bytes);
    }

    @Override
    public TurnCostExtension create( long initBytes )
    {
        turnCosts.create((long) initBytes * turnCostsEntryBytes);
        return this;
    }

    @Override
    public void flush()
    {
        turnCosts.setHeader(0, turnCostsEntryBytes);
        turnCosts.setHeader(1 * 4, turnCostsCount);
        turnCosts.flush();
    }

    @Override
    public void close()
    {
        turnCosts.close();
    }

    @Override
    public long getCapacity()
    {
        return turnCosts.getCapacity();
    }

    @Override
    public boolean loadExisting()
    {
        if (!turnCosts.loadExisting())
            return false;

        turnCostsEntryBytes = turnCosts.getHeader(0);
        turnCostsCount = turnCosts.getHeader(4);
        return true;
    }

    /**
     * This method adds a new entry which is a turn restriction or cost information via the
     * turnFlags.
     */
    public void addTurnInfo( int from, int viaNode, int to, long turnFlags )
    {
        // no need to store turn information
        if (turnFlags == EMPTY_FLAGS)
            return;

        // append
        int newEntryIndex = turnCostsCount;
        turnCostsCount++;
        ensureTurnCostIndex(newEntryIndex);

        // determine if we already have an cost entry for this node
        int previousEntryIndex = nodeAccess.getAdditionalNodeField(viaNode);
        if (previousEntryIndex == NO_TURN_ENTRY)
        {
            // set cost-pointer to this new cost entry
            nodeAccess.setAdditionalNodeField(viaNode, newEntryIndex);
        } else
        {
            int i = 0;
            int tmp = previousEntryIndex;
            while ((tmp = turnCosts.getInt((long) tmp * turnCostsEntryBytes + TC_NEXT)) != NO_TURN_ENTRY)
            {
                previousEntryIndex = tmp;
                // search for the last added cost entry
                if (i++ > 1000)
                {
                    throw new IllegalStateException("Something unexpected happened. A node probably will not have 1000+ relations.");
                }
            }
            // set next-pointer to this new cost entry
            turnCosts.setInt((long) previousEntryIndex * turnCostsEntryBytes + TC_NEXT, newEntryIndex);
        }
        // add entry
        long costsBase = (long) newEntryIndex * turnCostsEntryBytes;
        turnCosts.setInt(costsBase + TC_FROM, from);
        turnCosts.setInt(costsBase + TC_TO, to);
        turnCosts.setInt(costsBase + TC_FLAGS, (int) turnFlags);
        // next-pointer is NO_TURN_ENTRY
        turnCosts.setInt(costsBase + TC_NEXT, NO_TURN_ENTRY);
    }

    /**
     * @return turn flags of the specified node and edge properties.
     */
    public long getTurnCostFlags( int edgeFrom, int nodeVia, int edgeTo )
    {
        if (edgeFrom == EdgeIterator.NO_EDGE || edgeTo == EdgeIterator.NO_EDGE)
            throw new IllegalArgumentException("from and to edge cannot be NO_EDGE");
        if (nodeVia < 0)
            throw new IllegalArgumentException("via node cannot be negative");

        return nextCostFlags(edgeFrom, nodeVia, edgeTo);
    }

    private long nextCostFlags( int edgeFrom, int nodeVia, int edgeTo )
    {
        int turnCostIndex = nodeAccess.getAdditionalNodeField(nodeVia);
        int i = 0;
        for (; i < 1000; i++)
        {
            if (turnCostIndex == NO_TURN_ENTRY)
                break;
            long turnCostPtr = (long) turnCostIndex * turnCostsEntryBytes;
            if (edgeFrom == turnCosts.getInt(turnCostPtr + TC_FROM))
            {
                if (edgeTo == turnCosts.getInt(turnCostPtr + TC_TO))
                    return turnCosts.getInt(turnCostPtr + TC_FLAGS);
            }

            int nextTurnCostIndex = turnCosts.getInt(turnCostPtr + TC_NEXT);
            if (nextTurnCostIndex == turnCostIndex)
                throw new IllegalStateException("something went wrong: next entry would be the same");

            turnCostIndex = nextTurnCostIndex;
        }
        // so many turn restrictions on one node? here is something wrong
        if (i > 1000)
            throw new IllegalStateException("something went wrong: there seems to be no end of the turn cost-list!?");
        return EMPTY_FLAGS;
    }

    private void ensureTurnCostIndex( int nodeIndex )
    {
        turnCosts.ensureCapacity(((long) nodeIndex + 4) * turnCostsEntryBytes);
    }

    @Override
    public boolean isRequireNodeField()
    {
        //we require the additional field in the graph to point to the first entry in the node table
        return true;
    }

    @Override
    public boolean isRequireEdgeField()
    {
        return false;
    }

    @Override
    public int getDefaultNodeFieldValue()
    {
        return NO_TURN_ENTRY;
    }

    @Override
    public int getDefaultEdgeFieldValue()
    {
        throw new UnsupportedOperationException("Not supported by this storage");
    }

    @Override
    public GraphExtension copyTo( GraphExtension clonedStorage )
    {
        if (!(clonedStorage instanceof TurnCostExtension))
        {
            throw new IllegalStateException("the extended storage to clone must be the same");
        }

        TurnCostExtension clonedTC = (TurnCostExtension) clonedStorage;

        turnCosts.copyTo(clonedTC.turnCosts);
        clonedTC.turnCostsCount = turnCostsCount;

        return clonedStorage;
    }

    @Override
    public boolean isClosed()
    {
        return turnCosts.isClosed();
    }

    @Override
    public String toString()
    {
        return "turnCost";
    }
}


File: core/src/main/java/com/graphhopper/storage/index/LocationIndexTree.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.storage.index;

import com.graphhopper.coll.GHBitSet;
import com.graphhopper.coll.GHTBitSet;
import com.graphhopper.geohash.SpatialKeyAlgo;
import com.graphhopper.routing.util.EdgeFilter;
import com.graphhopper.storage.DataAccess;
import com.graphhopper.storage.Directory;
import com.graphhopper.storage.Graph;
import com.graphhopper.storage.LevelGraph;
import com.graphhopper.storage.NodeAccess;
import com.graphhopper.util.*;
import com.graphhopper.util.shapes.BBox;
import com.graphhopper.util.shapes.GHPoint;
import gnu.trove.iterator.TIntIterator;
import gnu.trove.list.array.TIntArrayList;
import gnu.trove.procedure.TIntProcedure;
import gnu.trove.set.hash.TIntHashSet;

import java.util.*;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * This implementation implements an n-tree to get the closest node or edge from GPS coordinates.
 * <p/>
 * All leafs are at the same depth, otherwise it is quite complicated to calculate the bresenham
 * line for different resolutions, especially if a leaf node could be split into a tree-node and
 * resolution changes.
 * <p/>
 * @author Peter Karich
 */
public class LocationIndexTree implements LocationIndex
{
    private final Logger logger = LoggerFactory.getLogger(getClass());
    private final int MAGIC_INT;
    protected DistanceCalc distCalc = Helper.DIST_PLANE;
    private DistanceCalc preciseDistCalc = Helper.DIST_EARTH;
    protected final Graph graph;
    private final NodeAccess nodeAccess;
    final DataAccess dataAccess;
    private int[] entries;
    private byte[] shifts;
    // convert spatial key to index for subentry of current depth
    private long[] bitmasks;
    protected SpatialKeyAlgo keyAlgo;
    private int minResolutionInMeter = 300;
    private double deltaLat;
    private double deltaLon;
    private int initSizeLeafEntries = 4;
    private boolean initialized = false;
    // do not start with 0 as a positive value means leaf and a negative means "entry with subentries"
    static final int START_POINTER = 1;
    int maxRegionSearch = 4;
    /**
     * If normed distance is smaller than this value the node or edge is 'identical' and the
     * algorithm can stop search.
     */
    private double equalNormedDelta;

    /**
     * @param g the graph for which this index should do the lookup based on latitude,longitude.
     */
    public LocationIndexTree( Graph g, Directory dir )
    {
        if (g instanceof LevelGraph)
            throw new IllegalArgumentException("Call LevelGraph.getBaseGraph() instead of using the LevelGraph itself");

        MAGIC_INT = Integer.MAX_VALUE / 22316;
        this.graph = g;
        this.nodeAccess = g.getNodeAccess();
        dataAccess = dir.find("location_index");
    }

    public int getMinResolutionInMeter()
    {
        return minResolutionInMeter;
    }

    /**
     * Minimum width in meter of one tile. Decrease this if you need faster queries, but keep in
     * mind that then queries with different coordinates are more likely to fail.
     */
    public LocationIndexTree setMinResolutionInMeter( int minResolutionInMeter )
    {
        this.minResolutionInMeter = minResolutionInMeter;
        return this;
    }

    /**
     * Searches also neighbouring tiles until the maximum distance from the query point is reached
     * (minResolutionInMeter*regionAround). Set to 1 for to force avoiding a fall back, good if you
     * have strict performance and lookup-quality requirements. Default is 4.
     */
    public LocationIndexTree setMaxRegionSearch( int numTiles )
    {
        if (numTiles < 1)
            throw new IllegalArgumentException("Region of location index must be at least 1 but was " + numTiles);

        // see #232
        if (numTiles % 2 == 1)
            numTiles++;

        this.maxRegionSearch = numTiles;
        return this;
    }

    void prepareAlgo()
    {
        // 0.1 meter should count as 'equal'
        equalNormedDelta = distCalc.calcNormalizedDist(0.1);

        // now calculate the necessary maxDepth d for our current bounds
        // if we assume a minimum resolution like 0.5km for a leaf-tile                
        // n^(depth/2) = toMeter(dLon) / minResolution
        BBox bounds = graph.getBounds();
        if (graph.getNodes() == 0)
            throw new IllegalStateException("Cannot create location index of empty graph!");

        if (!bounds.isValid())
            throw new IllegalStateException("Cannot create location index when graph has invalid bounds: " + bounds);

        double lat = Math.min(Math.abs(bounds.maxLat), Math.abs(bounds.minLat));
        double maxDistInMeter = Math.max(
                (bounds.maxLat - bounds.minLat) / 360 * DistanceCalcEarth.C,
                (bounds.maxLon - bounds.minLon) / 360 * preciseDistCalc.calcCircumference(lat));
        double tmp = maxDistInMeter / minResolutionInMeter;
        tmp = tmp * tmp;
        TIntArrayList tmpEntries = new TIntArrayList();
        // the last one is always 4 to reduce costs if only a single entry
        tmp /= 4;
        while (tmp > 1)
        {
            int tmpNo;
            if (tmp >= 64)
            {
                tmpNo = 64;
            } else if (tmp >= 16)
            {
                tmpNo = 16;
            } else if (tmp >= 4)
            {
                tmpNo = 4;
            } else
            {
                break;
            }
            tmpEntries.add(tmpNo);
            tmp /= tmpNo;
        }
        tmpEntries.add(4);
        initEntries(tmpEntries.toArray());
        int shiftSum = 0;
        long parts = 1;
        for (int i = 0; i < shifts.length; i++)
        {
            shiftSum += shifts[i];
            parts *= entries[i];
        }
        if (shiftSum > 64)
            throw new IllegalStateException("sum of all shifts does not fit into a long variable");

        keyAlgo = new SpatialKeyAlgo(shiftSum).bounds(bounds);
        parts = Math.round(Math.sqrt(parts));
        deltaLat = (bounds.maxLat - bounds.minLat) / parts;
        deltaLon = (bounds.maxLon - bounds.minLon) / parts;
    }

    private LocationIndexTree initEntries( int[] entries )
    {
        if (entries.length < 1)
        // at least one depth should have been specified
        {
            throw new IllegalStateException("depth needs to be at least 1");
        }
        this.entries = entries;
        int depth = entries.length;
        shifts = new byte[depth];
        bitmasks = new long[depth];
        int lastEntry = entries[0];
        for (int i = 0; i < depth; i++)
        {
            if (lastEntry < entries[i])
            {
                throw new IllegalStateException("entries should decrease or stay but was:"
                        + Arrays.toString(entries));
            }
            lastEntry = entries[i];
            shifts[i] = getShift(entries[i]);
            bitmasks[i] = getBitmask(shifts[i]);
        }
        return this;
    }

    private byte getShift( int entries )
    {
        byte b = (byte) Math.round(Math.log(entries) / Math.log(2));
        if (b <= 0)
            throw new IllegalStateException("invalid shift:" + b);

        return b;
    }

    private long getBitmask( int shift )
    {
        long bm = (1L << shift) - 1;
        if (bm <= 0)
        {
            throw new IllegalStateException("invalid bitmask:" + bm);
        }
        return bm;
    }

    InMemConstructionIndex getPrepareInMemIndex()
    {
        InMemConstructionIndex memIndex = new InMemConstructionIndex(entries[0]);
        memIndex.prepare();
        return memIndex;
    }

    @Override
    public int findID( double lat, double lon )
    {
        QueryResult res = findClosest(lat, lon, EdgeFilter.ALL_EDGES);
        if (res == null)
            return -1;

        return res.getClosestNode();
    }

    @Override
    public LocationIndex setResolution( int minResolutionInMeter )
    {
        if (minResolutionInMeter <= 0)
            throw new IllegalStateException("Negative precision is not allowed!");

        setMinResolutionInMeter(minResolutionInMeter);
        return this;
    }

    @Override
    public LocationIndex setApproximation( boolean approx )
    {
        if (approx)
            distCalc = Helper.DIST_PLANE;
        else
            distCalc = Helper.DIST_EARTH;
        return this;
    }

    @Override
    public LocationIndexTree create( long size )
    {
        throw new UnsupportedOperationException("Not supported. Use prepareIndex instead.");
    }

    @Override
    public boolean loadExisting()
    {
        if (initialized)
            throw new IllegalStateException("Call loadExisting only once");

        if (!dataAccess.loadExisting())
            return false;

        if (dataAccess.getHeader(0) != MAGIC_INT)
            throw new IllegalStateException("incorrect location index version, expected:" + MAGIC_INT);

        if (dataAccess.getHeader(1 * 4) != calcChecksum())
            throw new IllegalStateException("location index was opened with incorrect graph: "
                    + dataAccess.getHeader(1 * 4) + " vs. " + calcChecksum());

        setMinResolutionInMeter(dataAccess.getHeader(2 * 4));
        prepareAlgo();
        initialized = true;
        return true;
    }

    @Override
    public void flush()
    {
        dataAccess.setHeader(0, MAGIC_INT);
        dataAccess.setHeader(1 * 4, calcChecksum());
        dataAccess.setHeader(2 * 4, minResolutionInMeter);

        // saving space not necessary: dataAccess.trimTo((lastPointer + 1) * 4);
        dataAccess.flush();
    }

    @Override
    public LocationIndex prepareIndex()
    {
        if (initialized)
            throw new IllegalStateException("Call prepareIndex only once");

        StopWatch sw = new StopWatch().start();
        prepareAlgo();
        // in-memory preparation
        InMemConstructionIndex inMem = getPrepareInMemIndex();

        // compact & store to dataAccess
        dataAccess.create(64 * 1024);
        try
        {
            inMem.store(inMem.root, START_POINTER);
            flush();
        } catch (Exception ex)
        {
            throw new IllegalStateException("Problem while storing location index. " + Helper.getMemInfo(), ex);
        }
        float entriesPerLeaf = (float) inMem.size / inMem.leafs;
        initialized = true;
        logger.info("location index created in " + sw.stop().getSeconds()
                + "s, size:" + Helper.nf(inMem.size)
                + ", leafs:" + Helper.nf(inMem.leafs)
                + ", precision:" + minResolutionInMeter
                + ", depth:" + entries.length
                + ", checksum:" + calcChecksum()
                + ", entries:" + Arrays.toString(entries)
                + ", entriesPerLeaf:" + entriesPerLeaf);

        return this;
    }

    int calcChecksum()
    {
        // do not include the edges as we could get problem with LevelGraph due to shortcuts
        // ^ graph.getAllEdges().count();
        return graph.getNodes();
    }

    @Override
    public void close()
    {
        dataAccess.close();
    }

    @Override
    public boolean isClosed()
    {
        return dataAccess.isClosed();
    }

    @Override
    public long getCapacity()
    {
        return dataAccess.getCapacity();
    }

    @Override
    public void setSegmentSize( int bytes )
    {
        dataAccess.setSegmentSize(bytes);
    }

    class InMemConstructionIndex
    {
        int size;
        int leafs;
        InMemTreeEntry root;

        public InMemConstructionIndex( int noOfSubEntries )
        {
            root = new InMemTreeEntry(noOfSubEntries);
        }

        void prepare()
        {
            final EdgeIterator allIter = graph.getAllEdges();
            try
            {
                while (allIter.next())
                {
                    int nodeA = allIter.getBaseNode();
                    int nodeB = allIter.getAdjNode();
                    double lat1 = nodeAccess.getLatitude(nodeA);
                    double lon1 = nodeAccess.getLongitude(nodeA);
                    double lat2;
                    double lon2;
                    PointList points = allIter.fetchWayGeometry(0);
                    int len = points.getSize();
                    for (int i = 0; i < len; i++)
                    {
                        lat2 = points.getLatitude(i);
                        lon2 = points.getLongitude(i);
                        addNode(nodeA, nodeB, lat1, lon1, lat2, lon2);
                        lat1 = lat2;
                        lon1 = lon2;
                    }
                    lat2 = nodeAccess.getLatitude(nodeB);
                    lon2 = nodeAccess.getLongitude(nodeB);
                    addNode(nodeA, nodeB, lat1, lon1, lat2, lon2);
                }
            } catch (Exception ex)
            {
                logger.error("Problem! base:" + allIter.getBaseNode() + ", adj:" + allIter.getAdjNode()
                        + ", edge:" + allIter.getEdge(), ex);
            }
        }

        void addNode( final int nodeA, final int nodeB,
                      final double lat1, final double lon1,
                      final double lat2, final double lon2 )
        {
            PointEmitter pointEmitter = new PointEmitter()
            {
                @Override
                public void set( double lat, double lon )
                {
                    long key = keyAlgo.encode(lat, lon);
                    long keyPart = createReverseKey(key);
                    // no need to feed both nodes as we search neighbors in fillIDs
                    addNode(root, nodeA, 0, keyPart, key);
                }
            };
            BresenhamLine.calcPoints(lat1, lon1, lat2, lon2, pointEmitter,
                    graph.getBounds().minLat, graph.getBounds().minLon,
                    deltaLat, deltaLon);
        }

        void addNode( InMemEntry entry, int nodeId, int depth, long keyPart, long key )
        {
            if (entry.isLeaf())
            {
                InMemLeafEntry leafEntry = (InMemLeafEntry) entry;
                leafEntry.addNode(nodeId);
            } else
            {
                int index = (int) (bitmasks[depth] & keyPart);
                keyPart = keyPart >>> shifts[depth];
                InMemTreeEntry treeEntry = ((InMemTreeEntry) entry);
                InMemEntry subentry = treeEntry.getSubEntry(index);
                depth++;
                if (subentry == null)
                {
                    if (depth == entries.length)
                    {
                        subentry = new InMemLeafEntry(initSizeLeafEntries, key);
                    } else
                    {
                        subentry = new InMemTreeEntry(entries[depth]);
                    }
                    treeEntry.setSubEntry(index, subentry);
                }

                addNode(subentry, nodeId, depth, keyPart, key);
            }
        }

        Collection<InMemEntry> getEntriesOf( int selectDepth )
        {
            List<InMemEntry> list = new ArrayList<InMemEntry>();
            fillLayer(list, selectDepth, 0, ((InMemTreeEntry) root).getSubEntriesForDebug());
            return list;
        }

        void fillLayer( Collection<InMemEntry> list, int selectDepth, int depth, Collection<InMemEntry> entries )
        {
            for (InMemEntry entry : entries)
            {
                if (selectDepth == depth)
                {
                    list.add(entry);
                } else if (entry instanceof InMemTreeEntry)
                {
                    fillLayer(list, selectDepth, depth + 1, ((InMemTreeEntry) entry).getSubEntriesForDebug());
                }
            }
        }

        String print()
        {
            StringBuilder sb = new StringBuilder();
            print(root, sb, 0, 0);
            return sb.toString();
        }

        void print( InMemEntry e, StringBuilder sb, long key, int depth )
        {
            if (e.isLeaf())
            {
                InMemLeafEntry leaf = (InMemLeafEntry) e;
                int bits = keyAlgo.getBits();
                // print reverse keys
                sb.append(BitUtil.BIG.toBitString(BitUtil.BIG.reverse(key, bits), bits)).append("  ");
                TIntArrayList entries = leaf.getResults();
                for (int i = 0; i < entries.size(); i++)
                {
                    sb.append(leaf.get(i)).append(',');
                }
                sb.append('\n');
            } else
            {
                InMemTreeEntry tree = (InMemTreeEntry) e;
                key = key << shifts[depth];
                for (int counter = 0; counter < tree.subEntries.length; counter++)
                {
                    InMemEntry sube = tree.subEntries[counter];
                    if (sube != null)
                    {
                        print(sube, sb, key | counter, depth + 1);
                    }
                }
            }
        }

        // store and freezes tree
        int store( InMemEntry entry, int intIndex )
        {
            long refPointer = (long) intIndex * 4;
            if (entry.isLeaf())
            {
                InMemLeafEntry leaf = ((InMemLeafEntry) entry);
                TIntArrayList entries = leaf.getResults();
                int len = entries.size();
                if (len == 0)
                {
                    return intIndex;
                }
                size += len;
                intIndex++;
                leafs++;
                dataAccess.ensureCapacity((long) (intIndex + len + 1) * 4);
                if (len == 1)
                {
                    // less disc space for single entries
                    dataAccess.setInt(refPointer, -entries.get(0) - 1);
                } else
                {
                    for (int index = 0; index < len; index++, intIndex++)
                    {
                        dataAccess.setInt((long) intIndex * 4, entries.get(index));
                    }
                    dataAccess.setInt(refPointer, intIndex);
                }
            } else
            {
                InMemTreeEntry treeEntry = ((InMemTreeEntry) entry);
                int len = treeEntry.subEntries.length;
                intIndex += len;
                for (int subCounter = 0; subCounter < len; subCounter++, refPointer += 4)
                {
                    InMemEntry subEntry = treeEntry.subEntries[subCounter];
                    if (subEntry == null)
                    {
                        continue;
                    }
                    dataAccess.ensureCapacity((long) (intIndex + 1) * 4);
                    int beforeIntIndex = intIndex;
                    intIndex = store(subEntry, beforeIntIndex);
                    if (intIndex == beforeIntIndex)
                    {
                        dataAccess.setInt(refPointer, 0);
                    } else
                    {
                        dataAccess.setInt(refPointer, beforeIntIndex);
                    }
                }
            }
            return intIndex;
        }
    }

    TIntArrayList getEntries()
    {
        return new TIntArrayList(entries);
    }

    // fillIDs according to how they are stored
    final void fillIDs( long keyPart, int intIndex, TIntHashSet set, int depth )
    {
        long pointer = (long) intIndex << 2;
        if (depth == entries.length)
        {
            int value = dataAccess.getInt(pointer);
            if (value < 0)
            // single data entries (less disc space)            
            {
                set.add(-(value + 1));
            } else
            {
                long max = (long) value * 4;
                // leaf entry => value is maxPointer
                for (long leafIndex = pointer + 4; leafIndex < max; leafIndex += 4)
                {
                    set.add(dataAccess.getInt(leafIndex));
                }
            }
            return;
        }
        int offset = (int) (bitmasks[depth] & keyPart) << 2;
        int value = dataAccess.getInt(pointer + offset);
        if (value > 0)
        {
            // tree entry => negative value points to subentries
            fillIDs(keyPart >>> shifts[depth], value, set, depth + 1);
        }
    }

    // this method returns the spatial key in reverse order for easier right-shifting
    final long createReverseKey( double lat, double lon )
    {
        return BitUtil.BIG.reverse(keyAlgo.encode(lat, lon), keyAlgo.getBits());
    }

    final long createReverseKey( long key )
    {
        return BitUtil.BIG.reverse(key, keyAlgo.getBits());
    }

    /**
     * calculate the distance to the nearest tile border for a given lat/lon coordinate in the
     * context of a spatial key tile.
     * <p/>
     */
    final double calculateRMin( double lat, double lon )
    {
        return calculateRMin(lat, lon, 0);
    }

    /**
     * Calculates the distance to the nearest tile border, where the tile border is the rectangular
     * region with dimension 2*paddingTiles + 1 and where the center tile contains the given lat/lon
     * coordinate
     */
    final double calculateRMin( double lat, double lon, int paddingTiles )
    {
        GHPoint query = new GHPoint(lat, lon);
        long key = keyAlgo.encode(query);
        GHPoint center = new GHPoint();
        keyAlgo.decode(key, center);

        // deltaLat and deltaLon comes from the LocationIndex:
        double minLat = center.lat - (0.5 + paddingTiles) * deltaLat;
        double maxLat = center.lat + (0.5 + paddingTiles) * deltaLat;
        double minLon = center.lon - (0.5 + paddingTiles) * deltaLon;
        double maxLon = center.lon + (0.5 + paddingTiles) * deltaLon;

        double dSouthernLat = query.lat - minLat;
        double dNorthernLat = maxLat - query.lat;
        double dWesternLon = query.lon - minLon;
        double dEasternLon = maxLon - query.lon;

        // convert degree deltas into a radius in meter
        double dMinLat, dMinLon;
        if (dSouthernLat < dNorthernLat)
        {
            dMinLat = distCalc.calcDist(query.lat, query.lon, minLat, query.lon);
        } else
        {
            dMinLat = distCalc.calcDist(query.lat, query.lon, maxLat, query.lon);
        }

        if (dWesternLon < dEasternLon)
        {
            dMinLon = distCalc.calcDist(query.lat, query.lon, query.lat, minLon);
        } else
        {
            dMinLon = distCalc.calcDist(query.lat, query.lon, query.lat, maxLon);
        }

        double rMin = Math.min(dMinLat, dMinLon);
        return rMin;
    }

    /**
     * Provide info about tilesize for testing / visualization
     */
    double getDeltaLat()
    {
        return deltaLat;
    }

    double getDeltaLon()
    {
        return deltaLon;
    }

    GHPoint getCenter( double lat, double lon )
    {
        GHPoint query = new GHPoint(lat, lon);
        long key = keyAlgo.encode(query);
        GHPoint center = new GHPoint();
        keyAlgo.decode(key, center);
        return center;
    }

    /**
     * This method collects the node indices from the quad tree data structure in a certain order
     * which makes sure not too many nodes are collected as well as no nodes will be missing. See
     * discussion at issue #221.
     */
    public final TIntHashSet findNetworkEntries( double queryLat, double queryLon, int maxIteration )
    {
        TIntHashSet foundEntries = new TIntHashSet();

        for (int iteration = 0; iteration < maxIteration; iteration++)
        {
            // find entries in border of searchbox
            for (int yreg = -iteration; yreg <= iteration; yreg++)
            {
                double subqueryLat = queryLat + yreg * deltaLat;
                double subqueryLonA = queryLon - iteration * deltaLon;
                double subqueryLonB = queryLon + iteration * deltaLon;
                findNetworkEntriesSingleRegion(foundEntries, subqueryLat, subqueryLonA);

                // minor optimization for iteration == 0
                if (iteration > 0)
                {
                    findNetworkEntriesSingleRegion(foundEntries, subqueryLat, subqueryLonB);
                }
            }

            for (int xreg = -iteration + 1; xreg <= iteration - 1; xreg++)
            {
                double subqueryLon = queryLon + xreg * deltaLon;
                double subqueryLatA = queryLat - iteration * deltaLat;
                double subqueryLatB = queryLat + iteration * deltaLat;
                findNetworkEntriesSingleRegion(foundEntries, subqueryLatA, subqueryLon);
                findNetworkEntriesSingleRegion(foundEntries, subqueryLatB, subqueryLon);
            }

            // see #232
            if (iteration % 2 == 1)
            {
                // Check if something was found already...
                if (foundEntries.size() > 0)
                {
                    double rMin = calculateRMin(queryLat, queryLon, iteration);
                    double minDistance = calcMinDistance(queryLat, queryLon, foundEntries);

                    if (minDistance < rMin)
                    {   // resultEntries contains a nearest node for sure
                        break;
                    } // else: continue an undetected nearer node may sit in a neighbouring tile.
                    // Now calculate how far we have to look outside to find any hidden nearest nodes
                    // and repeat whole process with wider search area until this distance is covered.
                }
            }
        }
        return foundEntries;
    }

    final double calcMinDistance( double queryLat, double queryLon, TIntHashSet pointset )
    {
        double min = Double.MAX_VALUE;
        TIntIterator itr = pointset.iterator();
        while (itr.hasNext())
        {
            int node = itr.next();
            double lat = nodeAccess.getLat(node);
            double lon = nodeAccess.getLon(node);
            double dist = distCalc.calcDist(queryLat, queryLon, lat, lon);
            if (dist < min)
            {
                min = dist;
            }
        }
        return min;
    }

    final void findNetworkEntriesSingleRegion( TIntHashSet storedNetworkEntryIds, double queryLat, double queryLon )
    {
        long keyPart = createReverseKey(queryLat, queryLon);
        fillIDs(keyPart, START_POINTER, storedNetworkEntryIds, 0);
    }

    @Override
    public QueryResult findClosest( final double queryLat, final double queryLon, final EdgeFilter edgeFilter )
    {
        if (isClosed())
            throw new IllegalStateException("You need to create a new LocationIndex instance as it is already closed");

        final TIntHashSet storedNetworkEntryIds = findNetworkEntries(queryLat, queryLon, maxRegionSearch);
        final QueryResult closestMatch = new QueryResult(queryLat, queryLon);
        if (storedNetworkEntryIds.isEmpty())
            return closestMatch;

        // clone storedIds to avoid interference with forEach
        final GHBitSet checkBitset = new GHTBitSet(new TIntHashSet(storedNetworkEntryIds));
        // find nodes from the network entries which are close to 'point'
        final EdgeExplorer explorer = graph.createEdgeExplorer();
        storedNetworkEntryIds.forEach(new TIntProcedure()
        {
            @Override
            public boolean execute( int networkEntryNodeId )
            {
                new XFirstSearchCheck(queryLat, queryLon, checkBitset, edgeFilter)
                {
                    @Override
                    protected double getQueryDistance()
                    {
                        return closestMatch.getQueryDistance();
                    }

                    @Override
                    protected boolean check( int node, double normedDist, int wayIndex, EdgeIteratorState edge, QueryResult.Position pos )
                    {
                        if (normedDist < closestMatch.getQueryDistance())
                        {
                            closestMatch.setQueryDistance(normedDist);
                            closestMatch.setClosestNode(node);
                            closestMatch.setClosestEdge(edge.detach(false));
                            closestMatch.setWayIndex(wayIndex);
                            closestMatch.setSnappedPosition(pos);
                            return true;
                        }
                        return false;
                    }
                }.start(explorer, networkEntryNodeId);
                return true;
            }
        });

        if (closestMatch.isValid())
        {
            // denormalize distance            
            closestMatch.setQueryDistance(distCalc.calcDenormalizedDist(closestMatch.getQueryDistance()));
            closestMatch.calcSnappedPoint(distCalc);
        }

        return closestMatch;
    }

    /**
     * Make it possible to collect nearby location also for other purposes.
     */
    protected abstract class XFirstSearchCheck extends BreadthFirstSearch
    {
        boolean goFurther = true;
        double currNormedDist;
        double currLat;
        double currLon;
        int currNode;
        final double queryLat;
        final double queryLon;
        final GHBitSet checkBitset;
        final EdgeFilter edgeFilter;

        public XFirstSearchCheck( double queryLat, double queryLon, GHBitSet checkBitset, EdgeFilter edgeFilter )
        {
            this.queryLat = queryLat;
            this.queryLon = queryLon;
            this.checkBitset = checkBitset;
            this.edgeFilter = edgeFilter;
        }

        @Override
        protected GHBitSet createBitSet()
        {
            return checkBitset;
        }

        @Override
        protected boolean goFurther( int baseNode )
        {
            currNode = baseNode;
            currLat = nodeAccess.getLatitude(baseNode);
            currLon = nodeAccess.getLongitude(baseNode);
            currNormedDist = distCalc.calcNormalizedDist(queryLat, queryLon, currLat, currLon);
            return goFurther;
        }

        @Override
        protected boolean checkAdjacent( EdgeIteratorState currEdge )
        {
            goFurther = false;
            if (!edgeFilter.accept(currEdge))
            {
                // only limit the adjNode to a certain radius as currNode could be the wrong side of a valid edge
                // goFurther = currDist < minResolution2InMeterNormed;
                return true;
            }

            int tmpClosestNode = currNode;
            if (check(tmpClosestNode, currNormedDist, 0, currEdge, QueryResult.Position.TOWER))
            {
                if (currNormedDist <= equalNormedDelta)
                    return false;
            }

            int adjNode = currEdge.getAdjNode();
            double adjLat = nodeAccess.getLatitude(adjNode);
            double adjLon = nodeAccess.getLongitude(adjNode);
            double adjDist = distCalc.calcNormalizedDist(adjLat, adjLon, queryLat, queryLon);
            // if there are wayPoints this is only an approximation
            if (adjDist < currNormedDist)
                tmpClosestNode = adjNode;

            double tmpLat = currLat;
            double tmpLon = currLon;
            double tmpNormedDist;
            PointList pointList = currEdge.fetchWayGeometry(2);
            int len = pointList.getSize();
            for (int pointIndex = 0; pointIndex < len; pointIndex++)
            {
                double wayLat = pointList.getLatitude(pointIndex);
                double wayLon = pointList.getLongitude(pointIndex);
                QueryResult.Position pos = QueryResult.Position.EDGE;
                if (distCalc.validEdgeDistance(queryLat, queryLon, tmpLat, tmpLon, wayLat, wayLon))
                {
                    tmpNormedDist = distCalc.calcNormalizedEdgeDistance(queryLat, queryLon,
                            tmpLat, tmpLon, wayLat, wayLon);
                    check(tmpClosestNode, tmpNormedDist, pointIndex, currEdge, pos);
                } else
                {
                    if (pointIndex + 1 == len)
                    {
                        tmpNormedDist = adjDist;
                        pos = QueryResult.Position.TOWER;
                    } else
                    {
                        tmpNormedDist = distCalc.calcNormalizedDist(queryLat, queryLon, wayLat, wayLon);
                        pos = QueryResult.Position.PILLAR;
                    }
                    check(tmpClosestNode, tmpNormedDist, pointIndex + 1, currEdge, pos);
                }

                if (tmpNormedDist <= equalNormedDelta)
                    return false;

                tmpLat = wayLat;
                tmpLon = wayLon;
            }
            return getQueryDistance() > equalNormedDelta;
        }

        protected abstract double getQueryDistance();

        protected abstract boolean check( int node, double normedDist, int wayIndex, EdgeIteratorState iter, QueryResult.Position pos );
    }

    // make entries static as otherwise we get an additional reference to this class (memory waste)
    static interface InMemEntry
    {
        boolean isLeaf();
    }

    static class InMemLeafEntry extends SortedIntSet implements InMemEntry
    {
        // private long key;

        public InMemLeafEntry( int count, long key )
        {
            super(count);
            // this.key = key;
        }

        public boolean addNode( int nodeId )
        {
            return addOnce(nodeId);
        }

        @Override
        public final boolean isLeaf()
        {
            return true;
        }

        @Override
        public String toString()
        {
            return "LEAF " + /*key +*/ " " + super.toString();
        }

        TIntArrayList getResults()
        {
            return this;
        }
    }

    // Space efficient sorted integer set. Suited for only a few entries.
    static class SortedIntSet extends TIntArrayList
    {
        public SortedIntSet()
        {
        }

        public SortedIntSet( int capacity )
        {
            super(capacity);
        }

        /**
         * Allow adding a value only once
         */
        public boolean addOnce( int value )
        {
            int foundIndex = binarySearch(value);
            if (foundIndex >= 0)
            {
                return false;
            }
            foundIndex = -foundIndex - 1;
            insert(foundIndex, value);
            return true;
        }
    }

    static class InMemTreeEntry implements InMemEntry
    {
        InMemEntry[] subEntries;

        public InMemTreeEntry( int subEntryNo )
        {
            subEntries = new InMemEntry[subEntryNo];
        }

        public InMemEntry getSubEntry( int index )
        {
            return subEntries[index];
        }

        public void setSubEntry( int index, InMemEntry subEntry )
        {
            this.subEntries[index] = subEntry;
        }

        public Collection<InMemEntry> getSubEntriesForDebug()
        {
            List<InMemEntry> list = new ArrayList<InMemEntry>();
            for (InMemEntry e : subEntries)
            {
                if (e != null)
                {
                    list.add(e);
                }
            }
            return list;
        }

        @Override
        public final boolean isLeaf()
        {
            return false;
        }

        @Override
        public String toString()
        {
            return "TREE";
        }
    }
}


File: core/src/main/java/com/graphhopper/util/GHUtility.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.util;

import com.graphhopper.coll.GHBitSet;
import com.graphhopper.coll.GHBitSetImpl;
import com.graphhopper.routing.util.AllEdgesIterator;
import com.graphhopper.routing.util.AllEdgesSkipIterator;
import com.graphhopper.routing.util.EdgeFilter;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.routing.util.FlagEncoder;
import com.graphhopper.storage.*;
import gnu.trove.list.TIntList;
import gnu.trove.list.array.TIntArrayList;

import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * A helper class to avoid cluttering the Graph interface with all the common methods. Most of the
 * methods are useful for unit tests or debugging only.
 * <p/>
 * @author Peter Karich
 */
public class GHUtility
{
    /**
     * @throws could throw exception if uncatched problems like index out of bounds etc
     */
    public static List<String> getProblems( Graph g )
    {
        List<String> problems = new ArrayList<String>();
        int nodes = g.getNodes();
        int nodeIndex = 0;
        NodeAccess na = g.getNodeAccess();
        try
        {
            EdgeExplorer explorer = g.createEdgeExplorer();
            for (; nodeIndex < nodes; nodeIndex++)
            {
                double lat = na.getLatitude(nodeIndex);
                if (lat > 90 || lat < -90)
                    problems.add("latitude is not within its bounds " + lat);

                double lon = na.getLongitude(nodeIndex);
                if (lon > 180 || lon < -180)
                    problems.add("longitude is not within its bounds " + lon);

                EdgeIterator iter = explorer.setBaseNode(nodeIndex);
                while (iter.next())
                {
                    if (iter.getAdjNode() >= nodes)
                    {
                        problems.add("edge of " + nodeIndex + " has a node " + iter.getAdjNode() + " greater or equal to getNodes");
                    }
                    if (iter.getAdjNode() < 0)
                    {
                        problems.add("edge of " + nodeIndex + " has a negative node " + iter.getAdjNode());
                    }
                }
            }
        } catch (Exception ex)
        {
            throw new RuntimeException("problem with node " + nodeIndex, ex);
        }

//        for (int i = 0; i < nodes; i++) {
//            new BreadthFirstSearch().start(g, i);
//        }
        return problems;
    }

    /**
     * Counts reachable edges.
     */
    public static int count( EdgeIterator iter )
    {
        int counter = 0;
        while (iter.next())
        {
            counter++;
        }
        return counter;
    }

    public static Set<Integer> asSet( int... values )
    {
        Set<Integer> s = new HashSet<Integer>();
        for (int v : values)
        {
            s.add(v);
        }
        return s;
    }

    public static Set<Integer> getNeighbors( EdgeIterator iter )
    {
        // make iteration order over set static => linked
        Set<Integer> list = new LinkedHashSet<Integer>();
        while (iter.next())
        {
            list.add(iter.getAdjNode());
        }
        return list;
    }

    public static List<Integer> getEdgeIds( EdgeIterator iter )
    {
        List<Integer> list = new ArrayList<Integer>();
        while (iter.next())
        {
            list.add(iter.getEdge());
        }
        return list;
    }

    public static void printEdgeInfo( final Graph g, FlagEncoder encoder )
    {
        System.out.println("-- Graph n:" + g.getNodes() + " e:" + g.getAllEdges().getCount() + " ---");
        AllEdgesIterator iter = g.getAllEdges();
        while (iter.next())
        {
            String sc = "";
            if (iter instanceof AllEdgesSkipIterator)
            {
                AllEdgesSkipIterator aeSkip = (AllEdgesSkipIterator) iter;
                sc = aeSkip.isShortcut() ? "sc" : "  ";
            }
            String fwdStr = encoder.isForward(iter.getFlags()) ? "fwd" : "   ";
            String bckStr = encoder.isBackward(iter.getFlags()) ? "bckwd" : "";
            System.out.println(sc + " " + iter + " " + fwdStr + " " + bckStr);
        }
    }

    public static void printInfo( final Graph g, int startNode, final int counts, final EdgeFilter filter )
    {
        new BreadthFirstSearch()
        {
            int counter = 0;

            @Override
            protected boolean goFurther( int nodeId )
            {
                System.out.println(getNodeInfo(g, nodeId, filter));
                if (counter++ > counts)
                {
                    return false;
                }
                return true;
            }
        }.start(g.createEdgeExplorer(), startNode);
    }

    public static String getNodeInfo( LevelGraph g, int nodeId, EdgeFilter filter )
    {
        EdgeSkipExplorer ex = g.createEdgeExplorer(filter);
        EdgeSkipIterator iter = ex.setBaseNode(nodeId);
        NodeAccess na = g.getNodeAccess();
        String str = nodeId + ":" + na.getLatitude(nodeId) + "," + na.getLongitude(nodeId) + "\n";
        while (iter.next())
        {
            str += "  ->" + iter.getAdjNode() + "(" + iter.getSkippedEdge1() + "," + iter.getSkippedEdge2() + ") "
                    + iter.getEdge() + " \t" + BitUtil.BIG.toBitString(iter.getFlags(), 8) + "\n";
        }
        return str;
    }

    public static String getNodeInfo( Graph g, int nodeId, EdgeFilter filter )
    {
        EdgeIterator iter = g.createEdgeExplorer(filter).setBaseNode(nodeId);
        NodeAccess na = g.getNodeAccess();
        String str = nodeId + ":" + na.getLatitude(nodeId) + "," + na.getLongitude(nodeId) + "\n";
        while (iter.next())
        {
            str += "  ->" + iter.getAdjNode() + " (" + iter.getDistance() + ") pillars:"
                    + iter.fetchWayGeometry(0).getSize() + ", edgeId:" + iter.getEdge()
                    + "\t" + BitUtil.BIG.toBitString(iter.getFlags(), 8) + "\n";
        }
        return str;
    }

    public static Graph shuffle( Graph g, Graph sortedGraph )
    {
        int len = g.getNodes();
        TIntList list = new TIntArrayList(len, -1);
        list.fill(0, len, -1);
        for (int i = 0; i < len; i++)
        {
            list.set(i, i);
        }
        list.shuffle(new Random());
        return createSortedGraph(g, sortedGraph, list);
    }

    /**
     * Sorts the graph according to depth-first search traversal. Other traversals have either no
     * significant difference (bfs) for querying or are worse (z-curve).
     */
    public static Graph sortDFS( Graph g, Graph sortedGraph )
    {
        final TIntList list = new TIntArrayList(g.getNodes(), -1);
        int nodes = g.getNodes();
        list.fill(0, nodes, -1);
        final GHBitSetImpl bitset = new GHBitSetImpl(nodes);
        final AtomicInteger ref = new AtomicInteger(-1);
        EdgeExplorer explorer = g.createEdgeExplorer();
        for (int startNode = 0; startNode >= 0 && startNode < nodes;
                startNode = bitset.nextClear(startNode + 1))
        {
            new DepthFirstSearch()
            {
                @Override
                protected GHBitSet createBitSet()
                {
                    return bitset;
                }

                @Override
                protected boolean goFurther( int nodeId )
                {
                    list.set(nodeId, ref.incrementAndGet());
                    return super.goFurther(nodeId);
                }
            }.start(explorer, startNode);
        }
        return createSortedGraph(g, sortedGraph, list);
    }

    static Graph createSortedGraph( Graph fromGraph, Graph toSortedGraph, final TIntList oldToNewNodeList )
    {
        AllEdgesIterator eIter = fromGraph.getAllEdges();
        while (eIter.next())
        {
            int base = eIter.getBaseNode();
            int newBaseIndex = oldToNewNodeList.get(base);
            int adj = eIter.getAdjNode();
            int newAdjIndex = oldToNewNodeList.get(adj);

            // ignore empty entries
            if (newBaseIndex < 0 || newAdjIndex < 0)
                continue;

            eIter.copyPropertiesTo(toSortedGraph.edge(newBaseIndex, newAdjIndex));
        }

        int nodes = fromGraph.getNodes();
        NodeAccess na = fromGraph.getNodeAccess();
        NodeAccess sna = toSortedGraph.getNodeAccess();
        for (int old = 0; old < nodes; old++)
        {
            int newIndex = oldToNewNodeList.get(old);
            if (sna.is3D())
                sna.setNode(newIndex, na.getLatitude(old), na.getLongitude(old), na.getElevation(old));
            else
                sna.setNode(newIndex, na.getLatitude(old), na.getLongitude(old));
        }
        return toSortedGraph;
    }

    /**
     * @return the specified toGraph which is now filled with data from fromGraph
     */
    // TODO very similar to createSortedGraph -> use a 'int map(int)' interface
    public static Graph copyTo( Graph fromGraph, Graph toGraph )
    {
        AllEdgesIterator eIter = fromGraph.getAllEdges();
        while (eIter.next())
        {
            int base = eIter.getBaseNode();
            int adj = eIter.getAdjNode();
            eIter.copyPropertiesTo(toGraph.edge(base, adj));
        }

        NodeAccess fna = fromGraph.getNodeAccess();
        NodeAccess tna = toGraph.getNodeAccess();
        int nodes = fromGraph.getNodes();
        for (int node = 0; node < nodes; node++)
        {
            if (tna.is3D())
                tna.setNode(node, fna.getLatitude(node), fna.getLongitude(node), fna.getElevation(node));
            else
                tna.setNode(node, fna.getLatitude(node), fna.getLongitude(node));
        }
        return toGraph;
    }

    static Directory guessDirectory( GraphStorage store )
    {
        String location = store.getDirectory().getLocation();
        Directory outdir;
        if (store.getDirectory() instanceof MMapDirectory)
        {
            throw new IllegalStateException("not supported yet: mmap will overwrite existing storage at the same location");
        } else
        {
            boolean isStoring = ((GHDirectory) store.getDirectory()).isStoring();
            outdir = new RAMDirectory(location, isStoring);
        }
        return outdir;
    }

    static GraphStorage guessStorage( Graph g, Directory outdir, EncodingManager encodingManager )
    {
        GraphStorage store;
        boolean is3D = g.getNodeAccess().is3D();
        if (g instanceof LevelGraphStorage)
            store = new LevelGraphStorage(outdir, encodingManager, is3D);
        else
            store = new GraphHopperStorage(outdir, encodingManager, is3D);

        return store;
    }

    /**
     * Create a new storage from the specified one without copying the data.
     */
    public static GraphStorage newStorage( GraphStorage store )
    {
        return guessStorage(store, guessDirectory(store), store.getEncodingManager()).create(store.getNodes());
    }

    /**
     * @return the graph outGraph
     */
    public static Graph clone( Graph g, GraphStorage outGraph )
    {
        return g.copyTo(outGraph.create(g.getNodes()));
    }

    public static int getAdjNode( Graph g, int edge, int adjNode )
    {
        if (EdgeIterator.Edge.isValid(edge))
        {
            EdgeIteratorState iterTo = g.getEdgeProps(edge, adjNode);
            return iterTo.getAdjNode();
        }
        return adjNode;
    }

    public static class DisabledEdgeIterator implements EdgeSkipIterator
    {
        @Override
        public EdgeIterator detach( boolean reverse )
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public boolean isShortcut()
        {
            return false;
        }

        @Override
        public int getSkippedEdge1()
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public int getSkippedEdge2()
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public void setSkippedEdges( int edge1, int edge2 )
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public EdgeIteratorState setDistance( double dist )
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public EdgeIteratorState setFlags( long flags )
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public boolean next()
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public int getEdge()
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public int getBaseNode()
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public int getAdjNode()
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public double getDistance()
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public long getFlags()
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public PointList fetchWayGeometry( int type )
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public EdgeIteratorState setWayGeometry( PointList list )
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public String getName()
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public EdgeIteratorState setName( String name )
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public int getAdditionalField()
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public EdgeIteratorState setAdditionalField( int value )
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public EdgeIteratorState copyPropertiesTo( EdgeIteratorState edge )
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public double getWeight()
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }

        @Override
        public EdgeSkipIterState setWeight( double weight )
        {
            throw new UnsupportedOperationException("Not supported. Edge is empty.");
        }
    };

    /**
     * @return the <b>first</b> edge containing the specified nodes base and adj. Returns null if
     * not found.
     */
    public static EdgeIteratorState getEdge( Graph graph, int base, int adj )
    {
        EdgeIterator iter = graph.createEdgeExplorer().setBaseNode(base);
        while (iter.next())
        {
            if (iter.getAdjNode() == adj)
                return iter;
        }
        return null;
    }

    /**
     * Creates unique positive number for specified edgeId taking into account the direction defined
     * by nodeA, nodeB and reverse.
     */
    public static int createEdgeKey( int nodeA, int nodeB, int edgeId, boolean reverse )
    {
        edgeId = edgeId << 1;
        if (reverse)
            return (nodeA > nodeB) ? edgeId : edgeId + 1;
        return (nodeA > nodeB) ? edgeId + 1 : edgeId;
    }

    /**
     * Returns if the specified edgeKeys (created by createEdgeKey) are identical regardless of the
     * direction.
     */
    public static boolean isSameEdgeKeys( int edgeKey1, int edgeKey2 )
    {
        return edgeKey1 / 2 == edgeKey2 / 2;
    }

    /**
     * Returns the edgeKey of the opposite direction
     */
    public static int reverseEdgeKey( int edgeKey )
    {
        return edgeKey % 2 == 0 ? edgeKey + 1 : edgeKey - 1;
    }
}


File: core/src/test/java/com/graphhopper/GraphHopperAPITest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper;

import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.storage.GraphStorage;
import com.graphhopper.storage.GraphBuilder;
import com.graphhopper.storage.NodeAccess;
import org.junit.Test;

import static org.junit.Assert.*;

/**
 * @author Peter Karich
 */
public class GraphHopperAPITest
{
    final EncodingManager encodingManager = new EncodingManager("CAR");

    @Test
    public void testLoad()
    {
        GraphStorage graph = new GraphBuilder(encodingManager).create();
        NodeAccess na = graph.getNodeAccess();
        na.setNode(0, 42, 10);
        na.setNode(1, 42.1, 10.1);
        na.setNode(2, 42.1, 10.2);
        na.setNode(3, 42, 10.4);
        na.setNode(4, 41.9, 10.2);

        graph.edge(0, 1, 10, true);
        graph.edge(1, 2, 10, false);
        graph.edge(2, 3, 10, true);
        graph.edge(0, 4, 40, true);
        graph.edge(4, 3, 40, true);

        GraphHopper instance = new GraphHopper().
                setStoreOnFlush(false).
                setEncodingManager(encodingManager).
                setCHEnable(false).
                loadGraph(graph);
        GHResponse rsp = instance.route(new GHRequest(42, 10.4, 42, 10));
        assertFalse(rsp.hasErrors());
        assertEquals(80, rsp.getDistance(), 1e-6);
        assertEquals(42, rsp.getPoints().getLatitude(0), 1e-5);
        assertEquals(10.4, rsp.getPoints().getLongitude(0), 1e-5);
        assertEquals(41.9, rsp.getPoints().getLatitude(1), 1e-5);
        assertEquals(10.2, rsp.getPoints().getLongitude(1), 1e-5);
        assertEquals(3, rsp.getPoints().getSize());
        instance.close();
    }

    @Test
    public void testDisconnected179()
    {
        GraphStorage graph = new GraphBuilder(encodingManager).create();
        NodeAccess na = graph.getNodeAccess();
        na.setNode(0, 42, 10);
        na.setNode(1, 42.1, 10.1);
        na.setNode(2, 42.1, 10.2);
        na.setNode(3, 42, 10.4);

        graph.edge(0, 1, 10, true);
        graph.edge(2, 3, 10, true);

        GraphHopper instance = new GraphHopper().
                setStoreOnFlush(false).
                setEncodingManager(encodingManager).
                setCHEnable(false).
                loadGraph(graph);
        GHResponse rsp = instance.route(new GHRequest(42, 10, 42, 10.4));
        assertTrue(rsp.hasErrors());

        try
        {
            rsp.getPoints();
            assertTrue(false);
        } catch (Exception ex)
        {
        }

        instance.close();
    }

    @Test
    public void testNoLoad()
    {
        GraphHopper instance = new GraphHopper().
                setStoreOnFlush(false).
                setEncodingManager(encodingManager).
                setCHEnable(false);
        try
        {
            instance.route(new GHRequest(42, 10.4, 42, 10));
            assertTrue(false);
        } catch (Exception ex)
        {
            assertTrue(ex.getMessage(), ex.getMessage().startsWith("Call load or importOrLoad before routing"));
        }

        instance = new GraphHopper().setEncodingManager(encodingManager);
        try
        {
            instance.route(new GHRequest(42, 10.4, 42, 10));
            assertTrue(false);
        } catch (Exception ex)
        {
            assertTrue(ex.getMessage(), ex.getMessage().startsWith("Call load or importOrLoad before routing"));
        }
    }
}


File: core/src/test/java/com/graphhopper/GraphHopperTest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 *
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper;

import com.graphhopper.reader.DataReader;
import com.graphhopper.routing.AlgorithmOptions;
import com.graphhopper.routing.util.EdgeFilter;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.storage.index.QueryResult;
import com.graphhopper.util.CmdArgs;
import com.graphhopper.util.Helper;
import com.graphhopper.util.Instruction;
import com.graphhopper.util.shapes.GHPoint;

import java.io.File;
import java.io.IOException;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

import org.junit.After;
import org.junit.Test;

import static org.junit.Assert.*;

import org.junit.Before;

/**
 * @author Peter Karich
 */
public class GraphHopperTest
{
    private static final String ghLoc = "./target/tmp/ghosm";
    private static final String testOsm = "./src/test/resources/com/graphhopper/reader/test-osm.xml";
    private static final String testOsm3 = "./src/test/resources/com/graphhopper/reader/test-osm3.xml";
    private GraphHopper instance;

    @Before
    public void setUp()
    {
        Helper.removeDir(new File(ghLoc));
    }

    @After
    public void tearDown()
    {
        if (instance != null)
            instance.close();
        Helper.removeDir(new File(ghLoc));
    }

    @Test
    public void testLoadOSM()
    {
        GraphHopper closableInstance = new GraphHopper().setStoreOnFlush(true).
                setEncodingManager(new EncodingManager("CAR")).
                setGraphHopperLocation(ghLoc).
                setOSMFile(testOsm);
        closableInstance.importOrLoad();
        GHResponse rsp = closableInstance.route(new GHRequest(51.2492152, 9.4317166, 51.2, 9.4));
        assertFalse(rsp.hasErrors());
        assertEquals(3, rsp.getPoints().getSize());

        closableInstance.close();

        // no encoding manager necessary
        closableInstance = new GraphHopper().setStoreOnFlush(true);
        assertTrue(closableInstance.load(ghLoc));
        rsp = closableInstance.route(new GHRequest(51.2492152, 9.4317166, 51.2, 9.4));
        assertFalse(rsp.hasErrors());
        assertEquals(3, rsp.getPoints().getSize());

        closableInstance.close();
        try
        {
            rsp = closableInstance.route(new GHRequest(51.2492152, 9.4317166, 51.2, 9.4));
            assertTrue(false);
        } catch (Exception ex)
        {
            assertEquals("You need to create a new GraphHopper instance as it is already closed", ex.getMessage());
        }

        try
        {
            QueryResult qr = closableInstance.getLocationIndex().findClosest(51.2492152, 9.4317166, EdgeFilter.ALL_EDGES);
            assertTrue(false);
        } catch (Exception ex)
        {
            assertEquals("You need to create a new LocationIndex instance as it is already closed", ex.getMessage());
        }
    }

    @Test
    public void testLoadOSMNoCH()
    {
        GraphHopper gh = new GraphHopper().setStoreOnFlush(true).
                setCHEnable(false).
                setEncodingManager(new EncodingManager("CAR")).
                setGraphHopperLocation(ghLoc).
                setOSMFile(testOsm);
        gh.importOrLoad();
        GHResponse rsp = gh.route(new GHRequest(51.2492152, 9.4317166, 51.2, 9.4));
        assertFalse(rsp.hasErrors());
        assertEquals(3, rsp.getPoints().getSize());

        gh.close();
        gh = new GraphHopper().setStoreOnFlush(true).
                setCHEnable(false).
                setEncodingManager(new EncodingManager("CAR"));
        assertTrue(gh.load(ghLoc));
        rsp = gh.route(new GHRequest(51.2492152, 9.4317166, 51.2, 9.4));
        assertFalse(rsp.hasErrors());
        assertEquals(3, rsp.getPoints().getSize());

        gh.close();
    }

    @Test
    public void testAllowMultipleReadingInstances()
    {
        GraphHopper instance1 = new GraphHopper().setStoreOnFlush(true).
                setEncodingManager(new EncodingManager("CAR")).
                setGraphHopperLocation(ghLoc).
                setOSMFile(testOsm);
        instance1.importOrLoad();

        GraphHopper instance2 = new GraphHopper().setStoreOnFlush(true).
                setEncodingManager(new EncodingManager("CAR")).
                setOSMFile(testOsm);
        instance2.load(ghLoc);

        GraphHopper instance3 = new GraphHopper().setStoreOnFlush(true).
                setEncodingManager(new EncodingManager("CAR")).
                setOSMFile(testOsm);
        instance3.load(ghLoc);

        instance1.close();
        instance2.close();
        instance3.close();
    }

    @Test
    public void testDoNotAllowWritingAndLoadingAtTheSameTime() throws Exception
    {
        final CountDownLatch latch1 = new CountDownLatch(1);
        final CountDownLatch latch2 = new CountDownLatch(1);
        final GraphHopper instance1 = new GraphHopper()
        {
            @Override
            protected DataReader importData() throws IOException
            {
                try
                {
                    latch2.countDown();
                    latch1.await(3, TimeUnit.SECONDS);
                } catch (InterruptedException ex)
                {
                }
                return super.importData();
            }
        }.setStoreOnFlush(true).
                setEncodingManager(new EncodingManager("CAR")).
                setGraphHopperLocation(ghLoc).
                setOSMFile(testOsm);
        final AtomicReference<Exception> ar = new AtomicReference<Exception>();
        Thread thread = new Thread()
        {
            @Override
            public void run()
            {
                try
                {
                    instance1.importOrLoad();
                } catch (Exception ex)
                {
                    ar.set(ex);
                }
            }
        };
        thread.start();

        GraphHopper instance2 = new GraphHopper().setStoreOnFlush(true).
                setEncodingManager(new EncodingManager("CAR")).
                setOSMFile(testOsm);
        try
        {
            // let thread reach the CountDownLatch
            latch2.await(3, TimeUnit.SECONDS);
            // now importOrLoad should have create a lock which this load call does not like
            instance2.load(ghLoc);
            assertTrue(false);
        } catch (RuntimeException ex)
        {
            assertNotNull(ex);
            assertTrue(ex.getMessage(), ex.getMessage().startsWith("To avoid reading partial data"));
        } finally
        {
            instance2.close();
            latch1.countDown();
            // make sure the import process wasn't interrupted and no other error happened
            thread.join();
        }

        if (ar.get() != null)
            assertNull(ar.get().getMessage(), ar.get());
        instance1.close();
    }

    @Test
    public void testPrepare()
    {
        instance = new GraphHopper().
                setStoreOnFlush(false).
                setEncodingManager(new EncodingManager("CAR")).
                setCHWeighting("shortest").
                setGraphHopperLocation(ghLoc).
                setOSMFile(testOsm);
        instance.importOrLoad();
        GHResponse rsp = instance.route(new GHRequest(51.2492152, 9.4317166, 51.2, 9.4).
                setAlgorithm(AlgorithmOptions.DIJKSTRA_BI));
        assertFalse(rsp.hasErrors());
        assertEquals(Helper.createPointList(51.249215, 9.431716, 52.0, 9.0, 51.2, 9.4), rsp.getPoints());
        assertEquals(3, rsp.getPoints().getSize());
    }

    @Test
    public void testSortedGraph_noCH()
    {
        instance = new GraphHopper().setStoreOnFlush(false).
                setSortGraph(true).
                setEncodingManager(new EncodingManager("CAR")).
                setCHEnable(false).
                setGraphHopperLocation(ghLoc).
                setOSMFile(testOsm);
        instance.importOrLoad();
        GHResponse rsp = instance.route(new GHRequest(51.2492152, 9.4317166, 51.2, 9.4).
                setAlgorithm(AlgorithmOptions.DIJKSTRA_BI));
        assertFalse(rsp.hasErrors());
        assertEquals(3, rsp.getPoints().getSize());
        assertEquals(new GHPoint(51.24921503475044, 9.431716451757769), rsp.getPoints().toGHPoint(0));
        assertEquals(new GHPoint(52.0, 9.0), rsp.getPoints().toGHPoint(1));
        assertEquals(new GHPoint(51.199999850988384, 9.39999970197677), rsp.getPoints().toGHPoint(2));

        GHRequest req = new GHRequest(51.2492152, 9.4317166, 51.2, 9.4);
        boolean old = instance.enableInstructions;
        req.getHints().put("instructions", true);
        instance.route(req);
        assertEquals(old, instance.enableInstructions);

        req.getHints().put("instructions", false);
        instance.route(req);
        assertEquals("route method should not change instance field", old, instance.enableInstructions);
    }

    @Test
    public void testFootAndCar()
    {
        // now all ways are imported
        instance = new GraphHopper().setStoreOnFlush(false).
                setEncodingManager(new EncodingManager("CAR,FOOT")).
                setCHEnable(false).
                setGraphHopperLocation(ghLoc).
                setOSMFile(testOsm3);
        instance.importOrLoad();

        assertEquals(5, instance.getGraph().getNodes());
        assertEquals(8, instance.getGraph().getAllEdges().getCount());

        // A to D
        GHResponse rsp = instance.route(new GHRequest(11.1, 50, 11.3, 51).setVehicle(EncodingManager.CAR));
        assertFalse(rsp.hasErrors());
        assertFalse(rsp.hasErrors());
        assertEquals(3, rsp.getPoints().getSize());
        // => found A and D
        assertEquals(50, rsp.getPoints().getLongitude(0), 1e-3);
        assertEquals(11.1, rsp.getPoints().getLatitude(0), 1e-3);
        assertEquals(51, rsp.getPoints().getLongitude(2), 1e-3);
        assertEquals(11.3, rsp.getPoints().getLatitude(2), 1e-3);

        // A to D not allowed for foot. But the location index will choose a node close to D accessible to FOOT        
        rsp = instance.route(new GHRequest(11.1, 50, 11.3, 51).setVehicle(EncodingManager.FOOT));
        assertFalse(rsp.hasErrors());
        assertEquals(2, rsp.getPoints().getSize());
        // => found a point on edge A-B        
        assertEquals(11.680, rsp.getPoints().getLatitude(1), 1e-3);
        assertEquals(50.644, rsp.getPoints().getLongitude(1), 1e-3);

        // A to E only for foot
        rsp = instance.route(new GHRequest(11.1, 50, 10, 51).setVehicle(EncodingManager.FOOT));
        assertFalse(rsp.hasErrors());
        assertEquals(2, rsp.getPoints().size());

        // A D E for car
        rsp = instance.route(new GHRequest(11.1, 50, 10, 51).setVehicle(EncodingManager.CAR));
        assertFalse(rsp.hasErrors());
        assertEquals(3, rsp.getPoints().getSize());
    }

    @Test
    public void testFailsForWrongConfig() throws IOException
    {
        instance = new GraphHopper().init(
                new CmdArgs().
                        put("osmreader.osm", testOsm3).
                        put("osmreader.dataaccess", "RAM").
                        put("graph.flagEncoders", "FOOT,CAR").
                        put("prepare.chWeighting", "no")).
                setGraphHopperLocation(ghLoc);
        instance.importOrLoad();
        assertEquals(5, instance.getGraph().getNodes());
        instance.close();

        // different config (flagEncoder list)
        try
        {
            GraphHopper tmpGH = new GraphHopper().init(
                    new CmdArgs().
                            put("osmreader.osm", testOsm3).
                            put("osmreader.dataaccess", "RAM").
                            put("graph.flagEncoders", "FOOT").
                            put("prepare.chWeighting", "no")).
                    setOSMFile(testOsm3);
            tmpGH.load(ghLoc);
            assertTrue(false);
        } catch (Exception ex)
        {
        }

        // different order is no longer okay, see #350
        try
        {
            GraphHopper tmpGH = new GraphHopper().init(new CmdArgs().
                    put("osmreader.osm", testOsm3).
                    put("osmreader.dataaccess", "RAM").
                    put("prepare.chWeighting", "no").
                    put("graph.flagEncoders", "CAR,FOOT")).
                    setOSMFile(testOsm3);
            tmpGH.load(ghLoc);
            assertTrue(false);
        } catch (Exception ex)
        {
        }
    }

    @Test
    public void testNoNPE_ifLoadNotSuccessful()
    {
        // missing import of graph
        instance = new GraphHopper().
                setStoreOnFlush(true).
                setEncodingManager(new EncodingManager("CAR"));
        try
        {
            assertFalse(instance.load(ghLoc));
            instance.route(new GHRequest(10, 40, 12, 32));
            assertTrue(false);
        } catch (IllegalStateException ex)
        {
            assertEquals("Call load or importOrLoad before routing", ex.getMessage());
        }
    }

    @Test
    public void testFailsForMissingParameters() throws IOException
    {
        // missing load of graph
        instance = new GraphHopper();
        try
        {
            instance.setOSMFile(testOsm).importData();
            assertTrue(false);
        } catch (IllegalStateException ex)
        {
            assertEquals("Load graph before importing OSM data", ex.getMessage());
        }

        // missing graph location
        instance = new GraphHopper();
        try
        {
            instance.importOrLoad();
            assertTrue(false);
        } catch (IllegalStateException ex)
        {
            assertEquals("graphHopperLocation is not specified. call init before", ex.getMessage());
        }

        // missing OSM file to import
        instance = new GraphHopper().
                setStoreOnFlush(true).
                setEncodingManager(new EncodingManager("CAR")).
                setGraphHopperLocation(ghLoc);
        try
        {
            instance.importOrLoad();
            assertTrue(false);
        } catch (IllegalStateException ex)
        {
            assertEquals("Couldn't load from existing folder: " + ghLoc
                    + " but also cannot import from OSM file as it wasn't specified!", ex.getMessage());
        }

        // missing encoding manager          
        instance = new GraphHopper().
                setStoreOnFlush(true).
                setGraphHopperLocation(ghLoc).
                setOSMFile(testOsm3);
        try
        {
            instance.importOrLoad();
            assertTrue(false);
        } catch (IllegalStateException ex)
        {
            assertTrue(ex.getMessage(), ex.getMessage().startsWith("Cannot load properties to fetch EncodingManager"));
        }

        // Import is possible even if no storeOnFlush is specified BUT here we miss the OSM file
        instance = new GraphHopper().
                setStoreOnFlush(false).
                setEncodingManager(new EncodingManager("CAR")).
                setGraphHopperLocation(ghLoc);
        try
        {
            instance.importOrLoad();
            assertTrue(false);
        } catch (Exception ex)
        {
            assertEquals("Couldn't load from existing folder: " + ghLoc
                    + " but also cannot import from OSM file as it wasn't specified!", ex.getMessage());
        }
    }

    @Test
    public void testFootOnly()
    {
        // now only footable ways are imported => no A D C and B D E => the other both ways have pillar nodes!
        instance = new GraphHopper().setStoreOnFlush(false).
                setEncodingManager(new EncodingManager("FOOT")).
                setGraphHopperLocation(ghLoc).
                setOSMFile(testOsm3);
        instance.importOrLoad();

        assertEquals(2, instance.getGraph().getNodes());
        assertEquals(2, instance.getGraph().getAllEdges().getCount());

        // A to E only for foot
        GHResponse res = instance.route(new GHRequest(11.1, 50, 11.2, 52).setVehicle(EncodingManager.FOOT));
        assertFalse(res.hasErrors());
        assertEquals(3, res.getPoints().getSize());
    }

    @Test
    public void testPrepareOnly()
    {
        instance = new GraphHopper().setStoreOnFlush(true).
                setCHWeighting("shortest").
                setEncodingManager(new EncodingManager("FOOT")).
                setDoPrepare(false).
                setGraphHopperLocation(ghLoc).
                setOSMFile(testOsm3);
        instance.importOrLoad();
        instance.close();

        instance = new GraphHopper().setStoreOnFlush(true).
                setCHWeighting("shortest").
                setGraphHopperLocation(ghLoc).
                setOSMFile(testOsm3);

        // wrong encoding manager
        instance.setEncodingManager(new EncodingManager("CAR"));
        try
        {
            instance.load(ghLoc);
            assertTrue(false);
        } catch (IllegalStateException ex)
        {
            assertTrue(ex.getMessage(), ex.getMessage().startsWith("Encoding does not match:"));
        }

        // use the encoding manager from the graph
        instance = new GraphHopper().setStoreOnFlush(true).
                setEncodingManager(new EncodingManager("FOOT")).
                setCHWeighting("shortest").
                setGraphHopperLocation(ghLoc).
                setOSMFile(testOsm3);
        instance.load(ghLoc);
    }

    @Test
    public void testVia()
    {
        instance = new GraphHopper().setStoreOnFlush(true).
                init(new CmdArgs().
                        put("osmreader.osm", testOsm3).
                        put("prepare.minNetworkSize", "1").
                        put("graph.flagEncoders", "CAR")).
                setGraphHopperLocation(ghLoc);
        instance.importOrLoad();

        // A -> B -> C
        GHPoint first = new GHPoint(11.1, 50);
        GHPoint second = new GHPoint(12, 51);
        GHPoint third = new GHPoint(11.2, 51.9);
        GHResponse rsp12 = instance.route(new GHRequest().addPoint(first).addPoint(second));
        assertFalse("should find 1->2", rsp12.hasErrors());
        assertEquals(147930.5, rsp12.getDistance(), .1);
        GHResponse rsp23 = instance.route(new GHRequest().addPoint(second).addPoint(third));
        assertFalse("should find 2->3", rsp23.hasErrors());
        assertEquals(176608.9, rsp23.getDistance(), .1);

        GHResponse rsp = instance.route(new GHRequest().addPoint(first).addPoint(second).addPoint(third));

        assertFalse(rsp.hasErrors());
        assertFalse("should find 1->2->3", rsp.hasErrors());
        assertEquals(rsp12.getDistance() + rsp23.getDistance(), rsp.getDistance(), 1e-6);
        assertEquals(5, rsp.getPoints().getSize());
        assertEquals(5, rsp.getInstructions().size());
        assertEquals(Instruction.REACHED_VIA, rsp.getInstructions().get(1).getSign());
    }
}


File: core/src/test/java/com/graphhopper/reader/OSMReaderTest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.reader;

import static org.junit.Assert.*;

import gnu.trove.list.TLongList;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.net.URISyntaxException;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import com.graphhopper.GraphHopper;
import com.graphhopper.reader.dem.ElevationProvider;
import com.graphhopper.reader.dem.SRTMProvider;
import com.graphhopper.routing.util.*;
import com.graphhopper.storage.*;
import com.graphhopper.util.EdgeExplorer;
import com.graphhopper.util.EdgeIterator;
import com.graphhopper.util.EdgeIteratorState;
import com.graphhopper.util.GHUtility;
import com.graphhopper.util.Helper;
import com.graphhopper.util.shapes.GHPoint;

import java.util.*;

/**
 * Tests the OSMReader with the normal helper initialized.
 * <p/>
 * @author Peter Karich
 */
public class OSMReaderTest
{
    private final String file1 = "test-osm.xml";
    private final String file2 = "test-osm2.xml";
    private final String file3 = "test-osm3.xml";
    private final String file4 = "test-osm4.xml";
    private final String fileNegIds = "test-osm-negative-ids.xml";
    private final String fileBarriers = "test-barriers.xml";
    private final String fileTurnRestrictions = "test-restrictions.xml";
    private final String dir = "./target/tmp/test-db";
    private CarFlagEncoder carEncoder;
    private BikeFlagEncoder bikeEncoder;
    private FlagEncoder footEncoder;
    private EdgeExplorer carOutExplorer;
    private EdgeExplorer carAllExplorer;

    @Before
    public void setUp()
    {
        new File(dir).mkdirs();
    }

    @After
    public void tearDown()
    {
        Helper.removeDir(new File(dir));
    }

    GraphStorage newGraph( String directory, EncodingManager encodingManager, boolean is3D, boolean turnRestrictionsImport )
    {
        return new GraphHopperStorage(new RAMDirectory(directory, false), encodingManager,
                is3D, turnRestrictionsImport ? new TurnCostExtension() : new GraphExtension.NoExtendedStorage());
    }

    class GraphHopperTest extends GraphHopper
    {
        public GraphHopperTest( String osmFile )
        {
            this(osmFile, false);
        }

        public GraphHopperTest( String osmFile, boolean turnCosts )
        {
            setStoreOnFlush(false);
            setOSMFile(osmFile);
            setGraphHopperLocation(dir);
            setEncodingManager(new EncodingManager("CAR,FOOT"));
            setCHEnable(false);

            if (turnCosts)
            {
                carEncoder = new CarFlagEncoder(5, 5, 3);
                bikeEncoder = new BikeFlagEncoder(4, 2, 3);
            } else
            {
                carEncoder = new CarFlagEncoder();
                bikeEncoder = new BikeFlagEncoder();
            }

            footEncoder = new FootFlagEncoder();

            setEncodingManager(new EncodingManager(footEncoder, carEncoder, bikeEncoder));
        }

        @Override
        protected DataReader createReader( GraphStorage tmpGraph )
        {
            return initOSMReader(new OSMReader(tmpGraph));
        }

        @Override
        protected DataReader importData() throws IOException
        {
            GraphStorage tmpGraph = newGraph(dir, getEncodingManager(), hasElevation(), getEncodingManager().needsTurnCostsSupport());
            setGraph(tmpGraph);

            DataReader osmReader = createReader(tmpGraph);
            try
            {
                ((OSMReader) osmReader).setOSMFile(new File(getClass().getResource(getOSMFile()).toURI()));
            } catch (URISyntaxException e)
            {
                throw new RuntimeException(e);
            }
            osmReader.readGraph();
            carOutExplorer = getGraph().createEdgeExplorer(new DefaultEdgeFilter(carEncoder, false, true));
            carAllExplorer = getGraph().createEdgeExplorer(new DefaultEdgeFilter(carEncoder, true, true));
            return osmReader;
        }
    }

    InputStream getResource( String file )
    {
        return getClass().getResourceAsStream(file);
    }

    @Test
    public void testMain()
    {
        GraphHopper hopper = new GraphHopperTest(file1).importOrLoad();
        GraphStorage graph = (GraphStorage) hopper.getGraph();

        assertNotNull(graph.getProperties().get("osmreader.import.date"));
        assertNotEquals("", graph.getProperties().get("osmreader.import.date"));

        assertEquals(4, graph.getNodes());
        int n20 = AbstractGraphStorageTester.getIdOf(graph, 52);
        int n10 = AbstractGraphStorageTester.getIdOf(graph, 51.2492152);
        int n30 = AbstractGraphStorageTester.getIdOf(graph, 51.2);
        int n50 = AbstractGraphStorageTester.getIdOf(graph, 49);
        assertEquals(GHUtility.asSet(n20), GHUtility.getNeighbors(carOutExplorer.setBaseNode(n10)));
        assertEquals(3, GHUtility.count(carOutExplorer.setBaseNode(n20)));
        assertEquals(GHUtility.asSet(n20), GHUtility.getNeighbors(carOutExplorer.setBaseNode(n30)));

        EdgeIterator iter = carOutExplorer.setBaseNode(n20);
        assertTrue(iter.next());
        assertEquals("street 123, B 122", iter.getName());
        assertEquals(n50, iter.getAdjNode());
        AbstractGraphStorageTester.assertPList(Helper.createPointList(51.25, 9.43), iter.fetchWayGeometry(0));
        FlagEncoder flags = carEncoder;
        assertTrue(flags.isForward(iter.getFlags()));
        assertTrue(flags.isBackward(iter.getFlags()));

        assertTrue(iter.next());
        assertEquals("route 666", iter.getName());
        assertEquals(n30, iter.getAdjNode());
        assertEquals(93147, iter.getDistance(), 1);

        assertTrue(iter.next());
        assertEquals("route 666", iter.getName());
        assertEquals(n10, iter.getAdjNode());
        assertEquals(88643, iter.getDistance(), 1);

        assertTrue(flags.isForward(iter.getFlags()));
        assertTrue(flags.isBackward(iter.getFlags()));
        assertFalse(iter.next());

        // get third added location id=30
        iter = carOutExplorer.setBaseNode(n30);
        assertTrue(iter.next());
        assertEquals("route 666", iter.getName());
        assertEquals(n20, iter.getAdjNode());
        assertEquals(93146.888, iter.getDistance(), 1);

        NodeAccess na = graph.getNodeAccess();
        assertEquals(9.4, na.getLongitude(hopper.getLocationIndex().findID(51.2, 9.4)), 1e-3);
        assertEquals(10, na.getLongitude(hopper.getLocationIndex().findID(49, 10)), 1e-3);
        assertEquals(51.249, na.getLatitude(hopper.getLocationIndex().findID(51.2492152, 9.4317166)), 1e-3);

        // node 40 is on the way between 30 and 50 => 9.0
        assertEquals(9, na.getLongitude(hopper.getLocationIndex().findID(51.25, 9.43)), 1e-3);
    }

    @Test
    public void testSort()
    {
        GraphHopper hopper = new GraphHopperTest(file1).setSortGraph(true).importOrLoad();
        Graph graph = hopper.getGraph();
        NodeAccess na = graph.getNodeAccess();
        assertEquals(10, na.getLongitude(hopper.getLocationIndex().findID(49, 10)), 1e-3);
        assertEquals(51.249, na.getLatitude(hopper.getLocationIndex().findID(51.2492152, 9.4317166)), 1e-3);
    }

    @Test
    public void testWithBounds()
    {
        GraphHopper hopper = new GraphHopperTest(file1)
        {
            @Override
            protected DataReader createReader( GraphStorage tmpGraph )
            {
                return new OSMReader(tmpGraph)
                {
                    @Override
                    public boolean isInBounds( OSMNode node )
                    {
                        return node.getLat() > 49 && node.getLon() > 8;
                    }
                }.setEncodingManager(getEncodingManager());
            }
        };

        hopper.importOrLoad();

        Graph graph = hopper.getGraph();
        assertEquals(4, graph.getNodes());
        int n10 = AbstractGraphStorageTester.getIdOf(graph, 51.2492152);
        int n20 = AbstractGraphStorageTester.getIdOf(graph, 52);
        int n30 = AbstractGraphStorageTester.getIdOf(graph, 51.2);
        int n40 = AbstractGraphStorageTester.getIdOf(graph, 51.25);

        assertEquals(GHUtility.asSet(n20), GHUtility.getNeighbors(carOutExplorer.setBaseNode(n10)));
        assertEquals(3, GHUtility.count(carOutExplorer.setBaseNode(n20)));
        assertEquals(GHUtility.asSet(n20), GHUtility.getNeighbors(carOutExplorer.setBaseNode(n30)));

        EdgeIterator iter = carOutExplorer.setBaseNode(n20);
        assertTrue(iter.next());
        assertEquals(n40, iter.getAdjNode());
        AbstractGraphStorageTester.assertPList(Helper.createPointList(), iter.fetchWayGeometry(0));
        assertTrue(iter.next());
        assertEquals(n30, iter.getAdjNode());
        assertEquals(93146.888, iter.getDistance(), 1);
        assertTrue(iter.next());
        AbstractGraphStorageTester.assertPList(Helper.createPointList(), iter.fetchWayGeometry(0));
        assertEquals(n10, iter.getAdjNode());
        assertEquals(88643, iter.getDistance(), 1);

        // get third added location => 2
        iter = carOutExplorer.setBaseNode(n30);
        assertTrue(iter.next());
        assertEquals(n20, iter.getAdjNode());
        assertEquals(93146.888, iter.getDistance(), 1);
        assertFalse(iter.next());
    }

    @Test
    public void testOneWay()
    {
        GraphHopper hopper = new GraphHopperTest(file2).importOrLoad();
        Graph graph = hopper.getGraph();

        int n20 = AbstractGraphStorageTester.getIdOf(graph, 52.0);
        int n22 = AbstractGraphStorageTester.getIdOf(graph, 52.133);
        int n23 = AbstractGraphStorageTester.getIdOf(graph, 52.144);
        int n10 = AbstractGraphStorageTester.getIdOf(graph, 51.2492152);
        int n30 = AbstractGraphStorageTester.getIdOf(graph, 51.2);

        assertEquals(1, GHUtility.count(carOutExplorer.setBaseNode(n10)));
        assertEquals(2, GHUtility.count(carOutExplorer.setBaseNode(n20)));
        assertEquals(0, GHUtility.count(carOutExplorer.setBaseNode(n30)));

        EdgeIterator iter = carOutExplorer.setBaseNode(n20);
        assertTrue(iter.next());
        assertTrue(iter.next());
        assertEquals(n30, iter.getAdjNode());

        FlagEncoder encoder = carEncoder;
        iter = carAllExplorer.setBaseNode(n20);
        assertTrue(iter.next());
        assertEquals(n23, iter.getAdjNode());
        assertTrue(encoder.isForward(iter.getFlags()));
        assertFalse(encoder.isBackward(iter.getFlags()));

        assertTrue(iter.next());
        assertEquals(n22, iter.getAdjNode());
        assertFalse(encoder.isForward(iter.getFlags()));
        assertTrue(encoder.isBackward(iter.getFlags()));

        assertTrue(iter.next());
        assertFalse(encoder.isForward(iter.getFlags()));
        assertTrue(encoder.isBackward(iter.getFlags()));

        assertTrue(iter.next());
        assertEquals(n30, iter.getAdjNode());
        assertTrue(encoder.isForward(iter.getFlags()));
        assertFalse(encoder.isBackward(iter.getFlags()));

        assertTrue(iter.next());
        assertEquals(n10, iter.getAdjNode());
        assertFalse(encoder.isForward(iter.getFlags()));
        assertTrue(encoder.isBackward(iter.getFlags()));
    }

    @Test
    public void testFerry()
    {
        GraphHopper hopper = new GraphHopperTest(file2)
        {
            @Override
            public void cleanUp()
            {
            }
        }.importOrLoad();
        Graph graph = hopper.getGraph();

        int n40 = AbstractGraphStorageTester.getIdOf(graph, 54.0);
        int n50 = AbstractGraphStorageTester.getIdOf(graph, 55.0);
        assertEquals(GHUtility.asSet(n40), GHUtility.getNeighbors(carAllExplorer.setBaseNode(n50)));

        // no duration is given => slow speed only!
        int n80 = AbstractGraphStorageTester.getIdOf(graph, 54.1);
        EdgeIterator iter = carOutExplorer.setBaseNode(n80);
        iter.next();
        assertEquals(5, carEncoder.getSpeed(iter.getFlags()), 1e-1);

        // duration 01:10 is given => more precise speed calculation! 
        // ~111km (from 54.0,10.1 to 55.0,10.2) in duration=70 minutes => 95km/h => / 1.4 => 71km/h        
        iter = carOutExplorer.setBaseNode(n40);
        iter.next();
        assertEquals(70, carEncoder.getSpeed(iter.getFlags()), 1e-1);
    }

    @Test
    public void testMaxSpeed()
    {
        GraphHopper hopper = new GraphHopperTest(file2)
        {
            @Override
            public void cleanUp()
            {
            }
        }.importOrLoad();
        Graph graph = hopper.getGraph();

        int n60 = AbstractGraphStorageTester.getIdOf(graph, 56.0);
        EdgeIterator iter = carOutExplorer.setBaseNode(n60);
        iter.next();
        assertEquals(35, carEncoder.getSpeed(iter.getFlags()), 1e-1);
    }

    @Test
    public void testWayReferencesNotExistingAdjNode()
    {
        GraphHopper hopper = new GraphHopperTest(file4).importOrLoad();
        Graph graph = hopper.getGraph();

        assertEquals(2, graph.getNodes());
        int n10 = AbstractGraphStorageTester.getIdOf(graph, 51.2492152);
        int n30 = AbstractGraphStorageTester.getIdOf(graph, 51.2);

        assertEquals(GHUtility.asSet(n30), GHUtility.getNeighbors(carOutExplorer.setBaseNode(n10)));
    }

    @Test
    public void testFoot()
    {
        GraphHopper hopper = new GraphHopperTest(file3).importOrLoad();
        Graph graph = hopper.getGraph();

        int n10 = AbstractGraphStorageTester.getIdOf(graph, 11.1);
        int n20 = AbstractGraphStorageTester.getIdOf(graph, 12);
        int n30 = AbstractGraphStorageTester.getIdOf(graph, 11.2);
        int n40 = AbstractGraphStorageTester.getIdOf(graph, 11.3);
        int n50 = AbstractGraphStorageTester.getIdOf(graph, 10);

        assertEquals(GHUtility.asSet(n20, n40), GHUtility.getNeighbors(carAllExplorer.setBaseNode(n10)));
        assertEquals(GHUtility.asSet(), GHUtility.getNeighbors(carOutExplorer.setBaseNode(n30)));
        assertEquals(GHUtility.asSet(n10, n30, n40), GHUtility.getNeighbors(carAllExplorer.setBaseNode(n20)));
        assertEquals(GHUtility.asSet(n30, n40), GHUtility.getNeighbors(carOutExplorer.setBaseNode(n20)));

        EdgeExplorer footOutExplorer = graph.createEdgeExplorer(new DefaultEdgeFilter(footEncoder, false, true));
        assertEquals(GHUtility.asSet(n20, n50), GHUtility.getNeighbors(footOutExplorer.setBaseNode(n10)));
        assertEquals(GHUtility.asSet(n20, n50), GHUtility.getNeighbors(footOutExplorer.setBaseNode(n30)));
        assertEquals(GHUtility.asSet(n10, n30), GHUtility.getNeighbors(footOutExplorer.setBaseNode(n20)));
    }

    @Test
    public void testNegativeIds()
    {
        GraphHopper hopper = new GraphHopperTest(fileNegIds).importOrLoad();
        Graph graph = hopper.getGraph();
        assertEquals(4, graph.getNodes());
        int n20 = AbstractGraphStorageTester.getIdOf(graph, 52);
        int n10 = AbstractGraphStorageTester.getIdOf(graph, 51.2492152);
        int n30 = AbstractGraphStorageTester.getIdOf(graph, 51.2);
        assertEquals(GHUtility.asSet(n20), GHUtility.getNeighbors(carOutExplorer.setBaseNode(n10)));
        assertEquals(3, GHUtility.count(carOutExplorer.setBaseNode(n20)));
        assertEquals(GHUtility.asSet(n20), GHUtility.getNeighbors(carOutExplorer.setBaseNode(n30)));

        EdgeIterator iter = carOutExplorer.setBaseNode(n20);
        assertTrue(iter.next());

        assertTrue(iter.next());
        assertEquals(n30, iter.getAdjNode());
        assertEquals(93147, iter.getDistance(), 1);

        assertTrue(iter.next());
        assertEquals(n10, iter.getAdjNode());
        assertEquals(88643, iter.getDistance(), 1);
    }

    @Test
    public void testBarriers()
    {
        GraphHopper hopper = new GraphHopperTest(fileBarriers).importOrLoad();
        Graph graph = hopper.getGraph();
        assertEquals(8, graph.getNodes());

        int n10 = AbstractGraphStorageTester.getIdOf(graph, 51);
        int n20 = AbstractGraphStorageTester.getIdOf(graph, 52);
        int n30 = AbstractGraphStorageTester.getIdOf(graph, 53);
        int n50 = AbstractGraphStorageTester.getIdOf(graph, 55);

        // separate id
        int new20 = 4;
        assertNotEquals(n20, new20);
        NodeAccess na = graph.getNodeAccess();
        assertEquals(na.getLatitude(n20), na.getLatitude(new20), 1e-5);
        assertEquals(na.getLongitude(n20), na.getLongitude(new20), 1e-5);

        assertEquals(n20, hopper.getLocationIndex().findID(52, 9.4));

        assertEquals(GHUtility.asSet(n20, n30), GHUtility.getNeighbors(carOutExplorer.setBaseNode(n10)));
        assertEquals(GHUtility.asSet(new20, n10, n50), GHUtility.getNeighbors(carOutExplorer.setBaseNode(n30)));

        EdgeIterator iter = carOutExplorer.setBaseNode(n20);
        assertTrue(iter.next());
        assertEquals(n10, iter.getAdjNode());
        assertFalse(iter.next());

        iter = carOutExplorer.setBaseNode(new20);
        assertTrue(iter.next());
        assertEquals(n30, iter.getAdjNode());
        assertFalse(iter.next());
    }

    @Test
    public void testBarriersOnTowerNodes()
    {
        GraphHopper hopper = new GraphHopperTest(fileBarriers).importOrLoad();
        Graph graph = hopper.getGraph();
        assertEquals(8, graph.getNodes());

        int n60 = AbstractGraphStorageTester.getIdOf(graph, 56);
        int newId = 5;
        assertEquals(GHUtility.asSet(newId), GHUtility.getNeighbors(carOutExplorer.setBaseNode(n60)));

        EdgeIterator iter = carOutExplorer.setBaseNode(n60);
        assertTrue(iter.next());
        assertEquals(newId, iter.getAdjNode());
        assertFalse(iter.next());

        iter = carOutExplorer.setBaseNode(newId);
        assertTrue(iter.next());
        assertEquals(n60, iter.getAdjNode());
        assertFalse(iter.next());
    }

    @Test
    public void testRelation()
    {
        EncodingManager manager = new EncodingManager("bike");
        OSMReader reader = new OSMReader(new GraphHopperStorage(new RAMDirectory(), manager, false)).
                setEncodingManager(manager);
        OSMRelation osmRel = new OSMRelation(1);
        osmRel.getMembers().add(new OSMRelation.Member(OSMRelation.WAY, 1, ""));
        osmRel.getMembers().add(new OSMRelation.Member(OSMRelation.WAY, 2, ""));

        osmRel.setTag("route", "bicycle");
        osmRel.setTag("network", "lcn");
        reader.prepareWaysWithRelationInfo(osmRel);

        long flags = reader.getRelFlagsMap().get(1);
        assertTrue(flags != 0);

        // do NOT overwrite with UNCHANGED
        osmRel.setTag("network", "mtb");
        reader.prepareWaysWithRelationInfo(osmRel);
        long flags2 = reader.getRelFlagsMap().get(1);
        assertEquals(flags, flags2);

        // overwrite with outstanding
        osmRel.setTag("network", "ncn");
        reader.prepareWaysWithRelationInfo(osmRel);
        long flags3 = reader.getRelFlagsMap().get(1);
        assertTrue(flags != flags3);
    }

    @Test
    public void testTurnRestrictions()
    {
        GraphHopper hopper = new GraphHopperTest(fileTurnRestrictions, true).
                importOrLoad();
        GraphStorage graph = hopper.getGraph();
        assertEquals(15, graph.getNodes());
        assertTrue(graph.getExtension() instanceof TurnCostExtension);
        TurnCostExtension tcStorage = (TurnCostExtension) graph.getExtension();

        int n1 = AbstractGraphStorageTester.getIdOf(graph, 50, 10);
        int n2 = AbstractGraphStorageTester.getIdOf(graph, 52, 10);
        int n3 = AbstractGraphStorageTester.getIdOf(graph, 52, 11);
        int n4 = AbstractGraphStorageTester.getIdOf(graph, 52, 12);
        int n5 = AbstractGraphStorageTester.getIdOf(graph, 50, 12);
        int n6 = AbstractGraphStorageTester.getIdOf(graph, 51, 11);
        int n8 = AbstractGraphStorageTester.getIdOf(graph, 54, 11);

        int edge1_6 = GHUtility.getEdge(graph, n1, n6).getEdge();
        int edge2_3 = GHUtility.getEdge(graph, n2, n3).getEdge();
        int edge3_4 = GHUtility.getEdge(graph, n3, n4).getEdge();
        int edge3_8 = GHUtility.getEdge(graph, n3, n8).getEdge();

        int edge3_2 = GHUtility.getEdge(graph, n3, n2).getEdge();
        int edge4_3 = GHUtility.getEdge(graph, n4, n3).getEdge();
        int edge8_3 = GHUtility.getEdge(graph, n8, n3).getEdge();

        // (2-3)->(3-4) only_straight_on = (2-3)->(3-8) restricted
        // (4-3)->(3-8) no_right_turn = (4-3)->(3-8) restricted
        assertTrue(carEncoder.getTurnCost(tcStorage.getTurnCostFlags(edge2_3, n3, edge3_8)) > 0);
        assertTrue(carEncoder.getTurnCost(tcStorage.getTurnCostFlags(edge4_3, n3, edge3_8)) > 0);
        assertFalse(carEncoder.isTurnRestricted(tcStorage.getTurnCostFlags(edge2_3, n3, edge3_4)));
        assertFalse(carEncoder.isTurnRestricted(tcStorage.getTurnCostFlags(edge2_3, n3, edge3_2)));
        assertFalse(carEncoder.isTurnRestricted(tcStorage.getTurnCostFlags(edge2_3, n3, edge3_4)));
        assertFalse(carEncoder.isTurnRestricted(tcStorage.getTurnCostFlags(edge4_3, n3, edge3_2)));
        assertFalse(carEncoder.isTurnRestricted(tcStorage.getTurnCostFlags(edge8_3, n3, edge3_2)));

        // u-turn restriction for (6-1)->(1-6) but not for (1-6)->(6-1)
        assertTrue(carEncoder.getTurnCost(tcStorage.getTurnCostFlags(edge1_6, n1, edge1_6)) > 0);
        assertFalse(carEncoder.isTurnRestricted(tcStorage.getTurnCostFlags(edge1_6, n6, edge1_6)));

        int edge4_5 = GHUtility.getEdge(graph, n4, n5).getEdge();
        int edge5_6 = GHUtility.getEdge(graph, n5, n6).getEdge();
        int edge5_1 = GHUtility.getEdge(graph, n5, n1).getEdge();

        // (4-5)->(5-1) right_turn_only = (4-5)->(5-6) restricted 
        long costsFlags = tcStorage.getTurnCostFlags(edge4_5, n5, edge5_6);
        assertFalse(carEncoder.isTurnRestricted(costsFlags));
        assertTrue(carEncoder.getTurnCost(tcStorage.getTurnCostFlags(edge4_5, n5, edge5_1)) > 0);

        // for bike
        assertFalse(bikeEncoder.isTurnRestricted(costsFlags));

        int n10 = AbstractGraphStorageTester.getIdOf(graph, 40, 10);
        int n11 = AbstractGraphStorageTester.getIdOf(graph, 40, 11);
        int n14 = AbstractGraphStorageTester.getIdOf(graph, 39, 11);

        int edge10_11 = GHUtility.getEdge(graph, n10, n11).getEdge();
        int edge11_14 = GHUtility.getEdge(graph, n11, n14).getEdge();

        assertEquals(0, tcStorage.getTurnCostFlags(edge11_14, n11, edge10_11));

        costsFlags = tcStorage.getTurnCostFlags(edge10_11, n11, edge11_14);
        assertFalse(carEncoder.isTurnRestricted(costsFlags));
        assertTrue(bikeEncoder.isTurnRestricted(costsFlags));
    }

    @Test
    public void testEstimatedCenter()
    {
        final CarFlagEncoder encoder = new CarFlagEncoder()
        {
            private EncodedValue objectEncoder;

            @Override
            public int defineNodeBits( int index, int shift )
            {
                shift = super.defineNodeBits(index, shift);
                objectEncoder = new EncodedValue("oEnc", shift, 2, 1, 0, 3, true);
                return shift + 2;
            }

            @Override
            public long handleNodeTags( OSMNode node )
            {
                if (node.hasTag("test", "now"))
                    return -objectEncoder.setValue(0, 1);
                return 0;
            }
        };
        EncodingManager manager = new EncodingManager(encoder);
        GraphStorage graph = newGraph(dir, manager, false, false);
        final Map<Integer, Double> latMap = new HashMap<Integer, Double>();
        final Map<Integer, Double> lonMap = new HashMap<Integer, Double>();
        latMap.put(1, 1.1d);
        latMap.put(2, 1.2d);

        lonMap.put(1, 1.0d);
        lonMap.put(2, 1.0d);
        final AtomicInteger increased = new AtomicInteger(0);
        OSMReader osmreader = new OSMReader(graph)
        {
            // mock data access
            @Override
            double getTmpLatitude( int id )
            {
                return latMap.get(id);
            }

            @Override
            double getTmpLongitude( int id )
            {
                return lonMap.get(id);
            }

            @Override
            Collection<EdgeIteratorState> addOSMWay( TLongList osmNodeIds, long wayFlags, long osmId )
            {
                return Collections.emptyList();
            }
        };
        osmreader.setEncodingManager(manager);
        // save some node tags for first node
        OSMNode osmNode = new OSMNode(1, 1.1d, 1.0d);
        osmNode.setTag("test", "now");
        osmreader.getNodeFlagsMap().put(1, encoder.handleNodeTags(osmNode));

        OSMWay way = new OSMWay(1L);
        way.getNodes().add(1);
        way.getNodes().add(2);
        way.setTag("highway", "motorway");
        osmreader.getNodeMap().put(1, 1);
        osmreader.getNodeMap().put(2, 2);
        osmreader.processWay(way);

        GHPoint p = way.getTag("estimated_center", null);
        assertEquals(1.15, p.lat, 1e-3);
        assertEquals(1.0, p.lon, 1e-3);
        Double d = way.getTag("estimated_distance", null);
        assertEquals(11119.5, d, 1e-1);
    }

    @Test
    public void testReadEleFromCustomOSM()
    {
        GraphHopper hopper = new GraphHopperTest("custom-osm-ele.xml")
        {
            @Override
            protected DataReader createReader( GraphStorage tmpGraph )
            {
                return initOSMReader(new OSMReader(tmpGraph)
                {
                    @Override
                    protected double getElevation( OSMNode node )
                    {
                        return node.getEle();
                    }
                });
            }
        }.setElevation(true).importOrLoad();

        Graph graph = hopper.getGraph();
        int n20 = AbstractGraphStorageTester.getIdOf(graph, 52);
        int n50 = AbstractGraphStorageTester.getIdOf(graph, 49);

        EdgeIteratorState edge = GHUtility.getEdge(graph, n20, n50);
        assertEquals(Helper.createPointList3D(52, 9, -10, 51.25, 9.43, 100, 49, 10, -30), edge.fetchWayGeometry(3));
    }

    @Test
    public void testReadEleFromDataProvider()
    {
        GraphHopper hopper = new GraphHopperTest("test-osm5.xml");
        // get N10E046.hgt.zip
        ElevationProvider provider = new SRTMProvider();
        provider.setCacheDir(new File("./files"));
        hopper.setElevationProvider(provider);
        hopper.importOrLoad();

        Graph graph = hopper.getGraph();
        int n10 = AbstractGraphStorageTester.getIdOf(graph, 49.501);
        int n30 = AbstractGraphStorageTester.getIdOf(graph, 49.5011);
        int n50 = AbstractGraphStorageTester.getIdOf(graph, 49.5001);

        EdgeIteratorState edge = GHUtility.getEdge(graph, n50, n30);
        assertEquals(Helper.createPointList3D(49.5001, 11.501, 426, 49.5002, 11.5015, 441, 49.5011, 11.502, 410.0),
                edge.fetchWayGeometry(3));

        edge = GHUtility.getEdge(graph, n10, n50);
        assertEquals(Helper.createPointList3D(49.501, 11.5001, 383.0, 49.5001, 11.501, 426.0),
                edge.fetchWayGeometry(3));
    }

    /**
     * Tests the combination of different turn cost flags by different encoders.
     */
    @Test
    public void testTurnFlagCombination()
    {
        final OSMTurnRelation.TurnCostTableEntry turnCostEntry_car = new OSMTurnRelation.TurnCostTableEntry();
        final OSMTurnRelation.TurnCostTableEntry turnCostEntry_foot = new OSMTurnRelation.TurnCostTableEntry();
        final OSMTurnRelation.TurnCostTableEntry turnCostEntry_bike = new OSMTurnRelation.TurnCostTableEntry();

        CarFlagEncoder car = new CarFlagEncoder(5, 5, 24);
        FootFlagEncoder foot = new FootFlagEncoder();
        BikeFlagEncoder bike = new BikeFlagEncoder(4, 2, 24);
        EncodingManager manager = new EncodingManager(Arrays.asList(bike, foot, car), 4);

        OSMReader reader = new OSMReader(new GraphBuilder(manager).create())
        {
            @Override
            public Collection<OSMTurnRelation.TurnCostTableEntry> analyzeTurnRelation( FlagEncoder encoder,
                                                                                       OSMTurnRelation turnRelation )
            {
                // simulate by returning one turn cost entry directly
                if (encoder.toString().equalsIgnoreCase("car"))
                {

                    return Collections.singleton(turnCostEntry_car);
                } else if (encoder.toString().equalsIgnoreCase("foot"))
                {
                    return Collections.singleton(turnCostEntry_foot);
                } else if (encoder.toString().equalsIgnoreCase("bike"))
                {
                    return Collections.singleton(turnCostEntry_bike);
                } else
                {
                    throw new IllegalArgumentException("illegal encoder " + encoder.toString());
                }
            }
        }.setEncodingManager(manager);

        // turn cost entries for car and foot are for the same relations (same viaNode, edgeFrom and edgeTo), 
        // turn cost entry for bike is for another relation (different viaNode) 
        turnCostEntry_car.edgeFrom = 1;
        turnCostEntry_foot.edgeFrom = 1;
        turnCostEntry_bike.edgeFrom = 2;

        // calculating arbitrary flags using the encoders
        turnCostEntry_car.flags = car.getTurnFlags(true, 0);
        turnCostEntry_foot.flags = foot.getTurnFlags(true, 0);
        turnCostEntry_bike.flags = bike.getTurnFlags(false, 10);

        // we expect two different entries: the first one is a combination of turn flags of car and foot, 
        // since they provide the same relation, the other one is for bike only
        long assertFlag1 = turnCostEntry_car.flags | turnCostEntry_foot.flags;
        long assertFlag2 = turnCostEntry_bike.flags;

        // combine flags of all encoders
        Collection<OSMTurnRelation.TurnCostTableEntry> entries = reader.analyzeTurnRelation(null);

        // we expect two different turnCost entries
        assertEquals(2, entries.size());

        for (OSMTurnRelation.TurnCostTableEntry entry : entries)
        {
            if (entry.edgeFrom == 1)
            {
                // the first entry provides turn flags for car and foot only 
                assertEquals(assertFlag1, entry.flags);
                assertTrue(car.isTurnRestricted(entry.flags));
                assertFalse(foot.isTurnRestricted(entry.flags));
                assertFalse(bike.isTurnRestricted(entry.flags));

                assertTrue(Double.isInfinite(car.getTurnCost(entry.flags)));
                assertEquals(0, foot.getTurnCost(entry.flags), 1e-1);
                assertEquals(0, bike.getTurnCost(entry.flags), 1e-1);
            } else if (entry.edgeFrom == 2)
            {
                // the 2nd entry provides turn flags for bike only
                assertEquals(assertFlag2, entry.flags);
                assertFalse(car.isTurnRestricted(entry.flags));
                assertFalse(foot.isTurnRestricted(entry.flags));
                assertFalse(bike.isTurnRestricted(entry.flags));

                assertEquals(0, car.getTurnCost(entry.flags), 1e-1);
                assertEquals(0, foot.getTurnCost(entry.flags), 1e-1);
                assertEquals(10, bike.getTurnCost(entry.flags), 1e-1);
            }
        }
    }
}


File: core/src/test/java/com/graphhopper/reader/OSMTurnRelationTest.java
/*
 *  Licensed to Peter Karich under one or more contributor license
 *  agreements. See the NOTICE file distributed with this work for
 *  additional information regarding copyright ownership.
 *
 *  Peter Karich licenses this file to you under the Apache License,
 *  Version 2.0 (the "License"); you may not use this file except
 *  in compliance with the License. You may obtain a copy of the
 *  License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.reader;

import com.graphhopper.reader.OSMTurnRelation.Type;
import com.graphhopper.routing.EdgeBasedRoutingAlgorithmTest;
import com.graphhopper.routing.util.CarFlagEncoder;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.storage.GraphBuilder;
import com.graphhopper.storage.GraphStorage;
import com.graphhopper.util.EdgeExplorer;

import java.util.Collection;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

import org.junit.Test;

import static org.junit.Assert.*;

/**
 * @author Peter Karich
 */
public class OSMTurnRelationTest
{
    @Test
    public void testGetRestrictionAsEntries()
    {
        CarFlagEncoder encoder = new CarFlagEncoder(5, 5, 3);
        final Map<Long, Integer> osmNodeToInternal = new HashMap<Long, Integer>();
        final Map<Integer, Long> internalToOSMEdge = new HashMap<Integer, Long>();

        osmNodeToInternal.put(3L, 3);
        // edge ids are only stored if they occured before in an OSMRelation
        internalToOSMEdge.put(3, 3L);
        internalToOSMEdge.put(4, 4L);

        GraphStorage graph = new GraphBuilder(new EncodingManager(encoder)).create();
        EdgeBasedRoutingAlgorithmTest.initGraph(graph);
        OSMReader osmReader = new OSMReader(graph)
        {

            @Override
            public int getInternalNodeIdOfOsmNode( long nodeOsmId )
            {
                return osmNodeToInternal.get(nodeOsmId);
            }

            @Override
            public long getOsmIdOfInternalEdge( int edgeId )
            {
                Long l = internalToOSMEdge.get(edgeId);
                if (l == null)
                    return -1;
                return l;
            }
        };

        EdgeExplorer edgeExplorer = graph.createEdgeExplorer();

        // TYPE == ONLY
        OSMTurnRelation instance = new OSMTurnRelation(4, 3, 3, Type.ONLY);
        Collection<OSMTurnRelation.TurnCostTableEntry> result
                = instance.getRestrictionAsEntries(encoder, edgeExplorer, edgeExplorer, osmReader);

        assertEquals(2, result.size());
        Iterator<OSMTurnRelation.TurnCostTableEntry> iter = result.iterator();
        OSMTurnRelation.TurnCostTableEntry entry = iter.next();
        assertEquals(4, entry.edgeFrom);
        assertEquals(6, entry.edgeTo);
        assertEquals(3, entry.nodeVia);

        entry = iter.next();
        assertEquals(4, entry.edgeFrom);
        assertEquals(2, entry.edgeTo);
        assertEquals(3, entry.nodeVia);


        // TYPE == NOT
        instance = new OSMTurnRelation(4, 3, 3, Type.NOT);
        result = instance.getRestrictionAsEntries(encoder, edgeExplorer, edgeExplorer, osmReader);

        assertEquals(1, result.size());
        iter = result.iterator();
        entry = iter.next();
        assertEquals(4, entry.edgeFrom);
        assertEquals(3, entry.edgeTo);
        assertEquals(3, entry.nodeVia);
    }

}


File: core/src/test/java/com/graphhopper/routing/AStarBidirectionTest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing;

import com.graphhopper.routing.util.ShortestWeighting;

import java.util.Arrays;
import java.util.Collection;

import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;
import org.junit.runners.Parameterized.Parameters;

import com.graphhopper.routing.util.TraversalMode;
import com.graphhopper.storage.Graph;

import java.util.concurrent.atomic.AtomicReference;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

/**
 * @author Peter Karich
 */
@RunWith(Parameterized.class)
public class AStarBidirectionTest extends AbstractRoutingAlgorithmTester
{
    /**
     * Runs the same test with each of the supported traversal modes
     */
    @Parameters(name = "{0}")
    public static Collection<Object[]> configs()
    {
        return Arrays.asList(new Object[][]
                {
                        {
                                TraversalMode.NODE_BASED
                        },
                        {
                                TraversalMode.EDGE_BASED_1DIR
                        },
                        {
                                TraversalMode.EDGE_BASED_2DIR
                        },
                        {
                                TraversalMode.EDGE_BASED_2DIR_UTURN
                        }
                });
    }

    private final TraversalMode traversalMode;

    public AStarBidirectionTest( TraversalMode tMode )
    {
        this.traversalMode = tMode;
    }

    @Override
    public RoutingAlgorithmFactory createFactory( Graph prepareGraph, AlgorithmOptions prepareOpts )
    {
        return new RoutingAlgorithmFactory()
        {
            @Override
            public RoutingAlgorithm createAlgo( Graph g, AlgorithmOptions opts )
            {
                return new AStarBidirection(g, opts.getFlagEncoder(), opts.getWeighting(), traversalMode);
            }
        };
    }

    @Test
    public void testInitFromAndTo()
    {
        Graph g = createGraph(false);
        g.edge(0, 1, 1, true);
        updateDistancesFor(g, 0, 0.00, 0.00);
        updateDistancesFor(g, 1, 0.01, 0.01);

        final AtomicReference<AStar.AStarEdge> fromRef = new AtomicReference<AStar.AStarEdge>();
        final AtomicReference<AStar.AStarEdge> toRef = new AtomicReference<AStar.AStarEdge>();
        AStarBidirection astar = new AStarBidirection(g, carEncoder, new ShortestWeighting(), traversalMode)
        {
            @Override
            public void initFrom( int from, double weight )
            {
                super.initFrom(from, weight);
                fromRef.set(currFrom);
            }

            @Override
            public void initTo( int to, double weight )
            {
                super.initTo(to, weight);
                toRef.set(currTo);
            }
        };
        astar.initFrom(0, 1);
        astar.initTo(1, 0.5);

        assertEquals(1, fromRef.get().weightOfVisitedPath, .1);
        assertEquals(787.3, fromRef.get().weight, .1);

        assertEquals(0.5, toRef.get().weightOfVisitedPath, .1);
        assertEquals(786.8, toRef.get().weight, .1);
    }
}


File: core/src/test/java/com/graphhopper/routing/AStarTest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing;

import com.graphhopper.routing.util.*;

import java.util.Arrays;
import java.util.Collection;

import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;
import org.junit.runners.Parameterized.Parameters;

import com.graphhopper.storage.Graph;

/**
 * @author Peter Karich
 */
@RunWith(Parameterized.class)
public class AStarTest extends AbstractRoutingAlgorithmTester
{
    /**
     * Runs the same test with each of the supported traversal modes
     */
    @Parameters(name = "{0}")
    public static Collection<Object[]> configs()
    {
        return Arrays.asList(new Object[][]
                {
                        {TraversalMode.NODE_BASED},
                        {TraversalMode.EDGE_BASED_1DIR},
                        {TraversalMode.EDGE_BASED_2DIR},
                        {TraversalMode.EDGE_BASED_2DIR_UTURN}
                });
    }

    private final TraversalMode traversalMode;

    public AStarTest( TraversalMode tMode )
    {
        this.traversalMode = tMode;
    }

    @Override
    public RoutingAlgorithmFactory createFactory( Graph prepareGraph, AlgorithmOptions prepareOpts )
    {
        return new RoutingAlgorithmFactory()
        {
            @Override
            public RoutingAlgorithm createAlgo( Graph g, AlgorithmOptions opts )
            {
                return new AStar(g, opts.getFlagEncoder(), opts.getWeighting(), traversalMode);
            }
        };
    }
}


File: core/src/test/java/com/graphhopper/routing/AbstractRoutingAlgorithmTester.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing;

import com.graphhopper.routing.util.*;
import com.graphhopper.storage.*;
import com.graphhopper.storage.index.LocationIndex;
import com.graphhopper.storage.index.LocationIndexTree;
import com.graphhopper.storage.index.QueryResult;
import com.graphhopper.util.*;
import gnu.trove.list.TIntList;

import java.util.Random;

import static org.junit.Assert.*;

import org.junit.Before;
import org.junit.Test;

/**
 * @author Peter Karich
 */
public abstract class AbstractRoutingAlgorithmTester
{
    // problem is: matrix graph is expensive to create to cache it in a static variable
    private static Graph matrixGraph;
    protected static final EncodingManager encodingManager = new EncodingManager("CAR,FOOT");
    protected FlagEncoder carEncoder;
    protected FlagEncoder footEncoder;
    protected AlgorithmOptions defaultOpts;

    @Before
    public void setUp()
    {
        carEncoder = (CarFlagEncoder) encodingManager.getEncoder("CAR");
        footEncoder = (FootFlagEncoder) encodingManager.getEncoder("FOOT");
        defaultOpts = AlgorithmOptions.start().flagEncoder(carEncoder).
                weighting(new ShortestWeighting()).build();
    }

    protected Graph createGraph( EncodingManager em, boolean is3D )
    {
        return new GraphBuilder(em).set3D(is3D).create();
    }

    protected Graph createGraph( boolean is3D )
    {
        return createGraph(encodingManager, is3D);
    }

    public RoutingAlgorithm createAlgo( Graph g )
    {
        return createAlgo(g, defaultOpts);
    }

    public RoutingAlgorithm createAlgo( Graph g, AlgorithmOptions opts )
    {
        return createFactory(g, opts).createAlgo(g, opts);
    }

    public abstract RoutingAlgorithmFactory createFactory( Graph g, AlgorithmOptions opts );

    @Test
    public void testCalcShortestPath()
    {
        Graph graph = createTestGraph();
        RoutingAlgorithm algo = createAlgo(graph);
        Path p = algo.calcPath(0, 7);
        assertEquals(p.toString(), Helper.createTList(0, 4, 5, 7), p.calcNodes());
        assertEquals(p.toString(), 62.1, p.getDistance(), .1);
    }

    @Test
    public void testWeightLimit()
    {
        Graph graph = createTestGraph();
        RoutingAlgorithm algo = createAlgo(graph);
        algo.setWeightLimit(10);
        Path p = algo.calcPath(0, 7);
        assertTrue(algo.getVisitedNodes() < 7);
        assertFalse(p.isFound());
        assertEquals(p.toString(), Helper.createTList(), p.calcNodes());
    }

    @Test
    public void testWeightLimit_issue380()
    {
        Graph graph = createGraph(false);
        initGraphWeightLimit(graph);
        RoutingAlgorithm algo = createAlgo(graph);
        algo.setWeightLimit(3);
        Path p = algo.calcPath(0, 4);
        assertTrue(p.isFound());
        assertEquals(3.0, p.getWeight(), 1e-6);

        algo = createAlgo(graph);
        algo.setWeightLimit(3);
        p = algo.calcPath(0, 3);
        assertTrue(p.isFound());
        assertEquals(3.0, p.getWeight(), 1e-6);
    }

    // see calc-fastest-graph.svg
    @Test
    public void testCalcFastestPath()
    {
        Graph graphShortest = createGraph(false);
        initDirectedAndDiffSpeed(graphShortest, carEncoder);
        Path p1 = createAlgo(graphShortest, defaultOpts).
                calcPath(0, 3);
        assertEquals(Helper.createTList(0, 1, 5, 2, 3), p1.calcNodes());
        assertEquals(p1.toString(), 402.3, p1.getDistance(), .1);
        assertEquals(p1.toString(), 144823, p1.getTime());

        Graph graphFastest = createGraph(false);
        initDirectedAndDiffSpeed(graphFastest, carEncoder);
        Path p2 = createAlgo(graphFastest,
                AlgorithmOptions.start().flagEncoder(carEncoder).weighting(new FastestWeighting(carEncoder)).build()).
                calcPath(0, 3);
        assertEquals(Helper.createTList(0, 4, 6, 7, 5, 3), p2.calcNodes());
        assertEquals(p2.toString(), 1261.7, p2.getDistance(), 0.1);
        assertEquals(p2.toString(), 111442, p2.getMillis());
    }

    // 0-1-2-3
    // |/|/ /|
    // 4-5-- |
    // |/ \--7
    // 6----/
    protected void initDirectedAndDiffSpeed( Graph graph, FlagEncoder enc )
    {
        graph.edge(0, 1).setFlags(enc.setProperties(10, true, false));
        graph.edge(0, 4).setFlags(enc.setProperties(100, true, false));

        graph.edge(1, 4).setFlags(enc.setProperties(10, true, true));
        graph.edge(1, 5).setFlags(enc.setProperties(10, true, true));
        EdgeIteratorState edge12 = graph.edge(1, 2).setFlags(enc.setProperties(10, true, true));

        graph.edge(5, 2).setFlags(enc.setProperties(10, true, false));
        graph.edge(2, 3).setFlags(enc.setProperties(10, true, false));

        EdgeIteratorState edge53 = graph.edge(5, 3).setFlags(enc.setProperties(20, true, false));
        graph.edge(3, 7).setFlags(enc.setProperties(10, true, false));

        graph.edge(4, 6).setFlags(enc.setProperties(100, true, false));
        graph.edge(5, 4).setFlags(enc.setProperties(10, true, false));

        graph.edge(5, 6).setFlags(enc.setProperties(10, true, false));
        graph.edge(7, 5).setFlags(enc.setProperties(100, true, false));

        graph.edge(6, 7).setFlags(enc.setProperties(100, true, true));

        updateDistancesFor(graph, 0, 0.002, 0);
        updateDistancesFor(graph, 1, 0.002, 0.001);
        updateDistancesFor(graph, 2, 0.002, 0.002);
        updateDistancesFor(graph, 3, 0.002, 0.003);
        updateDistancesFor(graph, 4, 0.0015, 0);
        updateDistancesFor(graph, 5, 0.0015, 0.001);
        updateDistancesFor(graph, 6, 0, 0);
        updateDistancesFor(graph, 7, 0.001, 0.003);

        edge12.setDistance(edge12.getDistance() * 2);
        edge53.setDistance(edge53.getDistance() * 2);
    }

    @Test
    public void testCalcFootPath()
    {
        Graph graphShortest = createGraph(false);
        initFootVsCar(graphShortest);
        Path p1 = createAlgo(graphShortest, AlgorithmOptions.start().flagEncoder(footEncoder).
                weighting(new ShortestWeighting()).build()).
                calcPath(0, 7);
        assertEquals(p1.toString(), 17000, p1.getDistance(), 1e-6);
        assertEquals(p1.toString(), 12240 * 1000, p1.getTime());
        assertEquals(Helper.createTList(0, 4, 5, 7), p1.calcNodes());
    }

    protected void initFootVsCar( Graph graph )
    {
        graph.edge(0, 1).setDistance(7000).setFlags(footEncoder.setProperties(5, true, true) | carEncoder.setProperties(10, true, false));
        graph.edge(0, 4).setDistance(5000).setFlags(footEncoder.setProperties(5, true, true) | carEncoder.setProperties(20, true, false));

        graph.edge(1, 4).setDistance(7000).setFlags(carEncoder.setProperties(10, true, true));
        graph.edge(1, 5).setDistance(7000).setFlags(carEncoder.setProperties(10, true, true));
        graph.edge(1, 2).setDistance(20000).setFlags(footEncoder.setProperties(5, true, true) | carEncoder.setProperties(10, true, true));

        graph.edge(5, 2).setDistance(5000).setFlags(carEncoder.setProperties(10, true, false));
        graph.edge(2, 3).setDistance(5000).setFlags(footEncoder.setProperties(5, true, true) | carEncoder.setProperties(10, true, false));

        graph.edge(5, 3).setDistance(11000).setFlags(carEncoder.setProperties(20, true, false));
        graph.edge(3, 7).setDistance(7000).setFlags(footEncoder.setProperties(5, true, true) | carEncoder.setProperties(10, true, false));

        graph.edge(4, 6).setDistance(5000).setFlags(carEncoder.setProperties(20, true, false));
        graph.edge(5, 4).setDistance(7000).setFlags(footEncoder.setProperties(5, true, true) | carEncoder.setProperties(10, true, false));

        graph.edge(5, 6).setDistance(7000).setFlags(carEncoder.setProperties(10, true, false));
        graph.edge(7, 5).setDistance(5000).setFlags(footEncoder.setProperties(5, true, true) | carEncoder.setProperties(20, true, false));

        graph.edge(6, 7).setDistance(5000).setFlags(carEncoder.setProperties(20, true, true));
    }

    // see test-graph.svg !
    protected Graph createTestGraph()
    {
        Graph graph = createGraph(false);

        graph.edge(0, 1, 7, true);
        graph.edge(0, 4, 6, true);

        graph.edge(1, 4, 2, true);
        graph.edge(1, 5, 8, true);
        graph.edge(1, 2, 2, true);

        graph.edge(2, 5, 5, true);
        graph.edge(2, 3, 2, true);

        graph.edge(3, 5, 2, true);
        graph.edge(3, 7, 10, true);

        graph.edge(4, 6, 4, true);
        graph.edge(4, 5, 7, true);

        graph.edge(5, 6, 2, true);
        graph.edge(5, 7, 1, true);

        EdgeIteratorState edge6_7 = graph.edge(6, 7, 5, true);

        updateDistancesFor(graph, 0, 0.0010, 0.00001);
        updateDistancesFor(graph, 1, 0.0008, 0.0000);
        updateDistancesFor(graph, 2, 0.0005, 0.0001);
        updateDistancesFor(graph, 3, 0.0006, 0.0002);
        updateDistancesFor(graph, 4, 0.0009, 0.0001);
        updateDistancesFor(graph, 5, 0.0007, 0.0001);
        updateDistancesFor(graph, 6, 0.0009, 0.0002);
        updateDistancesFor(graph, 7, 0.0008, 0.0003);

        edge6_7.setDistance(5 * edge6_7.getDistance());
        return graph;
    }

    @Test
    public void testNoPathFound()
    {
        Graph graph = createGraph(false);
        assertFalse(createAlgo(graph).calcPath(0, 1).isFound());

        // two disconnected areas
        graph.edge(0, 1, 7, true);

        graph.edge(5, 6, 2, true);
        graph.edge(5, 7, 1, true);
        graph.edge(5, 8, 1, true);
        graph.edge(7, 8, 1, true);
        RoutingAlgorithm algo = createAlgo(graph);
        assertFalse(algo.calcPath(0, 5).isFound());
        // assertEquals(3, algo.getVisitedNodes());

        // disconnected as directed graph
        graph = createGraph(false);
        graph.edge(0, 1, 1, false);
        graph.edge(0, 2, 1, true);
        assertFalse(createAlgo(graph).calcPath(1, 2).isFound());
    }

    @Test
    public void testWikipediaShortestPath()
    {
        Graph graph = createWikipediaTestGraph();
        Path p = createAlgo(graph).calcPath(0, 4);
        assertEquals(p.toString(), 20, p.getDistance(), 1e-4);
        assertEquals(p.toString(), 4, p.calcNodes().size());
    }

    @Test
    public void testCalcIf1EdgeAway()
    {
        Graph graph = createTestGraph();
        Path p = createAlgo(graph).calcPath(1, 2);
        assertEquals(Helper.createTList(1, 2), p.calcNodes());
        assertEquals(p.toString(), 35.1, p.getDistance(), .1);
    }

    // see wikipedia-graph.svg !
    protected Graph createWikipediaTestGraph()
    {
        Graph graph = createGraph(false);
        graph.edge(0, 1, 7, true);
        graph.edge(0, 2, 9, true);
        graph.edge(0, 5, 14, true);
        graph.edge(1, 2, 10, true);
        graph.edge(1, 3, 15, true);
        graph.edge(2, 5, 2, true);
        graph.edge(2, 3, 11, true);
        graph.edge(3, 4, 6, true);
        graph.edge(4, 5, 9, true);
        return graph;
    }

    // 0-1-2-3-4
    // |     / |
    // |    8  |
    // \   /   |
    //  7-6----5
    public static Graph initBiGraph( Graph graph )
    {
        // distance will be overwritten in second step as we need to calculate it from lat,lon
        graph.edge(0, 1, 1, true);
        graph.edge(1, 2, 1, true);
        graph.edge(2, 3, 1, true);
        graph.edge(3, 4, 1, true);
        graph.edge(4, 5, 1, true);
        graph.edge(5, 6, 1, true);
        graph.edge(6, 7, 1, true);
        graph.edge(7, 0, 1, true);
        graph.edge(3, 8, 1, true);
        graph.edge(8, 6, 1, true);

        // we need lat,lon for edge precise queries because the distances of snapped point 
        // to adjacent nodes is calculated from lat,lon of the necessary points
        updateDistancesFor(graph, 0, 0.001, 0);
        updateDistancesFor(graph, 1, 0.100, 0.0005);
        updateDistancesFor(graph, 2, 0.010, 0.0010);
        updateDistancesFor(graph, 3, 0.001, 0.0011);
        updateDistancesFor(graph, 4, 0.001, 0.00111);

        updateDistancesFor(graph, 8, 0.0005, 0.0011);

        updateDistancesFor(graph, 7, 0, 0);
        updateDistancesFor(graph, 6, 0, 0.001);
        updateDistancesFor(graph, 5, 0, 0.004);
        return graph;
    }

    private static final DistanceCalc distCalc = new DistanceCalcEarth();

    public static void updateDistancesFor( Graph g, int node, double lat, double lon )
    {
        NodeAccess na = g.getNodeAccess();
        na.setNode(node, lat, lon);
        EdgeIterator iter = g.createEdgeExplorer().setBaseNode(node);
        while (iter.next())
        {
            iter.setDistance(iter.fetchWayGeometry(3).calcDistance(distCalc));
            // System.out.println(node + "->" + adj + ": " + iter.getDistance());
        }
    }

    @Test
    public void testBidirectional()
    {
        Graph graph = createGraph(false);
        initBiGraph(graph);

        // PrepareTowerNodesShortcutsTest.printEdges((LevelGraph) graph);
        Path p = createAlgo(graph).calcPath(0, 4);
        // PrepareTowerNodesShortcutsTest.printEdges((LevelGraph) graph);
        assertEquals(p.toString(), Helper.createTList(0, 7, 6, 8, 3, 4), p.calcNodes());
        assertEquals(p.toString(), 335.8, p.getDistance(), .1);

        p = createAlgo(graph).calcPath(1, 2);
        // the other way around is even larger as 0-1 is already 11008.452
        assertEquals(p.toString(), Helper.createTList(1, 2), p.calcNodes());
        assertEquals(p.toString(), 10007.7, p.getDistance(), .1);
    }

    // 1-2-3-4-5
    // |     / |
    // |    9  |
    // \   /   /
    //  8-7-6-/
    @Test
    public void testBidirectional2()
    {
        Graph graph = createGraph(false);

        graph.edge(0, 1, 100, true);
        graph.edge(1, 2, 1, true);
        graph.edge(2, 3, 1, true);
        graph.edge(3, 4, 1, true);
        graph.edge(4, 5, 20, true);
        graph.edge(5, 6, 10, true);
        graph.edge(6, 7, 5, true);
        graph.edge(7, 0, 5, true);
        graph.edge(3, 8, 20, true);
        graph.edge(8, 6, 20, true);

        Path p = createAlgo(graph).calcPath(0, 4);
        assertEquals(p.toString(), 40, p.getDistance(), 1e-4);
        assertEquals(p.toString(), 5, p.calcNodes().size());
        assertEquals(Helper.createTList(0, 7, 6, 5, 4), p.calcNodes());
    }

    @Test
    public void testRekeyBugOfIntBinHeap()
    {
        // using Dijkstra + IntBinHeap then rekey loops endlessly
        Path p = createAlgo(getMatrixGraph()).calcPath(36, 91);
        assertEquals(12, p.calcNodes().size());

        TIntList list = p.calcNodes();
        if (!Helper.createTList(36, 46, 56, 66, 76, 86, 85, 84, 94, 93, 92, 91).equals(list)
                && !Helper.createTList(36, 46, 56, 66, 76, 86, 85, 84, 83, 82, 92, 91).equals(list))
        {
            assertTrue("wrong locations: " + list.toString(), false);
        }
        assertEquals(66f, p.getDistance(), 1e-3);
    }

    @Test
    public void testBug1()
    {
        Path p = createAlgo(getMatrixGraph()).calcPath(34, 36);
        assertEquals(Helper.createTList(34, 35, 36), p.calcNodes());
        assertEquals(3, p.calcNodes().size());
        assertEquals(17, p.getDistance(), 1e-5);
    }

    @Test
    public void testCorrectWeight()
    {
        Path p = createAlgo(getMatrixGraph()).calcPath(45, 72);
        assertEquals(Helper.createTList(45, 44, 54, 64, 74, 73, 72), p.calcNodes());
        assertEquals(38f, p.getDistance(), 1e-3);
    }

    @Test
    public void testCannotCalculateSP()
    {
        Graph graph = createGraph(false);
        graph.edge(0, 1, 1, false);
        graph.edge(1, 2, 1, false);

        Path p = createAlgo(graph).calcPath(0, 2);
        assertEquals(p.toString(), 3, p.calcNodes().size());
    }

    @Test
    public void testDirectedGraphBug1()
    {
        Graph graph = createGraph(false);
        graph.edge(0, 1, 3, false);
        graph.edge(1, 2, 2.99, false);

        graph.edge(0, 3, 2, false);
        graph.edge(3, 4, 3, false);
        graph.edge(4, 2, 1, false);

        Path p = createAlgo(graph).calcPath(0, 2);
        assertEquals(Helper.createTList(0, 1, 2), p.calcNodes());
        assertEquals(p.toString(), 5.99, p.getDistance(), 1e-4);
        assertEquals(p.toString(), 3, p.calcNodes().size());
    }

    @Test
    public void testDirectedGraphBug2()
    {
        Graph graph = createGraph(false);
        graph.edge(0, 1, 1, false);
        graph.edge(1, 2, 1, false);
        graph.edge(2, 3, 1, false);

        graph.edge(3, 1, 4, true);

        Path p = createAlgo(graph).calcPath(0, 3);
        assertEquals(Helper.createTList(0, 1, 2, 3), p.calcNodes());
    }

    // a-b-0-c-1
    // |   |  _/\
    // |  /  /  |
    // d-2--3-e-4
    @Test
    public void testWithCoordinates()
    {
        Graph graph = createGraph(false);

        graph.edge(0, 1, 2, true).setWayGeometry(Helper.createPointList(1.5, 1));
        graph.edge(2, 3, 2, true).setWayGeometry(Helper.createPointList(0, 1.5));
        graph.edge(3, 4, 2, true).setWayGeometry(Helper.createPointList(0, 2));

        // duplicate but one is longer
        graph.edge(0, 2, 1.2, true);
        graph.edge(0, 2, 1.5, true).setWayGeometry(Helper.createPointList(0.5, 0));

        graph.edge(1, 3, 1.3, true).setWayGeometry(Helper.createPointList(0.5, 1.5));
        graph.edge(1, 4, 1, true);

        updateDistancesFor(graph, 0, 1, 0.6);
        updateDistancesFor(graph, 1, 1, 1.5);
        updateDistancesFor(graph, 2, 0, 0);
        updateDistancesFor(graph, 3, 0, 1);
        updateDistancesFor(graph, 4, 0, 2);

        AlgorithmOptions opts = new AlgorithmOptions(AlgorithmOptions.DIJKSTRA_BI, carEncoder, new ShortestWeighting());
        RoutingAlgorithmFactory prepare = createFactory(graph, opts);
        Path p = prepare.createAlgo(graph, opts).calcPath(4, 0);
        assertEquals(Helper.createTList(4, 1, 0), p.calcNodes());
        assertEquals(Helper.createPointList(0, 2, 1, 1.5, 1.5, 1, 1, 0.6), p.calcPoints());
        assertEquals(274128, p.calcPoints().calcDistance(new DistanceCalcEarth()), 1);

        // PrepareTowerNodesShortcutsTest.printEdges((LevelGraph) graph);
        p = prepare.createAlgo(graph, opts).calcPath(2, 1);
        assertEquals(Helper.createTList(2, 0, 1), p.calcNodes());
        assertEquals(Helper.createPointList(0, 0, 1, 0.6, 1.5, 1, 1, 1.5), p.calcPoints());
        assertEquals(279482, p.calcPoints().calcDistance(new DistanceCalcEarth()), 1);
    }

    @Test
    public void testCalcIfEmptyWay()
    {
        Graph graph = createTestGraph();
        Path p = createAlgo(graph).calcPath(0, 0);
        assertEquals(p.calcNodes().toString(), 1, p.calcNodes().size());
        assertEquals(p.toString(), 0, p.getDistance(), 1e-4);
    }

    @Test
    public void testViaEdges_FromEqualsTo()
    {
        Graph graph = createTestGraph();
        // identical tower nodes
        Path p = calcPathViaQuery(graph, 0.001, 0.000, 0.001, 0.000);
        assertTrue(p.isFound());
        assertEquals(Helper.createTList(0), p.calcNodes());
        // assertEquals(1, p.calcPoints().size());
        assertEquals(p.toString(), 0, p.getDistance(), 1e-4);

        // identical query points on edge
        p = calcPath(graph, 0, 1, 0, 1);
        assertTrue(p.isFound());
        assertEquals(Helper.createTList(8), p.calcNodes());
        // assertEquals(1, p.calcPoints().size());
        assertEquals(p.toString(), 0, p.getDistance(), 1e-4);

        // very close
        p = calcPathViaQuery(graph, 0.00092, 0, 0.00091, 0);
        assertEquals(Helper.createTList(8, 9), p.calcNodes());
        assertEquals(p.toString(), 1.11, p.getDistance(), .1);
    }

    @Test
    public void testViaEdges_BiGraph()
    {
        Graph graph = createGraph(false);
        initBiGraph(graph);

        // 0-7 to 4-3        
        Path p = calcPathViaQuery(graph, 0.0009, 0, 0.001, 0.001105);
        assertEquals(p.toString(), Helper.createTList(10, 7, 6, 8, 3, 9), p.calcNodes());
        assertEquals(p.toString(), 324.11, p.getDistance(), 0.01);

        // 0-1 to 2-3
        p = calcPathViaQuery(graph, 0.001, 0.0001, 0.010, 0.0011);
        assertEquals(p.toString(), Helper.createTList(0, 7, 6, 8, 3, 9), p.calcNodes());
        assertEquals(p.toString(), 1335.35, p.getDistance(), 0.01);
    }

    @Test
    public void testViaEdges_WithCoordinates()
    {
        Graph graph = createTestGraph();
        Path p = calcPath(graph, 0, 1, 2, 3);
        assertEquals(Helper.createTList(9, 1, 2, 8), p.calcNodes());
        assertEquals(p.toString(), 56.7, p.getDistance(), .1);
    }

    @Test
    public void testViaEdges_SpecialCases()
    {
        Graph graph = createGraph(false);
        // 0->1\
        // |    2
        // 4<-3/
        graph.edge(0, 1, 7, false);
        graph.edge(1, 2, 7, true);
        graph.edge(2, 3, 7, true);
        graph.edge(3, 4, 7, false);
        graph.edge(4, 0, 7, true);

        updateDistancesFor(graph, 4, 0, 0);
        updateDistancesFor(graph, 0, 0.00010, 0);
        updateDistancesFor(graph, 1, 0.00010, 0.0001);
        updateDistancesFor(graph, 2, 0.00005, 0.00015);
        updateDistancesFor(graph, 3, 0, 0.0001);

        // 0-1 to 3-4
        Path p = calcPathViaQuery(graph, 0.00010, 0.00001, 0, 0.00009);
        assertEquals(Helper.createTList(6, 1, 2, 3, 5), p.calcNodes());
        assertEquals(p.toString(), 26.81, p.getDistance(), .1);

        // overlapping edges: 2-3 and 3-2
        p = calcPathViaQuery(graph, 0.000049, 0.00014, 0.00001, 0.0001);
        assertEquals(Helper.createTList(5, 6), p.calcNodes());
        assertEquals(p.toString(), 6.2, p.getDistance(), .1);

        // 'from' and 'to' edge share one node '2': 1-2 to 3-2
        p = calcPathViaQuery(graph, 0.00009, 0.00011, 0.00001, 0.00011);
        assertEquals(p.toString(), Helper.createTList(6, 2, 5), p.calcNodes());
        assertEquals(p.toString(), 12.57, p.getDistance(), .1);
    }

    @Test
    public void testQueryGraphAndFastest()
    {
        Graph graph = createGraph(false);
        initDirectedAndDiffSpeed(graph, carEncoder);
        Path p = calcPathViaQuery("fastest", graph, 0.002, 0.0005, 0.0017, 0.0031);
        assertEquals(Helper.createTList(9, 1, 5, 3, 8), p.calcNodes());
        assertEquals(602.98, p.getDistance(), 1e-1);
    }

    // Problem: for contraction hierarchy we cannot easily select egdes by nodes as some edges are skipped
    Path calcPathViaQuery( Graph graph, double fromLat, double fromLon, double toLat, double toLon )
    {
        return calcPathViaQuery("shortest", graph, fromLat, fromLon, toLat, toLon);
    }

    Path calcPathViaQuery( String weighting, Graph graph, double fromLat, double fromLon, double toLat, double toLon )
    {
        LocationIndex index = new LocationIndexTree(graph.getBaseGraph(), new RAMDirectory());
        index.prepareIndex();
        QueryResult from = index.findClosest(fromLat, fromLon, EdgeFilter.ALL_EDGES);
        QueryResult to = index.findClosest(toLat, toLon, EdgeFilter.ALL_EDGES);
        Weighting w = new ShortestWeighting();
        if (weighting.equalsIgnoreCase("fastest"))
            w = new FastestWeighting(carEncoder);

        // correct order for CH: in factory do prepare and afterwards wrap in query graph
        AlgorithmOptions opts = AlgorithmOptions.start().flagEncoder(carEncoder).weighting(w).build();
        RoutingAlgorithmFactory factory = createFactory(graph, opts);
        QueryGraph qGraph = new QueryGraph(graph).lookup(from, to);
        return factory.createAlgo(qGraph, opts).
                calcPath(from.getClosestNode(), to.getClosestNode());
    }

    Path calcPath( Graph graph, int fromNode1, int fromNode2, int toNode1, int toNode2 )
    {
        // lookup two edges: fromNode1-fromNode2 and toNode1-toNode2        
        QueryResult from = newQR(graph, fromNode1, fromNode2);
        QueryResult to = newQR(graph, toNode1, toNode2);

        RoutingAlgorithmFactory factory = createFactory(graph, defaultOpts);
        QueryGraph qGraph = new QueryGraph(graph).lookup(from, to);
        return factory.createAlgo(qGraph, defaultOpts).calcPath(from.getClosestNode(), to.getClosestNode());
    }

    /**
     * Creates query result on edge (node1-node2) very close to node1.
     */
    QueryResult newQR( Graph graph, int node1, int node2 )
    {
        EdgeIteratorState edge = GHUtility.getEdge(graph, node1, node2);
        if (edge == null)
            throw new IllegalStateException("edge not found? " + node1 + "-" + node2);

        NodeAccess na = graph.getNodeAccess();
        double lat = na.getLatitude(edge.getBaseNode());
        double lon = na.getLongitude(edge.getBaseNode());
        double latAdj = na.getLatitude(edge.getAdjNode());
        double lonAdj = na.getLongitude(edge.getAdjNode());
        // calculate query point near the base node but not directly on it!
        QueryResult res = new QueryResult(lat + (latAdj - lat) * .1, lon + (lonAdj - lon) * .1);
        res.setClosestNode(edge.getBaseNode());
        res.setClosestEdge(edge);
        res.setWayIndex(0);
        res.setSnappedPosition(QueryResult.Position.EDGE);
        res.calcSnappedPoint(distCalc);
        return res;
    }

    @Test
    public void testTwoWeightsPerEdge()
    {
        FlagEncoder encoder = new Bike2WeightFlagEncoder();
        Graph graph = initEleGraph(createGraph(new EncodingManager(encoder), true));
        // force the other path
        GHUtility.getEdge(graph, 0, 3).setFlags(encoder.setProperties(10, false, true));

        // for two weights per edge it happened that Path (and also the Weighting) read the wrong side 
        // of the speed and read 0 => infinity weight => overflow of millis => negative millis!
        Path p = createAlgo(graph, AlgorithmOptions.start().flagEncoder(encoder).weighting(new FastestWeighting(encoder)).build()).calcPath(0, 10);
        assertEquals(85124371, p.getTime());
        assertEquals(425622, p.getDistance(), 1);
        assertEquals(85124.4, p.getWeight(), 1);
    }

    @Test
    public void test0SpeedButUnblocked_Issue242()
    {
        Graph graph = createGraph(false);
        long flags = carEncoder.setAccess(carEncoder.setSpeed(0, 0), true, true);

        graph.edge(0, 1).setFlags(flags).setDistance(10);
        graph.edge(1, 2).setFlags(flags).setDistance(10);

        RoutingAlgorithm algo = createAlgo(graph);
        try
        {
            Path p = algo.calcPath(0, 2);
            assertTrue(false);
        } catch (Exception ex)
        {
            assertTrue(ex.getMessage(), ex.getMessage().startsWith("Speed cannot be 0"));
        }
    }

    @Test
    public void testTwoWeightsPerEdge2()
    {
        // other direction should be different!
        Graph graph = initEleGraph(createGraph(true));
        Path p = createAlgo(graph).calcPath(0, 10);
        // GHUtility.printEdgeInfo(graph, carEncoder);
        assertEquals(Helper.createTList(0, 4, 6, 10), p.calcNodes());
        Weighting fakeWeighting = new Weighting()
        {
            @Override
            public double getMinWeight( double distance )
            {
                return 0.8 * distance;
            }

            @Override
            public double calcWeight( EdgeIteratorState edgeState, boolean reverse, int prevOrNextEdgeId )
            {
                int adj = edgeState.getAdjNode();
                int base = edgeState.getBaseNode();
                if (reverse)
                {
                    int tmp = base;
                    base = adj;
                    adj = tmp;
                }

                // a 'hill' at node 6
                if (adj == 6)
                    return 3 * edgeState.getDistance();
                else if (base == 6)
                    return edgeState.getDistance() * 0.9;
                else if (adj == 4)
                    return 2 * edgeState.getDistance();

                return edgeState.getDistance() * 0.8;
            }
        };

        graph = initEleGraph(createGraph(true));
        QueryResult from = newQR(graph, 3, 0);
        QueryResult to = newQR(graph, 10, 9);

        AlgorithmOptions opts = AlgorithmOptions.start().flagEncoder(carEncoder).weighting(fakeWeighting).build();
        RoutingAlgorithmFactory factory = createFactory(graph, opts);
        QueryGraph qGraph = new QueryGraph(graph).lookup(from, to);
        p = factory.createAlgo(qGraph, opts).calcPath(from.getClosestNode(), to.getClosestNode());
        assertEquals(Helper.createTList(13, 0, 1, 2, 11, 7, 10, 12), p.calcNodes());
        assertEquals(37009621, p.getTime());
        assertEquals(616827, p.getDistance(), 1);
        assertEquals(493462, p.getWeight(), 1);
    }

    // 0-1-2
    // |\| |
    // 3 4-11
    // | | |
    // 5-6-7
    // | |\|
    // 8-9-10
    Graph initEleGraph( Graph g )
    {
        g.edge(0, 1, 10, true);
        g.edge(0, 4, 12, true);
        g.edge(0, 3, 5, true);
        g.edge(1, 2, 10, true);
        g.edge(1, 4, 5, true);
        g.edge(3, 5, 5, false);
        g.edge(5, 6, 10, true);
        g.edge(5, 8, 10, true);
        g.edge(6, 4, 5, true);
        g.edge(6, 7, 10, true);
        g.edge(6, 10, 12, true);
        g.edge(6, 9, 12, true);
        g.edge(2, 11, 5, false);
        g.edge(4, 11, 10, true);
        g.edge(7, 11, 5, true);
        g.edge(7, 10, 5, true);
        g.edge(8, 9, 10, false);
        g.edge(9, 8, 9, false);
        g.edge(10, 9, 10, false);
        updateDistancesFor(g, 0, 3, 0);
        updateDistancesFor(g, 3, 2.5, 0);
        updateDistancesFor(g, 5, 1, 0);
        updateDistancesFor(g, 8, 0, 0);
        updateDistancesFor(g, 1, 3, 1);
        updateDistancesFor(g, 4, 2, 1);
        updateDistancesFor(g, 6, 1, 1);
        updateDistancesFor(g, 9, 0, 1);
        updateDistancesFor(g, 2, 3, 2);
        updateDistancesFor(g, 11, 2, 2);
        updateDistancesFor(g, 7, 1, 2);
        updateDistancesFor(g, 10, 0, 2);
        return g;
    }

    public static Graph initGraphWeightLimit( Graph g )
    {
        //      0----1
        //     /     |
        //    7--    |
        //   /   |   |
        //   6---5   |
        //   |   |   |
        //   4---3---2

        g.edge(0, 1, 1, true);
        g.edge(1, 2, 1, true);

        g.edge(3, 2, 1, true);
        g.edge(3, 5, 1, true);
        g.edge(5, 7, 1, true);
        g.edge(3, 4, 1, true);
        g.edge(4, 6, 1, true);
        g.edge(6, 7, 1, true);
        g.edge(6, 5, 1, true);
        g.edge(0, 7, 1, true);
        return g;
    }

    public Graph getMatrixGraph()
    {
        return getMatrixAlikeGraph();
    }

    public static Graph getMatrixAlikeGraph()
    {
        if (matrixGraph == null)
            matrixGraph = createMatrixAlikeGraph();
        return matrixGraph;
    }

    private static Graph createMatrixAlikeGraph()
    {
        int WIDTH = 10;
        int HEIGHT = 15;
        Graph tmpGraph = new GraphBuilder(encodingManager).create();
        int[][] matrix = new int[WIDTH][HEIGHT];
        int counter = 0;
        Random rand = new Random(12);
        boolean print = false;
        for (int h = 0; h < HEIGHT; h++)
        {
            if (print)
            {
                for (int w = 0; w < WIDTH; w++)
                {
                    System.out.print(" |\t           ");
                }
                System.out.println();
            }

            for (int w = 0; w < WIDTH; w++)
            {
                matrix[w][h] = counter++;
                if (h > 0)
                {
                    float dist = 5 + Math.abs(rand.nextInt(5));
                    if (print)
                        System.out.print(" " + (int) dist + "\t           ");

                    tmpGraph.edge(matrix[w][h], matrix[w][h - 1], dist, true);
                }
            }
            if (print)
            {
                System.out.println();
                if (h > 0)
                {
                    for (int w = 0; w < WIDTH; w++)
                    {
                        System.out.print(" |\t           ");
                    }
                    System.out.println();
                }
            }

            for (int w = 0; w < WIDTH; w++)
            {
                if (w > 0)
                {
                    float dist = 5 + Math.abs(rand.nextInt(5));
                    if (print)
                        System.out.print("-- " + (int) dist + "\t-- ");
                    tmpGraph.edge(matrix[w][h], matrix[w - 1][h], dist, true);
                }
                if (print)
                    System.out.print("(" + matrix[w][h] + ")\t");
            }
            if (print)
                System.out.println();
        }

        return tmpGraph;
    }
}


File: core/src/test/java/com/graphhopper/routing/DijkstraBidirectionRefTest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing;

import com.graphhopper.routing.util.*;

import java.util.Arrays;
import java.util.Collection;

import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;
import org.junit.runners.Parameterized.Parameters;

import com.graphhopper.storage.Graph;

/**
 * @author Peter Karich
 */
@RunWith(Parameterized.class)
public class DijkstraBidirectionRefTest extends AbstractRoutingAlgorithmTester
{
    /**
     * Runs the same test with each of the supported traversal modes
     */
    @Parameters(name = "{0}")
    public static Collection<Object[]> configs()
    {
        return Arrays.asList(new Object[][]
                {
                        {TraversalMode.NODE_BASED},
                        {TraversalMode.EDGE_BASED_1DIR},
                        {TraversalMode.EDGE_BASED_2DIR},
                        {TraversalMode.EDGE_BASED_2DIR_UTURN}
                });
    }

    private final TraversalMode traversalMode;

    public DijkstraBidirectionRefTest( TraversalMode tMode )
    {
        this.traversalMode = tMode;
    }

    @Override
    public RoutingAlgorithmFactory createFactory( Graph prepareGraph, AlgorithmOptions prepareOpts )
    {
        return new RoutingAlgorithmFactory()
        {
            @Override
            public RoutingAlgorithm createAlgo( Graph g, AlgorithmOptions opts )
            {
                return new DijkstraBidirectionRef(g, opts.getFlagEncoder(), opts.getWeighting(), traversalMode);
            }
        };
    }
}


File: core/src/test/java/com/graphhopper/routing/DijkstraOneToManyTest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing;

import com.graphhopper.routing.util.*;
import com.graphhopper.storage.Graph;
import com.graphhopper.storage.GraphBuilder;
import com.graphhopper.util.EdgeIteratorState;
import com.graphhopper.util.Helper;

import java.util.Arrays;
import java.util.Collection;

import static org.junit.Assert.*;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;
import org.junit.runners.Parameterized.Parameters;

/**
 * @author Peter Karich
 */
@RunWith(Parameterized.class)
public class DijkstraOneToManyTest extends AbstractRoutingAlgorithmTester
{
    /**
     * Runs the same test with each of the supported traversal modes
     */
    @Parameters(name = "{0}")
    public static Collection<Object[]> configs()
    {
        return Arrays.asList(new Object[][]
                {
                        {
                                TraversalMode.NODE_BASED
                        },
//            TODO { TraversalMode.EDGE_BASED_1DIR },
//            TODO { TraversalMode.EDGE_BASED_2DIR },
//            TODO { TraversalMode.EDGE_BASED_2DIR_UTURN }
                });
    }

    private final TraversalMode traversalMode;

    public DijkstraOneToManyTest( TraversalMode tMode )
    {
        this.traversalMode = tMode;
    }

    @Override
    public RoutingAlgorithmFactory createFactory( Graph prepareGraph, AlgorithmOptions prepareOpts )
    {
        return new RoutingAlgorithmFactory()
        {
            @Override
            public RoutingAlgorithm createAlgo( Graph g, AlgorithmOptions opts )
            {
                return new DijkstraOneToMany(g, opts.getFlagEncoder(), opts.getWeighting(), traversalMode);
            }
        };
    }

    @Override
    public void testViaEdges_BiGraph()
    {
        // calcPath with QueryResult not supported
    }

    @Override
    public void testViaEdges_SpecialCases()
    {
        // calcPath with QueryResult not supported
    }

    @Override
    public void testViaEdges_FromEqualsTo()
    {
        // calcPath with QueryResult not supported
    }

    @Override
    public void testViaEdges_WithCoordinates()
    {
        // calcPath with QueryResult not supported
    }

    @Override
    public void testQueryGraphAndFastest()
    {
        // calcPath with QueryResult not supported
    }

    @Override
    public void testTwoWeightsPerEdge2()
    {
        // calcPath with QueryResult not supported
    }

    @Test
    public void testIssue182()
    {
        RoutingAlgorithm algo = createAlgo(initGraph(createGraph(false)));
        Path p = algo.calcPath(0, 8);
        assertEquals(Helper.createTList(0, 7, 8), p.calcNodes());

        // expand SPT
        p = algo.calcPath(0, 10);
        assertEquals(Helper.createTList(0, 1, 2, 3, 4, 10), p.calcNodes());
    }

    @Test
    public void testIssue239_and362()
    {
        Graph g = createGraph(false);
        g.edge(0, 1, 1, true);
        g.edge(1, 2, 1, true);
        g.edge(2, 0, 1, true);

        g.edge(4, 5, 1, true);
        g.edge(5, 6, 1, true);
        g.edge(6, 4, 1, true);

        DijkstraOneToMany algo = (DijkstraOneToMany) createAlgo(g);
        assertEquals(-1, algo.findEndNode(0, 4));
        assertEquals(-1, algo.findEndNode(0, 4));

        assertEquals(1, algo.findEndNode(0, 1));
        assertEquals(1, algo.findEndNode(0, 1));
    }

    @Test
    public void testUseCache()
    {
        RoutingAlgorithm algo = createAlgo(createTestGraph());
        Path p = algo.calcPath(0, 4);
        assertEquals(Helper.createTList(0, 4), p.calcNodes());

        // expand SPT
        p = algo.calcPath(0, 7);
        assertEquals(Helper.createTList(0, 4, 5, 7), p.calcNodes());

        // use SPT
        p = algo.calcPath(0, 2);
        assertEquals(Helper.createTList(0, 1, 2), p.calcNodes());
    }

    @Test
    public void testDifferentEdgeFilter()
    {
        Graph g = new GraphBuilder(encodingManager).levelGraphCreate();
        g.edge(4, 3, 10, true);
        g.edge(3, 6, 10, true);

        g.edge(4, 5, 10, true);
        g.edge(5, 6, 10, true);

        DijkstraOneToMany algo = (DijkstraOneToMany) createAlgo(g);
        algo.setEdgeFilter(new EdgeFilter()
        {
            @Override
            public boolean accept( EdgeIteratorState iter )
            {
                return iter.getAdjNode() != 5;
            }
        });
        Path p = algo.calcPath(4, 6);
        assertEquals(Helper.createTList(4, 3, 6), p.calcNodes());

        // important call!
        algo.clear();
        algo.setEdgeFilter(new EdgeFilter()
        {
            @Override
            public boolean accept( EdgeIteratorState iter )
            {
                return iter.getAdjNode() != 3;
            }
        });
        p = algo.calcPath(4, 6);
        assertEquals(Helper.createTList(4, 5, 6), p.calcNodes());
    }

    private Graph initGraph( Graph g )
    {
        // 0-1-2-3-4
        // |       /
        // 7-10----
        // \-8
        g.edge(0, 1, 1, true);
        g.edge(1, 2, 1, true);
        g.edge(2, 3, 1, true);
        g.edge(3, 4, 1, true);
        g.edge(4, 10, 1, true);

        g.edge(0, 7, 1, true);
        g.edge(7, 8, 1, true);
        g.edge(7, 10, 10, true);
        return g;
    }
}


File: core/src/test/java/com/graphhopper/routing/DijkstraTest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing;

import com.graphhopper.routing.util.*;

import java.util.Arrays;
import java.util.Collection;

import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;
import org.junit.runners.Parameterized.Parameters;

import com.graphhopper.storage.Graph;

/**
 * @author Peter Karich
 */
@RunWith(Parameterized.class)
public class DijkstraTest extends AbstractRoutingAlgorithmTester
{
    /**
     * Runs the same test with each of the supported traversal modes
     */
    @Parameters(name = "{0}")
    public static Collection<Object[]> configs()
    {
        return Arrays.asList(new Object[][]
                {
                        {TraversalMode.NODE_BASED},
                        {TraversalMode.EDGE_BASED_1DIR},
                        {TraversalMode.EDGE_BASED_2DIR},
                        {TraversalMode.EDGE_BASED_2DIR_UTURN}
                });
    }

    private final TraversalMode traversalMode;

    public DijkstraTest( TraversalMode tMode )
    {
        this.traversalMode = tMode;
    }

    @Override
    public RoutingAlgorithmFactory createFactory( Graph prepareGraph, AlgorithmOptions prepareOpts )
    {
        return new RoutingAlgorithmFactory()
        {
            @Override
            public RoutingAlgorithm createAlgo( Graph g, AlgorithmOptions opts )
            {
                return new Dijkstra(g, opts.getFlagEncoder(), opts.getWeighting(), traversalMode);
            }
        };
    }
}


File: core/src/test/java/com/graphhopper/routing/EdgeBasedRoutingAlgorithmTest.java
/*
 *  Licensed to Peter Karich under one or more contributor license
 *  agreements. See the NOTICE file distributed with this work for
 *  additional information regarding copyright ownership.
 *
 *  Peter Karich licenses this file to you under the Apache License,
 *  Version 2.0 (the "License"); you may not use this file except
 *  in compliance with the License. You may obtain a copy of the
 *  License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing;

import com.graphhopper.routing.util.*;
import com.graphhopper.storage.Graph;
import com.graphhopper.storage.GraphBuilder;
import com.graphhopper.storage.GraphStorage;
import com.graphhopper.storage.TurnCostExtension;
import com.graphhopper.util.EdgeIteratorState;
import com.graphhopper.util.Helper;

import static org.junit.Assert.*;
import static com.graphhopper.util.GHUtility.*;

import java.util.Arrays;
import java.util.Collection;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;
import org.junit.runners.Parameterized.Parameters;

/**
 * @author Peter Karich
 */
@RunWith(Parameterized.class)
public class EdgeBasedRoutingAlgorithmTest
{
    private FlagEncoder carEncoder;

    EncodingManager createEncodingManager( boolean restrictedOnly )
    {
        if (restrictedOnly)
            carEncoder = new CarFlagEncoder(5, 5, 1);
        else
            // allow for basic costs too
            carEncoder = new CarFlagEncoder(5, 5, 3);
        return new EncodingManager(carEncoder);
    }

    @Parameters(name = "{0}")
    public static Collection<Object[]> configs()
    {
        return Arrays.asList(new Object[][]
                {
                        {AlgorithmOptions.DIJKSTRA},
                        {AlgorithmOptions.DIJKSTRA_BI},
                        {AlgorithmOptions.ASTAR},
                        {AlgorithmOptions.ASTAR_BI}
                        // TODO { AlgorithmOptions.DIJKSTRA_ONE_TO_MANY }
                });
    }

    private final String algoStr;

    public EdgeBasedRoutingAlgorithmTest( String algo )
    {
        this.algoStr = algo;
    }

    public RoutingAlgorithm createAlgo( Graph g, AlgorithmOptions opts )
    {
        opts = AlgorithmOptions.start(opts).algorithm(algoStr).build();
        return new RoutingAlgorithmFactorySimple().createAlgo(g, opts);
    }

    protected GraphStorage createGraph( EncodingManager em )
    {
        return new GraphBuilder(em).create();
    }

    // 0---1
    // |   /
    // 2--3--4
    // |  |  |
    // 5--6--7
    public static void initGraph( Graph g )
    {
        g.edge(0, 1, 3, true);
        g.edge(0, 2, 1, true);
        g.edge(1, 3, 1, true);
        g.edge(2, 3, 1, true);
        g.edge(3, 4, 1, true);
        g.edge(2, 5, .5, true);
        g.edge(3, 6, 1, true);
        g.edge(4, 7, 1, true);
        g.edge(5, 6, 1, true);
        g.edge(6, 7, 1, true);
    }

    private void initTurnRestrictions( Graph g, TurnCostExtension tcs, TurnCostEncoder tEncoder )
    {
        long tflags = tEncoder.getTurnFlags(true, 0);

        // only forward from 2-3 to 3-4 => limit 2,3->3,6 and 2,3->3,1
        tcs.addTurnInfo(getEdge(g, 2, 3).getEdge(), 3, getEdge(g, 3, 6).getEdge(), tflags);
        tcs.addTurnInfo(getEdge(g, 2, 3).getEdge(), 3, getEdge(g, 3, 1).getEdge(), tflags);

        // only right   from 5-2 to 2-3 => limit 5,2->2,0
        tcs.addTurnInfo(getEdge(g, 5, 2).getEdge(), 2, getEdge(g, 2, 0).getEdge(), tflags);

        // only right   from 7-6 to 6-3 => limit 7,6->6,5
        tcs.addTurnInfo(getEdge(g, 7, 6).getEdge(), 6, getEdge(g, 6, 5).getEdge(), tflags);

        // no 5-6 to 6-3
        tcs.addTurnInfo(getEdge(g, 5, 6).getEdge(), 6, getEdge(g, 6, 3).getEdge(), tflags);
        // no 4-3 to 3-1
        tcs.addTurnInfo(getEdge(g, 4, 3).getEdge(), 3, getEdge(g, 3, 1).getEdge(), tflags);
        // no 4-3 to 3-2
        tcs.addTurnInfo(getEdge(g, 4, 3).getEdge(), 3, getEdge(g, 3, 2).getEdge(), tflags);

        // no u-turn at 6-7
        tcs.addTurnInfo(getEdge(g, 6, 7).getEdge(), 7, getEdge(g, 7, 6).getEdge(), tflags);

        // no u-turn at 3-6
        tcs.addTurnInfo(getEdge(g, 3, 6).getEdge(), 6, getEdge(g, 6, 3).getEdge(), tflags);
    }

    Weighting createWeighting( FlagEncoder encoder, TurnCostExtension tcs, double turnCosts )
    {
        return new TurnWeighting(new FastestWeighting(encoder), encoder, tcs).setDefaultUTurnCost(turnCosts);
    }

    @Test
    public void testBasicTurnRestriction()
    {
        GraphStorage g = createGraph(createEncodingManager(true));
        initGraph(g);
        TurnCostExtension tcs = (TurnCostExtension) g.getExtension();
        initTurnRestrictions(g, tcs, carEncoder);
        Path p = createAlgo(g, AlgorithmOptions.start().
                flagEncoder(carEncoder).
                weighting(createWeighting(carEncoder, tcs, 40)).
                traversalMode(TraversalMode.EDGE_BASED_2DIR).build()).
                calcPath(5, 1);
        assertEquals(Helper.createTList(5, 2, 3, 4, 7, 6, 3, 1), p.calcNodes());

        // test 7-6-5 and reverse
        p = createAlgo(g, AlgorithmOptions.start().
                flagEncoder(carEncoder).
                weighting(createWeighting(carEncoder, tcs, 40)).
                traversalMode(TraversalMode.EDGE_BASED_1DIR).build()).
                calcPath(5, 7);
        assertEquals(Helper.createTList(5, 6, 7), p.calcNodes());

        p = createAlgo(g, AlgorithmOptions.start().
                flagEncoder(carEncoder).
                weighting(createWeighting(carEncoder, tcs, 40)).
                traversalMode(TraversalMode.EDGE_BASED_1DIR).build()).
                calcPath(7, 5);
        assertEquals(Helper.createTList(7, 6, 3, 2, 5), p.calcNodes());
    }

    @Test
    public void testUTurns()
    {
        GraphStorage g = createGraph(createEncodingManager(true));
        initGraph(g);
        TurnCostExtension tcs = (TurnCostExtension) g.getExtension();

        long tflags = carEncoder.getTurnFlags(true, 0);

        // force u-turn via lowering the cost for it
        EdgeIteratorState e3_6 = getEdge(g, 3, 6);
        e3_6.setDistance(0.1);
        getEdge(g, 3, 2).setDistance(864);
        getEdge(g, 1, 0).setDistance(864);

        tcs.addTurnInfo(getEdge(g, 7, 6).getEdge(), 6, getEdge(g, 6, 5).getEdge(), tflags);
        tcs.addTurnInfo(getEdge(g, 4, 3).getEdge(), 3, e3_6.getEdge(), tflags);
        AlgorithmOptions opts = AlgorithmOptions.start().
                flagEncoder(carEncoder).
                weighting(createWeighting(carEncoder, tcs, 50)).
                traversalMode(TraversalMode.EDGE_BASED_2DIR_UTURN).build();
        Path p = createAlgo(g, opts).calcPath(7, 5);

        assertEquals(Helper.createTList(7, 6, 3, 6, 5), p.calcNodes());

        // no u-turn for 6-3
        opts = AlgorithmOptions.start().
                flagEncoder(carEncoder).
                weighting(createWeighting(carEncoder, tcs, 100)).
                traversalMode(TraversalMode.EDGE_BASED_2DIR_UTURN).build();
        tcs.addTurnInfo(getEdge(g, 6, 3).getEdge(), 3, getEdge(g, 3, 6).getEdge(), tflags);
        p = createAlgo(g, opts).calcPath(7, 5);

        assertEquals(Helper.createTList(7, 6, 3, 2, 5), p.calcNodes());
    }

    @Test
    public void testBasicTurnCosts()
    {
        GraphStorage g = createGraph(createEncodingManager(false));
        initGraph(g);
        TurnCostExtension tcs = (TurnCostExtension) g.getExtension();
        Path p = createAlgo(g, AlgorithmOptions.start().
                flagEncoder(carEncoder).
                weighting(createWeighting(carEncoder, tcs, 40)).
                traversalMode(TraversalMode.EDGE_BASED_1DIR).build()).
                calcPath(5, 1);

        // no restriction and costs
        EdgeIteratorState e3_6 = getEdge(g, 5, 6);
        e3_6.setDistance(2);
        assertEquals(Helper.createTList(5, 2, 3, 1), p.calcNodes());

        // now introduce some turn costs
        long tflags = carEncoder.getTurnFlags(false, 2);
        tcs.addTurnInfo(getEdge(g, 5, 2).getEdge(), 2, getEdge(g, 2, 3).getEdge(), tflags);

        p = createAlgo(g, AlgorithmOptions.start().
                flagEncoder(carEncoder).
                weighting(createWeighting(carEncoder, tcs, 40)).
                traversalMode(TraversalMode.EDGE_BASED_1DIR).build()).
                calcPath(5, 1);
        assertEquals(Helper.createTList(5, 6, 3, 1), p.calcNodes());
    }
}


File: core/src/test/java/com/graphhopper/routing/PathTest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing;

import com.graphhopper.routing.util.*;
import com.graphhopper.storage.*;
import com.graphhopper.util.Helper;

import static com.graphhopper.storage.AbstractGraphStorageTester.*;

import com.graphhopper.util.EdgeIteratorState;
import com.graphhopper.util.Instruction;
import com.graphhopper.util.InstructionList;
import com.graphhopper.storage.EdgeEntry;
import com.graphhopper.util.*;

import java.util.*;

import org.junit.Test;

import static org.junit.Assert.*;

/**
 * @author Peter Karich
 */
public class PathTest
{
    private final FlagEncoder encoder = new CarFlagEncoder();
    private final EncodingManager carManager = new EncodingManager(encoder);
    private final EncodingManager mixedEncoders = new EncodingManager(
            new CarFlagEncoder(), new FootFlagEncoder(), new BikeFlagEncoder());
    private final TranslationMap trMap = TranslationMapTest.SINGLETON;
    private final Translation tr = trMap.getWithFallBack(Locale.US);
    private final AngleCalc ac = new AngleCalc();
    private final RoundaboutGraph roundaboutGraph = new RoundaboutGraph();

    @Test
    public void testFound()
    {
        GraphStorage g = new GraphBuilder(carManager).create();
        Path p = new Path(g, encoder);
        assertFalse(p.isFound());
        assertEquals(0, p.getDistance(), 1e-7);
        assertEquals(0, p.calcNodes().size());
        g.close();
    }

    @Test
    public void testTime()
    {
        FlagEncoder tmpEnc = new Bike2WeightFlagEncoder();
        GraphStorage g = new GraphBuilder(new EncodingManager(tmpEnc)).create();
        Path p = new Path(g, tmpEnc);
        long flags = tmpEnc.setSpeed(tmpEnc.setReverseSpeed(tmpEnc.setAccess(0, true, true), 10), 15);
        assertEquals(375 * 60 * 1000, p.calcMillis(100000, flags, false));
        assertEquals(600 * 60 * 1000, p.calcMillis(100000, flags, true));

        g.close();
    }

    @Test
    public void testWayList()
    {
        GraphStorage g = new GraphBuilder(carManager).create();
        NodeAccess na = g.getNodeAccess();
        na.setNode(0, 0.0, 0.1);
        na.setNode(1, 1.0, 0.1);
        na.setNode(2, 2.0, 0.1);

        EdgeIteratorState edge1 = g.edge(0, 1).setDistance(1000).setFlags(encoder.setProperties(10, true, true));
        edge1.setWayGeometry(Helper.createPointList(8, 1, 9, 1));
        EdgeIteratorState edge2 = g.edge(2, 1).setDistance(2000).setFlags(encoder.setProperties(50, true, true));
        edge2.setWayGeometry(Helper.createPointList(11, 1, 10, 1));

        Path path = new Path(g, encoder);
        EdgeEntry e1 = new EdgeEntry(edge2.getEdge(), 2, 1);
        e1.parent = new EdgeEntry(edge1.getEdge(), 1, 1);
        e1.parent.parent = new EdgeEntry(-1, 0, 1);
        path.setEdgeEntry(e1);
        path.extract();
        // 0-1-2
        assertPList(Helper.createPointList(0, 0.1, 8, 1, 9, 1, 1, 0.1, 10, 1, 11, 1, 2, 0.1), path.calcPoints());
        InstructionList instr = path.calcInstructions(tr);
        List<Map<String, Object>> res = instr.createJson();
        Map<String, Object> tmp = res.get(0);
        assertEquals(3000.0, tmp.get("distance"));
        assertEquals(504000L, tmp.get("time"));
        assertEquals("Continue", tmp.get("text"));
        assertEquals("[0, 6]", tmp.get("interval").toString());

        tmp = res.get(1);
        assertEquals(0.0, tmp.get("distance"));
        assertEquals(0L, tmp.get("time"));
        assertEquals("Finish!", tmp.get("text"));
        assertEquals("[6, 6]", tmp.get("interval").toString());
        int lastIndex = (Integer) ((List) res.get(res.size() - 1).get("interval")).get(0);
        assertEquals(path.calcPoints().size() - 1, lastIndex);

        // force minor change for instructions
        edge2.setName("2");
        path = new Path(g, encoder);
        e1 = new EdgeEntry(edge2.getEdge(), 2, 1);
        e1.parent = new EdgeEntry(edge1.getEdge(), 1, 1);
        e1.parent.parent = new EdgeEntry(-1, 0, 1);
        path.setEdgeEntry(e1);
        path.extract();
        instr = path.calcInstructions(tr);
        res = instr.createJson();

        tmp = res.get(0);
        assertEquals(1000.0, tmp.get("distance"));
        assertEquals(360000L, tmp.get("time"));
        assertEquals("Continue", tmp.get("text"));
        assertEquals("[0, 3]", tmp.get("interval").toString());

        tmp = res.get(1);
        assertEquals(2000.0, tmp.get("distance"));
        assertEquals(144000L, tmp.get("time"));
        assertEquals("Turn sharp right onto 2", tmp.get("text"));
        assertEquals("[3, 6]", tmp.get("interval").toString());
        lastIndex = (Integer) ((List) res.get(res.size() - 1).get("interval")).get(0);
        assertEquals(path.calcPoints().size() - 1, lastIndex);

        // now reverse order
        path = new Path(g, encoder);
        e1 = new EdgeEntry(edge1.getEdge(), 0, 1);
        e1.parent = new EdgeEntry(edge2.getEdge(), 1, 1);
        e1.parent.parent = new EdgeEntry(-1, 2, 1);
        path.setEdgeEntry(e1);
        path.extract();
        // 2-1-0
        assertPList(Helper.createPointList(2, 0.1, 11, 1, 10, 1, 1, 0.1, 9, 1, 8, 1, 0, 0.1), path.calcPoints());

        instr = path.calcInstructions(tr);
        res = instr.createJson();
        tmp = res.get(0);
        assertEquals(2000.0, tmp.get("distance"));
        assertEquals(144000L, tmp.get("time"));
        assertEquals("Continue onto 2", tmp.get("text"));
        assertEquals("[0, 3]", tmp.get("interval").toString());

        tmp = res.get(1);
        assertEquals(1000.0, tmp.get("distance"));
        assertEquals(360000L, tmp.get("time"));
        assertEquals("Turn sharp left", tmp.get("text"));
        assertEquals("[3, 6]", tmp.get("interval").toString());
        lastIndex = (Integer) ((List) res.get(res.size() - 1).get("interval")).get(0);
        assertEquals(path.calcPoints().size() - 1, lastIndex);
    }

    @Test
    public void testFindInstruction()
    {
        Graph g = new GraphBuilder(carManager).create();
        NodeAccess na = g.getNodeAccess();
        na.setNode(0, 0.0, 0.0);
        na.setNode(1, 5.0, 0.0);
        na.setNode(2, 5.0, 0.5);
        na.setNode(3, 10.0, 0.5);
        na.setNode(4, 7.5, 0.25);

        EdgeIteratorState edge1 = g.edge(0, 1).setDistance(1000).setFlags(encoder.setProperties(50, true, true));
        edge1.setWayGeometry(Helper.createPointList());
        edge1.setName("Street 1");
        EdgeIteratorState edge2 = g.edge(1, 2).setDistance(1000).setFlags(encoder.setProperties(50, true, true));
        edge2.setWayGeometry(Helper.createPointList());
        edge2.setName("Street 2");
        EdgeIteratorState edge3 = g.edge(2, 3).setDistance(1000).setFlags(encoder.setProperties(50, true, true));
        edge3.setWayGeometry(Helper.createPointList());
        edge3.setName("Street 3");
        EdgeIteratorState edge4 = g.edge(3, 4).setDistance(500).setFlags(encoder.setProperties(50, true, true));
        edge4.setWayGeometry(Helper.createPointList());
        edge4.setName("Street 4");

        Path path = new Path(g, encoder);
        EdgeEntry e1 = new EdgeEntry(edge4.getEdge(), 4, 1);
        e1.parent = new EdgeEntry(edge3.getEdge(), 3, 1);
        e1.parent.parent = new EdgeEntry(edge2.getEdge(), 2, 1);
        e1.parent.parent.parent = new EdgeEntry(edge1.getEdge(), 1, 1);
        e1.parent.parent.parent.parent = new EdgeEntry(-1, 0, 1);
        path.setEdgeEntry(e1);
        path.extract();

        InstructionList il = path.calcInstructions(tr);
        Instruction nextInstr0 = il.find(-0.001, 0.0, 1000);
        assertEquals(Instruction.CONTINUE_ON_STREET, nextInstr0.getSign());

        Instruction nextInstr1 = il.find(0.001, 0.001, 1000);
        assertEquals(Instruction.TURN_RIGHT, nextInstr1.getSign());

        Instruction nextInstr2 = il.find(5.0, 0.004, 1000);
        assertEquals(Instruction.TURN_LEFT, nextInstr2.getSign());

        Instruction nextInstr3 = il.find(9.99, 0.503, 1000);
        assertEquals(Instruction.TURN_SHARP_LEFT, nextInstr3.getSign());

        // a bit far away ...
        Instruction nextInstr4 = il.find(7.40, 0.25, 20000);
        assertEquals(Instruction.FINISH, nextInstr4.getSign());

        // too far away
        assertNull(il.find(50.8, 50.25, 1000));
    }

    private class RoundaboutGraph
    {
        private EdgeIteratorState edge3to6, edge3to9;
        boolean clockwise = false;
        final public Graph g = new GraphBuilder(mixedEncoders).create();
        final public NodeAccess na = g.getNodeAccess();
        List<EdgeIteratorState> roundaboutEdges = new LinkedList<EdgeIteratorState>();

        private RoundaboutGraph()
        {
            //                          
            //      8
            //       \
            //         5
            //       /  \
            //  1 - 2    4 - 7
            //       \  /
            //        3
            //        | \
            //        6 [ 9 ] edge 9 is turned off in default mode 

            na.setNode(1, 52.514, 13.348);
            na.setNode(2, 52.514, 13.349);
            na.setNode(3, 52.5135, 13.35);
            na.setNode(4, 52.514, 13.351);
            na.setNode(5, 52.5145, 13.351);
            na.setNode(6, 52.513, 13.35);
            na.setNode(7, 52.514, 13.352);
            na.setNode(8, 52.515, 13.351);
            na.setNode(9, 52.513, 13.351);


            EdgeIteratorState tmpEdge;
            tmpEdge = g.edge(1, 2, 5, true).setName("MainStreet");

            // roundabout
            tmpEdge = g.edge(3, 2, 5, false).setName("2-3");
            roundaboutEdges.add(tmpEdge.detach(false));
            tmpEdge = g.edge(4, 3, 5, false).setName("3-4");
            roundaboutEdges.add(tmpEdge.detach(false));
            tmpEdge = g.edge(5, 4, 5, false).setName("4-5");
            roundaboutEdges.add(tmpEdge.detach(false));
            tmpEdge = g.edge(2, 5, 5, false).setName("5-2");
            roundaboutEdges.add(tmpEdge.detach(false));

            tmpEdge = g.edge(4, 7, 5, true).setName("MainStreet");
            tmpEdge = g.edge(5, 8, 5, true).setName("5-8");

            tmpEdge = g.edge(3, 6, 5, true).setName("3-6");
            edge3to6 = tmpEdge.detach(false);

            tmpEdge = g.edge(3, 9, 5, false).setName("3-9");
            edge3to9 = tmpEdge.detach(false);

            setRoundabout(clockwise);
            inverse3to9();

        }

        public void setRoundabout( boolean clockwise )
        {
            for (FlagEncoder encoder : mixedEncoders.fetchEdgeEncoders())
            {
                for (EdgeIteratorState edge : roundaboutEdges)
                {
                    edge.setFlags(encoder.setAccess(edge.getFlags(), clockwise, !clockwise));
                    edge.setFlags(encoder.setBool(edge.getFlags(), encoder.K_ROUNDABOUT, true));
                }
            }
            this.clockwise = clockwise;
        }

        public void inverse3to9()
        {
            for (FlagEncoder encoder : mixedEncoders.fetchEdgeEncoders())
            {
                long flags = edge3to9.getFlags();
                edge3to9.setFlags(encoder.setAccess(flags, !encoder.isForward(flags), false));
            }
        }

        public void inverse3to6()
        {
            for (FlagEncoder encoder : mixedEncoders.fetchEdgeEncoders())
            {
                long flags = edge3to6.getFlags();
                edge3to6.setFlags(encoder.setAccess(flags, !encoder.isForward(flags), true));
            }
        }


        private double getAngle( int n1, int n2, int n3, int n4 )
        {
            double inOrientation = ac.calcOrientation(na.getLat(n1), na.getLon(n1), na.getLat(n2), na.getLon(n2));
            double outOrientation = ac.calcOrientation(na.getLat(n3), na.getLon(n3), na.getLat(n4), na.getLon(n4));
            outOrientation = ac.alignOrientation(inOrientation, outOrientation);
            double delta = (inOrientation - outOrientation);
            delta = clockwise ? (Math.PI + delta) : -1 * (Math.PI - delta);
            return delta;
        }
    }

    /**
     * Test roundabout instructions for different profiles
     */
    @Test
    public void testCalcInstructionsRoundabout()
    {
        for (FlagEncoder encoder : mixedEncoders.fetchEdgeEncoders())
        {
            Path p = new Dijkstra(roundaboutGraph.g, encoder, new ShortestWeighting(), TraversalMode.NODE_BASED)
                    .calcPath(1, 8);
            InstructionList wayList = p.calcInstructions(tr);
            // Test instructions
            List<String> tmpList = pick("text", wayList.createJson());
            assertEquals(Arrays.asList("Continue onto MainStreet",
                            "At roundabout, take exit 3 onto 5-8",
                            "Finish!"),
                    tmpList);
            // Test Radian
            double delta = roundaboutGraph.getAngle(1, 2, 5, 8);
            RoundaboutInstruction instr = (RoundaboutInstruction) wayList.get(1);
            assertEquals(delta, instr.getRadian(), 0.01);

            // case of continuing a street through a roundabout
            p = new Dijkstra(roundaboutGraph.g, encoder, new ShortestWeighting(), TraversalMode.NODE_BASED).calcPath(1, 7);
            wayList = p.calcInstructions(tr);
            tmpList = pick("text", wayList.createJson());
            assertEquals(Arrays.asList("Continue onto MainStreet",
                            "At roundabout, take exit 2 onto MainStreet",
                            "Finish!"),
                    tmpList);
            // Test Radian
            delta = roundaboutGraph.getAngle(1, 2, 4, 7);
            instr = (RoundaboutInstruction) wayList.get(1);
            assertEquals(delta, instr.getRadian(), 0.01);
        }
    }

    /**
     * case starting in Roundabout
     */
    @Test
    public void testCalcInstructionsRoundaboutBegin()
    {
        Path p = new Dijkstra(roundaboutGraph.g, encoder, new ShortestWeighting(), TraversalMode.NODE_BASED)
                .calcPath(2, 8);
        InstructionList wayList = p.calcInstructions(tr);
        List<String> tmpList = pick("text", wayList.createJson());
        assertEquals(Arrays.asList("At roundabout, take exit 3 onto 5-8",
                        "Finish!"),
                tmpList);
    }

    /**
     * case with one node being containig already exit
     */
    @Test
    public void testCalcInstructionsRoundaboutDirectExit()
    {
        roundaboutGraph.inverse3to9();
        Path p = new Dijkstra(roundaboutGraph.g, encoder, new ShortestWeighting(), TraversalMode.NODE_BASED)
                .calcPath(6, 8);
        InstructionList wayList = p.calcInstructions(tr);
        List<String> tmpList = pick("text", wayList.createJson());
        assertEquals(Arrays.asList("Continue onto 3-6",
                        "At roundabout, take exit 3 onto 5-8",
                        "Finish!"),
                tmpList);
        roundaboutGraph.inverse3to9();
    }

    /**
     * case with one edge being not an exit
     */
    @Test
    public void testCalcInstructionsRoundabout2()
    {
        roundaboutGraph.inverse3to6();
        Path p = new Dijkstra(roundaboutGraph.g, encoder, new ShortestWeighting(), TraversalMode.NODE_BASED)
                .calcPath(1, 8);
        InstructionList wayList = p.calcInstructions(tr);
        List<String> tmpList = pick("text", wayList.createJson());
        assertEquals(Arrays.asList("Continue onto MainStreet",
                        "At roundabout, take exit 2 onto 5-8",
                        "Finish!"),
                tmpList);
        // Test Radian
        double delta = roundaboutGraph.getAngle(1, 2, 5, 8);
        RoundaboutInstruction instr = (RoundaboutInstruction) wayList.get(1);
        assertEquals(delta, instr.getRadian(), 0.01);
        roundaboutGraph.inverse3to6();

    }


    /**
     * see https://github.com/graphhopper/graphhopper/issues/353
     */
    @Test
    public void testCalcInstructionsRoundaboutIssue353()
    {
        final Graph g = new GraphBuilder(carManager).create();
        final NodeAccess na = g.getNodeAccess();


        //
        //          8
        //           \
        //            5
        //           /  \
        //  11- 1 - 2    4 - 7
        //      |     \  /
        //      10 -9 -3
        //       \    |
        //        --- 6

        na.setNode(1, 52.514, 13.348);
        na.setNode(2, 52.514, 13.349);
        na.setNode(3, 52.5135, 13.35);
        na.setNode(4, 52.514, 13.351);
        na.setNode(5, 52.5145, 13.351);
        na.setNode(6, 52.513, 13.35);
        na.setNode(7, 52.514, 13.352);
        na.setNode(8, 52.515, 13.351);

        // Sidelane
        na.setNode(9, 52.5135, 13.349);
        na.setNode(10, 52.5135, 13.348);
        na.setNode(11, 52.514, 13.347);


        EdgeIteratorState tmpEdge;
        tmpEdge = g.edge(2, 1, 5, false).setName("MainStreet");
        tmpEdge = g.edge(1, 11, 5, false).setName("MainStreet");


        // roundabout
        tmpEdge = g.edge(3, 9, 2, false).setName("3-9");
        tmpEdge.setFlags(encoder.setBool(tmpEdge.getFlags(), encoder.K_ROUNDABOUT, true));
        tmpEdge = g.edge(9, 10, 2, false).setName("9-10");
        tmpEdge.setFlags(encoder.setBool(tmpEdge.getFlags(), encoder.K_ROUNDABOUT, true));
        tmpEdge = g.edge(6, 10, 2, false).setName("6-10");
        tmpEdge.setFlags(encoder.setBool(tmpEdge.getFlags(), encoder.K_ROUNDABOUT, true));
        tmpEdge = g.edge(10, 1, 2, false).setName("10-1");
        tmpEdge.setFlags(encoder.setBool(tmpEdge.getFlags(), encoder.K_ROUNDABOUT, true));
        tmpEdge = g.edge(3, 2, 5, false).setName("2-3");
        tmpEdge.setFlags(encoder.setBool(tmpEdge.getFlags(), encoder.K_ROUNDABOUT, true));
        tmpEdge = g.edge(4, 3, 5, false).setName("3-4");
        tmpEdge.setFlags(encoder.setBool(tmpEdge.getFlags(), encoder.K_ROUNDABOUT, true));
        tmpEdge = g.edge(5, 4, 5, false).setName("4-5");
        tmpEdge.setFlags(encoder.setBool(tmpEdge.getFlags(), encoder.K_ROUNDABOUT, true));
        tmpEdge = g.edge(2, 5, 5, false).setName("5-2");
        tmpEdge.setFlags(encoder.setBool(tmpEdge.getFlags(), encoder.K_ROUNDABOUT, true));

        tmpEdge = g.edge(4, 7, 5, true).setName("MainStreet");
        tmpEdge = g.edge(5, 8, 5, true).setName("5-8");
        tmpEdge = g.edge(3, 6, 5, true).setName("3-6");


        Path p = new Dijkstra(g, encoder, new ShortestWeighting(), TraversalMode.NODE_BASED)
                .calcPath(6, 11);
        InstructionList wayList = p.calcInstructions(tr);
        List<String> tmpList = pick("text", wayList.createJson());
        assertEquals(Arrays.asList("At roundabout, take exit 1 onto MainStreet",
                        "Finish!"),
                tmpList);
    }

    /**
     * clockwise roundabout
     */
    @Test
    public void testCalcInstructionsRoundaboutClockwise()
    {

        roundaboutGraph.setRoundabout(true);
        Path p = new Dijkstra(roundaboutGraph.g, encoder, new ShortestWeighting(), TraversalMode.NODE_BASED)
                .calcPath(1, 8);
        InstructionList wayList = p.calcInstructions(tr);
        List<String> tmpList = pick("text", wayList.createJson());
        assertEquals(Arrays.asList("Continue onto MainStreet",
                        "At roundabout, take exit 1 onto 5-8",
                        "Finish!"),
                tmpList);
        // Test Radian
        double delta = roundaboutGraph.getAngle(1, 2, 5, 8);
        RoundaboutInstruction instr = (RoundaboutInstruction) wayList.get(1);
        assertEquals(delta, instr.getRadian(), 0.01);
    }

    List<String> pick( String key, List<Map<String, Object>> instructionJson )
    {
        List<String> list = new ArrayList<String>();

        for (Map<String, Object> json : instructionJson)
        {
            list.add(json.get(key).toString());
        }
        return list;
    }

}


File: core/src/test/java/com/graphhopper/routing/QueryGraphTest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for
 *  additional information regarding copyright ownership.
 *
 *  GraphHopper licenses this file to you under the Apache License,
 *  Version 2.0 (the "License"); you may not use this file except in
 *  compliance with the License. You may obtain a copy of the License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing;

import com.graphhopper.routing.util.*;
import com.graphhopper.storage.*;
import com.graphhopper.storage.index.QueryResult;

import static com.graphhopper.storage.index.QueryResult.Position.*;

import com.graphhopper.util.*;
import com.graphhopper.util.shapes.GHPoint;
import gnu.trove.map.TIntObjectMap;

import java.util.Arrays;

import org.junit.After;
import org.junit.Test;

import static org.junit.Assert.*;

import org.junit.Before;

/**
 * @author Peter Karich
 */
public class QueryGraphTest
{
    private EncodingManager encodingManager;
    private FlagEncoder carEncoder;
    private GraphStorage g;

    @Before
    public void setUp()
    {
        carEncoder = new CarFlagEncoder();
        encodingManager = new EncodingManager(carEncoder);
        g = new GraphHopperStorage(new RAMDirectory(), encodingManager, false).create(100);
    }

    @After
    public void tearDown()
    {
        g.close();
    }

    void initGraph( Graph g )
    {
        //
        //  /*-*\
        // 0     1
        // |
        // 2
        NodeAccess na = g.getNodeAccess();
        na.setNode(0, 1, 0);
        na.setNode(1, 1, 2.5);
        na.setNode(2, 0, 0);
        g.edge(0, 2, 10, true);
        g.edge(0, 1, 10, true).setWayGeometry(Helper.createPointList(1.5, 1, 1.5, 1.5));
    }

    @Test
    public void testOneVirtualNode()
    {
        initGraph(g);
        EdgeExplorer expl = g.createEdgeExplorer();

        // snap directly to tower node => pointList could get of size 1?!?      
        // a)
        EdgeIterator iter = expl.setBaseNode(2);
        iter.next();

        QueryGraph queryGraph = new QueryGraph(g);
        QueryResult res = createLocationResult(1, -1, iter, 0, TOWER);
        queryGraph.lookup(Arrays.asList(res));
        assertEquals(new GHPoint(0, 0), res.getSnappedPoint());

        // b)
        res = createLocationResult(1, -1, iter, 1, TOWER);
        queryGraph = new QueryGraph(g);
        queryGraph.lookup(Arrays.asList(res));
        assertEquals(new GHPoint(1, 0), res.getSnappedPoint());
        // c)
        iter = expl.setBaseNode(1);
        iter.next();
        res = createLocationResult(1.2, 2.7, iter, 0, TOWER);
        queryGraph = new QueryGraph(g);
        queryGraph.lookup(Arrays.asList(res));
        assertEquals(new GHPoint(1, 2.5), res.getSnappedPoint());

        // node number stays
        assertEquals(3, queryGraph.getNodes());

        // snap directly to pillar node
        queryGraph = new QueryGraph(g);
        iter = expl.setBaseNode(1);
        iter.next();
        res = createLocationResult(2, 1.5, iter, 1, PILLAR);
        queryGraph.lookup(Arrays.asList(res));
        assertEquals(new GHPoint(1.5, 1.5), res.getSnappedPoint());
        assertEquals(3, res.getClosestNode());
        assertEquals(4, getPoints(queryGraph, 0, 3).getSize());
        assertEquals(2, getPoints(queryGraph, 3, 1).getSize());

        queryGraph = new QueryGraph(g);
        res = createLocationResult(2, 1.7, iter, 1, PILLAR);
        queryGraph.lookup(Arrays.asList(res));
        assertEquals(new GHPoint(1.5, 1.5), res.getSnappedPoint());
        assertEquals(3, res.getClosestNode());
        assertEquals(4, getPoints(queryGraph, 0, 3).getSize());
        assertEquals(2, getPoints(queryGraph, 3, 1).getSize());

        // snap to edge which has pillar nodes        
        queryGraph = new QueryGraph(g);
        res = createLocationResult(1.5, 2, iter, 0, EDGE);
        queryGraph.lookup(Arrays.asList(res));
        assertEquals(new GHPoint(1.300019, 1.899962), res.getSnappedPoint());
        assertEquals(3, res.getClosestNode());
        assertEquals(4, getPoints(queryGraph, 0, 3).getSize());
        assertEquals(2, getPoints(queryGraph, 3, 1).getSize());

        // snap to edge which has no pillar nodes
        queryGraph = new QueryGraph(g);
        iter = expl.setBaseNode(2);
        iter.next();
        res = createLocationResult(0.5, 0.1, iter, 0, EDGE);
        queryGraph.lookup(Arrays.asList(res));
        assertEquals(new GHPoint(0.5, 0), res.getSnappedPoint());
        assertEquals(3, res.getClosestNode());
        assertEquals(2, getPoints(queryGraph, 0, 3).getSize());
        assertEquals(2, getPoints(queryGraph, 3, 2).getSize());
    }

    @Test
    public void testFillVirtualEdges()
    {
        initGraph(g);
        g.getNodeAccess().setNode(3, 0, 1);
        g.edge(1, 3);

        final int baseNode = 1;
        EdgeIterator iter = g.createEdgeExplorer().setBaseNode(baseNode);
        iter.next();
        QueryResult res1 = createLocationResult(2, 1.7, iter, 1, PILLAR);
        QueryGraph queryGraph = new QueryGraph(g)
        {

            @Override
            void fillVirtualEdges( TIntObjectMap<VirtualEdgeIterator> node2Edge, int towerNode, EdgeExplorer mainExpl )
            {
                super.fillVirtualEdges(node2Edge, towerNode, mainExpl);
                // ignore nodes should include baseNode == 1
                if (towerNode == 3)
                    assertEquals("[3->4]", node2Edge.get(towerNode).toString());
                else if (towerNode == 1)
                    assertEquals("[1->4, 1 1-0]", node2Edge.get(towerNode).toString());
                else
                    throw new IllegalStateException("not allowed " + towerNode);
            }
        };
        queryGraph.lookup(Arrays.asList(res1));
        EdgeIteratorState state = GHUtility.getEdge(queryGraph, 0, 1);
        assertEquals(4, state.fetchWayGeometry(3).size());

        // fetch virtual edge and check way geometry
        state = GHUtility.getEdge(queryGraph, 4, 3);
        assertEquals(2, state.fetchWayGeometry(3).size());
    }

    @Test
    public void testMultipleVirtualNodes()
    {
        initGraph(g);

        // snap to edge which has pillar nodes        
        EdgeIterator iter = g.createEdgeExplorer().setBaseNode(1);
        iter.next();
        QueryResult res1 = createLocationResult(2, 1.7, iter, 1, PILLAR);
        QueryGraph queryGraph = new QueryGraph(g);
        queryGraph.lookup(Arrays.asList(res1));
        assertEquals(new GHPoint(1.5, 1.5), res1.getSnappedPoint());
        assertEquals(3, res1.getClosestNode());
        assertEquals(4, getPoints(queryGraph, 0, 3).getSize());
        PointList pl = getPoints(queryGraph, 3, 1);
        assertEquals(2, pl.getSize());
        assertEquals(new GHPoint(1.5, 1.5), pl.toGHPoint(0));
        assertEquals(new GHPoint(1, 2.5), pl.toGHPoint(1));

        EdgeIteratorState edge = GHUtility.getEdge(queryGraph, 3, 1);
        assertNotNull(queryGraph.getEdgeProps(edge.getEdge(), 3));
        assertNotNull(queryGraph.getEdgeProps(edge.getEdge(), 1));

        edge = GHUtility.getEdge(queryGraph, 3, 0);
        assertNotNull(queryGraph.getEdgeProps(edge.getEdge(), 3));
        assertNotNull(queryGraph.getEdgeProps(edge.getEdge(), 0));

        // snap again => new virtual node on same edge!
        iter = g.createEdgeExplorer().setBaseNode(1);
        iter.next();
        res1 = createLocationResult(2, 1.7, iter, 1, PILLAR);
        QueryResult res2 = createLocationResult(1.5, 2, iter, 0, EDGE);
        queryGraph = new QueryGraph(g);
        queryGraph.lookup(Arrays.asList(res1, res2));
        assertEquals(4, res2.getClosestNode());
        assertEquals(new GHPoint(1.300019, 1.899962), res2.getSnappedPoint());
        assertEquals(3, res1.getClosestNode());
        assertEquals(new GHPoint(1.5, 1.5), res1.getSnappedPoint());

        assertEquals(4, getPoints(queryGraph, 3, 0).getSize());
        assertEquals(2, getPoints(queryGraph, 3, 4).getSize());
        assertEquals(2, getPoints(queryGraph, 4, 1).getSize());
        assertNull(GHUtility.getEdge(queryGraph, 4, 0));
        assertNull(GHUtility.getEdge(queryGraph, 3, 1));
    }

    @Test
    public void testOneWay()
    {
        NodeAccess na = g.getNodeAccess();
        na.setNode(0, 0, 0);
        na.setNode(1, 0, 1);
        g.edge(0, 1, 10, false);

        EdgeIteratorState edge = GHUtility.getEdge(g, 0, 1);
        QueryResult res1 = createLocationResult(0.1, 0.1, edge, 0, EDGE);
        QueryResult res2 = createLocationResult(0.1, 0.9, edge, 0, EDGE);
        QueryGraph queryGraph = new QueryGraph(g);
        queryGraph.lookup(Arrays.asList(res2, res1));
        assertEquals(2, res1.getClosestNode());
        assertEquals(new GHPoint(0, 0.1), res1.getSnappedPoint());
        assertEquals(3, res2.getClosestNode());
        assertEquals(new GHPoint(0, 0.9), res2.getSnappedPoint());

        assertEquals(2, getPoints(queryGraph, 0, 2).getSize());
        assertEquals(2, getPoints(queryGraph, 2, 3).getSize());
        assertEquals(2, getPoints(queryGraph, 3, 1).getSize());
        assertNull(GHUtility.getEdge(queryGraph, 3, 0));
        assertNull(GHUtility.getEdge(queryGraph, 2, 1));
    }

    @Test
    public void testVirtEdges()
    {
        initGraph(g);

        EdgeIterator iter = g.createEdgeExplorer().setBaseNode(0);
        iter.next();

        VirtualEdgeIterator vi = new VirtualEdgeIterator(2);
        vi.add(iter.detach(false));

        assertTrue(vi.next());
    }

    @Test
    public void testUseMeanElevation()
    {
        g.close();
        g = new GraphHopperStorage(new RAMDirectory(), encodingManager, true).create(100);
        NodeAccess na = g.getNodeAccess();
        na.setNode(0, 0, 0, 0);
        na.setNode(1, 0, 0.0001, 20);
        EdgeIteratorState edge = g.edge(0, 1);
        EdgeIteratorState edgeReverse = edge.detach(true);

        DistanceCalc2D distCalc = new DistanceCalc2D();
        QueryResult qr = new QueryResult(0, 0.00005);
        qr.setClosestEdge(edge);
        qr.setWayIndex(0);
        qr.setSnappedPosition(EDGE);
        qr.calcSnappedPoint(distCalc);
        assertEquals(10, qr.getSnappedPoint().getEle(), 1e-1);

        qr = new QueryResult(0, 0.00005);
        qr.setClosestEdge(edgeReverse);
        qr.setWayIndex(0);
        qr.setSnappedPosition(EDGE);
        qr.calcSnappedPoint(distCalc);
        assertEquals(10, qr.getSnappedPoint().getEle(), 1e-1);
    }

    @Test
    public void testLoopStreet_Issue151()
    {
        // do query at x should result in ignoring only the bottom edge 1-3 not the upper one => getNeighbors are 0, 5, 3 and not only 0, 5
        //
        // 0--1--3--4
        //    |  |
        //    x---
        //
        g.edge(0, 1, 10, true);
        g.edge(1, 3, 10, true);
        g.edge(3, 4, 10, true);
        EdgeIteratorState edge = g.edge(1, 3, 20, true).setWayGeometry(Helper.createPointList(-0.001, 0.001, -0.001, 0.002));
        AbstractRoutingAlgorithmTester.updateDistancesFor(g, 0, 0, 0);
        AbstractRoutingAlgorithmTester.updateDistancesFor(g, 1, 0, 0.001);
        AbstractRoutingAlgorithmTester.updateDistancesFor(g, 3, 0, 0.002);
        AbstractRoutingAlgorithmTester.updateDistancesFor(g, 4, 0, 0.003);

        QueryResult qr = new QueryResult(-0.0005, 0.001);
        qr.setClosestEdge(edge);
        qr.setWayIndex(1);
        qr.calcSnappedPoint(new DistanceCalc2D());

        QueryGraph qg = new QueryGraph(g);
        qg.lookup(Arrays.asList(qr));
        EdgeExplorer ee = qg.createEdgeExplorer();

        assertEquals(GHUtility.asSet(0, 5, 3), GHUtility.getNeighbors(ee.setBaseNode(1)));
    }

    @Test
    public void testOneWayLoop_Issue162()
    {
        // do query at x, where edge is oneway
        //
        // |\
        // | x
        // 0<-\
        // |
        // 1        
        NodeAccess na = g.getNodeAccess();
        na.setNode(0, 0, 0);
        na.setNode(1, 0, -0.001);
        g.edge(0, 1, 10, true);
        // in the case of identical nodes the wayGeometry defines the direction!
        EdgeIteratorState edge = g.edge(0, 0).
                setDistance(100).
                setFlags(carEncoder.setProperties(20, true, false)).
                setWayGeometry(Helper.createPointList(0.001, 0, 0, 0.001));

        QueryResult qr = new QueryResult(0.0011, 0.0009);
        qr.setClosestEdge(edge);
        qr.setWayIndex(1);
        qr.calcSnappedPoint(new DistanceCalc2D());

        QueryGraph qg = new QueryGraph(g);
        qg.lookup(Arrays.asList(qr));
        EdgeExplorer ee = qg.createEdgeExplorer();
        assertTrue(qr.getClosestNode() > 1);
        assertEquals(2, GHUtility.count(ee.setBaseNode(qr.getClosestNode())));
        EdgeIterator iter = ee.setBaseNode(qr.getClosestNode());
        iter.next();
        assertTrue(iter.toString(), carEncoder.isForward(iter.getFlags()));
        assertFalse(iter.toString(), carEncoder.isBackward(iter.getFlags()));

        iter.next();
        assertFalse(iter.toString(), carEncoder.isForward(iter.getFlags()));
        assertTrue(iter.toString(), carEncoder.isBackward(iter.getFlags()));
    }

    @Test
    public void testEdgesShareOneNode()
    {
        initGraph(g);

        EdgeIteratorState iter = GHUtility.getEdge(g, 0, 2);
        QueryResult res1 = createLocationResult(0.5, 0, iter, 0, EDGE);
        iter = GHUtility.getEdge(g, 1, 0);
        QueryResult res2 = createLocationResult(1.5, 2, iter, 0, EDGE);
        QueryGraph queryGraph = new QueryGraph(g);
        queryGraph.lookup(Arrays.asList(res1, res2));
        assertEquals(new GHPoint(0.5, 0), res1.getSnappedPoint());
        assertEquals(new GHPoint(1.300019, 1.899962), res2.getSnappedPoint());
        assertNotNull(GHUtility.getEdge(queryGraph, 0, 4));
        assertNotNull(GHUtility.getEdge(queryGraph, 0, 3));
    }

    @Test
    public void testAvoidDuplicateVirtualNodesIfIdentical()
    {
        initGraph(g);

        EdgeIteratorState edgeState = GHUtility.getEdge(g, 0, 2);
        QueryResult res1 = createLocationResult(0.5, 0, edgeState, 0, EDGE);
        QueryResult res2 = createLocationResult(0.5, 0, edgeState, 0, EDGE);
        QueryGraph queryGraph = new QueryGraph(g);
        queryGraph.lookup(Arrays.asList(res1, res2));
        assertEquals(new GHPoint(0.5, 0), res1.getSnappedPoint());
        assertEquals(new GHPoint(0.5, 0), res2.getSnappedPoint());
        assertEquals(3, res1.getClosestNode());
        assertEquals(3, res2.getClosestNode());

        // force skip due to **tower** node snapping in phase 2, but no virtual edges should be created for res1
        edgeState = GHUtility.getEdge(g, 0, 1);
        res1 = createLocationResult(1, 0, edgeState, 0, EDGE);
        // now create virtual edges
        edgeState = GHUtility.getEdge(g, 0, 2);
        res2 = createLocationResult(0.5, 0, edgeState, 0, EDGE);
        queryGraph = new QueryGraph(g);
        queryGraph.lookup(Arrays.asList(res1, res2));
        // make sure only one virtual node was created
        assertEquals(queryGraph.getNodes(), g.getNodes() + 1);
        EdgeIterator iter = queryGraph.createEdgeExplorer().setBaseNode(0);
        assertEquals(GHUtility.asSet(1, 3), GHUtility.getNeighbors(iter));
    }

    @Test
    public void testGetEdgeProps()
    {
        initGraph(g);
        EdgeIteratorState e1 = GHUtility.getEdge(g, 0, 2);
        QueryGraph queryGraph = new QueryGraph(g);
        QueryResult res1 = createLocationResult(0.5, 0, e1, 0, EDGE);
        queryGraph.lookup(Arrays.asList(res1));
        // get virtual edge
        e1 = GHUtility.getEdge(queryGraph, res1.getClosestNode(), 0);
        EdgeIteratorState e2 = queryGraph.getEdgeProps(e1.getEdge(), Integer.MIN_VALUE);
        assertEquals(e1.getEdge(), e2.getEdge());
    }

    PointList getPoints( Graph g, int base, int adj )
    {
        EdgeIteratorState edge = GHUtility.getEdge(g, base, adj);
        if (edge == null)
            throw new IllegalStateException("edge " + base + "-" + adj + " not found");
        return edge.fetchWayGeometry(3);
    }

    public QueryResult createLocationResult( double lat, double lon,
                                             EdgeIteratorState edge, int wayIndex, QueryResult.Position pos )
    {
        if (edge == null)
            throw new IllegalStateException("Specify edge != null");
        QueryResult tmp = new QueryResult(lat, lon);
        tmp.setClosestEdge(edge);
        tmp.setWayIndex(wayIndex);
        tmp.setSnappedPosition(pos);
        tmp.calcSnappedPoint(new DistanceCalcEarth());
        return tmp;
    }

    @Test
    public void testIteration_Issue163()
    {
        EdgeFilter outEdgeFilter = new DefaultEdgeFilter(encodingManager.getEncoder("CAR"), false, true);
        EdgeFilter inEdgeFilter = new DefaultEdgeFilter(encodingManager.getEncoder("CAR"), true, false);
        EdgeExplorer inExplorer = g.createEdgeExplorer(inEdgeFilter);
        EdgeExplorer outExplorer = g.createEdgeExplorer(outEdgeFilter);

        int nodeA = 0;
        int nodeB = 1;

        /* init test graph: one directional edge going from A to B, via virtual nodes C and D
         * 
         *   (C)-(D)
         *  /       \
         * A         B
         */
        g.getNodeAccess().setNode(nodeA, 1, 0);
        g.getNodeAccess().setNode(nodeB, 1, 10);
        g.edge(nodeA, nodeB, 10, false).setWayGeometry(Helper.createPointList(1.5, 3, 1.5, 7));

        // assert the behavior for classic edgeIterator        
        assertEdgeIdsStayingEqual(inExplorer, outExplorer, nodeA, nodeB);

        // setup query results
        EdgeIteratorState it = GHUtility.getEdge(g, nodeA, nodeB);
        QueryResult res1 = createLocationResult(1.5, 3, it, 1, QueryResult.Position.EDGE);
        QueryResult res2 = createLocationResult(1.5, 7, it, 2, QueryResult.Position.EDGE);

        QueryGraph q = new QueryGraph(g);
        q.lookup(Arrays.asList(res1, res2));
        int nodeC = res1.getClosestNode();
        int nodeD = res2.getClosestNode();

        inExplorer = q.createEdgeExplorer(inEdgeFilter);
        outExplorer = q.createEdgeExplorer(outEdgeFilter);

        // assert the same behavior for queryGraph
        assertEdgeIdsStayingEqual(inExplorer, outExplorer, nodeA, nodeC);
        assertEdgeIdsStayingEqual(inExplorer, outExplorer, nodeC, nodeD);
        assertEdgeIdsStayingEqual(inExplorer, outExplorer, nodeD, nodeB);
    }

    private void assertEdgeIdsStayingEqual( EdgeExplorer inExplorer, EdgeExplorer outExplorer, int startNode, int endNode )
    {
        EdgeIterator it = outExplorer.setBaseNode(startNode);
        it.next();
        assertEquals(startNode, it.getBaseNode());
        assertEquals(endNode, it.getAdjNode());
        // we expect the edge id to be the same when exploring in backward direction
        int expectedEdgeId = it.getEdge();
        assertFalse(it.next());

        // backward iteration, edge id should remain the same!!
        it = inExplorer.setBaseNode(endNode);
        it.next();
        assertEquals(endNode, it.getBaseNode());
        assertEquals(startNode, it.getAdjNode());
        assertEquals("The edge id is not the same,", expectedEdgeId, it.getEdge());
        assertFalse(it.next());
    }

    @Test
    public void testTurnCostsProperlyPropagated_Issue282()
    {
        TurnCostExtension turnExt = new TurnCostExtension();
        FlagEncoder encoder = new CarFlagEncoder(5, 5, 15);

        GraphStorage graphWithTurnCosts = new GraphHopperStorage(new RAMDirectory(),
                new EncodingManager(encoder), false, turnExt).
                create(100);
        NodeAccess na = graphWithTurnCosts.getNodeAccess();
        na.setNode(0, .00, .00);
        na.setNode(1, .00, .01);
        na.setNode(2, .01, .01);

        EdgeIteratorState edge0 = graphWithTurnCosts.edge(0, 1, 10, true);
        EdgeIteratorState edge1 = graphWithTurnCosts.edge(2, 1, 10, true);

        QueryGraph qGraph = new QueryGraph(graphWithTurnCosts);
        FastestWeighting weighting = new FastestWeighting(encoder);
        TurnWeighting turnWeighting = new TurnWeighting(weighting, encoder, (TurnCostExtension) qGraph.getExtension());

        assertEquals(0, turnWeighting.calcTurnWeight(edge0.getEdge(), 1, edge1.getEdge()), .1);

        // now use turn costs and QueryGraph
        turnExt.addTurnInfo(edge0.getEdge(), 1, edge1.getEdge(), encoder.getTurnFlags(false, 10));
        assertEquals(10, turnWeighting.calcTurnWeight(edge0.getEdge(), 1, edge1.getEdge()), .1);

        QueryResult res1 = createLocationResult(0.000, 0.005, edge0, 0, QueryResult.Position.EDGE);
        QueryResult res2 = createLocationResult(0.005, 0.010, edge1, 0, QueryResult.Position.EDGE);

        qGraph.lookup(Arrays.asList(res1, res2));

        int fromQueryEdge = GHUtility.getEdge(qGraph, res1.getClosestNode(), 1).getEdge();
        int toQueryEdge = GHUtility.getEdge(qGraph, res2.getClosestNode(), 1).getEdge();

        assertEquals(10, turnWeighting.calcTurnWeight(fromQueryEdge, 1, toQueryEdge), .1);

        graphWithTurnCosts.close();
    }
}


File: core/src/test/java/com/graphhopper/routing/RoutingAlgorithmIT.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing;

import com.graphhopper.routing.util.TestAlgoCollector;
import com.graphhopper.GraphHopper;
import com.graphhopper.reader.PrinctonReader;
import com.graphhopper.reader.dem.SRTMProvider;
import com.graphhopper.routing.ch.PrepareContractionHierarchies;
import com.graphhopper.routing.util.*;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.routing.util.TestAlgoCollector.AlgoHelperEntry;
import com.graphhopper.routing.util.TestAlgoCollector.OneRun;
import com.graphhopper.storage.*;
import com.graphhopper.storage.index.LocationIndex;
import com.graphhopper.storage.index.LocationIndexTree;
import com.graphhopper.storage.index.QueryResult;
import com.graphhopper.util.GHUtility;
import com.graphhopper.util.Helper;
import com.graphhopper.util.StopWatch;

import java.io.File;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.zip.GZIPInputStream;

import static org.junit.Assert.*;

import org.junit.Before;
import org.junit.Test;

/**
 * Try algorithms, indices and graph storages with real data
 * <p/>
 * @author Peter Karich
 */
public class RoutingAlgorithmIT
{
    TestAlgoCollector testCollector;

    @Before
    public void setUp()
    {
        testCollector = new TestAlgoCollector("core integration tests");
    }

    List<OneRun> createMonacoCar()
    {
        List<OneRun> list = new ArrayList<OneRun>();
        list.add(new OneRun(43.730729, 7.42135, 43.727697, 7.419199, 2580, 110));
        list.add(new OneRun(43.727687, 7.418737, 43.74958, 7.436566, 3588, 170));
        list.add(new OneRun(43.728677, 7.41016, 43.739213, 7.4277, 2561, 133));
        list.add(new OneRun(43.733802, 7.413433, 43.739662, 7.424355, 2230, 137));
        list.add(new OneRun(43.730949, 7.412338, 43.739643, 7.424542, 2100, 116));
        list.add(new OneRun(43.727592, 7.419333, 43.727712, 7.419333, 0, 1));

        // same special cases where GPS-exact routing could have problems (same edge and neighbor edges)
        list.add(new OneRun(43.727592, 7.419333, 43.727712, 7.41934, 0, 1));
        // on the same edge and very release
        list.add(new OneRun(43.727592, 7.419333, 43.727712, 7.4193, 3, 2));
        // one way stuff
        list.add(new OneRun(43.729445, 7.415063, 43.728856, 7.41472, 103, 4));
        list.add(new OneRun(43.728856, 7.41472, 43.729445, 7.415063, 320, 11));
        return list;
    }

    @Test
    public void testMonaco()
    {
        Graph g = runAlgo(testCollector, "files/monaco.osm.gz", "target/monaco-gh",
                createMonacoCar(), "CAR", true, "CAR", "shortest", false);

        assertEquals(testCollector.toString(), 0, testCollector.errors.size());

        // When OSM file stays unchanged make static edge and node IDs a requirement
        assertEquals(GHUtility.asSet(9, 111, 182), GHUtility.getNeighbors(g.createEdgeExplorer().setBaseNode(10)));
        assertEquals(GHUtility.asSet(19, 21), GHUtility.getNeighbors(g.createEdgeExplorer().setBaseNode(20)));
        assertEquals(GHUtility.asSet(478, 84, 83), GHUtility.getNeighbors(g.createEdgeExplorer().setBaseNode(480)));

        assertEquals(43.736989, g.getNodeAccess().getLat(10), 1e-6);
        assertEquals(7.429758, g.getNodeAccess().getLon(201), 1e-6);
    }

    @Test
    public void testMonacoMotorcycle()
    {
        List<OneRun> list = new ArrayList<OneRun>();
        list.add(new OneRun(43.730729, 7.42135, 43.727697, 7.419199, 2697, 117));
        list.add(new OneRun(43.727687, 7.418737, 43.74958, 7.436566, 3749, 170));
        list.add(new OneRun(43.728677, 7.41016, 43.739213, 7.4277, 3164, 165));
        list.add(new OneRun(43.733802, 7.413433, 43.739662, 7.424355, 2423, 141));
        list.add(new OneRun(43.730949, 7.412338, 43.739643, 7.424542, 2253, 120));
        list.add(new OneRun(43.727592, 7.419333, 43.727712, 7.419333, 0, 1));
        runAlgo(testCollector, "files/monaco.osm.gz", "target/monaco-mc-gh",
                list, "motorcycle", true, "motorcycle", "fastest", true);

        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    @Test
    public void testBike2_issue432()
    {
        List<OneRun> list = new ArrayList<OneRun>();
        list.add(new OneRun(52.349969, 8.013813, 52.349713, 8.013293, 56, 7));
        // reverse route avoids the location
        list.add(new OneRun(52.349713, 8.013293, 52.349969, 8.013813, 293, 21));
        runAlgo(testCollector, "files/map-bug432.osm.gz", "target/map-bug432-gh",
                list, "bike2", true, "bike2", "fastest", true);

        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    @Test
    public void testMonacoAllAlgorithmsWithBaseGraph()
    {
        String vehicle = "car";
        String graphFile = "target/monaco-gh";
        String osmFile = "files/monaco.osm.gz";
        String importVehicles = vehicle;

        Helper.removeDir(new File(graphFile));
        GraphHopper hopper = new GraphHopper().
                // avoid that path.getDistance is too different to path.getPoint.calcDistance
                setWayPointMaxDistance(0).
                setOSMFile(osmFile).
                setCHEnable(false).
                setGraphHopperLocation(graphFile).
                setEncodingManager(new EncodingManager(importVehicles));

        hopper.importOrLoad();

        FlagEncoder encoder = hopper.getEncodingManager().getEncoder(vehicle);
        Weighting weighting = hopper.createWeighting(new WeightingMap("shortest"), encoder);

        List<AlgoHelperEntry> prepares = createAlgos(hopper.getGraph(), hopper.getLocationIndex(),
                encoder, true, TraversalMode.NODE_BASED, weighting, hopper.getEncodingManager());
        AlgoHelperEntry chPrepare = prepares.get(prepares.size() - 1);
        if (!(chPrepare.getQueryGraph() instanceof LevelGraph))
            throw new IllegalStateException("Last prepared queryGraph has to be a levelGraph");

        // set all normal algorithms to baseGraph of already prepared to see if all algorithms still work
        Graph baseGraphOfCHPrepared = chPrepare.getQueryGraph().getBaseGraph();
        for (AlgoHelperEntry ahe : prepares)
        {
            if (!(ahe.getQueryGraph() instanceof LevelGraph))
            {
                ahe.setQueryGraph(baseGraphOfCHPrepared);
            }
        }

        List<OneRun> forEveryAlgo = createMonacoCar();
        EdgeFilter edgeFilter = new DefaultEdgeFilter(encoder);
        for (AlgoHelperEntry entry : prepares)
        {
            LocationIndex idx = entry.getIdx();
            for (OneRun oneRun : forEveryAlgo)
            {
                List<QueryResult> list = oneRun.getList(idx, edgeFilter);
                testCollector.assertDistance(entry, list, oneRun);
            }
        }
    }

    @Test
    public void testOneWayCircleBug()
    {
        // export from http://www.openstreetmap.org/export#map=19/51.37605/-0.53155
        List<OneRun> list = new ArrayList<OneRun>();
        // going the bit longer way out of the circle
        list.add(new OneRun(51.376197, -0.531576, 51.376509, -0.530863, 153, 18));
        // now exacle the opposite direction: going into the circle (shorter)
        list.add(new OneRun(51.376509, -0.530863, 51.376197, -0.531576, 75, 15));

        runAlgo(testCollector, "files/circle-bug.osm.gz", "target/circle-bug-gh",
                list, "CAR", true, "CAR", "shortest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    @Test
    public void testMoscow()
    {
        // extracted via ./graphhopper.sh extract "37.582641,55.805261,37.626929,55.824455"
        List<OneRun> list = new ArrayList<OneRun>();
        // choose perpendicular
        // http://localhost:8989/?point=55.818994%2C37.595354&point=55.819175%2C37.596931
        list.add(new OneRun(55.818994, 37.595354, 55.819175, 37.596931, 1052, 14));
        // should choose the closest road not the other one (opposite direction)
        // http://localhost:8989/?point=55.818898%2C37.59661&point=55.819066%2C37.596374
        list.add(new OneRun(55.818898, 37.59661, 55.819066, 37.596374, 24, 2));
        // respect one way!
        // http://localhost:8989/?point=55.819066%2C37.596374&point=55.818898%2C37.59661
        list.add(new OneRun(55.819066, 37.596374, 55.818898, 37.59661, 1114, 23));
        runAlgo(testCollector, "files/moscow.osm.gz", "target/moscow-gh",
                list, "CAR", true, "CAR", "fastest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    @Test
    public void testMoscowTurnCosts()
    {
        List<OneRun> list = new ArrayList<OneRun>();
        list.add(new OneRun(55.813357, 37.5958585, 55.811042, 37.594689, 1043.99, 12));
        list.add(new OneRun(55.813159, 37.593884, 55.811278, 37.594217, 1048, 13));
        // TODO include CH
        boolean testAlsoCH = false, is3D = false;
        runAlgo(testCollector, "files/moscow.osm.gz", "target/graph-moscow",
                list, "CAR|turnCosts=true", testAlsoCH, "CAR", "fastest", is3D);

        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    @Test
    public void testMonacoFastest()
    {
        List<OneRun> list = createMonacoCar();
        list.get(0).setLocs(1, 117);
        list.get(0).setDistance(1, 2584);
        list.get(3).setDistance(1, 2279);
        list.get(3).setLocs(1, 141);
        list.get(4).setDistance(1, 2149);
        list.get(4).setLocs(1, 120);
        runAlgo(testCollector, "files/monaco.osm.gz", "target/monaco-gh",
                list, "CAR", true, "CAR", "fastest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    @Test
    public void testMonacoMixed()
    {
        // Additional locations are inserted because of new crossings from foot to highway paths!
        // Distance is the same.
        List<OneRun> list = createMonacoCar();
        list.get(0).setLocs(1, 110);
        list.get(1).setLocs(1, 170);
        list.get(2).setLocs(1, 132);
        list.get(3).setLocs(1, 137);
        list.get(4).setLocs(1, 116);

        runAlgo(testCollector, "files/monaco.osm.gz", "target/monaco-gh",
                list, "CAR,FOOT", false, "CAR", "shortest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    List<OneRun> createMonacoFoot()
    {
        List<OneRun> list = new ArrayList<OneRun>();
        list.add(new OneRun(43.730729, 7.421288, 43.727697, 7.419199, 1566, 92));
        list.add(new OneRun(43.727687, 7.418737, 43.74958, 7.436566, 3438, 136));
        list.add(new OneRun(43.728677, 7.41016, 43.739213, 7.427806, 2085, 112));
        list.add(new OneRun(43.733802, 7.413433, 43.739662, 7.424355, 1425, 89));
        return list;
    }

    @Test
    public void testMonacoFoot()
    {
        Graph g = runAlgo(testCollector, "files/monaco.osm.gz", "target/monaco-gh",
                createMonacoFoot(), "FOOT", true, "FOOT", "shortest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());

        // see testMonaco for a similar ID test
        assertEquals(GHUtility.asSet(2, 908, 570), GHUtility.getNeighbors(g.createEdgeExplorer().setBaseNode(10)));
        assertEquals(GHUtility.asSet(443, 954, 739), GHUtility.getNeighbors(g.createEdgeExplorer().setBaseNode(440)));
        assertEquals(GHUtility.asSet(910, 403, 122, 913), GHUtility.getNeighbors(g.createEdgeExplorer().setBaseNode(911)));

        assertEquals(43.743705, g.getNodeAccess().getLat(100), 1e-6);
        assertEquals(7.426362, g.getNodeAccess().getLon(701), 1e-6);
    }

    @Test
    public void testMonacoFoot3D()
    {
        // most routes have same number of points as testMonaceFoot results but longer distance due to elevation difference
        List<OneRun> list = createMonacoFoot();
        list.get(0).setDistance(1, 1627);
        list.get(2).setDistance(1, 2258);
        list.get(3).setDistance(1, 1482);

        // or slightly longer tour with less nodes: list.get(1).setDistance(1, 3610);
        list.get(1).setDistance(1, 3595);
        list.get(1).setLocs(1, 149);

        runAlgo(testCollector, "files/monaco.osm.gz", "target/monaco-gh",
                list, "FOOT", true, "FOOT", "shortest", true);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    @Test
    public void testNorthBayreuthFootFastestAnd3D()
    {
        List<OneRun> list = new ArrayList<OneRun>();
        // prefer hiking route 'Teufelsloch Unterwaiz' and 'Rotmain-Wanderweg'        
        list.add(new OneRun(49.974972, 11.515657, 49.991022, 11.512299, 2365, 66));
        // prefer hiking route 'Markgrafenweg Bayreuth Kulmbach'
        list.add(new OneRun(49.986111, 11.550407, 50.023182, 11.555386, 5165, 133));
        runAlgo(testCollector, "files/north-bayreuth.osm.gz", "target/north-bayreuth-gh",
                list, "FOOT", true, "FOOT", "fastest", true);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    @Test
    public void testMonacoBike3D_twoSpeedsPerEdge()
    {
        List<OneRun> list = new ArrayList<OneRun>();
        // 1. alternative: go over steps 'Rampe Major' => 1.7km vs. around 2.7km
        list.add(new OneRun(43.730864, 7.420771, 43.727687, 7.418737, 2710, 118));
        // 2.
        list.add(new OneRun(43.728499, 7.417907, 43.74958, 7.436566, 3777, 194));
        // 3.
        list.add(new OneRun(43.728677, 7.41016, 43.739213, 7.427806, 2776, 167));
        // 4.
        list.add(new OneRun(43.733802, 7.413433, 43.739662, 7.424355, 1544, 84));

        // try reverse direction
        // 1.
        list.add(new OneRun(43.727687, 7.418737, 43.730864, 7.420771, 2599, 115));
        list.add(new OneRun(43.74958, 7.436566, 43.728499, 7.417907, 4199, 165));
        list.add(new OneRun(43.739213, 7.427806, 43.728677, 7.41016, 3261, 177));
        // 4. avoid tunnel(s)!
        list.add(new OneRun(43.739662, 7.424355, 43.733802, 7.413433, 2452, 112));
        runAlgo(testCollector, "files/monaco.osm.gz", "target/monaco-gh",
                list, "BIKE2", true, "BIKE2", "fastest", true);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    @Test
    public void testMonacoBike()
    {
        List<OneRun> list = new ArrayList<OneRun>();
        list.add(new OneRun(43.730864, 7.420771, 43.727687, 7.418737, 1642, 87));
        list.add(new OneRun(43.727687, 7.418737, 43.74958, 7.436566, 3580, 168));
        list.add(new OneRun(43.728677, 7.41016, 43.739213, 7.427806, 2323, 121));
        list.add(new OneRun(43.733802, 7.413433, 43.739662, 7.424355, 1434, 89));
        runAlgo(testCollector, "files/monaco.osm.gz", "target/monaco-gh",
                list, "BIKE", true, "BIKE", "shortest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    @Test
    public void testMonacoMountainBike()
    {
        List<OneRun> list = new ArrayList<OneRun>();
        list.add(new OneRun(43.730864, 7.420771, 43.727687, 7.418737, 2322, 110));
        list.add(new OneRun(43.727687, 7.418737, 43.74958, 7.436566, 3613, 178));
        list.add(new OneRun(43.728677, 7.41016, 43.739213, 7.427806, 2331, 121));
        // hard to select between secondard and primary (both are AVOID for mtb)
        list.add(new OneRun(43.733802, 7.413433, 43.739662, 7.424355, 1459, 88));
        runAlgo(testCollector, "files/monaco.osm.gz", "target/monaco-gh",
                list, "MTB", true, "MTB", "fastest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());

        runAlgo(testCollector, "files/monaco.osm.gz", "target/monaco-gh",
                list, "MTB,RACINGBIKE", false, "MTB", "fastest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    @Test
    public void testMonacoRacingBike()
    {
        List<OneRun> list = new ArrayList<OneRun>();
        list.add(new OneRun(43.730864, 7.420771, 43.727687, 7.418737, 2594, 111));
        list.add(new OneRun(43.727687, 7.418737, 43.74958, 7.436566, 3588, 170));
        list.add(new OneRun(43.728677, 7.41016, 43.739213, 7.427806, 2572, 135));
        list.add(new OneRun(43.733802, 7.413433, 43.739662, 7.424355, 1490, 84));
        runAlgo(testCollector, "files/monaco.osm.gz", "target/monaco-gh",
                list, "RACINGBIKE", true, "RACINGBIKE", "fastest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());

        runAlgo(testCollector, "files/monaco.osm.gz", "target/monaco-gh",
                list, "BIKE,RACINGBIKE", false, "RACINGBIKE", "fastest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    @Test
    public void testKremsBikeRelation()
    {
        List<OneRun> list = new ArrayList<OneRun>();
        list.add(new OneRun(48.409523, 15.602394, 48.375466, 15.72916, 12491, 159));
        list.add(new OneRun(48.410061, 15.63951, 48.411386, 15.604899, 3113, 87));
        list.add(new OneRun(48.412294, 15.62007, 48.398306, 15.609667, 3965, 94));

        runAlgo(testCollector, "files/krems.osm.gz", "target/krems-gh",
                list, "BIKE", true, "BIKE", "fastest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());

        runAlgo(testCollector, "files/krems.osm.gz", "target/krems-gh",
                list, "CAR,BIKE", false, "BIKE", "fastest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    @Test
    public void testKremsMountainBikeRelation()
    {
        List<OneRun> list = new ArrayList<OneRun>();
        list.add(new OneRun(48.409523, 15.602394, 48.375466, 15.72916, 12574, 169));
        list.add(new OneRun(48.410061, 15.63951, 48.411386, 15.604899, 3101, 94));
        list.add(new OneRun(48.412294, 15.62007, 48.398306, 15.609667, 3965, 95));

        runAlgo(testCollector, "files/krems.osm.gz", "target/krems-gh",
                list, "MTB", true, "MTB", "fastest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());

        runAlgo(testCollector, "files/krems.osm.gz", "target/krems-gh",
                list, "BIKE,MTB", false, "MTB", "fastest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    List<OneRun> createAndorra()
    {
        List<OneRun> list = new ArrayList<OneRun>();
        list.add(new OneRun(42.56819, 1.603231, 42.571034, 1.520662, 17708, 524));
        list.add(new OneRun(42.529176, 1.571302, 42.571034, 1.520662, 11408, 305));
        return list;
    }

    @Test
    public void testAndorra()
    {
        runAlgo(testCollector, "files/andorra.osm.gz", "target/andorra-gh",
                createAndorra(), "CAR", true, "CAR", "shortest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    @Test
    public void testAndorraPbf()
    {
        runAlgo(testCollector, "files/andorra.osm.pbf", "target/andorra-gh",
                createAndorra(), "CAR", true, "CAR", "shortest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    @Test
    public void testAndorraFoot()
    {
        List<OneRun> list = createAndorra();
        list.get(0).setDistance(1, 16354);
        list.get(0).setLocs(1, 648);
        list.get(1).setDistance(1, 12701);
        list.get(1).setLocs(1, 431);

        runAlgo(testCollector, "files/andorra.osm.gz", "target/andorra-gh",
                list, "FOOT", true, "FOOT", "shortest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    @Test
    public void testCampoGrande()
    {
        // test not only NE quadrant of earth!

        // bzcat campo-grande.osm.bz2 
        //   | ./bin/osmosis --read-xml enableDateParsing=no file=- --bounding-box top=-20.4 left=-54.6 bottom=-20.6 right=-54.5 --write-xml file=- 
        //   | bzip2 > campo-grande.extracted.osm.bz2
        List<OneRun> list = new ArrayList<OneRun>();
        list.add(new OneRun(-20.4, -54.6, -20.6, -54.54, 25516, 271));
        list.add(new OneRun(-20.43, -54.54, -20.537, -54.674, 18009, 237));
        runAlgo(testCollector, "files/campo-grande.osm.gz", "target/campo-grande-gh", list,
                "CAR", false, "CAR", "shortest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    @Test
    public void testMonacoVia()
    {
        OneRun oneRun = new OneRun();
        oneRun.add(43.730729, 7.42135, 0, 0);
        oneRun.add(43.727697, 7.419199, 2581, 110);
        oneRun.add(43.726387, 7.4, 3001, 90);

        List<OneRun> list = new ArrayList<OneRun>();
        list.add(oneRun);

        runAlgo(testCollector, "files/monaco.osm.gz", "target/monaco-gh",
                list, "CAR", true, "CAR", "shortest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    @Test
    public void testHarsdorf()
    {
        List<OneRun> list = new ArrayList<OneRun>();
        // choose Unterloher Weg and the following residential + cycleway
        list.add(new OneRun(50.004333, 11.600254, 50.044449, 11.543434, 6931, 184));
        runAlgo(testCollector, "files/north-bayreuth.osm.gz", "target/north-bayreuth-gh",
                list, "bike", true, "bike", "fastest", false);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    @Test
    public void testNeudrossenfeld()
    {
        List<OneRun> list = new ArrayList<OneRun>();
        // choose cycleway (Dreschenauer Straße)
        list.add(new OneRun(49.987132, 11.510496, 50.018839, 11.505024, 3985, 106));

        runAlgo(testCollector, "files/north-bayreuth.osm.gz", "target/north-bayreuth-gh",
                list, "bike", true, "bike", "fastest", true);

        runAlgo(testCollector, "files/north-bayreuth.osm.gz", "target/north-bayreuth-gh",
                list, "bike2", true, "bike2", "fastest", true);
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
    }

    /**
     * @param testAlsoCH if true also the CH algorithms will be tested which needs preparation and
     * takes a bit longer
     */
    Graph runAlgo( TestAlgoCollector testCollector, String osmFile,
                   String graphFile, List<OneRun> forEveryAlgo, String importVehicles,
                   boolean testAlsoCH, String vehicle, String weightStr, boolean is3D )
    {
        AlgoHelperEntry algoEntry = null;
        OneRun tmpOneRun = null;
        try
        {
            Helper.removeDir(new File(graphFile));
            GraphHopper hopper = new GraphHopper().
                    setStoreOnFlush(true).
                    // avoid that path.getDistance is too different to path.getPoint.calcDistance
                    setWayPointMaxDistance(0).
                    setOSMFile(osmFile).
                    setCHEnable(false).
                    setGraphHopperLocation(graphFile).
                    setEncodingManager(new EncodingManager(importVehicles));
            if (is3D)
                hopper.setElevationProvider(new SRTMProvider().setCacheDir(new File("./files")));

            hopper.importOrLoad();

            TraversalMode tMode = importVehicles.toLowerCase().contains("turncosts=true")
                    ? TraversalMode.EDGE_BASED_1DIR : TraversalMode.NODE_BASED;
            FlagEncoder encoder = hopper.getEncodingManager().getEncoder(vehicle);
            Weighting weighting = hopper.createWeighting(new WeightingMap(weightStr), encoder);

            Collection<AlgoHelperEntry> prepares = createAlgos(hopper.getGraph(), hopper.getLocationIndex(),
                    encoder, testAlsoCH, tMode, weighting, hopper.getEncodingManager());
            EdgeFilter edgeFilter = new DefaultEdgeFilter(encoder);
            for (AlgoHelperEntry entry : prepares)
            {
                algoEntry = entry;
                LocationIndex idx = entry.getIdx();
                for (OneRun oneRun : forEveryAlgo)
                {
                    tmpOneRun = oneRun;
                    List<QueryResult> list = oneRun.getList(idx, edgeFilter);
                    testCollector.assertDistance(algoEntry, list, oneRun);
                }
            }

            return hopper.getGraph();
        } catch (Exception ex)
        {
            if (algoEntry == null)
                throw new RuntimeException("cannot handle file " + osmFile + ", " + ex.getMessage(), ex);

            throw new RuntimeException("cannot handle " + algoEntry.toString() + ", for " + tmpOneRun
                    + ", file " + osmFile + ", " + ex.getMessage(), ex);
        } finally
        {
            // Helper.removeDir(new File(graphFile));
        }
    }

    @Test
    public void testPerformance() throws IOException
    {
        int N = 10;
        int noJvmWarming = N / 4;

        Random rand = new Random(0);
        EncodingManager eManager = new EncodingManager("CAR");
        FlagEncoder encoder = eManager.getEncoder("CAR");
        Graph graph = new GraphBuilder(eManager).create();

        String bigFile = "10000EWD.txt.gz";
        new PrinctonReader(graph).setStream(new GZIPInputStream(PrinctonReader.class.getResourceAsStream(bigFile))).read();
        Collection<AlgoHelperEntry> prepares = createAlgos(graph, null, encoder, false, TraversalMode.NODE_BASED,
                new ShortestWeighting(), eManager);
        for (AlgoHelperEntry entry : prepares)
        {
            StopWatch sw = new StopWatch();
            for (int i = 0; i < N; i++)
            {
                int node1 = Math.abs(rand.nextInt(graph.getNodes()));
                int node2 = Math.abs(rand.nextInt(graph.getNodes()));
                RoutingAlgorithm d = entry.createAlgo(graph);
                if (i >= noJvmWarming)
                    sw.start();

                Path p = d.calcPath(node1, node2);
                // avoid jvm optimization => call p.distance
                if (i >= noJvmWarming && p.getDistance() > -1)
                    sw.stop();

                // System.out.println("#" + i + " " + name + ":" + sw.getSeconds() + " " + p.nodes());
            }

            float perRun = sw.stop().getSeconds() / ((float) (N - noJvmWarming));
            System.out.println("# " + getClass().getSimpleName() + " " + entry
                    + ":" + sw.stop().getSeconds() + ", per run:" + perRun);
            assertTrue("speed to low!? " + perRun + " per run", perRun < 0.08);
        }
    }

    @Test
    public void testMonacoParallel() throws IOException
    {
        System.out.println("testMonacoParallel takes a bit time...");
        String graphFile = "target/monaco-gh";
        Helper.removeDir(new File(graphFile));
        final EncodingManager encodingManager = new EncodingManager("CAR");
        GraphHopper hopper = new GraphHopper().
                setStoreOnFlush(true).
                setEncodingManager(encodingManager).
                setCHEnable(false).
                setWayPointMaxDistance(0).
                setOSMFile("files/monaco.osm.gz").
                setGraphHopperLocation(graphFile).
                importOrLoad();
        final Graph g = hopper.getGraph();
        final LocationIndex idx = hopper.getLocationIndex();
        final List<OneRun> instances = createMonacoCar();
        List<Thread> threads = new ArrayList<Thread>();
        final AtomicInteger integ = new AtomicInteger(0);
        int MAX = 100;
        final FlagEncoder carEncoder = encodingManager.getEncoder("CAR");

        // testing if algorithms are independent. should be. so test only two algorithms. 
        // also the preparing is too costly to be called for every thread
        int algosLength = 2;
        final Weighting weighting = new ShortestWeighting();
        final EdgeFilter filter = new DefaultEdgeFilter(carEncoder);
        for (int no = 0; no < MAX; no++)
        {
            for (int instanceNo = 0; instanceNo < instances.size(); instanceNo++)
            {
                String[] algos = new String[]
                {
                    "astar", "dijkstrabi"
                };
                for (final String algoStr : algos)
                {
                    // an algorithm is not thread safe! reuse via clear() is ONLY appropriated if used from same thread!
                    final int instanceIndex = instanceNo;
                    Thread t = new Thread()
                    {
                        @Override
                        public void run()
                        {
                            OneRun oneRun = instances.get(instanceIndex);
                            AlgorithmOptions opts = AlgorithmOptions.start().flagEncoder(carEncoder).weighting(weighting).algorithm(algoStr).build();
                            testCollector.assertDistance(new AlgoHelperEntry(g, opts, idx),
                                    oneRun.getList(idx, filter), oneRun);
                            integ.addAndGet(1);
                        }
                    };
                    t.start();
                    threads.add(t);
                }
            }
        }

        for (Thread t : threads)
        {
            try
            {
                t.join();
            } catch (InterruptedException ex)
            {
                throw new RuntimeException(ex);
            }
        }

        assertEquals(MAX * algosLength * instances.size(), integ.get());
        assertEquals(testCollector.toString(), 0, testCollector.errors.size());
        hopper.close();
    }

    static List<AlgoHelperEntry> createAlgos( Graph g,
                                              LocationIndex idx, final FlagEncoder encoder, boolean withCh,
                                              final TraversalMode tMode, final Weighting weighting, final EncodingManager manager )
    {
        List<AlgoHelperEntry> prepare = new ArrayList<AlgoHelperEntry>();
        prepare.add(new AlgoHelperEntry(g, new AlgorithmOptions(AlgorithmOptions.ASTAR, encoder, weighting, tMode), idx));
        // later: include dijkstraOneToMany        
        prepare.add(new AlgoHelperEntry(g, new AlgorithmOptions(AlgorithmOptions.DIJKSTRA, encoder, weighting, tMode), idx));

        final AlgorithmOptions astarbiOpts = new AlgorithmOptions(AlgorithmOptions.ASTAR_BI, encoder, weighting, tMode);
        astarbiOpts.getHints().put(AlgorithmOptions.ASTAR_BI + ".approximation", "BeelineSimplification");
        final AlgorithmOptions dijkstrabiOpts = new AlgorithmOptions(AlgorithmOptions.DIJKSTRA_BI, encoder, weighting, tMode);
        prepare.add(new AlgoHelperEntry(g, astarbiOpts, idx));
        prepare.add(new AlgoHelperEntry(g, dijkstrabiOpts, idx));

        if (withCh)
        {
            final LevelGraph graphCH = (LevelGraph) ((GraphStorage) g).copyTo(new GraphBuilder(manager).
                    set3D(g.getNodeAccess().is3D()).levelGraphCreate());
            final PrepareContractionHierarchies prepareCH = new PrepareContractionHierarchies(new GHDirectory("", DAType.RAM_INT),
                    graphCH, encoder, weighting, tMode);
            prepareCH.doWork();
            LocationIndex idxCH = new LocationIndexTree(graphCH.getBaseGraph(), new RAMDirectory()).prepareIndex();
            prepare.add(new AlgoHelperEntry(graphCH, dijkstrabiOpts, idxCH)
            {
                @Override
                public RoutingAlgorithm createAlgo( Graph qGraph )
                {
                    return prepareCH.createAlgo(qGraph, dijkstrabiOpts);
                }
            });

            prepare.add(new AlgoHelperEntry(graphCH, astarbiOpts, idxCH)
            {
                @Override
                public RoutingAlgorithm createAlgo( Graph qGraph )
                {
                    return prepareCH.createAlgo(qGraph, astarbiOpts);
                }
            });
        }
        return prepare;
    }
}


File: core/src/test/java/com/graphhopper/routing/ch/DijkstraBidirectionCHTest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing.ch;

import com.graphhopper.routing.*;
import com.graphhopper.routing.util.*;
import com.graphhopper.storage.*;
import com.graphhopper.util.EdgeIteratorState;
import com.graphhopper.util.EdgeSkipIterState;
import com.graphhopper.util.Helper;

import static org.junit.Assert.*;

import org.junit.Test;

/**
 * Tests if a graph optimized by contraction hierarchies returns the same results as a none
 * optimized one. Additionally fine grained path unpacking is tested.
 * <p/>
 * @author Peter Karich
 */
public class DijkstraBidirectionCHTest extends AbstractRoutingAlgorithmTester
{
    // matrix graph is expensive to create and to prepare!
    private static Graph preparedMatrixGraph;

    @Override
    public Graph getMatrixGraph()
    {
        if (preparedMatrixGraph == null)
        {
            LevelGraph lg = (LevelGraph) createGraph(false);
            getMatrixAlikeGraph().copyTo(lg);
            createFactory(lg, defaultOpts);
            preparedMatrixGraph = lg;
        }
        return preparedMatrixGraph;
    }

    @Override
    protected LevelGraph createGraph( EncodingManager em, boolean is3D )
    {
        return new GraphBuilder(em).set3D(is3D).levelGraphCreate();
    }

    @Override
    public RoutingAlgorithm createAlgo( Graph g, AlgorithmOptions opts )
    {
        return createFactory(g, opts).createAlgo(g, opts);
    }

    @Override
    public RoutingAlgorithmFactory createFactory( Graph g, AlgorithmOptions opts )
    {
        PrepareContractionHierarchies ch = new PrepareContractionHierarchies(new GHDirectory("", DAType.RAM_INT),
                (LevelGraph) g, opts.getFlagEncoder(), opts.getWeighting(), TraversalMode.NODE_BASED);
        // hack: prepare matrixGraph only once
        if (g != preparedMatrixGraph)
            ch.doWork();

        return ch;
    }

    @Test
    public void testPathRecursiveUnpacking()
    {
        // use an encoder where it is possible to store 2 weights per edge
        FlagEncoder encoder = new Bike2WeightFlagEncoder();
        EncodingManager em = new EncodingManager(encoder);
        LevelGraphStorage g2 = (LevelGraphStorage) createGraph(em, false);
        g2.edge(0, 1, 1, true);
        EdgeIteratorState iter1_1 = g2.edge(0, 2, 1.4, false);
        EdgeIteratorState iter1_2 = g2.edge(2, 5, 1.4, false);
        g2.edge(1, 2, 1, true);
        g2.edge(1, 3, 3, true);
        g2.edge(2, 3, 1, true);
        g2.edge(4, 3, 1, true);
        g2.edge(2, 5, 1.4, true);
        g2.edge(3, 5, 1, true);
        g2.edge(5, 6, 1, true);
        g2.edge(4, 6, 1, true);
        g2.edge(6, 7, 1, true);
        EdgeIteratorState iter2_2 = g2.edge(5, 7);
        iter2_2.setDistance(1.4).setFlags(encoder.setProperties(10, true, false));

        // simulate preparation
        EdgeSkipIterState iter2_1 = g2.shortcut(0, 5);
        iter2_1.setDistance(2.8).setFlags(encoder.setProperties(10, true, false));
        iter2_1.setSkippedEdges(iter1_1.getEdge(), iter1_2.getEdge());
        EdgeSkipIterState tmp = g2.shortcut(0, 7);
        tmp.setDistance(4.2).setFlags(encoder.setProperties(10, true, false));
        tmp.setSkippedEdges(iter2_1.getEdge(), iter2_2.getEdge());
        g2.setLevel(1, 0);
        g2.setLevel(3, 1);
        g2.setLevel(4, 2);
        g2.setLevel(6, 3);
        g2.setLevel(2, 4);
        g2.setLevel(5, 5);
        g2.setLevel(7, 6);
        g2.setLevel(0, 7);

        ShortestWeighting weighting = new ShortestWeighting();
        AlgorithmOptions opts = new AlgorithmOptions(AlgorithmOptions.DIJKSTRA_BI, encoder, weighting);
        Path p = new PrepareContractionHierarchies(new GHDirectory("", DAType.RAM_INT),
                g2, encoder, weighting, TraversalMode.NODE_BASED).
                createAlgo(g2, opts).calcPath(0, 7);

        assertEquals(Helper.createTList(0, 2, 5, 7), p.calcNodes());
        assertEquals(1064, p.getTime());
        assertEquals(4.2, p.getDistance(), 1e-5);
    }

    @Override
    public void testCalcFootPath()
    {
        // disable car encoder and move foot to first position => workaround as CH does not allow multiple vehicles
        FlagEncoder tmpFootEncoder = footEncoder;
        FlagEncoder tmpCarEncoder = carEncoder;
        carEncoder = new CarFlagEncoder()
        {
            @Override
            public long setProperties( double speed, boolean forward, boolean backward )
            {
                return 0;
            }
        };

        footEncoder = new FootFlagEncoder();
        new EncodingManager(footEncoder);

        super.testCalcFootPath();
        footEncoder = tmpFootEncoder;
        carEncoder = tmpCarEncoder;
    }

    @Test
    public void testBaseGraph()
    {
        CarFlagEncoder carFE = new CarFlagEncoder();
        Graph g = createGraph(new EncodingManager(carFE), false);
        initDirectedAndDiffSpeed(g, carFE);

        // do CH preparation for car
        createFactory(g, defaultOpts);

        // use base graph for solving normal Dijkstra
        Path p1 = new RoutingAlgorithmFactorySimple().createAlgo(g, defaultOpts).calcPath(0, 3);
        assertEquals(Helper.createTList(0, 1, 5, 2, 3), p1.calcNodes());
        assertEquals(p1.toString(), 402.29, p1.getDistance(), 1e-2);
        assertEquals(p1.toString(), 144823, p1.getTime());
    }

    @Test
    public void testBaseGraphMultipleVehicles()
    {
        Graph g = createGraph(encodingManager, false);
        initFootVsCar(g);

        AlgorithmOptions footOptions = AlgorithmOptions.start().flagEncoder(footEncoder).
                weighting(new FastestWeighting(footEncoder)).build();
        AlgorithmOptions carOptions = AlgorithmOptions.start().flagEncoder(carEncoder).
                weighting(new FastestWeighting(carEncoder)).build();

        // do CH preparation for car
        RoutingAlgorithmFactory contractedFactory = createFactory(g, carOptions);

        // use contracted graph
        Path p1 = contractedFactory.createAlgo(g, carOptions).calcPath(0, 7);
        assertEquals(Helper.createTList(0, 4, 6, 7), p1.calcNodes());
        assertEquals(p1.toString(), 15000, p1.getDistance(), 1e-6);

        // use base graph for solving normal Dijkstra via car
        Path p2 = new RoutingAlgorithmFactorySimple().createAlgo(g.getBaseGraph(), carOptions).calcPath(0, 7);
        assertEquals(Helper.createTList(0, 4, 6, 7), p2.calcNodes());
        assertEquals(p2.toString(), 15000, p2.getDistance(), 1e-6);
        assertEquals(p2.toString(), 2700 * 1000, p2.getTime());

        // use base graph for solving normal Dijkstra via foot
        Path p3 = new RoutingAlgorithmFactorySimple().createAlgo(g.getBaseGraph(), footOptions).calcPath(0, 7);
        assertEquals(p3.toString(), 17000, p3.getDistance(), 1e-6);
        assertEquals(p3.toString(), 12240 * 1000, p3.getTime());
        assertEquals(Helper.createTList(0, 4, 5, 7), p3.calcNodes());
    }
}


File: core/src/test/java/com/graphhopper/routing/ch/PrepareContractionHierarchiesTest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing.ch;

import com.graphhopper.routing.*;
import com.graphhopper.routing.ch.PrepareContractionHierarchies.Shortcut;
import com.graphhopper.routing.util.*;
import com.graphhopper.storage.*;
import com.graphhopper.util.*;

import java.util.Collection;
import java.util.Iterator;

import static org.junit.Assert.*;

import org.junit.Before;
import org.junit.Test;

/**
 * @author Peter Karich
 */
public class PrepareContractionHierarchiesTest
{
    private final EncodingManager encodingManager = new EncodingManager("CAR");
    private final CarFlagEncoder carEncoder = (CarFlagEncoder) encodingManager.getEncoder("CAR");
    private final Weighting weighting = new ShortestWeighting();
    private final TraversalMode tMode = TraversalMode.NODE_BASED;
    private Directory dir;

    LevelGraph createGraph()
    {
        return new GraphBuilder(encodingManager).levelGraphCreate();
    }

    LevelGraph createExampleGraph()
    {
        LevelGraph g = createGraph();

        //5-1-----2
        //   \ __/|
        //    0   |
        //   /    |
        //  4-----3
        //
        g.edge(0, 1, 1, true);
        g.edge(0, 2, 1, true);
        g.edge(0, 4, 3, true);
        g.edge(1, 2, 2, true);
        g.edge(2, 3, 1, true);
        g.edge(4, 3, 2, true);
        g.edge(5, 1, 2, true);
        return g;
    }

    @Before
    public void setUp()
    {
        dir = new GHDirectory("", DAType.RAM_INT);
    }

    @Test
    public void testShortestPathSkipNode()
    {
        LevelGraph g = createExampleGraph();
        double normalDist = new Dijkstra(g, carEncoder, weighting, tMode).calcPath(4, 2).getDistance();
        DijkstraOneToMany algo = new DijkstraOneToMany(g, carEncoder, weighting, tMode);
        PrepareContractionHierarchies prepare = new PrepareContractionHierarchies(dir, g, carEncoder, weighting, tMode);
        prepare.initFromGraph().prepareNodes();
        algo.setEdgeFilter(new PrepareContractionHierarchies.IgnoreNodeFilter(g, g.getNodes() + 1).setAvoidNode(3));
        algo.setWeightLimit(100);
        int nodeEntry = algo.findEndNode(4, 2);
        assertTrue(algo.getWeight(nodeEntry) > normalDist);

        algo.clear();
        nodeEntry = algo.setLimitVisitedNodes(1).findEndNode(4, 2);
        assertEquals(-1, nodeEntry);
    }

    @Test
    public void testShortestPathSkipNode2()
    {
        LevelGraph g = createExampleGraph();
        double normalDist = new Dijkstra(g, carEncoder, weighting, tMode).calcPath(4, 2).getDistance();
        assertEquals(3, normalDist, 1e-5);
        DijkstraOneToMany algo = new DijkstraOneToMany(g, carEncoder, weighting, tMode);
        PrepareContractionHierarchies prepare = new PrepareContractionHierarchies(dir, g, carEncoder, weighting, tMode);
        prepare.initFromGraph().prepareNodes();
        algo.setEdgeFilter(new PrepareContractionHierarchies.IgnoreNodeFilter(g, g.getNodes() + 1).setAvoidNode(3));
        algo.setWeightLimit(10);
        int nodeEntry = algo.findEndNode(4, 2);
        assertEquals(4, algo.getWeight(nodeEntry), 1e-5);

        nodeEntry = algo.findEndNode(4, 1);
        assertEquals(4, algo.getWeight(nodeEntry), 1e-5);
    }

    @Test
    public void testShortestPathLimit()
    {
        LevelGraph g = createExampleGraph();
        DijkstraOneToMany algo = new DijkstraOneToMany(g, carEncoder, weighting, tMode);
        PrepareContractionHierarchies prepare = new PrepareContractionHierarchies(dir, g, carEncoder, weighting, tMode);
        prepare.initFromGraph().prepareNodes();
        algo.setEdgeFilter(new PrepareContractionHierarchies.IgnoreNodeFilter(g, g.getNodes() + 1).setAvoidNode(0));
        algo.setWeightLimit(2);
        int endNode = algo.findEndNode(4, 1);
        // did not reach endNode
        assertNotEquals(1, endNode);
    }

    @Test
    public void testAddShortcuts()
    {
        LevelGraph g = createExampleGraph();
        int old = g.getAllEdges().getCount();
        PrepareContractionHierarchies prepare = new PrepareContractionHierarchies(dir, g, carEncoder, weighting, tMode);
        prepare.doWork();
        assertEquals(old + 1, g.getAllEdges().getCount());
    }

    @Test
    public void testMoreComplexGraph()
    {
        LevelGraph g = initShortcutsGraph(createGraph());
        int old = g.getAllEdges().getCount();
        PrepareContractionHierarchies prepare = new PrepareContractionHierarchies(dir, g, carEncoder, weighting, tMode);
        prepare.doWork();
        assertEquals(old + 7, g.getAllEdges().getCount());
    }

    @Test
    public void testDirectedGraph()
    {
        LevelGraph g = createGraph();
        g.edge(5, 4, 3, false);
        g.edge(4, 5, 10, false);
        g.edge(2, 4, 1, false);
        g.edge(5, 2, 1, false);
        g.edge(3, 5, 1, false);
        g.edge(4, 3, 1, false);
        int old = GHUtility.count(g.getAllEdges());
        PrepareContractionHierarchies prepare = new PrepareContractionHierarchies(dir, g, carEncoder, weighting, tMode);
        prepare.doWork();
        assertEquals(old + 2, GHUtility.count(g.getAllEdges()));
        RoutingAlgorithm algo = prepare.createAlgo(g, new AlgorithmOptions(AlgorithmOptions.DIJKSTRA_BI, carEncoder, weighting, tMode));
        Path p = algo.calcPath(4, 2);
        assertEquals(3, p.getDistance(), 1e-6);
        assertEquals(Helper.createTList(4, 3, 5, 2), p.calcNodes());
    }

    @Test
    public void testDirectedGraph2()
    {
        LevelGraph g = createGraph();
        initDirected2(g);
        int old = GHUtility.count(g.getAllEdges());
        PrepareContractionHierarchies prepare = new PrepareContractionHierarchies(dir, g, carEncoder, weighting, tMode);
        prepare.doWork();
        // PrepareTowerNodesShortcutsTest.printEdges(g);
        assertEquals(old + 9, GHUtility.count(g.getAllEdges()));
        RoutingAlgorithm algo = prepare.createAlgo(g, new AlgorithmOptions(AlgorithmOptions.DIJKSTRA_BI, carEncoder, weighting, tMode));
        Path p = algo.calcPath(0, 10);
        assertEquals(10, p.getDistance(), 1e-6);
        assertEquals(Helper.createTList(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10), p.calcNodes());
    }

    @Test
    public void testDirectedGraph3()
    {
        LevelGraph g = createGraph();
        //5 6 7
        // \|/
        //4-3_1<-
        //    \_|_10
        //   0__2_11

        g.edge(0, 2, 2, true);
        g.edge(10, 2, 2, true);
        g.edge(11, 2, 2, true);
        // create a longer one directional edge => no longish one-dir shortcut should be created        
        g.edge(2, 1, 2, true);
        g.edge(2, 1, 10, false);

        g.edge(1, 3, 2, true);
        g.edge(3, 4, 2, true);
        g.edge(3, 5, 2, true);
        g.edge(3, 6, 2, true);
        g.edge(3, 7, 2, true);

        PrepareContractionHierarchies prepare = new PrepareContractionHierarchies(dir, g, carEncoder, weighting, tMode);
        prepare.initFromGraph();
        prepare.prepareNodes();
        // find all shortcuts if we contract node 1
        Collection<Shortcut> scs = prepare.testFindShortcuts(1);
        assertEquals(2, scs.size());
        Iterator<Shortcut> iter = scs.iterator();
        Shortcut sc1 = iter.next();
        Shortcut sc2 = iter.next();
        if (sc1.weight > sc2.weight)
        {
            Shortcut tmp = sc1;
            sc1 = sc2;
            sc2 = tmp;
        }

        // both dirs
        assertTrue(sc1.toString(), sc1.from == 3 && sc1.to == 2);
        assertTrue(sc1.toString(), carEncoder.isForward(sc1.flags) && carEncoder.isBackward(sc1.flags));

        // directed
        assertTrue(sc2.toString(), sc2.from == 2 && sc2.to == 3);
        assertTrue(sc2.toString(), carEncoder.isForward(sc2.flags));

        assertEquals(sc1.toString(), 4, sc1.weight, 1e-4);
        assertEquals(sc2.toString(), 12, sc2.weight, 1e-4);
    }

    void initRoundaboutGraph( Graph g )
    {
        //              roundabout:
        //16-0-9-10--11   12<-13
        //    \       \  /      \
        //    17       \|        7-8-..
        // -15-1--2--3--4       /     /
        //     /         \-5->6/     /
        //  -14            \________/

        g.edge(16, 0, 1, true);
        g.edge(0, 9, 1, true);
        g.edge(0, 17, 1, true);
        g.edge(9, 10, 1, true);
        g.edge(10, 11, 1, true);
        g.edge(11, 28, 1, true);
        g.edge(28, 29, 1, true);
        g.edge(29, 30, 1, true);
        g.edge(30, 31, 1, true);
        g.edge(31, 4, 1, true);

        g.edge(17, 1, 1, true);
        g.edge(15, 1, 1, true);
        g.edge(14, 1, 1, true);
        g.edge(14, 18, 1, true);
        g.edge(18, 19, 1, true);
        g.edge(19, 20, 1, true);
        g.edge(20, 15, 1, true);
        g.edge(19, 21, 1, true);
        g.edge(21, 16, 1, true);
        g.edge(1, 2, 1, true);
        g.edge(2, 3, 1, true);
        g.edge(3, 4, 1, true);

        g.edge(4, 5, 1, false);
        g.edge(5, 6, 1, false);
        g.edge(6, 7, 1, false);
        g.edge(7, 13, 1, false);
        g.edge(13, 12, 1, false);
        g.edge(12, 4, 1, false);

        g.edge(7, 8, 1, true);
        g.edge(8, 22, 1, true);
        g.edge(22, 23, 1, true);
        g.edge(23, 24, 1, true);
        g.edge(24, 25, 1, true);
        g.edge(25, 27, 1, true);
        g.edge(27, 5, 1, true);
        g.edge(25, 26, 1, false);
        g.edge(26, 25, 1, false);
    }

    @Test
    public void testRoundaboutUnpacking()
    {
        LevelGraph g = createGraph();
        initRoundaboutGraph(g);
        int old = g.getAllEdges().getCount();
        PrepareContractionHierarchies prepare = new PrepareContractionHierarchies(dir, g, carEncoder, weighting, tMode);
        prepare.doWork();
        assertEquals(old + 23, g.getAllEdges().getCount());
        RoutingAlgorithm algo = prepare.createAlgo(g, new AlgorithmOptions(AlgorithmOptions.DIJKSTRA_BI, carEncoder, weighting, tMode));
        Path p = algo.calcPath(4, 7);
        assertEquals(Helper.createTList(4, 5, 6, 7), p.calcNodes());
    }

    @Test
    public void testFindShortcuts_Roundabout()
    {
        LevelGraphStorage g = (LevelGraphStorage) createGraph();
        EdgeIteratorState iter1_1 = g.edge(1, 3, 1, true);
        EdgeIteratorState iter1_2 = g.edge(3, 4, 1, true);
        EdgeIteratorState iter2_1 = g.edge(4, 5, 1, false);
        EdgeIteratorState iter2_2 = g.edge(5, 6, 1, false);
        EdgeIteratorState iter3_1 = g.edge(6, 7, 1, true);
        EdgeIteratorState iter3_2 = g.edge(6, 8, 2, false);
        g.edge(8, 4, 1, false);

        PrepareContractionHierarchies prepare = new PrepareContractionHierarchies(dir, g, carEncoder, weighting, tMode);
        EdgeSkipIterState tmp = g.shortcut(1, 4);
        tmp.setFlags(PrepareEncoder.getScDirMask());
        tmp.setWeight(2);
        tmp.setSkippedEdges(iter1_1.getEdge(), iter1_2.getEdge());
        long f = PrepareEncoder.getScFwdDir();
        tmp = g.shortcut(4, 6);
        tmp.setFlags(f);
        tmp.setWeight(2);
        tmp.setSkippedEdges(iter2_1.getEdge(), iter2_2.getEdge());
        tmp = g.shortcut(6, 4);
        tmp.setFlags(f);
        tmp.setWeight(3);
        tmp.setSkippedEdges(iter3_1.getEdge(), iter3_2.getEdge());

        prepare.initFromGraph();
        prepare.prepareNodes();
        g.setLevel(3, 3);
        g.setLevel(5, 5);
        g.setLevel(7, 7);
        g.setLevel(8, 8);

        // there should be two different shortcuts for both directions!
        Collection<Shortcut> sc = prepare.testFindShortcuts(4);
        assertEquals(2, sc.size());
    }

    void initUnpackingGraph( LevelGraphStorage g, Weighting w )
    {
        final long flags = carEncoder.setProperties(30, true, false);
        double dist = 1;
        g.edge(10, 0).setDistance(dist).setFlags(flags);
        EdgeIteratorState iterTmp1 = g.edge(0, 1);
        iterTmp1.setDistance(dist).setFlags(flags);
        EdgeIteratorState iter2 = g.edge(1, 2).setDistance(dist).setFlags(flags);
        EdgeIteratorState iter3 = g.edge(2, 3).setDistance(dist).setFlags(flags);
        EdgeIteratorState iter4 = g.edge(3, 4).setDistance(dist).setFlags(flags);
        EdgeIteratorState iter5 = g.edge(4, 5).setDistance(dist).setFlags(flags);
        EdgeIteratorState iter6 = g.edge(5, 6).setDistance(dist).setFlags(flags);
        long oneDirFlags = PrepareEncoder.getScFwdDir();

        int tmp = iterTmp1.getEdge();
        EdgeSkipIterState sc1 = g.shortcut(0, 2);
        int x = EdgeIterator.NO_EDGE;
        sc1.setWeight(w.calcWeight(iterTmp1, false, x) + w.calcWeight(iter2, false, x)).setDistance(2 * dist).setFlags(oneDirFlags);
        sc1.setSkippedEdges(tmp, iter2.getEdge());
        tmp = sc1.getEdge();
        EdgeSkipIterState sc2 = g.shortcut(0, 3);
        sc2.setWeight(w.calcWeight(sc1, false, x) + w.calcWeight(iter3, false, x)).setDistance(3 * dist).setFlags(oneDirFlags);
        sc2.setSkippedEdges(tmp, iter3.getEdge());
        tmp = sc2.getEdge();
        sc1 = g.shortcut(0, 4);
        sc1.setWeight(w.calcWeight(sc2, false, x) + w.calcWeight(iter4, false, x)).setDistance(4).setFlags(oneDirFlags);
        sc1.setSkippedEdges(tmp, iter4.getEdge());
        tmp = sc1.getEdge();
        sc2 = g.shortcut(0, 5);
        sc2.setWeight(w.calcWeight(sc1, false, x) + w.calcWeight(iter5, false, x)).setDistance(5).setFlags(oneDirFlags);
        sc2.setSkippedEdges(tmp, iter5.getEdge());
        tmp = sc2.getEdge();
        sc1 = g.shortcut(0, 6);
        sc1.setWeight(w.calcWeight(sc2, false, x) + w.calcWeight(iter6, false, x)).setDistance(6).setFlags(oneDirFlags);
        sc1.setSkippedEdges(tmp, iter6.getEdge());
        g.setLevel(0, 10);
        g.setLevel(6, 9);
        g.setLevel(5, 8);
        g.setLevel(4, 7);
        g.setLevel(3, 6);
        g.setLevel(2, 5);
        g.setLevel(1, 4);
        g.setLevel(10, 3);
    }

    @Test
    public void testUnpackingOrder()
    {
        LevelGraphStorage g = (LevelGraphStorage) createGraph();
        initUnpackingGraph(g, weighting);
        PrepareContractionHierarchies prepare = new PrepareContractionHierarchies(dir, g, carEncoder, weighting, tMode);
        RoutingAlgorithm algo = prepare.createAlgo(g, new AlgorithmOptions(AlgorithmOptions.DIJKSTRA_BI, carEncoder, weighting, tMode));
        Path p = algo.calcPath(10, 6);
        assertEquals(7, p.getDistance(), 1e-5);
        assertEquals(Helper.createTList(10, 0, 1, 2, 3, 4, 5, 6), p.calcNodes());
    }

    @Test
    public void testUnpackingOrder_Fastest()
    {
        LevelGraphStorage g = (LevelGraphStorage) createGraph();
        Weighting w = new FastestWeighting(carEncoder);
        initUnpackingGraph(g, w);

        PrepareContractionHierarchies prepare = new PrepareContractionHierarchies(dir, g, carEncoder, weighting, tMode);
        RoutingAlgorithm algo = prepare.createAlgo(g, new AlgorithmOptions(AlgorithmOptions.DIJKSTRA_BI, carEncoder, weighting, tMode));
        Path p = algo.calcPath(10, 6);
        assertEquals(7, p.getDistance(), 1e-1);
        assertEquals(Helper.createTList(10, 0, 1, 2, 3, 4, 5, 6), p.calcNodes());
    }

    @Test
    public void testCircleBug()
    {
        LevelGraph g = createGraph();
        //  /--1
        // -0--/
        //  |
        g.edge(0, 1, 10, true);
        g.edge(0, 1, 4, true);
        g.edge(0, 2, 10, true);
        g.edge(0, 3, 10, true);
        PrepareContractionHierarchies prepare = new PrepareContractionHierarchies(dir, g, carEncoder, weighting, tMode);
        prepare.doWork();
        assertEquals(0, prepare.getShortcuts());
    }

    @Test
    public void testBug178()
    {
        // 5--------6__
        // |        |  \
        // 0-1->-2--3--4
        //   \-<-/
        //
        LevelGraph g = createGraph();
        g.edge(1, 2, 1, false);
        g.edge(2, 1, 1, false);

        g.edge(5, 0, 1, true);
        g.edge(5, 6, 1, true);
        g.edge(0, 1, 1, true);
        g.edge(2, 3, 1, true);
        g.edge(3, 4, 1, true);
        g.edge(6, 3, 1, true);

        PrepareContractionHierarchies prepare = new PrepareContractionHierarchies(dir, g, carEncoder, weighting, tMode);
        prepare.doWork();
        assertEquals(2, prepare.getShortcuts());
    }

    // 0-1-2-3-4
    // |     / |
    // |    8  |
    // \   /   /
    //  7-6-5-/
    void initBiGraph( Graph graph )
    {
        graph.edge(0, 1, 100, true);
        graph.edge(1, 2, 1, true);
        graph.edge(2, 3, 1, true);
        graph.edge(3, 4, 1, true);
        graph.edge(4, 5, 25, true);
        graph.edge(5, 6, 25, true);
        graph.edge(6, 7, 5, true);
        graph.edge(7, 0, 5, true);
        graph.edge(3, 8, 20, true);
        graph.edge(8, 6, 20, true);
    }

    // 0-1-.....-9-10
    // |         ^   \
    // |         |    |
    // 17-16-...-11<-/
    public static void initDirected2( Graph g )
    {
        g.edge(0, 1, 1, true);
        g.edge(1, 2, 1, true);
        g.edge(2, 3, 1, true);
        g.edge(3, 4, 1, true);
        g.edge(4, 5, 1, true);
        g.edge(5, 6, 1, true);
        g.edge(6, 7, 1, true);
        g.edge(7, 8, 1, true);
        g.edge(8, 9, 1, true);
        g.edge(9, 10, 1, true);
        g.edge(10, 11, 1, false);
        g.edge(11, 12, 1, true);
        g.edge(11, 9, 3, false);
        g.edge(12, 13, 1, true);
        g.edge(13, 14, 1, true);
        g.edge(14, 15, 1, true);
        g.edge(15, 16, 1, true);
        g.edge(16, 17, 1, true);
        g.edge(17, 0, 1, true);
    }

    //       8
    //       |
    //    6->0->1->3->7
    //    |        |
    //    |        v
    //10<-2---4<---5
    //    9
    public static void initDirected1( Graph g )
    {
        g.edge(0, 8, 1, true);
        g.edge(0, 1, 1, false);
        g.edge(1, 3, 1, false);
        g.edge(3, 7, 1, false);
        g.edge(3, 5, 1, false);
        g.edge(5, 4, 1, false);
        g.edge(4, 2, 1, true);
        g.edge(2, 9, 1, false);
        g.edge(2, 10, 1, false);
        g.edge(2, 6, 1, true);
        g.edge(6, 0, 1, false);
    }

    // prepare-routing.svg
    public static LevelGraph initShortcutsGraph( LevelGraph g )
    {
        g.edge(0, 1, 1, true);
        g.edge(0, 2, 1, true);
        g.edge(1, 2, 1, true);
        g.edge(2, 3, 1, true);
        g.edge(1, 4, 1, true);
        g.edge(2, 9, 1, true);
        g.edge(9, 3, 1, true);
        g.edge(10, 3, 1, true);
        g.edge(4, 5, 1, true);
        g.edge(5, 6, 1, true);
        g.edge(6, 7, 1, true);
        g.edge(7, 8, 1, true);
        g.edge(8, 9, 1, true);
        g.edge(4, 11, 1, true);
        g.edge(9, 14, 1, true);
        g.edge(10, 14, 1, true);
        g.edge(11, 12, 1, true);
        g.edge(12, 15, 1, true);
        g.edge(12, 13, 1, true);
        g.edge(13, 16, 1, true);
        g.edge(15, 16, 2, true);
        g.edge(14, 16, 1, true);
        return g;
    }

    //    public static void printEdges(LevelGraph g) {
//        RawEdgeIterator iter = g.getAllEdges();
//        while (iter.next()) {
//            EdgeSkipIterator single = g.getEdgeProps(iter.edge(), iter.nodeB());
//            System.out.println(iter.nodeA() + "<->" + iter.nodeB() + " \\"
//                    + single.skippedEdge1() + "," + single.skippedEdge2() + " (" + iter.edge() + ")"
//                    + ", dist: " + (float) iter.weight()
//                    + ", level:" + g.getLevel(iter.nodeA()) + "<->" + g.getLevel(iter.nodeB())
//                    + ", bothDir:" + CarFlagEncoder.isBoth(iter.setProperties()));
//        }
//        System.out.println("---");
//    }
    @Test
    public void testBits()
    {
        int fromNode = Integer.MAX_VALUE / 3 * 2;
        int endNode = Integer.MAX_VALUE / 37 * 17;

        long edgeId = (long) fromNode << 32 | endNode;
        assertEquals((BitUtil.BIG.toBitString(edgeId)),
                BitUtil.BIG.toLastBitString(fromNode, 32) + BitUtil.BIG.toLastBitString(endNode, 32));
    }
}


File: core/src/test/java/com/graphhopper/routing/util/Bike2WeightFlagEncoderTest.java
/*
 *  Licensed to Peter Karich under one or more contributor license
 *  agreements. See the NOTICE file distributed with this work for
 *  additional information regarding copyright ownership.
 *
 *  Peter Karich licenses this file to you under the Apache License,
 *  Version 2.0 (the "License"); you may not use this file except
 *  in compliance with the License. You may obtain a copy of the
 *  License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing.util;

import com.graphhopper.reader.OSMWay;
import com.graphhopper.storage.*;
import com.graphhopper.util.EdgeIteratorState;
import com.graphhopper.util.GHUtility;
import com.graphhopper.util.Helper;
import org.junit.Test;

import static org.junit.Assert.*;

/**
 * @author Peter Karich
 */
public class Bike2WeightFlagEncoderTest extends BikeFlagEncoderTest
{
    private final EncodingManager em = new EncodingManager("bike,bike2");

    @Override
    protected BikeCommonFlagEncoder createBikeEncoder()
    {
        return (BikeCommonFlagEncoder) em.getEncoder("bike2");
    }

    private Graph initExampleGraph()
    {
        GraphStorage gs = new GraphHopperStorage(new RAMDirectory(), em, true).create(1000);
        NodeAccess na = gs.getNodeAccess();
        // 50--(0.0001)-->49--(0.0004)-->55--(0.0005)-->60
        na.setNode(0, 51.1, 12.001, 50);
        na.setNode(1, 51.1, 12.002, 60);
        EdgeIteratorState edge = gs.edge(0, 1).
                setWayGeometry(Helper.createPointList3D(51.1, 12.0011, 49, 51.1, 12.0015, 55));
        edge.setDistance(100);

        edge.setFlags(encoder.setReverseSpeed(encoder.setProperties(10, true, true), 15));
        return gs;
    }

    @Test
    public void testApplyWayTags()
    {
        Graph graph = initExampleGraph();
        EdgeIteratorState edge = GHUtility.getEdge(graph, 0, 1);
        OSMWay way = new OSMWay(1);
        encoder.applyWayTags(way, edge);

        long flags = edge.getFlags();
        // decrease speed
        assertEquals(2, encoder.getSpeed(flags), 1e-1);
        // increase speed but use maximum speed (calculated was 24)
        assertEquals(18, encoder.getReverseSpeed(flags), 1e-1);
    }

    @Test
    public void testUnchangedForStepsBridgeAndTunnel()
    {
        Graph graph = initExampleGraph();
        EdgeIteratorState edge = GHUtility.getEdge(graph, 0, 1);
        long oldFlags = edge.getFlags();
        OSMWay way = new OSMWay(1);
        way.setTag("highway", "steps");
        encoder.applyWayTags(way, edge);

        assertEquals(oldFlags, edge.getFlags());
    }

    @Test
    public void testSetSpeed0_issue367()
    {
        long flags = encoder.setProperties(10, true, true);
        flags = encoder.setSpeed(flags, 0);

        assertEquals(0, encoder.getSpeed(flags), .1);
        assertEquals(10, encoder.getReverseSpeed(flags), .1);
        assertFalse(encoder.isForward(flags));
        assertTrue(encoder.isBackward(flags));
    }
}


File: core/src/test/java/com/graphhopper/routing/util/CarFlagEncoderTest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 *
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing.util;

import com.graphhopper.reader.OSMNode;
import com.graphhopper.reader.OSMWay;
import org.junit.Test;

import static org.junit.Assert.*;

/**
 * @author Peter Karich
 */
public class CarFlagEncoderTest
{
    private final EncodingManager em = new EncodingManager("CAR,BIKE,FOOT");
    private final CarFlagEncoder encoder = (CarFlagEncoder) em.getEncoder("CAR");

    @Test
    public void testAccess()
    {
        OSMWay way = new OSMWay(1);
        assertFalse(encoder.acceptWay(way) > 0);
        way.setTag("highway", "service");
        assertTrue(encoder.acceptWay(way) > 0);
        way.setTag("access", "no");
        assertFalse(encoder.acceptWay(way) > 0);

        way.clearTags();
        way.setTag("highway", "track");
        assertTrue(encoder.acceptWay(way) > 0);

        way.setTag("motorcar", "no");
        assertFalse(encoder.acceptWay(way) > 0);

        // for now allow grade1+2+3 for every country, see #253
        way.clearTags();
        way.setTag("highway", "track");
        way.setTag("tracktype", "grade2");
        assertTrue(encoder.acceptWay(way) > 0);
        way.setTag("tracktype", "grade4");
        assertFalse(encoder.acceptWay(way) > 0);

        way.clearTags();
        way.setTag("highway", "service");
        way.setTag("access", "no");
        way.setTag("motorcar", "yes");
        assertTrue(encoder.acceptWay(way) > 0);

        way.clearTags();
        way.setTag("highway", "service");
        way.setTag("access", "delivery");
        assertFalse(encoder.acceptWay(way) > 0);

        way.clearTags();
        way.setTag("highway", "unclassified");
        way.setTag("ford", "yes");
        assertFalse(encoder.acceptWay(way) > 0);
        way.setTag("motorcar", "yes");
        assertTrue(encoder.acceptWay(way) > 0);

        way.clearTags();
        way.setTag("route", "ferry");
        assertTrue(encoder.acceptWay(way) > 0);
        assertTrue(encoder.isFerry(encoder.acceptWay(way)));
        way.setTag("motorcar", "no");
        assertFalse(encoder.acceptWay(way) > 0);

        way.clearTags();
        way.setTag("route", "ferry");
        way.setTag("foot", "yes");
        assertFalse(encoder.acceptWay(way) > 0);
        assertFalse(encoder.isFerry(encoder.acceptWay(way)));
    }

    @Test
    public void testOneway()
    {
        OSMWay way = new OSMWay(1);
        way.setTag("highway", "primary");
        long flags = encoder.handleWayTags(way, encoder.acceptWay(way), 0);
        assertTrue(encoder.isForward(flags));
        assertTrue(encoder.isBackward(flags));
        way.setTag("oneway", "yes");
        flags = encoder.handleWayTags(way, encoder.acceptWay(way), 0);
        assertTrue(encoder.isForward(flags));
        assertFalse(encoder.isBackward(flags));
        way.clearTags();

        way.setTag("highway", "tertiary");
        flags = encoder.handleWayTags(way, encoder.acceptWay(way), 0);
        assertTrue(encoder.isForward(flags));
        assertTrue(encoder.isBackward(flags));
        way.clearTags();

        way.setTag("highway", "tertiary");
        way.setTag("vehicle:forward", "no");
        flags = encoder.handleWayTags(way, encoder.acceptWay(way), 0);
        assertFalse(encoder.isForward(flags));
        assertTrue(encoder.isBackward(flags));
        way.clearTags();

        way.setTag("highway", "tertiary");
        way.setTag("vehicle:backward", "no");
        flags = encoder.handleWayTags(way, encoder.acceptWay(way), 0);
        assertTrue(encoder.isForward(flags));
        assertFalse(encoder.isBackward(flags));
        way.clearTags();
    }

    @Test
    public void testMilitaryAccess()
    {
        OSMWay way = new OSMWay(1);
        way.setTag("highway", "track");
        way.setTag("access", "military");
        assertFalse(encoder.acceptWay(way) > 0);
    }

    @Test
    public void testSetAccess()
    {
        assertTrue(encoder.isForward(encoder.setProperties(0, true, true)));
        assertTrue(encoder.isBackward(encoder.setProperties(0, true, true)));

        assertTrue(encoder.isForward(encoder.setProperties(0, true, false)));
        assertFalse(encoder.isBackward(encoder.setProperties(0, true, false)));

        assertFalse(encoder.isForward(encoder.setProperties(0, false, true)));
        assertTrue(encoder.isBackward(encoder.setProperties(0, false, true)));

        assertTrue(encoder.isForward(encoder.flagsDefault(true, true)));
        assertTrue(encoder.isBackward(encoder.flagsDefault(true, true)));

        assertTrue(encoder.isForward(encoder.flagsDefault(true, false)));
        assertFalse(encoder.isBackward(encoder.flagsDefault(true, false)));

        long flags = encoder.flagsDefault(true, true);
        // disable access
        assertFalse(encoder.isForward(encoder.setAccess(flags, false, false)));
        assertFalse(encoder.isBackward(encoder.setAccess(flags, false, false)));
    }

    @Test
    public void testMaxSpeed()
    {
        OSMWay way = new OSMWay(1);
        way.setTag("highway", "trunk");
        way.setTag("maxspeed", "500");
        long allowed = encoder.acceptWay(way);
        long encoded = encoder.handleWayTags(way, allowed, 0);
        assertEquals(140, encoder.getSpeed(encoded), 1e-1);

        way = new OSMWay(1);
        way.setTag("highway", "primary");
        way.setTag("maxspeed:backward", "10");
        way.setTag("maxspeed:forward", "20");
        encoded = encoder.handleWayTags(way, encoder.acceptWay(way), 0);
        assertEquals(10, encoder.getSpeed(encoded), 1e-1);

        way = new OSMWay(1);
        way.setTag("highway", "primary");
        way.setTag("maxspeed:forward", "20");
        encoded = encoder.handleWayTags(way, encoder.acceptWay(way), 0);
        assertEquals(20, encoder.getSpeed(encoded), 1e-1);

        way = new OSMWay(1);
        way.setTag("highway", "primary");
        way.setTag("maxspeed:backward", "20");
        encoded = encoder.handleWayTags(way, encoder.acceptWay(way), 0);
        assertEquals(20, encoder.getSpeed(encoded), 1e-1);

        way = new OSMWay(1);
        way.setTag("highway", "motorway");
        way.setTag("maxspeed", "none");
        encoded = encoder.handleWayTags(way, encoder.acceptWay(way), 0);
        assertEquals(125, encoder.getSpeed(encoded), .1);
    }

    @Test
    public void testSpeed()
    {
        // limit bigger than default road speed
        OSMWay way = new OSMWay(1);
        way.setTag("highway", "trunk");
        way.setTag("maxspeed", "110");
        long allowed = encoder.acceptWay(way);
        long encoded = encoder.handleWayTags(way, allowed, 0);
        assertEquals(100, encoder.getSpeed(encoded), 1e-1);

        way.clearTags();
        way.setTag("highway", "residential");
        way.setTag("surface", "cobblestone");
        allowed = encoder.acceptWay(way);
        encoded = encoder.handleWayTags(way, allowed, 0);
        assertEquals(30, encoder.getSpeed(encoded), 1e-1);

        way.clearTags();
        way.setTag("highway", "track");
        allowed = encoder.acceptWay(way);
        encoded = encoder.handleWayTags(way, allowed, 0);
        assertEquals(15, encoder.getSpeed(encoded), 1e-1);

        way.clearTags();
        way.setTag("highway", "track");
        way.setTag("tracktype", "grade1");
        allowed = encoder.acceptWay(way);
        encoded = encoder.handleWayTags(way, allowed, 0);
        assertEquals(20, encoder.getSpeed(encoded), 1e-1);

        try
        {
            encoder.setSpeed(0, -1);
            assertTrue(false);
        } catch (IllegalArgumentException ex)
        {
        }
    }

    @Test
    public void testSetSpeed()
    {
        assertEquals(10, encoder.getSpeed(encoder.setSpeed(0, 10)), 1e-1);
    }

    @Test
    public void testSetSpeed0_issue367()
    {
        long flags = encoder.setProperties(10, true, true);
        flags = encoder.setSpeed(flags, encoder.speedFactor * 0.49);

        assertEquals(0, encoder.getSpeed(flags), .1);
        assertEquals(0, encoder.getReverseSpeed(flags), .1);
        assertFalse(encoder.isForward(flags));
        assertFalse(encoder.isBackward(flags));
    }

    @Test
    public void testRoundabout()
    {
        long flags = encoder.setAccess(0, true, true);
        long resFlags = encoder.setBool(flags, FlagEncoder.K_ROUNDABOUT, true);
        assertTrue(encoder.isBool(resFlags, FlagEncoder.K_ROUNDABOUT));
        assertTrue(encoder.isForward(resFlags));
        assertTrue(encoder.isBackward(resFlags));

        resFlags = encoder.setBool(flags, FlagEncoder.K_ROUNDABOUT, false);
        assertFalse(encoder.isBool(resFlags, FlagEncoder.K_ROUNDABOUT));
        assertTrue(encoder.isForward(resFlags));
        assertTrue(encoder.isBackward(resFlags));

        OSMWay way = new OSMWay(1);
        way.setTag("highway", "motorway");
        flags = encoder.handleWayTags(way, encoder.acceptBit, 0);
        assertTrue(encoder.isForward(flags));
        assertTrue(encoder.isBackward(flags));
        assertFalse(encoder.isBool(flags, FlagEncoder.K_ROUNDABOUT));

        way.setTag("junction", "roundabout");
        flags = encoder.handleWayTags(way, encoder.acceptBit, 0);
        assertTrue(encoder.isForward(flags));
        assertFalse(encoder.isBackward(flags));
        assertTrue(encoder.isBool(flags, FlagEncoder.K_ROUNDABOUT));
    }

    @Test
    public void testRailway()
    {
        OSMWay way = new OSMWay(1);
        way.setTag("highway", "secondary");
        way.setTag("railway", "rail");
        // disallow rail
        assertTrue(encoder.acceptWay(way) == 0);

        way.clearTags();
        way.setTag("highway", "path");
        way.setTag("railway", "abandoned");
        assertTrue(encoder.acceptWay(way) == 0);

        // on disallowed highway, railway is allowed, sometimes incorrectly mapped
        way.setTag("highway", "track");
        assertTrue(encoder.acceptWay(way) > 0);

        // this is fully okay as sometimes old rails are on the road
        way.setTag("highway", "primary");
        way.setTag("railway", "historic");
        assertTrue(encoder.acceptWay(way) > 0);

        way.setTag("motorcar", "no");
        assertTrue(encoder.acceptWay(way) == 0);

        way = new OSMWay(1);
        way.setTag("highway", "secondary");
        way.setTag("railway", "tram");
        // but allow tram to be on the same way
        assertTrue(encoder.acceptWay(way) > 0);

        way = new OSMWay(1);
        way.setTag("route", "shuttle_train");
        way.setTag("motorcar", "yes");
        way.setTag("bicycle", "no");
        way.setTag("duration", "35");
        way.setTag("estimated_distance", 50000);
        // accept
        assertTrue(encoder.acceptWay(way) > 0);
        // calculate speed from estimated_distance and duration
        assertEquals(60, encoder.getSpeed(encoder.handleFerryTags(way, 20, 30, 40)), 1e-1);
    }

    @Test
    public void testSwapDir()
    {
        long swappedFlags = encoder.reverseFlags(encoder.flagsDefault(true, true));
        assertTrue(encoder.isForward(swappedFlags));
        assertTrue(encoder.isBackward(swappedFlags));

        swappedFlags = encoder.reverseFlags(encoder.flagsDefault(true, false));

        assertFalse(encoder.isForward(swappedFlags));
        assertTrue(encoder.isBackward(swappedFlags));

        assertEquals(0, encoder.reverseFlags(0));
    }

    @Test
    public void testBarrierAccess()
    {
        OSMNode node = new OSMNode(1, -1, -1);
        node.setTag("barrier", "lift_gate");
        node.setTag("access", "yes");
        // no barrier!
        assertTrue(encoder.handleNodeTags(node) == 0);

        node = new OSMNode(1, -1, -1);
        node.setTag("barrier", "lift_gate");
        node.setTag("bicycle", "yes");
        // barrier!
        assertTrue(encoder.handleNodeTags(node) > 0);

        node = new OSMNode(1, -1, -1);
        node.setTag("barrier", "lift_gate");
        node.setTag("access", "yes");
        node.setTag("bicycle", "yes");
        // should this be a barrier for motorcars too?
        // assertTrue(encoder.handleNodeTags(node) > 0);

        node = new OSMNode(1, -1, -1);
        node.setTag("barrier", "lift_gate");
        node.setTag("access", "no");
        node.setTag("motorcar", "yes");
        // no barrier!
        assertTrue(encoder.handleNodeTags(node) == 0);

        node = new OSMNode(1, -1, -1);
        node.setTag("barrier", "bollard");
        // barrier!
        assertTrue(encoder.handleNodeTags(node) > 0);

        // ignore other access tags for absolute barriers!
        node.setTag("motorcar", "yes");
        // still barrier!
        assertTrue(encoder.handleNodeTags(node) > 0);
    }

    @Test
    public void testTurnFlagEncoding_noCosts()
    {
        FlagEncoder tmpEnc = new CarFlagEncoder(8, 5, 0);
        EncodingManager em = new EncodingManager(tmpEnc);

        long flags_r0 = tmpEnc.getTurnFlags(true, 0);
        long flags_0 = tmpEnc.getTurnFlags(false, 0);

        long flags_r20 = tmpEnc.getTurnFlags(true, 0);
        long flags_20 = tmpEnc.getTurnFlags(false, 20);

        assertEquals(0, tmpEnc.getTurnCost(flags_r0), 1e-1);
        assertEquals(0, tmpEnc.getTurnCost(flags_0), 1e-1);

        assertEquals(0, tmpEnc.getTurnCost(flags_r20), 1e-1);
        assertEquals(0, tmpEnc.getTurnCost(flags_20), 1e-1);

        assertFalse(tmpEnc.isTurnRestricted(flags_r0));
        assertFalse(tmpEnc.isTurnRestricted(flags_0));

        assertFalse(tmpEnc.isTurnRestricted(flags_r20));
        assertFalse(tmpEnc.isTurnRestricted(flags_20));
    }

    @Test
    public void testTurnFlagEncoding_withCosts()
    {
        FlagEncoder tmpEncoder = new CarFlagEncoder(8, 5, 127);
        EncodingManager em = new EncodingManager(tmpEncoder);

        long flags_r0 = tmpEncoder.getTurnFlags(true, 0);
        long flags_0 = tmpEncoder.getTurnFlags(false, 0);
        assertTrue(Double.isInfinite(tmpEncoder.getTurnCost(flags_r0)));
        assertEquals(0, tmpEncoder.getTurnCost(flags_0), 1e-1);
        assertTrue(tmpEncoder.isTurnRestricted(flags_r0));
        assertFalse(tmpEncoder.isTurnRestricted(flags_0));

        long flags_r20 = tmpEncoder.getTurnFlags(true, 0);
        long flags_20 = tmpEncoder.getTurnFlags(false, 20);
        assertTrue(Double.isInfinite(tmpEncoder.getTurnCost(flags_r20)));
        assertEquals(20, tmpEncoder.getTurnCost(flags_20), 1e-1);
        assertTrue(tmpEncoder.isTurnRestricted(flags_r20));
        assertFalse(tmpEncoder.isTurnRestricted(flags_20));

        long flags_r220 = tmpEncoder.getTurnFlags(true, 0);
        try
        {
            tmpEncoder.getTurnFlags(false, 220);
            assertTrue(false);
        } catch (Exception ex)
        {
        }
        assertTrue(Double.isInfinite(tmpEncoder.getTurnCost(flags_r220)));
        assertTrue(tmpEncoder.isTurnRestricted(flags_r220));
    }

    @Test
    public void testMaxValue()
    {
        CarFlagEncoder instance = new CarFlagEncoder(10, 0.5, 0);
        EncodingManager em = new EncodingManager(instance);
        OSMWay way = new OSMWay(1);
        way.setTag("highway", "motorway_link");
        way.setTag("maxspeed", "60 mph");
        long flags = instance.handleWayTags(way, 1, 0);

        // double speed = AbstractFlagEncoder.parseSpeed("60 mph");
        // => 96.56 * 0.9 => 86.9
        assertEquals(86.9, instance.getSpeed(flags), 1e-1);
        flags = instance.reverseFlags(flags);
        assertEquals(86.9, instance.getSpeed(flags), 1e-1);

        // test that maxPossibleValue  is not exceeded
        way = new OSMWay(2);
        way.setTag("highway", "motorway_link");
        way.setTag("maxspeed", "70 mph");
        flags = instance.handleWayTags(way, 1, 0);
        assertEquals(101.5, instance.getSpeed(flags), .1);
    }

    @Test
    public void testRegisterOnlyOnceAllowed()
    {
        CarFlagEncoder instance = new CarFlagEncoder(10, 0.5, 0);
        EncodingManager em = new EncodingManager(instance);
        try
        {
            em = new EncodingManager(instance);
            assertTrue(false);
        } catch (IllegalStateException ex)
        {
        }
    }

    @Test
    public void testSetToMaxSpeed()
    {
        OSMWay way = new OSMWay(12);
        way.setTag("maxspeed", "90");
        assertEquals(90, encoder.getMaxSpeed(way), 1e-2);
    }

    @Test
    public void testFordAccess()
    {
        OSMNode node = new OSMNode(0, 0.0, 0.0);
        node.setTag("ford", "yes");

        OSMWay way = new OSMWay(1);
        way.setTag("highway", "unclassified");
        way.setTag("ford", "yes");

        // Node and way are initially blocking
        assertTrue(encoder.isBlockFords());
        assertFalse(encoder.acceptWay(way) > 0);
        assertTrue(encoder.handleNodeTags(node) > 0);

        try
        {
            // Now they are passable
            encoder.setBlockFords(false);
            assertTrue(encoder.acceptWay(way) > 0);
            assertFalse(encoder.handleNodeTags(node) > 0);
        } finally
        {
            encoder.setBlockFords(true);
        }
    }

    @Test
    public void testCombination()
    {
        OSMWay way = new OSMWay(123);
        way.setTag("highway", "cycleway");
        way.setTag("sac_scale", "hiking");

        long flags = em.acceptWay(way);
        long edgeFlags = em.handleWayTags(way, flags, 0);
        assertFalse(encoder.isBackward(edgeFlags));
        assertFalse(encoder.isForward(edgeFlags));
        assertTrue(em.getEncoder("bike").isBackward(edgeFlags));
        assertTrue(em.getEncoder("bike").isForward(edgeFlags));
    }
}


File: core/src/test/java/com/graphhopper/routing/util/PrepareRoutingSubnetworksTest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing.util;

import com.graphhopper.storage.GraphBuilder;
import com.graphhopper.storage.GraphStorage;
import com.graphhopper.util.EdgeExplorer;
import com.graphhopper.util.GHUtility;

import gnu.trove.list.array.TIntArrayList;

import java.util.Arrays;
import java.util.List;
import java.util.Map;

import org.junit.*;

import static org.junit.Assert.*;

/**
 * @author Peter Karich
 */
public class PrepareRoutingSubnetworksTest
{
    private final EncodingManager em = new EncodingManager("car");

    GraphStorage createGraph( EncodingManager eman )
    {
        return new GraphBuilder(eman).create();
    }

    GraphStorage createSubnetworkTestGraph()
    {
        GraphStorage g = createGraph(em);
        // big network
        g.edge(1, 2, 1, true);
        g.edge(1, 4, 1, false);
        g.edge(1, 8, 1, true);
        g.edge(2, 4, 1, true);
        g.edge(8, 4, 1, false);
        g.edge(8, 11, 1, true);
        g.edge(12, 11, 1, true);
        g.edge(9, 12, 1, false);
        g.edge(9, 15, 1, true);

        // large network
        g.edge(0, 13, 1, true);
        g.edge(0, 3, 1, true);
        g.edge(0, 7, 1, true);
        g.edge(3, 7, 1, true);
        g.edge(3, 5, 1, true);
        g.edge(13, 5, 1, true);

        // small network
        g.edge(6, 14, 1, true);
        g.edge(10, 14, 1, true);
        return g;
    }

    @Test
    public void testFindSubnetworks()
    {
        GraphStorage g = createSubnetworkTestGraph();
        PrepareRoutingSubnetworks instance = new PrepareRoutingSubnetworks(g, em);
        Map<Integer, Integer> map = instance.findSubnetworks();

        assertEquals(3, map.size());
        // start is at 0 => large network
        assertEquals(5, (int) map.get(0));
        // next smallest and unvisited node is 1 => big network
        assertEquals(8, (int) map.get(1));
        assertEquals(3, (int) map.get(6));
    }

    @Test
    public void testKeepLargestNetworks()
    {
        GraphStorage g = createSubnetworkTestGraph();
        PrepareRoutingSubnetworks instance = new PrepareRoutingSubnetworks(g, em);
        Map<Integer, Integer> map = instance.findSubnetworks();
        instance.keepLargeNetworks(map);
        g.optimize();

        assertEquals(8, g.getNodes());
        assertEquals(Arrays.<String>asList(), GHUtility.getProblems(g));
        map = instance.findSubnetworks();
        assertEquals(1, map.size());
        assertEquals(8, (int) map.get(0));
    }

    GraphStorage createSubnetworkTestGraph2( EncodingManager em )
    {
        GraphStorage g = createGraph(em);
        // large network
        g.edge(0, 1, 1, true);
        g.edge(1, 3, 1, true);
        g.edge(0, 2, 1, true);
        g.edge(2, 3, 1, true);
        g.edge(3, 7, 1, true);
        g.edge(7, 8, 1, true);

        // connecting both but do not allow CAR!
        g.edge(3, 4).setDistance(1);

        // small network
        g.edge(4, 5, 1, true);
        g.edge(5, 6, 1, true);
        g.edge(4, 6, 1, true);
        return g;
    }

    @Test
    public void testRemoveSubnetworkIfOnlyOneVehicle()
    {
        GraphStorage g = createSubnetworkTestGraph2(em);
        PrepareRoutingSubnetworks instance = new PrepareRoutingSubnetworks(g, em);
        instance.setMinNetworkSize(4);
        instance.doWork();
        g.optimize();
        assertEquals(6, g.getNodes());
        assertEquals(Arrays.<String>asList(), GHUtility.getProblems(g));
        EdgeExplorer explorer = g.createEdgeExplorer();
        assertEquals(GHUtility.asSet(2, 1, 5), GHUtility.getNeighbors(explorer.setBaseNode(3)));

        // do not remove because small network is big enough
        g = createSubnetworkTestGraph2(em);
        instance = new PrepareRoutingSubnetworks(g, em);
        instance.setMinNetworkSize(3);
        instance.doWork();
        g.optimize();
        assertEquals(9, g.getNodes());

        // do not remove because two two vehicles
        EncodingManager em2 = new EncodingManager("CAR,BIKE");
        g = createSubnetworkTestGraph2(em2);
        instance = new PrepareRoutingSubnetworks(g, em2);
        instance.setMinNetworkSize(3);
        instance.doWork();
        g.optimize();
        assertEquals(9, g.getNodes());
    }

    GraphStorage createDeadEndUnvisitedNetworkGraph( EncodingManager em )
    {
        GraphStorage g = createGraph(em);
        // 0 <-> 1 <-> 2 <-> 3 <-> 4 <- 5 <-> 6
        g.edge(0, 1, 1, true);
        g.edge(1, 2, 1, true);
        g.edge(2, 3, 1, true);
        g.edge(3, 4, 1, true);
        g.edge(5, 4, 1, false);
        g.edge(5, 6, 1, true);

        // 7 -> 8 <-> 9 <-> 10
        g.edge(7, 8, 1, false);
        g.edge(8, 9, 1, true);
        g.edge(9, 10, 1, true);

        return g;
    }

    GraphStorage createTarjanTestGraph()
    {
        GraphStorage g = createGraph(em);

        g.edge(1, 2, 1, false);
        g.edge(2, 3, 1, false);
        g.edge(3, 1, 1, false);

        g.edge(4, 2, 1, false);
        g.edge(4, 3, 1, false);
        g.edge(4, 5, 1, true);
        g.edge(5, 6, 1, false);

        g.edge(6, 3, 1, false);
        g.edge(6, 7, 1, true);

        g.edge(8, 5, 1, false);
        g.edge(8, 7, 1, false);
        g.edge(8, 8, 1, false);

        return g;
    }

    @Test
    public void testRemoveDeadEndUnvisitedNetworks()
    {
        GraphStorage g = createDeadEndUnvisitedNetworkGraph(em);
        assertEquals(11, g.getNodes());

        PrepareRoutingSubnetworks instance = new PrepareRoutingSubnetworks(g, em).
                setMinOneWayNetworkSize(3);
        int removed = instance.removeDeadEndUnvisitedNetworks(em.getEncoder("car"));

        assertEquals(3, removed);

        g.optimize();
        assertEquals(8, g.getNodes());
    }

    @Test
    public void testTarjan()
    {
        GraphStorage g = createSubnetworkTestGraph();

        // Requires a single vehicle type, otherwise we throw.
        final FlagEncoder flagEncoder = em.getEncoder("car");
        final EdgeFilter filter = new DefaultEdgeFilter(flagEncoder, false, true);

        TarjansStronglyConnectedComponentsAlgorithm tarjan = new TarjansStronglyConnectedComponentsAlgorithm(g, filter);

        List<TIntArrayList> components = tarjan.findComponents();

        assertEquals(4, components.size());
        assertEquals(new TIntArrayList(new int[]
        {
            13, 5, 3, 7, 0
        }), components.get(0));
        assertEquals(new TIntArrayList(new int[]
        {
            2, 4, 12, 11, 8, 1
        }), components.get(1));
        assertEquals(new TIntArrayList(new int[]
        {
            10, 14, 6
        }), components.get(2));
        assertEquals(new TIntArrayList(new int[]
        {
            15, 9
        }), components.get(3));
    }

    // Previous two-pass implementation failed on 1 -> 2 -> 0
    @Test
    public void testNodeOrderingRegression()
    {
        // 1 -> 2 -> 0
        GraphStorage g = createGraph(em);
        g.edge(1, 2, 1, false);
        g.edge(2, 0, 1, false);
        PrepareRoutingSubnetworks instance = new PrepareRoutingSubnetworks(g, em).
                setMinOneWayNetworkSize(2);
        int removed = instance.removeDeadEndUnvisitedNetworks(em.getEncoder("car"));

        assertEquals(3, removed);
    }
}


File: core/src/test/java/com/graphhopper/storage/AbstractGraphStorageTester.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.storage;

import static com.graphhopper.util.GHUtility.count;
import static org.junit.Assert.*;

import java.io.Closeable;
import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import com.graphhopper.routing.util.*;
import com.graphhopper.util.*;
import com.graphhopper.util.shapes.BBox;

/**
 * Abstract test class to be extended for implementations of the Graph interface. Graphs
 * implementing GraphStorage should extend GraphStorageTest instead.
 * <p/>
 * @author Peter Karich
 */
public abstract class AbstractGraphStorageTester
{
    private final String locationParent = "./target/graphstorage";
    protected int defaultSize = 100;
    protected String defaultGraphLoc = "./target/graphstorage/default";
    protected EncodingManager encodingManager = new EncodingManager("CAR,FOOT");
    protected CarFlagEncoder carEncoder = (CarFlagEncoder) encodingManager.getEncoder("CAR");
    protected FootFlagEncoder footEncoder = (FootFlagEncoder) encodingManager.getEncoder("FOOT");
    EdgeFilter carOutFilter = new DefaultEdgeFilter(carEncoder, false, true);
    EdgeFilter carInFilter = new DefaultEdgeFilter(carEncoder, true, false);
    EdgeExplorer carOutExplorer;
    EdgeExplorer carInExplorer;
    EdgeExplorer carAllExplorer;
    protected GraphStorage graph;

    protected GraphStorage createGraph()
    {
        GraphStorage g = createGraph(defaultGraphLoc, false);
        carOutExplorer = g.createEdgeExplorer(carOutFilter);
        carInExplorer = g.createEdgeExplorer(carInFilter);
        carAllExplorer = g.createEdgeExplorer();
        return g;
    }

    abstract GraphStorage createGraph( String location, boolean is3D );

    protected GraphStorage newRAMGraph()
    {
        return new GraphHopperStorage(new RAMDirectory(), encodingManager, false);
    }

    @Before
    public void setUp()
    {
        Helper.removeDir(new File(locationParent));
    }

    @After
    public void tearDown()
    {
        Helper.close((Closeable) graph);
        Helper.removeDir(new File(locationParent));
    }

    @Test
    public void testInfinityWeight()
    {
        graph = createGraph();
        EdgeIteratorState edge = graph.edge(0, 1);
        edge.setDistance(Double.POSITIVE_INFINITY);
        assertTrue(Double.isInfinite(edge.getDistance()));
    }

    @Test
    public void testSetNodes()
    {
        graph = createGraph();
        NodeAccess na = graph.getNodeAccess();
        for (int i = 0; i < defaultSize * 2; i++)
        {
            na.setNode(i, 2 * i, 3 * i);
        }
        graph.edge(defaultSize + 1, defaultSize + 2, 10, true);
        graph.edge(defaultSize + 1, defaultSize + 3, 10, true);
        assertEquals(2, GHUtility.count(carAllExplorer.setBaseNode(defaultSize + 1)));
    }

    @Test
    public void testPropertiesWithNoInit()
    {
        graph = createGraph();
        assertEquals(0, graph.edge(0, 1).getFlags());
        assertEquals(0, graph.edge(0, 2).getDistance(), 1e-6);
    }

    @Test
    public void testCreateLocation()
    {
        graph = createGraph();
        graph.edge(3, 1, 50, true);
        assertEquals(1, count(carOutExplorer.setBaseNode(1)));

        graph.edge(1, 2, 100, true);
        assertEquals(2, count(carOutExplorer.setBaseNode(1)));
    }

    @Test
    public void testEdges()
    {
        graph = createGraph();
        graph.edge(2, 1, 12, true);
        assertEquals(1, count(carOutExplorer.setBaseNode(2)));

        graph.edge(2, 3, 12, true);
        assertEquals(1, count(carOutExplorer.setBaseNode(1)));
        assertEquals(2, count(carOutExplorer.setBaseNode(2)));
        assertEquals(1, count(carOutExplorer.setBaseNode(3)));
    }

    @Test
    public void testUnidirectional()
    {
        graph = createGraph();

        graph.edge(1, 2, 12, false);
        graph.edge(1, 11, 12, false);
        graph.edge(11, 1, 12, false);
        graph.edge(1, 12, 12, false);
        graph.edge(3, 2, 112, false);
        EdgeIterator i = carOutExplorer.setBaseNode(2);
        assertFalse(i.next());

        assertEquals(1, GHUtility.count(carInExplorer.setBaseNode(1)));
        assertEquals(2, GHUtility.count(carInExplorer.setBaseNode(2)));
        assertEquals(0, GHUtility.count(carInExplorer.setBaseNode(3)));

        assertEquals(3, GHUtility.count(carOutExplorer.setBaseNode(1)));
        assertEquals(0, GHUtility.count(carOutExplorer.setBaseNode(2)));
        assertEquals(1, GHUtility.count(carOutExplorer.setBaseNode(3)));
        i = carOutExplorer.setBaseNode(3);
        i.next();
        assertEquals(2, i.getAdjNode());

        i = carOutExplorer.setBaseNode(1);
        assertTrue(i.next());
        assertEquals(12, i.getAdjNode());
        assertTrue(i.next());
        assertEquals(11, i.getAdjNode());
        assertTrue(i.next());
        assertEquals(2, i.getAdjNode());
        assertFalse(i.next());
    }

    @Test
    public void testUnidirectionalEdgeFilter()
    {
        graph = createGraph();

        graph.edge(1, 2, 12, false);
        graph.edge(1, 11, 12, false);
        graph.edge(11, 1, 12, false);
        graph.edge(1, 12, 12, false);
        graph.edge(3, 2, 112, false);
        EdgeIterator i = carOutExplorer.setBaseNode(2);
        assertFalse(i.next());

        assertEquals(4, GHUtility.count(carAllExplorer.setBaseNode(1)));

        assertEquals(1, GHUtility.count(carInExplorer.setBaseNode(1)));
        assertEquals(2, GHUtility.count(carInExplorer.setBaseNode(2)));
        assertEquals(0, GHUtility.count(carInExplorer.setBaseNode(3)));

        assertEquals(3, GHUtility.count(carOutExplorer.setBaseNode(1)));
        assertEquals(0, GHUtility.count(carOutExplorer.setBaseNode(2)));
        assertEquals(1, GHUtility.count(carOutExplorer.setBaseNode(3)));
        i = carOutExplorer.setBaseNode(3);
        i.next();
        assertEquals(2, i.getAdjNode());

        i = carOutExplorer.setBaseNode(1);
        assertTrue(i.next());
        assertEquals(12, i.getAdjNode());
        assertTrue(i.next());
        assertEquals(11, i.getAdjNode());
        assertTrue(i.next());
        assertEquals(2, i.getAdjNode());
        assertFalse(i.next());
    }

    @Test
    public void testUpdateUnidirectional()
    {
        graph = createGraph();

        graph.edge(1, 2, 12, false);
        graph.edge(3, 2, 112, false);
        EdgeIterator i = carOutExplorer.setBaseNode(2);
        assertFalse(i.next());
        i = carOutExplorer.setBaseNode(3);
        assertTrue(i.next());
        assertEquals(2, i.getAdjNode());
        assertFalse(i.next());

        graph.edge(2, 3, 112, false);
        i = carOutExplorer.setBaseNode(2);
        assertTrue(i.next());
        assertEquals(3, i.getAdjNode());
        i = carOutExplorer.setBaseNode(3);
        i.next();
        assertEquals(2, i.getAdjNode());
        assertFalse(i.next());
    }

    @Test
    public void testClone()
    {
        graph = createGraph();
        graph.edge(1, 2, 10, true);
        NodeAccess na = graph.getNodeAccess();
        na.setNode(0, 12, 23);
        na.setNode(1, 8, 13);
        na.setNode(2, 2, 10);
        na.setNode(3, 5, 9);
        graph.edge(1, 3, 10, true);

        Graph clone = graph.copyTo(createGraph(locationParent + "/clone", false));
        assertEquals(graph.getNodes(), clone.getNodes());
        assertEquals(count(carOutExplorer.setBaseNode(1)), count(clone.createEdgeExplorer(carOutFilter).setBaseNode(1)));
        clone.edge(1, 4, 10, true);
        assertEquals(3, count(clone.createEdgeExplorer(carOutFilter).setBaseNode(1)));
        assertEquals(graph.getBounds(), clone.getBounds());
        Helper.close((Closeable) clone);
    }

    @Test
    public void testCopyProperties()
    {
        graph = createGraph();
        EdgeIteratorState edge = graph.edge(1, 3, 10, false).setName("testing").setWayGeometry(Helper.createPointList(1, 2));

        EdgeIteratorState newEdge = graph.edge(1, 3, 10, false);
        edge.copyPropertiesTo(newEdge);
        assertEquals(edge.getName(), newEdge.getName());
        assertEquals(edge.getDistance(), newEdge.getDistance(), 1e-7);
        assertEquals(edge.getFlags(), newEdge.getFlags());
        assertEquals(edge.fetchWayGeometry(0), newEdge.fetchWayGeometry(0));
    }

    @Test
    public void testGetLocations()
    {
        graph = createGraph();
        NodeAccess na = graph.getNodeAccess();
        na.setNode(0, 12, 23);
        na.setNode(1, 22, 23);
        assertEquals(2, graph.getNodes());

        graph.edge(0, 1, 10, true);
        assertEquals(2, graph.getNodes());

        graph.edge(0, 2, 10, true);
        assertEquals(3, graph.getNodes());
        Helper.close((Closeable) graph);

        graph = createGraph();
        assertEquals(0, graph.getNodes());
    }

    @Test
    public void testCopyTo()
    {
        graph = createGraph();
        initExampleGraph(graph);
        GraphStorage gs = newRAMGraph();
        gs.setSegmentSize(8000);
        gs.create(10);
        try
        {
            graph.copyTo(gs);
            checkExampleGraph(gs);
        } catch (Exception ex)
        {
            ex.printStackTrace();
            assertTrue(ex.toString(), false);
        }

        try
        {
            Helper.close((Closeable) graph);
            graph = createGraph();
            gs.copyTo(graph);
            checkExampleGraph(graph);
        } catch (Exception ex)
        {
            ex.printStackTrace();
            assertTrue(ex.toString(), false);
        }
        Helper.close((Closeable) graph);
    }

    @Test
    public void testAddLocation()
    {
        graph = createGraph();
        initExampleGraph(graph);
        checkExampleGraph(graph);
    }

    protected void initExampleGraph( Graph g )
    {
        NodeAccess na = g.getNodeAccess();
        na.setNode(0, 12, 23);
        na.setNode(1, 38.33f, 135.3f);
        na.setNode(2, 6, 139);
        na.setNode(3, 78, 89);
        na.setNode(4, 2, 1);
        na.setNode(5, 7, 5);
        g.edge(0, 1, 12, true);
        g.edge(0, 2, 212, true);
        g.edge(0, 3, 212, true);
        g.edge(0, 4, 212, true);
        g.edge(0, 5, 212, true);
    }

    private void checkExampleGraph( Graph graph )
    {
        NodeAccess na = graph.getNodeAccess();
        assertEquals(12f, na.getLatitude(0), 1e-6);
        assertEquals(23f, na.getLongitude(0), 1e-6);

        assertEquals(38.33f, na.getLatitude(1), 1e-6);
        assertEquals(135.3f, na.getLongitude(1), 1e-6);

        assertEquals(6, na.getLatitude(2), 1e-6);
        assertEquals(139, na.getLongitude(2), 1e-6);

        assertEquals(78, na.getLatitude(3), 1e-6);
        assertEquals(89, na.getLongitude(3), 1e-6);

        assertEquals(GHUtility.asSet(0), GHUtility.getNeighbors(carOutExplorer.setBaseNode((1))));
        assertEquals(GHUtility.asSet(5, 4, 3, 2, 1), GHUtility.getNeighbors(carOutExplorer.setBaseNode(0)));
        try
        {
            assertEquals(0, count(carOutExplorer.setBaseNode(6)));
            // for now return empty iterator
            // assertFalse(true);
        } catch (Exception ex)
        {
        }
    }

    @Test
    public void testDirectional()
    {
        graph = createGraph();
        graph.edge(1, 2, 12, true);
        graph.edge(2, 3, 12, false);
        graph.edge(3, 4, 12, false);
        graph.edge(3, 5, 12, true);
        graph.edge(6, 3, 12, false);

        assertEquals(1, count(carAllExplorer.setBaseNode(1)));
        assertEquals(1, count(carInExplorer.setBaseNode(1)));
        assertEquals(1, count(carOutExplorer.setBaseNode(1)));

        assertEquals(2, count(carAllExplorer.setBaseNode(2)));
        assertEquals(1, count(carInExplorer.setBaseNode(2)));
        assertEquals(2, count(carOutExplorer.setBaseNode(2)));

        assertEquals(4, count(carAllExplorer.setBaseNode(3)));
        assertEquals(3, count(carInExplorer.setBaseNode(3)));
        assertEquals(2, count(carOutExplorer.setBaseNode(3)));

        assertEquals(1, count(carAllExplorer.setBaseNode(4)));
        assertEquals(1, count(carInExplorer.setBaseNode(4)));
        assertEquals(0, count(carOutExplorer.setBaseNode(4)));

        assertEquals(1, count(carAllExplorer.setBaseNode(5)));
        assertEquals(1, count(carInExplorer.setBaseNode(5)));
        assertEquals(1, count(carOutExplorer.setBaseNode(5)));
    }

    @Test
    public void testDozendEdges()
    {
        graph = createGraph();
        graph.edge(1, 2, 12, true);
        assertEquals(1, count(carAllExplorer.setBaseNode(1)));

        graph.edge(1, 3, 13, false);
        assertEquals(2, count(carAllExplorer.setBaseNode(1)));

        graph.edge(1, 4, 14, false);
        assertEquals(3, count(carAllExplorer.setBaseNode(1)));

        graph.edge(1, 5, 15, false);
        assertEquals(4, count(carAllExplorer.setBaseNode(1)));

        graph.edge(1, 6, 16, false);
        assertEquals(5, count(carAllExplorer.setBaseNode(1)));

        graph.edge(1, 7, 16, false);
        assertEquals(6, count(carAllExplorer.setBaseNode(1)));

        graph.edge(1, 8, 16, false);
        assertEquals(7, count(carAllExplorer.setBaseNode(1)));

        graph.edge(1, 9, 16, false);
        assertEquals(8, count(carAllExplorer.setBaseNode(1)));
        assertEquals(8, count(carOutExplorer.setBaseNode(1)));

        assertEquals(1, count(carInExplorer.setBaseNode(1)));
        assertEquals(1, count(carInExplorer.setBaseNode(2)));
    }

    @Test
    public void testCheckFirstNode()
    {
        graph = createGraph();

        assertEquals(0, count(carAllExplorer.setBaseNode(1)));
        graph.edge(0, 1, 12, true);
        assertEquals(1, count(carAllExplorer.setBaseNode(1)));
    }

    @Test
    public void testDeleteNodeForUnidir()
    {
        graph = createGraph();
        NodeAccess na = graph.getNodeAccess();
        na.setNode(10, 10, 1);
        na.setNode(6, 6, 1);
        na.setNode(20, 20, 1);
        na.setNode(21, 21, 1);

        graph.edge(10, 20, 10, false);
        graph.edge(21, 6, 10, false);

        graph.markNodeRemoved(0);
        graph.markNodeRemoved(7);
        assertEquals(22, graph.getNodes());
        graph.optimize();
        assertEquals(20, graph.getNodes());

        assertEquals(1, GHUtility.count(carInExplorer.setBaseNode(getIdOf(graph, 20))));
        assertEquals(0, GHUtility.count(carOutExplorer.setBaseNode(getIdOf(graph, 20))));

        assertEquals(1, GHUtility.count(carOutExplorer.setBaseNode(getIdOf(graph, 10))));
        assertEquals(0, GHUtility.count(carInExplorer.setBaseNode(getIdOf(graph, 10))));

        assertEquals(1, GHUtility.count(carInExplorer.setBaseNode(getIdOf(graph, 6))));
        assertEquals(0, GHUtility.count(carOutExplorer.setBaseNode(getIdOf(graph, 6))));

        assertEquals(1, GHUtility.count(carOutExplorer.setBaseNode(getIdOf(graph, 21))));
        assertEquals(0, GHUtility.count(carInExplorer.setBaseNode(getIdOf(graph, 21))));
    }

    @Test
    public void testComplexDeleteNode()
    {
        testDeleteNodes(21);
    }

    @Test
    public void testComplexDeleteNode2()
    {
        testDeleteNodes(6);
    }

    public void testDeleteNodes( int fillToSize )
    {
        graph = createGraph();
        NodeAccess na = graph.getNodeAccess();
        na.setNode(0, 12, 23);
        na.setNode(1, 38.33f, 135.3f);
        na.setNode(2, 3, 3);
        na.setNode(3, 78, 89);
        na.setNode(4, 2, 1);
        na.setNode(5, 2.5f, 1);

        int deleted = 2;
        for (int i = 6; i < fillToSize; i++)
        {
            na.setNode(i, i * 1.5, i * 1.6);
            if (i % 3 == 0)
            {
                graph.markNodeRemoved(i);
                deleted++;
            } else
            {
                // connect to
                // ... a deleted node
                graph.edge(i, 0, 10 * i, true);
                // ... a non-deleted and non-moved node
                graph.edge(i, 2, 10 * i, true);
                // ... a moved node
                graph.edge(i, fillToSize - 1, 10 * i, true);
            }
        }

        graph.edge(0, 1, 10, true);
        graph.edge(0, 3, 20, false);
        graph.edge(3, 5, 20, true);
        graph.edge(1, 5, 20, false);

        graph.markNodeRemoved(0);
        graph.markNodeRemoved(2);
        // no deletion happend
        assertEquals(fillToSize, graph.getNodes());

        assertEquals(Arrays.<String>asList(), GHUtility.getProblems(graph));

        // now actually perform deletion
        graph.optimize();

        assertEquals(Arrays.<String>asList(), GHUtility.getProblems(graph));

        assertEquals(fillToSize - deleted, graph.getNodes());
        int id1 = getIdOf(graph, 38.33f);
        assertEquals(135.3f, na.getLongitude(id1), 1e-4);
        assertTrue(containsLatitude(graph, carAllExplorer.setBaseNode(id1), 2.5));
        assertFalse(containsLatitude(graph, carAllExplorer.setBaseNode(id1), 12));

        int id3 = getIdOf(graph, 78);
        assertEquals(89, na.getLongitude(id3), 1e-4);
        assertTrue(containsLatitude(graph, carAllExplorer.setBaseNode(id3), 2.5));
        assertFalse(containsLatitude(graph, carAllExplorer.setBaseNode(id3), 12));
    }

    public boolean containsLatitude( Graph g, EdgeIterator iter, double latitude )
    {
        NodeAccess na = g.getNodeAccess();
        while (iter.next())
        {
            if (Math.abs(na.getLatitude(iter.getAdjNode()) - latitude) < 1e-4)
                return true;
        }
        return false;
    }

    @Test
    public void testSimpleDelete()
    {
        graph = createGraph();
        NodeAccess na = graph.getNodeAccess();
        na.setNode(0, 12, 23);
        na.setNode(1, 38.33f, 135.3f);
        na.setNode(2, 3, 3);
        na.setNode(3, 78, 89);

        graph.edge(3, 0, 21, true);
        graph.edge(5, 0, 22, true);
        graph.edge(5, 3, 23, true);

        graph.markNodeRemoved(0);
        graph.markNodeRemoved(3);

        assertEquals(6, graph.getNodes());
        assertEquals(Arrays.<String>asList(), GHUtility.getProblems(graph));

        // now actually perform deletion
        graph.optimize();

        assertEquals(4, graph.getNodes());
        assertEquals(Arrays.<String>asList(), GHUtility.getProblems(graph));
        // shouldn't change anything
        graph.optimize();
        assertEquals(4, graph.getNodes());
        assertEquals(Arrays.<String>asList(), GHUtility.getProblems(graph));
    }

    @Test
    public void testSimpleDelete2()
    {
        graph = createGraph();
        NodeAccess na = graph.getNodeAccess();
        assertEquals(-1, getIdOf(graph, 12));
        na.setNode(9, 9, 1);
        assertEquals(-1, getIdOf(graph, 12));

        na.setNode(11, 11, 1);
        na.setNode(12, 12, 1);

        // mini subnetwork which gets completely removed:
        graph.edge(5, 10, 510, true);
        graph.markNodeRemoved(5);
        graph.markNodeRemoved(10);

        PointList pl = new PointList();
        pl.add(1, 2, Double.NaN);
        pl.add(1, 3, Double.NaN);
        graph.edge(9, 11, 911, true).setWayGeometry(pl);
        graph.edge(9, 12, 912, true).setWayGeometry(pl);

        assertEquals(13, graph.getNodes());
        assertEquals(Arrays.<String>asList(), GHUtility.getProblems(graph));

        // perform deletion
        graph.optimize();

        assertEquals(11, graph.getNodes());
        assertEquals(Arrays.<String>asList(), GHUtility.getProblems(graph));

        int id11 = getIdOf(graph, 11); // is now 10
        int id12 = getIdOf(graph, 12); // is now 5
        int id9 = getIdOf(graph, 9); // is now 9
        assertEquals(GHUtility.asSet(id12, id11), GHUtility.getNeighbors(carAllExplorer.setBaseNode(id9)));
        assertEquals(GHUtility.asSet(id9), GHUtility.getNeighbors(carAllExplorer.setBaseNode(id11)));
        assertEquals(GHUtility.asSet(id9), GHUtility.getNeighbors(carAllExplorer.setBaseNode(id12)));

        EdgeIterator iter = carAllExplorer.setBaseNode(id9);
        assertTrue(iter.next());
        assertEquals(id12, iter.getAdjNode());
        assertEquals(2, iter.fetchWayGeometry(0).getLongitude(0), 1e-7);

        assertTrue(iter.next());
        assertEquals(id11, iter.getAdjNode());
        assertEquals(2, iter.fetchWayGeometry(0).getLongitude(0), 1e-7);
    }

    @Test
    public void testSimpleDelete3()
    {
        graph = createGraph();
        NodeAccess na = graph.getNodeAccess();
        na.setNode(7, 7, 1);
        na.setNode(8, 8, 1);
        na.setNode(9, 9, 1);
        na.setNode(11, 11, 1);

        // mini subnetwork which gets completely removed:
        graph.edge(5, 10, 510, true);
        graph.markNodeRemoved(3);
        graph.markNodeRemoved(4);
        graph.markNodeRemoved(5);
        graph.markNodeRemoved(10);

        graph.edge(9, 11, 911, true);
        graph.edge(7, 9, 78, true);
        graph.edge(8, 9, 89, true);

        // perform deletion
        graph.optimize();

        assertEquals(Arrays.<String>asList(), GHUtility.getProblems(graph));

        assertEquals(3, GHUtility.count(carAllExplorer.setBaseNode(getIdOf(graph, 9))));
        assertEquals(1, GHUtility.count(carAllExplorer.setBaseNode(getIdOf(graph, 7))));
        assertEquals(1, GHUtility.count(carAllExplorer.setBaseNode(getIdOf(graph, 8))));
        assertEquals(1, GHUtility.count(carAllExplorer.setBaseNode(getIdOf(graph, 11))));
    }

    @Test
    public void testDeleteAndOptimize()
    {
        graph = createGraph();
        NodeAccess na = graph.getNodeAccess();
        na.setNode(20, 10, 10);
        na.setNode(21, 10, 11);
        graph.markNodeRemoved(20);
        graph.optimize();
        assertEquals(11, na.getLongitude(20), 1e-5);
    }

    @Test
    public void testBounds()
    {
        graph = createGraph();
        BBox b = graph.getBounds();
        assertEquals(BBox.createInverse(false).maxLat, b.maxLat, 1e-6);

        NodeAccess na = graph.getNodeAccess();
        na.setNode(0, 10, 20);
        assertEquals(10, b.maxLat, 1e-6);
        assertEquals(20, b.maxLon, 1e-6);

        na.setNode(0, 15, -15);
        assertEquals(15, b.maxLat, 1e-6);
        assertEquals(20, b.maxLon, 1e-6);
        assertEquals(10, b.minLat, 1e-6);
        assertEquals(-15, b.minLon, 1e-6);
    }

    @Test
    public void testFlags()
    {
        graph = createGraph();
        graph.edge(0, 1).setDistance(10).setFlags(carEncoder.setProperties(100, true, true));
        graph.edge(2, 3).setDistance(10).setFlags(carEncoder.setProperties(10, true, false));

        EdgeIterator iter = carAllExplorer.setBaseNode(0);
        assertTrue(iter.next());
        assertEquals(carEncoder.setProperties(100, true, true), iter.getFlags());

        iter = carAllExplorer.setBaseNode(2);
        assertTrue(iter.next());
        assertEquals(carEncoder.setProperties(10, true, false), iter.getFlags());

        try
        {
            graph.edge(0, 1).setDistance(-1);
            assertTrue(false);
        } catch (IllegalArgumentException ex)
        {
        }
    }

    @Test
    public void testEdgeProperties()
    {
        graph = createGraph();
        EdgeIteratorState iter1 = graph.edge(0, 1, 10, true);
        EdgeIteratorState iter2 = graph.edge(0, 2, 20, true);

        int edgeId = iter1.getEdge();
        EdgeIteratorState iter = graph.getEdgeProps(edgeId, 0);
        assertEquals(10, iter.getDistance(), 1e-5);

        edgeId = iter2.getEdge();
        iter = graph.getEdgeProps(edgeId, 0);
        assertEquals(2, iter.getBaseNode());
        assertEquals(0, iter.getAdjNode());
        assertEquals(20, iter.getDistance(), 1e-5);

        iter = graph.getEdgeProps(edgeId, 2);
        assertEquals(0, iter.getBaseNode());
        assertEquals(2, iter.getAdjNode());
        assertEquals(20, iter.getDistance(), 1e-5);

        iter = graph.getEdgeProps(edgeId, Integer.MIN_VALUE);
        assertFalse(iter == null);
        assertEquals(0, iter.getBaseNode());
        assertEquals(2, iter.getAdjNode());
        iter = graph.getEdgeProps(edgeId, 1);
        assertTrue(iter == null);

        // delete
        graph.markNodeRemoved(1);
        graph.optimize();

        // throw exception if accessing deleted edge
        try
        {
            graph.getEdgeProps(iter1.getEdge(), -1);
            assertTrue(false);
        } catch (Exception ex)
        {
        }
    }

    @Test
    public void testCreateDuplicateEdges()
    {
        graph = createGraph();
        graph.edge(2, 1, 12, true);
        graph.edge(2, 3, 12, true);
        graph.edge(2, 3, 13, false);
        assertEquals(3, GHUtility.count(carOutExplorer.setBaseNode(2)));

        // no exception        
        graph.getEdgeProps(1, 3);

        // raise exception
        try
        {
            graph.getEdgeProps(4, 3);
            assertTrue(false);
        } catch (Exception ex)
        {
        }
        try
        {
            graph.getEdgeProps(-1, 3);
            assertTrue(false);
        } catch (Exception ex)
        {
        }

        EdgeIterator iter = carOutExplorer.setBaseNode(2);
        assertTrue(iter.next());
        EdgeIteratorState oneIter = graph.getEdgeProps(iter.getEdge(), 3);
        assertEquals(13, oneIter.getDistance(), 1e-6);
        assertEquals(2, oneIter.getBaseNode());
        assertTrue(carEncoder.isForward(oneIter.getFlags()));
        assertFalse(carEncoder.isBackward(oneIter.getFlags()));

        oneIter = graph.getEdgeProps(iter.getEdge(), 2);
        assertEquals(13, oneIter.getDistance(), 1e-6);
        assertEquals(3, oneIter.getBaseNode());
        assertFalse(carEncoder.isForward(oneIter.getFlags()));
        assertTrue(carEncoder.isBackward(oneIter.getFlags()));

        graph.edge(3, 2, 14, true);
        assertEquals(4, GHUtility.count(carOutExplorer.setBaseNode(2)));
    }

    @Test
    public void testIdenticalNodes()
    {
        graph = createGraph();
        graph.edge(0, 0, 100, true);
        assertEquals(1, GHUtility.count(carAllExplorer.setBaseNode(0)));
    }

    @Test
    public void testIdenticalNodes2()
    {
        graph = createGraph();
        graph.edge(0, 0, 100, false);
        graph.edge(0, 0, 100, false);
        assertEquals(2, GHUtility.count(carAllExplorer.setBaseNode(0)));
    }

    @Test
    public void testEdgeReturn()
    {
        graph = createGraph();
        EdgeIteratorState iter = graph.edge(4, 10).setDistance(100).setFlags(carEncoder.setProperties(10, true, false));
        assertEquals(4, iter.getBaseNode());
        assertEquals(10, iter.getAdjNode());
        iter = graph.edge(14, 10).setDistance(100).setFlags(carEncoder.setProperties(10, true, false));
        assertEquals(14, iter.getBaseNode());
        assertEquals(10, iter.getAdjNode());
    }

    @Test
    public void testPillarNodes()
    {
        graph = createGraph();
        NodeAccess na = graph.getNodeAccess();
        na.setNode(0, 0.01, 0.01);
        na.setNode(4, 0.4, 0.4);
        na.setNode(14, 0.14, 0.14);
        na.setNode(10, 0.99, 0.99);

        PointList pointList = Helper.createPointList(1, 1, 1, 2, 1, 3);
        graph.edge(0, 4).setDistance(100).setFlags(carEncoder.setProperties(10, true, false)).setWayGeometry(pointList);
        pointList = Helper.createPointList(1, 5, 1, 6, 1, 7, 1, 8, 1, 9);
        graph.edge(4, 10).setDistance(100).setFlags(carEncoder.setProperties(10, true, false)).setWayGeometry(pointList);
        pointList = Helper.createPointList(1, 13, 1, 12, 1, 11);
        graph.edge(14, 0).setDistance(100).setFlags(carEncoder.setProperties(10, true, false)).setWayGeometry(pointList);

        EdgeIterator iter = carAllExplorer.setBaseNode(0);
        assertTrue(iter.next());
        assertEquals(14, iter.getAdjNode());
        assertPList(Helper.createPointList(1, 11, 1, 12, 1, 13.0), iter.fetchWayGeometry(0));
        assertPList(Helper.createPointList(0.01, 0.01, 1, 11, 1, 12, 1, 13.0), iter.fetchWayGeometry(1));
        assertPList(Helper.createPointList(1, 11, 1, 12, 1, 13.0, 0.14, 0.14), iter.fetchWayGeometry(2));
        assertPList(Helper.createPointList(0.01, 0.01, 1, 11, 1, 12, 1, 13.0, 0.14, 0.14), iter.fetchWayGeometry(3));

        assertTrue(iter.next());
        assertEquals(4, iter.getAdjNode());
        assertPList(Helper.createPointList(1, 1, 1, 2, 1, 3), iter.fetchWayGeometry(0));
        assertPList(Helper.createPointList(0.01, 0.01, 1, 1, 1, 2, 1, 3), iter.fetchWayGeometry(1));
        assertPList(Helper.createPointList(1, 1, 1, 2, 1, 3, 0.4, 0.4), iter.fetchWayGeometry(2));
        assertPList(Helper.createPointList(0.01, 0.01, 1, 1, 1, 2, 1, 3, 0.4, 0.4), iter.fetchWayGeometry(3));

        assertFalse(iter.next());

        iter = carOutExplorer.setBaseNode(0);
        assertTrue(iter.next());
        assertEquals(4, iter.getAdjNode());
        assertPList(Helper.createPointList(1, 1, 1, 2, 1, 3), iter.fetchWayGeometry(0));
        assertFalse(iter.next());

        iter = carInExplorer.setBaseNode(10);
        assertTrue(iter.next());
        assertEquals(4, iter.getAdjNode());
        assertPList(Helper.createPointList(1, 9, 1, 8, 1, 7, 1, 6, 1, 5), iter.fetchWayGeometry(0));
        assertPList(Helper.createPointList(0.99, 0.99, 1, 9, 1, 8, 1, 7, 1, 6, 1, 5), iter.fetchWayGeometry(1));
        assertPList(Helper.createPointList(1, 9, 1, 8, 1, 7, 1, 6, 1, 5, 0.4, 0.4), iter.fetchWayGeometry(2));
        assertPList(Helper.createPointList(0.99, 0.99, 1, 9, 1, 8, 1, 7, 1, 6, 1, 5, 0.4, 0.4), iter.fetchWayGeometry(3));
        assertFalse(iter.next());
    }

    @Test
    public void testFootMix()
    {
        graph = createGraph();
        graph.edge(0, 1).setDistance(10).setFlags(footEncoder.setProperties(10, true, true));
        graph.edge(0, 2).setDistance(10).setFlags(carEncoder.setProperties(10, true, true));
        graph.edge(0, 3).setDistance(10).setFlags(footEncoder.setProperties(10, true, true) | carEncoder.setProperties(10, true, true));
        EdgeExplorer footOutExplorer = graph.createEdgeExplorer(new DefaultEdgeFilter(footEncoder, false, true));
        assertEquals(GHUtility.asSet(3, 1), GHUtility.getNeighbors(footOutExplorer.setBaseNode(0)));
        assertEquals(GHUtility.asSet(3, 2), GHUtility.getNeighbors(carOutExplorer.setBaseNode(0)));
    }

    @Test
    public void testGetAllEdges()
    {
        graph = createGraph();
        graph.edge(0, 1, 2, true);
        graph.edge(3, 1, 1, false);
        graph.edge(3, 2, 1, false);

        EdgeIterator iter = graph.getAllEdges();
        assertTrue(iter.next());
        int edgeId = iter.getEdge();
        assertEquals(0, iter.getBaseNode());
        assertEquals(1, iter.getAdjNode());
        assertEquals(2, iter.getDistance(), 1e-6);

        assertTrue(iter.next());
        int edgeId2 = iter.getEdge();
        assertEquals(1, edgeId2 - edgeId);
        assertEquals(1, iter.getBaseNode());
        assertEquals(3, iter.getAdjNode());

        assertTrue(iter.next());
        assertEquals(2, iter.getBaseNode());
        assertEquals(3, iter.getAdjNode());

        assertFalse(iter.next());
    }

    @Test
    public void testGetAllEdgesWithDelete()
    {
        graph = createGraph();
        NodeAccess na = graph.getNodeAccess();
        na.setNode(0, 0, 5);
        na.setNode(1, 1, 5);
        na.setNode(2, 2, 5);
        na.setNode(3, 3, 5);
        graph.edge(0, 1, 1, true);
        graph.edge(0, 2, 1, true);
        graph.edge(1, 2, 1, true);
        graph.edge(2, 3, 1, true);
        AllEdgesIterator iter = graph.getAllEdges();
        assertEquals(4, GHUtility.count(iter));
        assertEquals(4, iter.getCount());

        // delete
        graph.markNodeRemoved(1);
        graph.optimize();
        iter = graph.getAllEdges();
        assertEquals(2, GHUtility.count(iter));
        assertEquals(4, iter.getCount());

        iter = graph.getAllEdges();
        iter.next();
        EdgeIteratorState eState = iter.detach(false);
        assertEquals(iter.toString(), eState.toString());
        iter.next();
        assertNotEquals(iter.toString(), eState.toString());

        EdgeIteratorState eState2 = iter.detach(true);
        assertEquals(iter.getAdjNode(), eState2.getBaseNode());
        iter.next();
        assertNotEquals(iter.getAdjNode(), eState2.getBaseNode());
    }

    public static void assertPList( PointList expected, PointList list )
    {
        assertEquals("size of point lists is not equal", expected.getSize(), list.getSize());
        for (int i = 0; i < expected.getSize(); i++)
        {
            assertEquals(expected.getLatitude(i), list.getLatitude(i), 1e-4);
            assertEquals(expected.getLongitude(i), list.getLongitude(i), 1e-4);
        }
    }

    public static int getIdOf( Graph g, double latitude )
    {
        int s = g.getNodes();
        NodeAccess na = g.getNodeAccess();
        for (int i = 0; i < s; i++)
        {
            if (Math.abs(na.getLatitude(i) - latitude) < 1e-4)
            {
                return i;
            }
        }
        return -1;
    }

    public static int getIdOf( Graph g, double latitude, double longitude )
    {
        int s = g.getNodes();
        NodeAccess na = g.getNodeAccess();
        for (int i = 0; i < s; i++)
        {
            if (Math.abs(na.getLatitude(i) - latitude) < 1e-4 && Math.abs(na.getLongitude(i) - longitude) < 1e-4)
            {
                return i;
            }
        }
        throw new IllegalArgumentException("did not find node with location " + (float) latitude + "," + (float) longitude);
    }

    @Test
    public void testNameIndex()
    {
        graph = createGraph();
        EdgeIteratorState iter1 = graph.edge(0, 1, 10, true);
        iter1.setName("named street1");

        EdgeIteratorState iter2 = graph.edge(0, 1, 10, true);
        iter2.setName("named street2");

        assertEquals("named street1", graph.getEdgeProps(iter1.getEdge(), iter1.getAdjNode()).getName());
        assertEquals("named street2", graph.getEdgeProps(iter2.getEdge(), iter2.getAdjNode()).getName());
    }

    @Test
    public void test8BytesFlags()
    {
        Directory dir = new RAMDirectory();
        List<FlagEncoder> list = new ArrayList<FlagEncoder>();
        list.add(new TmpCarFlagEncoder(29, 0.001, 0));
        list.add(new TmpCarFlagEncoder(29, 0.001, 0));
        EncodingManager manager = new EncodingManager(list, 8);
        graph = new GraphHopperStorage(dir, manager, false).create(defaultSize);

        EdgeIteratorState edge = graph.edge(0, 1);
        edge.setFlags(Long.MAX_VALUE / 3);
        // System.out.println(BitUtil.LITTLE.toBitString(Long.MAX_VALUE / 3) + "\n" + BitUtil.LITTLE.toBitString(edge.getFlags()));
        assertEquals(Long.MAX_VALUE / 3, edge.getFlags());
        graph.close();

        graph = new GraphHopperStorage(dir, manager, false).create(defaultSize);

        edge = graph.edge(0, 1);
        edge.setFlags(list.get(0).setProperties(99.123, true, true));
        assertEquals(99.123, list.get(0).getSpeed(edge.getFlags()), 1e-3);
        long flags = GHUtility.getEdge(graph, 1, 0).getFlags();
        assertEquals(99.123, list.get(0).getSpeed(flags), 1e-3);
        assertTrue(list.get(0).isForward(flags));
        assertTrue(list.get(0).isBackward(flags));
        edge = graph.edge(2, 3);
        edge.setFlags(list.get(1).setProperties(44.123, true, false));
        assertEquals(44.123, list.get(1).getSpeed(edge.getFlags()), 1e-3);

        flags = GHUtility.getEdge(graph, 3, 2).getFlags();
        assertEquals(44.123, list.get(1).getSpeed(flags), 1e-3);
        assertEquals(44.123, list.get(1).getReverseSpeed(flags), 1e-3);
        assertFalse(list.get(1).isForward(flags));
        assertTrue(list.get(1).isBackward(flags));
    }

    @Test
    public void testEnabledElevation()
    {
        graph = createGraph(defaultGraphLoc, true);
        NodeAccess na = graph.getNodeAccess();
        assertTrue(na.is3D());
        na.setNode(0, 10, 20, -10);
        na.setNode(1, 11, 2, 100);
        assertEquals(-10, na.getEle(0), 1e-1);
        assertEquals(100, na.getEle(1), 1e-1);

        graph.edge(0, 1).setWayGeometry(Helper.createPointList3D(10, 27, 72, 11, 20, 1));
        assertEquals(Helper.createPointList3D(10, 27, 72, 11, 20, 1), GHUtility.getEdge(graph, 0, 1).fetchWayGeometry(0));
        assertEquals(Helper.createPointList3D(10, 20, -10, 10, 27, 72, 11, 20, 1, 11, 2, 100), GHUtility.getEdge(graph, 0, 1).fetchWayGeometry(3));
        assertEquals(Helper.createPointList3D(11, 2, 100, 11, 20, 1, 10, 27, 72, 10, 20, -10), GHUtility.getEdge(graph, 1, 0).fetchWayGeometry(3));
    }

    @Test
    public void testDetachEdge()
    {
        graph = createGraph();
        graph.edge(0, 1, 2, true);
        long flags = carEncoder.setProperties(10, true, false);
        graph.edge(0, 2, 2, true).setWayGeometry(Helper.createPointList(1, 2, 3, 4)).setFlags(flags);
        graph.edge(1, 2, 2, true);

        EdgeIterator iter = graph.createEdgeExplorer().setBaseNode(0);
        try
        {
            // currently not possible to detach without next, without introducing a new property inside EdgeIterable
            iter.detach(false);
            assertTrue(false);
        } catch (Exception ex)
        {
        }

        iter.next();
        EdgeIteratorState edgeState2 = iter.detach(false);
        assertEquals(2, iter.getAdjNode());
        assertEquals(1, edgeState2.fetchWayGeometry(0).getLatitude(0), 1e-1);
        assertEquals(2, edgeState2.getAdjNode());
        assertTrue(carEncoder.isForward(edgeState2.getFlags()));

        EdgeIteratorState edgeState3 = iter.detach(true);
        assertEquals(0, edgeState3.getAdjNode());
        assertEquals(2, edgeState3.getBaseNode());
        assertEquals(3, edgeState3.fetchWayGeometry(0).getLatitude(0), 1e-1);
        assertFalse(carEncoder.isForward(edgeState3.getFlags()));
        assertEquals(GHUtility.getEdge(graph, 0, 2).getFlags(), edgeState2.getFlags());
        assertEquals(GHUtility.getEdge(graph, 2, 0).getFlags(), edgeState3.getFlags());

        iter.next();
        assertEquals(1, iter.getAdjNode());
        assertEquals(2, edgeState2.getAdjNode());
        assertEquals(2, edgeState3.getBaseNode());

        assertEquals(0, iter.fetchWayGeometry(0).size());
        assertEquals(1, edgeState2.fetchWayGeometry(0).getLatitude(0), 1e-1);
        assertEquals(3, edgeState3.fetchWayGeometry(0).getLatitude(0), 1e-1);

        // #162 a directed self referencing edge should be able to reverse its state too
        graph.edge(3, 3, 2, true).setFlags(flags);
        EdgeIterator iter2 = graph.createEdgeExplorer().setBaseNode(3);
        iter2.next();
        assertEquals(edgeState2.getFlags(), iter2.detach(false).getFlags());
        assertEquals(edgeState3.getFlags(), iter2.detach(true).getFlags());
    }

    static class TmpCarFlagEncoder extends CarFlagEncoder
    {
        public TmpCarFlagEncoder( int speedBits, double speedFactor, int maxTurnCosts )
        {
            super(speedBits, speedFactor, maxTurnCosts);
        }
    }
}


File: core/src/test/java/com/graphhopper/storage/GraphHopperStorageTest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.storage;

import com.graphhopper.util.*;
import com.graphhopper.util.shapes.BBox;

import java.io.IOException;

import static org.junit.Assert.*;

import org.junit.Test;

/**
 * @author Peter Karich
 */
public class GraphHopperStorageTest extends AbstractGraphStorageTester
{
    @Override
    public GraphStorage createGraph( String location, boolean enabled3D )
    {
        // reduce segment size in order to test the case where multiple segments come into the game
        GraphStorage gs = newGraph(new RAMDirectory(location), enabled3D);
        gs.setSegmentSize(defaultSize / 2);
        gs.create(defaultSize);
        return gs;
    }

    protected GraphStorage newGraph( Directory dir, boolean enabled3D )
    {
        return new GraphHopperStorage(dir, encodingManager, enabled3D);
    }

    @Test
    public void testNoCreateCalled() throws IOException
    {
        GraphHopperStorage gs = (GraphHopperStorage) new GraphBuilder(encodingManager).build();
        try
        {
            gs.ensureNodeIndex(123);
            assertFalse("AssertionError should be raised", true);
        } catch (AssertionError err)
        {
            assertTrue(true);
        } catch (Exception ex)
        {
            assertFalse("AssertionError should be raised, but was " + ex.toString(), true);
        } finally
        {
            gs.close();
        }
    }

    @Test
    public void testSave_and_fileFormat() throws IOException
    {
        graph = newGraph(new RAMDirectory(defaultGraphLoc, true), true).create(defaultSize);
        NodeAccess na = graph.getNodeAccess();
        assertTrue(na.is3D());
        na.setNode(0, 10, 10, 0);
        na.setNode(1, 11, 20, 1);
        na.setNode(2, 12, 12, 0.4);

        EdgeIteratorState iter2 = graph.edge(0, 1, 100, true);
        iter2.setWayGeometry(Helper.createPointList3D(1.5, 1, 0, 2, 3, 0));
        EdgeIteratorState iter1 = graph.edge(0, 2, 200, true);
        iter1.setWayGeometry(Helper.createPointList3D(3.5, 4.5, 0, 5, 6, 0));
        graph.edge(9, 10, 200, true);
        graph.edge(9, 11, 200, true);
        graph.edge(1, 2, 120, false);

        iter1.setName("named street1");
        iter2.setName("named street2");

        checkGraph(graph);
        graph.flush();
        graph.close();

        graph = newGraph(new MMapDirectory(defaultGraphLoc), true);
        assertTrue(graph.loadExisting());

        assertEquals(12, graph.getNodes());
        checkGraph(graph);

        assertEquals("named street1", graph.getEdgeProps(iter1.getEdge(), iter1.getAdjNode()).getName());
        assertEquals("named street2", graph.getEdgeProps(iter2.getEdge(), iter2.getAdjNode()).getName());
        graph.edge(3, 4, 123, true).setWayGeometry(Helper.createPointList3D(4.4, 5.5, 0, 6.6, 7.7, 0));
        checkGraph(graph);
    }

    protected void checkGraph( Graph g )
    {
        NodeAccess na = g.getNodeAccess();
        assertTrue(na.is3D());
        assertTrue(g.getBounds().isValid());

        assertEquals(new BBox(10, 20, 10, 12, 0, 1), g.getBounds());
        assertEquals(10, na.getLatitude(0), 1e-2);
        assertEquals(10, na.getLongitude(0), 1e-2);
        EdgeExplorer explorer = g.createEdgeExplorer(carOutFilter);
        assertEquals(2, GHUtility.count(explorer.setBaseNode(0)));
        assertEquals(GHUtility.asSet(2, 1), GHUtility.getNeighbors(explorer.setBaseNode(0)));

        EdgeIterator iter = explorer.setBaseNode(0);
        assertTrue(iter.next());
        assertEquals(Helper.createPointList3D(3.5, 4.5, 0, 5, 6, 0), iter.fetchWayGeometry(0));

        assertTrue(iter.next());
        assertEquals(Helper.createPointList3D(1.5, 1, 0, 2, 3, 0), iter.fetchWayGeometry(0));
        assertEquals(Helper.createPointList3D(10, 10, 0, 1.5, 1, 0, 2, 3, 0), iter.fetchWayGeometry(1));
        assertEquals(Helper.createPointList3D(1.5, 1, 0, 2, 3, 0, 11, 20, 1), iter.fetchWayGeometry(2));

        assertEquals(11, na.getLatitude(1), 1e-2);
        assertEquals(20, na.getLongitude(1), 1e-2);
        assertEquals(2, GHUtility.count(explorer.setBaseNode(1)));
        assertEquals(GHUtility.asSet(2, 0), GHUtility.getNeighbors(explorer.setBaseNode(1)));

        assertEquals(12, na.getLatitude(2), 1e-2);
        assertEquals(12, na.getLongitude(2), 1e-2);
        assertEquals(1, GHUtility.count(explorer.setBaseNode(2)));

        assertEquals(GHUtility.asSet(0), GHUtility.getNeighbors(explorer.setBaseNode(2)));

        EdgeIteratorState eib = GHUtility.getEdge(g, 1, 2);
        assertEquals(Helper.createPointList3D(), eib.fetchWayGeometry(0));
        assertEquals(Helper.createPointList3D(11, 20, 1), eib.fetchWayGeometry(1));
        assertEquals(Helper.createPointList3D(12, 12, 0.4), eib.fetchWayGeometry(2));
        assertEquals(GHUtility.asSet(0), GHUtility.getNeighbors(explorer.setBaseNode(2)));
    }

    @Test
    public void internalDisconnect()
    {
        GraphHopperStorage graph = (GraphHopperStorage) createGraph();
        EdgeIteratorState iter0 = graph.edge(0, 1, 10, true);
        EdgeIteratorState iter2 = graph.edge(1, 2, 10, true);
        EdgeIteratorState iter3 = graph.edge(0, 3, 10, true);

        EdgeExplorer explorer = graph.createEdgeExplorer();

        assertEquals(GHUtility.asSet(3, 1), GHUtility.getNeighbors(explorer.setBaseNode(0)));
        assertEquals(GHUtility.asSet(2, 0), GHUtility.getNeighbors(explorer.setBaseNode(1)));
        // remove edge "1-2" but only from 1 not from 2
        graph.internalEdgeDisconnect(iter2.getEdge(), -1, iter2.getBaseNode(), iter2.getAdjNode());
        assertEquals(GHUtility.asSet(0), GHUtility.getNeighbors(explorer.setBaseNode(1)));
        assertEquals(GHUtility.asSet(1), GHUtility.getNeighbors(explorer.setBaseNode(2)));
        // let 0 unchanged -> no side effects
        assertEquals(GHUtility.asSet(3, 1), GHUtility.getNeighbors(explorer.setBaseNode(0)));

        // remove edge "0-1" but only from 0
        graph.internalEdgeDisconnect(iter0.getEdge(), (long) iter3.getEdge() * graph.edgeEntryBytes, iter0.getBaseNode(), iter0.getAdjNode());
        assertEquals(GHUtility.asSet(3), GHUtility.getNeighbors(explorer.setBaseNode(0)));
        assertEquals(GHUtility.asSet(0), GHUtility.getNeighbors(explorer.setBaseNode(3)));
        assertEquals(GHUtility.asSet(0), GHUtility.getNeighbors(explorer.setBaseNode(1)));
        graph.close();
    }

    @Test
    public void testEnsureSize()
    {
        Directory dir = new RAMDirectory();
        graph = newGraph(dir, false).create(defaultSize);
        int testIndex = dir.find("edges").getSegmentSize() * 3;
        graph.edge(0, testIndex, 10, true);

        // test if optimize works without error
        graph.optimize();
    }

    @Test
    public void testBigDataEdge()
    {
        Directory dir = new RAMDirectory();
        GraphHopperStorage graph = new GraphHopperStorage(dir, encodingManager, false);
        graph.create(defaultSize);
        graph.setEdgeCount(Integer.MAX_VALUE / 2);
        assertTrue(graph.getAllEdges().next());
        graph.close();
    }

    @Test
    public void testDoThrowExceptionIfDimDoesNotMatch()
    {
        graph = newGraph(new RAMDirectory(defaultGraphLoc, true), false);
        graph.create(1000);
        graph.flush();
        graph.close();

        graph = newGraph(new RAMDirectory(defaultGraphLoc, true), true);
        try
        {
            graph.loadExisting();
            assertTrue(false);
        } catch (Exception ex)
        {

        }
    }
}


File: core/src/test/java/com/graphhopper/storage/GraphHopperStorageWithTurnCostsTest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.storage;

import java.io.IOException;
import java.util.Random;

import com.graphhopper.util.EdgeIteratorState;
import com.graphhopper.util.Helper;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * @author Karl Hübner
 */
public class GraphHopperStorageWithTurnCostsTest extends GraphHopperStorageTest
{
    private TurnCostExtension turnCostStorage;

    @Override
    protected GraphStorage newGraph( Directory dir, boolean is3D )
    {
        turnCostStorage = new TurnCostExtension();
        return new GraphHopperStorage(dir, encodingManager, is3D, turnCostStorage);
    }

    @Override
    protected GraphStorage newRAMGraph()
    {
        return newGraph(new RAMDirectory(), false);
    }

    @Override
    @Test
    public void testSave_and_fileFormat() throws IOException
    {
        graph = newGraph(new RAMDirectory(defaultGraphLoc, true), true).create(defaultSize);
        NodeAccess na = graph.getNodeAccess();
        assertTrue(na.is3D());
        na.setNode(0, 10, 10, 0);
        na.setNode(1, 11, 20, 1);
        na.setNode(2, 12, 12, 0.4);

        EdgeIteratorState iter2 = graph.edge(0, 1, 100, true);
        iter2.setWayGeometry(Helper.createPointList3D(1.5, 1, 0, 2, 3, 0));
        EdgeIteratorState iter1 = graph.edge(0, 2, 200, true);
        iter1.setWayGeometry(Helper.createPointList3D(3.5, 4.5, 0, 5, 6, 0));
        graph.edge(9, 10, 200, true);
        graph.edge(9, 11, 200, true);
        graph.edge(1, 2, 120, false);

        turnCostStorage.addTurnInfo(iter1.getEdge(), 0, iter2.getEdge(), 1337);
        turnCostStorage.addTurnInfo(iter2.getEdge(), 0, iter1.getEdge(), 666);
        turnCostStorage.addTurnInfo(iter1.getEdge(), 1, iter2.getEdge(), 815);

        iter1.setName("named street1");
        iter2.setName("named street2");

        checkGraph(graph);
        graph.flush();
        graph.close();

        graph = newGraph(new MMapDirectory(defaultGraphLoc), true);
        assertTrue(graph.loadExisting());

        assertEquals(12, graph.getNodes());
        checkGraph(graph);

        assertEquals("named street1", graph.getEdgeProps(iter1.getEdge(), iter1.getAdjNode()).getName());
        assertEquals("named street2", graph.getEdgeProps(iter2.getEdge(), iter2.getAdjNode()).getName());

        assertEquals(1337, turnCostStorage.getTurnCostFlags(iter1.getEdge(), 0, iter2.getEdge()));
        assertEquals(666, turnCostStorage.getTurnCostFlags(iter2.getEdge(), 0, iter1.getEdge()));
        assertEquals(815, turnCostStorage.getTurnCostFlags(iter1.getEdge(), 1, iter2.getEdge()));
        assertEquals(0, turnCostStorage.getTurnCostFlags(iter1.getEdge(), 3, iter2.getEdge()));

        graph.edge(3, 4, 123, true).setWayGeometry(Helper.createPointList3D(4.4, 5.5, 0, 6.6, 7.7, 0));
        checkGraph(graph);
    }

    @Test
    public void testEnsureCapacity() throws IOException
    {
        graph = newGraph(new MMapDirectory(defaultGraphLoc), false);
        graph.setSegmentSize(128);
        graph.create(100); // 100 is the minimum size

        // assert that turnCostStorage can hold 104 turn cost entries at the beginning
        assertEquals(104, turnCostStorage.getCapacity() / 16);

        Random r = new Random();

        NodeAccess na = graph.getNodeAccess();
        for (int i = 0; i < 100; i++)
        {
            double randomLat = 90 * r.nextDouble();
            double randomLon = 180 * r.nextDouble();

            na.setNode(i, randomLat, randomLon);
        }

        // Make node 50 the 'center' node
        for (int nodeId = 51; nodeId < 100; nodeId++)
        {
            graph.edge(50, nodeId, r.nextDouble(), true);
        }
        for (int nodeId = 0; nodeId < 50; nodeId++)
        {
            graph.edge(nodeId, 50, r.nextDouble(), true);
        }

        // add 100 turn cost entries around node 50
        for (int edgeId = 0; edgeId < 50; edgeId++)
        {
            turnCostStorage.addTurnInfo(edgeId, 50, edgeId + 50, 1337);
            turnCostStorage.addTurnInfo(edgeId + 50, 50, edgeId, 1337);
        }

        turnCostStorage.addTurnInfo(0, 50, 1, 1337);
        assertEquals(104, turnCostStorage.getCapacity() / 16); // we are still good here

        turnCostStorage.addTurnInfo(0, 50, 2, 1337);
        // A new segment should be added, which will support 128 / 16 = 8 more entries.
        assertEquals(112, turnCostStorage.getCapacity() / 16);
    }
}


File: core/src/test/java/com/graphhopper/storage/GraphStorageViaMMapTest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.storage;

/**
 * @author Peter Karich
 */
public class GraphStorageViaMMapTest extends AbstractGraphStorageTester
{
    @Override
    public GraphStorage createGraph( String location, boolean is3D )
    {
        GraphStorage gs = new GraphBuilder(encodingManager).set3D(is3D).setLocation(location).setMmap(true).build();
        gs.setSegmentSize(defaultSize / 2);
        gs.create(defaultSize);
        return gs;
    }
}


File: core/src/test/java/com/graphhopper/storage/index/AbstractLocationIndexTester.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 *
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.storage.index;

import com.graphhopper.routing.util.CarFlagEncoder;
import com.graphhopper.routing.util.DefaultEdgeFilter;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.routing.util.FootFlagEncoder;
import com.graphhopper.storage.Directory;
import com.graphhopper.storage.Graph;
import com.graphhopper.storage.GraphHopperStorage;
import com.graphhopper.storage.MMapDirectory;
import com.graphhopper.storage.NodeAccess;
import com.graphhopper.storage.RAMDirectory;
import com.graphhopper.util.DistanceCalc;
import com.graphhopper.util.DistanceCalcEarth;
import com.graphhopper.util.EdgeIterator;
import com.graphhopper.util.Helper;

import java.io.Closeable;
import java.io.File;
import java.util.Random;

import org.junit.After;

import static org.junit.Assert.*;

import org.junit.Before;
import org.junit.Test;

/**
 * @author Peter Karich
 */
public abstract class AbstractLocationIndexTester
{
    String location = "./target/tmp/";
    LocationIndex idx;

    public abstract LocationIndex createIndex( Graph g, int resolution );

    public boolean hasEdgeSupport()
    {
        return false;
    }

    @Before
    public void setUp()
    {
        Helper.removeDir(new File(location));
    }

    @After
    public void tearDown()
    {
        if (idx != null)
            idx.close();
        Helper.removeDir(new File(location));
    }

    @Test
    public void testSimpleGraph()
    {
        Graph g = createGraph(new EncodingManager("CAR"));
        initSimpleGraph(g);

        idx = createIndex(g, -1);
        assertEquals(4, idx.findID(5, 2));
        assertEquals(3, idx.findID(1.5, 2));
        assertEquals(0, idx.findID(-1, -1));

        if (hasEdgeSupport())
        // now get the edge 1-4 and not node 6
        {
            assertEquals(4, idx.findID(4, 0));
        } else
        {
            assertEquals(6, idx.findID(4, 0));
        }
        Helper.close((Closeable) g);
    }

    public void initSimpleGraph( Graph g )
    {
        //  6 |       4
        //  5 |           
        //    |     6
        //  4 |              5
        //  3 |
        //  2 |    1  
        //  1 |          3
        //  0 |    2      
        // -1 | 0   
        // ---|-------------------
        //    |-2 -1 0 1 2 3 4
        //
        NodeAccess na = g.getNodeAccess();
        na.setNode(0, -1, -2);
        na.setNode(1, 2, -1);
        na.setNode(2, 0, 1);
        na.setNode(3, 1, 2);
        na.setNode(4, 6, 1);
        na.setNode(5, 4, 4);
        na.setNode(6, 4.5, -0.5);
        g.edge(0, 1, 3.5, true);
        g.edge(0, 2, 2.5, true);
        g.edge(2, 3, 1, true);
        g.edge(3, 4, 3.2, true);
        g.edge(1, 4, 2.4, true);
        g.edge(3, 5, 1.5, true);
        // make sure 6 is connected
        g.edge(6, 4, 1.2, true);
    }

    @Test
    public void testSimpleGraph2()
    {
        Graph g = createGraph(new EncodingManager("CAR"));
        initSimpleGraph(g);

        idx = createIndex(g, -1);
        assertEquals(4, idx.findID(5, 2));
        assertEquals(3, idx.findID(1.5, 2));
        assertEquals(0, idx.findID(-1, -1));
        assertEquals(6, idx.findID(4.5, -0.5));
        if (hasEdgeSupport())
        {
            assertEquals(4, idx.findID(4, 1));
            assertEquals(4, idx.findID(4, 0));
        } else
        {
            assertEquals(6, idx.findID(4, 1));
            assertEquals(6, idx.findID(4, 0));
        }
        assertEquals(6, idx.findID(4, -2));
        assertEquals(5, idx.findID(3, 3));
        Helper.close((Closeable) g);
    }

    @Test
    public void testGrid()
    {
        Graph g = createSampleGraph(new EncodingManager("CAR"));
        int locs = g.getNodes();

        idx = createIndex(g, -1);
        // if we would use less array entries then some points gets the same key so avoid that for this test
        // e.g. for 16 we get "expected 6 but was 9" i.e 6 was overwritten by node j9 which is a bit closer to the grid center        
        // go through every point of the graph if all points are reachable
        NodeAccess na = g.getNodeAccess();
        for (int i = 0; i < locs; i++)
        {
            double lat = na.getLatitude(i);
            double lon = na.getLongitude(i);
            assertEquals("nodeId:" + i + " " + (float) lat + "," + (float) lon, i, idx.findID(lat, lon));
        }

        // hit random lat,lon and compare result to full index
        Random rand = new Random(12);
        LocationIndex fullIndex;
        if (hasEdgeSupport())
            fullIndex = new Location2IDFullWithEdgesIndex(g);
        else
            fullIndex = new Location2IDFullIndex(g);

        DistanceCalc dist = new DistanceCalcEarth();
        for (int i = 0; i < 100; i++)
        {
            double lat = rand.nextDouble() * 5;
            double lon = rand.nextDouble() * 5;
            int fullId = fullIndex.findID(lat, lon);
            double fullLat = na.getLatitude(fullId);
            double fullLon = na.getLongitude(fullId);
            float fullDist = (float) dist.calcDist(lat, lon, fullLat, fullLon);
            int newId = idx.findID(lat, lon);
            double newLat = na.getLatitude(newId);
            double newLon = na.getLongitude(newId);
            float newDist = (float) dist.calcDist(lat, lon, newLat, newLon);

            if (testGridIgnore(i))
            {
                continue;
            }

            assertTrue(i + " orig:" + (float) lat + "," + (float) lon
                            + " full:" + fullLat + "," + fullLon + " fullDist:" + fullDist
                            + " found:" + newLat + "," + newLon + " foundDist:" + newDist,
                    Math.abs(fullDist - newDist) < 50000);
        }
        fullIndex.close();
        Helper.close((Closeable) g);
    }

    // our simple index has only one node per tile => problems if multiple subnetworks
    boolean testGridIgnore( int i )
    {
        return false;
    }

    @Test
    public void testSinglePoints120()
    {
        Graph g = createSampleGraph(new EncodingManager("CAR"));
        idx = createIndex(g, -1);

        assertEquals(1, idx.findID(1.637, 2.23));
        assertEquals(10, idx.findID(3.649, 1.375));
        assertEquals(9, idx.findID(3.3, 2.2));
        assertEquals(6, idx.findID(3.0, 1.5));

        assertEquals(10, idx.findID(3.8, 0));
        assertEquals(10, idx.findID(3.8466, 0.021));
        Helper.close((Closeable) g);
    }

    @Test
    public void testSinglePoints32()
    {
        Graph g = createSampleGraph(new EncodingManager("CAR"));
        idx = createIndex(g, -1);

        // 10 or 6
        assertEquals(10, idx.findID(3.649, 1.375));
        assertEquals(10, idx.findID(3.8465748, 0.021762699));
        if (hasEdgeSupport())
        {
            assertEquals(4, idx.findID(2.485, 1.373));
        } else
        {
            assertEquals(6, idx.findID(2.485, 1.373));
        }
        assertEquals(0, idx.findID(0.64628404, 0.53006625));
        Helper.close((Closeable) g);
    }

    @Test
    public void testNoErrorOnEdgeCase_lastIndex()
    {
        final EncodingManager encodingManager = new EncodingManager("CAR");
        int locs = 10000;
        Graph g = createGraph(new MMapDirectory(location), encodingManager, false);
        NodeAccess na = g.getNodeAccess();
        Random rand = new Random(12);
        for (int i = 0; i < locs; i++)
        {
            na.setNode(i, (float) rand.nextDouble() * 10 + 10, (float) rand.nextDouble() * 10 + 10);
        }
        idx = createIndex(g, 200);
        Helper.close((Closeable) g);
    }

    Graph createGraph( EncodingManager encodingManager )
    {
        return createGraph(new RAMDirectory(), encodingManager, false);
    }

    Graph createGraph( Directory dir, EncodingManager encodingManager, boolean is3D )
    {
        return new GraphHopperStorage(dir, encodingManager, is3D).create(100);
    }

    public Graph createSampleGraph( EncodingManager encodingManager )
    {
        Graph graph = createGraph(encodingManager);
        // length does not matter here but lat,lon and outgoing edges do!

//        
//   lat             /--------\
//    5   o-        p--------\ q
//          \  /-----\-----n | |
//    4       k    /--l--    m/                 
//           / \  j      \   |              
//    3     |   g  \  h---i  /             
//          |       \    /  /             
//    2     e---------f--  /
//                   /  \-d
//    1        /--b--      \               
//            |    \--------c
//    0       a                  
//        
//   lon: 0   1   2   3   4   5
        int a0 = 0;
        NodeAccess na = graph.getNodeAccess();
        na.setNode(0, 0, 1.0001f);
        int b1 = 1;
        na.setNode(1, 1, 2);
        int c2 = 2;
        na.setNode(2, 0.5f, 4.5f);
        int d3 = 3;
        na.setNode(3, 1.5f, 3.8f);
        int e4 = 4;
        na.setNode(4, 2.01f, 0.5f);
        int f5 = 5;
        na.setNode(5, 2, 3);
        int g6 = 6;
        na.setNode(6, 3, 1.5f);
        int h7 = 7;
        na.setNode(7, 2.99f, 3.01f);
        int i8 = 8;
        na.setNode(8, 3, 4);
        int j9 = 9;
        na.setNode(9, 3.3f, 2.2f);
        int k10 = 10;
        na.setNode(10, 4, 1);
        int l11 = 11;
        na.setNode(11, 4.1f, 3);
        int m12 = 12;
        na.setNode(12, 4, 4.5f);
        int n13 = 13;
        na.setNode(13, 4.5f, 4.1f);
        int o14 = 14;
        na.setNode(14, 5, 0);
        int p15 = 15;
        na.setNode(15, 4.9f, 2.5f);
        int q16 = 16;
        na.setNode(16, 5, 5);
        // => 17 locations

        graph.edge(a0, b1, 1, true);
        graph.edge(c2, b1, 1, true);
        graph.edge(c2, d3, 1, true);
        graph.edge(f5, b1, 1, true);
        graph.edge(e4, f5, 1, true);
        graph.edge(m12, d3, 1, true);
        graph.edge(e4, k10, 1, true);
        graph.edge(f5, d3, 1, true);
        graph.edge(f5, i8, 1, true);
        graph.edge(f5, j9, 1, true);
        graph.edge(k10, g6, 1, true);
        graph.edge(j9, l11, 1, true);
        graph.edge(i8, l11, 1, true);
        graph.edge(i8, h7, 1, true);
        graph.edge(k10, n13, 1, true);
        graph.edge(k10, o14, 1, true);
        graph.edge(l11, p15, 1, true);
        graph.edge(m12, p15, 1, true);
        graph.edge(q16, p15, 1, true);
        graph.edge(q16, m12, 1, true);
        return graph;
    }

    @Test
    public void testDifferentVehicles()
    {
        final EncodingManager encodingManager = new EncodingManager("CAR,FOOT");
        Graph g = createGraph(encodingManager);
        initSimpleGraph(g);
        idx = createIndex(g, -1);
        assertEquals(1, idx.findID(1, -1));

        // now make all edges from node 1 accessible for CAR only
        EdgeIterator iter = g.createEdgeExplorer().setBaseNode(1);
        CarFlagEncoder carEncoder = (CarFlagEncoder) encodingManager.getEncoder("CAR");
        while (iter.next())
        {
            iter.setFlags(carEncoder.setProperties(50, true, true));
        }
        idx.close();

        idx = createIndex(g, -1);
        FootFlagEncoder footEncoder = (FootFlagEncoder) encodingManager.getEncoder("FOOT");
        assertEquals(2, idx.findClosest(1, -1, new DefaultEdgeFilter(footEncoder)).getClosestNode());
        Helper.close((Closeable) g);
    }
}


File: core/src/test/java/com/graphhopper/storage/index/Location2IDQuadtreeTest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.storage.index;

import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.storage.Graph;
import com.graphhopper.storage.MMapDirectory;
import com.graphhopper.storage.RAMDirectory;

import static org.junit.Assert.*;

import org.junit.Test;

/**
 * @author Peter Karich
 */
public class Location2IDQuadtreeTest extends AbstractLocationIndexTester
{
    @Override
    public LocationIndex createIndex( Graph g, int resolution )
    {
        if (resolution < 0)
            resolution = 120;
        return new Location2IDQuadtree(g, new MMapDirectory(location + "loc2idIndex")).
                setResolution(resolution).prepareIndex();
    }

    @Test
    public void testNormedDist()
    {
        Location2IDQuadtree index = new Location2IDQuadtree(createGraph(new EncodingManager("car")), new RAMDirectory());
        index.initAlgo(5, 6);
        assertEquals(1, index.getNormedDist(0, 1), 1e-6);
        assertEquals(2, index.getNormedDist(0, 7), 1e-6);
        assertEquals(2, index.getNormedDist(7, 2), 1e-6);
        assertEquals(1, index.getNormedDist(7, 1), 1e-6);
        assertEquals(4, index.getNormedDist(13, 25), 1e-6);
        assertEquals(8, index.getNormedDist(15, 25), 1e-6);
    }

    @Override
    boolean testGridIgnore( int i )
    {
        // conceptual limitation where we are stuck in a blind alley limited
        // to the current tile
        if (i == 6 || i == 36 || i == 90 || i == 96)
        {
            return true;
        }
        return false;
    }

    @Override
    public void testDifferentVehicles()
    {
        // currently unsupported
    }
}


File: core/src/test/java/com/graphhopper/storage/index/LocationIndexTreeForLevelGraphTest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 *
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.storage.index;

import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.routing.util.FlagEncoder;
import com.graphhopper.storage.Directory;
import com.graphhopper.storage.Graph;
import com.graphhopper.storage.LevelGraph;
import com.graphhopper.storage.LevelGraphStorage;
import com.graphhopper.storage.NodeAccess;
import com.graphhopper.storage.RAMDirectory;
import com.graphhopper.util.EdgeIteratorState;
import com.graphhopper.util.EdgeSkipIterState;
import com.graphhopper.util.Helper;
import gnu.trove.list.TIntList;
import gnu.trove.set.TIntSet;
import gnu.trove.set.hash.TIntHashSet;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;

import org.junit.Test;

import static org.junit.Assert.*;

/**
 * @author Peter Karich
 */
public class LocationIndexTreeForLevelGraphTest extends LocationIndexTreeTest
{
    @Override
    public LocationIndexTree createIndex( Graph g, int resolution )
    {
        if (resolution < 0)
            resolution = 500000;
        return (LocationIndexTree) createIndexNoPrepare(g, resolution).prepareIndex();
    }

    @Override
    public LocationIndexTree createIndexNoPrepare( Graph g, int resolution )
    {
        Directory dir = new RAMDirectory(location);
        LocationIndexTree tmpIdx = new LocationIndexTree(g.getBaseGraph(), dir);
        tmpIdx.setResolution(resolution);
        return tmpIdx;
    }

    @Override
    LevelGraph createGraph( Directory dir, EncodingManager encodingManager, boolean is3D )
    {
        return new LevelGraphStorage(dir, encodingManager, is3D).create(100);
    }

    @Test
    public void testLevelGraph()
    {
        LevelGraph g = createGraph(new RAMDirectory(), encodingManager, false);
        // 0
        // 1
        // 2
        //  3
        //   4
        NodeAccess na = g.getNodeAccess();
        na.setNode(0, 1, 0);
        na.setNode(1, 0.5, 0);
        na.setNode(2, 0, 0);
        na.setNode(3, -1, 1);
        na.setNode(4, -2, 2);

        EdgeIteratorState iter1 = g.edge(0, 1, 10, true);
        EdgeIteratorState iter2 = g.edge(1, 2, 10, true);
        EdgeIteratorState iter3 = g.edge(2, 3, 14, true);
        EdgeIteratorState iter4 = g.edge(3, 4, 14, true);

        // create shortcuts
        FlagEncoder car = encodingManager.getEncoder("CAR");
        long flags = car.setProperties(60, true, true);
        EdgeSkipIterState iter5 = g.shortcut(0, 2);
        iter5.setDistance(20).setFlags(flags);
        iter5.setSkippedEdges(iter1.getEdge(), iter2.getEdge());
        EdgeSkipIterState iter6 = g.shortcut(2, 4);
        iter6.setDistance(28).setFlags(flags);
        iter6.setSkippedEdges(iter3.getEdge(), iter4.getEdge());
        EdgeSkipIterState tmp = g.shortcut(0, 4);
        tmp.setDistance(40).setFlags(flags);
        tmp.setSkippedEdges(iter5.getEdge(), iter6.getEdge());

        LocationIndex index = createIndex(g, -1);
        assertEquals(2, index.findID(0, 0.5));
    }

    @Test
    public void testSortHighLevelFirst()
    {
        final LevelGraph lg = createGraph(new RAMDirectory(), encodingManager, false);
        lg.getNodeAccess().ensureNode(4);
        lg.setLevel(1, 10);
        lg.setLevel(2, 30);
        lg.setLevel(3, 20);
        TIntList tlist = Helper.createTList(1, 2, 3);

        // nodes with high level should come first to be covered by lower level nodes
        ArrayList<Integer> list = Helper.tIntListToArrayList(tlist);
        Collections.sort(list, new Comparator<Integer>()
        {
            @Override
            public int compare( Integer o1, Integer o2 )
            {
                return lg.getLevel(o2) - lg.getLevel(o1);
            }
        });
        tlist.clear();
        tlist.addAll(list);
        assertEquals(Helper.createTList(2, 3, 1), tlist);
    }

    @Test
    public void testLevelGraphBug()
    {
        // 0
        // |
        // | X  2--3
        // |
        // 1

        LevelGraphStorage lg = (LevelGraphStorage) createGraph(new RAMDirectory(), encodingManager, false);
        NodeAccess na = lg.getNodeAccess();
        na.setNode(0, 1, 0);
        na.setNode(1, 0, 0);
        na.setNode(2, 0.5, 0.5);
        na.setNode(3, 0.5, 1);
        EdgeIteratorState iter1 = lg.edge(1, 0, 100, true);
        lg.edge(2, 3, 100, true);

        lg.setLevel(0, 11);
        lg.setLevel(1, 10);
        // disconnect higher 0 from lower 1
        lg.disconnect(lg.createEdgeExplorer(), iter1);

        lg.setLevel(2, 12);
        lg.setLevel(3, 13);
        // disconnect higher 3 from lower 2
        lg.disconnect(lg.createEdgeExplorer(), iter1);

        LocationIndexTree index = createIndex(lg, 100000);

        // very close to 2, but should match the edge 0--1
        TIntHashSet set = index.findNetworkEntries(0.51, 0.2, index.maxRegionSearch);
        assertEquals(0, index.findID(0.51, 0.2));
        assertEquals(1, index.findID(0.1, 0.1));
        assertEquals(2, index.findID(0.51, 0.51));
        assertEquals(3, index.findID(0.51, 1.1));
        TIntSet expectedSet = new TIntHashSet();
        expectedSet.add(0);
        expectedSet.add(2);
        assertEquals(expectedSet, set);
    }
}


File: core/src/test/java/com/graphhopper/storage/index/LocationIndexTreeTest.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 *
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.storage.index;

import com.graphhopper.routing.util.EdgeFilter;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.storage.Directory;
import com.graphhopper.storage.Graph;
import com.graphhopper.storage.NodeAccess;
import com.graphhopper.storage.RAMDirectory;
import com.graphhopper.util.*;
import com.graphhopper.util.shapes.GHPoint;
import gnu.trove.set.hash.TIntHashSet;

import java.util.Arrays;

import org.junit.Test;

import static org.junit.Assert.*;

/**
 * @author Peter Karich
 */
public class LocationIndexTreeTest extends AbstractLocationIndexTester
{

    protected final EncodingManager encodingManager = new EncodingManager("CAR");

    @Override
    public LocationIndexTree createIndex( Graph g, int resolution )
    {
        if (resolution < 0)
            resolution = 500000;
        return (LocationIndexTree) createIndexNoPrepare(g, resolution).prepareIndex();
    }

    public LocationIndexTree createIndexNoPrepare( Graph g, int resolution )
    {
        Directory dir = new RAMDirectory(location);
        LocationIndexTree tmpIDX = new LocationIndexTree(g, dir);
        tmpIDX.setResolution(resolution);
        return tmpIDX;
    }

    @Override
    public boolean hasEdgeSupport()
    {
        return true;
    }

    //  0------\
    // /|       \
    // |1----3-\|
    // |    /   4
    // 2---/---/
    Graph createTestGraph()
    {
        Graph graph = createGraph(new RAMDirectory(), encodingManager, false);
        NodeAccess na = graph.getNodeAccess();
        na.setNode(0, 0.5, -0.5);
        na.setNode(1, -0.5, -0.5);
        na.setNode(2, -1, -1);
        na.setNode(3, -0.4, 0.9);
        na.setNode(4, -0.6, 1.6);
        graph.edge(0, 1, 1, true);
        graph.edge(0, 2, 1, true);
        graph.edge(0, 4, 1, true);
        graph.edge(1, 3, 1, true);
        graph.edge(2, 3, 1, true);
        graph.edge(2, 4, 1, true);
        graph.edge(3, 4, 1, true);
        return graph;
    }

    @Test
    public void testSnappedPointAndGeometry()
    {
        Graph graph = createTestGraph();
        LocationIndex index = createIndex(graph, -1);
        // query directly the tower node
        QueryResult res = index.findClosest(-0.4, 0.9, EdgeFilter.ALL_EDGES);
        assertEquals(new GHPoint(-0.4, 0.9), res.getSnappedPoint());
        res = index.findClosest(-0.6, 1.6, EdgeFilter.ALL_EDGES);
        assertEquals(new GHPoint(-0.6, 1.6), res.getSnappedPoint());

        // query the edge (1,3)
        res = index.findClosest(-0.2, 0.3, EdgeFilter.ALL_EDGES);
        assertEquals(new GHPoint(-0.441624, 0.317259), res.getSnappedPoint());
    }

    @Test
    public void testInMemIndex()
    {
        Graph graph = createTestGraph();
        LocationIndexTree index = createIndexNoPrepare(graph, 50000);
        index.prepareAlgo();
        LocationIndexTree.InMemConstructionIndex inMemIndex = index.getPrepareInMemIndex();
        assertEquals(Helper.createTList(4, 4), index.getEntries());

        assertEquals(4, inMemIndex.getEntriesOf(0).size());
        assertEquals(10, inMemIndex.getEntriesOf(1).size());
        assertEquals(0, inMemIndex.getEntriesOf(2).size());
        // [LEAF 0 {} {0, 2}, LEAF 2 {} {0, 1}, LEAF 1 {} {2}, LEAF 3 {} {1}, LEAF 8 {} {0}, LEAF 10 {} {0}, LEAF 9 {} {0}, LEAF 4 {} {2}, LEAF 6 {} {0, 1, 2, 3}, LEAF 5 {} {0, 2, 3}, LEAF 7 {} {1, 2, 3}, LEAF 13 {} {1}]        
        // System.out.println(inMemIndex.getLayer(2));

        index.dataAccess.create(10);
        inMemIndex.store(inMemIndex.root, LocationIndexTree.START_POINTER);
        // [LEAF 0 {2} {},    LEAF 2 {1} {},    LEAF 1 {2} {}, LEAF 3 {1} {}, LEAF 8 {0} {}, LEAF 10 {0} {}, LEAF 9 {0} {}, LEAF 4 {2} {}, LEAF 6 {0, 3} {},       LEAF 5 {0, 2, 3} {}, LEAF 7 {1, 2, 3} {}, LEAF 13 {1} {}]
        // System.out.println(inMemIndex.getLayer(2));

        TIntHashSet set = new TIntHashSet();
        set.add(0);
        assertEquals(set, index.findNetworkEntries(0.5, -0.5, 2));
        set.add(1);
        set.add(2);
        assertEquals(set, index.findNetworkEntries(-0.5, -0.9, 2));
        assertEquals(2, index.findID(-0.5, -0.9));

        // The optimization if(dist > normedHalf) => feed nodeA or nodeB
        // although this reduces chance of nodes outside of the tile
        // in practice it even increases file size!?
        // Is this due to the LevelGraph disconnect problem?
//        set.clear();
//        set.add(4);
//        assertEquals(set, index.findNetworkEntries(-0.7, 1.5));
//        
//        set.clear();
//        set.add(4);
//        assertEquals(set, index.findNetworkEntries(-0.5, 0.5));
    }

    @Test
    public void testInMemIndex2()
    {
        Graph graph = createTestGraph2();
        LocationIndexTree index = createIndexNoPrepare(graph, 500);
        index.prepareAlgo();
        LocationIndexTree.InMemConstructionIndex inMemIndex = index.getPrepareInMemIndex();
        assertEquals(Helper.createTList(4, 4), index.getEntries());
        assertEquals(3, inMemIndex.getEntriesOf(0).size());
        assertEquals(5, inMemIndex.getEntriesOf(1).size());
        assertEquals(0, inMemIndex.getEntriesOf(2).size());

        index.dataAccess.create(10);
        inMemIndex.store(inMemIndex.root, LocationIndexTree.START_POINTER);

        // 0
        assertEquals(2L, index.keyAlgo.encode(49.94653, 11.57114));
        // 1
        assertEquals(3L, index.keyAlgo.encode(49.94653, 11.57214));
        // 28
        assertEquals(6L, index.keyAlgo.encode(49.95053, 11.57714));
        // 29
        assertEquals(6L, index.keyAlgo.encode(49.95053, 11.57814));
        // 8
        assertEquals(1L, index.keyAlgo.encode(49.94553, 11.57214));
        // 34
        assertEquals(12L, index.keyAlgo.encode(49.95153, 11.57714));

        // Query near point 25 (49.95053, 11.57314).
        // If we would have a perfect compaction (takes a lot longer) we would
        // get only 0 or any node in the lefter greater subgraph.
        // The other subnetwork is already perfect {26}.
        // For compaction see: https://github.com/graphhopper/graphhopper/blob/5594f7f9d98d932f365557dc37b4b2d3b7abf698/core/src/main/java/com/graphhopper/storage/index/Location2NodesNtree.java#L277
        TIntHashSet set = new TIntHashSet();
        set.addAll(Arrays.asList(28, 27, 26, 24, 23, 21, 19, 18, 16, 14, 6, 5, 4, 3, 2, 1, 0));
        assertEquals(set, index.findNetworkEntries(49.950, 11.5732, 1));
    }

    @Test
    public void testInMemIndex3()
    {
        LocationIndexTree index = createIndexNoPrepare(createTestGraph(), 10000);
        index.prepareAlgo();
        LocationIndexTree.InMemConstructionIndex inMemIndex = index.getPrepareInMemIndex();
        assertEquals(Helper.createTList(64, 4), index.getEntries());

        assertEquals(33, inMemIndex.getEntriesOf(0).size());
        assertEquals(69, inMemIndex.getEntriesOf(1).size());
        assertEquals(0, inMemIndex.getEntriesOf(2).size());

        index.dataAccess.create(1024);
        inMemIndex.store(inMemIndex.root, LocationIndexTree.START_POINTER);
        assertEquals(1 << 20, index.getCapacity());

        QueryResult res = index.findClosest(-.5, -.5, EdgeFilter.ALL_EDGES);
        assertEquals(1, res.getClosestNode());
    }

    @Test
    public void testReverseSpatialKey()
    {
        LocationIndexTree index = createIndex(createTestGraph(), 200);
        assertEquals(Helper.createTList(64, 64, 64, 4), index.getEntries());

        // 10111110111110101010
        String str44 = "00000000000000000000000000000000000000000000";
        assertEquals(str44 + "01010101111101111101", BitUtil.BIG.toBitString(index.createReverseKey(1.7, 0.099)));
    }

    @Test
    public void testMoreReal()
    {
        Graph graph = createGraph(new EncodingManager("CAR"));
        NodeAccess na = graph.getNodeAccess();
        na.setNode(1, 51.2492152, 9.4317166);
        na.setNode(0, 52, 9);
        na.setNode(2, 51.2, 9.4);
        na.setNode(3, 49, 10);

        graph.edge(1, 0, 1000, true);
        graph.edge(0, 2, 1000, true);
        graph.edge(0, 3, 1000, true).setWayGeometry(Helper.createPointList(51.21, 9.43));
        LocationIndex index = createIndex(graph, -1);
        assertEquals(2, index.findID(51.2, 9.4));
    }

    //    -1    0   1 1.5
    // --------------------
    // 1|         --A
    //  |    -0--/   \
    // 0|   / | B-\   \
    //  |  /  1/   3--4
    //  |  |/------/  /
    //-1|  2---------/
    //  |
    private Graph createTestGraphWithWayGeometry()
    {
        Graph graph = createGraph(encodingManager);
        NodeAccess na = graph.getNodeAccess();
        na.setNode(0, 0.5, -0.5);
        na.setNode(1, -0.5, -0.5);
        na.setNode(2, -1, -1);
        na.setNode(3, -0.4, 0.9);
        na.setNode(4, -0.6, 1.6);
        graph.edge(0, 1, 1, true);
        graph.edge(0, 2, 1, true);
        // insert A and B, without this we would get 0 for 0,0
        graph.edge(0, 4, 1, true).setWayGeometry(Helper.createPointList(1, 1));
        graph.edge(1, 3, 1, true).setWayGeometry(Helper.createPointList(0, 0));
        graph.edge(2, 3, 1, true);
        graph.edge(2, 4, 1, true);
        graph.edge(3, 4, 1, true);
        return graph;
    }

    @Test
    public void testWayGeometry()
    {
        Graph g = createTestGraphWithWayGeometry();
        LocationIndex index = createIndex(g, -1);
        assertEquals(1, index.findID(0, 0));
        assertEquals(1, index.findID(0, 0.1));
        assertEquals(1, index.findID(0.1, 0.1));
        assertEquals(1, index.findID(-0.5, -0.5));
    }

    @Test
    public void testFindingWayGeometry()
    {
        Graph g = createGraph(encodingManager);
        NodeAccess na = g.getNodeAccess();
        na.setNode(10, 51.2492152, 9.4317166);
        na.setNode(20, 52, 9);
        na.setNode(30, 51.2, 9.4);
        na.setNode(50, 49, 10);
        g.edge(20, 50, 1, true).setWayGeometry(Helper.createPointList(51.25, 9.43));
        g.edge(10, 20, 1, true);
        g.edge(20, 30, 1, true);

        LocationIndex index = createIndex(g, 2000);
        assertEquals(20, index.findID(51.25, 9.43));
    }

    @Test
    public void testEdgeFilter()
    {
        Graph graph = createTestGraph();
        LocationIndexTree index = createIndex(graph, -1);

        assertEquals(1, index.findClosest(-.6, -.6, EdgeFilter.ALL_EDGES).getClosestNode());
        assertEquals(2, index.findClosest(-.6, -.6, new EdgeFilter()
        {
            @Override
            public boolean accept( EdgeIteratorState iter )
            {
                return iter.getBaseNode() == 2 || iter.getAdjNode() == 2;
            }
        }).getClosestNode());
    }

    // see testgraph2.jpg
    Graph createTestGraph2()
    {
        Graph graph = createGraph(new RAMDirectory(), encodingManager, false);
        NodeAccess na = graph.getNodeAccess();
        na.setNode(8, 49.94553, 11.57214);
        na.setNode(9, 49.94553, 11.57314);
        na.setNode(10, 49.94553, 11.57414);
        na.setNode(11, 49.94553, 11.57514);
        na.setNode(12, 49.94553, 11.57614);
        na.setNode(13, 49.94553, 11.57714);

        na.setNode(0, 49.94653, 11.57114);
        na.setNode(1, 49.94653, 11.57214);
        na.setNode(2, 49.94653, 11.57314);
        na.setNode(3, 49.94653, 11.57414);
        na.setNode(4, 49.94653, 11.57514);
        na.setNode(5, 49.94653, 11.57614);
        na.setNode(6, 49.94653, 11.57714);
        na.setNode(7, 49.94653, 11.57814);

        na.setNode(14, 49.94753, 11.57214);
        na.setNode(15, 49.94753, 11.57314);
        na.setNode(16, 49.94753, 11.57614);
        na.setNode(17, 49.94753, 11.57814);

        na.setNode(18, 49.94853, 11.57114);
        na.setNode(19, 49.94853, 11.57214);
        na.setNode(20, 49.94853, 11.57814);

        na.setNode(21, 49.94953, 11.57214);
        na.setNode(22, 49.94953, 11.57614);

        na.setNode(23, 49.95053, 11.57114);
        na.setNode(24, 49.95053, 11.57214);
        na.setNode(25, 49.95053, 11.57314);
        na.setNode(26, 49.95053, 11.57514);
        na.setNode(27, 49.95053, 11.57614);
        na.setNode(28, 49.95053, 11.57714);
        na.setNode(29, 49.95053, 11.57814);

        na.setNode(30, 49.95153, 11.57214);
        na.setNode(31, 49.95153, 11.57314);
        na.setNode(32, 49.95153, 11.57514);
        na.setNode(33, 49.95153, 11.57614);
        na.setNode(34, 49.95153, 11.57714);

        na.setNode(34, 49.95153, 11.57714);

        // to create correct bounds
        // bottom left
        na.setNode(100, 49.941, 11.56614);
        // top right
        na.setNode(101, 49.96053, 11.58814);

        graph.edge(0, 1, 10, true);
        graph.edge(1, 2, 10, true);
        graph.edge(2, 3, 10, true);
        graph.edge(3, 4, 10, true);
        graph.edge(4, 5, 10, true);
        graph.edge(6, 7, 10, true);

        graph.edge(8, 2, 10, true);
        graph.edge(9, 2, 10, true);
        graph.edge(10, 3, 10, true);
        graph.edge(11, 4, 10, true);
        graph.edge(12, 5, 10, true);
        graph.edge(13, 6, 10, true);

        graph.edge(1, 14, 10, true);
        graph.edge(2, 15, 10, true);
        graph.edge(5, 16, 10, true);
        graph.edge(14, 15, 10, true);
        graph.edge(16, 17, 10, true);
        graph.edge(16, 20, 10, true);
        graph.edge(16, 25, 10, true);

        graph.edge(18, 14, 10, true);
        graph.edge(18, 19, 10, true);
        graph.edge(18, 21, 10, true);
        graph.edge(19, 21, 10, true);
        graph.edge(21, 24, 10, true);
        graph.edge(23, 24, 10, true);
        graph.edge(24, 25, 10, true);
        graph.edge(26, 27, 10, true);
        graph.edge(27, 28, 10, true);
        graph.edge(28, 29, 10, true);

        graph.edge(24, 30, 10, true);
        graph.edge(24, 31, 10, true);
        graph.edge(26, 32, 10, true);
        graph.edge(27, 33, 10, true);
        graph.edge(28, 34, 10, true);
        return graph;
    }

    @Test
    public void testRMin()
    {
        Graph graph = createTestGraph();
        LocationIndexTree index = createIndex(graph, 50000);

        //query: 0.05 | -0.3
        DistanceCalc distCalc = new DistancePlaneProjection();

        double rmin = index.calculateRMin(0.05, -0.3);
        double check = distCalc.calcDist(0.05, Math.abs(graph.getNodeAccess().getLon(2)) - index.getDeltaLon(), -0.3, -0.3);

        assertTrue((rmin - check) < 0.0001);

        double rmin2 = index.calculateRMin(0.05, -0.3, 1);
        double check2 = distCalc.calcDist(0.05, Math.abs(graph.getNodeAccess().getLat(0)), -0.3, -0.3);

        assertTrue((rmin2 - check2) < 0.0001);

        TIntHashSet points = new TIntHashSet();
        assertEquals(Double.MAX_VALUE, index.calcMinDistance(0.05, -0.3, points), 1e-1);

        points.add(0);
        points.add(1);
        assertEquals(54757.03, index.calcMinDistance(0.05, -0.3, points), 1e-1);

        /*GraphVisualizer gv = new GraphVisualizer(graph, index.getDeltaLat(), index.getDeltaLon(), index.getCenter(0, 0).lat, index.getCenter(0, 0).lon);
         try {
         Thread.sleep(4000);
         } catch(InterruptedException ie) {}*/
    }
}


File: tools/src/main/java/com/graphhopper/tools/Measurement.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 *
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.tools;

import com.graphhopper.GHRequest;
import com.graphhopper.GHResponse;
import com.graphhopper.GraphHopper;
import com.graphhopper.routing.util.*;
import com.graphhopper.storage.index.LocationIndex;
import com.graphhopper.storage.Graph;
import com.graphhopper.storage.GraphStorage;
import com.graphhopper.storage.NodeAccess;
import com.graphhopper.storage.RAMDirectory;
import com.graphhopper.util.CmdArgs;
import com.graphhopper.util.Constants;
import com.graphhopper.util.DistanceCalc;
import com.graphhopper.util.DistanceCalcEarth;
import com.graphhopper.util.Helper;
import com.graphhopper.util.MiniPerfTest;
import com.graphhopper.util.StopWatch;
import com.graphhopper.util.shapes.BBox;

import java.io.FileWriter;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Random;
import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * @author Peter Karich
 */
public class Measurement
{
    public static void main( String[] strs )
    {
        new Measurement().start(CmdArgs.read(strs));
    }

    private static final Logger logger = LoggerFactory.getLogger(Measurement.class);
    private final Map<String, String> properties = new TreeMap<String, String>();
    private long seed;
    private int maxNode;

    class MeasureHopper extends GraphHopper
    {
        @Override
        protected void prepare()
        {
            // do nothing as we need normal graph first. in second step do it explicitely
        }

        @Override
        protected void ensureNotLoaded()
        {
            // skip check. we know what we are doing
        }

        public void doPostProcessing()
        {
            // re-create index to avoid bug as pickNode in locationIndex.prepare could be wrong while indexing if level is not taken into account and assumed to be 0 for pre-initialized graph            
            StopWatch sw = new StopWatch().start();
            int edges = getGraph().getAllEdges().getCount();
            setAlgorithmFactory(createPrepare());
            super.prepare();
            setLocationIndex(createLocationIndex(new RAMDirectory()));
            put("prepare.time", sw.stop().getTime());
            put("prepare.shortcuts", getGraph().getAllEdges().getCount() - edges);
        }
    }

    // creates properties file in the format key=value
    // Every value is one y-value in a separate diagram with an identical x-value for every Measurement.start call
    void start( CmdArgs args )
    {
        long importTook = args.getLong("graph.importTime", -1);
        put("graph.importTime", importTook);

        String graphLocation = args.get("graph.location", "");
        if (Helper.isEmpty(graphLocation))
            throw new IllegalStateException("no graph.location specified");

        String propLocation = args.get("measurement.location", "");
        if (Helper.isEmpty(propLocation))
            propLocation = "measurement" + new SimpleDateFormat("yyyy-MM-dd_HH_mm_ss").format(new Date()) + ".properties";

        seed = args.getLong("measurement.seed", 123);
        String gitCommit = args.get("measurement.gitinfo", "");
        int count = args.getInt("measurement.count", 5000);

        MeasureHopper hopper = new MeasureHopper();
        hopper.forDesktop();
        if (!hopper.load(graphLocation))
            throw new IllegalStateException("Cannot load existing levelgraph at " + graphLocation);

        GraphStorage g = hopper.getGraph();
        if ("true".equals(g.getProperties().get("prepare.done")))
            throw new IllegalStateException("Graph has to be unprepared but wasn't!");

        String vehicleStr = args.get("graph.flagEncoders", "");
        StopWatch sw = new StopWatch().start();
        try
        {
            maxNode = g.getNodes();
            printGraphDetails(g, vehicleStr);
            printLocationIndexQuery(g, hopper.getLocationIndex(), count);

            // Route via dijkstrabi. Normal routing takes a lot of time => smaller query number than CH
            // => values are not really comparable to routingCH as e.g. the mean distance etc is different            
            hopper.setCHEnable(false);
            printTimeOfRouteQuery(hopper, count / 20, "routing", vehicleStr, true);

            System.gc();

            // route via CH. do preparation before                        
            hopper.setCHEnable(true);
            hopper.doPostProcessing();
            printTimeOfRouteQuery(hopper, count, "routingCH", vehicleStr, true);
            printTimeOfRouteQuery(hopper, count, "routingCH_no_instr", vehicleStr, false);
            logger.info("store into " + propLocation);
        } catch (Exception ex)
        {
            logger.error("Problem while measuring " + graphLocation, ex);
            put("error", ex.toString());
        } finally
        {
            put("measurement.gitinfo", gitCommit);
            put("measurement.count", count);
            put("measurement.seed", seed);
            put("measurement.time", sw.stop().getTime());
            System.gc();
            put("measurement.totalMB", Helper.getTotalMB());
            put("measurement.usedMB", Helper.getUsedMB());
            try
            {
                store(new FileWriter(propLocation), "measurement finish, "
                        + new Date().toString() + ", " + Constants.BUILD_DATE);
            } catch (IOException ex)
            {
                logger.error("Problem while storing properties " + graphLocation + ", " + propLocation, ex);
            }
        }
    }

    private void printGraphDetails( GraphStorage g, String vehicleStr )
    {
        // graph size (edge, node and storage size)
        put("graph.nodes", g.getNodes());
        put("graph.edges", g.getAllEdges().getCount());
        put("graph.sizeInMB", g.getCapacity() / Helper.MB);
        put("graph.encoder", vehicleStr);
    }

    private void printLocationIndexQuery( Graph g, final LocationIndex idx, int count )
    {
        count *= 2;
        final BBox bbox = g.getBounds();
        final double latDelta = bbox.maxLat - bbox.minLat;
        final double lonDelta = bbox.maxLon - bbox.minLon;
        final Random rand = new Random(seed);
        MiniPerfTest miniPerf = new MiniPerfTest()
        {
            @Override
            public int doCalc( boolean warmup, int run )
            {
                double lat = rand.nextDouble() * latDelta + bbox.minLat;
                double lon = rand.nextDouble() * lonDelta + bbox.minLon;
                int val = idx.findClosest(lat, lon, EdgeFilter.ALL_EDGES).getClosestNode();
//                if (!warmup && val >= 0)
//                    list.add(val);

                return val;
            }
        }.setIterations(count).start();

        print("location2id", miniPerf);
    }

    private void printTimeOfRouteQuery( final GraphHopper hopper, int count, String prefix,
                                        final String vehicle, final boolean withInstructions )
    {
        final Graph g = hopper.getGraph();
        final AtomicLong maxDistance = new AtomicLong(0);
        final AtomicLong minDistance = new AtomicLong(Long.MAX_VALUE);
        final AtomicLong distSum = new AtomicLong(0);
        final AtomicLong airDistSum = new AtomicLong(0);
        final AtomicInteger failedCount = new AtomicInteger(0);
        final DistanceCalc distCalc = new DistanceCalcEarth();

//        final AtomicLong extractTimeSum = new AtomicLong(0);
//        final AtomicLong calcPointsTimeSum = new AtomicLong(0);
//        final AtomicLong calcDistTimeSum = new AtomicLong(0);
//        final AtomicLong tmpDist = new AtomicLong(0);
        final Random rand = new Random(seed);
        final NodeAccess na = g.getNodeAccess();
        MiniPerfTest miniPerf = new MiniPerfTest()
        {
            @Override
            public int doCalc( boolean warmup, int run )
            {
                int from = rand.nextInt(maxNode);
                int to = rand.nextInt(maxNode);
                double fromLat = na.getLatitude(from);
                double fromLon = na.getLongitude(from);
                double toLat = na.getLatitude(to);
                double toLon = na.getLongitude(to);
                GHRequest req = new GHRequest(fromLat, fromLon, toLat, toLon).
                        setWeighting("fastest").
                        setVehicle(vehicle);
                req.getHints().put("instructions", withInstructions);
                GHResponse res;
                try
                {
                    res = hopper.route(req);
                } catch (Exception ex)
                {
                    // 'not found' can happen if import creates more than one subnetwork
                    throw new RuntimeException("Error while calculating route! "
                            + "nodes:" + from + " -> " + to + ", request:" + req, ex);
                }

                if (res.hasErrors())
                {
                    if (!warmup)
                        failedCount.incrementAndGet();

                    if (!res.getErrors().get(0).getMessage().toLowerCase().contains("not found"))
                        logger.error("errors should NOT happen in Measurement! " + req + " => " + res.getErrors());

                    return 0;
                }

                if (!warmup)
                {
                    long dist = (long) res.getDistance();
                    distSum.addAndGet(dist);

                    airDistSum.addAndGet((long) distCalc.calcDist(fromLat, fromLon, toLat, toLon));

                    if (dist > maxDistance.get())
                        maxDistance.set(dist);

                    if (dist < minDistance.get())
                        minDistance.set(dist);

//                    extractTimeSum.addAndGet(p.getExtractTime());                    
//                    long start = System.nanoTime();
//                    size = p.calcPoints().getSize();
//                    calcPointsTimeSum.addAndGet(System.nanoTime() - start);
                }

                return res.getPoints().getSize();
            }
        }.setIterations(count).start();

        count -= failedCount.get();
        put(prefix + ".failedCount", failedCount.get());
        put(prefix + ".distanceMin", minDistance.get());
        put(prefix + ".distanceMean", (float) distSum.get() / count);
        put(prefix + ".airDistanceMean", (float) airDistSum.get() / count);
        put(prefix + ".distanceMax", maxDistance.get());

//        put(prefix + ".extractTime", (float) extractTimeSum.get() / count / 1000000f);
//        put(prefix + ".calcPointsTime", (float) calcPointsTimeSum.get() / count / 1000000f);
//        put(prefix + ".calcDistTime", (float) calcDistTimeSum.get() / count / 1000000f);
        print(prefix, miniPerf);
    }

    void print( String prefix, MiniPerfTest perf )
    {
        logger.info(perf.getReport());
        put(prefix + ".sum", perf.getSum());
//        put(prefix+".rms", perf.getRMS());
        put(prefix + ".min", perf.getMin());
        put(prefix + ".mean", perf.getMean());
        put(prefix + ".max", perf.getMax());
    }

    void put( String key, Object val )
    {
        // convert object to string to make serialization possible
        properties.put(key, "" + val);
    }

    private void store( FileWriter fileWriter, String comment ) throws IOException
    {
        fileWriter.append("#" + comment + "\n");
        for (Entry<String, String> e : properties.entrySet())
        {
            fileWriter.append(e.getKey());
            fileWriter.append("=");
            fileWriter.append(e.getValue());
            fileWriter.append("\n");
        }
        fileWriter.flush();
    }
}


File: tools/src/main/java/com/graphhopper/ui/MiniGraphUI.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.ui;

import com.graphhopper.GraphHopper;
import com.graphhopper.coll.GHBitSet;
import com.graphhopper.coll.GHTBitSet;
import com.graphhopper.routing.*;
import com.graphhopper.routing.util.*;
import com.graphhopper.storage.Graph;
import com.graphhopper.storage.NodeAccess;
import com.graphhopper.storage.index.LocationIndexTree;
import com.graphhopper.storage.index.QueryResult;
import com.graphhopper.util.*;
import com.graphhopper.util.shapes.BBox;
import gnu.trove.list.TIntList;

import java.awt.*;
import java.awt.event.*;
import java.util.Random;
import javax.swing.*;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * A rough graphical user interface for visualizing the OSM graph. Mainly for debugging algorithms
 * and spatial datastructures.
 * <p/>
 * Use the project at https://github.com/graphhopper/graphhopper-web for a
 * better/faster/userfriendly/... alternative!
 * <p/>
 * @author Peter Karich
 */
public class MiniGraphUI
{
    public static void main( String[] strs ) throws Exception
    {
        CmdArgs args = CmdArgs.read(strs);
        GraphHopper hopper = new GraphHopper().init(args).importOrLoad();
        boolean debug = args.getBool("minigraphui.debug", false);
        new MiniGraphUI(hopper, debug).visualize();
    }

    private Logger logger = LoggerFactory.getLogger(getClass());
    private Path path;
    private RoutingAlgorithmFactory algoFactory;
    private final Graph graph;
    private final NodeAccess na;
    private LocationIndexTree index;
    private String latLon = "";
    private GraphicsWrapper mg;
    private JPanel infoPanel;
    private LayeredPanel mainPanel;
    private MapLayer roadsLayer;
    private final MapLayer pathLayer;
    private boolean fastPaint = false;
    private final Weighting weighting;
    private final FlagEncoder encoder;
    private AlgorithmOptions algoOpts;

    public MiniGraphUI( GraphHopper hopper, boolean debug )
    {
        this.graph = hopper.getGraph();
        this.na = graph.getNodeAccess();
        algoFactory = hopper.getAlgorithmFactory();
        encoder = hopper.getEncodingManager().getEncoder("car");
        weighting = hopper.createWeighting(new WeightingMap("fastest"), encoder);
        algoOpts = new AlgorithmOptions(AlgorithmOptions.DIJKSTRA_BI, encoder, weighting);

        logger.info("locations:" + graph.getNodes() + ", debug:" + debug + ", algoOpts:" + algoOpts);
        mg = new GraphicsWrapper(graph);

        // prepare node quadtree to 'enter' the graph. create a 313*313 grid => <3km
//         this.index = new DebugLocation2IDQuadtree(roadGraph, mg);
        this.index = (LocationIndexTree) hopper.getLocationIndex();
//        this.algo = new DebugDijkstraBidirection(graph, mg);
        // this.algo = new DijkstraBidirection(graph);
//        this.algo = new DebugAStar(graph, mg);
//        this.algo = new AStar(graph);
//        this.algo = new DijkstraSimple(graph);
//        this.algo = new DebugDijkstraSimple(graph, mg);
        infoPanel = new JPanel()
        {
            @Override
            protected void paintComponent( Graphics g )
            {
                g.setColor(Color.WHITE);
                Rectangle b = infoPanel.getBounds();
                g.fillRect(0, 0, b.width, b.height);

                g.setColor(Color.BLUE);
                g.drawString(latLon, 40, 20);
                g.drawString("scale:" + mg.getScaleX(), 40, 40);
                int w = mainPanel.getBounds().width;
                int h = mainPanel.getBounds().height;
                g.drawString(mg.setBounds(0, w, 0, h).toLessPrecisionString(), 40, 60);
            }
        };

        mainPanel = new LayeredPanel();

        // TODO make it correct with bitset-skipping too
        final GHBitSet bitset = new GHTBitSet(graph.getNodes());
        mainPanel.addLayer(roadsLayer = new DefaultMapLayer()
        {
            Random rand = new Random();

            @Override
            public void paintComponent( Graphics2D g2 )
            {
                clearGraphics(g2);
                int locs = graph.getNodes();
                Rectangle d = getBounds();
                BBox b = mg.setBounds(0, d.width, 0, d.height);
                if (fastPaint)
                {
                    rand.setSeed(0);
                    bitset.clear();
                }

//                g2.setColor(Color.BLUE);
//                double fromLat = 42.56819, fromLon = 1.603231;
//                mg.plotText(g2, fromLat, fromLon, "from");
//                QueryResult from = index.findClosest(fromLat, fromLon, EdgeFilter.ALL_EDGES);
//                double toLat = 42.571034, toLon = 1.520662;
//                mg.plotText(g2, toLat, toLon, "to");
//                QueryResult to = index.findClosest(toLat, toLon, EdgeFilter.ALL_EDGES);
//
//                g2.setColor(Color.RED.brighter().brighter());
//                path = prepare.createAlgo().calcPath(from, to);
//                System.out.println("now: " + path.toDetailsString());
//                plotPath(path, g2, 1);
                g2.setColor(Color.black);

                EdgeExplorer explorer = graph.createEdgeExplorer(EdgeFilter.ALL_EDGES);
                Color[] speedColors = generateColors(15);

                for (int nodeIndex = 0; nodeIndex < locs; nodeIndex++)
                {
                    if (fastPaint && rand.nextInt(30) > 1)
                        continue;
                    double lat = na.getLatitude(nodeIndex);
                    double lon = na.getLongitude(nodeIndex);

                    // mg.plotText(g2, lat, lon, "" + nodeIndex);
                    if (lat < b.minLat || lat > b.maxLat || lon < b.minLon || lon > b.maxLon)
                        continue;

                    EdgeIterator edge = explorer.setBaseNode(nodeIndex);
                    while (edge.next())
                    {
                        int nodeId = edge.getAdjNode();
                        int sum = nodeIndex + nodeId;
                        if (fastPaint)
                        {
                            if (bitset.contains(sum))
                                continue;

                            bitset.add(sum);
                        }
                        double lat2 = na.getLatitude(nodeId);
                        double lon2 = na.getLongitude(nodeId);

                        // mg.plotText(g2, lat * 0.9 + lat2 * 0.1, lon * 0.9 + lon2 * 0.1, iter.getName());
                        //mg.plotText(g2, lat * 0.9 + lat2 * 0.1, lon * 0.9 + lon2 * 0.1, "s:" + (int) encoder.getSpeed(iter.getFlags()));
                        double speed = encoder.getSpeed(edge.getFlags());
                        Color color;
                        if (speed >= 120)
                        {
                            // red
                            color = speedColors[12];
                        } else if (speed >= 100)
                        {
                            color = speedColors[10];
                        } else if (speed >= 80)
                        {
                            color = speedColors[8];
                        } else if (speed >= 60)
                        {
                            color = speedColors[6];
                        } else if (speed >= 50)
                        {
                            color = speedColors[5];
                        } else if (speed >= 40)
                        {
                            color = speedColors[4];
                        } else if (speed >= 30)
                        {
                            color = Color.GRAY;
                        } else
                        {
                            color = Color.LIGHT_GRAY;
                        }

                        g2.setColor(color);
                        mg.plotEdge(g2, lat, lon, lat2, lon2, 1.2f);
                    }
                }

                g2.setColor(Color.WHITE);
                g2.fillRect(0, 0, 1000, 20);
                for (int i = 4; i < speedColors.length; i++)
                {
                    g2.setColor(speedColors[i]);
                    g2.drawString("" + (i * 10), i * 30 - 100, 10);
                }

                g2.setColor(Color.BLACK);
            }
        });

        mainPanel.addLayer(pathLayer = new DefaultMapLayer()
        {
            @Override
            public void paintComponent( Graphics2D g2 )
            {
                if (fromRes == null || toRes == null)
                    return;

                makeTransparent(g2);
                QueryGraph qGraph = new QueryGraph(graph).lookup(fromRes, toRes);
                RoutingAlgorithm algo = algoFactory.createAlgo(qGraph, algoOpts);
                if (algo instanceof DebugAlgo)
                {
                    ((DebugAlgo) algo).setGraphics2D(g2);
                }

                StopWatch sw = new StopWatch().start();
                logger.info("start searching from:" + fromRes + " to:" + toRes + " " + weighting);

//                GHPoint qp = fromRes.getQueryPoint();
//                TIntHashSet set = index.findNetworkEntries(qp.lat, qp.lon, 1);
//                TIntIterator nodeIter = set.iterator();
//                DistanceCalc distCalc = new DistancePlaneProjection();
//                System.out.println("set:" + set.size());
//                while (nodeIter.hasNext())
//                {
//                    int nodeId = nodeIter.next();
//                    double lat = graph.getNodeAccess().getLat(nodeId);
//                    double lon = graph.getNodeAccess().getLon(nodeId);
//                    int dist = (int) Math.round(distCalc.calcDist(qp.lat, qp.lon, lat, lon));
//                    mg.plotText(g2, lat, lon, nodeId + ": " + dist);
//                    mg.plotNode(g2, nodeId, Color.red);
//                }
                path = algo.calcPath(fromRes.getClosestNode(), toRes.getClosestNode());
                sw.stop();

                // if directed edges
                if (!path.isFound())
                {
                    logger.warn("path not found! direction not valid?");
                    return;
                }

                logger.info("found path in " + sw.getSeconds() + "s with nodes:"
                        + path.calcNodes().size() + ", millis: " + path.getTime() + ", " + path);
                g2.setColor(Color.BLUE.brighter().brighter());
                plotPath(path, g2, 1);
            }
        });

        if (debug)
        {
            // disable double buffering for debugging drawing - nice! when do we need DebugGraphics then?
            RepaintManager repaintManager = RepaintManager.currentManager(mainPanel);
            repaintManager.setDoubleBufferingEnabled(false);
            mainPanel.setBuffering(false);
        }
    }

    public Color[] generateColors( int n )
    {
        Color[] cols = new Color[n];
        for (int i = 0; i < n; i++)
        {
            cols[i] = Color.getHSBColor((float) i / (float) n, 0.85f, 1.0f);
        }
        return cols;
    }

    // for debugging
    private Path calcPath( RoutingAlgorithm algo )
    {
//        int from = index.findID(50.042, 10.19);
//        int to = index.findID(50.049, 10.23);
//
////        System.out.println("path " + from + "->" + to);
//        return algo.calcPath(from, to);
        // System.out.println(GraphUtility.getNodeInfo(graph, 60139, new DefaultEdgeFilter(new CarFlagEncoder()).direction(false, true)));
        // System.out.println(((GraphStorage) graph).debug(202947, 10));
//        GraphUtility.printInfo(graph, 106511, 10);
        return algo.calcPath(162810, 35120);
    }

    void plotNodeName( Graphics2D g2, int node )
    {
        double lat = na.getLatitude(node);
        double lon = na.getLongitude(node);
        mg.plotText(g2, lat, lon, "" + node);
    }

    private Path plotPath( Path tmpPath, Graphics2D g2, int w )
    {
        if (!tmpPath.isFound())
        {
            logger.info("nothing found " + w);
            return tmpPath;
        }

        double prevLat = Double.NaN;
        double prevLon = Double.NaN;
        boolean plotNodes = false;
        TIntList nodes = tmpPath.calcNodes();
        if (plotNodes)
        {
            for (int i = 0; i < nodes.size(); i++)
            {
                plotNodeName(g2, nodes.get(i));
            }
        }
        PointList list = tmpPath.calcPoints();
        for (int i = 0; i < list.getSize(); i++)
        {
            double lat = list.getLatitude(i);
            double lon = list.getLongitude(i);
            if (!Double.isNaN(prevLat))
            {
                mg.plotEdge(g2, prevLat, prevLon, lat, lon, w);
            } else
            {
                mg.plot(g2, lat, lon, w);
            }
            prevLat = lat;
            prevLon = lon;
        }
        logger.info("dist:" + tmpPath.getDistance() + ", path points(" + list.getSize() + "):" + list + ", nodes:" + nodes);
        return tmpPath;
    }

    private QueryResult fromRes;
    private QueryResult toRes;

    public void visualize()
    {
        try
        {
            SwingUtilities.invokeAndWait(new Runnable()
            {
                @Override
                public void run()
                {
                    int frameHeight = 800;
                    int frameWidth = 1200;
                    JFrame frame = new JFrame("GraphHopper UI - Small&Ugly ;)");
                    frame.setLayout(new BorderLayout());
                    frame.add(mainPanel, BorderLayout.CENTER);
                    frame.add(infoPanel, BorderLayout.NORTH);

                    infoPanel.setPreferredSize(new Dimension(300, 100));

                    // scale
                    mainPanel.addMouseWheelListener(new MouseWheelListener()
                    {
                        @Override
                        public void mouseWheelMoved( MouseWheelEvent e )
                        {
                            mg.scale(e.getX(), e.getY(), e.getWheelRotation() < 0);
                            repaintRoads();
                        }
                    });

                    // listener to investigate findID behavior
//                    MouseAdapter ml = new MouseAdapter() {
//
//                        @Override public void mouseClicked(MouseEvent e) {
//                            findIDLat = mg.getLat(e.getY());
//                            findIDLon = mg.getLon(e.getX());
//                            findIdLayer.repaint();
//                            mainPanel.repaint();
//                        }
//
//                        @Override public void mouseMoved(MouseEvent e) {
//                            updateLatLon(e);
//                        }
//
//                        @Override public void mousePressed(MouseEvent e) {
//                            updateLatLon(e);
//                        }
//                    };
                    MouseAdapter ml = new MouseAdapter()
                    {
                        // for routing:
                        double fromLat, fromLon;
                        boolean fromDone = false;

                        @Override
                        public void mouseClicked( MouseEvent e )
                        {
                            if (!fromDone)
                            {
                                fromLat = mg.getLat(e.getY());
                                fromLon = mg.getLon(e.getX());
                            } else
                            {
                                double toLat = mg.getLat(e.getY());
                                double toLon = mg.getLon(e.getX());
                                StopWatch sw = new StopWatch().start();
                                logger.info("start searching from " + fromLat + "," + fromLon
                                        + " to " + toLat + "," + toLon);
                                // get from and to node id
                                fromRes = index.findClosest(fromLat, fromLon, EdgeFilter.ALL_EDGES);
                                toRes = index.findClosest(toLat, toLon, EdgeFilter.ALL_EDGES);
                                logger.info("found ids " + fromRes + " -> " + toRes + " in " + sw.stop().getSeconds() + "s");

                                repaintPaths();
                            }

                            fromDone = !fromDone;
                        }

                        boolean dragging = false;

                        @Override
                        public void mouseDragged( MouseEvent e )
                        {
                            dragging = true;
                            fastPaint = true;
                            update(e);
                            updateLatLon(e);
                        }

                        @Override
                        public void mouseReleased( MouseEvent e )
                        {
                            if (dragging)
                            {
                                // update only if mouse release comes from dragging! (at the moment equal to fastPaint)
                                dragging = false;
                                fastPaint = false;
                                update(e);
                            }
                        }

                        public void update( MouseEvent e )
                        {
                            mg.setNewOffset(e.getX() - currentPosX, e.getY() - currentPosY);
                            repaintRoads();
                        }

                        @Override
                        public void mouseMoved( MouseEvent e )
                        {
                            updateLatLon(e);
                        }

                        @Override
                        public void mousePressed( MouseEvent e )
                        {
                            updateLatLon(e);
                        }
                    };
                    mainPanel.addMouseListener(ml);
                    mainPanel.addMouseMotionListener(ml);

                    // just for fun
//                    mainPanel.getInputMap().put(KeyStroke.getKeyStroke("DELETE"), "removedNodes");
//                    mainPanel.getActionMap().put("removedNodes", new AbstractAction() {
//                        @Override public void actionPerformed(ActionEvent e) {
//                            int counter = 0;
//                            for (CoordTrig<Long> coord : quadTreeNodes) {
//                                int ret = quadTree.remove(coord.lat, coord.lon);
//                                if (ret < 1) {
////                                    logger.info("cannot remove " + coord + " " + ret);
////                                    ret = quadTree.remove(coord.getLatitude(), coord.getLongitude());
//                                } else
//                                    counter += ret;
//                            }
//                            logger.info("Removed " + counter + " of " + quadTreeNodes.size() + " nodes");
//                        }
//                    });
                    frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
                    frame.setSize(frameWidth + 10, frameHeight + 30);
                    frame.setVisible(true);
                }
            });
        } catch (Exception ex)
        {
            throw new RuntimeException(ex);
        }
    }

    // for moving
    int currentPosX;
    int currentPosY;

    void updateLatLon( MouseEvent e )
    {
        latLon = mg.getLat(e.getY()) + "," + mg.getLon(e.getX());
        infoPanel.repaint();
        currentPosX = e.getX();
        currentPosY = e.getY();
    }

    void repaintPaths()
    {
        pathLayer.repaint();
        mainPanel.repaint();
    }

    void repaintRoads()
    {
        // avoid threading as there should be no updated to scale or offset while painting 
        // (would to lead to artifacts)
        StopWatch sw = new StopWatch().start();
        pathLayer.repaint();
        roadsLayer.repaint();
        mainPanel.repaint();
        logger.info("roads painting took " + sw.stop().getSeconds() + " sec");
    }
}


File: web/src/main/java/com/graphhopper/http/DefaultModule.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.http;

import com.google.inject.AbstractModule;
import com.google.inject.name.Names;
import com.graphhopper.GraphHopper;
import com.graphhopper.util.CmdArgs;
import com.graphhopper.util.TranslationMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * @author Peter Karich
 */
public class DefaultModule extends AbstractModule
{
    private final Logger logger = LoggerFactory.getLogger(getClass());
    protected final CmdArgs args;
    private GraphHopper graphHopper;

    public DefaultModule( CmdArgs args )
    {
        this.args = CmdArgs.readFromConfigAndMerge(args, "config", "graphhopper.config");
    }

    public GraphHopper getGraphHopper()
    {
        if (graphHopper == null)
            throw new IllegalStateException("createGraphHopper not called");

        return graphHopper;
    }

    /**
     * @return an initialized GraphHopper instance
     */
    protected GraphHopper createGraphHopper( CmdArgs args )
    {
        GraphHopper tmp = new GraphHopper().forServer().init(args);
        tmp.importOrLoad();
        logger.info("loaded graph at:" + tmp.getGraphHopperLocation()
                + ", source:" + tmp.getOSMFile()
                + ", flagEncoders:" + tmp.getEncodingManager()
                + ", class:" + tmp.getGraph().getClass().getSimpleName());
        return tmp;
    }

    @Override
    protected void configure()
    {
        try
        {
            graphHopper = createGraphHopper(args);
            bind(GraphHopper.class).toInstance(graphHopper);
            bind(TranslationMap.class).toInstance(graphHopper.getTranslationMap());

            long timeout = args.getLong("web.timeout", 3000);
            bind(Long.class).annotatedWith(Names.named("timeout")).toInstance(timeout);
            boolean jsonpAllowed = args.getBool("web.jsonpAllowed", false);
            if (!jsonpAllowed)
                logger.info("jsonp disabled");

            bind(Boolean.class).annotatedWith(Names.named("jsonpAllowed")).toInstance(jsonpAllowed);

            bind(RouteSerializer.class).toInstance(new SimpleRouteSerializer(graphHopper.getGraph().getBounds()));
        } catch (Exception ex)
        {
            throw new IllegalStateException("Couldn't load graph", ex);
        }
    }
}


File: web/src/main/java/com/graphhopper/http/InfoServlet.java
/*
 *  Licensed to GraphHopper and Peter Karich under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for 
 *  additional information regarding copyright ownership.
 * 
 *  GraphHopper licenses this file to you under the Apache License, 
 *  Version 2.0 (the "License"); you may not use this file except in 
 *  compliance with the License. You may obtain a copy of the License at
 * 
 *       http://www.apache.org/licenses/LICENSE-2.0
 * 
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.http;

import com.graphhopper.GraphHopper;
import com.graphhopper.storage.StorableProperties;
import com.graphhopper.util.Constants;
import com.graphhopper.util.Helper;
import com.graphhopper.util.shapes.BBox;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import javax.inject.Inject;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import static javax.servlet.http.HttpServletResponse.SC_BAD_REQUEST;
import static javax.servlet.http.HttpServletResponse.SC_INTERNAL_SERVER_ERROR;

import org.json.JSONObject;

/**
 * @author Peter Karich
 */
public class InfoServlet extends GHBaseServlet
{
    @Inject
    private GraphHopper hopper;

    @Override
    public void doGet( HttpServletRequest req, HttpServletResponse res ) throws ServletException, IOException
    {
        BBox bb = hopper.getGraph().getBounds();
        List<Double> list = new ArrayList<Double>(4);
        list.add(bb.minLon);
        list.add(bb.minLat);
        list.add(bb.maxLon);
        list.add(bb.maxLat);

        JSONObject json = new JSONObject();
        json.put("bbox", list);

        String[] vehicles = hopper.getGraph().getEncodingManager().toString().split(",");
        json.put("supported_vehicles", vehicles);
        JSONObject features = new JSONObject();
        for (String v : vehicles)
        {
            JSONObject perVehicleJson = new JSONObject();
            perVehicleJson.put("elevation", hopper.hasElevation());
            features.put(v, perVehicleJson);
        }
        json.put("features", features);

        json.put("version", Constants.VERSION);
        json.put("build_date", Constants.BUILD_DATE);

        StorableProperties props = hopper.getGraph().getProperties();
        json.put("import_date", props.get("osmreader.import.date"));

        if (!Helper.isEmpty(props.get("prepare.date")))
            json.put("prepare_date", props.get("prepare.date"));

        writeJson(req, res, json);
    }
}
