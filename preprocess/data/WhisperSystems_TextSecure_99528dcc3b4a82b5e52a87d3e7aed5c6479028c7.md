Refactoring Types: ['Inline Method', 'Move Class']
vatarImageView.java
package org.thoughtcrime.securesms.components;

import android.content.Context;
import android.content.Intent;
import android.provider.ContactsContract;
import android.support.annotation.Nullable;
import android.util.AttributeSet;
import android.view.View;
import android.widget.ImageView;

import org.thoughtcrime.securesms.contacts.ContactPhotoFactory;
import org.thoughtcrime.securesms.recipients.Recipient;
import org.thoughtcrime.securesms.recipients.RecipientFactory;
import org.thoughtcrime.securesms.recipients.Recipients;

public class AvatarImageView extends ImageView {

  public AvatarImageView(Context context) {
    super(context);
    setScaleType(ScaleType.CENTER_CROP);
  }

  public AvatarImageView(Context context, AttributeSet attrs) {
    super(context, attrs);
    setScaleType(ScaleType.CENTER_CROP);
  }

  public void setAvatar(@Nullable Recipients recipients, boolean quickContactEnabled) {
    if (recipients != null) {
      setImageDrawable(recipients.getContactPhoto(getContext()));
      setAvatarClickHandler(recipients, quickContactEnabled);
    } else {
      setImageDrawable(ContactPhotoFactory.getDefaultContactPhoto(getContext(), null));
      setOnClickListener(null);
    }
  }

  public void setAvatar(@Nullable Recipient recipient, boolean quickContactEnabled) {
    setAvatar(RecipientFactory.getRecipientsFor(getContext(), recipient, true), quickContactEnabled);
  }

  private void setAvatarClickHandler(final Recipients recipients, boolean quickContactEnabled) {
    if (!recipients.isGroupRecipient() && quickContactEnabled) {
      setOnClickListener(new View.OnClickListener() {
        @Override
        public void onClick(View v) {
          Recipient recipient = recipients.getPrimaryRecipient();

          if (recipient != null && recipient.getContactUri() != null) {
            ContactsContract.QuickContact.showQuickContact(getContext(), AvatarImageView.this, recipient.getContactUri(), ContactsContract.QuickContact.MODE_LARGE, null);
          } else if (recipient != null) {
            final Intent intent = new Intent(Intent.ACTION_INSERT_OR_EDIT);
            intent.putExtra(ContactsContract.Intents.Insert.PHONE, recipient.getNumber());
            intent.setType(ContactsContract.Contacts.CONTENT_ITEM_TYPE);
            getContext().startActivity(intent);
          }
        }
      });
    } else {
      setOnClickListener(null);
    }
  }

}


File: src/org/thoughtcrime/securesms/contacts/ContactPhotoFactory.java
package org.thoughtcrime.securesms.contacts;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.LayerDrawable;
import android.net.Uri;
import android.os.Build.VERSION;
import android.os.Build.VERSION_CODES;
import android.provider.ContactsContract;
import android.support.annotation.Nullable;
import android.util.Log;
import android.widget.ImageView;

import com.amulyakhare.textdrawable.TextDrawable;
import com.amulyakhare.textdrawable.util.ColorGenerator;
import com.makeramen.roundedimageview.RoundedDrawable;

import org.thoughtcrime.securesms.R;
import org.thoughtcrime.securesms.recipients.Recipient;
import org.thoughtcrime.securesms.util.BitmapDecodingException;
import org.thoughtcrime.securesms.util.BitmapUtil;
import org.thoughtcrime.securesms.util.LRUCache;

import java.io.InputStream;
import java.util.Collections;
import java.util.Map;

public class ContactPhotoFactory {
  private static final String TAG = ContactPhotoFactory.class.getSimpleName();

  private static final ColorGenerator COLOR_GENERATOR = ColorGenerator.MATERIAL;
  private static final int            UNKNOWN_COLOR   = 0xff9E9E9E;

  private static final Object defaultPhotoLock      = new Object();
  private static final Object defaultGroupPhotoLock = new Object();
  private static final Object loadingPhotoLock      = new Object();

  private static Drawable defaultContactPhoto;
  private static Drawable defaultGroupContactPhoto;
  private static Drawable loadingPhoto;

  private static final Map<Uri,Bitmap> localUserContactPhotoCache =
      Collections.synchronizedMap(new LRUCache<Uri,Bitmap>(2));

  public static Drawable getLoadingPhoto(Context context) {
    synchronized (loadingPhotoLock) {
      if (loadingPhoto == null)
        loadingPhoto = RoundedDrawable.fromDrawable(context.getResources().getDrawable(android.R.color.transparent));

      return loadingPhoto;
    }
  }

  public static Drawable getDefaultContactPhoto(Context context, @Nullable String name) {
    int targetSize = context.getResources().getDimensionPixelSize(R.dimen.contact_photo_target_size);

    if (name != null && !name.isEmpty()) {
      return TextDrawable.builder().beginConfig()
                         .width(targetSize)
                         .height(targetSize)
                         .endConfig()
                         .buildRound(String.valueOf(name.charAt(0)),
                                     COLOR_GENERATOR.getColor(name));
    }

    synchronized (defaultPhotoLock) {
      if (defaultContactPhoto == null)
        defaultContactPhoto = TextDrawable.builder().beginConfig()
                                          .width(targetSize)
                                          .height(targetSize)
                                          .endConfig()
                                          .buildRound("#", UNKNOWN_COLOR);

      return defaultContactPhoto;
    }
  }

  public static Drawable getDefaultGroupPhoto(Context context) {
    synchronized (defaultGroupPhotoLock) {
      if (defaultGroupContactPhoto == null) {
        Drawable        background = TextDrawable.builder().buildRound(" ", UNKNOWN_COLOR);
        RoundedDrawable foreground = (RoundedDrawable) RoundedDrawable.fromDrawable(context.getResources().getDrawable(R.drawable.ic_group_white_24dp));
        foreground.setScaleType(ImageView.ScaleType.CENTER);


        defaultGroupContactPhoto = new ExpandingLayerDrawable(new Drawable[] {background, foreground});
      }

      return defaultGroupContactPhoto;
    }
  }

  public static void clearCache() {
    localUserContactPhotoCache.clear();
  }

  public static Drawable getContactPhoto(Context context, Uri uri, String name) {
    final InputStream inputStream = getContactPhotoStream(context, uri);
    final int         targetSize  = context.getResources().getDimensionPixelSize(R.dimen.contact_photo_target_size);

    if (inputStream != null) {
      try {
        return RoundedDrawable.fromBitmap(BitmapUtil.createScaledBitmap(inputStream,
                                                                        getContactPhotoStream(context, uri),
                                                                        targetSize,
                                                                        targetSize))
                              .setScaleType(ImageView.ScaleType.CENTER_CROP)
                              .setOval(true);
      } catch (BitmapDecodingException bde) {
        Log.w(TAG, bde);
      }
    }

    return getDefaultContactPhoto(context, name);
  }

  public static Drawable getGroupContactPhoto(Context context, @Nullable byte[] avatar) {
    if (avatar == null) return getDefaultGroupPhoto(context);

    return RoundedDrawable.fromBitmap(BitmapFactory.decodeByteArray(avatar, 0, avatar.length))
                          .setScaleType(ImageView.ScaleType.CENTER_CROP)
                          .setOval(true);
  }

  private static InputStream getContactPhotoStream(Context context, Uri uri) {
    if (VERSION.SDK_INT >= VERSION_CODES.ICE_CREAM_SANDWICH) {
      return ContactsContract.Contacts.openContactPhotoInputStream(context.getContentResolver(), uri, true);
    } else {
      return ContactsContract.Contacts.openContactPhotoInputStream(context.getContentResolver(), uri);
    }
  }

  private static class ExpandingLayerDrawable extends LayerDrawable {

    public ExpandingLayerDrawable(Drawable[] layers) {
      super(layers);
    }

    @Override
    public int getIntrinsicWidth() {
      return -1;
    }

    @Override
    public int getIntrinsicHeight() {
      return -1;
    }
  }
}


File: src/org/thoughtcrime/securesms/contacts/ContactSelectionListItem.java
package org.thoughtcrime.securesms.contacts;

import android.content.Context;
import android.support.annotation.Nullable;
import android.util.AttributeSet;
import android.view.View;
import android.widget.CheckBox;
import android.widget.ImageView;
import android.widget.RelativeLayout;
import android.widget.TextView;

import org.thoughtcrime.securesms.R;
import org.thoughtcrime.securesms.recipients.Recipient;
import org.thoughtcrime.securesms.recipients.RecipientFactory;

public class ContactSelectionListItem extends RelativeLayout implements Recipient.RecipientModifiedListener {

  private ImageView contactPhotoImage;
  private TextView  numberView;
  private TextView  nameView;
  private TextView  labelView;
  private CheckBox  checkBox;

  private long      id;
  private String    number;
  private Recipient recipient;

  public ContactSelectionListItem(Context context) {
    super(context);
  }

  public ContactSelectionListItem(Context context, AttributeSet attrs) {
    super(context, attrs);
  }

  public ContactSelectionListItem(Context context, AttributeSet attrs, int defStyleAttr) {
    super(context, attrs, defStyleAttr);
  }

  @Override
  protected void onFinishInflate() {
    this.contactPhotoImage = (ImageView) findViewById(R.id.contact_photo_image);
    this.numberView        = (TextView)  findViewById(R.id.number);
    this.labelView         = (TextView)  findViewById(R.id.label);
    this.nameView          = (TextView)  findViewById(R.id.name);
    this.checkBox          = (CheckBox)  findViewById(R.id.check_box);
  }

  public void set(long id, int type, String name, String number, String label, int color, boolean multiSelect) {
    this.id     = id;
    this.number = number;

    if (number != null) {
      this.recipient = RecipientFactory.getRecipientsFromString(getContext(), number, true)
                                       .getPrimaryRecipient();
    }

    this.nameView.setTextColor(color);
    this.numberView.setTextColor(color);

    setText(type, name, number, label);
    setContactPhotoImage(recipient);

    if (multiSelect) this.checkBox.setVisibility(View.VISIBLE);
    else             this.checkBox.setVisibility(View.GONE);
  }

  public void setChecked(boolean selected) {
    this.checkBox.setChecked(selected);
  }

  public void unbind() {
    if (recipient != null) {
      recipient.removeListener(this);
      recipient = null;
    }
  }

  private void setText(int type, String name, String number, String label) {
    if (number == null || number.isEmpty()) {
      this.nameView.setEnabled(false);
      this.numberView.setText("");
      this.labelView.setVisibility(View.GONE);
    } else if (type == ContactsDatabase.PUSH_TYPE) {
      this.numberView.setText(number);
      this.nameView.setEnabled(true);
      this.labelView.setVisibility(View.GONE);
    } else {
      this.numberView.setText(number);
      this.nameView.setEnabled(true);
      this.labelView.setText(label);
      this.labelView.setVisibility(View.VISIBLE);
    }

    this.nameView.setText(name);
  }

  private void setContactPhotoImage(@Nullable Recipient recipient) {
    if (recipient!= null) {
      contactPhotoImage.setImageDrawable(recipient.getContactPhoto());
      recipient.addListener(this);
    } else {
      contactPhotoImage.setImageDrawable(null);
    }
  }

  @Override
  public void onModified(final Recipient recipient) {
    if (this.recipient == recipient) {
      recipient.removeListener(this);
      this.contactPhotoImage.post(new Runnable() {
        @Override
        public void run() {
          contactPhotoImage.setImageDrawable(recipient.getContactPhoto());
        }
      });
    }
  }

  public long getContactId() {
    return id;
  }

  public String getNumber() {
    return number;
  }
}


File: src/org/thoughtcrime/securesms/database/MmsDatabase.java
/**
 * Copyright (C) 2011 Whisper Systems
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.thoughtcrime.securesms.database;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import android.net.Uri;
import android.support.annotation.NonNull;
import android.telephony.TelephonyManager;
import android.text.TextUtils;
import android.util.Log;
import android.util.Pair;

import com.google.i18n.phonenumbers.PhoneNumberUtil;

import org.thoughtcrime.securesms.ApplicationContext;
import org.thoughtcrime.securesms.R;
import org.thoughtcrime.securesms.crypto.MasterCipher;
import org.thoughtcrime.securesms.crypto.MasterSecret;
import org.thoughtcrime.securesms.database.documents.NetworkFailure;
import org.thoughtcrime.securesms.database.documents.NetworkFailureList;
import org.thoughtcrime.securesms.database.documents.IdentityKeyMismatch;
import org.thoughtcrime.securesms.database.documents.IdentityKeyMismatchList;
import org.thoughtcrime.securesms.database.model.DisplayRecord;
import org.thoughtcrime.securesms.database.model.MediaMmsMessageRecord;
import org.thoughtcrime.securesms.database.model.MessageRecord;
import org.thoughtcrime.securesms.database.model.NotificationMmsMessageRecord;
import org.thoughtcrime.securesms.jobs.TrimThreadJob;
import org.thoughtcrime.securesms.mms.IncomingMediaMessage;
import org.thoughtcrime.securesms.mms.OutgoingGroupMediaMessage;
import org.thoughtcrime.securesms.mms.OutgoingMediaMessage;
import org.thoughtcrime.securesms.mms.PartParser;
import org.thoughtcrime.securesms.mms.SlideDeck;
import org.thoughtcrime.securesms.mms.TextSlide;
import org.thoughtcrime.securesms.recipients.Recipient;
import org.thoughtcrime.securesms.recipients.RecipientFactory;
import org.thoughtcrime.securesms.recipients.RecipientFormattingException;
import org.thoughtcrime.securesms.recipients.Recipients;
import org.thoughtcrime.securesms.util.GroupUtil;
import org.thoughtcrime.securesms.util.JsonUtils;
import org.thoughtcrime.securesms.util.LRUCache;
import org.thoughtcrime.securesms.util.ListenableFutureTask;
import org.thoughtcrime.securesms.util.TextSecurePreferences;
import org.thoughtcrime.securesms.util.Util;
import org.whispersystems.jobqueue.JobManager;
import org.whispersystems.libaxolotl.InvalidMessageException;
import org.whispersystems.libaxolotl.util.guava.Optional;
import org.whispersystems.textsecure.api.util.InvalidNumberException;

import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.lang.ref.SoftReference;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;

import ws.com.google.android.mms.ContentType;
import ws.com.google.android.mms.InvalidHeaderValueException;
import ws.com.google.android.mms.MmsException;
import ws.com.google.android.mms.pdu.CharacterSets;
import ws.com.google.android.mms.pdu.EncodedStringValue;
import ws.com.google.android.mms.pdu.NotificationInd;
import ws.com.google.android.mms.pdu.PduBody;
import ws.com.google.android.mms.pdu.PduHeaders;
import ws.com.google.android.mms.pdu.PduPart;
import ws.com.google.android.mms.pdu.SendReq;

import static org.thoughtcrime.securesms.util.Util.canonicalizeNumber;
import static org.thoughtcrime.securesms.util.Util.canonicalizeNumberOrGroup;

// XXXX Clean up MMS efficiency:
// 1) We need to be careful about how much memory we're using for parts. SoftRefereences.
// 2) How many queries do we make?  calling getMediaMessageForId() from within an existing query
//    seems wasteful.

public class MmsDatabase extends MessagingDatabase {

  private static final String TAG = MmsDatabase.class.getSimpleName();

  public  static final String TABLE_NAME         = "mms";
          static final String DATE_SENT          = "date";
          static final String DATE_RECEIVED      = "date_received";
  public  static final String MESSAGE_BOX        = "msg_box";
  private static final String MESSAGE_ID         = "m_id";
  private static final String SUBJECT            = "sub";
  private static final String SUBJECT_CHARSET    = "sub_cs";
          static final String CONTENT_TYPE       = "ct_t";
          static final String CONTENT_LOCATION   = "ct_l";
          static final String EXPIRY             = "exp";
  private static final String MESSAGE_CLASS      = "m_cls";
  public  static final String MESSAGE_TYPE       = "m_type";
  private static final String MMS_VERSION        = "v";
          static final String MESSAGE_SIZE       = "m_size";
  private static final String PRIORITY           = "pri";
  private static final String READ_REPORT        = "rr";
  private static final String REPORT_ALLOWED     = "rpt_a";
  private static final String RESPONSE_STATUS    = "resp_st";
          static final String STATUS             = "st";
          static final String TRANSACTION_ID     = "tr_id";
  private static final String RETRIEVE_STATUS    = "retr_st";
  private static final String RETRIEVE_TEXT      = "retr_txt";
  private static final String RETRIEVE_TEXT_CS   = "retr_txt_cs";
  private static final String READ_STATUS        = "read_status";
  private static final String CONTENT_CLASS      = "ct_cls";
  private static final String RESPONSE_TEXT      = "resp_txt";
  private static final String DELIVERY_TIME      = "d_tm";
  private static final String DELIVERY_REPORT    = "d_rpt";
          static final String PART_COUNT         = "part_count";
          static final String NETWORK_FAILURE    = "network_failures";

  public static final String CREATE_TABLE = "CREATE TABLE " + TABLE_NAME + " (" + ID + " INTEGER PRIMARY KEY, "                          +
    THREAD_ID + " INTEGER, " + DATE_SENT + " INTEGER, " + DATE_RECEIVED + " INTEGER, " + MESSAGE_BOX + " INTEGER, " +
    READ + " INTEGER DEFAULT 0, " + MESSAGE_ID + " TEXT, " + SUBJECT + " TEXT, "                +
    SUBJECT_CHARSET + " INTEGER, " + BODY + " TEXT, " + PART_COUNT + " INTEGER, "               +
    CONTENT_TYPE + " TEXT, " + CONTENT_LOCATION + " TEXT, " + ADDRESS + " TEXT, "               +
    ADDRESS_DEVICE_ID + " INTEGER, "                                                            +
    EXPIRY + " INTEGER, " + MESSAGE_CLASS + " TEXT, " + MESSAGE_TYPE + " INTEGER, "             +
    MMS_VERSION + " INTEGER, " + MESSAGE_SIZE + " INTEGER, " + PRIORITY + " INTEGER, "          +
    READ_REPORT + " INTEGER, " + REPORT_ALLOWED + " INTEGER, " + RESPONSE_STATUS + " INTEGER, " +
    STATUS + " INTEGER, " + TRANSACTION_ID + " TEXT, " + RETRIEVE_STATUS + " INTEGER, "         +
    RETRIEVE_TEXT + " TEXT, " + RETRIEVE_TEXT_CS + " INTEGER, " + READ_STATUS + " INTEGER, "    +
    CONTENT_CLASS + " INTEGER, " + RESPONSE_TEXT + " TEXT, " + DELIVERY_TIME + " INTEGER, "     +
    RECEIPT_COUNT + " INTEGER DEFAULT 0, " + MISMATCHED_IDENTITIES + " TEXT DEFAULT NULL, "     +
    NETWORK_FAILURE + " TEXT DEFAULT NULL," + DELIVERY_REPORT + " INTEGER);";

  public static final String[] CREATE_INDEXS = {
    "CREATE INDEX IF NOT EXISTS mms_thread_id_index ON " + TABLE_NAME + " (" + THREAD_ID + ");",
    "CREATE INDEX IF NOT EXISTS mms_read_index ON " + TABLE_NAME + " (" + READ + ");",
    "CREATE INDEX IF NOT EXISTS mms_read_and_thread_id_index ON " + TABLE_NAME + "(" + READ + "," + THREAD_ID + ");",
    "CREATE INDEX IF NOT EXISTS mms_message_box_index ON " + TABLE_NAME + " (" + MESSAGE_BOX + ");",
    "CREATE INDEX IF NOT EXISTS mms_date_sent_index ON " + TABLE_NAME + " (" + DATE_SENT + ");"
  };

  private static final String[] MMS_PROJECTION = new String[] {
      ID, THREAD_ID, DATE_SENT + " * 1000 AS " + NORMALIZED_DATE_SENT,
      DATE_RECEIVED + " * 1000 AS " + NORMALIZED_DATE_RECEIVED,
      MESSAGE_BOX, READ, MESSAGE_ID, SUBJECT, SUBJECT_CHARSET, CONTENT_TYPE,
      CONTENT_LOCATION, EXPIRY, MESSAGE_CLASS, MESSAGE_TYPE, MMS_VERSION,
      MESSAGE_SIZE, PRIORITY, REPORT_ALLOWED, STATUS, TRANSACTION_ID, RETRIEVE_STATUS,
      RETRIEVE_TEXT, RETRIEVE_TEXT_CS, READ_STATUS, CONTENT_CLASS, RESPONSE_TEXT,
      DELIVERY_TIME, DELIVERY_REPORT, BODY, PART_COUNT, ADDRESS, ADDRESS_DEVICE_ID,
      RECEIPT_COUNT, MISMATCHED_IDENTITIES, NETWORK_FAILURE
  };

  public static final ExecutorService slideResolver = org.thoughtcrime.securesms.util.Util.newSingleThreadedLifoExecutor();
  private static final Map<String, SoftReference<SlideDeck>> slideCache =
      Collections.synchronizedMap(new LRUCache<String, SoftReference<SlideDeck>>(20));

  private final JobManager jobManager;

  public MmsDatabase(Context context, SQLiteOpenHelper databaseHelper) {
    super(context, databaseHelper);
    this.jobManager = ApplicationContext.getInstance(context).getJobManager();
  }

  @Override
  protected String getTableName() {
    return TABLE_NAME;
  }

  public int getMessageCountForThread(long threadId) {
    SQLiteDatabase db = databaseHelper.getReadableDatabase();
    Cursor cursor     = null;

    try {
      cursor = db.query(TABLE_NAME, new String[] {"COUNT(*)"}, THREAD_ID + " = ?", new String[] {threadId+""}, null, null, null);

      if (cursor != null && cursor.moveToFirst())
        return cursor.getInt(0);
    } finally {
      if (cursor != null)
        cursor.close();
    }

    return 0;
  }

  public void addFailures(long messageId, List<NetworkFailure> failure) {
    try {
      addToDocument(messageId, NETWORK_FAILURE, failure, NetworkFailureList.class);
    } catch (IOException e) {
      Log.w(TAG, e);
    }
  }

  public void removeFailure(long messageId, NetworkFailure failure) {
    try {
      removeFromDocument(messageId, NETWORK_FAILURE, failure, NetworkFailureList.class);
    } catch (IOException e) {
      Log.w(TAG, e);
    }
  }

  public void incrementDeliveryReceiptCount(String address, long timestamp) {
    MmsAddressDatabase addressDatabase = DatabaseFactory.getMmsAddressDatabase(context);
    SQLiteDatabase     database        = databaseHelper.getWritableDatabase();
    Cursor             cursor          = null;

    try {
      cursor = database.query(TABLE_NAME, new String[] {ID, THREAD_ID, MESSAGE_BOX}, DATE_SENT + " = ?", new String[] {String.valueOf(timestamp / 1000)}, null, null, null, null);

      while (cursor.moveToNext()) {
        if (Types.isOutgoingMessageType(cursor.getLong(cursor.getColumnIndexOrThrow(MESSAGE_BOX)))) {
          List<String> addresses = addressDatabase.getAddressesForId(cursor.getLong(cursor.getColumnIndexOrThrow(ID)));

          for (String storedAddress : addresses) {
            try {
              String ourAddress   = canonicalizeNumber(context, address);
              String theirAddress = canonicalizeNumberOrGroup(context, storedAddress);

              if (ourAddress.equals(theirAddress) || GroupUtil.isEncodedGroup(theirAddress)) {
                long id       = cursor.getLong(cursor.getColumnIndexOrThrow(ID));
                long threadId = cursor.getLong(cursor.getColumnIndexOrThrow(THREAD_ID));

                database.execSQL("UPDATE " + TABLE_NAME + " SET " +
                                 RECEIPT_COUNT + " = " + RECEIPT_COUNT + " + 1 WHERE " + ID + " = ?",
                                 new String[] {String.valueOf(id)});

                notifyConversationListeners(threadId);
              }
            } catch (InvalidNumberException e) {
              Log.w("MmsDatabase", e);
            }
          }
        }
      }
    } finally {
      if (cursor != null)
        cursor.close();
    }
  }

  public long getThreadIdForMessage(long id) {
    String sql        = "SELECT " + THREAD_ID + " FROM " + TABLE_NAME + " WHERE " + ID + " = ?";
    String[] sqlArgs  = new String[] {id+""};
    SQLiteDatabase db = databaseHelper.getReadableDatabase();

    Cursor cursor = null;

    try {
      cursor = db.rawQuery(sql, sqlArgs);
      if (cursor != null && cursor.moveToFirst())
        return cursor.getLong(0);
      else
        return -1;
    } finally {
      if (cursor != null)
        cursor.close();
    }
  }

  private long getThreadIdFor(IncomingMediaMessage retrieved) throws RecipientFormattingException, MmsException {
    if (retrieved.getGroupId() != null) {
      Recipients groupRecipients = RecipientFactory.getRecipientsFromString(context, retrieved.getGroupId(), true);
      return DatabaseFactory.getThreadDatabase(context).getThreadIdFor(groupRecipients);
    }

    try {
      PduHeaders headers = retrieved.getPduHeaders();
      Set<String> group = new HashSet<String>();

      EncodedStringValue   encodedFrom   = headers.getEncodedStringValue(PduHeaders.FROM);
      EncodedStringValue[] encodedCcList = headers.getEncodedStringValues(PduHeaders.CC);
      EncodedStringValue[] encodedToList = headers.getEncodedStringValues(PduHeaders.TO);

      if (encodedFrom == null) {
        throw new MmsException("FROM value in PduHeaders did not exist.");
      }

      group.add(new String(encodedFrom.getTextString(), CharacterSets.MIMENAME_ISO_8859_1));

      TelephonyManager telephonyManager = (TelephonyManager) context.getSystemService(Context.TELEPHONY_SERVICE);
      String           localNumber      = telephonyManager.getLine1Number();

      if (localNumber == null) {
          localNumber = TextSecurePreferences.getLocalNumber(context);
      }

      if (encodedCcList != null) {
        for (EncodedStringValue encodedCc : encodedCcList) {
          String cc = new String(encodedCc.getTextString(), CharacterSets.MIMENAME_ISO_8859_1);

          PhoneNumberUtil.MatchType match;

          if (localNumber == null) match = PhoneNumberUtil.MatchType.NO_MATCH;
          else                     match = PhoneNumberUtil.getInstance().isNumberMatch(localNumber, cc);

          if (match == PhoneNumberUtil.MatchType.NO_MATCH ||
              match == PhoneNumberUtil.MatchType.NOT_A_NUMBER)
          {
              group.add(cc);
          }
        }
      }

      if (encodedToList != null && (encodedToList.length > 1 || group.size() > 1)) {
        for (EncodedStringValue encodedTo : encodedToList) {
          String to = new String(encodedTo.getTextString(), CharacterSets.MIMENAME_ISO_8859_1);

          PhoneNumberUtil.MatchType match;

          if (localNumber == null) match = PhoneNumberUtil.MatchType.NO_MATCH;
          else                     match = PhoneNumberUtil.getInstance().isNumberMatch(localNumber, to);

          if (match == PhoneNumberUtil.MatchType.NO_MATCH ||
              match == PhoneNumberUtil.MatchType.NOT_A_NUMBER)
          {
            group.add(to);
          }
        }
      }

      String recipientsList = Util.join(group, ",");
      Recipients recipients = RecipientFactory.getRecipientsFromString(context, recipientsList, false);
      return DatabaseFactory.getThreadDatabase(context).getThreadIdFor(recipients);
    } catch (UnsupportedEncodingException e) {
      throw new AssertionError(e);
    }
  }

  private long getThreadIdFor(@NonNull NotificationInd notification) {
    String fromString = notification.getFrom() != null && notification.getFrom().getTextString() != null
                      ? Util.toIsoString(notification.getFrom().getTextString())
                      : "";
    Recipients recipients = RecipientFactory.getRecipientsFromString(context, fromString, false);
    if (recipients.isEmpty()) recipients = RecipientFactory.getRecipientsFor(context, Recipient.getUnknownRecipient(context), false);
    return DatabaseFactory.getThreadDatabase(context).getThreadIdFor(recipients);
  }

  public Cursor getMessage(long messageId) {
    SQLiteDatabase db = databaseHelper.getReadableDatabase();
    Cursor cursor = db.query(TABLE_NAME, MMS_PROJECTION, ID_WHERE, new String[] {messageId+""},
                             null, null, null);
    setNotifyConverationListeners(cursor, getThreadIdForMessage(messageId));
    return cursor;
  }

  public void updateResponseStatus(long messageId, int status) {
    SQLiteDatabase database     = databaseHelper.getWritableDatabase();
    ContentValues contentValues = new ContentValues();
    contentValues.put(RESPONSE_STATUS, status);

    database.update(TABLE_NAME, contentValues, ID_WHERE, new String[] {messageId + ""});
  }

  private void updateMailboxBitmask(long id, long maskOff, long maskOn) {
    SQLiteDatabase db = databaseHelper.getWritableDatabase();
    db.execSQL("UPDATE " + TABLE_NAME +
                   " SET " + MESSAGE_BOX + " = (" + MESSAGE_BOX + " & " + (Types.TOTAL_MASK - maskOff) + " | " + maskOn + " )" +
                   " WHERE " + ID + " = ?", new String[] {id + ""});
  }

  public void markAsOutbox(long messageId) {
    updateMailboxBitmask(messageId, Types.BASE_TYPE_MASK, Types.BASE_OUTBOX_TYPE);
    notifyConversationListeners(getThreadIdForMessage(messageId));
  }

  public void markAsForcedSms(long messageId) {
    updateMailboxBitmask(messageId, Types.PUSH_MESSAGE_BIT, Types.MESSAGE_FORCE_SMS_BIT);
    notifyConversationListeners(getThreadIdForMessage(messageId));
  }

  public void markAsPendingInsecureSmsFallback(long messageId) {
    updateMailboxBitmask(messageId, Types.BASE_TYPE_MASK, Types.BASE_PENDING_INSECURE_SMS_FALLBACK);
    notifyConversationListeners(getThreadIdForMessage(messageId));
  }

  public void markAsSending(long messageId) {
    updateMailboxBitmask(messageId, Types.BASE_TYPE_MASK, Types.BASE_SENDING_TYPE);
    notifyConversationListeners(getThreadIdForMessage(messageId));
  }

  public void markAsSentFailed(long messageId) {
    updateMailboxBitmask(messageId, Types.BASE_TYPE_MASK, Types.BASE_SENT_FAILED_TYPE);
    notifyConversationListeners(getThreadIdForMessage(messageId));
  }

  public void markAsSent(long messageId, byte[] mmsId, long status) {
    SQLiteDatabase database     = databaseHelper.getWritableDatabase();
    ContentValues contentValues = new ContentValues();
    contentValues.put(RESPONSE_STATUS, status);
    contentValues.put(MESSAGE_ID, new String(mmsId));

    database.update(TABLE_NAME, contentValues, ID_WHERE, new String[] {messageId+""});
    updateMailboxBitmask(messageId, Types.BASE_TYPE_MASK, Types.BASE_SENT_TYPE);
    notifyConversationListeners(getThreadIdForMessage(messageId));
  }

  public void markDownloadState(long messageId, long state) {
    SQLiteDatabase database     = databaseHelper.getWritableDatabase();
    ContentValues contentValues = new ContentValues();
    contentValues.put(STATUS, state);

    database.update(TABLE_NAME, contentValues, ID_WHERE, new String[] {messageId + ""});
    notifyConversationListeners(getThreadIdForMessage(messageId));
  }

  public void markDeliveryStatus(long messageId, int status) {
    SQLiteDatabase database     = databaseHelper.getWritableDatabase();
    ContentValues contentValues = new ContentValues();
    contentValues.put(STATUS, status);

    database.update(TABLE_NAME, contentValues, ID_WHERE, new String[] {messageId + ""});
    notifyConversationListeners(getThreadIdForMessage(messageId));
  }

  public void markAsNoSession(long messageId, long threadId) {
    updateMailboxBitmask(messageId, Types.ENCRYPTION_MASK, Types.ENCRYPTION_REMOTE_NO_SESSION_BIT);
    notifyConversationListeners(threadId);
  }

  public void markAsSecure(long messageId) {
    updateMailboxBitmask(messageId, 0, Types.SECURE_MESSAGE_BIT);
  }

  public void markAsInsecure(long messageId) {
    updateMailboxBitmask(messageId, Types.SECURE_MESSAGE_BIT, 0);
  }

  public void markAsPush(long messageId) {
    updateMailboxBitmask(messageId, 0, Types.PUSH_MESSAGE_BIT);
  }

  public void markAsDecryptFailed(long messageId, long threadId) {
    updateMailboxBitmask(messageId, Types.ENCRYPTION_MASK, Types.ENCRYPTION_REMOTE_FAILED_BIT);
    notifyConversationListeners(threadId);
  }

  public void markAsDecryptDuplicate(long messageId, long threadId) {
    updateMailboxBitmask(messageId, Types.ENCRYPTION_MASK, Types.ENCRYPTION_REMOTE_DUPLICATE_BIT);
    notifyConversationListeners(threadId);
  }

  public void markAsLegacyVersion(long messageId, long threadId) {
    updateMailboxBitmask(messageId, Types.ENCRYPTION_MASK, Types.ENCRYPTION_REMOTE_LEGACY_BIT);
    notifyConversationListeners(threadId);
  }

  public void setMessagesRead(long threadId) {
    SQLiteDatabase database     = databaseHelper.getWritableDatabase();
    ContentValues contentValues = new ContentValues();
    contentValues.put(READ, 1);

    database.update(TABLE_NAME, contentValues, THREAD_ID + " = ?", new String[] {threadId + ""});
  }

  public void setAllMessagesRead() {
    SQLiteDatabase database     = databaseHelper.getWritableDatabase();
    ContentValues contentValues = new ContentValues();
    contentValues.put(READ, 1);

    database.update(TABLE_NAME, contentValues, null, null);
  }

  public Optional<NotificationInd> getNotification(long messageId) {
    SQLiteDatabase     db              = databaseHelper.getReadableDatabase();
    MmsAddressDatabase addressDatabase = DatabaseFactory.getMmsAddressDatabase(context);

    Cursor cursor = null;

    try {
      cursor = db.query(TABLE_NAME, MMS_PROJECTION, ID_WHERE, new String[] {String.valueOf(messageId)}, null, null, null);

      if (cursor != null && cursor.moveToNext()) {
        PduHeaders headers = getHeadersFromCursor(cursor);
        addressDatabase.getAddressesForId(messageId, headers);

        return Optional.of(new NotificationInd(headers));
      } else {
        return Optional.absent();
      }
    } catch (InvalidHeaderValueException e) {
      Log.w("MmsDatabase", e);
      return Optional.absent();
    } finally {
      if (cursor != null)
        cursor.close();
    }
  }

  public SendReq getOutgoingMessage(MasterSecret masterSecret, long messageId)
      throws MmsException, NoSuchMessageException
  {
    MmsAddressDatabase addr         = DatabaseFactory.getMmsAddressDatabase(context);
    PartDatabase       partDatabase = DatabaseFactory.getPartDatabase(context);
    SQLiteDatabase     database     = databaseHelper.getReadableDatabase();
    MasterCipher       masterCipher = new MasterCipher(masterSecret);
    Cursor             cursor       = null;

    String   selection     = ID_WHERE;
    String[] selectionArgs = new String[]{String.valueOf(messageId)};

    try {
      cursor = database.query(TABLE_NAME, MMS_PROJECTION, selection, selectionArgs, null, null, null);

      if (cursor != null && cursor.moveToNext()) {
        long       outboxType  = cursor.getLong(cursor.getColumnIndexOrThrow(MESSAGE_BOX));
        String     messageText = cursor.getString(cursor.getColumnIndexOrThrow(BODY));
        long       timestamp   = cursor.getLong(cursor.getColumnIndexOrThrow(NORMALIZED_DATE_SENT));
        PduHeaders headers     = getHeadersFromCursor(cursor);
        addr.getAddressesForId(messageId, headers);

        PduBody body = getPartsAsBody(partDatabase.getParts(messageId));

        try {
          if (!TextUtils.isEmpty(messageText) && Types.isSymmetricEncryption(outboxType)) {
            body.addPart(new TextSlide(context, masterCipher.decryptBody(messageText)).getPart());
          } else if (!TextUtils.isEmpty(messageText)) {
            body.addPart(new TextSlide(context, messageText).getPart());
          }
        } catch (InvalidMessageException e) {
          Log.w("MmsDatabase", e);
        }

        return new SendReq(headers, body, messageId, outboxType, timestamp);
      }

      throw new NoSuchMessageException("No record found for id: " + messageId);
    } finally {
      if (cursor != null)
        cursor.close();
    }
  }

  public Reader getNotificationsWithDownloadState(MasterSecret masterSecret, long state) {
    SQLiteDatabase database   = databaseHelper.getReadableDatabase();
    String selection          = STATUS + " = ?";
    String[] selectionArgs    = new String[]{state + ""};

    Cursor cursor = database.query(TABLE_NAME, MMS_PROJECTION, selection, selectionArgs, null, null, null);
    return new Reader(masterSecret, cursor);
  }

  public long copyMessageInbox(MasterSecret masterSecret, long messageId) throws MmsException {
    try {
      SendReq request = getOutgoingMessage(masterSecret, messageId);
      ContentValues contentValues = getContentValuesFromHeader(request.getPduHeaders());

      contentValues.put(MESSAGE_BOX, Types.BASE_INBOX_TYPE | Types.SECURE_MESSAGE_BIT | Types.ENCRYPTION_SYMMETRIC_BIT);
      contentValues.put(THREAD_ID, getThreadIdForMessage(messageId));
      contentValues.put(READ, 1);
      contentValues.put(DATE_RECEIVED, contentValues.getAsLong(DATE_SENT));

      return insertMediaMessage(masterSecret, request.getPduHeaders(),
                                request.getBody(), contentValues);
    } catch (NoSuchMessageException e) {
      throw new MmsException(e);
    }
  }

  private Pair<Long, Long> insertMessageInbox(MasterSecret masterSecret, IncomingMediaMessage retrieved,
                                              String contentLocation, long threadId, long mailbox)
      throws MmsException
  {
    PduHeaders    headers       = retrieved.getPduHeaders();
    ContentValues contentValues = getContentValuesFromHeader(headers);
    boolean       unread        = org.thoughtcrime.securesms.util.Util.isDefaultSmsProvider(context) ||
                                  ((mailbox & Types.SECURE_MESSAGE_BIT) != 0);

    if (threadId == -1 || retrieved.isGroupMessage()) {
      try {
        threadId = getThreadIdFor(retrieved);
      } catch (RecipientFormattingException e) {
        Log.w("MmsDatabase", e);
        if (threadId == -1)
          throw new MmsException(e);
      }
    }

    contentValues.put(MESSAGE_BOX, mailbox);
    contentValues.put(THREAD_ID, threadId);
    contentValues.put(CONTENT_LOCATION, contentLocation);
    contentValues.put(STATUS, Status.DOWNLOAD_INITIALIZED);
    contentValues.put(DATE_RECEIVED, System.currentTimeMillis() / 1000);
    contentValues.put(READ, unread ? 0 : 1);

    if (!contentValues.containsKey(DATE_SENT)) {
      contentValues.put(DATE_SENT, contentValues.getAsLong(DATE_RECEIVED));
    }

    long messageId = insertMediaMessage(masterSecret, retrieved.getPduHeaders(),
                                        retrieved.getBody(), contentValues);

    if (unread) {
      DatabaseFactory.getThreadDatabase(context).setUnread(threadId);
    }

    DatabaseFactory.getThreadDatabase(context).update(threadId);
    notifyConversationListeners(threadId);
    jobManager.add(new TrimThreadJob(context, threadId));

    return new Pair<>(messageId, threadId);
  }

  public Pair<Long, Long> insertMessageInbox(MasterSecret masterSecret,
                                             IncomingMediaMessage retrieved,
                                             String contentLocation, long threadId)
      throws MmsException
  {
    return insertMessageInbox(masterSecret, retrieved, contentLocation, threadId,
                              Types.BASE_INBOX_TYPE | Types.ENCRYPTION_SYMMETRIC_BIT |
                              (retrieved.isPushMessage() ? Types.PUSH_MESSAGE_BIT : 0));
  }

  public Pair<Long, Long> insertSecureMessageInbox(MasterSecret masterSecret,
                                                   IncomingMediaMessage retrieved,
                                                   String contentLocation, long threadId)
      throws MmsException
  {
    return insertMessageInbox(masterSecret, retrieved, contentLocation, threadId,
                              Types.BASE_INBOX_TYPE | Types.SECURE_MESSAGE_BIT |
                              Types.ENCRYPTION_REMOTE_BIT);
  }

  public Pair<Long, Long> insertSecureDecryptedMessageInbox(MasterSecret masterSecret,
                                                            IncomingMediaMessage retrieved,
                                                            long threadId)
      throws MmsException
  {
    return insertMessageInbox(masterSecret, retrieved, "", threadId,
                              Types.BASE_INBOX_TYPE | Types.SECURE_MESSAGE_BIT |
                              Types.ENCRYPTION_SYMMETRIC_BIT |
                              (retrieved.isPushMessage() ? Types.PUSH_MESSAGE_BIT : 0));
  }

  public Pair<Long, Long> insertMessageInbox(@NonNull NotificationInd notification) {
    SQLiteDatabase     db              = databaseHelper.getWritableDatabase();
    MmsAddressDatabase addressDatabase = DatabaseFactory.getMmsAddressDatabase(context);
    long               threadId        = getThreadIdFor(notification);
    PduHeaders         headers         = notification.getPduHeaders();
    ContentValues      contentValues   = getContentValuesFromHeader(headers);

    Log.w(TAG, "Message received type: " + headers.getOctet(PduHeaders.MESSAGE_TYPE));

    contentValues.put(MESSAGE_BOX, Types.BASE_INBOX_TYPE);
    contentValues.put(THREAD_ID, threadId);
    contentValues.put(STATUS, Status.DOWNLOAD_INITIALIZED);
    contentValues.put(DATE_RECEIVED, System.currentTimeMillis() / 1000);
    contentValues.put(READ, Util.isDefaultSmsProvider(context) ? 0 : 1);

    if (!contentValues.containsKey(DATE_SENT))
      contentValues.put(DATE_SENT, contentValues.getAsLong(DATE_RECEIVED));

    long messageId = db.insert(TABLE_NAME, null, contentValues);
    addressDatabase.insertAddressesForId(messageId, headers);

    return new Pair<>(messageId, threadId);
  }

  public void markIncomingNotificationReceived(long threadId) {
    notifyConversationListeners(threadId);
    DatabaseFactory.getThreadDatabase(context).update(threadId);

    if (org.thoughtcrime.securesms.util.Util.isDefaultSmsProvider(context)) {
      DatabaseFactory.getThreadDatabase(context).setUnread(threadId);
    }

    jobManager.add(new TrimThreadJob(context, threadId));
  }

  public long insertMessageOutbox(MasterSecret masterSecret, OutgoingMediaMessage message,
                                  long threadId, boolean forceSms, long timestamp)
      throws MmsException
  {
    long type = Types.BASE_OUTBOX_TYPE | Types.ENCRYPTION_SYMMETRIC_BIT;

    if (message.isSecure()) type |= Types.SECURE_MESSAGE_BIT;
    if (forceSms)           type |= Types.MESSAGE_FORCE_SMS_BIT;

    if (message.isGroup()) {
      if      (((OutgoingGroupMediaMessage)message).isGroupUpdate()) type |= Types.GROUP_UPDATE_BIT;
      else if (((OutgoingGroupMediaMessage)message).isGroupQuit())   type |= Types.GROUP_QUIT_BIT;
    }

    SendReq sendRequest = new SendReq();
    sendRequest.setDate(timestamp / 1000L);
    sendRequest.setBody(message.getPduBody());
    sendRequest.setContentType(ContentType.MULTIPART_MIXED.getBytes());

    String[]             recipientsArray = message.getRecipients().toNumberStringArray(true);
    EncodedStringValue[] encodedNumbers  = EncodedStringValue.encodeStrings(recipientsArray);

    if (message.getRecipients().isSingleRecipient()) {
      sendRequest.setTo(encodedNumbers);
    } else if (message.getDistributionType() == ThreadDatabase.DistributionTypes.BROADCAST) {
      sendRequest.setBcc(encodedNumbers);
    } else if (message.getDistributionType() == ThreadDatabase.DistributionTypes.CONVERSATION  ||
               message.getDistributionType() == 0)
    {
      sendRequest.setTo(encodedNumbers);
    }

    PduHeaders    headers       = sendRequest.getPduHeaders();
    ContentValues contentValues = getContentValuesFromHeader(headers);

    contentValues.put(MESSAGE_BOX, type);
    contentValues.put(THREAD_ID, threadId);
    contentValues.put(READ, 1);
    contentValues.put(DATE_RECEIVED, contentValues.getAsLong(DATE_SENT));
    contentValues.remove(ADDRESS);

    long messageId = insertMediaMessage(masterSecret, sendRequest.getPduHeaders(),
                                        sendRequest.getBody(), contentValues);
    jobManager.add(new TrimThreadJob(context, threadId));

    return messageId;
  }

  private long insertMediaMessage(MasterSecret masterSecret,
                                  PduHeaders headers,
                                  PduBody body,
                                  ContentValues contentValues)
      throws MmsException
  {
    SQLiteDatabase     db              = databaseHelper.getWritableDatabase();
    PartDatabase       partsDatabase   = DatabaseFactory.getPartDatabase(context);
    MmsAddressDatabase addressDatabase = DatabaseFactory.getMmsAddressDatabase(context);

    if (Types.isSymmetricEncryption(contentValues.getAsLong(MESSAGE_BOX))) {
      String messageText = PartParser.getMessageText(body);
      body               = PartParser.getSupportedMediaParts(body);

      if (!TextUtils.isEmpty(messageText)) {
        contentValues.put(BODY, new MasterCipher(masterSecret).encryptBody(messageText));
      }
    }

    contentValues.put(PART_COUNT, PartParser.getSupportedMediaPartCount(body));

    db.beginTransaction();
    try {
      long messageId = db.insert(TABLE_NAME, null, contentValues);

      addressDatabase.insertAddressesForId(messageId, headers);
      partsDatabase.insertParts(masterSecret, messageId, body);

      notifyConversationListeners(contentValues.getAsLong(THREAD_ID));
      DatabaseFactory.getThreadDatabase(context).update(contentValues.getAsLong(THREAD_ID));
      db.setTransactionSuccessful();
      return messageId;
    } finally {
      db.endTransaction();
    }

  }

  public boolean delete(long messageId) {
    long threadId                   = getThreadIdForMessage(messageId);
    MmsAddressDatabase addrDatabase = DatabaseFactory.getMmsAddressDatabase(context);
    PartDatabase partDatabase       = DatabaseFactory.getPartDatabase(context);
    partDatabase.deleteParts(messageId);
    addrDatabase.deleteAddressesForId(messageId);

    SQLiteDatabase database = databaseHelper.getWritableDatabase();
    database.delete(TABLE_NAME, ID_WHERE, new String[] {messageId+""});
    boolean threadDeleted = DatabaseFactory.getThreadDatabase(context).update(threadId);
    notifyConversationListeners(threadId);
    return threadDeleted;
  }

  public void deleteThread(long threadId) {
    Set<Long> singleThreadSet = new HashSet<Long>();
    singleThreadSet.add(threadId);
    deleteThreads(singleThreadSet);
  }

  /*package*/ void deleteThreads(Set<Long> threadIds) {
    SQLiteDatabase db = databaseHelper.getWritableDatabase();
    String where      = "";
    Cursor cursor     = null;

    for (long threadId : threadIds) {
      where += THREAD_ID + " = '" + threadId + "' OR ";
    }

    where = where.substring(0, where.length() - 4);

    try {
      cursor = db.query(TABLE_NAME, new String[] {ID}, where, null, null, null, null);

      while (cursor != null && cursor.moveToNext()) {
        delete(cursor.getLong(0));
      }

    } finally {
      if (cursor != null)
        cursor.close();
    }
  }

  /*package*/void deleteMessagesInThreadBeforeDate(long threadId, long date) {
    date          = date / 1000;
    Cursor cursor = null;

    try {
      SQLiteDatabase db = databaseHelper.getReadableDatabase();
      String where      = THREAD_ID + " = ? AND (CASE (" + MESSAGE_BOX + " & " + Types.BASE_TYPE_MASK + ") ";

      for (long outgoingType : Types.OUTGOING_MESSAGE_TYPES) {
        where += " WHEN " + outgoingType + " THEN " + DATE_SENT + " < " + date;
      }

      where += (" ELSE " + DATE_RECEIVED + " < " + date + " END)");

      Log.w("MmsDatabase", "Executing trim query: " + where);
      cursor = db.query(TABLE_NAME, new String[] {ID}, where, new String[] {threadId+""}, null, null, null);

      while (cursor != null && cursor.moveToNext()) {
        Log.w("MmsDatabase", "Trimming: " + cursor.getLong(0));
        delete(cursor.getLong(0));
      }

    } finally {
      if (cursor != null)
        cursor.close();
    }
  }


  public void deleteAllThreads() {
    DatabaseFactory.getPartDatabase(context).deleteAllParts();
    DatabaseFactory.getMmsAddressDatabase(context).deleteAllAddresses();

    SQLiteDatabase database = databaseHelper.getWritableDatabase();
    database.delete(TABLE_NAME, null, null);
  }

  public Cursor getCarrierMmsInformation(String apn) {
    Uri uri                = Uri.withAppendedPath(Uri.parse("content://telephony/carriers"), "current");
    String selection       = TextUtils.isEmpty(apn) ? null : "apn = ?";
    String[] selectionArgs = TextUtils.isEmpty(apn) ? null : new String[] {apn.trim()};

    try {
      return context.getContentResolver().query(uri, null, selection, selectionArgs, null);
    } catch (NullPointerException npe) {
      // NOTE - This is dumb, but on some devices there's an NPE in the Android framework
      // for the provider of this call, which gets rethrown back to here through a binder
      // call.
      throw new IllegalArgumentException(npe);
    }
  }

  private PduHeaders getHeadersFromCursor(Cursor cursor) throws InvalidHeaderValueException {
    PduHeaders headers    = new PduHeaders();
    PduHeadersBuilder phb = new PduHeadersBuilder(headers, cursor);

    phb.add(RETRIEVE_TEXT, RETRIEVE_TEXT_CS, PduHeaders.RETRIEVE_TEXT);
    phb.add(SUBJECT, SUBJECT_CHARSET, PduHeaders.SUBJECT);
    phb.addText(CONTENT_LOCATION, PduHeaders.CONTENT_LOCATION);
    phb.addText(CONTENT_TYPE, PduHeaders.CONTENT_TYPE);
    phb.addText(MESSAGE_CLASS, PduHeaders.MESSAGE_CLASS);
    phb.addText(MESSAGE_ID, PduHeaders.MESSAGE_ID);
    phb.addText(RESPONSE_TEXT, PduHeaders.RESPONSE_TEXT);
    phb.addText(TRANSACTION_ID, PduHeaders.TRANSACTION_ID);
    phb.addOctet(CONTENT_CLASS, PduHeaders.CONTENT_CLASS);
    phb.addOctet(DELIVERY_REPORT, PduHeaders.DELIVERY_REPORT);
    phb.addOctet(MESSAGE_TYPE, PduHeaders.MESSAGE_TYPE);
    phb.addOctet(MMS_VERSION, PduHeaders.MMS_VERSION);
    phb.addOctet(PRIORITY, PduHeaders.PRIORITY);
    phb.addOctet(READ_STATUS, PduHeaders.READ_STATUS);
    phb.addOctet(REPORT_ALLOWED, PduHeaders.REPORT_ALLOWED);
    phb.addOctet(RETRIEVE_STATUS, PduHeaders.RETRIEVE_STATUS);
    phb.addOctet(STATUS, PduHeaders.STATUS);
    phb.addLong(NORMALIZED_DATE_SENT, PduHeaders.DATE);
    phb.addLong(DELIVERY_TIME, PduHeaders.DELIVERY_TIME);
    phb.addLong(EXPIRY, PduHeaders.EXPIRY);
    phb.addLong(MESSAGE_SIZE, PduHeaders.MESSAGE_SIZE);

    headers.setLongInteger(headers.getLongInteger(PduHeaders.DATE) / 1000L, PduHeaders.DATE);

    return headers;
  }

  private ContentValues getContentValuesFromHeader(PduHeaders headers) {
    ContentValues contentValues = new ContentValues();
    ContentValuesBuilder cvb    = new ContentValuesBuilder(contentValues);

    cvb.add(RETRIEVE_TEXT, RETRIEVE_TEXT_CS, headers.getEncodedStringValue(PduHeaders.RETRIEVE_TEXT));
    cvb.add(SUBJECT, SUBJECT_CHARSET, headers.getEncodedStringValue(PduHeaders.SUBJECT));
    cvb.add(CONTENT_LOCATION, headers.getTextString(PduHeaders.CONTENT_LOCATION));
    cvb.add(CONTENT_TYPE, headers.getTextString(PduHeaders.CONTENT_TYPE));
    cvb.add(MESSAGE_CLASS, headers.getTextString(PduHeaders.MESSAGE_CLASS));
    cvb.add(MESSAGE_ID, headers.getTextString(PduHeaders.MESSAGE_ID));
    cvb.add(RESPONSE_TEXT, headers.getTextString(PduHeaders.RESPONSE_TEXT));
    cvb.add(TRANSACTION_ID, headers.getTextString(PduHeaders.TRANSACTION_ID));
    cvb.add(CONTENT_CLASS, headers.getOctet(PduHeaders.CONTENT_CLASS));
    cvb.add(DELIVERY_REPORT, headers.getOctet(PduHeaders.DELIVERY_REPORT));
    cvb.add(MESSAGE_TYPE, headers.getOctet(PduHeaders.MESSAGE_TYPE));
    cvb.add(MMS_VERSION, headers.getOctet(PduHeaders.MMS_VERSION));
    cvb.add(PRIORITY, headers.getOctet(PduHeaders.PRIORITY));
    cvb.add(READ_REPORT, headers.getOctet(PduHeaders.READ_REPORT));
    cvb.add(READ_STATUS, headers.getOctet(PduHeaders.READ_STATUS));
    cvb.add(REPORT_ALLOWED, headers.getOctet(PduHeaders.REPORT_ALLOWED));
    cvb.add(RETRIEVE_STATUS, headers.getOctet(PduHeaders.RETRIEVE_STATUS));
    cvb.add(STATUS, headers.getOctet(PduHeaders.STATUS));
    cvb.add(DATE_SENT, headers.getLongInteger(PduHeaders.DATE));
    cvb.add(DELIVERY_TIME, headers.getLongInteger(PduHeaders.DELIVERY_TIME));
    cvb.add(EXPIRY, headers.getLongInteger(PduHeaders.EXPIRY));
    cvb.add(MESSAGE_SIZE, headers.getLongInteger(PduHeaders.MESSAGE_SIZE));

    if (headers.getEncodedStringValue(PduHeaders.FROM) != null)
      cvb.add(ADDRESS, headers.getEncodedStringValue(PduHeaders.FROM).getTextString());
    else
      cvb.add(ADDRESS, null);

    return cvb.getContentValues();
  }

  public Reader readerFor(MasterSecret masterSecret, Cursor cursor) {
    return new Reader(masterSecret, cursor);
  }

  public static class Status {
    public static final int DOWNLOAD_INITIALIZED     = 1;
    public static final int DOWNLOAD_NO_CONNECTIVITY = 2;
    public static final int DOWNLOAD_CONNECTING      = 3;
    public static final int DOWNLOAD_SOFT_FAILURE    = 4;
    public static final int DOWNLOAD_HARD_FAILURE    = 5;
    public static final int DOWNLOAD_APN_UNAVAILABLE = 6;

    public static boolean isDisplayDownloadButton(int status) {
      return
          status == DOWNLOAD_INITIALIZED     ||
          status == DOWNLOAD_NO_CONNECTIVITY ||
          status == DOWNLOAD_SOFT_FAILURE;
    }

    public static String getLabelForStatus(Context context, int status) {
      switch (status) {
        case DOWNLOAD_CONNECTING:      return context.getString(R.string.MmsDatabase_connecting_to_mms_server);
        case DOWNLOAD_INITIALIZED:     return context.getString(R.string.MmsDatabase_downloading_mms);
        case DOWNLOAD_HARD_FAILURE:    return context.getString(R.string.MmsDatabase_mms_download_failed);
        case DOWNLOAD_APN_UNAVAILABLE: return context.getString(R.string.MmsDatabase_mms_pending_download);
      }

      return context.getString(R.string.MmsDatabase_downloading);
    }

    public static boolean isHardError(int status) {
      return status == DOWNLOAD_HARD_FAILURE;
    }
  }

  public class Reader {

    private final Cursor       cursor;
    private final MasterSecret masterSecret;
    private final MasterCipher masterCipher;

    public Reader(MasterSecret masterSecret, Cursor cursor) {
      this.cursor       = cursor;
      this.masterSecret = masterSecret;

      if (masterSecret != null) masterCipher = new MasterCipher(masterSecret);
      else                      masterCipher = null;
    }

    public MessageRecord getNext() {
      if (cursor == null || !cursor.moveToNext())
        return null;

      return getCurrent();
    }

    public MessageRecord getCurrent() {
      long mmsType = cursor.getLong(cursor.getColumnIndexOrThrow(MmsDatabase.MESSAGE_TYPE));

      if (mmsType == PduHeaders.MESSAGE_TYPE_NOTIFICATION_IND) {
        return getNotificationMmsMessageRecord(cursor);
      } else {
        return getMediaMmsMessageRecord(cursor);
      }
    }

    private NotificationMmsMessageRecord getNotificationMmsMessageRecord(Cursor cursor) {
      long id                    = cursor.getLong(cursor.getColumnIndexOrThrow(MmsDatabase.ID));
      long dateSent              = cursor.getLong(cursor.getColumnIndexOrThrow(MmsDatabase.NORMALIZED_DATE_SENT));
      long dateReceived          = cursor.getLong(cursor.getColumnIndexOrThrow(MmsDatabase.NORMALIZED_DATE_RECEIVED));
      long threadId              = cursor.getLong(cursor.getColumnIndexOrThrow(MmsDatabase.THREAD_ID));
      long mailbox               = cursor.getLong(cursor.getColumnIndexOrThrow(MmsDatabase.MESSAGE_BOX));
      String address             = cursor.getString(cursor.getColumnIndexOrThrow(MmsDatabase.ADDRESS));
      int addressDeviceId        = cursor.getInt(cursor.getColumnIndexOrThrow(MmsDatabase.ADDRESS_DEVICE_ID));
      Recipients recipients      = getRecipientsFor(address);

      String contentLocation     = cursor.getString(cursor.getColumnIndexOrThrow(MmsDatabase.CONTENT_LOCATION));
      String transactionId       = cursor.getString(cursor.getColumnIndexOrThrow(MmsDatabase.TRANSACTION_ID));
      long messageSize           = cursor.getLong(cursor.getColumnIndexOrThrow(MmsDatabase.MESSAGE_SIZE));
      long expiry                = cursor.getLong(cursor.getColumnIndexOrThrow(MmsDatabase.EXPIRY));
      int status                 = cursor.getInt(cursor.getColumnIndexOrThrow(MmsDatabase.STATUS));
      int receiptCount           = cursor.getInt(cursor.getColumnIndexOrThrow(MmsDatabase.RECEIPT_COUNT));

      byte[]contentLocationBytes = null;
      byte[]transactionIdBytes   = null;

      if (!TextUtils.isEmpty(contentLocation))
        contentLocationBytes = org.thoughtcrime.securesms.util.Util.toIsoBytes(contentLocation);

      if (!TextUtils.isEmpty(transactionId))
        transactionIdBytes = org.thoughtcrime.securesms.util.Util.toIsoBytes(transactionId);


      return new NotificationMmsMessageRecord(context, id, recipients, recipients.getPrimaryRecipient(),
                                              addressDeviceId, dateSent, dateReceived, receiptCount, threadId,
                                              contentLocationBytes, messageSize, expiry, status,
                                              transactionIdBytes, mailbox);
    }

    private MediaMmsMessageRecord getMediaMmsMessageRecord(Cursor cursor) {
      long id                 = cursor.getLong(cursor.getColumnIndexOrThrow(MmsDatabase.ID));
      long dateSent           = cursor.getLong(cursor.getColumnIndexOrThrow(MmsDatabase.NORMALIZED_DATE_SENT));
      long dateReceived       = cursor.getLong(cursor.getColumnIndexOrThrow(MmsDatabase.NORMALIZED_DATE_RECEIVED));
      long box                = cursor.getLong(cursor.getColumnIndexOrThrow(MmsDatabase.MESSAGE_BOX));
      long threadId           = cursor.getLong(cursor.getColumnIndexOrThrow(MmsDatabase.THREAD_ID));
      String address          = cursor.getString(cursor.getColumnIndexOrThrow(MmsDatabase.ADDRESS));
      int addressDeviceId     = cursor.getInt(cursor.getColumnIndexOrThrow(MmsDatabase.ADDRESS_DEVICE_ID));
      int receiptCount        = cursor.getInt(cursor.getColumnIndexOrThrow(MmsDatabase.RECEIPT_COUNT));
      DisplayRecord.Body body = getBody(cursor);
      int partCount           = cursor.getInt(cursor.getColumnIndexOrThrow(MmsDatabase.PART_COUNT));
      String mismatchDocument = cursor.getString(cursor.getColumnIndexOrThrow(MmsDatabase.MISMATCHED_IDENTITIES));
      String networkDocument  = cursor.getString(cursor.getColumnIndexOrThrow(MmsDatabase.NETWORK_FAILURE));

      Recipients                recipients      = getRecipientsFor(address);
      List<IdentityKeyMismatch> mismatches      = getMismatchedIdentities(mismatchDocument);
      List<NetworkFailure>      networkFailures = getFailures(networkDocument);

      ListenableFutureTask<SlideDeck> slideDeck = getSlideDeck(masterSecret, dateReceived, id);

      return new MediaMmsMessageRecord(context, id, recipients, recipients.getPrimaryRecipient(),
                                       addressDeviceId, dateSent, dateReceived, receiptCount,
                                       threadId, body, slideDeck, partCount, box, mismatches, networkFailures);
    }

    private Recipients getRecipientsFor(String address) {
      if (TextUtils.isEmpty(address) || address.equals("insert-address-token")) {
        return RecipientFactory.getRecipientsFor(context, Recipient.getUnknownRecipient(context), false);
      }

      Recipients recipients =  RecipientFactory.getRecipientsFromString(context, address, false);

      if (recipients == null || recipients.isEmpty()) {
        return RecipientFactory.getRecipientsFor(context, Recipient.getUnknownRecipient(context), false);
      }

      return recipients;
    }

    private List<IdentityKeyMismatch> getMismatchedIdentities(String document) {
      if (!TextUtils.isEmpty(document)) {
        try {
          return JsonUtils.fromJson(document, IdentityKeyMismatchList.class).getList();
        } catch (IOException e) {
          Log.w(TAG, e);
        }
      }

      return new LinkedList<>();
    }

    private List<NetworkFailure> getFailures(String document) {
      if (!TextUtils.isEmpty(document)) {
        try {
          return JsonUtils.fromJson(document, NetworkFailureList.class).getList();
        } catch (IOException ioe) {
          Log.w(TAG, ioe);
        }
      }

      return new LinkedList<>();
    }

    private DisplayRecord.Body getBody(Cursor cursor) {
      try {
        String body = cursor.getString(cursor.getColumnIndexOrThrow(MmsDatabase.BODY));
        long box    = cursor.getLong(cursor.getColumnIndexOrThrow(MmsDatabase.MESSAGE_BOX));

        if (!TextUtils.isEmpty(body) && masterCipher != null && Types.isSymmetricEncryption(box)) {
          return new DisplayRecord.Body(masterCipher.decryptBody(body), true);
        } else if (!TextUtils.isEmpty(body) && masterCipher == null && Types.isSymmetricEncryption(box)) {
          return new DisplayRecord.Body(body, false);
        } else {
          return new DisplayRecord.Body(body == null ? "" : body, true);
        }
      } catch (InvalidMessageException e) {
        Log.w("MmsDatabase", e);
        return new DisplayRecord.Body(context.getString(R.string.MmsDatabase_error_decrypting_message), true);
      }
    }

    private ListenableFutureTask<SlideDeck> getSlideDeck(final MasterSecret masterSecret,
                                                         final long timestamp,
                                                         final long id)
    {
      ListenableFutureTask<SlideDeck> future = getCachedSlideDeck(timestamp, id);

      if (future != null) {
        return future;
      }

      Callable<SlideDeck> task = new Callable<SlideDeck>() {
        @Override
        public SlideDeck call() throws Exception {
          if (masterSecret == null)
            return null;

          PartDatabase partDatabase = DatabaseFactory.getPartDatabase(context);
          PduBody      body         = getPartsAsBody(partDatabase.getParts(id));
          SlideDeck    slideDeck    = new SlideDeck(context, masterSecret, body);

          if (!body.containsPushInProgress()) {
            slideCache.put(timestamp + "::" + id, new SoftReference<>(slideDeck));
          }

          return slideDeck;
        }
      };

      future = new ListenableFutureTask<>(task);
      slideResolver.execute(future);

      return future;
    }

    private ListenableFutureTask<SlideDeck> getCachedSlideDeck(final long timestamp, final long id) {
      SoftReference<SlideDeck> reference = slideCache.get(timestamp + "::" + id);

      if (reference != null) {
        final SlideDeck slideDeck = reference.get();

        if (slideDeck != null) {
          Callable<SlideDeck> task = new Callable<SlideDeck>() {
            @Override
            public SlideDeck call() throws Exception {
              return slideDeck;
            }
          };

          ListenableFutureTask<SlideDeck> future = new ListenableFutureTask<>(task);
          future.run();

          return future;
        }
      }

      return null;
    }

    public void close() {
      cursor.close();
    }
  }

  private PduBody getPartsAsBody(List<PduPart> parts) {
    PduBody body = new PduBody();

    for (PduPart part : parts) {
      body.addPart(part);
    }

    return body;
  }

}


File: src/org/thoughtcrime/securesms/database/SmsDatabase.java
/**
 * Copyright (C) 2011 Whisper Systems
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.thoughtcrime.securesms.database;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import android.database.sqlite.SQLiteStatement;
import android.telephony.PhoneNumberUtils;
import android.text.TextUtils;
import android.util.Log;
import android.util.Pair;

import org.thoughtcrime.securesms.ApplicationContext;
import org.thoughtcrime.securesms.database.documents.IdentityKeyMismatch;
import org.thoughtcrime.securesms.database.documents.IdentityKeyMismatchList;
import org.thoughtcrime.securesms.database.model.DisplayRecord;
import org.thoughtcrime.securesms.database.model.SmsMessageRecord;
import org.thoughtcrime.securesms.jobs.TrimThreadJob;
import org.thoughtcrime.securesms.recipients.Recipient;
import org.thoughtcrime.securesms.recipients.RecipientFactory;
import org.thoughtcrime.securesms.recipients.Recipients;
import org.thoughtcrime.securesms.sms.IncomingGroupMessage;
import org.thoughtcrime.securesms.sms.IncomingTextMessage;
import org.thoughtcrime.securesms.sms.OutgoingTextMessage;
import org.thoughtcrime.securesms.util.JsonUtils;
import org.whispersystems.jobqueue.JobManager;
import org.whispersystems.textsecure.api.util.InvalidNumberException;

import java.io.IOException;
import java.util.LinkedList;
import java.util.List;
import java.util.Set;

import static org.thoughtcrime.securesms.util.Util.canonicalizeNumber;

/**
 * Database for storage of SMS messages.
 *
 * @author Moxie Marlinspike
 */

public class SmsDatabase extends MessagingDatabase {

  private static final String TAG = SmsDatabase.class.getSimpleName();

  public  static final String TABLE_NAME         = "sms";
  public  static final String PERSON             = "person";
          static final String DATE_RECEIVED      = "date";
          static final String DATE_SENT          = "date_sent";
  public  static final String PROTOCOL           = "protocol";
  public  static final String STATUS             = "status";
  public  static final String TYPE               = "type";
  public  static final String REPLY_PATH_PRESENT = "reply_path_present";
  public  static final String SUBJECT            = "subject";
  public  static final String SERVICE_CENTER     = "service_center";

  public static final String CREATE_TABLE = "CREATE TABLE " + TABLE_NAME + " (" + ID + " integer PRIMARY KEY, "                +
    THREAD_ID + " INTEGER, " + ADDRESS + " TEXT, " + ADDRESS_DEVICE_ID + " INTEGER DEFAULT 1, " + PERSON + " INTEGER, " +
    DATE_RECEIVED  + " INTEGER, " + DATE_SENT + " INTEGER, " + PROTOCOL + " INTEGER, " + READ + " INTEGER DEFAULT 0, " +
    STATUS + " INTEGER DEFAULT -1," + TYPE + " INTEGER, " + REPLY_PATH_PRESENT + " INTEGER, " +
    RECEIPT_COUNT + " INTEGER DEFAULT 0," + SUBJECT + " TEXT, " + BODY + " TEXT, " +
    MISMATCHED_IDENTITIES + " TEXT DEFAULT NULL, " + SERVICE_CENTER + " TEXT);";

  public static final String[] CREATE_INDEXS = {
    "CREATE INDEX IF NOT EXISTS sms_thread_id_index ON " + TABLE_NAME + " (" + THREAD_ID + ");",
    "CREATE INDEX IF NOT EXISTS sms_read_index ON " + TABLE_NAME + " (" + READ + ");",
    "CREATE INDEX IF NOT EXISTS sms_read_and_thread_id_index ON " + TABLE_NAME + "(" + READ + "," + THREAD_ID + ");",
    "CREATE INDEX IF NOT EXISTS sms_type_index ON " + TABLE_NAME + " (" + TYPE + ");",
    "CREATE INDEX IF NOT EXISTS sms_date_sent_index ON " + TABLE_NAME + " (" + DATE_SENT + ");"
  };

  private static final String[] MESSAGE_PROJECTION = new String[] {
      ID, THREAD_ID, ADDRESS, ADDRESS_DEVICE_ID, PERSON,
      DATE_RECEIVED + " AS " + NORMALIZED_DATE_RECEIVED,
      DATE_SENT + " AS " + NORMALIZED_DATE_SENT,
      PROTOCOL, READ, STATUS, TYPE,
      REPLY_PATH_PRESENT, SUBJECT, BODY, SERVICE_CENTER, RECEIPT_COUNT,
      MISMATCHED_IDENTITIES
  };

  private final JobManager jobManager;

  public SmsDatabase(Context context, SQLiteOpenHelper databaseHelper) {
    super(context, databaseHelper);
    this.jobManager = ApplicationContext.getInstance(context).getJobManager();
  }

  protected String getTableName() {
    return TABLE_NAME;
  }

  private void updateTypeBitmask(long id, long maskOff, long maskOn) {
    Log.w("MessageDatabase", "Updating ID: " + id + " to base type: " + maskOn);

    SQLiteDatabase db = databaseHelper.getWritableDatabase();
    db.execSQL("UPDATE " + TABLE_NAME +
               " SET " + TYPE + " = (" + TYPE + " & " + (Types.TOTAL_MASK - maskOff) + " | " + maskOn + " )" +
               " WHERE " + ID + " = ?", new String[] {id+""});

    long threadId = getThreadIdForMessage(id);

    DatabaseFactory.getThreadDatabase(context).update(threadId);
    notifyConversationListeners(threadId);
    notifyConversationListListeners();
  }

  public long getThreadIdForMessage(long id) {
    String sql        = "SELECT " + THREAD_ID + " FROM " + TABLE_NAME + " WHERE " + ID + " = ?";
    String[] sqlArgs  = new String[] {id+""};
    SQLiteDatabase db = databaseHelper.getReadableDatabase();

    Cursor cursor = null;

    try {
      cursor = db.rawQuery(sql, sqlArgs);
      if (cursor != null && cursor.moveToFirst())
        return cursor.getLong(0);
      else
        return -1;
    } finally {
      if (cursor != null)
        cursor.close();
    }
  }

  public int getMessageCount() {
    SQLiteDatabase db = databaseHelper.getReadableDatabase();
    Cursor cursor     = null;

    try {
      cursor = db.query(TABLE_NAME, new String[] {"COUNT(*)"}, null, null, null, null, null);

      if (cursor != null && cursor.moveToFirst()) return cursor.getInt(0);
      else                                        return 0;
    } finally {
      if (cursor != null)
        cursor.close();
    }
  }

  public int getMessageCountForThread(long threadId) {
    SQLiteDatabase db = databaseHelper.getReadableDatabase();
    Cursor cursor     = null;

    try {
      cursor = db.query(TABLE_NAME, new String[] {"COUNT(*)"}, THREAD_ID + " = ?",
                        new String[] {threadId+""}, null, null, null);

      if (cursor != null && cursor.moveToFirst())
        return cursor.getInt(0);
    } finally {
      if (cursor != null)
        cursor.close();
    }

    return 0;
  }

  public void markAsEndSession(long id) {
    updateTypeBitmask(id, Types.KEY_EXCHANGE_MASK, Types.END_SESSION_BIT);
  }

  public void markAsPreKeyBundle(long id) {
    updateTypeBitmask(id, Types.KEY_EXCHANGE_MASK, Types.KEY_EXCHANGE_BIT | Types.KEY_EXCHANGE_BUNDLE_BIT);
  }

  public void markAsInvalidVersionKeyExchange(long id) {
    updateTypeBitmask(id, 0, Types.KEY_EXCHANGE_INVALID_VERSION_BIT);
  }

  public void markAsSecure(long id) {
    updateTypeBitmask(id, 0, Types.SECURE_MESSAGE_BIT);
  }

  public void markAsInsecure(long id) {
    updateTypeBitmask(id, Types.SECURE_MESSAGE_BIT, 0);
  }

  public void markAsPush(long id) {
    updateTypeBitmask(id, 0, Types.PUSH_MESSAGE_BIT);
  }

  public void markAsForcedSms(long id) {
    updateTypeBitmask(id, Types.PUSH_MESSAGE_BIT, Types.MESSAGE_FORCE_SMS_BIT);
  }

  public void markAsDecryptFailed(long id) {
    updateTypeBitmask(id, Types.ENCRYPTION_MASK, Types.ENCRYPTION_REMOTE_FAILED_BIT);
  }

  public void markAsDecryptDuplicate(long id) {
    updateTypeBitmask(id, Types.ENCRYPTION_MASK, Types.ENCRYPTION_REMOTE_DUPLICATE_BIT);
  }

  public void markAsNoSession(long id) {
    updateTypeBitmask(id, Types.ENCRYPTION_MASK, Types.ENCRYPTION_REMOTE_NO_SESSION_BIT);
  }

  public void markAsDecrypting(long id) {
    updateTypeBitmask(id, Types.ENCRYPTION_MASK, Types.ENCRYPTION_REMOTE_BIT);
  }

  public void markAsLegacyVersion(long id) {
    updateTypeBitmask(id, Types.ENCRYPTION_MASK, Types.ENCRYPTION_REMOTE_LEGACY_BIT);
  }

  public void markAsOutbox(long id) {
    updateTypeBitmask(id, Types.BASE_TYPE_MASK, Types.BASE_OUTBOX_TYPE);
  }

  public void markAsPendingInsecureSmsFallback(long id) {
    updateTypeBitmask(id, Types.BASE_TYPE_MASK, Types.BASE_PENDING_INSECURE_SMS_FALLBACK);
  }

  public void markAsSending(long id) {
    updateTypeBitmask(id, Types.BASE_TYPE_MASK, Types.BASE_SENDING_TYPE);
  }

  public void markAsSent(long id) {
    updateTypeBitmask(id, Types.BASE_TYPE_MASK, Types.BASE_SENT_TYPE);
  }

  public void markStatus(long id, int status) {
    Log.w("MessageDatabase", "Updating ID: " + id + " to status: " + status);
    ContentValues contentValues = new ContentValues();
    contentValues.put(STATUS, status);

    SQLiteDatabase db = databaseHelper.getWritableDatabase();
    db.update(TABLE_NAME, contentValues, ID_WHERE, new String[] {id+""});
    notifyConversationListeners(getThreadIdForMessage(id));
  }

  public void markAsSentFailed(long id) {
    updateTypeBitmask(id, Types.BASE_TYPE_MASK, Types.BASE_SENT_FAILED_TYPE);
  }

  public void incrementDeliveryReceiptCount(String address, long timestamp) {
    SQLiteDatabase database = databaseHelper.getWritableDatabase();
    Cursor         cursor   = null;

    try {
      cursor = database.query(TABLE_NAME, new String[] {ID, THREAD_ID, ADDRESS, TYPE},
                              DATE_SENT + " = ?", new String[] {String.valueOf(timestamp)},
                              null, null, null, null);

      while (cursor.moveToNext()) {
        if (Types.isOutgoingMessageType(cursor.getLong(cursor.getColumnIndexOrThrow(TYPE)))) {
          try {
            String theirAddress = canonicalizeNumber(context, address);
            String ourAddress   = canonicalizeNumber(context, cursor.getString(cursor.getColumnIndexOrThrow(ADDRESS)));

            if (ourAddress.equals(theirAddress)) {
              database.execSQL("UPDATE " + TABLE_NAME +
                               " SET " + RECEIPT_COUNT + " = " + RECEIPT_COUNT + " + 1 WHERE " +
                               ID + " = ?",
                               new String[] {String.valueOf(cursor.getLong(cursor.getColumnIndexOrThrow(ID)))});

              notifyConversationListeners(cursor.getLong(cursor.getColumnIndexOrThrow(THREAD_ID)));
            }
          } catch (InvalidNumberException e) {
            Log.w("SmsDatabase", e);
          }
        }
      }
    } finally {
      if (cursor != null)
        cursor.close();
    }
  }

  public void setMessagesRead(long threadId) {
    SQLiteDatabase database     = databaseHelper.getWritableDatabase();
    ContentValues contentValues = new ContentValues();
    contentValues.put(READ, 1);

    database.update(TABLE_NAME, contentValues,
                    THREAD_ID + " = ? AND " + READ + " = 0",
                    new String[] {threadId+""});
  }

  public void setAllMessagesRead() {
    SQLiteDatabase database     = databaseHelper.getWritableDatabase();
    ContentValues contentValues = new ContentValues();
    contentValues.put(READ, 1);

    database.update(TABLE_NAME, contentValues, null, null);
  }

  protected Pair<Long, Long> updateMessageBodyAndType(long messageId, String body, long maskOff, long maskOn) {
    SQLiteDatabase db = databaseHelper.getWritableDatabase();
    db.execSQL("UPDATE " + TABLE_NAME + " SET " + BODY + " = ?, " +
                   TYPE + " = (" + TYPE + " & " + (Types.TOTAL_MASK - maskOff) + " | " + maskOn + ") " +
                   "WHERE " + ID + " = ?",
               new String[] {body, messageId + ""});

    long threadId = getThreadIdForMessage(messageId);

    DatabaseFactory.getThreadDatabase(context).update(threadId);
    notifyConversationListeners(threadId);
    notifyConversationListListeners();

    return new Pair<>(messageId, threadId);
  }

  public Pair<Long, Long> copyMessageInbox(long messageId) {
    Reader           reader = readerFor(getMessage(messageId));
    SmsMessageRecord record = reader.getNext();

    ContentValues contentValues = new ContentValues();
    contentValues.put(TYPE, (record.getType() & ~Types.BASE_TYPE_MASK) | Types.BASE_INBOX_TYPE);
    contentValues.put(ADDRESS, record.getIndividualRecipient().getNumber());
    contentValues.put(ADDRESS_DEVICE_ID, record.getRecipientDeviceId());
    contentValues.put(DATE_RECEIVED, System.currentTimeMillis());
    contentValues.put(DATE_SENT, record.getDateSent());
    contentValues.put(PROTOCOL, 31337);
    contentValues.put(READ, 0);
    contentValues.put(BODY, record.getBody().getBody());
    contentValues.put(THREAD_ID, record.getThreadId());

    SQLiteDatabase db           = databaseHelper.getWritableDatabase();
    long           newMessageId = db.insert(TABLE_NAME, null, contentValues);

    DatabaseFactory.getThreadDatabase(context).update(record.getThreadId());
    notifyConversationListeners(record.getThreadId());

    jobManager.add(new TrimThreadJob(context, record.getThreadId()));
    reader.close();
    
    return new Pair<>(newMessageId, record.getThreadId());
  }

  protected Pair<Long, Long> insertMessageInbox(IncomingTextMessage message, long type) {
    if (message.isPreKeyBundle()) {
      type |= Types.KEY_EXCHANGE_BIT | Types.KEY_EXCHANGE_BUNDLE_BIT;
    } else if (message.isSecureMessage()) {
      type |= Types.SECURE_MESSAGE_BIT;
    } else if (message.isGroup()) {
      type |= Types.SECURE_MESSAGE_BIT;
      if      (((IncomingGroupMessage)message).isUpdate()) type |= Types.GROUP_UPDATE_BIT;
      else if (((IncomingGroupMessage)message).isQuit())   type |= Types.GROUP_QUIT_BIT;
    } else if (message.isEndSession()) {
      type |= Types.SECURE_MESSAGE_BIT;
      type |= Types.END_SESSION_BIT;
    }

    if (message.isPush()) type |= Types.PUSH_MESSAGE_BIT;

    Recipients recipients;

    if (message.getSender() != null) {
      recipients = RecipientFactory.getRecipientsFromString(context, message.getSender(), true);
    } else {
      Log.w(TAG, "Sender is null, returning unknown recipient");
      recipients = RecipientFactory.getRecipientsFor(context, Recipient.getUnknownRecipient(context), false);
    }

    Recipients groupRecipients;

    if (message.getGroupId() == null) {
      groupRecipients = null;
    } else {
      groupRecipients = RecipientFactory.getRecipientsFromString(context, message.getGroupId(), true);
    }

    boolean    unread     = org.thoughtcrime.securesms.util.Util.isDefaultSmsProvider(context) ||
                            message.isSecureMessage() || message.isPreKeyBundle();

    long       threadId;

    if (groupRecipients == null) threadId = DatabaseFactory.getThreadDatabase(context).getThreadIdFor(recipients);
    else                         threadId = DatabaseFactory.getThreadDatabase(context).getThreadIdFor(groupRecipients);

    ContentValues values = new ContentValues(6);
    values.put(ADDRESS, message.getSender());
    values.put(ADDRESS_DEVICE_ID,  message.getSenderDeviceId());
    values.put(DATE_RECEIVED, System.currentTimeMillis());
    values.put(DATE_SENT, message.getSentTimestampMillis());
    values.put(PROTOCOL, message.getProtocol());
    values.put(READ, unread ? 0 : 1);

    if (!TextUtils.isEmpty(message.getPseudoSubject()))
      values.put(SUBJECT, message.getPseudoSubject());

    values.put(REPLY_PATH_PRESENT, message.isReplyPathPresent());
    values.put(SERVICE_CENTER, message.getServiceCenterAddress());
    values.put(BODY, message.getMessageBody());
    values.put(TYPE, type);
    values.put(THREAD_ID, threadId);

    SQLiteDatabase db = databaseHelper.getWritableDatabase();
    long messageId    = db.insert(TABLE_NAME, null, values);

    if (unread) {
      DatabaseFactory.getThreadDatabase(context).setUnread(threadId);
    }

    DatabaseFactory.getThreadDatabase(context).update(threadId);
    notifyConversationListeners(threadId);
    jobManager.add(new TrimThreadJob(context, threadId));

    return new Pair<>(messageId, threadId);
  }

  public Pair<Long, Long> insertMessageInbox(IncomingTextMessage message) {
    return insertMessageInbox(message, Types.BASE_INBOX_TYPE);
  }

  protected long insertMessageOutbox(long threadId, OutgoingTextMessage message,
                                     long type, boolean forceSms, long date)
  {
    if      (message.isKeyExchange())   type |= Types.KEY_EXCHANGE_BIT;
    else if (message.isSecureMessage()) type |= Types.SECURE_MESSAGE_BIT;
    else if (message.isEndSession())    type |= Types.END_SESSION_BIT;
    if      (forceSms)                  type |= Types.MESSAGE_FORCE_SMS_BIT;

    ContentValues contentValues = new ContentValues(6);
    contentValues.put(ADDRESS, PhoneNumberUtils.formatNumber(message.getRecipients().getPrimaryRecipient().getNumber()));
    contentValues.put(THREAD_ID, threadId);
    contentValues.put(BODY, message.getMessageBody());
    contentValues.put(DATE_RECEIVED, date);
    contentValues.put(DATE_SENT, date);
    contentValues.put(READ, 1);
    contentValues.put(TYPE, type);

    SQLiteDatabase db        = databaseHelper.getWritableDatabase();
    long           messageId = db.insert(TABLE_NAME, ADDRESS, contentValues);

    DatabaseFactory.getThreadDatabase(context).update(threadId);
    notifyConversationListeners(threadId);
    jobManager.add(new TrimThreadJob(context, threadId));

    return messageId;
  }

  Cursor getMessages(int skip, int limit) {
    SQLiteDatabase db = databaseHelper.getReadableDatabase();
    return db.query(TABLE_NAME, MESSAGE_PROJECTION, null, null, null, null, ID, skip + "," + limit);
  }

  Cursor getOutgoingMessages() {
    String outgoingSelection = TYPE + " & "  + Types.BASE_TYPE_MASK + " = " + Types.BASE_OUTBOX_TYPE;
    SQLiteDatabase db        = databaseHelper.getReadableDatabase();
    return db.query(TABLE_NAME, MESSAGE_PROJECTION, outgoingSelection, null, null, null, null);
  }

  public Cursor getDecryptInProgressMessages() {
    String where       = TYPE + " & " + (Types.ENCRYPTION_REMOTE_BIT | Types.ENCRYPTION_ASYMMETRIC_BIT) + " != 0";
    SQLiteDatabase db  = databaseHelper.getReadableDatabase();
    return db.query(TABLE_NAME, MESSAGE_PROJECTION, where, null, null, null, null);
  }

  public Cursor getEncryptedRogueMessages(Recipient recipient) {
    String selection  = TYPE + " & " + Types.ENCRYPTION_REMOTE_NO_SESSION_BIT + " != 0" +
                        " AND PHONE_NUMBERS_EQUAL(" + ADDRESS + ", ?)";
    String[] args     = {recipient.getNumber()};
    SQLiteDatabase db = databaseHelper.getReadableDatabase();
    return db.query(TABLE_NAME, MESSAGE_PROJECTION, selection, args, null, null, null);
  }

  public Cursor getMessage(long messageId) {
    SQLiteDatabase db     = databaseHelper.getReadableDatabase();
    Cursor         cursor = db.query(TABLE_NAME, MESSAGE_PROJECTION, ID_WHERE, new String[]{messageId + ""},
                                     null, null, null);
    setNotifyConverationListeners(cursor, getThreadIdForMessage(messageId));
    return cursor;
  }

  public boolean deleteMessage(long messageId) {
    Log.w("MessageDatabase", "Deleting: " + messageId);
    SQLiteDatabase db = databaseHelper.getWritableDatabase();
    long threadId     = getThreadIdForMessage(messageId);
    db.delete(TABLE_NAME, ID_WHERE, new String[] {messageId+""});
    boolean threadDeleted = DatabaseFactory.getThreadDatabase(context).update(threadId);
    notifyConversationListeners(threadId);
    return threadDeleted;
  }

  /*package */void deleteThread(long threadId) {
    SQLiteDatabase db = databaseHelper.getWritableDatabase();
    db.delete(TABLE_NAME, THREAD_ID + " = ?", new String[] {threadId+""});
  }

  /*package*/void deleteMessagesInThreadBeforeDate(long threadId, long date) {
    SQLiteDatabase db = databaseHelper.getWritableDatabase();
    String where      = THREAD_ID + " = ? AND (CASE " + TYPE;

    for (long outgoingType : Types.OUTGOING_MESSAGE_TYPES) {
      where += " WHEN " + outgoingType + " THEN " + DATE_SENT + " < " + date;
    }

    where += (" ELSE " + DATE_RECEIVED + " < " + date + " END)");

    db.delete(TABLE_NAME, where, new String[] {threadId + ""});
  }

  /*package*/ void deleteThreads(Set<Long> threadIds) {
    SQLiteDatabase db = databaseHelper.getWritableDatabase();
    String where      = "";

    for (long threadId : threadIds) {
      where += THREAD_ID + " = '" + threadId + "' OR ";
    }

    where = where.substring(0, where.length() - 4);

    db.delete(TABLE_NAME, where, null);
  }

  /*package */ void deleteAllThreads() {
    SQLiteDatabase db = databaseHelper.getWritableDatabase();
    db.delete(TABLE_NAME, null, null);
  }

  /*package*/ SQLiteDatabase beginTransaction() {
    SQLiteDatabase database = databaseHelper.getWritableDatabase();
    database.beginTransaction();
    return database;
  }

  /*package*/ void endTransaction(SQLiteDatabase database) {
    database.setTransactionSuccessful();
    database.endTransaction();
  }

  /*package*/ SQLiteStatement createInsertStatement(SQLiteDatabase database) {
    return database.compileStatement("INSERT INTO " + TABLE_NAME + " (" + ADDRESS + ", " +
                                                                      PERSON + ", " +
                                                                      DATE_SENT + ", " +
                                                                      DATE_RECEIVED  + ", " +
                                                                      PROTOCOL + ", " +
                                                                      READ + ", " +
                                                                      STATUS + ", " +
                                                                      TYPE + ", " +
                                                                      REPLY_PATH_PRESENT + ", " +
                                                                      SUBJECT + ", " +
                                                                      BODY + ", " +
                                                                      SERVICE_CENTER +
                                                                      ", " + THREAD_ID + ") " +
                                     " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
  }

  public static class Status {
    public static final int STATUS_NONE     = -1;
    public static final int STATUS_COMPLETE  = 0;
    public static final int STATUS_PENDING   = 0x20;
    public static final int STATUS_FAILED    = 0x40;
  }

  public Reader readerFor(Cursor cursor) {
    return new Reader(cursor);
  }

  public class Reader {

    private final Cursor cursor;

    public Reader(Cursor cursor) {
      this.cursor = cursor;
    }

    public SmsMessageRecord getNext() {
      if (cursor == null || !cursor.moveToNext())
        return null;

      return getCurrent();
    }

    public int getCount() {
      if (cursor == null) return 0;
      else                return cursor.getCount();
    }

    public SmsMessageRecord getCurrent() {
      long messageId          = cursor.getLong(cursor.getColumnIndexOrThrow(SmsDatabase.ID));
      String address          = cursor.getString(cursor.getColumnIndexOrThrow(SmsDatabase.ADDRESS));
      int addressDeviceId     = cursor.getInt(cursor.getColumnIndexOrThrow(SmsDatabase.ADDRESS_DEVICE_ID));
      long type               = cursor.getLong(cursor.getColumnIndexOrThrow(SmsDatabase.TYPE));
      long dateReceived       = cursor.getLong(cursor.getColumnIndexOrThrow(SmsDatabase.NORMALIZED_DATE_RECEIVED));
      long dateSent           = cursor.getLong(cursor.getColumnIndexOrThrow(SmsDatabase.NORMALIZED_DATE_SENT));
      long threadId           = cursor.getLong(cursor.getColumnIndexOrThrow(SmsDatabase.THREAD_ID));
      int status              = cursor.getInt(cursor.getColumnIndexOrThrow(SmsDatabase.STATUS));
      int receiptCount        = cursor.getInt(cursor.getColumnIndexOrThrow(SmsDatabase.RECEIPT_COUNT));
      String mismatchDocument = cursor.getString(cursor.getColumnIndexOrThrow(SmsDatabase.MISMATCHED_IDENTITIES));

      List<IdentityKeyMismatch> mismatches = getMismatches(mismatchDocument);
      Recipients                recipients = getRecipientsFor(address);
      DisplayRecord.Body        body       = getBody(cursor);

      return new SmsMessageRecord(context, messageId, body, recipients,
                                  recipients.getPrimaryRecipient(),
                                  addressDeviceId,
                                  dateSent, dateReceived, receiptCount, type,
                                  threadId, status, mismatches);
    }

    private Recipients getRecipientsFor(String address) {
      if (address != null) {
        Recipients recipients = RecipientFactory.getRecipientsFromString(context, address, false);

        if (recipients == null || recipients.isEmpty()) {
          return RecipientFactory.getRecipientsFor(context, Recipient.getUnknownRecipient(context), false);
        }

        return recipients;
      } else {
        Log.w(TAG, "getRecipientsFor() address is null");
        return RecipientFactory.getRecipientsFor(context, Recipient.getUnknownRecipient(context), false);
      }
    }

    private List<IdentityKeyMismatch> getMismatches(String document) {
      try {
        if (!TextUtils.isEmpty(document)) {
          return JsonUtils.fromJson(document, IdentityKeyMismatchList.class).getList();
        }
      } catch (IOException e) {
        Log.w(TAG, e);
      }

      return new LinkedList<>();
    }

    protected DisplayRecord.Body getBody(Cursor cursor) {
      long type   = cursor.getLong(cursor.getColumnIndexOrThrow(SmsDatabase.TYPE));
      String body = cursor.getString(cursor.getColumnIndexOrThrow(SmsDatabase.BODY));

      if (Types.isSymmetricEncryption(type)) {
        return new DisplayRecord.Body(body, false);
      } else {
        return new DisplayRecord.Body(body, true);
      }
    }

    public void close() {
      cursor.close();
    }
  }
}


File: src/org/thoughtcrime/securesms/notifications/MessageNotifier.java
/**
 * Copyright (C) 2011 Whisper Systems
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.thoughtcrime.securesms.notifications;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.database.Cursor;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.drawable.Drawable;
import android.media.AudioManager;
import android.media.MediaPlayer;
import android.net.Uri;
import android.support.annotation.Nullable;
import android.support.v4.app.NotificationCompat;
import android.support.v4.app.NotificationCompat.Action;
import android.support.v4.app.NotificationCompat.BigTextStyle;
import android.support.v4.app.NotificationCompat.InboxStyle;
import android.text.Spannable;
import android.text.SpannableString;
import android.text.SpannableStringBuilder;
import android.text.TextUtils;
import android.text.style.StyleSpan;
import android.util.Log;

import org.thoughtcrime.securesms.ConversationActivity;
import org.thoughtcrime.securesms.ConversationListActivity;
import org.thoughtcrime.securesms.R;
import org.thoughtcrime.securesms.crypto.MasterSecret;
import org.thoughtcrime.securesms.database.DatabaseFactory;
import org.thoughtcrime.securesms.database.MmsSmsDatabase;
import org.thoughtcrime.securesms.database.PushDatabase;
import org.thoughtcrime.securesms.database.RecipientPreferenceDatabase.VibrateState;
import org.thoughtcrime.securesms.database.SmsDatabase;
import org.thoughtcrime.securesms.database.ThreadDatabase;
import org.thoughtcrime.securesms.database.model.MessageRecord;
import org.thoughtcrime.securesms.recipients.Recipient;
import org.thoughtcrime.securesms.recipients.RecipientFactory;
import org.thoughtcrime.securesms.recipients.Recipients;
import org.thoughtcrime.securesms.service.KeyCachingService;
import org.thoughtcrime.securesms.util.BitmapUtil;
import org.thoughtcrime.securesms.util.SpanUtil;
import org.thoughtcrime.securesms.util.TextSecurePreferences;
import org.whispersystems.textsecure.api.messages.TextSecureEnvelope;

import java.io.IOException;
import java.util.List;
import java.util.ListIterator;
import java.util.concurrent.TimeUnit;

import me.leolin.shortcutbadger.ShortcutBadger;


/**
 * Handles posting system notifications for new messages.
 *
 *
 * @author Moxie Marlinspike
 */

public class MessageNotifier {
  private static final String TAG = MessageNotifier.class.getSimpleName();

  public static final int NOTIFICATION_ID = 1338;

  private volatile static long visibleThread = -1;

  public static void setVisibleThread(long threadId) {
    visibleThread = threadId;
  }

  public static void notifyMessageDeliveryFailed(Context context, Recipients recipients, long threadId) {
    if (visibleThread == threadId) {
      sendInThreadNotification(context, recipients);
    } else {
      Intent intent = new Intent(context, ConversationActivity.class);
      intent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
      intent.putExtra("recipients", recipients.getIds());
      intent.putExtra("thread_id", threadId);
      intent.setData((Uri.parse("custom://"+System.currentTimeMillis())));

      NotificationCompat.Builder builder = new NotificationCompat.Builder(context);
      builder.setSmallIcon(R.drawable.icon_notification);
      builder.setLargeIcon(BitmapFactory.decodeResource(context.getResources(),
                                                        R.drawable.ic_action_warning_red));
      builder.setContentTitle(context.getString(R.string.MessageNotifier_message_delivery_failed));
      builder.setContentText(context.getString(R.string.MessageNotifier_failed_to_deliver_message));
      builder.setTicker(context.getString(R.string.MessageNotifier_error_delivering_message));
      builder.setContentIntent(PendingIntent.getActivity(context, 0, intent, 0));
      builder.setAutoCancel(true);
      setNotificationAlarms(context, builder, true, null, VibrateState.DEFAULT);

      ((NotificationManager)context.getSystemService(Context.NOTIFICATION_SERVICE))
        .notify((int)threadId, builder.build());
    }
  }

  public static void updateNotification(Context context, MasterSecret masterSecret) {
    if (!TextSecurePreferences.isNotificationsEnabled(context)) {
      return;
    }

    updateNotification(context, masterSecret, false, 0);
  }

  public static void updateNotification(Context context, MasterSecret masterSecret, long threadId) {
    Recipients recipients = DatabaseFactory.getThreadDatabase(context)
                                           .getRecipientsForThreadId(threadId);

    if (!TextSecurePreferences.isNotificationsEnabled(context) ||
        (recipients != null && recipients.isMuted()))
    {
      return;
    }


    if (visibleThread == threadId) {
      ThreadDatabase threads = DatabaseFactory.getThreadDatabase(context);
      threads.setRead(threadId);
      sendInThreadNotification(context, threads.getRecipientsForThreadId(threadId));
    } else {
      updateNotification(context, masterSecret, true, 0);
    }
  }

  private static void updateNotification(Context context, MasterSecret masterSecret, boolean signal, int reminderCount) {
    Cursor telcoCursor = null;
    Cursor pushCursor  = null;

    try {
      telcoCursor = DatabaseFactory.getMmsSmsDatabase(context).getUnread();
      pushCursor  = DatabaseFactory.getPushDatabase(context).getPending();

      if ((telcoCursor == null || telcoCursor.isAfterLast()) &&
          (pushCursor == null || pushCursor.isAfterLast()))
      {
        ((NotificationManager)context.getSystemService(Context.NOTIFICATION_SERVICE))
          .cancel(NOTIFICATION_ID);
        updateBadge(context, 0);
        clearReminder(context);
        return;
      }

      NotificationState notificationState = constructNotificationState(context, masterSecret, telcoCursor);

      appendPushNotificationState(context, masterSecret, notificationState, pushCursor);

      if (notificationState.hasMultipleThreads()) {
        sendMultipleThreadNotification(context, masterSecret, notificationState, signal);
      } else {
        sendSingleThreadNotification(context, masterSecret, notificationState, signal);
      }

      updateBadge(context, notificationState.getMessageCount());
      scheduleReminder(context, masterSecret, reminderCount);
    } finally {
      if (telcoCursor != null) telcoCursor.close();
      if (pushCursor != null)  pushCursor.close();
    }
  }

  private static void sendSingleThreadNotification(Context context,
                                                   MasterSecret masterSecret,
                                                   NotificationState notificationState,
                                                   boolean signal)
  {
    if (notificationState.getNotifications().isEmpty()) {
      ((NotificationManager)context.getSystemService(Context.NOTIFICATION_SERVICE))
          .cancel(NOTIFICATION_ID);
      return;
    }

    List<NotificationItem>     notifications       = notificationState.getNotifications();
    NotificationCompat.Builder builder             = new NotificationCompat.Builder(context);
    Recipient                  recipient           = notifications.get(0).getIndividualRecipient();
    Drawable                   recipientPhoto      = recipient.getContactPhoto();
    int                        largeIconTargetSize = context.getResources().getDimensionPixelSize(R.dimen.contact_photo_target_size);

    if (recipientPhoto != null) {
      Bitmap recipientPhotoBitmap = BitmapUtil.createFromDrawable(recipientPhoto, largeIconTargetSize, largeIconTargetSize);
      if (recipientPhotoBitmap != null) builder.setLargeIcon(recipientPhotoBitmap);
    }

    builder.setSmallIcon(R.drawable.icon_notification);
    builder.setColor(context.getResources().getColor(R.color.textsecure_primary));
    builder.setContentTitle(recipient.toShortString());
    builder.setContentText(notifications.get(0).getText());
    builder.setContentIntent(notifications.get(0).getPendingIntent(context));
    builder.setContentInfo(String.valueOf(notificationState.getMessageCount()));
    builder.setPriority(NotificationCompat.PRIORITY_HIGH);
    builder.setNumber(notificationState.getMessageCount());
    builder.setCategory(NotificationCompat.CATEGORY_MESSAGE);
    builder.setDeleteIntent(PendingIntent.getBroadcast(context, 0, new Intent(DeleteReceiver.DELETE_REMINDER_ACTION), 0));
    if (recipient.getContactUri() != null) builder.addPerson(recipient.getContactUri().toString());

    long timestamp = notifications.get(0).getTimestamp();
    if (timestamp != 0) builder.setWhen(timestamp);

    if (masterSecret != null) {
      Action markAsReadAction = new Action(R.drawable.check,
                                           context.getString(R.string.MessageNotifier_mark_as_read),
                                           notificationState.getMarkAsReadIntent(context, masterSecret));
      builder.addAction(markAsReadAction);
      builder.extend(new NotificationCompat.WearableExtender().addAction(markAsReadAction));
    }

    SpannableStringBuilder content = new SpannableStringBuilder();

    ListIterator<NotificationItem> iterator = notifications.listIterator(notifications.size());
    while(iterator.hasPrevious()) {
      NotificationItem item = iterator.previous();
      content.append(item.getBigStyleSummary());
      content.append('\n');
    }

    builder.setStyle(new BigTextStyle().bigText(content));

    setNotificationAlarms(context, builder, signal,
                          notificationState.getRingtone(),
                          notificationState.getVibrate());

    if (signal) {
      builder.setTicker(notifications.get(0).getTickerText());
    }

    ((NotificationManager)context.getSystemService(Context.NOTIFICATION_SERVICE))
      .notify(NOTIFICATION_ID, builder.build());
  }

  private static void sendMultipleThreadNotification(Context context,
                                                     MasterSecret masterSecret,
                                                     NotificationState notificationState,
                                                     boolean signal)
  {
    List<NotificationItem> notifications = notificationState.getNotifications();
    NotificationCompat.Builder builder   = new NotificationCompat.Builder(context);

    builder.setColor(context.getResources().getColor(R.color.textsecure_primary));
    builder.setSmallIcon(R.drawable.icon_notification);
    builder.setContentTitle(context.getString(R.string.app_name));
    builder.setSubText(context.getString(R.string.MessageNotifier_d_messages_in_d_conversations,
                                         notificationState.getMessageCount(),
                                         notificationState.getThreadCount()));
    builder.setContentText(context.getString(R.string.MessageNotifier_most_recent_from_s,
                                             notifications.get(0).getIndividualRecipientName()));
    builder.setContentIntent(PendingIntent.getActivity(context, 0, new Intent(context, ConversationListActivity.class), 0));
    
    builder.setContentInfo(String.valueOf(notificationState.getMessageCount()));
    builder.setNumber(notificationState.getMessageCount());
    builder.setCategory(NotificationCompat.CATEGORY_MESSAGE);

    long timestamp = notifications.get(0).getTimestamp();
    if (timestamp != 0) builder.setWhen(timestamp);

    builder.setDeleteIntent(PendingIntent.getBroadcast(context, 0, new Intent(DeleteReceiver.DELETE_REMINDER_ACTION), 0));

    if (masterSecret != null) {
       Action markAllAsReadAction = new Action(R.drawable.check,
                                               context.getString(R.string.MessageNotifier_mark_all_as_read),
                                               notificationState.getMarkAsReadIntent(context, masterSecret));
       builder.addAction(markAllAsReadAction);
       builder.extend(new NotificationCompat.WearableExtender().addAction(markAllAsReadAction));
    }

    InboxStyle style = new InboxStyle();

    ListIterator<NotificationItem> iterator = notifications.listIterator(notifications.size());
    while(iterator.hasPrevious()) {
      NotificationItem item = iterator.previous();
      style.addLine(item.getTickerText());
      if (item.getIndividualRecipient().getContactUri() != null) {
        builder.addPerson(item.getIndividualRecipient().getContactUri().toString());
      }
    }

    builder.setStyle(style);

    setNotificationAlarms(context, builder, signal,
                          notificationState.getRingtone(),
                          notificationState.getVibrate());

    if (signal) {
      builder.setTicker(notifications.get(0).getTickerText());
    }

    ((NotificationManager)context.getSystemService(Context.NOTIFICATION_SERVICE))
      .notify(NOTIFICATION_ID, builder.build());
  }

  private static void sendInThreadNotification(Context context, Recipients recipients) {
    try {
      if (!TextSecurePreferences.isInThreadNotifications(context)) {
        return;
      }

      Uri uri = recipients != null ? recipients.getRingtone() : null;

      if (uri == null) {
        String ringtone = TextSecurePreferences.getNotificationRingtone(context);

        if (ringtone == null) {
          Log.w(TAG, "ringtone preference was null.");
          return;
        } else {
          uri = Uri.parse(ringtone);
        }
      }

      if (uri == null) {
        Log.w(TAG, "couldn't parse ringtone uri " + TextSecurePreferences.getNotificationRingtone(context));
        return;
      }

      MediaPlayer player = new MediaPlayer();
      player.setAudioStreamType(AudioManager.STREAM_NOTIFICATION);
      player.setDataSource(context, uri);
      player.setLooping(false);
      player.setVolume(0.25f, 0.25f);
      player.prepare();

      final AudioManager audioManager = ((AudioManager)context.getSystemService(Context.AUDIO_SERVICE));

      audioManager.requestAudioFocus(null, AudioManager.STREAM_NOTIFICATION,
                                     AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK);

      player.setOnCompletionListener(new MediaPlayer.OnCompletionListener() {
        @Override
        public void onCompletion(MediaPlayer mp) {
          audioManager.abandonAudioFocus(null);
        }
      });

      player.start();
    } catch (IOException ioe) {
      Log.w("MessageNotifier", ioe);
    }
  }

  private static void appendPushNotificationState(Context context,
                                                  MasterSecret masterSecret,
                                                  NotificationState notificationState,
                                                  Cursor cursor)
  {
    if (masterSecret != null) return;

    PushDatabase.Reader reader = null;
    TextSecureEnvelope envelope;

    try {
      reader = DatabaseFactory.getPushDatabase(context).readerFor(cursor);

      while ((envelope = reader.getNext()) != null) {
        Recipients      recipients = RecipientFactory.getRecipientsFromString(context, envelope.getSource(), false);
        Recipient       recipient  = recipients.getPrimaryRecipient();
        long            threadId   = DatabaseFactory.getThreadDatabase(context).getThreadIdFor(recipients);
        SpannableString body       = new SpannableString(context.getString(R.string.MessageNotifier_encrypted_message));
        body.setSpan(new StyleSpan(android.graphics.Typeface.ITALIC), 0, body.length(), Spannable.SPAN_EXCLUSIVE_EXCLUSIVE);

        if (!recipients.isMuted()) {
          notificationState.addNotification(new NotificationItem(recipient, recipients, null, threadId, body, null, 0));
        }
      }
    } finally {
      if (reader != null)
        reader.close();
    }
  }

  private static NotificationState constructNotificationState(Context context,
                                                              MasterSecret masterSecret,
                                                              Cursor cursor)
  {
    NotificationState notificationState = new NotificationState();
    MessageRecord record;
    MmsSmsDatabase.Reader reader;

    if (masterSecret == null) reader = DatabaseFactory.getMmsSmsDatabase(context).readerFor(cursor);
    else                      reader = DatabaseFactory.getMmsSmsDatabase(context).readerFor(cursor, masterSecret);

    while ((record = reader.getNext()) != null) {
      Recipient       recipient        = record.getIndividualRecipient();
      Recipients      recipients       = record.getRecipients();
      long            threadId         = record.getThreadId();
      CharSequence    body             = record.getDisplayBody();
      Uri             image            = null;
      Recipients      threadRecipients = null;
      long            timestamp;

      if (record.isPush()) timestamp = record.getDateSent();
      else                 timestamp = record.getDateReceived();

      if (threadId != -1) {
        threadRecipients = DatabaseFactory.getThreadDatabase(context).getRecipientsForThreadId(threadId);
      }

      if (SmsDatabase.Types.isDecryptInProgressType(record.getType()) || !record.getBody().isPlaintext()) {
        body = SpanUtil.italic(context.getString(R.string.MessageNotifier_encrypted_message));
      } else if (record.isMms() && TextUtils.isEmpty(body)) {
        body = SpanUtil.italic(context.getString(R.string.MessageNotifier_media_message));
      } else if (record.isMms() && !record.isMmsNotification()) {
        String message      = context.getString(R.string.MessageNotifier_media_message_with_text, body);
        int    italicLength = message.length() - body.length();
        body = SpanUtil.italic(message, italicLength);
      }

      if (threadRecipients == null || !threadRecipients.isMuted()) {
        notificationState.addNotification(new NotificationItem(recipient, recipients, threadRecipients, threadId, body, image, timestamp));
      }
    }

    reader.close();
    return notificationState;
  }

  private static void setNotificationAlarms(Context context,
                                            NotificationCompat.Builder builder,
                                            boolean signal,
                                            @Nullable Uri ringtone,
                                            VibrateState vibrate)

  {
    String defaultRingtoneName   = TextSecurePreferences.getNotificationRingtone(context);
    boolean defaultVibrate       = TextSecurePreferences.isNotificationVibrateEnabled(context);
    String ledColor              = TextSecurePreferences.getNotificationLedColor(context);
    String ledBlinkPattern       = TextSecurePreferences.getNotificationLedPattern(context);
    String ledBlinkPatternCustom = TextSecurePreferences.getNotificationLedPatternCustom(context);
    String[] blinkPatternArray   = parseBlinkPattern(ledBlinkPattern, ledBlinkPatternCustom);

    if      (signal && ringtone != null)                        builder.setSound(ringtone);
    else if (signal && !TextUtils.isEmpty(defaultRingtoneName)) builder.setSound(Uri.parse(defaultRingtoneName));
    else                                                        builder.setSound(null);

    if (signal && (vibrate == VibrateState.ENABLED || (vibrate == VibrateState.DEFAULT && defaultVibrate))) {
      builder.setDefaults(Notification.DEFAULT_VIBRATE);
    }

    if (!ledColor.equals("none")) {
      builder.setLights(Color.parseColor(ledColor),
                        Integer.parseInt(blinkPatternArray[0]),
                        Integer.parseInt(blinkPatternArray[1]));
    }
  }

  private static String[] parseBlinkPattern(String blinkPattern, String blinkPatternCustom) {
    if (blinkPattern.equals("custom"))
      blinkPattern = blinkPatternCustom;

    return blinkPattern.split(",");
  }

  private static void updateBadge(Context context, int count) {
    try {
      ShortcutBadger.setBadge(context, count);
    } catch (Throwable t) {
      // NOTE :: I don't totally trust this thing, so I'm catching
      // everything.
      Log.w("MessageNotifier", t);
    }
  }

  private static void scheduleReminder(Context context, MasterSecret masterSecret, int count) {
    if (count >= TextSecurePreferences.getRepeatAlertsCount(context)) {
      return;
    }

    AlarmManager alarmManager = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
    Intent       alarmIntent  = new Intent(ReminderReceiver.REMINDER_ACTION);
    alarmIntent.putExtra("reminder_count", count);

    PendingIntent pendingIntent = PendingIntent.getBroadcast(context, 0, alarmIntent, PendingIntent.FLAG_CANCEL_CURRENT);
    long          timeout       = TimeUnit.MINUTES.toMillis(2);

    alarmManager.set(AlarmManager.RTC_WAKEUP, System.currentTimeMillis() + timeout, pendingIntent);
  }

  private static void clearReminder(Context context) {
    Intent        alarmIntent   = new Intent(ReminderReceiver.REMINDER_ACTION);
    PendingIntent pendingIntent = PendingIntent.getBroadcast(context, 0, alarmIntent, PendingIntent.FLAG_CANCEL_CURRENT);
    AlarmManager  alarmManager  = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
    alarmManager.cancel(pendingIntent);
  }

  public static class ReminderReceiver extends BroadcastReceiver {

    public static final String REMINDER_ACTION = "org.thoughtcrime.securesms.MessageNotifier.REMINDER_ACTION";

    @Override
    public void onReceive(Context context, Intent intent) {
      MasterSecret masterSecret  = KeyCachingService.getMasterSecret(context);
      int          reminderCount = intent.getIntExtra("reminder_count", 0);
      MessageNotifier.updateNotification(context, masterSecret, true, reminderCount + 1);
    }
  }

  public static class DeleteReceiver extends BroadcastReceiver {

    public static final String DELETE_REMINDER_ACTION = "org.thoughtcrime.securesms.MessageNotifier.DELETE_REMINDER_ACTION";

    @Override
    public void onReceive(Context context, Intent intent) {
      clearReminder(context);
    }
  }
}


File: src/org/thoughtcrime/securesms/recipients/Recipient.java
/**
 * Copyright (C) 2011 Whisper Systems
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.thoughtcrime.securesms.recipients;

import android.content.Context;
import android.graphics.drawable.Drawable;
import android.net.Uri;
import android.util.Log;

import org.thoughtcrime.securesms.contacts.ContactPhotoFactory;
import org.thoughtcrime.securesms.recipients.RecipientProvider.RecipientDetails;
import org.thoughtcrime.securesms.util.FutureTaskListener;
import org.thoughtcrime.securesms.util.GroupUtil;
import org.thoughtcrime.securesms.util.ListenableFutureTask;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;
import java.util.WeakHashMap;

public class Recipient {

  private final static String TAG = Recipient.class.getSimpleName();

  private final Set<RecipientModifiedListener> listeners = Collections.newSetFromMap(new WeakHashMap<RecipientModifiedListener, Boolean>());

  private final long recipientId;

  private String number;
  private String name;

  private Drawable contactPhoto;
  private Uri      contactUri;

  Recipient(String number, Drawable contactPhoto,
            long recipientId, ListenableFutureTask<RecipientDetails> future)
  {
    this.number                     = number;
    this.contactPhoto               = contactPhoto;
    this.recipientId                = recipientId;

    future.addListener(new FutureTaskListener<RecipientDetails>() {
      @Override
      public void onSuccess(RecipientDetails result) {
        if (result != null) {
          Set<RecipientModifiedListener> localListeners;

          synchronized (Recipient.this) {
            Recipient.this.name                      = result.name;
            Recipient.this.number                    = result.number;
            Recipient.this.contactUri                = result.contactUri;
            Recipient.this.contactPhoto              = result.avatar;

            localListeners                           = new HashSet<>(listeners);
            listeners.clear();
          }

          for (RecipientModifiedListener listener : localListeners)
            listener.onModified(Recipient.this);
        }
      }

      @Override
      public void onFailure(Throwable error) {
        Log.w("Recipient", error);
      }
    });
  }

  Recipient(String name, String number, long recipientId, Uri contactUri, Drawable contactPhoto) {
    this.number                     = number;
    this.recipientId                = recipientId;
    this.contactUri                 = contactUri;
    this.name                       = name;
    this.contactPhoto               = contactPhoto;
  }

  public synchronized Uri getContactUri() {
    return this.contactUri;
  }

  public synchronized String getName() {
    return this.name;
  }

  public String getNumber() {
    return number;
  }

  public long getRecipientId() {
    return recipientId;
  }

  public boolean isGroupRecipient() {
    return GroupUtil.isEncodedGroup(number);
  }

  public synchronized void addListener(RecipientModifiedListener listener) {
    listeners.add(listener);
  }

  public synchronized void removeListener(RecipientModifiedListener listener) {
    listeners.remove(listener);
  }

  public synchronized String toShortString() {
    return (name == null ? number : name);
  }

  public synchronized Drawable getContactPhoto() {
    return contactPhoto;
  }

  public static Recipient getUnknownRecipient(Context context) {
    return new Recipient("Unknown", "Unknown", -1, null,
                         ContactPhotoFactory.getDefaultContactPhoto(context, null));
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (o == null || !(o instanceof Recipient)) return false;

    Recipient that = (Recipient) o;

    return this.recipientId == that.recipientId;
  }

  @Override
  public int hashCode() {
    return 31 + (int)this.recipientId;
  }

  public interface RecipientModifiedListener {
    public void onModified(Recipient recipient);
  }
}


File: src/org/thoughtcrime/securesms/recipients/RecipientFactory.java
/**
 * Copyright (C) 2011 Whisper Systems
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.thoughtcrime.securesms.recipients;

import android.content.Context;
import android.support.annotation.NonNull;
import android.text.TextUtils;

import org.thoughtcrime.securesms.contacts.ContactPhotoFactory;
import org.thoughtcrime.securesms.database.CanonicalAddressDatabase;
import org.thoughtcrime.securesms.util.Util;
import org.whispersystems.libaxolotl.util.guava.Optional;

import java.util.LinkedList;
import java.util.List;
import java.util.StringTokenizer;

public class RecipientFactory {

  private static final RecipientProvider provider = new RecipientProvider();

  public static Recipients getRecipientsForIds(Context context, String recipientIds, boolean asynchronous) {
    if (TextUtils.isEmpty(recipientIds))
      return new Recipients();

    return getRecipientsForIds(context, Util.split(recipientIds, " "), asynchronous);
  }

  public static Recipients getRecipientsFor(Context context, List<Recipient> recipients, boolean asynchronous) {
    long[] ids = new long[recipients.size()];
    int    i   = 0;

    for (Recipient recipient : recipients) {
      ids[i++] = recipient.getRecipientId();
    }

    return provider.getRecipients(context, ids, asynchronous);
  }

  public static Recipients getRecipientsFor(Context context, Recipient recipient, boolean asynchronous) {
    long[] ids = new long[1];
    ids[0] = recipient.getRecipientId();

    return provider.getRecipients(context, ids, asynchronous);
  }

  public static Recipient getRecipientForId(Context context, long recipientId, boolean asynchronous) {
    return provider.getRecipient(context, recipientId, asynchronous);
  }

  public static Recipients getRecipientsForIds(Context context, long[] recipientIds, boolean asynchronous) {
    return provider.getRecipients(context, recipientIds, asynchronous);
  }

  public static Recipients getRecipientsFromString(Context context, @NonNull String rawText, boolean asynchronous) {
    StringTokenizer tokenizer = new StringTokenizer(rawText, ",");
    List<String>    ids       = new LinkedList<>();

    while (tokenizer.hasMoreTokens()) {
      Optional<Long> id = getRecipientIdFromNumber(context, tokenizer.nextToken());

      if (id.isPresent()) {
        ids.add(String.valueOf(id.get()));
      }
    }

    return getRecipientsForIds(context, ids, asynchronous);
  }

  private static Recipients getRecipientsForIds(Context context, List<String> idStrings, boolean asynchronous) {
    long[]       ids      = new long[idStrings.size()];
    int          i        = 0;

    for (String id : idStrings) {
      ids[i++] = Long.parseLong(id);
    }

    return provider.getRecipients(context, ids, asynchronous);
  }

  private static Optional<Long> getRecipientIdFromNumber(Context context, String number) {
    number = number.trim();

    if (number.isEmpty()) return Optional.absent();

    if (hasBracketedNumber(number)) {
      number = parseBracketedNumber(number);
    }

    return Optional.of(CanonicalAddressDatabase.getInstance(context).getCanonicalAddressId(number));
  }

  private static boolean hasBracketedNumber(String recipient) {
    int openBracketIndex = recipient.indexOf('<');

    return (openBracketIndex != -1) &&
           (recipient.indexOf('>', openBracketIndex) != -1);
  }

  private static String parseBracketedNumber(String recipient) {
    int begin    = recipient.indexOf('<');
    int end      = recipient.indexOf('>', begin);
    String value = recipient.substring(begin + 1, end);

    return value;
  }

  public static void clearCache() {
    ContactPhotoFactory.clearCache();
    provider.clearCache();
  }

}


File: src/org/thoughtcrime/securesms/recipients/RecipientProvider.java
/**
 * Copyright (C) 2011 Whisper Systems
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.thoughtcrime.securesms.recipients;

import android.content.Context;
import android.database.Cursor;
import android.graphics.drawable.Drawable;
import android.net.Uri;
import android.provider.ContactsContract.Contacts;
import android.provider.ContactsContract.PhoneLookup;
import android.support.annotation.Nullable;
import android.util.Log;

import org.thoughtcrime.securesms.contacts.ContactPhotoFactory;
import org.thoughtcrime.securesms.database.CanonicalAddressDatabase;
import org.thoughtcrime.securesms.database.DatabaseFactory;
import org.thoughtcrime.securesms.database.GroupDatabase;
import org.thoughtcrime.securesms.database.RecipientPreferenceDatabase;
import org.thoughtcrime.securesms.database.RecipientPreferenceDatabase.RecipientsPreferences;
import org.thoughtcrime.securesms.util.GroupUtil;
import org.thoughtcrime.securesms.util.LRUCache;
import org.thoughtcrime.securesms.util.ListenableFutureTask;
import org.thoughtcrime.securesms.util.Util;

import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;

public class RecipientProvider {

  private static final Map<Long,Recipient>          recipientCache         = Collections.synchronizedMap(new LRUCache<Long,Recipient>(1000));
  private static final Map<RecipientIds,Recipients> recipientsCache        = Collections.synchronizedMap(new LRUCache<RecipientIds, Recipients>(1000));
  private static final ExecutorService              asyncRecipientResolver = Util.newSingleThreadedLifoExecutor();

  private static final String[] CALLER_ID_PROJECTION = new String[] {
    PhoneLookup.DISPLAY_NAME,
    PhoneLookup.LOOKUP_KEY,
    PhoneLookup._ID,
    PhoneLookup.NUMBER
  };

  Recipient getRecipient(Context context, long recipientId, boolean asynchronous) {
    Recipient cachedRecipient = recipientCache.get(recipientId);

    if      (cachedRecipient != null) return cachedRecipient;
    else if (asynchronous)            return getAsynchronousRecipient(context, recipientId);
    else                              return getSynchronousRecipient(context, recipientId);
  }

  Recipients getRecipients(Context context, long[] recipientIds, boolean asynchronous) {
    Recipients cachedRecipients = recipientsCache.get(new RecipientIds(recipientIds));
    if (cachedRecipients != null) return cachedRecipients;

    List<Recipient> recipientList = new LinkedList<>();

    for (long recipientId : recipientIds) {
      recipientList.add(getRecipient(context, recipientId, false));
    }

    if (asynchronous) cachedRecipients = new Recipients(recipientList, getRecipientsPreferencesAsync(context, recipientIds));
    else              cachedRecipients = new Recipients(recipientList, getRecipientsPreferencesSync(context, recipientIds));

    recipientsCache.put(new RecipientIds(recipientIds), cachedRecipients);
    return cachedRecipients;
  }

  private Recipient getSynchronousRecipient(final Context context, final long recipientId) {
    Log.w("RecipientProvider", "Cache miss [SYNC]!");

    final Recipient recipient;
    RecipientDetails details;
    String number = CanonicalAddressDatabase.getInstance(context).getAddressFromId(recipientId);
    final boolean isGroupRecipient = GroupUtil.isEncodedGroup(number);

    if (isGroupRecipient) details = getGroupRecipientDetails(context, number);
    else                  details = getRecipientDetails(context, number);

    if (details != null) {
      recipient = new Recipient(details.name, details.number, recipientId, details.contactUri, details.avatar);
    } else {
      final Drawable defaultPhoto        = isGroupRecipient
                                           ? ContactPhotoFactory.getDefaultGroupPhoto(context)
                                           : ContactPhotoFactory.getDefaultContactPhoto(context, null);

      recipient = new Recipient(null, number, recipientId, null, defaultPhoto);
    }

    recipientCache.put(recipientId, recipient);
    return recipient;
  }

  private Recipient getAsynchronousRecipient(final Context context, final long recipientId) {
    Log.w("RecipientProvider", "Cache miss [ASYNC]!");

    final String number = CanonicalAddressDatabase.getInstance(context).getAddressFromId(recipientId);
    final boolean isGroupRecipient = GroupUtil.isEncodedGroup(number);

    Callable<RecipientDetails> task = new Callable<RecipientDetails>() {
      @Override
      public RecipientDetails call() throws Exception {
        if (isGroupRecipient) return getGroupRecipientDetails(context, number);
        else                  return getRecipientDetails(context, number);
      }
    };

    ListenableFutureTask<RecipientDetails> future = new ListenableFutureTask<>(task);

    asyncRecipientResolver.submit(future);

    Drawable contactPhoto;

    if (isGroupRecipient) {
      contactPhoto        = ContactPhotoFactory.getDefaultGroupPhoto(context);
    } else {
      contactPhoto        = ContactPhotoFactory.getLoadingPhoto(context);
    }

    Recipient recipient = new Recipient(number, contactPhoto, recipientId, future);
    recipientCache.put(recipientId, recipient);

    return recipient;
  }

  void clearCache() {
    recipientCache.clear();
    recipientsCache.clear();
  }

  private RecipientDetails getRecipientDetails(Context context, String number) {
    Uri uri       = Uri.withAppendedPath(PhoneLookup.CONTENT_FILTER_URI, Uri.encode(number));
    Cursor cursor = context.getContentResolver().query(uri, CALLER_ID_PROJECTION,
                                                       null, null, null);

    try {
      if (cursor != null && cursor.moveToFirst()) {
        Uri      contactUri   = Contacts.getLookupUri(cursor.getLong(2), cursor.getString(1));
        String   name         = cursor.getString(3).equals(cursor.getString(0)) ? null : cursor.getString(0);
        Drawable contactPhoto = ContactPhotoFactory.getContactPhoto(context,
                                                                    Uri.withAppendedPath(Contacts.CONTENT_URI, cursor.getLong(2) + ""),
                                                                    name);
        return new RecipientDetails(cursor.getString(0), cursor.getString(3), contactUri, contactPhoto);
      }
    } finally {
      if (cursor != null)
        cursor.close();
    }

    return new RecipientDetails(null, number, null, ContactPhotoFactory.getDefaultContactPhoto(context, null));
  }

  private RecipientDetails getGroupRecipientDetails(Context context, String groupId) {
    try {
      GroupDatabase.GroupRecord record  = DatabaseFactory.getGroupDatabase(context)
                                                         .getGroup(GroupUtil.getDecodedId(groupId));

      if (record != null) {
        Drawable avatar = ContactPhotoFactory.getGroupContactPhoto(context, record.getAvatar());
        return new RecipientDetails(record.getTitle(), groupId, null, avatar);
      }

      return null;
    } catch (IOException e) {
      Log.w("RecipientProvider", e);
      return null;
    }
  }

  private @Nullable RecipientsPreferences getRecipientsPreferencesSync(Context context, long[] recipientIds) {
    return DatabaseFactory.getRecipientPreferenceDatabase(context)
                          .getRecipientsPreferences(recipientIds)
                          .orNull();
  }

  private ListenableFutureTask<RecipientsPreferences> getRecipientsPreferencesAsync(final Context context, final long[] recipientIds) {
    ListenableFutureTask<RecipientsPreferences> task = new ListenableFutureTask<>(new Callable<RecipientsPreferences>() {
      @Override
      public RecipientsPreferences call() throws Exception {
        return getRecipientsPreferencesSync(context, recipientIds);
      }
    });

    asyncRecipientResolver.execute(task);

    return task;
  }

  public static class RecipientDetails {
    public final String   name;
    public final String   number;
    public final Drawable avatar;
    public final Uri      contactUri;

    public RecipientDetails(String name, String number, Uri contactUri, Drawable avatar) {
      this.name          = name;
      this.number        = number;
      this.avatar        = avatar;
      this.contactUri    = contactUri;
    }
  }

  private static class RecipientIds {
    private final long[] ids;

    private RecipientIds(long[] ids) {
      this.ids = ids;
    }

    public boolean equals(Object other) {
      if (other == null || !(other instanceof RecipientIds)) return false;
      return Arrays.equals(this.ids, ((RecipientIds) other).ids);
    }

    public int hashCode() {
      return Arrays.hashCode(ids);
    }
  }



}

File: src/org/thoughtcrime/securesms/recipients/Recipients.java
/**
 * Copyright (C) 2015 Open Whisper Systems
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.thoughtcrime.securesms.recipients;

import android.content.Context;
import android.graphics.drawable.Drawable;
import android.net.Uri;
import android.support.annotation.Nullable;
import android.util.Log;
import android.util.Patterns;

import org.thoughtcrime.securesms.contacts.ContactPhotoFactory;
import org.thoughtcrime.securesms.database.RecipientPreferenceDatabase.RecipientsPreferences;
import org.thoughtcrime.securesms.database.RecipientPreferenceDatabase.VibrateState;
import org.thoughtcrime.securesms.recipients.Recipient.RecipientModifiedListener;
import org.thoughtcrime.securesms.util.FutureTaskListener;
import org.thoughtcrime.securesms.util.GroupUtil;
import org.thoughtcrime.securesms.util.ListenableFutureTask;
import org.thoughtcrime.securesms.util.NumberUtil;
import org.thoughtcrime.securesms.util.Util;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;
import java.util.Set;
import java.util.WeakHashMap;

public class Recipients implements Iterable<Recipient>, RecipientModifiedListener {

  private static final String TAG = Recipients.class.getSimpleName();

  private final Set<RecipientsModifiedListener> listeners = Collections.newSetFromMap(new WeakHashMap<RecipientsModifiedListener, Boolean>());
  private final List<Recipient> recipients;

  private Uri          ringtone          = null;
  private long         mutedUntil        = 0;
  private boolean      blocked           = false;
  private VibrateState vibrate           = VibrateState.DEFAULT;

  Recipients() {
    this(new LinkedList<Recipient>(), (RecipientsPreferences)null);
  }

  Recipients(List<Recipient> recipients, @Nullable RecipientsPreferences preferences) {
    this.recipients = recipients;

    if (preferences != null) {
      ringtone   = preferences.getRingtone();
      mutedUntil = preferences.getMuteUntil();
      vibrate    = preferences.getVibrateState();
      blocked    = preferences.isBlocked();
    }
  }

  Recipients(List<Recipient> recipients, ListenableFutureTask<RecipientsPreferences> preferences) {
    this.recipients = recipients;

    preferences.addListener(new FutureTaskListener<RecipientsPreferences>() {
      @Override
      public void onSuccess(RecipientsPreferences result) {
        if (result != null) {

          Set<RecipientsModifiedListener> localListeners;

          synchronized (Recipients.this) {
            ringtone   = result.getRingtone();
            mutedUntil = result.getMuteUntil();
            vibrate    = result.getVibrateState();
            blocked    = result.isBlocked();

            localListeners = new HashSet<>(listeners);
          }

          for (RecipientsModifiedListener listener : localListeners) {
            listener.onModified(Recipients.this);
          }
        }
      }

      @Override
      public void onFailure(Throwable error) {
        Log.w(TAG, error);
      }
    });
  }

  public synchronized @Nullable Uri getRingtone() {
    return ringtone;
  }

  public void setRingtone(Uri ringtone) {
    synchronized (this) {
      this.ringtone = ringtone;
    }

    notifyListeners();
  }

  public synchronized boolean isMuted() {
    return System.currentTimeMillis() <= mutedUntil;
  }

  public void setMuted(long mutedUntil) {
    synchronized (this) {
      this.mutedUntil = mutedUntil;
    }

    notifyListeners();
  }

  public synchronized boolean isBlocked() {
    return blocked;
  }

  public void setBlocked(boolean blocked) {
    synchronized (this) {
      this.blocked = blocked;
    }

    notifyListeners();
  }

  public synchronized VibrateState getVibrate() {
    return vibrate;
  }

  public void setVibrate(VibrateState vibrate) {
    synchronized (this) {
      this.vibrate = vibrate;
    }

    notifyListeners();
  }

  public Drawable getContactPhoto(Context context) {
    if (recipients.size() == 1) return recipients.get(0).getContactPhoto();
    else                        return ContactPhotoFactory.getDefaultGroupPhoto(context);
  }

  public synchronized void addListener(RecipientsModifiedListener listener) {
    if (listeners.isEmpty()) {
      for (Recipient recipient : recipients) {
        recipient.addListener(this);
      }
    }

    synchronized (this) {
      listeners.add(listener);
    }
  }

  public synchronized void removeListener(RecipientsModifiedListener listener) {
    listeners.remove(listener);

    if (listeners.isEmpty()) {
      for (Recipient recipient : recipients) {
        recipient.removeListener(this);
      }
    }
  }

  public boolean isEmailRecipient() {
    for (Recipient recipient : recipients) {
      if (NumberUtil.isValidEmail(recipient.getNumber()))
        return true;
    }

    return false;
  }

  public boolean isGroupRecipient() {
    return isSingleRecipient() && GroupUtil.isEncodedGroup(recipients.get(0).getNumber());
  }

  public boolean isEmpty() {
    return this.recipients.isEmpty();
  }

  public boolean isSingleRecipient() {
    return this.recipients.size() == 1;
  }

  public @Nullable Recipient getPrimaryRecipient() {
    if (!isEmpty())
      return this.recipients.get(0);
    else
      return null;
  }

  public List<Recipient> getRecipientsList() {
    return this.recipients;
  }

  public long[] getIds() {
    long[] ids = new long[recipients.size()];
    for (int i=0; i<recipients.size(); i++) {
      ids[i] = recipients.get(i).getRecipientId();
    }
    return ids;
  }

  public String getSortedIdsString() {
    Set<Long> recipientSet  = new HashSet<>();

    for (Recipient recipient : this.recipients) {
      recipientSet.add(recipient.getRecipientId());
    }

    long[] recipientArray = new long[recipientSet.size()];
    int i                 = 0;

    for (Long recipientId : recipientSet) {
      recipientArray[i++] = recipientId;
    }

    Arrays.sort(recipientArray);

    return Util.join(recipientArray, " ");
  }

  public String[] toNumberStringArray(boolean scrub) {
    String[] recipientsArray     = new String[recipients.size()];
    Iterator<Recipient> iterator = recipients.iterator();
    int i                        = 0;

    while (iterator.hasNext()) {
      String number = iterator.next().getNumber();

      if (scrub && number != null &&
          !Patterns.EMAIL_ADDRESS.matcher(number).matches() &&
          !GroupUtil.isEncodedGroup(number))
      {
        number = number.replaceAll("[^0-9+]", "");
      }

      recipientsArray[i++] = number;
    }

    return recipientsArray;
  }

  public String toShortString() {
    String fromString = "";

    for (int i=0;i<recipients.size();i++) {
      fromString += recipients.get(i).toShortString();

      if (i != recipients.size() -1 )
        fromString += ", ";
    }

    return fromString;
  }

  @Override
  public Iterator<Recipient> iterator() {
    return recipients.iterator();
  }

  @Override
  public void onModified(Recipient recipient) {
    notifyListeners();
  }

  private void notifyListeners() {
    Set<RecipientsModifiedListener> localListeners;

    synchronized (this) {
      localListeners = new HashSet<>(listeners);
    }

    for (RecipientsModifiedListener listener : localListeners) {
      listener.onModified(this);
    }
  }


  public interface RecipientsModifiedListener {
    public void onModified(Recipients recipient);
  }

}


File: src/org/thoughtcrime/securesms/service/ApplicationMigrationService.java
package org.thoughtcrime.securesms.service;

import android.app.Notification;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.graphics.BitmapFactory;
import android.os.Binder;
import android.os.Handler;
import android.os.IBinder;
import android.os.PowerManager;
import android.os.PowerManager.WakeLock;
import android.support.v4.app.NotificationCompat;
import android.util.Log;

import org.thoughtcrime.securesms.ConversationListActivity;
import org.thoughtcrime.securesms.R;
import org.thoughtcrime.securesms.crypto.MasterSecret;
import org.thoughtcrime.securesms.database.SmsMigrator;
import org.thoughtcrime.securesms.database.SmsMigrator.ProgressDescription;

import java.lang.ref.WeakReference;
import java.util.concurrent.Executor;
import java.util.concurrent.Executors;

// FIXME: This class is nuts.
public class ApplicationMigrationService extends Service
    implements SmsMigrator.SmsMigrationProgressListener
{
  private static final String TAG               = ApplicationMigrationService.class.getSimpleName();
  public  static final String MIGRATE_DATABASE  = "org.thoughtcrime.securesms.ApplicationMigration.MIGRATE_DATABSE";
  public  static final String COMPLETED_ACTION  = "org.thoughtcrime.securesms.ApplicationMigrationService.COMPLETED";
  private static final String PREFERENCES_NAME  = "SecureSMS";
  private static final String DATABASE_MIGRATED = "migrated";

  private final BroadcastReceiver completedReceiver = new CompletedReceiver();
  private final Binder binder                       = new ApplicationMigrationBinder();
  private final Executor executor                   = Executors.newSingleThreadExecutor();

  private WeakReference<Handler>     handler      = null;
  private NotificationCompat.Builder notification = null;
  private ImportState                state        = new ImportState(ImportState.STATE_IDLE, null);

  @Override
  public void onCreate() {
    registerCompletedReceiver();
  }

  @Override
  public int onStartCommand(Intent intent, int flags, int startId) {
    if (intent == null) return START_NOT_STICKY;

    if (intent.getAction() != null && intent.getAction().equals(MIGRATE_DATABASE)) {
      executor.execute(new ImportRunnable(intent));
    }

    return START_NOT_STICKY;
  }

  @Override
  public void onDestroy() {
    unregisterCompletedReceiver();
  }

  @Override
  public IBinder onBind(Intent intent) {
    return binder;
  }

  public void setImportStateHandler(Handler handler) {
    this.handler = new WeakReference<>(handler);
  }

  private void registerCompletedReceiver() {
    IntentFilter filter = new IntentFilter();
    filter.addAction(COMPLETED_ACTION);

    registerReceiver(completedReceiver, filter);
  }

  private void unregisterCompletedReceiver() {
    unregisterReceiver(completedReceiver);
  }

  private void notifyImportComplete() {
    Intent intent = new Intent();
    intent.setAction(COMPLETED_ACTION);

    sendOrderedBroadcast(intent, null);
  }

  @Override
  public void progressUpdate(ProgressDescription progress) {
    setState(new ImportState(ImportState.STATE_MIGRATING_IN_PROGRESS, progress));
  }

  public ImportState getState() {
    return state;
  }

  private void setState(ImportState state) {
    this.state = state;

    Handler handler = this.handler.get();

    if (handler != null) {
      handler.obtainMessage(state.state, state.progress).sendToTarget();
    }

    if (state.progress != null && state.progress.secondaryComplete == 0) {
      updateBackgroundNotification(state.progress.primaryTotal, state.progress.primaryComplete);
    }
  }

  private void updateBackgroundNotification(int total, int complete) {
    notification.setProgress(total, complete, false);

    ((NotificationManager)getSystemService(Context.NOTIFICATION_SERVICE))
      .notify(4242, notification.build());
  }

  private NotificationCompat.Builder initializeBackgroundNotification() {
    NotificationCompat.Builder builder = new NotificationCompat.Builder(this);

    builder.setSmallIcon(R.drawable.icon_notification);
    builder.setLargeIcon(BitmapFactory.decodeResource(getResources(), R.drawable.icon_notification));
    builder.setContentTitle(getString(R.string.ApplicationMigrationService_importing_text_messages));
    builder.setContentText(getString(R.string.ApplicationMigrationService_import_in_progress));
    builder.setOngoing(true);
    builder.setProgress(100, 0, false);
    builder.setContentIntent(PendingIntent.getActivity(this, 0, new Intent(this, ConversationListActivity.class), 0));

    stopForeground(true);
    startForeground(4242, builder.build());

    return builder;
  }

  private class ImportRunnable implements Runnable {
    private final MasterSecret masterSecret;

    public ImportRunnable(Intent intent) {
      this.masterSecret = intent.getParcelableExtra("master_secret");
      Log.w(TAG, "Service got mastersecret: " + masterSecret);
    }

    @Override
    public void run() {
      notification              = initializeBackgroundNotification();
      PowerManager powerManager = (PowerManager)getSystemService(Context.POWER_SERVICE);
      WakeLock     wakeLock     = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Migration");

      try {
        wakeLock.acquire();

        setState(new ImportState(ImportState.STATE_MIGRATING_BEGIN, null));

        SmsMigrator.migrateDatabase(ApplicationMigrationService.this,
                                    masterSecret,
                                    ApplicationMigrationService.this);

        setState(new ImportState(ImportState.STATE_MIGRATING_COMPLETE, null));

        setDatabaseImported(ApplicationMigrationService.this);
        stopForeground(true);
        notifyImportComplete();
        stopSelf();
      } finally {
        wakeLock.release();
      }
    }
  }

  public class ApplicationMigrationBinder extends Binder {
    public ApplicationMigrationService getService() {
      return ApplicationMigrationService.this;
    }
  }

  private class CompletedReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
      NotificationCompat.Builder builder = new NotificationCompat.Builder(context);
      builder.setSmallIcon(R.drawable.icon_notification);
      builder.setContentTitle("Import Complete");
      builder.setContentText("TextSecure system database import is complete.");
      builder.setContentIntent(PendingIntent.getActivity(context, 0, new Intent(context, ConversationListActivity.class), 0));
      builder.setWhen(System.currentTimeMillis());
      builder.setDefaults(Notification.DEFAULT_VIBRATE);
      builder.setAutoCancel(true);

      Notification notification = builder.build();
      ((NotificationManager)context.getSystemService(Context.NOTIFICATION_SERVICE)).notify(31337, notification);
    }
  }

  public static class ImportState {
    public static final int STATE_IDLE                  = 0;
    public static final int STATE_MIGRATING_BEGIN       = 1;
    public static final int STATE_MIGRATING_IN_PROGRESS = 2;
    public static final int STATE_MIGRATING_COMPLETE    = 3;

    public int                 state;
    public ProgressDescription progress;

    public ImportState(int state, ProgressDescription progress) {
      this.state    = state;
      this.progress = progress;
    }
  }

  public static boolean isDatabaseImported(Context context) {
    return context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)
              .getBoolean(DATABASE_MIGRATED, false);
  }

  public static void setDatabaseImported(Context context) {
    context.getSharedPreferences(PREFERENCES_NAME, 0).edit().putBoolean(DATABASE_MIGRATED, true).apply();
  }
}
