Refactoring Types: ['Extract Method']
Push.java
/*
 * Copyright (c) 2014.
 *
 * BaasBox - info-at-baasbox.com
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

package com.baasbox.configuration;

import org.apache.commons.lang.StringUtils;

import com.baasbox.service.logging.BaasBoxLogger;

import com.baasbox.configuration.index.IndexPushConfiguration;
import com.baasbox.exception.ConfigurationException;
import com.baasbox.service.push.PushNotInitializedException;
import com.baasbox.service.push.PushSwitchException;
import com.baasbox.service.push.providers.GCMServer;
import com.baasbox.util.ConfigurationFileContainer;
import com.fasterxml.jackson.databind.ObjectMapper;


public enum Push implements IProperties	{
	//DEFAULT PROFILE or FIRST
	PROFILE1_PUSH_SANDBOX_ENABLE("profile1.push.sandbox.enable", "The value to verify if BaasBox needs to contact the SANDBOX server or the PRODUCTION server for the first app", Boolean.class),
	PROFILE1_PUSH_APPLE_TIMEOUT("profile1.push.apple.timeout", "The timeout for push notifications on Apple devices for the first app", Integer.class),
	PROFILE1_SANDBOX_ANDROID_API_KEY("profile1.sandbox.android.api.key", "The key to send push notifications to Android devices in SANDBOX mode for the first app", String.class),
	PROFILE1_SANDBOX_IOS_CERTIFICATE("profile1.sandbox.ios.certificate", "The Apple certificate in SANDBOX mode for the first app", ConfigurationFileContainer.class,new IosCertificateHandler()),
	PROFILE1_SANDBOX_IOS_CERTIFICATE_PASSWORD("profile1.sandbox.ios.certificate.password", "The password of the Apple certificate in SANDBOX mode for the first app", String.class),
	PROFILE1_PRODUCTION_ANDROID_API_KEY("profile1.production.android.api.key", "The key to send push notifications to Android devices in PRODUCTION mode for the first app", String.class),
	PROFILE1_PRODUCTION_IOS_CERTIFICATE("profile1.production.ios.certificate", "The Apple certificate in PRODUCTION mode for the first app", ConfigurationFileContainer.class,new IosCertificateHandler()),	
	PROFILE1_PRODUCTION_IOS_CERTIFICATE_PASSWORD("profile1.production.ios.certificate.password", "The password of the Apple certificate in PRODUCTION mode for the first app", String.class),
	PROFILE1_PUSH_PROFILE_ENABLE("profile1.push.profile.enable","Enable this profile",Boolean.class),
	
	//SECOND PROFILE
	PROFILE2_PUSH_SANDBOX_ENABLE("profile2.push.sandbox.enable", "The value to verify if BaasBox needs to contact the SANDBOX server or the PRODUCTION server for the second app", Boolean.class),
	PROFILE2_PUSH_APPLE_TIMEOUT("profile2.push.apple.timeout", "The timeout for push notifications on Apple devices for the second app", Integer.class),
	PROFILE2_SANDBOX_ANDROID_API_KEY("profile2.sandbox.android.api.key", "The key to send push notifications to Android devices in SANDBOX mode for the second app", String.class),
	PROFILE2_SANDBOX_IOS_CERTIFICATE("profile2.sandbox.ios.certificate", "The Apple certificate in SANDBOX mode for the second app", ConfigurationFileContainer.class,new IosCertificateHandler()),
	PROFILE2_SANDBOX_IOS_CERTIFICATE_PASSWORD("profile2.sandbox.ios.certificate.password", "The password of the Apple certificate in SANDBOX mode for the second app", String.class),
	PROFILE2_PRODUCTION_ANDROID_API_KEY("profile2.production.android.api.key", "The key to send push notifications to Android devices in PRODUCTION mode for the second app", String.class),
	PROFILE2_PRODUCTION_IOS_CERTIFICATE("profile2.production.ios.certificate", "The Apple certificate in PRODUCTION mode for the second app", ConfigurationFileContainer.class,new IosCertificateHandler()),	
	PROFILE2_PRODUCTION_IOS_CERTIFICATE_PASSWORD("profile2.production.ios.certificate.password", "The password of the Apple certificate in PRODUCTION mode for the second app", String.class),
	PROFILE2_PUSH_PROFILE_ENABLE("profile2.push.profile.enable","Enable this profile",Boolean.class),

	
	//THIRD PROFILE
	PROFILE3_PUSH_SANDBOX_ENABLE("profile3.push.sandbox.enable", "The value to verify if BaasBox needs to contact the SANDBOX server or the PRODUCTION server for the third app", Boolean.class),
	PROFILE3_PUSH_APPLE_TIMEOUT("profile3.push.apple.timeout", "The timeout for push notifications on Apple devices for the third app", Integer.class),
	PROFILE3_SANDBOX_ANDROID_API_KEY("profile3.sandbox.android.api.key", "The key to send push notifications to Android devices in SANDBOX mode for the third app", String.class),
	PROFILE3_SANDBOX_IOS_CERTIFICATE("profile3.sandbox.ios.certificate", "The Apple certificate in SANDBOX mode for the third app", ConfigurationFileContainer.class,new IosCertificateHandler()),
	PROFILE3_SANDBOX_IOS_CERTIFICATE_PASSWORD("profile3.sandbox.ios.certificate.password", "The password of the Apple certificate in SANDBOX mode for the third app", String.class),
	PROFILE3_PRODUCTION_ANDROID_API_KEY("profile3.production.android.api.key", "The key to send push notifications to Android devices in PRODUCTION mode for the third app", String.class),
	PROFILE3_PRODUCTION_IOS_CERTIFICATE("profile3.production.ios.certificate", "The Apple certificate in PRODUCTION mode for the third app", ConfigurationFileContainer.class,new IosCertificateHandler()),	
	PROFILE3_PRODUCTION_IOS_CERTIFICATE_PASSWORD("profile3.production.ios.certificate.password", "The password of the Apple certificate in PRODUCTION mode for the third app", String.class),
	PROFILE3_PUSH_PROFILE_ENABLE("profile3.push.profile.enable","Enable this profile",Boolean.class);

	
	private final String                 key;
	private final Class<?>               type;
	private String                       description;
	private IPropertyChangeCallback 	 changeCallback = null;

	//override 
	private boolean 					 editable=true;
	private boolean						 visible=true;
	private Object 						 overriddenValue=null;
	private boolean						 overridden=false;
  

	 Push(final String iKey, final String iDescription, final Class<?> iType, 
			final IPropertyChangeCallback iChangeAction) {
		this(iKey, iDescription, iType);
		changeCallback = iChangeAction;
	}

	 Push(final String iKey, final String iDescription, final Class<?> iType) {
		 key = iKey;
		 description = iDescription;
		 type = iType;
	}

	@Override
	public void setValue(Object newValue) throws Exception{
		if (!editable) throw new IllegalStateException("The value cannot be changed");
		//the following tests are necessary due the first db initialization
		if((this.key.equals("profile1.push.profile.enable")) || (this.key.equals("profile2.push.profile.enable")) || (this.key.equals("profile3.push.profile.enable"))) {
			if(this.getValue()==null) {
				_setValue(newValue);
				return;
			}
		}
		if((this.key.equals("profile1.push.sandbox.enable")) || (this.key.equals("profile2.push.sandbox.enable")) || (this.key.equals("profile3.push.sandbox.enable"))) {
			if(this.getValue()==null) {
				_setValue(newValue);
				return;
			}
		}
		if (this.key.contains("api.key")) {
			if(this.getValue()==null) {
				_setValue(newValue);
				return;
			}
			else GCMServer.validateApiKey(newValue.toString());
		}
		boolean bNewValue=false;
		switch  (this) {
			case PROFILE1_PUSH_PROFILE_ENABLE:
				bNewValue = Boolean.parseBoolean(newValue.toString());
				if(bNewValue){
					if(Push.PROFILE1_PUSH_SANDBOX_ENABLE.getValueAsBoolean()){
						if(StringUtils.isEmpty(Push.PROFILE1_SANDBOX_ANDROID_API_KEY.getValueAsString()) 
								&& (Push.PROFILE1_SANDBOX_IOS_CERTIFICATE.getValue()==null
								|| StringUtils.isEmpty(Push.PROFILE1_SANDBOX_IOS_CERTIFICATE_PASSWORD.getValueAsString()))
						   ) throw new PushNotInitializedException("Sandbox configuration not properly initialized for the first (default) profile. Hint: check if both iOS Certificate and iOS password or Android API Key are set");
					}else //production
						if(StringUtils.isEmpty(Push.PROFILE1_PRODUCTION_ANDROID_API_KEY.getValueAsString()) 
								&& (Push.PROFILE1_PRODUCTION_IOS_CERTIFICATE.getValue()==null
								|| StringUtils.isEmpty(Push.PROFILE1_PRODUCTION_IOS_CERTIFICATE_PASSWORD.getValueAsString()))
						   ) throw new PushNotInitializedException("Production configuration not properly initialized for the first (default) profile. Hint: check if both iOS Certificate and iOS password or Android API Key are set");
				}
				break;
			case PROFILE2_PUSH_PROFILE_ENABLE:
				bNewValue = Boolean.parseBoolean(newValue.toString());
				if(bNewValue){
					if(Push.PROFILE2_PUSH_SANDBOX_ENABLE.getValueAsBoolean()){
						if(StringUtils.isEmpty(Push.PROFILE2_SANDBOX_ANDROID_API_KEY.getValueAsString()) 
								&& (Push.PROFILE2_SANDBOX_IOS_CERTIFICATE.getValue()==null
								|| StringUtils.isEmpty(Push.PROFILE2_SANDBOX_IOS_CERTIFICATE_PASSWORD.getValueAsString()))
						   ) throw new PushNotInitializedException("Sandbox configuration not properly initialized for profile 2. Hint: check if both iOS Certificate and iOS password or Android API Key are set");
					}else //production
						if(StringUtils.isEmpty(Push.PROFILE2_PRODUCTION_ANDROID_API_KEY.getValueAsString()) 
								&& (Push.PROFILE2_PRODUCTION_IOS_CERTIFICATE.getValue()==null
								|| StringUtils.isEmpty(Push.PROFILE2_PRODUCTION_IOS_CERTIFICATE_PASSWORD.getValueAsString()))
						   ) throw new PushNotInitializedException("Production configuration not properly initialized for profile 2. Hint: check if both iOS Certificate and iOS password or Android API Key are set");
				}
				break;
			case PROFILE3_PUSH_PROFILE_ENABLE:	
				bNewValue = Boolean.parseBoolean(newValue.toString());
				if(bNewValue){
					if(Push.PROFILE3_PUSH_SANDBOX_ENABLE.getValueAsBoolean()){
						if(StringUtils.isEmpty(Push.PROFILE3_SANDBOX_ANDROID_API_KEY.getValueAsString()) 
								&& (Push.PROFILE3_SANDBOX_IOS_CERTIFICATE.getValue()==null
								|| StringUtils.isEmpty(Push.PROFILE3_SANDBOX_IOS_CERTIFICATE_PASSWORD.getValueAsString()))
						   ) throw new PushNotInitializedException("Sandbox configuration not properly initialized for profile 3. Hint: check if both iOS Certificate and iOS password or Android API Key are set");
					}else //production
						if(StringUtils.isEmpty(Push.PROFILE3_PRODUCTION_ANDROID_API_KEY.getValueAsString()) 
								&& (Push.PROFILE3_PRODUCTION_IOS_CERTIFICATE.getValue()==null
								|| StringUtils.isEmpty(Push.PROFILE3_PRODUCTION_IOS_CERTIFICATE_PASSWORD.getValueAsString()))
						   ) throw new PushNotInitializedException("Production configuration not properly initialized for profile 3. Hint: check if both iOS Certificate and iOS password or Android API Key are set");
				}
				break;
			case PROFILE1_PUSH_SANDBOX_ENABLE:
				if(!(PROFILE1_PUSH_PROFILE_ENABLE.getValueAsBoolean())){
					_setValue(newValue);
					return;
				}
				bNewValue = Boolean.parseBoolean(newValue.toString());
				if(!bNewValue){//switch to production mode
					if(StringUtils.isEmpty(Push.PROFILE1_PRODUCTION_ANDROID_API_KEY.getValueAsString()) 
							&& (Push.PROFILE1_PRODUCTION_IOS_CERTIFICATE.getValue()==null
							|| StringUtils.isEmpty(Push.PROFILE1_PRODUCTION_IOS_CERTIFICATE_PASSWORD.getValueAsString()))
					   ) throw new PushSwitchException("");
				}
				else if(StringUtils.isEmpty(Push.PROFILE1_SANDBOX_ANDROID_API_KEY.getValueAsString()) //switch to sandbox mode
						&& (Push.PROFILE1_SANDBOX_IOS_CERTIFICATE.getValue()==null
						|| StringUtils.isEmpty(Push.PROFILE1_SANDBOX_IOS_CERTIFICATE_PASSWORD.getValueAsString()))
				   ) throw new PushSwitchException("");
				break;
			case PROFILE2_PUSH_SANDBOX_ENABLE:
				if(!(PROFILE2_PUSH_PROFILE_ENABLE.getValueAsBoolean())){
					_setValue(newValue);
					return;
				}
				bNewValue = Boolean.parseBoolean(newValue.toString());
				if(!bNewValue){//switch to production mode
					if(StringUtils.isEmpty(Push.PROFILE2_PRODUCTION_ANDROID_API_KEY.getValueAsString()) 
							&& (Push.PROFILE2_PRODUCTION_IOS_CERTIFICATE.getValue()==null
							|| StringUtils.isEmpty(Push.PROFILE2_PRODUCTION_IOS_CERTIFICATE_PASSWORD.getValueAsString()))
					   ) throw new PushSwitchException("");
				}
				else if(StringUtils.isEmpty(Push.PROFILE2_SANDBOX_ANDROID_API_KEY.getValueAsString()) //switch to sandbox mode
						&& (Push.PROFILE2_SANDBOX_IOS_CERTIFICATE.getValue()==null
						|| StringUtils.isEmpty(Push.PROFILE2_SANDBOX_IOS_CERTIFICATE_PASSWORD.getValueAsString()))
				   ) throw new PushSwitchException("");
				break;
			case PROFILE3_PUSH_SANDBOX_ENABLE:
				if(!(PROFILE3_PUSH_PROFILE_ENABLE.getValueAsBoolean())){
					_setValue(newValue);
					return;
				}				
				bNewValue = Boolean.parseBoolean(newValue.toString());
				if(!bNewValue){//switch to production mode
					if(StringUtils.isEmpty(Push.PROFILE3_PRODUCTION_ANDROID_API_KEY.getValueAsString()) 
							&& (Push.PROFILE3_PRODUCTION_IOS_CERTIFICATE.getValue()==null
							|| StringUtils.isEmpty(Push.PROFILE3_PRODUCTION_IOS_CERTIFICATE_PASSWORD.getValueAsString()))
					   ) throw new PushSwitchException("");
				}
				else if(StringUtils.isEmpty(Push.PROFILE3_SANDBOX_ANDROID_API_KEY.getValueAsString()) //switch to sandbox mode
						&& (Push.PROFILE3_SANDBOX_IOS_CERTIFICATE.getValue()==null
						|| StringUtils.isEmpty(Push.PROFILE3_SANDBOX_IOS_CERTIFICATE_PASSWORD.getValueAsString()))
				   ) throw new PushSwitchException("");
				break;
			
		}
		_setValue(newValue);
	}

	@Override
	public void _setValue(Object newValue) {
		Object parsedValue=null;
		if (BaasBoxLogger.isDebugEnabled()) BaasBoxLogger.debug("Type:"+type+" Setting "+newValue.toString() + "of class: "+newValue.getClass().toString());
		try{
			if (newValue != null)
				if (type == Boolean.class)
					parsedValue = Boolean.parseBoolean(newValue.toString());
				else if (type == Integer.class)
					parsedValue = Integer.parseInt(newValue.toString());
				else if (type == Float.class)
					parsedValue = Float.parseFloat(newValue.toString());
				else if (type == String.class)
					parsedValue = newValue.toString();
				else if (type == ConfigurationFileContainer.class){
					parsedValue = (ConfigurationFileContainer)newValue;
				}
				else
					parsedValue = newValue;
		}catch (Exception e){
			BaasBoxLogger.warn(newValue + " value is invalid for key " + key + "\nNULL will be stored");
		}
		if (changeCallback != null) changeCallback.change(getValue(), newValue);		
		IndexPushConfiguration idx;
		try {

			idx = new IndexPushConfiguration();
			if(type == ConfigurationFileContainer.class && parsedValue!=null){
				ConfigurationFileContainer cfc = (ConfigurationFileContainer)parsedValue;
				ObjectMapper om = new ObjectMapper();
				idx.put(key, om.writeValueAsString(cfc));
			}else{
				idx.put(key, parsedValue);
			}
		} catch (Exception e) {
			BaasBoxLogger.error("Could not store key " + key, e);
			throw new RuntimeException("Could not store key " + key,e);
		}
	}

	@Override
	public Object getValue() {
		if (overridden) return overriddenValue;
		return _getValue();
	}

	@Override
	public Object _getValue() {
		IndexPushConfiguration idx;
		try {

			idx = new IndexPushConfiguration();
			return idx.get(key);
		} catch (Exception e) {
			BaasBoxLogger.error("Could not retrieve key " + key, e);
		}
		return null;
	}

	@Override
	public boolean getValueAsBoolean() {
		Object v = getValue();
		return v instanceof Boolean ? ((Boolean) v).booleanValue() : Boolean.parseBoolean(v.toString());
	}

	@Override
	public String getValueAsString() {
		Object v = getValue();
		return v != null ? v.toString() : null;
	}

	public ConfigurationFileContainer getValueAsFileContainer() {
		Object v = getValue();
		ConfigurationFileContainer result = null;
		if(v!=null){
			ObjectMapper om = new ObjectMapper();
			try {
				result = om.readValue(v.toString(), ConfigurationFileContainer.class);
			} catch (Exception e) {
				e.printStackTrace();
				return result;
			}
		}
		return result;
	}

	@Override
	public int getValueAsInteger() {
		Object v = getValue();
		return (int) (v instanceof Number ? ((Number) v).intValue() : Integer.parseInt(v.toString()));
	}

	@Override
	public long getValueAsLong() {
		Object v = getValue();
		return (long) (v instanceof Number ? ((Number) v).longValue() : Long.parseLong(v.toString()));
	}

	@Override
	public float getValueAsFloat() {
		Object v = getValue();
		return (float) (v instanceof Number ? ((Number) v).floatValue() : Float.parseFloat(v.toString()));
	}

	@Override
	public String getKey() {
		return key;
	}
	

	@Override
	public Class<?> getType() {
		return type;
	}

	@Override
	public String getValueDescription() {
		return description;
	}

	public static String getEnumDescription() {
		return "Configurations for push related properties"; 
	}
	
	@Override
	public void override(Object newValue) {
	    Object parsedValue=null;

	    if (BaasBoxLogger.isDebugEnabled()) BaasBoxLogger.debug("New setting value, key: " + this.key + ", type: "+ this.type + ", new value: " + newValue);
	    if (changeCallback != null) changeCallback.change(getValue(), newValue);	
	    if (newValue != null)
	      if (type == Boolean.class)
	    	  parsedValue = Boolean.parseBoolean(newValue.toString());
	      else if (type == Integer.class)
	    	  parsedValue = Integer.parseInt(newValue.toString());
	      else if (type == Float.class)
	    	  parsedValue = Float.parseFloat(newValue.toString());
	      else if (type == String.class)
	    	  parsedValue = newValue.toString();
	      else
	    	  parsedValue = newValue;
	    this.overriddenValue=parsedValue;
	    this.overridden=true;
	    this.editable=false;
	}

	
	@Override
	public void setEditable(boolean editable) {
		this.editable = editable;
	}

	@Override
	public void setVisible(boolean visible) {
		this.visible = visible;
	}
	
	@Override
	public boolean isOverridden() {
		return overridden;
	}
	
	@Override
	public boolean isVisible() {
		return visible;
	}

	@Override
	public boolean isEditable() {
		return editable;
	}

}


File: app/com/baasbox/db/DbHelper.java
/*
     Copyright 2012-2013 
     Claudio Tesoriero - c.tesoriero-at-baasbox.com

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
 */
package com.baasbox.db;



import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.math.BigInteger;
import java.util.Iterator;
import java.util.List;
import java.util.Set;

import org.apache.commons.codec.binary.Base64;
import org.apache.commons.configuration.ConfigurationException;
import org.apache.commons.configuration.HierarchicalINIConfiguration;
import org.apache.commons.configuration.SubnodeConfiguration;
import org.apache.commons.io.FileUtils;
import org.apache.commons.io.IOUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.exception.ExceptionUtils;

import play.Play;
import play.mvc.Http;

import com.baasbox.BBConfiguration;
import com.baasbox.IBBConfigurationKeys;
import com.baasbox.configuration.Internal;
import com.baasbox.configuration.IosCertificateHandler;
import com.baasbox.configuration.PropertiesConfigurationHelper;
import com.baasbox.dao.RoleDao;
import com.baasbox.dao.UserDao;
import com.baasbox.dao.exception.SqlInjectionException;
import com.baasbox.db.hook.HooksManager;
import com.baasbox.enumerations.DefaultRoles;
import com.baasbox.exception.InvalidAppCodeException;
import com.baasbox.exception.NoTransactionException;
import com.baasbox.exception.RoleAlreadyExistsException;
import com.baasbox.exception.RoleNotFoundException;
import com.baasbox.exception.ShuttingDownDBException;
import com.baasbox.exception.SwitchUserContextException;
import com.baasbox.exception.TransactionIsStillOpenException;
import com.baasbox.exception.UnableToExportDbException;
import com.baasbox.exception.UnableToImportDbException;
import com.baasbox.service.logging.BaasBoxLogger;
import com.baasbox.service.permissions.PermissionTagService;
import com.baasbox.service.user.RoleService;
import com.baasbox.service.user.UserService;
import com.baasbox.util.QueryParams;
import com.eaio.uuid.UUID;
import com.orientechnologies.orient.core.command.OCommandOutputListener;
import com.orientechnologies.orient.core.command.OCommandRequest;
import com.orientechnologies.orient.core.db.ODatabaseRecordThreadLocal;
import com.orientechnologies.orient.core.db.document.ODatabaseDocumentTx;
import com.orientechnologies.orient.core.db.record.ODatabaseRecordTx;
import com.orientechnologies.orient.core.db.tool.ODatabaseExport;
import com.orientechnologies.orient.core.db.tool.ODatabaseImport;
import com.orientechnologies.orient.core.exception.ODatabaseException;
import com.orientechnologies.orient.core.id.ORID;
import com.orientechnologies.orient.core.metadata.security.ORole;
import com.orientechnologies.orient.core.metadata.security.OUser;
import com.orientechnologies.orient.core.record.impl.ODocument;
import com.orientechnologies.orient.core.sql.OCommandSQL;
import com.orientechnologies.orient.core.sql.query.OSQLSynchQuery;
import com.tinkerpop.blueprints.impls.orient.OrientGraph;
import com.tinkerpop.blueprints.impls.orient.OrientGraphNoTx;



public class DbHelper {

	private static final String SCRIPT_FILE_NAME="db.sql";
	private static final String CONFIGURATION_FILE_NAME="configuration.conf";

	private static ThreadLocal<Boolean> dbFreeze = new ThreadLocal<Boolean>() {
		protected Boolean initialValue() {return Boolean.FALSE;};
	};
	private static ThreadLocal<Integer> tranCount = new ThreadLocal<Integer>() {
		protected Integer initialValue() {return 0;};
	};
	
	private static ThreadLocal<String> appcode = new ThreadLocal<String>() {
		protected String initialValue() {return "";};
	};

	private static ThreadLocal<String> username = new ThreadLocal<String>() {
		protected String initialValue() {return "";};
	};
	
	private static ThreadLocal<String> password = new ThreadLocal<String>() {
		protected String initialValue() {return "";};
	};
	
	private static final String fetchPlan = "*:?";

	public static BigInteger getDBTotalSize(){
		return FileUtils.sizeOfDirectoryAsBigInteger(new File (BBConfiguration.getDBDir()));
	}
	
	public static BigInteger getDBStorageFreeSpace(){
		if (BBConfiguration.getDBSizeThreshold()!=BigInteger.ZERO) return BBConfiguration.getDBSizeThreshold();
		return BigInteger.valueOf(new File(BBConfiguration.getDBDir()).getFreeSpace());
	}
	
		
	public static String currentUsername(){
		return username.get();
	}
	
	public static boolean isInTransaction(){
		 ODatabaseRecordTx db = getConnection();
		 return db.getTransaction().isActive();
	}

	public static void requestTransaction(){
		if (BaasBoxLogger.isDebugEnabled()) BaasBoxLogger.debug("Request Transaction: transaction count -before-: " + tranCount.get());
		ODatabaseRecordTx db = getConnection();
		if (!isInTransaction()){
			if (BaasBoxLogger.isTraceEnabled()) BaasBoxLogger.trace("Begin transaction");
			db.begin();
		}
		tranCount.set(tranCount.get().intValue()+1);
		if (BaasBoxLogger.isDebugEnabled()) BaasBoxLogger.debug("Request Transaction: transaction count -after-: " + tranCount.get());
	}

	public static void commitTransaction(){
		if (BaasBoxLogger.isDebugEnabled()) BaasBoxLogger.debug("Commit Transaction: transaction count -before-: " + tranCount.get());
		ODatabaseRecordTx db = getConnection();
		if (isInTransaction()){

			if (BaasBoxLogger.isDebugEnabled()) BaasBoxLogger.debug("Commit transaction");
			tranCount.set(tranCount.get().intValue()-1);
			if (tranCount.get()<0) throw new RuntimeException("Commit without transaction!");
			if (tranCount.get()==0) {
				db.commit();
				db.getTransaction().close();
			}	
		}else throw new NoTransactionException("There is no open transaction to commit");
		if (BaasBoxLogger.isDebugEnabled()) BaasBoxLogger.debug("Commit Transaction: transaction count -after-: " + tranCount.get());

	}

	public static void rollbackTransaction(){
		if (BaasBoxLogger.isDebugEnabled()) BaasBoxLogger.debug("Rollback Transaction: transaction count -before-: " + tranCount.get());
		ODatabaseRecordTx db = getConnection();
		if (isInTransaction()){
			if (BaasBoxLogger.isDebugEnabled()) BaasBoxLogger.debug("Rollback transaction");
			db.getTransaction().rollback();
			db.getTransaction().close();
			tranCount.set(0);
		}
		if (BaasBoxLogger.isDebugEnabled()) BaasBoxLogger.debug("Rollback Transaction: transaction count -after-: " + tranCount.get());
	}

	public static String selectQueryBuilder(String from, boolean count,
			QueryParams criteria) {
		String ret;
		if (count || criteria.justCountTheRecords())
			ret = "select count(*) from ";
		else
			ret = "select " + criteria.getFields() + " from ";
		ret += from;
		if (criteria.getWhere() != null && !criteria.getWhere().equals("")) {
			ret += " where ( " + criteria.getWhere() + " )";
		}
		// patch for issue #469
		if (StringUtils.isEmpty(criteria.getWhere()) && !isConnectedAsAdmin(false)) {
			ret += " where 1=1";
		}
		if (!count && !StringUtils.isEmpty(criteria.getGroupBy())) {
			ret += " group by ( " + criteria.getGroupBy() + " )";
		}
		if (!count && criteria.getOrderBy() != null
				&& !criteria.getOrderBy().equals("")) {
			ret += " order by " + criteria.getOrderBy();
		}
		int skip = 0;
		if (!count && criteria.getPage() != null && criteria.getPage() != -1) {
			skip += (criteria.getPage() * criteria.getRecordPerPage());
		}
		if (!count && (criteria.getSkip() != null)) {
			skip += criteria.getSkip();
		}

		if (!count && skip != 0) {
			ret += " skip " + skip;
		}

		if (!count && criteria.getPage() != null && criteria.getPage() != -1) {
			ret += " limit " + criteria.getRecordPerPage();
		}
		if (BaasBoxLogger.isDebugEnabled())
			BaasBoxLogger.debug("queryBuilder: " + ret);
		return ret;
	}

	/***
	 * Prepares a select statement
	 * @param from the class to query
	 * @param count if true, perform a count instead of to retrieve the records
	 * @param criteria the criteria to apply in the 'where' clause of the select
	 * @return an OCommandRequest object ready to be passed to the {@link #selectCommandExecute(com.orientechnologies.orient.core.command.OCommandRequest, Object[])} (OCommandRequest, String[])} method
	 * @throws SqlInjectionException If the query is not a select statement
	 */
	public static OCommandRequest selectCommandBuilder(String from, boolean count, QueryParams criteria) throws SqlInjectionException{
		ODatabaseRecordTx db =  DbHelper.getConnection();
		OCommandRequest command = db.command(new OSQLSynchQuery<ODocument>(
				selectQueryBuilder(from, count, criteria)
				));
		if (!command.isIdempotent()) throw new SqlInjectionException();
		if (BaasBoxLogger.isDebugEnabled()) BaasBoxLogger.debug("commandBuilder: ");
		if (BaasBoxLogger.isDebugEnabled()) BaasBoxLogger.debug("  " + criteria.toString());
		if (BaasBoxLogger.isDebugEnabled()) BaasBoxLogger.debug("  " + command.toString());
		return command;
	}

	/***
	 * Executes a select eventually passing the parameters 
	 * @param command
	 * @param params positional parameters
	 * @return the List of the record retrieved (the command MUST be a select)
	 */
	public static List<ODocument> selectCommandExecute(OCommandRequest command, Object[] params){
		DbHelper.filterOUserPasswords(true);
		List<ODocument> queryResult = command.execute((Object[])params);
		DbHelper.filterOUserPasswords(false);
		return queryResult;
	}
	public static Integer sqlCommandExecute(OCommandRequest command, Object[] params){
		Integer updateQueryResult = command.execute((Object[])params);
		return updateQueryResult;
	}
	public static List<ODocument> commandExecute(OCommandRequest command, Object[] params){
		DbHelper.filterOUserPasswords(true);
        List<ODocument> queryResult = command.execute((Object[])params);
        DbHelper.filterOUserPasswords(false);
        return queryResult;
	}
	
	/**
	 * Prepares the command API to execute an arbitrary SQL statement
	 * @param theQuery
	 * @return
	 */
	public static OCommandRequest genericSQLStatementCommandBuilder (String theQuery){
		ODatabaseRecordTx db =  DbHelper.getConnection();
		OCommandRequest command = db.command(new OCommandSQL(theQuery));
		return command;
	}
	
	/***
	 * Executes a generic SQL command statements
	 * @param command the command to execute prepared by {@link #genericSQLStatementCommandBuilder(String)}
	 * @param params The positional parameters to pass to the statement
	 * @return
	 */
	public static Object genericSQLCommandExecute(OCommandRequest command, Object[] params){
		Object queryResult = command.execute((Object[])params);
		return queryResult;
	}
	
	/**
	 * Executes an arbitrary sql statement applying the positional parameters
	 * @param statement
	 * @param params
	 * @return
	 */
	public static Object genericSQLStatementExecute(String statement, Object[] params){
		OCommandRequest command = genericSQLStatementCommandBuilder(statement);
		BaasBoxLogger.debug("Command to execute: " + command.toString() );
		Object ret = genericSQLCommandExecute(command,params);
		return ret;
	}
	
	public static void shutdownDB(boolean repopulate){
		ODatabaseRecordTx db = null;

		try{
			//WE GET THE CONNECTION BEFORE SETTING THE SEMAPHORE
			db = getConnection();

			synchronized(DbHelper.class)  {
				if(!dbFreeze.get()){
					dbFreeze.set(true);
				}
				db.drop();
				db.close();
				db.create();
				db.getLevel1Cache().clear();
				db.getLevel2Cache().clear();
				db.reload();
				db.getMetadata().reload();
				if(repopulate){
					HooksManager.registerAll(db);
					setupDb();
				}


			}

		}catch(Throwable e){
			throw new RuntimeException(e);
		}finally{
			synchronized(DbHelper.class)  {

				dbFreeze.set(false);

			}
		}

	}

	public static ODatabaseRecordTx getOrOpenConnection(String appcode, String username,String password) throws InvalidAppCodeException {
		ODatabaseRecordTx db= getConnection();
		if (db==null || db.isClosed()) db = open ( appcode,  username, password) ;
		return db;
	}

	public static ODatabaseRecordTx getOrOpenConnectionWIthHTTPUsername() throws InvalidAppCodeException {
		ODatabaseRecordTx db= getConnection();
		if (db==null || db.isClosed()) db = open (  
				(String) Http.Context.current().args.get("appcode"),  
				getCurrentHTTPUsername(), 
				getCurrentHTTPPassword()) ;
		return db;
	}
	
	public static ODatabaseRecordTx open(String appcode, String username,String password) throws InvalidAppCodeException {
		
		if (appcode==null || !appcode.equals(BBConfiguration.configuration.getString(BBConfiguration.APP_CODE)))
			throw new InvalidAppCodeException("Authentication info not valid or not provided: " + appcode + " is an Invalid App Code");
		if(dbFreeze.get()){
			throw new ShuttingDownDBException();
		}
		String databaseName=BBConfiguration.getDBDir();
		if (BaasBoxLogger.isDebugEnabled()) BaasBoxLogger.debug("opening connection on db: " + databaseName + " for " + username);
		
		ODatabaseDocumentTx conn = new ODatabaseDocumentTx("plocal:" + BBConfiguration.getDBDir());
		conn.open(username,password);
		HooksManager.registerAll(getConnection());
		DbHelper.appcode.set(appcode);
		DbHelper.username.set(username);
		DbHelper.password.set(password);
		
		return getConnection();
	}

    public static boolean isConnectedAsAdmin(boolean excludeInternal){
        OUser user = getConnection().getUser();
        Set<ORole> roles = user.getRoles();
        boolean isAdminRole = roles.contains(RoleDao.getRole(DefaultRoles.ADMIN.toString()));
        return excludeInternal ? isAdminRole && !BBConfiguration.getBaasBoxAdminUsername().equals(user.getName()) : isAdminRole;
    }


	public static ODatabaseRecordTx reconnectAsAdmin (){
		if (tranCount.get()>0) throw new SwitchUserContextException("Cannot switch to admin context within an open transaction");
		DbHelper.close(DbHelper.getConnection());
		try {
			return open (appcode.get(),BBConfiguration.getBaasBoxAdminUsername(),BBConfiguration.getBaasBoxAdminPassword());
		} catch (InvalidAppCodeException e) {
			throw new RuntimeException(e);
		}
	}

	public static ODatabaseRecordTx reconnectAsAuthenticatedUser (){
		if (tranCount.get()>0) throw new SwitchUserContextException("Cannot switch to user context within an open transaction");
		DbHelper.close(DbHelper.getConnection());
		try {
			return open (appcode.get(),getCurrentHTTPUsername(),getCurrentHTTPPassword());
		} catch (InvalidAppCodeException e) {
			throw new RuntimeException(e);
		}
	}
	
	public static void close(ODatabaseRecordTx db) {
		if (BaasBoxLogger.isDebugEnabled()) BaasBoxLogger.debug("closing connection");
		if (db!=null && !db.isClosed()){
			//HooksManager.unregisteredAll(db);
			try{
				if (tranCount.get()!=0) throw new TransactionIsStillOpenException("Closing a connection with an active transaction: " + tranCount.get());
			}finally{
				db.close();
				tranCount.set(0);
			}
		}else if (BaasBoxLogger.isDebugEnabled()) BaasBoxLogger.debug("connection already close or null");
	}

	public static ODatabaseRecordTx getConnection(){
		ODatabaseRecordTx db = null;
		try {
			db=(ODatabaseRecordTx)ODatabaseRecordThreadLocal.INSTANCE.get();
			if (BaasBoxLogger.isDebugEnabled()) BaasBoxLogger.debug("Connection id: " + db + " " + ((Object) db).hashCode());
		}catch (ODatabaseException e){
			BaasBoxLogger.debug("Cound not retrieve the DB connection within this thread: " + ExceptionUtils.getMessage(e));
		}
		return db;
	}

	
	public static String getCurrentHTTPPassword(){
		return (String) Http.Context.current().args.get("password");
	}

	public static String getCurrentHTTPUsername(){
		return (String) Http.Context.current().args.get("username");
	}

	public static String getCurrentUserNameFromConnection(){
		return getConnection().getUser().getName();
	}

	public static boolean isConnectedLikeBaasBox(){
		return getCurrentHTTPUsername().equalsIgnoreCase(BBConfiguration.getBaasBoxUsername());
	}

	public static void createDefaultRoles() throws RoleNotFoundException, RoleAlreadyExistsException{
		if (BaasBoxLogger.isTraceEnabled()) BaasBoxLogger.trace("Method Start");
		RoleService.createInternalRoles();
		if (BaasBoxLogger.isTraceEnabled()) BaasBoxLogger.trace("Method End");
	}

	public static void createDefaultUsers() throws Exception{
		if (BaasBoxLogger.isTraceEnabled()) BaasBoxLogger.trace("Method Start");
		UserService.createDefaultUsers();
		if (BaasBoxLogger.isTraceEnabled()) BaasBoxLogger.trace("Method End");
	}

	
	public static void updateDefaultUsers() throws Exception{
		if (BaasBoxLogger.isTraceEnabled()) BaasBoxLogger.trace("Method Start");
		UserDao udao = UserDao.getInstance();
		OUser user = udao.getOUserByUsername(BBConfiguration.getBaasBoxUsername());
		user.setPassword(BBConfiguration.getBaasBoxPassword());
		user.save();
		user = udao.getOUserByUsername(BBConfiguration.getBaasBoxAdminUsername());
		user.setPassword(BBConfiguration.getBaasBoxAdminPassword());
		user.save();

		if (BaasBoxLogger.isTraceEnabled()) BaasBoxLogger.trace("Method End");
	}


	public static void populateDB() throws IOException{
		ODatabaseRecordTx db = getConnection();
		//DO NOT DELETE THE FOLLOWING LINE!
		OrientGraphNoTx dbg =  new OrientGraphNoTx(getODatabaseDocumentTxConnection()); 
		BaasBoxLogger.info("Populating the db...");
		InputStream is;
		if (Play.application().isProd()) is	=Play.application().resourceAsStream(SCRIPT_FILE_NAME);
		else is = new FileInputStream(Play.application().getFile("conf/"+SCRIPT_FILE_NAME));
		List<String> script=IOUtils.readLines(is, "UTF-8");
		is.close();

		for (String line:script){
			if (BaasBoxLogger.isDebugEnabled()) BaasBoxLogger.debug(line);
			if (!line.startsWith("--") && !line.trim().isEmpty()){ //skip comments
				db.command(new OCommandSQL(line.replace(';', ' '))).execute();
			}
		} 
		Internal.DB_VERSION._setValue(BBConfiguration.configuration.getString(IBBConfigurationKeys.API_VERSION));
		String uniqueId="";
		try{
			UUID u = new UUID();
			uniqueId=new String(Base64.encodeBase64(u.toString().getBytes()));
		}catch (Exception e){
			java.util.UUID u = java.util.UUID.randomUUID();
			uniqueId=new String(Base64.encodeBase64(u.toString().getBytes()));
		}
		Internal.INSTALLATION_ID._setValue(uniqueId);
		BaasBoxLogger.info("Unique installation id is: " + uniqueId);
		BaasBoxLogger.info("...done");
	}

	public static void populateConfiguration () throws IOException, ConfigurationException{
		BaasBoxLogger.info("Load initial configuration...");
		InputStream is;
		if (Play.application().isProd()) is	=Play.application().resourceAsStream(CONFIGURATION_FILE_NAME);
		else is = new FileInputStream(Play.application().getFile("conf/"+CONFIGURATION_FILE_NAME));
		HierarchicalINIConfiguration c = new HierarchicalINIConfiguration();
		c.setEncoding("UTF-8");
		c.load(is);
		CharSequence doubleDot = "..";
		CharSequence dot = ".";

		Set<String> sections= c.getSections();
		for (String section: sections){
			Class en = PropertiesConfigurationHelper.CONFIGURATION_SECTIONS.get(section);
			if (en==null){
				BaasBoxLogger.warn(section  + " is not a valid configuration section, it will be skipped!");
				continue;
			}
			SubnodeConfiguration subConf=c.getSection(section);
			Iterator<String> it = subConf.getKeys();
			while (it.hasNext()){
				String key = (it.next()); 
				Object value =subConf.getString(key);
				key=key.replace(doubleDot, dot);//bug on the Apache library: if the key contain a dot, it will be doubled!
				try {
					BaasBoxLogger.info("Setting "+value+ " to "+key);
					PropertiesConfigurationHelper.setByKey(en, key, value);
				} catch (Exception e) {
					BaasBoxLogger.warn("Error loading initial configuration: Section " + section + ", key: " + key +", value: " + value, e);
				}
			}
		}
		is.close();
		BaasBoxLogger.info("...done");
	}

    static void createDefaultPermissionTags(){
        if (BaasBoxLogger.isTraceEnabled()) BaasBoxLogger.trace("Method Start");
        PermissionTagService.createDefaultPermissions();
        if (BaasBoxLogger.isTraceEnabled()) BaasBoxLogger.trace("Method End");
    }

	public static void setupDb() throws Exception{
		BaasBoxLogger.info("Creating default roles...");
		DbHelper.createDefaultRoles();
		populateDB();
		getConnection().getMetadata().getIndexManager().reload();
		BaasBoxLogger.info("Creating default users...");
		createDefaultUsers();
		populateConfiguration();
        createDefaultPermissionTags();
	}

	public static void exportData(String appcode,OutputStream os) throws UnableToExportDbException{
		ODatabaseRecordTx db = null;
		try{
			db = open(appcode, BBConfiguration.getBaasBoxAdminUsername(), BBConfiguration.getBaasBoxAdminPassword());
			
			ODatabaseExport oe = new ODatabaseExport(db, os, new OCommandOutputListener() {
				@Override
				public void onMessage(String m) {
					BaasBoxLogger.info(m);
				}
			});
			synchronized(DbHelper.class)  {
				if(!dbFreeze.get()){
					dbFreeze.set(true);
				}
			}
			oe.setUseLineFeedForRecords(true);
			oe.setIncludeManualIndexes(true);
			oe.exportDatabase();
			oe.close();
		}catch(Exception ioe){
			throw new UnableToExportDbException(ioe);
		}finally{
			if(db!=null && ! db.isClosed()){
				db.close();
			}
			dbFreeze.set(false);
		}
	}
	
	public static void importData(String appcode,String importData) throws UnableToImportDbException{
		ODatabaseRecordTx db = null;
		java.io.File f = null;
		try{
			BaasBoxLogger.info("Initializing restore operation..:");
			BaasBoxLogger.info("...dropping the old db..:");
			DbHelper.shutdownDB(false);
			f = java.io.File.createTempFile("import", ".json");
			FileUtils.writeStringToFile(f, importData);
			synchronized(DbHelper.class)  {
				if(!dbFreeze.get()){
					dbFreeze.set(true);
				}
			}

			db=getConnection(); 
			BaasBoxLogger.info("...unregistering hooks...");
			HooksManager.unregisteredAll(db);
			BaasBoxLogger.info("...drop the O-Classes...");
			db.getMetadata().getSchema().dropClass("OFunction");
			 db.getMetadata().getSchema().dropClass("OSchedule");
			 db.getMetadata().getSchema().dropClass("ORIDs");
			   ODatabaseDocumentTx dbd = new ODatabaseDocumentTx(db);
			ODatabaseImport oi = new ODatabaseImport(dbd, f.getAbsolutePath(), new OCommandOutputListener() {
				@Override
				public void onMessage(String m) {
					BaasBoxLogger.info("Restore db: " + m);
				}
			});
			
			 oi.setIncludeManualIndexes(true);
			 oi.setUseLineFeedForRecords(true);
			 oi.setPreserveClusterIDs(true);
			 oi.setPreserveRids(true);
			 BaasBoxLogger.info("...starting import procedure...");
			 oi.importDatabase();
			 oi.close();
			
			 BaasBoxLogger.info("...setting up internal user credential...");
			 updateDefaultUsers();
			 BaasBoxLogger.info("...setting up DataBase attributes...");
			 setupAttributes();
			 BaasBoxLogger.info("...registering hooks...");
			 evolveDB(db);
			 HooksManager.registerAll(db);
			 BaasBoxLogger.info("...extract iOS certificates...");
			 IosCertificateHandler.init();
		}catch(Exception ioe){
			BaasBoxLogger.error("*** Error importing the db: ", ioe);
			throw new UnableToImportDbException(ioe);
		}finally{
			if(db!=null && ! db.isClosed()){
				db.close();
			}
			BaasBoxLogger.info("...releasing the db...");
			dbFreeze.set(false);
			if(f!=null && f.exists()){
				f.delete();
			}
			BaasBoxLogger.info("...restore terminated");
		}
	}

	private static void setupAttributes() {
		ODatabaseRecordTx db = DbHelper.getConnection();
		DbHelper.execMultiLineCommands(db,BaasBoxLogger.isDebugEnabled(),
				"alter database DATETIMEFORMAT yyyy-MM-dd'T'HH:mm:ss.sssZ"
				,"alter database custom useLightweightEdges=false"
				,"alter database custom useClassForEdgeLabel=false"
				,"alter database custom useClassForVertexLabel=true"
				,"alter database custom useVertexFieldsForEdgeLabels=true"
  	        );
	}

	/**
	 * Check the db level and evolve it
	 * @param db
	 */
	public static void evolveDB(ODatabaseRecordTx db) {
		//check for evolutions
		 BaasBoxLogger.info("...looking for evolutions...");
		 String fromVersion="";
		 if (db.getMetadata().getIndexManager().getIndex("_bb_internal")!=null){
			 BaasBoxLogger.info("...db is < 0.7 ....");
			 ORID o = (ORID) db.getMetadata().getIndexManager().getIndex("_bb_internal").get(Internal.DB_VERSION.getKey());
			 ODocument od = db.load(o);
			 fromVersion=od.field("value");
		 }else fromVersion=Internal.DB_VERSION.getValueAsString();
		 BaasBoxLogger.info("...db version is: " + fromVersion);
		 if (!fromVersion.equalsIgnoreCase(BBConfiguration.getApiVersion())){
			 BaasBoxLogger.info("...imported DB needs evolutions!...");
			 Evolutions.performEvolutions(db, fromVersion);
			 Internal.DB_VERSION._setValue(BBConfiguration.getApiVersion());
			 BaasBoxLogger.info("DB version is now " + BBConfiguration.getApiVersion());
		 }//end of evolutions
	}
	


	public static OrientGraph getOrientGraphConnection(){
		return new OrientGraph(getODatabaseDocumentTxConnection(),false);
	}


	public static ODatabaseDocumentTx getODatabaseDocumentTxConnection(){
		return new ODatabaseDocumentTx(getConnection());
	}

    /**
     * Executes a sequence of orient sql commands
     */
    public static void execMultiLineCommands(ODatabaseRecordTx db,boolean log,String ... commands){

    		BaasBoxLogger.debug("Ready to execute these commands: " + commands);
        if (commands==null) return;
        for (String command:commands){
            if (command==null){
                BaasBoxLogger.warn("null command found!! skipping");
                continue;
            }
            if (log)BaasBoxLogger.debug("sql:> "+command);
            if (!command.startsWith("--")&&!command.trim().isEmpty()){
            	if (BaasBoxLogger.isDebugEnabled()) BaasBoxLogger.debug("Executing command: " + command);
                db.command(new OCommandSQL(command.replace(';',' '))).execute();
            }
        }
    }
    
    public static void filterOUserPasswords(boolean activate){
    	HooksManager.enableHidePasswordHook(getConnection(), activate);
    }
    
}


File: app/com/baasbox/db/Evolution_0_8_3.java
/*
 * Copyright (c) 2014.
 *
 * BaasBox - info-at-baasbox.com
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

package com.baasbox.db;

import com.baasbox.service.logging.BaasBoxLogger;

import com.orientechnologies.orient.core.db.record.ODatabaseRecordTx;

public class Evolution_0_8_3 implements IEvolution {
	private String version="0.8.3";
	
	public Evolution_0_8_3() {}

	@Override
	public String getFinalVersion() {
		return version;
	}

	@Override
	public void evolve(ODatabaseRecordTx db) {
		BaasBoxLogger.info ("Applying evolutions to evolve to the " + version + " level");
		try{
			setIndexOnUsername(db);
		}catch (Throwable e){
			BaasBoxLogger.error("Error applying evolution to " + version + " level!!" ,e);
			throw new RuntimeException(e);
		}
		BaasBoxLogger.info ("DB now is on " + version + " level");
	}
	
	private void setIndexOnUsername(ODatabaseRecordTx db) {
		BaasBoxLogger.info("..creating index on _bb_user.user.name..:");
      		DbHelper.execMultiLineCommands(db,BaasBoxLogger.isDebugEnabled(),
      	            "create index _bb_user.user.name unique;"
      	        );
		BaasBoxLogger.info("...done...");
	}

    
    
}