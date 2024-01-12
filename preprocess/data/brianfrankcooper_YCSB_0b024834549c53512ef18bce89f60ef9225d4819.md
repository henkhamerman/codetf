Refactoring Types: ['Extract Method']
csb/Client.java
/**                                                                                                                                                                                
 * Copyright (c) 2010 Yahoo! Inc. All rights reserved.                                                                                                                             
 *                                                                                                                                                                                 
 * Licensed under the Apache License, Version 2.0 (the "License"); you                                                                                                             
 * may not use this file except in compliance with the License. You                                                                                                                
 * may obtain a copy of the License at                                                                                                                                             
 *                                                                                                                                                                                 
 * http://www.apache.org/licenses/LICENSE-2.0                                                                                                                                      
 *                                                                                                                                                                                 
 * Unless required by applicable law or agreed to in writing, software                                                                                                             
 * distributed under the License is distributed on an "AS IS" BASIS,                                                                                                               
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or                                                                                                                 
 * implied. See the License for the specific language governing                                                                                                                    
 * permissions and limitations under the License. See accompanying                                                                                                                 
 * LICENSE file.                                                                                                                                                                   
 */

package com.yahoo.ycsb;


import com.yahoo.ycsb.measurements.Measurements;
import com.yahoo.ycsb.measurements.exporter.MeasurementsExporter;
import com.yahoo.ycsb.measurements.exporter.TextMeasurementsExporter;

import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.text.DecimalFormat;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Enumeration;
import java.util.Properties;
import java.util.Vector;

//import org.apache.log4j.BasicConfigurator;

/**
 * A thread to periodically show the status of the experiment, to reassure you that progress is being made.
 * 
 * @author cooperb
 *
 */
class StatusThread extends Thread
{
	Vector<Thread> _threads;
	String _label;
	boolean _standardstatus;
	
	/**
	 * The interval for reporting status.
	 */
	public static final long sleeptime=10000;

	public StatusThread(Vector<Thread> threads, String label, boolean standardstatus)
	{
		_threads=threads;
		_label=label;
		_standardstatus=standardstatus;
	}

	/**
	 * Run and periodically report status.
	 */
	public void run()
	{
		long st=System.currentTimeMillis();

		long lasten=st;
		long lasttotalops=0;
		
		boolean alldone;
		SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss:SSS");
		
		do 
		{
			alldone=true;

			int totalops=0;

			//terminate this thread when all the worker threads are done
			for (Thread t : _threads)
			{
				if (t.getState()!=Thread.State.TERMINATED)
				{
					alldone=false;
				}

				ClientThread ct=(ClientThread)t;
				totalops+=ct.getOpsDone();
			}

			long en=System.currentTimeMillis();

			long interval=en-st;
			//double throughput=1000.0*((double)totalops)/((double)interval);

			double curthroughput=1000.0*(((double)(totalops-lasttotalops))/((double)(en-lasten)));
			
			lasttotalops=totalops;
			lasten=en;
			
			DecimalFormat d = new DecimalFormat("#.##");
			String label = _label + format.format(new Date());

			StringBuilder msg = new StringBuilder(label).append(" ").append(interval/1000).append(" sec: ");
			msg.append(totalops).append(" operations; ");

			if (totalops != 0) {
				msg.append(d.format(curthroughput)).append(" current ops/sec; ");
			}

			msg.append(Measurements.getMeasurements().getSummary());

			System.err.println(msg);

			if (_standardstatus) {
				System.out.println(msg);
			}

			try
			{
				sleep(sleeptime);
			}
			catch (InterruptedException e)
			{
				//do nothing
			}

		}
		while (!alldone);
	}
}

/**
 * A thread for executing transactions or data inserts to the database.
 * 
 * @author cooperb
 *
 */
class ClientThread extends Thread
{
	DB _db;
	boolean _dotransactions;
	Workload _workload;
	int _opcount;
	double _target;

	int _opsdone;
	int _threadid;
	int _threadcount;
	Object _workloadstate;
	Properties _props;


	/**
	 * Constructor.
	 * 
	 * @param db the DB implementation to use
	 * @param dotransactions true to do transactions, false to insert data
	 * @param workload the workload to use
	 * @param threadid the id of this thread 
	 * @param threadcount the total number of threads 
	 * @param props the properties defining the experiment
	 * @param opcount the number of operations (transactions or inserts) to do
	 * @param targetperthreadperms target number of operations per thread per ms
	 */
	public ClientThread(DB db, boolean dotransactions, Workload workload, int threadid, int threadcount, Properties props, int opcount, double targetperthreadperms)
	{
		//TODO: consider removing threadcount and threadid
		_db=db;
		_dotransactions=dotransactions;
		_workload=workload;
		_opcount=opcount;
		_opsdone=0;
		_target=targetperthreadperms;
		_threadid=threadid;
		_threadcount=threadcount;
		_props=props;
		//System.out.println("Interval = "+interval);
	}

	public int getOpsDone()
	{
		return _opsdone;
	}

	public void run()
	{
		try
		{
			_db.init();
		}
		catch (DBException e)
		{
			e.printStackTrace();
			e.printStackTrace(System.out);
			return;
		}

		try
		{
			_workloadstate=_workload.initThread(_props,_threadid,_threadcount);
		}
		catch (WorkloadException e)
		{
			e.printStackTrace();
			e.printStackTrace(System.out);
			return;
		}

		//spread the thread operations out so they don't all hit the DB at the same time
		try
		{
		   //GH issue 4 - throws exception if _target>1 because random.nextInt argument must be >0
		   //and the sleep() doesn't make sense for granularities < 1 ms anyway
		   if ( (_target>0) && (_target<=1.0) ) 
		   {
		      sleep(Utils.random().nextInt((int)(1.0/_target)));
		   }
		}
		catch (InterruptedException e)
		{
		  // do nothing.
		}
		
		try
		{
			if (_dotransactions)
			{
				long st=System.currentTimeMillis();

				while (((_opcount == 0) || (_opsdone < _opcount)) && !_workload.isStopRequested())
				{

					if (!_workload.doTransaction(_db,_workloadstate))
					{
						break;
					}

					_opsdone++;

					//throttle the operations
					if (_target>0)
					{
						//this is more accurate than other throttling approaches we have tried,
						//like sleeping for (1/target throughput)-operation latency,
						//because it smooths timing inaccuracies (from sleep() taking an int, 
						//current time in millis) over many operations
						while (System.currentTimeMillis()-st<((double)_opsdone)/_target)
						{
							try
							{
								sleep(1);
							}
							catch (InterruptedException e)
							{
							  // do nothing.
							}

						}
					}
				}
			}
			else
			{
				long st=System.currentTimeMillis();

				while (((_opcount == 0) || (_opsdone < _opcount)) && !_workload.isStopRequested())
				{

					if (!_workload.doInsert(_db,_workloadstate))
					{
						break;
					}

					_opsdone++;

					//throttle the operations
					if (_target>0)
					{
						//this is more accurate than other throttling approaches we have tried,
						//like sleeping for (1/target throughput)-operation latency,
						//because it smooths timing inaccuracies (from sleep() taking an int, 
						//current time in millis) over many operations
						while (System.currentTimeMillis()-st<((double)_opsdone)/_target)
						{
							try 
							{
								sleep(1);
							}
							catch (InterruptedException e)
							{
							  // do nothing.
							}
						}
					}
				}
			}
		}
		catch (Exception e)
		{
			e.printStackTrace();
			e.printStackTrace(System.out);
			System.exit(0);
		}

		try
		{
			_db.cleanup();
		}
		catch (DBException e)
		{
			e.printStackTrace();
			e.printStackTrace(System.out);
			return;
		}
	}
}

/**
 * Main class for executing YCSB.
 */
public class Client
{

    /**
     * The target number of operations to perform.
     */
	public static final String OPERATION_COUNT_PROPERTY="operationcount";

    /**
     * The number of records to load into the database initially.
     */
	public static final String RECORD_COUNT_PROPERTY="recordcount";

    /**
     * The workload class to be loaded.
     */
	public static final String WORKLOAD_PROPERTY="workload";
	
	/**
     * The database class to be used.
     */
    public static final String DB_PROPERTY="db";

    /**
     * The exporter class to be used. The default is
     * com.yahoo.ycsb.measurements.exporter.TextMeasurementsExporter.
     */
    public static final String EXPORTER_PROPERTY="exporter";

    /**
     * If set to the path of a file, YCSB will write all output to this file
     * instead of STDOUT.
     */
    public static final String EXPORT_FILE_PROPERTY="exportfile";

    /**
     * The number of YCSB client threads to run.
     */
    public static final String THREAD_COUNT_PROPERTY="threadcount";

	/**
	 * Indicates how many inserts to do, if less than recordcount. Useful for partitioning
	 * the load among multiple servers, if the client is the bottleneck. Additionally, workloads
	 * should support the "insertstart" property, which tells them which record to start at.
	 */
	public static final String INSERT_COUNT_PROPERTY="insertcount";
	
	/**
     * Target number of operations per second
     */
    public static final String TARGET_PROPERTY="target";

    /**
   * The maximum amount of time (in seconds) for which the benchmark will be run.
   */
  public static final String MAX_EXECUTION_TIME = "maxexecutiontime";

	public static void usageMessage()
	{
		System.out.println("Usage: java com.yahoo.ycsb.Client [options]");
		System.out.println("Options:");
		System.out.println("  -threads n: execute using n threads (default: 1) - can also be specified as the \n" +
				"              \"threadcount\" property using -p");
		System.out.println("  -target n: attempt to do n operations per second (default: unlimited) - can also\n" +
				"             be specified as the \"target\" property using -p");
		System.out.println("  -load:  run the loading phase of the workload");
		System.out.println("  -t:  run the transactions phase of the workload (default)");
		System.out.println("  -db dbname: specify the name of the DB to use (default: com.yahoo.ycsb.BasicDB) - \n" +
				"              can also be specified as the \"db\" property using -p");
		System.out.println("  -P propertyfile: load properties from the given file. Multiple files can");
		System.out.println("                   be specified, and will be processed in the order specified");
		System.out.println("  -p name=value:  specify a property to be passed to the DB and workloads;");
		System.out.println("                  multiple properties can be specified, and override any");
		System.out.println("                  values in the propertyfile");
		System.out.println("  -s:  show status during run (default: no status)");
		System.out.println("  -l label:  use label for status (e.g. to label one experiment out of a whole batch)");
		System.out.println("");
		System.out.println("Required properties:");
		System.out.println("  "+WORKLOAD_PROPERTY+": the name of the workload class to use (e.g. com.yahoo.ycsb.workloads.CoreWorkload)");
		System.out.println("");
		System.out.println("To run the transaction phase from multiple servers, start a separate client on each.");
		System.out.println("To run the load phase from multiple servers, start a separate client on each; additionally,");
		System.out.println("use the \"insertcount\" and \"insertstart\" properties to divide up the records to be inserted");
	}

	public static boolean checkRequiredProperties(Properties props)
	{
		if (props.getProperty(WORKLOAD_PROPERTY)==null)
		{
			System.out.println("Missing property: "+WORKLOAD_PROPERTY);
			return false;
		}

		return true;
	}


	/**
	 * Exports the measurements to either sysout or a file using the exporter
	 * loaded from conf.
	 * @throws IOException Either failed to write to output stream or failed to close it.
	 */
	private static void exportMeasurements(Properties props, int opcount, long runtime)
			throws IOException
	{
		MeasurementsExporter exporter = null;
		try
		{
			// if no destination file is provided the results will be written to stdout
			OutputStream out;
			String exportFile = props.getProperty(EXPORT_FILE_PROPERTY);
			if (exportFile == null)
			{
				out = System.out;
			} else
			{
				out = new FileOutputStream(exportFile);
			}

			// if no exporter is provided the default text one will be used
			String exporterStr = props.getProperty(EXPORTER_PROPERTY, "com.yahoo.ycsb.measurements.exporter.TextMeasurementsExporter");
			try
			{
				exporter = (MeasurementsExporter) Class.forName(exporterStr).getConstructor(OutputStream.class).newInstance(out);
			} catch (Exception e)
			{
				System.err.println("Could not find exporter " + exporterStr
						+ ", will use default text reporter.");
				e.printStackTrace();
				exporter = new TextMeasurementsExporter(out);
			}

			exporter.write("OVERALL", "RunTime(ms)", runtime);
			double throughput = 1000.0 * ((double) opcount) / ((double) runtime);
			exporter.write("OVERALL", "Throughput(ops/sec)", throughput);

			Measurements.getMeasurements().exportMeasurements(exporter);
		} finally
		{
			if (exporter != null)
			{
				exporter.close();
			}
		}
	}
	
	@SuppressWarnings("unchecked")
	public static void main(String[] args)
	{
		String dbname;
		Properties props=new Properties();
		Properties fileprops=new Properties();
		boolean dotransactions=true;
		int threadcount=1;
		int target=0;
		boolean status=false;
		String label="";

		//parse arguments
		int argindex=0;

		if (args.length==0)
		{
			usageMessage();
			System.exit(0);
		}

		while (args[argindex].startsWith("-"))
		{
			if (args[argindex].compareTo("-threads")==0)
			{
				argindex++;
				if (argindex>=args.length)
				{
					usageMessage();
					System.exit(0);
				}
				int tcount=Integer.parseInt(args[argindex]);
				props.setProperty(THREAD_COUNT_PROPERTY, tcount+"");
				argindex++;
			}
			else if (args[argindex].compareTo("-target")==0)
			{
				argindex++;
				if (argindex>=args.length)
				{
					usageMessage();
					System.exit(0);
				}
				int ttarget=Integer.parseInt(args[argindex]);
				props.setProperty(TARGET_PROPERTY, ttarget+"");
				argindex++;
			}
			else if (args[argindex].compareTo("-load")==0)
			{
				dotransactions=false;
				argindex++;
			}
			else if (args[argindex].compareTo("-t")==0)
			{
				dotransactions=true;
				argindex++;
			}
			else if (args[argindex].compareTo("-s")==0)
			{
				status=true;
				argindex++;
			}
			else if (args[argindex].compareTo("-db")==0)
			{
				argindex++;
				if (argindex>=args.length)
				{
					usageMessage();
					System.exit(0);
				}
				props.setProperty(DB_PROPERTY,args[argindex]);
				argindex++;
			}
			else if (args[argindex].compareTo("-l")==0)
			{
				argindex++;
				if (argindex>=args.length)
				{
					usageMessage();
					System.exit(0);
				}
				label=args[argindex];
				argindex++;
			}
			else if (args[argindex].compareTo("-P")==0)
			{
				argindex++;
				if (argindex>=args.length)
				{
					usageMessage();
					System.exit(0);
				}
				String propfile=args[argindex];
				argindex++;

				Properties myfileprops=new Properties();
				try
				{
					myfileprops.load(new FileInputStream(propfile));
				}
				catch (IOException e)
				{
					System.out.println(e.getMessage());
					System.exit(0);
				}

				//Issue #5 - remove call to stringPropertyNames to make compilable under Java 1.5
				for (Enumeration e=myfileprops.propertyNames(); e.hasMoreElements(); )
				{
				   String prop=(String)e.nextElement();
				   
				   fileprops.setProperty(prop,myfileprops.getProperty(prop));
				}

			}
			else if (args[argindex].compareTo("-p")==0)
			{
				argindex++;
				if (argindex>=args.length)
				{
					usageMessage();
					System.exit(0);
				}
				int eq=args[argindex].indexOf('=');
				if (eq<0)
				{
					usageMessage();
					System.exit(0);
				}

				String name=args[argindex].substring(0,eq);
				String value=args[argindex].substring(eq+1);
				props.put(name,value);
				//System.out.println("["+name+"]=["+value+"]");
				argindex++;
			}
			else
			{
				System.out.println("Unknown option "+args[argindex]);
				usageMessage();
				System.exit(0);
			}

			if (argindex>=args.length)
			{
				break;
			}
		}

		if (argindex!=args.length)
		{
			usageMessage();
			System.exit(0);
		}

		//set up logging
		//BasicConfigurator.configure();

		//overwrite file properties with properties from the command line

		//Issue #5 - remove call to stringPropertyNames to make compilable under Java 1.5
		for (Enumeration e=props.propertyNames(); e.hasMoreElements(); )
		{
		   String prop=(String)e.nextElement();
		   
		   fileprops.setProperty(prop,props.getProperty(prop));
		}

		props=fileprops;

		if (!checkRequiredProperties(props))
		{
			System.exit(0);
		}
		
		long maxExecutionTime = Integer.parseInt(props.getProperty(MAX_EXECUTION_TIME, "0"));

		//get number of threads, target and db
		threadcount=Integer.parseInt(props.getProperty(THREAD_COUNT_PROPERTY,"1"));
		dbname=props.getProperty(DB_PROPERTY,"com.yahoo.ycsb.BasicDB");
		target=Integer.parseInt(props.getProperty(TARGET_PROPERTY,"0"));
		
		//compute the target throughput
		double targetperthreadperms=-1;
		if (target>0)
		{
			double targetperthread=((double)target)/((double)threadcount);
			targetperthreadperms=targetperthread/1000.0;
		}	 

		System.out.println("YCSB Client 0.1");
		System.out.print("Command line:");
		for (int i=0; i<args.length; i++)
		{
			System.out.print(" "+args[i]);
		}
		System.out.println();
		System.err.println("Loading workload...");
		
		//show a warning message that creating the workload is taking a while
		//but only do so if it is taking longer than 2 seconds 
		//(showing the message right away if the setup wasn't taking very long was confusing people)
		Thread warningthread=new Thread() 
		{
			public void run()
			{
				try
				{
					sleep(2000);
				}
				catch (InterruptedException e)
				{
					return;
				}
				System.err.println(" (might take a few minutes for large data sets)");
			}
		};

		warningthread.start();
		
		//set up measurements
		Measurements.setProperties(props);
		
		//load the workload
		ClassLoader classLoader = Client.class.getClassLoader();

		Workload workload=null;

		try 
		{
			Class workloadclass = classLoader.loadClass(props.getProperty(WORKLOAD_PROPERTY));

			workload=(Workload)workloadclass.newInstance();
		}
		catch (Exception e) 
		{  
			e.printStackTrace();
			e.printStackTrace(System.out);
			System.exit(0);
		}

		try
		{
			workload.init(props);
		}
		catch (WorkloadException e)
		{
			e.printStackTrace();
			e.printStackTrace(System.out);
			System.exit(0);
		}
		
		warningthread.interrupt();

		//run the workload

		System.err.println("Starting test.");

		int opcount;
		if (dotransactions)
		{
			opcount=Integer.parseInt(props.getProperty(OPERATION_COUNT_PROPERTY,"0"));
		}
		else
		{
			if (props.containsKey(INSERT_COUNT_PROPERTY))
			{
				opcount=Integer.parseInt(props.getProperty(INSERT_COUNT_PROPERTY,"0"));
			}
			else
			{
				opcount=Integer.parseInt(props.getProperty(RECORD_COUNT_PROPERTY,"0"));
			}
		}

		Vector<Thread> threads=new Vector<Thread>();

		for (int threadid=0; threadid<threadcount; threadid++)
		{
			DB db=null;
			try
			{
				db=DBFactory.newDB(dbname,props);
			}
			catch (UnknownDBException e)
			{
				System.out.println("Unknown DB "+dbname);
				System.exit(0);
			}

			Thread t=new ClientThread(db,dotransactions,workload,threadid,threadcount,props,opcount/threadcount,targetperthreadperms);

			threads.add(t);
			//t.start();
		}

		StatusThread statusthread=null;

		if (status)
		{
			boolean standardstatus=false;
			if (props.getProperty(Measurements.MEASUREMENT_TYPE_PROPERTY,"").compareTo("timeseries")==0)
			{
				standardstatus=true;
			}	
			statusthread=new StatusThread(threads,label,standardstatus);
			statusthread.start();
		}

		long st=System.currentTimeMillis();

		for (Thread t : threads)
		{
			t.start();
		}
		
    Thread terminator = null;
    
    if (maxExecutionTime > 0) {
      terminator = new TerminatorThread(maxExecutionTime, threads, workload);
      terminator.start();
    }
    
    int opsDone = 0;

		for (Thread t : threads)
		{
			try
			{
				t.join();
				opsDone += ((ClientThread)t).getOpsDone();
			}
			catch (InterruptedException e)
			{
			}
		}

		long en=System.currentTimeMillis();
		
		if (terminator != null && !terminator.isInterrupted()) {
      terminator.interrupt();
    }

		if (status)
		{
			statusthread.interrupt();
		}

		try
		{
			workload.cleanup();
		}
		catch (WorkloadException e)
		{
			e.printStackTrace();
			e.printStackTrace(System.out);
			System.exit(0);
		}

		try
		{
			exportMeasurements(props, opsDone, en - st);
		} catch (IOException e)
		{
			System.err.println("Could not export measurements, error: " + e.getMessage());
			e.printStackTrace();
			System.exit(-1);
		}

		System.exit(0);
	}
}


File: core/src/main/java/com/yahoo/ycsb/workloads/CoreWorkload.java
/**
 * Copyright (c) 2010 Yahoo! Inc. All rights reserved. 
 * 
 * Licensed under the Apache License, Version 2.0 (the "License"); you
 * may not use this file except in compliance with the License. You
 * may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0 
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
 * implied. See the License for the specific language governing
 * permissions and limitations under the License. See accompanying
 * LICENSE file.
 */

package com.yahoo.ycsb.workloads;

import java.util.Properties;
import com.yahoo.ycsb.*;
import com.yahoo.ycsb.generator.CounterGenerator;
import com.yahoo.ycsb.generator.DiscreteGenerator;
import com.yahoo.ycsb.generator.ExponentialGenerator;
import com.yahoo.ycsb.generator.Generator;
import com.yahoo.ycsb.generator.ConstantIntegerGenerator;
import com.yahoo.ycsb.generator.HotspotIntegerGenerator;
import com.yahoo.ycsb.generator.HistogramGenerator;
import com.yahoo.ycsb.generator.IntegerGenerator;
import com.yahoo.ycsb.generator.ScrambledZipfianGenerator;
import com.yahoo.ycsb.generator.SkewedLatestGenerator;
import com.yahoo.ycsb.generator.UniformIntegerGenerator;
import com.yahoo.ycsb.generator.ZipfianGenerator;
import com.yahoo.ycsb.measurements.Measurements;

import java.io.IOException;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Vector;
import java.util.List;
import java.util.Map;
import java.util.ArrayList;

/**
 * The core benchmark scenario. Represents a set of clients doing simple CRUD operations. The relative 
 * proportion of different kinds of operations, and other properties of the workload, are controlled
 * by parameters specified at runtime.
 * 
 * Properties to control the client:
 * <UL>
 * <LI><b>fieldcount</b>: the number of fields in a record (default: 10)
 * <LI><b>fieldlength</b>: the size of each field (default: 100)
 * <LI><b>readallfields</b>: should reads read all fields (true) or just one (false) (default: true)
 * <LI><b>writeallfields</b>: should updates and read/modify/writes update all fields (true) or just one (false) (default: false)
 * <LI><b>readproportion</b>: what proportion of operations should be reads (default: 0.95)
 * <LI><b>updateproportion</b>: what proportion of operations should be updates (default: 0.05)
 * <LI><b>insertproportion</b>: what proportion of operations should be inserts (default: 0)
 * <LI><b>scanproportion</b>: what proportion of operations should be scans (default: 0)
 * <LI><b>readmodifywriteproportion</b>: what proportion of operations should be read a record, modify it, write it back (default: 0)
 * <LI><b>requestdistribution</b>: what distribution should be used to select the records to operate on - uniform, zipfian, hotspot, or latest (default: uniform)
 * <LI><b>maxscanlength</b>: for scans, what is the maximum number of records to scan (default: 1000)
 * <LI><b>scanlengthdistribution</b>: for scans, what distribution should be used to choose the number of records to scan, for each scan, between 1 and maxscanlength (default: uniform)
 * <LI><b>insertorder</b>: should records be inserted in order by key ("ordered"), or in hashed order ("hashed") (default: hashed)
 * </ul> 
 */
public class CoreWorkload extends Workload
{

	/**
	 * The name of the database table to run queries against.
	 */
	public static final String TABLENAME_PROPERTY="table";

	/**
	 * The default name of the database table to run queries against.
	 */
	public static final String TABLENAME_PROPERTY_DEFAULT="usertable";

	public static String table;


	/**
	 * The name of the property for the number of fields in a record.
	 */
	public static final String FIELD_COUNT_PROPERTY="fieldcount";
	
	/**
	 * Default number of fields in a record.
	 */
	public static final String FIELD_COUNT_PROPERTY_DEFAULT="10";

	int fieldcount;

	private List<String> fieldnames;

	/**
	 * The name of the property for the field length distribution. Options are "uniform", "zipfian" (favoring short records), "constant", and "histogram".
	 * 
	 * If "uniform", "zipfian" or "constant", the maximum field length will be that specified by the fieldlength property.  If "histogram", then the
	 * histogram will be read from the filename specified in the "fieldlengthhistogram" property.
	 */
	public static final String FIELD_LENGTH_DISTRIBUTION_PROPERTY="fieldlengthdistribution";
	/**
	 * The default field length distribution.
	 */
	public static final String FIELD_LENGTH_DISTRIBUTION_PROPERTY_DEFAULT = "constant";

	/**
	 * The name of the property for the length of a field in bytes.
	 */
	public static final String FIELD_LENGTH_PROPERTY="fieldlength";
	/**
	 * The default maximum length of a field in bytes.
	 */
	public static final String FIELD_LENGTH_PROPERTY_DEFAULT="100";

	/**
	 * The name of a property that specifies the filename containing the field length histogram (only used if fieldlengthdistribution is "histogram").
	 */
	public static final String FIELD_LENGTH_HISTOGRAM_FILE_PROPERTY = "fieldlengthhistogram";
	/**
	 * The default filename containing a field length histogram.
	 */
	public static final String FIELD_LENGTH_HISTOGRAM_FILE_PROPERTY_DEFAULT = "hist.txt";

	/**
	 * Generator object that produces field lengths.  The value of this depends on the properties that start with "FIELD_LENGTH_".
	 */
	IntegerGenerator fieldlengthgenerator;
	
	/**
	 * The name of the property for deciding whether to read one field (false) or all fields (true) of a record.
	 */
	public static final String READ_ALL_FIELDS_PROPERTY="readallfields";
	
	/**
	 * The default value for the readallfields property.
	 */
	public static final String READ_ALL_FIELDS_PROPERTY_DEFAULT="true";

	boolean readallfields;

	/**
	 * The name of the property for deciding whether to write one field (false) or all fields (true) of a record.
	 */
	public static final String WRITE_ALL_FIELDS_PROPERTY="writeallfields";
	
	/**
	 * The default value for the writeallfields property.
	 */
	public static final String WRITE_ALL_FIELDS_PROPERTY_DEFAULT="false";

	boolean writeallfields;


  /**
   * The name of the property for deciding whether to check all returned
   * data against the formation template to ensure data integrity.
   */
  public static final String DATA_INTEGRITY_PROPERTY = "dataintegrity";
  
  /**
   * The default value for the dataintegrity property.
   */
  public static final String DATA_INTEGRITY_PROPERTY_DEFAULT = "false";

  /**
   * Set to true if want to check correctness of reads. Must also
   * be set to true during loading phase to function.
   */
  private boolean dataintegrity;

  /**
   * Response values for data integrity checks.
   * Need to be multiples of 1000 to match bucket offsets of
   * measurements/OneMeasurementHistogram.java.
   */
  private final int DATA_INT_MATCH = 0;
  private final int DATA_INT_DEVIATE = 1000;
  private final int DATA_INT_UNEXPECTED_NULL = 2000;


	/**
	 * The name of the property for the proportion of transactions that are reads.
	 */
	public static final String READ_PROPORTION_PROPERTY="readproportion";
	
	/**
	 * The default proportion of transactions that are reads.	
	 */
	public static final String READ_PROPORTION_PROPERTY_DEFAULT="0.95";

	/**
	 * The name of the property for the proportion of transactions that are updates.
	 */
	public static final String UPDATE_PROPORTION_PROPERTY="updateproportion";
	
	/**
	 * The default proportion of transactions that are updates.
	 */
	public static final String UPDATE_PROPORTION_PROPERTY_DEFAULT="0.05";

	/**
	 * The name of the property for the proportion of transactions that are inserts.
	 */
	public static final String INSERT_PROPORTION_PROPERTY="insertproportion";
	
	/**
	 * The default proportion of transactions that are inserts.
	 */
	public static final String INSERT_PROPORTION_PROPERTY_DEFAULT="0.0";

	/**
	 * The name of the property for the proportion of transactions that are scans.
	 */
	public static final String SCAN_PROPORTION_PROPERTY="scanproportion";
	
	/**
	 * The default proportion of transactions that are scans.
	 */
	public static final String SCAN_PROPORTION_PROPERTY_DEFAULT="0.0";
	
	/**
	 * The name of the property for the proportion of transactions that are read-modify-write.
	 */
	public static final String READMODIFYWRITE_PROPORTION_PROPERTY="readmodifywriteproportion";
	
	/**
	 * The default proportion of transactions that are scans.
	 */
	public static final String READMODIFYWRITE_PROPORTION_PROPERTY_DEFAULT="0.0";
	
	/**
	 * The name of the property for the the distribution of requests across the keyspace. Options are "uniform", "zipfian" and "latest"
	 */
	public static final String REQUEST_DISTRIBUTION_PROPERTY="requestdistribution";
	
	/**
	 * The default distribution of requests across the keyspace
	 */
	public static final String REQUEST_DISTRIBUTION_PROPERTY_DEFAULT="uniform";

	/**
	 * The name of the property for the max scan length (number of records)
	 */
	public static final String MAX_SCAN_LENGTH_PROPERTY="maxscanlength";
	
	/**
	 * The default max scan length.
	 */
	public static final String MAX_SCAN_LENGTH_PROPERTY_DEFAULT="1000";
	
	/**
	 * The name of the property for the scan length distribution. Options are "uniform" and "zipfian" (favoring short scans)
	 */
	public static final String SCAN_LENGTH_DISTRIBUTION_PROPERTY="scanlengthdistribution";
	
	/**
	 * The default max scan length.
	 */
	public static final String SCAN_LENGTH_DISTRIBUTION_PROPERTY_DEFAULT="uniform";
	
	/**
	 * The name of the property for the order to insert records. Options are "ordered" or "hashed"
	 */
	public static final String INSERT_ORDER_PROPERTY="insertorder";
	
	/**
	 * Default insert order.
	 */
	public static final String INSERT_ORDER_PROPERTY_DEFAULT="hashed";
	
	/**
   * Percentage data items that constitute the hot set.
   */
  public static final String HOTSPOT_DATA_FRACTION = "hotspotdatafraction";
  
  /**
   * Default value of the size of the hot set.
   */
  public static final String HOTSPOT_DATA_FRACTION_DEFAULT = "0.2";
  
  /**
   * Percentage operations that access the hot set.
   */
  public static final String HOTSPOT_OPN_FRACTION = "hotspotopnfraction";
  
  /**
   * Default value of the percentage operations accessing the hot set.
   */
  public static final String HOTSPOT_OPN_FRACTION_DEFAULT = "0.8";
	
	IntegerGenerator keysequence;

	DiscreteGenerator operationchooser;

	IntegerGenerator keychooser;

	Generator fieldchooser;

	CounterGenerator transactioninsertkeysequence;
	
	IntegerGenerator scanlength;
	
	boolean orderedinserts;

	int recordcount;
	
	protected static IntegerGenerator getFieldLengthGenerator(Properties p) throws WorkloadException{
		IntegerGenerator fieldlengthgenerator;
		String fieldlengthdistribution = p.getProperty(FIELD_LENGTH_DISTRIBUTION_PROPERTY, FIELD_LENGTH_DISTRIBUTION_PROPERTY_DEFAULT);
		int fieldlength=Integer.parseInt(p.getProperty(FIELD_LENGTH_PROPERTY,FIELD_LENGTH_PROPERTY_DEFAULT));
		String fieldlengthhistogram = p.getProperty(FIELD_LENGTH_HISTOGRAM_FILE_PROPERTY, FIELD_LENGTH_HISTOGRAM_FILE_PROPERTY_DEFAULT);
		if(fieldlengthdistribution.compareTo("constant") == 0) {
			fieldlengthgenerator = new ConstantIntegerGenerator(fieldlength);
		} else if(fieldlengthdistribution.compareTo("uniform") == 0) {
			fieldlengthgenerator = new UniformIntegerGenerator(1, fieldlength);
		} else if(fieldlengthdistribution.compareTo("zipfian") == 0) {
			fieldlengthgenerator = new ZipfianGenerator(1, fieldlength);
		} else if(fieldlengthdistribution.compareTo("histogram") == 0) {
			try {
				fieldlengthgenerator = new HistogramGenerator(fieldlengthhistogram);
			} catch(IOException e) {
				throw new WorkloadException("Couldn't read field length histogram file: "+fieldlengthhistogram, e);
			}
		} else {
			throw new WorkloadException("Unknown field length distribution \""+fieldlengthdistribution+"\"");
		}
		return fieldlengthgenerator;
	}
	
	/**
	 * Initialize the scenario. 
	 * Called once, in the main client thread, before any operations are started.
	 */
	public void init(Properties p) throws WorkloadException
	{
		table = p.getProperty(TABLENAME_PROPERTY,TABLENAME_PROPERTY_DEFAULT);
		
		fieldcount=Integer.parseInt(p.getProperty(FIELD_COUNT_PROPERTY,FIELD_COUNT_PROPERTY_DEFAULT));
    fieldnames = new ArrayList<String>();
    for (int i = 0; i < fieldcount; i++) {
        fieldnames.add("field" + i);
    }
		fieldlengthgenerator = CoreWorkload.getFieldLengthGenerator(p);
		
		double readproportion=Double.parseDouble(p.getProperty(READ_PROPORTION_PROPERTY,READ_PROPORTION_PROPERTY_DEFAULT));
		double updateproportion=Double.parseDouble(p.getProperty(UPDATE_PROPORTION_PROPERTY,UPDATE_PROPORTION_PROPERTY_DEFAULT));
		double insertproportion=Double.parseDouble(p.getProperty(INSERT_PROPORTION_PROPERTY,INSERT_PROPORTION_PROPERTY_DEFAULT));
		double scanproportion=Double.parseDouble(p.getProperty(SCAN_PROPORTION_PROPERTY,SCAN_PROPORTION_PROPERTY_DEFAULT));
		double readmodifywriteproportion=Double.parseDouble(p.getProperty(READMODIFYWRITE_PROPORTION_PROPERTY,READMODIFYWRITE_PROPORTION_PROPERTY_DEFAULT));
		recordcount=Integer.parseInt(p.getProperty(Client.RECORD_COUNT_PROPERTY));
		String requestdistrib=p.getProperty(REQUEST_DISTRIBUTION_PROPERTY,REQUEST_DISTRIBUTION_PROPERTY_DEFAULT);
		int maxscanlength=Integer.parseInt(p.getProperty(MAX_SCAN_LENGTH_PROPERTY,MAX_SCAN_LENGTH_PROPERTY_DEFAULT));
		String scanlengthdistrib=p.getProperty(SCAN_LENGTH_DISTRIBUTION_PROPERTY,SCAN_LENGTH_DISTRIBUTION_PROPERTY_DEFAULT);
		
		int insertstart=Integer.parseInt(p.getProperty(INSERT_START_PROPERTY,INSERT_START_PROPERTY_DEFAULT));
		
		readallfields=Boolean.parseBoolean(p.getProperty(READ_ALL_FIELDS_PROPERTY,READ_ALL_FIELDS_PROPERTY_DEFAULT));
		writeallfields=Boolean.parseBoolean(p.getProperty(WRITE_ALL_FIELDS_PROPERTY,WRITE_ALL_FIELDS_PROPERTY_DEFAULT));
		
    dataintegrity = Boolean.parseBoolean(p.getProperty(DATA_INTEGRITY_PROPERTY, DATA_INTEGRITY_PROPERTY_DEFAULT));
    //Confirm that fieldlengthgenerator returns a constant if data
    //integrity check requested.
    if (dataintegrity && !(p.getProperty(FIELD_LENGTH_DISTRIBUTION_PROPERTY, FIELD_LENGTH_DISTRIBUTION_PROPERTY_DEFAULT)).equals("constant"))
    {
      System.err.println("Must have constant field size to check data integrity.");
      System.exit(-1);
    }

		if (p.getProperty(INSERT_ORDER_PROPERTY,INSERT_ORDER_PROPERTY_DEFAULT).compareTo("hashed")==0)
		{
			orderedinserts=false;
		}
		else if (requestdistrib.compareTo("exponential")==0)
		{
                    double percentile = Double.parseDouble(p.getProperty(ExponentialGenerator.EXPONENTIAL_PERCENTILE_PROPERTY,
                                                                         ExponentialGenerator.EXPONENTIAL_PERCENTILE_DEFAULT));
                    double frac       = Double.parseDouble(p.getProperty(ExponentialGenerator.EXPONENTIAL_FRAC_PROPERTY,
                                                                         ExponentialGenerator.EXPONENTIAL_FRAC_DEFAULT));
                    keychooser = new ExponentialGenerator(percentile, recordcount*frac);
		}
		else
		{
			orderedinserts=true;
		}

		keysequence=new CounterGenerator(insertstart);
		operationchooser=new DiscreteGenerator();
		if (readproportion>0)
		{
			operationchooser.addValue(readproportion,"READ");
		}

		if (updateproportion>0)
		{
			operationchooser.addValue(updateproportion,"UPDATE");
		}

		if (insertproportion>0)
		{
			operationchooser.addValue(insertproportion,"INSERT");
		}
		
		if (scanproportion>0)
		{
			operationchooser.addValue(scanproportion,"SCAN");
		}
		
		if (readmodifywriteproportion>0)
		{
			operationchooser.addValue(readmodifywriteproportion,"READMODIFYWRITE");
		}

		transactioninsertkeysequence=new CounterGenerator(recordcount);
		if (requestdistrib.compareTo("uniform")==0)
		{
			keychooser=new UniformIntegerGenerator(0,recordcount-1);
		}
		else if (requestdistrib.compareTo("zipfian")==0)
		{
			//it does this by generating a random "next key" in part by taking the modulus over the number of keys
			//if the number of keys changes, this would shift the modulus, and we don't want that to change which keys are popular
			//so we'll actually construct the scrambled zipfian generator with a keyspace that is larger than exists at the beginning
			//of the test. that is, we'll predict the number of inserts, and tell the scrambled zipfian generator the number of existing keys
			//plus the number of predicted keys as the total keyspace. then, if the generator picks a key that hasn't been inserted yet, will
			//just ignore it and pick another key. this way, the size of the keyspace doesn't change from the perspective of the scrambled zipfian generator
			
			int opcount=Integer.parseInt(p.getProperty(Client.OPERATION_COUNT_PROPERTY));
			int expectednewkeys=(int)(((double)opcount)*insertproportion*2.0); //2 is fudge factor
			
			keychooser=new ScrambledZipfianGenerator(recordcount+expectednewkeys);
		}
		else if (requestdistrib.compareTo("latest")==0)
		{
			keychooser=new SkewedLatestGenerator(transactioninsertkeysequence);
		}
		else if (requestdistrib.equals("hotspot")) 
		{
      double hotsetfraction = Double.parseDouble(p.getProperty(
          HOTSPOT_DATA_FRACTION, HOTSPOT_DATA_FRACTION_DEFAULT));
      double hotopnfraction = Double.parseDouble(p.getProperty(
          HOTSPOT_OPN_FRACTION, HOTSPOT_OPN_FRACTION_DEFAULT));
      keychooser = new HotspotIntegerGenerator(0, recordcount - 1, 
          hotsetfraction, hotopnfraction);
    }
		else
		{
			throw new WorkloadException("Unknown request distribution \""+requestdistrib+"\"");
		}

		fieldchooser=new UniformIntegerGenerator(0,fieldcount-1);
		
		if (scanlengthdistrib.compareTo("uniform")==0)
		{
			scanlength=new UniformIntegerGenerator(1,maxscanlength);
		}
		else if (scanlengthdistrib.compareTo("zipfian")==0)
		{
			scanlength=new ZipfianGenerator(1,maxscanlength);
		}
		else
		{
			throw new WorkloadException("Distribution \""+scanlengthdistrib+"\" not allowed for scan length");
		}
	}

	public String buildKeyName(long keynum) {
 		if (!orderedinserts)
 		{
 			keynum=Utils.hash(keynum);
 		}
		return "user"+keynum;
	}
	
  /**
   * Builds a value for a randomly chosen field.
   */
  private HashMap<String, ByteIterator> buildSingleValue(String key) {
    HashMap<String,ByteIterator> value = new HashMap<String,ByteIterator>();

    String fieldkey = fieldnames.get(Integer.parseInt(fieldchooser.nextString()));
    ByteIterator data;
    if (dataintegrity) {
      data = new StringByteIterator(buildDeterministicValue(key, fieldkey));
    } else {
      //fill with random data
      data = new RandomByteIterator(fieldlengthgenerator.nextInt());
    }
    value.put(fieldkey,data);

    return value;    
  }

  /**
   * Builds values for all fields.
   */
  private HashMap<String, ByteIterator> buildValues(String key) {        
    HashMap<String,ByteIterator> values = new HashMap<String,ByteIterator>();

    for (String fieldkey : fieldnames) {
      ByteIterator data;
      if (dataintegrity) {
        data = new StringByteIterator(buildDeterministicValue(key, fieldkey));
      } else {
        //fill with random data
        data = new RandomByteIterator(fieldlengthgenerator.nextInt());
      }
      values.put(fieldkey,data);
    }
    return values;
  }

  /**
   * Build a deterministic value given the key information.
   */
  private String buildDeterministicValue(String key, String fieldkey) {
    int size = fieldlengthgenerator.nextInt();
    StringBuilder sb = new StringBuilder(size);
    sb.append(key);
    sb.append(':');
    sb.append(fieldkey);
    while (sb.length() < size) {
      sb.append(':');
      sb.append(sb.toString().hashCode());
    }
    sb.setLength(size);

    return sb.toString();
  }

	/**
	 * Do one insert operation. Because it will be called concurrently from multiple client threads, this 
	 * function must be thread safe. However, avoid synchronized, or the threads will block waiting for each 
	 * other, and it will be difficult to reach the target throughput. Ideally, this function would have no side
	 * effects other than DB operations.
	 */
	public boolean doInsert(DB db, Object threadstate)
	{
		int keynum=keysequence.nextInt();
		String dbkey = buildKeyName(keynum);
		HashMap<String, ByteIterator> values = buildValues(dbkey);
		if (db.insert(table,dbkey,values) == 0)
			return true;
		else
			return false;
	}

	/**
	 * Do one transaction operation. Because it will be called concurrently from multiple client threads, this 
	 * function must be thread safe. However, avoid synchronized, or the threads will block waiting for each 
	 * other, and it will be difficult to reach the target throughput. Ideally, this function would have no side
	 * effects other than DB operations.
	 */
	public boolean doTransaction(DB db, Object threadstate)
	{
		String op=operationchooser.nextString();

		if (op.compareTo("READ")==0)
		{
			doTransactionRead(db);
		}
		else if (op.compareTo("UPDATE")==0)
		{
			doTransactionUpdate(db);
		}
		else if (op.compareTo("INSERT")==0)
		{
			doTransactionInsert(db);
		}
		else if (op.compareTo("SCAN")==0)
		{
			doTransactionScan(db);
		}
		else
		{
			doTransactionReadModifyWrite(db);
		}
		
		return true;
	}

  /**
   * Results are reported in the first three buckets of the histogram under
   * the label "VERIFY". 
   * Bucket 0 means the expected data was returned.
   * Bucket 1 means incorrect data was returned.
   * Bucket 2 means null data was returned when some data was expected. 
   */
  protected void verifyRow(String key, HashMap<String,ByteIterator> cells) {
    int matchType = DATA_INT_MATCH;
    if (!cells.isEmpty()) {
      for (Map.Entry<String, ByteIterator> entry : cells.entrySet()) {
        if (!entry.getValue().toString().equals(
            buildDeterministicValue(key, entry.getKey()))) {
          matchType = DATA_INT_DEVIATE;
          break;
        }
      }
    } else {
      //This assumes that null data is never valid
      matchType = DATA_INT_UNEXPECTED_NULL;
    }
    Measurements.getMeasurements().measure("VERIFY", matchType);
  }

    int nextKeynum() {
        int keynum;
        if(keychooser instanceof ExponentialGenerator) {
            do
                {
                    keynum=transactioninsertkeysequence.lastInt() - keychooser.nextInt();
                }
            while(keynum < 0);
        } else {
            do
                {
                    keynum=keychooser.nextInt();
                }
            while (keynum > transactioninsertkeysequence.lastInt());
        }
        return keynum;
    }

	public void doTransactionRead(DB db)
	{
		//choose a random key
		int keynum = nextKeynum();
		
		String keyname = buildKeyName(keynum);
		
		HashSet<String> fields=null;

		if (!readallfields)
		{
			//read a random field  
			String fieldname=fieldnames.get(Integer.parseInt(fieldchooser.nextString()));

			fields=new HashSet<String>();
			fields.add(fieldname);
		}

    HashMap<String,ByteIterator> cells =
        new HashMap<String,ByteIterator>();
		db.read(table,keyname,fields,cells);

    if (dataintegrity) {
      verifyRow(keyname, cells);
    }
	}
	
	public void doTransactionReadModifyWrite(DB db)
	{
		//choose a random key
		int keynum = nextKeynum();

		String keyname = buildKeyName(keynum);

		HashSet<String> fields=null;

		if (!readallfields)
		{
			//read a random field  
			String fieldname=fieldnames.get(Integer.parseInt(fieldchooser.nextString()));

			fields=new HashSet<String>();
			fields.add(fieldname);
		}
		
		HashMap<String,ByteIterator> values;

		if (writeallfields)
		{
		   //new data for all the fields
		   values = buildValues(keyname);
		}
		else
		{
		   //update a random field
		   values = buildSingleValue(keyname);
		}

		//do the transaction

		HashMap<String,ByteIterator> cells =
		    new HashMap<String,ByteIterator>();

		long st=System.nanoTime();

		db.read(table,keyname,fields,cells);
		
		db.update(table,keyname,values);

		long en=System.nanoTime();

    if (dataintegrity) {
      verifyRow(keyname, cells);
    }

		Measurements.getMeasurements().measure("READ-MODIFY-WRITE", (int)((en-st)/1000));
	}
	
	public void doTransactionScan(DB db)
	{
		//choose a random key
		int keynum = nextKeynum();

		String startkeyname = buildKeyName(keynum);
		
		//choose a random scan length
		int len=scanlength.nextInt();

		HashSet<String> fields=null;

		if (!readallfields)
		{
			//read a random field  
			String fieldname=fieldnames.get(Integer.parseInt(fieldchooser.nextString()));

			fields=new HashSet<String>();
			fields.add(fieldname);
		}

		db.scan(table,startkeyname,len,fields,new Vector<HashMap<String,ByteIterator>>());
	}

	public void doTransactionUpdate(DB db)
	{
		//choose a random key
		int keynum = nextKeynum();

		String keyname=buildKeyName(keynum);

		HashMap<String,ByteIterator> values;

		if (writeallfields)
		{
		   //new data for all the fields
		   values = buildValues(keyname);
		}
		else
		{
		   //update a random field
		   values = buildSingleValue(keyname);
		}

		db.update(table,keyname,values);
	}

	public void doTransactionInsert(DB db)
	{
		//choose the next key
		int keynum=transactioninsertkeysequence.nextInt();

		String dbkey = buildKeyName(keynum);

		HashMap<String, ByteIterator> values = buildValues(dbkey);
		db.insert(table,dbkey,values);
	}
}
