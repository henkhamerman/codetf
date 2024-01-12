Refactoring Types: ['Extract Method']
lealone/command/ddl/AlterUser.java
/*
 * Copyright 2004-2013 H2 Group. Multiple-Licensed under the H2 License,
 * Version 1.0, and under the Eclipse Public License, Version 1.0
 * (http://h2database.com/html/license.html).
 * Initial Developer: H2 Group
 */
package org.lealone.command.ddl;

import org.lealone.api.ErrorCode;
import org.lealone.command.CommandInterface;
import org.lealone.dbobject.User;
import org.lealone.engine.Database;
import org.lealone.engine.Session;
import org.lealone.expression.Expression;
import org.lealone.message.DbException;
import org.lealone.security.SHA256;
import org.lealone.util.StringUtils;

/**
 * This class represents the statements
 * ALTER USER ADMIN,
 * ALTER USER RENAME,
 * ALTER USER SET PASSWORD
 */
public class AlterUser extends DefineCommand {

    private int type;
    private User user;
    private String newName;
    private Expression password;
    private Expression salt;
    private Expression hash;
    private boolean admin;

    public AlterUser(Session session) {
        super(session);
    }

    public void setType(int type) {
        this.type = type;
    }

    public void setNewName(String newName) {
        this.newName = newName;
    }

    public void setUser(User user) {
        this.user = user;
    }

    public void setAdmin(boolean admin) {
        this.admin = admin;
    }

    public void setSalt(Expression e) {
        salt = e;
    }

    public void setHash(Expression e) {
        hash = e;
    }

    public void setPassword(Expression password) {
        this.password = password;
    }

    private char[] getCharArray(Expression e) {
        return e.optimize(session).getValue(session).getString().toCharArray();
    }

    private byte[] getByteArray(Expression e) {
        return StringUtils.convertHexToBytes(e.optimize(session).getValue(session).getString());
    }

    public int update() {
        session.commit(true);
        Database db = session.getDatabase();
        switch (type) {
        case CommandInterface.ALTER_USER_SET_PASSWORD:
            if (user != session.getUser()) {
                session.getUser().checkAdmin();
            }
            if (hash != null && salt != null) {
                user.setSaltAndHash(getByteArray(salt), getByteArray(hash));
            } else {
                String name = newName == null ? user.getName() : newName;
                char[] passwordChars = getCharArray(password);
                byte[] userPasswordHash = SHA256.getKeyPasswordHash(name, passwordChars);
                user.setUserPasswordHash(userPasswordHash);
            }
            break;
        case CommandInterface.ALTER_USER_RENAME:
            session.getUser().checkAdmin();
            if (db.findUser(newName) != null || newName.equals(user.getName())) {
                throw DbException.get(ErrorCode.USER_ALREADY_EXISTS_1, newName);
            }
            db.renameDatabaseObject(session, user, newName);
            break;
        case CommandInterface.ALTER_USER_ADMIN:
            session.getUser().checkAdmin();
            if (!admin) {
                user.checkOwnsNoSchemas();
            }
            user.setAdmin(admin);
            break;
        default:
            DbException.throwInternalError("type=" + type);
        }
        db.update(session, user);
        return 0;
    }

    public int getType() {
        return type;
    }

}


File: lealone-sql/src/main/java/org/lealone/command/ddl/CreateUser.java
/*
 * Copyright 2004-2013 H2 Group. Multiple-Licensed under the H2 License,
 * Version 1.0, and under the Eclipse Public License, Version 1.0
 * (http://h2database.com/html/license.html).
 * Initial Developer: H2 Group
 */
package org.lealone.command.ddl;

import org.lealone.api.ErrorCode;
import org.lealone.command.CommandInterface;
import org.lealone.dbobject.User;
import org.lealone.engine.Database;
import org.lealone.engine.Session;
import org.lealone.expression.Expression;
import org.lealone.message.DbException;
import org.lealone.security.SHA256;
import org.lealone.util.StringUtils;

/**
 * This class represents the statement
 * CREATE USER
 */
public class CreateUser extends DefineCommand {

    private String userName;
    private boolean admin;
    private Expression password;
    private Expression salt;
    private Expression hash;
    private boolean ifNotExists;
    private String comment;

    public CreateUser(Session session) {
        super(session);
    }

    public void setIfNotExists(boolean ifNotExists) {
        this.ifNotExists = ifNotExists;
    }

    public void setUserName(String userName) {
        this.userName = userName;
    }

    public void setPassword(Expression password) {
        this.password = password;
    }

    private char[] getCharArray(Expression e) {
        return e.optimize(session).getValue(session).getString().toCharArray();
    }

    private byte[] getByteArray(Expression e) {
        return StringUtils.convertHexToBytes(e.optimize(session).getValue(session).getString());
    }

    public int update() {
        session.getUser().checkAdmin();
        session.commit(true);
        Database db = session.getDatabase();
        if (db.findRole(userName) != null) {
            throw DbException.get(ErrorCode.ROLE_ALREADY_EXISTS_1, userName);
        }
        if (db.findUser(userName) != null) {
            if (ifNotExists) {
                return 0;
            }
            throw DbException.get(ErrorCode.USER_ALREADY_EXISTS_1, userName);
        }
        int id = getObjectId();
        User user = new User(db, id, userName, false);
        user.setAdmin(admin);
        user.setComment(comment);
        if (hash != null && salt != null) {
            user.setSaltAndHash(getByteArray(salt), getByteArray(hash));
        } else if (password != null) {
            char[] passwordChars = getCharArray(password);
            byte[] userPasswordHash;
            if (userName.length() == 0 && passwordChars.length == 0) {
                userPasswordHash = new byte[0];
            } else {
                userPasswordHash = SHA256.getKeyPasswordHash(userName, passwordChars);
            }
            user.setUserPasswordHash(userPasswordHash);
        } else {
            throw DbException.throwInternalError();
        }
        db.addDatabaseObject(session, user);
        return 0;
    }

    public void setSalt(Expression e) {
        salt = e;
    }

    public void setHash(Expression e) {
        hash = e;
    }

    public void setAdmin(boolean b) {
        admin = b;
    }

    public void setComment(String comment) {
        this.comment = comment;
    }

    public int getType() {
        return CommandInterface.CREATE_USER;
    }

}
