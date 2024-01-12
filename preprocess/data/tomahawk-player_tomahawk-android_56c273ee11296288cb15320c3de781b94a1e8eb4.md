Refactoring Types: ['Pull Up Attribute', 'Push Down Attribute', 'Push Down Method', 'Pull Up Method']
ayer - <http://tomahawk-player.org> ===
 *
 *   Copyright 2015, Enno Gottschalk <mrmaffen@googlemail.com>
 *
 *   Tomahawk is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   Tomahawk is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with Tomahawk. If not, see <http://www.gnu.org/licenses/>.
 */
package org.tomahawk.libtomahawk.collection;

import org.jdeferred.Promise;
import org.tomahawk.libtomahawk.resolver.Query;

import android.widget.ImageView;

import java.util.List;
import java.util.Set;

public abstract class Collection {

    private final String mId;

    private final String mName;

    public Collection(String id, String name) {
        mId = id;
        mName = name;
    }

    /**
     * Load this {@link NativeCollection}'s icon into the given {@link ImageView}
     */
    public abstract void loadIcon(ImageView imageView, boolean grayOut);

    public String getId() {
        return mId;
    }

    public String getName() {
        return mName;
    }

    public abstract Promise<Set<Query>, Throwable, Void> getQueries();

    public abstract Promise<Set<Artist>, Throwable, Void> getArtists();

    public abstract Promise<Set<Artist>, Throwable, Void> getAlbumArtists();

    public abstract Promise<Set<Album>, Throwable, Void> getAlbums();

    public abstract Promise<List<Album>, Throwable, Void> getArtistAlbums(Artist artist);

    public abstract Promise<Boolean, Throwable, Void> hasArtistAlbums(Artist artist);

    public abstract Promise<List<Query>, Throwable, Void> getAlbumTracks(Album album);

    public abstract Promise<Boolean, Throwable, Void> hasAlbumTracks(Album album);

}


File: src/org/tomahawk/libtomahawk/collection/CollectionManager.java
/* == This file is part of Tomahawk Player - <http://tomahawk-player.org> ===
 *
 *   Copyright 2012, Christopher Reichert <creichert07@gmail.com>
 *   Copyright 2012, Enno Gottschalk <mrmaffen@googlemail.com>
 *
 *   Tomahawk is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   Tomahawk is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with Tomahawk. If not, see <http://www.gnu.org/licenses/>.
 */
package org.tomahawk.libtomahawk.collection;

import com.google.common.collect.Sets;

import org.jdeferred.DonePipe;
import org.jdeferred.Promise;
import org.jdeferred.multiple.MultipleResults;
import org.tomahawk.libtomahawk.authentication.AuthenticatorManager;
import org.tomahawk.libtomahawk.authentication.AuthenticatorUtils;
import org.tomahawk.libtomahawk.authentication.HatchetAuthenticatorUtils;
import org.tomahawk.libtomahawk.database.DatabaseHelper;
import org.tomahawk.libtomahawk.infosystem.InfoRequestData;
import org.tomahawk.libtomahawk.infosystem.InfoSystem;
import org.tomahawk.libtomahawk.infosystem.QueryParams;
import org.tomahawk.libtomahawk.infosystem.hatchet.HatchetInfoPlugin;
import org.tomahawk.libtomahawk.resolver.Query;
import org.tomahawk.libtomahawk.utils.ADeferredObject;
import org.tomahawk.libtomahawk.utils.BetterDeferredManager;
import org.tomahawk.tomahawk_android.R;
import org.tomahawk.tomahawk_android.TomahawkApp;

import android.util.Log;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

import de.greenrobot.event.EventBus;

public class CollectionManager {

    public static final String TAG = CollectionManager.class.getSimpleName();

    private static class Holder {

        private static final CollectionManager instance = new CollectionManager();

    }

    public static class AddedEvent {

        public Collection mCollection;

    }

    public static class RemovedEvent {

        public Collection mCollection;

    }


    public static class UpdatedEvent {

        public Collection mCollection;

        public HashSet<String> mUpdatedItemIds;

    }

    private final ConcurrentHashMap<String, Collection> mCollections
            = new ConcurrentHashMap<>();

    private final HashSet<String> mCorrespondingRequestIds = new HashSet<>();

    private final HashSet<String> mResolvingHatchetIds = new HashSet<>();

    private final Set<String> mShowAsDeletedPlaylistMap =
            Sets.newSetFromMap(new ConcurrentHashMap<String, Boolean>());

    private final Set<String> mShowAsCreatedPlaylistMap =
            Sets.newSetFromMap(new ConcurrentHashMap<String, Boolean>());

    private CollectionManager() {
        EventBus.getDefault().register(this);

        addCollection(new UserCollection());
        addCollection(new HatchetCollection());

        ensureLovedItemsPlaylist();
        fetchAll();
    }

    @SuppressWarnings("unused")
    public void onEventAsync(InfoSystem.OpLogIsEmptiedEvent event) {
        for (Integer requestType : event.mRequestTypes) {
            if (requestType
                    == InfoRequestData.INFOREQUESTDATA_TYPE_SOCIALACTIONS) {
                fetchStarredArtists();
                fetchStarredAlbums();
                fetchLovedItemsPlaylist();
            } else if (requestType
                    == InfoRequestData.INFOREQUESTDATA_TYPE_PLAYBACKLOGENTRIES) {
                HatchetAuthenticatorUtils hatchetAuthUtils =
                        (HatchetAuthenticatorUtils) AuthenticatorManager.getInstance()
                                .getAuthenticatorUtils(TomahawkApp.PLUGINNAME_HATCHET);
                InfoSystem.getInstance()
                        .resolvePlaybackLog(hatchetAuthUtils.getLoggedInUser());
            } else if (requestType
                    == InfoRequestData.INFOREQUESTDATA_TYPE_PLAYLISTS
                    || requestType
                    == InfoRequestData.INFOREQUESTDATA_TYPE_PLAYLISTS_PLAYLISTENTRIES) {
                fetchPlaylists();
            }
        }
    }

    @SuppressWarnings("unused")
    public void onEventAsync(final InfoSystem.ResultsEvent event) {
        if (mCorrespondingRequestIds.contains(event.mInfoRequestData.getRequestId())) {
            mCorrespondingRequestIds.remove(event.mInfoRequestData.getRequestId());
            handleHatchetPlaylistResponse(event.mInfoRequestData);
        }
    }

    @SuppressWarnings("unused")
    public void onEventAsync(HatchetAuthenticatorUtils.UserLoginEvent event) {
        HatchetAuthenticatorUtils hatchetAuthUtils =
                (HatchetAuthenticatorUtils) AuthenticatorManager.getInstance()
                        .getAuthenticatorUtils(TomahawkApp.PLUGINNAME_HATCHET);
        InfoSystem.getInstance().resolvePlaybackLog(hatchetAuthUtils.getLoggedInUser());
        fetchAll();
    }

    public void fetchAll() {
        fetchPlaylists();
        fetchLovedItemsPlaylist();
        fetchStarredAlbums();
        fetchStarredArtists();
    }

    public static CollectionManager getInstance() {
        return Holder.instance;
    }

    public void addCollection(Collection collection) {
        mCollections.put(collection.getId(), collection);
        AddedEvent event = new AddedEvent();
        event.mCollection = collection;
        EventBus.getDefault().post(event);
    }

    public void removeCollection(Collection collection) {
        mCollections.remove(collection.getId());
        RemovedEvent event = new RemovedEvent();
        event.mCollection = collection;
        EventBus.getDefault().post(event);
    }

    public Collection getCollection(String collectionId) {
        return mCollections.get(collectionId);
    }

    public java.util.Collection<Collection> getCollections() {
        return mCollections.values();
    }

    /**
     * Store the PlaybackService's currentPlaylist
     */
    public void setCachedPlaylist(Playlist playlist) {
        DatabaseHelper.getInstance().storePlaylist(playlist, false);
    }

    /**
     * @return the previously cached {@link Playlist}
     */
    public Playlist getCachedPlaylist() {
        return DatabaseHelper.getInstance().getCachedPlaylist();
    }

    /**
     * Remove or add a lovedItem-query from the LovedItems-Playlist, depending on whether or not it
     * is already a lovedItem
     */
    public void toggleLovedItem(Query query) {
        boolean doSweetSweetLovin = !DatabaseHelper.getInstance().isItemLoved(query);
        Log.d(TAG, "Hatchet sync - " + (doSweetSweetLovin ? "loved" : "unloved") + " track "
                + query.getName() + " by " + query.getArtist().getName() + " on "
                + query.getAlbum().getName());
        DatabaseHelper.getInstance().setLovedItem(query, doSweetSweetLovin);
        UpdatedEvent event = new UpdatedEvent();
        event.mUpdatedItemIds = new HashSet<>();
        event.mUpdatedItemIds.add(query.getCacheKey());
        EventBus.getDefault().post(event);
        AuthenticatorUtils hatchetAuthUtils = AuthenticatorManager.getInstance()
                .getAuthenticatorUtils(TomahawkApp.PLUGINNAME_HATCHET);
        InfoSystem.getInstance().sendSocialActionPostStruct(hatchetAuthUtils, query,
                HatchetInfoPlugin.HATCHET_SOCIALACTION_TYPE_LOVE, doSweetSweetLovin);
    }

    public void toggleLovedItem(Artist artist) {
        boolean doSweetSweetLovin = !DatabaseHelper.getInstance().isItemLoved(artist);
        Log.d(TAG, "Hatchet sync - " + (doSweetSweetLovin ? "starred" : "unstarred") + " artist "
                + artist.getName());
        DatabaseHelper.getInstance().setLovedItem(artist, doSweetSweetLovin);
        UpdatedEvent event = new UpdatedEvent();
        event.mUpdatedItemIds = new HashSet<>();
        event.mUpdatedItemIds.add(artist.getCacheKey());
        EventBus.getDefault().post(event);
        AuthenticatorUtils hatchetAuthUtils = AuthenticatorManager.getInstance()
                .getAuthenticatorUtils(TomahawkApp.PLUGINNAME_HATCHET);
        InfoSystem.getInstance().sendSocialActionPostStruct(hatchetAuthUtils, artist,
                HatchetInfoPlugin.HATCHET_SOCIALACTION_TYPE_LOVE, doSweetSweetLovin);
    }

    public void toggleLovedItem(Album album) {
        boolean doSweetSweetLovin = !DatabaseHelper.getInstance().isItemLoved(album);
        Log.d(TAG, "Hatchet sync - " + (doSweetSweetLovin ? "starred" : "unstarred") + " album "
                + album.getName() + " by " + album.getArtist().getName());
        DatabaseHelper.getInstance().setLovedItem(album, doSweetSweetLovin);
        UpdatedEvent event = new UpdatedEvent();
        event.mUpdatedItemIds = new HashSet<>();
        event.mUpdatedItemIds.add(album.getCacheKey());
        EventBus.getDefault().post(event);
        AuthenticatorUtils hatchetAuthUtils = AuthenticatorManager.getInstance()
                .getAuthenticatorUtils(TomahawkApp.PLUGINNAME_HATCHET);
        InfoSystem.getInstance().sendSocialActionPostStruct(hatchetAuthUtils, album,
                HatchetInfoPlugin.HATCHET_SOCIALACTION_TYPE_LOVE, doSweetSweetLovin);
    }

    /**
     * Update the loved items user-playlist and the contained queries.
     */
    private void ensureLovedItemsPlaylist() {
        Playlist lovedItemsPlayList =
                DatabaseHelper.getInstance().getPlaylist(DatabaseHelper.LOVEDITEMS_PLAYLIST_ID);
        if (lovedItemsPlayList == null) {
            // If we don't yet have a Playlist to store loved items, we create and store an
            // empty Playlist here
            Playlist playlist = Playlist.fromQueryList(DatabaseHelper.LOVEDITEMS_PLAYLIST_NAME,
                    new ArrayList<Query>());
            playlist.setId(DatabaseHelper.LOVEDITEMS_PLAYLIST_ID);
            DatabaseHelper.getInstance().storePlaylist(playlist, false);
        }
    }

    /**
     * Fetch the lovedItems Playlist from the Hatchet API and store it in the local db, if the log
     * of pending operations is empty. Meaning if every love/unlove has already been delivered to
     * the API.
     */
    public void fetchLovedItemsPlaylist() {
        HatchetAuthenticatorUtils hatchetAuthUtils = (HatchetAuthenticatorUtils)
                AuthenticatorManager.getInstance().getAuthenticatorUtils(
                        TomahawkApp.PLUGINNAME_HATCHET);
        if (DatabaseHelper.getInstance().getLoggedOpsCount() == 0) {
            Log.d(TAG, "Hatchet sync - fetching loved tracks");
            String requestId = InfoSystem.getInstance().resolveFavorites(
                    hatchetAuthUtils.getLoggedInUser());
            if (requestId != null) {
                mCorrespondingRequestIds.add(requestId);
            }
        } else {
            Log.d(TAG, "Hatchet sync - sending logged ops before fetching loved tracks");
            InfoSystem.getInstance().sendLoggedOps(hatchetAuthUtils);
        }
    }

    /**
     * Fetch the starred artists from the Hatchet API and store it in the local db, if the log of
     * pending operations is empty. Meaning if every love/unlove has already been delivered to the
     * API.
     */
    public void fetchStarredArtists() {
        HatchetAuthenticatorUtils hatchetAuthUtils = (HatchetAuthenticatorUtils)
                AuthenticatorManager.getInstance().getAuthenticatorUtils(
                        TomahawkApp.PLUGINNAME_HATCHET);
        if (DatabaseHelper.getInstance().getLoggedOpsCount() == 0) {
            Log.d(TAG, "Hatchet sync - fetching starred artists");
            mCorrespondingRequestIds.add(InfoSystem.getInstance().
                    resolveStarredArtists(hatchetAuthUtils.getLoggedInUser()));
        } else {
            Log.d(TAG, "Hatchet sync - sending logged ops before fetching starred artists");
            InfoSystem.getInstance().sendLoggedOps(hatchetAuthUtils);
        }
    }

    /**
     * Fetch the starred albums from the Hatchet API and store it in the local db, if the log of
     * pending operations is empty. Meaning if every love/unlove has already been delivered to the
     * API.
     */
    public void fetchStarredAlbums() {
        HatchetAuthenticatorUtils hatchetAuthUtils = (HatchetAuthenticatorUtils)
                AuthenticatorManager.getInstance().getAuthenticatorUtils(
                        TomahawkApp.PLUGINNAME_HATCHET);
        if (DatabaseHelper.getInstance().getLoggedOpsCount() == 0) {
            Log.d(TAG, "Hatchet sync - fetching starred albums");
            mCorrespondingRequestIds.add(InfoSystem.getInstance()
                    .resolveStarredAlbums(hatchetAuthUtils.getLoggedInUser()));
        } else {
            Log.d(TAG, "Hatchet sync - sending logged ops before fetching starred albums");
            InfoSystem.getInstance().sendLoggedOps(hatchetAuthUtils);
        }
    }

    /**
     * Fetch the Playlists from the Hatchet API and store it in the local db.
     */
    public void fetchPlaylists() {
        HatchetAuthenticatorUtils hatchetAuthUtils = (HatchetAuthenticatorUtils)
                AuthenticatorManager.getInstance().getAuthenticatorUtils(
                        TomahawkApp.PLUGINNAME_HATCHET);
        if (DatabaseHelper.getInstance().getLoggedOpsCount() == 0) {
            Log.d(TAG, "Hatchet sync - fetching playlists");
            String requestId = InfoSystem.getInstance()
                    .resolvePlaylists(hatchetAuthUtils.getLoggedInUser(), true);
            if (requestId != null) {
                mCorrespondingRequestIds.add(requestId);
            }
        } else {
            Log.d(TAG, "Hatchet sync - sending logged ops before fetching playlists");
            InfoSystem.getInstance().sendLoggedOps(hatchetAuthUtils);
        }
    }

    /**
     * Fetch the Playlist entries from the Hatchet API and store them in the local db.
     */
    public void fetchHatchetPlaylistEntries(String playlistId) {
        String hatchetId = DatabaseHelper.getInstance().getPlaylistHatchetId(playlistId);
        String name = DatabaseHelper.getInstance().getPlaylistName(playlistId);
        if (DatabaseHelper.getInstance().getLoggedOpsCount() == 0) {
            if (hatchetId != null) {
                if (!mResolvingHatchetIds.contains(hatchetId)) {
                    Log.d(TAG, "Hatchet sync - fetching entry list for playlist \"" + name
                            + "\", hatchetId: " + hatchetId);
                    mResolvingHatchetIds.add(hatchetId);
                    QueryParams params = new QueryParams();
                    params.playlist_local_id = playlistId;
                    params.playlist_id = hatchetId;
                    String requestid = InfoSystem.getInstance().resolve(
                            InfoRequestData.INFOREQUESTDATA_TYPE_PLAYLISTS, params, true);
                    mCorrespondingRequestIds.add(requestid);
                } else {
                    Log.d(TAG, "Hatchet sync - couldn't fetch entry list for playlist \""
                            + name + "\", because this playlist is already waiting for its entry "
                            + "list, hatchetId: " + hatchetId);
                }
            } else {
                Log.d(TAG, "Hatchet sync - couldn't fetch entry list for playlist \""
                        + name + "\" because hatchetId was null");
            }
        } else {
            Log.d(TAG, "Hatchet sync - sending logged ops before fetching entry list for playlist"
                    + " \"" + name + "\", hatchetId: " + hatchetId);
            AuthenticatorUtils hatchetAuthUtils = AuthenticatorManager.getInstance()
                    .getAuthenticatorUtils(TomahawkApp.PLUGINNAME_HATCHET);
            InfoSystem.getInstance().sendLoggedOps(hatchetAuthUtils);
        }
    }

    public void handleHatchetPlaylistResponse(InfoRequestData data) {
        if (data.getType() == InfoRequestData.INFOREQUESTDATA_TYPE_USERS_PLAYLISTS) {
            List<Playlist> storedLists = DatabaseHelper.getInstance().getPlaylists();
            HashMap<String, Playlist> storedListsMap = new HashMap<>();
            for (Playlist storedList : storedLists) {
                if (storedListsMap.containsKey(storedList.getHatchetId())) {
                    Log.e(TAG, "Hatchet sync - playlist \"" + storedList.getName()
                            + "\" is duplicated ... deleting");
                    DatabaseHelper.getInstance().deletePlaylist(storedList.getId());
                } else {
                    storedListsMap.put(storedList.getHatchetId(), storedList);
                }
            }
            List<Playlist> fetchedLists = data.getResultList(Playlist.class);
            Log.d(TAG, "Hatchet sync - playlist count in database: " + storedLists.size()
                    + ", playlist count on Hatchet: " + fetchedLists.size());
            for (final Playlist fetchedList : fetchedLists) {
                Playlist storedList = storedListsMap.remove(fetchedList.getHatchetId());
                if (storedList == null) {
                    if (mShowAsDeletedPlaylistMap.contains(fetchedList.getHatchetId())) {
                        Log.d(TAG, "Hatchet sync - playlist \"" + fetchedList.getName()
                                + "\" didn't exist in database, but was marked as showAsDeleted so"
                                + " we don't store it.");
                    } else {
                        if (mShowAsCreatedPlaylistMap.contains(fetchedList.getHatchetId())) {
                            mShowAsCreatedPlaylistMap.remove(fetchedList.getHatchetId());
                            Log.d(TAG, "Hatchet sync - playlist \"" + fetchedList.getName()
                                    + "\" is no longer marked as showAsCreated, since it seems to "
                                    + "have arrived on the server");
                        }
                        Log.d(TAG, "Hatchet sync - playlist \"" + fetchedList.getName()
                                + "\" didn't exist in database ... storing and fetching entries");
                        // Delete the current revision since we don't want to store it until we have
                        // fetched and added the playlist's entries
                        fetchedList.setCurrentRevision("");
                        DatabaseHelper.getInstance().storePlaylist(fetchedList, false);
                        fetchHatchetPlaylistEntries(fetchedList.getId());
                    }
                } else if (!storedList.getCurrentRevision()
                        .equals(fetchedList.getCurrentRevision())) {
                    Log.d(TAG, "Hatchet sync - revision differed for playlist \""
                            + fetchedList.getName() + "\" ... fetching entries");
                    fetchHatchetPlaylistEntries(storedList.getId());
                } else if (!storedList.getName().equals(fetchedList.getName())) {
                    Log.d(TAG, "Hatchet sync - title differed for playlist \""
                            + storedList.getName() + "\", new name: \"" + fetchedList.getName()
                            + "\" ... renaming");
                    DatabaseHelper.getInstance().renamePlaylist(storedList, fetchedList.getName());
                }
            }
            for (Playlist storedList : storedListsMap.values()) {
                if (storedList.getHatchetId() == null
                        || !mShowAsCreatedPlaylistMap.contains(storedList.getHatchetId())) {
                    Log.d(TAG, "Hatchet sync - playlist \"" + storedList.getName()
                            + "\" doesn't exist on Hatchet ... deleting");
                    DatabaseHelper.getInstance().deletePlaylist(storedList.getId());
                } else {
                    Log.d(TAG, "Hatchet sync - playlist \"" + storedList.getName()
                            + "\" doesn't exist on Hatchet, but we don't delete it since it's"
                            + " marked as showAsCreated");
                }
            }
        } else if (data.getType() == InfoRequestData.INFOREQUESTDATA_TYPE_PLAYLISTS) {
            if (data.getHttpType() == InfoRequestData.HTTPTYPE_GET) {
                Playlist filledList = data.getResult(Playlist.class);
                if (filledList != null) {
                    Log.d(TAG, "Hatchet sync - received entry list for playlist \""
                            + filledList.getName() + "\", hatchetId: " + filledList.getHatchetId()
                            + ", count: " + filledList.getEntries().size());
                    mResolvingHatchetIds.remove(filledList.getHatchetId());
                    DatabaseHelper.getInstance().storePlaylist(filledList, false);
                }
            } else if (data.getHttpType() == InfoRequestData.HTTPTYPE_POST) {
                String hatchetId = DatabaseHelper.getInstance()
                        .getPlaylistHatchetId(data.getQueryParams().playlist_local_id);
                if (hatchetId != null) {
                    mShowAsCreatedPlaylistMap.add(hatchetId);
                    Log.d(TAG, "Hatchet sync - created playlist and marked as showAsCreated, id: "
                            + data.getQueryParams().playlist_local_id + ", hatchetId: "
                            + hatchetId);
                }
            }
        } else if (data.getType() == InfoRequestData.INFOREQUESTDATA_TYPE_USERS_LOVEDITEMS) {
            Playlist fetchedList = data.getResult(Playlist.class);
            if (fetchedList != null) {
                HatchetAuthenticatorUtils hatchetAuthUtils =
                        (HatchetAuthenticatorUtils) AuthenticatorManager.getInstance()
                                .getAuthenticatorUtils(TomahawkApp.PLUGINNAME_HATCHET);
                String userName = hatchetAuthUtils.getUserName();
                fetchedList.setName(TomahawkApp.getContext()
                        .getString(R.string.users_favorites_suffix, userName));
                fetchedList.setId(DatabaseHelper.LOVEDITEMS_PLAYLIST_ID);
                Log.d(TAG, "Hatchet sync - received list of loved tracks, count: "
                        + fetchedList.getEntries().size());
                DatabaseHelper.getInstance().storePlaylist(fetchedList, true);
            }
        } else if (data.getType()
                == InfoRequestData.INFOREQUESTDATA_TYPE_RELATIONSHIPS_USERS_STARREDALBUMS) {
            List<Album> fetchedAlbums = data.getResultList(Album.class);
            Log.d(TAG, "Hatchet sync - received list of starred albums, count: "
                    + fetchedAlbums.size());
            DatabaseHelper.getInstance().storeStarredAlbums(fetchedAlbums);
        } else if (data.getType()
                == InfoRequestData.INFOREQUESTDATA_TYPE_RELATIONSHIPS_USERS_STARREDARTISTS) {
            List<Artist> fetchedArtists = data.getResultList(Artist.class);
            Log.d(TAG, "Hatchet sync - received list of starred artists, count: "
                    + fetchedArtists.size());
            DatabaseHelper.getInstance().storeStarredArtists(fetchedArtists);
        }
    }

    public void deletePlaylist(String playlistId) {
        String playlistName = DatabaseHelper.getInstance().getPlaylistName(playlistId);
        if (playlistName != null) {
            Log.d(TAG, "Hatchet sync - deleting playlist \"" + playlistName + "\", id: "
                    + playlistId);
            Playlist playlist = DatabaseHelper.getInstance().getEmptyPlaylist(playlistId);
            if (playlist.getHatchetId() != null) {
                mShowAsDeletedPlaylistMap.add(playlist.getHatchetId());
            }
            AuthenticatorUtils hatchetAuthUtils = AuthenticatorManager.getInstance()
                    .getAuthenticatorUtils(TomahawkApp.PLUGINNAME_HATCHET);
            InfoSystem.getInstance().deletePlaylist(hatchetAuthUtils, playlistId);
            DatabaseHelper.getInstance().deletePlaylist(playlistId);
        } else {
            Log.e(TAG, "Hatchet sync - couldn't delete playlist with id: " + playlistId);
        }
    }

    public void createPlaylist(Playlist playlist) {
        Log.d(TAG, "Hatchet sync - creating playlist \"" + playlist.getName() + "\", id: "
                + playlist.getId() + " with " + playlist.getEntries().size() + " entries");
        DatabaseHelper.getInstance().storePlaylist(playlist, false);
        AuthenticatorUtils hatchetAuthUtils = AuthenticatorManager.getInstance()
                .getAuthenticatorUtils(TomahawkApp.PLUGINNAME_HATCHET);
        List<String> requestIds = InfoSystem.getInstance()
                .sendPlaylistPostStruct(hatchetAuthUtils, playlist.getId(), playlist.getName());
        if (requestIds != null) {
            mCorrespondingRequestIds.addAll(requestIds);
        }
        for (PlaylistEntry entry : playlist.getEntries()) {
            InfoSystem.getInstance().sendPlaylistEntriesPostStruct(hatchetAuthUtils,
                    playlist.getId(), entry.getName(), entry.getArtist().getName(),
                    entry.getAlbum().getName());
        }
    }

    public void addPlaylistEntries(String playlistId, ArrayList<PlaylistEntry> entries) {
        String playlistName = DatabaseHelper.getInstance().getPlaylistName(playlistId);
        if (playlistName != null) {
            Log.d(TAG, "Hatchet sync - adding " + entries.size() + " entries to \""
                    + playlistName + "\", id: " + playlistId);
            DatabaseHelper.getInstance().addEntriesToPlaylist(playlistId, entries);
            AuthenticatorUtils hatchetAuthUtils = AuthenticatorManager.getInstance()
                    .getAuthenticatorUtils(TomahawkApp.PLUGINNAME_HATCHET);
            for (PlaylistEntry entry : entries) {
                InfoSystem.getInstance().sendPlaylistEntriesPostStruct(hatchetAuthUtils, playlistId,
                        entry.getName(), entry.getArtist().getName(), entry.getAlbum().getName());
            }
        } else {
            Log.e(TAG, "Hatchet sync - couldn't add " + entries.size()
                    + " entries to playlist with id: " + playlistId);
        }
    }

    public void deletePlaylistEntry(String playlistId, String entryId) {
        String playlistName = DatabaseHelper.getInstance().getPlaylistName(playlistId);
        if (playlistName != null) {
            Log.d(TAG, "Hatchet sync - deleting playlist entry in \"" + playlistName
                    + "\", playlistId: " + playlistId + ", entryId: " + entryId);
            DatabaseHelper.getInstance().deleteEntryInPlaylist(playlistId, entryId);
            AuthenticatorUtils hatchetAuthUtils = AuthenticatorManager.getInstance()
                    .getAuthenticatorUtils(TomahawkApp.PLUGINNAME_HATCHET);
            InfoSystem.getInstance().deletePlaylistEntry(hatchetAuthUtils, playlistId, entryId);
        } else {
            Log.e(TAG, "Hatchet sync - couldn't delete entry in playlist, playlistId: "
                    + playlistId + ", entryId: " + entryId);
        }
    }

    public Promise<List<Collection>, Throwable, Object> getAvailableCollections(Artist artist) {
        return getAvailableCollections((Object) artist);
    }

    public Promise<List<Collection>, Throwable, Object> getAvailableCollections(Album album) {
        return getAvailableCollections((Object) album);
    }

    private Promise<List<Collection>, Throwable, Object> getAvailableCollections(Object object) {
        final List<Collection> collections = new ArrayList<>();
        final List<Promise> deferreds = new ArrayList<>();
        for (final Collection collection : mCollections.values()) {
            if (!collection.getId().equals(TomahawkApp.PLUGINNAME_HATCHET)) {
                if (object instanceof Album) {
                    deferreds.add(collection.hasAlbumTracks((Album) object));
                } else {
                    deferreds.add(collection.hasArtistAlbums((Artist) object));
                }
                collections.add(collection);
            }
        }
        BetterDeferredManager dm = new BetterDeferredManager();
        return dm.when(deferreds).then(
                new DonePipe<MultipleResults, List<Collection>, Throwable, Object>() {
                    @Override
                    public Promise<List<Collection>, Throwable, Object> pipeDone(
                            MultipleResults result) {
                        List<Collection> availableCollections = new ArrayList<>();
                        for (int i = 0; i < result.size(); i++) {
                            Object boolResult = result.get(i).getResult();
                            if ((Boolean) boolResult) {
                                availableCollections.add(collections.get(i));
                            }
                        }
                        availableCollections
                                .add(mCollections.get(TomahawkApp.PLUGINNAME_HATCHET));
                        return new ADeferredObject<List<Collection>, Throwable, Object>()
                                .resolve(availableCollections);
                    }
                }
        );
    }
}


File: src/org/tomahawk/libtomahawk/collection/HatchetCollection.java
/* == This file is part of Tomahawk Player - <http://tomahawk-player.org> ===
 *
 *   Copyright 2014, Enno Gottschalk <mrmaffen@googlemail.com>
 *
 *   Tomahawk is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   Tomahawk is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with Tomahawk. If not, see <http://www.gnu.org/licenses/>.
 */
package org.tomahawk.libtomahawk.collection;

import org.jdeferred.Promise;
import org.tomahawk.libtomahawk.resolver.Query;
import org.tomahawk.libtomahawk.utils.BetterDeferredManager;
import org.tomahawk.libtomahawk.utils.TomahawkUtils;
import org.tomahawk.tomahawk_android.R;
import org.tomahawk.tomahawk_android.TomahawkApp;

import android.widget.ImageView;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.ConcurrentHashMap;

/**
 * This class holds the metadata retrieved via Hatchet.
 */
public class HatchetCollection extends NativeCollection {

    private final ConcurrentHashMap<Artist, List<Query>> mArtistTopHits
            = new ConcurrentHashMap<>();

    public HatchetCollection() {
        super(TomahawkApp.PLUGINNAME_HATCHET, "", true);
    }

    public void addArtistTopHits(Artist artist, List<Query> topHits) {
        mArtistTopHits.put(artist, topHits);
    }

    /**
     * @return A {@link java.util.List} of all top hits {@link Track}s from the given Artist.
     */
    public Promise<List<Query>, Throwable, Void> getArtistTopHits(final Artist artist) {
        BetterDeferredManager dm = new BetterDeferredManager();
        return dm.when(new Callable<List<Query>>() {
            @Override
            public List<Query> call() throws Exception {
                List<Query> queries = new ArrayList<>();
                if (mArtistTopHits.get(artist) != null) {
                    queries.addAll(mArtistTopHits.get(artist));
                }
                return queries;
            }
        });
    }

    @Override
    public void loadIcon(ImageView imageView, boolean grayOut) {
        TomahawkUtils.loadDrawableIntoImageView(TomahawkApp.getContext(), imageView,
                R.drawable.ic_hatchet, grayOut);
    }
}


File: src/org/tomahawk/libtomahawk/collection/NativeCollection.java
/* == This file is part of Tomahawk Player - <http://tomahawk-player.org> ===
 *
 *   Copyright 2014, Enno Gottschalk <mrmaffen@googlemail.com>
 *
 *   Tomahawk is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   Tomahawk is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with Tomahawk. If not, see <http://www.gnu.org/licenses/>.
 */
package org.tomahawk.libtomahawk.collection;

import org.jdeferred.Deferred;
import org.jdeferred.Promise;
import org.tomahawk.libtomahawk.resolver.Query;
import org.tomahawk.libtomahawk.utils.ADeferredObject;
import org.tomahawk.libtomahawk.utils.BetterDeferredManager;

import android.text.TextUtils;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.ConcurrentHashMap;

public abstract class NativeCollection extends Collection {

    private final boolean mIsLocal;

    protected Set<Album> mAlbums =
            Collections.newSetFromMap(new ConcurrentHashMap<Album, Boolean>());

    protected Set<Artist> mArtists =
            Collections.newSetFromMap(new ConcurrentHashMap<Artist, Boolean>());

    protected Set<Artist> mAlbumArtists =
            Collections.newSetFromMap(new ConcurrentHashMap<Artist, Boolean>());

    protected Set<Query> mQueries =
            Collections.newSetFromMap(new ConcurrentHashMap<Query, Boolean>());

    protected ConcurrentHashMap<Album, Set<Query>> mAlbumTracks
            = new ConcurrentHashMap<>();

    protected ConcurrentHashMap<Artist, Set<Album>> mArtistAlbums
            = new ConcurrentHashMap<>();

    protected final ConcurrentHashMap<Query, Long> mQueryTimeStamps
            = new ConcurrentHashMap<>();

    protected final ConcurrentHashMap<Artist, Long> mArtistTimeStamps
            = new ConcurrentHashMap<>();

    protected final ConcurrentHashMap<Album, Long> mAlbumTimeStamps
            = new ConcurrentHashMap<>();

    protected NativeCollection(String id, String name, boolean isLocal) {
        super(id, name);

        mIsLocal = isLocal;
    }

    public boolean isLocal() {
        return mIsLocal;
    }

    public void wipe() {
        mQueries.clear();
        mArtists.clear();
        mAlbums.clear();
        mAlbumTracks.clear();
        mArtistAlbums.clear();
    }

    public void addQuery(Query query, long addedTimeStamp) {
        if (!TextUtils.isEmpty(query.getName())) {
            mQueries.add(query);
        }
        if (addedTimeStamp > 0) {
            if (mAlbumTimeStamps.get(query.getAlbum()) == null
                    || mAlbumTimeStamps.get(query.getAlbum()) < addedTimeStamp) {
                mAlbumTimeStamps.put(query.getAlbum(), addedTimeStamp);
            }
            if (mArtistTimeStamps.get(query.getArtist()) == null
                    || mArtistTimeStamps.get(query.getArtist()) < addedTimeStamp) {
                mArtistTimeStamps.put(query.getArtist(), addedTimeStamp);
            }
            mQueryTimeStamps.put(query, addedTimeStamp);
        }
    }

    @Override
    public Promise<Set<Query>, Throwable, Void> getQueries() {
        BetterDeferredManager dm = new BetterDeferredManager();
        return dm.when(new Callable<Set<Query>>() {
            @Override
            public Set<Query> call() throws Exception {
                return mQueries;
            }
        });
    }

    public void addArtist(Artist artist) {
        mArtists.add(artist);
    }

    @Override
    public Promise<Set<Artist>, Throwable, Void> getArtists() {
        BetterDeferredManager dm = new BetterDeferredManager();
        return dm.when(new Callable<Set<Artist>>() {
            @Override
            public Set<Artist> call() throws Exception {
                return mArtists;
            }
        });
    }

    public void addAlbumArtist(Artist artist) {
        mAlbumArtists.add(artist);
    }

    @Override
    public Promise<Set<Artist>, Throwable, Void> getAlbumArtists() {
        BetterDeferredManager dm = new BetterDeferredManager();
        return dm.when(new Callable<Set<Artist>>() {
            @Override
            public Set<Artist> call() throws Exception {
                return mAlbumArtists;
            }
        });
    }

    public void addAlbum(Album album) {
        mAlbums.add(album);
    }

    @Override
    public Promise<Set<Album>, Throwable, Void> getAlbums() {
        BetterDeferredManager dm = new BetterDeferredManager();
        return dm.when(new Callable<Set<Album>>() {
            @Override
            public Set<Album> call() throws Exception {
                return new HashSet<>(mAlbums);
            }
        });
    }

    public void addArtistAlbum(Artist artist, Album album) {
        if (mArtistAlbums.get(artist) == null) {
            mArtistAlbums.put(artist, new HashSet<Album>());
        }
        mArtistAlbums.get(artist).add(album);
    }

    @Override
    public Promise<List<Album>, Throwable, Void> getArtistAlbums(final Artist artist) {
        BetterDeferredManager dm = new BetterDeferredManager();
        return dm.when(new Callable<List<Album>>() {
            @Override
            public List<Album> call() throws Exception {
                List<Album> albums = new ArrayList<>();
                if (mArtistAlbums.get(artist) != null) {
                    albums.addAll(mArtistAlbums.get(artist));
                }
                return albums;
            }
        });
    }

    public Promise<Boolean, Throwable, Void> hasArtistAlbums(Artist artist) {
        final Deferred<Boolean, Throwable, Void> deferred = new ADeferredObject<>();
        return deferred
                .resolve(mArtistAlbums.get(artist) != null && mArtistAlbums.get(artist).size() > 0);
    }

    public void addAlbumTracks(Album album, Set<Query> queries) {
        mAlbumTracks.put(album, queries);
    }

    public void addAlbumTrack(Album album, Query query) {
        if (mAlbumTracks.get(album) == null) {
            mAlbumTracks.put(album, new HashSet<Query>());
        }
        mAlbumTracks.get(album).add(query);
    }

    @Override
    public Promise<List<Query>, Throwable, Void> getAlbumTracks(final Album album) {
        BetterDeferredManager dm = new BetterDeferredManager();
        return dm.when(new Callable<List<Query>>() {
            @Override
            public List<Query> call() throws Exception {
                List<Query> queries = new ArrayList<>();
                if (mAlbumTracks.get(album) != null) {
                    queries.addAll(mAlbumTracks.get(album));
                }
                return queries;
            }
        });
    }

    public Promise<Boolean, Throwable, Void> hasAlbumTracks(Album album) {
        Deferred<Boolean, Throwable, Void> deferred = new ADeferredObject<>();
        return deferred
                .resolve(mAlbumTracks.get(album) != null && mAlbumTracks.get(album).size() > 0);
    }

    public ConcurrentHashMap<Query, Long> getQueryTimeStamps() {
        return mQueryTimeStamps;
    }

    public ConcurrentHashMap<Artist, Long> getArtistTimeStamps() {
        return mArtistTimeStamps;
    }

    public ConcurrentHashMap<Album, Long> getAlbumTimeStamps() {
        return mAlbumTimeStamps;
    }
}


File: src/org/tomahawk/libtomahawk/collection/ScriptResolverCollection.java
/* == This file is part of Tomahawk Player - <http://tomahawk-player.org> ===
 *
 *   Copyright 2014, Enno Gottschalk <mrmaffen@googlemail.com>
 *
 *   Tomahawk is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   Tomahawk is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with Tomahawk. If not, see <http://www.gnu.org/licenses/>.
 */
package org.tomahawk.libtomahawk.collection;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;

import org.jdeferred.Deferred;
import org.jdeferred.DoneCallback;
import org.jdeferred.Promise;
import org.tomahawk.libtomahawk.resolver.Query;
import org.tomahawk.libtomahawk.resolver.Result;
import org.tomahawk.libtomahawk.resolver.ScriptAccount;
import org.tomahawk.libtomahawk.resolver.ScriptJob;
import org.tomahawk.libtomahawk.resolver.ScriptObject;
import org.tomahawk.libtomahawk.resolver.ScriptPlugin;
import org.tomahawk.libtomahawk.resolver.ScriptUtils;
import org.tomahawk.libtomahawk.resolver.models.ScriptResolverCollectionMetaData;
import org.tomahawk.libtomahawk.utils.ADeferredObject;
import org.tomahawk.libtomahawk.utils.TomahawkUtils;
import org.tomahawk.tomahawk_android.TomahawkApp;

import android.util.Log;
import android.widget.ImageView;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * This class represents a Collection which contains tracks/albums/artists retrieved by a
 * ScriptResolver.
 */
public class ScriptResolverCollection extends Collection implements ScriptPlugin {

    private final static String TAG = ScriptResolverCollection.class.getSimpleName();

    private Set<Album> mCachedAlbums;

    private Set<Artist> mCachedArtists;

    private Set<Artist> mCachedAlbumArtists;

    private Set<Query> mCachedQueries;

    private ScriptObject mScriptObject;

    private ScriptAccount mScriptAccount;

    private ScriptResolverCollectionMetaData mMetaData;

    public ScriptResolverCollection(ScriptObject object, ScriptAccount account) {
        super(account.getScriptResolver().getId(), account.getName());

        mScriptObject = object;
        mScriptAccount = account;

        // initialize everything
        getAlbums();
        getQueries();
        getArtists();
    }

    public Deferred<ScriptResolverCollectionMetaData, String, Object> getMetaData() {
        final Deferred<ScriptResolverCollectionMetaData, String, Object> deferred
                = new ADeferredObject<>();
        if (mMetaData == null) {
            ScriptJob.start(mScriptObject, "settings",
                    new ScriptJob.ResultsCallback<ScriptResolverCollectionMetaData>(
                            ScriptResolverCollectionMetaData.class) {
                        @Override
                        public void onReportResults(ScriptResolverCollectionMetaData results) {
                            mMetaData = results;
                            deferred.resolve(results);
                        }
                    });
        } else {
            deferred.resolve(mMetaData);
        }
        return deferred;
    }

    @Override
    public ScriptObject getScriptObject() {
        return mScriptObject;
    }

    @Override
    public ScriptAccount getScriptAccount() {
        return mScriptAccount;
    }

    @Override
    public void start(ScriptJob job) {
        mScriptAccount.startJob(job);
    }

    @Override
    public void loadIcon(final ImageView imageView, final boolean grayOut) {
        getMetaData().done(new DoneCallback<ScriptResolverCollectionMetaData>() {
            @Override
            public void onDone(ScriptResolverCollectionMetaData result) {
                String completeIconPath = "file:///android_asset/" + mScriptAccount.getPath()
                        + "/content/" + result.iconfile;
                TomahawkUtils.loadDrawableIntoImageView(TomahawkApp.getContext(), imageView,
                        completeIconPath);
            }
        });
    }

    @Override
    public Promise<Set<Query>, Throwable, Void> getQueries() {
        final Deferred<Set<Query>, Throwable, Void> deferred = new ADeferredObject<>();
        if (mCachedQueries != null) {
            deferred.resolve(mCachedQueries);
        } else {
            getMetaData().done(new DoneCallback<ScriptResolverCollectionMetaData>() {
                @Override
                public void onDone(ScriptResolverCollectionMetaData result) {
                    HashMap<String, Object> a = new HashMap<>();
                    a.put("id", result.id);
                    final long timeBefore = System.currentTimeMillis();
                    ScriptJob.start(mScriptObject, "tracks", a,
                            new ScriptJob.ResultsArrayCallback() {
                                @Override
                                public void onReportResults(JsonArray results) {
                                    Log.d(TAG,
                                            "Received " + results.size() + " trackResults in " + (
                                                    System.currentTimeMillis() - timeBefore)
                                                    + "ms");
                                    long time = System.currentTimeMillis();
                                    ArrayList<Result> parsedResults = ScriptUtils.parseResultList(
                                            mScriptAccount.getScriptResolver(), results);
                                    Log.d(TAG,
                                            "Parsed " + parsedResults.size() + " trackResults in "
                                                    + (
                                                    System.currentTimeMillis() - time) + "ms");
                                    time = System.currentTimeMillis();
                                    Set<Query> queries = new HashSet<>();
                                    for (Result r : parsedResults) {
                                        Query query = Query.get(r, false);
                                        query.addTrackResult(r, 1f);
                                        queries.add(query);
                                    }
                                    Log.d(TAG, "Converted " + parsedResults.size()
                                            + " trackResults in " + (
                                            System.currentTimeMillis() - time) + "ms");
                                    mCachedQueries = queries;
                                    deferred.resolve(queries);
                                }
                            });
                }
            });
        }
        return deferred;
    }

    @Override
    public Promise<Set<Artist>, Throwable, Void> getArtists() {
        final Deferred<Set<Artist>, Throwable, Void> deferred = new ADeferredObject<>();
        if (mCachedArtists != null) {
            deferred.resolve(mCachedArtists);
        } else {
            getMetaData().done(new DoneCallback<ScriptResolverCollectionMetaData>() {
                @Override
                public void onDone(ScriptResolverCollectionMetaData result) {
                    HashMap<String, Object> a = new HashMap<>();
                    a.put("id", result.id);
                    final long timeBefore = System.currentTimeMillis();
                    ScriptJob.start(mScriptObject, "artists", a,
                            new ScriptJob.ResultsArrayCallback() {
                                @Override
                                public void onReportResults(JsonArray results) {
                                    Log.d(TAG,
                                            "Received " + results.size() + " artistResults in " + (
                                                    System.currentTimeMillis() - timeBefore)
                                                    + "ms");
                                    long time = System.currentTimeMillis();
                                    Set<Artist> artists = new HashSet<>();
                                    for (JsonElement result : results) {
                                        Artist artist = Artist
                                                .get(ScriptUtils
                                                        .getNodeChildAsText(result, "artist"));
                                        artists.add(artist);
                                    }
                                    Log.d(TAG,
                                            "Converted " + artists.size() + " artistResults in " + (
                                                    System.currentTimeMillis() - time) + "ms");
                                    mCachedArtists = artists;
                                    deferred.resolve(artists);
                                }
                            });
                }
            });
        }
        return deferred;
    }

    @Override
    public Promise<Set<Artist>, Throwable, Void> getAlbumArtists() {
        final Deferred<Set<Artist>, Throwable, Void> deferred = new ADeferredObject<>();
        if (mCachedAlbumArtists != null) {
            deferred.resolve(mCachedAlbumArtists);
        } else {
            getMetaData().done(new DoneCallback<ScriptResolverCollectionMetaData>() {
                @Override
                public void onDone(ScriptResolverCollectionMetaData result) {
                    HashMap<String, Object> a = new HashMap<>();
                    a.put("id", result.id);
                    ScriptJob.start(mScriptObject, "albumArtists", a,
                            new ScriptJob.ResultsArrayCallback() {
                                @Override
                                public void onReportResults(JsonArray results) {
                                    Set<Artist> artists = new HashSet<>();
                                    for (JsonElement result : results) {
                                        Artist artist = Artist.get(
                                                ScriptUtils
                                                        .getNodeChildAsText(result, "albumArtist"));
                                        artists.add(artist);
                                    }
                                    mCachedAlbumArtists = artists;
                                    deferred.resolve(artists);
                                }
                            });
                }
            });
        }
        return deferred;
    }

    @Override
    public Promise<Set<Album>, Throwable, Void> getAlbums() {
        final Deferred<Set<Album>, Throwable, Void> deferred = new ADeferredObject<>();
        if (mCachedAlbums != null) {
            deferred.resolve(mCachedAlbums);
        } else {
            getMetaData().done(new DoneCallback<ScriptResolverCollectionMetaData>() {
                @Override
                public void onDone(ScriptResolverCollectionMetaData result) {
                    final HashMap<String, Object> a = new HashMap<>();
                    a.put("id", result.id);
                    final long timeBefore = System.currentTimeMillis();
                    ScriptJob.start(mScriptObject, "albums", a,
                            new ScriptJob.ResultsArrayCallback() {
                                @Override
                                public void onReportResults(JsonArray results) {
                                    Log.d(TAG,
                                            "Received " + results.size() + " albumResults in " + (
                                                    System.currentTimeMillis() - timeBefore)
                                                    + "ms");
                                    long time = System.currentTimeMillis();
                                    Set<Album> albums = new HashSet<>();
                                    for (JsonElement result : results) {
                                        Artist albumArtist = Artist.get(
                                                ScriptUtils
                                                        .getNodeChildAsText(result, "albumArtist"));
                                        Album album = Album.get(
                                                ScriptUtils.getNodeChildAsText(result, "album"),
                                                albumArtist);
                                        albums.add(album);
                                    }
                                    Log.d(TAG,
                                            "Converted " + albums.size() + " albumResults in " + (
                                                    System.currentTimeMillis() - time) + "ms");
                                    mCachedAlbums = albums;
                                    deferred.resolve(albums);
                                }
                            });
                }
            });
        }
        return deferred;
    }

    @Override
    public Promise<List<Album>, Throwable, Void> getArtistAlbums(final Artist artist) {
        final Deferred<List<Album>, Throwable, Void> deferred = new ADeferredObject<>();
        getMetaData().done(new DoneCallback<ScriptResolverCollectionMetaData>() {
            @Override
            public void onDone(ScriptResolverCollectionMetaData result) {
                HashMap<String, Object> a = new HashMap<>();
                a.put("id", result.id);
                a.put("artist", artist.getName());
                a.put("artistDisambiguation", "");
                ScriptJob.start(mScriptObject, "artistAlbums", a,
                        new ScriptJob.ResultsArrayCallback() {
                            @Override
                            public void onReportResults(JsonArray results) {
                                List<Album> albums = new ArrayList<>();
                                for (JsonElement result : results) {
                                    Artist albumArtist = Artist.get(
                                            ScriptUtils.getNodeChildAsText(result, "albumArtist"));
                                    Album album = Album.get(
                                            ScriptUtils.getNodeChildAsText(result, "album"),
                                            albumArtist);
                                    albums.add(album);
                                }
                                deferred.resolve(albums);
                            }
                        });
            }
        });
        return deferred;
    }

    @Override
    public Promise<Boolean, Throwable, Void> hasArtistAlbums(final Artist artist) {
        final Deferred<Boolean, Throwable, Void> deferred = new ADeferredObject<>();
        getMetaData().done(new DoneCallback<ScriptResolverCollectionMetaData>() {
            @Override
            public void onDone(ScriptResolverCollectionMetaData result) {
                HashMap<String, Object> a = new HashMap<>();
                a.put("id", result.id);
                a.put("artist", artist.getName());
                a.put("artistDisambiguation", "");
                ScriptJob.start(mScriptObject, "artistAlbums", a,
                        new ScriptJob.ResultsArrayCallback() {
                            @Override
                            public void onReportResults(JsonArray results) {
                                deferred.resolve(results.size() > 0);
                            }
                        }, new ScriptJob.FailureCallback() {
                            @Override
                            public void onReportFailure(String errormessage) {
                                deferred.resolve(false);
                            }
                        });
            }
        });
        return deferred;
    }

    @Override
    public Promise<List<Query>, Throwable, Void> getAlbumTracks(final Album album) {
        final Deferred<List<Query>, Throwable, Void> deferred = new ADeferredObject<>();
        final long time = System.currentTimeMillis();
        getMetaData().done(new DoneCallback<ScriptResolverCollectionMetaData>() {
            @Override
            public void onDone(ScriptResolverCollectionMetaData result) {
                Log.d("perftest", "getMetadata in " + (System.currentTimeMillis() - time) + "ms");
                HashMap<String, Object> a = new HashMap<>();
                a.put("id", result.id);
                a.put("albumArtist", album.getArtist().getName());
                a.put("albumArtistDisambiguation", "");
                a.put("album", album.getName());
                final long time = System.currentTimeMillis();
                ScriptJob.start(mScriptObject, "albumTracks", a,
                        new ScriptJob.ResultsArrayCallback() {
                            @Override
                            public void onReportResults(JsonArray results) {
                                Log.d("perftest",
                                        "albumTracks in " + (System.currentTimeMillis() - time)
                                                + "ms");
                                long time = System.currentTimeMillis();
                                ArrayList<Result> parsedResults = ScriptUtils.parseResultList(
                                        mScriptAccount.getScriptResolver(), results);
                                Log.d("perftest",
                                        "albumTracks parsed in " + (System.currentTimeMillis()
                                                - time) + "ms");
                                time = System.currentTimeMillis();
                                List<Query> queries = new ArrayList<>();
                                for (Result r : parsedResults) {
                                    Query query = Query.get(r, false);
                                    float trackScore = query.howSimilar(r);
                                    query.addTrackResult(r, trackScore);
                                    queries.add(query);
                                }
                                Log.d("perftest",
                                        "albumTracks converted in " + (System.currentTimeMillis()
                                                - time) + "ms");
                                deferred.resolve(queries);
                            }
                        });
            }
        });
        return deferred;
    }

    @Override
    public Promise<Boolean, Throwable, Void> hasAlbumTracks(final Album album) {
        final Deferred<Boolean, Throwable, Void> deferred = new ADeferredObject<>();
        getMetaData().done(new DoneCallback<ScriptResolverCollectionMetaData>() {
            @Override
            public void onDone(ScriptResolverCollectionMetaData result) {
                HashMap<String, Object> a = new HashMap<>();
                a.put("id", result.id);
                a.put("albumArtist", album.getArtist().getName());
                a.put("albumArtistDisambiguation", "");
                a.put("album", album.getName());
                ScriptJob.start(mScriptObject, "albumTracks", a,
                        new ScriptJob.ResultsArrayCallback() {
                            @Override
                            public void onReportResults(JsonArray results) {
                                deferred.resolve(results.size() > 0);
                            }
                        }, new ScriptJob.FailureCallback() {
                            @Override
                            public void onReportFailure(String errormessage) {
                                deferred.resolve(false);
                            }
                        });
            }
        });
        return deferred;
    }
}


File: src/org/tomahawk/libtomahawk/collection/UserCollection.java
/* == This file is part of Tomahawk Player - <http://tomahawk-player.org> ===
 *
 *   Copyright 2012, Christopher Reichert <creichert07@gmail.com>
 *   Copyright 2012, Enno Gottschalk <mrmaffen@googlemail.com>
 *
 *   Tomahawk is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   Tomahawk is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with Tomahawk. If not, see <http://www.gnu.org/licenses/>.
 */
package org.tomahawk.libtomahawk.collection;

import org.tomahawk.libtomahawk.database.DatabaseHelper;
import org.tomahawk.libtomahawk.resolver.PipeLine;
import org.tomahawk.libtomahawk.resolver.Query;
import org.tomahawk.libtomahawk.resolver.Resolver;
import org.tomahawk.libtomahawk.resolver.Result;
import org.tomahawk.tomahawk_android.R;
import org.tomahawk.tomahawk_android.TomahawkApp;
import org.tomahawk.tomahawk_android.mediaplayers.VLCMediaPlayer;
import org.tomahawk.tomahawk_android.utils.MediaWrapper;
import org.tomahawk.tomahawk_android.utils.WeakReferenceHandler;
import org.videolan.libvlc.LibVLC;
import org.videolan.libvlc.Media;
import org.videolan.libvlc.util.Extensions;

import android.content.SharedPreferences;
import android.os.Environment;
import android.os.Looper;
import android.os.Message;
import android.preference.PreferenceManager;
import android.text.TextUtils;
import android.util.Log;
import android.widget.ImageView;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileFilter;
import java.io.FileReader;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.Stack;
import java.util.StringTokenizer;

import de.greenrobot.event.EventBus;

/**
 * This class represents a user's local {@link UserCollection}.
 */
public class UserCollection extends NativeCollection {

    private static final String TAG = UserCollection.class.getSimpleName();

    private static final String HAS_SET_DEFAULTDIRS
            = "org.tomahawk.tomahawk_android.has_set_defaultdirs";

    private boolean isStopping = false;

    private boolean mRestart = false;

    protected Thread mLoadingThread;

    public final static HashSet<String> FOLDER_BLACKLIST;

    static {
        final String[] folder_blacklist = {
                "/alarms",
                "/notifications",
                "/ringtones",
                "/media/alarms",
                "/media/notifications",
                "/media/ringtones",
                "/media/audio/alarms",
                "/media/audio/notifications",
                "/media/audio/ringtones",
                "/Android/data/"};

        FOLDER_BLACKLIST = new HashSet<>();
        for (String item : folder_blacklist) {
            FOLDER_BLACKLIST
                    .add(android.os.Environment.getExternalStorageDirectory().getPath() + item);
        }
    }

    public UserCollection() {
        super(TomahawkApp.PLUGINNAME_USERCOLLECTION,
                TomahawkApp.getContext().getString(R.string.local_collection_pretty_name), true);
    }

    @Override
    public void loadIcon(ImageView imageView, boolean grayOut) {

    }

    public int getQueryCount() {
        return mQueries.size();
    }

    public void loadMediaItems(boolean restart) {
        if (restart && isWorking()) {
            /* do a clean restart if a scan is ongoing */
            mRestart = true;
            isStopping = true;
        } else {
            loadMediaItems();
        }
    }

    public void loadMediaItems() {
        if (mLoadingThread == null || mLoadingThread.getState() == Thread.State.TERMINATED) {
            isStopping = false;
            mLoadingThread = new Thread(new GetMediaItemsRunnable());
            mLoadingThread.start();
        }
    }

    public void stop() {
        isStopping = true;
    }

    public boolean isWorking() {
        return mLoadingThread != null &&
                mLoadingThread.isAlive() &&
                mLoadingThread.getState() != Thread.State.TERMINATED &&
                mLoadingThread.getState() != Thread.State.NEW;
    }

    private class GetMediaItemsRunnable implements Runnable {

        private final Stack<File> directories = new Stack<>();

        private final HashSet<String> directoriesScanned = new HashSet<>();

        public GetMediaItemsRunnable() {
        }

        @Override
        public void run() {
            SharedPreferences preferences = PreferenceManager
                    .getDefaultSharedPreferences(TomahawkApp.getContext());
            Set<String> setDefaultDirs =
                    preferences.getStringSet(HAS_SET_DEFAULTDIRS, null);
            if (setDefaultDirs == null) {
                setDefaultDirs = new HashSet<>();
            }
            for (String defaultDir : getStorageDirectories()) {
                if (!setDefaultDirs.contains(defaultDir)) {
                    DatabaseHelper.getInstance().addMediaDir(defaultDir);
                    setDefaultDirs.add(defaultDir);
                }
            }
            preferences.edit().putStringSet(HAS_SET_DEFAULTDIRS, setDefaultDirs).commit();

            List<File> mediaDirs = DatabaseHelper.getInstance().getMediaDirs(false);
            directories.addAll(mediaDirs);

            // get all existing media items
            HashMap<String, MediaWrapper> existingMedias = DatabaseHelper.getInstance()
                    .getMedias();

            // list of all added files
            HashSet<String> addedLocations = new HashSet<>();

            MediaItemFilter mediaFileFilter = new MediaItemFilter();

            ArrayList<File> mediaToScan = new ArrayList<>();
            try {
                // Count total files, and stack them
                while (!directories.isEmpty()) {
                    File dir = directories.pop();
                    String dirPath = dir.getAbsolutePath();

                    // Skip some system folders
                    if (dirPath.startsWith("/proc/") || dirPath.startsWith("/sys/") || dirPath
                            .startsWith("/dev/")) {
                        continue;
                    }

                    // Do not scan again if same canonical path
                    try {
                        dirPath = dir.getCanonicalPath();
                    } catch (IOException e) {
                        e.printStackTrace();
                    }
                    if (directoriesScanned.contains(dirPath)) {
                        continue;
                    } else {
                        directoriesScanned.add(dirPath);
                    }

                    // Do no scan media in .nomedia folders
                    if (new File(dirPath + "/.nomedia").exists()) {
                        continue;
                    }

                    // Filter the extensions and the folders
                    try {
                        File[] f;
                        if ((f = dir.listFiles(mediaFileFilter)) != null) {
                            for (File file : f) {
                                if (file.isFile()) {
                                    mediaToScan.add(file);
                                } else if (file.isDirectory()) {
                                    directories.push(file);
                                }
                            }
                        }
                    } catch (Exception e) {
                        // listFiles can fail in OutOfMemoryError, go to the next folder
                        continue;
                    }

                    if (isStopping) {
                        Log.d(TAG, "Stopping scan");
                        return;
                    }
                }
                ArrayList<MediaWrapper> mediaWrappers = new ArrayList<>();
                // Process the stacked items
                for (File file : mediaToScan) {
                    String fileURI = LibVLC.PathToURI(file.getPath());
                    if (existingMedias.containsKey(fileURI)) {
                        /**
                         * only add file if it is not already in the list. eg. if
                         * user select an subfolder as well
                         */
                        if (!addedLocations.contains(fileURI)) {
                            // get existing media item from database
                            mediaWrappers.add(existingMedias.get(fileURI));
                            addedLocations.add(fileURI);
                        }
                    } else {
                        // create new media item
                        final Media media = new Media(
                                VLCMediaPlayer.getInstance().getLibVlcInstance(), fileURI);
                        media.parse();
                        media.release();
                        /* skip files with .mod extension and no duration */
                        if ((media.getDuration() == 0 || (media.getTrackCount() != 0 && TextUtils
                                .isEmpty(media.getTrack(0).codec))) &&
                                fileURI.endsWith(".mod")) {
                            continue;
                        }
                        MediaWrapper mw = new MediaWrapper(media);
                        mw.setLastModified(file.lastModified());
                        mediaWrappers.add(mw);
                        // Add this item to database
                        DatabaseHelper.getInstance().addMedia(mw);
                    }
                    if (isStopping) {
                        Log.d(TAG, "Stopping scan");
                        return;
                    }
                }
                processMediaWrappers(mediaWrappers);
            } finally {
                // remove old files & folders from database if storage is mounted
                if (!isStopping && Environment.getExternalStorageState()
                        .equals(Environment.MEDIA_MOUNTED)) {
                    for (String fileURI : addedLocations) {
                        existingMedias.remove(fileURI);
                    }
                    DatabaseHelper.getInstance().removeMedias(existingMedias.keySet());
                }

                if (mRestart) {
                    Log.d(TAG, "Restarting scan");
                    mRestart = false;
                    mRestartHandler.sendEmptyMessageDelayed(1, 200);
                }
                EventBus.getDefault().post(new CollectionManager.UpdatedEvent());
            }
        }

        private void processMediaWrappers(List<MediaWrapper> mws) {
            Map<String, Set<String>> albumArtistsMap = new HashMap<>();
            Map<String, Album> albumMap = new HashMap<>();
            for (MediaWrapper mw : mws) {
                if (mw.getType() == MediaWrapper.TYPE_AUDIO) {
                    String albumKey = mw.getAlbum() != null ? mw.getAlbum().toLowerCase() : "";
                    if (albumArtistsMap.get(albumKey) == null) {
                        albumArtistsMap.put(albumKey, new HashSet<String>());
                    }
                    albumArtistsMap.get(albumKey).add(mw.getArtist());
                    int artistCount = albumArtistsMap.get(albumKey).size();
                    if (artistCount == 1) {
                        Artist artist = Artist.get(mw.getArtist());
                        albumMap.put(albumKey, Album.get(mw.getAlbum(), artist));
                    } else if (artistCount == 2) {
                        albumMap.put(albumKey, Album.get(mw.getAlbum(), Artist.COMPILATION_ARTIST));
                    }
                }
            }
            for (MediaWrapper mw : mws) {
                if (mw.getType() == MediaWrapper.TYPE_AUDIO) {
                    Artist artist = Artist.get(mw.getArtist());
                    String albumKey = mw.getAlbum() != null ? mw.getAlbum().toLowerCase() : "";
                    Album album = albumMap.get(albumKey);
                    if (!TextUtils.isEmpty(mw.getAlbum())
                            && !TextUtils.isEmpty(mw.getArtworkURL())) {
                        album.setImage(Image.get(mw.getArtworkURL(), false));
                    }
                    Track track = Track.get(mw.getTitle(), album, artist);
                    track.setDuration(mw.getLength());
                    track.setAlbumPos(mw.getTrackNumber());
                    Query query = Query.get(mw.getTitle(), mw.getAlbum(), mw.getArtist(), true);
                    Resolver userCollectionResolver = PipeLine.getInstance().getResolver(
                            TomahawkApp.PLUGINNAME_USERCOLLECTION);
                    Result result = Result.get(mw.getLocation(), track, userCollectionResolver);
                    query.addTrackResult(result, 1f);
                    addQuery(query, mw.getLastModified());
                    addArtist(artist);
                    addAlbum(album);
                    addAlbumTrack(album, query);
                    addArtistAlbum(artist, album);
                    if (mw.getAlbumArtist() != null) {
                        Artist albumArtist = Artist.get(mw.getAlbumArtist());
                        addAlbumArtist(albumArtist);
                        addArtistAlbum(albumArtist, album);
                    }
                }
            }
        }
    }

    private final RestartHandler mRestartHandler = new RestartHandler(this);

    private static class RestartHandler extends WeakReferenceHandler<UserCollection> {

        public RestartHandler(UserCollection userCollection) {
            super(Looper.getMainLooper(), userCollection);
        }

        @Override
        public void handleMessage(Message msg) {
            if (getReferencedObject() != null) {
                getReferencedObject().loadMediaItems();
            }
        }
    }

    /**
     * Filters all irrelevant files
     */
    private static class MediaItemFilter implements FileFilter {

        @Override
        public boolean accept(File f) {
            boolean accepted = false;
            if (!f.isHidden()) {
                if (f.isDirectory() && !FOLDER_BLACKLIST
                        .contains(f.getPath().toLowerCase(Locale.ENGLISH))) {
                    accepted = true;
                } else {
                    String fileName = f.getName().toLowerCase(Locale.ENGLISH);
                    int dotIndex = fileName.lastIndexOf(".");
                    if (dotIndex != -1) {
                        String fileExt = fileName.substring(dotIndex);
                        accepted = Extensions.AUDIO.contains(fileExt) ||
                                Extensions.VIDEO.contains(fileExt) ||
                                Extensions.PLAYLIST.contains(fileExt);
                    }
                }
            }
            return accepted;
        }
    }

    public static ArrayList<String> getStorageDirectories() {
        BufferedReader bufReader = null;
        ArrayList<String> list = new ArrayList<>();
        list.add(Environment.getExternalStorageDirectory().getPath());

        List<String> typeWL =
                Arrays.asList("vfat", "exfat", "sdcardfs", "fuse", "ntfs", "fat32", "ext3", "ext4",
                        "esdfs");
        List<String> typeBL = Arrays.asList("tmpfs");
        String[] mountWL = {"/mnt", "/Removable", "/storage"};
        String[] mountBL = {
                "/mnt/secure",
                "/mnt/shell",
                "/mnt/asec",
                "/mnt/obb",
                "/mnt/media_rw/extSdCard",
                "/mnt/media_rw/sdcard",
                "/storage/emulated"};
        String[] deviceWL = {
                "/dev/block/vold",
                "/dev/fuse",
                "/mnt/media_rw"};

        try {
            bufReader = new BufferedReader(new FileReader("/proc/mounts"));
            String line;
            while ((line = bufReader.readLine()) != null) {

                StringTokenizer tokens = new StringTokenizer(line, " ");
                String device = tokens.nextToken();
                String mountpoint = tokens.nextToken();
                String type = tokens.nextToken();

                // skip if already in list or if type/mountpoint is blacklisted
                if (list.contains(mountpoint) || typeBL.contains(type)
                        || doStringsStartWith(mountBL, mountpoint)) {
                    continue;
                }

                // check that device is in whitelist, and either type or mountpoint is in a whitelist
                if (doStringsStartWith(deviceWL, device) && (typeWL.contains(type)
                        || doStringsStartWith(mountWL, mountpoint))) {
                    list.add(mountpoint);
                }
            }
        } catch (IOException e) {
            Log.e(TAG, "getStorageDirectories: " + e.getClass() + ": " + e.getLocalizedMessage());
        } finally {
            if (bufReader != null) {
                try {
                    bufReader.close();
                } catch (IOException e) {
                    Log.e(TAG, "getStorageDirectories: " + e.getClass() + ": "
                            + e.getLocalizedMessage());
                }
            }
        }
        return list;
    }

    private static boolean doStringsStartWith(String[] array, String text) {
        for (String item : array) {
            if (text.startsWith(item)) {
                return true;
            }
        }
        return false;
    }
}


File: src/org/tomahawk/tomahawk_android/adapters/ViewHolder.java
/* == This file is part of Tomahawk Player - <http://tomahawk-player.org> ===
 *
 *   Copyright 2014, Enno Gottschalk <mrmaffen@googlemail.com>
 *
 *   Tomahawk is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   Tomahawk is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with Tomahawk. If not, see <http://www.gnu.org/licenses/>.
 */
package org.tomahawk.tomahawk_android.adapters;

import org.jdeferred.DoneCallback;
import org.tomahawk.libtomahawk.collection.Album;
import org.tomahawk.libtomahawk.collection.Artist;
import org.tomahawk.libtomahawk.collection.Collection;
import org.tomahawk.libtomahawk.collection.CollectionManager;
import org.tomahawk.libtomahawk.collection.Image;
import org.tomahawk.libtomahawk.collection.Playlist;
import org.tomahawk.libtomahawk.infosystem.SocialAction;
import org.tomahawk.libtomahawk.infosystem.User;
import org.tomahawk.libtomahawk.infosystem.hatchet.HatchetInfoPlugin;
import org.tomahawk.libtomahawk.resolver.Query;
import org.tomahawk.libtomahawk.resolver.Resolver;
import org.tomahawk.libtomahawk.utils.TomahawkUtils;
import org.tomahawk.tomahawk_android.R;
import org.tomahawk.tomahawk_android.TomahawkApp;
import org.tomahawk.tomahawk_android.fragments.PlaylistsFragment;
import org.tomahawk.tomahawk_android.views.PlaybackPanel;

import android.content.res.Resources;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.ImageView;
import android.widget.Spinner;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

public class ViewHolder {

    final int mLayoutId;

    private final View mRootView;

    private final Map<Integer, View> mCachedViews = new HashMap<>();

    public ViewHolder(View rootView, int layoutId) {
        mLayoutId = layoutId;
        mRootView = rootView;
    }

    public View ensureInflation(int stubResId, int inflatedId) {
        return TomahawkUtils.ensureInflation(mRootView, stubResId, inflatedId);
    }

    public View findViewById(int id) {
        if (mCachedViews.containsKey(id)) {
            return mCachedViews.get(id);
        } else {
            View view = mRootView.findViewById(id);
            if (view != null) {
                mCachedViews.put(id, view);
            }
            return view;
        }
    }

    public void setMainClickListener(ClickListener listener) {
        View mainClickArea = findViewById(R.id.mainclickarea);
        mainClickArea.setOnClickListener(listener);
        mainClickArea.setOnLongClickListener(listener);
    }

    public void fillView(Query query, String numerationString, boolean showAsPlaying,
            View.OnClickListener swipeMenuButton1Listener, boolean showAsQueued) {
        TextView trackNameTextView = (TextView) findViewById(R.id.track_textview);
        trackNameTextView.setText(query.getPrettyName());
        setTextViewEnabled(trackNameTextView, query.isPlayable(), false);

        ImageView resolverImageView = (ImageView) ensureInflation(R.id.resolver_imageview_stub,
                R.id.resolver_imageview);
        TextView numerationTextView = (TextView) findViewById(R.id.numeration_textview);
        if (showAsQueued) {
            if (numerationTextView != null) {
                numerationTextView.setVisibility(View.GONE);
            }
            if (resolverImageView != null) {
                resolverImageView.setVisibility(View.VISIBLE);
                TomahawkUtils.loadDrawableIntoImageView(TomahawkApp.getContext(), resolverImageView,
                        R.drawable.ic_action_queue_red);
            }
        } else if (showAsPlaying) {
            if (numerationTextView != null) {
                numerationTextView.setVisibility(View.GONE);
            }
            if (resolverImageView != null) {
                resolverImageView.setVisibility(View.VISIBLE);
                if (query.getPreferredTrackResult() != null) {
                    Resolver resolver = query.getPreferredTrackResult().getResolvedBy();
                    resolver.loadIcon(resolverImageView, false);
                }
            }
        } else if (numerationString != null) {
            if (resolverImageView != null) {
                resolverImageView.setVisibility(View.GONE);
            }
            if (numerationTextView != null) {
                numerationTextView.setVisibility(View.VISIBLE);
                numerationTextView.setText(numerationString);
                setTextViewEnabled(numerationTextView, query.isPlayable(), false);
            }
        }
        if (mLayoutId == R.layout.list_item_numeration_track_artist
                || mLayoutId == R.layout.list_item_track_artist) {
            TextView artistNameTextView = (TextView) findViewById(R.id.artist_textview);
            artistNameTextView.setText(query.getArtist().getPrettyName());
            setTextViewEnabled(artistNameTextView, query.isPlayable(), false);
        }
        if (mLayoutId == R.layout.list_item_numeration_track_duration) {
            TextView durationTextView = (TextView) findViewById(R.id.duration_textview);
            if (query.getPreferredTrack().getDuration() > 0) {
                durationTextView.setText(TomahawkUtils.durationToString(
                        (query.getPreferredTrack().getDuration())));
            } else {
                durationTextView.setText(PlaybackPanel.COMPLETION_STRING_DEFAULT);
            }
            setTextViewEnabled(durationTextView, query.isPlayable(), false);
        }
        ImageView swipeMenuButton;
        if (showAsQueued) {
            swipeMenuButton = (ImageView) ensureInflation(R.id.swipe_menu_button_dequeue_stub,
                    R.id.swipe_menu_button_dequeue);
            swipeMenuButton.setVisibility(View.VISIBLE);
            swipeMenuButton.setImageResource(R.drawable.ic_player_exit_light);
            TomahawkUtils.setTint(swipeMenuButton.getDrawable(), R.color.tomahawk_red);
            ImageView swipeMenuButtonEnqueue =
                    (ImageView) findViewById(R.id.swipe_menu_button_enqueue);
            if (swipeMenuButtonEnqueue != null) {
                swipeMenuButtonEnqueue.setVisibility(View.GONE);
            }
        } else {
            swipeMenuButton = (ImageView) ensureInflation(R.id.swipe_menu_button_enqueue_stub,
                    R.id.swipe_menu_button_enqueue);
            swipeMenuButton.setVisibility(View.VISIBLE);
            ImageView swipeMenuButtonDequeue =
                    (ImageView) findViewById(R.id.swipe_menu_button_dequeue);
            if (swipeMenuButtonDequeue != null) {
                swipeMenuButtonDequeue.setVisibility(View.GONE);
            }
        }
        swipeMenuButton.setOnClickListener(swipeMenuButton1Listener);
    }

    public void fillView(String string) {
        TextView textView1 = (TextView) findViewById(R.id.textview1);
        textView1.setText(string);
    }

    public void fillView(User user) {
        TextView textView1 = (TextView) findViewById(R.id.textview1);
        textView1.setText(user.getName());
        if (mLayoutId == R.layout.list_item_user) {
            TextView textView2 = (TextView) findViewById(R.id.textview2);
            textView2.setText(TomahawkApp.getContext().getString(R.string.followers_count,
                    user.getFollowersCount(), user.getFollowCount()));
        }
        TextView userTextView1 = (TextView) findViewById(R.id.usertextview1);
        ImageView userImageView1 = (ImageView) findViewById(R.id.userimageview1);
        TomahawkUtils.loadUserImageIntoImageView(TomahawkApp.getContext(),
                userImageView1, user, Image.getSmallImageSize(),
                userTextView1);
    }

    public void fillView(Artist artist) {
        TextView textView1 = (TextView) findViewById(R.id.textview1);
        textView1.setText(artist.getPrettyName());
        ImageView imageView1 = (ImageView) findViewById(R.id.imageview1);
        TomahawkUtils.loadImageIntoImageView(TomahawkApp.getContext(), imageView1,
                artist.getImage(), Image.getSmallImageSize(), true);
    }

    public void fillView(final Album album, Collection collection) {
        if (collection == null) {
            collection =
                    CollectionManager.getInstance().getCollection(TomahawkApp.PLUGINNAME_HATCHET);
        }
        TextView textView1 = (TextView) findViewById(R.id.textview1);
        textView1.setText(album.getPrettyName());
        TextView textView2 = (TextView) findViewById(R.id.textview2);
        textView2.setText(album.getArtist().getPrettyName());
        ImageView imageView1 = (ImageView) findViewById(R.id.imageview1);
        TomahawkUtils.loadImageIntoImageView(TomahawkApp.getContext(), imageView1,
                album.getImage(), Image.getSmallImageSize(), false);
        final TextView textView3 = (TextView) findViewById(R.id.textview3);
        collection.getAlbumTracks(album).done(new DoneCallback<List<Query>>() {
            @Override
            public void onDone(List<Query> result) {
                textView3.setVisibility(View.VISIBLE);
                textView3.setText(TomahawkApp.getContext().getResources()
                        .getQuantityString(R.plurals.songs_with_count, result.size(),
                                result.size()));
            }
        });
    }

    public void fillView(Resolver resolver) {
        TextView textView1 = (TextView) findViewById(R.id.textview1);
        textView1.setText(resolver.getPrettyName());
        ImageView imageView1 = (ImageView) findViewById(R.id.imageview1);
        imageView1.clearColorFilter();
        resolver.loadIconBackground(imageView1, !resolver.isEnabled());
        ImageView imageView2 = (ImageView) findViewById(R.id.imageview2);
        resolver.loadIconWhite(imageView2);
        View connectImageViewContainer = findViewById(R.id.connect_imageview);
        if (resolver.isEnabled()) {
            connectImageViewContainer.setVisibility(View.VISIBLE);
        } else {
            connectImageViewContainer.setVisibility(View.GONE);
        }
    }

    public void fillView(Playlist playlist) {
        if (findViewById(R.id.imageview_create_playlist) != null) {
            findViewById(R.id.imageview_create_playlist).setVisibility(View.GONE);
        }
        ArrayList<Image> artistImages = new ArrayList<>();
        String topArtistsString = "";
        String[] artists = playlist.getTopArtistNames();
        if (artists != null) {
            for (int i = 0; i < artists.length && i < 5 && artistImages.size() < 3; i++) {
                Artist artist = Artist.get(artists[i]);
                topArtistsString += artists[i];
                if (i != artists.length - 1) {
                    topArtistsString += ", ";
                }
                if (artist.getImage() != null) {
                    artistImages.add(artist.getImage());
                }
            }
        }
        fillView(mRootView, artistImages, 0, false);
        TextView textView1 = (TextView) findViewById(R.id.textview1);
        if (textView1 != null) {
            textView1.setText(playlist.getName());
        }
        TextView textView2 = (TextView) findViewById(R.id.textview2);
        if (textView2 != null) {
            textView2.setText(topArtistsString);
            textView2.setVisibility(View.VISIBLE);
        }
        TextView textView3 = (TextView) findViewById(R.id.textview3);
        if (textView3 != null) {
            textView3.setVisibility(View.VISIBLE);
            textView3.setText(TomahawkApp.getContext().getResources().getQuantityString(
                    R.plurals.songs_with_count, (int) playlist.getCount(), playlist.getCount()));
        }
    }

    public static void fillView(View view, Playlist playlist, int height, boolean isPagerFragment) {
        ArrayList<Image> artistImages = new ArrayList<>();
        String[] artists = playlist.getTopArtistNames();
        if (artists != null) {
            for (int i = 0; i < artists.length && i < 5 && artistImages.size() < 3; i++) {
                Artist artist = Artist.get(artists[i]);
                if (artist.getImage() != null) {
                    artistImages.add(artist.getImage());
                }
            }
        }
        fillView(view, artistImages, height, isPagerFragment);
    }

    private static void fillView(View view, List<Image> artistImages, int height,
            boolean isPagerFragment) {
        View v;
        int gridOneResId = isPagerFragment ? R.id.imageview_grid_one_pager
                : R.id.imageview_grid_one;
        int gridTwoResId = isPagerFragment ? R.id.imageview_grid_two_pager
                : R.id.imageview_grid_two;
        int gridThreeResId = isPagerFragment ? R.id.imageview_grid_three_pager
                : R.id.imageview_grid_three;
        int gridOneStubId = isPagerFragment ? R.id.imageview_grid_one_pager_stub
                : R.id.imageview_grid_one_stub;
        int gridTwoStubId = isPagerFragment ? R.id.imageview_grid_two_pager_stub
                : R.id.imageview_grid_two_stub;
        int gridThreeStubId = isPagerFragment ? R.id.imageview_grid_three_pager_stub
                : R.id.imageview_grid_three_stub;
        if (artistImages.size() > 2) {
            v = view.findViewById(gridOneResId);
            if (v != null) {
                v.setVisibility(View.GONE);
            }
            v = view.findViewById(gridTwoResId);
            if (v != null) {
                v.setVisibility(View.GONE);
            }
            v = TomahawkUtils.ensureInflation(view, gridThreeStubId, gridThreeResId);
            v.setVisibility(View.VISIBLE);
            TomahawkUtils.loadImageIntoImageView(TomahawkApp.getContext(),
                    (ImageView) v.findViewById(R.id.imageview1),
                    artistImages.get(0), Image.getLargeImageSize(), false);
            TomahawkUtils.loadImageIntoImageView(TomahawkApp.getContext(),
                    (ImageView) v.findViewById(R.id.imageview2),
                    artistImages.get(1), Image.getSmallImageSize(), false);
            TomahawkUtils.loadImageIntoImageView(TomahawkApp.getContext(),
                    (ImageView) v.findViewById(R.id.imageview3),
                    artistImages.get(2), Image.getSmallImageSize(), false);
        } else if (artistImages.size() > 1) {
            v = view.findViewById(gridOneResId);
            if (v != null) {
                v.setVisibility(View.GONE);
            }
            v = view.findViewById(gridThreeResId);
            if (v != null) {
                v.setVisibility(View.GONE);
            }
            v = TomahawkUtils.ensureInflation(view, gridTwoStubId, gridTwoResId);
            v.setVisibility(View.VISIBLE);
            TomahawkUtils.loadImageIntoImageView(TomahawkApp.getContext(),
                    (ImageView) v.findViewById(R.id.imageview1),
                    artistImages.get(0), Image.getLargeImageSize(), false);
            TomahawkUtils.loadImageIntoImageView(TomahawkApp.getContext(),
                    (ImageView) v.findViewById(R.id.imageview2),
                    artistImages.get(1), Image.getSmallImageSize(), false);
        } else {
            v = view.findViewById(gridTwoResId);
            if (v != null) {
                v.setVisibility(View.GONE);
            }
            v = view.findViewById(gridThreeResId);
            if (v != null) {
                v.setVisibility(View.GONE);
            }
            v = TomahawkUtils.ensureInflation(view, gridOneStubId, gridOneResId);
            v.setVisibility(View.VISIBLE);
            if (artistImages.size() > 0) {
                TomahawkUtils.loadImageIntoImageView(TomahawkApp.getContext(),
                        (ImageView) v.findViewById(R.id.imageview1),
                        artistImages.get(0), Image.getLargeImageSize(), false);
            } else {
                TomahawkUtils.loadDrawableIntoImageView(TomahawkApp.getContext(),
                        (ImageView) v.findViewById(R.id.imageview1),
                        R.drawable.album_placeholder_grid);
            }
        }
        if (height > 0) {
            v.getLayoutParams().height = height;
        }
    }

    public void fillView(int id) {
        switch (id) {
            case PlaylistsFragment.CREATE_PLAYLIST_BUTTON_ID:
                View v = mRootView.findViewById(R.id.imageview_grid_one);
                if (v != null) {
                    v.setVisibility(View.GONE);
                }
                v = mRootView.findViewById(R.id.imageview_grid_two);
                if (v != null) {
                    v.setVisibility(View.GONE);
                }
                v = mRootView.findViewById(R.id.imageview_grid_three);
                if (v != null) {
                    v.setVisibility(View.GONE);
                }
                TomahawkUtils.ensureInflation(mRootView, R.id.imageview_create_playlist_stub,
                        R.id.imageview_create_playlist);
                findViewById(R.id.imageview_create_playlist).setVisibility(View.VISIBLE);
                TextView textView1 = (TextView) findViewById(R.id.textview1);
                textView1.setText(
                        TomahawkApp.getContext().getString(R.string.create_playlist).toUpperCase());
                TextView textView2 = (TextView) findViewById(R.id.textview2);
                textView2.setVisibility(View.GONE);
                TextView textView3 = (TextView) findViewById(R.id.textview3);
                textView3.setVisibility(View.GONE);
                break;
        }
    }

    public void fillHeaderView(ArrayList<CharSequence> spinnerItems,
            int initialSelection, AdapterView.OnItemSelectedListener listener) {
        ArrayAdapter<CharSequence> adapter =
                new ArrayAdapter<>(TomahawkApp.getContext(),
                        R.layout.dropdown_header_textview, spinnerItems);
        adapter.setDropDownViewResource(R.layout.dropdown_header_dropdown_textview);
        Spinner spinner = (Spinner) findViewById(R.id.spinner1);
        spinner.setAdapter(adapter);
        spinner.setSelection(initialSelection);
        spinner.setOnItemSelectedListener(listener);
    }

    public void fillHeaderView(String text) {
        TextView textView1 = (TextView) findViewById(R.id.textview1);
        textView1.setText(text);
    }

    public void fillHeaderView(SocialAction socialAction, int segmentSize) {
        ImageView userImageView1 = (ImageView) findViewById(R.id.userimageview1);
        TextView userTextView = (TextView) findViewById(R.id.usertextview1);
        TomahawkUtils.loadUserImageIntoImageView(TomahawkApp.getContext(),
                userImageView1, socialAction.getUser(),
                Image.getSmallImageSize(), userTextView);
        Object targetObject = socialAction.getTargetObject();
        Resources resources = TomahawkApp.getContext().getResources();
        String userName = socialAction.getUser().getName();
        String phrase = "!FIXME! type: " + socialAction.getType()
                + ", action: " + socialAction.getAction() + ", user: " + userName;
        if (HatchetInfoPlugin.HATCHET_SOCIALACTION_TYPE_LOVE
                .equals(socialAction.getType())) {
            if (targetObject instanceof Query) {
                phrase = resources.getQuantityString(R.plurals.socialaction_type_love_track,
                        segmentSize, userName, segmentSize);
            } else if (targetObject instanceof Album) {
                phrase = resources.getQuantityString(R.plurals.socialaction_type_collected_album,
                        segmentSize, userName, segmentSize);
            } else if (targetObject instanceof Artist) {
                phrase = resources.getQuantityString(R.plurals.socialaction_type_collected_artist,
                        segmentSize, userName, segmentSize);
            }
        } else if (HatchetInfoPlugin.HATCHET_SOCIALACTION_TYPE_FOLLOW
                .equals(socialAction.getType())) {
            phrase = resources.getString(R.string.socialaction_type_follow, userName);
        } else if (HatchetInfoPlugin.HATCHET_SOCIALACTION_TYPE_CREATEPLAYLIST
                .equals(socialAction.getType())) {
            phrase = resources.getQuantityString(R.plurals.socialaction_type_createplaylist,
                    segmentSize, userName, segmentSize);
        } else if (HatchetInfoPlugin.HATCHET_SOCIALACTION_TYPE_LATCHON
                .equals(socialAction.getType())) {
            phrase = resources.getQuantityString(R.plurals.socialaction_type_latchon,
                    segmentSize, userName, segmentSize);
        }
        TextView textView1 = (TextView) findViewById(R.id.textview1);
        textView1.setText(phrase + ":");
    }

    private static String dateToString(Resources resources, Date date) {
        String s = "";
        if (date != null) {
            long diff = System.currentTimeMillis() - date.getTime();
            if (diff < 60000) {
                s += resources.getString(R.string.time_afewseconds);
            } else if (diff < 3600000) {
                long minutes = TimeUnit.MILLISECONDS.toMinutes(diff);
                s += resources.getQuantityString(R.plurals.time_minute, (int) minutes, minutes);
            } else if (diff < 86400000) {
                long hours = TimeUnit.MILLISECONDS.toHours(diff);
                s += resources.getQuantityString(R.plurals.time_hour, (int) hours, hours);
            } else {
                long days = TimeUnit.MILLISECONDS.toDays(diff);
                s += resources.getQuantityString(R.plurals.time_day, (int) days, days);
            }
        }
        return s;
    }

    private static void setTextViewEnabled(TextView textView, boolean enabled,
            boolean isSecondary) {
        if (textView != null && textView.getResources() != null) {
            int colorResId;
            if (enabled) {
                if (isSecondary) {
                    colorResId = R.color.secondary_textcolor;
                } else {
                    colorResId = R.color.primary_textcolor;
                }
            } else {
                colorResId = R.color.disabled;
            }
            textView.setTextColor(textView.getResources().getColor(colorResId));
        }
    }
}


File: src/org/tomahawk/tomahawk_android/fragments/AlbumsFragment.java
/* == This file is part of Tomahawk Player - <http://tomahawk-player.org> ===
 *
 *   Copyright 2012, Enno Gottschalk <mrmaffen@googlemail.com>
 *
 *   Tomahawk is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   Tomahawk is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with Tomahawk. If not, see <http://www.gnu.org/licenses/>.
 */
package org.tomahawk.tomahawk_android.fragments;

import org.jdeferred.DoneCallback;
import org.tomahawk.libtomahawk.collection.Album;
import org.tomahawk.libtomahawk.collection.AlphaComparator;
import org.tomahawk.libtomahawk.collection.ArtistAlphaComparator;
import org.tomahawk.libtomahawk.collection.CollectionManager;
import org.tomahawk.libtomahawk.collection.HatchetCollection;
import org.tomahawk.libtomahawk.collection.LastModifiedComparator;
import org.tomahawk.libtomahawk.collection.PlaylistEntry;
import org.tomahawk.libtomahawk.collection.UserCollection;
import org.tomahawk.libtomahawk.database.DatabaseHelper;
import org.tomahawk.libtomahawk.resolver.Query;
import org.tomahawk.libtomahawk.resolver.QueryComparator;
import org.tomahawk.tomahawk_android.R;
import org.tomahawk.tomahawk_android.TomahawkApp;
import org.tomahawk.tomahawk_android.activities.TomahawkMainActivity;
import org.tomahawk.tomahawk_android.adapters.Segment;
import org.tomahawk.tomahawk_android.adapters.TomahawkListAdapter;
import org.tomahawk.tomahawk_android.services.PlaybackService;
import org.tomahawk.tomahawk_android.utils.FragmentUtils;

import android.os.Bundle;
import android.view.View;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Set;

/**
 * {@link TomahawkFragment} which shows a set of {@link Album}s inside its {@link
 * se.emilsjolander.stickylistheaders.StickyListHeadersListView}
 */
public class AlbumsFragment extends TomahawkFragment {

    public static final String COLLECTION_ALBUMS_SPINNER_POSITION
            = "org.tomahawk.tomahawk_android.collection_albums_spinner_position";

    @Override
    public void onResume() {
        super.onResume();

        if (getArguments() != null) {
            if (getArguments().containsKey(SHOW_MODE)) {
                mShowMode = getArguments().getInt(SHOW_MODE);
            }
        }
        if (mContainerFragmentClass == null) {
            getActivity().setTitle("");
        }
        updateAdapter();
    }

    /**
     * Called every time an item inside a ListView or GridView is clicked
     *
     * @param view the clicked view
     * @param item the Object which corresponds to the click
     */
    @Override
    public void onItemClick(View view, final Object item) {
        TomahawkMainActivity activity = (TomahawkMainActivity) getActivity();
        if (item instanceof Query) {
            PlaylistEntry entry = getListAdapter().getPlaylistEntry(item);
            if (entry.getQuery().isPlayable()) {
                PlaybackService playbackService = activity.getPlaybackService();
                if (playbackService != null) {
                    if (playbackService.getCurrentEntry() == entry) {
                        playbackService.playPause();
                    } else {
                        playbackService.setPlaylist(getListAdapter().getPlaylist(), entry);
                        playbackService.start();
                    }
                }
            }
        } else if (item instanceof Album) {
            mCollection.hasAlbumTracks((Album) item).done(new DoneCallback<Boolean>() {
                @Override
                public void onDone(Boolean result) {
                    Bundle bundle = new Bundle();
                    bundle.putString(TomahawkFragment.ALBUM, ((Album) item).getCacheKey());
                    if (result) {
                        bundle.putString(TomahawkFragment.COLLECTION_ID, mCollection.getId());
                    } else {
                        bundle.putString(TomahawkFragment.COLLECTION_ID,
                                TomahawkApp.PLUGINNAME_HATCHET);
                    }
                    bundle.putInt(CONTENT_HEADER_MODE,
                            ContentHeaderFragment.MODE_HEADER_DYNAMIC);
                    FragmentUtils.replace((TomahawkMainActivity) getActivity(),
                            TracksFragment.class, bundle);
                }
            });
        }
    }

    /**
     * Update this {@link TomahawkFragment}'s {@link TomahawkListAdapter} content
     */
    @Override
    protected void updateAdapter() {
        if (!mIsResumed) {
            return;
        }

        if (mArtist != null) {
            if (!TomahawkApp.PLUGINNAME_HATCHET.equals(mCollection.getId())) {
                mCollection.getArtistAlbums(mArtist).done(new DoneCallback<List<Album>>() {
                    @Override
                    public void onDone(List<Album> result) {
                        fillAdapter(new Segment(
                                        mCollection.getName() + " " + getString(R.string.albums),
                                        sortAlbums(result), R.integer.grid_column_count,
                                        R.dimen.padding_superlarge, R.dimen.padding_superlarge),
                                mCollection);
                    }
                });
            } else {
                mCollection.getArtistAlbums(mArtist).done(new DoneCallback<List<Album>>() {
                    @Override
                    public void onDone(List<Album> result) {
                        final List<Segment> segments = new ArrayList<>();
                        Segment segment = new Segment(R.string.top_albums, sortAlbums(result),
                                R.integer.grid_column_count, R.dimen.padding_superlarge,
                                R.dimen.padding_superlarge);
                        segments.add(segment);
                        fillAdapter(segment);
                        ((HatchetCollection) mCollection).getArtistTopHits(mArtist).done(
                                new DoneCallback<List<Query>>() {
                                    @Override
                                    public void onDone(List<Query> result) {
                                        Collections.sort(result, new QueryComparator(
                                                QueryComparator.COMPARE_ALBUMPOS));
                                        Segment segment = new Segment(R.string.top_hits, result);
                                        segment.setShowNumeration(true, 1);
                                        segment.setHideArtistName(true);
                                        segment.setShowDuration(true);
                                        segments.add(segment);
                                        fillAdapter(segments);
                                    }
                                });
                    }
                });
            }
        } else if (mAlbumArray != null) {
            fillAdapter(new Segment(mAlbumArray));
        } else if (mUser != null) {
            fillAdapter(new Segment(getDropdownPos(COLLECTION_ALBUMS_SPINNER_POSITION),
                    constructDropdownItems(),
                    constructDropdownListener(COLLECTION_ALBUMS_SPINNER_POSITION),
                    sortAlbums(mUser.getStarredAlbums()), R.integer.grid_column_count,
                    R.dimen.padding_superlarge, R.dimen.padding_superlarge));
        } else {
            final List<Album> starredAlbums;
            if (mCollection.getId().equals(TomahawkApp.PLUGINNAME_USERCOLLECTION)) {
                starredAlbums = DatabaseHelper.getInstance().getStarredAlbums();
            } else {
                starredAlbums = null;
            }
            mCollection.getAlbums().done(new DoneCallback<Set<Album>>() {
                @Override
                public void onDone(Set<Album> result) {
                    if (starredAlbums != null) {
                        result.addAll(starredAlbums);
                    }
                    fillAdapter(new Segment(getDropdownPos(COLLECTION_ALBUMS_SPINNER_POSITION),
                            constructDropdownItems(),
                            constructDropdownListener(COLLECTION_ALBUMS_SPINNER_POSITION),
                            sortAlbums(result), R.integer.grid_column_count,
                            R.dimen.padding_superlarge, R.dimen.padding_superlarge), mCollection);
                }
            });
        }
    }

    private List<Integer> constructDropdownItems() {
        List<Integer> dropDownItems = new ArrayList<>();
        dropDownItems.add(R.string.collection_dropdown_recently_added);
        dropDownItems.add(R.string.collection_dropdown_alpha);
        dropDownItems.add(R.string.collection_dropdown_alpha_artists);
        return dropDownItems;
    }

    private List<Album> sortAlbums(java.util.Collection<Album> albums) {
        List<Album> sortedAlbums;
        if (albums instanceof List) {
            sortedAlbums = (List<Album>) albums;
        } else {
            sortedAlbums = new ArrayList<>(albums);
        }
        switch (getDropdownPos(COLLECTION_ALBUMS_SPINNER_POSITION)) {
            case 0:
                UserCollection userColl = (UserCollection) CollectionManager.getInstance()
                        .getCollection(TomahawkApp.PLUGINNAME_USERCOLLECTION);
                Collections.sort(sortedAlbums,
                        new LastModifiedComparator<>(userColl.getAlbumTimeStamps()));
                break;
            case 1:
                Collections.sort(sortedAlbums, new AlphaComparator());
                break;
            case 2:
                Collections.sort(sortedAlbums, new ArtistAlphaComparator());
                break;
        }
        return sortedAlbums;
    }
}


File: src/org/tomahawk/tomahawk_android/fragments/ArtistsFragment.java
/* == This file is part of Tomahawk Player - <http://tomahawk-player.org> ===
 *
 *   Copyright 2012, Enno Gottschalk <mrmaffen@googlemail.com>
 *
 *   Tomahawk is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   Tomahawk is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with Tomahawk. If not, see <http://www.gnu.org/licenses/>.
 */
package org.tomahawk.tomahawk_android.fragments;

import org.jdeferred.DoneCallback;
import org.tomahawk.libtomahawk.collection.AlphaComparator;
import org.tomahawk.libtomahawk.collection.Artist;
import org.tomahawk.libtomahawk.collection.CollectionManager;
import org.tomahawk.libtomahawk.collection.LastModifiedComparator;
import org.tomahawk.libtomahawk.collection.UserCollection;
import org.tomahawk.libtomahawk.database.DatabaseHelper;
import org.tomahawk.tomahawk_android.R;
import org.tomahawk.tomahawk_android.TomahawkApp;
import org.tomahawk.tomahawk_android.activities.TomahawkMainActivity;
import org.tomahawk.tomahawk_android.adapters.Segment;
import org.tomahawk.tomahawk_android.utils.FragmentUtils;

import android.os.Bundle;
import android.view.View;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Set;

/**
 * {@link TomahawkFragment} which shows a set of {@link Artist}s inside its {@link
 * se.emilsjolander.stickylistheaders.StickyListHeadersListView}
 */
public class ArtistsFragment extends TomahawkFragment {

    public static final String COLLECTION_ARTISTS_SPINNER_POSITION
            = "org.tomahawk.tomahawk_android.collection_artists_spinner_position";

    @Override
    public void onResume() {
        super.onResume();

        if (getArguments() != null) {
            if (getArguments().containsKey(SHOW_MODE)) {
                mShowMode = getArguments().getInt(SHOW_MODE);
            }
        }
        updateAdapter();
    }

    /**
     * Called every time an item inside a ListView or GridView is clicked
     *
     * @param view the clicked view
     * @param item the Object which corresponds to the click
     */
    @Override
    public void onItemClick(View view, final Object item) {
        if (item instanceof Artist) {
            mCollection.hasArtistAlbums((Artist) item).done(new DoneCallback<Boolean>() {
                @Override
                public void onDone(Boolean result) {
                    Bundle bundle = new Bundle();
                    bundle.putString(TomahawkFragment.ARTIST,
                            ((Artist) item).getCacheKey());
                    if (result) {
                        bundle.putString(TomahawkFragment.COLLECTION_ID,
                                mCollection.getId());
                    } else {
                        bundle.putString(TomahawkFragment.COLLECTION_ID,
                                TomahawkApp.PLUGINNAME_HATCHET);
                    }
                    bundle.putInt(CONTENT_HEADER_MODE,
                            ContentHeaderFragment.MODE_HEADER_DYNAMIC_PAGER);
                    bundle.putLong(CONTAINER_FRAGMENT_ID,
                            TomahawkMainActivity.getSessionUniqueId());
                    FragmentUtils.replace((TomahawkMainActivity) getActivity(),
                            ArtistPagerFragment.class, bundle);
                }
            });
        }
    }

    /**
     * Update this {@link TomahawkFragment}'s {@link org.tomahawk.tomahawk_android.adapters.TomahawkListAdapter}
     * content
     */
    @Override
    protected void updateAdapter() {
        if (!mIsResumed) {
            return;
        }

        if (mArtistArray != null) {
            fillAdapter(new Segment(mArtistArray));
        } else {
            final List<Artist> starredArtists;
            if (mCollection.getId().equals(TomahawkApp.PLUGINNAME_USERCOLLECTION)) {
                starredArtists = DatabaseHelper.getInstance().getStarredArtists();
            } else {
                starredArtists = null;
            }
            mCollection.getArtists().done(new DoneCallback<Set<Artist>>() {
                @Override
                public void onDone(Set<Artist> result) {
                    if (starredArtists != null) {
                        result.addAll(starredArtists);
                    }
                    fillAdapter(new Segment(getDropdownPos(COLLECTION_ARTISTS_SPINNER_POSITION),
                            constructDropdownItems(),
                            constructDropdownListener(COLLECTION_ARTISTS_SPINNER_POSITION),
                            sortArtists(result), R.integer.grid_column_count,
                            R.dimen.padding_superlarge, R.dimen.padding_superlarge));
                }
            });
        }
    }

    private List<Integer> constructDropdownItems() {
        List<Integer> dropDownItems = new ArrayList<>();
        dropDownItems.add(R.string.collection_dropdown_recently_added);
        dropDownItems.add(R.string.collection_dropdown_alpha);
        return dropDownItems;
    }

    private List<Artist> sortArtists(Collection<Artist> artists) {
        List<Artist> sortedArtists;
        if (artists instanceof List) {
            sortedArtists = (List<Artist>) artists;
        } else {
            sortedArtists = new ArrayList<>(artists);
        }
        switch (getDropdownPos(COLLECTION_ARTISTS_SPINNER_POSITION)) {
            case 0:
                UserCollection userColl = (UserCollection) CollectionManager.getInstance()
                        .getCollection(TomahawkApp.PLUGINNAME_USERCOLLECTION);
                Collections.sort(sortedArtists,
                        new LastModifiedComparator<>(userColl.getArtistTimeStamps()));
                break;
            case 1:
                Collections.sort(sortedArtists, new AlphaComparator());
                break;
        }
        return sortedArtists;
    }
}


File: src/org/tomahawk/tomahawk_android/fragments/ContextMenuFragment.java
/* == This file is part of Tomahawk Player - <http://tomahawk-player.org> ===
 *
 *   Copyright 2013, Enno Gottschalk <mrmaffen@googlemail.com>
 *
 *   Tomahawk is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   Tomahawk is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with Tomahawk. If not, see <http://www.gnu.org/licenses/>.
 */
package org.tomahawk.tomahawk_android.fragments;

import org.jdeferred.DoneCallback;
import org.tomahawk.libtomahawk.collection.Album;
import org.tomahawk.libtomahawk.collection.Artist;
import org.tomahawk.libtomahawk.collection.Collection;
import org.tomahawk.libtomahawk.collection.CollectionManager;
import org.tomahawk.libtomahawk.collection.Image;
import org.tomahawk.libtomahawk.collection.Playlist;
import org.tomahawk.libtomahawk.collection.PlaylistEntry;
import org.tomahawk.libtomahawk.database.DatabaseHelper;
import org.tomahawk.libtomahawk.infosystem.InfoSystem;
import org.tomahawk.libtomahawk.infosystem.SocialAction;
import org.tomahawk.libtomahawk.resolver.Query;
import org.tomahawk.libtomahawk.utils.TomahawkUtils;
import org.tomahawk.tomahawk_android.R;
import org.tomahawk.tomahawk_android.TomahawkApp;
import org.tomahawk.tomahawk_android.activities.TomahawkMainActivity;
import org.tomahawk.tomahawk_android.utils.AnimationUtils;
import org.tomahawk.tomahawk_android.utils.BlurTransformation;
import org.tomahawk.tomahawk_android.utils.FragmentUtils;
import org.tomahawk.tomahawk_android.utils.ShareUtils;
import org.tomahawk.tomahawk_android.views.PlaybackPanel;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.os.Bundle;
import android.support.v4.app.DialogFragment;
import android.support.v4.app.Fragment;
import android.text.TextUtils;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;

import de.greenrobot.event.EventBus;

/**
 * A {@link DialogFragment} which emulates the appearance and behaviour of the standard context menu
 * dialog, so that it is fully customizable.
 */
public class ContextMenuFragment extends Fragment {

    private Album mAlbum;

    private Artist mArtist;

    private Playlist mPlaylist;

    private PlaylistEntry mPlaylistEntry;

    private Query mQuery;

    private Collection mCollection;

    private boolean mFromPlaybackFragment;

    private final HashSet<String> mCorrespondingRequestIds = new HashSet<>();

    @SuppressWarnings("unused")
    public void onEventMainThread(InfoSystem.ResultsEvent event) {
        if (mCorrespondingRequestIds.contains(event.mInfoRequestData.getRequestId())
                && getView() != null) {
            ImageView albumImageView = (ImageView) getView().findViewById(R.id.album_imageview);
            Album album;
            if (mAlbum != null) {
                album = mAlbum;
            } else if (mQuery != null) {
                album = mQuery.getAlbum();
            } else {
                album = mPlaylistEntry.getAlbum();
            }
            TomahawkUtils.loadImageIntoImageView(TomahawkApp.getContext(), albumImageView,
                    album.getImage(), Image.getLargeImageSize(), true, false);
        }
    }

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container,
            Bundle savedInstanceState) {
        unpackArgs();
        int layoutResId = mFromPlaybackFragment ? R.layout.context_menu_fragment_playback
                : R.layout.context_menu_fragment;
        return inflater.inflate(layoutResId, container, false);
    }

    @Override
    public void onStart() {
        super.onStart();

        TomahawkMainActivity activity = (TomahawkMainActivity) getActivity();
        activity.hideActionbar();

        EventBus.getDefault().register(this);
    }

    @Override
    public void onViewCreated(final View view, Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);

        TomahawkMainActivity activity = (TomahawkMainActivity) getActivity();
        activity.hideActionbar();

        setupCloseButton(view);
        setupContextMenuItems(view);
        setupBlurredBackground(view);

        if (mFromPlaybackFragment) {
            setupPlaybackTextViews(view, activity.getPlaybackPanel());
            activity.getPlaybackPanel().showButtons();
        } else {
            setupTextViews(view);
            setupAlbumArt(view);
            activity.hidePlaybackPanel();
        }
    }

    @Override
    public void onStop() {
        TomahawkMainActivity activity = (TomahawkMainActivity) getActivity();
        activity.showActionBar(false);

        if (mFromPlaybackFragment) {
            activity.getPlaybackPanel().hideButtons();
        } else {
            activity.showPlaybackPanel(false);
        }

        EventBus.getDefault().unregister(this);

        super.onStop();
    }

    private void unpackArgs() {
        if (getArguments() != null) {
            if (getArguments().containsKey(TomahawkFragment.FROM_PLAYBACKFRAGMENT)) {
                mFromPlaybackFragment = getArguments()
                        .getBoolean(TomahawkFragment.FROM_PLAYBACKFRAGMENT);
            }
            if (getArguments().containsKey(TomahawkFragment.TOMAHAWKLISTITEM_TYPE)
                    && getArguments().containsKey(TomahawkFragment.TOMAHAWKLISTITEM)) {
                String type = getArguments().getString(TomahawkFragment.TOMAHAWKLISTITEM_TYPE);
                String key = getArguments().getString(TomahawkFragment.TOMAHAWKLISTITEM);
                switch (type) {
                    case TomahawkFragment.ALBUM:
                        mAlbum = Album.getByKey(key);
                        break;
                    case TomahawkFragment.PLAYLIST:
                        mPlaylist = Playlist.getByKey(key);
                        break;
                    case TomahawkFragment.ARTIST:
                        mArtist = Artist.getByKey(key);
                        break;
                    case TomahawkFragment.QUERY:
                        mQuery = Query.getByKey(key);
                        break;
                    case TomahawkFragment.SOCIALACTION:
                        SocialAction socialAction = SocialAction.getByKey(key);
                        Object targetObject = socialAction.getTargetObject();
                        if (targetObject instanceof Artist) {
                            mArtist = (Artist) targetObject;
                        } else if (targetObject instanceof Album) {
                            mAlbum = (Album) targetObject;
                        } else if (targetObject instanceof Query) {
                            mQuery = (Query) targetObject;
                        } else if (targetObject instanceof Playlist) {
                            mPlaylist = (Playlist) targetObject;
                        }
                        break;
                    case TomahawkFragment.PLAYLISTENTRY:
                        mPlaylistEntry = PlaylistEntry.getByKey(key);
                        break;
                }
            }
            if (getArguments().containsKey(TomahawkFragment.COLLECTION_ID)) {
                mCollection = CollectionManager.getInstance()
                        .getCollection(getArguments().getString(TomahawkFragment.COLLECTION_ID));
            }
        }
    }

    private void setupBlurredBackground(final View view) {
        final View rootView = getActivity().findViewById(R.id.sliding_layout);
        TomahawkUtils.afterViewGlobalLayout(new TomahawkUtils.ViewRunnable(rootView) {
            @Override
            public void run() {
                Bitmap bm = Bitmap.createBitmap(rootView.getWidth(),
                        rootView.getHeight(), Bitmap.Config.ARGB_8888);
                Canvas canvas = new Canvas(bm);
                rootView.draw(canvas);
                bm = Bitmap.createScaledBitmap(bm, bm.getWidth() / 4,
                        bm.getHeight() / 4, true);
                bm = BlurTransformation.staticTransform(bm, 25f);

                ImageView bgImageView =
                        (ImageView) view.findViewById(R.id.background);
                bgImageView.setImageBitmap(bm);
            }
        });
    }

    private void setupCloseButton(View view) {
        View closeButton = view.findViewById(R.id.close_button);
        closeButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                getActivity().getSupportFragmentManager().popBackStack();
                TomahawkMainActivity activity = (TomahawkMainActivity) getActivity();
                if (!activity.getSlidingUpPanelLayout().isPanelHidden()) {
                    AnimationUtils.fade(activity.getPlaybackPanel(),
                            AnimationUtils.DURATION_CONTEXTMENU, true);
                }
            }
        });
        TextView closeButtonText = (TextView) closeButton.findViewById(R.id.close_button_text);
        closeButtonText.setText(getString(R.string.button_close).toUpperCase());
    }

    private void setupContextMenuItems(View view) {
        final TomahawkMainActivity activity = (TomahawkMainActivity) getActivity();

        // set up "Add to playlist" context menu item
        if (mAlbum != null || mQuery != null || mPlaylistEntry != null || mPlaylist != null) {
            View v = TomahawkUtils.ensureInflation(view, R.id.context_menu_addtoplaylist_stub,
                    R.id.context_menu_addtoplaylist);
            TextView textView = (TextView) v.findViewById(R.id.textview);
            ImageView imageView = (ImageView) v.findViewById(R.id.imageview);
            imageView.setImageResource(R.drawable.ic_action_playlist_light);
            textView.setText(R.string.context_menu_add_to_playlist);
            v.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    getActivity().getSupportFragmentManager().popBackStack();
                    if (mAlbum != null) {
                        mCollection.getAlbumTracks(mAlbum).done(new DoneCallback<List<Query>>() {
                            @Override
                            public void onDone(List<Query> result) {
                                showAddToPlaylist(activity, new ArrayList<>(result));
                            }
                        });
                    } else if (mQuery != null) {
                        ArrayList<Query> queries = new ArrayList<>();
                        queries.add(mQuery);
                        showAddToPlaylist(activity, queries);
                    } else if (mPlaylistEntry != null) {
                        ArrayList<Query> queries = new ArrayList<>();
                        queries.add(mPlaylistEntry.getQuery());
                        showAddToPlaylist(activity, queries);
                    } else if (mPlaylist != null) {
                        showAddToPlaylist(activity, mPlaylist.getQueries());
                    }
                }
            });
        }

        // set up "Add to collection" context menu item
        if (mAlbum != null || mArtist != null) {
            int drawableResId;
            int stringResId;
            if ((mAlbum != null && DatabaseHelper.getInstance().isItemLoved(mAlbum))
                    || (mArtist != null && DatabaseHelper.getInstance().isItemLoved(mArtist))) {
                drawableResId = R.drawable.ic_action_collection_underlined;
                stringResId = R.string.context_menu_removefromcollection;
            } else {
                drawableResId = R.drawable.ic_action_collection;
                stringResId = R.string.context_menu_addtocollection;
            }
            View v = TomahawkUtils.ensureInflation(view, R.id.context_menu_addtocollection_stub,
                    R.id.context_menu_addtocollection);
            TextView textView = (TextView) v.findViewById(R.id.textview);
            ImageView imageView = (ImageView) v.findViewById(R.id.imageview);
            imageView.setImageResource(drawableResId);
            textView.setText(stringResId);
            v.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    getActivity().getSupportFragmentManager().popBackStack();
                    if (mAlbum != null) {
                        CollectionManager.getInstance().toggleLovedItem(mAlbum);
                    } else {
                        CollectionManager.getInstance().toggleLovedItem(mArtist);
                    }
                }
            });
        }

        // set up "Add to favorites" context menu item
        if (mQuery != null || mPlaylistEntry != null) {
            final Query query = mQuery != null ? mQuery : mPlaylistEntry.getQuery();
            int drawableResId;
            int stringResId;
            if (DatabaseHelper.getInstance().isItemLoved(query)) {
                drawableResId = R.drawable.ic_action_favorites_underlined;
                stringResId = R.string.context_menu_unlove;
            } else {
                drawableResId = R.drawable.ic_action_favorites;
                stringResId = R.string.context_menu_love;
            }
            View v = TomahawkUtils.ensureInflation(view, R.id.context_menu_favorite_stub,
                    R.id.context_menu_favorite);
            TextView textView = (TextView) v.findViewById(R.id.textview);
            ImageView imageView = (ImageView) v.findViewById(R.id.imageview);
            imageView.setImageResource(drawableResId);
            textView.setText(stringResId);
            v.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    getActivity().getSupportFragmentManager().popBackStack();
                    CollectionManager.getInstance().toggleLovedItem(query);
                }
            });
        }

        // set up "Share" context menu item
        View v = TomahawkUtils
                .ensureInflation(view, R.id.context_menu_share_stub, R.id.context_menu_share);
        TextView textView = (TextView) v.findViewById(R.id.textview);
        ImageView imageView = (ImageView) v.findViewById(R.id.imageview);
        imageView.setImageResource(R.drawable.ic_action_share);
        textView.setText(R.string.context_menu_share);
        v.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                getActivity().getSupportFragmentManager().popBackStack();
                if (mAlbum != null) {
                    ShareUtils.sendShareIntent(activity, mAlbum);
                } else if (mArtist != null) {
                    ShareUtils.sendShareIntent(activity, mArtist);
                } else if (mQuery != null) {
                    ShareUtils.sendShareIntent(activity, mQuery);
                } else if (mPlaylistEntry != null) {
                    ShareUtils.sendShareIntent(activity, mPlaylistEntry.getQuery());
                } else if (mPlaylist != null) {
                    ShareUtils.sendShareIntent(activity, mPlaylist);
                }
            }
        });

        // set up "Remove" context menu item
        if (mPlaylist != null || mPlaylistEntry != null) {
            final String playlistId = mPlaylist != null ? mPlaylist.getId()
                    : mPlaylistEntry.getPlaylistId();
            if (!DatabaseHelper.LOVEDITEMS_PLAYLIST_ID.equals(playlistId)
                    && DatabaseHelper.getInstance().getEmptyPlaylist(playlistId) != null) {
                int stringResId;
                if (mPlaylistEntry != null) {
                    stringResId = R.string.context_menu_removefromplaylist;
                } else {
                    stringResId = R.string.context_menu_delete;
                }
                v = TomahawkUtils.ensureInflation(view, R.id.context_menu_remove_stub,
                        R.id.context_menu_remove);
                textView = (TextView) v.findViewById(R.id.textview);
                imageView = (ImageView) v.findViewById(R.id.imageview);
                imageView.setImageResource(R.drawable.ic_player_exit_light);
                textView.setText(stringResId);
                v.setOnClickListener(new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        getActivity().getSupportFragmentManager().popBackStack();
                        if (mPlaylistEntry != null) {
                            CollectionManager.getInstance().deletePlaylistEntry(playlistId,
                                    mPlaylistEntry.getId());
                        } else {
                            CollectionManager.getInstance().deletePlaylist(playlistId);
                        }
                    }
                });
            }
        }
    }

    private void showAddToPlaylist(TomahawkMainActivity activity, List<Query> queries) {
        ArrayList<String> queryKeys = new ArrayList<>();
        for (Query query : queries) {
            queryKeys.add(query.getCacheKey());
        }
        Bundle bundle = new Bundle();
        bundle.putInt(TomahawkFragment.CONTENT_HEADER_MODE,
                ContentHeaderFragment.MODE_HEADER_STATIC);
        bundle.putStringArrayList(TomahawkFragment.QUERYARRAY, queryKeys);
        FragmentUtils.replace(activity, PlaylistsFragment.class, bundle);
    }

    private void setupTextViews(View view) {
        if (mAlbum != null) {
            View v = TomahawkUtils
                    .ensureInflation(view, R.id.album_name_button_stub, R.id.album_name_button);
            TextView textView = (TextView) v.findViewById(R.id.textview);
            textView.setText(mAlbum.getName());
            v.setOnClickListener(constructAlbumNameClickListener(mAlbum.getCacheKey()));
        } else if (mQuery != null || mPlaylistEntry != null || mPlaylist != null) {
            View v = TomahawkUtils.ensureInflation(view, R.id.track_name_stub, R.id.track_name);
            TextView textView = (TextView) v;
            if (mQuery != null) {
                textView.setText(mQuery.getName());
            } else if (mPlaylistEntry != null) {
                textView.setText(mPlaylistEntry.getName());
            } else if (mPlaylist != null) {
                textView.setText(mPlaylist.getName());
            }
        }
        if (mAlbum != null || mQuery != null || mPlaylistEntry != null || mArtist != null) {
            View v = TomahawkUtils
                    .ensureInflation(view, R.id.artist_name_button_stub, R.id.artist_name_button);
            TextView textView = (TextView) v.findViewById(R.id.textview);
            String cacheKey;
            if (mQuery != null) {
                textView.setText(mQuery.getArtist().getPrettyName());
                cacheKey = mQuery.getArtist().getCacheKey();
            } else if (mAlbum != null) {
                textView.setText(mAlbum.getArtist().getPrettyName());
                cacheKey = mAlbum.getArtist().getCacheKey();
            } else if (mPlaylistEntry != null) {
                textView.setText(mPlaylistEntry.getArtist().getPrettyName());
                cacheKey = mPlaylistEntry.getArtist().getCacheKey();
            } else {
                textView.setText(mArtist.getPrettyName());
                cacheKey = mArtist.getCacheKey();
            }
            v.setOnClickListener(constructArtistNameClickListener(cacheKey));
        }
    }

    private void setupPlaybackTextViews(View view, PlaybackPanel playbackPanel) {
        if (mAlbum != null
                || (mQuery != null
                && !TextUtils.isEmpty(mQuery.getAlbum().getName()))
                || (mPlaylistEntry != null
                && !TextUtils.isEmpty(mPlaylistEntry.getQuery().getAlbum().getName()))) {
            View v = TomahawkUtils
                    .ensureInflation(view, R.id.view_album_button_stub, R.id.view_album_button);
            TextView viewAlbumButtonText = (TextView) v.findViewById(R.id.textview);
            viewAlbumButtonText.setText(
                    TomahawkApp.getContext().getString(R.string.view_album).toUpperCase());
            String cacheKey;
            if (mAlbum != null) {
                cacheKey = mAlbum.getCacheKey();
            } else if (mQuery != null) {
                cacheKey = mQuery.getAlbum().getCacheKey();
            } else {
                cacheKey = mPlaylistEntry.getAlbum().getCacheKey();
            }
            v.setOnClickListener(constructAlbumNameClickListener(cacheKey));
        }
        if (mAlbum != null || mQuery != null || mPlaylistEntry != null || mArtist != null) {
            View artistNameButton = playbackPanel.findViewById(R.id.artist_name_button);
            String cacheKey;
            if (mAlbum != null) {
                cacheKey = mAlbum.getArtist().getCacheKey();
            } else if (mQuery != null) {
                cacheKey = mQuery.getArtist().getCacheKey();
            } else if (mPlaylistEntry != null) {
                cacheKey = mPlaylistEntry.getArtist().getCacheKey();
            } else {
                cacheKey = mArtist.getCacheKey();
            }
            artistNameButton.setOnClickListener(constructArtistNameClickListener(cacheKey));
        }
    }

    private void setupAlbumArt(View view) {
        if (mAlbum != null
                || (mQuery != null
                && !TextUtils.isEmpty(mQuery.getAlbum().getName()))
                || (mPlaylistEntry != null
                && !TextUtils.isEmpty(mPlaylistEntry.getQuery().getAlbum().getName()))) {
            View v = TomahawkUtils.ensureInflation(view, R.id.context_menu_albumart_stub,
                    R.id.context_menu_albumart);

            // load albumart image
            ImageView albumImageView = (ImageView) v.findViewById(R.id.album_imageview);
            Album album;
            String cacheKey;
            if (mAlbum != null) {
                album = mAlbum;
                cacheKey = mAlbum.getCacheKey();
            } else if (mQuery != null) {
                album = mQuery.getAlbum();
                cacheKey = mQuery.getAlbum().getCacheKey();
            } else {
                album = mPlaylistEntry.getAlbum();
                cacheKey = mPlaylistEntry.getAlbum().getCacheKey();
            }
            if (album.getImage() != null) {
                TomahawkUtils.loadImageIntoImageView(TomahawkApp.getContext(), albumImageView,
                        album.getImage(), Image.getLargeImageSize(), true, false);
            } else {
                String requestId = InfoSystem.getInstance().resolve(album);
                if (requestId != null) {
                    mCorrespondingRequestIds.add(requestId);
                }
            }

            // set text on "view album"-button and set up click listener
            View viewAlbumButton = view.findViewById(R.id.view_album_button);
            TextView viewAlbumButtonText =
                    (TextView) viewAlbumButton.findViewById(R.id.textview);
            viewAlbumButtonText.setText(
                    TomahawkApp.getContext().getString(R.string.view_album).toUpperCase());
            viewAlbumButton.setOnClickListener(constructAlbumNameClickListener(cacheKey));
        }
    }

    private View.OnClickListener constructArtistNameClickListener(final String cacheKey) {
        return new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                getActivity().getSupportFragmentManager().popBackStack();
                Bundle bundle = new Bundle();
                bundle.putString(TomahawkFragment.ARTIST, cacheKey);
                if (mCollection != null) {
                    bundle.putString(TomahawkFragment.COLLECTION_ID, mCollection.getId());
                }
                bundle.putInt(TomahawkFragment.CONTENT_HEADER_MODE,
                        ContentHeaderFragment.MODE_HEADER_DYNAMIC_PAGER);
                bundle.putLong(TomahawkFragment.CONTAINER_FRAGMENT_ID,
                        TomahawkMainActivity.getSessionUniqueId());
                FragmentUtils.replace((TomahawkMainActivity) getActivity(),
                        ArtistPagerFragment.class, bundle);
            }
        };
    }

    private View.OnClickListener constructAlbumNameClickListener(final String cachekey) {
        return new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                getActivity().getSupportFragmentManager().popBackStack();
                Bundle bundle = new Bundle();
                bundle.putString(TomahawkFragment.ALBUM, cachekey);
                if (mCollection != null) {
                    bundle.putString(TomahawkFragment.COLLECTION_ID, mCollection.getId());
                }
                bundle.putInt(TomahawkFragment.CONTENT_HEADER_MODE,
                        ContentHeaderFragment.MODE_HEADER_DYNAMIC);
                FragmentUtils.replace((TomahawkMainActivity) getActivity(),
                        TracksFragment.class, bundle);
            }
        };
    }
}


File: src/org/tomahawk/tomahawk_android/fragments/TomahawkFragment.java
/* == This file is part of Tomahawk Player - <http://tomahawk-player.org> ===
 *
 *   Copyright 2013, Christopher Reichert <creichert07@gmail.com>
 *   Copyright 2013, Enno Gottschalk <mrmaffen@googlemail.com>
 *
 *   Tomahawk is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   Tomahawk is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with Tomahawk. If not, see <http://www.gnu.org/licenses/>.
 */
package org.tomahawk.tomahawk_android.fragments;

import com.google.common.collect.Sets;

import org.tomahawk.libtomahawk.authentication.AuthenticatorManager;
import org.tomahawk.libtomahawk.authentication.HatchetAuthenticatorUtils;
import org.tomahawk.libtomahawk.collection.Album;
import org.tomahawk.libtomahawk.collection.Artist;
import org.tomahawk.libtomahawk.collection.Collection;
import org.tomahawk.libtomahawk.collection.CollectionManager;
import org.tomahawk.libtomahawk.collection.Playlist;
import org.tomahawk.libtomahawk.collection.PlaylistEntry;
import org.tomahawk.libtomahawk.database.DatabaseHelper;
import org.tomahawk.libtomahawk.infosystem.InfoSystem;
import org.tomahawk.libtomahawk.infosystem.SocialAction;
import org.tomahawk.libtomahawk.infosystem.User;
import org.tomahawk.libtomahawk.resolver.PipeLine;
import org.tomahawk.libtomahawk.resolver.Query;
import org.tomahawk.tomahawk_android.TomahawkApp;
import org.tomahawk.tomahawk_android.activities.TomahawkMainActivity;
import org.tomahawk.tomahawk_android.adapters.Segment;
import org.tomahawk.tomahawk_android.adapters.TomahawkListAdapter;
import org.tomahawk.tomahawk_android.services.PlaybackService;
import org.tomahawk.tomahawk_android.utils.FragmentUtils;
import org.tomahawk.tomahawk_android.utils.MultiColumnClickListener;
import org.tomahawk.tomahawk_android.utils.ThreadManager;
import org.tomahawk.tomahawk_android.utils.TomahawkRunnable;
import org.tomahawk.tomahawk_android.utils.WeakReferenceHandler;

import android.annotation.SuppressLint;
import android.content.SharedPreferences;
import android.os.Handler;
import android.os.Looper;
import android.os.Message;
import android.preference.PreferenceManager;
import android.text.TextUtils;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.widget.AbsListView;
import android.widget.AdapterView;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

import se.emilsjolander.stickylistheaders.StickyListHeadersListView;

/**
 * The base class for {@link AlbumsFragment}, {@link TracksFragment}, {@link ArtistsFragment},
 * {@link PlaylistsFragment} and {@link SearchPagerFragment}.
 */
public abstract class TomahawkFragment extends TomahawkListFragment
        implements MultiColumnClickListener, AbsListView.OnScrollListener {

    public static final String TAG = TomahawkFragment.class.getSimpleName();

    public static final String ALBUM = "album";

    public static final String ALBUMARRAY = "albumarray";

    public static final String ARTIST = "artist";

    public static final String ARTISTARRAY = "artistarray";

    public static final String PLAYLIST = "playlist";

    public static final String USER = "user";

    public static final String USERARRAY = "userarray";

    public static final String SOCIALACTION = "socialaction";

    public static final String PLAYLISTENTRY = "playlistentry";

    public static final String QUERY = "query";

    public static final String QUERYARRAY = "queryarray";

    public static final String PREFERENCEID = "preferenceid";

    public static final String TOMAHAWKLISTITEM = "tomahawklistitem";

    public static final String TOMAHAWKLISTITEM_TYPE = "tomahawklistitem_type";

    public static final String FROM_PLAYBACKFRAGMENT = "from_playbackfragment";

    public static final String QUERY_STRING = "query_string";

    public static final String SHOW_MODE = "show_mode";

    public static final String COLLECTION_ID = "collection_id";

    public static final String CONTENT_HEADER_MODE = "content_header_mode";

    public static final String CONTAINER_FRAGMENT_ID = "container_fragment_id";

    public static final String CONTAINER_FRAGMENT_PAGE = "container_fragment_page";

    public static final String CONTAINER_FRAGMENT_CLASSNAME = "container_fragment_classname";

    public static final String LIST_SCROLL_POSITION = "list_scroll_position";

    protected static final int RESOLVE_QUERIES_REPORTER_MSG = 1336;

    protected static final long RESOLVE_QUERIES_REPORTER_DELAY = 100;

    protected static final int ADAPTER_UPDATE_MSG = 1337;

    protected static final long ADAPTER_UPDATE_DELAY = 500;

    public static final int CREATE_PLAYLIST_BUTTON_ID = 8008135;

    private TomahawkListAdapter mTomahawkListAdapter;

    protected boolean mIsResumed;

    protected final Set<String> mCorrespondingRequestIds =
            Sets.newSetFromMap(new ConcurrentHashMap<String, Boolean>());

    protected final HashSet<Object> mResolvingItems = new HashSet<>();

    protected final Set<Query> mCorrespondingQueries
            = Sets.newSetFromMap(new ConcurrentHashMap<Query, Boolean>());

    protected ArrayList<Query> mQueryArray;

    protected ArrayList<Album> mAlbumArray;

    protected ArrayList<Artist> mArtistArray;

    protected ArrayList<User> mUserArray;

    protected Album mAlbum;

    protected Artist mArtist;

    protected Playlist mPlaylist;

    protected User mUser;

    protected Query mQuery;

    private int mFirstVisibleItemLastTime = -1;

    private int mVisibleItemCount = 0;

    protected int mShowMode;

    private final Handler mResolveQueriesHandler = new ResolveQueriesHandler(this);

    private static class ResolveQueriesHandler extends WeakReferenceHandler<TomahawkFragment> {

        public ResolveQueriesHandler(TomahawkFragment referencedObject) {
            super(referencedObject);
        }

        @Override
        public void handleMessage(Message msg) {
            TomahawkFragment fragment = getReferencedObject();
            if (fragment != null) {
                removeMessages(msg.what);
                fragment.resolveVisibleItems();
            }
        }
    }

    // Handler which reports the PipeLine's and InfoSystem's results in intervals
    protected final Handler mAdapterUpdateHandler = new AdapterUpdateHandler(this);

    private static class AdapterUpdateHandler extends WeakReferenceHandler<TomahawkFragment> {

        public AdapterUpdateHandler(TomahawkFragment referencedObject) {
            super(referencedObject);
        }

        @Override
        public void handleMessage(Message msg) {
            TomahawkFragment fragment = getReferencedObject();
            if (fragment != null) {
                removeMessages(msg.what);
                fragment.updateAdapter();
            }
        }
    }

    @SuppressWarnings("unused")
    public void onEvent(PipeLine.ResolversChangedEvent event) {
        forceResolveVisibleItems(true);
    }

    @SuppressWarnings("unused")
    public void onEvent(PipeLine.ResultsEvent event) {
        if (mCorrespondingQueries.contains(event.mQuery)) {
            if (!mAdapterUpdateHandler.hasMessages(ADAPTER_UPDATE_MSG)) {
                mAdapterUpdateHandler.sendEmptyMessageDelayed(ADAPTER_UPDATE_MSG,
                        ADAPTER_UPDATE_DELAY);
            }
        }
    }

    @SuppressWarnings("unused")
    public void onEvent(InfoSystem.ResultsEvent event) {
        if (mCorrespondingRequestIds.contains(event.mInfoRequestData.getRequestId())) {
            if (!mAdapterUpdateHandler.hasMessages(ADAPTER_UPDATE_MSG)) {
                mAdapterUpdateHandler.sendEmptyMessageDelayed(ADAPTER_UPDATE_MSG,
                        ADAPTER_UPDATE_DELAY);
            }
        }
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(PlaybackService.PlayingTrackChangedEvent event) {
        onTrackChanged();
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(PlaybackService.PlayStateChangedEvent event) {
        onPlaystateChanged();
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(PlaybackService.PlayingPlaylistChangedEvent event) {
        onPlaylistChanged();
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(CollectionManager.UpdatedEvent event) {
        if (event.mUpdatedItemIds != null) {
            if ((mPlaylist != null && event.mUpdatedItemIds.contains(mPlaylist.getId()))
                    || (mAlbum != null && event.mUpdatedItemIds.contains(mAlbum.getCacheKey()))
                    || (mArtist != null && event.mUpdatedItemIds.contains(mArtist.getCacheKey()))
                    || (mQuery != null && event.mUpdatedItemIds.contains(mQuery.getCacheKey()))) {
                if (!mAdapterUpdateHandler.hasMessages(ADAPTER_UPDATE_MSG)) {
                    mAdapterUpdateHandler.sendEmptyMessageDelayed(ADAPTER_UPDATE_MSG,
                            ADAPTER_UPDATE_DELAY);
                }
            }
        } else {
            if (!mAdapterUpdateHandler.hasMessages(ADAPTER_UPDATE_MSG)) {
                mAdapterUpdateHandler.sendEmptyMessageDelayed(ADAPTER_UPDATE_MSG,
                        ADAPTER_UPDATE_DELAY);
            }
        }
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(PlaybackService.ReadyEvent event) {
        onPlaybackServiceReady();
    }

    @SuppressWarnings("unused")
    public void onEventMainThread(PlaybackService.PlayPositionChangedEvent event) {
        if (mTomahawkListAdapter != null) {
            mTomahawkListAdapter.onPlayPositionChanged(event.duration, event.currentPosition);
        }
    }

    @Override
    public void onResume() {
        super.onResume();

        if (getArguments() != null) {
            if (getArguments().containsKey(ALBUM)
                    && !TextUtils.isEmpty(getArguments().getString(ALBUM))) {
                mAlbum = Album.getByKey(getArguments().getString(ALBUM));
                if (mAlbum == null) {
                    getActivity().getSupportFragmentManager().popBackStack();
                    return;
                } else {
                    String requestId = InfoSystem.getInstance().resolve(mAlbum);
                    if (requestId != null) {
                        mCorrespondingRequestIds.add(requestId);
                    }
                }
            }
            if (getArguments().containsKey(PLAYLIST)
                    && !TextUtils.isEmpty(getArguments().getString(PLAYLIST))) {
                String playlistId = getArguments().getString(TomahawkFragment.PLAYLIST);
                mPlaylist = DatabaseHelper.getInstance().getPlaylist(playlistId);
                if (mPlaylist == null) {
                    mPlaylist = Playlist.getByKey(playlistId);
                    if (mPlaylist == null) {
                        getActivity().getSupportFragmentManager().popBackStack();
                        return;
                    } else {
                        HatchetAuthenticatorUtils authenticatorUtils
                                = (HatchetAuthenticatorUtils) AuthenticatorManager.getInstance()
                                .getAuthenticatorUtils(TomahawkApp.PLUGINNAME_HATCHET);
                        if (mUser != authenticatorUtils.getLoggedInUser()) {
                            String requestId = InfoSystem.getInstance().resolve(mPlaylist);
                            if (requestId != null) {
                                mCorrespondingRequestIds.add(requestId);
                            }
                        }
                    }
                }
            }
            if (getArguments().containsKey(ARTIST)
                    && !TextUtils.isEmpty(getArguments().getString(ARTIST))) {
                mArtist = Artist.getByKey(getArguments().getString(ARTIST));
                if (mArtist == null) {
                    getActivity().getSupportFragmentManager().popBackStack();
                    return;
                } else {
                    ArrayList<String> requestIds = InfoSystem.getInstance().resolve(mArtist, false);
                    for (String requestId : requestIds) {
                        mCorrespondingRequestIds.add(requestId);
                    }
                }
            }
            if (getArguments().containsKey(USER)
                    && !TextUtils.isEmpty(getArguments().getString(USER))) {
                mUser = User.getUserById(getArguments().getString(USER));
                if (mUser == null) {
                    getActivity().getSupportFragmentManager().popBackStack();
                    return;
                } else if (mUser.getName() == null) {
                    String requestId = InfoSystem.getInstance().resolve(mUser);
                    if (requestId != null) {
                        mCorrespondingRequestIds.add(requestId);
                    }
                }
            }
            if (getArguments().containsKey(COLLECTION_ID)) {
                mCollection = CollectionManager.getInstance()
                        .getCollection(getArguments().getString(COLLECTION_ID));
            } else {
                mCollection = CollectionManager.getInstance()
                        .getCollection(TomahawkApp.PLUGINNAME_HATCHET);
            }
            if (getArguments().containsKey(QUERY)
                    && !TextUtils.isEmpty(getArguments().getString(QUERY))) {
                mQuery = Query.getByKey(getArguments().getString(QUERY));
                if (mQuery == null) {
                    getActivity().getSupportFragmentManager().popBackStack();
                    return;
                } else {
                    ArrayList<String> requestIds =
                            InfoSystem.getInstance().resolve(mQuery.getArtist(), false);
                    for (String requestId : requestIds) {
                        mCorrespondingRequestIds.add(requestId);
                    }
                }
            }
            if (getArguments().containsKey(USERARRAY)) {
                mUserArray = new ArrayList<>();
                for (String userId : getArguments().getStringArrayList(USERARRAY)) {
                    mUserArray.add(User.getUserById(userId));
                }
            }
            if (getArguments().containsKey(ARTISTARRAY)) {
                mArtistArray = new ArrayList<>();
                for (String artistKey : getArguments().getStringArrayList(ARTISTARRAY)) {
                    Artist artist = Artist.getByKey(artistKey);
                    if (artist != null) {
                        mArtistArray.add(artist);
                    }
                }
            }
            if (getArguments().containsKey(ALBUMARRAY)) {
                mAlbumArray = new ArrayList<>();
                for (String albumKey : getArguments().getStringArrayList(ALBUMARRAY)) {
                    Album album = Album.getByKey(albumKey);
                    if (album != null) {
                        mAlbumArray.add(album);
                    }
                }
            }
            if (getArguments().containsKey(QUERYARRAY)) {
                mQueryArray = new ArrayList<>();
                for (String queryKey : getArguments().getStringArrayList(QUERYARRAY)) {
                    Query query = Query.getByKey(queryKey);
                    if (query != null) {
                        mQueryArray.add(query);
                    }
                }
            }
        }

        StickyListHeadersListView list = getListView();
        if (list != null) {
            list.setOnScrollListener(this);
            if (mTomahawkListAdapter != null) {
                getListView().setOnItemClickListener(mTomahawkListAdapter);
                getListView().setOnItemLongClickListener(mTomahawkListAdapter);
            }
        }

        onPlaylistChanged();

        mIsResumed = true;
    }

    @Override
    public void onPause() {
        super.onPause();

        for (Query query : mCorrespondingQueries) {
            if (ThreadManager.getInstance().stop(query)) {
                mCorrespondingQueries.remove(query);
            }
        }

        mAdapterUpdateHandler.removeCallbacksAndMessages(null);

        mIsResumed = false;
    }

    @Override
    public abstract void onItemClick(View view, Object item);

    /**
     * Called every time an item inside a ListView or GridView is long-clicked
     *
     * @param item the Object which corresponds to the long-click
     */
    @Override
    public boolean onItemLongClick(View view, Object item) {
        return FragmentUtils.showContextMenu((TomahawkMainActivity) getActivity(), item,
                mCollection.getId(), false);
    }

    protected void fillAdapter(Segment segment, Collection collection) {
        List<Segment> segments = new ArrayList<>();
        segments.add(segment);
        fillAdapter(segments, null, collection);
    }

    protected void fillAdapter(Segment segment) {
        List<Segment> segments = new ArrayList<>();
        segments.add(segment);
        fillAdapter(segments, null, null);
    }

    protected void fillAdapter(List<Segment> segments) {
        fillAdapter(segments, null, null);
    }

    protected void fillAdapter(final List<Segment> segments, final View headerSpacerForwardView,
            final Collection collection) {
        final TomahawkMainActivity activity = (TomahawkMainActivity) getActivity();
        if (activity != null && getListView() != null) {
            new Handler(Looper.getMainLooper()).post(new Runnable() {
                @Override
                public void run() {
                    if (mTomahawkListAdapter == null) {
                        LayoutInflater inflater = activity.getLayoutInflater();
                        TomahawkListAdapter adapter = new TomahawkListAdapter(activity, inflater,
                                segments, collection, getListView(), TomahawkFragment.this);
                        TomahawkFragment.super.setListAdapter(adapter);
                        mTomahawkListAdapter = adapter;
                        getListView().setOnItemClickListener(mTomahawkListAdapter);
                        getListView().setOnItemLongClickListener(mTomahawkListAdapter);
                    } else {
                        mTomahawkListAdapter.setSegments(segments, getListView());
                    }
                    updateShowPlaystate();
                    forceResolveVisibleItems(false);
                    setupNonScrollableSpacer(getListView());
                    setupScrollableSpacer(getListAdapter(), getListView(), headerSpacerForwardView);
                    if (headerSpacerForwardView == null) {
                        setupAnimations();
                    }
                }
            });
        } else {
            Log.e(TAG, "fillAdapter - getActivity() or getListView() returned null!");
        }
    }

    /**
     * Get the {@link TomahawkListAdapter} associated with this activity's ListView.
     */
    public TomahawkListAdapter getListAdapter() {
        return (TomahawkListAdapter) super.getListAdapter();
    }

    protected void setAreHeadersSticky(final boolean areHeadersSticky) {
        new Handler(Looper.getMainLooper()).post(new Runnable() {
            @Override
            public void run() {
                if (getListView() != null) {
                    getListView().setAreHeadersSticky(areHeadersSticky);
                } else {
                    Log.e(TAG, "setAreHeadersSticky - getListView() returned null!");
                }
            }
        });
    }

    /**
     * Update this {@link TomahawkFragment}'s {@link TomahawkListAdapter} content
     */
    protected abstract void updateAdapter();

    /**
     * If the PlaybackService signals, that it is ready, this method is being called
     */
    protected void onPlaybackServiceReady() {
        updateShowPlaystate();
    }

    /**
     * Called when the PlaybackServiceBroadcastReceiver received a Broadcast indicating that the
     * playlist has changed inside our PlaybackService
     */
    protected void onPlaylistChanged() {
        updateShowPlaystate();
    }

    /**
     * Called when the PlaybackServiceBroadcastReceiver in PlaybackFragment received a Broadcast
     * indicating that the playState (playing or paused) has changed inside our PlaybackService
     */
    protected void onPlaystateChanged() {
        updateShowPlaystate();
    }

    /**
     * Called when the PlaybackServiceBroadcastReceiver received a Broadcast indicating that the
     * track has changed inside our PlaybackService
     */
    protected void onTrackChanged() {
        updateShowPlaystate();
    }

    private void updateShowPlaystate() {
        PlaybackService playbackService = ((TomahawkMainActivity) getActivity())
                .getPlaybackService();
        if (mTomahawkListAdapter != null) {
            if (playbackService != null) {
                mTomahawkListAdapter.setShowPlaystate(true);
                mTomahawkListAdapter.setHighlightedItemIsPlaying(playbackService.isPlaying());
                mTomahawkListAdapter.setHighlightedEntry(playbackService.getCurrentEntry());
                mTomahawkListAdapter.setHighlightedQuery(playbackService.getCurrentQuery());
            } else {
                mTomahawkListAdapter.setShowPlaystate(false);
            }
            mTomahawkListAdapter.notifyDataSetChanged();
        }
    }

    @Override
    public void onScroll(AbsListView view, int firstVisibleItem, int visibleItemCount,
            int totalItemCount) {
        super.onScroll(view, firstVisibleItem, visibleItemCount, totalItemCount);

        mVisibleItemCount = visibleItemCount;
        if (mFirstVisibleItemLastTime != firstVisibleItem) {
            mFirstVisibleItemLastTime = firstVisibleItem;
            mResolveQueriesHandler.removeCallbacksAndMessages(null);
            mResolveQueriesHandler.sendEmptyMessageDelayed(RESOLVE_QUERIES_REPORTER_MSG,
                    RESOLVE_QUERIES_REPORTER_DELAY);
        }
    }

    protected void forceResolveVisibleItems(boolean reresolve) {
        if (reresolve) {
            mCorrespondingQueries.clear();
        }
        mResolveQueriesHandler.removeCallbacksAndMessages(null);
        mResolveQueriesHandler.sendEmptyMessageDelayed(RESOLVE_QUERIES_REPORTER_MSG,
                RESOLVE_QUERIES_REPORTER_DELAY);
    }

    private void resolveVisibleItems() {
        resolveItemsFromTo(mFirstVisibleItemLastTime - 2,
                mFirstVisibleItemLastTime + mVisibleItemCount + 2);
    }

    private void resolveItemsFromTo(int start, int end) {
        if (mTomahawkListAdapter != null) {
            start = Math.max(start, 0);
            end = Math.min(end, mTomahawkListAdapter.getCount());
            for (int i = start; i < end; i++) {
                Object object = mTomahawkListAdapter.getItem(i);
                if (object instanceof List) {
                    for (Object item : (List) object) {
                        resolveItem(item);
                    }
                } else {
                    resolveItem(object);
                }
            }
        }
    }

    private void resolveItem(final Object object) {
        PlaylistEntry entry = mTomahawkListAdapter.getPlaylistEntry(object);
        if (entry != null) {
            Query q = entry.getQuery();
            if (!q.isSolved() && !mCorrespondingQueries.contains(q)) {
                mCorrespondingQueries.add(PipeLine.getInstance().resolve(q));
            }
        }
        if (object instanceof Playlist) {
            resolveItem((Playlist) object);
        } else if (object instanceof SocialAction) {
            resolveItem((SocialAction) object);
        } else if (object instanceof Album) {
            resolveItem((Album) object);
        } else if (object instanceof Artist) {
            resolveItem((Artist) object);
        } else if (object instanceof User) {
            resolveItem((User) object);
        }
    }

    private void resolveItem(final Playlist playlist) {
        HatchetAuthenticatorUtils authenticatorUtils
                = (HatchetAuthenticatorUtils) AuthenticatorManager.getInstance()
                .getAuthenticatorUtils(TomahawkApp.PLUGINNAME_HATCHET);
        if (mUser == null || mUser == authenticatorUtils.getLoggedInUser()) {
            TomahawkRunnable r = new TomahawkRunnable(TomahawkRunnable.PRIORITY_IS_DATABASEACTION) {
                @Override
                public void run() {
                    if (mResolvingItems.add(playlist)) {
                        Playlist pl = playlist;
                        if (pl.getEntries().size() == 0) {
                            pl = DatabaseHelper.getInstance().getPlaylist(pl.getId());
                        }
                        if (pl != null && pl.getEntries().size() > 0) {
                            pl.updateTopArtistNames();
                            DatabaseHelper.getInstance().updatePlaylist(pl);
                            if (pl.getTopArtistNames() != null) {
                                for (int i = 0; i < pl.getTopArtistNames().length && i < 5;
                                        i++) {
                                    resolveItem(Artist.get(pl.getTopArtistNames()[i]));
                                }
                            }
                        } else {
                            mResolvingItems.remove(pl);
                        }
                    }
                }
            };
            ThreadManager.getInstance().execute(r);
        }
    }

    private void resolveItem(SocialAction socialAction) {
        if (mResolvingItems.add(socialAction)) {
            if (socialAction.getTargetObject() != null) {
                resolveItem(socialAction.getTargetObject());
            }
            resolveItem(socialAction.getUser());
        }
    }

    private void resolveItem(Album album) {
        if (mResolvingItems.add(album)) {
            if (album.getImage() == null) {
                String requestId = InfoSystem.getInstance().resolve(album);
                if (requestId != null) {
                    mCorrespondingRequestIds.add(requestId);
                }
            }
        }
    }

    private void resolveItem(Artist artist) {
        if (mResolvingItems.add(artist)) {
            if (artist.getImage() == null) {
                mCorrespondingRequestIds.addAll(InfoSystem.getInstance().resolve(artist, false));
            }
        }
    }

    private void resolveItem(User user) {
        if (mResolvingItems.add(user)) {
            if (user.getImage() == null) {
                String requestId = InfoSystem.getInstance().resolve(user);
                if (requestId != null) {
                    mCorrespondingRequestIds.add(requestId);
                }
            }
        }
    }

    protected AdapterView.OnItemSelectedListener constructDropdownListener(final String prefKey) {
        return new AdapterView.OnItemSelectedListener() {
            @SuppressLint("CommitPrefEdits")
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                if (getDropdownPos(prefKey) != position) {
                    SharedPreferences preferences = PreferenceManager
                            .getDefaultSharedPreferences(TomahawkApp.getContext());
                    preferences.edit().putInt(prefKey, position).commit();
                    updateAdapter();
                }
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        };
    }

    protected int getDropdownPos(String prefKey) {
        SharedPreferences preferences = PreferenceManager
                .getDefaultSharedPreferences(TomahawkApp.getContext());
        return preferences.getInt(prefKey, 0);
    }
}



File: src/org/tomahawk/tomahawk_android/fragments/TracksFragment.java
/* == This file is part of Tomahawk Player - <http://tomahawk-player.org> ===
 *
 *   Copyright 2012, Enno Gottschalk <mrmaffen@googlemail.com>
 *
 *   Tomahawk is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   Tomahawk is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with Tomahawk. If not, see <http://www.gnu.org/licenses/>.
 */
package org.tomahawk.tomahawk_android.fragments;

import org.jdeferred.DoneCallback;
import org.tomahawk.libtomahawk.collection.AlphaComparator;
import org.tomahawk.libtomahawk.collection.ArtistAlphaComparator;
import org.tomahawk.libtomahawk.collection.Collection;
import org.tomahawk.libtomahawk.collection.CollectionManager;
import org.tomahawk.libtomahawk.collection.CollectionUtils;
import org.tomahawk.libtomahawk.collection.LastModifiedComparator;
import org.tomahawk.libtomahawk.collection.PlaylistEntry;
import org.tomahawk.libtomahawk.collection.Track;
import org.tomahawk.libtomahawk.collection.UserCollection;
import org.tomahawk.libtomahawk.resolver.Query;
import org.tomahawk.libtomahawk.resolver.QueryComparator;
import org.tomahawk.tomahawk_android.R;
import org.tomahawk.tomahawk_android.TomahawkApp;
import org.tomahawk.tomahawk_android.activities.TomahawkMainActivity;
import org.tomahawk.tomahawk_android.adapters.Segment;
import org.tomahawk.tomahawk_android.services.PlaybackService;
import org.tomahawk.tomahawk_android.views.FancyDropDown;

import android.view.View;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Set;

/**
 * {@link TomahawkFragment} which shows a set of {@link Track}s inside its {@link
 * se.emilsjolander.stickylistheaders.StickyListHeadersListView}
 */
public class TracksFragment extends TomahawkFragment {

    public static final String COLLECTION_TRACKS_SPINNER_POSITION
            = "org.tomahawk.tomahawk_android.collection_tracks_spinner_position";

    @SuppressWarnings("unused")
    public void onEventMainThread(CollectionManager.UpdatedEvent event) {
        super.onEventMainThread(event);

        if (event.mUpdatedItemIds != null && event.mUpdatedItemIds.contains(mAlbum.getCacheKey())) {
            showAlbumFancyDropDown();
        }
    }

    @Override
    public void onResume() {
        super.onResume();

        if (mContainerFragmentClass == null) {
            getActivity().setTitle("");
        }
        updateAdapter();
    }

    /**
     * Called every time an item inside a ListView or GridView is clicked
     *
     * @param view the clicked view
     * @param item the Object which corresponds to the click
     */
    @Override
    public void onItemClick(View view, Object item) {
        if (item instanceof Query) {
            PlaylistEntry entry = getListAdapter().getPlaylistEntry(item);
            if (entry.getQuery().isPlayable()) {
                TomahawkMainActivity activity = (TomahawkMainActivity) getActivity();
                PlaybackService playbackService = activity.getPlaybackService();
                if (playbackService != null) {
                    if (playbackService.getCurrentEntry() == entry) {
                        playbackService.playPause();
                    } else {
                        playbackService.setPlaylist(getListAdapter().getPlaylist(), entry);
                        playbackService.start();
                    }
                }
            }
        }
    }

    /**
     * Update this {@link TomahawkFragment}'s {@link org.tomahawk.tomahawk_android.adapters.TomahawkListAdapter}
     * content
     */
    @Override
    protected void updateAdapter() {
        if (!mIsResumed) {
            return;
        }

        if (mAlbum != null) {
            showContentHeader(mAlbum);
            showAlbumFancyDropDown();
            mCollection.getAlbumTracks(mAlbum).done(new DoneCallback<List<Query>>() {
                @Override
                public void onDone(List<Query> queries) {
                    Collections.sort(queries,
                            new QueryComparator(QueryComparator.COMPARE_ALBUMPOS));
                    Segment segment = new Segment(mAlbum.getArtist().getPrettyName(), queries);
                    if (CollectionUtils.allFromOneArtist(queries)) {
                        segment.setHideArtistName(true);
                        segment.setShowDuration(true);
                    }
                    segment.setShowNumeration(true, 1);
                    fillAdapter(segment);
                }
            });
        } else if (mQuery != null) {
            ArrayList<Object> queries = new ArrayList<>();
            queries.add(mQuery);
            Segment segment = new Segment(queries);
            segment.setShowDuration(true);
            fillAdapter(segment);
            showContentHeader(mQuery);
            showFancyDropDown(0, mQuery.getName(), null, null);
        } else if (mQueryArray != null) {
            Segment segment = new Segment(mQueryArray);
            segment.setShowDuration(true);
            fillAdapter(segment);
        } else {
            mCollection.getQueries().done(new DoneCallback<Set<Query>>() {
                @Override
                public void onDone(Set<Query> queries) {
                    fillAdapter(new Segment(getDropdownPos(COLLECTION_TRACKS_SPINNER_POSITION),
                            constructDropdownItems(),
                            constructDropdownListener(COLLECTION_TRACKS_SPINNER_POSITION),
                            sortQueries(queries)));
                }
            });
        }
    }

    private List<Integer> constructDropdownItems() {
        List<Integer> dropDownItems = new ArrayList<>();
        dropDownItems.add(R.string.collection_dropdown_recently_added);
        dropDownItems.add(R.string.collection_dropdown_alpha);
        dropDownItems.add(R.string.collection_dropdown_alpha_artists);
        return dropDownItems;
    }

    private List<Query> sortQueries(java.util.Collection<Query> queries) {
        List<Query> sortedQueries;
        if (queries instanceof List) {
            sortedQueries = (List<Query>) queries;
        } else {
            sortedQueries = new ArrayList<>(queries);
        }
        switch (getDropdownPos(COLLECTION_TRACKS_SPINNER_POSITION)) {
            case 0:
                UserCollection userColl = (UserCollection) CollectionManager.getInstance()
                        .getCollection(TomahawkApp.PLUGINNAME_USERCOLLECTION);
                Collections.sort(sortedQueries,
                        new LastModifiedComparator<>(userColl.getQueryTimeStamps()));
                break;
            case 1:
                Collections.sort(sortedQueries, new AlphaComparator());
                break;
            case 2:
                Collections.sort(sortedQueries, new ArtistAlphaComparator());
                break;
        }
        return sortedQueries;
    }

    private void showAlbumFancyDropDown() {
        if (mAlbum != null) {
            CollectionManager.getInstance().getAvailableCollections(mAlbum).done(
                    new DoneCallback<List<Collection>>() {
                        @Override
                        public void onDone(final List<Collection> result) {
                            int initialSelection = 0;
                            for (int i = 0; i < result.size(); i++) {
                                if (result.get(i) == mCollection) {
                                    initialSelection = i;
                                    break;
                                }
                            }
                            showFancyDropDown(mAlbum.getName(), initialSelection,
                                    FancyDropDown.convertToDropDownItemInfo(result),
                                    new FancyDropDown.DropDownListener() {
                                        @Override
                                        public void onDropDownItemSelected(int position) {
                                            mCollection = result.get(position);
                                            updateAdapter();
                                        }

                                        @Override
                                        public void onCancel() {
                                        }
                                    });
                        }
                    });
        }
    }
}


File: src/org/tomahawk/tomahawk_android/fragments/UserCollectionFragment.java
/* == This file is part of Tomahawk Player - <http://tomahawk-player.org> ===
 *
 *   Copyright 2014, Enno Gottschalk <mrmaffen@googlemail.com>
 *
 *   Tomahawk is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   Tomahawk is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with Tomahawk. If not, see <http://www.gnu.org/licenses/>.
 */
package org.tomahawk.tomahawk_android.fragments;

import org.jdeferred.DoneCallback;
import org.tomahawk.libtomahawk.collection.Album;
import org.tomahawk.libtomahawk.collection.Collection;
import org.tomahawk.libtomahawk.collection.CollectionManager;
import org.tomahawk.libtomahawk.infosystem.InfoSystem;
import org.tomahawk.tomahawk_android.R;
import org.tomahawk.tomahawk_android.TomahawkApp;
import org.tomahawk.tomahawk_android.activities.TomahawkMainActivity;
import org.tomahawk.tomahawk_android.utils.FragmentUtils;

import android.os.Bundle;
import android.view.View;

public class UserCollectionFragment extends TomahawkFragment {

    public static final String USER_COLLECTION_SPINNER_POSITION
            = "org.tomahawk.tomahawk_android.user_collection_spinner_position";

    @Override
    public void onResume() {
        super.onResume();

        if (mUser == null) {
            getActivity().setTitle(getString(R.string.drawer_title_collection).toUpperCase());
        } else {
            mCorrespondingRequestIds.add(InfoSystem.getInstance().resolveStarredAlbums(mUser));
        }

        updateAdapter();
    }

    /**
     * Called every time an item inside a ListView or GridView is clicked
     *
     * @param view the clicked view
     * @param item the Object which corresponds to the click
     */
    @Override
    public void onItemClick(View view, final Object item) {
        if (item instanceof Album) {
            final Collection userCollection = CollectionManager.getInstance()
                    .getCollection(TomahawkApp.PLUGINNAME_USERCOLLECTION);
            userCollection.hasAlbumTracks((Album) item).done(new DoneCallback<Boolean>() {
                @Override
                public void onDone(Boolean result) {
                    TomahawkMainActivity activity = (TomahawkMainActivity) getActivity();
                    Bundle bundle = new Bundle();
                    if (result) {
                        bundle.putString(TomahawkFragment.ALBUM, ((Album) item).getCacheKey());
                        bundle.putString(TomahawkFragment.COLLECTION_ID, userCollection.getId());
                        bundle.putInt(CONTENT_HEADER_MODE,
                                ContentHeaderFragment.MODE_HEADER_DYNAMIC);
                        FragmentUtils.replace(activity, TracksFragment.class, bundle);
                    } else {
                        bundle.putString(TomahawkFragment.ALBUM, ((Album) item).getCacheKey());
                        bundle.putString(TomahawkFragment.COLLECTION_ID,
                                CollectionManager.getInstance()
                                        .getCollection(TomahawkApp.PLUGINNAME_HATCHET).getId());
                        bundle.putInt(CONTENT_HEADER_MODE,
                                ContentHeaderFragment.MODE_HEADER_DYNAMIC);
                        FragmentUtils.replace(activity, TracksFragment.class, bundle);
                    }
                }
            });
        }
    }

    /**
     * Update this {@link org.tomahawk.tomahawk_android.fragments.TomahawkFragment}'s {@link
     * org.tomahawk.tomahawk_android.adapters.TomahawkListAdapter} content
     */
    @Override
    protected void updateAdapter() {
        /*if (!mIsResumed) {
            return;
        }

        ArrayList items = new ArrayList();
        if (mUser != null) {
            items.addAll(mUser.getStarredAlbums());
        } else {
            items.addAll(CollectionManager.getInstance()
                    .getCollection(TomahawkApp.PLUGINNAME_USERCOLLECTION).getAlbums());
            for (Album album : DatabaseHelper.getInstance().getStarredAlbums()) {
                if (!items.contains(album)) {
                    items.add(album);
                }
            }
        }

        SharedPreferences preferences =
                PreferenceManager.getDefaultSharedPreferences(TomahawkApp.getContext());
        List<Integer> dropDownItems = new ArrayList<>();
        dropDownItems.add(R.string.collection_dropdown_recently_added);
        dropDownItems.add(R.string.collection_dropdown_alpha);
        dropDownItems.add(R.string.collection_dropdown_alpha_artists);
        AdapterView.OnItemSelectedListener spinnerClickListener
                = new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                SharedPreferences preferences =
                        PreferenceManager.getDefaultSharedPreferences(TomahawkApp.getContext());
                int initialPos = preferences.getInt(USER_COLLECTION_SPINNER_POSITION, 0);
                if (initialPos != position) {
                    preferences.edit().putInt(USER_COLLECTION_SPINNER_POSITION, position).commit();
                    updateAdapter();
                }
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        };
        int initialPos = preferences.getInt(USER_COLLECTION_SPINNER_POSITION, 0);
        if (initialPos == 0) {
            UserCollection userColl = (UserCollection) CollectionManager.getInstance()
                    .getCollection(TomahawkApp.PLUGINNAME_USERCOLLECTION);
            Collections.sort(items, new TomahawkListItemComparator(
                    TomahawkListItemComparator.COMPARE_RECENTLY_ADDED,
                    userColl.getAlbumTimeStamps()));
        } else if (initialPos == 1) {
            Collections.sort(items, new TomahawkListItemComparator(
                    TomahawkListItemComparator.COMPARE_ALPHA));
        } else if (initialPos == 2) {
            Collections.sort(items, new TomahawkListItemComparator(
                    TomahawkListItemComparator.COMPARE_ARTIST_ALPHA));
        }
        fillAdapter(new Segment(initialPos, dropDownItems, spinnerClickListener, items,
                R.integer.grid_column_count, R.dimen.padding_superlarge,
                R.dimen.padding_superlarge));
        if (!getResources().getBoolean(R.bool.is_landscape)) {
            setAreHeadersSticky(true);
        }
        showContentHeader(R.drawable.collection_header);     */
    }
}
