Refactoring Types: ['Move Class']
onnector/ConnectorFactory.java
package cgeo.geocaching.connector;

import cgeo.geocaching.Geocache;
import cgeo.geocaching.R;
import cgeo.geocaching.SearchResult;
import cgeo.geocaching.Trackable;
import cgeo.geocaching.connector.capability.ILogin;
import cgeo.geocaching.connector.capability.ISearchByCenter;
import cgeo.geocaching.connector.capability.ISearchByFinder;
import cgeo.geocaching.connector.capability.ISearchByKeyword;
import cgeo.geocaching.connector.capability.ISearchByNextPage;
import cgeo.geocaching.connector.capability.ISearchByOwner;
import cgeo.geocaching.connector.capability.ISearchByViewPort;
import cgeo.geocaching.connector.ec.ECConnector;
import cgeo.geocaching.connector.gc.GCConnector;
import cgeo.geocaching.connector.gc.MapTokens;
import cgeo.geocaching.connector.oc.OCApiConnector.ApiSupport;
import cgeo.geocaching.connector.oc.OCApiLiveConnector;
import cgeo.geocaching.connector.oc.OCCZConnector;
import cgeo.geocaching.connector.oc.OCConnector;
import cgeo.geocaching.connector.ox.OXConnector;
import cgeo.geocaching.connector.trackable.GeokretyConnector;
import cgeo.geocaching.connector.trackable.SwaggieConnector;
import cgeo.geocaching.connector.trackable.TrackableConnector;
import cgeo.geocaching.connector.trackable.TravelBugConnector;
import cgeo.geocaching.connector.trackable.UnknownTrackableConnector;
import cgeo.geocaching.location.Viewport;

import org.apache.commons.lang3.StringUtils;
import org.eclipse.jdt.annotation.NonNull;
import org.eclipse.jdt.annotation.Nullable;

import rx.functions.Func1;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.List;

public final class ConnectorFactory {
    @NonNull private static final UnknownConnector UNKNOWN_CONNECTOR = new UnknownConnector();
    @NonNull private static final Collection<IConnector> CONNECTORS = Collections.unmodifiableCollection(Arrays.<IConnector> asList(
            GCConnector.getInstance(),
            ECConnector.getInstance(),
            new OCApiLiveConnector("opencaching.de", "www.opencaching.de", "OC", "CC BY-NC-ND, alle Logeinträge © jeweiliger Autor",
                    R.string.oc_de_okapi_consumer_key, R.string.oc_de_okapi_consumer_secret,
                    R.string.pref_connectorOCActive, R.string.pref_ocde_tokenpublic, R.string.pref_ocde_tokensecret, ApiSupport.current),
            new OCCZConnector(),
            new OCApiLiveConnector("opencaching.org.uk", "www.opencaching.org.uk", "OK", "CC BY-NC-SA 2.5",
                    R.string.oc_uk_okapi_consumer_key, R.string.oc_uk_okapi_consumer_secret,
                    R.string.pref_connectorOCUKActive, R.string.pref_ocuk_tokenpublic, R.string.pref_ocuk_tokensecret, ApiSupport.oldapi),
            new OCConnector("OpenCaching.ES", "www.opencachingspain.es", "OC"),
            new OCConnector("OpenCaching.IT", "www.opencaching.it", "OC"),
            new OCConnector("OpenCaching.JP", "www.opencaching.jp", "OJ"),
            new OCConnector("OpenCaching.NO/SE", "www.opencaching.se", "OS"),
            new OCApiLiveConnector("opencaching.nl", "www.opencaching.nl", "OB", "CC BY-SA 3.0",
                    R.string.oc_nl_okapi_consumer_key, R.string.oc_nl_okapi_consumer_secret,
                    R.string.pref_connectorOCNLActive, R.string.pref_ocnl_tokenpublic, R.string.pref_ocnl_tokensecret, ApiSupport.current),
            new OCApiLiveConnector("opencaching.pl", "www.opencaching.pl", "OP", "CC BY-SA 3.0",
                    R.string.oc_pl_okapi_consumer_key, R.string.oc_pl_okapi_consumer_secret,
                    R.string.pref_connectorOCPLActive, R.string.pref_ocpl_tokenpublic, R.string.pref_ocpl_tokensecret, ApiSupport.current),
            new OCApiLiveConnector("opencaching.us", "www.opencaching.us", "OU", "CC BY-NC-SA 2.5",
                    R.string.oc_us_okapi_consumer_key, R.string.oc_us_okapi_consumer_secret,
                    R.string.pref_connectorOCUSActive, R.string.pref_ocus_tokenpublic, R.string.pref_ocus_tokensecret, ApiSupport.current),
            new OCApiLiveConnector("opencaching.ro", "www.opencaching.ro", "OR", "CC BY-SA 3.0",
                    R.string.oc_ro_okapi_consumer_key, R.string.oc_ro_okapi_consumer_secret,
                    R.string.pref_connectorOCROActive, R.string.pref_ocro_tokenpublic, R.string.pref_ocro_tokensecret, ApiSupport.current),
            new OXConnector(),
            new GeocachingAustraliaConnector(),
            new GeopeitusConnector(),
            new TerraCachingConnector(),
            new WaymarkingConnector(),
            UNKNOWN_CONNECTOR // the unknown connector MUST be the last one
    ));

    @NonNull public static final UnknownTrackableConnector UNKNOWN_TRACKABLE_CONNECTOR = new UnknownTrackableConnector();

    @NonNull
    private static final Collection<TrackableConnector> TRACKABLE_CONNECTORS = Collections.unmodifiableCollection(Arrays.<TrackableConnector> asList(
            new GeokretyConnector(),
            new SwaggieConnector(),
            TravelBugConnector.getInstance(), // travel bugs last, as their secret codes overlap with other connectors
            UNKNOWN_TRACKABLE_CONNECTOR // must be last
    ));

    @NonNull
    private static final Collection<ISearchByViewPort> searchByViewPortConns = getMatchingConnectors(ISearchByViewPort.class);

    @NonNull
    private static final Collection<ISearchByCenter> searchByCenterConns = getMatchingConnectors(ISearchByCenter.class);

    @NonNull
    private static final Collection<ISearchByNextPage> searchByNextPageConns = getMatchingConnectors(ISearchByNextPage.class);

    @NonNull
    private static final Collection<ISearchByKeyword> searchByKeywordConns = getMatchingConnectors(ISearchByKeyword.class);

    @NonNull
    private static final Collection<ISearchByOwner> SEARCH_BY_OWNER_CONNECTORS = getMatchingConnectors(ISearchByOwner.class);

    @NonNull
    private static final Collection<ISearchByFinder> SEARCH_BY_FINDER_CONNECTORS = getMatchingConnectors(ISearchByFinder.class);

    @NonNull
    @SuppressWarnings("unchecked")
    private static <T extends IConnector> Collection<T> getMatchingConnectors(final Class<T> clazz) {
        final List<T> matching = new ArrayList<>();
        for (final IConnector connector : CONNECTORS) {
            if (clazz.isInstance(connector)) {
                matching.add((T) connector);
            }
        }
        return Collections.unmodifiableCollection(matching);
    }

    @NonNull
    public static Collection<IConnector> getConnectors() {
        return CONNECTORS;
    }

    @NonNull
    public static Collection<ISearchByCenter> getSearchByCenterConnectors() {
        return searchByCenterConns;
    }

    @NonNull
    public static Collection<ISearchByNextPage> getSearchByNextPageConnectors() {
        return searchByNextPageConns;
    }

    @NonNull
    public static Collection<ISearchByKeyword> getSearchByKeywordConnectors() {
        return searchByKeywordConns;
    }

    @NonNull
    public static Collection<ISearchByOwner> getSearchByOwnerConnectors() {
        return SEARCH_BY_OWNER_CONNECTORS;
    }

    @NonNull
    public static Collection<ISearchByFinder> getSearchByFinderConnectors() {
        return SEARCH_BY_FINDER_CONNECTORS;
    }

    @NonNull
    public static ILogin[] getActiveLiveConnectors() {
        final List<ILogin> liveConns = new ArrayList<>();
        for (final IConnector conn : CONNECTORS) {
            if (conn instanceof ILogin && conn.isActive()) {
                liveConns.add((ILogin) conn);
            }
        }
        return liveConns.toArray(new ILogin[liveConns.size()]);
    }

    public static boolean canHandle(final @Nullable String geocode) {
        if (geocode == null) {
            return false;
        }
        if (isInvalidGeocode(geocode)) {
            return false;
        }
        for (final IConnector connector : CONNECTORS) {
            if (connector.canHandle(geocode)) {
                return true;
            }
        }
        return false;
    }

    @NonNull
    public static IConnector getConnector(final Geocache cache) {
        return getConnector(cache.getGeocode());
    }

    @NonNull
    public static TrackableConnector getConnector(final Trackable trackable) {
        return getTrackableConnector(trackable.getGeocode());
    }

    @NonNull
    public static TrackableConnector getTrackableConnector(final String geocode) {
        for (final TrackableConnector connector : TRACKABLE_CONNECTORS) {
            if (connector.canHandleTrackable(geocode)) {
                return connector;
            }
        }
        return UNKNOWN_TRACKABLE_CONNECTOR; // avoid null checks by returning a non implementing connector
    }

    public static List<TrackableConnector> getGenericTrackablesConnectors() {
        final List<TrackableConnector> trackableConnectors = new ArrayList<>();
        for (final TrackableConnector connector : TRACKABLE_CONNECTORS) {
            if (connector.isGenericLoggable() && connector.isActive()) {
                trackableConnectors.add(connector);
            }
        }
        return trackableConnectors;
    }

    @NonNull
    public static IConnector getConnector(final String geocodeInput) {
        // this may come from user input
        final String geocode = StringUtils.trim(geocodeInput);
        if (geocode == null) {
            return UNKNOWN_CONNECTOR;
        }
        if (isInvalidGeocode(geocode)) {
            return UNKNOWN_CONNECTOR;
        }
        for (final IConnector connector : CONNECTORS) {
            if (connector.canHandle(geocode)) {
                return connector;
            }
        }
        // in case of errors, take UNKNOWN to avoid null checks everywhere
        return UNKNOWN_CONNECTOR;
    }

    /**
     * Obtain the connector by it's name.
     * If connector is not found, return UNKNOWN_CONNECTOR.
     *
     * @param connectorName
     *          connector name String
     * @return
     *          The connector matching name
     */
    @NonNull
    public static IConnector getConnectorByName(final String connectorName) {
        for (final IConnector connector : CONNECTORS) {
            if (StringUtils.equals(connectorName, connector.getName())) {
                return connector;
            }
        }
        // in case of errors, take UNKNOWN to avoid null checks everywhere
        return UNKNOWN_CONNECTOR;
    }

    private static boolean isInvalidGeocode(final String geocode) {
        return StringUtils.isBlank(geocode) || !Character.isLetterOrDigit(geocode.charAt(0));
    }

    /** @see ISearchByViewPort#searchByViewport */
    @NonNull
    public static SearchResult searchByViewport(final @NonNull Viewport viewport, @NonNull final MapTokens tokens) {
        return SearchResult.parallelCombineActive(searchByViewPortConns, new Func1<ISearchByViewPort, SearchResult>() {
            @Override
            public SearchResult call(final ISearchByViewPort connector) {
                return connector.searchByViewport(viewport, tokens);
            }
        });
    }

    @Nullable
    public static String getGeocodeFromURL(@Nullable final String url) {
        if (url == null) {
            return null;
        }
        for (final IConnector connector : CONNECTORS) {
            @Nullable final String geocode = connector.getGeocodeFromUrl(url);
            if (StringUtils.isNotBlank(geocode)) {
                return StringUtils.upperCase(geocode);
            }
        }
        return null;
    }

    @NonNull
    public static Collection<TrackableConnector> getTrackableConnectors() {
        return TRACKABLE_CONNECTORS;
    }

    /**
     * Get the geocode of a trackable from a URL.
     *
     * @return {@code null} if the URL cannot be decoded
     */
    @Nullable
    public static String getTrackableFromURL(final String url) {
        if (url == null) {
            return null;
        }
        for (final TrackableConnector connector : TRACKABLE_CONNECTORS) {
            final String geocode = connector.getTrackableCodeFromUrl(url);
            if (StringUtils.isNotBlank(geocode)) {
                return geocode;
            }
        }
        return null;
    }

}


File: main/src/cgeo/geocaching/files/GPXParser.java
package cgeo.geocaching.files;

import cgeo.geocaching.CgeoApplication;
import cgeo.geocaching.DataStore;
import cgeo.geocaching.Geocache;
import cgeo.geocaching.LogEntry;
import cgeo.geocaching.R;
import cgeo.geocaching.Trackable;
import cgeo.geocaching.Waypoint;
import cgeo.geocaching.connector.ConnectorFactory;
import cgeo.geocaching.connector.IConnector;
import cgeo.geocaching.connector.capability.ILogin;
import cgeo.geocaching.enumerations.CacheSize;
import cgeo.geocaching.enumerations.CacheType;
import cgeo.geocaching.enumerations.LoadFlags;
import cgeo.geocaching.enumerations.LoadFlags.LoadFlag;
import cgeo.geocaching.enumerations.LoadFlags.RemoveFlag;
import cgeo.geocaching.enumerations.LoadFlags.SaveFlag;
import cgeo.geocaching.enumerations.LogType;
import cgeo.geocaching.enumerations.WaypointType;
import cgeo.geocaching.list.StoredList;
import cgeo.geocaching.location.Geopoint;
import cgeo.geocaching.utils.CancellableHandler;
import cgeo.geocaching.utils.Log;
import cgeo.geocaching.utils.MatcherWrapper;
import cgeo.geocaching.utils.SynchronizedDateFormat;

import org.apache.commons.lang3.CharEncoding;
import org.apache.commons.lang3.StringUtils;
import org.eclipse.jdt.annotation.NonNull;
import org.eclipse.jdt.annotation.Nullable;
import org.xml.sax.Attributes;
import org.xml.sax.SAXException;

import android.sax.Element;
import android.sax.EndElementListener;
import android.sax.EndTextElementListener;
import android.sax.RootElement;
import android.sax.StartElementListener;
import android.util.Xml;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.text.ParseException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Date;
import java.util.EnumSet;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;

public abstract class GPXParser extends FileParser {

    private static final SynchronizedDateFormat formatSimple = new SynchronizedDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US); // 2010-04-20T07:00:00
    private static final SynchronizedDateFormat formatSimpleZ = new SynchronizedDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US); // 2010-04-20T07:00:00Z
    private static final SynchronizedDateFormat formatTimezone = new SynchronizedDateFormat("yyyy-MM-dd'T'HH:mm:ssZ", Locale.US); // 2010-04-20T01:01:03-04:00

    /**
     * Attention: case sensitive geocode pattern to avoid matching normal words in the name or description of the cache.
     */
    private static final Pattern PATTERN_GEOCODE = Pattern.compile("([0-9A-Z]{2,})");
    private static final Pattern PATTERN_GUID = Pattern.compile(".*" + Pattern.quote("guid=") + "([0-9a-z\\-]+)", Pattern.CASE_INSENSITIVE);
    private static final Pattern PATTERN_URL_GEOCODE = Pattern.compile(".*" + Pattern.quote("wp=") + "([A-Z][0-9A-Z]+)", Pattern.CASE_INSENSITIVE);
    /**
     * supported groundspeak extensions of the GPX format
     */
    private static final String[] GROUNDSPEAK_NAMESPACE = {
            "http://www.groundspeak.com/cache/1/1", // PQ 1.1
            "http://www.groundspeak.com/cache/1/0/1", // PQ 1.0.1
            "http://www.groundspeak.com/cache/1/0", // PQ 1.0
    };

    /**
     * supported GSAK extension of the GPX format
     */
    private static final String[] GSAK_NS = {
            "http://www.gsak.net/xmlv1/4",
            "http://www.gsak.net/xmlv1/5",
            "http://www.gsak.net/xmlv1/6"
    };
    /**
     * c:geo extensions of the gpx format
     */
    private static final String CGEO_NS = "http://www.cgeo.org/wptext/1/0";

    private static final Pattern PATTERN_MILLISECONDS = Pattern.compile("\\.\\d{3,7}");

    private int listId = StoredList.STANDARD_LIST_ID;
    final protected String namespace;
    final private String version;

    private Geocache cache;
    private Trackable trackable = new Trackable();
    private LogEntry log = null;

    private String type = null;
    private String sym = null;
    private String name = null;
    private String cmt = null;
    private String desc = null;
    protected final String[] userData = new String[5]; // take 5 cells, that makes indexing 1..4 easier
    private String parentCacheCode = null;
    private boolean wptVisited = false;
    private boolean wptUserDefined = false;
    private List<LogEntry> logs = new ArrayList<>();

    /**
     * Parser result. Maps geocode to cache.
     */
    private final Set<String> result = new HashSet<>(100);
    private ProgressInputStream progressStream;
    /**
     * URL contained in the header of the GPX file. Used to guess where the file is coming from.
     */
    protected String scriptUrl;
    /**
     * original longitude in case of modified coordinates
     */
    @Nullable protected String originalLon;
    /**
     * original latitude in case of modified coordinates
     */
    @Nullable protected String originalLat;

    private final class UserDataListener implements EndTextElementListener {
        private final int index;

        public UserDataListener(final int index) {
            this.index = index;
        }

        @Override
        public void end(final String user) {
            userData[index] = validate(user);
        }
    }

    private static final class CacheAttributeTranslator {
        // List of cache attributes matching IDs used in GPX files.
        // The ID is represented by the position of the String in the array.
        // Strings are not used as text but as resource IDs of strings, just to be aware of changes
        // made in strings.xml which then will lead to compile errors here and not to runtime errors.
        private static final int[] CACHE_ATTRIBUTES = {
                -1, // 0
                R.string.attribute_dogs_yes, // 1
                R.string.attribute_fee_yes, // 2
                R.string.attribute_rappelling_yes, // 3
                R.string.attribute_boat_yes, // 4
                R.string.attribute_scuba_yes, // 5
                R.string.attribute_kids_yes, // 6
                R.string.attribute_onehour_yes, // 7
                R.string.attribute_scenic_yes, // 8
                R.string.attribute_hiking_yes, // 9
                R.string.attribute_climbing_yes, // 10
                R.string.attribute_wading_yes, // 11
                R.string.attribute_swimming_yes, // 12
                R.string.attribute_available_yes, // 13
                R.string.attribute_night_yes, // 14
                R.string.attribute_winter_yes, // 15
                -1, // 16
                R.string.attribute_poisonoak_yes, // 17
                R.string.attribute_dangerousanimals_yes, // 18
                R.string.attribute_ticks_yes, // 19
                R.string.attribute_mine_yes, // 20
                R.string.attribute_cliff_yes, // 21
                R.string.attribute_hunting_yes, // 22
                R.string.attribute_danger_yes, // 23
                R.string.attribute_wheelchair_yes, // 24
                R.string.attribute_parking_yes, // 25
                R.string.attribute_public_yes, // 26
                R.string.attribute_water_yes, // 27
                R.string.attribute_restrooms_yes, // 28
                R.string.attribute_phone_yes, // 29
                R.string.attribute_picnic_yes, // 30
                R.string.attribute_camping_yes, // 31
                R.string.attribute_bicycles_yes, // 32
                R.string.attribute_motorcycles_yes, // 33
                R.string.attribute_quads_yes, // 34
                R.string.attribute_jeeps_yes, // 35
                R.string.attribute_snowmobiles_yes, // 36
                R.string.attribute_horses_yes, // 37
                R.string.attribute_campfires_yes, // 38
                R.string.attribute_thorn_yes, // 39
                R.string.attribute_stealth_yes, // 40
                R.string.attribute_stroller_yes, // 41
                R.string.attribute_firstaid_yes, // 42
                R.string.attribute_cow_yes, // 43
                R.string.attribute_flashlight_yes, // 44
                R.string.attribute_landf_yes, // 45
                R.string.attribute_rv_yes, // 46
                R.string.attribute_field_puzzle_yes, // 47
                R.string.attribute_uv_yes, // 48
                R.string.attribute_snowshoes_yes, // 49
                R.string.attribute_skiis_yes, // 50
                R.string.attribute_s_tool_yes, // 51
                R.string.attribute_nightcache_yes, // 52
                R.string.attribute_parkngrab_yes, // 53
                R.string.attribute_abandonedbuilding_yes, // 54
                R.string.attribute_hike_short_yes, // 55
                R.string.attribute_hike_med_yes, // 56
                R.string.attribute_hike_long_yes, // 57
                R.string.attribute_fuel_yes, // 58
                R.string.attribute_food_yes, // 59
                R.string.attribute_wirelessbeacon_yes, // 60
                R.string.attribute_partnership_yes, // 61
                R.string.attribute_seasonal_yes, // 62
                R.string.attribute_touristok_yes, // 63
                R.string.attribute_treeclimbing_yes, // 64
                R.string.attribute_frontyard_yes, // 65
                R.string.attribute_teamwork_yes, // 66
                R.string.attribute_geotour_yes, // 67
        };
        private static final String YES = "_yes";
        private static final String NO = "_no";
        private static final Pattern BASENAME_PATTERN = Pattern.compile("^.*attribute_(.*)(_yes|_no)");

        // map GPX-Attribute-Id to baseName
        public static String getBaseName(final int id) {
            if (id < 0) {
                return null;
            }
            // get String out of array
            if (CACHE_ATTRIBUTES.length <= id) {
                return null;
            }
            final int stringId = CACHE_ATTRIBUTES[id];
            if (stringId == -1) {
                return null; // id not found
            }
            // get text for string
            final String stringName;
            try {
                stringName = CgeoApplication.getInstance().getResources().getResourceName(stringId);
            } catch (final NullPointerException ignored) {
                return null;
            }
            if (stringName == null) {
                return null;
            }
            // cut out baseName
            final MatcherWrapper m = new MatcherWrapper(BASENAME_PATTERN, stringName);
            if (!m.matches()) {
                return null;
            }
            return m.group(1);
        }

        // @return  baseName + "_yes" or "_no" e.g. "food_no" or "uv_yes"
        public static String getInternalId(final int attributeId, final boolean active) {
            final String baseName = getBaseName(attributeId);
            if (baseName == null) {
                return null;
            }
            return baseName + (active ? YES : NO);
        }
    }

    protected GPXParser(final int listIdIn, final String namespaceIn, final String versionIn) {
        listId = listIdIn;
        namespace = namespaceIn;
        version = versionIn;
    }

    static Date parseDate(final String inputUntrimmed) throws ParseException {
        // remove milliseconds to reduce number of needed patterns
        final MatcherWrapper matcher = new MatcherWrapper(PATTERN_MILLISECONDS, inputUntrimmed.trim());
        final String input = matcher.replaceFirst("");
        if (input.contains("Z")) {
            return formatSimpleZ.parse(input);
        }
        if (StringUtils.countMatches(input, ":") == 3) {
            final String removeColon = input.substring(0, input.length() - 3) + input.substring(input.length() - 2);
            return formatTimezone.parse(removeColon);
        }
        return formatSimple.parse(input);
    }

    @Override
    @NonNull
    public Collection<Geocache> parse(@NonNull final InputStream stream, @Nullable final CancellableHandler progressHandler) throws IOException, ParserException {
        resetCache();
        final RootElement root = new RootElement(namespace, "gpx");
        final Element waypoint = root.getChild(namespace, "wpt");

        root.getChild(namespace, "url").setEndTextElementListener(new EndTextElementListener() {

            @Override
            public void end(final String body) {
                scriptUrl = body;
            }
        });

        // waypoint - attributes
        waypoint.setStartElementListener(new StartElementListener() {

            @Override
            public void start(final Attributes attrs) {
                try {
                    if (attrs.getIndex("lat") > -1 && attrs.getIndex("lon") > -1) {
                        final String latitude = attrs.getValue("lat");
                        final String longitude = attrs.getValue("lon");
                        // latitude and longitude are required attributes, but we export them empty for waypoints without coordinates
                        if (StringUtils.isNotBlank(latitude) && StringUtils.isNotBlank(longitude)) {
                            cache.setCoords(new Geopoint(Double.parseDouble(latitude),
                                    Double.parseDouble(longitude)));
                        }
                    }
                } catch (final NumberFormatException e) {
                    Log.w("Failed to parse waypoint's latitude and/or longitude", e);
                }
            }
        });

        // waypoint
        waypoint.setEndElementListener(new EndElementListener() {

            @Override
            public void end() {
                // try to find geocode somewhere else
                if (StringUtils.isBlank(cache.getGeocode())) {
                    findGeoCode(name);
                    findGeoCode(desc);
                    findGeoCode(cmt);
                }
                // take the name as code, if nothing else is available
                if (StringUtils.isBlank(cache.getGeocode())) {
                    if (StringUtils.isNotBlank(name)) {
                        cache.setGeocode(name.trim());
                    }
                }

                if (isValidForImport()) {
                    fixCache(cache);
                    cache.setListId(listId);
                    cache.setDetailed(true);

                    createNoteFromGSAKUserdata();

                    final String geocode = cache.getGeocode();
                    if (result.contains(geocode)) {
                        Log.w("Duplicate geocode during GPX import: " + geocode);
                    }
                    // modify cache depending on the use case/connector
                    afterParsing(cache);

                    // finally store the cache in the database
                    result.add(geocode);
                    DataStore.saveCache(cache, EnumSet.of(SaveFlag.DB));
                    DataStore.saveLogs(cache.getGeocode(), logs);

                    // avoid the cachecache using lots of memory for caches which the user did not actually look at
                    DataStore.removeCache(geocode, EnumSet.of(RemoveFlag.CACHE));
                    showProgressMessage(progressHandler, progressStream.getProgress());
                } else if (StringUtils.isNotBlank(cache.getName())
                        && StringUtils.containsIgnoreCase(type, "waypoint")) {
                    addWaypointToCache();
                }

                resetCache();
            }

            private void addWaypointToCache() {
                fixCache(cache);

                if (cache.getName().length() > 2 || StringUtils.isNotBlank(parentCacheCode)) {
                    if (StringUtils.isBlank(parentCacheCode)) {
                        if (StringUtils.containsIgnoreCase(scriptUrl, "extremcaching")) {
                            parentCacheCode = cache.getName().substring(2);
                        }
                        else {
                            parentCacheCode = "GC" + cache.getName().substring(2).toUpperCase(Locale.US);
                        }
                    }
                    final Geocache cacheForWaypoint = findParentCache();
                    if (cacheForWaypoint != null) {
                        final Waypoint waypoint = new Waypoint(cache.getShortDescription(), WaypointType.fromGPXString(sym), false);
                        if (wptUserDefined) {
                            waypoint.setUserDefined();
                        }
                        waypoint.setId(-1);
                        waypoint.setGeocode(parentCacheCode);
                        waypoint.setPrefix(cacheForWaypoint.getWaypointPrefix(cache.getName()));
                        waypoint.setLookup("---");
                        // there is no lookup code in gpx file
                        waypoint.setCoords(cache.getCoords());
                        waypoint.setNote(cache.getDescription());
                        waypoint.setVisited(wptVisited);
                        final List<Waypoint> mergedWayPoints = new ArrayList<>();
                        mergedWayPoints.addAll(cacheForWaypoint.getWaypoints());

                        final List<Waypoint> newPoints = new ArrayList<>();
                        newPoints.add(waypoint);
                        Waypoint.mergeWayPoints(newPoints, mergedWayPoints, true);
                        cacheForWaypoint.setWaypoints(newPoints, false);
                        DataStore.saveCache(cacheForWaypoint, EnumSet.of(SaveFlag.DB));
                        showProgressMessage(progressHandler, progressStream.getProgress());
                    }
                }
            }

        });

        // waypoint.time
        waypoint.getChild(namespace, "time").setEndTextElementListener(new EndTextElementListener() {

            @Override
            public void end(final String body) {
                try {
                    cache.setHidden(parseDate(body));
                } catch (final Exception e) {
                    Log.w("Failed to parse cache date", e);
                }
            }
        });

        // waypoint.name
        waypoint.getChild(namespace, "name").setEndTextElementListener(new EndTextElementListener() {

            @Override
            public void end(final String body) {
                name = body;

                String content = body.trim();

                // extremcaching.com manipulates the GC code by adding GC in front of ECxxx
                if (StringUtils.startsWithIgnoreCase(content, "GCEC") && StringUtils.containsIgnoreCase(scriptUrl, "extremcaching")) {
                    content = content.substring(2);
                }

                cache.setName(content);

                findGeoCode(cache.getName());
            }
        });

        // waypoint.desc
        waypoint.getChild(namespace, "desc").setEndTextElementListener(new EndTextElementListener() {

            @Override
            public void end(final String body) {
                desc = body;

                cache.setShortDescription(validate(body));
            }
        });

        // waypoint.cmt
        waypoint.getChild(namespace, "cmt").setEndTextElementListener(new EndTextElementListener() {

            @Override
            public void end(final String body) {
                cmt = body;

                cache.setDescription(validate(body));
            }
        });

        // waypoint.getType()
        waypoint.getChild(namespace, "type").setEndTextElementListener(new EndTextElementListener() {

            @Override
            public void end(final String body) {
                final String[] content = StringUtils.split(body, '|');
                if (content.length > 0) {
                    type = content[0].toLowerCase(Locale.US).trim();
                }
            }
        });

        // waypoint.sym
        waypoint.getChild(namespace, "sym").setEndTextElementListener(new EndTextElementListener() {

            @Override
            public void end(final String body) {
                sym = body.toLowerCase(Locale.US);
                if (sym.contains("geocache") && sym.contains("found")) {
                    cache.setFound(true);
                }
            }
        });

        // waypoint.url
        waypoint.getChild(namespace, "url").setEndTextElementListener(new EndTextElementListener() {

            @Override
            public void end(final String url) {
                final MatcherWrapper matcher = new MatcherWrapper(PATTERN_GUID, url);
                if (matcher.matches()) {
                    final String guid = matcher.group(1);
                    if (StringUtils.isNotBlank(guid)) {
                        cache.setGuid(guid);
                    }
                }
                final MatcherWrapper matcherCode = new MatcherWrapper(PATTERN_URL_GEOCODE, url);
                if (matcherCode.matches()) {
                    final String geocode = matcherCode.group(1);
                    cache.setGeocode(geocode);
                }
            }
        });

        // waypoint.urlname (name for waymarks)
        waypoint.getChild(namespace, "urlname").setEndTextElementListener(new EndTextElementListener() {

            @Override
            public void end(final String urlName) {
                if (cache.getName().equals(cache.getGeocode()) && StringUtils.startsWith(cache.getGeocode(), "WM")) {
                    cache.setName(StringUtils.trim(urlName));
                }
            }
        });

        // for GPX 1.0, cache info comes from waypoint node (so called private children,
        // for GPX 1.1 from extensions node
        final Element cacheParent = getCacheParent(waypoint);

        registerGsakExtensions(cacheParent);
        registerTerraCachingExtensions(cacheParent);
        registerCgeoExtensions(cacheParent);

        // 3 different versions of the GC schema
        for (final String nsGC : GROUNDSPEAK_NAMESPACE) {
            // waypoints.cache
            final Element gcCache = cacheParent.getChild(nsGC, "cache");

            gcCache.setStartElementListener(new StartElementListener() {

                @Override
                public void start(final Attributes attrs) {
                    try {
                        if (attrs.getIndex("id") > -1) {
                            cache.setCacheId(attrs.getValue("id"));
                        }
                        if (attrs.getIndex("archived") > -1) {
                            cache.setArchived(attrs.getValue("archived").equalsIgnoreCase("true"));
                        }
                        if (attrs.getIndex("available") > -1) {
                            cache.setDisabled(!attrs.getValue("available").equalsIgnoreCase("true"));
                        }
                    } catch (final RuntimeException e) {
                        Log.w("Failed to parse cache attributes", e);
                    }
                }
            });

            // waypoint.cache.getName()
            gcCache.getChild(nsGC, "name").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String cacheName) {
                    cache.setName(validate(cacheName));
                }
            });

            // waypoint.cache.getOwner()
            gcCache.getChild(nsGC, "owner").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String ownerUserId) {
                    cache.setOwnerUserId(validate(ownerUserId));
                }
            });

            // waypoint.cache.getOwner()
            gcCache.getChild(nsGC, "placed_by").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String ownerDisplayName) {
                    cache.setOwnerDisplayName(validate(ownerDisplayName));
                }
            });

            // waypoint.cache.getType()
            gcCache.getChild(nsGC, "type").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String bodyIn) {
                    String body = validate(bodyIn);
                    // lab caches wrongly contain a prefix in the type
                    if (body.startsWith("Geocache|")) {
                        body = StringUtils.substringAfter(body, "Geocache|").trim();
                    }
                    cache.setType(CacheType.getByPattern(body));
                }
            });

            // waypoint.cache.container
            gcCache.getChild(nsGC, "container").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String body) {
                    cache.setSize(CacheSize.getById(validate(body)));
                }
            });

            // waypoint.cache.getAttributes()
            // @see issue #299

            // <groundspeak:attributes>
            //   <groundspeak:attribute id="32" inc="1">Bicycles</groundspeak:attribute>
            //   <groundspeak:attribute id="13" inc="1">Available at all times</groundspeak:attribute>
            // where inc = 0 => _no, inc = 1 => _yes
            // IDs see array CACHE_ATTRIBUTES
            final Element gcAttributes = gcCache.getChild(nsGC, "attributes");

            // waypoint.cache.attribute
            final Element gcAttribute = gcAttributes.getChild(nsGC, "attribute");

            gcAttribute.setStartElementListener(new StartElementListener() {
                @Override
                public void start(final Attributes attrs) {
                    try {
                        if (attrs.getIndex("id") > -1 && attrs.getIndex("inc") > -1) {
                            final int attributeId = Integer.parseInt(attrs.getValue("id"));
                            final boolean attributeActive = Integer.parseInt(attrs.getValue("inc")) != 0;
                            final String internalId = CacheAttributeTranslator.getInternalId(attributeId, attributeActive);
                            if (internalId != null) {
                                cache.getAttributes().add(internalId);
                            }
                        }
                    } catch (final NumberFormatException ignored) {
                        // nothing
                    }
                }
            });

            // waypoint.cache.getDifficulty()
            gcCache.getChild(nsGC, "difficulty").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String body) {
                    try {
                        cache.setDifficulty(Float.parseFloat(body));
                    } catch (final NumberFormatException e) {
                        Log.w("Failed to parse difficulty", e);
                    }
                }
            });

            // waypoint.cache.getTerrain()
            gcCache.getChild(nsGC, "terrain").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String body) {
                    try {
                        cache.setTerrain(Float.parseFloat(body));
                    } catch (final NumberFormatException e) {
                        Log.w("Failed to parse terrain", e);
                    }
                }
            });

            // waypoint.cache.country
            gcCache.getChild(nsGC, "country").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String country) {
                    if (StringUtils.isBlank(cache.getLocation())) {
                        cache.setLocation(validate(country));
                    } else {
                        cache.setLocation(cache.getLocation() + ", " + country.trim());
                    }
                }
            });

            // waypoint.cache.state
            gcCache.getChild(nsGC, "state").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String state) {
                    final String trimmedState = state.trim();
                    if (StringUtils.isNotEmpty(trimmedState)) { // state can be completely empty
                        if (StringUtils.isBlank(cache.getLocation())) {
                            cache.setLocation(validate(state));
                        } else {
                            cache.setLocation(trimmedState + ", " + cache.getLocation());
                        }
                    }
                }
            });

            // waypoint.cache.encoded_hints
            gcCache.getChild(nsGC, "encoded_hints").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String encoded) {
                    cache.setHint(validate(encoded));
                }
            });

            gcCache.getChild(nsGC, "short_description").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String shortDesc) {
                    cache.setShortDescription(validate(shortDesc));
                }
            });

            gcCache.getChild(nsGC, "long_description").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String desc) {
                    cache.setDescription(validate(desc));
                }
            });

            // waypoint.cache.travelbugs
            final Element gcTBs = gcCache.getChild(nsGC, "travelbugs");

            // waypoint.cache.travelbug
            final Element gcTB = gcTBs.getChild(nsGC, "travelbug");

            // waypoint.cache.travelbugs.travelbug
            gcTB.setStartElementListener(new StartElementListener() {

                @Override
                public void start(final Attributes attrs) {
                    trackable = new Trackable();

                    try {
                        if (attrs.getIndex("ref") > -1) {
                            trackable.setGeocode(attrs.getValue("ref"));
                        }
                    } catch (final RuntimeException ignored) {
                        // nothing
                    }
                }
            });

            gcTB.setEndElementListener(new EndElementListener() {

                @Override
                public void end() {
                    if (StringUtils.isNotBlank(trackable.getGeocode()) && StringUtils.isNotBlank(trackable.getName())) {
                        cache.addInventoryItem(trackable);
                    }
                }
            });

            // waypoint.cache.travelbugs.travelbug.getName()
            gcTB.getChild(nsGC, "name").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String tbName) {
                    trackable.setName(validate(tbName));
                }
            });

            // waypoint.cache.logs
            final Element gcLogs = gcCache.getChild(nsGC, "logs");

            // waypoint.cache.log
            final Element gcLog = gcLogs.getChild(nsGC, "log");

            gcLog.setStartElementListener(new StartElementListener() {

                @Override
                public void start(final Attributes attrs) {
                    log = new LogEntry("", 0, LogType.UNKNOWN, "");

                    try {
                        if (attrs.getIndex("id") > -1) {
                            log.id = Integer.parseInt(attrs.getValue("id"));
                        }
                    } catch (final NumberFormatException ignored) {
                        // nothing
                    }
                }
            });

            gcLog.setEndElementListener(new EndElementListener() {

                @Override
                public void end() {
                    if (log.type != LogType.UNKNOWN) {
                        if (log.type.isFoundLog() && StringUtils.isNotBlank(log.author)) {
                            final IConnector connector = ConnectorFactory.getConnector(cache);
                            if (connector instanceof ILogin && StringUtils.equals(log.author, ((ILogin) connector).getUserName())) {
                                cache.setFound(true);
                                cache.setVisitedDate(log.date);
                            }
                        }
                        logs.add(log);
                    }
                }
            });

            // waypoint.cache.logs.log.date
            gcLog.getChild(nsGC, "date").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String body) {
                    try {
                        log.date = parseDate(body).getTime();
                    } catch (final Exception e) {
                        Log.w("Failed to parse log date", e);
                    }
                }
            });

            // waypoint.cache.logs.log.getType()
            gcLog.getChild(nsGC, "type").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String body) {
                    final String logType = validate(body);
                    log.type = LogType.getByType(logType);
                }
            });

            // waypoint.cache.logs.log.finder
            gcLog.getChild(nsGC, "finder").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String finderName) {
                    log.author = validate(finderName);
                }
            });

            // waypoint.cache.logs.log.text
            gcLog.getChild(nsGC, "text").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String logText) {
                    log.log = validate(logText);
                }
            });
        }

        try {
            progressStream = new ProgressInputStream(stream);
            final BufferedReader reader = new BufferedReader(new InputStreamReader(progressStream, CharEncoding.UTF_8));
            Xml.parse(new InvalidXMLCharacterFilterReader(reader), root.getContentHandler());
            return DataStore.loadCaches(result, EnumSet.of(LoadFlag.DB_MINIMAL));
        } catch (final SAXException e) {
            throw new ParserException("Cannot parse .gpx file as GPX " + version + ": could not parse XML", e);
        }
    }

    /**
     * Add listeners for GSAK extensions
     *
     */
    private void registerGsakExtensions(final Element cacheParent) {
        for (final String gsakNamespace : GSAK_NS) {
            final Element gsak = cacheParent.getChild(gsakNamespace, "wptExtension");
            gsak.getChild(gsakNamespace, "Watch").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String watchList) {
                    cache.setOnWatchlist(Boolean.parseBoolean(watchList.trim()));
                }
            });

            gsak.getChild(gsakNamespace, "UserData").setEndTextElementListener(new UserDataListener(1));

            for (int i = 2; i <= 4; i++) {
                gsak.getChild(gsakNamespace, "User" + i).setEndTextElementListener(new UserDataListener(i));
            }

            gsak.getChild(gsakNamespace, "Parent").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String body) {
                    parentCacheCode = body;
                }
            });

            gsak.getChild(gsakNamespace, "FavPoints").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String favoritePoints) {
                    try {
                        cache.setFavoritePoints(Integer.parseInt(favoritePoints));
                    }
                    catch (final NumberFormatException e) {
                        Log.w("Failed to parse favorite points", e);
                    }
                }
            });

            gsak.getChild(gsakNamespace, "GcNote").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String personalNote) {
                    cache.setPersonalNote(StringUtils.trim(personalNote));
                }
            });

            gsak.getChild(gsakNamespace, "IsPremium").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String premium) {
                    cache.setPremiumMembersOnly(Boolean.parseBoolean(premium));
                }
            });

            gsak.getChild(gsakNamespace, "LatBeforeCorrect").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String latitude) {
                    originalLat = latitude;
                    addOriginalCoordinates();
                }
            });

            gsak.getChild(gsakNamespace, "LonBeforeCorrect").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String longitude) {
                    originalLon = longitude;
                    addOriginalCoordinates();
                }
            });

            gsak.getChild(gsakNamespace, "Code").setEndTextElementListener(new EndTextElementListener() {

                @Override
                public void end(final String geocode) {
                    if (StringUtils.isNotBlank(geocode)) {
                        cache.setGeocode(StringUtils.trim(geocode));
                    }
                }
            });

        }
    }

    /**
     * Add listeners for TerraCaching extensions
     *
     */
    private void registerTerraCachingExtensions(final Element cacheParent) {
        final String terraNamespace = "http://www.TerraCaching.com/GPX/1/0";
        final Element terraCache = cacheParent.getChild(terraNamespace, "terracache");

        terraCache.getChild(terraNamespace, "name").setEndTextElementListener(new EndTextElementListener() {

            @Override
            public void end(final String name) {
                cache.setName(StringUtils.trim(name));
            }
        });

        terraCache.getChild(terraNamespace, "owner").setEndTextElementListener(new EndTextElementListener() {

            @Override
            public void end(final String ownerName) {
                cache.setOwnerDisplayName(validate(ownerName));
            }
        });

        terraCache.getChild(terraNamespace, "size").setEndTextElementListener(new EndTextElementListener() {

            @Override
            public void end(final String size) {
                cache.setSize(CacheSize.getById(size));
            }
        });

    }

    protected void addOriginalCoordinates() {
        if (StringUtils.isNotEmpty(originalLat) && StringUtils.isNotEmpty(originalLon)) {
            final Waypoint waypoint = new Waypoint(CgeoApplication.getInstance().getString(R.string.cache_coordinates_original), WaypointType.ORIGINAL, false);
            waypoint.setCoords(new Geopoint(originalLat, originalLon));
            cache.addOrChangeWaypoint(waypoint, false);
            cache.setUserModifiedCoords(true);
        }
    }

    /**
     * Add listeners for c:geo extensions
     *
     */
    private void registerCgeoExtensions(final Element cacheParent) {
        final Element cgeoVisited = cacheParent.getChild(CGEO_NS, "visited");

        cgeoVisited.setEndTextElementListener(new EndTextElementListener() {

            @Override
            public void end(final String visited) {
                wptVisited = Boolean.parseBoolean(visited.trim());
            }
        });

        final Element cgeoUserDefined = cacheParent.getChild(CGEO_NS, "userdefined");

        cgeoUserDefined.setEndTextElementListener(new EndTextElementListener() {

            @Override
            public void end(final String userDefined) {
                wptUserDefined = Boolean.parseBoolean(userDefined.trim());
            }
        });
    }

    /**
     * Overwrite this method in a GPX parser sub class to modify the {@link Geocache}, after it has been fully parsed
     * from the GPX file and before it gets stored.
     *
     * @param cache
     *            currently imported cache
     */
    protected void afterParsing(final Geocache cache) {
        // can be overridden by sub classes
    }

    /**
     * GPX 1.0 and 1.1 use different XML elements to put the cache into, therefore needs to be overwritten in the
     * version specific subclasses
     *
     */
    protected abstract Element getCacheParent(Element waypoint);

    protected static String validate(final String input) {
        if ("nil".equalsIgnoreCase(input)) {
            return "";
        }
        return input.trim();
    }

    private void findGeoCode(final String input) {
        if (input == null || StringUtils.isNotBlank(cache.getGeocode())) {
            return;
        }
        final String trimmed = input.trim();
        final MatcherWrapper matcherGeocode = new MatcherWrapper(PATTERN_GEOCODE, trimmed);
        if (matcherGeocode.find()) {
            final String geocode = matcherGeocode.group(1);
            // a geocode should not be part of a word
            if (geocode.length() == trimmed.length() || Character.isWhitespace(trimmed.charAt(geocode.length()))) {
                if (ConnectorFactory.canHandle(geocode)) {
                    cache.setGeocode(geocode);
                }
            }
        }
    }

    /**
     * reset all fields that are used to store cache fields over the duration of parsing a single cache
     */
    private void resetCache() {
        type = null;
        sym = null;
        name = null;
        desc = null;
        cmt = null;
        parentCacheCode = null;
        wptVisited = false;
        wptUserDefined = false;
        logs = new ArrayList<>();

        cache = new Geocache(this);

        // explicitly set all properties which could lead to database access, if left as null value
        cache.setLocation("");
        cache.setDescription("");
        cache.setShortDescription("");
        cache.setHint("");

        for (int i = 0; i < userData.length; i++) {
            userData[i] = null;
        }
        originalLon = null;
        originalLat = null;
    }

    /**
     * create a cache note from the UserData1 to UserData4 fields supported by GSAK
     */
    private void createNoteFromGSAKUserdata() {
        if (StringUtils.isBlank(cache.getPersonalNote())) {
            final StringBuilder buffer = new StringBuilder();
            for (final String anUserData : userData) {
                if (StringUtils.isNotBlank(anUserData)) {
                    buffer.append(' ').append(anUserData);
                }
            }
            final String note = buffer.toString().trim();
            if (StringUtils.isNotBlank(note)) {
                cache.setPersonalNote(note);
            }
        }
    }

    private boolean isValidForImport() {
        if (StringUtils.isBlank(cache.getGeocode())) {
            return false;
        }
        if (cache.getCoords() == null) {
            return false;
        }
        return ((type == null && sym == null)
                || StringUtils.contains(type, "geocache")
                || StringUtils.contains(sym, "geocache")
                || StringUtils.containsIgnoreCase(sym, "waymark")
                || StringUtils.containsIgnoreCase(sym, "terracache"));
    }

    @Nullable
    private Geocache findParentCache() {
        if (StringUtils.isBlank(parentCacheCode)) {
            return null;
        }
        // first match by geocode only
        Geocache cacheForWaypoint = DataStore.loadCache(parentCacheCode, LoadFlags.LOAD_CACHE_OR_DB);
        if (cacheForWaypoint == null) {
            // then match by title
            final String geocode = DataStore.getGeocodeForTitle(parentCacheCode);
            if (StringUtils.isNotBlank(geocode)) {
                cacheForWaypoint = DataStore.loadCache(geocode, LoadFlags.LOAD_CACHE_OR_DB);
            }
        }
        return cacheForWaypoint;
    }
}


File: tests/src/cgeo/geocaching/connector/TerraCachingConnectorTest.java
package cgeo.geocaching.connector;

import static org.assertj.core.api.Assertions.assertThat;
import junit.framework.TestCase;

public class TerraCachingConnectorTest extends TestCase {

    public static void testCanHandle() {
        final IConnector tcConnector = ConnectorFactory.getConnector("TCABC");
        assertThat(tcConnector).isNotNull();

        assertThat(tcConnector.canHandle("TCABC")).isTrue();
        assertThat(tcConnector.canHandle("TC2JP")).isTrue();

        assertThat(tcConnector.canHandle("TC1234")).isFalse();
        assertThat(tcConnector.canHandle("GC1234")).isFalse();
    }

}


File: tests/src/cgeo/geocaching/files/GPXParserTest.java
package cgeo.geocaching.files;

import static org.assertj.core.api.Assertions.assertThat;

import cgeo.geocaching.DataStore;
import cgeo.geocaching.Geocache;
import cgeo.geocaching.LogEntry;
import cgeo.geocaching.Waypoint;
import cgeo.geocaching.connector.ConnectorFactory;
import cgeo.geocaching.connector.IConnector;
import cgeo.geocaching.enumerations.CacheSize;
import cgeo.geocaching.enumerations.CacheType;
import cgeo.geocaching.enumerations.LoadFlags;
import cgeo.geocaching.enumerations.LoadFlags.LoadFlag;
import cgeo.geocaching.enumerations.WaypointType;
import cgeo.geocaching.location.Geopoint;
import cgeo.geocaching.sorting.GeocodeComparator;
import cgeo.geocaching.test.AbstractResourceInstrumentationTestCase;
import cgeo.geocaching.test.R;
import cgeo.geocaching.utils.CalendarUtils;
import cgeo.geocaching.utils.SynchronizedDateFormat;

import java.io.IOException;
import java.io.InputStream;
import java.text.ParseException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.EnumSet;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

public class GPXParserTest extends AbstractResourceInstrumentationTestCase {
    private static final SynchronizedDateFormat LOG_DATE_FORMAT = new SynchronizedDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US); // 2010-04-20T07:00:00Z

    public void testGPXVersion100() throws Exception {
        testGPXVersion(R.raw.gc1bkp3_gpx100);
    }

    private Geocache testGPXVersion(final int resourceId) throws IOException, ParserException {
        final List<Geocache> caches = readGPX10(resourceId);
        assertThat(caches).isNotNull();
        assertThat(caches).hasSize(1);
        final Geocache cache = caches.get(0);
        assertThat(cache.getGeocode()).isEqualTo("GC1BKP3");
        assertThat(cache.getGuid()).isEqualTo("9946f030-a514-46d8-a050-a60e92fd2e1a");
        assertThat(cache.getType()).isEqualTo(CacheType.TRADITIONAL);
        assertThat(cache.isArchived()).isEqualTo(false);
        assertThat(cache.isDisabled()).isEqualTo(false);
        assertThat(cache.getName()).isEqualTo("Die Schatzinsel / treasure island");
        assertThat(cache.getOwnerDisplayName()).isEqualTo("Die unbesiegbaren Geo - Geparden");
        assertThat(cache.getOwnerUserId()).isEqualTo("Die unbesiegbaren Geo - Geparden");
        assertThat(cache.getSize()).isEqualTo(CacheSize.MICRO);
        assertThat(cache.getDifficulty()).isEqualTo(1.0f);
        assertThat(cache.getTerrain()).isEqualTo(5.0f);
        assertThat(cache.getLocation()).isEqualTo("Baden-Württemberg, Germany");
        assertThat(cache.getShortDescription()).isEqualTo("Ein alter Kindheitstraum, ein Schatz auf einer unbewohnten Insel.\nA old dream of my childhood, a treasure on a lonely island.");
        assertThat(cache.getCoords()).isEqualTo(new Geopoint(48.859683, 9.1874));
        return cache;
    }

    public void testGPXVersion101() throws IOException, ParserException {
        final Geocache cache = testGPXVersion(R.raw.gc1bkp3_gpx101);
        assertThat(cache.getAttributes()).isNotNull();
        assertThat(cache.getAttributes()).hasSize(10);
    }

    public void testOC() throws IOException, ParserException {
        final List<Geocache> caches = readGPX10(R.raw.oc5952_gpx);
        final Geocache cache = caches.get(0);
        assertThat(cache.getGeocode()).isEqualTo("OC5952");
        assertThat(cache.getType()).isEqualTo(CacheType.TRADITIONAL);
        assertThat(cache.isArchived()).isEqualTo(false);
        assertThat(cache.isDisabled()).isEqualTo(false);
        assertThat(cache.getName()).isEqualTo("Die Schatzinsel / treasure island");
        assertThat(cache.getOwnerDisplayName()).isEqualTo("Die unbesiegbaren Geo - Geparden");
        assertThat(cache.getOwnerUserId()).isEqualTo("Die unbesiegbaren Geo - Geparden");
        assertThat(cache.getSize()).isEqualTo(CacheSize.SMALL);
        assertThat(cache.getDifficulty()).isEqualTo(1.0f);
        assertThat(cache.getTerrain()).isEqualTo(4.0f);
        assertThat(cache.getLocation()).isEqualTo("Baden-Württemberg, Germany");
        assertThat(cache.getShortDescription()).isEqualTo("Ein alter Kindheitstraum, ein Schatz auf einer unbewohnten Insel. A old dream of my childhood, a treasure on a lonely is");
        assertThat(cache.getCoords()).isEqualTo(new Geopoint(48.85968, 9.18740));
        assertThat(cache.isReliableLatLon()).isTrue();
    }

    public void testGc31j2h() throws IOException, ParserException {
        removeCacheCompletely("GC31J2H");
        final List<Geocache> caches = readGPX10(R.raw.gc31j2h);
        assertThat(caches).hasSize(1);
        final Geocache cache = caches.get(0);

        assertGc31j2h(cache);
        assertThat(caches.get(0)).isSameAs(cache);

        // no waypoints without importing waypoint file
        assertThat(cache.getWaypoints()).isEmpty();
        assertThat(cache.isReliableLatLon()).isTrue();
    }

    public void testGc31j2hWpts() throws IOException, ParserException {
        removeCacheCompletely("GC31J2H");
        final List<Geocache> caches = readGPX10(R.raw.gc31j2h, R.raw.gc31j2h_wpts);
        assertThat(caches).hasSize(1);
        final Geocache cache = caches.get(0);
        assertGc31j2h(cache);
        assertGc31j2hWaypoints(cache);
    }

    private static void checkWaypointType(final Collection<Geocache> caches, final String geocode, final int wpIndex, final WaypointType waypointType) {
        for (final Geocache cache : caches) {
            if (cache.getGeocode().equals(geocode)) {
                final List<Waypoint> waypoints = cache.getWaypoints();
                assertThat(waypoints).isNotEmpty();
                final Waypoint waypoint = waypoints.get(wpIndex);
                assertThat(waypoint).isNotNull();
                assertThat(waypoint.getWaypointType()).isEqualTo(waypointType);
                return;
            }
        }
        fail("could not find cache with geocode " + geocode);
    }

    public void testRenamedWaypointTypes() throws IOException, ParserException {
        final List<Geocache> caches = readGPX10(R.raw.renamed_waypoints, R.raw.renamed_waypoints_wpts);
        assertThat(caches).hasSize(25);
        checkWaypointType(caches, "GC3NBDE", 1, WaypointType.STAGE);        // multi waypoint (now "physical stage")
        checkWaypointType(caches, "GC16CBG", 1, WaypointType.PUZZLE);       // mystery waypoint (now "virtual stage")
    }

    public void testGc31j2hWptsWithoutCache() throws IOException, ParserException {
        final List<Geocache> caches = readGPX10(R.raw.gc31j2h_wpts);
        assertThat(caches).isEmpty();
    }

    public void testGc3abcd() throws IOException, ParserException {
        final List<Geocache> caches = readGPX10(R.raw.gc3abcd);
        assertThat(caches.size()).isEqualTo(1);
        final Geocache gc3abcd = caches.get(0);
        assertThat(gc3abcd.getGeocode()).isEqualTo("GC3ABCD");
        final List<Waypoint> waypoints = gc3abcd.getWaypoints();
        assertThat(waypoints.size()).isEqualTo(2);
    }

    private static void assertGc31j2h(final Geocache cache) {
        assertThat(cache.getGeocode()).isEqualTo("GC31J2H");
        assertThat(cache.getName()).isEqualTo("Hockenheimer City-Brunnen");
        assertThat(cache.getShortDescription()).startsWith("Kurzer informativer Multi entlang der Brunnen");
        assertThat(cache.getDescription()).startsWith("Cachemobile können kostenfrei am Messplatz geparkt werden.");
        assertThat(cache.hasTrackables()).isTrue();
        assertEquals(2.0f, cache.getDifficulty(), 0.01f);
        assertEquals(1.0f, cache.getTerrain(), 0.01f);
        final Geopoint refCoordinates = new Geopoint("N 49° 19.122", "E 008° 32.739");
        assertThat(cache.getCoords()).isEqualTo(refCoordinates);
        assertThat(cache.getOwnerDisplayName()).isEqualTo("vptsz");
        assertThat(cache.getOwnerUserId()).isEqualTo("vptsz");
        assertThat(cache.getSize()).isEqualTo(CacheSize.SMALL);
        assertThat(cache.getType()).isEqualTo(CacheType.MULTI);
        assertThat(cache.isArchived()).isFalse();
        assertThat(cache.isDisabled()).isFalse();
        assertThat(cache.isEventCache()).isFalse();
        assertThat(cache.isPremiumMembersOnly()).isFalse();
        assertThat(cache.isOwner()).isFalse();
        assertThat(cache.isFound()).isTrue();
        assertThat(cache.getHint()).isEqualTo("Station3: Der zerbrochene Stein zählt doppelt.\nFinal: Oben neben dem Tor");
        // logs
        assertThat(cache.getLogs()).hasSize(6);
        final LogEntry log = cache.getLogs().get(5);
        assertThat(log.author).isEqualTo("Geoteufel");
        assertThat(log.date).isEqualTo(parseTime("2011-09-11T07:00:00Z"));
        assertThat(log.found).isEqualTo(-1);
        assertThat(log.log).isEqualTo("Sehr schöne Runde und wir haben wieder etwas Neues über Hockenheim gelernt. Super Tarnung.\nTFTC, Geoteufel");
        assertThat(log.isOwn()).isFalse();
        assertThat(log.getDisplayText()).isEqualTo(log.log);
        assertThat(CalendarUtils.daysSince(log.date)).isGreaterThan(700);

        // following info is not contained in pocket query gpx file
        assertThat(cache.getAttributes()).isEmpty();
    }

    private static long parseTime(final String time) {
        try {
            return LOG_DATE_FORMAT.parse(time).getTime();
        } catch (final ParseException e) {
            return 0;
        }
    }

    private static void assertGc31j2hWaypoints(final Geocache cache) {
        assertThat(cache.getWaypoints()).isNotNull();
        assertThat(cache.getWaypoints()).hasSize(2);
        Waypoint wp = cache.getWaypoints().get(0);
        assertThat(wp.getGeocode()).isEqualTo("GC31J2H");
        assertThat(wp.getPrefix()).isEqualTo("00");
        assertThat(wp.getLookup()).isEqualTo("---");
        assertThat(wp.getName()).isEqualTo("Parkplatz");
        assertThat(wp.getNote()).isEqualTo("Kostenfreies Parken (je nach Parkreihe Parkscheibe erforderlich)");
        assertThat(wp.getWaypointType()).isEqualTo(WaypointType.PARKING);
        assertEquals(49.317517, wp.getCoords().getLatitude(), 0.000001);
        assertEquals(8.545083, wp.getCoords().getLongitude(), 0.000001);

        wp = cache.getWaypoints().get(1);
        assertThat(wp.getGeocode()).isEqualTo("GC31J2H");
        assertThat(wp.getPrefix()).isEqualTo("S1");
        assertThat(wp.getLookup()).isEqualTo("---");
        assertThat(wp.getName()).isEqualTo("Station 1");
        assertThat(wp.getNote()).isEqualTo("Ein zweiter Wegpunkt, der nicht wirklich existiert sondern nur zum Testen gedacht ist.");
        assertThat(wp.getWaypointType()).isEqualTo(WaypointType.STAGE);
        assertEquals(49.317500, wp.getCoords().getLatitude(), 0.000001);
        assertEquals(8.545100, wp.getCoords().getLongitude(), 0.000001);
    }

    private List<Geocache> readGPX10(final int... resourceIds) throws IOException, ParserException {
        final GPX10Parser parser = new GPX10Parser(getTemporaryListId());
        return readVersionedGPX(parser, resourceIds);
    }

    private List<Geocache> readGPX11(final int... resourceIds) throws IOException, ParserException {
        final GPX11Parser parser = new GPX11Parser(getTemporaryListId());
        return readVersionedGPX(parser, resourceIds);
    }

    private List<Geocache> readVersionedGPX(final GPXParser parser, final int... resourceIds) throws IOException, ParserException {
        final Set<String> result = new HashSet<String>();
        for (final int resourceId : resourceIds) {
            final InputStream instream = getResourceStream(resourceId);
            try {
                final Collection<Geocache> caches = parser.parse(instream, null);
                assertThat(caches).isNotNull();
                for (final Geocache cache : caches) {
                    result.add(cache.getGeocode());
                }
            } finally {
                instream.close();
            }
        }
        // reload caches, because the parser only returns the minimum version of each cache
        return new ArrayList<Geocache>(DataStore.loadCaches(result, LoadFlags.LOAD_ALL_DB_ONLY));
    }

    public static void testParseDateWithFractionalSeconds() throws ParseException {
        // was experienced in GSAK file
        final String dateString = "2011-08-13T02:52:18.103Z";
        GPXParser.parseDate(dateString);
    }

    public static void testParseDateWithHugeFraction() throws ParseException {
        // see issue 821
        final String dateString = "2011-11-07T00:00:00.0000000-07:00";
        GPXParser.parseDate(dateString);
    }

    public void testSelfmadeGPXWithoutGeocodes() throws Exception {
        final List<Geocache> caches = readGPX11(R.raw.no_connector);
        assertThat(caches).hasSize(13);
    }

    public void testTexasChallenge2012() throws Exception {
        final List<Geocache> caches = readGPX10(R.raw.challenge);
        // previously these caches overwrote each other during parsing
        assertThat(caches).hasSize(130);
    }

    public void testGeoToad() throws Exception {
        final List<Geocache> caches = readGPX10(R.raw.geotoad);
        assertThat(caches).hasSize(2);
        final List<String> codes = new ArrayList<String>();
        for (final Geocache cache : caches) {
            codes.add(cache.getGeocode());
        }
        assertThat(codes).contains("GC2KN6K", "GC1T3MK");
    }

    public void testLazyLogLoading() throws IOException, ParserException {
        // this test should be in CacheTest, but it is easier to create here due to the GPX import abilities
        final String geocode = "GC31J2H";
        removeCacheCompletely(geocode);
        final List<Geocache> caches = readGPX10(R.raw.lazy);
        assertThat(caches).hasSize(1);
        DataStore.removeAllFromCache();
        // load only the minimum cache, it has several members missing
        final Geocache minimalCache = DataStore.loadCache(geocode, EnumSet.of(LoadFlag.DB_MINIMAL));
        assert minimalCache != null;
        assertThat(minimalCache).isNotNull();

        // now check that we load lazy members on demand
        assertThat(minimalCache.getAttributes()).isNotEmpty();
        assertThat(minimalCache.getLogs()).isNotEmpty();

        removeCacheCompletely(geocode);
    }

    public void testDuplicateImport() throws IOException, ParserException {
        final String geocode = "GC31J2H";
        removeCacheCompletely(geocode);

        // first import
        List<Geocache> caches = readGPX10(R.raw.lazy);
        assertThat(caches).hasSize(1);
        assertThat(caches.get(0).getLogs()).hasSize(6);

        // second import
        caches = readGPX10(R.raw.lazy);
        assertThat(caches).hasSize(1);
        assertThat(caches.get(0).getLogs()).hasSize(6);

        removeCacheCompletely(geocode);
    }

    public void testWaymarking() throws Exception {
        final List<Geocache> caches = readGPX10(R.raw.waymarking_gpx);
        assertThat(caches).hasSize(1);
        final Geocache waymark = caches.get(0);
        assertThat(waymark).isNotNull();
        assertThat(waymark.getGeocode()).isEqualTo("WM7BM7");
        assertThat(waymark.getName()).isEqualTo("Roman water pipe Kornwestheim");
        assertThat(waymark.getUrl()).isNotEmpty(); // connector must be able to create it
        assertThat(waymark.getType()).isEqualTo(CacheType.UNKNOWN);
        assertThat(waymark.getSize()).isEqualTo(CacheSize.UNKNOWN);
    }

    public void testTerraCaching() throws Exception {
        final List<Geocache> caches = readGPX11(R.raw.terracaching_gpx);
        assertThat(caches).hasSize(55);

        Collections.sort(caches, new GeocodeComparator());

        final Geocache cache = caches.get(0);
        assertThat(cache.getGeocode()).isEqualTo("TC2JP");
        assertThat(cache.getName()).isEqualTo("Pingo");
        assertThat(cache.getOwnerDisplayName()).isEqualTo("harrieklomp");
        assertThat(cache.getType()).isEqualTo(CacheType.UNKNOWN);
        assertThat(cache.getSize()).isEqualTo(CacheSize.MICRO);
    }

    /**
     * This one uses geocodes where the first character is actually a digit, not a character
     */
    public void testGCTour() throws Exception {
        final List<Geocache> caches = readGPX10(R.raw.gctour_gpx);
        assertThat(caches).hasSize(54);
    }

    public void testOX() throws IOException, ParserException {
        final List<Geocache> caches = readGPX10(R.raw.ox1ry0y_gpx);
        assertThat(caches).hasSize(1);
        final Geocache cache = caches.get(0);
        assertThat(cache.getGeocode()).isEqualTo("OX1RY0Y");
        assertThat(cache.getType()).isEqualTo(CacheType.TRADITIONAL);
        assertThat(cache.isArchived()).isEqualTo(false);
        assertThat(cache.isDisabled()).isEqualTo(false);
        assertThat(cache.getName()).isEqualTo("Kornwestheim und die Römer");
        assertThat(cache.getOwnerDisplayName()).isEqualTo("Thomas&Dani");
        assertThat(cache.getSize()).isEqualTo(CacheSize.SMALL);
        assertThat(cache.getDifficulty()).isEqualTo(1.5f);
        assertThat(cache.getTerrain()).isEqualTo(1.0f);
        assertThat(cache.getDescription().startsWith("Dieses sind die Reste einer in Kornwestheim gefundenen")).isTrue();
        assertThat(cache.getCoords()).isEqualTo(new Geopoint(48.8642167, 9.1836));
        assertThat(cache.isReliableLatLon()).isTrue();
        assertThat(cache.getHint()).isEqualTo("Wasserleitung");
    }

    private Geocache getFirstCache(final int gpxResourceId) throws IOException, ParserException {
        final List<Geocache> caches = readGPX10(gpxResourceId);
        assertThat(caches).isNotNull();
        assertThat(caches).hasSize(1);
        return caches.get(0);
    }

    public void testGsakFavPoints() throws IOException, ParserException {
        final Geocache cache = getFirstCache(R.raw.gc3t1xg_gsak);
        assertThat(cache.getFavoritePoints()).isEqualTo(258);
    }

    public void testGsakPersonalNote() throws IOException, ParserException {
        final Geocache cache = getFirstCache(R.raw.gc3t1xg_gsak);
        assertThat(cache.getPersonalNote()).isEqualTo("Personal Note Test");
    }

    public void testGsakPremium() throws IOException, ParserException {
        final Geocache cache = getFirstCache(R.raw.gc3t1xg_gsak);
        assertThat(cache.isPremiumMembersOnly()).isTrue();
    }

    public void testGsakModified() throws IOException, ParserException {
        final Geocache unmodified = getFirstCache(R.raw.gc3t1xg_gsak);
        assertThat(unmodified.hasUserModifiedCoords()).isFalse();
        final Geocache cache = getFirstCache(R.raw.modified_gsak);
        assertThat(cache.hasUserModifiedCoords()).isTrue();
        assertThat(cache.getWaypoints()).hasSize(1);
        final Waypoint waypoint = cache.getWaypoints().get(0);
        assertThat(waypoint.getWaypointType()).isEqualTo(WaypointType.ORIGINAL);
        assertThat(waypoint.getCoords()).isEqualTo(new Geopoint("51.223032", "6.026147"));
        assertThat(cache.getCoords()).isEqualTo(new Geopoint("51.223033", "6.027767"));
    }

    public void testGPXMysteryType() throws IOException, ParserException {
        final List<Geocache> caches = readGPX10(R.raw.tc2012);
        final Geocache mystery = getCache(caches, "U017");
        assertThat(mystery).isNotNull();
        assert mystery != null;
        assertThat(mystery.getType()).isEqualTo(CacheType.MYSTERY);
    }

    private static Geocache getCache(final List<Geocache> caches, final String geocode) {
        for (final Geocache geocache : caches) {
            if (geocache.getName().equals(geocode)) {
                return geocache;
            }
        }
        return null;
    }

    public void testLabCaches() throws IOException, ParserException {
        final List<Geocache> caches = readGPX10(R.raw.giga_lab_caches);
        assertThat(caches).hasSize(10);
        final Geocache lab = getCache(caches, "01_Munich Olympic Walk Of Stars_Updated-Project MUNICH2014 - Mia san Giga! Olympiapark");
        assertThat(lab).isNotNull();

        // parse labs as virtual for the time being
        assertThat(lab.getType()).isEqualTo(CacheType.VIRTUAL);

        // no difficulty and terrain rating
        assertThat(lab.getTerrain()).isEqualTo(0);
        assertThat(lab.getDifficulty()).isEqualTo(0);

        // geocodes are just big hashes
        assertThat(lab.getGeocode()).isEqualTo("01_Munich Olympic Walk Of Stars_Updated-Project MUNICH2014 - Mia san Giga! Olympiapark".toUpperCase(Locale.US));

        // other normal cache properties
        assertThat(lab.getName()).isEqualTo("01_Munich Olympic Walk Of Stars_Updated-Project MUNICH2014 - Mia san Giga! Olympiapark");
        assertThat(lab.getShortDescription()).isEqualTo("01_Munich Olympic Walk Of Stars_Updated (Giga! Olympia Park)-Project MUNICH2014 - Mia san Giga! Olympiapark");
        assertThat(lab.getDescription()).startsWith("DEU:");

        final IConnector unknownConnector = ConnectorFactory.getConnector("ABC123");
        assertThat(ConnectorFactory.getConnector(lab)).isSameAs(unknownConnector);
    }

    public void testGSAKGeocode() throws IOException, ParserException {
        final List<Geocache> caches = readGPX10(R.raw.liptov_gpx);
        assertThat(caches).hasSize(1);

        final Geocache cache = caches.get(0);

        // make sure we get the right geocode, even though the name seems to start with a code, too
        assertThat(cache.getGeocode()).isEqualTo("GC3A5N1");
    }

}
