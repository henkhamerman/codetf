Refactoring Types: ['Extract Method']
obovm/apple/corebluetooth/CBAdvertisementData.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.corebluetooth;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.dispatch.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CBAdvertisementData.Marshaler.class)
/*<annotations>*/@Library("CoreBluetooth")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CBAdvertisementData/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {
    
    public static class Marshaler {
        @SuppressWarnings("unchecked")
        @MarshalsPointer
        public static CBAdvertisementData toObject(Class<CBAdvertisementData> cls, long handle, long flags) {
            NSDictionary<NSString, NSObject> o = (NSDictionary<NSString, NSObject>) NSObject.Marshaler.toObject(NSDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CBAdvertisementData(o);
        }
        @MarshalsPointer
        public static long toNative(CBAdvertisementData o, long flags) {
            if (o == null) {
                return 0L;
            }
            return NSObject.Marshaler.toNative(o.data, flags);
        }
    }

    /*<ptr>*/
    /*</ptr>*/
    private NSDictionary<NSString, NSObject> data;
    
    protected CBAdvertisementData(NSDictionary<NSString, NSObject> data) {
        this.data = data;
    }
    /*<bind>*/static { Bro.bind(CBAdvertisementData.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public NSDictionary<NSString, NSObject> getDictionary() {
        return data;
    }
    
    
    public String getLocalName() {
        if (data.containsKey(LocalNameKey())) {
            NSString val = (NSString)data.get(LocalNameKey());
            return val.toString();
        }
        return null;
    }
    public double getTxPowerLevel() {
        if (data.containsKey(TxPowerLevelKey())) {
            NSNumber val = (NSNumber)data.get(TxPowerLevelKey());
            return val.doubleValue();
        }
        return 0;
    }
    @SuppressWarnings("unchecked")
    public NSArray<CBUUID> getServiceUUIDs() {
        if (data.containsKey(ServiceUUIDsKey())) {
            NSArray<CBUUID> val = (NSArray<CBUUID>)data.get(ServiceUUIDsKey());
            return val;
        }
        return null;
    }
    @SuppressWarnings("unchecked")
    public NSDictionary<CBUUID, NSData> getServiceData() {
        if (data.containsKey(ServiceDataKey())) {
            NSDictionary<CBUUID, NSData> val = (NSDictionary<CBUUID, NSData>)data.get(ServiceDataKey());
            return val;
        }
        return null;
    }
    public NSData getManufacturerData() {
        if (data.containsKey(ManufacturerDataKey())) {
            NSData val = (NSData)data.get(ManufacturerDataKey());
            return val;
        }
        return null;
    }
    /**
     * @since Available in iOS 6.0 and later.
     */
    @SuppressWarnings("unchecked")
    public NSArray<CBUUID> getOverflowServiceUUIDs() {
        if (data.containsKey(OverflowServiceUUIDsKey())) {
            NSArray<CBUUID> val = (NSArray<CBUUID>)data.get(OverflowServiceUUIDsKey());
            return val;
        }
        return null;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public boolean isConnectable() {
        if (data.containsKey(IsConnectable())) {
            NSNumber val = (NSNumber)data.get(IsConnectable());
            return val.booleanValue();
        }
        return false;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    @SuppressWarnings("unchecked")
    public NSArray<CBUUID> getSolicitedServiceUUIDs() {
        if (data.containsKey(SolicitedServiceUUIDsKey())) {
            NSArray<CBUUID> val = (NSArray<CBUUID>)data.get(SolicitedServiceUUIDsKey());
            return val;
        }
        return null;
    }
    /*<methods>*/
    @GlobalValue(symbol="CBAdvertisementDataLocalNameKey", optional=true)
    protected static native NSString LocalNameKey();
    @GlobalValue(symbol="CBAdvertisementDataTxPowerLevelKey", optional=true)
    protected static native NSString TxPowerLevelKey();
    @GlobalValue(symbol="CBAdvertisementDataServiceUUIDsKey", optional=true)
    protected static native NSString ServiceUUIDsKey();
    @GlobalValue(symbol="CBAdvertisementDataServiceDataKey", optional=true)
    protected static native NSString ServiceDataKey();
    @GlobalValue(symbol="CBAdvertisementDataManufacturerDataKey", optional=true)
    protected static native NSString ManufacturerDataKey();
    /**
     * @since Available in iOS 6.0 and later.
     */
    @GlobalValue(symbol="CBAdvertisementDataOverflowServiceUUIDsKey", optional=true)
    protected static native NSString OverflowServiceUUIDsKey();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="CBAdvertisementDataIsConnectable", optional=true)
    protected static native NSString IsConnectable();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="CBAdvertisementDataSolicitedServiceUUIDsKey", optional=true)
    protected static native NSString SolicitedServiceUUIDsKey();
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/corebluetooth/CBCentralManagerOptions.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.corebluetooth;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.dispatch.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CBCentralManagerOptions.Marshaler.class)
/*<annotations>*/@Library("CoreBluetooth")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CBCentralManagerOptions/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @SuppressWarnings("unchecked")
        @MarshalsPointer
        public static CBCentralManagerOptions toObject(Class<CBCentralManagerOptions> cls, long handle, long flags) {
            NSDictionary<NSString, NSObject> o = (NSDictionary<NSString, NSObject>) NSObject.Marshaler.toObject(NSDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CBCentralManagerOptions(o);
        }
        @MarshalsPointer
        public static long toNative(CBCentralManagerOptions o, long flags) {
            if (o == null) {
                return 0L;
            }
            return NSObject.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private NSDictionary<NSString, NSObject> data;
    
    protected CBCentralManagerOptions(NSDictionary<NSString, NSObject> data) {
        this.data = data;
    }
    public CBCentralManagerOptions() {
    	this.data = new NSMutableDictionary<>();
	}
    /*<bind>*/static { Bro.bind(CBCentralManagerOptions.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public NSDictionary<NSString, NSObject> getDictionary() {
        return data;
    }
    
    
    /**
     * @since Available in iOS 7.0 and later.
     */
    public boolean isShowingPowerAlert() {
        if (data.containsKey(ShowPowerAlertKey())) {
            NSNumber val = (NSNumber)data.get(ShowPowerAlertKey());
            return val.booleanValue();
        }
        return false;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public CBCentralManagerOptions setShowPowerAlert(boolean showAlert) {
        data.put(ShowPowerAlertKey(), NSNumber.valueOf(showAlert));
        return this;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public String getRestoreIdentifier() {
        if (data.containsKey(RestoreIdentifierKey())) {
            NSString val = (NSString)data.get(RestoreIdentifierKey());
            return val.toString();
        }
        return null;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public CBCentralManagerOptions setRestoreIdentifier(String identifier) {
        data.put(RestoreIdentifierKey(), new NSString(identifier));
        return this;
    }
    /*<methods>*/
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="CBCentralManagerOptionShowPowerAlertKey", optional=true)
    protected static native NSString ShowPowerAlertKey();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="CBCentralManagerOptionRestoreIdentifierKey", optional=true)
    protected static native NSString RestoreIdentifierKey();
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/corebluetooth/CBCentralManagerRestoredState.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.corebluetooth;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.dispatch.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CBCentralManagerRestoredState.Marshaler.class)
/*<annotations>*/@Library("CoreBluetooth")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CBCentralManagerRestoredState/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @SuppressWarnings("unchecked")
        @MarshalsPointer
        public static CBCentralManagerRestoredState toObject(Class<CBCentralManagerRestoredState> cls, long handle, long flags) {
            NSDictionary<NSString, NSObject> o = (NSDictionary<NSString, NSObject>) NSObject.Marshaler.toObject(NSDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CBCentralManagerRestoredState(o);
        }
        @MarshalsPointer
        public static long toNative(CBCentralManagerRestoredState o, long flags) {
            if (o == null) {
                return 0L;
            }
            return NSObject.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private NSDictionary<NSString, NSObject> data;
    
    protected CBCentralManagerRestoredState(NSDictionary<NSString, NSObject> data) {
        this.data = data;
    }
    /*<bind>*/static { Bro.bind(CBCentralManagerRestoredState.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public NSDictionary<NSString, NSObject> getDictionary() {
        return data;
    }
    
    
    /**
     * @since Available in iOS 7.0 and later.
     */
    @SuppressWarnings("unchecked")
    public NSArray<CBPeripheral> getPeripherals() {
        if (data.containsKey(PeripheralsKey())) {
            NSArray<CBPeripheral> val = (NSArray<CBPeripheral>)data.get(PeripheralsKey());
            return val;
        }
        return null;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    @SuppressWarnings("unchecked")
    public NSArray<CBUUID> getScanServices() {
        if (data.containsKey(ScanServicesKey())) {
            NSArray<CBUUID> val = (NSArray<CBUUID>)data.get(ScanServicesKey());
            return val;
        }
        return null;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    @SuppressWarnings("unchecked")
    public CBCentralManagerScanOptions getScanOptions() {
        if (data.containsKey(ScanOptionsKey())) {
            NSDictionary<NSString, NSObject> val = (NSDictionary<NSString, NSObject>)data.get(ScanOptionsKey());
            return new CBCentralManagerScanOptions(val);
        }
        return null;
    }
    /*<methods>*/
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="CBCentralManagerRestoredStatePeripheralsKey", optional=true)
    protected static native NSString PeripheralsKey();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="CBCentralManagerRestoredStateScanServicesKey", optional=true)
    protected static native NSString ScanServicesKey();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="CBCentralManagerRestoredStateScanOptionsKey", optional=true)
    protected static native NSString ScanOptionsKey();
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/corebluetooth/CBCentralManagerScanOptions.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.corebluetooth;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.dispatch.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CBCentralManagerScanOptions.Marshaler.class)
/*<annotations>*/@Library("CoreBluetooth")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CBCentralManagerScanOptions/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @SuppressWarnings("unchecked")
        @MarshalsPointer
        public static CBCentralManagerScanOptions toObject(Class<CBCentralManagerScanOptions> cls, long handle, long flags) {
            NSDictionary<NSString, NSObject> o = (NSDictionary<NSString, NSObject>) NSObject.Marshaler.toObject(NSDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CBCentralManagerScanOptions(o);
        }
        @MarshalsPointer
        public static long toNative(CBCentralManagerScanOptions o, long flags) {
            if (o == null) {
                return 0L;
            }
            return NSObject.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private NSDictionary<NSString, NSObject> data;
    
    protected CBCentralManagerScanOptions(NSDictionary<NSString, NSObject> data) {
        this.data = data;
    }
    public CBCentralManagerScanOptions() {
    	this.data = new NSMutableDictionary<>();
    }
    /*<bind>*/static { Bro.bind(CBCentralManagerScanOptions.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public NSDictionary<NSString, NSObject> getDictionary() {
        return data;
    }
    
    public boolean isAllowingDuplicates() {
        if (data.containsKey(AllowDuplicatesKey())) {
            NSNumber val = (NSNumber)data.get(AllowDuplicatesKey());
            return val.booleanValue();
        }
        return false;
    }
    public CBCentralManagerScanOptions setAllowsDuplicates(boolean allowDuplicates) {
        data.put(AllowDuplicatesKey(), NSNumber.valueOf(allowDuplicates));
        return this;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    @SuppressWarnings("unchecked")
    public NSArray<CBUUID> getSolicitedServiceUUIDs() {
        if (data.containsKey(SolicitedServiceUUIDsKey())) {
            NSArray<CBUUID> val = (NSArray<CBUUID>)data.get(SolicitedServiceUUIDsKey());
            return val;
        }
        return null;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public CBCentralManagerScanOptions setSolicitedServiceUUIDs(NSArray<CBUUID> uuids) {
        data.put(SolicitedServiceUUIDsKey(), uuids);
        return this;
    }
    /*<methods>*/
    @GlobalValue(symbol="CBCentralManagerScanOptionAllowDuplicatesKey", optional=true)
    protected static native NSString AllowDuplicatesKey();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="CBCentralManagerScanOptionSolicitedServiceUUIDsKey", optional=true)
    protected static native NSString SolicitedServiceUUIDsKey();
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/corebluetooth/CBConnectPeripheralOptions.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.corebluetooth;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.dispatch.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CBConnectPeripheralOptions.Marshaler.class)
/*<annotations>*/@Library("CoreBluetooth")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CBConnectPeripheralOptions/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @SuppressWarnings("unchecked")
        @MarshalsPointer
        public static CBConnectPeripheralOptions toObject(Class<CBConnectPeripheralOptions> cls, long handle, long flags) {
            NSDictionary<NSString, NSObject> o = (NSDictionary<NSString, NSObject>) NSObject.Marshaler.toObject(NSDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CBConnectPeripheralOptions(o);
        }
        @MarshalsPointer
        public static long toNative(CBConnectPeripheralOptions o, long flags) {
            if (o == null) {
                return 0L;
            }
            return NSObject.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private NSDictionary<NSString, NSObject> data;
    
    protected CBConnectPeripheralOptions(NSDictionary<NSString, NSObject> data) {
        this.data = data;
    }
    public CBConnectPeripheralOptions() {
    	this.data = new NSMutableDictionary<>();
    }
    /*<bind>*/static { Bro.bind(CBConnectPeripheralOptions.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public NSDictionary<NSString, NSObject> getDictionary() {
        return data;
    }
    
    /**
     * @since Available in iOS 6.0 and later.
     */
    public boolean isNotifyingOnConnection() {
        if (data.containsKey(NotifyOnConnectionKey())) {
            NSNumber val = (NSNumber)data.get(NotifyOnConnectionKey());
            return val.booleanValue();
        }
        return false;
    }
    /**
     * @since Available in iOS 6.0 and later.
     */
    public CBConnectPeripheralOptions setNotifyOnConnection(boolean notify) {
        data.put(NotifyOnConnectionKey(), NSNumber.valueOf(notify));
        return this;
    }
    public boolean isNotifyingOnDisconnection() {
        if (data.containsKey(NotifyOnDisconnectionKey())) {
            NSNumber val = (NSNumber)data.get(NotifyOnDisconnectionKey());
            return val.booleanValue();
        }
        return false;
    }
    public CBConnectPeripheralOptions setNotifyOnDisconnection(boolean notify) {
        data.put(NotifyOnDisconnectionKey(), NSNumber.valueOf(notify));
        return this;
    }
    /**
     * @since Available in iOS 6.0 and later.
     */
    public boolean isNotifyingOnNotification() {
        if (data.containsKey(NotifyOnNotificationKey())) {
            NSNumber val = (NSNumber)data.get(NotifyOnNotificationKey());
            return val.booleanValue();
        }
        return false;
    }
    /**
     * @since Available in iOS 6.0 and later.
     */
    public CBConnectPeripheralOptions setNotifyOnNotification(boolean notify) {
        data.put(NotifyOnNotificationKey(), NSNumber.valueOf(notify));
        return this;
    }
    /*<methods>*/
    /**
     * @since Available in iOS 6.0 and later.
     */
    @GlobalValue(symbol="CBConnectPeripheralOptionNotifyOnConnectionKey", optional=true)
    protected static native NSString NotifyOnConnectionKey();
    @GlobalValue(symbol="CBConnectPeripheralOptionNotifyOnDisconnectionKey", optional=true)
    protected static native NSString NotifyOnDisconnectionKey();
    /**
     * @since Available in iOS 6.0 and later.
     */
    @GlobalValue(symbol="CBConnectPeripheralOptionNotifyOnNotificationKey", optional=true)
    protected static native NSString NotifyOnNotificationKey();
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/corebluetooth/CBPeripheralManagerOptions.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.corebluetooth;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.dispatch.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CBPeripheralManagerOptions.Marshaler.class)
/*<annotations>*/@Library("CoreBluetooth")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CBPeripheralManagerOptions/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @SuppressWarnings("unchecked")
        @MarshalsPointer
        public static CBPeripheralManagerOptions toObject(Class<CBPeripheralManagerOptions> cls, long handle, long flags) {
            NSDictionary<NSString, NSObject> o = (NSDictionary<NSString, NSObject>) NSObject.Marshaler.toObject(NSDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CBPeripheralManagerOptions(o);
        }
        @MarshalsPointer
        public static long toNative(CBPeripheralManagerOptions o, long flags) {
            if (o == null) {
                return 0L;
            }
            return NSObject.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private NSDictionary<NSString, NSObject> data;
    
    protected CBPeripheralManagerOptions(NSDictionary<NSString, NSObject> data) {
        this.data = data;
    }
    public CBPeripheralManagerOptions() {
    	this.data = new NSMutableDictionary<>();
    }
    /*<bind>*/static { Bro.bind(CBPeripheralManagerOptions.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public NSDictionary<NSString, NSObject> getDictionary() {
        return data;
    }
    
    
    /**
     * @since Available in iOS 7.0 and later.
     */
    public boolean isShowingPowerAlert() {
        if (data.containsKey(ShowPowerAlertKey())) {
            NSNumber val = (NSNumber)data.get(ShowPowerAlertKey());
            return val.booleanValue();
        }
        return false;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public CBPeripheralManagerOptions setShowPowerAlert(boolean showAlert) {
        data.put(ShowPowerAlertKey(), NSNumber.valueOf(showAlert));
        return this;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public String getRestoreIdentifier() {
        if (data.containsKey(RestoreIdentifierKey())) {
            NSString val = (NSString)data.get(RestoreIdentifierKey());
            return val.toString();
        }
        return null;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public CBPeripheralManagerOptions setRestoreIdentifier(String identifier) {
        data.put(RestoreIdentifierKey(), new NSString(identifier));
        return this;
    }
    /*<methods>*/
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="CBPeripheralManagerOptionShowPowerAlertKey", optional=true)
    protected static native NSString ShowPowerAlertKey();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="CBPeripheralManagerOptionRestoreIdentifierKey", optional=true)
    protected static native NSString RestoreIdentifierKey();
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/corebluetooth/CBPeripheralManagerRestoredState.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.corebluetooth;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.dispatch.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CBPeripheralManagerRestoredState.Marshaler.class)
/*<annotations>*/@Library("CoreBluetooth")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CBPeripheralManagerRestoredState/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @SuppressWarnings("unchecked")
        @MarshalsPointer
        public static CBPeripheralManagerRestoredState toObject(Class<CBPeripheralManagerRestoredState> cls, long handle, long flags) {
            NSDictionary<NSString, NSObject> o = (NSDictionary<NSString, NSObject>) NSObject.Marshaler.toObject(NSDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CBPeripheralManagerRestoredState(o);
        }
        @MarshalsPointer
        public static long toNative(CBPeripheralManagerRestoredState o, long flags) {
            if (o == null) {
                return 0L;
            }
            return NSObject.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private NSDictionary<NSString, NSObject> data;
    
    protected CBPeripheralManagerRestoredState(NSDictionary<NSString, NSObject> data) {
        this.data = data;
    }
    /*<bind>*/static { Bro.bind(CBPeripheralManagerRestoredState.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public NSDictionary<NSString, NSObject> getDictionary() {
        return data;
    }
    
    
    /**
     * @since Available in iOS 7.0 and later.
     */
    @SuppressWarnings("unchecked")
    public NSArray<CBMutableService> getServices() {
        if (data.containsKey(ServicesKey())) {
            NSArray<CBMutableService> val = (NSArray<CBMutableService>)data.get(ServicesKey());
            return val;
        }
        return null;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    @SuppressWarnings("unchecked")
    public CBAdvertisementData getAdvertisementData() {
        if (data.containsKey(AdvertisementDataKey())) {
            NSDictionary<NSString, NSObject> val = (NSDictionary<NSString, NSObject>)data.get(AdvertisementDataKey());
            return new CBAdvertisementData(val);
        }
        return null;
    }
    /*<methods>*/
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="CBPeripheralManagerRestoredStateServicesKey", optional=true)
    protected static native NSString ServicesKey();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="CBPeripheralManagerRestoredStateAdvertisementDataKey", optional=true)
    protected static native NSString AdvertisementDataKey();
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/corebluetooth/CBUUID.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.corebluetooth;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.dispatch.*;
/*</imports>*/

/*<javadoc>*/
/**
 * @since Available in iOS 5.0 and later.
 */
/*</javadoc>*/
/*<annotations>*/@Library("CoreBluetooth") @NativeClass/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CBUUID/*</name>*/ 
    extends /*<extends>*/NSObject/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    /*<ptr>*/public static class CBUUIDPtr extends Ptr<CBUUID, CBUUIDPtr> {}/*</ptr>*/
    /*<bind>*/static { ObjCRuntime.bind(CBUUID.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*/
    public CBUUID() {}
    protected CBUUID(SkipInit skipInit) { super(skipInit); }
    /*</constructors>*/
    /*<properties>*/
    @Property(selector = "data")
    public native NSData getData();
    /**
     * @since Available in iOS 7.1 and later.
     */
    @Property(selector = "UUIDString")
    public native String getUUIDString();
    /*</properties>*/
    /*<members>*//*</members>*/
    public static CBUUID create(CBUUIDIdentifier identifier) {
        return create(identifier.value());
    }
    /*<methods>*/
    @Method(selector = "UUIDWithString:")
    public static native CBUUID create(String theString);
    @Method(selector = "UUIDWithData:")
    public static native CBUUID create(NSData theData);
    @WeaklyLinked
    @Method(selector = "UUIDWithCFUUID:")
    public static native CBUUID create(CFUUID theUUID);
    /**
     * @since Available in iOS 7.0 and later.
     */
    @Method(selector = "UUIDWithNSUUID:")
    public static native CBUUID create(NSUUID theUUID);
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/corebluetooth/CBUUIDIdentifier.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.corebluetooth;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.dispatch.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CBUUIDIdentifier.Marshaler.class)
/*<annotations>*/@Library("CoreBluetooth")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CBUUIDIdentifier/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {
    
    public static class Marshaler {
        @MarshalsPointer
        public static CBUUIDIdentifier toObject(Class<CBUUIDIdentifier> cls, long handle, long flags) {
            NSString o = (NSString) NSObject.Marshaler.toObject(NSString.class, handle, flags);
            if (o == null) {
                return null;
            }
            return CBUUIDIdentifier.valueOf(o.toString());
        }
        @MarshalsPointer
        public static long toNative(CBUUIDIdentifier o, long flags) {
            if (o == null) {
                return 0L;
            }
            return NSObject.Marshaler.toNative(new NSString(o.value()), flags);
        }
    }

    /*<ptr>*/
    /*</ptr>*/
    /*<bind>*/static { Bro.bind(CBUUIDIdentifier.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    public static final CBUUIDIdentifier CharacteristicExtendedProperties = new CBUUIDIdentifier("CharacteristicExtendedPropertiesValue");
    public static final CBUUIDIdentifier CharacteristicUserDescription = new CBUUIDIdentifier("CharacteristicUserDescriptionValue");
    public static final CBUUIDIdentifier ClientCharacteristicConfiguration = new CBUUIDIdentifier("ClientCharacteristicConfigurationValue");
    public static final CBUUIDIdentifier ServerCharacteristicConfiguration = new CBUUIDIdentifier("ServerCharacteristicConfigurationValue");
    public static final CBUUIDIdentifier CharacteristicFormat = new CBUUIDIdentifier("CharacteristicFormatValue");
    public static final CBUUIDIdentifier CharacteristicAggregateFormat = new CBUUIDIdentifier("CharacteristicAggregateFormatValue");
    /**
     * @since Available in iOS 5.0 and later.
     * @deprecated Deprecated in iOS 7.0.
     */
    @Deprecated
    public static final CBUUIDIdentifier GenericAccessProfile = new CBUUIDIdentifier("GenericAccessProfileValue");
    /**
     * @since Available in iOS 5.0 and later.
     * @deprecated Deprecated in iOS 7.0.
     */
    @Deprecated
    public static final CBUUIDIdentifier GenericAttributeProfile = new CBUUIDIdentifier("GenericAttributeProfileValue");
    /**
     * @since Available in iOS 5.0 and later.
     * @deprecated Deprecated in iOS 7.0.
     */
    @Deprecated
    public static final CBUUIDIdentifier DeviceName = new CBUUIDIdentifier("DeviceNameValue");
    /**
     * @since Available in iOS 5.0 and later.
     * @deprecated Deprecated in iOS 7.0.
     */
    @Deprecated
    public static final CBUUIDIdentifier Appearance = new CBUUIDIdentifier("AppearanceValue");
    /**
     * @since Available in iOS 5.0 and later.
     * @deprecated Deprecated in iOS 7.0.
     */
    @Deprecated
    public static final CBUUIDIdentifier PeripheralPrivacyFlag = new CBUUIDIdentifier("PeripheralPrivacyFlagValue");
    /**
     * @since Available in iOS 5.0 and later.
     * @deprecated Deprecated in iOS 7.0.
     */
    @Deprecated
    public static final CBUUIDIdentifier ReconnectionAddress = new CBUUIDIdentifier("ReconnectionAddressValue");
    /**
     * @since Available in iOS 5.0 and later.
     * @deprecated Deprecated in iOS 7.0.
     */
    @Deprecated
    public static final CBUUIDIdentifier PeripheralPreferredConnectionParameters = new CBUUIDIdentifier("PeripheralPreferredConnectionParametersValue");
    /**
     * @since Available in iOS 5.0 and later.
     * @deprecated Deprecated in iOS 7.0.
     */
    @Deprecated
    public static final CBUUIDIdentifier ServiceChanged = new CBUUIDIdentifier("ServiceChangedValue");
    
    private static CBUUIDIdentifier[] values = new CBUUIDIdentifier[] {CharacteristicExtendedProperties, CharacteristicUserDescription, ClientCharacteristicConfiguration, ServerCharacteristicConfiguration, 
        CharacteristicFormat, CharacteristicAggregateFormat, GenericAccessProfile, GenericAttributeProfile, DeviceName, Appearance, PeripheralPrivacyFlag, ReconnectionAddress, PeripheralPreferredConnectionParameters, 
        ServiceChanged};
    private final LazyGlobalValue<String> lazyGlobalValue;
    
    private CBUUIDIdentifier(String getterName) {
        lazyGlobalValue = new LazyGlobalValue<>(getClass(), getterName);
    }
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public String value() {
        return lazyGlobalValue.value();
    }
    
    public static CBUUIDIdentifier valueOf(String value) {
        for (CBUUIDIdentifier v : values) {
            if (v.value().equals(value)) {
                return v;
            }
        }
        throw new IllegalArgumentException("No constant with value " + value + " found in " 
            + /*<name>*/CBUUIDIdentifier/*</name>*/.class.getName());
    }
    /*<methods>*/
    @GlobalValue(symbol="CBUUIDCharacteristicExtendedPropertiesString", optional=true)
    protected static native String CharacteristicExtendedPropertiesValue();
    @GlobalValue(symbol="CBUUIDCharacteristicUserDescriptionString", optional=true)
    protected static native String CharacteristicUserDescriptionValue();
    @GlobalValue(symbol="CBUUIDClientCharacteristicConfigurationString", optional=true)
    protected static native String ClientCharacteristicConfigurationValue();
    @GlobalValue(symbol="CBUUIDServerCharacteristicConfigurationString", optional=true)
    protected static native String ServerCharacteristicConfigurationValue();
    @GlobalValue(symbol="CBUUIDCharacteristicFormatString", optional=true)
    protected static native String CharacteristicFormatValue();
    @GlobalValue(symbol="CBUUIDCharacteristicAggregateFormatString", optional=true)
    protected static native String CharacteristicAggregateFormatValue();
    /**
     * @since Available in iOS 5.0 and later.
     * @deprecated Deprecated in iOS 7.0.
     */
    @Deprecated
    @GlobalValue(symbol="CBUUIDGenericAccessProfileString", optional=true)
    protected static native String GenericAccessProfileValue();
    /**
     * @since Available in iOS 5.0 and later.
     * @deprecated Deprecated in iOS 7.0.
     */
    @Deprecated
    @GlobalValue(symbol="CBUUIDGenericAttributeProfileString", optional=true)
    protected static native String GenericAttributeProfileValue();
    /**
     * @since Available in iOS 5.0 and later.
     * @deprecated Deprecated in iOS 7.0.
     */
    @Deprecated
    @GlobalValue(symbol="CBUUIDDeviceNameString", optional=true)
    protected static native String DeviceNameValue();
    /**
     * @since Available in iOS 5.0 and later.
     * @deprecated Deprecated in iOS 7.0.
     */
    @Deprecated
    @GlobalValue(symbol="CBUUIDAppearanceString", optional=true)
    protected static native String AppearanceValue();
    /**
     * @since Available in iOS 5.0 and later.
     * @deprecated Deprecated in iOS 7.0.
     */
    @Deprecated
    @GlobalValue(symbol="CBUUIDPeripheralPrivacyFlagString", optional=true)
    protected static native String PeripheralPrivacyFlagValue();
    /**
     * @since Available in iOS 5.0 and later.
     * @deprecated Deprecated in iOS 7.0.
     */
    @Deprecated
    @GlobalValue(symbol="CBUUIDReconnectionAddressString", optional=true)
    protected static native String ReconnectionAddressValue();
    /**
     * @since Available in iOS 5.0 and later.
     * @deprecated Deprecated in iOS 7.0.
     */
    @Deprecated
    @GlobalValue(symbol="CBUUIDPeripheralPreferredConnectionParametersString", optional=true)
    protected static native String PeripheralPreferredConnectionParametersValue();
    /**
     * @since Available in iOS 5.0 and later.
     * @deprecated Deprecated in iOS 7.0.
     */
    @Deprecated
    @GlobalValue(symbol="CBUUIDServiceChangedString", optional=true)
    protected static native String ServiceChangedValue();
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImageDestinationCopySourceOptions.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImageDestinationCopySourceOptions.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImageDestinationCopySourceOptions/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {
    
    public static class Marshaler {
        @MarshalsPointer
        public static CGImageDestinationCopySourceOptions toObject(Class<CGImageDestinationCopySourceOptions> cls, long handle, long flags) {
            CFDictionary o = (CFDictionary) CFType.Marshaler.toObject(CFDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CGImageDestinationCopySourceOptions(o);
        }
        @MarshalsPointer
        public static long toNative(CGImageDestinationCopySourceOptions o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.data, flags);
        }
    }

    /*<ptr>*/
    /*</ptr>*/
    private CFDictionary data;
    
    protected CGImageDestinationCopySourceOptions(CFDictionary data) {
        this.data = data;
    }
    public CGImageDestinationCopySourceOptions() {
        this.data = CFMutableDictionary.create();
    }
    /*<bind>*/static { Bro.bind(CGImageDestinationCopySourceOptions.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFDictionary getDictionary() {
        return data;
    }
    
    /**
     * @since Available in iOS 7.0 and later.
     */
    public CGImageMetadata getMetadata() {
        if (data.containsKey(DestinationMetadataKey())) {
            CGImageMetadata val = data.get(DestinationMetadataKey(), CGImageMetadata.class);
            return val;
        }
        return null;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public CGImageDestinationCopySourceOptions setMetadata(CGImageMetadata metadata) {
        data.put(DestinationMetadataKey(), metadata);
        return this;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public boolean isMergingMetadata() {
        if (data.containsKey(DestinationMergeMetadataKey())) {
            CFBoolean val = data.get(DestinationMergeMetadataKey(), CFBoolean.class);
            return val.booleanValue();
        }
        return false;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public CGImageDestinationCopySourceOptions setMergeMetadata(boolean merge) {
        data.put(DestinationMergeMetadataKey(), CFBoolean.valueOf(merge));
        return this;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public boolean shouldExcludeXMP() {
        if (data.containsKey(MetadataShouldExcludeXMPKey())) {
            CFBoolean val = data.get(MetadataShouldExcludeXMPKey(), CFBoolean.class);
            return val.booleanValue();
        }
        return false;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public CGImageDestinationCopySourceOptions setShouldExcludeXMP(boolean exclude) {
        data.put(MetadataShouldExcludeXMPKey(), CFBoolean.valueOf(exclude));
        return this;
    }
    /**
     * @since Available in iOS 8.0 and later.
     */
    public boolean shouldExcludeGPS() {
        if (data.containsKey(MetadataShouldExcludeGPSKey())) {
            CFBoolean val = data.get(MetadataShouldExcludeGPSKey(), CFBoolean.class);
            return val.booleanValue();
        }
        return false;
    }
    /**
     * @since Available in iOS 8.0 and later.
     */
    public CGImageDestinationCopySourceOptions setShouldExcludeGPS(boolean exclude) {
        data.put(MetadataShouldExcludeGPSKey(), CFBoolean.valueOf(exclude));
        return this;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public String getDateTime() {
        if (data.containsKey(DestinationDateTimeKey())) {
            CFString val = data.get(DestinationDateTimeKey(), CFString.class);
            return val.toString();
        }
        return null;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public CGImageDestinationCopySourceOptions setDateTime(String dateTime) {
        data.put(DestinationDateTimeKey(), new CFString(dateTime));
        return this;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public CGImageDestinationCopySourceOptions setDateTime(NSDate dateTime) {
        data.put(DestinationDateTimeKey(), dateTime);
        return this;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public CGImagePropertyOrientation getOrientation() {
        if (data.containsKey(DestinationOrientationKey())) {
            CFNumber val = data.get(DestinationOrientationKey(), CFNumber.class);
            return CGImagePropertyOrientation.valueOf(val.intValue());
        }
        return null;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public CGImageDestinationCopySourceOptions setOrientation(CGImagePropertyOrientation orientation) {
        data.put(DestinationOrientationKey(), CFNumber.valueOf(orientation.value()));
        return this;
    }
    /*<methods>*/
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageDestinationMetadata", optional=true)
    protected static native CFString DestinationMetadataKey();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageDestinationMergeMetadata", optional=true)
    protected static native CFString DestinationMergeMetadataKey();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataShouldExcludeXMP", optional=true)
    protected static native CFString MetadataShouldExcludeXMPKey();
    /**
     * @since Available in iOS 8.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataShouldExcludeGPS", optional=true)
    protected static native CFString MetadataShouldExcludeGPSKey();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageDestinationDateTime", optional=true)
    protected static native CFString DestinationDateTimeKey();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageDestinationOrientation", optional=true)
    protected static native CFString DestinationOrientationKey();
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImageDestinationProperties.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImageDestinationProperties.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImageDestinationProperties/*</name>*/ 
    extends /*<extends>*/CGImageProperties/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImageDestinationProperties toObject(Class<CGImageDestinationProperties> cls, long handle, long flags) {
            CFDictionary o = (CFDictionary) CFType.Marshaler.toObject(CFDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CGImageDestinationProperties(o);
        }
        @MarshalsPointer
        public static long toNative(CGImageDestinationProperties o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    public CGImageDestinationProperties(CFDictionary data) {
        this.data = data;
    }
    public CGImageDestinationProperties() {
        this.data = CFMutableDictionary.create();
    }
    /*<bind>*/static { Bro.bind(CGImageDestinationProperties.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    public double getLossyCompressionQuality() {
        if (data.containsKey(LossyCompressionQualityKey())) {
            CFNumber val = data.get(LossyCompressionQualityKey(), CFNumber.class);
            return val.doubleValue();
        }
        return 1;
    }
    /**
     * @since Available in iOS 4.0 and later.
     */
    public CGImageDestinationProperties setLossyCompressionQuality(double quality) {
        data.put(LossyCompressionQualityKey(), CFNumber.valueOf(quality));
        return this;
    }
    /**
     * @since Available in iOS 4.0 and later.
     */
    public CGColor getBackgroundColor() {
        if (data.containsKey(BackgroundColorKey())) {
            CGColor val = data.get(BackgroundColorKey(), CGColor.class);
            return val;
        }
        return null;
    }
    /**
     * @since Available in iOS 4.0 and later.
     */
    public CGImageDestinationProperties setBackgroundColor(CGColor color) {
        data.put(BackgroundColorKey(), color);
        return this;
    }
    /**
     * @since Available in iOS 8.0 and later.
     */
    public long getMaxPixelSize() {
        if (data.containsKey(ImageMaxPixelSizeKey())) {
            CFNumber val = data.get(ImageMaxPixelSizeKey(), CFNumber.class);
            return val.longValue();
        }
        return 0;
    }
    /**
     * @since Available in iOS 8.0 and later.
     */
    public CGImageDestinationProperties setMaxPixelSize(long size) {
        data.put(ImageMaxPixelSizeKey(), CFNumber.valueOf(size));
        return this;
    }
    /**
     * @since Available in iOS 8.0 and later.
     */
    public boolean isEmbeddingThumbnail() {
        if (data.containsKey(EmbedThumbnailKey())) {
            CFBoolean val = data.get(EmbedThumbnailKey(), CFBoolean.class);
            return val.booleanValue();
        }
        return false;
    }
    /**
     * @since Available in iOS 8.0 and later.
     */
    public CGImageDestinationProperties setEmbedThumbnail(boolean embed) {
        data.put(EmbedThumbnailKey(), CFBoolean.valueOf(embed));
        return this;
    }
    /*<methods>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImageDestinationLossyCompressionQuality", optional=true)
    protected static native CFString LossyCompressionQualityKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImageDestinationBackgroundColor", optional=true)
    protected static native CFString BackgroundColorKey();
    /**
     * @since Available in iOS 8.0 and later.
     */
    @GlobalValue(symbol="kCGImageDestinationImageMaxPixelSize", optional=true)
    protected static native CFString ImageMaxPixelSizeKey();
    /**
     * @since Available in iOS 8.0 and later.
     */
    @GlobalValue(symbol="kCGImageDestinationEmbedThumbnail", optional=true)
    protected static native CFString EmbedThumbnailKey();
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImageMetadataEnumerationOptions.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImageMetadataEnumerationOptions.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImageMetadataEnumerationOptions/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImageMetadataEnumerationOptions toObject(Class<CGImageMetadataEnumerationOptions> cls, long handle, long flags) {
            CFDictionary o = (CFDictionary) CFType.Marshaler.toObject(CFDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CGImageMetadataEnumerationOptions(o);
        }
        @MarshalsPointer
        public static long toNative(CGImageMetadataEnumerationOptions o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private CFDictionary data;
    
    protected CGImageMetadataEnumerationOptions(CFDictionary data) {
        this.data = data;
    }
    public CGImageMetadataEnumerationOptions() {
        this.data = CFMutableDictionary.create();
    }
    /*<bind>*/static { Bro.bind(CGImageMetadataEnumerationOptions.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFDictionary getDictionary() {
        return data;
    }
    
    /**
     * @since Available in iOS 7.0 and later.
     */
    public boolean isEnumeratingRecursively() {
        if (data.containsKey(EnumerateRecursivelyKey())) {
            CFBoolean val = data.get(EnumerateRecursivelyKey(), CFBoolean.class);
            return val.booleanValue();
        }
        return false;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public CGImageMetadataEnumerationOptions setEnumerateRecursively(boolean recursive) {
        data.put(EnumerateRecursivelyKey(), CFBoolean.valueOf(recursive));
        return this;
    }
    /*<methods>*/
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataEnumerateRecursively", optional=true)
    protected static native CFString EnumerateRecursivelyKey();
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImageMetadataNamespace.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImageMetadataNamespace.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImageMetadataNamespace/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImageMetadataNamespace toObject(Class<CGImageMetadataNamespace> cls, long handle, long flags) {
            CFString o = (CFString) CFType.Marshaler.toObject(CFString.class, handle, flags);
            if (o == null) {
                return null;
            }
            return CGImageMetadataNamespace.valueOf(o);
        }
        @MarshalsPointer
        public static long toNative(CGImageMetadataNamespace o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.value(), flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    /*<bind>*/static { Bro.bind(CGImageMetadataNamespace.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImageMetadataNamespace Exif = new CGImageMetadataNamespace("ExifValue");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImageMetadataNamespace ExifAux = new CGImageMetadataNamespace("ExifAuxValue");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImageMetadataNamespace ExifEX = new CGImageMetadataNamespace("ExifEXValue");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImageMetadataNamespace DublinCore = new CGImageMetadataNamespace("DublinCoreValue");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImageMetadataNamespace IPTCCore = new CGImageMetadataNamespace("IPTCCoreValue");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImageMetadataNamespace Photoshop = new CGImageMetadataNamespace("PhotoshopValue");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImageMetadataNamespace TIFF = new CGImageMetadataNamespace("TIFFValue");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImageMetadataNamespace XMPBasic = new CGImageMetadataNamespace("XMPBasicValue");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImageMetadataNamespace XMPRights = new CGImageMetadataNamespace("XMPRightsValue");
    
    private static CGImageMetadataNamespace[] values = new CGImageMetadataNamespace[] {Exif, ExifAux, ExifEX, DublinCore, 
        IPTCCore, Photoshop, TIFF, XMPBasic, XMPRights};
    private final LazyGlobalValue<CFString> lazyGlobalValue;
    
    private CGImageMetadataNamespace(String getterName) {
        lazyGlobalValue = new LazyGlobalValue<>(getClass(), getterName);
    }
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFString value() {
        return lazyGlobalValue.value();
    }
    
    public static CGImageMetadataNamespace valueOf(CFString value) {
        for (CGImageMetadataNamespace v : values) {
            if (v.value().equals(value)) {
                return v;
            }
        }
        throw new IllegalArgumentException("No constant with value " + value + " found in " 
            + /*<name>*/CGImageMetadataNamespace/*</name>*/.class.getName());
    }
    /*<methods>*/
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataNamespaceExif", optional=true)
    protected static native CFString ExifValue();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataNamespaceExifAux", optional=true)
    protected static native CFString ExifAuxValue();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataNamespaceExifEX", optional=true)
    protected static native CFString ExifEXValue();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataNamespaceDublinCore", optional=true)
    protected static native CFString DublinCoreValue();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataNamespaceIPTCCore", optional=true)
    protected static native CFString IPTCCoreValue();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataNamespacePhotoshop", optional=true)
    protected static native CFString PhotoshopValue();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataNamespaceTIFF", optional=true)
    protected static native CFString TIFFValue();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataNamespaceXMPBasic", optional=true)
    protected static native CFString XMPBasicValue();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataNamespaceXMPRights", optional=true)
    protected static native CFString XMPRightsValue();
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImageMetadataPrefix.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImageMetadataPrefix.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImageMetadataPrefix/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {
    
    public static class Marshaler {
        @MarshalsPointer
        public static CGImageMetadataPrefix toObject(Class<CGImageMetadataPrefix> cls, long handle, long flags) {
            CFString o = (CFString) CFType.Marshaler.toObject(CFString.class, handle, flags);
            if (o == null) {
                return null;
            }
            return CGImageMetadataPrefix.valueOf(o);
        }
        @MarshalsPointer
        public static long toNative(CGImageMetadataPrefix o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.value(), flags);
        }
    }

    /*<ptr>*/
    /*</ptr>*/
    /*<bind>*/static { Bro.bind(CGImageMetadataPrefix.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImageMetadataPrefix Exif = new CGImageMetadataPrefix("ExifValue");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImageMetadataPrefix ExifAux = new CGImageMetadataPrefix("ExifAuxValue");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImageMetadataPrefix ExifEX = new CGImageMetadataPrefix("ExifEXValue");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImageMetadataPrefix DublinCore = new CGImageMetadataPrefix("DublinCoreValue");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImageMetadataPrefix IPTCCore = new CGImageMetadataPrefix("IPTCCoreValue");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImageMetadataPrefix Photoshop = new CGImageMetadataPrefix("PhotoshopValue");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImageMetadataPrefix TIFF = new CGImageMetadataPrefix("TIFFValue");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImageMetadataPrefix XMPBasic = new CGImageMetadataPrefix("XMPBasicValue");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImageMetadataPrefix XMPRights = new CGImageMetadataPrefix("XMPRightsValue");
    
    private static CGImageMetadataPrefix[] values = new CGImageMetadataPrefix[] {Exif, ExifAux, ExifEX, DublinCore, 
        IPTCCore, Photoshop, TIFF, XMPBasic, XMPRights};
    private final LazyGlobalValue<CFString> lazyGlobalValue;
    
    private CGImageMetadataPrefix(String getterName) {
        lazyGlobalValue = new LazyGlobalValue<>(getClass(), getterName);
    }
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFString value() {
        return lazyGlobalValue.value();
    }
    
    public static CGImageMetadataPrefix valueOf(CFString value) {
        for (CGImageMetadataPrefix v : values) {
            if (v.value().equals(value)) {
                return v;
            }
        }
        throw new IllegalArgumentException("No constant with value " + value + " found in " 
            + /*<name>*/CGImageMetadataPrefix/*</name>*/.class.getName());
    }
    /*<methods>*/
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataPrefixExif", optional=true)
    protected static native CFString ExifValue();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataPrefixExifAux", optional=true)
    protected static native CFString ExifAuxValue();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataPrefixExifEX", optional=true)
    protected static native CFString ExifEXValue();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataPrefixDublinCore", optional=true)
    protected static native CFString DublinCoreValue();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataPrefixIPTCCore", optional=true)
    protected static native CFString IPTCCoreValue();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataPrefixPhotoshop", optional=true)
    protected static native CFString PhotoshopValue();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataPrefixTIFF", optional=true)
    protected static native CFString TIFFValue();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataPrefixXMPBasic", optional=true)
    protected static native CFString XMPBasicValue();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageMetadataPrefixXMPRights", optional=true)
    protected static native CFString XMPRightsValue();
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImageProperties.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
/**
 * @since Available in iOS 4.0 and later.
 */
@Marshaler(CGImageProperties.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImageProperties/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {
    
    public static class Marshaler {
        @MarshalsPointer
        public static CGImageProperties toObject(Class<CGImageProperties> cls, long handle, long flags) {
            CFDictionary o = (CFDictionary) CFType.Marshaler.toObject(CFDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CGImageProperties(o);
        }
        @MarshalsPointer
        public static long toNative(CGImageProperties o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.data, flags);
        }
    }

    /*<ptr>*/
    /*</ptr>*/
    protected CFDictionary data;
    
    public CGImageProperties(CFDictionary data) {
        this.data = data;
    }
    public CGImageProperties() {
        this.data = CFMutableDictionary.create();
    }
    /*<bind>*/static { Bro.bind(CGImageProperties.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFDictionary getDictionary() {
        return data;
    }
    
    
    public CGImagePropertyTIFFData getTIFFData() {
        if (data.containsKey(TIFFDictionaryKey())) {
            CFDictionary val = data.get(TIFFDictionaryKey(), CFDictionary.class);
            return new CGImagePropertyTIFFData(val);
        }
        return null;
    }
    public CGImageProperties setTIFFData(CGImagePropertyTIFFData metadata) {
        data.put(TIFFDictionaryKey(), metadata.getDictionary());
        return this;
    }
    public CGImagePropertyGIFData getGIFData() {
        if (data.containsKey(GIFDictionaryKey())) {
            CFDictionary val = data.get(GIFDictionaryKey(), CFDictionary.class);
            return new CGImagePropertyGIFData(val);
        }
        return null;
    }
    public CGImageProperties setGIFData(CGImagePropertyGIFData metadata) {
        data.put(GIFDictionaryKey(), metadata.getDictionary());
        return this;
    }
    public CGImagePropertyJFIFData getJFIFData() {
        if (data.containsKey(JFIFDictionaryKey())) {
            CFDictionary val = data.get(JFIFDictionaryKey(), CFDictionary.class);
            return new CGImagePropertyJFIFData(val);
        }
        return null;
    }
    public CGImageProperties setJFIFData(CGImagePropertyJFIFData metadata) {
        data.put(JFIFDictionaryKey(), metadata.getDictionary());
        return this;
    }
    public CGImagePropertyExifData getExifData() {
        if (data.containsKey(ExifDictionaryKey())) {
            CFDictionary val = data.get(ExifDictionaryKey(), CFDictionary.class);
            return new CGImagePropertyExifData(val);
        }
        return null;
    }
    public CGImageProperties setExifData(CGImagePropertyExifData metadata) {
        data.put(ExifDictionaryKey(), metadata.getDictionary());
        return this;
    }
    public CGImagePropertyPNGData getPNGData() {
        if (data.containsKey(PNGDictionaryKey())) {
            CFDictionary val = data.get(PNGDictionaryKey(), CFDictionary.class);
            return new CGImagePropertyPNGData(val);
        }
        return null;
    }
    public CGImageProperties setPNGData(CGImagePropertyPNGData metadata) {
        data.put(PNGDictionaryKey(), metadata.getDictionary());
        return this;
    }
    public CGImagePropertyIPTCData getIPTCData() {
        if (data.containsKey(IPTCDictionaryKey())) {
            CFDictionary val = data.get(IPTCDictionaryKey(), CFDictionary.class);
            return new CGImagePropertyIPTCData(val);
        }
        return null;
    }
    public CGImageProperties setIPTCData(CGImagePropertyIPTCData metadata) {
        data.put(PNGDictionaryKey(), metadata.getDictionary());
        return this;
    }
    public CGImagePropertyGPSData getGPSData() {
        if (data.containsKey(GPSDictionaryKey())) {
            CFDictionary val = data.get(GPSDictionaryKey(), CFDictionary.class);
            return new CGImagePropertyGPSData(val);
        }
        return null;
    }
    public CGImageProperties setGPSData(CGImagePropertyGPSData metadata) {
        data.put(GPSDictionaryKey(), metadata.getDictionary());
        return this;
    }
    public CFDictionary getRawData() {
        if (data.containsKey(RawDictionaryKey())) {
            CFDictionary val = data.get(RawDictionaryKey(), CFDictionary.class);
            return val;
        }
        return null;
    }
    public CGImageProperties setRawData(CFDictionary metadata) {
        data.put(RawDictionaryKey(), metadata);
        return this;
    }
    public CGImagePropertyCIFFData getCIFFData() {
        if (data.containsKey(CIFFDictionaryKey())) {
            CFDictionary val = data.get(CIFFDictionaryKey(), CFDictionary.class);
            return new CGImagePropertyCIFFData(val);
        }
        return null;
    }
    public CGImageProperties setCIFFData(CGImagePropertyCIFFData metadata) {
        data.put(CIFFDictionaryKey(), metadata.getDictionary());
        return this;
    }
    public CGImageProperty8BIMData get8BIMData() {
        if (data.containsKey(_8BIMDictionaryKey())) {
            CFDictionary val = data.get(_8BIMDictionaryKey(), CFDictionary.class);
            return new CGImageProperty8BIMData(val);
        }
        return null;
    }
    public CGImageProperties set8BIMData(CGImageProperty8BIMData metadata) {
        data.put(_8BIMDictionaryKey(), metadata.getDictionary());
        return this;
    }
    public CGImagePropertyDNGData getDNGData() {
        if (data.containsKey(DNGDictionaryKey())) {
            CFDictionary val = data.get(DNGDictionaryKey(), CFDictionary.class);
            return new CGImagePropertyDNGData(val);
        }
        return null;
    }
    public CGImageProperties setDNGData(CGImagePropertyDNGData metadata) {
        data.put(DNGDictionaryKey(), metadata.getDictionary());
        return this;
    }
    public CGImagePropertyExifAuxData getExifAuxData() {
        if (data.containsKey(ExifAuxDictionaryKey())) {
            CFDictionary val = data.get(ExifAuxDictionaryKey(), CFDictionary.class);
            return new CGImagePropertyExifAuxData(val);
        }
        return null;
    }
    public CGImageProperties setExifAuxData(CGImagePropertyExifAuxData metadata) {
        data.put(ExifAuxDictionaryKey(), metadata.getDictionary());
        return this;
    }
    public CGImagePropertyCanonData getMakerCanonData() {
        if (data.containsKey(MakerCanonDictionaryKey())) {
            CFDictionary val = data.get(MakerCanonDictionaryKey(), CFDictionary.class);
            return new CGImagePropertyCanonData(val);
        }
        return null;
    }
    public CGImageProperties setMakerCanonData(CGImagePropertyCanonData metadata) {
        data.put(MakerCanonDictionaryKey(), metadata.getDictionary());
        return this;
    }
    public CGImagePropertyNikonData getMakerNikonData() {
        if (data.containsKey(MakerNikonDictionaryKey())) {
            CFDictionary val = data.get(MakerNikonDictionaryKey(), CFDictionary.class);
            return new CGImagePropertyNikonData(val);
        }
        return null;
    }
    public CGImageProperties setMakerNikonData(CGImagePropertyNikonData metadata) {
        data.put(MakerNikonDictionaryKey(), metadata.getDictionary());
        return this;
    }
    public CFDictionary getMakerMinoltaData() {
        if (data.containsKey(MakerMinoltaDictionaryKey())) {
            CFDictionary val = data.get(MakerMinoltaDictionaryKey(), CFDictionary.class);
            return val;
        }
        return null;
    }
    public CGImageProperties setMakerMinoltaData(CFDictionary metadata) {
        data.put(MakerMinoltaDictionaryKey(), metadata);
        return this;
    }
    public CFDictionary getMakerFujiData() {
        if (data.containsKey(MakerFujiDictionaryKey())) {
            CFDictionary val = data.get(MakerFujiDictionaryKey(), CFDictionary.class);
            return val;
        }
        return null;
    }
    public CGImageProperties setMakerFujiData(CFDictionary metadata) {
        data.put(MakerFujiDictionaryKey(), metadata);
        return this;
    }
    public CFDictionary getMakerOlympusData() {
        if (data.containsKey(MakerOlympusDictionaryKey())) {
            CFDictionary val = data.get(MakerOlympusDictionaryKey(), CFDictionary.class);
            return val;
        }
        return null;
    }
    public CGImageProperties setMakerOlympusData(CFDictionary metadata) {
        data.put(MakerOlympusDictionaryKey(), metadata);
        return this;
    }
    public CFDictionary getMakerPentaxData() {
        if (data.containsKey(MakerPentaxDictionaryKey())) {
            CFDictionary val = data.get(MakerPentaxDictionaryKey(), CFDictionary.class);
            return val;
        }
        return null;
    }
    public CGImageProperties setMakerPentaxData(CFDictionary metadata) {
        data.put(MakerPentaxDictionaryKey(), metadata);
        return this;
    }
    
    public long getFileSize() {
        if (data.containsKey(FileSizeKey())) {
            CFNumber val = data.get(FileSizeKey(), CFNumber.class);
            return val.longValue();
        }
        return 0;
    }
    public CGImageProperties setFileSize(long fileSize) {
        data.put(FileSizeKey(), CFNumber.valueOf(fileSize));
        return this;
    }
    
    public long getDPIHeight() {
        if (data.containsKey(DPIHeightKey())) {
            CFNumber val = data.get(DPIHeightKey(), CFNumber.class);
            return val.longValue();
        }
        return 0;
    }
    public CGImageProperties setDPIHeight(long dpi) {
        data.put(DPIHeightKey(), CFNumber.valueOf(dpi));
        return this;
    }
    public long getDPIWidth() {
        if (data.containsKey(DPIWidthKey())) {
            CFNumber val = data.get(DPIWidthKey(), CFNumber.class);
            return val.longValue();
        }
        return 0;
    }
    public CGImageProperties setDPIWidth(long dpi) {
        data.put(DPIWidthKey(), CFNumber.valueOf(dpi));
        return this;
    }
    public long getPixelWidth() {
        if (data.containsKey(PixelWidthKey())) {
            CFNumber val = data.get(PixelWidthKey(), CFNumber.class);
            return val.longValue();
        }
        return 0;
    }
    public CGImageProperties setPixelWidth(long width) {
        data.put(PixelWidthKey(), CFNumber.valueOf(width));
        return this;
    }
    public long getPixelHeight() {
        if (data.containsKey(PixelHeightKey())) {
            CFNumber val = data.get(PixelHeightKey(), CFNumber.class);
            return val.longValue();
        }
        return 0;
    }
    public CGImageProperties setPixelHeight(long height) {
        data.put(PixelHeightKey(), CFNumber.valueOf(height));
        return this;
    }
    public int getDepth() {
        if (data.containsKey(DepthKey())) {
            CFNumber val = data.get(DepthKey(), CFNumber.class);
            return val.intValue();
        }
        return 0;
    }
    public CGImageProperties setDepth(int depth) {
        data.put(DepthKey(), CFNumber.valueOf(depth));
        return this;
    }
    public CGImagePropertyOrientation getOrientation() {
        if (data.containsKey(OrientationKey())) {
            CFNumber val = data.get(OrientationKey(), CFNumber.class);
            return CGImagePropertyOrientation.valueOf(val.longValue());
        }
        return null;
    }
    public CGImageProperties setOrientation(CGImagePropertyOrientation orientation) {
        data.put(OrientationKey(), CFNumber.valueOf(orientation.value()));
        return this;
    }
    public boolean isContainingFloatingPointPixels() {
        if (data.containsKey(IsFloatKey())) {
            CFBoolean val = data.get(IsFloatKey(), CFBoolean.class);
            return val.booleanValue();
        }
        return false;
    }
    public CGImageProperties setContainsFloatingPointPixels(boolean isFloat) {
        data.put(IsFloatKey(), CFBoolean.valueOf(isFloat));
        return this;
    }
    public boolean isIndexed() {
        if (data.containsKey(IsIndexedKey())) {
            CFBoolean val = data.get(IsIndexedKey(), CFBoolean.class);
            return val.booleanValue();
        }
        return false;
    }
    public CGImageProperties setIndexed(boolean isIndexed) {
        data.put(IsIndexedKey(), CFBoolean.valueOf(isIndexed));
        return this;
    }
    public boolean hasAlphaChannel() {
        if (data.containsKey(HasAlphaKey())) {
            CFBoolean val = data.get(HasAlphaKey(), CFBoolean.class);
            return val.booleanValue();
        }
        return false;
    }
    public CGImageProperties setHasAlphaChannel(boolean alphaChannel) {
        data.put(HasAlphaKey(), CFBoolean.valueOf(alphaChannel));
        return this;
    }
    public CGImagePropertyColorModel getColorModel() {
        if (data.containsKey(ColorModelKey())) {
            CFString val = data.get(ColorModelKey(), CFString.class);
            return CGImagePropertyColorModel.valueOf(val);
        }
        return null;
    }
    public CGImageProperties setColorModel(CGImagePropertyColorModel colorModel) {
        data.put(ColorModelKey(), colorModel.value());
        return this;
    }
    public String getICCProfile() {
        if (data.containsKey(ProfileNameKey())) {
            CFString val = data.get(ProfileNameKey(), CFString.class);
            return val.toString();
        }
        return null;
    }
    public CGImageProperties setICCProfile(String profile) {
        data.put(ProfileNameKey(), new CFString(profile));
        return this;
    }
    /*<methods>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyTIFFDictionary", optional=true)
    protected static native CFString TIFFDictionaryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGIFDictionary", optional=true)
    protected static native CFString GIFDictionaryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyJFIFDictionary", optional=true)
    protected static native CFString JFIFDictionaryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifDictionary", optional=true)
    protected static native CFString ExifDictionaryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyPNGDictionary", optional=true)
    protected static native CFString PNGDictionaryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCDictionary", optional=true)
    protected static native CFString IPTCDictionaryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSDictionary", optional=true)
    protected static native CFString GPSDictionaryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyRawDictionary", optional=true)
    protected static native CFString RawDictionaryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFDictionary", optional=true)
    protected static native CFString CIFFDictionaryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerCanonDictionary", optional=true)
    protected static native CFString MakerCanonDictionaryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerNikonDictionary", optional=true)
    protected static native CFString MakerNikonDictionaryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerMinoltaDictionary", optional=true)
    protected static native CFString MakerMinoltaDictionaryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerFujiDictionary", optional=true)
    protected static native CFString MakerFujiDictionaryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerOlympusDictionary", optional=true)
    protected static native CFString MakerOlympusDictionaryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerPentaxDictionary", optional=true)
    protected static native CFString MakerPentaxDictionaryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImageProperty8BIMDictionary", optional=true)
    protected static native CFString _8BIMDictionaryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyDNGDictionary", optional=true)
    protected static native CFString DNGDictionaryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifAuxDictionary", optional=true)
    protected static native CFString ExifAuxDictionaryKey();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerAppleDictionary", optional=true)
    protected static native CFString MakerAppleDictionaryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyFileSize", optional=true)
    protected static native CFString FileSizeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyPixelHeight", optional=true)
    protected static native CFString PixelHeightKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyPixelWidth", optional=true)
    protected static native CFString PixelWidthKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyDPIHeight", optional=true)
    protected static native CFString DPIHeightKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyDPIWidth", optional=true)
    protected static native CFString DPIWidthKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyDepth", optional=true)
    protected static native CFString DepthKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyOrientation", optional=true)
    protected static native CFString OrientationKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIsFloat", optional=true)
    protected static native CFString IsFloatKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIsIndexed", optional=true)
    protected static native CFString IsIndexedKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyHasAlpha", optional=true)
    protected static native CFString HasAlphaKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyColorModel", optional=true)
    protected static native CFString ColorModelKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyProfileName", optional=true)
    protected static native CFString ProfileNameKey();
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImageProperty8BIM.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImageProperty8BIM.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImageProperty8BIM/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImageProperty8BIM toObject(Class<CGImageProperty8BIM> cls, long handle, long flags) {
            CFString o = (CFString) CFType.Marshaler.toObject(CFString.class, handle, flags);
            if (o == null) {
                return null;
            }
            return CGImageProperty8BIM.valueOf(o);
        }
        @MarshalsPointer
        public static long toNative(CGImageProperty8BIM o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.value(), flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    /*<bind>*/static { Bro.bind(CGImageProperty8BIM.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImageProperty8BIM LayerNames = new CGImageProperty8BIM("LayerNamesKey");
    /**
     * @since Available in iOS 8.0 and later.
     */
    public static final CGImageProperty8BIM Version = new CGImageProperty8BIM("VersionKey");
    
    private static CGImageProperty8BIM[] values = new CGImageProperty8BIM[] {LayerNames, Version};
    private final LazyGlobalValue<CFString> lazyGlobalValue;
    
    private CGImageProperty8BIM(String getterName) {
        lazyGlobalValue = new LazyGlobalValue<>(getClass(), getterName);
    }
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFString value() {
        return lazyGlobalValue.value();
    }
    
    public static CGImageProperty8BIM valueOf(CFString value) {
        for (CGImageProperty8BIM v : values) {
            if (v.value().equals(value)) {
                return v;
            }
        }
        throw new IllegalArgumentException("No constant with value " + value + " found in " 
            + /*<name>*/CGImageProperty8BIM/*</name>*/.class.getName());
    }
    /*<methods>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImageProperty8BIMLayerNames", optional=true)
    protected static native CFString LayerNamesKey();
    /**
     * @since Available in iOS 8.0 and later.
     */
    @GlobalValue(symbol="kCGImageProperty8BIMVersion", optional=true)
    protected static native CFString VersionKey();
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImageProperty8BIMData.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;

import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImageProperty8BIMData.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class CGImageProperty8BIMData 
    extends /*<extends>*/Object/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImageProperty8BIMData toObject(Class<CGImageProperty8BIMData> cls, long handle, long flags) {
            CFDictionary o = (CFDictionary) CFType.Marshaler.toObject(CFDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CGImageProperty8BIMData(o);
        }
        @MarshalsPointer
        public static long toNative(CGImageProperty8BIMData o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private CFDictionary data;
    
    protected CGImageProperty8BIMData(CFDictionary data) {
        this.data = data;
    }
    public CGImageProperty8BIMData() {
        this.data = CFMutableDictionary.create();
    }
    /*<bind>*/static { Bro.bind(CGImageProperty8BIMData.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFDictionary getDictionary() {
        return data;
    }
    
    public boolean has(CGImageProperty8BIM property) {
        return data.containsKey(property.value());
    }
    
    public String getString(CGImageProperty8BIM property) {
        if (has(property)) {
            CFString val = data.get(property.value(), CFString.class);
            return val.toString();
        }
        return null;
    }
    public double getNumber(CGImageProperty8BIM property) {
        if (has(property)) {
            CFNumber val = data.get(property.value(), CFNumber.class);
            return val.doubleValue();
        }
        return 0;
    }
    public CGImageProperty8BIMData set(CGImageProperty8BIM property, String value) {
        data.put(property.value(), new CFString(value));
        return this;
    }
    public CGImageProperty8BIMData set(CGImageProperty8BIM property, double value) {
        data.put(property.value(), CFNumber.valueOf(value));
        return this;
    }
    /*<methods>*/
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyCIFF.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyCIFF.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImagePropertyCIFF/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyCIFF toObject(Class<CGImagePropertyCIFF> cls, long handle, long flags) {
            CFString o = (CFString) CFType.Marshaler.toObject(CFString.class, handle, flags);
            if (o == null) {
                return null;
            }
            return CGImagePropertyCIFF.valueOf(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyCIFF o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.value(), flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    /*<bind>*/static { Bro.bind(CGImagePropertyCIFF.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF Description = new CGImagePropertyCIFF("DescriptionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF Firmware = new CGImagePropertyCIFF("FirmwareKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF OwnerName = new CGImagePropertyCIFF("OwnerNameKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF ImageName = new CGImagePropertyCIFF("ImageNameKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF ImageFileName = new CGImagePropertyCIFF("ImageFileNameKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF ReleaseMethod = new CGImagePropertyCIFF("ReleaseMethodKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF ReleaseTiming = new CGImagePropertyCIFF("ReleaseTimingKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF RecordID = new CGImagePropertyCIFF("RecordIDKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF SelfTimingTime = new CGImagePropertyCIFF("SelfTimingTimeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF CameraSerialNumber = new CGImagePropertyCIFF("CameraSerialNumberKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF ImageSerialNumber = new CGImagePropertyCIFF("ImageSerialNumberKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF ContinuousDrive = new CGImagePropertyCIFF("ContinuousDriveKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF FocusMode = new CGImagePropertyCIFF("FocusModeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF MeteringMode = new CGImagePropertyCIFF("MeteringModeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF ShootingMode = new CGImagePropertyCIFF("ShootingModeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF LensModel = new CGImagePropertyCIFF("LensModelKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF LensMaxMM = new CGImagePropertyCIFF("LensMaxMMKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF LensMinMM = new CGImagePropertyCIFF("LensMinMMKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF WhiteBalanceIndex = new CGImagePropertyCIFF("WhiteBalanceIndexKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF FlashExposureComp = new CGImagePropertyCIFF("FlashExposureCompKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCIFF MeasuredEV = new CGImagePropertyCIFF("MeasuredEVKey");
    
    private static CGImagePropertyCIFF[] values = new CGImagePropertyCIFF[] {Description, Firmware, OwnerName, ImageName, 
        ImageFileName, ReleaseMethod, ReleaseTiming, RecordID, SelfTimingTime, CameraSerialNumber, ImageSerialNumber, 
        ContinuousDrive, FocusMode, MeteringMode, ShootingMode, LensModel, LensMaxMM, LensMinMM, WhiteBalanceIndex, 
        FlashExposureComp, MeasuredEV};
    private final LazyGlobalValue<CFString> lazyGlobalValue;
    
    private CGImagePropertyCIFF(String getterName) {
        lazyGlobalValue = new LazyGlobalValue<>(getClass(), getterName);
    }
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFString value() {
        return lazyGlobalValue.value();
    }
    
    public static CGImagePropertyCIFF valueOf(CFString value) {
        for (CGImagePropertyCIFF v : values) {
            if (v.value().equals(value)) {
                return v;
            }
        }
        throw new IllegalArgumentException("No constant with value " + value + " found in " 
            + /*<name>*/CGImagePropertyCIFF/*</name>*/.class.getName());
    }
    /*<methods>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFDescription", optional=true)
    protected static native CFString DescriptionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFFirmware", optional=true)
    protected static native CFString FirmwareKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFOwnerName", optional=true)
    protected static native CFString OwnerNameKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFImageName", optional=true)
    protected static native CFString ImageNameKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFImageFileName", optional=true)
    protected static native CFString ImageFileNameKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFReleaseMethod", optional=true)
    protected static native CFString ReleaseMethodKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFReleaseTiming", optional=true)
    protected static native CFString ReleaseTimingKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFRecordID", optional=true)
    protected static native CFString RecordIDKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFSelfTimingTime", optional=true)
    protected static native CFString SelfTimingTimeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFCameraSerialNumber", optional=true)
    protected static native CFString CameraSerialNumberKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFImageSerialNumber", optional=true)
    protected static native CFString ImageSerialNumberKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFContinuousDrive", optional=true)
    protected static native CFString ContinuousDriveKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFFocusMode", optional=true)
    protected static native CFString FocusModeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFMeteringMode", optional=true)
    protected static native CFString MeteringModeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFShootingMode", optional=true)
    protected static native CFString ShootingModeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFLensModel", optional=true)
    protected static native CFString LensModelKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFLensMaxMM", optional=true)
    protected static native CFString LensMaxMMKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFLensMinMM", optional=true)
    protected static native CFString LensMinMMKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFWhiteBalanceIndex", optional=true)
    protected static native CFString WhiteBalanceIndexKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFFlashExposureComp", optional=true)
    protected static native CFString FlashExposureCompKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyCIFFMeasuredEV", optional=true)
    protected static native CFString MeasuredEVKey();
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyCIFFData.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;

import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyCIFFData.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class CGImagePropertyCIFFData 
    extends /*<extends>*/Object/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyCIFFData toObject(Class<CGImagePropertyCIFFData> cls, long handle, long flags) {
            CFDictionary o = (CFDictionary) CFType.Marshaler.toObject(CFDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CGImagePropertyCIFFData(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyCIFFData o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private CFDictionary data;
    
    protected CGImagePropertyCIFFData(CFDictionary data) {
        this.data = data;
    }
    public CGImagePropertyCIFFData() {
        this.data = CFMutableDictionary.create();
    }
    /*<bind>*/static { Bro.bind(CGImagePropertyCIFFData.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFDictionary getDictionary() {
        return data;
    }
    
    public boolean has(CGImagePropertyCIFF property) {
        return data.containsKey(property.value());
    }
    
    public String getString(CGImagePropertyCIFF property) {
        if (has(property)) {
            CFString val = data.get(property.value(), CFString.class);
            return val.toString();
        }
        return null;
    }
    public double getNumber(CGImagePropertyCIFF property) {
        if (has(property)) {
            CFNumber val = data.get(property.value(), CFNumber.class);
            return val.doubleValue();
        }
        return 0;
    }
    public CGImagePropertyCIFFData set(CGImagePropertyCIFF property, String value) {
        data.put(property.value(), new CFString(value));
        return this;
    }
    public CGImagePropertyCIFFData set(CGImagePropertyCIFF property, double value) {
        data.put(property.value(), CFNumber.valueOf(value));
        return this;
    }
    /*<methods>*/
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyCanon.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyCanon.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImagePropertyCanon/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyCanon toObject(Class<CGImagePropertyCanon> cls, long handle, long flags) {
            CFString o = (CFString) CFType.Marshaler.toObject(CFString.class, handle, flags);
            if (o == null) {
                return null;
            }
            return CGImagePropertyCanon.valueOf(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyCanon o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.value(), flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    /*<bind>*/static { Bro.bind(CGImagePropertyCanon.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCanon OwnerName = new CGImagePropertyCanon("OwnerNameKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCanon CameraSerialNumber = new CGImagePropertyCanon("CameraSerialNumberKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCanon ImageSerialNumber = new CGImagePropertyCanon("ImageSerialNumberKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCanon FlashExposureComp = new CGImagePropertyCanon("FlashExposureCompKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCanon ContinuousDrive = new CGImagePropertyCanon("ContinuousDriveKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCanon LensModel = new CGImagePropertyCanon("LensModelKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCanon Firmware = new CGImagePropertyCanon("FirmwareKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyCanon AspectRatioInfo = new CGImagePropertyCanon("AspectRatioInfoKey");
    
    private static CGImagePropertyCanon[] values = new CGImagePropertyCanon[] {OwnerName, CameraSerialNumber, ImageSerialNumber, 
        FlashExposureComp, ContinuousDrive, LensModel, Firmware, AspectRatioInfo};
    private final LazyGlobalValue<CFString> lazyGlobalValue;
    
    private CGImagePropertyCanon(String getterName) {
        lazyGlobalValue = new LazyGlobalValue<>(getClass(), getterName);
    }
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFString value() {
        return lazyGlobalValue.value();
    }
    
    public static CGImagePropertyCanon valueOf(CFString value) {
        for (CGImagePropertyCanon v : values) {
            if (v.value().equals(value)) {
                return v;
            }
        }
        throw new IllegalArgumentException("No constant with value " + value + " found in " 
            + /*<name>*/CGImagePropertyCanon/*</name>*/.class.getName());
    }
    /*<methods>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerCanonOwnerName", optional=true)
    protected static native CFString OwnerNameKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerCanonCameraSerialNumber", optional=true)
    protected static native CFString CameraSerialNumberKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerCanonImageSerialNumber", optional=true)
    protected static native CFString ImageSerialNumberKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerCanonFlashExposureComp", optional=true)
    protected static native CFString FlashExposureCompKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerCanonContinuousDrive", optional=true)
    protected static native CFString ContinuousDriveKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerCanonLensModel", optional=true)
    protected static native CFString LensModelKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerCanonFirmware", optional=true)
    protected static native CFString FirmwareKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerCanonAspectRatioInfo", optional=true)
    protected static native CFString AspectRatioInfoKey();
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyCanonData.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;

import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyCanonData.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class CGImagePropertyCanonData 
    extends /*<extends>*/Object/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyCanonData toObject(Class<CGImagePropertyCanonData> cls, long handle, long flags) {
            CFDictionary o = (CFDictionary) CFType.Marshaler.toObject(CFDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CGImagePropertyCanonData(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyCanonData o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private CFDictionary data;
    
    protected CGImagePropertyCanonData(CFDictionary data) {
        this.data = data;
    }
    public CGImagePropertyCanonData() {
        this.data = CFMutableDictionary.create();
    }
    /*<bind>*/static { Bro.bind(CGImagePropertyCanonData.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFDictionary getDictionary() {
        return data;
    }
    
    public boolean has(CGImagePropertyCanon property) {
        return data.containsKey(property.value());
    }
    
    public String getString(CGImagePropertyCanon property) {
        if (has(property)) {
            CFString val = data.get(property.value(), CFString.class);
            return val.toString();
        }
        return null;
    }
    public double getNumber(CGImagePropertyCanon property) {
        if (has(property)) {
            CFNumber val = data.get(property.value(), CFNumber.class);
            return val.doubleValue();
        }
        return 0;
    }
    public CGImagePropertyCanonData set(CGImagePropertyCanon property, String value) {
        data.put(property.value(), new CFString(value));
        return this;
    }
    public CGImagePropertyCanonData set(CGImagePropertyCanon property, double value) {
        data.put(property.value(), CFNumber.valueOf(value));
        return this;
    }
    /*<methods>*/
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyColorModel.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyColorModel.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImagePropertyColorModel/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyColorModel toObject(Class<CGImagePropertyColorModel> cls, long handle, long flags) {
            CFString o = (CFString) CFType.Marshaler.toObject(CFString.class, handle, flags);
            if (o == null) {
                return null;
            }
            return CGImagePropertyColorModel.valueOf(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyColorModel o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.value(), flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    /*<bind>*/static { Bro.bind(CGImagePropertyColorModel.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyColorModel RGB = new CGImagePropertyColorModel("RGBValue");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyColorModel Gray = new CGImagePropertyColorModel("GrayValue");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyColorModel CMYK = new CGImagePropertyColorModel("CMYKValue");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyColorModel Lab = new CGImagePropertyColorModel("LabValue");
    
    private static CGImagePropertyColorModel[] values = new CGImagePropertyColorModel[] {RGB, Gray, CMYK, Lab};
    private final LazyGlobalValue<CFString> lazyGlobalValue;
    
    private CGImagePropertyColorModel(String getterName) {
        lazyGlobalValue = new LazyGlobalValue<>(getClass(), getterName);
    }
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFString value() {
        return lazyGlobalValue.value();
    }
    
    public static CGImagePropertyColorModel valueOf(CFString value) {
        for (CGImagePropertyColorModel v : values) {
            if (v.value().equals(value)) {
                return v;
            }
        }
        throw new IllegalArgumentException("No constant with value " + value + " found in " 
            + /*<name>*/CGImagePropertyColorModel/*</name>*/.class.getName());
    }
    /*<methods>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyColorModelRGB", optional=true)
    protected static native CFString RGBValue();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyColorModelGray", optional=true)
    protected static native CFString GrayValue();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyColorModelCMYK", optional=true)
    protected static native CFString CMYKValue();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyColorModelLab", optional=true)
    protected static native CFString LabValue();
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyDNG.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyDNG.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImagePropertyDNG/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {
    
    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyDNG toObject(Class<CGImagePropertyDNG> cls, long handle, long flags) {
            CFString o = (CFString) CFType.Marshaler.toObject(CFString.class, handle, flags);
            if (o == null) {
                return null;
            }
            return CGImagePropertyDNG.valueOf(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyDNG o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.value(), flags);
        }
    }

    /*<ptr>*/
    /*</ptr>*/
    /*<bind>*/static { Bro.bind(CGImagePropertyDNG.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyDNG Version = new CGImagePropertyDNG("VersionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyDNG BackwardVersion = new CGImagePropertyDNG("BackwardVersionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyDNG UniqueCameraModel = new CGImagePropertyDNG("UniqueCameraModelKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyDNG LocalizedCameraModel = new CGImagePropertyDNG("LocalizedCameraModelKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyDNG CameraSerialNumber = new CGImagePropertyDNG("CameraSerialNumberKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyDNG LensInfo = new CGImagePropertyDNG("LensInfoKey");
    
    private static CGImagePropertyDNG[] values = new CGImagePropertyDNG[] {Version, BackwardVersion, UniqueCameraModel, LocalizedCameraModel, 
        CameraSerialNumber, LensInfo};
    private final LazyGlobalValue<CFString> lazyGlobalValue;
    
    private CGImagePropertyDNG(String getterName) {
        lazyGlobalValue = new LazyGlobalValue<>(getClass(), getterName);
    }
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFString value() {
        return lazyGlobalValue.value();
    }
    
    public static CGImagePropertyDNG valueOf(CFString value) {
        for (CGImagePropertyDNG v : values) {
            if (v.value().equals(value)) {
                return v;
            }
        }
        throw new IllegalArgumentException("No constant with value " + value + " found in " 
            + /*<name>*/CGImagePropertyDNG/*</name>*/.class.getName());
    }
    /*<methods>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyDNGVersion", optional=true)
    protected static native CFString VersionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyDNGBackwardVersion", optional=true)
    protected static native CFString BackwardVersionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyDNGUniqueCameraModel", optional=true)
    protected static native CFString UniqueCameraModelKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyDNGLocalizedCameraModel", optional=true)
    protected static native CFString LocalizedCameraModelKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyDNGCameraSerialNumber", optional=true)
    protected static native CFString CameraSerialNumberKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyDNGLensInfo", optional=true)
    protected static native CFString LensInfoKey();
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyDNGData.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;

import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyDNGData.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class CGImagePropertyDNGData 
    extends /*<extends>*/Object/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyDNGData toObject(Class<CGImagePropertyDNGData> cls, long handle, long flags) {
            CFDictionary o = (CFDictionary) CFType.Marshaler.toObject(CFDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CGImagePropertyDNGData(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyDNGData o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private CFDictionary data;
    
    protected CGImagePropertyDNGData(CFDictionary data) {
        this.data = data;
    }
    public CGImagePropertyDNGData() {
        this.data = CFMutableDictionary.create();
    }
    /*<bind>*/static { Bro.bind(CGImagePropertyDNGData.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFDictionary getDictionary() {
        return data;
    }
    
    public boolean has(CGImagePropertyDNG property) {
        return data.containsKey(property.value());
    }
    
    public String getString(CGImagePropertyDNG property) {
        if (has(property)) {
            CFString val = data.get(property.value(), CFString.class);
            return val.toString();
        }
        return null;
    }
    public double getNumber(CGImagePropertyDNG property) {
        if (has(property)) {
            CFNumber val = data.get(property.value(), CFNumber.class);
            return val.doubleValue();
        }
        return 0;
    }
    public CGImagePropertyDNGData set(CGImagePropertyDNG property, String value) {
        data.put(property.value(), new CFString(value));
        return this;
    }
    public CGImagePropertyDNGData set(CGImagePropertyDNG property, double value) {
        data.put(property.value(), CFNumber.valueOf(value));
        return this;
    }
    /*<methods>*/
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyExif.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyExif.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImagePropertyExif/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {
    
    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyExif toObject(Class<CGImagePropertyExif> cls, long handle, long flags) {
            CFString o = (CFString) CFType.Marshaler.toObject(CFString.class, handle, flags);
            if (o == null) {
                return null;
            }
            return CGImagePropertyExif.valueOf(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyExif o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.value(), flags);
        }
    }

    /*<ptr>*/
    /*</ptr>*/
    /*<bind>*/static { Bro.bind(CGImagePropertyExif.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif ExposureTime = new CGImagePropertyExif("ExposureTimeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif FNumber = new CGImagePropertyExif("FNumberKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif ExposureProgram = new CGImagePropertyExif("ExposureProgramKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif SpectralSensitivity = new CGImagePropertyExif("SpectralSensitivityKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif ISOSpeedRatings = new CGImagePropertyExif("ISOSpeedRatingsKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif OECF = new CGImagePropertyExif("OECFKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif Version = new CGImagePropertyExif("VersionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif DateTimeOriginal = new CGImagePropertyExif("DateTimeOriginalKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif DateTimeDigitized = new CGImagePropertyExif("DateTimeDigitizedKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif ComponentsConfiguration = new CGImagePropertyExif("ComponentsConfigurationKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif CompressedBitsPerPixel = new CGImagePropertyExif("CompressedBitsPerPixelKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif ShutterSpeedValue = new CGImagePropertyExif("ShutterSpeedValueKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif ApertureValue = new CGImagePropertyExif("ApertureValueKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif BrightnessValue = new CGImagePropertyExif("BrightnessValueKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif ExposureBiasValue = new CGImagePropertyExif("ExposureBiasValueKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif MaxApertureValue = new CGImagePropertyExif("MaxApertureValueKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif SubjectDistance = new CGImagePropertyExif("SubjectDistanceKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif MeteringMode = new CGImagePropertyExif("MeteringModeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif LightSource = new CGImagePropertyExif("LightSourceKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif Flash = new CGImagePropertyExif("FlashKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif FocalLength = new CGImagePropertyExif("FocalLengthKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif SubjectArea = new CGImagePropertyExif("SubjectAreaKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif MakerNote = new CGImagePropertyExif("MakerNoteKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif UserComment = new CGImagePropertyExif("UserCommentKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif SubsecTime = new CGImagePropertyExif("SubsecTimeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif SubsecTimeOrginal = new CGImagePropertyExif("SubsecTimeOrginalKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif SubsecTimeDigitized = new CGImagePropertyExif("SubsecTimeDigitizedKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif FlashPixVersion = new CGImagePropertyExif("FlashPixVersionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif ColorSpace = new CGImagePropertyExif("ColorSpaceKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif PixelXDimension = new CGImagePropertyExif("PixelXDimensionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif PixelYDimension = new CGImagePropertyExif("PixelYDimensionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif RelatedSoundFile = new CGImagePropertyExif("RelatedSoundFileKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif FlashEnergy = new CGImagePropertyExif("FlashEnergyKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif SpatialFrequencyResponse = new CGImagePropertyExif("SpatialFrequencyResponseKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif FocalPlaneXResolution = new CGImagePropertyExif("FocalPlaneXResolutionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif FocalPlaneYResolution = new CGImagePropertyExif("FocalPlaneYResolutionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif FocalPlaneResolutionUnit = new CGImagePropertyExif("FocalPlaneResolutionUnitKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif SubjectLocation = new CGImagePropertyExif("SubjectLocationKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif ExposureIndex = new CGImagePropertyExif("ExposureIndexKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif SensingMethod = new CGImagePropertyExif("SensingMethodKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif FileSource = new CGImagePropertyExif("FileSourceKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif SceneType = new CGImagePropertyExif("SceneTypeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif CFAPattern = new CGImagePropertyExif("CFAPatternKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif CustomRendered = new CGImagePropertyExif("CustomRenderedKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif ExposureMode = new CGImagePropertyExif("ExposureModeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif WhiteBalance = new CGImagePropertyExif("WhiteBalanceKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif DigitalZoomRatio = new CGImagePropertyExif("DigitalZoomRatioKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif FocalLenIn35mmFilm = new CGImagePropertyExif("FocalLenIn35mmFilmKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif SceneCaptureType = new CGImagePropertyExif("SceneCaptureTypeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif GainControl = new CGImagePropertyExif("GainControlKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif Contrast = new CGImagePropertyExif("ContrastKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif Saturation = new CGImagePropertyExif("SaturationKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif Sharpness = new CGImagePropertyExif("SharpnessKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif DeviceSettingDescription = new CGImagePropertyExif("DeviceSettingDescriptionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif SubjectDistRange = new CGImagePropertyExif("SubjectDistRangeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif ImageUniqueID = new CGImagePropertyExif("ImageUniqueIDKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExif Gamma = new CGImagePropertyExif("GammaKey");
    /**
     * @since Available in iOS 5.0 and later.
     */
    public static final CGImagePropertyExif LensSerialNumber = new CGImagePropertyExif("LensSerialNumberKey");
    /**
     * @since Available in iOS 5.0 and later.
     */
    public static final CGImagePropertyExif CameraOwnerName = new CGImagePropertyExif("CameraOwnerNameKey");
    /**
     * @since Available in iOS 5.0 and later.
     */
    public static final CGImagePropertyExif BodySerialNumber = new CGImagePropertyExif("BodySerialNumberKey");
    /**
     * @since Available in iOS 5.0 and later.
     */
    public static final CGImagePropertyExif LensSpecification = new CGImagePropertyExif("LensSpecificationKey");
    /**
     * @since Available in iOS 5.0 and later.
     */
    public static final CGImagePropertyExif LensMake = new CGImagePropertyExif("LensMakeKey");
    /**
     * @since Available in iOS 5.0 and later.
     */
    public static final CGImagePropertyExif LensModel = new CGImagePropertyExif("LensModelKey");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImagePropertyExif SensitivityType = new CGImagePropertyExif("SensitivityTypeKey");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImagePropertyExif StandardOutputSensitivity = new CGImagePropertyExif("StandardOutputSensitivityKey");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImagePropertyExif RecommendedExposureIndex = new CGImagePropertyExif("RecommendedExposureIndexKey");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImagePropertyExif ISOSpeed = new CGImagePropertyExif("ISOSpeedKey");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImagePropertyExif ISOSpeedLatitudeyyy = new CGImagePropertyExif("ISOSpeedLatitudeyyyKey");
    /**
     * @since Available in iOS 7.0 and later.
     */
    public static final CGImagePropertyExif ISOSpeedLatitudezzz = new CGImagePropertyExif("ISOSpeedLatitudezzzKey");

    
    private static CGImagePropertyExif[] values = new CGImagePropertyExif[] {ExposureTime, FNumber, ExposureProgram, SpectralSensitivity, 
        ISOSpeedRatings, OECF, Version, DateTimeOriginal, DateTimeDigitized, ComponentsConfiguration, CompressedBitsPerPixel, ShutterSpeedValue, 
        ApertureValue, BrightnessValue, ExposureBiasValue, MaxApertureValue, SubjectDistance, MeteringMode, LightSource, Flash, FocalLength, 
        SubjectArea, MakerNote, UserComment, SubsecTime, SubsecTimeOrginal, SubsecTimeDigitized, FlashPixVersion, ColorSpace, PixelXDimension, 
        PixelYDimension, RelatedSoundFile, FlashEnergy, SpatialFrequencyResponse, FocalPlaneXResolution, FocalPlaneYResolution, FocalPlaneResolutionUnit, 
        SubjectLocation, ExposureIndex, SensingMethod, FileSource, SceneType, CFAPattern, CustomRendered, ExposureMode, WhiteBalance, DigitalZoomRatio, 
        FocalLenIn35mmFilm, SceneCaptureType, GainControl, Contrast, Saturation, Sharpness, DeviceSettingDescription, SubjectDistRange, ImageUniqueID, 
        Gamma, LensSerialNumber, CameraOwnerName, BodySerialNumber, LensSpecification, LensMake, LensModel, SensitivityType, StandardOutputSensitivity, 
        RecommendedExposureIndex, ISOSpeed, ISOSpeedLatitudeyyy, ISOSpeedLatitudezzz};
    private final LazyGlobalValue<CFString> lazyGlobalValue;
    
    private CGImagePropertyExif(String getterName) {
        lazyGlobalValue = new LazyGlobalValue<>(getClass(), getterName);
    }
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFString value() {
        return lazyGlobalValue.value();
    }
    
    public static CGImagePropertyExif valueOf(CFString value) {
        for (CGImagePropertyExif v : values) {
            if (v.value().equals(value)) {
                return v;
            }
        }
        throw new IllegalArgumentException("No constant with value " + value + " found in " 
            + /*<name>*/CGImagePropertyExif/*</name>*/.class.getName());
    }
    /*<methods>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifExposureTime", optional=true)
    protected static native CFString ExposureTimeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifFNumber", optional=true)
    protected static native CFString FNumberKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifExposureProgram", optional=true)
    protected static native CFString ExposureProgramKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifSpectralSensitivity", optional=true)
    protected static native CFString SpectralSensitivityKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifISOSpeedRatings", optional=true)
    protected static native CFString ISOSpeedRatingsKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifOECF", optional=true)
    protected static native CFString OECFKey();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifSensitivityType", optional=true)
    protected static native CFString SensitivityTypeKey();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifStandardOutputSensitivity", optional=true)
    protected static native CFString StandardOutputSensitivityKey();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifRecommendedExposureIndex", optional=true)
    protected static native CFString RecommendedExposureIndexKey();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifISOSpeed", optional=true)
    protected static native CFString ISOSpeedKey();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifISOSpeedLatitudeyyy", optional=true)
    protected static native CFString ISOSpeedLatitudeyyyKey();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifISOSpeedLatitudezzz", optional=true)
    protected static native CFString ISOSpeedLatitudezzzKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifVersion", optional=true)
    protected static native CFString VersionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifDateTimeOriginal", optional=true)
    protected static native CFString DateTimeOriginalKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifDateTimeDigitized", optional=true)
    protected static native CFString DateTimeDigitizedKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifComponentsConfiguration", optional=true)
    protected static native CFString ComponentsConfigurationKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifCompressedBitsPerPixel", optional=true)
    protected static native CFString CompressedBitsPerPixelKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifShutterSpeedValue", optional=true)
    protected static native CFString ShutterSpeedValueKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifApertureValue", optional=true)
    protected static native CFString ApertureValueKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifBrightnessValue", optional=true)
    protected static native CFString BrightnessValueKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifExposureBiasValue", optional=true)
    protected static native CFString ExposureBiasValueKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifMaxApertureValue", optional=true)
    protected static native CFString MaxApertureValueKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifSubjectDistance", optional=true)
    protected static native CFString SubjectDistanceKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifMeteringMode", optional=true)
    protected static native CFString MeteringModeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifLightSource", optional=true)
    protected static native CFString LightSourceKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifFlash", optional=true)
    protected static native CFString FlashKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifFocalLength", optional=true)
    protected static native CFString FocalLengthKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifSubjectArea", optional=true)
    protected static native CFString SubjectAreaKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifMakerNote", optional=true)
    protected static native CFString MakerNoteKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifUserComment", optional=true)
    protected static native CFString UserCommentKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifSubsecTime", optional=true)
    protected static native CFString SubsecTimeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifSubsecTimeOrginal", optional=true)
    protected static native CFString SubsecTimeOrginalKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifSubsecTimeDigitized", optional=true)
    protected static native CFString SubsecTimeDigitizedKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifFlashPixVersion", optional=true)
    protected static native CFString FlashPixVersionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifColorSpace", optional=true)
    protected static native CFString ColorSpaceKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifPixelXDimension", optional=true)
    protected static native CFString PixelXDimensionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifPixelYDimension", optional=true)
    protected static native CFString PixelYDimensionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifRelatedSoundFile", optional=true)
    protected static native CFString RelatedSoundFileKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifFlashEnergy", optional=true)
    protected static native CFString FlashEnergyKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifSpatialFrequencyResponse", optional=true)
    protected static native CFString SpatialFrequencyResponseKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifFocalPlaneXResolution", optional=true)
    protected static native CFString FocalPlaneXResolutionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifFocalPlaneYResolution", optional=true)
    protected static native CFString FocalPlaneYResolutionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifFocalPlaneResolutionUnit", optional=true)
    protected static native CFString FocalPlaneResolutionUnitKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifSubjectLocation", optional=true)
    protected static native CFString SubjectLocationKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifExposureIndex", optional=true)
    protected static native CFString ExposureIndexKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifSensingMethod", optional=true)
    protected static native CFString SensingMethodKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifFileSource", optional=true)
    protected static native CFString FileSourceKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifSceneType", optional=true)
    protected static native CFString SceneTypeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifCFAPattern", optional=true)
    protected static native CFString CFAPatternKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifCustomRendered", optional=true)
    protected static native CFString CustomRenderedKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifExposureMode", optional=true)
    protected static native CFString ExposureModeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifWhiteBalance", optional=true)
    protected static native CFString WhiteBalanceKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifDigitalZoomRatio", optional=true)
    protected static native CFString DigitalZoomRatioKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifFocalLenIn35mmFilm", optional=true)
    protected static native CFString FocalLenIn35mmFilmKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifSceneCaptureType", optional=true)
    protected static native CFString SceneCaptureTypeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifGainControl", optional=true)
    protected static native CFString GainControlKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifContrast", optional=true)
    protected static native CFString ContrastKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifSaturation", optional=true)
    protected static native CFString SaturationKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifSharpness", optional=true)
    protected static native CFString SharpnessKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifDeviceSettingDescription", optional=true)
    protected static native CFString DeviceSettingDescriptionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifSubjectDistRange", optional=true)
    protected static native CFString SubjectDistRangeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifImageUniqueID", optional=true)
    protected static native CFString ImageUniqueIDKey();
    /**
     * @since Available in iOS 5.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifCameraOwnerName", optional=true)
    protected static native CFString CameraOwnerNameKey();
    /**
     * @since Available in iOS 5.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifBodySerialNumber", optional=true)
    protected static native CFString BodySerialNumberKey();
    /**
     * @since Available in iOS 5.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifLensSpecification", optional=true)
    protected static native CFString LensSpecificationKey();
    /**
     * @since Available in iOS 5.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifLensMake", optional=true)
    protected static native CFString LensMakeKey();
    /**
     * @since Available in iOS 5.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifLensModel", optional=true)
    protected static native CFString LensModelKey();
    /**
     * @since Available in iOS 5.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifLensSerialNumber", optional=true)
    protected static native CFString LensSerialNumberKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifGamma", optional=true)
    protected static native CFString GammaKey();
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyExifAux.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyExifAux.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImagePropertyExifAux/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyExifAux toObject(Class<CGImagePropertyExifAux> cls, long handle, long flags) {
            CFString o = (CFString) CFType.Marshaler.toObject(CFString.class, handle, flags);
            if (o == null) {
                return null;
            }
            return CGImagePropertyExifAux.valueOf(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyExifAux o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.value(), flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    /*<bind>*/static { Bro.bind(CGImagePropertyExifAux.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExifAux LensInfo = new CGImagePropertyExifAux("LensInfoKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExifAux LensModel = new CGImagePropertyExifAux("LensModelKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExifAux SerialNumber = new CGImagePropertyExifAux("SerialNumberKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExifAux LensID = new CGImagePropertyExifAux("LensIDKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExifAux LensSerialNumber = new CGImagePropertyExifAux("LensSerialNumberKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExifAux ImageNumber = new CGImagePropertyExifAux("ImageNumberKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExifAux FlashCompensation = new CGImagePropertyExifAux("FlashCompensationKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExifAux OwnerName = new CGImagePropertyExifAux("OwnerNameKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyExifAux Firmware = new CGImagePropertyExifAux("FirmwareKey");
    
    private static CGImagePropertyExifAux[] values = new CGImagePropertyExifAux[] {LensInfo, LensModel, SerialNumber, 
        LensID, LensSerialNumber, ImageNumber, FlashCompensation, OwnerName, Firmware};
    private final LazyGlobalValue<CFString> lazyGlobalValue;
    
    private CGImagePropertyExifAux(String getterName) {
        lazyGlobalValue = new LazyGlobalValue<>(getClass(), getterName);
    }
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFString value() {
        return lazyGlobalValue.value();
    }
    
    public static CGImagePropertyExifAux valueOf(CFString value) {
        for (CGImagePropertyExifAux v : values) {
            if (v.value().equals(value)) {
                return v;
            }
        }
        throw new IllegalArgumentException("No constant with value " + value + " found in " 
            + /*<name>*/CGImagePropertyExifAux/*</name>*/.class.getName());
    }
    /*<methods>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifAuxLensInfo", optional=true)
    protected static native CFString LensInfoKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifAuxLensModel", optional=true)
    protected static native CFString LensModelKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifAuxSerialNumber", optional=true)
    protected static native CFString SerialNumberKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifAuxLensID", optional=true)
    protected static native CFString LensIDKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifAuxLensSerialNumber", optional=true)
    protected static native CFString LensSerialNumberKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifAuxImageNumber", optional=true)
    protected static native CFString ImageNumberKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifAuxFlashCompensation", optional=true)
    protected static native CFString FlashCompensationKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifAuxOwnerName", optional=true)
    protected static native CFString OwnerNameKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyExifAuxFirmware", optional=true)
    protected static native CFString FirmwareKey();
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyExifAuxData.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;

import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyExifAuxData.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class CGImagePropertyExifAuxData 
    extends /*<extends>*/Object/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyExifAuxData toObject(Class<CGImagePropertyExifAuxData> cls, long handle, long flags) {
            CFDictionary o = (CFDictionary) CFType.Marshaler.toObject(CFDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CGImagePropertyExifAuxData(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyExifAuxData o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private CFDictionary data;
    
    protected CGImagePropertyExifAuxData(CFDictionary data) {
        this.data = data;
    }
    public CGImagePropertyExifAuxData() {
        this.data = CFMutableDictionary.create();
    }
    /*<bind>*/static { Bro.bind(CGImagePropertyExifAuxData.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFDictionary getDictionary() {
        return data;
    }
    
    public boolean has(CGImagePropertyExifAux property) {
        return data.containsKey(property.value());
    }
    
    public String getString(CGImagePropertyExifAux property) {
        if (has(property)) {
            CFString val = data.get(property.value(), CFString.class);
            return val.toString();
        }
        return null;
    }
    public double getNumber(CGImagePropertyExifAux property) {
        if (has(property)) {
            CFNumber val = data.get(property.value(), CFNumber.class);
            return val.doubleValue();
        }
        return 0;
    }
    public CGImagePropertyExifAuxData set(CGImagePropertyExifAux property, String value) {
        data.put(property.value(), new CFString(value));
        return this;
    }
    public CGImagePropertyExifAuxData set(CGImagePropertyExifAux property, double value) {
        data.put(property.value(), CFNumber.valueOf(value));
        return this;
    }
    /*<methods>*/
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyExifData.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;

import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyExifData.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class CGImagePropertyExifData 
    extends /*<extends>*/Object/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyExifData toObject(Class<CGImagePropertyExifData> cls, long handle, long flags) {
            CFDictionary o = (CFDictionary) CFType.Marshaler.toObject(CFDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CGImagePropertyExifData(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyExifData o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private CFDictionary data;
    
    protected CGImagePropertyExifData(CFDictionary data) {
        this.data = data;
    }
    public CGImagePropertyExifData() {
        this.data = CFMutableDictionary.create();
    }
    /*<bind>*/static { Bro.bind(CGImagePropertyExifData.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFDictionary getDictionary() {
        return data;
    }
    
    public boolean has(CGImagePropertyExif property) {
        return data.containsKey(property.value());
    }
    
    public String getString(CGImagePropertyExif property) {
        if (has(property)) {
            CFString val = data.get(property.value(), CFString.class);
            return val.toString();
        }
        return null;
    }
    public double getNumber(CGImagePropertyExif property) {
        if (has(property)) {
            CFNumber val = data.get(property.value(), CFNumber.class);
            return val.doubleValue();
        }
        return 0;
    }
    public CGImagePropertyExifData set(CGImagePropertyExif property, String value) {
        data.put(property.value(), new CFString(value));
        return this;
    }
    public CGImagePropertyExifData set(CGImagePropertyExif property, double value) {
        data.put(property.value(), CFNumber.valueOf(value));
        return this;
    }
    /*<methods>*/
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyGIF.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyGIF.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImagePropertyGIF/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyGIF toObject(Class<CGImagePropertyGIF> cls, long handle, long flags) {
            CFString o = (CFString) CFType.Marshaler.toObject(CFString.class, handle, flags);
            if (o == null) {
                return null;
            }
            return CGImagePropertyGIF.valueOf(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyGIF o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.value(), flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    /*<bind>*/static { Bro.bind(CGImagePropertyGIF.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGIF LoopCount = new CGImagePropertyGIF("LoopCountKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGIF DelayTime = new CGImagePropertyGIF("DelayTimeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGIF ImageColorMap = new CGImagePropertyGIF("ImageColorMapKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGIF HasGlobalColorMap = new CGImagePropertyGIF("HasGlobalColorMapKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGIF UnclampedDelayTime = new CGImagePropertyGIF("UnclampedDelayTimeKey");
    
    private static CGImagePropertyGIF[] values = new CGImagePropertyGIF[] {LoopCount, DelayTime, ImageColorMap, 
        HasGlobalColorMap, UnclampedDelayTime};
    private final LazyGlobalValue<CFString> lazyGlobalValue;
    
    private CGImagePropertyGIF(String getterName) {
        lazyGlobalValue = new LazyGlobalValue<>(getClass(), getterName);
    }
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFString value() {
        return lazyGlobalValue.value();
    }
    
    public static CGImagePropertyGIF valueOf(CFString value) {
        for (CGImagePropertyGIF v : values) {
            if (v.value().equals(value)) {
                return v;
            }
        }
        throw new IllegalArgumentException("No constant with value " + value + " found in " 
            + /*<name>*/CGImagePropertyGIF/*</name>*/.class.getName());
    }
    /*<methods>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGIFLoopCount", optional=true)
    protected static native CFString LoopCountKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGIFDelayTime", optional=true)
    protected static native CFString DelayTimeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGIFImageColorMap", optional=true)
    protected static native CFString ImageColorMapKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGIFHasGlobalColorMap", optional=true)
    protected static native CFString HasGlobalColorMapKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGIFUnclampedDelayTime", optional=true)
    protected static native CFString UnclampedDelayTimeKey();
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyGIFData.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;

import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyGIFData.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class CGImagePropertyGIFData 
    extends /*<extends>*/Object/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyGIFData toObject(Class<CGImagePropertyGIFData> cls, long handle, long flags) {
            CFDictionary o = (CFDictionary) CFType.Marshaler.toObject(CFDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CGImagePropertyGIFData(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyGIFData o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private CFDictionary data;
    
    protected CGImagePropertyGIFData(CFDictionary data) {
        this.data = data;
    }
    public CGImagePropertyGIFData() {
        this.data = CFMutableDictionary.create();
    }
    /*<bind>*/static { Bro.bind(CGImagePropertyGIFData.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFDictionary getDictionary() {
        return data;
    }
    
    public boolean has(CGImagePropertyGIF property) {
        return data.containsKey(property.value());
    }
    
    public String getString(CGImagePropertyGIF property) {
        if (has(property)) {
            CFString val = data.get(property.value(), CFString.class);
            return val.toString();
        }
        return null;
    }
    public double getNumber(CGImagePropertyGIF property) {
        if (has(property)) {
            CFNumber val = data.get(property.value(), CFNumber.class);
            return val.doubleValue();
        }
        return 0;
    }
    public CGImagePropertyGIFData set(CGImagePropertyGIF property, String value) {
        data.put(property.value(), new CFString(value));
        return this;
    }
    public CGImagePropertyGIFData set(CGImagePropertyGIF property, double value) {
        data.put(property.value(), CFNumber.valueOf(value));
        return this;
    }
    /*<methods>*/
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyGPS.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyGPS.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImagePropertyGPS/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {
    
    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyGPS toObject(Class<CGImagePropertyGPS> cls, long handle, long flags) {
            CFString o = (CFString) CFType.Marshaler.toObject(CFString.class, handle, flags);
            if (o == null) {
                return null;
            }
            return CGImagePropertyGPS.valueOf(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyGPS o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.value(), flags);
        }
    }

    /*<ptr>*/
    /*</ptr>*/
    /*<bind>*/static { Bro.bind(CGImagePropertyGPS.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS Version = new CGImagePropertyGPS("VersionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS LatitudeRef = new CGImagePropertyGPS("LatitudeRefKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS Latitude = new CGImagePropertyGPS("LatitudeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS LongitudeRef = new CGImagePropertyGPS("LongitudeRefKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS Longitude = new CGImagePropertyGPS("LongitudeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS AltitudeRef = new CGImagePropertyGPS("AltitudeRefKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS Altitude = new CGImagePropertyGPS("AltitudeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS TimeStamp = new CGImagePropertyGPS("TimeStampKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS Satellites = new CGImagePropertyGPS("SatellitesKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS Status = new CGImagePropertyGPS("StatusKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS MeasureMode = new CGImagePropertyGPS("MeasureModeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS DOP = new CGImagePropertyGPS("DOPKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS SpeedRef = new CGImagePropertyGPS("SpeedRefKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS Speed = new CGImagePropertyGPS("SpeedKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS TrackRef = new CGImagePropertyGPS("TrackRefKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS Track = new CGImagePropertyGPS("TrackKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS ImgDirectionRef = new CGImagePropertyGPS("ImgDirectionRefKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS ImgDirection = new CGImagePropertyGPS("ImgDirectionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS MapDatum = new CGImagePropertyGPS("MapDatumKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS DestLatitudeRef = new CGImagePropertyGPS("DestLatitudeRefKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS DestLatitude = new CGImagePropertyGPS("DestLatitudeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS DestLongitudeRef = new CGImagePropertyGPS("DestLongitudeRefKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS DestLongitude = new CGImagePropertyGPS("DestLongitudeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS DestBearingRef = new CGImagePropertyGPS("DestBearingRefKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS DestBearing = new CGImagePropertyGPS("DestBearingKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS DestDistanceRef = new CGImagePropertyGPS("DestDistanceRefKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS DestDistance = new CGImagePropertyGPS("DestDistanceKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS ProcessingMethod = new CGImagePropertyGPS("ProcessingMethodKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS AreaInformation = new CGImagePropertyGPS("AreaInformationKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS DateStamp = new CGImagePropertyGPS("DateStampKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyGPS Differental = new CGImagePropertyGPS("DifferentalKey");
    /**
     * @since Available in iOS 8.0 and later.
     */
    public static final CGImagePropertyGPS HPositioningError = new CGImagePropertyGPS("HPositioningErrorKey");    
    
    private static CGImagePropertyGPS[] values = new CGImagePropertyGPS[] {Version, LatitudeRef, Latitude, LongitudeRef, 
        Longitude, AltitudeRef, Altitude, TimeStamp, Satellites, Status, MeasureMode, DOP, SpeedRef, Speed, TrackRef, Track, 
        ImgDirectionRef, ImgDirection, MapDatum, DestLatitudeRef, DestLatitude, DestLongitudeRef, DestLongitude, DestBearingRef, 
        DestBearing, DestDistanceRef, DestDistance, ProcessingMethod, AreaInformation, DateStamp, Differental, HPositioningError};
    private final LazyGlobalValue<CFString> lazyGlobalValue;
    
    private CGImagePropertyGPS(String getterName) {
        lazyGlobalValue = new LazyGlobalValue<>(getClass(), getterName);
    }
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFString value() {
        return lazyGlobalValue.value();
    }
    
    public static CGImagePropertyGPS valueOf(CFString value) {
        for (CGImagePropertyGPS v : values) {
            if (v.value().equals(value)) {
                return v;
            }
        }
        throw new IllegalArgumentException("No constant with value " + value + " found in " 
            + /*<name>*/CGImagePropertyGPS/*</name>*/.class.getName());
    }
    /*<methods>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSVersion", optional=true)
    protected static native CFString VersionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSLatitudeRef", optional=true)
    protected static native CFString LatitudeRefKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSLatitude", optional=true)
    protected static native CFString LatitudeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSLongitudeRef", optional=true)
    protected static native CFString LongitudeRefKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSLongitude", optional=true)
    protected static native CFString LongitudeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSAltitudeRef", optional=true)
    protected static native CFString AltitudeRefKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSAltitude", optional=true)
    protected static native CFString AltitudeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSTimeStamp", optional=true)
    protected static native CFString TimeStampKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSSatellites", optional=true)
    protected static native CFString SatellitesKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSStatus", optional=true)
    protected static native CFString StatusKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSMeasureMode", optional=true)
    protected static native CFString MeasureModeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSDOP", optional=true)
    protected static native CFString DOPKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSSpeedRef", optional=true)
    protected static native CFString SpeedRefKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSSpeed", optional=true)
    protected static native CFString SpeedKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSTrackRef", optional=true)
    protected static native CFString TrackRefKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSTrack", optional=true)
    protected static native CFString TrackKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSImgDirectionRef", optional=true)
    protected static native CFString ImgDirectionRefKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSImgDirection", optional=true)
    protected static native CFString ImgDirectionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSMapDatum", optional=true)
    protected static native CFString MapDatumKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSDestLatitudeRef", optional=true)
    protected static native CFString DestLatitudeRefKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSDestLatitude", optional=true)
    protected static native CFString DestLatitudeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSDestLongitudeRef", optional=true)
    protected static native CFString DestLongitudeRefKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSDestLongitude", optional=true)
    protected static native CFString DestLongitudeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSDestBearingRef", optional=true)
    protected static native CFString DestBearingRefKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSDestBearing", optional=true)
    protected static native CFString DestBearingKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSDestDistanceRef", optional=true)
    protected static native CFString DestDistanceRefKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSDestDistance", optional=true)
    protected static native CFString DestDistanceKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSProcessingMethod", optional=true)
    protected static native CFString ProcessingMethodKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSAreaInformation", optional=true)
    protected static native CFString AreaInformationKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSDateStamp", optional=true)
    protected static native CFString DateStampKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSDifferental", optional=true)
    protected static native CFString DifferentalKey();
    /**
     * @since Available in iOS 8.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyGPSHPositioningError", optional=true)
    protected static native CFString HPositioningErrorKey();
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyGPSData.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;

import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyGPSData.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class CGImagePropertyGPSData 
    extends /*<extends>*/Object/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyGPSData toObject(Class<CGImagePropertyGPSData> cls, long handle, long flags) {
            CFDictionary o = (CFDictionary) CFType.Marshaler.toObject(CFDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CGImagePropertyGPSData(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyGPSData o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private CFDictionary data;
    
    protected CGImagePropertyGPSData(CFDictionary data) {
        this.data = data;
    }
    public CGImagePropertyGPSData() {
        this.data = CFMutableDictionary.create();
    }
    /*<bind>*/static { Bro.bind(CGImagePropertyGPSData.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFDictionary getDictionary() {
        return data;
    }
    
    public boolean has(CGImagePropertyGPS property) {
        return data.containsKey(property.value());
    }
    
    public String getString(CGImagePropertyGPS property) {
        if (has(property)) {
            CFString val = data.get(property.value(), CFString.class);
            return val.toString();
        }
        return null;
    }
    public double getNumber(CGImagePropertyGPS property) {
        if (has(property)) {
            CFNumber val = data.get(property.value(), CFNumber.class);
            return val.doubleValue();
        }
        return 0;
    }
    public CGImagePropertyGPSData set(CGImagePropertyGPS property, String value) {
        data.put(property.value(), new CFString(value));
        return this;
    }
    public CGImagePropertyGPSData set(CGImagePropertyGPS property, double value) {
        data.put(property.value(), CFNumber.valueOf(value));
        return this;
    }
    /*<methods>*/
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyIPTC.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyIPTC.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImagePropertyIPTC/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyIPTC toObject(Class<CGImagePropertyIPTC> cls, long handle, long flags) {
            CFString o = (CFString) CFType.Marshaler.toObject(CFString.class, handle, flags);
            if (o == null) {
                return null;
            }
            return CGImagePropertyIPTC.valueOf(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyIPTC o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.value(), flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    /*<bind>*/static { Bro.bind(CGImagePropertyIPTC.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC ObjectTypeReference = new CGImagePropertyIPTC("ObjectTypeReferenceKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC ObjectAttributeReference = new CGImagePropertyIPTC("ObjectAttributeReferenceKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC ObjectName = new CGImagePropertyIPTC("ObjectNameKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC EditStatus = new CGImagePropertyIPTC("EditStatusKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC EditorialUpdate = new CGImagePropertyIPTC("EditorialUpdateKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC Urgency = new CGImagePropertyIPTC("UrgencyKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC SubjectReference = new CGImagePropertyIPTC("SubjectReferenceKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC Category = new CGImagePropertyIPTC("CategoryKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC SupplementalCategory = new CGImagePropertyIPTC("SupplementalCategoryKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC FixtureIdentifier = new CGImagePropertyIPTC("FixtureIdentifierKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC Keywords = new CGImagePropertyIPTC("KeywordsKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC ContentLocationCode = new CGImagePropertyIPTC("ContentLocationCodeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC ContentLocationName = new CGImagePropertyIPTC("ContentLocationNameKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC ReleaseDate = new CGImagePropertyIPTC("ReleaseDateKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC ReleaseTime = new CGImagePropertyIPTC("ReleaseTimeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC ExpirationDate = new CGImagePropertyIPTC("ExpirationDateKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC ExpirationTime = new CGImagePropertyIPTC("ExpirationTimeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC SpecialInstructions = new CGImagePropertyIPTC("SpecialInstructionsKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC ActionAdvised = new CGImagePropertyIPTC("ActionAdvisedKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC ReferenceService = new CGImagePropertyIPTC("ReferenceServiceKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC ReferenceDate = new CGImagePropertyIPTC("ReferenceDateKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC ReferenceNumber = new CGImagePropertyIPTC("ReferenceNumberKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC DateCreated = new CGImagePropertyIPTC("DateCreatedKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC TimeCreated = new CGImagePropertyIPTC("TimeCreatedKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC DigitalCreationDate = new CGImagePropertyIPTC("DigitalCreationDateKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC DigitalCreationTime = new CGImagePropertyIPTC("DigitalCreationTimeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC OriginatingProgram = new CGImagePropertyIPTC("OriginatingProgramKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC ProgramVersion = new CGImagePropertyIPTC("ProgramVersionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC ObjectCycle = new CGImagePropertyIPTC("ObjectCycleKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC Byline = new CGImagePropertyIPTC("BylineKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC BylineTitle = new CGImagePropertyIPTC("BylineTitleKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC City = new CGImagePropertyIPTC("CityKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC SubLocation = new CGImagePropertyIPTC("SubLocationKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC ProvinceState = new CGImagePropertyIPTC("ProvinceStateKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC CountryPrimaryLocationCode = new CGImagePropertyIPTC("CountryPrimaryLocationCodeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC CountryPrimaryLocationName = new CGImagePropertyIPTC("CountryPrimaryLocationNameKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC OriginalTransmissionReference = new CGImagePropertyIPTC("OriginalTransmissionReferenceKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC Headline = new CGImagePropertyIPTC("HeadlineKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC Credit = new CGImagePropertyIPTC("CreditKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC Source = new CGImagePropertyIPTC("SourceKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC CopyrightNotice = new CGImagePropertyIPTC("CopyrightNoticeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC Contact = new CGImagePropertyIPTC("ContactKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC CaptionAbstract = new CGImagePropertyIPTC("CaptionAbstractKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC WriterEditor = new CGImagePropertyIPTC("WriterEditorKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC ImageType = new CGImagePropertyIPTC("ImageTypeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC ImageOrientation = new CGImagePropertyIPTC("ImageOrientationKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC LanguageIdentifier = new CGImagePropertyIPTC("LanguageIdentifierKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC StarRating = new CGImagePropertyIPTC("StarRatingKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC CreatorContactInfo = new CGImagePropertyIPTC("CreatorContactInfoKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC RightsUsageTerms = new CGImagePropertyIPTC("RightsUsageTermsKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTC Scene = new CGImagePropertyIPTC("SceneKey");
    
    private static CGImagePropertyIPTC[] values = new CGImagePropertyIPTC[] {ObjectTypeReference, ObjectAttributeReference, 
        ObjectName, EditStatus, EditorialUpdate, Urgency, SubjectReference, Category, SupplementalCategory, FixtureIdentifier, 
        Keywords, ContentLocationCode, ContentLocationName, ReleaseDate, ReleaseTime, ExpirationDate, ExpirationTime, SpecialInstructions, 
        ActionAdvised, ReferenceService, ReferenceDate, ReferenceNumber, DateCreated, TimeCreated, DigitalCreationDate, DigitalCreationTime, 
        OriginatingProgram, ProgramVersion, ObjectCycle, Byline, BylineTitle, City, SubLocation, ProvinceState, CountryPrimaryLocationCode, 
        CountryPrimaryLocationName, OriginalTransmissionReference, Headline, Credit, Source, CopyrightNotice, Contact, CaptionAbstract, 
        WriterEditor, ImageType, ImageOrientation, LanguageIdentifier, StarRating, CreatorContactInfo, RightsUsageTerms, Scene};
    private final LazyGlobalValue<CFString> lazyGlobalValue;
    
    private CGImagePropertyIPTC(String getterName) {
        lazyGlobalValue = new LazyGlobalValue<>(getClass(), getterName);
    }
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFString value() {
        return lazyGlobalValue.value();
    }
    
    public static CGImagePropertyIPTC valueOf(CFString value) {
        for (CGImagePropertyIPTC v : values) {
            if (v.value().equals(value)) {
                return v;
            }
        }
        throw new IllegalArgumentException("No constant with value " + value + " found in " 
            + /*<name>*/CGImagePropertyIPTC/*</name>*/.class.getName());
    }
    /*<methods>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCObjectTypeReference", optional=true)
    protected static native CFString ObjectTypeReferenceKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCObjectAttributeReference", optional=true)
    protected static native CFString ObjectAttributeReferenceKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCObjectName", optional=true)
    protected static native CFString ObjectNameKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCEditStatus", optional=true)
    protected static native CFString EditStatusKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCEditorialUpdate", optional=true)
    protected static native CFString EditorialUpdateKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCUrgency", optional=true)
    protected static native CFString UrgencyKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCSubjectReference", optional=true)
    protected static native CFString SubjectReferenceKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCCategory", optional=true)
    protected static native CFString CategoryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCSupplementalCategory", optional=true)
    protected static native CFString SupplementalCategoryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCFixtureIdentifier", optional=true)
    protected static native CFString FixtureIdentifierKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCKeywords", optional=true)
    protected static native CFString KeywordsKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCContentLocationCode", optional=true)
    protected static native CFString ContentLocationCodeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCContentLocationName", optional=true)
    protected static native CFString ContentLocationNameKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCReleaseDate", optional=true)
    protected static native CFString ReleaseDateKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCReleaseTime", optional=true)
    protected static native CFString ReleaseTimeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCExpirationDate", optional=true)
    protected static native CFString ExpirationDateKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCExpirationTime", optional=true)
    protected static native CFString ExpirationTimeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCSpecialInstructions", optional=true)
    protected static native CFString SpecialInstructionsKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCActionAdvised", optional=true)
    protected static native CFString ActionAdvisedKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCReferenceService", optional=true)
    protected static native CFString ReferenceServiceKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCReferenceDate", optional=true)
    protected static native CFString ReferenceDateKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCReferenceNumber", optional=true)
    protected static native CFString ReferenceNumberKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCDateCreated", optional=true)
    protected static native CFString DateCreatedKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCTimeCreated", optional=true)
    protected static native CFString TimeCreatedKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCDigitalCreationDate", optional=true)
    protected static native CFString DigitalCreationDateKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCDigitalCreationTime", optional=true)
    protected static native CFString DigitalCreationTimeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCOriginatingProgram", optional=true)
    protected static native CFString OriginatingProgramKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCProgramVersion", optional=true)
    protected static native CFString ProgramVersionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCObjectCycle", optional=true)
    protected static native CFString ObjectCycleKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCByline", optional=true)
    protected static native CFString BylineKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCBylineTitle", optional=true)
    protected static native CFString BylineTitleKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCCity", optional=true)
    protected static native CFString CityKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCSubLocation", optional=true)
    protected static native CFString SubLocationKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCProvinceState", optional=true)
    protected static native CFString ProvinceStateKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCCountryPrimaryLocationCode", optional=true)
    protected static native CFString CountryPrimaryLocationCodeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCCountryPrimaryLocationName", optional=true)
    protected static native CFString CountryPrimaryLocationNameKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCOriginalTransmissionReference", optional=true)
    protected static native CFString OriginalTransmissionReferenceKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCHeadline", optional=true)
    protected static native CFString HeadlineKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCCredit", optional=true)
    protected static native CFString CreditKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCSource", optional=true)
    protected static native CFString SourceKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCCopyrightNotice", optional=true)
    protected static native CFString CopyrightNoticeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCContact", optional=true)
    protected static native CFString ContactKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCCaptionAbstract", optional=true)
    protected static native CFString CaptionAbstractKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCWriterEditor", optional=true)
    protected static native CFString WriterEditorKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCImageType", optional=true)
    protected static native CFString ImageTypeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCImageOrientation", optional=true)
    protected static native CFString ImageOrientationKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCLanguageIdentifier", optional=true)
    protected static native CFString LanguageIdentifierKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCStarRating", optional=true)
    protected static native CFString StarRatingKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCCreatorContactInfo", optional=true)
    protected static native CFString CreatorContactInfoKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCRightsUsageTerms", optional=true)
    protected static native CFString RightsUsageTermsKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCScene", optional=true)
    protected static native CFString SceneKey();
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyIPTCContactInfo.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyIPTCContactInfo.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImagePropertyIPTCContactInfo/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyIPTCContactInfo toObject(Class<CGImagePropertyIPTCContactInfo> cls, long handle, long flags) {
            CFString o = (CFString) CFType.Marshaler.toObject(CFString.class, handle, flags);
            if (o == null) {
                return null;
            }
            return CGImagePropertyIPTCContactInfo.valueOf(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyIPTCContactInfo o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.value(), flags);
        }
    }

    /*<ptr>*/
    /*</ptr>*/
    /*<bind>*/static { Bro.bind(CGImagePropertyIPTCContactInfo.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTCContactInfo City = new CGImagePropertyIPTCContactInfo("CityKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTCContactInfo Country = new CGImagePropertyIPTCContactInfo("CountryKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTCContactInfo Address = new CGImagePropertyIPTCContactInfo("AddressKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTCContactInfo PostalCode = new CGImagePropertyIPTCContactInfo("PostalCodeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTCContactInfo StateProvince = new CGImagePropertyIPTCContactInfo("StateProvinceKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTCContactInfo Emails = new CGImagePropertyIPTCContactInfo("EmailsKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTCContactInfo Phones = new CGImagePropertyIPTCContactInfo("PhonesKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyIPTCContactInfo WebURLs = new CGImagePropertyIPTCContactInfo("WebURLsKey");
    
    private static CGImagePropertyIPTCContactInfo[] values = new CGImagePropertyIPTCContactInfo[] {City, Country, Address, PostalCode, 
        StateProvince, Emails, Phones, WebURLs};
    private final LazyGlobalValue<CFString> lazyGlobalValue;
    
    private CGImagePropertyIPTCContactInfo(String getterName) {
        lazyGlobalValue = new LazyGlobalValue<>(getClass(), getterName);
    }
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFString value() {
        return lazyGlobalValue.value();
    }
    
    public static CGImagePropertyIPTCContactInfo valueOf(CFString value) {
        for (CGImagePropertyIPTCContactInfo v : values) {
            if (v.value().equals(value)) {
                return v;
            }
        }
        throw new IllegalArgumentException("No constant with value " + value + " found in " 
            + /*<name>*/CGImagePropertyIPTCContactInfo/*</name>*/.class.getName());
    }
    /*<methods>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCContactInfoCity", optional=true)
    protected static native CFString CityKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCContactInfoCountry", optional=true)
    protected static native CFString CountryKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCContactInfoAddress", optional=true)
    protected static native CFString AddressKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCContactInfoPostalCode", optional=true)
    protected static native CFString PostalCodeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCContactInfoStateProvince", optional=true)
    protected static native CFString StateProvinceKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCContactInfoEmails", optional=true)
    protected static native CFString EmailsKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCContactInfoPhones", optional=true)
    protected static native CFString PhonesKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyIPTCContactInfoWebURLs", optional=true)
    protected static native CFString WebURLsKey();
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyIPTCContactInfoData.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;

import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyIPTCContactInfoData.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImagePropertyIPTCContactInfoData/*</name>*/ 
    extends /*<extends>*/Object/*</extends>*/ 
    /*<implements>*//*</implements>*/ {
    
    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyIPTCContactInfoData toObject(Class<CGImagePropertyIPTCContactInfoData> cls, long handle, long flags) {
            CFDictionary o = (CFDictionary) CFType.Marshaler.toObject(CFDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CGImagePropertyIPTCContactInfoData(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyIPTCContactInfoData o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.data, flags);
        }
    }

    /*<ptr>*/
    /*</ptr>*/
    private CFDictionary data;
    
    protected CGImagePropertyIPTCContactInfoData(CFDictionary data) {
        this.data = data;
    }
    public CGImagePropertyIPTCContactInfoData() {
        this.data = CFMutableDictionary.create();
    }
    /*<bind>*/static { Bro.bind(CGImagePropertyIPTCContactInfoData.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFDictionary getDictionary() {
        return data;
    }
    
    public boolean has(CGImagePropertyIPTCContactInfo property) {
        return data.containsKey(property.value());
    }
    
    public String getString(CGImagePropertyIPTCContactInfo property) {
        if (has(property)) {
            CFString val = data.get(property.value(), CFString.class);
            return val.toString();
        }
        return null;
    }
    public double getNumber(CGImagePropertyIPTCContactInfo property) {
        if (has(property)) {
            CFNumber val = data.get(property.value(), CFNumber.class);
            return val.doubleValue();
        }
        return 0;
    }
    public CGImagePropertyIPTCContactInfoData set(CGImagePropertyIPTCContactInfo property, String value) {
        data.put(property.value(), new CFString(value));
        return this;
    }
    public CGImagePropertyIPTCContactInfoData set(CGImagePropertyIPTCContactInfo property, double value) {
        data.put(property.value(), CFNumber.valueOf(value));
        return this;
    }
    /*<methods>*/
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyIPTCData.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;

import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyIPTCData.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class CGImagePropertyIPTCData 
    extends /*<extends>*/Object/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyIPTCData toObject(Class<CGImagePropertyIPTCData> cls, long handle, long flags) {
            CFDictionary o = (CFDictionary) CFType.Marshaler.toObject(CFDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CGImagePropertyIPTCData(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyIPTCData o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private CFDictionary data;
    
    protected CGImagePropertyIPTCData(CFDictionary data) {
        this.data = data;
    }
    public CGImagePropertyIPTCData() {
        this.data = CFMutableDictionary.create();
    }
    /*<bind>*/static { Bro.bind(CGImagePropertyIPTCData.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFDictionary getDictionary() {
        return data;
    }
    
    public boolean has(CGImagePropertyIPTC property) {
        return data.containsKey(property.value());
    }
    
    public String getString(CGImagePropertyIPTC property) {
        if (has(property)) {
            CFString val = data.get(property.value(), CFString.class);
            return val.toString();
        }
        return null;
    }
    public double getNumber(CGImagePropertyIPTC property) {
        if (has(property)) {
            CFNumber val = data.get(property.value(), CFNumber.class);
            return val.doubleValue();
        }
        return 0;
    }
    public CGImagePropertyIPTCData set(CGImagePropertyIPTC property, String value) {
        data.put(property.value(), new CFString(value));
        return this;
    }
    public CGImagePropertyIPTCData set(CGImagePropertyIPTC property, double value) {
        data.put(property.value(), CFNumber.valueOf(value));
        return this;
    }
    
    
    public CGImagePropertyIPTCContactInfoData getContactInfo() {
        if (has(CGImagePropertyIPTC.CreatorContactInfo)) {
            CFDictionary val = data.get(CGImagePropertyIPTC.CreatorContactInfoKey(), CFDictionary.class);
            return new CGImagePropertyIPTCContactInfoData(val);
        }
        return null;
    }
    public CGImagePropertyIPTCData setContactInfo(CGImagePropertyIPTCContactInfoData contactInfo) {
        data.put(CGImagePropertyIPTC.CreatorContactInfoKey(), contactInfo.getDictionary());
        return this;
    }
    /*<methods>*/
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyJFIF.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyJFIF.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImagePropertyJFIF/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyJFIF toObject(Class<CGImagePropertyJFIF> cls, long handle, long flags) {
            CFString o = (CFString) CFType.Marshaler.toObject(CFString.class, handle, flags);
            if (o == null) {
                return null;
            }
            return CGImagePropertyJFIF.valueOf(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyJFIF o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.value(), flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    /*<bind>*/static { Bro.bind(CGImagePropertyJFIF.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyJFIF Version = new CGImagePropertyJFIF("VersionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyJFIF XDensity = new CGImagePropertyJFIF("XDensityKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyJFIF YDensity = new CGImagePropertyJFIF("YDensityKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyJFIF DensityUnit = new CGImagePropertyJFIF("DensityUnitKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyJFIF IsProgressive = new CGImagePropertyJFIF("IsProgressiveKey");
    
    private static CGImagePropertyJFIF[] values = new CGImagePropertyJFIF[] {Version, XDensity, YDensity, DensityUnit, IsProgressive};
    private final LazyGlobalValue<CFString> lazyGlobalValue;
    
    private CGImagePropertyJFIF(String getterName) {
        lazyGlobalValue = new LazyGlobalValue<>(getClass(), getterName);
    }
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFString value() {
        return lazyGlobalValue.value();
    }
    
    public static CGImagePropertyJFIF valueOf(CFString value) {
        for (CGImagePropertyJFIF v : values) {
            if (v.value().equals(value)) {
                return v;
            }
        }
        throw new IllegalArgumentException("No constant with value " + value + " found in " 
            + /*<name>*/CGImagePropertyJFIF/*</name>*/.class.getName());
    }
    /*<methods>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyJFIFVersion", optional=true)
    protected static native CFString VersionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyJFIFXDensity", optional=true)
    protected static native CFString XDensityKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyJFIFYDensity", optional=true)
    protected static native CFString YDensityKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyJFIFDensityUnit", optional=true)
    protected static native CFString DensityUnitKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyJFIFIsProgressive", optional=true)
    protected static native CFString IsProgressiveKey();
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyJFIFData.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;

import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyJFIFData.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class CGImagePropertyJFIFData 
    extends /*<extends>*/Object/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyJFIFData toObject(Class<CGImagePropertyJFIFData> cls, long handle, long flags) {
            CFDictionary o = (CFDictionary) CFType.Marshaler.toObject(CFDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CGImagePropertyJFIFData(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyJFIFData o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private CFDictionary data;
    
    protected CGImagePropertyJFIFData(CFDictionary data) {
        this.data = data;
    }
    public CGImagePropertyJFIFData() {
        this.data = CFMutableDictionary.create();
    }
    /*<bind>*/static { Bro.bind(CGImagePropertyJFIFData.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFDictionary getDictionary() {
        return data;
    }
    
    public boolean has(CGImagePropertyJFIF property) {
        return data.containsKey(property.value());
    }
    
    public String getString(CGImagePropertyJFIF property) {
        if (has(property)) {
            CFString val = data.get(property.value(), CFString.class);
            return val.toString();
        }
        return null;
    }
    public double getNumber(CGImagePropertyJFIF property) {
        if (has(property)) {
            CFNumber val = data.get(property.value(), CFNumber.class);
            return val.doubleValue();
        }
        return 0;
    }
    public CGImagePropertyJFIFData set(CGImagePropertyJFIF property, String value) {
        data.put(property.value(), new CFString(value));
        return this;
    }
    public CGImagePropertyJFIFData set(CGImagePropertyJFIF property, double value) {
        data.put(property.value(), CFNumber.valueOf(value));
        return this;
    }
    /*<methods>*/
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyNikon.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyNikon.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImagePropertyNikon/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {
    
    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyNikon toObject(Class<CGImagePropertyNikon> cls, long handle, long flags) {
            CFString o = (CFString) CFType.Marshaler.toObject(CFString.class, handle, flags);
            if (o == null) {
                return null;
            }
            return CGImagePropertyNikon.valueOf(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyNikon o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.value(), flags);
        }
    }

    /*<ptr>*/
    /*</ptr>*/
    /*<bind>*/static { Bro.bind(CGImagePropertyNikon.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyNikon ISOSetting = new CGImagePropertyNikon("ISOSettingKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyNikon ColorMode = new CGImagePropertyNikon("ColorModeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyNikon Quality = new CGImagePropertyNikon("QualityKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyNikon WhiteBalanceMode = new CGImagePropertyNikon("WhiteBalanceModeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyNikon SharpenMode = new CGImagePropertyNikon("SharpenModeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyNikon FocusMode = new CGImagePropertyNikon("FocusModeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyNikon FlashSetting = new CGImagePropertyNikon("FlashSettingKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyNikon ISOSelection = new CGImagePropertyNikon("ISOSelectionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyNikon FlashExposureComp = new CGImagePropertyNikon("FlashExposureCompKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyNikon ImageAdjustment = new CGImagePropertyNikon("ImageAdjustmentKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyNikon LensAdapter = new CGImagePropertyNikon("LensAdapterKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyNikon LensType = new CGImagePropertyNikon("LensTypeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyNikon LensInfo = new CGImagePropertyNikon("LensInfoKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyNikon FocusDistance = new CGImagePropertyNikon("FocusDistanceKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyNikon DigitalZoom = new CGImagePropertyNikon("DigitalZoomKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyNikon ShootingMode = new CGImagePropertyNikon("ShootingModeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyNikon CameraSerialNumber = new CGImagePropertyNikon("CameraSerialNumberKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyNikon ShutterCount = new CGImagePropertyNikon("ShutterCountKey");
    
    private static CGImagePropertyNikon[] values = new CGImagePropertyNikon[] {ISOSetting, ColorMode, Quality, 
        WhiteBalanceMode, SharpenMode, FocusMode, FlashSetting, ISOSelection, FlashExposureComp, ImageAdjustment, 
        LensAdapter, LensType, LensInfo, FocusDistance, DigitalZoom, ShootingMode, CameraSerialNumber, ShutterCount};
    private final LazyGlobalValue<CFString> lazyGlobalValue;
    
    private CGImagePropertyNikon(String getterName) {
        lazyGlobalValue = new LazyGlobalValue<>(getClass(), getterName);
    }
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFString value() {
        return lazyGlobalValue.value();
    }
    
    public static CGImagePropertyNikon valueOf(CFString value) {
        for (CGImagePropertyNikon v : values) {
            if (v.value().equals(value)) {
                return v;
            }
        }
        throw new IllegalArgumentException("No constant with value " + value + " found in " 
            + /*<name>*/CGImagePropertyNikon/*</name>*/.class.getName());
    }
    /*<methods>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerNikonISOSetting", optional=true)
    protected static native CFString ISOSettingKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerNikonColorMode", optional=true)
    protected static native CFString ColorModeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerNikonQuality", optional=true)
    protected static native CFString QualityKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerNikonWhiteBalanceMode", optional=true)
    protected static native CFString WhiteBalanceModeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerNikonSharpenMode", optional=true)
    protected static native CFString SharpenModeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerNikonFocusMode", optional=true)
    protected static native CFString FocusModeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerNikonFlashSetting", optional=true)
    protected static native CFString FlashSettingKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerNikonISOSelection", optional=true)
    protected static native CFString ISOSelectionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerNikonFlashExposureComp", optional=true)
    protected static native CFString FlashExposureCompKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerNikonImageAdjustment", optional=true)
    protected static native CFString ImageAdjustmentKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerNikonLensAdapter", optional=true)
    protected static native CFString LensAdapterKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerNikonLensType", optional=true)
    protected static native CFString LensTypeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerNikonLensInfo", optional=true)
    protected static native CFString LensInfoKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerNikonFocusDistance", optional=true)
    protected static native CFString FocusDistanceKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerNikonDigitalZoom", optional=true)
    protected static native CFString DigitalZoomKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerNikonShootingMode", optional=true)
    protected static native CFString ShootingModeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerNikonCameraSerialNumber", optional=true)
    protected static native CFString CameraSerialNumberKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyMakerNikonShutterCount", optional=true)
    protected static native CFString ShutterCountKey();
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyNikonData.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;

import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyNikonData.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class CGImagePropertyNikonData 
    extends /*<extends>*/Object/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyNikonData toObject(Class<CGImagePropertyNikonData> cls, long handle, long flags) {
            CFDictionary o = (CFDictionary) CFType.Marshaler.toObject(CFDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CGImagePropertyNikonData(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyNikonData o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private CFDictionary data;
    
    protected CGImagePropertyNikonData(CFDictionary data) {
        this.data = data;
    }
    public CGImagePropertyNikonData() {
        this.data = CFMutableDictionary.create();
    }
    /*<bind>*/static { Bro.bind(CGImagePropertyNikonData.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFDictionary getDictionary() {
        return data;
    }
    
    public boolean has(CGImagePropertyNikon property) {
        return data.containsKey(property.value());
    }
    
    public String getString(CGImagePropertyNikon property) {
        if (has(property)) {
            CFString val = data.get(property.value(), CFString.class);
            return val.toString();
        }
        return null;
    }
    public double getNumber(CGImagePropertyNikon property) {
        if (has(property)) {
            CFNumber val = data.get(property.value(), CFNumber.class);
            return val.doubleValue();
        }
        return 0;
    }
    public CGImagePropertyNikonData set(CGImagePropertyNikon property, String value) {
        data.put(property.value(), new CFString(value));
        return this;
    }
    public CGImagePropertyNikonData set(CGImagePropertyNikon property, double value) {
        data.put(property.value(), CFNumber.valueOf(value));
        return this;
    }
    /*<methods>*/
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyPNG.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyPNG.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImagePropertyPNG/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {
    
    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyPNG toObject(Class<CGImagePropertyPNG> cls, long handle, long flags) {
            CFString o = (CFString) CFType.Marshaler.toObject(CFString.class, handle, flags);
            if (o == null) {
                return null;
            }
            return CGImagePropertyPNG.valueOf(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyPNG o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.value(), flags);
        }
    }

    /*<ptr>*/
    /*</ptr>*/
    /*<bind>*/static { Bro.bind(CGImagePropertyPNG.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyPNG Gamma = new CGImagePropertyPNG("GammaKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyPNG InterlaceType = new CGImagePropertyPNG("InterlaceTypeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyPNG XPixelsPerMeter = new CGImagePropertyPNG("XPixelsPerMeterKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyPNG YPixelsPerMeter = new CGImagePropertyPNG("YPixelsPerMeterKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyPNG sRGBIntent = new CGImagePropertyPNG("sRGBIntentKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyPNG Chromaticities = new CGImagePropertyPNG("ChromaticitiesKey");
    /**
     * @since Available in iOS 5.0 and later.
     */
    public static final CGImagePropertyPNG Author = new CGImagePropertyPNG("AuthorKey");
    /**
     * @since Available in iOS 5.0 and later.
     */
    public static final CGImagePropertyPNG Copyright = new CGImagePropertyPNG("CopyrightKey");
    /**
     * @since Available in iOS 5.0 and later.
     */
    public static final CGImagePropertyPNG CreationTime = new CGImagePropertyPNG("CreationTimeKey");
    /**
     * @since Available in iOS 5.0 and later.
     */
    public static final CGImagePropertyPNG Description = new CGImagePropertyPNG("DescriptionKey");
    /**
     * @since Available in iOS 5.0 and later.
     */
    public static final CGImagePropertyPNG ModificationTime = new CGImagePropertyPNG("ModificationTimeKey");
    /**
     * @since Available in iOS 5.0 and later.
     */
    public static final CGImagePropertyPNG Software = new CGImagePropertyPNG("SoftwareKey");
    /**
     * @since Available in iOS 5.0 and later.
     */
    public static final CGImagePropertyPNG Title = new CGImagePropertyPNG("TitleKey");
    /**
     * @since Available in iOS 8.0 and later.
     */
    public static final CGImagePropertyPNG LoopCount = new CGImagePropertyPNG("LoopCountKey");
    /**
     * @since Available in iOS 8.0 and later.
     */
    public static final CGImagePropertyPNG DelayTime = new CGImagePropertyPNG("DelayTimeKey");
    /**
     * @since Available in iOS 8.0 and later.
     */
    public static final CGImagePropertyPNG UnclampedDelayTime = new CGImagePropertyPNG("UnclampedDelayTimeKey");
    
    private static CGImagePropertyPNG[] values = new CGImagePropertyPNG[] {Gamma, InterlaceType, XPixelsPerMeter, YPixelsPerMeter, 
        sRGBIntent, Chromaticities, Author, Copyright, CreationTime, Description, ModificationTime, Software, Title, LoopCount, 
        DelayTime, UnclampedDelayTime};
    private final LazyGlobalValue<CFString> lazyGlobalValue;
    
    private CGImagePropertyPNG(String getterName) {
        lazyGlobalValue = new LazyGlobalValue<>(getClass(), getterName);
    }
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFString value() {
        return lazyGlobalValue.value();
    }
    
    public static CGImagePropertyPNG valueOf(CFString value) {
        for (CGImagePropertyPNG v : values) {
            if (v.value().equals(value)) {
                return v;
            }
        }
        throw new IllegalArgumentException("No constant with value " + value + " found in " 
            + /*<name>*/CGImagePropertyPNG/*</name>*/.class.getName());
    }
    /*<methods>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyPNGGamma", optional=true)
    protected static native CFString GammaKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyPNGInterlaceType", optional=true)
    protected static native CFString InterlaceTypeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyPNGXPixelsPerMeter", optional=true)
    protected static native CFString XPixelsPerMeterKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyPNGYPixelsPerMeter", optional=true)
    protected static native CFString YPixelsPerMeterKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyPNGsRGBIntent", optional=true)
    protected static native CFString sRGBIntentKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyPNGChromaticities", optional=true)
    protected static native CFString ChromaticitiesKey();
    /**
     * @since Available in iOS 5.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyPNGAuthor", optional=true)
    protected static native CFString AuthorKey();
    /**
     * @since Available in iOS 5.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyPNGCopyright", optional=true)
    protected static native CFString CopyrightKey();
    /**
     * @since Available in iOS 5.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyPNGCreationTime", optional=true)
    protected static native CFString CreationTimeKey();
    /**
     * @since Available in iOS 5.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyPNGDescription", optional=true)
    protected static native CFString DescriptionKey();
    /**
     * @since Available in iOS 5.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyPNGModificationTime", optional=true)
    protected static native CFString ModificationTimeKey();
    /**
     * @since Available in iOS 5.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyPNGSoftware", optional=true)
    protected static native CFString SoftwareKey();
    /**
     * @since Available in iOS 5.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyPNGTitle", optional=true)
    protected static native CFString TitleKey();
    /**
     * @since Available in iOS 8.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyAPNGLoopCount", optional=true)
    protected static native CFString LoopCountKey();
    /**
     * @since Available in iOS 8.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyAPNGDelayTime", optional=true)
    protected static native CFString DelayTimeKey();
    /**
     * @since Available in iOS 8.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyAPNGUnclampedDelayTime", optional=true)
    protected static native CFString UnclampedDelayTimeKey();
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyPNGData.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;

import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyPNGData.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class CGImagePropertyPNGData 
    extends /*<extends>*/Object/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyPNGData toObject(Class<CGImagePropertyPNGData> cls, long handle, long flags) {
            CFDictionary o = (CFDictionary) CFType.Marshaler.toObject(CFDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CGImagePropertyPNGData(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyPNGData o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private CFDictionary data;
    
    protected CGImagePropertyPNGData(CFDictionary data) {
        this.data = data;
    }
    public CGImagePropertyPNGData() {
        this.data = CFMutableDictionary.create();
    }
    /*<bind>*/static { Bro.bind(CGImagePropertyPNGData.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFDictionary getDictionary() {
        return data;
    }
    
    public boolean has(CGImagePropertyPNG property) {
        return data.containsKey(property.value());
    }
    
    public String getString(CGImagePropertyPNG property) {
        if (has(property)) {
            CFString val = data.get(property.value(), CFString.class);
            return val.toString();
        }
        return null;
    }
    public double getNumber(CGImagePropertyPNG property) {
        if (has(property)) {
            CFNumber val = data.get(property.value(), CFNumber.class);
            return val.doubleValue();
        }
        return 0;
    }
    public CGImagePropertyPNGData set(CGImagePropertyPNG property, String value) {
        data.put(property.value(), new CFString(value));
        return this;
    }
    public CGImagePropertyPNGData set(CGImagePropertyPNG property, double value) {
        data.put(property.value(), CFNumber.valueOf(value));
        return this;
    }
    /*<methods>*/
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyTIFF.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyTIFF.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImagePropertyTIFF/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {
    
    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyTIFF toObject(Class<CGImagePropertyTIFF> cls, long handle, long flags) {
            CFString o = (CFString) CFType.Marshaler.toObject(CFString.class, handle, flags);
            if (o == null) {
                return null;
            }
            return CGImagePropertyTIFF.valueOf(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyTIFF o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.value(), flags);
        }
    }

    /*<ptr>*/
    /*</ptr>*/
    /*<bind>*/static { Bro.bind(CGImagePropertyTIFF.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyTIFF Compression = new CGImagePropertyTIFF("CompressionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyTIFF PhotometricInterpretation = new CGImagePropertyTIFF("PhotometricInterpretationKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyTIFF DocumentName = new CGImagePropertyTIFF("DocumentNameKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyTIFF ImageDescription = new CGImagePropertyTIFF("ImageDescriptionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyTIFF Make = new CGImagePropertyTIFF("MakeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyTIFF Model = new CGImagePropertyTIFF("ModelKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyTIFF Orientation = new CGImagePropertyTIFF("OrientationKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyTIFF XResolution = new CGImagePropertyTIFF("XResolutionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyTIFF YResolution = new CGImagePropertyTIFF("YResolutionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyTIFF ResolutionUnit = new CGImagePropertyTIFF("ResolutionUnitKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyTIFF Software = new CGImagePropertyTIFF("SoftwareKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyTIFF TransferFunction = new CGImagePropertyTIFF("TransferFunctionKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyTIFF DateTime = new CGImagePropertyTIFF("DateTimeKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyTIFF Artist = new CGImagePropertyTIFF("ArtistKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyTIFF HostComputer = new CGImagePropertyTIFF("HostComputerKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyTIFF Copyright = new CGImagePropertyTIFF("CopyrightKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyTIFF WhitePoint = new CGImagePropertyTIFF("WhitePointKey");
    /**
     * @since Available in iOS 4.0 and later.
     */
    public static final CGImagePropertyTIFF PrimaryChromaticities = new CGImagePropertyTIFF("PrimaryChromaticitiesKey");
    
    private static CGImagePropertyTIFF[] values = new CGImagePropertyTIFF[] {Compression, PhotometricInterpretation, DocumentName, 
        ImageDescription, Make, Model, Orientation, XResolution, YResolution, ResolutionUnit, Software, TransferFunction, 
        DateTime, Artist, HostComputer, Copyright, WhitePoint, PrimaryChromaticities};
    private final LazyGlobalValue<CFString> lazyGlobalValue;
    
    private CGImagePropertyTIFF(String getterName) {
        lazyGlobalValue = new LazyGlobalValue<>(getClass(), getterName);
    }
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFString value() {
        return lazyGlobalValue.value();
    }
    
    public static CGImagePropertyTIFF valueOf(CFString value) {
        for (CGImagePropertyTIFF v : values) {
            if (v.value().equals(value)) {
                return v;
            }
        }
        throw new IllegalArgumentException("No constant with value " + value + " found in " 
            + /*<name>*/CGImagePropertyTIFF/*</name>*/.class.getName());
    }
    /*<methods>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyTIFFCompression", optional=true)
    protected static native CFString CompressionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyTIFFPhotometricInterpretation", optional=true)
    protected static native CFString PhotometricInterpretationKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyTIFFDocumentName", optional=true)
    protected static native CFString DocumentNameKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyTIFFImageDescription", optional=true)
    protected static native CFString ImageDescriptionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyTIFFMake", optional=true)
    protected static native CFString MakeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyTIFFModel", optional=true)
    protected static native CFString ModelKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyTIFFOrientation", optional=true)
    protected static native CFString OrientationKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyTIFFXResolution", optional=true)
    protected static native CFString XResolutionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyTIFFYResolution", optional=true)
    protected static native CFString YResolutionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyTIFFResolutionUnit", optional=true)
    protected static native CFString ResolutionUnitKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyTIFFSoftware", optional=true)
    protected static native CFString SoftwareKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyTIFFTransferFunction", optional=true)
    protected static native CFString TransferFunctionKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyTIFFDateTime", optional=true)
    protected static native CFString DateTimeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyTIFFArtist", optional=true)
    protected static native CFString ArtistKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyTIFFHostComputer", optional=true)
    protected static native CFString HostComputerKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyTIFFCopyright", optional=true)
    protected static native CFString CopyrightKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyTIFFWhitePoint", optional=true)
    protected static native CFString WhitePointKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImagePropertyTIFFPrimaryChromaticities", optional=true)
    protected static native CFString PrimaryChromaticitiesKey();
    /*</methods>*/
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImagePropertyTIFFData.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;

import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImagePropertyTIFFData.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class CGImagePropertyTIFFData 
    extends /*<extends>*/Object/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImagePropertyTIFFData toObject(Class<CGImagePropertyTIFFData> cls, long handle, long flags) {
            CFDictionary o = (CFDictionary) CFType.Marshaler.toObject(CFDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CGImagePropertyTIFFData(o);
        }
        @MarshalsPointer
        public static long toNative(CGImagePropertyTIFFData o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private CFDictionary data;
    
    protected CGImagePropertyTIFFData(CFDictionary data) {
        this.data = data;
    }
    public CGImagePropertyTIFFData() {
        this.data = CFMutableDictionary.create();
    }
    /*<bind>*/static { Bro.bind(CGImagePropertyTIFFData.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFDictionary getDictionary() {
        return data;
    }
    
    public boolean has(CGImagePropertyTIFF property) {
        return data.containsKey(property.value());
    }
    
    public String getString(CGImagePropertyTIFF property) {
        if (has(property)) {
            CFString val = data.get(property.value(), CFString.class);
            return val.toString();
        }
        return null;
    }
    public double getNumber(CGImagePropertyTIFF property) {
        if (has(property)) {
            CFNumber val = data.get(property.value(), CFNumber.class);
            return val.doubleValue();
        }
        return 0;
    }
    public CGImagePropertyTIFFData set(CGImagePropertyTIFF property, String value) {
        data.put(property.value(), new CFString(value));
        return this;
    }
    public CGImagePropertyTIFFData set(CGImagePropertyTIFF property, double value) {
        data.put(property.value(), CFNumber.valueOf(value));
        return this;
    }
    /*<methods>*/
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}


File: cocoatouch/src/main/java/org/robovm/apple/imageio/CGImageSourceOptions.java
/*
 * Copyright (C) 2013-2015 RoboVM AB
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
package org.robovm.apple.imageio;

/*<imports>*/
import java.io.*;
import java.nio.*;
import java.util.*;
import org.robovm.objc.*;
import org.robovm.objc.annotation.*;
import org.robovm.objc.block.*;
import org.robovm.rt.*;
import org.robovm.rt.annotation.*;
import org.robovm.rt.bro.*;
import org.robovm.rt.bro.annotation.*;
import org.robovm.rt.bro.ptr.*;
import org.robovm.apple.foundation.*;
import org.robovm.apple.corefoundation.*;
import org.robovm.apple.coregraphics.*;
/*</imports>*/

/*<javadoc>*/
/*</javadoc>*/
@Marshaler(CGImageSourceOptions.Marshaler.class)
/*<annotations>*/@Library("ImageIO")/*</annotations>*/
/*<visibility>*/public/*</visibility>*/ class /*<name>*/CGImageSourceOptions/*</name>*/ 
    extends /*<extends>*/CocoaUtility/*</extends>*/ 
    /*<implements>*//*</implements>*/ {

    public static class Marshaler {
        @MarshalsPointer
        public static CGImageSourceOptions toObject(Class<CGImageSourceOptions> cls, long handle, long flags) {
            CFDictionary o = (CFDictionary) CFType.Marshaler.toObject(CFDictionary.class, handle, flags);
            if (o == null) {
                return null;
            }
            return new CGImageSourceOptions(o);
        }
        @MarshalsPointer
        public static long toNative(CGImageSourceOptions o, long flags) {
            if (o == null) {
                return 0L;
            }
            return CFType.Marshaler.toNative(o.data, flags);
        }
    }
    
    /*<ptr>*/
    /*</ptr>*/
    private CFDictionary data;
    
    protected CGImageSourceOptions(CFDictionary data) {
        this.data = data;
    }
    public CGImageSourceOptions() {
        this.data = CFMutableDictionary.create();
    }
    /*<bind>*/static { Bro.bind(CGImageSourceOptions.class); }/*</bind>*/
    /*<constants>*//*</constants>*/
    /*<constructors>*//*</constructors>*/
    /*<properties>*//*</properties>*/
    /*<members>*//*</members>*/
    public CFDictionary getDictionary() {
        return data;
    }
    
    
    /**
     * @since Available in iOS 4.0 and later.
     */
    public String getTypeIdentifierHint() {
        if (data.containsKey(TypeIdentifierHintKey())) {
            CFString val = data.get(TypeIdentifierHintKey(), CFString.class);
            return val.toString();
        }
        return null;
    }
    /**
     * @since Available in iOS 4.0 and later.
     */
    public CGImageSourceOptions setTypeIdentifierHint(String typeIdentifier) {
        data.put(TypeIdentifierHintKey(), new CFString(typeIdentifier));
        return this;
    }
    /**
     * @since Available in iOS 4.0 and later.
     */
    public boolean shouldCache() {
        if (data.containsKey(ShouldCacheKey())) {
            CFBoolean val = data.get(ShouldCacheKey(), CFBoolean.class);
            return val.booleanValue();
        }
        return false;
    }
    /**
     * @since Available in iOS 4.0 and later.
     */
    public CGImageSourceOptions setShouldCache(boolean cache) {
        data.put(ShouldCacheKey(), CFBoolean.valueOf(cache));
        return this;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public boolean shouldCacheImmediately() {
        if (data.containsKey(ShouldCacheImmediatelyKey())) {
            CFBoolean val = data.get(ShouldCacheImmediatelyKey(), CFBoolean.class);
            return val.booleanValue();
        }
        return false;
    }
    /**
     * @since Available in iOS 7.0 and later.
     */
    public CGImageSourceOptions setShouldCacheImmediately(boolean cache) {
        data.put(ShouldCacheImmediatelyKey(), CFBoolean.valueOf(cache));
        return this;
    }
    /**
     * @since Available in iOS 4.0 and later.
     */
    public boolean shouldAllowFloat() {
        if (data.containsKey(ShouldAllowFloatKey())) {
            CFBoolean val = data.get(ShouldAllowFloatKey(), CFBoolean.class);
            return val.booleanValue();
        }
        return false;
    }
    /**
     * @since Available in iOS 4.0 and later.
     */
    public CGImageSourceOptions setShouldAllowFloat(boolean allowFloat) {
        data.put(ShouldAllowFloatKey(), CFBoolean.valueOf(allowFloat));
        return this;
    }
    /**
     * @since Available in iOS 4.0 and later.
     */
    public boolean shouldCreateThumbnailFromImageIfAbsent() {
        if (data.containsKey(CreateThumbnailFromImageIfAbsentKey())) {
            CFBoolean val = data.get(CreateThumbnailFromImageIfAbsentKey(), CFBoolean.class);
            return val.booleanValue();
        }
        return false;
    }
    /**
     * @since Available in iOS 4.0 and later.
     */
    public CGImageSourceOptions setShouldCreateThumbnailFromImageIfAbsent(boolean createThumbnail) {
        data.put(CreateThumbnailFromImageIfAbsentKey(), CFBoolean.valueOf(createThumbnail));
        return this;
    }
    /**
     * @since Available in iOS 4.0 and later.
     */
    public boolean shouldCreateThumbnailFromImageAlways() {
        if (data.containsKey(CreateThumbnailFromImageAlwaysKey())) {
            CFBoolean val = data.get(CreateThumbnailFromImageAlwaysKey(), CFBoolean.class);
            return val.booleanValue();
        }
        return false;
    }
    /**
     * @since Available in iOS 4.0 and later.
     */
    public CGImageSourceOptions setShouldCreateThumbnailFromImageAlways(boolean createThumbnail) {
        data.put(CreateThumbnailFromImageAlwaysKey(), CFBoolean.valueOf(createThumbnail));
        return this;
    }
    /**
     * @since Available in iOS 4.0 and later.
     */
    public long getThumbnailMaxPixelSize() {
        if (data.containsKey(ThumbnailMaxPixelSizeKey())) {
            CFNumber val = data.get(ThumbnailMaxPixelSizeKey(), CFNumber.class);
            return val.longValue();
        }
        return 0;
    }
    /**
     * @since Available in iOS 4.0 and later.
     */
    public CGImageSourceOptions setThumbnailMaxPixelSize(long maxSize) {
        data.put(ThumbnailMaxPixelSizeKey(), CFNumber.valueOf(maxSize));
        return this;
    }
    /**
     * @since Available in iOS 4.0 and later.
     */
    public boolean shouldCreateThumbnailWithTransform() {
        if (data.containsKey(CreateThumbnailWithTransformKey())) {
            CFBoolean val = data.get(CreateThumbnailWithTransformKey(), CFBoolean.class);
            return val.booleanValue();
        }
        return false;
    }
    /**
     * @since Available in iOS 4.0 and later.
     */
    public CGImageSourceOptions setShouldCreateThumbnailWithTransform(boolean transform) {
        data.put(CreateThumbnailWithTransformKey(), CFBoolean.valueOf(transform));
        return this;
    }
    /*<methods>*/
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImageSourceTypeIdentifierHint", optional=true)
    protected static native CFString TypeIdentifierHintKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImageSourceShouldCache", optional=true)
    protected static native CFString ShouldCacheKey();
    /**
     * @since Available in iOS 7.0 and later.
     */
    @GlobalValue(symbol="kCGImageSourceShouldCacheImmediately", optional=true)
    protected static native CFString ShouldCacheImmediatelyKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImageSourceShouldAllowFloat", optional=true)
    protected static native CFString ShouldAllowFloatKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImageSourceCreateThumbnailFromImageIfAbsent", optional=true)
    protected static native CFString CreateThumbnailFromImageIfAbsentKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImageSourceCreateThumbnailFromImageAlways", optional=true)
    protected static native CFString CreateThumbnailFromImageAlwaysKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImageSourceThumbnailMaxPixelSize", optional=true)
    protected static native CFString ThumbnailMaxPixelSizeKey();
    /**
     * @since Available in iOS 4.0 and later.
     */
    @GlobalValue(symbol="kCGImageSourceCreateThumbnailWithTransform", optional=true)
    protected static native CFString CreateThumbnailWithTransformKey();
    /*</methods>*/
    @Override
    public String toString() {
        if (data != null) return data.toString();
        return super.toString();
    }
}
