Refactoring Types: ['Pull Up Method']
nucash/android/test/ui/ExportTransactionsTest.java
/*
 * Copyright (c) 2012 - 2015 Ngewi Fet <ngewif@gmail.com>
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

package org.gnucash.android.test.ui;

import android.database.SQLException;
import android.database.sqlite.SQLiteDatabase;
import android.preference.PreferenceManager;
import android.support.test.InstrumentationRegistry;
import android.support.test.runner.AndroidJUnit4;
import android.test.ActivityInstrumentationTestCase2;
import android.util.Log;
import android.widget.CompoundButton;

import org.gnucash.android.R;
import org.gnucash.android.db.AccountsDbAdapter;
import org.gnucash.android.db.DatabaseHelper;
import org.gnucash.android.db.ScheduledActionDbAdapter;
import org.gnucash.android.db.SplitsDbAdapter;
import org.gnucash.android.db.TransactionsDbAdapter;
import org.gnucash.android.export.ExportFormat;
import org.gnucash.android.export.Exporter;
import org.gnucash.android.model.Account;
import org.gnucash.android.model.Money;
import org.gnucash.android.model.PeriodType;
import org.gnucash.android.model.ScheduledAction;
import org.gnucash.android.model.Split;
import org.gnucash.android.model.Transaction;
import org.gnucash.android.ui.account.AccountsActivity;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;

import java.io.File;
import java.util.Currency;
import java.util.List;

import static android.support.test.espresso.Espresso.onView;
import static android.support.test.espresso.action.ViewActions.click;
import static android.support.test.espresso.matcher.ViewMatchers.isAssignableFrom;
import static android.support.test.espresso.matcher.ViewMatchers.isDisplayed;
import static android.support.test.espresso.matcher.ViewMatchers.isEnabled;
import static android.support.test.espresso.matcher.ViewMatchers.withId;
import static android.support.test.espresso.matcher.ViewMatchers.withText;
import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.allOf;

@RunWith(AndroidJUnit4.class)
public class ExportTransactionsTest extends
		ActivityInstrumentationTestCase2<AccountsActivity> {

    private DatabaseHelper mDbHelper;
    private SQLiteDatabase mDb;
    private AccountsDbAdapter mAccountsDbAdapter;
    private TransactionsDbAdapter mTransactionsDbAdapter;
    private SplitsDbAdapter mSplitsDbAdapter;

	private AccountsActivity mAcccountsActivity;

    public ExportTransactionsTest() {
		super(AccountsActivity.class);
	}
	
	@Override
	@Before
	public void setUp() throws Exception {
		super.setUp();
		injectInstrumentation(InstrumentationRegistry.getInstrumentation());
		AccountsActivityTest.preventFirstRunDialogs(getInstrumentation().getTargetContext());
		mAcccountsActivity = getActivity();

        mDbHelper = new DatabaseHelper(getActivity());
        try {
            mDb = mDbHelper.getWritableDatabase();
        } catch (SQLException e) {
            Log.e(getClass().getName(), "Error getting database: " + e.getMessage());
            mDb = mDbHelper.getReadableDatabase();
        }
        mSplitsDbAdapter = new SplitsDbAdapter(mDb);
        mTransactionsDbAdapter = new TransactionsDbAdapter(mDb, mSplitsDbAdapter);
        mAccountsDbAdapter = new AccountsDbAdapter(mDb, mTransactionsDbAdapter);
		mAccountsDbAdapter.deleteAllRecords();

		Account account = new Account("Exportable");		
		Transaction transaction = new Transaction("Pizza");
		transaction.setNote("What up?");
		transaction.setTime(System.currentTimeMillis());
        Split split = new Split(new Money("8.99", "USD"), account.getUID());
		split.setMemo("Hawaii is the best!");
		transaction.addSplit(split);
		transaction.addSplit(split.createPair(mAccountsDbAdapter.getOrCreateImbalanceAccountUID(Currency.getInstance("USD"))));
		account.addTransaction(transaction);

		mAccountsDbAdapter.addAccount(account);

	}
	
	/**
	 * Tests the export of an OFX file with the transactions from the application.
	 * The exported file name contains a timestamp with minute precision.
	 * If this test fails, it may be due to the file being created and tested in different minutes of the clock
	 * Just try rerunning it again.
	 */
	@Test
	public void testOfxExport(){
        testExport(ExportFormat.OFX);
	}

	/**
	 * Test the export of transactions in the QIF format
	 */
	@Test
	public void testQifExport(){
		testExport(ExportFormat.QIF);
	}

	@Test
	public void testXmlExport(){
		testExport(ExportFormat.XML);
	}

	/**
	 * Generates export for the specified format and tests that the file actually is created
	 * @param format Export format to use
	 */
    public void testExport(ExportFormat format){
		File folder = new File(Exporter.EXPORT_FOLDER_PATH);
		folder.mkdirs();
		assertThat(folder).exists();

		for (File file : folder.listFiles()) {
			file.delete();
		}
		//legacy menu will be removed in the future
		//onView(withId(R.id.menu_export)).perform(click());
		onView(withId(android.R.id.home)).perform(click());
		onView(withText(R.string.nav_menu_export)).perform(click());
		onView(withText(format.name())).perform(click());

		onView(withId(R.id.btn_save)).perform(click());

		assertThat(folder.listFiles().length).isEqualTo(1);
		File exportFile = folder.listFiles()[0];
		assertThat(exportFile.getName()).endsWith(format.getExtension());
    }

	@Test
	public void testDeleteTransactionsAfterExport(){
		assertThat(mTransactionsDbAdapter.getAllTransactionsCount()).isGreaterThan(0);

		PreferenceManager.getDefaultSharedPreferences(getActivity()).edit()
				.putBoolean(mAcccountsActivity.getString(R.string.key_delete_transactions_after_export), true).commit();

		testExport(ExportFormat.QIF);

		assertThat(mTransactionsDbAdapter.getAllTransactionsCount()).isEqualTo(0);
		PreferenceManager.getDefaultSharedPreferences(getActivity()).edit()
				.putBoolean(mAcccountsActivity.getString(R.string.key_delete_transactions_after_export), false).commit();
	}

	/**
	 * Test creating a scheduled export
	 * Does not work on Travis yet
	 */
	@Test
	public void shouldCreateExportSchedule(){
		onView(withId(android.R.id.home)).perform(click());
		onView(withText(R.string.nav_menu_export)).perform(click());

		onView(withText(ExportFormat.XML.name())).perform(click());
		onView(withId(R.id.input_recurrence)).perform(click());

		//switch on recurrence dialog
		onView(allOf(isAssignableFrom(CompoundButton.class), isDisplayed(), isEnabled())).perform(click());
		onView(withText("Done")).perform(click());

		onView(withId(R.id.btn_save)).perform(click());
		ScheduledActionDbAdapter scheduledactionDbAdapter = new ScheduledActionDbAdapter(mDb);
		List<ScheduledAction> scheduledActions = scheduledactionDbAdapter.getAllEnabledScheduledActions();
		assertThat(scheduledActions)
				.hasSize(1)
				.extracting("mActionType").contains(ScheduledAction.ActionType.BACKUP);

		ScheduledAction action = scheduledActions.get(0);
		assertThat(action.getPeriodType()).isEqualTo(PeriodType.WEEK);
		assertThat(action.getEndTime()).isEqualTo(0);
	}

	//todo: add testing of export flag to unit test
	//todo: add test of ignore exported transactions to unit tests
	@Override
	@After public void tearDown() throws Exception {
        mDbHelper.close();
        mDb.close();
		super.tearDown();
	}
}


File: app/src/main/java/org/gnucash/android/db/AccountsDbAdapter.java
/*
 * Copyright (c) 2012 - 2015 Ngewi Fet <ngewif@gmail.com>
 * Copyright (c) 2014 Yongxin Wang <fefe.wyx@gmail.com>
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

package org.gnucash.android.db;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteStatement;
import android.support.annotation.NonNull;
import android.support.annotation.Nullable;
import android.text.TextUtils;
import android.util.Log;
import org.gnucash.android.R;
import org.gnucash.android.app.GnuCashApplication;
import org.gnucash.android.model.Account;
import org.gnucash.android.model.AccountType;
import org.gnucash.android.model.Money;
import org.gnucash.android.model.Split;
import org.gnucash.android.model.Transaction;
import org.gnucash.android.model.TransactionType;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Currency;
import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;

import static org.gnucash.android.db.DatabaseSchema.AccountEntry;
import static org.gnucash.android.db.DatabaseSchema.SplitEntry;
import static org.gnucash.android.db.DatabaseSchema.TransactionEntry;

/**
 * Manages persistence of {@link Account}s in the database
 * Handles adding, modifying and deleting of account records.
 * @author Ngewi Fet <ngewif@gmail.com>
 * @author Yongxin Wang <fefe.wyx@gmail.com>
 * @author Oleksandr Tyshkovets <olexandr.tyshkovets@gmail.com>
 */
public class AccountsDbAdapter extends DatabaseAdapter {
    /**
     * Separator used for account name hierarchies between parent and child accounts
     */
    public static final String ACCOUNT_NAME_SEPARATOR = ":";

    /**
     * ROOT account full name.
     * should ensure the ROOT account's full name will always sort before any other
     * account's full name.
     */
    public static final String ROOT_ACCOUNT_FULL_NAME = " ";

	/**
	 * Transactions database adapter for manipulating transactions associated with accounts
	 */
    private final TransactionsDbAdapter mTransactionsAdapter;

//    private static String mImbalanceAccountPrefix = GnuCashApplication.getAppContext().getString(R.string.imbalance_account_name) + "-";

    /**
     * Overloaded constructor. Creates an adapter for an already open database
     * @param db SQliteDatabase instance
     */
    public AccountsDbAdapter(SQLiteDatabase db, TransactionsDbAdapter transactionsDbAdapter) {
        super(db, AccountEntry.TABLE_NAME);
        mTransactionsAdapter = transactionsDbAdapter;
        LOG_TAG = "AccountsDbAdapter";
    }

    /**
     * Returns an application-wide instance of this database adapter
     * @return Instance of Accounts db adapter
     */
    public static AccountsDbAdapter getInstance(){
        return GnuCashApplication.getAccountsDbAdapter();
    }

    /**
	 * Adds an account to the database. 
	 * If an account already exists in the database with the same unique ID, 
	 * then just update that account. 
	 * @param account {@link Account} to be inserted to database
	 * @return Database row ID of the inserted account
	 */
	public long addAccount(Account account){
		ContentValues contentValues = getContentValues(account);
		contentValues.put(AccountEntry.COLUMN_NAME,         account.getName());
		contentValues.put(AccountEntry.COLUMN_TYPE,         account.getAccountType().name());
		contentValues.put(AccountEntry.COLUMN_CURRENCY,     account.getCurrency().getCurrencyCode());
        contentValues.put(AccountEntry.COLUMN_PLACEHOLDER,  account.isPlaceholderAccount() ? 1 : 0);
        contentValues.put(AccountEntry.COLUMN_HIDDEN,       account.isHidden() ? 1 : 0);
        if (account.getColorHexCode() != null) {
            contentValues.put(AccountEntry.COLUMN_COLOR_CODE, account.getColorHexCode());
        } else {
            contentValues.putNull(AccountEntry.COLUMN_COLOR_CODE);
        }
        contentValues.put(AccountEntry.COLUMN_FAVORITE,     account.isFavorite() ? 1 : 0);
        contentValues.put(AccountEntry.COLUMN_FULL_NAME,    account.getFullName());
        String parentAccountUID = account.getParentUID();
        if (parentAccountUID == null && account.getAccountType() != AccountType.ROOT) {
            parentAccountUID = getOrCreateGnuCashRootAccountUID();
        }
        contentValues.put(AccountEntry.COLUMN_PARENT_ACCOUNT_UID, parentAccountUID);

        if (account.getDefaultTransferAccountUID() != null) {
            contentValues.put(AccountEntry.COLUMN_DEFAULT_TRANSFER_ACCOUNT_UID, account.getDefaultTransferAccountUID());
        } else {
            contentValues.putNull(AccountEntry.COLUMN_DEFAULT_TRANSFER_ACCOUNT_UID);
        }

        Log.d(LOG_TAG, "Replace account to db");
        long rowId =  mDb.replace(AccountEntry.TABLE_NAME, null, contentValues);

		//now add transactions if there are any
		if (rowId > 0 && account.getAccountType() != AccountType.ROOT){
            //update the fully qualified account name
            updateAccount(rowId, AccountEntry.COLUMN_FULL_NAME, getFullyQualifiedAccountName(rowId));
			for (Transaction t : account.getTransactions()) {
		        mTransactionsAdapter.addTransaction(t);
			}
		}
		return rowId;
	}

    /**
     * Adds some accounts to the database.
     * If an account already exists in the database with the same unique ID,
     * then just update that account. This function will NOT try to determine the full name
     * of the accounts inserted, full names should be generated prior to the insert.
     * All or none of the accounts will be inserted;
     * @param accountList {@link Account} to be inserted to database
     * @return number of rows inserted
     */
    public long bulkAddAccounts(List<Account> accountList){
        long nRow = 0;
        try {
            mDb.beginTransaction();
            SQLiteStatement replaceStatement = mDb.compileStatement("REPLACE INTO " + AccountEntry.TABLE_NAME + " ( "
                    + AccountEntry.COLUMN_UID 	            + " , "
                    + AccountEntry.COLUMN_NAME 	            + " , "
                    + AccountEntry.COLUMN_TYPE              + " , "
                    + AccountEntry.COLUMN_CURRENCY          + " , "
                    + AccountEntry.COLUMN_COLOR_CODE        + " , "
                    + AccountEntry.COLUMN_FAVORITE 		    + " , "
                    + AccountEntry.COLUMN_FULL_NAME 	    + " , "
                    + AccountEntry.COLUMN_PLACEHOLDER       + " , "
                    + AccountEntry.COLUMN_CREATED_AT        + " , "
                    + AccountEntry.COLUMN_HIDDEN            + " , "
                    + AccountEntry.COLUMN_PARENT_ACCOUNT_UID    + " , "
                    + AccountEntry.COLUMN_DEFAULT_TRANSFER_ACCOUNT_UID   + " ) VALUES ( ? , ? , ? , ? , ? , ? , ? , ? , ? , ? , ? , ? )");
            for (Account account:accountList) {
                replaceStatement.clearBindings();
                replaceStatement.bindString(1, account.getUID());
                replaceStatement.bindString(2, account.getName());
                replaceStatement.bindString(3, account.getAccountType().name());
                replaceStatement.bindString(4, account.getCurrency().getCurrencyCode());
                if (account.getColorHexCode() != null) {
                    replaceStatement.bindString(5, account.getColorHexCode());
                }
                replaceStatement.bindLong(6,    account.isFavorite() ? 1 : 0);
                replaceStatement.bindString(7,  account.getFullName());
                replaceStatement.bindLong(8,    account.isPlaceholderAccount() ? 1 : 0);
                replaceStatement.bindString(9,  account.getCreatedTimestamp().toString());
                replaceStatement.bindLong(10, account.isHidden() ? 1 : 0);
                if (account.getParentUID() != null) {
                    replaceStatement.bindString(11, account.getParentUID());
                }
                if (account.getDefaultTransferAccountUID() != null) {
                    replaceStatement.bindString(12, account.getDefaultTransferAccountUID());
                }
                //Log.d(LOG_TAG, "Replacing account in db");
                replaceStatement.execute();
                nRow ++;
            }
            mDb.setTransactionSuccessful();
        }
        finally {
            mDb.endTransaction();
        }
        return nRow;
    }
    /**
     * Marks all transactions for a given account as exported
     * @param accountUID Unique ID of the record to be marked as exported
     * @return Number of records marked as exported
     */
    public int markAsExported(String accountUID){
        ContentValues contentValues = new ContentValues();
        contentValues.put(TransactionEntry.COLUMN_EXPORTED, 1);
        return mDb.update(
                TransactionEntry.TABLE_NAME,
                contentValues,
                TransactionEntry.COLUMN_UID + " IN ( " +
                        "SELECT DISTINCT " + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_UID +
                        " FROM " + TransactionEntry.TABLE_NAME + " , " + SplitEntry.TABLE_NAME + " ON " +
                        TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_UID + " = " +
                        SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_TRANSACTION_UID + " , " +
                        AccountEntry.TABLE_NAME + " ON " + SplitEntry.TABLE_NAME + "." +
                        SplitEntry.COLUMN_ACCOUNT_UID + " = " + AccountEntry.TABLE_NAME + "." +
                        AccountEntry.COLUMN_UID + " WHERE " + AccountEntry.TABLE_NAME + "." +
                        AccountEntry.COLUMN_UID + " = ? "
                        + " ) ",
                new String[] {accountUID}
        );
    }

    /**
     * This feature goes through all the rows in the accounts and changes value for <code>columnKey</code> to <code>newValue</code><br/>
     * The <code>newValue</code> parameter is taken as string since SQLite typically stores everything as text.
     * <p><b>This method affects all rows, exercise caution when using it</b></p>
     * @param columnKey Name of column to be updated
     * @param newValue New value to be assigned to the columnKey
     * @return Number of records affected
     */
    public int updateAllAccounts(String columnKey, String newValue){
        ContentValues contentValues = new ContentValues();
        if (newValue == null) {
            contentValues.putNull(columnKey);
        } else {
            contentValues.put(columnKey, newValue);
        }
        return mDb.update(AccountEntry.TABLE_NAME, contentValues, null, null);
    }

    /**
     * Updates a specific entry of an account
     * @param accountId Database record ID of the account to be updated
     * @param columnKey Name of column to be updated
     * @param newValue  New value to be assigned to the columnKey
     * @return Number of records affected
     */
    public int updateAccount(long accountId, String columnKey, String newValue){
        return updateRecord(AccountEntry.TABLE_NAME, accountId, columnKey, newValue);
    }

    /**
     * This method goes through all the children of {@code accountUID} and updates the parent account
     * to {@code newParentAccountUID}. The fully qualified account names for all descendant accounts will also be updated.
     * @param accountUID GUID of the account
     * @param newParentAccountUID GUID of the new parent account
     */
    public void reassignDescendantAccounts(@NonNull String accountUID, @NonNull String newParentAccountUID) {
        List<String> descendantAccountUIDs = getDescendantAccountUIDs(accountUID, null, null);
        if (descendantAccountUIDs.size() > 0) {
            List<Account> descendantAccounts = getSimpleAccountList(
                    AccountEntry.COLUMN_UID + " IN ('" + TextUtils.join("','", descendantAccountUIDs) + "')",
                    null,
                    null
            );
            HashMap<String, Account> mapAccounts = new HashMap<>();
            for (Account account : descendantAccounts)
                mapAccounts.put(account.getUID(), account);
            String parentAccountFullName;
            if (newParentAccountUID == null || getAccountType(newParentAccountUID) == AccountType.ROOT) {
                parentAccountFullName = "";
            } else {
                parentAccountFullName = getAccountFullName(newParentAccountUID);
            }
            ContentValues contentValues = new ContentValues();
            for (String acctUID : descendantAccountUIDs) {
                Account acct = mapAccounts.get(acctUID);
                if (accountUID.equals(acct.getParentUID())) {
                    // direct descendant
                    acct.setParentUID(newParentAccountUID);
                    if (parentAccountFullName == null || parentAccountFullName.isEmpty()) {
                        acct.setFullName(acct.getName());
                    } else {
                        acct.setFullName(parentAccountFullName + ACCOUNT_NAME_SEPARATOR + acct.getName());
                    }
                    // update DB
                    contentValues.clear();
                    contentValues.put(AccountEntry.COLUMN_PARENT_ACCOUNT_UID, newParentAccountUID);
                    contentValues.put(AccountEntry.COLUMN_FULL_NAME, acct.getFullName());
                    mDb.update(
                            AccountEntry.TABLE_NAME, contentValues,
                            AccountEntry.COLUMN_UID + " = ?",
                            new String[]{acct.getUID()}
                    );
                } else {
                    // indirect descendant
                    acct.setFullName(
                            mapAccounts.get(acct.getParentUID()).getFullName() +
                                    ACCOUNT_NAME_SEPARATOR + acct.getName()
                    );
                    // update DB
                    contentValues.clear();
                    contentValues.put(AccountEntry.COLUMN_FULL_NAME, acct.getFullName());
                    mDb.update(
                            AccountEntry.TABLE_NAME, contentValues,
                            AccountEntry.COLUMN_UID + " = ?",
                            new String[]{acct.getUID()}
                    );
                }
            }
        }
    }

    /**
     * Deletes an account and its transactions, and all its sub-accounts and their transactions.
     * <p>Not only the splits belonging to the account and its descendants will be deleted, rather,
     * the complete transactions associated with this account and its descendants
     * (i.e. as long as the transaction has at least one split belonging to one of the accounts).
     * This prevents an split imbalance from being caused.</p>
     * <p>If you want to preserve transactions, make sure to first reassign the children accounts (see {@link #reassignDescendantAccounts(String, String)}
     * before calling this method. This method will however not delete a root account. </p>
     * <p><b>This method does a thorough delete, use with caution!!!</b></p>
     * @param accountId Database record ID of account
     * @return <code>true</code> if the account and subaccounts were all successfully deleted, <code>false</code> if
     * even one was not deleted
     * @see #reassignDescendantAccounts(String, String)
     */
    public boolean recursiveDeleteAccount(long accountId){
        String accountUID = getUID(accountId);
        if (getAccountType(accountUID) == AccountType.ROOT) {
            // refuse to delete ROOT
            return false;
        }

        Log.d(LOG_TAG, "Delete account with rowId with its transactions and sub-accounts: " + accountId);

        List<String> descendantAccountUIDs = getDescendantAccountUIDs(accountUID, null, null);
        mDb.beginTransaction();
        try {
            descendantAccountUIDs.add(accountUID); //add account to descendants list just for convenience
            for (String descendantAccountUID : descendantAccountUIDs) {
                mTransactionsAdapter.deleteTransactionsForAccount(descendantAccountUID);
            }

            String accountUIDList = "'" + TextUtils.join("','", descendantAccountUIDs) + "'";

            // delete accounts
            mDb.delete(
                    AccountEntry.TABLE_NAME,
                    AccountEntry.COLUMN_UID + " IN (" + accountUIDList + ")",
                    null
            );
            mDb.setTransactionSuccessful();
            return true;
        }
        finally {
            mDb.endTransaction();
        }
    }

	/**
	 * Builds an account instance with the provided cursor and loads its corresponding transactions.
	 *
	 * @param c Cursor pointing to account record in database
	 * @return {@link Account} object constructed from database record
	 */
    public Account buildAccountInstance(Cursor c){
        Account account = buildSimpleAccountInstance(c);
        account.setTransactions(mTransactionsAdapter.getAllTransactionsForAccount(account.getUID()));

        return account;
	}

    /**
     * Builds an account instance with the provided cursor and loads its corresponding transactions.
     * <p>The method will not move the cursor position, so the cursor should already be pointing
     * to the account record in the database<br/>
     * <b>Note</b> Unlike {@link  #buildAccountInstance(android.database.Cursor)} this method will not load transactions</p>
     *
     * @param c Cursor pointing to account record in database
     * @return {@link Account} object constructed from database record
     */
    private Account buildSimpleAccountInstance(Cursor c) {
        Account account = new Account(c.getString(c.getColumnIndexOrThrow(AccountEntry.COLUMN_NAME)));
        populateModel(c, account);

        account.setParentUID(c.getString(c.getColumnIndexOrThrow(AccountEntry.COLUMN_PARENT_ACCOUNT_UID)));
        account.setAccountType(AccountType.valueOf(c.getString(c.getColumnIndexOrThrow(AccountEntry.COLUMN_TYPE))));
        Currency currency = Currency.getInstance(c.getString(c.getColumnIndexOrThrow(AccountEntry.COLUMN_CURRENCY)));
        account.setCurrency(currency);
        account.setPlaceHolderFlag(c.getInt(c.getColumnIndexOrThrow(AccountEntry.COLUMN_PLACEHOLDER)) == 1);
        account.setDefaultTransferAccountUID(c.getString(c.getColumnIndexOrThrow(AccountEntry.COLUMN_DEFAULT_TRANSFER_ACCOUNT_UID)));
        account.setColorCode(c.getString(c.getColumnIndexOrThrow(AccountEntry.COLUMN_COLOR_CODE)));
        account.setFavorite(c.getInt(c.getColumnIndexOrThrow(AccountEntry.COLUMN_FAVORITE)) == 1);
        account.setFullName(c.getString(c.getColumnIndexOrThrow(AccountEntry.COLUMN_FULL_NAME)));
        account.setHidden(c.getInt(c.getColumnIndexOrThrow(AccountEntry.COLUMN_HIDDEN)) == 1);
        return account;
    }

    /**
	 * Returns the  unique ID of the parent account of the account with unique ID <code>uid</code>
	 * If the account has no parent, null is returned
	 * @param uid Unique Identifier of account whose parent is to be returned. Should not be null
	 * @return DB record UID of the parent account, null if the account has no parent
	 */
    public String getParentAccountUID(String uid){
		Cursor cursor = mDb.query(AccountEntry.TABLE_NAME,
				new String[] {AccountEntry._ID, AccountEntry.COLUMN_PARENT_ACCOUNT_UID},
                AccountEntry.COLUMN_UID + " = ?",
                new String[]{uid},
                null, null, null, null);
        try {
            if (cursor.moveToFirst()) {
                Log.d(LOG_TAG, "Account already exists. Returning existing id");
                return cursor.getString(cursor.getColumnIndexOrThrow(AccountEntry.COLUMN_PARENT_ACCOUNT_UID));
            } else {
                return null;
            }
        } finally {
            cursor.close();
        }
	}

    /**
     * Returns the  unique ID of the parent account of the account with database ID <code>id</code>
     * If the account has no parent, null is returned.
     * @param id DB record ID of account . Should not be null
     * @return DB record UID of the parent account, null if the account has no parent
     * @see #getParentAccountUID(String)
     */
    public String getParentAccountUID(long id){
        return getParentAccountUID(getUID(id));
    }

	/**
	 * Retrieves an account object from a database with database ID <code>rowId</code>
	 * @param rowId Identifier of the account record to be retrieved
	 * @return {@link Account} object corresponding to database record
	 */
    public Account getAccount(long rowId){
		Log.v(LOG_TAG, "Fetching account with id " + rowId);
		Cursor c =	fetchRecord(rowId);
		try {
            if (c.moveToFirst()) {
                return buildAccountInstance(c);
            } else {
                throw new IllegalArgumentException(String.format("rowId %d does not exist", rowId));
            }
        } finally {
            c.close();
        }
	}
		
	/**
	 * Returns the {@link Account} object populated with data from the database
	 * for the record with UID <code>uid</code>
	 * @param uid Unique ID of the account to be retrieved
	 * @return {@link Account} object for unique ID <code>uid</code>
	 */
    public Account getAccount(String uid){
		return getAccount(getID(uid));
	}	
	
    /**
     * Returns the color code for the account in format #rrggbb
     * @param accountId Database row ID of the account
     * @return String color code of account or null if none
     */
    public String getAccountColorCode(long accountId){
        Cursor c = mDb.query(AccountEntry.TABLE_NAME,
                new String[]{AccountEntry._ID, AccountEntry.COLUMN_COLOR_CODE},
                AccountEntry._ID + "=" + accountId,
                null, null, null, null);
        try {
            if (c.moveToFirst()) {
                return c.getString(c.getColumnIndexOrThrow(AccountEntry.COLUMN_COLOR_CODE));
            }
            else {
                return null;
            }
        } finally {
            c.close();
        }
    }

    /**
     * Overloaded method. Resolves the account unique ID from the row ID and makes a call to {@link #getAccountType(String)}
     * @param accountId Database row ID of the account
     * @return {@link AccountType} of the account
     */
    public AccountType getAccountType(long accountId){
        return getAccountType(getUID(accountId));
    }

    /**
	 * Returns the name of the account with id <code>accountID</code>
	 * @param accountID Database ID of the account record
	 * @return Name of the account 
	 */
    public String getName(long accountID) {
		Cursor c = fetchRecord(accountID);
        try {
            if (c.moveToFirst()) {
                return c.getString(c.getColumnIndexOrThrow(AccountEntry.COLUMN_NAME));
            } else {
                throw new IllegalArgumentException("account " + accountID + " does not exist");
            }
        } finally {
            c.close();
        }
	}
	
	/**
	 * Returns a list of all account objects in the system
	 * @return List of {@link Account}s in the database
	 */
    public List<Account> getAllAccounts(){
		LinkedList<Account> accounts = new LinkedList<Account>();
		Cursor c = fetchAllRecords();
        try {
            while (c.moveToNext()) {
                accounts.add(buildAccountInstance(c));
            }
        } finally {
            c.close();
        }
		return accounts;
	}

    /**
     * Returns a list of all account entries in the system (includes root account)
     * No transactions are loaded, just the accounts
     * @return List of {@link Account}s in the database
     */
    public List<Account> getSimpleAccountList(){
        LinkedList<Account> accounts = new LinkedList<>();
        Cursor c = fetchAccounts(null, null, AccountEntry.COLUMN_FULL_NAME + " ASC");

        try {
            while (c.moveToNext()) {
                accounts.add(buildSimpleAccountInstance(c));
            }
        }
        finally {
            c.close();
        }
        return accounts;
    }

    /**
     * Returns a list of all account entries in the system (includes root account)
     * No transactions are loaded, just the accounts
     * @return List of {@link Account}s in the database
     */
    public List<Account> getSimpleAccountList(String where, String[] whereArgs, String orderBy){
        LinkedList<Account> accounts = new LinkedList<>();
        Cursor c = fetchAccounts(where, whereArgs, orderBy);
        try {
            while (c.moveToNext()) {
                accounts.add(buildSimpleAccountInstance(c));
            }
        }
        finally {
            c.close();
        }
        return accounts;
    }
	/**
	 * Returns a list of accounts which have transactions that have not been exported yet
	 * @return List of {@link Account}s with unexported transactions
	 */
    public List<Account> getExportableAccounts(){
        LinkedList<Account> accountsList = new LinkedList<Account>();
        Cursor cursor = mDb.query(
                TransactionEntry.TABLE_NAME + " , " + SplitEntry.TABLE_NAME +
                        " ON " + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_UID + " = " +
                        SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_TRANSACTION_UID + " , " +
                        AccountEntry.TABLE_NAME + " ON " + AccountEntry.TABLE_NAME + "." +
                        AccountEntry.COLUMN_UID + " = " + SplitEntry.TABLE_NAME + "." +
                        SplitEntry.COLUMN_ACCOUNT_UID,
                new String[]{AccountEntry.TABLE_NAME + ".*"},
                TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_EXPORTED + " == 0",
                null,
                AccountEntry.TABLE_NAME + "." + AccountEntry.COLUMN_UID,
                null,
                null
        );
        try {
            while (cursor.moveToNext()) {
                accountsList.add(buildAccountInstance(cursor));
            }
        }
        finally {
            cursor.close();
        }
        return accountsList;
	}

    /**
     * Retrieves the unique ID of the imbalance account for a particular currency (creates the imbalance account
     * on demand if necessary)
     * @param currency Currency for the imbalance account
     * @return String unique ID of the account
     */
    public String getOrCreateImbalanceAccountUID(Currency currency){
        String imbalanceAccountName = getImbalanceAccountName(currency);
        String uid = findAccountUidByFullName(imbalanceAccountName);
        if (uid == null){
            Account account = new Account(imbalanceAccountName, currency);
            account.setAccountType(AccountType.BANK);
            account.setParentUID(getOrCreateGnuCashRootAccountUID());
            account.setHidden(!GnuCashApplication.isDoubleEntryEnabled());
            addAccount(account);
            uid = account.getUID();
        }
        return uid;
    }

    /**
     * Returns the GUID of the imbalance account for the currency
     * @param currency Currency for the imbalance account
     * @return GUID of the account or null if the account doesn't exist yet
     * @see #getOrCreateImbalanceAccountUID(java.util.Currency)
     */
    public String getImbalanceAccountUID(Currency currency){
        String imbalanceAccountName = getImbalanceAccountName(currency);
        return findAccountUidByFullName(imbalanceAccountName);
    }

    /**
     * Creates the account with the specified name and returns its unique identifier.
     * <p>If a full hierarchical account name is provided, then the whole hierarchy is created and the
     * unique ID of the last account (at bottom) of the hierarchy is returned</p>
     * @param fullName Fully qualified name of the account
     * @param accountType Type to assign to all accounts created
     * @return String unique ID of the account at bottom of hierarchy
     */
    public String createAccountHierarchy(String fullName, AccountType accountType) {
        if ("".equals(fullName)) {
            throw new IllegalArgumentException("fullName cannot be empty");
        }
        String[] tokens = fullName.trim().split(ACCOUNT_NAME_SEPARATOR);
        String uid = getOrCreateGnuCashRootAccountUID();
        String parentName = "";
        ArrayList<Account> accountsList = new ArrayList<Account>();
        for (String token : tokens) {
            parentName += token;
            String parentUID = findAccountUidByFullName(parentName);
            if (parentUID != null) { //the parent account exists, don't recreate
                uid = parentUID;
            } else {
                Account account = new Account(token);
                account.setAccountType(accountType);
                account.setParentUID(uid); //set its parent
                account.setFullName(parentName);
                accountsList.add(account);
                uid = account.getUID();
            }
            parentName += ACCOUNT_NAME_SEPARATOR;
        }
        if (accountsList.size() > 0) {
            bulkAddAccounts(accountsList);
        }
        // if fullName is not empty, loop will be entered and then uid will never be null
        //noinspection ConstantConditions
        return uid;
    }

    /**
     * Returns the unique ID of the opening balance account or creates one if necessary
     * @return String unique ID of the opening balance account
     */
    public String getOrCreateOpeningBalanceAccountUID() {
        String openingBalanceAccountName = getOpeningBalanceAccountFullName();
        String uid = findAccountUidByFullName(openingBalanceAccountName);
        if (uid == null) {
            uid = createAccountHierarchy(openingBalanceAccountName, AccountType.EQUITY);
        }
        return uid;
    }

    /**
     * Finds an account unique ID by its full name
     * @param fullName Fully qualified name of the account
     * @return String unique ID of the account or null if no match is found
     */
    public String findAccountUidByFullName(String fullName){
        Cursor c = mDb.query(AccountEntry.TABLE_NAME, new String[]{AccountEntry.COLUMN_UID},
                AccountEntry.COLUMN_FULL_NAME + "= ?", new String[]{fullName},
                null, null, null, "1");
        try {
            if (c.moveToNext()) {
                return c.getString(c.getColumnIndexOrThrow(AccountEntry.COLUMN_UID));
            } else {
                return null;
            }
        } finally {
            c.close();
        }
    }

	/**
	 * Returns a cursor to all account records in the database.
     * GnuCash ROOT accounts and hidden accounts will <b>not</b> be included in the result set
	 * @return {@link Cursor} to all account records
	 */
    @Override
	public Cursor fetchAllRecords(){
		Log.v(LOG_TAG, "Fetching all accounts from db");
        String selection =  AccountEntry.COLUMN_HIDDEN + " = 0 AND " + AccountEntry.COLUMN_TYPE + " != ?" ;
        return mDb.query(AccountEntry.TABLE_NAME,
                null,
                selection,
                new String[]{AccountType.ROOT.name()},
                null, null,
                AccountEntry.COLUMN_NAME + " ASC");
	}

    /**
     * Returns a cursor to all account records in the database ordered by full name.
     * GnuCash ROOT accounts and hidden accounts will not be included in the result set.
     * @return {@link Cursor} to all account records
     */
    public Cursor fetchAllRecordsOrderedByFullName(){
        Log.v(LOG_TAG, "Fetching all accounts from db");
        String selection =  AccountEntry.COLUMN_HIDDEN + " = 0 AND " + AccountEntry.COLUMN_TYPE + " != ?" ;
        return mDb.query(AccountEntry.TABLE_NAME,
                null,
                selection,
                new String[]{AccountType.ROOT.name()},
                null, null,
                AccountEntry.COLUMN_FULL_NAME + " ASC");
    }

    /**
     * Returns a Cursor set of accounts which fulfill <code>where</code>
     * and ordered by <code>orderBy</code>
     * @param where SQL WHERE statement without the 'WHERE' itself
     * @param whereArgs args to where clause
     * @param orderBy orderBy clause
     * @return Cursor set of accounts which fulfill <code>where</code>
     */
    public Cursor fetchAccounts(@Nullable String where, @Nullable String[] whereArgs, @Nullable String orderBy){
        if (orderBy == null){
            orderBy = AccountEntry.COLUMN_NAME + " ASC";
        }
        Log.v(LOG_TAG, "Fetching all accounts from db where " + where + " order by " + orderBy);

        return mDb.query(AccountEntry.TABLE_NAME,
                null, where, whereArgs, null, null,
                orderBy);
    }
    /**
     * Returns a Cursor set of accounts which fulfill <code>where</code>
     * <p>This method returns the accounts list sorted by the full account name</p>
     * @param where SQL WHERE statement without the 'WHERE' itself
     * @param whereArgs where args
     * @return Cursor set of accounts which fulfill <code>where</code>
     */
    public Cursor fetchAccountsOrderedByFullName(String where, String[] whereArgs) {
        Log.v(LOG_TAG, "Fetching all accounts from db where " + where);
        return mDb.query(AccountEntry.TABLE_NAME,
                null, where, whereArgs, null, null,
                AccountEntry.COLUMN_FULL_NAME + " ASC");
    }

    /**
     * Returns the balance of an account while taking sub-accounts into consideration
     * @return Account Balance of an account including sub-accounts
     */
    public Money getAccountBalance(String accountUID){
        return computeBalance(accountUID, -1, -1);
    }

    /**
     * Returns the balance of an account within the specified time range while taking sub-accounts into consideration
     * @param accountUID the account's UUID
     * @param startTimestamp the start timestamp of the time range
     * @param endTimestamp the end timestamp of the time range
     * @return the balance of an account within the specified range including sub-accounts
     */
    public Money getAccountBalance(String accountUID, long startTimestamp, long endTimestamp) {
        return computeBalance(accountUID, startTimestamp, endTimestamp);
    }

    private Money computeBalance(String accountUID, long startTimestamp, long endTimestamp) {
        Log.d(LOG_TAG, "Computing account balance for account ID " + accountUID);
        String currencyCode = mTransactionsAdapter.getAccountCurrencyCode(accountUID);
        boolean hasDebitNormalBalance = getAccountType(accountUID).hasDebitNormalBalance();
        Money balance = Money.createZeroInstance(currencyCode);

        List<String> accountsList = getDescendantAccountUIDs(accountUID,
                AccountEntry.COLUMN_CURRENCY + " = ? ",
                new String[]{currencyCode});

        accountsList.add(0, accountUID);

        Log.d(LOG_TAG, "all account list : " + accountsList.size());
		SplitsDbAdapter splitsDbAdapter = SplitsDbAdapter.getInstance();
        Money splitSum = (startTimestamp == -1 && endTimestamp == -1)
                ? splitsDbAdapter.computeSplitBalance(accountsList, currencyCode, hasDebitNormalBalance)
                : splitsDbAdapter.computeSplitBalance(accountsList, currencyCode, hasDebitNormalBalance, startTimestamp, endTimestamp);
        
        return balance.add(splitSum);
    }

    /**
     * Returns the absolute balance of account list within the specified time range while taking sub-accounts
     * into consideration. The default currency takes as base currency.
     * @param accountUIDList list of account UIDs
     * @param startTimestamp the start timestamp of the time range
     * @param endTimestamp the end timestamp of the time range
     * @return the absolute balance of account list
     */
    public Money getAccountsBalance(List<String> accountUIDList, long startTimestamp, long endTimestamp) {
        String currencyCode = GnuCashApplication.getDefaultCurrency();
        Money balance = Money.createZeroInstance(currencyCode);

        SplitsDbAdapter splitsDbAdapter = SplitsDbAdapter.getInstance();
        Money splitSum = (startTimestamp == -1 && endTimestamp == -1)
                ? splitsDbAdapter.computeSplitBalance(accountUIDList, currencyCode, true)
                : splitsDbAdapter.computeSplitBalance(accountUIDList, currencyCode, true, startTimestamp, endTimestamp);

        return balance.add(splitSum).absolute();
    }

    /**
     * Retrieve all descendant accounts of an account
     * Note, in filtering, once an account is filtered out, all its descendants
     * will also be filtered out, even they don't meet the filter where
     * @param accountUID The account to retrieve descendant accounts
     * @param where      Condition to filter accounts
     * @param whereArgs  Condition args to filter accounts
     * @return The descendant accounts list.
     */
    public List<String> getDescendantAccountUIDs(String accountUID, String where, String[] whereArgs) {
        // accountsList will hold accountUID with all descendant accounts.
        // accountsListLevel will hold descendant accounts of the same level
        ArrayList<String> accountsList = new ArrayList<String>();
        ArrayList<String> accountsListLevel = new ArrayList<String>();
        accountsListLevel.add(accountUID);
        for (;;) {
            Cursor cursor = mDb.query(AccountEntry.TABLE_NAME,
                    new String[]{AccountEntry.COLUMN_UID},
                    AccountEntry.COLUMN_PARENT_ACCOUNT_UID + " IN ( '" + TextUtils.join("' , '", accountsListLevel) + "' )" +
                            (where == null ? "" : " AND " + where),
                    whereArgs, null, null, null);
            accountsListLevel.clear();
            if (cursor != null) {
                try {
                    int columnIndex = cursor.getColumnIndexOrThrow(AccountEntry.COLUMN_UID);
                    while (cursor.moveToNext()) {
                        accountsListLevel.add(cursor.getString(columnIndex));
                    }
                } finally {
                    cursor.close();
                }
            }
            if (accountsListLevel.size() > 0) {
                accountsList.addAll(accountsListLevel);
            }
            else {
                break;
            }
        }
        return accountsList;
    }

    /**
     * Returns a cursor to the dataset containing sub-accounts of the account with record ID <code>accoundId</code>
     * @param accountUID GUID of the parent account
     * @return {@link Cursor} to the sub accounts data set
     */
    public Cursor fetchSubAccounts(String accountUID) {
        Log.v(LOG_TAG, "Fetching sub accounts for account id " + accountUID);
        String selection = AccountEntry.COLUMN_HIDDEN + " = 0 AND "
                + AccountEntry.COLUMN_PARENT_ACCOUNT_UID + " = ?";
        return mDb.query(AccountEntry.TABLE_NAME,
                null,
                selection,
                new String[]{accountUID}, null, null, AccountEntry.COLUMN_NAME + " ASC");
    }

    /**
     * Returns the top level accounts i.e. accounts with no parent or with the GnuCash ROOT account as parent
     * @return Cursor to the top level accounts
     */
    public Cursor fetchTopLevelAccounts() {
        //condition which selects accounts with no parent, whose UID is not ROOT and whose type is not ROOT
        return fetchAccounts("(" + AccountEntry.COLUMN_PARENT_ACCOUNT_UID + " IS NULL OR "
                        + AccountEntry.COLUMN_PARENT_ACCOUNT_UID + " = ?) AND "
                        + AccountEntry.COLUMN_HIDDEN + " = 0 AND "
                        + AccountEntry.COLUMN_TYPE + " != ?",
                new String[]{getOrCreateGnuCashRootAccountUID(), AccountType.ROOT.name()},
                AccountEntry.COLUMN_NAME + " ASC");
    }

    /**
     * Returns a cursor to accounts which have recently had transactions added to them
     * @return Cursor to recently used accounts
     */
    public Cursor fetchRecentAccounts(int numberOfRecent) {
        return mDb.query(TransactionEntry.TABLE_NAME
                        + " LEFT OUTER JOIN " + SplitEntry.TABLE_NAME + " ON "
                        + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_UID + " = "
                        + SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_TRANSACTION_UID
                        + " , " + AccountEntry.TABLE_NAME + " ON " + SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_ACCOUNT_UID
                        + " = " + AccountEntry.TABLE_NAME + "." + AccountEntry.COLUMN_UID,
                new String[]{AccountEntry.TABLE_NAME + ".*"},
                AccountEntry.COLUMN_HIDDEN + " = 0",
                null,
                SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_ACCOUNT_UID, //groupby
                null, //haveing
                "MAX ( " + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_TIMESTAMP + " ) DESC", // order
                Integer.toString(numberOfRecent) // limit;
        );
    }

    /**
     * Fetches favorite accounts from the database
     * @return Cursor holding set of favorite accounts
     */
    public Cursor fetchFavoriteAccounts(){
        Log.v(LOG_TAG, "Fetching favorite accounts from db");
        String condition = AccountEntry.COLUMN_FAVORITE + " = 1";
        return mDb.query(AccountEntry.TABLE_NAME,
                null, condition, null, null, null,
                AccountEntry.COLUMN_NAME + " ASC");
    }

    /**
     * Returns the GnuCash ROOT account UID if one exists (or creates one if necessary).
     * <p>In GnuCash desktop account structure, there is a root account (which is not visible in the UI) from which
     * other top level accounts derive. GnuCash Android also enforces a ROOT account now</p>
     * @return Unique ID of the GnuCash root account.
     */
    public String getOrCreateGnuCashRootAccountUID() {
        Cursor cursor = fetchAccounts(AccountEntry.COLUMN_TYPE + "= ?",
                new String[]{AccountType.ROOT.name()}, null);
        try {
            if (cursor.moveToFirst()) {
                return cursor.getString(cursor.getColumnIndexOrThrow(AccountEntry.COLUMN_UID));
            }
        } finally {
            cursor.close();
        }
        // No ROOT exits, create a new one
        Account rootAccount = new Account("ROOT Account");
        rootAccount.setAccountType(AccountType.ROOT);
        rootAccount.setFullName(ROOT_ACCOUNT_FULL_NAME);
        rootAccount.setHidden(true);
        addAccount(rootAccount);
        return rootAccount.getUID();
    }

    /**
     * Returns the number of accounts for which the account with ID <code>accoundId</code> is a first level parent
     * @param accountUID String Unique ID (GUID) of the account
     * @return Number of sub accounts
     */
    public int getSubAccountCount(String accountUID){
        //TODO: at some point when API level 11 and above only is supported, use DatabaseUtils.queryNumEntries

        String queryCount = "SELECT COUNT(*) FROM " + AccountEntry.TABLE_NAME + " WHERE "
                + AccountEntry.COLUMN_PARENT_ACCOUNT_UID + " = ?";
        Cursor cursor = mDb.rawQuery(queryCount, new String[]{accountUID});
        cursor.moveToFirst();
        int count = cursor.getInt(0);
        cursor.close();
        return count;
    }

    /**
     * Returns the number of accounts in the database
     * @return Number of accounts in the database
     */
    public int getTotalAccountCount() {
        String queryCount = "SELECT COUNT(*) FROM " + AccountEntry.TABLE_NAME;
        Cursor cursor = mDb.rawQuery(queryCount, null);
        try {
            cursor.moveToFirst();
            return cursor.getInt(0);
        } finally {
            cursor.close();
        }
    }

    /**
	 * Returns currency code of account with database ID <code>id</code>
	 * @param uid GUID of the account
	 * @return Currency code of the account
	 */
	public String getCurrencyCode(String uid){
		return getAccountCurrencyCode(uid);
	}

    /**
     * Returns the simple name of the account with unique ID <code>accountUID</code>.
     * @param accountUID Unique identifier of the account
     * @return Name of the account as String
     * @throws java.lang.IllegalArgumentException if accountUID does not exist
     * @see #getFullyQualifiedAccountName(String)
     */
    public String getAccountName(String accountUID){
        Cursor cursor = mDb.query(AccountEntry.TABLE_NAME,
                new String[]{AccountEntry._ID, AccountEntry.COLUMN_NAME},
                AccountEntry.COLUMN_UID + " = ?",
                new String[]{accountUID}, null, null, null);
        try {
            if (cursor.moveToNext()) {
                return cursor.getString(cursor.getColumnIndexOrThrow(AccountEntry.COLUMN_NAME));
            } else {
                throw new IllegalArgumentException("account " + accountUID + " does not exist");
            }
        } finally {
            cursor.close();
        }
    }

    /**
     * Returns the default transfer account record ID for the account with UID <code>accountUID</code>
     * @param accountID Database ID of the account record
     * @return Record ID of default transfer account
     */
    public long getDefaultTransferAccountID(long accountID){
        Cursor cursor = mDb.query(AccountEntry.TABLE_NAME,
                new String[]{AccountEntry.COLUMN_DEFAULT_TRANSFER_ACCOUNT_UID},
                AccountEntry._ID + " = " + accountID,
                null, null, null, null);
       try {
            if (cursor.moveToNext()) {
                String uid = cursor.getString(
                        cursor.getColumnIndexOrThrow(AccountEntry.COLUMN_DEFAULT_TRANSFER_ACCOUNT_UID));
                if (uid == null)
                    return 0;
                else
                    return getID(uid);
            } else {
                return 0;
            }
        } finally {
            cursor.close();
        }
    }

    /**
     * Returns the full account name including the account hierarchy (parent accounts)
     * @param accountUID Unique ID of account
     * @return Fully qualified (with parent hierarchy) account name
     */
    public String getFullyQualifiedAccountName(String accountUID){
        String accountName = getAccountName(accountUID);
        String parentAccountUID = getParentAccountUID(accountUID);

        if (parentAccountUID == null || parentAccountUID.equalsIgnoreCase(getOrCreateGnuCashRootAccountUID())){
            return accountName;
        }

        String parentAccountName = getFullyQualifiedAccountName(parentAccountUID);

        return parentAccountName + ACCOUNT_NAME_SEPARATOR + accountName;
    }

    /**
     * get account's full name directly from DB
     * @param accountUID the account to retrieve full name
     * @return full name registered in DB
     */
    public String getAccountFullName(String accountUID) {
        Cursor cursor = mDb.query(AccountEntry.TABLE_NAME, new String[]{AccountEntry.COLUMN_FULL_NAME},
                AccountEntry.COLUMN_UID + " = ?", new String[]{accountUID},
                null, null, null);
        try {
            if (cursor.moveToFirst()) {
                return cursor.getString(cursor.getColumnIndexOrThrow(AccountEntry.COLUMN_FULL_NAME));
            }
        }
        finally {
            cursor.close();
        }
        throw new IllegalArgumentException("account UID: " + accountUID + " does not exist");
    }

    /**
     * Overloaded convenience method.
     * Simply resolves the account UID and calls {@link #getFullyQualifiedAccountName(String)}
     * @param accountId Database record ID of account
     * @return Fully qualified (with parent hierarchy) account name
     */
    public String getFullyQualifiedAccountName(long accountId){
        return getFullyQualifiedAccountName(getUID(accountId));
    }

    /**
     * Returns <code>true</code> if the account with unique ID <code>accountUID</code> is a placeholder account.
     * @param accountUID Unique identifier of the account
     * @return <code>true</code> if the account is a placeholder account, <code>false</code> otherwise
     */
    public boolean isPlaceholderAccount(String accountUID) {
        String isPlaceholder = getAttribute(accountUID, AccountEntry.COLUMN_PLACEHOLDER);
        return Integer.parseInt(isPlaceholder) == 1;
    }

    /**
     * Convenience method, resolves the account unique ID and calls {@link #isPlaceholderAccount(String)}
     * @param accountUID GUID of the account
     * @return <code>true</code> if the account is hidden, <code>false</code> otherwise
     */
    public boolean isHiddenAccount(String accountUID){
        String isHidden = getAttribute(accountUID, AccountEntry.COLUMN_HIDDEN);
        return Integer.parseInt(isHidden) == 1;
    }

    /**
     * Returns true if the account is a favorite account, false otherwise
     * @param accountUID GUID of the account
     * @return <code>true</code> if the account is a favorite account, <code>false</code> otherwise
     */
    public boolean isFavoriteAccount(String accountUID){
        String isFavorite = getAttribute(accountUID, AccountEntry.COLUMN_FAVORITE);
        return Integer.parseInt(isFavorite) == 1;
    }

    /**
     * Updates all opening balances to the current account balances
     */
    public List<Transaction> getAllOpeningBalanceTransactions(){
        Cursor cursor = fetchAccounts(null, null, null);
        List<Transaction> openingTransactions = new ArrayList<Transaction>();
        try {
            SplitsDbAdapter splitsDbAdapter = mTransactionsAdapter.getSplitDbAdapter();
            while (cursor.moveToNext()) {
                long id = cursor.getLong(cursor.getColumnIndexOrThrow(AccountEntry._ID));
                String accountUID = getUID(id);
                String currencyCode = getCurrencyCode(accountUID);
                ArrayList<String> accountList = new ArrayList<String>();
                accountList.add(accountUID);
                Money balance = splitsDbAdapter.computeSplitBalance(accountList,
                        currencyCode, getAccountType(accountUID).hasDebitNormalBalance());
                if (balance.asBigDecimal().compareTo(new BigDecimal(0)) == 0)
                    continue;

                Transaction transaction = new Transaction(GnuCashApplication.getAppContext().getString(R.string.account_name_opening_balances));
                transaction.setNote(getName(id));
                transaction.setCurrencyCode(currencyCode);
                TransactionType transactionType = Transaction.getTypeForBalance(getAccountType(accountUID),
                        balance.isNegative());
                Split split = new Split(balance.absolute(), accountUID);
                split.setType(transactionType);
                transaction.addSplit(split);
                transaction.addSplit(split.createPair(getOrCreateOpeningBalanceAccountUID()));
                transaction.setExported(true);
                openingTransactions.add(transaction);
            }
        } finally {
            cursor.close();
        }
        return openingTransactions;
    }

    public static String getImbalanceAccountPrefix() {
         return GnuCashApplication.getAppContext().getString(R.string.imbalance_account_name) + "-";
    }

    /**
     * Returns the imbalance account where to store transactions which are not double entry
     * @param currency Currency of the transaction
     * @return Imbalance account name
     */
    public static String getImbalanceAccountName(Currency currency){
        return getImbalanceAccountPrefix() + currency.getCurrencyCode();
    }

    /**
     * Get the name of the default account for opening balances for the current locale.
     * For the English locale, it will be "Equity:Opening Balances"
     * @return Fully qualified account name of the opening balances account
     */
    public static String getOpeningBalanceAccountFullName(){
        Context context = GnuCashApplication.getAppContext();
        String parentEquity = context.getString(R.string.account_name_equity).trim();
        //German locale has no parent Equity account
        if (parentEquity.length() > 0) {
            return parentEquity + ACCOUNT_NAME_SEPARATOR
                    + context.getString(R.string.account_name_opening_balances);
        } else
            return context.getString(R.string.account_name_opening_balances);
    }

    /**
     * Returns the list of currencies in the database
     * @return List of currencies in the database
     */
    public List<Currency> getCurrencies(){
        Cursor cursor = mDb.query(true, AccountEntry.TABLE_NAME, new String[]{AccountEntry.COLUMN_CURRENCY},
                null, null, null, null, null, null);
        List<Currency> currencyList = new ArrayList<Currency>();
        try {
            while (cursor.moveToNext()) {
                String currencyCode = cursor.getString(cursor.getColumnIndexOrThrow(AccountEntry.COLUMN_CURRENCY));
                currencyList.add(Currency.getInstance(currencyCode));
            }
        } finally {
            cursor.close();
        }
        return currencyList;
    }

    /**
	 * Deletes all accounts, transactions (and their splits) from the database.
     * Basically empties all 3 tables, so use with care ;)
	 */
    @Override
	public int deleteAllRecords(){
		mDb.delete(TransactionEntry.TABLE_NAME, null, null); //this will take the splits along with it
        mDb.delete(DatabaseSchema.ScheduledActionEntry.TABLE_NAME, null, null);
        return mDb.delete(AccountEntry.TABLE_NAME, null, null);
	}

    public int getTransactionMaxSplitNum(@NonNull String accountUID) {
        Cursor cursor = mDb.query("trans_extra_info",
                new String[]{"MAX(trans_split_count)"},
                "trans_acct_t_uid IN ( SELECT DISTINCT " + TransactionEntry.TABLE_NAME + "_" + TransactionEntry.COLUMN_UID +
                        " FROM trans_split_acct WHERE " + AccountEntry.TABLE_NAME + "_" + AccountEntry.COLUMN_UID +
                        " = ? )",
                new String[]{accountUID},
                null,
                null,
                null
                );
        try {
            if (cursor.moveToFirst()) {
                return (int)cursor.getLong(0);
            } else {
                return 0;
            }
        }
        finally {
            cursor.close();
        }
    }
}


File: app/src/main/java/org/gnucash/android/db/DatabaseAdapter.java
/*
 * Copyright (c) 2012 - 2015 Ngewi Fet <ngewif@gmail.com>
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

package org.gnucash.android.db;

import android.content.ContentValues;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.support.annotation.NonNull;
import android.util.Log;

import org.gnucash.android.db.DatabaseSchema.AccountEntry;
import org.gnucash.android.db.DatabaseSchema.CommonColumns;
import org.gnucash.android.db.DatabaseSchema.SplitEntry;
import org.gnucash.android.db.DatabaseSchema.TransactionEntry;
import org.gnucash.android.model.AccountType;
import org.gnucash.android.model.BaseModel;

import java.sql.Timestamp;

/**
 * Adapter to be used for creating and opening the database for read/write operations.
 * The adapter abstracts several methods for database access and should be subclassed
 * by any other adapters to database-backed data models.
 * @author Ngewi Fet <ngewif@gmail.com>
 *
 */
public abstract class DatabaseAdapter {
	/**
	 * Tag for logging
	 */
	protected static String LOG_TAG = "DatabaseAdapter";

	/**
	 * SQLite database
	 */
    protected final SQLiteDatabase mDb;

    protected final String mTableName;

    /**
     * Opens the database adapter with an existing database
     * @param db SQLiteDatabase object
     */
    public DatabaseAdapter(SQLiteDatabase db, @NonNull String tableName) {
        this.mTableName = tableName;
        this.mDb = db;
        if (!db.isOpen() || db.isReadOnly())
            throw new IllegalArgumentException("Database not open or is read-only. Require writeable database");

        if (mDb.getVersion() >= DatabaseSchema.SPLITS_DB_VERSION) {
            createTempView();
        }
    }

    private void createTempView() {
        // Create some temporary views. Temporary views only exists in one DB session, and will not
        // be saved in the DB
        //
        // TODO: Useful views should be add to the DB
        //
        // create a temporary view, combining accounts, transactions and splits, as this is often used
        // in the queries
        mDb.execSQL("CREATE TEMP VIEW IF NOT EXISTS trans_split_acct AS SELECT "
                        + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_UID + " AS "
                        + TransactionEntry.TABLE_NAME + "_" + TransactionEntry.COLUMN_UID + " , "
                        + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_DESCRIPTION + " AS "
                        + TransactionEntry.TABLE_NAME + "_" + TransactionEntry.COLUMN_DESCRIPTION + " , "
                        + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_NOTES + " AS "
                        + TransactionEntry.TABLE_NAME + "_" + TransactionEntry.COLUMN_NOTES + " , "
                        + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_CURRENCY + " AS "
                        + TransactionEntry.TABLE_NAME + "_" + TransactionEntry.COLUMN_CURRENCY + " , "
                        + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_TIMESTAMP + " AS "
                        + TransactionEntry.TABLE_NAME + "_" + TransactionEntry.COLUMN_TIMESTAMP + " , "
                        + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_EXPORTED + " AS "
                        + TransactionEntry.TABLE_NAME + "_" + TransactionEntry.COLUMN_EXPORTED + " , "
                        + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_TEMPLATE + " AS "
                        + TransactionEntry.TABLE_NAME + "_" + TransactionEntry.COLUMN_TEMPLATE + " , "
                        + SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_UID + " AS "
                        + SplitEntry.TABLE_NAME + "_" + SplitEntry.COLUMN_UID + " , "
                        + SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_TYPE + " AS "
                        + SplitEntry.TABLE_NAME + "_" + SplitEntry.COLUMN_TYPE + " , "
                        + SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_AMOUNT + " AS "
                        + SplitEntry.TABLE_NAME + "_" + SplitEntry.COLUMN_AMOUNT + " , "
                        + SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_MEMO + " AS "
                        + SplitEntry.TABLE_NAME + "_" + SplitEntry.COLUMN_MEMO + " , "
                        + AccountEntry.TABLE_NAME + "." + AccountEntry.COLUMN_UID + " AS "
                        + AccountEntry.TABLE_NAME + "_" + AccountEntry.COLUMN_UID + " , "
                        + AccountEntry.TABLE_NAME + "." + AccountEntry.COLUMN_NAME + " AS "
                        + AccountEntry.TABLE_NAME + "_" + AccountEntry.COLUMN_NAME + " , "
                        + AccountEntry.TABLE_NAME + "." + AccountEntry.COLUMN_CURRENCY + " AS "
                        + AccountEntry.TABLE_NAME + "_" + AccountEntry.COLUMN_CURRENCY + " , "
                        + AccountEntry.TABLE_NAME + "." + AccountEntry.COLUMN_PARENT_ACCOUNT_UID + " AS "
                        + AccountEntry.TABLE_NAME + "_" + AccountEntry.COLUMN_PARENT_ACCOUNT_UID + " , "
                        + AccountEntry.TABLE_NAME + "." + AccountEntry.COLUMN_PLACEHOLDER + " AS "
                        + AccountEntry.TABLE_NAME + "_" + AccountEntry.COLUMN_PLACEHOLDER + " , "
                        + AccountEntry.TABLE_NAME + "." + AccountEntry.COLUMN_COLOR_CODE + " AS "
                        + AccountEntry.TABLE_NAME + "_" + AccountEntry.COLUMN_COLOR_CODE + " , "
                        + AccountEntry.TABLE_NAME + "." + AccountEntry.COLUMN_FAVORITE + " AS "
                        + AccountEntry.TABLE_NAME + "_" + AccountEntry.COLUMN_FAVORITE + " , "
                        + AccountEntry.TABLE_NAME + "." + AccountEntry.COLUMN_FULL_NAME + " AS "
                        + AccountEntry.TABLE_NAME + "_" + AccountEntry.COLUMN_FULL_NAME + " , "
                        + AccountEntry.TABLE_NAME + "." + AccountEntry.COLUMN_TYPE + " AS "
                        + AccountEntry.TABLE_NAME + "_" + AccountEntry.COLUMN_TYPE + " , "
                        + AccountEntry.TABLE_NAME + "." + AccountEntry.COLUMN_DEFAULT_TRANSFER_ACCOUNT_UID + " AS "
                        + AccountEntry.TABLE_NAME + "_" + AccountEntry.COLUMN_DEFAULT_TRANSFER_ACCOUNT_UID
                        + " FROM " + TransactionEntry.TABLE_NAME + " , " + SplitEntry.TABLE_NAME + " ON "
                        + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_UID + "=" + SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_TRANSACTION_UID
                        + " , " + AccountEntry.TABLE_NAME + " ON "
                        + SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_ACCOUNT_UID + "=" + AccountEntry.TABLE_NAME + "." + AccountEntry.COLUMN_UID
        );

        // SELECT transactions_uid AS trans_acct_t_uid ,
        //      SUBSTR (
        //          MIN (
        //              ( CASE WHEN IFNULL ( splits_memo , '' ) == '' THEN 'a' ELSE 'b' END ) || accounts_uid
        //          ) ,
        //          2
        //      ) as trans_acct_a_uid ,
        //   TOTAL ( CASE WHEN splits_type = 'DEBIT' THEN splits_amount ELSE - splits_amount END ) AS trans_acct_balance,
        //   COUNT ( DISTINCT accounts_currency ) as trans_currency_count
        //   FROM trans_split_acct GROUP BY transactions_uid
        //
        // This temporary view would pick one Account_UID for each
        // Transaction, which can be used to order all transactions. If possible, account_uid of a split whose
        // memo is null is select.
        //
        // Transaction balance is also picked out by this view
        //
        // a split without split memo is chosen if possible, in the following manner:
        //   if the splits memo is null or empty string, attach an 'a' in front of the split account uid,
        //   if not, attach a 'b' to the split account uid
        //   pick the minimal value of the modified account uid (one of the ones begins with 'a', if exists)
        //   use substr to get account uid
        mDb.execSQL("CREATE TEMP VIEW IF NOT EXISTS trans_extra_info AS SELECT " + TransactionEntry.TABLE_NAME + "_" + TransactionEntry.COLUMN_UID +
                " AS trans_acct_t_uid , SUBSTR ( MIN ( ( CASE WHEN IFNULL ( " + SplitEntry.TABLE_NAME + "_" +
                SplitEntry.COLUMN_MEMO + " , '' ) == '' THEN 'a' ELSE 'b' END ) || " +
                AccountEntry.TABLE_NAME + "_" + AccountEntry.COLUMN_UID +
                " ) , 2 ) AS trans_acct_a_uid , TOTAL ( CASE WHEN " + SplitEntry.TABLE_NAME + "_" +
                SplitEntry.COLUMN_TYPE + " = 'DEBIT' THEN "+ SplitEntry.TABLE_NAME + "_" +
                SplitEntry.COLUMN_AMOUNT + " ELSE - " + SplitEntry.TABLE_NAME + "_" +
                SplitEntry.COLUMN_AMOUNT + " END ) AS trans_acct_balance , COUNT ( DISTINCT " +
                AccountEntry.TABLE_NAME + "_" + AccountEntry.COLUMN_CURRENCY +
                " ) AS trans_currency_count , COUNT (*) AS trans_split_count FROM trans_split_acct " +
                " GROUP BY " + TransactionEntry.TABLE_NAME + "_" + TransactionEntry.COLUMN_UID
        );
    }

    /**
     * Checks if the database is open
     * @return <code>true</code> if the database is open, <code>false</code> otherwise
     */
    public boolean isOpen(){
        return mDb.isOpen();
    }

    /**
     * Returns a ContentValues object which has the data of the base model
     * @param model {@link org.gnucash.android.model.BaseModel} from which to extract values
     * @return {@link android.content.ContentValues} with the data to be inserted into the db
     */
    protected ContentValues getContentValues(BaseModel model){
        ContentValues contentValues = new ContentValues();
        contentValues.put(CommonColumns.COLUMN_UID, model.getUID());
        contentValues.put(CommonColumns.COLUMN_CREATED_AT, model.getCreatedTimestamp().toString());
        //there is a trigger in the database for updated the modified_at column
        /* Due to the use of SQL REPLACE syntax, we insert the created_at values each time
        * (maintain the original creation time and not the time of creation of the replacement)
        * The updated_at column has a trigger in the database which will update the column
         */
        return contentValues;
    }

    /**
     * Initializes the model with values from the database record common to all models (i.e. in the BaseModel)
     * @param cursor Cursor pointing to database record
     * @param model Model instance to be initialized
     */
    protected static void populateModel(Cursor cursor, BaseModel model){
        String uid = cursor.getString(cursor.getColumnIndexOrThrow(CommonColumns.COLUMN_UID));
        String created = cursor.getString(cursor.getColumnIndexOrThrow(CommonColumns.COLUMN_CREATED_AT));
        String modified= cursor.getString(cursor.getColumnIndexOrThrow(CommonColumns.COLUMN_MODIFIED_AT));

        model.setUID(uid);
        model.setCreatedTimestamp(Timestamp.valueOf(created));
        model.setModifiedTimestamp(Timestamp.valueOf(modified));
    }

	/**
	 * Retrieves record with id <code>rowId</code> from database table
	 * @param rowId ID of record to be retrieved
	 * @return {@link Cursor} to record retrieved
	 */
	public Cursor fetchRecord(long rowId){
		return mDb.query(mTableName, null, DatabaseSchema.CommonColumns._ID + "=" + rowId,
				null, null, null, null);
	}

    /**
     * Retrieves record with GUID {@code uid} from database table
     * @param uid GUID of record to be retrieved
     * @return {@link Cursor} to record retrieved
     */
    public Cursor fetchRecord(@NonNull String uid){
        return mDb.query(mTableName, null, CommonColumns.COLUMN_UID + "=?" ,
                new String[]{uid}, null, null, null);
    }

	/**
	 * Retrieves all records from database table
	 * @return {@link Cursor} to all records in table <code>tableName</code>
	 */
	public Cursor fetchAllRecords(){
		return fetchAllRecords(null, null);
	}

    /**
     * Fetch all records from database matching conditions
     * @param where SQL where clause
     * @param whereArgs String arguments for where clause
     * @return Cursor to records matching conditions
     */
    public Cursor fetchAllRecords(String where, String[] whereArgs){
        return mDb.query(mTableName, null, where, whereArgs, null, null, null);
    }

	/**
	 * Deletes record with ID <code>rowID</code> from database table.
	 * @param rowId ID of record to be deleted
	 * @return <code>true</code> if deletion was successful, <code>false</code> otherwise
	 */
	public boolean deleteRecord(long rowId){
        Log.d(LOG_TAG, "Deleting record with id " + rowId + " from " + mTableName);
		return mDb.delete(mTableName, DatabaseSchema.CommonColumns._ID + "=" + rowId, null) > 0;
	}

    /**
     * Deletes all records in the database
     * @return Number of deleted records
     */
    public int deleteAllRecords(){
        return mDb.delete(mTableName, null, null);
    }

    /**
     * Returns the string unique ID (GUID) of a record in the database
     * @param uid GUID of the record
     * @return Long record ID
     * @throws IllegalArgumentException if the GUID does not exist in the database
     */
    public long getID(@NonNull String uid){
        Cursor cursor = mDb.query(mTableName,
                new String[] {DatabaseSchema.CommonColumns._ID},
                DatabaseSchema.CommonColumns.COLUMN_UID + " = ?",
                new String[]{uid},
                null, null, null);
        long result = -1;
        try{
            if (cursor.moveToFirst()) {
                Log.d(LOG_TAG, "Transaction already exists. Returning existing id");
                result = cursor.getLong(cursor.getColumnIndexOrThrow(DatabaseSchema.CommonColumns._ID));
            } else {
                throw new IllegalArgumentException("Account UID " + uid + " does not exist in the db");
            }
        } finally {
            cursor.close();
        }
        return result;
    }

    /**
     * Returns the string unique ID (GUID) of a record in the database
     * @param id long database record ID
     * @return GUID of the record
     */
    public String getUID(long id){
        Cursor cursor = mDb.query(mTableName,
                new String[]{DatabaseSchema.CommonColumns.COLUMN_UID},
                DatabaseSchema.CommonColumns._ID + " = " + id,
                null, null, null, null);

        String uid = null;
        try {
            if (cursor.moveToFirst()) {
                uid = cursor.getString(cursor.getColumnIndexOrThrow(DatabaseSchema.CommonColumns.COLUMN_UID));
            } else {
                throw new IllegalArgumentException("Account record ID " + id + " does not exist in the db");
            }
        } finally {
            cursor.close();
        }
        return uid;
    }

    /**
     * Returns the currency code (according to the ISO 4217 standard) of the account
     * with unique Identifier <code>accountUID</code>
     * @param accountUID Unique Identifier of the account
     * @return Currency code of the account. "" if accountUID
     *      does not exist in DB
     */
    public String getAccountCurrencyCode(@NonNull String accountUID) {
        Cursor cursor = mDb.query(DatabaseSchema.AccountEntry.TABLE_NAME,
                new String[] {DatabaseSchema.AccountEntry.COLUMN_CURRENCY},
                DatabaseSchema.AccountEntry.COLUMN_UID + "= ?",
                new String[]{accountUID}, null, null, null);
        try {
            if (cursor.moveToFirst()) {
                return cursor.getString(0);
            } else {
                throw new IllegalArgumentException("Account " + accountUID + " does not exist");
            }
        } finally {
            cursor.close();
        }
    }

    /**
     * Returns the {@link org.gnucash.android.model.AccountType} of the account with unique ID <code>uid</code>
     * @param accountUID Unique ID of the account
     * @return {@link org.gnucash.android.model.AccountType} of the account.
     * @throws java.lang.IllegalArgumentException if accountUID does not exist in DB,
     */
    public AccountType getAccountType(@NonNull String accountUID){
        String type = "";
        Cursor c = mDb.query(DatabaseSchema.AccountEntry.TABLE_NAME,
                new String[]{DatabaseSchema.AccountEntry.COLUMN_TYPE},
                DatabaseSchema.AccountEntry.COLUMN_UID + "=?",
                new String[]{accountUID}, null, null, null);
        try {
            if (c.moveToFirst()) {
                type = c.getString(c.getColumnIndexOrThrow(DatabaseSchema.AccountEntry.COLUMN_TYPE));
            } else {
                throw new IllegalArgumentException("account " + accountUID + " does not exist in DB");
            }
        } finally {
            c.close();
        }
        return AccountType.valueOf(type);
    }

    /**
     * Updates a record in the table
     * @param recordId Database ID of the record to be updated
     * @param columnKey Name of column to be updated
     * @param newValue  New value to be assigned to the columnKey
     * @return Number of records affected
     */
    protected int updateRecord(String tableName, long recordId, String columnKey, String newValue) {
        ContentValues contentValues = new ContentValues();
        if (newValue == null) {
            contentValues.putNull(columnKey);
        } else {
            contentValues.put(columnKey, newValue);
        }
        return mDb.update(tableName, contentValues,
                DatabaseSchema.CommonColumns._ID + "=" + recordId, null);
    }

    /**
     * Updates a record in the table
     * @param uid GUID of the record
     * @param columnKey Name of column to be updated
     * @param newValue  New value to be assigned to the columnKey
     * @return Number of records affected
     */
    public int updateRecord(@NonNull String uid, @NonNull String columnKey, String newValue) {
        return updateRecords(CommonColumns.COLUMN_UID + "= ?", new String[]{uid}, columnKey, newValue);
    }

    /**
     * Overloaded method. Updates the record with GUID {@code uid} with the content values
     * @param uid GUID of the record
     * @param contentValues Content values to update
     * @return Number of records updated
     */
    public int updateRecord(@NonNull String uid, @NonNull ContentValues contentValues){
        return mDb.update(mTableName, contentValues, CommonColumns.COLUMN_UID + "=?", new String[]{uid});
    }

    /**
     * Updates all records which match the {@code where} clause with the {@code newValue} for the column
     * @param where SQL where clause
     * @param whereArgs String arguments for where clause
     * @param columnKey Name of column to be updated
     * @param newValue New value to be assigned to the columnKey
     * @return Number of records affected
     */
    public int updateRecords(String where, String[] whereArgs, @NonNull String columnKey, String newValue){
        ContentValues contentValues = new ContentValues();
        if (newValue == null) {
            contentValues.putNull(columnKey);
        } else {
            contentValues.put(columnKey, newValue);
        }
        return mDb.update(mTableName, contentValues, where, whereArgs);
    }

    /**
     * Deletes a record from the database given its unique identifier.
     * <p>Overload of the method {@link #deleteRecord(long)}</p>
     * @param uid GUID of the record
     * @return <code>true</code> if deletion was successful, <code>false</code> otherwise
     * @see #deleteRecord(long)
     */
    public boolean deleteRecord(@NonNull String uid){
        return deleteRecord(getID(uid));
    }

    /**
     * Returns an attribute from a specific column in the database for a specific record.
     * <p>The attribute is returned as a string which can then be converted to another type if
     * the caller was expecting something other type </p>
     * @param recordUID GUID of the record
     * @param columnName Name of the column to be retrieved
     * @return String value of the column entry
     * @throws IllegalArgumentException if either the {@code recordUID} or {@code columnName} do not exist in the database
     */
    public String getAttribute(@NonNull String recordUID, @NonNull String columnName){
        Cursor cursor = mDb.query(mTableName,
                new String[]{columnName},
                AccountEntry.COLUMN_UID + " = ?",
                new String[]{recordUID}, null, null, null);

        try {
            if (cursor.moveToFirst())
                return cursor.getString(cursor.getColumnIndexOrThrow(columnName));
            else {
                throw new IllegalArgumentException(String.format("Record with GUID %s does not exist in the db", recordUID));
            }
        } finally {
            cursor.close();
        }
    }

    /**
     * Expose mDb.beginTransaction()
     */
    public void beginTransaction() {
        mDb.beginTransaction();
    }

    /**
     * Expose mDb.setTransactionSuccessful()
     */
    public void setTransactionSuccessful() {
        mDb.setTransactionSuccessful();
    }

    /**
     * Expose mDb.endTransaction()
     */
    public void endTransaction() {
        mDb.endTransaction();
    }
}


File: app/src/main/java/org/gnucash/android/db/TransactionsDbAdapter.java
/*
 * Copyright (c) 2012 - 2015 Ngewi Fet <ngewif@gmail.com>
 * Copyright (c) 2014 Yongxin Wang <fefe.wyx@gmail.com>
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

package org.gnucash.android.db;

import android.content.ContentValues;
import android.database.Cursor;
import android.database.SQLException;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteQueryBuilder;
import android.database.sqlite.SQLiteStatement;
import android.support.annotation.Nullable;
import android.text.TextUtils;
import android.util.Log;

import com.crashlytics.android.Crashlytics;

import org.gnucash.android.app.GnuCashApplication;
import org.gnucash.android.model.AccountType;
import org.gnucash.android.model.Money;
import org.gnucash.android.model.Split;
import org.gnucash.android.model.Transaction;

import java.util.ArrayList;
import java.util.List;

import static org.gnucash.android.db.DatabaseSchema.AccountEntry;
import static org.gnucash.android.db.DatabaseSchema.ScheduledActionEntry;
import static org.gnucash.android.db.DatabaseSchema.SplitEntry;
import static org.gnucash.android.db.DatabaseSchema.TransactionEntry;

/**
 * Manages persistence of {@link Transaction}s in the database
 * Handles adding, modifying and deleting of transaction records.
 * @author Ngewi Fet <ngewif@gmail.com> 
 * @author Yongxin Wang <fefe.wyx@gmail.com>
 * @author Oleksandr Tyshkovets <olexandr.tyshkovets@gmail.com>
 */
public class TransactionsDbAdapter extends DatabaseAdapter {

    private final SplitsDbAdapter mSplitsDbAdapter;

    /**
     * Overloaded constructor. Creates adapter for already open db
     * @param db SQlite db instance
     */
    public TransactionsDbAdapter(SQLiteDatabase db, SplitsDbAdapter splitsDbAdapter) {
        super(db, TransactionEntry.TABLE_NAME);
        mSplitsDbAdapter = splitsDbAdapter;
        LOG_TAG = "TransactionsDbAdapter";
    }

    /**
     * Returns an application-wide instance of the database adapter
     * @return Transaction database adapter
     */
    public static TransactionsDbAdapter getInstance(){
        return GnuCashApplication.getTransactionDbAdapter();
    }

    public SplitsDbAdapter getSplitDbAdapter() {
        return mSplitsDbAdapter;
    }

    /**
	 * Adds an transaction to the database. 
	 * If a transaction already exists in the database with the same unique ID, 
	 * then the record will just be updated instead
	 * @param transaction {@link Transaction} to be inserted to database
	 * @return Database row ID of the inserted transaction
	 */
	public long addTransaction(Transaction transaction){
		ContentValues contentValues = getContentValues(transaction);
		contentValues.put(TransactionEntry.COLUMN_DESCRIPTION, transaction.getDescription());
		contentValues.put(TransactionEntry.COLUMN_TIMESTAMP,    transaction.getTimeMillis());
		contentValues.put(TransactionEntry.COLUMN_NOTES,        transaction.getNote());
		contentValues.put(TransactionEntry.COLUMN_EXPORTED,     transaction.isExported() ? 1 : 0);
		contentValues.put(TransactionEntry.COLUMN_TEMPLATE,     transaction.isTemplate() ? 1 : 0);
        contentValues.put(TransactionEntry.COLUMN_CURRENCY,     transaction.getCurrencyCode());
        contentValues.put(TransactionEntry.COLUMN_SCHEDX_ACTION_UID, transaction.getScheduledActionUID());

        Log.d(LOG_TAG, "Replacing transaction in db");
        long rowId = -1;
        mDb.beginTransaction();
        try {
            rowId = mDb.replaceOrThrow(TransactionEntry.TABLE_NAME, null, contentValues);

            Log.d(LOG_TAG, "Adding splits for transaction");
            ArrayList<String> splitUIDs = new ArrayList<String>(transaction.getSplits().size());
            for (Split split : transaction.getSplits()) {
                contentValues = getContentValues(split);
                contentValues.put(SplitEntry.COLUMN_AMOUNT,     split.getAmount().absolute().toPlainString());
                contentValues.put(SplitEntry.COLUMN_TYPE,       split.getType().name());
                contentValues.put(SplitEntry.COLUMN_MEMO,       split.getMemo());
                contentValues.put(SplitEntry.COLUMN_ACCOUNT_UID, split.getAccountUID());
                contentValues.put(SplitEntry.COLUMN_TRANSACTION_UID, split.getTransactionUID());
                splitUIDs.add(split.getUID());

                Log.d(LOG_TAG, "Replace transaction split in db");
                mDb.replaceOrThrow(SplitEntry.TABLE_NAME, null, contentValues);
            }
            Log.d(LOG_TAG, transaction.getSplits().size() + " splits added");

            long deleted = mDb.delete(SplitEntry.TABLE_NAME,
                    SplitEntry.COLUMN_TRANSACTION_UID + " = ? AND "
                            + SplitEntry.COLUMN_UID + " NOT IN ('" + TextUtils.join("' , '", splitUIDs) + "')",
                    new String[]{transaction.getUID()});
            Log.d(LOG_TAG, deleted + " splits deleted");
            mDb.setTransactionSuccessful();
        } catch (SQLException sqle) {
            Log.e(LOG_TAG, sqle.getMessage());
            Crashlytics.logException(sqle);
        } finally {
            mDb.endTransaction();
        }
        return rowId;
	}

    /**
     * Adds an several transactions to the database.
     * If a transaction already exists in the database with the same unique ID,
     * then the record will just be updated instead. Recurrence Transactions will not
     * be inserted, instead schedule Transaction would be called. If an exception
     * occurs, no transaction would be inserted.
     * @param transactionList {@link Transaction} transactions to be inserted to database
     * @return Number of transactions inserted
     */
    public long bulkAddTransactions(List<Transaction> transactionList){
        List<Split> splitList = new ArrayList<>(transactionList.size()*3);
        long rowInserted = 0;
        try {
            mDb.beginTransaction();
            SQLiteStatement replaceStatement = mDb.compileStatement("REPLACE INTO " + TransactionEntry.TABLE_NAME + " ( "
                    + TransactionEntry.COLUMN_UID + " , "
                    + TransactionEntry.COLUMN_DESCRIPTION + " , "
                    + TransactionEntry.COLUMN_NOTES + " , "
                    + TransactionEntry.COLUMN_TIMESTAMP + " , "
                    + TransactionEntry.COLUMN_EXPORTED + " , "
                    + TransactionEntry.COLUMN_CURRENCY + " , "
                    + TransactionEntry.COLUMN_CREATED_AT + " , "
                    + TransactionEntry.COLUMN_SCHEDX_ACTION_UID + " , "
                    + TransactionEntry.COLUMN_TEMPLATE + " ) VALUES ( ? , ? , ? , ?, ? , ? , ? , ? , ?)");
            for (Transaction transaction : transactionList) {
                //Log.d(TAG, "Replacing transaction in db");
                replaceStatement.clearBindings();
                replaceStatement.bindString(1, transaction.getUID());
                replaceStatement.bindString(2, transaction.getDescription());
                replaceStatement.bindString(3, transaction.getNote());
                replaceStatement.bindLong(4, transaction.getTimeMillis());
                replaceStatement.bindLong(5, transaction.isExported() ? 1 : 0);
                replaceStatement.bindString(6,  transaction.getCurrencyCode());
                replaceStatement.bindString(7,  transaction.getCreatedTimestamp().toString());
                if (transaction.getScheduledActionUID() == null)
                    replaceStatement.bindNull(8);
                else
                    replaceStatement.bindString(8,  transaction.getScheduledActionUID());
                replaceStatement.bindLong(9,    transaction.isTemplate() ? 1 : 0);
                replaceStatement.execute();
                rowInserted ++;
                splitList.addAll(transaction.getSplits());
            }
            mDb.setTransactionSuccessful();
        }
        finally {
            mDb.endTransaction();
        }
        if (rowInserted != 0 && !splitList.isEmpty()) {
            try {
                long nSplits = mSplitsDbAdapter.bulkAddSplits(splitList);
                Log.d(LOG_TAG, String.format("%d splits inserted", nSplits));
            }
            finally {
                SQLiteStatement deleteEmptyTransaction = mDb.compileStatement("DELETE FROM " +
                        TransactionEntry.TABLE_NAME + " WHERE NOT EXISTS ( SELECT * FROM " +
                        SplitEntry.TABLE_NAME +
                        " WHERE " + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_UID +
                        " = " + SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_TRANSACTION_UID + " ) ");
                deleteEmptyTransaction.execute();
            }
        }
        return rowInserted;
    }

	/**
	 * Retrieves a transaction object from a database with database ID <code>rowId</code>
	 * @param rowId Identifier of the transaction record to be retrieved
	 * @return {@link Transaction} object corresponding to database record
	 */
    public Transaction getTransaction(long rowId) {
        Log.v(LOG_TAG, "Fetching transaction with id " + rowId);
        Cursor c = fetchRecord(rowId);
        try {
            if (c.moveToFirst()) {
                return buildTransactionInstance(c);
            } else {
                throw new IllegalArgumentException("row " + rowId + " does not exist");
            }
        } finally {
            c.close();
        }
    }
	
	/**
	 * Returns a cursor to a set of all transactions which have a split belonging to the accound with unique ID
	 * <code>accountUID</code>.
	 * @param accountUID UID of the account whose transactions are to be retrieved
	 * @return Cursor holding set of transactions for particular account
     * @throws java.lang.IllegalArgumentException if the accountUID is null
	 */
	public Cursor fetchAllTransactionsForAccount(String accountUID){
        SQLiteQueryBuilder queryBuilder = new SQLiteQueryBuilder();
        queryBuilder.setTables(TransactionEntry.TABLE_NAME
                + " INNER JOIN " + SplitEntry.TABLE_NAME + " ON "
                + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_UID + " = "
                + SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_TRANSACTION_UID);
        queryBuilder.setDistinct(true);
        String[] projectionIn = new String[]{TransactionEntry.TABLE_NAME + ".*"};
        String selection = SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_ACCOUNT_UID + " = ?"
                + " AND " + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_TEMPLATE + " = 0";
        String[] selectionArgs = new String[]{accountUID};
        String sortOrder = TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_TIMESTAMP + " DESC";

        return queryBuilder.query(mDb, projectionIn, selection, selectionArgs, null, null, sortOrder);
    }

    /**
     * Deletes all transactions which contain a split in the account.
     * <p><b>Note:</b>As long as the transaction has one split which belongs to the account {@code accountUID},
     * it will be deleted. The other splits belonging to the transaction will also go away</p>
     * @param accountUID GUID of the account
     */
    public void deleteTransactionsForAccount(String accountUID){
        String rawDeleteQuery = "DELETE FROM " + TransactionEntry.TABLE_NAME + " WHERE " + TransactionEntry.COLUMN_UID + " IN "
                + " (SELECT " + SplitEntry.COLUMN_TRANSACTION_UID + " FROM " + SplitEntry.TABLE_NAME + " WHERE "
                + SplitEntry.COLUMN_ACCOUNT_UID + " = ?)";
        mDb.execSQL(rawDeleteQuery, new String[]{accountUID});
    }

    /**
     * Deletes all transactions which have no splits associated with them
     * @return Number of records deleted
     */
    public int deleteTransactionsWithNoSplits(){
        return mDb.delete(
                TransactionEntry.TABLE_NAME,
                "NOT EXISTS ( SELECT * FROM " + SplitEntry.TABLE_NAME +
                        " WHERE " + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_UID +
                        " = " + SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_TRANSACTION_UID + " ) ",
                null
        );
    }

    /**
     * Fetches all recurring transactions from the database.
     * <p>Recurring transactions are the transaction templates which have an entry in the scheduled events table</p>
     * @return Cursor holding set of all recurring transactions
     */
    public Cursor fetchAllScheduledTransactions(){
        SQLiteQueryBuilder queryBuilder = new SQLiteQueryBuilder();
        queryBuilder.setTables(TransactionEntry.TABLE_NAME + " INNER JOIN " + ScheduledActionEntry.TABLE_NAME + " ON "
                + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_UID + " = "
                + ScheduledActionEntry.TABLE_NAME + "." + ScheduledActionEntry.COLUMN_ACTION_UID);

        String[] projectionIn = new String[]{TransactionEntry.TABLE_NAME + ".*",
                ScheduledActionEntry.TABLE_NAME+"."+ScheduledActionEntry.COLUMN_UID + " AS " + "origin_scheduled_action_uid"};
        String sortOrder = TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_DESCRIPTION + " ASC";
//        queryBuilder.setDistinct(true);

        return queryBuilder.query(mDb, projectionIn, null, null, null, null, sortOrder);
    }

	/**
	 * Returns a cursor to a set of all transactions for the account with ID <code>accountID</code>
	 * or for which this account is the origin account in a double entry
	 * @param accountID ID of the account whose transactions are to be retrieved
	 * @return Cursor holding set of transactions for particular account
	 */
	public Cursor fetchAllTransactionsForAccount(long accountID){
        String accountUID = AccountsDbAdapter.getInstance().getUID(accountID);
		return fetchAllTransactionsForAccount(accountUID);
	}
	
	/**
	 * Returns list of all transactions for account with UID <code>accountUID</code>
	 * @param accountUID UID of account whose transactions are to be retrieved
	 * @return List of {@link Transaction}s for account with UID <code>accountUID</code>
	 */
    public List<Transaction> getAllTransactionsForAccount(String accountUID){
		Cursor c = fetchAllTransactionsForAccount(accountUID);
		ArrayList<Transaction> transactionsList = new ArrayList<>();
        try {
            while (c.moveToNext()) {
                transactionsList.add(buildTransactionInstance(c));
            }
        } finally {
            c.close();
        }
		return transactionsList;
	}

    /**
     * Returns all transaction instances in the database.
     * @return List of all transactions
     */
    public List<Transaction> getAllTransactions(){
        Cursor cursor = fetchAllRecords();
        List<Transaction> transactions = new ArrayList<Transaction>();
        try {
            while (cursor.moveToNext()) {
                transactions.add(buildTransactionInstance(cursor));
            }
        } finally {
            cursor.close();
        }
        return transactions;
    }

    public Cursor fetchTransactionsWithSplits(String [] columns, @Nullable String where, @Nullable String[] whereArgs, @Nullable String orderBy) {
        return mDb.query(TransactionEntry.TABLE_NAME + " , " + SplitEntry.TABLE_NAME +
                        " ON " + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_UID +
                        " = " + SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_TRANSACTION_UID +
                        " , trans_extra_info ON trans_extra_info.trans_acct_t_uid = " + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_UID ,
                columns, where, whereArgs, null, null,
                orderBy);
    }

    public Cursor fetchTransactionsWithSplitsWithTransactionAccount(String [] columns, String where, String[] whereArgs, String orderBy) {
        // table is :
        // trans_split_acct , trans_extra_info ON trans_extra_info.trans_acct_t_uid = transactions_uid ,
        // accounts AS account1 ON account1.uid = trans_extra_info.trans_acct_a_uid
        //
        // views effectively simplified this query
        //
        // account1 provides information for the grouped account. Splits from the grouped account
        // can be eliminated with a WHERE clause. Transactions in QIF can be auto balanced.
        //
        // Account, transaction and split Information can be retrieve in a single query.
        return mDb.query(
                "trans_split_acct , trans_extra_info ON trans_extra_info.trans_acct_t_uid = trans_split_acct." +
                TransactionEntry.TABLE_NAME + "_" + TransactionEntry.COLUMN_UID + " , " +
                AccountEntry.TABLE_NAME + " AS account1 ON account1." + AccountEntry.COLUMN_UID +
                " = trans_extra_info.trans_acct_a_uid",
                columns, where, whereArgs, null, null , orderBy);
    }

    /**
     * Return number of transactions in the database which are non recurring
     * @return Number of transactions
     */
    public int getTotalTransactionsCount() {
        String queryCount = "SELECT COUNT(*) FROM " + TransactionEntry.TABLE_NAME +
                " WHERE " + TransactionEntry.COLUMN_TEMPLATE + " =0";
        Cursor cursor = mDb.rawQuery(queryCount, null);
        try {
            cursor.moveToFirst();
            return cursor.getInt(0);
        } finally {
            cursor.close();
        }
    }

    public int getTotalTransactionsCount(@Nullable String where, @Nullable String[] whereArgs) {
        Cursor cursor = mDb.query(true, TransactionEntry.TABLE_NAME + " , trans_extra_info ON "
                        + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_UID
                        + " = trans_extra_info.trans_acct_t_uid",
                new String[]{"COUNT(*)"},
                where,
                whereArgs,
                null,
                null,
                null,
                null);
        try{
            cursor.moveToFirst();
            return cursor.getInt(0);
        } finally {
            cursor.close();
        }
    }

	/**
	 * Builds a transaction instance with the provided cursor.
	 * The cursor should already be pointing to the transaction record in the database
	 * @param c Cursor pointing to transaction record in database
	 * @return {@link Transaction} object constructed from database record
	 */
    public Transaction buildTransactionInstance(Cursor c){
		String name   = c.getString(c.getColumnIndexOrThrow(TransactionEntry.COLUMN_DESCRIPTION));
		Transaction transaction = new Transaction(name);
        populateModel(c, transaction);

		transaction.setTime(c.getLong(c.getColumnIndexOrThrow(TransactionEntry.COLUMN_TIMESTAMP)));
		transaction.setNote(c.getString(c.getColumnIndexOrThrow(TransactionEntry.COLUMN_NOTES)));
		transaction.setExported(c.getInt(c.getColumnIndexOrThrow(TransactionEntry.COLUMN_EXPORTED)) == 1);
		transaction.setTemplate(c.getInt(c.getColumnIndexOrThrow(TransactionEntry.COLUMN_TEMPLATE)) == 1);
        transaction.setCurrencyCode(c.getString(c.getColumnIndexOrThrow(TransactionEntry.COLUMN_CURRENCY)));
        transaction.setScheduledActionUID(c.getString(c.getColumnIndexOrThrow(TransactionEntry.COLUMN_SCHEDX_ACTION_UID)));
        long transactionID = c.getLong(c.getColumnIndexOrThrow(TransactionEntry._ID));
        transaction.setSplits(mSplitsDbAdapter.getSplitsForTransaction(transactionID));

		return transaction;
	}

	/**
	 * Returns the currency code (ISO 4217) used by the account with id <code>accountId</code>
	 * If you do not have the database record Id, you can call {@link #getID(String)}  instead.
	 * @param accountId Database record id of the account 
	 * @return Currency code of the account with Id <code>accountId</code>
	 * @see #getAccountCurrencyCode(String)
	 */
	public String getAccountCurrencyCode(long accountId){
		String accountUID = AccountsDbAdapter.getInstance().getUID(accountId);
		return getAccountCurrencyCode(accountUID);
	}

    /**
     * Returns the transaction balance for the transaction for the specified account.
     * <p>We consider only those splits which belong to this account</p>
     * @param transactionUID GUID of the transaction
     * @param accountUID GUID of the account
     * @return {@link org.gnucash.android.model.Money} balance of the transaction for that account
     */
    public Money getBalance(String transactionUID, String accountUID){
        List<Split> splitList = mSplitsDbAdapter.getSplitsForTransactionInAccount(
                transactionUID, accountUID);

        return Transaction.computeBalance(accountUID, splitList);
    }

    /**
	 * Assigns transaction with id <code>rowId</code> to account with id <code>accountId</code>
	 * @param transactionUID GUID of the transaction
     * @param srcAccountUID GUID of the account from which the transaction is to be moved
	 * @param dstAccountUID GUID of the account to which the transaction will be assigned
	 * @return Number of transactions splits affected
	 */
	public int moveTransaction(String transactionUID, String srcAccountUID, String dstAccountUID){
		Log.i(LOG_TAG, "Moving transaction ID " + transactionUID
                + " splits from " + srcAccountUID + " to account " + dstAccountUID);

		List<Split> splits = mSplitsDbAdapter.getSplitsForTransactionInAccount(transactionUID, srcAccountUID);
        for (Split split : splits) {
            split.setAccountUID(dstAccountUID);
        }
        mSplitsDbAdapter.bulkAddSplits(splits);
        return splits.size();
	}
	
	/**
	 * Returns the number of transactions belonging to account with id <code>accountId</code>
	 * @param accountId Long ID of account
	 * @return Number of transactions assigned to account with id <code>accountId</code>
	 */
	public int getTransactionsCount(long accountId){
		Cursor cursor = fetchAllTransactionsForAccount(accountId);
        try {
            return cursor.getCount();
        } finally {
            cursor.close();
		}
	}

    /**
     * Returns the number of transactions belonging to an account
     * @param accountUID GUID of the account
     * @return Number of transactions with splits in the account
     */
    public int getTransactionsCount(String accountUID){
        Cursor cursor = fetchAllTransactionsForAccount(accountUID);
        int count = 0;
        if (cursor == null)
            return count;
        else {
            count = cursor.getCount();
            cursor.close();
        }
        return count;
    }

    /**
	 * Returns the total number of transactions in the database
	 * regardless of what account they belong to
	 * @return Number of transaction in the database
	 */
	public long getAllTransactionsCount() {
        String sql = "SELECT COUNT(*) FROM " + TransactionEntry.TABLE_NAME;
        SQLiteStatement statement = mDb.compileStatement(sql);
        return statement.simpleQueryForLong();
    }

    /**
     * Returns the number of template transactions in the database
     * @return Number of template transactions
     */
    public long getTemplateTransactionsCount(){
        String sql = "SELECT COUNT(*) FROM " + TransactionEntry.TABLE_NAME
                + " WHERE " + TransactionEntry.COLUMN_TEMPLATE + "=1";
        SQLiteStatement statement = mDb.compileStatement(sql);
        return statement.simpleQueryForLong();
    }

    /**
     * Returns a cursor to transactions whose name (UI: description) start with the <code>prefix</code>
     * <p>This method is used for autocomplete suggestions when creating new transactions. <br/>
     * The suggestions are either transactions which have at least one split with {@code accountUID} or templates.</p>
     * @param prefix Starting characters of the transaction name
     * @param accountUID GUID of account within which to search for transactions
     * @return Cursor to the data set containing all matching transactions
     */
    public Cursor fetchTransactionSuggestions(String prefix, String accountUID){
        SQLiteQueryBuilder queryBuilder = new SQLiteQueryBuilder();
        queryBuilder.setTables(TransactionEntry.TABLE_NAME
                + " INNER JOIN " + SplitEntry.TABLE_NAME + " ON "
                + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_UID + " = "
                + SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_TRANSACTION_UID);
        queryBuilder.setDistinct(true);
        String[] projectionIn = new String[]{TransactionEntry.TABLE_NAME + ".*"};
        String selection = "(" + SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_ACCOUNT_UID + " = ?"
                + " OR " + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_TEMPLATE + "=1 )"
                + " AND " + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_DESCRIPTION + " LIKE '" + prefix + "%'";
        String[] selectionArgs = new String[]{accountUID};
        String sortOrder = TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_TIMESTAMP + " DESC";
        String groupBy = TransactionEntry.COLUMN_DESCRIPTION;
        String limit = Integer.toString(5);

        return queryBuilder.query(mDb, projectionIn, selection, selectionArgs, groupBy, null, sortOrder, limit);
    }

    /**
     * Updates a specific entry of an transaction
     * @param contentValues Values with which to update the record
     * @param whereClause Conditions for updating formatted as SQL where statement
     * @param whereArgs Arguments for the SQL wehere statement
     * @return Number of records affected
     */
    public int updateTransaction(ContentValues contentValues, String whereClause, String[] whereArgs){
        return mDb.update(TransactionEntry.TABLE_NAME, contentValues, whereClause, whereArgs);
    }

    /**
     * Returns a transaction for the given transaction GUID
     * @param transactionUID GUID of the transaction
     * @return Retrieves a transaction from the database
     */
    public Transaction getTransaction(String transactionUID) {
        return getTransaction(getID(transactionUID));
    }

    /**
     * Return the number of currencies used in the transaction.
     * For example if there are different splits with different currencies
     * @param transactionUID GUID of the transaction
     * @return Number of currencies within the transaction
     */
    public int getNumCurrencies(String transactionUID) {
        Cursor cursor = mDb.query("trans_extra_info",
                new String[]{"trans_currency_count"},
                "trans_acct_t_uid=?",
                new String[]{transactionUID},
                null, null, null);
        int numCurrencies = 0;
        try {
            if (cursor.moveToFirst()) {
                numCurrencies = cursor.getInt(0);
            }
        }
        finally {
            cursor.close();
        }
        return numCurrencies;
    }

    /**
     * Deletes all transactions except those which are marked as templates.
     * <p>If you want to delete really all transaction records, use {@link #deleteAllRecords()}</p>
     * @return Number of records deleted
     */
    public int deleteAllNonTemplateTransactions(){
        String where = TransactionEntry.COLUMN_TEMPLATE + "=0";
        return mDb.delete(mTableName, where, null);
    }

    /**
     * Returns a timestamp of the earliest transaction for a specified account type and currency
     * @param type the account type
     * @param currencyCode the currency code
     * @return the earliest transaction's timestamp. Returns 1970-01-01 00:00:00.000 if no transaction found
     */
    public long getTimestampOfEarliestTransaction(AccountType type, String currencyCode) {
        return getTimestamp("MIN", type, currencyCode);
    }

    /**
     * Returns a timestamp of the latest transaction for a specified account type and currency
     * @param type the account type
     * @param currencyCode the currency code
     * @return the latest transaction's timestamp. Returns 1970-01-01 00:00:00.000 if no transaction found
     */
    public long getTimestampOfLatestTransaction(AccountType type, String currencyCode) {
        return getTimestamp("MAX", type, currencyCode);
    }

    /**
     * Returns the earliest or latest timestamp of transactions for a specific account type and currency
     * @param mod Mode (either MAX or MIN)
     * @param type AccountType
     * @param currencyCode the currency code
     * @return earliest or latest timestamp of transactions
     * @see #getTimestampOfLatestTransaction(AccountType, String)
     * @see #getTimestampOfEarliestTransaction(AccountType, String)
     */
    private long getTimestamp(String mod, AccountType type, String currencyCode) {
        String sql = "SELECT " + mod + "(" + TransactionEntry.COLUMN_TIMESTAMP + ")"
                + " FROM " + TransactionEntry.TABLE_NAME
                + " INNER JOIN " + SplitEntry.TABLE_NAME + " ON "
                + SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_TRANSACTION_UID + " = "
                + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_UID
                + " INNER JOIN " + AccountEntry.TABLE_NAME + " ON "
                + AccountEntry.TABLE_NAME + "." + AccountEntry.COLUMN_UID + " = "
                + SplitEntry.TABLE_NAME + "." + SplitEntry.COLUMN_ACCOUNT_UID
                + " WHERE " + AccountEntry.TABLE_NAME + "." + AccountEntry.COLUMN_TYPE + " = ? AND "
                + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_CURRENCY + " = ? AND "
                + TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_TEMPLATE + " = 0";
        Cursor cursor = mDb.rawQuery(sql, new String[]{ type.name(), currencyCode });
        long timestamp= 0;
        if (cursor != null) {
            if (cursor.moveToFirst()) {
                timestamp = cursor.getLong(0);
            }
            cursor.close();
        }
        return timestamp;
    }

}


File: app/src/main/java/org/gnucash/android/export/xml/GncXmlExporter.java
/*
 * Copyright (c) 2014 - 2015 Ngewi Fet <ngewif@gmail.com>
 * Copyright (c) 2014 Yongxin Wang <fefe.wyx@gmail.com>
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

package org.gnucash.android.export.xml;

import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.util.Log;

import com.crashlytics.android.Crashlytics;

import org.gnucash.android.db.DatabaseSchema;
import org.gnucash.android.db.TransactionsDbAdapter;
import org.gnucash.android.export.ExportFormat;
import org.gnucash.android.export.ExportParams;
import org.gnucash.android.export.Exporter;
import org.gnucash.android.model.Account;
import org.gnucash.android.model.AccountType;
import org.gnucash.android.model.PeriodType;
import org.gnucash.android.model.ScheduledAction;
import org.gnucash.android.model.TransactionType;
import org.xmlpull.v1.XmlPullParserFactory;
import org.xmlpull.v1.XmlSerializer;

import java.io.BufferedOutputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.math.BigDecimal;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Currency;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.UUID;
import java.util.zip.GZIPOutputStream;

import static org.gnucash.android.db.DatabaseSchema.ScheduledActionEntry;
import static org.gnucash.android.db.DatabaseSchema.SplitEntry;
import static org.gnucash.android.db.DatabaseSchema.TransactionEntry;

/**
 * Creates a GnuCash XML representation of the accounts and transactions
 *
 * @author Ngewi Fet <ngewif@gmail.com>
 * @author Yongxin Wang <fefe.wyx@gmail.com>
 */
public class GncXmlExporter extends Exporter{

    /**
     * Root account for template accounts
     */
    private Account mRootTemplateAccount;
    private Map<String, Account> mTransactionToTemplateAccountMap = new TreeMap<>();

    /**
     * Construct a new exporter with export parameters
     * @param params Parameters for the export
     */
    public GncXmlExporter(ExportParams params) {
        super(params, null);
        LOG_TAG = "GncXmlExporter";
    }

    /**
     * Overloaded constructor.
     * Creates an exporter with an already open database instance.
     * @param params Parameters for the export
     * @param db SQLite database
     */
    public GncXmlExporter(ExportParams params, SQLiteDatabase db) {
        super(params, db);
        LOG_TAG = "GncXmlExporter";
    }

    private void exportSlots(XmlSerializer xmlSerializer,
                             List<String> slotKey,
                             List<String> slotType,
                             List<String> slotValue) throws IOException {
        if (slotKey == null || slotType == null || slotValue == null ||
                slotKey.size() == 0 || slotType.size() != slotKey.size() || slotValue.size() != slotKey.size()) {
            return;
        }

        for (int i = 0; i < slotKey.size(); i++) {
            xmlSerializer.startTag(null, GncXmlHelper.TAG_SLOT);
            xmlSerializer.startTag(null, GncXmlHelper.TAG_SLOT_KEY);
            xmlSerializer.text(slotKey.get(i));
            xmlSerializer.endTag(null, GncXmlHelper.TAG_SLOT_KEY);
            xmlSerializer.startTag(null, GncXmlHelper.TAG_SLOT_VALUE);
            xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_TYPE, slotType.get(i));
            xmlSerializer.text(slotValue.get(i));
            xmlSerializer.endTag(null, GncXmlHelper.TAG_SLOT_VALUE);
            xmlSerializer.endTag(null, GncXmlHelper.TAG_SLOT);
        }
    }

    private void exportAccounts(XmlSerializer xmlSerializer) throws IOException {
        Cursor cursor = mAccountsDbAdapter.fetchAccounts(null, null, DatabaseSchema.AccountEntry.COLUMN_FULL_NAME + " ASC");
        while (cursor.moveToNext()) {
            // write account
            xmlSerializer.startTag(null, GncXmlHelper.TAG_ACCOUNT);
            xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_VERSION, GncXmlHelper.BOOK_VERSION);
            // account name
            xmlSerializer.startTag(null, GncXmlHelper.TAG_NAME);
            xmlSerializer.text(cursor.getString(cursor.getColumnIndexOrThrow(DatabaseSchema.AccountEntry.COLUMN_NAME)));
            xmlSerializer.endTag(null, GncXmlHelper.TAG_NAME);
            // account guid
            xmlSerializer.startTag(null, GncXmlHelper.TAG_ACCT_ID);
            xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_TYPE, GncXmlHelper.ATTR_VALUE_GUID);
            xmlSerializer.text(cursor.getString(cursor.getColumnIndexOrThrow(DatabaseSchema.AccountEntry.COLUMN_UID)));
            xmlSerializer.endTag(null, GncXmlHelper.TAG_ACCT_ID);
            // account type
            xmlSerializer.startTag(null, GncXmlHelper.TAG_TYPE);
            String acct_type = cursor.getString(cursor.getColumnIndexOrThrow(DatabaseSchema.AccountEntry.COLUMN_TYPE));
            xmlSerializer.text(acct_type);
            xmlSerializer.endTag(null, GncXmlHelper.TAG_TYPE);
            // commodity
            xmlSerializer.startTag(null, GncXmlHelper.TAG_ACCOUNT_COMMODITY);
            xmlSerializer.startTag(null, GncXmlHelper.TAG_COMMODITY_SPACE);
            xmlSerializer.text("ISO4217");
            xmlSerializer.endTag(null, GncXmlHelper.TAG_COMMODITY_SPACE);
            xmlSerializer.startTag(null, GncXmlHelper.TAG_COMMODITY_ID);
            String acctCurrencyCode = cursor.getString(cursor.getColumnIndexOrThrow(DatabaseSchema.AccountEntry.COLUMN_CURRENCY));
            xmlSerializer.text(acctCurrencyCode);
            xmlSerializer.endTag(null, GncXmlHelper.TAG_COMMODITY_ID);
            xmlSerializer.endTag(null, GncXmlHelper.TAG_ACCOUNT_COMMODITY);
            // commodity scu
            xmlSerializer.startTag(null, GncXmlHelper.TAG_COMMODITY_SCU);
            xmlSerializer.text(Integer.toString((int) Math.pow(10, Currency.getInstance(acctCurrencyCode).getDefaultFractionDigits())));
            xmlSerializer.endTag(null, GncXmlHelper.TAG_COMMODITY_SCU);
            // account description
            // this is optional in Gnc XML, and currently not in the db, so description node
            // is omitted
            //
            // account slots, color, placeholder, default transfer account, favorite
            ArrayList<String> slotKey = new ArrayList<>();
            ArrayList<String> slotType = new ArrayList<>();
            ArrayList<String> slotValue = new ArrayList<>();
            slotKey.add(GncXmlHelper.KEY_PLACEHOLDER);
            slotType.add(GncXmlHelper.ATTR_VALUE_STRING);
            slotValue.add(Boolean.toString(cursor.getInt(cursor.getColumnIndexOrThrow(DatabaseSchema.AccountEntry.COLUMN_PLACEHOLDER)) != 0));

            String color = cursor.getString(cursor.getColumnIndexOrThrow(DatabaseSchema.AccountEntry.COLUMN_COLOR_CODE));
            if (color != null && color.length() > 0) {
                slotKey.add(GncXmlHelper.KEY_COLOR);
                slotType.add(GncXmlHelper.ATTR_VALUE_STRING);
                slotValue.add(color);
            }

            String defaultTransferAcctUID = cursor.getString(cursor.getColumnIndexOrThrow(DatabaseSchema.AccountEntry.COLUMN_DEFAULT_TRANSFER_ACCOUNT_UID));
            if (defaultTransferAcctUID != null && defaultTransferAcctUID.length() > 0) {
                slotKey.add(GncXmlHelper.KEY_DEFAULT_TRANSFER_ACCOUNT);
                slotType.add(GncXmlHelper.ATTR_VALUE_STRING);
                slotValue.add(defaultTransferAcctUID);
            }

            slotKey.add(GncXmlHelper.KEY_FAVORITE);
            slotType.add(GncXmlHelper.ATTR_VALUE_STRING);
            slotValue.add(Boolean.toString(cursor.getInt(cursor.getColumnIndexOrThrow(DatabaseSchema.AccountEntry.COLUMN_FAVORITE)) != 0));

            xmlSerializer.startTag(null, GncXmlHelper.TAG_ACT_SLOTS);
            exportSlots(xmlSerializer, slotKey, slotType, slotValue);
            xmlSerializer.endTag(null, GncXmlHelper.TAG_ACT_SLOTS);

            // parent uid
            String parentUID = cursor.getString(cursor.getColumnIndexOrThrow(DatabaseSchema.AccountEntry.COLUMN_PARENT_ACCOUNT_UID));
            if (!acct_type.equals("ROOT") && parentUID != null && parentUID.length() > 0) {
                xmlSerializer.startTag(null, GncXmlHelper.TAG_PARENT_UID);
                xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_TYPE, GncXmlHelper.ATTR_VALUE_GUID);
                xmlSerializer.text(parentUID);
                xmlSerializer.endTag(null, GncXmlHelper.TAG_PARENT_UID);
            } else {
                Log.d("export", "root account : " + cursor.getString(cursor.getColumnIndexOrThrow(DatabaseSchema.AccountEntry.COLUMN_UID)));
            }
            xmlSerializer.endTag(null, GncXmlHelper.TAG_ACCOUNT);
        }
        cursor.close();
    }

    /**
     * Exports template accounts
     * <p>Template accounts are just dummy accounts created for use with template transactions</p>
     * @param xmlSerializer XML serializer
     * @param accountList List of template accounts
     * @throws IOException if could not write XML to output stream
     */
    private void exportTemplateAccounts(XmlSerializer xmlSerializer, Collection<Account> accountList) throws IOException {
        for (Account account : accountList) {
            xmlSerializer.startTag(null, GncXmlHelper.TAG_ACCOUNT);
            xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_VERSION, GncXmlHelper.BOOK_VERSION);
            // account name
            xmlSerializer.startTag(null, GncXmlHelper.TAG_NAME);
            xmlSerializer.text(account.getName());
            xmlSerializer.endTag(null, GncXmlHelper.TAG_NAME);
            // account guid
            xmlSerializer.startTag(null, GncXmlHelper.TAG_ACCT_ID);
            xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_TYPE, GncXmlHelper.ATTR_VALUE_GUID);
            xmlSerializer.text(account.getUID());
            xmlSerializer.endTag(null, GncXmlHelper.TAG_ACCT_ID);
            // account type
            xmlSerializer.startTag(null, GncXmlHelper.TAG_TYPE);
            xmlSerializer.text(account.getAccountType().name());
            xmlSerializer.endTag(null, GncXmlHelper.TAG_TYPE);
            // commodity
            xmlSerializer.startTag(null, GncXmlHelper.TAG_ACCOUNT_COMMODITY);
            xmlSerializer.startTag(null, GncXmlHelper.TAG_COMMODITY_SPACE);
            xmlSerializer.text("template");
            xmlSerializer.endTag(null, GncXmlHelper.TAG_COMMODITY_SPACE);
            xmlSerializer.startTag(null, GncXmlHelper.TAG_COMMODITY_ID);
            String acctCurrencyCode = "template";
            xmlSerializer.text(acctCurrencyCode);
            xmlSerializer.endTag(null, GncXmlHelper.TAG_COMMODITY_ID);
            xmlSerializer.endTag(null, GncXmlHelper.TAG_ACCOUNT_COMMODITY);
            // commodity scu
            xmlSerializer.startTag(null, GncXmlHelper.TAG_COMMODITY_SCU);
            xmlSerializer.text("1");
            xmlSerializer.endTag(null, GncXmlHelper.TAG_COMMODITY_SCU);

            if (account.getAccountType() != AccountType.ROOT && mRootTemplateAccount != null) {
                xmlSerializer.startTag(null, GncXmlHelper.TAG_PARENT_UID);
                xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_TYPE, GncXmlHelper.ATTR_VALUE_GUID);
                xmlSerializer.text(mRootTemplateAccount.getUID());
                xmlSerializer.endTag(null, GncXmlHelper.TAG_PARENT_UID);
            }
            xmlSerializer.endTag(null, GncXmlHelper.TAG_ACCOUNT);
        }
    }

    /**
     * Serializes transactions from the database to XML
     * @param xmlSerializer XML serializer
     * @param exportTemplates Flag whether to export templates or normal transactions
     * @throws IOException if the XML serializer cannot be written to
     */
    private void exportTransactions(XmlSerializer xmlSerializer, boolean exportTemplates) throws IOException {
        String where = TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_TEMPLATE + "=0";
        if (exportTemplates) {
            where = TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_TEMPLATE + "=1";
        }
        Cursor cursor = mTransactionsDbAdapter.fetchTransactionsWithSplits(
                new String[]{
                        TransactionEntry.TABLE_NAME+"."+ TransactionEntry.COLUMN_UID + " AS trans_uid",
                        TransactionEntry.TABLE_NAME+"."+ TransactionEntry.COLUMN_DESCRIPTION + " AS trans_desc",
                        TransactionEntry.TABLE_NAME+"."+ TransactionEntry.COLUMN_NOTES + " AS trans_notes",
                        TransactionEntry.TABLE_NAME+"."+ TransactionEntry.COLUMN_TIMESTAMP + " AS trans_time",
                        TransactionEntry.TABLE_NAME+"."+ TransactionEntry.COLUMN_EXPORTED + " AS trans_exported",
                        TransactionEntry.TABLE_NAME+"."+ TransactionEntry.COLUMN_CURRENCY + " AS trans_currency",
                        TransactionEntry.TABLE_NAME+"."+ TransactionEntry.COLUMN_CREATED_AT + " AS trans_date_posted",
                        TransactionEntry.TABLE_NAME+"."+ TransactionEntry.COLUMN_SCHEDX_ACTION_UID + " AS trans_from_sched_action",
                        SplitEntry.TABLE_NAME+"."+ SplitEntry.COLUMN_UID + " AS split_uid",
                        SplitEntry.TABLE_NAME+"."+ SplitEntry.COLUMN_MEMO + " AS split_memo",
                        SplitEntry.TABLE_NAME+"."+ SplitEntry.COLUMN_TYPE + " AS split_type",
                        SplitEntry.TABLE_NAME+"."+ SplitEntry.COLUMN_AMOUNT + " AS split_amount",
                        SplitEntry.TABLE_NAME+"."+ SplitEntry.COLUMN_ACCOUNT_UID + " AS split_acct_uid"},
                        where, null,
                        TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_TIMESTAMP + " ASC , " +
                        TransactionEntry.TABLE_NAME + "." + TransactionEntry.COLUMN_UID + " ASC ");
        String lastTrxUID = "";
        Currency trxCurrency = null;
        String denomString = "100";

        if (exportTemplates) {
            mRootTemplateAccount = new Account("Template Root");
            mRootTemplateAccount.setAccountType(AccountType.ROOT);
            mTransactionToTemplateAccountMap.put(" ", mRootTemplateAccount);
            while (cursor.moveToNext()) {
                Account account = new Account(UUID.randomUUID().toString().replaceAll("-", ""));
                account.setAccountType(AccountType.BANK);
                String trnUID = cursor.getString(cursor.getColumnIndexOrThrow("trans_uid"));
                mTransactionToTemplateAccountMap.put(trnUID, account);
            }

            exportTemplateAccounts(xmlSerializer, mTransactionToTemplateAccountMap.values());
            //push cursor back to before the beginning
            cursor.moveToFirst();
            cursor.moveToPrevious();
        }

        while (cursor.moveToNext()){
            String curTrxUID = cursor.getString(cursor.getColumnIndexOrThrow("trans_uid"));
            if (!lastTrxUID.equals(curTrxUID)) { // new transaction starts
                if (!lastTrxUID.equals("")) { // there's an old transaction, close it
                    xmlSerializer.endTag(null, GncXmlHelper.TAG_TRN_SPLITS);
                    xmlSerializer.endTag(null, GncXmlHelper.TAG_TRANSACTION);
                }
                // new transaction
                xmlSerializer.startTag(null, GncXmlHelper.TAG_TRANSACTION);
                xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_VERSION, GncXmlHelper.BOOK_VERSION);
                // transaction id
                xmlSerializer.startTag(null, GncXmlHelper.TAG_TRX_ID);
                xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_TYPE, GncXmlHelper.ATTR_VALUE_GUID);
                xmlSerializer.text(curTrxUID);
                xmlSerializer.endTag(null, GncXmlHelper.TAG_TRX_ID);
                // currency
                String currency = cursor.getString(cursor.getColumnIndexOrThrow("trans_currency"));
                trxCurrency = Currency.getInstance(currency);
                xmlSerializer.startTag(null, GncXmlHelper.TAG_TRX_CURRENCY);
                xmlSerializer.startTag(null, GncXmlHelper.TAG_COMMODITY_SPACE);
                xmlSerializer.text("ISO4217");
                xmlSerializer.endTag(null, GncXmlHelper.TAG_COMMODITY_SPACE);
                xmlSerializer.startTag(null, GncXmlHelper.TAG_COMMODITY_ID);
                xmlSerializer.text(currency);
                xmlSerializer.endTag(null, GncXmlHelper.TAG_COMMODITY_ID);
                xmlSerializer.endTag(null, GncXmlHelper.TAG_TRX_CURRENCY);
                // date posted, time which user put on the transaction
                String strDate = GncXmlHelper.formatDate(cursor.getLong(cursor.getColumnIndexOrThrow("trans_time")));
                xmlSerializer.startTag(null, GncXmlHelper.TAG_DATE_POSTED);
                xmlSerializer.startTag(null, GncXmlHelper.TAG_TS_DATE);
                xmlSerializer.text(strDate);
                xmlSerializer.endTag(null, GncXmlHelper.TAG_TS_DATE);
                xmlSerializer.endTag(null, GncXmlHelper.TAG_DATE_POSTED);

                // date entered, time when the transaction was actually created
                Timestamp timeEntered = Timestamp.valueOf(cursor.getString(cursor.getColumnIndexOrThrow("trans_date_posted")));
                String dateEntered = GncXmlHelper.formatDate(timeEntered.getTime());
                xmlSerializer.startTag(null, GncXmlHelper.TAG_DATE_ENTERED);
                xmlSerializer.startTag(null, GncXmlHelper.TAG_TS_DATE);
                xmlSerializer.text(dateEntered);
                xmlSerializer.endTag(null, GncXmlHelper.TAG_TS_DATE);
                xmlSerializer.endTag(null, GncXmlHelper.TAG_DATE_ENTERED);

                // description
                xmlSerializer.startTag(null, GncXmlHelper.TAG_TRN_DESCRIPTION);
                xmlSerializer.text(cursor.getString(cursor.getColumnIndexOrThrow("trans_desc")));
                xmlSerializer.endTag(null, GncXmlHelper.TAG_TRN_DESCRIPTION);
                lastTrxUID = curTrxUID;
                // slots
                ArrayList<String> slotKey = new ArrayList<>();
                ArrayList<String> slotType = new ArrayList<>();
                ArrayList<String> slotValue = new ArrayList<>();

                String notes = cursor.getString(cursor.getColumnIndexOrThrow("trans_notes"));
                boolean exported = cursor.getInt(cursor.getColumnIndexOrThrow("trans_exported")) == 1;
                if (notes != null && notes.length() > 0) {
                    slotKey.add(GncXmlHelper.KEY_NOTES);
                    slotType.add(GncXmlHelper.ATTR_VALUE_STRING);
                    slotValue.add(notes);
                }
                if (!exported) {
                    slotKey.add(GncXmlHelper.KEY_EXPORTED);
                    slotType.add(GncXmlHelper.ATTR_VALUE_STRING);
                    slotValue.add("false");
                }

                String scheduledActionUID = cursor.getString(cursor.getColumnIndexOrThrow("trans_from_sched_action"));
                if (scheduledActionUID != null && !scheduledActionUID.isEmpty()){
                    slotKey.add(GncXmlHelper.KEY_FROM_SCHED_ACTION);
                    slotType.add(GncXmlHelper.ATTR_VALUE_GUID);
                    slotValue.add(scheduledActionUID);
                }
                xmlSerializer.startTag(null, GncXmlHelper.TAG_TRN_SLOTS);
                exportSlots(xmlSerializer, slotKey, slotType, slotValue);
                xmlSerializer.endTag(null, GncXmlHelper.TAG_TRN_SLOTS);

                // splits start
                xmlSerializer.startTag(null, GncXmlHelper.TAG_TRN_SPLITS);
            }
            xmlSerializer.startTag(null, GncXmlHelper.TAG_TRN_SPLIT);
            // split id
            xmlSerializer.startTag(null, GncXmlHelper.TAG_SPLIT_ID);
            xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_TYPE, GncXmlHelper.ATTR_VALUE_GUID);
            xmlSerializer.text(cursor.getString(cursor.getColumnIndexOrThrow("split_uid")));
            xmlSerializer.endTag(null, GncXmlHelper.TAG_SPLIT_ID);
            // memo
            String memo = cursor.getString(cursor.getColumnIndexOrThrow("split_memo"));
            if (memo != null && memo.length() > 0){
                xmlSerializer.startTag(null, GncXmlHelper.TAG_SPLIT_MEMO);
                xmlSerializer.text(memo);
                xmlSerializer.endTag(null, GncXmlHelper.TAG_SPLIT_MEMO);
            }
            // reconciled
            xmlSerializer.startTag(null, GncXmlHelper.TAG_RECONCILED_STATE);
            xmlSerializer.text("n");
            xmlSerializer.endTag(null, GncXmlHelper.TAG_RECONCILED_STATE);
            // value, in the transaction's currency
            String trxType = cursor.getString(cursor.getColumnIndexOrThrow("split_type"));
            BigDecimal splitAmount = new BigDecimal(cursor.getString(cursor.getColumnIndexOrThrow("split_amount")));
            String strValue = "0/" + denomString;
            if (!exportTemplates) { //when doing normal transaction export
                strValue = (trxType.equals("CREDIT") ? "-" : "") + GncXmlHelper.formatSplitAmount(splitAmount, trxCurrency);
            }
            xmlSerializer.startTag(null, GncXmlHelper.TAG_SPLIT_VALUE);
            xmlSerializer.text(strValue);
            xmlSerializer.endTag(null, GncXmlHelper.TAG_SPLIT_VALUE);
            // quantity, in the split account's currency
            // TODO: multi currency support.
            xmlSerializer.startTag(null, GncXmlHelper.TAG_SPLIT_QUANTITY);
            xmlSerializer.text(strValue);
            xmlSerializer.endTag(null, GncXmlHelper.TAG_SPLIT_QUANTITY);
            // account guid
            xmlSerializer.startTag(null, GncXmlHelper.TAG_SPLIT_ACCOUNT);
            xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_TYPE, GncXmlHelper.ATTR_VALUE_GUID);
            String splitAccountUID = null;
            if (exportTemplates){
                //get the UID of the template account
                 splitAccountUID = mTransactionToTemplateAccountMap.get(curTrxUID).getUID();
            } else {
                splitAccountUID = cursor.getString(cursor.getColumnIndexOrThrow("split_acct_uid"));
            }
            xmlSerializer.text(splitAccountUID);
            xmlSerializer.endTag(null, GncXmlHelper.TAG_SPLIT_ACCOUNT);

            //if we are exporting a template transaction, then we need to add some extra slots
            if (exportTemplates){
                xmlSerializer.startTag(null, GncXmlHelper.TAG_SPLIT_SLOTS);
                xmlSerializer.startTag(null, GncXmlHelper.TAG_SLOT);
                xmlSerializer.startTag(null, GncXmlHelper.TAG_SLOT_KEY);
                xmlSerializer.text(GncXmlHelper.KEY_SCHEDX_ACTION); //FIXME: not all templates may be scheduled actions
                xmlSerializer.endTag(null, GncXmlHelper.TAG_SLOT_KEY);
                xmlSerializer.startTag(null, GncXmlHelper.TAG_SLOT_VALUE);
                xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_TYPE, "frame");

                List<String> slotKeys = new ArrayList<>();
                List<String> slotTypes = new ArrayList<>();
                List<String> slotValues = new ArrayList<>();
                slotKeys.add(GncXmlHelper.KEY_SPLIT_ACCOUNT_SLOT);
                slotTypes.add(GncXmlHelper.ATTR_VALUE_GUID);
                slotValues.add(cursor.getString(cursor.getColumnIndexOrThrow("split_acct_uid")));
                TransactionType type = TransactionType.valueOf(trxType);
                if (type == TransactionType.CREDIT){
                    slotKeys.add(GncXmlHelper.KEY_CREDIT_FORMULA);
                    slotTypes.add(GncXmlHelper.ATTR_VALUE_STRING);
                    slotValues.add(GncXmlHelper.formatTemplateSplitAmount(splitAmount));
                    slotKeys.add(GncXmlHelper.KEY_CREDIT_NUMERIC);
                    slotTypes.add(GncXmlHelper.ATTR_VALUE_NUMERIC);
                    slotValues.add(GncXmlHelper.formatSplitAmount(splitAmount, trxCurrency));
                } else {
                    slotKeys.add(GncXmlHelper.KEY_DEBIT_FORMULA);
                    slotTypes.add(GncXmlHelper.ATTR_VALUE_STRING);
                    slotValues.add(GncXmlHelper.formatTemplateSplitAmount(splitAmount));
                    slotKeys.add(GncXmlHelper.KEY_DEBIT_NUMERIC);
                    slotTypes.add(GncXmlHelper.ATTR_VALUE_NUMERIC);
                    slotValues.add(GncXmlHelper.formatSplitAmount(splitAmount, trxCurrency));
                }

                exportSlots(xmlSerializer, slotKeys, slotTypes, slotValues);

                xmlSerializer.endTag(null, GncXmlHelper.TAG_SLOT_VALUE);
                xmlSerializer.endTag(null, GncXmlHelper.TAG_SLOT);
                xmlSerializer.endTag(null, GncXmlHelper.TAG_SPLIT_SLOTS);
            }

            xmlSerializer.endTag(null, GncXmlHelper.TAG_TRN_SPLIT);
        }
        if (!lastTrxUID.equals("")){ // there's an unfinished transaction, close it
            xmlSerializer.endTag(null,GncXmlHelper.TAG_TRN_SPLITS);
            xmlSerializer.endTag(null, GncXmlHelper.TAG_TRANSACTION);
        }
        cursor.close();
    }

    /**
     * Serializes {@link ScheduledAction}s from the database to XML
     * @param xmlSerializer XML serializer
     * @throws IOException
     */
    private void exportScheduledTransactions(XmlSerializer xmlSerializer) throws IOException{
        //for now we will export only scheduled transactions to XML
        Cursor cursor = mScheduledActionDbAdapter.fetchAllRecords(
                ScheduledActionEntry.COLUMN_TYPE + "=?", new String[]{ScheduledAction.ActionType.TRANSACTION.name()});

        while (cursor.moveToNext()) {
            String actionUID = cursor.getString(cursor.getColumnIndexOrThrow(ScheduledActionEntry.COLUMN_ACTION_UID));
            Account accountUID = mTransactionToTemplateAccountMap.get(actionUID);

            xmlSerializer.startTag(null, GncXmlHelper.TAG_SCHEDULED_ACTION);
            xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_VERSION, GncXmlHelper.BOOK_VERSION);
            xmlSerializer.startTag(null, GncXmlHelper.TAG_SX_ID);

            String nameUID = accountUID.getName();
            xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_TYPE, GncXmlHelper.ATTR_VALUE_GUID);
            xmlSerializer.text(nameUID);
            xmlSerializer.endTag(null, GncXmlHelper.TAG_SX_ID);
            xmlSerializer.startTag(null, GncXmlHelper.TAG_SX_NAME);

            ScheduledAction.ActionType actionType = ScheduledAction.ActionType.valueOf(cursor.getString(cursor.getColumnIndexOrThrow(ScheduledActionEntry.COLUMN_TYPE)));
            if (actionType == ScheduledAction.ActionType.TRANSACTION) {
                String description = TransactionsDbAdapter.getInstance().getAttribute(actionUID, TransactionEntry.COLUMN_DESCRIPTION);
                xmlSerializer.text(description);
            } else {
                xmlSerializer.text(actionType.name());
            }
            xmlSerializer.endTag(null, GncXmlHelper.TAG_SX_NAME);
            xmlSerializer.startTag(null, GncXmlHelper.TAG_SX_ENABLED);
            boolean enabled = cursor.getShort(cursor.getColumnIndexOrThrow(ScheduledActionEntry.COLUMN_ENABLED)) > 0;
            xmlSerializer.text(enabled ? "y" : "n");
            xmlSerializer.endTag(null, GncXmlHelper.TAG_SX_ENABLED);
            xmlSerializer.startTag(null, GncXmlHelper.TAG_SX_AUTO_CREATE);
            xmlSerializer.text("n"); //we do not want transactions auto-created on the desktop.
            xmlSerializer.endTag(null, GncXmlHelper.TAG_SX_AUTO_CREATE);
            xmlSerializer.startTag(null, GncXmlHelper.TAG_SX_AUTO_CREATE_NOTIFY);
            xmlSerializer.text("n"); //TODO: if we ever support notifying before creating a scheduled transaction, then update this
            xmlSerializer.endTag(null, GncXmlHelper.TAG_SX_AUTO_CREATE_NOTIFY);
            xmlSerializer.startTag(null, GncXmlHelper.TAG_SX_ADVANCE_CREATE_DAYS);
            xmlSerializer.text("0");
            xmlSerializer.endTag(null, GncXmlHelper.TAG_SX_ADVANCE_CREATE_DAYS);
            xmlSerializer.startTag(null, GncXmlHelper.TAG_SX_ADVANCE_REMIND_DAYS);
            xmlSerializer.text("0");
            xmlSerializer.endTag(null, GncXmlHelper.TAG_SX_ADVANCE_REMIND_DAYS);
            xmlSerializer.startTag(null, GncXmlHelper.TAG_SX_INSTANCE_COUNT);
            String scheduledActionUID = cursor.getString(cursor.getColumnIndexOrThrow(ScheduledActionEntry.COLUMN_UID));
            long instanceCount = mScheduledActionDbAdapter.getActionInstanceCount(scheduledActionUID);
            xmlSerializer.text(Long.toString(instanceCount));
            xmlSerializer.endTag(null, GncXmlHelper.TAG_SX_INSTANCE_COUNT);

            //start date
            String createdTimestamp = cursor.getString(cursor.getColumnIndexOrThrow(ScheduledActionEntry.COLUMN_CREATED_AT));
            long scheduleStartTime = Timestamp.valueOf(createdTimestamp).getTime();
            serializeDate(xmlSerializer, GncXmlHelper.TAG_SX_START, scheduleStartTime);

            long lastRunTime = cursor.getLong(cursor.getColumnIndexOrThrow(ScheduledActionEntry.COLUMN_LAST_RUN));
            if (lastRunTime > 0){
                serializeDate(xmlSerializer, GncXmlHelper.TAG_SX_LAST, lastRunTime);
            }

            long endTime = cursor.getLong(cursor.getColumnIndexOrThrow(ScheduledActionEntry.COLUMN_END_TIME));
            if (endTime > 0) {
                //end date
                serializeDate(xmlSerializer, GncXmlHelper.TAG_SX_END, endTime);
            } else { //add number of occurrences
                int totalFrequency = cursor.getInt(cursor.getColumnIndexOrThrow(ScheduledActionEntry.COLUMN_TOTAL_FREQUENCY));
                xmlSerializer.startTag(null, GncXmlHelper.TAG_SX_NUM_OCCUR);
                xmlSerializer.text(Integer.toString(totalFrequency));
                xmlSerializer.endTag(null, GncXmlHelper.TAG_SX_NUM_OCCUR);

                //remaining occurrences
                int executionCount = cursor.getInt(cursor.getColumnIndexOrThrow(ScheduledActionEntry.COLUMN_EXECUTION_COUNT));
                xmlSerializer.startTag(null, GncXmlHelper.TAG_SX_REM_OCCUR);
                xmlSerializer.text(Integer.toString(totalFrequency - executionCount));
                xmlSerializer.endTag(null, GncXmlHelper.TAG_SX_REM_OCCUR);
            }

            String tag = cursor.getString(cursor.getColumnIndexOrThrow(ScheduledActionEntry.COLUMN_TAG));
            if (tag != null && !tag.isEmpty()){
                xmlSerializer.startTag(null, GncXmlHelper.TAG_SX_TAG);
                xmlSerializer.text(tag);
                xmlSerializer.endTag(null, GncXmlHelper.TAG_SX_TAG);
            }

            xmlSerializer.startTag(null, GncXmlHelper.TAG_SX_TEMPL_ACCOUNT);
            xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_TYPE, GncXmlHelper.ATTR_VALUE_GUID);
            xmlSerializer.text(accountUID.getUID());
            xmlSerializer.endTag(null, GncXmlHelper.TAG_SX_TEMPL_ACCOUNT);

            xmlSerializer.startTag(null, GncXmlHelper.TAG_SX_SCHEDULE);
            xmlSerializer.startTag(null, GncXmlHelper.TAG_RECURRENCE);
            xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_VERSION, GncXmlHelper.RECURRENCE_VERSION);
            long period = cursor.getLong(cursor.getColumnIndexOrThrow(ScheduledActionEntry.COLUMN_PERIOD));
            PeriodType periodType = ScheduledAction.getPeriodType(period);
            xmlSerializer.startTag(null, GncXmlHelper.TAG_RX_MULT);
            xmlSerializer.text(String.valueOf(periodType.getMultiplier()));
            xmlSerializer.endTag(null, GncXmlHelper.TAG_RX_MULT);
            xmlSerializer.startTag(null, GncXmlHelper.TAG_RX_PERIOD_TYPE);
            xmlSerializer.text(periodType.name().toLowerCase());
            xmlSerializer.endTag(null, GncXmlHelper.TAG_RX_PERIOD_TYPE);

            long recurrenceStartTime = cursor.getLong(cursor.getColumnIndexOrThrow(ScheduledActionEntry.COLUMN_START_TIME));
            serializeDate(xmlSerializer, GncXmlHelper.TAG_RX_START, recurrenceStartTime);

            xmlSerializer.endTag(null, GncXmlHelper.TAG_RECURRENCE);
            xmlSerializer.endTag(null, GncXmlHelper.TAG_SX_SCHEDULE);

            xmlSerializer.endTag(null, GncXmlHelper.TAG_SCHEDULED_ACTION);
        }
    }

    /**
     * Serializes a date as a {@code tag} which has a nested {@link GncXmlHelper#TAG_GDATE} which
     * has the date as a text element formatted using {@link GncXmlHelper#DATE_FORMATTER}
     * @param xmlSerializer XML serializer
     * @param tag Enclosing tag
     * @param timeMillis Date to be formatted and output
     * @throws IOException
     */
    private void serializeDate(XmlSerializer xmlSerializer, String tag, long timeMillis) throws IOException {
        xmlSerializer.startTag(null, tag);
        xmlSerializer.startTag(null, GncXmlHelper.TAG_GDATE);
        xmlSerializer.text(GncXmlHelper.DATE_FORMATTER.format(timeMillis));
        xmlSerializer.endTag(null, GncXmlHelper.TAG_GDATE);
        xmlSerializer.endTag(null, tag);
    }

    private void exportCommodity(XmlSerializer xmlSerializer, List<Currency> currencies) throws IOException {
        for (Currency currency : currencies) {
            xmlSerializer.startTag(null, GncXmlHelper.TAG_COMMODITY);
            xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_VERSION, "2.0.0");
            xmlSerializer.startTag(null, GncXmlHelper.TAG_COMMODITY_SPACE);
            xmlSerializer.text("ISO4217");
            xmlSerializer.endTag(null, GncXmlHelper.TAG_COMMODITY_SPACE);
            xmlSerializer.startTag(null, GncXmlHelper.TAG_COMMODITY_ID);
            xmlSerializer.text(currency.getCurrencyCode());
            xmlSerializer.endTag(null, GncXmlHelper.TAG_COMMODITY_ID);
            xmlSerializer.endTag(null, GncXmlHelper.TAG_COMMODITY);
        }
    }

    @Override
    public void generateExport(Writer writer) throws ExporterException{
        try {
            String[] namespaces = new String[] {"gnc", "act", "book", "cd", "cmdty", "price", "slot",
                    "split", "trn", "ts", "sx", "recurrence"};
            XmlSerializer xmlSerializer = XmlPullParserFactory.newInstance().newSerializer();
            xmlSerializer.setOutput(writer);
            xmlSerializer.startDocument("utf-8", true);
            // root tag
            xmlSerializer.startTag(null, GncXmlHelper.TAG_ROOT);
            for(String ns : namespaces) {
                xmlSerializer.attribute(null, "xmlns:" + ns, "http://www.gnucash.org/XML/" + ns);
            }
            // book count
            xmlSerializer.startTag(null, GncXmlHelper.TAG_COUNT_DATA);
            xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_CD_TYPE, GncXmlHelper.ATTR_VALUE_BOOK);
            xmlSerializer.text("1");
            xmlSerializer.endTag(null, GncXmlHelper.TAG_COUNT_DATA);
            // book
            xmlSerializer.startTag(null, GncXmlHelper.TAG_BOOK);
            xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_VERSION, GncXmlHelper.BOOK_VERSION);
            // book_id
            xmlSerializer.startTag(null, GncXmlHelper.TAG_BOOK_ID);
            xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_TYPE, GncXmlHelper.ATTR_VALUE_GUID);
            xmlSerializer.text(UUID.randomUUID().toString().replaceAll("-", ""));
            xmlSerializer.endTag(null, GncXmlHelper.TAG_BOOK_ID);
            //commodity count
            List<Currency> currencies = mAccountsDbAdapter.getCurrencies();
            for (int i = 0; i< currencies.size();i++) {
                if (currencies.get(i).getCurrencyCode().equals("XXX")) {
                    currencies.remove(i);
                }
            }
            xmlSerializer.startTag(null, GncXmlHelper.TAG_COUNT_DATA);
            xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_CD_TYPE, "commodity");
            xmlSerializer.text(currencies.size() + "");
            xmlSerializer.endTag(null, GncXmlHelper.TAG_COUNT_DATA);
            //account count
            xmlSerializer.startTag(null, GncXmlHelper.TAG_COUNT_DATA);
            xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_CD_TYPE, "account");
            xmlSerializer.text(mAccountsDbAdapter.getTotalAccountCount() + "");
            xmlSerializer.endTag(null, GncXmlHelper.TAG_COUNT_DATA);
            //transaction count
            xmlSerializer.startTag(null, GncXmlHelper.TAG_COUNT_DATA);
            xmlSerializer.attribute(null, GncXmlHelper.ATTR_KEY_CD_TYPE, "transaction");
            xmlSerializer.text(mTransactionsDbAdapter.getTotalTransactionsCount() + "");
            xmlSerializer.endTag(null, GncXmlHelper.TAG_COUNT_DATA);
            // export the commodities used in the DB
            exportCommodity(xmlSerializer, currencies);
            // accounts. bulk import does not rely on account order
            // the cursor gather account in arbitrary order
            exportAccounts(xmlSerializer);
            // transactions.
            exportTransactions(xmlSerializer, false);

            //transaction templates
            if (mTransactionsDbAdapter.getTemplateTransactionsCount() > 0) {
                xmlSerializer.startTag(null, GncXmlHelper.TAG_TEMPLATE_TRANSACTIONS);
                exportTransactions(xmlSerializer, true);
                xmlSerializer.endTag(null, GncXmlHelper.TAG_TEMPLATE_TRANSACTIONS);
            }
            //scheduled actions
            exportScheduledTransactions(xmlSerializer);

            xmlSerializer.endTag(null, GncXmlHelper.TAG_BOOK);
            xmlSerializer.endTag(null, GncXmlHelper.TAG_ROOT);
            xmlSerializer.endDocument();
        } catch (Exception e) {
            Crashlytics.logException(e);
            throw new ExporterException(mParameters, e);
        }
    }
    /**
     * Creates a backup of current database contents to the default backup location
     * @return {@code true} if backup was successful, {@code false} otherwise
     */
    public static boolean createBackup(){
        ExportParams params = new ExportParams(ExportFormat.XML);
        try {
            FileOutputStream fileOutputStream = new FileOutputStream(Exporter.buildBackupFile());
            BufferedOutputStream bufferedOutputStream = new BufferedOutputStream(fileOutputStream);
            GZIPOutputStream gzipOutputStream = new GZIPOutputStream(bufferedOutputStream);
            OutputStreamWriter outputStreamWriter = new OutputStreamWriter(gzipOutputStream);
            new GncXmlExporter(params).generateExport(outputStreamWriter);
            outputStreamWriter.close();
            return true;
        } catch (IOException e) {
            Crashlytics.logException(e);
            Log.e("GncXmlExporter", "Error creating backup", e);
            return false;
        }
    }
}


File: app/src/test/java/org/gnucash/android/test/unit/db/AccountsDbAdapterTest.java
package org.gnucash.android.test.unit.db;

import org.assertj.core.data.Index;
import org.gnucash.android.BuildConfig;
import org.gnucash.android.db.AccountsDbAdapter;
import org.gnucash.android.db.SplitsDbAdapter;
import org.gnucash.android.db.TransactionsDbAdapter;
import org.gnucash.android.model.Account;
import org.gnucash.android.model.AccountType;
import org.gnucash.android.model.Money;
import org.gnucash.android.model.Split;
import org.gnucash.android.model.Transaction;
import org.gnucash.android.test.unit.util.GnucashTestRunner;
import org.gnucash.android.test.unit.util.ShadowCrashlytics;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.annotation.Config;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

@RunWith(GnucashTestRunner.class)
@Config(constants = BuildConfig.class, shadows = {ShadowCrashlytics.class})
public class AccountsDbAdapterTest{

	private static final String BRAVO_ACCOUNT_NAME = "Bravo";
	private static final String ALPHA_ACCOUNT_NAME = "Alpha";
    private AccountsDbAdapter mAccountsDbAdapter;
    private TransactionsDbAdapter mTransactionsDbAdapter;
    private SplitsDbAdapter mSplitsDbAdapter;

	@Before
	public void setUp() throws Exception {

        mSplitsDbAdapter = SplitsDbAdapter.getInstance();
        mTransactionsDbAdapter = TransactionsDbAdapter.getInstance();
        mAccountsDbAdapter = AccountsDbAdapter.getInstance();
	}

    /**
     * Test that the list of accounts is always returned sorted alphabetically
     */
    @Test
	public void testAlphabeticalSorting(){
        Account first = new Account(ALPHA_ACCOUNT_NAME);
        Account second = new Account(BRAVO_ACCOUNT_NAME);
        //purposefully added the second after the first
        mAccountsDbAdapter.addAccount(second);
        mAccountsDbAdapter.addAccount(first);

		List<Account> accountsList = mAccountsDbAdapter.getAllAccounts();
		assertEquals(2, accountsList.size());
		//bravo was saved first, but alpha should be first alphabetically
        assertThat(accountsList).contains(first, Index.atIndex(0));
        assertThat(accountsList).contains(second, Index.atIndex(1));
	}

    @Test
    public void testAddAccountWithTransaction(){
        Account account1 = new Account("AlphaAccount");
        Account account2 = new Account("BetaAccount");
        Transaction transaction = new Transaction("MyTransaction");
        Split split = new Split(Money.getZeroInstance(), account1.getUID());
        transaction.addSplit(split);
        transaction.addSplit(split.createPair(account2.getUID()));

        long id1 = mAccountsDbAdapter.addAccount(account1);
        long id2 = mAccountsDbAdapter.addAccount(account2);

        assertTrue(id1 > 0);
        assertTrue(id2 > 0);
    }

    /**
     * Tests the foreign key constraint "ON DELETE CASCADE" between accounts and splits
     */
    @Test
    public void testDeletingAccountShouldDeleteSplits(){
        Account first = new Account(ALPHA_ACCOUNT_NAME);
        first.setUID(ALPHA_ACCOUNT_NAME);
        Account second = new Account(BRAVO_ACCOUNT_NAME);
        second.setUID(BRAVO_ACCOUNT_NAME);

        mAccountsDbAdapter.addAccount(second);
        mAccountsDbAdapter.addAccount(first);

        Transaction transaction = new Transaction("TestTrn");
        Split split = new Split(Money.getZeroInstance(), ALPHA_ACCOUNT_NAME);
        transaction.addSplit(split);
        transaction.addSplit(split.createPair(BRAVO_ACCOUNT_NAME));

        long id = mTransactionsDbAdapter.addTransaction(transaction);
        assertTrue(id > 0);

        mAccountsDbAdapter.deleteRecord(ALPHA_ACCOUNT_NAME);

        Transaction trxn = mTransactionsDbAdapter.getTransaction(transaction.getUID());
        assertEquals(1, trxn.getSplits().size());
        assertEquals(BRAVO_ACCOUNT_NAME, trxn.getSplits().get(0).getAccountUID());
    }

    /**
     * Tests that a ROOT account will always be created in the system
     */
    @Test
    public void shouldCreateDefaultRootAccount(){
        Account account = new Account("Some account");
        mAccountsDbAdapter.addAccount(account);
        assertThat(2).isEqualTo(mAccountsDbAdapter.getTotalAccountCount());

        List<Account> accounts = mAccountsDbAdapter.getSimpleAccountList();
        assertThat(accounts).extracting("mAccountType").contains(AccountType.ROOT);

        String rootAccountUID = mAccountsDbAdapter.getOrCreateGnuCashRootAccountUID();
        assertThat(rootAccountUID).isEqualTo(accounts.get(1).getParentUID());
    }

    @Test
    public void shouldUpdateFullNameAfterParentChange(){
        Account parent = new Account("Test");
        Account child = new Account("Child");

        mAccountsDbAdapter.addAccount(parent);
        mAccountsDbAdapter.addAccount(child);

        child.setParentUID(parent.getUID());
        mAccountsDbAdapter.addAccount(child);

        child = mAccountsDbAdapter.getAccount(child.getUID());
        parent = mAccountsDbAdapter.getAccount(parent.getUID());

        assertThat(mAccountsDbAdapter.getSubAccountCount(parent.getUID())).isEqualTo(1);
        assertThat(parent.getUID()).isEqualTo(child.getParentUID());

        assertThat(child.getFullName()).isEqualTo("Test:Child");
    }

	@After
	public void tearDown() throws Exception {
		mAccountsDbAdapter.deleteAllRecords();
	}
}
