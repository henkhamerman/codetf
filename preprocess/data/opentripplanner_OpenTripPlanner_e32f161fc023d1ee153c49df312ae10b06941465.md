Refactoring Types: ['Rename Package']
ner/analyst/cluster/AnalystClusterRequest.java
package org.opentripplanner.analyst.cluster;

import org.opentripplanner.profile.ProfileRequest;
import org.opentripplanner.routing.core.RoutingRequest;

import java.io.Serializable;

/**
 * A request sent to an Analyst cluster worker.
 * It has two separate fields for RoutingReqeust or ProfileReqeust to facilitate binding from JSON.
 * Only one of them should be set in a given instance, with the ProfileRequest taking precedence if both are set.
 */
public class AnalystClusterRequest implements Serializable {

	/** The ID of the destinations pointset */
	public String destinationPointsetId;

	/** The Analyst Cluster user that created this request */
	public String userId;

	/** The ID of the graph against which to calculate this request */
	public String graphId;

	/** The job ID this is associated with */
	public String jobId;

	/** The id of this particular origin */
	public String id;

	/** To where should the result be POSTed */
	public String directOutputUrl;

	/**
	 * To what queue should the notification of the result be delivered?
	 */
	public String outputQueue;

	/**
	 * Where should the job be saved?
	 */
	public String outputLocation;

	/**
	 * The routing parameters to use if this is a one-to-many profile request.
	 * If profileRequest is provided, it will take precedence and routingRequest will be ignored.
	 */
	public ProfileRequest profileRequest;

	/**
	 * The routing parameters to use if this is a non-profile one-to-many request.
	 * If profileRequest is not provided, we will fall back on this routingRequest.
	 */
	public RoutingRequest routingRequest;

	/** Should times be included in the results (i.e. ResultSetWithTimes rather than ResultSet) */
	public boolean includeTimes = false;
	
	private AnalystClusterRequest(String destinationPointsetId, String graphId) {
		this.destinationPointsetId = destinationPointsetId;
		this.graphId = graphId;
	}

	/** Create a cluster request that wraps a ProfileRequest, and has no RoutingRequest. */
	public AnalystClusterRequest(String destinationPointsetId, String graphId, ProfileRequest req) {
		this(destinationPointsetId, graphId);
		routingRequest = null;
		try {
			profileRequest = req.clone();
		} catch (CloneNotSupportedException e) {
			throw new AssertionError();
		}
		profileRequest.analyst = true;
		profileRequest.toLat = profileRequest.fromLat;
		profileRequest.toLon = profileRequest.fromLon;
	}

	/** Create a cluster request that wraps a RoutingRequest, and has no ProfileRequest. */
	public AnalystClusterRequest(String destinationPointsetId, String graphId, RoutingRequest req) {
		this(destinationPointsetId, graphId);
		profileRequest = null;
		routingRequest = req.clone();
		routingRequest.batch = true;
		routingRequest.rctx = null;
	}

	/** Used for deserialization from JSON */
	public AnalystClusterRequest () { /* do nothing */ }
}


File: src/main/java/org/opentripplanner/analyst/cluster/AnalystWorker.java
package org.opentripplanner.analyst.cluster;

import com.amazonaws.regions.Region;
import com.amazonaws.regions.Regions;
import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.AmazonS3Client;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.http.HttpEntity;
import org.apache.http.HttpResponse;
import org.apache.http.client.methods.HttpDelete;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.conn.HttpHostConnectException;
import org.apache.http.impl.client.DefaultHttpClient;
import org.apache.http.params.BasicHttpParams;
import org.apache.http.params.HttpConnectionParams;
import org.apache.http.params.HttpParams;
import org.apache.http.util.EntityUtils;
import org.opentripplanner.analyst.PointSet;
import org.opentripplanner.analyst.ResultSet;
import org.opentripplanner.analyst.SampleSet;
import org.opentripplanner.api.model.AgencyAndIdSerializer;
import org.opentripplanner.profile.RepeatedRaptorProfileRouter;
import org.opentripplanner.routing.core.RoutingRequest;
import org.opentripplanner.routing.graph.Graph;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.OutputStream;
import java.io.PipedInputStream;
import java.io.PipedOutputStream;
import java.net.SocketTimeoutException;
import java.util.Map;
import java.util.Random;
import java.util.zip.GZIPOutputStream;

/**
 *
 */
public class AnalystWorker implements Runnable {

    private static final Logger LOG = LoggerFactory.getLogger(AnalystWorker.class);

    public static final int POLL_TIMEOUT = 30000;

    public static final Random random = new Random();

    ObjectMapper objectMapper;

    String s3Prefix = "analyst-dev";

    DefaultHttpClient httpClient = new DefaultHttpClient();

    // Of course this will eventually need to be shared between multiple AnalystWorker threads.
    ClusterGraphBuilder clusterGraphBuilder;

    // Of course this will eventually need to be shared between multiple AnalystWorker threads.
    PointSetDatastore pointSetDatastore;

    // Clients for communicating with Amazon web services
    AmazonS3 s3;

    String graphId = null;
    long startupTime;

    // Region awsRegion = Region.getRegion(Regions.EU_CENTRAL_1);
    Region awsRegion = Region.getRegion(Regions.US_EAST_1);

    boolean isSinglePoint = false;

    public AnalystWorker () {

        startupTime = System.currentTimeMillis() / 1000; // TODO auto-shutdown

        // When creating the S3 and SQS clients use the default credentials chain.
        // This will check environment variables and ~/.aws/credentials first, then fall back on
        // the auto-assigned IAM role if this code is running on an EC2 instance.
        // http://docs.aws.amazon.com/AWSSdkDocsJava/latest/DeveloperGuide/java-dg-roles.html
        s3 = new AmazonS3Client();
        s3.setRegion(awsRegion);

        /* The ObjectMapper (de)serializes JSON. */
        objectMapper = new ObjectMapper();
        objectMapper.configure(JsonParser.Feature.ALLOW_COMMENTS, true);
        objectMapper.configure(JsonParser.Feature.ALLOW_UNQUOTED_FIELD_NAMES, true);
        objectMapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false); // ignore JSON fields that don't match target type

        /* Tell Jackson how to (de)serialize AgencyAndIds, which appear as map keys in routing requests. */
        objectMapper.registerModule(AgencyAndIdSerializer.makeModule());

        /* These serve as lazy-loading caches for graphs and point sets. */
        clusterGraphBuilder = new ClusterGraphBuilder(s3Prefix + "-graphs");
        pointSetDatastore = new PointSetDatastore(10, null, false, s3Prefix + "-pointsets");

        /* The HTTP Client for talking to the Analyst Broker. */
        HttpParams httpParams = new BasicHttpParams();
        HttpConnectionParams.setConnectionTimeout(httpParams, POLL_TIMEOUT);
        HttpConnectionParams.setSoTimeout(httpParams, POLL_TIMEOUT);
        HttpConnectionParams.setSoKeepalive(httpParams, true);
        httpClient.setParams(httpParams);

    }

    @Override
    public void run() {
        // Loop forever, attempting to fetch some messages from a queue and process them.
        while (true) {
            LOG.info("Long-polling for work ({} second timeout).", POLL_TIMEOUT/1000.0);
            // Long-poll (wait a few seconds for messages to become available)
            // TODO internal blocking queue feeding work threads, polls whenever queue.size() < nProcessors
            Map<Integer, AnalystClusterRequest> requests = getSomeWork();
            if (requests == null) {
                LOG.info("Didn't get any work. Retrying.");
                continue;
            }
            requests.values().parallelStream().forEach(this::handleOneRequest);
            // Remove messages from queue so they won't be re-delivered to other workers.
            LOG.info("Removing requests from broker queue.");
            for (int taskId : requests.keySet()) {
                boolean success = deleteRequest(taskId, requests.get(taskId));
                LOG.info("deleted task {}: {}", taskId, success ? "SUCCESS" : "FAIL");
            }
        }
    }

    private void handleOneRequest(AnalystClusterRequest clusterRequest) {
        try {
            LOG.info("Handling message {}", clusterRequest.toString());

            // Get the graph object for the ID given in the request, fetching inputs and building as needed.
            // All requests handled together are for the same graph, and this call is synchronized so the graph will
            // only be built once.
            Graph graph = clusterGraphBuilder.getGraph(clusterRequest.graphId);
            graphId = clusterRequest.graphId; // Record graphId so we "stick" to this same graph on subsequent polls

            // This result envelope will hold the result of the profile or single-time one-to-many search.
            ResultEnvelope envelope = new ResultEnvelope();
            if (clusterRequest.profileRequest != null) {
                // TODO check graph and job ID against queue URL for coherency
                SampleSet sampleSet = null;
                if (clusterRequest.destinationPointsetId != null) {
                    // A pointset was specified, calculate travel times to the points in the pointset.
                    // Fetch the set of points we will use as destinations for this one-to-many search
                    PointSet pointSet = pointSetDatastore.get(clusterRequest.destinationPointsetId);
                    sampleSet = pointSet.getSampleSet(graph);
                }
                // Passing a null SampleSet parameter will properly return only isochrones in the RangeSet
                RepeatedRaptorProfileRouter router =
                        new RepeatedRaptorProfileRouter(graph, clusterRequest.profileRequest, sampleSet);
                router.route();
                ResultSet.RangeSet results = router.makeResults(clusterRequest.includeTimes);
                // put in constructor?
                envelope.bestCase  = results.min;
                envelope.avgCase   = results.avg;
                envelope.worstCase = results.max;
            } else {
                // No profile request, this must be a plain one to many routing request.
                RoutingRequest routingRequest = clusterRequest.routingRequest;
                // TODO finish the non-profile case
            }

            if (clusterRequest.outputQueue != null) {
                // TODO Enqueue a notification that the work is done
            }
            if (clusterRequest.outputLocation != null) {
                // Convert the result envelope and its contents to JSON and gzip it in this thread.
                // Transfer the results to Amazon S3 in another thread, piping between the two.
                try {
                    String s3key = String.join("/", clusterRequest.jobId, clusterRequest.id + ".json.gz");
                    PipedInputStream inPipe = new PipedInputStream();
                    PipedOutputStream outPipe = new PipedOutputStream(inPipe);
                    new Thread(() -> {
                        s3.putObject(clusterRequest.outputLocation, s3key, inPipe, null);
                    }).start();
                    OutputStream gzipOutputStream = new GZIPOutputStream(outPipe);
                    objectMapper.writeValue(gzipOutputStream, envelope);
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }

        } catch (Exception ex) {
            LOG.error("An error occurred while routing: " + ex.getMessage());
            ex.printStackTrace();
        }

    }

    public Map<Integer, AnalystClusterRequest> getSomeWork() {

        // Run a GET request (long-polling for work)
        String url = "http://localhost:9001";
        url += "/jobs/userA/graphA/jobA";
        HttpGet httpGet = new HttpGet(url);
        HttpResponse response = null;
        try {
            response = httpClient.execute(httpGet);
            if (response.getStatusLine().getStatusCode() != 200) {
                return null;
            }
            HttpEntity entity = response.getEntity();
            if (entity == null) {
                return null;
            }
            return objectMapper.readValue(entity.getContent(), new TypeReference<Map<Integer, AnalystClusterRequest>>(){});
        } catch (JsonProcessingException e) {
            LOG.error("JSON processing exception while getting work: {}", e.getMessage());
        } catch (SocketTimeoutException stex) {
            LOG.error("Socket timeout while waiting to receive work.");
        } catch (HttpHostConnectException ce) {
            LOG.error("Broker refused connection. Sleeping before retry.");
            try {
                Thread.currentThread().sleep(5000);
            } catch (InterruptedException e) { }
        } catch (IOException e) {
            LOG.error("IO exception while getting work.");
            e.printStackTrace();
        }
        return null;

    }

    /** DELETE the given message from the broker, indicating that it has been processed by a worker. */
    public boolean deleteRequest (int taskId, AnalystClusterRequest clusterRequest) {
        String url = "http://localhost:9001";
        url += String.format("/jobs/%s/%s/%s/%s", clusterRequest.userId, clusterRequest.graphId, clusterRequest.jobId, taskId);
        HttpDelete httpDelete = new HttpDelete(url);
        try {
            // TODO provide any parse errors etc. that occurred on the worker as the request body.
            HttpResponse response = httpClient.execute(httpDelete);
            // Signal the http client that we're done with this response, allowing connection reuse.
            EntityUtils.consumeQuietly(response.getEntity());
            return (response.getStatusLine().getStatusCode() == 200);
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }

}

File: src/main/java/org/opentripplanner/analyst/cluster/ClusterGraphService.java
package org.opentripplanner.analyst.cluster;

import com.amazonaws.AmazonServiceException;
import com.amazonaws.auth.AWSCredentials;
import com.amazonaws.auth.profile.ProfileCredentialsProvider;
import com.amazonaws.services.s3.AmazonS3Client;
import com.amazonaws.services.s3.model.S3Object;
import com.google.common.collect.Maps;
import org.apache.commons.io.FileUtils;
import org.apache.commons.io.IOUtils;
import org.opentripplanner.graph_builder.GraphBuilder;
import org.opentripplanner.routing.graph.Graph;
import org.opentripplanner.routing.impl.DefaultStreetVertexIndexFactory;
import org.opentripplanner.routing.services.GraphService;
import org.opentripplanner.routing.services.GraphSource;
import org.opentripplanner.routing.services.GraphSource.Factory;
import org.opentripplanner.standalone.CommandLineParameters;
import org.opentripplanner.standalone.Router;

import java.io.*;
import java.util.Collection;
import java.util.Enumeration;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipException;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;


public class ClusterGraphService extends GraphService { 

	static File GRAPH_DIR = new File("cache", "graphs");
	
	private String graphBucket;
	
	private Boolean workOffline = false;
	private AmazonS3Client s3;

	// don't use more than 60% of free memory to cache graphs
	private Map<String,Router> graphMap = Maps.newConcurrentMap();
	
	@Override
	public synchronized Router getRouter(String graphId) {
		
		GRAPH_DIR.mkdirs();
		
		if(!graphMap.containsKey(graphId)) {
			
			try {
				if (!bucketCached(graphId)) {
					if(!workOffline) {
						downloadGraphSourceFiles(graphId, GRAPH_DIR);
					}
				}
			} catch (IOException e) {
				e.printStackTrace();
			}
			
			CommandLineParameters params = new CommandLineParameters();
			params.build = new File(GRAPH_DIR, graphId);
			params.inMemory = true;
			GraphBuilder gbt = GraphBuilder.forDirectory(params, params.build);
			gbt.run();
			
			Graph g = gbt.getGraph();
			
			g.routerId = graphId;
			
			g.index(new DefaultStreetVertexIndexFactory());

			g.index.clusterStopsAsNeeded();
			
			Router r = new Router(graphId, g);
			
			// temporarily disable graph caching so we don't run out of RAM.
			// Long-term we will use an actual cache for this.
			//graphMap.put(graphId,r);
			
			return r;
					
		}
		else {
			return graphMap.get(graphId);
		}
	}

	public ClusterGraphService(String s3CredentialsFilename, Boolean workOffline, String bucket) {
		
		if(!workOffline) {
			if (s3CredentialsFilename != null) {
				AWSCredentials creds = new ProfileCredentialsProvider(s3CredentialsFilename, "default").getCredentials();
				s3 = new AmazonS3Client(creds);
			}
			else {
				// This will first check for credentials in environment variables or ~/.aws/credentials
				// then fall back on S3 credentials propagated to EC2 instances via IAM roles.
				s3 = new AmazonS3Client();
			}
			
			this.graphBucket = bucket;
		}
		
		this.workOffline = workOffline;
	}
	
	// adds either a zip file or graph directory to S3, or local cache for offline use
	public void addGraphFile(File graphFile) throws IOException {
		
		String graphId = graphFile.getName();
		
		if(graphId.endsWith(".zip"))
			graphId = graphId.substring(0, graphId.length() - 4);
		
		File graphDir = new File(GRAPH_DIR, graphId);
		
		if (graphDir.exists()) {
			if (graphDir.list().length == 0) {
				graphDir.delete();
			}
			else {
				return;
			}
		}
		
		// if we're here the directory has either been deleted or never existed
		graphDir.mkdirs();
		
		File graphDataZip = new File(GRAPH_DIR, graphId + ".zip");
				
		// if directory zip contents  store as zip
		// either way ensure there is an extracted copy in the local cache
		if(graphFile.isDirectory()) {
			FileUtils.copyDirectory(graphFile, graphDir);
			
			zipGraphDir(graphDir, graphDataZip);
		}
		else if(graphFile.getName().endsWith(".zip")) {
			FileUtils.copyFile(graphFile, graphDataZip);
			unpackGraphZip(graphDataZip, graphDir, false);
		}
		else {
			graphDataZip = null;
		}
			
		if(!workOffline && graphDataZip != null) {
			// only upload if it's not there already
			try {
				s3.getObject(graphBucket, graphId + ".zip");
			} catch (AmazonServiceException e) {
				s3.putObject(graphBucket, graphId+".zip", graphDataZip);
			}
		}
		
		graphDataZip.delete();
		
	}
	
	public synchronized File getZippedGraph(String graphId) throws IOException {
		
		File graphDataDir = new File(GRAPH_DIR, graphId);
		
		File graphZipFile = new File(GRAPH_DIR, graphId + ".zip");
		
		if(!graphDataDir.exists() && graphDataDir.isDirectory()) {
			
			FileOutputStream fileOutputStream = new FileOutputStream(graphZipFile);
			ZipOutputStream zipOutputStream = new ZipOutputStream(fileOutputStream);
			
			byte[] buffer = new byte[1024];
			
			for(File f : graphDataDir.listFiles()) {
				ZipEntry zipEntry = new ZipEntry(f.getName());
				zipOutputStream.putNextEntry(zipEntry);
	    		FileInputStream fileInput = new FileInputStream(f);

	    		int len;
	    		while ((len = fileInput.read(buffer)) > 0) {
	    			zipOutputStream.write(buffer, 0, len);
	    		}
	 
	    		fileInput.close();
	    		zipOutputStream.closeEntry();
			}
			
			zipOutputStream.close();
			
			return graphZipFile;
					
		}
		
		return null;
		
	}
	
	private static boolean bucketCached(String graphId) throws IOException {
		File graphData = new File(GRAPH_DIR, graphId);
		
		// check if cached but only as zip
		if(!graphData.exists()) {
			File graphDataZip = new File(GRAPH_DIR, graphId + ".zip");
			
			if(graphDataZip.exists()) {
				zipGraphDir(graphData, graphDataZip);
			}
		}
		
		
		return graphData.exists() && graphData.isDirectory();
	}

	private void downloadGraphSourceFiles(String graphId, File dir) throws IOException {

		File graphCacheDir = dir;
		if (!graphCacheDir.exists())
			graphCacheDir.mkdirs();

		File graphZipFile = new File(graphCacheDir, graphId + ".zip");

		File extractedGraphDir = new File(graphCacheDir, graphId);

		if (extractedGraphDir.exists()) {
			FileUtils.deleteDirectory(extractedGraphDir);
		}

		extractedGraphDir.mkdirs();

		S3Object graphZip = s3.getObject(graphBucket, graphId+".zip");

		InputStream zipFileIn = graphZip.getObjectContent();

		OutputStream zipFileOut = new FileOutputStream(graphZipFile);

		IOUtils.copy(zipFileIn, zipFileOut);
		IOUtils.closeQuietly(zipFileIn);
		IOUtils.closeQuietly(zipFileOut);

		unpackGraphZip(graphZipFile, extractedGraphDir);
	}

	private static void unpackGraphZip(File graphZipFile, File extractedGraphDir) throws ZipException, IOException {
		// delete by default
		unpackGraphZip(graphZipFile, extractedGraphDir, true);
	}
	
	private static void unpackGraphZip(File graphZipFile, File extractedGraphDir, boolean delete) throws ZipException, IOException {
		
		ZipFile zipFile = new ZipFile(graphZipFile);
		
		Enumeration<? extends ZipEntry> entries = zipFile.entries();

		while (entries.hasMoreElements()) {

			ZipEntry entry = entries.nextElement();
			File entryDestination = new File(extractedGraphDir, entry.getName());

			entryDestination.getParentFile().mkdirs();

			if (entry.isDirectory())
				entryDestination.mkdirs();
			else {
				InputStream entryFileIn = zipFile.getInputStream(entry);
				OutputStream entryFileOut = new FileOutputStream(entryDestination);
				IOUtils.copy(entryFileIn, entryFileOut);
				IOUtils.closeQuietly(entryFileIn);
				IOUtils.closeQuietly(entryFileOut);
			}
		}

		zipFile.close();

		if (delete) {
			graphZipFile.delete();
		}
	}
	
	private static void zipGraphDir(File graphDirectory, File zipGraphFile) throws IOException {
		
		FileOutputStream fileOutputStream = new FileOutputStream(zipGraphFile);
		ZipOutputStream zipOutputStream = new ZipOutputStream(fileOutputStream);
		
		byte[] buffer = new byte[1024];
		
		for(File f : graphDirectory.listFiles()) {
			if (f.isDirectory())
				continue;
			
			ZipEntry zipEntry = new ZipEntry(f.getName());
			zipOutputStream.putNextEntry(zipEntry);
    		FileInputStream fileInput = new FileInputStream(f);

    		int len;
    		while ((len = fileInput.read(buffer)) > 0) {
    			zipOutputStream.write(buffer, 0, len);
    		}
 
    		fileInput.close();
    		zipOutputStream.closeEntry();
		}
		
		zipOutputStream.close();
	}
	

	@Override
	public int evictAll() {
		graphMap.clear();
		return 0;
	}

	@Override
	public Collection<String> getRouterIds() {
		return graphMap.keySet();
	}

	@Override
	public Factory getGraphSourceFactory() {
		return null;
	}

	@Override
	public boolean registerGraph(String arg0, GraphSource arg1) {
		return false;
	}

	@Override
	public void setDefaultRouterId(String arg0) {	
	}
}


File: src/main/java/org/opentripplanner/analyst/qbroker/LongPollConnection.java
package org.opentripplanner.analyst.qbroker;

import org.glassfish.grizzly.http.server.Request;
import org.glassfish.grizzly.http.server.Response;

/**
 * Represents a dormant connection waiting for
 */
public class LongPollConnection {

    Task affinity;
    Request request;
    Response response;

    public LongPollConnection(Request request, Response response) {
        this.request = request;
        this.response = response;
    }


}


File: src/main/java/org/opentripplanner/analyst/qbroker/Task.java
package org.opentripplanner.analyst.qbroker;

/**
 *
 */
public class Task {

    public int taskId;
    public String payload; // Requests are stored as JSON text because we don't have the model objects from OTP.
    public long invisibleUntil; // This task has been delivered or hidden, and should not be re-delivered until this time.

}
