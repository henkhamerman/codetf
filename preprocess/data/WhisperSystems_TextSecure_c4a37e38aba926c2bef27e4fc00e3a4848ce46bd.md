Refactoring Types: ['Extract Method']
/ConversationActivity.java
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
package org.thoughtcrime.securesms;

import android.annotation.TargetApi;
import android.content.ActivityNotFoundException;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.res.TypedArray;
import android.graphics.Color;
import android.graphics.PorterDuff;
import android.graphics.PorterDuff.Mode;
import android.graphics.drawable.ColorDrawable;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Build;
import android.os.Bundle;
import android.provider.ContactsContract;
import android.support.annotation.NonNull;
import android.text.Editable;
import android.text.InputType;
import android.text.TextWatcher;
import android.util.Log;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.Menu;
import android.view.MenuInflater;
import android.view.MenuItem;
import android.view.View;
import android.view.View.OnClickListener;
import android.view.View.OnFocusChangeListener;
import android.view.View.OnKeyListener;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.ImageButton;
import android.widget.TextView;
import android.widget.TextView.OnEditorActionListener;
import android.widget.Toast;

import com.afollestad.materialdialogs.AlertDialogWrapper;
import com.google.protobuf.ByteString;

import org.thoughtcrime.securesms.TransportOptions.OnTransportChangedListener;
import org.thoughtcrime.securesms.color.MaterialColor;
import org.thoughtcrime.securesms.components.AnimatingToggle;
import org.thoughtcrime.securesms.components.ComposeText;
import org.thoughtcrime.securesms.components.KeyboardAwareLinearLayout;
import org.thoughtcrime.securesms.components.KeyboardAwareLinearLayout.OnKeyboardShownListener;
import org.thoughtcrime.securesms.components.SendButton;
import org.thoughtcrime.securesms.components.emoji.EmojiDrawer.EmojiEventListener;
import org.thoughtcrime.securesms.components.emoji.EmojiPopup;
import org.thoughtcrime.securesms.components.emoji.EmojiToggle;
import org.thoughtcrime.securesms.contacts.ContactAccessor;
import org.thoughtcrime.securesms.contacts.ContactAccessor.ContactData;
import org.thoughtcrime.securesms.crypto.MasterCipher;
import org.thoughtcrime.securesms.crypto.MasterSecret;
import org.thoughtcrime.securesms.crypto.SecurityEvent;
import org.thoughtcrime.securesms.database.DatabaseFactory;
import org.thoughtcrime.securesms.database.DraftDatabase;
import org.thoughtcrime.securesms.database.DraftDatabase.Draft;
import org.thoughtcrime.securesms.database.DraftDatabase.Drafts;
import org.thoughtcrime.securesms.database.GroupDatabase;
import org.thoughtcrime.securesms.database.MmsSmsColumns.Types;
import org.thoughtcrime.securesms.database.ThreadDatabase;
import org.thoughtcrime.securesms.mms.AttachmentManager;
import org.thoughtcrime.securesms.mms.AttachmentTypeSelectorAdapter;
import org.thoughtcrime.securesms.mms.MediaTooLargeException;
import org.thoughtcrime.securesms.mms.MmsMediaConstraints;
import org.thoughtcrime.securesms.mms.OutgoingGroupMediaMessage;
import org.thoughtcrime.securesms.mms.OutgoingMediaMessage;
import org.thoughtcrime.securesms.mms.OutgoingSecureMediaMessage;
import org.thoughtcrime.securesms.mms.Slide;
import org.thoughtcrime.securesms.mms.SlideDeck;
import org.thoughtcrime.securesms.notifications.MessageNotifier;
import org.thoughtcrime.securesms.recipients.Recipient;
import org.thoughtcrime.securesms.recipients.RecipientFactory;
import org.thoughtcrime.securesms.recipients.RecipientFormattingException;
import org.thoughtcrime.securesms.recipients.Recipients;
import org.thoughtcrime.securesms.recipients.Recipients.RecipientsModifiedListener;
import org.thoughtcrime.securesms.service.KeyCachingService;
import org.thoughtcrime.securesms.sms.MessageSender;
import org.thoughtcrime.securesms.sms.OutgoingEncryptedMessage;
import org.thoughtcrime.securesms.sms.OutgoingEndSessionMessage;
import org.thoughtcrime.securesms.sms.OutgoingTextMessage;
import org.thoughtcrime.securesms.util.BitmapDecodingException;
import org.thoughtcrime.securesms.util.CharacterCalculator.CharacterState;
import org.thoughtcrime.securesms.util.Dialogs;
import org.thoughtcrime.securesms.util.DirectoryHelper;
import org.thoughtcrime.securesms.util.DynamicLanguage;
import org.thoughtcrime.securesms.util.DynamicTheme;
import org.thoughtcrime.securesms.util.GroupUtil;
import org.thoughtcrime.securesms.util.TextSecurePreferences;
import org.thoughtcrime.securesms.util.Util;
import org.thoughtcrime.securesms.util.concurrent.ListenableFuture;
import org.thoughtcrime.securesms.util.concurrent.SettableFuture;
import org.whispersystems.libaxolotl.InvalidMessageException;
import org.whispersystems.libaxolotl.util.guava.Optional;

import java.io.IOException;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.List;

import static org.thoughtcrime.securesms.TransportOption.Type;
import static org.thoughtcrime.securesms.database.GroupDatabase.GroupRecord;
import static org.whispersystems.textsecure.internal.push.TextSecureProtos.GroupContext;

/**
 * Activity for displaying a message thread, as well as
 * composing/sending a new message into that thread.
 *
 * @author Moxie Marlinspike
 *
 */
public class ConversationActivity extends PassphraseRequiredActionBarActivity
    implements ConversationFragment.ConversationFragmentListener,
               AttachmentManager.AttachmentListener,
               RecipientsModifiedListener,
               OnKeyboardShownListener
{
  private static final String TAG = ConversationActivity.class.getSimpleName();

  public static final String RECIPIENTS_EXTRA        = "recipients";
  public static final String THREAD_ID_EXTRA         = "thread_id";
  public static final String DRAFT_TEXT_EXTRA        = "draft_text";
  public static final String DRAFT_IMAGE_EXTRA       = "draft_image";
  public static final String DRAFT_AUDIO_EXTRA       = "draft_audio";
  public static final String DRAFT_VIDEO_EXTRA       = "draft_video";
  public static final String DISTRIBUTION_TYPE_EXTRA = "distribution_type";

  private static final int PICK_IMAGE        = 1;
  private static final int PICK_VIDEO        = 2;
  private static final int PICK_AUDIO        = 3;
  private static final int PICK_CONTACT_INFO = 4;
  private static final int GROUP_EDIT        = 5;
  private static final int CAPTURE_PHOTO     = 6;

  private   MasterSecret              masterSecret;
  protected ComposeText               composeText;
  private   AnimatingToggle           buttonToggle;
  private   SendButton                sendButton;
  private   ImageButton               attachButton;
  protected ConversationTitleView     titleView;
  private   TextView                  charactersLeft;
  private   ConversationFragment      fragment;
  private   Button                    unblockButton;
  private   KeyboardAwareLinearLayout container;
  private   View                      composePanel;
  private   View                      composeBubble;

  private AttachmentTypeSelectorAdapter attachmentAdapter;
  private AttachmentManager             attachmentManager;
  private BroadcastReceiver             securityUpdateReceiver;
  private BroadcastReceiver             groupUpdateReceiver;
  private Optional<EmojiPopup>          emojiPopup = Optional.absent();
  private EmojiToggle                   emojiToggle;

  private Recipients recipients;
  private long       threadId;
  private int        distributionType;
  private boolean    isEncryptedConversation;
  private boolean    isMmsEnabled = true;

  private DynamicTheme    dynamicTheme    = new DynamicTheme();
  private DynamicLanguage dynamicLanguage = new DynamicLanguage();

  @TargetApi(Build.VERSION_CODES.KITKAT)
  @Override
  protected void onPreCreate() {
    dynamicTheme.onCreate(this);
    dynamicLanguage.onCreate(this);
  }

  @Override
  protected void onCreate(Bundle state, @NonNull MasterSecret masterSecret) {
    this.masterSecret = masterSecret;

    setContentView(R.layout.conversation_activity);

    fragment = initFragment(R.id.fragment_content, new ConversationFragment(),
                            masterSecret, dynamicLanguage.getCurrentLocale());

    initializeReceivers();
    initializeActionBar();
    initializeViews();
    initializeResources();
    initializeDraft();
  }

  @Override
  protected void onNewIntent(Intent intent) {
    Log.w(TAG, "onNewIntent()");

    if (!Util.isEmpty(composeText) || attachmentManager.isAttachmentPresent()) {
      saveDraft();
      attachmentManager.clear();
      composeText.setText("");
    }

    setIntent(intent);
    initializeResources();
    initializeDraft();

    if (fragment != null) {
      fragment.onNewIntent();
    }
  }

  @Override
  protected void onResume() {
    super.onResume();
    dynamicTheme.onResume(this);
    dynamicLanguage.onResume(this);

    initializeSecurity();
    initializeEnabledCheck();
    initializeMmsEnabledCheck();
    initializeIme();

    titleView.setTitle(recipients);
    setActionBarColor(recipients.getColor());
    setBlockedUserState(recipients);
    calculateCharactersRemaining();

    MessageNotifier.setVisibleThread(threadId);
    markThreadAsRead();
  }

  @Override
  protected void onPause() {
    super.onPause();
    MessageNotifier.setVisibleThread(-1L);
    if (isFinishing()) overridePendingTransition(R.anim.fade_scale_in, R.anim.slide_to_right);
  }

  @Override
  protected void onDestroy() {
    saveDraft();
    if (recipients != null)             recipients.removeListener(this);
    if (securityUpdateReceiver != null) unregisterReceiver(securityUpdateReceiver);
    if (groupUpdateReceiver != null)    unregisterReceiver(groupUpdateReceiver);
    super.onDestroy();
  }

  @Override
  public void onActivityResult(int reqCode, int resultCode, Intent data) {
    Log.w(TAG, "onActivityResult called: " + reqCode + ", " + resultCode + " , " + data);
    super.onActivityResult(reqCode, resultCode, data);

    if ((data == null && reqCode != CAPTURE_PHOTO) || resultCode != RESULT_OK) return;

    switch (reqCode) {
    case PICK_IMAGE:
      addAttachmentImage(data.getData());
      break;
    case PICK_VIDEO:
      addAttachmentVideo(data.getData());
      break;
    case PICK_AUDIO:
      addAttachmentAudio(data.getData());
      break;
    case PICK_CONTACT_INFO:
      addAttachmentContactInfo(data.getData());
      break;
    case CAPTURE_PHOTO:
      if (attachmentManager.getCaptureFile() != null) {
        addAttachmentImage(Uri.fromFile(attachmentManager.getCaptureFile()));
      }
      break;
    case GROUP_EDIT:
      this.recipients = RecipientFactory.getRecipientsForIds(this, data.getLongArrayExtra(GroupCreateActivity.GROUP_RECIPIENT_EXTRA), true);
      titleView.setTitle(recipients);
      setBlockedUserState(recipients);
      supportInvalidateOptionsMenu();
      break;
    }
  }

  @Override
  public boolean onPrepareOptionsMenu(Menu menu) {
    MenuInflater inflater = this.getMenuInflater();
    menu.clear();

    if (isSingleConversation() && isEncryptedConversation) {
      inflater.inflate(R.menu.conversation_secure_identity, menu);
      inflater.inflate(R.menu.conversation_secure_sms, menu.findItem(R.id.menu_security).getSubMenu());
    } else if (isSingleConversation()) {
      inflater.inflate(R.menu.conversation_insecure, menu);
    }

    if (isSingleConversation()) {
      inflater.inflate(R.menu.conversation_callable, menu);
    } else if (isGroupConversation()) {
      inflater.inflate(R.menu.conversation_group_options, menu);

      if (!isPushGroupConversation()) {
        inflater.inflate(R.menu.conversation_mms_group_options, menu);
        if (distributionType == ThreadDatabase.DistributionTypes.BROADCAST) {
          menu.findItem(R.id.menu_distribution_broadcast).setChecked(true);
        } else {
          menu.findItem(R.id.menu_distribution_conversation).setChecked(true);
        }
      } else if (isActiveGroup()) {
        inflater.inflate(R.menu.conversation_push_group_options, menu);
      }
    }

    inflater.inflate(R.menu.conversation, menu);

    if (recipients != null && recipients.isMuted()) inflater.inflate(R.menu.conversation_muted, menu);
    else                                            inflater.inflate(R.menu.conversation_unmuted, menu);

    if (isSingleConversation() && getRecipients().getPrimaryRecipient().getContactUri() == null) {
      inflater.inflate(R.menu.conversation_add_to_contacts, menu);
    }

    super.onPrepareOptionsMenu(menu);
    return true;
  }

  @Override
  public boolean onOptionsItemSelected(MenuItem item) {
    super.onOptionsItemSelected(item);
    switch (item.getItemId()) {
    case R.id.menu_call:                      handleDial(getRecipients().getPrimaryRecipient()); return true;
    case R.id.menu_delete_thread:             handleDeleteThread();                              return true;
    case R.id.menu_add_attachment:            handleAddAttachment();                             return true;
    case R.id.menu_view_media:                handleViewMedia();                                 return true;
    case R.id.menu_add_to_contacts:           handleAddToContacts();                             return true;
    case R.id.menu_abort_session:             handleAbortSecureSession();                        return true;
    case R.id.menu_verify_identity:           handleVerifyIdentity();                            return true;
    case R.id.menu_group_recipients:          handleDisplayGroupRecipients();                    return true;
    case R.id.menu_distribution_broadcast:    handleDistributionBroadcastEnabled(item);          return true;
    case R.id.menu_distribution_conversation: handleDistributionConversationEnabled(item);       return true;
    case R.id.menu_edit_group:                handleEditPushGroup();                             return true;
    case R.id.menu_leave:                     handleLeavePushGroup();                            return true;
    case R.id.menu_invite:                    handleInviteLink();                                return true;
    case R.id.menu_mute_notifications:        handleMuteNotifications();                         return true;
    case R.id.menu_unmute_notifications:      handleUnmuteNotifications();                       return true;
    case R.id.menu_conversation_settings:     handleConversationSettings();                      return true;
    case android.R.id.home:                   handleReturnToConversationList();                  return true;
    }

    return false;
  }

  @Override
  public void onBackPressed() {
    if (isEmojiDrawerOpen()) {
      hideEmojiPopup(false);
    } else {
      super.onBackPressed();
    }
  }

  @Override
  public void onKeyboardShown() {
    hideEmojiPopup(true);
  }

  //////// Event Handlers

  private void handleReturnToConversationList() {
    Intent intent = new Intent(this, ConversationListActivity.class);
    intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);
    startActivity(intent);
    finish();
  }

  private void handleMuteNotifications() {
    MuteDialog.show(this, new MuteDialog.MuteSelectionListener() {
      @Override
      public void onMuted(final long until) {
        recipients.setMuted(until);

        new AsyncTask<Void, Void, Void>() {
          @Override
          protected Void doInBackground(Void... params) {
            DatabaseFactory.getRecipientPreferenceDatabase(ConversationActivity.this)
                           .setMuted(recipients, until);

            return null;
          }
        }.execute();
      }
    });
  }

  private void handleConversationSettings() {
    titleView.performClick();
  }

  private void handleUnmuteNotifications() {
    recipients.setMuted(0);

    new AsyncTask<Void, Void, Void>() {
      @Override
      protected Void doInBackground(Void... params) {
        DatabaseFactory.getRecipientPreferenceDatabase(ConversationActivity.this)
                       .setMuted(recipients, 0);

        return null;
      }
    }.execute();
  }

  private void handleUnblock() {
    new AlertDialogWrapper.Builder(this)
        .setTitle(R.string.ConversationActivity_unblock_question)
        .setMessage(R.string.ConversationActivity_are_you_sure_you_want_to_unblock_this_contact)
        .setNegativeButton(android.R.string.cancel, null)
        .setPositiveButton(R.string.ConversationActivity_unblock, new DialogInterface.OnClickListener() {
          @Override
          public void onClick(DialogInterface dialog, int which) {
            recipients.setBlocked(false);

            new AsyncTask<Void, Void, Void>() {
              @Override
              protected Void doInBackground(Void... params) {
                DatabaseFactory.getRecipientPreferenceDatabase(ConversationActivity.this)
                               .setBlocked(recipients, false);
                return null;
              }
            }.execute();
          }
        }).show();
  }

  private void handleInviteLink() {
    try {
      boolean a = SecureRandom.getInstance("SHA1PRNG").nextBoolean();
      if (a) composeText.appendInvite(getString(R.string.ConversationActivity_get_with_it, "http://sgnl.link/1IvurmD"));
      else   composeText.appendInvite(getString(R.string.ConversationActivity_lets_use_this_to_chat, "http://sgnl.link/1CYCQQN"));
    } catch (NoSuchAlgorithmException e) {
      throw new AssertionError(e);
    }
  }

  private void handleVerifyIdentity() {
    Intent verifyIdentityIntent = new Intent(this, VerifyIdentityActivity.class);
    verifyIdentityIntent.putExtra("recipient", getRecipients().getPrimaryRecipient().getRecipientId());
    startActivity(verifyIdentityIntent);
  }

  private void handleAbortSecureSession() {
    AlertDialogWrapper.Builder builder = new AlertDialogWrapper.Builder(this);
    builder.setTitle(R.string.ConversationActivity_abort_secure_session_confirmation);
    builder.setIconAttribute(R.attr.dialog_alert_icon);
    builder.setCancelable(true);
    builder.setMessage(R.string.ConversationActivity_are_you_sure_that_you_want_to_abort_this_secure_session_question);
    builder.setPositiveButton(R.string.yes, new DialogInterface.OnClickListener() {
      @Override
      public void onClick(DialogInterface dialog, int which) {
        if (isSingleConversation()) {
          final Context context = getApplicationContext();

          OutgoingEndSessionMessage endSessionMessage =
              new OutgoingEndSessionMessage(new OutgoingTextMessage(getRecipients(), "TERMINATE"));

          new AsyncTask<OutgoingEndSessionMessage, Void, Long>() {
            @Override
            protected Long doInBackground(OutgoingEndSessionMessage... messages) {
              return MessageSender.send(context, masterSecret, messages[0], threadId, false);
            }

            @Override
            protected void onPostExecute(Long result) {
              sendComplete(result);
            }
          }.execute(endSessionMessage);
        }
      }
    });
    builder.setNegativeButton(R.string.no, null);
    builder.show();
  }

  private void handleViewMedia() {
    Intent intent = new Intent(this, MediaOverviewActivity.class);
    intent.putExtra(MediaOverviewActivity.THREAD_ID_EXTRA, threadId);
    intent.putExtra(MediaOverviewActivity.RECIPIENT_EXTRA, recipients.getPrimaryRecipient().getRecipientId());
    startActivity(intent);
  }

  private void handleLeavePushGroup() {
    if (getRecipients() == null) {
      Toast.makeText(this, getString(R.string.ConversationActivity_invalid_recipient),
                     Toast.LENGTH_LONG).show();
      return;
    }

    AlertDialogWrapper.Builder builder = new AlertDialogWrapper.Builder(this);
    builder.setTitle(getString(R.string.ConversationActivity_leave_group));
    builder.setIconAttribute(R.attr.dialog_info_icon);
    builder.setCancelable(true);
    builder.setMessage(getString(R.string.ConversationActivity_are_you_sure_you_want_to_leave_this_group));
    builder.setPositiveButton(R.string.yes, new DialogInterface.OnClickListener() {
      @Override
      public void onClick(DialogInterface dialog, int which) {
        Context self = ConversationActivity.this;
        try {
          byte[] groupId = GroupUtil.getDecodedId(getRecipients().getPrimaryRecipient().getNumber());
          DatabaseFactory.getGroupDatabase(self).setActive(groupId, false);

          GroupContext context = GroupContext.newBuilder()
                                             .setId(ByteString.copyFrom(groupId))
                                             .setType(GroupContext.Type.QUIT)
                                             .build();

          OutgoingGroupMediaMessage outgoingMessage = new OutgoingGroupMediaMessage(self, getRecipients(),
                                                                                    context, null);
          MessageSender.send(self, masterSecret, outgoingMessage, threadId, false);
          DatabaseFactory.getGroupDatabase(self).remove(groupId, TextSecurePreferences.getLocalNumber(self));
          initializeEnabledCheck();
        } catch (IOException e) {
          Log.w(TAG, e);
          Toast.makeText(self, R.string.ConversationActivity_error_leaving_group, Toast.LENGTH_LONG).show();
        }
      }
    });

    builder.setNegativeButton(R.string.no, null);
    builder.show();
  }

  private void handleEditPushGroup() {
    Intent intent = new Intent(ConversationActivity.this, GroupCreateActivity.class);
    intent.putExtra(GroupCreateActivity.GROUP_RECIPIENT_EXTRA, recipients.getPrimaryRecipient().getRecipientId());
    startActivityForResult(intent, GROUP_EDIT);
  }

  private void handleDistributionBroadcastEnabled(MenuItem item) {
    distributionType = ThreadDatabase.DistributionTypes.BROADCAST;
    item.setChecked(true);

    if (threadId != -1) {
      new AsyncTask<Void, Void, Void>() {
        @Override
        protected Void doInBackground(Void... params) {
          DatabaseFactory.getThreadDatabase(ConversationActivity.this)
                         .setDistributionType(threadId, ThreadDatabase.DistributionTypes.BROADCAST);
          return null;
        }
      }.execute();
    }
  }

  private void handleDistributionConversationEnabled(MenuItem item) {
    distributionType = ThreadDatabase.DistributionTypes.CONVERSATION;
    item.setChecked(true);

    if (threadId != -1) {
      new AsyncTask<Void, Void, Void>() {
        @Override
        protected Void doInBackground(Void... params) {
          DatabaseFactory.getThreadDatabase(ConversationActivity.this)
                         .setDistributionType(threadId, ThreadDatabase.DistributionTypes.CONVERSATION);
          return null;
        }
      }.execute();
    }
  }

  private void handleDial(Recipient recipient) {
    try {
      if (recipient == null) return;

      Intent dialIntent = new Intent(Intent.ACTION_DIAL,
                              Uri.parse("tel:" + recipient.getNumber()));
      startActivity(dialIntent);
    } catch (ActivityNotFoundException anfe) {
      Log.w(TAG, anfe);
      Dialogs.showAlertDialog(this,
                           getString(R.string.ConversationActivity_calls_not_supported),
                           getString(R.string.ConversationActivity_this_device_does_not_appear_to_support_dial_actions));
    }
  }

  private void handleDisplayGroupRecipients() {
    new GroupMembersDialog(this, getRecipients()).display();
  }

  private void handleDeleteThread() {
    AlertDialogWrapper.Builder builder = new AlertDialogWrapper.Builder(this);
    builder.setTitle(R.string.ConversationActivity_delete_thread_confirmation);
    builder.setIconAttribute(R.attr.dialog_alert_icon);
    builder.setCancelable(true);
    builder.setMessage(R.string.ConversationActivity_are_you_sure_that_you_want_to_permanently_delete_this_conversation_question);
    builder.setPositiveButton(R.string.yes, new DialogInterface.OnClickListener() {
      @Override
      public void onClick(DialogInterface dialog, int which) {
        if (threadId > 0) {
          DatabaseFactory.getThreadDatabase(ConversationActivity.this).deleteConversation(threadId);
        }
        composeText.getText().clear();
        threadId = -1;
        finish();
      }
    });

    builder.setNegativeButton(R.string.no, null);
    builder.show();
  }

  private void handleAddToContacts() {
    final Intent intent = new Intent(Intent.ACTION_INSERT_OR_EDIT);
    intent.putExtra(ContactsContract.Intents.Insert.PHONE, recipients.getPrimaryRecipient().getNumber());
    intent.setType(ContactsContract.Contacts.CONTENT_ITEM_TYPE);
    startActivity(intent);
  }

  private void handleAddAttachment() {
    if (this.isMmsEnabled || DirectoryHelper.isPushDestination(this, getRecipients())) {
      new AlertDialogWrapper.Builder(this).setAdapter(attachmentAdapter, new AttachmentTypeListener())
                                          .show();
    } else {
      handleManualMmsRequired();
    }
  }

  private void handleManualMmsRequired() {
    Toast.makeText(this, R.string.MmsDownloader_error_reading_mms_settings, Toast.LENGTH_LONG).show();

    Intent intent = new Intent(this, PromptMmsActivity.class);
    intent.putExtras(getIntent().getExtras());
    startActivity(intent);
  }

  ///// Initializers

  private void initializeDraft() {
    String draftText  = getIntent().getStringExtra(DRAFT_TEXT_EXTRA);
    Uri    draftImage = getIntent().getParcelableExtra(DRAFT_IMAGE_EXTRA);
    Uri    draftAudio = getIntent().getParcelableExtra(DRAFT_AUDIO_EXTRA);
    Uri    draftVideo = getIntent().getParcelableExtra(DRAFT_VIDEO_EXTRA);

    if (draftText != null)  composeText.setText(draftText);
    if (draftImage != null) addAttachmentImage(draftImage);
    if (draftAudio != null) addAttachmentAudio(draftAudio);
    if (draftVideo != null) addAttachmentVideo(draftVideo);

    if (draftText == null && draftImage == null && draftAudio == null && draftVideo == null) {
      initializeDraftFromDatabase();
    } else {
      updateToggleButtonState();
    }
  }

  private void initializeEnabledCheck() {
    boolean enabled = !(isPushGroupConversation() && !isActiveGroup());
    composeText.setEnabled(enabled);
    sendButton.setEnabled(enabled);
  }

  private void initializeDraftFromDatabase() {
    new AsyncTask<Void, Void, List<Draft>>() {
      @Override
      protected List<Draft> doInBackground(Void... params) {
        MasterCipher masterCipher   = new MasterCipher(masterSecret);
        DraftDatabase draftDatabase = DatabaseFactory.getDraftDatabase(ConversationActivity.this);
        List<Draft> results         = draftDatabase.getDrafts(masterCipher, threadId);

        draftDatabase.clearDrafts(threadId);

        return results;
      }

      @Override
      protected void onPostExecute(List<Draft> drafts) {
        for (Draft draft : drafts) {
          if (draft.getType().equals(Draft.TEXT)) {
            composeText.setText(draft.getValue());
          } else if (draft.getType().equals(Draft.IMAGE)) {
            addAttachmentImage(Uri.parse(draft.getValue()));
          } else if (draft.getType().equals(Draft.AUDIO)) {
            addAttachmentAudio(Uri.parse(draft.getValue()));
          } else if (draft.getType().equals(Draft.VIDEO)) {
            addAttachmentVideo(Uri.parse(draft.getValue()));
          }
        }

        updateToggleButtonState();
      }
    }.execute();
  }

  private void initializeSecurity() {
    boolean isMediaMessage = !recipients.isSingleRecipient() || attachmentManager.isAttachmentPresent();
    this.isEncryptedConversation = DirectoryHelper.isPushDestination(this, getRecipients());

    sendButton.resetAvailableTransports(isMediaMessage);

    if (!isEncryptedConversation)      sendButton.disableTransport(Type.TEXTSECURE);
    if (recipients.isGroupRecipient()) sendButton.disableTransport(Type.SMS);

    if (isEncryptedConversation) sendButton.setDefaultTransport(Type.TEXTSECURE);
    else                         sendButton.setDefaultTransport(Type.SMS);

    calculateCharactersRemaining();
    supportInvalidateOptionsMenu();
  }

  private void initializeMmsEnabledCheck() {
    new AsyncTask<Void, Void, Boolean>() {
      @Override
      protected Boolean doInBackground(Void... params) {
        return Util.isMmsCapable(ConversationActivity.this);
      }

      @Override
      protected void onPostExecute(Boolean isMmsEnabled) {
        ConversationActivity.this.isMmsEnabled = isMmsEnabled;
      }
    }.execute();
  }

  private void initializeIme() {
    if (TextSecurePreferences.isEnterSendsEnabled(this)) {
      composeText.setInputType (composeText.getInputType()  & ~InputType.TYPE_TEXT_FLAG_MULTI_LINE);
      composeText.setImeOptions(composeText.getImeOptions() & ~EditorInfo.IME_FLAG_NO_ENTER_ACTION);
    } else {
      composeText.setInputType (composeText.getInputType()  | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
      composeText.setImeOptions(composeText.getImeOptions() | EditorInfo.IME_FLAG_NO_ENTER_ACTION);
    }
    composeText.setOnEditorActionListener(new OnEditorActionListener() {
      @Override public boolean onEditorAction(TextView v, int actionId, KeyEvent event) {
        if (actionId == EditorInfo.IME_ACTION_SEND) {
          sendMessage();
          return true;
        }
        return false;
      }
    });
  }

  private void initializeViews() {
    titleView      = (ConversationTitleView)     getSupportActionBar().getCustomView();
    buttonToggle   = (AnimatingToggle)           findViewById(R.id.button_toggle);
    sendButton     = (SendButton)                findViewById(R.id.send_button);
    attachButton   = (ImageButton)               findViewById(R.id.attach_button);
    composeText    = (ComposeText)               findViewById(R.id.embedded_text_editor);
    charactersLeft = (TextView)                  findViewById(R.id.space_left);
    emojiToggle    = (EmojiToggle)               findViewById(R.id.emoji_toggle);
    unblockButton  = (Button)                    findViewById(R.id.unblock_button);
    composePanel   =                             findViewById(R.id.bottom_panel);
    composeBubble  =                             findViewById(R.id.compose_bubble);
    container      = (KeyboardAwareLinearLayout) findViewById(R.id.layout_container);

    container.addOnKeyboardShownListener(this);

    int[]      attributes   = new int[]{R.attr.conversation_item_bubble_background};
    TypedArray colors       = obtainStyledAttributes(attributes);
    int        defaultColor = colors.getColor(0, Color.WHITE);
    composeBubble.getBackground().setColorFilter(defaultColor, PorterDuff.Mode.MULTIPLY);
    colors.recycle();

    attachmentAdapter = new AttachmentTypeSelectorAdapter(this);
    attachmentManager = new AttachmentManager(this, this);

    SendButtonListener        sendButtonListener        = new SendButtonListener();
    ComposeKeyPressedListener composeKeyPressedListener = new ComposeKeyPressedListener();

    attachButton.setOnClickListener(new AttachButtonListener());
    sendButton.setOnClickListener(sendButtonListener);
    sendButton.setEnabled(true);
    sendButton.addOnTransportChangedListener(new OnTransportChangedListener() {
      @Override
      public void onChange(TransportOption newTransport) {
        calculateCharactersRemaining();
        composeText.setHint(newTransport.getComposeHint());
        composeText.setImeActionLabel(newTransport.getComposeHint(), EditorInfo.IME_ACTION_SEND);
        buttonToggle.getBackground().setColorFilter(newTransport.getBackgroundColor(), Mode.MULTIPLY);
      }
    });

    titleView.setOnClickListener(new OnClickListener() {
      @Override
      public void onClick(View v) {
        Intent intent = new Intent(ConversationActivity.this, RecipientPreferenceActivity.class);
        intent.putExtra(RecipientPreferenceActivity.RECIPIENTS_EXTRA, recipients.getIds());

        startActivitySceneTransition(intent, titleView.findViewById(R.id.title), "recipient_name");
      }
    });

    unblockButton.setOnClickListener(new OnClickListener() {
      @Override
      public void onClick(View v) {
        handleUnblock();
      }
    });

    composeText.setOnKeyListener(composeKeyPressedListener);
    composeText.addTextChangedListener(composeKeyPressedListener);
    composeText.setOnEditorActionListener(sendButtonListener);
    composeText.setOnClickListener(composeKeyPressedListener);
    composeText.setOnFocusChangeListener(composeKeyPressedListener);
    emojiToggle.setOnClickListener(new EmojiToggleListener());
  }

  protected void initializeActionBar() {
    getSupportActionBar().setDisplayHomeAsUpEnabled(true);
    getSupportActionBar().setCustomView(R.layout.conversation_title_view);
    getSupportActionBar().setDisplayShowCustomEnabled(true);
    getSupportActionBar().setDisplayShowTitleEnabled(false);
  }

  private EmojiPopup getEmojiPopup() {
    if (!emojiPopup.isPresent()) {
      EmojiPopup emojiPopup = new EmojiPopup(getWindow().getDecorView());
      emojiPopup.setEmojiEventListener(new EmojiEventListener() {
        @Override public void onKeyEvent(KeyEvent keyEvent) {
          composeText.dispatchKeyEvent(keyEvent);
        }

        @Override public void onEmojiSelected(String emoji) {
          composeText.insertEmoji(emoji);
        }
      });
      this.emojiPopup = Optional.of(emojiPopup);
    }
    return emojiPopup.get();
  }

  private void showEmojiPopup() {
    int height = Math.max(getResources().getDimensionPixelSize(R.dimen.min_emoji_drawer_height),
                          container.getKeyboardHeight());
    container.padForCustomKeyboard(height);
    getEmojiPopup().show(height);
    emojiToggle.setToIme();
  }

  private void hideEmojiPopup(boolean expectingKeyboard) {
    if (isEmojiDrawerOpen()) {
      getEmojiPopup().dismiss();
      if (!expectingKeyboard) {
        container.unpadForCustomKeyboard();
      }
    }
    emojiToggle.setToEmoji();
  }

  private boolean isEmojiDrawerOpen() {
    return emojiPopup.isPresent() && emojiPopup.get().isShowing();
  }

  private void initializeResources() {
    recipients       = RecipientFactory.getRecipientsForIds(this, getIntent().getLongArrayExtra(RECIPIENTS_EXTRA), true);
    threadId         = getIntent().getLongExtra(THREAD_ID_EXTRA, -1);
    distributionType = getIntent().getIntExtra(DISTRIBUTION_TYPE_EXTRA, ThreadDatabase.DistributionTypes.DEFAULT);

    recipients.addListener(this);
  }

  @Override
  public void onModified(final Recipients recipients) {
    titleView.post(new Runnable() {
      @Override
      public void run() {
        titleView.setTitle(recipients);
        setBlockedUserState(recipients);
        setActionBarColor(recipients.getColor());
      }
    });
  }

  private void initializeReceivers() {
    securityUpdateReceiver = new BroadcastReceiver() {
      @Override
      public void onReceive(Context context, Intent intent) {
        long eventThreadId = intent.getLongExtra("thread_id", -1);

        if (eventThreadId == threadId || eventThreadId == -2) {
          initializeSecurity();
          calculateCharactersRemaining();
        }
      }
    };

    groupUpdateReceiver = new BroadcastReceiver() {
      @Override
      public void onReceive(Context context, Intent intent) {
        Log.w("ConversationActivity", "Group update received...");
        if (recipients != null) {
          long[] ids = recipients.getIds();
          Log.w("ConversationActivity", "Looking up new recipients...");
          recipients = RecipientFactory.getRecipientsForIds(context, ids, false);
          titleView.setTitle(recipients);
        }
      }
    };

    registerReceiver(securityUpdateReceiver,
                     new IntentFilter(SecurityEvent.SECURITY_UPDATE_EVENT),
                     KeyCachingService.KEY_PERMISSION, null);

    registerReceiver(groupUpdateReceiver,
                     new IntentFilter(GroupDatabase.DATABASE_UPDATE_ACTION));
  }

  //////// Helper Methods

  private void addAttachment(int type) {
    Log.w("ComposeMessageActivity", "Selected: " + type);
    switch (type) {
    case AttachmentTypeSelectorAdapter.TAKE_PHOTO:
      attachmentManager.capturePhoto(this, CAPTURE_PHOTO); break;
    case AttachmentTypeSelectorAdapter.ADD_IMAGE:
      AttachmentManager.selectImage(this, PICK_IMAGE); break;
    case AttachmentTypeSelectorAdapter.ADD_VIDEO:
      AttachmentManager.selectVideo(this, PICK_VIDEO); break;
    case AttachmentTypeSelectorAdapter.ADD_SOUND:
      AttachmentManager.selectAudio(this, PICK_AUDIO); break;
    case AttachmentTypeSelectorAdapter.ADD_CONTACT_INFO:
      AttachmentManager.selectContactInfo(this, PICK_CONTACT_INFO); break;
    }
  }

  private void addAttachmentImage(Uri imageUri) {
    try {
      attachmentManager.setImage(imageUri);
    } catch (IOException | BitmapDecodingException e) {
      Log.w(TAG, e);
      attachmentManager.clear();
      Toast.makeText(this, R.string.ConversationActivity_sorry_there_was_an_error_setting_your_attachment,
                     Toast.LENGTH_LONG).show();
    }
  }

  private void addAttachmentVideo(Uri videoUri) {
    try {
      attachmentManager.setVideo(videoUri);
    } catch (IOException e) {
      attachmentManager.clear();
      Toast.makeText(this, R.string.ConversationActivity_sorry_there_was_an_error_setting_your_attachment,
                     Toast.LENGTH_LONG).show();
      Log.w("ComposeMessageActivity", e);
    } catch (MediaTooLargeException e) {
      attachmentManager.clear();

      Toast.makeText(this, getString(R.string.ConversationActivity_sorry_the_selected_video_exceeds_message_size_restrictions,
                                     (MmsMediaConstraints.MAX_MESSAGE_SIZE/1024)),
                     Toast.LENGTH_LONG).show();
      Log.w("ComposeMessageActivity", e);
    }
  }

  private void addAttachmentAudio(Uri audioUri) {
    try {
      attachmentManager.setAudio(audioUri);
    } catch (IOException e) {
      attachmentManager.clear();
      Toast.makeText(this, R.string.ConversationActivity_sorry_there_was_an_error_setting_your_attachment,
                     Toast.LENGTH_LONG).show();
      Log.w("ComposeMessageActivity", e);
    } catch (MediaTooLargeException e) {
      attachmentManager.clear();
      Toast.makeText(this, getString(R.string.ConversationActivity_sorry_the_selected_audio_exceeds_message_size_restrictions,
                                     (MmsMediaConstraints.MAX_MESSAGE_SIZE/1024)),
                     Toast.LENGTH_LONG).show();
      Log.w("ComposeMessageActivity", e);
    }
  }

  private void addAttachmentContactInfo(Uri contactUri) {
    ContactAccessor contactDataList = ContactAccessor.getInstance();
    ContactData contactData = contactDataList.getContactData(this, contactUri);

    if      (contactData.numbers.size() == 1) composeText.append(contactData.numbers.get(0).number);
    else if (contactData.numbers.size() > 1)  selectContactInfo(contactData);
  }

  private void selectContactInfo(ContactData contactData) {
    final CharSequence[] numbers     = new CharSequence[contactData.numbers.size()];
    final CharSequence[] numberItems = new CharSequence[contactData.numbers.size()];

    for (int i = 0; i < contactData.numbers.size(); i++) {
      numbers[i]     = contactData.numbers.get(i).number;
      numberItems[i] = contactData.numbers.get(i).type + ": " + contactData.numbers.get(i).number;
    }

    AlertDialogWrapper.Builder builder = new AlertDialogWrapper.Builder(this);
    builder.setIconAttribute(R.attr.conversation_attach_contact_info);
    builder.setTitle(R.string.ConversationActivity_select_contact_info);

    builder.setItems(numberItems, new DialogInterface.OnClickListener() {
      @Override
      public void onClick(DialogInterface dialog, int which) {
        composeText.append(numbers[which]);
      }
    });
    builder.show();
  }

  private Drafts getDraftsForCurrentState() {
    Drafts drafts = new Drafts();

    if (!Util.isEmpty(composeText)) {
      drafts.add(new Draft(Draft.TEXT, composeText.getText().toString()));
    }

    for (Slide slide : attachmentManager.getSlideDeck().getSlides()) {
      if      (slide.hasAudio()) drafts.add(new Draft(Draft.AUDIO, slide.getUri().toString()));
      else if (slide.hasVideo()) drafts.add(new Draft(Draft.VIDEO, slide.getUri().toString()));
      else if (slide.hasImage()) drafts.add(new Draft(Draft.IMAGE, slide.getUri().toString()));
    }

    return drafts;
  }

  protected ListenableFuture<Long> saveDraft() {
    final SettableFuture<Long> future = new SettableFuture<>();

    if (this.recipients == null || this.recipients.isEmpty()) {
      future.set(threadId);
      return future;
    }

    final Drafts       drafts               = getDraftsForCurrentState();
    final long         thisThreadId         = this.threadId;
    final MasterSecret thisMasterSecret     = this.masterSecret.parcelClone();
    final int          thisDistributionType = this.distributionType;

    new AsyncTask<Long, Void, Long>() {
      @Override
      protected Long doInBackground(Long... params) {
        ThreadDatabase threadDatabase = DatabaseFactory.getThreadDatabase(ConversationActivity.this);
        DraftDatabase  draftDatabase  = DatabaseFactory.getDraftDatabase(ConversationActivity.this);
        long           threadId       = params[0];

        if (drafts.size() > 0) {
          if (threadId == -1) threadId = threadDatabase.getThreadIdFor(getRecipients(), thisDistributionType);

          draftDatabase.insertDrafts(new MasterCipher(thisMasterSecret), threadId, drafts);
          threadDatabase.updateSnippet(threadId, drafts.getSnippet(ConversationActivity.this), System.currentTimeMillis(), Types.BASE_DRAFT_TYPE);
        } else if (threadId > 0) {
          threadDatabase.update(threadId);
        }

        return threadId;
      }

      @Override
      protected void onPostExecute(Long result) {
        future.set(result);
      }

    }.execute(thisThreadId);

    return future;
  }

  private void setActionBarColor(MaterialColor color) {
    getSupportActionBar().setBackgroundDrawable(new ColorDrawable(color.toActionBarColor(this)));

    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
      getWindow().setStatusBarColor(color.toStatusBarColor(this));
    }
  }

  private void setBlockedUserState(Recipients recipients) {
    if (recipients.isBlocked()) {
      unblockButton.setVisibility(View.VISIBLE);
      composePanel.setVisibility(View.GONE);
    } else {
      composePanel.setVisibility(View.VISIBLE);
      unblockButton.setVisibility(View.GONE);
    }
  }

  private void calculateCharactersRemaining() {
    int             charactersSpent = composeText.getText().toString().length();
    TransportOption transportOption = sendButton.getSelectedTransport();
    CharacterState  characterState  = transportOption.calculateCharacters(charactersSpent);

    if (characterState.charactersRemaining <= 15 || characterState.messagesSpent > 1) {
      charactersLeft.setText(characterState.charactersRemaining + "/" + characterState.maxMessageSize
                                 + " (" + characterState.messagesSpent + ")");
      charactersLeft.setVisibility(View.VISIBLE);
    } else {
      charactersLeft.setVisibility(View.GONE);
    }
  }

  private boolean isSingleConversation() {
    return getRecipients() != null && getRecipients().isSingleRecipient() && !getRecipients().isGroupRecipient();
  }

  private boolean isActiveGroup() {
    if (!isGroupConversation()) return false;

    try {
      byte[]      groupId = GroupUtil.getDecodedId(getRecipients().getPrimaryRecipient().getNumber());
      GroupRecord record  = DatabaseFactory.getGroupDatabase(this).getGroup(groupId);

      return record != null && record.isActive();
    } catch (IOException e) {
      Log.w("ConversationActivity", e);
      return false;
    }
  }

  private boolean isGroupConversation() {
    return getRecipients() != null &&
        (!getRecipients().isSingleRecipient() || getRecipients().isGroupRecipient());
  }

  private boolean isPushGroupConversation() {
    return getRecipients() != null && getRecipients().isGroupRecipient();
  }

  protected Recipients getRecipients() {
    return this.recipients;
  }

  protected long getThreadId() {
    return this.threadId;
  }

  private String getMessage() throws InvalidMessageException {
    String rawText = composeText.getText().toString();

    if (rawText.length() < 1 && !attachmentManager.isAttachmentPresent())
      throw new InvalidMessageException(getString(R.string.ConversationActivity_message_is_empty_exclamation));

    return rawText;
  }

  private void markThreadAsRead() {
    new AsyncTask<Long, Void, Void>() {
      @Override
      protected Void doInBackground(Long... params) {
        DatabaseFactory.getThreadDatabase(ConversationActivity.this).setRead(params[0]);
        MessageNotifier.updateNotification(ConversationActivity.this, masterSecret);
        return null;
      }
    }.execute(threadId);
  }

  protected void sendComplete(long threadId) {
    boolean refreshFragment = (threadId != this.threadId);
    this.threadId = threadId;

    if (fragment == null || !fragment.isVisible() || isFinishing()) {
      return;
    }

    if (refreshFragment) {
      fragment.reload(recipients, threadId);

      initializeSecurity();
    }

    fragment.scrollToBottom();
    attachmentManager.cleanup();
  }

  private void sendMessage() {
    try {
      Recipients recipients = getRecipients();
      boolean    forceSms   = sendButton.isManualSelection() && sendButton.getSelectedTransport().isSms();

      Log.w(TAG, "isManual Selection: " + sendButton.isManualSelection());
      Log.w(TAG, "forceSms: " + forceSms);

      if (recipients == null) {
        throw new RecipientFormattingException("Badly formatted");
      }

      if ((!recipients.isSingleRecipient() || recipients.isEmailRecipient()) && !isMmsEnabled) {
        handleManualMmsRequired();
      } else if (attachmentManager.isAttachmentPresent() || !recipients.isSingleRecipient() || recipients.isGroupRecipient() || recipients.isEmailRecipient()) {
        sendMediaMessage(forceSms);
      } else {
        sendTextMessage(forceSms);
      }
    } catch (RecipientFormattingException ex) {
      Toast.makeText(ConversationActivity.this,
                     R.string.ConversationActivity_recipient_is_not_a_valid_sms_or_email_address_exclamation,
                     Toast.LENGTH_LONG).show();
      Log.w(TAG, ex);
    } catch (InvalidMessageException ex) {
      Toast.makeText(ConversationActivity.this, R.string.ConversationActivity_message_is_empty_exclamation,
                     Toast.LENGTH_SHORT).show();
      Log.w(TAG, ex);
    }
  }

  private void sendMediaMessage(final boolean forceSms)
      throws InvalidMessageException
  {
    final Context context = getApplicationContext();
    SlideDeck slideDeck;

    if (attachmentManager.isAttachmentPresent()) slideDeck = new SlideDeck(attachmentManager.getSlideDeck());
    else                                         slideDeck = new SlideDeck();

    OutgoingMediaMessage outgoingMessage = new OutgoingMediaMessage(this, recipients, slideDeck,
                                                                    getMessage(), distributionType);

    if (isEncryptedConversation && !forceSms) {
      outgoingMessage = new OutgoingSecureMediaMessage(outgoingMessage);
    }

    attachmentManager.clear();
    composeText.setText("");

    new AsyncTask<OutgoingMediaMessage, Void, Long>() {
      @Override
      protected Long doInBackground(OutgoingMediaMessage... messages) {
        return MessageSender.send(context, masterSecret, messages[0], threadId, forceSms);
      }

      @Override
      protected void onPostExecute(Long result) {
        sendComplete(result);
      }
    }.execute(outgoingMessage);
  }

  private void sendTextMessage(final boolean forceSms)
      throws InvalidMessageException
  {
    final Context context = getApplicationContext();
    OutgoingTextMessage message;

    if (isEncryptedConversation && !forceSms) {
      message = new OutgoingEncryptedMessage(recipients, getMessage());
    } else {
      message = new OutgoingTextMessage(recipients, getMessage());
    }

    this.composeText.setText("");

    new AsyncTask<OutgoingTextMessage, Void, Long>() {
      @Override
      protected Long doInBackground(OutgoingTextMessage... messages) {
        return MessageSender.send(context, masterSecret, messages[0], threadId, forceSms);
      }

      @Override
      protected void onPostExecute(Long result) {
        sendComplete(result);
      }
    }.execute(message);
  }

  private void updateToggleButtonState() {
    if (composeText.getText().length() == 0 && !attachmentManager.isAttachmentPresent()) {
      buttonToggle.display(attachButton);
    } else {
      buttonToggle.display(sendButton);
    }
  }

  // Listeners

  private class AttachmentTypeListener implements DialogInterface.OnClickListener {
    @Override
    public void onClick(DialogInterface dialog, int which) {
      addAttachment(attachmentAdapter.buttonToCommand(which));
      dialog.dismiss();
    }
  }

  private class EmojiToggleListener implements OnClickListener {
    @Override
    public void onClick(View v) {
      InputMethodManager input = (InputMethodManager)getSystemService(Context.INPUT_METHOD_SERVICE);

      if (isEmojiDrawerOpen()) {
        hideEmojiPopup(true);
        input.showSoftInput(composeText, 0);
      } else {
        container.postOnKeyboardClose(new Runnable() {
          @Override public void run() {
            showEmojiPopup();
          }
        });
        input.hideSoftInputFromWindow(composeText.getWindowToken(), 0);
      }
    }
  }

  private class SendButtonListener implements OnClickListener, TextView.OnEditorActionListener {
    @Override
    public void onClick(View v) {
      sendMessage();
    }

    @Override
    public boolean onEditorAction(TextView v, int actionId, KeyEvent event) {
      if (actionId == EditorInfo.IME_ACTION_SEND) {
        sendButton.performClick();
        return true;
      }
      return false;
    }
  }

  private class AttachButtonListener implements OnClickListener {
    @Override
    public void onClick(View v) {
      handleAddAttachment();
    }
  }

  private class ComposeKeyPressedListener implements OnKeyListener, OnClickListener, TextWatcher, OnFocusChangeListener {

    int beforeLength;

    @Override
    public boolean onKey(View v, int keyCode, KeyEvent event) {
      if (event.getAction() == KeyEvent.ACTION_DOWN) {
        if (keyCode == KeyEvent.KEYCODE_ENTER) {
          if (TextSecurePreferences.isEnterSendsEnabled(ConversationActivity.this)) {
            sendButton.dispatchKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_ENTER));
            sendButton.dispatchKeyEvent(new KeyEvent(KeyEvent.ACTION_UP, KeyEvent.KEYCODE_ENTER));
            return true;
          }
        }
      }
      return false;
    }

    @Override
    public void onClick(View v) {
      hideEmojiPopup(true);
    }

    @Override
    public void beforeTextChanged(CharSequence s, int start, int count,int after) {
      beforeLength = composeText.getText().length();
    }

    @Override
    public void afterTextChanged(Editable s) {
      calculateCharactersRemaining();

      if (composeText.getText().length() == 0 || beforeLength == 0) {
        composeText.postDelayed(new Runnable() {
          @Override
          public void run() {
            updateToggleButtonState();
          }
        }, 50);
      }
    }

    @Override
    public void onTextChanged(CharSequence s, int start, int before,int count) {}

    @Override
    public void onFocusChange(View v, boolean hasFocus) {
      if (hasFocus) {
        hideEmojiPopup(true);
      }
    }
  }

  @Override
  public void setComposeText(String text) {
    this.composeText.setText(text);
  }

  @Override
  public void setThreadId(long threadId) {
    this.threadId = threadId;
  }

  @Override
  public void onAttachmentChanged() {
    initializeSecurity();
    updateToggleButtonState();
  }
}


File: src/org/thoughtcrime/securesms/components/ThumbnailView.java
package org.thoughtcrime.securesms.components;

import android.annotation.TargetApi;
import android.app.Activity;
import android.content.Context;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Build.VERSION;
import android.os.Build.VERSION_CODES;
import android.support.annotation.NonNull;
import android.support.annotation.Nullable;
import android.util.AttributeSet;
import android.util.Log;
import android.view.View;
import android.view.animation.AlphaAnimation;
import android.view.animation.Animation;
import android.view.animation.Animation.AnimationListener;
import android.widget.FrameLayout;

import com.bumptech.glide.GenericRequestBuilder;
import com.bumptech.glide.Glide;
import com.bumptech.glide.request.RequestListener;
import com.bumptech.glide.request.target.Target;
import com.makeramen.roundedimageview.RoundedImageView;
import com.pnikosis.materialishprogress.ProgressWheel;

import org.thoughtcrime.securesms.R;
import org.thoughtcrime.securesms.crypto.MasterSecret;
import org.thoughtcrime.securesms.jobs.PartProgressEvent;
import org.thoughtcrime.securesms.mms.DecryptableStreamUriLoader.DecryptableUri;
import org.thoughtcrime.securesms.mms.Slide;
import org.thoughtcrime.securesms.mms.SlideDeck;
import org.thoughtcrime.securesms.util.FutureTaskListener;
import org.thoughtcrime.securesms.util.ListenableFutureTask;
import org.thoughtcrime.securesms.util.Util;

import de.greenrobot.event.EventBus;
import ws.com.google.android.mms.pdu.PduPart;

public class ThumbnailView extends FrameLayout {
  private static final String TAG = ThumbnailView.class.getSimpleName();

  private boolean          showProgress = true;
  private RoundedImageView image;
  private ProgressWheel    progress;

  private ListenableFutureTask<SlideDeck> slideDeckFuture        = null;
  private SlideDeckListener               slideDeckListener      = null;
  private ThumbnailClickListener          thumbnailClickListener = null;
  private String                          slideId                = null;
  private Slide                           slide                  = null;

  public ThumbnailView(Context context) {
    this(context, null);
  }

  public ThumbnailView(Context context, AttributeSet attrs) {
    this(context, attrs, 0);
  }

  public ThumbnailView(Context context, AttributeSet attrs, int defStyle) {
    super(context, attrs, defStyle);
    inflate(context, R.layout.thumbnail_view, this);
    image    = (RoundedImageView) findViewById(R.id.thumbnail_image);
    progress = (ProgressWheel)    findViewById(R.id.progress_wheel);
  }

  @Override protected void onAttachedToWindow() {
    super.onAttachedToWindow();
    EventBus.getDefault().registerSticky(this);
  }

  @Override protected void onDetachedFromWindow() {
    super.onDetachedFromWindow();
    EventBus.getDefault().unregister(this);
  }

  @SuppressWarnings("unused")
  public void onEventAsync(final PartProgressEvent event) {
    if (this.slide != null && event.partId.equals(this.slide.getPart().getPartId())) {
      Util.runOnMain(new Runnable() {
        @Override public void run() {
          progress.setInstantProgress(((float) event.progress) / event.total);
          if (event.progress >= event.total) animateOutProgress();
        }
      });
    }
  }

  public void setImageResource(@Nullable MasterSecret masterSecret,
                               long id, long timestamp,
                               @NonNull ListenableFutureTask<SlideDeck> slideDeckFuture)
  {
    if (this.slideDeckFuture != null && this.slideDeckListener != null) {
      this.slideDeckFuture.removeListener(this.slideDeckListener);
    }

    String slideId = id + "::" + timestamp;

    if (!slideId.equals(this.slideId)) {
      image.setImageDrawable(null);
      this.slide   = null;
      this.slideId = slideId;
    }

    this.slideDeckListener = new SlideDeckListener(masterSecret);
    this.slideDeckFuture   = slideDeckFuture;
    this.slideDeckFuture.addListener(this.slideDeckListener);
  }

  public void setImageResource(@NonNull Slide slide) {
    setImageResource(slide, null);
  }

  public void setImageResource(@NonNull Slide slide, @Nullable MasterSecret masterSecret) {
    if (Util.equals(slide, this.slide)) {
      Log.w(TAG, "Not loading resource, slide was identical");
      return;
    }
    if (!isContextValid()) {
      Log.w(TAG, "Not loading resource, context is invalid");
      return;
    }

    this.slide = slide;
    if (slide.isInProgress() && showProgress) {
      progress.spin();
      progress.setVisibility(VISIBLE);
    } else {
      progress.setVisibility(GONE);
    }
    buildGlideRequest(slide, masterSecret).into(image);
    setOnClickListener(new ThumbnailClickDispatcher(thumbnailClickListener, slide));
  }

  public void setThumbnailClickListener(ThumbnailClickListener listener) {
    this.thumbnailClickListener = listener;
  }

  public void clear() {
    if (isContextValid()) Glide.clear(this);
  }

  public void setShowProgress(boolean showProgress) {
    this.showProgress = showProgress;
    if (progress.getVisibility() == View.VISIBLE && !showProgress) {
      animateOutProgress();
    }
  }

  @TargetApi(VERSION_CODES.JELLY_BEAN_MR1)
  private boolean isContextValid() {
    return !(getContext() instanceof Activity)            ||
           VERSION.SDK_INT < VERSION_CODES.JELLY_BEAN_MR1 ||
           !((Activity)getContext()).isDestroyed();
  }

  private GenericRequestBuilder buildGlideRequest(@NonNull Slide slide,
                                                  @Nullable MasterSecret masterSecret)
  {
    final GenericRequestBuilder builder;
    if (slide.getThumbnailUri() != null) {
      builder = buildThumbnailGlideRequest(slide, masterSecret);
    } else {
      builder = buildPlaceholderGlideRequest(slide);
    }

    if (slide.isInProgress() && showProgress) {
      return builder;
    } else {
      return builder.error(R.drawable.ic_missing_thumbnail_picture);
    }
  }

  private GenericRequestBuilder buildThumbnailGlideRequest(Slide slide, MasterSecret masterSecret) {

    final GenericRequestBuilder builder;
    if (slide.isDraft()) builder = buildDraftGlideRequest(slide);
    else                 builder = buildEncryptedPartGlideRequest(slide, masterSecret);
    return builder;
  }

  private GenericRequestBuilder buildDraftGlideRequest(Slide slide) {
    return Glide.with(getContext()).load(slide.getThumbnailUri()).asBitmap()
                                   .fitCenter()
                                   .listener(new PduThumbnailSetListener(slide.getPart()));
  }

  private GenericRequestBuilder buildEncryptedPartGlideRequest(Slide slide, MasterSecret masterSecret) {
    if (masterSecret == null) {
      throw new IllegalStateException("null MasterSecret when loading non-draft thumbnail");
    }

    return  Glide.with(getContext()).load(new DecryptableUri(masterSecret, slide.getThumbnailUri()))
                                    .centerCrop();
  }

  private GenericRequestBuilder buildPlaceholderGlideRequest(Slide slide) {
    return Glide.with(getContext()).load(slide.getPlaceholderRes(getContext().getTheme()))
                                   .fitCenter()
                                   .crossFade();
  }

  private void animateOutProgress() {
    AlphaAnimation animation = new AlphaAnimation(1f, 0f);
    animation.setDuration(200);
    animation.setAnimationListener(new AnimationListener() {
      @Override public void onAnimationStart(Animation animation) { }
      @Override public void onAnimationRepeat(Animation animation) { }
      @Override public void onAnimationEnd(Animation animation) {
        progress.setVisibility(View.GONE);
      }
    });
    progress.startAnimation(animation);
  }

  private class SlideDeckListener implements FutureTaskListener<SlideDeck> {
    private final MasterSecret masterSecret;

    public SlideDeckListener(MasterSecret masterSecret) {
      this.masterSecret = masterSecret;
    }

    @Override
    public void onSuccess(final SlideDeck slideDeck) {
      if (slideDeck == null) return;

      final Slide slide = slideDeck.getThumbnailSlide(getContext());
      if (slide != null) {
        Util.runOnMain(new Runnable() {
          @Override
          public void run() {
            setImageResource(slide, masterSecret);
          }
        });
      } else {
        Util.runOnMain(new Runnable() {
          @Override
          public void run() {
            Log.w(TAG, "Resolved slide was null!");
            setVisibility(View.GONE);
          }
        });
      }
    }

    @Override
    public void onFailure(Throwable error) {
      Log.w(TAG, error);
      Util.runOnMain(new Runnable() {
        @Override
        public void run() {
          Log.w(TAG, "onFailure!");
          setVisibility(View.GONE);
        }
      });
    }
  }

  public interface ThumbnailClickListener {
    void onClick(View v, Slide slide);
  }

  private class ThumbnailClickDispatcher implements View.OnClickListener {
    private ThumbnailClickListener listener;
    private Slide                  slide;

    public ThumbnailClickDispatcher(ThumbnailClickListener listener, Slide slide) {
      this.listener = listener;
      this.slide    = slide;
    }

    @Override
    public void onClick(View view) {
      if (listener != null) {
        listener.onClick(view, slide);
      } else {
        Log.w(TAG, "onClick, but no thumbnail click listener attached.");
      }
    }
  }

  private static class PduThumbnailSetListener implements RequestListener<Uri, Bitmap> {
    private PduPart part;

    public PduThumbnailSetListener(@NonNull PduPart part) {
      this.part = part;
    }

    @Override
    public boolean onException(Exception e, Uri model, Target<Bitmap> target, boolean isFirstResource) {
      return false;
    }

    @Override
    public boolean onResourceReady(Bitmap resource, Uri model, Target<Bitmap> target, boolean isFromMemoryCache, boolean isFirstResource) {
      part.setThumbnail(resource);
      return false;
    }
  }

}


File: src/org/thoughtcrime/securesms/database/DraftDatabase.java
package org.thoughtcrime.securesms.database;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import android.util.Log;

import org.thoughtcrime.securesms.R;
import org.whispersystems.libaxolotl.InvalidMessageException;
import org.thoughtcrime.securesms.crypto.MasterCipher;

import java.util.LinkedList;
import java.util.List;
import java.util.Set;

public class DraftDatabase extends Database {

  private static final String TABLE_NAME  = "drafts";
  public  static final String ID          = "_id";
  public  static final String THREAD_ID   = "thread_id";
  public  static final String DRAFT_TYPE  = "type";
  public  static final String DRAFT_VALUE = "value";

  public static final String CREATE_TABLE = "CREATE TABLE " + TABLE_NAME + " (" + ID + " INTEGER PRIMARY KEY, " +
                                            THREAD_ID + " INTEGER, " + DRAFT_TYPE + " TEXT, " + DRAFT_VALUE + " TEXT);";

  public static final String[] CREATE_INDEXS = {
    "CREATE INDEX IF NOT EXISTS draft_thread_index ON " + TABLE_NAME + " (" + THREAD_ID + ");",
  };

  public DraftDatabase(Context context, SQLiteOpenHelper databaseHelper) {
    super(context, databaseHelper);
  }

  public void insertDrafts(MasterCipher masterCipher, long threadId, List<Draft> drafts) {
    SQLiteDatabase db    = databaseHelper.getWritableDatabase();

    for (Draft draft : drafts) {
      ContentValues values = new ContentValues(3);
      values.put(THREAD_ID, threadId);
      values.put(DRAFT_TYPE, masterCipher.encryptBody(draft.getType()));
      values.put(DRAFT_VALUE, masterCipher.encryptBody(draft.getValue()));

      db.insert(TABLE_NAME, null, values);
    }
  }

  public void clearDrafts(long threadId) {
    SQLiteDatabase db = databaseHelper.getWritableDatabase();
    db.delete(TABLE_NAME, THREAD_ID + " = ?", new String[] {threadId+""});
  }

  public void clearDrafts(Set<Long> threadIds) {
    SQLiteDatabase db        = databaseHelper.getWritableDatabase();
    StringBuilder  where     = new StringBuilder();
    List<String>   arguments = new LinkedList<>();

    for (long threadId : threadIds) {
      where.append(" OR ")
           .append(THREAD_ID)
           .append(" = ?");

      arguments.add(String.valueOf(threadId));
    }

    db.delete(TABLE_NAME, where.toString().substring(4), arguments.toArray(new String[0]));
  }

  public void clearAllDrafts() {
    SQLiteDatabase db = databaseHelper.getWritableDatabase();
    db.delete(TABLE_NAME, null, null);
  }

  public List<Draft> getDrafts(MasterCipher masterCipher, long threadId) {
    SQLiteDatabase db   = databaseHelper.getReadableDatabase();
    List<Draft> results = new LinkedList<Draft>();
    Cursor cursor       = null;

    try {
      cursor = db.query(TABLE_NAME, null, THREAD_ID + " = ?", new String[] {threadId+""}, null, null, null);

      while (cursor != null && cursor.moveToNext()) {
        try {
          String encryptedType  = cursor.getString(cursor.getColumnIndexOrThrow(DRAFT_TYPE));
          String encryptedValue = cursor.getString(cursor.getColumnIndexOrThrow(DRAFT_VALUE));

          results.add(new Draft(masterCipher.decryptBody(encryptedType),
                                masterCipher.decryptBody(encryptedValue)));
        } catch (InvalidMessageException ime) {
          Log.w("DraftDatabase", ime);
        }
      }

      return results;
    } finally {
      if (cursor != null)
        cursor.close();
    }
  }

  public static class Draft {
    public static final String TEXT  = "text";
    public static final String IMAGE = "image";
    public static final String VIDEO = "video";
    public static final String AUDIO = "audio";

    private final String type;
    private final String value;

    public Draft(String type, String value) {
      this.type  = type;
      this.value = value;
    }

    public String getType() {
      return type;
    }

    public String getValue() {
      return value;
    }

    public String getSnippet(Context context) {
      switch (type) {
      case TEXT:  return value;
      case IMAGE: return context.getString(R.string.DraftDatabase_Draft_image_snippet);
      case VIDEO: return context.getString(R.string.DraftDatabase_Draft_video_snippet);
      case AUDIO: return context.getString(R.string.DraftDatabase_Draft_audio_snippet);
      default:    return null;
      }
    }
  }

  public static class Drafts extends LinkedList<Draft> {
    private Draft getDraftOfType(String type) {
      for (Draft draft : this) {
        if (Draft.TEXT.equals(draft.getType())) {
          return draft;
        }
      }
      return null;
    }

    public String getSnippet(Context context) {
      Draft textDraft = getDraftOfType(Draft.TEXT);
      if (textDraft != null) {
        return textDraft.getSnippet(context);
      } else if (size() > 0) {
        return get(0).getSnippet(context);
      } else {
        return "";
      }
    }
  }
}


File: src/org/thoughtcrime/securesms/mms/AttachmentManager.java
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
package org.thoughtcrime.securesms.mms;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.provider.ContactsContract;
import android.provider.MediaStore;
import android.util.Log;
import android.view.View;
import android.view.animation.AlphaAnimation;
import android.view.animation.Animation;
import android.view.animation.ScaleAnimation;
import android.widget.Button;
import android.widget.ImageButton;
import android.widget.ImageView;
import android.widget.Toast;

import org.thoughtcrime.securesms.R;
import org.thoughtcrime.securesms.components.ThumbnailView;
import org.thoughtcrime.securesms.util.BitmapDecodingException;

import java.io.File;
import java.io.IOException;

public class AttachmentManager {
  private final static String TAG = AttachmentManager.class.getSimpleName();

  private final Context            context;
  private final View               attachmentView;
  private final ThumbnailView      thumbnail;
  private final ImageView          removeButton;
  private final SlideDeck          slideDeck;
  private final AttachmentListener attachmentListener;

  private File captureFile;

  public AttachmentManager(Activity view, AttachmentListener listener) {
    this.attachmentView     = view.findViewById(R.id.attachment_editor);
    this.thumbnail          = (ThumbnailView)view.findViewById(R.id.attachment_thumbnail);
    this.removeButton       = (ImageView)view.findViewById(R.id.remove_image_button);
    this.slideDeck          = new SlideDeck();
    this.context            = view;
    this.attachmentListener = listener;

    this.removeButton.setOnClickListener(new RemoveButtonListener());
  }

  public void clear() {
    AlphaAnimation animation = new AlphaAnimation(1.0f, 0.0f);
    animation.setDuration(200);
    animation.setAnimationListener(new Animation.AnimationListener() {
      @Override
      public void onAnimationStart(Animation animation) {

      }

      @Override
      public void onAnimationEnd(Animation animation) {
        slideDeck.clear();
        attachmentView.setVisibility(View.GONE);
        attachmentListener.onAttachmentChanged();
      }

      @Override
      public void onAnimationRepeat(Animation animation) {

      }
    });

    attachmentView.startAnimation(animation);
  }

  public void cleanup() {
    if (captureFile != null) captureFile.delete();
    captureFile = null;
  }

  public void setImage(Uri image) throws IOException, BitmapDecodingException {
    setMedia(new ImageSlide(context, image));
  }

  public void setVideo(Uri video) throws IOException, MediaTooLargeException {
    setMedia(new VideoSlide(context, video));
  }

  public void setAudio(Uri audio) throws IOException, MediaTooLargeException {
    setMedia(new AudioSlide(context, audio));
  }

  public void setMedia(final Slide slide) {
    slideDeck.clear();
    slideDeck.addSlide(slide);
    attachmentView.setVisibility(View.VISIBLE);
    thumbnail.setImageResource(slide);
    attachmentListener.onAttachmentChanged();
  }

  public boolean isAttachmentPresent() {
    return attachmentView.getVisibility() == View.VISIBLE;
  }

  public SlideDeck getSlideDeck() {
    return slideDeck;
  }

  public File getCaptureFile() {
    return captureFile;
  }

  public void capturePhoto(Activity activity, int requestCode) {
    try {
      Intent captureIntent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);

      if (captureIntent.resolveActivity(activity.getPackageManager()) != null) {
        captureFile = File.createTempFile(String.valueOf(System.currentTimeMillis()), ".jpg", activity.getExternalFilesDir(null));
        captureIntent.putExtra(MediaStore.EXTRA_OUTPUT, Uri.fromFile(captureFile));
        activity.startActivityForResult(captureIntent, requestCode);
      }
    } catch (IOException e) {
      Log.w(TAG, e);
    }
  }

  public static void selectVideo(Activity activity, int requestCode) {
    selectMediaType(activity, "video/*", requestCode);
  }

  public static void selectImage(Activity activity, int requestCode) {
    selectMediaType(activity, "image/*", requestCode);
  }

  public static void selectAudio(Activity activity, int requestCode) {
    selectMediaType(activity, "audio/*", requestCode);
  }

  public static void selectContactInfo(Activity activity, int requestCode) {
    Intent intent = new Intent(Intent.ACTION_PICK, ContactsContract.Contacts.CONTENT_URI);
    activity.startActivityForResult(intent, requestCode);
  }

  private static void selectMediaType(Activity activity, String type, int requestCode) {
    final Intent intent = new Intent();
    intent.setType(type);

    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
      intent.setAction(Intent.ACTION_OPEN_DOCUMENT);
      try {
        activity.startActivityForResult(intent, requestCode);
        return;
      } catch (ActivityNotFoundException anfe) {
        Log.w(TAG, "couldn't complete ACTION_OPEN_DOCUMENT, no activity found. falling back.");
      }
    }

    intent.setAction(Intent.ACTION_GET_CONTENT);
    try {
      activity.startActivityForResult(intent, requestCode);
    } catch (ActivityNotFoundException anfe) {
      Log.w(TAG, "couldn't complete ACTION_GET_CONTENT intent, no activity found. falling back.");
      Toast.makeText(activity, R.string.AttachmentManager_cant_open_media_selection, Toast.LENGTH_LONG).show();
    }
  }

  private class RemoveButtonListener implements View.OnClickListener {
    @Override
    public void onClick(View v) {
      clear();
      cleanup();
    }
  }

  public interface AttachmentListener {
    public void onAttachmentChanged();
  }
}


File: src/org/thoughtcrime/securesms/mms/ImageSlide.java
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
package org.thoughtcrime.securesms.mms;

import android.content.Context;
import android.content.res.Resources.Theme;
import android.net.Uri;
import android.support.annotation.DrawableRes;

import org.thoughtcrime.securesms.R;
import org.thoughtcrime.securesms.crypto.MasterSecret;
import org.thoughtcrime.securesms.util.BitmapDecodingException;

import java.io.IOException;

import ws.com.google.android.mms.ContentType;
import ws.com.google.android.mms.pdu.PduPart;

public class ImageSlide extends Slide {
  private static final String TAG = ImageSlide.class.getSimpleName();

  public ImageSlide(Context context, MasterSecret masterSecret, PduPart part) {
    super(context, masterSecret, part);
  }

  public ImageSlide(Context context, Uri uri) throws IOException, BitmapDecodingException {
    super(context, constructPartFromUri(uri));
  }

  @Override
  public Uri getThumbnailUri() {
    if (getPart().getDataUri() != null) {
      return isDraft()
             ? getPart().getDataUri()
             : PartAuthority.getThumbnailUri(getPart().getPartId());
    }

    return null;
  }

  @Override
  public @DrawableRes int getPlaceholderRes(Theme theme) {
    return R.drawable.ic_missing_thumbnail_picture;
  }

  @Override
  public boolean hasImage() {
    return true;
  }

  private static PduPart constructPartFromUri(Uri uri)
      throws IOException, BitmapDecodingException
  {
    PduPart part = new PduPart();

    part.setDataUri(uri);
    part.setContentType(ContentType.IMAGE_JPEG.getBytes());
    part.setContentId((System.currentTimeMillis()+"").getBytes());
    part.setName(("Image" + System.currentTimeMillis()).getBytes());

    return part;
  }

}


File: src/org/thoughtcrime/securesms/mms/PartAuthority.java
package org.thoughtcrime.securesms.mms;

import android.content.ContentUris;
import android.content.Context;
import android.content.UriMatcher;
import android.net.Uri;

import org.thoughtcrime.securesms.crypto.MasterSecret;
import org.thoughtcrime.securesms.database.DatabaseFactory;
import org.thoughtcrime.securesms.database.PartDatabase;
import org.thoughtcrime.securesms.providers.PartProvider;

import java.io.IOException;
import java.io.InputStream;

public class PartAuthority {

  private static final String PART_URI_STRING   = "content://org.thoughtcrime.securesms/part";
  private static final String THUMB_URI_STRING  = "content://org.thoughtcrime.securesms/thumb";
  private static final Uri    PART_CONTENT_URI  = Uri.parse(PART_URI_STRING);
  private static final Uri    THUMB_CONTENT_URI = Uri.parse(THUMB_URI_STRING);

  private static final int PART_ROW  = 1;
  private static final int THUMB_ROW = 2;

  private static final UriMatcher uriMatcher;

  static {
    uriMatcher = new UriMatcher(UriMatcher.NO_MATCH);
    uriMatcher.addURI("org.thoughtcrime.securesms", "part/*/#", PART_ROW);
    uriMatcher.addURI("org.thoughtcrime.securesms", "thumb/*/#", THUMB_ROW);
  }

  public static InputStream getPartStream(Context context, MasterSecret masterSecret, Uri uri)
      throws IOException
  {
    PartDatabase partDatabase = DatabaseFactory.getPartDatabase(context);
    int          match        = uriMatcher.match(uri);

    try {
      switch (match) {
      case PART_ROW:
        PartUriParser partUri = new PartUriParser(uri);
        return partDatabase.getPartStream(masterSecret, partUri.getPartId());
      case THUMB_ROW:
        partUri = new PartUriParser(uri);
        return partDatabase.getThumbnailStream(masterSecret, partUri.getPartId());
      default:
        return context.getContentResolver().openInputStream(uri);
      }
    } catch (SecurityException se) {
      throw new IOException(se);
    }
  }

  public static Uri getPublicPartUri(Uri uri) {
    PartUriParser partUri = new PartUriParser(uri);
    return PartProvider.getContentUri(partUri.getPartId());
  }

  public static Uri getPartUri(PartDatabase.PartId partId) {
    Uri uri = Uri.withAppendedPath(PART_CONTENT_URI, String.valueOf(partId.getUniqueId()));
    return ContentUris.withAppendedId(uri, partId.getRowId());
  }

  public static Uri getThumbnailUri(PartDatabase.PartId partId) {
    Uri uri = Uri.withAppendedPath(THUMB_CONTENT_URI, String.valueOf(partId.getUniqueId()));
    return ContentUris.withAppendedId(uri, partId.getRowId());
  }
}


File: src/org/thoughtcrime/securesms/mms/Slide.java
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
package org.thoughtcrime.securesms.mms;

import android.content.Context;
import android.content.res.Resources.Theme;
import android.net.Uri;
import android.support.annotation.DrawableRes;
import android.support.annotation.NonNull;

import org.thoughtcrime.securesms.crypto.MasterSecret;
import org.thoughtcrime.securesms.util.Util;

import java.io.IOException;
import java.io.InputStream;

import ws.com.google.android.mms.pdu.PduPart;

public abstract class Slide {

  protected final PduPart      part;
  protected final Context      context;
  protected       MasterSecret masterSecret;

  public Slide(Context context, @NonNull PduPart part) {
    this.part    = part;
    this.context = context;
  }

  public Slide(Context context, @NonNull MasterSecret masterSecret, @NonNull PduPart part) {
    this(context, part);
    this.masterSecret = masterSecret;
  }

  public String getContentType() {
    return new String(part.getContentType());
  }

  public Uri getUri() {
    return part.getDataUri();
  }

  public boolean hasImage() {
    return false;
  }

  public boolean hasVideo() {
    return false;
  }

  public boolean hasAudio() {
    return false;
  }

  public PduPart getPart() {
    return part;
  }

  public Uri getThumbnailUri() {
    return null;
  }

  public boolean isInProgress() {
    return part.isInProgress();
  }

  public @DrawableRes int getPlaceholderRes(Theme theme) {
    throw new AssertionError("getPlaceholderRes() called for non-drawable slide");
  }

  public boolean isDraft() {
    return !getPart().getPartId().isValid();
  }

  protected static void assertMediaSize(Context context, Uri uri)
      throws MediaTooLargeException, IOException
  {
    InputStream in = context.getContentResolver().openInputStream(uri);
    long   size    = 0;
    byte[] buffer  = new byte[512];
    int read;

    while ((read = in.read(buffer)) != -1) {
      size += read;
      if (size > MmsMediaConstraints.MAX_MESSAGE_SIZE) throw new MediaTooLargeException("Media exceeds maximum message size.");
    }
  }

  @Override
  public boolean equals(Object other) {
    if (!(other instanceof Slide)) return false;

    Slide that = (Slide)other;

    return Util.equals(this.getContentType(), that.getContentType()) &&
           this.hasAudio() == that.hasAudio()                        &&
           this.hasImage() == that.hasImage()                        &&
           this.hasVideo() == that.hasVideo()                        &&
           this.isDraft() == that.isDraft()                          &&
           this.isInProgress() == that.isInProgress()                &&
           Util.equals(this.getUri(), that.getUri())                 &&
           Util.equals(this.getThumbnailUri(), that.getThumbnailUri());
  }

  @Override
  public int hashCode() {
    return Util.hashCode(getContentType(), hasAudio(), hasImage(),
                         hasVideo(), isDraft(), getUri(), getThumbnailUri());
  }



}


File: src/org/thoughtcrime/securesms/util/BitmapUtil.java
package org.thoughtcrime.securesms.util;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Bitmap.CompressFormat;
import android.graphics.Bitmap.Config;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.PorterDuff;
import android.graphics.PorterDuffXfermode;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.drawable.BitmapDrawable;
import android.graphics.drawable.Drawable;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.util.Pair;

import com.android.gallery3d.data.Exif;

import org.thoughtcrime.securesms.crypto.MasterSecret;
import org.thoughtcrime.securesms.mms.PartAuthority;

import java.io.BufferedInputStream;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.concurrent.atomic.AtomicBoolean;

public class BitmapUtil {
  private static final String TAG = BitmapUtil.class.getSimpleName();

  private static final int MAX_COMPRESSION_QUALITY  = 95;
  private static final int MIN_COMPRESSION_QUALITY  = 50;
  private static final int MAX_COMPRESSION_ATTEMPTS = 4;

  public static byte[] createScaledBytes(Context context, MasterSecret masterSecret, Uri uri, int maxWidth, int maxHeight, int maxSize)
      throws IOException, BitmapDecodingException
  {
    Bitmap bitmap;
    try {
      bitmap = createScaledBitmap(context, masterSecret, uri, maxWidth, maxHeight, false);
    } catch(OutOfMemoryError oome) {
      Log.w(TAG, "OutOfMemoryError when scaling precisely, doing rough scale to save memory instead");
      bitmap = createScaledBitmap(context, masterSecret, uri, maxWidth, maxHeight, true);
    }
    int quality         = MAX_COMPRESSION_QUALITY;
    int attempts        = 0;

    ByteArrayOutputStream baos;

    do {
      baos = new ByteArrayOutputStream();
      bitmap.compress(Bitmap.CompressFormat.JPEG, quality, baos);

      quality = Math.max((quality * maxSize) / baos.size(), MIN_COMPRESSION_QUALITY);
    } while (baos.size() > maxSize && attempts++ < MAX_COMPRESSION_ATTEMPTS);

    Log.w(TAG, "createScaledBytes(" + uri + ") -> quality " + Math.min(quality, MAX_COMPRESSION_QUALITY) + ", " + attempts + " attempt(s)");

    bitmap.recycle();

    if (baos.size() <= maxSize) return baos.toByteArray();
    else                        throw new IOException("Unable to scale image below: " + baos.size());
  }

  public static Bitmap createScaledBitmap(Context context, MasterSecret masterSecret, Uri uri, int maxWidth, int maxHeight)
      throws BitmapDecodingException, IOException
  {
    Bitmap bitmap;
    try {
      bitmap = createScaledBitmap(context, masterSecret, uri, maxWidth, maxHeight, false);
    } catch(OutOfMemoryError oome) {
      Log.w(TAG, "OutOfMemoryError when scaling precisely, doing rough scale to save memory instead");
      bitmap = createScaledBitmap(context, masterSecret, uri, maxWidth, maxHeight, true);
    }

    return bitmap;
  }

  private static Bitmap createScaledBitmap(Context context, MasterSecret masterSecret, Uri uri, int maxWidth, int maxHeight, boolean constrainedMemory)
      throws IOException, BitmapDecodingException
  {
    InputStream is = PartAuthority.getPartStream(context, masterSecret, uri);
    if (is == null) throw new IOException("Couldn't obtain InputStream");
    return createScaledBitmap(is,
                              PartAuthority.getPartStream(context, masterSecret, uri),
                              PartAuthority.getPartStream(context, masterSecret, uri),
                              maxWidth, maxHeight, constrainedMemory);
  }

  private static Bitmap createScaledBitmap(InputStream measure, InputStream orientationStream, InputStream data,
                                           int maxWidth, int maxHeight, boolean constrainedMemory)
      throws BitmapDecodingException
  {
    Bitmap bitmap = createScaledBitmap(measure, data, maxWidth, maxHeight, constrainedMemory);
    return fixOrientation(bitmap, orientationStream);
  }

  private static Bitmap createScaledBitmap(InputStream measure, InputStream data, int maxWidth, int maxHeight,
                                           boolean constrainedMemory)
      throws BitmapDecodingException
  {
    final BitmapFactory.Options options = getImageDimensions(measure);
    return createScaledBitmap(data, maxWidth, maxHeight, options, constrainedMemory);
  }

  public static Bitmap createScaledBitmap(InputStream measure, InputStream data, float scale)
      throws BitmapDecodingException
  {
    final BitmapFactory.Options options = getImageDimensions(measure);
    final int outWidth = (int)(options.outWidth * scale);
    final int outHeight = (int)(options.outHeight * scale);
    Log.w(TAG, "creating scaled bitmap with scale " + scale + " => " + outWidth + "x" + outHeight);
    return createScaledBitmap(data, outWidth, outHeight, options, false);
  }

  public static Bitmap createScaledBitmap(InputStream measure, InputStream data, int maxWidth, int maxHeight)
      throws BitmapDecodingException
  {
    return createScaledBitmap(measure, data, maxWidth, maxHeight, false);
  }

  private static Bitmap createScaledBitmap(InputStream data, int maxWidth, int maxHeight,
                                           BitmapFactory.Options options, boolean constrainedMemory)
      throws BitmapDecodingException
  {
    final int imageWidth  = options.outWidth;
    final int imageHeight = options.outHeight;

    options.inSampleSize       = getScaleFactor(imageWidth, imageHeight, maxWidth, maxHeight, constrainedMemory);
    options.inJustDecodeBounds = false;
    options.inPreferredConfig  = constrainedMemory ? Config.RGB_565 : Config.ARGB_8888;

    InputStream is             = new BufferedInputStream(data);
    Bitmap      roughThumbnail = BitmapFactory.decodeStream(is, null, options);
    try {
      is.close();
    } catch (IOException ioe) {
      Log.w(TAG, "IOException thrown when closing an images InputStream", ioe);
    }
    Log.w(TAG, "rough scale " + (imageWidth) + "x" + (imageHeight) +
               " => " + (options.outWidth) + "x" + (options.outHeight));
    if (roughThumbnail == null) {
      throw new BitmapDecodingException("Decoded stream was null.");
    }
    if (constrainedMemory) {
      return roughThumbnail;
    }

    if (options.outWidth > maxWidth || options.outHeight > maxHeight) {
      final float aspectWidth, aspectHeight;

      if (imageWidth == 0 || imageHeight == 0) {
        aspectWidth = maxWidth;
        aspectHeight = maxHeight;
      } else if (options.outWidth >= options.outHeight) {
        aspectWidth = maxWidth;
        aspectHeight = (aspectWidth / options.outWidth) * options.outHeight;
      } else {
        aspectHeight = maxHeight;
        aspectWidth = (aspectHeight / options.outHeight) * options.outWidth;
      }

      final int fineWidth  = Math.round(aspectWidth);
      final int fineHeight = Math.round(aspectHeight);

      Log.w(TAG, "fine scale " + options.outWidth + "x" + options.outHeight +
                 " => " + fineWidth + "x" + fineHeight);
      Bitmap scaledThumbnail = null;
      try {
        scaledThumbnail = Bitmap.createScaledBitmap(roughThumbnail, fineWidth, fineHeight, true);
      } finally {
        if (roughThumbnail != scaledThumbnail) roughThumbnail.recycle();
      }
      return scaledThumbnail;
    } else {
      return roughThumbnail;
    }
  }

  @VisibleForTesting static int getScaleFactor(int inWidth, int inHeight,
                                               int maxWidth, int maxHeight,
                                               boolean constrained)
  {
    int scaler = 1;
    while (!constrained && ((inWidth / scaler / 2 >= maxWidth) && (inHeight / scaler / 2 >= maxHeight))) {
      scaler *= 2;
    }
    while (constrained && ((inWidth / scaler > maxWidth) || (inHeight / scaler > maxHeight))) {
      scaler *= 2;
    }
    return scaler;
  }

  private static Bitmap fixOrientation(Bitmap bitmap, InputStream orientationStream) {
    final int orientation = Exif.getOrientation(orientationStream);

    if (orientation != 0) {
      return rotateBitmap(bitmap, orientation);
    } else {
      return bitmap;
    }
  }

  private static Bitmap rotateBitmap(Bitmap bitmap, int angle) {
    Matrix matrix = new Matrix();
    matrix.postRotate(angle);
    Bitmap rotated = Bitmap.createBitmap(bitmap, 0, 0, bitmap.getWidth(), bitmap.getHeight(), matrix, true);
    if (rotated != bitmap) bitmap.recycle();
    return rotated;
  }

  private static BitmapFactory.Options getImageDimensions(InputStream inputStream) {
    BitmapFactory.Options options = new BitmapFactory.Options();
    options.inJustDecodeBounds    = true;
    BufferedInputStream fis       = new BufferedInputStream(inputStream);
    BitmapFactory.decodeStream(fis, null, options);
    try {
      fis.close();
    } catch (IOException ioe) {
      Log.w(TAG, "failed to close the InputStream after reading image dimensions");
    }
    return options;
  }

  public static Pair<Integer, Integer> getDimensions(InputStream inputStream) {
    BitmapFactory.Options options = getImageDimensions(inputStream);
    return new Pair<>(options.outWidth, options.outHeight);
  }

  public static InputStream toCompressedJpeg(Bitmap bitmap) {
    ByteArrayOutputStream thumbnailBytes = new ByteArrayOutputStream();
    bitmap.compress(CompressFormat.JPEG, 85, thumbnailBytes);
    return new ByteArrayInputStream(thumbnailBytes.toByteArray());
  }

  public static byte[] toByteArray(Bitmap bitmap) {
    ByteArrayOutputStream stream = new ByteArrayOutputStream();
    bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream);
    return stream.toByteArray();
  }

  public static Bitmap getCircleBitmap(Bitmap bitmap) {
    final Bitmap output = Bitmap.createBitmap(bitmap.getWidth(),
                                              bitmap.getHeight(), Bitmap.Config.ARGB_8888);
    final Canvas canvas = new Canvas(output);

    final int   color = Color.RED;
    final Paint paint = new Paint();
    final Rect  rect  = new Rect(0, 0, bitmap.getWidth(), bitmap.getHeight());
    final RectF rectF = new RectF(rect);

    paint.setAntiAlias(true);
    canvas.drawARGB(0, 0, 0, 0);
    paint.setColor(color);
    canvas.drawOval(rectF, paint);

    paint.setXfermode(new PorterDuffXfermode(PorterDuff.Mode.SRC_IN));
    canvas.drawBitmap(bitmap, rect, rect, paint);

    return output;
  }

  public static Bitmap createFromDrawable(final Drawable drawable, final int width, final int height) {
    final AtomicBoolean created = new AtomicBoolean(false);
    final Bitmap[]      result  = new Bitmap[1];

    Runnable runnable = new Runnable() {
      @Override
      public void run() {
        if (drawable instanceof BitmapDrawable) {
          result[0] = ((BitmapDrawable) drawable).getBitmap();
        } else {
          int canvasWidth = drawable.getIntrinsicWidth();
          if (canvasWidth <= 0) canvasWidth = width;

          int canvasHeight = drawable.getIntrinsicHeight();
          if (canvasHeight <= 0) canvasHeight = height;

          Bitmap bitmap;

          try {
            bitmap = Bitmap.createBitmap(canvasWidth, canvasHeight, Bitmap.Config.ARGB_8888);
            Canvas canvas = new Canvas(bitmap);
            drawable.setBounds(0, 0, canvas.getWidth(), canvas.getHeight());
            drawable.draw(canvas);
          } catch (Exception e) {
            Log.w(TAG, e);
            bitmap = null;
          }

          result[0] = bitmap;
        }

        synchronized (result) {
          created.set(true);
          result.notifyAll();
        }
      }
    };

    Util.runOnMain(runnable);

    synchronized (result) {
      while (!created.get()) Util.wait(result, 0);
      return result[0];
    }
  }
}
