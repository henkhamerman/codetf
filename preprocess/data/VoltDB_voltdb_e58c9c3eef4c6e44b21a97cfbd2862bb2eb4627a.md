Refactoring Types: ['Extract Method']
g/voltdb/sqlparser/semantics/grammar/DDLListener.java
package org.voltdb.sqlparser.semantics.grammar;

import java.util.ArrayList;
import java.util.List;

import org.antlr.v4.runtime.ANTLRErrorListener;
import org.antlr.v4.runtime.Parser;
import org.antlr.v4.runtime.RecognitionException;
import org.antlr.v4.runtime.Recognizer;
import org.antlr.v4.runtime.atn.ATNConfigSet;
import org.antlr.v4.runtime.dfa.DFA;
import org.antlr.v4.runtime.misc.NotNull;
import org.voltdb.sqlparser.semantics.symtab.CatalogAdapter;
import org.voltdb.sqlparser.semantics.symtab.Neutrino;
import org.voltdb.sqlparser.semantics.symtab.Type;
import org.voltdb.sqlparser.syntax.grammar.ErrorMessage;
import org.voltdb.sqlparser.syntax.grammar.ICatalog;
import org.voltdb.sqlparser.syntax.grammar.IInsertStatement;
import org.voltdb.sqlparser.syntax.grammar.IOperator;
import org.voltdb.sqlparser.syntax.grammar.ISelectQuery;
import org.voltdb.sqlparser.syntax.grammar.SQLParserBaseListener;
import org.voltdb.sqlparser.syntax.grammar.SQLParserParser;
import org.voltdb.sqlparser.syntax.grammar.ErrorMessage.Severity;
import org.voltdb.sqlparser.syntax.grammar.SQLParserParser.Column_definitionContext;
import org.voltdb.sqlparser.syntax.grammar.SQLParserParser.Column_nameContext;
import org.voltdb.sqlparser.syntax.grammar.SQLParserParser.Column_refContext;
import org.voltdb.sqlparser.syntax.grammar.SQLParserParser.Create_table_statementContext;
import org.voltdb.sqlparser.syntax.grammar.SQLParserParser.ExpressionContext;
import org.voltdb.sqlparser.syntax.grammar.SQLParserParser.Insert_statementContext;
import org.voltdb.sqlparser.syntax.grammar.SQLParserParser.ProjectionContext;
import org.voltdb.sqlparser.syntax.grammar.SQLParserParser.Select_statementContext;
import org.voltdb.sqlparser.syntax.grammar.SQLParserParser.Table_clauseContext;
import org.voltdb.sqlparser.syntax.grammar.SQLParserParser.Table_refContext;
import org.voltdb.sqlparser.syntax.grammar.SQLParserParser.ValueContext;
import org.voltdb.sqlparser.syntax.grammar.SQLParserParser.Where_clauseContext;
import org.voltdb.sqlparser.syntax.symtab.IColumn;
import org.voltdb.sqlparser.syntax.symtab.IParserFactory;
import org.voltdb.sqlparser.syntax.symtab.ISymbolTable;
import org.voltdb.sqlparser.syntax.symtab.ITable;
import org.voltdb.sqlparser.syntax.symtab.IType;

public class DDLListener extends SQLParserBaseListener implements ANTLRErrorListener {
	private ITable m_currentlyCreatedTable = null;
    private ISymbolTable m_symbolTable;
    private IParserFactory m_factory;
    private ICatalog m_catalog;
    private List<ErrorMessage> m_errorMessages = new ArrayList<ErrorMessage>();
    private ISelectQuery m_selectQuery = null;
    private IInsertStatement m_insertStatement = null;

    public DDLListener(IParserFactory aFactory) {
        m_factory = aFactory;
        m_symbolTable = aFactory.getStandardPrelude();
        m_catalog = aFactory.getCatalog();
        m_selectQuery = null;
        m_insertStatement = null;
    }

    public boolean hasErrors() {
        return m_errorMessages.size() > 0;
    }

    private final void addError(int line, int col, String errorMessageFormat, Object ... args) {
        String msg = String.format(errorMessageFormat, args);
        m_errorMessages.add(new ErrorMessage(line,
                                             col,
                                             Severity.Error,
                                             msg));
    }

    public final List<ErrorMessage> getErrorMessages() {
        return m_errorMessages;
    }

    public String getErrorMessagesAsString() {
        StringBuffer sb = new StringBuffer();
        int nerrs = getErrorMessages().size();
        sb.append(String.format("\nOh, dear, there seem%s to be %serror%s here.\n",
                                nerrs > 1 ? "" : "s",
                                nerrs > 1 ? "" : "an ",
                                nerrs > 1 ? "s" : ""));
        for (ErrorMessage em : getErrorMessages()) {
            sb.append(String.format("line %d, column %d: %s\n", em.getLine(), em.getCol(), em.getMsg()));
        }
        return sb.toString();
    }

	/**
	 * {@inheritDoc}
	 */
	@Override public void exitColumn_definition(SQLParserParser.Column_definitionContext ctx) {
	    String colName = ctx.column_name().IDENTIFIER().getText();
	    String type = ctx.type_expression().type_name().IDENTIFIER().getText();
	    Type colType = (Type) m_symbolTable.getType(type);
	    if (colType == null) {
	        addError(ctx.start.getLine(), ctx.start.getCharPositionInLine(), "Type expected");
	    } else {
	        m_currentlyCreatedTable.addColumn(colName, m_factory.newColumn(colName, colType));
	    }
	}

	/**
	 * {@inheritDoc}
	 *
	 * <p>The default implementation does nothing.</p>
	 */
	@Override public void enterCreate_table_statement(SQLParserParser.Create_table_statementContext ctx) {
	    String tableName = ctx.table_name().IDENTIFIER().getText();
	    m_currentlyCreatedTable = m_factory.newTable(tableName);
	}
	/**
	 * {@inheritDoc}
	 *
	 * <p>The default implementation does nothing.</p>
	 */
	@Override public void exitCreate_table_statement(SQLParserParser.Create_table_statementContext ctx) {
	    m_catalog.addTable(m_currentlyCreatedTable);
	    m_currentlyCreatedTable = null;
	}

	@Override public void enterSelect_statement(SQLParserParser.Select_statementContext ctx) {
	    m_selectQuery = m_factory.newSelectQuery(m_symbolTable);
	}
	/**
	 * {@inheritDoc}
	 *
	 * <p>The default implementation does nothing.</p>
	 */
	@Override public void exitSelect_statement(SQLParserParser.Select_statementContext ctx) {
	    m_factory.processQuery(m_selectQuery);
	}

	/**
	 * {@inheritDoc}
	 *
	 * <p>The default implementation does nothing.</p>
	 */
	@Override public void exitProjection(SQLParserParser.ProjectionContext ctx) {
	    String tableName = null;
	    String columnName = ctx.projection_ref().column_name().IDENTIFIER().getText();
	    String alias = null;
	    if (ctx.projection_ref().table_name() != null) {
	        tableName = ctx.projection_ref().table_name().IDENTIFIER().getText();
	    }
	    if (ctx.column_name() != null) {
	        alias = ctx.column_name().IDENTIFIER().getText();
	    }
	    m_selectQuery.addProjection(tableName, columnName, alias);
	}
	/**
	 * {@inheritDoc}
	 *
	 * <p>The default implementation does nothing.</p>
	 */
	@Override public void exitTable_clause(SQLParserParser.Table_clauseContext ctx) {
        for (SQLParserParser.Table_refContext tr : ctx.table_ref()) {
            String tableName = tr.table_name().get(0).IDENTIFIER().getText();
            String alias = null;
            if (tr.table_name().size() > 1) {
                alias = tr.table_name().get(1).IDENTIFIER().getText();
            }
            ITable table = m_catalog.getTableByName(tableName);
            if (table == null) {
                addError(tr.start.getLine(),
                         tr.start.getCharPositionInLine(),
                         "Cannot find table %s",
                         tableName);
            }
	        m_selectQuery.addTable(table, alias);
	    }
        while(m_selectQuery.hasNeutrinos()) {
        	m_selectQuery.popNeutrino();
        }
	}
	/**
	 * {@inheritDoc}
	 *
	 * <p>The default implementation does nothing.</p>
	 */
	@Override public void exitColumn_ref(@NotNull SQLParserParser.Column_refContext ctx) {
		String columnName = ctx.column_name().IDENTIFIER().getText();
		String tableName = null;
	    if (ctx.table_name() != null) {
	        tableName = ctx.table_name().IDENTIFIER().getText();
	    }
	    m_selectQuery.pushNeutrino(m_selectQuery.getColumnNeutrino(columnName,tableName));
	}

	/**
	 * {@inheritDoc}
	 *
	 * <p>The default implementation does nothing.</p>
	 */
	@Override public void exitWhere_clause(SQLParserParser.Where_clauseContext ctx) {
		Neutrino ret = (Neutrino) m_selectQuery.popNeutrino();
		if (!(ret != null && ret.isBooleanExpression())) { // check if expr is boolean
			addError(ctx.start.getLine(),
			        ctx.start.getCharPositionInLine(),
			        "Boolean expression expected");
		} else {
			// Push where statement, select knows if where exists and can pop it off if it does.
			m_selectQuery.setWhereCondition(ret);
		}
	}

	/**
	 * {@inheritDoc}
	 *
	 */
	@Override public void exitExpression(@NotNull SQLParserParser.ExpressionContext ctx) {
		List<ExpressionContext> exprs = ctx.expression();
		// If there is only one expression, the form is ( expression ), and we
		// just processed the inner expression.  So, only worry about
		// The case when there are 0 or 2 expressions.
		if (exprs.size() == 2) { // two expressions separated by something
		    // Calculate the operation.
		    String opString;
		    IOperator op;
		    if (ctx.timesop() != null) {
		        opString = ctx.timesop().getText();
		    } else if (ctx.addop() != null) {
		        opString = ctx.addop().getText();
		    } else if (ctx.relop() != null) {
		        opString = ctx.relop().getText();
		    } else {
		        addError(ctx.start.getLine(),
		                 ctx.start.getCharPositionInLine(),
		                 "Unknown operator");
		        return;
		    }
		    op = m_factory.getExpressionOperator(opString);
		    //
		    // Now, given the kind of operation, calculate the output.
		    //
		    Neutrino rightoperand = (Neutrino) m_selectQuery.popNeutrino();
		    Neutrino leftoperand = (Neutrino) m_selectQuery.popNeutrino();
		    Neutrino answer;
		    if (op.isArithmetic()) {
    		    answer = (Neutrino) m_selectQuery.getNeutrinoMath(op,
    		                                           leftoperand,
    		                                           rightoperand);
		    } else if (op.isRelational()) {
		        answer = (Neutrino) m_selectQuery.getNeutrinoCompare(op,
		                                                  leftoperand,
		                                                  rightoperand);
		    } else if (op.isBoolean()) {
		        answer = (Neutrino) m_selectQuery.getNeutrinoBoolean(op,
		                                                  leftoperand,
		                                                  rightoperand);
		    } else {
		        addError(ctx.start.getLine(),
		                 ctx.start.getCharPositionInLine(),
		                 "Internal Error: Unknown operation kind for operator \"%s\"",
		                 opString);
		        return;
		    }
		    if (answer == null) {
		        addError(ctx.start.getLine(),
		                ctx.start.getCharPositionInLine(),
		                "Incompatible argument types %s and %s",
		                leftoperand.getType().getName(),
		                rightoperand.getType().getName());
		        return;
		    }
		    m_selectQuery.pushNeutrino(answer);
		} else { // zero expressions.
			Column_refContext cref = ctx.column_ref();
			if (cref != null) {
			    String tableName = (cref.table_name() != null) ? cref.table_name().IDENTIFIER().getText() : null;
			    String columnName = cref.column_name().IDENTIFIER().getText();
			    Neutrino crefNeutrino = (Neutrino) m_selectQuery.getColumnNeutrino(columnName, tableName);
			    m_selectQuery.pushNeutrino(crefNeutrino);
			} else {
			    // TRUE,FALSE,or NUMBER constants.
				if (ctx.FALSE() != null) { // FALSE
				    Type boolType = (Type) m_factory.makeBooleanType();
					m_selectQuery.pushNeutrino(
							new Neutrino(boolType,
									     m_factory.makeUnaryAST(boolType, false)));
				} else if (ctx.TRUE() != null ) { // TRUE
				    Type boolType = (Type) m_factory.makeBooleanType();
					m_selectQuery.pushNeutrino(
							new Neutrino(boolType,
									    m_factory.makeUnaryAST(boolType, true)));
				} else { // must be NUMBER
				    Type intType = (Type) m_factory.makeIntegerType();
					m_selectQuery.pushNeutrino(
							new Neutrino(intType,
							             m_factory.makeUnaryAST(intType, Integer.valueOf(ctx.NUMBER().getText()))));
				}
			}
		}
	}

	/**
	 * {@inheritDoc}
	 *
	 * <p>The default implementation does nothing.</p>
	 */
	@Override public void exitInsert_statement(SQLParserParser.Insert_statementContext ctx) {
	    String tableName = ctx.table_name().IDENTIFIER().getText();
	    ITable table = m_catalog.getTableByName(tableName);
	    if (table == null) {
	        addError(ctx.table_name().start.getLine(),
	                 ctx.table_name().start.getCharPositionInLine(),
	                 "Undefined table name %s",
	                 tableName);
	        return;
	    }
	    if (ctx.column_name().size() != ctx.values().value().size()) {
	        addError(ctx.column_name().get(0).start.getLine(),
	                 ctx.column_name().get(0).start.getCharPositionInLine(),
	                 (ctx.column_name().size() > ctx.values().value().size())
	                   ? "Too few values in insert statement."
	                   : "Too many values in insert statement.");
	        return;
	    }
	    m_insertStatement = m_factory.newInsertStatement();
	    m_insertStatement.addTable(table);
	    List<String> colNames = new ArrayList<String>();
	    List<IType>  colTypes = new ArrayList<IType>();
	    List<String> colVals  = new ArrayList<String>();
	    for (Column_nameContext colCtx : ctx.column_name()) {
	        String colName = colCtx.IDENTIFIER().getText();
	        IColumn col = table.getColumnByName(colName);
	        if (col == null) {
	            addError(colCtx.start.getLine(),
	                     colCtx.start.getCharPositionInLine(),
	                     "Undefined column name %s in table %s",
	                     colName,
	                     tableName);
	            return;
	        }
	        IType colType = col.getType();
	        colNames.add(colName);
	        colTypes.add(colType);
	    }
	    for (ValueContext val : ctx.values().value()) {
	        String valStr = val.NUMBER().getText();
	        colVals.add(valStr);
	    }
	    for (int idx = 0; idx < colNames.size(); idx += 1) {
	        m_insertStatement.addColumn(colNames.get(idx),
	                                    colTypes.get(idx),
	                                    colVals.get(idx));
	    }
	}

    @Override
    public void reportAmbiguity(Parser aArg0, DFA aArg1, int aArg2, int aArg3,
            boolean aArg4, java.util.BitSet aArg5, ATNConfigSet aArg6) {
        // TODO Auto-generated method stub

    }

    @Override
    public void reportAttemptingFullContext(Parser aArg0, DFA aArg1, int aArg2,
            int aArg3, java.util.BitSet aArg4, ATNConfigSet aArg5) {
        // TODO Auto-generated method stub

    }

    @Override
    public void reportContextSensitivity(Parser aArg0, DFA aArg1, int aArg2,
            int aArg3, int aArg4, ATNConfigSet aArg5) {
    }

    @Override
    public void syntaxError(Recognizer<?, ?> aArg0, Object aTokObj, int aLine,
            int aCol, String msg, RecognitionException aArg5) {
        addError(aLine, aCol, msg);
    }

    public final ISelectQuery getSelectQuery() {
        return m_selectQuery;
    }

    public final IInsertStatement getInsertStatement() {
        return m_insertStatement;
    }

    public CatalogAdapter getCatalogAdapter() {
        assert(m_catalog instanceof CatalogAdapter);
        return (CatalogAdapter)m_catalog;
    }

    protected final IParserFactory getFactory() {
        return m_factory;
    }

}


File: src/voltsqlparser/semantics/org/voltdb/sqlparser/semantics/symtab/SymbolTable.java
package org.voltdb.sqlparser.semantics.symtab;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import org.voltdb.sqlparser.syntax.symtab.ISymbolTable;
import org.voltdb.sqlparser.syntax.symtab.ITop;

/**
 * A SymbolTable associates values and types with
 * strings.  SymbolTables may be nested.  Tables are
 * a kind of SymbolTable, since they have columns
 * and columns have names.  All entities have numeric
 * ids as well.  Numeric IDs with value less than 1000
 * are pre-defined entities, such as pre-defined types.
 * IDs with values more than 1000 are user defined entities,
 * such as columns and tables.
 *
 * @author bwhite
 *
 */
public class SymbolTable implements ISymbolTable {
    ISymbolTable m_parent;
    Type         m_integerType = null;
    public class TablePair {
        Table m_table;
        String m_alias;
        public TablePair(Table aTable, String aAlias) {
            m_table = aTable;
            m_alias = aAlias;
        }
        public final Table getTable() {
            return m_table;
        }
        public final String getAlias() {
            return m_alias;
        }
    }
    List<TablePair> m_tables = new ArrayList<TablePair>();
    Map<String, Top> m_lookup = new TreeMap<String, Top>(String.CASE_INSENSITIVE_ORDER);

    public SymbolTable(SymbolTable aParent) {
        m_parent = aParent;
    }

    /* (non-Javadoc)
     * @see org.voltdb.sqlparser.symtab.ISymbolTable#define(org.voltdb.sqlparser.symtab.Top)
     */
    @Override
    public void define(ITop aEntity) {
        if (aEntity.getName() != null) {
            m_lookup.put(aEntity.getName(), (Top) aEntity);
        }
        if (aEntity instanceof Table) {
            m_tables.add(new TablePair((Table)aEntity, aEntity.getName()));
        }
    }

    public String toString() {
    	return m_lookup.toString();
    }

    public void addTable(Table aTable,String aAlias) {
    	m_lookup.put(aAlias, aTable);
    	m_tables.add(new TablePair(aTable, aAlias));
    }

    /* (non-Javadoc)
     * @see org.voltdb.sqlparser.symtab.ISymbolTable#size()
     */
    @Override
    public int size() {
        return m_lookup.size();
    }

    /**
     * called with input tables as arguments, so that this table knows what to do.
     * @param args
     */
    public void buildLookup(String[] args) {

    }

    /* (non-Javadoc)
     * @see org.voltdb.sqlparser.symtab.ISymbolTable#isEmpty()
     */
    @Override
    public boolean isEmpty() {
        return m_lookup.size() == 0;
    }
    /* (non-Javadoc)
     * @see org.voltdb.sqlparser.symtab.ISymbolTable#get(java.lang.String)
     */
    @Override
    public final Top get(String aName) {
        Top ret = m_lookup.get(aName);
        if (ret == null) {
        	if (m_parent != null)
        		ret = (Top) m_parent.get(aName);
        }
        return ret;
    }

    /* (non-Javadoc)
     * @see org.voltdb.sqlparser.symtab.ISymbolTable#getType(java.lang.String)
     */
    @Override
    public final Type getType(String aName) { // is it illegal to name tables the same thing as types? I don't think that would work here.
        Top answer = get(aName);
        if (answer != null && answer instanceof Type) {
            return (Type)answer;
        } else if (m_parent != null) {
            return (Type) m_parent.getType(aName);
        } else {
            return null;
        }
    }

    /* (non-Javadoc)
     * @see org.voltdb.sqlparser.symtab.ISymbolTable#getValue(java.lang.String)
     */
    @Override
    public final Value getValue(String aName) {
        Top answer = get(aName);
        if (answer != null && answer instanceof Value) {
            return (Value)answer;
        }
        return null;
    }

    public final Table getTable(String aName) {
    	Top table = get(aName);
    	if (table != null && table instanceof Table)
    		return (Table)table;
    	return null;
    }

    public static ISymbolTable newStandardPrelude() {
        ISymbolTable answer = new SymbolTable(null);
        answer.define(new IntegerType("bigint", 8, 8));
        answer.define(new IntegerType("integer", 4, 4));
        answer.define(new IntegerType("tinyint", 1, 1));
        answer.define(new IntegerType("smallint", 2, 2));
        return answer;
    }

    public String getTableAliasByColumn(String aColName) {
        for (TablePair tp : m_tables) {
            Column col = tp.getTable().getColumnByName(aColName);
            if (col != null) {
                if (tp.getAlias() == null) {
                    return tp.getTable().getName();
                }
                return tp.getAlias();
            }
        }
        return null;
    }

    public String getTableNameByColumn(String aColName) {
        for (TablePair tp : m_tables) {
            Column col = tp.getTable().getColumnByName(aColName);
            if (col != null) {
                return tp.getTable().getName();
            }
        }
        return null;
    }

    public final List<TablePair> getTables() {
        return m_tables;
    }
}


File: src/voltsqlparser/syntax/org/voltdb/sqlparser/syntax/grammar/DDLListener.java
package org.voltdb.sqlparser.syntax.grammar;

import java.util.ArrayList;
import java.util.List;

import org.antlr.v4.runtime.ANTLRErrorListener;
import org.antlr.v4.runtime.Parser;
import org.antlr.v4.runtime.RecognitionException;
import org.antlr.v4.runtime.Recognizer;
import org.antlr.v4.runtime.atn.ATNConfigSet;
import org.antlr.v4.runtime.dfa.DFA;
import org.antlr.v4.runtime.misc.NotNull;
import org.voltdb.sqlparser.semantics.grammar.ErrorMessage;
import org.voltdb.sqlparser.semantics.grammar.ErrorMessage.Severity;
import org.voltdb.sqlparser.semantics.symtab.CatalogAdapter;
import org.voltdb.sqlparser.semantics.symtab.Neutrino;
import org.voltdb.sqlparser.semantics.symtab.Type;
import org.voltdb.sqlparser.syntax.grammar.SQLParserParser.Column_nameContext;
import org.voltdb.sqlparser.syntax.grammar.SQLParserParser.Column_refContext;
import org.voltdb.sqlparser.syntax.grammar.SQLParserParser.ExpressionContext;
import org.voltdb.sqlparser.syntax.grammar.SQLParserParser.ValueContext;
import org.voltdb.sqlparser.syntax.symtab.IColumn;
import org.voltdb.sqlparser.syntax.symtab.IParserFactory;
import org.voltdb.sqlparser.syntax.symtab.ISymbolTable;
import org.voltdb.sqlparser.syntax.symtab.ITable;
import org.voltdb.sqlparser.syntax.symtab.IType;

public class DDLListener extends SQLParserBaseListener implements ANTLRErrorListener {
	private ITable m_currentlyCreatedTable = null;
    private ISymbolTable m_symbolTable;
    private IParserFactory m_factory;
    private ICatalog m_catalog;
    private List<ErrorMessage> m_errorMessages = new ArrayList<ErrorMessage>();
    private ISelectQuery m_selectQuery = null;
    private IInsertStatement m_insertStatement = null;

    public DDLListener(IParserFactory aFactory) {
        m_factory = aFactory;
        m_symbolTable = aFactory.getStandardPrelude();
        m_catalog = aFactory.getCatalog();
        m_selectQuery = null;
        m_insertStatement = null;
    }

    public boolean hasErrors() {
        return m_errorMessages.size() > 0;
    }

    private final void addError(int line, int col, String errorMessageFormat, Object ... args) {
        String msg = String.format(errorMessageFormat, args);
        m_errorMessages.add(new ErrorMessage(line,
                                             col,
                                             Severity.Error,
                                             msg));
    }

    public final List<ErrorMessage> getErrorMessages() {
        return m_errorMessages;
    }

    public String getErrorMessagesAsString() {
        StringBuffer sb = new StringBuffer();
        int nerrs = getErrorMessages().size();
        sb.append(String.format("\nOh, dear, there seem%s to be %serror%s here.\n",
                                nerrs > 1 ? "" : "s",
                                nerrs > 1 ? "" : "an ",
                                nerrs > 1 ? "s" : ""));
        for (ErrorMessage em : getErrorMessages()) {
            sb.append(String.format("line %d, column %d: %s\n", em.getLine(), em.getCol(), em.getMsg()));
        }
        return sb.toString();
    }

	/**
	 * {@inheritDoc}
	 */
	@Override public void exitColumn_definition(SQLParserParser.Column_definitionContext ctx) {
	    String colName = ctx.column_name().IDENTIFIER().getText();
	    String type = ctx.type_expression().type_name().IDENTIFIER().getText();
	    Type colType = (Type) m_symbolTable.getType(type);
	    if (colType == null) {
	        addError(ctx.start.getLine(), ctx.start.getCharPositionInLine(), "Type expected");
	    } else {
	        m_currentlyCreatedTable.addColumn(colName, m_factory.newColumn(colName, colType));
	    }
	}

	/**
	 * {@inheritDoc}
	 *
	 * <p>The default implementation does nothing.</p>
	 */
	@Override public void enterCreate_table_statement(SQLParserParser.Create_table_statementContext ctx) {
	    String tableName = ctx.table_name().IDENTIFIER().getText();
	    m_currentlyCreatedTable = m_factory.newTable(tableName);
	}
	/**
	 * {@inheritDoc}
	 *
	 * <p>The default implementation does nothing.</p>
	 */
	@Override public void exitCreate_table_statement(SQLParserParser.Create_table_statementContext ctx) {
	    m_catalog.addTable(m_currentlyCreatedTable);
	    m_currentlyCreatedTable = null;
	}

	@Override public void enterSelect_statement(SQLParserParser.Select_statementContext ctx) {
	    m_selectQuery = m_factory.newSelectQuery(m_symbolTable);
	}
	/**
	 * {@inheritDoc}
	 *
	 * <p>The default implementation does nothing.</p>
	 */
	@Override public void exitSelect_statement(SQLParserParser.Select_statementContext ctx) {
	    m_factory.processQuery(m_selectQuery);
	}

	/**
	 * {@inheritDoc}
	 *
	 * <p>The default implementation does nothing.</p>
	 */
	@Override public void exitProjection(SQLParserParser.ProjectionContext ctx) {
	    String tableName = null;
	    String columnName = ctx.projection_ref().column_name().IDENTIFIER().getText();
	    String alias = null;
	    if (ctx.projection_ref().table_name() != null) {
	        tableName = ctx.projection_ref().table_name().IDENTIFIER().getText();
	    }
	    if (ctx.column_name() != null) {
	        alias = ctx.column_name().IDENTIFIER().getText();
	    }
	    m_selectQuery.addProjection(tableName, columnName, alias);
	}
	/**
	 * {@inheritDoc}
	 *
	 * <p>The default implementation does nothing.</p>
	 */
	@Override public void exitTable_clause(SQLParserParser.Table_clauseContext ctx) {
        for (SQLParserParser.Table_refContext tr : ctx.table_ref()) {
            String tableName = tr.table_name().get(0).IDENTIFIER().getText();
            String alias = null;
            if (tr.table_name().size() > 1) {
                alias = tr.table_name().get(1).IDENTIFIER().getText();
            }
            ITable table = m_catalog.getTableByName(tableName);
            if (table == null) {
                addError(tr.start.getLine(),
                         tr.start.getCharPositionInLine(),
                         "Cannot find table %s",
                         tableName);
            }
	        m_selectQuery.addTable(table, alias);
	    }
        while(m_selectQuery.hasNeutrinos()) {
        	m_selectQuery.popNeutrino();
        }
	}
	/**
	 * {@inheritDoc}
	 *
	 * <p>The default implementation does nothing.</p>
	 */
	@Override public void exitColumn_ref(@NotNull SQLParserParser.Column_refContext ctx) {
		String columnName = ctx.column_name().IDENTIFIER().getText();
		String tableName = null;
	    if (ctx.table_name() != null) {
	        tableName = ctx.table_name().IDENTIFIER().getText();
	    }
	    m_selectQuery.pushNeutrino(m_selectQuery.getColumnNeutrino(columnName,tableName));
	}

	/**
	 * {@inheritDoc}
	 *
	 * <p>The default implementation does nothing.</p>
	 */
	@Override public void exitWhere_clause(SQLParserParser.Where_clauseContext ctx) {
		Neutrino ret = (Neutrino)m_selectQuery.popNeutrino();
		if (!(ret != null && ret.isBooleanExpression())) { // check if expr is boolean
			addError(ctx.start.getLine(),
			        ctx.start.getCharPositionInLine(),
			        "Boolean expression expected");
		} else {
			// Push where statement, select knows if where exists and can pop it off if it does.
			m_selectQuery.setWhereCondition(ret);
		}
	}

	/**
	 * {@inheritDoc}
	 *
	 */
	@Override public void exitExpression(@NotNull SQLParserParser.ExpressionContext ctx) {
		List<ExpressionContext> exprs = ctx.expression();
		// If there is only one expression, the form is ( expression ), and we
		// just processed the inner expression.  So, only worry about
		// The case when there are 0 or 2 expressions.
		if (exprs.size() == 2) { // two expressions separated by something
		    // Calculate the operation.
		    String opString;
		    IOperator op;
		    if (ctx.timesop() != null) {
		        opString = ctx.timesop().getText();
		    } else if (ctx.addop() != null) {
		        opString = ctx.addop().getText();
		    } else if (ctx.relop() != null) {
		        opString = ctx.relop().getText();
		    } else {
		        addError(ctx.start.getLine(),
		                 ctx.start.getCharPositionInLine(),
		                 "Unknown operator");
		        return;
		    }
		    op = m_factory.getExpressionOperator(opString);
		    //
		    // Now, given the kind of operation, calculate the output.
		    //
		    Neutrino rightoperand = (Neutrino)m_selectQuery.popNeutrino();
		    Neutrino leftoperand = (Neutrino)m_selectQuery.popNeutrino();
		    Neutrino answer;
		    if (op.isArithmetic()) {
    		    answer = (Neutrino)m_selectQuery.getNeutrinoMath(op,
    		                                           leftoperand,
    		                                           rightoperand);
		    } else if (op.isRelational()) {
		        answer = (Neutrino)m_selectQuery.getNeutrinoCompare(op,
		                                                  leftoperand,
		                                                  rightoperand);
		    } else if (op.isBoolean()) {
		        answer = (Neutrino)m_selectQuery.getNeutrinoBoolean(op,
		                                                  leftoperand,
		                                                  rightoperand);
		    } else {
		        addError(ctx.start.getLine(),
		                 ctx.start.getCharPositionInLine(),
		                 "Internal Error: Unknown operation kind for operator \"%s\"",
		                 opString);
		        return;
		    }
		    if (answer == null) {
		        addError(ctx.start.getLine(),
		                ctx.start.getCharPositionInLine(),
		                "Incompatible argument types %s and %s",
		                leftoperand.getType().getName(),
		                rightoperand.getType().getName());
		        return;
		    }
		    m_selectQuery.pushNeutrino(answer);
		} else { // zero expressions.
			Column_refContext cref = ctx.column_ref();
			if (cref != null) {
			    String tableName = (cref.table_name() != null) ? cref.table_name().IDENTIFIER().getText() : null;
			    String columnName = cref.column_name().IDENTIFIER().getText();
			    Neutrino crefNeutrino = (Neutrino)m_selectQuery.getColumnNeutrino(columnName, tableName);
			    m_selectQuery.pushNeutrino(crefNeutrino);
			} else {
			    // TRUE,FALSE,or NUMBER constants.
				if (ctx.FALSE() != null) { // FALSE
				    Type boolType = (Type) m_factory.makeBooleanType();
					m_selectQuery.pushNeutrino(
							new Neutrino(boolType,
									     m_factory.makeUnaryAST(boolType, false)));
				} else if (ctx.TRUE() != null ) { // TRUE
				    Type boolType = (Type) m_factory.makeBooleanType();
					m_selectQuery.pushNeutrino(
							new Neutrino(boolType,
									    m_factory.makeUnaryAST(boolType, true)));
				} else { // must be NUMBER
				    Type intType = (Type) m_factory.makeIntegerType();
					m_selectQuery.pushNeutrino(
							new Neutrino(intType,
							             m_factory.makeUnaryAST(intType, Integer.valueOf(ctx.NUMBER().getText()))));
				}
			}
		}
	}

	/**
	 * {@inheritDoc}
	 *
	 * <p>The default implementation does nothing.</p>
	 */
	@Override public void exitInsert_statement(SQLParserParser.Insert_statementContext ctx) {
	    String tableName = ctx.table_name().IDENTIFIER().getText();
	    ITable table = m_catalog.getTableByName(tableName);
	    if (table == null) {
	        addError(ctx.table_name().start.getLine(),
	                 ctx.table_name().start.getCharPositionInLine(),
	                 "Undefined table name %s",
	                 tableName);
	        return;
	    }
	    if (ctx.column_name().size() != ctx.values().value().size()) {
	        addError(ctx.column_name().get(0).start.getLine(),
	                 ctx.column_name().get(0).start.getCharPositionInLine(),
	                 (ctx.column_name().size() > ctx.values().value().size())
	                   ? "Too few values in insert statement."
	                   : "Too many values in insert statement.");
	        return;
	    }
	    m_insertStatement = m_factory.newInsertStatement();
	    m_insertStatement.addTable(table);
	    List<String> colNames = new ArrayList<String>();
	    List<IType>  colTypes = new ArrayList<IType>();
	    List<String> colVals  = new ArrayList<String>();
	    for (Column_nameContext colCtx : ctx.column_name()) {
	        String colName = colCtx.IDENTIFIER().getText();
	        IColumn col = table.getColumnByName(colName);
	        if (col == null) {
	            addError(colCtx.start.getLine(),
	                     colCtx.start.getCharPositionInLine(),
	                     "Undefined column name %s in table %s",
	                     colName,
	                     tableName);
	            return;
	        }
	        IType colType = col.getType();
	        colNames.add(colName);
	        colTypes.add(colType);
	    }
	    for (ValueContext val : ctx.values().value()) {
	        String valStr = val.NUMBER().getText();
	        colVals.add(valStr);
	    }
	    for (int idx = 0; idx < colNames.size(); idx += 1) {
	        m_insertStatement.addColumn(colNames.get(idx),
	                                    colTypes.get(idx),
	                                    colVals.get(idx));
	    }
	}

    @Override
    public void reportAmbiguity(Parser aArg0, DFA aArg1, int aArg2, int aArg3,
            boolean aArg4, java.util.BitSet aArg5, ATNConfigSet aArg6) {
        // TODO Auto-generated method stub

    }

    @Override
    public void reportAttemptingFullContext(Parser aArg0, DFA aArg1, int aArg2,
            int aArg3, java.util.BitSet aArg4, ATNConfigSet aArg5) {
        // TODO Auto-generated method stub

    }

    @Override
    public void reportContextSensitivity(Parser aArg0, DFA aArg1, int aArg2,
            int aArg3, int aArg4, ATNConfigSet aArg5) {
    }

    @Override
    public void syntaxError(Recognizer<?, ?> aArg0, Object aTokObj, int aLine,
            int aCol, String msg, RecognitionException aArg5) {
        addError(aLine, aCol, msg);
    }

    public final ISelectQuery getSelectQuery() {
        return m_selectQuery;
    }

    public final IInsertStatement getInsertStatement() {
        return m_insertStatement;
    }

    public CatalogAdapter getCatalogAdapter() {
        assert(m_catalog instanceof CatalogAdapter);
        return (CatalogAdapter)m_catalog;
    }

    protected final IParserFactory getFactory() {
        return m_factory;
    }

}


File: tests/assertions/org/voltdb/sqlparser/matchers/SymbolTableAssert.java
package org.voltdb.sqlparser.matchers;

import org.assertj.core.api.AbstractAssert;
import org.voltdb.sqlparser.semantics.symtab.SymbolTable;
import org.voltdb.sqlparser.semantics.symtab.Type;

public class SymbolTableAssert extends AbstractAssert<SymbolTableAssert, SymbolTable> {
    public SymbolTableAssert(SymbolTable aSymTab) {
        super(aSymTab, SymbolTableAssert.class);
    }

    public static SymbolTableAssert assertThat(SymbolTable aSymTab) {
        return new SymbolTableAssert(aSymTab);
    }
    /**
     * True iff the symbol table is empty.
     */
    public SymbolTableAssert isEmpty() {
        isNotNull();
        if (!actual.isEmpty()) {
            failWithMessage("Expected empty symbol table");
        }
        return this;
    };

    public SymbolTableAssert hasSize(int aSize) {
        isNotNull();
        if (actual.size() != aSize) {
            failWithMessage("Expected %d elements, not %d", aSize, actual.size());
        }
        return this;
    }

    public TypeAssert definesType(String aTypeName) {
        isNotNull();
        Type t = actual.getType(aTypeName);
        if (t == null) {
            failWithMessage("Expected type <%s> to be defined", aTypeName);
        }
        return new TypeAssert(t);
    }
}


File: tests/assertions/org/voltdb/sqlparser/matchers/TypeAssert.java
package org.voltdb.sqlparser.matchers;

import org.assertj.core.api.AbstractAssert;
import org.voltdb.sqlparser.semantics.symtab.Type;

public class TypeAssert extends AbstractAssert<TypeAssert, Type> {

    protected TypeAssert(Type aActual) {
        super(aActual, TypeAssert.class);
        // TODO Auto-generated constructor stub
    }

    public TypeAssert hasName(String aTypeName) {
        isNotNull();
        if (actual.getName().equalsIgnoreCase(aTypeName)) {
            failWithMessage("Expected type named <%s>.", aTypeName);
        }
        return this;
    }

    public TypeAssert hasMaxSize(int aMaxSize) {
        isNotNull();
        if (actual.getMaxSize() != aMaxSize) {
            failWithMessage("Expected type name <%s> to have max size %d not %d",
                            actual.getName(), aMaxSize, actual.getMaxSize());
        }
        return this;
    }

    public TypeAssert hasNominalSize(int aNominalSize) {
        isNotNull();
        if (actual.getNominalSize() != aNominalSize) {
            failWithMessage("Expected type name <%s> to have nominal size %d not %d",
                            actual.getName(), aNominalSize, actual.getNominalSize());
        }
        return this;
    }

}


File: tests/assertions/org/voltdb/sqlparser/symtab/CatalogAdapterAssert.java
package org.voltdb.sqlparser.symtab;

import org.assertj.core.api.AbstractAssert;
import org.assertj.core.api.Condition;
import org.voltdb.sqlparser.semantics.symtab.CatalogAdapter;
import org.voltdb.sqlparser.semantics.symtab.Table;

/**
 * {@link CatalogAdapter} specific assertions - Generated by CustomAssertionGenerator.
 */
public class CatalogAdapterAssert extends
        AbstractAssert<CatalogAdapterAssert, CatalogAdapter> {

    /**
     * Creates a new </code>{@link CatalogAdapterAssert}</code> to make assertions on actual CatalogAdapter.
     * @param actual the CatalogAdapter we want to make assertions on.
     */
    public CatalogAdapterAssert(CatalogAdapter actual) {
        super(actual, CatalogAdapterAssert.class);
    }

    /**
     * An entry point for CatalogAdapterAssert to follow AssertJ standard <code>assertThat()</code> statements.<br>
     * With a static import, one's can write directly : <code>assertThat(myCatalogAdapter)</code> and get specific assertion with code completion.
     * @param actual the CatalogAdapter we want to make assertions on.
     * @return a new </code>{@link CatalogAdapterAssert}</code>
     */
    public static CatalogAdapterAssert assertThat(CatalogAdapter actual) {
        return new CatalogAdapterAssert(actual);
    }

    public CatalogAdapterAssert hasTableNamed(String aTableName,
                                              Condition<Table> ...conditions) {
        isNotNull();
        Table tbl = actual.getTableByName(aTableName);
        if (tbl == null) {
            failWithMessage("Expected to find a table named <%s>", aTableName);
        }
        for (Condition<Table> cond : conditions) {
            org.voltdb.sqlparser.symtab.TableAssert.assertThat(tbl).has(cond);
        }
        return this;
    }

}


File: tests/assertions/org/voltdb/sqlparser/symtab/SymbolTableAssert.java
package org.voltdb.sqlparser.symtab;

import static java.lang.String.format;

import org.assertj.core.api.AbstractAssert;
import org.voltdb.sqlparser.semantics.symtab.SymbolTable;

/**
 * {@link SymbolTable} specific assertions - Generated by CustomAssertionGenerator.
 */
public class SymbolTableAssert extends
        AbstractAssert<SymbolTableAssert, SymbolTable> {

    /**
     * Creates a new </code>{@link SymbolTableAssert}</code> to make assertions on actual SymbolTable.
     * @param actual the SymbolTable we want to make assertions on.
     */
    public SymbolTableAssert(SymbolTable actual) {
        super(actual, SymbolTableAssert.class);
    }

    /**
     * An entry point for SymbolTableAssert to follow AssertJ standard <code>assertThat()</code> statements.<br>
     * With a static import, one's can write directly : <code>assertThat(mySymbolTable)</code> and get specific assertion with code completion.
     * @param actual the SymbolTable we want to make assertions on.
     * @return a new </code>{@link SymbolTableAssert}</code>
     */
    public static SymbolTableAssert assertThat(SymbolTable actual) {
        return new SymbolTableAssert(actual);
    }

    /**
     * Verifies that the actual SymbolTable is empty.
     * @return this assertion object.
     * @throws AssertionError - if the actual SymbolTable is not empty.
     */
    public SymbolTableAssert isEmpty() {
        // check that actual SymbolTable we want to make assertions on is not null.
        isNotNull();

        // we overrides the default error message with a more explicit one
        String errorMessage = format(
                "Expected actual SymbolTable to be empty but was not.", actual);

        // check
        if (!actual.isEmpty())
            throw new AssertionError(errorMessage);

        // return the current assertion for method chaining
        return this;
    }

    /**
     * Verifies that the actual SymbolTable is not empty.
     * @return this assertion object.
     * @throws AssertionError - if the actual SymbolTable is empty.
     */
    public SymbolTableAssert isNotEmpty() {
        // check that actual SymbolTable we want to make assertions on is not null.
        isNotNull();

        // we overrides the default error message with a more explicit one
        String errorMessage = format(
                "Expected actual SymbolTable not to be empty but was.", actual);

        // check
        if (actual.isEmpty())
            throw new AssertionError(errorMessage);

        // return the current assertion for method chaining
        return this;
    }

}


File: tests/assertions/org/voltdb/sqlparser/symtab/TableAssert.java
package org.voltdb.sqlparser.symtab;

import org.assertj.core.api.AbstractAssert;
import org.assertj.core.api.Condition;
import org.assertj.core.api.Fail;
import org.voltdb.sqlparser.semantics.symtab.Column;
import org.voltdb.sqlparser.semantics.symtab.Table;

/**
 * {@link Table} specific assertions - Generated by CustomAssertionGenerator.
 */
public class TableAssert extends AbstractAssert<TableAssert, Table> {

    /**
     * Creates a new </code>{@link TableAssert}</code> to make assertions on actual Table.
     * @param actual the Table we want to make assertions on.
     */
    public TableAssert(Table actual) {
        super(actual, TableAssert.class);
    }

    /**
     * An entry point for TableAssert to follow AssertJ standard <code>assertThat()</code> statements.<br>
     * With a static import, one's can write directly : <code>assertThat(myTable)</code> and get specific assertion with code completion.
     * @param actual the Table we want to make assertions on.
     * @return a new </code>{@link TableAssert}</code>
     */
    public static TableAssert assertThat(Table actual) {
        return new TableAssert(actual);
    }

    public static Condition<Table> withColumnNamed(final String aColumnName,
                                                    final Condition<Column> ...conditions) {
        return new Condition<Table>() {
            @Override
            public boolean matches(Table aValue) {
                Column col = aValue.getColumnByName(aColumnName);
                if (col == null) {
                    Fail.fail(String.format("Expected column named <%s>", aColumnName));
                }
                for (Condition<Column> cond : conditions) {
                    org.voltdb.sqlparser.symtab.ColumnAssert.assertThat(col).has(cond);
                }
                return true;
            }
        };
    }
}


File: tests/assertions/org/voltdb/sqlparser/symtab/TypeAssert.java
package org.voltdb.sqlparser.symtab;

import org.assertj.core.api.AbstractAssert;
import org.voltdb.sqlparser.semantics.symtab.Type;

/**
 * {@link Type} specific assertions - Generated by CustomAssertionGenerator.
 */
public class TypeAssert extends AbstractAssert<TypeAssert, Type> {

    /**
     * Creates a new </code>{@link TypeAssert}</code> to make assertions on actual Type.
     * @param actual the Type we want to make assertions on.
     */
    public TypeAssert(Type actual) {
        super(actual, TypeAssert.class);
    }

    /**
     * An entry point for TypeAssert to follow AssertJ standard <code>assertThat()</code> statements.<br>
     * With a static import, one's can write directly : <code>assertThat(myType)</code> and get specific assertion with code completion.
     * @param actual the Type we want to make assertions on.
     * @return a new </code>{@link TypeAssert}</code>
     */
    public static TypeAssert assertThat(Type actual) {
        return new TypeAssert(actual);
    }

}


File: tests/frontend/org/voltdb/sqlparser/TestCreateTable.java
package org.voltdb.sqlparser;

import static org.voltdb.sqlparser.symtab.CatalogAdapterAssert.assertThat;
import static org.voltdb.sqlparser.symtab.ColumnAssert.withColumnTypeNamed;
import static org.voltdb.sqlparser.symtab.TableAssert.withColumnNamed;

import java.io.IOException;

import org.junit.Test;
import org.voltdb.sqlparser.semantics.grammar.DDLListener;
import org.voltdb.sqlparser.semantics.symtab.CatalogAdapter;
import org.voltdb.sqlparser.semantics.symtab.ParserFactory;
import org.voltdb.sqlparser.syntax.SQLParserDriver;

public class TestCreateTable {

    @Test
    public void testMultiTableCreation() throws IOException {
        testDDL1("create table alpha ( id bigint );");
        testDDL2("create table beta ( id bigint not null, local tinyint not null );");
    }

    private void testDDL1(String ddl) throws IOException {
        CatalogAdapter catalog = new CatalogAdapter();
        ParserFactory factory = new ParserFactory(catalog);
        DDLListener listener = new DDLListener(factory);
        SQLParserDriver driver = new SQLParserDriver(ddl, null);
        driver.walk(listener);
        assertThat(catalog)
            .hasTableNamed("alpha",
                      withColumnNamed("id",
                                      withColumnTypeNamed("bigint")));
    }

    private void testDDL2(String ddl) throws IOException {
        CatalogAdapter catalog = new CatalogAdapter();
        ParserFactory factory = new ParserFactory(catalog);
        DDLListener listener = new DDLListener(factory);
        SQLParserDriver driver = new SQLParserDriver(ddl, null);
        driver.walk(listener);

        assertThat(catalog)
            .hasTableNamed("beta",
                      withColumnNamed("id",
                                      withColumnTypeNamed("bigint")),
                      withColumnNamed("local",
                                     withColumnTypeNamed("tinyint")));
    }
}


File: tests/frontend/org/voltdb/sqlparser/TestSymbolTable.java
package org.voltdb.sqlparser;

import static org.voltdb.sqlparser.matchers.SymbolTableAssert.assertThat;

import org.junit.Test;
import org.voltdb.sqlparser.semantics.symtab.IntegerType;
import org.voltdb.sqlparser.semantics.symtab.SymbolTable;

public class TestSymbolTable {
    @Test
    public void test() {
        SymbolTable s = new SymbolTable(null);
        assertThat(s).isEmpty();
        assertThat(s).hasSize(0);
        IntegerType bigint = new IntegerType("bigint", 8, 8);
        s.define(bigint);
        assertThat(s).hasSize(1)
                     .definesType("bigint")
                     .hasMaxSize(8)
                     .hasNominalSize(8);
    }
}
