Refactoring Types: ['Extract Method']
ations/crypto/axolotl/AxolotlService.java
package eu.siacs.conversations.crypto.axolotl;

import android.support.annotation.NonNull;
import android.support.annotation.Nullable;
import android.util.Base64;
import android.util.Log;

import org.whispersystems.libaxolotl.AxolotlAddress;
import org.whispersystems.libaxolotl.DuplicateMessageException;
import org.whispersystems.libaxolotl.IdentityKey;
import org.whispersystems.libaxolotl.IdentityKeyPair;
import org.whispersystems.libaxolotl.InvalidKeyException;
import org.whispersystems.libaxolotl.InvalidKeyIdException;
import org.whispersystems.libaxolotl.InvalidMessageException;
import org.whispersystems.libaxolotl.InvalidVersionException;
import org.whispersystems.libaxolotl.LegacyMessageException;
import org.whispersystems.libaxolotl.NoSessionException;
import org.whispersystems.libaxolotl.SessionBuilder;
import org.whispersystems.libaxolotl.SessionCipher;
import org.whispersystems.libaxolotl.UntrustedIdentityException;
import org.whispersystems.libaxolotl.ecc.Curve;
import org.whispersystems.libaxolotl.ecc.ECKeyPair;
import org.whispersystems.libaxolotl.ecc.ECPublicKey;
import org.whispersystems.libaxolotl.protocol.CiphertextMessage;
import org.whispersystems.libaxolotl.protocol.PreKeyWhisperMessage;
import org.whispersystems.libaxolotl.protocol.WhisperMessage;
import org.whispersystems.libaxolotl.state.AxolotlStore;
import org.whispersystems.libaxolotl.state.PreKeyBundle;
import org.whispersystems.libaxolotl.state.PreKeyRecord;
import org.whispersystems.libaxolotl.state.SessionRecord;
import org.whispersystems.libaxolotl.state.SignedPreKeyRecord;
import org.whispersystems.libaxolotl.util.KeyHelper;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;

import eu.siacs.conversations.Config;
import eu.siacs.conversations.entities.Account;
import eu.siacs.conversations.entities.Contact;
import eu.siacs.conversations.entities.Conversation;
import eu.siacs.conversations.entities.Message;
import eu.siacs.conversations.parser.IqParser;
import eu.siacs.conversations.services.XmppConnectionService;
import eu.siacs.conversations.utils.SerialSingleThreadExecutor;
import eu.siacs.conversations.xml.Element;
import eu.siacs.conversations.xmpp.OnIqPacketReceived;
import eu.siacs.conversations.xmpp.jid.InvalidJidException;
import eu.siacs.conversations.xmpp.jid.Jid;
import eu.siacs.conversations.xmpp.stanzas.IqPacket;
import eu.siacs.conversations.xmpp.stanzas.MessagePacket;

public class AxolotlService {

	public static final String PEP_PREFIX = "eu.siacs.conversations.axolotl";
	public static final String PEP_DEVICE_LIST = PEP_PREFIX + ".devicelist";
	public static final String PEP_BUNDLES = PEP_PREFIX + ".bundles";

	public static final String LOGPREFIX = "AxolotlService";

	public static final int NUM_KEYS_TO_PUBLISH = 10;

	private final Account account;
	private final XmppConnectionService mXmppConnectionService;
	private final SQLiteAxolotlStore axolotlStore;
	private final SessionMap sessions;
	private final Map<Jid, Set<Integer>> deviceIds;
	private final Map<String, MessagePacket> messageCache;
	private final FetchStatusMap fetchStatusMap;
	private final SerialSingleThreadExecutor executor;
	private int ownDeviceId;

	public static class SQLiteAxolotlStore implements AxolotlStore {

		public static final String PREKEY_TABLENAME = "prekeys";
		public static final String SIGNED_PREKEY_TABLENAME = "signed_prekeys";
		public static final String SESSION_TABLENAME = "sessions";
		public static final String IDENTITIES_TABLENAME = "identities";
		public static final String ACCOUNT = "account";
		public static final String DEVICE_ID = "device_id";
		public static final String ID = "id";
		public static final String KEY = "key";
		public static final String NAME = "name";
		public static final String TRUSTED = "trusted";
		public static final String OWN = "ownkey";

		public static final String JSONKEY_REGISTRATION_ID = "axolotl_reg_id";
		public static final String JSONKEY_CURRENT_PREKEY_ID = "axolotl_cur_prekey_id";

		private final Account account;
		private final XmppConnectionService mXmppConnectionService;

		private IdentityKeyPair identityKeyPair;
		private final int localRegistrationId;
		private int currentPreKeyId = 0;


		private static IdentityKeyPair generateIdentityKeyPair() {
			Log.i(Config.LOGTAG, AxolotlService.LOGPREFIX+" : "+"Generating axolotl IdentityKeyPair...");
			ECKeyPair identityKeyPairKeys = Curve.generateKeyPair();
			IdentityKeyPair ownKey = new IdentityKeyPair(new IdentityKey(identityKeyPairKeys.getPublicKey()),
					identityKeyPairKeys.getPrivateKey());
			return ownKey;
		}

		private static int generateRegistrationId() {
			Log.i(Config.LOGTAG, AxolotlService.LOGPREFIX+" : "+"Generating axolotl registration ID...");
			int reg_id = KeyHelper.generateRegistrationId(true);
			return reg_id;
		}

		public SQLiteAxolotlStore(Account account, XmppConnectionService service) {
			this.account = account;
			this.mXmppConnectionService = service;
			this.localRegistrationId = loadRegistrationId();
			this.currentPreKeyId = loadCurrentPreKeyId();
			for (SignedPreKeyRecord record : loadSignedPreKeys()) {
				Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Got Axolotl signed prekey record:" + record.getId());
			}
		}

		public int getCurrentPreKeyId() {
			return currentPreKeyId;
		}

		// --------------------------------------
		// IdentityKeyStore
		// --------------------------------------

		private IdentityKeyPair loadIdentityKeyPair() {
			String ownName = account.getJid().toBareJid().toString();
			IdentityKeyPair ownKey = mXmppConnectionService.databaseBackend.loadOwnIdentityKeyPair(account,
					ownName);

			if (ownKey != null) {
				return ownKey;
			} else {
				Log.i(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Could not retrieve axolotl key for account " + ownName);
				ownKey = generateIdentityKeyPair();
				mXmppConnectionService.databaseBackend.storeOwnIdentityKeyPair(account, ownName, ownKey);
			}
			return ownKey;
		}

		private int loadRegistrationId() {
			String regIdString = this.account.getKey(JSONKEY_REGISTRATION_ID);
			int reg_id;
			if (regIdString != null) {
				reg_id = Integer.valueOf(regIdString);
			} else {
				Log.i(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Could not retrieve axolotl registration id for account " + account.getJid());
				reg_id = generateRegistrationId();
				boolean success = this.account.setKey(JSONKEY_REGISTRATION_ID, Integer.toString(reg_id));
				if (success) {
					mXmppConnectionService.databaseBackend.updateAccount(account);
				} else {
					Log.e(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Failed to write new key to the database!");
				}
			}
			return reg_id;
		}

		private int loadCurrentPreKeyId() {
			String regIdString = this.account.getKey(JSONKEY_CURRENT_PREKEY_ID);
			int reg_id;
			if (regIdString != null) {
				reg_id = Integer.valueOf(regIdString);
			} else {
				Log.w(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Could not retrieve current prekey id for account " + account.getJid());
				reg_id = 0;
			}
			return reg_id;
		}

		public void regenerate() {
			mXmppConnectionService.databaseBackend.wipeAxolotlDb(account);
			account.setKey(JSONKEY_CURRENT_PREKEY_ID, Integer.toString(0));
			identityKeyPair = loadIdentityKeyPair();
			currentPreKeyId = 0;
			mXmppConnectionService.updateAccountUi();
		}

		/**
		 * Get the local client's identity key pair.
		 *
		 * @return The local client's persistent identity key pair.
		 */
		@Override
		public IdentityKeyPair getIdentityKeyPair() {
			if(identityKeyPair == null) {
				identityKeyPair = loadIdentityKeyPair();
			}
			return identityKeyPair;
		}

		/**
		 * Return the local client's registration ID.
		 * <p/>
		 * Clients should maintain a registration ID, a random number
		 * between 1 and 16380 that's generated once at install time.
		 *
		 * @return the local client's registration ID.
		 */
		@Override
		public int getLocalRegistrationId() {
			return localRegistrationId;
		}

		/**
		 * Save a remote client's identity key
		 * <p/>
		 * Store a remote client's identity key as trusted.
		 *
		 * @param name        The name of the remote client.
		 * @param identityKey The remote client's identity key.
		 */
		@Override
		public void saveIdentity(String name, IdentityKey identityKey) {
			if(!mXmppConnectionService.databaseBackend.loadIdentityKeys(account, name).contains(identityKey)) {
				mXmppConnectionService.databaseBackend.storeIdentityKey(account, name, identityKey);
			}
		}

		/**
		 * Verify a remote client's identity key.
		 * <p/>
		 * Determine whether a remote client's identity is trusted.  Convention is
		 * that the TextSecure protocol is 'trust on first use.'  This means that
		 * an identity key is considered 'trusted' if there is no entry for the recipient
		 * in the local store, or if it matches the saved key for a recipient in the local
		 * store.  Only if it mismatches an entry in the local store is it considered
		 * 'untrusted.'
		 *
		 * @param name        The name of the remote client.
		 * @param identityKey The identity key to verify.
		 * @return true if trusted, false if untrusted.
		 */
		@Override
		public boolean isTrustedIdentity(String name, IdentityKey identityKey) {
			//Set<IdentityKey> trustedKeys = mXmppConnectionService.databaseBackend.loadIdentityKeys(account, name);
			//return trustedKeys.isEmpty() || trustedKeys.contains(identityKey);
			return true;
		}

		// --------------------------------------
		// SessionStore
		// --------------------------------------

		/**
		 * Returns a copy of the {@link SessionRecord} corresponding to the recipientId + deviceId tuple,
		 * or a new SessionRecord if one does not currently exist.
		 * <p/>
		 * It is important that implementations return a copy of the current durable information.  The
		 * returned SessionRecord may be modified, but those changes should not have an effect on the
		 * durable session state (what is returned by subsequent calls to this method) without the
		 * store method being called here first.
		 *
		 * @param address The name and device ID of the remote client.
		 * @return a copy of the SessionRecord corresponding to the recipientId + deviceId tuple, or
		 * a new SessionRecord if one does not currently exist.
		 */
		@Override
		public SessionRecord loadSession(AxolotlAddress address) {
			SessionRecord session = mXmppConnectionService.databaseBackend.loadSession(this.account, address);
			return (session != null) ? session : new SessionRecord();
		}

		/**
		 * Returns all known devices with active sessions for a recipient
		 *
		 * @param name the name of the client.
		 * @return all known sub-devices with active sessions.
		 */
		@Override
		public List<Integer> getSubDeviceSessions(String name) {
			return mXmppConnectionService.databaseBackend.getSubDeviceSessions(account,
					new AxolotlAddress(name, 0));
		}

		/**
		 * Commit to storage the {@link SessionRecord} for a given recipientId + deviceId tuple.
		 *
		 * @param address the address of the remote client.
		 * @param record  the current SessionRecord for the remote client.
		 */
		@Override
		public void storeSession(AxolotlAddress address, SessionRecord record) {
			mXmppConnectionService.databaseBackend.storeSession(account, address, record);
		}

		/**
		 * Determine whether there is a committed {@link SessionRecord} for a recipientId + deviceId tuple.
		 *
		 * @param address the address of the remote client.
		 * @return true if a {@link SessionRecord} exists, false otherwise.
		 */
		@Override
		public boolean containsSession(AxolotlAddress address) {
			return mXmppConnectionService.databaseBackend.containsSession(account, address);
		}

		/**
		 * Remove a {@link SessionRecord} for a recipientId + deviceId tuple.
		 *
		 * @param address the address of the remote client.
		 */
		@Override
		public void deleteSession(AxolotlAddress address) {
			mXmppConnectionService.databaseBackend.deleteSession(account, address);
		}

		/**
		 * Remove the {@link SessionRecord}s corresponding to all devices of a recipientId.
		 *
		 * @param name the name of the remote client.
		 */
		@Override
		public void deleteAllSessions(String name) {
			mXmppConnectionService.databaseBackend.deleteAllSessions(account,
					new AxolotlAddress(name, 0));
		}

		public boolean isTrustedSession(AxolotlAddress address) {
			return mXmppConnectionService.databaseBackend.isTrustedSession(this.account, address);
		}

		public void setTrustedSession(AxolotlAddress address, boolean trusted) {
			mXmppConnectionService.databaseBackend.setTrustedSession(this.account, address, trusted);
		}

		// --------------------------------------
		// PreKeyStore
		// --------------------------------------

		/**
		 * Load a local PreKeyRecord.
		 *
		 * @param preKeyId the ID of the local PreKeyRecord.
		 * @return the corresponding PreKeyRecord.
		 * @throws InvalidKeyIdException when there is no corresponding PreKeyRecord.
		 */
		@Override
		public PreKeyRecord loadPreKey(int preKeyId) throws InvalidKeyIdException {
			PreKeyRecord record = mXmppConnectionService.databaseBackend.loadPreKey(account, preKeyId);
			if (record == null) {
				throw new InvalidKeyIdException("No such PreKeyRecord: " + preKeyId);
			}
			return record;
		}

		/**
		 * Store a local PreKeyRecord.
		 *
		 * @param preKeyId the ID of the PreKeyRecord to store.
		 * @param record   the PreKeyRecord.
		 */
		@Override
		public void storePreKey(int preKeyId, PreKeyRecord record) {
			mXmppConnectionService.databaseBackend.storePreKey(account, record);
			currentPreKeyId = preKeyId;
			boolean success = this.account.setKey(JSONKEY_CURRENT_PREKEY_ID, Integer.toString(preKeyId));
			if (success) {
				mXmppConnectionService.databaseBackend.updateAccount(account);
			} else {
				Log.e(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Failed to write new prekey id to the database!");
			}
		}

		/**
		 * @param preKeyId A PreKeyRecord ID.
		 * @return true if the store has a record for the preKeyId, otherwise false.
		 */
		@Override
		public boolean containsPreKey(int preKeyId) {
			return mXmppConnectionService.databaseBackend.containsPreKey(account, preKeyId);
		}

		/**
		 * Delete a PreKeyRecord from local storage.
		 *
		 * @param preKeyId The ID of the PreKeyRecord to remove.
		 */
		@Override
		public void removePreKey(int preKeyId) {
			mXmppConnectionService.databaseBackend.deletePreKey(account, preKeyId);
		}

		// --------------------------------------
		// SignedPreKeyStore
		// --------------------------------------

		/**
		 * Load a local SignedPreKeyRecord.
		 *
		 * @param signedPreKeyId the ID of the local SignedPreKeyRecord.
		 * @return the corresponding SignedPreKeyRecord.
		 * @throws InvalidKeyIdException when there is no corresponding SignedPreKeyRecord.
		 */
		@Override
		public SignedPreKeyRecord loadSignedPreKey(int signedPreKeyId) throws InvalidKeyIdException {
			SignedPreKeyRecord record = mXmppConnectionService.databaseBackend.loadSignedPreKey(account, signedPreKeyId);
			if (record == null) {
				throw new InvalidKeyIdException("No such SignedPreKeyRecord: " + signedPreKeyId);
			}
			return record;
		}

		/**
		 * Load all local SignedPreKeyRecords.
		 *
		 * @return All stored SignedPreKeyRecords.
		 */
		@Override
		public List<SignedPreKeyRecord> loadSignedPreKeys() {
			return mXmppConnectionService.databaseBackend.loadSignedPreKeys(account);
		}

		/**
		 * Store a local SignedPreKeyRecord.
		 *
		 * @param signedPreKeyId the ID of the SignedPreKeyRecord to store.
		 * @param record         the SignedPreKeyRecord.
		 */
		@Override
		public void storeSignedPreKey(int signedPreKeyId, SignedPreKeyRecord record) {
			mXmppConnectionService.databaseBackend.storeSignedPreKey(account, record);
		}

		/**
		 * @param signedPreKeyId A SignedPreKeyRecord ID.
		 * @return true if the store has a record for the signedPreKeyId, otherwise false.
		 */
		@Override
		public boolean containsSignedPreKey(int signedPreKeyId) {
			return mXmppConnectionService.databaseBackend.containsSignedPreKey(account, signedPreKeyId);
		}

		/**
		 * Delete a SignedPreKeyRecord from local storage.
		 *
		 * @param signedPreKeyId The ID of the SignedPreKeyRecord to remove.
		 */
		@Override
		public void removeSignedPreKey(int signedPreKeyId) {
			mXmppConnectionService.databaseBackend.deleteSignedPreKey(account, signedPreKeyId);
		}
	}

	public static class XmppAxolotlSession {
		private final SessionCipher cipher;
		private boolean isTrusted = false;
		private Integer preKeyId = null;
		private final SQLiteAxolotlStore sqLiteAxolotlStore;
		private final AxolotlAddress remoteAddress;
		private final Account account;

		public XmppAxolotlSession(Account account, SQLiteAxolotlStore store, AxolotlAddress remoteAddress) {
			this.cipher = new SessionCipher(store, remoteAddress);
			this.remoteAddress = remoteAddress;
			this.sqLiteAxolotlStore = store;
			this.account = account;
			this.isTrusted = sqLiteAxolotlStore.isTrustedSession(remoteAddress);
		}

		public void trust() {
			sqLiteAxolotlStore.setTrustedSession(remoteAddress, true);
			this.isTrusted = true;
		}

		public boolean isTrusted() {
			return this.isTrusted;
		}

		public Integer getPreKeyId() {
			return preKeyId;
		}

		public void resetPreKeyId() {
			preKeyId = null;
		}

		public byte[] processReceiving(XmppAxolotlMessage.XmppAxolotlMessageHeader incomingHeader) {
			byte[] plaintext = null;
			try {
				try {
					PreKeyWhisperMessage message = new PreKeyWhisperMessage(incomingHeader.getContents());
					Log.i(Config.LOGTAG, AxolotlService.getLogprefix(account)+"PreKeyWhisperMessage received, new session ID:" + message.getSignedPreKeyId() + "/" + message.getPreKeyId());
					plaintext = cipher.decrypt(message);
					if (message.getPreKeyId().isPresent()) {
						preKeyId = message.getPreKeyId().get();
					}
				} catch (InvalidMessageException | InvalidVersionException e) {
					Log.i(Config.LOGTAG, AxolotlService.getLogprefix(account)+"WhisperMessage received");
					WhisperMessage message = new WhisperMessage(incomingHeader.getContents());
					plaintext = cipher.decrypt(message);
				} catch (InvalidKeyException | InvalidKeyIdException | UntrustedIdentityException e) {
					Log.w(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Error decrypting axolotl header, "+e.getClass().getName()+": " + e.getMessage());
				}
			} catch (LegacyMessageException | InvalidMessageException | DuplicateMessageException | NoSessionException  e) {
				Log.w(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Error decrypting axolotl header, "+e.getClass().getName()+": " + e.getMessage());
			}
			return plaintext;
		}

		public XmppAxolotlMessage.XmppAxolotlMessageHeader processSending(byte[] outgoingMessage) {
			CiphertextMessage ciphertextMessage = cipher.encrypt(outgoingMessage);
			XmppAxolotlMessage.XmppAxolotlMessageHeader header =
					new XmppAxolotlMessage.XmppAxolotlMessageHeader(remoteAddress.getDeviceId(),
							ciphertextMessage.serialize());
			return header;
		}
	}

	private static class AxolotlAddressMap<T> {
		protected Map<String, Map<Integer, T>> map;
		protected final Object MAP_LOCK = new Object();

		public AxolotlAddressMap() {
			this.map = new HashMap<>();
		}

		public void put(AxolotlAddress address, T value) {
			synchronized (MAP_LOCK) {
				Map<Integer, T> devices = map.get(address.getName());
				if (devices == null) {
					devices = new HashMap<>();
					map.put(address.getName(), devices);
				}
				devices.put(address.getDeviceId(), value);
			}
		}

		public T get(AxolotlAddress address) {
			synchronized (MAP_LOCK) {
				Map<Integer, T> devices = map.get(address.getName());
				if (devices == null) {
					return null;
				}
				return devices.get(address.getDeviceId());
			}
		}

		public Map<Integer, T> getAll(AxolotlAddress address) {
			synchronized (MAP_LOCK) {
				Map<Integer, T> devices = map.get(address.getName());
				if (devices == null) {
					return new HashMap<>();
				}
				return devices;
			}
		}

		public boolean hasAny(AxolotlAddress address) {
			synchronized (MAP_LOCK) {
				Map<Integer, T> devices = map.get(address.getName());
				return devices != null && !devices.isEmpty();
			}
		}


	}

	private static class SessionMap extends AxolotlAddressMap<XmppAxolotlSession> {

		public SessionMap(SQLiteAxolotlStore store, Account account) {
			super();
			this.fillMap(store, account);
		}

		private void fillMap(SQLiteAxolotlStore store, Account account) {
			for (Contact contact : account.getRoster().getContacts()) {
				Jid bareJid = contact.getJid().toBareJid();
				if (bareJid == null) {
					continue; // FIXME: handle this?
				}
				String address = bareJid.toString();
				List<Integer> deviceIDs = store.getSubDeviceSessions(address);
				for (Integer deviceId : deviceIDs) {
					AxolotlAddress axolotlAddress = new AxolotlAddress(address, deviceId);
					this.put(axolotlAddress, new XmppAxolotlSession(account, store, axolotlAddress));
				}
			}
		}

	}

	private static enum FetchStatus {
		PENDING,
		SUCCESS,
		ERROR
	}

	private static class FetchStatusMap extends AxolotlAddressMap<FetchStatus> {

	}
	
	public static String getLogprefix(Account account) {
		return LOGPREFIX+" ("+account.getJid().toBareJid().toString()+"): ";
	}

	public AxolotlService(Account account, XmppConnectionService connectionService) {
		this.mXmppConnectionService = connectionService;
		this.account = account;
		this.axolotlStore = new SQLiteAxolotlStore(this.account, this.mXmppConnectionService);
		this.deviceIds = new HashMap<>();
		this.messageCache = new HashMap<>();
		this.sessions = new SessionMap(axolotlStore, account);
		this.fetchStatusMap = new FetchStatusMap();
		this.executor = new SerialSingleThreadExecutor();
		this.ownDeviceId = axolotlStore.getLocalRegistrationId();
	}

	public IdentityKey getOwnPublicKey() {
		return axolotlStore.getIdentityKeyPair().getPublicKey();
	}

	public void trustSession(AxolotlAddress counterpart) {
		XmppAxolotlSession session = sessions.get(counterpart);
		if (session != null) {
			session.trust();
		}
	}

	public boolean isTrustedSession(AxolotlAddress counterpart) {
		XmppAxolotlSession session = sessions.get(counterpart);
		return session != null && session.isTrusted();
	}

	private AxolotlAddress getAddressForJid(Jid jid) {
		return new AxolotlAddress(jid.toString(), 0);
	}

	private Set<XmppAxolotlSession> findOwnSessions() {
		AxolotlAddress ownAddress = getAddressForJid(account.getJid().toBareJid());
		Set<XmppAxolotlSession> ownDeviceSessions = new HashSet<>(this.sessions.getAll(ownAddress).values());
		return ownDeviceSessions;
	}

	private Set<XmppAxolotlSession> findSessionsforContact(Contact contact) {
		AxolotlAddress contactAddress = getAddressForJid(contact.getJid());
		Set<XmppAxolotlSession> sessions = new HashSet<>(this.sessions.getAll(contactAddress).values());
		return sessions;
	}

	private boolean hasAny(Contact contact) {
		AxolotlAddress contactAddress = getAddressForJid(contact.getJid());
		return sessions.hasAny(contactAddress);
	}

	public void regenerateKeys() {
		axolotlStore.regenerate();
		publishBundlesIfNeeded();
	}

	public int getOwnDeviceId() {
		return ownDeviceId;
	}

	public Set<Integer> getOwnDeviceIds() {
		return this.deviceIds.get(account.getJid().toBareJid());
	}

	public void registerDevices(final Jid jid, @NonNull final Set<Integer> deviceIds) {
		if(deviceIds.contains(getOwnDeviceId())) {
			Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Skipping own Device ID:"+ jid + ":"+getOwnDeviceId());
			deviceIds.remove(getOwnDeviceId());
		}
		for(Integer i:deviceIds) {
			Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Adding Device ID:"+ jid + ":"+i);
		}
		this.deviceIds.put(jid, deviceIds);
		publishOwnDeviceIdIfNeeded();
	}

	public void wipeOtherPepDevices() {
		Set<Integer> deviceIds = new HashSet<>();
		deviceIds.add(getOwnDeviceId());
		IqPacket publish = mXmppConnectionService.getIqGenerator().publishDeviceIds(deviceIds);
		Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Wiping all other devices from Pep:" + publish);
		mXmppConnectionService.sendIqPacket(account, publish, new OnIqPacketReceived() {
			@Override
			public void onIqPacketReceived(Account account, IqPacket packet) {
				// TODO: implement this!
			}
		});
	}

	public void publishOwnDeviceIdIfNeeded() {
		IqPacket packet = mXmppConnectionService.getIqGenerator().retrieveDeviceIds(account.getJid().toBareJid());
		mXmppConnectionService.sendIqPacket(account, packet, new OnIqPacketReceived() {
			@Override
			public void onIqPacketReceived(Account account, IqPacket packet) {
				Element item = mXmppConnectionService.getIqParser().getItem(packet);
				Set<Integer> deviceIds = mXmppConnectionService.getIqParser().deviceIds(item);
				if (deviceIds == null) {
					deviceIds = new HashSet<Integer>();
				}
				if (!deviceIds.contains(getOwnDeviceId())) {
					deviceIds.add(getOwnDeviceId());
					IqPacket publish = mXmppConnectionService.getIqGenerator().publishDeviceIds(deviceIds);
					Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Own device " + getOwnDeviceId() + " not in PEP devicelist. Publishing: " + publish);
					mXmppConnectionService.sendIqPacket(account, publish, new OnIqPacketReceived() {
						@Override
						public void onIqPacketReceived(Account account, IqPacket packet) {
							// TODO: implement this!
						}
					});
				}
			}
		});
	}

	public void publishBundlesIfNeeded() {
		IqPacket packet = mXmppConnectionService.getIqGenerator().retrieveBundlesForDevice(account.getJid().toBareJid(), ownDeviceId);
		mXmppConnectionService.sendIqPacket(account, packet, new OnIqPacketReceived() {
			@Override
			public void onIqPacketReceived(Account account, IqPacket packet) {
				PreKeyBundle bundle = mXmppConnectionService.getIqParser().bundle(packet);
				Map<Integer, ECPublicKey> keys = mXmppConnectionService.getIqParser().preKeyPublics(packet);
				boolean flush = false;
				if (bundle == null) {
					Log.w(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Received invalid bundle:" + packet);
					bundle = new PreKeyBundle(-1, -1, -1 , null, -1, null, null, null);
					flush = true;
				}
				if (keys == null) {
					Log.w(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Received invalid prekeys:" + packet);
				}
				try {
					boolean changed = false;
					// Validate IdentityKey
					IdentityKeyPair identityKeyPair = axolotlStore.getIdentityKeyPair();
					if (flush || !identityKeyPair.getPublicKey().equals(bundle.getIdentityKey())) {
						Log.i(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Adding own IdentityKey " + identityKeyPair.getPublicKey() + " to PEP.");
						changed = true;
					}

					// Validate signedPreKeyRecord + ID
					SignedPreKeyRecord signedPreKeyRecord;
					int numSignedPreKeys = axolotlStore.loadSignedPreKeys().size();
					try {
						signedPreKeyRecord = axolotlStore.loadSignedPreKey(bundle.getSignedPreKeyId());
						if ( flush
								||!bundle.getSignedPreKey().equals(signedPreKeyRecord.getKeyPair().getPublicKey())
								|| !Arrays.equals(bundle.getSignedPreKeySignature(), signedPreKeyRecord.getSignature())) {
							Log.i(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Adding new signedPreKey with ID " + (numSignedPreKeys + 1) + " to PEP.");
							signedPreKeyRecord = KeyHelper.generateSignedPreKey(identityKeyPair, numSignedPreKeys + 1);
							axolotlStore.storeSignedPreKey(signedPreKeyRecord.getId(), signedPreKeyRecord);
							changed = true;
						}
					} catch (InvalidKeyIdException e) {
						Log.i(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Adding new signedPreKey with ID " + (numSignedPreKeys + 1) + " to PEP.");
						signedPreKeyRecord = KeyHelper.generateSignedPreKey(identityKeyPair, numSignedPreKeys + 1);
						axolotlStore.storeSignedPreKey(signedPreKeyRecord.getId(), signedPreKeyRecord);
						changed = true;
					}

					// Validate PreKeys
					Set<PreKeyRecord> preKeyRecords = new HashSet<>();
					if (keys != null) {
						for (Integer id : keys.keySet()) {
							try {
								PreKeyRecord preKeyRecord = axolotlStore.loadPreKey(id);
								if (preKeyRecord.getKeyPair().getPublicKey().equals(keys.get(id))) {
									preKeyRecords.add(preKeyRecord);
								}
							} catch (InvalidKeyIdException ignored) {
							}
						}
					}
					int newKeys = NUM_KEYS_TO_PUBLISH - preKeyRecords.size();
					if (newKeys > 0) {
						List<PreKeyRecord> newRecords = KeyHelper.generatePreKeys(
								axolotlStore.getCurrentPreKeyId()+1, newKeys);
						preKeyRecords.addAll(newRecords);
						for (PreKeyRecord record : newRecords) {
							axolotlStore.storePreKey(record.getId(), record);
						}
						changed = true;
						Log.i(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Adding " + newKeys + " new preKeys to PEP.");
					}


					if(changed) {
						IqPacket publish = mXmppConnectionService.getIqGenerator().publishBundles(
								signedPreKeyRecord, axolotlStore.getIdentityKeyPair().getPublicKey(),
								preKeyRecords, ownDeviceId);
						Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+ ": Bundle " + getOwnDeviceId() + " in PEP not current. Publishing: " + publish);
						mXmppConnectionService.sendIqPacket(account, publish, new OnIqPacketReceived() {
							@Override
							public void onIqPacketReceived(Account account, IqPacket packet) {
								// TODO: implement this!
								Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Published bundle, got: " + packet);
							}
						});
					}
				} catch (InvalidKeyException e) {
						Log.e(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Failed to publish bundle " + getOwnDeviceId() + ", reason: " + e.getMessage());
						return;
				}
			}
		});
	}

	public boolean isContactAxolotlCapable(Contact contact) {
		Jid jid = contact.getJid().toBareJid();
		AxolotlAddress address = new AxolotlAddress(jid.toString(), 0);
		return sessions.hasAny(address) ||
				( deviceIds.containsKey(jid) && !deviceIds.get(jid).isEmpty());
	}

	private void buildSessionFromPEP(final Conversation conversation, final AxolotlAddress address) {
		Log.i(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Building new sesstion for " + address.getDeviceId());

		try {
			IqPacket bundlesPacket = mXmppConnectionService.getIqGenerator().retrieveBundlesForDevice(
					Jid.fromString(address.getName()), address.getDeviceId());
			Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Retrieving bundle: " + bundlesPacket);
			mXmppConnectionService.sendIqPacket(account, bundlesPacket, new OnIqPacketReceived() {
				@Override
				public void onIqPacketReceived(Account account, IqPacket packet) {
					Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Received preKey IQ packet, processing...");
					final IqParser parser = mXmppConnectionService.getIqParser();
					final List<PreKeyBundle> preKeyBundleList = parser.preKeys(packet);
					final PreKeyBundle bundle = parser.bundle(packet);
					if (preKeyBundleList.isEmpty() || bundle == null) {
						Log.e(Config.LOGTAG, AxolotlService.getLogprefix(account)+"preKey IQ packet invalid: " + packet);
						fetchStatusMap.put(address, FetchStatus.ERROR);
						return;
					}
					Random random = new Random();
					final PreKeyBundle preKey = preKeyBundleList.get(random.nextInt(preKeyBundleList.size()));
					if (preKey == null) {
						//should never happen
						fetchStatusMap.put(address, FetchStatus.ERROR);
						return;
					}

					final PreKeyBundle preKeyBundle = new PreKeyBundle(0, address.getDeviceId(),
							preKey.getPreKeyId(), preKey.getPreKey(),
							bundle.getSignedPreKeyId(), bundle.getSignedPreKey(),
							bundle.getSignedPreKeySignature(), bundle.getIdentityKey());

					axolotlStore.saveIdentity(address.getName(), bundle.getIdentityKey());

					try {
						SessionBuilder builder = new SessionBuilder(axolotlStore, address);
						builder.process(preKeyBundle);
						XmppAxolotlSession session = new XmppAxolotlSession(account, axolotlStore, address);
						sessions.put(address, session);
						fetchStatusMap.put(address, FetchStatus.SUCCESS);
					} catch (UntrustedIdentityException|InvalidKeyException e) {
						Log.e(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Error building session for " + address + ": "
								+ e.getClass().getName() + ", " + e.getMessage());
						fetchStatusMap.put(address, FetchStatus.ERROR);
					}

					AxolotlAddress ownAddress = new AxolotlAddress(conversation.getAccount().getJid().toBareJid().toString(),0);
					AxolotlAddress foreignAddress = new AxolotlAddress(conversation.getJid().toBareJid().toString(),0);
					if (!fetchStatusMap.getAll(ownAddress).containsValue(FetchStatus.PENDING)
							&& !fetchStatusMap.getAll(foreignAddress).containsValue(FetchStatus.PENDING)) {
						conversation.findUnsentMessagesWithEncryption(Message.ENCRYPTION_AXOLOTL,
								new Conversation.OnMessageFound() {
									@Override
									public void onMessageFound(Message message) {
										processSending(message);
									}
								});
					}
				}
			});
		} catch (InvalidJidException e) {
			Log.e(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Got address with invalid jid: " + address.getName());
		}
	}

	private boolean createSessionsIfNeeded(Conversation conversation) {
		boolean newSessions = false;
		Log.i(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Creating axolotl sessions if needed...");
		Jid contactJid = conversation.getContact().getJid().toBareJid();
		Set<AxolotlAddress> addresses = new HashSet<>();
		if(deviceIds.get(contactJid) != null) {
			for(Integer foreignId:this.deviceIds.get(contactJid)) {
				Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Found device "+account.getJid().toBareJid()+":"+foreignId);
				addresses.add(new AxolotlAddress(contactJid.toString(), foreignId));
			}
		} else {
			Log.w(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Have no target devices in PEP!");
		}
		Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Checking own account "+account.getJid().toBareJid());
		if(deviceIds.get(account.getJid().toBareJid()) != null) {
			for(Integer ownId:this.deviceIds.get(account.getJid().toBareJid())) {
				Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Found device "+account.getJid().toBareJid()+":"+ownId);
				addresses.add(new AxolotlAddress(account.getJid().toBareJid().toString(), ownId));
			}
		}
		for (AxolotlAddress address : addresses) {
			Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Processing device: " + address.toString());
			FetchStatus status = fetchStatusMap.get(address);
			XmppAxolotlSession session = sessions.get(address);
			if ( session == null && ( status == null || status == FetchStatus.ERROR) ) {
				fetchStatusMap.put(address, FetchStatus.PENDING);
				this.buildSessionFromPEP(conversation,  address);
				newSessions = true;
			} else {
				Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Already have session for " +  address.toString());
			}
		}
		return newSessions;
	}

	@Nullable
	public XmppAxolotlMessage encrypt(Message message ){
		final XmppAxolotlMessage axolotlMessage = new XmppAxolotlMessage(message.getContact().getJid().toBareJid(),
				ownDeviceId, message.getBody());

		if(findSessionsforContact(message.getContact()).isEmpty()) {
			return null;
		}
		Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Building axolotl foreign headers...");
		for (XmppAxolotlSession session : findSessionsforContact(message.getContact())) {
			Log.v(Config.LOGTAG, AxolotlService.getLogprefix(account)+session.remoteAddress.toString());
			//if(!session.isTrusted()) {
			// TODO: handle this properly
			//              continue;
			//        }
			axolotlMessage.addHeader(session.processSending(axolotlMessage.getInnerKey()));
		}
		Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Building axolotl own headers...");
		for (XmppAxolotlSession session : findOwnSessions()) {
			Log.v(Config.LOGTAG, AxolotlService.getLogprefix(account)+session.remoteAddress.toString());
			//        if(!session.isTrusted()) {
			// TODO: handle this properly
			//          continue;
			//    }
			axolotlMessage.addHeader(session.processSending(axolotlMessage.getInnerKey()));
		}

		return axolotlMessage;
	}

	private void processSending(final Message message) {
		executor.execute(new Runnable() {
			@Override
			public void run() {
				MessagePacket packet = mXmppConnectionService.getMessageGenerator()
						.generateAxolotlChat(message);
				if (packet == null) {
					mXmppConnectionService.markMessage(message, Message.STATUS_SEND_FAILED);
					//mXmppConnectionService.updateConversationUi();
				} else {
					Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Generated message, caching: " + message.getUuid());
					messageCache.put(message.getUuid(), packet);
					mXmppConnectionService.resendMessage(message);
				}
			}
		});
	}

	public void prepareMessage(Message message) {
		if (!messageCache.containsKey(message.getUuid())) {
			boolean newSessions = createSessionsIfNeeded(message.getConversation());

			if (!newSessions) {
				this.processSending(message);
			}
		}
	}

	public MessagePacket fetchPacketFromCache(Message message) {
		MessagePacket packet = messageCache.get(message.getUuid());
		if (packet != null) {
			Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Cache hit: " + message.getUuid());
			messageCache.remove(message.getUuid());
		} else {
			Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Cache miss: " + message.getUuid());
		}
		return packet;
	}

	public XmppAxolotlMessage.XmppAxolotlPlaintextMessage processReceiving(XmppAxolotlMessage message) {
		XmppAxolotlMessage.XmppAxolotlPlaintextMessage plaintextMessage = null;
		AxolotlAddress senderAddress = new AxolotlAddress(message.getFrom().toString(),
				message.getSenderDeviceId());

		boolean newSession = false;
		XmppAxolotlSession session = sessions.get(senderAddress);
		if (session == null) {
			Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Account: "+account.getJid()+" No axolotl session found while parsing received message " + message);
			// TODO: handle this properly
			session = new XmppAxolotlSession(account, axolotlStore, senderAddress);
			newSession = true;
		}

		for (XmppAxolotlMessage.XmppAxolotlMessageHeader header : message.getHeaders()) {
			if (header.getRecipientDeviceId() == ownDeviceId) {
				Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Found axolotl header matching own device ID, processing...");
				byte[] payloadKey = session.processReceiving(header);
				if (payloadKey != null) {
					Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Got payload key from axolotl header. Decrypting message...");
					plaintextMessage = message.decrypt(session, payloadKey);
				}
				Integer preKeyId = session.getPreKeyId();
				if (preKeyId != null) {
					publishBundlesIfNeeded();
					session.resetPreKeyId();
				}
				break;
			}
		}

		if (newSession && plaintextMessage != null) {
			sessions.put(senderAddress,session);
		}

		return plaintextMessage;
	}
}


File: src/main/java/eu/siacs/conversations/crypto/axolotl/XmppAxolotlMessage.java
package eu.siacs.conversations.crypto.axolotl;

import android.util.Base64;

import java.security.InvalidAlgorithmParameterException;
import java.security.NoSuchAlgorithmException;
import java.security.InvalidKeyException;
import java.util.HashSet;
import java.util.Set;

import javax.crypto.BadPaddingException;
import javax.crypto.Cipher;
import javax.crypto.IllegalBlockSizeException;
import javax.crypto.KeyGenerator;
import javax.crypto.NoSuchPaddingException;
import javax.crypto.SecretKey;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

import eu.siacs.conversations.entities.Contact;
import eu.siacs.conversations.xml.Element;
import eu.siacs.conversations.xmpp.jid.Jid;

public class XmppAxolotlMessage {
	private byte[] innerKey;
	private byte[] ciphertext;
	private byte[] iv;
	private final Set<XmppAxolotlMessageHeader> headers;
	private final Jid from;
	private final int sourceDeviceId;

	public static class XmppAxolotlMessageHeader {
		private final int recipientDeviceId;
		private final byte[] content;

		public XmppAxolotlMessageHeader(int deviceId, byte[] content) {
			this.recipientDeviceId = deviceId;
			this.content = content;
		}

		public XmppAxolotlMessageHeader(Element header) {
			if("header".equals(header.getName())) {
				this.recipientDeviceId = Integer.parseInt(header.getAttribute("rid"));
				this.content = Base64.decode(header.getContent(),Base64.DEFAULT);
			} else {
				throw new IllegalArgumentException("Argument not a <header> Element!");
			}
		}

		public int getRecipientDeviceId() {
			return recipientDeviceId;
		}

		public byte[] getContents() {
			return content;
		}

		public Element toXml() {
			Element headerElement = new Element("header");
			// TODO: generate XML
			headerElement.setAttribute("rid", getRecipientDeviceId());
			headerElement.setContent(Base64.encodeToString(getContents(), Base64.DEFAULT));
			return headerElement;
		}
	}

	public static class XmppAxolotlPlaintextMessage {
		private final AxolotlService.XmppAxolotlSession session;
		private final String plaintext;

		public XmppAxolotlPlaintextMessage(AxolotlService.XmppAxolotlSession session, String plaintext) {
			this.session = session;
			this.plaintext = plaintext;
		}

		public String getPlaintext() {
			return plaintext;
		}

		public AxolotlService.XmppAxolotlSession getSession() {
			return session;
		}

	}

	public XmppAxolotlMessage(Jid from, Element axolotlMessage) {
		this.from = from;
		this.sourceDeviceId = Integer.parseInt(axolotlMessage.getAttribute("id"));
		this.headers = new HashSet<>();
		for(Element child:axolotlMessage.getChildren()) {
			switch(child.getName()) {
				case "header":
					headers.add(new XmppAxolotlMessageHeader(child));
					break;
				case "message":
					iv = Base64.decode(child.getAttribute("iv"),Base64.DEFAULT);
					ciphertext = Base64.decode(child.getContent(),Base64.DEFAULT);
					break;
				default:
					break;
			}
		}
	}

	public XmppAxolotlMessage(Jid from, int sourceDeviceId, String plaintext) {
		this.from = from;
		this.sourceDeviceId = sourceDeviceId;
		this.headers = new HashSet<>();
		this.encrypt(plaintext);
	}

	private void encrypt(String plaintext) {
		try {
			KeyGenerator generator = KeyGenerator.getInstance("AES");
			generator.init(128);
			SecretKey secretKey = generator.generateKey();
			Cipher cipher = Cipher.getInstance("AES/CTR/NoPadding");
			cipher.init(Cipher.ENCRYPT_MODE, secretKey);
			this.innerKey = secretKey.getEncoded();
			this.iv = cipher.getIV();
			this.ciphertext = cipher.doFinal(plaintext.getBytes());
		} catch (NoSuchAlgorithmException | NoSuchPaddingException | InvalidKeyException
				| IllegalBlockSizeException | BadPaddingException e) {

		}
	}

	public Jid getFrom() {
		return this.from;
	}

	public int getSenderDeviceId() {
		return sourceDeviceId;
	}

	public byte[] getCiphertext() {
		return ciphertext;
	}

	public Set<XmppAxolotlMessageHeader> getHeaders() {
		return headers;
	}

	public void addHeader(XmppAxolotlMessageHeader header) {
		headers.add(header);
	}

	public byte[] getInnerKey(){
		return innerKey;
	}

	public byte[] getIV() {
		return this.iv;
	}

	public Element toXml() {
		// TODO: generate outer XML, add in header XML
		Element message= new Element("axolotl_message", AxolotlService.PEP_PREFIX);
		message.setAttribute("id", sourceDeviceId);
		for(XmppAxolotlMessageHeader header: headers) {
			message.addChild(header.toXml());
		}
		Element payload = message.addChild("message");
		payload.setAttribute("iv",Base64.encodeToString(iv, Base64.DEFAULT));
		payload.setContent(Base64.encodeToString(ciphertext,Base64.DEFAULT));
		return message;
	}


	public XmppAxolotlPlaintextMessage decrypt(AxolotlService.XmppAxolotlSession session, byte[] key) {
		XmppAxolotlPlaintextMessage plaintextMessage = null;
		try {

			Cipher cipher = Cipher.getInstance("AES/CTR/NoPadding");
			SecretKeySpec keySpec = new SecretKeySpec(key, "AES");
			IvParameterSpec ivSpec = new IvParameterSpec(iv);

			cipher.init(Cipher.DECRYPT_MODE, keySpec, ivSpec);

			String plaintext = new String(cipher.doFinal(ciphertext));
			plaintextMessage = new XmppAxolotlPlaintextMessage(session, plaintext);

		} catch (NoSuchAlgorithmException | NoSuchPaddingException | InvalidKeyException
				| InvalidAlgorithmParameterException | IllegalBlockSizeException
				| BadPaddingException e) {
			throw new AssertionError(e);
		}
		return plaintextMessage;
	}
}


File: src/main/java/eu/siacs/conversations/entities/Message.java
package eu.siacs.conversations.entities;

import android.content.ContentValues;
import android.database.Cursor;

import java.net.MalformedURLException;
import java.net.URL;
import java.util.Arrays;

import eu.siacs.conversations.Config;
import eu.siacs.conversations.crypto.axolotl.AxolotlService;
import eu.siacs.conversations.utils.GeoHelper;
import eu.siacs.conversations.utils.MimeUtils;
import eu.siacs.conversations.utils.UIHelper;
import eu.siacs.conversations.xmpp.jid.InvalidJidException;
import eu.siacs.conversations.xmpp.jid.Jid;

public class Message extends AbstractEntity {

	public static final String TABLENAME = "messages";

	public static final String MERGE_SEPARATOR = " \u200B\n\n";

	public static final int STATUS_RECEIVED = 0;
	public static final int STATUS_UNSEND = 1;
	public static final int STATUS_SEND = 2;
	public static final int STATUS_SEND_FAILED = 3;
	public static final int STATUS_WAITING = 5;
	public static final int STATUS_OFFERED = 6;
	public static final int STATUS_SEND_RECEIVED = 7;
	public static final int STATUS_SEND_DISPLAYED = 8;

	public static final int ENCRYPTION_NONE = 0;
	public static final int ENCRYPTION_PGP = 1;
	public static final int ENCRYPTION_OTR = 2;
	public static final int ENCRYPTION_DECRYPTED = 3;
	public static final int ENCRYPTION_DECRYPTION_FAILED = 4;
	public static final int ENCRYPTION_AXOLOTL = 5;

	public static final int TYPE_TEXT = 0;
	public static final int TYPE_IMAGE = 1;
	public static final int TYPE_FILE = 2;
	public static final int TYPE_STATUS = 3;
	public static final int TYPE_PRIVATE = 4;

	public static final String CONVERSATION = "conversationUuid";
	public static final String COUNTERPART = "counterpart";
	public static final String TRUE_COUNTERPART = "trueCounterpart";
	public static final String BODY = "body";
	public static final String TIME_SENT = "timeSent";
	public static final String ENCRYPTION = "encryption";
	public static final String STATUS = "status";
	public static final String TYPE = "type";
	public static final String REMOTE_MSG_ID = "remoteMsgId";
	public static final String SERVER_MSG_ID = "serverMsgId";
	public static final String RELATIVE_FILE_PATH = "relativeFilePath";
	public static final String ME_COMMAND = "/me ";


	public boolean markable = false;
	protected String conversationUuid;
	protected Jid counterpart;
	protected Jid trueCounterpart;
	protected String body;
	protected String encryptedBody;
	protected long timeSent;
	protected int encryption;
	protected int status;
	protected int type;
	private AxolotlService.XmppAxolotlSession axolotlSession = null;
	protected String relativeFilePath;
	protected boolean read = true;
	protected String remoteMsgId = null;
	protected String serverMsgId = null;
	protected Conversation conversation = null;
	protected Downloadable downloadable = null;
	private Message mNextMessage = null;
	private Message mPreviousMessage = null;

	private Message() {

	}

	public Message(Conversation conversation, String body, int encryption) {
		this(conversation, body, encryption, STATUS_UNSEND);
	}

	public Message(Conversation conversation, String body, int encryption, int status) {
		this(java.util.UUID.randomUUID().toString(),
				conversation.getUuid(),
				conversation.getJid() == null ? null : conversation.getJid().toBareJid(),
				null,
				body,
				System.currentTimeMillis(),
				encryption,
				status,
				TYPE_TEXT,
				null,
				null,
				null);
		this.conversation = conversation;
	}

	private Message(final String uuid, final String conversationUUid, final Jid counterpart,
					final Jid trueCounterpart, final String body, final long timeSent,
					final int encryption, final int status, final int type, final String remoteMsgId,
					final String relativeFilePath, final String serverMsgId) {
		this.uuid = uuid;
		this.conversationUuid = conversationUUid;
		this.counterpart = counterpart;
		this.trueCounterpart = trueCounterpart;
		this.body = body;
		this.timeSent = timeSent;
		this.encryption = encryption;
		this.status = status;
		this.type = type;
		this.remoteMsgId = remoteMsgId;
		this.relativeFilePath = relativeFilePath;
		this.serverMsgId = serverMsgId;
	}

	public static Message fromCursor(Cursor cursor) {
		Jid jid;
		try {
			String value = cursor.getString(cursor.getColumnIndex(COUNTERPART));
			if (value != null) {
				jid = Jid.fromString(value, true);
			} else {
				jid = null;
			}
		} catch (InvalidJidException e) {
			jid = null;
		}
		Jid trueCounterpart;
		try {
			String value = cursor.getString(cursor.getColumnIndex(TRUE_COUNTERPART));
			if (value != null) {
				trueCounterpart = Jid.fromString(value, true);
			} else {
				trueCounterpart = null;
			}
		} catch (InvalidJidException e) {
			trueCounterpart = null;
		}
		return new Message(cursor.getString(cursor.getColumnIndex(UUID)),
				cursor.getString(cursor.getColumnIndex(CONVERSATION)),
				jid,
				trueCounterpart,
				cursor.getString(cursor.getColumnIndex(BODY)),
				cursor.getLong(cursor.getColumnIndex(TIME_SENT)),
				cursor.getInt(cursor.getColumnIndex(ENCRYPTION)),
				cursor.getInt(cursor.getColumnIndex(STATUS)),
				cursor.getInt(cursor.getColumnIndex(TYPE)),
				cursor.getString(cursor.getColumnIndex(REMOTE_MSG_ID)),
				cursor.getString(cursor.getColumnIndex(RELATIVE_FILE_PATH)),
				cursor.getString(cursor.getColumnIndex(SERVER_MSG_ID)));
	}

	public static Message createStatusMessage(Conversation conversation, String body) {
		Message message = new Message();
		message.setType(Message.TYPE_STATUS);
		message.setConversation(conversation);
		message.setBody(body);
		return message;
	}

	@Override
	public ContentValues getContentValues() {
		ContentValues values = new ContentValues();
		values.put(UUID, uuid);
		values.put(CONVERSATION, conversationUuid);
		if (counterpart == null) {
			values.putNull(COUNTERPART);
		} else {
			values.put(COUNTERPART, counterpart.toString());
		}
		if (trueCounterpart == null) {
			values.putNull(TRUE_COUNTERPART);
		} else {
			values.put(TRUE_COUNTERPART, trueCounterpart.toString());
		}
		values.put(BODY, body);
		values.put(TIME_SENT, timeSent);
		values.put(ENCRYPTION, encryption);
		values.put(STATUS, status);
		values.put(TYPE, type);
		values.put(REMOTE_MSG_ID, remoteMsgId);
		values.put(RELATIVE_FILE_PATH, relativeFilePath);
		values.put(SERVER_MSG_ID, serverMsgId);
		return values;
	}

	public String getConversationUuid() {
		return conversationUuid;
	}

	public Conversation getConversation() {
		return this.conversation;
	}

	public void setConversation(Conversation conv) {
		this.conversation = conv;
	}

	public Jid getCounterpart() {
		return counterpart;
	}

	public void setCounterpart(final Jid counterpart) {
		this.counterpart = counterpart;
	}

	public Contact getContact() {
		if (this.conversation.getMode() == Conversation.MODE_SINGLE) {
			return this.conversation.getContact();
		} else {
			if (this.trueCounterpart == null) {
				return null;
			} else {
				return this.conversation.getAccount().getRoster()
						.getContactFromRoster(this.trueCounterpart);
			}
		}
	}

	public String getBody() {
		return body;
	}

	public void setBody(String body) {
		this.body = body;
	}

	public long getTimeSent() {
		return timeSent;
	}

	public int getEncryption() {
		return encryption;
	}

	public void setEncryption(int encryption) {
		this.encryption = encryption;
	}

	public int getStatus() {
		return status;
	}

	public void setStatus(int status) {
		this.status = status;
	}

	public String getRelativeFilePath() {
		return this.relativeFilePath;
	}

	public void setRelativeFilePath(String path) {
		this.relativeFilePath = path;
	}

	public String getRemoteMsgId() {
		return this.remoteMsgId;
	}

	public void setRemoteMsgId(String id) {
		this.remoteMsgId = id;
	}

	public String getServerMsgId() {
		return this.serverMsgId;
	}

	public void setServerMsgId(String id) {
		this.serverMsgId = id;
	}

	public boolean isRead() {
		return this.read;
	}

	public void markRead() {
		this.read = true;
	}

	public void markUnread() {
		this.read = false;
	}

	public void setTime(long time) {
		this.timeSent = time;
	}

	public String getEncryptedBody() {
		return this.encryptedBody;
	}

	public void setEncryptedBody(String body) {
		this.encryptedBody = body;
	}

	public int getType() {
		return this.type;
	}

	public void setType(int type) {
		this.type = type;
	}

	public void setTrueCounterpart(Jid trueCounterpart) {
		this.trueCounterpart = trueCounterpart;
	}

	public Downloadable getDownloadable() {
		return this.downloadable;
	}

	public void setDownloadable(Downloadable downloadable) {
		this.downloadable = downloadable;
	}

	public boolean equals(Message message) {
		if (this.serverMsgId != null && message.getServerMsgId() != null) {
			return this.serverMsgId.equals(message.getServerMsgId());
		} else if (this.body == null || this.counterpart == null) {
			return false;
		} else if (message.getRemoteMsgId() != null) {
			return (message.getRemoteMsgId().equals(this.remoteMsgId) || message.getRemoteMsgId().equals(this.uuid))
					&& this.counterpart.equals(message.getCounterpart())
					&& this.body.equals(message.getBody());
		} else {
			return this.remoteMsgId == null
					&& this.counterpart.equals(message.getCounterpart())
					&& this.body.equals(message.getBody())
					&& Math.abs(this.getTimeSent() - message.getTimeSent()) < Config.MESSAGE_MERGE_WINDOW * 1000;
		}
	}

	public Message next() {
		synchronized (this.conversation.messages) {
			if (this.mNextMessage == null) {
				int index = this.conversation.messages.indexOf(this);
				if (index < 0 || index >= this.conversation.messages.size() - 1) {
					this.mNextMessage = null;
				} else {
					this.mNextMessage = this.conversation.messages.get(index + 1);
				}
			}
			return this.mNextMessage;
		}
	}

	public Message prev() {
		synchronized (this.conversation.messages) {
			if (this.mPreviousMessage == null) {
				int index = this.conversation.messages.indexOf(this);
				if (index <= 0 || index > this.conversation.messages.size()) {
					this.mPreviousMessage = null;
				} else {
					this.mPreviousMessage = this.conversation.messages.get(index - 1);
				}
			}
			return this.mPreviousMessage;
		}
	}

	public boolean mergeable(final Message message) {
		return message != null &&
				(message.getType() == Message.TYPE_TEXT &&
						this.getDownloadable() == null &&
						message.getDownloadable() == null &&
						message.getEncryption() != Message.ENCRYPTION_PGP &&
						this.getType() == message.getType() &&
						//this.getStatus() == message.getStatus() &&
						isStatusMergeable(this.getStatus(), message.getStatus()) &&
						this.getEncryption() == message.getEncryption() &&
						this.getCounterpart() != null &&
						this.getCounterpart().equals(message.getCounterpart()) &&
						(message.getTimeSent() - this.getTimeSent()) <= (Config.MESSAGE_MERGE_WINDOW * 1000) &&
						!GeoHelper.isGeoUri(message.getBody()) &&
						!GeoHelper.isGeoUri(this.body) &&
						message.treatAsDownloadable() == Decision.NEVER &&
						this.treatAsDownloadable() == Decision.NEVER &&
						!message.getBody().startsWith(ME_COMMAND) &&
						!this.getBody().startsWith(ME_COMMAND) &&
						!this.bodyIsHeart() &&
						!message.bodyIsHeart()
				);
	}

	private static boolean isStatusMergeable(int a, int b) {
		return a == b || (
				(a == Message.STATUS_SEND_RECEIVED && b == Message.STATUS_UNSEND)
						|| (a == Message.STATUS_SEND_RECEIVED && b == Message.STATUS_SEND)
						|| (a == Message.STATUS_UNSEND && b == Message.STATUS_SEND)
						|| (a == Message.STATUS_UNSEND && b == Message.STATUS_SEND_RECEIVED)
						|| (a == Message.STATUS_SEND && b == Message.STATUS_UNSEND)
						|| (a == Message.STATUS_SEND && b == Message.STATUS_SEND_RECEIVED)
		);
	}

	public String getMergedBody() {
		final Message next = this.next();
		if (this.mergeable(next)) {
			return getBody().trim() + MERGE_SEPARATOR + next.getMergedBody();
		}
		return getBody().trim();
	}

	public boolean hasMeCommand() {
		return getMergedBody().startsWith(ME_COMMAND);
	}

	public int getMergedStatus() {
		final Message next = this.next();
		if (this.mergeable(next)) {
			return next.getStatus();
		}
		return getStatus();
	}

	public long getMergedTimeSent() {
		Message next = this.next();
		if (this.mergeable(next)) {
			return next.getMergedTimeSent();
		} else {
			return getTimeSent();
		}
	}

	public boolean wasMergedIntoPrevious() {
		Message prev = this.prev();
		return prev != null && prev.mergeable(this);
	}

	public boolean trusted() {
		Contact contact = this.getContact();
		return (status > STATUS_RECEIVED || (contact != null && contact.trusted()));
	}

	public boolean fixCounterpart() {
		Presences presences = conversation.getContact().getPresences();
		if (counterpart != null && presences.has(counterpart.getResourcepart())) {
			return true;
		} else if (presences.size() >= 1) {
			try {
				counterpart = Jid.fromParts(conversation.getJid().getLocalpart(),
						conversation.getJid().getDomainpart(),
						presences.asStringArray()[0]);
				return true;
			} catch (InvalidJidException e) {
				counterpart = null;
				return false;
			}
		} else {
			counterpart = null;
			return false;
		}
	}

	public enum Decision {
		MUST,
		SHOULD,
		NEVER,
	}

	private static String extractRelevantExtension(URL url) {
		String path = url.getPath();
		if (path == null || path.isEmpty()) {
			return null;
		}
		String filename = path.substring(path.lastIndexOf('/') + 1).toLowerCase();
		String[] extensionParts = filename.split("\\.");
		if (extensionParts.length == 2) {
			return extensionParts[extensionParts.length - 1];
		} else if (extensionParts.length == 3 && Arrays
				.asList(Downloadable.VALID_CRYPTO_EXTENSIONS)
				.contains(extensionParts[extensionParts.length - 1])) {
			return extensionParts[extensionParts.length -2];
		}
		return null;
	}

	public String getMimeType() {
		if (relativeFilePath != null) {
			int start = relativeFilePath.lastIndexOf('.') + 1;
			if (start < relativeFilePath.length()) {
				return MimeUtils.guessMimeTypeFromExtension(relativeFilePath.substring(start));
			} else {
				return null;
			}
		} else {
			try {
				return MimeUtils.guessMimeTypeFromExtension(extractRelevantExtension(new URL(body.trim())));
			} catch (MalformedURLException e) {
				return null;
			}
		}
	}

	public Decision treatAsDownloadable() {
		if (body.trim().contains(" ")) {
			return Decision.NEVER;
		}
		try {
			URL url = new URL(body);
			if (!url.getProtocol().equalsIgnoreCase("http") && !url.getProtocol().equalsIgnoreCase("https")) {
				return Decision.NEVER;
			}
			String extension = extractRelevantExtension(url);
			if (extension == null) {
				return Decision.NEVER;
			}
			String ref = url.getRef();
			boolean encrypted = ref != null && ref.matches("([A-Fa-f0-9]{2}){48}");

			if (encrypted) {
				if (MimeUtils.guessMimeTypeFromExtension(extension) != null) {
					return Decision.MUST;
				} else {
					return Decision.NEVER;
				}
			} else if (Arrays.asList(Downloadable.VALID_IMAGE_EXTENSIONS).contains(extension)
					|| Arrays.asList(Downloadable.WELL_KNOWN_EXTENSIONS).contains(extension)) {
				return Decision.SHOULD;
			} else {
				return Decision.NEVER;
			}

		} catch (MalformedURLException e) {
			return Decision.NEVER;
		}
	}

	public boolean bodyIsHeart() {
		return body != null && UIHelper.HEARTS.contains(body.trim());
	}

	public FileParams getFileParams() {
		FileParams params = getLegacyFileParams();
		if (params != null) {
			return params;
		}
		params = new FileParams();
		if (this.downloadable != null) {
			params.size = this.downloadable.getFileSize();
		}
		if (body == null) {
			return params;
		}
		String parts[] = body.split("\\|");
		switch (parts.length) {
			case 1:
				try {
					params.size = Long.parseLong(parts[0]);
				} catch (NumberFormatException e) {
					try {
						params.url = new URL(parts[0]);
					} catch (MalformedURLException e1) {
						params.url = null;
					}
				}
				break;
			case 2:
			case 4:
				try {
					params.url = new URL(parts[0]);
				} catch (MalformedURLException e1) {
					params.url = null;
				}
				try {
					params.size = Long.parseLong(parts[1]);
				} catch (NumberFormatException e) {
					params.size = 0;
				}
				try {
					params.width = Integer.parseInt(parts[2]);
				} catch (NumberFormatException | ArrayIndexOutOfBoundsException e) {
					params.width = 0;
				}
				try {
					params.height = Integer.parseInt(parts[3]);
				} catch (NumberFormatException | ArrayIndexOutOfBoundsException e) {
					params.height = 0;
				}
				break;
			case 3:
				try {
					params.size = Long.parseLong(parts[0]);
				} catch (NumberFormatException e) {
					params.size = 0;
				}
				try {
					params.width = Integer.parseInt(parts[1]);
				} catch (NumberFormatException e) {
					params.width = 0;
				}
				try {
					params.height = Integer.parseInt(parts[2]);
				} catch (NumberFormatException e) {
					params.height = 0;
				}
				break;
		}
		return params;
	}

	public FileParams getLegacyFileParams() {
		FileParams params = new FileParams();
		if (body == null) {
			return params;
		}
		String parts[] = body.split(",");
		if (parts.length == 3) {
			try {
				params.size = Long.parseLong(parts[0]);
			} catch (NumberFormatException e) {
				return null;
			}
			try {
				params.width = Integer.parseInt(parts[1]);
			} catch (NumberFormatException e) {
				return null;
			}
			try {
				params.height = Integer.parseInt(parts[2]);
			} catch (NumberFormatException e) {
				return null;
			}
			return params;
		} else {
			return null;
		}
	}

	public void untie() {
		this.mNextMessage = null;
		this.mPreviousMessage = null;
	}

	public boolean isFileOrImage() {
		return type == TYPE_FILE || type == TYPE_IMAGE;
	}

	public boolean hasFileOnRemoteHost() {
		return isFileOrImage() && getFileParams().url != null;
	}

	public boolean needsUploading() {
		return isFileOrImage() && getFileParams().url == null;
	}

	public class FileParams {
		public URL url;
		public long size = 0;
		public int width = 0;
		public int height = 0;
	}

	public boolean isTrusted() {
		return this.axolotlSession != null && this.axolotlSession.isTrusted();
	}

	public void setAxolotlSession(AxolotlService.XmppAxolotlSession session) {
		this.axolotlSession = session;
	}
}


File: src/main/java/eu/siacs/conversations/parser/MessageParser.java
package eu.siacs.conversations.parser;

import android.util.Log;
import android.util.Pair;

import net.java.otr4j.session.Session;
import net.java.otr4j.session.SessionStatus;

import java.util.List;
import java.util.Set;

import eu.siacs.conversations.Config;
import eu.siacs.conversations.crypto.axolotl.AxolotlService;
import eu.siacs.conversations.crypto.axolotl.XmppAxolotlMessage;
import eu.siacs.conversations.entities.Account;
import eu.siacs.conversations.entities.Contact;
import eu.siacs.conversations.entities.Conversation;
import eu.siacs.conversations.entities.Message;
import eu.siacs.conversations.entities.MucOptions;
import eu.siacs.conversations.http.HttpConnectionManager;
import eu.siacs.conversations.services.MessageArchiveService;
import eu.siacs.conversations.services.XmppConnectionService;
import eu.siacs.conversations.utils.CryptoHelper;
import eu.siacs.conversations.xml.Element;
import eu.siacs.conversations.xmpp.OnMessagePacketReceived;
import eu.siacs.conversations.xmpp.chatstate.ChatState;
import eu.siacs.conversations.xmpp.jid.Jid;
import eu.siacs.conversations.xmpp.pep.Avatar;
import eu.siacs.conversations.xmpp.stanzas.MessagePacket;

public class MessageParser extends AbstractParser implements
		OnMessagePacketReceived {
	public MessageParser(XmppConnectionService service) {
		super(service);
	}

	private boolean extractChatState(Conversation conversation, final MessagePacket packet) {
		ChatState state = ChatState.parse(packet);
		if (state != null && conversation != null) {
			final Account account = conversation.getAccount();
			Jid from = packet.getFrom();
			if (from.toBareJid().equals(account.getJid().toBareJid())) {
				conversation.setOutgoingChatState(state);
				return false;
			} else {
				return conversation.setIncomingChatState(state);
			}
		}
		return false;
	}

	private Message parseOtrChat(String body, Jid from, String id, Conversation conversation) {
		String presence;
		if (from.isBareJid()) {
			presence = "";
		} else {
			presence = from.getResourcepart();
		}
		if (body.matches("^\\?OTRv\\d{1,2}\\?.*")) {
			conversation.endOtrIfNeeded();
		}
		if (!conversation.hasValidOtrSession()) {
			conversation.startOtrSession(presence,false);
		} else {
			String foreignPresence = conversation.getOtrSession().getSessionID().getUserID();
			if (!foreignPresence.equals(presence)) {
				conversation.endOtrIfNeeded();
				conversation.startOtrSession(presence, false);
			}
		}
		try {
			conversation.setLastReceivedOtrMessageId(id);
			Session otrSession = conversation.getOtrSession();
			SessionStatus before = otrSession.getSessionStatus();
			body = otrSession.transformReceiving(body);
			SessionStatus after = otrSession.getSessionStatus();
			if ((before != after) && (after == SessionStatus.ENCRYPTED)) {
				conversation.setNextEncryption(Message.ENCRYPTION_OTR);
				mXmppConnectionService.onOtrSessionEstablished(conversation);
			} else if ((before != after) && (after == SessionStatus.FINISHED)) {
				conversation.setNextEncryption(Message.ENCRYPTION_NONE);
				conversation.resetOtrSession();
				mXmppConnectionService.updateConversationUi();
			}
			if ((body == null) || (body.isEmpty())) {
				return null;
			}
			if (body.startsWith(CryptoHelper.FILETRANSFER)) {
				String key = body.substring(CryptoHelper.FILETRANSFER.length());
				conversation.setSymmetricKey(CryptoHelper.hexToBytes(key));
				return null;
			}
			Message finishedMessage = new Message(conversation, body, Message.ENCRYPTION_OTR, Message.STATUS_RECEIVED);
			conversation.setLastReceivedOtrMessageId(null);
			return finishedMessage;
		} catch (Exception e) {
			conversation.resetOtrSession();
			return null;
		}
	}

	private Message parseAxolotlChat(Element axolotlMessage, Jid from, String id, Conversation conversation, int status) {
		Message finishedMessage = null;
		AxolotlService service = conversation.getAccount().getAxolotlService();
		XmppAxolotlMessage xmppAxolotlMessage = new XmppAxolotlMessage(from.toBareJid(), axolotlMessage);
		XmppAxolotlMessage.XmppAxolotlPlaintextMessage plaintextMessage = service.processReceiving(xmppAxolotlMessage);
		if(plaintextMessage != null) {
			finishedMessage = new Message(conversation, plaintextMessage.getPlaintext(), Message.ENCRYPTION_AXOLOTL, status);
			finishedMessage.setAxolotlSession(plaintextMessage.getSession());
		}

		return finishedMessage;
	}

	private class Invite {
		Jid jid;
		String password;
		Invite(Jid jid, String password) {
			this.jid = jid;
			this.password = password;
		}

		public boolean execute(Account account) {
			if (jid != null) {
				Conversation conversation = mXmppConnectionService.findOrCreateConversation(account, jid, true);
				if (!conversation.getMucOptions().online()) {
					conversation.getMucOptions().setPassword(password);
					mXmppConnectionService.databaseBackend.updateConversation(conversation);
					mXmppConnectionService.joinMuc(conversation);
					mXmppConnectionService.updateConversationUi();
				}
				return true;
			}
			return false;
		}
	}

	private Invite extractInvite(Element message) {
		Element x = message.findChild("x", "http://jabber.org/protocol/muc#user");
		if (x != null) {
			Element invite = x.findChild("invite");
			if (invite != null) {
				Element pw = x.findChild("password");
				return new Invite(message.getAttributeAsJid("from"), pw != null ? pw.getContent(): null);
			}
		} else {
			x = message.findChild("x","jabber:x:conference");
			if (x != null) {
				return new Invite(x.getAttributeAsJid("jid"),x.getAttribute("password"));
			}
		}
		return null;
	}

	private void parseEvent(final Element event, final Jid from, final Account account) {
		Element items = event.findChild("items");
		String node = items == null ? null : items.getAttribute("node");
		if ("urn:xmpp:avatar:metadata".equals(node)) {
			Avatar avatar = Avatar.parseMetadata(items);
			if (avatar != null) {
				avatar.owner = from;
				if (mXmppConnectionService.getFileBackend().isAvatarCached(avatar)) {
					if (account.getJid().toBareJid().equals(from)) {
						if (account.setAvatar(avatar.getFilename())) {
							mXmppConnectionService.databaseBackend.updateAccount(account);
						}
						mXmppConnectionService.getAvatarService().clear(account);
						mXmppConnectionService.updateConversationUi();
						mXmppConnectionService.updateAccountUi();
					} else {
						Contact contact = account.getRoster().getContact(from);
						contact.setAvatar(avatar);
						mXmppConnectionService.getAvatarService().clear(contact);
						mXmppConnectionService.updateConversationUi();
						mXmppConnectionService.updateRosterUi();
					}
				} else {
					mXmppConnectionService.fetchAvatar(account, avatar);
				}
			}
		} else if ("http://jabber.org/protocol/nick".equals(node)) {
			Element i = items.findChild("item");
			Element nick = i == null ? null : i.findChild("nick", "http://jabber.org/protocol/nick");
			if (nick != null) {
				Contact contact = account.getRoster().getContact(from);
				contact.setPresenceName(nick.getContent());
				mXmppConnectionService.getAvatarService().clear(account);
				mXmppConnectionService.updateConversationUi();
				mXmppConnectionService.updateAccountUi();
			}
		} else if (AxolotlService.PEP_DEVICE_LIST.equals(node)) {
			Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Received PEP device list update from "+ from + ", processing...");
			Element item = items.findChild("item");
			Set<Integer> deviceIds = mXmppConnectionService.getIqParser().deviceIds(item);
			AxolotlService axolotlService = account.getAxolotlService();
			axolotlService.registerDevices(from, deviceIds);
			mXmppConnectionService.updateAccountUi();
		}
	}

	private boolean handleErrorMessage(Account account, MessagePacket packet) {
		if (packet.getType() == MessagePacket.TYPE_ERROR) {
			Jid from = packet.getFrom();
			if (from != null) {
				mXmppConnectionService.markMessage(account, from.toBareJid(), packet.getId(), Message.STATUS_SEND_FAILED);
			}
			return true;
		}
		return false;
	}

	@Override
	public void onMessagePacketReceived(Account account, MessagePacket original) {
		if (handleErrorMessage(account, original)) {
			return;
		}
		final MessagePacket packet;
		Long timestamp = null;
		final boolean isForwarded;
		String serverMsgId = null;
		final Element fin = original.findChild("fin", "urn:xmpp:mam:0");
		if (fin != null) {
			mXmppConnectionService.getMessageArchiveService().processFin(fin,original.getFrom());
			return;
		}
		final Element result = original.findChild("result","urn:xmpp:mam:0");
		final MessageArchiveService.Query query = result == null ? null : mXmppConnectionService.getMessageArchiveService().findQuery(result.getAttribute("queryid"));
		if (query != null && query.validFrom(original.getFrom())) {
			Pair<MessagePacket, Long> f = original.getForwardedMessagePacket("result", "urn:xmpp:mam:0");
			if (f == null) {
				return;
			}
			timestamp = f.second;
			packet = f.first;
			isForwarded = true;
			serverMsgId = result.getAttribute("id");
			query.incrementTotalCount();
		} else if (query != null) {
			Log.d(Config.LOGTAG,account.getJid().toBareJid()+": received mam result from invalid sender");
			return;
		} else if (original.fromServer(account)) {
			Pair<MessagePacket, Long> f;
			f = original.getForwardedMessagePacket("received", "urn:xmpp:carbons:2");
			f = f == null ? original.getForwardedMessagePacket("sent", "urn:xmpp:carbons:2") : f;
			packet = f != null ? f.first : original;
			if (handleErrorMessage(account, packet)) {
				return;
			}
			timestamp = f != null ? f.second : null;
			isForwarded = f != null;
		} else {
			packet = original;
			isForwarded = false;
		}

		if (timestamp == null) {
			timestamp = AbstractParser.getTimestamp(packet, System.currentTimeMillis());
		}
		final String body = packet.getBody();
		final Element mucUserElement = packet.findChild("x","http://jabber.org/protocol/muc#user");
		final String pgpEncrypted = packet.findChildContent("x", "jabber:x:encrypted");
		final Element axolotlEncrypted = packet.findChild("axolotl_message", AxolotlService.PEP_PREFIX);
		int status;
		final Jid counterpart;
		final Jid to = packet.getTo();
		final Jid from = packet.getFrom();
		final String remoteMsgId = packet.getId();

		if (from == null || to == null) {
			Log.d(Config.LOGTAG,"no to or from in: "+packet.toString());
			return;
		}
		
		boolean isTypeGroupChat = packet.getType() == MessagePacket.TYPE_GROUPCHAT;
		boolean isProperlyAddressed = !to.isBareJid() || account.countPresences() == 1;
		boolean isMucStatusMessage = from.isBareJid() && mucUserElement != null && mucUserElement.hasChild("status");
		if (packet.fromAccount(account)) {
			status = Message.STATUS_SEND;
			counterpart = to;
		} else {
			status = Message.STATUS_RECEIVED;
			counterpart = from;
		}

		Invite invite = extractInvite(packet);
		if (invite != null && invite.execute(account)) {
			return;
		}

		if (extractChatState(mXmppConnectionService.find(account, from), packet)) {
			mXmppConnectionService.updateConversationUi();
		}

		if ((body != null || pgpEncrypted != null || axolotlEncrypted != null) && !isMucStatusMessage) {
			Conversation conversation = mXmppConnectionService.findOrCreateConversation(account, counterpart.toBareJid(), isTypeGroupChat);
			if (isTypeGroupChat) {
				if (counterpart.getResourcepart().equals(conversation.getMucOptions().getActualNick())) {
					status = Message.STATUS_SEND_RECEIVED;
					if (mXmppConnectionService.markMessage(conversation, remoteMsgId, status)) {
						return;
					} else {
						Message message = conversation.findSentMessageWithBody(body);
						if (message != null) {
							message.setRemoteMsgId(remoteMsgId);
							mXmppConnectionService.markMessage(message, status);
							return;
						}
					}
				} else {
					status = Message.STATUS_RECEIVED;
				}
			}
			Message message;
			if (body != null && body.startsWith("?OTR")) {
				if (!isForwarded && !isTypeGroupChat && isProperlyAddressed) {
					message = parseOtrChat(body, from, remoteMsgId, conversation);
					if (message == null) {
						return;
					}
				} else {
					message = new Message(conversation, body, Message.ENCRYPTION_NONE, status);
				}
			} else if (pgpEncrypted != null) {
				message = new Message(conversation, pgpEncrypted, Message.ENCRYPTION_PGP, status);
			} else if (axolotlEncrypted != null) {
				message = parseAxolotlChat(axolotlEncrypted, from, remoteMsgId, conversation, status);
				if (message == null) {
					return;
				}
			} else {
				message = new Message(conversation, body, Message.ENCRYPTION_NONE, status);
			}
			message.setCounterpart(counterpart);
			message.setRemoteMsgId(remoteMsgId);
			message.setServerMsgId(serverMsgId);
			message.setTime(timestamp);
			message.markable = packet.hasChild("markable", "urn:xmpp:chat-markers:0");
			if (conversation.getMode() == Conversation.MODE_MULTI) {
				message.setTrueCounterpart(conversation.getMucOptions().getTrueCounterpart(counterpart.getResourcepart()));
				if (!isTypeGroupChat) {
					message.setType(Message.TYPE_PRIVATE);
				}
			}
			updateLastseen(packet,account,true);
			boolean checkForDuplicates = serverMsgId != null
					|| (isTypeGroupChat && packet.hasChild("delay","urn:xmpp:delay"))
					|| message.getType() == Message.TYPE_PRIVATE;
			if (checkForDuplicates && conversation.hasDuplicateMessage(message)) {
				Log.d(Config.LOGTAG,"skipping duplicate message from "+message.getCounterpart().toString()+" "+message.getBody());
				return;
			}
			if (query != null) {
				query.incrementMessageCount();
			}
			conversation.add(message);
			if (serverMsgId == null) {
				if (status == Message.STATUS_SEND || status == Message.STATUS_SEND_RECEIVED) {
					mXmppConnectionService.markRead(conversation);
					account.activateGracePeriod();
				} else {
					message.markUnread();
				}
				mXmppConnectionService.updateConversationUi();
			}

			if (mXmppConnectionService.confirmMessages() && remoteMsgId != null && !isForwarded) {
				if (packet.hasChild("markable", "urn:xmpp:chat-markers:0")) {
					MessagePacket receipt = mXmppConnectionService
							.getMessageGenerator().received(account, packet, "urn:xmpp:chat-markers:0");
					mXmppConnectionService.sendMessagePacket(account, receipt);
				}
				if (packet.hasChild("request", "urn:xmpp:receipts")) {
					MessagePacket receipt = mXmppConnectionService
							.getMessageGenerator().received(account, packet, "urn:xmpp:receipts");
					mXmppConnectionService.sendMessagePacket(account, receipt);
				}
			}
			if (account.getXmppConnection() != null && account.getXmppConnection().getFeatures().advancedStreamFeaturesLoaded()) {
				if (conversation.setLastMessageTransmitted(System.currentTimeMillis())) {
					mXmppConnectionService.updateConversation(conversation);
				}
			}

			if (message.getStatus() == Message.STATUS_RECEIVED
					&& conversation.getOtrSession() != null
					&& !conversation.getOtrSession().getSessionID().getUserID()
					.equals(message.getCounterpart().getResourcepart())) {
				conversation.endOtrIfNeeded();
			}

			if (message.getEncryption() == Message.ENCRYPTION_NONE || mXmppConnectionService.saveEncryptedMessages()) {
				mXmppConnectionService.databaseBackend.createMessage(message);
			}
			final HttpConnectionManager manager = this.mXmppConnectionService.getHttpConnectionManager();
			if (message.trusted() && message.treatAsDownloadable() != Message.Decision.NEVER && manager.getAutoAcceptFileSize() > 0) {
				manager.createNewConnection(message);
			} else if (!message.isRead()) {
				mXmppConnectionService.getNotificationService().push(message);
			}
		} else { //no body
			if (isTypeGroupChat) {
				Conversation conversation = mXmppConnectionService.find(account, from.toBareJid());
				if (packet.hasChild("subject")) {
					if (conversation != null && conversation.getMode() == Conversation.MODE_MULTI) {
						conversation.setHasMessagesLeftOnServer(conversation.countMessages() > 0);
						conversation.getMucOptions().setSubject(packet.findChildContent("subject"));
						mXmppConnectionService.updateConversationUi();
						return;
					}
				}

				if (conversation != null && isMucStatusMessage) {
					for (Element child : mucUserElement.getChildren()) {
						if (child.getName().equals("status")
								&& MucOptions.STATUS_CODE_ROOM_CONFIG_CHANGED.equals(child.getAttribute("code"))) {
							mXmppConnectionService.fetchConferenceConfiguration(conversation);
						}
					}
				}
			}
		}

		Element received = packet.findChild("received", "urn:xmpp:chat-markers:0");
		if (received == null) {
			received = packet.findChild("received", "urn:xmpp:receipts");
		}
		if (received != null && !packet.fromAccount(account)) {
			mXmppConnectionService.markMessage(account, from.toBareJid(), received.getAttribute("id"), Message.STATUS_SEND_RECEIVED);
		}
		Element displayed = packet.findChild("displayed", "urn:xmpp:chat-markers:0");
		if (displayed != null) {
			if (packet.fromAccount(account)) {
				Conversation conversation = mXmppConnectionService.find(account,counterpart.toBareJid());
				if (conversation != null) {
					mXmppConnectionService.markRead(conversation);
				}
			} else {
				updateLastseen(packet, account, true);
				final Message displayedMessage = mXmppConnectionService.markMessage(account, from.toBareJid(), displayed.getAttribute("id"), Message.STATUS_SEND_DISPLAYED);
				Message message = displayedMessage == null ? null : displayedMessage.prev();
				while (message != null
						&& message.getStatus() == Message.STATUS_SEND_RECEIVED
						&& message.getTimeSent() < displayedMessage.getTimeSent()) {
					mXmppConnectionService.markMessage(message, Message.STATUS_SEND_DISPLAYED);
					message = message.prev();
				}
			}
		}

		Element event = packet.findChild("event", "http://jabber.org/protocol/pubsub#event");
		if (event != null) {
			parseEvent(event, from, account);
		}

		String nick = packet.findChildContent("nick", "http://jabber.org/protocol/nick");
		if (nick != null) {
			Contact contact = account.getRoster().getContact(from);
			contact.setPresenceName(nick);
		}
	}
}

File: src/main/java/eu/siacs/conversations/persistance/DatabaseBackend.java
package eu.siacs.conversations.persistance;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteCantOpenDatabaseException;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import android.util.Base64;
import android.util.Log;

import org.whispersystems.libaxolotl.AxolotlAddress;
import org.whispersystems.libaxolotl.IdentityKey;
import org.whispersystems.libaxolotl.IdentityKeyPair;
import org.whispersystems.libaxolotl.InvalidKeyException;
import org.whispersystems.libaxolotl.state.PreKeyRecord;
import org.whispersystems.libaxolotl.state.SessionRecord;
import org.whispersystems.libaxolotl.state.SignedPreKeyRecord;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CopyOnWriteArrayList;

import eu.siacs.conversations.Config;
import eu.siacs.conversations.crypto.axolotl.AxolotlService;
import eu.siacs.conversations.entities.Account;
import eu.siacs.conversations.entities.Contact;
import eu.siacs.conversations.entities.Conversation;
import eu.siacs.conversations.entities.Message;
import eu.siacs.conversations.entities.Roster;
import eu.siacs.conversations.xmpp.jid.InvalidJidException;
import eu.siacs.conversations.xmpp.jid.Jid;

public class DatabaseBackend extends SQLiteOpenHelper {

	private static DatabaseBackend instance = null;

	private static final String DATABASE_NAME = "history";
	private static final int DATABASE_VERSION = 15;

	private static String CREATE_CONTATCS_STATEMENT = "create table "
			+ Contact.TABLENAME + "(" + Contact.ACCOUNT + " TEXT, "
			+ Contact.SERVERNAME + " TEXT, " + Contact.SYSTEMNAME + " TEXT,"
			+ Contact.JID + " TEXT," + Contact.KEYS + " TEXT,"
			+ Contact.PHOTOURI + " TEXT," + Contact.OPTIONS + " NUMBER,"
			+ Contact.SYSTEMACCOUNT + " NUMBER, " + Contact.AVATAR + " TEXT, "
			+ Contact.LAST_PRESENCE + " TEXT, " + Contact.LAST_TIME + " NUMBER, "
			+ Contact.GROUPS + " TEXT, FOREIGN KEY(" + Contact.ACCOUNT + ") REFERENCES "
			+ Account.TABLENAME + "(" + Account.UUID
			+ ") ON DELETE CASCADE, UNIQUE(" + Contact.ACCOUNT + ", "
			+ Contact.JID + ") ON CONFLICT REPLACE);";

	private static String CREATE_PREKEYS_STATEMENT = "CREATE TABLE "
			+ AxolotlService.SQLiteAxolotlStore.PREKEY_TABLENAME + "("
				+ AxolotlService.SQLiteAxolotlStore.ACCOUNT + " TEXT,  "
				+ AxolotlService.SQLiteAxolotlStore.ID + " INTEGER, "
				+ AxolotlService.SQLiteAxolotlStore.KEY + " TEXT, FOREIGN KEY("
					+ AxolotlService.SQLiteAxolotlStore.ACCOUNT
				+ ") REFERENCES " + Account.TABLENAME + "(" + Account.UUID + ") ON DELETE CASCADE, "
				+ "UNIQUE( " + AxolotlService.SQLiteAxolotlStore.ACCOUNT + ", "
					+ AxolotlService.SQLiteAxolotlStore.ID
				+ ") ON CONFLICT REPLACE"
			+");";

	private static String CREATE_SIGNED_PREKEYS_STATEMENT = "CREATE TABLE "
			+ AxolotlService.SQLiteAxolotlStore.SIGNED_PREKEY_TABLENAME + "("
				+ AxolotlService.SQLiteAxolotlStore.ACCOUNT + " TEXT,  "
				+ AxolotlService.SQLiteAxolotlStore.ID + " INTEGER, "
				+ AxolotlService.SQLiteAxolotlStore.KEY + " TEXT, FOREIGN KEY("
					+ AxolotlService.SQLiteAxolotlStore.ACCOUNT
				+ ") REFERENCES " + Account.TABLENAME + "(" + Account.UUID + ") ON DELETE CASCADE, "
				+ "UNIQUE( " + AxolotlService.SQLiteAxolotlStore.ACCOUNT + ", "
					+ AxolotlService.SQLiteAxolotlStore.ID
				+ ") ON CONFLICT REPLACE"+
			");";

	private static String CREATE_SESSIONS_STATEMENT = "CREATE TABLE "
			+ AxolotlService.SQLiteAxolotlStore.SESSION_TABLENAME + "("
				+ AxolotlService.SQLiteAxolotlStore.ACCOUNT + " TEXT,  "
				+ AxolotlService.SQLiteAxolotlStore.NAME + " TEXT, "
				+ AxolotlService.SQLiteAxolotlStore.DEVICE_ID + " INTEGER, "
				+ AxolotlService.SQLiteAxolotlStore.TRUSTED + " INTEGER, "
				+ AxolotlService.SQLiteAxolotlStore.KEY + " TEXT, FOREIGN KEY("
					+ AxolotlService.SQLiteAxolotlStore.ACCOUNT
				+ ") REFERENCES " + Account.TABLENAME + "(" + Account.UUID + ") ON DELETE CASCADE, "
				+ "UNIQUE( " + AxolotlService.SQLiteAxolotlStore.ACCOUNT + ", "
					+ AxolotlService.SQLiteAxolotlStore.NAME + ", "
					+ AxolotlService.SQLiteAxolotlStore.DEVICE_ID
				+ ") ON CONFLICT REPLACE"
			+");";

	private static String CREATE_IDENTITIES_STATEMENT = "CREATE TABLE "
			+ AxolotlService.SQLiteAxolotlStore.IDENTITIES_TABLENAME + "("
			+ AxolotlService.SQLiteAxolotlStore.ACCOUNT + " TEXT,  "
			+ AxolotlService.SQLiteAxolotlStore.NAME + " TEXT, "
			+ AxolotlService.SQLiteAxolotlStore.OWN + " INTEGER, "
			+ AxolotlService.SQLiteAxolotlStore.KEY + " TEXT, FOREIGN KEY("
			+ AxolotlService.SQLiteAxolotlStore.ACCOUNT
			+ ") REFERENCES " + Account.TABLENAME + "(" + Account.UUID + ") ON DELETE CASCADE "
			+");";

	private DatabaseBackend(Context context) {
		super(context, DATABASE_NAME, null, DATABASE_VERSION);
	}

	@Override
	public void onCreate(SQLiteDatabase db) {
		db.execSQL("PRAGMA foreign_keys=ON;");
		db.execSQL("create table " + Account.TABLENAME + "(" + Account.UUID
				+ " TEXT PRIMARY KEY," + Account.USERNAME + " TEXT,"
				+ Account.SERVER + " TEXT," + Account.PASSWORD + " TEXT,"
				+ Account.ROSTERVERSION + " TEXT," + Account.OPTIONS
				+ " NUMBER, " + Account.AVATAR + " TEXT, " + Account.KEYS
				+ " TEXT)");
		db.execSQL("create table " + Conversation.TABLENAME + " ("
				+ Conversation.UUID + " TEXT PRIMARY KEY, " + Conversation.NAME
				+ " TEXT, " + Conversation.CONTACT + " TEXT, "
				+ Conversation.ACCOUNT + " TEXT, " + Conversation.CONTACTJID
				+ " TEXT, " + Conversation.CREATED + " NUMBER, "
				+ Conversation.STATUS + " NUMBER, " + Conversation.MODE
				+ " NUMBER, " + Conversation.ATTRIBUTES + " TEXT, FOREIGN KEY("
				+ Conversation.ACCOUNT + ") REFERENCES " + Account.TABLENAME
				+ "(" + Account.UUID + ") ON DELETE CASCADE);");
		db.execSQL("create table " + Message.TABLENAME + "( " + Message.UUID
				+ " TEXT PRIMARY KEY, " + Message.CONVERSATION + " TEXT, "
				+ Message.TIME_SENT + " NUMBER, " + Message.COUNTERPART
				+ " TEXT, " + Message.TRUE_COUNTERPART + " TEXT,"
				+ Message.BODY + " TEXT, " + Message.ENCRYPTION + " NUMBER, "
				+ Message.STATUS + " NUMBER," + Message.TYPE + " NUMBER, "
				+ Message.RELATIVE_FILE_PATH + " TEXT, "
				+ Message.SERVER_MSG_ID + " TEXT, "
				+ Message.REMOTE_MSG_ID + " TEXT, FOREIGN KEY("
				+ Message.CONVERSATION + ") REFERENCES "
				+ Conversation.TABLENAME + "(" + Conversation.UUID
				+ ") ON DELETE CASCADE);");

		db.execSQL(CREATE_CONTATCS_STATEMENT);
		db.execSQL(CREATE_SESSIONS_STATEMENT);
		db.execSQL(CREATE_PREKEYS_STATEMENT);
		db.execSQL(CREATE_SIGNED_PREKEYS_STATEMENT);
		db.execSQL(CREATE_IDENTITIES_STATEMENT);
	}

	@Override
	public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
		if (oldVersion < 2 && newVersion >= 2) {
			db.execSQL("update " + Account.TABLENAME + " set "
					+ Account.OPTIONS + " = " + Account.OPTIONS + " | 8");
		}
		if (oldVersion < 3 && newVersion >= 3) {
			db.execSQL("ALTER TABLE " + Message.TABLENAME + " ADD COLUMN "
					+ Message.TYPE + " NUMBER");
		}
		if (oldVersion < 5 && newVersion >= 5) {
			db.execSQL("DROP TABLE " + Contact.TABLENAME);
			db.execSQL(CREATE_CONTATCS_STATEMENT);
			db.execSQL("UPDATE " + Account.TABLENAME + " SET "
					+ Account.ROSTERVERSION + " = NULL");
		}
		if (oldVersion < 6 && newVersion >= 6) {
			db.execSQL("ALTER TABLE " + Message.TABLENAME + " ADD COLUMN "
					+ Message.TRUE_COUNTERPART + " TEXT");
		}
		if (oldVersion < 7 && newVersion >= 7) {
			db.execSQL("ALTER TABLE " + Message.TABLENAME + " ADD COLUMN "
					+ Message.REMOTE_MSG_ID + " TEXT");
			db.execSQL("ALTER TABLE " + Contact.TABLENAME + " ADD COLUMN "
					+ Contact.AVATAR + " TEXT");
			db.execSQL("ALTER TABLE " + Account.TABLENAME + " ADD COLUMN "
					+ Account.AVATAR + " TEXT");
		}
		if (oldVersion < 8 && newVersion >= 8) {
			db.execSQL("ALTER TABLE " + Conversation.TABLENAME + " ADD COLUMN "
					+ Conversation.ATTRIBUTES + " TEXT");
		}
		if (oldVersion < 9 && newVersion >= 9) {
			db.execSQL("ALTER TABLE " + Contact.TABLENAME + " ADD COLUMN "
					+ Contact.LAST_TIME + " NUMBER");
			db.execSQL("ALTER TABLE " + Contact.TABLENAME + " ADD COLUMN "
					+ Contact.LAST_PRESENCE + " TEXT");
		}
		if (oldVersion < 10 && newVersion >= 10) {
			db.execSQL("ALTER TABLE " + Message.TABLENAME + " ADD COLUMN "
					+ Message.RELATIVE_FILE_PATH + " TEXT");
		}
		if (oldVersion < 11 && newVersion >= 11) {
			db.execSQL("ALTER TABLE " + Contact.TABLENAME + " ADD COLUMN "
					+ Contact.GROUPS + " TEXT");
			db.execSQL("delete from "+Contact.TABLENAME);
			db.execSQL("update "+Account.TABLENAME+" set "+Account.ROSTERVERSION+" = NULL");
		}
		if (oldVersion < 12 && newVersion >= 12) {
			db.execSQL("ALTER TABLE " + Message.TABLENAME + " ADD COLUMN "
					+ Message.SERVER_MSG_ID + " TEXT");
		}
		if (oldVersion < 13 && newVersion >= 13) {
			db.execSQL("delete from "+Contact.TABLENAME);
			db.execSQL("update "+Account.TABLENAME+" set "+Account.ROSTERVERSION+" = NULL");
		}
		if (oldVersion < 14 && newVersion >= 14) {
			// migrate db to new, canonicalized JID domainpart representation

			// Conversation table
			Cursor cursor = db.rawQuery("select * from " + Conversation.TABLENAME, new String[0]);
			while(cursor.moveToNext()) {
				String newJid;
				try {
					newJid = Jid.fromString(
							cursor.getString(cursor.getColumnIndex(Conversation.CONTACTJID))
					).toString();
				} catch (InvalidJidException ignored) {
					Log.e(Config.LOGTAG, "Failed to migrate Conversation CONTACTJID "
							+cursor.getString(cursor.getColumnIndex(Conversation.CONTACTJID))
							+": " + ignored +". Skipping...");
					continue;
				}

				String updateArgs[] = {
						newJid,
						cursor.getString(cursor.getColumnIndex(Conversation.UUID)),
				};
				db.execSQL("update " + Conversation.TABLENAME
						+ " set " + Conversation.CONTACTJID	+ " = ? "
						+ " where " + Conversation.UUID + " = ?", updateArgs);
			}
			cursor.close();

			// Contact table
			cursor = db.rawQuery("select * from " + Contact.TABLENAME, new String[0]);
			while(cursor.moveToNext()) {
				String newJid;
				try {
					newJid = Jid.fromString(
							cursor.getString(cursor.getColumnIndex(Contact.JID))
					).toString();
				} catch (InvalidJidException ignored) {
					Log.e(Config.LOGTAG, "Failed to migrate Contact JID "
							+cursor.getString(cursor.getColumnIndex(Contact.JID))
							+": " + ignored +". Skipping...");
					continue;
				}

				String updateArgs[] = {
						newJid,
						cursor.getString(cursor.getColumnIndex(Contact.ACCOUNT)),
						cursor.getString(cursor.getColumnIndex(Contact.JID)),
				};
				db.execSQL("update " + Contact.TABLENAME
						+ " set " + Contact.JID + " = ? "
						+ " where " + Contact.ACCOUNT + " = ? "
						+ " AND " + Contact.JID + " = ?", updateArgs);
			}
			cursor.close();

			// Account table
			cursor = db.rawQuery("select * from " + Account.TABLENAME, new String[0]);
			while(cursor.moveToNext()) {
				String newServer;
				try {
					newServer = Jid.fromParts(
							cursor.getString(cursor.getColumnIndex(Account.USERNAME)),
							cursor.getString(cursor.getColumnIndex(Account.SERVER)),
							"mobile"
					).getDomainpart();
				} catch (InvalidJidException ignored) {
					Log.e(Config.LOGTAG, "Failed to migrate Account SERVER "
							+cursor.getString(cursor.getColumnIndex(Account.SERVER))
							+": " + ignored +". Skipping...");
					continue;
				}

				String updateArgs[] = {
						newServer,
						cursor.getString(cursor.getColumnIndex(Account.UUID)),
				};
				db.execSQL("update " + Account.TABLENAME
						+ " set " + Account.SERVER + " = ? "
						+ " where " + Account.UUID + " = ?", updateArgs);
			}
			cursor.close();
		}
		if (oldVersion < 15  && newVersion >= 15) {
			recreateAxolotlDb();
		}
	}

	public static synchronized DatabaseBackend getInstance(Context context) {
		if (instance == null) {
			instance = new DatabaseBackend(context);
		}
		return instance;
	}

	public void createConversation(Conversation conversation) {
		SQLiteDatabase db = this.getWritableDatabase();
		db.insert(Conversation.TABLENAME, null, conversation.getContentValues());
	}

	public void createMessage(Message message) {
		SQLiteDatabase db = this.getWritableDatabase();
		db.insert(Message.TABLENAME, null, message.getContentValues());
	}

	public void createAccount(Account account) {
		SQLiteDatabase db = this.getWritableDatabase();
		db.insert(Account.TABLENAME, null, account.getContentValues());
	}

	public void createContact(Contact contact) {
		SQLiteDatabase db = this.getWritableDatabase();
		db.insert(Contact.TABLENAME, null, contact.getContentValues());
	}

	public int getConversationCount() {
		SQLiteDatabase db = this.getReadableDatabase();
		Cursor cursor = db.rawQuery("select count(uuid) as count from "
				+ Conversation.TABLENAME + " where " + Conversation.STATUS
				+ "=" + Conversation.STATUS_AVAILABLE, null);
		cursor.moveToFirst();
		int count = cursor.getInt(0);
		cursor.close();
		return count;
	}

	public CopyOnWriteArrayList<Conversation> getConversations(int status) {
		CopyOnWriteArrayList<Conversation> list = new CopyOnWriteArrayList<>();
		SQLiteDatabase db = this.getReadableDatabase();
		String[] selectionArgs = { Integer.toString(status) };
		Cursor cursor = db.rawQuery("select * from " + Conversation.TABLENAME
				+ " where " + Conversation.STATUS + " = ? order by "
				+ Conversation.CREATED + " desc", selectionArgs);
		while (cursor.moveToNext()) {
			list.add(Conversation.fromCursor(cursor));
		}
		cursor.close();
		return list;
	}

	public ArrayList<Message> getMessages(Conversation conversations, int limit) {
		return getMessages(conversations, limit, -1);
	}

	public ArrayList<Message> getMessages(Conversation conversation, int limit,
			long timestamp) {
		ArrayList<Message> list = new ArrayList<>();
		SQLiteDatabase db = this.getReadableDatabase();
		Cursor cursor;
		if (timestamp == -1) {
			String[] selectionArgs = { conversation.getUuid() };
			cursor = db.query(Message.TABLENAME, null, Message.CONVERSATION
					+ "=?", selectionArgs, null, null, Message.TIME_SENT
					+ " DESC", String.valueOf(limit));
		} else {
			String[] selectionArgs = { conversation.getUuid(),
					Long.toString(timestamp) };
			cursor = db.query(Message.TABLENAME, null, Message.CONVERSATION
					+ "=? and " + Message.TIME_SENT + "<?", selectionArgs,
					null, null, Message.TIME_SENT + " DESC",
					String.valueOf(limit));
		}
		if (cursor.getCount() > 0) {
			cursor.moveToLast();
			do {
				Message message = Message.fromCursor(cursor);
				message.setConversation(conversation);
				list.add(message);
			} while (cursor.moveToPrevious());
		}
		cursor.close();
		return list;
	}

	public Conversation findConversation(final Account account, final Jid contactJid) {
		SQLiteDatabase db = this.getReadableDatabase();
		String[] selectionArgs = { account.getUuid(),
				contactJid.toBareJid().toString() + "/%",
				contactJid.toBareJid().toString()
				};
		Cursor cursor = db.query(Conversation.TABLENAME, null,
				Conversation.ACCOUNT + "=? AND (" + Conversation.CONTACTJID
						+ " like ? OR " + Conversation.CONTACTJID + "=?)", selectionArgs, null, null, null);
		if (cursor.getCount() == 0)
			return null;
		cursor.moveToFirst();
		Conversation conversation = Conversation.fromCursor(cursor);
		cursor.close();
		return conversation;
	}

	public void updateConversation(final Conversation conversation) {
		final SQLiteDatabase db = this.getWritableDatabase();
		final String[] args = { conversation.getUuid() };
		db.update(Conversation.TABLENAME, conversation.getContentValues(),
				Conversation.UUID + "=?", args);
	}

	public List<Account> getAccounts() {
		List<Account> list = new ArrayList<>();
		SQLiteDatabase db = this.getReadableDatabase();
		Cursor cursor = db.query(Account.TABLENAME, null, null, null, null,
				null, null);
		while (cursor.moveToNext()) {
			list.add(Account.fromCursor(cursor));
		}
		cursor.close();
		return list;
	}

	public void updateAccount(Account account) {
		SQLiteDatabase db = this.getWritableDatabase();
		String[] args = { account.getUuid() };
		db.update(Account.TABLENAME, account.getContentValues(), Account.UUID
				+ "=?", args);
	}

	public void deleteAccount(Account account) {
		SQLiteDatabase db = this.getWritableDatabase();
		String[] args = { account.getUuid() };
		db.delete(Account.TABLENAME, Account.UUID + "=?", args);
	}

	public boolean hasEnabledAccounts() {
		SQLiteDatabase db = this.getReadableDatabase();
		Cursor cursor = db.rawQuery("select count(" + Account.UUID + ")  from "
				+ Account.TABLENAME + " where not options & (1 <<1)", null);
		try {
			cursor.moveToFirst();
			int count = cursor.getInt(0);
			cursor.close();
			return (count > 0);
		} catch (SQLiteCantOpenDatabaseException e) {
			return true; // better safe than sorry
		} catch (RuntimeException e) {
			return true; // better safe than sorry
		}
	}

	@Override
	public SQLiteDatabase getWritableDatabase() {
		SQLiteDatabase db = super.getWritableDatabase();
		db.execSQL("PRAGMA foreign_keys=ON;");
		return db;
	}

	public void updateMessage(Message message) {
		SQLiteDatabase db = this.getWritableDatabase();
		String[] args = { message.getUuid() };
		db.update(Message.TABLENAME, message.getContentValues(), Message.UUID
				+ "=?", args);
	}

	public void readRoster(Roster roster) {
		SQLiteDatabase db = this.getReadableDatabase();
		Cursor cursor;
		String args[] = { roster.getAccount().getUuid() };
		cursor = db.query(Contact.TABLENAME, null, Contact.ACCOUNT + "=?", args, null, null, null);
		while (cursor.moveToNext()) {
			roster.initContact(Contact.fromCursor(cursor));
		}
		cursor.close();
	}

	public void writeRoster(final Roster roster) {
		final Account account = roster.getAccount();
		final SQLiteDatabase db = this.getWritableDatabase();
		for (Contact contact : roster.getContacts()) {
			if (contact.getOption(Contact.Options.IN_ROSTER)) {
				db.insert(Contact.TABLENAME, null, contact.getContentValues());
			} else {
				String where = Contact.ACCOUNT + "=? AND " + Contact.JID + "=?";
				String[] whereArgs = { account.getUuid(), contact.getJid().toString() };
				db.delete(Contact.TABLENAME, where, whereArgs);
			}
		}
		account.setRosterVersion(roster.getVersion());
		updateAccount(account);
	}

	public void deleteMessage(Message message) {
		SQLiteDatabase db = this.getWritableDatabase();
		String[] args = { message.getUuid() };
		db.delete(Message.TABLENAME, Message.UUID + "=?", args);
	}

	public void deleteMessagesInConversation(Conversation conversation) {
		SQLiteDatabase db = this.getWritableDatabase();
		String[] args = { conversation.getUuid() };
		db.delete(Message.TABLENAME, Message.CONVERSATION + "=?", args);
	}

	public Conversation findConversationByUuid(String conversationUuid) {
		SQLiteDatabase db = this.getReadableDatabase();
		String[] selectionArgs = { conversationUuid };
		Cursor cursor = db.query(Conversation.TABLENAME, null,
				Conversation.UUID + "=?", selectionArgs, null, null, null);
		if (cursor.getCount() == 0) {
			return null;
		}
		cursor.moveToFirst();
		Conversation conversation = Conversation.fromCursor(cursor);
		cursor.close();
		return conversation;
	}

	public Message findMessageByUuid(String messageUuid) {
		SQLiteDatabase db = this.getReadableDatabase();
		String[] selectionArgs = { messageUuid };
		Cursor cursor = db.query(Message.TABLENAME, null, Message.UUID + "=?",
				selectionArgs, null, null, null);
		if (cursor.getCount() == 0) {
			return null;
		}
		cursor.moveToFirst();
		Message message = Message.fromCursor(cursor);
		cursor.close();
		return message;
	}

	public Account findAccountByUuid(String accountUuid) {
		SQLiteDatabase db = this.getReadableDatabase();
		String[] selectionArgs = { accountUuid };
		Cursor cursor = db.query(Account.TABLENAME, null, Account.UUID + "=?",
				selectionArgs, null, null, null);
		if (cursor.getCount() == 0) {
			return null;
		}
		cursor.moveToFirst();
		Account account = Account.fromCursor(cursor);
		cursor.close();
		return account;
	}

	public List<Message> getImageMessages(Conversation conversation) {
		ArrayList<Message> list = new ArrayList<>();
		SQLiteDatabase db = this.getReadableDatabase();
		Cursor cursor;
			String[] selectionArgs = { conversation.getUuid(), String.valueOf(Message.TYPE_IMAGE) };
			cursor = db.query(Message.TABLENAME, null, Message.CONVERSATION
					+ "=? AND "+Message.TYPE+"=?", selectionArgs, null, null,null);
		if (cursor.getCount() > 0) {
			cursor.moveToLast();
			do {
				Message message = Message.fromCursor(cursor);
				message.setConversation(conversation);
				list.add(message);
			} while (cursor.moveToPrevious());
		}
		cursor.close();
		return list;
	}

	private Cursor getCursorForSession(Account account, AxolotlAddress contact) {
		final SQLiteDatabase db = this.getReadableDatabase();
		String[] columns = null;
		String[] selectionArgs = {account.getUuid(),
				contact.getName(),
				Integer.toString(contact.getDeviceId())};
		Cursor cursor = db.query(AxolotlService.SQLiteAxolotlStore.SESSION_TABLENAME,
				columns,
				AxolotlService.SQLiteAxolotlStore.ACCOUNT + " = ? AND "
						+ AxolotlService.SQLiteAxolotlStore.NAME + " = ? AND "
						+ AxolotlService.SQLiteAxolotlStore.DEVICE_ID + " = ? ",
				selectionArgs,
				null, null, null);

		return cursor;
	}

	public SessionRecord loadSession(Account account, AxolotlAddress contact) {
		SessionRecord session = null;
		Cursor cursor = getCursorForSession(account, contact);
		if(cursor.getCount() != 0) {
			cursor.moveToFirst();
			try {
				session = new SessionRecord(Base64.decode(cursor.getString(cursor.getColumnIndex(AxolotlService.SQLiteAxolotlStore.KEY)),Base64.DEFAULT));
			} catch (IOException e) {
				cursor.close();
				throw new AssertionError(e);
			}
		}
		cursor.close();
		return session;
	}

	public List<Integer> getSubDeviceSessions(Account account, AxolotlAddress contact) {
		List<Integer> devices = new ArrayList<>();
		final SQLiteDatabase db = this.getReadableDatabase();
		String[] columns = {AxolotlService.SQLiteAxolotlStore.DEVICE_ID};
		String[] selectionArgs = {account.getUuid(),
				contact.getName()};
		Cursor cursor = db.query(AxolotlService.SQLiteAxolotlStore.SESSION_TABLENAME,
				columns,
				AxolotlService.SQLiteAxolotlStore.ACCOUNT + " = ? AND "
						+ AxolotlService.SQLiteAxolotlStore.NAME + " = ?",
				selectionArgs,
				null, null, null);

		while(cursor.moveToNext()) {
			devices.add(cursor.getInt(
					cursor.getColumnIndex(AxolotlService.SQLiteAxolotlStore.DEVICE_ID)));
		}

		cursor.close();
		return devices;
	}

	public boolean containsSession(Account account, AxolotlAddress contact) {
		Cursor cursor = getCursorForSession(account, contact);
		int count = cursor.getCount();
		cursor.close();
		return count != 0;
	}

	public void storeSession(Account account, AxolotlAddress contact, SessionRecord session) {
		SQLiteDatabase db = this.getWritableDatabase();
		ContentValues values = new ContentValues();
		values.put(AxolotlService.SQLiteAxolotlStore.NAME, contact.getName());
		values.put(AxolotlService.SQLiteAxolotlStore.DEVICE_ID, contact.getDeviceId());
		values.put(AxolotlService.SQLiteAxolotlStore.KEY, Base64.encodeToString(session.serialize(),Base64.DEFAULT));
		values.put(AxolotlService.SQLiteAxolotlStore.ACCOUNT, account.getUuid());
		db.insert(AxolotlService.SQLiteAxolotlStore.SESSION_TABLENAME, null, values);
	}

	public void deleteSession(Account account, AxolotlAddress contact) {
		SQLiteDatabase db = this.getWritableDatabase();
		String[] args = {account.getUuid(),
				contact.getName(),
				Integer.toString(contact.getDeviceId())};
		db.delete(AxolotlService.SQLiteAxolotlStore.SESSION_TABLENAME,
				AxolotlService.SQLiteAxolotlStore.ACCOUNT + " = ? AND "
						+ AxolotlService.SQLiteAxolotlStore.NAME + " = ? AND "
						+ AxolotlService.SQLiteAxolotlStore.DEVICE_ID + " = ? ",
				args);
	}

	public void deleteAllSessions(Account account, AxolotlAddress contact) {
		SQLiteDatabase db = this.getWritableDatabase();
		String[] args = {account.getUuid(), contact.getName()};
		db.delete(AxolotlService.SQLiteAxolotlStore.SESSION_TABLENAME,
				AxolotlService.SQLiteAxolotlStore.ACCOUNT + "=? AND "
						+ AxolotlService.SQLiteAxolotlStore.NAME + " = ?",
				args);
	}

	public boolean isTrustedSession(Account account, AxolotlAddress contact) {
		boolean trusted = false;
		Cursor cursor = getCursorForSession(account, contact);
		if(cursor.getCount() != 0) {
			cursor.moveToFirst();
			trusted = cursor.getInt(cursor.getColumnIndex(
					AxolotlService.SQLiteAxolotlStore.TRUSTED)) > 0;
		}
		cursor.close();
		return trusted;
	}

	public void setTrustedSession(Account account, AxolotlAddress contact, boolean trusted) {
		SQLiteDatabase db = this.getWritableDatabase();
		ContentValues values = new ContentValues();
		values.put(AxolotlService.SQLiteAxolotlStore.NAME, contact.getName());
		values.put(AxolotlService.SQLiteAxolotlStore.DEVICE_ID, contact.getDeviceId());
		values.put(AxolotlService.SQLiteAxolotlStore.ACCOUNT, account.getUuid());
		values.put(AxolotlService.SQLiteAxolotlStore.TRUSTED, trusted?1:0);
		db.insert(AxolotlService.SQLiteAxolotlStore.SESSION_TABLENAME, null, values);
	}

	private Cursor getCursorForPreKey(Account account, int preKeyId) {
		SQLiteDatabase db = this.getReadableDatabase();
		String[] columns = {AxolotlService.SQLiteAxolotlStore.KEY};
		String[] selectionArgs = {account.getUuid(), Integer.toString(preKeyId)};
		Cursor cursor = db.query(AxolotlService.SQLiteAxolotlStore.PREKEY_TABLENAME,
				columns,
				AxolotlService.SQLiteAxolotlStore.ACCOUNT + "=? AND "
						+ AxolotlService.SQLiteAxolotlStore.ID + "=?",
				selectionArgs,
				null, null, null);

		return cursor;
	}

	public PreKeyRecord loadPreKey(Account account, int preKeyId) {
		PreKeyRecord record = null;
		Cursor cursor = getCursorForPreKey(account, preKeyId);
		if(cursor.getCount() != 0) {
			cursor.moveToFirst();
			try {
				record = new PreKeyRecord(Base64.decode(cursor.getString(cursor.getColumnIndex(AxolotlService.SQLiteAxolotlStore.KEY)),Base64.DEFAULT));
			} catch (IOException e ) {
				throw new AssertionError(e);
			}
		}
		cursor.close();
		return record;
	}

	public boolean containsPreKey(Account account, int preKeyId) {
		Cursor cursor = getCursorForPreKey(account, preKeyId);
		int count = cursor.getCount();
		cursor.close();
		return count != 0;
	}

	public void storePreKey(Account account, PreKeyRecord record) {
		SQLiteDatabase db = this.getWritableDatabase();
		ContentValues values = new ContentValues();
		values.put(AxolotlService.SQLiteAxolotlStore.ID, record.getId());
		values.put(AxolotlService.SQLiteAxolotlStore.KEY, Base64.encodeToString(record.serialize(),Base64.DEFAULT));
		values.put(AxolotlService.SQLiteAxolotlStore.ACCOUNT, account.getUuid());
		db.insert(AxolotlService.SQLiteAxolotlStore.PREKEY_TABLENAME, null, values);
	}

	public void deletePreKey(Account account, int preKeyId) {
		SQLiteDatabase db = this.getWritableDatabase();
		String[] args = {account.getUuid(), Integer.toString(preKeyId)};
		db.delete(AxolotlService.SQLiteAxolotlStore.PREKEY_TABLENAME,
				AxolotlService.SQLiteAxolotlStore.ACCOUNT + "=? AND "
						+ AxolotlService.SQLiteAxolotlStore.ID + "=?",
				args);
	}

	private Cursor getCursorForSignedPreKey(Account account, int signedPreKeyId) {
		SQLiteDatabase db = this.getReadableDatabase();
		String[] columns = {AxolotlService.SQLiteAxolotlStore.KEY};
		String[] selectionArgs = {account.getUuid(), Integer.toString(signedPreKeyId)};
		Cursor cursor = db.query(AxolotlService.SQLiteAxolotlStore.SIGNED_PREKEY_TABLENAME,
				columns,
				AxolotlService.SQLiteAxolotlStore.ACCOUNT + "=? AND " + AxolotlService.SQLiteAxolotlStore.ID + "=?",
				selectionArgs,
				null, null, null);

		return cursor;
	}

	public SignedPreKeyRecord loadSignedPreKey(Account account, int signedPreKeyId) {
		SignedPreKeyRecord record = null;
		Cursor cursor = getCursorForSignedPreKey(account, signedPreKeyId);
		if(cursor.getCount() != 0) {
			cursor.moveToFirst();
			try {
				record = new SignedPreKeyRecord(Base64.decode(cursor.getString(cursor.getColumnIndex(AxolotlService.SQLiteAxolotlStore.KEY)),Base64.DEFAULT));
			} catch (IOException e ) {
				throw new AssertionError(e);
			}
		}
		cursor.close();
		return record;
	}

	public List<SignedPreKeyRecord> loadSignedPreKeys(Account account) {
		List<SignedPreKeyRecord> prekeys = new ArrayList<>();
		SQLiteDatabase db = this.getReadableDatabase();
		String[] columns = {AxolotlService.SQLiteAxolotlStore.KEY};
		String[] selectionArgs = {account.getUuid()};
		Cursor cursor = db.query(AxolotlService.SQLiteAxolotlStore.SIGNED_PREKEY_TABLENAME,
				columns,
				AxolotlService.SQLiteAxolotlStore.ACCOUNT + "=?",
				selectionArgs,
				null, null, null);

		while(cursor.moveToNext()) {
			try {
				prekeys.add(new SignedPreKeyRecord(Base64.decode(cursor.getString(cursor.getColumnIndex(AxolotlService.SQLiteAxolotlStore.KEY)), Base64.DEFAULT)));
			} catch (IOException ignored) {
			}
		}
		cursor.close();
		return prekeys;
	}

	public boolean containsSignedPreKey(Account account, int signedPreKeyId) {
		Cursor cursor = getCursorForPreKey(account, signedPreKeyId);
		int count = cursor.getCount();
		cursor.close();
		return count != 0;
	}

	public void storeSignedPreKey(Account account, SignedPreKeyRecord record) {
		SQLiteDatabase db = this.getWritableDatabase();
		ContentValues values = new ContentValues();
		values.put(AxolotlService.SQLiteAxolotlStore.ID, record.getId());
		values.put(AxolotlService.SQLiteAxolotlStore.KEY, Base64.encodeToString(record.serialize(),Base64.DEFAULT));
		values.put(AxolotlService.SQLiteAxolotlStore.ACCOUNT, account.getUuid());
		db.insert(AxolotlService.SQLiteAxolotlStore.SIGNED_PREKEY_TABLENAME, null, values);
	}

	public void deleteSignedPreKey(Account account, int signedPreKeyId) {
		SQLiteDatabase db = this.getWritableDatabase();
		String[] args = {account.getUuid(), Integer.toString(signedPreKeyId)};
		db.delete(AxolotlService.SQLiteAxolotlStore.SIGNED_PREKEY_TABLENAME,
				AxolotlService.SQLiteAxolotlStore.ACCOUNT + "=? AND "
						+ AxolotlService.SQLiteAxolotlStore.ID + "=?",
				args);
	}

	private Cursor getIdentityKeyCursor(Account account, String name, boolean own) {
		final SQLiteDatabase db = this.getReadableDatabase();
		String[] columns = {AxolotlService.SQLiteAxolotlStore.KEY};
		String[] selectionArgs = {account.getUuid(),
				name,
				own?"1":"0"};
		Cursor cursor = db.query(AxolotlService.SQLiteAxolotlStore.IDENTITIES_TABLENAME,
				columns,
				AxolotlService.SQLiteAxolotlStore.ACCOUNT + " = ? AND "
						+ AxolotlService.SQLiteAxolotlStore.NAME + " = ? AND "
						+ AxolotlService.SQLiteAxolotlStore.OWN + " = ? ",
				selectionArgs,
				null, null, null);

		return cursor;
	}

	public IdentityKeyPair loadOwnIdentityKeyPair(Account account, String name) {
		IdentityKeyPair identityKeyPair = null;
		Cursor cursor = getIdentityKeyCursor(account, name, true);
		if(cursor.getCount() != 0) {
			cursor.moveToFirst();
			try {
				identityKeyPair = new IdentityKeyPair(Base64.decode(cursor.getString(cursor.getColumnIndex(AxolotlService.SQLiteAxolotlStore.KEY)),Base64.DEFAULT));
			} catch (InvalidKeyException e) {
				Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Encountered invalid IdentityKey in database for account" + account.getJid().toBareJid() + ", address: " + name);
			}
		}
		cursor.close();

		return identityKeyPair;
	}

	public Set<IdentityKey> loadIdentityKeys(Account account, String name) {
		Set<IdentityKey> identityKeys = new HashSet<>();
		Cursor cursor = getIdentityKeyCursor(account, name, false);

		while(cursor.moveToNext()) {
			try {
				identityKeys.add(new IdentityKey(Base64.decode(cursor.getString(cursor.getColumnIndex(AxolotlService.SQLiteAxolotlStore.KEY)),Base64.DEFAULT),0));
			} catch (InvalidKeyException e) {
				Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+"Encountered invalid IdentityKey in database for account"+account.getJid().toBareJid()+", address: "+name);
			}
		}
		cursor.close();

		return identityKeys;
	}

	private void storeIdentityKey(Account account, String name, boolean own, String base64Serialized) {
		SQLiteDatabase db = this.getWritableDatabase();
		ContentValues values = new ContentValues();
		values.put(AxolotlService.SQLiteAxolotlStore.ACCOUNT, account.getUuid());
		values.put(AxolotlService.SQLiteAxolotlStore.NAME, name);
		values.put(AxolotlService.SQLiteAxolotlStore.OWN, own?1:0);
		values.put(AxolotlService.SQLiteAxolotlStore.KEY, base64Serialized);
		db.insert(AxolotlService.SQLiteAxolotlStore.IDENTITIES_TABLENAME, null, values);
	}

	public void storeIdentityKey(Account account, String name, IdentityKey identityKey) {
		storeIdentityKey(account, name, false, Base64.encodeToString(identityKey.serialize(), Base64.DEFAULT));
	}

	public void storeOwnIdentityKeyPair(Account account, String name, IdentityKeyPair identityKeyPair) {
		storeIdentityKey(account, name, true, Base64.encodeToString(identityKeyPair.serialize(),Base64.DEFAULT));
	}

	public void recreateAxolotlDb() {
		Log.d(Config.LOGTAG, AxolotlService.LOGPREFIX+" : "+">>> (RE)CREATING AXOLOTL DATABASE <<<");
		SQLiteDatabase db = this.getWritableDatabase();
		db.execSQL("DROP TABLE IF EXISTS " + AxolotlService.SQLiteAxolotlStore.SESSION_TABLENAME);
		db.execSQL(CREATE_SESSIONS_STATEMENT);
		db.execSQL("DROP TABLE IF EXISTS " + AxolotlService.SQLiteAxolotlStore.PREKEY_TABLENAME);
		db.execSQL(CREATE_PREKEYS_STATEMENT);
		db.execSQL("DROP TABLE IF EXISTS " + AxolotlService.SQLiteAxolotlStore.SIGNED_PREKEY_TABLENAME);
		db.execSQL(CREATE_SIGNED_PREKEYS_STATEMENT);
		db.execSQL("DROP TABLE IF EXISTS " + AxolotlService.SQLiteAxolotlStore.IDENTITIES_TABLENAME);
		db.execSQL(CREATE_IDENTITIES_STATEMENT);
	}
	
	public void wipeAxolotlDb(Account account) {
		String accountName = account.getUuid();
		Log.d(Config.LOGTAG, AxolotlService.getLogprefix(account)+">>> WIPING AXOLOTL DATABASE FOR ACCOUNT " + accountName + " <<<");
		SQLiteDatabase db = this.getWritableDatabase();
		String[] deleteArgs= {
				accountName
		};
		db.delete(AxolotlService.SQLiteAxolotlStore.SESSION_TABLENAME,
				AxolotlService.SQLiteAxolotlStore.ACCOUNT + " = ?",
				deleteArgs);
		db.delete(AxolotlService.SQLiteAxolotlStore.PREKEY_TABLENAME,
				AxolotlService.SQLiteAxolotlStore.ACCOUNT + " = ?",
				deleteArgs);
		db.delete(AxolotlService.SQLiteAxolotlStore.SIGNED_PREKEY_TABLENAME,
				AxolotlService.SQLiteAxolotlStore.ACCOUNT + " = ?",
				deleteArgs);
		db.delete(AxolotlService.SQLiteAxolotlStore.IDENTITIES_TABLENAME,
				AxolotlService.SQLiteAxolotlStore.ACCOUNT + " = ?",
				deleteArgs);
	}
}
