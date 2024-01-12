Refactoring Types: ['Extract Method', 'Extract Interface']
ght (C) 2006 The Android Open Source Project
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

package android.app;

import android.app.usage.IUsageStatsManager;
import android.app.usage.UsageStatsManager;
import android.appwidget.AppWidgetManager;
import android.content.res.IThemeService;
import android.content.res.ThemeManager;
import android.hardware.ITorchService;
import android.hardware.TorchManager;
import android.os.Build;
import android.service.persistentdata.IPersistentDataBlockService;
import android.service.persistentdata.PersistentDataBlockManager;

import com.android.internal.appwidget.IAppWidgetService;
import com.android.internal.policy.PolicyManager;
import com.android.internal.util.Preconditions;

import android.bluetooth.BluetoothManager;
import android.content.BroadcastReceiver;
import android.content.ComponentName;
import android.content.ContentProvider;
import android.content.ContentResolver;
import android.content.Context;
import android.content.ContextWrapper;
import android.content.IContentProvider;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.IIntentReceiver;
import android.content.IntentSender;
import android.content.IRestrictionsManager;
import android.content.ReceiverCallNotAllowedException;
import android.content.RestrictionsManager;
import android.content.ServiceConnection;
import android.content.SharedPreferences;
import android.content.pm.ApplicationInfo;
import android.content.pm.ILauncherApps;
import android.content.pm.IPackageManager;
import android.content.pm.LauncherApps;
import android.content.pm.PackageManager;
import android.content.pm.PackageManager.NameNotFoundException;
import android.content.res.AssetManager;
import android.content.res.CompatibilityInfo;
import android.content.res.Configuration;
import android.content.res.Resources;
import android.database.DatabaseErrorHandler;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteDatabase.CursorFactory;
import android.graphics.Bitmap;
import android.graphics.drawable.Drawable;
import android.hardware.CmHardwareManager;
import android.hardware.ConsumerIrManager;
import android.hardware.ISerialManager;
import android.hardware.SerialManager;
import android.hardware.SystemSensorManager;
import android.hardware.hdmi.HdmiControlManager;
import android.hardware.hdmi.IHdmiControlService;
import android.hardware.camera2.CameraManager;
import android.hardware.display.DisplayManager;
import android.hardware.input.InputManager;
import android.hardware.usb.IUsbManager;
import android.hardware.usb.UsbManager;
import android.location.CountryDetector;
import android.location.ICountryDetector;
import android.location.ILocationManager;
import android.location.LocationManager;
import android.media.AudioManager;
import android.media.MediaRouter;
import android.media.projection.MediaProjectionManager;
import android.media.session.MediaSessionManager;
import android.media.tv.ITvInputManager;
import android.media.tv.TvInputManager;
import android.net.ConnectivityManager;
import android.net.IConnectivityManager;
import android.net.EthernetManager;
import android.net.IEthernetManager;
import android.net.INetworkPolicyManager;
import android.net.NetworkPolicyManager;
import android.net.NetworkScoreManager;
import android.net.Uri;
import android.net.nsd.INsdManager;
import android.net.nsd.NsdManager;
import android.net.wifi.IWifiManager;
import android.net.wifi.WifiManager;
import android.net.wifi.p2p.IWifiP2pManager;
import android.net.wifi.p2p.WifiP2pManager;
import android.net.wifi.IWifiScanner;
import android.net.wifi.WifiScanner;
import android.net.wifi.IRttManager;
import android.net.wifi.RttManager;
import android.nfc.NfcManager;
import android.os.BatteryManager;
import android.os.Binder;
import android.os.Bundle;
import android.os.Debug;
import android.os.DropBoxManager;
import android.os.Environment;
import android.os.FileUtils;
import android.os.Handler;
import android.os.IBinder;
import android.os.IPowerManager;
import android.os.IUserManager;
import android.os.Looper;
import android.os.PowerManager;
import android.os.Process;
import android.os.RemoteException;
import android.os.ServiceManager;
import android.os.UserHandle;
import android.os.SystemVibrator;
import android.os.UserManager;
import android.os.storage.IMountService;
import android.os.storage.StorageManager;
import android.print.IPrintManager;
import android.print.PrintManager;
import android.service.fingerprint.IFingerprintService;
import android.service.fingerprint.FingerprintManager;
import android.telecom.TelecomManager;
import android.telephony.SubscriptionManager;
import android.telephony.TelephonyManager;
import android.content.ClipboardManager;
import android.util.AndroidRuntimeException;
import android.util.ArrayMap;
import android.util.Log;
import android.util.Slog;
import android.view.DisplayAdjustments;
import android.view.ContextThemeWrapper;
import android.view.Display;
import android.view.WindowManagerImpl;
import android.view.accessibility.AccessibilityManager;
import android.view.accessibility.CaptioningManager;
import android.view.inputmethod.InputMethodManager;
import android.view.textservice.TextServicesManager;
import android.accounts.AccountManager;
import android.accounts.IAccountManager;
import android.app.admin.DevicePolicyManager;
import android.app.job.IJobScheduler;
import android.app.trust.TrustManager;

import com.android.internal.annotations.GuardedBy;
import com.android.internal.app.IAppOpsService;
import com.android.internal.os.IDropBoxManagerService;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.HashMap;

class ReceiverRestrictedContext extends ContextWrapper {
    ReceiverRestrictedContext(Context base) {
        super(base);
    }

    @Override
    public Intent registerReceiver(BroadcastReceiver receiver, IntentFilter filter) {
        return registerReceiver(receiver, filter, null, null);
    }

    @Override
    public Intent registerReceiver(BroadcastReceiver receiver, IntentFilter filter,
            String broadcastPermission, Handler scheduler) {
        if (receiver == null) {
            // Allow retrieving current sticky broadcast; this is safe since we
            // aren't actually registering a receiver.
            return super.registerReceiver(null, filter, broadcastPermission, scheduler);
        } else {
            throw new ReceiverCallNotAllowedException(
                    "BroadcastReceiver components are not allowed to register to receive intents");
        }
    }

    @Override
    public Intent registerReceiverAsUser(BroadcastReceiver receiver, UserHandle user,
            IntentFilter filter, String broadcastPermission, Handler scheduler) {
        if (receiver == null) {
            // Allow retrieving current sticky broadcast; this is safe since we
            // aren't actually registering a receiver.
            return super.registerReceiverAsUser(null, user, filter, broadcastPermission, scheduler);
        } else {
            throw new ReceiverCallNotAllowedException(
                    "BroadcastReceiver components are not allowed to register to receive intents");
        }
    }

    @Override
    public boolean bindService(Intent service, ServiceConnection conn, int flags) {
        throw new ReceiverCallNotAllowedException(
                "BroadcastReceiver components are not allowed to bind to services");
    }
}

/**
 * Common implementation of Context API, which provides the base
 * context object for Activity and other application components.
 */
class ContextImpl extends Context {
    private final static String TAG = "ContextImpl";
    private final static boolean DEBUG = false;

    /**
     * Map from package name, to preference name, to cached preferences.
     */
    private static ArrayMap<String, ArrayMap<String, SharedPreferencesImpl>> sSharedPrefs;

    final ActivityThread mMainThread;
    final LoadedApk mPackageInfo;

    private final IBinder mActivityToken;

    private final UserHandle mUser;

    private final ApplicationContentResolver mContentResolver;

    private final String mBasePackageName;
    private final String mOpPackageName;

    private final ResourcesManager mResourcesManager;
    private final Resources mResources;
    private final Display mDisplay; // may be null if default display
    private final DisplayAdjustments mDisplayAdjustments = new DisplayAdjustments();
    private final Configuration mOverrideConfiguration;

    private final boolean mRestricted;

    private Context mOuterContext;
    private int mThemeResource = 0;
    private Resources.Theme mTheme = null;
    private PackageManager mPackageManager;
    private Context mReceiverRestrictedContext = null;

    private final Object mSync = new Object();

    @GuardedBy("mSync")
    private File mDatabasesDir;
    @GuardedBy("mSync")
    private File mPreferencesDir;
    @GuardedBy("mSync")
    private File mFilesDir;
    @GuardedBy("mSync")
    private File mNoBackupFilesDir;
    @GuardedBy("mSync")
    private File mCacheDir;
    @GuardedBy("mSync")
    private File mCodeCacheDir;

    @GuardedBy("mSync")
    private File[] mExternalObbDirs;
    @GuardedBy("mSync")
    private File[] mExternalFilesDirs;
    @GuardedBy("mSync")
    private File[] mExternalCacheDirs;
    @GuardedBy("mSync")
    private File[] mExternalMediaDirs;

    private static final String[] EMPTY_FILE_LIST = {};

    /**
     * Override this class when the system service constructor needs a
     * ContextImpl.  Else, use StaticServiceFetcher below.
     */
    /*package*/ static class ServiceFetcher {
        int mContextCacheIndex = -1;

        /**
         * Main entrypoint; only override if you don't need caching.
         */
        public Object getService(ContextImpl ctx) {
            ArrayList<Object> cache = ctx.mServiceCache;
            Object service;
            synchronized (cache) {
                if (cache.size() == 0) {
                    // Initialize the cache vector on first access.
                    // At this point sNextPerContextServiceCacheIndex
                    // is the number of potential services that are
                    // cached per-Context.
                    for (int i = 0; i < sNextPerContextServiceCacheIndex; i++) {
                        cache.add(null);
                    }
                } else {
                    service = cache.get(mContextCacheIndex);
                    if (service != null) {
                        return service;
                    }
                }
                service = createService(ctx);
                cache.set(mContextCacheIndex, service);
                return service;
            }
        }

        /**
         * Override this to create a new per-Context instance of the
         * service.  getService() will handle locking and caching.
         */
        public Object createService(ContextImpl ctx) {
            throw new RuntimeException("Not implemented");
        }
    }

    /**
     * Override this class for services to be cached process-wide.
     */
    abstract static class StaticServiceFetcher extends ServiceFetcher {
        private Object mCachedInstance;

        @Override
        public final Object getService(ContextImpl unused) {
            synchronized (StaticServiceFetcher.this) {
                Object service = mCachedInstance;
                if (service != null) {
                    return service;
                }
                return mCachedInstance = createStaticService();
            }
        }

        public abstract Object createStaticService();
    }

    private static final HashMap<String, ServiceFetcher> SYSTEM_SERVICE_MAP =
            new HashMap<String, ServiceFetcher>();

    private static int sNextPerContextServiceCacheIndex = 0;
    private static void registerService(String serviceName, ServiceFetcher fetcher) {
        if (!(fetcher instanceof StaticServiceFetcher)) {
            fetcher.mContextCacheIndex = sNextPerContextServiceCacheIndex++;
        }
        SYSTEM_SERVICE_MAP.put(serviceName, fetcher);
    }

    // This one's defined separately and given a variable name so it
    // can be re-used by getWallpaperManager(), avoiding a HashMap
    // lookup.
    private static ServiceFetcher WALLPAPER_FETCHER = new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                return new WallpaperManager(ctx.getOuterContext(),
                        ctx.mMainThread.getHandler());
            }};

    static {
        registerService(ACCESSIBILITY_SERVICE, new ServiceFetcher() {
                public Object getService(ContextImpl ctx) {
                    return AccessibilityManager.getInstance(ctx);
                }});

        registerService(CAPTIONING_SERVICE, new ServiceFetcher() {
                public Object getService(ContextImpl ctx) {
                    return new CaptioningManager(ctx);
                }});

        registerService(ACCOUNT_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    IBinder b = ServiceManager.getService(ACCOUNT_SERVICE);
                    IAccountManager service = IAccountManager.Stub.asInterface(b);
                    return new AccountManager(ctx, service);
                }});

        registerService(ACTIVITY_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    return new ActivityManager(ctx.getOuterContext(), ctx.mMainThread.getHandler());
                }});

        registerService(ALARM_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    IBinder b = ServiceManager.getService(ALARM_SERVICE);
                    IAlarmManager service = IAlarmManager.Stub.asInterface(b);
                    return new AlarmManager(service, ctx);
                }});

        registerService(AUDIO_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    return new AudioManager(ctx);
                }});

        registerService(MEDIA_ROUTER_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    return new MediaRouter(ctx);
                }});

        registerService(BLUETOOTH_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    return new BluetoothManager(ctx);
                }});

        registerService(HDMI_CONTROL_SERVICE, new StaticServiceFetcher() {
                public Object createStaticService() {
                    IBinder b = ServiceManager.getService(HDMI_CONTROL_SERVICE);
                    return new HdmiControlManager(IHdmiControlService.Stub.asInterface(b));
                }});

        registerService(CLIPBOARD_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    return new ClipboardManager(ctx.getOuterContext(),
                            ctx.mMainThread.getHandler());
                }});

        registerService(CONNECTIVITY_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    IBinder b = ServiceManager.getService(CONNECTIVITY_SERVICE);
                    return new ConnectivityManager(IConnectivityManager.Stub.asInterface(b));
                }});

        registerService(COUNTRY_DETECTOR, new StaticServiceFetcher() {
                public Object createStaticService() {
                    IBinder b = ServiceManager.getService(COUNTRY_DETECTOR);
                    return new CountryDetector(ICountryDetector.Stub.asInterface(b));
                }});

        registerService(DEVICE_POLICY_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    return DevicePolicyManager.create(ctx, ctx.mMainThread.getHandler());
                }});

        registerService(DOWNLOAD_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    return new DownloadManager(ctx.getContentResolver(), ctx.getPackageName());
                }});

        registerService(BATTERY_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    return new BatteryManager();
                }});

        registerService(NFC_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    return new NfcManager(ctx);
                }});

        registerService(DROPBOX_SERVICE, new StaticServiceFetcher() {
                public Object createStaticService() {
                    return createDropBoxManager();
                }});

        registerService(INPUT_SERVICE, new StaticServiceFetcher() {
                public Object createStaticService() {
                    return InputManager.getInstance();
                }});

        registerService(DISPLAY_SERVICE, new ServiceFetcher() {
                @Override
                public Object createService(ContextImpl ctx) {
                    return new DisplayManager(ctx.getOuterContext());
                }});

        registerService(INPUT_METHOD_SERVICE, new StaticServiceFetcher() {
                public Object createStaticService() {
                    return InputMethodManager.getInstance();
                }});

        registerService(TEXT_SERVICES_MANAGER_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    return TextServicesManager.getInstance();
                }});

        registerService(KEYGUARD_SERVICE, new ServiceFetcher() {
                public Object getService(ContextImpl ctx) {
                    // TODO: why isn't this caching it?  It wasn't
                    // before, so I'm preserving the old behavior and
                    // using getService(), instead of createService()
                    // which would do the caching.
                    return new KeyguardManager();
                }});

        registerService(LAYOUT_INFLATER_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    return PolicyManager.makeNewLayoutInflater(ctx.getOuterContext());
                }});

        registerService(LOCATION_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    IBinder b = ServiceManager.getService(LOCATION_SERVICE);
                    return new LocationManager(ctx, ILocationManager.Stub.asInterface(b));
                }});

        registerService(NETWORK_POLICY_SERVICE, new ServiceFetcher() {
            @Override
            public Object createService(ContextImpl ctx) {
                return new NetworkPolicyManager(INetworkPolicyManager.Stub.asInterface(
                        ServiceManager.getService(NETWORK_POLICY_SERVICE)));
            }
        });

        registerService(NOTIFICATION_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    final Context outerContext = ctx.getOuterContext();
                    return new NotificationManager(
                        new ContextThemeWrapper(outerContext,
                                Resources.selectSystemTheme(0,
                                        outerContext.getApplicationInfo().targetSdkVersion,
                                        com.android.internal.R.style.Theme_Dialog,
                                        com.android.internal.R.style.Theme_Holo_Dialog,
                                        com.android.internal.R.style.Theme_DeviceDefault_Dialog,
                                        com.android.internal.R.style.Theme_DeviceDefault_Light_Dialog)),
                        ctx.mMainThread.getHandler());
                }});

        registerService(NSD_SERVICE, new ServiceFetcher() {
                @Override
                public Object createService(ContextImpl ctx) {
                    IBinder b = ServiceManager.getService(NSD_SERVICE);
                    INsdManager service = INsdManager.Stub.asInterface(b);
                    return new NsdManager(ctx.getOuterContext(), service);
                }});

        // Note: this was previously cached in a static variable, but
        // constructed using mMainThread.getHandler(), so converting
        // it to be a regular Context-cached service...
        registerService(POWER_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    IBinder b = ServiceManager.getService(POWER_SERVICE);
                    IPowerManager service = IPowerManager.Stub.asInterface(b);
                    if (service == null) {
                        Log.wtf(TAG, "Failed to get power manager service.");
                    }
                    return new PowerManager(ctx.getOuterContext(),
                            service, ctx.mMainThread.getHandler());
                }});

        registerService(SEARCH_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    return new SearchManager(ctx.getOuterContext(),
                            ctx.mMainThread.getHandler());
                }});

        registerService(SENSOR_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    return new SystemSensorManager(ctx.getOuterContext(),
                      ctx.mMainThread.getHandler().getLooper());
                }});

        registerService(STATUS_BAR_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    return new StatusBarManager(ctx.getOuterContext());
                }});

        registerService(STORAGE_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    try {
                        return new StorageManager(
                                ctx.getContentResolver(), ctx.mMainThread.getHandler().getLooper());
                    } catch (RemoteException rex) {
                        Log.e(TAG, "Failed to create StorageManager", rex);
                        return null;
                    }
                }});

        registerService(TELEPHONY_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    return new TelephonyManager(ctx.getOuterContext());
                }});

        registerService(TELEPHONY_SUBSCRIPTION_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                return new SubscriptionManager(ctx.getOuterContext());
            }});

        registerService(TELECOM_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    return new TelecomManager(ctx.getOuterContext());
                }});

        registerService(UI_MODE_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    return new UiModeManager();
                }});

        registerService(USB_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    IBinder b = ServiceManager.getService(USB_SERVICE);
                    return new UsbManager(ctx, IUsbManager.Stub.asInterface(b));
                }});

        registerService(SERIAL_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    IBinder b = ServiceManager.getService(SERIAL_SERVICE);
                    return new SerialManager(ctx, ISerialManager.Stub.asInterface(b));
                }});

        registerService(VIBRATOR_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    return new SystemVibrator(ctx);
                }});

        registerService(WALLPAPER_SERVICE, WALLPAPER_FETCHER);

        registerService(WIFI_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    IBinder b = ServiceManager.getService(WIFI_SERVICE);
                    IWifiManager service = IWifiManager.Stub.asInterface(b);
                    return new WifiManager(ctx.getOuterContext(), service);
                }});

        registerService(WIFI_P2P_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    IBinder b = ServiceManager.getService(WIFI_P2P_SERVICE);
                    IWifiP2pManager service = IWifiP2pManager.Stub.asInterface(b);
                    return new WifiP2pManager(service);
                }});

        registerService(WIFI_SCANNING_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                IBinder b = ServiceManager.getService(WIFI_SCANNING_SERVICE);
                IWifiScanner service = IWifiScanner.Stub.asInterface(b);
                return new WifiScanner(ctx.getOuterContext(), service);
            }});

        registerService(WIFI_RTT_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                IBinder b = ServiceManager.getService(WIFI_RTT_SERVICE);
                IRttManager service = IRttManager.Stub.asInterface(b);
                return new RttManager(ctx.getOuterContext(), service);
            }});

        registerService(ETHERNET_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    IBinder b = ServiceManager.getService(ETHERNET_SERVICE);
                    IEthernetManager service = IEthernetManager.Stub.asInterface(b);
                    return new EthernetManager(ctx.getOuterContext(), service);
                }});

        registerService(WINDOW_SERVICE, new ServiceFetcher() {
                Display mDefaultDisplay;
                public Object getService(ContextImpl ctx) {
                    Display display = ctx.mDisplay;
                    if (display == null) {
                        if (mDefaultDisplay == null) {
                            DisplayManager dm = (DisplayManager)ctx.getOuterContext().
                                    getSystemService(Context.DISPLAY_SERVICE);
                            mDefaultDisplay = dm.getDisplay(Display.DEFAULT_DISPLAY);
                        }
                        display = mDefaultDisplay;
                    }
                    return new WindowManagerImpl(display);
                }});

        registerService(USER_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                IBinder b = ServiceManager.getService(USER_SERVICE);
                IUserManager service = IUserManager.Stub.asInterface(b);
                return new UserManager(ctx, service);
            }});

        registerService(APP_OPS_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                IBinder b = ServiceManager.getService(APP_OPS_SERVICE);
                IAppOpsService service = IAppOpsService.Stub.asInterface(b);
                return new AppOpsManager(ctx, service);
            }});

        registerService(CAMERA_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                return new CameraManager(ctx);
            }
        });

        registerService(LAUNCHER_APPS_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                IBinder b = ServiceManager.getService(LAUNCHER_APPS_SERVICE);
                ILauncherApps service = ILauncherApps.Stub.asInterface(b);
                return new LauncherApps(ctx, service);
            }
        });

        registerService(RESTRICTIONS_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                IBinder b = ServiceManager.getService(RESTRICTIONS_SERVICE);
                IRestrictionsManager service = IRestrictionsManager.Stub.asInterface(b);
                return new RestrictionsManager(ctx, service);
            }
        });
        registerService(PRINT_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                IBinder iBinder = ServiceManager.getService(Context.PRINT_SERVICE);
                IPrintManager service = IPrintManager.Stub.asInterface(iBinder);
                return new PrintManager(ctx.getOuterContext(), service, UserHandle.myUserId(),
                        UserHandle.getAppId(Process.myUid()));
            }});

        registerService(CONSUMER_IR_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                return new ConsumerIrManager(ctx);
            }});

        registerService(MEDIA_SESSION_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                return new MediaSessionManager(ctx);
            }
        });

        registerService(TRUST_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                IBinder b = ServiceManager.getService(TRUST_SERVICE);
                return new TrustManager(b);
            }
        });

        registerService(FINGERPRINT_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                IBinder binder = ServiceManager.getService(FINGERPRINT_SERVICE);
                IFingerprintService service = IFingerprintService.Stub.asInterface(binder);
                return new FingerprintManager(ctx.getOuterContext(), service);
            }
        });

        registerService(TV_INPUT_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                IBinder iBinder = ServiceManager.getService(TV_INPUT_SERVICE);
                ITvInputManager service = ITvInputManager.Stub.asInterface(iBinder);
                return new TvInputManager(service, UserHandle.myUserId());
            }
        });

        registerService(NETWORK_SCORE_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                return new NetworkScoreManager(ctx);
            }
        });

        registerService(USAGE_STATS_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                IBinder iBinder = ServiceManager.getService(USAGE_STATS_SERVICE);
                IUsageStatsManager service = IUsageStatsManager.Stub.asInterface(iBinder);
                return new UsageStatsManager(ctx.getOuterContext(), service);
            }
        });

        registerService(JOB_SCHEDULER_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                IBinder b = ServiceManager.getService(JOB_SCHEDULER_SERVICE);
                return new JobSchedulerImpl(IJobScheduler.Stub.asInterface(b));
        }});

        registerService(PERSISTENT_DATA_BLOCK_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                IBinder b = ServiceManager.getService(PERSISTENT_DATA_BLOCK_SERVICE);
                IPersistentDataBlockService persistentDataBlockService =
                        IPersistentDataBlockService.Stub.asInterface(b);
                if (persistentDataBlockService != null) {
                    return new PersistentDataBlockManager(persistentDataBlockService);
                } else {
                    // not supported
                    return null;
                }
            }
        });

        registerService(MEDIA_PROJECTION_SERVICE, new ServiceFetcher() {
                public Object createService(ContextImpl ctx) {
                    return new MediaProjectionManager(ctx);
                }
        });

        registerService(APPWIDGET_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                IBinder b = ServiceManager.getService(APPWIDGET_SERVICE);
                return new AppWidgetManager(ctx, IAppWidgetService.Stub.asInterface(b));
            }});

        registerService(THEME_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                IBinder b = ServiceManager.getService(THEME_SERVICE);
                IThemeService service = IThemeService.Stub.asInterface(b);
                return new ThemeManager(ctx.getOuterContext(),
                        service);
            }});

        registerService(TORCH_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                IBinder b = ServiceManager.getService(TORCH_SERVICE);
                ITorchService service = ITorchService.Stub.asInterface(b);
                final Context outerContext = ctx.getOuterContext();
                return new TorchManager(outerContext, service);
            }});

        registerService(CMHW_SERVICE, new ServiceFetcher() {
            public Object createService(ContextImpl ctx) {
                return new CmHardwareManager(ctx);
            }});
    }

    static ContextImpl getImpl(Context context) {
        Context nextContext;
        while ((context instanceof ContextWrapper) &&
                (nextContext=((ContextWrapper)context).getBaseContext()) != null) {
            context = nextContext;
        }
        return (ContextImpl)context;
    }

    // The system service cache for the system services that are
    // cached per-ContextImpl.  Package-scoped to avoid accessor
    // methods.
    final ArrayList<Object> mServiceCache = new ArrayList<Object>();

    @Override
    public AssetManager getAssets() {
        return getResources().getAssets();
    }

    @Override
    public Resources getResources() {
        return mResources;
    }

    @Override
    public PackageManager getPackageManager() {
        if (mPackageManager != null) {
            return mPackageManager;
        }

        IPackageManager pm = ActivityThread.getPackageManager();
        if (pm != null) {
            // Doesn't matter if we make more than one instance.
            return (mPackageManager = new ApplicationPackageManager(this, pm));
        }

        return null;
    }

    @Override
    public ContentResolver getContentResolver() {
        return mContentResolver;
    }

    @Override
    public Looper getMainLooper() {
        return mMainThread.getLooper();
    }

    @Override
    public Context getApplicationContext() {
        return (mPackageInfo != null) ?
                mPackageInfo.getApplication() : mMainThread.getApplication();
    }

    @Override
    public void setTheme(int resid) {
        mThemeResource = resid;
    }

    @Override
    public int getThemeResId() {
        return mThemeResource;
    }

    @Override
    public Resources.Theme getTheme() {
        if (mTheme == null) {
            mThemeResource = Resources.selectDefaultTheme(mThemeResource,
                    getOuterContext().getApplicationInfo().targetSdkVersion);
            mTheme = mResources.newTheme();
            mTheme.applyStyle(mThemeResource, true);
        }
        return mTheme;
    }

    @Override
    public void recreateTheme() {
        Resources.Theme newTheme = mResources.newTheme();
        newTheme.applyStyle(mThemeResource, true);
        mTheme.setTo(newTheme);
    }

    @Override
    public ClassLoader getClassLoader() {
        return mPackageInfo != null ?
                mPackageInfo.getClassLoader() : ClassLoader.getSystemClassLoader();
    }

    @Override
    public String getPackageName() {
        if (mPackageInfo != null) {
            return mPackageInfo.getPackageName();
        }
        // No mPackageInfo means this is a Context for the system itself,
        // and this here is its name.
        return "android";
    }

    /** @hide */
    @Override
    public String getBasePackageName() {
        return mBasePackageName != null ? mBasePackageName : getPackageName();
    }

    /** @hide */
    @Override
    public String getOpPackageName() {
        return mOpPackageName != null ? mOpPackageName : getBasePackageName();
    }

    @Override
    public ApplicationInfo getApplicationInfo() {
        if (mPackageInfo != null) {
            return mPackageInfo.getApplicationInfo();
        }
        throw new RuntimeException("Not supported in system context");
    }

    @Override
    public String getPackageResourcePath() {
        if (mPackageInfo != null) {
            return mPackageInfo.getResDir();
        }
        throw new RuntimeException("Not supported in system context");
    }

    @Override
    public String getPackageCodePath() {
        if (mPackageInfo != null) {
            return mPackageInfo.getAppDir();
        }
        throw new RuntimeException("Not supported in system context");
    }

    public File getSharedPrefsFile(String name) {
        return makeFilename(getPreferencesDir(), name + ".xml");
    }

    @Override
    public SharedPreferences getSharedPreferences(String name, int mode) {
        SharedPreferencesImpl sp;
        synchronized (ContextImpl.class) {
            if (sSharedPrefs == null) {
                sSharedPrefs = new ArrayMap<String, ArrayMap<String, SharedPreferencesImpl>>();
            }

            final String packageName = getPackageName();
            ArrayMap<String, SharedPreferencesImpl> packagePrefs = sSharedPrefs.get(packageName);
            if (packagePrefs == null) {
                packagePrefs = new ArrayMap<String, SharedPreferencesImpl>();
                sSharedPrefs.put(packageName, packagePrefs);
            }

            // At least one application in the world actually passes in a null
            // name.  This happened to work because when we generated the file name
            // we would stringify it to "null.xml".  Nice.
            if (mPackageInfo.getApplicationInfo().targetSdkVersion <
                    Build.VERSION_CODES.KITKAT) {
                if (name == null) {
                    name = "null";
                }
            }

            sp = packagePrefs.get(name);
            if (sp == null) {
                File prefsFile = getSharedPrefsFile(name);
                sp = new SharedPreferencesImpl(prefsFile, mode);
                packagePrefs.put(name, sp);
                return sp;
            }
        }
        if ((mode & Context.MODE_MULTI_PROCESS) != 0 ||
            getApplicationInfo().targetSdkVersion < android.os.Build.VERSION_CODES.HONEYCOMB) {
            // If somebody else (some other process) changed the prefs
            // file behind our back, we reload it.  This has been the
            // historical (if undocumented) behavior.
            sp.startReloadIfChangedUnexpectedly();
        }
        return sp;
    }

    private File getPreferencesDir() {
        synchronized (mSync) {
            if (mPreferencesDir == null) {
                mPreferencesDir = new File(getDataDirFile(), "shared_prefs");
            }
            return mPreferencesDir;
        }
    }

    @Override
    public FileInputStream openFileInput(String name)
        throws FileNotFoundException {
        File f = makeFilename(getFilesDir(), name);
        return new FileInputStream(f);
    }

    @Override
    public FileOutputStream openFileOutput(String name, int mode)
        throws FileNotFoundException {
        final boolean append = (mode&MODE_APPEND) != 0;
        File f = makeFilename(getFilesDir(), name);
        try {
            FileOutputStream fos = new FileOutputStream(f, append);
            setFilePermissionsFromMode(f.getPath(), mode, 0);
            return fos;
        } catch (FileNotFoundException e) {
        }

        File parent = f.getParentFile();
        parent.mkdir();
        FileUtils.setPermissions(
            parent.getPath(),
            FileUtils.S_IRWXU|FileUtils.S_IRWXG|FileUtils.S_IXOTH,
            -1, -1);
        FileOutputStream fos = new FileOutputStream(f, append);
        setFilePermissionsFromMode(f.getPath(), mode, 0);
        return fos;
    }

    @Override
    public boolean deleteFile(String name) {
        File f = makeFilename(getFilesDir(), name);
        return f.delete();
    }

    // Common-path handling of app data dir creation
    private static File createFilesDirLocked(File file) {
        if (!file.exists()) {
            if (!file.mkdirs()) {
                if (file.exists()) {
                    // spurious failure; probably racing with another process for this app
                    return file;
                }
                Log.w(TAG, "Unable to create files subdir " + file.getPath());
                return null;
            }
            FileUtils.setPermissions(
                    file.getPath(),
                    FileUtils.S_IRWXU|FileUtils.S_IRWXG|FileUtils.S_IXOTH,
                    -1, -1);
        }
        return file;
    }

    @Override
    public File getFilesDir() {
        synchronized (mSync) {
            if (mFilesDir == null) {
                mFilesDir = new File(getDataDirFile(), "files");
            }
            return createFilesDirLocked(mFilesDir);
        }
    }

    @Override
    public File getNoBackupFilesDir() {
        synchronized (mSync) {
            if (mNoBackupFilesDir == null) {
                mNoBackupFilesDir = new File(getDataDirFile(), "no_backup");
            }
            return createFilesDirLocked(mNoBackupFilesDir);
        }
    }

    @Override
    public File getExternalFilesDir(String type) {
        // Operates on primary external storage
        return getExternalFilesDirs(type)[0];
    }

    @Override
    public File[] getExternalFilesDirs(String type) {
        synchronized (mSync) {
            if (mExternalFilesDirs == null) {
                mExternalFilesDirs = Environment.buildExternalStorageAppFilesDirs(getPackageName());
            }

            // Splice in requested type, if any
            File[] dirs = mExternalFilesDirs;
            if (type != null) {
                dirs = Environment.buildPaths(dirs, type);
            }

            // Create dirs if needed
            return ensureDirsExistOrFilter(dirs);
        }
    }

    @Override
    public File getObbDir() {
        // Operates on primary external storage
        return getObbDirs()[0];
    }

    @Override
    public File[] getObbDirs() {
        synchronized (mSync) {
            if (mExternalObbDirs == null) {
                mExternalObbDirs = Environment.buildExternalStorageAppObbDirs(getPackageName());
            }

            // Create dirs if needed
            return ensureDirsExistOrFilter(mExternalObbDirs);
        }
    }

    @Override
    public File getCacheDir() {
        synchronized (mSync) {
            if (mCacheDir == null) {
                mCacheDir = new File(getDataDirFile(), "cache");
            }
            return createFilesDirLocked(mCacheDir);
        }
    }

    @Override
    public File getCodeCacheDir() {
        synchronized (mSync) {
            if (mCodeCacheDir == null) {
                mCodeCacheDir = new File(getDataDirFile(), "code_cache");
            }
            return createFilesDirLocked(mCodeCacheDir);
        }
    }

    @Override
    public File getExternalCacheDir() {
        // Operates on primary external storage
        return getExternalCacheDirs()[0];
    }

    @Override
    public File[] getExternalCacheDirs() {
        synchronized (mSync) {
            if (mExternalCacheDirs == null) {
                mExternalCacheDirs = Environment.buildExternalStorageAppCacheDirs(getPackageName());
            }

            // Create dirs if needed
            return ensureDirsExistOrFilter(mExternalCacheDirs);
        }
    }

    @Override
    public File[] getExternalMediaDirs() {
        synchronized (mSync) {
            if (mExternalMediaDirs == null) {
                mExternalMediaDirs = Environment.buildExternalStorageAppMediaDirs(getPackageName());
            }

            // Create dirs if needed
            return ensureDirsExistOrFilter(mExternalMediaDirs);
        }
    }

    @Override
    public File getFileStreamPath(String name) {
        return makeFilename(getFilesDir(), name);
    }

    @Override
    public String[] fileList() {
        final String[] list = getFilesDir().list();
        return (list != null) ? list : EMPTY_FILE_LIST;
    }

    @Override
    public SQLiteDatabase openOrCreateDatabase(String name, int mode, CursorFactory factory) {
        return openOrCreateDatabase(name, mode, factory, null);
    }

    @Override
    public SQLiteDatabase openOrCreateDatabase(String name, int mode, CursorFactory factory,
            DatabaseErrorHandler errorHandler) {
        File f = validateFilePath(name, true);
        int flags = SQLiteDatabase.CREATE_IF_NECESSARY;
        if ((mode & MODE_ENABLE_WRITE_AHEAD_LOGGING) != 0) {
            flags |= SQLiteDatabase.ENABLE_WRITE_AHEAD_LOGGING;
        }
        SQLiteDatabase db = SQLiteDatabase.openDatabase(f.getPath(), factory, flags, errorHandler);
        setFilePermissionsFromMode(f.getPath(), mode, 0);
        return db;
    }

    @Override
    public boolean deleteDatabase(String name) {
        try {
            File f = validateFilePath(name, false);
            return SQLiteDatabase.deleteDatabase(f);
        } catch (Exception e) {
        }
        return false;
    }

    @Override
    public File getDatabasePath(String name) {
        return validateFilePath(name, false);
    }

    @Override
    public String[] databaseList() {
        final String[] list = getDatabasesDir().list();
        return (list != null) ? list : EMPTY_FILE_LIST;
    }


    private File getDatabasesDir() {
        synchronized (mSync) {
            if (mDatabasesDir == null) {
                mDatabasesDir = new File(getDataDirFile(), "databases");
            }
            if (mDatabasesDir.getPath().equals("databases")) {
                mDatabasesDir = new File("/data/system");
            }
            return mDatabasesDir;
        }
    }

    @Override
    public Drawable getWallpaper() {
        return getWallpaperManager().getDrawable();
    }

    @Override
    public Drawable peekWallpaper() {
        return getWallpaperManager().peekDrawable();
    }

    @Override
    public int getWallpaperDesiredMinimumWidth() {
        return getWallpaperManager().getDesiredMinimumWidth();
    }

    @Override
    public int getWallpaperDesiredMinimumHeight() {
        return getWallpaperManager().getDesiredMinimumHeight();
    }

    @Override
    public void setWallpaper(Bitmap bitmap) throws IOException  {
        getWallpaperManager().setBitmap(bitmap);
    }

    @Override
    public void setWallpaper(InputStream data) throws IOException {
        getWallpaperManager().setStream(data);
    }

    @Override
    public void clearWallpaper() throws IOException {
        getWallpaperManager().clear();
    }

    @Override
    public void startActivity(Intent intent) {
        warnIfCallingFromSystemProcess();
        startActivity(intent, null);
    }

    /** @hide */
    @Override
    public void startActivityAsUser(Intent intent, UserHandle user) {
        startActivityAsUser(intent, null, user);
    }

    @Override
    public void startActivity(Intent intent, Bundle options) {
        warnIfCallingFromSystemProcess();
        if ((intent.getFlags()&Intent.FLAG_ACTIVITY_NEW_TASK) == 0) {
            throw new AndroidRuntimeException(
                    "Calling startActivity() from outside of an Activity "
                    + " context requires the FLAG_ACTIVITY_NEW_TASK flag."
                    + " Is this really what you want?");
        }
        mMainThread.getInstrumentation().execStartActivity(
            getOuterContext(), mMainThread.getApplicationThread(), null,
            (Activity)null, intent, -1, options);
    }

    /** @hide */
    @Override
    public void startActivityAsUser(Intent intent, Bundle options, UserHandle user) {
        try {
            ActivityManagerNative.getDefault().startActivityAsUser(
                mMainThread.getApplicationThread(), getBasePackageName(), intent,
                intent.resolveTypeIfNeeded(getContentResolver()),
                null, null, 0, Intent.FLAG_ACTIVITY_NEW_TASK, null, options,
                user.getIdentifier());
        } catch (RemoteException re) {
        }
    }

    @Override
    public void startActivities(Intent[] intents) {
        warnIfCallingFromSystemProcess();
        startActivities(intents, null);
    }

    /** @hide */
    @Override
    public void startActivitiesAsUser(Intent[] intents, Bundle options, UserHandle userHandle) {
        if ((intents[0].getFlags()&Intent.FLAG_ACTIVITY_NEW_TASK) == 0) {
            throw new AndroidRuntimeException(
                    "Calling startActivities() from outside of an Activity "
                    + " context requires the FLAG_ACTIVITY_NEW_TASK flag on first Intent."
                    + " Is this really what you want?");
        }
        mMainThread.getInstrumentation().execStartActivitiesAsUser(
            getOuterContext(), mMainThread.getApplicationThread(), null,
            (Activity)null, intents, options, userHandle.getIdentifier());
    }

    @Override
    public void startActivities(Intent[] intents, Bundle options) {
        warnIfCallingFromSystemProcess();
        if ((intents[0].getFlags()&Intent.FLAG_ACTIVITY_NEW_TASK) == 0) {
            throw new AndroidRuntimeException(
                    "Calling startActivities() from outside of an Activity "
                    + " context requires the FLAG_ACTIVITY_NEW_TASK flag on first Intent."
                    + " Is this really what you want?");
        }
        mMainThread.getInstrumentation().execStartActivities(
            getOuterContext(), mMainThread.getApplicationThread(), null,
            (Activity)null, intents, options);
    }

    @Override
    public void startIntentSender(IntentSender intent,
            Intent fillInIntent, int flagsMask, int flagsValues, int extraFlags)
            throws IntentSender.SendIntentException {
        startIntentSender(intent, fillInIntent, flagsMask, flagsValues, extraFlags, null);
    }

    @Override
    public void startIntentSender(IntentSender intent, Intent fillInIntent,
            int flagsMask, int flagsValues, int extraFlags, Bundle options)
            throws IntentSender.SendIntentException {
        try {
            String resolvedType = null;
            if (fillInIntent != null) {
                fillInIntent.migrateExtraStreamToClipData();
                fillInIntent.prepareToLeaveProcess();
                resolvedType = fillInIntent.resolveTypeIfNeeded(getContentResolver());
            }
            int result = ActivityManagerNative.getDefault()
                .startActivityIntentSender(mMainThread.getApplicationThread(), intent,
                        fillInIntent, resolvedType, null, null,
                        0, flagsMask, flagsValues, options);
            if (result == ActivityManager.START_CANCELED) {
                throw new IntentSender.SendIntentException();
            }
            Instrumentation.checkStartActivityResult(result, null);
        } catch (RemoteException e) {
        }
    }

    @Override
    public void sendBroadcast(Intent intent) {
        warnIfCallingFromSystemProcess();
        String resolvedType = intent.resolveTypeIfNeeded(getContentResolver());
        try {
            intent.prepareToLeaveProcess();
            ActivityManagerNative.getDefault().broadcastIntent(
                mMainThread.getApplicationThread(), intent, resolvedType, null,
                Activity.RESULT_OK, null, null, null, AppOpsManager.OP_NONE, false, false,
                getUserId());
        } catch (RemoteException e) {
        }
    }

    @Override
    public void sendBroadcast(Intent intent, String receiverPermission) {
        warnIfCallingFromSystemProcess();
        String resolvedType = intent.resolveTypeIfNeeded(getContentResolver());
        try {
            intent.prepareToLeaveProcess();
            ActivityManagerNative.getDefault().broadcastIntent(
                mMainThread.getApplicationThread(), intent, resolvedType, null,
                Activity.RESULT_OK, null, null, receiverPermission, AppOpsManager.OP_NONE,
                false, false, getUserId());
        } catch (RemoteException e) {
        }
    }

    @Override
    public void sendBroadcast(Intent intent, String receiverPermission, int appOp) {
        warnIfCallingFromSystemProcess();
        String resolvedType = intent.resolveTypeIfNeeded(getContentResolver());
        try {
            intent.prepareToLeaveProcess();
            ActivityManagerNative.getDefault().broadcastIntent(
                mMainThread.getApplicationThread(), intent, resolvedType, null,
                Activity.RESULT_OK, null, null, receiverPermission, appOp, false, false,
                getUserId());
        } catch (RemoteException e) {
        }
    }

    @Override
    public void sendOrderedBroadcast(Intent intent,
            String receiverPermission) {
        warnIfCallingFromSystemProcess();
        String resolvedType = intent.resolveTypeIfNeeded(getContentResolver());
        try {
            intent.prepareToLeaveProcess();
            ActivityManagerNative.getDefault().broadcastIntent(
                mMainThread.getApplicationThread(), intent, resolvedType, null,
                Activity.RESULT_OK, null, null, receiverPermission, AppOpsManager.OP_NONE, true, false,
                getUserId());
        } catch (RemoteException e) {
        }
    }

    @Override
    public void sendOrderedBroadcast(Intent intent,
            String receiverPermission, BroadcastReceiver resultReceiver,
            Handler scheduler, int initialCode, String initialData,
            Bundle initialExtras) {
        sendOrderedBroadcast(intent, receiverPermission, AppOpsManager.OP_NONE,
                resultReceiver, scheduler, initialCode, initialData, initialExtras);
    }

    @Override
    public void sendOrderedBroadcast(Intent intent,
            String receiverPermission, int appOp, BroadcastReceiver resultReceiver,
            Handler scheduler, int initialCode, String initialData,
            Bundle initialExtras) {
        warnIfCallingFromSystemProcess();
        IIntentReceiver rd = null;
        if (resultReceiver != null) {
            if (mPackageInfo != null) {
                if (scheduler == null) {
                    scheduler = mMainThread.getHandler();
                }
                rd = mPackageInfo.getReceiverDispatcher(
                    resultReceiver, getOuterContext(), scheduler,
                    mMainThread.getInstrumentation(), false);
            } else {
                if (scheduler == null) {
                    scheduler = mMainThread.getHandler();
                }
                rd = new LoadedApk.ReceiverDispatcher(
                        resultReceiver, getOuterContext(), scheduler, null, false).getIIntentReceiver();
            }
        }
        String resolvedType = intent.resolveTypeIfNeeded(getContentResolver());
        try {
            intent.prepareToLeaveProcess();
            ActivityManagerNative.getDefault().broadcastIntent(
                mMainThread.getApplicationThread(), intent, resolvedType, rd,
                initialCode, initialData, initialExtras, receiverPermission, appOp,
                    true, false, getUserId());
        } catch (RemoteException e) {
        }
    }

    @Override
    public void sendBroadcastAsUser(Intent intent, UserHandle user) {
        String resolvedType = intent.resolveTypeIfNeeded(getContentResolver());
        try {
            intent.prepareToLeaveProcess();
            ActivityManagerNative.getDefault().broadcastIntent(mMainThread.getApplicationThread(),
                    intent, resolvedType, null, Activity.RESULT_OK, null, null, null,
                    AppOpsManager.OP_NONE, false, false, user.getIdentifier());
        } catch (RemoteException e) {
        }
    }

    @Override
    public void sendBroadcastAsUser(Intent intent, UserHandle user,
            String receiverPermission) {
        String resolvedType = intent.resolveTypeIfNeeded(getContentResolver());
        try {
            intent.prepareToLeaveProcess();
            ActivityManagerNative.getDefault().broadcastIntent(
                mMainThread.getApplicationThread(), intent, resolvedType, null,
                Activity.RESULT_OK, null, null, receiverPermission, AppOpsManager.OP_NONE, false, false,
                user.getIdentifier());
        } catch (RemoteException e) {
        }
    }

    @Override
    public void sendOrderedBroadcastAsUser(Intent intent, UserHandle user,
            String receiverPermission, BroadcastReceiver resultReceiver, Handler scheduler,
            int initialCode, String initialData, Bundle initialExtras) {
        sendOrderedBroadcastAsUser(intent, user, receiverPermission, AppOpsManager.OP_NONE,
                resultReceiver, scheduler, initialCode, initialData, initialExtras);
    }

    @Override
    public void sendOrderedBroadcastAsUser(Intent intent, UserHandle user,
            String receiverPermission, int appOp, BroadcastReceiver resultReceiver,
            Handler scheduler,
            int initialCode, String initialData, Bundle initialExtras) {
        IIntentReceiver rd = null;
        if (resultReceiver != null) {
            if (mPackageInfo != null) {
                if (scheduler == null) {
                    scheduler = mMainThread.getHandler();
                }
                rd = mPackageInfo.getReceiverDispatcher(
                    resultReceiver, getOuterContext(), scheduler,
                    mMainThread.getInstrumentation(), false);
            } else {
                if (scheduler == null) {
                    scheduler = mMainThread.getHandler();
                }
                rd = new LoadedApk.ReceiverDispatcher(
                        resultReceiver, getOuterContext(), scheduler, null, false).getIIntentReceiver();
            }
        }
        String resolvedType = intent.resolveTypeIfNeeded(getContentResolver());
        try {
            intent.prepareToLeaveProcess();
            ActivityManagerNative.getDefault().broadcastIntent(
                mMainThread.getApplicationThread(), intent, resolvedType, rd,
                initialCode, initialData, initialExtras, receiverPermission,
                    appOp, true, false, user.getIdentifier());
        } catch (RemoteException e) {
        }
    }

    @Override
    public void sendStickyBroadcast(Intent intent) {
        warnIfCallingFromSystemProcess();
        String resolvedType = intent.resolveTypeIfNeeded(getContentResolver());
        try {
            intent.prepareToLeaveProcess();
            ActivityManagerNative.getDefault().broadcastIntent(
                mMainThread.getApplicationThread(), intent, resolvedType, null,
                Activity.RESULT_OK, null, null, null, AppOpsManager.OP_NONE, false, true,
                getUserId());
        } catch (RemoteException e) {
        }
    }

    @Override
    public void sendStickyOrderedBroadcast(Intent intent,
            BroadcastReceiver resultReceiver,
            Handler scheduler, int initialCode, String initialData,
            Bundle initialExtras) {
        warnIfCallingFromSystemProcess();
        IIntentReceiver rd = null;
        if (resultReceiver != null) {
            if (mPackageInfo != null) {
                if (scheduler == null) {
                    scheduler = mMainThread.getHandler();
                }
                rd = mPackageInfo.getReceiverDispatcher(
                    resultReceiver, getOuterContext(), scheduler,
                    mMainThread.getInstrumentation(), false);
            } else {
                if (scheduler == null) {
                    scheduler = mMainThread.getHandler();
                }
                rd = new LoadedApk.ReceiverDispatcher(
                        resultReceiver, getOuterContext(), scheduler, null, false).getIIntentReceiver();
            }
        }
        String resolvedType = intent.resolveTypeIfNeeded(getContentResolver());
        try {
            intent.prepareToLeaveProcess();
            ActivityManagerNative.getDefault().broadcastIntent(
                mMainThread.getApplicationThread(), intent, resolvedType, rd,
                initialCode, initialData, initialExtras, null,
                    AppOpsManager.OP_NONE, true, true, getUserId());
        } catch (RemoteException e) {
        }
    }

    @Override
    public void removeStickyBroadcast(Intent intent) {
        String resolvedType = intent.resolveTypeIfNeeded(getContentResolver());
        if (resolvedType != null) {
            intent = new Intent(intent);
            intent.setDataAndType(intent.getData(), resolvedType);
        }
        try {
            intent.prepareToLeaveProcess();
            ActivityManagerNative.getDefault().unbroadcastIntent(
                    mMainThread.getApplicationThread(), intent, getUserId());
        } catch (RemoteException e) {
        }
    }

    @Override
    public void sendStickyBroadcastAsUser(Intent intent, UserHandle user) {
        String resolvedType = intent.resolveTypeIfNeeded(getContentResolver());
        try {
            intent.prepareToLeaveProcess();
            ActivityManagerNative.getDefault().broadcastIntent(
                mMainThread.getApplicationThread(), intent, resolvedType, null,
                Activity.RESULT_OK, null, null, null, AppOpsManager.OP_NONE, false, true, user.getIdentifier());
        } catch (RemoteException e) {
        }
    }

    @Override
    public void sendStickyOrderedBroadcastAsUser(Intent intent,
            UserHandle user, BroadcastReceiver resultReceiver,
            Handler scheduler, int initialCode, String initialData,
            Bundle initialExtras) {
        IIntentReceiver rd = null;
        if (resultReceiver != null) {
            if (mPackageInfo != null) {
                if (scheduler == null) {
                    scheduler = mMainThread.getHandler();
                }
                rd = mPackageInfo.getReceiverDispatcher(
                    resultReceiver, getOuterContext(), scheduler,
                    mMainThread.getInstrumentation(), false);
            } else {
                if (scheduler == null) {
                    scheduler = mMainThread.getHandler();
                }
                rd = new LoadedApk.ReceiverDispatcher(
                        resultReceiver, getOuterContext(), scheduler, null, false).getIIntentReceiver();
            }
        }
        String resolvedType = intent.resolveTypeIfNeeded(getContentResolver());
        try {
            intent.prepareToLeaveProcess();
            ActivityManagerNative.getDefault().broadcastIntent(
                mMainThread.getApplicationThread(), intent, resolvedType, rd,
                initialCode, initialData, initialExtras, null,
                    AppOpsManager.OP_NONE, true, true, user.getIdentifier());
        } catch (RemoteException e) {
        }
    }

    @Override
    public void removeStickyBroadcastAsUser(Intent intent, UserHandle user) {
        String resolvedType = intent.resolveTypeIfNeeded(getContentResolver());
        if (resolvedType != null) {
            intent = new Intent(intent);
            intent.setDataAndType(intent.getData(), resolvedType);
        }
        try {
            intent.prepareToLeaveProcess();
            ActivityManagerNative.getDefault().unbroadcastIntent(
                    mMainThread.getApplicationThread(), intent, user.getIdentifier());
        } catch (RemoteException e) {
        }
    }

    @Override
    public Intent registerReceiver(BroadcastReceiver receiver, IntentFilter filter) {
        return registerReceiver(receiver, filter, null, null);
    }

    @Override
    public Intent registerReceiver(BroadcastReceiver receiver, IntentFilter filter,
            String broadcastPermission, Handler scheduler) {
        return registerReceiverInternal(receiver, getUserId(),
                filter, broadcastPermission, scheduler, getOuterContext());
    }

    @Override
    public Intent registerReceiverAsUser(BroadcastReceiver receiver, UserHandle user,
            IntentFilter filter, String broadcastPermission, Handler scheduler) {
        return registerReceiverInternal(receiver, user.getIdentifier(),
                filter, broadcastPermission, scheduler, getOuterContext());
    }

    private Intent registerReceiverInternal(BroadcastReceiver receiver, int userId,
            IntentFilter filter, String broadcastPermission,
            Handler scheduler, Context context) {
        IIntentReceiver rd = null;
        if (receiver != null) {
            if (mPackageInfo != null && context != null) {
                if (scheduler == null) {
                    scheduler = mMainThread.getHandler();
                }
                rd = mPackageInfo.getReceiverDispatcher(
                    receiver, context, scheduler,
                    mMainThread.getInstrumentation(), true);
            } else {
                if (scheduler == null) {
                    scheduler = mMainThread.getHandler();
                }
                rd = new LoadedApk.ReceiverDispatcher(
                        receiver, context, scheduler, null, true).getIIntentReceiver();
            }
        }
        try {
            return ActivityManagerNative.getDefault().registerReceiver(
                    mMainThread.getApplicationThread(), mBasePackageName,
                    rd, filter, broadcastPermission, userId);
        } catch (RemoteException e) {
            return null;
        }
    }

    @Override
    public void unregisterReceiver(BroadcastReceiver receiver) {
        if (mPackageInfo != null) {
            IIntentReceiver rd = mPackageInfo.forgetReceiverDispatcher(
                    getOuterContext(), receiver);
            try {
                ActivityManagerNative.getDefault().unregisterReceiver(rd);
            } catch (RemoteException e) {
            }
        } else {
            throw new RuntimeException("Not supported in system context");
        }
    }

    private void validateServiceIntent(Intent service) {
        if (service.getComponent() == null && service.getPackage() == null) {
            if (getApplicationInfo().targetSdkVersion >= Build.VERSION_CODES.LOLLIPOP) {
                IllegalArgumentException ex = new IllegalArgumentException(
                        "Service Intent must be explicit: " + service);
                throw ex;
            } else {
                Log.w(TAG, "Implicit intents with startService are not safe: " + service
                        + " " + Debug.getCallers(2, 3));
            }
        }
    }

    @Override
    public ComponentName startService(Intent service) {
        warnIfCallingFromSystemProcess();
        return startServiceCommon(service, mUser);
    }

    @Override
    public boolean stopService(Intent service) {
        warnIfCallingFromSystemProcess();
        return stopServiceCommon(service, mUser);
    }

    @Override
    public ComponentName startServiceAsUser(Intent service, UserHandle user) {
        return startServiceCommon(service, user);
    }

    private ComponentName startServiceCommon(Intent service, UserHandle user) {
        try {
            validateServiceIntent(service);
            service.prepareToLeaveProcess();
            ComponentName cn = ActivityManagerNative.getDefault().startService(
                mMainThread.getApplicationThread(), service,
                service.resolveTypeIfNeeded(getContentResolver()), user.getIdentifier());
            if (cn != null) {
                if (cn.getPackageName().equals("!")) {
                    throw new SecurityException(
                            "Not allowed to start service " + service
                            + " without permission " + cn.getClassName());
                } else if (cn.getPackageName().equals("!!")) {
                    throw new SecurityException(
                            "Unable to start service " + service
                            + ": " + cn.getClassName());
                }
            }
            return cn;
        } catch (RemoteException e) {
            return null;
        }
    }

    @Override
    public boolean stopServiceAsUser(Intent service, UserHandle user) {
        return stopServiceCommon(service, user);
    }

    private boolean stopServiceCommon(Intent service, UserHandle user) {
        try {
            validateServiceIntent(service);
            service.prepareToLeaveProcess();
            int res = ActivityManagerNative.getDefault().stopService(
                mMainThread.getApplicationThread(), service,
                service.resolveTypeIfNeeded(getContentResolver()), user.getIdentifier());
            if (res < 0) {
                throw new SecurityException(
                        "Not allowed to stop service " + service);
            }
            return res != 0;
        } catch (RemoteException e) {
            return false;
        }
    }

    @Override
    public boolean bindService(Intent service, ServiceConnection conn,
            int flags) {
        warnIfCallingFromSystemProcess();
        return bindServiceCommon(service, conn, flags, Process.myUserHandle());
    }

    /** @hide */
    @Override
    public boolean bindServiceAsUser(Intent service, ServiceConnection conn, int flags,
            UserHandle user) {
        return bindServiceCommon(service, conn, flags, user);
    }

    private boolean bindServiceCommon(Intent service, ServiceConnection conn, int flags,
            UserHandle user) {
        IServiceConnection sd;
        if (conn == null) {
            throw new IllegalArgumentException("connection is null");
        }
        if (mPackageInfo != null) {
            sd = mPackageInfo.getServiceDispatcher(conn, getOuterContext(),
                    mMainThread.getHandler(), flags);
        } else {
            throw new RuntimeException("Not supported in system context");
        }
        validateServiceIntent(service);
        try {
            IBinder token = getActivityToken();
            if (token == null && (flags&BIND_AUTO_CREATE) == 0 && mPackageInfo != null
                    && mPackageInfo.getApplicationInfo().targetSdkVersion
                    < android.os.Build.VERSION_CODES.ICE_CREAM_SANDWICH) {
                flags |= BIND_WAIVE_PRIORITY;
            }
            service.prepareToLeaveProcess();
            int res = ActivityManagerNative.getDefault().bindService(
                mMainThread.getApplicationThread(), getActivityToken(),
                service, service.resolveTypeIfNeeded(getContentResolver()),
                sd, flags, user.getIdentifier());
            if (res < 0) {
                throw new SecurityException(
                        "Not allowed to bind to service " + service);
            }
            return res != 0;
        } catch (RemoteException e) {
            return false;
        }
    }

    @Override
    public void unbindService(ServiceConnection conn) {
        if (conn == null) {
            throw new IllegalArgumentException("connection is null");
        }
        if (mPackageInfo != null) {
            IServiceConnection sd = mPackageInfo.forgetServiceDispatcher(
                    getOuterContext(), conn);
            try {
                ActivityManagerNative.getDefault().unbindService(sd);
            } catch (RemoteException e) {
            }
        } else {
            throw new RuntimeException("Not supported in system context");
        }
    }

    @Override
    public boolean startInstrumentation(ComponentName className,
            String profileFile, Bundle arguments) {
        try {
            if (arguments != null) {
                arguments.setAllowFds(false);
            }
            return ActivityManagerNative.getDefault().startInstrumentation(
                    className, profileFile, 0, arguments, null, null, getUserId(),
                    null /* ABI override */);
        } catch (RemoteException e) {
            // System has crashed, nothing we can do.
        }
        return false;
    }

    @Override
    public Object getSystemService(String name) {
        ServiceFetcher fetcher = SYSTEM_SERVICE_MAP.get(name);
        return fetcher == null ? null : fetcher.getService(this);
    }

    private WallpaperManager getWallpaperManager() {
        return (WallpaperManager) WALLPAPER_FETCHER.getService(this);
    }

    /* package */ static DropBoxManager createDropBoxManager() {
        IBinder b = ServiceManager.getService(DROPBOX_SERVICE);
        IDropBoxManagerService service = IDropBoxManagerService.Stub.asInterface(b);
        if (service == null) {
            // Don't return a DropBoxManager that will NPE upon use.
            // This also avoids caching a broken DropBoxManager in
            // getDropBoxManager during early boot, before the
            // DROPBOX_SERVICE is registered.
            return null;
        }
        return new DropBoxManager(service);
    }

    @Override
    public int checkPermission(String permission, int pid, int uid) {
        if (permission == null) {
            throw new IllegalArgumentException("permission is null");
        }

        try {
            return ActivityManagerNative.getDefault().checkPermission(
                    permission, pid, uid);
        } catch (RemoteException e) {
            return PackageManager.PERMISSION_DENIED;
        }
    }

    /** @hide */
    @Override
    public int checkPermission(String permission, int pid, int uid, IBinder callerToken) {
        if (permission == null) {
            throw new IllegalArgumentException("permission is null");
        }

        try {
            return ActivityManagerNative.getDefault().checkPermissionWithToken(
                    permission, pid, uid, callerToken);
        } catch (RemoteException e) {
            return PackageManager.PERMISSION_DENIED;
        }
    }

    @Override
    public int checkCallingPermission(String permission) {
        if (permission == null) {
            throw new IllegalArgumentException("permission is null");
        }

        int pid = Binder.getCallingPid();
        if (pid != Process.myPid()) {
            return checkPermission(permission, pid, Binder.getCallingUid());
        }
        return PackageManager.PERMISSION_DENIED;
    }

    @Override
    public int checkCallingOrSelfPermission(String permission) {
        if (permission == null) {
            throw new IllegalArgumentException("permission is null");
        }

        return checkPermission(permission, Binder.getCallingPid(),
                Binder.getCallingUid());
    }

    private void enforce(
            String permission, int resultOfCheck,
            boolean selfToo, int uid, String message) {
        if (resultOfCheck != PackageManager.PERMISSION_GRANTED) {
            throw new SecurityException(
                    (message != null ? (message + ": ") : "") +
                    (selfToo
                     ? "Neither user " + uid + " nor current process has "
                     : "uid " + uid + " does not have ") +
                    permission +
                    ".");
        }
    }

    public void enforcePermission(
            String permission, int pid, int uid, String message) {
        enforce(permission,
                checkPermission(permission, pid, uid),
                false,
                uid,
                message);
    }

    public void enforceCallingPermission(String permission, String message) {
        enforce(permission,
                checkCallingPermission(permission),
                false,
                Binder.getCallingUid(),
                message);
    }

    public void enforceCallingOrSelfPermission(
            String permission, String message) {
        enforce(permission,
                checkCallingOrSelfPermission(permission),
                true,
                Binder.getCallingUid(),
                message);
    }

    @Override
    public void grantUriPermission(String toPackage, Uri uri, int modeFlags) {
         try {
            ActivityManagerNative.getDefault().grantUriPermission(
                    mMainThread.getApplicationThread(), toPackage,
                    ContentProvider.getUriWithoutUserId(uri), modeFlags, resolveUserId(uri));
        } catch (RemoteException e) {
        }
    }

    @Override
    public void revokeUriPermission(Uri uri, int modeFlags) {
         try {
            ActivityManagerNative.getDefault().revokeUriPermission(
                    mMainThread.getApplicationThread(),
                    ContentProvider.getUriWithoutUserId(uri), modeFlags, resolveUserId(uri));
        } catch (RemoteException e) {
        }
    }

    @Override
    public int checkUriPermission(Uri uri, int pid, int uid, int modeFlags) {
        try {
            return ActivityManagerNative.getDefault().checkUriPermission(
                    ContentProvider.getUriWithoutUserId(uri), pid, uid, modeFlags,
                    resolveUserId(uri), null);
        } catch (RemoteException e) {
            return PackageManager.PERMISSION_DENIED;
        }
    }

    /** @hide */
    @Override
    public int checkUriPermission(Uri uri, int pid, int uid, int modeFlags, IBinder callerToken) {
        try {
            return ActivityManagerNative.getDefault().checkUriPermission(
                    ContentProvider.getUriWithoutUserId(uri), pid, uid, modeFlags,
                    resolveUserId(uri), callerToken);
        } catch (RemoteException e) {
            return PackageManager.PERMISSION_DENIED;
        }
    }

    private int resolveUserId(Uri uri) {
        return ContentProvider.getUserIdFromUri(uri, getUserId());
    }

    @Override
    public int checkCallingUriPermission(Uri uri, int modeFlags) {
        int pid = Binder.getCallingPid();
        if (pid != Process.myPid()) {
            return checkUriPermission(uri, pid,
                    Binder.getCallingUid(), modeFlags);
        }
        return PackageManager.PERMISSION_DENIED;
    }

    @Override
    public int checkCallingOrSelfUriPermission(Uri uri, int modeFlags) {
        return checkUriPermission(uri, Binder.getCallingPid(),
                Binder.getCallingUid(), modeFlags);
    }

    @Override
    public int checkUriPermission(Uri uri, String readPermission,
            String writePermission, int pid, int uid, int modeFlags) {
        if (DEBUG) {
            Log.i("foo", "checkUriPermission: uri=" + uri + "readPermission="
                    + readPermission + " writePermission=" + writePermission
                    + " pid=" + pid + " uid=" + uid + " mode" + modeFlags);
        }
        if ((modeFlags&Intent.FLAG_GRANT_READ_URI_PERMISSION) != 0) {
            if (readPermission == null
                    || checkPermission(readPermission, pid, uid)
                    == PackageManager.PERMISSION_GRANTED) {
                return PackageManager.PERMISSION_GRANTED;
            }
        }
        if ((modeFlags&Intent.FLAG_GRANT_WRITE_URI_PERMISSION) != 0) {
            if (writePermission == null
                    || checkPermission(writePermission, pid, uid)
                    == PackageManager.PERMISSION_GRANTED) {
                return PackageManager.PERMISSION_GRANTED;
            }
        }
        return uri != null ? checkUriPermission(uri, pid, uid, modeFlags)
                : PackageManager.PERMISSION_DENIED;
    }

    private String uriModeFlagToString(int uriModeFlags) {
        StringBuilder builder = new StringBuilder();
        if ((uriModeFlags & Intent.FLAG_GRANT_READ_URI_PERMISSION) != 0) {
            builder.append("read and ");
        }
        if ((uriModeFlags & Intent.FLAG_GRANT_WRITE_URI_PERMISSION) != 0) {
            builder.append("write and ");
        }
        if ((uriModeFlags & Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION) != 0) {
            builder.append("persistable and ");
        }
        if ((uriModeFlags & Intent.FLAG_GRANT_PREFIX_URI_PERMISSION) != 0) {
            builder.append("prefix and ");
        }

        if (builder.length() > 5) {
            builder.setLength(builder.length() - 5);
            return builder.toString();
        } else {
            throw new IllegalArgumentException("Unknown permission mode flags: " + uriModeFlags);
        }
    }

    private void enforceForUri(
            int modeFlags, int resultOfCheck, boolean selfToo,
            int uid, Uri uri, String message) {
        if (resultOfCheck != PackageManager.PERMISSION_GRANTED) {
            throw new SecurityException(
                    (message != null ? (message + ": ") : "") +
                    (selfToo
                     ? "Neither user " + uid + " nor current process has "
                     : "User " + uid + " does not have ") +
                    uriModeFlagToString(modeFlags) +
                    " permission on " +
                    uri +
                    ".");
        }
    }

    public void enforceUriPermission(
            Uri uri, int pid, int uid, int modeFlags, String message) {
        enforceForUri(
                modeFlags, checkUriPermission(uri, pid, uid, modeFlags),
                false, uid, uri, message);
    }

    public void enforceCallingUriPermission(
            Uri uri, int modeFlags, String message) {
        enforceForUri(
                modeFlags, checkCallingUriPermission(uri, modeFlags),
                false,
                Binder.getCallingUid(), uri, message);
    }

    public void enforceCallingOrSelfUriPermission(
            Uri uri, int modeFlags, String message) {
        enforceForUri(
                modeFlags,
                checkCallingOrSelfUriPermission(uri, modeFlags), true,
                Binder.getCallingUid(), uri, message);
    }

    public void enforceUriPermission(
            Uri uri, String readPermission, String writePermission,
            int pid, int uid, int modeFlags, String message) {
        enforceForUri(modeFlags,
                      checkUriPermission(
                              uri, readPermission, writePermission, pid, uid,
                              modeFlags),
                      false,
                      uid,
                      uri,
                      message);
    }

    /**
     * Logs a warning if the system process directly called a method such as
     * {@link #startService(Intent)} instead of {@link #startServiceAsUser(Intent, UserHandle)}.
     * The "AsUser" variants allow us to properly enforce the user's restrictions.
     */
    private void warnIfCallingFromSystemProcess() {
        if (Process.myUid() == Process.SYSTEM_UID) {
            Slog.w(TAG, "Calling a method in the system process without a qualified user: "
                    + Debug.getCallers(5));
        }
    }

    @Override
    public Context createApplicationContext(ApplicationInfo application, int flags)
            throws NameNotFoundException {
        return createApplicationContext(application, null, flags);
    }

    @Override
    public Context createApplicationContext(ApplicationInfo application, String themePackageName,
            int flags) throws NameNotFoundException {
        LoadedApk pi = mMainThread.getPackageInfo(application, mResources.getCompatibilityInfo(),
                flags | CONTEXT_REGISTER_PACKAGE);
        if (pi != null) {
            final boolean restricted = (flags & CONTEXT_RESTRICTED) == CONTEXT_RESTRICTED;
            ContextImpl c = new ContextImpl(this, mMainThread, pi, mActivityToken,
                    new UserHandle(UserHandle.getUserId(application.uid)), restricted,
                    mDisplay, mOverrideConfiguration, themePackageName);
            if (c.mResources != null) {
                return c;
            }
        }

        throw new PackageManager.NameNotFoundException(
                "Application package " + application.packageName + " not found");
    }

    @Override
    public Context createPackageContext(String packageName, int flags)
            throws NameNotFoundException {
        return createPackageContextAsUser(packageName, null, flags,
                mUser != null ? mUser : Process.myUserHandle());
    }

    @Override
    public Context createPackageContextAsUser(String packageName, int flags, UserHandle user)
            throws NameNotFoundException {
        return createPackageContextAsUser(packageName, null, flags, user);
    }

    @Override
    public Context createPackageContextAsUser(String packageName, String themePackageName,
            int flags, UserHandle user) throws NameNotFoundException {
        final boolean restricted = (flags & CONTEXT_RESTRICTED) == CONTEXT_RESTRICTED;
        if (packageName.equals("system") || packageName.equals("android")) {
            return new ContextImpl(this, mMainThread, mPackageInfo, mActivityToken,
                    user, restricted, mDisplay, mOverrideConfiguration, themePackageName);
        }

        LoadedApk pi = mMainThread.getPackageInfo(packageName, mResources.getCompatibilityInfo(),
                flags | CONTEXT_REGISTER_PACKAGE, user.getIdentifier());
        if (pi != null) {
            ContextImpl c = new ContextImpl(this, mMainThread, pi, mActivityToken,
                    user, restricted, mDisplay, mOverrideConfiguration, themePackageName);
            if (c.mResources != null) {
                return c;
            }
        }

        // Should be a better exception.
        throw new PackageManager.NameNotFoundException(
                "Application package " + packageName + " not found");
    }

    @Override
    public Context createConfigurationContext(Configuration overrideConfiguration) {
        if (overrideConfiguration == null) {
            throw new IllegalArgumentException("overrideConfiguration must not be null");
        }

        return new ContextImpl(this, mMainThread, mPackageInfo, mActivityToken,
                mUser, mRestricted, mDisplay, overrideConfiguration);
    }

    @Override
    public Context createDisplayContext(Display display) {
        if (display == null) {
            throw new IllegalArgumentException("display must not be null");
        }

        return new ContextImpl(this, mMainThread, mPackageInfo, mActivityToken,
                mUser, mRestricted, display, mOverrideConfiguration);
    }

    private int getDisplayId() {
        return mDisplay != null ? mDisplay.getDisplayId() : Display.DEFAULT_DISPLAY;
    }

    @Override
    public boolean isRestricted() {
        return mRestricted;
    }

    @Override
    public DisplayAdjustments getDisplayAdjustments(int displayId) {
        return mDisplayAdjustments;
    }

    private File getDataDirFile() {
        if (mPackageInfo != null) {
            return mPackageInfo.getDataDirFile();
        }
        throw new RuntimeException("Not supported in system context");
    }

    @Override
    public File getDir(String name, int mode) {
        name = "app_" + name;
        File file = makeFilename(getDataDirFile(), name);
        if (!file.exists()) {
            file.mkdir();
            setFilePermissionsFromMode(file.getPath(), mode,
                    FileUtils.S_IRWXU|FileUtils.S_IRWXG|FileUtils.S_IXOTH);
        }
        return file;
    }

    /** {@hide} */
    public int getUserId() {
        return mUser.getIdentifier();
    }

    static ContextImpl createSystemContext(ActivityThread mainThread) {
        LoadedApk packageInfo = new LoadedApk(mainThread);
        ContextImpl context = new ContextImpl(null, mainThread,
                packageInfo, null, null, false, null, null, null);
        context.mResources.updateConfiguration(context.mResourcesManager.getConfiguration(),
                context.mResourcesManager.getDisplayMetricsLocked(Display.DEFAULT_DISPLAY));
        return context;
    }

    static ContextImpl createAppContext(ActivityThread mainThread, LoadedApk packageInfo) {
        if (packageInfo == null) throw new IllegalArgumentException("packageInfo");
        return new ContextImpl(null, mainThread,
                packageInfo, null, null, false, null, null, null);
    }

    static ContextImpl createActivityContext(ActivityThread mainThread,
            LoadedApk packageInfo, IBinder activityToken) {
        if (packageInfo == null) throw new IllegalArgumentException("packageInfo");
        if (activityToken == null) throw new IllegalArgumentException("activityInfo");
        return new ContextImpl(null, mainThread,
                packageInfo, activityToken, null, false, null, null, null);
    }

    private ContextImpl(ContextImpl container, ActivityThread mainThread,
            LoadedApk packageInfo, IBinder activityToken, UserHandle user, boolean restricted,
            Display display, Configuration overrideConfiguration) {
        this(container, mainThread, packageInfo, activityToken, user, restricted, display,
                overrideConfiguration, null);
    }

    private ContextImpl(ContextImpl container, ActivityThread mainThread,
            LoadedApk packageInfo, IBinder activityToken, UserHandle user, boolean restricted,
            Display display, Configuration overrideConfiguration, String themePackageName) {
        mOuterContext = this;

        mMainThread = mainThread;
        mActivityToken = activityToken;
        mRestricted = restricted;

        if (user == null) {
            user = Process.myUserHandle();
        }
        mUser = user;

        mPackageInfo = packageInfo;
        mResourcesManager = ResourcesManager.getInstance();
        mDisplay = display;
        mOverrideConfiguration = overrideConfiguration;

        final int displayId = getDisplayId();
        CompatibilityInfo compatInfo = null;
        if (container != null) {
            compatInfo = container.getDisplayAdjustments(displayId).getCompatibilityInfo();
        }
        if (compatInfo == null && displayId == Display.DEFAULT_DISPLAY) {
            compatInfo = packageInfo.getCompatibilityInfo();
        }
        mDisplayAdjustments.setCompatibilityInfo(compatInfo);
        mDisplayAdjustments.setActivityToken(activityToken);

        Resources resources = packageInfo.getResources(mainThread);
        if (resources != null) {
            if (activityToken != null || themePackageName != null
                    || displayId != Display.DEFAULT_DISPLAY
                    || overrideConfiguration != null
                    || (compatInfo != null && compatInfo.applicationScale
                            != resources.getCompatibilityInfo().applicationScale)) {
                resources = themePackageName == null ? mResourcesManager.getTopLevelResources(
                        packageInfo.getResDir(), packageInfo.getSplitResDirs(),
                        packageInfo.getOverlayDirs(),
                        packageInfo.getApplicationInfo().sharedLibraryFiles, displayId,
                        packageInfo.getAppDir(), overrideConfiguration, compatInfo, activityToken,
                        mOuterContext) :
                mResourcesManager.getTopLevelThemedResources(packageInfo.getResDir(), displayId,
                        packageInfo.getPackageName(), themePackageName, compatInfo ,activityToken);
            }
        }
        mResources = resources;

        if (container != null) {
            mBasePackageName = container.mBasePackageName;
            mOpPackageName = container.mOpPackageName;
        } else {
            mBasePackageName = packageInfo.mPackageName;
            ApplicationInfo ainfo = packageInfo.getApplicationInfo();
            if (ainfo.uid == Process.SYSTEM_UID && ainfo.uid != Process.myUid()) {
                // Special case: system components allow themselves to be loaded in to other
                // processes.  For purposes of app ops, we must then consider the context as
                // belonging to the package of this process, not the system itself, otherwise
                // the package+uid verifications in app ops will fail.
                mOpPackageName = ActivityThread.currentPackageName();
            } else {
                mOpPackageName = mBasePackageName;
            }
        }

        mContentResolver = new ApplicationContentResolver(this, mainThread, user);
    }

    void installSystemApplicationInfo(ApplicationInfo info, ClassLoader classLoader) {
        mPackageInfo.installSystemApplicationInfo(info, classLoader);
    }

    final void scheduleFinalCleanup(String who, String what) {
        mMainThread.scheduleContextCleanup(this, who, what);
    }

    final void performFinalCleanup(String who, String what) {
        //Log.i(TAG, "Cleanup up context: " + this);
        mPackageInfo.removeContextRegistrations(getOuterContext(), who, what);
    }

    final Context getReceiverRestrictedContext() {
        if (mReceiverRestrictedContext != null) {
            return mReceiverRestrictedContext;
        }
        return mReceiverRestrictedContext = new ReceiverRestrictedContext(getOuterContext());
    }

    final void setOuterContext(Context context) {
        mOuterContext = context;
    }

    final Context getOuterContext() {
        return mOuterContext;
    }

    final IBinder getActivityToken() {
        return mActivityToken;
    }

    static void setFilePermissionsFromMode(String name, int mode,
            int extraPermissions) {
        int perms = FileUtils.S_IRUSR|FileUtils.S_IWUSR
            |FileUtils.S_IRGRP|FileUtils.S_IWGRP
            |extraPermissions;
        if ((mode&MODE_WORLD_READABLE) != 0) {
            perms |= FileUtils.S_IROTH;
        }
        if ((mode&MODE_WORLD_WRITEABLE) != 0) {
            perms |= FileUtils.S_IWOTH;
        }
        if (DEBUG) {
            Log.i(TAG, "File " + name + ": mode=0x" + Integer.toHexString(mode)
                  + ", perms=0x" + Integer.toHexString(perms));
        }
        FileUtils.setPermissions(name, perms, -1, -1);
    }

    private File validateFilePath(String name, boolean createDirectory) {
        File dir;
        File f;

        if (name.charAt(0) == File.separatorChar) {
            String dirPath = name.substring(0, name.lastIndexOf(File.separatorChar));
            dir = new File(dirPath);
            name = name.substring(name.lastIndexOf(File.separatorChar));
            f = new File(dir, name);
        } else {
            dir = getDatabasesDir();
            f = makeFilename(dir, name);
        }

        if (createDirectory && !dir.isDirectory() && dir.mkdir()) {
            FileUtils.setPermissions(dir.getPath(),
                FileUtils.S_IRWXU|FileUtils.S_IRWXG|FileUtils.S_IXOTH,
                -1, -1);
        }

        return f;
    }

    private File makeFilename(File base, String name) {
        if (name.indexOf(File.separatorChar) < 0) {
            return new File(base, name);
        }
        throw new IllegalArgumentException(
                "File " + name + " contains a path separator");
    }

    /**
     * Ensure that given directories exist, trying to create them if missing. If
     * unable to create, they are filtered by replacing with {@code null}.
     */
    private File[] ensureDirsExistOrFilter(File[] dirs) {
        ArrayList<File> result = new ArrayList<File>(dirs.length);
        for (int i = 0; i < dirs.length; i++) {
            File dir = dirs[i];
            if (Environment.MEDIA_REMOVED.equals(Environment.getStorageState(dir))) {
                continue;
            }
            if (!dir.exists()) {
                if (!dir.mkdirs()) {
                    // recheck existence in case of cross-process race
                    if (!dir.exists()) {
                        // Failing to mkdir() may be okay, since we might not have
                        // enough permissions; ask vold to create on our behalf.
                        final IMountService mount = IMountService.Stub.asInterface(
                                ServiceManager.getService("mount"));
                        int res = -1;
                        try {
                            res = mount.mkdirs(getPackageName(), dir.getAbsolutePath());
                        } catch (Exception ignored) {
                        }
                        if (res != 0) {
                            Log.w(TAG, "Failed to ensure directory: " + dir);
                            dir = null;
                        }
                    }
                }
            }
            result.add(dir);
        }
        return result.toArray(new File[result.size()]);
    }

    // ----------------------------------------------------------------------
    // ----------------------------------------------------------------------
    // ----------------------------------------------------------------------

    private static final class ApplicationContentResolver extends ContentResolver {
        private final ActivityThread mMainThread;
        private final UserHandle mUser;

        public ApplicationContentResolver(
                Context context, ActivityThread mainThread, UserHandle user) {
            super(context);
            mMainThread = Preconditions.checkNotNull(mainThread);
            mUser = Preconditions.checkNotNull(user);
        }

        @Override
        protected IContentProvider acquireProvider(Context context, String auth) {
            return mMainThread.acquireProvider(context,
                    ContentProvider.getAuthorityWithoutUserId(auth),
                    resolveUserIdFromAuthority(auth), true);
        }

        @Override
        protected IContentProvider acquireExistingProvider(Context context, String auth) {
            return mMainThread.acquireExistingProvider(context,
                    ContentProvider.getAuthorityWithoutUserId(auth),
                    resolveUserIdFromAuthority(auth), true);
        }

        @Override
        public boolean releaseProvider(IContentProvider provider) {
            return mMainThread.releaseProvider(provider, true);
        }

        @Override
        protected IContentProvider acquireUnstableProvider(Context c, String auth) {
            return mMainThread.acquireProvider(c,
                    ContentProvider.getAuthorityWithoutUserId(auth),
                    resolveUserIdFromAuthority(auth), false);
        }

        @Override
        public boolean releaseUnstableProvider(IContentProvider icp) {
            return mMainThread.releaseProvider(icp, false);
        }

        @Override
        public void unstableProviderDied(IContentProvider icp) {
            mMainThread.handleUnstableProviderDied(icp.asBinder(), true);
        }

        @Override
        public void appNotRespondingViaProvider(IContentProvider icp) {
            mMainThread.appNotRespondingViaProvider(icp.asBinder());
        }

        /** @hide */
        protected int resolveUserIdFromAuthority(String auth) {
            return ContentProvider.getUserIdFromAuthority(auth, mUser.getIdentifier());
        }
    }
}


File: core/java/android/os/BatteryManager.java
/*
 * Copyright (C) 2008 The Android Open Source Project
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

package android.os;

import android.os.BatteryProperty;
import android.os.IBatteryPropertiesRegistrar;
import android.os.RemoteException;
import android.os.ServiceManager;

/**
 * The BatteryManager class contains strings and constants used for values
 * in the {@link android.content.Intent#ACTION_BATTERY_CHANGED} Intent, and
 * provides a method for querying battery and charging properties.
 */
public class BatteryManager {
    /**
     * Extra for {@link android.content.Intent#ACTION_BATTERY_CHANGED}:
     * integer containing the current status constant.
     */
    public static final String EXTRA_STATUS = "status";
    
    /**
     * Extra for {@link android.content.Intent#ACTION_BATTERY_CHANGED}:
     * integer containing the current health constant.
     */
    public static final String EXTRA_HEALTH = "health";
    
    /**
     * Extra for {@link android.content.Intent#ACTION_BATTERY_CHANGED}:
     * boolean indicating whether a battery is present.
     */
    public static final String EXTRA_PRESENT = "present";
    
    /**
     * Extra for {@link android.content.Intent#ACTION_BATTERY_CHANGED}:
     * integer field containing the current battery level, from 0 to
     * {@link #EXTRA_SCALE}.
     */
    public static final String EXTRA_LEVEL = "level";
    
    /**
     * Extra for {@link android.content.Intent#ACTION_BATTERY_CHANGED}:
     * integer containing the maximum battery level.
     */
    public static final String EXTRA_SCALE = "scale";
    
    /**
     * Extra for {@link android.content.Intent#ACTION_BATTERY_CHANGED}:
     * integer containing the resource ID of a small status bar icon
     * indicating the current battery state.
     */
    public static final String EXTRA_ICON_SMALL = "icon-small";
    
    /**
     * Extra for {@link android.content.Intent#ACTION_BATTERY_CHANGED}:
     * integer indicating whether the device is plugged in to a power
     * source; 0 means it is on battery, other constants are different
     * types of power sources.
     */
    public static final String EXTRA_PLUGGED = "plugged";
    
    /**
     * Extra for {@link android.content.Intent#ACTION_BATTERY_CHANGED}:
     * integer containing the current battery voltage level.
     */
    public static final String EXTRA_VOLTAGE = "voltage";
    
    /**
     * Extra for {@link android.content.Intent#ACTION_BATTERY_CHANGED}:
     * integer containing the current battery temperature.
     */
    public static final String EXTRA_TEMPERATURE = "temperature";
    
    /**
     * Extra for {@link android.content.Intent#ACTION_BATTERY_CHANGED}:
     * String describing the technology of the current battery.
     */
    public static final String EXTRA_TECHNOLOGY = "technology";

    /**
     * Extra for {@link android.content.Intent#ACTION_BATTERY_CHANGED}:
     * Int value set to nonzero if an unsupported charger is attached
     * to the device.
     * {@hide}
     */
    public static final String EXTRA_INVALID_CHARGER = "invalid_charger";

    // values for "status" field in the ACTION_BATTERY_CHANGED Intent
    public static final int BATTERY_STATUS_UNKNOWN = 1;
    public static final int BATTERY_STATUS_CHARGING = 2;
    public static final int BATTERY_STATUS_DISCHARGING = 3;
    public static final int BATTERY_STATUS_NOT_CHARGING = 4;
    public static final int BATTERY_STATUS_FULL = 5;

    // values for "health" field in the ACTION_BATTERY_CHANGED Intent
    public static final int BATTERY_HEALTH_UNKNOWN = 1;
    public static final int BATTERY_HEALTH_GOOD = 2;
    public static final int BATTERY_HEALTH_OVERHEAT = 3;
    public static final int BATTERY_HEALTH_DEAD = 4;
    public static final int BATTERY_HEALTH_OVER_VOLTAGE = 5;
    public static final int BATTERY_HEALTH_UNSPECIFIED_FAILURE = 6;
    public static final int BATTERY_HEALTH_COLD = 7;

    // values of the "plugged" field in the ACTION_BATTERY_CHANGED intent.
    // These must be powers of 2.
    /** Power source is an AC charger. */
    public static final int BATTERY_PLUGGED_AC = 1;
    /** Power source is a USB port. */
    public static final int BATTERY_PLUGGED_USB = 2;
    /** Power source is wireless. */
    public static final int BATTERY_PLUGGED_WIRELESS = 4;

    /** @hide */
    public static final int BATTERY_PLUGGED_ANY =
            BATTERY_PLUGGED_AC | BATTERY_PLUGGED_USB | BATTERY_PLUGGED_WIRELESS;

    /*
     * Battery property identifiers.  These must match the values in
     * frameworks/native/include/batteryservice/BatteryService.h
     */
    /** Battery capacity in microampere-hours, as an integer. */
    public static final int BATTERY_PROPERTY_CHARGE_COUNTER = 1;

    /**
     * Instantaneous battery current in microamperes, as an integer.  Positive
     * values indicate net current entering the battery from a charge source,
     * negative values indicate net current discharging from the battery.
     */
    public static final int BATTERY_PROPERTY_CURRENT_NOW = 2;

    /**
     * Average battery current in microamperes, as an integer.  Positive
     * values indicate net current entering the battery from a charge source,
     * negative values indicate net current discharging from the battery.
     * The time period over which the average is computed may depend on the
     * fuel gauge hardware and its configuration.
     */
    public static final int BATTERY_PROPERTY_CURRENT_AVERAGE = 3;

    /**
     * Remaining battery capacity as an integer percentage of total capacity
     * (with no fractional part).
     */
    public static final int BATTERY_PROPERTY_CAPACITY = 4;

    /**
     * Battery remaining energy in nanowatt-hours, as a long integer.
     */
    public static final int BATTERY_PROPERTY_ENERGY_COUNTER = 5;

    private IBatteryPropertiesRegistrar mBatteryPropertiesRegistrar;

    /**
     * Query a battery property from the batteryproperties service.
     *
     * Returns the requested value, or Long.MIN_VALUE if property not
     * supported on this system or on other error.
     */
    private long queryProperty(int id) {
        long ret;

        if (mBatteryPropertiesRegistrar == null) {
            IBinder b = ServiceManager.getService("batteryproperties");
            mBatteryPropertiesRegistrar =
                IBatteryPropertiesRegistrar.Stub.asInterface(b);

            if (mBatteryPropertiesRegistrar == null)
                return Long.MIN_VALUE;
        }

        try {
            BatteryProperty prop = new BatteryProperty();

            if (mBatteryPropertiesRegistrar.getProperty(id, prop) == 0)
                ret = prop.getLong();
            else
                ret = Long.MIN_VALUE;
        } catch (RemoteException e) {
            ret = Long.MIN_VALUE;
        }

        return ret;
    }

    /**
     * Return the value of a battery property of integer type.  If the
     * platform does not provide the property queried, this value will
     * be Integer.MIN_VALUE.
     *
     * @param id identifier of the requested property
     *
     * @return the property value, or Integer.MIN_VALUE if not supported.
     */
    public int getIntProperty(int id) {
        return (int)queryProperty(id);
    }

    /**
     * Return the value of a battery property of long type If the
     * platform does not provide the property queried, this value will
     * be Long.MIN_VALUE.
     *
     * @param id identifier of the requested property
     *
     * @return the property value, or Long.MIN_VALUE if not supported.
     */
    public long getLongProperty(int id) {
        return queryProperty(id);
    }
}


File: core/java/android/os/BatteryManagerInternal.java
/*
 * Copyright (C) 2014 The Android Open Source Project
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

package android.os;

/**
 * Battery manager local system service interface.
 *
 * @hide Only for use within the system server.
 */
public abstract class BatteryManagerInternal {
    /**
     * Returns true if the device is plugged into any of the specified plug types.
     */
    public abstract boolean isPowered(int plugTypeSet);

    /**
     * Returns the current plug type.
     */
    public abstract int getPlugType();

    /**
     * Returns battery level as a percentage.
     */
    public abstract int getBatteryLevel();

    /**
     * Returns whether we currently consider the battery level to be low.
     */
    public abstract boolean getBatteryLevelLow();

    /**
     * Returns a non-zero value if an unsupported charger is attached.
     */
    public abstract int getInvalidCharger();
}


File: core/java/android/os/BatteryProperties.java
/* Copyright 2013, The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
*/

package android.os;

/**
 * {@hide}
 */
public class BatteryProperties implements Parcelable {
    public boolean chargerAcOnline;
    public boolean chargerUsbOnline;
    public boolean chargerWirelessOnline;
    public int batteryStatus;
    public int batteryHealth;
    public boolean batteryPresent;
    public int batteryLevel;
    public int batteryVoltage;
    public int batteryTemperature;
    public String batteryTechnology;

    public BatteryProperties() {
    }

    public void set(BatteryProperties other) {
        chargerAcOnline = other.chargerAcOnline;
        chargerUsbOnline = other.chargerUsbOnline;
        chargerWirelessOnline = other.chargerWirelessOnline;
        batteryStatus = other.batteryStatus;
        batteryHealth = other.batteryHealth;
        batteryPresent = other.batteryPresent;
        batteryLevel = other.batteryLevel;
        batteryVoltage = other.batteryVoltage;
        batteryTemperature = other.batteryTemperature;
        batteryTechnology = other.batteryTechnology;
    }

    /*
     * Parcel read/write code must be kept in sync with
     * frameworks/native/services/batteryservice/BatteryProperties.cpp
     */

    private BatteryProperties(Parcel p) {
        chargerAcOnline = p.readInt() == 1 ? true : false;
        chargerUsbOnline = p.readInt() == 1 ? true : false;
        chargerWirelessOnline = p.readInt() == 1 ? true : false;
        batteryStatus = p.readInt();
        batteryHealth = p.readInt();
        batteryPresent = p.readInt() == 1 ? true : false;
        batteryLevel = p.readInt();
        batteryVoltage = p.readInt();
        batteryTemperature = p.readInt();
        batteryTechnology = p.readString();
    }

    public void writeToParcel(Parcel p, int flags) {
        p.writeInt(chargerAcOnline ? 1 : 0);
        p.writeInt(chargerUsbOnline ? 1 : 0);
        p.writeInt(chargerWirelessOnline ? 1 : 0);
        p.writeInt(batteryStatus);
        p.writeInt(batteryHealth);
        p.writeInt(batteryPresent ? 1 : 0);
        p.writeInt(batteryLevel);
        p.writeInt(batteryVoltage);
        p.writeInt(batteryTemperature);
        p.writeString(batteryTechnology);
    }

    public static final Parcelable.Creator<BatteryProperties> CREATOR
        = new Parcelable.Creator<BatteryProperties>() {
        public BatteryProperties createFromParcel(Parcel p) {
            return new BatteryProperties(p);
        }

        public BatteryProperties[] newArray(int size) {
            return new BatteryProperties[size];
        }
    };

    public int describeContents() {
        return 0;
    }
}


File: core/java/com/android/internal/os/BatteryStatsHelper.java
/*
 * Copyright (C) 2009 The Android Open Source Project
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

package com.android.internal.os;

import static android.os.BatteryStats.NETWORK_MOBILE_RX_DATA;
import static android.os.BatteryStats.NETWORK_MOBILE_TX_DATA;
import static android.os.BatteryStats.NETWORK_WIFI_RX_DATA;
import static android.os.BatteryStats.NETWORK_WIFI_TX_DATA;

import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.hardware.Sensor;
import android.hardware.SensorManager;
import android.net.ConnectivityManager;
import android.os.BatteryStats;
import android.os.BatteryStats.Uid;
import android.os.Bundle;
import android.os.MemoryFile;
import android.os.Parcel;
import android.os.ParcelFileDescriptor;
import android.os.Process;
import android.os.RemoteException;
import android.os.ServiceManager;
import android.os.SystemClock;
import android.os.UserHandle;
import android.telephony.SignalStrength;
import android.util.ArrayMap;
import android.util.Log;
import android.util.SparseArray;

import com.android.internal.app.IBatteryStats;
import com.android.internal.os.BatterySipper.DrainType;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

/**
 * A helper class for retrieving the power usage information for all applications and services.
 *
 * The caller must initialize this class as soon as activity object is ready to use (for example, in
 * onAttach() for Fragment), call create() in onCreate() and call destroy() in onDestroy().
 */
public final class BatteryStatsHelper {

    private static final boolean DEBUG = false;

    private static final String TAG = BatteryStatsHelper.class.getSimpleName();

    private static BatteryStats sStatsXfer;
    private static Intent sBatteryBroadcastXfer;
    private static ArrayMap<File, BatteryStats> sFileXfer = new ArrayMap<>();

    final private Context mContext;
    final private boolean mCollectBatteryBroadcast;
    final private boolean mWifiOnly;

    private IBatteryStats mBatteryInfo;
    private BatteryStats mStats;
    private Intent mBatteryBroadcast;
    private PowerProfile mPowerProfile;

    private final List<BatterySipper> mUsageList = new ArrayList<BatterySipper>();
    private final List<BatterySipper> mWifiSippers = new ArrayList<BatterySipper>();
    private final List<BatterySipper> mBluetoothSippers = new ArrayList<BatterySipper>();
    private final SparseArray<List<BatterySipper>> mUserSippers
            = new SparseArray<List<BatterySipper>>();
    private final SparseArray<Double> mUserPower = new SparseArray<Double>();

    private final List<BatterySipper> mMobilemsppList = new ArrayList<BatterySipper>();

    private int mStatsType = BatteryStats.STATS_SINCE_CHARGED;

    long mRawRealtime;
    long mRawUptime;
    long mBatteryRealtime;
    long mBatteryUptime;
    long mTypeBatteryRealtime;
    long mTypeBatteryUptime;
    long mBatteryTimeRemaining;
    long mChargeTimeRemaining;

    private long mStatsPeriod = 0;
    private double mMaxPower = 1;
    private double mMaxRealPower = 1;
    private double mComputedPower;
    private double mTotalPower;
    private double mWifiPower;
    private double mBluetoothPower;
    private double mMinDrainedPower;
    private double mMaxDrainedPower;

    // How much the apps together have kept the mobile radio active.
    private long mAppMobileActive;

    // How much the apps together have left WIFI running.
    private long mAppWifiRunning;

    public BatteryStatsHelper(Context context) {
        this(context, true);
    }

    public BatteryStatsHelper(Context context, boolean collectBatteryBroadcast) {
        mContext = context;
        mCollectBatteryBroadcast = collectBatteryBroadcast;
        mWifiOnly = checkWifiOnly(context);
    }

    public BatteryStatsHelper(Context context, boolean collectBatteryBroadcast, boolean wifiOnly) {
        mContext = context;
        mCollectBatteryBroadcast = collectBatteryBroadcast;
        mWifiOnly = wifiOnly;
    }

    public static boolean checkWifiOnly(Context context) {
        ConnectivityManager cm = (ConnectivityManager)context.getSystemService(
                Context.CONNECTIVITY_SERVICE);
        return !cm.isNetworkSupported(ConnectivityManager.TYPE_MOBILE);
    }

    public void storeStatsHistoryInFile(String fname) {
        synchronized (sFileXfer) {
            File path = makeFilePath(mContext, fname);
            sFileXfer.put(path, this.getStats());
            FileOutputStream fout = null;
            try {
                fout = new FileOutputStream(path);
                Parcel hist = Parcel.obtain();
                getStats().writeToParcelWithoutUids(hist, 0);
                byte[] histData = hist.marshall();
                fout.write(histData);
            } catch (IOException e) {
                Log.w(TAG, "Unable to write history to file", e);
            } finally {
                if (fout != null) {
                    try {
                        fout.close();
                    } catch (IOException e) {
                    }
                }
            }
        }
    }

    public static BatteryStats statsFromFile(Context context, String fname) {
        synchronized (sFileXfer) {
            File path = makeFilePath(context, fname);
            BatteryStats stats = sFileXfer.get(path);
            if (stats != null) {
                return stats;
            }
            FileInputStream fin = null;
            try {
                fin = new FileInputStream(path);
                byte[] data = readFully(fin);
                Parcel parcel = Parcel.obtain();
                parcel.unmarshall(data, 0, data.length);
                parcel.setDataPosition(0);
                return com.android.internal.os.BatteryStatsImpl.CREATOR.createFromParcel(parcel);
            } catch (IOException e) {
                Log.w(TAG, "Unable to read history to file", e);
            } finally {
                if (fin != null) {
                    try {
                        fin.close();
                    } catch (IOException e) {
                    }
                }
            }
        }
        return getStats(IBatteryStats.Stub.asInterface(
                        ServiceManager.getService(BatteryStats.SERVICE_NAME)));
    }

    public static void dropFile(Context context, String fname) {
        makeFilePath(context, fname).delete();
    }

    private static File makeFilePath(Context context, String fname) {
        return new File(context.getFilesDir(), fname);
    }

    /** Clears the current stats and forces recreating for future use. */
    public void clearStats() {
        mStats = null;
    }

    public BatteryStats getStats() {
        if (mStats == null) {
            load();
        }
        return mStats;
    }

    public Intent getBatteryBroadcast() {
        if (mBatteryBroadcast == null && mCollectBatteryBroadcast) {
            load();
        }
        return mBatteryBroadcast;
    }

    public PowerProfile getPowerProfile() {
        return mPowerProfile;
    }

    public void create(BatteryStats stats) {
        mPowerProfile = new PowerProfile(mContext);
        mStats = stats;
    }

    public void create(Bundle icicle) {
        if (icicle != null) {
            mStats = sStatsXfer;
            mBatteryBroadcast = sBatteryBroadcastXfer;
        }
        mBatteryInfo = IBatteryStats.Stub.asInterface(
                ServiceManager.getService(BatteryStats.SERVICE_NAME));
        mPowerProfile = new PowerProfile(mContext);
    }

    public void storeState() {
        sStatsXfer = mStats;
        sBatteryBroadcastXfer = mBatteryBroadcast;
    }

    public static String makemAh(double power) {
        if (power < .00001) return String.format("%.8f", power);
        else if (power < .0001) return String.format("%.7f", power);
        else if (power < .001) return String.format("%.6f", power);
        else if (power < .01) return String.format("%.5f", power);
        else if (power < .1) return String.format("%.4f", power);
        else if (power < 1) return String.format("%.3f", power);
        else if (power < 10) return String.format("%.2f", power);
        else if (power < 100) return String.format("%.1f", power);
        else return String.format("%.0f", power);
    }

    /**
     * Refreshes the power usage list.
     */
    public void refreshStats(int statsType, int asUser) {
        SparseArray<UserHandle> users = new SparseArray<UserHandle>(1);
        users.put(asUser, new UserHandle(asUser));
        refreshStats(statsType, users);
    }

    /**
     * Refreshes the power usage list.
     */
    public void refreshStats(int statsType, List<UserHandle> asUsers) {
        final int n = asUsers.size();
        SparseArray<UserHandle> users = new SparseArray<UserHandle>(n);
        for (int i = 0; i < n; ++i) {
            UserHandle userHandle = asUsers.get(i);
            users.put(userHandle.getIdentifier(), userHandle);
        }
        refreshStats(statsType, users);
    }

    /**
     * Refreshes the power usage list.
     */
    public void refreshStats(int statsType, SparseArray<UserHandle> asUsers) {
        refreshStats(statsType, asUsers, SystemClock.elapsedRealtime() * 1000,
                SystemClock.uptimeMillis() * 1000);
    }

    public void refreshStats(int statsType, SparseArray<UserHandle> asUsers, long rawRealtimeUs,
            long rawUptimeUs) {
        // Initialize mStats if necessary.
        getStats();

        mMaxPower = 0;
        mMaxRealPower = 0;
        mComputedPower = 0;
        mTotalPower = 0;
        mWifiPower = 0;
        mBluetoothPower = 0;
        mAppMobileActive = 0;
        mAppWifiRunning = 0;

        mUsageList.clear();
        mWifiSippers.clear();
        mBluetoothSippers.clear();
        mUserSippers.clear();
        mUserPower.clear();
        mMobilemsppList.clear();

        if (mStats == null) {
            return;
        }

        mStatsType = statsType;
        mRawUptime = rawUptimeUs;
        mRawRealtime = rawRealtimeUs;
        mBatteryUptime = mStats.getBatteryUptime(rawUptimeUs);
        mBatteryRealtime = mStats.getBatteryRealtime(rawRealtimeUs);
        mTypeBatteryUptime = mStats.computeBatteryUptime(rawUptimeUs, mStatsType);
        mTypeBatteryRealtime = mStats.computeBatteryRealtime(rawRealtimeUs, mStatsType);
        mBatteryTimeRemaining = mStats.computeBatteryTimeRemaining(rawRealtimeUs);
        mChargeTimeRemaining = mStats.computeChargeTimeRemaining(rawRealtimeUs);

        if (DEBUG) {
            Log.d(TAG, "Raw time: realtime=" + (rawRealtimeUs/1000) + " uptime="
                    + (rawUptimeUs/1000));
            Log.d(TAG, "Battery time: realtime=" + (mBatteryRealtime/1000) + " uptime="
                    + (mBatteryUptime/1000));
            Log.d(TAG, "Battery type time: realtime=" + (mTypeBatteryRealtime/1000) + " uptime="
                    + (mTypeBatteryUptime/1000));
        }
        mMinDrainedPower = (mStats.getLowDischargeAmountSinceCharge()
                * mPowerProfile.getBatteryCapacity()) / 100;
        mMaxDrainedPower = (mStats.getHighDischargeAmountSinceCharge()
                * mPowerProfile.getBatteryCapacity()) / 100;

        processAppUsage(asUsers);

        // Before aggregating apps in to users, collect all apps to sort by their ms per packet.
        for (int i=0; i<mUsageList.size(); i++) {
            BatterySipper bs = mUsageList.get(i);
            bs.computeMobilemspp();
            if (bs.mobilemspp != 0) {
                mMobilemsppList.add(bs);
            }
        }
        for (int i=0; i<mUserSippers.size(); i++) {
            List<BatterySipper> user = mUserSippers.valueAt(i);
            for (int j=0; j<user.size(); j++) {
                BatterySipper bs = user.get(j);
                bs.computeMobilemspp();
                if (bs.mobilemspp != 0) {
                    mMobilemsppList.add(bs);
                }
            }
        }
        Collections.sort(mMobilemsppList, new Comparator<BatterySipper>() {
            @Override
            public int compare(BatterySipper lhs, BatterySipper rhs) {
                if (lhs.mobilemspp < rhs.mobilemspp) {
                    return 1;
                } else if (lhs.mobilemspp > rhs.mobilemspp) {
                    return -1;
                }
                return 0;
            }
        });

        processMiscUsage();

        if (DEBUG) {
            Log.d(TAG, "Accuracy: total computed=" + makemAh(mComputedPower) + ", min discharge="
                    + makemAh(mMinDrainedPower) + ", max discharge=" + makemAh(mMaxDrainedPower));
        }
        mTotalPower = mComputedPower;
        if (mStats.getLowDischargeAmountSinceCharge() > 1) {
            if (mMinDrainedPower > mComputedPower) {
                double amount = mMinDrainedPower - mComputedPower;
                mTotalPower = mMinDrainedPower;
                addEntryNoTotal(BatterySipper.DrainType.UNACCOUNTED, 0, amount);
            } else if (mMaxDrainedPower < mComputedPower) {
                double amount = mComputedPower - mMaxDrainedPower;
                addEntryNoTotal(BatterySipper.DrainType.OVERCOUNTED, 0, amount);
            }
        }

        Collections.sort(mUsageList);
    }

    private void processAppUsage(SparseArray<UserHandle> asUsers) {
        final boolean forAllUsers = (asUsers.get(UserHandle.USER_ALL) != null);
        SensorManager sensorManager = (SensorManager) mContext.getSystemService(
                Context.SENSOR_SERVICE);
        final int which = mStatsType;
        final int speedSteps = mPowerProfile.getNumSpeedSteps();
        final double[] powerCpuNormal = new double[speedSteps];
        final long[] cpuSpeedStepTimes = new long[speedSteps];
        for (int p = 0; p < speedSteps; p++) {
            powerCpuNormal[p] = mPowerProfile.getAveragePower(PowerProfile.POWER_CPU_ACTIVE, p);
        }
        final double mobilePowerPerPacket = getMobilePowerPerPacket();
        final double mobilePowerPerMs = getMobilePowerPerMs();
        final double wifiPowerPerPacket = getWifiPowerPerPacket();
        long appWakelockTimeUs = 0;
        BatterySipper osApp = null;
        mStatsPeriod = mTypeBatteryRealtime;
        SparseArray<? extends Uid> uidStats = mStats.getUidStats();
        final int NU = uidStats.size();
        for (int iu = 0; iu < NU; iu++) {
            Uid u = uidStats.valueAt(iu);
            double p; // in mAs
            double power = 0; // in mAs
            double highestDrain = 0;
            String packageWithHighestDrain = null;
            Map<String, ? extends BatteryStats.Uid.Proc> processStats = u.getProcessStats();
            long cpuTime = 0;
            long cpuFgTime = 0;
            long wakelockTime = 0;
            long gpsTime = 0;
            if (processStats.size() > 0) {
                // Process CPU time
                for (Map.Entry<String, ? extends BatteryStats.Uid.Proc> ent
                        : processStats.entrySet()) {
                    Uid.Proc ps = ent.getValue();
                    final long userTime = ps.getUserTime(which);
                    final long systemTime = ps.getSystemTime(which);
                    final long foregroundTime = ps.getForegroundTime(which);
                    cpuFgTime += foregroundTime * 10; // convert to millis
                    final long tmpCpuTime = (userTime + systemTime) * 10; // convert to millis
                    int totalTimeAtSpeeds = 0;
                    // Get the total first
                    for (int step = 0; step < speedSteps; step++) {
                        cpuSpeedStepTimes[step] = ps.getTimeAtCpuSpeedStep(step, which);
                        totalTimeAtSpeeds += cpuSpeedStepTimes[step];
                    }
                    if (totalTimeAtSpeeds == 0) totalTimeAtSpeeds = 1;
                    // Then compute the ratio of time spent at each speed
                    double processPower = 0;
                    for (int step = 0; step < speedSteps; step++) {
                        double ratio = (double) cpuSpeedStepTimes[step] / totalTimeAtSpeeds;
                        if (DEBUG && ratio != 0) Log.d(TAG, "UID " + u.getUid() + ": CPU step #"
                                + step + " ratio=" + makemAh(ratio) + " power="
                                + makemAh(ratio*tmpCpuTime*powerCpuNormal[step] / (60*60*1000)));
                        processPower += ratio * tmpCpuTime * powerCpuNormal[step];
                    }
                    cpuTime += tmpCpuTime;
                    if (DEBUG && processPower != 0) {
                        Log.d(TAG, String.format("process %s, cpu power=%s",
                                ent.getKey(), makemAh(processPower / (60*60*1000))));
                    }
                    power += processPower;
                    if (packageWithHighestDrain == null
                            || packageWithHighestDrain.startsWith("*")) {
                        highestDrain = processPower;
                        packageWithHighestDrain = ent.getKey();
                    } else if (highestDrain < processPower
                            && !ent.getKey().startsWith("*")) {
                        highestDrain = processPower;
                        packageWithHighestDrain = ent.getKey();
                    }
                }
            }
            if (cpuFgTime > cpuTime) {
                if (DEBUG && cpuFgTime > cpuTime + 10000) {
                    Log.d(TAG, "WARNING! Cputime is more than 10 seconds behind Foreground time");
                }
                cpuTime = cpuFgTime; // Statistics may not have been gathered yet.
            }
            power /= (60*60*1000);

            // Process wake lock usage
            Map<String, ? extends BatteryStats.Uid.Wakelock> wakelockStats = u.getWakelockStats();
            for (Map.Entry<String, ? extends BatteryStats.Uid.Wakelock> wakelockEntry
                    : wakelockStats.entrySet()) {
                Uid.Wakelock wakelock = wakelockEntry.getValue();
                // Only care about partial wake locks since full wake locks
                // are canceled when the user turns the screen off.
                BatteryStats.Timer timer = wakelock.getWakeTime(BatteryStats.WAKE_TYPE_PARTIAL);
                if (timer != null) {
                    wakelockTime += timer.getTotalTimeLocked(mRawRealtime, which);
                }
            }
            appWakelockTimeUs += wakelockTime;
            wakelockTime /= 1000; // convert to millis

            // Add cost of holding a wake lock
            p = (wakelockTime
                    * mPowerProfile.getAveragePower(PowerProfile.POWER_CPU_AWAKE)) / (60*60*1000);
            if (DEBUG && p != 0) Log.d(TAG, "UID " + u.getUid() + ": wake "
                    + wakelockTime + " power=" + makemAh(p));
            power += p;

            // Add cost of mobile traffic
            final long mobileRx = u.getNetworkActivityPackets(NETWORK_MOBILE_RX_DATA, mStatsType);
            final long mobileTx = u.getNetworkActivityPackets(NETWORK_MOBILE_TX_DATA, mStatsType);
            final long mobileRxB = u.getNetworkActivityBytes(NETWORK_MOBILE_RX_DATA, mStatsType);
            final long mobileTxB = u.getNetworkActivityBytes(NETWORK_MOBILE_TX_DATA, mStatsType);
            final long mobileActive = u.getMobileRadioActiveTime(mStatsType);
            if (mobileActive > 0) {
                // We are tracking when the radio is up, so can use the active time to
                // determine power use.
                mAppMobileActive += mobileActive;
                p = (mobilePowerPerMs * mobileActive) / 1000;
            } else {
                // We are not tracking when the radio is up, so must approximate power use
                // based on the number of packets.
                p = (mobileRx + mobileTx) * mobilePowerPerPacket;
            }
            if (DEBUG && p != 0) Log.d(TAG, "UID " + u.getUid() + ": mobile packets "
                    + (mobileRx+mobileTx) + " active time " + mobileActive
                    + " power=" + makemAh(p));
            power += p;

            // Add cost of wifi traffic
            final long wifiRx = u.getNetworkActivityPackets(NETWORK_WIFI_RX_DATA, mStatsType);
            final long wifiTx = u.getNetworkActivityPackets(NETWORK_WIFI_TX_DATA, mStatsType);
            final long wifiRxB = u.getNetworkActivityBytes(NETWORK_WIFI_RX_DATA, mStatsType);
            final long wifiTxB = u.getNetworkActivityBytes(NETWORK_WIFI_TX_DATA, mStatsType);
            p = (wifiRx + wifiTx) * wifiPowerPerPacket;
            if (DEBUG && p != 0) Log.d(TAG, "UID " + u.getUid() + ": wifi packets "
                    + (mobileRx+mobileTx) + " power=" + makemAh(p));
            power += p;

            // Add cost of keeping WIFI running.
            long wifiRunningTimeMs = u.getWifiRunningTime(mRawRealtime, which) / 1000;
            mAppWifiRunning += wifiRunningTimeMs;
            p = (wifiRunningTimeMs
                    * mPowerProfile.getAveragePower(PowerProfile.POWER_WIFI_ON)) / (60*60*1000);
            if (DEBUG && p != 0) Log.d(TAG, "UID " + u.getUid() + ": wifi running "
                    + wifiRunningTimeMs + " power=" + makemAh(p));
            power += p;

            // Add cost of WIFI scans
            long wifiScanTimeMs = u.getWifiScanTime(mRawRealtime, which) / 1000;
            p = (wifiScanTimeMs
                    * mPowerProfile.getAveragePower(PowerProfile.POWER_WIFI_SCAN)) / (60*60*1000);
            if (DEBUG) Log.d(TAG, "UID " + u.getUid() + ": wifi scan " + wifiScanTimeMs
                    + " power=" + makemAh(p));
            power += p;
            for (int bin = 0; bin < BatteryStats.Uid.NUM_WIFI_BATCHED_SCAN_BINS; bin++) {
                long batchScanTimeMs = u.getWifiBatchedScanTime(bin, mRawRealtime, which) / 1000;
                p = ((batchScanTimeMs
                        * mPowerProfile.getAveragePower(PowerProfile.POWER_WIFI_BATCHED_SCAN, bin))
                    ) / (60*60*1000);
                if (DEBUG && p != 0) Log.d(TAG, "UID " + u.getUid() + ": wifi batched scan # " + bin
                        + " time=" + batchScanTimeMs + " power=" + makemAh(p));
                power += p;
            }

            // Process Sensor usage
            SparseArray<? extends BatteryStats.Uid.Sensor> sensorStats = u.getSensorStats();
            int NSE = sensorStats.size();
            for (int ise=0; ise<NSE; ise++) {
                Uid.Sensor sensor = sensorStats.valueAt(ise);
                int sensorHandle = sensorStats.keyAt(ise);
                BatteryStats.Timer timer = sensor.getSensorTime();
                long sensorTime = timer.getTotalTimeLocked(mRawRealtime, which) / 1000;
                double multiplier = 0;
                switch (sensorHandle) {
                    case Uid.Sensor.GPS:
                        multiplier = mPowerProfile.getAveragePower(PowerProfile.POWER_GPS_ON);
                        gpsTime = sensorTime;
                        break;
                    default:
                        List<Sensor> sensorList = sensorManager.getSensorList(
                                android.hardware.Sensor.TYPE_ALL);
                        for (android.hardware.Sensor s : sensorList) {
                            if (s.getHandle() == sensorHandle) {
                                multiplier = s.getPower();
                                break;
                            }
                        }
                }
                p = (multiplier * sensorTime) / (60*60*1000);
                if (DEBUG && p != 0) Log.d(TAG, "UID " + u.getUid() + ": sensor #" + sensorHandle
                        + " time=" + sensorTime + " power=" + makemAh(p));
                power += p;
            }

            if (DEBUG && power != 0) Log.d(TAG, String.format("UID %d: total power=%s",
                    u.getUid(), makemAh(power)));

            // Add the app to the list if it is consuming power
            final int userId = UserHandle.getUserId(u.getUid());
            if (power != 0 || u.getUid() == 0) {
                BatterySipper app = new BatterySipper(BatterySipper.DrainType.APP, u,
                        new double[] {power});
                app.cpuTime = cpuTime;
                app.gpsTime = gpsTime;
                app.wifiRunningTime = wifiRunningTimeMs;
                app.cpuFgTime = cpuFgTime;
                app.wakeLockTime = wakelockTime;
                app.mobileRxPackets = mobileRx;
                app.mobileTxPackets = mobileTx;
                app.mobileActive = mobileActive / 1000;
                app.mobileActiveCount = u.getMobileRadioActiveCount(mStatsType);
                app.wifiRxPackets = wifiRx;
                app.wifiTxPackets = wifiTx;
                app.mobileRxBytes = mobileRxB;
                app.mobileTxBytes = mobileTxB;
                app.wifiRxBytes = wifiRxB;
                app.wifiTxBytes = wifiTxB;
                app.packageWithHighestDrain = packageWithHighestDrain;
                if (u.getUid() == Process.WIFI_UID) {
                    mWifiSippers.add(app);
                    mWifiPower += power;
                } else if (u.getUid() == Process.BLUETOOTH_UID) {
                    mBluetoothSippers.add(app);
                    mBluetoothPower += power;
                } else if (!forAllUsers && asUsers.get(userId) == null
                        && UserHandle.getAppId(u.getUid()) >= Process.FIRST_APPLICATION_UID) {
                    List<BatterySipper> list = mUserSippers.get(userId);
                    if (list == null) {
                        list = new ArrayList<BatterySipper>();
                        mUserSippers.put(userId, list);
                    }
                    list.add(app);
                    if (power != 0) {
                        Double userPower = mUserPower.get(userId);
                        if (userPower == null) {
                            userPower = power;
                        } else {
                            userPower += power;
                        }
                        mUserPower.put(userId, userPower);
                    }
                } else {
                    mUsageList.add(app);
                    if (power > mMaxPower) mMaxPower = power;
                    if (power > mMaxRealPower) mMaxRealPower = power;
                    mComputedPower += power;
                }
                if (u.getUid() == 0) {
                    osApp = app;
                }
            }
        }

        // The device has probably been awake for longer than the screen on
        // time and application wake lock time would account for.  Assign
        // this remainder to the OS, if possible.
        if (osApp != null) {
            long wakeTimeMillis = mBatteryUptime / 1000;
            wakeTimeMillis -= (appWakelockTimeUs / 1000)
                    + (mStats.getScreenOnTime(mRawRealtime, which) / 1000);
            if (wakeTimeMillis > 0) {
                double power = (wakeTimeMillis
                        * mPowerProfile.getAveragePower(PowerProfile.POWER_CPU_AWAKE))
                        /  (60*60*1000);
                if (DEBUG) Log.d(TAG, "OS wakeLockTime " + wakeTimeMillis + " power "
                        + makemAh(power));
                osApp.wakeLockTime += wakeTimeMillis;
                osApp.value += power;
                osApp.values[0] += power;
                if (osApp.value > mMaxPower) mMaxPower = osApp.value;
                if (osApp.value > mMaxRealPower) mMaxRealPower = osApp.value;
                mComputedPower += power;
            }
        }
    }

    private void addPhoneUsage() {
        long phoneOnTimeMs = mStats.getPhoneOnTime(mRawRealtime, mStatsType) / 1000;
        double phoneOnPower = mPowerProfile.getAveragePower(PowerProfile.POWER_RADIO_ACTIVE)
                * phoneOnTimeMs / (60*60*1000);
        if (phoneOnPower != 0) {
            BatterySipper bs = addEntry(BatterySipper.DrainType.PHONE, phoneOnTimeMs, phoneOnPower);
        }
    }

    private void addScreenUsage() {
        double power = 0;
        long screenOnTimeMs = mStats.getScreenOnTime(mRawRealtime, mStatsType) / 1000;
        power += screenOnTimeMs * mPowerProfile.getAveragePower(PowerProfile.POWER_SCREEN_ON);
        final double screenFullPower =
                mPowerProfile.getAveragePower(PowerProfile.POWER_SCREEN_FULL);
        for (int i = 0; i < BatteryStats.NUM_SCREEN_BRIGHTNESS_BINS; i++) {
            double screenBinPower = screenFullPower * (i + 0.5f)
                    / BatteryStats.NUM_SCREEN_BRIGHTNESS_BINS;
            long brightnessTime = mStats.getScreenBrightnessTime(i, mRawRealtime, mStatsType)
                    / 1000;
            double p = screenBinPower*brightnessTime;
            if (DEBUG && p != 0) {
                Log.d(TAG, "Screen bin #" + i + ": time=" + brightnessTime
                        + " power=" + makemAh(p / (60 * 60 * 1000)));
            }
            power += p;
        }
        power /= (60*60*1000); // To hours
        if (power != 0) {
            addEntry(BatterySipper.DrainType.SCREEN, screenOnTimeMs, power);
        }
    }

    private void addRadioUsage() {
        double power = 0;
        final int BINS = SignalStrength.NUM_SIGNAL_STRENGTH_BINS;
        long signalTimeMs = 0;
        long noCoverageTimeMs = 0;
        for (int i = 0; i < BINS; i++) {
            long strengthTimeMs = mStats.getPhoneSignalStrengthTime(i, mRawRealtime, mStatsType)
                    / 1000;
            double p = (strengthTimeMs * mPowerProfile.getAveragePower(PowerProfile.POWER_RADIO_ON, i))
                        / (60*60*1000);
            if (DEBUG && p != 0) {
                Log.d(TAG, "Cell strength #" + i + ": time=" + strengthTimeMs + " power="
                        + makemAh(p));
            }
            power += p;
            signalTimeMs += strengthTimeMs;
            if (i == 0) {
                noCoverageTimeMs = strengthTimeMs;
            }
        }
        long scanningTimeMs = mStats.getPhoneSignalScanningTime(mRawRealtime, mStatsType)
                / 1000;
        double p = (scanningTimeMs * mPowerProfile.getAveragePower(
                        PowerProfile.POWER_RADIO_SCANNING))
                        / (60*60*1000);
        if (DEBUG && p != 0) {
            Log.d(TAG, "Cell radio scanning: time=" + scanningTimeMs + " power=" + makemAh(p));
        }
        power += p;
        long radioActiveTimeUs = mStats.getMobileRadioActiveTime(mRawRealtime, mStatsType);
        long remainingActiveTime = (radioActiveTimeUs - mAppMobileActive) / 1000;
        if (remainingActiveTime > 0) {
            power += getMobilePowerPerMs() * remainingActiveTime;
        }
        if (power != 0) {
            BatterySipper bs =
                    addEntry(BatterySipper.DrainType.CELL, signalTimeMs, power);
            if (signalTimeMs != 0) {
                bs.noCoveragePercent = noCoverageTimeMs * 100.0 / signalTimeMs;
            }
            bs.mobileActive = remainingActiveTime;
            bs.mobileActiveCount = mStats.getMobileRadioActiveUnknownCount(mStatsType);
        }
    }

    private void aggregateSippers(BatterySipper bs, List<BatterySipper> from, String tag) {
        for (int i=0; i<from.size(); i++) {
            BatterySipper wbs = from.get(i);
            if (DEBUG) Log.d(TAG, tag + " adding sipper " + wbs + ": cpu=" + wbs.cpuTime);
            bs.cpuTime += wbs.cpuTime;
            bs.gpsTime += wbs.gpsTime;
            bs.wifiRunningTime += wbs.wifiRunningTime;
            bs.cpuFgTime += wbs.cpuFgTime;
            bs.wakeLockTime += wbs.wakeLockTime;
            bs.mobileRxPackets += wbs.mobileRxPackets;
            bs.mobileTxPackets += wbs.mobileTxPackets;
            bs.mobileActive += wbs.mobileActive;
            bs.mobileActiveCount += wbs.mobileActiveCount;
            bs.wifiRxPackets += wbs.wifiRxPackets;
            bs.wifiTxPackets += wbs.wifiTxPackets;
            bs.mobileRxBytes += wbs.mobileRxBytes;
            bs.mobileTxBytes += wbs.mobileTxBytes;
            bs.wifiRxBytes += wbs.wifiRxBytes;
            bs.wifiTxBytes += wbs.wifiTxBytes;
        }
        bs.computeMobilemspp();
    }

    private void addWiFiUsage() {
        long onTimeMs = mStats.getWifiOnTime(mRawRealtime, mStatsType) / 1000;
        long runningTimeMs = mStats.getGlobalWifiRunningTime(mRawRealtime, mStatsType) / 1000;
        if (DEBUG) Log.d(TAG, "WIFI runningTime=" + runningTimeMs
                + " app runningTime=" + mAppWifiRunning);
        runningTimeMs -= mAppWifiRunning;
        if (runningTimeMs < 0) runningTimeMs = 0;
        double wifiPower = (onTimeMs * 0 /* TODO */
                    * mPowerProfile.getAveragePower(PowerProfile.POWER_WIFI_ON)
                + runningTimeMs * mPowerProfile.getAveragePower(PowerProfile.POWER_WIFI_ON))
                / (60*60*1000);
        if (DEBUG && wifiPower != 0) {
            Log.d(TAG, "Wifi: time=" + runningTimeMs + " power=" + makemAh(wifiPower));
        }
        if ((wifiPower+mWifiPower) != 0) {
            BatterySipper bs = addEntry(BatterySipper.DrainType.WIFI, runningTimeMs,
                    wifiPower + mWifiPower);
            aggregateSippers(bs, mWifiSippers, "WIFI");
        }
    }

    private void addIdleUsage() {
        long idleTimeMs = (mTypeBatteryRealtime
                - mStats.getScreenOnTime(mRawRealtime, mStatsType)) / 1000;
        double idlePower = (idleTimeMs * mPowerProfile.getAveragePower(PowerProfile.POWER_CPU_IDLE))
                / (60*60*1000);
        if (DEBUG && idlePower != 0) {
            Log.d(TAG, "Idle: time=" + idleTimeMs + " power=" + makemAh(idlePower));
        }
        if (idlePower != 0) {
            addEntry(BatterySipper.DrainType.IDLE, idleTimeMs, idlePower);
        }
    }

    private void addBluetoothUsage() {
        long btOnTimeMs = mStats.getBluetoothOnTime(mRawRealtime, mStatsType) / 1000;
        double btPower = btOnTimeMs * mPowerProfile.getAveragePower(PowerProfile.POWER_BLUETOOTH_ON)
                / (60*60*1000);
        if (DEBUG && btPower != 0) {
            Log.d(TAG, "Bluetooth: time=" + btOnTimeMs + " power=" + makemAh(btPower));
        }
        int btPingCount = mStats.getBluetoothPingCount();
        double pingPower = (btPingCount
                * mPowerProfile.getAveragePower(PowerProfile.POWER_BLUETOOTH_AT_CMD))
                / (60*60*1000);
        if (DEBUG && pingPower != 0) {
            Log.d(TAG, "Bluetooth ping: count=" + btPingCount + " power=" + makemAh(pingPower));
        }
        btPower += pingPower;
        if ((btPower+mBluetoothPower) != 0) {
            BatterySipper bs = addEntry(BatterySipper.DrainType.BLUETOOTH, btOnTimeMs,
                    btPower + mBluetoothPower);
            aggregateSippers(bs, mBluetoothSippers, "Bluetooth");
        }
    }

    private void addFlashlightUsage() {
        long flashlightOnTimeMs = mStats.getFlashlightOnTime(mRawRealtime, mStatsType) / 1000;
        double flashlightPower = flashlightOnTimeMs
                * mPowerProfile.getAveragePower(PowerProfile.POWER_FLASHLIGHT) / (60*60*1000);
        if (flashlightPower != 0) {
            addEntry(BatterySipper.DrainType.FLASHLIGHT, flashlightOnTimeMs, flashlightPower);
        }
    }

    private void addUserUsage() {
        for (int i=0; i<mUserSippers.size(); i++) {
            final int userId = mUserSippers.keyAt(i);
            final List<BatterySipper> sippers = mUserSippers.valueAt(i);
            Double userPower = mUserPower.get(userId);
            double power = (userPower != null) ? userPower : 0.0;
            BatterySipper bs = addEntry(BatterySipper.DrainType.USER, 0, power);
            bs.userId = userId;
            aggregateSippers(bs, sippers, "User");
        }
    }

    /**
     * Return estimated power (in mAs) of sending or receiving a packet with the mobile radio.
     */
    private double getMobilePowerPerPacket() {
        final long MOBILE_BPS = 200000; // TODO: Extract average bit rates from system
        final double MOBILE_POWER = mPowerProfile.getAveragePower(PowerProfile.POWER_RADIO_ACTIVE)
                / 3600;

        final long mobileRx = mStats.getNetworkActivityPackets(NETWORK_MOBILE_RX_DATA, mStatsType);
        final long mobileTx = mStats.getNetworkActivityPackets(NETWORK_MOBILE_TX_DATA, mStatsType);
        final long mobileData = mobileRx + mobileTx;

        final long radioDataUptimeMs
                = mStats.getMobileRadioActiveTime(mRawRealtime, mStatsType) / 1000;
        final double mobilePps = (mobileData != 0 && radioDataUptimeMs != 0)
                ? (mobileData / (double)radioDataUptimeMs)
                : (((double)MOBILE_BPS) / 8 / 2048);

        return (MOBILE_POWER / mobilePps) / (60*60);
    }

    /**
     * Return estimated power (in mAs) of keeping the radio up
     */
    private double getMobilePowerPerMs() {
        return mPowerProfile.getAveragePower(PowerProfile.POWER_RADIO_ACTIVE) / (60*60*1000);
    }

    /**
     * Return estimated power (in mAs) of sending a byte with the Wi-Fi radio.
     */
    private double getWifiPowerPerPacket() {
        final long WIFI_BPS = 1000000; // TODO: Extract average bit rates from system
        final double WIFI_POWER = mPowerProfile.getAveragePower(PowerProfile.POWER_WIFI_ACTIVE)
                / 3600;
        return (WIFI_POWER / (((double)WIFI_BPS) / 8 / 2048)) / (60*60);
    }

    private void processMiscUsage() {
        addUserUsage();
        addPhoneUsage();
        addScreenUsage();
        addFlashlightUsage();
        addWiFiUsage();
        addBluetoothUsage();
        addIdleUsage(); // Not including cellular idle power
        // Don't compute radio usage if it's a wifi-only device
        if (!mWifiOnly) {
            addRadioUsage();
        }
    }

    private BatterySipper addEntry(DrainType drainType, long time, double power) {
        mComputedPower += power;
        if (power > mMaxRealPower) mMaxRealPower = power;
        return addEntryNoTotal(drainType, time, power);
    }

    private BatterySipper addEntryNoTotal(DrainType drainType, long time, double power) {
        if (power > mMaxPower) mMaxPower = power;
        BatterySipper bs = new BatterySipper(drainType, null, new double[] {power});
        bs.usageTime = time;
        mUsageList.add(bs);
        return bs;
    }

    public List<BatterySipper> getUsageList() {
        return mUsageList;
    }

    public List<BatterySipper> getMobilemsppList() {
        return mMobilemsppList;
    }

    public long getStatsPeriod() { return mStatsPeriod; }

    public int getStatsType() { return mStatsType; };

    public double getMaxPower() { return mMaxPower; }

    public double getMaxRealPower() { return mMaxRealPower; }

    public double getTotalPower() { return mTotalPower; }

    public double getComputedPower() { return mComputedPower; }

    public double getMinDrainedPower() {
        return mMinDrainedPower;
    }

    public double getMaxDrainedPower() {
        return mMaxDrainedPower;
    }

    public long getBatteryTimeRemaining() { return mBatteryTimeRemaining; }

    public long getChargeTimeRemaining() { return mChargeTimeRemaining; }

    public static byte[] readFully(FileInputStream stream) throws java.io.IOException {
        return readFully(stream, stream.available());
    }

    public static byte[] readFully(FileInputStream stream, int avail) throws java.io.IOException {
        int pos = 0;
        byte[] data = new byte[avail];
        while (true) {
            int amt = stream.read(data, pos, data.length-pos);
            //Log.i("foo", "Read " + amt + " bytes at " + pos
            //        + " of avail " + data.length);
            if (amt <= 0) {
                //Log.i("foo", "**** FINISHED READING: pos=" + pos
                //        + " len=" + data.length);
                return data;
            }
            pos += amt;
            avail = stream.available();
            if (avail > data.length-pos) {
                byte[] newData = new byte[pos+avail];
                System.arraycopy(data, 0, newData, 0, pos);
                data = newData;
            }
        }
    }

    private void load() {
        if (mBatteryInfo == null) {
            return;
        }
        mStats = getStats(mBatteryInfo);
        if (mCollectBatteryBroadcast) {
            mBatteryBroadcast = mContext.registerReceiver(null,
                    new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        }
    }

    private static BatteryStatsImpl getStats(IBatteryStats service) {
        try {
            ParcelFileDescriptor pfd = service.getStatisticsStream();
            if (pfd != null) {
                FileInputStream fis = new ParcelFileDescriptor.AutoCloseInputStream(pfd);
                try {
                    byte[] data = readFully(fis, MemoryFile.getSize(pfd.getFileDescriptor()));
                    Parcel parcel = Parcel.obtain();
                    parcel.unmarshall(data, 0, data.length);
                    parcel.setDataPosition(0);
                    BatteryStatsImpl stats = com.android.internal.os.BatteryStatsImpl.CREATOR
                            .createFromParcel(parcel);
                    stats.distributeWorkLocked(BatteryStats.STATS_SINCE_CHARGED);
                    return stats;
                } catch (IOException e) {
                    Log.w(TAG, "Unable to read statistics stream", e);
                }
            }
        } catch (RemoteException e) {
            Log.w(TAG, "RemoteException:", e);
        }
        return new BatteryStatsImpl();
    }
}


File: core/java/com/android/internal/os/BatteryStatsImpl.java
/*
 * Copyright (C) 2006-2007 The Android Open Source Project
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

package com.android.internal.os;

import static android.net.NetworkStats.UID_ALL;
import static com.android.server.NetworkManagementSocketTagger.PROP_QTAGUID_ENABLED;

import android.app.ActivityManager;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothHeadset;
import android.content.Context;
import android.net.ConnectivityManager;
import android.net.NetworkStats;
import android.net.wifi.WifiManager;
import android.os.BadParcelableException;
import android.os.BatteryManager;
import android.os.BatteryStats;
import android.os.Build;
import android.os.FileUtils;
import android.os.Handler;
import android.os.Looper;
import android.os.Message;
import android.os.Parcel;
import android.os.ParcelFormatException;
import android.os.Parcelable;
import android.os.Process;
import android.os.SystemClock;
import android.os.SystemProperties;
import android.os.WorkSource;
import android.telephony.DataConnectionRealTimeInfo;
import android.telephony.ServiceState;
import android.telephony.SignalStrength;
import android.telephony.TelephonyManager;
import android.text.TextUtils;
import android.util.ArrayMap;
import android.util.Log;
import android.util.LogWriter;
import android.util.MutableInt;
import android.util.PrintWriterPrinter;
import android.util.Printer;
import android.util.Slog;
import android.util.SparseArray;
import android.util.SparseIntArray;
import android.util.TimeUtils;
import android.view.Display;

import com.android.internal.annotations.GuardedBy;
import com.android.internal.net.NetworkStatsFactory;
import com.android.internal.util.ArrayUtils;
import com.android.internal.util.FastPrintWriter;
import com.android.internal.util.JournaledFile;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.locks.ReentrantLock;

/**
 * All information we are collecting about things that can happen that impact
 * battery life.  All times are represented in microseconds except where indicated
 * otherwise.
 */
public final class BatteryStatsImpl extends BatteryStats {
    private static final String TAG = "BatteryStatsImpl";
    private static final boolean DEBUG = false;
    private static final boolean DEBUG_HISTORY = false;
    private static final boolean USE_OLD_HISTORY = false;   // for debugging.

    // TODO: remove "tcp" from network methods, since we measure total stats.

    // In-memory Parcel magic number, used to detect attempts to unmarshall bad data
    private static final int MAGIC = 0xBA757475; // 'BATSTATS'

    // Current on-disk Parcel version
    private static final int VERSION = 116 + (USE_OLD_HISTORY ? 1000 : 0);

    // Maximum number of items we will record in the history.
    private static final int MAX_HISTORY_ITEMS = 2000;

    // No, really, THIS is the maximum number of items we will record in the history.
    private static final int MAX_MAX_HISTORY_ITEMS = 3000;

    // The maximum number of names wakelocks we will keep track of
    // per uid; once the limit is reached, we batch the remaining wakelocks
    // in to one common name.
    private static final int MAX_WAKELOCKS_PER_UID = 100;

    private static int sNumSpeedSteps;

    private final JournaledFile mFile;
    public final AtomicFile mCheckinFile;

    static final int MSG_UPDATE_WAKELOCKS = 1;
    static final int MSG_REPORT_POWER_CHANGE = 2;
    static final long DELAY_UPDATE_WAKELOCKS = 5*1000;

    public interface BatteryCallback {
        public void batteryNeedsCpuUpdate();
        public void batteryPowerChanged(boolean onBattery);
    }

    final class MyHandler extends Handler {
        public MyHandler(Looper looper) {
            super(looper, null, true);
        }

        @Override
        public void handleMessage(Message msg) {
            BatteryCallback cb = mCallback;
            switch (msg.what) {
                case MSG_UPDATE_WAKELOCKS:
                    if (cb != null) {
                        cb.batteryNeedsCpuUpdate();
                    }
                    break;
                case MSG_REPORT_POWER_CHANGE:
                    if (cb != null) {
                        cb.batteryPowerChanged(msg.arg1 != 0);
                    }
                    break;
            }
        }
    }

    public final MyHandler mHandler;

    private BatteryCallback mCallback;

    /**
     * Mapping isolated uids to the actual owning app uid.
     */
    final SparseIntArray mIsolatedUids = new SparseIntArray();

    /**
     * The statistics we have collected organized by uids.
     */
    final SparseArray<BatteryStatsImpl.Uid> mUidStats =
        new SparseArray<BatteryStatsImpl.Uid>();

    // A set of pools of currently active timers.  When a timer is queried, we will divide the
    // elapsed time by the number of active timers to arrive at that timer's share of the time.
    // In order to do this, we must refresh each timer whenever the number of active timers
    // changes.
    final ArrayList<StopwatchTimer> mPartialTimers = new ArrayList<StopwatchTimer>();
    final ArrayList<StopwatchTimer> mFullTimers = new ArrayList<StopwatchTimer>();
    final ArrayList<StopwatchTimer> mWindowTimers = new ArrayList<StopwatchTimer>();
    final SparseArray<ArrayList<StopwatchTimer>> mSensorTimers
            = new SparseArray<ArrayList<StopwatchTimer>>();
    final ArrayList<StopwatchTimer> mWifiRunningTimers = new ArrayList<StopwatchTimer>();
    final ArrayList<StopwatchTimer> mFullWifiLockTimers = new ArrayList<StopwatchTimer>();
    final ArrayList<StopwatchTimer> mWifiMulticastTimers = new ArrayList<StopwatchTimer>();
    final ArrayList<StopwatchTimer> mWifiScanTimers = new ArrayList<StopwatchTimer>();
    final SparseArray<ArrayList<StopwatchTimer>> mWifiBatchedScanTimers =
            new SparseArray<ArrayList<StopwatchTimer>>();
    final ArrayList<StopwatchTimer> mAudioTurnedOnTimers = new ArrayList<StopwatchTimer>();
    final ArrayList<StopwatchTimer> mVideoTurnedOnTimers = new ArrayList<StopwatchTimer>();

    // Last partial timers we use for distributing CPU usage.
    final ArrayList<StopwatchTimer> mLastPartialTimers = new ArrayList<StopwatchTimer>();

    // These are the objects that will want to do something when the device
    // is unplugged from power.
    final TimeBase mOnBatteryTimeBase = new TimeBase();

    // These are the objects that will want to do something when the device
    // is unplugged from power *and* the screen is off.
    final TimeBase mOnBatteryScreenOffTimeBase = new TimeBase();

    // Set to true when we want to distribute CPU across wakelocks for the next
    // CPU update, even if we aren't currently running wake locks.
    boolean mDistributeWakelockCpu;

    boolean mShuttingDown;

    final HistoryEventTracker mActiveEvents = new HistoryEventTracker();

    long mHistoryBaseTime;
    boolean mHaveBatteryLevel = false;
    boolean mRecordingHistory = false;
    int mNumHistoryItems;

    static final int MAX_HISTORY_BUFFER = 256*1024; // 256KB
    static final int MAX_MAX_HISTORY_BUFFER = 320*1024; // 320KB
    final Parcel mHistoryBuffer = Parcel.obtain();
    final HistoryItem mHistoryLastWritten = new HistoryItem();
    final HistoryItem mHistoryLastLastWritten = new HistoryItem();
    final HistoryItem mHistoryReadTmp = new HistoryItem();
    final HistoryItem mHistoryAddTmp = new HistoryItem();
    final HashMap<HistoryTag, Integer> mHistoryTagPool = new HashMap<HistoryTag, Integer>();
    String[] mReadHistoryStrings;
    int[] mReadHistoryUids;
    int mReadHistoryChars;
    int mNextHistoryTagIdx = 0;
    int mNumHistoryTagChars = 0;
    int mHistoryBufferLastPos = -1;
    boolean mHistoryOverflow = false;
    long mLastHistoryElapsedRealtime = 0;
    long mTrackRunningHistoryElapsedRealtime = 0;
    long mTrackRunningHistoryUptime = 0;

    final HistoryItem mHistoryCur = new HistoryItem();

    HistoryItem mHistory;
    HistoryItem mHistoryEnd;
    HistoryItem mHistoryLastEnd;
    HistoryItem mHistoryCache;

    private HistoryItem mHistoryIterator;
    private boolean mReadOverflow;
    private boolean mIteratingHistory;

    int mStartCount;

    long mStartClockTime;
    String mStartPlatformVersion;
    String mEndPlatformVersion;

    long mLastRecordedClockTime;
    long mLastRecordedClockRealtime;

    long mUptime;
    long mUptimeStart;
    long mRealtime;
    long mRealtimeStart;

    int mWakeLockNesting;
    boolean mWakeLockImportant;
    boolean mRecordAllHistory;
    boolean mNoAutoReset;

    int mScreenState = Display.STATE_UNKNOWN;
    StopwatchTimer mScreenOnTimer;

    int mScreenBrightnessBin = -1;
    final StopwatchTimer[] mScreenBrightnessTimer = new StopwatchTimer[NUM_SCREEN_BRIGHTNESS_BINS];

    boolean mInteractive;
    StopwatchTimer mInteractiveTimer;

    boolean mLowPowerModeEnabled;
    StopwatchTimer mLowPowerModeEnabledTimer;

    boolean mPhoneOn;
    StopwatchTimer mPhoneOnTimer;

    int mAudioOnNesting;
    StopwatchTimer mAudioOnTimer;

    int mVideoOnNesting;
    StopwatchTimer mVideoOnTimer;

    boolean mFlashlightOn;
    StopwatchTimer mFlashlightOnTimer;

    int mPhoneSignalStrengthBin = -1;
    int mPhoneSignalStrengthBinRaw = -1;
    final StopwatchTimer[] mPhoneSignalStrengthsTimer = 
            new StopwatchTimer[SignalStrength.NUM_SIGNAL_STRENGTH_BINS];

    StopwatchTimer mPhoneSignalScanningTimer;

    int mPhoneDataConnectionType = -1;
    final StopwatchTimer[] mPhoneDataConnectionsTimer =
            new StopwatchTimer[NUM_DATA_CONNECTION_TYPES];

    final LongSamplingCounter[] mNetworkByteActivityCounters =
            new LongSamplingCounter[NUM_NETWORK_ACTIVITY_TYPES];
    final LongSamplingCounter[] mNetworkPacketActivityCounters =
            new LongSamplingCounter[NUM_NETWORK_ACTIVITY_TYPES];

    boolean mWifiOn;
    StopwatchTimer mWifiOnTimer;

    boolean mGlobalWifiRunning;
    StopwatchTimer mGlobalWifiRunningTimer;

    int mWifiState = -1;
    final StopwatchTimer[] mWifiStateTimer = new StopwatchTimer[NUM_WIFI_STATES];

    int mWifiSupplState = -1;
    final StopwatchTimer[] mWifiSupplStateTimer = new StopwatchTimer[NUM_WIFI_SUPPL_STATES];

    int mWifiSignalStrengthBin = -1;
    final StopwatchTimer[] mWifiSignalStrengthsTimer =
            new StopwatchTimer[NUM_WIFI_SIGNAL_STRENGTH_BINS];

    boolean mBluetoothOn;
    StopwatchTimer mBluetoothOnTimer;

    int mBluetoothState = -1;
    final StopwatchTimer[] mBluetoothStateTimer = new StopwatchTimer[NUM_BLUETOOTH_STATES];

    int mMobileRadioPowerState = DataConnectionRealTimeInfo.DC_POWER_STATE_LOW;
    long mMobileRadioActiveStartTime;
    StopwatchTimer mMobileRadioActiveTimer;
    StopwatchTimer mMobileRadioActivePerAppTimer;
    LongSamplingCounter mMobileRadioActiveAdjustedTime;
    LongSamplingCounter mMobileRadioActiveUnknownTime;
    LongSamplingCounter mMobileRadioActiveUnknownCount;

    /** Bluetooth headset object */
    BluetoothHeadset mBtHeadset;

    /**
     * These provide time bases that discount the time the device is plugged
     * in to power.
     */
    boolean mOnBattery;
    boolean mOnBatteryInternal;

    /*
     * These keep track of battery levels (1-100) at the last plug event and the last unplug event.
     */
    int mDischargeStartLevel;
    int mDischargeUnplugLevel;
    int mDischargePlugLevel;
    int mDischargeCurrentLevel;
    int mCurrentBatteryLevel;
    int mLowDischargeAmountSinceCharge;
    int mHighDischargeAmountSinceCharge;
    int mDischargeScreenOnUnplugLevel;
    int mDischargeScreenOffUnplugLevel;
    int mDischargeAmountScreenOn;
    int mDischargeAmountScreenOnSinceCharge;
    int mDischargeAmountScreenOff;
    int mDischargeAmountScreenOffSinceCharge;

    static final int MAX_LEVEL_STEPS = 200;

    int mInitStepMode = 0;
    int mCurStepMode = 0;
    int mModStepMode = 0;

    int mLastDischargeStepLevel;
    long mLastDischargeStepTime;
    int mMinDischargeStepLevel;
    int mNumDischargeStepDurations;
    final long[] mDischargeStepDurations = new long[MAX_LEVEL_STEPS];

    int mLastChargeStepLevel;
    long mLastChargeStepTime;
    int mMaxChargeStepLevel;
    int mNumChargeStepDurations;
    final long[] mChargeStepDurations = new long[MAX_LEVEL_STEPS];

    long mLastWriteTime = 0; // Milliseconds

    private int mBluetoothPingCount;
    private int mBluetoothPingStart = -1;

    private int mPhoneServiceState = -1;
    private int mPhoneServiceStateRaw = -1;
    private int mPhoneSimStateRaw = -1;

    private int mNumConnectivityChange;
    private int mLoadedNumConnectivityChange;
    private int mUnpluggedNumConnectivityChange;

    /*
     * Holds a SamplingTimer associated with each kernel wakelock name being tracked.
     */
    private final HashMap<String, SamplingTimer> mKernelWakelockStats =
            new HashMap<String, SamplingTimer>();

    public Map<String, ? extends Timer> getKernelWakelockStats() {
        return mKernelWakelockStats;
    }

    private static int sKernelWakelockUpdateVersion = 0;

    String mLastWakeupReason = null;
    long mLastWakeupUptimeMs = 0;
    private final HashMap<String, SamplingTimer> mWakeupReasonStats = new HashMap<>();

    public Map<String, ? extends Timer> getWakeupReasonStats() {
        return mWakeupReasonStats;
    }

    private static final int[] PROC_WAKELOCKS_FORMAT = new int[] {
        Process.PROC_TAB_TERM|Process.PROC_OUT_STRING|                // 0: name
                              Process.PROC_QUOTES,
        Process.PROC_TAB_TERM|Process.PROC_OUT_LONG,                  // 1: count
        Process.PROC_TAB_TERM,
        Process.PROC_TAB_TERM,
        Process.PROC_TAB_TERM,
        Process.PROC_TAB_TERM|Process.PROC_OUT_LONG,                  // 5: totalTime
    };

    private static final int[] WAKEUP_SOURCES_FORMAT = new int[] {
        Process.PROC_TAB_TERM|Process.PROC_OUT_STRING,                // 0: name
        Process.PROC_TAB_TERM|Process.PROC_COMBINE|
                              Process.PROC_OUT_LONG,                  // 1: count
        Process.PROC_TAB_TERM|Process.PROC_COMBINE,
        Process.PROC_TAB_TERM|Process.PROC_COMBINE,
        Process.PROC_TAB_TERM|Process.PROC_COMBINE,
        Process.PROC_TAB_TERM|Process.PROC_COMBINE,
        Process.PROC_TAB_TERM|Process.PROC_COMBINE
                             |Process.PROC_OUT_LONG,                  // 6: totalTime
    };

    private final String[] mProcWakelocksName = new String[3];
    private final long[] mProcWakelocksData = new long[3];

    /*
     * Used as a buffer for reading in data from /proc/wakelocks before it is processed and added
     * to mKernelWakelockStats.
     */
    private final Map<String, KernelWakelockStats> mProcWakelockFileStats =
            new HashMap<String, KernelWakelockStats>();

    private final NetworkStatsFactory mNetworkStatsFactory = new NetworkStatsFactory();
    private NetworkStats mCurMobileSnapshot = new NetworkStats(SystemClock.elapsedRealtime(), 50);
    private NetworkStats mLastMobileSnapshot = new NetworkStats(SystemClock.elapsedRealtime(), 50);
    private NetworkStats mCurWifiSnapshot = new NetworkStats(SystemClock.elapsedRealtime(), 50);
    private NetworkStats mLastWifiSnapshot = new NetworkStats(SystemClock.elapsedRealtime(), 50);
    private NetworkStats mTmpNetworkStats;
    private final NetworkStats.Entry mTmpNetworkStatsEntry = new NetworkStats.Entry();

    @GuardedBy("this")
    private String[] mMobileIfaces = new String[0];
    @GuardedBy("this")
    private String[] mWifiIfaces = new String[0];

    public BatteryStatsImpl() {
        mFile = null;
        mCheckinFile = null;
        mHandler = null;
        clearHistoryLocked();
    }

    public static interface TimeBaseObs {
        void onTimeStarted(long elapsedRealtime, long baseUptime, long baseRealtime);
        void onTimeStopped(long elapsedRealtime, long baseUptime, long baseRealtime);
    }

    static class TimeBase {
        private final ArrayList<TimeBaseObs> mObservers = new ArrayList<TimeBaseObs>();

        private long mUptime;
        private long mRealtime;

        private boolean mRunning;

        private long mPastUptime;
        private long mUptimeStart;
        private long mPastRealtime;
        private long mRealtimeStart;
        private long mUnpluggedUptime;
        private long mUnpluggedRealtime;

        public void dump(PrintWriter pw, String prefix) {
            StringBuilder sb = new StringBuilder(128);
            pw.print(prefix); pw.print("mRunning="); pw.println(mRunning);
            sb.setLength(0);
            sb.append(prefix);
                    sb.append("mUptime=");
                    formatTimeMs(sb, mUptime / 1000);
            pw.println(sb.toString());
            sb.setLength(0);
            sb.append(prefix);
                    sb.append("mRealtime=");
                    formatTimeMs(sb, mRealtime / 1000);
            pw.println(sb.toString());
            sb.setLength(0);
            sb.append(prefix);
                    sb.append("mPastUptime=");
                    formatTimeMs(sb, mPastUptime / 1000); sb.append("mUptimeStart=");
                    formatTimeMs(sb, mUptimeStart / 1000);
                    sb.append("mUnpluggedUptime="); formatTimeMs(sb, mUnpluggedUptime / 1000);
            pw.println(sb.toString());
            sb.setLength(0);
            sb.append(prefix);
                    sb.append("mPastRealtime=");
                    formatTimeMs(sb, mPastRealtime / 1000); sb.append("mRealtimeStart=");
                    formatTimeMs(sb, mRealtimeStart / 1000);
                    sb.append("mUnpluggedRealtime="); formatTimeMs(sb, mUnpluggedRealtime / 1000);
            pw.println(sb.toString());
        }

        public void add(TimeBaseObs observer) {
            mObservers.add(observer);
        }

        public void remove(TimeBaseObs observer) {
            if (!mObservers.remove(observer)) {
                Slog.wtf(TAG, "Removed unknown observer: " + observer);
            }
        }

        public void init(long uptime, long realtime) {
            mRealtime = 0;
            mUptime = 0;
            mPastUptime = 0;
            mPastRealtime = 0;
            mUptimeStart = uptime;
            mRealtimeStart = realtime;
            mUnpluggedUptime = getUptime(mUptimeStart);
            mUnpluggedRealtime = getRealtime(mRealtimeStart);
        }

        public void reset(long uptime, long realtime) {
            if (!mRunning) {
                mPastUptime = 0;
                mPastRealtime = 0;
            } else {
                mUptimeStart = uptime;
                mRealtimeStart = realtime;
                mUnpluggedUptime = getUptime(uptime);
                mUnpluggedRealtime = getRealtime(realtime);
            }
        }

        public long computeUptime(long curTime, int which) {
            switch (which) {
                case STATS_SINCE_CHARGED:
                    return mUptime + getUptime(curTime);
                case STATS_CURRENT:
                    return getUptime(curTime);
                case STATS_SINCE_UNPLUGGED:
                    return getUptime(curTime) - mUnpluggedUptime;
            }
            return 0;
        }

        public long computeRealtime(long curTime, int which) {
            switch (which) {
                case STATS_SINCE_CHARGED:
                    return mRealtime + getRealtime(curTime);
                case STATS_CURRENT:
                    return getRealtime(curTime);
                case STATS_SINCE_UNPLUGGED:
                    return getRealtime(curTime) - mUnpluggedRealtime;
            }
            return 0;
        }

        public long getUptime(long curTime) {
            long time = mPastUptime;
            if (mRunning) {
                time += curTime - mUptimeStart;
            }
            return time;
        }

        public long getRealtime(long curTime) {
            long time = mPastRealtime;
            if (mRunning) {
                time += curTime - mRealtimeStart;
            }
            return time;
        }

        public long getUptimeStart() {
            return mUptimeStart;
        }

        public long getRealtimeStart() {
            return mRealtimeStart;
        }

        public boolean isRunning() {
            return mRunning;
        }

        public boolean setRunning(boolean running, long uptime, long realtime) {
            if (mRunning != running) {
                mRunning = running;
                if (running) {
                    mUptimeStart = uptime;
                    mRealtimeStart = realtime;
                    long batteryUptime = mUnpluggedUptime = getUptime(uptime);
                    long batteryRealtime = mUnpluggedRealtime = getRealtime(realtime);

                    for (int i = mObservers.size() - 1; i >= 0; i--) {
                        mObservers.get(i).onTimeStarted(realtime, batteryUptime, batteryRealtime);
                    }
                } else {
                    mPastUptime += uptime - mUptimeStart;
                    mPastRealtime += realtime - mRealtimeStart;

                    long batteryUptime = getUptime(uptime);
                    long batteryRealtime = getRealtime(realtime);

                    for (int i = mObservers.size() - 1; i >= 0; i--) {
                        mObservers.get(i).onTimeStopped(realtime, batteryUptime, batteryRealtime);
                    }
                }
                return true;
            }
            return false;
        }

        public void readSummaryFromParcel(Parcel in) {
            mUptime = in.readLong();
            mRealtime = in.readLong();
        }

        public void writeSummaryToParcel(Parcel out, long uptime, long realtime) {
            out.writeLong(computeUptime(uptime, STATS_SINCE_CHARGED));
            out.writeLong(computeRealtime(realtime, STATS_SINCE_CHARGED));
        }

        public void readFromParcel(Parcel in) {
            mRunning = false;
            mUptime = in.readLong();
            mPastUptime = in.readLong();
            mUptimeStart = in.readLong();
            mRealtime = in.readLong();
            mPastRealtime = in.readLong();
            mRealtimeStart = in.readLong();
            mUnpluggedUptime = in.readLong();
            mUnpluggedRealtime = in.readLong();
        }

        public void writeToParcel(Parcel out, long uptime, long realtime) {
            final long runningUptime = getUptime(uptime);
            final long runningRealtime = getRealtime(realtime);
            out.writeLong(mUptime);
            out.writeLong(runningUptime);
            out.writeLong(mUptimeStart);
            out.writeLong(mRealtime);
            out.writeLong(runningRealtime);
            out.writeLong(mRealtimeStart);
            out.writeLong(mUnpluggedUptime);
            out.writeLong(mUnpluggedRealtime);
        }
    }

    /**
     * State for keeping track of counting information.
     */
    public static class Counter extends BatteryStats.Counter implements TimeBaseObs {
        final AtomicInteger mCount = new AtomicInteger();
        final TimeBase mTimeBase;
        int mLoadedCount;
        int mLastCount;
        int mUnpluggedCount;
        int mPluggedCount;

        Counter(TimeBase timeBase, Parcel in) {
            mTimeBase = timeBase;
            mPluggedCount = in.readInt();
            mCount.set(mPluggedCount);
            mLoadedCount = in.readInt();
            mLastCount = 0;
            mUnpluggedCount = in.readInt();
            timeBase.add(this);
        }

        Counter(TimeBase timeBase) {
            mTimeBase = timeBase;
            timeBase.add(this);
        }

        public void writeToParcel(Parcel out) {
            out.writeInt(mCount.get());
            out.writeInt(mLoadedCount);
            out.writeInt(mUnpluggedCount);
        }

        public void onTimeStarted(long elapsedRealtime, long baseUptime, long baseRealtime) {
            mUnpluggedCount = mPluggedCount;
            mCount.set(mPluggedCount);
        }

        public void onTimeStopped(long elapsedRealtime, long baseUptime, long baseRealtime) {
            mPluggedCount = mCount.get();
        }

        /**
         * Writes a possibly null Counter to a Parcel.
         *
         * @param out the Parcel to be written to.
         * @param counter a Counter, or null.
         */
        public static void writeCounterToParcel(Parcel out, Counter counter) {
            if (counter == null) {
                out.writeInt(0); // indicates null
                return;
            }
            out.writeInt(1); // indicates non-null

            counter.writeToParcel(out);
        }

        @Override
        public int getCountLocked(int which) {
            int val = mCount.get();
            if (which == STATS_SINCE_UNPLUGGED) {
                val -= mUnpluggedCount;
            } else if (which != STATS_SINCE_CHARGED) {
                val -= mLoadedCount;
            }

            return val;
        }

        public void logState(Printer pw, String prefix) {
            pw.println(prefix + "mCount=" + mCount.get()
                    + " mLoadedCount=" + mLoadedCount + " mLastCount=" + mLastCount
                    + " mUnpluggedCount=" + mUnpluggedCount
                    + " mPluggedCount=" + mPluggedCount);
        }

        void stepAtomic() {
            mCount.incrementAndGet();
        }

        /**
         * Clear state of this counter.
         */
        void reset(boolean detachIfReset) {
            mCount.set(0);
            mLoadedCount = mLastCount = mPluggedCount = mUnpluggedCount = 0;
            if (detachIfReset) {
                detach();
            }
        }

        void detach() {
            mTimeBase.remove(this);
        }

        void writeSummaryFromParcelLocked(Parcel out) {
            int count = mCount.get();
            out.writeInt(count);
        }

        void readSummaryFromParcelLocked(Parcel in) {
            mLoadedCount = in.readInt();
            mCount.set(mLoadedCount);
            mLastCount = 0;
            mUnpluggedCount = mPluggedCount = mLoadedCount;
        }
    }

    public static class SamplingCounter extends Counter {
        SamplingCounter(TimeBase timeBase, Parcel in) {
            super(timeBase, in);
        }

        SamplingCounter(TimeBase timeBase) {
            super(timeBase);
        }

        public void addCountAtomic(long count) {
            mCount.addAndGet((int)count);
        }
    }

    public static class LongSamplingCounter extends LongCounter implements TimeBaseObs {
        final TimeBase mTimeBase;
        long mCount;
        long mLoadedCount;
        long mLastCount;
        long mUnpluggedCount;
        long mPluggedCount;

        LongSamplingCounter(TimeBase timeBase, Parcel in) {
            mTimeBase = timeBase;
            mPluggedCount = in.readLong();
            mCount = mPluggedCount;
            mLoadedCount = in.readLong();
            mLastCount = 0;
            mUnpluggedCount = in.readLong();
            timeBase.add(this);
        }

        LongSamplingCounter(TimeBase timeBase) {
            mTimeBase = timeBase;
            timeBase.add(this);
        }

        public void writeToParcel(Parcel out) {
            out.writeLong(mCount);
            out.writeLong(mLoadedCount);
            out.writeLong(mUnpluggedCount);
        }

        @Override
        public void onTimeStarted(long elapsedRealtime, long baseUptime, long baseRealtime) {
            mUnpluggedCount = mPluggedCount;
            mCount = mPluggedCount;
        }

        @Override
        public void onTimeStopped(long elapsedRealtime, long baseUptime, long baseRealtime) {
            mPluggedCount = mCount;
        }

        public long getCountLocked(int which) {
            long val = mCount;
            if (which == STATS_SINCE_UNPLUGGED) {
                val -= mUnpluggedCount;
            } else if (which != STATS_SINCE_CHARGED) {
                val -= mLoadedCount;
            }

            return val;
        }

        @Override
        public void logState(Printer pw, String prefix) {
            pw.println(prefix + "mCount=" + mCount
                    + " mLoadedCount=" + mLoadedCount + " mLastCount=" + mLastCount
                    + " mUnpluggedCount=" + mUnpluggedCount
                    + " mPluggedCount=" + mPluggedCount);
        }

        void addCountLocked(long count) {
            mCount += count;
        }

        /**
         * Clear state of this counter.
         */
        void reset(boolean detachIfReset) {
            mCount = 0;
            mLoadedCount = mLastCount = mPluggedCount = mUnpluggedCount = 0;
            if (detachIfReset) {
                detach();
            }
        }

        void detach() {
            mTimeBase.remove(this);
        }

        void writeSummaryFromParcelLocked(Parcel out) {
            out.writeLong(mCount);
        }

        void readSummaryFromParcelLocked(Parcel in) {
            mLoadedCount = in.readLong();
            mCount = mLoadedCount;
            mLastCount = 0;
            mUnpluggedCount = mPluggedCount = mLoadedCount;
        }
    }

    /**
     * State for keeping track of timing information.
     */
    public static abstract class Timer extends BatteryStats.Timer implements TimeBaseObs {
        final int mType;
        final TimeBase mTimeBase;

        int mCount;
        int mLoadedCount;
        int mLastCount;
        int mUnpluggedCount;

        // Times are in microseconds for better accuracy when dividing by the
        // lock count, and are in "battery realtime" units.

        /**
         * The total time we have accumulated since the start of the original
         * boot, to the last time something interesting happened in the
         * current run.
         */
        long mTotalTime;

        /**
         * The total time we loaded for the previous runs.  Subtract this from
         * mTotalTime to find the time for the current run of the system.
         */
        long mLoadedTime;

        /**
         * The run time of the last run of the system, as loaded from the
         * saved data.
         */
        long mLastTime;

        /**
         * The value of mTotalTime when unplug() was last called.  Subtract
         * this from mTotalTime to find the time since the last unplug from
         * power.
         */
        long mUnpluggedTime;

        /**
         * Constructs from a parcel.
         * @param type
         * @param timeBase
         * @param in
         */
        Timer(int type, TimeBase timeBase, Parcel in) {
            mType = type;
            mTimeBase = timeBase;

            mCount = in.readInt();
            mLoadedCount = in.readInt();
            mLastCount = 0;
            mUnpluggedCount = in.readInt();
            mTotalTime = in.readLong();
            mLoadedTime = in.readLong();
            mLastTime = 0;
            mUnpluggedTime = in.readLong();
            timeBase.add(this);
            if (DEBUG) Log.i(TAG, "**** READ TIMER #" + mType + ": mTotalTime=" + mTotalTime);
        }

        Timer(int type, TimeBase timeBase) {
            mType = type;
            mTimeBase = timeBase;
            timeBase.add(this);
        }

        protected abstract long computeRunTimeLocked(long curBatteryRealtime);

        protected abstract int computeCurrentCountLocked();

        /**
         * Clear state of this timer.  Returns true if the timer is inactive
         * so can be completely dropped.
         */
        boolean reset(boolean detachIfReset) {
            mTotalTime = mLoadedTime = mLastTime = 0;
            mCount = mLoadedCount = mLastCount = 0;
            if (detachIfReset) {
                detach();
            }
            return true;
        }

        void detach() {
            mTimeBase.remove(this);
        }

        public void writeToParcel(Parcel out, long elapsedRealtimeUs) {
            if (DEBUG) Log.i(TAG, "**** WRITING TIMER #" + mType + ": mTotalTime="
                    + computeRunTimeLocked(mTimeBase.getRealtime(elapsedRealtimeUs)));
            out.writeInt(mCount);
            out.writeInt(mLoadedCount);
            out.writeInt(mUnpluggedCount);
            out.writeLong(computeRunTimeLocked(mTimeBase.getRealtime(elapsedRealtimeUs)));
            out.writeLong(mLoadedTime);
            out.writeLong(mUnpluggedTime);
        }

        public void onTimeStarted(long elapsedRealtime, long timeBaseUptime, long baseRealtime) {
            if (DEBUG && mType < 0) {
                Log.v(TAG, "unplug #" + mType + ": realtime=" + baseRealtime
                        + " old mUnpluggedTime=" + mUnpluggedTime
                        + " old mUnpluggedCount=" + mUnpluggedCount);
            }
            mUnpluggedTime = computeRunTimeLocked(baseRealtime);
            mUnpluggedCount = mCount;
            if (DEBUG && mType < 0) {
                Log.v(TAG, "unplug #" + mType
                        + ": new mUnpluggedTime=" + mUnpluggedTime
                        + " new mUnpluggedCount=" + mUnpluggedCount);
            }
        }

        public void onTimeStopped(long elapsedRealtime, long baseUptime, long baseRealtime) {
            if (DEBUG && mType < 0) {
                Log.v(TAG, "plug #" + mType + ": realtime=" + baseRealtime
                        + " old mTotalTime=" + mTotalTime);
            }
            mTotalTime = computeRunTimeLocked(baseRealtime);
            mCount = computeCurrentCountLocked();
            if (DEBUG && mType < 0) {
                Log.v(TAG, "plug #" + mType
                        + ": new mTotalTime=" + mTotalTime);
            }
        }

        /**
         * Writes a possibly null Timer to a Parcel.
         *
         * @param out the Parcel to be written to.
         * @param timer a Timer, or null.
         */
        public static void writeTimerToParcel(Parcel out, Timer timer, long elapsedRealtimeUs) {
            if (timer == null) {
                out.writeInt(0); // indicates null
                return;
            }
            out.writeInt(1); // indicates non-null

            timer.writeToParcel(out, elapsedRealtimeUs);
        }

        @Override
        public long getTotalTimeLocked(long elapsedRealtimeUs, int which) {
            long val = computeRunTimeLocked(mTimeBase.getRealtime(elapsedRealtimeUs));
            if (which == STATS_SINCE_UNPLUGGED) {
                val -= mUnpluggedTime;
            } else if (which != STATS_SINCE_CHARGED) {
                val -= mLoadedTime;
            }

            return val;
        }

        @Override
        public int getCountLocked(int which) {
            int val = computeCurrentCountLocked();
            if (which == STATS_SINCE_UNPLUGGED) {
                val -= mUnpluggedCount;
            } else if (which != STATS_SINCE_CHARGED) {
                val -= mLoadedCount;
            }

            return val;
        }

        public void logState(Printer pw, String prefix) {
            pw.println(prefix + "mCount=" + mCount
                    + " mLoadedCount=" + mLoadedCount + " mLastCount=" + mLastCount
                    + " mUnpluggedCount=" + mUnpluggedCount);
            pw.println(prefix + "mTotalTime=" + mTotalTime
                    + " mLoadedTime=" + mLoadedTime);
            pw.println(prefix + "mLastTime=" + mLastTime
                    + " mUnpluggedTime=" + mUnpluggedTime);
        }


        void writeSummaryFromParcelLocked(Parcel out, long elapsedRealtimeUs) {
            long runTime = computeRunTimeLocked(mTimeBase.getRealtime(elapsedRealtimeUs));
            out.writeLong(runTime);
            out.writeInt(mCount);
        }

        void readSummaryFromParcelLocked(Parcel in) {
            // Multiply by 1000 for backwards compatibility
            mTotalTime = mLoadedTime = in.readLong();
            mLastTime = 0;
            mUnpluggedTime = mTotalTime;
            mCount = mLoadedCount = in.readInt();
            mLastCount = 0;
            mUnpluggedCount = mCount;
        }
    }

    public static final class SamplingTimer extends Timer {

        /**
         * The most recent reported count from /proc/wakelocks.
         */
        int mCurrentReportedCount;

        /**
         * The reported count from /proc/wakelocks when unplug() was last
         * called.
         */
        int mUnpluggedReportedCount;

        /**
         * The most recent reported total_time from /proc/wakelocks.
         */
        long mCurrentReportedTotalTime;


        /**
         * The reported total_time from /proc/wakelocks when unplug() was last
         * called.
         */
        long mUnpluggedReportedTotalTime;

        /**
         * Whether we are currently in a discharge cycle.
         */
        boolean mTimeBaseRunning;

        /**
         * Whether we are currently recording reported values.
         */
        boolean mTrackingReportedValues;

        /*
         * A sequence counter, incremented once for each update of the stats.
         */
        int mUpdateVersion;

        SamplingTimer(TimeBase timeBase, Parcel in) {
            super(0, timeBase, in);
            mCurrentReportedCount = in.readInt();
            mUnpluggedReportedCount = in.readInt();
            mCurrentReportedTotalTime = in.readLong();
            mUnpluggedReportedTotalTime = in.readLong();
            mTrackingReportedValues = in.readInt() == 1;
            mTimeBaseRunning = timeBase.isRunning();
        }

        SamplingTimer(TimeBase timeBase, boolean trackReportedValues) {
            super(0, timeBase);
            mTrackingReportedValues = trackReportedValues;
            mTimeBaseRunning = timeBase.isRunning();
        }

        public void setStale() {
            mTrackingReportedValues = false;
            mUnpluggedReportedTotalTime = 0;
            mUnpluggedReportedCount = 0;
        }

        public void setUpdateVersion(int version) {
            mUpdateVersion = version;
        }

        public int getUpdateVersion() {
            return mUpdateVersion;
        }

        public void updateCurrentReportedCount(int count) {
            if (mTimeBaseRunning && mUnpluggedReportedCount == 0) {
                // Updating the reported value for the first time.
                mUnpluggedReportedCount = count;
                // If we are receiving an update update mTrackingReportedValues;
                mTrackingReportedValues = true;
            }
            mCurrentReportedCount = count;
        }

        public void addCurrentReportedCount(int delta) {
            updateCurrentReportedCount(mCurrentReportedCount + delta);
        }

        public void updateCurrentReportedTotalTime(long totalTime) {
            if (mTimeBaseRunning && mUnpluggedReportedTotalTime == 0) {
                // Updating the reported value for the first time.
                mUnpluggedReportedTotalTime = totalTime;
                // If we are receiving an update update mTrackingReportedValues;
                mTrackingReportedValues = true;
            }
            mCurrentReportedTotalTime = totalTime;
        }

        public void addCurrentReportedTotalTime(long delta) {
            updateCurrentReportedTotalTime(mCurrentReportedTotalTime + delta);
        }

        public void onTimeStarted(long elapsedRealtime, long baseUptime, long baseRealtime) {
            super.onTimeStarted(elapsedRealtime, baseUptime, baseRealtime);
            if (mTrackingReportedValues) {
                mUnpluggedReportedTotalTime = mCurrentReportedTotalTime;
                mUnpluggedReportedCount = mCurrentReportedCount;
            }
            mTimeBaseRunning = true;
        }

        public void onTimeStopped(long elapsedRealtime, long baseUptime, long baseRealtime) {
            super.onTimeStopped(elapsedRealtime, baseUptime, baseRealtime);
            mTimeBaseRunning = false;
        }

        public void logState(Printer pw, String prefix) {
            super.logState(pw, prefix);
            pw.println(prefix + "mCurrentReportedCount=" + mCurrentReportedCount
                    + " mUnpluggedReportedCount=" + mUnpluggedReportedCount
                    + " mCurrentReportedTotalTime=" + mCurrentReportedTotalTime
                    + " mUnpluggedReportedTotalTime=" + mUnpluggedReportedTotalTime);
        }

        protected long computeRunTimeLocked(long curBatteryRealtime) {
            return mTotalTime + (mTimeBaseRunning && mTrackingReportedValues
                    ? mCurrentReportedTotalTime - mUnpluggedReportedTotalTime : 0);
        }

        protected int computeCurrentCountLocked() {
            return mCount + (mTimeBaseRunning && mTrackingReportedValues
                    ? mCurrentReportedCount - mUnpluggedReportedCount : 0);
        }

        public void writeToParcel(Parcel out, long elapsedRealtimeUs) {
            super.writeToParcel(out, elapsedRealtimeUs);
            out.writeInt(mCurrentReportedCount);
            out.writeInt(mUnpluggedReportedCount);
            out.writeLong(mCurrentReportedTotalTime);
            out.writeLong(mUnpluggedReportedTotalTime);
            out.writeInt(mTrackingReportedValues ? 1 : 0);
        }

        boolean reset(boolean detachIfReset) {
            super.reset(detachIfReset);
            setStale();
            return true;
        }

        void writeSummaryFromParcelLocked(Parcel out, long batteryRealtime) {
            super.writeSummaryFromParcelLocked(out, batteryRealtime);
            out.writeLong(mCurrentReportedTotalTime);
            out.writeInt(mCurrentReportedCount);
            out.writeInt(mTrackingReportedValues ? 1 : 0);
        }

        void readSummaryFromParcelLocked(Parcel in) {
            super.readSummaryFromParcelLocked(in);
            mUnpluggedReportedTotalTime = mCurrentReportedTotalTime = in.readLong();
            mUnpluggedReportedCount = mCurrentReportedCount = in.readInt();
            mTrackingReportedValues = in.readInt() == 1;
        }
    }

    /**
     * A timer that increments in batches.  It does not run for durations, but just jumps
     * for a pre-determined amount.
     */
    public static final class BatchTimer extends Timer {
        final Uid mUid;

        /**
         * The last time at which we updated the timer.  This is in elapsed realtime microseconds.
         */
        long mLastAddedTime;

        /**
         * The last duration that we added to the timer.  This is in microseconds.
         */
        long mLastAddedDuration;

        /**
         * Whether we are currently in a discharge cycle.
         */
        boolean mInDischarge;

        BatchTimer(Uid uid, int type, TimeBase timeBase, Parcel in) {
            super(type, timeBase, in);
            mUid = uid;
            mLastAddedTime = in.readLong();
            mLastAddedDuration = in.readLong();
            mInDischarge = timeBase.isRunning();
        }

        BatchTimer(Uid uid, int type, TimeBase timeBase) {
            super(type, timeBase);
            mUid = uid;
            mInDischarge = timeBase.isRunning();
        }

        @Override
        public void writeToParcel(Parcel out, long elapsedRealtimeUs) {
            super.writeToParcel(out, elapsedRealtimeUs);
            out.writeLong(mLastAddedTime);
            out.writeLong(mLastAddedDuration);
        }

        @Override
        public void onTimeStopped(long elapsedRealtime, long baseUptime, long baseRealtime) {
            recomputeLastDuration(SystemClock.elapsedRealtime() * 1000, false);
            mInDischarge = false;
            super.onTimeStopped(elapsedRealtime, baseUptime, baseRealtime);
        }

        @Override
        public void onTimeStarted(long elapsedRealtime, long baseUptime, long baseRealtime) {
            recomputeLastDuration(elapsedRealtime, false);
            mInDischarge = true;
            // If we are still within the last added duration, then re-added whatever remains.
            if (mLastAddedTime == elapsedRealtime) {
                mTotalTime += mLastAddedDuration;
            }
            super.onTimeStarted(elapsedRealtime, baseUptime, baseRealtime);
        }

        @Override
        public void logState(Printer pw, String prefix) {
            super.logState(pw, prefix);
            pw.println(prefix + "mLastAddedTime=" + mLastAddedTime
                    + " mLastAddedDuration=" + mLastAddedDuration);
        }

        private long computeOverage(long curTime) {
            if (mLastAddedTime > 0) {
                return mLastTime + mLastAddedDuration - curTime;
            }
            return 0;
        }

        private void recomputeLastDuration(long curTime, boolean abort) {
            final long overage = computeOverage(curTime);
            if (overage > 0) {
                // Aborting before the duration ran out -- roll back the remaining
                // duration.  Only do this if currently discharging; otherwise we didn't
                // actually add the time.
                if (mInDischarge) {
                    mTotalTime -= overage;
                }
                if (abort) {
                    mLastAddedTime = 0;
                } else {
                    mLastAddedTime = curTime;
                    mLastAddedDuration -= overage;
                }
            }
        }

        public void addDuration(BatteryStatsImpl stats, long durationMillis) {
            final long now = SystemClock.elapsedRealtime() * 1000;
            recomputeLastDuration(now, true);
            mLastAddedTime = now;
            mLastAddedDuration = durationMillis * 1000;
            if (mInDischarge) {
                mTotalTime += mLastAddedDuration;
                mCount++;
            }
        }

        public void abortLastDuration(BatteryStatsImpl stats) {
            final long now = SystemClock.elapsedRealtime() * 1000;
            recomputeLastDuration(now, true);
        }

        @Override
        protected int computeCurrentCountLocked() {
            return mCount;
        }

        @Override
        protected long computeRunTimeLocked(long curBatteryRealtime) {
            final long overage = computeOverage(SystemClock.elapsedRealtime() * 1000);
            if (overage > 0) {
                return mTotalTime = overage;
            }
            return mTotalTime;
        }

        @Override
        boolean reset(boolean detachIfReset) {
            final long now = SystemClock.elapsedRealtime() * 1000;
            recomputeLastDuration(now, true);
            boolean stillActive = mLastAddedTime == now;
            super.reset(!stillActive && detachIfReset);
            return !stillActive;
        }
    }

    /**
     * State for keeping track of timing information.
     */
    public static final class StopwatchTimer extends Timer {
        final Uid mUid;
        final ArrayList<StopwatchTimer> mTimerPool;

        int mNesting;

        /**
         * The last time at which we updated the timer.  If mNesting is > 0,
         * subtract this from the current battery time to find the amount of
         * time we have been running since we last computed an update.
         */
        long mUpdateTime;

        /**
         * The total time at which the timer was acquired, to determine if it
         * was actually held for an interesting duration.
         */
        long mAcquireTime;

        long mTimeout;

        /**
         * For partial wake locks, keep track of whether we are in the list
         * to consume CPU cycles.
         */
        boolean mInList;

        StopwatchTimer(Uid uid, int type, ArrayList<StopwatchTimer> timerPool,
                TimeBase timeBase, Parcel in) {
            super(type, timeBase, in);
            mUid = uid;
            mTimerPool = timerPool;
            mUpdateTime = in.readLong();
        }

        StopwatchTimer(Uid uid, int type, ArrayList<StopwatchTimer> timerPool,
                TimeBase timeBase) {
            super(type, timeBase);
            mUid = uid;
            mTimerPool = timerPool;
        }

        void setTimeout(long timeout) {
            mTimeout = timeout;
        }

        public void writeToParcel(Parcel out, long elapsedRealtimeUs) {
            super.writeToParcel(out, elapsedRealtimeUs);
            out.writeLong(mUpdateTime);
        }

        public void onTimeStopped(long elapsedRealtime, long baseUptime, long baseRealtime) {
            if (mNesting > 0) {
                if (DEBUG && mType < 0) {
                    Log.v(TAG, "old mUpdateTime=" + mUpdateTime);
                }
                super.onTimeStopped(elapsedRealtime, baseUptime, baseRealtime);
                mUpdateTime = baseRealtime;
                if (DEBUG && mType < 0) {
                    Log.v(TAG, "new mUpdateTime=" + mUpdateTime);
                }
            }
        }

        public void logState(Printer pw, String prefix) {
            super.logState(pw, prefix);
            pw.println(prefix + "mNesting=" + mNesting + " mUpdateTime=" + mUpdateTime
                    + " mAcquireTime=" + mAcquireTime);
        }

        void startRunningLocked(long elapsedRealtimeMs) {
            if (mNesting++ == 0) {
                final long batteryRealtime = mTimeBase.getRealtime(elapsedRealtimeMs * 1000);
                mUpdateTime = batteryRealtime;
                if (mTimerPool != null) {
                    // Accumulate time to all currently active timers before adding
                    // this new one to the pool.
                    refreshTimersLocked(batteryRealtime, mTimerPool, null);
                    // Add this timer to the active pool
                    mTimerPool.add(this);
                }
                // Increment the count
                mCount++;
                mAcquireTime = mTotalTime;
                if (DEBUG && mType < 0) {
                    Log.v(TAG, "start #" + mType + ": mUpdateTime=" + mUpdateTime
                            + " mTotalTime=" + mTotalTime + " mCount=" + mCount
                            + " mAcquireTime=" + mAcquireTime);
                }
            }
        }

        boolean isRunningLocked() {
            return mNesting > 0;
        }

        long checkpointRunningLocked(long elapsedRealtimeMs) {
            if (mNesting > 0) {
                // We are running...
                final long batteryRealtime = mTimeBase.getRealtime(elapsedRealtimeMs * 1000);
                if (mTimerPool != null) {
                    return refreshTimersLocked(batteryRealtime, mTimerPool, this);
                }
                final long heldTime = batteryRealtime - mUpdateTime;
                mUpdateTime = batteryRealtime;
                mTotalTime += heldTime;
                return heldTime;
            }
            return 0;
        }

        void stopRunningLocked(long elapsedRealtimeMs) {
            // Ignore attempt to stop a timer that isn't running
            if (mNesting == 0) {
                return;
            }
            if (--mNesting == 0) {
                final long batteryRealtime = mTimeBase.getRealtime(elapsedRealtimeMs * 1000);
                if (mTimerPool != null) {
                    // Accumulate time to all active counters, scaled by the total
                    // active in the pool, before taking this one out of the pool.
                    refreshTimersLocked(batteryRealtime, mTimerPool, null);
                    // Remove this timer from the active pool
                    mTimerPool.remove(this);
                } else {
                    mNesting = 1;
                    mTotalTime = computeRunTimeLocked(batteryRealtime);
                    mNesting = 0;
                }

                if (DEBUG && mType < 0) {
                    Log.v(TAG, "stop #" + mType + ": mUpdateTime=" + mUpdateTime
                            + " mTotalTime=" + mTotalTime + " mCount=" + mCount
                            + " mAcquireTime=" + mAcquireTime);
                }

                if (mTotalTime == mAcquireTime) {
                    // If there was no change in the time, then discard this
                    // count.  A somewhat cheezy strategy, but hey.
                    mCount--;
                }
            }
        }

        void stopAllRunningLocked(long elapsedRealtimeMs) {
            if (mNesting > 0) {
                mNesting = 1;
                stopRunningLocked(elapsedRealtimeMs);
            }
        }

        // Update the total time for all other running Timers with the same type as this Timer
        // due to a change in timer count
        private static long refreshTimersLocked(long batteryRealtime,
                final ArrayList<StopwatchTimer> pool, StopwatchTimer self) {
            long selfTime = 0;
            final int N = pool.size();
            for (int i=N-1; i>= 0; i--) {
                final StopwatchTimer t = pool.get(i);
                long heldTime = batteryRealtime - t.mUpdateTime;
                if (heldTime > 0) {
                    final long myTime = heldTime / N;
                    if (t == self) {
                        selfTime = myTime;
                    }
                    t.mTotalTime += myTime;
                }
                t.mUpdateTime = batteryRealtime;
            }
            return selfTime;
        }

        @Override
        protected long computeRunTimeLocked(long curBatteryRealtime) {
            if (mTimeout > 0 && curBatteryRealtime > mUpdateTime + mTimeout) {
                curBatteryRealtime = mUpdateTime + mTimeout;
            }
            return mTotalTime + (mNesting > 0
                    ? (curBatteryRealtime - mUpdateTime)
                            / (mTimerPool != null ? mTimerPool.size() : 1)
                    : 0);
        }

        @Override
        protected int computeCurrentCountLocked() {
            return mCount;
        }

        boolean reset(boolean detachIfReset) {
            boolean canDetach = mNesting <= 0;
            super.reset(canDetach && detachIfReset);
            if (mNesting > 0) {
                mUpdateTime = mTimeBase.getRealtime(SystemClock.elapsedRealtime() * 1000);
            }
            mAcquireTime = mTotalTime;
            return canDetach;
        }

        void detach() {
            super.detach();
            if (mTimerPool != null) {
                mTimerPool.remove(this);
            }
        }

        void readSummaryFromParcelLocked(Parcel in) {
            super.readSummaryFromParcelLocked(in);
            mNesting = 0;
        }
    }

    public abstract class OverflowArrayMap<T> {
        private static final String OVERFLOW_NAME = "*overflow*";

        final ArrayMap<String, T> mMap = new ArrayMap<>();
        T mCurOverflow;
        ArrayMap<String, MutableInt> mActiveOverflow;

        public OverflowArrayMap() {
        }

        public ArrayMap<String, T> getMap() {
            return mMap;
        }

        public void clear() {
            mMap.clear();
            mCurOverflow = null;
            mActiveOverflow = null;
        }

        public void add(String name, T obj) {
            mMap.put(name, obj);
            if (OVERFLOW_NAME.equals(name)) {
                mCurOverflow = obj;
            }
        }

        public void cleanup() {
            if (mActiveOverflow != null) {
                if (mActiveOverflow.size() == 0) {
                    mActiveOverflow = null;
                }
            }
            if (mActiveOverflow == null) {
                // There is no currently active overflow, so we should no longer have
                // an overflow entry.
                if (mMap.containsKey(OVERFLOW_NAME)) {
                    Slog.wtf(TAG, "Cleaning up with no active overflow, but have overflow entry "
                            + mMap.get(OVERFLOW_NAME));
                    mMap.remove(OVERFLOW_NAME);
                }
                mCurOverflow = null;
            } else {
                // There is currently active overflow, so we should still have an overflow entry.
                if (mCurOverflow == null || !mMap.containsKey(OVERFLOW_NAME)) {
                    Slog.wtf(TAG, "Cleaning up with active overflow, but no overflow entry: cur="
                            + mCurOverflow + " map=" + mMap.get(OVERFLOW_NAME));
                }
            }
        }

        public T startObject(String name) {
            T obj = mMap.get(name);
            if (obj != null) {
                return obj;
            }

            // No object exists for the given name, but do we currently have it
            // running as part of the overflow?
            if (mActiveOverflow != null) {
                MutableInt over = mActiveOverflow.get(name);
                if (over != null) {
                    // We are already actively counting this name in the overflow object.
                    obj = mCurOverflow;
                    if (obj == null) {
                        // Shouldn't be here, but we'll try to recover.
                        Slog.wtf(TAG, "Have active overflow " + name + " but null overflow");
                        obj = mCurOverflow = instantiateObject();
                        mMap.put(OVERFLOW_NAME, obj);
                    }
                    over.value++;
                    return obj;
                }
            }

            // No object exists for given name nor in the overflow; we need to make
            // a new one.
            final int N = mMap.size();
            if (N >= MAX_WAKELOCKS_PER_UID) {
                // Went over the limit on number of objects to track; this one goes
                // in to the overflow.
                obj = mCurOverflow;
                if (obj == null) {
                    // Need to start overflow now...
                    obj = mCurOverflow = instantiateObject();
                    mMap.put(OVERFLOW_NAME, obj);
                }
                if (mActiveOverflow == null) {
                    mActiveOverflow = new ArrayMap<>();
                }
                mActiveOverflow.put(name, new MutableInt(1));
                return obj;
            }

            // Normal case where we just need to make a new object.
            obj = instantiateObject();
            mMap.put(name, obj);
            return obj;
        }

        public T stopObject(String name) {
            T obj = mMap.get(name);
            if (obj != null) {
                return obj;
            }

            // No object exists for the given name, but do we currently have it
            // running as part of the overflow?
            if (mActiveOverflow != null) {
                MutableInt over = mActiveOverflow.get(name);
                if (over != null) {
                    // We are already actively counting this name in the overflow object.
                    obj = mCurOverflow;
                    if (obj != null) {
                        over.value--;
                        if (over.value <= 0) {
                            mActiveOverflow.remove(name);
                        }
                        return obj;
                    }
                }
            }

            // Huh, they are stopping an active operation but we can't find one!
            // That's not good.
            Slog.wtf(TAG, "Unable to find object for " + name + " mapsize="
                    + mMap.size() + " activeoverflow=" + mActiveOverflow
                    + " curoverflow=" + mCurOverflow);
            return null;
        }

        public abstract T instantiateObject();
    }

    /*
     * Get the wakeup reason counter, and create a new one if one
     * doesn't already exist.
     */
    public SamplingTimer getWakeupReasonTimerLocked(String name) {
        SamplingTimer timer = mWakeupReasonStats.get(name);
        if (timer == null) {
            timer = new SamplingTimer(mOnBatteryTimeBase, true);
            mWakeupReasonStats.put(name, timer);
        }
        return timer;
    }

    private final Map<String, KernelWakelockStats> readKernelWakelockStats() {

        FileInputStream is;
        byte[] buffer = new byte[8192];
        int len;
        boolean wakeup_sources = false;

        try {
            try {
                is = new FileInputStream("/proc/wakelocks");
            } catch (java.io.FileNotFoundException e) {
                try {
                    is = new FileInputStream("/d/wakeup_sources");
                    wakeup_sources = true;
                } catch (java.io.FileNotFoundException e2) {
                    return null;
                }
            }

            len = is.read(buffer);
            is.close();
        } catch (java.io.IOException e) {
            return null;
        }

        if (len > 0) {
            int i;
            for (i=0; i<len; i++) {
                if (buffer[i] == '\0') {
                    len = i;
                    break;
                }
            }
        }

        return parseProcWakelocks(buffer, len, wakeup_sources);
    }

    private final Map<String, KernelWakelockStats> parseProcWakelocks(
            byte[] wlBuffer, int len, boolean wakeup_sources) {
        String name;
        int count;
        long totalTime;
        int startIndex;
        int endIndex;
        int numUpdatedWlNames = 0;

        // Advance past the first line.
        int i;
        for (i = 0; i < len && wlBuffer[i] != '\n' && wlBuffer[i] != '\0'; i++);
        startIndex = endIndex = i + 1;

        synchronized(this) {
            Map<String, KernelWakelockStats> m = mProcWakelockFileStats;

            sKernelWakelockUpdateVersion++;
            while (endIndex < len) {
                for (endIndex=startIndex;
                        endIndex < len && wlBuffer[endIndex] != '\n' && wlBuffer[endIndex] != '\0';
                        endIndex++);
                endIndex++; // endIndex is an exclusive upper bound.
                // Don't go over the end of the buffer, Process.parseProcLine might
                // write to wlBuffer[endIndex]
                if (endIndex >= (len - 1) ) {
                    return m;
                }

                String[] nameStringArray = mProcWakelocksName;
                long[] wlData = mProcWakelocksData;
                // Stomp out any bad characters since this is from a circular buffer
                // A corruption is seen sometimes that results in the vm crashing
                // This should prevent crashes and the line will probably fail to parse
                for (int j = startIndex; j < endIndex; j++) {
                    if ((wlBuffer[j] & 0x80) != 0) wlBuffer[j] = (byte) '?';
                }
                boolean parsed = Process.parseProcLine(wlBuffer, startIndex, endIndex,
                        wakeup_sources ? WAKEUP_SOURCES_FORMAT :
                                         PROC_WAKELOCKS_FORMAT,
                        nameStringArray, wlData, null);

                name = nameStringArray[0];
                count = (int) wlData[1];

                if (wakeup_sources) {
                        // convert milliseconds to microseconds
                        totalTime = wlData[2] * 1000;
                } else {
                        // convert nanoseconds to microseconds with rounding.
                        totalTime = (wlData[2] + 500) / 1000;
                }

                if (parsed && name.length() > 0) {
                    if (!m.containsKey(name)) {
                        m.put(name, new KernelWakelockStats(count, totalTime,
                                sKernelWakelockUpdateVersion));
                        numUpdatedWlNames++;
                    } else {
                        KernelWakelockStats kwlStats = m.get(name);
                        if (kwlStats.mVersion == sKernelWakelockUpdateVersion) {
                            kwlStats.mCount += count;
                            kwlStats.mTotalTime += totalTime;
                        } else {
                            kwlStats.mCount = count;
                            kwlStats.mTotalTime = totalTime;
                            kwlStats.mVersion = sKernelWakelockUpdateVersion;
                            numUpdatedWlNames++;
                        }
                    }
                }
                startIndex = endIndex;
            }

            if (m.size() != numUpdatedWlNames) {
                // Don't report old data.
                Iterator<KernelWakelockStats> itr = m.values().iterator();
                while (itr.hasNext()) {
                    if (itr.next().mVersion != sKernelWakelockUpdateVersion) {
                        itr.remove();
                    }
                }
            }
            return m;
        }
    }

    private class KernelWakelockStats {
        public int mCount;
        public long mTotalTime;
        public int mVersion;

        KernelWakelockStats(int count, long totalTime, int version) {
            mCount = count;
            mTotalTime = totalTime;
            mVersion = version;
        }
    }

    /*
     * Get the KernelWakelockTimer associated with name, and create a new one if one
     * doesn't already exist.
     */
    public SamplingTimer getKernelWakelockTimerLocked(String name) {
        SamplingTimer kwlt = mKernelWakelockStats.get(name);
        if (kwlt == null) {
            kwlt = new SamplingTimer(mOnBatteryScreenOffTimeBase, true /* track reported values */);
            mKernelWakelockStats.put(name, kwlt);
        }
        return kwlt;
    }

    private int getCurrentBluetoothPingCount() {
        if (mBtHeadset != null) {
            List<BluetoothDevice> deviceList = mBtHeadset.getConnectedDevices();
            if (deviceList.size() > 0) {
                return mBtHeadset.getBatteryUsageHint(deviceList.get(0));
            }
        }
        return -1;
    }

    public int getBluetoothPingCount() {
        if (mBluetoothPingStart == -1) {
            return mBluetoothPingCount;
        } else if (mBtHeadset != null) {
            return getCurrentBluetoothPingCount() - mBluetoothPingStart;
        }
        return 0;
    }

    public void setBtHeadset(BluetoothHeadset headset) {
        if (headset != null && mBtHeadset == null && isOnBattery() && mBluetoothPingStart == -1) {
            mBluetoothPingStart = getCurrentBluetoothPingCount();
        }
        mBtHeadset = headset;
    }

    private int writeHistoryTag(HistoryTag tag) {
        Integer idxObj = mHistoryTagPool.get(tag);
        int idx;
        if (idxObj != null) {
            idx = idxObj;
        } else {
            idx = mNextHistoryTagIdx;
            HistoryTag key = new HistoryTag();
            key.setTo(tag);
            tag.poolIdx = idx;
            mHistoryTagPool.put(key, idx);
            mNextHistoryTagIdx++;
            mNumHistoryTagChars += key.string.length() + 1;
        }
        return idx;
    }

    private void readHistoryTag(int index, HistoryTag tag) {
        tag.string = mReadHistoryStrings[index];
        tag.uid = mReadHistoryUids[index];
        tag.poolIdx = index;
    }

    // Part of initial delta int that specifies the time delta.
    static final int DELTA_TIME_MASK = 0x7ffff;
    static final int DELTA_TIME_LONG = 0x7ffff;   // The delta is a following long
    static final int DELTA_TIME_INT = 0x7fffe;    // The delta is a following int
    static final int DELTA_TIME_ABS = 0x7fffd;    // Following is an entire abs update.
    // Flag in delta int: a new battery level int follows.
    static final int DELTA_BATTERY_LEVEL_FLAG   = 0x00080000;
    // Flag in delta int: a new full state and battery status int follows.
    static final int DELTA_STATE_FLAG           = 0x00100000;
    // Flag in delta int: a new full state2 int follows.
    static final int DELTA_STATE2_FLAG          = 0x00200000;
    // Flag in delta int: contains a wakelock or wakeReason tag.
    static final int DELTA_WAKELOCK_FLAG        = 0x00400000;
    // Flag in delta int: contains an event description.
    static final int DELTA_EVENT_FLAG           = 0x00800000;
    // These upper bits are the frequently changing state bits.
    static final int DELTA_STATE_MASK           = 0xff000000;

    // These are the pieces of battery state that are packed in to the upper bits of
    // the state int that have been packed in to the first delta int.  They must fit
    // in DELTA_STATE_MASK.
    static final int STATE_BATTERY_STATUS_MASK  = 0x00000007;
    static final int STATE_BATTERY_STATUS_SHIFT = 29;
    static final int STATE_BATTERY_HEALTH_MASK  = 0x00000007;
    static final int STATE_BATTERY_HEALTH_SHIFT = 26;
    static final int STATE_BATTERY_PLUG_MASK    = 0x00000003;
    static final int STATE_BATTERY_PLUG_SHIFT   = 24;

    public void writeHistoryDelta(Parcel dest, HistoryItem cur, HistoryItem last) {
        if (last == null || cur.cmd != HistoryItem.CMD_UPDATE) {
            dest.writeInt(DELTA_TIME_ABS);
            cur.writeToParcel(dest, 0);
            return;
        }

        final long deltaTime = cur.time - last.time;
        final int lastBatteryLevelInt = buildBatteryLevelInt(last);
        final int lastStateInt = buildStateInt(last);

        int deltaTimeToken;
        if (deltaTime < 0 || deltaTime > Integer.MAX_VALUE) {
            deltaTimeToken = DELTA_TIME_LONG;
        } else if (deltaTime >= DELTA_TIME_ABS) {
            deltaTimeToken = DELTA_TIME_INT;
        } else {
            deltaTimeToken = (int)deltaTime;
        }
        int firstToken = deltaTimeToken | (cur.states&DELTA_STATE_MASK);
        final int batteryLevelInt = buildBatteryLevelInt(cur);
        final boolean batteryLevelIntChanged = batteryLevelInt != lastBatteryLevelInt;
        if (batteryLevelIntChanged) {
            firstToken |= DELTA_BATTERY_LEVEL_FLAG;
        }
        final int stateInt = buildStateInt(cur);
        final boolean stateIntChanged = stateInt != lastStateInt;
        if (stateIntChanged) {
            firstToken |= DELTA_STATE_FLAG;
        }
        final boolean state2IntChanged = cur.states2 != last.states2;
        if (state2IntChanged) {
            firstToken |= DELTA_STATE2_FLAG;
        }
        if (cur.wakelockTag != null || cur.wakeReasonTag != null) {
            firstToken |= DELTA_WAKELOCK_FLAG;
        }
        if (cur.eventCode != HistoryItem.EVENT_NONE) {
            firstToken |= DELTA_EVENT_FLAG;
        }
        dest.writeInt(firstToken);
        if (DEBUG) Slog.i(TAG, "WRITE DELTA: firstToken=0x" + Integer.toHexString(firstToken)
                + " deltaTime=" + deltaTime);

        if (deltaTimeToken >= DELTA_TIME_INT) {
            if (deltaTimeToken == DELTA_TIME_INT) {
                if (DEBUG) Slog.i(TAG, "WRITE DELTA: int deltaTime=" + (int)deltaTime);
                dest.writeInt((int)deltaTime);
            } else {
                if (DEBUG) Slog.i(TAG, "WRITE DELTA: long deltaTime=" + deltaTime);
                dest.writeLong(deltaTime);
            }
        }
        if (batteryLevelIntChanged) {
            dest.writeInt(batteryLevelInt);
            if (DEBUG) Slog.i(TAG, "WRITE DELTA: batteryToken=0x"
                    + Integer.toHexString(batteryLevelInt)
                    + " batteryLevel=" + cur.batteryLevel
                    + " batteryTemp=" + cur.batteryTemperature
                    + " batteryVolt=" + (int)cur.batteryVoltage);
        }
        if (stateIntChanged) {
            dest.writeInt(stateInt);
            if (DEBUG) Slog.i(TAG, "WRITE DELTA: stateToken=0x"
                    + Integer.toHexString(stateInt)
                    + " batteryStatus=" + cur.batteryStatus
                    + " batteryHealth=" + cur.batteryHealth
                    + " batteryPlugType=" + cur.batteryPlugType
                    + " states=0x" + Integer.toHexString(cur.states));
        }
        if (state2IntChanged) {
            dest.writeInt(cur.states2);
            if (DEBUG) Slog.i(TAG, "WRITE DELTA: states2=0x"
                    + Integer.toHexString(cur.states2));
        }
        if (cur.wakelockTag != null || cur.wakeReasonTag != null) {
            int wakeLockIndex;
            int wakeReasonIndex;
            if (cur.wakelockTag != null) {
                wakeLockIndex = writeHistoryTag(cur.wakelockTag);
                if (DEBUG) Slog.i(TAG, "WRITE DELTA: wakelockTag=#" + cur.wakelockTag.poolIdx
                    + " " + cur.wakelockTag.uid + ":" + cur.wakelockTag.string);
            } else {
                wakeLockIndex = 0xffff;
            }
            if (cur.wakeReasonTag != null) {
                wakeReasonIndex = writeHistoryTag(cur.wakeReasonTag);
                if (DEBUG) Slog.i(TAG, "WRITE DELTA: wakeReasonTag=#" + cur.wakeReasonTag.poolIdx
                    + " " + cur.wakeReasonTag.uid + ":" + cur.wakeReasonTag.string);
            } else {
                wakeReasonIndex = 0xffff;
            }
            dest.writeInt((wakeReasonIndex<<16) | wakeLockIndex);
        }
        if (cur.eventCode != HistoryItem.EVENT_NONE) {
            int index = writeHistoryTag(cur.eventTag);
            int codeAndIndex = (cur.eventCode&0xffff) | (index<<16);
            dest.writeInt(codeAndIndex);
            if (DEBUG) Slog.i(TAG, "WRITE DELTA: event=" + cur.eventCode + " tag=#"
                    + cur.eventTag.poolIdx + " " + cur.eventTag.uid + ":"
                    + cur.eventTag.string);
        }
    }

    private int buildBatteryLevelInt(HistoryItem h) {
        return ((((int)h.batteryLevel)<<25)&0xfe000000)
                | ((((int)h.batteryTemperature)<<14)&0x01ffc000)
                | (((int)h.batteryVoltage)&0x00003fff);
    }

    private int buildStateInt(HistoryItem h) {
        int plugType = 0;
        if ((h.batteryPlugType&BatteryManager.BATTERY_PLUGGED_AC) != 0) {
            plugType = 1;
        } else if ((h.batteryPlugType&BatteryManager.BATTERY_PLUGGED_USB) != 0) {
            plugType = 2;
        } else if ((h.batteryPlugType&BatteryManager.BATTERY_PLUGGED_WIRELESS) != 0) {
            plugType = 3;
        }
        return ((h.batteryStatus&STATE_BATTERY_STATUS_MASK)<<STATE_BATTERY_STATUS_SHIFT)
                | ((h.batteryHealth&STATE_BATTERY_HEALTH_MASK)<<STATE_BATTERY_HEALTH_SHIFT)
                | ((plugType&STATE_BATTERY_PLUG_MASK)<<STATE_BATTERY_PLUG_SHIFT)
                | (h.states&(~DELTA_STATE_MASK));
    }

    public void readHistoryDelta(Parcel src, HistoryItem cur) {
        int firstToken = src.readInt();
        int deltaTimeToken = firstToken&DELTA_TIME_MASK;
        cur.cmd = HistoryItem.CMD_UPDATE;
        cur.numReadInts = 1;
        if (DEBUG) Slog.i(TAG, "READ DELTA: firstToken=0x" + Integer.toHexString(firstToken)
                + " deltaTimeToken=" + deltaTimeToken);

        if (deltaTimeToken < DELTA_TIME_ABS) {
            cur.time += deltaTimeToken;
        } else if (deltaTimeToken == DELTA_TIME_ABS) {
            cur.time = src.readLong();
            cur.numReadInts += 2;
            if (DEBUG) Slog.i(TAG, "READ DELTA: ABS time=" + cur.time);
            cur.readFromParcel(src);
            return;
        } else if (deltaTimeToken == DELTA_TIME_INT) {
            int delta = src.readInt();
            cur.time += delta;
            cur.numReadInts += 1;
            if (DEBUG) Slog.i(TAG, "READ DELTA: time delta=" + delta + " new time=" + cur.time);
        } else {
            long delta = src.readLong();
            if (DEBUG) Slog.i(TAG, "READ DELTA: time delta=" + delta + " new time=" + cur.time);
            cur.time += delta;
            cur.numReadInts += 2;
        }

        if ((firstToken&DELTA_BATTERY_LEVEL_FLAG) != 0) {
            int batteryLevelInt = src.readInt();
            cur.batteryLevel = (byte)((batteryLevelInt>>25)&0x7f);
            cur.batteryTemperature = (short)((batteryLevelInt<<7)>>21);
            cur.batteryVoltage = (char)(batteryLevelInt&0x3fff);
            cur.numReadInts += 1;
            if (DEBUG) Slog.i(TAG, "READ DELTA: batteryToken=0x"
                    + Integer.toHexString(batteryLevelInt)
                    + " batteryLevel=" + cur.batteryLevel
                    + " batteryTemp=" + cur.batteryTemperature
                    + " batteryVolt=" + (int)cur.batteryVoltage);
        }

        if ((firstToken&DELTA_STATE_FLAG) != 0) {
            int stateInt = src.readInt();
            cur.states = (firstToken&DELTA_STATE_MASK) | (stateInt&(~DELTA_STATE_MASK));
            cur.batteryStatus = (byte)((stateInt>>STATE_BATTERY_STATUS_SHIFT)
                    & STATE_BATTERY_STATUS_MASK);
            cur.batteryHealth = (byte)((stateInt>>STATE_BATTERY_HEALTH_SHIFT)
                    & STATE_BATTERY_HEALTH_MASK);
            cur.batteryPlugType = (byte)((stateInt>>STATE_BATTERY_PLUG_SHIFT)
                    & STATE_BATTERY_PLUG_MASK);
            switch (cur.batteryPlugType) {
                case 1:
                    cur.batteryPlugType = BatteryManager.BATTERY_PLUGGED_AC;
                    break;
                case 2:
                    cur.batteryPlugType = BatteryManager.BATTERY_PLUGGED_USB;
                    break;
                case 3:
                    cur.batteryPlugType = BatteryManager.BATTERY_PLUGGED_WIRELESS;
                    break;
            }
            cur.numReadInts += 1;
            if (DEBUG) Slog.i(TAG, "READ DELTA: stateToken=0x"
                    + Integer.toHexString(stateInt)
                    + " batteryStatus=" + cur.batteryStatus
                    + " batteryHealth=" + cur.batteryHealth
                    + " batteryPlugType=" + cur.batteryPlugType
                    + " states=0x" + Integer.toHexString(cur.states));
        } else {
            cur.states = (firstToken&DELTA_STATE_MASK) | (cur.states&(~DELTA_STATE_MASK));
        }

        if ((firstToken&DELTA_STATE2_FLAG) != 0) {
            cur.states2 = src.readInt();
            if (DEBUG) Slog.i(TAG, "READ DELTA: states2=0x"
                    + Integer.toHexString(cur.states2));
        }

        if ((firstToken&DELTA_WAKELOCK_FLAG) != 0) {
            int indexes = src.readInt();
            int wakeLockIndex = indexes&0xffff;
            int wakeReasonIndex = (indexes>>16)&0xffff;
            if (wakeLockIndex != 0xffff) {
                cur.wakelockTag = cur.localWakelockTag;
                readHistoryTag(wakeLockIndex, cur.wakelockTag);
                if (DEBUG) Slog.i(TAG, "READ DELTA: wakelockTag=#" + cur.wakelockTag.poolIdx
                    + " " + cur.wakelockTag.uid + ":" + cur.wakelockTag.string);
            } else {
                cur.wakelockTag = null;
            }
            if (wakeReasonIndex != 0xffff) {
                cur.wakeReasonTag = cur.localWakeReasonTag;
                readHistoryTag(wakeReasonIndex, cur.wakeReasonTag);
                if (DEBUG) Slog.i(TAG, "READ DELTA: wakeReasonTag=#" + cur.wakeReasonTag.poolIdx
                    + " " + cur.wakeReasonTag.uid + ":" + cur.wakeReasonTag.string);
            } else {
                cur.wakeReasonTag = null;
            }
            cur.numReadInts += 1;
        } else {
            cur.wakelockTag = null;
            cur.wakeReasonTag = null;
        }

        if ((firstToken&DELTA_EVENT_FLAG) != 0) {
            cur.eventTag = cur.localEventTag;
            final int codeAndIndex = src.readInt();
            cur.eventCode = (codeAndIndex&0xffff);
            final int index = ((codeAndIndex>>16)&0xffff);
            readHistoryTag(index, cur.eventTag);
            cur.numReadInts += 1;
            if (DEBUG) Slog.i(TAG, "READ DELTA: event=" + cur.eventCode + " tag=#"
                    + cur.eventTag.poolIdx + " " + cur.eventTag.uid + ":"
                    + cur.eventTag.string);
        } else {
            cur.eventCode = HistoryItem.EVENT_NONE;
        }
    }

    @Override
    public void commitCurrentHistoryBatchLocked() {
        mHistoryLastWritten.cmd = HistoryItem.CMD_NULL;
    }

    void addHistoryBufferLocked(long elapsedRealtimeMs, long uptimeMs, HistoryItem cur) {
        if (!mHaveBatteryLevel || !mRecordingHistory) {
            return;
        }

        final long timeDiff = (mHistoryBaseTime+elapsedRealtimeMs) - mHistoryLastWritten.time;
        final int diffStates = mHistoryLastWritten.states^cur.states;
        final int diffStates2 = mHistoryLastWritten.states2^cur.states2;
        final int lastDiffStates = mHistoryLastWritten.states^mHistoryLastLastWritten.states;
        final int lastDiffStates2 = mHistoryLastWritten.states2^mHistoryLastLastWritten.states2;
        if (DEBUG) Slog.i(TAG, "ADD: tdelta=" + timeDiff + " diff="
                + Integer.toHexString(diffStates) + " lastDiff="
                + Integer.toHexString(lastDiffStates) + " diff2="
                + Integer.toHexString(diffStates2) + " lastDiff2="
                + Integer.toHexString(lastDiffStates2));
        if (mHistoryBufferLastPos >= 0 && mHistoryLastWritten.cmd == HistoryItem.CMD_UPDATE
                && timeDiff < 1000 && (diffStates&lastDiffStates) == 0
                && (diffStates2&lastDiffStates2) == 0
                && (mHistoryLastWritten.wakelockTag == null || cur.wakelockTag == null)
                && (mHistoryLastWritten.wakeReasonTag == null || cur.wakeReasonTag == null)
                && (mHistoryLastWritten.eventCode == HistoryItem.EVENT_NONE
                        || cur.eventCode == HistoryItem.EVENT_NONE)
                && mHistoryLastWritten.batteryLevel == cur.batteryLevel
                && mHistoryLastWritten.batteryStatus == cur.batteryStatus
                && mHistoryLastWritten.batteryHealth == cur.batteryHealth
                && mHistoryLastWritten.batteryPlugType == cur.batteryPlugType
                && mHistoryLastWritten.batteryTemperature == cur.batteryTemperature
                && mHistoryLastWritten.batteryVoltage == cur.batteryVoltage) {
            // We can merge this new change in with the last one.  Merging is
            // allowed as long as only the states have changed, and within those states
            // as long as no bit has changed both between now and the last entry, as
            // well as the last entry and the one before it (so we capture any toggles).
            if (DEBUG) Slog.i(TAG, "ADD: rewinding back to " + mHistoryBufferLastPos);
            mHistoryBuffer.setDataSize(mHistoryBufferLastPos);
            mHistoryBuffer.setDataPosition(mHistoryBufferLastPos);
            mHistoryBufferLastPos = -1;
            elapsedRealtimeMs = mHistoryLastWritten.time - mHistoryBaseTime;
            // If the last written history had a wakelock tag, we need to retain it.
            // Note that the condition above made sure that we aren't in a case where
            // both it and the current history item have a wakelock tag.
            if (mHistoryLastWritten.wakelockTag != null) {
                cur.wakelockTag = cur.localWakelockTag;
                cur.wakelockTag.setTo(mHistoryLastWritten.wakelockTag);
            }
            // If the last written history had a wake reason tag, we need to retain it.
            // Note that the condition above made sure that we aren't in a case where
            // both it and the current history item have a wakelock tag.
            if (mHistoryLastWritten.wakeReasonTag != null) {
                cur.wakeReasonTag = cur.localWakeReasonTag;
                cur.wakeReasonTag.setTo(mHistoryLastWritten.wakeReasonTag);
            }
            // If the last written history had an event, we need to retain it.
            // Note that the condition above made sure that we aren't in a case where
            // both it and the current history item have an event.
            if (mHistoryLastWritten.eventCode != HistoryItem.EVENT_NONE) {
                cur.eventCode = mHistoryLastWritten.eventCode;
                cur.eventTag = cur.localEventTag;
                cur.eventTag.setTo(mHistoryLastWritten.eventTag);
            }
            mHistoryLastWritten.setTo(mHistoryLastLastWritten);
        }

        final int dataSize = mHistoryBuffer.dataSize();
        if (dataSize >= MAX_HISTORY_BUFFER) {
            if (!mHistoryOverflow) {
                mHistoryOverflow = true;
                addHistoryBufferLocked(elapsedRealtimeMs, uptimeMs, HistoryItem.CMD_UPDATE, cur);
                addHistoryBufferLocked(elapsedRealtimeMs, uptimeMs, HistoryItem.CMD_OVERFLOW, cur);
                return;
            }

            // Once we've reached the maximum number of items, we only
            // record changes to the battery level and the most interesting states.
            // Once we've reached the maximum maximum number of items, we only
            // record changes to the battery level.
            if (mHistoryLastWritten.batteryLevel == cur.batteryLevel &&
                    (dataSize >= MAX_MAX_HISTORY_BUFFER
                            || ((mHistoryLastWritten.states^cur.states)
                                    & HistoryItem.MOST_INTERESTING_STATES) == 0
                            || ((mHistoryLastWritten.states2^cur.states2)
                                    & HistoryItem.MOST_INTERESTING_STATES2) == 0)) {
                return;
            }

            addHistoryBufferLocked(elapsedRealtimeMs, uptimeMs, HistoryItem.CMD_UPDATE, cur);
            return;
        }

        if (dataSize == 0) {
            // The history is currently empty; we need it to start with a time stamp.
            cur.currentTime = System.currentTimeMillis();
            mLastRecordedClockTime = cur.currentTime;
            mLastRecordedClockRealtime = elapsedRealtimeMs;
            addHistoryBufferLocked(elapsedRealtimeMs, uptimeMs, HistoryItem.CMD_RESET, cur);
        }
        addHistoryBufferLocked(elapsedRealtimeMs, uptimeMs, HistoryItem.CMD_UPDATE, cur);
    }

    private void addHistoryBufferLocked(long elapsedRealtimeMs, long uptimeMs, byte cmd,
            HistoryItem cur) {
        if (mIteratingHistory) {
            throw new IllegalStateException("Can't do this while iterating history!");
        }
        mHistoryBufferLastPos = mHistoryBuffer.dataPosition();
        mHistoryLastLastWritten.setTo(mHistoryLastWritten);
        mHistoryLastWritten.setTo(mHistoryBaseTime + elapsedRealtimeMs, cmd, cur);
        writeHistoryDelta(mHistoryBuffer, mHistoryLastWritten, mHistoryLastLastWritten);
        mLastHistoryElapsedRealtime = elapsedRealtimeMs;
        cur.wakelockTag = null;
        cur.wakeReasonTag = null;
        cur.eventCode = HistoryItem.EVENT_NONE;
        cur.eventTag = null;
        if (DEBUG_HISTORY) Slog.i(TAG, "Writing history buffer: was " + mHistoryBufferLastPos
                + " now " + mHistoryBuffer.dataPosition()
                + " size is now " + mHistoryBuffer.dataSize());
    }

    int mChangedStates = 0;
    int mChangedStates2 = 0;

    void addHistoryRecordLocked(long elapsedRealtimeMs, long uptimeMs) {
        if (mTrackRunningHistoryElapsedRealtime != 0) {
            final long diffElapsed = elapsedRealtimeMs - mTrackRunningHistoryElapsedRealtime;
            final long diffUptime = uptimeMs - mTrackRunningHistoryUptime;
            if (diffUptime < (diffElapsed-20)) {
                final long wakeElapsedTime = elapsedRealtimeMs - (diffElapsed - diffUptime);
                mHistoryAddTmp.setTo(mHistoryLastWritten);
                mHistoryAddTmp.wakelockTag = null;
                mHistoryAddTmp.wakeReasonTag = null;
                mHistoryAddTmp.eventCode = HistoryItem.EVENT_NONE;
                mHistoryAddTmp.states &= ~HistoryItem.STATE_CPU_RUNNING_FLAG;
                addHistoryRecordInnerLocked(wakeElapsedTime, uptimeMs, mHistoryAddTmp);
            }
        }
        mHistoryCur.states |= HistoryItem.STATE_CPU_RUNNING_FLAG;
        mTrackRunningHistoryElapsedRealtime = elapsedRealtimeMs;
        mTrackRunningHistoryUptime = uptimeMs;
        addHistoryRecordInnerLocked(elapsedRealtimeMs, uptimeMs, mHistoryCur);
    }

    void addHistoryRecordInnerLocked(long elapsedRealtimeMs, long uptimeMs, HistoryItem cur) {
        addHistoryBufferLocked(elapsedRealtimeMs, uptimeMs, cur);

        if (!USE_OLD_HISTORY) {
            return;
        }

        if (!mHaveBatteryLevel || !mRecordingHistory) {
            return;
        }

        // If the current time is basically the same as the last time,
        // and no states have since the last recorded entry changed and
        // are now resetting back to their original value, then just collapse
        // into one record.
        if (mHistoryEnd != null && mHistoryEnd.cmd == HistoryItem.CMD_UPDATE
                && (mHistoryBaseTime+elapsedRealtimeMs) < (mHistoryEnd.time+1000)
                && ((mHistoryEnd.states^cur.states)&mChangedStates) == 0
                && ((mHistoryEnd.states2^cur.states2)&mChangedStates2) == 0) {
            // If the current is the same as the one before, then we no
            // longer need the entry.
            if (mHistoryLastEnd != null && mHistoryLastEnd.cmd == HistoryItem.CMD_UPDATE
                    && (mHistoryBaseTime+elapsedRealtimeMs) < (mHistoryEnd.time+500)
                    && mHistoryLastEnd.sameNonEvent(cur)) {
                mHistoryLastEnd.next = null;
                mHistoryEnd.next = mHistoryCache;
                mHistoryCache = mHistoryEnd;
                mHistoryEnd = mHistoryLastEnd;
                mHistoryLastEnd = null;
            } else {
                mChangedStates |= mHistoryEnd.states^cur.states;
                mChangedStates2 |= mHistoryEnd.states^cur.states2;
                mHistoryEnd.setTo(mHistoryEnd.time, HistoryItem.CMD_UPDATE, cur);
            }
            return;
        }

        mChangedStates = 0;
        mChangedStates2 = 0;

        if (mNumHistoryItems == MAX_HISTORY_ITEMS
                || mNumHistoryItems == MAX_MAX_HISTORY_ITEMS) {
            addHistoryRecordLocked(elapsedRealtimeMs, HistoryItem.CMD_OVERFLOW);
        }

        if (mNumHistoryItems >= MAX_HISTORY_ITEMS) {
            // Once we've reached the maximum number of items, we only
            // record changes to the battery level and the most interesting states.
            // Once we've reached the maximum maximum number of items, we only
            // record changes to the battery level.
            if (mHistoryEnd != null && mHistoryEnd.batteryLevel
                    == cur.batteryLevel &&
                    (mNumHistoryItems >= MAX_MAX_HISTORY_ITEMS
                            || ((mHistoryEnd.states^cur.states)
                                    & HistoryItem.MOST_INTERESTING_STATES) == 0)) {
                return;
            }
        }

        addHistoryRecordLocked(elapsedRealtimeMs, HistoryItem.CMD_UPDATE);
    }

    void addHistoryEventLocked(long elapsedRealtimeMs, long uptimeMs, int code,
            String name, int uid) {
        mHistoryCur.eventCode = code;
        mHistoryCur.eventTag = mHistoryCur.localEventTag;
        mHistoryCur.eventTag.string = name;
        mHistoryCur.eventTag.uid = uid;
        addHistoryRecordLocked(elapsedRealtimeMs, uptimeMs);
    }

    void addHistoryRecordLocked(long elapsedRealtimeMs, long uptimeMs, byte cmd, HistoryItem cur) {
        HistoryItem rec = mHistoryCache;
        if (rec != null) {
            mHistoryCache = rec.next;
        } else {
            rec = new HistoryItem();
        }
        rec.setTo(mHistoryBaseTime + elapsedRealtimeMs, cmd, cur);

        addHistoryRecordLocked(rec);
    }

    void addHistoryRecordLocked(HistoryItem rec) {
        mNumHistoryItems++;
        rec.next = null;
        mHistoryLastEnd = mHistoryEnd;
        if (mHistoryEnd != null) {
            mHistoryEnd.next = rec;
            mHistoryEnd = rec;
        } else {
            mHistory = mHistoryEnd = rec;
        }
    }

    void clearHistoryLocked() {
        if (DEBUG_HISTORY) Slog.i(TAG, "********** CLEARING HISTORY!");
        if (USE_OLD_HISTORY) {
            if (mHistory != null) {
                mHistoryEnd.next = mHistoryCache;
                mHistoryCache = mHistory;
                mHistory = mHistoryLastEnd = mHistoryEnd = null;
            }
            mNumHistoryItems = 0;
        }

        mHistoryBaseTime = 0;
        mLastHistoryElapsedRealtime = 0;
        mTrackRunningHistoryElapsedRealtime = 0;
        mTrackRunningHistoryUptime = 0;

        mHistoryBuffer.setDataSize(0);
        mHistoryBuffer.setDataPosition(0);
        mHistoryBuffer.setDataCapacity(MAX_HISTORY_BUFFER / 2);
        mHistoryLastLastWritten.clear();
        mHistoryLastWritten.clear();
        mHistoryTagPool.clear();
        mNextHistoryTagIdx = 0;
        mNumHistoryTagChars = 0;
        mHistoryBufferLastPos = -1;
        mHistoryOverflow = false;
        mLastRecordedClockTime = 0;
        mLastRecordedClockRealtime = 0;
    }

    public void updateTimeBasesLocked(boolean unplugged, boolean screenOff, long uptime,
            long realtime) {
        if (mOnBatteryTimeBase.setRunning(unplugged, uptime, realtime)) {
            if (unplugged) {
                // Track bt headset ping count
                mBluetoothPingStart = getCurrentBluetoothPingCount();
                mBluetoothPingCount = 0;
            } else {
                // Track bt headset ping count
                mBluetoothPingCount = getBluetoothPingCount();
                mBluetoothPingStart = -1;
            }
        }

        boolean unpluggedScreenOff = unplugged && screenOff;
        if (unpluggedScreenOff != mOnBatteryScreenOffTimeBase.isRunning()) {
            updateKernelWakelocksLocked();
            requestWakelockCpuUpdate();
            if (!unpluggedScreenOff) {
                // We are switching to no longer tracking wake locks, but we want
                // the next CPU update we receive to take them in to account.
                mDistributeWakelockCpu = true;
            }
            mOnBatteryScreenOffTimeBase.setRunning(unpluggedScreenOff, uptime, realtime);
        }
    }

    public void addIsolatedUidLocked(int isolatedUid, int appUid) {
        mIsolatedUids.put(isolatedUid, appUid);
    }

    public void removeIsolatedUidLocked(int isolatedUid, int appUid) {
        int curUid = mIsolatedUids.get(isolatedUid, -1);
        if (curUid == appUid) {
            mIsolatedUids.delete(isolatedUid);
        }
    }

    public int mapUid(int uid) {
        int isolated = mIsolatedUids.get(uid, -1);
        return isolated > 0 ? isolated : uid;
    }

    public void noteEventLocked(int code, String name, int uid) {
        uid = mapUid(uid);
        if (!mActiveEvents.updateState(code, name, uid, 0)) {
            return;
        }
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        addHistoryEventLocked(elapsedRealtime, uptime, code, name, uid);
    }

    public void noteCurrentTimeChangedLocked() {
        final long currentTime = System.currentTimeMillis();
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        if (isStartClockTimeValid()) {
            // Has the time changed sufficiently that it is really worth recording?
            if (mLastRecordedClockTime != 0) {
                long expectedClockTime = mLastRecordedClockTime
                        + (elapsedRealtime - mLastRecordedClockRealtime);
                if (currentTime >= (expectedClockTime-500)
                        && currentTime <= (expectedClockTime+500)) {
                    // Not sufficiently changed, skip!
                    return;
                }
            }
        }
        recordCurrentTimeChangeLocked(currentTime, elapsedRealtime, uptime);
        if (isStartClockTimeValid()) {
            mStartClockTime = currentTime;
        }
    }

    public void noteProcessStartLocked(String name, int uid) {
        uid = mapUid(uid);
        if (isOnBattery()) {
            Uid u = getUidStatsLocked(uid);
            u.getProcessStatsLocked(name).incStartsLocked();
        }
        if (!mActiveEvents.updateState(HistoryItem.EVENT_PROC_START, name, uid, 0)) {
            return;
        }
        if (!mRecordAllHistory) {
            return;
        }
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        addHistoryEventLocked(elapsedRealtime, uptime, HistoryItem.EVENT_PROC_START, name, uid);
    }

    public void noteProcessCrashLocked(String name, int uid) {
        uid = mapUid(uid);
        if (isOnBattery()) {
            Uid u = getUidStatsLocked(uid);
            u.getProcessStatsLocked(name).incNumCrashesLocked();
        }
    }

    public void noteProcessAnrLocked(String name, int uid) {
        uid = mapUid(uid);
        if (isOnBattery()) {
            Uid u = getUidStatsLocked(uid);
            u.getProcessStatsLocked(name).incNumAnrsLocked();
        }
    }

    public void noteProcessStateLocked(String name, int uid, int state) {
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        getUidStatsLocked(uid).updateProcessStateLocked(name, state, elapsedRealtime);
    }

    public void noteProcessFinishLocked(String name, int uid) {
        uid = mapUid(uid);
        if (!mActiveEvents.updateState(HistoryItem.EVENT_PROC_FINISH, name, uid, 0)) {
            return;
        }
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        getUidStatsLocked(uid).updateProcessStateLocked(name, Uid.PROCESS_STATE_NONE,
                elapsedRealtime);
        if (!mRecordAllHistory) {
            return;
        }
        addHistoryEventLocked(elapsedRealtime, uptime, HistoryItem.EVENT_PROC_FINISH, name, uid);
    }

    public void noteSyncStartLocked(String name, int uid) {
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        getUidStatsLocked(uid).noteStartSyncLocked(name, elapsedRealtime);
        if (!mActiveEvents.updateState(HistoryItem.EVENT_SYNC_START, name, uid, 0)) {
            return;
        }
        addHistoryEventLocked(elapsedRealtime, uptime, HistoryItem.EVENT_SYNC_START, name, uid);
    }

    public void noteSyncFinishLocked(String name, int uid) {
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        getUidStatsLocked(uid).noteStopSyncLocked(name, elapsedRealtime);
        if (!mActiveEvents.updateState(HistoryItem.EVENT_SYNC_FINISH, name, uid, 0)) {
            return;
        }
        addHistoryEventLocked(elapsedRealtime, uptime, HistoryItem.EVENT_SYNC_FINISH, name, uid);
    }

    public void noteJobStartLocked(String name, int uid) {
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        getUidStatsLocked(uid).noteStartJobLocked(name, elapsedRealtime);
        if (!mActiveEvents.updateState(HistoryItem.EVENT_JOB_START, name, uid, 0)) {
            return;
        }
        addHistoryEventLocked(elapsedRealtime, uptime, HistoryItem.EVENT_JOB_START, name, uid);
    }

    public void noteJobFinishLocked(String name, int uid) {
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        getUidStatsLocked(uid).noteStopJobLocked(name, elapsedRealtime);
        if (!mActiveEvents.updateState(HistoryItem.EVENT_JOB_FINISH, name, uid, 0)) {
            return;
        }
        addHistoryEventLocked(elapsedRealtime, uptime, HistoryItem.EVENT_JOB_FINISH, name, uid);
    }

    private void requestWakelockCpuUpdate() {
        if (!mHandler.hasMessages(MSG_UPDATE_WAKELOCKS)) {
            Message m = mHandler.obtainMessage(MSG_UPDATE_WAKELOCKS);
            mHandler.sendMessageDelayed(m, DELAY_UPDATE_WAKELOCKS);
        }
    }

    public void setRecordAllHistoryLocked(boolean enabled) {
        mRecordAllHistory = enabled;
        if (!enabled) {
            // Clear out any existing state.
            mActiveEvents.removeEvents(HistoryItem.EVENT_WAKE_LOCK);
            // Record the currently running processes as stopping, now that we are no
            // longer tracking them.
            HashMap<String, SparseIntArray> active = mActiveEvents.getStateForEvent(
                    HistoryItem.EVENT_PROC);
            if (active != null) {
                long mSecRealtime = SystemClock.elapsedRealtime();
                final long mSecUptime = SystemClock.uptimeMillis();
                for (HashMap.Entry<String, SparseIntArray> ent : active.entrySet()) {
                    SparseIntArray uids = ent.getValue();
                    for (int j=0; j<uids.size(); j++) {
                        addHistoryEventLocked(mSecRealtime, mSecUptime,
                                HistoryItem.EVENT_PROC_FINISH, ent.getKey(), uids.keyAt(j));
                    }
                }
            }
        } else {
            // Record the currently running processes as starting, now that we are tracking them.
            HashMap<String, SparseIntArray> active = mActiveEvents.getStateForEvent(
                    HistoryItem.EVENT_PROC);
            if (active != null) {
                long mSecRealtime = SystemClock.elapsedRealtime();
                final long mSecUptime = SystemClock.uptimeMillis();
                for (HashMap.Entry<String, SparseIntArray> ent : active.entrySet()) {
                    SparseIntArray uids = ent.getValue();
                    for (int j=0; j<uids.size(); j++) {
                        addHistoryEventLocked(mSecRealtime, mSecUptime,
                                HistoryItem.EVENT_PROC_START, ent.getKey(), uids.keyAt(j));
                    }
                }
            }
        }
    }

    public void setNoAutoReset(boolean enabled) {
        mNoAutoReset = enabled;
    }

    private String mInitialAcquireWakeName;
    private int mInitialAcquireWakeUid = -1;

    public void noteStartWakeLocked(int uid, int pid, String name, String historyName, int type,
            boolean unimportantForLogging, long elapsedRealtime, long uptime) {
        uid = mapUid(uid);
        if (type == WAKE_TYPE_PARTIAL) {
            // Only care about partial wake locks, since full wake locks
            // will be canceled when the user puts the screen to sleep.
            aggregateLastWakeupUptimeLocked(uptime);
            if (historyName == null) {
                historyName = name;
            }
            if (mRecordAllHistory) {
                if (mActiveEvents.updateState(HistoryItem.EVENT_WAKE_LOCK_START, historyName,
                        uid, 0)) {
                    addHistoryEventLocked(elapsedRealtime, uptime,
                            HistoryItem.EVENT_WAKE_LOCK_START, historyName, uid);
                }
            }
            if (mWakeLockNesting == 0) {
                mHistoryCur.states |= HistoryItem.STATE_WAKE_LOCK_FLAG;
                if (DEBUG_HISTORY) Slog.v(TAG, "Start wake lock to: "
                        + Integer.toHexString(mHistoryCur.states));
                mHistoryCur.wakelockTag = mHistoryCur.localWakelockTag;
                mHistoryCur.wakelockTag.string = mInitialAcquireWakeName = historyName;
                mHistoryCur.wakelockTag.uid = mInitialAcquireWakeUid = uid;
                mWakeLockImportant = !unimportantForLogging;
                addHistoryRecordLocked(elapsedRealtime, uptime);
            } else if (!mWakeLockImportant && !unimportantForLogging
                    && mHistoryLastWritten.cmd == HistoryItem.CMD_UPDATE) {
                if (mHistoryLastWritten.wakelockTag != null) {
                    // We'll try to update the last tag.
                    mHistoryLastWritten.wakelockTag = null;
                    mHistoryCur.wakelockTag = mHistoryCur.localWakelockTag;
                    mHistoryCur.wakelockTag.string = mInitialAcquireWakeName = historyName;
                    mHistoryCur.wakelockTag.uid = mInitialAcquireWakeUid = uid;
                    addHistoryRecordLocked(elapsedRealtime, uptime);
                }
                mWakeLockImportant = true;
            }
            mWakeLockNesting++;
        }
        if (uid >= 0) {
            //if (uid == 0) {
            //    Slog.wtf(TAG, "Acquiring wake lock from root: " + name);
            //}
            requestWakelockCpuUpdate();
            getUidStatsLocked(uid).noteStartWakeLocked(pid, name, type, elapsedRealtime);
        }
    }

    public void noteStopWakeLocked(int uid, int pid, String name, String historyName, int type,
            long elapsedRealtime, long uptime) {
        uid = mapUid(uid);
        if (type == WAKE_TYPE_PARTIAL) {
            mWakeLockNesting--;
            if (mRecordAllHistory) {
                if (historyName == null) {
                    historyName = name;
                }
                if (mActiveEvents.updateState(HistoryItem.EVENT_WAKE_LOCK_FINISH, historyName,
                        uid, 0)) {
                    addHistoryEventLocked(elapsedRealtime, uptime,
                            HistoryItem.EVENT_WAKE_LOCK_FINISH, historyName, uid);
                }
            }
            if (mWakeLockNesting == 0) {
                mHistoryCur.states &= ~HistoryItem.STATE_WAKE_LOCK_FLAG;
                if (DEBUG_HISTORY) Slog.v(TAG, "Stop wake lock to: "
                        + Integer.toHexString(mHistoryCur.states));
                mInitialAcquireWakeName = null;
                mInitialAcquireWakeUid = -1;
                addHistoryRecordLocked(elapsedRealtime, uptime);
            }
        }
        if (uid >= 0) {
            requestWakelockCpuUpdate();
            getUidStatsLocked(uid).noteStopWakeLocked(pid, name, type, elapsedRealtime);
        }
    }

    public void noteStartWakeFromSourceLocked(WorkSource ws, int pid, String name,
            String historyName, int type, boolean unimportantForLogging) {
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        final int N = ws.size();
        for (int i=0; i<N; i++) {
            noteStartWakeLocked(ws.get(i), pid, name, historyName, type, unimportantForLogging,
                    elapsedRealtime, uptime);
        }
    }

    public void noteChangeWakelockFromSourceLocked(WorkSource ws, int pid, String name,
            String historyName, int type, WorkSource newWs, int newPid, String newName,
            String newHistoryName, int newType, boolean newUnimportantForLogging) {
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        // For correct semantics, we start the need worksources first, so that we won't
        // make inappropriate history items as if all wake locks went away and new ones
        // appeared.  This is okay because tracking of wake locks allows nesting.
        final int NN = newWs.size();
        for (int i=0; i<NN; i++) {
            noteStartWakeLocked(newWs.get(i), newPid, newName, newHistoryName, newType,
                    newUnimportantForLogging, elapsedRealtime, uptime);
        }
        final int NO = ws.size();
        for (int i=0; i<NO; i++) {
            noteStopWakeLocked(ws.get(i), pid, name, historyName, type, elapsedRealtime, uptime);
        }
    }

    public void noteStopWakeFromSourceLocked(WorkSource ws, int pid, String name,
            String historyName, int type) {
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        final int N = ws.size();
        for (int i=0; i<N; i++) {
            noteStopWakeLocked(ws.get(i), pid, name, historyName, type, elapsedRealtime, uptime);
        }
    }

    void aggregateLastWakeupUptimeLocked(long uptimeMs) {
        if (mLastWakeupReason != null) {
            long deltaUptime = uptimeMs - mLastWakeupUptimeMs;
            SamplingTimer timer = getWakeupReasonTimerLocked(mLastWakeupReason);
            timer.addCurrentReportedCount(1);
            timer.addCurrentReportedTotalTime(deltaUptime * 1000); // time is in microseconds
            mLastWakeupReason = null;
        }
    }

    public void noteWakeupReasonLocked(String reason) {
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        if (DEBUG_HISTORY) Slog.v(TAG, "Wakeup reason \"" + reason +"\": "
                + Integer.toHexString(mHistoryCur.states));
        aggregateLastWakeupUptimeLocked(uptime);
        mHistoryCur.wakeReasonTag = mHistoryCur.localWakeReasonTag;
        mHistoryCur.wakeReasonTag.string = reason;
        mHistoryCur.wakeReasonTag.uid = 0;
        mLastWakeupReason = reason;
        mLastWakeupUptimeMs = uptime;
        addHistoryRecordLocked(elapsedRealtime, uptime);
    }

    public int startAddingCpuLocked() {
        mHandler.removeMessages(MSG_UPDATE_WAKELOCKS);

        final int N = mPartialTimers.size();
        if (N == 0) {
            mLastPartialTimers.clear();
            mDistributeWakelockCpu = false;
            return 0;
        }

        if (!mOnBatteryScreenOffTimeBase.isRunning() && !mDistributeWakelockCpu) {
            return 0;
        }

        mDistributeWakelockCpu = false;

        // How many timers should consume CPU?  Only want to include ones
        // that have already been in the list.
        for (int i=0; i<N; i++) {
            StopwatchTimer st = mPartialTimers.get(i);
            if (st.mInList) {
                Uid uid = st.mUid;
                // We don't include the system UID, because it so often
                // holds wake locks at one request or another of an app.
                if (uid != null && uid.mUid != Process.SYSTEM_UID) {
                    return 50;
                }
            }
        }

        return 0;
    }

    public void finishAddingCpuLocked(int perc, int utime, int stime, long[] cpuSpeedTimes) {
        final int N = mPartialTimers.size();
        if (perc != 0) {
            int num = 0;
            for (int i=0; i<N; i++) {
                StopwatchTimer st = mPartialTimers.get(i);
                if (st.mInList) {
                    Uid uid = st.mUid;
                    // We don't include the system UID, because it so often
                    // holds wake locks at one request or another of an app.
                    if (uid != null && uid.mUid != Process.SYSTEM_UID) {
                        num++;
                    }
                }
            }
            if (num != 0) {
                for (int i=0; i<N; i++) {
                    StopwatchTimer st = mPartialTimers.get(i);
                    if (st.mInList) {
                        Uid uid = st.mUid;
                        if (uid != null && uid.mUid != Process.SYSTEM_UID) {
                            int myUTime = utime/num;
                            int mySTime = stime/num;
                            utime -= myUTime;
                            stime -= mySTime;
                            num--;
                            Uid.Proc proc = uid.getProcessStatsLocked("*wakelock*");
                            proc.addCpuTimeLocked(myUTime, mySTime);
                            proc.addSpeedStepTimes(cpuSpeedTimes);
                        }
                    }
                }
            }

            // Just in case, collect any lost CPU time.
            if (utime != 0 || stime != 0) {
                Uid uid = getUidStatsLocked(Process.SYSTEM_UID);
                if (uid != null) {
                    Uid.Proc proc = uid.getProcessStatsLocked("*lost*");
                    proc.addCpuTimeLocked(utime, stime);
                    proc.addSpeedStepTimes(cpuSpeedTimes);
                }
            }
        }

        final int NL = mLastPartialTimers.size();
        boolean diff = N != NL;
        for (int i=0; i<NL && !diff; i++) {
            diff |= mPartialTimers.get(i) != mLastPartialTimers.get(i);
        }
        if (!diff) {
            for (int i=0; i<NL; i++) {
                mPartialTimers.get(i).mInList = true;
            }
            return;
        }

        for (int i=0; i<NL; i++) {
            mLastPartialTimers.get(i).mInList = false;
        }
        mLastPartialTimers.clear();
        for (int i=0; i<N; i++) {
            StopwatchTimer st = mPartialTimers.get(i);
            st.mInList = true;
            mLastPartialTimers.add(st);
        }
    }

    public void noteProcessDiedLocked(int uid, int pid) {
        uid = mapUid(uid);
        Uid u = mUidStats.get(uid);
        if (u != null) {
            u.mPids.remove(pid);
        }
    }

    public long getProcessWakeTime(int uid, int pid, long realtime) {
        uid = mapUid(uid);
        Uid u = mUidStats.get(uid);
        if (u != null) {
            Uid.Pid p = u.mPids.get(pid);
            if (p != null) {
                return p.mWakeSumMs + (p.mWakeNesting > 0 ? (realtime - p.mWakeStartMs) : 0);
            }
        }
        return 0;
    }

    public void reportExcessiveWakeLocked(int uid, String proc, long overTime, long usedTime) {
        uid = mapUid(uid);
        Uid u = mUidStats.get(uid);
        if (u != null) {
            u.reportExcessiveWakeLocked(proc, overTime, usedTime);
        }
    }

    public void reportExcessiveCpuLocked(int uid, String proc, long overTime, long usedTime) {
        uid = mapUid(uid);
        Uid u = mUidStats.get(uid);
        if (u != null) {
            u.reportExcessiveCpuLocked(proc, overTime, usedTime);
        }
    }

    int mSensorNesting;

    public void noteStartSensorLocked(int uid, int sensor) {
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        if (mSensorNesting == 0) {
            mHistoryCur.states |= HistoryItem.STATE_SENSOR_ON_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "Start sensor to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
        }
        mSensorNesting++;
        getUidStatsLocked(uid).noteStartSensor(sensor, elapsedRealtime);
    }

    public void noteStopSensorLocked(int uid, int sensor) {
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        mSensorNesting--;
        if (mSensorNesting == 0) {
            mHistoryCur.states &= ~HistoryItem.STATE_SENSOR_ON_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "Stop sensor to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
        }
        getUidStatsLocked(uid).noteStopSensor(sensor, elapsedRealtime);
    }

    int mGpsNesting;

    public void noteStartGpsLocked(int uid) {
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        if (mGpsNesting == 0) {
            mHistoryCur.states |= HistoryItem.STATE_GPS_ON_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "Start GPS to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
        }
        mGpsNesting++;
        getUidStatsLocked(uid).noteStartGps(elapsedRealtime);
    }

    public void noteStopGpsLocked(int uid) {
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        mGpsNesting--;
        if (mGpsNesting == 0) {
            mHistoryCur.states &= ~HistoryItem.STATE_GPS_ON_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "Stop GPS to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
        }
        getUidStatsLocked(uid).noteStopGps(elapsedRealtime);
    }

    public void noteScreenStateLocked(int state) {
        if (mScreenState != state) {
            final int oldState = mScreenState;
            mScreenState = state;
            if (DEBUG) Slog.v(TAG, "Screen state: oldState=" + Display.stateToString(oldState)
                    + ", newState=" + Display.stateToString(state));

            if (state != Display.STATE_UNKNOWN) {
                int stepState = state-1;
                if (stepState < 4) {
                    mModStepMode |= (mCurStepMode&STEP_LEVEL_MODE_SCREEN_STATE) ^ stepState;
                    mCurStepMode = (mCurStepMode&~STEP_LEVEL_MODE_SCREEN_STATE) | stepState;
                } else {
                    Slog.wtf(TAG, "Unexpected screen state: " + state);
                }
            }

            if (state == Display.STATE_ON) {
                // Screen turning on.
                final long elapsedRealtime = SystemClock.elapsedRealtime();
                final long uptime = SystemClock.uptimeMillis();
                mHistoryCur.states |= HistoryItem.STATE_SCREEN_ON_FLAG;
                if (DEBUG_HISTORY) Slog.v(TAG, "Screen on to: "
                        + Integer.toHexString(mHistoryCur.states));
                addHistoryRecordLocked(elapsedRealtime, uptime);
                mScreenOnTimer.startRunningLocked(elapsedRealtime);
                if (mScreenBrightnessBin >= 0) {
                    mScreenBrightnessTimer[mScreenBrightnessBin].startRunningLocked(elapsedRealtime);
                }

                updateTimeBasesLocked(mOnBatteryTimeBase.isRunning(), false,
                        SystemClock.uptimeMillis() * 1000, elapsedRealtime * 1000);

                // Fake a wake lock, so we consider the device waked as long
                // as the screen is on.
                noteStartWakeLocked(-1, -1, "screen", null, WAKE_TYPE_PARTIAL, false,
                        elapsedRealtime, uptime);

                // Update discharge amounts.
                if (mOnBatteryInternal) {
                    updateDischargeScreenLevelsLocked(false, true);
                }
            } else if (oldState == Display.STATE_ON) {
                // Screen turning off or dozing.
                final long elapsedRealtime = SystemClock.elapsedRealtime();
                final long uptime = SystemClock.uptimeMillis();
                mHistoryCur.states &= ~HistoryItem.STATE_SCREEN_ON_FLAG;
                if (DEBUG_HISTORY) Slog.v(TAG, "Screen off to: "
                        + Integer.toHexString(mHistoryCur.states));
                addHistoryRecordLocked(elapsedRealtime, uptime);
                mScreenOnTimer.stopRunningLocked(elapsedRealtime);
                if (mScreenBrightnessBin >= 0) {
                    mScreenBrightnessTimer[mScreenBrightnessBin].stopRunningLocked(elapsedRealtime);
                }

                noteStopWakeLocked(-1, -1, "screen", "screen", WAKE_TYPE_PARTIAL,
                        elapsedRealtime, uptime);

                updateTimeBasesLocked(mOnBatteryTimeBase.isRunning(), true,
                        SystemClock.uptimeMillis() * 1000, elapsedRealtime * 1000);

                // Update discharge amounts.
                if (mOnBatteryInternal) {
                    updateDischargeScreenLevelsLocked(true, false);
                }
            }
        }
    }

    public void noteScreenBrightnessLocked(int brightness) {
        // Bin the brightness.
        int bin = brightness / (256/NUM_SCREEN_BRIGHTNESS_BINS);
        if (bin < 0) bin = 0;
        else if (bin >= NUM_SCREEN_BRIGHTNESS_BINS) bin = NUM_SCREEN_BRIGHTNESS_BINS-1;
        if (mScreenBrightnessBin != bin) {
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            final long uptime = SystemClock.uptimeMillis();
            mHistoryCur.states = (mHistoryCur.states&~HistoryItem.STATE_BRIGHTNESS_MASK)
                    | (bin << HistoryItem.STATE_BRIGHTNESS_SHIFT);
            if (DEBUG_HISTORY) Slog.v(TAG, "Screen brightness " + bin + " to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
            if (mScreenState == Display.STATE_ON) {
                if (mScreenBrightnessBin >= 0) {
                    mScreenBrightnessTimer[mScreenBrightnessBin].stopRunningLocked(elapsedRealtime);
                }
                mScreenBrightnessTimer[bin].startRunningLocked(elapsedRealtime);
            }
            mScreenBrightnessBin = bin;
        }
    }

    public void noteUserActivityLocked(int uid, int event) {
        if (mOnBatteryInternal) {
            uid = mapUid(uid);
            getUidStatsLocked(uid).noteUserActivityLocked(event);
        }
    }

    public void noteInteractiveLocked(boolean interactive) {
        if (mInteractive != interactive) {
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            mInteractive = interactive;
            if (DEBUG) Slog.v(TAG, "Interactive: " + interactive);
            if (interactive) {
                mInteractiveTimer.startRunningLocked(elapsedRealtime);
            } else {
                mInteractiveTimer.stopRunningLocked(elapsedRealtime);
            }
        }
    }

    public void noteConnectivityChangedLocked(int type, String extra) {
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        addHistoryEventLocked(elapsedRealtime, uptime, HistoryItem.EVENT_CONNECTIVITY_CHANGED,
                extra, type);
        mNumConnectivityChange++;
    }

    public void noteMobileRadioPowerState(int powerState, long timestampNs) {
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        if (mMobileRadioPowerState != powerState) {
            long realElapsedRealtimeMs;
            final boolean active =
                    powerState == DataConnectionRealTimeInfo.DC_POWER_STATE_MEDIUM
                            || powerState == DataConnectionRealTimeInfo.DC_POWER_STATE_HIGH;
            if (active) {
                mMobileRadioActiveStartTime = realElapsedRealtimeMs = elapsedRealtime;
                mHistoryCur.states |= HistoryItem.STATE_MOBILE_RADIO_ACTIVE_FLAG;
            } else {
                realElapsedRealtimeMs = timestampNs / (1000*1000);
                long lastUpdateTimeMs = mMobileRadioActiveStartTime;
                if (realElapsedRealtimeMs < lastUpdateTimeMs) {
                    Slog.wtf(TAG, "Data connection inactive timestamp " + realElapsedRealtimeMs
                            + " is before start time " + lastUpdateTimeMs);
                    realElapsedRealtimeMs = elapsedRealtime;
                } else if (realElapsedRealtimeMs < elapsedRealtime) {
                    mMobileRadioActiveAdjustedTime.addCountLocked(elapsedRealtime
                            - realElapsedRealtimeMs);
                }
                mHistoryCur.states &= ~HistoryItem.STATE_MOBILE_RADIO_ACTIVE_FLAG;
            }
            if (DEBUG_HISTORY) Slog.v(TAG, "Mobile network active " + active + " to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
            mMobileRadioPowerState = powerState;
            if (active) {
                mMobileRadioActiveTimer.startRunningLocked(elapsedRealtime);
                mMobileRadioActivePerAppTimer.startRunningLocked(elapsedRealtime);
            } else {
                mMobileRadioActiveTimer.stopRunningLocked(realElapsedRealtimeMs);
                updateNetworkActivityLocked(NET_UPDATE_MOBILE, realElapsedRealtimeMs);
                mMobileRadioActivePerAppTimer.stopRunningLocked(realElapsedRealtimeMs);
            }
        }
    }

    public void noteLowPowerMode(boolean enabled) {
        if (mLowPowerModeEnabled != enabled) {
            int stepState = enabled ? STEP_LEVEL_MODE_POWER_SAVE : 0;
            mModStepMode |= (mCurStepMode&STEP_LEVEL_MODE_POWER_SAVE) ^ stepState;
            mCurStepMode = (mCurStepMode&~STEP_LEVEL_MODE_POWER_SAVE) | stepState;
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            final long uptime = SystemClock.uptimeMillis();
            mLowPowerModeEnabled = enabled;
            if (enabled) {
                mHistoryCur.states2 |= HistoryItem.STATE2_LOW_POWER_FLAG;
                if (DEBUG_HISTORY) Slog.v(TAG, "Low power mode enabled to: "
                        + Integer.toHexString(mHistoryCur.states2));
                mLowPowerModeEnabledTimer.startRunningLocked(elapsedRealtime);
            } else {
                mHistoryCur.states2 &= ~HistoryItem.STATE2_LOW_POWER_FLAG;
                if (DEBUG_HISTORY) Slog.v(TAG, "Low power mode disabled to: "
                        + Integer.toHexString(mHistoryCur.states2));
                mLowPowerModeEnabledTimer.stopRunningLocked(elapsedRealtime);
            }
            addHistoryRecordLocked(elapsedRealtime, uptime);
        }
    }

    public void notePhoneOnLocked() {
        if (!mPhoneOn) {
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            final long uptime = SystemClock.uptimeMillis();
            mHistoryCur.states |= HistoryItem.STATE_PHONE_IN_CALL_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "Phone on to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
            mPhoneOn = true;
            mPhoneOnTimer.startRunningLocked(elapsedRealtime);
        }
    }

    public void notePhoneOffLocked() {
        if (mPhoneOn) {
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            final long uptime = SystemClock.uptimeMillis();
            mHistoryCur.states &= ~HistoryItem.STATE_PHONE_IN_CALL_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "Phone off to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
            mPhoneOn = false;
            mPhoneOnTimer.stopRunningLocked(elapsedRealtime);
        }
    }

    void stopAllPhoneSignalStrengthTimersLocked(int except) {
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        for (int i = 0; i < SignalStrength.NUM_SIGNAL_STRENGTH_BINS; i++) {
            if (i == except) {
                continue;
            }
            while (mPhoneSignalStrengthsTimer[i].isRunningLocked()) {
                mPhoneSignalStrengthsTimer[i].stopRunningLocked(elapsedRealtime);
            }
        }
    }

    private int fixPhoneServiceState(int state, int signalBin) {
        if (mPhoneSimStateRaw == TelephonyManager.SIM_STATE_ABSENT) {
            // In this case we will always be STATE_OUT_OF_SERVICE, so need
            // to infer that we are scanning from other data.
            if (state == ServiceState.STATE_OUT_OF_SERVICE
                    && signalBin > SignalStrength.SIGNAL_STRENGTH_NONE_OR_UNKNOWN) {
                state = ServiceState.STATE_IN_SERVICE;
            }
        }

        return state;
    }

    private void updateAllPhoneStateLocked(int state, int simState, int strengthBin) {
        boolean scanning = false;
        boolean newHistory = false;

        mPhoneServiceStateRaw = state;
        mPhoneSimStateRaw = simState;
        mPhoneSignalStrengthBinRaw = strengthBin;

        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();

        if (simState == TelephonyManager.SIM_STATE_ABSENT) {
            // In this case we will always be STATE_OUT_OF_SERVICE, so need
            // to infer that we are scanning from other data.
            if (state == ServiceState.STATE_OUT_OF_SERVICE
                    && strengthBin > SignalStrength.SIGNAL_STRENGTH_NONE_OR_UNKNOWN) {
                state = ServiceState.STATE_IN_SERVICE;
            }
        }

        // If the phone is powered off, stop all timers.
        if (state == ServiceState.STATE_POWER_OFF) {
            strengthBin = -1;

        // If we are in service, make sure the correct signal string timer is running.
        } else if (state == ServiceState.STATE_IN_SERVICE) {
            // Bin will be changed below.

        // If we're out of service, we are in the lowest signal strength
        // bin and have the scanning bit set.
        } else if (state == ServiceState.STATE_OUT_OF_SERVICE) {
            scanning = true;
            strengthBin = SignalStrength.SIGNAL_STRENGTH_NONE_OR_UNKNOWN;
            if (!mPhoneSignalScanningTimer.isRunningLocked()) {
                mHistoryCur.states |= HistoryItem.STATE_PHONE_SCANNING_FLAG;
                newHistory = true;
                if (DEBUG_HISTORY) Slog.v(TAG, "Phone started scanning to: "
                        + Integer.toHexString(mHistoryCur.states));
                mPhoneSignalScanningTimer.startRunningLocked(elapsedRealtime);
            }
        }

        if (!scanning) {
            // If we are no longer scanning, then stop the scanning timer.
            if (mPhoneSignalScanningTimer.isRunningLocked()) {
                mHistoryCur.states &= ~HistoryItem.STATE_PHONE_SCANNING_FLAG;
                if (DEBUG_HISTORY) Slog.v(TAG, "Phone stopped scanning to: "
                        + Integer.toHexString(mHistoryCur.states));
                newHistory = true;
                mPhoneSignalScanningTimer.stopRunningLocked(elapsedRealtime);
            }
        }

        if (mPhoneServiceState != state) {
            mHistoryCur.states = (mHistoryCur.states&~HistoryItem.STATE_PHONE_STATE_MASK)
                    | (state << HistoryItem.STATE_PHONE_STATE_SHIFT);
            if (DEBUG_HISTORY) Slog.v(TAG, "Phone state " + state + " to: "
                    + Integer.toHexString(mHistoryCur.states));
            newHistory = true;
            mPhoneServiceState = state;
        }

        if (mPhoneSignalStrengthBin != strengthBin) {
            if (mPhoneSignalStrengthBin >= 0) {
                mPhoneSignalStrengthsTimer[mPhoneSignalStrengthBin].stopRunningLocked(
                        elapsedRealtime);
            }
            if (strengthBin >= 0) {
                if (!mPhoneSignalStrengthsTimer[strengthBin].isRunningLocked()) {
                    mPhoneSignalStrengthsTimer[strengthBin].startRunningLocked(elapsedRealtime);
                }
                mHistoryCur.states = (mHistoryCur.states&~HistoryItem.STATE_PHONE_SIGNAL_STRENGTH_MASK)
                        | (strengthBin << HistoryItem.STATE_PHONE_SIGNAL_STRENGTH_SHIFT);
                if (DEBUG_HISTORY) Slog.v(TAG, "Signal strength " + strengthBin + " to: "
                        + Integer.toHexString(mHistoryCur.states));
                newHistory = true;
            } else {
                stopAllPhoneSignalStrengthTimersLocked(-1);
            }
            mPhoneSignalStrengthBin = strengthBin;
        }

        if (newHistory) {
            addHistoryRecordLocked(elapsedRealtime, uptime);
        }
    }

    /**
     * Telephony stack updates the phone state.
     * @param state phone state from ServiceState.getState()
     */
    public void notePhoneStateLocked(int state, int simState) {
        updateAllPhoneStateLocked(state, simState, mPhoneSignalStrengthBinRaw);
    }

    public void notePhoneSignalStrengthLocked(SignalStrength signalStrength) {
        // Bin the strength.
        int bin = signalStrength.getLevel();
        updateAllPhoneStateLocked(mPhoneServiceStateRaw, mPhoneSimStateRaw, bin);
    }

    public void notePhoneDataConnectionStateLocked(int dataType, boolean hasData) {
        int bin = DATA_CONNECTION_NONE;
        if (hasData) {
            switch (dataType) {
                case TelephonyManager.NETWORK_TYPE_EDGE:
                    bin = DATA_CONNECTION_EDGE;
                    break;
                case TelephonyManager.NETWORK_TYPE_GPRS:
                    bin = DATA_CONNECTION_GPRS;
                    break;
                case TelephonyManager.NETWORK_TYPE_UMTS:
                    bin = DATA_CONNECTION_UMTS;
                    break;
                case TelephonyManager.NETWORK_TYPE_CDMA:
                    bin = DATA_CONNECTION_CDMA;
                    break;
                case TelephonyManager.NETWORK_TYPE_EVDO_0:
                    bin = DATA_CONNECTION_EVDO_0;
                    break;
                case TelephonyManager.NETWORK_TYPE_EVDO_A:
                    bin = DATA_CONNECTION_EVDO_A;
                    break;
                case TelephonyManager.NETWORK_TYPE_1xRTT:
                    bin = DATA_CONNECTION_1xRTT;
                    break;
                case TelephonyManager.NETWORK_TYPE_HSDPA:
                    bin = DATA_CONNECTION_HSDPA;
                    break;
                case TelephonyManager.NETWORK_TYPE_HSUPA:
                    bin = DATA_CONNECTION_HSUPA;
                    break;
                case TelephonyManager.NETWORK_TYPE_HSPA:
                    bin = DATA_CONNECTION_HSPA;
                    break;
                case TelephonyManager.NETWORK_TYPE_IDEN:
                    bin = DATA_CONNECTION_IDEN;
                    break;
                case TelephonyManager.NETWORK_TYPE_EVDO_B:
                    bin = DATA_CONNECTION_EVDO_B;
                    break;
                case TelephonyManager.NETWORK_TYPE_LTE:
                    bin = DATA_CONNECTION_LTE;
                    break;
                case TelephonyManager.NETWORK_TYPE_EHRPD:
                    bin = DATA_CONNECTION_EHRPD;
                    break;
                case TelephonyManager.NETWORK_TYPE_HSPAP:
                    bin = DATA_CONNECTION_HSPAP;
                    break;
                default:
                    bin = DATA_CONNECTION_OTHER;
                    break;
            }
        }
        if (DEBUG) Log.i(TAG, "Phone Data Connection -> " + dataType + " = " + hasData);
        if (mPhoneDataConnectionType != bin) {
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            final long uptime = SystemClock.uptimeMillis();
            mHistoryCur.states = (mHistoryCur.states&~HistoryItem.STATE_DATA_CONNECTION_MASK)
                    | (bin << HistoryItem.STATE_DATA_CONNECTION_SHIFT);
            if (DEBUG_HISTORY) Slog.v(TAG, "Data connection " + bin + " to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
            if (mPhoneDataConnectionType >= 0) {
                mPhoneDataConnectionsTimer[mPhoneDataConnectionType].stopRunningLocked(
                        elapsedRealtime);
            }
            mPhoneDataConnectionType = bin;
            mPhoneDataConnectionsTimer[bin].startRunningLocked(elapsedRealtime);
        }
    }

    public void noteWifiOnLocked() {
        if (!mWifiOn) {
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            final long uptime = SystemClock.uptimeMillis();
            mHistoryCur.states2 |= HistoryItem.STATE2_WIFI_ON_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "WIFI on to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
            mWifiOn = true;
            mWifiOnTimer.startRunningLocked(elapsedRealtime);
        }
    }

    public void noteWifiOffLocked() {
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        if (mWifiOn) {
            mHistoryCur.states2 &= ~HistoryItem.STATE2_WIFI_ON_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "WIFI off to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
            mWifiOn = false;
            mWifiOnTimer.stopRunningLocked(elapsedRealtime);
        }
    }

    public void noteAudioOnLocked(int uid) {
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        if (mAudioOnNesting == 0) {
            mHistoryCur.states |= HistoryItem.STATE_AUDIO_ON_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "Audio on to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
            mAudioOnTimer.startRunningLocked(elapsedRealtime);
        }
        mAudioOnNesting++;
        getUidStatsLocked(uid).noteAudioTurnedOnLocked(elapsedRealtime);
    }

    public void noteAudioOffLocked(int uid) {
        if (mAudioOnNesting == 0) {
            return;
        }
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        if (--mAudioOnNesting == 0) {
            mHistoryCur.states &= ~HistoryItem.STATE_AUDIO_ON_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "Audio off to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
            mAudioOnTimer.stopRunningLocked(elapsedRealtime);
        }
        getUidStatsLocked(uid).noteAudioTurnedOffLocked(elapsedRealtime);
    }

    public void noteVideoOnLocked(int uid) {
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        if (mVideoOnNesting == 0) {
            mHistoryCur.states2 |= HistoryItem.STATE2_VIDEO_ON_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "Video on to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
            mVideoOnTimer.startRunningLocked(elapsedRealtime);
        }
        mVideoOnNesting++;
        getUidStatsLocked(uid).noteVideoTurnedOnLocked(elapsedRealtime);
    }

    public void noteVideoOffLocked(int uid) {
        if (mVideoOnNesting == 0) {
            return;
        }
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        if (--mVideoOnNesting == 0) {
            mHistoryCur.states2 &= ~HistoryItem.STATE2_VIDEO_ON_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "Video off to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
            mVideoOnTimer.stopRunningLocked(elapsedRealtime);
        }
        getUidStatsLocked(uid).noteVideoTurnedOffLocked(elapsedRealtime);
    }

    public void noteResetAudioLocked() {
        if (mAudioOnNesting > 0) {
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            final long uptime = SystemClock.uptimeMillis();
            mAudioOnNesting = 0;
            mHistoryCur.states &= ~HistoryItem.STATE_AUDIO_ON_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "Audio off to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
            mAudioOnTimer.stopAllRunningLocked(elapsedRealtime);
            for (int i=0; i<mUidStats.size(); i++) {
                BatteryStatsImpl.Uid uid = mUidStats.valueAt(i);
                uid.noteResetAudioLocked(elapsedRealtime);
            }
        }
    }

    public void noteResetVideoLocked() {
        if (mVideoOnNesting > 0) {
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            final long uptime = SystemClock.uptimeMillis();
            mAudioOnNesting = 0;
            mHistoryCur.states2 &= ~HistoryItem.STATE2_VIDEO_ON_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "Video off to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
            mVideoOnTimer.stopAllRunningLocked(elapsedRealtime);
            for (int i=0; i<mUidStats.size(); i++) {
                BatteryStatsImpl.Uid uid = mUidStats.valueAt(i);
                uid.noteResetVideoLocked(elapsedRealtime);
            }
        }
    }

    public void noteActivityResumedLocked(int uid) {
        uid = mapUid(uid);
        getUidStatsLocked(uid).noteActivityResumedLocked(SystemClock.elapsedRealtime());
    }

    public void noteActivityPausedLocked(int uid) {
        uid = mapUid(uid);
        getUidStatsLocked(uid).noteActivityPausedLocked(SystemClock.elapsedRealtime());
    }

    public void noteVibratorOnLocked(int uid, long durationMillis) {
        uid = mapUid(uid);
        getUidStatsLocked(uid).noteVibratorOnLocked(durationMillis);
    }

    public void noteVibratorOffLocked(int uid) {
        uid = mapUid(uid);
        getUidStatsLocked(uid).noteVibratorOffLocked();
    }

    public void noteFlashlightOnLocked() {
        if (!mFlashlightOn) {
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            final long uptime = SystemClock.uptimeMillis();
            mHistoryCur.states2 |= HistoryItem.STATE2_FLASHLIGHT_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "Flashlight on to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
            mFlashlightOn = true;
            mFlashlightOnTimer.startRunningLocked(elapsedRealtime);
        }
    }

    public void noteFlashlightOffLocked() {
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        if (mFlashlightOn) {
            mHistoryCur.states2 &= ~HistoryItem.STATE2_FLASHLIGHT_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "Flashlight off to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
            mFlashlightOn = false;
            mFlashlightOnTimer.stopRunningLocked(elapsedRealtime);
        }
    }

    public void noteWifiRunningLocked(WorkSource ws) {
        if (!mGlobalWifiRunning) {
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            final long uptime = SystemClock.uptimeMillis();
            mHistoryCur.states2 |= HistoryItem.STATE2_WIFI_RUNNING_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "WIFI running to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
            mGlobalWifiRunning = true;
            mGlobalWifiRunningTimer.startRunningLocked(elapsedRealtime);
            int N = ws.size();
            for (int i=0; i<N; i++) {
                int uid = mapUid(ws.get(i));
                getUidStatsLocked(uid).noteWifiRunningLocked(elapsedRealtime);
            }
        } else {
            Log.w(TAG, "noteWifiRunningLocked -- called while WIFI running");
        }
    }

    public void noteWifiRunningChangedLocked(WorkSource oldWs, WorkSource newWs) {
        if (mGlobalWifiRunning) {
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            int N = oldWs.size();
            for (int i=0; i<N; i++) {
                int uid = mapUid(oldWs.get(i));
                getUidStatsLocked(uid).noteWifiStoppedLocked(elapsedRealtime);
            }
            N = newWs.size();
            for (int i=0; i<N; i++) {
                int uid = mapUid(newWs.get(i));
                getUidStatsLocked(uid).noteWifiRunningLocked(elapsedRealtime);
            }
        } else {
            Log.w(TAG, "noteWifiRunningChangedLocked -- called while WIFI not running");
        }
    }

    public void noteWifiStoppedLocked(WorkSource ws) {
        if (mGlobalWifiRunning) {
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            final long uptime = SystemClock.uptimeMillis();
            mHistoryCur.states2 &= ~HistoryItem.STATE2_WIFI_RUNNING_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "WIFI stopped to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
            mGlobalWifiRunning = false;
            mGlobalWifiRunningTimer.stopRunningLocked(elapsedRealtime);
            int N = ws.size();
            for (int i=0; i<N; i++) {
                int uid = mapUid(ws.get(i));
                getUidStatsLocked(uid).noteWifiStoppedLocked(elapsedRealtime);
            }
        } else {
            Log.w(TAG, "noteWifiStoppedLocked -- called while WIFI not running");
        }
    }

    public void noteWifiStateLocked(int wifiState, String accessPoint) {
        if (DEBUG) Log.i(TAG, "WiFi state -> " + wifiState);
        if (mWifiState != wifiState) {
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            if (mWifiState >= 0) {
                mWifiStateTimer[mWifiState].stopRunningLocked(elapsedRealtime);
            }
            mWifiState = wifiState;
            mWifiStateTimer[wifiState].startRunningLocked(elapsedRealtime);
        }
    }

    public void noteWifiSupplicantStateChangedLocked(int supplState, boolean failedAuth) {
        if (DEBUG) Log.i(TAG, "WiFi suppl state -> " + supplState);
        if (mWifiSupplState != supplState) {
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            final long uptime = SystemClock.uptimeMillis();
            if (mWifiSupplState >= 0) {
                mWifiSupplStateTimer[mWifiSupplState].stopRunningLocked(elapsedRealtime);
            }
            mWifiSupplState = supplState;
            mWifiSupplStateTimer[supplState].startRunningLocked(elapsedRealtime);
            mHistoryCur.states2 =
                    (mHistoryCur.states2&~HistoryItem.STATE2_WIFI_SUPPL_STATE_MASK)
                    | (supplState << HistoryItem.STATE2_WIFI_SUPPL_STATE_SHIFT);
            if (DEBUG_HISTORY) Slog.v(TAG, "Wifi suppl state " + supplState + " to: "
                    + Integer.toHexString(mHistoryCur.states2));
            addHistoryRecordLocked(elapsedRealtime, uptime);
        }
    }

    void stopAllWifiSignalStrengthTimersLocked(int except) {
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        for (int i = 0; i < NUM_WIFI_SIGNAL_STRENGTH_BINS; i++) {
            if (i == except) {
                continue;
            }
            while (mWifiSignalStrengthsTimer[i].isRunningLocked()) {
                mWifiSignalStrengthsTimer[i].stopRunningLocked(elapsedRealtime);
            }
        }
    }

    public void noteWifiRssiChangedLocked(int newRssi) {
        int strengthBin = WifiManager.calculateSignalLevel(newRssi, NUM_WIFI_SIGNAL_STRENGTH_BINS);
        if (DEBUG) Log.i(TAG, "WiFi rssi -> " + newRssi + " bin=" + strengthBin);
        if (mWifiSignalStrengthBin != strengthBin) {
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            final long uptime = SystemClock.uptimeMillis();
            if (mWifiSignalStrengthBin >= 0) {
                mWifiSignalStrengthsTimer[mWifiSignalStrengthBin].stopRunningLocked(
                        elapsedRealtime);
            }
            if (strengthBin >= 0) {
                if (!mWifiSignalStrengthsTimer[strengthBin].isRunningLocked()) {
                    mWifiSignalStrengthsTimer[strengthBin].startRunningLocked(elapsedRealtime);
                }
                mHistoryCur.states2 =
                        (mHistoryCur.states2&~HistoryItem.STATE2_WIFI_SIGNAL_STRENGTH_MASK)
                        | (strengthBin << HistoryItem.STATE2_WIFI_SIGNAL_STRENGTH_SHIFT);
                if (DEBUG_HISTORY) Slog.v(TAG, "Wifi signal strength " + strengthBin + " to: "
                        + Integer.toHexString(mHistoryCur.states2));
                addHistoryRecordLocked(elapsedRealtime, uptime);
            } else {
                stopAllWifiSignalStrengthTimersLocked(-1);
            }
            mWifiSignalStrengthBin = strengthBin;
        }
    }

    public void noteBluetoothOnLocked() {
        if (!mBluetoothOn) {
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            final long uptime = SystemClock.uptimeMillis();
            mHistoryCur.states |= HistoryItem.STATE_BLUETOOTH_ON_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "Bluetooth on to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
            mBluetoothOn = true;
            mBluetoothOnTimer.startRunningLocked(elapsedRealtime);
        }
    }

    public void noteBluetoothOffLocked() {
        if (mBluetoothOn) {
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            final long uptime = SystemClock.uptimeMillis();
            mHistoryCur.states &= ~HistoryItem.STATE_BLUETOOTH_ON_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "Bluetooth off to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
            mBluetoothOn = false;
            mBluetoothOnTimer.stopRunningLocked(elapsedRealtime);
        }
    }

    public void noteBluetoothStateLocked(int bluetoothState) {
        if (DEBUG) Log.i(TAG, "Bluetooth state -> " + bluetoothState);
        if (mBluetoothState != bluetoothState) {
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            if (mBluetoothState >= 0) {
                mBluetoothStateTimer[mBluetoothState].stopRunningLocked(elapsedRealtime);
            }
            mBluetoothState = bluetoothState;
            mBluetoothStateTimer[bluetoothState].startRunningLocked(elapsedRealtime);
        }
    }

    int mWifiFullLockNesting = 0;

    public void noteFullWifiLockAcquiredLocked(int uid) {
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        if (mWifiFullLockNesting == 0) {
            mHistoryCur.states |= HistoryItem.STATE_WIFI_FULL_LOCK_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "WIFI full lock on to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
        }
        mWifiFullLockNesting++;
        getUidStatsLocked(uid).noteFullWifiLockAcquiredLocked(elapsedRealtime);
    }

    public void noteFullWifiLockReleasedLocked(int uid) {
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        mWifiFullLockNesting--;
        if (mWifiFullLockNesting == 0) {
            mHistoryCur.states &= ~HistoryItem.STATE_WIFI_FULL_LOCK_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "WIFI full lock off to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
        }
        getUidStatsLocked(uid).noteFullWifiLockReleasedLocked(elapsedRealtime);
    }

    int mWifiScanNesting = 0;

    public void noteWifiScanStartedLocked(int uid) {
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        if (mWifiScanNesting == 0) {
            mHistoryCur.states |= HistoryItem.STATE_WIFI_SCAN_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "WIFI scan started for: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
        }
        mWifiScanNesting++;
        getUidStatsLocked(uid).noteWifiScanStartedLocked(elapsedRealtime);
    }

    public void noteWifiScanStoppedLocked(int uid) {
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        mWifiScanNesting--;
        if (mWifiScanNesting == 0) {
            mHistoryCur.states &= ~HistoryItem.STATE_WIFI_SCAN_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "WIFI scan stopped for: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
        }
        getUidStatsLocked(uid).noteWifiScanStoppedLocked(elapsedRealtime);
    }

    public void noteWifiBatchedScanStartedLocked(int uid, int csph) {
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        getUidStatsLocked(uid).noteWifiBatchedScanStartedLocked(csph, elapsedRealtime);
    }

    public void noteWifiBatchedScanStoppedLocked(int uid) {
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        getUidStatsLocked(uid).noteWifiBatchedScanStoppedLocked(elapsedRealtime);
    }

    int mWifiMulticastNesting = 0;

    public void noteWifiMulticastEnabledLocked(int uid) {
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        if (mWifiMulticastNesting == 0) {
            mHistoryCur.states |= HistoryItem.STATE_WIFI_MULTICAST_ON_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "WIFI multicast on to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
        }
        mWifiMulticastNesting++;
        getUidStatsLocked(uid).noteWifiMulticastEnabledLocked(elapsedRealtime);
    }

    public void noteWifiMulticastDisabledLocked(int uid) {
        uid = mapUid(uid);
        final long elapsedRealtime = SystemClock.elapsedRealtime();
        final long uptime = SystemClock.uptimeMillis();
        mWifiMulticastNesting--;
        if (mWifiMulticastNesting == 0) {
            mHistoryCur.states &= ~HistoryItem.STATE_WIFI_MULTICAST_ON_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "WIFI multicast off to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(elapsedRealtime, uptime);
        }
        getUidStatsLocked(uid).noteWifiMulticastDisabledLocked(elapsedRealtime);
    }

    public void noteFullWifiLockAcquiredFromSourceLocked(WorkSource ws) {
        int N = ws.size();
        for (int i=0; i<N; i++) {
            noteFullWifiLockAcquiredLocked(ws.get(i));
        }
    }

    public void noteFullWifiLockReleasedFromSourceLocked(WorkSource ws) {
        int N = ws.size();
        for (int i=0; i<N; i++) {
            noteFullWifiLockReleasedLocked(ws.get(i));
        }
    }

    public void noteWifiScanStartedFromSourceLocked(WorkSource ws) {
        int N = ws.size();
        for (int i=0; i<N; i++) {
            noteWifiScanStartedLocked(ws.get(i));
        }
    }

    public void noteWifiScanStoppedFromSourceLocked(WorkSource ws) {
        int N = ws.size();
        for (int i=0; i<N; i++) {
            noteWifiScanStoppedLocked(ws.get(i));
        }
    }

    public void noteWifiBatchedScanStartedFromSourceLocked(WorkSource ws, int csph) {
        int N = ws.size();
        for (int i=0; i<N; i++) {
            noteWifiBatchedScanStartedLocked(ws.get(i), csph);
        }
    }

    public void noteWifiBatchedScanStoppedFromSourceLocked(WorkSource ws) {
        int N = ws.size();
        for (int i=0; i<N; i++) {
            noteWifiBatchedScanStoppedLocked(ws.get(i));
        }
    }

    public void noteWifiMulticastEnabledFromSourceLocked(WorkSource ws) {
        int N = ws.size();
        for (int i=0; i<N; i++) {
            noteWifiMulticastEnabledLocked(ws.get(i));
        }
    }

    public void noteWifiMulticastDisabledFromSourceLocked(WorkSource ws) {
        int N = ws.size();
        for (int i=0; i<N; i++) {
            noteWifiMulticastDisabledLocked(ws.get(i));
        }
    }

    private static String[] includeInStringArray(String[] array, String str) {
        if (ArrayUtils.indexOf(array, str) >= 0) {
            return array;
        }
        String[] newArray = new String[array.length+1];
        System.arraycopy(array, 0, newArray, 0, array.length);
        newArray[array.length] = str;
        return newArray;
    }

    private static String[] excludeFromStringArray(String[] array, String str) {
        int index = ArrayUtils.indexOf(array, str);
        if (index >= 0) {
            String[] newArray = new String[array.length-1];
            if (index > 0) {
                System.arraycopy(array, 0, newArray, 0, index);
            }
            if (index < array.length-1) {
                System.arraycopy(array, index+1, newArray, index, array.length-index-1);
            }
            return newArray;
        }
        return array;
    }

    public void noteNetworkInterfaceTypeLocked(String iface, int networkType) {
        if (TextUtils.isEmpty(iface)) return;
        if (ConnectivityManager.isNetworkTypeMobile(networkType)) {
            mMobileIfaces = includeInStringArray(mMobileIfaces, iface);
            if (DEBUG) Slog.d(TAG, "Note mobile iface " + iface + ": " + mMobileIfaces);
        } else {
            mMobileIfaces = excludeFromStringArray(mMobileIfaces, iface);
            if (DEBUG) Slog.d(TAG, "Note non-mobile iface " + iface + ": " + mMobileIfaces);
        }
        if (ConnectivityManager.isNetworkTypeWifi(networkType)) {
            mWifiIfaces = includeInStringArray(mWifiIfaces, iface);
            if (DEBUG) Slog.d(TAG, "Note wifi iface " + iface + ": " + mWifiIfaces);
        } else {
            mWifiIfaces = excludeFromStringArray(mWifiIfaces, iface);
            if (DEBUG) Slog.d(TAG, "Note non-wifi iface " + iface + ": " + mWifiIfaces);
        }
    }

    public void noteNetworkStatsEnabledLocked() {
        // During device boot, qtaguid isn't enabled until after the inital
        // loading of battery stats. Now that they're enabled, take our initial
        // snapshot for future delta calculation.
        updateNetworkActivityLocked(NET_UPDATE_ALL, SystemClock.elapsedRealtime());
    }

    @Override public long getScreenOnTime(long elapsedRealtimeUs, int which) {
        return mScreenOnTimer.getTotalTimeLocked(elapsedRealtimeUs, which);
    }

    @Override public int getScreenOnCount(int which) {
        return mScreenOnTimer.getCountLocked(which);
    }

    @Override public long getScreenBrightnessTime(int brightnessBin,
            long elapsedRealtimeUs, int which) {
        return mScreenBrightnessTimer[brightnessBin].getTotalTimeLocked(
                elapsedRealtimeUs, which);
    }

    @Override public long getInteractiveTime(long elapsedRealtimeUs, int which) {
        return mInteractiveTimer.getTotalTimeLocked(elapsedRealtimeUs, which);
    }

    @Override public long getLowPowerModeEnabledTime(long elapsedRealtimeUs, int which) {
        return mLowPowerModeEnabledTimer.getTotalTimeLocked(elapsedRealtimeUs, which);
    }

    @Override public int getLowPowerModeEnabledCount(int which) {
        return mLowPowerModeEnabledTimer.getCountLocked(which);
    }

    @Override public int getNumConnectivityChange(int which) {
        int val = mNumConnectivityChange;
        if (which == STATS_CURRENT) {
            val -= mLoadedNumConnectivityChange;
        } else if (which == STATS_SINCE_UNPLUGGED) {
            val -= mUnpluggedNumConnectivityChange;
        }
        return val;
    }

    @Override public long getPhoneOnTime(long elapsedRealtimeUs, int which) {
        return mPhoneOnTimer.getTotalTimeLocked(elapsedRealtimeUs, which);
    }

    @Override public int getPhoneOnCount(int which) {
        return mPhoneOnTimer.getCountLocked(which);
    }

    @Override public long getPhoneSignalStrengthTime(int strengthBin,
            long elapsedRealtimeUs, int which) {
        return mPhoneSignalStrengthsTimer[strengthBin].getTotalTimeLocked(
                elapsedRealtimeUs, which);
    }

    @Override public long getPhoneSignalScanningTime(
            long elapsedRealtimeUs, int which) {
        return mPhoneSignalScanningTimer.getTotalTimeLocked(
                elapsedRealtimeUs, which);
    }

    @Override public int getPhoneSignalStrengthCount(int strengthBin, int which) {
        return mPhoneSignalStrengthsTimer[strengthBin].getCountLocked(which);
    }

    @Override public long getPhoneDataConnectionTime(int dataType,
            long elapsedRealtimeUs, int which) {
        return mPhoneDataConnectionsTimer[dataType].getTotalTimeLocked(
                elapsedRealtimeUs, which);
    }

    @Override public int getPhoneDataConnectionCount(int dataType, int which) {
        return mPhoneDataConnectionsTimer[dataType].getCountLocked(which);
    }

    @Override public long getMobileRadioActiveTime(long elapsedRealtimeUs, int which) {
        return mMobileRadioActiveTimer.getTotalTimeLocked(elapsedRealtimeUs, which);
    }

    @Override public int getMobileRadioActiveCount(int which) {
        return mMobileRadioActiveTimer.getCountLocked(which);
    }

    @Override public long getMobileRadioActiveAdjustedTime(int which) {
        return mMobileRadioActiveAdjustedTime.getCountLocked(which);
    }

    @Override public long getMobileRadioActiveUnknownTime(int which) {
        return mMobileRadioActiveUnknownTime.getCountLocked(which);
    }

    @Override public int getMobileRadioActiveUnknownCount(int which) {
        return (int)mMobileRadioActiveUnknownCount.getCountLocked(which);
    }

    @Override public long getWifiOnTime(long elapsedRealtimeUs, int which) {
        return mWifiOnTimer.getTotalTimeLocked(elapsedRealtimeUs, which);
    }

    @Override public long getGlobalWifiRunningTime(long elapsedRealtimeUs, int which) {
        return mGlobalWifiRunningTimer.getTotalTimeLocked(elapsedRealtimeUs, which);
    }

    @Override public long getWifiStateTime(int wifiState,
            long elapsedRealtimeUs, int which) {
        return mWifiStateTimer[wifiState].getTotalTimeLocked(
                elapsedRealtimeUs, which);
    }

    @Override public int getWifiStateCount(int wifiState, int which) {
        return mWifiStateTimer[wifiState].getCountLocked(which);
    }

    @Override public long getWifiSupplStateTime(int state,
            long elapsedRealtimeUs, int which) {
        return mWifiSupplStateTimer[state].getTotalTimeLocked(
                elapsedRealtimeUs, which);
    }

    @Override public int getWifiSupplStateCount(int state, int which) {
        return mWifiSupplStateTimer[state].getCountLocked(which);
    }

    @Override public long getWifiSignalStrengthTime(int strengthBin,
            long elapsedRealtimeUs, int which) {
        return mWifiSignalStrengthsTimer[strengthBin].getTotalTimeLocked(
                elapsedRealtimeUs, which);
    }

    @Override public int getWifiSignalStrengthCount(int strengthBin, int which) {
        return mWifiSignalStrengthsTimer[strengthBin].getCountLocked(which);
    }

    @Override public long getBluetoothOnTime(long elapsedRealtimeUs, int which) {
        return mBluetoothOnTimer.getTotalTimeLocked(elapsedRealtimeUs, which);
    }

    @Override public long getBluetoothStateTime(int bluetoothState,
            long elapsedRealtimeUs, int which) {
        return mBluetoothStateTimer[bluetoothState].getTotalTimeLocked(
                elapsedRealtimeUs, which);
    }

    @Override public int getBluetoothStateCount(int bluetoothState, int which) {
        return mBluetoothStateTimer[bluetoothState].getCountLocked(which);
    }

    @Override public long getFlashlightOnTime(long elapsedRealtimeUs, int which) {
        return mFlashlightOnTimer.getTotalTimeLocked(elapsedRealtimeUs, which);
    }

    @Override public long getFlashlightOnCount(int which) {
        return mFlashlightOnTimer.getCountLocked(which);
    }

    @Override
    public long getNetworkActivityBytes(int type, int which) {
        if (type >= 0 && type < mNetworkByteActivityCounters.length) {
            return mNetworkByteActivityCounters[type].getCountLocked(which);
        } else {
            return 0;
        }
    }

    @Override
    public long getNetworkActivityPackets(int type, int which) {
        if (type >= 0 && type < mNetworkPacketActivityCounters.length) {
            return mNetworkPacketActivityCounters[type].getCountLocked(which);
        } else {
            return 0;
        }
    }

    boolean isStartClockTimeValid() {
        return mStartClockTime > 365*24*60*60*1000L;
    }

    @Override public long getStartClockTime() {
        if (!isStartClockTimeValid()) {
            // If the last clock time we got was very small, then we hadn't had a real
            // time yet, so try to get it again.
            mStartClockTime = System.currentTimeMillis();
            if (isStartClockTimeValid()) {
                recordCurrentTimeChangeLocked(mStartClockTime, SystemClock.elapsedRealtime(),
                        SystemClock.uptimeMillis());
            }
        }
        return mStartClockTime;
    }

    @Override public String getStartPlatformVersion() {
        return mStartPlatformVersion;
    }

    @Override public String getEndPlatformVersion() {
        return mEndPlatformVersion;
    }

    @Override public int getParcelVersion() {
        return VERSION;
    }

    @Override public boolean getIsOnBattery() {
        return mOnBattery;
    }

    @Override public SparseArray<? extends BatteryStats.Uid> getUidStats() {
        return mUidStats;
    }

    /**
     * The statistics associated with a particular uid.
     */
    public final class Uid extends BatteryStats.Uid {

        final int mUid;

        boolean mWifiRunning;
        StopwatchTimer mWifiRunningTimer;

        boolean mFullWifiLockOut;
        StopwatchTimer mFullWifiLockTimer;

        boolean mWifiScanStarted;
        StopwatchTimer mWifiScanTimer;

        static final int NO_BATCHED_SCAN_STARTED = -1;
        int mWifiBatchedScanBinStarted = NO_BATCHED_SCAN_STARTED;
        StopwatchTimer[] mWifiBatchedScanTimer;

        boolean mWifiMulticastEnabled;
        StopwatchTimer mWifiMulticastTimer;

        StopwatchTimer mAudioTurnedOnTimer;
        StopwatchTimer mVideoTurnedOnTimer;

        StopwatchTimer mForegroundActivityTimer;

        static final int PROCESS_STATE_NONE = NUM_PROCESS_STATE;
        int mProcessState = PROCESS_STATE_NONE;
        StopwatchTimer[] mProcessStateTimer;

        BatchTimer mVibratorOnTimer;

        Counter[] mUserActivityCounters;

        LongSamplingCounter[] mNetworkByteActivityCounters;
        LongSamplingCounter[] mNetworkPacketActivityCounters;
        LongSamplingCounter mMobileRadioActiveTime;
        LongSamplingCounter mMobileRadioActiveCount;

        /**
         * The statistics we have collected for this uid's wake locks.
         */
        final OverflowArrayMap<Wakelock> mWakelockStats = new OverflowArrayMap<Wakelock>() {
            @Override public Wakelock instantiateObject() { return new Wakelock(); }
        };

        /**
         * The statistics we have collected for this uid's syncs.
         */
        final OverflowArrayMap<StopwatchTimer> mSyncStats = new OverflowArrayMap<StopwatchTimer>() {
            @Override public StopwatchTimer instantiateObject() {
                return new StopwatchTimer(Uid.this, SYNC, null, mOnBatteryTimeBase);
            }
        };

        /**
         * The statistics we have collected for this uid's jobs.
         */
        final OverflowArrayMap<StopwatchTimer> mJobStats = new OverflowArrayMap<StopwatchTimer>() {
            @Override public StopwatchTimer instantiateObject() {
                return new StopwatchTimer(Uid.this, JOB, null, mOnBatteryTimeBase);
            }
        };

        /**
         * The statistics we have collected for this uid's sensor activations.
         */
        final SparseArray<Sensor> mSensorStats = new SparseArray<Sensor>();

        /**
         * The statistics we have collected for this uid's processes.
         */
        final ArrayMap<String, Proc> mProcessStats = new ArrayMap<String, Proc>();

        /**
         * The statistics we have collected for this uid's processes.
         */
        final ArrayMap<String, Pkg> mPackageStats = new ArrayMap<String, Pkg>();

        /**
         * The transient wake stats we have collected for this uid's pids.
         */
        final SparseArray<Pid> mPids = new SparseArray<Pid>();

        public Uid(int uid) {
            mUid = uid;
            mWifiRunningTimer = new StopwatchTimer(Uid.this, WIFI_RUNNING,
                    mWifiRunningTimers, mOnBatteryTimeBase);
            mFullWifiLockTimer = new StopwatchTimer(Uid.this, FULL_WIFI_LOCK,
                    mFullWifiLockTimers, mOnBatteryTimeBase);
            mWifiScanTimer = new StopwatchTimer(Uid.this, WIFI_SCAN,
                    mWifiScanTimers, mOnBatteryTimeBase);
            mWifiBatchedScanTimer = new StopwatchTimer[NUM_WIFI_BATCHED_SCAN_BINS];
            mWifiMulticastTimer = new StopwatchTimer(Uid.this, WIFI_MULTICAST_ENABLED,
                    mWifiMulticastTimers, mOnBatteryTimeBase);
            mProcessStateTimer = new StopwatchTimer[NUM_PROCESS_STATE];
        }

        @Override
        public Map<String, ? extends BatteryStats.Uid.Wakelock> getWakelockStats() {
            return mWakelockStats.getMap();
        }

        @Override
        public Map<String, ? extends BatteryStats.Timer> getSyncStats() {
            return mSyncStats.getMap();
        }

        @Override
        public Map<String, ? extends BatteryStats.Timer> getJobStats() {
            return mJobStats.getMap();
        }

        @Override
        public SparseArray<? extends BatteryStats.Uid.Sensor> getSensorStats() {
            return mSensorStats;
        }

        @Override
        public Map<String, ? extends BatteryStats.Uid.Proc> getProcessStats() {
            return mProcessStats;
        }

        @Override
        public Map<String, ? extends BatteryStats.Uid.Pkg> getPackageStats() {
            return mPackageStats;
        }

        @Override
        public int getUid() {
            return mUid;
        }

        @Override
        public void noteWifiRunningLocked(long elapsedRealtimeMs) {
            if (!mWifiRunning) {
                mWifiRunning = true;
                if (mWifiRunningTimer == null) {
                    mWifiRunningTimer = new StopwatchTimer(Uid.this, WIFI_RUNNING,
                            mWifiRunningTimers, mOnBatteryTimeBase);
                }
                mWifiRunningTimer.startRunningLocked(elapsedRealtimeMs);
            }
        }

        @Override
        public void noteWifiStoppedLocked(long elapsedRealtimeMs) {
            if (mWifiRunning) {
                mWifiRunning = false;
                mWifiRunningTimer.stopRunningLocked(elapsedRealtimeMs);
            }
        }

        @Override
        public void noteFullWifiLockAcquiredLocked(long elapsedRealtimeMs) {
            if (!mFullWifiLockOut) {
                mFullWifiLockOut = true;
                if (mFullWifiLockTimer == null) {
                    mFullWifiLockTimer = new StopwatchTimer(Uid.this, FULL_WIFI_LOCK,
                            mFullWifiLockTimers, mOnBatteryTimeBase);
                }
                mFullWifiLockTimer.startRunningLocked(elapsedRealtimeMs);
            }
        }

        @Override
        public void noteFullWifiLockReleasedLocked(long elapsedRealtimeMs) {
            if (mFullWifiLockOut) {
                mFullWifiLockOut = false;
                mFullWifiLockTimer.stopRunningLocked(elapsedRealtimeMs);
            }
        }

        @Override
        public void noteWifiScanStartedLocked(long elapsedRealtimeMs) {
            if (!mWifiScanStarted) {
                mWifiScanStarted = true;
                if (mWifiScanTimer == null) {
                    mWifiScanTimer = new StopwatchTimer(Uid.this, WIFI_SCAN,
                            mWifiScanTimers, mOnBatteryTimeBase);
                }
                mWifiScanTimer.startRunningLocked(elapsedRealtimeMs);
            }
        }

        @Override
        public void noteWifiScanStoppedLocked(long elapsedRealtimeMs) {
            if (mWifiScanStarted) {
                mWifiScanStarted = false;
                mWifiScanTimer.stopRunningLocked(elapsedRealtimeMs);
            }
        }

        @Override
        public void noteWifiBatchedScanStartedLocked(int csph, long elapsedRealtimeMs) {
            int bin = 0;
            while (csph > 8 && bin < NUM_WIFI_BATCHED_SCAN_BINS) {
                csph = csph >> 3;
                bin++;
            }

            if (mWifiBatchedScanBinStarted == bin) return;

            if (mWifiBatchedScanBinStarted != NO_BATCHED_SCAN_STARTED) {
                mWifiBatchedScanTimer[mWifiBatchedScanBinStarted].
                        stopRunningLocked(elapsedRealtimeMs);
            }
            mWifiBatchedScanBinStarted = bin;
            if (mWifiBatchedScanTimer[bin] == null) {
                makeWifiBatchedScanBin(bin, null);
            }
            mWifiBatchedScanTimer[bin].startRunningLocked(elapsedRealtimeMs);
        }

        @Override
        public void noteWifiBatchedScanStoppedLocked(long elapsedRealtimeMs) {
            if (mWifiBatchedScanBinStarted != NO_BATCHED_SCAN_STARTED) {
                mWifiBatchedScanTimer[mWifiBatchedScanBinStarted].
                        stopRunningLocked(elapsedRealtimeMs);
                mWifiBatchedScanBinStarted = NO_BATCHED_SCAN_STARTED;
            }
        }

        @Override
        public void noteWifiMulticastEnabledLocked(long elapsedRealtimeMs) {
            if (!mWifiMulticastEnabled) {
                mWifiMulticastEnabled = true;
                if (mWifiMulticastTimer == null) {
                    mWifiMulticastTimer = new StopwatchTimer(Uid.this, WIFI_MULTICAST_ENABLED,
                            mWifiMulticastTimers, mOnBatteryTimeBase);
                }
                mWifiMulticastTimer.startRunningLocked(elapsedRealtimeMs);
            }
        }

        @Override
        public void noteWifiMulticastDisabledLocked(long elapsedRealtimeMs) {
            if (mWifiMulticastEnabled) {
                mWifiMulticastEnabled = false;
                mWifiMulticastTimer.stopRunningLocked(elapsedRealtimeMs);
            }
        }

        public StopwatchTimer createAudioTurnedOnTimerLocked() {
            if (mAudioTurnedOnTimer == null) {
                mAudioTurnedOnTimer = new StopwatchTimer(Uid.this, AUDIO_TURNED_ON,
                        mAudioTurnedOnTimers, mOnBatteryTimeBase);
            }
            return mAudioTurnedOnTimer;
        }

        public void noteAudioTurnedOnLocked(long elapsedRealtimeMs) {
            createAudioTurnedOnTimerLocked().startRunningLocked(elapsedRealtimeMs);
        }

        public void noteAudioTurnedOffLocked(long elapsedRealtimeMs) {
            if (mAudioTurnedOnTimer != null) {
                mAudioTurnedOnTimer.stopRunningLocked(elapsedRealtimeMs);
            }
        }

        public void noteResetAudioLocked(long elapsedRealtimeMs) {
            if (mAudioTurnedOnTimer != null) {
                mAudioTurnedOnTimer.stopAllRunningLocked(elapsedRealtimeMs);
            }
        }

        public StopwatchTimer createVideoTurnedOnTimerLocked() {
            if (mVideoTurnedOnTimer == null) {
                mVideoTurnedOnTimer = new StopwatchTimer(Uid.this, VIDEO_TURNED_ON,
                        mVideoTurnedOnTimers, mOnBatteryTimeBase);
            }
            return mVideoTurnedOnTimer;
        }

        public void noteVideoTurnedOnLocked(long elapsedRealtimeMs) {
            createVideoTurnedOnTimerLocked().startRunningLocked(elapsedRealtimeMs);
        }

        public void noteVideoTurnedOffLocked(long elapsedRealtimeMs) {
            if (mVideoTurnedOnTimer != null) {
                mVideoTurnedOnTimer.stopRunningLocked(elapsedRealtimeMs);
            }
        }

        public void noteResetVideoLocked(long elapsedRealtimeMs) {
            if (mVideoTurnedOnTimer != null) {
                mVideoTurnedOnTimer.stopAllRunningLocked(elapsedRealtimeMs);
            }
        }

        public StopwatchTimer createForegroundActivityTimerLocked() {
            if (mForegroundActivityTimer == null) {
                mForegroundActivityTimer = new StopwatchTimer(
                        Uid.this, FOREGROUND_ACTIVITY, null, mOnBatteryTimeBase);
            }
            return mForegroundActivityTimer;
        }

        @Override
        public void noteActivityResumedLocked(long elapsedRealtimeMs) {
            // We always start, since we want multiple foreground PIDs to nest
            createForegroundActivityTimerLocked().startRunningLocked(elapsedRealtimeMs);
        }

        @Override
        public void noteActivityPausedLocked(long elapsedRealtimeMs) {
            if (mForegroundActivityTimer != null) {
                mForegroundActivityTimer.stopRunningLocked(elapsedRealtimeMs);
            }
        }

        void updateUidProcessStateLocked(int state, long elapsedRealtimeMs) {
            if (mProcessState == state) return;

            if (mProcessState != PROCESS_STATE_NONE) {
                mProcessStateTimer[mProcessState].stopRunningLocked(elapsedRealtimeMs);
            }
            mProcessState = state;
            if (state != PROCESS_STATE_NONE) {
                if (mProcessStateTimer[state] == null) {
                    makeProcessState(state, null);
                }
                mProcessStateTimer[state].startRunningLocked(elapsedRealtimeMs);
            }
        }

        public BatchTimer createVibratorOnTimerLocked() {
            if (mVibratorOnTimer == null) {
                mVibratorOnTimer = new BatchTimer(Uid.this, VIBRATOR_ON, mOnBatteryTimeBase);
            }
            return mVibratorOnTimer;
        }

        public void noteVibratorOnLocked(long durationMillis) {
            createVibratorOnTimerLocked().addDuration(BatteryStatsImpl.this, durationMillis);
        }

        public void noteVibratorOffLocked() {
            if (mVibratorOnTimer != null) {
                mVibratorOnTimer.abortLastDuration(BatteryStatsImpl.this);
            }
        }

        @Override
        public long getWifiRunningTime(long elapsedRealtimeUs, int which) {
            if (mWifiRunningTimer == null) {
                return 0;
            }
            return mWifiRunningTimer.getTotalTimeLocked(elapsedRealtimeUs, which);
        }

        @Override
        public long getFullWifiLockTime(long elapsedRealtimeUs, int which) {
            if (mFullWifiLockTimer == null) {
                return 0;
            }
            return mFullWifiLockTimer.getTotalTimeLocked(elapsedRealtimeUs, which);
        }

        @Override
        public long getWifiScanTime(long elapsedRealtimeUs, int which) {
            if (mWifiScanTimer == null) {
                return 0;
            }
            return mWifiScanTimer.getTotalTimeLocked(elapsedRealtimeUs, which);
        }

        @Override
        public long getWifiBatchedScanTime(int csphBin, long elapsedRealtimeUs, int which) {
            if (csphBin < 0 || csphBin >= NUM_WIFI_BATCHED_SCAN_BINS) return 0;
            if (mWifiBatchedScanTimer[csphBin] == null) {
                return 0;
            }
            return mWifiBatchedScanTimer[csphBin].getTotalTimeLocked(elapsedRealtimeUs, which);
        }

        @Override
        public long getWifiMulticastTime(long elapsedRealtimeUs, int which) {
            if (mWifiMulticastTimer == null) {
                return 0;
            }
            return mWifiMulticastTimer.getTotalTimeLocked(elapsedRealtimeUs, which);
        }

        @Override
        public long getAudioTurnedOnTime(long elapsedRealtimeUs, int which) {
            if (mAudioTurnedOnTimer == null) {
                return 0;
            }
            return mAudioTurnedOnTimer.getTotalTimeLocked(elapsedRealtimeUs, which);
        }

        @Override
        public long getVideoTurnedOnTime(long elapsedRealtimeUs, int which) {
            if (mVideoTurnedOnTimer == null) {
                return 0;
            }
            return mVideoTurnedOnTimer.getTotalTimeLocked(elapsedRealtimeUs, which);
        }

        @Override
        public Timer getForegroundActivityTimer() {
            return mForegroundActivityTimer;
        }

        void makeProcessState(int i, Parcel in) {
            if (i < 0 || i >= NUM_PROCESS_STATE) return;

            if (in == null) {
                mProcessStateTimer[i] = new StopwatchTimer(this, PROCESS_STATE, null,
                        mOnBatteryTimeBase);
            } else {
                mProcessStateTimer[i] = new StopwatchTimer(this, PROCESS_STATE, null,
                        mOnBatteryTimeBase, in);
            }
        }

        @Override
        public long getProcessStateTime(int state, long elapsedRealtimeUs, int which) {
            if (state < 0 || state >= NUM_PROCESS_STATE) return 0;
            if (mProcessStateTimer[state] == null) {
                return 0;
            }
            return mProcessStateTimer[state].getTotalTimeLocked(elapsedRealtimeUs, which);
        }

        @Override
        public Timer getVibratorOnTimer() {
            return mVibratorOnTimer;
        }

        @Override
        public void noteUserActivityLocked(int type) {
            if (mUserActivityCounters == null) {
                initUserActivityLocked();
            }
            if (type >= 0 && type < NUM_USER_ACTIVITY_TYPES) {
                mUserActivityCounters[type].stepAtomic();
            } else {
                Slog.w(TAG, "Unknown user activity type " + type + " was specified.",
                        new Throwable());
            }
        }

        @Override
        public boolean hasUserActivity() {
            return mUserActivityCounters != null;
        }

        @Override
        public int getUserActivityCount(int type, int which) {
            if (mUserActivityCounters == null) {
                return 0;
            }
            return mUserActivityCounters[type].getCountLocked(which);
        }

        void makeWifiBatchedScanBin(int i, Parcel in) {
            if (i < 0 || i >= NUM_WIFI_BATCHED_SCAN_BINS) return;

            ArrayList<StopwatchTimer> collected = mWifiBatchedScanTimers.get(i);
            if (collected == null) {
                collected = new ArrayList<StopwatchTimer>();
                mWifiBatchedScanTimers.put(i, collected);
            }
            if (in == null) {
                mWifiBatchedScanTimer[i] = new StopwatchTimer(this, WIFI_BATCHED_SCAN, collected,
                        mOnBatteryTimeBase);
            } else {
                mWifiBatchedScanTimer[i] = new StopwatchTimer(this, WIFI_BATCHED_SCAN, collected,
                        mOnBatteryTimeBase, in);
            }
        }


        void initUserActivityLocked() {
            mUserActivityCounters = new Counter[NUM_USER_ACTIVITY_TYPES];
            for (int i=0; i<NUM_USER_ACTIVITY_TYPES; i++) {
                mUserActivityCounters[i] = new Counter(mOnBatteryTimeBase);
            }
        }

        void noteNetworkActivityLocked(int type, long deltaBytes, long deltaPackets) {
            if (mNetworkByteActivityCounters == null) {
                initNetworkActivityLocked();
            }
            if (type >= 0 && type < NUM_NETWORK_ACTIVITY_TYPES) {
                mNetworkByteActivityCounters[type].addCountLocked(deltaBytes);
                mNetworkPacketActivityCounters[type].addCountLocked(deltaPackets);
            } else {
                Slog.w(TAG, "Unknown network activity type " + type + " was specified.",
                        new Throwable());
            }
        }

        void noteMobileRadioActiveTimeLocked(long batteryUptime) {
            if (mNetworkByteActivityCounters == null) {
                initNetworkActivityLocked();
            }
            mMobileRadioActiveTime.addCountLocked(batteryUptime);
            mMobileRadioActiveCount.addCountLocked(1);
        }

        @Override
        public boolean hasNetworkActivity() {
            return mNetworkByteActivityCounters != null;
        }

        @Override
        public long getNetworkActivityBytes(int type, int which) {
            if (mNetworkByteActivityCounters != null && type >= 0
                    && type < mNetworkByteActivityCounters.length) {
                return mNetworkByteActivityCounters[type].getCountLocked(which);
            } else {
                return 0;
            }
        }

        @Override
        public long getNetworkActivityPackets(int type, int which) {
            if (mNetworkPacketActivityCounters != null && type >= 0
                    && type < mNetworkPacketActivityCounters.length) {
                return mNetworkPacketActivityCounters[type].getCountLocked(which);
            } else {
                return 0;
            }
        }

        @Override
        public long getMobileRadioActiveTime(int which) {
            return mMobileRadioActiveTime != null
                    ? mMobileRadioActiveTime.getCountLocked(which) : 0;
        }

        @Override
        public int getMobileRadioActiveCount(int which) {
            return mMobileRadioActiveCount != null
                    ? (int)mMobileRadioActiveCount.getCountLocked(which) : 0;
        }

        void initNetworkActivityLocked() {
            mNetworkByteActivityCounters = new LongSamplingCounter[NUM_NETWORK_ACTIVITY_TYPES];
            mNetworkPacketActivityCounters = new LongSamplingCounter[NUM_NETWORK_ACTIVITY_TYPES];
            for (int i = 0; i < NUM_NETWORK_ACTIVITY_TYPES; i++) {
                mNetworkByteActivityCounters[i] = new LongSamplingCounter(mOnBatteryTimeBase);
                mNetworkPacketActivityCounters[i] = new LongSamplingCounter(mOnBatteryTimeBase);
            }
            mMobileRadioActiveTime = new LongSamplingCounter(mOnBatteryTimeBase);
            mMobileRadioActiveCount = new LongSamplingCounter(mOnBatteryTimeBase);
        }

        /**
         * Clear all stats for this uid.  Returns true if the uid is completely
         * inactive so can be dropped.
         */
        boolean reset() {
            boolean active = false;

            if (mWifiRunningTimer != null) {
                active |= !mWifiRunningTimer.reset(false);
                active |= mWifiRunning;
            }
            if (mFullWifiLockTimer != null) {
                active |= !mFullWifiLockTimer.reset(false);
                active |= mFullWifiLockOut;
            }
            if (mWifiScanTimer != null) {
                active |= !mWifiScanTimer.reset(false);
                active |= mWifiScanStarted;
            }
            if (mWifiBatchedScanTimer != null) {
                for (int i = 0; i < NUM_WIFI_BATCHED_SCAN_BINS; i++) {
                    if (mWifiBatchedScanTimer[i] != null) {
                        active |= !mWifiBatchedScanTimer[i].reset(false);
                    }
                }
                active |= (mWifiBatchedScanBinStarted != NO_BATCHED_SCAN_STARTED);
            }
            if (mWifiMulticastTimer != null) {
                active |= !mWifiMulticastTimer.reset(false);
                active |= mWifiMulticastEnabled;
            }
            if (mAudioTurnedOnTimer != null) {
                active |= !mAudioTurnedOnTimer.reset(false);
            }
            if (mVideoTurnedOnTimer != null) {
                active |= !mVideoTurnedOnTimer.reset(false);
            }
            if (mForegroundActivityTimer != null) {
                active |= !mForegroundActivityTimer.reset(false);
            }
            if (mProcessStateTimer != null) {
                for (int i = 0; i < NUM_PROCESS_STATE; i++) {
                    if (mProcessStateTimer[i] != null) {
                        active |= !mProcessStateTimer[i].reset(false);
                    }
                }
                active |= (mProcessState != PROCESS_STATE_NONE);
            }
            if (mVibratorOnTimer != null) {
                if (mVibratorOnTimer.reset(false)) {
                    mVibratorOnTimer.detach();
                    mVibratorOnTimer = null;
                } else {
                    active = true;
                }
            }

            if (mUserActivityCounters != null) {
                for (int i=0; i<NUM_USER_ACTIVITY_TYPES; i++) {
                    mUserActivityCounters[i].reset(false);
                }
            }

            if (mNetworkByteActivityCounters != null) {
                for (int i = 0; i < NUM_NETWORK_ACTIVITY_TYPES; i++) {
                    mNetworkByteActivityCounters[i].reset(false);
                    mNetworkPacketActivityCounters[i].reset(false);
                }
                mMobileRadioActiveTime.reset(false);
                mMobileRadioActiveCount.reset(false);
            }

            final ArrayMap<String, Wakelock> wakeStats = mWakelockStats.getMap();
            for (int iw=wakeStats.size()-1; iw>=0; iw--) {
                Wakelock wl = wakeStats.valueAt(iw);
                if (wl.reset()) {
                    wakeStats.removeAt(iw);
                } else {
                    active = true;
                }
            }
            mWakelockStats.cleanup();
            final ArrayMap<String, StopwatchTimer> syncStats = mSyncStats.getMap();
            for (int is=syncStats.size()-1; is>=0; is--) {
                StopwatchTimer timer = syncStats.valueAt(is);
                if (timer.reset(false)) {
                    syncStats.removeAt(is);
                    timer.detach();
                } else {
                    active = true;
                }
            }
            mSyncStats.cleanup();
            final ArrayMap<String, StopwatchTimer> jobStats = mJobStats.getMap();
            for (int ij=jobStats.size()-1; ij>=0; ij--) {
                StopwatchTimer timer = jobStats.valueAt(ij);
                if (timer.reset(false)) {
                    jobStats.removeAt(ij);
                    timer.detach();
                } else {
                    active = true;
                }
            }
            mJobStats.cleanup();
            for (int ise=mSensorStats.size()-1; ise>=0; ise--) {
                Sensor s = mSensorStats.valueAt(ise);
                if (s.reset()) {
                    mSensorStats.removeAt(ise);
                } else {
                    active = true;
                }
            }
            for (int ip=mProcessStats.size()-1; ip>=0; ip--) {
                Proc proc = mProcessStats.valueAt(ip);
                if (proc.mProcessState == PROCESS_STATE_NONE) {
                    proc.detach();
                    mProcessStats.removeAt(ip);
                } else {
                    proc.reset();
                    active = true;
                }
            }
            if (mPids.size() > 0) {
                for (int i=mPids.size()-1; i>=0; i--) {
                    Pid pid = mPids.valueAt(i);
                    if (pid.mWakeNesting > 0) {
                        active = true;
                    } else {
                        mPids.removeAt(i);
                    }
                }
            }
            if (mPackageStats.size() > 0) {
                Iterator<Map.Entry<String, Pkg>> it = mPackageStats.entrySet().iterator();
                while (it.hasNext()) {
                    Map.Entry<String, Pkg> pkgEntry = it.next();
                    Pkg p = pkgEntry.getValue();
                    p.detach();
                    if (p.mServiceStats.size() > 0) {
                        Iterator<Map.Entry<String, Pkg.Serv>> it2
                                = p.mServiceStats.entrySet().iterator();
                        while (it2.hasNext()) {
                            Map.Entry<String, Pkg.Serv> servEntry = it2.next();
                            servEntry.getValue().detach();
                        }
                    }
                }
                mPackageStats.clear();
            }

            if (!active) {
                if (mWifiRunningTimer != null) {
                    mWifiRunningTimer.detach();
                }
                if (mFullWifiLockTimer != null) {
                    mFullWifiLockTimer.detach();
                }
                if (mWifiScanTimer != null) {
                    mWifiScanTimer.detach();
                }
                for (int i = 0; i < NUM_WIFI_BATCHED_SCAN_BINS; i++) {
                    if (mWifiBatchedScanTimer[i] != null) {
                        mWifiBatchedScanTimer[i].detach();
                    }
                }
                if (mWifiMulticastTimer != null) {
                    mWifiMulticastTimer.detach();
                }
                if (mAudioTurnedOnTimer != null) {
                    mAudioTurnedOnTimer.detach();
                    mAudioTurnedOnTimer = null;
                }
                if (mVideoTurnedOnTimer != null) {
                    mVideoTurnedOnTimer.detach();
                    mVideoTurnedOnTimer = null;
                }
                if (mForegroundActivityTimer != null) {
                    mForegroundActivityTimer.detach();
                    mForegroundActivityTimer = null;
                }
                if (mUserActivityCounters != null) {
                    for (int i=0; i<NUM_USER_ACTIVITY_TYPES; i++) {
                        mUserActivityCounters[i].detach();
                    }
                }
                if (mNetworkByteActivityCounters != null) {
                    for (int i = 0; i < NUM_NETWORK_ACTIVITY_TYPES; i++) {
                        mNetworkByteActivityCounters[i].detach();
                        mNetworkPacketActivityCounters[i].detach();
                    }
                }
                mPids.clear();
            }

            return !active;
        }

        void writeToParcelLocked(Parcel out, long elapsedRealtimeUs) {
            final ArrayMap<String, Wakelock> wakeStats = mWakelockStats.getMap();
            int NW = wakeStats.size();
            out.writeInt(NW);
            for (int iw=0; iw<NW; iw++) {
                out.writeString(wakeStats.keyAt(iw));
                Uid.Wakelock wakelock = wakeStats.valueAt(iw);
                wakelock.writeToParcelLocked(out, elapsedRealtimeUs);
            }

            final ArrayMap<String, StopwatchTimer> syncStats = mSyncStats.getMap();
            int NS = syncStats.size();
            out.writeInt(NS);
            for (int is=0; is<NS; is++) {
                out.writeString(syncStats.keyAt(is));
                StopwatchTimer timer = syncStats.valueAt(is);
                Timer.writeTimerToParcel(out, timer, elapsedRealtimeUs);
            }

            final ArrayMap<String, StopwatchTimer> jobStats = mJobStats.getMap();
            int NJ = jobStats.size();
            out.writeInt(NJ);
            for (int ij=0; ij<NJ; ij++) {
                out.writeString(jobStats.keyAt(ij));
                StopwatchTimer timer = jobStats.valueAt(ij);
                Timer.writeTimerToParcel(out, timer, elapsedRealtimeUs);
            }

            int NSE = mSensorStats.size();
            out.writeInt(NSE);
            for (int ise=0; ise<NSE; ise++) {
                out.writeInt(mSensorStats.keyAt(ise));
                Uid.Sensor sensor = mSensorStats.valueAt(ise);
                sensor.writeToParcelLocked(out, elapsedRealtimeUs);
            }

            int NP = mProcessStats.size();
            out.writeInt(NP);
            for (int ip=0; ip<NP; ip++) {
                out.writeString(mProcessStats.keyAt(ip));
                Uid.Proc proc = mProcessStats.valueAt(ip);
                proc.writeToParcelLocked(out);
            }

            out.writeInt(mPackageStats.size());
            for (Map.Entry<String, Uid.Pkg> pkgEntry : mPackageStats.entrySet()) {
                out.writeString(pkgEntry.getKey());
                Uid.Pkg pkg = pkgEntry.getValue();
                pkg.writeToParcelLocked(out);
            }

            if (mWifiRunningTimer != null) {
                out.writeInt(1);
                mWifiRunningTimer.writeToParcel(out, elapsedRealtimeUs);
            } else {
                out.writeInt(0);
            }
            if (mFullWifiLockTimer != null) {
                out.writeInt(1);
                mFullWifiLockTimer.writeToParcel(out, elapsedRealtimeUs);
            } else {
                out.writeInt(0);
            }
            if (mWifiScanTimer != null) {
                out.writeInt(1);
                mWifiScanTimer.writeToParcel(out, elapsedRealtimeUs);
            } else {
                out.writeInt(0);
            }
            for (int i = 0; i < NUM_WIFI_BATCHED_SCAN_BINS; i++) {
                if (mWifiBatchedScanTimer[i] != null) {
                    out.writeInt(1);
                    mWifiBatchedScanTimer[i].writeToParcel(out, elapsedRealtimeUs);
                } else {
                    out.writeInt(0);
                }
            }
            if (mWifiMulticastTimer != null) {
                out.writeInt(1);
                mWifiMulticastTimer.writeToParcel(out, elapsedRealtimeUs);
            } else {
                out.writeInt(0);
            }
            if (mAudioTurnedOnTimer != null) {
                out.writeInt(1);
                mAudioTurnedOnTimer.writeToParcel(out, elapsedRealtimeUs);
            } else {
                out.writeInt(0);
            }
            if (mVideoTurnedOnTimer != null) {
                out.writeInt(1);
                mVideoTurnedOnTimer.writeToParcel(out, elapsedRealtimeUs);
            } else {
                out.writeInt(0);
            }
            if (mForegroundActivityTimer != null) {
                out.writeInt(1);
                mForegroundActivityTimer.writeToParcel(out, elapsedRealtimeUs);
            } else {
                out.writeInt(0);
            }
            for (int i = 0; i < NUM_PROCESS_STATE; i++) {
                if (mProcessStateTimer[i] != null) {
                    out.writeInt(1);
                    mProcessStateTimer[i].writeToParcel(out, elapsedRealtimeUs);
                } else {
                    out.writeInt(0);
                }
            }
            if (mVibratorOnTimer != null) {
                out.writeInt(1);
                mVibratorOnTimer.writeToParcel(out, elapsedRealtimeUs);
            } else {
                out.writeInt(0);
            }
            if (mUserActivityCounters != null) {
                out.writeInt(1);
                for (int i=0; i<NUM_USER_ACTIVITY_TYPES; i++) {
                    mUserActivityCounters[i].writeToParcel(out);
                }
            } else {
                out.writeInt(0);
            }
            if (mNetworkByteActivityCounters != null) {
                out.writeInt(1);
                for (int i = 0; i < NUM_NETWORK_ACTIVITY_TYPES; i++) {
                    mNetworkByteActivityCounters[i].writeToParcel(out);
                    mNetworkPacketActivityCounters[i].writeToParcel(out);
                }
                mMobileRadioActiveTime.writeToParcel(out);
                mMobileRadioActiveCount.writeToParcel(out);
            } else {
                out.writeInt(0);
            }
        }

        void readFromParcelLocked(TimeBase timeBase, TimeBase screenOffTimeBase, Parcel in) {
            int numWakelocks = in.readInt();
            mWakelockStats.clear();
            for (int j = 0; j < numWakelocks; j++) {
                String wakelockName = in.readString();
                Uid.Wakelock wakelock = new Wakelock();
                wakelock.readFromParcelLocked(timeBase, screenOffTimeBase, in);
                mWakelockStats.add(wakelockName, wakelock);
            }

            int numSyncs = in.readInt();
            mSyncStats.clear();
            for (int j = 0; j < numSyncs; j++) {
                String syncName = in.readString();
                if (in.readInt() != 0) {
                    mSyncStats.add(syncName,
                            new StopwatchTimer(Uid.this, SYNC, null, timeBase, in));
                }
            }

            int numJobs = in.readInt();
            mJobStats.clear();
            for (int j = 0; j < numJobs; j++) {
                String jobName = in.readString();
                if (in.readInt() != 0) {
                    mJobStats.add(jobName, new StopwatchTimer(Uid.this, JOB, null, timeBase, in));
                }
            }

            int numSensors = in.readInt();
            mSensorStats.clear();
            for (int k = 0; k < numSensors; k++) {
                int sensorNumber = in.readInt();
                Uid.Sensor sensor = new Sensor(sensorNumber);
                sensor.readFromParcelLocked(mOnBatteryTimeBase, in);
                mSensorStats.put(sensorNumber, sensor);
            }

            int numProcs = in.readInt();
            mProcessStats.clear();
            for (int k = 0; k < numProcs; k++) {
                String processName = in.readString();
                Uid.Proc proc = new Proc(processName);
                proc.readFromParcelLocked(in);
                mProcessStats.put(processName, proc);
            }

            int numPkgs = in.readInt();
            mPackageStats.clear();
            for (int l = 0; l < numPkgs; l++) {
                String packageName = in.readString();
                Uid.Pkg pkg = new Pkg();
                pkg.readFromParcelLocked(in);
                mPackageStats.put(packageName, pkg);
            }

            mWifiRunning = false;
            if (in.readInt() != 0) {
                mWifiRunningTimer = new StopwatchTimer(Uid.this, WIFI_RUNNING,
                        mWifiRunningTimers, mOnBatteryTimeBase, in);
            } else {
                mWifiRunningTimer = null;
            }
            mFullWifiLockOut = false;
            if (in.readInt() != 0) {
                mFullWifiLockTimer = new StopwatchTimer(Uid.this, FULL_WIFI_LOCK,
                        mFullWifiLockTimers, mOnBatteryTimeBase, in);
            } else {
                mFullWifiLockTimer = null;
            }
            mWifiScanStarted = false;
            if (in.readInt() != 0) {
                mWifiScanTimer = new StopwatchTimer(Uid.this, WIFI_SCAN,
                        mWifiScanTimers, mOnBatteryTimeBase, in);
            } else {
                mWifiScanTimer = null;
            }
            mWifiBatchedScanBinStarted = NO_BATCHED_SCAN_STARTED;
            for (int i = 0; i < NUM_WIFI_BATCHED_SCAN_BINS; i++) {
                if (in.readInt() != 0) {
                    makeWifiBatchedScanBin(i, in);
                } else {
                    mWifiBatchedScanTimer[i] = null;
                }
            }
            mWifiMulticastEnabled = false;
            if (in.readInt() != 0) {
                mWifiMulticastTimer = new StopwatchTimer(Uid.this, WIFI_MULTICAST_ENABLED,
                        mWifiMulticastTimers, mOnBatteryTimeBase, in);
            } else {
                mWifiMulticastTimer = null;
            }
            if (in.readInt() != 0) {
                mAudioTurnedOnTimer = new StopwatchTimer(Uid.this, AUDIO_TURNED_ON,
                        mAudioTurnedOnTimers, mOnBatteryTimeBase, in);
            } else {
                mAudioTurnedOnTimer = null;
            }
            if (in.readInt() != 0) {
                mVideoTurnedOnTimer = new StopwatchTimer(Uid.this, VIDEO_TURNED_ON,
                        mVideoTurnedOnTimers, mOnBatteryTimeBase, in);
            } else {
                mVideoTurnedOnTimer = null;
            }
            if (in.readInt() != 0) {
                mForegroundActivityTimer = new StopwatchTimer(
                        Uid.this, FOREGROUND_ACTIVITY, null, mOnBatteryTimeBase, in);
            } else {
                mForegroundActivityTimer = null;
            }
            mProcessState = PROCESS_STATE_NONE;
            for (int i = 0; i < NUM_PROCESS_STATE; i++) {
                if (in.readInt() != 0) {
                    makeProcessState(i, in);
                } else {
                    mProcessStateTimer[i] = null;
                }
            }
            if (in.readInt() != 0) {
                mVibratorOnTimer = new BatchTimer(Uid.this, VIBRATOR_ON, mOnBatteryTimeBase, in);
            } else {
                mVibratorOnTimer = null;
            }
            if (in.readInt() != 0) {
                mUserActivityCounters = new Counter[NUM_USER_ACTIVITY_TYPES];
                for (int i=0; i<NUM_USER_ACTIVITY_TYPES; i++) {
                    mUserActivityCounters[i] = new Counter(mOnBatteryTimeBase, in);
                }
            } else {
                mUserActivityCounters = null;
            }
            if (in.readInt() != 0) {
                mNetworkByteActivityCounters = new LongSamplingCounter[NUM_NETWORK_ACTIVITY_TYPES];
                mNetworkPacketActivityCounters
                        = new LongSamplingCounter[NUM_NETWORK_ACTIVITY_TYPES];
                for (int i = 0; i < NUM_NETWORK_ACTIVITY_TYPES; i++) {
                    mNetworkByteActivityCounters[i]
                            = new LongSamplingCounter(mOnBatteryTimeBase, in);
                    mNetworkPacketActivityCounters[i]
                            = new LongSamplingCounter(mOnBatteryTimeBase, in);
                }
                mMobileRadioActiveTime = new LongSamplingCounter(mOnBatteryTimeBase, in);
                mMobileRadioActiveCount = new LongSamplingCounter(mOnBatteryTimeBase, in);
            } else {
                mNetworkByteActivityCounters = null;
                mNetworkPacketActivityCounters = null;
            }
        }

        /**
         * The statistics associated with a particular wake lock.
         */
        public final class Wakelock extends BatteryStats.Uid.Wakelock {
            /**
             * How long (in ms) this uid has been keeping the device partially awake.
             */
            StopwatchTimer mTimerPartial;

            /**
             * How long (in ms) this uid has been keeping the device fully awake.
             */
            StopwatchTimer mTimerFull;

            /**
             * How long (in ms) this uid has had a window keeping the device awake.
             */
            StopwatchTimer mTimerWindow;

            /**
             * Reads a possibly null Timer from a Parcel.  The timer is associated with the
             * proper timer pool from the given BatteryStatsImpl object.
             *
             * @param in the Parcel to be read from.
             * return a new Timer, or null.
             */
            private StopwatchTimer readTimerFromParcel(int type, ArrayList<StopwatchTimer> pool,
                    TimeBase timeBase, Parcel in) {
                if (in.readInt() == 0) {
                    return null;
                }

                return new StopwatchTimer(Uid.this, type, pool, timeBase, in);
            }

            boolean reset() {
                boolean wlactive = false;
                if (mTimerFull != null) {
                    wlactive |= !mTimerFull.reset(false);
                }
                if (mTimerPartial != null) {
                    wlactive |= !mTimerPartial.reset(false);
                }
                if (mTimerWindow != null) {
                    wlactive |= !mTimerWindow.reset(false);
                }
                if (!wlactive) {
                    if (mTimerFull != null) {
                        mTimerFull.detach();
                        mTimerFull = null;
                    }
                    if (mTimerPartial != null) {
                        mTimerPartial.detach();
                        mTimerPartial = null;
                    }
                    if (mTimerWindow != null) {
                        mTimerWindow.detach();
                        mTimerWindow = null;
                    }
                }
                return !wlactive;
            }

            void readFromParcelLocked(TimeBase timeBase, TimeBase screenOffTimeBase, Parcel in) {
                mTimerPartial = readTimerFromParcel(WAKE_TYPE_PARTIAL,
                        mPartialTimers, screenOffTimeBase, in);
                mTimerFull = readTimerFromParcel(WAKE_TYPE_FULL,
                        mFullTimers, timeBase, in);
                mTimerWindow = readTimerFromParcel(WAKE_TYPE_WINDOW,
                        mWindowTimers, timeBase, in);
            }

            void writeToParcelLocked(Parcel out, long elapsedRealtimeUs) {
                Timer.writeTimerToParcel(out, mTimerPartial, elapsedRealtimeUs);
                Timer.writeTimerToParcel(out, mTimerFull, elapsedRealtimeUs);
                Timer.writeTimerToParcel(out, mTimerWindow, elapsedRealtimeUs);
            }

            @Override
            public Timer getWakeTime(int type) {
                switch (type) {
                case WAKE_TYPE_FULL: return mTimerFull;
                case WAKE_TYPE_PARTIAL: return mTimerPartial;
                case WAKE_TYPE_WINDOW: return mTimerWindow;
                default: throw new IllegalArgumentException("type = " + type);
                }
            }

            public StopwatchTimer getStopwatchTimer(int type) {
                StopwatchTimer t;
                switch (type) {
                    case WAKE_TYPE_PARTIAL:
                        t = mTimerPartial;
                        if (t == null) {
                            t = new StopwatchTimer(Uid.this, WAKE_TYPE_PARTIAL,
                                    mPartialTimers, mOnBatteryScreenOffTimeBase);
                            mTimerPartial = t;
                        }
                        return t;
                    case WAKE_TYPE_FULL:
                        t = mTimerFull;
                        if (t == null) {
                            t = new StopwatchTimer(Uid.this, WAKE_TYPE_FULL,
                                    mFullTimers, mOnBatteryTimeBase);
                            mTimerFull = t;
                        }
                        return t;
                    case WAKE_TYPE_WINDOW:
                        t = mTimerWindow;
                        if (t == null) {
                            t = new StopwatchTimer(Uid.this, WAKE_TYPE_WINDOW,
                                    mWindowTimers, mOnBatteryTimeBase);
                            mTimerWindow = t;
                        }
                        return t;
                    default:
                        throw new IllegalArgumentException("type=" + type);
                }
            }
        }

        public final class Sensor extends BatteryStats.Uid.Sensor {
            final int mHandle;
            StopwatchTimer mTimer;

            public Sensor(int handle) {
                mHandle = handle;
            }

            private StopwatchTimer readTimerFromParcel(TimeBase timeBase, Parcel in) {
                if (in.readInt() == 0) {
                    return null;
                }

                ArrayList<StopwatchTimer> pool = mSensorTimers.get(mHandle);
                if (pool == null) {
                    pool = new ArrayList<StopwatchTimer>();
                    mSensorTimers.put(mHandle, pool);
                }
                return new StopwatchTimer(Uid.this, 0, pool, timeBase, in);
            }

            boolean reset() {
                if (mTimer.reset(true)) {
                    mTimer = null;
                    return true;
                }
                return false;
            }

            void readFromParcelLocked(TimeBase timeBase, Parcel in) {
                mTimer = readTimerFromParcel(timeBase, in);
            }

            void writeToParcelLocked(Parcel out, long elapsedRealtimeUs) {
                Timer.writeTimerToParcel(out, mTimer, elapsedRealtimeUs);
            }

            @Override
            public Timer getSensorTime() {
                return mTimer;
            }

            @Override
            public int getHandle() {
                return mHandle;
            }
        }

        /**
         * The statistics associated with a particular process.
         */
        public final class Proc extends BatteryStats.Uid.Proc implements TimeBaseObs {
            /**
             * The name of this process.
             */
            final String mName;

            /**
             * Remains true until removed from the stats.
             */
            boolean mActive = true;

            /**
             * Total time (in 1/100 sec) spent executing in user code.
             */
            long mUserTime;

            /**
             * Total time (in 1/100 sec) spent executing in kernel code.
             */
            long mSystemTime;

            /**
             * Amount of time the process was running in the foreground.
             */
            long mForegroundTime;

            /**
             * Number of times the process has been started.
             */
            int mStarts;

            /**
             * Number of times the process has crashed.
             */
            int mNumCrashes;

            /**
             * Number of times the process has had an ANR.
             */
            int mNumAnrs;

            /**
             * The amount of user time loaded from a previous save.
             */
            long mLoadedUserTime;

            /**
             * The amount of system time loaded from a previous save.
             */
            long mLoadedSystemTime;

            /**
             * The amount of foreground time loaded from a previous save.
             */
            long mLoadedForegroundTime;

            /**
             * The number of times the process has started from a previous save.
             */
            int mLoadedStarts;

            /**
             * Number of times the process has crashed from a previous save.
             */
            int mLoadedNumCrashes;

            /**
             * Number of times the process has had an ANR from a previous save.
             */
            int mLoadedNumAnrs;

            /**
             * The amount of user time when last unplugged.
             */
            long mUnpluggedUserTime;

            /**
             * The amount of system time when last unplugged.
             */
            long mUnpluggedSystemTime;

            /**
             * The amount of foreground time since unplugged.
             */
            long mUnpluggedForegroundTime;

            /**
             * The number of times the process has started before unplugged.
             */
            int mUnpluggedStarts;

            /**
             * Number of times the process has crashed before unplugged.
             */
            int mUnpluggedNumCrashes;

            /**
             * Number of times the process has had an ANR before unplugged.
             */
            int mUnpluggedNumAnrs;

            /**
             * Current process state.
             */
            int mProcessState = PROCESS_STATE_NONE;

            SamplingCounter[] mSpeedBins;

            ArrayList<ExcessivePower> mExcessivePower;

            Proc(String name) {
                mName = name;
                mOnBatteryTimeBase.add(this);
                mSpeedBins = new SamplingCounter[getCpuSpeedSteps()];
            }

            public void onTimeStarted(long elapsedRealtime, long baseUptime, long baseRealtime) {
                mUnpluggedUserTime = mUserTime;
                mUnpluggedSystemTime = mSystemTime;
                mUnpluggedForegroundTime = mForegroundTime;
                mUnpluggedStarts = mStarts;
                mUnpluggedNumCrashes = mNumCrashes;
                mUnpluggedNumAnrs = mNumAnrs;
            }

            public void onTimeStopped(long elapsedRealtime, long baseUptime, long baseRealtime) {
            }

            void reset() {
                mUserTime = mSystemTime = mForegroundTime = 0;
                mStarts = mNumCrashes = mNumAnrs = 0;
                mLoadedUserTime = mLoadedSystemTime = mLoadedForegroundTime = 0;
                mLoadedStarts = mLoadedNumCrashes = mLoadedNumAnrs = 0;
                mUnpluggedUserTime = mUnpluggedSystemTime = mUnpluggedForegroundTime = 0;
                mUnpluggedStarts = mUnpluggedNumCrashes = mUnpluggedNumAnrs = 0;
                for (int i = 0; i < mSpeedBins.length; i++) {
                    SamplingCounter c = mSpeedBins[i];
                    if (c != null) {
                        c.reset(false);
                    }
                }
                mExcessivePower = null;
            }

            void detach() {
                mActive = false;
                mOnBatteryTimeBase.remove(this);
                for (int i = 0; i < mSpeedBins.length; i++) {
                    SamplingCounter c = mSpeedBins[i];
                    if (c != null) {
                        mOnBatteryTimeBase.remove(c);
                        mSpeedBins[i] = null;
                    }
                }
            }

            public int countExcessivePowers() {
                return mExcessivePower != null ? mExcessivePower.size() : 0;
            }

            public ExcessivePower getExcessivePower(int i) {
                if (mExcessivePower != null) {
                    return mExcessivePower.get(i);
                }
                return null;
            }

            public void addExcessiveWake(long overTime, long usedTime) {
                if (mExcessivePower == null) {
                    mExcessivePower = new ArrayList<ExcessivePower>();
                }
                ExcessivePower ew = new ExcessivePower();
                ew.type = ExcessivePower.TYPE_WAKE;
                ew.overTime = overTime;
                ew.usedTime = usedTime;
                mExcessivePower.add(ew);
            }

            public void addExcessiveCpu(long overTime, long usedTime) {
                if (mExcessivePower == null) {
                    mExcessivePower = new ArrayList<ExcessivePower>();
                }
                ExcessivePower ew = new ExcessivePower();
                ew.type = ExcessivePower.TYPE_CPU;
                ew.overTime = overTime;
                ew.usedTime = usedTime;
                mExcessivePower.add(ew);
            }

            void writeExcessivePowerToParcelLocked(Parcel out) {
                if (mExcessivePower == null) {
                    out.writeInt(0);
                    return;
                }

                final int N = mExcessivePower.size();
                out.writeInt(N);
                for (int i=0; i<N; i++) {
                    ExcessivePower ew = mExcessivePower.get(i);
                    out.writeInt(ew.type);
                    out.writeLong(ew.overTime);
                    out.writeLong(ew.usedTime);
                }
            }

            boolean readExcessivePowerFromParcelLocked(Parcel in) {
                final int N = in.readInt();
                if (N == 0) {
                    mExcessivePower = null;
                    return true;
                }

                if (N > 10000) {
                    Slog.w(TAG, "File corrupt: too many excessive power entries " + N);
                    return false;
                }
                
                mExcessivePower = new ArrayList<ExcessivePower>();
                for (int i=0; i<N; i++) {
                    ExcessivePower ew = new ExcessivePower();
                    ew.type = in.readInt();
                    ew.overTime = in.readLong();
                    ew.usedTime = in.readLong();
                    mExcessivePower.add(ew);
                }
                return true;
            }

            void writeToParcelLocked(Parcel out) {
                out.writeLong(mUserTime);
                out.writeLong(mSystemTime);
                out.writeLong(mForegroundTime);
                out.writeInt(mStarts);
                out.writeInt(mNumCrashes);
                out.writeInt(mNumAnrs);
                out.writeLong(mLoadedUserTime);
                out.writeLong(mLoadedSystemTime);
                out.writeLong(mLoadedForegroundTime);
                out.writeInt(mLoadedStarts);
                out.writeInt(mLoadedNumCrashes);
                out.writeInt(mLoadedNumAnrs);
                out.writeLong(mUnpluggedUserTime);
                out.writeLong(mUnpluggedSystemTime);
                out.writeLong(mUnpluggedForegroundTime);
                out.writeInt(mUnpluggedStarts);
                out.writeInt(mUnpluggedNumCrashes);
                out.writeInt(mUnpluggedNumAnrs);

                out.writeInt(mSpeedBins.length);
                for (int i = 0; i < mSpeedBins.length; i++) {
                    SamplingCounter c = mSpeedBins[i];
                    if (c != null) {
                        out.writeInt(1);
                        c.writeToParcel(out);
                    } else {
                        out.writeInt(0);
                    }
                }

                writeExcessivePowerToParcelLocked(out);
            }

            void readFromParcelLocked(Parcel in) {
                mUserTime = in.readLong();
                mSystemTime = in.readLong();
                mForegroundTime = in.readLong();
                mStarts = in.readInt();
                mNumCrashes = in.readInt();
                mNumAnrs = in.readInt();
                mLoadedUserTime = in.readLong();
                mLoadedSystemTime = in.readLong();
                mLoadedForegroundTime = in.readLong();
                mLoadedStarts = in.readInt();
                mLoadedNumCrashes = in.readInt();
                mLoadedNumAnrs = in.readInt();
                mUnpluggedUserTime = in.readLong();
                mUnpluggedSystemTime = in.readLong();
                mUnpluggedForegroundTime = in.readLong();
                mUnpluggedStarts = in.readInt();
                mUnpluggedNumCrashes = in.readInt();
                mUnpluggedNumAnrs = in.readInt();

                int bins = in.readInt();
                int steps = getCpuSpeedSteps();
                mSpeedBins = new SamplingCounter[bins >= steps ? bins : steps];
                for (int i = 0; i < bins; i++) {
                    if (in.readInt() != 0) {
                        mSpeedBins[i] = new SamplingCounter(mOnBatteryTimeBase, in);
                    }
                }

                readExcessivePowerFromParcelLocked(in);
            }

            public BatteryStatsImpl getBatteryStats() {
                return BatteryStatsImpl.this;
            }

            public void addCpuTimeLocked(int utime, int stime) {
                mUserTime += utime;
                mSystemTime += stime;
            }

            public void addForegroundTimeLocked(long ttime) {
                mForegroundTime += ttime;
            }

            public void incStartsLocked() {
                mStarts++;
            }

            public void incNumCrashesLocked() {
                mNumCrashes++;
            }

            public void incNumAnrsLocked() {
                mNumAnrs++;
            }

            @Override
            public boolean isActive() {
                return mActive;
            }

            @Override
            public long getUserTime(int which) {
                long val = mUserTime;
                if (which == STATS_CURRENT) {
                    val -= mLoadedUserTime;
                } else if (which == STATS_SINCE_UNPLUGGED) {
                    val -= mUnpluggedUserTime;
                }
                return val;
            }

            @Override
            public long getSystemTime(int which) {
                long val = mSystemTime;
                if (which == STATS_CURRENT) {
                    val -= mLoadedSystemTime;
                } else if (which == STATS_SINCE_UNPLUGGED) {
                    val -= mUnpluggedSystemTime;
                }
                return val;
            }

            @Override
            public long getForegroundTime(int which) {
                long val = mForegroundTime;
                if (which == STATS_CURRENT) {
                    val -= mLoadedForegroundTime;
                } else if (which == STATS_SINCE_UNPLUGGED) {
                    val -= mUnpluggedForegroundTime;
                }
                return val;
            }

            @Override
            public int getStarts(int which) {
                int val = mStarts;
                if (which == STATS_CURRENT) {
                    val -= mLoadedStarts;
                } else if (which == STATS_SINCE_UNPLUGGED) {
                    val -= mUnpluggedStarts;
                }
                return val;
            }

            @Override
            public int getNumCrashes(int which) {
                int val = mNumCrashes;
                if (which == STATS_CURRENT) {
                    val -= mLoadedNumCrashes;
                } else if (which == STATS_SINCE_UNPLUGGED) {
                    val -= mUnpluggedNumCrashes;
                }
                return val;
            }

            @Override
            public int getNumAnrs(int which) {
                int val = mNumAnrs;
                if (which == STATS_CURRENT) {
                    val -= mLoadedNumAnrs;
                } else if (which == STATS_SINCE_UNPLUGGED) {
                    val -= mUnpluggedNumAnrs;
                }
                return val;
            }

            /* Called by ActivityManagerService when CPU times are updated. */
            public void addSpeedStepTimes(long[] values) {
                for (int i = 0; i < mSpeedBins.length && i < values.length; i++) {
                    long amt = values[i];
                    if (amt != 0) {
                        SamplingCounter c = mSpeedBins[i];
                        if (c == null) {
                            mSpeedBins[i] = c = new SamplingCounter(mOnBatteryTimeBase);
                        }
                        c.addCountAtomic(values[i]);
                    }
                }
            }

            @Override
            public long getTimeAtCpuSpeedStep(int speedStep, int which) {
                if (speedStep < mSpeedBins.length) {
                    SamplingCounter c = mSpeedBins[speedStep];
                    return c != null ? c.getCountLocked(which) : 0;
                } else {
                    return 0;
                }
            }
        }

        /**
         * The statistics associated with a particular package.
         */
        public final class Pkg extends BatteryStats.Uid.Pkg implements TimeBaseObs {
            /**
             * Number of times this package has done something that could wake up the
             * device from sleep.
             */
            int mWakeups;

            /**
             * Number of things that could wake up the device loaded from a
             * previous save.
             */
            int mLoadedWakeups;

            /**
             * Number of things that could wake up the device as of the
             * last run.
             */
            int mLastWakeups;

            /**
             * Number of things that could wake up the device as of the
             * last run.
             */
            int mUnpluggedWakeups;

            /**
             * The statics we have collected for this package's services.
             */
            final HashMap<String, Serv> mServiceStats = new HashMap<String, Serv>();

            Pkg() {
                mOnBatteryScreenOffTimeBase.add(this);
            }

            public void onTimeStarted(long elapsedRealtime, long baseUptime, long baseRealtime) {
                mUnpluggedWakeups = mWakeups;
            }

            public void onTimeStopped(long elapsedRealtime, long baseUptime, long baseRealtime) {
            }

            void detach() {
                mOnBatteryScreenOffTimeBase.remove(this);
            }

            void readFromParcelLocked(Parcel in) {
                mWakeups = in.readInt();
                mLoadedWakeups = in.readInt();
                mLastWakeups = 0;
                mUnpluggedWakeups = in.readInt();

                int numServs = in.readInt();
                mServiceStats.clear();
                for (int m = 0; m < numServs; m++) {
                    String serviceName = in.readString();
                    Uid.Pkg.Serv serv = new Serv();
                    mServiceStats.put(serviceName, serv);

                    serv.readFromParcelLocked(in);
                }
            }

            void writeToParcelLocked(Parcel out) {
                out.writeInt(mWakeups);
                out.writeInt(mLoadedWakeups);
                out.writeInt(mUnpluggedWakeups);

                out.writeInt(mServiceStats.size());
                for (Map.Entry<String, Uid.Pkg.Serv> servEntry : mServiceStats.entrySet()) {
                    out.writeString(servEntry.getKey());
                    Uid.Pkg.Serv serv = servEntry.getValue();

                    serv.writeToParcelLocked(out);
                }
            }

            @Override
            public Map<String, ? extends BatteryStats.Uid.Pkg.Serv> getServiceStats() {
                return mServiceStats;
            }

            @Override
            public int getWakeups(int which) {
                int val = mWakeups;
                if (which == STATS_CURRENT) {
                    val -= mLoadedWakeups;
                } else if (which == STATS_SINCE_UNPLUGGED) {
                    val -= mUnpluggedWakeups;
                }

                return val;
            }

            /**
             * The statistics associated with a particular service.
             */
            public final class Serv extends BatteryStats.Uid.Pkg.Serv implements TimeBaseObs {
                /**
                 * Total time (ms in battery uptime) the service has been left started.
                 */
                long mStartTime;

                /**
                 * If service has been started and not yet stopped, this is
                 * when it was started.
                 */
                long mRunningSince;

                /**
                 * True if we are currently running.
                 */
                boolean mRunning;

                /**
                 * Total number of times startService() has been called.
                 */
                int mStarts;

                /**
                 * Total time (ms in battery uptime) the service has been left launched.
                 */
                long mLaunchedTime;

                /**
                 * If service has been launched and not yet exited, this is
                 * when it was launched (ms in battery uptime).
                 */
                long mLaunchedSince;

                /**
                 * True if we are currently launched.
                 */
                boolean mLaunched;

                /**
                 * Total number times the service has been launched.
                 */
                int mLaunches;

                /**
                 * The amount of time spent started loaded from a previous save
                 * (ms in battery uptime).
                 */
                long mLoadedStartTime;

                /**
                 * The number of starts loaded from a previous save.
                 */
                int mLoadedStarts;

                /**
                 * The number of launches loaded from a previous save.
                 */
                int mLoadedLaunches;

                /**
                 * The amount of time spent started as of the last run (ms
                 * in battery uptime).
                 */
                long mLastStartTime;

                /**
                 * The number of starts as of the last run.
                 */
                int mLastStarts;

                /**
                 * The number of launches as of the last run.
                 */
                int mLastLaunches;

                /**
                 * The amount of time spent started when last unplugged (ms
                 * in battery uptime).
                 */
                long mUnpluggedStartTime;

                /**
                 * The number of starts when last unplugged.
                 */
                int mUnpluggedStarts;

                /**
                 * The number of launches when last unplugged.
                 */
                int mUnpluggedLaunches;

                Serv() {
                    mOnBatteryTimeBase.add(this);
                }

                public void onTimeStarted(long elapsedRealtime, long baseUptime,
                        long baseRealtime) {
                    mUnpluggedStartTime = getStartTimeToNowLocked(baseUptime);
                    mUnpluggedStarts = mStarts;
                    mUnpluggedLaunches = mLaunches;
                }

                public void onTimeStopped(long elapsedRealtime, long baseUptime,
                        long baseRealtime) {
                }

                void detach() {
                    mOnBatteryTimeBase.remove(this);
                }

                void readFromParcelLocked(Parcel in) {
                    mStartTime = in.readLong();
                    mRunningSince = in.readLong();
                    mRunning = in.readInt() != 0;
                    mStarts = in.readInt();
                    mLaunchedTime = in.readLong();
                    mLaunchedSince = in.readLong();
                    mLaunched = in.readInt() != 0;
                    mLaunches = in.readInt();
                    mLoadedStartTime = in.readLong();
                    mLoadedStarts = in.readInt();
                    mLoadedLaunches = in.readInt();
                    mLastStartTime = 0;
                    mLastStarts = 0;
                    mLastLaunches = 0;
                    mUnpluggedStartTime = in.readLong();
                    mUnpluggedStarts = in.readInt();
                    mUnpluggedLaunches = in.readInt();
                }

                void writeToParcelLocked(Parcel out) {
                    out.writeLong(mStartTime);
                    out.writeLong(mRunningSince);
                    out.writeInt(mRunning ? 1 : 0);
                    out.writeInt(mStarts);
                    out.writeLong(mLaunchedTime);
                    out.writeLong(mLaunchedSince);
                    out.writeInt(mLaunched ? 1 : 0);
                    out.writeInt(mLaunches);
                    out.writeLong(mLoadedStartTime);
                    out.writeInt(mLoadedStarts);
                    out.writeInt(mLoadedLaunches);
                    out.writeLong(mUnpluggedStartTime);
                    out.writeInt(mUnpluggedStarts);
                    out.writeInt(mUnpluggedLaunches);
                }

                long getLaunchTimeToNowLocked(long batteryUptime) {
                    if (!mLaunched) return mLaunchedTime;
                    return mLaunchedTime + batteryUptime - mLaunchedSince;
                }

                long getStartTimeToNowLocked(long batteryUptime) {
                    if (!mRunning) return mStartTime;
                    return mStartTime + batteryUptime - mRunningSince;
                }

                public void startLaunchedLocked() {
                    if (!mLaunched) {
                        mLaunches++;
                        mLaunchedSince = getBatteryUptimeLocked();
                        mLaunched = true;
                    }
                }

                public void stopLaunchedLocked() {
                    if (mLaunched) {
                        long time = getBatteryUptimeLocked() - mLaunchedSince;
                        if (time > 0) {
                            mLaunchedTime += time;
                        } else {
                            mLaunches--;
                        }
                        mLaunched = false;
                    }
                }

                public void startRunningLocked() {
                    if (!mRunning) {
                        mStarts++;
                        mRunningSince = getBatteryUptimeLocked();
                        mRunning = true;
                    }
                }

                public void stopRunningLocked() {
                    if (mRunning) {
                        long time = getBatteryUptimeLocked() - mRunningSince;
                        if (time > 0) {
                            mStartTime += time;
                        } else {
                            mStarts--;
                        }
                        mRunning = false;
                    }
                }

                public BatteryStatsImpl getBatteryStats() {
                    return BatteryStatsImpl.this;
                }

                @Override
                public int getLaunches(int which) {
                    int val = mLaunches;
                    if (which == STATS_CURRENT) {
                        val -= mLoadedLaunches;
                    } else if (which == STATS_SINCE_UNPLUGGED) {
                        val -= mUnpluggedLaunches;
                    }
                    return val;
                }

                @Override
                public long getStartTime(long now, int which) {
                    long val = getStartTimeToNowLocked(now);
                    if (which == STATS_CURRENT) {
                        val -= mLoadedStartTime;
                    } else if (which == STATS_SINCE_UNPLUGGED) {
                        val -= mUnpluggedStartTime;
                    }
                    return val;
                }

                @Override
                public int getStarts(int which) {
                    int val = mStarts;
                    if (which == STATS_CURRENT) {
                        val -= mLoadedStarts;
                    } else if (which == STATS_SINCE_UNPLUGGED) {
                        val -= mUnpluggedStarts;
                    }

                    return val;
                }
            }

            public BatteryStatsImpl getBatteryStats() {
                return BatteryStatsImpl.this;
            }

            public void incWakeupsLocked() {
                mWakeups++;
            }

            final Serv newServiceStatsLocked() {
                return new Serv();
            }
        }

        /**
         * Retrieve the statistics object for a particular process, creating
         * if needed.
         */
        public Proc getProcessStatsLocked(String name) {
            Proc ps = mProcessStats.get(name);
            if (ps == null) {
                ps = new Proc(name);
                mProcessStats.put(name, ps);
            }

            return ps;
        }

        public void updateProcessStateLocked(String procName, int state, long elapsedRealtimeMs) {
            int procState;
            if (state <= ActivityManager.PROCESS_STATE_IMPORTANT_FOREGROUND) {
                procState = PROCESS_STATE_FOREGROUND;
            } else if (state <= ActivityManager.PROCESS_STATE_RECEIVER) {
                procState = PROCESS_STATE_ACTIVE;
            } else {
                procState = PROCESS_STATE_RUNNING;
            }
            updateRealProcessStateLocked(procName, procState, elapsedRealtimeMs);
        }

        public void updateRealProcessStateLocked(String procName, int procState,
                long elapsedRealtimeMs) {
            Proc proc = getProcessStatsLocked(procName);
            if (proc.mProcessState != procState) {
                boolean changed;
                if (procState < proc.mProcessState) {
                    // Has this process become more important?  If so,
                    // we may need to change the uid if the currrent uid proc state
                    // is not as important as what we are now setting.
                    changed = mProcessState > procState;
                } else {
                    // Has this process become less important?  If so,
                    // we may need to change the uid if the current uid proc state
                    // is the same importance as the old setting.
                    changed = mProcessState == proc.mProcessState;
                }
                proc.mProcessState = procState;
                if (changed) {
                    // uid's state may have changed; compute what the new state should be.
                    int uidProcState = PROCESS_STATE_NONE;
                    for (int ip=mProcessStats.size()-1; ip>=0; ip--) {
                        proc = mProcessStats.valueAt(ip);
                        if (proc.mProcessState < uidProcState) {
                            uidProcState = proc.mProcessState;
                        }
                    }
                    updateUidProcessStateLocked(uidProcState, elapsedRealtimeMs);
                }
            }
        }

        public SparseArray<? extends Pid> getPidStats() {
            return mPids;
        }

        public Pid getPidStatsLocked(int pid) {
            Pid p = mPids.get(pid);
            if (p == null) {
                p = new Pid();
                mPids.put(pid, p);
            }
            return p;
        }

        /**
         * Retrieve the statistics object for a particular service, creating
         * if needed.
         */
        public Pkg getPackageStatsLocked(String name) {
            Pkg ps = mPackageStats.get(name);
            if (ps == null) {
                ps = new Pkg();
                mPackageStats.put(name, ps);
            }

            return ps;
        }

        /**
         * Retrieve the statistics object for a particular service, creating
         * if needed.
         */
        public Pkg.Serv getServiceStatsLocked(String pkg, String serv) {
            Pkg ps = getPackageStatsLocked(pkg);
            Pkg.Serv ss = ps.mServiceStats.get(serv);
            if (ss == null) {
                ss = ps.newServiceStatsLocked();
                ps.mServiceStats.put(serv, ss);
            }

            return ss;
        }

        public void readSyncSummaryFromParcelLocked(String name, Parcel in) {
            StopwatchTimer timer = mSyncStats.instantiateObject();
            timer.readSummaryFromParcelLocked(in);
            mSyncStats.add(name, timer);
        }

        public void readJobSummaryFromParcelLocked(String name, Parcel in) {
            StopwatchTimer timer = mJobStats.instantiateObject();
            timer.readSummaryFromParcelLocked(in);
            mJobStats.add(name, timer);
        }

        public void readWakeSummaryFromParcelLocked(String wlName, Parcel in) {
            Wakelock wl = new Wakelock();
            mWakelockStats.add(wlName, wl);
            if (in.readInt() != 0) {
                wl.getStopwatchTimer(WAKE_TYPE_FULL).readSummaryFromParcelLocked(in);
            }
            if (in.readInt() != 0) {
                wl.getStopwatchTimer(WAKE_TYPE_PARTIAL).readSummaryFromParcelLocked(in);
            }
            if (in.readInt() != 0) {
                wl.getStopwatchTimer(WAKE_TYPE_WINDOW).readSummaryFromParcelLocked(in);
            }
        }

        public StopwatchTimer getSensorTimerLocked(int sensor, boolean create) {
            Sensor se = mSensorStats.get(sensor);
            if (se == null) {
                if (!create) {
                    return null;
                }
                se = new Sensor(sensor);
                mSensorStats.put(sensor, se);
            }
            StopwatchTimer t = se.mTimer;
            if (t != null) {
                return t;
            }
            ArrayList<StopwatchTimer> timers = mSensorTimers.get(sensor);
            if (timers == null) {
                timers = new ArrayList<StopwatchTimer>();
                mSensorTimers.put(sensor, timers);
            }
            t = new StopwatchTimer(Uid.this, BatteryStats.SENSOR, timers, mOnBatteryTimeBase);
            se.mTimer = t;
            return t;
        }

        public void noteStartSyncLocked(String name, long elapsedRealtimeMs) {
            StopwatchTimer t = mSyncStats.startObject(name);
            if (t != null) {
                t.startRunningLocked(elapsedRealtimeMs);
            }
        }

        public void noteStopSyncLocked(String name, long elapsedRealtimeMs) {
            StopwatchTimer t = mSyncStats.stopObject(name);
            if (t != null) {
                t.stopRunningLocked(elapsedRealtimeMs);
            }
        }

        public void noteStartJobLocked(String name, long elapsedRealtimeMs) {
            StopwatchTimer t = mJobStats.startObject(name);
            if (t != null) {
                t.startRunningLocked(elapsedRealtimeMs);
            }
        }

        public void noteStopJobLocked(String name, long elapsedRealtimeMs) {
            StopwatchTimer t = mJobStats.stopObject(name);
            if (t != null) {
                t.stopRunningLocked(elapsedRealtimeMs);
            }
        }

        public void noteStartWakeLocked(int pid, String name, int type, long elapsedRealtimeMs) {
            Wakelock wl = mWakelockStats.startObject(name);
            if (wl != null) {
                wl.getStopwatchTimer(type).startRunningLocked(elapsedRealtimeMs);
            }
            if (pid >= 0 && type == WAKE_TYPE_PARTIAL) {
                Pid p = getPidStatsLocked(pid);
                if (p.mWakeNesting++ == 0) {
                    p.mWakeStartMs = elapsedRealtimeMs;
                }
            }
        }

        public void noteStopWakeLocked(int pid, String name, int type, long elapsedRealtimeMs) {
            Wakelock wl = mWakelockStats.stopObject(name);
            if (wl != null) {
                wl.getStopwatchTimer(type).stopRunningLocked(elapsedRealtimeMs);
            }
            if (pid >= 0 && type == WAKE_TYPE_PARTIAL) {
                Pid p = mPids.get(pid);
                if (p != null && p.mWakeNesting > 0) {
                    if (p.mWakeNesting-- == 1) {
                        p.mWakeSumMs += elapsedRealtimeMs - p.mWakeStartMs;
                        p.mWakeStartMs = 0;
                    }
                }
            }
        }

        public void reportExcessiveWakeLocked(String proc, long overTime, long usedTime) {
            Proc p = getProcessStatsLocked(proc);
            if (p != null) {
                p.addExcessiveWake(overTime, usedTime);
            }
        }

        public void reportExcessiveCpuLocked(String proc, long overTime, long usedTime) {
            Proc p = getProcessStatsLocked(proc);
            if (p != null) {
                p.addExcessiveCpu(overTime, usedTime);
            }
        }

        public void noteStartSensor(int sensor, long elapsedRealtimeMs) {
            StopwatchTimer t = getSensorTimerLocked(sensor, true);
            if (t != null) {
                t.startRunningLocked(elapsedRealtimeMs);
            }
        }

        public void noteStopSensor(int sensor, long elapsedRealtimeMs) {
            // Don't create a timer if one doesn't already exist
            StopwatchTimer t = getSensorTimerLocked(sensor, false);
            if (t != null) {
                t.stopRunningLocked(elapsedRealtimeMs);
            }
        }

        public void noteStartGps(long elapsedRealtimeMs) {
            StopwatchTimer t = getSensorTimerLocked(Sensor.GPS, true);
            if (t != null) {
                t.startRunningLocked(elapsedRealtimeMs);
            }
        }

        public void noteStopGps(long elapsedRealtimeMs) {
            StopwatchTimer t = getSensorTimerLocked(Sensor.GPS, false);
            if (t != null) {
                t.stopRunningLocked(elapsedRealtimeMs);
            }
        }

        public BatteryStatsImpl getBatteryStats() {
            return BatteryStatsImpl.this;
        }
    }

    public BatteryStatsImpl(File systemDir, Handler handler) {
        if (systemDir != null) {
            mFile = new JournaledFile(new File(systemDir, "batterystats.bin"),
                    new File(systemDir, "batterystats.bin.tmp"));
        } else {
            mFile = null;
        }
        mCheckinFile = new AtomicFile(new File(systemDir, "batterystats-checkin.bin"));
        mHandler = new MyHandler(handler.getLooper());
        mStartCount++;
        mScreenOnTimer = new StopwatchTimer(null, -1, null, mOnBatteryTimeBase);
        for (int i=0; i<NUM_SCREEN_BRIGHTNESS_BINS; i++) {
            mScreenBrightnessTimer[i] = new StopwatchTimer(null, -100-i, null, mOnBatteryTimeBase);
        }
        mInteractiveTimer = new StopwatchTimer(null, -9, null, mOnBatteryTimeBase);
        mLowPowerModeEnabledTimer = new StopwatchTimer(null, -2, null, mOnBatteryTimeBase);
        mPhoneOnTimer = new StopwatchTimer(null, -3, null, mOnBatteryTimeBase);
        for (int i=0; i<SignalStrength.NUM_SIGNAL_STRENGTH_BINS; i++) {
            mPhoneSignalStrengthsTimer[i] = new StopwatchTimer(null, -200-i, null,
                    mOnBatteryTimeBase);
        }
        mPhoneSignalScanningTimer = new StopwatchTimer(null, -200+1, null, mOnBatteryTimeBase);
        for (int i=0; i<NUM_DATA_CONNECTION_TYPES; i++) {
            mPhoneDataConnectionsTimer[i] = new StopwatchTimer(null, -300-i, null,
                    mOnBatteryTimeBase);
        }
        for (int i = 0; i < NUM_NETWORK_ACTIVITY_TYPES; i++) {
            mNetworkByteActivityCounters[i] = new LongSamplingCounter(mOnBatteryTimeBase);
            mNetworkPacketActivityCounters[i] = new LongSamplingCounter(mOnBatteryTimeBase);
        }
        mMobileRadioActiveTimer = new StopwatchTimer(null, -400, null, mOnBatteryTimeBase);
        mMobileRadioActivePerAppTimer = new StopwatchTimer(null, -401, null, mOnBatteryTimeBase);
        mMobileRadioActiveAdjustedTime = new LongSamplingCounter(mOnBatteryTimeBase);
        mMobileRadioActiveUnknownTime = new LongSamplingCounter(mOnBatteryTimeBase);
        mMobileRadioActiveUnknownCount = new LongSamplingCounter(mOnBatteryTimeBase);
        mWifiOnTimer = new StopwatchTimer(null, -4, null, mOnBatteryTimeBase);
        mGlobalWifiRunningTimer = new StopwatchTimer(null, -5, null, mOnBatteryTimeBase);
        for (int i=0; i<NUM_WIFI_STATES; i++) {
            mWifiStateTimer[i] = new StopwatchTimer(null, -600-i, null, mOnBatteryTimeBase);
        }
        for (int i=0; i<NUM_WIFI_SUPPL_STATES; i++) {
            mWifiSupplStateTimer[i] = new StopwatchTimer(null, -700-i, null, mOnBatteryTimeBase);
        }
        for (int i=0; i<NUM_WIFI_SIGNAL_STRENGTH_BINS; i++) {
            mWifiSignalStrengthsTimer[i] = new StopwatchTimer(null, -800-i, null,
                    mOnBatteryTimeBase);
        }
        mBluetoothOnTimer = new StopwatchTimer(null, -6, null, mOnBatteryTimeBase);
        for (int i=0; i< NUM_BLUETOOTH_STATES; i++) {
            mBluetoothStateTimer[i] = new StopwatchTimer(null, -500-i, null, mOnBatteryTimeBase);
        }
        mAudioOnTimer = new StopwatchTimer(null, -7, null, mOnBatteryTimeBase);
        mVideoOnTimer = new StopwatchTimer(null, -8, null, mOnBatteryTimeBase);
        mFlashlightOnTimer = new StopwatchTimer(null, -9, null, mOnBatteryTimeBase);
        mOnBattery = mOnBatteryInternal = false;
        long uptime = SystemClock.uptimeMillis() * 1000;
        long realtime = SystemClock.elapsedRealtime() * 1000;
        initTimes(uptime, realtime);
        mStartPlatformVersion = mEndPlatformVersion = Build.ID;
        mDischargeStartLevel = 0;
        mDischargeUnplugLevel = 0;
        mDischargePlugLevel = -1;
        mDischargeCurrentLevel = 0;
        mCurrentBatteryLevel = 0;
        initDischarge();
        clearHistoryLocked();
    }

    public BatteryStatsImpl(Parcel p) {
        mFile = null;
        mCheckinFile = null;
        mHandler = null;
        clearHistoryLocked();
        readFromParcel(p);
    }

    public void setCallback(BatteryCallback cb) {
        mCallback = cb;
    }

    public void setNumSpeedSteps(int steps) {
        if (sNumSpeedSteps == 0) sNumSpeedSteps = steps;
    }

    public void setRadioScanningTimeout(long timeout) {
        if (mPhoneSignalScanningTimer != null) {
            mPhoneSignalScanningTimer.setTimeout(timeout);
        }
    }

    @Override
    public boolean startIteratingOldHistoryLocked() {
        if (DEBUG_HISTORY) Slog.i(TAG, "ITERATING: buff size=" + mHistoryBuffer.dataSize()
                + " pos=" + mHistoryBuffer.dataPosition());
        if ((mHistoryIterator = mHistory) == null) {
            return false;
        }
        mHistoryBuffer.setDataPosition(0);
        mHistoryReadTmp.clear();
        mReadOverflow = false;
        mIteratingHistory = true;
        return true;
    }

    @Override
    public boolean getNextOldHistoryLocked(HistoryItem out) {
        boolean end = mHistoryBuffer.dataPosition() >= mHistoryBuffer.dataSize();
        if (!end) {
            readHistoryDelta(mHistoryBuffer, mHistoryReadTmp);
            mReadOverflow |= mHistoryReadTmp.cmd == HistoryItem.CMD_OVERFLOW;
        }
        HistoryItem cur = mHistoryIterator;
        if (cur == null) {
            if (!mReadOverflow && !end) {
                Slog.w(TAG, "Old history ends before new history!");
            }
            return false;
        }
        out.setTo(cur);
        mHistoryIterator = cur.next;
        if (!mReadOverflow) {
            if (end) {
                Slog.w(TAG, "New history ends before old history!");
            } else if (!out.same(mHistoryReadTmp)) {
                PrintWriter pw = new FastPrintWriter(new LogWriter(android.util.Log.WARN, TAG));
                pw.println("Histories differ!");
                pw.println("Old history:");
                (new HistoryPrinter()).printNextItem(pw, out, 0, false, true);
                pw.println("New history:");
                (new HistoryPrinter()).printNextItem(pw, mHistoryReadTmp, 0, false,
                        true);
                pw.flush();
            }
        }
        return true;
    }

    @Override
    public void finishIteratingOldHistoryLocked() {
        mIteratingHistory = false;
        mHistoryBuffer.setDataPosition(mHistoryBuffer.dataSize());
        mHistoryIterator = null;
    }

    public int getHistoryTotalSize() {
        return MAX_HISTORY_BUFFER;
    }

    public int getHistoryUsedSize() {
        return mHistoryBuffer.dataSize();
    }

    @Override
    public boolean startIteratingHistoryLocked() {
        if (DEBUG_HISTORY) Slog.i(TAG, "ITERATING: buff size=" + mHistoryBuffer.dataSize()
                + " pos=" + mHistoryBuffer.dataPosition());
        if (mHistoryBuffer.dataSize() <= 0) {
            return false;
        }
        mHistoryBuffer.setDataPosition(0);
        mReadOverflow = false;
        mIteratingHistory = true;
        mReadHistoryStrings = new String[mHistoryTagPool.size()];
        mReadHistoryUids = new int[mHistoryTagPool.size()];
        mReadHistoryChars = 0;
        for (HashMap.Entry<HistoryTag, Integer> ent : mHistoryTagPool.entrySet()) {
            final HistoryTag tag = ent.getKey();
            final int idx = ent.getValue();
            mReadHistoryStrings[idx] = tag.string;
            mReadHistoryUids[idx] = tag.uid;
            mReadHistoryChars += tag.string.length() + 1;
        }
        return true;
    }

    @Override
    public int getHistoryStringPoolSize() {
        return mReadHistoryStrings.length;
    }

    @Override
    public int getHistoryStringPoolBytes() {
        // Each entry is a fixed 12 bytes: 4 for index, 4 for uid, 4 for string size
        // Each string character is 2 bytes.
        return (mReadHistoryStrings.length * 12) + (mReadHistoryChars * 2);
    }

    @Override
    public String getHistoryTagPoolString(int index) {
        return mReadHistoryStrings[index];
    }

    @Override
    public int getHistoryTagPoolUid(int index) {
        return mReadHistoryUids[index];
    }

    @Override
    public boolean getNextHistoryLocked(HistoryItem out) {
        final int pos = mHistoryBuffer.dataPosition();
        if (pos == 0) {
            out.clear();
        }
        boolean end = pos >= mHistoryBuffer.dataSize();
        if (end) {
            return false;
        }

        final long lastRealtime = out.time;
        final long lastWalltime = out.currentTime;
        readHistoryDelta(mHistoryBuffer, out);
        if (out.cmd != HistoryItem.CMD_CURRENT_TIME
                && out.cmd != HistoryItem.CMD_RESET && lastWalltime != 0) {
            out.currentTime = lastWalltime + (out.time - lastRealtime);
        }
        return true;
    }

    @Override
    public void finishIteratingHistoryLocked() {
        mIteratingHistory = false;
        mHistoryBuffer.setDataPosition(mHistoryBuffer.dataSize());
        mReadHistoryStrings = null;
    }

    @Override
    public long getHistoryBaseTime() {
        return mHistoryBaseTime;
    }

    @Override
    public int getStartCount() {
        return mStartCount;
    }

    public boolean isOnBattery() {
        return mOnBattery;
    }

    public boolean isScreenOn() {
        return mScreenState == Display.STATE_ON;
    }

    void initTimes(long uptime, long realtime) {
        mStartClockTime = System.currentTimeMillis();
        mOnBatteryTimeBase.init(uptime, realtime);
        mOnBatteryScreenOffTimeBase.init(uptime, realtime);
        mRealtime = 0;
        mUptime = 0;
        mRealtimeStart = realtime;
        mUptimeStart = uptime;
    }

    void initDischarge() {
        mLowDischargeAmountSinceCharge = 0;
        mHighDischargeAmountSinceCharge = 0;
        mDischargeAmountScreenOn = 0;
        mDischargeAmountScreenOnSinceCharge = 0;
        mDischargeAmountScreenOff = 0;
        mDischargeAmountScreenOffSinceCharge = 0;
        mLastDischargeStepTime = -1;
        mNumDischargeStepDurations = 0;
        mLastChargeStepTime = -1;
        mNumChargeStepDurations = 0;
    }

    public void resetAllStatsCmdLocked() {
        resetAllStatsLocked();
        final long mSecUptime = SystemClock.uptimeMillis();
        long uptime = mSecUptime * 1000;
        long mSecRealtime = SystemClock.elapsedRealtime();
        long realtime = mSecRealtime * 1000;
        mDischargeStartLevel = mHistoryCur.batteryLevel;
        pullPendingStateUpdatesLocked();
        addHistoryRecordLocked(mSecRealtime, mSecUptime);
        mDischargeCurrentLevel = mDischargeUnplugLevel = mDischargePlugLevel
                = mCurrentBatteryLevel = mHistoryCur.batteryLevel;
        mOnBatteryTimeBase.reset(uptime, realtime);
        mOnBatteryScreenOffTimeBase.reset(uptime, realtime);
        if ((mHistoryCur.states&HistoryItem.STATE_BATTERY_PLUGGED_FLAG) == 0) {
            if (mScreenState == Display.STATE_ON) {
                mDischargeScreenOnUnplugLevel = mHistoryCur.batteryLevel;
                mDischargeScreenOffUnplugLevel = 0;
            } else {
                mDischargeScreenOnUnplugLevel = 0;
                mDischargeScreenOffUnplugLevel = mHistoryCur.batteryLevel;
            }
            mDischargeAmountScreenOn = 0;
            mDischargeAmountScreenOff = 0;
        }
        initActiveHistoryEventsLocked(mSecRealtime, mSecUptime);
    }

    private void resetAllStatsLocked() {
        mStartCount = 0;
        initTimes(SystemClock.uptimeMillis() * 1000, SystemClock.elapsedRealtime() * 1000);
        mScreenOnTimer.reset(false);
        for (int i=0; i<NUM_SCREEN_BRIGHTNESS_BINS; i++) {
            mScreenBrightnessTimer[i].reset(false);
        }
        mInteractiveTimer.reset(false);
        mLowPowerModeEnabledTimer.reset(false);
        mPhoneOnTimer.reset(false);
        mAudioOnTimer.reset(false);
        mVideoOnTimer.reset(false);
        mFlashlightOnTimer.reset(false);
        for (int i=0; i<SignalStrength.NUM_SIGNAL_STRENGTH_BINS; i++) {
            mPhoneSignalStrengthsTimer[i].reset(false);
        }
        mPhoneSignalScanningTimer.reset(false);
        for (int i=0; i<NUM_DATA_CONNECTION_TYPES; i++) {
            mPhoneDataConnectionsTimer[i].reset(false);
        }
        for (int i = 0; i < NUM_NETWORK_ACTIVITY_TYPES; i++) {
            mNetworkByteActivityCounters[i].reset(false);
            mNetworkPacketActivityCounters[i].reset(false);
        }
        mMobileRadioActiveTimer.reset(false);
        mMobileRadioActivePerAppTimer.reset(false);
        mMobileRadioActiveAdjustedTime.reset(false);
        mMobileRadioActiveUnknownTime.reset(false);
        mMobileRadioActiveUnknownCount.reset(false);
        mWifiOnTimer.reset(false);
        mGlobalWifiRunningTimer.reset(false);
        for (int i=0; i<NUM_WIFI_STATES; i++) {
            mWifiStateTimer[i].reset(false);
        }
        for (int i=0; i<NUM_WIFI_SUPPL_STATES; i++) {
            mWifiSupplStateTimer[i].reset(false);
        }
        for (int i=0; i<NUM_WIFI_SIGNAL_STRENGTH_BINS; i++) {
            mWifiSignalStrengthsTimer[i].reset(false);
        }
        mBluetoothOnTimer.reset(false);
        for (int i=0; i< NUM_BLUETOOTH_STATES; i++) {
            mBluetoothStateTimer[i].reset(false);
        }
        mNumConnectivityChange = mLoadedNumConnectivityChange = mUnpluggedNumConnectivityChange = 0;

        for (int i=0; i<mUidStats.size(); i++) {
            if (mUidStats.valueAt(i).reset()) {
                mUidStats.remove(mUidStats.keyAt(i));
                i--;
            }
        }

        if (mKernelWakelockStats.size() > 0) {
            for (SamplingTimer timer : mKernelWakelockStats.values()) {
                mOnBatteryScreenOffTimeBase.remove(timer);
            }
            mKernelWakelockStats.clear();
        }

        if (mWakeupReasonStats.size() > 0) {
            for (SamplingTimer timer : mWakeupReasonStats.values()) {
                mOnBatteryTimeBase.remove(timer);
            }
            mWakeupReasonStats.clear();
        }

        initDischarge();

        clearHistoryLocked();
    }

    private void initActiveHistoryEventsLocked(long elapsedRealtimeMs, long uptimeMs) {
        for (int i=0; i<HistoryItem.EVENT_COUNT; i++) {
            if (!mRecordAllHistory && i == HistoryItem.EVENT_PROC) {
                // Not recording process starts/stops.
                continue;
            }
            HashMap<String, SparseIntArray> active = mActiveEvents.getStateForEvent(i);
            if (active == null) {
                continue;
            }
            for (HashMap.Entry<String, SparseIntArray> ent : active.entrySet()) {
                SparseIntArray uids = ent.getValue();
                for (int j=0; j<uids.size(); j++) {
                    addHistoryEventLocked(elapsedRealtimeMs, uptimeMs, i, ent.getKey(),
                            uids.keyAt(j));
                }
            }
        }
    }

    void updateDischargeScreenLevelsLocked(boolean oldScreenOn, boolean newScreenOn) {
        if (oldScreenOn) {
            int diff = mDischargeScreenOnUnplugLevel - mDischargeCurrentLevel;
            if (diff > 0) {
                mDischargeAmountScreenOn += diff;
                mDischargeAmountScreenOnSinceCharge += diff;
            }
        } else {
            int diff = mDischargeScreenOffUnplugLevel - mDischargeCurrentLevel;
            if (diff > 0) {
                mDischargeAmountScreenOff += diff;
                mDischargeAmountScreenOffSinceCharge += diff;
            }
        }
        if (newScreenOn) {
            mDischargeScreenOnUnplugLevel = mDischargeCurrentLevel;
            mDischargeScreenOffUnplugLevel = 0;
        } else {
            mDischargeScreenOnUnplugLevel = 0;
            mDischargeScreenOffUnplugLevel = mDischargeCurrentLevel;
        }
    }
    
    public void pullPendingStateUpdatesLocked() {
        updateKernelWakelocksLocked();
        updateNetworkActivityLocked(NET_UPDATE_ALL, SystemClock.elapsedRealtime());
        if (mOnBatteryInternal) {
            final boolean screenOn = mScreenState == Display.STATE_ON;
            updateDischargeScreenLevelsLocked(screenOn, screenOn);
        }
    }

    void setOnBatteryLocked(final long mSecRealtime, final long mSecUptime, final boolean onBattery,
            final int oldStatus, final int level) {
        boolean doWrite = false;
        Message m = mHandler.obtainMessage(MSG_REPORT_POWER_CHANGE);
        m.arg1 = onBattery ? 1 : 0;
        mHandler.sendMessage(m);

        final long uptime = mSecUptime * 1000;
        final long realtime = mSecRealtime * 1000;
        final boolean screenOn = mScreenState == Display.STATE_ON;
        if (onBattery) {
            // We will reset our status if we are unplugging after the
            // battery was last full, or the level is at 100, or
            // we have gone through a significant charge (from a very low
            // level to a now very high level).
            boolean reset = false;
            if (!mNoAutoReset && (oldStatus == BatteryManager.BATTERY_STATUS_FULL
                    || level >= 90
                    || (mDischargeCurrentLevel < 20 && level >= 80)
                    || (getHighDischargeAmountSinceCharge() >= 200
                            && mHistoryBuffer.dataSize() >= MAX_HISTORY_BUFFER))) {
                Slog.i(TAG, "Resetting battery stats: level=" + level + " status=" + oldStatus
                        + " dischargeLevel=" + mDischargeCurrentLevel
                        + " lowAmount=" + getLowDischargeAmountSinceCharge()
                        + " highAmount=" + getHighDischargeAmountSinceCharge());
                // Before we write, collect a snapshot of the final aggregated
                // stats to be reported in the next checkin.  Only do this if we have
                // a sufficient amount of data to make it interesting.
                if (getLowDischargeAmountSinceCharge() >= 20) {
                    final Parcel parcel = Parcel.obtain();
                    writeSummaryToParcel(parcel, true);
                    BackgroundThread.getHandler().post(new Runnable() {
                        @Override public void run() {
                            synchronized (mCheckinFile) {
                                FileOutputStream stream = null;
                                try {
                                    stream = mCheckinFile.startWrite();
                                    stream.write(parcel.marshall());
                                    stream.flush();
                                    FileUtils.sync(stream);
                                    stream.close();
                                    mCheckinFile.finishWrite(stream);
                                } catch (IOException e) {
                                    Slog.w("BatteryStats",
                                            "Error writing checkin battery statistics", e);
                                    mCheckinFile.failWrite(stream);
                                } finally {
                                    parcel.recycle();
                                }
                            }
                        }
                    });
                }
                doWrite = true;
                resetAllStatsLocked();
                mDischargeStartLevel = level;
                reset = true;
                mNumDischargeStepDurations = 0;
            }
            mOnBattery = mOnBatteryInternal = onBattery;
            mLastDischargeStepLevel = level;
            mMinDischargeStepLevel = level;
            mLastDischargeStepTime = -1;
            mInitStepMode = mCurStepMode;
            mModStepMode = 0;
            pullPendingStateUpdatesLocked();
            mHistoryCur.batteryLevel = (byte)level;
            mHistoryCur.states &= ~HistoryItem.STATE_BATTERY_PLUGGED_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "Battery unplugged to: "
                    + Integer.toHexString(mHistoryCur.states));
            if (reset) {
                mRecordingHistory = true;
                startRecordingHistory(mSecRealtime, mSecUptime, reset);
            }
            addHistoryRecordLocked(mSecRealtime, mSecUptime);
            mDischargeCurrentLevel = mDischargeUnplugLevel = level;
            if (screenOn) {
                mDischargeScreenOnUnplugLevel = level;
                mDischargeScreenOffUnplugLevel = 0;
            } else {
                mDischargeScreenOnUnplugLevel = 0;
                mDischargeScreenOffUnplugLevel = level;
            }
            mDischargeAmountScreenOn = 0;
            mDischargeAmountScreenOff = 0;
            updateTimeBasesLocked(true, !screenOn, uptime, realtime);
        } else {
            mOnBattery = mOnBatteryInternal = onBattery;
            pullPendingStateUpdatesLocked();
            mHistoryCur.batteryLevel = (byte)level;
            mHistoryCur.states |= HistoryItem.STATE_BATTERY_PLUGGED_FLAG;
            if (DEBUG_HISTORY) Slog.v(TAG, "Battery plugged to: "
                    + Integer.toHexString(mHistoryCur.states));
            addHistoryRecordLocked(mSecRealtime, mSecUptime);
            mDischargeCurrentLevel = mDischargePlugLevel = level;
            if (level < mDischargeUnplugLevel) {
                mLowDischargeAmountSinceCharge += mDischargeUnplugLevel-level-1;
                mHighDischargeAmountSinceCharge += mDischargeUnplugLevel-level;
            }
            updateDischargeScreenLevelsLocked(screenOn, screenOn);
            updateTimeBasesLocked(false, !screenOn, uptime, realtime);
            mNumChargeStepDurations = 0;
            mLastChargeStepLevel = level;
            mMaxChargeStepLevel = level;
            mLastChargeStepTime = -1;
            mInitStepMode = mCurStepMode;
            mModStepMode = 0;
        }
        if (doWrite || (mLastWriteTime + (60 * 1000)) < mSecRealtime) {
            if (mFile != null) {
                writeAsyncLocked();
            }
        }
    }

    private void startRecordingHistory(final long elapsedRealtimeMs, final long uptimeMs,
            boolean reset) {
        mRecordingHistory = true;
        mHistoryCur.currentTime = System.currentTimeMillis();
        mLastRecordedClockTime = mHistoryCur.currentTime;
        mLastRecordedClockRealtime = elapsedRealtimeMs;
        addHistoryBufferLocked(elapsedRealtimeMs, uptimeMs,
                reset ? HistoryItem.CMD_RESET : HistoryItem.CMD_CURRENT_TIME,
                mHistoryCur);
        mHistoryCur.currentTime = 0;
        if (reset) {
            initActiveHistoryEventsLocked(elapsedRealtimeMs, uptimeMs);
        }
    }

    private void recordCurrentTimeChangeLocked(final long currentTime, final long elapsedRealtimeMs,
            final long uptimeMs) {
        if (mRecordingHistory) {
            mHistoryCur.currentTime = currentTime;
            mLastRecordedClockTime = currentTime;
            mLastRecordedClockRealtime = elapsedRealtimeMs;
            addHistoryBufferLocked(elapsedRealtimeMs, uptimeMs, HistoryItem.CMD_CURRENT_TIME,
                    mHistoryCur);
            mHistoryCur.currentTime = 0;
        }
    }

    private void recordShutdownLocked(final long elapsedRealtimeMs, final long uptimeMs) {
        if (mRecordingHistory) {
            mHistoryCur.currentTime = System.currentTimeMillis();
            mLastRecordedClockTime = mHistoryCur.currentTime;
            mLastRecordedClockRealtime = elapsedRealtimeMs;
            addHistoryBufferLocked(elapsedRealtimeMs, uptimeMs, HistoryItem.CMD_SHUTDOWN,
                    mHistoryCur);
            mHistoryCur.currentTime = 0;
        }
    }

    // This should probably be exposed in the API, though it's not critical
    private static final int BATTERY_PLUGGED_NONE = 0;

    private static int addLevelSteps(long[] steps, int stepCount, long lastStepTime,
            int numStepLevels, long modeBits, long elapsedRealtime) {
        if (lastStepTime >= 0 && numStepLevels > 0) {
            long duration = elapsedRealtime - lastStepTime;
            for (int i=0; i<numStepLevels; i++) {
                System.arraycopy(steps, 0, steps, 1, steps.length-1);
                long thisDuration = duration / (numStepLevels-i);
                duration -= thisDuration;
                if (thisDuration > STEP_LEVEL_TIME_MASK) {
                    thisDuration = STEP_LEVEL_TIME_MASK;
                }
                steps[0] = thisDuration | modeBits;
            }
            stepCount += numStepLevels;
            if (stepCount > steps.length) {
                stepCount = steps.length;
            }
        }
        return stepCount;
    }

    public void setBatteryState(int status, int health, int plugType, int level,
            int temp, int volt) {
        synchronized(this) {
            final boolean onBattery = plugType == BATTERY_PLUGGED_NONE;
            final long uptime = SystemClock.uptimeMillis();
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            int oldStatus = mHistoryCur.batteryStatus;
            if (!mHaveBatteryLevel) {
                mHaveBatteryLevel = true;
                // We start out assuming that the device is plugged in (not
                // on battery).  If our first report is now that we are indeed
                // plugged in, then twiddle our state to correctly reflect that
                // since we won't be going through the full setOnBattery().
                if (onBattery == mOnBattery) {
                    if (onBattery) {
                        mHistoryCur.states &= ~HistoryItem.STATE_BATTERY_PLUGGED_FLAG;
                    } else {
                        mHistoryCur.states |= HistoryItem.STATE_BATTERY_PLUGGED_FLAG;
                    }
                }
                oldStatus = status;
            }
            if (onBattery) {
                mDischargeCurrentLevel = level;
                if (!mRecordingHistory) {
                    mRecordingHistory = true;
                    startRecordingHistory(elapsedRealtime, uptime, true);
                }
            } else if (level < 96) {
                if (!mRecordingHistory) {
                    mRecordingHistory = true;
                    startRecordingHistory(elapsedRealtime, uptime, true);
                }
            }
            mCurrentBatteryLevel = level;
            if (mDischargePlugLevel < 0) {
                mDischargePlugLevel = level;
            }
            if (onBattery != mOnBattery) {
                mHistoryCur.batteryLevel = (byte)level;
                mHistoryCur.batteryStatus = (byte)status;
                mHistoryCur.batteryHealth = (byte)health;
                mHistoryCur.batteryPlugType = (byte)plugType;
                mHistoryCur.batteryTemperature = (short)temp;
                mHistoryCur.batteryVoltage = (char)volt;
                setOnBatteryLocked(elapsedRealtime, uptime, onBattery, oldStatus, level);
            } else {
                boolean changed = false;
                if (mHistoryCur.batteryLevel != level) {
                    mHistoryCur.batteryLevel = (byte)level;
                    changed = true;
                }
                if (mHistoryCur.batteryStatus != status) {
                    mHistoryCur.batteryStatus = (byte)status;
                    changed = true;
                }
                if (mHistoryCur.batteryHealth != health) {
                    mHistoryCur.batteryHealth = (byte)health;
                    changed = true;
                }
                if (mHistoryCur.batteryPlugType != plugType) {
                    mHistoryCur.batteryPlugType = (byte)plugType;
                    changed = true;
                }
                if (temp >= (mHistoryCur.batteryTemperature+10)
                        || temp <= (mHistoryCur.batteryTemperature-10)) {
                    mHistoryCur.batteryTemperature = (short)temp;
                    changed = true;
                }
                if (volt > (mHistoryCur.batteryVoltage+20)
                        || volt < (mHistoryCur.batteryVoltage-20)) {
                    mHistoryCur.batteryVoltage = (char)volt;
                    changed = true;
                }
                if (changed) {
                    addHistoryRecordLocked(elapsedRealtime, uptime);
                }
                long modeBits = (((long)mInitStepMode) << STEP_LEVEL_INITIAL_MODE_SHIFT)
                        | (((long)mModStepMode) << STEP_LEVEL_MODIFIED_MODE_SHIFT)
                        | (((long)(level&0xff)) << STEP_LEVEL_LEVEL_SHIFT);
                if (onBattery) {
                    if (mLastDischargeStepLevel != level && mMinDischargeStepLevel > level) {
                        mNumDischargeStepDurations = addLevelSteps(mDischargeStepDurations,
                                mNumDischargeStepDurations, mLastDischargeStepTime,
                                mLastDischargeStepLevel - level, modeBits, elapsedRealtime);
                        mLastDischargeStepLevel = level;
                        mMinDischargeStepLevel = level;
                        mLastDischargeStepTime = elapsedRealtime;
                        mInitStepMode = mCurStepMode;
                        mModStepMode = 0;
                    }
                } else {
                    if (mLastChargeStepLevel != level && mMaxChargeStepLevel < level) {
                        mNumChargeStepDurations = addLevelSteps(mChargeStepDurations,
                                mNumChargeStepDurations, mLastChargeStepTime,
                                level - mLastChargeStepLevel, modeBits, elapsedRealtime);
                        mLastChargeStepLevel = level;
                        mMaxChargeStepLevel = level;
                        mLastChargeStepTime = elapsedRealtime;
                        mInitStepMode = mCurStepMode;
                        mModStepMode = 0;
                    }
                }
            }
            if (!onBattery && status == BatteryManager.BATTERY_STATUS_FULL) {
                // We don't record history while we are plugged in and fully charged.
                // The next time we are unplugged, history will be cleared.
                mRecordingHistory = DEBUG;
            }
        }
    }

    public void updateKernelWakelocksLocked() {
        Map<String, KernelWakelockStats> m = readKernelWakelockStats();

        if (m == null) {
            // Not crashing might make board bringup easier.
            Slog.w(TAG, "Couldn't get kernel wake lock stats");
            return;
        }

        for (Map.Entry<String, KernelWakelockStats> ent : m.entrySet()) {
            String name = ent.getKey();
            KernelWakelockStats kws = ent.getValue();

            SamplingTimer kwlt = mKernelWakelockStats.get(name);
            if (kwlt == null) {
                kwlt = new SamplingTimer(mOnBatteryScreenOffTimeBase,
                        true /* track reported val */);
                mKernelWakelockStats.put(name, kwlt);
            }
            kwlt.updateCurrentReportedCount(kws.mCount);
            kwlt.updateCurrentReportedTotalTime(kws.mTotalTime);
            kwlt.setUpdateVersion(sKernelWakelockUpdateVersion);
        }

        if (m.size() != mKernelWakelockStats.size()) {
            // Set timers to stale if they didn't appear in /proc/wakelocks this time.
            for (Map.Entry<String, SamplingTimer> ent : mKernelWakelockStats.entrySet()) {
                SamplingTimer st = ent.getValue();
                if (st.getUpdateVersion() != sKernelWakelockUpdateVersion) {
                    st.setStale();
                }
            }
        }
    }

    static final int NET_UPDATE_MOBILE = 1<<0;
    static final int NET_UPDATE_WIFI = 1<<1;
    static final int NET_UPDATE_ALL = 0xffff;

    private void updateNetworkActivityLocked(int which, long elapsedRealtimeMs) {
        if (!SystemProperties.getBoolean(PROP_QTAGUID_ENABLED, false)) return;

        if ((which&NET_UPDATE_MOBILE) != 0 && mMobileIfaces.length > 0) {
            final NetworkStats snapshot;
            final NetworkStats last = mCurMobileSnapshot;
            try {
                snapshot = mNetworkStatsFactory.readNetworkStatsDetail(UID_ALL,
                        mMobileIfaces, NetworkStats.TAG_NONE, mLastMobileSnapshot);
            } catch (IOException e) {
                Log.wtf(TAG, "Failed to read mobile network stats", e);
                return;
            }

            mCurMobileSnapshot = snapshot;
            mLastMobileSnapshot = last;

            if (mOnBatteryInternal) {
                final NetworkStats delta = NetworkStats.subtract(snapshot, last,
                        null, null, mTmpNetworkStats);
                mTmpNetworkStats = delta;

                long radioTime = mMobileRadioActivePerAppTimer.checkpointRunningLocked(
                        elapsedRealtimeMs);
                long totalPackets = delta.getTotalPackets();

                final int size = delta.size();
                for (int i = 0; i < size; i++) {
                    final NetworkStats.Entry entry = delta.getValues(i, mTmpNetworkStatsEntry);

                    if (entry.rxBytes == 0 || entry.txBytes == 0) continue;

                    final Uid u = getUidStatsLocked(mapUid(entry.uid));
                    u.noteNetworkActivityLocked(NETWORK_MOBILE_RX_DATA, entry.rxBytes,
                            entry.rxPackets);
                    u.noteNetworkActivityLocked(NETWORK_MOBILE_TX_DATA, entry.txBytes,
                            entry.txPackets);

                    if (radioTime > 0) {
                        // Distribute total radio active time in to this app.
                        long appPackets = entry.rxPackets + entry.txPackets;
                        long appRadioTime = (radioTime*appPackets)/totalPackets;
                        u.noteMobileRadioActiveTimeLocked(appRadioTime);
                        // Remove this app from the totals, so that we don't lose any time
                        // due to rounding.
                        radioTime -= appRadioTime;
                        totalPackets -= appPackets;
                    }

                    mNetworkByteActivityCounters[NETWORK_MOBILE_RX_DATA].addCountLocked(
                            entry.rxBytes);
                    mNetworkByteActivityCounters[NETWORK_MOBILE_TX_DATA].addCountLocked(
                            entry.txBytes);
                    mNetworkPacketActivityCounters[NETWORK_MOBILE_RX_DATA].addCountLocked(
                            entry.rxPackets);
                    mNetworkPacketActivityCounters[NETWORK_MOBILE_TX_DATA].addCountLocked(
                            entry.txPackets);
                }

                if (radioTime > 0) {
                    // Whoops, there is some radio time we can't blame on an app!
                    mMobileRadioActiveUnknownTime.addCountLocked(radioTime);
                    mMobileRadioActiveUnknownCount.addCountLocked(1);
                }
            }
        }

        if ((which&NET_UPDATE_WIFI) != 0 && mWifiIfaces.length > 0) {
            final NetworkStats snapshot;
            final NetworkStats last = mCurWifiSnapshot;
            try {
                snapshot = mNetworkStatsFactory.readNetworkStatsDetail(UID_ALL,
                        mWifiIfaces, NetworkStats.TAG_NONE, mLastWifiSnapshot);
            } catch (IOException e) {
                Log.wtf(TAG, "Failed to read wifi network stats", e);
                return;
            }

            mCurWifiSnapshot = snapshot;
            mLastWifiSnapshot = last;

            if (mOnBatteryInternal) {
                final NetworkStats delta = NetworkStats.subtract(snapshot, last,
                        null, null, mTmpNetworkStats);
                mTmpNetworkStats = delta;

                final int size = delta.size();
                for (int i = 0; i < size; i++) {
                    final NetworkStats.Entry entry = delta.getValues(i, mTmpNetworkStatsEntry);

                    if (DEBUG) {
                        final NetworkStats.Entry cur = snapshot.getValues(i, null);
                        Slog.d(TAG, "Wifi uid " + entry.uid + ": delta rx=" + entry.rxBytes
                                + " tx=" + entry.txBytes + ", cur rx=" + cur.rxBytes
                                + " tx=" + cur.txBytes);
                    }

                    if (entry.rxBytes == 0 || entry.txBytes == 0) continue;

                    final Uid u = getUidStatsLocked(mapUid(entry.uid));
                    u.noteNetworkActivityLocked(NETWORK_WIFI_RX_DATA, entry.rxBytes,
                            entry.rxPackets);
                    u.noteNetworkActivityLocked(NETWORK_WIFI_TX_DATA, entry.txBytes,
                            entry.txPackets);

                    mNetworkByteActivityCounters[NETWORK_WIFI_RX_DATA].addCountLocked(
                            entry.rxBytes);
                    mNetworkByteActivityCounters[NETWORK_WIFI_TX_DATA].addCountLocked(
                            entry.txBytes);
                    mNetworkPacketActivityCounters[NETWORK_WIFI_RX_DATA].addCountLocked(
                            entry.rxPackets);
                    mNetworkPacketActivityCounters[NETWORK_WIFI_TX_DATA].addCountLocked(
                            entry.txPackets);
                }
            }
        }
    }

    public long getAwakeTimeBattery() {
        return computeBatteryUptime(getBatteryUptimeLocked(), STATS_CURRENT);
    }

    public long getAwakeTimePlugged() {
        return (SystemClock.uptimeMillis() * 1000) - getAwakeTimeBattery();
    }

    @Override
    public long computeUptime(long curTime, int which) {
        switch (which) {
            case STATS_SINCE_CHARGED: return mUptime + (curTime-mUptimeStart);
            case STATS_CURRENT: return (curTime-mUptimeStart);
            case STATS_SINCE_UNPLUGGED: return (curTime-mOnBatteryTimeBase.getUptimeStart());
        }
        return 0;
    }

    @Override
    public long computeRealtime(long curTime, int which) {
        switch (which) {
            case STATS_SINCE_CHARGED: return mRealtime + (curTime-mRealtimeStart);
            case STATS_CURRENT: return (curTime-mRealtimeStart);
            case STATS_SINCE_UNPLUGGED: return (curTime-mOnBatteryTimeBase.getRealtimeStart());
        }
        return 0;
    }

    @Override
    public long computeBatteryUptime(long curTime, int which) {
        return mOnBatteryTimeBase.computeUptime(curTime, which);
    }

    @Override
    public long computeBatteryRealtime(long curTime, int which) {
        return mOnBatteryTimeBase.computeRealtime(curTime, which);
    }

    @Override
    public long computeBatteryScreenOffUptime(long curTime, int which) {
        return mOnBatteryScreenOffTimeBase.computeUptime(curTime, which);
    }

    @Override
    public long computeBatteryScreenOffRealtime(long curTime, int which) {
        return mOnBatteryScreenOffTimeBase.computeRealtime(curTime, which);
    }

    private long computeTimePerLevel(long[] steps, int numSteps) {
        // For now we'll do a simple average across all steps.
        if (numSteps <= 0) {
            return -1;
        }
        long total = 0;
        for (int i=0; i<numSteps; i++) {
            total += steps[i] & STEP_LEVEL_TIME_MASK;
        }
        return total / numSteps;
        /*
        long[] buckets = new long[numSteps];
        int numBuckets = 0;
        int numToAverage = 4;
        int i = 0;
        while (i < numSteps) {
            long totalTime = 0;
            int num = 0;
            for (int j=0; j<numToAverage && (i+j)<numSteps; j++) {
                totalTime += steps[i+j] & STEP_LEVEL_TIME_MASK;
                num++;
            }
            buckets[numBuckets] = totalTime / num;
            numBuckets++;
            numToAverage *= 2;
            i += num;
        }
        if (numBuckets < 1) {
            return -1;
        }
        long averageTime = buckets[numBuckets-1];
        for (i=numBuckets-2; i>=0; i--) {
            averageTime = (averageTime + buckets[i]) / 2;
        }
        return averageTime;
        */
    }

    @Override
    public long computeBatteryTimeRemaining(long curTime) {
        if (!mOnBattery) {
            return -1;
        }
        /* Simple implementation just looks at the average discharge per level across the
           entire sample period.
        int discharge = (getLowDischargeAmountSinceCharge()+getHighDischargeAmountSinceCharge())/2;
        if (discharge < 2) {
            return -1;
        }
        long duration = computeBatteryRealtime(curTime, STATS_SINCE_CHARGED);
        if (duration < 1000*1000) {
            return -1;
        }
        long usPerLevel = duration/discharge;
        return usPerLevel * mCurrentBatteryLevel;
        */
        if (mNumDischargeStepDurations < 1) {
            return -1;
        }
        long msPerLevel = computeTimePerLevel(mDischargeStepDurations, mNumDischargeStepDurations);
        if (msPerLevel <= 0) {
            return -1;
        }
        return (msPerLevel * mCurrentBatteryLevel) * 1000;
    }

    public int getNumDischargeStepDurations() {
        return mNumDischargeStepDurations;
    }

    public long[] getDischargeStepDurationsArray() {
        return mDischargeStepDurations;
    }

    @Override
    public long computeChargeTimeRemaining(long curTime) {
        if (mOnBattery) {
            // Not yet working.
            return -1;
        }
        /* Broken
        int curLevel = mCurrentBatteryLevel;
        int plugLevel = mDischargePlugLevel;
        if (plugLevel < 0 || curLevel < (plugLevel+1)) {
            return -1;
        }
        long duration = computeBatteryRealtime(curTime, STATS_SINCE_UNPLUGGED);
        if (duration < 1000*1000) {
            return -1;
        }
        long usPerLevel = duration/(curLevel-plugLevel);
        return usPerLevel * (100-curLevel);
        */
        if (mNumChargeStepDurations < 1) {
            return -1;
        }
        long msPerLevel = computeTimePerLevel(mChargeStepDurations, mNumChargeStepDurations);
        if (msPerLevel <= 0) {
            return -1;
        }
        return (msPerLevel * (100-mCurrentBatteryLevel)) * 1000;
    }

    public int getNumChargeStepDurations() {
        return mNumChargeStepDurations;
    }

    public long[] getChargeStepDurationsArray() {
        return mChargeStepDurations;
    }

    long getBatteryUptimeLocked() {
        return mOnBatteryTimeBase.getUptime(SystemClock.uptimeMillis() * 1000);
    }

    @Override
    public long getBatteryUptime(long curTime) {
        return mOnBatteryTimeBase.getUptime(curTime);
    }

    @Override
    public long getBatteryRealtime(long curTime) {
        return mOnBatteryTimeBase.getRealtime(curTime);
    }

    @Override
    public int getDischargeStartLevel() {
        synchronized(this) {
            return getDischargeStartLevelLocked();
        }
    }

    public int getDischargeStartLevelLocked() {
            return mDischargeUnplugLevel;
    }

    @Override
    public int getDischargeCurrentLevel() {
        synchronized(this) {
            return getDischargeCurrentLevelLocked();
        }
    }

    public int getDischargeCurrentLevelLocked() {
        return mDischargeCurrentLevel;
    }

    @Override
    public int getLowDischargeAmountSinceCharge() {
        synchronized(this) {
            int val = mLowDischargeAmountSinceCharge;
            if (mOnBattery && mDischargeCurrentLevel < mDischargeUnplugLevel) {
                val += mDischargeUnplugLevel-mDischargeCurrentLevel-1;
            }
            return val;
        }
    }

    @Override
    public int getHighDischargeAmountSinceCharge() {
        synchronized(this) {
            int val = mHighDischargeAmountSinceCharge;
            if (mOnBattery && mDischargeCurrentLevel < mDischargeUnplugLevel) {
                val += mDischargeUnplugLevel-mDischargeCurrentLevel;
            }
            return val;
        }
    }

    @Override
    public int getDischargeAmount(int which) {
        int dischargeAmount = which == STATS_SINCE_CHARGED
                ? getHighDischargeAmountSinceCharge()
                : (getDischargeStartLevel() - getDischargeCurrentLevel());
        if (dischargeAmount < 0) {
            dischargeAmount = 0;
        }
        return dischargeAmount;
    }

    public int getDischargeAmountScreenOn() {
        synchronized(this) {
            int val = mDischargeAmountScreenOn;
            if (mOnBattery && mScreenState == Display.STATE_ON
                    && mDischargeCurrentLevel < mDischargeScreenOnUnplugLevel) {
                val += mDischargeScreenOnUnplugLevel-mDischargeCurrentLevel;
            }
            return val;
        }
    }

    public int getDischargeAmountScreenOnSinceCharge() {
        synchronized(this) {
            int val = mDischargeAmountScreenOnSinceCharge;
            if (mOnBattery && mScreenState == Display.STATE_ON
                    && mDischargeCurrentLevel < mDischargeScreenOnUnplugLevel) {
                val += mDischargeScreenOnUnplugLevel-mDischargeCurrentLevel;
            }
            return val;
        }
    }

    public int getDischargeAmountScreenOff() {
        synchronized(this) {
            int val = mDischargeAmountScreenOff;
            if (mOnBattery && mScreenState != Display.STATE_ON
                    && mDischargeCurrentLevel < mDischargeScreenOffUnplugLevel) {
                val += mDischargeScreenOffUnplugLevel-mDischargeCurrentLevel;
            }
            return val;
        }
    }

    public int getDischargeAmountScreenOffSinceCharge() {
        synchronized(this) {
            int val = mDischargeAmountScreenOffSinceCharge;
            if (mOnBattery && mScreenState != Display.STATE_ON
                    && mDischargeCurrentLevel < mDischargeScreenOffUnplugLevel) {
                val += mDischargeScreenOffUnplugLevel-mDischargeCurrentLevel;
            }
            return val;
        }
    }

    @Override
    public int getCpuSpeedSteps() {
        return sNumSpeedSteps;
    }

    /**
     * Retrieve the statistics object for a particular uid, creating if needed.
     */
    public Uid getUidStatsLocked(int uid) {
        Uid u = mUidStats.get(uid);
        if (u == null) {
            u = new Uid(uid);
            mUidStats.put(uid, u);
        }
        return u;
    }

    /**
     * Remove the statistics object for a particular uid.
     */
    public void removeUidStatsLocked(int uid) {
        mUidStats.remove(uid);
    }

    /**
     * Retrieve the statistics object for a particular process, creating
     * if needed.
     */
    public Uid.Proc getProcessStatsLocked(int uid, String name) {
        uid = mapUid(uid);
        Uid u = getUidStatsLocked(uid);
        return u.getProcessStatsLocked(name);
    }

    /**
     * Retrieve the statistics object for a particular process, creating
     * if needed.
     */
    public Uid.Pkg getPackageStatsLocked(int uid, String pkg) {
        uid = mapUid(uid);
        Uid u = getUidStatsLocked(uid);
        return u.getPackageStatsLocked(pkg);
    }

    /**
     * Retrieve the statistics object for a particular service, creating
     * if needed.
     */
    public Uid.Pkg.Serv getServiceStatsLocked(int uid, String pkg, String name) {
        uid = mapUid(uid);
        Uid u = getUidStatsLocked(uid);
        return u.getServiceStatsLocked(pkg, name);
    }

    /**
     * Massage data to distribute any reasonable work down to more specific
     * owners.  Must only be called on a dead BatteryStats object!
     */
    public void distributeWorkLocked(int which) {
        // Aggregate all CPU time associated with WIFI.
        Uid wifiUid = mUidStats.get(Process.WIFI_UID);
        if (wifiUid != null) {
            long uSecTime = computeBatteryRealtime(SystemClock.elapsedRealtime() * 1000, which);
            for (int ip=wifiUid.mProcessStats.size()-1; ip>=0; ip--) {
                Uid.Proc proc = wifiUid.mProcessStats.valueAt(ip);
                long totalRunningTime = getGlobalWifiRunningTime(uSecTime, which);
                for (int i=0; i<mUidStats.size(); i++) {
                    Uid uid = mUidStats.valueAt(i);
                    if (uid.mUid != Process.WIFI_UID) {
                        long uidRunningTime = uid.getWifiRunningTime(uSecTime, which);
                        if (uidRunningTime > 0) {
                            Uid.Proc uidProc = uid.getProcessStatsLocked("*wifi*");
                            long time = proc.getUserTime(which);
                            time = (time*uidRunningTime)/totalRunningTime;
                            uidProc.mUserTime += time;
                            proc.mUserTime -= time;
                            time = proc.getSystemTime(which);
                            time = (time*uidRunningTime)/totalRunningTime;
                            uidProc.mSystemTime += time;
                            proc.mSystemTime -= time;
                            time = proc.getForegroundTime(which);
                            time = (time*uidRunningTime)/totalRunningTime;
                            uidProc.mForegroundTime += time;
                            proc.mForegroundTime -= time;
                            for (int sb=0; sb<proc.mSpeedBins.length; sb++) {
                                SamplingCounter sc = proc.mSpeedBins[sb];
                                if (sc != null) {
                                    time = sc.getCountLocked(which);
                                    time = (time*uidRunningTime)/totalRunningTime;
                                    SamplingCounter uidSc = uidProc.mSpeedBins[sb];
                                    if (uidSc == null) {
                                        uidSc = new SamplingCounter(mOnBatteryTimeBase);
                                        uidProc.mSpeedBins[sb] = uidSc;
                                    }
                                    uidSc.mCount.addAndGet((int)time);
                                    sc.mCount.addAndGet((int)-time);
                                }
                            }
                            totalRunningTime -= uidRunningTime;
                        }
                    }
                }
            }
        }
    }

    public void shutdownLocked() {
        recordShutdownLocked(SystemClock.elapsedRealtime(), SystemClock.uptimeMillis());
        writeSyncLocked();
        mShuttingDown = true;
    }

    Parcel mPendingWrite = null;
    final ReentrantLock mWriteLock = new ReentrantLock();

    public void writeAsyncLocked() {
        writeLocked(false);
    }

    public void writeSyncLocked() {
        writeLocked(true);
    }

    void writeLocked(boolean sync) {
        if (mFile == null) {
            Slog.w("BatteryStats", "writeLocked: no file associated with this instance");
            return;
        }

        if (mShuttingDown) {
            return;
        }

        Parcel out = Parcel.obtain();
        writeSummaryToParcel(out, true);
        mLastWriteTime = SystemClock.elapsedRealtime();

        if (mPendingWrite != null) {
            mPendingWrite.recycle();
        }
        mPendingWrite = out;

        if (sync) {
            commitPendingDataToDisk();
        } else {
            BackgroundThread.getHandler().post(new Runnable() {
                @Override public void run() {
                    commitPendingDataToDisk();
                }
            });
        }
    }

    public void commitPendingDataToDisk() {
        final Parcel next;
        synchronized (this) {
            next = mPendingWrite;
            mPendingWrite = null;
            if (next == null) {
                return;
            }

            mWriteLock.lock();
        }

        try {
            FileOutputStream stream = new FileOutputStream(mFile.chooseForWrite());
            stream.write(next.marshall());
            stream.flush();
            FileUtils.sync(stream);
            stream.close();
            mFile.commit();
        } catch (IOException e) {
            Slog.w("BatteryStats", "Error writing battery statistics", e);
            mFile.rollback();
        } finally {
            next.recycle();
            mWriteLock.unlock();
        }
    }

    public void readLocked() {
        if (mFile == null) {
            Slog.w("BatteryStats", "readLocked: no file associated with this instance");
            return;
        }

        mUidStats.clear();

        try {
            File file = mFile.chooseForRead();
            if (!file.exists()) {
                return;
            }
            FileInputStream stream = new FileInputStream(file);

            byte[] raw = BatteryStatsHelper.readFully(stream);
            Parcel in = Parcel.obtain();
            in.unmarshall(raw, 0, raw.length);
            in.setDataPosition(0);
            stream.close();

            readSummaryFromParcel(in);
        } catch(Exception e) {
            Slog.e("BatteryStats", "Error reading battery statistics", e);
        }

        mEndPlatformVersion = Build.ID;

        if (mHistoryBuffer.dataPosition() > 0) {
            mRecordingHistory = true;
            final long elapsedRealtime = SystemClock.elapsedRealtime();
            final long uptime = SystemClock.uptimeMillis();
            if (USE_OLD_HISTORY) {
                addHistoryRecordLocked(elapsedRealtime, uptime, HistoryItem.CMD_START, mHistoryCur);
            }
            addHistoryBufferLocked(elapsedRealtime, uptime, HistoryItem.CMD_START, mHistoryCur);
            startRecordingHistory(elapsedRealtime, uptime, false);
        }
    }

    public int describeContents() {
        return 0;
    }

    void readHistory(Parcel in, boolean andOldHistory) {
        final long historyBaseTime = in.readLong();

        mHistoryBuffer.setDataSize(0);
        mHistoryBuffer.setDataPosition(0);
        mHistoryTagPool.clear();
        mNextHistoryTagIdx = 0;
        mNumHistoryTagChars = 0;

        int numTags = in.readInt();
        for (int i=0; i<numTags; i++) {
            int idx = in.readInt();
            String str = in.readString();
            int uid = in.readInt();
            HistoryTag tag = new HistoryTag();
            tag.string = str;
            tag.uid = uid;
            tag.poolIdx = idx;
            mHistoryTagPool.put(tag, idx);
            if (idx >= mNextHistoryTagIdx) {
                mNextHistoryTagIdx = idx+1;
            }
            mNumHistoryTagChars += tag.string.length() + 1;
        }

        int bufSize = in.readInt();
        int curPos = in.dataPosition();
        if (bufSize >= (MAX_MAX_HISTORY_BUFFER*3)) {
            Slog.w(TAG, "File corrupt: history data buffer too large " + bufSize);
        } else if ((bufSize&~3) != bufSize) {
            Slog.w(TAG, "File corrupt: history data buffer not aligned " + bufSize);
        } else {
            if (DEBUG_HISTORY) Slog.i(TAG, "***************** READING NEW HISTORY: " + bufSize
                    + " bytes at " + curPos);
            mHistoryBuffer.appendFrom(in, curPos, bufSize);
            in.setDataPosition(curPos + bufSize);
        }

        if (andOldHistory) {
            readOldHistory(in);
        }

        if (DEBUG_HISTORY) {
            StringBuilder sb = new StringBuilder(128);
            sb.append("****************** OLD mHistoryBaseTime: ");
            TimeUtils.formatDuration(mHistoryBaseTime, sb);
            Slog.i(TAG, sb.toString());
        }
        mHistoryBaseTime = historyBaseTime;
        if (DEBUG_HISTORY) {
            StringBuilder sb = new StringBuilder(128);
            sb.append("****************** NEW mHistoryBaseTime: ");
            TimeUtils.formatDuration(mHistoryBaseTime, sb);
            Slog.i(TAG, sb.toString());
        }

        // We are just arbitrarily going to insert 1 minute from the sample of
        // the last run until samples in this run.
        if (mHistoryBaseTime > 0) {
            long oldnow = SystemClock.elapsedRealtime();
            mHistoryBaseTime = mHistoryBaseTime - oldnow + 1;
            if (DEBUG_HISTORY) {
                StringBuilder sb = new StringBuilder(128);
                sb.append("****************** ADJUSTED mHistoryBaseTime: ");
                TimeUtils.formatDuration(mHistoryBaseTime, sb);
                Slog.i(TAG, sb.toString());
            }
        }
    }

    void readOldHistory(Parcel in) {
        if (!USE_OLD_HISTORY) {
            return;
        }
        mHistory = mHistoryEnd = mHistoryCache = null;
        long time;
        while (in.dataAvail() > 0 && (time=in.readLong()) >= 0) {
            HistoryItem rec = new HistoryItem(time, in);
            addHistoryRecordLocked(rec);
        }
    }

    void writeHistory(Parcel out, boolean inclData, boolean andOldHistory) {
        if (DEBUG_HISTORY) {
            StringBuilder sb = new StringBuilder(128);
            sb.append("****************** WRITING mHistoryBaseTime: ");
            TimeUtils.formatDuration(mHistoryBaseTime, sb);
            sb.append(" mLastHistoryElapsedRealtime: ");
            TimeUtils.formatDuration(mLastHistoryElapsedRealtime, sb);
            Slog.i(TAG, sb.toString());
        }
        out.writeLong(mHistoryBaseTime + mLastHistoryElapsedRealtime);
        if (!inclData) {
            out.writeInt(0);
            out.writeInt(0);
            return;
        }
        out.writeInt(mHistoryTagPool.size());
        for (HashMap.Entry<HistoryTag, Integer> ent : mHistoryTagPool.entrySet()) {
            HistoryTag tag = ent.getKey();
            out.writeInt(ent.getValue());
            out.writeString(tag.string);
            out.writeInt(tag.uid);
        }
        out.writeInt(mHistoryBuffer.dataSize());
        if (DEBUG_HISTORY) Slog.i(TAG, "***************** WRITING HISTORY: "
                + mHistoryBuffer.dataSize() + " bytes at " + out.dataPosition());
        out.appendFrom(mHistoryBuffer, 0, mHistoryBuffer.dataSize());

        if (andOldHistory) {
            writeOldHistory(out);
        }
    }

    void writeOldHistory(Parcel out) {
        if (!USE_OLD_HISTORY) {
            return;
        }
        HistoryItem rec = mHistory;
        while (rec != null) {
            if (rec.time >= 0) rec.writeToParcel(out, 0);
            rec = rec.next;
        }
        out.writeLong(-1);
    }

    public void readSummaryFromParcel(Parcel in) {
        final int version = in.readInt();
        if (version != VERSION) {
            Slog.w("BatteryStats", "readFromParcel: version got " + version
                + ", expected " + VERSION + "; erasing old stats");
            return;
        }

        readHistory(in, true);

        mStartCount = in.readInt();
        mUptime = in.readLong();
        mRealtime = in.readLong();
        mStartClockTime = in.readLong();
        mStartPlatformVersion = in.readString();
        mEndPlatformVersion = in.readString();
        mOnBatteryTimeBase.readSummaryFromParcel(in);
        mOnBatteryScreenOffTimeBase.readSummaryFromParcel(in);
        mDischargeUnplugLevel = in.readInt();
        mDischargePlugLevel = in.readInt();
        mDischargeCurrentLevel = in.readInt();
        mCurrentBatteryLevel = in.readInt();
        mLowDischargeAmountSinceCharge = in.readInt();
        mHighDischargeAmountSinceCharge = in.readInt();
        mDischargeAmountScreenOnSinceCharge = in.readInt();
        mDischargeAmountScreenOffSinceCharge = in.readInt();
        mNumDischargeStepDurations = in.readInt();
        in.readLongArray(mDischargeStepDurations);
        mNumChargeStepDurations = in.readInt();
        in.readLongArray(mChargeStepDurations);

        mStartCount++;

        mScreenState = Display.STATE_UNKNOWN;
        mScreenOnTimer.readSummaryFromParcelLocked(in);
        for (int i=0; i<NUM_SCREEN_BRIGHTNESS_BINS; i++) {
            mScreenBrightnessTimer[i].readSummaryFromParcelLocked(in);
        }
        mInteractive = false;
        mInteractiveTimer.readSummaryFromParcelLocked(in);
        mPhoneOn = false;
        mLowPowerModeEnabledTimer.readSummaryFromParcelLocked(in);
        mPhoneOnTimer.readSummaryFromParcelLocked(in);
        for (int i=0; i<SignalStrength.NUM_SIGNAL_STRENGTH_BINS; i++) {
            mPhoneSignalStrengthsTimer[i].readSummaryFromParcelLocked(in);
        }
        mPhoneSignalScanningTimer.readSummaryFromParcelLocked(in);
        for (int i=0; i<NUM_DATA_CONNECTION_TYPES; i++) {
            mPhoneDataConnectionsTimer[i].readSummaryFromParcelLocked(in);
        }
        for (int i = 0; i < NUM_NETWORK_ACTIVITY_TYPES; i++) {
            mNetworkByteActivityCounters[i].readSummaryFromParcelLocked(in);
            mNetworkPacketActivityCounters[i].readSummaryFromParcelLocked(in);
        }
        mMobileRadioPowerState = DataConnectionRealTimeInfo.DC_POWER_STATE_LOW;
        mMobileRadioActiveTimer.readSummaryFromParcelLocked(in);
        mMobileRadioActivePerAppTimer.readSummaryFromParcelLocked(in);
        mMobileRadioActiveAdjustedTime.readSummaryFromParcelLocked(in);
        mMobileRadioActiveUnknownTime.readSummaryFromParcelLocked(in);
        mMobileRadioActiveUnknownCount.readSummaryFromParcelLocked(in);
        mWifiOn = false;
        mWifiOnTimer.readSummaryFromParcelLocked(in);
        mGlobalWifiRunning = false;
        mGlobalWifiRunningTimer.readSummaryFromParcelLocked(in);
        for (int i=0; i<NUM_WIFI_STATES; i++) {
            mWifiStateTimer[i].readSummaryFromParcelLocked(in);
        }
        for (int i=0; i<NUM_WIFI_SUPPL_STATES; i++) {
            mWifiSupplStateTimer[i].readSummaryFromParcelLocked(in);
        }
        for (int i=0; i<NUM_WIFI_SIGNAL_STRENGTH_BINS; i++) {
            mWifiSignalStrengthsTimer[i].readSummaryFromParcelLocked(in);
        }
        mBluetoothOn = false;
        mBluetoothOnTimer.readSummaryFromParcelLocked(in);
        for (int i=0; i< NUM_BLUETOOTH_STATES; i++) {
            mBluetoothStateTimer[i].readSummaryFromParcelLocked(in);
        }
        mNumConnectivityChange = mLoadedNumConnectivityChange = in.readInt();
        mFlashlightOn = false;
        mFlashlightOnTimer.readSummaryFromParcelLocked(in);

        int NKW = in.readInt();
        if (NKW > 10000) {
            Slog.w(TAG, "File corrupt: too many kernel wake locks " + NKW);
            return;
        }
        for (int ikw = 0; ikw < NKW; ikw++) {
            if (in.readInt() != 0) {
                String kwltName = in.readString();
                getKernelWakelockTimerLocked(kwltName).readSummaryFromParcelLocked(in);
            }
        }

        int NWR = in.readInt();
        if (NWR > 10000) {
            Slog.w(TAG, "File corrupt: too many wakeup reasons " + NWR);
            return;
        }
        for (int iwr = 0; iwr < NWR; iwr++) {
            if (in.readInt() != 0) {
                String reasonName = in.readString();
                getWakeupReasonTimerLocked(reasonName).readSummaryFromParcelLocked(in);
            }
        }

        sNumSpeedSteps = in.readInt();
        if (sNumSpeedSteps < 0 || sNumSpeedSteps > 100) {
            throw new BadParcelableException("Bad speed steps in data: " + sNumSpeedSteps);
        }

        final int NU = in.readInt();
        if (NU > 10000) {
            Slog.w(TAG, "File corrupt: too many uids " + NU);
            return;
        }
        for (int iu = 0; iu < NU; iu++) {
            int uid = in.readInt();
            Uid u = new Uid(uid);
            mUidStats.put(uid, u);

            u.mWifiRunning = false;
            if (in.readInt() != 0) {
                u.mWifiRunningTimer.readSummaryFromParcelLocked(in);
            }
            u.mFullWifiLockOut = false;
            if (in.readInt() != 0) {
                u.mFullWifiLockTimer.readSummaryFromParcelLocked(in);
            }
            u.mWifiScanStarted = false;
            if (in.readInt() != 0) {
                u.mWifiScanTimer.readSummaryFromParcelLocked(in);
            }
            u.mWifiBatchedScanBinStarted = Uid.NO_BATCHED_SCAN_STARTED;
            for (int i = 0; i < Uid.NUM_WIFI_BATCHED_SCAN_BINS; i++) {
                if (in.readInt() != 0) {
                    u.makeWifiBatchedScanBin(i, null);
                    u.mWifiBatchedScanTimer[i].readSummaryFromParcelLocked(in);
                }
            }
            u.mWifiMulticastEnabled = false;
            if (in.readInt() != 0) {
                u.mWifiMulticastTimer.readSummaryFromParcelLocked(in);
            }
            if (in.readInt() != 0) {
                u.createAudioTurnedOnTimerLocked().readSummaryFromParcelLocked(in);
            }
            if (in.readInt() != 0) {
                u.createVideoTurnedOnTimerLocked().readSummaryFromParcelLocked(in);
            }
            if (in.readInt() != 0) {
                u.createForegroundActivityTimerLocked().readSummaryFromParcelLocked(in);
            }
            u.mProcessState = Uid.PROCESS_STATE_NONE;
            for (int i = 0; i < Uid.NUM_PROCESS_STATE; i++) {
                if (in.readInt() != 0) {
                    u.makeProcessState(i, null);
                    u.mProcessStateTimer[i].readSummaryFromParcelLocked(in);
                }
            }
            if (in.readInt() != 0) {
                u.createVibratorOnTimerLocked().readSummaryFromParcelLocked(in);
            }

            if (in.readInt() != 0) {
                if (u.mUserActivityCounters == null) {
                    u.initUserActivityLocked();
                }
                for (int i=0; i<Uid.NUM_USER_ACTIVITY_TYPES; i++) {
                    u.mUserActivityCounters[i].readSummaryFromParcelLocked(in);
                }
            }

            if (in.readInt() != 0) {
                if (u.mNetworkByteActivityCounters == null) {
                    u.initNetworkActivityLocked();
                }
                for (int i = 0; i < NUM_NETWORK_ACTIVITY_TYPES; i++) {
                    u.mNetworkByteActivityCounters[i].readSummaryFromParcelLocked(in);
                    u.mNetworkPacketActivityCounters[i].readSummaryFromParcelLocked(in);
                }
                u.mMobileRadioActiveTime.readSummaryFromParcelLocked(in);
                u.mMobileRadioActiveCount.readSummaryFromParcelLocked(in);
            }

            int NW = in.readInt();
            if (NW > 100) {
                Slog.w(TAG, "File corrupt: too many wake locks " + NW);
                return;
            }
            for (int iw = 0; iw < NW; iw++) {
                String wlName = in.readString();
                u.readWakeSummaryFromParcelLocked(wlName, in);
            }

            int NS = in.readInt();
            if (NS > 100) {
                Slog.w(TAG, "File corrupt: too many syncs " + NS);
                return;
            }
            for (int is = 0; is < NS; is++) {
                String name = in.readString();
                u.readSyncSummaryFromParcelLocked(name, in);
            }

            int NJ = in.readInt();
            if (NJ > 100) {
                Slog.w(TAG, "File corrupt: too many job timers " + NJ);
                return;
            }
            for (int ij = 0; ij < NJ; ij++) {
                String name = in.readString();
                u.readJobSummaryFromParcelLocked(name, in);
            }

            int NP = in.readInt();
            if (NP > 1000) {
                Slog.w(TAG, "File corrupt: too many sensors " + NP);
                return;
            }
            for (int is = 0; is < NP; is++) {
                int seNumber = in.readInt();
                if (in.readInt() != 0) {
                    u.getSensorTimerLocked(seNumber, true)
                            .readSummaryFromParcelLocked(in);
                }
            }

            NP = in.readInt();
            if (NP > 1000) {
                Slog.w(TAG, "File corrupt: too many processes " + NP);
                return;
            }
            for (int ip = 0; ip < NP; ip++) {
                String procName = in.readString();
                Uid.Proc p = u.getProcessStatsLocked(procName);
                p.mUserTime = p.mLoadedUserTime = in.readLong();
                p.mSystemTime = p.mLoadedSystemTime = in.readLong();
                p.mForegroundTime = p.mLoadedForegroundTime = in.readLong();
                p.mStarts = p.mLoadedStarts = in.readInt();
                p.mNumCrashes = p.mLoadedNumCrashes = in.readInt();
                p.mNumAnrs = p.mLoadedNumAnrs = in.readInt();
                int NSB = in.readInt();
                if (NSB > 100) {
                    Slog.w(TAG, "File corrupt: too many speed bins " + NSB);
                    return;
                }
                p.mSpeedBins = new SamplingCounter[NSB];
                for (int i=0; i<NSB; i++) {
                    if (in.readInt() != 0) {
                        p.mSpeedBins[i] = new SamplingCounter(mOnBatteryTimeBase);
                        p.mSpeedBins[i].readSummaryFromParcelLocked(in);
                    }
                }
                if (!p.readExcessivePowerFromParcelLocked(in)) {
                    return;
                }
            }

            NP = in.readInt();
            if (NP > 10000) {
                Slog.w(TAG, "File corrupt: too many packages " + NP);
                return;
            }
            for (int ip = 0; ip < NP; ip++) {
                String pkgName = in.readString();
                Uid.Pkg p = u.getPackageStatsLocked(pkgName);
                p.mWakeups = p.mLoadedWakeups = in.readInt();
                NS = in.readInt();
                if (NS > 1000) {
                    Slog.w(TAG, "File corrupt: too many services " + NS);
                    return;
                }
                for (int is = 0; is < NS; is++) {
                    String servName = in.readString();
                    Uid.Pkg.Serv s = u.getServiceStatsLocked(pkgName, servName);
                    s.mStartTime = s.mLoadedStartTime = in.readLong();
                    s.mStarts = s.mLoadedStarts = in.readInt();
                    s.mLaunches = s.mLoadedLaunches = in.readInt();
                }
            }
        }
    }

    /**
     * Writes a summary of the statistics to a Parcel, in a format suitable to be written to
     * disk.  This format does not allow a lossless round-trip.
     *
     * @param out the Parcel to be written to.
     */
    public void writeSummaryToParcel(Parcel out, boolean inclHistory) {
        pullPendingStateUpdatesLocked();

        // Pull the clock time.  This may update the time and make a new history entry
        // if we had originally pulled a time before the RTC was set.
        long startClockTime = getStartClockTime();

        final long NOW_SYS = SystemClock.uptimeMillis() * 1000;
        final long NOWREAL_SYS = SystemClock.elapsedRealtime() * 1000;

        out.writeInt(VERSION);

        writeHistory(out, inclHistory, true);

        out.writeInt(mStartCount);
        out.writeLong(computeUptime(NOW_SYS, STATS_SINCE_CHARGED));
        out.writeLong(computeRealtime(NOWREAL_SYS, STATS_SINCE_CHARGED));
        out.writeLong(startClockTime);
        out.writeString(mStartPlatformVersion);
        out.writeString(mEndPlatformVersion);
        mOnBatteryTimeBase.writeSummaryToParcel(out, NOW_SYS, NOWREAL_SYS);
        mOnBatteryScreenOffTimeBase.writeSummaryToParcel(out, NOW_SYS, NOWREAL_SYS);
        out.writeInt(mDischargeUnplugLevel);
        out.writeInt(mDischargePlugLevel);
        out.writeInt(mDischargeCurrentLevel);
        out.writeInt(mCurrentBatteryLevel);
        out.writeInt(getLowDischargeAmountSinceCharge());
        out.writeInt(getHighDischargeAmountSinceCharge());
        out.writeInt(getDischargeAmountScreenOnSinceCharge());
        out.writeInt(getDischargeAmountScreenOffSinceCharge());
        out.writeInt(mNumDischargeStepDurations);
        out.writeLongArray(mDischargeStepDurations);
        out.writeInt(mNumChargeStepDurations);
        out.writeLongArray(mChargeStepDurations);

        mScreenOnTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
        for (int i=0; i<NUM_SCREEN_BRIGHTNESS_BINS; i++) {
            mScreenBrightnessTimer[i].writeSummaryFromParcelLocked(out, NOWREAL_SYS);
        }
        mInteractiveTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
        mLowPowerModeEnabledTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
        mPhoneOnTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
        for (int i=0; i<SignalStrength.NUM_SIGNAL_STRENGTH_BINS; i++) {
            mPhoneSignalStrengthsTimer[i].writeSummaryFromParcelLocked(out, NOWREAL_SYS);
        }
        mPhoneSignalScanningTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
        for (int i=0; i<NUM_DATA_CONNECTION_TYPES; i++) {
            mPhoneDataConnectionsTimer[i].writeSummaryFromParcelLocked(out, NOWREAL_SYS);
        }
        for (int i = 0; i < NUM_NETWORK_ACTIVITY_TYPES; i++) {
            mNetworkByteActivityCounters[i].writeSummaryFromParcelLocked(out);
            mNetworkPacketActivityCounters[i].writeSummaryFromParcelLocked(out);
        }
        mMobileRadioActiveTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
        mMobileRadioActivePerAppTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
        mMobileRadioActiveAdjustedTime.writeSummaryFromParcelLocked(out);
        mMobileRadioActiveUnknownTime.writeSummaryFromParcelLocked(out);
        mMobileRadioActiveUnknownCount.writeSummaryFromParcelLocked(out);
        mWifiOnTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
        mGlobalWifiRunningTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
        for (int i=0; i<NUM_WIFI_STATES; i++) {
            mWifiStateTimer[i].writeSummaryFromParcelLocked(out, NOWREAL_SYS);
        }
        for (int i=0; i<NUM_WIFI_SUPPL_STATES; i++) {
            mWifiSupplStateTimer[i].writeSummaryFromParcelLocked(out, NOWREAL_SYS);
        }
        for (int i=0; i<NUM_WIFI_SIGNAL_STRENGTH_BINS; i++) {
            mWifiSignalStrengthsTimer[i].writeSummaryFromParcelLocked(out, NOWREAL_SYS);
        }
        mBluetoothOnTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
        for (int i=0; i< NUM_BLUETOOTH_STATES; i++) {
            mBluetoothStateTimer[i].writeSummaryFromParcelLocked(out, NOWREAL_SYS);
        }
        out.writeInt(mNumConnectivityChange);
        mFlashlightOnTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);

        out.writeInt(mKernelWakelockStats.size());
        for (Map.Entry<String, SamplingTimer> ent : mKernelWakelockStats.entrySet()) {
            Timer kwlt = ent.getValue();
            if (kwlt != null) {
                out.writeInt(1);
                out.writeString(ent.getKey());
                kwlt.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
            } else {
                out.writeInt(0);
            }
        }

        out.writeInt(mWakeupReasonStats.size());
        for (Map.Entry<String, SamplingTimer> ent : mWakeupReasonStats.entrySet()) {
            SamplingTimer timer = ent.getValue();
            if (timer != null) {
                out.writeInt(1);
                out.writeString(ent.getKey());
                timer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
            } else {
                out.writeInt(0);
            }
        }

        out.writeInt(sNumSpeedSteps);
        final int NU = mUidStats.size();
        out.writeInt(NU);
        for (int iu = 0; iu < NU; iu++) {
            out.writeInt(mUidStats.keyAt(iu));
            Uid u = mUidStats.valueAt(iu);

            if (u.mWifiRunningTimer != null) {
                out.writeInt(1);
                u.mWifiRunningTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
            } else {
                out.writeInt(0);
            }
            if (u.mFullWifiLockTimer != null) {
                out.writeInt(1);
                u.mFullWifiLockTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
            } else {
                out.writeInt(0);
            }
            if (u.mWifiScanTimer != null) {
                out.writeInt(1);
                u.mWifiScanTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
            } else {
                out.writeInt(0);
            }
            for (int i = 0; i < Uid.NUM_WIFI_BATCHED_SCAN_BINS; i++) {
                if (u.mWifiBatchedScanTimer[i] != null) {
                    out.writeInt(1);
                    u.mWifiBatchedScanTimer[i].writeSummaryFromParcelLocked(out, NOWREAL_SYS);
                } else {
                    out.writeInt(0);
                }
            }
            if (u.mWifiMulticastTimer != null) {
                out.writeInt(1);
                u.mWifiMulticastTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
            } else {
                out.writeInt(0);
            }
            if (u.mAudioTurnedOnTimer != null) {
                out.writeInt(1);
                u.mAudioTurnedOnTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
            } else {
                out.writeInt(0);
            }
            if (u.mVideoTurnedOnTimer != null) {
                out.writeInt(1);
                u.mVideoTurnedOnTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
            } else {
                out.writeInt(0);
            }
            if (u.mForegroundActivityTimer != null) {
                out.writeInt(1);
                u.mForegroundActivityTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
            } else {
                out.writeInt(0);
            }
            for (int i = 0; i < Uid.NUM_PROCESS_STATE; i++) {
                if (u.mProcessStateTimer[i] != null) {
                    out.writeInt(1);
                    u.mProcessStateTimer[i].writeSummaryFromParcelLocked(out, NOWREAL_SYS);
                } else {
                    out.writeInt(0);
                }
            }
            if (u.mVibratorOnTimer != null) {
                out.writeInt(1);
                u.mVibratorOnTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
            } else {
                out.writeInt(0);
            }

            if (u.mUserActivityCounters == null) {
                out.writeInt(0);
            } else {
                out.writeInt(1);
                for (int i=0; i<Uid.NUM_USER_ACTIVITY_TYPES; i++) {
                    u.mUserActivityCounters[i].writeSummaryFromParcelLocked(out);
                }
            }

            if (u.mNetworkByteActivityCounters == null) {
                out.writeInt(0);
            } else {
                out.writeInt(1);
                for (int i = 0; i < NUM_NETWORK_ACTIVITY_TYPES; i++) {
                    u.mNetworkByteActivityCounters[i].writeSummaryFromParcelLocked(out);
                    u.mNetworkPacketActivityCounters[i].writeSummaryFromParcelLocked(out);
                }
                u.mMobileRadioActiveTime.writeSummaryFromParcelLocked(out);
                u.mMobileRadioActiveCount.writeSummaryFromParcelLocked(out);
            }

            final ArrayMap<String, Uid.Wakelock> wakeStats = u.mWakelockStats.getMap();
            int NW = wakeStats.size();
            out.writeInt(NW);
            for (int iw=0; iw<NW; iw++) {
                out.writeString(wakeStats.keyAt(iw));
                Uid.Wakelock wl = wakeStats.valueAt(iw);
                if (wl.mTimerFull != null) {
                    out.writeInt(1);
                    wl.mTimerFull.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
                } else {
                    out.writeInt(0);
                }
                if (wl.mTimerPartial != null) {
                    out.writeInt(1);
                    wl.mTimerPartial.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
                } else {
                    out.writeInt(0);
                }
                if (wl.mTimerWindow != null) {
                    out.writeInt(1);
                    wl.mTimerWindow.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
                } else {
                    out.writeInt(0);
                }
            }

            final ArrayMap<String, StopwatchTimer> syncStats = u.mSyncStats.getMap();
            int NS = syncStats.size();
            out.writeInt(NS);
            for (int is=0; is<NS; is++) {
                out.writeString(syncStats.keyAt(is));
                syncStats.valueAt(is).writeSummaryFromParcelLocked(out, NOWREAL_SYS);
            }

            final ArrayMap<String, StopwatchTimer> jobStats = u.mJobStats.getMap();
            int NJ = jobStats.size();
            out.writeInt(NJ);
            for (int ij=0; ij<NJ; ij++) {
                out.writeString(jobStats.keyAt(ij));
                jobStats.valueAt(ij).writeSummaryFromParcelLocked(out, NOWREAL_SYS);
            }

            int NSE = u.mSensorStats.size();
            out.writeInt(NSE);
            for (int ise=0; ise<NSE; ise++) {
                out.writeInt(u.mSensorStats.keyAt(ise));
                Uid.Sensor se = u.mSensorStats.valueAt(ise);
                if (se.mTimer != null) {
                    out.writeInt(1);
                    se.mTimer.writeSummaryFromParcelLocked(out, NOWREAL_SYS);
                } else {
                    out.writeInt(0);
                }
            }

            int NP = u.mProcessStats.size();
            out.writeInt(NP);
            for (int ip=0; ip<NP; ip++) {
                out.writeString(u.mProcessStats.keyAt(ip));
                Uid.Proc ps = u.mProcessStats.valueAt(ip);
                out.writeLong(ps.mUserTime);
                out.writeLong(ps.mSystemTime);
                out.writeLong(ps.mForegroundTime);
                out.writeInt(ps.mStarts);
                out.writeInt(ps.mNumCrashes);
                out.writeInt(ps.mNumAnrs);
                final int N = ps.mSpeedBins.length;
                out.writeInt(N);
                for (int i=0; i<N; i++) {
                    if (ps.mSpeedBins[i] != null) {
                        out.writeInt(1);
                        ps.mSpeedBins[i].writeSummaryFromParcelLocked(out);
                    } else {
                        out.writeInt(0);
                    }
                }
                ps.writeExcessivePowerToParcelLocked(out);
            }

            NP = u.mPackageStats.size();
            out.writeInt(NP);
            if (NP > 0) {
                for (Map.Entry<String, BatteryStatsImpl.Uid.Pkg> ent
                    : u.mPackageStats.entrySet()) {
                    out.writeString(ent.getKey());
                    Uid.Pkg ps = ent.getValue();
                    out.writeInt(ps.mWakeups);
                    NS = ps.mServiceStats.size();
                    out.writeInt(NS);
                    if (NS > 0) {
                        for (Map.Entry<String, BatteryStatsImpl.Uid.Pkg.Serv> sent
                                : ps.mServiceStats.entrySet()) {
                            out.writeString(sent.getKey());
                            BatteryStatsImpl.Uid.Pkg.Serv ss = sent.getValue();
                            long time = ss.getStartTimeToNowLocked(
                                    mOnBatteryTimeBase.getUptime(NOW_SYS));
                            out.writeLong(time);
                            out.writeInt(ss.mStarts);
                            out.writeInt(ss.mLaunches);
                        }
                    }
                }
            }
        }
    }

    public void readFromParcel(Parcel in) {
        readFromParcelLocked(in);
    }

    void readFromParcelLocked(Parcel in) {
        int magic = in.readInt();
        if (magic != MAGIC) {
            throw new ParcelFormatException("Bad magic number: #" + Integer.toHexString(magic));
        }

        readHistory(in, false);

        mStartCount = in.readInt();
        mStartClockTime = in.readLong();
        mStartPlatformVersion = in.readString();
        mEndPlatformVersion = in.readString();
        mUptime = in.readLong();
        mUptimeStart = in.readLong();
        mRealtime = in.readLong();
        mRealtimeStart = in.readLong();
        mOnBattery = in.readInt() != 0;
        mOnBatteryInternal = false; // we are no longer really running.
        mOnBatteryTimeBase.readFromParcel(in);
        mOnBatteryScreenOffTimeBase.readFromParcel(in);

        mScreenState = Display.STATE_UNKNOWN;
        mScreenOnTimer = new StopwatchTimer(null, -1, null, mOnBatteryTimeBase, in);
        for (int i=0; i<NUM_SCREEN_BRIGHTNESS_BINS; i++) {
            mScreenBrightnessTimer[i] = new StopwatchTimer(null, -100-i, null, mOnBatteryTimeBase,
                    in);
        }
        mInteractive = false;
        mInteractiveTimer = new StopwatchTimer(null, -9, null, mOnBatteryTimeBase, in);
        mPhoneOn = false;
        mLowPowerModeEnabledTimer = new StopwatchTimer(null, -2, null, mOnBatteryTimeBase, in);
        mPhoneOnTimer = new StopwatchTimer(null, -3, null, mOnBatteryTimeBase, in);
        for (int i=0; i<SignalStrength.NUM_SIGNAL_STRENGTH_BINS; i++) {
            mPhoneSignalStrengthsTimer[i] = new StopwatchTimer(null, -200-i,
                    null, mOnBatteryTimeBase, in);
        }
        mPhoneSignalScanningTimer = new StopwatchTimer(null, -200+1, null, mOnBatteryTimeBase, in);
        for (int i=0; i<NUM_DATA_CONNECTION_TYPES; i++) {
            mPhoneDataConnectionsTimer[i] = new StopwatchTimer(null, -300-i,
                    null, mOnBatteryTimeBase, in);
        }
        for (int i = 0; i < NUM_NETWORK_ACTIVITY_TYPES; i++) {
            mNetworkByteActivityCounters[i] = new LongSamplingCounter(mOnBatteryTimeBase, in);
            mNetworkPacketActivityCounters[i] = new LongSamplingCounter(mOnBatteryTimeBase, in);
        }
        mMobileRadioPowerState = DataConnectionRealTimeInfo.DC_POWER_STATE_LOW;
        mMobileRadioActiveTimer = new StopwatchTimer(null, -400, null, mOnBatteryTimeBase, in);
        mMobileRadioActivePerAppTimer = new StopwatchTimer(null, -401, null, mOnBatteryTimeBase,
                in);
        mMobileRadioActiveAdjustedTime = new LongSamplingCounter(mOnBatteryTimeBase, in);
        mMobileRadioActiveUnknownTime = new LongSamplingCounter(mOnBatteryTimeBase, in);
        mMobileRadioActiveUnknownCount = new LongSamplingCounter(mOnBatteryTimeBase, in);
        mWifiOn = false;
        mWifiOnTimer = new StopwatchTimer(null, -4, null, mOnBatteryTimeBase, in);
        mGlobalWifiRunning = false;
        mGlobalWifiRunningTimer = new StopwatchTimer(null, -5, null, mOnBatteryTimeBase, in);
        for (int i=0; i<NUM_WIFI_STATES; i++) {
            mWifiStateTimer[i] = new StopwatchTimer(null, -600-i,
                    null, mOnBatteryTimeBase, in);
        }
        for (int i=0; i<NUM_WIFI_SUPPL_STATES; i++) {
            mWifiSupplStateTimer[i] = new StopwatchTimer(null, -700-i,
                    null, mOnBatteryTimeBase, in);
        }
        for (int i=0; i<NUM_WIFI_SIGNAL_STRENGTH_BINS; i++) {
            mWifiSignalStrengthsTimer[i] = new StopwatchTimer(null, -800-i,
                    null, mOnBatteryTimeBase, in);
        }
        mBluetoothOn = false;
        mBluetoothOnTimer = new StopwatchTimer(null, -6, null, mOnBatteryTimeBase, in);
        for (int i=0; i< NUM_BLUETOOTH_STATES; i++) {
            mBluetoothStateTimer[i] = new StopwatchTimer(null, -500-i,
                    null, mOnBatteryTimeBase, in);
        }
        mNumConnectivityChange = in.readInt();
        mLoadedNumConnectivityChange = in.readInt();
        mUnpluggedNumConnectivityChange = in.readInt();
        mAudioOnNesting = 0;
        mAudioOnTimer = new StopwatchTimer(null, -7, null, mOnBatteryTimeBase);
        mVideoOnNesting = 0;
        mVideoOnTimer = new StopwatchTimer(null, -8, null, mOnBatteryTimeBase);
        mFlashlightOn = false;
        mFlashlightOnTimer = new StopwatchTimer(null, -9, null, mOnBatteryTimeBase, in);
        mDischargeUnplugLevel = in.readInt();
        mDischargePlugLevel = in.readInt();
        mDischargeCurrentLevel = in.readInt();
        mCurrentBatteryLevel = in.readInt();
        mLowDischargeAmountSinceCharge = in.readInt();
        mHighDischargeAmountSinceCharge = in.readInt();
        mDischargeAmountScreenOn = in.readInt();
        mDischargeAmountScreenOnSinceCharge = in.readInt();
        mDischargeAmountScreenOff = in.readInt();
        mDischargeAmountScreenOffSinceCharge = in.readInt();
        mNumDischargeStepDurations = in.readInt();
        in.readLongArray(mDischargeStepDurations);
        mNumChargeStepDurations = in.readInt();
        in.readLongArray(mChargeStepDurations);
        mLastWriteTime = in.readLong();

        mBluetoothPingCount = in.readInt();
        mBluetoothPingStart = -1;

        mKernelWakelockStats.clear();
        int NKW = in.readInt();
        for (int ikw = 0; ikw < NKW; ikw++) {
            if (in.readInt() != 0) {
                String wakelockName = in.readString();
                SamplingTimer kwlt = new SamplingTimer(mOnBatteryScreenOffTimeBase, in);
                mKernelWakelockStats.put(wakelockName, kwlt);
            }
        }

        mWakeupReasonStats.clear();
        int NWR = in.readInt();
        for (int iwr = 0; iwr < NWR; iwr++) {
            if (in.readInt() != 0) {
                String reasonName = in.readString();
                SamplingTimer timer = new SamplingTimer(mOnBatteryTimeBase, in);
                mWakeupReasonStats.put(reasonName, timer);
            }
        }

        mPartialTimers.clear();
        mFullTimers.clear();
        mWindowTimers.clear();
        mWifiRunningTimers.clear();
        mFullWifiLockTimers.clear();
        mWifiScanTimers.clear();
        mWifiBatchedScanTimers.clear();
        mWifiMulticastTimers.clear();
        mAudioTurnedOnTimers.clear();
        mVideoTurnedOnTimers.clear();

        sNumSpeedSteps = in.readInt();

        int numUids = in.readInt();
        mUidStats.clear();
        for (int i = 0; i < numUids; i++) {
            int uid = in.readInt();
            Uid u = new Uid(uid);
            u.readFromParcelLocked(mOnBatteryTimeBase, mOnBatteryScreenOffTimeBase, in);
            mUidStats.append(uid, u);
        }
    }

    public void writeToParcel(Parcel out, int flags) {
        writeToParcelLocked(out, true, flags);
    }

    public void writeToParcelWithoutUids(Parcel out, int flags) {
        writeToParcelLocked(out, false, flags);
    }

    @SuppressWarnings("unused")
    void writeToParcelLocked(Parcel out, boolean inclUids, int flags) {
        // Need to update with current kernel wake lock counts.
        pullPendingStateUpdatesLocked();

        // Pull the clock time.  This may update the time and make a new history entry
        // if we had originally pulled a time before the RTC was set.
        long startClockTime = getStartClockTime();

        final long uSecUptime = SystemClock.uptimeMillis() * 1000;
        final long uSecRealtime = SystemClock.elapsedRealtime() * 1000;
        final long batteryRealtime = mOnBatteryTimeBase.getRealtime(uSecRealtime);
        final long batteryScreenOffRealtime = mOnBatteryScreenOffTimeBase.getRealtime(uSecRealtime);

        out.writeInt(MAGIC);

        writeHistory(out, true, false);

        out.writeInt(mStartCount);
        out.writeLong(startClockTime);
        out.writeString(mStartPlatformVersion);
        out.writeString(mEndPlatformVersion);
        out.writeLong(mUptime);
        out.writeLong(mUptimeStart);
        out.writeLong(mRealtime);
        out.writeLong(mRealtimeStart);
        out.writeInt(mOnBattery ? 1 : 0);
        mOnBatteryTimeBase.writeToParcel(out, uSecUptime, uSecRealtime);
        mOnBatteryScreenOffTimeBase.writeToParcel(out, uSecUptime, uSecRealtime);

        mScreenOnTimer.writeToParcel(out, uSecRealtime);
        for (int i=0; i<NUM_SCREEN_BRIGHTNESS_BINS; i++) {
            mScreenBrightnessTimer[i].writeToParcel(out, uSecRealtime);
        }
        mInteractiveTimer.writeToParcel(out, uSecRealtime);
        mLowPowerModeEnabledTimer.writeToParcel(out, uSecRealtime);
        mPhoneOnTimer.writeToParcel(out, uSecRealtime);
        for (int i=0; i<SignalStrength.NUM_SIGNAL_STRENGTH_BINS; i++) {
            mPhoneSignalStrengthsTimer[i].writeToParcel(out, uSecRealtime);
        }
        mPhoneSignalScanningTimer.writeToParcel(out, uSecRealtime);
        for (int i=0; i<NUM_DATA_CONNECTION_TYPES; i++) {
            mPhoneDataConnectionsTimer[i].writeToParcel(out, uSecRealtime);
        }
        for (int i = 0; i < NUM_NETWORK_ACTIVITY_TYPES; i++) {
            mNetworkByteActivityCounters[i].writeToParcel(out);
            mNetworkPacketActivityCounters[i].writeToParcel(out);
        }
        mMobileRadioActiveTimer.writeToParcel(out, uSecRealtime);
        mMobileRadioActivePerAppTimer.writeToParcel(out, uSecRealtime);
        mMobileRadioActiveAdjustedTime.writeToParcel(out);
        mMobileRadioActiveUnknownTime.writeToParcel(out);
        mMobileRadioActiveUnknownCount.writeToParcel(out);
        mWifiOnTimer.writeToParcel(out, uSecRealtime);
        mGlobalWifiRunningTimer.writeToParcel(out, uSecRealtime);
        for (int i=0; i<NUM_WIFI_STATES; i++) {
            mWifiStateTimer[i].writeToParcel(out, uSecRealtime);
        }
        for (int i=0; i<NUM_WIFI_SUPPL_STATES; i++) {
            mWifiSupplStateTimer[i].writeToParcel(out, uSecRealtime);
        }
        for (int i=0; i<NUM_WIFI_SIGNAL_STRENGTH_BINS; i++) {
            mWifiSignalStrengthsTimer[i].writeToParcel(out, uSecRealtime);
        }
        mBluetoothOnTimer.writeToParcel(out, uSecRealtime);
        for (int i=0; i< NUM_BLUETOOTH_STATES; i++) {
            mBluetoothStateTimer[i].writeToParcel(out, uSecRealtime);
        }
        out.writeInt(mNumConnectivityChange);
        out.writeInt(mLoadedNumConnectivityChange);
        out.writeInt(mUnpluggedNumConnectivityChange);
        mFlashlightOnTimer.writeToParcel(out, uSecRealtime);
        out.writeInt(mDischargeUnplugLevel);
        out.writeInt(mDischargePlugLevel);
        out.writeInt(mDischargeCurrentLevel);
        out.writeInt(mCurrentBatteryLevel);
        out.writeInt(mLowDischargeAmountSinceCharge);
        out.writeInt(mHighDischargeAmountSinceCharge);
        out.writeInt(mDischargeAmountScreenOn);
        out.writeInt(mDischargeAmountScreenOnSinceCharge);
        out.writeInt(mDischargeAmountScreenOff);
        out.writeInt(mDischargeAmountScreenOffSinceCharge);
        out.writeInt(mNumDischargeStepDurations);
        out.writeLongArray(mDischargeStepDurations);
        out.writeInt(mNumChargeStepDurations);
        out.writeLongArray(mChargeStepDurations);
        out.writeLong(mLastWriteTime);

        out.writeInt(getBluetoothPingCount());

        if (inclUids) {
            out.writeInt(mKernelWakelockStats.size());
            for (Map.Entry<String, SamplingTimer> ent : mKernelWakelockStats.entrySet()) {
                SamplingTimer kwlt = ent.getValue();
                if (kwlt != null) {
                    out.writeInt(1);
                    out.writeString(ent.getKey());
                    kwlt.writeToParcel(out, uSecRealtime);
                } else {
                    out.writeInt(0);
                }
            }
            out.writeInt(mWakeupReasonStats.size());
            for (Map.Entry<String, SamplingTimer> ent : mWakeupReasonStats.entrySet()) {
                SamplingTimer timer = ent.getValue();
                if (timer != null) {
                    out.writeInt(1);
                    out.writeString(ent.getKey());
                    timer.writeToParcel(out, uSecRealtime);
                } else {
                    out.writeInt(0);
                }
            }
        } else {
            out.writeInt(0);
        }

        out.writeInt(sNumSpeedSteps);

        if (inclUids) {
            int size = mUidStats.size();
            out.writeInt(size);
            for (int i = 0; i < size; i++) {
                out.writeInt(mUidStats.keyAt(i));
                Uid uid = mUidStats.valueAt(i);

                uid.writeToParcelLocked(out, uSecRealtime);
            }
        } else {
            out.writeInt(0);
        }
    }

    public static final Parcelable.Creator<BatteryStatsImpl> CREATOR =
        new Parcelable.Creator<BatteryStatsImpl>() {
        public BatteryStatsImpl createFromParcel(Parcel in) {
            return new BatteryStatsImpl(in);
        }

        public BatteryStatsImpl[] newArray(int size) {
            return new BatteryStatsImpl[size];
        }
    };

    public void prepareForDumpLocked() {
        // Need to retrieve current kernel wake lock stats before printing.
        pullPendingStateUpdatesLocked();

        // Pull the clock time.  This may update the time and make a new history entry
        // if we had originally pulled a time before the RTC was set.
        getStartClockTime();
    }

    public void dumpLocked(Context context, PrintWriter pw, int flags, int reqUid, long histStart) {
        if (DEBUG) {
            pw.println("mOnBatteryTimeBase:");
            mOnBatteryTimeBase.dump(pw, "  ");
            pw.println("mOnBatteryScreenOffTimeBase:");
            mOnBatteryScreenOffTimeBase.dump(pw, "  ");
            Printer pr = new PrintWriterPrinter(pw);
            pr.println("*** Screen timer:");
            mScreenOnTimer.logState(pr, "  ");
            for (int i=0; i<NUM_SCREEN_BRIGHTNESS_BINS; i++) {
                pr.println("*** Screen brightness #" + i + ":");
                mScreenBrightnessTimer[i].logState(pr, "  ");
            }
            pr.println("*** Interactive timer:");
            mInteractiveTimer.logState(pr, "  ");
            pr.println("*** Low power mode timer:");
            mLowPowerModeEnabledTimer.logState(pr, "  ");
            pr.println("*** Phone timer:");
            mPhoneOnTimer.logState(pr, "  ");
            for (int i=0; i<SignalStrength.NUM_SIGNAL_STRENGTH_BINS; i++) {
                pr.println("*** Phone signal strength #" + i + ":");
                mPhoneSignalStrengthsTimer[i].logState(pr, "  ");
            }
            pr.println("*** Signal scanning :");
            mPhoneSignalScanningTimer.logState(pr, "  ");
            for (int i=0; i<NUM_DATA_CONNECTION_TYPES; i++) {
                pr.println("*** Data connection type #" + i + ":");
                mPhoneDataConnectionsTimer[i].logState(pr, "  ");
            }
            pr.println("*** mMobileRadioPowerState=" + mMobileRadioPowerState);
            pr.println("*** Mobile network active timer:");
            mMobileRadioActiveTimer.logState(pr, "  ");
            pr.println("*** Mobile network active adjusted timer:");
            mMobileRadioActiveAdjustedTime.logState(pr, "  ");
            pr.println("*** Wifi timer:");
            mWifiOnTimer.logState(pr, "  ");
            pr.println("*** WifiRunning timer:");
            mGlobalWifiRunningTimer.logState(pr, "  ");
            for (int i=0; i<NUM_WIFI_STATES; i++) {
                pr.println("*** Wifi state #" + i + ":");
                mWifiStateTimer[i].logState(pr, "  ");
            }
            for (int i=0; i<NUM_WIFI_SUPPL_STATES; i++) {
                pr.println("*** Wifi suppl state #" + i + ":");
                mWifiSupplStateTimer[i].logState(pr, "  ");
            }
            for (int i=0; i<NUM_WIFI_SIGNAL_STRENGTH_BINS; i++) {
                pr.println("*** Wifi signal strength #" + i + ":");
                mWifiSignalStrengthsTimer[i].logState(pr, "  ");
            }
            pr.println("*** Bluetooth timer:");
            mBluetoothOnTimer.logState(pr, "  ");
            for (int i=0; i< NUM_BLUETOOTH_STATES; i++) {
                pr.println("*** Bluetooth active type #" + i + ":");
                mBluetoothStateTimer[i].logState(pr, "  ");
            }
            pr.println("*** Flashlight timer:");
            mFlashlightOnTimer.logState(pr, "  ");
        }
        super.dumpLocked(context, pw, flags, reqUid, histStart);
    }
}


File: packages/SystemUI/src/com/android/systemui/BatteryLevelTextView.java
/*
 * Copyright (C) 2014 The CyanogenMod Project
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

package com.android.systemui;

import android.content.Context;
import android.content.res.Configuration;
import android.util.AttributeSet;
import android.util.TypedValue;
import android.widget.TextView;

import com.android.systemui.statusbar.policy.BatteryController;

public class BatteryLevelTextView extends TextView implements
        BatteryController.BatteryStateChangeCallback{

    private static final String STATUS_BAR_BATTERY_STYLE = "status_bar_battery_style";
    private static final String STATUS_BAR_SHOW_BATTERY_PERCENT = "status_bar_show_battery_percent";

    private BatteryController mBatteryController;
    private boolean mBatteryCharging;
    private boolean mForceShow;
    private boolean mAttached;
    private int mRequestedVisibility;

    private int mStyle;
    private int mPercentMode;

    public BatteryLevelTextView(Context context, AttributeSet attrs) {
        super(context, attrs);
        mRequestedVisibility = getVisibility();
    }

    public void setForceShown(boolean forceShow) {
        mForceShow = forceShow;
        updateVisibility();
    }

    public void setBatteryController(BatteryController batteryController) {
        mBatteryController = batteryController;
        if (mAttached) {
            mBatteryController.addStateChangedCallback(this);
        }
    }

    @Override
    public void setVisibility(int visibility) {
        mRequestedVisibility = visibility;
        updateVisibility();
    }

    @Override
    protected void onConfigurationChanged(Configuration newConfig) {
        super.onConfigurationChanged(newConfig);

        // Respect font size setting.
        setTextSize(TypedValue.COMPLEX_UNIT_PX,
                getResources().getDimensionPixelSize(R.dimen.battery_level_text_size));
     }

    @Override
    public void onBatteryLevelChanged(int level, boolean pluggedIn, boolean charging) {
        setText(getResources().getString(R.string.battery_level_template, level));
        if (mBatteryCharging != charging) {
            mBatteryCharging = charging;
            updateVisibility();
        }
    }

    @Override
    public void onPowerSaveChanged() {
        // Not used
    }

    @Override
    public void onBatteryStyleChanged(int style, int percentMode) {
        mStyle = style;
        mPercentMode = percentMode;
        updateVisibility();
    }

    @Override
    public void onAttachedToWindow() {
        super.onAttachedToWindow();

        if (mBatteryController != null) {
            mBatteryController.addStateChangedCallback(this);
        }

        mAttached = true;
    }

    @Override
    public void onDetachedFromWindow() {
        super.onDetachedFromWindow();
        mAttached = false;

        if (mBatteryController != null) {
            mBatteryController.removeStateChangedCallback(this);
        }
    }

    private void updateVisibility() {
        boolean showNextPercent = mPercentMode == BatteryController.PERCENTAGE_MODE_OUTSIDE
                || (mBatteryCharging && mPercentMode == BatteryController.PERCENTAGE_MODE_INSIDE);
        if (mStyle == BatteryController.STYLE_GONE) {
            showNextPercent = false;
        } else if (mStyle == BatteryController.STYLE_TEXT) {
            showNextPercent = true;
        }

        if (showNextPercent || mForceShow) {
            super.setVisibility(mRequestedVisibility);
        } else {
            super.setVisibility(GONE);
        }
    }
}


File: packages/SystemUI/src/com/android/systemui/BatteryMeterView.java
/*
 * Copyright (C) 2013 The Android Open Source Project
 * Copyright (C) 2014 The CyanogenMod Project
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

package com.android.systemui;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.res.Resources;
import android.content.res.TypedArray;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.os.BatteryManager;
import android.os.Bundle;
import android.os.Handler;
import android.util.DisplayMetrics;
import android.util.AttributeSet;
import android.util.Log;
import android.view.View;

import com.android.systemui.statusbar.policy.BatteryController;

public class BatteryMeterView extends View implements DemoMode,
        BatteryController.BatteryStateChangeCallback {
    public static final String TAG = BatteryMeterView.class.getSimpleName();
    public static final String ACTION_LEVEL_TEST = "com.android.systemui.BATTERY_LEVEL_TEST";

    private static final String STATUS_BAR_BATTERY_STYLE = "status_bar_battery_style";
    private static final String STATUS_BAR_SHOW_BATTERY_PERCENT = "status_bar_show_battery_percent";

    private static final boolean SINGLE_DIGIT_PERCENT = false;
    private static final boolean SHOW_100_PERCENT = false;

    private static final int FULL = 96;

    private static final float BOLT_LEVEL_THRESHOLD = 0.3f;  // opaque bolt below this fraction

    private final int[] mColors;

    protected boolean mShowPercent = true;
    private float mButtonHeightFraction;
    private float mSubpixelSmoothingLeft;
    private float mSubpixelSmoothingRight;

    public static enum BatteryMeterMode {
        BATTERY_METER_GONE,
        BATTERY_METER_ICON_PORTRAIT,
        BATTERY_METER_ICON_LANDSCAPE,
        BATTERY_METER_CIRCLE,
        BATTERY_METER_TEXT
    }

    private int mHeight;
    private int mWidth;

    private String mWarningString;
    private final int mCriticalLevel;
    private final int mFrameColor;

    private final Path mShapePath = new Path();
    private final Path mClipPath = new Path();
    private final Path mTextPath = new Path();

    private BatteryController mBatteryController;
    private boolean mPowerSaveEnabled;

    private final Handler mHandler;

    protected BatteryMeterMode mMeterMode = null;

    protected boolean mAttached;

    private boolean mDemoMode;
    protected BatteryTracker mDemoTracker = new BatteryTracker();
    protected BatteryTracker mTracker = new BatteryTracker();
    private BatteryMeterDrawable mBatteryMeterDrawable;
    private final Object mLock = new Object();

    private class BatteryTracker extends BroadcastReceiver {
        public static final int UNKNOWN_LEVEL = -1;

        // current battery status
        boolean present = true;
        int level = UNKNOWN_LEVEL;
        String percentStr;
        int plugType;
        boolean plugged;
        int health;
        int status;
        String technology;
        int voltage;
        int temperature;
        boolean testmode = false;

        @Override
        public void onReceive(Context context, Intent intent) {
            final String action = intent.getAction();
            if (action.equals(Intent.ACTION_BATTERY_CHANGED)) {
                if (testmode && ! intent.getBooleanExtra("testmode", false)) return;

                level = (int)(100f
                        * intent.getIntExtra(BatteryManager.EXTRA_LEVEL, 0)
                        / intent.getIntExtra(BatteryManager.EXTRA_SCALE, 100));

                present = intent.getBooleanExtra(BatteryManager.EXTRA_PRESENT, true);
                plugType = intent.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0);
                plugged = plugType != 0;
                health = intent.getIntExtra(BatteryManager.EXTRA_HEALTH,
                        BatteryManager.BATTERY_HEALTH_UNKNOWN);
                status = intent.getIntExtra(BatteryManager.EXTRA_STATUS,
                        BatteryManager.BATTERY_STATUS_UNKNOWN);
                technology = intent.getStringExtra(BatteryManager.EXTRA_TECHNOLOGY);
                voltage = intent.getIntExtra(BatteryManager.EXTRA_VOLTAGE, 0);
                temperature = intent.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, 0);

                setContentDescription(
                        context.getString(R.string.accessibility_battery_level, level));
                synchronized (mLock) {
                    if (mBatteryMeterDrawable != null) {
                        setVisibility(View.VISIBLE);
                        invalidateIfVisible();
                    }
                }
            } else if (action.equals(ACTION_LEVEL_TEST)) {
                testmode = true;
                post(new Runnable() {
                    int curLevel = 0;
                    int incr = 1;
                    int saveLevel = level;
                    int savePlugged = plugType;
                    Intent dummy = new Intent(Intent.ACTION_BATTERY_CHANGED);
                    @Override
                    public void run() {
                        if (curLevel < 0) {
                            testmode = false;
                            dummy.putExtra("level", saveLevel);
                            dummy.putExtra("plugged", savePlugged);
                            dummy.putExtra("testmode", false);
                        } else {
                            dummy.putExtra("level", curLevel);
                            dummy.putExtra("plugged", incr > 0
                                    ? BatteryManager.BATTERY_PLUGGED_AC : 0);
                            dummy.putExtra("testmode", true);
                        }
                        getContext().sendBroadcast(dummy);

                        if (!testmode) return;

                        curLevel += incr;
                        if (curLevel == 100) {
                            incr *= -1;
                        }
                        postDelayed(this, 200);
                    }
                });
            }
        }

        protected boolean shouldIndicateCharging() {
            if (status == BatteryManager.BATTERY_STATUS_CHARGING) {
                return true;
            }
            if (plugged) {
                return status == BatteryManager.BATTERY_STATUS_FULL;
            }
            return false;
        }
    }

    private final Runnable mInvalidate = new Runnable() {
        public void run() {
            invalidateIfVisible();
        }
    };

    @Override
    public void onAttachedToWindow() {
        super.onAttachedToWindow();

        IntentFilter filter = new IntentFilter();
        filter.addAction(Intent.ACTION_BATTERY_CHANGED);
        filter.addAction(ACTION_LEVEL_TEST);
        final Intent sticky = getContext().registerReceiver(mTracker, filter);
        if (sticky != null) {
            // preload the battery level
            mTracker.onReceive(getContext(), sticky);
        }
        mBatteryController.addStateChangedCallback(this);
        mAttached = true;
    }

    @Override
    public void onDetachedFromWindow() {
        super.onDetachedFromWindow();

        mAttached = false;
        getContext().unregisterReceiver(mTracker);
        mBatteryController.removeStateChangedCallback(this);
    }

    public BatteryMeterView(Context context) {
        this(context, null, 0);
    }

    public BatteryMeterView(Context context, AttributeSet attrs) {
        this(context, attrs, 0);
    }

    public BatteryMeterView(Context context, AttributeSet attrs, int defStyle) {
        super(context, attrs, defStyle);
        mHandler = new Handler();

        final Resources res = context.getResources();
        TypedArray atts = context.obtainStyledAttributes(attrs, R.styleable.BatteryMeterView,
                defStyle, 0);
        mFrameColor = atts.getColor(R.styleable.BatteryMeterView_frameColor,
                res.getColor(R.color.batterymeter_frame_color));
        TypedArray levels = res.obtainTypedArray(R.array.batterymeter_color_levels);
        TypedArray colors = res.obtainTypedArray(R.array.batterymeter_color_values);

        final int N = levels.length();
        mColors = new int[2*N];
        for (int i=0; i<N; i++) {
            mColors[2*i] = levels.getInt(i, 0);
            mColors[2*i+1] = colors.getColor(i, 0);
        }
        levels.recycle();
        colors.recycle();
        atts.recycle();
        mWarningString = context.getString(R.string.battery_meter_very_low_overlay_symbol);
        mCriticalLevel = mContext.getResources().getInteger(
                com.android.internal.R.integer.config_criticalBatteryWarningLevel);
        mButtonHeightFraction = context.getResources().getFraction(
                R.fraction.battery_button_height_fraction, 1, 1);
        mSubpixelSmoothingLeft = context.getResources().getFraction(
                R.fraction.battery_subpixel_smoothing_left, 1, 1);
        mSubpixelSmoothingRight = context.getResources().getFraction(
                R.fraction.battery_subpixel_smoothing_right, 1, 1);
    }

    protected BatteryMeterDrawable createBatteryMeterDrawable(BatteryMeterMode mode) {
        Resources res = mContext.getResources();
        switch (mode) {
            case BATTERY_METER_CIRCLE:
                return new CircleBatteryMeterDrawable(res);
            case BATTERY_METER_ICON_LANDSCAPE:
                return new NormalBatteryMeterDrawable(res, true);
            case BATTERY_METER_TEXT:
            case BATTERY_METER_GONE:
                return null;
            default:
                return new NormalBatteryMeterDrawable(res, false);
        }
    }

    @Override
    protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
        int width = MeasureSpec.getSize(widthMeasureSpec);
        int height = MeasureSpec.getSize(heightMeasureSpec);

        if (mMeterMode == BatteryMeterMode.BATTERY_METER_CIRCLE) {
            height += (CircleBatteryMeterDrawable.STROKE_WITH / 3);
            width = height;
        } else if (mMeterMode == BatteryMeterMode.BATTERY_METER_TEXT) {
            onSizeChanged(width, height, 0, 0); // Force a size changed event
        } else if (mMeterMode.compareTo(BatteryMeterMode.BATTERY_METER_ICON_LANDSCAPE) == 0) {
            width = (int)(height * 1.2f);
        }

        setMeasuredDimension(width, height);
    }

    public void setBatteryController(BatteryController batteryController) {
        mBatteryController = batteryController;
        mPowerSaveEnabled = mBatteryController.isPowerSave();
    }

    @Override
    public void onBatteryLevelChanged(int level, boolean pluggedIn, boolean charging) {
        // TODO: Use this callback instead of own broadcast receiver.
    }

    @Override
    public void onPowerSaveChanged() {
        mPowerSaveEnabled = mBatteryController.isPowerSave();
        invalidate();
    }

    @Override
    public void onBatteryStyleChanged(int style, int percentMode) {
        boolean showInsidePercent = percentMode == BatteryController.PERCENTAGE_MODE_INSIDE;
        BatteryMeterMode meterMode = BatteryMeterMode.BATTERY_METER_ICON_PORTRAIT;

        switch (style) {
            case BatteryController.STYLE_CIRCLE:
                meterMode = BatteryMeterMode.BATTERY_METER_CIRCLE;
                break;
            case BatteryController.STYLE_GONE:
                meterMode = BatteryMeterMode.BATTERY_METER_GONE;
                showInsidePercent = false;
                break;
            case BatteryController.STYLE_ICON_LANDSCAPE:
                meterMode = BatteryMeterMode.BATTERY_METER_ICON_LANDSCAPE;
                break;
            case BatteryController.STYLE_TEXT:
                meterMode = BatteryMeterMode.BATTERY_METER_TEXT;
                showInsidePercent = false;
                break;
            default:
                break;
        }

        setMode(meterMode);
        mShowPercent = showInsidePercent;
        invalidateIfVisible();
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        mHeight = h;
        mWidth = w;
        synchronized (mLock) {
            if (mBatteryMeterDrawable != null) {
                mBatteryMeterDrawable.onSizeChanged(w, h, oldw, oldh);
            }
        }
    }

    protected void invalidateIfVisible() {
        if (getVisibility() == View.VISIBLE && mAttached) {
            if (mAttached) {
                postInvalidate();
            } else {
                invalidate();
            }
        }
    }

    public void setMode(BatteryMeterMode mode) {
        if (mMeterMode == mode) {
            return;
        }

        mMeterMode = mode;
        BatteryTracker tracker = mDemoMode ? mDemoTracker : mTracker;
        if (mode == BatteryMeterMode.BATTERY_METER_GONE ||
                mode == BatteryMeterMode.BATTERY_METER_TEXT) {
            setVisibility(View.GONE);
            synchronized (mLock) {
                mBatteryMeterDrawable = null;
            }
        } else {
            synchronized (mLock) {
                if (mBatteryMeterDrawable != null) {
                    mBatteryMeterDrawable.onDispose();
                }
                mBatteryMeterDrawable = createBatteryMeterDrawable(mode);
            }
            if (mMeterMode == BatteryMeterMode.BATTERY_METER_ICON_PORTRAIT ||
                    mMeterMode == BatteryMeterMode.BATTERY_METER_ICON_LANDSCAPE) {
                ((NormalBatteryMeterDrawable)mBatteryMeterDrawable).loadBoltPoints(
                        mContext.getResources());
            }
            if (tracker.present) {
                setVisibility(View.VISIBLE);
                postInvalidate();
                requestLayout();
            } else {
                setVisibility(View.GONE);
            }
        }
    }

    public int getColorForLevel(int percent) {

        // If we are in power save mode, always use the normal color.
        if (mPowerSaveEnabled) {
            return mColors[mColors.length-1];
        }
        int thresh, color = 0;
        for (int i=0; i<mColors.length; i+=2) {
            thresh = mColors[i];
            color = mColors[i+1];
            if (percent <= thresh) return color;
        }
        return color;
    }

    @Override
    public void draw(Canvas c) {
        synchronized (mLock) {
            if (mBatteryMeterDrawable != null) {
                BatteryTracker tracker = mDemoMode ? mDemoTracker : mTracker;
                mBatteryMeterDrawable.onDraw(c, tracker);
            }
        }
    }

    @Override
    public boolean hasOverlappingRendering() {
        return false;
    }

    @Override
    public void dispatchDemoCommand(String command, Bundle args) {
        if (getVisibility() == View.VISIBLE) {
            if (!mDemoMode && command.equals(COMMAND_ENTER)) {
                mDemoMode = true;
                mDemoTracker.level = mTracker.level;
                mDemoTracker.plugged = mTracker.plugged;
            } else if (mDemoMode && command.equals(COMMAND_EXIT)) {
                mDemoMode = false;
                postInvalidate();
            } else if (mDemoMode && command.equals(COMMAND_BATTERY)) {
               String level = args.getString("level");
               String plugged = args.getString("plugged");
               if (level != null) {
                   mDemoTracker.level = Math.min(Math.max(Integer.parseInt(level), 0), 100);
               }
               if (plugged != null) {
                   mDemoTracker.plugged = Boolean.parseBoolean(plugged);
               }
               postInvalidate();
            }
        }
    }

    protected interface BatteryMeterDrawable {
        void onDraw(Canvas c, BatteryTracker tracker);
        void onSizeChanged(int w, int h, int oldw, int oldh);
        void onDispose();
    }

    protected class NormalBatteryMeterDrawable implements BatteryMeterDrawable {
        private static final boolean SINGLE_DIGIT_PERCENT = false;
        private static final boolean SHOW_100_PERCENT = false;

        private boolean mDisposed;

        protected final boolean mHorizontal;

        private final Paint mFramePaint, mBatteryPaint, mWarningTextPaint, mTextPaint, mBoltPaint;
        private float mTextHeight, mWarningTextHeight;

        private final int mChargeColor;
        private final float[] mBoltPoints;
        private final Path mBoltPath = new Path();

        private final RectF mFrame = new RectF();
        private final RectF mButtonFrame = new RectF();
        private final RectF mBoltFrame = new RectF();

        public NormalBatteryMeterDrawable(Resources res, boolean horizontal) {
            super();
            mHorizontal = horizontal;
            mDisposed = false;

            mFramePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
            mFramePaint.setColor(mFrameColor);
            mFramePaint.setDither(true);
            mFramePaint.setStrokeWidth(0);
            mFramePaint.setStyle(Paint.Style.FILL_AND_STROKE);

            mBatteryPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
            mBatteryPaint.setDither(true);
            mBatteryPaint.setStrokeWidth(0);
            mBatteryPaint.setStyle(Paint.Style.FILL_AND_STROKE);

            mTextPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
            Typeface font = Typeface.create("sans-serif-condensed", Typeface.BOLD);
            mTextPaint.setTypeface(font);
            mTextPaint.setTextAlign(Paint.Align.CENTER);

            mWarningTextPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
            mWarningTextPaint.setColor(mColors[1]);
            font = Typeface.create("sans-serif", Typeface.BOLD);
            mWarningTextPaint.setTypeface(font);
            mWarningTextPaint.setTextAlign(Paint.Align.CENTER);

            mChargeColor = getResources().getColor(R.color.batterymeter_charge_color);

            mBoltPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
            mBoltPaint.setColor(res.getColor(R.color.batterymeter_bolt_color));
            mBoltPoints = loadBoltPoints(res);
        }

        @Override
        public void onDraw(Canvas c, BatteryTracker tracker) {
            if (mDisposed) return;

            final int level = tracker.level;

            if (level == BatteryTracker.UNKNOWN_LEVEL) return;

            float drawFrac = (float) level / 100f;
            final int pt = getPaddingTop() + (mHorizontal ? (int)(mHeight * 0.12f) : 0);
            final int pl = getPaddingLeft();
            final int pr = getPaddingRight();
            final int pb = getPaddingBottom() + (mHorizontal ? (int)(mHeight * 0.08f) : 0);
            final int height = mHeight - pt - pb;
            final int width = mWidth - pl - pr;

            final int buttonHeight = (int) ((mHorizontal ? width : height) * mButtonHeightFraction);

            mFrame.set(0, 0, width, height);
            mFrame.offset(pl, pt);

            if (mHorizontal) {
                mButtonFrame.set(
                        /*cover frame border of intersecting area*/
                        width - buttonHeight - mFrame.left,
                        mFrame.top + Math.round(height * 0.25f),
                        mFrame.right,
                        mFrame.bottom - Math.round(height * 0.25f));

                mButtonFrame.top += mSubpixelSmoothingLeft;
                mButtonFrame.bottom -= mSubpixelSmoothingRight;
                mButtonFrame.right -= mSubpixelSmoothingRight;
            } else {
                // button-frame: area above the battery body
                mButtonFrame.set(
                        mFrame.left + Math.round(width * 0.25f),
                        mFrame.top,
                        mFrame.right - Math.round(width * 0.25f),
                        mFrame.top + buttonHeight);

                mButtonFrame.top += mSubpixelSmoothingLeft;
                mButtonFrame.left += mSubpixelSmoothingLeft;
                mButtonFrame.right -= mSubpixelSmoothingRight;
            }

            // frame: battery body area

            if (mHorizontal) {
                mFrame.right -= buttonHeight;
            } else {
                mFrame.top += buttonHeight;
            }
            mFrame.left += mSubpixelSmoothingLeft;
            mFrame.top += mSubpixelSmoothingLeft;
            mFrame.right -= mSubpixelSmoothingRight;
            mFrame.bottom -= mSubpixelSmoothingRight;

            // set the battery charging color
            mBatteryPaint.setColor(tracker.plugged ? mChargeColor : getColorForLevel(level));

            if (level >= FULL) {
                drawFrac = 1f;
            } else if (level <= mCriticalLevel) {
                drawFrac = 0f;
            }

            final float levelTop;

            if (drawFrac == 1f) {
                if (mHorizontal) {
                    levelTop = mButtonFrame.right;
                } else {
                    levelTop = mButtonFrame.top;
                }
            } else {
                if (mHorizontal) {
                    levelTop = (mFrame.right - (mFrame.width() * (1f - drawFrac)));
                } else {
                    levelTop = (mFrame.top + (mFrame.height() * (1f - drawFrac)));
                }
            }

            // define the battery shape
            mShapePath.reset();
            mShapePath.moveTo(mButtonFrame.left, mButtonFrame.top);
            if (mHorizontal) {
                mShapePath.lineTo(mButtonFrame.right, mButtonFrame.top);
                mShapePath.lineTo(mButtonFrame.right, mButtonFrame.bottom);
                mShapePath.lineTo(mButtonFrame.left, mButtonFrame.bottom);
                mShapePath.lineTo(mFrame.right, mFrame.bottom);
                mShapePath.lineTo(mFrame.left, mFrame.bottom);
                mShapePath.lineTo(mFrame.left, mFrame.top);
                mShapePath.lineTo(mButtonFrame.left, mFrame.top);
                mShapePath.lineTo(mButtonFrame.left, mButtonFrame.top);
            } else {
                mShapePath.lineTo(mButtonFrame.right, mButtonFrame.top);
                mShapePath.lineTo(mButtonFrame.right, mFrame.top);
                mShapePath.lineTo(mFrame.right, mFrame.top);
                mShapePath.lineTo(mFrame.right, mFrame.bottom);
                mShapePath.lineTo(mFrame.left, mFrame.bottom);
                mShapePath.lineTo(mFrame.left, mFrame.top);
                mShapePath.lineTo(mButtonFrame.left, mFrame.top);
                mShapePath.lineTo(mButtonFrame.left, mButtonFrame.top);
            }

            if (tracker.plugged) {
                // define the bolt shape
                final float bl = mFrame.left + mFrame.width() / (mHorizontal ? 9f : 4.5f);
                final float bt = mFrame.top + mFrame.height() / (mHorizontal ? 4.5f : 6f);
                final float br = mFrame.right - mFrame.width() / (mHorizontal ? 6f : 7f);
                final float bb = mFrame.bottom - mFrame.height() / (mHorizontal ? 7f : 10f);
                if (mBoltFrame.left != bl || mBoltFrame.top != bt
                        || mBoltFrame.right != br || mBoltFrame.bottom != bb) {
                    mBoltFrame.set(bl, bt, br, bb);
                    mBoltPath.reset();
                    mBoltPath.moveTo(
                            mBoltFrame.left + mBoltPoints[0] * mBoltFrame.width(),
                            mBoltFrame.top + mBoltPoints[1] * mBoltFrame.height());
                    for (int i = 2; i < mBoltPoints.length; i += 2) {
                        mBoltPath.lineTo(
                                mBoltFrame.left + mBoltPoints[i] * mBoltFrame.width(),
                                mBoltFrame.top + mBoltPoints[i + 1] * mBoltFrame.height());
                    }
                    mBoltPath.lineTo(
                            mBoltFrame.left + mBoltPoints[0] * mBoltFrame.width(),
                            mBoltFrame.top + mBoltPoints[1] * mBoltFrame.height());
                }

                float boltPct = mHorizontal ?
                        (mBoltFrame.left - levelTop) / (mBoltFrame.left - mBoltFrame.right) :
                        (mBoltFrame.bottom - levelTop) / (mBoltFrame.bottom - mBoltFrame.top);
                boltPct = Math.min(Math.max(boltPct, 0), 1);
                if (boltPct <= BOLT_LEVEL_THRESHOLD) {
                    // draw the bolt if opaque
                    c.drawPath(mBoltPath, mBoltPaint);
                } else {
                    // otherwise cut the bolt out of the overall shape
                    mShapePath.op(mBoltPath, Path.Op.DIFFERENCE);
                }
            }

            // compute percentage text
            boolean pctOpaque = false;
            float pctX = 0, pctY = 0;
            String pctText = null;
            if (!tracker.plugged && level > mCriticalLevel && (mShowPercent
                    && !(tracker.level == 100 && !SHOW_100_PERCENT))) {
                mTextPaint.setColor(getColorForLevel(level));
                final float full = mHorizontal ? 0.60f : 0.45f;
                final float nofull = mHorizontal ? 0.75f : 0.6f;
                final float single = mHorizontal ? 0.86f : 0.75f;
                mTextPaint.setTextSize(height *
                        (SINGLE_DIGIT_PERCENT ? single
                                : (tracker.level == 100 ? full : nofull)));
                mTextHeight = -mTextPaint.getFontMetrics().ascent;
                pctText = String.valueOf(SINGLE_DIGIT_PERCENT ? (level/10) : level);
                pctX = mWidth * 0.5f;
                pctY = (mHeight + mTextHeight) * 0.47f;
                if (mHorizontal) {
                    pctOpaque = pctX > levelTop;
                } else {
                    pctOpaque = levelTop > pctY;
                }
                if (!pctOpaque) {
                    mTextPath.reset();
                    mTextPaint.getTextPath(pctText, 0, pctText.length(), pctX, pctY, mTextPath);
                    // cut the percentage text out of the overall shape
                    mShapePath.op(mTextPath, Path.Op.DIFFERENCE);
                }
            }

            // draw the battery shape background
            c.drawPath(mShapePath, mFramePaint);

            // draw the battery shape, clipped to charging level
            if (mHorizontal) {
                mFrame.right = levelTop;
            } else {
                mFrame.top = levelTop;
            }
            mClipPath.reset();
            mClipPath.addRect(mFrame,  Path.Direction.CCW);
            mShapePath.op(mClipPath, Path.Op.INTERSECT);
            c.drawPath(mShapePath, mBatteryPaint);

            if (!tracker.plugged) {
                if (level <= mCriticalLevel) {
                    // draw the warning text
                    final float x = mWidth * 0.5f;
                    final float y = (mHeight + mWarningTextHeight) * 0.48f;
                    c.drawText(mWarningString, x, y, mWarningTextPaint);
                } else if (pctOpaque) {
                    // draw the percentage text
                    c.drawText(pctText, pctX, pctY, mTextPaint);
                }
            }
        }

        @Override
        public void onDispose() {
            mHandler.removeCallbacks(mInvalidate);
            mDisposed = true;
        }

        @Override
        public void onSizeChanged(int w, int h, int oldw, int oldh) {
            mHeight = h;
            mWidth = w;
            mWarningTextPaint.setTextSize(h * 0.75f);
            mWarningTextHeight = -mWarningTextPaint.getFontMetrics().ascent;
        }

        private float[] loadBoltPoints(Resources res) {
            final int[] pts = res.getIntArray((mHorizontal
                                                ? R.array.batterymeter_inverted_bolt_points
                                                : R.array.batterymeter_bolt_points));
            int maxX = 0, maxY = 0;
            for (int i = 0; i < pts.length; i += 2) {
                maxX = Math.max(maxX, pts[i]);
                maxY = Math.max(maxY, pts[i + 1]);
            }
            final float[] ptsF = new float[pts.length];
            for (int i = 0; i < pts.length; i += 2) {
                ptsF[i] = (float)pts[i] / maxX;
                ptsF[i + 1] = (float)pts[i + 1] / maxY;
            }
            return ptsF;
        }
    }

    protected class CircleBatteryMeterDrawable implements BatteryMeterDrawable {
        private static final boolean SINGLE_DIGIT_PERCENT = false;
        private static final boolean SHOW_100_PERCENT = false;

        private static final int FULL = 96;

        public static final float STROKE_WITH = 6.5f;

        private boolean mDisposed;

        private int     mAnimOffset;
        private boolean mIsAnimating;   // stores charge-animation status to reliably
                                        //remove callbacks

        private int     mCircleSize;    // draw size of circle
        private RectF   mRectLeft;      // contains the precalculated rect used in drawArc(),
                                        // derived from mCircleSize
        private float   mTextX, mTextY; // precalculated position for drawText() to appear centered

        private Paint   mTextPaint;
        private Paint   mFrontPaint;
        private Paint   mBackPaint;
        private Paint   mBoltPaint;
        private Paint   mWarningTextPaint;

        private final RectF mBoltFrame = new RectF();

        private final int mChargeColor;
        private final float[] mBoltPoints;
        private final Path mBoltPath = new Path();

        public CircleBatteryMeterDrawable(Resources res) {
            super();
            mDisposed = false;

            mTextPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
            Typeface font = Typeface.create("sans-serif-condensed", Typeface.BOLD);
            mTextPaint.setTypeface(font);
            mTextPaint.setTextAlign(Paint.Align.CENTER);

            mFrontPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
            mFrontPaint.setStrokeCap(Paint.Cap.BUTT);
            mFrontPaint.setDither(true);
            mFrontPaint.setStrokeWidth(0);
            mFrontPaint.setStyle(Paint.Style.STROKE);

            mBackPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
            mBackPaint.setColor(res.getColor(R.color.batterymeter_frame_color));
            mBackPaint.setStrokeCap(Paint.Cap.BUTT);
            mBackPaint.setDither(true);
            mBackPaint.setStrokeWidth(0);
            mBackPaint.setStyle(Paint.Style.STROKE);

            mWarningTextPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
            mWarningTextPaint.setColor(mColors[1]);
            font = Typeface.create("sans-serif", Typeface.BOLD);
            mWarningTextPaint.setTypeface(font);
            mWarningTextPaint.setTextAlign(Paint.Align.CENTER);

            mChargeColor = getResources().getColor(R.color.batterymeter_charge_color);

            mBoltPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
            mBoltPaint.setColor(res.getColor(R.color.batterymeter_bolt_color));
            mBoltPoints = loadBoltPoints(res);
        }

        @Override
        public void onDraw(Canvas c, BatteryTracker tracker) {
            if (mDisposed) return;

            if (mRectLeft == null) {
                initSizeBasedStuff();
            }

            updateChargeAnim(tracker);
            drawCircle(c, tracker, mTextX, mRectLeft);
        }

        @Override
        public void onDispose() {
            mHandler.removeCallbacks(mInvalidate);
            mDisposed = true;
        }

        @Override
        public void onSizeChanged(int w, int h, int oldw, int oldh) {
            initSizeBasedStuff();
        }

        private float[] loadBoltPoints(Resources res) {
            final int[] pts = res.getIntArray(R.array.batterymeter_bolt_points);
            int maxX = 0, maxY = 0;
            for (int i = 0; i < pts.length; i += 2) {
                maxX = Math.max(maxX, pts[i]);
                maxY = Math.max(maxY, pts[i + 1]);
            }
            final float[] ptsF = new float[pts.length];
            for (int i = 0; i < pts.length; i += 2) {
                ptsF[i] = (float)pts[i] / maxX;
                ptsF[i + 1] = (float)pts[i + 1] / maxY;
            }
            return ptsF;
        }

        private void drawCircle(Canvas canvas, BatteryTracker tracker,
                float textX, RectF drawRect) {
            boolean unknownStatus = tracker.status == BatteryManager.BATTERY_STATUS_UNKNOWN;
            int level = tracker.level;
            Paint paint;

            if (unknownStatus) {
                paint = mBackPaint;
                level = 100; // Draw all the circle;
            } else {
                paint = mFrontPaint;
                paint.setColor(getColorForLevel(level));
                if (tracker.status == BatteryManager.BATTERY_STATUS_FULL) {
                    level = 100;
                }
            }

            // draw thin gray ring first
            canvas.drawArc(drawRect, 270, 360, false, mBackPaint);
            // draw colored arc representing charge level
            canvas.drawArc(drawRect, 270 + mAnimOffset, 3.6f * level, false, paint);
            // if chosen by options, draw percentage text in the middle
            // always skip percentage when 100, so layout doesnt break
            if (unknownStatus) {
                mTextPaint.setColor(paint.getColor());
                canvas.drawText("?", textX, mTextY, mTextPaint);

            } else if (tracker.plugged) {
                // draw the bolt
                final float bl = (int)(drawRect.left + drawRect.width() / 3.2f);
                final float bt = (int)(drawRect.top + drawRect.height() / 4f);
                final float br = (int)(drawRect.right - drawRect.width() / 5.2f);
                final float bb = (int)(drawRect.bottom - drawRect.height() / 8f);
                if (mBoltFrame.left != bl || mBoltFrame.top != bt
                        || mBoltFrame.right != br || mBoltFrame.bottom != bb) {
                    mBoltFrame.set(bl, bt, br, bb);
                    mBoltPath.reset();
                    mBoltPath.moveTo(
                            mBoltFrame.left + mBoltPoints[0] * mBoltFrame.width(),
                            mBoltFrame.top + mBoltPoints[1] * mBoltFrame.height());
                    for (int i = 2; i < mBoltPoints.length; i += 2) {
                        mBoltPath.lineTo(
                                mBoltFrame.left + mBoltPoints[i] * mBoltFrame.width(),
                                mBoltFrame.top + mBoltPoints[i + 1] * mBoltFrame.height());
                    }
                    mBoltPath.lineTo(
                            mBoltFrame.left + mBoltPoints[0] * mBoltFrame.width(),
                            mBoltFrame.top + mBoltPoints[1] * mBoltFrame.height());
                }
                canvas.drawPath(mBoltPath, mBoltPaint);

            } else {
                if (level > mCriticalLevel
                        && (mShowPercent && !(tracker.level == 100 && !SHOW_100_PERCENT))) {
                    // draw the percentage text
                    String pctText = String.valueOf(SINGLE_DIGIT_PERCENT ? (level/10) : level);
                    mTextPaint.setColor(paint.getColor());
                    canvas.drawText(pctText, textX, mTextY, mTextPaint);
                } else if (level <= mCriticalLevel) {
                    // draw the warning text
                    canvas.drawText(mWarningString, textX, mTextY, mWarningTextPaint);
                }
            }
        }

        /**
         * updates the animation counter
         * cares for timed callbacks to continue animation cycles
         * uses mInvalidate for delayed invalidate() callbacks
         */
        private void updateChargeAnim(BatteryTracker tracker) {
            // Stop animation when battery is full or after the meter
            // rotated back to 0 after unplugging.
            if (!tracker.shouldIndicateCharging() && mAnimOffset == 0
                    || tracker.status == BatteryManager.BATTERY_STATUS_FULL) {
                if (mIsAnimating) {
                    mIsAnimating = false;
                    mAnimOffset = 0;
                    mHandler.removeCallbacks(mInvalidate);
                }
                return;
            }

            mIsAnimating = true;

            if (mAnimOffset > 360) {
                mAnimOffset = 0;
            } else {
                mAnimOffset += 3;
            }

            mHandler.removeCallbacks(mInvalidate);
            mHandler.postDelayed(mInvalidate, 50);
        }

        /**
         * initializes all size dependent variables
         * sets stroke width and text size of all involved paints
         * YES! i think the method name is appropriate
         */
        private void initSizeBasedStuff() {
            mCircleSize = Math.min(getMeasuredWidth(), getMeasuredHeight());
            mTextPaint.setTextSize(mCircleSize / 2f);
            mWarningTextPaint.setTextSize(mCircleSize / 2f);

            float strokeWidth = mCircleSize / STROKE_WITH;
            mFrontPaint.setStrokeWidth(strokeWidth);
            mBackPaint.setStrokeWidth(strokeWidth);

            // calculate rectangle for drawArc calls
            int pLeft = getPaddingLeft();
            mRectLeft = new RectF(pLeft + strokeWidth / 2.0f, 0 + strokeWidth / 2.0f, mCircleSize
                    - strokeWidth / 2.0f + pLeft, mCircleSize - strokeWidth / 2.0f);

            // calculate Y position for text
            Rect bounds = new Rect();
            mTextPaint.getTextBounds("99", 0, "99".length(), bounds);
            mTextX = mCircleSize / 2.0f + getPaddingLeft();
            // the +1dp at end of formula balances out rounding issues.works out on all resolutions
            mTextY = mCircleSize / 2.0f + (bounds.bottom - bounds.top) / 2.0f
                    - strokeWidth / 2.0f + getResources().getDisplayMetrics().density;
        }
    }
}


File: packages/SystemUI/src/com/android/systemui/statusbar/phone/KeyguardStatusBarView.java
/*
 * Copyright (C) 2014 The Android Open Source Project
 * Copyright (C) 2014 The CyanogenMod Project
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
 * limitations under the License
 */

package com.android.systemui.statusbar.phone;

import android.animation.LayoutTransition;
import android.content.Context;
import android.graphics.drawable.Drawable;
import android.util.AttributeSet;
import android.view.View;
import android.view.ViewTreeObserver;
import android.view.animation.AnimationUtils;
import android.view.animation.Interpolator;
import android.widget.ImageView;
import android.widget.RelativeLayout;
import android.widget.TextView;

import com.android.systemui.BatteryMeterView;
import com.android.systemui.BatteryLevelTextView;
import com.android.systemui.R;
import com.android.systemui.statusbar.policy.BatteryController;
import com.android.systemui.statusbar.policy.KeyguardUserSwitcher;
import com.android.systemui.statusbar.policy.UserInfoController;

import java.text.NumberFormat;

/**
 * The header group on Keyguard.
 */
public class KeyguardStatusBarView extends RelativeLayout {

    private boolean mKeyguardUserSwitcherShowing;

    private View mSystemIconsSuperContainer;
    private MultiUserSwitch mMultiUserSwitch;
    private ImageView mMultiUserAvatar;
    private BatteryLevelTextView mBatteryLevel;

    private BatteryController mBatteryController;
    private KeyguardUserSwitcher mKeyguardUserSwitcher;

    private int mSystemIconsSwitcherHiddenExpandedMargin;
    private Interpolator mFastOutSlowInInterpolator;

    public KeyguardStatusBarView(Context context, AttributeSet attrs) {
        super(context, attrs);
    }

    @Override
    protected void onFinishInflate() {
        super.onFinishInflate();
        mSystemIconsSuperContainer = findViewById(R.id.system_icons_super_container);
        mMultiUserSwitch = (MultiUserSwitch) findViewById(R.id.multi_user_switch);
        mMultiUserAvatar = (ImageView) findViewById(R.id.multi_user_avatar);
        mBatteryLevel = (BatteryLevelTextView) findViewById(R.id.battery_level_text);
        loadDimens();
        mFastOutSlowInInterpolator = AnimationUtils.loadInterpolator(getContext(),
                android.R.interpolator.fast_out_slow_in);
        updateUserSwitcher();
        updateVisibilities();
    }

    private void loadDimens() {
        mSystemIconsSwitcherHiddenExpandedMargin = getResources().getDimensionPixelSize(
                R.dimen.system_icons_switcher_hidden_expanded_margin);
    }

    private void updateVisibilities() {
        if (mMultiUserSwitch.getParent() != this && !mKeyguardUserSwitcherShowing) {
            if (mMultiUserSwitch.getParent() != null) {
                getOverlay().remove(mMultiUserSwitch);
            }
            addView(mMultiUserSwitch, 0);
        } else if (mMultiUserSwitch.getParent() == this && mKeyguardUserSwitcherShowing) {
            removeView(mMultiUserSwitch);
        }
        mBatteryLevel.setVisibility(View.VISIBLE);
    }

    private void updateSystemIconsLayoutParams() {
        RelativeLayout.LayoutParams lp =
                (LayoutParams) mSystemIconsSuperContainer.getLayoutParams();
        int marginEnd = mKeyguardUserSwitcherShowing ? mSystemIconsSwitcherHiddenExpandedMargin : 0;
        if (marginEnd != lp.getMarginEnd()) {
            lp.setMarginEnd(marginEnd);
            mSystemIconsSuperContainer.setLayoutParams(lp);
        }
    }

    private void updateUserSwitcher() {
        boolean keyguardSwitcherAvailable = mKeyguardUserSwitcher != null;
        mMultiUserSwitch.setClickable(keyguardSwitcherAvailable);
        mMultiUserSwitch.setFocusable(keyguardSwitcherAvailable);
        mMultiUserSwitch.setKeyguardMode(keyguardSwitcherAvailable);
    }

    public void setBatteryController(BatteryController batteryController) {
        mBatteryController = batteryController;
        ((BatteryMeterView) findViewById(R.id.battery)).setBatteryController(batteryController);
        mBatteryLevel.setBatteryController(batteryController);
    }

    public void setUserInfoController(UserInfoController userInfoController) {
        userInfoController.addListener(new UserInfoController.OnUserInfoChangedListener() {
            @Override
            public void onUserInfoChanged(String name, Drawable picture) {
                mMultiUserAvatar.setImageDrawable(picture);
            }
        });
    }

    public void setKeyguardUserSwitcher(KeyguardUserSwitcher keyguardUserSwitcher) {
        mKeyguardUserSwitcher = keyguardUserSwitcher;
        mMultiUserSwitch.setKeyguardUserSwitcher(keyguardUserSwitcher);
        updateUserSwitcher();
    }

    public void setKeyguardUserSwitcherShowing(boolean showing, boolean animate) {
        mKeyguardUserSwitcherShowing = showing;
        if (animate) {
            animateNextLayoutChange();
        }
        updateVisibilities();
        updateSystemIconsLayoutParams();
    }

    private void animateNextLayoutChange() {
        final int systemIconsCurrentX = mSystemIconsSuperContainer.getLeft();
        final boolean userSwitcherVisible = mMultiUserSwitch.getParent() == this;
        getViewTreeObserver().addOnPreDrawListener(new ViewTreeObserver.OnPreDrawListener() {
            @Override
            public boolean onPreDraw() {
                getViewTreeObserver().removeOnPreDrawListener(this);
                boolean userSwitcherHiding = userSwitcherVisible
                        && mMultiUserSwitch.getParent() != KeyguardStatusBarView.this;
                mSystemIconsSuperContainer.setX(systemIconsCurrentX);
                mSystemIconsSuperContainer.animate()
                        .translationX(0)
                        .setDuration(400)
                        .setStartDelay(userSwitcherHiding ? 300 : 0)
                        .setInterpolator(mFastOutSlowInInterpolator)
                        .start();
                if (userSwitcherHiding) {
                    getOverlay().add(mMultiUserSwitch);
                    mMultiUserSwitch.animate()
                            .alpha(0f)
                            .setDuration(300)
                            .setStartDelay(0)
                            .setInterpolator(PhoneStatusBar.ALPHA_OUT)
                            .withEndAction(new Runnable() {
                                @Override
                                public void run() {
                                    mMultiUserSwitch.setAlpha(1f);
                                    getOverlay().remove(mMultiUserSwitch);
                                }
                            })
                            .start();

                } else {
                    mMultiUserSwitch.setAlpha(0f);
                    mMultiUserSwitch.animate()
                            .alpha(1f)
                            .setDuration(300)
                            .setStartDelay(200)
                            .setInterpolator(PhoneStatusBar.ALPHA_IN);
                }
                return true;
            }
        });

    }

    @Override
    public void setVisibility(int visibility) {
        super.setVisibility(visibility);
        if (visibility != View.VISIBLE) {
            mSystemIconsSuperContainer.animate().cancel();
            mMultiUserSwitch.animate().cancel();
            mMultiUserSwitch.setAlpha(1f);
        }
    }

    @Override
    public boolean hasOverlappingRendering() {
        return false;
    }
}


File: packages/SystemUI/src/com/android/systemui/statusbar/phone/PhoneStatusBar.java
/*
 * Copyright (c) 2012-2014 The Linux Foundation. All rights reserved.
 * Not a Contribution.
 * Copyright (C) 2010 The Android Open Source Project
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

package com.android.systemui.statusbar.phone;


import static android.app.StatusBarManager.NAVIGATION_HINT_BACK_ALT;
import static android.app.StatusBarManager.NAVIGATION_HINT_IME_SHOWN;
import static android.app.StatusBarManager.WINDOW_STATE_HIDDEN;
import static android.app.StatusBarManager.WINDOW_STATE_SHOWING;
import static android.app.StatusBarManager.windowStateToString;
import static com.android.systemui.settings.BrightnessController.BRIGHTNESS_ADJ_RESOLUTION;
import static com.android.systemui.statusbar.phone.BarTransitions.MODE_LIGHTS_OUT;
import static com.android.systemui.statusbar.phone.BarTransitions.MODE_LIGHTS_OUT_TRANSPARENT;
import static com.android.systemui.statusbar.phone.BarTransitions.MODE_OPAQUE;
import static com.android.systemui.statusbar.phone.BarTransitions.MODE_SEMI_TRANSPARENT;
import static com.android.systemui.statusbar.phone.BarTransitions.MODE_TRANSLUCENT;
import static com.android.systemui.statusbar.phone.BarTransitions.MODE_TRANSPARENT;
import static com.android.systemui.statusbar.phone.BarTransitions.MODE_WARNING;

import android.animation.Animator;
import android.animation.AnimatorListenerAdapter;
import android.animation.TimeInterpolator;
import android.annotation.NonNull;
import android.app.ActivityManager;
import android.app.ActivityManagerNative;
import android.app.IActivityManager;
import android.app.Notification;
import android.app.PendingIntent;
import android.app.StatusBarManager;
import android.app.WallpaperManager;
import android.content.ActivityNotFoundException;
import android.content.ComponentCallbacks2;
import android.content.BroadcastReceiver;
import android.content.ComponentName;
import android.content.ContentResolver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.content.res.Configuration;
import android.content.res.ThemeChangeRequest.RequestType;
import android.content.res.ThemeConfig;
import android.content.res.Resources;
import android.database.ContentObserver;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.PixelFormat;
import android.graphics.Point;
import android.graphics.PointF;
import android.graphics.PorterDuff;
import android.graphics.PorterDuffXfermode;
import android.graphics.Rect;
import android.graphics.drawable.ColorDrawable;
import android.graphics.drawable.Drawable;
import android.inputmethodservice.InputMethodService;
import android.media.AudioAttributes;
import android.media.MediaMetadata;
import android.media.session.MediaController;
import android.media.session.MediaSession;
import android.media.session.MediaSessionManager;
import android.media.session.PlaybackState;
import android.os.AsyncTask;
import android.os.Bundle;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.IBinder;
import android.os.IPowerManager;
import android.os.Message;
import android.os.PowerManager;
import android.os.Process;
import android.os.RemoteException;
import android.os.ServiceManager;
import android.os.SystemClock;
import android.os.UserHandle;
import android.provider.Settings;
import android.service.notification.NotificationListenerService;
import android.service.notification.NotificationListenerService.RankingMap;
import android.service.notification.StatusBarNotification;
import android.telephony.TelephonyManager;
import android.text.TextUtils;
import android.util.ArraySet;
import android.util.DisplayMetrics;
import android.util.EventLog;
import android.util.Log;
import android.util.Pair;
import android.view.Display;
import android.view.Gravity;
import android.view.HardwareCanvas;
import android.view.KeyEvent;
import android.view.LayoutInflater;
import android.view.HapticFeedbackConstants;
import android.view.MotionEvent;
import android.view.VelocityTracker;
import android.view.View;
import android.view.View.OnClickListener;
import android.view.ViewConfiguration;
import android.view.ViewGroup;
import android.view.ViewGroup.LayoutParams;
import android.view.ViewPropertyAnimator;
import android.view.ViewStub;
import android.view.ViewTreeObserver;
import android.view.WindowManager;
import android.view.WindowManagerGlobal;
import android.view.accessibility.AccessibilityEvent;
import android.view.animation.AccelerateDecelerateInterpolator;
import android.view.animation.AccelerateInterpolator;
import android.view.animation.Animation;
import android.view.animation.AnimationUtils;
import android.view.animation.DecelerateInterpolator;
import android.view.animation.Interpolator;
import android.view.animation.LinearInterpolator;
import android.view.animation.PathInterpolator;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import com.android.internal.statusbar.StatusBarIcon;
import com.android.internal.util.cm.ActionUtils;
import com.android.keyguard.KeyguardHostView.OnDismissAction;
import com.android.keyguard.ViewMediatorCallback;
import com.android.systemui.BatteryMeterView;
import com.android.systemui.BatteryLevelTextView;
import com.android.systemui.DemoMode;
import com.android.systemui.EventLogConstants;
import com.android.systemui.EventLogTags;
import com.android.systemui.FontSizeUtils;
import com.android.systemui.R;
import com.android.systemui.cm.UserContentObserver;
import com.android.systemui.doze.DozeHost;
import com.android.systemui.doze.DozeLog;
import com.android.systemui.keyguard.KeyguardViewMediator;
import com.android.systemui.qs.QSPanel;
import com.android.systemui.recent.ScreenPinningRequest;
import com.android.systemui.settings.BrightnessController;
import com.android.systemui.statusbar.ActivatableNotificationView;
import com.android.systemui.statusbar.BackDropView;
import com.android.systemui.statusbar.BaseStatusBar;
import com.android.systemui.statusbar.CommandQueue;
import com.android.systemui.statusbar.DismissView;
import com.android.systemui.statusbar.DragDownHelper;
import com.android.systemui.statusbar.EmptyShadeView;
import com.android.systemui.statusbar.ExpandableNotificationRow;
import com.android.systemui.statusbar.GestureRecorder;
import com.android.systemui.statusbar.KeyguardIndicationController;
import com.android.systemui.statusbar.NotificationData;
import com.android.systemui.statusbar.NotificationData.Entry;
import com.android.systemui.statusbar.NotificationOverflowContainer;
import com.android.systemui.statusbar.ScrimView;
import com.android.systemui.statusbar.SignalClusterView;
import com.android.systemui.statusbar.SpeedBumpView;
import com.android.systemui.statusbar.StatusBarIconView;
import com.android.systemui.statusbar.StatusBarState;
import com.android.systemui.statusbar.phone.UnlockMethodCache.OnUnlockMethodChangedListener;
import com.android.systemui.statusbar.policy.AccessibilityController;
import com.android.systemui.statusbar.policy.BatteryController;
import com.android.systemui.statusbar.policy.BatteryController.BatteryStateChangeCallback;
import com.android.systemui.statusbar.policy.BluetoothControllerImpl;
import com.android.systemui.statusbar.policy.BrightnessMirrorController;
import com.android.systemui.statusbar.policy.CastControllerImpl;
import com.android.systemui.statusbar.policy.Clock;
import com.android.systemui.statusbar.policy.HeadsUpNotificationView;
import com.android.systemui.statusbar.policy.HotspotControllerImpl;
import com.android.systemui.statusbar.policy.KeyButtonView;
import com.android.systemui.statusbar.policy.KeyguardMonitor;
import com.android.systemui.statusbar.policy.KeyguardUserSwitcher;
import com.android.systemui.statusbar.policy.LocationControllerImpl;
import com.android.systemui.statusbar.policy.NetworkControllerImpl;
import com.android.systemui.statusbar.policy.NextAlarmController;
import com.android.systemui.statusbar.policy.PreviewInflater;
import com.android.systemui.statusbar.policy.RotationLockControllerImpl;
import com.android.systemui.statusbar.policy.SecurityControllerImpl;
import com.android.systemui.statusbar.policy.SuControllerImpl;
import com.android.systemui.statusbar.policy.UserInfoController;
import com.android.systemui.statusbar.policy.UserSwitcherController;
import com.android.systemui.statusbar.policy.WeatherControllerImpl;
import com.android.systemui.statusbar.policy.ZenModeController;
import com.android.systemui.statusbar.stack.NotificationStackScrollLayout;
import com.android.systemui.statusbar.stack.NotificationStackScrollLayout.OnChildLocationsChangedListener;
import com.android.systemui.statusbar.stack.StackScrollAlgorithm;
import com.android.systemui.statusbar.stack.StackScrollState.ViewState;
import com.android.systemui.volume.VolumeComponent;
import cyanogenmod.app.CustomTileListenerService;
import cyanogenmod.app.StatusBarPanelCustomTile;

import java.io.FileDescriptor;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Map;

public class PhoneStatusBar extends BaseStatusBar implements DemoMode,
        DragDownHelper.DragDownCallback, ActivityStarter, OnUnlockMethodChangedListener {
    static final String TAG = "PhoneStatusBar";
    public static final boolean DEBUG = BaseStatusBar.DEBUG;
    public static final boolean SPEW = false;
    public static final boolean DUMPTRUCK = true; // extra dumpsys info
    public static final boolean DEBUG_GESTURES = false;
    public static final boolean DEBUG_MEDIA = false;
    public static final boolean DEBUG_MEDIA_FAKE_ARTWORK = false;

    public static final boolean DEBUG_WINDOW_STATE = false;

    // additional instrumentation for testing purposes; intended to be left on during development
    public static final boolean CHATTY = DEBUG;

    public static final String ACTION_STATUSBAR_START
            = "com.android.internal.policy.statusbar.START";

    public static final boolean SHOW_LOCKSCREEN_MEDIA_ARTWORK = true;

    private static final int MSG_OPEN_NOTIFICATION_PANEL = 1000;
    private static final int MSG_CLOSE_PANELS = 1001;
    private static final int MSG_OPEN_SETTINGS_PANEL = 1002;
    private static final int MSG_LAUNCH_TRANSITION_TIMEOUT = 1003;
    private static final int MSG_UPDATE_NOTIFICATIONS = 1004;
    // 1020-1040 reserved for BaseStatusBar

    // Time after we abort the launch transition.
    private static final long LAUNCH_TRANSITION_TIMEOUT_MS = 5000;

    private static final boolean CLOSE_PANEL_WHEN_EMPTIED = true;

    private static final int NOTIFICATION_PRIORITY_MULTIPLIER = 10; // see NotificationManagerService
    private static final int HIDE_ICONS_BELOW_SCORE = Notification.PRIORITY_LOW * NOTIFICATION_PRIORITY_MULTIPLIER;

    private static final int STATUS_OR_NAV_TRANSIENT =
            View.STATUS_BAR_TRANSIENT | View.NAVIGATION_BAR_TRANSIENT;
    private static final long AUTOHIDE_TIMEOUT_MS = 3000;
    private static final long AUTOHIDE_TIMEOUT_MS_PROVISIONING = 0;

    /** The minimum delay in ms between reports of notification visibility. */
    private static final int VISIBILITY_REPORT_MIN_DELAY_MS = 500;

    /**
     * The delay to reset the hint text when the hint animation is finished running.
     */
    private static final int HINT_RESET_DELAY_MS = 4000;

    private static final AudioAttributes VIBRATION_ATTRIBUTES = new AudioAttributes.Builder()
            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
            .setUsage(AudioAttributes.USAGE_ASSISTANCE_SONIFICATION)
            .build();

    private static final float BRIGHTNESS_CONTROL_PADDING = 0.15f;
    private static final int BRIGHTNESS_CONTROL_LONG_PRESS_TIMEOUT = 750; // ms
    private static final int BRIGHTNESS_CONTROL_LINGER_THRESHOLD = 20;

    public static final int FADE_KEYGUARD_START_DELAY = 100;
    public static final int FADE_KEYGUARD_DURATION = 300;

    /** Allow some time inbetween the long press for back and recents. */
    private static final int LOCK_TO_APP_GESTURE_TOLERENCE = 200;

    PhoneStatusBarPolicy mIconPolicy;

    // These are no longer handled by the policy, because we need custom strategies for them
    BluetoothControllerImpl mBluetoothController;
    SecurityControllerImpl mSecurityController;
    BatteryController mBatteryController;
    LocationControllerImpl mLocationController;
    NetworkControllerImpl mNetworkController;
    HotspotControllerImpl mHotspotController;
    RotationLockControllerImpl mRotationLockController;
    UserInfoController mUserInfoController;
    ZenModeController mZenModeController;
    CastControllerImpl mCastController;
    VolumeComponent mVolumeComponent;
    KeyguardUserSwitcher mKeyguardUserSwitcher;
    UserSwitcherController mUserSwitcherController;
    NextAlarmController mNextAlarmController;
    KeyguardMonitor mKeyguardMonitor;
    BrightnessMirrorController mBrightnessMirrorController;
    AccessibilityController mAccessibilityController;
    WeatherControllerImpl mWeatherController;
    SuControllerImpl mSuController;

    int mNaturalBarHeight = -1;
    int mIconSize = -1;
    int mIconHPadding = -1;
    Display mDisplay;
    Point mCurrentDisplaySize = new Point();

    StatusBarWindowView mStatusBarWindow;
    FrameLayout mStatusBarWindowContent;
    PhoneStatusBarView mStatusBarView;
    private int mStatusBarWindowState = WINDOW_STATE_SHOWING;
    private StatusBarWindowManager mStatusBarWindowManager;
    private UnlockMethodCache mUnlockMethodCache;
    private DozeServiceHost mDozeServiceHost;
    private boolean mScreenOnComingFromTouch;
    private PointF mScreenOnTouchLocation;

    int mPixelFormat;
    Object mQueueLock = new Object();

    // viewgroup containing the normal contents of the statusbar
    LinearLayout mStatusBarContents;

    // right-hand icons
    LinearLayout mSystemIconArea;
    LinearLayout mSystemIcons;

    // left-hand icons
    LinearLayout mStatusIcons;
    LinearLayout mStatusIconsKeyguard;

    // the icons themselves
    IconMerger mNotificationIcons;
    View mNotificationIconArea;

    // [+>
    View mMoreIcon;
    TextView mClockView;
    Clock mClockController;
    private int mClockLocation;

    // expanded notifications
    NotificationPanelView mNotificationPanel; // the sliding/resizing panel within the notification window
    View mExpandedContents;
    int mNotificationPanelGravity;
    int mNotificationPanelMarginBottomPx;
    float mNotificationPanelMinHeightFrac;
    TextView mNotificationPanelDebugText;

    // settings
    View mFlipSettingsView;
    private QSPanel mQSPanel;
    private DevForceNavbarObserver mDevForceNavbarObserver;

    // top bar
    StatusBarHeaderView mHeader;
    KeyguardStatusBarView mKeyguardStatusBar;
    View mKeyguardStatusView;
    KeyguardBottomAreaView mKeyguardBottomArea;
    boolean mLeaveOpenOnKeyguardHide;
    KeyguardIndicationController mKeyguardIndicationController;

    private boolean mKeyguardFadingAway;
    private boolean mKeyguardShowingMedia;
    private long mKeyguardFadingAwayDelay;
    private long mKeyguardFadingAwayDuration;

    private Bitmap mKeyguardWallpaper;

    int mKeyguardMaxNotificationCount;

    // carrier/wifi label
    private TextView mCarrierLabel;
    private boolean mCarrierLabelVisible = false;
    private int mCarrierLabelHeight;
    private int mStatusBarHeaderHeight;

    private boolean mShowCarrierInPanel = false;

    // position
    int[] mPositionTmp = new int[2];
    boolean mExpandedVisible;

    private int mNavigationBarWindowState = WINDOW_STATE_SHOWING;

    // the tracker view
    int mTrackingPosition; // the position of the top of the tracking view.

    // ticker
    private boolean mTickerEnabled;
    private Ticker mTicker;
    private View mTickerView;
    private boolean mTicking;

    // Tracking finger for opening/closing.
    int mEdgeBorder; // corresponds to R.dimen.status_bar_edge_ignore
    boolean mTracking;
    VelocityTracker mVelocityTracker;

    int[] mAbsPos = new int[2];
    ArrayList<Runnable> mPostCollapseRunnables = new ArrayList<>();

    // last theme that was applied in order to detect theme change (as opposed
    // to some other configuration change).
    ThemeConfig mCurrentTheme;
    private boolean mRecreating = false;

    private boolean mAutomaticBrightness;
    private boolean mBrightnessControl;
    private boolean mBrightnessChanged;
    private float mScreenWidth;
    private int mMinBrightness;
    private boolean mJustPeeked;
    int mLinger;
    int mInitialTouchX;
    int mInitialTouchY;

    // for disabling the status bar
    int mDisabled = 0;

    // tracking calls to View.setSystemUiVisibility()
    int mSystemUiVisibility = View.SYSTEM_UI_FLAG_VISIBLE;

    DisplayMetrics mDisplayMetrics = new DisplayMetrics();

    // XXX: gesture research
    private final GestureRecorder mGestureRec = DEBUG_GESTURES
        ? new GestureRecorder("/sdcard/statusbar_gestures.dat")
        : null;

    private ScreenPinningRequest mScreenPinningRequest;

    private int mNavigationIconHints = 0;
    private HandlerThread mHandlerThread;

    Runnable mLongPressBrightnessChange = new Runnable() {
        @Override
        public void run() {
            mStatusBarView.performHapticFeedback(HapticFeedbackConstants.LONG_PRESS);
            adjustBrightness(mInitialTouchX);
            mLinger = BRIGHTNESS_CONTROL_LINGER_THRESHOLD + 1;
        }
    };

    // Custom Recents Long Press
    // - Tracks Event state for custom (user-configurable) Long Presses.
    private boolean mCustomRecentsLongPressed = false;
    // - The ArrayList is updated when packages are added and removed.
    private List<ComponentName> mCustomRecentsLongPressHandlerCandidates = new ArrayList<>();
    // - The custom Recents Long Press, if selected.  When null, use default (switch last app).
    private ComponentName mCustomRecentsLongPressHandler = null;

    class SettingsObserver extends UserContentObserver {
        SettingsObserver(Handler handler) {
            super(handler);
        }

        @Override
        protected void observe() {
            super.observe();

            ContentResolver resolver = mContext.getContentResolver();
            resolver.registerContentObserver(Settings.System.getUriFor(
                    Settings.System.STATUS_BAR_BRIGHTNESS_CONTROL), false, this,
                    UserHandle.USER_ALL);
            resolver.registerContentObserver(Settings.System.getUriFor(
                    Settings.System.SCREEN_BRIGHTNESS_MODE), false, this, UserHandle.USER_ALL);
            resolver.registerContentObserver(Settings.System.getUriFor(
                    Settings.System.STATUS_BAR_CLOCK), false, this, UserHandle.USER_ALL);
            resolver.registerContentObserver(Settings.System.getUriFor(
                    Settings.System.NAVBAR_LEFT_IN_LANDSCAPE), false, this, UserHandle.USER_ALL);
            resolver.registerContentObserver(Settings.Secure.getUriFor(
                    Settings.Secure.LOCKSCREEN_VISUALIZER_ENABLED), false, this, UserHandle.USER_ALL);
            resolver.registerContentObserver(Settings.Secure.getUriFor(
                    Settings.Secure.RECENTS_LONG_PRESS_ACTIVITY), false, this);
            update();
        }

        @Override
        protected void unobserve() {
            super.unobserve();
            ContentResolver resolver = mContext.getContentResolver();
            resolver.unregisterContentObserver(this);
        }

        @Override
        public void update() {
            ContentResolver resolver = mContext.getContentResolver();
            int mode = Settings.System.getIntForUser(mContext.getContentResolver(),
                            Settings.System.SCREEN_BRIGHTNESS_MODE,
                            Settings.System.SCREEN_BRIGHTNESS_MODE_MANUAL,
                            UserHandle.USER_CURRENT);
            mAutomaticBrightness = mode != Settings.System.SCREEN_BRIGHTNESS_MODE_MANUAL;
            mBrightnessControl = Settings.System.getIntForUser(
                    resolver, Settings.System.STATUS_BAR_BRIGHTNESS_CONTROL, 0,
                    UserHandle.USER_CURRENT) == 1;
            mVisualizerEnabled = Settings.Secure.getIntForUser(resolver,
                    Settings.Secure.LOCKSCREEN_VISUALIZER_ENABLED, 1,
                    UserHandle.USER_CURRENT) != 0;

            final int oldClockLocation = mClockLocation;
            final View oldClockView = mClockView;
            mClockLocation = Settings.System.getIntForUser(
                    resolver, Settings.System.STATUS_BAR_CLOCK, Clock.STYLE_CLOCK_RIGHT,
                    UserHandle.USER_CURRENT);
            updateClockView();

            // check to see if we need to adjust alpha/visibility
            // this fixes the bug where if User A has left and User B has center and you switch
            // from A to B then go into the settings and adjust the clock to left - without this
            // code block it will adjust the space but be transparent
            if (oldClockView != mClockView) {
                // if the new clock position is outside the system icon area, make the alpha
                // and visibility match the system icon area alpha/visibility
                if (isClockLocationOutsideSystemIconArea(mClockLocation)) {
                    mClockView.setAlpha(mSystemIconArea.getAlpha());
                    mClockView.setVisibility(mSystemIconArea.getVisibility());
                }

                // if the old clock position it outside the system icon area, make it opaque
                // and set visibility to gone
                if (isClockLocationOutsideSystemIconArea(oldClockLocation)) {
                    oldClockView.setAlpha(1f);
                    oldClockView.setVisibility(View.GONE);
                }
            }

            if (mNavigationBarView != null) {
                boolean navLeftInLandscape = Settings.System.getIntForUser(resolver,
                        Settings.System.NAVBAR_LEFT_IN_LANDSCAPE, 0, UserHandle.USER_CURRENT) == 1;
                mNavigationBarView.setLeftInLandscape(navLeftInLandscape);
            }

            // This method reads Settings.Secure.RECENTS_LONG_PRESS_ACTIVITY
            updateCustomRecentsLongPressHandler(false);
        }
    }

    void updateClockView() {
        mClockView.setVisibility(View.GONE);

        switch (mClockLocation) {
            default:
            case Clock.STYLE_HIDE_CLOCK:
                mClockView = (TextView) mStatusBarView.findViewById(R.id.clock);
                // Don't set visibility here...
                break;
            case Clock.STYLE_CLOCK_RIGHT:
                mClockView = (TextView) mStatusBarView.findViewById(R.id.clock);
                mClockView.setVisibility(View.VISIBLE);
                break;
            case Clock.STYLE_CLOCK_CENTER:
                mClockView = (TextView) mStatusBarView.findViewById(R.id.center_clock);
                mClockView.setVisibility(View.VISIBLE);
                break;
            case Clock.STYLE_CLOCK_LEFT:
                mClockView = (TextView) mStatusBarView.findViewById(R.id.left_clock);
                mClockView.setVisibility(View.VISIBLE);
                break;
        }

        setClockAndDateStatus();
        mClockController.updateClockView(mClockView);
    }

    public void setClockAndDateStatus() {
        if (mNotificationIcons != null) {
            mNotificationIcons.setClockAndDateStatus(mClockLocation);
        }
    }

    private static boolean isClockLocationOutsideSystemIconArea(int clockLocation) {
        return clockLocation == Clock.STYLE_CLOCK_CENTER
                || clockLocation == Clock.STYLE_CLOCK_LEFT;
    }

    class DevForceNavbarObserver extends UserContentObserver {
        DevForceNavbarObserver(Handler handler) {
            super(handler);
        }

        @Override
        protected void observe() {
            super.observe();
            ContentResolver resolver = mContext.getContentResolver();
            resolver.registerContentObserver(Settings.Secure.getUriFor(
                    Settings.Secure.DEV_FORCE_SHOW_NAVBAR), false, this, UserHandle.USER_ALL);
        }

        @Override
        public void update() {
            boolean visible = Settings.Secure.getIntForUser(mContext.getContentResolver(),
                    Settings.Secure.DEV_FORCE_SHOW_NAVBAR, 0, UserHandle.USER_CURRENT) == 1;

            if (visible) {
                forceAddNavigationBar();
            } else {
                removeNavigationBar();
            }

            // Send a broadcast to Settings to update Key disabling when user changes
            Intent intent = new Intent("com.cyanogenmod.action.UserChanged");
            intent.setPackage("com.android.settings");
            mContext.sendBroadcastAsUser(intent, new UserHandle(UserHandle.USER_CURRENT));
        }
    }

    private void forceAddNavigationBar() {
        // If we have no Navbar view and we should have one, create it
        if (mNavigationBarView != null) {
            return;
        }

        mNavigationBarView =
                (NavigationBarView) View.inflate(mContext, R.layout.navigation_bar, null);

        mNavigationBarView.setDisabledFlags(mDisabled);
        mNavigationBarView.setBar(this);
        mNavigationBarView.updateResources(getNavbarThemedResources());
        addNavigationBar(true); // dynamically adding nav bar, reset System UI visibility!
    }

    // ensure quick settings is disabled until the current user makes it through the setup wizard
    private boolean mUserSetup = false;
    private ContentObserver mUserSetupObserver = new ContentObserver(new Handler()) {
        @Override
        public void onChange(boolean selfChange) {
            final boolean userSetup = 0 != Settings.Secure.getIntForUser(
                    mContext.getContentResolver(),
                    Settings.Secure.USER_SETUP_COMPLETE,
                    0 /*default */,
                    mCurrentUserId);
            if (MULTIUSER_DEBUG) Log.d(TAG, String.format("User setup changed: " +
                    "selfChange=%s userSetup=%s mUserSetup=%s",
                    selfChange, userSetup, mUserSetup));

            if (userSetup != mUserSetup) {
                mUserSetup = userSetup;
                if (!mUserSetup && mStatusBarView != null)
                    animateCollapseQuickSettings();
            }
        }
    };

    final private ContentObserver mHeadsUpObserver = new ContentObserver(mHandler) {
        @Override
        public void onChange(boolean selfChange) {
            boolean wasUsing = mUseHeadsUp;
            mUseHeadsUp = ENABLE_HEADS_UP && !mDisableNotificationAlerts
                    && Settings.Global.HEADS_UP_OFF != Settings.Global.getInt(
                    mContext.getContentResolver(), Settings.Global.HEADS_UP_NOTIFICATIONS_ENABLED,
                    Settings.Global.HEADS_UP_OFF);
            mHeadsUpTicker = mUseHeadsUp && 0 != Settings.Global.getInt(
                    mContext.getContentResolver(), SETTING_HEADS_UP_TICKER, 0);
            mTickerEnabled = !mUseHeadsUp;
            Log.d(TAG, "heads up is " + (mUseHeadsUp ? "enabled" : "disabled"));
            if (wasUsing != mUseHeadsUp) {
                if (!mUseHeadsUp) {
                    Log.d(TAG, "dismissing any existing heads up notification on disable event");
                    setHeadsUpVisibility(false);
                    mHeadsUpNotificationView.release();
                    removeHeadsUpView();
                } else {
                    addHeadsUpView();
                }
            }
            initTickerView();
        }
    };

    private int mInteractingWindows;
    private boolean mAutohideSuspended;
    private int mStatusBarMode;
    private int mNavigationBarMode;

    private ViewMediatorCallback mKeyguardViewMediatorCallback;
    private ScrimController mScrimController;
    private DozeScrimController mDozeScrimController;

    private final Runnable mAutohide = new Runnable() {
        @Override
        public void run() {
            int requested = mSystemUiVisibility & ~STATUS_OR_NAV_TRANSIENT;
            if (mSystemUiVisibility != requested) {
                notifyUiVisibilityChanged(requested);
            }
        }};

    private boolean mWaitingForKeyguardExit;
    private boolean mDozing;
    private boolean mScrimSrcModeEnabled;

    private Interpolator mLinearOutSlowIn;
    private Interpolator mLinearInterpolator = new LinearInterpolator();
    private Interpolator mBackdropInterpolator = new AccelerateDecelerateInterpolator();
    public static final Interpolator ALPHA_IN = new PathInterpolator(0.4f, 0f, 1f, 1f);
    public static final Interpolator ALPHA_OUT = new PathInterpolator(0f, 0f, 0.8f, 1f);

    private BackDropView mBackdrop;
    private ImageView mBackdropFront, mBackdropBack;
    private PorterDuffXfermode mSrcXferMode = new PorterDuffXfermode(PorterDuff.Mode.SRC);
    private PorterDuffXfermode mSrcOverXferMode = new PorterDuffXfermode(PorterDuff.Mode.SRC_OVER);
    private boolean mVisualizerEnabled;

    private MediaSessionManager mMediaSessionManager;
    private MediaController mMediaController;
    private String mMediaNotificationKey;
    private MediaMetadata mMediaMetadata;
    private MediaController.Callback mMediaListener
            = new MediaController.Callback() {
        @Override
        public void onPlaybackStateChanged(PlaybackState state) {
            if (mVisualizerEnabled && state != null) {
                mBackdrop.setPlaying(state.getState() == PlaybackState.STATE_PLAYING);
            }
            super.onPlaybackStateChanged(state);
            if (DEBUG_MEDIA) Log.v(TAG, "DEBUG_MEDIA: onPlaybackStateChanged: " + state);
        }

        @Override
        public void onMetadataChanged(MediaMetadata metadata) {
            super.onMetadataChanged(metadata);
            if (DEBUG_MEDIA) Log.v(TAG, "DEBUG_MEDIA: onMetadataChanged: " + metadata);
            mMediaMetadata = metadata;
            updateMediaMetaData(true);
        }
    };

    private final OnChildLocationsChangedListener mOnChildLocationsChangedListener =
            new OnChildLocationsChangedListener() {
        @Override
        public void onChildLocationsChanged(NotificationStackScrollLayout stackScrollLayout) {
            userActivity();
        }
    };

    private int mDisabledUnmodified;

    /** Keys of notifications currently visible to the user. */
    private final ArraySet<String> mCurrentlyVisibleNotifications = new ArraySet<String>();
    private long mLastVisibilityReportUptimeMs;

    private final ShadeUpdates mShadeUpdates = new ShadeUpdates();

    private int mDrawCount;
    private Runnable mLaunchTransitionEndRunnable;
    private boolean mLaunchTransitionFadingAway;
    private ExpandableNotificationRow mDraggedDownRow;

    // Fingerprint (as computed by getLoggingFingerprint() of the last logged state.
    private int mLastLoggedStateFingerprint;

    private static final int VISIBLE_LOCATIONS = ViewState.LOCATION_FIRST_CARD
            | ViewState.LOCATION_TOP_STACK_PEEKING
            | ViewState.LOCATION_MAIN_AREA
            | ViewState.LOCATION_BOTTOM_STACK_PEEKING;

    private final OnChildLocationsChangedListener mNotificationLocationsChangedListener =
            new OnChildLocationsChangedListener() {
                @Override
                public void onChildLocationsChanged(
                        NotificationStackScrollLayout stackScrollLayout) {
                    if (mHandler.hasCallbacks(mVisibilityReporter)) {
                        // Visibilities will be reported when the existing
                        // callback is executed.
                        return;
                    }
                    // Calculate when we're allowed to run the visibility
                    // reporter. Note that this timestamp might already have
                    // passed. That's OK, the callback will just be executed
                    // ASAP.
                    long nextReportUptimeMs =
                            mLastVisibilityReportUptimeMs + VISIBILITY_REPORT_MIN_DELAY_MS;
                    mHandler.postAtTime(mVisibilityReporter, nextReportUptimeMs);
                }
            };

    // Tracks notifications currently visible in mNotificationStackScroller and
    // emits visibility events via NoMan on changes.
    private final Runnable mVisibilityReporter = new Runnable() {
        private final ArrayList<String> mTmpNewlyVisibleNotifications = new ArrayList<String>();
        private final ArrayList<String> mTmpCurrentlyVisibleNotifications = new ArrayList<String>();

        @Override
        public void run() {
            mLastVisibilityReportUptimeMs = SystemClock.uptimeMillis();

            // 1. Loop over mNotificationData entries:
            //   A. Keep list of visible notifications.
            //   B. Keep list of previously hidden, now visible notifications.
            // 2. Compute no-longer visible notifications by removing currently
            //    visible notifications from the set of previously visible
            //    notifications.
            // 3. Report newly visible and no-longer visible notifications.
            // 4. Keep currently visible notifications for next report.
            ArrayList<Entry> activeNotifications = mNotificationData.getActiveNotifications();
            int N = activeNotifications.size();
            for (int i = 0; i < N; i++) {
                Entry entry = activeNotifications.get(i);
                String key = entry.notification.getKey();
                boolean previouslyVisible = mCurrentlyVisibleNotifications.contains(key);
                boolean currentlyVisible =
                        (mStackScroller.getChildLocation(entry.row) & VISIBLE_LOCATIONS) != 0;
                if (currentlyVisible) {
                    // Build new set of visible notifications.
                    mTmpCurrentlyVisibleNotifications.add(key);
                }
                if (!previouslyVisible && currentlyVisible) {
                    mTmpNewlyVisibleNotifications.add(key);
                }
            }
            ArraySet<String> noLongerVisibleNotifications = mCurrentlyVisibleNotifications;
            noLongerVisibleNotifications.removeAll(mTmpCurrentlyVisibleNotifications);

            logNotificationVisibilityChanges(
                    mTmpNewlyVisibleNotifications, noLongerVisibleNotifications);

            mCurrentlyVisibleNotifications.clear();
            mCurrentlyVisibleNotifications.addAll(mTmpCurrentlyVisibleNotifications);

            mTmpNewlyVisibleNotifications.clear();
            mTmpCurrentlyVisibleNotifications.clear();
        }
    };

    private final View.OnClickListener mOverflowClickListener = new View.OnClickListener() {
        @Override
        public void onClick(View v) {
            goToLockedShade(null);
        }
    };

    @Override
    public void start() {
        mDisplay = ((WindowManager)mContext.getSystemService(Context.WINDOW_SERVICE))
                .getDefaultDisplay();
        updateDisplaySize();
        mScrimSrcModeEnabled = mContext.getResources().getBoolean(
                R.bool.config_status_bar_scrim_behind_use_src);

        ThemeConfig currentTheme = mContext.getResources().getConfiguration().themeConfig;
        if (currentTheme != null) {
            mCurrentTheme = (ThemeConfig)currentTheme.clone();
        } else {
            mCurrentTheme = ThemeConfig.getSystemTheme();
        }

        mStatusBarWindow = new StatusBarWindowView(mContext, null);
        mStatusBarWindow.mService = this;

        super.start(); // calls createAndAddWindows()

        mMediaSessionManager
                = (MediaSessionManager) mContext.getSystemService(Context.MEDIA_SESSION_SERVICE);
        // TODO: use MediaSessionManager.SessionListener to hook us up to future updates
        // in session state

        addNavigationBar(false);

        SettingsObserver observer = new SettingsObserver(mHandler);
        observer.observe();

        // Developer options - Force Navigation bar
        try {
            boolean needsNav = mWindowManagerService.needsNavigationBar();
            if (!needsNav) {
                mDevForceNavbarObserver = new DevForceNavbarObserver(mHandler);
                mDevForceNavbarObserver.observe();
            }
        } catch (RemoteException ex) {
            // no window manager? good luck with that
        }

        // Lastly, call to the icon policy to install/update all the icons.
        mIconPolicy = new PhoneStatusBarPolicy(mContext, mCastController, mHotspotController, mSuController);
        mSettingsObserver.onChange(false); // set up

        mHeadsUpObserver.onChange(true); // set up
        if (ENABLE_HEADS_UP) {
            mContext.getContentResolver().registerContentObserver(
                    Settings.Global.getUriFor(Settings.Global.HEADS_UP_NOTIFICATIONS_ENABLED), true,
                    mHeadsUpObserver);
            mContext.getContentResolver().registerContentObserver(
                    Settings.Global.getUriFor(SETTING_HEADS_UP_TICKER), true,
                    mHeadsUpObserver);
        }

        WallpaperManager wm = (WallpaperManager) mContext.getSystemService(
                Context.WALLPAPER_SERVICE);
        mKeyguardWallpaper = wm.getKeyguardBitmap();

        mUnlockMethodCache = UnlockMethodCache.getInstance(mContext);
        mUnlockMethodCache.addListener(this);
        startKeyguard();

        mDozeServiceHost = new DozeServiceHost();
        putComponent(DozeHost.class, mDozeServiceHost);
        putComponent(PhoneStatusBar.class, this);

        setControllerUsers();

        notifyUserAboutHiddenNotifications();

        mScreenPinningRequest = new ScreenPinningRequest(mContext);

        updateCustomRecentsLongPressHandler(true);
    }

    // ================================================================================
    // Constructing the view
    // ================================================================================
    protected PhoneStatusBarView makeStatusBarView() {
        final Context context = mContext;

        Resources res = context.getResources();

        mScreenWidth = (float) context.getResources().getDisplayMetrics().widthPixels;
        mMinBrightness = context.getResources().getInteger(
                com.android.internal.R.integer.config_screenBrightnessDim);

        updateDisplaySize(); // populates mDisplayMetrics
        updateResources(null);

        mIconSize = res.getDimensionPixelSize(com.android.internal.R.dimen.status_bar_icon_size);

        mStatusBarWindowContent = (FrameLayout) View.inflate(context,
                R.layout.super_status_bar, null);
        mStatusBarWindowContent.setOnTouchListener(new View.OnTouchListener() {
            @Override
            public boolean onTouch(View v, MotionEvent event) {
                checkUserAutohide(v, event);
                if (event.getAction() == MotionEvent.ACTION_DOWN) {
                    if (mExpandedVisible) {
                        animateCollapsePanels();
                    }
                }
                return mStatusBarWindowContent.onTouchEvent(event);
            }});

        mStatusBarView = (PhoneStatusBarView) mStatusBarWindowContent.findViewById(
                R.id.status_bar);
        mStatusBarView.setBar(this);

        PanelHolder holder = (PanelHolder) mStatusBarWindowContent.findViewById(R.id.panel_holder);
        mStatusBarView.setPanelHolder(holder);

        mNotificationPanel = (NotificationPanelView) mStatusBarWindowContent.findViewById(
                R.id.notification_panel);
        mNotificationPanel.setStatusBar(this);

        if (!ActivityManager.isHighEndGfx()) {
            mStatusBarWindowContent.setBackground(null);
            mNotificationPanel.setBackground(new FastColorDrawable(context.getResources().getColor(
                    R.color.notification_panel_solid_background)));
        }
        if (ENABLE_HEADS_UP) {
            mHeadsUpNotificationView =
                    (HeadsUpNotificationView) View.inflate(context, R.layout.heads_up, null);
            mHeadsUpNotificationView.setVisibility(View.GONE);
            mHeadsUpNotificationView.setBar(this);
        }
        if (MULTIUSER_DEBUG) {
            mNotificationPanelDebugText = (TextView) mNotificationPanel.findViewById(
                    R.id.header_debug_info);
            mNotificationPanelDebugText.setVisibility(View.VISIBLE);
        }

        updateShowSearchHoldoff();

        try {
            boolean showNav = mWindowManagerService.hasNavigationBar();
            if (DEBUG) Log.v(TAG, "hasNavigationBar=" + showNav);
            if (showNav && !mRecreating) {
                mNavigationBarView =
                    (NavigationBarView) View.inflate(context, R.layout.navigation_bar, null);
                mNavigationBarView.updateResources(getNavbarThemedResources());

                mNavigationBarView.setDisabledFlags(mDisabled);
                mNavigationBarView.setBar(this);
                mNavigationBarView.setOnVerticalChangedListener(
                        new NavigationBarView.OnVerticalChangedListener() {
                    @Override
                    public void onVerticalChanged(boolean isVertical) {
                        if (mSearchPanelView != null) {
                            mSearchPanelView.setHorizontal(isVertical);
                        }
                        mNotificationPanel.setQsScrimEnabled(!isVertical);
                    }
                });
                mNavigationBarView.setOnTouchListener(new View.OnTouchListener() {
                    @Override
                    public boolean onTouch(View v, MotionEvent event) {
                        checkUserAutohide(v, event);
                        return false;
                    }});
            }
        } catch (RemoteException ex) {
            // no window manager? good luck with that
        }

        // figure out which pixel-format to use for the status bar.
        mPixelFormat = PixelFormat.OPAQUE;

        mSystemIconArea = (LinearLayout) mStatusBarView.findViewById(R.id.system_icon_area);
        mSystemIcons = (LinearLayout) mStatusBarView.findViewById(R.id.system_icons);
        mStatusIcons = (LinearLayout)mStatusBarView.findViewById(R.id.statusIcons);
        mNotificationIconArea = mStatusBarView.findViewById(R.id.notification_icon_area_inner);
        mNotificationIcons = (IconMerger)mStatusBarView.findViewById(R.id.notificationIcons);
        mMoreIcon = mStatusBarView.findViewById(R.id.moreIcon);
        mNotificationIcons.setOverflowIndicator(mMoreIcon);
        mStatusBarContents = (LinearLayout)mStatusBarView.findViewById(R.id.status_bar_contents);

        mClockView = (TextView) mStatusBarView.findViewById(R.id.clock);
        mClockLocation = Settings.System.getIntForUser(mContext.getContentResolver(),
                Settings.System.STATUS_BAR_CLOCK, Clock.STYLE_CLOCK_RIGHT, UserHandle.USER_CURRENT);
        if (mClockController == null) mClockController = new Clock(mContext, mClockView);
        updateClockView();

        mStackScroller = (NotificationStackScrollLayout) mStatusBarWindowContent.findViewById(
                R.id.notification_stack_scroller);
        mStackScroller.setLongPressListener(getNotificationLongClicker());
        mStackScroller.setPhoneStatusBar(this);

        mKeyguardIconOverflowContainer =
                (NotificationOverflowContainer) LayoutInflater.from(mContext).inflate(
                        R.layout.status_bar_notification_keyguard_overflow, mStackScroller, false);
        mKeyguardIconOverflowContainer.setOnActivatedListener(this);
        mKeyguardIconOverflowContainer.setOnClickListener(mOverflowClickListener);
        mStackScroller.addView(mKeyguardIconOverflowContainer);

        SpeedBumpView speedBump = (SpeedBumpView) LayoutInflater.from(mContext).inflate(
                        R.layout.status_bar_notification_speed_bump, mStackScroller, false);
        mStackScroller.setSpeedBumpView(speedBump);
        mEmptyShadeView = (EmptyShadeView) LayoutInflater.from(mContext).inflate(
                R.layout.status_bar_no_notifications, mStackScroller, false);
        mStackScroller.setEmptyShadeView(mEmptyShadeView);
        mDismissView = (DismissView) LayoutInflater.from(mContext).inflate(
                R.layout.status_bar_notification_dismiss_all, mStackScroller, false);
        mDismissView.setOnButtonClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                clearAllNotifications();
            }
        });
        mStackScroller.setDismissView(mDismissView);
        mExpandedContents = mStackScroller;

        mBackdrop = (BackDropView) mStatusBarWindowContent.findViewById(R.id.backdrop);
        mBackdropFront = (ImageView) mBackdrop.findViewById(R.id.backdrop_front);
        mBackdropBack = (ImageView) mBackdrop.findViewById(R.id.backdrop_back);

        ScrimView scrimBehind = (ScrimView) mStatusBarWindowContent.findViewById(R.id.scrim_behind);
        ScrimView scrimInFront =
                (ScrimView) mStatusBarWindowContent.findViewById(R.id.scrim_in_front);
        mScrimController = new ScrimController(scrimBehind, scrimInFront, mScrimSrcModeEnabled);
        mScrimController.setBackDropView(mBackdrop);
        mStatusBarView.setScrimController(mScrimController);
        mDozeScrimController = new DozeScrimController(mScrimController, context);

        mHeader = (StatusBarHeaderView) mStatusBarWindowContent.findViewById(R.id.header);
        mHeader.setActivityStarter(this);
        mKeyguardStatusBar =
                (KeyguardStatusBarView) mStatusBarWindowContent.findViewById(R.id.keyguard_header);
        mStatusIconsKeyguard = (LinearLayout) mKeyguardStatusBar.findViewById(R.id.statusIcons);
        mKeyguardStatusView = mStatusBarWindowContent.findViewById(R.id.keyguard_status_view);
        mKeyguardBottomArea = (KeyguardBottomAreaView) mStatusBarWindowContent.findViewById(
                R.id.keyguard_bottom_area);
        mKeyguardBottomArea.setActivityStarter(this);
        mKeyguardIndicationController = new KeyguardIndicationController(mContext,
                (KeyguardIndicationTextView) mStatusBarWindowContent.findViewById(
                        R.id.keyguard_indication_text));
        mKeyguardBottomArea.setKeyguardIndicationController(mKeyguardIndicationController);

        initTickerView();

        mEdgeBorder = res.getDimensionPixelSize(R.dimen.status_bar_edge_ignore);

        // set the inital view visibility
        setAreThereNotifications();

        // Background thread for any controllers that need it.
        mHandlerThread = new HandlerThread(TAG, Process.THREAD_PRIORITY_BACKGROUND);
        mHandlerThread.start();

        // Other icons
        if (mLocationController == null) {
            mLocationController = new LocationControllerImpl(mContext); // will post a notification
        }
        if (mBatteryController == null) {
            mBatteryController = new BatteryController(mContext, mHandler);
            mBatteryController.addStateChangedCallback(new BatteryStateChangeCallback() {
                @Override
                public void onPowerSaveChanged() {
                    boolean isPowerSave = mBatteryController.isPowerSave();
                    if (mVisualizerEnabled) {
                        mBackdrop.setPowerSaveMode(isPowerSave);
                    }
                    mHandler.post(mCheckBarModes);
                    if (mDozeServiceHost != null) {
                        mDozeServiceHost.firePowerSaveChanged(isPowerSave);
                    }
                }

                @Override
                public void onBatteryLevelChanged(int level, boolean pluggedIn, boolean charging) {
                    // noop
                }

                @Override
                public void onBatteryStyleChanged(int style, int percentMode) {
                    // noop
                }
            });
        }
        if (mHotspotController == null) {
            mHotspotController = new HotspotControllerImpl(mContext);
        }
        if (mBluetoothController == null) {
            mBluetoothController = new BluetoothControllerImpl(mContext, mHandlerThread.getLooper());
        }
        if (mSecurityController == null) {
            mSecurityController = new SecurityControllerImpl(mContext);
        }
        if (mContext.getResources().getBoolean(R.bool.config_showRotationLock)
                && mRotationLockController == null) {
            mRotationLockController = new RotationLockControllerImpl(mContext);
        }
        if (mUserInfoController == null) {
            mUserInfoController = new UserInfoController(mContext);
        }
        if (mVolumeComponent == null) {
            mVolumeComponent = getComponent(VolumeComponent.class);
        }
        if (mZenModeController == null) {
            mZenModeController = mVolumeComponent.getZenController();
        }
        if (mCastController == null) {
            mCastController = new CastControllerImpl(mContext);
        }
        if (mSuController == null) {
            mSuController = new SuControllerImpl(mContext);
        }
        if (mNetworkController == null) {
            mNetworkController = new NetworkControllerImpl(mContext);
        }

        final SignalClusterView signalCluster =
            (SignalClusterView) mStatusBarView.findViewById(R.id.signal_cluster);
        final SignalClusterView signalClusterKeyguard =
            (SignalClusterView) mKeyguardStatusBar.findViewById(R.id.signal_cluster);
        final SignalClusterView signalClusterQs =
            (SignalClusterView) mHeader.findViewById(R.id.signal_cluster);
        mNetworkController.addSignalCluster(signalCluster);
        mNetworkController.addSignalCluster(signalClusterKeyguard);
        mNetworkController.addSignalCluster(signalClusterQs);
        signalCluster.setSecurityController(mSecurityController);
        signalCluster.setNetworkController(mNetworkController);
        signalClusterKeyguard.setSecurityController(mSecurityController);
        signalClusterKeyguard.setNetworkController(mNetworkController);
        signalClusterQs.setSecurityController(mSecurityController);
        signalClusterQs.setNetworkController(mNetworkController);
        final boolean isAPhone = mNetworkController.hasVoiceCallingFeature();
        if (isAPhone) {
            mNetworkController.addEmergencyListener(new NetworkControllerImpl.EmergencyListener() {
                @Override
                public void setEmergencyCallsOnly(boolean emergencyOnly) {
                    mHeader.setShowEmergencyCallsOnly(emergencyOnly);
                }
            });
        }

        mCarrierLabel = (TextView)mStatusBarWindowContent.findViewById(R.id.carrier_label);
        mShowCarrierInPanel = (mCarrierLabel != null);
        if (DEBUG) Log.v(TAG, "carrierlabel=" + mCarrierLabel + " show=" + mShowCarrierInPanel);
        if (mShowCarrierInPanel) {
            mCarrierLabel.setVisibility(mCarrierLabelVisible ? View.VISIBLE : View.INVISIBLE);

            mNetworkController.addCarrierLabel(new NetworkControllerImpl.CarrierLabelListener() {
                @Override
                public void setCarrierLabel(String label) {
                    mCarrierLabel.setText(label);
                    if (mNetworkController.hasMobileDataFeature()) {
                        if (TextUtils.isEmpty(label)) {
                            mCarrierLabel.setVisibility(View.GONE);
                        } else {
                            mCarrierLabel.setVisibility(View.VISIBLE);
                        }
                    }
                }
            });
        }

        mKeyguardBottomArea.setPhoneStatusBar(this);
        if (mAccessibilityController == null) {
            mAccessibilityController = new AccessibilityController(mContext);
        }
        mKeyguardBottomArea.setAccessibilityController(mAccessibilityController);
        if (mNextAlarmController == null) {
            mNextAlarmController = new NextAlarmController(mContext);
        }
        if (mKeyguardMonitor == null) {
            mKeyguardMonitor = new KeyguardMonitor();
        }
        if (mUserSwitcherController == null) {
            mUserSwitcherController = new UserSwitcherController(mContext, mKeyguardMonitor);
        }
        if (mWeatherController == null) {
            mWeatherController = new WeatherControllerImpl(mContext);
        }

        mKeyguardUserSwitcher = new KeyguardUserSwitcher(mContext,
                (ViewStub) mStatusBarWindowContent.findViewById(R.id.keyguard_user_switcher),
                mKeyguardStatusBar, mNotificationPanel, mUserSwitcherController);


        // Set up the quick settings tile panel
        mQSPanel = (QSPanel) mStatusBarWindowContent.findViewById(R.id.quick_settings_panel);
        if (mQSPanel != null) {
            final QSTileHost qsh = new QSTileHost(mContext, this,
                    mBluetoothController, mLocationController, mRotationLockController,
                    mNetworkController, mZenModeController, mVolumeComponent,
                    mHotspotController, mCastController, mUserSwitcherController,
                    mKeyguardMonitor, mSecurityController);
            mQSPanel.setHost(qsh);
            mQSPanel.setTiles(qsh.getTiles());
            mBrightnessMirrorController = new BrightnessMirrorController(mStatusBarWindowContent);
            mQSPanel.setBrightnessMirror(mBrightnessMirrorController);
            mHeader.setQSPanel(mQSPanel);
            qsh.setCallback(new QSTileHost.Callback() {
                @Override
                public void onTilesChanged() {
                    mQSPanel.setTiles(qsh.getTiles());
                }
            });
        }

        // Set up the initial custom tile listener state.
        try {
            mCustomTileListenerService.registerAsSystemService(mContext,
                    new ComponentName(mContext.getPackageName(), getClass().getCanonicalName()),
                    UserHandle.USER_ALL);
        } catch (RemoteException e) {
            Log.e(TAG, "Unable to register custom tile listener", e);
        }

        mQSPanel.getHost().setCustomTileListenerService(mCustomTileListenerService);

        // User info. Trigger first load.
        mHeader.setUserInfoController(mUserInfoController);
        mKeyguardStatusBar.setUserInfoController(mUserInfoController);
        mUserInfoController.reloadUserInfo();

        mHeader.setBatteryController(mBatteryController);
        ((BatteryMeterView) mStatusBarView.findViewById(R.id.battery)).setBatteryController(
                mBatteryController);
        ((BatteryLevelTextView) mStatusBarView.findViewById(R.id.battery_level_text))
                .setBatteryController(mBatteryController);
        mKeyguardStatusBar.setBatteryController(mBatteryController);
        mHeader.setNextAlarmController(mNextAlarmController);
        mHeader.setWeatherController(mWeatherController);

        PowerManager pm = (PowerManager) mContext.getSystemService(Context.POWER_SERVICE);
        mBroadcastReceiver.onReceive(mContext,
                new Intent(pm.isScreenOn() ? Intent.ACTION_SCREEN_ON : Intent.ACTION_SCREEN_OFF));

        startGlyphRasterizeHack();
        return mStatusBarView;
    }

    private void clearAllNotifications() {

        // animate-swipe all dismissable notifications, then animate the shade closed
        int numChildren = mStackScroller.getChildCount();

        final ArrayList<View> viewsToHide = new ArrayList<View>(numChildren);
        for (int i = 0; i < numChildren; i++) {
            final View child = mStackScroller.getChildAt(i);
            if (mStackScroller.canChildBeDismissed(child)) {
                if (child.getVisibility() == View.VISIBLE) {
                    viewsToHide.add(child);
                }
            }
        }
        if (viewsToHide.isEmpty()) {
            animateCollapsePanels(CommandQueue.FLAG_EXCLUDE_NONE);
            return;
        }

        addPostCollapseAction(new Runnable() {
            @Override
            public void run() {
                try {
                    mBarService.onClearAllNotifications(mCurrentUserId);
                } catch (Exception ex) { }
            }
        });

        performDismissAllAnimations(viewsToHide);

    }

    private void performDismissAllAnimations(ArrayList<View> hideAnimatedList) {
        Runnable animationFinishAction = new Runnable() {
            @Override
            public void run() {
                mStackScroller.post(new Runnable() {
                    @Override
                    public void run() {
                        mStackScroller.setDismissAllInProgress(false);
                    }
                });
                animateCollapsePanels(CommandQueue.FLAG_EXCLUDE_NONE);
            }
        };

        // let's disable our normal animations
        mStackScroller.setDismissAllInProgress(true);

        // Decrease the delay for every row we animate to give the sense of
        // accelerating the swipes
        int rowDelayDecrement = 10;
        int currentDelay = 140;
        int totalDelay = 180;
        int numItems = hideAnimatedList.size();
        for (int i = numItems - 1; i >= 0; i--) {
            View view = hideAnimatedList.get(i);
            Runnable endRunnable = null;
            if (i == 0) {
                endRunnable = animationFinishAction;
            }
            mStackScroller.dismissViewAnimated(view, endRunnable, totalDelay, 260);
            currentDelay = Math.max(50, currentDelay - rowDelayDecrement);
            totalDelay += currentDelay;
        }
    }

    /**
     * Hack to improve glyph rasterization for scaled text views.
     */
    private void startGlyphRasterizeHack() {
        mStatusBarView.getViewTreeObserver().addOnPreDrawListener(
                new ViewTreeObserver.OnPreDrawListener() {
            @Override
            public boolean onPreDraw() {
                if (mDrawCount == 1) {
                    mStatusBarView.getViewTreeObserver().removeOnPreDrawListener(this);
                    HardwareCanvas.setProperty("extraRasterBucket",
                            Float.toString(StackScrollAlgorithm.DIMMED_SCALE));
                    HardwareCanvas.setProperty("extraRasterBucket", Float.toString(
                            mContext.getResources().getDimensionPixelSize(
                                    R.dimen.qs_time_collapsed_size)
                            / mContext.getResources().getDimensionPixelSize(
                                    R.dimen.qs_time_expanded_size)));
                }
                mDrawCount++;
                return true;
            }
        });
    }

    @Override
    protected void setZenMode(int mode) {
        super.setZenMode(mode);
        if (mIconPolicy != null) {
            mIconPolicy.setZenMode(mode);
        }
    }

    private void startKeyguard() {
        KeyguardViewMediator keyguardViewMediator = getComponent(KeyguardViewMediator.class);
        mStatusBarKeyguardViewManager = keyguardViewMediator.registerStatusBar(this,
                mStatusBarWindow, mStatusBarWindowManager, mScrimController);
        mKeyguardViewMediatorCallback = keyguardViewMediator.getViewMediatorCallback();
    }

    @Override
    protected View getStatusBarView() {
        return mStatusBarView;
    }

    public StatusBarWindowView getStatusBarWindow() {
        return mStatusBarWindow;
    }

    private void initTickerView() {
        if (mTickerEnabled && (mTicker == null || mTickerView == null)) {
            final ViewStub tickerStub = (ViewStub) mStatusBarView.findViewById(R.id.ticker_stub);
            if (tickerStub != null) {
                mTickerView = tickerStub.inflate();
                mTicker = new MyTicker(mContext, mStatusBarView);

                TickerView tickerView = (TickerView) mStatusBarView.findViewById(R.id.tickerText);
                tickerView.mTicker = mTicker;
            } else {
                mTickerEnabled = false;
            }
        }
    }

    @Override
    protected WindowManager.LayoutParams getSearchLayoutParams(LayoutParams layoutParams) {
        boolean opaque = false;
        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                LayoutParams.MATCH_PARENT,
                LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.TYPE_NAVIGATION_BAR_PANEL,
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
                | WindowManager.LayoutParams.FLAG_ALT_FOCUSABLE_IM
                | WindowManager.LayoutParams.FLAG_SPLIT_TOUCH,
                (opaque ? PixelFormat.OPAQUE : PixelFormat.TRANSLUCENT));
        if (ActivityManager.isHighEndGfx()) {
            lp.flags |= WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED;
        }
        lp.gravity = Gravity.BOTTOM | Gravity.START;
        lp.setTitle("SearchPanel");
        lp.softInputMode = WindowManager.LayoutParams.SOFT_INPUT_STATE_UNCHANGED
        | WindowManager.LayoutParams.SOFT_INPUT_ADJUST_NOTHING;
        return lp;
    }

    @Override
    protected void updateSearchPanel() {
        super.updateSearchPanel();
        if (mNavigationBarView != null) {
            mNavigationBarView.setDelegateView(mSearchPanelView);
        }
    }

    @Override
    public void showSearchPanel() {
        super.showSearchPanel();
        mHandler.removeCallbacks(mShowSearchPanel);

        // we want to freeze the sysui state wherever it is
        mSearchPanelView.setSystemUiVisibility(mSystemUiVisibility);

        if (mNavigationBarView != null) {
            WindowManager.LayoutParams lp =
                (android.view.WindowManager.LayoutParams) mNavigationBarView.getLayoutParams();
            lp.flags &= ~WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL;
            mWindowManager.updateViewLayout(mNavigationBarView, lp);
        }
    }

    @Override
    public void hideSearchPanel() {
        super.hideSearchPanel();
        if (mNavigationBarView != null) {
            WindowManager.LayoutParams lp =
                (android.view.WindowManager.LayoutParams) mNavigationBarView.getLayoutParams();
            lp.flags |= WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL;
            mWindowManager.updateViewLayout(mNavigationBarView, lp);
        }
    }

    public int getStatusBarHeight() {
        if (mNaturalBarHeight < 0) {
            final Resources res = mContext.getResources();
            mNaturalBarHeight =
                    res.getDimensionPixelSize(com.android.internal.R.dimen.status_bar_height);
        }
        return mNaturalBarHeight;
    }

    private final CustomTileListenerService mCustomTileListenerService =
            new CustomTileListenerService() {
                @Override
                public void onListenerConnected() {
                    //Connected
                }
                @Override
                public void onCustomTilePosted(final StatusBarPanelCustomTile sbc) {
                    if (DEBUG) Log.d(TAG, "onCustomTilePosted: " + sbc.getCustomTile());
                    mHandler.post(new Runnable() {
                        @Override
                        public void run() {
                            boolean isUpdate = mQSPanel.getHost().getCustomTileData()
                                    .get(sbc.getKey()) != null;
                            if (isUpdate) {
                                mQSPanel.getHost().updateCustomTile(sbc);
                            } else {
                                mQSPanel.getHost().addCustomTile(sbc);
                            }
                        }
                    });
                }

                @Override
                public void onCustomTileRemoved(final StatusBarPanelCustomTile sbc) {
                    if (DEBUG) Log.d(TAG, "onCustomTileRemoved: " + sbc.getCustomTile());
                    mHandler.post(new Runnable() {
                        @Override
                        public void run() {
                            mQSPanel.getHost().removeCustomTileSysUi(sbc.getKey());
                        }
                    });
                }
            };

    private View.OnClickListener mRecentsClickListener = new View.OnClickListener() {
        public void onClick(View v) {
            awakenDreams();
            toggleRecentApps();
        }
    };

    private long mLastLockToAppLongPress;
    private View.OnLongClickListener mLongPressBackRecentsListener =
            new View.OnLongClickListener() {
        @Override
        public boolean onLongClick(View v) {
            handleLongPressBackRecents(v);
            return true;
        }
    };

    private int mShowSearchHoldoff = 0;
    private Runnable mShowSearchPanel = new Runnable() {
        public void run() {
            showSearchPanel();
            awakenDreams();
        }
    };

    View.OnTouchListener mHomeActionListener = new View.OnTouchListener() {
        public boolean onTouch(View v, MotionEvent event) {
            switch(event.getAction()) {
                case MotionEvent.ACTION_DOWN:
                if (!shouldDisableNavbarGestures()) {
                    mHandler.removeCallbacks(mShowSearchPanel);
                    mHandler.postDelayed(mShowSearchPanel, mShowSearchHoldoff);
                }
            break;

            case MotionEvent.ACTION_UP:
            case MotionEvent.ACTION_CANCEL:
                mHandler.removeCallbacks(mShowSearchPanel);
                awakenDreams();
            break;
        }
        return false;
        }
    };

    private void awakenDreams() {
        if (mDreamManager != null) {
            try {
                mDreamManager.awaken();
            } catch (RemoteException e) {
                // fine, stay asleep then
            }
        }
    }

    private void prepareNavigationBarView(boolean forceReset) {
        mNavigationBarView.reorient();
        mNavigationBarView.setListeners(mRecentsClickListener, mRecentsPreloadOnTouchListener,
                mLongPressBackRecentsListener, mHomeActionListener);

        if (forceReset) {
            // Nav Bar was added dynamically - we need to reset the mSystemUiVisibility and call
            // setSystemUiVisibility so that mNavigationBarMode is set to the correct value
            int newVal = mSystemUiVisibility;
            mSystemUiVisibility = 0;
            setSystemUiVisibility(newVal, SYSTEM_UI_VISIBILITY_MASK);
        }

        updateSearchPanel();
    }

    // For small-screen devices (read: phones) that lack hardware navigation buttons
    private void addNavigationBar(boolean forceReset) {
        if (DEBUG) Log.v(TAG, "addNavigationBar: about to add " + mNavigationBarView);
        if (mNavigationBarView == null) return;

        ThemeConfig newTheme = mContext.getResources().getConfiguration().themeConfig;
        if (newTheme != null &&
                (mCurrentTheme == null || !mCurrentTheme.equals(newTheme))) {
            // Nevermind, this will be re-created
            return;
        }

        prepareNavigationBarView(forceReset);

        mWindowManager.addView(mNavigationBarView, getNavigationBarLayoutParams());
    }

    private void removeNavigationBar() {
        if (DEBUG) Log.d(TAG, "removeNavigationBar: about to remove " + mNavigationBarView);
        if (mNavigationBarView == null) return;

        mWindowManager.removeView(mNavigationBarView);
        mNavigationBarView = null;
    }

    private void repositionNavigationBar() {
        if (mNavigationBarView == null || !mNavigationBarView.isAttachedToWindow()) return;

        prepareNavigationBarView(false);

        mWindowManager.updateViewLayout(mNavigationBarView, getNavigationBarLayoutParams());
    }

    private void notifyNavigationBarScreenOn(boolean screenOn) {
        if (mNavigationBarView == null) return;
        mNavigationBarView.notifyScreenOn(screenOn);
    }

    private WindowManager.LayoutParams getNavigationBarLayoutParams() {
        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.TYPE_NAVIGATION_BAR,
                    0
                    | WindowManager.LayoutParams.FLAG_TOUCHABLE_WHEN_WAKING
                    | WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                    | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                    | WindowManager.LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH
                    | WindowManager.LayoutParams.FLAG_SPLIT_TOUCH,
                PixelFormat.TRANSLUCENT);
        // this will allow the navbar to run in an overlay on devices that support this
        if (ActivityManager.isHighEndGfx()) {
            lp.flags |= WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED;
        }

        lp.setTitle("NavigationBar");
        lp.windowAnimations = 0;
        return lp;
    }

    private Resources getNavbarThemedResources() {
        String pkgName = mCurrentTheme.getOverlayPkgNameForApp(ThemeConfig.SYSTEMUI_NAVBAR_PKG);
        Resources res = null;
        try {
            res = mContext.getPackageManager().getThemedResourcesForApplication(
                    mContext.getPackageName(), pkgName);
        } catch (PackageManager.NameNotFoundException e) {
            res = mContext.getResources();
        }
        return res;
    }

    private void addHeadsUpView() {
        int headsUpHeight = mContext.getResources()
                .getDimensionPixelSize(R.dimen.heads_up_window_height);
        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                LayoutParams.MATCH_PARENT, headsUpHeight,
                WindowManager.LayoutParams.TYPE_STATUS_BAR_PANEL, // above the status bar!
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
                    | WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS
                    | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                    | WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                    | WindowManager.LayoutParams.FLAG_ALT_FOCUSABLE_IM
                    | WindowManager.LayoutParams.FLAG_SPLIT_TOUCH,
                PixelFormat.TRANSLUCENT);
        lp.flags |= WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED;
        lp.gravity = Gravity.TOP;
        lp.setTitle("Heads Up");
        lp.packageName = mContext.getPackageName();
        lp.windowAnimations = R.style.Animation_StatusBar_HeadsUp;

        mWindowManager.addView(mHeadsUpNotificationView, lp);
    }

    private void removeHeadsUpView() {
        if (mHeadsUpNotificationView != null && mHeadsUpNotificationView.isAttachedToWindow()) {
            mWindowManager.removeView(mHeadsUpNotificationView);
        }
    }

    public void refreshAllStatusBarIcons() {
        refreshAllIconsForLayout(mStatusIcons);
        refreshAllIconsForLayout(mStatusIconsKeyguard);
        refreshAllIconsForLayout(mNotificationIcons);
    }

    private void refreshAllIconsForLayout(LinearLayout ll) {
        final int count = ll.getChildCount();
        for (int n = 0; n < count; n++) {
            View child = ll.getChildAt(n);
            if (child instanceof StatusBarIconView) {
                ((StatusBarIconView) child).updateDrawable();
            }
        }
    }

    public void addIcon(String slot, int index, int viewIndex, StatusBarIcon icon) {
        if (SPEW) Log.d(TAG, "addIcon slot=" + slot + " index=" + index + " viewIndex=" + viewIndex
                + " icon=" + icon);
        StatusBarIconView view = new StatusBarIconView(mContext, slot, null);
        view.set(icon);
        mStatusIcons.addView(view, viewIndex, new LinearLayout.LayoutParams(
                LayoutParams.WRAP_CONTENT, mIconSize));
        view = new StatusBarIconView(mContext, slot, null);
        view.set(icon);
        mStatusIconsKeyguard.addView(view, viewIndex, new LinearLayout.LayoutParams(
                LayoutParams.WRAP_CONTENT, mIconSize));
    }

    public void updateIcon(String slot, int index, int viewIndex,
            StatusBarIcon old, StatusBarIcon icon) {
        if (SPEW) Log.d(TAG, "updateIcon slot=" + slot + " index=" + index + " viewIndex=" + viewIndex
                + " old=" + old + " icon=" + icon);
        StatusBarIconView view = (StatusBarIconView) mStatusIcons.getChildAt(viewIndex);
        view.set(icon);
        view = (StatusBarIconView) mStatusIconsKeyguard.getChildAt(viewIndex);
        view.set(icon);
    }

    public void removeIcon(String slot, int index, int viewIndex) {
        if (SPEW) Log.d(TAG, "removeIcon slot=" + slot + " index=" + index + " viewIndex=" + viewIndex);
        mStatusIcons.removeViewAt(viewIndex);
        mStatusIconsKeyguard.removeViewAt(viewIndex);
    }

    public UserHandle getCurrentUserHandle() {
        return new UserHandle(mCurrentUserId);
    }

    @Override
    public void addNotification(StatusBarNotification notification, RankingMap ranking) {
        if (DEBUG) Log.d(TAG, "addNotification key=" + notification.getKey());
        if (mUseHeadsUp && shouldInterrupt(notification)) {
            if (DEBUG) Log.d(TAG, "launching notification in heads up mode");
            Entry interruptionCandidate = new Entry(notification, null);
            ViewGroup holder = mHeadsUpNotificationView.getHolder();
            if (inflateViewsForHeadsUp(interruptionCandidate, holder)) {
                // 1. Populate mHeadsUpNotificationView
                mHeadsUpNotificationView.showNotification(interruptionCandidate);

                // do not show the notification in the shade, yet.
                return;
            }
        }

        Entry shadeEntry = createNotificationViews(notification);
        if (shadeEntry == null) {
            return;
        }

        if (notification.getNotification().fullScreenIntent != null) {
            // Stop screensaver if the notification has a full-screen intent.
            // (like an incoming phone call)
            awakenDreams();

            // not immersive & a full-screen alert should be shown
            if (DEBUG) Log.d(TAG, "Notification has fullScreenIntent; sending fullScreenIntent");
            try {
                EventLog.writeEvent(EventLogTags.SYSUI_FULLSCREEN_NOTIFICATION,
                        notification.getKey());
                notification.getNotification().fullScreenIntent.send();
            } catch (PendingIntent.CanceledException e) {
            }
        } else if (!mRecreating) {
            // usual case: status bar visible & not immersive

            // show the ticker if there isn't already a heads up
            if (mHeadsUpNotificationView.getEntry() == null) {
                tick(notification, true);
            }
        }
        addNotificationViews(shadeEntry, ranking);
        // Recalculate the position of the sliding windows and the titles.
        setAreThereNotifications();
        updateExpandedViewPos(EXPANDED_LEAVE_ALONE);
    }

    public void displayNotificationFromHeadsUp(StatusBarNotification notification) {
        NotificationData.Entry shadeEntry = createNotificationViews(notification);
        if (shadeEntry == null) {
            return;
        }
        shadeEntry.setInterruption();

        addNotificationViews(shadeEntry, null);
        // Recalculate the position of the sliding windows and the titles.
        setAreThereNotifications();
        updateExpandedViewPos(EXPANDED_LEAVE_ALONE);
    }

    @Override
    public void resetHeadsUpDecayTimer() {
        mHandler.removeMessages(MSG_DECAY_HEADS_UP);
        if (mUseHeadsUp && mHeadsUpNotificationDecay > 0
                && mHeadsUpNotificationView.isClearable()) {
            mHandler.sendEmptyMessageDelayed(MSG_DECAY_HEADS_UP, mHeadsUpNotificationDecay);
        }
    }

    @Override
    public void scheduleHeadsUpOpen() {
        mHandler.removeMessages(MSG_SHOW_HEADS_UP);
        mHandler.sendEmptyMessage(MSG_SHOW_HEADS_UP);
    }

    @Override
    public void scheduleHeadsUpClose() {
        mHandler.removeMessages(MSG_HIDE_HEADS_UP);
        mHandler.sendEmptyMessage(MSG_HIDE_HEADS_UP);
    }

    @Override
    public void scheduleHeadsUpEscalation() {
        mHandler.removeMessages(MSG_ESCALATE_HEADS_UP);
        mHandler.sendEmptyMessage(MSG_ESCALATE_HEADS_UP);
    }

    @Override
    protected void updateNotificationRanking(RankingMap ranking) {
        mNotificationData.updateRanking(ranking);
        updateNotifications();
    }

    @Override
    public void removeNotification(String key, RankingMap ranking) {
        if (ENABLE_HEADS_UP && mHeadsUpNotificationView.getEntry() != null
                && key.equals(mHeadsUpNotificationView.getEntry().notification.getKey())) {
            mHeadsUpNotificationView.clear();
        }

        StatusBarNotification old = removeNotificationViews(key, ranking);
        if (SPEW) Log.d(TAG, "removeNotification key=" + key + " old=" + old);

        if (old != null) {
            // Cancel the ticker if it's still running
            if (mTickerEnabled && shouldInterrupt(old)) {
                mTicker.removeEntry(old);
            }

            // Recalculate the position of the sliding windows and the titles.
            updateExpandedViewPos(EXPANDED_LEAVE_ALONE);

            if (CLOSE_PANEL_WHEN_EMPTIED && !hasActiveNotifications()
                    && !mNotificationPanel.isTracking() && !mNotificationPanel.isQsExpanded()) {
                if (mState == StatusBarState.SHADE) {
                    animateCollapsePanels();
                } else if (mState == StatusBarState.SHADE_LOCKED) {
                    goToKeyguard();
                }
            }
        }
        setAreThereNotifications();
    }

    @Override
    protected void refreshLayout(int layoutDirection) {
        if (mNavigationBarView != null) {
            mNavigationBarView.setLayoutDirection(layoutDirection);
        }
        refreshAllStatusBarIcons();
    }

    private void updateShowSearchHoldoff() {
        mShowSearchHoldoff = mContext.getResources().getInteger(
            R.integer.config_show_search_delay);
    }

    private void updateNotificationShade() {
        if (mStackScroller == null) return;

        // Do not modify the notifications during collapse.
        if (isCollapsing()) {
            addPostCollapseAction(new Runnable() {
                @Override
                public void run() {
                    updateNotificationShade();
                }
            });
            return;
        }

        ArrayList<Entry> activeNotifications = mNotificationData.getActiveNotifications();
        ArrayList<ExpandableNotificationRow> toShow = new ArrayList<>(activeNotifications.size());
        final int N = activeNotifications.size();
        for (int i=0; i<N; i++) {
            Entry ent = activeNotifications.get(i);
            int vis = ent.notification.getNotification().visibility;

            // Display public version of the notification if we need to redact.
            final boolean hideSensitive =
                    !userAllowsPrivateNotificationsInPublic(ent.notification.getUserId());
            boolean sensitiveNote = vis == Notification.VISIBILITY_PRIVATE;
            boolean sensitivePackage = packageHasVisibilityOverride(ent.notification.getKey());
            boolean sensitive = (sensitiveNote && hideSensitive) || sensitivePackage;
            boolean showingPublic = sensitive && isLockscreenPublicMode();
            ent.row.setSensitive(sensitive);
            if (ent.autoRedacted && ent.legacy) {
                // TODO: Also fade this? Or, maybe easier (and better), provide a dark redacted form
                // for legacy auto redacted notifications.
                if (showingPublic) {
                    ent.row.setShowingLegacyBackground(false);
                } else {
                    ent.row.setShowingLegacyBackground(true);
                }
            }
            toShow.add(ent.row);
        }

        ArrayList<View> toRemove = new ArrayList<View>();
        for (int i=0; i< mStackScroller.getChildCount(); i++) {
            View child = mStackScroller.getChildAt(i);
            if (!toShow.contains(child) && child instanceof ExpandableNotificationRow) {
                toRemove.add(child);
            }
        }

        for (View remove : toRemove) {
            mStackScroller.removeView(remove);
        }
        for (int i=0; i<toShow.size(); i++) {
            View v = toShow.get(i);
            if (v.getParent() == null) {
                mStackScroller.addView(v);
            }
        }

        // So after all this work notifications still aren't sorted correctly.
        // Let's do that now by advancing through toShow and mStackScroller in
        // lock-step, making sure mStackScroller matches what we see in toShow.
        int j = 0;
        for (int i = 0; i < mStackScroller.getChildCount(); i++) {
            View child = mStackScroller.getChildAt(i);
            if (!(child instanceof ExpandableNotificationRow)) {
                // We don't care about non-notification views.
                continue;
            }

            if (child == toShow.get(j)) {
                // Everything is well, advance both lists.
                j++;
                continue;
            }

            // Oops, wrong notification at this position. Put the right one
            // here and advance both lists.
            mStackScroller.changeViewPosition(toShow.get(j), i);
            j++;
        }
        updateRowStates();
        updateSpeedbump();
        updateClearAll();
        updateEmptyShadeView();

        // Disable QS if device not provisioned.
        // If the user switcher is simple then disable QS during setup because
        // the user intends to use the lock screen user switcher, QS in not needed.
        mNotificationPanel.setQsExpansionEnabled(isDeviceProvisioned()
                && (mUserSetup || mUserSwitcherController == null
                        || !mUserSwitcherController.isSimpleUserSwitcher()));
        mShadeUpdates.check();
    }

    private boolean packageHasVisibilityOverride(String key) {
        return mNotificationData.getVisibilityOverride(key)
                != NotificationListenerService.Ranking.VISIBILITY_NO_OVERRIDE;
    }

    private void updateClearAll() {
        boolean showDismissView =
                mState != StatusBarState.KEYGUARD &&
                mNotificationData.hasActiveClearableNotifications();
        mStackScroller.updateDismissView(showDismissView);
    }

    private void updateEmptyShadeView() {
        boolean showEmptyShade =
                mState != StatusBarState.KEYGUARD &&
                        mNotificationData.getActiveNotifications().size() == 0;
        mNotificationPanel.setShadeEmpty(showEmptyShade);
    }

    private void updateSpeedbump() {
        int speedbumpIndex = -1;
        int currentIndex = 0;
        ArrayList<Entry> activeNotifications = mNotificationData.getActiveNotifications();
        final int N = activeNotifications.size();
        for (int i = 0; i < N; i++) {
            Entry entry = activeNotifications.get(i);
            if (entry.row.getVisibility() != View.GONE &&
                    mNotificationData.isAmbient(entry.key)) {
                speedbumpIndex = currentIndex;
                break;
            }
            currentIndex++;
        }
        mStackScroller.updateSpeedBumpIndex(speedbumpIndex);
    }

    private void handleUpdateNotifications() {
        // TODO: Move this into updateNotificationIcons()?
        if (mNotificationIcons == null) return;

        mNotificationData.filterAndSort();

        updateNotificationShade();
        updateNotificationIcons();
    }

    @Override
    protected void updateNotifications() {
        if (!mHandler.hasMessages(MSG_UPDATE_NOTIFICATIONS)) {
            mHandler.sendEmptyMessage(MSG_UPDATE_NOTIFICATIONS);
        }
    }

    private void updateNotificationIcons() {
        final LinearLayout.LayoutParams params
            = new LinearLayout.LayoutParams(mIconSize + 2*mIconHPadding, mNaturalBarHeight);

        ArrayList<Entry> activeNotifications = mNotificationData.getActiveNotifications();
        final int N = activeNotifications.size();
        ArrayList<StatusBarIconView> toShow = new ArrayList<>(N);

        // Filter out notifications with low scores.
        for (int i = 0; i < N; i++) {
            Entry ent = activeNotifications.get(i);
            if (ent.notification.getScore() < HIDE_ICONS_BELOW_SCORE &&
                    !NotificationData.showNotificationEvenIfUnprovisioned(ent.notification)) {
                continue;
            }
            toShow.add(ent.icon);
        }

        if (DEBUG) {
            Log.d(TAG, "refreshing icons: " + toShow.size() +
                    " notifications, mNotificationIcons=" + mNotificationIcons);
        }

        ArrayList<View> toRemove = new ArrayList<View>();
        for (int i=0; i<mNotificationIcons.getChildCount(); i++) {
            View child = mNotificationIcons.getChildAt(i);
            if (!toShow.contains(child)) {
                toRemove.add(child);
            }
        }

        final int toRemoveCount = toRemove.size();
        for (int i = 0; i < toRemoveCount; i++) {
            mNotificationIcons.removeView(toRemove.get(i));
        }

        for (int i=0; i<toShow.size(); i++) {
            View v = toShow.get(i);
            if (v.getParent() == null) {
                mNotificationIcons.addView(v, i, params);
            }
        }

        // Resort notification icons
        final int childCount = mNotificationIcons.getChildCount();
        for (int i = 0; i < childCount; i++) {
            View actual = mNotificationIcons.getChildAt(i);
            StatusBarIconView expected = toShow.get(i);
            if (actual == expected) {
                continue;
            }
            mNotificationIcons.removeView(expected);
            mNotificationIcons.addView(expected, i);
        }
    }

    @Override
    protected void updateRowStates() {
        super.updateRowStates();
        mNotificationPanel.notifyVisibleChildrenChanged();
    }

    protected void updateCarrierLabelVisibility(boolean force) {
        // TODO: Handle this for the notification stack scroller as well
        if (!mShowCarrierInPanel) return;
        // The idea here is to only show the carrier label when there is enough room to see it,
        // i.e. when there aren't enough notifications to fill the panel.
        if (SPEW) {
            Log.d(TAG, String.format("stackScrollerh=%d scrollh=%d carrierh=%d",
                    mStackScroller.getHeight(), mStackScroller.getHeight(),
                    mCarrierLabelHeight));
        }

        // Emergency calls only is shown in the expanded header now.
        final boolean emergencyCallsShownElsewhere = mContext.getResources().getBoolean(
                R.bool.config_showEmergencyCallLabelOnly);

        final boolean makeVisible =
                !(emergencyCallsShownElsewhere && mNetworkController.isEmergencyOnly())
                && mStackScroller.getHeight() < (mNotificationPanel.getHeight()
                        - mCarrierLabelHeight - mStatusBarHeaderHeight)
                && mStackScroller.getVisibility() == View.VISIBLE
                && mState != StatusBarState.KEYGUARD;

        if (force || mCarrierLabelVisible != makeVisible) {
            mCarrierLabelVisible = makeVisible;
            if (DEBUG) {
                Log.d(TAG, "making carrier label " + (makeVisible?"visible":"invisible"));
            }
            mCarrierLabel.animate().cancel();
            if (makeVisible) {
                mCarrierLabel.setVisibility(View.VISIBLE);
            }
            mCarrierLabel.animate()
                .alpha(makeVisible ? 1f : 0f)
                //.setStartDelay(makeVisible ? 500 : 0)
                //.setDuration(makeVisible ? 750 : 100)
                .setDuration(150)
                .setListener(makeVisible ? null : new AnimatorListenerAdapter() {
                    @Override
                    public void onAnimationEnd(Animator animation) {
                        if (!mCarrierLabelVisible) { // race
                            mCarrierLabel.setVisibility(View.INVISIBLE);
                            mCarrierLabel.setAlpha(0f);
                        }
                    }
                })
                .start();
        }
    }

    @Override
    protected void setAreThereNotifications() {

        if (SPEW) {
            final boolean clearable = hasActiveNotifications() &&
                    mNotificationData.hasActiveClearableNotifications();
            Log.d(TAG, "setAreThereNotifications: N=" +
                    mNotificationData.getActiveNotifications().size() + " any=" +
                    hasActiveNotifications() + " clearable=" + clearable);
        }

        final View nlo = mStatusBarView.findViewById(R.id.notification_lights_out);
        final boolean showDot = hasActiveNotifications() && !areLightsOn();
        if (showDot != (nlo.getAlpha() == 1.0f)) {
            if (showDot) {
                nlo.setAlpha(0f);
                nlo.setVisibility(View.VISIBLE);
            }
            nlo.animate()
                .alpha(showDot?1:0)
                .setDuration(showDot?750:250)
                .setInterpolator(new AccelerateInterpolator(2.0f))
                .setListener(showDot ? null : new AnimatorListenerAdapter() {
                    @Override
                    public void onAnimationEnd(Animator _a) {
                        nlo.setVisibility(View.GONE);
                    }
                })
                .start();
        }

        findAndUpdateMediaNotifications();

        updateCarrierLabelVisibility(false);
    }

    public void showClock(boolean show) {
        mClockView.setVisibility(show ? View.VISIBLE : View.GONE);
    }

    public void findAndUpdateMediaNotifications() {
        boolean metaDataChanged = false;

        synchronized (mNotificationData) {
            ArrayList<Entry> activeNotifications = mNotificationData.getActiveNotifications();
            final int N = activeNotifications.size();
            Entry mediaNotification = null;
            MediaController controller = null;
            for (int i = 0; i < N; i++) {
                final Entry entry = activeNotifications.get(i);
                if (isMediaNotification(entry)) {
                    final MediaSession.Token token = entry.notification.getNotification().extras
                            .getParcelable(Notification.EXTRA_MEDIA_SESSION);
                    if (token != null) {
                        controller = new MediaController(mContext, token);
                        if (controller != null) {
                            // we've got a live one, here
                            mediaNotification = entry;
                        }
                    }
                }
            }

            if (mediaNotification == null) {
                // Still nothing? OK, let's just look for live media sessions and see if they match
                // one of our notifications. This will catch apps that aren't (yet!) using media
                // notifications.

                if (mMediaSessionManager != null) {
                    final List<MediaController> sessions
                            = mMediaSessionManager.getActiveSessionsForUser(
                                    null,
                                    UserHandle.USER_ALL);

                    for (MediaController aController : sessions) {
                        if (aController == null) continue;
                        final PlaybackState state = aController.getPlaybackState();
                        if (state == null) continue;
                        switch (state.getState()) {
                            case PlaybackState.STATE_STOPPED:
                            case PlaybackState.STATE_ERROR:
                                continue;
                            default:
                                // now to see if we have one like this
                                final String pkg = aController.getPackageName();

                                for (int i = 0; i < N; i++) {
                                    final Entry entry = activeNotifications.get(i);
                                    if (entry.notification.getPackageName().equals(pkg)) {
                                        if (DEBUG_MEDIA) {
                                            Log.v(TAG, "DEBUG_MEDIA: found controller matching "
                                                + entry.notification.getKey());
                                        }
                                        controller = aController;
                                        mediaNotification = entry;
                                        break;
                                    }
                                }
                        }
                    }
                }
            }

            if (!sameSessions(mMediaController, controller)) {
                // We have a new media session

                if (mMediaController != null) {
                    // something old was playing
                    Log.v(TAG, "DEBUG_MEDIA: Disconnecting from old controller: "
                            + mMediaController);
                    mMediaController.unregisterCallback(mMediaListener);
                }
                mMediaController = controller;

                if (mMediaController != null) {
                    mMediaController.registerCallback(mMediaListener);
                    if (mVisualizerEnabled) {
                        mBackdrop.setPlaying(true);
                    }
                    mMediaMetadata = mMediaController.getMetadata();
                    if (DEBUG_MEDIA) {
                        Log.v(TAG, "DEBUG_MEDIA: insert listener, receive metadata: "
                                + mMediaMetadata);
                    }

                    final String notificationKey = mediaNotification == null
                            ? null
                            : mediaNotification.notification.getKey();

                    if (notificationKey == null || !notificationKey.equals(mMediaNotificationKey)) {
                        // we have a new notification!
                        if (DEBUG_MEDIA) {
                            Log.v(TAG, "DEBUG_MEDIA: Found new media notification: key="
                                    + notificationKey + " controller=" + controller);
                        }
                        mMediaNotificationKey = notificationKey;
                    }
                } else {
                    mMediaMetadata = null;
                    mMediaNotificationKey = null;
                }

                metaDataChanged = true;
            } else {
                // Media session unchanged

                if (DEBUG_MEDIA) {
                    Log.v(TAG, "DEBUG_MEDIA: Continuing media notification: key=" + mMediaNotificationKey);
                }
            }
        }

        updateMediaMetaData(metaDataChanged);
    }

    private boolean sameSessions(MediaController a, MediaController b) {
        if (a == b) return true;
        if (a == null) return false;
        return a.controlsSameSession(b);
    }

    /**
     * Hide the album artwork that is fading out and release its bitmap.
     */
    private Runnable mHideBackdropFront = new Runnable() {
        @Override
        public void run() {
            if (DEBUG_MEDIA) {
                Log.v(TAG, "DEBUG_MEDIA: removing fade layer");
            }
            mBackdropFront.setVisibility(View.INVISIBLE);
            mBackdropFront.animate().cancel();
            mBackdropFront.setImageDrawable(null);
        }
    };

    /**
     * Refresh or remove lockscreen artwork from media metadata.
     */
    public void updateMediaMetaData(boolean metaDataChanged) {
        if (!SHOW_LOCKSCREEN_MEDIA_ARTWORK) return;

        if (mBackdrop == null) return; // called too early

        if (DEBUG_MEDIA) {
            Log.v(TAG, "DEBUG_MEDIA: updating album art for notification " + mMediaNotificationKey
                + " metadata=" + mMediaMetadata
                + " metaDataChanged=" + metaDataChanged
                + " state=" + mState);
        }

        Bitmap backdropBitmap = null;

        // apply any album artwork first
        if (mMediaMetadata != null) {
            backdropBitmap = mMediaMetadata.getBitmap(MediaMetadata.METADATA_KEY_ART);
            if (backdropBitmap == null) {
                backdropBitmap = mMediaMetadata.getBitmap(MediaMetadata.METADATA_KEY_ALBUM_ART);
                // might still be null
            }
        }

        WallpaperManager wm = (WallpaperManager) mContext.getSystemService(
                Context.WALLPAPER_SERVICE);
        boolean keyguardVisible = (mState != StatusBarState.SHADE);
        boolean visualizerVisible = mVisualizerEnabled && keyguardVisible
                && (mMediaController != null);

        if (backdropBitmap == null && (mMediaMetadata == null || visualizerVisible)) {
            backdropBitmap = mKeyguardWallpaper;
        }

        if (visualizerVisible) {
            mBackdrop.setBitmap(backdropBitmap);
        }

        final boolean hasBackdrop = backdropBitmap != null;
        mKeyguardShowingMedia = hasBackdrop;
        if (mStatusBarWindowManager != null) {
            mStatusBarWindowManager.setShowingMedia(mKeyguardShowingMedia);
        }

        if ((hasBackdrop || DEBUG_MEDIA_FAKE_ARTWORK) && keyguardVisible) {
            // time to show some art!
            if (mBackdrop.getVisibility() != View.VISIBLE) {
                mBackdrop.setVisibility(View.VISIBLE);
                mBackdrop.animate().alpha(1f);
                metaDataChanged = true;
                if (DEBUG_MEDIA) {
                    Log.v(TAG, "DEBUG_MEDIA: Fading in album artwork");
                }
            }
            if (metaDataChanged) {
                if (mBackdropBack.getDrawable() != null) {
                    Drawable drawable = mBackdropBack.getDrawable();
                    mBackdropFront.setImageDrawable(drawable);
                    if (mScrimSrcModeEnabled) {
                        mBackdropFront.getDrawable().mutate().setXfermode(mSrcOverXferMode);
                    }
                    mBackdropFront.setAlpha(1f);
                    mBackdropFront.setVisibility(View.VISIBLE);
                } else {
                    mBackdropFront.setVisibility(View.INVISIBLE);
                }

                if (DEBUG_MEDIA_FAKE_ARTWORK) {
                    final int c = 0xFF000000 | (int)(Math.random() * 0xFFFFFF);
                    Log.v(TAG, String.format("DEBUG_MEDIA: setting new color: 0x%08x", c));
                    mBackdropBack.setBackgroundColor(0xFFFFFFFF);
                    mBackdropBack.setImageDrawable(new ColorDrawable(c));
                } else {
                    mBackdropBack.setImageBitmap(backdropBitmap);
                }
                if (mScrimSrcModeEnabled) {
                    mBackdropBack.getDrawable().mutate().setXfermode(mSrcXferMode);
                }

                if (mBackdropFront.getVisibility() == View.VISIBLE) {
                    if (DEBUG_MEDIA) {
                        Log.v(TAG, "DEBUG_MEDIA: Crossfading album artwork from "
                                + mBackdropFront.getDrawable()
                                + " to "
                                + mBackdropBack.getDrawable());
                    }
                    mBackdropFront.animate()
                            .setDuration(250)
                            .alpha(0f).withEndAction(mHideBackdropFront);
                }
            }
        } else {
            // need to hide the album art, either because we are unlocked or because
            // the metadata isn't there to support it
            if (mBackdrop.getVisibility() != View.GONE) {
                if (DEBUG_MEDIA) {
                    Log.v(TAG, "DEBUG_MEDIA: Fading out album artwork");
                }
                mBackdrop.animate()
                        .alpha(0f)
                        .setInterpolator(mBackdropInterpolator)
                        .setDuration(300)
                        .setStartDelay(0)
                        .withEndAction(new Runnable() {
                            @Override
                            public void run() {
                                mBackdrop.setVisibility(View.GONE);
                                mBackdropFront.animate().cancel();
                                mBackdropBack.animate().cancel();
                                mHandler.post(mHideBackdropFront);
                            }
                        });
                if (mKeyguardFadingAway) {
                    mBackdrop.animate()

                            // Make it disappear faster, as the focus should be on the activity behind.
                            .setDuration(mKeyguardFadingAwayDuration / 2)
                            .setStartDelay(mKeyguardFadingAwayDelay)
                            .setInterpolator(mLinearInterpolator)
                            .start();
                }
            }
        }
    }

    private int adjustDisableFlags(int state) {
        if (!mLaunchTransitionFadingAway
                && (mExpandedVisible || mBouncerShowing || mWaitingForKeyguardExit)) {
            state |= StatusBarManager.DISABLE_NOTIFICATION_ICONS;
            state |= StatusBarManager.DISABLE_SYSTEM_INFO;
        }
        return state;
    }

    /**
     * State is one or more of the DISABLE constants from StatusBarManager.
     */
    public void disable(int state, boolean animate) {
        mDisabledUnmodified = state;
        state = adjustDisableFlags(state);
        final int old = mDisabled;
        final int diff = state ^ old;
        mDisabled = state;

        if (DEBUG) {
            Log.d(TAG, String.format("disable: 0x%08x -> 0x%08x (diff: 0x%08x)",
                old, state, diff));
        }

        StringBuilder flagdbg = new StringBuilder();
        flagdbg.append("disable: < ");
        flagdbg.append(((state & StatusBarManager.DISABLE_EXPAND) != 0) ? "EXPAND" : "expand");
        flagdbg.append(((diff  & StatusBarManager.DISABLE_EXPAND) != 0) ? "* " : " ");
        flagdbg.append(((state & StatusBarManager.DISABLE_NOTIFICATION_ICONS) != 0) ? "ICONS" : "icons");
        flagdbg.append(((diff  & StatusBarManager.DISABLE_NOTIFICATION_ICONS) != 0) ? "* " : " ");
        flagdbg.append(((state & StatusBarManager.DISABLE_NOTIFICATION_ALERTS) != 0) ? "ALERTS" : "alerts");
        flagdbg.append(((diff  & StatusBarManager.DISABLE_NOTIFICATION_ALERTS) != 0) ? "* " : " ");
        flagdbg.append(((state & StatusBarManager.DISABLE_SYSTEM_INFO) != 0) ? "SYSTEM_INFO" : "system_info");
        flagdbg.append(((diff  & StatusBarManager.DISABLE_SYSTEM_INFO) != 0) ? "* " : " ");
        flagdbg.append(((state & StatusBarManager.DISABLE_BACK) != 0) ? "BACK" : "back");
        flagdbg.append(((diff  & StatusBarManager.DISABLE_BACK) != 0) ? "* " : " ");
        flagdbg.append(((state & StatusBarManager.DISABLE_HOME) != 0) ? "HOME" : "home");
        flagdbg.append(((diff  & StatusBarManager.DISABLE_HOME) != 0) ? "* " : " ");
        flagdbg.append(((state & StatusBarManager.DISABLE_RECENT) != 0) ? "RECENT" : "recent");
        flagdbg.append(((diff  & StatusBarManager.DISABLE_RECENT) != 0) ? "* " : " ");
        flagdbg.append(((state & StatusBarManager.DISABLE_CLOCK) != 0) ? "CLOCK" : "clock");
        flagdbg.append(((diff  & StatusBarManager.DISABLE_CLOCK) != 0) ? "* " : " ");
        flagdbg.append(((state & StatusBarManager.DISABLE_SEARCH) != 0) ? "SEARCH" : "search");
        flagdbg.append(((diff  & StatusBarManager.DISABLE_SEARCH) != 0) ? "* " : " ");
        flagdbg.append(">");
        Log.d(TAG, flagdbg.toString());

        if ((diff & StatusBarManager.DISABLE_SYSTEM_INFO) != 0) {
            mSystemIconArea.animate().cancel();
            mClockView.animate().cancel();
            if ((state & StatusBarManager.DISABLE_SYSTEM_INFO) != 0) {
                if (mClockLocation != Clock.STYLE_HIDE_CLOCK) {
                    animateStatusBarHide(mClockView, animate);
                }
                animateStatusBarHide(mSystemIconArea, animate);
            } else {
                if (mClockLocation != Clock.STYLE_HIDE_CLOCK) {
                    animateStatusBarShow(mClockView, animate);
                }
                animateStatusBarShow(mSystemIconArea, animate);
            }
        }

        if ((diff & StatusBarManager.DISABLE_CLOCK) != 0) {
            boolean show = (state & StatusBarManager.DISABLE_CLOCK) == 0;
            showClock(show);
        }
        if ((diff & StatusBarManager.DISABLE_EXPAND) != 0) {
            if ((state & StatusBarManager.DISABLE_EXPAND) != 0) {
                animateCollapsePanels();
            }
        }

        if ((diff & (StatusBarManager.DISABLE_HOME
                        | StatusBarManager.DISABLE_RECENT
                        | StatusBarManager.DISABLE_BACK
                        | StatusBarManager.DISABLE_SEARCH)) != 0) {
            // the nav bar will take care of these
            if (mNavigationBarView != null) mNavigationBarView.setDisabledFlags(state);

            if ((state & StatusBarManager.DISABLE_RECENT) != 0) {
                // close recents if it's visible
                mHandler.removeMessages(MSG_HIDE_RECENT_APPS);
                mHandler.sendEmptyMessage(MSG_HIDE_RECENT_APPS);
            }
        }

        if ((diff & StatusBarManager.DISABLE_NOTIFICATION_ICONS) != 0) {
            if ((state & StatusBarManager.DISABLE_NOTIFICATION_ICONS) != 0) {
                if (mTicking) {
                    haltTicker();
                }
                animateStatusBarHide(mNotificationIconArea, animate);
            } else {
                animateStatusBarShow(mNotificationIconArea, animate);
            }
        }

        if ((diff & StatusBarManager.DISABLE_NOTIFICATION_ALERTS) != 0) {
            mDisableNotificationAlerts =
                    (state & StatusBarManager.DISABLE_NOTIFICATION_ALERTS) != 0;
            mHeadsUpObserver.onChange(true);
        }
    }

    /**
     * Animates {@code v}, a view that is part of the status bar, out.
     */
    private void animateStatusBarHide(final View v, boolean animate) {
        v.animate().cancel();
        if (!animate) {
            v.setAlpha(0f);
            v.setVisibility(View.INVISIBLE);
            return;
        }
        v.animate()
                .alpha(0f)
                .setDuration(160)
                .setStartDelay(0)
                .setInterpolator(ALPHA_OUT)
                .withEndAction(new Runnable() {
                    @Override
                    public void run() {
                        v.setVisibility(View.INVISIBLE);
                    }
                });
    }

    /**
     * Animates {@code v}, a view that is part of the status bar, in.
     */
    private void animateStatusBarShow(View v, boolean animate) {
        v.animate().cancel();
        v.setVisibility(View.VISIBLE);
        if (!animate) {
            v.setAlpha(1f);
            return;
        }
        v.animate()
                .alpha(1f)
                .setDuration(320)
                .setInterpolator(ALPHA_IN)
                .setStartDelay(50)

                // We need to clean up any pending end action from animateStatusBarHide if we call
                // both hide and show in the same frame before the animation actually gets started.
                // cancel() doesn't really remove the end action.
                .withEndAction(null);

        // Synchronize the motion with the Keyguard fading if necessary.
        if (mKeyguardFadingAway) {
            v.animate()
                    .setDuration(mKeyguardFadingAwayDuration)
                    .setInterpolator(mLinearOutSlowIn)
                    .setStartDelay(mKeyguardFadingAwayDelay)
                    .start();
        }
    }

    @Override
    protected BaseStatusBar.H createHandler() {
        return new PhoneStatusBar.H();
    }

    @Override
    public void startActivity(Intent intent, boolean dismissShade) {
        startActivityDismissingKeyguard(intent, false, dismissShade);
    }

    public ScrimController getScrimController() {
        return mScrimController;
    }

    public void setQsExpanded(boolean expanded) {
        mStatusBarWindowManager.setQsExpanded(expanded);
    }

    public boolean isGoingToNotificationShade() {
        return mLeaveOpenOnKeyguardHide;
    }

    public boolean isKeyguardShowingMedia() {
        return mKeyguardShowingMedia;
    }

    public boolean isQsExpanded() {
        return mNotificationPanel.isQsExpanded();
    }

    public boolean isScreenOnComingFromTouch() {
        return mScreenOnComingFromTouch;
    }

    void setBlur(float b){
        mStatusBarWindowManager.setBlur(b);
    }

    public boolean isFalsingThresholdNeeded() {
        boolean onKeyguard = getBarState() == StatusBarState.KEYGUARD;
        boolean isCurrentlyInsecure = mUnlockMethodCache.isCurrentlyInsecure();
        return onKeyguard && (isCurrentlyInsecure || mDozing || mScreenOnComingFromTouch);
    }

    public boolean isDozing() {
        return mDozing;
    }

    @Override  // NotificationData.Environment
    public String getCurrentMediaNotificationKey() {
        return mMediaNotificationKey;
    }

    public boolean isScrimSrcModeEnabled() {
        return mScrimSrcModeEnabled;
    }

    /**
     * To be called when there's a state change in StatusBarKeyguardViewManager.
     */
    public void onKeyguardViewManagerStatesUpdated() {
        logStateToEventlog();
    }

    @Override  // UnlockMethodCache.OnUnlockMethodChangedListener
    public void onUnlockMethodStateChanged() {
        logStateToEventlog();
    }

    /**
     * All changes to the status bar and notifications funnel through here and are batched.
     */
    private class H extends BaseStatusBar.H {
        public void handleMessage(Message m) {
            super.handleMessage(m);
            switch (m.what) {
                case MSG_OPEN_NOTIFICATION_PANEL:
                    animateExpandNotificationsPanel();
                    break;
                case MSG_OPEN_SETTINGS_PANEL:
                    animateExpandSettingsPanel();
                    break;
                case MSG_CLOSE_PANELS:
                    animateCollapsePanels();
                    break;
                case MSG_SHOW_HEADS_UP:
                    setHeadsUpVisibility(true);
                    break;
                case MSG_DECAY_HEADS_UP:
                    mHeadsUpNotificationView.release();
                    setHeadsUpVisibility(false);
                    break;
                case MSG_HIDE_HEADS_UP:
                    mHeadsUpNotificationView.release();
                    setHeadsUpVisibility(false);
                    break;
                case MSG_ESCALATE_HEADS_UP:
                    escalateHeadsUp();
                    setHeadsUpVisibility(false);
                    break;
                case MSG_LAUNCH_TRANSITION_TIMEOUT:
                    onLaunchTransitionTimeout();
                    break;
                case MSG_UPDATE_NOTIFICATIONS:
                    handleUpdateNotifications();
                    break;
            }
        }
    }

    /**  if the interrupting notification had a fullscreen intent, fire it now.  */
    private void escalateHeadsUp() {
        if (mHeadsUpNotificationView.getEntry() != null) {
            final StatusBarNotification sbn = mHeadsUpNotificationView.getEntry().notification;
            mHeadsUpNotificationView.release();
            final Notification notification = sbn.getNotification();
            if (notification.fullScreenIntent != null) {
                if (DEBUG)
                    Log.d(TAG, "converting a heads up to fullScreen");
                try {
                    EventLog.writeEvent(EventLogTags.SYSUI_HEADS_UP_ESCALATION,
                            sbn.getKey());
                    notification.fullScreenIntent.send();
                } catch (PendingIntent.CanceledException e) {
                }
            }
        }
    }

    View.OnFocusChangeListener mFocusChangeListener = new View.OnFocusChangeListener() {
        public void onFocusChange(View v, boolean hasFocus) {
            // Because 'v' is a ViewGroup, all its children will be (un)selected
            // too, which allows marqueeing to work.
            v.setSelected(hasFocus);
        }
    };

    boolean panelsEnabled() {
        return (mDisabled & StatusBarManager.DISABLE_EXPAND) == 0;
    }

    void makeExpandedVisible(boolean force) {
        if (SPEW) Log.d(TAG, "Make expanded visible: expanded visible=" + mExpandedVisible);
        if (!force && (mExpandedVisible || !panelsEnabled())) {
            return;
        }

        mExpandedVisible = true;
        if (mNavigationBarView != null)
            mNavigationBarView.setSlippery(true);

        updateCarrierLabelVisibility(true);

        updateExpandedViewPos(EXPANDED_LEAVE_ALONE);

        // Expand the window to encompass the full screen in anticipation of the drag.
        // This is only possible to do atomically because the status bar is at the top of the screen!
        mStatusBarWindowManager.setStatusBarExpanded(true);
        mStatusBarView.setFocusable(false);

        visibilityChanged(true);
        mWaitingForKeyguardExit = false;
        disable(mDisabledUnmodified, !force /* animate */);
        setInteracting(StatusBarManager.WINDOW_STATUS_BAR, true);
    }

    public void animateCollapsePanels() {
        animateCollapsePanels(CommandQueue.FLAG_EXCLUDE_NONE);
    }

    private final Runnable mAnimateCollapsePanels = new Runnable() {
        @Override
        public void run() {
            animateCollapsePanels();
        }
    };

    public void postAnimateCollapsePanels() {
        mHandler.post(mAnimateCollapsePanels);
    }

    public void animateCollapsePanels(int flags) {
        animateCollapsePanels(flags, false /* force */);
    }

    public void animateCollapsePanels(int flags, boolean force) {
        if (!force &&
                (mState == StatusBarState.KEYGUARD || mState == StatusBarState.SHADE_LOCKED)) {
            runPostCollapseRunnables();
            return;
        }
        if (SPEW) {
            Log.d(TAG, "animateCollapse():"
                    + " mExpandedVisible=" + mExpandedVisible
                    + " flags=" + flags);
        }

        if ((flags & CommandQueue.FLAG_EXCLUDE_RECENTS_PANEL) == 0) {
            if (!mHandler.hasMessages(MSG_HIDE_RECENT_APPS)) {
                mHandler.removeMessages(MSG_HIDE_RECENT_APPS);
                mHandler.sendEmptyMessage(MSG_HIDE_RECENT_APPS);
            }
        }

        if ((flags & CommandQueue.FLAG_EXCLUDE_SEARCH_PANEL) == 0) {
            mHandler.removeMessages(MSG_CLOSE_SEARCH_PANEL);
            mHandler.sendEmptyMessage(MSG_CLOSE_SEARCH_PANEL);
        }

        if (mStatusBarWindow != null) {
            // release focus immediately to kick off focus change transition
            mStatusBarWindowManager.setStatusBarFocusable(false);

            mStatusBarWindow.cancelExpandHelper();
            mStatusBarView.collapseAllPanels(true);
        }
    }

    private void runPostCollapseRunnables() {
        int size = mPostCollapseRunnables.size();
        for (int i = 0; i < size; i++) {
            mPostCollapseRunnables.get(i).run();
        }
        mPostCollapseRunnables.clear();
    }

    public ViewPropertyAnimator setVisibilityWhenDone(
            final ViewPropertyAnimator a, final View v, final int vis) {
        a.setListener(new AnimatorListenerAdapter() {
            @Override
            public void onAnimationEnd(Animator animation) {
                v.setVisibility(vis);
                a.setListener(null); // oneshot
            }
        });
        return a;
    }

    public Animator setVisibilityWhenDone(
            final Animator a, final View v, final int vis) {
        a.addListener(new AnimatorListenerAdapter() {
            @Override
            public void onAnimationEnd(Animator animation) {
                v.setVisibility(vis);
            }
        });
        return a;
    }

    public Animator interpolator(TimeInterpolator ti, Animator a) {
        a.setInterpolator(ti);
        return a;
    }

    public Animator startDelay(int d, Animator a) {
        a.setStartDelay(d);
        return a;
    }

    public Animator start(Animator a) {
        a.start();
        return a;
    }

    final TimeInterpolator mAccelerateInterpolator = new AccelerateInterpolator();
    final TimeInterpolator mDecelerateInterpolator = new DecelerateInterpolator();
    final int FLIP_DURATION_OUT = 125;
    final int FLIP_DURATION_IN = 225;
    final int FLIP_DURATION = (FLIP_DURATION_IN + FLIP_DURATION_OUT);

    Animator mScrollViewAnim, mClearButtonAnim;

    @Override
    public void animateExpandNotificationsPanel() {
        if (SPEW) Log.d(TAG, "animateExpand: mExpandedVisible=" + mExpandedVisible);
        if (!panelsEnabled()) {
            return ;
        }

        mNotificationPanel.expand();

        if (false) postStartTracing();
    }

    @Override
    public void animateExpandSettingsPanel() {
        if (SPEW) Log.d(TAG, "animateExpand: mExpandedVisible=" + mExpandedVisible);
        if (!panelsEnabled()) {
            return;
        }

        // Settings are not available in setup
        if (!mUserSetup) return;

        mNotificationPanel.expandWithQs();

        if (false) postStartTracing();
    }

    public void animateCollapseQuickSettings() {
        if (mState == StatusBarState.SHADE) {
            mStatusBarView.collapseAllPanels(true);
        }
    }

    void makeExpandedInvisible() {
        if (SPEW) Log.d(TAG, "makeExpandedInvisible: mExpandedVisible=" + mExpandedVisible
                + " mExpandedVisible=" + mExpandedVisible);

        if (!mExpandedVisible || mStatusBarWindow == null) {
            return;
        }

        // Ensure the panel is fully collapsed (just in case; bug 6765842, 7260868)
        mStatusBarView.collapseAllPanels(/*animate=*/ false);

        // reset things to their proper state
        if (mScrollViewAnim != null) mScrollViewAnim.cancel();
        if (mClearButtonAnim != null) mClearButtonAnim.cancel();

        mStackScroller.setVisibility(View.VISIBLE);
        mNotificationPanel.setVisibility(View.GONE);

        mNotificationPanel.closeQs();

        mExpandedVisible = false;
        if (mNavigationBarView != null)
            mNavigationBarView.setSlippery(false);
        visibilityChanged(false);

        // Shrink the window to the size of the status bar only
        mStatusBarWindowManager.setStatusBarExpanded(false);
        mStatusBarView.setFocusable(true);

        // Close any "App info" popups that might have snuck on-screen
        dismissPopups();

        runPostCollapseRunnables();
        setInteracting(StatusBarManager.WINDOW_STATUS_BAR, false);
        showBouncer();
        disable(mDisabledUnmodified, true /* animate */);

        // Trimming will happen later if Keyguard is showing - doing it here might cause a jank in
        // the bouncer appear animation.
        if (!mStatusBarKeyguardViewManager.isShowing()) {
            WindowManagerGlobal.getInstance().trimMemory(ComponentCallbacks2.TRIM_MEMORY_UI_HIDDEN);
        }
    }

    private void adjustBrightness(int x) {
        mBrightnessChanged = true;
        float raw = ((float) x) / mScreenWidth;

        // Add a padding to the brightness control on both sides to
        // make it easier to reach min/max brightness
        float padded = Math.min(1.0f - BRIGHTNESS_CONTROL_PADDING,
                Math.max(BRIGHTNESS_CONTROL_PADDING, raw));
        float value = (padded - BRIGHTNESS_CONTROL_PADDING) /
                (1 - (2.0f * BRIGHTNESS_CONTROL_PADDING));
        try {
            IPowerManager power = IPowerManager.Stub.asInterface(
                    ServiceManager.getService("power"));
            if (power != null) {
                if (mAutomaticBrightness) {
                    float adj = (value * 100) / (BRIGHTNESS_ADJ_RESOLUTION / 2f) - 1;
                    adj = Math.max(adj, -1);
                    adj = Math.min(adj, 1);
                    final float val = adj;
                    power.setTemporaryScreenAutoBrightnessAdjustmentSettingOverride(val);
                    AsyncTask.execute(new Runnable() {
                        public void run() {
                            Settings.System.putFloatForUser(mContext.getContentResolver(),
                                    Settings.System.SCREEN_AUTO_BRIGHTNESS_ADJ, val,
                                    UserHandle.USER_CURRENT);
                        }
                    });
                } else {
                    int newBrightness = mMinBrightness + (int) Math.round(value *
                            (android.os.PowerManager.BRIGHTNESS_ON - mMinBrightness));
                    newBrightness = Math.min(newBrightness, android.os.PowerManager.BRIGHTNESS_ON);
                    newBrightness = Math.max(newBrightness, mMinBrightness);
                    final int val = newBrightness;
                    power.setTemporaryScreenBrightnessSettingOverride(val);
                    AsyncTask.execute(new Runnable() {
                        @Override
                        public void run() {
                            Settings.System.putIntForUser(mContext.getContentResolver(),
                                    Settings.System.SCREEN_BRIGHTNESS, val,
                                    UserHandle.USER_CURRENT);
                        }
                    });
                }


            }
        } catch (RemoteException e) {
            Log.w(TAG, "Setting Brightness failed: " + e);
        }
    }

    private void brightnessControl(MotionEvent event) {
        final int action = event.getAction();
        final int x = (int) event.getRawX();
        final int y = (int) event.getRawY();
        if (action == MotionEvent.ACTION_DOWN) {
            if (y < mStatusBarHeaderHeight) {
                mLinger = 0;
                mInitialTouchX = x;
                mInitialTouchY = y;
                mJustPeeked = true;
                mHandler.removeCallbacks(mLongPressBrightnessChange);
                mHandler.postDelayed(mLongPressBrightnessChange,
                        BRIGHTNESS_CONTROL_LONG_PRESS_TIMEOUT);
            }
        } else if (action == MotionEvent.ACTION_MOVE) {
            if (y < mStatusBarHeaderHeight && mJustPeeked) {
                if (mLinger > BRIGHTNESS_CONTROL_LINGER_THRESHOLD) {
                    adjustBrightness(x);
                } else {
                    final int xDiff = Math.abs(x - mInitialTouchX);
                    final int yDiff = Math.abs(y - mInitialTouchY);
                    final int touchSlop = ViewConfiguration.get(mContext).getScaledTouchSlop();
                    if (xDiff > yDiff) {
                        mLinger++;
                    }
                    if (xDiff > touchSlop || yDiff > touchSlop) {
                        mHandler.removeCallbacks(mLongPressBrightnessChange);
                    }
                }
            } else {
                if (y > mStatusBarHeaderHeight) {
                    mJustPeeked = false;
                }
                mHandler.removeCallbacks(mLongPressBrightnessChange);
            }
        } else if (action == MotionEvent.ACTION_UP
                || action == MotionEvent.ACTION_CANCEL) {
            mHandler.removeCallbacks(mLongPressBrightnessChange);
        }
    }

    public boolean interceptTouchEvent(MotionEvent event) {
        if (DEBUG_GESTURES) {
            if (event.getActionMasked() != MotionEvent.ACTION_MOVE) {
                EventLog.writeEvent(EventLogTags.SYSUI_STATUSBAR_TOUCH,
                        event.getActionMasked(), (int) event.getX(), (int) event.getY(), mDisabled);
            }

        }

        if (SPEW) {
            Log.d(TAG, "Touch: rawY=" + event.getRawY() + " event=" + event + " mDisabled="
                + mDisabled + " mTracking=" + mTracking);
        } else if (CHATTY) {
            if (event.getAction() != MotionEvent.ACTION_MOVE) {
                Log.d(TAG, String.format(
                            "panel: %s at (%f, %f) mDisabled=0x%08x",
                            MotionEvent.actionToString(event.getAction()),
                            event.getRawX(), event.getRawY(), mDisabled));
            }
        }

        if (DEBUG_GESTURES) {
            mGestureRec.add(event);
        }

        if (mBrightnessControl) {
            brightnessControl(event);
            if ((mDisabled & StatusBarManager.DISABLE_EXPAND) != 0) {
                return true;
            }
        }

        final boolean upOrCancel =
                event.getAction() == MotionEvent.ACTION_UP ||
                        event.getAction() == MotionEvent.ACTION_CANCEL;
        if (mStatusBarWindowState == WINDOW_STATE_SHOWING) {
            if (upOrCancel && !mExpandedVisible) {
                setInteracting(StatusBarManager.WINDOW_STATUS_BAR, false);
            } else {
                setInteracting(StatusBarManager.WINDOW_STATUS_BAR, true);
            }
        }
        if (mBrightnessChanged && upOrCancel) {
            mBrightnessChanged = false;
            if (mJustPeeked && mExpandedVisible) {
                mNotificationPanel.fling(10, false);
            }
        }
        return false;
    }

    public GestureRecorder getGestureRecorder() {
        return mGestureRec;
    }

    private void setNavigationIconHints(int hints) {
        if (hints == mNavigationIconHints) return;

        mNavigationIconHints = hints;

        if (mNavigationBarView != null) {
            mNavigationBarView.setNavigationIconHints(hints);
        }
        checkBarModes();
    }

    @Override // CommandQueue
    public void setWindowState(int window, int state) {
        boolean showing = state == WINDOW_STATE_SHOWING;
        if (mStatusBarWindow != null
                && window == StatusBarManager.WINDOW_STATUS_BAR
                && mStatusBarWindowState != state) {
            mStatusBarWindowState = state;
            if (DEBUG_WINDOW_STATE) Log.d(TAG, "Status bar " + windowStateToString(state));
            if (!showing && mState == StatusBarState.SHADE) {
                mStatusBarView.collapseAllPanels(false);
            }
        }
        if (mNavigationBarView != null
                && window == StatusBarManager.WINDOW_NAVIGATION_BAR
                && mNavigationBarWindowState != state) {
            mNavigationBarWindowState = state;
            if (DEBUG_WINDOW_STATE) Log.d(TAG, "Navigation bar " + windowStateToString(state));
        }
    }

    @Override // CommandQueue
    public void buzzBeepBlinked() {
        if (mDozeServiceHost != null) {
            mDozeServiceHost.fireBuzzBeepBlinked();
        }
    }

    @Override
    public void notificationLightOff() {
        if (mDozeServiceHost != null) {
            mDozeServiceHost.fireNotificationLight(false);
        }
    }

    @Override
    public void notificationLightPulse(int argb, int onMillis, int offMillis) {
        if (mDozeServiceHost != null) {
            mDozeServiceHost.fireNotificationLight(true);
        }
    }

    @Override // CommandQueue
    public void setSystemUiVisibility(int vis, int mask) {
        final int oldVal = mSystemUiVisibility;
        final int newVal = (oldVal&~mask) | (vis&mask);
        final int diff = newVal ^ oldVal;
        if (DEBUG) Log.d(TAG, String.format(
                "setSystemUiVisibility vis=%s mask=%s oldVal=%s newVal=%s diff=%s",
                Integer.toHexString(vis), Integer.toHexString(mask),
                Integer.toHexString(oldVal), Integer.toHexString(newVal),
                Integer.toHexString(diff)));
        if (diff != 0) {
            // we never set the recents bit via this method, so save the prior state to prevent
            // clobbering the bit below
            final boolean wasRecentsVisible = (mSystemUiVisibility & View.RECENT_APPS_VISIBLE) > 0;

            mSystemUiVisibility = newVal;

            // update low profile
            if ((diff & View.SYSTEM_UI_FLAG_LOW_PROFILE) != 0) {
                final boolean lightsOut = (vis & View.SYSTEM_UI_FLAG_LOW_PROFILE) != 0;
                if (lightsOut) {
                    animateCollapsePanels();
                    if (mTicking) {
                        haltTicker();
                    }
                }

                setAreThereNotifications();
            }

            // update status bar mode
            final int sbMode = computeBarMode(oldVal, newVal, mStatusBarView.getBarTransitions(),
                    View.STATUS_BAR_TRANSIENT, View.STATUS_BAR_TRANSLUCENT);

            // update navigation bar mode
            final int nbMode = mNavigationBarView == null ? -1 : computeBarMode(
                    oldVal, newVal, mNavigationBarView.getBarTransitions(),
                    View.NAVIGATION_BAR_TRANSIENT, View.NAVIGATION_BAR_TRANSLUCENT);
            final boolean sbModeChanged = sbMode != -1;
            final boolean nbModeChanged = nbMode != -1;
            boolean checkBarModes = false;
            if (sbModeChanged && sbMode != mStatusBarMode) {
                mStatusBarMode = sbMode;
                checkBarModes = true;
            }
            if (nbModeChanged && nbMode != mNavigationBarMode) {
                mNavigationBarMode = nbMode;
                checkBarModes = true;
            }
            if (checkBarModes) {
                checkBarModes();
            }
            if (sbModeChanged || nbModeChanged) {
                // update transient bar autohide
                if (mStatusBarMode == MODE_SEMI_TRANSPARENT || mNavigationBarMode == MODE_SEMI_TRANSPARENT) {
                    scheduleAutohide();
                } else {
                    cancelAutohide();
                }
            }

            // ready to unhide
            if ((vis & View.STATUS_BAR_UNHIDE) != 0) {
                mSystemUiVisibility &= ~View.STATUS_BAR_UNHIDE;
            }
            if ((vis & View.NAVIGATION_BAR_UNHIDE) != 0) {
                mSystemUiVisibility &= ~View.NAVIGATION_BAR_UNHIDE;
            }

            // restore the recents bit
            if (wasRecentsVisible) {
                mSystemUiVisibility |= View.RECENT_APPS_VISIBLE;
            }

            // send updated sysui visibility to window manager
            notifyUiVisibilityChanged(mSystemUiVisibility);
        }
    }

    private int computeBarMode(int oldVis, int newVis, BarTransitions transitions,
            int transientFlag, int translucentFlag) {
        final int oldMode = barMode(oldVis, transientFlag, translucentFlag);
        final int newMode = barMode(newVis, transientFlag, translucentFlag);
        if (oldMode == newMode) {
            return -1; // no mode change
        }
        return newMode;
    }

    private int barMode(int vis, int transientFlag, int translucentFlag) {
        int lightsOutTransparent = View.SYSTEM_UI_FLAG_LOW_PROFILE | View.SYSTEM_UI_TRANSPARENT;
        return (vis & transientFlag) != 0 ? MODE_SEMI_TRANSPARENT
                : (vis & translucentFlag) != 0 ? MODE_TRANSLUCENT
                : (vis & lightsOutTransparent) == lightsOutTransparent ? MODE_LIGHTS_OUT_TRANSPARENT
                : (vis & View.SYSTEM_UI_TRANSPARENT) != 0 ? MODE_TRANSPARENT
                : (vis & View.SYSTEM_UI_FLAG_LOW_PROFILE) != 0 ? MODE_LIGHTS_OUT
                : MODE_OPAQUE;
    }

    private void checkBarModes() {
        if (mDemoMode) return;
        checkBarMode(mStatusBarMode, mStatusBarWindowState, mStatusBarView.getBarTransitions());
        if (mNavigationBarView != null) {
            checkBarMode(mNavigationBarMode,
                    mNavigationBarWindowState, mNavigationBarView.getBarTransitions());
        }
    }

    private void checkBarMode(int mode, int windowState, BarTransitions transitions) {
        final boolean powerSave = mBatteryController.isPowerSave();
        final boolean anim = (mScreenOn == null || mScreenOn) && windowState != WINDOW_STATE_HIDDEN
                && !powerSave;
        if (powerSave && getBarState() == StatusBarState.SHADE) {
            mode = MODE_WARNING;
        }
        transitions.transitionTo(mode, anim);
    }

    private void finishBarAnimations() {
        mStatusBarView.getBarTransitions().finishAnimations();
        if (mNavigationBarView != null) {
            mNavigationBarView.getBarTransitions().finishAnimations();
        }
    }

    private final Runnable mCheckBarModes = new Runnable() {
        @Override
        public void run() {
            checkBarModes();
        }
    };

    @Override
    public void setInteracting(int barWindow, boolean interacting) {
        final boolean changing = ((mInteractingWindows & barWindow) != 0) != interacting;
        mInteractingWindows = interacting
                ? (mInteractingWindows | barWindow)
                : (mInteractingWindows & ~barWindow);
        if (mInteractingWindows != 0) {
            suspendAutohide();
        } else {
            resumeSuspendedAutohide();
        }
        // manually dismiss the volume panel when interacting with the nav bar
        if (changing && interacting && barWindow == StatusBarManager.WINDOW_NAVIGATION_BAR) {
            if (mVolumeComponent != null) {
                mVolumeComponent.dismissNow();
            }
        }
        checkBarModes();
    }

    private void resumeSuspendedAutohide() {
        if (mAutohideSuspended) {
            scheduleAutohide();
            mHandler.postDelayed(mCheckBarModes, 500); // longer than home -> launcher
        }
    }

    private void suspendAutohide() {
        mHandler.removeCallbacks(mAutohide);
        mHandler.removeCallbacks(mCheckBarModes);
        mAutohideSuspended = (mSystemUiVisibility & STATUS_OR_NAV_TRANSIENT) != 0;
    }

    private void cancelAutohide() {
        mAutohideSuspended = false;
        mHandler.removeCallbacks(mAutohide);
    }

    private void scheduleAutohide() {
        cancelAutohide();
        mHandler.postDelayed(mAutohide, isDeviceProvisioned()
                ? AUTOHIDE_TIMEOUT_MS : AUTOHIDE_TIMEOUT_MS_PROVISIONING);
    }

    private void checkUserAutohide(View v, MotionEvent event) {
        if ((mSystemUiVisibility & STATUS_OR_NAV_TRANSIENT) != 0  // a transient bar is revealed
                && event.getAction() == MotionEvent.ACTION_OUTSIDE // touch outside the source bar
                && event.getX() == 0 && event.getY() == 0  // a touch outside both bars
                ) {
            userAutohide();
        }
    }

    private void userAutohide() {
        cancelAutohide();
        mHandler.postDelayed(mAutohide, 350); // longer than app gesture -> flag clear
    }

    private boolean areLightsOn() {
        return 0 == (mSystemUiVisibility & View.SYSTEM_UI_FLAG_LOW_PROFILE);
    }

    public void setLightsOn(boolean on) {
        Log.v(TAG, "setLightsOn(" + on + ")");
        if (on) {
            setSystemUiVisibility(0, View.SYSTEM_UI_FLAG_LOW_PROFILE);
        } else {
            setSystemUiVisibility(View.SYSTEM_UI_FLAG_LOW_PROFILE, View.SYSTEM_UI_FLAG_LOW_PROFILE);
        }
    }

    private void notifyUiVisibilityChanged(int vis) {
        try {
            mWindowManagerService.statusBarVisibilityChanged(vis);
        } catch (RemoteException ex) {
        }
    }

    public void topAppWindowChanged(boolean showMenu) {
        if (DEBUG) {
            Log.d(TAG, (showMenu?"showing":"hiding") + " the MENU button");
        }
        if (mNavigationBarView != null) {
            mNavigationBarView.setMenuVisibility(showMenu);
        }

        // See above re: lights-out policy for legacy apps.
        if (showMenu) setLightsOn(true);
    }

    @Override
    public void setImeWindowStatus(IBinder token, int vis, int backDisposition,
            boolean showImeSwitcher) {
        boolean imeShown = (vis & InputMethodService.IME_VISIBLE) != 0;
        int flags = mNavigationIconHints;
        if ((backDisposition == InputMethodService.BACK_DISPOSITION_WILL_DISMISS) || imeShown) {
            flags |= NAVIGATION_HINT_BACK_ALT;
        } else {
            flags &= ~NAVIGATION_HINT_BACK_ALT;
        }
        if (showImeSwitcher) {
            flags |= NAVIGATION_HINT_IME_SHOWN;
        } else {
            flags &= ~NAVIGATION_HINT_IME_SHOWN;
        }

        setNavigationIconHints(flags);
    }

    @Override
    protected void tick(StatusBarNotification n, boolean firstTime) {
        if (!mTickerEnabled) return;

        // no ticking in lights-out mode
        if (!areLightsOn()) return;

        // no ticking in Setup
        if (!isDeviceProvisioned()) return;

        // not for you
        if (!isNotificationForCurrentProfiles(n)) return;

        // Show the ticker if one is requested. Also don't do this
        // until status bar window is attached to the window manager,
        // because...  well, what's the point otherwise?  And trying to
        // run a ticker without being attached will crash!
        if (n.getNotification().tickerText != null && mStatusBarWindow != null
                && mStatusBarWindow.getWindowToken() != null
                && shouldInterrupt(n)) {
            if (0 == (mDisabled & (StatusBarManager.DISABLE_NOTIFICATION_ICONS
                    | StatusBarManager.DISABLE_NOTIFICATION_TICKER))) {
                mTicker.addEntry(n);
            }
        }
    }

    private class MyTicker extends Ticker {
        MyTicker(Context context, View sb) {
            super(context, sb);
            if (!mTickerEnabled) {
                Log.w(TAG, "MyTicker instantiated with mTickerEnabled=false", new Throwable());
            }
        }

        @Override
        public void tickerStarting() {
            if (!mTickerEnabled) return;
            mTicking = true;
            mStatusBarContents.setVisibility(View.GONE);
            mStatusBarContents.startAnimation(loadAnim(com.android.internal.R.anim.push_up_out,
                    null));
            mTickerView.setVisibility(View.VISIBLE);
            mTickerView.startAnimation(loadAnim(com.android.internal.R.anim.push_up_in, null));
            mClockView.setVisibility(View.GONE);
            mClockView.startAnimation(loadAnim(com.android.internal.R.anim.push_up_out, null));
        }

        @Override
        public void tickerDone() {
            if (!mTickerEnabled) return;
            mStatusBarContents.setVisibility(View.VISIBLE);
            mStatusBarContents.startAnimation(loadAnim(com.android.internal.R.anim.push_down_in,
                    null));
            mTickerView.setVisibility(View.GONE);
            mTickerView.startAnimation(loadAnim(com.android.internal.R.anim.push_down_out,
                    mTickingDoneListener));
            mClockView.setVisibility(View.VISIBLE);
            mClockView.startAnimation(loadAnim(com.android.internal.R.anim.push_down_in, null));
        }

        public void tickerHalting() {
            if (!mTickerEnabled) return;
            if (mStatusBarContents.getVisibility() != View.VISIBLE) {
                mStatusBarContents.setVisibility(View.VISIBLE);
                mStatusBarContents
                        .startAnimation(loadAnim(com.android.internal.R.anim.fade_in, null));
                mClockView.setVisibility(View.VISIBLE);
                mClockView.startAnimation(loadAnim(com.android.internal.R.anim.fade_in, null));
            }
            mTickerView.setVisibility(View.GONE);
            // we do not animate the ticker away at this point, just get rid of it (b/6992707)
        }
    }

    Animation.AnimationListener mTickingDoneListener = new Animation.AnimationListener() {
        public void onAnimationEnd(Animation animation) {
            mTicking = false;
        }
        public void onAnimationRepeat(Animation animation) {
        }
        public void onAnimationStart(Animation animation) {
        }
    };

    private Animation loadAnim(int id, Animation.AnimationListener listener) {
        Animation anim = AnimationUtils.loadAnimation(mContext, id);
        if (listener != null) {
            anim.setAnimationListener(listener);
        }
        return anim;
    }

    public static String viewInfo(View v) {
        return "[(" + v.getLeft() + "," + v.getTop() + ")(" + v.getRight() + "," + v.getBottom()
                + ") " + v.getWidth() + "x" + v.getHeight() + "]";
    }

    public void dump(FileDescriptor fd, PrintWriter pw, String[] args) {
        synchronized (mQueueLock) {
            pw.println("Current Status Bar state:");
            pw.println("  mExpandedVisible=" + mExpandedVisible
                    + ", mTrackingPosition=" + mTrackingPosition);
            pw.println("  mTickerEnabled=" + mTickerEnabled);
            if (mTickerEnabled) {
                pw.println("  mTicking=" + mTicking);
                pw.println("  mTickerView: " + viewInfo(mTickerView));
            }
            pw.println("  mTracking=" + mTracking);
            pw.println("  mDisplayMetrics=" + mDisplayMetrics);
            pw.println("  mStackScroller: " + viewInfo(mStackScroller));
            pw.println("  mStackScroller: " + viewInfo(mStackScroller)
                    + " scroll " + mStackScroller.getScrollX()
                    + "," + mStackScroller.getScrollY());
        }

        pw.print("  mInteractingWindows="); pw.println(mInteractingWindows);
        pw.print("  mStatusBarWindowState=");
        pw.println(windowStateToString(mStatusBarWindowState));
        pw.print("  mStatusBarMode=");
        pw.println(BarTransitions.modeToString(mStatusBarMode));
        pw.print("  mDozing="); pw.println(mDozing);
        pw.print("  mZenMode=");
        pw.println(Settings.Global.zenModeToString(mZenMode));
        pw.print("  mUseHeadsUp=");
        pw.println(mUseHeadsUp);
        pw.print("  interrupting package: ");
        pw.println(hunStateToString(mHeadsUpNotificationView.getEntry()));
        dumpBarTransitions(pw, "mStatusBarView", mStatusBarView.getBarTransitions());
        if (mNavigationBarView != null) {
            pw.print("  mNavigationBarWindowState=");
            pw.println(windowStateToString(mNavigationBarWindowState));
            pw.print("  mNavigationBarMode=");
            pw.println(BarTransitions.modeToString(mNavigationBarMode));
            dumpBarTransitions(pw, "mNavigationBarView", mNavigationBarView.getBarTransitions());
        }

        pw.print("  mNavigationBarView=");
        if (mNavigationBarView == null) {
            pw.println("null");
        } else {
            mNavigationBarView.dump(fd, pw, args);
        }

        pw.print("  mMediaSessionManager=");
        pw.println(mMediaSessionManager);
        pw.print("  mMediaNotificationKey=");
        pw.println(mMediaNotificationKey);
        pw.print("  mMediaController=");
        pw.print(mMediaController);
        if (mMediaController != null) {
            pw.print(" state=" + mMediaController.getPlaybackState());
        }
        pw.println();
        pw.print("  mMediaMetadata=");
        pw.print(mMediaMetadata);
        if (mMediaMetadata != null) {
            pw.print(" title=" + mMediaMetadata.getText(MediaMetadata.METADATA_KEY_TITLE));
        }
        pw.println();

        pw.println("  Panels: ");
        if (mNotificationPanel != null) {
            pw.println("    mNotificationPanel=" +
                mNotificationPanel + " params=" + mNotificationPanel.getLayoutParams().debug(""));
            pw.print  ("      ");
            mNotificationPanel.dump(fd, pw, args);
        }

        DozeLog.dump(pw);

        if (DUMPTRUCK) {
            synchronized (mNotificationData) {
                mNotificationData.dump(pw, "  ");
            }

            int N = mStatusIcons.getChildCount();
            pw.println("  system icons: " + N);
            for (int i=0; i<N; i++) {
                StatusBarIconView ic = (StatusBarIconView) mStatusIcons.getChildAt(i);
                pw.println("    [" + i + "] icon=" + ic);
            }

            if (false) {
                pw.println("see the logcat for a dump of the views we have created.");
                // must happen on ui thread
                mHandler.post(new Runnable() {
                        public void run() {
                            mStatusBarView.getLocationOnScreen(mAbsPos);
                            Log.d(TAG, "mStatusBarView: ----- (" + mAbsPos[0] + "," + mAbsPos[1]
                                    + ") " + mStatusBarView.getWidth() + "x"
                                    + getStatusBarHeight());
                            mStatusBarView.debug();
                        }
                    });
            }
        }

        if (DEBUG_GESTURES) {
            pw.print("  status bar gestures: ");
            mGestureRec.dump(fd, pw, args);
        }

        if (mNetworkController != null) {
            mNetworkController.dump(fd, pw, args);
        }
        if (mBluetoothController != null) {
            mBluetoothController.dump(fd, pw, args);
        }
        if (mCastController != null) {
            mCastController.dump(fd, pw, args);
        }
        if (mUserSwitcherController != null) {
            mUserSwitcherController.dump(fd, pw, args);
        }
        if (mBatteryController != null) {
            mBatteryController.dump(fd, pw, args);
        }
        if (mNextAlarmController != null) {
            mNextAlarmController.dump(fd, pw, args);
        }
        if (mSecurityController != null) {
            mSecurityController.dump(fd, pw, args);
        }
        pw.println("SharedPreferences:");
        for (Map.Entry<String, ?> entry : mContext.getSharedPreferences(mContext.getPackageName(),
                Context.MODE_PRIVATE).getAll().entrySet()) {
            pw.print("  "); pw.print(entry.getKey()); pw.print("="); pw.println(entry.getValue());
        }
    }

    private String hunStateToString(Entry entry) {
        if (entry == null) return "null";
        if (entry.notification == null) return "corrupt";
        return entry.notification.getPackageName();
    }

    private static void dumpBarTransitions(PrintWriter pw, String var, BarTransitions transitions) {
        pw.print("  "); pw.print(var); pw.print(".BarTransitions.mMode=");
        pw.println(BarTransitions.modeToString(transitions.getMode()));
    }

    @Override
    public void createAndAddWindows() {
        addStatusBarWindow();

        // listen for USER_SETUP_COMPLETE setting (per-user)
        resetUserSetupObserver();

        // receive broadcasts
        IntentFilter filter = new IntentFilter();
        filter.addAction(Intent.ACTION_CLOSE_SYSTEM_DIALOGS);
        filter.addAction(Intent.ACTION_SCREEN_OFF);
        filter.addAction(Intent.ACTION_SCREEN_ON);
        filter.addAction(Intent.ACTION_KEYGUARD_WALLPAPER_CHANGED);
        if (DEBUG_MEDIA_FAKE_ARTWORK) {
            filter.addAction("fake_artwork");
        }
        filter.addAction(ACTION_DEMO);
        mContext.registerReceiver(mBroadcastReceiver, filter);

        // receive broadcasts for packages
        IntentFilter packageFilter = new IntentFilter();
        packageFilter.addAction(Intent.ACTION_PACKAGE_ADDED);
        packageFilter.addAction(Intent.ACTION_PACKAGE_CHANGED);
        packageFilter.addAction(Intent.ACTION_PACKAGE_FULLY_REMOVED);
        packageFilter.addAction(Intent.ACTION_PACKAGE_REMOVED);
        packageFilter.addDataScheme("package");
        mContext.registerReceiver(mPackageBroadcastReceiver, packageFilter);
    }

    private void addStatusBarWindow() {
        makeStatusBarView();
        mStatusBarWindow.addContent(mStatusBarWindowContent);
        mStatusBarWindowManager = new StatusBarWindowManager(mContext, mKeyguardMonitor);
        mStatusBarWindowManager.setShowingMedia(mKeyguardShowingMedia);
        mStatusBarWindowManager.add(mStatusBarWindow, getStatusBarHeight());
    }

    static final float saturate(float a) {
        return a < 0f ? 0f : (a > 1f ? 1f : a);
    }

    @Override
    public void updateExpandedViewPos(int thingy) {
        if (SPEW) Log.v(TAG, "updateExpandedViewPos");

        // on larger devices, the notification panel is propped open a bit
        mNotificationPanel.setMinimumHeight(
                (int)(mNotificationPanelMinHeightFrac * mCurrentDisplaySize.y));

        FrameLayout.LayoutParams lp = (FrameLayout.LayoutParams) mNotificationPanel.getLayoutParams();
        lp.gravity = mNotificationPanelGravity;
        mNotificationPanel.setLayoutParams(lp);

        updateCarrierLabelVisibility(false);
    }

    // called by makeStatusbar and also by PhoneStatusBarView
    void updateDisplaySize() {
        mDisplay.getMetrics(mDisplayMetrics);
        mDisplay.getSize(mCurrentDisplaySize);
        if (DEBUG_GESTURES) {
            mGestureRec.tag("display",
                    String.format("%dx%d", mDisplayMetrics.widthPixels, mDisplayMetrics.heightPixels));
        }
    }

    float getDisplayDensity() {
        return mDisplayMetrics.density;
    }

    public void startActivityDismissingKeyguard(final Intent intent, boolean onlyProvisioned,
            final boolean dismissShade) {
        if (onlyProvisioned && !isDeviceProvisioned()) return;

        final boolean afterKeyguardGone = PreviewInflater.wouldLaunchResolverActivity(
                mContext, intent, mCurrentUserId);
        final boolean keyguardShowing = mStatusBarKeyguardViewManager.isShowing();
        dismissKeyguardThenExecute(new OnDismissAction() {
            @Override
            public boolean onDismiss() {
                AsyncTask.execute(new Runnable() {
                    public void run() {
                        try {
                            if (keyguardShowing && !afterKeyguardGone) {
                                ActivityManagerNative.getDefault()
                                        .keyguardWaitingForActivityDrawn();
                            }
                            intent.setFlags(
                                    Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
                            mContext.startActivityAsUser(
                                    intent, new UserHandle(UserHandle.USER_CURRENT));
                            overrideActivityPendingAppTransition(
                                    keyguardShowing && !afterKeyguardGone);
                        } catch (RemoteException e) {
                        }
                    }
                });
                if (dismissShade) {
                    animateCollapsePanels(
                            CommandQueue.FLAG_EXCLUDE_RECENTS_PANEL, true /* force */);
                }
                return true;
            }
        }, afterKeyguardGone);
    }

    private BroadcastReceiver mBroadcastReceiver = new BroadcastReceiver() {
        public void onReceive(Context context, Intent intent) {
            if (DEBUG) Log.v(TAG, "onReceive: " + intent);
            String action = intent.getAction();
            if (Intent.ACTION_CLOSE_SYSTEM_DIALOGS.equals(action)) {
                if (isCurrentProfile(getSendingUserId())) {
                    int flags = CommandQueue.FLAG_EXCLUDE_NONE;
                    String reason = intent.getStringExtra("reason");
                    if (reason != null && reason.equals(SYSTEM_DIALOG_REASON_RECENT_APPS)) {
                        flags |= CommandQueue.FLAG_EXCLUDE_RECENTS_PANEL;
                    }
                    animateCollapsePanels(flags);
                }
            }
            else if (Intent.ACTION_SCREEN_OFF.equals(action)) {
                mScreenOn = false;
                notifyNavigationBarScreenOn(false);
                notifyHeadsUpScreenOn(false);
                finishBarAnimations();
                resetUserExpandedStates();
            }
            else if (Intent.ACTION_SCREEN_ON.equals(action)) {
                mScreenOn = true;
                notifyNavigationBarScreenOn(true);
            }
            else if (ACTION_DEMO.equals(action)) {
                Bundle bundle = intent.getExtras();
                if (bundle != null) {
                    String command = bundle.getString("command", "").trim().toLowerCase();
                    if (command.length() > 0) {
                        try {
                            dispatchDemoCommand(command, bundle);
                        } catch (Throwable t) {
                            Log.w(TAG, "Error running demo command, intent=" + intent, t);
                        }
                    }
                }
            } else if ("fake_artwork".equals(action)) {
                if (DEBUG_MEDIA_FAKE_ARTWORK) {
                    updateMediaMetaData(true);
                }
            } else if (Intent.ACTION_KEYGUARD_WALLPAPER_CHANGED.equals(action)) {
                WallpaperManager wm = (WallpaperManager) mContext.getSystemService(
                        Context.WALLPAPER_SERVICE);
                mKeyguardWallpaper = wm.getKeyguardBitmap();
                updateMediaMetaData(true);
            }
        }
    };

    private BroadcastReceiver mPackageBroadcastReceiver = new BroadcastReceiver() {
        public void onReceive(Context context, Intent intent) {
            if (DEBUG) Log.v(TAG, "onReceive: " + intent);
            String action = intent.getAction();
            if (Intent.ACTION_PACKAGE_ADDED.equals(action) ||
                    Intent.ACTION_PACKAGE_CHANGED.equals(action) ||
                    Intent.ACTION_PACKAGE_FULLY_REMOVED.equals(action) ||
                    Intent.ACTION_PACKAGE_REMOVED.equals(action)) {
                updateCustomRecentsLongPressHandler(true);
            }
        }
    };
    private void resetUserExpandedStates() {
        ArrayList<Entry> activeNotifications = mNotificationData.getActiveNotifications();
        final int notificationCount = activeNotifications.size();
        for (int i = 0; i < notificationCount; i++) {
            NotificationData.Entry entry = activeNotifications.get(i);
            if (entry.row != null) {
                entry.row.resetUserExpansion();
            }
        }
    }

    @Override
    protected void dismissKeyguardThenExecute(final OnDismissAction action,
            boolean afterKeyguardGone) {
        if (mStatusBarKeyguardViewManager.isShowing()) {
            mStatusBarKeyguardViewManager.dismissWithAction(action, afterKeyguardGone);
        } else {
            action.onDismiss();
        }
    }

    // SystemUIService notifies SystemBars of configuration changes, which then calls down here
    @Override
    protected void onConfigurationChanged(Configuration newConfig) {
        super.onConfigurationChanged(newConfig); // calls refreshLayout

        if (DEBUG) {
            Log.v(TAG, "configuration changed: " + mContext.getResources().getConfiguration());
        }
        updateDisplaySize(); // populates mDisplayMetrics

        updateResources(newConfig);
        updateClockSize();
        repositionNavigationBar();
        updateExpandedViewPos(EXPANDED_LEAVE_ALONE);
        updateShowSearchHoldoff();
        updateRowStates();
        mScreenPinningRequest.onConfigurationChanged();
    }

    @Override
    public void userSwitched(int newUserId) {
        super.userSwitched(newUserId);
        if (MULTIUSER_DEBUG) mNotificationPanelDebugText.setText("USER " + newUserId);
        animateCollapsePanels();
        updatePublicMode(); 
        updateNotifications();
        resetUserSetupObserver();
        setControllerUsers();

        WallpaperManager wm = (WallpaperManager)
                mContext.getSystemService(Context.WALLPAPER_SERVICE);
        wm.forgetLoadedKeyguardWallpaper();
        mKeyguardWallpaper = wm.getKeyguardBitmap();
        updateMediaMetaData(true);

        if (mNavigationBarView != null) {
            mNavigationBarView.updateSettings();
        }
    }

    private void setControllerUsers() {
        if (mZenModeController != null) {
            mZenModeController.setUserId(mCurrentUserId);
        }
        if (mBatteryController != null) {
            mBatteryController.setUserId(mCurrentUserId);
        }
    }

    private void resetUserSetupObserver() {
        mContext.getContentResolver().unregisterContentObserver(mUserSetupObserver);
        mUserSetupObserver.onChange(false);
        mContext.getContentResolver().registerContentObserver(
                Settings.Secure.getUriFor(Settings.Secure.USER_SETUP_COMPLETE), true,
                mUserSetupObserver,
                mCurrentUserId);
    }

    private void setHeadsUpVisibility(boolean vis) {
        if (!ENABLE_HEADS_UP) return;
        if (DEBUG) Log.v(TAG, (vis ? "showing" : "hiding") + " heads up window");
        EventLog.writeEvent(EventLogTags.SYSUI_HEADS_UP_STATUS,
                vis ? mHeadsUpNotificationView.getKey() : "",
                vis ? 1 : 0);
        mHeadsUpNotificationView.setVisibility(vis ? View.VISIBLE : View.GONE);
    }

    public void onHeadsUpDismissed() {
        mHeadsUpNotificationView.dismiss();
    }

    private static void copyNotifications(ArrayList<Pair<String, StatusBarNotification>> dest,
            NotificationData source) {
        int N = source.size();
        for (int i = 0; i < N; i++) {
            NotificationData.Entry entry = source.get(i);
            dest.add(Pair.create(entry.key, entry.notification));
        }
    }

    private void recreateStatusBar() {
        mRecreating = true;

        instantCollapseNotificationPanel();

        if (mNetworkController != null) {
            mNetworkController.removeAllSignalClusters();
        }

        removeHeadsUpView();

        mStatusBarWindow.removeContent(mStatusBarWindowContent);
        mStatusBarWindow.clearDisappearingChildren();

        // extract icons from the soon-to-be recreated viewgroup.
        int nIcons = mStatusIcons != null ? mStatusIcons.getChildCount() : 0;
        ArrayList<StatusBarIcon> icons = new ArrayList<StatusBarIcon>(nIcons);
        ArrayList<String> iconSlots = new ArrayList<String>(nIcons);
        RankingMap rankingMap = mNotificationData.getRankingMap();
        for (int i = 0; i < nIcons; i++) {
            StatusBarIconView iconView = (StatusBarIconView) mStatusIcons.getChildAt(i);
            icons.add(iconView.getStatusBarIcon());
            iconSlots.add(iconView.getStatusBarSlot());
        }

        removeAllViews(mStatusBarWindowContent);

        // extract notifications.
        int nNotifs = mNotificationData.size();
        ArrayList<Pair<String, StatusBarNotification>> notifications =
                new ArrayList<Pair<String, StatusBarNotification>>(nNotifs);
        copyNotifications(notifications, mNotificationData);
        mNotificationData.clear();

        // Halts the old ticker. A new ticker is created in makeStatusBarView() so
        // this MUST happen before makeStatusBarView();
        haltTicker();

        // Stop the command queue until the new status bar container settles and has a layout pass
        mCommandQueue.pause();

        if (mCustomTileListenerService != null) {
            try {
                mCustomTileListenerService.unregisterAsSystemService();
            } catch (RemoteException e) {
                Log.e(TAG, "Unable to unregister custom tile listener", e);
            }
        }

        mQSPanel.getHost().setCustomTileListenerService(null);

        makeStatusBarView();
        repositionNavigationBar();
        addHeadsUpView();
        if (mNavigationBarView != null) {
            mNavigationBarView.updateResources(getNavbarThemedResources());
        }

        // recreate StatusBarIconViews.
        for (int i = 0; i < nIcons; i++) {
            StatusBarIcon icon = icons.get(i);
            String slot = iconSlots.get(i);
            addIcon(slot, i, i, icon);
        }

        // recreate notifications.
        for (int i = 0; i < nNotifs; i++) {
            Pair<String, StatusBarNotification> notifData = notifications.get(i);
            addNotificationViews(createNotificationViews(notifData.second), rankingMap);
        }
        mNotificationData.filterAndSort();

        setAreThereNotifications();
        mNotificationPanel.setShadeEmpty(!hasActiveNotifications());

        mStatusBarWindow.addContent(mStatusBarWindowContent);

        updateExpandedViewPos(EXPANDED_LEAVE_ALONE);
        checkBarModes();

        mStatusBarWindow.requestLayout();
        mStatusBarWindow.getViewTreeObserver().addOnGlobalLayoutListener(
                new ViewTreeObserver.OnGlobalLayoutListener() {
                    @Override
                    public void onGlobalLayout() {
                        mStatusBarWindow.getViewTreeObserver().removeOnGlobalLayoutListener(this);
                        mCommandQueue.resume();
                        mRecreating = false;
                    }
                });
        // restart the keyguard so it picks up the newly created ScrimController
        startKeyguard();

        // if the keyguard was showing while this change occurred we'll need to do some extra work
        if (mState == StatusBarState.KEYGUARD) {
            // this will make sure the keyguard is showing
            showKeyguard();
            // The following views need to be invisible if the keyguard is showing
            // These views were hidden but re-inflating the status bar changed them back to visible
            mClockView.setVisibility(View.INVISIBLE);
            mNotificationIconArea.setVisibility(View.INVISIBLE);
            mSystemIconArea.setVisibility(View.INVISIBLE);
        }
    }

    private void removeAllViews(ViewGroup parent) {
        int N = parent.getChildCount();
        for (int i = 0; i < N; i++) {
            View child = parent.getChildAt(i);
            if (child instanceof ViewGroup) {
                removeAllViews((ViewGroup) child);
            }
        }
        parent.removeAllViews();
    }

    /**
     * Reload some of our resources when the configuration changes.
     *
     * We don't reload everything when the configuration changes -- we probably
     * should, but getting that smooth is tough.  Someday we'll fix that.  In the
     * meantime, just update the things that we know change.
     */
    void updateResources(Configuration newConfig) {
        // detect theme change.
        ThemeConfig newTheme = newConfig != null ? newConfig.themeConfig : null;
        final boolean updateStatusBar = shouldUpdateStatusbar(mCurrentTheme, newTheme);
        if (newTheme != null) mCurrentTheme = (ThemeConfig) newTheme.clone();
        if (updateStatusBar) {
            mContext.recreateTheme();
            recreateStatusBar();
        } else {
            loadDimens();
        }

        // Update the quick setting tiles
        if (mQSPanel != null) {
            mQSPanel.updateResources();
        }

        loadDimens();
        mLinearOutSlowIn = AnimationUtils.loadInterpolator(
                mContext, android.R.interpolator.linear_out_slow_in);

        if (mNotificationPanel != null) {
            mNotificationPanel.updateResources();
        }
        if (mHeadsUpNotificationView != null) {
            mHeadsUpNotificationView.updateResources();
        }
        if (mBrightnessMirrorController != null) {
            mBrightnessMirrorController.updateResources();
        }

        if (mNavigationBarView != null)  {
            mNavigationBarView.updateResources(getNavbarThemedResources());
            updateSearchPanel();
        }
    }

    /**
     * Determines if we need to recreate the status bar due to a theme change.  We currently
     * check if the overlay for the status bar, fonts, or icons, or forced update count have
     * changed.
     *
     * @param oldTheme
     * @param newTheme
     * @return True if we should recreate the status bar
     */
    private boolean shouldUpdateStatusbar(ThemeConfig oldTheme, ThemeConfig newTheme) {
        // no newTheme, so no need to update status bar
        if (newTheme == null) return false;

        final String overlay = newTheme.getOverlayForStatusBar();
        final String icons = newTheme.getIconPackPkgName();
        final String fonts = newTheme.getFontPkgName();

        return oldTheme == null ||
                (overlay != null && !overlay.equals(oldTheme.getOverlayForStatusBar()) ||
                (fonts != null && !fonts.equals(oldTheme.getFontPkgName())) ||
                (icons != null && !icons.equals(oldTheme.getIconPackPkgName())) ||
                newTheme.getLastThemeChangeRequestType() == RequestType.THEME_UPDATED);
    }

    private void updateClockSize() {
        if (mStatusBarView == null) return;
        TextView clock = (TextView) mStatusBarView.findViewById(R.id.clock);
        if (clock != null) {
            FontSizeUtils.updateFontSize(clock, R.dimen.status_bar_clock_size);
        }
    }
    protected void loadDimens() {
        final Resources res = mContext.getResources();

        mNaturalBarHeight = res.getDimensionPixelSize(
                com.android.internal.R.dimen.status_bar_height);

        int newIconSize = res.getDimensionPixelSize(
            com.android.internal.R.dimen.status_bar_icon_size);
        int newIconHPadding = res.getDimensionPixelSize(
            R.dimen.status_bar_icon_padding);

        if (newIconHPadding != mIconHPadding || newIconSize != mIconSize) {
//            Log.d(TAG, "size=" + newIconSize + " padding=" + newIconHPadding);
            mIconHPadding = newIconHPadding;
            mIconSize = newIconSize;
            //reloadAllNotificationIcons(); // reload the tray
        }

        mEdgeBorder = res.getDimensionPixelSize(R.dimen.status_bar_edge_ignore);

        mNotificationPanelGravity = res.getInteger(R.integer.notification_panel_layout_gravity);
        if (mNotificationPanelGravity <= 0) {
            mNotificationPanelGravity = Gravity.START | Gravity.TOP;
        }

        mCarrierLabelHeight = res.getDimensionPixelSize(R.dimen.carrier_label_height);
        mStatusBarHeaderHeight = res.getDimensionPixelSize(R.dimen.status_bar_header_height);
        mNotificationPanelMinHeightFrac = res.getFraction(R.dimen.notification_panel_min_height_frac, 1, 1);
        if (mNotificationPanelMinHeightFrac < 0f || mNotificationPanelMinHeightFrac > 1f) {
            mNotificationPanelMinHeightFrac = 0f;
        }

        mHeadsUpNotificationDecay = res.getInteger(R.integer.heads_up_notification_decay);
        mRowMinHeight =  res.getDimensionPixelSize(R.dimen.notification_min_height);
        mRowMaxHeight =  res.getDimensionPixelSize(R.dimen.notification_max_height);

        mKeyguardMaxNotificationCount = res.getInteger(R.integer.keyguard_max_notification_count);

        if (DEBUG) Log.v(TAG, "updateResources");
    }

    // Visibility reporting

    @Override
    protected void handleVisibleToUserChanged(boolean visibleToUser) {
        if (visibleToUser) {
            super.handleVisibleToUserChanged(visibleToUser);
            startNotificationLogging();
        } else {
            stopNotificationLogging();
            super.handleVisibleToUserChanged(visibleToUser);
        }
    }

    private void stopNotificationLogging() {
        // Report all notifications as invisible and turn down the
        // reporter.
        if (!mCurrentlyVisibleNotifications.isEmpty()) {
            logNotificationVisibilityChanges(
                    Collections.<String>emptyList(), mCurrentlyVisibleNotifications);
            mCurrentlyVisibleNotifications.clear();
        }
        mHandler.removeCallbacks(mVisibilityReporter);
        mStackScroller.setChildLocationsChangedListener(null);
    }

    private void startNotificationLogging() {
        mStackScroller.setChildLocationsChangedListener(mNotificationLocationsChangedListener);
        // Some transitions like mVisibleToUser=false -> mVisibleToUser=true don't
        // cause the scroller to emit child location events. Hence generate
        // one ourselves to guarantee that we're reporting visible
        // notifications.
        // (Note that in cases where the scroller does emit events, this
        // additional event doesn't break anything.)
        mNotificationLocationsChangedListener.onChildLocationsChanged(mStackScroller);
    }

    private void logNotificationVisibilityChanges(
            Collection<String> newlyVisible, Collection<String> noLongerVisible) {
        if (newlyVisible.isEmpty() && noLongerVisible.isEmpty()) {
            return;
        }
        String[] newlyVisibleAr = newlyVisible.toArray(new String[newlyVisible.size()]);
        String[] noLongerVisibleAr = noLongerVisible.toArray(new String[noLongerVisible.size()]);
        try {
            mBarService.onNotificationVisibilityChanged(newlyVisibleAr, noLongerVisibleAr);
        } catch (RemoteException e) {
            // Ignore.
        }
    }

    // State logging

    private void logStateToEventlog() {
        boolean isShowing = mStatusBarKeyguardViewManager.isShowing();
        boolean isOccluded = mStatusBarKeyguardViewManager.isOccluded();
        boolean isBouncerShowing = mStatusBarKeyguardViewManager.isBouncerShowing();
        boolean isSecure = mUnlockMethodCache.isMethodSecure();
        boolean isCurrentlyInsecure = mUnlockMethodCache.isCurrentlyInsecure();
        int stateFingerprint = getLoggingFingerprint(mState,
                isShowing,
                isOccluded,
                isBouncerShowing,
                isSecure,
                isCurrentlyInsecure);
        if (stateFingerprint != mLastLoggedStateFingerprint) {
            EventLogTags.writeSysuiStatusBarState(mState,
                    isShowing ? 1 : 0,
                    isOccluded ? 1 : 0,
                    isBouncerShowing ? 1 : 0,
                    isSecure ? 1 : 0,
                    isCurrentlyInsecure ? 1 : 0);
            mLastLoggedStateFingerprint = stateFingerprint;
        }
    }

    /**
     * Returns a fingerprint of fields logged to eventlog
     */
    private static int getLoggingFingerprint(int statusBarState, boolean keyguardShowing,
            boolean keyguardOccluded, boolean bouncerShowing, boolean secure,
            boolean currentlyInsecure) {
        // Reserve 8 bits for statusBarState. We'll never go higher than
        // that, right? Riiiight.
        return (statusBarState & 0xFF)
                | ((keyguardShowing   ? 1 : 0) <<  8)
                | ((keyguardOccluded  ? 1 : 0) <<  9)
                | ((bouncerShowing    ? 1 : 0) << 10)
                | ((secure            ? 1 : 0) << 11)
                | ((currentlyInsecure ? 1 : 0) << 12);
    }

    //
    // tracing
    //

    void postStartTracing() {
        mHandler.postDelayed(mStartTracing, 3000);
    }

    void vibrate() {
        android.os.Vibrator vib = (android.os.Vibrator)mContext.getSystemService(
                Context.VIBRATOR_SERVICE);
        vib.vibrate(250, VIBRATION_ATTRIBUTES);
    }

    Runnable mStartTracing = new Runnable() {
        public void run() {
            vibrate();
            SystemClock.sleep(250);
            Log.d(TAG, "startTracing");
            android.os.Debug.startMethodTracing("/data/statusbar-traces/trace");
            mHandler.postDelayed(mStopTracing, 10000);
        }
    };

    Runnable mStopTracing = new Runnable() {
        public void run() {
            android.os.Debug.stopMethodTracing();
            Log.d(TAG, "stopTracing");
            vibrate();
        }
    };

    @Override
    protected void haltTicker() {
        if (mTickerEnabled) {
            mTicker.halt();
        }
    }

    @Override
    protected boolean shouldDisableNavbarGestures() {
        return !isDeviceProvisioned()
                || mExpandedVisible
                || (mNavigationBarView != null && mNavigationBarView.isInEditMode())
                || (mDisabled & StatusBarManager.DISABLE_SEARCH) != 0;
    }

    public void postStartSettingsActivity(final Intent intent, int delay) {
        mHandler.postDelayed(new Runnable() {
            @Override
            public void run() {
                handleStartSettingsActivity(intent, true /*onlyProvisioned*/);
            }
        }, delay);
    }

    private void handleStartSettingsActivity(Intent intent, boolean onlyProvisioned) {
        startActivityDismissingKeyguard(intent, onlyProvisioned, true /* dismissShade */);
    }

    private static class FastColorDrawable extends Drawable {
        private final int mColor;

        public FastColorDrawable(int color) {
            mColor = 0xff000000 | color;
        }

        @Override
        public void draw(Canvas canvas) {
            canvas.drawColor(mColor, PorterDuff.Mode.SRC);
        }

        @Override
        public void setAlpha(int alpha) {
        }

        @Override
        public void setColorFilter(ColorFilter cf) {
        }

        @Override
        public int getOpacity() {
            return PixelFormat.OPAQUE;
        }

        @Override
        public void setBounds(int left, int top, int right, int bottom) {
        }

        @Override
        public void setBounds(Rect bounds) {
        }
    }

    @Override
    public void destroy() {
        super.destroy();
        if (mStatusBarWindow != null) {
            mWindowManager.removeViewImmediate(mStatusBarWindow);
            mStatusBarWindow = null;
        }
        if (mNavigationBarView != null) {
            mWindowManager.removeViewImmediate(mNavigationBarView);
            mNavigationBarView = null;
        }
        if (mHandlerThread != null) {
            mHandlerThread.quitSafely();
            mHandlerThread = null;
        }
        mContext.unregisterReceiver(mBroadcastReceiver);
    }

    private boolean mDemoModeAllowed;
    private boolean mDemoMode;
    private DemoStatusIcons mDemoStatusIcons;

    @Override
    public void dispatchDemoCommand(String command, Bundle args) {
        if (!mDemoModeAllowed) {
            mDemoModeAllowed = Settings.Global.getInt(mContext.getContentResolver(),
                    "sysui_demo_allowed", 0) != 0;
        }
        if (!mDemoModeAllowed) return;
        if (command.equals(COMMAND_ENTER)) {
            mDemoMode = true;
        } else if (command.equals(COMMAND_EXIT)) {
            mDemoMode = false;
            checkBarModes();
        } else if (!mDemoMode) {
            // automatically enter demo mode on first demo command
            dispatchDemoCommand(COMMAND_ENTER, new Bundle());
        }
        boolean modeChange = command.equals(COMMAND_ENTER) || command.equals(COMMAND_EXIT);
        if ((modeChange || command.equals(COMMAND_VOLUME)) && mVolumeComponent != null) {
            mVolumeComponent.dispatchDemoCommand(command, args);
        }
        if (modeChange || command.equals(COMMAND_CLOCK)) {
            dispatchDemoCommandToView(command, args, R.id.clock);
        }
        if (modeChange || command.equals(COMMAND_BATTERY)) {
            dispatchDemoCommandToView(command, args, R.id.battery);
        }
        if (modeChange || command.equals(COMMAND_STATUS)) {
            if (mDemoStatusIcons == null) {
                mDemoStatusIcons = new DemoStatusIcons(mStatusIcons, mIconSize);
            }
            mDemoStatusIcons.dispatchDemoCommand(command, args);
        }
        if (mNetworkController != null && (modeChange || command.equals(COMMAND_NETWORK))) {
            mNetworkController.dispatchDemoCommand(command, args);
        }
        if (modeChange || command.equals(COMMAND_NOTIFICATIONS)) {
            View notifications = mStatusBarView == null ? null
                    : mStatusBarView.findViewById(R.id.notification_icon_area);
            if (notifications != null) {
                String visible = args.getString("visible");
                int vis = mDemoMode && "false".equals(visible) ? View.INVISIBLE : View.VISIBLE;
                notifications.setVisibility(vis);
            }
        }
        if (command.equals(COMMAND_BARS)) {
            String mode = args.getString("mode");
            int barMode = "opaque".equals(mode) ? MODE_OPAQUE :
                    "translucent".equals(mode) ? MODE_TRANSLUCENT :
                    "semi-transparent".equals(mode) ? MODE_SEMI_TRANSPARENT :
                    "transparent".equals(mode) ? MODE_TRANSPARENT :
                    "warning".equals(mode) ? MODE_WARNING :
                    -1;
            if (barMode != -1) {
                boolean animate = true;
                if (mStatusBarView != null) {
                    mStatusBarView.getBarTransitions().transitionTo(barMode, animate);
                }
                if (mNavigationBarView != null) {
                    mNavigationBarView.getBarTransitions().transitionTo(barMode, animate);
                }
            }
        }
    }

    private void dispatchDemoCommandToView(String command, Bundle args, int id) {
        if (mStatusBarView == null) return;
        View v = mStatusBarView.findViewById(id);
        if (v instanceof DemoMode) {
            ((DemoMode)v).dispatchDemoCommand(command, args);
        }
    }

    /**
     * @return The {@link StatusBarState} the status bar is in.
     */
    public int getBarState() {
        return mState;
    }

    public void showKeyguard() {
        if (mLaunchTransitionFadingAway) {
            mNotificationPanel.animate().cancel();
            mNotificationPanel.setAlpha(1f);
            runLaunchTransitionEndRunnable();
            mLaunchTransitionFadingAway = false;
        }
        mHandler.removeMessages(MSG_LAUNCH_TRANSITION_TIMEOUT);
        setBarState(StatusBarState.KEYGUARD);
        updateKeyguardState(false /* goingToFullShade */, false /* fromShadeLocked */);
        if (!mScreenOnFromKeyguard) {

            // If the screen is off already, we need to disable touch events because these might
            // collapse the panel after we expanded it, and thus we would end up with a blank
            // Keyguard.
            mNotificationPanel.setTouchDisabled(true);
        }
        instantExpandNotificationsPanel();
        mLeaveOpenOnKeyguardHide = false;
        if (mDraggedDownRow != null) {
            mDraggedDownRow.setUserLocked(false);
            mDraggedDownRow.notifyHeightChanged();
            mDraggedDownRow = null;
        }
    }

    public boolean isCollapsing() {
        return mNotificationPanel.isCollapsing();
    }

    public void addPostCollapseAction(Runnable r) {
        mPostCollapseRunnables.add(r);
    }

    public boolean isInLaunchTransition() {
        return mNotificationPanel.isLaunchTransitionRunning()
                || mNotificationPanel.isLaunchTransitionFinished();
    }

    /**
     * Fades the content of the keyguard away after the launch transition is done.
     *
     * @param beforeFading the runnable to be run when the circle is fully expanded and the fading
     *                     starts
     * @param endRunnable the runnable to be run when the transition is done
     */
    public void fadeKeyguardAfterLaunchTransition(final Runnable beforeFading,
            Runnable endRunnable) {
        mHandler.removeMessages(MSG_LAUNCH_TRANSITION_TIMEOUT);
        mLaunchTransitionEndRunnable = endRunnable;
        Runnable hideRunnable = new Runnable() {
            @Override
            public void run() {
                mLaunchTransitionFadingAway = true;
                if (beforeFading != null) {
                    beforeFading.run();
                }
                mNotificationPanel.setAlpha(1);
                mNotificationPanel.animate()
                        .alpha(0)
                        .setStartDelay(FADE_KEYGUARD_START_DELAY)
                        .setDuration(FADE_KEYGUARD_DURATION)
                        .withLayer()
                        .withEndAction(new Runnable() {
                            @Override
                            public void run() {
                                mNotificationPanel.setAlpha(1);
                                runLaunchTransitionEndRunnable();
                                mLaunchTransitionFadingAway = false;
                            }
                        });
            }
        };
        if (mNotificationPanel.isLaunchTransitionRunning()) {
            mNotificationPanel.setLaunchTransitionEndRunnable(hideRunnable);
        } else {
            hideRunnable.run();
        }
    }

    /**
     * Starts the timeout when we try to start the affordances on Keyguard. We usually rely that
     * Keyguard goes away via fadeKeyguardAfterLaunchTransition, however, that might not happen
     * because the launched app crashed or something else went wrong.
     */
    public void startLaunchTransitionTimeout() {
        if (mVisualizerEnabled) {
            mBackdrop.setVisible(false);
        }
        mHandler.sendEmptyMessageDelayed(MSG_LAUNCH_TRANSITION_TIMEOUT,
                LAUNCH_TRANSITION_TIMEOUT_MS);
    }

    private void onLaunchTransitionTimeout() {
        Log.w(TAG, "Launch transition: Timeout!");
        mNotificationPanel.resetViews();
    }

    private void runLaunchTransitionEndRunnable() {
        if (mLaunchTransitionEndRunnable != null) {
            Runnable r = mLaunchTransitionEndRunnable;

            // mLaunchTransitionEndRunnable might call showKeyguard, which would execute it again,
            // which would lead to infinite recursion. Protect against it.
            mLaunchTransitionEndRunnable = null;
            r.run();
        }
    }

    /**
     * @return true if we would like to stay in the shade, false if it should go away entirely
     */
    public boolean hideKeyguard() {
        boolean staying = mLeaveOpenOnKeyguardHide;
        setBarState(StatusBarState.SHADE);
        if (mLeaveOpenOnKeyguardHide) {
            mLeaveOpenOnKeyguardHide = false;
            mNotificationPanel.animateToFullShade(calculateGoingToFullShadeDelay());
            if (mDraggedDownRow != null) {
                mDraggedDownRow.setUserLocked(false);
                mDraggedDownRow = null;
            }
        } else {
            instantCollapseNotificationPanel();
        }
        updateKeyguardState(staying, false /* fromShadeLocked */);

        // Keyguard state has changed, but QS is not listening anymore. Make sure to update the tile
        // visibilities so next time we open the panel we know the correct height already.
        if (mQSPanel != null) {
            mQSPanel.refreshAllTiles();
        }
        mHandler.removeMessages(MSG_LAUNCH_TRANSITION_TIMEOUT);
        return staying;
    }

    boolean isSecure() {
        return mStatusBarKeyguardViewManager != null && mStatusBarKeyguardViewManager.isSecure();
    }

    public long calculateGoingToFullShadeDelay() {
        return mKeyguardFadingAwayDelay + mKeyguardFadingAwayDuration;
    }

    /**
     * Notifies the status bar the Keyguard is fading away with the specified timings.
     *
     * @param delay the animation delay in miliseconds
     * @param fadeoutDuration the duration of the exit animation, in milliseconds
     */
    public void setKeyguardFadingAway(long delay, long fadeoutDuration) {
        if (mVisualizerEnabled) {
            mBackdrop.setVisible(false);
        }
        mKeyguardFadingAway = true;
        mKeyguardFadingAwayDelay = delay;
        mKeyguardFadingAwayDuration = fadeoutDuration;
        mWaitingForKeyguardExit = false;
        disable(mDisabledUnmodified, true /* animate */);
    }

    public boolean isKeyguardFadingAway() {
        return mKeyguardFadingAway;
    }

    /**
     * Notifies that the Keyguard fading away animation is done.
     */
    public void finishKeyguardFadingAway() {
        mKeyguardFadingAway = false;
    }

    private void updatePublicMode() {
        setLockscreenPublicMode(mStatusBarKeyguardViewManager.isShowing()
                && mStatusBarKeyguardViewManager.isSecure(mCurrentUserId));
    }

    private void updateKeyguardState(boolean goingToFullShade, boolean fromShadeLocked) {
        if (mState == StatusBarState.KEYGUARD) {
            mKeyguardIndicationController.setVisible(true);
            mNotificationPanel.resetViews();
            mKeyguardUserSwitcher.setKeyguard(true, fromShadeLocked);
        } else {
            mKeyguardIndicationController.setVisible(false);
            mKeyguardUserSwitcher.setKeyguard(false,
                    goingToFullShade || mState == StatusBarState.SHADE_LOCKED || fromShadeLocked);
        }
        if (mState == StatusBarState.KEYGUARD || mState == StatusBarState.SHADE_LOCKED) {
            mScrimController.setKeyguardShowing(true);
        } else {
            mScrimController.setKeyguardShowing(false);
        }
        mNotificationPanel.setBarState(mState, mKeyguardFadingAway, goingToFullShade);
        updateDozingState();
        updatePublicMode();
        updateStackScrollerState(goingToFullShade);
        updateNotifications();
        checkBarModes();
        updateCarrierLabelVisibility(false);
        updateMediaMetaData(false);
        mKeyguardMonitor.notifyKeyguardState(mStatusBarKeyguardViewManager.isShowing(),
                mStatusBarKeyguardViewManager.isSecure());
    }

    private void updateDozingState() {
        if (mState != StatusBarState.KEYGUARD && !mNotificationPanel.isDozing()) {
            return;
        }
        boolean animate = !mDozing && mDozeScrimController.isPulsing();
        mNotificationPanel.setDozing(mDozing, animate);
        mStackScroller.setDark(mDozing, animate, mScreenOnTouchLocation);
        mScrimController.setDozing(mDozing);
        mDozeScrimController.setDozing(mDozing, animate);
    }

    public void updateStackScrollerState(boolean goingToFullShade) {
        if (mStackScroller == null) return;
        boolean onKeyguard = mState == StatusBarState.KEYGUARD;
        mStackScroller.setHideSensitive(isLockscreenPublicMode(), goingToFullShade);
        mStackScroller.setDimmed(onKeyguard, false /* animate */);
        mStackScroller.setExpandingEnabled(!onKeyguard);
        ActivatableNotificationView activatedChild = mStackScroller.getActivatedChild();
        mStackScroller.setActivatedChild(null);
        if (activatedChild != null) {
            activatedChild.makeInactive(false /* animate */);
        }
    }

    public void userActivity() {
        if (mState == StatusBarState.KEYGUARD) {
            mKeyguardViewMediatorCallback.userActivity();
        }
    }

    public boolean interceptMediaKey(KeyEvent event) {
        return mState == StatusBarState.KEYGUARD
                && mStatusBarKeyguardViewManager.interceptMediaKey(event);
    }

    public boolean onMenuPressed() {
        return mState == StatusBarState.KEYGUARD && mStatusBarKeyguardViewManager.onMenuPressed();
    }

    public boolean onBackPressed() {
        if (mStatusBarKeyguardViewManager.onBackPressed()) {
            return true;
        }
        if (mNotificationPanel.isQsExpanded()) {
            if (mNotificationPanel.isQsDetailShowing()) {
                mNotificationPanel.closeQsDetail();
            } else {
                mNotificationPanel.animateCloseQs();
            }
            return true;
        }
        if (mState != StatusBarState.KEYGUARD && mState != StatusBarState.SHADE_LOCKED) {
            animateCollapsePanels();
            return true;
        }
        return false;
    }

    public boolean onSpacePressed() {
        if (mScreenOn != null && mScreenOn
                && (mState == StatusBarState.KEYGUARD || mState == StatusBarState.SHADE_LOCKED)) {
            animateCollapsePanels(
                    CommandQueue.FLAG_EXCLUDE_RECENTS_PANEL /* flags */, true /* force */);
            return true;
        }
        return false;
    }

    private void showBouncer() {
        if (!mRecreating &&
                (mState == StatusBarState.KEYGUARD || mState == StatusBarState.SHADE_LOCKED)) {
            mWaitingForKeyguardExit = mStatusBarKeyguardViewManager.isShowing();
            mStatusBarKeyguardViewManager.dismiss();
        }
    }

    private void instantExpandNotificationsPanel() {

        // Make our window larger and the panel expanded.
        makeExpandedVisible(true);
        mNotificationPanel.instantExpand();
    }

    private void instantCollapseNotificationPanel() {
        mNotificationPanel.instantCollapse();
    }

    @Override
    public void onActivated(ActivatableNotificationView view) {
        setVisualizerAnimating(true);
        EventLogTags.writeSysuiLockscreenGesture(
                EventLogConstants.SYSUI_LOCKSCREEN_GESTURE_TAP_NOTIFICATION_ACTIVATE,
                0 /* lengthDp - N/A */, 0 /* velocityDp - N/A */);
        mKeyguardIndicationController.showTransientIndication(R.string.notification_tap_again);
        ActivatableNotificationView previousView = mStackScroller.getActivatedChild();
        if (previousView != null) {
            previousView.makeInactive(true /* animate */);
        }
        mStackScroller.setActivatedChild(view);
    }

    /**
     * @param state The {@link StatusBarState} to set.
     */
    public void setBarState(int state) {
        // If we're visible and switched to SHADE_LOCKED (the user dragged
        // down on the lockscreen), clear notification LED, vibration,
        // ringing.
        // Other transitions are covered in handleVisibleToUserChanged().
        if (state != mState && mVisible && state == StatusBarState.SHADE_LOCKED) {
            try {
                mBarService.clearNotificationEffects();
            } catch (RemoteException e) {
                // Ignore.
            }
        }
        mState = state;
        mStatusBarWindowManager.setStatusBarState(state);
        logStateToEventlog();
    }

    @Override
    public void onActivationReset(ActivatableNotificationView view) {
        if (view == mStackScroller.getActivatedChild()) {
            mKeyguardIndicationController.hideTransientIndication();
            mStackScroller.setActivatedChild(null);
            setVisualizerAnimating(false);
        }
    }

    public void onTrackingStarted() {
        runPostCollapseRunnables();
    }

    public void onClosingFinished() {
        runPostCollapseRunnables();
    }

    public void onUnlockHintStarted() {
        mKeyguardIndicationController.showTransientIndication(R.string.keyguard_unlock);
    }

    public void onHintFinished() {
        // Delay the reset a bit so the user can read the text.
        mKeyguardIndicationController.hideTransientIndicationDelayed(HINT_RESET_DELAY_MS);
    }

    public void onCameraHintStarted(String hint) {
        mKeyguardIndicationController.showTransientIndication(hint);
    }

    public void onPhoneHintStarted(String hint) {
        mKeyguardIndicationController.showTransientIndication(hint);
    }

    public void onFingerprintHintStarted() {
        mKeyguardIndicationController.showTransientIndication(R.string.fingerprint_try_again_hint);
    }

    public void onTrackingStopped(boolean expand) {
        if (mState == StatusBarState.KEYGUARD || mState == StatusBarState.SHADE_LOCKED) {
            if (!expand && !mUnlockMethodCache.isCurrentlyInsecure()) {
                showBouncer();
            }
        }
    }

    @Override
    protected int getMaxKeyguardNotifications() {
        return mKeyguardMaxNotificationCount;
    }

    public NavigationBarView getNavigationBarView() {
        return mNavigationBarView;
    }

    // ---------------------- DragDownHelper.OnDragDownListener ------------------------------------

    @Override
    public boolean onDraggedDown(View startingChild, int dragLengthY) {
        if (hasActiveNotifications()) {
            EventLogTags.writeSysuiLockscreenGesture(
                    EventLogConstants.SYSUI_LOCKSCREEN_GESTURE_SWIPE_DOWN_FULL_SHADE,
                    (int) (dragLengthY / mDisplayMetrics.density),
                    0 /* velocityDp - N/A */);

            // We have notifications, go to locked shade.
            goToLockedShade(startingChild);
            return true;
        } else {

            // No notifications - abort gesture.
            return false;
        }
    }

    @Override
    public void onDragDownReset() {
        mStackScroller.setDimmed(true /* dimmed */, true /* animated */);
    }

    @Override
    public void onThresholdReached() {
        mStackScroller.setDimmed(false /* dimmed */, true /* animate */);
    }

    @Override
    public void onTouchSlopExceeded() {
        mStackScroller.removeLongPressCallback();
    }

    @Override
    public void setEmptyDragAmount(float amount) {
        mNotificationPanel.setEmptyDragAmount(amount);
    }

    /**
     * If secure with redaction: Show bouncer, go to unlocked shade.
     *
     * <p>If secure without redaction or no security: Go to {@link StatusBarState#SHADE_LOCKED}.</p>
     *
     * @param expandView The view to expand after going to the shade.
     */
    public void goToLockedShade(View expandView) {
        ExpandableNotificationRow row = null;
        if (expandView instanceof ExpandableNotificationRow) {
            row = (ExpandableNotificationRow) expandView;
            row.setUserExpanded(true);
        }
        boolean fullShadeNeedsBouncer = !userAllowsPrivateNotificationsInPublic(mCurrentUserId)
                || !mShowLockscreenNotifications;
        if (isLockscreenPublicMode() && fullShadeNeedsBouncer) {
            mLeaveOpenOnKeyguardHide = true;
            showBouncer();
            mDraggedDownRow = row;
        } else {
            if (mVisualizerEnabled) {
                mBackdrop.setVisible(false);
            }
            mNotificationPanel.animateToFullShade(0 /* delay */);
            setBarState(StatusBarState.SHADE_LOCKED);
            updateKeyguardState(false /* goingToFullShade */, false /* fromShadeLocked */);
            if (row != null) {
                row.setUserLocked(false);
            }
        }
    }

    /**
     * Goes back to the keyguard after hanging around in {@link StatusBarState#SHADE_LOCKED}.
     */
    public void goToKeyguard() {
        if (mState == StatusBarState.SHADE_LOCKED) {
            mStackScroller.onGoToKeyguard();
            setBarState(StatusBarState.KEYGUARD);
            updateKeyguardState(false /* goingToFullShade */, true /* fromShadeLocked*/);
            if (mVisualizerEnabled) {
                mBackdrop.setVisible(true);
            }
        }
    }

    /**
     * @return a ViewGroup that spans the entire panel which contains the quick settings
     */
    public ViewGroup getQuickSettingsOverlayParent() {
        return mNotificationPanel;
    }

    public long getKeyguardFadingAwayDelay() {
        return mKeyguardFadingAwayDelay;
    }

    public long getKeyguardFadingAwayDuration() {
        return mKeyguardFadingAwayDuration;
    }

    public LinearLayout getSystemIcons() {
        return mSystemIcons;
    }

    public LinearLayout getSystemIconArea() {
        return mSystemIconArea;
    }

    @Override
    public void setBouncerShowing(boolean bouncerShowing) {
        super.setBouncerShowing(bouncerShowing);
        disable(mDisabledUnmodified, true /* animate */);
    }

    void onScreenTurnedOff() {
        if (mVisualizerEnabled) {
            mBackdrop.setVisible(false);
        }
        mScreenOnFromKeyguard = false;
        mScreenOnComingFromTouch = false;
        mScreenOnTouchLocation = null;
        mStackScroller.setAnimationsEnabled(false);
        updateVisibleToUser();
    }

    public void onScreenTurnedOn() {
        mScreenOnFromKeyguard = true;
        mStackScroller.setAnimationsEnabled(true);
        mNotificationPanel.onScreenTurnedOn();
        mNotificationPanel.setTouchDisabled(false);
        updateVisibleToUser();
        if (mVisualizerEnabled) {
            mBackdrop.setVisible(true);
        }
    }

    /**
     * This handles long-press of both back and recents.  They are
     * handled together to capture them both being long-pressed
     * at the same time to exit screen pinning (lock task).
     *
     * When accessibility mode is on, only a long-press from recents
     * is required to exit.
     *
     * In all other circumstances we try to pass through long-press events
     * for Back, so that apps can still use it.  Which can be from two things.
     * 1) Not currently in screen pinning (lock task).
     * 2) Back is long-pressed without recents.
     */
    private void handleLongPressBackRecents(View v) {
        try {
            boolean sendBackLongPress = false;
            boolean hijackRecentsLongPress = false;
            IActivityManager activityManager = ActivityManagerNative.getDefault();
            boolean isAccessiblityEnabled = mAccessibilityManager.isEnabled();
            if (activityManager.isInLockTaskMode() && !isAccessiblityEnabled) {
                long time = System.currentTimeMillis();
                // If we recently long-pressed the other button then they were
                // long-pressed 'together'
                if ((time - mLastLockToAppLongPress) < LOCK_TO_APP_GESTURE_TOLERENCE) {
                    activityManager.stopLockTaskModeOnCurrent();
                    // When exiting refresh disabled flags.
                    mNavigationBarView.setDisabledFlags(mDisabled, true);
                } else if ((NavbarEditor.NAVBAR_BACK.equals(v.getTag()))
                        && !mNavigationBarView.getRecentsButton().isPressed()) {
                    // If we aren't pressing recents right now then they presses
                    // won't be together, so send the standard long-press action.
                    sendBackLongPress = true;
                } else if (NavbarEditor.NAVBAR_RECENT.equals(v.getTag()) && !activityManager.isInLockTaskMode()) {
                    hijackRecentsLongPress = true;
                }
                mLastLockToAppLongPress = time;
            } else {
                // If this is back still need to handle sending the long-press event.
                if (NavbarEditor.NAVBAR_BACK.equals(v.getTag())) {
                    sendBackLongPress = true;
                } else if (NavbarEditor.NAVBAR_RECENT.equals(v.getTag()) && !activityManager.isInLockTaskMode()) {
                    hijackRecentsLongPress = true;
                } else if (isAccessiblityEnabled && activityManager.isInLockTaskMode()) {
                    // When in accessibility mode a long press that is recents (not back)
                    // should stop lock task.
                    activityManager.stopLockTaskModeOnCurrent();
                    // When exiting refresh disabled flags.
                    mNavigationBarView.setDisabledFlags(mDisabled, true);
                }
            }
            if (sendBackLongPress) {
                KeyButtonView keyButtonView = (KeyButtonView) v;
                keyButtonView.sendEvent(KeyEvent.ACTION_DOWN, KeyEvent.FLAG_LONG_PRESS);
                keyButtonView.sendAccessibilityEvent(AccessibilityEvent.TYPE_VIEW_LONG_CLICKED);
            }

            if (hijackRecentsLongPress) {
                // If there is a user-selected, registered handler for the
                // recents long press, start the Intent.  Otherwise,
                // perform the default action, which is last app switching.

                // Copy it so the value doesn't change between now and when the activity is started.
                ComponentName customRecentsLongPressHandler = mCustomRecentsLongPressHandler;
                if (customRecentsLongPressHandler != null) {
                    startCustomRecentsLongPressActivity(customRecentsLongPressHandler);
                } else {
                    ActionUtils.switchToLastApp(mContext, mCurrentUserId);
                }
            }
        } catch (RemoteException e) {
            Log.d(TAG, "Unable to reach activity manager", e);
        }
    }

    protected View.OnTouchListener mRecentsPreloadOnTouchListener = new View.OnTouchListener() {
        @Override
        public boolean onTouch(View v, MotionEvent event) {
            int action = event.getAction() & MotionEvent.ACTION_MASK;

            // Handle Document switcher
            // Additional optimization when we have software system buttons - start loading the recent
            // tasks on touch down
            if (action == MotionEvent.ACTION_DOWN) {
                preloadRecents();
            } else if (action == MotionEvent.ACTION_CANCEL) {
                cancelPreloadingRecents();
            } else if (action == MotionEvent.ACTION_UP) {
                if (!v.isPressed()) {
                    cancelPreloadingRecents();
                }
            }

            // Handle custom recents long press
            if (action == MotionEvent.ACTION_CANCEL ||
                action == MotionEvent.ACTION_UP) {
                cleanupCustomRecentsLongPressHandler();
            }
            return false;
        }
    };

    /**
     * If a custom Recents Long Press activity was dispatched, then the certain
     * handlers need to be cleaned up after the event ends.
     */
    private void cleanupCustomRecentsLongPressHandler() {
        if (mCustomRecentsLongPressed) {
            mNavigationBarView.setSlippery(false);
            mNavigationBarView.enableSearchBar();
        }
        mCustomRecentsLongPressed = false;
    }

    /**
     * An ACTION_RECENTS_LONG_PRESS intent was received, and a custom handler is
     * set and points to a valid app.  Start this activity.
     */
    private void startCustomRecentsLongPressActivity(ComponentName customComponentName) {
        Intent intent = new Intent(Intent.ACTION_RECENTS_LONG_PRESS);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);

        // Include the package name of the app currently in the foreground
        IActivityManager am = ActivityManagerNative.getDefault();
        List<ActivityManager.RecentTaskInfo> recentTasks = null;
        try {
            recentTasks = am.getRecentTasks(
                    1, ActivityManager.RECENT_WITH_EXCLUDED, UserHandle.myUserId());
        } catch (RemoteException e) {
            Log.e(TAG, "Cannot get recent tasks", e);
        }
        if (recentTasks != null && recentTasks.size() > 0) {
            String pkgName = recentTasks.get(0).baseIntent.getComponent().getPackageName();
            intent.putExtra(Intent.EXTRA_CURRENT_PACKAGE_NAME, pkgName);
        }

        intent.setComponent(customComponentName);
        try {
            // Allow the touch event to continue into the new activity.
            mNavigationBarView.setSlippery(true);
            mNavigationBarView.disableSearchBar();
            mCustomRecentsLongPressed = true;

            mContext.startActivityAsUser(intent, new UserHandle(UserHandle.USER_CURRENT));

        } catch (ActivityNotFoundException e) {
            Log.e(TAG, "Cannot start activity", e);

            // If the activity failed to launch, clean up
            cleanupCustomRecentsLongPressHandler();
        }
    }

    /**
     * Get component name for the recent long press setting. Null means default switch to last app.
     *
     * Note: every time packages changed, the setting must be re-evaluated.  This is to check that the
     * component was not uninstalled or disabled.
     */
    private void updateCustomRecentsLongPressHandler(boolean scanPackages) {
        // scanPackages should be true when the PhoneStatusBar is starting for
        // the first time, and when any package activity occurred.
        if (scanPackages) {
            updateCustomRecentsLongPressCandidates();
        }

        String componentString = Settings.Secure.getString(mContext.getContentResolver(),
                Settings.Secure.RECENTS_LONG_PRESS_ACTIVITY);
        if (componentString == null) {
            mCustomRecentsLongPressHandler = null;
            return;
        }

        ComponentName customComponentName = ComponentName.unflattenFromString(componentString);
        synchronized (mCustomRecentsLongPressHandlerCandidates) {
            for (ComponentName candidate : mCustomRecentsLongPressHandlerCandidates) {
                if (candidate.equals(customComponentName)) {
                    // Found match
                    mCustomRecentsLongPressHandler = customComponentName;

                    return;
                }
            }

            // Did not find match, probably because the selected application has
            // now been uninstalled for some reason. Since user-selected app is
            // still saved inside Settings, PhoneStatusBar should fall back to
            // the default for now.  (We will update this either when the
            // package is reinstalled or when the user selects another Setting.)
            mCustomRecentsLongPressHandler = null;
        }
    }

    /**
     * Updates the cache of Recents Long Press applications.
     *
     * These applications must:
     * - handle the Intent.ACTION_RECENTS_LONG_PRESS (which is permissions protected); and
     * - not be disabled by the user or the system.
     *
     * More than one handler can be a candidate.  When the action is invoked,
     * the user setting (stored in Settings.Secure) is consulted.
     */
    private void updateCustomRecentsLongPressCandidates() {
        synchronized (mCustomRecentsLongPressHandlerCandidates) {
            mCustomRecentsLongPressHandlerCandidates.clear();

            PackageManager pm = mContext.getPackageManager();
            Intent intent = new Intent(Intent.ACTION_RECENTS_LONG_PRESS);

            // Search for all apps that can handle ACTION_RECENTS_LONG_PRESS
            List<ResolveInfo> activities = pm.queryIntentActivities(intent,
                    PackageManager.MATCH_DEFAULT_ONLY);
            for (ResolveInfo info : activities) {
                // Only cache packages that are not disabled
                int packageState = mContext.getPackageManager().getApplicationEnabledSetting(
                        info.activityInfo.packageName);

                if (packageState != PackageManager.COMPONENT_ENABLED_STATE_DISABLED &&
                    packageState != PackageManager.COMPONENT_ENABLED_STATE_DISABLED_USER) {

                    mCustomRecentsLongPressHandlerCandidates.add(
                        new ComponentName(info.activityInfo.packageName, info.activityInfo.name));
                }

            }
        }
    }

    private ActivityManager.RunningTaskInfo getLastTask(final ActivityManager am) {
        final String defaultHomePackage = resolveCurrentLauncherPackage();
        List<ActivityManager.RunningTaskInfo> tasks = am.getRunningTasks(5);

        for (int i = 1; i < tasks.size(); i++) {
            String packageName = tasks.get(i).topActivity.getPackageName();
            if (!packageName.equals(defaultHomePackage)
                    && !packageName.equals(mContext.getPackageName())) {
                return tasks.get(i);
            }
        }

        return null;
    }

    private String resolveCurrentLauncherPackage() {
        final Intent launcherIntent = new Intent(Intent.ACTION_MAIN)
                .addCategory(Intent.CATEGORY_HOME);
        final PackageManager pm = mContext.getPackageManager();
        final ResolveInfo launcherInfo = pm.resolveActivity(launcherIntent, 0);
        return launcherInfo.activityInfo.packageName;
    }

    // Recents

    @Override
    protected void showRecents(boolean triggeredFromAltTab) {
        // Set the recents visibility flag
        mSystemUiVisibility |= View.RECENT_APPS_VISIBLE;
        notifyUiVisibilityChanged(mSystemUiVisibility);
        super.showRecents(triggeredFromAltTab);
    }

    @Override
    protected void hideRecents(boolean triggeredFromAltTab, boolean triggeredFromHomeKey) {
        // Unset the recents visibility flag
        mSystemUiVisibility &= ~View.RECENT_APPS_VISIBLE;
        notifyUiVisibilityChanged(mSystemUiVisibility);
        super.hideRecents(triggeredFromAltTab, triggeredFromHomeKey);
    }

    @Override
    protected void toggleRecents() {
        // Toggle the recents visibility flag
        mSystemUiVisibility ^= View.RECENT_APPS_VISIBLE;
        notifyUiVisibilityChanged(mSystemUiVisibility);
        super.toggleRecents();
    }

    @Override
    public void onVisibilityChanged(boolean visible) {
        // Update the recents visibility flag
        if (visible) {
            mSystemUiVisibility |= View.RECENT_APPS_VISIBLE;
        } else {
            mSystemUiVisibility &= ~View.RECENT_APPS_VISIBLE;
        }
        notifyUiVisibilityChanged(mSystemUiVisibility);
    }

    @Override
    public void showScreenPinningRequest() {
        if (mKeyguardMonitor.isShowing()) {
            // Don't allow apps to trigger this from keyguard.
            return;
        }
        // Show screen pinning request, since this comes from an app, show 'no thanks', button.
        showScreenPinningRequest(true);
    }

    public void showScreenPinningRequest(boolean allowCancel) {
        mScreenPinningRequest.showPrompt(allowCancel);
    }

    public boolean hasActiveNotifications() {
        return !mNotificationData.getActiveNotifications().isEmpty();
    }

    public void wakeUpIfDozing(long time, MotionEvent event) {
        if (mDozing && mDozeScrimController.isPulsing()) {
            PowerManager pm = (PowerManager) mContext.getSystemService(Context.POWER_SERVICE);
            pm.wakeUp(time);
            mScreenOnComingFromTouch = true;
            mScreenOnTouchLocation = new PointF(event.getX(), event.getY());
            mNotificationPanel.setTouchDisabled(false);
        }
    }

    private final class ShadeUpdates {
        private final ArraySet<String> mVisibleNotifications = new ArraySet<String>();
        private final ArraySet<String> mNewVisibleNotifications = new ArraySet<String>();

        public void check() {
            mNewVisibleNotifications.clear();
            ArrayList<Entry> activeNotifications = mNotificationData.getActiveNotifications();
            for (int i = 0; i < activeNotifications.size(); i++) {
                final Entry entry = activeNotifications.get(i);
                final boolean visible = entry.row != null
                        && entry.row.getVisibility() == View.VISIBLE;
                if (visible) {
                    mNewVisibleNotifications.add(entry.key + entry.notification.getPostTime());
                }
            }
            final boolean updates = !mVisibleNotifications.containsAll(mNewVisibleNotifications);
            mVisibleNotifications.clear();
            mVisibleNotifications.addAll(mNewVisibleNotifications);

            // We have new notifications
            if (updates && mDozeServiceHost != null) {
                mDozeServiceHost.fireNewNotifications();
            }
        }
    }

    private final class DozeServiceHost implements DozeHost {
        // Amount of time to allow to update the time shown on the screen before releasing
        // the wakelock.  This timeout is design to compensate for the fact that we don't
        // currently have a way to know when time display contents have actually been
        // refreshed once we've finished rendering a new frame.
        private static final long PROCESSING_TIME = 500;

        private final ArrayList<Callback> mCallbacks = new ArrayList<Callback>();
        private final H mHandler = new H();
        // Keeps the last reported state by fireNotificationLight.
        private boolean mNotificationLightOn;

        @Override
        public String toString() {
            return "PSB.DozeServiceHost[mCallbacks=" + mCallbacks.size() + "]";
        }

        public void firePowerSaveChanged(boolean active) {
            for (Callback callback : mCallbacks) {
                callback.onPowerSaveChanged(active);
            }
        }

        public void fireBuzzBeepBlinked() {
            for (Callback callback : mCallbacks) {
                callback.onBuzzBeepBlinked();
            }
        }

        public void fireNotificationLight(boolean on) {
            mNotificationLightOn = on;
            for (Callback callback : mCallbacks) {
                callback.onNotificationLight(on);
            }
        }

        public void fireNewNotifications() {
            for (Callback callback : mCallbacks) {
                callback.onNewNotifications();
            }
        }

        @Override
        public void addCallback(@NonNull Callback callback) {
            mCallbacks.add(callback);
        }

        @Override
        public void removeCallback(@NonNull Callback callback) {
            mCallbacks.remove(callback);
        }

        @Override
        public void startDozing(@NonNull Runnable ready) {
            mHandler.obtainMessage(H.MSG_START_DOZING, ready).sendToTarget();
        }

        @Override
        public void pulseWhileDozing(@NonNull PulseCallback callback, int reason) {
            mHandler.obtainMessage(H.MSG_PULSE_WHILE_DOZING, reason, 0, callback).sendToTarget();
        }

        @Override
        public void stopDozing() {
            mHandler.obtainMessage(H.MSG_STOP_DOZING).sendToTarget();
        }

        @Override
        public boolean isPowerSaveActive() {
            return mBatteryController != null && mBatteryController.isPowerSave();
        }

        @Override
        public boolean isNotificationLightOn() {
            return mNotificationLightOn;
        }

        private void handleStartDozing(@NonNull Runnable ready) {
            if (!mDozing) {
                mDozing = true;
                DozeLog.traceDozing(mContext, mDozing);
                updateDozingState();
            }
            ready.run();
        }

        private void handlePulseWhileDozing(@NonNull PulseCallback callback, int reason) {
            mDozeScrimController.pulse(callback, reason);
        }

        private void handleStopDozing() {
            if (mDozing) {
                mDozing = false;
                DozeLog.traceDozing(mContext, mDozing);
                updateDozingState();
            }
        }

        private final class H extends Handler {
            private static final int MSG_START_DOZING = 1;
            private static final int MSG_PULSE_WHILE_DOZING = 2;
            private static final int MSG_STOP_DOZING = 3;

            @Override
            public void handleMessage(Message msg) {
                switch (msg.what) {
                    case MSG_START_DOZING:
                        handleStartDozing((Runnable) msg.obj);
                        break;
                    case MSG_PULSE_WHILE_DOZING:
                        handlePulseWhileDozing((PulseCallback) msg.obj, msg.arg1);
                        break;
                    case MSG_STOP_DOZING:
                        handleStopDozing();
                        break;
                }
            }
        }
    }

    private final Runnable mSetVisualizerNotTouching = new Runnable() {
        @Override
        public void run() {
            mBackdrop.setTouching(false);
        }
    };

    public void setVisualizerAnimating(boolean animating) {
        if (mVisualizerEnabled && (mState != StatusBarState.SHADE)) {
            mBackdrop.setAnimating(animating);
        }
    }

    public void setVisualizerTouching(boolean touching) {
        if (mVisualizerEnabled && (mState != StatusBarState.SHADE)) {
            mHandler.removeCallbacks(mSetVisualizerNotTouching);
            if (touching) {
                mBackdrop.setTouching(true);
            } else {
                mHandler.postDelayed(mSetVisualizerNotTouching, 300);
            }
        }
    }
}


File: packages/SystemUI/src/com/android/systemui/statusbar/phone/StatusBarHeaderView.java
/*
 * Copyright (C) 2014 The Android Open Source Project
 * Copyright (C) 2014 The CyanogenMod Project
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
 * limitations under the License
 */

package com.android.systemui.statusbar.phone;

import android.app.ActivityManager;
import android.app.ActivityManagerNative;
import android.app.AlarmManager;
import android.app.IUserSwitchObserver;
import android.app.PendingIntent;
import android.content.ContentUris;
import android.content.ContentResolver;
import android.content.Context;
import android.content.Intent;
import android.content.res.Configuration;
import android.content.res.Resources;
import android.database.ContentObserver;
import android.graphics.Outline;
import android.graphics.Rect;
import android.graphics.drawable.Animatable;
import android.graphics.drawable.Drawable;
import android.net.Uri;
import android.os.Handler;
import android.os.IRemoteCallback;
import android.os.RemoteException;
import android.os.UserHandle;
import android.provider.AlarmClock;
import android.provider.CalendarContract;
import android.provider.Settings;
import android.telephony.TelephonyManager;
import android.util.AttributeSet;
import android.util.Log;
import android.util.MathUtils;
import android.util.TypedValue;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewOutlineProvider;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.RelativeLayout;
import android.widget.Switch;
import android.widget.TextView;

import com.android.keyguard.KeyguardStatusView;
import com.android.systemui.BatteryMeterView;
import com.android.systemui.BatteryLevelTextView;
import com.android.systemui.FontSizeUtils;
import com.android.systemui.R;
import com.android.systemui.cm.UserContentObserver;
import com.android.systemui.qs.QSPanel;
import com.android.systemui.qs.QSTile;
import com.android.systemui.statusbar.policy.BatteryController;
import com.android.systemui.statusbar.policy.NextAlarmController;
import com.android.systemui.statusbar.policy.UserInfoController;
import com.android.systemui.statusbar.policy.WeatherController;
import com.android.systemui.statusbar.policy.WeatherControllerImpl;

/**
 * The view to manage the header area in the expanded status bar.
 */
public class StatusBarHeaderView extends RelativeLayout implements View.OnClickListener,
        NextAlarmController.NextAlarmChangeCallback, WeatherController.Callback {

    private boolean mExpanded;
    private boolean mListening;

    private ViewGroup mSystemIconsContainer;
    private ViewGroup mWeatherContainer;
    private View mSystemIconsSuperContainer;
    private View mDateGroup;
    private View mClock;
    private TextView mTime;
    private TextView mAmPm;
    private MultiUserSwitch mMultiUserSwitch;
    private ImageView mMultiUserAvatar;
    private TextView mDateCollapsed;
    private TextView mDateExpanded;
    private LinearLayout mSystemIcons;
    private View mSignalCluster;
    private View mSettingsButton;
    private View mQsDetailHeader;
    private TextView mQsDetailHeaderTitle;
    private Switch mQsDetailHeaderSwitch;
    private ImageView mQsDetailHeaderProgress;
    private TextView mEmergencyCallsOnly;
    private BatteryLevelTextView mBatteryLevel;
    private TextView mAlarmStatus;
    private TextView mWeatherLine1, mWeatherLine2;

    private boolean mShowEmergencyCallsOnly;
    private boolean mAlarmShowing;
    private AlarmManager.AlarmClockInfo mNextAlarm;

    private int mCollapsedHeight;
    private int mExpandedHeight;

    private int mMultiUserExpandedMargin;
    private int mMultiUserCollapsedMargin;

    private int mClockMarginBottomExpanded;
    private int mClockMarginBottomCollapsed;
    private int mMultiUserSwitchWidthCollapsed;
    private int mMultiUserSwitchWidthExpanded;

    private int mClockCollapsedSize;
    private int mClockExpandedSize;

    /**
     * In collapsed QS, the clock and avatar are scaled down a bit post-layout to allow for a nice
     * transition. These values determine that factor.
     */
    private float mClockCollapsedScaleFactor;
    private float mAvatarCollapsedScaleFactor;

    private ActivityStarter mActivityStarter;
    private BatteryController mBatteryController;
    private NextAlarmController mNextAlarmController;
    private WeatherController mWeatherController;
    private QSPanel mQSPanel;


    private final Rect mClipBounds = new Rect();

    private boolean mCaptureValues;
    private boolean mSignalClusterDetached;
    private final LayoutValues mCollapsedValues = new LayoutValues();
    private final LayoutValues mExpandedValues = new LayoutValues();
    private final LayoutValues mCurrentValues = new LayoutValues();

    private float mCurrentT;
    private boolean mShowingDetail;

    private SettingsObserver mSettingsObserver;
    private boolean mShowWeather;
    private boolean mShowBatteryTextExpanded;

    public StatusBarHeaderView(Context context, AttributeSet attrs) {
        super(context, attrs);
    }

    @Override
    protected void onFinishInflate() {
        super.onFinishInflate();
        mSystemIconsSuperContainer = findViewById(R.id.system_icons_super_container);
        mSystemIconsContainer = (ViewGroup) findViewById(R.id.system_icons_container);
        mSystemIconsSuperContainer.setOnClickListener(this);
        mDateGroup = findViewById(R.id.date_group);
        mDateGroup.setOnClickListener(this);
        mClock = findViewById(R.id.clock);
        mClock.setOnClickListener(this);
        mTime = (TextView) findViewById(R.id.time_view);
        mAmPm = (TextView) findViewById(R.id.am_pm_view);
        mMultiUserSwitch = (MultiUserSwitch) findViewById(R.id.multi_user_switch);
        mMultiUserAvatar = (ImageView) findViewById(R.id.multi_user_avatar);
        mDateCollapsed = (TextView) findViewById(R.id.date_collapsed);
        mDateExpanded = (TextView) findViewById(R.id.date_expanded);
        mSettingsButton = findViewById(R.id.settings_button);
        mSettingsButton.setOnClickListener(this);
        mQsDetailHeader = findViewById(R.id.qs_detail_header);
        mQsDetailHeader.setAlpha(0);
        mQsDetailHeaderTitle = (TextView) mQsDetailHeader.findViewById(android.R.id.title);
        mQsDetailHeaderSwitch = (Switch) mQsDetailHeader.findViewById(android.R.id.toggle);
        mQsDetailHeaderProgress = (ImageView) findViewById(R.id.qs_detail_header_progress);
        mEmergencyCallsOnly = (TextView) findViewById(R.id.header_emergency_calls_only);
        mBatteryLevel = (BatteryLevelTextView) findViewById(R.id.battery_level_text);
        mAlarmStatus = (TextView) findViewById(R.id.alarm_status);
        mAlarmStatus.setOnClickListener(this);
        mSignalCluster = findViewById(R.id.signal_cluster);
        mSystemIcons = (LinearLayout) findViewById(R.id.system_icons);
        mWeatherContainer = (LinearLayout) findViewById(R.id.weather_container);
        mWeatherContainer.setOnClickListener(this);
        mWeatherLine1 = (TextView) findViewById(R.id.weather_line_1);
        mWeatherLine2 = (TextView) findViewById(R.id.weather_line_2);
        mSettingsObserver = new SettingsObserver(new Handler());
        loadDimens();
        updateVisibilities();
        updateClockScale();
        updateAvatarScale();
        addOnLayoutChangeListener(new View.OnLayoutChangeListener() {
            @Override
            public void onLayoutChange(View v, int left, int top, int right,
                    int bottom, int oldLeft, int oldTop, int oldRight, int oldBottom) {
                if ((right - left) != (oldRight - oldLeft)) {
                    // width changed, update clipping
                    setClipping(getHeight());
                }
                boolean rtl = getLayoutDirection() == LAYOUT_DIRECTION_RTL;
                mTime.setPivotX(rtl ? mTime.getWidth() : 0);
                mTime.setPivotY(mTime.getBaseline());
                updateAmPmTranslation();
            }
        });
        setOutlineProvider(new ViewOutlineProvider() {
            @Override
            public void getOutline(View view, Outline outline) {
                outline.setRect(mClipBounds);
            }
        });
        requestCaptureValues();
    }

    @Override
    protected void onLayout(boolean changed, int l, int t, int r, int b) {
        super.onLayout(changed, l, t, r, b);
        if (mCaptureValues) {
            if (mExpanded) {
                captureLayoutValues(mExpandedValues);
            } else {
                captureLayoutValues(mCollapsedValues);
            }
            mCaptureValues = false;
            updateLayoutValues(mCurrentT);
        }
        mAlarmStatus.setX(mDateGroup.getLeft() + mDateCollapsed.getRight());
    }

    @Override
    protected void onConfigurationChanged(Configuration newConfig) {
        super.onConfigurationChanged(newConfig);
        FontSizeUtils.updateFontSize(mEmergencyCallsOnly,
                R.dimen.qs_emergency_calls_only_text_size);
        FontSizeUtils.updateFontSize(mDateCollapsed, R.dimen.qs_date_collapsed_size);
        FontSizeUtils.updateFontSize(mDateExpanded, R.dimen.qs_date_collapsed_size);
        FontSizeUtils.updateFontSize(mAlarmStatus, R.dimen.qs_date_collapsed_size);
        FontSizeUtils.updateFontSize(this, android.R.id.title, R.dimen.qs_detail_header_text_size);
        FontSizeUtils.updateFontSize(this, android.R.id.toggle, R.dimen.qs_detail_header_text_size);
        FontSizeUtils.updateFontSize(mAmPm, R.dimen.qs_time_collapsed_size);
        FontSizeUtils.updateFontSize(this, R.id.empty_time_view, R.dimen.qs_time_expanded_size);

        mEmergencyCallsOnly.setText(com.android.internal.R.string.emergency_calls_only);

        mClockCollapsedSize = getResources().getDimensionPixelSize(R.dimen.qs_time_collapsed_size);
        mClockExpandedSize = getResources().getDimensionPixelSize(R.dimen.qs_time_expanded_size);
        mClockCollapsedScaleFactor = (float) mClockCollapsedSize / (float) mClockExpandedSize;

        updateClockScale();
        updateClockCollapsedMargin();
    }

    private void updateClockCollapsedMargin() {
        Resources res = getResources();
        int padding = res.getDimensionPixelSize(R.dimen.clock_collapsed_bottom_margin);
        int largePadding = res.getDimensionPixelSize(
                R.dimen.clock_collapsed_bottom_margin_large_text);
        float largeFactor = (MathUtils.constrain(getResources().getConfiguration().fontScale, 1.0f,
                FontSizeUtils.LARGE_TEXT_SCALE) - 1f) / (FontSizeUtils.LARGE_TEXT_SCALE - 1f);
        mClockMarginBottomCollapsed = Math.round((1 - largeFactor) * padding + largeFactor * largePadding);
        requestLayout();
    }

    private void requestCaptureValues() {
        mCaptureValues = true;
        requestLayout();
    }

    private void loadDimens() {
        mCollapsedHeight = getResources().getDimensionPixelSize(R.dimen.status_bar_header_height);
        mExpandedHeight = getResources().getDimensionPixelSize(
                R.dimen.status_bar_header_height_expanded);
        mMultiUserExpandedMargin =
                getResources().getDimensionPixelSize(R.dimen.multi_user_switch_expanded_margin);
        mMultiUserCollapsedMargin =
                getResources().getDimensionPixelSize(R.dimen.multi_user_switch_collapsed_margin);
        mClockMarginBottomExpanded =
                getResources().getDimensionPixelSize(R.dimen.clock_expanded_bottom_margin);
        updateClockCollapsedMargin();
        mMultiUserSwitchWidthCollapsed =
                getResources().getDimensionPixelSize(R.dimen.multi_user_switch_width_collapsed);
        mMultiUserSwitchWidthExpanded =
                getResources().getDimensionPixelSize(R.dimen.multi_user_switch_width_expanded);
        mAvatarCollapsedScaleFactor =
                getResources().getDimensionPixelSize(R.dimen.multi_user_avatar_collapsed_size)
                / (float) mMultiUserAvatar.getLayoutParams().width;
        mClockCollapsedSize = getResources().getDimensionPixelSize(R.dimen.qs_time_collapsed_size);
        mClockExpandedSize = getResources().getDimensionPixelSize(R.dimen.qs_time_expanded_size);
        mClockCollapsedScaleFactor = (float) mClockCollapsedSize / (float) mClockExpandedSize;

    }

    public void setActivityStarter(ActivityStarter activityStarter) {
        mActivityStarter = activityStarter;
        if (mMultiUserSwitch != null) {
            mMultiUserSwitch.setActivityStarter(activityStarter);
        }
    }

    public void setBatteryController(BatteryController batteryController) {
        mBatteryController = batteryController;
        ((BatteryMeterView) findViewById(R.id.battery)).setBatteryController(batteryController);
        mBatteryLevel.setBatteryController(batteryController);
    }

    public void setNextAlarmController(NextAlarmController nextAlarmController) {
        mNextAlarmController = nextAlarmController;
    }

    public void setWeatherController(WeatherController weatherController) {
        mWeatherController = weatherController;
    }

    public int getCollapsedHeight() {
        return mCollapsedHeight;
    }

    public int getExpandedHeight() {
        return mExpandedHeight;
    }

    public void setListening(boolean listening) {
        if (listening == mListening) {
            return;
        }
        mListening = listening;
        updateListeners();
    }

    public void setExpanded(boolean expanded) {
        boolean changed = expanded != mExpanded;
        mExpanded = expanded;
        if (changed) {
            updateEverything();
        }
    }

    public void updateEverything() {
        updateHeights();
        updateVisibilities();
        updateSystemIconsLayoutParams();
        updateClickTargets();
        updateMultiUserSwitch();
        if (mQSPanel != null) {
            mQSPanel.setExpanded(mExpanded);
        }
        updateClockScale();
        updateAvatarScale();
        updateClockLp();
        requestCaptureValues();
    }

    private void updateHeights() {
        int height = mExpanded ? mExpandedHeight : mCollapsedHeight;
        ViewGroup.LayoutParams lp = getLayoutParams();
        if (lp.height != height) {
            lp.height = height;
            setLayoutParams(lp);
        }
    }

    private void updateVisibilities() {
        mDateCollapsed.setVisibility(mExpanded && mAlarmShowing ? View.VISIBLE : View.INVISIBLE);
        mDateExpanded.setVisibility(mExpanded && mAlarmShowing ? View.INVISIBLE : View.VISIBLE);
        mAlarmStatus.setVisibility(mExpanded && mAlarmShowing ? View.VISIBLE : View.INVISIBLE);
        mSettingsButton.setVisibility(mExpanded ? View.VISIBLE : View.INVISIBLE);
        mWeatherContainer.setVisibility(mExpanded && mShowWeather ? View.VISIBLE : View.GONE);
        mQsDetailHeader.setVisibility(mExpanded && mShowingDetail ? View.VISIBLE : View.INVISIBLE);
        if (mSignalCluster != null) {
            updateSignalClusterDetachment();
        }
        mEmergencyCallsOnly.setVisibility(mExpanded && mShowEmergencyCallsOnly ? VISIBLE : GONE);
        mBatteryLevel.setForceShown(mExpanded && mShowBatteryTextExpanded);
        mBatteryLevel.setVisibility(View.VISIBLE);
    }

    private void updateSignalClusterDetachment() {
        boolean detached = mExpanded;
        if (detached != mSignalClusterDetached) {
            if (detached) {
                getOverlay().add(mSignalCluster);
            } else {
                reattachSignalCluster();
            }
        }
        mSignalClusterDetached = detached;
    }

    private void reattachSignalCluster() {
        getOverlay().remove(mSignalCluster);
        mSystemIcons.addView(mSignalCluster, 1);
    }

    private void updateSystemIconsLayoutParams() {
        RelativeLayout.LayoutParams lp = (LayoutParams) mSystemIconsSuperContainer.getLayoutParams();
        int rule = mExpanded
                ? mSettingsButton.getId()
                : mMultiUserSwitch.getId();
        if (rule != lp.getRules()[RelativeLayout.START_OF]) {
            lp.addRule(RelativeLayout.START_OF, rule);
            mSystemIconsSuperContainer.setLayoutParams(lp);
        }
    }

    private void updateListeners() {
        if (mListening) {
            mSettingsObserver.observe();
            mNextAlarmController.addStateChangedCallback(this);
            mWeatherController.addCallback(this);
        } else {
            mNextAlarmController.removeStateChangedCallback(this);
            mWeatherController.removeCallback(this);
            mSettingsObserver.unobserve();
        }
    }

    private void updateAvatarScale() {
        if (mExpanded) {
            mMultiUserAvatar.setScaleX(1f);
            mMultiUserAvatar.setScaleY(1f);
        } else {
            mMultiUserAvatar.setScaleX(mAvatarCollapsedScaleFactor);
            mMultiUserAvatar.setScaleY(mAvatarCollapsedScaleFactor);
        }
    }

    private void updateClockScale() {
        mTime.setTextSize(TypedValue.COMPLEX_UNIT_PX, mExpanded
                ? mClockExpandedSize
                : mClockCollapsedSize);
        mTime.setScaleX(1f);
        mTime.setScaleY(1f);
        updateAmPmTranslation();
    }

    private void updateAmPmTranslation() {
        boolean rtl = getLayoutDirection() == LAYOUT_DIRECTION_RTL;
        mAmPm.setTranslationX((rtl ? 1 : -1) * mTime.getWidth() * (1 - mTime.getScaleX()));
    }

    @Override
    public void onNextAlarmChanged(AlarmManager.AlarmClockInfo nextAlarm) {
        mNextAlarm = nextAlarm;
        if (nextAlarm != null) {
            mAlarmStatus.setText(KeyguardStatusView.formatNextAlarm(getContext(), nextAlarm));
        }
        mAlarmShowing = nextAlarm != null;
        updateEverything();
        requestCaptureValues();
    }

    @Override
    public void onWeatherChanged(WeatherController.WeatherInfo info) {
        if (info.temp == null || info.condition == null) {
            mWeatherLine1.setText(null);
        } else {
            mWeatherLine1.setText(mContext.getString(
                    R.string.status_bar_expanded_header_weather_format,
                    info.temp,
                    info.condition));
        }
        mWeatherLine2.setText(info.city);
    }

    private void updateClickTargets() {
        mMultiUserSwitch.setClickable(mExpanded);
        mMultiUserSwitch.setFocusable(mExpanded);
        mSystemIconsSuperContainer.setClickable(mExpanded);
        mSystemIconsSuperContainer.setFocusable(mExpanded);
        mAlarmStatus.setClickable(mNextAlarm != null && mNextAlarm.getShowIntent() != null);
    }

    private void updateClockLp() {
        int marginBottom = mExpanded
                ? mClockMarginBottomExpanded
                : mClockMarginBottomCollapsed;
        LayoutParams lp = (LayoutParams) mDateGroup.getLayoutParams();
        if (marginBottom != lp.bottomMargin) {
            lp.bottomMargin = marginBottom;
            mDateGroup.setLayoutParams(lp);
        }
    }

    private void updateMultiUserSwitch() {
        int marginEnd;
        int width;
        if (mExpanded) {
            marginEnd = mMultiUserExpandedMargin;
            width = mMultiUserSwitchWidthExpanded;
        } else {
            marginEnd = mMultiUserCollapsedMargin;
            width = mMultiUserSwitchWidthCollapsed;
        }
        MarginLayoutParams lp = (MarginLayoutParams) mMultiUserSwitch.getLayoutParams();
        if (marginEnd != lp.getMarginEnd() || lp.width != width) {
            lp.setMarginEnd(marginEnd);
            lp.width = width;
            mMultiUserSwitch.setLayoutParams(lp);
        }
    }

    public void setExpansion(float t) {
        if (!mExpanded) {
            t = 0f;
        }
        mCurrentT = t;
        float height = mCollapsedHeight + t * (mExpandedHeight - mCollapsedHeight);
        if (height < mCollapsedHeight) {
            height = mCollapsedHeight;
        }
        if (height > mExpandedHeight) {
            height = mExpandedHeight;
        }
        setClipping(height);
        updateLayoutValues(t);
    }

    private void updateLayoutValues(float t) {
        if (mCaptureValues) {
            return;
        }
        mCurrentValues.interpoloate(mCollapsedValues, mExpandedValues, t);
        applyLayoutValues(mCurrentValues);
    }

    private void setClipping(float height) {
        mClipBounds.set(getPaddingLeft(), 0, getWidth() - getPaddingRight(), (int) height);
        setClipBounds(mClipBounds);
        invalidateOutline();
    }

    public void setUserInfoController(UserInfoController userInfoController) {
        userInfoController.addListener(new UserInfoController.OnUserInfoChangedListener() {
            @Override
            public void onUserInfoChanged(String name, Drawable picture) {
                mMultiUserAvatar.setImageDrawable(picture);
            }
        });
    }

    @Override
    public void onClick(View v) {
        if (v == mSettingsButton) {
            startSettingsActivity();
        } else if (v == mSystemIconsSuperContainer) {
            startBatteryActivity();
        } else if (v == mAlarmStatus && mNextAlarm != null) {
            PendingIntent showIntent = mNextAlarm.getShowIntent();
            if (showIntent != null && showIntent.isActivity()) {
                mActivityStarter.startActivity(showIntent.getIntent(), true /* dismissShade */);
            }
        } else if (v == mClock) {
            startClockActivity();
        } else if (v == mDateGroup) {
            startDateActivity();
        } else if (v == mWeatherContainer) {
            startForecastActivity();
        }
    }

    private void startSettingsActivity() {
        mActivityStarter.startActivity(new Intent(android.provider.Settings.ACTION_SETTINGS),
                true /* dismissShade */);
    }

    private void startBatteryActivity() {
        mActivityStarter.startActivity(new Intent(Intent.ACTION_POWER_USAGE_SUMMARY),
                true /* dismissShade */);
    }

    private void startClockActivity() {
        mActivityStarter.startActivity(new Intent(AlarmClock.ACTION_SHOW_ALARMS),
                true /* dismissShade */);
    }

    private void startDateActivity() {
        Uri.Builder builder = CalendarContract.CONTENT_URI.buildUpon();
        builder.appendPath("time");
        ContentUris.appendId(builder, System.currentTimeMillis());
        Intent intent = new Intent(Intent.ACTION_VIEW).setData(builder.build());
        mActivityStarter.startActivity(intent, true /* dismissShade */);
    }

    private void startForecastActivity() {
        Intent intent = new Intent(Intent.ACTION_MAIN);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        intent.setComponent(WeatherControllerImpl.COMPONENT_WEATHER_FORECAST);
        mActivityStarter.startActivity(intent, true /* dismissShade */);
    }

    public void setQSPanel(QSPanel qsp) {
        mQSPanel = qsp;
        if (mQSPanel != null) {
            mQSPanel.setCallback(mQsPanelCallback);
        }
        mMultiUserSwitch.setQsPanel(qsp);
    }

    @Override
    public boolean shouldDelayChildPressedState() {
        return true;
    }

    public void setShowEmergencyCallsOnly(boolean show) {
        boolean changed = show != mShowEmergencyCallsOnly;
        if (changed) {
            mShowEmergencyCallsOnly = show;
            if (mExpanded) {
                updateEverything();
                requestCaptureValues();
            }
        }
    }

    @Override
    protected void dispatchSetPressed(boolean pressed) {
        // We don't want that everything lights up when we click on the header, so block the request
        // here.
    }

    private void captureLayoutValues(LayoutValues target) {
        target.timeScale = mExpanded ? 1f : mClockCollapsedScaleFactor;
        target.clockY = mClock.getBottom();
        target.dateY = mDateGroup.getTop();
        target.emergencyCallsOnlyAlpha = getAlphaForVisibility(mEmergencyCallsOnly);
        target.alarmStatusAlpha = getAlphaForVisibility(mAlarmStatus);
        target.dateCollapsedAlpha = getAlphaForVisibility(mDateCollapsed);
        target.dateExpandedAlpha = getAlphaForVisibility(mDateExpanded);
        target.avatarScale = mMultiUserAvatar.getScaleX();
        target.avatarX = mMultiUserSwitch.getLeft() + mMultiUserAvatar.getLeft();
        target.avatarY = mMultiUserSwitch.getTop() + mMultiUserAvatar.getTop();
        target.weatherY = mClock.getBottom() - mWeatherLine1.getHeight();
        if (getLayoutDirection() == LAYOUT_DIRECTION_LTR) {
            target.batteryX = mSystemIconsSuperContainer.getLeft()
                    + mSystemIconsContainer.getRight();
        } else {
            target.batteryX = mSystemIconsSuperContainer.getLeft()
                    + mSystemIconsContainer.getLeft();
        }
        target.batteryY = mSystemIconsSuperContainer.getTop() + mSystemIconsContainer.getTop();
        target.batteryLevelAlpha = getAlphaForVisibility(mBatteryLevel);
        target.settingsAlpha = getAlphaForVisibility(mSettingsButton);
        target.settingsTranslation = mExpanded
                ? 0
                : mMultiUserSwitch.getLeft() - mSettingsButton.getLeft();
        target.signalClusterAlpha = mSignalClusterDetached ? 0f : 1f;
        target.settingsRotation = !mExpanded ? 90f : 0f;
    }

    private float getAlphaForVisibility(View v) {
        return v == null || v.getVisibility() == View.VISIBLE ? 1f : 0f;
    }

    private void applyAlpha(View v, float alpha) {
        if (v == null || v.getVisibility() == View.GONE) {
            return;
        }
        if (alpha == 0f) {
            v.setVisibility(View.INVISIBLE);
        } else {
            v.setVisibility(View.VISIBLE);
            v.setAlpha(alpha);
        }
    }

    private void applyLayoutValues(LayoutValues values) {
        mTime.setScaleX(values.timeScale);
        mTime.setScaleY(values.timeScale);
        mClock.setY(values.clockY - mClock.getHeight());
        mDateGroup.setY(values.dateY);
        mWeatherContainer.setY(values.weatherY);
        mAlarmStatus.setY(values.dateY - mAlarmStatus.getPaddingTop());
        mMultiUserAvatar.setScaleX(values.avatarScale);
        mMultiUserAvatar.setScaleY(values.avatarScale);
        mMultiUserAvatar.setX(values.avatarX - mMultiUserSwitch.getLeft());
        mMultiUserAvatar.setY(values.avatarY - mMultiUserSwitch.getTop());
        if (getLayoutDirection() == LAYOUT_DIRECTION_LTR) {
            mSystemIconsSuperContainer.setX(values.batteryX - mSystemIconsContainer.getRight());
        } else {
            mSystemIconsSuperContainer.setX(values.batteryX - mSystemIconsContainer.getLeft());
        }
        mSystemIconsSuperContainer.setY(values.batteryY - mSystemIconsContainer.getTop());
        if (mSignalCluster != null && mExpanded) {
            if (getLayoutDirection() == LAYOUT_DIRECTION_LTR) {
                mSignalCluster.setX(mSystemIconsSuperContainer.getX()
                        - mSignalCluster.getWidth());
            } else {
                mSignalCluster.setX(mSystemIconsSuperContainer.getX()
                        + mSystemIconsSuperContainer.getWidth());
            }
            mSignalCluster.setY(
                    mSystemIconsSuperContainer.getY() + mSystemIconsSuperContainer.getHeight()/2
                            - mSignalCluster.getHeight()/2);
        } else if (mSignalCluster != null) {
            mSignalCluster.setTranslationX(0f);
            mSignalCluster.setTranslationY(0f);
        }
        mSettingsButton.setTranslationY(mSystemIconsSuperContainer.getTranslationY());
        mSettingsButton.setTranslationX(values.settingsTranslation);
        mSettingsButton.setRotation(values.settingsRotation);
        applyAlpha(mEmergencyCallsOnly, values.emergencyCallsOnlyAlpha);
        if (!mShowingDetail) {
            // Otherwise it needs to stay invisible
            applyAlpha(mAlarmStatus, values.alarmStatusAlpha);
        }
        applyAlpha(mDateCollapsed, values.dateCollapsedAlpha);
        applyAlpha(mDateExpanded, values.dateExpandedAlpha);
        applyAlpha(mBatteryLevel, values.batteryLevelAlpha);
        applyAlpha(mSettingsButton, values.settingsAlpha);
        applyAlpha(mWeatherLine1, values.settingsAlpha);
        applyAlpha(mWeatherLine2, values.settingsAlpha);
        applyAlpha(mSignalCluster, values.signalClusterAlpha);
        if (!mExpanded) {
            mTime.setScaleX(1f);
            mTime.setScaleY(1f);
        }
        updateAmPmTranslation();
    }

    /**
     * Captures all layout values (position, visibility) for a certain state. This is used for
     * animations.
     */
    private static final class LayoutValues {

        float dateExpandedAlpha;
        float dateCollapsedAlpha;
        float emergencyCallsOnlyAlpha;
        float alarmStatusAlpha;
        float timeScale = 1f;
        float clockY;
        float dateY;
        float avatarScale;
        float avatarX;
        float avatarY;
        float batteryX;
        float batteryY;
        float batteryLevelAlpha;
        float batteryLevelExpandedAlpha;
        float settingsAlpha;
        float settingsTranslation;
        float signalClusterAlpha;
        float settingsRotation;
        float weatherY;

        public void interpoloate(LayoutValues v1, LayoutValues v2, float t) {
            timeScale = v1.timeScale * (1 - t) + v2.timeScale * t;
            clockY = v1.clockY * (1 - t) + v2.clockY * t;
            dateY = v1.dateY * (1 - t) + v2.dateY * t;
            avatarScale = v1.avatarScale * (1 - t) + v2.avatarScale * t;
            avatarX = v1.avatarX * (1 - t) + v2.avatarX * t;
            avatarY = v1.avatarY * (1 - t) + v2.avatarY * t;
            batteryX = v1.batteryX * (1 - t) + v2.batteryX * t;
            batteryY = v1.batteryY * (1 - t) + v2.batteryY * t;
            settingsTranslation = v1.settingsTranslation * (1 - t) + v2.settingsTranslation * t;
            weatherY = v1.weatherY * (1 - t) + v2.weatherY * t;

            float t1 = Math.max(0, t - 0.5f) * 2;
            settingsRotation = v1.settingsRotation * (1 - t1) + v2.settingsRotation * t1;
            emergencyCallsOnlyAlpha =
                    v1.emergencyCallsOnlyAlpha * (1 - t1) + v2.emergencyCallsOnlyAlpha * t1;

            float t2 = Math.min(1, 2 * t);
            signalClusterAlpha = v1.signalClusterAlpha * (1 - t2) + v2.signalClusterAlpha * t2;

            float t3 = Math.max(0, t - 0.7f) / 0.3f;
            batteryLevelAlpha = v1.batteryLevelAlpha * (1 - t3) + v2.batteryLevelAlpha * t3;
            batteryLevelExpandedAlpha =
                    v1.batteryLevelExpandedAlpha * (1 - t3) + v2.batteryLevelExpandedAlpha * t3;
            settingsAlpha = v1.settingsAlpha * (1 - t3) + v2.settingsAlpha * t3;
            dateExpandedAlpha = v1.dateExpandedAlpha * (1 - t3) + v2.dateExpandedAlpha * t3;
            dateCollapsedAlpha = v1.dateCollapsedAlpha * (1 - t3) + v2.dateCollapsedAlpha * t3;
            alarmStatusAlpha = v1.alarmStatusAlpha * (1 - t3) + v2.alarmStatusAlpha * t3;
        }
    }

    private final QSPanel.Callback mQsPanelCallback = new QSPanel.Callback() {
        private boolean mScanState;

        @Override
        public void onToggleStateChanged(final boolean state) {
            post(new Runnable() {
                @Override
                public void run() {
                    handleToggleStateChanged(state);
                }
            });
        }

        @Override
        public void onShowingDetail(final QSTile.DetailAdapter detail) {
            post(new Runnable() {
                @Override
                public void run() {
                    handleShowingDetail(detail);
                }
            });
        }

        @Override
        public void onScanStateChanged(final boolean state) {
            post(new Runnable() {
                @Override
                public void run() {
                    handleScanStateChanged(state);
                }
            });
        }

        private void handleToggleStateChanged(boolean state) {
            mQsDetailHeaderSwitch.setChecked(state);
        }

        private void handleScanStateChanged(boolean state) {
            if (mScanState == state) return;
            mScanState = state;
            final Animatable anim = (Animatable) mQsDetailHeaderProgress.getDrawable();
            if (state) {
                mQsDetailHeaderProgress.animate().alpha(1f);
                anim.start();
            } else {
                mQsDetailHeaderProgress.animate().alpha(0f);
                anim.stop();
            }
        }

        private void handleShowingDetail(final QSTile.DetailAdapter detail) {
            final boolean showingDetail = detail != null;
            transition(mClock, !showingDetail);
            transition(mDateGroup, !showingDetail);
            if (mShowWeather) {
                transition(mWeatherContainer, !showingDetail);
            }
            if (mAlarmShowing) {
                transition(mAlarmStatus, !showingDetail);
            }
            transition(mQsDetailHeader, showingDetail);
            mShowingDetail = showingDetail;
            if (showingDetail) {
                mQsDetailHeaderTitle.setText(detail.getTitle());
                final Boolean toggleState = detail.getToggleState();
                if (toggleState == null) {
                    mQsDetailHeaderSwitch.setVisibility(INVISIBLE);
                    mQsDetailHeader.setClickable(false);
                } else {
                    mQsDetailHeaderSwitch.setVisibility(VISIBLE);
                    mQsDetailHeaderSwitch.setChecked(toggleState);
                    mQsDetailHeader.setClickable(true);
                    mQsDetailHeader.setOnClickListener(new OnClickListener() {
                        @Override
                        public void onClick(View v) {
                            detail.setToggleState(!mQsDetailHeaderSwitch.isChecked());
                        }
                    });
                }
            } else {
                mQsDetailHeader.setClickable(false);
            }
        }

        private void transition(final View v, final boolean in) {
            if (in) {
                v.bringToFront();
                v.setVisibility(VISIBLE);
            }
            v.animate()
                    .alpha(in ? 1 : 0)
                    .withLayer()
                    .withEndAction(new Runnable() {
                        @Override
                        public void run() {
                            if (!in) {
                                v.setVisibility(INVISIBLE);
                            }
                        }
                    })
                    .start();
        }
    };

    class SettingsObserver extends UserContentObserver {
        SettingsObserver(Handler handler) {
            super(handler);
        }

        @Override
        protected void observe() {
            super.observe();

            ContentResolver resolver = mContext.getContentResolver();
            resolver.registerContentObserver(Settings.System.getUriFor(
                    Settings.System.STATUS_BAR_SHOW_WEATHER), false, this, UserHandle.USER_ALL);
            resolver.registerContentObserver(Settings.System.getUriFor(
                    Settings.System.STATUS_BAR_BATTERY_STYLE), false, this, UserHandle.USER_ALL);
            resolver.registerContentObserver(Settings.System.getUriFor(
                    Settings.System.STATUS_BAR_SHOW_BATTERY_PERCENT), false, this,
                    UserHandle.USER_ALL);
            update();
        }

        @Override
        protected void unobserve() {
            super.unobserve();

            ContentResolver resolver = mContext.getContentResolver();
            resolver.unregisterContentObserver(this);
        }

        @Override
        public void update() {

            ContentResolver resolver = mContext.getContentResolver();
            int currentUserId = ActivityManager.getCurrentUser();
            int batteryStyle = Settings.System.getIntForUser(resolver,
                    Settings.System.STATUS_BAR_BATTERY_STYLE, 0, currentUserId);
            boolean showExpandedBatteryPercentage = Settings.System.getIntForUser(resolver,
                    Settings.System.STATUS_BAR_SHOW_BATTERY_PERCENT, 0, currentUserId) == 0;

            switch (batteryStyle) {
                case 4: //BATTERY_METER_GONE
                case 6: //BATTERY_METER_TEXT
                    showExpandedBatteryPercentage = false;
                    break;
                default:
                    break;
            }

            mShowBatteryTextExpanded = showExpandedBatteryPercentage;
            mShowWeather = Settings.System.getInt(
                    resolver, Settings.System.STATUS_BAR_SHOW_WEATHER, 1) == 1;
            updateVisibilities();
            requestCaptureValues();
        }
    }
}


File: packages/SystemUI/src/com/android/systemui/statusbar/policy/BatteryController.java
/*
 * Copyright (C) 2010 The Android Open Source Project
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

package com.android.systemui.statusbar.policy;

import android.content.BroadcastReceiver;
import android.content.ContentResolver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.database.ContentObserver;
import android.net.Uri;
import android.os.BatteryManager;
import android.os.Handler;
import android.os.PowerManager;
import android.provider.Settings;
import android.util.Log;

import java.io.FileDescriptor;
import java.io.PrintWriter;
import java.util.ArrayList;

public class BatteryController extends BroadcastReceiver {
    private static final String TAG = "BatteryController";
    private static final boolean DEBUG = Log.isLoggable(TAG, Log.DEBUG);

    public static final int STYLE_ICON_PORTRAIT = 0;
    public static final int STYLE_CIRCLE = 2;
    public static final int STYLE_GONE = 4;
    public static final int STYLE_ICON_LANDSCAPE = 5;
    public static final int STYLE_TEXT = 6;

    public static final int PERCENTAGE_MODE_OFF = 0;
    public static final int PERCENTAGE_MODE_INSIDE = 1;
    public static final int PERCENTAGE_MODE_OUTSIDE = 2;

    private final ArrayList<BatteryStateChangeCallback> mChangeCallbacks = new ArrayList<>();
    private final PowerManager mPowerManager;

    private int mLevel;
    private boolean mPluggedIn;
    private boolean mCharging;
    private boolean mCharged;
    private boolean mPowerSave;

    private int mStyle;
    private int mPercentMode;
    private int mUserId;
    private SettingsObserver mObserver;

    public BatteryController(Context context, Handler handler) {
        mPowerManager = (PowerManager) context.getSystemService(Context.POWER_SERVICE);

        IntentFilter filter = new IntentFilter();
        filter.addAction(Intent.ACTION_BATTERY_CHANGED);
        filter.addAction(PowerManager.ACTION_POWER_SAVE_MODE_CHANGED);
        filter.addAction(PowerManager.ACTION_POWER_SAVE_MODE_CHANGING);
        context.registerReceiver(this, filter);

        updatePowerSave();

        mObserver = new SettingsObserver(context, handler);
        mObserver.observe();
    }

    public void setUserId(int userId) {
        mUserId = userId;
        mObserver.observe();
    }

    public void dump(FileDescriptor fd, PrintWriter pw, String[] args) {
        pw.println("BatteryController state:");
        pw.print("  mLevel="); pw.println(mLevel);
        pw.print("  mPluggedIn="); pw.println(mPluggedIn);
        pw.print("  mCharging="); pw.println(mCharging);
        pw.print("  mCharged="); pw.println(mCharged);
        pw.print("  mPowerSave="); pw.println(mPowerSave);
    }

    public void addStateChangedCallback(BatteryStateChangeCallback cb) {
        mChangeCallbacks.add(cb);
        cb.onBatteryLevelChanged(mLevel, mPluggedIn, mCharging);
        cb.onBatteryStyleChanged(mStyle, mPercentMode);
    }

    public void removeStateChangedCallback(BatteryStateChangeCallback cb) {
        mChangeCallbacks.remove(cb);
    }

    public void onReceive(Context context, Intent intent) {
        final String action = intent.getAction();
        if (action.equals(Intent.ACTION_BATTERY_CHANGED)) {
            mLevel = (int)(100f
                    * intent.getIntExtra(BatteryManager.EXTRA_LEVEL, 0)
                    / intent.getIntExtra(BatteryManager.EXTRA_SCALE, 100));
            mPluggedIn = intent.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0) != 0;

            final int status = intent.getIntExtra(BatteryManager.EXTRA_STATUS,
                    BatteryManager.BATTERY_STATUS_UNKNOWN);
            mCharged = status == BatteryManager.BATTERY_STATUS_FULL;
            mCharging = mCharged || status == BatteryManager.BATTERY_STATUS_CHARGING;

            fireBatteryLevelChanged();
        } else if (action.equals(PowerManager.ACTION_POWER_SAVE_MODE_CHANGED)) {
            updatePowerSave();
        } else if (action.equals(PowerManager.ACTION_POWER_SAVE_MODE_CHANGING)) {
            setPowerSave(intent.getBooleanExtra(PowerManager.EXTRA_POWER_SAVE_MODE, false));
        }
    }

    public boolean isPowerSave() {
        return mPowerSave;
    }

    private void updatePowerSave() {
        setPowerSave(mPowerManager.isPowerSaveMode());
    }

    private void setPowerSave(boolean powerSave) {
        if (powerSave == mPowerSave) return;
        mPowerSave = powerSave;
        if (DEBUG) Log.d(TAG, "Power save is " + (mPowerSave ? "on" : "off"));
        firePowerSaveChanged();
    }

    private void fireBatteryLevelChanged() {
        final int N = mChangeCallbacks.size();
        for (int i = 0; i < N; i++) {
            mChangeCallbacks.get(i).onBatteryLevelChanged(mLevel, mPluggedIn, mCharging);
        }
    }

    private void firePowerSaveChanged() {
        final int N = mChangeCallbacks.size();
        for (int i = 0; i < N; i++) {
            mChangeCallbacks.get(i).onPowerSaveChanged();
        }
    }

    private void fireSettingsChanged() {
        final int N = mChangeCallbacks.size();
        for (int i = 0; i < N; i++) {
            mChangeCallbacks.get(i).onBatteryStyleChanged(mStyle, mPercentMode);
        }
    }

    public interface BatteryStateChangeCallback {
        void onBatteryLevelChanged(int level, boolean pluggedIn, boolean charging);
        void onPowerSaveChanged();
        void onBatteryStyleChanged(int style, int percentMode);
    }

    private final class SettingsObserver extends ContentObserver {
        private ContentResolver mResolver;
        private boolean mRegistered;

        private final Uri STYLE_URI =
                Settings.System.getUriFor(Settings.System.STATUS_BAR_BATTERY_STYLE);
        private final Uri PERCENT_URI =
                Settings.System.getUriFor(Settings.System.STATUS_BAR_SHOW_BATTERY_PERCENT);

        public SettingsObserver(Context context, Handler handler) {
            super(handler);
            mResolver = context.getContentResolver();
        }

        public void observe() {
            if (mRegistered) {
                mResolver.unregisterContentObserver(this);
            }
            mResolver.registerContentObserver(STYLE_URI, false, this, mUserId);
            mResolver.registerContentObserver(PERCENT_URI, false, this, mUserId);
            mRegistered = true;

            update();
        }

        @Override
        public void onChange(boolean selfChange, Uri uri) {
            update();
        }

        private void update() {
            mStyle = Settings.System.getIntForUser(mResolver,
                    Settings.System.STATUS_BAR_BATTERY_STYLE, 0, mUserId);
            mPercentMode = Settings.System.getIntForUser(mResolver,
                    Settings.System.STATUS_BAR_SHOW_BATTERY_PERCENT, 0, mUserId);

            fireSettingsChanged();
        }
    };
}


File: services/core/java/com/android/server/BatteryService.java
/*
 * Copyright (C) 2006 The Android Open Source Project
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

package com.android.server;

import android.database.ContentObserver;
import android.os.BatteryStats;

import com.android.internal.app.IBatteryStats;
import com.android.server.am.BatteryStatsService;
import com.android.server.lights.Light;
import com.android.server.lights.LightsManager;

import android.app.ActivityManagerNative;
import android.content.ContentResolver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.res.Resources;
import android.database.ContentObserver;
import android.os.BatteryManager;
import android.os.BatteryManagerInternal;
import android.os.BatteryProperties;
import android.os.Binder;
import android.os.FileUtils;
import android.os.Handler;
import android.os.IBatteryPropertiesListener;
import android.os.IBatteryPropertiesRegistrar;
import android.os.IBinder;
import android.os.DropBoxManager;
import android.os.RemoteException;
import android.os.ServiceManager;
import android.os.SystemClock;
import android.os.UEventObserver;
import android.os.UserHandle;
import android.provider.Settings;
import android.util.EventLog;
import android.util.Slog;

import java.io.File;
import java.io.FileDescriptor;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.PrintWriter;


/**
 * <p>BatteryService monitors the charging status, and charge level of the device
 * battery.  When these values change this service broadcasts the new values
 * to all {@link android.content.BroadcastReceiver IntentReceivers} that are
 * watching the {@link android.content.Intent#ACTION_BATTERY_CHANGED
 * BATTERY_CHANGED} action.</p>
 * <p>The new values are stored in the Intent data and can be retrieved by
 * calling {@link android.content.Intent#getExtra Intent.getExtra} with the
 * following keys:</p>
 * <p>&quot;scale&quot; - int, the maximum value for the charge level</p>
 * <p>&quot;level&quot; - int, charge level, from 0 through &quot;scale&quot; inclusive</p>
 * <p>&quot;status&quot; - String, the current charging status.<br />
 * <p>&quot;health&quot; - String, the current battery health.<br />
 * <p>&quot;present&quot; - boolean, true if the battery is present<br />
 * <p>&quot;icon-small&quot; - int, suggested small icon to use for this state</p>
 * <p>&quot;plugged&quot; - int, 0 if the device is not plugged in; 1 if plugged
 * into an AC power adapter; 2 if plugged in via USB.</p>
 * <p>&quot;voltage&quot; - int, current battery voltage in millivolts</p>
 * <p>&quot;temperature&quot; - int, current battery temperature in tenths of
 * a degree Centigrade</p>
 * <p>&quot;technology&quot; - String, the type of battery installed, e.g. "Li-ion"</p>
 *
 * <p>
 * The battery service may be called by the power manager while holding its locks so
 * we take care to post all outcalls into the activity manager to a handler.
 *
 * FIXME: Ideally the power manager would perform all of its calls into the battery
 * service asynchronously itself.
 * </p>
 */
public final class BatteryService extends SystemService {
    private static final String TAG = BatteryService.class.getSimpleName();

    private static final boolean DEBUG = false;

    private static final int BATTERY_SCALE = 100;    // battery capacity is a percentage

    // Used locally for determining when to make a last ditch effort to log
    // discharge stats before the device dies.
    private int mCriticalBatteryLevel;

    private static final int DUMP_MAX_LENGTH = 24 * 1024;
    private static final String[] DUMPSYS_ARGS = new String[] { "--checkin", "--unplugged" };

    private static final String DUMPSYS_DATA_PATH = "/data/system/";

    // This should probably be exposed in the API, though it's not critical
    private static final int BATTERY_PLUGGED_NONE = 0;

    private final Context mContext;
    private final IBatteryStats mBatteryStats;
    private final Handler mHandler;

    private final Object mLock = new Object();

    private BatteryProperties mBatteryProps;
    private final BatteryProperties mLastBatteryProps = new BatteryProperties();
    private boolean mBatteryLevelCritical;
    private int mLastBatteryStatus;
    private int mLastBatteryHealth;
    private boolean mLastBatteryPresent;
    private int mLastBatteryLevel;
    private int mLastBatteryVoltage;
    private int mLastBatteryTemperature;
    private boolean mLastBatteryLevelCritical;

    private int mInvalidCharger;
    private int mLastInvalidCharger;

    private int mLowBatteryWarningLevel;
    private int mLowBatteryCloseWarningLevel;
    private int mShutdownBatteryTemperature;

    private int mPlugType;
    private int mLastPlugType = -1; // Extra state so we can detect first run

    private boolean mBatteryLevelLow;

    private long mDischargeStartTime;
    private int mDischargeStartLevel;

    private boolean mUpdatesStopped;

    private Led mLed;
    // Disable LED until SettingsObserver can be started
    private boolean mLightEnabled = false;
    private boolean mLedPulseEnabled;
    private int mBatteryLowARGB;
    private int mBatteryMediumARGB;
    private int mBatteryFullARGB;
    private boolean mMultiColorLed;

    private boolean mSentLowBatteryBroadcast = false;

    public BatteryService(Context context) {
        super(context);

        mContext = context;
        mHandler = new Handler(true /*async*/);
        mLed = new Led(context, getLocalService(LightsManager.class));
        mBatteryStats = BatteryStatsService.getService();

        mCriticalBatteryLevel = mContext.getResources().getInteger(
                com.android.internal.R.integer.config_criticalBatteryWarningLevel);
        mLowBatteryWarningLevel = mContext.getResources().getInteger(
                com.android.internal.R.integer.config_lowBatteryWarningLevel);
        mLowBatteryCloseWarningLevel = mLowBatteryWarningLevel + mContext.getResources().getInteger(
                com.android.internal.R.integer.config_lowBatteryCloseWarningBump);
        mShutdownBatteryTemperature = mContext.getResources().getInteger(
                com.android.internal.R.integer.config_shutdownBatteryTemperature);

        // watch for invalid charger messages if the invalid_charger switch exists
        if (new File("/sys/devices/virtual/switch/invalid_charger/state").exists()) {
            mInvalidChargerObserver.startObserving(
                    "DEVPATH=/devices/virtual/switch/invalid_charger");
        }
    }

    @Override
    public void onStart() {
        IBinder b = ServiceManager.getService("batteryproperties");
        final IBatteryPropertiesRegistrar batteryPropertiesRegistrar =
                IBatteryPropertiesRegistrar.Stub.asInterface(b);
        try {
            batteryPropertiesRegistrar.registerListener(new BatteryListener());
        } catch (RemoteException e) {
            // Should never happen.
        }

        publishBinderService("battery", new BinderService());
        publishLocalService(BatteryManagerInternal.class, new LocalService());
    }

    @Override
    public void onBootPhase(int phase) {
        if (phase == PHASE_ACTIVITY_MANAGER_READY) {
            // check our power situation now that it is safe to display the shutdown dialog.
            synchronized (mLock) {
                ContentObserver obs = new ContentObserver(mHandler) {
                    @Override
                    public void onChange(boolean selfChange) {
                        synchronized (mLock) {
                            updateBatteryWarningLevelLocked();
                        }
                    }
                };
                final ContentResolver resolver = mContext.getContentResolver();
                resolver.registerContentObserver(Settings.Global.getUriFor(
                        Settings.Global.LOW_POWER_MODE_TRIGGER_LEVEL),
                        false, obs, UserHandle.USER_ALL);
                updateBatteryWarningLevelLocked();
            }
        } else if (phase == PHASE_BOOT_COMPLETED) {
            SettingsObserver observer = new SettingsObserver(new Handler());
            observer.observe();
        }
    }

    private void updateBatteryWarningLevelLocked() {
        final ContentResolver resolver = mContext.getContentResolver();
        int defWarnLevel = mContext.getResources().getInteger(
                com.android.internal.R.integer.config_lowBatteryWarningLevel);
        mLowBatteryWarningLevel = Settings.Global.getInt(resolver,
                Settings.Global.LOW_POWER_MODE_TRIGGER_LEVEL, defWarnLevel);
        if (mLowBatteryWarningLevel == 0) {
            mLowBatteryWarningLevel = defWarnLevel;
        }
        if (mLowBatteryWarningLevel < mCriticalBatteryLevel) {
            mLowBatteryWarningLevel = mCriticalBatteryLevel;
        }
        mLowBatteryCloseWarningLevel = mLowBatteryWarningLevel + mContext.getResources().getInteger(
                com.android.internal.R.integer.config_lowBatteryCloseWarningBump);
        processValuesLocked(true);
    }

    private boolean isPoweredLocked(int plugTypeSet) {
        // assume we are powered if battery state is unknown so
        // the "stay on while plugged in" option will work.
        if (mBatteryProps.batteryStatus == BatteryManager.BATTERY_STATUS_UNKNOWN) {
            return true;
        }
        if ((plugTypeSet & BatteryManager.BATTERY_PLUGGED_AC) != 0 && mBatteryProps.chargerAcOnline) {
            return true;
        }
        if ((plugTypeSet & BatteryManager.BATTERY_PLUGGED_USB) != 0 && mBatteryProps.chargerUsbOnline) {
            return true;
        }
        if ((plugTypeSet & BatteryManager.BATTERY_PLUGGED_WIRELESS) != 0 && mBatteryProps.chargerWirelessOnline) {
            return true;
        }
        return false;
    }

    private boolean shouldSendBatteryLowLocked() {
        final boolean plugged = mPlugType != BATTERY_PLUGGED_NONE;
        final boolean oldPlugged = mLastPlugType != BATTERY_PLUGGED_NONE;

        /* The ACTION_BATTERY_LOW broadcast is sent in these situations:
         * - is just un-plugged (previously was plugged) and battery level is
         *   less than or equal to WARNING, or
         * - is not plugged and battery level falls to WARNING boundary
         *   (becomes <= mLowBatteryWarningLevel).
         */
        return !plugged
                && mBatteryProps.batteryStatus != BatteryManager.BATTERY_STATUS_UNKNOWN
                && mBatteryProps.batteryLevel <= mLowBatteryWarningLevel
                && (oldPlugged || mLastBatteryLevel > mLowBatteryWarningLevel);
    }

    private void shutdownIfNoPowerLocked() {
        // shut down gracefully if our battery is critically low and we are not powered.
        // wait until the system has booted before attempting to display the shutdown dialog.
        if (mBatteryProps.batteryLevel == 0 && !isPoweredLocked(BatteryManager.BATTERY_PLUGGED_ANY)) {
            mHandler.post(new Runnable() {
                @Override
                public void run() {
                    if (ActivityManagerNative.isSystemReady()) {
                        Slog.e(TAG, "silent_reboot shutdownIfNoPowerLocked");
                        Intent intent = new Intent(Intent.ACTION_REQUEST_SHUTDOWN);
                        intent.putExtra(Intent.EXTRA_KEY_CONFIRM, false);
                        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                        mContext.startActivityAsUser(intent, UserHandle.CURRENT);
                    }
                }
            });
        }
    }

    private void shutdownIfOverTempLocked() {
        // shut down gracefully if temperature is too high (> 68.0C by default)
        // wait until the system has booted before attempting to display the
        // shutdown dialog.
        if (mBatteryProps.batteryTemperature > mShutdownBatteryTemperature) {
            mHandler.post(new Runnable() {
                @Override
                public void run() {
                    if (ActivityManagerNative.isSystemReady()) {
                        Slog.e(TAG, "silent_reboot shutdownIfOverTempLocked");
                        Intent intent = new Intent(Intent.ACTION_REQUEST_SHUTDOWN);
                        intent.putExtra(Intent.EXTRA_KEY_CONFIRM, false);
                        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                        mContext.startActivityAsUser(intent, UserHandle.CURRENT);
                    }
                }
            });
        }
    }

    private void update(BatteryProperties props) {
        synchronized (mLock) {
            if (!mUpdatesStopped) {
                mBatteryProps = props;
                // Process the new values.
                processValuesLocked(false);
            } else {
                mLastBatteryProps.set(props);
            }
        }
    }

    private void processValuesLocked(boolean force) {
        boolean logOutlier = false;
        long dischargeDuration = 0;

        mBatteryLevelCritical = (mBatteryProps.batteryLevel <= mCriticalBatteryLevel);
        if (mBatteryProps.chargerAcOnline) {
            mPlugType = BatteryManager.BATTERY_PLUGGED_AC;
        } else if (mBatteryProps.chargerUsbOnline) {
            mPlugType = BatteryManager.BATTERY_PLUGGED_USB;
        } else if (mBatteryProps.chargerWirelessOnline) {
            mPlugType = BatteryManager.BATTERY_PLUGGED_WIRELESS;
        } else {
            mPlugType = BATTERY_PLUGGED_NONE;
        }

        if (DEBUG) {
            Slog.d(TAG, "Processing new values: "
                    + "chargerAcOnline=" + mBatteryProps.chargerAcOnline
                    + ", chargerUsbOnline=" + mBatteryProps.chargerUsbOnline
                    + ", chargerWirelessOnline=" + mBatteryProps.chargerWirelessOnline
                    + ", batteryStatus=" + mBatteryProps.batteryStatus
                    + ", batteryHealth=" + mBatteryProps.batteryHealth
                    + ", batteryPresent=" + mBatteryProps.batteryPresent
                    + ", batteryLevel=" + mBatteryProps.batteryLevel
                    + ", batteryTechnology=" + mBatteryProps.batteryTechnology
                    + ", batteryVoltage=" + mBatteryProps.batteryVoltage
                    + ", batteryTemperature=" + mBatteryProps.batteryTemperature
                    + ", mBatteryLevelCritical=" + mBatteryLevelCritical
                    + ", mPlugType=" + mPlugType);
        }

        // Let the battery stats keep track of the current level.
        try {
            mBatteryStats.setBatteryState(mBatteryProps.batteryStatus, mBatteryProps.batteryHealth,
                    mPlugType, mBatteryProps.batteryLevel, mBatteryProps.batteryTemperature,
                    mBatteryProps.batteryVoltage);
        } catch (RemoteException e) {
            // Should never happen.
        }

        shutdownIfNoPowerLocked();
        shutdownIfOverTempLocked();

        if (force || (mBatteryProps.batteryStatus != mLastBatteryStatus ||
                mBatteryProps.batteryHealth != mLastBatteryHealth ||
                mBatteryProps.batteryPresent != mLastBatteryPresent ||
                mBatteryProps.batteryLevel != mLastBatteryLevel ||
                mPlugType != mLastPlugType ||
                mBatteryProps.batteryVoltage != mLastBatteryVoltage ||
                mBatteryProps.batteryTemperature != mLastBatteryTemperature ||
                mInvalidCharger != mLastInvalidCharger)) {

            if (mPlugType != mLastPlugType) {
                if (mLastPlugType == BATTERY_PLUGGED_NONE) {
                    // discharging -> charging

                    // There's no value in this data unless we've discharged at least once and the
                    // battery level has changed; so don't log until it does.
                    if (mDischargeStartTime != 0 && mDischargeStartLevel != mBatteryProps.batteryLevel) {
                        dischargeDuration = SystemClock.elapsedRealtime() - mDischargeStartTime;
                        logOutlier = true;
                        EventLog.writeEvent(EventLogTags.BATTERY_DISCHARGE, dischargeDuration,
                                mDischargeStartLevel, mBatteryProps.batteryLevel);
                        // make sure we see a discharge event before logging again
                        mDischargeStartTime = 0;
                    }
                } else if (mPlugType == BATTERY_PLUGGED_NONE) {
                    // charging -> discharging or we just powered up
                    mDischargeStartTime = SystemClock.elapsedRealtime();
                    mDischargeStartLevel = mBatteryProps.batteryLevel;
                }
            }
            if (mBatteryProps.batteryStatus != mLastBatteryStatus ||
                    mBatteryProps.batteryHealth != mLastBatteryHealth ||
                    mBatteryProps.batteryPresent != mLastBatteryPresent ||
                    mPlugType != mLastPlugType) {
                EventLog.writeEvent(EventLogTags.BATTERY_STATUS,
                        mBatteryProps.batteryStatus, mBatteryProps.batteryHealth, mBatteryProps.batteryPresent ? 1 : 0,
                        mPlugType, mBatteryProps.batteryTechnology);
            }
            if (mBatteryProps.batteryLevel != mLastBatteryLevel) {
                // Don't do this just from voltage or temperature changes, that is
                // too noisy.
                EventLog.writeEvent(EventLogTags.BATTERY_LEVEL,
                        mBatteryProps.batteryLevel, mBatteryProps.batteryVoltage, mBatteryProps.batteryTemperature);
            }
            if (mBatteryLevelCritical && !mLastBatteryLevelCritical &&
                    mPlugType == BATTERY_PLUGGED_NONE) {
                // We want to make sure we log discharge cycle outliers
                // if the battery is about to die.
                dischargeDuration = SystemClock.elapsedRealtime() - mDischargeStartTime;
                logOutlier = true;
            }

            if (!mBatteryLevelLow) {
                // Should we now switch in to low battery mode?
                if (mPlugType == BATTERY_PLUGGED_NONE
                        && mBatteryProps.batteryLevel <= mLowBatteryWarningLevel) {
                    mBatteryLevelLow = true;
                }
            } else {
                // Should we now switch out of low battery mode?
                if (mPlugType != BATTERY_PLUGGED_NONE) {
                    mBatteryLevelLow = false;
                } else if (mBatteryProps.batteryLevel >= mLowBatteryCloseWarningLevel)  {
                    mBatteryLevelLow = false;
                } else if (force && mBatteryProps.batteryLevel >= mLowBatteryWarningLevel) {
                    // If being forced, the previous state doesn't matter, we will just
                    // absolutely check to see if we are now above the warning level.
                    mBatteryLevelLow = false;
                }
            }

            sendIntentLocked();

            // Separate broadcast is sent for power connected / not connected
            // since the standard intent will not wake any applications and some
            // applications may want to have smart behavior based on this.
            if (mPlugType != 0 && mLastPlugType == 0) {
                mHandler.post(new Runnable() {
                    @Override
                    public void run() {
                        Intent statusIntent = new Intent(Intent.ACTION_POWER_CONNECTED);
                        statusIntent.setFlags(Intent.FLAG_RECEIVER_REGISTERED_ONLY_BEFORE_BOOT);
                        mContext.sendBroadcastAsUser(statusIntent, UserHandle.ALL);
                    }
                });
            }
            else if (mPlugType == 0 && mLastPlugType != 0) {
                mHandler.post(new Runnable() {
                    @Override
                    public void run() {
                        Intent statusIntent = new Intent(Intent.ACTION_POWER_DISCONNECTED);
                        statusIntent.setFlags(Intent.FLAG_RECEIVER_REGISTERED_ONLY_BEFORE_BOOT);
                        mContext.sendBroadcastAsUser(statusIntent, UserHandle.ALL);
                    }
                });
            }

            if (shouldSendBatteryLowLocked()) {
                mSentLowBatteryBroadcast = true;
                mHandler.post(new Runnable() {
                    @Override
                    public void run() {
                        Intent statusIntent = new Intent(Intent.ACTION_BATTERY_LOW);
                        statusIntent.setFlags(Intent.FLAG_RECEIVER_REGISTERED_ONLY_BEFORE_BOOT);
                        mContext.sendBroadcastAsUser(statusIntent, UserHandle.ALL);
                    }
                });
            } else if (mSentLowBatteryBroadcast && mLastBatteryLevel >= mLowBatteryCloseWarningLevel) {
                mSentLowBatteryBroadcast = false;
                mHandler.post(new Runnable() {
                    @Override
                    public void run() {
                        Intent statusIntent = new Intent(Intent.ACTION_BATTERY_OKAY);
                        statusIntent.setFlags(Intent.FLAG_RECEIVER_REGISTERED_ONLY_BEFORE_BOOT);
                        mContext.sendBroadcastAsUser(statusIntent, UserHandle.ALL);
                    }
                });
            }

            // Update the battery LED
            mLed.updateLightsLocked();

            // This needs to be done after sendIntent() so that we get the lastest battery stats.
            if (logOutlier && dischargeDuration != 0) {
                logOutlierLocked(dischargeDuration);
            }

            mLastBatteryStatus = mBatteryProps.batteryStatus;
            mLastBatteryHealth = mBatteryProps.batteryHealth;
            mLastBatteryPresent = mBatteryProps.batteryPresent;
            mLastBatteryLevel = mBatteryProps.batteryLevel;
            mLastPlugType = mPlugType;
            mLastBatteryVoltage = mBatteryProps.batteryVoltage;
            mLastBatteryTemperature = mBatteryProps.batteryTemperature;
            mLastBatteryLevelCritical = mBatteryLevelCritical;
            mLastInvalidCharger = mInvalidCharger;
        }
    }

    private void sendIntentLocked() {
        //  Pack up the values and broadcast them to everyone
        final Intent intent = new Intent(Intent.ACTION_BATTERY_CHANGED);
        intent.addFlags(Intent.FLAG_RECEIVER_REGISTERED_ONLY
                | Intent.FLAG_RECEIVER_REPLACE_PENDING);

        int icon = getIconLocked(mBatteryProps.batteryLevel);

        intent.putExtra(BatteryManager.EXTRA_STATUS, mBatteryProps.batteryStatus);
        intent.putExtra(BatteryManager.EXTRA_HEALTH, mBatteryProps.batteryHealth);
        intent.putExtra(BatteryManager.EXTRA_PRESENT, mBatteryProps.batteryPresent);
        intent.putExtra(BatteryManager.EXTRA_LEVEL, mBatteryProps.batteryLevel);
        intent.putExtra(BatteryManager.EXTRA_SCALE, BATTERY_SCALE);
        intent.putExtra(BatteryManager.EXTRA_ICON_SMALL, icon);
        intent.putExtra(BatteryManager.EXTRA_PLUGGED, mPlugType);
        intent.putExtra(BatteryManager.EXTRA_VOLTAGE, mBatteryProps.batteryVoltage);
        intent.putExtra(BatteryManager.EXTRA_TEMPERATURE, mBatteryProps.batteryTemperature);
        intent.putExtra(BatteryManager.EXTRA_TECHNOLOGY, mBatteryProps.batteryTechnology);
        intent.putExtra(BatteryManager.EXTRA_INVALID_CHARGER, mInvalidCharger);

        if (DEBUG) {
            Slog.d(TAG, "Sending ACTION_BATTERY_CHANGED.  level:" + mBatteryProps.batteryLevel +
                    ", scale:" + BATTERY_SCALE + ", status:" + mBatteryProps.batteryStatus +
                    ", health:" + mBatteryProps.batteryHealth +  ", present:" + mBatteryProps.batteryPresent +
                    ", voltage: " + mBatteryProps.batteryVoltage +
                    ", temperature: " + mBatteryProps.batteryTemperature +
                    ", technology: " + mBatteryProps.batteryTechnology +
                    ", AC powered:" + mBatteryProps.chargerAcOnline + ", USB powered:" + mBatteryProps.chargerUsbOnline +
                    ", Wireless powered:" + mBatteryProps.chargerWirelessOnline +
                    ", icon:" + icon  + ", invalid charger:" + mInvalidCharger);
        }

        mHandler.post(new Runnable() {
            @Override
            public void run() {
                ActivityManagerNative.broadcastStickyIntent(intent, null, UserHandle.USER_ALL);
            }
        });
    }

    private void logBatteryStatsLocked() {
        IBinder batteryInfoService = ServiceManager.getService(BatteryStats.SERVICE_NAME);
        if (batteryInfoService == null) return;

        DropBoxManager db = (DropBoxManager) mContext.getSystemService(Context.DROPBOX_SERVICE);
        if (db == null || !db.isTagEnabled("BATTERY_DISCHARGE_INFO")) return;

        File dumpFile = null;
        FileOutputStream dumpStream = null;
        try {
            // dump the service to a file
            dumpFile = new File(DUMPSYS_DATA_PATH + BatteryStats.SERVICE_NAME + ".dump");
            dumpStream = new FileOutputStream(dumpFile);
            batteryInfoService.dump(dumpStream.getFD(), DUMPSYS_ARGS);
            FileUtils.sync(dumpStream);

            // add dump file to drop box
            db.addFile("BATTERY_DISCHARGE_INFO", dumpFile, DropBoxManager.IS_TEXT);
        } catch (RemoteException e) {
            Slog.e(TAG, "failed to dump battery service", e);
        } catch (IOException e) {
            Slog.e(TAG, "failed to write dumpsys file", e);
        } finally {
            // make sure we clean up
            if (dumpStream != null) {
                try {
                    dumpStream.close();
                } catch (IOException e) {
                    Slog.e(TAG, "failed to close dumpsys output stream");
                }
            }
            if (dumpFile != null && !dumpFile.delete()) {
                Slog.e(TAG, "failed to delete temporary dumpsys file: "
                        + dumpFile.getAbsolutePath());
            }
        }
    }

    private void logOutlierLocked(long duration) {
        ContentResolver cr = mContext.getContentResolver();
        String dischargeThresholdString = Settings.Global.getString(cr,
                Settings.Global.BATTERY_DISCHARGE_THRESHOLD);
        String durationThresholdString = Settings.Global.getString(cr,
                Settings.Global.BATTERY_DISCHARGE_DURATION_THRESHOLD);

        if (dischargeThresholdString != null && durationThresholdString != null) {
            try {
                long durationThreshold = Long.parseLong(durationThresholdString);
                int dischargeThreshold = Integer.parseInt(dischargeThresholdString);
                if (duration <= durationThreshold &&
                        mDischargeStartLevel - mBatteryProps.batteryLevel >= dischargeThreshold) {
                    // If the discharge cycle is bad enough we want to know about it.
                    logBatteryStatsLocked();
                }
                if (DEBUG) Slog.v(TAG, "duration threshold: " + durationThreshold +
                        " discharge threshold: " + dischargeThreshold);
                if (DEBUG) Slog.v(TAG, "duration: " + duration + " discharge: " +
                        (mDischargeStartLevel - mBatteryProps.batteryLevel));
            } catch (NumberFormatException e) {
                Slog.e(TAG, "Invalid DischargeThresholds GService string: " +
                        durationThresholdString + " or " + dischargeThresholdString);
                return;
            }
        }
    }

    private int getIconLocked(int level) {
        if (mBatteryProps.batteryStatus == BatteryManager.BATTERY_STATUS_CHARGING) {
            return com.android.internal.R.drawable.stat_sys_battery_charge;
        } else if (mBatteryProps.batteryStatus == BatteryManager.BATTERY_STATUS_DISCHARGING) {
            return com.android.internal.R.drawable.stat_sys_battery;
        } else if (mBatteryProps.batteryStatus == BatteryManager.BATTERY_STATUS_NOT_CHARGING
                || mBatteryProps.batteryStatus == BatteryManager.BATTERY_STATUS_FULL) {
            if (isPoweredLocked(BatteryManager.BATTERY_PLUGGED_ANY)
                    && mBatteryProps.batteryLevel >= 100) {
                return com.android.internal.R.drawable.stat_sys_battery_charge;
            } else {
                return com.android.internal.R.drawable.stat_sys_battery;
            }
        } else {
            return com.android.internal.R.drawable.stat_sys_battery_unknown;
        }
    }

    private void dumpInternal(PrintWriter pw, String[] args) {
        synchronized (mLock) {
            if (args == null || args.length == 0 || "-a".equals(args[0])) {
                pw.println("Current Battery Service state:");
                if (mUpdatesStopped) {
                    pw.println("  (UPDATES STOPPED -- use 'reset' to restart)");
                }
                pw.println("  AC powered: " + mBatteryProps.chargerAcOnline);
                pw.println("  USB powered: " + mBatteryProps.chargerUsbOnline);
                pw.println("  Wireless powered: " + mBatteryProps.chargerWirelessOnline);
                pw.println("  status: " + mBatteryProps.batteryStatus);
                pw.println("  health: " + mBatteryProps.batteryHealth);
                pw.println("  present: " + mBatteryProps.batteryPresent);
                pw.println("  level: " + mBatteryProps.batteryLevel);
                pw.println("  scale: " + BATTERY_SCALE);
                pw.println("  voltage: " + mBatteryProps.batteryVoltage);
                pw.println("  temperature: " + mBatteryProps.batteryTemperature);
                pw.println("  technology: " + mBatteryProps.batteryTechnology);
            } else if (args.length == 3 && "set".equals(args[0])) {
                String key = args[1];
                String value = args[2];
                try {
                    if (!mUpdatesStopped) {
                        mLastBatteryProps.set(mBatteryProps);
                    }
                    boolean update = true;
                    if ("ac".equals(key)) {
                        mBatteryProps.chargerAcOnline = Integer.parseInt(value) != 0;
                    } else if ("usb".equals(key)) {
                        mBatteryProps.chargerUsbOnline = Integer.parseInt(value) != 0;
                    } else if ("wireless".equals(key)) {
                        mBatteryProps.chargerWirelessOnline = Integer.parseInt(value) != 0;
                    } else if ("status".equals(key)) {
                        mBatteryProps.batteryStatus = Integer.parseInt(value);
                    } else if ("level".equals(key)) {
                        mBatteryProps.batteryLevel = Integer.parseInt(value);
                    } else if ("invalid".equals(key)) {
                        mInvalidCharger = Integer.parseInt(value);
                    } else {
                        pw.println("Unknown set option: " + key);
                        update = false;
                    }
                    if (update) {
                        long ident = Binder.clearCallingIdentity();
                        try {
                            mUpdatesStopped = true;
                            processValuesLocked(false);
                        } finally {
                            Binder.restoreCallingIdentity(ident);
                        }
                    }
                } catch (NumberFormatException ex) {
                    pw.println("Bad value: " + value);
                }
            } else if (args.length == 1 && "reset".equals(args[0])) {
                long ident = Binder.clearCallingIdentity();
                try {
                    if (mUpdatesStopped) {
                        mUpdatesStopped = false;
                        mBatteryProps.set(mLastBatteryProps);
                        processValuesLocked(false);
                    }
                } finally {
                    Binder.restoreCallingIdentity(ident);
                }
            } else {
                pw.println("Dump current battery state, or:");
                pw.println("  set [ac|usb|wireless|status|level|invalid] <value>");
                pw.println("  reset");
            }
        }
    }

    private final UEventObserver mInvalidChargerObserver = new UEventObserver() {
        @Override
        public void onUEvent(UEventObserver.UEvent event) {
            final int invalidCharger = "1".equals(event.get("SWITCH_STATE")) ? 1 : 0;
            synchronized (mLock) {
                if (mInvalidCharger != invalidCharger) {
                    mInvalidCharger = invalidCharger;
                }
            }
        }
    };

    private synchronized void updateLedPulse() {
        mLed.updateLightsLocked();
    }

    private final class Led {
        private final Light mBatteryLight;

        private final int mBatteryLedOn;
        private final int mBatteryLedOff;

        public Led(Context context, LightsManager lights) {
            mBatteryLight = lights.getLight(LightsManager.LIGHT_ID_BATTERY);

            // Does the Device support changing battery LED colors?
            mMultiColorLed = context.getResources().getBoolean(
                    com.android.internal.R.bool.config_multiColorBatteryLed);

            mBatteryLedOn = context.getResources().getInteger(
                    com.android.internal.R.integer.config_notificationsBatteryLedOn);
            mBatteryLedOff = context.getResources().getInteger(
                    com.android.internal.R.integer.config_notificationsBatteryLedOff);
        }

        /**
         * Synchronize on BatteryService.
         */
        public void updateLightsLocked() {
            // mBatteryProps could be null on startup (called by SettingsObserver)
            if (mBatteryProps == null) {
                Slog.w(TAG, "updateLightsLocked: mBatteryProps is null; skipping");
                return;
            }

            final int level = mBatteryProps.batteryLevel;
            final int status = mBatteryProps.batteryStatus;
            if (!mLightEnabled) {
                // No lights if explicitly disabled
                mBatteryLight.turnOff();
            } else if (level < mLowBatteryWarningLevel) {
                if (status == BatteryManager.BATTERY_STATUS_CHARGING) {
                    // Battery is charging and low
                    mBatteryLight.setColor(mBatteryLowARGB);
                } else if (mLedPulseEnabled) {
                    // Battery is low and not charging
                    mBatteryLight.setFlashing(mBatteryLowARGB, Light.LIGHT_FLASH_TIMED,
                            mBatteryLedOn, mBatteryLedOff);
                } else {
                    // "Pulse low battery light" is disabled, no lights.
                    mBatteryLight.turnOff();
                }
            } else if (status == BatteryManager.BATTERY_STATUS_CHARGING
                    || status == BatteryManager.BATTERY_STATUS_FULL) {
                if (status == BatteryManager.BATTERY_STATUS_FULL || level >= 90) {
                    // Battery is full or charging and nearly full
                    mBatteryLight.setColor(mBatteryFullARGB);
                } else {
                    // Battery is charging and halfway full
                    mBatteryLight.setColor(mBatteryMediumARGB);
                }
            } else {
                // No lights if not charging and not low
                mBatteryLight.turnOff();
            }
        }
    }

    private final class BatteryListener extends IBatteryPropertiesListener.Stub {
        @Override
        public void batteryPropertiesChanged(BatteryProperties props) {
            final long identity = Binder.clearCallingIdentity();
            try {
                BatteryService.this.update(props);
            } finally {
                Binder.restoreCallingIdentity(identity);
            }
       }
    }

    private final class BinderService extends Binder {
        @Override
        protected void dump(FileDescriptor fd, PrintWriter pw, String[] args) {
            if (mContext.checkCallingOrSelfPermission(android.Manifest.permission.DUMP)
                    != PackageManager.PERMISSION_GRANTED) {

                pw.println("Permission Denial: can't dump Battery service from from pid="
                        + Binder.getCallingPid()
                        + ", uid=" + Binder.getCallingUid());
                return;
            }

            dumpInternal(pw, args);
        }
    }

    private final class LocalService extends BatteryManagerInternal {
        @Override
        public boolean isPowered(int plugTypeSet) {
            synchronized (mLock) {
                return isPoweredLocked(plugTypeSet);
            }
        }

        @Override
        public int getPlugType() {
            synchronized (mLock) {
                return mPlugType;
            }
        }

        @Override
        public int getBatteryLevel() {
            synchronized (mLock) {
                return mBatteryProps.batteryLevel;
            }
        }

        @Override
        public boolean getBatteryLevelLow() {
            synchronized (mLock) {
                return mBatteryLevelLow;
            }
        }

        @Override
        public int getInvalidCharger() {
            synchronized (mLock) {
                return mInvalidCharger;
            }
        }
    }

    class SettingsObserver extends ContentObserver {
        SettingsObserver(Handler handler) {
            super(handler);
        }

        void observe() {
            ContentResolver resolver = mContext.getContentResolver();

            // Battery light enabled
            resolver.registerContentObserver(Settings.System.getUriFor(
                    Settings.System.BATTERY_LIGHT_ENABLED), false, this, UserHandle.USER_ALL);

            // Low battery pulse
            resolver.registerContentObserver(Settings.System.getUriFor(
                    Settings.System.BATTERY_LIGHT_PULSE), false, this, UserHandle.USER_ALL);

            // Light colors
            if (mMultiColorLed) {
                // Register observer if we have a multi color led
                resolver.registerContentObserver(
                        Settings.System.getUriFor(Settings.System.BATTERY_LIGHT_LOW_COLOR),
                        false, this, UserHandle.USER_ALL);
                resolver.registerContentObserver(
                        Settings.System.getUriFor(Settings.System.BATTERY_LIGHT_MEDIUM_COLOR),
                        false, this, UserHandle.USER_ALL);
                resolver.registerContentObserver(
                        Settings.System.getUriFor(Settings.System.BATTERY_LIGHT_FULL_COLOR),
                        false, this, UserHandle.USER_ALL);
            }

            update();
        }

        @Override public void onChange(boolean selfChange) {
            update();
        }

        public void update() {
            ContentResolver resolver = mContext.getContentResolver();
            Resources res = mContext.getResources();

            // Battery light enabled
            mLightEnabled = Settings.System.getInt(resolver,
                    Settings.System.BATTERY_LIGHT_ENABLED, 1) != 0;

            // Low battery pulse
            mLedPulseEnabled = Settings.System.getInt(resolver,
                        Settings.System.BATTERY_LIGHT_PULSE, 1) != 0;

            // Light colors
            mBatteryLowARGB = Settings.System.getInt(resolver,
                    Settings.System.BATTERY_LIGHT_LOW_COLOR, res.getInteger(
                    com.android.internal.R.integer.config_notificationsBatteryLowARGB));
            mBatteryMediumARGB = Settings.System.getInt(resolver,
                    Settings.System.BATTERY_LIGHT_MEDIUM_COLOR, res.getInteger(
                    com.android.internal.R.integer.config_notificationsBatteryMediumARGB));
            mBatteryFullARGB = Settings.System.getInt(resolver,
                    Settings.System.BATTERY_LIGHT_FULL_COLOR, res.getInteger(
                    com.android.internal.R.integer.config_notificationsBatteryFullARGB));

            updateLedPulse();
        }
    }
}


File: services/core/java/com/android/server/am/BatteryStatsService.java
/*
 * Copyright (C) 2006-2007 The Android Open Source Project
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

package com.android.server.am;

import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothHeadset;
import android.bluetooth.BluetoothProfile;
import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.os.BatteryStats;
import android.os.Binder;
import android.os.Handler;
import android.os.IBinder;
import android.os.Parcel;
import android.os.ParcelFileDescriptor;
import android.os.PowerManagerInternal;
import android.os.Process;
import android.os.ServiceManager;
import android.os.SystemClock;
import android.os.UserHandle;
import android.os.WorkSource;
import android.telephony.SignalStrength;
import android.telephony.TelephonyManager;
import android.util.Slog;

import com.android.internal.app.IBatteryStats;
import com.android.internal.os.BatteryStatsHelper;
import com.android.internal.os.BatteryStatsImpl;
import com.android.internal.os.PowerProfile;
import com.android.server.LocalServices;

import java.io.File;
import java.io.FileDescriptor;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.List;

/**
 * All information we are collecting about things that can happen that impact
 * battery life.
 */
public final class BatteryStatsService extends IBatteryStats.Stub
        implements PowerManagerInternal.LowPowerModeListener {
    static final String TAG = "BatteryStatsService";

    static IBatteryStats sService;
    
    final BatteryStatsImpl mStats;
    Context mContext;
    private boolean mBluetoothPendingStats;
    private BluetoothHeadset mBluetoothHeadset;
    PowerManagerInternal mPowerManagerInternal;

    BatteryStatsService(File systemDir, Handler handler) {
        mStats = new BatteryStatsImpl(systemDir, handler);
    }
    
    public void publish(Context context) {
        mContext = context;
        ServiceManager.addService(BatteryStats.SERVICE_NAME, asBinder());
        mStats.setNumSpeedSteps(new PowerProfile(mContext).getNumSpeedSteps());
        mStats.setRadioScanningTimeout(mContext.getResources().getInteger(
                com.android.internal.R.integer.config_radioScanningTimeout)
                * 1000L);
    }

    /**
     * At the time when the constructor runs, the power manager has not yet been
     * initialized.  So we initialize the low power observer later.
     */
    public void initPowerManagement() {
        mPowerManagerInternal = LocalServices.getService(PowerManagerInternal.class);
        mPowerManagerInternal.registerLowPowerModeObserver(this);
        mStats.noteLowPowerMode(mPowerManagerInternal.getLowPowerModeEnabled());
        (new WakeupReasonThread()).start();
    }

    public void shutdown() {
        Slog.w("BatteryStats", "Writing battery stats before shutdown...");
        synchronized (mStats) {
            mStats.shutdownLocked();
        }
    }
    
    public static IBatteryStats getService() {
        if (sService != null) {
            return sService;
        }
        IBinder b = ServiceManager.getService(BatteryStats.SERVICE_NAME);
        sService = asInterface(b);
        return sService;
    }

    @Override
    public void onLowPowerModeChanged(boolean enabled) {
        synchronized (mStats) {
            mStats.noteLowPowerMode(enabled);
        }
    }

    /**
     * @return the current statistics object, which may be modified
     * to reflect events that affect battery usage.  You must lock the
     * stats object before doing anything with it.
     */
    public BatteryStatsImpl getActiveStatistics() {
        return mStats;
    }

    // These are for direct use by the activity manager...

    void addIsolatedUid(int isolatedUid, int appUid) {
        synchronized (mStats) {
            mStats.addIsolatedUidLocked(isolatedUid, appUid);
        }
    }

    void removeIsolatedUid(int isolatedUid, int appUid) {
        synchronized (mStats) {
            mStats.removeIsolatedUidLocked(isolatedUid, appUid);
        }
    }

    void noteProcessStart(String name, int uid) {
        synchronized (mStats) {
            mStats.noteProcessStartLocked(name, uid);
        }
    }

    void noteProcessCrash(String name, int uid) {
        synchronized (mStats) {
            mStats.noteProcessCrashLocked(name, uid);
        }
    }

    void noteProcessAnr(String name, int uid) {
        synchronized (mStats) {
            mStats.noteProcessAnrLocked(name, uid);
        }
    }

    void noteProcessState(String name, int uid, int state) {
        synchronized (mStats) {
            mStats.noteProcessStateLocked(name, uid, state);
        }
    }

    void noteProcessFinish(String name, int uid) {
        synchronized (mStats) {
            mStats.noteProcessFinishLocked(name, uid);
        }
    }

    // Public interface...

    public byte[] getStatistics() {
        mContext.enforceCallingPermission(
                android.Manifest.permission.BATTERY_STATS, null);
        //Slog.i("foo", "SENDING BATTERY INFO:");
        //mStats.dumpLocked(new LogPrinter(Log.INFO, "foo", Log.LOG_ID_SYSTEM));
        Parcel out = Parcel.obtain();
        mStats.writeToParcel(out, 0);
        byte[] data = out.marshall();
        out.recycle();
        return data;
    }

    public ParcelFileDescriptor getStatisticsStream() {
        mContext.enforceCallingPermission(
                android.Manifest.permission.BATTERY_STATS, null);
        //Slog.i("foo", "SENDING BATTERY INFO:");
        //mStats.dumpLocked(new LogPrinter(Log.INFO, "foo", Log.LOG_ID_SYSTEM));
        Parcel out = Parcel.obtain();
        mStats.writeToParcel(out, 0);
        byte[] data = out.marshall();
        out.recycle();
        try {
            return ParcelFileDescriptor.fromData(data, "battery-stats");
        } catch (IOException e) {
            Slog.w(TAG, "Unable to create shared memory", e);
            return null;
        }
    }

    public long computeBatteryTimeRemaining() {
        synchronized (mStats) {
            long time = mStats.computeBatteryTimeRemaining(SystemClock.elapsedRealtime());
            return time >= 0 ? (time/1000) : time;
        }
    }

    public long computeChargeTimeRemaining() {
        synchronized (mStats) {
            long time = mStats.computeChargeTimeRemaining(SystemClock.elapsedRealtime());
            return time >= 0 ? (time/1000) : time;
        }
    }

    public void noteEvent(int code, String name, int uid) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteEventLocked(code, name, uid);
        }
    }

    public void noteSyncStart(String name, int uid) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteSyncStartLocked(name, uid);
        }
    }

    public void noteSyncFinish(String name, int uid) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteSyncFinishLocked(name, uid);
        }
    }

    public void noteJobStart(String name, int uid) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteJobStartLocked(name, uid);
        }
    }

    public void noteJobFinish(String name, int uid) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteJobFinishLocked(name, uid);
        }
    }

    public void noteStartWakelock(int uid, int pid, String name, String historyName, int type,
            boolean unimportantForLogging) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteStartWakeLocked(uid, pid, name, historyName, type, unimportantForLogging,
                    SystemClock.elapsedRealtime(), SystemClock.uptimeMillis());
        }
    }

    public void noteStopWakelock(int uid, int pid, String name, String historyName, int type) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteStopWakeLocked(uid, pid, name, historyName, type,
                    SystemClock.elapsedRealtime(), SystemClock.uptimeMillis());
        }
    }

    public void noteStartWakelockFromSource(WorkSource ws, int pid, String name,
            String historyName, int type, boolean unimportantForLogging) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteStartWakeFromSourceLocked(ws, pid, name, historyName,
                    type, unimportantForLogging);
        }
    }

    public void noteChangeWakelockFromSource(WorkSource ws, int pid, String name,
            String historyName, int type, WorkSource newWs, int newPid, String newName,
            String newHistoryName, int newType, boolean newUnimportantForLogging) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteChangeWakelockFromSourceLocked(ws, pid, name, historyName, type,
                    newWs, newPid, newName, newHistoryName, newType, newUnimportantForLogging);
        }
    }

    public void noteStopWakelockFromSource(WorkSource ws, int pid, String name, String historyName,
            int type) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteStopWakeFromSourceLocked(ws, pid, name, historyName, type);
        }
    }

    public void noteStartSensor(int uid, int sensor) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteStartSensorLocked(uid, sensor);
        }
    }
    
    public void noteStopSensor(int uid, int sensor) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteStopSensorLocked(uid, sensor);
        }
    }
    
    public void noteVibratorOn(int uid, long durationMillis) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteVibratorOnLocked(uid, durationMillis);
        }
    }

    public void noteVibratorOff(int uid) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteVibratorOffLocked(uid);
        }
    }

    public void noteStartGps(int uid) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteStartGpsLocked(uid);
        }
    }
    
    public void noteStopGps(int uid) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteStopGpsLocked(uid);
        }
    }
        
    public void noteScreenState(int state) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteScreenStateLocked(state);
        }
    }
    
    public void noteScreenBrightness(int brightness) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteScreenBrightnessLocked(brightness);
        }
    }
    
    public void noteUserActivity(int uid, int event) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteUserActivityLocked(uid, event);
        }
    }
    
    public void noteInteractive(boolean interactive) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteInteractiveLocked(interactive);
        }
    }

    public void noteConnectivityChanged(int type, String extra) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteConnectivityChangedLocked(type, extra);
        }
    }

    public void noteMobileRadioPowerState(int powerState, long timestampNs) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteMobileRadioPowerState(powerState, timestampNs);
        }
    }

    public void notePhoneOn() {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.notePhoneOnLocked();
        }
    }
    
    public void notePhoneOff() {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.notePhoneOffLocked();
        }
    }
    
    public void notePhoneSignalStrength(SignalStrength signalStrength) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.notePhoneSignalStrengthLocked(signalStrength);
        }
    }
    
    public void notePhoneDataConnectionState(int dataType, boolean hasData) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.notePhoneDataConnectionStateLocked(dataType, hasData);
        }
    }

    public void notePhoneState(int state) {
        enforceCallingPermission();
        int simState = TelephonyManager.getDefault().getSimState();
        synchronized (mStats) {
            mStats.notePhoneStateLocked(state, simState);
        }
    }

    public void noteWifiOn() {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteWifiOnLocked();
        }
    }
    
    public void noteWifiOff() {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteWifiOffLocked();
        }
    }

    public void noteStartAudio(int uid) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteAudioOnLocked(uid);
        }
    }

    public void noteStopAudio(int uid) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteAudioOffLocked(uid);
        }
    }

    public void noteStartVideo(int uid) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteVideoOnLocked(uid);
        }
    }

    public void noteStopVideo(int uid) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteVideoOffLocked(uid);
        }
    }

    public void noteResetAudio() {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteResetAudioLocked();
        }
    }

    public void noteResetVideo() {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteResetVideoLocked();
        }
    }

    public void noteFlashlightOn() {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteFlashlightOnLocked();
        }
    }

    public void noteFlashlightOff() {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteFlashlightOffLocked();
        }
    }

    public void noteWifiRunning(WorkSource ws) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteWifiRunningLocked(ws);
        }
    }

    public void noteWifiRunningChanged(WorkSource oldWs, WorkSource newWs) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteWifiRunningChangedLocked(oldWs, newWs);
        }
    }

    public void noteWifiStopped(WorkSource ws) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteWifiStoppedLocked(ws);
        }
    }

    public void noteWifiState(int wifiState, String accessPoint) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteWifiStateLocked(wifiState, accessPoint);
        }
    }

    public void noteWifiSupplicantStateChanged(int supplState, boolean failedAuth) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteWifiSupplicantStateChangedLocked(supplState, failedAuth);
        }
    }

    public void noteWifiRssiChanged(int newRssi) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteWifiRssiChangedLocked(newRssi);
        }
    }

    public void noteBluetoothOn() {
        enforceCallingPermission();
        BluetoothAdapter adapter = BluetoothAdapter.getDefaultAdapter();
        if (adapter != null) {
            adapter.getProfileProxy(mContext, mBluetoothProfileServiceListener,
                                    BluetoothProfile.HEADSET);
        }
        synchronized (mStats) {
            if (mBluetoothHeadset != null) {
                mStats.noteBluetoothOnLocked();
                mStats.setBtHeadset(mBluetoothHeadset);
            } else {
                mBluetoothPendingStats = true;
            }
        }
    }

    private BluetoothProfile.ServiceListener mBluetoothProfileServiceListener =
        new BluetoothProfile.ServiceListener() {
        public void onServiceConnected(int profile, BluetoothProfile proxy) {
            mBluetoothHeadset = (BluetoothHeadset) proxy;
            synchronized (mStats) {
                if (mBluetoothPendingStats) {
                    mStats.noteBluetoothOnLocked();
                    mStats.setBtHeadset(mBluetoothHeadset);
                    mBluetoothPendingStats = false;
                }
            }
        }

        public void onServiceDisconnected(int profile) {
            mBluetoothHeadset = null;
        }
    };

    public void noteBluetoothOff() {
        enforceCallingPermission();
        synchronized (mStats) {
            mBluetoothPendingStats = false;
            mStats.noteBluetoothOffLocked();
        }
    }
    
    public void noteBluetoothState(int bluetoothState) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteBluetoothStateLocked(bluetoothState);
        }
    }

    public void noteFullWifiLockAcquired(int uid) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteFullWifiLockAcquiredLocked(uid);
        }
    }
    
    public void noteFullWifiLockReleased(int uid) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteFullWifiLockReleasedLocked(uid);
        }
    }

    public void noteWifiScanStarted(int uid) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteWifiScanStartedLocked(uid);
        }
    }

    public void noteWifiScanStopped(int uid) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteWifiScanStoppedLocked(uid);
        }
    }

    public void noteWifiMulticastEnabled(int uid) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteWifiMulticastEnabledLocked(uid);
        }
    }

    public void noteWifiMulticastDisabled(int uid) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteWifiMulticastDisabledLocked(uid);
        }
    }

    public void noteFullWifiLockAcquiredFromSource(WorkSource ws) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteFullWifiLockAcquiredFromSourceLocked(ws);
        }
    }

    public void noteFullWifiLockReleasedFromSource(WorkSource ws) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteFullWifiLockReleasedFromSourceLocked(ws);
        }
    }

    public void noteWifiScanStartedFromSource(WorkSource ws) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteWifiScanStartedFromSourceLocked(ws);
        }
    }

    public void noteWifiScanStoppedFromSource(WorkSource ws) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteWifiScanStoppedFromSourceLocked(ws);
        }
    }

    public void noteWifiBatchedScanStartedFromSource(WorkSource ws, int csph) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteWifiBatchedScanStartedFromSourceLocked(ws, csph);
        }
    }

    public void noteWifiBatchedScanStoppedFromSource(WorkSource ws) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteWifiBatchedScanStoppedFromSourceLocked(ws);
        }
    }

    public void noteWifiMulticastEnabledFromSource(WorkSource ws) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteWifiMulticastEnabledFromSourceLocked(ws);
        }
    }

    public void noteWifiMulticastDisabledFromSource(WorkSource ws) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteWifiMulticastDisabledFromSourceLocked(ws);
        }
    }

    @Override
    public void noteNetworkInterfaceType(String iface, int type) {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteNetworkInterfaceTypeLocked(iface, type);
        }
    }

    @Override
    public void noteNetworkStatsEnabled() {
        enforceCallingPermission();
        synchronized (mStats) {
            mStats.noteNetworkStatsEnabledLocked();
        }
    }

    public boolean isOnBattery() {
        return mStats.isOnBattery();
    }
    
    public void setBatteryState(int status, int health, int plugType, int level,
            int temp, int volt) {
        enforceCallingPermission();
        mStats.setBatteryState(status, health, plugType, level, temp, volt);
    }
    
    public long getAwakeTimeBattery() {
        mContext.enforceCallingOrSelfPermission(
                android.Manifest.permission.BATTERY_STATS, null);
        return mStats.getAwakeTimeBattery();
    }

    public long getAwakeTimePlugged() {
        mContext.enforceCallingOrSelfPermission(
                android.Manifest.permission.BATTERY_STATS, null);
        return mStats.getAwakeTimePlugged();
    }

    public void enforceCallingPermission() {
        if (Binder.getCallingPid() == Process.myPid()) {
            return;
        }
        mContext.enforcePermission(android.Manifest.permission.UPDATE_DEVICE_STATS,
                Binder.getCallingPid(), Binder.getCallingUid(), null);
    }

    final class WakeupReasonThread extends Thread {
        final int[] mIrqs = new int[32];
        final String[] mReasons = new String[32];

        WakeupReasonThread() {
            super("BatteryStats_wakeupReason");
        }

        public void run() {
            Process.setThreadPriority(Process.THREAD_PRIORITY_FOREGROUND);

            try {
                int num;
                while ((num=nativeWaitWakeup(mIrqs, mReasons)) >= 0) {
                    synchronized (mStats) {
                        if (num > 0) {
                            for (int i=0; i<num; i++) {
                                mStats.noteWakeupReasonLocked(mReasons[i]);
                            }
                        } else {
                            mStats.noteWakeupReasonLocked("unknown");
                        }
                    }
                }
            } catch (RuntimeException e) {
                Slog.e(TAG, "Failure reading wakeup reasons", e);
            }
        }
    }

    private static native int nativeWaitWakeup(int[] outIrqs, String[] outReasons);

    private void dumpHelp(PrintWriter pw) {
        pw.println("Battery stats (batterystats) dump options:");
        pw.println("  [--checkin] [--history] [--history-start] [--unplugged] [--charged] [-c]");
        pw.println("  [--reset] [--write] [-h] [<package.name>]");
        pw.println("  --checkin: format output for a checkin report.");
        pw.println("  --history: show only history data.");
        pw.println("  --history-start <num>: show only history data starting at given time offset.");
        pw.println("  --unplugged: only output data since last unplugged.");
        pw.println("  --charged: only output data since last charged.");
        pw.println("  --reset: reset the stats, clearing all current data.");
        pw.println("  --write: force write current collected stats to disk.");
        pw.println("  <package.name>: optional name of package to filter output by.");
        pw.println("  -h: print this help text.");
        pw.println("Battery stats (batterystats) commands:");
        pw.println("  enable|disable <option>");
        pw.println("    Enable or disable a running option.  Option state is not saved across boots.");
        pw.println("    Options are:");
        pw.println("      full-history: include additional detailed events in battery history:");
        pw.println("          wake_lock_in and proc events");
        pw.println("      no-auto-reset: don't automatically reset stats when unplugged");
    }

    private int doEnableOrDisable(PrintWriter pw, int i, String[] args, boolean enable) {
        i++;
        if (i >= args.length) {
            pw.println("Missing option argument for " + (enable ? "--enable" : "--disable"));
            dumpHelp(pw);
            return -1;
        }
        if ("full-wake-history".equals(args[i]) || "full-history".equals(args[i])) {
            synchronized (mStats) {
                mStats.setRecordAllHistoryLocked(enable);
            }
        } else if ("no-auto-reset".equals(args[i])) {
            synchronized (mStats) {
                mStats.setNoAutoReset(enable);
            }
        } else {
            pw.println("Unknown enable/disable option: " + args[i]);
            dumpHelp(pw);
            return -1;
        }
        return i;
    }

    @Override
    protected void dump(FileDescriptor fd, PrintWriter pw, String[] args) {
        if (mContext.checkCallingOrSelfPermission(android.Manifest.permission.DUMP)
                != PackageManager.PERMISSION_GRANTED) {
            pw.println("Permission Denial: can't dump BatteryStats from from pid="
                    + Binder.getCallingPid() + ", uid=" + Binder.getCallingUid()
                    + " without permission " + android.Manifest.permission.DUMP);
            return;
        }

        int flags = 0;
        boolean useCheckinFormat = false;
        boolean isRealCheckin = false;
        boolean noOutput = false;
        boolean writeData = false;
        long historyStart = -1;
        int reqUid = -1;
        if (args != null) {
            for (int i=0; i<args.length; i++) {
                String arg = args[i];
                if ("--checkin".equals(arg)) {
                    useCheckinFormat = true;
                    isRealCheckin = true;
                } else if ("--history".equals(arg)) {
                    flags |= BatteryStats.DUMP_HISTORY_ONLY;
                } else if ("--history-start".equals(arg)) {
                    flags |= BatteryStats.DUMP_HISTORY_ONLY;
                    i++;
                    if (i >= args.length) {
                        pw.println("Missing time argument for --history-since");
                        dumpHelp(pw);
                        return;
                    }
                    historyStart = Long.parseLong(args[i]);
                    writeData = true;
                } else if ("-c".equals(arg)) {
                    useCheckinFormat = true;
                    flags |= BatteryStats.DUMP_INCLUDE_HISTORY;
                } else if ("--unplugged".equals(arg)) {
                    flags |= BatteryStats.DUMP_UNPLUGGED_ONLY;
                } else if ("--charged".equals(arg)) {
                    flags |= BatteryStats.DUMP_CHARGED_ONLY;
                } else if ("--reset".equals(arg)) {
                    synchronized (mStats) {
                        mStats.resetAllStatsCmdLocked();
                        pw.println("Battery stats reset.");
                        noOutput = true;
                    }
                } else if ("--write".equals(arg)) {
                    synchronized (mStats) {
                        mStats.writeSyncLocked();
                        pw.println("Battery stats written.");
                        noOutput = true;
                    }
                } else if ("--enable".equals(arg) || "enable".equals(arg)) {
                    i = doEnableOrDisable(pw, i, args, true);
                    if (i < 0) {
                        return;
                    }
                    pw.println("Enabled: " + args[i]);
                    return;
                } else if ("--disable".equals(arg) || "disable".equals(arg)) {
                    i = doEnableOrDisable(pw, i, args, false);
                    if (i < 0) {
                        return;
                    }
                    pw.println("Disabled: " + args[i]);
                    return;
                } else if ("-h".equals(arg)) {
                    dumpHelp(pw);
                    return;
                } else if ("-a".equals(arg)) {
                    flags |= BatteryStats.DUMP_VERBOSE;
                } else if (arg.length() > 0 && arg.charAt(0) == '-'){
                    pw.println("Unknown option: " + arg);
                    dumpHelp(pw);
                    return;
                } else {
                    // Not an option, last argument must be a package name.
                    try {
                        reqUid = mContext.getPackageManager().getPackageUid(arg,
                                UserHandle.getCallingUserId());
                    } catch (PackageManager.NameNotFoundException e) {
                        pw.println("Unknown package: " + arg);
                        dumpHelp(pw);
                        return;
                    }
                }
            }
        }
        if (noOutput) {
            return;
        }
        if (BatteryStatsHelper.checkWifiOnly(mContext)) {
            flags |= BatteryStats.DUMP_DEVICE_WIFI_ONLY;
        }
        if (reqUid >= 0) {
            // By default, if the caller is only interested in a specific package, then
            // we only dump the aggregated data since charged.
            if ((flags&(BatteryStats.DUMP_HISTORY_ONLY|BatteryStats.DUMP_UNPLUGGED_ONLY
                    |BatteryStats.DUMP_CHARGED_ONLY)) == 0) {
                flags |= BatteryStats.DUMP_CHARGED_ONLY;
                // Also if they are doing -c, we don't want history.
                flags &= ~BatteryStats.DUMP_INCLUDE_HISTORY;
            }
        }
        if (useCheckinFormat) {
            List<ApplicationInfo> apps = mContext.getPackageManager().getInstalledApplications(0);
            if (isRealCheckin) {
                // For a real checkin, first we want to prefer to use the last complete checkin
                // file if there is one.
                synchronized (mStats.mCheckinFile) {
                    if (mStats.mCheckinFile.exists()) {
                        try {
                            byte[] raw = mStats.mCheckinFile.readFully();
                            if (raw != null) {
                                Parcel in = Parcel.obtain();
                                in.unmarshall(raw, 0, raw.length);
                                in.setDataPosition(0);
                                BatteryStatsImpl checkinStats = new BatteryStatsImpl(
                                        null, mStats.mHandler);
                                checkinStats.readSummaryFromParcel(in);
                                in.recycle();
                                checkinStats.dumpCheckinLocked(mContext, pw, apps, flags,
                                        historyStart);
                                mStats.mCheckinFile.delete();
                                return;
                            }
                        } catch (IOException e) {
                            Slog.w(TAG, "Failure reading checkin file "
                                    + mStats.mCheckinFile.getBaseFile(), e);
                        }
                    }
                }
            }
            synchronized (mStats) {
                mStats.dumpCheckinLocked(mContext, pw, apps, flags, historyStart);
                if (writeData) {
                    mStats.writeAsyncLocked();
                }
            }
        } else {
            synchronized (mStats) {
                mStats.dumpLocked(mContext, pw, flags, reqUid, historyStart);
                if (writeData) {
                    mStats.writeAsyncLocked();
                }
            }
        }
    }
}
