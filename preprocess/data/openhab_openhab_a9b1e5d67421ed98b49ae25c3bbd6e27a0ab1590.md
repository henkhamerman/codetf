Refactoring Types: ['Extract Method']
nding.insteonplm/src/main/java/org/openhab/binding/insteonplm/InsteonPLMActiveBinding.java
/**
 * Copyright (c) 2010-2015, openHAB.org and others.
 *
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 */
package org.openhab.binding.insteonplm;


import java.util.Collection;
import java.util.Dictionary;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Map;
import java.util.Map.Entry;
import java.util.concurrent.ConcurrentHashMap;

import org.openhab.binding.insteonplm.internal.device.DeviceFeature;
import org.openhab.binding.insteonplm.internal.device.DeviceFeatureListener;
import org.openhab.binding.insteonplm.internal.device.DeviceType;
import org.openhab.binding.insteonplm.internal.device.DeviceTypeLoader;
import org.openhab.binding.insteonplm.internal.device.InsteonAddress;
import org.openhab.binding.insteonplm.internal.device.InsteonDevice;
import org.openhab.binding.insteonplm.internal.device.InsteonDevice.DeviceStatus;
import org.openhab.binding.insteonplm.internal.device.RequestQueueManager;
import org.openhab.binding.insteonplm.internal.driver.Driver;
import org.openhab.binding.insteonplm.internal.driver.DriverListener;
import org.openhab.binding.insteonplm.internal.driver.ModemDBEntry;
import org.openhab.binding.insteonplm.internal.driver.Poller;
import org.openhab.binding.insteonplm.internal.message.FieldException;
import org.openhab.binding.insteonplm.internal.message.Msg;
import org.openhab.binding.insteonplm.internal.message.MsgListener;
import org.openhab.core.binding.AbstractActiveBinding;
import org.openhab.core.binding.BindingProvider;
import org.openhab.core.types.Command;
import org.osgi.service.cm.ConfigurationException;
import org.osgi.service.cm.ManagedService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


/**
 * This class represents the actual implementation of the binding, and controls the high level flow
 * of messages to and from the InsteonModem.
 * 
 * Writing this binding has been an odyssey through the quirks of the Insteon protocol
 * and Insteon devices. A substantial redesign was necessary at some point along the way.
 * Here are some of the hard learned lessons that should be considered by anyone who wants
 * to re-architect the binding:
 * 
 * 1) The entries of the link database of the modem are not reliable. The category/subcategory entries in
 *    particular have junk data. Forget about using the modem database to generate a list of devices.
 *    The database should only be used to verify that a device has been linked.
 *    
 * 2) Querying devices for their product information does not work either. First of all, battery operated devices
 *    (and there are a lot of those) have their radio switched off, and may generally not respond to product
 *    queries. Even main stream hardwired devices sold presently (like the 2477s switch and the 2477d dimmer)
 *    don't even have a product ID. Although supposedly part of the Insteon protocol, we have yet to
 *    encounter a device that would cough up a product id when queried, even among very recent devices. They
 *    simply return zeros as product id. Lesson: forget about querying devices to generate a device list.
 *    
 * 3) Polling is a thorny issue: too much traffic on the network, and messages will be dropped left and right,
 *    and not just the poll related ones, but others as well. In particular sending back-to-back messages
 *    seemed to result in the second message simply never getting sent, without flow control back pressure
 *    (NACK) from the modem. For now the work-around is to space out the messages upon sending, and
 *    in general poll as infrequently as acceptable.
 * 
 * 4) Instantiating and tracking devices when reported by the modem (either from the database, or when
 *    messages are received) leads to complicated state management because there is no guarantee at what
 *    point (if at all) the binding configuration will be available. It gets even more difficult when
 *    items are created, destroyed, and modified while the binding runs.
 *    
 * For the above reasons, devices are only instantiated when they are referenced by binding information.
 * As nice as it would be to discover devices and their properties dynamically, we have abandoned that
 * path because it had led to a complicated and fragile system which due to the technical limitations
 * above was inherently squirrely.
 *  
 * 
 * @author Bernd Pfrommer
 * @author Daniel Pfrommer
 * @since 1.5.0
 */

public class InsteonPLMActiveBinding
	extends AbstractActiveBinding<InsteonPLMBindingProvider>
	implements ManagedService {
	private static final Logger logger = LoggerFactory.getLogger(InsteonPLMActiveBinding.class);

	private Driver					m_driver			= null;
	private ConcurrentHashMap<InsteonAddress, InsteonDevice>  m_devices = null; // list of all configured devices
	private HashMap<String, String> m_config			= new HashMap<String, String>();
	private PortListener			m_portListener 		= new PortListener();
	private long					m_devicePollInterval 	= 300000L;
	private long					m_deadDeviceTimeout 	= -1L;
	private long					m_refreshInterval		= 600000L;
	private int						m_messagesReceived		= 0;
	private boolean					m_isActive		  		= false; // state of binding
	private boolean					m_hasInitialItemConfig	= false;
	private int						m_x10HouseUnit			= -1;

	/**
	 * Constructor
	 */
	public InsteonPLMActiveBinding() {
		m_driver	= new Driver();
		m_devices 	= new ConcurrentHashMap<InsteonAddress, InsteonDevice>();
	}

	/**
	 * Inherited from AbstractBinding. This method is invoked by the framework whenever
	 * a command is coming from openhab, i.e. a switch is flipped via the GUI or other
	 * controls. The binding translates this openhab command into a message to the modem.
	 * {@inheritDoc}
	 */

	@Override
	public void internalReceiveCommand(String itemName, Command command) {
		logger.info("Item: {} got command {}", itemName, command);

		if(!(isProperlyConfigured() && m_isActive)) {
			logger.debug("not ready to handle commands yet, returning.");
			return;
		}
		boolean commandHandled = false;
		for (InsteonPLMBindingProvider provider : providers) {
			if (provider.providesBindingFor(itemName)) {
				commandHandled = true;
				InsteonPLMBindingConfig c = provider.getInsteonPLMBindingConfig(itemName);
				if (c == null) {
					logger.warn("could not find config for item {}", itemName);
				} else {
					sendCommand(c, command);
				}
			}
		}
		
		if (!commandHandled)
			logger.warn("No converter found for item = {}, command = {}, ignoring.",
						itemName, command.toString());
	}

	/**
	 * Inherited from AbstractBinding.
	 * Activates the binding. There is nothing we can do at this point
	 * if we don't have the configuration information, which usually comes
	 * in later, when updated() is called.
	 * {@inheritDoc}
	 */
	@Override
	public void activate() {
		logger.debug("activating binding");
		if (isProperlyConfigured() && !m_isActive) {
			initialize();
		}
		m_isActive = true;
	}
	
	/**
	 * Inherited from AbstractBinding. Deactivates the binding.
	 * The Controller is stopped and the serial interface is closed as well.
	 * {@inheritDoc}
	 */
	@Override
	public void deactivate() {
		logger.debug("deactivating binding!");
		shutdown();
		m_isActive = false;
	}


	/**
	 * Inherited from AbstractActiveBinding.
	 * {@inheritDoc}
	 */
	@Override
	protected String getName() {
		return "InsteonPLM";
	}
	
	/**
	 * Inherited from AbstractActiveBinding.
	 * Periodically called by the framework to execute a refresh of the binding.
	 * {@inheritDoc}
	 */
	@Override
	protected void execute() {
		logDeviceStatistics();
	}

	/**
	 * Inherited from AbstractActiveBinding.
	 * Returns the refresh interval (time between calls to execute()) in milliseconds.
	 * {@inheritDoc}
	 */
	@Override
	protected long getRefreshInterval() {
		return m_refreshInterval;
	}
	
	/**
	 * Inherited from AbstractActiveBinding.
	 * This method is called by the framework whenever there are changes to
	 * a binding configuration.
	 * @param provider the binding provider where the binding has changed
	 * @param itemName the item name for which the binding has changed
	 */
	@Override
	public void bindingChanged(BindingProvider provider, String itemName) {
		super.bindingChanged(provider, itemName);
		m_hasInitialItemConfig = true; // hack around openHAB bug
		InsteonPLMBindingConfig c =
					((InsteonPLMBindingProvider)provider).getInsteonPLMBindingConfig(itemName);
		logger.debug("item {} binding changed: {}", String.format("%-30s", itemName), c);
		if (c == null) {
			// Item has been removed. This condition is also found when *any*
			// change to the items file is made: the items are first removed (c == null),
			// and then added anew.
			removeFeatureListener(itemName);
		} else {
			InsteonDevice dev = getDevice(c.getAddress());
			if (dev == null) {
				dev = makeNewDevice(c);
			}
			addFeatureListener(dev, itemName, c);
		}
	}
	/**
	 * Inherited from the ManagedService interface. This method is called whenever the configuration
	 * is updated. This could be signaling that e.g. the port has changed etc.
	 * {@inheritDoc}
	 */
	@Override
	public void updated(Dictionary<String, ?> config) throws ConfigurationException {
		HashMap<String, String> newConfig = new HashMap<String, String>();
		if (config == null) {
			logger.debug("seems like our configuration has been erased, will reset everything!");
		} else {
			// turn config into new HashMap
			for (Enumeration<String> e = config.keys(); e.hasMoreElements();) {
				String key   = e.nextElement();
				String value = config.get(key).toString();
				newConfig.put(key, value);
			}
		}
		
		if (newConfig.entrySet().equals(m_config.entrySet())) {
			logger.debug("config has not changed, done.");
			return;
		}
		m_config = newConfig;

		// configuration has changed
		if (m_isActive) {
			if (isProperlyConfigured()) {
				logger.debug("global binding config has changed, resetting.");
				shutdown();
			} else {
				logger.debug("global binding config has arrived.");
			}
		}
		long deadDeviceCount = 10;
		if (m_config.containsKey("refresh")) {
			m_refreshInterval = Integer.parseInt(m_config.get("refresh"));
			logger.info("refresh interval set to {}s", m_refreshInterval / 1000);
		}
		if (m_config.containsKey("device_dead_count")) {
			deadDeviceCount = s_parseLong(m_config.get("device_dead_count"), 2L, 100000L);
			logger.info("device_dead_count set to {} per config file", deadDeviceCount);
		}
		if (m_config.containsKey("poll_interval")) {
			m_devicePollInterval = s_parseLong(m_config.get("poll_interval"), 5000L, 3600000L);
			logger.info("poll interval set to {} per config file", m_devicePollInterval);
		}
		if (m_config.containsKey("more_devices")) {
			String fileName = m_config.get("more_devices");
			try {
				DeviceTypeLoader.s_instance().loadDeviceTypesXML(fileName);
				logger.info("read additional device definitions from {}", fileName);
			} catch (Exception e) {
				logger.error("error reading additional devices from {}", fileName, e);
			}
		}
		if (m_config.containsKey("more_features")) {
			String fileName = m_config.get("more_features");
			logger.info("reading additional feature templates from {}", fileName);
			DeviceFeature.s_readFeatureTemplates(fileName);
		}
 		
		m_deadDeviceTimeout = m_devicePollInterval * deadDeviceCount;
		logger.info("dead device timeout set to {}s", m_deadDeviceTimeout / 1000);
		logger.debug("configuration update complete!");
		setProperlyConfigured(true);
		if (m_isActive) {
			initialize();
		}
		if (!m_hasInitialItemConfig) triggerBindingChangedCalls();
		return;
	}
	/**
	 * Method to find a device by address
	 * @param aAddr the insteon address to search for
	 * @return reference to the device, or null if not found
	 */
	public InsteonDevice getDevice(InsteonAddress aAddr) {
		InsteonDevice dev = (aAddr == null) ? null : m_devices.get(aAddr);
		return (dev);
	}
	

	/**
	 * HACK around openHAB synchronization issues that don't show
	 * up in the IDE environment, but when running as packaged bundle:
	 * The InsteonPLMGenericBindingProvider is instantiated *before*
	 * the InsteonPLMActiveBinding. This means: the binding provider parses
	 * all the configuration strings, but bindingChanged() in the actual
	 * binding is not called, because the binding is not even instantiated
	 * at that point. Later when the binding is active, it has to artificially
	 * trigger these calls.
	 */
	private void triggerBindingChangedCalls() {
		for (InsteonPLMBindingProvider provider : providers) {
			Collection<String> items = provider.getItemNames();
			for (Iterator<String> item = items.iterator(); item.hasNext();) {
				String itemName = item.next();
				bindingChanged(provider, itemName);
			}
        }
	}
	
	/**
	 * Initialize the binding: initialize the driver etc
	 */
	private void initialize() {
		logger.debug("initializing...");
		
		HashSet<String> ports = new HashSet<String>();

		//Initialize ports
		for (Map.Entry<String, String> e : m_config.entrySet()) {
			String name = e.getKey();
			String port  = e.getValue();
			if (ports.contains(port)) {
				logger.warn("port {} {} already in use, check config!", name, port);
				continue;
			}
			logger.info("config: {} -> {}", name, port);
			if (name.startsWith("port_")) {
				m_driver.addPort(name,  port);
				m_driver.addMsgListener(m_portListener, port);
			}
		}
		logger.debug("setting driver listener");
		m_driver.setDriverListener(m_portListener);
		logger.debug("starting {} ports", m_driver.getNumberOfPorts());
		m_driver.startAllPorts();
		logger.debug("ports started");
		switch (m_driver.getNumberOfPorts()) {
		case 0:
			logger.error("initialization complete, but found no ports!");
			break;
		case 1:
			logger.debug("initialization complete, found 1 port!");
			break;
		default:
			logger.warn("initialization complete, found {} ports.",
					m_driver.getNumberOfPorts());
			break;
		}
	}
	
	/**
	 * Clean up all state.
	 */
	private void shutdown() {
		logger.debug("shutting down binding");
		m_driver.stopAllPorts();
		m_devices.clear();
		RequestQueueManager.s_destroyInstance();
		Poller.s_instance().stop();
	}
	
	/**
	 * Send command to insteon device
	 * @param c item binding configuration
	 * @param command The command to be sent
	 */
	private void sendCommand(InsteonPLMBindingConfig c, Command command) {
		InsteonDevice dev = getDevice(c.getAddress());
		if (dev == null) {
			logger.warn("no device found with insteon address {}", c.getAddress());
			return;
		}
		dev.processCommand(m_driver, c, command);
	}

	/**
	 * Finds the device that a particular item was bound to, and removes the
	 * item as a listener
	 * @param aItem The item (FeatureListener) to remove from all devices
	 */
	private void removeFeatureListener(String aItem) {
		for (Iterator<Entry<InsteonAddress, InsteonDevice>> it = m_devices.entrySet().iterator();
				it.hasNext(); ) {
			InsteonDevice dev = it.next().getValue();
			boolean removedListener = dev.removeFeatureListener(aItem);
			if (removedListener) {
				logger.trace("removed feature listener {} from dev {}", aItem, dev);
			}
			if (!dev.hasAnyListeners()) {
				Poller.s_instance().stopPolling(dev);
				it.remove();
				logger.trace("removing unreferenced {}", dev);
				if (m_devices.isEmpty()) {
					logger.debug("all devices removed!", dev);
				}
			}
		}
	}
	
	/**
	 * Creates a new insteon device for a given product key
	 * @param aConfig The binding configuration parameters, needed to make device.
	 * @return Reference to the new device that has been created
	 */
	private InsteonDevice makeNewDevice(InsteonPLMBindingConfig aConfig) {
		String prodKey = aConfig.getProductKey();
		DeviceType dt = DeviceTypeLoader.s_instance().getDeviceType(prodKey);
		if (dt == null) {
			logger.error("unknown product key: {} for config: {}." +
					" Add definition to xml file and try again", prodKey, aConfig);
			return null;
		}
		InsteonDevice dev =	InsteonDevice.s_makeDevice(dt);
		dev.setAddress(aConfig.getAddress());
		dev.setDriver(m_driver);
		dev.addPort(m_driver.getDefaultPort());
		if (!dev.hasValidPollingInterval()) {
			dev.setPollInterval(m_devicePollInterval);
		}
		if (m_driver.isModemDBComplete() && dev.getStatus() != DeviceStatus.POLLING) {
			int ndev = checkIfInModemDatabase(dev);
			if (dev.hasModemDBEntry()) {
				dev.setStatus(DeviceStatus.POLLING);
				Poller.s_instance().startPolling(dev, ndev);
			}
		}
		m_devices.put(aConfig.getAddress(), dev);
		return (dev);
	}
	
	/**
	 * Checks if a device is in the modem link database, and, if the database
	 * is complete, logs a warning if the device is not present
	 * @param dev The device to search for in the modem database
	 * @return number of devices in modem database
	 */
	private int checkIfInModemDatabase(InsteonDevice dev) {
		InsteonAddress addr = dev.getAddress();
		HashMap<InsteonAddress, ModemDBEntry> dbes = m_driver.lockModemDBEntries();
		if (dbes.containsKey(addr)) {
			if (!dev.hasModemDBEntry()) {
				logger.info("device {} found in the modem database!", addr);
				dev.setHasModemDBEntry(true);
			}
		} else {
			if (m_driver.isModemDBComplete() && !addr.isX10()) {
				logger.warn("device {} not found in the modem database. Did you forget to link?", addr);
			}
		}
		int ndev = dbes.size();
		m_driver.unlockModemDBEntries();
		return ndev;
	}
	/**
	 * Adds a feature listener (i.e. item to a feature of a device)
	 * @param aDev The device to add the feature listener
	 * @param aItemName The name of the item (needed for logging and later lookups)
	 * @param aConfig The binding configuration for the item
	 */
	private void addFeatureListener(InsteonDevice aDev, String aItemName,
				InsteonPLMBindingConfig aConfig) {
		if (aDev == null) {
			return;
		}
		DeviceFeature f = aDev.getFeature(aConfig.getFeature());
		if (f == null) {
			logger.error("item {} references unknown feature: {}, item disabled!", aItemName, aConfig.getFeature());
			return;
		}
		DeviceFeatureListener fl = new DeviceFeatureListener(this, aItemName, eventPublisher);
		fl.setParameters(aConfig.getParameters());
		f.addListener(fl);	
	}

	/**
	 * Handles messages that come in from the ports.
	 * Will only process one message at a time.
	 */
	private class PortListener implements MsgListener, DriverListener {
		/**
		 * {@inheritDoc}
		 */
		@Override
		public void msg(Msg msg, String fromPort) {
			if (msg.isEcho() || msg.isPureNack()) return;
			m_messagesReceived++;
			logger.debug("got msg: {}", msg);
			if (msg.isX10()) {
				handleX10Message(msg, fromPort);
			} else {
				handleInsteonMessage(msg, fromPort);
			}
			
		}
		/**
		 * {@inheritDoc}
		 */
		@Override
		public void driverCompletelyInitialized() {
			HashMap<InsteonAddress, ModemDBEntry> dbes = m_driver.lockModemDBEntries();
			logger.info("modem database has {} entries!", dbes.size());
			if (dbes.isEmpty()) {
				logger.warn("the modem link database is empty!");
			}
			for (InsteonAddress k : dbes.keySet()) {
				logger.debug("modem db entry: {}", k);
			}
			for (InsteonDevice dev : m_devices.values()) {
				InsteonAddress a = dev.getAddress();
				if (!dbes.containsKey(a)) {
					if (!a.isX10())
						logger.warn("device {} not found in the modem database. Did you forget to link?", a);
				} else {
					if (!dev.hasModemDBEntry()) {
						logger.info("device {}     found in the modem database!", a);
						dev.setHasModemDBEntry(true);
					}
					if (dev.getStatus() != DeviceStatus.POLLING) {
						Poller.s_instance().startPolling(dev, dbes.size());
					}
				}
			}
			m_driver.unlockModemDBEntries();
		}
		private void handleInsteonMessage(Msg msg, String fromPort) {
			InsteonAddress toAddr = msg.getAddr("toAddress");
			if (!msg.isBroadcast() && !m_driver.isMsgForUs(toAddr)) {
				// not for one of our modems, do not process
				return;
			}
			InsteonAddress fromAddr = msg.getAddr("fromAddress");
			if (fromAddr == null) {
				logger.debug("invalid fromAddress, ignoring msg {}", msg);
				return;
			}
			handleMessage(fromPort, fromAddr, msg);
		}

		private void handleX10Message(Msg msg, String fromPort) {
			try {
				int x10Flag	= msg.getByte("X10Flag") & 0xff;
				int rawX10	= msg.getByte("rawX10") & 0xff;
				if (x10Flag == 0x80) { // actual command
					if (m_x10HouseUnit != -1) {
						InsteonAddress fromAddr = new InsteonAddress((byte)m_x10HouseUnit);
						handleMessage(fromPort, fromAddr, msg);
					}
				} else if (x10Flag == 0) {
					// what unit the next cmd will apply to
					m_x10HouseUnit = rawX10 & 0xFF; 
				}
			} catch (FieldException e) {
				logger.error("got bad X10 message: {}", msg, e);
				return;
			}
		}
		private void handleMessage(String fromPort, InsteonAddress fromAddr, Msg msg) {
			InsteonDevice  dev = getDevice(fromAddr);
			if (dev == null) {
				logger.debug("dropping message from unknown device with address {}", fromAddr);
			} else {
				dev.handleMessage(fromPort, msg);
			}
		}
	}
	
	private void logDeviceStatistics() {
		logger.info(String.format("devices: %3d configured, %3d polling, msgs received: %5d",
				m_devices.size(), Poller.s_instance().getSizeOfQueue(), m_messagesReceived));
		m_messagesReceived = 0;
		for (InsteonDevice dev : m_devices.values()) {
			if (dev.isModem()) continue;
			if (m_deadDeviceTimeout > 0 &&
					dev.getPollOverDueTime() > m_deadDeviceTimeout) {
				logger.info("device {} has not responded to polls for {} sec", dev.toString(),
						dev.getPollOverDueTime() / 3600);
			}
		}
	}

	private static long s_parseLong(String pi, long min, long max) {
		long t = Long.parseLong(pi);
		t = Math.max(t, min);
		t = Math.min(t, max);
		return t;
	}
}

File: bundles/binding/org.openhab.binding.insteonplm/src/main/java/org/openhab/binding/insteonplm/internal/device/MessageHandler.java
/**
 * Copyright (c) 2010-2015, openHAB.org and others.
 *
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 */
package org.openhab.binding.insteonplm.internal.device;

import java.io.IOException;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.GregorianCalendar;
import java.util.HashMap;

import org.openhab.binding.insteonplm.internal.device.DeviceFeatureListener.StateChangeType;
import org.openhab.binding.insteonplm.internal.device.GroupMessageStateMachine.GroupMessage;
import org.openhab.binding.insteonplm.internal.message.FieldException;
import org.openhab.binding.insteonplm.internal.message.Msg;
import org.openhab.binding.insteonplm.internal.message.MsgType;
import org.openhab.binding.insteonplm.internal.utils.Utils;
import org.openhab.core.library.types.DateTimeType;
import org.openhab.core.library.types.DecimalType;
import org.openhab.core.library.types.OnOffType;
import org.openhab.core.library.types.OpenClosedType;
import org.openhab.core.library.types.PercentType;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * A message handler processes incoming Insteon messages and reacts by publishing
 * corresponding messages on the openhab bus, updating device state etc.
 * @author Daniel Pfrommer
 * @author Bernd Pfrommer
 * @since 1.5.0
 */

public abstract class MessageHandler {
	private static final Logger logger = LoggerFactory.getLogger(MessageHandler.class);
	
	DeviceFeature				m_feature	 	= null;
	HashMap<String, String> 	m_parameters	= new HashMap<String, String>();
	HashMap<Integer, GroupMessageStateMachine>	m_groupState = new HashMap<Integer, GroupMessageStateMachine>();
	/**
	 * Constructor
	 * @param p state publishing object for dissemination of state changes
	 */
	MessageHandler(DeviceFeature p) {
		m_feature = p;
	}
	/**
	 * Method that processes incoming message. The cmd1 parameter
	 * has been extracted earlier already (to make a decision which message handler to call),
	 * and is passed in as an argument so cmd1 does not have to be extracted from the message again.
	 * @param group all-link group or -1 if not specified
	 * @param cmd1 the insteon cmd1 field
	 * @param msg the received insteon message
	 * @param feature the DeviceFeature to which this message handler is attached
	 * @param fromPort the device (/dev/ttyUSB0) from which the message has been received
	 */
	public abstract void handleMessage(int group, byte cmd1, Msg msg,
			DeviceFeature feature, String fromPort);
	
	/**
	 * Method to send an extended insteon message for querying a device
	 * @param f		DeviceFeature that is being currently handled
	 * @param aCmd1	cmd1 for message to be sent
	 * @param aCmd2	cmd2 for message to be sent
	 */
	public void sendExtendedQuery(DeviceFeature f, byte aCmd1, byte aCmd2) {
		InsteonDevice d = f.getDevice();
		try {
			Msg m = d.makeExtendedMessage((byte)0x1f, aCmd1, aCmd2);
			m.setQuietTime(500L);
			d.enqueueMessage(m, f);
		} catch (IOException e) {
			logger.warn("i/o problem sending query message to device {}", d.getAddress());
		} catch (FieldException e) {
			logger.warn("field exception sending query message to device {}", d.getAddress());
		}
	}
	/**
	 * Retrieve group parameter or -1 if no group is specified
	 * @return group parameter
	 */
	public int getGroup() {
		return (getIntParameter("group", -1));
	}
	/**
	 * Helper function to get an integer parameter for the handler
	 * @param key name of the int parameter (as specified in device features!)
	 * @param def default to return if parameter not found
	 * @return value of int parameter (or default if not found)
	 */
	protected int getIntParameter(String key, int def) {
		try {
			if (m_parameters.get(key) != null) {
				return Integer.parseInt(m_parameters.get(key));
			}
		} catch (NumberFormatException e) {
			logger.error("malformed int parameter in message handler: {}", key);
		}
		return def;
	}
	/**
	 * Test if message refers to the button configured for given feature
	 * @param msg received message
	 * @param f device feature to test
	 * @return true if we have no button configured or the message is for this button
	 */
	protected boolean isMybutton(Msg msg, DeviceFeature f) {
		int myButton = getIntParameter("button", -1);
		// if there is no button configured for this handler
		// the message is assumed to refer to this feature
		// no matter what button is addressed in the message
		if (myButton == -1) return true;
		
		int button = getButtonInfo(msg, f);
		return button != -1 && myButton == button;
	}
	/**
	 * Determines is an incoming ALL LINK message is a duplicate
	 * @param msg the received ALL LINK message
	 * @return true if this message is a duplicate
	 */
	protected boolean isDuplicate(Msg msg) {
		boolean isDuplicate = false;
		try {
			MsgType t = MsgType.s_fromValue(msg.getByte("messageFlags"));
			int hops = msg.getHopsLeft();
			if (t == MsgType.ALL_LINK_BROADCAST) {
				int group = (int) (msg.getAddress("toAddress").getLowByte() & 0xff);
				byte cmd1 = msg.getByte("command1");
				// if the command is 0x06, then it's success message
				// from the original broadcaster, with which the device
				// confirms that it got all cleanup replies successfully.
				GroupMessage gm = (cmd1 == 0x06) ? GroupMessage.SUCCESS :
										GroupMessage.BCAST;
				isDuplicate = !updateGroupState(group, hops, gm);
			} else if (t == MsgType.ALL_LINK_CLEANUP) {
				// the cleanup messages are direct messages, so the
				// group # is not in the toAddress, but in cmd2 
				int group = (int)(msg.getByte("command2") & 0xff);
				isDuplicate = !updateGroupState(group, hops,
								GroupMessage.CLEAN);
			}
		} catch (IllegalArgumentException e) {
			logger.error("cannot parse msg: {}", msg, e);			
		} catch (FieldException e) {
			logger.error("cannot parse msg: {}", msg, e);
		}
		return (isDuplicate);
	}
	/**
	 * Advance the state of the state machine that suppresses duplicates
	 * 
	 * @param group the insteon group of the broadcast message
	 * @param hops number of hops left
	 * @param a what type of group message came in (action etc)
	 * @return true if this is message is NOT a duplicate
	 */
	private boolean updateGroupState(int group, int hops, GroupMessage a) {
		GroupMessageStateMachine m = m_groupState.get(new Integer(group));
		if (m == null) {
			m = new GroupMessageStateMachine();
			m_groupState.put(new Integer(group), m);
		}
		logger.debug("updating group state for {} to {}", group, a);
		return (m.action(a, hops));
	}
	
	/**
	 * Extract button information from message
	 * @param msg the message to extract from
	 * @param the device feature (needed for debug printing)
	 * @return the button number or -1 if no button found
	 */
	static protected int getButtonInfo(Msg msg, DeviceFeature f) {
		// the cleanup messages have the button number in the command2 field
		// the broadcast messages have it as the lsb of the toAddress
		try {
			int bclean = (int) (msg.getByte("command2") & 0xff);
			int bbcast = (int) (msg.getAddress("toAddress").getLowByte() & 0xff);
			int button = msg.isCleanup() ? bclean : bbcast;
			logger.trace("{} button: {} bclean: {} bbcast: {}",
					f.getDevice().getAddress(), button, bclean, bbcast);
			return button;
		}  catch (FieldException e) {
			logger.error("field exception while parsing msg {}: ", msg, e);
		}
		return -1;
	}
	
	/**
	 * Shorthand to return class name for logging purposes
	 * @return name of the class
	 */
	protected String nm() {
		return (this.getClass().getSimpleName());
	}
	
	/**
	 * Set parameter map
	 * @param hm the parameter map for this message handler
	 */
	public void setParameters(HashMap<String, String> hm) { m_parameters = hm; }
	
	
	//
	//
	// ---------------- the various command handler start here -------------------
	//
	//
	
	public static class DefaultMsgHandler extends MessageHandler {
		DefaultMsgHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
					DeviceFeature f, String fromPort) {
			logger.debug("{} drop unimpl message {}: {}", nm(), Utils.getHexByte(cmd1), msg);
		}
	}

	public static class NoOpMsgHandler extends MessageHandler {
		NoOpMsgHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			logger.debug("{} ignore msg {}: {}", nm(), Utils.getHexByte(cmd1), msg);
		}
	}

	public static class LightOnDimmerHandler extends MessageHandler {
		LightOnDimmerHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			if (isDuplicate(msg) || !isMybutton(msg, f)) {
				return;
			}
			InsteonAddress a = f.getDevice().getAddress();
			if (msg.isAckOfDirect()) {
				logger.error("{}: device {}: ignoring ack of direct.", nm(), a);
			} else {
				logger.info("{}: device {} was turned on. Sending poll request to get actual level", nm(), a);
				m_feature.publish(PercentType.HUNDRED, StateChangeType.ALWAYS);
				// need to poll to find out what level the dimmer is at now.
				// it may not be at 100% because dimmers can be configured
				// to switch to e.g. 75% when turned on.
				Msg m = f.makePollMsg();
				if (m != null)	f.getDevice().enqueueDelayedMessage(m, f, 1000);
			}
		}
	}

	public static class LightOnSwitchHandler extends MessageHandler {
		LightOnSwitchHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			if (!isDuplicate(msg) && isMybutton(msg, f)) {
				logger.info("{}: device {} was switched on.", nm(),
								f.getDevice().getAddress());
				f.publish(OnOffType.ON, StateChangeType.ALWAYS);
			} else {
				logger.debug("ignored message: {} or {}", isDuplicate(msg), isMybutton(msg,f));
			}
		}
	}

	public static class LightOffDimmerHandler extends MessageHandler {
		LightOffDimmerHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			if (!isDuplicate(msg) && isMybutton(msg, f)) {
				logger.info("{}: device {} was turned off.", nm(),
						f.getDevice().getAddress());
				f.publish(PercentType.ZERO, StateChangeType.ALWAYS);
			}
		}
	}

	public static class LightOffSwitchHandler extends MessageHandler {
		LightOffSwitchHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			if (!isDuplicate(msg) && isMybutton(msg, f)) {
				logger.info("{}: device {} was switched off.", nm(),
						f.getDevice().getAddress());
				f.publish(OnOffType.OFF, StateChangeType.ALWAYS);
			}
		}
	}

	/**
	 * A message handler that processes replies to queries.
	 * If command2 == 0xFF then the light has been turned on
	 * else if command2 == 0x00 then the light has been turned off
	 */

	public static class SwitchRequestReplyHandler extends  MessageHandler {
		SwitchRequestReplyHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			try {
				InsteonAddress a = f.getDevice().getAddress();
				int cmd2	= (int) (msg.getByte("command2") & 0xff);
				int button	= this.getIntParameter("button", -1);
				if (button < 0) {
					handleNoButtons(cmd2, a, msg);
				} else {
					boolean isOn = isLEDLit(cmd2, button);
					logger.info("{}: dev {} button {} switched to {}", nm(),
													a, button, isOn ? "ON" : "OFF");
					m_feature.publish(isOn ? OnOffType.ON : OnOffType.OFF, StateChangeType.CHANGED);
				}
			} catch (FieldException e) {
				logger.error("{} error parsing {}: ", nm(), msg, e);
			}
		}
		/**
		 * Handle the case where no buttons have been configured.
		 * In this situation, the only return values should be 0 (light off)
		 * or 0xff (light on)
		 * @param cmd2
		 */
		void handleNoButtons(int cmd2, InsteonAddress a, Msg msg) {
			if (cmd2 == 0) {
				logger.info("{}: set device {} to OFF", nm(), a);
				m_feature.publish(OnOffType.OFF, StateChangeType.CHANGED);
			} else if (cmd2 == 0xff) {
				logger.info("{}: set device {} to ON", nm(), a);
				m_feature.publish(OnOffType.ON, StateChangeType.CHANGED);
			} else {
				logger.warn("{}: {} ignoring unexpected cmd2 in msg: {}",
							nm(), a, msg);
			}	
		}
		/**
		 * Test if cmd byte indicates that button is lit.
		 * The cmd byte has the LED status bitwise from the left:
		 *       87654321
		 * Note that the 2487S has buttons assigned like this:
		 *      22|6543|11
		 * They used the basis of the 8-button remote, and assigned
		 * the ON button to 1+2, the OFF button to 7+8
		 * 
		 * @param cmd    cmd byte as received in message
		 * @param button button to test (number in range 1..8)
		 * @return true if button is lit, false otherwise
		 */
		private boolean isLEDLit(int cmd, int button) {
			boolean isSet = (cmd & (0x1 << (button-1))) != 0;
			logger.trace("cmd: {} button {}", Integer.toBinaryString(cmd), button);
			logger.trace("msk: {} isSet: {}", Integer.toBinaryString(0x1 << (button-1)), isSet);
			return (isSet);
		}
	}

	/**
	 * Handles Dimmer replies to status requests.
	 * In the dimmers case the command2 byte represents the light level from 0-255
	 */
	public static class DimmerRequestReplyHandler extends  MessageHandler {
		DimmerRequestReplyHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			InsteonDevice dev = f.getDevice();
			try {
				int cmd2 = (int) (msg.getByte("command2") & 0xff);
				if (cmd2 == 0xfe) {
					// sometimes dimmer devices are returning 0xfe when on instead of 0xff
					cmd2 = 0xff;
				}

				if (cmd2 == 0) {
					logger.info("{}: set device {} to level 0", nm(),
							dev.getAddress());
					m_feature.publish(PercentType.ZERO, StateChangeType.CHANGED);
				} else if (cmd2 == 0xff) {
					logger.info("{}: set device {} to level 100", nm(),
							dev.getAddress());
					m_feature.publish(PercentType.HUNDRED, StateChangeType.CHANGED);
				} else {
					int level = cmd2*100/255;
					if (level == 0) level = 1;
					logger.info("{}: set device {} to level {}", nm(),
							dev.getAddress(), level);
					m_feature.publish(new PercentType(level), StateChangeType.CHANGED);
				}
			} catch (FieldException e) {
				logger.error("{}: error parsing {}: ", nm(), msg, e);
			}
		}
	}

	public static class StopManualChangeHandler extends MessageHandler {
		StopManualChangeHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			Msg m = f.makePollMsg();
			if (m != null)	f.getDevice().enqueueMessage(m, f);
		}
	}

	public static class InfoRequestReplyHandler extends MessageHandler {
		InfoRequestReplyHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			InsteonDevice dev = f.getDevice();
			if (!msg.isExtended()) {
				logger.warn("{} device {} expected extended msg as info reply, got {}",
						nm(), dev.getAddress(), msg);
				return;
			}
			try {
				int cmd2 = (int) (msg.getByte("command2") & 0xff);
				switch (cmd2) {
				case 0x00: // this is a product data response message
					int prodKey = msg.getInt24("userData2", "userData3", "userData4");
					int devCat  = msg.getByte("userData5");
					int subCat  = msg.getByte("userData6");
					logger.info("{} {} got product data: cat: {} subcat: {} key: {} ",
							nm(), dev.getAddress(), devCat, subCat,	Utils.getHexString(prodKey));
					break;
				case 0x02: // this is a device text string response message
					logger.info("{} {} got text str {} ", nm(), dev.getAddress(), msg);
					break;
				default:
					logger.warn("{} unknown cmd2 = {} in info reply message {}", nm(), cmd2, msg);
					break;
				}
			} catch (FieldException e) {
				logger.error("error parsing {}: ", msg, e);
			}
		}
	}

	public static class MotionSensorDataReplyHandler extends MessageHandler {
		MotionSensorDataReplyHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			InsteonDevice dev = f.getDevice();
			if (!msg.isExtended()) {
				logger.trace("{} device {} ignoring non-extended msg {}", nm(), dev.getAddress(), msg);
				return;
			}
			try {
				int cmd2 = (int) (msg.getByte("command2") & 0xff);
				switch (cmd2) {
				case 0x00: // this is a product data response message
					int batteryLevel = msg.getByte("userData12") & 0xff;
					int lightLevel = msg.getByte("userData11") & 0xff;
					logger.debug("{}: {} got light level: {}, battery level: {}",
								nm(), dev.getAddress(), lightLevel, batteryLevel);
					m_feature.publish(new DecimalType(lightLevel), StateChangeType.CHANGED, "field", "light_level");
					m_feature.publish(new DecimalType(batteryLevel), StateChangeType.CHANGED, "field", "battery_level");
					break;
				default:
					logger.warn("unknown cmd2 = {} in info reply message {}", cmd2, msg);
					break;
				}
			} catch (FieldException e) {
				logger.error("error parsing {}: ", msg, e);
			}
		}
	}
	
	public static class HiddenDoorSensorDataReplyHandler extends MessageHandler {
		HiddenDoorSensorDataReplyHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			InsteonDevice dev = f.getDevice();
			if (!msg.isExtended()) {
				logger.trace("{} device {} ignoring non-extended msg {}", nm(), dev.getAddress(), msg);
				return;
			}
			try {
				int cmd2 = (int) (msg.getByte("command2") & 0xff);
				switch (cmd2) {
				case 0x00: // this is a product data response message
					int batteryLevel = msg.getByte("userData4") & 0xff;
					int batteryWatermark = msg.getByte("userData7") & 0xff;
					logger.debug("{}: {} got light level: {}, battery level: {}",
								nm(), dev.getAddress(), batteryWatermark, batteryLevel);
					m_feature.publish(new DecimalType(batteryWatermark), StateChangeType.CHANGED, "field", "battery_watermark_level");
					m_feature.publish(new DecimalType(batteryLevel), StateChangeType.CHANGED, "field", "battery_level");
					break;
				default:
					logger.warn("unknown cmd2 = {} in info reply message {}", cmd2, msg);
					break;
				}
			} catch (FieldException e) {
				logger.error("error parsing {}: ", msg, e);
			}
		}
	}

	public static class PowerMeterUpdateHandler extends MessageHandler {
		PowerMeterUpdateHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			if (msg.isExtended()) {
				try {
					// see iMeter developer notes 2423A1dev-072013-en.pdf
					int b7	= msg.getByte("userData7")	& 0xff;
					int b8	= msg.getByte("userData8")	& 0xff;
					int watts = (b7 << 8) | b8;
					if (watts > 32767) {
						watts -= 65535;
					}

					int b9	= msg.getByte("userData9")	& 0xff;
					int b10	= msg.getByte("userData10")	& 0xff;
					int b11	= msg.getByte("userData11")	& 0xff;
					int b12	= msg.getByte("userData12")	& 0xff;
					BigDecimal kwh = BigDecimal.ZERO;
					if (b9 < 254) {
						int e = (b9 << 24) | (b10 << 16) | (b11 << 8) | b12;
						kwh = new BigDecimal(e * 65535.0 / (1000 * 60 * 60 * 60)).setScale(4, RoundingMode.HALF_UP);
					}

					logger.debug("{}:{} watts: {} kwh: {} ", nm(), f.getDevice().getAddress(), watts, kwh);
					m_feature.publish(new DecimalType(kwh), StateChangeType.CHANGED, "field", "kwh");
					m_feature.publish(new DecimalType(watts), StateChangeType.CHANGED, "field", "watts");
				} catch (FieldException e) {
					logger.error("error parsing {}: ", msg, e);
				}
			}
		}
	}
	
	public static class PowerMeterResetHandler extends MessageHandler {
		PowerMeterResetHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			InsteonDevice dev = f.getDevice();
			logger.info("{}: power meter {} was reset", nm(), dev.getAddress());

			// poll device to get updated kilowatt hours and watts
			Msg m = f.makePollMsg();
			if (m != null)	f.getDevice().enqueueMessage(m, f);
		}
	}
	
	public static class LastTimeHandler extends MessageHandler {
		LastTimeHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1a, Msg msg,
				DeviceFeature f, String fromPort) {
			GregorianCalendar calendar = new GregorianCalendar();
			calendar.setTimeInMillis(System.currentTimeMillis());
			DateTimeType t = new DateTimeType(calendar);
			m_feature.publish(t, StateChangeType.ALWAYS);
		}
	}

	public static class ContactRequestReplyHandler extends MessageHandler {
		ContactRequestReplyHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1a, Msg msg,
				DeviceFeature f, String fromPort) {
			byte cmd  = 0x00;
			byte cmd2 = 0x00;
			try {
				cmd = msg.getByte("Cmd");
				cmd2 = msg.getByte("command2");
			} catch (FieldException e) {
				logger.debug("{} no cmd found, dropping msg {}", nm(), msg);
				return;
			}
			if (msg.isAckOfDirect() && (f.getQueryStatus() == DeviceFeature.QueryStatus.QUERY_PENDING)
					&& cmd == 0x50) {
				OpenClosedType oc = (cmd2 == 0) ? OpenClosedType.OPEN : OpenClosedType.CLOSED;
				logger.info("{}: set contact {} to: {}", nm(), f.getDevice().getAddress(), oc);
				m_feature.publish(oc, StateChangeType.CHANGED);
			}
		}
	}

	public static class ClosedContactHandler extends MessageHandler {
		ClosedContactHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			m_feature.publish(OpenClosedType.CLOSED, StateChangeType.ALWAYS);
		}
	}

	public static class OpenedContactHandler extends MessageHandler {
		OpenedContactHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			m_feature.publish(OpenClosedType.OPEN, StateChangeType.ALWAYS);
		}
	}

	public static class OpenedOrClosedContactHandler extends MessageHandler {
		OpenedOrClosedContactHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			if (cmd1 != 0x11) return;
			try {
				byte cmd2 = msg.getByte("command2");
				switch (cmd2) {
				case 0x02:
					m_feature.publish(OpenClosedType.CLOSED, StateChangeType.CHANGED);
					break;
				case 0x01:
					m_feature.publish(OpenClosedType.OPEN, StateChangeType.CHANGED);
					break;
				default: // do nothing
					break;
				}
			} catch (FieldException e) {
				logger.debug("{} no cmd2 found, dropping msg {}", nm(), msg);
				return;
			}

		}
	}

	public static class ClosedSleepingContactHandler extends MessageHandler {
		ClosedSleepingContactHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			m_feature.publish(OpenClosedType.CLOSED, StateChangeType.ALWAYS);
			sendExtendedQuery(f, (byte)0x2e, (byte) 00);
		}
	}

	public static class OpenedSleepingContactHandler extends MessageHandler {
		OpenedSleepingContactHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			m_feature.publish(OpenClosedType.OPEN, StateChangeType.ALWAYS);
			sendExtendedQuery(f, (byte)0x2e, (byte) 00);
		}
	}
	/**
	 * Process X10 messages that are generated when another controller
	 * changes the state of an X10 device.
	 */
	public static class X10OnHandler extends  MessageHandler {
		X10OnHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			InsteonAddress a = f.getDevice().getAddress();
			logger.info("{}: set X10 device {} to ON", nm(), a);
			m_feature.publish(OnOffType.ON, StateChangeType.ALWAYS);
		}
	}
	public static class X10OffHandler extends  MessageHandler {
		X10OffHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			InsteonAddress a = f.getDevice().getAddress();
			logger.info("{}: set X10 device {} to OFF", nm(), a);
			m_feature.publish(OnOffType.OFF, StateChangeType.ALWAYS);
		}
	}
	public static class X10BrightHandler extends  MessageHandler {
		X10BrightHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			InsteonAddress a = f.getDevice().getAddress();
			logger.debug("{}: ignoring brighten message for device {}", nm(), a);
		}
	}
	public static class X10DimHandler extends  MessageHandler {
		X10DimHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			InsteonAddress a = f.getDevice().getAddress();
			logger.debug("{}: ignoring dim message for device {}", nm(), a);
		}
	}
	public static class X10OpenHandler extends  MessageHandler {
		X10OpenHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			InsteonAddress a = f.getDevice().getAddress();
			logger.info("{}: set X10 device {} to OPEN", nm(), a);
			m_feature.publish(OpenClosedType.OPEN, StateChangeType.ALWAYS);
		}
	}
	public static class X10ClosedHandler extends  MessageHandler {
		X10ClosedHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			InsteonAddress a = f.getDevice().getAddress();
			logger.info("{}: set X10 device {} to CLOSED", nm(), a);
			m_feature.publish(OpenClosedType.CLOSED, StateChangeType.ALWAYS);
		}
	}

	/**
	 * Handles Thermostat replies to Set Cool SetPoint requests.
	 */
	public static class ThermostatSetPointMsgHandler extends  MessageHandler {
		ThermostatSetPointMsgHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			InsteonDevice dev = f.getDevice();
			try {
				if (msg.isExtended()) {
					logger.info("{}: received msg for feature {}", nm(), f.getName());
					int level = ((f.getName()).equals("ThermostatCoolSetPoint")) ? (int)(msg.getByte("userData7") & 0xff) : (int)(msg.getByte("userData8") & 0xff);
					logger.info("{}: got SetPoint from {} of value: {}", nm(), dev.getAddress(), level);
					f.publish(new DecimalType(level), StateChangeType.CHANGED);
				} else {
					logger.info("{}: received msg for feature {}", nm(), f.getName());
					int cmd2 = (int) (msg.getByte("command2") & 0xff);
					int level = cmd2/2;
					logger.info("{}: got SETPOINT from {} of value: {}", nm(), dev.getAddress(), level);
					f.publish(new DecimalType(level), StateChangeType.CHANGED);
				}
			} catch (FieldException e) {
				logger.debug("{} no cmd2 found, dropping msg {}", nm(), msg);
				return;
			}
		}
	}

	/**
	 * Handles Thermostat replies to Temperature requests.
	 */
	public static class ThermostatTemperatureRequestReplyHandler extends  MessageHandler {
		ThermostatTemperatureRequestReplyHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			InsteonDevice dev = f.getDevice();
			try {
				int cmd2 = (int) (msg.getByte("command2") & 0xff);
				int level = cmd2/2;
				logger.info("{}: got TEMPERATURE from {} of value: {}", nm(), dev.getAddress(), level);
				logger.info("{}: set device {} to level {}", nm(), dev.getAddress(), level);
				f.publish(new DecimalType(level), StateChangeType.CHANGED);
			} catch (FieldException e) {
				logger.debug("{} no cmd2 found, dropping msg {}", nm(), msg);
				return;
			}
		}
	}	
		
	/**
	 * Handles Thermostat replies to Humidity requests.
	 */
	public static class ThermostatHumidityRequestReplyHandler extends  MessageHandler {
		ThermostatHumidityRequestReplyHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			InsteonDevice dev = f.getDevice();
			try {
				int cmd2 = (int) msg.getByte("command2");
				logger.info("{}: got HUMIDITY from {} of value: {}", nm(), dev.getAddress(), cmd2);
				logger.info("{}: set device {} to level {}", nm(), dev.getAddress(), cmd2);
				f.publish(new PercentType(cmd2), StateChangeType.CHANGED);
			} catch (FieldException e) {
				logger.debug("{} no cmd2 found, dropping msg {}", nm(), msg);
				return;
			}
		}
	}
	
	/**
	 * Handles Thermostat replies to Mode requests.
	 */
	public static class ThermostatModeControlReplyHandler extends  MessageHandler {
		ThermostatModeControlReplyHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			InsteonDevice dev = f.getDevice();
			try {
				/**
				* Cmd2 Description 										Thermostat Support 	Comments
				* 0x04 set mode to heat and returns 04 in ACK 			yes 				On Heat
				* 0x05 set mode to cool and returns 05 in ACK 			yes 				On Cool
				* 0x06 set mode to manual auto and returns 06 in ACK 	yes 				Manual Auto
				*/
				byte cmd2 = msg.getByte("command2");
				switch (cmd2) {
				case 0x04:
					logger.info("{}: set device {} to {}", nm(),
							dev.getAddress(), "HEAT");
					f.publish(new DecimalType(2), StateChangeType.CHANGED);
					break;
				case 0x05:
					logger.info("{}: set device {} to {}", nm(),
							dev.getAddress(), "COOL");
					f.publish(new DecimalType(1), StateChangeType.CHANGED);
					break;
				case 0x06:
					logger.info("{}: set device {} to {}", nm(),
							dev.getAddress(), "AUTO");
					f.publish(new DecimalType(3), StateChangeType.CHANGED);
					break;
				default: // do nothing
					break;
				}
			} catch (FieldException e) {
				logger.debug("{} no cmd2 found, dropping msg {}", nm(), msg);
				return;
			}
		}
	}

	/**
	 * Handles Thermostat replies to Fan requests.
	 */
	public static class ThermostatFanControlReplyHandler extends  MessageHandler {
		ThermostatFanControlReplyHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			InsteonDevice dev = f.getDevice();
			try {
				/**
				* Cmd2 Description 										Thermostat Support 	Comments
				* 0x07 Turn fan on and returns 07 in ACK 				yes 				On Fan
				* 0x08 Turn fan auto mode and returns 08 in ACK 		yes 				Auto Fan
				* 0x09 Turn all off and returns 09 in ACK 				yes 				Off All
				*/
				byte cmd2 = msg.getByte("command2");
				switch (cmd2) {
				case 0x07:
					logger.info("{}: set device {} to {}", nm(),
							dev.getAddress(), "ON");
					f.publish(new DecimalType(2), StateChangeType.CHANGED);
					break;
				case 0x08:
					logger.info("{}: set device {} to {}", nm(),
							dev.getAddress(), "AUTO");
					f.publish(new DecimalType(3), StateChangeType.CHANGED);
					break;	
				case 0x09:
					logger.info("{}: set device {} to {}", nm(),
							dev.getAddress(), "OFF");
					f.publish(new DecimalType(1), StateChangeType.CHANGED);
					break;	
				default: // do nothing
					break;
				}
			} catch (FieldException e) {
				logger.debug("{} no cmd2 found, dropping msg {}", nm(), msg);
				return;
			}
		}
	}

	/**
	 * Handles Thermostat replies to Master requests.
	 */
	public static class ThermostatMasterControlReplyHandler extends  MessageHandler {
		ThermostatMasterControlReplyHandler(DeviceFeature p) { super(p); }
		@Override
		public void handleMessage(int group, byte cmd1, Msg msg,
				DeviceFeature f, String fromPort) {
			try {
				/**
				* 
				*/
				byte cmd2 = msg.getByte("userData3");
				switch (cmd2) {
				case 0x00:
					logger.info("{}: set PRIMARY Thermostat to MASTER", nm());
					f.publish(new DecimalType(1), StateChangeType.CHANGED);
					break;
				case 0x01:
					logger.info("{}: set SECONDARY Thermostat to MASTER", nm());
					f.publish(new DecimalType(2), StateChangeType.CHANGED);
					break;	
				case 0x02:
					logger.info("{}: set TERTIARY Thermostat to MASTER", nm());
					f.publish(new DecimalType(3), StateChangeType.CHANGED);
					break;	
				default: // do nothing
					break;
				}
			} catch (FieldException e) {
				logger.debug("{} no cmd2 found, dropping msg {}", nm(), msg);
				return;
			}
		}
	}
	
	/**
	 * Factory method for creating handlers of a given name using java reflection
	 * @param name the name of the handler to create
	 * @param params 
	 * @param f the feature for which to create the handler
	 * @return the handler which was created
	 */
	public static <T extends MessageHandler> T s_makeHandler(String name, HashMap<String, String> params, DeviceFeature f) {
		String cname = MessageHandler.class.getName() + "$" + name;
		try {
			Class<?> c = Class.forName(cname);
			@SuppressWarnings("unchecked")
			Class<? extends T> dc = (Class <? extends T>) c;
			T mh = dc.getDeclaredConstructor(DeviceFeature.class).newInstance(f);
			mh.setParameters(params);
			return mh;
		} catch (Exception e) {
			logger.error("error trying to create message handler: {}", name, e);
		}
		return null;
	}
}


File: bundles/binding/org.openhab.binding.insteonplm/src/main/java/org/openhab/binding/insteonplm/internal/device/ModemDBBuilder.java
/**
 * Copyright (c) 2010-2015, openHAB.org and others.
 *
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 */
package org.openhab.binding.insteonplm.internal.device;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map.Entry;

import org.openhab.binding.insteonplm.internal.driver.ModemDBEntry;
import org.openhab.binding.insteonplm.internal.driver.Port;
import org.openhab.binding.insteonplm.internal.message.FieldException;
import org.openhab.binding.insteonplm.internal.message.Msg;
import org.openhab.binding.insteonplm.internal.message.MsgListener;
import org.openhab.binding.insteonplm.internal.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
/**
 * Builds the modem database from incoming link record messages
 * 
 * @author Bernd Pfrommer
 * @since 1.5.0
 */
public class ModemDBBuilder implements MsgListener {
	private static final Logger logger = LoggerFactory.getLogger(ModemDBBuilder.class);
	
	Port m_port = null;
	
	public ModemDBBuilder(Port port) {
		m_port = port;
	}
	
	public void start() {
		m_port.addListener(this);
		logger.debug("querying port for first link record");
		try {
			m_port.writeMessage(Msg.s_makeMessage("GetFirstALLLinkRecord"));
		} catch (IOException e) {
			logger.error("cannot query for link messages", e);
		}
	}
	
	/**
	 * processes link record messages from the modem to build database
	 * and request more link records if not finished.
	 * {@inheritDoc}
	 */
	@Override
	public void msg(Msg msg, String fromPort) {
		if (msg.isPureNack()) return;
		try {
			if (msg.getByte("Cmd") == 0x69 ||
						msg.getByte("Cmd") == 0x6a) {
				// If the flag is "ACK/NACK", a record response
				// will follow, so we do nothing here.
				// If its "NACK", there are none
				if (msg.getByte("ACK/NACK") == 0x15) {
					logger.debug("got all link records.");
					done();
				}
			} else if (msg.getByte("Cmd") == 0x57) {
				// we got the link record response
				updateModemDB(msg);
				m_port.writeMessage(Msg.s_makeMessage("GetNextALLLinkRecord"));
			}
		} catch (FieldException e) {
			logger.debug("bad field handling link records {}", e);
		} catch (IOException e) {
			logger.debug("got IO exception handling link records {}", e);
		} catch (IllegalStateException e) {
			logger.debug("got exception requesting link records {}", e);
		}
	}
	
	private void done() {
		logModemDB();
		m_port.removeListener(this);
		m_port.modemDBComplete();
	}
	
	private void logModemDB() {
		try {
			logger.debug("MDB ------- start of modem link records ------------------");
			HashMap<InsteonAddress, ModemDBEntry> dbes = m_port.getDriver().lockModemDBEntries();
			for (Entry<InsteonAddress, ModemDBEntry> db : dbes.entrySet()) {
				ArrayList<Msg> lrs = db.getValue().getLinkRecords();
				for (Msg m: lrs) {
					int recordFlags = m.getByte("RecordFlags") & 0xff;
					String ms = ((recordFlags & (0x1 << 6)) != 0) ? "CTRL" : "RESP";
					logger.debug("MDB {}: {} group: {} data1: {} data2: {} data3: {}",
								db.getKey(), ms, toHex(m.getByte("ALLLinkGroup")),
									toHex(m.getByte("LinkData1")), toHex(m.getByte("LinkData2")),
											toHex(m.getByte("LinkData2")));
				}
				logger.debug("MDB -----");
			}
			logger.debug("MDB ---------------- end of modem link records -----------");
		} catch (FieldException e) {
			logger.error("cannot access field:", e);
		} finally {
			m_port.getDriver().unlockModemDBEntries();
		}
	}
	
	public static String toHex(byte b) {
		return Utils.getHexString(b);
	}
	
	private void updateModemDB(Msg m) 	{
		try {
			HashMap<InsteonAddress, ModemDBEntry> dbes = m_port.getDriver().lockModemDBEntries();
			InsteonAddress linkAddr = m.getAddress("LinkAddr");
			ModemDBEntry dbe = dbes.get(linkAddr);
			if (dbe == null) {
				dbe = new ModemDBEntry(linkAddr);
				dbes.put(linkAddr, dbe);
			}
			dbe.setPort(m_port);
			dbe.addLinkRecord(m);
		} catch (FieldException e) {
			logger.error("cannot access field:", e);
		} finally {
			m_port.getDriver().unlockModemDBEntries();
		}
	}
}


File: bundles/binding/org.openhab.binding.insteonplm/src/main/java/org/openhab/binding/insteonplm/internal/driver/Driver.java
/**
 * Copyright (c) 2010-2015, openHAB.org and others.
 *
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 */
package org.openhab.binding.insteonplm.internal.driver;
import java.io.IOException;
import java.util.HashMap;
import java.util.concurrent.locks.ReentrantLock;

import org.openhab.binding.insteonplm.internal.device.InsteonAddress;
import org.openhab.binding.insteonplm.internal.message.Msg;
import org.openhab.binding.insteonplm.internal.message.MsgListener;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
/**
 * The driver class manages the modem ports.
 * XXX: at this time, only a single modem has ever been used. Expect
 * the worst if you connect multiple modems. When multiple modems
 * are required, this code needs to be tested and fixed.
 * 
 * @author Bernd Pfrommer
 * @since 1.5.0
 */

public class Driver {
	private static final Logger logger = LoggerFactory.getLogger(Driver.class);

	// maps device name to serial port, i.e /dev/insteon -> Port object
	private HashMap<String, Port> m_ports = new HashMap<String, Port>();
	private DriverListener m_listener = null; // single listener for notifications
	private HashMap<InsteonAddress, ModemDBEntry> m_modemDBEntries = new HashMap<InsteonAddress, ModemDBEntry>();
	private ReentrantLock m_modemDBEntriesLock = new ReentrantLock();

	public void setDriverListener(DriverListener listener) {
		m_listener = listener;
	}
	public boolean isReady() {
		for (Port p : m_ports.values()) {
			if (!p.isRunning()) return false;
		}
		return true;
	}
	public HashMap<InsteonAddress, ModemDBEntry> lockModemDBEntries() {
		m_modemDBEntriesLock.lock();
		return m_modemDBEntries;
	}
	public void unlockModemDBEntries() {
		m_modemDBEntriesLock.unlock();
	}
	/**
	 * Add new port (modem) to the driver
	 * @param name the name of the port (from the config file, e.g. port_0, port_1, etc
	 * @param port the device name, e.g. /dev/insteon, /dev/ttyUSB0 etc
	 */
	public void addPort(String name, String port) {
		if (m_ports.keySet().contains(port)) {
			logger.warn("ignored attempt to add duplicate port: {} {}", name, port);
		} else {
			m_ports.put(port, new Port(port, this));
			logger.debug("added new port: {} {}", name, port);
		}
	}
	/**
	 * Register a message listener with a port
	 * @param listener the listener who wants to listen to port messages
	 * @param port the port (e.g. /dev/ttyUSB0) to which the listener listens
	 */
	public void addMsgListener(MsgListener listener, String port) {
		if (m_ports.keySet().contains(port)) {
			m_ports.get(port).addListener(listener);
		} else {
			logger.error("referencing unknown port {}!", port);
		}
	}
	
	public void startAllPorts() {
		for (Port p : m_ports.values()) { p.start(); }
	}
	
	public void stopAllPorts() {
		for (Port p : m_ports.values()) { p.stop(); }
	}

	/**
	 * Write message to a port
	 * @param port name of the port to write to (e.g. '/dev/ttyUSB0')
	 * @param m the message to write
	 * @throws IOException
	 */
	public void writeMessage(String port, Msg m) throws IOException {
		Port p = getPort(port);
		if (p == null) {
			logger.error("cannot write to unknown port {}", port);
			throw new IOException();
		}
		p.writeMessage(m);
	}
	
	public String getDefaultPort() {
		return (m_ports.isEmpty() ? null : m_ports.keySet().iterator().next());
	}
	
	public int getNumberOfPorts() {
		int n = 0;
		for (Port p : m_ports.values()) {
			if (p.isRunning()) n++;
		}
		return n;
	}
	
	public boolean isMsgForUs(InsteonAddress toAddr) {
		if (toAddr == null) return false;
		for (Port p : m_ports.values()) {
			if (p.getAddress().equals(toAddr)) return true;
		}
		return false;
	}
	/**
	 * Get port object corresponding to device
	 * @param port device name of port (e.g. /dev/ttyUSB0)
	 * @return corresponding Port object or null if not found 
	 */
	public Port getPort(String port) {
		if (port.equalsIgnoreCase("DEFAULT")) {
			if (m_ports.isEmpty()) {
				logger.error("no default port found!");
				return null;
			}
			return m_ports.values().iterator().next();
		}
		if (!m_ports.containsKey(port)) {
			logger.error("no port of name {} found!", port);
			return null;
		}
		return m_ports.get(port);
	}
	
	public void modemDBComplete(Port port) {
		// check if all ports have a complete device list
		if (!isModemDBComplete()) return;
		// if yes, notify listener
		m_listener.driverCompletelyInitialized();
	}

	public boolean isModemDBComplete() {
		// check if all ports have a complete device list
		for (Port p : m_ports.values()) {
			if (!p.isModemDBComplete()) {
				return false;
			}
		}
		return true;
	}
}


File: bundles/binding/org.openhab.binding.insteonplm/src/main/java/org/openhab/binding/insteonplm/internal/driver/Port.java
/**
 * Copyright (c) 2010-2015, openHAB.org and others.
 *
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 */
package org.openhab.binding.insteonplm.internal.driver;

import java.io.IOException;
import java.util.ArrayList;
import java.util.concurrent.LinkedBlockingQueue;

import org.openhab.binding.insteonplm.internal.device.ModemDBBuilder;
import org.openhab.binding.insteonplm.internal.device.DeviceType;
import org.openhab.binding.insteonplm.internal.device.DeviceTypeLoader;
import org.openhab.binding.insteonplm.internal.device.InsteonAddress;
import org.openhab.binding.insteonplm.internal.device.InsteonDevice;
import org.openhab.binding.insteonplm.internal.message.FieldException;
import org.openhab.binding.insteonplm.internal.message.Msg;
import org.openhab.binding.insteonplm.internal.message.MsgFactory;
import org.openhab.binding.insteonplm.internal.message.MsgListener;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
/**
 * The Port class represents a port, that is a connection to either an Insteon modem either through
 * a serial or USB port, or via an Insteon Hub.
 * It does the initialization of the port, and (via its inner classes IOStreamReader and IOStreamWriter)
 * manages the reading/writing of messages on the Insteon network.
 * 
 * The IOStreamReader and IOStreamWriter class combined implement the somewhat tricky flow control protocol.
 * In combination with the MsgFactory class, the incoming data stream is turned into a Msg structure
 * for further processing by the upper layers (MsgListeners).
 *
 * A write queue is maintained to pace the flow of outgoing messages. Sending messages back-to-back
 * can lead to dropped messages.
 *
 *
 * @author Bernd Pfrommer
 * @author Daniel Pfrommer
 * @since 1.5.0
 */

public class Port {
	private static final Logger logger = LoggerFactory.getLogger(Port.class);

	/**
	 * The ReplyType is used to keep track of the state of the serial port receiver
	 */
	enum ReplyType {
		GOT_ACK,
		WAITING_FOR_ACK,
		GOT_NACK
	}

	private IOStream		m_ioStream	= null;
	private	String			m_devName	= "INVALID";
	private	String			m_logName	= "INVALID";
	private Modem			m_modem		= null;
	private IOStreamReader	m_reader	= null;
	private	IOStreamWriter	m_writer	= null;
	private	final int		m_readSize	= 1024; // read buffer size
	private	Thread			m_readThread  = null;
	private	Thread			m_writeThread = null;
	private	boolean			m_running	  = false;
	private boolean			m_modemDBComplete = false;
	private MsgFactory		m_msgFactory = new MsgFactory();
	private Driver			m_driver	 = null;
	private ArrayList<MsgListener>	 m_listeners = new ArrayList<MsgListener>();
	private LinkedBlockingQueue<Msg> m_writeQueue = new LinkedBlockingQueue<Msg>();

	/**
	 * Constructor
	 * @param devName the name of the port, i.e. '/dev/insteon'
	 * @param d The Driver object that manages this port
	 */
	public Port(String devName, Driver d) {
		m_devName	= devName;
		m_driver	= d;
		m_logName	= devName;
		m_modem		= new Modem();
		addListener(m_modem);
		m_ioStream 	= IOStream.s_create(devName);
		m_reader	= new IOStreamReader();
		m_writer	= new IOStreamWriter();
	}

	public synchronized boolean isModemDBComplete() { return (m_modemDBComplete); }
	public boolean 			isRunning() 	{ return m_running; }
	public InsteonAddress	getAddress()	{ return m_modem.getAddress(); }
	public String			getDeviceName()	{ return m_devName; }
	public Driver			getDriver()		{ return m_driver; }

	
	public void addListener (MsgListener l) {
		synchronized(m_listeners) {
			if (!m_listeners.contains(l)) m_listeners.add(l);
		}
	}
	
	public void removeListener(MsgListener l) {
		synchronized(m_listeners) {
			if (m_listeners.remove(l)) {
				// logger.debug("removed listener from port");
			}
		}
	}

	/**
	 * Starts threads necessary for reading and writing
	 */
	public void start() {
		logger.debug("starting port {}", m_logName);
		if (m_running) {
			logger.debug("port {} already running, not started again", m_logName);
		}
		if (!m_ioStream.open()) {
			logger.debug("failed to open port {}", m_logName);
			return;
		}
		m_readThread	= new Thread(m_reader);
		m_writeThread	= new Thread(m_writer);
		m_readThread.setName(m_logName + " Reader");
		m_writeThread.setName(m_logName + " Writer");
		m_readThread.start();
		m_writeThread.start();
		m_modem.initialize();
		ModemDBBuilder mdbb = new ModemDBBuilder(this);
		mdbb.start(); // start downloading the device list
		m_running = true;
	}

	/**
	 * Stops all threads
	 */
	public void stop() {
		if (!m_running) {
			logger.debug("port {} not running, no need to stop it", m_logName);
			return;
		}
		if (m_readThread != null) m_readThread.interrupt();
		if (m_writeThread != null) m_writeThread.interrupt();
		logger.debug("waiting for read thread to exit for port {}",
				m_logName);
		try {
			if (m_readThread != null) m_readThread.join();
		} catch (InterruptedException e) {
			logger.debug("got interrupted waiting for read thread to exit.");
		}
		logger.debug("waiting for write thread to exit for port {}",
				m_logName);
		try {
			if (m_writeThread != null) m_writeThread.join();
		} catch (InterruptedException e) {
			logger.debug("got interrupted waiting for write thread to exit.");
		}
		logger.debug("all threads for port {} stopped.", m_logName);
		m_ioStream.close();
		m_running = false;
		synchronized (m_listeners) {
			m_listeners.clear();
		}
	}
	/**
	 * Adds message to the write queue
	 * @param m message to be added to the write queue
	 * @throws IOException
	 */
	public void writeMessage(Msg m) throws IOException {
		if (m == null) {
			logger.error("trying to write null message!");
			throw new IOException("trying to write null message!");
		}
		if (m.getData() == null) {
			logger.error("trying to write message without data!");
			throw new IOException("trying to write message without data!");
		}
		try {
			m_writeQueue.add(m);
			logger.trace("enqueued msg: {}", m);
		} catch (IllegalStateException e) {
			logger.error("cannot write message {}, write queue is full!", m);
		}
		
	}

	/**
	 * Gets called by the modem database builder when the modem database is complete
	 */
	public void modemDBComplete() {
		synchronized (this) {
			m_modemDBComplete = true;
		}
		m_driver.modemDBComplete(this);
	}

	/**
	 * The IOStreamReader uses the MsgFactory to turn the incoming bytes into
	 * Msgs for the listeners. It also communicates with the IOStreamWriter
	 * to implement flow control (tell the IOStreamWriter that it needs to retransmit,
	 * or the reply message has been received correctly).
	 * 
	 * @author Bernd Pfrommer
	 */
	class IOStreamReader implements Runnable {
		
		private ReplyType	m_reply = ReplyType.GOT_ACK;
		private	Object		m_replyLock = new Object();
		/**
		 * Helper function for implementing synchronization between reader and writer
		 * @return reference to the RequesReplyLock
		 */
		public	Object getRequestReplyLock() { return m_replyLock; }

		@Override
		public void run() {
			logger.debug("starting reader...");
			byte[] buffer = new byte[2 * m_readSize];
			for (int len = -1; (len = m_ioStream.read(buffer, 0, m_readSize)) > 0;) {
				m_msgFactory.addData(buffer, len);
				processMessages();
			}
		}
		
		private void processMessages() {
			try {
				// must call processData() until we get a null pointer back
				for (Msg m = m_msgFactory.processData(); m != null;
						m = m_msgFactory.processData()) {
						toAllListeners(m);
						notifyWriter(m);
				}
			} catch (IOException e) {
				// got bad data from modem,
				// unblock those waiting for ack
				logger.warn("bad data received: {}", e.toString());
				synchronized (getRequestReplyLock()) {
					if (m_reply == ReplyType.WAITING_FOR_ACK) {
						logger.warn("got bad data back, must assume message was acked.");
						m_reply = ReplyType.GOT_ACK;
						getRequestReplyLock().notify();
					}
				}
			}
		}

		private void notifyWriter(Msg msg) {
			synchronized (getRequestReplyLock()) {
				if (m_reply == ReplyType.WAITING_FOR_ACK) {
					if (!msg.isUnsolicited()) {
						m_reply = (msg.isPureNack() ? ReplyType.GOT_NACK : ReplyType.GOT_ACK);
						logger.trace("signaling receipt of ack: {}", (m_reply == ReplyType.GOT_ACK));
						getRequestReplyLock().notify();
					} else if (msg.isPureNack()){
						m_reply = ReplyType.GOT_NACK;
						logger.trace("signaling receipt of pure nack");
						getRequestReplyLock().notify();
					} else {
						logger.trace("got unsolicited message");
					}
				}
			}
		}

		@SuppressWarnings("unchecked")
		private void toAllListeners(Msg msg) {
			// When we deliver the message, the recipient
			// may in turn call removeListener() or addListener(),
			// thereby corrupting the very same list we are iterating
			// through. That's why we make a copy of it, and
			// iterate through the copy.
			ArrayList<MsgListener> tempList = null;
			synchronized(m_listeners) {
				tempList= (ArrayList<MsgListener>) m_listeners.clone();
			}
			for (MsgListener l : tempList) {
				l.msg(msg, m_devName); // deliver msg to listener
			}
		}
		
		/**
		 * Blocking wait for ack or nack from modem.
		 * Called by IOStreamWriter for flow control.
		 * @return true if retransmission is necessary
		 */
		public boolean waitForReply() {
			m_reply = ReplyType.WAITING_FOR_ACK;
			while (m_reply == ReplyType.WAITING_FOR_ACK) {
				try {
					logger.trace("writer waiting for ack.");
					getRequestReplyLock().wait();
					logger.trace("writer got ack: {}", (m_reply == ReplyType.GOT_ACK));
				} catch (InterruptedException e) {
					// do nothing
				}
			}
			return (m_reply == ReplyType.GOT_NACK);
		}
	}
	/**
	 * Writes messages to the port. Flow control is implemented following Insteon
	 * documents to avoid over running the modem.
	 * 
	 * @author Bernd Pfrommer
	 */
	class IOStreamWriter implements Runnable {
		private static final int WAIT_TIME = 200; // milliseconds
		@Override
		public void run() {
			logger.debug("starting writer...");
			while(true) {
				try {
					// this call blocks until the lock on the queue is released
					logger.trace("writer checking message queue");
					Msg msg = m_writeQueue.take();
					if (msg.getData() == null) {
						logger.error("found null message in write queue!");
					} else {
						logger.debug("writing ({}): {}", msg.getQuietTime(), msg);
						// To debug race conditions during startup (i.e. make the .items
						// file definitions be available *before* the modem link records,
						// slow down the modem traffic with the following statement:
						// Thread.sleep(500);
						synchronized (m_reader.getRequestReplyLock()) {
							m_ioStream.write(msg.getData());
							while (m_reader.waitForReply()) {
								Thread.sleep(WAIT_TIME);
								logger.trace("retransmitting msg: {}", msg);
								m_ioStream.write(msg.getData());
							}
							
						}
						// if rate limited, need to sleep now.
						if (msg.getQuietTime() > 0) {
							Thread.sleep(msg.getQuietTime());
						}
					}
				} catch (InterruptedException e) {
					logger.error("got interrupted exception in write thread:", e);
				} catch (Exception e) {
					logger.error("got exception in write thread:", e);
				}
			}
		}
	}
	/**
	 * Class to get info about the modem
	 */
	class Modem implements MsgListener {
		private InsteonDevice m_device = null;
		InsteonAddress getAddress() { return (m_device == null) ? new InsteonAddress() : (m_device.getAddress()); }
		InsteonDevice getDevice() { return m_device; }
		@Override
		public void msg(Msg msg, String fromPort) {
			try {
				if (msg.isPureNack()) return;
				if (msg.getByte("Cmd") == 0x60) {
					// add the modem to the device list
					InsteonAddress a = new InsteonAddress(msg.getAddress("IMAddress"));
					String prodKey = "0x000045";
					DeviceType dt = DeviceTypeLoader.s_instance().getDeviceType(prodKey);
					if (dt == null) {
						logger.error("unknown modem product key: {} for modem: {}.", prodKey, a);
					} else {
						m_device =	InsteonDevice.s_makeDevice(dt);
						m_device.setAddress(a);
						m_device.setProductKey(prodKey);
						m_device.setDriver(m_driver);
						m_device.setIsModem(true);
						m_device.addPort(fromPort);
						logger.debug("found modem {} in device_types: {}", a, m_device.toString());
					}
					// can unsubscribe now
					removeListener(this);
				}
			} catch (FieldException e) {
				logger.error("error parsing im info reply field: ", e);
			}
		}
		public void initialize() {
			try {
				Msg m = Msg.s_makeMessage("GetIMInfo");
				writeMessage(m);
			} catch (IOException e) {
				logger.error("modem init failed!", e);
			}
		}
	}
}


File: bundles/binding/org.openhab.binding.insteonplm/src/main/java/org/openhab/binding/insteonplm/internal/message/MsgFactory.java
/**
 * Copyright (c) 2010-2015, openHAB.org and others.
 *
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 */
package org.openhab.binding.insteonplm.internal.message;

import java.io.IOException;

import org.openhab.binding.insteonplm.internal.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
/**
 * This class takes data coming from the serial port and turns it
 * into an message. For that, it has to figure out the length of the 
 * message from the header, and read enough bytes until it hits the
 * message boundary. The code is tricky, partly because the Insteon protocol is.
 * Most of the time the command code (second byte) is enough to determine the length
 * of the incoming message, but sometimes one has to look deeper into the message
 * to determine if it is a standard or extended message (their lengths differ).
 * 
 * @author Bernd Pfrommer
 * @since 1.5.0
 */
public class MsgFactory {
	private static final Logger logger = LoggerFactory.getLogger(MsgFactory.class);
	// no idea what the max msg length could be, but
	// I doubt it'll ever be larger than 4k
	private final static int	MAX_MSG_LEN = 4096;
	private byte[] 				m_buf = new byte[MAX_MSG_LEN];
	private int					m_end = 0;	// offset of end of buffer
	
	/**
	 * Constructor
	 */
	public MsgFactory() {
	}
	
	/**
	 * Adds incoming data to the data buffer. First call addData(), then call processData()
	 * @param data data to be added
	 * @param len length of data to be added
	 */
	public void addData(byte [] data, int len) {
		if (len + m_end > MAX_MSG_LEN) {
			logger.error("warn: truncating excessively long message!");
			len = MAX_MSG_LEN - m_end;
		}
		// append the new data to the one we already have
		System.arraycopy(data, 0, m_buf, m_end, len);
		m_end += len;
		// copy the incoming data to the end of the buffer
		logger.trace("read buffer: len {} data: {}", m_end, Utils.getHexString(m_buf, m_end));
	}
	/**
	 * After data has been added, this method processes it.
	 * processData() needs to be called until it returns null, indicating that no
	 * more messages can be formed from the data buffer.
	 * @return a valid message, or null if the message is not complete
	 * @throws IOException if data was received with unknown command codes
	 */
	public Msg processData() throws IOException {
		// handle the case where we get a pure nack
		if (m_end > 0 && m_buf[0] == 0x15) {
			logger.trace("got pure nack!");
			removeFromBuffer(1);
			try {
				Msg m = Msg.s_makeMessage("PureNACK");
				return m;
			} catch (IOException e) {
				return null;
			}
		}
		// drain the buffer until the first byte is 0x02
		if (m_end > 0 && m_buf[0] != 0x02) {
			logger.error("incoming message does not start with 0x02, searching for start");
			drainBuffer();
			throw new IOException("message does not start with 0x02!");
		}
		// Now see if we have enough data for a complete message.
		// If not, we return null, and expect this method to be called again
		// when more data has come in.
		int msgLen = -1;
		boolean isExtended = false;
		if (m_end > 1) {
			// we have some data, but do we have enough to read the entire header? 
			int headerLength = Msg.s_getHeaderLength(m_buf[1]);
			isExtended = Msg.s_isExtended(m_buf, m_end, headerLength);
			logger.trace("header length expected: {} extended: {}", headerLength, isExtended);
			if (headerLength < 0) {
				String cmdCode = Utils.getHexByte(m_buf[1]);
				logger.debug("got unknown command code {}, draining!", cmdCode);
				// got unknown command code, drain the buffer and wait for more data
				removeFromBuffer(1); // get rid of the leading 0x02
				drainBuffer(); // this will drain until end or it finds the next 0x02
				msgLen = -1; // signal that we don't have a message
				throw new IOException("got unknown command code: " + cmdCode);
			} else if (headerLength >= 2) {
				if (m_end >= headerLength) {
					// only when the header is complete do we know that isExtended is correct!
					msgLen = Msg.s_getMessageLength(m_buf[1], isExtended);
				}
			} else { // should never happen
				logger.error("invalid header length, internal error!");
				msgLen = -1;
			}
		}
		logger.trace("msgLen expected: {}", msgLen);
		Msg msg = null;
		if (msgLen > 0 && m_end >= msgLen) {
			msg = Msg.s_createMessage(m_buf, msgLen, isExtended);
			removeFromBuffer(msgLen);
		}
		logger.trace("keeping buffer len {} data: {}", m_end, Utils.getHexString(m_buf, m_end));
		return msg;
	}
	
	private void drainBuffer() {
		while (m_end > 0 && m_buf[0] != 0x02) {
			removeFromBuffer(1);
		}
	}
	
	private void removeFromBuffer(int len) {
		if (len > m_end) len = m_end;
		System.arraycopy(m_buf, len, m_buf, 0, m_end + 1 - len);
		m_end -= len;
	}
}
