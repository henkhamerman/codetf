Refactoring Types: ['Move Class']
k/src/main/java/org/neo4j/consistency/checking/SchemaRecordCheck.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.consistency.checking;

import java.util.HashMap;
import java.util.Map;

import org.neo4j.consistency.report.ConsistencyReport;
import org.neo4j.consistency.store.DiffRecordAccess;
import org.neo4j.consistency.store.RecordAccess;
import org.neo4j.kernel.api.exceptions.schema.MalformedSchemaRuleException;
import org.neo4j.kernel.impl.store.MandatoryNodePropertyConstraintRule;
import org.neo4j.kernel.impl.store.MandatoryRelationshipPropertyConstraintRule;
import org.neo4j.kernel.impl.store.SchemaRuleAccess;
import org.neo4j.kernel.impl.store.UniquePropertyConstraintRule;
import org.neo4j.kernel.impl.store.record.DynamicRecord;
import org.neo4j.kernel.impl.store.record.IndexRule;
import org.neo4j.kernel.impl.store.record.LabelTokenRecord;
import org.neo4j.kernel.impl.store.record.PropertyKeyTokenRecord;
import org.neo4j.kernel.impl.store.record.SchemaRule;

/**
 * Note that this class builds up an in-memory representation of the complete schema store by being used in
 * multiple phases.
 *
 * This differs from other store checks, where we deliberately avoid building up state, expecting store to generally be
 * larger than available memory. However, it is safe to make the assumption that schema storage will fit in memory
 * because the same assumption is also made by the online database.
 */
public class SchemaRecordCheck implements RecordCheck<DynamicRecord, ConsistencyReport.SchemaConsistencyReport>
{
    enum Phase
    {
        /**
         * Verify rules can be de-serialized, have valid forward references, and build up internal state
         * for checking in back references in later phases (obligations)
         */
        CHECK_RULES,

        /** Verify obligations, that is correct back references */
        CHECK_OBLIGATIONS
    }

    final SchemaRuleAccess ruleAccess;
    final Map<Long, DynamicRecord> indexObligations;
    final Map<Long, DynamicRecord> constraintObligations;
    final Map<SchemaRuleContent, DynamicRecord> contentMap;
    final Phase phase;

    private SchemaRecordCheck(
            SchemaRuleAccess ruleAccess,
            Map<Long, DynamicRecord> indexObligations,
            Map<Long, DynamicRecord> constraintObligations,
            Map<SchemaRuleContent, DynamicRecord> contentMap,
            Phase phase )
    {
        this.ruleAccess = ruleAccess;
        this.indexObligations = indexObligations;
        this.constraintObligations = constraintObligations;
        this.contentMap = contentMap;
        this.phase = phase;
    }

    public SchemaRecordCheck( SchemaRuleAccess ruleAccess )
    {
        this( ruleAccess,
              new HashMap<Long, DynamicRecord>(),
              new HashMap<Long, DynamicRecord>(),
              new HashMap<SchemaRuleContent, DynamicRecord>(),
              Phase.CHECK_RULES );
    }

    public SchemaRecordCheck forObligationChecking()
    {
        return new SchemaRecordCheck(
                ruleAccess, indexObligations, constraintObligations, contentMap, Phase.CHECK_OBLIGATIONS );
    }

    @Override
    public void check( DynamicRecord record,
                       CheckerEngine<DynamicRecord, ConsistencyReport.SchemaConsistencyReport> engine,
                       RecordAccess records )
    {
        if ( record.inUse() && record.isStartRecord() )
        {
            // parse schema rule
            SchemaRule rule;
            try
            {
                rule = ruleAccess.loadSingleSchemaRule( record.getId() );
            }
            catch ( MalformedSchemaRuleException e )
            {
                engine.report().malformedSchemaRule();
                return;
            }

            // given a parsed schema rule
            if ( Phase.CHECK_RULES == phase )
            {
                engine.comparativeCheck( records.label( rule.getLabel() ), VALID_LABEL );

                SchemaRuleContent content = new SchemaRuleContent( rule );
                DynamicRecord previousContentRecord = contentMap.put( content, record );
                if ( null != previousContentRecord )
                {
                    engine.report().duplicateRuleContent( previousContentRecord );
                }
            }

            SchemaRule.Kind kind = rule.getKind();
            switch ( kind )
            {
                case INDEX_RULE:
                case CONSTRAINT_INDEX_RULE:
                    checkIndexRule( (IndexRule) rule, engine, record, records );
                    break;
                case UNIQUENESS_CONSTRAINT:
                    checkUniquenessConstraintRule( (UniquePropertyConstraintRule) rule, engine, record, records );
                    break;
                case MANDATORY_NODE_PROPERTY_CONSTRAINT:
                    checkMandatoryProperty( ((MandatoryNodePropertyConstraintRule) rule).getPropertyKey(),
                            records, engine );
                    break;
                case MANDATORY_RELATIONSHIP_PROPERTY_CONSTRAINT:
                    checkMandatoryProperty( ((MandatoryRelationshipPropertyConstraintRule) rule).getPropertyKey(),
                            records, engine );
                    break;
                default:
                    engine.report().unsupportedSchemaRuleKind( kind );
            }
        }
    }

    private void checkUniquenessConstraintRule( UniquePropertyConstraintRule rule,
                                                CheckerEngine<DynamicRecord, ConsistencyReport.SchemaConsistencyReport> engine,
                                                DynamicRecord record, RecordAccess records )
    {
        if ( phase == Phase.CHECK_RULES )
        {
            engine.comparativeCheck( records.propertyKey( rule.getPropertyKey() ), VALID_PROPERTY_KEY );
            DynamicRecord previousObligation = indexObligations.put( rule.getOwnedIndex(), record );
            if ( null != previousObligation )
            {
                engine.report().duplicateObligation( previousObligation );
            }
        }
        else if ( phase == Phase.CHECK_OBLIGATIONS )
        {
            DynamicRecord obligation = constraintObligations.get( rule.getId() );
            if ( null == obligation)
            {
                engine.report().missingObligation( SchemaRule.Kind.CONSTRAINT_INDEX_RULE );
            }
            else
            {
                if ( obligation.getId() != rule.getOwnedIndex() )
                {
                    engine.report().uniquenessConstraintNotReferencingBack( obligation );
                }
            }
        }
    }

    private void checkMandatoryProperty( int propertyKey, RecordAccess records,
            CheckerEngine<DynamicRecord,ConsistencyReport.SchemaConsistencyReport> engine )
    {
        if ( phase == Phase.CHECK_RULES )
        {
            engine.comparativeCheck( records.propertyKey( propertyKey ), VALID_PROPERTY_KEY );
        }
    }

    private void checkIndexRule( IndexRule rule,
                                 CheckerEngine<DynamicRecord, ConsistencyReport.SchemaConsistencyReport> engine,
                                 DynamicRecord record, RecordAccess records )
    {
        if ( phase == Phase.CHECK_RULES )
        {
            engine.comparativeCheck( records.propertyKey( rule.getPropertyKey() ), VALID_PROPERTY_KEY );
            if ( rule.isConstraintIndex() && rule.getOwningConstraint() != null )
            {
                DynamicRecord previousObligation = constraintObligations.put( rule.getOwningConstraint(), record );
                if ( null != previousObligation )
                {
                    engine.report().duplicateObligation( previousObligation );
                }
            }
        }
        else if ( phase == Phase.CHECK_OBLIGATIONS )
        {
            if ( rule.isConstraintIndex() )
            {
                DynamicRecord obligation = indexObligations.get( rule.getId() );
                if ( null == obligation ) // no pointer to here
                {
                    if ( rule.getOwningConstraint() != null ) // we only expect a pointer if we have an owner
                    {
                        engine.report().missingObligation( SchemaRule.Kind.UNIQUENESS_CONSTRAINT );
                    }
                }
                else
                {
                    // if someone points to here, it must be our owner
                    if ( obligation.getId() != rule.getOwningConstraint() )
                    {
                        engine.report().constraintIndexRuleNotReferencingBack( obligation );
                    }
                }
            }
        }
    }

    @Override
    public void checkChange( DynamicRecord oldRecord, DynamicRecord newRecord,
                             CheckerEngine<DynamicRecord, ConsistencyReport.SchemaConsistencyReport> engine,
                             DiffRecordAccess records )
    {
    }

    public static final ComparativeRecordChecker<DynamicRecord,LabelTokenRecord,
            ConsistencyReport.SchemaConsistencyReport> VALID_LABEL =
            new ComparativeRecordChecker<DynamicRecord, LabelTokenRecord, ConsistencyReport.SchemaConsistencyReport>()
    {
        @Override
        public void checkReference( DynamicRecord record, LabelTokenRecord labelTokenRecord,
                                    CheckerEngine<DynamicRecord, ConsistencyReport.SchemaConsistencyReport> engine,
                                    RecordAccess records )
        {
            if ( !labelTokenRecord.inUse() )
            {
                engine.report().labelNotInUse( labelTokenRecord );
            }
        }
    };

    public static final ComparativeRecordChecker<DynamicRecord, PropertyKeyTokenRecord,
            ConsistencyReport.SchemaConsistencyReport> VALID_PROPERTY_KEY =
            new ComparativeRecordChecker<DynamicRecord, PropertyKeyTokenRecord, ConsistencyReport.SchemaConsistencyReport>()
    {
        @Override
        public void checkReference( DynamicRecord record, PropertyKeyTokenRecord propertyKeyTokenRecord,
                                    CheckerEngine<DynamicRecord, ConsistencyReport.SchemaConsistencyReport> engine,
                                    RecordAccess records )
        {
            if ( !propertyKeyTokenRecord.inUse() )
            {
                engine.report().propertyKeyNotInUse( propertyKeyTokenRecord );
            }
        }
    };
}


File: community/consistency-check/src/main/java/org/neo4j/consistency/checking/SchemaRuleContent.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.consistency.checking;

import org.neo4j.kernel.impl.store.UniquePropertyConstraintRule;
import org.neo4j.kernel.impl.store.record.IndexRule;
import org.neo4j.kernel.impl.store.record.SchemaRule;

public class SchemaRuleContent
{
    private final SchemaRule schemaRule;

    public SchemaRuleContent( SchemaRule schemaRule )
    {
        this.schemaRule = schemaRule;
    }

    @Override
    public String toString()
    {
        return "ContentOf:" + schemaRule.toString();
    }

    @Override
    public boolean equals( Object obj )
    {
        if ( this == obj )
        {
            return true;
        }
        if ( obj instanceof SchemaRuleContent )
        {
            SchemaRuleContent that = (SchemaRuleContent) obj;
            if ( this.schemaRule.getLabel() != that.schemaRule.getLabel() )
            {
                return false;
            }
            switch ( schemaRule.getKind() )
            {
                case INDEX_RULE:
                case CONSTRAINT_INDEX_RULE:
                    if ( !that.schemaRule.getKind().isIndex() )
                    {
                        return false;
                    }
                    return indexRulesEquals( (IndexRule) this.schemaRule, (IndexRule) that.schemaRule );
                case UNIQUENESS_CONSTRAINT:
                    return this.schemaRule.getKind() == that.schemaRule.getKind() && uniquenessConstraintEquals(
                            (UniquePropertyConstraintRule) this.schemaRule,
                            (UniquePropertyConstraintRule) that.schemaRule );
                default:
                    throw new IllegalArgumentException( "Invalid SchemaRule kind: " + schemaRule.getKind() );
            }
        }
        return false;
    }

    private static boolean indexRulesEquals( IndexRule lhs, IndexRule rhs )
    {
        return lhs.getPropertyKey() == rhs.getPropertyKey();
    }

    private static boolean uniquenessConstraintEquals( UniquePropertyConstraintRule lhs, UniquePropertyConstraintRule rhs )
    {
        return lhs.getPropertyKey() == rhs.getPropertyKey();
    }

    @Override
    public int hashCode()
    {
        return (int) schemaRule.getLabel();
    }
}


File: community/consistency-check/src/main/java/org/neo4j/consistency/checking/full/MandatoryPropertyChecker.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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

package org.neo4j.consistency.checking.full;

import java.util.Arrays;
import java.util.Iterator;

import org.neo4j.collection.primitive.Primitive;
import org.neo4j.collection.primitive.PrimitiveIntIterator;
import org.neo4j.collection.primitive.PrimitiveIntObjectMap;
import org.neo4j.collection.primitive.PrimitiveIntObjectVisitor;
import org.neo4j.collection.primitive.PrimitiveIntSet;
import org.neo4j.consistency.checking.CheckDecorator;
import org.neo4j.consistency.checking.CheckerEngine;
import org.neo4j.consistency.checking.ComparativeRecordChecker;
import org.neo4j.consistency.checking.OwningRecordCheck;
import org.neo4j.consistency.report.ConsistencyReport;
import org.neo4j.consistency.store.DiffRecordAccess;
import org.neo4j.consistency.store.RecordAccess;
import org.neo4j.kernel.impl.store.MandatoryNodePropertyConstraintRule;
import org.neo4j.kernel.impl.store.MandatoryRelationshipPropertyConstraintRule;
import org.neo4j.kernel.impl.store.PropertyConstraintRule;
import org.neo4j.kernel.impl.store.RecordStore;
import org.neo4j.kernel.impl.store.SchemaStorage;
import org.neo4j.kernel.impl.store.record.DynamicRecord;
import org.neo4j.kernel.impl.store.record.NodeRecord;
import org.neo4j.kernel.impl.store.record.PrimitiveRecord;
import org.neo4j.kernel.impl.store.record.PropertyBlock;
import org.neo4j.kernel.impl.store.record.PropertyRecord;
import org.neo4j.kernel.impl.store.record.Record;
import org.neo4j.kernel.impl.store.record.RelationshipRecord;

import static org.neo4j.consistency.checking.full.NodeLabelReader.getListOfLabels;

public class MandatoryPropertyChecker extends CheckDecorator.Adapter
{
    private static final Class<PropertyConstraintRule> BASE_RULE = PropertyConstraintRule.class;

    private final PrimitiveIntObjectMap<int[]> nodes = Primitive.intObjectMap();
    private final PrimitiveIntObjectMap<int[]> relationships = Primitive.intObjectMap();

    public MandatoryPropertyChecker( RecordStore<DynamicRecord> schemaStore )
    {
        SchemaStorage schemaStorage = new SchemaStorage( schemaStore );
        for ( Iterator<PropertyConstraintRule> rules = schemaStorage.schemaRules( BASE_RULE ); safeHasNext( rules ); )
        {
            PropertyConstraintRule rule = rules.next();

            PrimitiveIntObjectMap<int[]> storage;
            int labelOrRelType;
            int propertyKey;

            switch ( rule.getKind() )
            {
            case MANDATORY_NODE_PROPERTY_CONSTRAINT:
                storage = nodes;
                MandatoryNodePropertyConstraintRule nodeRule = (MandatoryNodePropertyConstraintRule) rule;
                labelOrRelType = nodeRule.getLabel();
                propertyKey = nodeRule.getPropertyKey();
                break;

            case MANDATORY_RELATIONSHIP_PROPERTY_CONSTRAINT:
                storage = relationships;
                MandatoryRelationshipPropertyConstraintRule relRule = (MandatoryRelationshipPropertyConstraintRule) rule;
                labelOrRelType = relRule.getRelationshipType();
                propertyKey = relRule.getPropertyKey();
                break;

            default:
                continue;
            }

            recordConstraint( labelOrRelType, propertyKey, storage );
        }
    }

    private boolean safeHasNext( Iterator<?> iterator )
    {
        for (; ; )
        {
            try
            {
                return iterator.hasNext();
            }
            catch ( Exception e )
            {
                // ignore
            }
        }
    }

    private static void recordConstraint( int labelOrRelType, int propertyKey, PrimitiveIntObjectMap<int[]> storage )
    {
        int[] propertyKeys = storage.get( labelOrRelType );
        if ( propertyKeys == null )
        {
            propertyKeys = new int[]{propertyKey};
        }
        else
        {
            propertyKeys = Arrays.copyOf( propertyKeys, propertyKeys.length + 1 );
            propertyKeys[propertyKeys.length - 1] = propertyKey;
        }
        storage.put( labelOrRelType, propertyKeys );
    }

    @Override
    public OwningRecordCheck<NodeRecord,ConsistencyReport.NodeConsistencyReport> decorateNodeChecker(
            OwningRecordCheck<NodeRecord,ConsistencyReport.NodeConsistencyReport> checker )
    {
        if ( nodes.isEmpty() )
        {
            return checker;
        }
        else
        {
            return new NodeChecker( nodes, checker );
        }
    }

    @Override
    public OwningRecordCheck<RelationshipRecord,ConsistencyReport.RelationshipConsistencyReport>
    decorateRelationshipChecker(
            OwningRecordCheck<RelationshipRecord,ConsistencyReport.RelationshipConsistencyReport> checker )
    {
        if ( relationships.isEmpty() )
        {
            return checker;
        }
        else
        {
            return new RelationshipChecker( relationships, checker );
        }
    }

    private static abstract class Checker<RECORD extends PrimitiveRecord,
            REPORT extends ConsistencyReport.PrimitiveConsistencyReport>
            implements OwningRecordCheck<RECORD,REPORT>
    {
        private final OwningRecordCheck<RECORD,REPORT> next;

        private Checker( OwningRecordCheck<RECORD,REPORT> next )
        {
            this.next = next;
        }

        @Override
        public void check( RECORD record, CheckerEngine<RECORD,REPORT> engine, RecordAccess records )
        {
            next.check( record, engine, records );
            if ( record.inUse() )
            {
                PrimitiveIntSet keys = mandatoryPropertiesFor( record, engine, records );
                if ( keys != null )
                {
                    checkProperties( record, keys, engine, records );
                }
            }
        }

        private void checkProperties( RECORD record, PrimitiveIntSet keys, CheckerEngine<RECORD,REPORT> engine,
                RecordAccess records )
        {
            long firstProperty = record.getNextProp();
            if ( !Record.NO_NEXT_PROPERTY.is( firstProperty ) )
            {
                engine.comparativeCheck( records.property( firstProperty ), new ChainCheck<RECORD,REPORT>( keys ) );
            }
            else
            {
                reportMissingKeys( engine.report(), keys );
            }
        }

        abstract PrimitiveIntSet mandatoryPropertiesFor( RECORD record, CheckerEngine<RECORD,REPORT> engine,
                RecordAccess records );


        @Override
        public ComparativeRecordChecker<RECORD,PrimitiveRecord,REPORT> ownerCheck()
        {
            return next.ownerCheck();
        }

        @Override
        public void checkChange( RECORD oldRecord, RECORD newRecord, CheckerEngine<RECORD,REPORT> engine,
                DiffRecordAccess records )
        {
            next.checkChange( oldRecord, newRecord, engine, records );
        }
    }

    static class NodeChecker extends Checker<NodeRecord,ConsistencyReport.NodeConsistencyReport>
    {
        private final PrimitiveIntObjectMap<int[]> mandatory;
        private final int capacity;

        private NodeChecker( PrimitiveIntObjectMap<int[]> mandatory,
                OwningRecordCheck<NodeRecord,ConsistencyReport.NodeConsistencyReport> next )
        {
            super( next );
            this.mandatory = mandatory;
            this.capacity = SizeCounter.countSizeOf( mandatory );
        }

        @Override
        PrimitiveIntSet mandatoryPropertiesFor( NodeRecord record,
                CheckerEngine<NodeRecord,ConsistencyReport.NodeConsistencyReport> engine, RecordAccess records )
        {
            PrimitiveIntSet keys = null;
            for ( Long label : getListOfLabels( record, records, engine ) )
            {
                int[] propertyKeys = mandatory.get( label.intValue() );
                if ( propertyKeys != null )
                {
                    if ( keys == null )
                    {
                        keys = Primitive.intSet( capacity );
                    }
                    for ( int key : propertyKeys )
                    {
                        keys.add( key );
                    }
                }
            }
            return keys;
        }
    }

    static class RelationshipChecker extends Checker<RelationshipRecord,ConsistencyReport.RelationshipConsistencyReport>
    {
        private final PrimitiveIntObjectMap<int[]> mandatory;

        private RelationshipChecker( PrimitiveIntObjectMap<int[]> mandatory,
                OwningRecordCheck<RelationshipRecord,ConsistencyReport.RelationshipConsistencyReport> next )
        {
            super( next );
            this.mandatory = mandatory;
        }

        @Override
        PrimitiveIntSet mandatoryPropertiesFor( RelationshipRecord record,
                CheckerEngine<RelationshipRecord,ConsistencyReport.RelationshipConsistencyReport> engine,
                RecordAccess records )
        {
            int[] propertyKeys = mandatory.get( record.getType() );
            if ( propertyKeys != null )
            {
                PrimitiveIntSet keys = Primitive.intSet( propertyKeys.length );
                for ( int key : propertyKeys )
                {
                    keys.add( key );
                }
                return keys;
            }
            return null;
        }
    }

    static void reportMissingKeys( ConsistencyReport.PrimitiveConsistencyReport report, PrimitiveIntSet keys )
    {
        for ( PrimitiveIntIterator key = keys.iterator(); key.hasNext(); )
        {
            report.missingMandatoryProperty( key.next() );
        }
    }

    private static class ChainCheck<RECORD extends PrimitiveRecord,
            REPORT extends ConsistencyReport.PrimitiveConsistencyReport>
            implements ComparativeRecordChecker<RECORD,PropertyRecord,REPORT>
    {
        private static final int MAX_BLOCK_PER_RECORD_COUNT = 4;
        private final PrimitiveIntSet keys;

        public ChainCheck( PrimitiveIntSet keys )
        {
            this.keys = keys;
        }

        @Override
        public void checkReference( RECORD record, PropertyRecord property, CheckerEngine<RECORD,REPORT> engine,
                RecordAccess records )
        {
            for ( int key : keys( property ) )
            {
                keys.remove( key );
            }
            if ( Record.NO_NEXT_PROPERTY.is( property.getNextProp() ) )
            {
                if ( !keys.isEmpty() )
                {
                    reportMissingKeys( engine.report(), keys );
                }
            }
        }

        static int[] keys( PropertyRecord property )
        {
            int[] toStartWith = new int[MAX_BLOCK_PER_RECORD_COUNT];
            int index = 0;
            for ( PropertyBlock propertyBlock : property )
            {
                toStartWith[index++] = propertyBlock.getKeyIndexId();
            }
            return Arrays.copyOf( toStartWith, index );
        }
    }

    private static class SizeCounter implements PrimitiveIntObjectVisitor<int[],RuntimeException>
    {
        static int countSizeOf( PrimitiveIntObjectMap<int[]> map )
        {
            SizeCounter counter = new SizeCounter();
            map.visitEntries( counter );
            return counter.size;
        }

        private int size;

        @Override
        public boolean visited( int key, int[] ints ) throws RuntimeException
        {
            size += ints.length;
            return false;
        }
    }
}


File: community/consistency-check/src/test/java/org/neo4j/consistency/checking/SchemaRecordCheckTest.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.consistency.checking;

import org.junit.Test;

import org.neo4j.consistency.report.ConsistencyReport;
import org.neo4j.consistency.store.RecordAccessStub;
import org.neo4j.kernel.api.exceptions.schema.MalformedSchemaRuleException;
import org.neo4j.kernel.api.index.SchemaIndexProvider;
import org.neo4j.kernel.impl.store.SchemaStorage;
import org.neo4j.kernel.impl.store.UniquePropertyConstraintRule;
import org.neo4j.kernel.impl.store.record.DynamicRecord;
import org.neo4j.kernel.impl.store.record.IndexRule;
import org.neo4j.kernel.impl.store.record.LabelTokenRecord;
import org.neo4j.kernel.impl.store.record.PropertyKeyTokenRecord;
import org.neo4j.kernel.impl.store.record.SchemaRule;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyZeroInteractions;
import static org.mockito.Mockito.when;

public class SchemaRecordCheckTest
        extends RecordCheckTestBase<DynamicRecord, ConsistencyReport.SchemaConsistencyReport, SchemaRecordCheck>
{
    public SchemaRecordCheckTest()
    {
        super( new SchemaRecordCheck( configureSchemaStore() ),
                ConsistencyReport.SchemaConsistencyReport.class );
    }

    public static SchemaStorage configureSchemaStore()
    {
        return mock( SchemaStorage.class );
    }

    @Test
    public void shouldReportMalformedSchemaRule() throws Exception
    {
        // given
        DynamicRecord badRecord = inUse( new DynamicRecord( 0 ) );
        badRecord.setType( RecordAccessStub.SCHEMA_RECORD_TYPE );

        when( checker().ruleAccess.loadSingleSchemaRule( 0 ) ).thenThrow( new MalformedSchemaRuleException( "Bad Record" ) );

        // when
        ConsistencyReport.SchemaConsistencyReport report = check( badRecord );

        // then
        verify( report ).malformedSchemaRule();
    }

    @Test
    public void shouldReportInvalidLabelReferences() throws Exception
    {
        // given
        int schemaRuleId = 0;
        int labelId = 1;
        int propertyKeyId = 2;

        DynamicRecord record = inUse( dynamicRecord( schemaRuleId ) );
        SchemaIndexProvider.Descriptor providerDescriptor = new SchemaIndexProvider.Descriptor( "in-memory", "1.0" );
        IndexRule rule = IndexRule.indexRule( schemaRuleId, labelId, propertyKeyId, providerDescriptor );
        when( checker().ruleAccess.loadSingleSchemaRule( schemaRuleId ) ).thenReturn( rule );

        LabelTokenRecord labelTokenRecord = add ( notInUse( new LabelTokenRecord( labelId ) ) );
        add(inUse( new PropertyKeyTokenRecord( propertyKeyId ) ) );

        // when
        ConsistencyReport.SchemaConsistencyReport report = check( record );

        // then
        verify( report ).labelNotInUse( labelTokenRecord );
    }

    @Test
    public void shouldReportInvalidPropertyReferenceFromIndexRule() throws Exception
    {
        // given
        int schemaRuleId = 0;
        int labelId = 1;
        int propertyKeyId = 2;

        DynamicRecord record = inUse( dynamicRecord( schemaRuleId ) );
        SchemaIndexProvider.Descriptor providerDescriptor = new SchemaIndexProvider.Descriptor( "in-memory", "1.0" );
        IndexRule rule = IndexRule.indexRule( schemaRuleId, labelId, propertyKeyId, providerDescriptor );
        when( checker().ruleAccess.loadSingleSchemaRule( schemaRuleId ) ).thenReturn( rule );

        add( inUse( new LabelTokenRecord( labelId ) ) );
        PropertyKeyTokenRecord propertyKeyToken = add( notInUse( new PropertyKeyTokenRecord( propertyKeyId ) ) );

        // when
        ConsistencyReport.SchemaConsistencyReport report = check( record );

        // then
        verify( report ).propertyKeyNotInUse( propertyKeyToken );
    }

    @Test
    public void shouldReportInvalidPropertyReferenceFromUniquenessConstraintRule() throws Exception
    {
        // given
        int schemaRuleId = 0;
        int indexRuleId = 1;

        int labelId = 1;
        int propertyKeyId = 2;

        DynamicRecord record = inUse( dynamicRecord( schemaRuleId ) );

        UniquePropertyConstraintRule rule = UniquePropertyConstraintRule
                .uniquenessConstraintRule( schemaRuleId, labelId, propertyKeyId, indexRuleId );

        when( checker().ruleAccess.loadSingleSchemaRule( schemaRuleId ) ).thenReturn( rule );

        add( inUse( new LabelTokenRecord( labelId ) ) );
        PropertyKeyTokenRecord propertyKeyToken = add( notInUse( new PropertyKeyTokenRecord( propertyKeyId ) ) );

        // when
        ConsistencyReport.SchemaConsistencyReport report = check( record );

        // then
        verify( report ).propertyKeyNotInUse( propertyKeyToken );
    }

    @Test
    public void shouldReportUniquenessConstraintNotReferencingBack() throws Exception
    {
        // given
        int ruleId1 = 0;
        int ruleId2 = 1;
        int labelId = 1;
        int propertyKeyId = 2;

        DynamicRecord record1 = inUse( dynamicRecord( ruleId1 ) );
        DynamicRecord record2 = inUse( dynamicRecord( ruleId2 ) );

        SchemaIndexProvider.Descriptor providerDescriptor = new SchemaIndexProvider.Descriptor( "in-memory", "1.0" );

        IndexRule rule1 = IndexRule.constraintIndexRule( ruleId1, labelId, propertyKeyId, providerDescriptor, (long) ruleId2 );
        UniquePropertyConstraintRule rule2 = UniquePropertyConstraintRule
                .uniquenessConstraintRule( ruleId2, labelId, propertyKeyId, ruleId2 );

        when( checker().ruleAccess.loadSingleSchemaRule( ruleId1 ) ).thenReturn( rule1 );
        when( checker().ruleAccess.loadSingleSchemaRule( ruleId2 ) ).thenReturn( rule2 );

        add( inUse( new LabelTokenRecord( labelId ) ) );
        add( inUse( new PropertyKeyTokenRecord( propertyKeyId ) ) );

        // when
        check( record1 );
        check( record2 );
        SchemaRecordCheck obligationChecker = checker().forObligationChecking();
        check( obligationChecker, record1 );
        ConsistencyReport.SchemaConsistencyReport report = check( obligationChecker, record2 );

        // then
        verify( report ).uniquenessConstraintNotReferencingBack( record1 );
    }

    @Test
    public void shouldNotReportConstraintIndexRuleWithoutBackReference() throws Exception
    {
        // given
        int ruleId = 1;
        int labelId = 1;
        int propertyKeyId = 2;

        DynamicRecord record = inUse( dynamicRecord( ruleId ) );

        SchemaIndexProvider.Descriptor providerDescriptor = new SchemaIndexProvider.Descriptor( "in-memory", "1.0" );

        IndexRule rule = IndexRule.constraintIndexRule( ruleId, labelId, propertyKeyId, providerDescriptor, null );

        when( checker().ruleAccess.loadSingleSchemaRule( ruleId ) ).thenReturn( rule );

        add( inUse( new LabelTokenRecord( labelId ) ) );
        add( inUse( new PropertyKeyTokenRecord( propertyKeyId ) ) );

        // when
        check( record );
        SchemaRecordCheck obligationChecker = checker().forObligationChecking();
        ConsistencyReport.SchemaConsistencyReport report = check( obligationChecker, record );

        // then
        verifyZeroInteractions( report );
    }

    @Test
    public void shouldReportTwoUniquenessConstraintsReferencingSameIndex() throws Exception
    {
        // given
        int ruleId1 = 0;
        int ruleId2 = 1;
        int labelId = 1;
        int propertyKeyId = 2;

        DynamicRecord record1 = inUse( dynamicRecord( ruleId1 ) );
        DynamicRecord record2 = inUse( dynamicRecord( ruleId2 ) );

        UniquePropertyConstraintRule rule1 = UniquePropertyConstraintRule
                .uniquenessConstraintRule( ruleId1, labelId, propertyKeyId, ruleId2 );
        UniquePropertyConstraintRule rule2 = UniquePropertyConstraintRule
                .uniquenessConstraintRule( ruleId2, labelId, propertyKeyId, ruleId2 );

        when( checker().ruleAccess.loadSingleSchemaRule( ruleId1 ) ).thenReturn( rule1 );
        when( checker().ruleAccess.loadSingleSchemaRule( ruleId2 ) ).thenReturn( rule2 );

        add( inUse( new LabelTokenRecord( labelId ) ) );
        add( inUse( new PropertyKeyTokenRecord( propertyKeyId ) ) );

        // when
        check( record1 );
        ConsistencyReport.SchemaConsistencyReport report = check( record2 );

        // then
        verify( report ).duplicateObligation( record1 );
    }

    @Test
    public void shouldReportUnreferencedUniquenessConstraint() throws Exception
    {
        // given
        int ruleId = 0;
        int labelId = 1;
        int propertyKeyId = 2;

        DynamicRecord record = inUse( dynamicRecord( ruleId ) );

        UniquePropertyConstraintRule rule = UniquePropertyConstraintRule
                .uniquenessConstraintRule( ruleId, labelId, propertyKeyId, ruleId );

        when( checker().ruleAccess.loadSingleSchemaRule( ruleId ) ).thenReturn( rule );

        add( inUse( new LabelTokenRecord( labelId ) ) );
        add( inUse( new PropertyKeyTokenRecord( propertyKeyId ) ) );

        // when
        check( record );
        SchemaRecordCheck obligationChecker = checker().forObligationChecking();
        ConsistencyReport.SchemaConsistencyReport report = check( obligationChecker, record );

        // then
        verify( report ).missingObligation( SchemaRule.Kind.CONSTRAINT_INDEX_RULE );
    }

    @Test
    public void shouldReportConstraintIndexNotReferencingBack() throws Exception
    {
        // given
        int ruleId1 = 0;
        int ruleId2 = 1;
        int labelId = 1;
        int propertyKeyId = 2;

        DynamicRecord record1 = inUse( dynamicRecord( ruleId1 ) );
        DynamicRecord record2 = inUse( dynamicRecord( ruleId2) );

        SchemaIndexProvider.Descriptor providerDescriptor = new SchemaIndexProvider.Descriptor( "in-memory", "1.0" );

        IndexRule rule1 = IndexRule.constraintIndexRule( ruleId1, labelId, propertyKeyId, providerDescriptor, (long)
                ruleId1 );
        UniquePropertyConstraintRule rule2 = UniquePropertyConstraintRule
                .uniquenessConstraintRule( ruleId2, labelId, propertyKeyId, ruleId1 );

        when( checker().ruleAccess.loadSingleSchemaRule( ruleId1 ) ).thenReturn( rule1 );
        when( checker().ruleAccess.loadSingleSchemaRule( ruleId2 ) ).thenReturn( rule2 );

        add( inUse( new LabelTokenRecord( labelId ) ) );
        add( inUse( new PropertyKeyTokenRecord( propertyKeyId ) ) );

        // when
        check( record1 );
        check( record2 );
        SchemaRecordCheck obligationChecker = checker().forObligationChecking();
        ConsistencyReport.SchemaConsistencyReport report = check( obligationChecker, record1 );
        check( obligationChecker, record2 );

        // then
        verify( report ).constraintIndexRuleNotReferencingBack( record2 );
    }

    @Test
    public void shouldReportTwoConstraintIndexesReferencingSameConstraint() throws Exception
    {
        // given
        int ruleId1 = 0;
        int ruleId2 = 1;
        int labelId = 1;
        int propertyKeyId = 2;

        DynamicRecord record1 = inUse( dynamicRecord( ruleId1 ) );
        DynamicRecord record2 = inUse( dynamicRecord( ruleId2 ) );

        SchemaIndexProvider.Descriptor providerDescriptor = new SchemaIndexProvider.Descriptor( "in-memory", "1.0" );

        IndexRule rule1 = IndexRule.constraintIndexRule( ruleId1, labelId, propertyKeyId, providerDescriptor, (long) ruleId1 );
        IndexRule rule2 = IndexRule.constraintIndexRule( ruleId2, labelId, propertyKeyId, providerDescriptor, (long) ruleId1 );

        when( checker().ruleAccess.loadSingleSchemaRule( ruleId1 ) ).thenReturn( rule1 );
        when( checker().ruleAccess.loadSingleSchemaRule( ruleId2 ) ).thenReturn( rule2 );

        add( inUse( new LabelTokenRecord( labelId ) ) );
        add( inUse( new PropertyKeyTokenRecord( propertyKeyId ) ) );

        // when
        check( record1 );
        ConsistencyReport.SchemaConsistencyReport report = check( record2 );

        // then
        verify( report ).duplicateObligation( record1 );
    }

    @Test
    public void shouldReportUnreferencedConstraintIndex() throws Exception
    {
        // given
        int ruleId = 0;
        int labelId = 1;
        int propertyKeyId = 2;

        DynamicRecord record = inUse( dynamicRecord( ruleId ) );

        SchemaIndexProvider.Descriptor providerDescriptor = new SchemaIndexProvider.Descriptor( "in-memory", "1.0" );

        IndexRule rule = IndexRule.constraintIndexRule( ruleId, labelId, propertyKeyId, providerDescriptor, (long) ruleId );

        when( checker().ruleAccess.loadSingleSchemaRule( ruleId ) ).thenReturn( rule );

        add( inUse( new LabelTokenRecord( labelId ) ) );
        add( inUse( new PropertyKeyTokenRecord( propertyKeyId ) ) );

        // when
        check( record );
        SchemaRecordCheck obligationChecker = checker().forObligationChecking();
        ConsistencyReport.SchemaConsistencyReport report = check( obligationChecker, record );

        // then
        verify( report ).missingObligation( SchemaRule.Kind.UNIQUENESS_CONSTRAINT );
    }

    @Test
    public void shouldReportTwoIndexRulesWithDuplicateContent() throws Exception
    {
        // given
        int ruleId1 = 0;
        int ruleId2 = 1;
        int labelId = 1;
        int propertyKeyId = 2;

        DynamicRecord record1 = inUse( dynamicRecord( ruleId1 ) );
        DynamicRecord record2 = inUse( dynamicRecord( ruleId2 ) );

        SchemaIndexProvider.Descriptor providerDescriptor = new SchemaIndexProvider.Descriptor( "in-memory", "1.0" );

        IndexRule rule1 = IndexRule.constraintIndexRule( ruleId1, labelId, propertyKeyId, providerDescriptor, (long) ruleId1 );
        IndexRule rule2 = IndexRule.constraintIndexRule( ruleId2, labelId, propertyKeyId, providerDescriptor, (long) ruleId2 );

        when( checker().ruleAccess.loadSingleSchemaRule( ruleId1 ) ).thenReturn( rule1 );
        when( checker().ruleAccess.loadSingleSchemaRule( ruleId2 ) ).thenReturn( rule2 );

        add( inUse( new LabelTokenRecord( labelId ) ) );
        add( inUse( new PropertyKeyTokenRecord( propertyKeyId ) ) );

        // when
        check( record1 );
        ConsistencyReport.SchemaConsistencyReport report = check( record2 );

        // then
        verify( report ).duplicateRuleContent( record1 );
    }


    private DynamicRecord dynamicRecord( long id )
    {
        DynamicRecord record = new DynamicRecord( id );
        record.setType( RecordAccessStub.SCHEMA_RECORD_TYPE );
        return record;
    }
}


File: community/consistency-check/src/test/java/org/neo4j/consistency/checking/SchemaRuleContentTest.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.consistency.checking;

import org.junit.Test;

import org.neo4j.kernel.api.index.SchemaIndexProvider;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotEquals;

import static org.neo4j.kernel.impl.store.UniquePropertyConstraintRule.uniquenessConstraintRule;
import static org.neo4j.kernel.impl.store.record.IndexRule.constraintIndexRule;
import static org.neo4j.kernel.impl.store.record.IndexRule.indexRule;

public class SchemaRuleContentTest
{
    @Test
    public void shouldReportIndexRulesWithSameLabelAndPropertyAsEqual() throws Exception
    {
        // given
        SchemaIndexProvider.Descriptor descriptor = new SchemaIndexProvider.Descriptor( "in-memory", "1.0" );
        SchemaRuleContent rule1 = new SchemaRuleContent( indexRule( 0, 1, 2, descriptor ) );
        SchemaRuleContent rule2 = new SchemaRuleContent( indexRule( 1, 1, 2, descriptor ) );

        // then
        assertReflectivelyEquals( rule1, rule2 );
    }

    @Test
    public void shouldReportConstraintIndexRulesWithSameLabelAndPropertyAsEqual() throws Exception
    {
        // given
        SchemaIndexProvider.Descriptor descriptor = new SchemaIndexProvider.Descriptor( "in-memory", "1.0" );
        SchemaRuleContent rule1 = new SchemaRuleContent( constraintIndexRule( 0, 1, 2, descriptor, null ) );
        SchemaRuleContent rule2 = new SchemaRuleContent( constraintIndexRule( 1, 1, 2, descriptor, 4l ) );

        // then
        assertReflectivelyEquals( rule1, rule2 );
    }

    @Test
    public void shouldReportUniquenessConstraintRulesWithSameLabelAndPropertyAsEqual() throws Exception
    {
        // given
        SchemaRuleContent rule1 = new SchemaRuleContent( uniquenessConstraintRule( 0, 1, 2, 0 ) );
        SchemaRuleContent rule2 = new SchemaRuleContent( uniquenessConstraintRule( 1, 1, 2, 0 ) );

        // then
        assertReflectivelyEquals( rule1, rule2 );
    }

    @Test
    public void shouldReportIndexRulesWithSameLabelButDifferentPropertyAsNotEqual() throws Exception
    {
        // given
        SchemaIndexProvider.Descriptor descriptor = new SchemaIndexProvider.Descriptor( "in-memory", "1.0" );
        SchemaRuleContent rule1 = new SchemaRuleContent( indexRule( 0, 1, 2, descriptor ) );
        SchemaRuleContent rule2 = new SchemaRuleContent( indexRule( 1, 1, 3, descriptor ) );

        // then
        assertReflectivelyNotEquals( rule1, rule2 );
    }

    @Test
    public void shouldReportIndexRulesWithSamePropertyButDifferentLabelAsNotEqual() throws Exception
    {
        // given
        SchemaIndexProvider.Descriptor descriptor = new SchemaIndexProvider.Descriptor( "in-memory", "1.0" );
        SchemaRuleContent rule1 = new SchemaRuleContent( indexRule( 0, 1, 2, descriptor ) );
        SchemaRuleContent rule2 = new SchemaRuleContent( indexRule( 1, 4, 2, descriptor ) );

        // then
        assertReflectivelyNotEquals( rule1, rule2 );
    }

    @Test
    public void shouldReportIndexRuleAndUniquenessConstraintAsNotEqual() throws Exception
    {
        // given
        SchemaIndexProvider.Descriptor descriptor = new SchemaIndexProvider.Descriptor( "in-memory", "1.0" );
        SchemaRuleContent rule1 = new SchemaRuleContent( indexRule( 0, 1, 2, descriptor ) );
        SchemaRuleContent rule2 = new SchemaRuleContent( uniquenessConstraintRule( 1, 1, 2, 0 ) );

        // then
        assertReflectivelyNotEquals( rule1, rule2 );
    }

    @Test
    public void shouldReportConstraintIndexRuleAndUniquenessConstraintAsNotEqual() throws Exception
    {
        // given
        SchemaIndexProvider.Descriptor descriptor = new SchemaIndexProvider.Descriptor( "in-memory", "1.0" );
        SchemaRuleContent rule1 = new SchemaRuleContent( constraintIndexRule( 0, 1, 2, descriptor, null ) );
        SchemaRuleContent rule2 = new SchemaRuleContent( uniquenessConstraintRule( 1, 1, 2, 0 ) );

        // then
        assertReflectivelyNotEquals( rule1, rule2 );
    }

    @Test
    public void shouldReportIndexRuleAndUniqueIndexRuleWithSameLabelAndPropertyAsEqual() throws Exception
    {
        // given
        SchemaIndexProvider.Descriptor descriptor = new SchemaIndexProvider.Descriptor( "in-memory", "1.0" );
        SchemaRuleContent rule1 = new SchemaRuleContent( indexRule( 0, 1, 2, descriptor ) );
        SchemaRuleContent rule2 = new SchemaRuleContent( constraintIndexRule( 1, 1, 2, descriptor, null ) );

        // then
        assertReflectivelyEquals( rule1, rule2 );
    }

    private static void assertReflectivelyEquals( Object lhs, Object rhs )
    {
        assertEquals( "lhs should be equal to rhs", lhs, rhs );
        assertEquals( "rhs should be equal to lhs", rhs, lhs );
        assertEquals( "hash codes should be equal", lhs.hashCode(), rhs.hashCode() );
    }

    private static void assertReflectivelyNotEquals( Object lhs, Object rhs )
    {
        assertNotEquals( "lhs should not be equal to rhs", lhs, rhs );
        assertNotEquals( "rhs should not be equal to lhs", rhs, lhs );
    }
}


File: community/consistency-check/src/test/java/org/neo4j/consistency/checking/full/FullCheckIntegrationTest.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.consistency.checking.full;

import org.junit.Ignore;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TestRule;
import org.junit.runner.Description;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;
import org.junit.runners.Parameterized.Parameter;
import org.junit.runners.Parameterized.Parameters;
import org.junit.runners.model.Statement;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Set;

import org.neo4j.collection.primitive.PrimitiveLongCollections;
import org.neo4j.collection.primitive.PrimitiveLongSet;
import org.neo4j.consistency.RecordType;
import org.neo4j.consistency.checking.GraphStoreFixture;
import org.neo4j.consistency.report.ConsistencySummaryStatistics;
import org.neo4j.function.Supplier;
import org.neo4j.graphdb.Direction;
import org.neo4j.graphdb.GraphDatabaseService;
import org.neo4j.graphdb.Node;
import org.neo4j.helpers.Pair;
import org.neo4j.helpers.UTF8;
import org.neo4j.helpers.progress.ProgressMonitorFactory;
import org.neo4j.kernel.GraphDatabaseAPI;
import org.neo4j.kernel.api.direct.DirectStoreAccess;
import org.neo4j.kernel.api.exceptions.TransactionFailureException;
import org.neo4j.kernel.api.exceptions.index.IndexCapacityExceededException;
import org.neo4j.kernel.api.index.IndexAccessor;
import org.neo4j.kernel.api.index.IndexConfiguration;
import org.neo4j.kernel.api.index.IndexDescriptor;
import org.neo4j.kernel.api.index.IndexPopulator;
import org.neo4j.kernel.api.index.IndexUpdater;
import org.neo4j.kernel.api.index.NodePropertyUpdate;
import org.neo4j.kernel.api.index.SchemaIndexProvider;
import org.neo4j.kernel.api.labelscan.LabelScanStore;
import org.neo4j.kernel.api.labelscan.NodeLabelUpdate;
import org.neo4j.kernel.configuration.Config;
import org.neo4j.kernel.impl.api.index.IndexUpdateMode;
import org.neo4j.kernel.impl.api.index.sampling.IndexSamplingConfig;
import org.neo4j.kernel.impl.core.ThreadToStatementContextBridge;
import org.neo4j.kernel.impl.store.AbstractDynamicStore;
import org.neo4j.kernel.impl.store.NodeLabelsField;
import org.neo4j.kernel.impl.store.PreAllocatedRecords;
import org.neo4j.kernel.impl.store.PropertyType;
import org.neo4j.kernel.impl.store.RecordStore;
import org.neo4j.kernel.impl.store.SchemaStorage;
import org.neo4j.kernel.impl.store.StoreAccess;
import org.neo4j.kernel.impl.store.UniquePropertyConstraintRule;
import org.neo4j.kernel.impl.store.record.DynamicRecord;
import org.neo4j.kernel.impl.store.record.IndexRule;
import org.neo4j.kernel.impl.store.record.LabelTokenRecord;
import org.neo4j.kernel.impl.store.record.NeoStoreRecord;
import org.neo4j.kernel.impl.store.record.NodeRecord;
import org.neo4j.kernel.impl.store.record.PropertyBlock;
import org.neo4j.kernel.impl.store.record.PropertyRecord;
import org.neo4j.kernel.impl.store.record.RecordSerializer;
import org.neo4j.kernel.impl.store.record.RelationshipGroupRecord;
import org.neo4j.kernel.impl.store.record.RelationshipRecord;
import org.neo4j.kernel.impl.store.record.RelationshipTypeTokenRecord;
import org.neo4j.kernel.impl.store.record.SchemaRule;
import org.neo4j.kernel.impl.util.Bits;
import org.neo4j.logging.FormattedLog;
import org.neo4j.unsafe.batchinsert.LabelScanWriter;

import static java.util.Arrays.asList;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.neo4j.consistency.checking.RecordCheckTestBase.inUse;
import static org.neo4j.consistency.checking.RecordCheckTestBase.notInUse;
import static org.neo4j.consistency.checking.full.ExecutionOrderIntegrationTest.config;
import static org.neo4j.consistency.checking.full.FullCheckIntegrationTest.ConsistencySummaryVerifier.on;
import static org.neo4j.consistency.checking.schema.IndexRules.loadAllIndexRules;
import static org.neo4j.graphdb.DynamicLabel.label;
import static org.neo4j.graphdb.DynamicRelationshipType.withName;
import static org.neo4j.helpers.collection.IteratorUtil.asIterable;
import static org.neo4j.helpers.collection.IteratorUtil.iterator;
import static org.neo4j.kernel.api.ReadOperations.ANY_LABEL;
import static org.neo4j.kernel.api.ReadOperations.ANY_RELATIONSHIP_TYPE;
import static org.neo4j.kernel.api.labelscan.NodeLabelUpdate.labelChanges;
import static org.neo4j.kernel.impl.store.AbstractDynamicStore.readFullByteArrayFromHeavyRecords;
import static org.neo4j.kernel.impl.store.DynamicArrayStore.allocateFromNumbers;
import static org.neo4j.kernel.impl.store.DynamicArrayStore.getRightArray;
import static org.neo4j.kernel.impl.store.DynamicNodeLabels.dynamicPointer;
import static org.neo4j.kernel.impl.store.LabelIdArray.prependNodeId;
import static org.neo4j.kernel.impl.store.PropertyType.ARRAY;
import static org.neo4j.kernel.impl.store.record.Record.NO_LABELS_FIELD;
import static org.neo4j.kernel.impl.store.record.Record.NO_NEXT_PROPERTY;
import static org.neo4j.kernel.impl.store.record.Record.NO_NEXT_RELATIONSHIP;
import static org.neo4j.kernel.impl.store.record.Record.NO_PREV_RELATIONSHIP;
import static org.neo4j.kernel.impl.util.Bits.bits;
import static org.neo4j.test.Property.property;
import static org.neo4j.test.Property.set;

@RunWith( Parameterized.class )
public class FullCheckIntegrationTest
{
    @Parameter
    public TaskExecutionOrder taskExecutionOrder;

    @Parameters( name = "execution_order={0}" )
    public static Iterable<Object[]> taskExecutions()
    {
        return Arrays.asList( new Object[][]{
                {TaskExecutionOrder.SINGLE_THREADED},
                {TaskExecutionOrder.MULTI_PASS}
        } );
    }

    @Test
    public void shouldCheckConsistencyOfAConsistentStore() throws Exception
    {
        // when
        ConsistencySummaryStatistics result = check();

        // then
        assertEquals( result.toString(), 0, result.getTotalInconsistencyCount() );
    }

    @Test
    @Ignore("Support for checking NeoStore needs to be added")
    public void shouldReportNeoStoreInconsistencies() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                NeoStoreRecord record = new NeoStoreRecord();
                record.setNextProp( next.property() );
                tx.update( record );
                // We get exceptions when only the above happens in a transaction...
                tx.create( new NodeRecord( next.node(), false, -1, -1 ) );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.NEO_STORE, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportNodeInconsistencies() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                tx.create( new NodeRecord( next.node(), false, next.relationship(), -1 ) );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.NODE, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportInlineNodeLabelInconsistencies() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                NodeRecord nodeRecord = new NodeRecord( next.node(), false, -1, -1 );
                NodeLabelsField.parseLabelsField( nodeRecord ).add( 10, null, null );
                tx.create( nodeRecord );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.NODE, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportNodeDynamicLabelContainingUnknownLabelAsNodeInconsistency() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                NodeRecord nodeRecord = new NodeRecord( next.node(), false, -1, -1 );
                DynamicRecord record = inUse( new DynamicRecord( next.nodeLabel() ) );
                Collection<DynamicRecord> newRecords = new ArrayList<>();
                allocateFromNumbers( newRecords, prependNodeId( nodeRecord.getLongId(), new long[]{42l} ),
                        iterator( record ), new PreAllocatedRecords( 60 ) );
                nodeRecord.setLabelField( dynamicPointer( newRecords ), newRecords );

                tx.create( nodeRecord );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.NODE, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldNotReportAnythingForNodeWithConsistentChainOfDynamicRecordsWithLabels() throws Exception
    {
        // given
        assertEquals( 3, chainOfDynamicRecordsWithLabelsForANode( 130 ).first().size() );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        assertTrue( "should be consistent", stats.isConsistent() );
    }

    @Test @Ignore("2013-07-17 Revisit once we store sorted label ids")
    public void shouldReportOrphanNodeDynamicLabelAsInconsistency() throws Exception
    {
        // given
        final List<DynamicRecord> chain = chainOfDynamicRecordsWithLabelsForANode( 130 ).first();
        assertEquals( 3, chain.size() );
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                DynamicRecord record1 = inUse( new DynamicRecord( chain.get( 0 ).getId() ) );
                DynamicRecord record2 = notInUse( new DynamicRecord( chain.get( 1 ).getId() ) );
                long[] data = (long[]) getRightArray( readFullByteArrayFromHeavyRecords( chain, ARRAY ) );
                PreAllocatedRecords allocator = new PreAllocatedRecords( 60 );
                allocateFromNumbers( new ArrayList<DynamicRecord>(), Arrays.copyOf( data, 11 ),
                        iterator( record1 ), allocator );

                NodeRecord before = inUse( new NodeRecord( data[0], false, -1, -1 ) );
                NodeRecord after = inUse( new NodeRecord( data[0], false, -1, -1 ) );
                before.setLabelField( dynamicPointer( asList( record1 ) ), chain );
                after.setLabelField( dynamicPointer( asList( record1 ) ), asList( record1, record2 ) );
                tx.update( before, after );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.NODE_DYNAMIC_LABEL, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportLabelScanStoreInconsistencies() throws Exception
    {
        // given
        GraphStoreFixture.IdGenerator idGenerator = fixture.idGenerator();
        long nodeId1 = idGenerator.node();
        long labelId = idGenerator.label() - 1;

        LabelScanStore labelScanStore = fixture.directStoreAccess().labelScanStore();
        Iterable<NodeLabelUpdate> nodeLabelUpdates = asIterable(
                labelChanges( nodeId1, new long[]{}, new long[]{labelId} )
        );
        write( labelScanStore, nodeLabelUpdates );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.LABEL_SCAN_DOCUMENT, 1 )
                   .andThatsAllFolks();
    }

    private void write( LabelScanStore labelScanStore, Iterable<NodeLabelUpdate> nodeLabelUpdates )
            throws IOException, IndexCapacityExceededException
    {
        try ( LabelScanWriter writer = labelScanStore.newWriter() )
        {
            for ( NodeLabelUpdate update : nodeLabelUpdates )
            {
                writer.write( update );
            }
        }
    }

    @Test
    public void shouldReportIndexInconsistencies() throws Exception
    {
        // given
        for ( Long indexedNodeId : indexedNodes )
        {
            fixture.directStoreAccess().nativeStores().getNodeStore().forceUpdateRecord(
                    notInUse( new NodeRecord( indexedNodeId, false, -1, -1 ) ) );
        }

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.INDEX, 1 )
                   .verify( RecordType.LABEL_SCAN_DOCUMENT, 1 )
                   .verify( RecordType.COUNTS, 3 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldNotReportIndexInconsistenciesIfIndexIsFailed() throws Exception
    {
        // this test fails all indexes, and then destroys a record and makes sure we only get a failure for
        // the label scan store but not for any index

        // given
        DirectStoreAccess storeAccess = fixture.directStoreAccess();

        // fail all indexes
        Iterator<IndexRule> rules = new SchemaStorage( storeAccess.nativeStores().getSchemaStore() ).allIndexRules();
        while ( rules.hasNext() )
        {
            IndexRule rule = rules.next();
            IndexDescriptor descriptor = new IndexDescriptor( rule.getLabel(), rule.getPropertyKey() );
            IndexConfiguration indexConfig = new IndexConfiguration( false );
            IndexSamplingConfig samplingConfig = new IndexSamplingConfig( new Config() );
            IndexPopulator populator =
                storeAccess.indexes().getPopulator( rule.getId(), descriptor, indexConfig, samplingConfig );
            populator.markAsFailed( "Oh noes! I was a shiny index and then I was failed" );
            populator.close( false );

        }

        for ( Long indexedNodeId : indexedNodes )
        {
            storeAccess.nativeStores().getNodeStore().forceUpdateRecord(
                    notInUse( new NodeRecord( indexedNodeId, false, -1, -1 ) ) );
        }

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.LABEL_SCAN_DOCUMENT, 1 )
                   .verify( RecordType.COUNTS, 3 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportMismatchedLabels() throws Exception
    {
        final List<Integer> labels = new ArrayList<>();

        // given
        final Pair<List<DynamicRecord>, List<Integer>> pair = chainOfDynamicRecordsWithLabelsForANode( 3 );
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                NodeRecord node = new NodeRecord( 42, false, -1, -1 );
                node.setInUse( true );
                List<DynamicRecord> dynamicRecords;
                dynamicRecords = pair.first();
                labels.addAll( pair.other() );
                node.setLabelField( dynamicPointer( dynamicRecords ), dynamicRecords );
                tx.create( node );

            }
        } );

        long[] before = asArray( labels );
        labels.remove( 1 );
        long[] after = asArray( labels );

        write( fixture.directStoreAccess().labelScanStore(), asList( labelChanges( 42, before, after ) ) );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.NODE, 1 )
                   .andThatsAllFolks();
    }

    private long[] asArray( List<? extends Number> in )
    {
        long[] longs = new long[in.size()];
        for ( int i = 0; i < in.size(); i++ )
        {
            longs[i] = in.get( i ).longValue();
        }
        return longs;
    }

    private PrimitiveLongSet asPrimitiveLongSet( List<? extends Number> in )
    {
        return PrimitiveLongCollections.setOf( asArray( in ) );
    }

    @Test
    public void shouldReportMismatchedInlinedLabels() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                NodeRecord node = new NodeRecord( 42, false, -1, -1 );
                node.setInUse( true );
                node.setLabelField( inlinedLabelsLongRepresentation( label1, label2 ), Collections.<DynamicRecord>emptySet() );
                tx.create( node );
            }
        } );

        write( fixture.directStoreAccess().labelScanStore(), asList( labelChanges( 42, new long[]{label1, label2}, new long[]{label1} ) ) );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.NODE, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportNodesThatAreNotIndexed() throws Exception
    {
        // given
        IndexSamplingConfig samplingConfig = new IndexSamplingConfig( new Config() );
        for ( IndexRule indexRule : loadAllIndexRules( fixture.directStoreAccess().nativeStores().getSchemaStore() ) )
        {
            IndexAccessor accessor = fixture.directStoreAccess().indexes().getOnlineAccessor(
                    indexRule.getId(), new IndexConfiguration( indexRule.isConstraintIndex() ), samplingConfig );
            IndexUpdater updater = accessor.newUpdater( IndexUpdateMode.ONLINE );
            updater.remove( asPrimitiveLongSet( indexedNodes ) );
            updater.close();
            accessor.close();
        }

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.NODE, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportNodesWithDuplicatePropertyValueInUniqueIndex() throws Exception
    {
        // given
        IndexConfiguration indexConfig = new IndexConfiguration( false );
        IndexSamplingConfig samplingConfig = new IndexSamplingConfig( new Config() );
        for ( IndexRule indexRule : loadAllIndexRules( fixture.directStoreAccess().nativeStores().getSchemaStore() ) )
        {
            IndexAccessor accessor = fixture.directStoreAccess()
                                            .indexes()
                                            .getOnlineAccessor( indexRule.getId(), indexConfig, samplingConfig );
            IndexUpdater updater = accessor.newUpdater( IndexUpdateMode.ONLINE );
            updater.process( NodePropertyUpdate.add( 42, 0, "value", new long[]{3} ) );
            updater.close();
            accessor.close();
        }

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.NODE, 1 )
                   .verify( RecordType.INDEX, 2 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportMissingMandatoryNodeProperty() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                    GraphStoreFixture.IdGenerator next )
            {
                // structurally correct, but does not have the 'mandatory' property with the 'draconian' label
                NodeRecord node = new NodeRecord( next.node(), false, -1, next.property() );
                node.setInUse( true );
                node.setLabelField( inlinedLabelsLongRepresentation( draconian ),
                        Collections.<DynamicRecord>emptySet() );
                PropertyRecord property = new PropertyRecord( node.getNextProp(), node );
                property.setInUse( true );
                PropertyBlock block = new PropertyBlock();
                block.setSingleBlock( key | (((long) PropertyType.INT.intValue()) << 24) | (1337L << 28) );
                property.addPropertyBlock( block );
                tx.create( node );
                tx.create( property );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.NODE, 1 )
                .andThatsAllFolks();
    }

    @Test
    public void shouldReportMissingMandatoryRelationshipProperty() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                    GraphStoreFixture.IdGenerator next )
            {
                long nodeId1 = next.node();
                long nodeId2 = next.node();
                long relId = next.relationship();
                long propId = next.property();

                NodeRecord node1 = new NodeRecord( nodeId1, true, false, relId, NO_NEXT_PROPERTY.intValue(),
                        NO_LABELS_FIELD.intValue() );
                NodeRecord node2 = new NodeRecord( nodeId2, true, false, relId, NO_NEXT_PROPERTY.intValue(),
                        NO_LABELS_FIELD.intValue() );

                // structurally correct, but does not have the 'mandatory' property with the 'M' rel type
                RelationshipRecord relationship = new RelationshipRecord( relId, true, nodeId1, nodeId2, M,
                        NO_PREV_RELATIONSHIP.intValue(), NO_NEXT_RELATIONSHIP.intValue(),
                        NO_PREV_RELATIONSHIP.intValue(), NO_NEXT_RELATIONSHIP.intValue(), true, true );
                relationship.setNextProp( propId );

                PropertyRecord property = new PropertyRecord( propId, relationship );
                property.setInUse( true );
                PropertyBlock block = new PropertyBlock();
                block.setSingleBlock( key | (((long) PropertyType.INT.intValue()) << 24) | (1337L << 28) );
                property.addPropertyBlock( block );

                tx.create( node1 );
                tx.create( node2 );
                tx.create( relationship );
                tx.create( property );
                tx.incrementRelationshipCount( ANY_LABEL, ANY_RELATIONSHIP_TYPE, ANY_LABEL, 1 );
                tx.incrementRelationshipCount( ANY_LABEL, M, ANY_LABEL, 1 );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.RELATIONSHIP, 1 )
                .andThatsAllFolks();
    }

    private long inlinedLabelsLongRepresentation( long... labelIds )
    {
        long header = (long) labelIds.length << 36;
        byte bitsPerLabel = (byte) (36 / labelIds.length);
        Bits bits = bits( 5 );
        for ( long labelId : labelIds )
        {
            bits.put( labelId, bitsPerLabel );
        }
        return header | bits.getLongs()[0];
    }

    @Test
    public void shouldReportCyclesInDynamicRecordsWithLabels() throws Exception
    {
        // given
        final List<DynamicRecord> chain = chainOfDynamicRecordsWithLabelsForANode( 176/*3 full records*/ ).first();
        assertEquals( "number of records in chain", 3, chain.size() );
        assertEquals( "all records full", chain.get( 0 ).getLength(), chain.get( 2 ).getLength() );
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                long nodeId = ((long[]) getRightArray( readFullByteArrayFromHeavyRecords( chain, ARRAY ) ))[0];
                NodeRecord before = inUse( new NodeRecord( nodeId, false, -1, -1 ) );
                NodeRecord after = inUse( new NodeRecord( nodeId, false, -1, -1 ) );
                DynamicRecord record1 = chain.get( 0 ).clone();
                DynamicRecord record2 = chain.get( 1 ).clone();
                DynamicRecord record3 = chain.get( 2 ).clone();

                record3.setNextBlock( record2.getId() );
                before.setLabelField( dynamicPointer( chain ), chain );
                after.setLabelField( dynamicPointer( chain ), asList( record1, record2, record3 ) );
                tx.update( before, after );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.NODE, 1 )
                   .verify( RecordType.COUNTS, 177 )
                   .andThatsAllFolks();
    }

    private Pair<List<DynamicRecord>, List<Integer>> chainOfDynamicRecordsWithLabelsForANode( int labelCount ) throws TransactionFailureException
    {
        final long[] labels = new long[labelCount+1]; // allocate enough labels to need three records
        final List<Integer> createdLabels = new ArrayList<>(  );
        for ( int i = 1/*leave space for the node id*/; i < labels.length; i++ )
        {
            final int offset = i;
            fixture.apply( new GraphStoreFixture.Transaction()
            { // Neo4j can create no more than one label per transaction...
                @Override
                protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                                GraphStoreFixture.IdGenerator next )
                {
                    Integer label = next.label();
                    tx.nodeLabel( (int) (labels[offset] = label), "label:" + offset );
                    createdLabels.add( label );
                }
            } );
        }
        final List<DynamicRecord> chain = new ArrayList<>();
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                NodeRecord nodeRecord = new NodeRecord( next.node(), false, -1, -1 );
                DynamicRecord record1 = inUse( new DynamicRecord( next.nodeLabel() ) );
                DynamicRecord record2 = inUse( new DynamicRecord( next.nodeLabel() ) );
                DynamicRecord record3 = inUse( new DynamicRecord( next.nodeLabel() ) );
                labels[0] = nodeRecord.getLongId(); // the first id should not be a label id, but the id of the node
                PreAllocatedRecords allocator = new PreAllocatedRecords( 60 );
                allocateFromNumbers( chain, labels, iterator( record1, record2, record3 ), allocator );

                nodeRecord.setLabelField( dynamicPointer( chain ), chain );

                tx.create( nodeRecord );
            }
        } );
        return Pair.of( chain, createdLabels );
    }

    @Test
    public void shouldReportNodeDynamicLabelContainingDuplicateLabelAsNodeInconsistency() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                tx.nodeLabel( 42, "Label" );

                NodeRecord nodeRecord = new NodeRecord( next.node(), false, -1, -1 );
                DynamicRecord record = inUse( new DynamicRecord( next.nodeLabel() ) );
                Collection<DynamicRecord> newRecords = new ArrayList<>();
                allocateFromNumbers( newRecords,
                        prependNodeId( nodeRecord.getLongId(), new long[]{42l, 42l} ),
                        iterator( record ), new PreAllocatedRecords( 60 ) );
                nodeRecord.setLabelField( dynamicPointer( newRecords ), newRecords );

                tx.create( nodeRecord );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.NODE, 1 )
                   .verify( RecordType.COUNTS, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportOrphanedNodeDynamicLabelAsNodeInconsistency() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                tx.nodeLabel( 42, "Label" );

                NodeRecord nodeRecord = new NodeRecord( next.node(), false, -1, -1 );
                DynamicRecord record = inUse( new DynamicRecord( next.nodeLabel() ) );
                Collection<DynamicRecord> newRecords = new ArrayList<>();
                allocateFromNumbers( newRecords, prependNodeId( next.node(), new long[]{42l} ),
                        iterator( record ), new PreAllocatedRecords( 60 ) );
                nodeRecord.setLabelField( dynamicPointer( newRecords ), newRecords );

                tx.create( nodeRecord );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.NODE_DYNAMIC_LABEL, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportRelationshipInconsistencies() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                tx.create( new RelationshipRecord( next.relationship(), 1, 2, C ) );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.RELATIONSHIP, 2 )
                   .verify( RecordType.COUNTS, 3 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportPropertyInconsistencies() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                PropertyRecord property = new PropertyRecord( next.property() );
                property.setPrevProp( next.property() );
                PropertyBlock block = new PropertyBlock();
                block.setSingleBlock( next.propertyKey() | (((long) PropertyType.INT.intValue()) << 24) | (666L << 28) );
                property.addPropertyBlock( block );
                tx.create( property );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.PROPERTY, 2 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportStringPropertyInconsistencies() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                DynamicRecord string = new DynamicRecord( next.stringProperty() );
                string.setInUse( true );
                string.setCreated();
                string.setType( PropertyType.STRING.intValue() );
                string.setNextBlock( next.stringProperty() );
                string.setData( UTF8.encode( "hello world" ) );

                PropertyBlock block = new PropertyBlock();
                block.setSingleBlock( (((long) PropertyType.STRING.intValue()) << 24) | (string.getId() << 28) );
                block.addValueRecord( string );

                PropertyRecord property = new PropertyRecord( next.property() );
                property.addPropertyBlock( block );

                tx.create( property );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.STRING_PROPERTY, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportBrokenSchemaRecordChain() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                DynamicRecord schema = new DynamicRecord( next.schema() );
                DynamicRecord schemaBefore = schema.clone();

                schema.setNextBlock( next.schema() ); // Point to a record that isn't in use.
                IndexRule rule = IndexRule.indexRule( schema.getId(), label1, key,
                        new SchemaIndexProvider.Descriptor( "lucene", "1.0" ) );
                schema.setData( new RecordSerializer().append( rule ).serialize() );

                tx.createSchema( asList( schemaBefore ), asList( schema ), rule );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.SCHEMA, 3 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportDuplicateConstraintReferences() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                int ruleId1 = (int) next.schema();
                int ruleId2 = (int) next.schema();
                int labelId = next.label();
                int propertyKeyId = next.propertyKey();

                DynamicRecord record1 = new DynamicRecord( ruleId1 );
                DynamicRecord record2 = new DynamicRecord( ruleId2 );
                DynamicRecord record1Before = record1.clone();
                DynamicRecord record2Before = record2.clone();

                SchemaIndexProvider.Descriptor providerDescriptor = new SchemaIndexProvider.Descriptor( "lucene", "1.0" );

                IndexRule rule1 = IndexRule.constraintIndexRule( ruleId1, labelId, propertyKeyId, providerDescriptor,
                        (long) ruleId1 );
                IndexRule rule2 = IndexRule.constraintIndexRule( ruleId2, labelId, propertyKeyId, providerDescriptor, (long) ruleId1 );

                Collection<DynamicRecord> records1 = serializeRule( rule1, record1 );
                Collection<DynamicRecord> records2 = serializeRule( rule2, record2 );

                assertEquals( asList( record1 ), records1 );
                assertEquals( asList( record2 ), records2 );

                tx.nodeLabel( labelId, "label" );
                tx.propertyKey( propertyKeyId, "property" );

                tx.createSchema( asList(record1Before), records1, rule1 );
                tx.createSchema( asList(record2Before), records2, rule2 );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.SCHEMA, 4 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportInvalidConstraintBackReferences() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                int ruleId1 = (int) next.schema();
                int ruleId2 = (int) next.schema();
                int labelId = next.label();
                int propertyKeyId = next.propertyKey();

                DynamicRecord record1 = new DynamicRecord( ruleId1 );
                DynamicRecord record2 = new DynamicRecord( ruleId2 );
                DynamicRecord record1Before = record1.clone();
                DynamicRecord record2Before = record2.clone();

                SchemaIndexProvider.Descriptor providerDescriptor = new SchemaIndexProvider.Descriptor( "lucene", "1.0" );

                IndexRule rule1 = IndexRule.constraintIndexRule( ruleId1, labelId, propertyKeyId, providerDescriptor, (long) ruleId2 );
                UniquePropertyConstraintRule rule2 = UniquePropertyConstraintRule
                        .uniquenessConstraintRule( ruleId2, labelId, propertyKeyId, ruleId2 );


                Collection<DynamicRecord> records1 = serializeRule( rule1, record1 );
                Collection<DynamicRecord> records2 = serializeRule( rule2, record2 );

                assertEquals( asList( record1 ), records1 );
                assertEquals( asList( record2 ), records2 );

                tx.nodeLabel( labelId, "label" );
                tx.propertyKey( propertyKeyId, "property" );

                tx.createSchema( asList(record1Before), records1, rule1 );
                tx.createSchema( asList(record2Before), records2, rule2 );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.SCHEMA, 2 )
                   .andThatsAllFolks();
    }

    public static Collection<DynamicRecord> serializeRule( SchemaRule rule, DynamicRecord... records )
    {
        return serializeRule( rule, asList( records ) );
    }

    public static Collection<DynamicRecord> serializeRule( SchemaRule rule, Collection<DynamicRecord> records )
    {
        RecordSerializer serializer = new RecordSerializer();
        serializer.append( rule );

        byte[] data = serializer.serialize();
        PreAllocatedRecords dynamicRecordAllocator = new PreAllocatedRecords( data.length );
        Collection<DynamicRecord> result = new ArrayList<>();
        AbstractDynamicStore.allocateRecordsFromBytes( result, data, records.iterator(), dynamicRecordAllocator );
        return result;
    }

    @Test
    public void shouldReportArrayPropertyInconsistencies() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                DynamicRecord array = new DynamicRecord( next.arrayProperty() );
                array.setInUse( true );
                array.setCreated();
                array.setType( ARRAY.intValue() );
                array.setNextBlock( next.arrayProperty() );
                array.setData( UTF8.encode( "hello world" ) );

                PropertyBlock block = new PropertyBlock();
                block.setSingleBlock( (((long) ARRAY.intValue()) << 24) | (array.getId() << 28) );
                block.addValueRecord( array );

                PropertyRecord property = new PropertyRecord( next.property() );
                property.addPropertyBlock( block );

                tx.create( property );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.ARRAY_PROPERTY, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportRelationshipLabelNameInconsistencies() throws Exception
    {
        // given
        final Reference<Integer> inconsistentName = new Reference<>();
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                inconsistentName.set( next.relationshipType() );
                tx.relationshipType( inconsistentName.get(), "FOO" );
            }
        } );
        StoreAccess access = fixture.directStoreAccess().nativeStores();
        DynamicRecord record = access.getRelationshipTypeNameStore().forceGetRecord( inconsistentName.get() );
        record.setNextBlock( record.getId() );
        access.getRelationshipTypeNameStore().updateRecord( record );

        // when
        ConsistencySummaryStatistics stats = check( fixture.directStoreAccess() );

        // then
        on( stats ).verify( RecordType.RELATIONSHIP_TYPE_NAME, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportPropertyKeyNameInconsistencies() throws Exception
    {
        // given
        final Reference<Integer> inconsistentName = new Reference<>();
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                inconsistentName.set( next.propertyKey() );
                tx.propertyKey( inconsistentName.get(), "FOO" );
            }
        } );
        StoreAccess access = fixture.directStoreAccess().nativeStores();
        DynamicRecord record = access.getPropertyKeyNameStore().forceGetRecord( inconsistentName.get()+1 );
        record.setNextBlock( record.getId() );
        access.getPropertyKeyNameStore().updateRecord( record );

        // when
        ConsistencySummaryStatistics stats = check( fixture.directStoreAccess() );

        // then
        on( stats ).verify( RecordType.PROPERTY_KEY_NAME, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportRelationshipTypeInconsistencies() throws Exception
    {
        // given
        StoreAccess access = fixture.directStoreAccess().nativeStores();
        RecordStore<RelationshipTypeTokenRecord> relTypeStore = access.getRelationshipTypeTokenStore();
        RelationshipTypeTokenRecord record = relTypeStore.forceGetRecord( (int) relTypeStore.nextId() );
        record.setNameId( 20 );
        record.setInUse( true );
        relTypeStore.updateRecord( record );

        // when
        ConsistencySummaryStatistics stats = check( fixture.directStoreAccess() );

        // then
        access.close();
        on( stats ).verify( RecordType.RELATIONSHIP_TYPE, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportLabelInconsistencies() throws Exception
    {
        // given
        StoreAccess access = fixture.directStoreAccess().nativeStores();
        LabelTokenRecord record = access.getLabelTokenStore().forceGetRecord( 1 );
        record.setNameId( 20 );
        record.setInUse( true );
        access.getLabelTokenStore().updateRecord( record );

        // when
        ConsistencySummaryStatistics stats = check( fixture.directStoreAccess() );

        // then
        on( stats ).verify( RecordType.LABEL, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportPropertyKeyInconsistencies() throws Exception
    {
        // given
        final Reference<Integer> inconsistentKey = new Reference<>();
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                inconsistentKey.set( next.propertyKey() );
                tx.propertyKey( inconsistentKey.get(), "FOO" );
            }
        } );
        StoreAccess access = fixture.directStoreAccess().nativeStores();
        DynamicRecord record = access.getPropertyKeyNameStore().forceGetRecord( inconsistentKey.get()+1 );
        record.setInUse( false );
        access.getPropertyKeyNameStore().updateRecord( record );

        // when
        ConsistencySummaryStatistics stats = check( fixture.directStoreAccess() );

        // then
        on( stats ).verify( RecordType.PROPERTY_KEY, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportRelationshipGroupTypeInconsistencies() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                long node = next.node();
                long group = next.relationshipGroup();
                int nonExistentType = next.relationshipType() + 1;
                tx.create( inUse( new NodeRecord( node, true, group, NO_NEXT_PROPERTY.intValue() ) ) );
                tx.create( withOwner( inUse( new RelationshipGroupRecord( group, nonExistentType ) ), node ) );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.RELATIONSHIP_GROUP, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportRelationshipGroupChainInconsistencies() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                    GraphStoreFixture.IdGenerator next )
            {
                long node = next.node();
                long group = next.relationshipGroup();
                tx.create( inUse( new NodeRecord( node, true, group, NO_NEXT_PROPERTY.intValue() ) ) );
                tx.create( withOwner( withNext( inUse( new RelationshipGroupRecord( group, C ) ),
                        group+1 /*non-existent group id*/ ), node ) );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.RELATIONSHIP_GROUP, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportRelationshipGroupUnsortedChainInconsistencies() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                    GraphStoreFixture.IdGenerator next )
            {
                long node = next.node();
                long firstGroupId = next.relationshipGroup();
                long otherGroupId = next.relationshipGroup();
                tx.create( inUse( new NodeRecord( node, true, firstGroupId, NO_NEXT_PROPERTY.intValue() ) ) );
                tx.create( withOwner( withNext( inUse( new RelationshipGroupRecord( firstGroupId, T ) ),
                        otherGroupId ), node ) );
                tx.create( withOwner( inUse( new RelationshipGroupRecord( otherGroupId, C ) ), node ) );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.RELATIONSHIP_GROUP, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportRelationshipGroupRelationshipNotInUseInconsistencies() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                    GraphStoreFixture.IdGenerator next )
            {
                long node = next.node();
                long groupId = next.relationshipGroup();
                long rel = next.relationship();
                tx.create( inUse( new NodeRecord( node, true, groupId, NO_NEXT_PROPERTY.intValue() ) ) );
                tx.create( withOwner( withRelationships( inUse( new RelationshipGroupRecord( groupId, C ) ),
                        rel, rel, rel ), node ) );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.RELATIONSHIP_GROUP, 3 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportRelationshipGroupRelationshipNotFirstInconsistencies() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                    GraphStoreFixture.IdGenerator next )
            {
                /*
                 *   node ----------------> group
                 *                             |
                 *                             v
                 *   otherNode <--> relA <--> relB
                 */
                long node = next.node();
                long otherNode = next.node();
                long group = next.relationshipGroup();
                long relA = next.relationship();
                long relB = next.relationship();
                tx.create( inUse( new NodeRecord( node, true, group, NO_NEXT_PROPERTY.intValue() ) ) );
                tx.create( inUse( new NodeRecord( otherNode, false, relA, NO_NEXT_PROPERTY.intValue() ) ) );
                tx.create( withNext( inUse( new RelationshipRecord( relA, otherNode, otherNode, C ) ), relB ) );
                tx.create( withPrev( inUse( new RelationshipRecord( relB, otherNode, otherNode, C ) ), relA ) );
                tx.create( withOwner( withRelationships( inUse( new RelationshipGroupRecord( group, C ) ), relB, relB, relB ), node ) );
                tx.incrementRelationshipCount( ANY_LABEL, ANY_RELATIONSHIP_TYPE, ANY_LABEL, 2 );
                tx.incrementRelationshipCount( ANY_LABEL, C, ANY_LABEL, 2 );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.RELATIONSHIP_GROUP, 3 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportFirstRelationshipGroupOwnerInconsistency() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                    GraphStoreFixture.IdGenerator next )
            {
                // node -[first]-> group -[owner]-> otherNode
                long node = next.node();
                long otherNode = next.node();
                long group = next.relationshipGroup();
                tx.create( inUse( new NodeRecord( node, true, group, NO_NEXT_PROPERTY.intValue() ) ) );
                tx.create( inUse( new NodeRecord( otherNode, false, NO_NEXT_RELATIONSHIP.intValue(),
                        NO_NEXT_PROPERTY.intValue() ) ) );
                tx.create( withOwner( inUse( new RelationshipGroupRecord( group, C ) ), otherNode ) );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        // - next group has other owner that its previous
        // - first group has other owner
        on( stats ).verify( RecordType.NODE, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportChainedRelationshipGroupOwnerInconsistency() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                    GraphStoreFixture.IdGenerator next )
            {
                /* node -[first]-> groupA -[next]-> groupB
                 *    ^               /                |
                 *     \--[owner]----               [owner]
                 *                                     v
                 *                                  otherNode
                 */
                long node = next.node();
                long otherNode = next.node();
                long groupA = next.relationshipGroup();
                long groupB = next.relationshipGroup();
                tx.create( inUse( new NodeRecord( node, true, groupA, NO_NEXT_PROPERTY.intValue() ) ) );
                tx.create( inUse( new NodeRecord( otherNode, false, NO_NEXT_RELATIONSHIP.intValue(),
                        NO_NEXT_PROPERTY.intValue() ) ) );
                tx.create( withNext( withOwner( inUse( new RelationshipGroupRecord( groupA, C ) ),
                        node ), groupB ) );
                tx.create( withOwner( inUse( new RelationshipGroupRecord( groupB, T ) ), otherNode ) );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.RELATIONSHIP_GROUP, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportRelationshipGroupOwnerNotInUse() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                    GraphStoreFixture.IdGenerator next )
            {
                // group -[owner]-> <not-in-use node>
                long node = next.node();
                long group = next.relationshipGroup();
                tx.create( withOwner( inUse( new RelationshipGroupRecord( group, C ) ), node ) );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.RELATIONSHIP_GROUP, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportRelationshipGroupOwnerInvalidValue() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                    GraphStoreFixture.IdGenerator next )
            {
                // node -[first]-> group -[owner]-> -1
                long group = next.relationshipGroup();
                tx.create( withOwner( inUse( new RelationshipGroupRecord( group, C ) ), -1 ) );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.RELATIONSHIP_GROUP, 1 )
                   .andThatsAllFolks();
    }

    protected RelationshipRecord withNext( RelationshipRecord relationship, long next )
    {
        relationship.setFirstNextRel( next );
        relationship.setSecondNextRel( next );
        return relationship;
    }

    protected RelationshipRecord withPrev( RelationshipRecord relationship, long prev )
    {
        relationship.setFirstInFirstChain( false );
        relationship.setFirstInSecondChain( false );
        relationship.setFirstPrevRel( prev );
        relationship.setSecondPrevRel( prev );
        return relationship;
    }

    @Test
    public void shouldReportRelationshipGroupRelationshipOfOtherTypeInconsistencies() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                    GraphStoreFixture.IdGenerator next )
            {
                /*
                 *   node -----> groupA
                 *                   |
                 *                   v
                 *   otherNode <--> relB
                 */
                long node = next.node();
                long otherNode = next.node();
                long group = next.relationshipGroup();
                long rel = next.relationship();
                tx.create( new NodeRecord( node, true, group, NO_NEXT_PROPERTY.intValue() ) );
                tx.create( new NodeRecord( otherNode, false, rel, NO_NEXT_PROPERTY.intValue() ) );
                tx.create( new RelationshipRecord( rel, otherNode, otherNode, T ) );
                tx.create( withOwner( withRelationships( new RelationshipGroupRecord( group, C ),
                        rel, rel, rel ), node ) );
                tx.incrementRelationshipCount( ANY_LABEL, ANY_RELATIONSHIP_TYPE, ANY_LABEL, 1 );
                tx.incrementRelationshipCount( ANY_LABEL, T, ANY_LABEL, 1 );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.RELATIONSHIP_GROUP, 3 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldNotReportRelationshipGroupInconsistenciesForConsistentRecords() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                    GraphStoreFixture.IdGenerator next )
            {
                /* Create a little mini consistent structure:
                 *
                 *    nodeA --> groupA -[next]-> groupB
                 *      ^          |
                 *       \       [out]
                 *        \        v
                 *       [start]- rel -[end]-> nodeB
                 */

                long nodeA = next.node();
                long nodeB = next.node();
                long rel = next.relationship();
                long groupA = next.relationshipGroup();
                long groupB = next.relationshipGroup();

                tx.create( new NodeRecord( nodeA, true, groupA, NO_NEXT_PROPERTY.intValue() ) );
                tx.create( new NodeRecord( nodeB, false, rel, NO_NEXT_PROPERTY.intValue() ) );
                tx.create( firstInChains( new RelationshipRecord( rel, nodeA, nodeB, C ), 1 ) );
                tx.incrementRelationshipCount( ANY_LABEL, ANY_RELATIONSHIP_TYPE, ANY_LABEL, 1 );
                tx.incrementRelationshipCount( ANY_LABEL, C, ANY_LABEL, 1 );

                tx.create( withOwner( withRelationship( withNext( new RelationshipGroupRecord( groupA, C ), groupB ),
                        Direction.OUTGOING, rel ), nodeA ) );
                tx.create( withOwner( new RelationshipGroupRecord( groupB, T ), nodeA ) );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        assertTrue( "should be consistent", stats.isConsistent() );
    }

    @Test
    public void shouldReportWrongNodeCountsEntries() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                tx.incrementNodeCount( label3, 1 );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.COUNTS, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportWrongRelationshipCountsEntries() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                tx.incrementRelationshipCount( label1 , C, ANY_LABEL, 1 );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.COUNTS, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportIfSomeKeysAreMissing() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                tx.incrementNodeCount( label3, -1 );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.COUNTS, 1 )
                   .andThatsAllFolks();
    }

    @Test
    public void shouldReportIfThereAreExtraKeys() throws Exception
    {
        // given
        fixture.apply( new GraphStoreFixture.Transaction()
        {
            @Override
            protected void transactionData( GraphStoreFixture.TransactionDataBuilder tx,
                                            GraphStoreFixture.IdGenerator next )
            {
                tx.incrementNodeCount( 1024 /* new label */, 1 );
            }
        } );

        // when
        ConsistencySummaryStatistics stats = check();

        // then
        on( stats ).verify( RecordType.COUNTS, 2 )
                   .andThatsAllFolks();
    }

    @Rule
    public final GraphStoreFixture fixture = new GraphStoreFixture()
    {
        @Override
        protected void generateInitialData( GraphDatabaseService graphDb )
        {
            Supplier<org.neo4j.kernel.api.Statement> stmt =
                    ((GraphDatabaseAPI) graphDb).getDependencyResolver()
                            .resolveDependency( ThreadToStatementContextBridge.class );

            try ( org.neo4j.graphdb.Transaction tx = graphDb.beginTx() )
            {
                graphDb.schema().indexFor( label( "label3" ) ).on( "key" ).create();
                graphDb.schema().constraintFor( label( "label4" ) ).assertPropertyIsUnique( "key" ).create();
                graphDb.schema().constraintFor( label( "draconian" ) ).assertPropertyExists( "mandatory" ).create();
                graphDb.schema().constraintFor( withName( "M" ) ).assertPropertyExists( "mandatory" ).create();
                tx.success();
            }

            try ( org.neo4j.graphdb.Transaction tx = graphDb.beginTx() )
            {
                Node node1 = set( graphDb.createNode( label( "label1" ) ) );
                Node node2 = set( graphDb.createNode( label( "label2" ) ), property( "key", "value" ) );
                node1.createRelationshipTo( node2, withName( "C" ) );
                // Just to create one more rel type
                graphDb.createNode().createRelationshipTo( graphDb.createNode(), withName( "T" ) );
                indexedNodes.add( set( graphDb.createNode( label( "label3" ) ), property( "key", "value" ) ).getId() );
                set( graphDb.createNode( label( "label4" ) ), property( "key", "value" ) );
                tx.success();

                org.neo4j.kernel.api.Statement statement = stmt.get();
                label1 = statement.readOperations().labelGetForName( "label1" );
                label2 = statement.readOperations().labelGetForName( "label2" );
                label3 = statement.readOperations().labelGetForName( "label3" );
                label4 = statement.readOperations().labelGetForName( "label4" );
                draconian = statement.readOperations().labelGetForName( "draconian" );
                key = statement.readOperations().propertyKeyGetForName( "key" );
                mandatory = statement.readOperations().propertyKeyGetForName( "mandatory" );
                C = statement.readOperations().relationshipTypeGetForName( "C" );
                T = statement.readOperations().relationshipTypeGetForName( "T" );
                M = statement.readOperations().relationshipTypeGetForName( "M" );
            }
        }
    };
    private int label1, label2, label3, label4, draconian;
    private int key, mandatory;
    private int C, T, M;

    private final ByteArrayOutputStream out = new ByteArrayOutputStream();
    private final List<Long> indexedNodes = new ArrayList<>();
    public final @Rule TestRule print_log_on_failure = new TestRule()
    {
        @Override
        public Statement apply( final Statement base, Description description )
        {
            return new Statement()
            {
                @Override
                public void evaluate() throws Throwable
                {
                    try
                    {
                        base.evaluate();
                    }
                    catch ( Throwable t )
                    {
                        System.out.write( out.toByteArray() );
                        throw t;
                    }
                }
            };
        }
    };

    private ConsistencySummaryStatistics check() throws ConsistencyCheckIncompleteException
    {
        return check( fixture.directStoreAccess() );
    }

    private ConsistencySummaryStatistics check( DirectStoreAccess stores ) throws ConsistencyCheckIncompleteException
    {
        Config config = config( taskExecutionOrder );
        FullCheck checker = new FullCheck( config, ProgressMonitorFactory.NONE );
        return checker.execute( stores, FormattedLog.toOutputStream( out ) );
    }

    protected static RelationshipGroupRecord withRelationships( RelationshipGroupRecord group, long out,
            long in, long loop )
    {
        group.setFirstOut( out );
        group.setFirstIn( in );
        group.setFirstLoop( loop );
        return group;
    }

    protected static RelationshipGroupRecord withRelationship( RelationshipGroupRecord group, Direction direction,
            long rel )
    {
        switch ( direction )
        {
        case OUTGOING:
            group.setFirstOut( rel );
            break;
        case INCOMING:
            group.setFirstIn( rel );
            break;
        case BOTH:
            group.setFirstLoop( rel );
            break;
        default:
            throw new IllegalArgumentException( direction.name() );
        }
        return group;
    }

    protected static RelationshipRecord firstInChains( RelationshipRecord relationship, int count )
    {
        relationship.setFirstInFirstChain( true );
        relationship.setFirstPrevRel( count );
        relationship.setFirstInSecondChain( true );
        relationship.setSecondPrevRel( count );
        return relationship;
    }

    protected static RelationshipGroupRecord withNext( RelationshipGroupRecord group, long next )
    {
        group.setNext( next );
        return group;
    }

    protected static RelationshipGroupRecord withOwner( RelationshipGroupRecord record, long owner )
    {
        record.setOwningNode( owner );
        return record;
    }

    private static class Reference<T>
    {
        private T value;

        void set(T value)
        {
            this.value = value;
        }

        T get()
        {
            return value;
        }

        @Override
        public String toString()
        {
            return String.valueOf( value );
        }
    }

    public static final class ConsistencySummaryVerifier
    {
        private final ConsistencySummaryStatistics stats;
        private final Set<RecordType> types = new HashSet<>();
        private long total;

        public static ConsistencySummaryVerifier on( ConsistencySummaryStatistics stats )
        {
            return new ConsistencySummaryVerifier( stats );
        }


        private ConsistencySummaryVerifier( ConsistencySummaryStatistics stats )
        {
            this.stats = stats;
        }

        public ConsistencySummaryVerifier verify( RecordType type, int inconsistencies )
        {
            if ( !types.add( type ) )
            {
                throw new IllegalStateException( "Tried to verify the same type twice: " + type );
            }
            assertEquals( "Inconsistencies of type: " + type, inconsistencies,
                    stats.getInconsistencyCountForRecordType( type ) );
            total += inconsistencies;
            return this;
        }

        public void andThatsAllFolks()
        {
            assertEquals( "Total number of inconsistencies: " + stats, total, stats.getTotalInconsistencyCount() );
        }
    }
}


File: community/kernel/src/main/java/org/neo4j/kernel/impl/api/KernelTransactionImplementation.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.kernel.impl.api;

import java.util.Collection;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;

import org.neo4j.collection.pool.Pool;
import org.neo4j.collection.primitive.PrimitiveIntCollections;
import org.neo4j.collection.primitive.PrimitiveIntIterator;
import org.neo4j.graphdb.schema.ConstraintType;
import org.neo4j.helpers.Clock;
import org.neo4j.helpers.ThisShouldNotHappenError;
import org.neo4j.kernel.api.KernelTransaction;
import org.neo4j.kernel.api.KeyReadTokenNameLookup;
import org.neo4j.kernel.api.Statement;
import org.neo4j.kernel.api.constraints.MandatoryNodePropertyConstraint;
import org.neo4j.kernel.api.constraints.MandatoryRelationshipPropertyConstraint;
import org.neo4j.kernel.api.constraints.PropertyConstraint;
import org.neo4j.kernel.api.constraints.UniquenessConstraint;
import org.neo4j.kernel.api.exceptions.ConstraintViolationTransactionFailureException;
import org.neo4j.kernel.api.exceptions.EntityNotFoundException;
import org.neo4j.kernel.api.exceptions.InvalidTransactionTypeKernelException;
import org.neo4j.kernel.api.exceptions.Status;
import org.neo4j.kernel.api.exceptions.TransactionFailureException;
import org.neo4j.kernel.api.exceptions.schema.ConstraintValidationKernelException;
import org.neo4j.kernel.api.exceptions.schema.DropIndexFailureException;
import org.neo4j.kernel.api.exceptions.schema.SchemaRuleNotFoundException;
import org.neo4j.kernel.api.index.IndexDescriptor;
import org.neo4j.kernel.api.index.SchemaIndexProvider;
import org.neo4j.kernel.api.labelscan.LabelScanStore;
import org.neo4j.kernel.api.properties.DefinedProperty;
import org.neo4j.kernel.api.txstate.LegacyIndexTransactionState;
import org.neo4j.kernel.api.txstate.TransactionState;
import org.neo4j.kernel.api.txstate.TxStateHolder;
import org.neo4j.kernel.api.txstate.TxStateVisitor;
import org.neo4j.kernel.impl.api.index.IndexingService;
import org.neo4j.kernel.impl.api.index.SchemaIndexProviderMap;
import org.neo4j.kernel.impl.api.state.ConstraintIndexCreator;
import org.neo4j.kernel.impl.api.state.TxState;
import org.neo4j.kernel.impl.api.store.StoreReadLayer;
import org.neo4j.kernel.impl.api.store.StoreStatement;
import org.neo4j.kernel.impl.index.IndexEntityType;
import org.neo4j.kernel.impl.locking.LockGroup;
import org.neo4j.kernel.impl.locking.Locks;
import org.neo4j.kernel.impl.store.MandatoryNodePropertyConstraintRule;
import org.neo4j.kernel.impl.store.MandatoryRelationshipPropertyConstraintRule;
import org.neo4j.kernel.impl.store.NeoStore;
import org.neo4j.kernel.impl.store.SchemaStorage;
import org.neo4j.kernel.impl.store.UniquePropertyConstraintRule;
import org.neo4j.kernel.impl.store.record.IndexRule;
import org.neo4j.kernel.impl.store.record.SchemaRule;
import org.neo4j.kernel.impl.transaction.TransactionHeaderInformationFactory;
import org.neo4j.kernel.impl.transaction.TransactionMonitor;
import org.neo4j.kernel.impl.transaction.command.Command;
import org.neo4j.kernel.impl.transaction.log.PhysicalTransactionRepresentation;
import org.neo4j.kernel.impl.transaction.state.TransactionRecordState;
import org.neo4j.kernel.impl.transaction.tracing.CommitEvent;
import org.neo4j.kernel.impl.transaction.tracing.TransactionEvent;
import org.neo4j.kernel.impl.transaction.tracing.TransactionTracer;
import org.neo4j.kernel.impl.util.collection.ArrayCollection;

import static org.neo4j.kernel.api.ReadOperations.ANY_LABEL;
import static org.neo4j.kernel.api.ReadOperations.ANY_RELATIONSHIP_TYPE;
import static org.neo4j.kernel.impl.api.TransactionApplicationMode.INTERNAL;

/**
 * This class should replace the {@link org.neo4j.kernel.api.KernelTransaction} interface, and take its name, as soon
 * as
 * {@code TransitionalTxManagementKernelTransaction} is gone from {@code server}.
 */
public class KernelTransactionImplementation implements KernelTransaction, TxStateHolder
{
    /*
     * IMPORTANT:
     * This class is pooled and re-used. If you add *any* state to it, you *must* make sure that the #initialize()
     * method resets that state for re-use.
     */

    private enum TransactionType
    {
        ANY,
        DATA
                {
                    @Override
                    TransactionType upgradeToSchemaTransaction() throws InvalidTransactionTypeKernelException
                    {
                        throw new InvalidTransactionTypeKernelException(
                                "Cannot perform schema updates in a transaction that has performed data updates." );
                    }
                },
        SCHEMA
                {
                    @Override
                    TransactionType upgradeToDataTransaction() throws InvalidTransactionTypeKernelException
                    {
                        throw new InvalidTransactionTypeKernelException(
                                "Cannot perform data updates in a transaction that has performed schema updates." );
                    }
                };

        TransactionType upgradeToDataTransaction() throws InvalidTransactionTypeKernelException
        {
            return DATA;
        }

        TransactionType upgradeToSchemaTransaction() throws InvalidTransactionTypeKernelException
        {
            return SCHEMA;
        }
    }

    // Logic
    private final SchemaWriteGuard schemaWriteGuard;
    private final IndexingService indexService;
    private final TransactionHooks hooks;
    private final LabelScanStore labelScanStore;
    private final SchemaStorage schemaStorage;
    private final ConstraintIndexCreator constraintIndexCreator;
    private final SchemaIndexProviderMap providerMap;
    private final UpdateableSchemaState schemaState;
    private final StatementOperationParts operations;
    private final Pool<KernelTransactionImplementation> pool;
    // State
    private final TransactionRecordState recordState;
    private final CountsRecordState counts = new CountsRecordState();
    // For committing
    private final TransactionHeaderInformationFactory headerInformationFactory;
    private final TransactionCommitProcess commitProcess;
    private final TransactionMonitor transactionMonitor;
    private final StoreReadLayer storeLayer;
    private final Clock clock;
    private final TransactionToRecordStateVisitor txStateToRecordStateVisitor = new TransactionToRecordStateVisitor();
    private final Collection<Command> extractedCommands = new ArrayCollection<>( 32 );
    private TransactionState txState;
    private LegacyIndexTransactionState legacyIndexTransactionState;
    private TransactionType transactionType = TransactionType.ANY;
    private TransactionHooks.TransactionHooksState hooksState;
    private boolean beforeHookInvoked;
    private Locks.Client locks;
    private StoreStatement storeStatement;
    private boolean closing, closed;
    private boolean failure, success;
    private volatile boolean terminated;
    // Some header information
    private long startTimeMillis;
    private long lastTransactionIdWhenStarted;
    /**
     * Implements reusing the same underlying {@link KernelStatement} for overlapping statements.
     */
    private KernelStatement currentStatement;
    // Event tracing
    private final TransactionTracer tracer;
    private TransactionEvent transactionEvent;


    public KernelTransactionImplementation( StatementOperationParts operations,
            SchemaWriteGuard schemaWriteGuard, LabelScanStore labelScanStore,
            IndexingService indexService,
            UpdateableSchemaState schemaState,
            TransactionRecordState recordState,
            SchemaIndexProviderMap providerMap, NeoStore neoStore,
            Locks.Client locks, TransactionHooks hooks,
            ConstraintIndexCreator constraintIndexCreator,
            TransactionHeaderInformationFactory headerInformationFactory,
            TransactionCommitProcess commitProcess,
            TransactionMonitor transactionMonitor,
            StoreReadLayer storeLayer,
            LegacyIndexTransactionState legacyIndexTransactionState,
            Pool<KernelTransactionImplementation> pool,
            Clock clock,
            TransactionTracer tracer )
    {
        this.operations = operations;
        this.schemaWriteGuard = schemaWriteGuard;
        this.labelScanStore = labelScanStore;
        this.indexService = indexService;
        this.recordState = recordState;
        this.providerMap = providerMap;
        this.schemaState = schemaState;
        this.hooks = hooks;
        this.locks = locks;
        this.constraintIndexCreator = constraintIndexCreator;
        this.headerInformationFactory = headerInformationFactory;
        this.commitProcess = commitProcess;
        this.transactionMonitor = transactionMonitor;
        this.storeLayer = storeLayer;
        this.legacyIndexTransactionState = new CachingLegacyIndexTransactionState( legacyIndexTransactionState );
        this.pool = pool;
        this.clock = clock;
        this.schemaStorage = new SchemaStorage( neoStore.getSchemaStore() );
        this.tracer = tracer;
    }

    /**
     * Reset this transaction to a vanilla state, turning it into a logically new transaction.
     */
    public KernelTransactionImplementation initialize( long lastCommittedTx )
    {
        assert locks != null : "This transaction has been disposed off, it should not be used.";
        this.terminated = closing = closed = failure = success = false;
        this.transactionType = TransactionType.ANY;
        this.hooksState = null;
        this.beforeHookInvoked = false;
        this.txState = null; // TODO: Implement txState.clear() instead, to re-use data structures
        this.legacyIndexTransactionState.initialize();
        this.recordState.initialize( lastCommittedTx );
        this.counts.initialize();
        this.startTimeMillis = clock.currentTimeMillis();
        this.lastTransactionIdWhenStarted = lastCommittedTx;
        this.transactionEvent = tracer.beginTransaction();
        this.storeStatement = storeLayer.acquireStatement();
        assert transactionEvent != null : "transactionEvent was null!";
        return this;
    }

    @Override
    public void success()
    {
        this.success = true;
    }

    @Override
    public void failure()
    {
        failure = true;
    }

    @Override
    public boolean shouldBeTerminated()
    {
        return terminated;
    }

    @Override
    public void markForTermination()
    {
        if ( !terminated )
        {
            failure = true;
            terminated = true;
            transactionMonitor.transactionTerminated();
        }
    }

    @Override
    public boolean isOpen()
    {
        return !closed && !closing;
    }

    @Override
    public KernelStatement acquireStatement()
    {
        assertTransactionOpen();
        if ( currentStatement == null )
        {
            currentStatement = new KernelStatement( this, new IndexReaderFactory.Caching( indexService ),
                    labelScanStore, this, locks, operations, storeStatement );
        }
        currentStatement.acquire();
        return currentStatement;
    }

    public void releaseStatement( Statement statement )
    {
        assert currentStatement == statement;
        currentStatement = null;
    }

    public void upgradeToDataTransaction() throws InvalidTransactionTypeKernelException
    {
        transactionType = transactionType.upgradeToDataTransaction();
    }

    public void upgradeToSchemaTransaction() throws InvalidTransactionTypeKernelException
    {
        doUpgradeToSchemaTransaction();
        transactionType = transactionType.upgradeToSchemaTransaction();
    }

    public void doUpgradeToSchemaTransaction() throws InvalidTransactionTypeKernelException
    {
        schemaWriteGuard.assertSchemaWritesAllowed();
    }

    private void dropCreatedConstraintIndexes() throws TransactionFailureException
    {
        if ( hasTxStateWithChanges() )
        {
            for ( IndexDescriptor createdConstraintIndex : txState().constraintIndexesCreatedInTx() )
            {
                try
                {
                    // TODO logically, which statement should this operation be performed on?
                    constraintIndexCreator.dropUniquenessConstraintIndex( createdConstraintIndex );
                }
                catch ( DropIndexFailureException e )
                {
                    throw new IllegalStateException( "Constraint index that was created in a transaction should be " +
                            "possible to drop during rollback of that transaction.", e );
                }
            }
        }
    }

    @Override
    public TransactionState txState()
    {
        if ( txState == null )
        {
            txState = new TxState();
        }
        return txState;
    }

    @Override
    public LegacyIndexTransactionState legacyIndexTxState()
    {
        return legacyIndexTransactionState;
    }

    @Override
    public boolean hasTxStateWithChanges()
    {
        return txState != null && txState.hasChanges();
    }

    private void closeTransaction()
    {
        assertTransactionOpen();
        closed = true;
        if ( currentStatement != null )
        {
            currentStatement.forceClose();
            currentStatement = null;
        }
    }

    private void closeCurrentStatementIfAny()
    {
        if ( currentStatement != null )
        {
            currentStatement.forceClose();
            currentStatement = null;
        }
    }

    private void assertTransactionNotClosing()
    {
        if ( closing )
        {
            throw new IllegalStateException( "This transaction is already being closed." );
        }
    }

    private void prepareRecordChangesFromTransactionState() throws ConstraintValidationKernelException
    {
        if ( hasTxStateWithChanges() )
        {
            txState().accept( txStateVisitor() );
            txStateToRecordStateVisitor.done();
        }
    }

    private TxStateVisitor txStateVisitor()
    {
        Iterator<PropertyConstraint> constraints = storeLayer.constraintsGetAll();
        while ( constraints.hasNext() )
        {
            PropertyConstraint constraint = constraints.next();
            if ( constraint.type() == ConstraintType.MANDATORY_NODE_PROPERTY ||
                 constraint.type() == ConstraintType.MANDATORY_RELATIONSHIP_PROPERTY )
            {
                return new MandatoryPropertyEnforcer( operations.entityReadOperations(), txStateToRecordStateVisitor,
                        this, storeLayer, storeStatement );
            }
        }
        return txStateToRecordStateVisitor;
    }

    private void assertTransactionOpen()
    {
        if ( closed )
        {
            throw new IllegalStateException( "This transaction has already been completed." );
        }
    }

    private boolean hasChanges()
    {
        return hasTxStateWithChanges() ||
                recordState.hasChanges() ||
                legacyIndexTransactionState.hasChanges() ||
                counts.hasChanges();
    }

    private boolean hasAnyTokenChanges()
    {
        return hasTxStateWithChanges() ? txState.hasTokenChanges() : false;
    }

    public TransactionRecordState getTransactionRecordState()
    {
        return recordState;
    }

    @Override
    public void close() throws TransactionFailureException
    {
        assertTransactionOpen();
        assertTransactionNotClosing();
        closeCurrentStatementIfAny();
        closing = true;
        try
        {
            if ( failure || !success )
            {
                rollback();
                if ( success )
                {
                    // Success was called, but also failure which means that the client code using this
                    // transaction passed through a happy path, but the transaction was still marked as
                    // failed for one or more reasons. Tell the user that although it looked happy it
                    // wasn't committed, but was instead rolled back.
                    throw new TransactionFailureException( Status.Transaction.MarkedAsFailed,
                            "Transaction rolled back even if marked as successful" );
                }
            }
            else
            {
                commit();
            }
        }
        finally
        {
            try
            {
                closed = true;
                closing = false;
                transactionEvent.setSuccess( success );
                transactionEvent.setFailure( failure );
                transactionEvent.setTransactionType( transactionType.name() );
                transactionEvent.setReadOnly( txState == null || !txState.hasChanges() );
                transactionEvent.close();
                transactionEvent = null;
            }
            finally
            {
                release();
            }
        }
    }

    protected void dispose()
    {
        if ( locks != null )
        {
            locks.close();
        }

        this.locks = null;
        this.transactionType = null;
        this.hooksState = null;
        this.txState = null;
        this.legacyIndexTransactionState = null;

        if ( storeStatement != null )
        {
            this.storeStatement.close();
            this.storeStatement = null;
        }
    }

    private void commit() throws TransactionFailureException
    {
        boolean success = false;

        try ( CommitEvent commitEvent = transactionEvent.beginCommitEvent() )
        {
            // Trigger transaction "before" hooks.
            if ( hasChanges() && !hasAnyTokenChanges() )
            {
                try
                {
                    if ( (hooksState = hooks.beforeCommit( txState, this, storeLayer )) != null && hooksState.failed() )
                    {
                        throw new TransactionFailureException( Status.Transaction.HookFailed, hooksState.failure(), "" );
                    }
                }
                finally
                {
                    beforeHookInvoked = true;
                }
            }

            prepareRecordChangesFromTransactionState();

            // Convert changes into commands and commit
            if ( hasChanges() )
            {
                try ( LockGroup lockGroup = new LockGroup() )
                {
                    // Gather up commands from the various sources
                    extractedCommands.clear();
                    recordState.extractCommands( extractedCommands );
                    legacyIndexTransactionState.extractCommands( extractedCommands );
                    counts.extractCommands( extractedCommands );

                    /* Here's the deal: we track a quick-to-access hasChanges in transaction state which is true
                     * if there are any changes imposed by this transaction. Some changes made inside a transaction undo
                     * previously made changes in that same transaction, and so at some point a transaction may have
                     * changes and at another point, after more changes seemingly,
                     * the transaction may not have any changes.
                     * However, to track that "undoing" of the changes is a bit tedious, intrusive and hard to maintain
                     * and get right.... So to really make sure the transaction has changes we re-check by looking if we
                     * have produced any commands to add to the logical log.
                     */
                    if ( !extractedCommands.isEmpty() )
                    {
                        // Finish up the whole transaction representation
                        PhysicalTransactionRepresentation transactionRepresentation =
                                new PhysicalTransactionRepresentation( extractedCommands );
                        TransactionHeaderInformation headerInformation = headerInformationFactory.create();
                        transactionRepresentation.setHeader( headerInformation.getAdditionalHeader(),
                                headerInformation.getMasterId(),
                                headerInformation.getAuthorId(),
                                startTimeMillis, lastTransactionIdWhenStarted, clock.currentTimeMillis(),
                                locks.getLockSessionId() );

                        // Commit the transaction
                        commitProcess.commit( transactionRepresentation, lockGroup, commitEvent, INTERNAL );
                    }
                }
            }
            success = true;
        }
        catch ( ConstraintValidationKernelException e )
        {
            throw new ConstraintViolationTransactionFailureException(
                    e.getUserMessage( new KeyReadTokenNameLookup( operations.keyReadOperations() ) ), e );
        }
        finally
        {
            if ( !success )
            {
                rollback();
            }
            else
            {
                afterCommit();
            }
        }
    }

    private void rollback() throws TransactionFailureException
    {
        try
        {
            try
            {
                dropCreatedConstraintIndexes();
            }
            catch ( IllegalStateException | SecurityException e )
            {
                throw new TransactionFailureException( Status.Transaction.CouldNotRollback, e,
                        "Could not drop created constraint indexes" );
            }

            // Free any acquired id's
            if ( txState != null )
            {
                try
                {
                    txState.accept( new TxStateVisitor.Adapter()
                    {
                        @Override
                        public void visitCreatedNode( long id )
                        {
                            storeLayer.releaseNode( id );
                        }

                        @Override
                        public void visitCreatedRelationship( long id, int type, long startNode, long endNode )
                        {
                            storeLayer.releaseRelationship( id );
                        }
                    } );
                }
                catch ( ConstraintValidationKernelException e )
                {
                    throw new IllegalStateException(
                            "Releasing locks during rollback should perform no constraints checking.", e );
                }
            }
        }
        finally
        {
            afterRollback();
        }
    }

    private void afterCommit()
    {
        try
        {
            closeTransaction();
            if ( beforeHookInvoked )
            {
                hooks.afterCommit( txState, this, hooksState );
            }
        }
        finally
        {
            transactionMonitor.transactionFinished( true );
        }
    }

    private void afterRollback()
    {
        try
        {
            closeTransaction();
            if ( beforeHookInvoked )
            {
                hooks.afterRollback( txState, this, hooksState );
            }
        }
        finally
        {
            transactionMonitor.transactionFinished( false );
        }
    }

    /**
     * Release resources held up by this transaction & return it to the transaction pool.
     */
    private void release()
    {
        locks.releaseAll();
        pool.release( this );
        if ( storeStatement != null )
        {
            storeStatement.close();
            storeStatement = null;
        }
    }

    private class TransactionToRecordStateVisitor extends TxStateVisitor.Adapter
    {
        private final RelationshipDataExtractor edge = new RelationshipDataExtractor();
        private boolean clearState;

        void done()
        {
            try
            {
                if ( clearState )
                {
                    schemaState.clear();
                }
            }
            finally
            {
                clearState = false;
            }
        }

        @Override
        public void visitCreatedNode( long id )
        {
            recordState.nodeCreate( id );
            counts.incrementNodeCount( ANY_LABEL, 1 );
        }

        @Override
        public void visitDeletedNode( long id )
        {
            try ( StoreStatement statement = storeLayer.acquireStatement() )
            {
                counts.incrementNodeCount( ANY_LABEL, -1 );
                PrimitiveIntIterator labels = storeLayer.nodeGetLabels( statement, id );
                if ( labels.hasNext() )
                {
                    final int[] removed = PrimitiveIntCollections.asArray( labels );
                    for ( int label : removed )
                    {
                        counts.incrementNodeCount( label, -1 );
                    }
                    storeLayer.nodeVisitDegrees( statement, id, new DegreeVisitor()
                    {
                        @Override
                        public void visitDegree( int type, int outgoing, int incoming )
                        {
                            for ( int label : removed )
                            {
                                updateRelationshipsCountsFromDegrees( type, label, -outgoing, -incoming );
                            }
                        }
                    } );
                }
            }
            catch ( EntityNotFoundException e )
            {
                // this should not happen, but I guess it means the node we deleted did not exist...?
            }
            recordState.nodeDelete( id );
        }

        @Override
        public void visitCreatedRelationship( long id, int type, long startNode, long endNode )
        {
            try
            {
                updateRelationshipCount( startNode, type, endNode, 1 );
            }
            catch ( EntityNotFoundException e )
            {
                throw new IllegalStateException( "Nodes with added relationships should exist.", e );
            }

            // record the state changes to be made to the store
            recordState.relCreate( id, type, startNode, endNode );
        }

        @Override
        public void visitDeletedRelationship( long id )
        {
            try
            {
                storeLayer.relationshipVisit( id, edge );
                updateRelationshipCount( edge.startNode(), edge.type(), edge.endNode(), -1 );
            }
            catch ( EntityNotFoundException e )
            {
                throw new IllegalStateException(
                        "Relationship being deleted should exist along with its nodes.", e );
            }

            // record the state changes to be made to the store
            recordState.relDelete( id );
        }

        @Override
        public void visitNodePropertyChanges( long id, Iterator<DefinedProperty> added,
                Iterator<DefinedProperty> changed, Iterator<Integer> removed )
        {
            while ( removed.hasNext() )
            {
                recordState.nodeRemoveProperty( id, removed.next() );
            }
            while ( changed.hasNext() )
            {
                DefinedProperty prop = changed.next();
                recordState.nodeChangeProperty( id, prop.propertyKeyId(), prop.value() );
            }
            while ( added.hasNext() )
            {
                DefinedProperty prop = added.next();
                recordState.nodeAddProperty( id, prop.propertyKeyId(), prop.value() );
            }
        }

        @Override
        public void visitRelPropertyChanges( long id, Iterator<DefinedProperty> added,
                Iterator<DefinedProperty> changed, Iterator<Integer> removed )
        {
            while ( removed.hasNext() )
            {
                recordState.relRemoveProperty( id, removed.next() );
            }
            while ( changed.hasNext() )
            {
                DefinedProperty prop = changed.next();
                recordState.relChangeProperty( id, prop.propertyKeyId(), prop.value() );
            }
            while ( added.hasNext() )
            {
                DefinedProperty prop = added.next();
                recordState.relAddProperty( id, prop.propertyKeyId(), prop.value() );
            }
        }

        @Override
        public void visitGraphPropertyChanges( Iterator<DefinedProperty> added, Iterator<DefinedProperty> changed,
                Iterator<Integer> removed )
        {
            while ( removed.hasNext() )
            {
                recordState.graphRemoveProperty( removed.next() );
            }
            while ( changed.hasNext() )
            {
                DefinedProperty prop = changed.next();
                recordState.graphChangeProperty( prop.propertyKeyId(), prop.value() );
            }
            while ( added.hasNext() )
            {
                DefinedProperty prop = added.next();
                recordState.graphAddProperty( prop.propertyKeyId(), prop.value() );
            }
        }

        @Override
        public void visitNodeLabelChanges( long id, final Set<Integer> added, final Set<Integer> removed )
        {
            try ( StoreStatement statement = storeLayer.acquireStatement() )
            {
                // update counts
                if ( !(added.isEmpty() && removed.isEmpty()) )
                {
                    for ( Integer label : added )
                    {
                        counts.incrementNodeCount( label, 1 );
                    }
                    for ( Integer label : removed )
                    {
                        counts.incrementNodeCount( label, -1 );
                    }
                    // get the relationship counts from *before* this transaction,
                    // the relationship changes will compensate for what happens during the transaction
                    storeLayer.nodeVisitDegrees( statement, id, new DegreeVisitor()
                    {
                        @Override
                        public void visitDegree( int type, int outgoing, int incoming )
                        {
                            for ( Integer label : added )
                            {
                                updateRelationshipsCountsFromDegrees( type, label, outgoing, incoming );
                            }
                            for ( Integer label : removed )
                            {
                                updateRelationshipsCountsFromDegrees( type, label, -outgoing, -incoming );
                            }
                        }
                    } );
                }
            }

            // record the state changes to be made to the store
            for ( Integer label : removed )
            {
                recordState.removeLabelFromNode( label, id );
            }
            for ( Integer label : added )
            {
                recordState.addLabelToNode( label, id );
            }
        }

        @Override
        public void visitAddedIndex( IndexDescriptor element, boolean isConstraintIndex )
        {
            SchemaIndexProvider.Descriptor providerDescriptor = providerMap.getDefaultProvider()
                    .getProviderDescriptor();
            IndexRule rule;
            if ( isConstraintIndex )
            {
                rule = IndexRule.constraintIndexRule( schemaStorage.newRuleId(), element.getLabelId(),
                        element.getPropertyKeyId(), providerDescriptor,
                        null );
            }
            else
            {
                rule = IndexRule.indexRule( schemaStorage.newRuleId(), element.getLabelId(),
                        element.getPropertyKeyId(), providerDescriptor );
            }
            recordState.createSchemaRule( rule );
        }

        @Override
        public void visitRemovedIndex( IndexDescriptor element, boolean isConstraintIndex )
        {
            SchemaStorage.IndexRuleKind kind = isConstraintIndex ?
                    SchemaStorage.IndexRuleKind.CONSTRAINT
                    : SchemaStorage.IndexRuleKind.INDEX;
            IndexRule rule = schemaStorage.indexRule( element.getLabelId(), element.getPropertyKeyId(), kind );
            recordState.dropSchemaRule( rule );
        }

        @Override
        public void visitAddedUniquePropertyConstraint( UniquenessConstraint element )
        {
            clearState = true;
            long constraintId = schemaStorage.newRuleId();
            IndexRule indexRule = schemaStorage.indexRule(
                    element.label(),
                    element.propertyKey(),
                    SchemaStorage.IndexRuleKind.CONSTRAINT );
            recordState.createSchemaRule( UniquePropertyConstraintRule.uniquenessConstraintRule(
                    constraintId, element.label(), element.propertyKey(), indexRule.getId() ) );
            recordState.setConstraintIndexOwner( indexRule, constraintId );
        }

        @Override
        public void visitRemovedUniquePropertyConstraint( UniquenessConstraint element )
        {
            try
            {
                clearState = true;
                UniquePropertyConstraintRule rule = schemaStorage
                        .uniquenessConstraint( element.label(), element.propertyKey() );
                recordState.dropSchemaRule( rule );
            }
            catch ( SchemaRuleNotFoundException e )
            {
                throw new ThisShouldNotHappenError(
                        "Tobias Lindaaker",
                        "Constraint to be removed should exist, since its existence should " +
                                "have been validated earlier and the schema should have been locked." );
            }
            // Remove the index for the constraint as well
            visitRemovedIndex( new IndexDescriptor( element.label(), element.propertyKey() ), true );
        }

        @Override
        public void visitAddedNodeMandatoryPropertyConstraint( MandatoryNodePropertyConstraint element )
        {
            clearState = true;
            recordState.createSchemaRule( MandatoryNodePropertyConstraintRule.mandatoryNodePropertyConstraintRule(
                    schemaStorage.newRuleId(), element.label(), element.propertyKey() ) );
        }

        @Override
        public void visitRemovedNodeMandatoryPropertyConstraint( MandatoryNodePropertyConstraint element )
        {
            try
            {
                clearState = true;
                recordState.dropSchemaRule(
                        schemaStorage.mandatoryNodePropertyConstraint( element.label(), element.propertyKey() ) );
            }
            catch ( SchemaRuleNotFoundException e )
            {
                throw new IllegalStateException(
                        "Mandatory node property constraint to be removed should exist, since its existence should " +
                        "have been validated earlier and the schema should have been locked." );
            }
        }

        @Override
        public void visitAddedRelationshipMandatoryPropertyConstraint( MandatoryRelationshipPropertyConstraint element )
        {
            clearState = true;
            recordState.createSchemaRule( MandatoryRelationshipPropertyConstraintRule.mandatoryRelPropertyConstraintRule(
                    schemaStorage.newRuleId(), element.relationshipType(), element.propertyKey() ) );
        }

        @Override
        public void visitRemovedRelationshipMandatoryPropertyConstraint( MandatoryRelationshipPropertyConstraint element )
        {
            try
            {
                clearState = true;
                SchemaRule rule = schemaStorage.mandatoryRelationshipPropertyConstraint( element.relationshipType(),
                        element.propertyKey() );
                recordState.dropSchemaRule( rule );
            }
            catch ( SchemaRuleNotFoundException e )
            {
                throw new IllegalStateException(
                        "Mandatory relationship property constraint to be removed should exist, since its existence " +
                        "should have been validated earlier and the schema should have been locked." );
            }
        }

        @Override
        public void visitCreatedLabelToken( String name, int id )
        {
            recordState.createLabelToken( name, id );
        }

        @Override
        public void visitCreatedPropertyKeyToken( String name, int id )
        {
            recordState.createPropertyKeyToken( name, id );
        }

        @Override
        public void visitCreatedRelationshipTypeToken( String name, int id )
        {
            recordState.createRelationshipTypeToken( name, id );
        }

        @Override
        public void visitCreatedNodeLegacyIndex( String name, Map<String, String> config )
        {
            legacyIndexTransactionState.createIndex( IndexEntityType.Node, name, config );
        }

        @Override
        public void visitCreatedRelationshipLegacyIndex( String name, Map<String, String> config )
        {
            legacyIndexTransactionState.createIndex( IndexEntityType.Relationship, name, config );
        }
    }

    private void updateRelationshipsCountsFromDegrees( int type, int label, int outgoing, int incoming )
    {
        // untyped
        counts.incrementRelationshipCount( label, ANY_RELATIONSHIP_TYPE, ANY_LABEL, outgoing );
        counts.incrementRelationshipCount( ANY_LABEL, ANY_RELATIONSHIP_TYPE, label, incoming );
        // typed
        counts.incrementRelationshipCount( label, type, ANY_LABEL, outgoing );
        counts.incrementRelationshipCount( ANY_LABEL, type, label, incoming );
    }

    private void updateRelationshipCount( long startNode, int type, long endNode, int delta )
            throws EntityNotFoundException
    {
        updateRelationshipsCountsFromDegrees( type, ANY_LABEL, delta, 0 );
        for ( PrimitiveIntIterator startLabels = labelsOf( startNode ); startLabels.hasNext(); )
        {
            updateRelationshipsCountsFromDegrees( type, startLabels.next(), delta, 0 );
        }
        for ( PrimitiveIntIterator endLabels = labelsOf( endNode ); endLabels.hasNext(); )
        {
            updateRelationshipsCountsFromDegrees( type, endLabels.next(), 0, delta );
        }
    }

    private PrimitiveIntIterator labelsOf( long nodeId )
    {
        try ( StoreStatement statement = storeLayer.acquireStatement() )
        {
            return StateHandlingStatementOperations.nodeGetLabels( storeLayer, statement,
                    txState, nodeId );
        }
        catch ( EntityNotFoundException ex )
        {
            return PrimitiveIntCollections.emptyIterator();
        }
    }
}


File: community/kernel/src/main/java/org/neo4j/kernel/impl/api/store/DiskLayer.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.kernel.impl.api.store;

import java.util.Iterator;

import org.neo4j.collection.primitive.Primitive;
import org.neo4j.collection.primitive.PrimitiveIntCollections;
import org.neo4j.collection.primitive.PrimitiveIntIterator;
import org.neo4j.collection.primitive.PrimitiveIntObjectMap;
import org.neo4j.collection.primitive.PrimitiveIntObjectVisitor;
import org.neo4j.collection.primitive.PrimitiveIntSet;
import org.neo4j.collection.primitive.PrimitiveLongCollections.PrimitiveLongBaseIterator;
import org.neo4j.collection.primitive.PrimitiveLongIterator;
import org.neo4j.function.Function;
import org.neo4j.function.Predicate;
import org.neo4j.function.Predicates;
import org.neo4j.graphdb.Direction;
import org.neo4j.graphdb.TransactionFailureException;
import org.neo4j.kernel.api.EntityType;
import org.neo4j.kernel.api.ReadOperations;
import org.neo4j.kernel.api.constraints.NodePropertyConstraint;
import org.neo4j.kernel.api.constraints.PropertyConstraint;
import org.neo4j.kernel.api.constraints.RelationshipPropertyConstraint;
import org.neo4j.kernel.api.cursor.LabelCursor;
import org.neo4j.kernel.api.cursor.NodeCursor;
import org.neo4j.kernel.api.cursor.RelationshipCursor;
import org.neo4j.kernel.api.exceptions.EntityNotFoundException;
import org.neo4j.kernel.api.exceptions.LabelNotFoundKernelException;
import org.neo4j.kernel.api.exceptions.PropertyKeyIdNotFoundKernelException;
import org.neo4j.kernel.api.exceptions.RelationshipTypeIdNotFoundKernelException;
import org.neo4j.kernel.api.exceptions.index.IndexNotFoundKernelException;
import org.neo4j.kernel.api.exceptions.schema.IndexBrokenKernelException;
import org.neo4j.kernel.api.exceptions.schema.SchemaRuleNotFoundException;
import org.neo4j.kernel.api.exceptions.schema.TooManyLabelsException;
import org.neo4j.kernel.api.index.IndexDescriptor;
import org.neo4j.kernel.api.index.IndexReader;
import org.neo4j.kernel.api.index.InternalIndexState;
import org.neo4j.kernel.api.properties.DefinedProperty;
import org.neo4j.kernel.api.properties.PropertyKeyIdIterator;
import org.neo4j.kernel.impl.api.CountsAccessor;
import org.neo4j.kernel.impl.api.DegreeVisitor;
import org.neo4j.kernel.impl.api.KernelStatement;
import org.neo4j.kernel.impl.api.RelationshipVisitor;
import org.neo4j.kernel.impl.api.index.IndexingService;
import org.neo4j.kernel.impl.core.IteratingPropertyReceiver;
import org.neo4j.kernel.impl.core.LabelTokenHolder;
import org.neo4j.kernel.impl.core.PropertyKeyTokenHolder;
import org.neo4j.kernel.impl.core.RelationshipTypeTokenHolder;
import org.neo4j.kernel.impl.core.Token;
import org.neo4j.kernel.impl.core.TokenNotFoundException;
import org.neo4j.kernel.impl.store.CommonAbstractStore;
import org.neo4j.kernel.impl.store.InvalidRecordException;
import org.neo4j.kernel.impl.store.NeoStore;
import org.neo4j.kernel.impl.store.NodePropertyConstraintRule;
import org.neo4j.kernel.impl.store.NodeStore;
import org.neo4j.kernel.impl.store.PropertyConstraintRule;
import org.neo4j.kernel.impl.store.RelationshipGroupStore;
import org.neo4j.kernel.impl.store.RelationshipPropertyConstraintRule;
import org.neo4j.kernel.impl.store.RelationshipStore;
import org.neo4j.kernel.impl.store.SchemaStorage;
import org.neo4j.kernel.impl.store.UnderlyingStorageException;
import org.neo4j.kernel.impl.store.record.IndexRule;
import org.neo4j.kernel.impl.store.record.NodeRecord;
import org.neo4j.kernel.impl.store.record.Record;
import org.neo4j.kernel.impl.store.record.RelationshipGroupRecord;
import org.neo4j.kernel.impl.store.record.RelationshipRecord;
import org.neo4j.kernel.impl.store.record.SchemaRule;
import org.neo4j.kernel.impl.transaction.state.PropertyLoader;
import org.neo4j.kernel.impl.util.Cursors;
import org.neo4j.kernel.impl.util.PrimitiveLongResourceIterator;

import static org.neo4j.collection.primitive.PrimitiveLongCollections.count;
import static org.neo4j.helpers.collection.Iterables.filter;
import static org.neo4j.helpers.collection.Iterables.map;
import static org.neo4j.helpers.collection.IteratorUtil.resourceIterator;
import static org.neo4j.kernel.impl.store.record.RecordLoad.CHECK;
import static org.neo4j.register.Registers.newDoubleLongRegister;

/**
 * Default implementation of StoreReadLayer. Delegates to NeoStore and indexes.
 */
public class DiskLayer implements StoreReadLayer
{
    private static final Function<PropertyConstraintRule,PropertyConstraint> RULE_TO_CONSTRAINT =
            new Function<PropertyConstraintRule,PropertyConstraint>()
            {
                @Override
                public PropertyConstraint apply( PropertyConstraintRule rule )
                {
                    // We can use propertyKeyId straight up here, without reading from the record, since we have
                    // verified that it has that propertyKeyId in the predicate. And since we currently only support
                    // uniqueness on single properties, there is nothing else to pass in to UniquenessConstraint.
                    return rule.toConstraint();
                }
            };

    private static final Function<NodePropertyConstraintRule,NodePropertyConstraint> NODE_RULE_TO_CONSTRAINT =
            new Function<NodePropertyConstraintRule,NodePropertyConstraint>()
            {
                @Override
                public NodePropertyConstraint apply( NodePropertyConstraintRule rule )
                {
                    return rule.toConstraint();
                }
            };

    private static final Function<RelationshipPropertyConstraintRule,RelationshipPropertyConstraint> REL_RULE_TO_CONSTRAINT =
            new Function<RelationshipPropertyConstraintRule,RelationshipPropertyConstraint>()
            {
                @Override
                public RelationshipPropertyConstraint apply( RelationshipPropertyConstraintRule rule )
                {
                    return rule.toConstraint();
                }
            };

    // These token holders should perhaps move to the cache layer.. not really any reason to have them here?
    private final PropertyKeyTokenHolder propertyKeyTokenHolder;
    private final LabelTokenHolder labelTokenHolder;
    private final RelationshipTypeTokenHolder relationshipTokenHolder;

    private final NeoStore neoStore;
    private final IndexingService indexService;
    private final NodeStore nodeStore;
    private final RelationshipGroupStore relationshipGroupStore;
    private final RelationshipStore relationshipStore;
    private final SchemaStorage schemaStorage;
    private final CountsAccessor counts;
    private final PropertyLoader propertyLoader;

    public DiskLayer( PropertyKeyTokenHolder propertyKeyTokenHolder, LabelTokenHolder labelTokenHolder,
            RelationshipTypeTokenHolder relationshipTokenHolder, SchemaStorage schemaStorage, NeoStore neoStore,
            IndexingService indexService )
    {
        this.relationshipTokenHolder = relationshipTokenHolder;
        this.schemaStorage = schemaStorage;
        this.indexService = indexService;
        this.propertyKeyTokenHolder = propertyKeyTokenHolder;
        this.labelTokenHolder = labelTokenHolder;
        this.neoStore = neoStore;
        this.nodeStore = this.neoStore.getNodeStore();
        this.relationshipStore = this.neoStore.getRelationshipStore();
        this.relationshipGroupStore = this.neoStore.getRelationshipGroupStore();
        this.counts = neoStore.getCounts();
        this.propertyLoader = new PropertyLoader( neoStore );

    }

    @Override
    public StoreStatement acquireStatement()
    {
        return neoStore.acquireStatement();
    }

    @Override
    public int labelGetOrCreateForName( String label ) throws TooManyLabelsException
    {
        try
        {
            return labelTokenHolder.getOrCreateId( label );
        }
        catch ( TransactionFailureException e )
        {
            // Temporary workaround for the property store based label
            // implementation. Actual
            // implementation should not depend on internal kernel exception
            // messages like this.
            if ( e.getCause() instanceof UnderlyingStorageException
                    && e.getCause().getMessage().equals( "Id capacity exceeded" ) )
            {
                throw new TooManyLabelsException( e );
            }
            throw e;
        }
    }

    @Override
    public int labelGetForName( String label )
    {
        return labelTokenHolder.getIdByName( label );
    }

    @Override
    public PrimitiveIntIterator nodeGetLabels( StoreStatement statement, long nodeId ) throws EntityNotFoundException
    {
        try ( NodeCursor nodeCursor = statement.acquireSingleNodeCursor( nodeId ) )
        {
            if ( nodeCursor.next() )
            {
                return Cursors.intIterator( nodeCursor.labels(), LabelCursor.GET_LABEL );
            }
            throw new EntityNotFoundException( EntityType.NODE, nodeId );
        }
    }

    @Override
    public RelationshipIterator nodeListRelationships( StoreStatement statement,
            long nodeId,
            Direction direction )
            throws EntityNotFoundException
    {
        return nodeListRelationships( statement, nodeId, direction, null );
    }

    @Override
    public RelationshipIterator nodeListRelationships( final StoreStatement statement,
            long nodeId,
            Direction direction,
            int[] relTypes )
            throws EntityNotFoundException
    {
        try ( final NodeCursor nodeCursor = statement.acquireSingleNodeCursor( nodeId ) )
        {
            if ( nodeCursor.next() )
            {
                return new CursorRelationshipIterator( nodeCursor.relationships( direction, relTypes ) );
            }
            throw new EntityNotFoundException( EntityType.NODE, nodeId );
        }
    }

    @Override
    public int nodeGetDegree( StoreStatement statement,
            long nodeId,
            Direction direction ) throws EntityNotFoundException
    {
        NodeRecord node = nodeStore.loadRecord( nodeId, null );
        if ( node == null )
        {
            throw new EntityNotFoundException( EntityType.NODE, nodeId );
        }

        if ( node.isDense() )
        {
            long groupId = node.getNextRel();
            long count = 0;
            while ( groupId != Record.NO_NEXT_RELATIONSHIP.intValue() )
            {
                RelationshipGroupRecord group = relationshipGroupStore.getRecord( groupId );
                count += nodeDegreeByDirection( nodeId, group, direction );
                groupId = group.getNext();
            }
            return (int) count;
        }

        return count( nodeListRelationships( statement, nodeId, direction ) );
    }

    @Override
    public int nodeGetDegree( StoreStatement statement, long nodeId,
            Direction direction,
            int relType ) throws EntityNotFoundException
    {
        NodeRecord node = nodeStore.loadRecord( nodeId, null );
        if ( node == null )
        {
            throw new EntityNotFoundException( EntityType.NODE, nodeId );
        }

        if ( node.isDense() )
        {
            long groupId = node.getNextRel();
            while ( groupId != Record.NO_NEXT_RELATIONSHIP.intValue() )
            {
                RelationshipGroupRecord group = relationshipGroupStore.getRecord( groupId );
                if ( group.getType() == relType )
                {
                    return (int) nodeDegreeByDirection( nodeId, group, direction );
                }
                groupId = group.getNext();
            }
            return 0;
        }

        return count( nodeListRelationships( statement, nodeId, direction, new int[]{relType} ) );
    }

    private long nodeDegreeByDirection( long nodeId, RelationshipGroupRecord group, Direction direction )
    {
        long loopCount = countByFirstPrevPointer( nodeId, group.getFirstLoop() );
        switch ( direction )
        {
            case OUTGOING:
                return countByFirstPrevPointer( nodeId, group.getFirstOut() ) + loopCount;
            case INCOMING:
                return countByFirstPrevPointer( nodeId, group.getFirstIn() ) + loopCount;
            case BOTH:
                return countByFirstPrevPointer( nodeId, group.getFirstOut() ) +
                        countByFirstPrevPointer( nodeId, group.getFirstIn() ) + loopCount;
            default:
                throw new IllegalArgumentException( direction.name() );
        }
    }

    @Override
    public boolean nodeVisitDegrees( StoreStatement statement, final long nodeId, final DegreeVisitor visitor )
    {
        NodeRecord node = nodeStore.loadRecord( nodeId, null );
        if ( node == null )
        {
            return true;
        }

        if ( node.isDense() )
        {
            long groupId = node.getNextRel();
            while ( groupId != Record.NO_NEXT_RELATIONSHIP.intValue() )
            {
                RelationshipGroupRecord group = relationshipGroupStore.getRecord( groupId );
                long outCount = countByFirstPrevPointer( nodeId, group.getFirstOut() );
                long inCount = countByFirstPrevPointer( nodeId, group.getFirstIn() );
                long loopCount = countByFirstPrevPointer( nodeId, group.getFirstLoop() );
                visitor.visitDegree( group.getType(), (int) (outCount + loopCount), (int) (inCount + loopCount) );
                groupId = group.getNext();
            }
        }
        else
        {
            final PrimitiveIntObjectMap<int[]> degrees = Primitive.intObjectMap( 5 );
            RelationshipVisitor<RuntimeException> typeVisitor = new RelationshipVisitor<RuntimeException>()
            {
                @Override
                public void visit( long relId, int type, long startNode, long endNode ) throws RuntimeException
                {
                    int[] byType = degrees.get( type );
                    if ( byType == null )
                    {
                        degrees.put( type, byType = new int[3] );
                    }
                    byType[directionOf( nodeId, relId, startNode, endNode ).ordinal()]++;
                }
            };
            RelationshipIterator relationships;
            try
            {
                relationships = nodeListRelationships( statement, nodeId, Direction.BOTH );
                while ( relationships.hasNext() )
                {
                    relationships.relationshipVisit( relationships.next(), typeVisitor );
                }

                degrees.visitEntries( new PrimitiveIntObjectVisitor<int[], RuntimeException>()
                {
                    @Override
                    public boolean visited( int type, int[] degrees /*out,in,loop*/ ) throws RuntimeException
                    {
                        visitor.visitDegree( type, degrees[0] + degrees[2], degrees[1] + degrees[2] );
                        return false;
                    }
                } );
            }
            catch ( EntityNotFoundException e )
            {
                // OK?
            }
        }
        return false;
    }

    private Direction directionOf( long nodeId, long relationshipId, long startNode, long endNode )
    {
        if ( startNode == nodeId )
        {
            return endNode == nodeId ? Direction.BOTH : Direction.OUTGOING;
        }
        if ( endNode == nodeId )
        {
            return Direction.INCOMING;
        }
        throw new InvalidRecordException( "Node " + nodeId + " neither start nor end node of relationship " +
                relationshipId + " with startNode:" + startNode + " and endNode:" + endNode );
    }

    private long countByFirstPrevPointer( long nodeId, long relationshipId )
    {
        if ( relationshipId == Record.NO_NEXT_RELATIONSHIP.intValue() )
        {
            return 0;
        }
        RelationshipRecord record = relationshipStore.getRecord( relationshipId );
        if ( record.getFirstNode() == nodeId )
        {
            return record.getFirstPrevRel();
        }
        if ( record.getSecondNode() == nodeId )
        {
            return record.getSecondPrevRel();
        }
        throw new InvalidRecordException( "Node " + nodeId + " neither start nor end node of " + record );
    }

    @Override
    public PrimitiveIntIterator nodeGetRelationshipTypes( StoreStatement statement,
            long nodeId ) throws EntityNotFoundException
    {
        final NodeRecord node = nodeStore.loadRecord( nodeId, null );
        if ( node == null )
        {
            throw new EntityNotFoundException( EntityType.NODE, nodeId );
        }

        if ( node.isDense() )
        {
            return new PrimitiveIntCollections.PrimitiveIntBaseIterator()
            {
                private long groupId = node.getNextRel();

                @Override
                protected boolean fetchNext()
                {
                    if ( groupId == Record.NO_NEXT_RELATIONSHIP.intValue() )
                    {
                        return false;
                    }

                    RelationshipGroupRecord group = relationshipGroupStore.getRecord( groupId );
                    try
                    {
                        return next( group.getType() );
                    }
                    finally
                    {
                        groupId = group.getNext();
                    }
                }
            };
        }

        final PrimitiveIntSet types = Primitive.intSet( 5 );
        RelationshipVisitor<RuntimeException> visitor = new RelationshipVisitor<RuntimeException>()
        {
            @Override
            public void visit( long relId, int type, long startNode, long endNode ) throws RuntimeException
            {
                types.add( type );
            }
        };
        RelationshipIterator relationships = nodeListRelationships( statement, nodeId, Direction.BOTH );
        while ( relationships.hasNext() )
        {
            relationships.relationshipVisit( relationships.next(), visitor );
        }
        return types.iterator();
    }

    @Override
    public String labelGetName( int labelId ) throws LabelNotFoundKernelException
    {
        try
        {
            return labelTokenHolder.getTokenById( labelId ).name();
        }
        catch ( TokenNotFoundException e )
        {
            throw new LabelNotFoundKernelException( "Label by id " + labelId, e );
        }
    }

    @Override
    public PrimitiveLongIterator nodesGetForLabel( KernelStatement state, int labelId )
    {
        return state.getLabelScanReader().nodesWithLabel( labelId );
    }

    @Override
    public PrimitiveLongIterator nodesGetFromIndexSeek( KernelStatement state, IndexDescriptor index,
            Object value ) throws IndexNotFoundKernelException
    {
        IndexReader reader = state.getIndexReader( index );
        return reader.seek( value );
    }

    @Override
    public PrimitiveLongIterator nodesGetFromIndexRangeSeekByNumber( KernelStatement statement,
                                                                     IndexDescriptor index,
                                                                     Number lower, boolean includeLower,
                                                                     Number upper, boolean includeUpper )
            throws IndexNotFoundKernelException

    {
        IndexReader reader = statement.getIndexReader( index );
        return reader.rangeSeekByNumber( lower, includeLower, upper, includeUpper );
    }

    @Override
    public PrimitiveLongIterator nodesGetFromIndexRangeSeekByString( KernelStatement statement,
                                                                     IndexDescriptor index,
                                                                     String lower, boolean includeLower,
                                                                     String upper, boolean includeUpper )
            throws IndexNotFoundKernelException

    {
        IndexReader reader = statement.getIndexReader( index );
        return reader.rangeSeekByString( lower, includeLower, upper, includeUpper );
    }

    @Override
    public PrimitiveLongIterator nodesGetFromIndexRangeSeekByPrefix( KernelStatement state,
                                                                     IndexDescriptor index,
                                                                     String prefix )
            throws IndexNotFoundKernelException
    {
        IndexReader reader = state.getIndexReader( index );
        return reader.rangeSeekByPrefix( prefix );
    }

    @Override
    public PrimitiveLongIterator nodesGetFromIndexScan( KernelStatement state, IndexDescriptor index ) throws
            IndexNotFoundKernelException
    {
        IndexReader reader = state.getIndexReader( index );
        return reader.scan();
    }

    @Override
    public IndexDescriptor indexesGetForLabelAndPropertyKey( int labelId, int propertyKey )
    {
        return descriptor( schemaStorage.indexRule( labelId, propertyKey ) );
    }

    private static IndexDescriptor descriptor( IndexRule ruleRecord )
    {
        return new IndexDescriptor( ruleRecord.getLabel(), ruleRecord.getPropertyKey() );
    }

    @Override
    public Iterator<IndexDescriptor> indexesGetForLabel( int labelId )
    {
        return getIndexDescriptorsFor( indexRules( labelId ) );
    }

    @Override
    public Iterator<IndexDescriptor> indexesGetAll()
    {
        return getIndexDescriptorsFor( INDEX_RULES );
    }

    @Override
    public Iterator<IndexDescriptor> uniqueIndexesGetForLabel( int labelId )
    {
        return getIndexDescriptorsFor( constraintIndexRules( labelId ) );
    }

    @Override
    public Iterator<IndexDescriptor> uniqueIndexesGetAll()
    {
        return getIndexDescriptorsFor( CONSTRAINT_INDEX_RULES );
    }

    private static Predicate<SchemaRule> indexRules( final int labelId )
    {
        return new Predicate<SchemaRule>()
        {

            @Override
            public boolean test( SchemaRule rule )
            {
                return rule.getLabel() == labelId && rule.getKind() == SchemaRule.Kind.INDEX_RULE;
            }
        };
    }

    private static Predicate<SchemaRule> constraintIndexRules( final int labelId )
    {
        return new Predicate<SchemaRule>()
        {

            @Override
            public boolean test( SchemaRule rule )
            {
                return rule.getLabel() == labelId && rule.getKind() == SchemaRule.Kind.CONSTRAINT_INDEX_RULE;
            }
        };
    }

    private static final Predicate<SchemaRule> INDEX_RULES = new Predicate<SchemaRule>()
    {

        @Override
        public boolean test( SchemaRule rule )
        {
            return rule.getKind() == SchemaRule.Kind.INDEX_RULE;
        }
    }, CONSTRAINT_INDEX_RULES = new Predicate<SchemaRule>()
    {

        @Override
        public boolean test( SchemaRule rule )
        {
            return rule.getKind() == SchemaRule.Kind.CONSTRAINT_INDEX_RULE;
        }
    };

    private Iterator<IndexDescriptor> getIndexDescriptorsFor( Predicate<SchemaRule> filter )
    {
        Iterator<SchemaRule> filtered = filter( filter, neoStore.getSchemaStore().loadAllSchemaRules() );

        return map( new Function<SchemaRule, IndexDescriptor>()
        {

            @Override
            public IndexDescriptor apply( SchemaRule from )
            {
                return descriptor( (IndexRule) from );
            }
        }, filtered );
    }

    @Override
    public Long indexGetOwningUniquenessConstraintId( IndexDescriptor index )
            throws SchemaRuleNotFoundException
    {
        return schemaStorage.indexRule( index.getLabelId(), index.getPropertyKeyId() ).getOwningConstraint();
    }

    @Override
    public IndexRule indexRule( IndexDescriptor index, SchemaStorage.IndexRuleKind kind )
    {
        throw new UnsupportedOperationException();
    }

    @Override
    public long indexGetCommittedId( IndexDescriptor index, SchemaStorage.IndexRuleKind kind )
            throws SchemaRuleNotFoundException
    {
        return schemaStorage.indexRule( index.getLabelId(), index.getPropertyKeyId() ).getId();
    }

    @Override
    public InternalIndexState indexGetState( IndexDescriptor descriptor )
            throws IndexNotFoundKernelException
    {
        return indexService.getIndexProxy( descriptor ).getState();
    }

    @Override
    public long indexSize( IndexDescriptor descriptor ) throws IndexNotFoundKernelException
    {
        return indexService.indexSize( descriptor );
    }

    @Override
    public double indexUniqueValuesPercentage( IndexDescriptor descriptor ) throws IndexNotFoundKernelException
    {
        return indexService.indexUniqueValuesPercentage( descriptor );
    }

    @Override
    public String indexGetFailure( IndexDescriptor descriptor ) throws IndexNotFoundKernelException
    {
        return indexService.getIndexProxy( descriptor ).getPopulationFailure().asString();
    }

    @Override
    public Iterator<NodePropertyConstraint> constraintsGetForLabelAndPropertyKey( int labelId, final int propertyKeyId )
    {
        return schemaStorage.schemaRulesForNodes( NODE_RULE_TO_CONSTRAINT, NodePropertyConstraintRule.class,
                labelId, new Predicate<NodePropertyConstraintRule>()
                {
                    @Override
                    public boolean test( NodePropertyConstraintRule rule )
                    {
                        return rule.containsPropertyKeyId( propertyKeyId );
                    }
                } );
    }

    @Override
    public Iterator<NodePropertyConstraint> constraintsGetForLabel( int labelId )
    {
        return schemaStorage.schemaRulesForNodes( NODE_RULE_TO_CONSTRAINT, NodePropertyConstraintRule.class,
                labelId, Predicates.<NodePropertyConstraintRule>alwaysTrue() );
    }

    @Override
    public Iterator<RelationshipPropertyConstraint> constraintsGetForRelationshipTypeAndPropertyKey( int typeId,
            final int propertyKeyId )
    {
        return schemaStorage.schemaRulesForRelationships( REL_RULE_TO_CONSTRAINT,
                RelationshipPropertyConstraintRule.class, typeId, new Predicate<RelationshipPropertyConstraintRule>()
                {
                    @Override
                    public boolean test( RelationshipPropertyConstraintRule rule )
                    {
                        return rule.containsPropertyKeyId( propertyKeyId );
                    }
                } );
    }

    @Override
    public Iterator<RelationshipPropertyConstraint> constraintsGetForRelationshipType( int typeId )
    {
        return schemaStorage.schemaRulesForRelationships( REL_RULE_TO_CONSTRAINT,
                RelationshipPropertyConstraintRule.class, typeId,
                Predicates.<RelationshipPropertyConstraintRule>alwaysTrue() );
    }

    @Override
    public Iterator<PropertyConstraint> constraintsGetAll()
    {
        return schemaStorage.schemaRules( RULE_TO_CONSTRAINT, PropertyConstraintRule.class);
    }

    @Override
    public PrimitiveLongResourceIterator nodeGetFromUniqueIndexSeek( KernelStatement state, IndexDescriptor descriptor,
            Object value ) throws IndexNotFoundKernelException, IndexBrokenKernelException
    {
        /* Here we have an intricate scenario where we need to return the PrimitiveLongIterator
         * since subsequent filtering will happen outside, but at the same time have the ability to
         * close the IndexReader when done iterating over the lookup result. This is because we get
         * a fresh reader that isn't associated with the current transaction and hence will not be
         * automatically closed. */
        IndexReader reader = state.getFreshIndexReader( descriptor );
        return resourceIterator( reader.seek( value ), reader );
    }

    @Override
    public int propertyKeyGetOrCreateForName( String propertyKey )
    {
        return propertyKeyTokenHolder.getOrCreateId( propertyKey );
    }

    @Override
    public int propertyKeyGetForName( String propertyKey )
    {
        return propertyKeyTokenHolder.getIdByName( propertyKey );
    }

    @Override
    public String propertyKeyGetName( int propertyKeyId )
            throws PropertyKeyIdNotFoundKernelException
    {
        try
        {
            return propertyKeyTokenHolder.getTokenById( propertyKeyId ).name();
        }
        catch ( TokenNotFoundException e )
        {
            throw new PropertyKeyIdNotFoundKernelException( propertyKeyId, e );
        }
    }

    @Override
    public PrimitiveIntIterator graphGetPropertyKeys( KernelStatement state )
    {
        return new PropertyKeyIdIterator(propertyLoader.graphLoadProperties( new IteratingPropertyReceiver() ));
    }

    @Override
    public Object graphGetProperty( int propertyKeyId )
    {
        throw new UnsupportedOperationException();
    }

    @Override
    public Iterator<DefinedProperty> graphGetAllProperties()
    {
        return propertyLoader.graphLoadProperties( new IteratingPropertyReceiver() );
    }

    @Override
    public Iterator<Token> propertyKeyGetAllTokens()
    {
        return propertyKeyTokenHolder.getAllTokens().iterator();
    }

    @Override
    public Iterator<Token> labelsGetAllTokens()
    {
        return labelTokenHolder.getAllTokens().iterator();
    }

    @Override
    public int relationshipTypeGetForName( String relationshipTypeName )
    {
        return relationshipTokenHolder.getIdByName( relationshipTypeName );
    }

    @Override
    public String relationshipTypeGetName( int relationshipTypeId ) throws RelationshipTypeIdNotFoundKernelException
    {
        try
        {
            return relationshipTokenHolder.getTokenById( relationshipTypeId ).name();
        }
        catch ( TokenNotFoundException e )
        {
            throw new RelationshipTypeIdNotFoundKernelException( relationshipTypeId, e );
        }
    }

    @Override
    public int relationshipTypeGetOrCreateForName( String relationshipTypeName )
    {
        return relationshipTokenHolder.getOrCreateId( relationshipTypeName );
    }

    @Override
    public <EXCEPTION extends Exception> void relationshipVisit( long relationshipId,
            RelationshipVisitor<EXCEPTION> relationshipVisitor ) throws EntityNotFoundException, EXCEPTION
    {
        // TODO Please don't create a record for this, it's ridiculous
        RelationshipRecord record;
        try
        {
            record = relationshipStore.getRecord( relationshipId );
        }
        catch ( InvalidRecordException e )
        {
            throw new EntityNotFoundException( EntityType.RELATIONSHIP, relationshipId );
        }
        relationshipVisitor.visit( relationshipId, record.getType(), record.getFirstNode(), record.getSecondNode() );
    }

    @Override
    public long highestNodeIdInUse()
    {
        return nodeStore.getHighestPossibleIdInUse();
    }

    @Override
    public PrimitiveLongIterator nodesGetAll()
    {
        return new PrimitiveLongBaseIterator()
        {
            private final NodeStore store = neoStore.getNodeStore();
            private long highId = store.getHighestPossibleIdInUse();
            private long currentId;
            private final NodeRecord reusableNodeRecord = new NodeRecord( -1 ); // reused

            @Override
            protected boolean fetchNext()
            {
                while ( true )
                {   // This outer loop is for checking if highId has changed since we started.
                    while ( currentId <= highId )
                    {
                        try
                        {
                            NodeRecord record = store.loadRecord( currentId, reusableNodeRecord );
                            if ( record != null && record.inUse() )
                            {
                                return next( record.getId() );
                            }
                        }
                        finally
                        {
                            currentId++;
                        }
                    }

                    long newHighId = store.getHighestPossibleIdInUse();
                    if ( newHighId > highId )
                    {
                        highId = newHighId;
                    }
                    else
                    {
                        break;
                    }
                }
                return false;
            }
        };
    }

    @Override
    public NodeCursor nodesGetAllCursor( StoreStatement statement )
    {
        return statement.acquireIteratorNodeCursor( new AllStoreIdIterator( neoStore.getNodeStore() ) );
    }

    @Override
    public RelationshipIterator relationshipsGetAll()
    {
        return new RelationshipIterator.BaseIterator()
        {
            private final RelationshipStore store = neoStore.getRelationshipStore();
            private long highId = store.getHighestPossibleIdInUse();
            private long currentId;
            private final RelationshipRecord reusableRecord = new RelationshipRecord( -1 ); // reused

            @Override
            protected boolean fetchNext()
            {
                while ( true )
                {   // This outer loop is for checking if highId has changed since we started.
                    while ( currentId <= highId )
                    {
                        try
                        {
                            if ( store.fillRecord( currentId, reusableRecord, CHECK ) && reusableRecord.inUse() )
                            {
                                return next( reusableRecord.getId() );
                            }
                        }
                        finally
                        {
                            currentId++;
                        }
                    }

                    long newHighId = store.getHighestPossibleIdInUse();
                    if ( newHighId > highId )
                    {
                        highId = newHighId;
                    }
                    else
                    {
                        break;
                    }
                }
                return false;
            }

            @Override
            public <EXCEPTION extends Exception> boolean relationshipVisit( long relationshipId,
                    RelationshipVisitor<EXCEPTION> visitor ) throws EXCEPTION
            {
                visitor.visit( relationshipId, reusableRecord.getType(),
                        reusableRecord.getFirstNode(), reusableRecord.getSecondNode() );
                return false;
            }
        };
    }

    @Override
    public RelationshipCursor relationshipsGetAllCursor( StoreStatement storeStatement )
    {
        return storeStatement.acquireIteratorRelationshipCursor(
                new AllStoreIdIterator( neoStore.getRelationshipStore() ) );
    }

    @Override
    public long reserveNode()
    {
        return nodeStore.nextId();
    }

    @Override
    public long reserveRelationship()
    {
        return relationshipStore.nextId();
    }

    @Override
    public void releaseNode( long id )
    {
        nodeStore.freeId( id );
    }

    @Override
    public void releaseRelationship( long id )
    {
        relationshipStore.freeId( id );
    }

    @Override
    public long countsForNode( int labelId )
    {
        return counts.nodeCount( labelId, newDoubleLongRegister() ).readSecond();
    }

    @Override
    public long countsForRelationship( int startLabelId, int typeId, int endLabelId )
    {
        if ( !(startLabelId == ReadOperations.ANY_LABEL || endLabelId == ReadOperations.ANY_LABEL) )
        {
            throw new UnsupportedOperationException( "not implemented" );
        }
        return counts.relationshipCount( startLabelId, typeId, endLabelId, newDoubleLongRegister() ).readSecond();
    }

    private class AllStoreIdIterator extends PrimitiveLongBaseIterator
    {
        private final CommonAbstractStore store;
        private long highId;
        private long currentId;

        public AllStoreIdIterator( CommonAbstractStore store )
        {
            this.store = store;
            highId = store.getHighestPossibleIdInUse();
        }

        @Override
        protected boolean fetchNext()
        {
            while ( true )
            {   // This outer loop is for checking if highId has changed since we started.
                if ( currentId <= highId )
                {
                    try
                    {
                        return next( currentId );
                    }
                    finally
                    {
                        currentId++;
                    }
                }

                long newHighId = store.getHighestPossibleIdInUse();
                if ( newHighId > highId )
                {
                    highId = newHighId;
                }
                else
                {
                    break;
                }
            }
            return false;
        }
    }
}


File: community/kernel/src/main/java/org/neo4j/kernel/impl/api/store/SchemaCache.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.kernel.impl.api.store;

import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Map;

import org.neo4j.function.Predicate;
import org.neo4j.helpers.collection.Iterables;
import org.neo4j.kernel.api.constraints.NodePropertyConstraint;
import org.neo4j.kernel.api.constraints.PropertyConstraint;
import org.neo4j.kernel.api.constraints.RelationshipPropertyConstraint;
import org.neo4j.kernel.api.index.IndexDescriptor;
import org.neo4j.kernel.impl.store.NodePropertyConstraintRule;
import org.neo4j.kernel.impl.store.RelationshipPropertyConstraintRule;
import org.neo4j.kernel.impl.store.record.IndexRule;
import org.neo4j.kernel.impl.store.record.SchemaRule;

import static org.neo4j.helpers.collection.Iterables.filter;

/**
 * A cache of {@link SchemaRule schema rules} as well as enforcement of schema consistency.
 * Will always reflect the committed state of the schema store.
 *
 * Assume synchronization/locking is done outside, with locks.
 *
 * @author Mattias Persson
 * @author Stefan Plantikow
 */
public class SchemaCache
{
    private final Map<Long, SchemaRule> rulesByIdMap = new HashMap<>();

    private final Collection<NodePropertyConstraint> nodeConstraints = new HashSet<>();
    private final Collection<RelationshipPropertyConstraint> relationshipConstraints = new HashSet<>();
    private final Map<Integer, Map<Integer, CommittedIndexDescriptor>> indexDescriptors = new HashMap<>();

    public SchemaCache( Iterable<SchemaRule> initialRules )
    {
        splitUpInitialRules( initialRules );
    }

    private void splitUpInitialRules( Iterable<SchemaRule> initialRules )
    {
        for ( SchemaRule rule : initialRules )
        {
            addSchemaRule( rule );
        }
    }

    public Iterable<SchemaRule> schemaRules()
    {
        return rulesByIdMap.values();
    }

    public Iterable<SchemaRule> schemaRulesForLabel( final int label )
    {
        return filter( new Predicate<SchemaRule>()
        {
            @Override
            public boolean test( SchemaRule schemaRule )
            {
                return schemaRule.getKind() != SchemaRule.Kind.MANDATORY_RELATIONSHIP_PROPERTY_CONSTRAINT &&
                       schemaRule.getLabel() == label;
            }
        }, schemaRules() );
    }

    public Iterable<SchemaRule> schemaRulesForRelationshipType( final int typeId )
    {
        return filter( new Predicate<SchemaRule>()
        {
            @Override
            public boolean test( SchemaRule schemaRule )
            {
                return schemaRule.getKind() == SchemaRule.Kind.MANDATORY_RELATIONSHIP_PROPERTY_CONSTRAINT &&
                       schemaRule.getRelationshipType() == typeId;
            }
        }, schemaRules() );
    }

    public Iterator<PropertyConstraint> constraints()
    {
        return Iterables.concat( nodeConstraints.iterator(), relationshipConstraints.iterator() );
    }

    public Iterator<NodePropertyConstraint> constraintsForLabel( final int label )
    {
        return filter( new Predicate<NodePropertyConstraint>()
        {
            @Override
            public boolean test( NodePropertyConstraint constraint )
            {
                return constraint.label() == label;
            }
        }, nodeConstraints.iterator() );
    }

    public Iterator<NodePropertyConstraint> constraintsForLabelAndProperty( final int label, final int property )
    {
        return filter( new Predicate<NodePropertyConstraint>()
        {
            @Override
            public boolean test( NodePropertyConstraint constraint )
            {
                return constraint.label() == label && constraint.propertyKey() == property;
            }
        }, nodeConstraints.iterator() );
    }

    public Iterator<RelationshipPropertyConstraint> constraintsForRelationshipType( final int typeId )
    {
        return filter( new Predicate<RelationshipPropertyConstraint>()
        {
            @Override
            public boolean test( RelationshipPropertyConstraint constraint )
            {
                return constraint.relationshipType() == typeId;
            }
        }, relationshipConstraints.iterator() );
    }

    public Iterator<RelationshipPropertyConstraint> constraintsForRelationshipTypeAndProperty( final int typeId,
            final int propertyKeyId )
    {
        return filter( new Predicate<RelationshipPropertyConstraint>()
        {
            @Override
            public boolean test( RelationshipPropertyConstraint constraint )
            {
                return constraint.relationshipType() == typeId && constraint.propertyKey() == propertyKeyId;
            }
        }, relationshipConstraints.iterator() );
    }

    public void addSchemaRule( SchemaRule rule )
    {
        rulesByIdMap.put( rule.getId(), rule );

        if ( rule instanceof NodePropertyConstraintRule )
        {
            nodeConstraints.add( ((NodePropertyConstraintRule) rule).toConstraint() );
        }
        else if ( rule instanceof RelationshipPropertyConstraintRule )
        {
            relationshipConstraints.add( ((RelationshipPropertyConstraintRule) rule).toConstraint() );
        }
        else if ( rule instanceof IndexRule )
        {
            IndexRule indexRule = (IndexRule) rule;
            Map<Integer, CommittedIndexDescriptor> byLabel = indexDescriptors.get( indexRule.getLabel() );
            if ( byLabel == null )
            {
                indexDescriptors.put( indexRule.getLabel(), byLabel = new HashMap<>() );
            }
            byLabel.put( indexRule.getPropertyKey(), new CommittedIndexDescriptor( indexRule.getLabel(),
                    indexRule.getPropertyKey(), indexRule.getId() ) );
        }
    }

    public void clear()
    {
        rulesByIdMap.clear();
        nodeConstraints.clear();
        relationshipConstraints.clear();
        indexDescriptors.clear();
    }

    public void load( Iterator<SchemaRule> schemaRuleIterator )
    {
        clear();
        for ( SchemaRule schemaRule : Iterables.toList( schemaRuleIterator ) )
        {
            addSchemaRule( schemaRule );
        }
    }

    // We could have had this class extend IndexDescriptor instead. That way we could have gotten the id
    // from an IndexDescriptor instance directly. The problem is that it would only work for index descriptors
    // instantiated by a SchemaCache. Perhaps that is always the case. Anyways, doing it like that resulted
    // in unit test failures regarding the schema cache, so this way (the wrapping way) is a more generic
    // and stable way of doing it.
    private static class CommittedIndexDescriptor
    {
        private final IndexDescriptor descriptor;
        private final long id;

        public CommittedIndexDescriptor( int labelId, int propertyKey, long id )
        {
            this.descriptor = new IndexDescriptor( labelId, propertyKey );
            this.id = id;
        }

        public IndexDescriptor getDescriptor()
        {
            return descriptor;
        }

        public long getId()
        {
            return id;
        }
    }

    public void removeSchemaRule( long id )
    {
        SchemaRule rule = rulesByIdMap.remove( id );
        if ( rule == null )
        {
            return;
        }

        if ( rule instanceof NodePropertyConstraintRule )
        {
            nodeConstraints.remove( ((NodePropertyConstraintRule) rule).toConstraint() );
        }
        else if ( rule instanceof RelationshipPropertyConstraintRule )
        {
            relationshipConstraints.remove( ((RelationshipPropertyConstraintRule) rule).toConstraint() );
        }
        else if ( rule instanceof IndexRule )
        {
            IndexRule indexRule = (IndexRule) rule;
            Map<Integer, CommittedIndexDescriptor> byLabel = indexDescriptors.get( indexRule.getLabel() );
            byLabel.remove( indexRule.getPropertyKey() );
            if ( byLabel.isEmpty() )
            {
                indexDescriptors.remove( indexRule.getLabel() );
            }
        }
    }

    public IndexDescriptor indexDescriptor( int labelId, int propertyKey )
    {
        Map<Integer, CommittedIndexDescriptor> byLabel = indexDescriptors.get( labelId );
        if ( byLabel != null )
        {
            CommittedIndexDescriptor committed = byLabel.get( propertyKey );
            if ( committed != null )
            {
                return committed.getDescriptor();
            }
        }
        return null;
    }
}


File: community/kernel/src/main/java/org/neo4j/kernel/impl/store/SchemaStorage.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.kernel.impl.store;

import java.util.Collection;
import java.util.Iterator;

import org.neo4j.function.Function;
import org.neo4j.function.Predicate;
import org.neo4j.function.Predicates;
import org.neo4j.helpers.ThisShouldNotHappenError;
import org.neo4j.helpers.collection.PrefetchingIterator;
import org.neo4j.kernel.api.exceptions.schema.MalformedSchemaRuleException;
import org.neo4j.kernel.api.exceptions.schema.SchemaRuleNotFoundException;
import org.neo4j.kernel.impl.store.record.DynamicRecord;
import org.neo4j.kernel.impl.store.record.IndexRule;
import org.neo4j.kernel.impl.store.record.SchemaRule;

import static org.neo4j.function.Functions.cast;
import static org.neo4j.helpers.collection.Iterables.filter;
import static org.neo4j.helpers.collection.Iterables.map;

public class SchemaStorage implements SchemaRuleAccess
{
    public static enum IndexRuleKind
    {
        INDEX
                {
                    @Override
                    public boolean isOfKind( IndexRule rule )
                    {
                        return !rule.isConstraintIndex();
                    }
                },
        CONSTRAINT
                {
                    @Override
                    public boolean isOfKind( IndexRule rule )
                    {
                        return rule.isConstraintIndex();
                    }
                },
        ALL
                {
                    @Override
                    public boolean isOfKind( IndexRule rule )
                    {
                        return true;
                    }
                };

        public abstract boolean isOfKind( IndexRule rule );
    }

    private final RecordStore<DynamicRecord> schemaStore;

    public SchemaStorage( RecordStore<DynamicRecord> schemaStore )
    {
        this.schemaStore = schemaStore;
    }

    /**
     * Find the IndexRule, of any kind, for the given label and property key.
     *
     * Otherwise throw if there are not exactly one matching candidate rule.
     */
    public IndexRule indexRule( int labelId, int propertyKeyId )
    {
        return indexRule( labelId, propertyKeyId, IndexRuleKind.ALL );
    }

    /**
     * Find and IndexRule of the given kind, for the given label and property.
     *
     * Otherwise throw if there are not exactly one matching candidate rule.
     */
    public IndexRule indexRule( final int labelId, final int propertyKeyId, IndexRuleKind kind )
    {
        Iterator<IndexRule> rules = schemaRules( cast( IndexRule.class ), IndexRule.class, new Predicate<IndexRule>()
        {
            @Override
            public boolean test( IndexRule rule )
            {
                return rule.getLabel() == labelId && rule.getPropertyKey() == propertyKeyId;
            }
        } );

        IndexRule foundRule = null;

        while ( rules.hasNext() )
        {
            IndexRule candidate = rules.next();
            if ( kind.isOfKind( candidate ) )
            {
                if ( foundRule != null )
                {
                    throw new ThisShouldNotHappenError( "Jake", String.format("Found more than one matching index rule, %s and %s", foundRule, candidate) );
                }
                foundRule = candidate;
            }
        }

        return foundRule;
    }

    public Iterator<IndexRule> allIndexRules()
    {
        return schemaRules( IndexRule.class );
    }

    public <R extends NodePropertyConstraintRule, T> Iterator<T> schemaRulesForNodes(
            Function<? super R,T> conversion, Class<R> type, final int labelId, Predicate<R> predicate )
    {
        return schemaRules( conversion, type, Predicates.all( predicate, new Predicate<R>()
        {
            @Override
            public boolean test( R rule )
            {
                return rule.getLabel() == labelId;
            }
        } ) );
    }

    public <R extends RelationshipPropertyConstraintRule, T> Iterator<T> schemaRulesForRelationships(
            Function<? super R,T> conversion, Class<R> type, final int typeId, Predicate<R> predicate )
    {
        return schemaRules( conversion, type, Predicates.all( predicate, new Predicate<R>()
        {
            @Override
            public boolean test( R rule )
            {
                return rule.getRelationshipType() == typeId;
            }
        } ) );
    }

    private <R extends SchemaRule, T> Iterator<T> schemaRules(
            Function<? super R, T> conversion, final Class<R> ruleType, final Predicate<R> predicate )
    {
        @SuppressWarnings("unchecked"/*the predicate ensures that this is safe*/)
        Function<SchemaRule, T> ruleConversion = (Function) conversion;
        return map( ruleConversion, filter( new Predicate<SchemaRule>()
        {
            @SuppressWarnings( "unchecked" )
            @Override
            public boolean test( SchemaRule rule )
            {
                return ruleType.isAssignableFrom( rule.getKind().getRuleClass() ) &&
                       predicate.test( (R) rule );
            }
        }, loadAllSchemaRules() ) );
    }

    public <R extends SchemaRule, T> Iterator<T> schemaRules(
            Function<? super R, T> conversion, final Class<R> ruleClass )
    {
        @SuppressWarnings("unchecked"/*the predicate ensures that this is safe*/)
        Function<SchemaRule, T> ruleConversion = (Function) conversion;
        return map( ruleConversion, filter( new Predicate<SchemaRule>()
        {
            @SuppressWarnings("unchecked")
            @Override
            public boolean test( SchemaRule rule )
            {
                return ruleClass.isInstance( rule );
            }
        }, loadAllSchemaRules() ) );
    }

    public <R extends SchemaRule> Iterator<R> schemaRules( final Class<R> ruleClass )
    {
        @SuppressWarnings({"UnnecessaryLocalVariable", "unchecked"/*the predicate ensures that this cast is safe*/})
        Iterator<R> result = (Iterator)filter( new Predicate<SchemaRule>()
        {
            @Override
            public boolean test( SchemaRule rule )
            {
                return ruleClass.isInstance( rule );
            }
        }, loadAllSchemaRules() );
        return result;
    }

    public Iterator<SchemaRule> loadAllSchemaRules()
    {
        return new PrefetchingIterator<SchemaRule>()
        {
            private final long highestId = schemaStore.getHighestPossibleIdInUse();
            private long currentId = 1; /*record 0 contains the block size*/
            private final byte[] scratchData = newRecordBuffer();

            @Override
            protected SchemaRule fetchNextOrNull()
            {
                while ( currentId <= highestId )
                {
                    long id = currentId++;
                    DynamicRecord record = schemaStore.forceGetRecord( id );
                    if ( record.inUse() && record.isStartRecord() )
                    {
                        try
                        {
                            return getSchemaRule( id, scratchData );
                        }
                        catch ( MalformedSchemaRuleException e )
                        {
                            // TODO remove this and throw this further up
                            throw new RuntimeException( e );
                        }
                    }
                }
                return null;
            }
        };
    }

    @Override
    public SchemaRule loadSingleSchemaRule( long ruleId ) throws MalformedSchemaRuleException
    {
        return getSchemaRule( ruleId, newRecordBuffer() );
    }

    private byte[] newRecordBuffer()
    {
        return new byte[schemaStore.getRecordSize()*4];
    }

    private SchemaRule getSchemaRule( long id, byte[] buffer ) throws MalformedSchemaRuleException
    {
        Collection<DynamicRecord> records;
        try
        {
            records = schemaStore.getRecords( id );
        }
        catch ( Exception e )
        {
            throw new MalformedSchemaRuleException( e.getMessage(), e );
        }
        return SchemaStore.readSchemaRule( id, records, buffer );
    }

    public long newRuleId()
    {
        return schemaStore.nextId();
    }

    public MandatoryNodePropertyConstraintRule mandatoryNodePropertyConstraint( int labelId, int propertyKeyId )
            throws SchemaRuleNotFoundException
    {
        return nodeConstraintRule( MandatoryNodePropertyConstraintRule.class, labelId, propertyKeyId );
    }

    public MandatoryRelationshipPropertyConstraintRule mandatoryRelationshipPropertyConstraint( int typeId,
            int propertyKeyId ) throws SchemaRuleNotFoundException
    {
        return relationshipConstraintRule( MandatoryRelationshipPropertyConstraintRule.class, typeId, propertyKeyId );
    }

    public UniquePropertyConstraintRule uniquenessConstraint( int labelId, final int propertyKeyId )
            throws SchemaRuleNotFoundException
    {
        return nodeConstraintRule( UniquePropertyConstraintRule.class, labelId, propertyKeyId );
    }

    private <Rule extends NodePropertyConstraintRule> Rule nodeConstraintRule( Class<Rule> type,
            final int labelId, final int propertyKeyId ) throws SchemaRuleNotFoundException
    {
        Iterator<Rule> rules = schemaRules( cast( type ), type, new Predicate<Rule>()
        {
            @Override
            public boolean test( Rule item )
            {
                return item.getLabel() == labelId &&
                       item.containsPropertyKeyId( propertyKeyId );
            }
        } );
        if ( !rules.hasNext() )
        {
            throw SchemaRuleNotFoundException.forNode( labelId, propertyKeyId, "not found" );
        }

        Rule rule = rules.next();

        if ( rules.hasNext() )
        {
            throw SchemaRuleNotFoundException.forNode( labelId, propertyKeyId, "found more than one matching index" );
        }
        return rule;
    }

    private <Rule extends RelationshipPropertyConstraintRule> Rule relationshipConstraintRule( Class<Rule> type,
            final int relationshipTypeId, final int propertyKeyId ) throws SchemaRuleNotFoundException
    {
        Iterator<Rule> rules = schemaRules( cast( type ), type, new Predicate<Rule>()
        {
            @Override
            public boolean test( Rule item )
            {
                return item.getRelationshipType() == relationshipTypeId &&
                       item.containsPropertyKeyId( propertyKeyId );
            }
        } );
        if ( !rules.hasNext() )
        {
            throw SchemaRuleNotFoundException.forRelationship( relationshipTypeId, propertyKeyId, "not found" );
        }

        Rule rule = rules.next();

        if ( rules.hasNext() )
        {
            throw SchemaRuleNotFoundException.forRelationship( relationshipTypeId, propertyKeyId,
                    "found more than one matching index" );
        }
        return rule;
    }
}


File: community/kernel/src/main/java/org/neo4j/kernel/impl/store/record/SchemaRule.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.kernel.impl.store.record;

import java.nio.ByteBuffer;

import org.neo4j.kernel.api.exceptions.schema.MalformedSchemaRuleException;
import org.neo4j.kernel.impl.store.MandatoryNodePropertyConstraintRule;
import org.neo4j.kernel.impl.store.MandatoryRelationshipPropertyConstraintRule;
import org.neo4j.kernel.impl.store.UniquePropertyConstraintRule;

public interface SchemaRule extends RecordSerializable
{
    /**
     * The persistence id for this rule.
     */
    long getId();

    /**
     * @return id of label to which this schema rule has been attached
     * @throws IllegalStateException when this rule has kind {@link Kind#MANDATORY_RELATIONSHIP_PROPERTY_CONSTRAINT}
     */
    int getLabel();

    /**
     * @return id of relationship type to which this schema rule has been attached
     * @throws IllegalStateException when this rule has kind different from
     * {@link Kind#MANDATORY_RELATIONSHIP_PROPERTY_CONSTRAINT}
     */
    int getRelationshipType();

    /**
     * @return the kind of this schema rule
     */
    Kind getKind();

    enum Kind
    {
        INDEX_RULE( 1, IndexRule.class )
        {
            @Override
            protected SchemaRule newRule( long id, int labelId, ByteBuffer buffer )
            {
                return IndexRule.readIndexRule( id, false, labelId, buffer );
            }
        },
        CONSTRAINT_INDEX_RULE( 2, IndexRule.class )
        {
            @Override
            protected SchemaRule newRule( long id, int labelId, ByteBuffer buffer )
            {
                return IndexRule.readIndexRule( id, true, labelId, buffer );
            }
        },
        UNIQUENESS_CONSTRAINT( 3, UniquePropertyConstraintRule.class )
        {
            @Override
            protected SchemaRule newRule( long id, int labelId, ByteBuffer buffer )
            {
                return UniquePropertyConstraintRule.readUniquenessConstraintRule( id, labelId, buffer );
            }
        },
        MANDATORY_NODE_PROPERTY_CONSTRAINT( 4, MandatoryNodePropertyConstraintRule.class )
        {
            @Override
            protected SchemaRule newRule( long id, int labelId, ByteBuffer buffer )
            {
                return MandatoryNodePropertyConstraintRule.readMandatoryNodePropertyConstraintRule( id, labelId, buffer );
            }
        },
        MANDATORY_RELATIONSHIP_PROPERTY_CONSTRAINT( 5, MandatoryRelationshipPropertyConstraintRule.class )
        {
            @Override
            protected SchemaRule newRule( long id, int labelId, ByteBuffer buffer )
            {
                return MandatoryRelationshipPropertyConstraintRule.readMandatoryRelPropertyConstraintRule( id, labelId, buffer );
            }
        };

        private final byte id;
        private final Class<? extends SchemaRule> ruleClass;

        private Kind( int id, Class<? extends SchemaRule> ruleClass )
        {
            assert id > 0 : "Kind id 0 is reserved";
            this.id = (byte) id;
            this.ruleClass = ruleClass;
        }

        public Class<? extends SchemaRule> getRuleClass()
        {
            return this.ruleClass;
        }

        public byte id()
        {
            return this.id;
        }

        protected abstract SchemaRule newRule( long id, int labelId, ByteBuffer buffer );

        public static SchemaRule deserialize( long id, ByteBuffer buffer ) throws MalformedSchemaRuleException
        {
            int labelId = buffer.getInt();
            Kind kind = kindForId( buffer.get() );
            try
            {
                SchemaRule rule = kind.newRule( id, labelId, buffer );
                if ( null == rule )
                {
                    throw new MalformedSchemaRuleException( null,
                            "Deserialized null schema rule for id %d with kind %s", id, kind.name() );
                }
                return rule;
            }
            catch ( Exception e )
            {
                throw new MalformedSchemaRuleException( e,
                        "Could not deserialize schema rule for id %d with kind %s", id, kind.name() );
            }
        }

        public static Kind kindForId( byte id ) throws MalformedSchemaRuleException
        {
            switch ( id )
            {
            case 1: return INDEX_RULE;
            case 2: return CONSTRAINT_INDEX_RULE;
            case 3: return UNIQUENESS_CONSTRAINT;
            case 4: return MANDATORY_NODE_PROPERTY_CONSTRAINT;
            case 5: return MANDATORY_RELATIONSHIP_PROPERTY_CONSTRAINT;
            default:
                throw new MalformedSchemaRuleException( null, "Unknown kind id %d", id );
            }
        }

        public boolean isIndex()
        {
            return ruleClass == IndexRule.class;
        }
    }
}


File: community/kernel/src/main/java/org/neo4j/kernel/impl/transaction/command/NeoStoreTransactionApplier.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.kernel.impl.transaction.command;

import java.io.IOException;

import org.neo4j.kernel.impl.core.CacheAccessBackDoor;
import org.neo4j.kernel.impl.locking.LockGroup;
import org.neo4j.kernel.impl.locking.LockService;
import org.neo4j.kernel.impl.store.NeoStore;
import org.neo4j.kernel.impl.store.NodeStore;
import org.neo4j.kernel.impl.store.PropertyConstraintRule;
import org.neo4j.kernel.impl.store.SchemaStore;
import org.neo4j.kernel.impl.store.record.DynamicRecord;
import org.neo4j.kernel.impl.store.record.RelationshipRecord;

/**
 * Visits commands targeted towards the {@link NeoStore} and update corresponding stores.
 * What happens in here is what will happen in a "internal" transaction, i.e. a transaction that has been
 * forged in this database, with transaction state, a KernelTransaction and all that and is now committing.
 * <p>
 * For other modes of application, like recovery or external there are other, added functionality, decorated
 * outside this applier.
 */
public class NeoStoreTransactionApplier extends NeoCommandHandler.Adapter
{
    private final NeoStore neoStore;
    // Ideally we don't want any cache access in here, but it is how it is. At least we try to minimize use of it
    private final CacheAccessBackDoor cacheAccess;
    private final LockService lockService;
    private final LockGroup lockGroup;
    private final long transactionId;

    public NeoStoreTransactionApplier( NeoStore store, CacheAccessBackDoor cacheAccess,
                                       LockService lockService, LockGroup lockGroup, long transactionId )
    {
        this.neoStore = store;
        this.cacheAccess = cacheAccess;
        this.lockService = lockService;
        this.transactionId = transactionId;
        this.lockGroup = lockGroup;
    }

    @Override
    public boolean visitNodeCommand( Command.NodeCommand command ) throws IOException
    {
        // acquire lock
        lockGroup.add( lockService.acquireNodeLock( command.getKey(), LockService.LockType.WRITE_LOCK ) );

        // update store
        NodeStore nodeStore = neoStore.getNodeStore();
        nodeStore.updateRecord( command.getAfter() );
        // getDynamicLabelRecords will contain even deleted records
        nodeStore.updateDynamicLabelRecords( command.getAfter().getDynamicLabelRecords() );

        return false;
    }

    @Override
    public boolean visitRelationshipCommand( Command.RelationshipCommand command ) throws IOException
    {
        RelationshipRecord record = command.getRecord();
        neoStore.getRelationshipStore().updateRecord( record );
        return false;
    }

    @Override
    public boolean visitPropertyCommand( Command.PropertyCommand command ) throws IOException
    {
        // acquire lock
        long nodeId = command.getNodeId();
        if ( nodeId != -1 )
        {
            lockGroup.add( lockService.acquireNodeLock( nodeId, LockService.LockType.WRITE_LOCK ) );
        }

        // track the dynamic value record high ids
        // update store
        neoStore.getPropertyStore().updateRecord( command.getAfter() );
        return false;
    }

    @Override
    public boolean visitRelationshipGroupCommand( Command.RelationshipGroupCommand command ) throws IOException
    {
        neoStore.getRelationshipGroupStore().updateRecord( command.getRecord() );
        return false;
    }

    @Override
    public boolean visitRelationshipTypeTokenCommand( Command.RelationshipTypeTokenCommand command ) throws IOException
    {
        neoStore.getRelationshipTypeTokenStore().updateRecord( command.getRecord() );
        return false;
    }

    @Override
    public boolean visitLabelTokenCommand( Command.LabelTokenCommand command ) throws IOException
    {
        neoStore.getLabelTokenStore().updateRecord( command.getRecord() );
        return false;
    }

    @Override
    public boolean visitPropertyKeyTokenCommand( Command.PropertyKeyTokenCommand command ) throws IOException
    {
        neoStore.getPropertyKeyTokenStore().updateRecord( command.getRecord() );
        return false;
    }

    @Override
    public boolean visitSchemaRuleCommand( Command.SchemaRuleCommand command ) throws IOException
    {
        // schema rules. Execute these after generating the property updates so. If executed
        // before and we've got a transaction that sets properties/labels as well as creating an index
        // we might end up with this corner-case:
        // 1) index rule created and index population job started
        // 2) index population job processes some nodes, but doesn't complete
        // 3) we gather up property updates and send those to the indexes. The newly created population
        //    job might get those as updates
        // 4) the population job will apply those updates as added properties, and might end up with duplicate
        //    entries for the same property

        SchemaStore schemaStore = neoStore.getSchemaStore();
        for ( DynamicRecord record : command.getRecordsAfter() )
        {
            schemaStore.updateRecord( record );
        }

        if ( command.getSchemaRule() instanceof PropertyConstraintRule )
        {
            switch ( command.getMode() )
            {
            case UPDATE:
            case CREATE:
                neoStore.setLatestConstraintIntroducingTx( transactionId );
                break;
            case DELETE:
                break;
            default:
                throw new IllegalStateException( command.getMode().name() );
            }
        }

        switch ( command.getMode() )
        {
        case DELETE:
            cacheAccess.removeSchemaRuleFromCache( command.getKey() );
            break;
        default:
            cacheAccess.addSchemaRule( command.getSchemaRule() );
        }
        return false;
    }

    @Override
    public boolean visitNeoStoreCommand( Command.NeoStoreCommand command ) throws IOException
    {
        neoStore.setGraphNextProp( command.getRecord().getNextProp() );
        return false;
    }
}


File: community/kernel/src/main/java/org/neo4j/kernel/impl/transaction/state/IntegrityValidator.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.kernel.impl.transaction.state;

import org.neo4j.kernel.api.exceptions.Status;
import org.neo4j.kernel.api.exceptions.TransactionFailureException;
import org.neo4j.kernel.api.exceptions.index.IndexNotFoundKernelException;
import org.neo4j.kernel.api.exceptions.index.IndexPopulationFailedKernelException;
import org.neo4j.kernel.api.exceptions.schema.ConstraintVerificationFailedKernelException;
import org.neo4j.kernel.impl.api.index.IndexingService;
import org.neo4j.kernel.impl.store.NeoStore;
import org.neo4j.kernel.impl.store.UniquePropertyConstraintRule;
import org.neo4j.kernel.impl.store.record.NodeRecord;
import org.neo4j.kernel.impl.store.record.Record;
import org.neo4j.kernel.impl.store.record.SchemaRule;

/**
 * Validates data integrity during the prepare phase of {@link TransactionRecordState}.
 */
public class IntegrityValidator
{
    private final NeoStore neoStore;
    private final IndexingService indexes;

    public IntegrityValidator( NeoStore neoStore, IndexingService indexes )
    {
        this.neoStore = neoStore;
        this.indexes = indexes;
    }

    public void validateNodeRecord( NodeRecord record ) throws TransactionFailureException
    {
        if ( !record.inUse() && record.getNextRel() != Record.NO_NEXT_RELATIONSHIP.intValue() )
        {
            throw new TransactionFailureException( Status.Transaction.ValidationFailed,
                    "Node record " + record + " still has relationships" );
        }
    }

    public void validateTransactionStartKnowledge( long lastCommittedTxWhenTransactionStarted )
            throws TransactionFailureException
    {
        long latestConstraintIntroducingTx = neoStore.getLatestConstraintIntroducingTx();
        if ( lastCommittedTxWhenTransactionStarted < latestConstraintIntroducingTx )
        {
            // Constraints have changed since the transaction begun

            // This should be a relatively uncommon case, window for this happening is a few milliseconds when an admin
            // explicitly creates a constraint, after the index has been populated. We can improve this later on by
            // replicating the constraint validation logic down here, or rethinking where we validate constraints.
            // For now, we just kill these transactions.
            throw new TransactionFailureException( Status.Transaction.ConstraintsChanged,
                            "Database constraints have changed (txId=%d) after this transaction (txId=%d) started, " +
                            "which is not yet supported. Please retry your transaction to ensure all " +
                            "constraints are executed.", latestConstraintIntroducingTx,
                            lastCommittedTxWhenTransactionStarted );
        }
    }

    public void validateSchemaRule( SchemaRule schemaRule ) throws TransactionFailureException
    {
        if ( schemaRule instanceof UniquePropertyConstraintRule )
        {
            try
            {
                indexes.validateIndex( ((UniquePropertyConstraintRule)schemaRule).getOwnedIndex() );
            }
            catch ( ConstraintVerificationFailedKernelException e )
            {
                throw new TransactionFailureException( Status.Transaction.ValidationFailed, e, "Index validation failed" );
            }
            catch ( IndexNotFoundKernelException | IndexPopulationFailedKernelException e )
            {
                // We don't expect this to occur, and if they do, it is because we are in a very bad state - out of
                // disk or index corruption, or similar. This will kill the database such that it can be shut down
                // and have recovery performed. It's the safest bet to avoid loosing data.
                throw new TransactionFailureException( Status.Transaction.ValidationFailed, e, "Index population failure" );
            }
        }
    }
}


File: community/kernel/src/main/java/org/neo4j/unsafe/batchinsert/BatchInserterImpl.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.unsafe.batchinsert;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;

import org.neo4j.collection.primitive.PrimitiveLongCollections;
import org.neo4j.function.LongFunction;
import org.neo4j.graphdb.ConstraintViolationException;
import org.neo4j.graphdb.Label;
import org.neo4j.graphdb.NotFoundException;
import org.neo4j.graphdb.RelationshipType;
import org.neo4j.graphdb.factory.GraphDatabaseSettings;
import org.neo4j.graphdb.schema.ConstraintCreator;
import org.neo4j.graphdb.schema.ConstraintDefinition;
import org.neo4j.graphdb.schema.IndexCreator;
import org.neo4j.graphdb.schema.IndexDefinition;
import org.neo4j.graphdb.schema.RelationshipConstraintCreator;
import org.neo4j.helpers.collection.IteratorUtil;
import org.neo4j.helpers.collection.IteratorWrapper;
import org.neo4j.helpers.collection.Visitor;
import org.neo4j.io.fs.FileSystemAbstraction;
import org.neo4j.io.fs.FileUtils;
import org.neo4j.io.pagecache.PageCache;
import org.neo4j.io.pagecache.tracing.PageCacheTracer;
import org.neo4j.kernel.DefaultFileSystemAbstraction;
import org.neo4j.kernel.DefaultIdGeneratorFactory;
import org.neo4j.kernel.EmbeddedGraphDatabase;
import org.neo4j.kernel.IdGeneratorFactory;
import org.neo4j.kernel.IdType;
import org.neo4j.kernel.StoreLocker;
import org.neo4j.kernel.api.constraints.MandatoryNodePropertyConstraint;
import org.neo4j.kernel.api.constraints.MandatoryRelationshipPropertyConstraint;
import org.neo4j.kernel.api.constraints.UniquenessConstraint;
import org.neo4j.kernel.api.exceptions.KernelException;
import org.neo4j.kernel.api.exceptions.index.IndexCapacityExceededException;
import org.neo4j.kernel.api.exceptions.schema.AlreadyConstrainedException;
import org.neo4j.kernel.api.exceptions.schema.CreateConstraintFailureException;
import org.neo4j.kernel.api.index.IndexConfiguration;
import org.neo4j.kernel.api.index.IndexDescriptor;
import org.neo4j.kernel.api.index.IndexEntryConflictException;
import org.neo4j.kernel.api.index.IndexPopulator;
import org.neo4j.kernel.api.index.InternalIndexState;
import org.neo4j.kernel.api.index.NodePropertyUpdate;
import org.neo4j.kernel.api.index.SchemaIndexProvider;
import org.neo4j.kernel.api.labelscan.LabelScanStore;
import org.neo4j.kernel.api.labelscan.NodeLabelUpdate;
import org.neo4j.kernel.api.properties.DefinedProperty;
import org.neo4j.kernel.configuration.Config;
import org.neo4j.kernel.extension.KernelExtensionFactory;
import org.neo4j.kernel.extension.KernelExtensions;
import org.neo4j.kernel.extension.UnsatisfiedDependencyStrategies;
import org.neo4j.kernel.impl.api.index.IndexStoreView;
import org.neo4j.kernel.impl.api.index.SchemaIndexProviderMap;
import org.neo4j.kernel.impl.api.index.StoreScan;
import org.neo4j.kernel.impl.api.index.sampling.IndexSamplingConfig;
import org.neo4j.kernel.impl.api.scan.LabelScanStoreProvider;
import org.neo4j.kernel.impl.api.store.SchemaCache;
import org.neo4j.kernel.impl.core.RelationshipTypeToken;
import org.neo4j.kernel.impl.core.Token;
import org.neo4j.kernel.impl.coreapi.schema.BaseNodeConstraintCreator;
import org.neo4j.kernel.impl.coreapi.schema.BaseRelationshipConstraintCreator;
import org.neo4j.kernel.impl.coreapi.schema.IndexCreatorImpl;
import org.neo4j.kernel.impl.coreapi.schema.IndexDefinitionImpl;
import org.neo4j.kernel.impl.coreapi.schema.InternalSchemaActions;
import org.neo4j.kernel.impl.coreapi.schema.MandatoryNodePropertyConstraintDefinition;
import org.neo4j.kernel.impl.coreapi.schema.MandatoryRelationshipPropertyConstraintDefinition;
import org.neo4j.kernel.impl.coreapi.schema.UniquenessConstraintDefinition;
import org.neo4j.kernel.impl.index.IndexConfigStore;
import org.neo4j.kernel.impl.locking.LockService;
import org.neo4j.kernel.impl.locking.ReentrantLockService;
import org.neo4j.kernel.impl.logging.StoreLogService;
import org.neo4j.kernel.impl.pagecache.ConfiguringPageCacheFactory;
import org.neo4j.kernel.impl.spi.KernelContext;
import org.neo4j.kernel.impl.store.CountsComputer;
import org.neo4j.kernel.impl.store.LabelTokenStore;
import org.neo4j.kernel.impl.store.MandatoryNodePropertyConstraintRule;
import org.neo4j.kernel.impl.store.MandatoryRelationshipPropertyConstraintRule;
import org.neo4j.kernel.impl.store.NeoStore;
import org.neo4j.kernel.impl.store.NodeLabels;
import org.neo4j.kernel.impl.store.NodeStore;
import org.neo4j.kernel.impl.store.PropertyKeyTokenStore;
import org.neo4j.kernel.impl.store.PropertyStore;
import org.neo4j.kernel.impl.store.RelationshipStore;
import org.neo4j.kernel.impl.store.RelationshipTypeTokenStore;
import org.neo4j.kernel.impl.store.SchemaStore;
import org.neo4j.kernel.impl.store.StoreFactory;
import org.neo4j.kernel.impl.store.UnderlyingStorageException;
import org.neo4j.kernel.impl.store.UniquePropertyConstraintRule;
import org.neo4j.kernel.impl.store.counts.CountsTracker;
import org.neo4j.kernel.impl.store.id.IdGeneratorImpl;
import org.neo4j.kernel.impl.store.record.DynamicRecord;
import org.neo4j.kernel.impl.store.record.IndexRule;
import org.neo4j.kernel.impl.store.record.LabelTokenRecord;
import org.neo4j.kernel.impl.store.record.NodeRecord;
import org.neo4j.kernel.impl.store.record.PrimitiveRecord;
import org.neo4j.kernel.impl.store.record.PropertyBlock;
import org.neo4j.kernel.impl.store.record.PropertyKeyTokenRecord;
import org.neo4j.kernel.impl.store.record.PropertyRecord;
import org.neo4j.kernel.impl.store.record.Record;
import org.neo4j.kernel.impl.store.record.RelationshipRecord;
import org.neo4j.kernel.impl.store.record.RelationshipTypeTokenRecord;
import org.neo4j.kernel.impl.store.record.SchemaRule;
import org.neo4j.kernel.impl.transaction.state.DefaultSchemaIndexProviderMap;
import org.neo4j.kernel.impl.transaction.state.NeoStoreIndexStoreView;
import org.neo4j.kernel.impl.transaction.state.NeoStoreSupplier;
import org.neo4j.kernel.impl.transaction.state.PropertyCreator;
import org.neo4j.kernel.impl.transaction.state.PropertyDeleter;
import org.neo4j.kernel.impl.transaction.state.PropertyTraverser;
import org.neo4j.kernel.impl.transaction.state.RecordAccess;
import org.neo4j.kernel.impl.transaction.state.RecordAccess.RecordProxy;
import org.neo4j.kernel.impl.transaction.state.RelationshipCreator;
import org.neo4j.kernel.impl.transaction.state.RelationshipGroupGetter;
import org.neo4j.kernel.impl.transaction.state.RelationshipLocker;
import org.neo4j.kernel.impl.util.Dependencies;
import org.neo4j.kernel.impl.util.Listener;
import org.neo4j.kernel.lifecycle.LifeSupport;
import org.neo4j.kernel.monitoring.Monitors;
import org.neo4j.logging.Log;
import org.neo4j.logging.NullLog;

import static java.lang.Boolean.parseBoolean;
import static org.neo4j.collection.primitive.PrimitiveLongCollections.map;
import static org.neo4j.graphdb.DynamicLabel.label;
import static org.neo4j.helpers.collection.IteratorUtil.first;
import static org.neo4j.kernel.impl.store.NodeLabelsField.parseLabelsField;
import static org.neo4j.kernel.impl.store.PropertyStore.encodeString;
import static org.neo4j.kernel.impl.util.IoPrimitiveUtils.safeCastLongToInt;

/**
 * @deprecated will be moved to an internal package in a future release
 */
@Deprecated
public class BatchInserterImpl implements BatchInserter
{
    private static final long MAX_NODE_ID = IdType.NODE.getMaxValue();

    private final LifeSupport life;
    private final NeoStore neoStore;
    private final IndexConfigStore indexStore;
    private final File storeDir;
    private final BatchTokenHolder propertyKeyTokens;
    private final BatchTokenHolder relationshipTypeTokens;
    private final BatchTokenHolder labelTokens;
    private final IdGeneratorFactory idGeneratorFactory;
    private final SchemaIndexProviderMap schemaIndexProviders;
    private final LabelScanStore labelScanStore;
    private final StoreLogService logService;
    private final Log msgLog;
    private final FileSystemAbstraction fileSystem;
    private final SchemaCache schemaCache;
    private final Config config;
    private final BatchInserterImpl.BatchSchemaActions actions;
    private final StoreLocker storeLocker;
    private boolean labelsTouched;

    private final LongFunction<Label> labelIdToLabelFunction = new LongFunction<Label>()
    {
        @Override
        public Label apply( long from )
        {
            return label( labelTokens.byId( safeCastLongToInt( from ) ).name() );
        }
    };

    private boolean isShutdown = false;

    private FlushStrategy flushStrategy;
    // Helper structure for setNodeProperty
    private final RelationshipCreator relationshipCreator;
    private final DirectRecordAccessSet recordAccess;
    private final PropertyTraverser propertyTraverser;
    private final PropertyCreator propertyCreator;
    private final PropertyDeleter propertyDeletor;

    /**
     * @deprecated use {@link #BatchInserterImpl(File, Map)} instead
     */
    @Deprecated
    BatchInserterImpl( String storeDir,
                       Map<String, String> stringParams ) throws IOException
    {
        this( new File( FileUtils.fixSeparatorsInPath( storeDir ) ), stringParams );
    }

    /**
     * @deprecated use {@link #BatchInserterImpl(File, FileSystemAbstraction, Map, Iterable)} instead
     */
    @Deprecated
    BatchInserterImpl( String storeDir, final FileSystemAbstraction fileSystem,
                       Map<String, String> stringParams, Iterable<KernelExtensionFactory<?>> kernelExtensions ) throws IOException
    {
        this( new File( FileUtils.fixSeparatorsInPath( storeDir ) ),
                fileSystem,
                stringParams,
                kernelExtensions
        );
    }

    BatchInserterImpl( File storeDir,
                       Map<String, String> stringParams ) throws IOException
    {
        this( storeDir,
              new DefaultFileSystemAbstraction(),
              stringParams,
              Collections.<KernelExtensionFactory<?>>emptyList()
        );
    }

    BatchInserterImpl( final File storeDir, final FileSystemAbstraction fileSystem,
                       Map<String, String> stringParams, Iterable<KernelExtensionFactory<?>> kernelExtensions ) throws IOException
    {
        rejectAutoUpgrade( stringParams );
        Map<String, String> params = getDefaultParams();
        params.putAll( stringParams );
        this.config = new Config( params, GraphDatabaseSettings.class );
        Monitors monitors = new Monitors();

        life = new LifeSupport();
        this.fileSystem = fileSystem;
        this.storeDir = storeDir;
        ConfiguringPageCacheFactory pageCacheFactory = new ConfiguringPageCacheFactory(
                fileSystem, config, PageCacheTracer.NULL, NullLog.getInstance() );
        PageCache pageCache = pageCacheFactory.getOrCreatePageCache();

        logService = life.add( StoreLogService.inStoreDirectory( fileSystem, this.storeDir ) );
        msgLog = logService.getInternalLog( getClass() );
        storeLocker = new StoreLocker( fileSystem );
        storeLocker.checkLock( this.storeDir );

        boolean dump = config.get( GraphDatabaseSettings.dump_configuration );
        this.idGeneratorFactory = new DefaultIdGeneratorFactory();

        StoreFactory sf = new StoreFactory(
                this.storeDir,
                config,
                idGeneratorFactory,
                pageCache,
                fileSystem,
                logService.getInternalLogProvider(),
                monitors );

        if ( dump )
        {
            dumpConfiguration( params );
        }
        msgLog.info( Thread.currentThread() + " Starting BatchInserter(" + this + ")" );
        life.start();
        neoStore = sf.newNeoStore( true );
        neoStore.verifyStoreOk();
        neoStore.makeStoreOk();
        Token[] indexes = getPropertyKeyTokenStore().getTokens( 10000 );
        propertyKeyTokens = new BatchTokenHolder( indexes );
        labelTokens = new BatchTokenHolder( neoStore.getLabelTokenStore().getTokens( Integer.MAX_VALUE ) );
        Token[] types = getRelationshipTypeStore().getTokens( Integer.MAX_VALUE );
        relationshipTypeTokens = new BatchTokenHolder( types );
        indexStore = life.add( new IndexConfigStore( this.storeDir, fileSystem ) );
        schemaCache = new SchemaCache( neoStore.getSchemaStore() );

        Dependencies deps = new Dependencies();
        deps.satisfyDependencies( fileSystem, config, logService, new NeoStoreSupplier()
                        {
                            @Override
                            public NeoStore get()
                            {
                                return neoStore;
                            }
                        } );

        KernelContext kernelContext = new KernelContext()
        {
            @Override
            public FileSystemAbstraction fileSystem()
            {
                return fileSystem;
            }

            @Override
            public File storeDir()
            {
                return storeDir;
            }
        };
        KernelExtensions extensions = life
                .add( new KernelExtensions( kernelContext, kernelExtensions, deps,
                                            UnsatisfiedDependencyStrategies.ignore() ) );

        SchemaIndexProvider provider = extensions.resolveDependency( SchemaIndexProvider.class,
                SchemaIndexProvider.HIGHEST_PRIORITIZED_OR_NONE );
        schemaIndexProviders = new DefaultSchemaIndexProviderMap( provider );
        labelScanStore = life.add( extensions.resolveDependency( LabelScanStoreProvider.class,
                LabelScanStoreProvider.HIGHEST_PRIORITIZED ).getLabelScanStore() );
        actions = new BatchSchemaActions();

        // Record access
        recordAccess = new DirectRecordAccessSet( neoStore );
        relationshipCreator = new RelationshipCreator( RelationshipLocker.NO_LOCKING,
                new RelationshipGroupGetter( neoStore.getRelationshipGroupStore() ), neoStore.getDenseNodeThreshold() );
        propertyTraverser = new PropertyTraverser();
        propertyCreator = new PropertyCreator( getPropertyStore(), propertyTraverser );
        propertyDeletor = new PropertyDeleter( getPropertyStore(), propertyTraverser );

        flushStrategy = new BatchedFlushStrategy( recordAccess, config.get( GraphDatabaseSettings
                .batch_inserter_batch_size ) );
    }

    private Map<String, String> getDefaultParams()
    {
        Map<String, String> params = new HashMap<>();
        params.put( GraphDatabaseSettings.pagecache_memory.name(), "32m" );
        return params;
    }

    @Override
    public boolean nodeHasProperty( long node, String propertyName )
    {
        return primitiveHasProperty( getNodeRecord( node ).forChangingData(), propertyName );
    }

    @Override
    public boolean relationshipHasProperty( long relationship, String propertyName )
    {
        return primitiveHasProperty(
                recordAccess.getRelRecords().getOrLoad( relationship, null ).forReadingData(), propertyName );
    }

    @Override
    public void setNodeProperty( long node, String propertyName, Object propertyValue )
    {
        RecordProxy<Long,NodeRecord,Void> nodeRecord = getNodeRecord( node );
        setPrimitiveProperty( nodeRecord, propertyName, propertyValue );

        flushStrategy.flush();
    }

    @Override
    public void setRelationshipProperty( long relationship, String propertyName, Object propertyValue )
    {
        RecordProxy<Long,RelationshipRecord,Void> relationshipRecord = getRelationshipRecord( relationship );
        setPrimitiveProperty( relationshipRecord, propertyName, propertyValue );

        flushStrategy.flush();
    }

    @Override
    public void removeNodeProperty( long node, String propertyName )
    {
        int propertyKey = getOrCreatePropertyKeyId( propertyName );
        propertyDeletor.removeProperty( getNodeRecord( node ), propertyKey, recordAccess.getPropertyRecords() );
        flushStrategy.flush();
    }

    @Override
    public void removeRelationshipProperty( long relationship,
                                            String propertyName )
    {
        int propertyKey = getOrCreatePropertyKeyId( propertyName );
        propertyDeletor.removeProperty( getRelationshipRecord( relationship ), propertyKey,
                recordAccess.getPropertyRecords() );
        flushStrategy.flush();
    }

    @Override
    public IndexCreator createDeferredSchemaIndex( Label label )
    {
        return new IndexCreatorImpl( actions, label );
    }

    private void removePropertyIfExist( RecordProxy<Long, ? extends PrimitiveRecord,Void> recordProxy,
            int propertyKey, RecordAccess<Long,PropertyRecord,PrimitiveRecord> propertyRecords )
    {
        if ( propertyTraverser.findPropertyRecordContaining( recordProxy.forReadingData(),
                propertyKey, propertyRecords, false ) != Record.NO_NEXT_PROPERTY.intValue() )
        {
            propertyDeletor.removeProperty( recordProxy, propertyKey, propertyRecords );
        }
    }

    private void setPrimitiveProperty( RecordProxy<Long,? extends PrimitiveRecord,Void> primitiveRecord,
            String propertyName, Object propertyValue )
    {
        int propertyKey = getOrCreatePropertyKeyId( propertyName );
        RecordAccess<Long,PropertyRecord,PrimitiveRecord> propertyRecords = recordAccess.getPropertyRecords();

        removePropertyIfExist( primitiveRecord, propertyKey, propertyRecords );
        propertyCreator.primitiveAddProperty( primitiveRecord, propertyKey, propertyValue, propertyRecords );
    }

    private void validateNodeConstraintCanBeCreated( int labelId, int propertyKeyId )
    {
        for ( SchemaRule rule : schemaCache.schemaRulesForLabel( labelId ) )
        {
            int otherPropertyKeyId;

            switch ( rule.getKind() )
            {
                case INDEX_RULE:
                case CONSTRAINT_INDEX_RULE:
                    otherPropertyKeyId = ((IndexRule) rule).getPropertyKey();
                    break;
                case UNIQUENESS_CONSTRAINT:
                    otherPropertyKeyId = ((UniquePropertyConstraintRule) rule).getPropertyKey();
                    break;
                case MANDATORY_NODE_PROPERTY_CONSTRAINT:
                    otherPropertyKeyId = ((MandatoryNodePropertyConstraintRule) rule).getPropertyKey();
                    break;
                default:
                    throw new IllegalStateException( "Case not handled for " + rule.getKind());
            }

            if ( otherPropertyKeyId == propertyKeyId )
            {
                throw new ConstraintViolationException(
                        "It is not allowed to create schema constraints and indexes on the same {label;property}." );
            }
        }
    }

    private void validateRelationshipConstraintCanBeCreated( int typeId, int propertyKeyId )
    {
        for ( SchemaRule rule : schemaCache.schemaRulesForRelationshipType( typeId ) )
        {
            int otherPropertyKeyId;

            switch ( rule.getKind() )
            {
                case MANDATORY_RELATIONSHIP_PROPERTY_CONSTRAINT:
                    otherPropertyKeyId = ((MandatoryRelationshipPropertyConstraintRule) rule).getPropertyKey();
                    break;
                default:
                    throw new IllegalStateException( "Case not handled for " + rule.getKind() );
            }

            if ( otherPropertyKeyId == propertyKeyId )
            {
                throw new ConstraintViolationException( "It is not allowed to create schema constraints and " +
                                                        "indexes on the same {relationshipType;property}." );
            }
        }
    }

    private void createIndexRule( int labelId, int propertyKeyId )
    {
        SchemaStore schemaStore = getSchemaStore();
        IndexRule schemaRule = IndexRule.indexRule( schemaStore.nextId(), labelId, propertyKeyId,
                                                    this.schemaIndexProviders.getDefaultProvider()
                                                                             .getProviderDescriptor() );
        for ( DynamicRecord record : schemaStore.allocateFrom( schemaRule ) )
        {
            schemaStore.updateRecord( record );
        }
        schemaCache.addSchemaRule( schemaRule );
        labelsTouched = true;
        flushStrategy.forceFlush();
    }

    private void repopulateAllIndexes() throws IOException, IndexCapacityExceededException
    {
        if ( !labelsTouched )
        {
            return;
        }

        final IndexRule[] rules = getIndexesNeedingPopulation();
        final IndexPopulator[] populators = new IndexPopulator[rules.length];
        // the store is uncontended at this point, so creating a local LockService is safe.
        LockService locks = new ReentrantLockService();
        IndexStoreView storeView = new NeoStoreIndexStoreView( locks, neoStore );

        final int[] labelIds = new int[rules.length];
        final int[] propertyKeyIds = new int[rules.length];

        for ( int i = 0; i < labelIds.length; i++ )
        {
            IndexRule rule = rules[i];
            int labelId = rule.getLabel();
            int propertyKeyId = rule.getPropertyKey();
            labelIds[i] = labelId;
            propertyKeyIds[i] = propertyKeyId;

            IndexDescriptor descriptor = new IndexDescriptor( labelId, propertyKeyId );
            boolean isConstraint = rule.isConstraintIndex();
            populators[i] = schemaIndexProviders.apply( rule.getProviderDescriptor() )
                                                .getPopulator( rule.getId(),
                                                        descriptor,
                                                        new IndexConfiguration( isConstraint ),
                                                        new IndexSamplingConfig( config ) );
            populators[i].create();
        }

        Visitor<NodePropertyUpdate, IOException> propertyUpdateVisitor = new Visitor<NodePropertyUpdate, IOException>()
        {
            @Override
            public boolean visit( NodePropertyUpdate update ) throws IOException
            {
                // Do a lookup from which property has changed to a list of indexes worried about that property.
                int propertyKeyInQuestion = update.getPropertyKeyId();
                for ( int i = 0; i < propertyKeyIds.length; i++ )
                {
                    if ( propertyKeyIds[i] == propertyKeyInQuestion )
                    {
                        if ( update.forLabel( labelIds[i] ) )
                        {
                            try
                            {
                                populators[i].add( update.getNodeId(), update.getValueAfter() );
                            }
                            catch ( IndexEntryConflictException conflict )
                            {
                                throw conflict.notAllowed( rules[i].getLabel(), rules[i].getPropertyKey() );
                            }
                            catch ( IndexCapacityExceededException e )
                            {
                                throw new UnderlyingStorageException( e );
                            }
                        }
                    }
                }
                return true;
            }
        };

        InitialNodeLabelCreationVisitor labelUpdateVisitor = new InitialNodeLabelCreationVisitor();
        StoreScan<IOException> storeScan = storeView.visitNodes( labelIds, propertyKeyIds,
                propertyUpdateVisitor, labelUpdateVisitor );
        storeScan.run();

        for ( IndexPopulator populator : populators )
        {
            populator.close( true );
        }
        labelUpdateVisitor.close();
    }

    private void rebuildCounts()
    {
        CountsTracker counts = neoStore.getCounts();
        try
        {
            counts.start();
        }
        catch ( IOException e )
        {
            throw new UnderlyingStorageException( e );
        }

        CountsComputer.recomputeCounts( neoStore );
    }

    private class InitialNodeLabelCreationVisitor implements Visitor<NodeLabelUpdate, IOException>
    {
        LabelScanWriter writer = labelScanStore.newWriter();

        @Override
        public boolean visit( NodeLabelUpdate update ) throws IOException
        {
            try
            {
                writer.write( update );
            }
            catch ( IndexCapacityExceededException e )
            {
                throw new UnderlyingStorageException( e );
            }
            return true;
        }

        public void close() throws IOException
        {
            writer.close();
        }
    }

    private IndexRule[] getIndexesNeedingPopulation()
    {
        List<IndexRule> indexesNeedingPopulation = new ArrayList<>();
        for ( SchemaRule rule : schemaCache.schemaRules() )
        {
            if ( rule.getKind().isIndex() )
            {
                IndexRule indexRule = (IndexRule) rule;
                SchemaIndexProvider provider =
                        schemaIndexProviders.apply( indexRule.getProviderDescriptor() );
                if ( provider.getInitialState( indexRule.getId() ) != InternalIndexState.FAILED )
                {
                    indexesNeedingPopulation.add( indexRule );
                }
            }
        }
        return indexesNeedingPopulation.toArray( new IndexRule[indexesNeedingPopulation.size()] );
    }

    @Override
    public ConstraintCreator createDeferredConstraint( Label label )
    {
        return new BaseNodeConstraintCreator( new BatchSchemaActions(), label );
    }

    @Override
    public RelationshipConstraintCreator createDeferredConstraint( RelationshipType type )
    {
        return new BaseRelationshipConstraintCreator( new BatchSchemaActions(), type );
    }

    private void createConstraintRule( UniquenessConstraint constraint )
    {
        // TODO: Do not create duplicate index

        SchemaStore schemaStore = getSchemaStore();

        long indexRuleId = schemaStore.nextId();
        long constraintRuleId = schemaStore.nextId();

        IndexRule indexRule = IndexRule.constraintIndexRule(
                indexRuleId, constraint.label(), constraint.propertyKey(),
                this.schemaIndexProviders.getDefaultProvider().getProviderDescriptor(),
                constraintRuleId );
        UniquePropertyConstraintRule
                constraintRule = UniquePropertyConstraintRule.uniquenessConstraintRule(
                constraintRuleId, constraint.label(), constraint.propertyKey(), indexRuleId );

        for ( DynamicRecord record : schemaStore.allocateFrom( constraintRule ) )
        {
            schemaStore.updateRecord( record );
        }
        schemaCache.addSchemaRule( constraintRule );
        for ( DynamicRecord record : schemaStore.allocateFrom( indexRule ) )
        {
            schemaStore.updateRecord( record );
        }
        schemaCache.addSchemaRule( indexRule );
        labelsTouched = true;
        flushStrategy.forceFlush();
    }

    private void createConstraintRule( MandatoryNodePropertyConstraint constraint )
    {
        SchemaStore schemaStore = getSchemaStore();

        SchemaRule rule = MandatoryNodePropertyConstraintRule.mandatoryNodePropertyConstraintRule( schemaStore.nextId(),
                constraint.label(), constraint.propertyKey() );

        for ( DynamicRecord record : schemaStore.allocateFrom( rule ) )
        {
            schemaStore.updateRecord( record );
        }
        schemaCache.addSchemaRule( rule );
        labelsTouched = true;
        flushStrategy.forceFlush();
    }

    private void createConstraintRule( MandatoryRelationshipPropertyConstraint constraint )
    {
        SchemaStore schemaStore = getSchemaStore();

        SchemaRule rule = MandatoryRelationshipPropertyConstraintRule.mandatoryRelPropertyConstraintRule(
                schemaStore.nextId(), constraint.relationshipType(), constraint.propertyKey() );

        for ( DynamicRecord record : schemaStore.allocateFrom( rule ) )
        {
            schemaStore.updateRecord( record );
        }
        schemaCache.addSchemaRule( rule );
        flushStrategy.forceFlush();
    }

    private int getOrCreatePropertyKeyId( String name )
    {
        int propertyKeyId = tokenIdByName( propertyKeyTokens, name );
        if ( propertyKeyId == -1 )
        {
            propertyKeyId = createNewPropertyKeyId( name );
        }
        return propertyKeyId;
    }

    private int getOrCreateRelationshipTypeToken( RelationshipType type )
    {
        int typeId = tokenIdByName( relationshipTypeTokens, type.name() );
        if ( typeId == -1 )
        {
            typeId = createNewRelationshipType( type.name() );
        }
        return typeId;
    }

    private int getOrCreateLabelId( String name )
    {
        int labelId = tokenIdByName( labelTokens, name );
        if ( labelId == -1 )
        {
            labelId = createNewLabelId( name );
        }
        return labelId;
    }

    private int getOrCreateRelationshipTypeId( String name )
    {
        int relationshipTypeId = tokenIdByName( relationshipTypeTokens, name );
        if ( relationshipTypeId == -1 )
        {
            relationshipTypeId = createNewRelationshipType( name );
        }
        return relationshipTypeId;
    }

    private int tokenIdByName( BatchTokenHolder tokens, String name )
    {
        Token token = tokens.byName( name );
        return token != null ? token.id() : -1;
    }

    private boolean primitiveHasProperty( PrimitiveRecord record, String propertyName )
    {
        int propertyKeyId = tokenIdByName( propertyKeyTokens, propertyName );
        return propertyKeyId != -1 && propertyTraverser.findPropertyRecordContaining( record, propertyKeyId,
                recordAccess.getPropertyRecords(), false ) != Record.NO_NEXT_PROPERTY.intValue();
    }

    private void rejectAutoUpgrade( Map<String, String> params )
    {
        if ( parseBoolean( params.get( GraphDatabaseSettings.allow_store_upgrade.name() ) ) )
        {
            throw new IllegalArgumentException( "Batch inserter is not allowed to do upgrade of a store" +
                                                ", use " + EmbeddedGraphDatabase.class.getSimpleName() + " instead" );
        }
    }

    @Override
    public long createNode( Map<String, Object> properties, Label... labels )
    {
        return internalCreateNode( getNodeStore().nextId(), properties, labels );
    }

    private long internalCreateNode( long nodeId, Map<String, Object> properties, Label... labels )
    {
        NodeRecord nodeRecord = recordAccess.getNodeRecords().create( nodeId, null ).forChangingData();
        nodeRecord.setInUse( true );
        nodeRecord.setCreated();
        nodeRecord.setNextProp( propertyCreator.createPropertyChain( nodeRecord,
                propertiesIterator( properties ), recordAccess.getPropertyRecords() ) );

        if ( labels.length > 0 )
        {
            setNodeLabels( nodeRecord, labels );
        }

        flushStrategy.flush();
        return nodeId;
    }

    private Iterator<PropertyBlock> propertiesIterator( Map<String, Object> properties )
    {
        if ( properties == null || properties.isEmpty() )
        {
            return IteratorUtil.emptyIterator();
        }
        return new IteratorWrapper<PropertyBlock, Map.Entry<String,Object>>( properties.entrySet().iterator() )
        {
            @Override
            protected PropertyBlock underlyingObjectToObject( Entry<String, Object> property )
            {
                return propertyCreator.encodePropertyValue(
                        getOrCreatePropertyKeyId( property.getKey() ), property.getValue() );
            }
        };
    }

    private void setNodeLabels( NodeRecord nodeRecord, Label... labels )
    {
        NodeLabels nodeLabels = parseLabelsField( nodeRecord );
        getNodeStore().updateDynamicLabelRecords( nodeLabels.put( getOrCreateLabelIds( labels ), getNodeStore(),
                getNodeStore().getDynamicLabelStore() ) );
        labelsTouched = true;
    }

    private long[] getOrCreateLabelIds( Label[] labels )
    {
        long[] ids = new long[labels.length];
        int cursor = 0;
        for ( int i = 0; i < ids.length; i++ )
        {
            int labelId = getOrCreateLabelId( labels[i].name() );
            if ( !arrayContains( ids, cursor, labelId ) )
            {
                ids[cursor++] = labelId;
            }
        }
        if ( cursor < ids.length )
        {
            ids = Arrays.copyOf( ids, cursor );
        }
        return ids;
    }

    private boolean arrayContains( long[] ids, int cursor, int labelId )
    {
        for ( int i = 0; i < cursor; i++ )
        {
            if ( ids[i] == labelId )
            {
                return true;
            }
        }
        return false;
    }

    @Override
    public void createNode( long id, Map<String, Object> properties, Label... labels )
    {
        if ( id < 0 || id > MAX_NODE_ID )
        {
            throw new IllegalArgumentException( "id=" + id );
        }
        if ( id == IdGeneratorImpl.INTEGER_MINUS_ONE )
        {
            throw new IllegalArgumentException( "id " + id + " is reserved for internal use" );
        }
        NodeStore nodeStore = neoStore.getNodeStore();
        if ( neoStore.getNodeStore().loadLightNode( id ) != null )
        {
            throw new IllegalArgumentException( "id=" + id + " already in use" );
        }
        long highId = nodeStore.getHighId();
        if ( highId <= id )
        {
            nodeStore.setHighestPossibleIdInUse( id );
        }
        internalCreateNode( id, properties, labels );
    }

    @Override
    public void setNodeLabels( long node, Label... labels )
    {
        NodeRecord record = getNodeRecord( node ).forChangingData();
        setNodeLabels( record, labels );
        flushStrategy.flush();
    }

    @Override
    public Iterable<Label> getNodeLabels( final long node )
    {
        return new Iterable<Label>()
        {
            @Override
            public Iterator<Label> iterator()
            {
                NodeRecord record = getNodeRecord( node ).forReadingData();
                long[] labels = parseLabelsField( record ).get( getNodeStore() );
                return map( labelIdToLabelFunction, PrimitiveLongCollections.iterator( labels ) );
            }
        };
    }

    @Override
    public boolean nodeHasLabel( long node, Label label )
    {
        int labelId = tokenIdByName( labelTokens, label.name() );
        return labelId != -1 && nodeHasLabel( node, labelId );
    }

    private boolean nodeHasLabel( long node, int labelId )
    {
        NodeRecord record = getNodeRecord( node ).forReadingData();
        for ( long label : parseLabelsField( record ).get( getNodeStore() ) )
        {
            if ( label == labelId )
            {
                return true;
            }
        }
        return false;
    }

    @Override
    public long createRelationship( long node1, long node2, RelationshipType type,
            Map<String, Object> properties )
    {
        long id = neoStore.getRelationshipStore().nextId();
        int typeId = getOrCreateRelationshipTypeToken( type );
        relationshipCreator.relationshipCreate( id, typeId, node1, node2, recordAccess );
        if ( properties != null && !properties.isEmpty() )
        {
            RelationshipRecord record = recordAccess.getRelRecords().getOrLoad( id, null ).forChangingData();
            record.setNextProp( propertyCreator.createPropertyChain( record,
                    propertiesIterator( properties ), recordAccess.getPropertyRecords() ) );
        }
        flushStrategy.flush();
        return id;
    }

    @Override
    public void setNodeProperties( long node, Map<String, Object> properties )
    {
        NodeRecord record = getNodeRecord( node ).forChangingData();
        if ( record.getNextProp() != Record.NO_NEXT_PROPERTY.intValue() )
        {
            propertyDeletor.getAndDeletePropertyChain( record, recordAccess.getPropertyRecords() );
        }
        record.setNextProp( propertyCreator.createPropertyChain( record, propertiesIterator( properties ),
                recordAccess.getPropertyRecords() ) );
        flushStrategy.flush();
    }

    @Override
    public void setRelationshipProperties( long rel, Map<String, Object> properties )
    {
        RelationshipRecord record = recordAccess.getRelRecords().getOrLoad( rel, null ).forChangingData();
        if ( record.getNextProp() != Record.NO_NEXT_PROPERTY.intValue() )
        {
            propertyDeletor.getAndDeletePropertyChain( record, recordAccess.getPropertyRecords() );
        }
        record.setNextProp( propertyCreator.createPropertyChain( record, propertiesIterator( properties ),
                recordAccess.getPropertyRecords() ) );
        flushStrategy.flush();
    }

    @Override
    public boolean nodeExists( long nodeId )
    {
        flushStrategy.forceFlush();
        return neoStore.getNodeStore().loadLightNode( nodeId ) != null;
    }

    @Override
    public Map<String, Object> getNodeProperties( long nodeId )
    {
        NodeRecord record = getNodeRecord( nodeId ).forReadingData();
        if ( record.getNextProp() != Record.NO_NEXT_PROPERTY.intValue() )
        {
            return getPropertyChain( record.getNextProp() );
        }
        return Collections.emptyMap();
    }

    @Override
    public Iterable<Long> getRelationshipIds( long nodeId )
    {
        flushStrategy.forceFlush();
        return new BatchRelationshipIterable<Long>( neoStore, nodeId )
        {
            @Override
            protected Long nextFrom( long relId, int type, long startNode, long endNode )
            {
                return relId;
            }
        };
    }

    @Override
    public Iterable<BatchRelationship> getRelationships( long nodeId )
    {
        flushStrategy.forceFlush();
        return new BatchRelationshipIterable<BatchRelationship>( neoStore, nodeId )
        {
            @Override
            protected BatchRelationship nextFrom( long relId, int type, long startNode, long endNode )
            {
                return new BatchRelationship( relId, startNode, endNode,
                        (RelationshipType) relationshipTypeTokens.byId( type ) );
            }
        };
    }

    @Override
    public BatchRelationship getRelationshipById( long relId )
    {
        RelationshipRecord record = getRelationshipRecord( relId ).forReadingData();
        RelationshipType type = (RelationshipType) relationshipTypeTokens.byId( record.getType() );
        return new BatchRelationship( record.getId(), record.getFirstNode(), record.getSecondNode(), type );
    }

    @Override
    public Map<String, Object> getRelationshipProperties( long relId )
    {
        RelationshipRecord record = recordAccess.getRelRecords().getOrLoad( relId, null ).forChangingData();
        if ( record.getNextProp() != Record.NO_NEXT_PROPERTY.intValue() )
        {
            return getPropertyChain( record.getNextProp() );
        }
        return Collections.emptyMap();
    }

    @Override
    public void shutdown()
    {
        flushStrategy.forceFlush();

        if ( isShutdown )
        {
            throw new IllegalStateException( "Batch inserter already has shutdown" );
        }
        isShutdown = true;

        try
        {
            repopulateAllIndexes();
        }
        catch ( IOException | IndexCapacityExceededException e )
        {
            throw new RuntimeException( e );
        }
        rebuildCounts();
        neoStore.close();

        try
        {
            storeLocker.release();
        }
        catch ( IOException e )
        {
            throw new UnderlyingStorageException( "Could not release store lock", e );
        }

        msgLog.info( Thread.currentThread() + " Clean shutdown on BatchInserter(" + this + ")", true );
        life.shutdown();
    }

    @Override
    public String toString()
    {
        return "EmbeddedBatchInserter[" + storeDir + "]";
    }

    private Map<String, Object> getPropertyChain( long nextProp )
    {
        final Map<String, Object> map = new HashMap<>();
        propertyTraverser.getPropertyChain( nextProp, recordAccess.getPropertyRecords(), new Listener<PropertyBlock>()
        {
            @Override
            public void receive( PropertyBlock propBlock )
            {
                String key = propertyKeyTokens.byId( propBlock.getKeyIndexId() ).name();
                DefinedProperty propertyData = propBlock.newPropertyData( getPropertyStore() );
                Object value = propertyData.value() != null ? propertyData.value() :
                               propBlock.getType().getValue( propBlock, getPropertyStore() );
                map.put( key, value );
            }
        } );
        return map;
    }

    private int createNewPropertyKeyId( String stringKey )
    {
        PropertyKeyTokenStore idxStore = getPropertyKeyTokenStore();
        int keyId = (int) idxStore.nextId();
        PropertyKeyTokenRecord record = new PropertyKeyTokenRecord( keyId );
        record.setInUse( true );
        record.setCreated();
        Collection<DynamicRecord> keyRecords =
                idxStore.allocateNameRecords( encodeString( stringKey ) );
        record.setNameId( (int) first( keyRecords ).getId() );
        record.addNameRecords( keyRecords );
        idxStore.updateRecord( record );
        propertyKeyTokens.addToken( new Token( stringKey, keyId ) );
        return keyId;
    }

    private int createNewLabelId( String stringKey )
    {
        LabelTokenStore labelTokenStore = neoStore.getLabelTokenStore();
        int keyId = (int) labelTokenStore.nextId();
        LabelTokenRecord record = new LabelTokenRecord( keyId );
        record.setInUse( true );
        record.setCreated();
        Collection<DynamicRecord> keyRecords =
                labelTokenStore.allocateNameRecords( encodeString( stringKey ) );
        record.setNameId( (int) first( keyRecords ).getId() );
        record.addNameRecords( keyRecords );
        labelTokenStore.updateRecord( record );
        labelTokens.addToken( new Token( stringKey, keyId ) );
        return keyId;
    }

    private int createNewRelationshipType( String name )
    {
        RelationshipTypeTokenStore typeStore = getRelationshipTypeStore();
        int id = (int) typeStore.nextId();
        RelationshipTypeTokenRecord record = new RelationshipTypeTokenRecord( id );
        record.setInUse( true );
        record.setCreated();
        Collection<DynamicRecord> nameRecords = typeStore.allocateNameRecords( encodeString( name ) );
        record.setNameId( (int) first( nameRecords ).getId() );
        record.addNameRecords( nameRecords );
        typeStore.updateRecord( record );
        relationshipTypeTokens.addToken( new RelationshipTypeToken( name, id ) );
        return id;
    }

    private NodeStore getNodeStore()
    {
        return neoStore.getNodeStore();
    }

    private RelationshipStore getRelationshipStore()
    {
        return neoStore.getRelationshipStore();
    }

    private PropertyStore getPropertyStore()
    {
        return neoStore.getPropertyStore();
    }

    private PropertyKeyTokenStore getPropertyKeyTokenStore()
    {
        return neoStore.getPropertyKeyTokenStore();
    }

    private RelationshipTypeTokenStore getRelationshipTypeStore()
    {
        return neoStore.getRelationshipTypeTokenStore();
    }

    private SchemaStore getSchemaStore()
    {
        return neoStore.getSchemaStore();
    }

    private RecordProxy<Long,NodeRecord,Void> getNodeRecord( long id )
    {
        if ( id < 0 || id >= getNodeStore().getHighId() )
        {
            throw new NotFoundException( "id=" + id );
        }
        return recordAccess.getNodeRecords().getOrLoad( id, null );
    }

    private RecordProxy<Long,RelationshipRecord,Void> getRelationshipRecord( long id )
    {
        if ( id < 0 || id >= getRelationshipStore().getHighId() )
        {
            throw new NotFoundException( "id=" + id );
        }
        return recordAccess.getRelRecords().getOrLoad( id, null );
    }

    @Override
    public String getStoreDir()
    {
        return storeDir.getPath();
    }

    // needed by lucene-index
    public IndexConfigStore getIndexStore()
    {
        return this.indexStore;
    }

    public IdGeneratorFactory getIdGeneratorFactory()
    {
        return idGeneratorFactory;
    }

    private void dumpConfiguration( Map<String, String> config )
    {
        for ( String key : config.keySet() )
        {
            Object value = config.get( key );
            if ( value != null )
            {
                // TODO no, No, NO NO NO!!! No. Pass in the PrintStream instead.
                System.out.println( key + "=" + value );
            }
        }
    }

    private class BatchSchemaActions implements InternalSchemaActions
    {
        @Override
        public IndexDefinition createIndexDefinition( Label label, String propertyKey )
        {
            int labelId = getOrCreateLabelId( label.name() );
            int propertyKeyId = getOrCreatePropertyKeyId( propertyKey );

            validateNodeConstraintCanBeCreated( labelId, propertyKeyId );

            createIndexRule( labelId, propertyKeyId );
            return new IndexDefinitionImpl( this, label, propertyKey, false );
        }

        @Override
        public void dropIndexDefinitions( Label label, String propertyKey )
        {
            throw unsupportedException();
        }

        @Override
        public ConstraintDefinition createPropertyUniquenessConstraint( Label label, String propertyKey )
        {
            int labelId = getOrCreateLabelId( label.name() );
            int propertyKeyId = getOrCreatePropertyKeyId( propertyKey );

            validateNodeConstraintCanBeCreated( labelId, propertyKeyId );

            createConstraintRule( new UniquenessConstraint( labelId, propertyKeyId ) );
            return new UniquenessConstraintDefinition( this, label, propertyKey );
        }

        @Override
        public ConstraintDefinition createPropertyExistenceConstraint( Label label, String propertyKey )
        {
            int labelId = getOrCreateLabelId( label.name() );
            int propertyKeyId = getOrCreatePropertyKeyId( propertyKey );

            validateNodeConstraintCanBeCreated( labelId, propertyKeyId );

            createConstraintRule( new MandatoryNodePropertyConstraint( labelId, propertyKeyId ) );
            return new MandatoryNodePropertyConstraintDefinition( this, label, propertyKey );
        }

        @Override
        public ConstraintDefinition createPropertyExistenceConstraint( RelationshipType type, String propertyKey )
                throws CreateConstraintFailureException, AlreadyConstrainedException
        {
            int relationshipTypeId = getOrCreateRelationshipTypeId( type.name() );
            int propertyKeyId = getOrCreatePropertyKeyId( propertyKey );

            validateRelationshipConstraintCanBeCreated( relationshipTypeId, propertyKeyId );

            createConstraintRule( new MandatoryRelationshipPropertyConstraint( relationshipTypeId, propertyKeyId ) );
            return new MandatoryRelationshipPropertyConstraintDefinition( this, type, propertyKey );
        }

        @Override
        public void dropPropertyUniquenessConstraint( Label label, String propertyKey )
        {
            throw unsupportedException();
        }

        @Override
        public void dropNodePropertyExistenceConstraint( Label label, String propertyKey )
        {
            throw unsupportedException();
        }

        @Override
        public void dropRelationshipPropertyExistenceConstraint( RelationshipType type, String propertyKey )
        {
            throw unsupportedException();
        }

        @Override
        public String getUserMessage( KernelException e )
        {
            throw unsupportedException();
        }

        @Override
        public void assertInUnterminatedTransaction()
        {
            // BatchInserterImpl always is expected to be running in one big single "transaction"
        }

        private UnsupportedOperationException unsupportedException()
        {
            return new UnsupportedOperationException( "Batch inserter doesn't support this" );
        }
    }

    interface FlushStrategy
    {
        void flush();

        void forceFlush();
    }

    static final class BatchedFlushStrategy implements FlushStrategy
    {
        private final DirectRecordAccessSet directRecordAccess;
        private final int batchSize;
        private int attempts;

        public BatchedFlushStrategy(DirectRecordAccessSet directRecordAccess,  int batchSize )
        {
            this.directRecordAccess = directRecordAccess;
            this.batchSize = batchSize;
        }


        @Override
        public void flush()
        {
            attempts++;
            if ( attempts >= batchSize)
            {
                forceFlush();
            }
        }

        @Override
        public void forceFlush()
        {
            directRecordAccess.commit();
            attempts = 0;
        }
    }
}


File: community/kernel/src/test/java/org/neo4j/kernel/impl/api/integrationtest/ConstraintCreationIT.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.kernel.impl.api.integrationtest;

import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Suite;

import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

import org.neo4j.function.Function;
import org.neo4j.graphdb.ConstraintViolationException;
import org.neo4j.graphdb.GraphDatabaseService;
import org.neo4j.graphdb.Node;
import org.neo4j.graphdb.Relationship;
import org.neo4j.graphdb.ResourceIterator;
import org.neo4j.graphdb.Transaction;
import org.neo4j.graphdb.schema.ConstraintDefinition;
import org.neo4j.graphdb.schema.IndexDefinition;
import org.neo4j.graphdb.schema.Schema;
import org.neo4j.kernel.api.DataWriteOperations;
import org.neo4j.kernel.api.ReadOperations;
import org.neo4j.kernel.api.SchemaWriteOperations;
import org.neo4j.kernel.api.StatementTokenNameLookup;
import org.neo4j.kernel.api.constraints.MandatoryNodePropertyConstraint;
import org.neo4j.kernel.api.constraints.MandatoryRelationshipPropertyConstraint;
import org.neo4j.kernel.api.constraints.NodePropertyConstraint;
import org.neo4j.kernel.api.constraints.PropertyConstraint;
import org.neo4j.kernel.api.constraints.UniquenessConstraint;
import org.neo4j.kernel.api.exceptions.KernelException;
import org.neo4j.kernel.api.exceptions.TransactionFailureException;
import org.neo4j.kernel.api.exceptions.schema.AlreadyConstrainedException;
import org.neo4j.kernel.api.exceptions.schema.ConstraintVerificationFailedKernelException;
import org.neo4j.kernel.api.exceptions.schema.CreateConstraintFailureException;
import org.neo4j.kernel.api.exceptions.schema.DropConstraintFailureException;
import org.neo4j.kernel.api.exceptions.schema.NoSuchConstraintException;
import org.neo4j.kernel.api.index.IndexDescriptor;
import org.neo4j.kernel.api.properties.Property;
import org.neo4j.kernel.impl.store.SchemaStorage;
import org.neo4j.kernel.impl.store.UniquePropertyConstraintRule;
import org.neo4j.kernel.impl.store.record.IndexRule;
import org.neo4j.test.OtherThreadRule;
import org.neo4j.test.TargetDirectory;
import org.neo4j.tooling.GlobalGraphOperations;

import static java.lang.String.format;
import static java.util.Collections.singletonList;
import static org.hamcrest.CoreMatchers.instanceOf;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertThat;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;
import static org.junit.runners.Suite.SuiteClasses;
import static org.neo4j.graphdb.DynamicLabel.label;
import static org.neo4j.graphdb.DynamicRelationshipType.withName;
import static org.neo4j.helpers.collection.IteratorUtil.asCollection;
import static org.neo4j.helpers.collection.IteratorUtil.asList;
import static org.neo4j.helpers.collection.IteratorUtil.asSet;
import static org.neo4j.helpers.collection.IteratorUtil.emptySetOf;
import static org.neo4j.helpers.collection.IteratorUtil.single;
import static org.neo4j.kernel.impl.api.integrationtest.ConstraintCreationIT.*;

@RunWith( Suite.class )
@SuiteClasses( {
        MandatoryNodePropertyConstraintCreationIT.class,
        MandatoryRelationshipPropertyConstraintCreationIT.class,
        UniquenessConstraintCreationIT.class
} )
public class ConstraintCreationIT
{
    public static class MandatoryNodePropertyConstraintCreationIT
            extends AbstractConstraintCreationIT<MandatoryNodePropertyConstraint>
    {
        @Override
        int initializeLabelOrRelType( SchemaWriteOperations writeOps, String name ) throws KernelException
        {
            return writeOps.labelGetOrCreateForName( name );
        }

        @Override
        MandatoryNodePropertyConstraint createConstraint( SchemaWriteOperations writeOps, int type, int property )
                throws Exception
        {
            return writeOps.mandatoryNodePropertyConstraintCreate( type, property );
        }

        @Override
        void createConstraintInRunningTx( GraphDatabaseService db, String type, String property )
        {
            db.schema().constraintFor( label( type ) ).assertPropertyExists( property ).create();
        }

        @Override
        MandatoryNodePropertyConstraint newConstraintObject( int type, int property )
        {
            return new MandatoryNodePropertyConstraint( type, property );
        }

        @Override
        void dropConstraint( SchemaWriteOperations writeOps, MandatoryNodePropertyConstraint constraint )
                throws Exception
        {
            writeOps.constraintDrop( constraint );
        }

        @Override
        void createOffendingDataInRunningTx( GraphDatabaseService db )
        {
            db.createNode( label( KEY ) );
        }

        @Override
        void removeOffendingDataInRunningTx( GraphDatabaseService db )
        {
            try ( ResourceIterator<Node> nodes = db.findNodes( label( KEY ) ) )
            {
                while ( nodes.hasNext() )
                {
                    nodes.next().delete();
                }
            }
        }

        @Test
        public void shouldNotDropMandatoryPropertyConstraintThatDoesNotExistWhenThereIsAUniquePropertyConstraint()
                throws Exception
        {
            // given
            UniquenessConstraint constraint;
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();
                constraint = statement.uniquePropertyConstraintCreate( typeId, propertyKeyId );
                commit();
            }

            // when
            try
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();
                statement.constraintDrop(
                        new MandatoryNodePropertyConstraint( constraint.label(), constraint.propertyKey() ) );

                fail( "expected exception" );
            }
            // then
            catch ( DropConstraintFailureException e )
            {
                assertThat( e.getCause(), instanceOf( NoSuchConstraintException.class ) );
            }
            finally
            {
                rollback();
            }

            // then
            {
                ReadOperations statement = readOperationsInNewTransaction();

                Iterator<NodePropertyConstraint> constraints =
                        statement.constraintsGetForLabelAndPropertyKey( typeId, propertyKeyId );

                assertEquals( constraint, single( constraints ) );
            }
        }
    }

    public static class MandatoryRelationshipPropertyConstraintCreationIT
            extends AbstractConstraintCreationIT<MandatoryRelationshipPropertyConstraint>
    {
        @Override
        int initializeLabelOrRelType( SchemaWriteOperations writeOps, String name ) throws KernelException
        {
            return writeOps.relationshipTypeGetOrCreateForName( name );
        }

        @Override
        MandatoryRelationshipPropertyConstraint createConstraint( SchemaWriteOperations writeOps, int type,
                int property ) throws Exception
        {
            return writeOps.mandatoryRelationshipPropertyConstraintCreate( type, property );
        }

        @Override
        void createConstraintInRunningTx( GraphDatabaseService db, String type, String property )
        {
            db.schema().constraintFor( withName( type ) ).assertPropertyExists( property ).create();
        }

        @Override
        MandatoryRelationshipPropertyConstraint newConstraintObject( int type, int property )
        {
            return new MandatoryRelationshipPropertyConstraint( type, property );
        }

        @Override
        void dropConstraint( SchemaWriteOperations writeOps, MandatoryRelationshipPropertyConstraint constraint )
                throws Exception
        {
            writeOps.constraintDrop( constraint );
        }

        @Override
        void createOffendingDataInRunningTx( GraphDatabaseService db )
        {
            Node start = db.createNode();
            Node end = db.createNode();
            start.createRelationshipTo( end, withName( KEY ) );
        }

        @Override
        void removeOffendingDataInRunningTx( GraphDatabaseService db )
        {
            Iterable<Relationship> relationships = GlobalGraphOperations.at( db ).getAllRelationships();
            for ( Relationship relationship : relationships )
            {
                relationship.delete();
            }
        }
    }

    public static class UniquenessConstraintCreationIT extends AbstractConstraintCreationIT<UniquenessConstraint>
    {
        private static final String DUPLICATED_VALUE = "apa";

        @Rule
        public final TargetDirectory.TestDirectory testDir = TargetDirectory.testDirForTest( getClass() );

        @Rule
        public final OtherThreadRule<Void> otherThread = new OtherThreadRule<>();

        @Override
        int initializeLabelOrRelType( SchemaWriteOperations writeOps, String name ) throws KernelException
        {
            return writeOps.labelGetOrCreateForName( KEY );
        }

        @Override
        UniquenessConstraint createConstraint( SchemaWriteOperations writeOps, int type, int property ) throws Exception
        {
            return writeOps.uniquePropertyConstraintCreate( type, property );
        }

        @Override
        void createConstraintInRunningTx( GraphDatabaseService db, String type, String property )
        {
            db.schema().constraintFor( label( type ) ).assertPropertyIsUnique( property ).create();
        }

        @Override
        UniquenessConstraint newConstraintObject( int type, int property )
        {
            return new UniquenessConstraint( type, property );
        }

        @Override
        void dropConstraint( SchemaWriteOperations writeOps, UniquenessConstraint constraint ) throws Exception
        {
            writeOps.constraintDrop( constraint );
        }

        @Override
        void createOffendingDataInRunningTx( GraphDatabaseService db )
        {
            db.createNode( label( KEY ) ).setProperty( PROP, DUPLICATED_VALUE );
            db.createNode( label( KEY ) ).setProperty( PROP, DUPLICATED_VALUE );
        }

        @Override
        void removeOffendingDataInRunningTx( GraphDatabaseService db )
        {
            try ( ResourceIterator<Node> nodes = db.findNodes( label( KEY ), PROP, DUPLICATED_VALUE ) )
            {
                while ( nodes.hasNext() )
                {
                    nodes.next().delete();
                }
            }
        }

        @Test
        public void shouldAbortConstraintCreationWhenDuplicatesExist() throws Exception
        {
            // given
            long node1, node2;
            int foo, name;
            {
                DataWriteOperations statement = dataWriteOperationsInNewTransaction();
                // name is not unique for Foo in the existing data

                foo = statement.labelGetOrCreateForName( "Foo" );
                name = statement.propertyKeyGetOrCreateForName( "name" );

                long node = statement.nodeCreate();
                node1 = node;
                statement.nodeAddLabel( node, foo );
                statement.nodeSetProperty( node, Property.stringProperty( name, "foo" ) );

                node = statement.nodeCreate();
                statement.nodeAddLabel( node, foo );
                node2 = node;
                statement.nodeSetProperty( node, Property.stringProperty( name, "foo" ) );
                commit();
            }

            // when
            try
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();
                statement.uniquePropertyConstraintCreate( foo, name );

                fail( "expected exception" );
            }
            // then
            catch ( CreateConstraintFailureException ex )
            {
                assertEquals( new UniquenessConstraint( foo, name ), ex.constraint() );
                Throwable cause = ex.getCause();
                assertThat( cause, instanceOf( ConstraintVerificationFailedKernelException.class ) );

                String expectedMessage = format(
                        "Multiple nodes with label `%s` have property `%s` = '%s':%n  node(%d)%n  node(%d)",
                        "Foo", "name", "foo", node1, node2 );
                String actualMessage = userMessage( (ConstraintVerificationFailedKernelException) cause );
                assertEquals( expectedMessage, actualMessage );
            }
        }

        @Test
        public void shouldCreateAnIndexToGoAlongWithAUniquePropertyConstraint() throws Exception
        {
            // when
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();
                statement.uniquePropertyConstraintCreate( typeId, propertyKeyId );
                commit();
            }

            // then
            {
                ReadOperations statement = readOperationsInNewTransaction();
                assertEquals( asSet( new IndexDescriptor( typeId, propertyKeyId ) ),
                        asSet( statement.uniqueIndexesGetAll() ) );
            }
        }

        @Test
        public void shouldDropCreatedConstraintIndexWhenRollingBackConstraintCreation() throws Exception
        {
            // given
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();
                statement.uniquePropertyConstraintCreate( typeId, propertyKeyId );
                assertEquals( asSet( new IndexDescriptor( typeId, propertyKeyId ) ),
                        asSet( statement.uniqueIndexesGetAll() ) );
            }

            // when
            rollback();

            // then
            {
                ReadOperations statement = readOperationsInNewTransaction();
                assertEquals( emptySetOf( IndexDescriptor.class ), asSet( statement.uniqueIndexesGetAll() ) );
                commit();
            }
        }

        @Test
        public void shouldNotDropUniquePropertyConstraintThatDoesNotExistWhenThereIsAMandatoryPropertyConstraint()
                throws Exception
        {
            // given
            MandatoryNodePropertyConstraint constraint;
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();
                constraint = statement.mandatoryNodePropertyConstraintCreate( typeId, propertyKeyId );
                commit();
            }

            // when
            try
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();
                statement.constraintDrop( new UniquenessConstraint( constraint.label(), constraint.propertyKey() ) );

                fail( "expected exception" );
            }
            // then
            catch ( DropConstraintFailureException e )
            {
                assertThat( e.getCause(), instanceOf( NoSuchConstraintException.class ) );
            }
            finally
            {
                rollback();
            }

            // then
            {
                ReadOperations statement = readOperationsInNewTransaction();

                Iterator<NodePropertyConstraint> constraints =
                        statement.constraintsGetForLabelAndPropertyKey( typeId, propertyKeyId );

                assertEquals( constraint, single( constraints ) );
            }
        }

        @Test
        public void committedConstraintRuleShouldCrossReferenceTheCorrespondingIndexRule() throws Exception
        {
            // when
            SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();
            statement.uniquePropertyConstraintCreate( typeId, propertyKeyId );
            commit();

            // then
            SchemaStorage schema = new SchemaStorage( neoStore().getSchemaStore() );
            IndexRule indexRule = schema.indexRule( typeId, propertyKeyId );
            UniquePropertyConstraintRule constraintRule = schema.uniquenessConstraint( typeId, propertyKeyId );
            assertEquals( constraintRule.getId(), indexRule.getOwningConstraint().longValue() );
            assertEquals( indexRule.getId(), constraintRule.getOwnedIndex() );
        }

        @Test
        public void shouldDropConstraintIndexWhenDroppingConstraint() throws Exception
        {
            // given
            UniquenessConstraint constraint;
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();
                constraint = statement.uniquePropertyConstraintCreate( typeId, propertyKeyId );
                assertEquals( asSet( new IndexDescriptor( typeId, propertyKeyId ) ),
                        asSet( statement.uniqueIndexesGetAll() ) );
                commit();
            }

            // when
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();
                statement.constraintDrop( constraint );
                commit();
            }

            // then
            {
                ReadOperations statement = readOperationsInNewTransaction();
                assertEquals( emptySetOf( IndexDescriptor.class ), asSet( statement.uniqueIndexesGetAll() ) );
                commit();
            }
        }

        private String userMessage( ConstraintVerificationFailedKernelException cause )
                throws TransactionFailureException
        {
            StatementTokenNameLookup lookup = new StatementTokenNameLookup( readOperationsInNewTransaction() );
            String actualMessage = cause.getUserMessage( lookup );
            commit();
            return actualMessage;
        }
    }

    public abstract static class AbstractConstraintCreationIT<Constraint extends PropertyConstraint>
            extends KernelIntegrationTest
    {
        protected static final String KEY = "Foo";
        protected static final String PROP = "bar";

        protected int typeId;
        protected int propertyKeyId;

        abstract int initializeLabelOrRelType( SchemaWriteOperations writeOps, String name ) throws KernelException;

        abstract Constraint createConstraint( SchemaWriteOperations writeOps, int type, int property ) throws Exception;

        abstract void createConstraintInRunningTx( GraphDatabaseService db, String type, String property );

        abstract Constraint newConstraintObject( int type, int property );

        abstract void dropConstraint( SchemaWriteOperations writeOps, Constraint constraint ) throws Exception;

        abstract void createOffendingDataInRunningTx( GraphDatabaseService db );

        abstract void removeOffendingDataInRunningTx( GraphDatabaseService db );


        @Before
        public void createKeys() throws Exception
        {
            SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();
            this.typeId = initializeLabelOrRelType( statement, KEY );
            this.propertyKeyId = statement.propertyKeyGetOrCreateForName( PROP );
            commit();
        }

        @Test
        public void shouldBeAbleToStoreAndRetrieveConstraint() throws Exception
        {
            // given
            PropertyConstraint constraint;
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();

                // when
                constraint = createConstraint( statement, typeId, propertyKeyId );

                // then
                assertEquals( constraint, single( statement.constraintsGetAll() ) );

                // given
                commit();
            }
            {
                ReadOperations statement = readOperationsInNewTransaction();

                // when
                Iterator<?> constraints = statement.constraintsGetAll();

                // then
                assertEquals( constraint, single( constraints ) );
            }
        }

        @Test
        public void shouldNotPersistConstraintCreatedInAbortedTransaction() throws Exception
        {
            // given
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();

                createConstraint( statement, typeId, propertyKeyId );

                // when
                rollback();
            }
            {
                ReadOperations statement = readOperationsInNewTransaction();

                // then
                Iterator<?> constraints = statement.constraintsGetAll();
                assertFalse( "should not have any constraints", constraints.hasNext() );
            }
        }

        @Test
        public void shouldNotStoreConstraintThatIsRemovedInTheSameTransaction() throws Exception
        {
            // given
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();

                Constraint constraint = createConstraint( statement, typeId, propertyKeyId );

                // when
                dropConstraint( statement, constraint );

                // then
                assertFalse( "should not have any constraints", statement.constraintsGetAll().hasNext() );

                // when
                commit();
            }
            {
                ReadOperations statement = readOperationsInNewTransaction();

                // then
                assertFalse( "should not have any constraints", statement.constraintsGetAll().hasNext() );
            }
        }

        @Test
        public void shouldDropConstraint() throws Exception
        {
            // given
            Constraint constraint;
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();
                constraint = createConstraint( statement, typeId, propertyKeyId );
                commit();
            }

            // when
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();
                dropConstraint( statement, constraint );
                commit();
            }

            // then
            {
                ReadOperations statement = readOperationsInNewTransaction();

                // then
                assertFalse( "should not have any constraints", statement.constraintsGetAll().hasNext() );
            }
        }

        @Test
        public void shouldNotCreateConstraintThatAlreadyExists() throws Exception
        {
            // given
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();
                createConstraint( statement, typeId, propertyKeyId );
                commit();
            }

            // when
            try
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();

                createConstraint( statement, typeId, propertyKeyId );

                fail( "Should not have validated" );
            }
            // then
            catch ( AlreadyConstrainedException e )
            {
                // good
            }
        }

        @Test
        public void shouldNotRemoveConstraintThatGetsReAdded() throws Exception
        {
            // given
            Constraint constraint;
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();
                constraint = createConstraint( statement, typeId, propertyKeyId );
                commit();
            }
            SchemaStateCheck schemaState = new SchemaStateCheck().setUp();
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();

                // when
                dropConstraint( statement, constraint );
                createConstraint( statement, typeId, propertyKeyId );
                commit();
            }
            {
                ReadOperations statement = readOperationsInNewTransaction();

                // then
                assertEquals( singletonList( constraint ), asCollection( statement.constraintsGetAll() ) );
                schemaState.assertNotCleared( statement );
            }
        }

        @Test
        public void shouldClearSchemaStateWhenConstraintIsCreated() throws Exception
        {
            // given
            SchemaStateCheck schemaState = new SchemaStateCheck().setUp();

            SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();

            // when
            createConstraint( statement, typeId, propertyKeyId );
            commit();

            // then
            schemaState.assertCleared( readOperationsInNewTransaction() );
            rollback();
        }

        @Test
        public void shouldClearSchemaStateWhenConstraintIsDropped() throws Exception
        {
            // given
            Constraint constraint;
            SchemaStateCheck schemaState;
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();
                constraint = createConstraint( statement, typeId, propertyKeyId );
                commit();

                schemaState = new SchemaStateCheck().setUp();
            }

            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();

                // when
                dropConstraint( statement, constraint );
                commit();
            }

            // then
            schemaState.assertCleared( readOperationsInNewTransaction() );
            rollback();
        }

        @Test
        public void shouldNotDropConstraintThatDoesNotExist() throws Exception
        {
            // given
            Constraint constraint = newConstraintObject( typeId, propertyKeyId );

            // when
            {
                SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();

                try
                {
                    dropConstraint( statement, constraint );
                    fail( "Should not have dropped constraint" );
                }
                catch ( DropConstraintFailureException e )
                {
                    assertThat( e.getCause(), instanceOf( NoSuchConstraintException.class ) );
                }
                commit();
            }

            // then
            {
                ReadOperations statement = readOperationsInNewTransaction();
                assertEquals( emptySetOf( IndexDescriptor.class ), asSet( statement.uniqueIndexesGetAll() ) );
                commit();
            }
        }

        @Test
        public void shouldNotLeaveAnyStateBehindAfterFailingToCreateConstraint() throws Exception
        {
            // given
            try ( Transaction tx = db.beginTx() )
            {
                assertEquals( Collections.<ConstraintDefinition>emptyList(), asList( db.schema().getConstraints() ) );
                assertEquals( Collections.<IndexDefinition,Schema.IndexState>emptyMap(),
                        indexesWithState( db.schema() ) );
                createOffendingDataInRunningTx( db );

                tx.success();
            }

            // when
            try ( Transaction tx = db.beginTx() )
            {
                createConstraintInRunningTx( db, KEY, PROP );

                tx.success();
                fail( "expected failure" );
            }
            catch ( ConstraintViolationException e )
            {
                assertTrue( e.getMessage().startsWith( "Unable to create CONSTRAINT" ) );
            }

            // then
            try ( Transaction tx = db.beginTx() )
            {
                assertEquals( Collections.<ConstraintDefinition>emptyList(), asList( db.schema().getConstraints() ) );
                assertEquals( Collections.<IndexDefinition,Schema.IndexState>emptyMap(),
                        indexesWithState( db.schema() ) );
                tx.success();
            }
        }

        @Test
        public void shouldBeAbleToResolveConflictsAndRecreateConstraintAfterFailingToCreateItDueToConflict()
                throws Exception
        {
            // given
            try ( Transaction tx = db.beginTx() )
            {
                assertEquals( Collections.<ConstraintDefinition>emptyList(), asList( db.schema().getConstraints() ) );
                assertEquals( Collections.<IndexDefinition,Schema.IndexState>emptyMap(),
                        indexesWithState( db.schema() ) );
                createOffendingDataInRunningTx( db );

                tx.success();
            }

            // when
            try ( Transaction tx = db.beginTx() )
            {
                createConstraintInRunningTx( db, KEY, PROP );

                tx.success();
                fail( "expected failure" );
            }
            catch ( ConstraintViolationException e )
            {
                assertTrue( e.getMessage().startsWith( "Unable to create CONSTRAINT" ) );
            }

            try ( Transaction tx = db.beginTx() )
            {
                removeOffendingDataInRunningTx( db );
                tx.success();
            }

            // then - this should not fail
            SchemaWriteOperations statement = schemaWriteOperationsInNewTransaction();
            createConstraint( statement, typeId, propertyKeyId );
            commit();
        }

        private static Map<IndexDefinition,Schema.IndexState> indexesWithState( Schema schema )
        {
            Map<IndexDefinition,Schema.IndexState> result = new HashMap<>();
            for ( IndexDefinition definition : schema.getIndexes() )
            {
                result.put( definition, schema.getIndexState( definition ) );
            }
            return result;
        }

        private class SchemaStateCheck implements Function<String,Integer>
        {
            int invocationCount;

            @Override
            public Integer apply( String s )
            {
                invocationCount++;
                return Integer.parseInt( s );
            }

            public SchemaStateCheck setUp() throws TransactionFailureException
            {
                ReadOperations readOperations = readOperationsInNewTransaction();
                checkState( readOperations );
                commit();
                return this;
            }

            public void assertCleared( ReadOperations readOperations )
            {
                int count = invocationCount;
                checkState( readOperations );
                assertEquals( "schema state should have been cleared.", count + 1, invocationCount );
            }

            public void assertNotCleared( ReadOperations readOperations )
            {
                int count = invocationCount;
                checkState( readOperations );
                assertEquals( "schema state should not have been cleared.", count, invocationCount );
            }

            private SchemaStateCheck checkState( ReadOperations readOperations )
            {
                assertEquals( Integer.valueOf( 7 ), readOperations.schemaStateGetOrCreate( "7", this ) );
                return this;
            }
        }
    }
}


File: community/kernel/src/test/java/org/neo4j/kernel/impl/api/store/SchemaCacheTest.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.kernel.impl.api.store;

import org.junit.Test;

import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.Set;

import org.neo4j.helpers.collection.IteratorUtil;
import org.neo4j.kernel.api.constraints.MandatoryNodePropertyConstraint;
import org.neo4j.kernel.api.constraints.MandatoryRelationshipPropertyConstraint;
import org.neo4j.kernel.api.constraints.NodePropertyConstraint;
import org.neo4j.kernel.api.constraints.RelationshipPropertyConstraint;
import org.neo4j.kernel.api.constraints.UniquenessConstraint;
import org.neo4j.kernel.api.index.IndexDescriptor;
import org.neo4j.kernel.impl.store.MandatoryNodePropertyConstraintRule;
import org.neo4j.kernel.impl.store.MandatoryRelationshipPropertyConstraintRule;
import org.neo4j.kernel.impl.store.UniquePropertyConstraintRule;
import org.neo4j.kernel.impl.store.record.IndexRule;
import org.neo4j.kernel.impl.store.record.SchemaRule;

import static java.util.Arrays.asList;
import static java.util.Collections.singleton;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.neo4j.helpers.collection.IteratorUtil.asSet;
import static org.neo4j.kernel.impl.api.index.TestSchemaIndexProviderDescriptor.PROVIDER_DESCRIPTOR;
import static org.neo4j.kernel.impl.store.MandatoryNodePropertyConstraintRule.mandatoryNodePropertyConstraintRule;
import static org.neo4j.kernel.impl.store.MandatoryRelationshipPropertyConstraintRule.mandatoryRelPropertyConstraintRule;
import static org.neo4j.kernel.impl.store.UniquePropertyConstraintRule.uniquenessConstraintRule;

public class SchemaCacheTest
{
    final SchemaRule hans = newIndexRule( 1, 0, 5 );
    final SchemaRule witch = newIndexRule( 2, 3, 6 );
    final SchemaRule gretel = newIndexRule( 3, 0, 7 );

    @Test
    public void should_construct_schema_cache()
    {
        // GIVEN
        Collection<SchemaRule> rules = asList( hans, witch, gretel );
        SchemaCache cache = new SchemaCache( rules );

        // THEN
        assertEquals( asSet( hans, gretel ), asSet( cache.schemaRulesForLabel( 0 ) ) );
        assertEquals( asSet( witch ), asSet( cache.schemaRulesForLabel( 3 ) ) );
        assertEquals( asSet( rules ), asSet( cache.schemaRules() ) );
    }

    @Test
    public void should_add_schema_rules_to_a_label()
    {
        // GIVEN
        Collection<SchemaRule> rules = Collections.emptyList();
        SchemaCache cache = new SchemaCache( rules );

        // WHEN
        cache.addSchemaRule( hans );
        cache.addSchemaRule( gretel );

        // THEN
        assertEquals( asSet( hans, gretel ), asSet( cache.schemaRulesForLabel( 0 ) ) );
    }

    @Test
    public void should_to_retrieve_all_schema_rules()
    {
        // GIVEN
        SchemaCache cache = newSchemaCache();

        // WHEN
        cache.addSchemaRule( hans );
        cache.addSchemaRule( gretel );

        // THEN
        assertEquals( asSet( hans, gretel ), asSet( cache.schemaRules() ) );
    }

    @Test
    public void should_list_constraints()
    {
        // GIVEN
        SchemaCache cache = newSchemaCache();

        // WHEN
        cache.addSchemaRule( uniquenessConstraintRule( 0l, 1, 2, 133l ) );
        cache.addSchemaRule( uniquenessConstraintRule( 1l, 3, 4, 133l ) );
        cache.addSchemaRule( mandatoryRelPropertyConstraintRule( 2l, 5, 6 ) );
        cache.addSchemaRule( mandatoryNodePropertyConstraintRule( 3l, 7, 8 ) );

        // THEN
        assertEquals(
                asSet( new UniquenessConstraint( 1, 2 ), new UniquenessConstraint( 3, 4 ),
                        new MandatoryRelationshipPropertyConstraint( 5, 6 ),
                        new MandatoryNodePropertyConstraint( 7, 8 ) ),
                asSet( cache.constraints() ) );

        assertEquals(
                asSet( new UniquenessConstraint( 1, 2 ) ),
                asSet( cache.constraintsForLabel( 1 ) ) );

        assertEquals(
                asSet( new UniquenessConstraint( 1, 2 ) ),
                asSet( cache.constraintsForLabelAndProperty( 1, 2 ) ) );

        assertEquals(
                asSet(),
                asSet( cache.constraintsForLabelAndProperty( 1, 3 ) ) );

        assertEquals(
                asSet( new MandatoryRelationshipPropertyConstraint( 5, 6 ) ),
                asSet( cache.constraintsForRelationshipType( 5 ) ) );

        assertEquals(
                asSet( new MandatoryRelationshipPropertyConstraint( 5, 6 ) ),
                asSet( cache.constraintsForRelationshipTypeAndProperty( 5, 6 ) ) );
    }

    @Test
    public void should_remove_constraints()
    {
        // GIVEN
        SchemaCache cache = newSchemaCache();

        cache.addSchemaRule( uniquenessConstraintRule( 0l, 1, 2, 133l ) );
        cache.addSchemaRule( uniquenessConstraintRule( 1l, 3, 4, 133l ) );

        // WHEN
        cache.removeSchemaRule( 0l );

        // THEN
        assertEquals(
                asSet( new UniquenessConstraint( 3, 4 ) ),
                asSet( cache.constraints() ) );

        assertEquals(
                asSet(),
                asSet( cache.constraintsForLabel( 1 ) ) );

        assertEquals(
                asSet(),
                asSet( cache.constraintsForLabelAndProperty( 1, 2 ) ) );
    }

    @Test
    public void adding_constraints_should_be_idempotent() throws Exception
    {
        // given
        SchemaCache cache = newSchemaCache();

        cache.addSchemaRule( uniquenessConstraintRule( 0l, 1, 2, 133l ) );

        // when
        cache.addSchemaRule( uniquenessConstraintRule( 0l, 1, 2, 133l ) );

        // then
        assertEquals(
                asList( new UniquenessConstraint( 1, 2 ) ),
                IteratorUtil.asList( cache.constraints() ) );
    }

    @Test
    public void shouldResolveIndexDescriptor() throws Exception
    {
        // Given
        SchemaCache cache = newSchemaCache();

        cache.addSchemaRule( newIndexRule( 1l, 1, 2 ) );
        cache.addSchemaRule( newIndexRule( 2l, 1, 3 ) );
        cache.addSchemaRule( newIndexRule( 3l, 2, 2 ) );

        // When
        IndexDescriptor descriptor = cache.indexDescriptor( 1, 3 );

        // Then
        assertEquals( 1, descriptor.getLabelId() );
        assertEquals( 3, descriptor.getPropertyKeyId() );
    }

    @Test
    public void shouldReturnNullWhenNoIndexExists()
    {
        // Given
        SchemaCache schemaCache = newSchemaCache();

        // When
        IndexDescriptor indexDescriptor = schemaCache.indexDescriptor( 1, 1 );

        // Then
        assertNull( indexDescriptor );
    }

    @Test
    public void shouldListConstraintsForLabel()
    {
        // Given
        UniquePropertyConstraintRule rule1 = uniquenessConstraintRule( 0, 1, 1, 0 );
        UniquePropertyConstraintRule rule2 = uniquenessConstraintRule( 1, 2, 1, 0 );
        MandatoryNodePropertyConstraintRule rule3 = mandatoryNodePropertyConstraintRule( 2, 1, 2 );

        SchemaCache cache = newSchemaCache( rule1, rule2, rule3 );

        // When
        Set<NodePropertyConstraint> listed = asSet( cache.constraintsForLabel( 1 ) );

        // Then
        Set<NodePropertyConstraint> expected = asSet( rule1.toConstraint(), rule3.toConstraint() );
        assertEquals( expected, listed );
    }

    @Test
    public void shouldListConstraintsForLabelAndProperty()
    {
        // Given
        UniquePropertyConstraintRule rule1 = uniquenessConstraintRule( 0, 1, 1, 0 );
        UniquePropertyConstraintRule rule2 = uniquenessConstraintRule( 1, 2, 1, 0 );
        MandatoryNodePropertyConstraintRule rule3 = mandatoryNodePropertyConstraintRule( 2, 1, 2 );

        SchemaCache cache = newSchemaCache( rule1, rule2, rule3 );

        // When
        Set<NodePropertyConstraint> listed = asSet( cache.constraintsForLabelAndProperty( 1, 2 ) );

        // Then
        assertEquals( singleton( rule3.toConstraint() ), listed );
    }

    @Test
    public void shouldListConstraintsForRelationshipType()
    {
        // Given
        MandatoryRelationshipPropertyConstraintRule rule1 = mandatoryRelPropertyConstraintRule( 0, 1, 1 );
        MandatoryRelationshipPropertyConstraintRule rule2 = mandatoryRelPropertyConstraintRule( 0, 2, 1 );
        MandatoryRelationshipPropertyConstraintRule rule3 = mandatoryRelPropertyConstraintRule( 0, 1, 2 );

        SchemaCache cache = newSchemaCache( rule1, rule2, rule3 );

        // When
        Set<RelationshipPropertyConstraint> listed = asSet( cache.constraintsForRelationshipType( 1 ) );

        // Then
        Set<RelationshipPropertyConstraint> expected = asSet( rule1.toConstraint(), rule3.toConstraint() );
        assertEquals( expected, listed );
    }

    @Test
    public void shouldListConstraintsForRelationshipTypeAndProperty()
    {
        // Given
        MandatoryRelationshipPropertyConstraintRule rule1 = mandatoryRelPropertyConstraintRule( 0, 1, 1 );
        MandatoryRelationshipPropertyConstraintRule rule2 = mandatoryRelPropertyConstraintRule( 0, 2, 1 );
        MandatoryRelationshipPropertyConstraintRule rule3 = mandatoryRelPropertyConstraintRule( 0, 1, 2 );

        SchemaCache cache = newSchemaCache( rule1, rule2, rule3 );

        // When
        Set<RelationshipPropertyConstraint> listed = asSet( cache.constraintsForRelationshipTypeAndProperty( 2, 1 ) );

        // Then
        assertEquals( singleton( rule2.toConstraint() ), listed );
    }

    private IndexRule newIndexRule( long id, int label, int propertyKey )
    {
        return IndexRule.indexRule( id, label, propertyKey, PROVIDER_DESCRIPTOR );
    }

    private static SchemaCache newSchemaCache( SchemaRule... rules )
    {
        return new SchemaCache( (rules == null || rules.length == 0)
                                ? Collections.<SchemaRule>emptyList() : Arrays.asList( rules ) );
    }
}


File: community/kernel/src/test/java/org/neo4j/kernel/impl/store/SchemaStorageTest.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.kernel.impl.store;

import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;

import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.TimeUnit;

import org.neo4j.function.Functions;
import org.neo4j.function.Predicates;
import org.neo4j.graphdb.DependencyResolver;
import org.neo4j.graphdb.Transaction;
import org.neo4j.kernel.api.ReadOperations;
import org.neo4j.kernel.api.Statement;
import org.neo4j.kernel.api.exceptions.schema.SchemaRuleNotFoundException;
import org.neo4j.kernel.impl.core.ThreadToStatementContextBridge;
import org.neo4j.kernel.impl.store.SchemaStorage.IndexRuleKind;
import org.neo4j.kernel.impl.store.record.IndexRule;
import org.neo4j.kernel.impl.store.record.SchemaRule;
import org.neo4j.test.EmbeddedDatabaseRule;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.neo4j.graphdb.DynamicLabel.label;
import static org.neo4j.graphdb.DynamicRelationshipType.withName;
import static org.neo4j.helpers.collection.IteratorUtil.asSet;
import static org.neo4j.kernel.impl.api.index.inmemory.InMemoryIndexProviderFactory.PROVIDER_DESCRIPTOR;
import static org.neo4j.kernel.impl.store.MandatoryNodePropertyConstraintRule.mandatoryNodePropertyConstraintRule;
import static org.neo4j.kernel.impl.store.MandatoryRelationshipPropertyConstraintRule.mandatoryRelPropertyConstraintRule;
import static org.neo4j.kernel.impl.store.UniquePropertyConstraintRule.uniquenessConstraintRule;

public class SchemaStorageTest
{
    private static final String LABEL1 = "Label1";
    private static final String LABEL2 = "Label2";
    private static final String TYPE1 = "Type1";
    private static final String TYPE2 = "Type2";
    private static final String PROP1 = "prop1";
    private static final String PROP2 = "prop2";

    @Rule
    public final EmbeddedDatabaseRule db = new EmbeddedDatabaseRule();

    private SchemaStorage storage;

    @Before
    public void initStorage() throws Exception
    {
        storage = new SchemaStorage( dependencyResolver().resolveDependency( NeoStore.class ).getSchemaStore() );
    }

    @Test
    public void shouldReturnIndexRuleForLabelAndProperty()
    {
        // Given
        createIndex( LABEL1, PROP1 );
        createIndex( LABEL1, PROP2 );
        createIndex( LABEL2, PROP1 );

        // When
        IndexRule rule = storage.indexRule( labelId( LABEL1 ), propId( PROP1 ) );

        // Then
        assertNotNull( rule );
        assertEquals( labelId( LABEL1 ), rule.getLabel() );
        assertEquals( propId( PROP1 ), rule.getPropertyKey() );
        assertEquals( SchemaRule.Kind.INDEX_RULE, rule.getKind() );
    }

    @Test
    public void shouldReturnNullIfIndexRuleForLabelAndPropertyDoesNotExist()
    {
        // Given
        createIndex( LABEL1, PROP1 );

        // When
        IndexRule rule = storage.indexRule( labelId( LABEL1 ), propId( PROP2 ) );

        // Then
        assertNull( rule );
    }

    @Test
    public void shouldListIndexRulesForLabelPropertyAndKind()
    {
        // Given
        createUniquenessConstraint( LABEL1, PROP1 );
        createIndex( LABEL1, PROP2 );

        // When
        IndexRule rule = storage.indexRule( labelId( LABEL1 ), propId( PROP1 ), IndexRuleKind.CONSTRAINT );

        // Then
        assertNotNull( rule );
        assertEquals( labelId( LABEL1 ), rule.getLabel() );
        assertEquals( propId( PROP1 ), rule.getPropertyKey() );
        assertEquals( SchemaRule.Kind.CONSTRAINT_INDEX_RULE, rule.getKind() );
    }

    @Test
    public void shouldListAllIndexRules()
    {
        // Given
        createIndex( LABEL1, PROP1 );
        createIndex( LABEL1, PROP2 );
        createUniquenessConstraint( LABEL2, PROP1 );

        // When
        Set<IndexRule> listedRules = asSet( storage.allIndexRules() );

        // Then
        Set<IndexRule> expectedRules = new HashSet<>();
        expectedRules.add( new IndexRule( 0, labelId( LABEL1 ), propId( PROP1 ), PROVIDER_DESCRIPTOR, null ) );
        expectedRules.add( new IndexRule( 1, labelId( LABEL1 ), propId( PROP2 ), PROVIDER_DESCRIPTOR, null ) );
        expectedRules.add( new IndexRule( 2, labelId( LABEL2 ), propId( PROP1 ), PROVIDER_DESCRIPTOR, 0L ) );

        assertEquals( expectedRules, listedRules );
    }

    @Test
    public void shouldListAllSchemaRulesForNodes()
    {
        // Given
        createIndex( LABEL2, PROP1 );
        createUniquenessConstraint( LABEL1, PROP1 );
        createMandatoryNodePropertyConstraint( LABEL1, PROP1 );
        createMandatoryRelPropertyConstraint( LABEL1, PROP1 );

        // When
        Set<NodePropertyConstraintRule> listedRules = asSet( storage.schemaRulesForNodes(
                Functions.<NodePropertyConstraintRule>identity(), NodePropertyConstraintRule.class, labelId( LABEL1 ),
                Predicates.<NodePropertyConstraintRule>alwaysTrue() ) );

        // Then
        Set<NodePropertyConstraintRule> expectedRules = new HashSet<>();
        expectedRules.add( uniquenessConstraintRule( 1, labelId( LABEL1 ), propId( PROP1 ), 0 ) );
        expectedRules.add( mandatoryNodePropertyConstraintRule( 1, labelId( LABEL1 ), propId( PROP1 ) ) );

        assertEquals( expectedRules, listedRules );
    }

    @Test
    public void shouldListAllSchemaRulesForRelationships()
    {
        // Given
        createIndex( LABEL1, PROP1 );
        createMandatoryRelPropertyConstraint( TYPE1, PROP1 );
        createMandatoryRelPropertyConstraint( TYPE2, PROP1 );
        createMandatoryRelPropertyConstraint( TYPE1, PROP2 );

        // When
        Set<RelationshipPropertyConstraintRule> listedRules = asSet( storage.schemaRulesForRelationships(
                Functions.<RelationshipPropertyConstraintRule>identity(), RelationshipPropertyConstraintRule.class,
                labelId( LABEL1 ), Predicates.<RelationshipPropertyConstraintRule>alwaysTrue() ) );

        // Then
        Set<RelationshipPropertyConstraintRule> expectedRules = new HashSet<>();
        expectedRules.add( mandatoryRelPropertyConstraintRule( 0, typeId( TYPE1 ), propId( PROP1 ) ) );
        expectedRules.add( mandatoryRelPropertyConstraintRule( 1, typeId( TYPE1 ), propId( PROP2 ) ) );

        assertEquals( expectedRules, listedRules );
    }

    @Test
    public void shouldListSchemaRulesByClass()
    {
        // Given
        createUniquenessConstraint( LABEL1, PROP1 );
        createMandatoryNodePropertyConstraint( LABEL1, PROP1 );
        createMandatoryRelPropertyConstraint( TYPE1, PROP1 );

        // When
        Set<RelationshipPropertyConstraintRule> listedRules = asSet(
                storage.schemaRules( RelationshipPropertyConstraintRule.class ) );

        // Then
        Set<RelationshipPropertyConstraintRule> expectedRules = new HashSet<>();
        expectedRules.add( mandatoryRelPropertyConstraintRule( 0, typeId( TYPE1 ), propId( PROP1 ) ) );

        assertEquals( expectedRules, listedRules );
    }

    @Test
    public void shouldReturnCorrectUniquenessRuleForLabelAndProperty() throws SchemaRuleNotFoundException
    {
        // Given
        createUniquenessConstraint( LABEL1, PROP1 );
        createUniquenessConstraint( LABEL2, PROP1 );

        // When
        UniquePropertyConstraintRule rule = storage.uniquenessConstraint( labelId( LABEL1 ), propId( PROP1 ) );

        // Then
        assertNotNull( rule );
        assertEquals( labelId( LABEL1 ), rule.getLabel() );
        assertEquals( propId( PROP1 ), rule.getPropertyKey() );
        assertEquals( SchemaRule.Kind.UNIQUENESS_CONSTRAINT, rule.getKind() );
    }

    @Test
    public void shouldReturnCorrectMandatoryRuleForLabelAndProperty() throws SchemaRuleNotFoundException
    {
        // Given
        createMandatoryNodePropertyConstraint( LABEL1, PROP1 );
        createMandatoryNodePropertyConstraint( LABEL2, PROP1 );

        // When
        MandatoryNodePropertyConstraintRule rule =
                storage.mandatoryNodePropertyConstraint( labelId( LABEL1 ), propId( PROP1 ) );

        // Then
        assertNotNull( rule );
        assertEquals( labelId( LABEL1 ), rule.getLabel() );
        assertEquals( propId( PROP1 ), rule.getPropertyKey() );
        assertEquals( SchemaRule.Kind.MANDATORY_NODE_PROPERTY_CONSTRAINT, rule.getKind() );
    }

    @Test
    public void shouldReturnCorrectMandatoryRuleForRelTypeAndProperty() throws SchemaRuleNotFoundException
    {
        // Given
        createMandatoryRelPropertyConstraint( TYPE1, PROP1 );
        createMandatoryRelPropertyConstraint( TYPE2, PROP1 );

        // When
        MandatoryRelationshipPropertyConstraintRule rule =
                storage.mandatoryRelationshipPropertyConstraint( typeId( TYPE1 ), propId( PROP1 ) );

        // Then
        assertNotNull( rule );
        assertEquals( typeId( TYPE1 ), rule.getRelationshipType() );
        assertEquals( propId( PROP1 ), rule.getPropertyKey() );
        assertEquals( SchemaRule.Kind.MANDATORY_RELATIONSHIP_PROPERTY_CONSTRAINT, rule.getKind() );
    }

    private void createIndex( String labelName, String propertyName )
    {
        try ( Transaction tx = db.beginTx() )
        {
            db.schema().indexFor( label( labelName ) ).on( propertyName ).create();
            tx.success();
        }
        awaitIndexes();
    }

    private void createUniquenessConstraint( String labelName, String propertyName )
    {
        try ( Transaction tx = db.beginTx() )
        {
            db.schema().constraintFor( label( labelName ) ).assertPropertyIsUnique( propertyName ).create();
            tx.success();
        }
        awaitIndexes();
    }

    private void createMandatoryNodePropertyConstraint( String labelName, String propertyName )
    {
        try ( Transaction tx = db.beginTx() )
        {
            db.schema().constraintFor( label( labelName ) ).assertPropertyExists( propertyName ).create();
            tx.success();
        }
        awaitIndexes();
    }

    private void createMandatoryRelPropertyConstraint( String typeName, String propertyName )
    {
        try ( Transaction tx = db.beginTx() )
        {
            db.schema().constraintFor( withName( typeName ) ).assertPropertyExists( propertyName ).create();
            tx.success();
        }
        awaitIndexes();
    }

    private void awaitIndexes()
    {
        try ( Transaction tx = db.beginTx() )
        {
            db.schema().awaitIndexesOnline( 10, TimeUnit.SECONDS );
            tx.success();
        }
    }

    private int labelId( String labelName )
    {
        try ( Transaction ignore = db.beginTx() )
        {
            return readOps().labelGetForName( labelName );
        }
    }

    private int propId( String propName )
    {
        try ( Transaction ignore = db.beginTx() )
        {
            return readOps().propertyKeyGetForName( propName );
        }
    }

    private int typeId( String typeName )
    {
        try ( Transaction ignore = db.beginTx() )
        {
            return readOps().relationshipTypeGetForName( typeName );
        }
    }

    private ReadOperations readOps()
    {
        DependencyResolver dependencyResolver = dependencyResolver();
        Statement statement = dependencyResolver.resolveDependency( ThreadToStatementContextBridge.class ).get();
        return statement.readOperations();
    }

    private DependencyResolver dependencyResolver()
    {
        return db.getGraphDatabaseAPI().getDependencyResolver();
    }
}


File: community/kernel/src/test/java/org/neo4j/kernel/impl/transaction/command/NeoTransactionStoreApplierTest.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.kernel.impl.transaction.command;

import org.junit.Before;
import org.junit.Test;
import org.mockito.Matchers;

import java.io.IOException;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;

import org.neo4j.concurrent.WorkSync;
import org.neo4j.helpers.Provider;
import org.neo4j.kernel.api.exceptions.index.IndexActivationFailedKernelException;
import org.neo4j.kernel.api.exceptions.index.IndexNotFoundKernelException;
import org.neo4j.kernel.api.exceptions.index.IndexPopulationFailedKernelException;
import org.neo4j.kernel.api.index.SchemaIndexProvider;
import org.neo4j.kernel.impl.api.TransactionApplicationMode;
import org.neo4j.kernel.impl.api.index.IndexingService;
import org.neo4j.kernel.impl.api.index.ValidatedIndexUpdates;
import org.neo4j.kernel.impl.core.CacheAccessBackDoor;
import org.neo4j.kernel.impl.core.Token;
import org.neo4j.kernel.impl.locking.LockGroup;
import org.neo4j.kernel.impl.locking.LockService;
import org.neo4j.kernel.impl.store.DynamicArrayStore;
import org.neo4j.kernel.impl.store.LabelTokenStore;
import org.neo4j.kernel.impl.store.NeoStore;
import org.neo4j.kernel.impl.store.NodeStore;
import org.neo4j.kernel.impl.store.PropertyKeyTokenStore;
import org.neo4j.kernel.impl.store.PropertyStore;
import org.neo4j.kernel.impl.store.RelationshipGroupStore;
import org.neo4j.kernel.impl.store.RelationshipStore;
import org.neo4j.kernel.impl.store.RelationshipTypeTokenStore;
import org.neo4j.kernel.impl.store.SchemaStore;
import org.neo4j.kernel.impl.store.UniquePropertyConstraintRule;
import org.neo4j.kernel.impl.store.record.DynamicRecord;
import org.neo4j.kernel.impl.store.record.IndexRule;
import org.neo4j.kernel.impl.store.record.LabelTokenRecord;
import org.neo4j.kernel.impl.store.record.NeoStoreRecord;
import org.neo4j.kernel.impl.store.record.NodeRecord;
import org.neo4j.kernel.impl.store.record.PropertyKeyTokenRecord;
import org.neo4j.kernel.impl.store.record.PropertyRecord;
import org.neo4j.kernel.impl.store.record.RelationshipGroupRecord;
import org.neo4j.kernel.impl.store.record.RelationshipRecord;
import org.neo4j.kernel.impl.store.record.RelationshipTypeTokenRecord;
import org.neo4j.kernel.impl.transaction.command.Command.LabelTokenCommand;
import org.neo4j.kernel.impl.transaction.command.Command.PropertyKeyTokenCommand;
import org.neo4j.kernel.impl.transaction.command.Command.RelationshipTypeTokenCommand;
import org.neo4j.unsafe.batchinsert.LabelScanWriter;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;
import static org.mockito.Matchers.anyLong;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

public class NeoTransactionStoreApplierTest
{
    private final NeoStore neoStore = mock( NeoStore.class );
    private final IndexingService indexingService = mock( IndexingService.class );
    @SuppressWarnings( "unchecked" )
    private final Provider<LabelScanWriter> labelScanStore = mock( Provider.class );
    private final CacheAccessBackDoor cacheAccess = mock( CacheAccessBackDoor.class );
    private final LockService lockService = mock( LockService.class );

    private final NodeStore nodeStore = mock( NodeStore.class );
    private final RelationshipStore relationshipStore = mock( RelationshipStore.class );
    private final PropertyStore propertyStore = mock( PropertyStore.class );
    private final RelationshipGroupStore relationshipGroupStore = mock( RelationshipGroupStore.class );
    private final RelationshipTypeTokenStore relationshipTypeTokenStore = mock( RelationshipTypeTokenStore.class );
    private final LabelTokenStore labelTokenStore = mock( LabelTokenStore.class );
    private final PropertyKeyTokenStore propertyKeyTokenStore = mock( PropertyKeyTokenStore.class );
    private final SchemaStore schemaStore = mock( SchemaStore.class );
    private final DynamicArrayStore dynamicLabelStore = mock( DynamicArrayStore.class );

    private final int transactionId = 55555;
    private final DynamicRecord one = DynamicRecord.dynamicRecord( 1, true );
    private final DynamicRecord two = DynamicRecord.dynamicRecord( 2, true );
    private final DynamicRecord three = DynamicRecord.dynamicRecord( 3, true );
    private final WorkSync<Provider<LabelScanWriter>,IndexTransactionApplier.LabelUpdateWork>
            labelScanStoreSynchronizer = new WorkSync<>( labelScanStore );

    @Before
    public void setup()
    {
        when( neoStore.getNodeStore() ).thenReturn( nodeStore );
        when( neoStore.getRelationshipStore() ).thenReturn( relationshipStore );
        when( neoStore.getPropertyStore() ).thenReturn( propertyStore );
        when( neoStore.getRelationshipGroupStore() ).thenReturn( relationshipGroupStore );
        when( neoStore.getRelationshipTypeTokenStore() ).thenReturn( relationshipTypeTokenStore );
        when( neoStore.getLabelTokenStore() ).thenReturn( labelTokenStore );
        when( neoStore.getPropertyKeyTokenStore() ).thenReturn( propertyKeyTokenStore );
        when( neoStore.getSchemaStore() ).thenReturn( schemaStore );
        when( nodeStore.getDynamicLabelStore() ).thenReturn( dynamicLabelStore );
        when( lockService.acquireNodeLock( anyLong(), Matchers.<LockService.LockType>any() ) )
                .thenReturn( LockService.NO_LOCK );
    }

    // NODE COMMAND

    @Test
    public void shouldApplyNodeCommandToTheStore() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( false );
        final NodeRecord before = new NodeRecord( 11 );
        before.setLabelField( 42, Arrays.asList( one, two ) );
        final NodeRecord after = new NodeRecord( 12 );
        after.setInUse( true );
        after.setLabelField( 42, Arrays.asList( one, two, three ) );
        final Command.NodeCommand command = new Command.NodeCommand().init( before, after );

        // when
        final boolean result = applier.visitNodeCommand( command );

        // then
        assertFalse( result );

        verify( lockService, times( 1 ) ).acquireNodeLock( command.getKey(), LockService.LockType.WRITE_LOCK );
        verify( nodeStore, times( 1 ) ).updateRecord( after );
        verify( nodeStore, times( 1 ) ).updateDynamicLabelRecords( Arrays.asList( one, two, three ) );
    }

    private NeoCommandHandler newApplier( boolean recovery )
    {
        NeoCommandHandler applier = new NeoStoreTransactionApplier( neoStore, cacheAccess, lockService,
                new LockGroup(), transactionId );
        if ( recovery )
        {
            applier = new HighIdTransactionApplier( applier, neoStore );
            applier = new CacheInvalidationTransactionApplier( applier, neoStore, cacheAccess );
        }
        return applier;
    }

    @Test
    public void shouldApplyNodeCommandToTheStoreAndInvalidateTheCache() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( false );
        final NodeRecord before = new NodeRecord( 11 );
        before.setLabelField( 42, Arrays.asList( one, two ) );
        final NodeRecord after = new NodeRecord( 12 );
        after.setInUse( false );
        after.setLabelField( 42, Arrays.asList( one, two, three ) );
        final Command.NodeCommand command = new Command.NodeCommand().init( before, after );

        // when
        final boolean result = applier.visitNodeCommand( command );

        // then
        assertFalse( result );

        verify( lockService, times( 1 ) ).acquireNodeLock( command.getKey(), LockService.LockType.WRITE_LOCK );
        verify( nodeStore, times( 1 ) ).updateRecord( after );
        verify( nodeStore, times( 1 ) ).updateDynamicLabelRecords( Arrays.asList( one, two, three ) );
    }

    @Test
    public void shouldApplyNodeCommandToTheStoreInRecoveryMode() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( true );
        final NodeRecord before = new NodeRecord( 11 );
        before.setLabelField( 42, Arrays.asList( one, two ) );
        final NodeRecord after = new NodeRecord( 12 );
        after.setInUse( true );
        after.setLabelField( 42, Arrays.asList( one, two, three ) );
        final Command.NodeCommand command = new Command.NodeCommand().init( before, after );

        // when
        final boolean result = applier.visitNodeCommand( command );
        applyAndClose( applier );

        // then
        assertFalse( result );

        verify( lockService, times( 1 ) ).acquireNodeLock( command.getKey(), LockService.LockType.WRITE_LOCK );
        verify( nodeStore, times( 1 ) ).setHighestPossibleIdInUse( after.getId() );
        verify( nodeStore, times( 1 ) ).updateRecord( after );
        verify( dynamicLabelStore, times( 1 ) ).setHighestPossibleIdInUse( three.getId() );
        verify( nodeStore, times( 1 ) ).updateDynamicLabelRecords( Arrays.asList( one, two, three ) );
    }

    @Test
    public void shouldInvalidateTheCacheWhenTheNodeBecomesDense() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( false );
        final NodeRecord before = new NodeRecord( 11 );
        before.setLabelField( 42, Arrays.asList( one ) );
        before.setInUse( true );
        before.setDense( false );
        final NodeRecord after = new NodeRecord( 12 );
        after.setInUse( true );
        after.setDense( true );
        after.setLabelField( 42, Arrays.asList( one, two, three ) );
        final Command.NodeCommand command = new Command.NodeCommand().init( before, after );

        // when
        final boolean result = applier.visitNodeCommand( command );

        // then
        assertFalse( result );

        verify( lockService, times( 1 ) ).acquireNodeLock( command.getKey(), LockService.LockType.WRITE_LOCK );
        verify( nodeStore, times( 1 ) ).updateRecord( after );
        verify( nodeStore, times( 1 ) ).updateDynamicLabelRecords( Arrays.asList( one, two, three ) );
    }

    // RELATIONSHIP COMMAND

    @Test
    public void shouldApplyRelationshipCommandToTheStore() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( false );
        final RelationshipRecord record = new RelationshipRecord( 12, 3, 4, 5 );
        record.setInUse( true );

        // when
        final boolean result = applier.visitRelationshipCommand( new Command.RelationshipCommand().init( record ) );

        // then
        assertFalse( result );

        verify( relationshipStore, times( 1 ) ).updateRecord( record );
    }

    @Test
    public void shouldApplyRelationshipCommandToTheStoreAndInvalidateTheCache() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( false );
        final RelationshipRecord record = new RelationshipRecord( 12, 3, 4, 5 );
        record.setInUse( false );

        // when
        final boolean result = applier.visitRelationshipCommand( new Command.RelationshipCommand().init( record ) );

        // then
        assertFalse( result );

        verify( relationshipStore, times( 1 ) ).updateRecord( record );
    }

    @Test
    public void shouldApplyRelationshipCommandToTheStoreInRecovery() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( true );
        final RelationshipRecord record = new RelationshipRecord( 12, 3, 4, 5 );
        record.setInUse( true );

        // when
        final boolean result = applier.visitRelationshipCommand( new Command.RelationshipCommand().init( record ) );
        applyAndClose( applier );

        // then
        assertFalse( result );

        verify( relationshipStore, times( 1 ) ).setHighestPossibleIdInUse( record.getId() );
        verify( relationshipStore, times( 1 ) ).updateRecord( record );
    }

    // PROPERTY COMMAND

    @Test
    public void shouldApplyNodePropertyCommandToTheStore() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( false );
        final PropertyRecord before = new PropertyRecord( 11 );
        final PropertyRecord after = new PropertyRecord( 12 );
        after.setNodeId( 42 );

        // when
        final boolean result = applier.visitPropertyCommand( new Command.PropertyCommand().init( before, after ) );

        // then
        assertFalse( result );

        verify( lockService, times( 1 ) ).acquireNodeLock( 42, LockService.LockType.WRITE_LOCK );
        verify( propertyStore, times( 1 ) ).updateRecord( after );
    }

    @Test
    public void shouldApplyNodePropertyCommandToTheStoreInRecovery() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( true );
        final PropertyRecord before = new PropertyRecord( 11 );
        final PropertyRecord after = new PropertyRecord( 12 );
        after.setNodeId( 42 );

        // when
        final boolean result = applier.visitPropertyCommand( new Command.PropertyCommand().init( before, after ) );
        applyAndClose( applier );

        // then
        assertFalse( result );

        verify( lockService, times( 1 ) ).acquireNodeLock( 42, LockService.LockType.WRITE_LOCK );
        verify( propertyStore, times( 1 ) ).setHighestPossibleIdInUse( after.getId() );
        verify( propertyStore, times( 1 ) ).updateRecord( after );
    }

    @Test
    public void shouldApplyRelPropertyCommandToTheStore() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( false );
        final PropertyRecord before = new PropertyRecord( 11 );
        final PropertyRecord after = new PropertyRecord( 12 );
        after.setRelId( 42 );

        // when
        final boolean result = applier.visitPropertyCommand( new Command.PropertyCommand().init( before, after ) );

        // then
        assertFalse( result );

        verify( propertyStore, times( 1 ) ).updateRecord( after );
    }

    @Test
    public void shouldApplyRelPropertyCommandToTheStoreInRecovery() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( true );
        final PropertyRecord before = new PropertyRecord( 11 );
        final PropertyRecord after = new PropertyRecord( 12 );
        after.setRelId( 42 );

        // when
        final boolean result = applier.visitPropertyCommand( new Command.PropertyCommand().init( before, after ) );
        applyAndClose( applier );

        // then
        assertFalse( result );

        verify( propertyStore, times( 1 ) ).setHighestPossibleIdInUse( 12 );
        verify( propertyStore, times( 1 ) ).updateRecord( after );
    }

    private void applyAndClose( NeoCommandHandler... appliers )
    {
        for ( NeoCommandHandler applier : appliers )
        {
            applier.apply();
        }
        for ( NeoCommandHandler applier : appliers )
        {
            applier.close();
        }
    }

    // RELATIONSHIP GROUP COMMAND

    @Test
    public void shouldApplyRelationshipGroupCommandToTheStore() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( false );
        // when
        final RelationshipGroupRecord record = new RelationshipGroupRecord( 42, 1 );
        final boolean result = applier.visitRelationshipGroupCommand(
                new Command.RelationshipGroupCommand().init( record )
        );

        // then
        assertFalse( result );

        verify( relationshipGroupStore, times( 1 ) ).updateRecord( record );
    }

    @Test
    public void shouldApplyRelationshipGroupCommandToTheStoreInRecovery() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( true );
        // when
        final RelationshipGroupRecord record = new RelationshipGroupRecord( 42, 1 );
        final boolean result = applier.visitRelationshipGroupCommand(
                new Command.RelationshipGroupCommand().init( record ) );
        applyAndClose( applier );

        // then
        assertFalse( result );

        verify( relationshipGroupStore, times( 1 ) ).setHighestPossibleIdInUse( record.getId() );
        verify( relationshipGroupStore, times( 1 ) ).updateRecord( record );
    }

    // RELATIONSHIP TYPE TOKEN COMMAND

    @Test
    public void shouldApplyRelationshipTypeTokenCommandToTheStore() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( false );
        final RelationshipTypeTokenRecord record = new RelationshipTypeTokenRecord( 42 );

        // when
        final boolean result = applier.visitRelationshipTypeTokenCommand(
                (RelationshipTypeTokenCommand) new Command.RelationshipTypeTokenCommand().init( record ) );

        // then
        assertFalse( result );

        verify( relationshipTypeTokenStore, times( 1 ) ).updateRecord( record );
    }

    @Test
    public void shouldApplyRelationshipTypeTokenCommandToTheStoreInRecovery() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( true );
        final RelationshipTypeTokenRecord record = new RelationshipTypeTokenRecord( 42 );
        final Command.RelationshipTypeTokenCommand command =
                (RelationshipTypeTokenCommand) new Command.RelationshipTypeTokenCommand().init( record );
        final Token token = new Token( "token", 21 );
        when( relationshipTypeTokenStore.getToken( (int) command.getKey() ) ).thenReturn( token );

        // when
        final boolean result = applier.visitRelationshipTypeTokenCommand( command );
        applyAndClose( applier );

        // then
        assertFalse( result );

        verify( relationshipTypeTokenStore, times( 1 ) ).setHighestPossibleIdInUse( record.getId() );
        verify( relationshipTypeTokenStore, times( 1 ) ).updateRecord( record );
        verify( cacheAccess, times( 1 ) ).addRelationshipTypeToken( token );
    }

    // LABEL TOKEN COMMAND

    @Test
    public void shouldApplyLabelTokenCommandToTheStore() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( false );
        final LabelTokenRecord record = new LabelTokenRecord( 42 );

        // when
        final boolean result = applier.visitLabelTokenCommand(
                (LabelTokenCommand) new Command.LabelTokenCommand().init( record ) );

        // then
        assertFalse( result );

        verify( labelTokenStore, times( 1 ) ).updateRecord( record );
    }

    @Test
    public void shouldApplyLabelTokenCommandToTheStoreInRecovery() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( true );
        final LabelTokenRecord record = new LabelTokenRecord( 42 );
        final Command.LabelTokenCommand command = (LabelTokenCommand) new Command.LabelTokenCommand().init( record );
        final Token token = new Token( "token", 21 );
        when( labelTokenStore.getToken( (int) command.getKey() ) ).thenReturn( token );

        // when
        final boolean result = applier.visitLabelTokenCommand( command );
        applyAndClose( applier );

        // then
        assertFalse( result );

        verify( labelTokenStore, times( 1 ) ).setHighestPossibleIdInUse( record.getId() );
        verify( labelTokenStore, times( 1 ) ).updateRecord( record );
        verify( cacheAccess, times( 1 ) ).addLabelToken( token );
    }

    // PROPERTY KEY TOKEN COMMAND

    @Test
    public void shouldApplyPropertyKeyTokenCommandToTheStore() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( false );
        final PropertyKeyTokenRecord record = new PropertyKeyTokenRecord( 42 );

        // when
        final boolean result = applier.visitPropertyKeyTokenCommand(
                (PropertyKeyTokenCommand) new Command.PropertyKeyTokenCommand().init( record ) );

        // then
        assertFalse( result );

        verify( propertyKeyTokenStore, times( 1 ) ).updateRecord( record );
    }

    @Test
    public void shouldApplyPropertyKeyTokenCommandToTheStoreInRecovery() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( true );
        final PropertyKeyTokenRecord record = new PropertyKeyTokenRecord( 42 );
        final Command.PropertyKeyTokenCommand command =
                (PropertyKeyTokenCommand) new Command.PropertyKeyTokenCommand().init( record );
        final Token token = new Token( "token", 21 );
        when( propertyKeyTokenStore.getToken( (int) command.getKey() ) ).thenReturn( token );

        // when
        final boolean result = applier.visitPropertyKeyTokenCommand( command );
        applyAndClose( applier );

        // then
        assertFalse( result );

        verify( propertyKeyTokenStore, times( 1 ) ).setHighestPossibleIdInUse( record.getId() );
        verify( propertyKeyTokenStore, times( 1 ) ).updateRecord( record );
        verify( cacheAccess, times( 1 ) ).addPropertyKeyToken( token );
    }

    // SCHEMA RULE COMMAND

    @Test
    public void shouldApplyCreateIndexRuleSchemaRuleCommandToTheStore() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( false );
        final NeoCommandHandler indexApplier = new IndexTransactionApplier( indexingService,
                ValidatedIndexUpdates.NONE, labelScanStoreSynchronizer );
        final DynamicRecord record = DynamicRecord.dynamicRecord( 21, true );
        record.setCreated();
        final Collection<DynamicRecord> recordsAfter = Arrays.asList( record );
        final IndexRule rule = IndexRule.indexRule( 0, 1, 2, new SchemaIndexProvider.Descriptor( "K", "X.Y" ) );
        final Command.SchemaRuleCommand command =
                new Command.SchemaRuleCommand().init( Collections.<DynamicRecord>emptyList(), recordsAfter, rule );

        // when
        final boolean result =
                applier.visitSchemaRuleCommand( command ) & indexApplier.visitSchemaRuleCommand( command );

        // then
        assertFalse( result );

        verify( schemaStore, times( 1 ) ).updateRecord( record );
        verify( indexingService, times( 1 ) ).createIndex( rule );
        verify( cacheAccess, times( 1 ) ).addSchemaRule( rule );
    }

    @Test
    public void shouldApplyCreateIndexRuleSchemaRuleCommandToTheStoreInRecovery() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( true );
        final NeoCommandHandler indexApplier = newIndexApplier( TransactionApplicationMode.EXTERNAL );
        final DynamicRecord record = DynamicRecord.dynamicRecord( 21, true );
        record.setCreated();
        final Collection<DynamicRecord> recordsAfter = Arrays.asList( record );
        final IndexRule rule = IndexRule.indexRule( 0, 1, 2, new SchemaIndexProvider.Descriptor( "K", "X.Y" ) );
        final Command.SchemaRuleCommand command =
                new Command.SchemaRuleCommand().init( Collections.<DynamicRecord>emptyList(), recordsAfter, rule );

        // when
        final boolean result = applier.visitSchemaRuleCommand( command ) &
                               indexApplier.visitSchemaRuleCommand( command );
        applyAndClose( applier, indexApplier );

        // then
        assertFalse( result );

        verify( schemaStore, times( 1 ) ).setHighestPossibleIdInUse( record.getId() );
        verify( schemaStore, times( 1 ) ).updateRecord( record );
        verify( indexingService, times( 1 ) ).createIndex( rule );
        verify( cacheAccess, times( 1 ) ).addSchemaRule( rule );
    }

    @Test
    public void shouldApplyUpdateIndexRuleSchemaRuleCommandToTheStore()
            throws IOException, IndexNotFoundKernelException,
            IndexPopulationFailedKernelException, IndexActivationFailedKernelException
    {
        // given
        final NeoCommandHandler applier = newApplier( false );
        final NeoCommandHandler indexApplier = newIndexApplier( TransactionApplicationMode.INTERNAL );
        final DynamicRecord record = DynamicRecord.dynamicRecord( 21, true );
        final Collection<DynamicRecord> recordsAfter = Arrays.asList( record );
        final IndexRule rule =
                IndexRule.constraintIndexRule( 0, 1, 2, new SchemaIndexProvider.Descriptor( "K", "X.Y" ), 42l );
        final Command.SchemaRuleCommand command =
                new Command.SchemaRuleCommand().init( Collections.<DynamicRecord>emptyList(), recordsAfter, rule );

        // when
        final boolean result = applier.visitSchemaRuleCommand( command ) &
                               indexApplier.visitSchemaRuleCommand( command );

        // then
        assertFalse( result );

        verify( schemaStore, times( 1 ) ).updateRecord( record );
        verify( indexingService, times( 1 ) ).activateIndex( rule.getId() );
        verify( cacheAccess, times( 1 ) ).addSchemaRule( rule );
    }

    @Test
    public void shouldApplyUpdateIndexRuleSchemaRuleCommandToTheStoreInRecovery()
            throws IOException, IndexNotFoundKernelException,
            IndexPopulationFailedKernelException, IndexActivationFailedKernelException
    {
        // given
        final NeoCommandHandler applier = newApplier( true );
        final NeoCommandHandler indexApplier = newIndexApplier( TransactionApplicationMode.EXTERNAL );
        final DynamicRecord record = DynamicRecord.dynamicRecord( 21, true );
        final Collection<DynamicRecord> recordsAfter = Arrays.asList( record );
        final IndexRule rule =
                IndexRule.constraintIndexRule( 0, 1, 2, new SchemaIndexProvider.Descriptor( "K", "X.Y" ), 42l );
        final Command.SchemaRuleCommand command =
                new Command.SchemaRuleCommand().init( Collections.<DynamicRecord>emptyList(), recordsAfter, rule );

        // when
        final boolean result =
                applier.visitSchemaRuleCommand( command ) & indexApplier.visitSchemaRuleCommand( command );
        applyAndClose( applier, indexApplier );

        // then
        assertFalse( result );

        verify( schemaStore, times( 1 ) ).setHighestPossibleIdInUse( record.getId() );
        verify( schemaStore, times( 1 ) ).updateRecord( record );
        verify( indexingService, times( 1 ) ).activateIndex( rule.getId() );
        verify( cacheAccess, times( 1 ) ).addSchemaRule( rule );
    }

    @Test
    public void shouldApplyUpdateIndexRuleSchemaRuleCommandToTheStoreThrowingIndexProblem()
            throws IOException, IndexNotFoundKernelException,
            IndexPopulationFailedKernelException, IndexActivationFailedKernelException
    {
        // given
        final NeoCommandHandler applier = newIndexApplier( TransactionApplicationMode.INTERNAL );
        doThrow( new IndexNotFoundKernelException( "" ) ).when( indexingService ).activateIndex( anyLong() );

        final DynamicRecord record = DynamicRecord.dynamicRecord( 21, true );
        final Collection<DynamicRecord> recordsAfter = Arrays.asList( record );
        final IndexRule rule =
                IndexRule.constraintIndexRule( 0, 1, 2, new SchemaIndexProvider.Descriptor( "K", "X.Y" ), 42l );
        final Command.SchemaRuleCommand command =
                new Command.SchemaRuleCommand().init( Collections.<DynamicRecord>emptyList(), recordsAfter, rule );

        // when
        try
        {
            applier.visitSchemaRuleCommand( command );
            fail( "should have thrown" );
        }
        catch ( RuntimeException e )
        {
            // then
            assertTrue( e.getCause() instanceof IndexNotFoundKernelException );
        }
    }

    @Test
    public void shouldApplyDeleteIndexRuleSchemaRuleCommandToTheStore()
            throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( false );
        final NeoCommandHandler indexApplier = newIndexApplier( TransactionApplicationMode.INTERNAL );
        final DynamicRecord record = DynamicRecord.dynamicRecord( 21, true );
        record.setInUse( false );
        final Collection<DynamicRecord> recordsAfter = Arrays.asList( record );
        final IndexRule rule = IndexRule.indexRule( 0, 1, 2, new SchemaIndexProvider.Descriptor( "K", "X.Y" ) );
        final Command.SchemaRuleCommand command =
                new Command.SchemaRuleCommand().init( Collections.<DynamicRecord>emptyList(), recordsAfter, rule );

        // when
        final boolean result =
                applier.visitSchemaRuleCommand( command ) & indexApplier.visitSchemaRuleCommand( command );

        // then
        assertFalse( result );

        verify( schemaStore, times( 1 ) ).updateRecord( record );
        verify( indexingService, times( 1 ) ).dropIndex( rule );
        verify( cacheAccess, times( 1 ) ).removeSchemaRuleFromCache( command.getKey() );
    }

    @Test
    public void shouldApplyDeleteIndexRuleSchemaRuleCommandToTheStoreInRecovery() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( true );
        final NeoCommandHandler indexApplier = newIndexApplier( TransactionApplicationMode.RECOVERY );
        final DynamicRecord record = DynamicRecord.dynamicRecord( 21, true );
        record.setInUse( false );
        final Collection<DynamicRecord> recordsAfter = Arrays.asList( record );
        final IndexRule rule = IndexRule.indexRule( 0, 1, 2, new SchemaIndexProvider.Descriptor( "K", "X.Y" ) );
        final Command.SchemaRuleCommand command =
                new Command.SchemaRuleCommand().init( Collections.<DynamicRecord>emptyList(), recordsAfter, rule );

        // when
        final boolean result =
                applier.visitSchemaRuleCommand( command ) & indexApplier.visitSchemaRuleCommand( command );
        applyAndClose( applier, indexApplier );

        // then
        assertFalse( result );

        verify( schemaStore, times( 1 ) ).setHighestPossibleIdInUse( record.getId() );
        verify( schemaStore, times( 1 ) ).updateRecord( record );
        verify( indexingService, times( 1 ) ).dropIndex( rule );
        verify( cacheAccess, times( 1 ) ).removeSchemaRuleFromCache( command.getKey() );
    }

    private NeoCommandHandler newIndexApplier( TransactionApplicationMode mode )
    {
        return new IndexTransactionApplier( indexingService, ValidatedIndexUpdates.NONE, labelScanStoreSynchronizer );
    }

    @Test
    public void shouldApplyCreateUniquenessConstraintRuleSchemaRuleCommandToTheStore() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( false );
        final DynamicRecord record = DynamicRecord.dynamicRecord( 21, true );
        record.setCreated();
        final Collection<DynamicRecord> recordsAfter = Arrays.asList( record );
        final UniquePropertyConstraintRule
                rule = UniquePropertyConstraintRule.uniquenessConstraintRule( 0l, 1, 2, 3l );
        final Command.SchemaRuleCommand command =
                new Command.SchemaRuleCommand().init( Collections.<DynamicRecord>emptyList(), recordsAfter, rule );

        // when
        final boolean result = applier.visitSchemaRuleCommand( command );

        // then
        assertFalse( result );

        verify( schemaStore, times( 1 ) ).updateRecord( record );
        verify( neoStore, times( 1 ) ).setLatestConstraintIntroducingTx( transactionId );
        verify( cacheAccess, times( 1 ) ).addSchemaRule( rule );
    }

    @Test
    public void shouldApplyCreateUniquenessConstraintRuleSchemaRuleCommandToTheStoreInRecovery() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( true );
        final DynamicRecord record = DynamicRecord.dynamicRecord( 21, true );
        record.setCreated();
        final Collection<DynamicRecord> recordsAfter = Arrays.asList( record );
        final UniquePropertyConstraintRule
                rule = UniquePropertyConstraintRule.uniquenessConstraintRule( 0l, 1, 2, 3l );
        final Command.SchemaRuleCommand command =
                new Command.SchemaRuleCommand().init( Collections.<DynamicRecord>emptyList(), recordsAfter, rule );

        // when
        final boolean result = applier.visitSchemaRuleCommand( command );
        applyAndClose( applier );

        // then
        assertFalse( result );

        verify( schemaStore, times( 1 ) ).setHighestPossibleIdInUse( record.getId() );
        verify( schemaStore, times( 1 ) ).updateRecord( record );
        verify( neoStore, times( 1 ) ).setLatestConstraintIntroducingTx( transactionId );
        verify( cacheAccess, times( 1 ) ).addSchemaRule( rule );
    }

    @Test
    public void shouldApplyUpdateUniquenessConstraintRuleSchemaRuleCommandToTheStore() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( false );
        final DynamicRecord record = DynamicRecord.dynamicRecord( 21, true );
        final Collection<DynamicRecord> recordsAfter = Arrays.asList( record );
        final UniquePropertyConstraintRule
                rule = UniquePropertyConstraintRule.uniquenessConstraintRule( 0l, 1, 2, 3l );
        final Command.SchemaRuleCommand command =
                new Command.SchemaRuleCommand().init( Collections.<DynamicRecord>emptyList(), recordsAfter, rule );

        // when
        final boolean result = applier.visitSchemaRuleCommand( command );

        // then
        assertFalse( result );

        verify( schemaStore, times( 1 ) ).updateRecord( record );
        verify( neoStore, times( 1 ) ).setLatestConstraintIntroducingTx( transactionId );
        verify( cacheAccess, times( 1 ) ).addSchemaRule( rule );
    }

    @Test
    public void shouldApplyUpdateUniquenessConstraintRuleSchemaRuleCommandToTheStoreInRecovery() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( true );
        final DynamicRecord record = DynamicRecord.dynamicRecord( 21, true );
        final Collection<DynamicRecord> recordsAfter = Arrays.asList( record );
        final UniquePropertyConstraintRule
                rule = UniquePropertyConstraintRule.uniquenessConstraintRule( 0l, 1, 2, 3l );
        final Command.SchemaRuleCommand command =
                new Command.SchemaRuleCommand().init( Collections.<DynamicRecord>emptyList(), recordsAfter, rule );

        // when
        final boolean result = applier.visitSchemaRuleCommand( command );
        applyAndClose( applier );

        // then
        assertFalse( result );

        verify( schemaStore, times( 1 ) ).setHighestPossibleIdInUse( record.getId() );
        verify( schemaStore, times( 1 ) ).updateRecord( record );
        verify( neoStore, times( 1 ) ).setLatestConstraintIntroducingTx( transactionId );
        verify( cacheAccess, times( 1 ) ).addSchemaRule( rule );
    }

    @Test
    public void shouldApplyDeleteUniquenessConstraintRuleSchemaRuleCommandToTheStore() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( false );
        final DynamicRecord record = DynamicRecord.dynamicRecord( 21, true );
        record.setInUse( false );
        final Collection<DynamicRecord> recordsAfter = Arrays.asList( record );
        final UniquePropertyConstraintRule
                rule = UniquePropertyConstraintRule.uniquenessConstraintRule( 0l, 1, 2, 3l );
        final Command.SchemaRuleCommand command =
                new Command.SchemaRuleCommand().init( Collections.<DynamicRecord>emptyList(), recordsAfter, rule );

        // when
        final boolean result = applier.visitSchemaRuleCommand( command );

        // then
        assertFalse( result );

        verify( schemaStore, times( 1 ) ).updateRecord( record );
        verify( neoStore, never() ).setLatestConstraintIntroducingTx( transactionId );
        verify( cacheAccess, times( 1 ) ).removeSchemaRuleFromCache( command.getKey() );
    }

    @Test
    public void shouldApplyDeleteUniquenessConstraintRuleSchemaRuleCommandToTheStoreInRecovery() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( true );
        final DynamicRecord record = DynamicRecord.dynamicRecord( 21, true );
        record.setInUse( false );
        final Collection<DynamicRecord> recordsAfter = Arrays.asList( record );
        final UniquePropertyConstraintRule
                rule = UniquePropertyConstraintRule.uniquenessConstraintRule( 0l, 1, 2, 3l );
        final Command.SchemaRuleCommand command =
                new Command.SchemaRuleCommand().init( Collections.<DynamicRecord>emptyList(), recordsAfter, rule );

        // when
        final boolean result = applier.visitSchemaRuleCommand( command );
        applyAndClose( applier );

        // then
        assertFalse( result );

        verify( schemaStore, times( 1 ) ).setHighestPossibleIdInUse( record.getId() );
        verify( schemaStore, times( 1 ) ).updateRecord( record );
        verify( neoStore, never() ).setLatestConstraintIntroducingTx( transactionId );
        verify( cacheAccess, times( 1 ) ).removeSchemaRuleFromCache( command.getKey() );
    }

    // NEO STORE COMMAND

    @Test
    public void shouldApplyNeoStoreCommandToTheStore() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( false );
        final NeoStoreRecord record = new NeoStoreRecord();
        record.setNextProp( 42 );

        // when
        final boolean result = applier.visitNeoStoreCommand( new Command.NeoStoreCommand().init( record ) );

        // then
        assertFalse( result );

        verify( neoStore, times( 1 ) ).setGraphNextProp( record.getNextProp() );
    }

    @Test
    public void shouldApplyNeoStoreCommandToTheStoreInRecovery() throws IOException
    {
        // given
        final NeoCommandHandler applier = newApplier( true );
        final NeoStoreRecord record = new NeoStoreRecord();
        record.setNextProp( 42 );

        // when
        final boolean result = applier.visitNeoStoreCommand( new Command.NeoStoreCommand().init( record ) );

        // then
        assertFalse( result );

        verify( neoStore, times( 1 ) ).setGraphNextProp( record.getNextProp() );
    }

    // CLOSE
}


File: community/kernel/src/test/java/org/neo4j/kernel/impl/transaction/state/IntegrityValidatorTest.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.kernel.impl.transaction.state;

import org.junit.Test;

import org.neo4j.kernel.api.exceptions.schema.UniquenessConstraintVerificationFailedKernelException;
import org.neo4j.kernel.impl.api.index.IndexingService;
import org.neo4j.kernel.impl.store.NeoStore;
import org.neo4j.kernel.impl.store.UniquePropertyConstraintRule;
import org.neo4j.kernel.impl.store.record.NodeRecord;

import static org.junit.Assert.fail;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.when;
import static org.neo4j.kernel.impl.store.UniquePropertyConstraintRule.uniquenessConstraintRule;
import static org.powermock.api.mockito.PowerMockito.mock;

public class IntegrityValidatorTest
{
    @Test
    public void shouldValidateUniquenessIndexes() throws Exception
    {
        // Given
        NeoStore store = mock( NeoStore.class );
        IndexingService indexes = mock(IndexingService.class);
        IntegrityValidator validator = new IntegrityValidator(store, indexes);

        doThrow( new UniquenessConstraintVerificationFailedKernelException( null, new RuntimeException() ) )
                .when( indexes ).validateIndex( 2l );

        UniquePropertyConstraintRule record = uniquenessConstraintRule( 1l, 1, 1, 2l );

        // When
        try
        {
            validator.validateSchemaRule( record );
            fail("Should have thrown integrity error.");
        }
        catch(Exception e)
        {
            // good 
        }
    }

    @Test
    public void deletingNodeWithRelationshipsIsNotAllowed() throws Exception
    {
        // Given
        NeoStore store = mock( NeoStore.class );
        IndexingService indexes = mock(IndexingService.class);
        IntegrityValidator validator = new IntegrityValidator(store, indexes );

        NodeRecord record = new NodeRecord( 1l, false, 1l, -1l );
        record.setInUse( false );

        // When
        try
        {
            validator.validateNodeRecord( record );
            fail("Should have thrown integrity error.");
        }
        catch(Exception e)
        {
            // good
        }
    }

    @Test
    public void transactionsStartedBeforeAConstraintWasCreatedAreDisallowed() throws Exception
    {
        // Given
        NeoStore store = mock( NeoStore.class );
        IndexingService indexes = mock(IndexingService.class);
        when(store.getLatestConstraintIntroducingTx()).thenReturn( 10l );
        IntegrityValidator validator = new IntegrityValidator( store, indexes );

        // When
        try
        {
            validator.validateTransactionStartKnowledge( 1 );
            fail("Should have thrown integrity error.");
        }
        catch(Exception e)
        {
            // good
        }
    }
}


File: community/kernel/src/test/java/org/neo4j/kernel/impl/transaction/state/NeoStoreTransactionTest.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.kernel.impl.transaction.state;

import org.junit.After;
import org.junit.Before;
import org.junit.ClassRule;
import org.junit.Test;
import org.mockito.Matchers;
import org.mockito.invocation.InvocationOnMock;
import org.mockito.stubbing.Answer;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;
import java.util.Set;
import java.util.concurrent.atomic.AtomicBoolean;

import org.neo4j.collection.primitive.PrimitiveLongCollections;
import org.neo4j.graphdb.Direction;
import org.neo4j.graphdb.factory.GraphDatabaseSettings;
import org.neo4j.graphdb.mockfs.EphemeralFileSystemAbstraction;
import org.neo4j.helpers.Pair;
import org.neo4j.helpers.Provider;
import org.neo4j.helpers.collection.Visitor;
import org.neo4j.io.pagecache.PageCache;
import org.neo4j.kernel.DefaultIdGeneratorFactory;
import org.neo4j.kernel.IdType;
import org.neo4j.kernel.KernelHealth;
import org.neo4j.kernel.api.TokenNameLookup;
import org.neo4j.kernel.api.exceptions.TransactionFailureException;
import org.neo4j.kernel.api.index.NodePropertyUpdate;
import org.neo4j.kernel.api.labelscan.LabelScanStore;
import org.neo4j.kernel.api.properties.DefinedProperty;
import org.neo4j.kernel.configuration.Config;
import org.neo4j.kernel.impl.api.KernelSchemaStateStore;
import org.neo4j.kernel.impl.api.TransactionApplicationMode;
import org.neo4j.kernel.impl.api.TransactionRepresentationCommitProcess;
import org.neo4j.kernel.impl.api.TransactionRepresentationStoreApplier;
import org.neo4j.kernel.impl.api.UpdateableSchemaState;
import org.neo4j.kernel.impl.api.index.IndexMapReference;
import org.neo4j.kernel.impl.api.index.IndexProxySetup;
import org.neo4j.kernel.impl.api.index.IndexStoreView;
import org.neo4j.kernel.impl.api.index.IndexUpdatesValidator;
import org.neo4j.kernel.impl.api.index.IndexingService;
import org.neo4j.kernel.impl.api.index.SchemaIndexProviderMap;
import org.neo4j.kernel.impl.api.index.ValidatedIndexUpdates;
import org.neo4j.kernel.impl.api.index.sampling.IndexSamplingConfig;
import org.neo4j.kernel.impl.api.index.sampling.IndexSamplingController;
import org.neo4j.kernel.impl.api.index.sampling.IndexSamplingControllerFactory;
import org.neo4j.kernel.impl.core.CacheAccessBackDoor;
import org.neo4j.kernel.impl.locking.Lock;
import org.neo4j.kernel.impl.locking.LockGroup;
import org.neo4j.kernel.impl.locking.LockService;
import org.neo4j.kernel.impl.locking.Locks;
import org.neo4j.kernel.impl.store.NeoStore;
import org.neo4j.kernel.impl.store.NodeStore;
import org.neo4j.kernel.impl.store.SchemaStore;
import org.neo4j.kernel.impl.store.StoreFactory;
import org.neo4j.kernel.impl.store.record.DynamicRecord;
import org.neo4j.kernel.impl.store.record.IndexRule;
import org.neo4j.kernel.impl.store.record.NodeRecord;
import org.neo4j.kernel.impl.store.record.PropertyBlock;
import org.neo4j.kernel.impl.store.record.PropertyRecord;
import org.neo4j.kernel.impl.store.record.Record;
import org.neo4j.kernel.impl.store.record.RelationshipGroupRecord;
import org.neo4j.kernel.impl.store.record.RelationshipRecord;
import org.neo4j.kernel.impl.store.record.SchemaRule;
import org.neo4j.kernel.impl.transaction.TransactionRepresentation;
import org.neo4j.kernel.impl.transaction.command.Command;
import org.neo4j.kernel.impl.transaction.command.Command.NodeCommand;
import org.neo4j.kernel.impl.transaction.command.Command.PropertyCommand;
import org.neo4j.kernel.impl.transaction.command.Command.RelationshipGroupCommand;
import org.neo4j.kernel.impl.transaction.command.Command.SchemaRuleCommand;
import org.neo4j.kernel.impl.transaction.command.NeoCommandHandler;
import org.neo4j.kernel.impl.transaction.log.FakeCommitment;
import org.neo4j.kernel.impl.transaction.log.PhysicalTransactionRepresentation;
import org.neo4j.kernel.impl.transaction.log.TransactionAppender;
import org.neo4j.kernel.impl.transaction.tracing.CommitEvent;
import org.neo4j.kernel.impl.transaction.tracing.LogAppendEvent;
import org.neo4j.kernel.monitoring.Monitors;
import org.neo4j.logging.LogProvider;
import org.neo4j.logging.NullLogProvider;
import org.neo4j.test.PageCacheRule;
import org.neo4j.unsafe.batchinsert.LabelScanWriter;

import static org.hamcrest.Matchers.equalTo;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertThat;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;
import static org.mockito.Matchers.any;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.reset;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoMoreInteractions;
import static org.mockito.Mockito.when;

import static java.lang.Integer.parseInt;

import static org.neo4j.graphdb.Direction.INCOMING;
import static org.neo4j.graphdb.Direction.OUTGOING;
import static org.neo4j.helpers.collection.Iterables.count;
import static org.neo4j.helpers.collection.IteratorUtil.asCollection;
import static org.neo4j.helpers.collection.IteratorUtil.asSet;
import static org.neo4j.helpers.collection.IteratorUtil.first;
import static org.neo4j.helpers.collection.MapUtil.stringMap;
import static org.neo4j.kernel.IdType.NODE;
import static org.neo4j.kernel.IdType.RELATIONSHIP;
import static org.neo4j.kernel.api.index.NodePropertyUpdate.add;
import static org.neo4j.kernel.api.index.NodePropertyUpdate.change;
import static org.neo4j.kernel.api.index.NodePropertyUpdate.remove;
import static org.neo4j.kernel.api.index.SchemaIndexProvider.NO_INDEX_PROVIDER;
import static org.neo4j.kernel.impl.api.TransactionApplicationMode.INTERNAL;
import static org.neo4j.kernel.impl.api.index.TestSchemaIndexProviderDescriptor.PROVIDER_DESCRIPTOR;
import static org.neo4j.kernel.impl.store.UniquePropertyConstraintRule.uniquenessConstraintRule;
import static org.neo4j.kernel.impl.store.record.IndexRule.indexRule;
import static org.neo4j.kernel.impl.transaction.log.TransactionIdStore.BASE_TX_ID;

public class NeoStoreTransactionTest
{
    public static final String LONG_STRING = "string value long enough not to be stored as a short string";
    private static final long[] none = new long[0];
    private static final LogProvider NULL_LOG_PROVIDER = NullLogProvider.getInstance();
    @ClassRule
    public static PageCacheRule pageCacheRule = new PageCacheRule();
    @SuppressWarnings( "deprecation" )
    private final DefaultIdGeneratorFactory idGeneratorFactory = new DefaultIdGeneratorFactory();
    private final List<Lock> lockMocks = new ArrayList<>();
    private final CommitEvent commitEvent = CommitEvent.NULL;
    private EphemeralFileSystemAbstraction fs;
    private PageCache pageCache;
    private Config config;
    private NeoStore neoStore;
    private long nextTxId = BASE_TX_ID + 1;

    // TODO change property record
    // TODO remove property record
    private LockService locks;
    private CacheAccessBackDoor cacheAccessBackDoor;
    private IndexingService mockIndexing;
    private StoreFactory storeFactory;

    private static void assertRelationshipGroupDoesNotExist( NeoStoreTransactionContext txCtx, NodeRecord node,
                                                             int type )
    {
        assertNull( txCtx.getRelationshipGroup( node, type ) );
    }

    private static void assertDenseRelationshipCounts( TransactionRecordState tx, NeoStoreTransactionContext txCtx,
                                                       long nodeId, int type, int outCount, int inCount )
    {
        RelationshipGroupRecord group = txCtx.getRelationshipGroup(
                txCtx.getNodeRecords().getOrLoad( nodeId, null ).forReadingData(), type ).forReadingData();
        assertNotNull( group );

        RelationshipRecord rel;
        long relId = group.getFirstOut();
        if ( relId != Record.NO_NEXT_RELATIONSHIP.intValue() )
        {
            rel = txCtx.getRelRecords().getOrLoad( relId, null ).forReadingData();
            // count is stored in the back pointer of the first relationship in the chain
            assertEquals( "Stored relationship count for OUTGOING differs", outCount, rel.getFirstPrevRel() );
            assertEquals( "Manually counted relationships for OUTGOING differs", outCount,
                    manuallyCountRelationships( txCtx, nodeId, relId ) );
        }

        relId = group.getFirstIn();
        if ( relId != Record.NO_NEXT_RELATIONSHIP.intValue() )
        {
            rel = txCtx.getRelRecords().getOrLoad( relId, null ).forReadingData();
            assertEquals( "Stored relationship count for INCOMING differs", inCount, rel.getSecondPrevRel() );
            assertEquals( "Manually counted relationships for INCOMING differs", inCount,
                    manuallyCountRelationships( txCtx, nodeId, relId ) );
        }
    }

    private static int manuallyCountRelationships( NeoStoreTransactionContext txCtx, long nodeId,
                                                   long firstRelId )
    {
        int count = 0;
        long relId = firstRelId;
        while ( relId != Record.NO_NEXT_RELATIONSHIP.intValue() )
        {
            count++;
            RelationshipRecord record = txCtx.getRelRecords().getOrLoad( relId, null ).forReadingData();
            relId = record.getFirstNode() == nodeId ? record.getFirstNextRel() : record.getSecondNextRel();
        }
        return count;
    }

    @Test
    public void shouldValidateConstraintIndexAsPartOfPrepare() throws Exception
    {
        // GIVEN
        TransactionRecordState writeTransaction = newWriteTransaction().first();

        final long indexId = neoStore.getSchemaStore().nextId();
        final long constraintId = neoStore.getSchemaStore().nextId();

        writeTransaction.createSchemaRule( uniquenessConstraintRule( constraintId, 1, 1, indexId ) );

        // WHEN
        writeTransaction.extractCommands( new ArrayList<Command>() );

        // THEN
        verify( mockIndexing ).validateIndex( indexId );
    }

    @Test
    public void shouldAddSchemaRuleToCacheWhenApplyingTransactionThatCreatesOne() throws Exception
    {
        // GIVEN
        TransactionRecordState writeTransaction = newWriteTransaction().first();

        // WHEN
        final long ruleId = neoStore.getSchemaStore().nextId();
        IndexRule schemaRule = indexRule( ruleId, 10, 8, PROVIDER_DESCRIPTOR );
        writeTransaction.createSchemaRule( schemaRule );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( transactionRepresentationOf( writeTransaction ), locks, commitEvent, INTERNAL );
        }

        // THEN
        verify( cacheAccessBackDoor ).addSchemaRule( schemaRule );
    }

    private PhysicalTransactionRepresentation transactionRepresentationOf( TransactionRecordState writeTransaction )
            throws TransactionFailureException
    {
        List<Command> commands = new ArrayList<>();
        writeTransaction.extractCommands( commands );
        return new PhysicalTransactionRepresentation( commands );
    }

    @Test
    public void shouldRemoveSchemaRuleFromCacheWhenApplyingTransactionThatDeletesOne() throws Exception
    {
        // GIVEN
        SchemaStore schemaStore = neoStore.getSchemaStore();
        int labelId = 10, propertyKey = 10;
        IndexRule rule = indexRule( schemaStore.nextId(), labelId, propertyKey, PROVIDER_DESCRIPTOR );
        Collection<DynamicRecord> records = schemaStore.allocateFrom( rule );
        for ( DynamicRecord record : records )
        {
            schemaStore.updateRecord( record );
        }
        long ruleId = first( records ).getId();
        TransactionRecordState writeTransaction = newWriteTransaction().first();

        // WHEN
        writeTransaction.dropSchemaRule( rule );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( transactionRepresentationOf( writeTransaction ), locks, commitEvent, INTERNAL );
        }

        // THEN
        verify( cacheAccessBackDoor ).removeSchemaRuleFromCache( ruleId );
    }

    @Test
    public void shouldMarkDynamicLabelRecordsAsNotInUseWhenLabelsAreReInlined() throws Exception
    {
        // GIVEN
        final long nodeId = neoStore.getNodeStore().nextId();

        // A transaction that creates labels that just barely fit to be inlined
        TransactionRecordState writeTransaction = newWriteTransaction().first();
        writeTransaction.nodeCreate( nodeId );

        writeTransaction.addLabelToNode( 7, nodeId );
        writeTransaction.addLabelToNode( 11, nodeId );
        writeTransaction.addLabelToNode( 12, nodeId );
        writeTransaction.addLabelToNode( 15, nodeId );
        writeTransaction.addLabelToNode( 23, nodeId );
        writeTransaction.addLabelToNode( 27, nodeId );
        writeTransaction.addLabelToNode( 50, nodeId );

        PhysicalTransactionRepresentation transactionCommands = transactionRepresentationOf( writeTransaction );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( transactionCommands, locks, commitEvent, INTERNAL );
        }


        // WHEN
        // I then remove multiple labels
        writeTransaction = newWriteTransaction().first();

        writeTransaction.removeLabelFromNode( 11, nodeId );
        writeTransaction.removeLabelFromNode( 23, nodeId );

        transactionCommands = transactionRepresentationOf( writeTransaction );

        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( transactionCommands, locks, commitEvent, INTERNAL );
        }

        // THEN
        // The dynamic label record should be part of what is logged, and it should be set to not in use anymore.
        final AtomicBoolean nodeCommandsExist = new AtomicBoolean( false );

        transactionCommands.accept( new NeoCommandHandler.HandlerVisitor( new NeoCommandHandler.Adapter()
        {
            @Override
            public boolean visitNodeCommand( NodeCommand command ) throws IOException
            {
                nodeCommandsExist.set( true );
                Collection<DynamicRecord> beforeDynLabels = command.getAfter().getDynamicLabelRecords();
                assertThat( beforeDynLabels.size(), equalTo( 1 ) );
                assertThat( beforeDynLabels.iterator().next().inUse(), equalTo( false ) );
                return false;
            }
        } ) );

        assertTrue( "No node commands found", nodeCommandsExist.get() );
    }

    @Test
    public void shouldReUseOriginalDynamicRecordWhenInlinedAndThenExpandedLabelsInSameTx() throws Exception
    {
        // GIVEN
        final long nodeId = neoStore.getNodeStore().nextId();

        // A transaction that creates labels that just barely fit to be inlined
        TransactionRecordState writeTransaction = newWriteTransaction().first();
        writeTransaction.nodeCreate( nodeId );

        writeTransaction.addLabelToNode( 16, nodeId );
        writeTransaction.addLabelToNode( 29, nodeId );
        writeTransaction.addLabelToNode( 32, nodeId );
        writeTransaction.addLabelToNode( 41, nodeId );
        writeTransaction.addLabelToNode( 44, nodeId );
        writeTransaction.addLabelToNode( 45, nodeId );
        writeTransaction.addLabelToNode( 50, nodeId );
        writeTransaction.addLabelToNode( 51, nodeId );
        writeTransaction.addLabelToNode( 52, nodeId );

        PhysicalTransactionRepresentation transactionCommands = transactionRepresentationOf( writeTransaction );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( transactionCommands, locks, commitEvent, INTERNAL );
        }

        // WHEN
        // I remove enough labels to inline them, but then add enough new labels to expand it back to dynamic
        writeTransaction = newWriteTransaction().first();

        writeTransaction.removeLabelFromNode( 50, nodeId );
        writeTransaction.removeLabelFromNode( 51, nodeId );
        writeTransaction.removeLabelFromNode( 52, nodeId );
        writeTransaction.addLabelToNode( 60, nodeId );
        writeTransaction.addLabelToNode( 61, nodeId );
        writeTransaction.addLabelToNode( 62, nodeId );

        transactionCommands = transactionRepresentationOf( writeTransaction );

        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( transactionCommands, locks, commitEvent, INTERNAL );
        }

        final AtomicBoolean nodeCommandsExist = new AtomicBoolean( false );

        transactionCommands.accept( new NeoCommandHandler.HandlerVisitor( new NeoCommandHandler.Adapter()
        {
            @Override
            public boolean visitNodeCommand( NodeCommand command ) throws IOException
            {
                nodeCommandsExist.set( true );
                DynamicRecord before = command.getBefore().getDynamicLabelRecords().iterator().next();
                DynamicRecord after = command.getAfter().getDynamicLabelRecords().iterator().next();

                assertThat( before.getId(), equalTo( after.getId() ) );
                assertThat( after.inUse(), equalTo( true ) );

                return false;
            }
        } ) );

        assertTrue( "No node commands found", nodeCommandsExist.get() );
    }

    @Test
    public void shouldRemoveSchemaRuleWhenRollingBackTransaction() throws Exception
    {
        // GIVEN
        TransactionRecordState writeTransaction = newWriteTransaction().first();

        // WHEN
        final long ruleId = neoStore.getSchemaStore().nextId();
        writeTransaction.createSchemaRule( indexRule( ruleId, 10, 7, PROVIDER_DESCRIPTOR ) );
        transactionRepresentationOf( writeTransaction );
        // rollback simply means do not commit

        // THEN
        verifyNoMoreInteractions( cacheAccessBackDoor );
    }

    @Test
    public void shouldWriteProperBeforeAndAfterPropertyRecordsWhenAddingProperty() throws Exception
    {
        // THEN
        Visitor<Command,RuntimeException> verifier = new Visitor<Command,RuntimeException>()
        {
            @Override
            public boolean visit( Command element )
            {
                if ( element instanceof PropertyCommand )
                {
                    PropertyRecord before = ((PropertyCommand) element).getBefore();
                    assertFalse( before.inUse() );
                    assertFalse( before.iterator().hasNext() );

                    PropertyRecord after = ((PropertyCommand) element).getAfter();
                    assertTrue( after.inUse() );
                    assertEquals( 1, count( after ) );
                }
                return true;
            }
        };

        // GIVEN
        TransactionRecordState writeTransaction = newWriteTransaction().first();
        int nodeId = 1;
        writeTransaction.nodeCreate( nodeId );
        int propertyKey = 1;
        Object value = 5;

        // WHEN
        writeTransaction.nodeAddProperty( nodeId, propertyKey, value );
        transactionRepresentationOf( writeTransaction );
    }

    @Test
    public void shouldConvertAddedPropertyToNodePropertyUpdates() throws Exception
    {
        // GIVEN
        long nodeId = 0;
        CapturingIndexingService indexingService = createCapturingIndexingService();
        TransactionRecordState writeTransaction = newWriteTransaction( indexingService ).first();
        int labelId = 3;
        int propertyKey1 = 1, propertyKey2 = 2;
        Object value1 = "first", value2 = 4;

        // WHEN
        writeTransaction.nodeCreate( nodeId );
        writeTransaction.addLabelToNode( labelId, nodeId );
        writeTransaction.nodeAddProperty( nodeId, propertyKey1, value1 );
        writeTransaction.nodeAddProperty( nodeId, propertyKey2, value2 );
        PhysicalTransactionRepresentation transactionCommands = transactionRepresentationOf( writeTransaction );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess( indexingService ).commit( transactionCommands, locks, commitEvent, INTERNAL );
        }

        // THEN
        assertEquals( asSet(
                        add( nodeId, propertyKey1, value1, new long[]{labelId} ),
                        add( nodeId, propertyKey2, value2, new long[]{labelId} )
                ),
                indexingService.updates );
    }

    @Test
    public void shouldConvertChangedPropertyToNodePropertyUpdates() throws Exception
    {
        // GIVEN
        int nodeId = 0;
        TransactionRecordState writeTransaction = newWriteTransaction().first();
        int propertyKey1 = 1, propertyKey2 = 2;
        Object value1 = "first", value2 = 4;
        writeTransaction.nodeCreate( nodeId );
        DefinedProperty property1 = writeTransaction.nodeAddProperty( nodeId, propertyKey1, value1 );
        DefinedProperty property2 = writeTransaction.nodeAddProperty( nodeId, propertyKey2, value2 );
        PhysicalTransactionRepresentation transactionCommands = transactionRepresentationOf( writeTransaction );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( transactionCommands, locks, commitEvent, INTERNAL );
        }

        // WHEN
        CapturingIndexingService indexingService = createCapturingIndexingService();
        Object newValue1 = "new", newValue2 = "new 2";
        writeTransaction = newWriteTransaction( indexingService ).first();
        writeTransaction.nodeChangeProperty( nodeId, property1.propertyKeyId(), newValue1 );
        writeTransaction.nodeChangeProperty( nodeId, property2.propertyKeyId(), newValue2 );
        transactionCommands = transactionRepresentationOf( writeTransaction );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess( indexingService ).commit( transactionCommands, locks, commitEvent, INTERNAL );
        }

        // THEN
        assertEquals( asSet(
                        change( nodeId, propertyKey1, value1, none, newValue1, none ),
                        change( nodeId, propertyKey2, value2, none, newValue2, none ) ),

                indexingService.updates );
    }

    @Test
    public void shouldConvertRemovedPropertyToNodePropertyUpdates() throws Exception
    {
        // GIVEN
        int nodeId = 0;
        TransactionRecordState writeTransaction = newWriteTransaction().first();
        int propertyKey1 = 1, propertyKey2 = 2;
        int labelId = 3;
        Object value1 = "first", value2 = 4;
        writeTransaction.nodeCreate( nodeId );
        writeTransaction.addLabelToNode( labelId, nodeId );
        DefinedProperty property1 = writeTransaction.nodeAddProperty( nodeId, propertyKey1, value1 );
        DefinedProperty property2 = writeTransaction.nodeAddProperty( nodeId, propertyKey2, value2 );
        PhysicalTransactionRepresentation transactionCommands = transactionRepresentationOf( writeTransaction );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( transactionCommands, locks, commitEvent, INTERNAL );
        }

        // WHEN
        CapturingIndexingService indexingService = createCapturingIndexingService();
        writeTransaction = newWriteTransaction( indexingService ).first();
        writeTransaction.nodeRemoveProperty( nodeId, property1.propertyKeyId() );
        writeTransaction.nodeRemoveProperty( nodeId, property2.propertyKeyId() );
        transactionCommands = transactionRepresentationOf( writeTransaction );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess( indexingService ).commit( transactionCommands, locks, commitEvent, INTERNAL );
        }

        // THEN
        assertEquals( asSet(
                        remove( nodeId, propertyKey1, value1, new long[]{labelId} ),
                        remove( nodeId, propertyKey2, value2, new long[]{labelId} )
                ),
                indexingService.updates );
    }

    @Test
    public void shouldConvertLabelAdditionToNodePropertyUpdates() throws Exception
    {
        // GIVEN
        long nodeId = 0;
        TransactionRecordState writeTransaction = newWriteTransaction().first();
        int propertyKey1 = 1, propertyKey2 = 2, labelId = 3;
        long[] labelIds = new long[]{labelId};
        Object value1 = LONG_STRING, value2 = LONG_STRING.getBytes();
        writeTransaction.nodeCreate( nodeId );
        writeTransaction.nodeAddProperty( nodeId, propertyKey1, value1 );
        writeTransaction.nodeAddProperty( nodeId, propertyKey2, value2 );
        PhysicalTransactionRepresentation transactionCommands = transactionRepresentationOf( writeTransaction );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( transactionCommands, locks, commitEvent, INTERNAL );
        }

        // WHEN
        CapturingIndexingService indexingService = createCapturingIndexingService();
        writeTransaction = newWriteTransaction( indexingService ).first();
        writeTransaction.addLabelToNode( labelId, nodeId );
        transactionCommands = transactionRepresentationOf( writeTransaction );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess( indexingService ).commit( transactionCommands, locks, commitEvent, INTERNAL );
        }

        // THEN
        assertEquals( asSet(
                        add( nodeId, propertyKey1, value1, labelIds ),
                        add( nodeId, propertyKey2, value2, labelIds ) ),

                indexingService.updates );
    }

    @Test
    public void shouldConvertMixedLabelAdditionAndSetPropertyToNodePropertyUpdates() throws Exception
    {
        // GIVEN
        long nodeId = 0;
        TransactionRecordState writeTransaction = newWriteTransaction().first();
        int propertyKey1 = 1, propertyKey2 = 2, labelId1 = 3, labelId2 = 4;
        Object value1 = "first", value2 = 4;
        writeTransaction.nodeCreate( nodeId );
        writeTransaction.nodeAddProperty( nodeId, propertyKey1, value1 );
        writeTransaction.addLabelToNode( labelId1, nodeId );
        PhysicalTransactionRepresentation transactionCommands = transactionRepresentationOf( writeTransaction );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( transactionCommands, locks, commitEvent, INTERNAL );
        }

        // WHEN
        CapturingIndexingService indexingService = createCapturingIndexingService();
        writeTransaction = newWriteTransaction( indexingService ).first();
        writeTransaction.nodeAddProperty( nodeId, propertyKey2, value2 );
        writeTransaction.addLabelToNode( labelId2, nodeId );
        transactionCommands = transactionRepresentationOf( writeTransaction );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess( indexingService ).commit( transactionCommands, locks, commitEvent, INTERNAL );
        }

        // THEN
        assertEquals( asSet(
                        add( nodeId, propertyKey1, value1, new long[]{labelId2} ),
                        add( nodeId, propertyKey2, value2, new long[]{labelId2} ),
                        add( nodeId, propertyKey2, value2, new long[]{labelId1} ) ),
                indexingService.updates );
    }

    @Test
    public void shouldConvertLabelRemovalToNodePropertyUpdates() throws Exception
    {
        // GIVEN
        long nodeId = 0;
        TransactionRecordState writeTransaction = newWriteTransaction().first();
        int propertyKey1 = 1, propertyKey2 = 2, labelId = 3;
        long[] labelIds = new long[]{labelId};
        Object value1 = "first", value2 = 4;
        writeTransaction.nodeCreate( nodeId );
        writeTransaction.nodeAddProperty( nodeId, propertyKey1, value1 );
        writeTransaction.nodeAddProperty( nodeId, propertyKey2, value2 );
        writeTransaction.addLabelToNode( labelId, nodeId );
        PhysicalTransactionRepresentation transactionCommands = transactionRepresentationOf( writeTransaction );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( transactionCommands, locks, commitEvent, INTERNAL );
        }

        // WHEN
        CapturingIndexingService indexingService = createCapturingIndexingService();
        writeTransaction = newWriteTransaction( indexingService ).first();
        writeTransaction.removeLabelFromNode( labelId, nodeId );
        transactionCommands = transactionRepresentationOf( writeTransaction );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess( indexingService ).commit( transactionCommands, locks, commitEvent, INTERNAL );
        }

        // THEN
        assertEquals( asSet(
                        remove( nodeId, propertyKey1, value1, labelIds ),
                        remove( nodeId, propertyKey2, value2, labelIds ) ),

                indexingService.updates );
    }

    @Test
    public void shouldConvertMixedLabelRemovalAndRemovePropertyToNodePropertyUpdates() throws Exception
    {
        // GIVEN
        long nodeId = 0;
        TransactionRecordState writeTransaction = newWriteTransaction().first();
        int propertyKey1 = 1, propertyKey2 = 2, labelId1 = 3, labelId2 = 4;
        Object value1 = "first", value2 = 4;
        writeTransaction.nodeCreate( nodeId );
        DefinedProperty property1 = writeTransaction.nodeAddProperty( nodeId, propertyKey1, value1 );
        writeTransaction.nodeAddProperty( nodeId, propertyKey2, value2 );
        writeTransaction.addLabelToNode( labelId1, nodeId );
        writeTransaction.addLabelToNode( labelId2, nodeId );
        PhysicalTransactionRepresentation transactionCommands = transactionRepresentationOf( writeTransaction );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( transactionCommands, locks, commitEvent, INTERNAL );
        }

        // WHEN
        CapturingIndexingService indexingService = createCapturingIndexingService();
        writeTransaction = newWriteTransaction( indexingService ).first();
        writeTransaction.nodeRemoveProperty( nodeId, property1.propertyKeyId() );
        writeTransaction.removeLabelFromNode( labelId2, nodeId );
        transactionCommands = transactionRepresentationOf( writeTransaction );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess( indexingService ).commit( transactionCommands, locks, commitEvent, INTERNAL );
        }

        // THEN
        assertEquals( asSet(
                        remove( nodeId, propertyKey1, value1, new long[]{labelId1, labelId2} ),
                        remove( nodeId, propertyKey2, value2, new long[]{labelId2} ) ),

                indexingService.updates );
    }

    @Test
    public void shouldConvertMixedLabelRemovalAndAddPropertyToNodePropertyUpdates() throws Exception
    {
        // GIVEN
        long nodeId = 0;
        TransactionRecordState writeTransaction = newWriteTransaction().first();
        int propertyKey1 = 1, propertyKey2 = 2, labelId1 = 3, labelId2 = 4;
        Object value1 = "first", value2 = 4;
        writeTransaction.nodeCreate( nodeId );
        writeTransaction.nodeAddProperty( nodeId, propertyKey1, value1 );
        writeTransaction.addLabelToNode( labelId1, nodeId );
        writeTransaction.addLabelToNode( labelId2, nodeId );
        PhysicalTransactionRepresentation transactionCommands = transactionRepresentationOf( writeTransaction );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( transactionCommands, locks, commitEvent, INTERNAL );
        }

        // WHEN
        CapturingIndexingService indexingService = createCapturingIndexingService();
        writeTransaction = newWriteTransaction( indexingService ).first();
        writeTransaction.nodeAddProperty( nodeId, propertyKey2, value2 );
        writeTransaction.removeLabelFromNode( labelId2, nodeId );
        transactionCommands = transactionRepresentationOf( writeTransaction );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess( indexingService ).commit( transactionCommands, locks, commitEvent, INTERNAL );
        }

        // THEN
        assertEquals( asSet(
                        add( nodeId, propertyKey2, value2, new long[]{labelId1} ),
                        remove( nodeId, propertyKey1, value1, new long[]{labelId2} ),
                        remove( nodeId, propertyKey2, value2, new long[]{labelId2} ) ),

                indexingService.updates );
    }

    @Test
    public void shouldUpdateHighIdsOnExternalTransaction() throws Exception
    {
        // GIVEN
        TransactionRecordState tx = newWriteTransaction().first();
        int nodeId = 5, relId = 10, relationshipType = 3, propertyKeyId = 4, ruleId = 8;

        // WHEN
        tx.nodeCreate( nodeId );
        tx.createRelationshipTypeToken( "type", relationshipType );
        tx.relCreate( relId, 0, nodeId, nodeId );
        tx.relAddProperty( relId, propertyKeyId,
                new long[]{1l << 60, 1l << 60, 1l << 60, 1l << 60, 1l << 60, 1l << 60, 1l << 60, 1l << 60, 1l << 60,
                        1l << 60} );
        tx.createPropertyKeyToken( "key", propertyKeyId );
        tx.nodeAddProperty( nodeId, propertyKeyId,
                "something long and nasty that requires dynamic records for sure I would think and hope. Ok then " +
                "åäö%!=" );
        for ( int i = 0; i < 10; i++ )
        {
            tx.addLabelToNode( 10000 + i, nodeId );
        }
        tx.createSchemaRule( indexRule( ruleId, 100, propertyKeyId, PROVIDER_DESCRIPTOR ) );

        PhysicalTransactionRepresentation toCommit = transactionRepresentationOf( tx );
        RecoveryCreatingCopyingNeoCommandHandler recoverer = new RecoveryCreatingCopyingNeoCommandHandler();
        toCommit.accept( recoverer );

        commit( recoverer.getAsRecovered(), TransactionApplicationMode.EXTERNAL );

        // THEN
        assertEquals( "NodeStore", nodeId + 1, neoStore.getNodeStore().getHighId() );
        assertEquals( "DynamicNodeLabelStore", 2, neoStore.getNodeStore().getDynamicLabelStore().getHighId() );
        assertEquals( "RelationshipStore", relId + 1, neoStore.getRelationshipStore().getHighId() );
        assertEquals( "RelationshipTypeStore", relationshipType + 1,
                neoStore.getRelationshipTypeTokenStore().getHighId() );
        assertEquals( "RelationshipType NameStore", 2,
                neoStore.getRelationshipTypeTokenStore().getNameStore().getHighId() );
        assertEquals( "PropertyStore", 2, neoStore.getPropertyStore().getHighId() );
        assertEquals( "PropertyStore DynamicStringStore", 2, neoStore.getPropertyStore().getStringStore().getHighId() );
        assertEquals( "PropertyStore DynamicArrayStore", 2, neoStore.getPropertyStore().getArrayStore().getHighId() );
        assertEquals( "PropertyIndexStore", propertyKeyId + 1, neoStore.getPropertyKeyTokenStore().getHighId() );
        assertEquals( "PropertyKeyToken NameStore", 2,
                neoStore.getPropertyStore().getPropertyKeyTokenStore().getNameStore().getHighId() );
        assertEquals( "SchemaStore", ruleId + 1, neoStore.getSchemaStore().getHighId() );
    }

    @Test
    public void createdSchemaRuleRecordMustBeWrittenHeavy() throws Exception
    {
        // GIVEN
        TransactionRecordState tx = newWriteTransaction().first();
        long ruleId = 0;
        int labelId = 5, propertyKeyId = 7;
        SchemaRule rule = indexRule( ruleId, labelId, propertyKeyId, PROVIDER_DESCRIPTOR );

        // WHEN
        tx.createSchemaRule( rule );
        PhysicalTransactionRepresentation transactionCommands = transactionRepresentationOf( tx );

        transactionCommands.accept( new NeoCommandHandler.HandlerVisitor( new NeoCommandHandler.Adapter()
        {
            @Override
            public boolean visitSchemaRuleCommand( SchemaRuleCommand command ) throws IOException
            {
                for ( DynamicRecord record : command.getRecordsAfter() )
                {
                    assertFalse( record + " should have been heavy", record.isLight() );
                }
                return false;
            }
        } ) );
    }

    @Test
    public void shouldWriteProperPropertyRecordsWhenOnlyChangingLinkage() throws Exception
    {
        /* There was an issue where GIVEN:
         *
         *   Legend: () = node, [] = property record
         *
         *   ()-->[0:block{size:1}]
         *
         * WHEN adding a new property record in front of if, not changing any data in that record i.e:
         *
         *   ()-->[1:block{size:4}]-->[0:block{size:1}]
         *
         * The state of property record 0 would be that it had loaded value records for that block,
         * but those value records weren't heavy, so writing that record to the log would fail
         * w/ an assertion data != null.
         */

        // GIVEN
        TransactionRecordState tx = newWriteTransaction().first();
        int nodeId = 0;
        tx.nodeCreate( nodeId );
        int index = 0;
        tx.nodeAddProperty( nodeId, index, string( 70 ) ); // will require a block of size 1
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( transactionRepresentationOf( tx ), locks, commitEvent, INTERNAL );
        }

        // WHEN
        Visitor<Command, IOException> verifier = new NeoCommandHandler.HandlerVisitor( new NeoCommandHandler.Adapter()
        {
            @Override
            public boolean visitPropertyCommand( PropertyCommand command ) throws IOException
            {
                // THEN
                verifyPropertyRecord( command.getBefore() );
                verifyPropertyRecord( command.getAfter() );
                return false;
            }

            private void verifyPropertyRecord( PropertyRecord record )
            {
                if ( record.getPrevProp() != Record.NO_NEXT_PROPERTY.intValue() )
                {
                    for ( PropertyBlock block : record )
                    {
                        assertTrue( block.isLight() );
                    }
                }
            }
        } );
        tx = newWriteTransaction( mockIndexing ).first();
        int index2 = 1;
        tx.nodeAddProperty( nodeId, index2, string( 40 ) ); // will require a block of size 4
        PhysicalTransactionRepresentation representation = transactionRepresentationOf( tx );
        representation.accept( verifier );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( representation, locks, commitEvent, INTERNAL );
        }
    }

    @Test
    @SuppressWarnings( "unchecked" )
    public void shouldCreateEqualNodePropertyUpdatesOnRecoveryOfCreatedNode() throws Exception
    {
        /* There was an issue where recovering a tx where a node with a label and a property
         * was created resulted in two exact copies of NodePropertyUpdates. */

        // GIVEN
        long nodeId = 0;
        int labelId = 5, propertyKeyId = 7;
        NodePropertyUpdate expectedUpdate = NodePropertyUpdate.add( nodeId, propertyKeyId, "Neo", new long[]{labelId} );

        // -- an index
        long ruleId = 0;
        TransactionRecordState tx = newWriteTransaction().first();
        SchemaRule rule = indexRule( ruleId, labelId, propertyKeyId, PROVIDER_DESCRIPTOR );
        tx.createSchemaRule( rule );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( transactionRepresentationOf( tx ), locks, commitEvent, INTERNAL );
        }

        // -- and a tx creating a node with that label and property key
        IteratorCollector<NodePropertyUpdate> indexUpdates = new IteratorCollector<>( 0 );
        doAnswer( indexUpdates ).when( mockIndexing ).validate( any( Iterable.class ) );
        tx = newWriteTransaction().first();
        tx.nodeCreate( nodeId );
        tx.addLabelToNode( labelId, nodeId );
        tx.nodeAddProperty( nodeId, propertyKeyId, "Neo" );
        PhysicalTransactionRepresentation representation = transactionRepresentationOf( tx );
        RecoveryCreatingCopyingNeoCommandHandler recoverer = new RecoveryCreatingCopyingNeoCommandHandler();
        representation.accept( recoverer );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( representation, locks, commitEvent, INTERNAL );
        }
        verify( mockIndexing, times( 1 ) ).validate( any( Iterable.class ) );
        indexUpdates.assertContent( expectedUpdate );

        reset( mockIndexing );
        indexUpdates = new IteratorCollector<>( 0 );
        doAnswer( indexUpdates ).when( mockIndexing ).validate( any( Iterable.class ) );

        // WHEN
        // -- later recovering that tx, there should be only one update
        commit( recoverer.getAsRecovered(), TransactionApplicationMode.RECOVERY );
        verify( mockIndexing, times( 1 ) ).addRecoveredNodeIds( PrimitiveLongCollections.setOf( nodeId ) );
        verify( mockIndexing, never() ).validate( any( Iterable.class ) );
    }

    @Test
    public void shouldLockUpdatedNodes() throws Exception
    {
        // given
        NodeStore nodeStore = neoStore.getNodeStore();
        long[] nodes = { // allocate ids
                nodeStore.nextId(),
                nodeStore.nextId(),
                nodeStore.nextId(),
                nodeStore.nextId(),
                nodeStore.nextId(),
                nodeStore.nextId(),
                nodeStore.nextId(),
        };
        // create the node records that we will modify in our main tx.
        try ( LockGroup lockGroup = new LockGroup() )
        {
            TransactionRecordState tx = newWriteTransaction().first();
            for ( int i = 1; i < nodes.length - 1; i++ )
            {
                tx.nodeCreate( nodes[i] );
            }
            tx.nodeAddProperty( nodes[3], 0, "old" );
            tx.nodeAddProperty( nodes[4], 0, "old" );
            commitProcess().commit( transactionRepresentationOf( tx ), lockGroup, commitEvent, INTERNAL );
            reset( locks ); // reset the lock counts
        }

        // These are the changes we want to assert locking on
        TransactionRecordState tx = newWriteTransaction().first();
        tx.nodeCreate( nodes[0] );
        tx.addLabelToNode( 0, nodes[1] );
        tx.nodeAddProperty( nodes[2], 0, "value" );
        tx.nodeChangeProperty( nodes[3], 0, "value" );
        tx.nodeRemoveProperty( nodes[4], 0 );
        tx.nodeDelete( nodes[5] );

        tx.nodeCreate( nodes[6] );
        tx.addLabelToNode( 0, nodes[6] );
        tx.nodeAddProperty( nodes[6], 0, "value" );

        // when
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( transactionRepresentationOf( tx ), locks, commitEvent, INTERNAL );
        }

        // then
        // create node, NodeCommand == 1 update
        verify( locks, times( 1 ) ).acquireNodeLock( nodes[0], LockService.LockType.WRITE_LOCK );
        // add label, NodeCommand == 1 update
        verify( locks, times( 1 ) ).acquireNodeLock( nodes[1], LockService.LockType.WRITE_LOCK );
        // add property, NodeCommand and PropertyCommand == 2 updates
        verify( locks, times( 2 ) ).acquireNodeLock( nodes[2], LockService.LockType.WRITE_LOCK );
        // update property, in place, PropertyCommand == 1 update
        verify( locks, times( 1 ) ).acquireNodeLock( nodes[3], LockService.LockType.WRITE_LOCK );
        // remove property, updates the Node and the Property == 2 updates
        verify( locks, times( 2 ) ).acquireNodeLock( nodes[4], LockService.LockType.WRITE_LOCK );
        // delete node, single NodeCommand == 1 update
        verify( locks, times( 1 ) ).acquireNodeLock( nodes[5], LockService.LockType.WRITE_LOCK );
        // create and add-label goes into the NodeCommand, add property is a PropertyCommand == 2 updates
        verify( locks, times( 2 ) ).acquireNodeLock( nodes[6], LockService.LockType.WRITE_LOCK );
    }

    @Test
    public void shouldConvertToDenseNodeRepresentationWhenHittingThresholdWithDifferentTypes() throws Exception
    {
        // GIVEN a node with a total of denseNodeThreshold-1 relationships
        resetFileSystem();
        instantiateNeoStore( 50 );
        Pair<TransactionRecordState, NeoStoreTransactionContext> transactionContextPair =
                newWriteTransaction();
        TransactionRecordState tx = transactionContextPair.first();
        NeoStoreTransactionContext txCtx = transactionContextPair.other();
        long nodeId = nextId( NODE );
        int typeA = 0, typeB = 1, typeC = 2;
        tx.nodeCreate( nodeId );
        tx.createRelationshipTypeToken( "A", typeA );
        createRelationships( tx, nodeId, typeA, OUTGOING, 6 );
        createRelationships( tx, nodeId, typeA, INCOMING, 7 );

        tx.createRelationshipTypeToken( "B", typeB );
        createRelationships( tx, nodeId, typeB, OUTGOING, 8 );
        createRelationships( tx, nodeId, typeB, INCOMING, 9 );

        tx.createRelationshipTypeToken( "C", typeC );
        createRelationships( tx, nodeId, typeC, OUTGOING, 10 );
        createRelationships( tx, nodeId, typeC, INCOMING, 10 );
        // here we're at the edge
        assertFalse( txCtx.getNodeRecords().getOrLoad( nodeId, null ).forReadingData().isDense() );

        // WHEN creating the relationship that pushes us over the threshold
        createRelationships( tx, nodeId, typeC, INCOMING, 1 );

        // THEN the node should have been converted into a dense node
        assertTrue( txCtx.getNodeRecords().getOrLoad( nodeId, null ).forReadingData().isDense() );
        assertDenseRelationshipCounts( tx, txCtx, nodeId, typeA, 6, 7 );
        assertDenseRelationshipCounts( tx, txCtx, nodeId, typeB, 8, 9 );
        assertDenseRelationshipCounts( tx, txCtx, nodeId, typeC, 10, 11 );
    }

    @Test
    public void shouldConvertToDenseNodeRepresentationWhenHittingThresholdWithTheSameTypeDifferentDirection()
            throws Exception
    {
        // GIVEN a node with a total of denseNodeThreshold-1 relationships
        resetFileSystem();
        instantiateNeoStore( 49 );
        Pair<TransactionRecordState, NeoStoreTransactionContext> transactionContextPair =
                newWriteTransaction();
        TransactionRecordState tx = transactionContextPair.first();
        NeoStoreTransactionContext txCtx = transactionContextPair.other();
        long nodeId = nextId( NODE );
        int typeA = 0;
        tx.nodeCreate( nodeId );
        tx.createRelationshipTypeToken( "A", typeA );
        createRelationships( tx, nodeId, typeA, OUTGOING, 24 );
        createRelationships( tx, nodeId, typeA, INCOMING, 25 );

        // here we're at the edge
        assertFalse( txCtx.getNodeRecords().getOrLoad( nodeId, null ).forReadingData().isDense() );

        // WHEN creating the relationship that pushes us over the threshold
        createRelationships( tx, nodeId, typeA, INCOMING, 1 );

        // THEN the node should have been converted into a dense node
        assertTrue( txCtx.getNodeRecords().getOrLoad( nodeId, null ).forReadingData().isDense() );
        assertDenseRelationshipCounts( tx, txCtx, nodeId, typeA, 24, 26 );
    }

    @Test
    public void shouldConvertToDenseNodeRepresentationWhenHittingThresholdWithTheSameTypeSameDirection()
            throws Exception
    {
        // GIVEN a node with a total of denseNodeThreshold-1 relationships
        resetFileSystem();
        instantiateNeoStore( 8 );
        Pair<TransactionRecordState, NeoStoreTransactionContext> transactionContextPair =
                newWriteTransaction();
        TransactionRecordState tx = transactionContextPair.first();
        NeoStoreTransactionContext txCtx = transactionContextPair.other();
        long nodeId = nextId( NODE );
        int typeA = 0;
        tx.nodeCreate( nodeId );
        tx.createRelationshipTypeToken( "A", typeA );
        createRelationships( tx, nodeId, typeA, OUTGOING, 8 );

        // here we're at the edge
        assertFalse( txCtx.getNodeRecords().getOrLoad( nodeId, null ).forReadingData().isDense() );

        // WHEN creating the relationship that pushes us over the threshold
        createRelationships( tx, nodeId, typeA, OUTGOING, 1 );

        // THEN the node should have been converted into a dense node
        assertTrue( txCtx.getNodeRecords().getOrLoad( nodeId, null ).forReadingData().isDense() );
        assertDenseRelationshipCounts( tx, txCtx, nodeId, typeA, 9, 0 );
    }

    @Test
    public void shouldMaintainCorrectDataWhenDeletingFromDenseNodeWithOneType() throws Exception
    {
        // GIVEN a node with a total of denseNodeThreshold-1 relationships
        resetFileSystem();
        instantiateNeoStore( 13 );
        Pair<TransactionRecordState, NeoStoreTransactionContext> transactionContextPair =
                newWriteTransaction();
        TransactionRecordState tx = transactionContextPair.first();
        NeoStoreTransactionContext txCtx = transactionContextPair.other();
        int nodeId = (int) nextId( NODE ), typeA = 0;
        tx.nodeCreate( nodeId );
        tx.createRelationshipTypeToken( "A", typeA );
        long[] relationshipsCreated = createRelationships( tx, nodeId, typeA, INCOMING, 15 );

        //WHEN
        deleteRelationship( tx, relationshipsCreated[0] );

        // THEN the node should have been converted into a dense node
        assertDenseRelationshipCounts( tx, txCtx, nodeId, typeA, 0, 14 );
    }

    @Test
    public void shouldMaintainCorrectDataWhenDeletingFromDenseNodeWithManyTypes() throws Exception
    {
        // GIVEN a node with a total of denseNodeThreshold-1 relationships
        resetFileSystem();
        instantiateNeoStore( 1 );
        Pair<TransactionRecordState, NeoStoreTransactionContext> transactionAndContextPair =
                newWriteTransaction();
        TransactionRecordState tx = transactionAndContextPair.first();
        NeoStoreTransactionContext txCtx = transactionAndContextPair.other();
        long nodeId = nextId( NODE );
        int typeA = 0, typeB = 12, typeC = 600;
        tx.nodeCreate( nodeId );
        tx.createRelationshipTypeToken( "A", typeA );
        long[] relationshipsCreatedAIncoming = createRelationships( tx, nodeId, typeA, INCOMING, 1 );
        long[] relationshipsCreatedAOutgoing = createRelationships( tx, nodeId, typeA, OUTGOING, 1 );

        tx.createRelationshipTypeToken( "B", typeB );
        long[] relationshipsCreatedBIncoming = createRelationships( tx, nodeId, typeB, INCOMING, 1 );
        long[] relationshipsCreatedBOutgoing = createRelationships( tx, nodeId, typeB, OUTGOING, 1 );

        tx.createRelationshipTypeToken( "C", typeC );
        long[] relationshipsCreatedCIncoming = createRelationships( tx, nodeId, typeC, INCOMING, 1 );
        long[] relationshipsCreatedCOutgoing = createRelationships( tx, nodeId, typeC, OUTGOING, 1 );

        // WHEN
        deleteRelationship( tx, relationshipsCreatedAIncoming[0] );

        // THEN
        assertDenseRelationshipCounts( tx, txCtx, nodeId, typeA, 1, 0 );
        assertDenseRelationshipCounts( tx, txCtx, nodeId, typeB, 1, 1 );
        assertDenseRelationshipCounts( tx, txCtx, nodeId, typeC, 1, 1 );

        // WHEN
        deleteRelationship( tx, relationshipsCreatedAOutgoing[0] );

        // THEN
        assertRelationshipGroupDoesNotExist(
                txCtx, txCtx.getNodeRecords().getOrLoad( nodeId, null ).forReadingData(), typeA );
        assertDenseRelationshipCounts( tx, txCtx, nodeId, typeB, 1, 1 );
        assertDenseRelationshipCounts( tx, txCtx, nodeId, typeC, 1, 1 );

        // WHEN
        deleteRelationship( tx, relationshipsCreatedBIncoming[0] );

        // THEN
        assertRelationshipGroupDoesNotExist(
                txCtx, txCtx.getNodeRecords().getOrLoad( nodeId, null ).forReadingData(), typeA );
        assertDenseRelationshipCounts( tx, txCtx, nodeId, typeB, 1, 0 );
        assertDenseRelationshipCounts( tx, txCtx, nodeId, typeC, 1, 1 );

        // WHEN
        deleteRelationship( tx, relationshipsCreatedBOutgoing[0] );

        // THEN
        assertRelationshipGroupDoesNotExist(
                txCtx, txCtx.getNodeRecords().getOrLoad( nodeId, null ).forReadingData(), typeA );
        assertRelationshipGroupDoesNotExist(
                txCtx, txCtx.getNodeRecords().getOrLoad( nodeId, null ).forReadingData(), typeB );
        assertDenseRelationshipCounts( tx, txCtx, nodeId, typeC, 1, 1 );

        // WHEN
        deleteRelationship( tx, relationshipsCreatedCIncoming[0] );

        // THEN
        assertRelationshipGroupDoesNotExist(
                txCtx, txCtx.getNodeRecords().getOrLoad( nodeId, null ).forReadingData(), typeA );
        assertRelationshipGroupDoesNotExist(
                txCtx, txCtx.getNodeRecords().getOrLoad( nodeId, null ).forReadingData(), typeB );
        assertDenseRelationshipCounts( tx, txCtx, nodeId, typeC, 1, 0 );

        // WHEN
        deleteRelationship( tx, relationshipsCreatedCOutgoing[0] );

        // THEN
        assertRelationshipGroupDoesNotExist(
                txCtx, txCtx.getNodeRecords().getOrLoad( nodeId, null ).forReadingData(), typeA );
        assertRelationshipGroupDoesNotExist(
                txCtx, txCtx.getNodeRecords().getOrLoad( nodeId, null ).forReadingData(), typeB );
        assertRelationshipGroupDoesNotExist(
                txCtx, txCtx.getNodeRecords().getOrLoad( nodeId, null ).forReadingData(), typeC );
    }

    @Test
    public void movingBilaterallyOfTheDenseNodeThresholdIsConsistent() throws Exception
    {
        // GIVEN
        resetFileSystem();
        instantiateNeoStore( 10 );
        final long nodeId = neoStore.getNodeStore().nextId();

        TransactionRecordState writeTransaction = newWriteTransaction().first();
        writeTransaction.nodeCreate( nodeId );

        int typeA = (int) neoStore.getRelationshipTypeTokenStore().nextId();
        writeTransaction.createRelationshipTypeToken( "A", typeA );
        createRelationships( writeTransaction, nodeId, typeA, INCOMING, 20 );

        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( transactionRepresentationOf( writeTransaction ), locks, commitEvent, INTERNAL );
        }
        writeTransaction = newWriteTransaction().first();

        int typeB = 1;
        writeTransaction.createRelationshipTypeToken( "B", typeB );


        // WHEN
        // i remove enough relationships to become dense and remove enough to become not dense
        long[] relationshipsOfTypeB = createRelationships( writeTransaction, nodeId, typeB, OUTGOING, 5 );
        for ( long relationshipToDelete : relationshipsOfTypeB )
        {
            deleteRelationship( writeTransaction, relationshipToDelete );
        }

        PhysicalTransactionRepresentation tx = transactionRepresentationOf( writeTransaction );
        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( tx, locks, commitEvent, INTERNAL );
        }

        // THEN
        // The dynamic label record in before should be the same id as in after, and should be in use
        final AtomicBoolean foundRelationshipGroupInUse = new AtomicBoolean();

        tx.accept( new NeoCommandHandler.HandlerVisitor( new NeoCommandHandler.Adapter()
        {
            @Override
            public boolean visitRelationshipGroupCommand(
                    RelationshipGroupCommand command ) throws IOException
            {
                if ( command.getRecord().inUse() )
                {
                    if ( !foundRelationshipGroupInUse.get() )
                    {
                        foundRelationshipGroupInUse.set( true );
                    }
                    else
                    {
                        fail();
                    }
                }
                return false;
            }
        } ) );

        assertTrue( "Did not create relationship group command", foundRelationshipGroupInUse.get() );
    }

    @Test
    public void testRecordTransactionClosed() throws Exception
    {
        // GIVEN
        long[] originalClosedTransaction = neoStore.getLastClosedTransaction();
        long transactionId = originalClosedTransaction[0] + 1;
        long version = 1l;
        long byteOffset = 777l;

        // WHEN
        neoStore.transactionClosed( transactionId, version, byteOffset );
        long[] closedTransactionFlags = neoStore.getLastClosedTransaction();

        //EXPECT
        assertEquals( version, closedTransactionFlags[1]);
        assertEquals( byteOffset, closedTransactionFlags[2]);

        // WHEN
        neoStore.close();
        neoStore = storeFactory.newNeoStore( false );

        // EXPECT
        long[] lastClosedTransactionFlags = neoStore.getLastClosedTransaction();
        assertEquals( version, lastClosedTransactionFlags[1]);
        assertEquals( byteOffset, lastClosedTransactionFlags[2]);
    }

    @Test
    public void shouldSortRelationshipGroups() throws Exception
    {
        // GIVEN a node with group of type 10
        resetFileSystem();
        instantiateNeoStore( 1 );
        int type5 = 5, type10 = 10, type15 = 15;
        try ( LockGroup locks = new LockGroup() )
        {
            TransactionRecordState tx = newWriteTransaction().first();
            neoStore.getRelationshipTypeTokenStore().setHighId( 16 );
            tx.createRelationshipTypeToken( "5", type5 );
            tx.createRelationshipTypeToken( "10", type10 );
            tx.createRelationshipTypeToken( "15", type15 );
            commitProcess().commit( transactionRepresentationOf( tx ), locks, commitEvent, INTERNAL );
        }
        long nodeId = neoStore.getNodeStore().nextId();
        try ( LockGroup locks = new LockGroup() )
        {
            TransactionRecordState tx = newWriteTransaction().first();
            long otherNode1Id = neoStore.getNodeStore().nextId();
            long otherNode2Id = neoStore.getNodeStore().nextId();
            tx.nodeCreate( nodeId );
            tx.nodeCreate( otherNode1Id );
            tx.nodeCreate( otherNode2Id );
            tx.relCreate( neoStore.getRelationshipStore().nextId(), type10, nodeId, otherNode1Id );
            // This relationship will cause the switch to dense
            tx.relCreate( neoStore.getRelationshipStore().nextId(), type10, nodeId, otherNode2Id );
            commitProcess().commit( transactionRepresentationOf( tx ), locks, commitEvent, INTERNAL );
            // Just a little validation of assumptions
            assertRelationshipGroupsInOrder( nodeId, type10 );
        }

        // WHEN inserting a relationship of type 5
        try ( LockGroup locks = new LockGroup() )
        {
            TransactionRecordState tx = newWriteTransaction().first();
            long otherNodeId = neoStore.getNodeStore().nextId();
            tx.nodeCreate( otherNodeId );
            tx.relCreate( neoStore.getRelationshipStore().nextId(), type5, nodeId, otherNodeId );
            commitProcess().commit( transactionRepresentationOf( tx ), locks, commitEvent, INTERNAL );
        }

        // THEN that group should end up first in the chain
        assertRelationshipGroupsInOrder( nodeId, type5, type10 );

        // WHEN inserting a relationship of type 15
        try ( LockGroup locks = new LockGroup() )
        {
            TransactionRecordState tx = newWriteTransaction().first();
            long otherNodeId = neoStore.getNodeStore().nextId();
            tx.nodeCreate( otherNodeId );
            tx.relCreate( neoStore.getRelationshipStore().nextId(), type15, nodeId, otherNodeId );
            commitProcess().commit( transactionRepresentationOf( tx ), locks, commitEvent, INTERNAL );
        }

        // THEN that group should end up last in the chain
        assertRelationshipGroupsInOrder( nodeId, type5, type10, type15 );
    }

    private void assertRelationshipGroupsInOrder( long nodeId, int... types )
    {
        NodeRecord node = neoStore.getNodeStore().getRecord( nodeId );
        assertTrue( "Node should be dense, is " + node, node.isDense() );
        long groupId = node.getNextRel();
        int cursor = 0;
        List<RelationshipGroupRecord> seen = new ArrayList<>();
        while ( groupId != Record.NO_NEXT_RELATIONSHIP.intValue() )
        {
            RelationshipGroupRecord group = neoStore.getRelationshipGroupStore().getRecord( groupId );
            seen.add( group );
            assertEquals( "Invalid type, seen groups so far " + seen, types[cursor++], group.getType() );
            groupId = group.getNext();
        }
        assertEquals( "Not enough relationship group records found in chain for " + node, types.length, cursor );
    }

    private long nextId( IdType type )
    {
        return idGeneratorFactory.get( type ).nextId();
    }

    private long[] createRelationships( TransactionRecordState tx, long nodeId, int type, Direction direction,
                                        int count )
    {
        long[] result = new long[count];
        for ( int i = 0; i < count; i++ )
        {
            long otherNodeId = nextId( NODE );
            tx.nodeCreate( otherNodeId );
            long first = direction == OUTGOING ? nodeId : otherNodeId;
            long other = direction == INCOMING ? nodeId : otherNodeId;
            long relId = nextId( RELATIONSHIP );
            result[i] = relId;
            tx.relCreate( relId, type, first, other );
        }
        return result;
    }

    private void deleteRelationship( TransactionRecordState tx, long relId )
    {
        tx.relDelete( relId );
    }

    private String string( int length )
    {
        StringBuilder result = new StringBuilder();
        char ch = 'a';
        for ( int i = 0; i < length; i++ )
        {
            result.append( (char) ((ch + (i % 10))) );
        }
        return result.toString();
    }

    @Before
    public void before() throws Exception
    {
        fs = new EphemeralFileSystemAbstraction();
        pageCache = pageCacheRule.getPageCache( fs );
        instantiateNeoStore( parseInt( GraphDatabaseSettings.dense_node_threshold.getDefaultValue() ) );
    }

    @SuppressWarnings( "unchecked" )
    private void instantiateNeoStore( int denseNodeThreshold ) throws Exception
    {
        config = new Config( stringMap(
                GraphDatabaseSettings.dense_node_threshold.name(), "" + denseNodeThreshold ) );

        File storeDir = new File( "dir" );

        storeFactory = new StoreFactory(
                storeDir,
                config,
                idGeneratorFactory,
                pageCache,
                fs,
                NULL_LOG_PROVIDER,
                new Monitors() );
        neoStore = storeFactory.createNeoStore();
        neoStore.rebuildCountStoreIfNeeded();
        lockMocks.clear();
        locks = mock( LockService.class, new Answer()
        {
            @Override
            public synchronized Object answer( final InvocationOnMock invocation ) throws Throwable
            {
                // This is necessary because finalize() will also be called
                if ( invocation.getMethod().getName().equals( "acquireNodeLock" ) )
                {
                    final Lock mock = mock( Lock.class, new Answer()
                    {
                        @Override
                        public Object answer( InvocationOnMock invocationOnMock ) throws Throwable
                        {
                            return null;
                        }
                    } );
                    lockMocks.add( mock );
                    return mock;
                }
                else
                {
                    return null;
                }
            }
        } );

        cacheAccessBackDoor = mock( CacheAccessBackDoor.class );
        mockIndexing = mock( IndexingService.class );
        doReturn( ValidatedIndexUpdates.NONE ).when( mockIndexing ).validate( any( Iterable.class ) );
    }

    private TransactionRepresentationCommitProcess commitProcess() throws IOException
    {
        return commitProcess( mockIndexing );
    }

    private TransactionRepresentationCommitProcess commitProcess( IndexingService indexing ) throws IOException
    {
        TransactionAppender appenderMock = mock( TransactionAppender.class );
        when( appenderMock.append(
                Matchers.<TransactionRepresentation>any(),
                any( LogAppendEvent.class ) ) ).thenReturn( new FakeCommitment( nextTxId++, neoStore ) );
        @SuppressWarnings( "unchecked" )
        Provider<LabelScanWriter> labelScanStore = mock( Provider.class );
        when( labelScanStore.instance() ).thenReturn( mock( LabelScanWriter.class ) );
        TransactionRepresentationStoreApplier applier = new TransactionRepresentationStoreApplier(
                indexing, labelScanStore, neoStore, cacheAccessBackDoor, locks, null, null, null, null );

        // Call this just to make sure the counters have been initialized.
        // This is only a problem in a mocked environment like this.
        neoStore.nextCommittingTransactionId();

        PropertyLoader propertyLoader = new PropertyLoader( neoStore );

        return new TransactionRepresentationCommitProcess( appenderMock, mock( KernelHealth.class ),
                neoStore, applier, new IndexUpdatesValidator( neoStore, null, propertyLoader, indexing ) );
    }

    @After
    public void shouldReleaseAllLocks()
    {
        for ( Lock lock : lockMocks )
        {
            verify( lock ).release();
        }
        neoStore.close();
    }

    public void resetFileSystem()
    {
        if ( neoStore != null )
        {
            neoStore.close();
        }
        fs = new EphemeralFileSystemAbstraction();
        pageCache = pageCacheRule.getPageCache( fs );
    }

    private Pair<TransactionRecordState, NeoStoreTransactionContext> newWriteTransaction()
    {
        return newWriteTransaction( mockIndexing );
    }

    private Pair<TransactionRecordState, NeoStoreTransactionContext> newWriteTransaction( IndexingService indexing )
    {
        NeoStoreTransactionContext context =
                new NeoStoreTransactionContext( mock( NeoStoreTransactionContextSupplier.class ), neoStore );
        context.bind( mock( Locks.Client.class ) );
        TransactionRecordState result = new TransactionRecordState( neoStore,
                new IntegrityValidator( neoStore, indexing ), context );

        return Pair.of( result, context );
    }

    private void commit( TransactionRepresentation recoveredTx, TransactionApplicationMode mode ) throws Exception
    {
        LabelScanStore labelScanStore = mock( LabelScanStore.class );
        when( labelScanStore.newWriter() ).thenReturn( mock( LabelScanWriter.class ) );

        try ( LockGroup locks = new LockGroup() )
        {
            commitProcess().commit( recoveredTx, locks, CommitEvent.NULL, mode );
        }
    }

    public static class RecoveryCreatingCopyingNeoCommandHandler implements Visitor<Command,IOException>
    {
        private final List<Command> commands = new LinkedList<>();

        @Override
        public boolean visit( Command element ) throws IOException
        {
            commands.add( element );
            return false;
        }

        public TransactionRepresentation getAsRecovered()
        {
            return new PhysicalTransactionRepresentation( commands );
        }
    }

    private class CapturingIndexingService extends IndexingService
    {
        private final Set<NodePropertyUpdate> updates = new HashSet<>();

        public CapturingIndexingService( IndexProxySetup proxySetup, SchemaIndexProviderMap providerMap,
                                         IndexMapReference indexMapRef, IndexStoreView storeView,
                                         Iterable<IndexRule> indexRules, IndexSamplingController samplingController,
                                         LogProvider logProvider, Monitor monitor )
        {
            super( proxySetup, providerMap, indexMapRef, storeView, indexRules, samplingController, null, logProvider,
                    monitor );
        }

        @Override
        public ValidatedIndexUpdates validate( Iterable<NodePropertyUpdate> indexUpdates )
        {
            this.updates.addAll( asCollection( indexUpdates ) );
            return ValidatedIndexUpdates.NONE;
        }
    }

    private CapturingIndexingService createCapturingIndexingService()
    {
        NeoStoreIndexStoreView storeView = new NeoStoreIndexStoreView( locks, neoStore );
        SchemaIndexProviderMap providerMap = new DefaultSchemaIndexProviderMap( NO_INDEX_PROVIDER );
        IndexingService.Monitor monitor = IndexingService.NO_MONITOR;
        UpdateableSchemaState schemaState = new KernelSchemaStateStore( NULL_LOG_PROVIDER );
        IndexSamplingConfig samplingConfig = new IndexSamplingConfig( new Config() );
        TokenNameLookup tokenNameLookup = mock( TokenNameLookup.class );
        IndexMapReference indexMapRef = new IndexMapReference();
        IndexSamplingControllerFactory
                samplingFactory = new IndexSamplingControllerFactory(
                samplingConfig, storeView, null, tokenNameLookup, NULL_LOG_PROVIDER
        );
        IndexProxySetup proxySetup =
                new IndexProxySetup( samplingConfig, storeView, providerMap, schemaState, null, null, NULL_LOG_PROVIDER );
        IndexSamplingController samplingController = samplingFactory.create( indexMapRef );
        return new CapturingIndexingService(
                proxySetup,
                providerMap,
                indexMapRef,
                storeView,
                Collections.<IndexRule>emptyList(),
                samplingController,
                NULL_LOG_PROVIDER,
                monitor
        );
    }

    private class IteratorCollector<T> implements Answer<Object>
    {
        private final int arg;
        private final List<T> elements = new ArrayList<>();

        public IteratorCollector( int arg )
        {
            this.arg = arg;
        }

        @SafeVarargs
        public final void assertContent( T... expected )
        {
            assertEquals( Arrays.asList( expected ), elements );
        }

        @Override
        @SuppressWarnings( "unchecked" )
        public Object answer( InvocationOnMock invocation ) throws Throwable
        {
            Object iterator = invocation.getArguments()[arg];
            if ( iterator instanceof Iterable )
            {
                iterator = ((Iterable<T>) iterator).iterator();
            }
            if ( iterator instanceof Iterator )
            {
                collect( (Iterator<T>) iterator );
            }
            return ValidatedIndexUpdates.NONE;
        }

        private void collect( Iterator<T> iterator )
        {
            while ( iterator.hasNext() )
            {
                elements.add( iterator.next() );
            }
        }
    }
}


File: community/kernel/src/test/java/org/neo4j/kernel/impl/transaction/state/SchemaRuleCommandTest.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.kernel.impl.transaction.state;

import org.junit.Test;

import java.util.Arrays;
import java.util.Collection;

import org.neo4j.concurrent.WorkSync;
import org.neo4j.helpers.Provider;
import org.neo4j.kernel.impl.api.index.IndexingService;
import org.neo4j.kernel.impl.api.index.ValidatedIndexUpdates;
import org.neo4j.kernel.impl.core.CacheAccessBackDoor;
import org.neo4j.kernel.impl.locking.LockGroup;
import org.neo4j.kernel.impl.locking.LockService;
import org.neo4j.kernel.impl.store.NeoStore;
import org.neo4j.kernel.impl.store.SchemaStore;
import org.neo4j.kernel.impl.store.record.DynamicRecord;
import org.neo4j.kernel.impl.store.record.IndexRule;
import org.neo4j.kernel.impl.store.record.RecordSerializer;
import org.neo4j.kernel.impl.store.record.SchemaRule;
import org.neo4j.kernel.impl.transaction.command.Command;
import org.neo4j.kernel.impl.transaction.command.Command.SchemaRuleCommand;
import org.neo4j.kernel.impl.transaction.command.IndexTransactionApplier;
import org.neo4j.kernel.impl.transaction.command.NeoStoreTransactionApplier;
import org.neo4j.kernel.impl.transaction.command.PhysicalLogNeoCommandReaderV2;
import org.neo4j.kernel.impl.transaction.log.CommandWriter;
import org.neo4j.kernel.impl.transaction.log.InMemoryLogChannel;
import org.neo4j.unsafe.batchinsert.LabelScanWriter;

import static org.hamcrest.CoreMatchers.instanceOf;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import static org.neo4j.helpers.collection.IteratorUtil.first;
import static org.neo4j.kernel.impl.api.index.TestSchemaIndexProviderDescriptor.PROVIDER_DESCRIPTOR;
import static org.neo4j.kernel.impl.store.UniquePropertyConstraintRule.uniquenessConstraintRule;

public class SchemaRuleCommandTest
{
    @Test
    public void shouldWriteCreatedSchemaRuleToStore() throws Exception
    {
        // GIVEN
        Collection<DynamicRecord> beforeRecords = serialize( rule, id, false, false);
        Collection<DynamicRecord> afterRecords = serialize( rule, id, true, true);

        when( neoStore.getSchemaStore() ).thenReturn( store );

        SchemaRuleCommand command = new SchemaRuleCommand();
        command.init( beforeRecords, afterRecords, rule );

        // WHEN
        storeApplier.visitSchemaRuleCommand( command );

        // THEN
        verify( store ).updateRecord( first( afterRecords ) );
    }

    @Test
    public void shouldCreateIndexForCreatedSchemaRule() throws Exception
    {
        // GIVEN
        Collection<DynamicRecord> beforeRecords = serialize( rule, id, false, false);
        Collection<DynamicRecord> afterRecords = serialize( rule, id, true, true);

        when( neoStore.getSchemaStore() ).thenReturn( store );

        SchemaRuleCommand command = new SchemaRuleCommand();
        command.init( beforeRecords, afterRecords, rule );

        // WHEN
        indexApplier.visitSchemaRuleCommand( command );

        // THEN
        verify( indexes ).createIndex( rule );
    }

    @Test
    public void shouldSetLatestConstraintRule() throws Exception
    {
        // Given
        Collection<DynamicRecord> beforeRecords = serialize( rule, id, true, true);
        Collection<DynamicRecord> afterRecords = serialize( rule, id, true, false);

        when( neoStore.getSchemaStore() ).thenReturn( store );

        SchemaRuleCommand command = new SchemaRuleCommand();
        command.init( beforeRecords, afterRecords, uniquenessConstraintRule( id, labelId, propertyKey, 0 )  );

        // WHEN
        storeApplier.visitSchemaRuleCommand( command );

        // THEN
        verify( store ).updateRecord( first( afterRecords ) );
        verify( neoStore ).setLatestConstraintIntroducingTx( txId );
    }

    @Test
    public void shouldDropSchemaRuleFromStore() throws Exception
    {
        // GIVEN
        Collection<DynamicRecord> beforeRecords = serialize( rule, id, true, true);
        Collection<DynamicRecord> afterRecords = serialize( rule, id, false, false);

        when( neoStore.getSchemaStore() ).thenReturn( store );

        SchemaRuleCommand command = new SchemaRuleCommand();
        command.init( beforeRecords, afterRecords, rule );

        // WHEN
        storeApplier.visitSchemaRuleCommand( command );

        // THEN
        verify( store ).updateRecord( first( afterRecords ) );
    }

    @Test
    public void shouldDropSchemaRuleFromIndex() throws Exception
    {
        // GIVEN
        Collection<DynamicRecord> beforeRecords = serialize( rule, id, true, true);
        Collection<DynamicRecord> afterRecords = serialize( rule, id, false, false);

        when( neoStore.getSchemaStore() ).thenReturn( store );

        SchemaRuleCommand command = new SchemaRuleCommand();
        command.init( beforeRecords, afterRecords, rule );

        // WHEN
        indexApplier.visitSchemaRuleCommand( command );

        // THEN
        verify( indexes ).dropIndex( rule );
    }

    @Test
    public void shouldWriteSchemaRuleToLog() throws Exception
    {
        // GIVEN
        Collection<DynamicRecord> beforeRecords = serialize( rule, id, false, false);
        Collection<DynamicRecord> afterRecords = serialize( rule, id, true, true);

        SchemaRuleCommand command = new SchemaRuleCommand();
        command.init( beforeRecords, afterRecords, rule );
        InMemoryLogChannel buffer = new InMemoryLogChannel();

        when( neoStore.getSchemaStore() ).thenReturn( store );

        // WHEN
        new CommandWriter( buffer ).visitSchemaRuleCommand( command );
        Command readCommand = reader.read( buffer );

        // THEN
        assertThat( readCommand, instanceOf( SchemaRuleCommand.class ) );

        assertSchemaRule( (SchemaRuleCommand)readCommand );
    }

    @Test
    public void shouldRecreateSchemaRuleWhenDeleteCommandReadFromDisk() throws Exception
    {
        // GIVEN
        Collection<DynamicRecord> beforeRecords = serialize( rule, id, true, true);
        Collection<DynamicRecord> afterRecords = serialize( rule, id, false, false);

        SchemaRuleCommand command = new SchemaRuleCommand();
        command.init( beforeRecords, afterRecords, rule );
        InMemoryLogChannel buffer = new InMemoryLogChannel();
        when( neoStore.getSchemaStore() ).thenReturn( store );

        // WHEN
        new CommandWriter( buffer ).visitSchemaRuleCommand( command );
        Command readCommand = reader.read( buffer );

        // THEN
        assertThat( readCommand, instanceOf( SchemaRuleCommand.class ) );

        assertSchemaRule( (SchemaRuleCommand)readCommand );
    }

    private final int labelId = 2;
    private final int propertyKey = 8;
    private final long id = 0;
    private final long txId = 1337l;
    private final NeoStore neoStore = mock( NeoStore.class );
    private final SchemaStore store = mock( SchemaStore.class );
    private final IndexingService indexes = mock( IndexingService.class );
    @SuppressWarnings( "unchecked" )
    private final Provider<LabelScanWriter> labelScanStore = mock( Provider.class );
    private final NeoStoreTransactionApplier storeApplier = new NeoStoreTransactionApplier( neoStore,
            mock( CacheAccessBackDoor.class ), LockService.NO_LOCK_SERVICE, new LockGroup(), txId );
    private final WorkSync<Provider<LabelScanWriter>,IndexTransactionApplier.LabelUpdateWork> labelScanStoreSynchronizer =
            new WorkSync<>( labelScanStore );
    private final IndexTransactionApplier indexApplier = new IndexTransactionApplier( indexes,
            ValidatedIndexUpdates.NONE, labelScanStoreSynchronizer );
    private final PhysicalLogNeoCommandReaderV2 reader = new PhysicalLogNeoCommandReaderV2();
    private final IndexRule rule = IndexRule.indexRule( id, labelId, propertyKey, PROVIDER_DESCRIPTOR );

    private Collection<DynamicRecord> serialize( SchemaRule rule, long id, boolean inUse, boolean created )
    {
        RecordSerializer serializer = new RecordSerializer();
        serializer = serializer.append( rule );
        DynamicRecord record = new DynamicRecord( id );
        record.setData( serializer.serialize() );
        if ( created )
        {
            record.setCreated();
        }
        if ( inUse )
        {
            record.setInUse( true );
        }
        return Arrays.asList( record );
    }

    private void assertSchemaRule( SchemaRuleCommand readSchemaCommand )
    {
        assertEquals( id, readSchemaCommand.getKey() );
        assertEquals( labelId, readSchemaCommand.getSchemaRule().getLabel() );
        assertEquals( propertyKey, ((IndexRule)readSchemaCommand.getSchemaRule()).getPropertyKey() );
    }

}


File: community/kernel/src/test/java/org/neo4j/unsafe/batchinsert/BatchInsertTest.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
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
package org.neo4j.unsafe.batchinsert;

import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;

import java.io.File;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.neo4j.function.Function;
import org.neo4j.graphdb.ConstraintViolationException;
import org.neo4j.graphdb.DependencyResolver;
import org.neo4j.graphdb.Direction;
import org.neo4j.graphdb.DynamicLabel;
import org.neo4j.graphdb.DynamicRelationshipType;
import org.neo4j.graphdb.GraphDatabaseService;
import org.neo4j.graphdb.Label;
import org.neo4j.graphdb.Node;
import org.neo4j.graphdb.Relationship;
import org.neo4j.graphdb.RelationshipType;
import org.neo4j.graphdb.ResourceIterator;
import org.neo4j.graphdb.Transaction;
import org.neo4j.graphdb.factory.GraphDatabaseSettings;
import org.neo4j.graphdb.schema.ConstraintDefinition;
import org.neo4j.graphdb.schema.ConstraintType;
import org.neo4j.graphdb.schema.IndexDefinition;
import org.neo4j.helpers.Pair;
import org.neo4j.helpers.collection.MapUtil;
import org.neo4j.io.fs.FileSystemAbstraction;
import org.neo4j.io.pagecache.PageCache;
import org.neo4j.kernel.GraphDatabaseAPI;
import org.neo4j.kernel.api.direct.AllEntriesLabelScanReader;
import org.neo4j.kernel.api.index.IndexConfiguration;
import org.neo4j.kernel.api.index.IndexDescriptor;
import org.neo4j.kernel.api.index.IndexPopulator;
import org.neo4j.kernel.api.index.SchemaIndexProvider;
import org.neo4j.kernel.api.labelscan.LabelScanReader;
import org.neo4j.kernel.api.labelscan.LabelScanStore;
import org.neo4j.kernel.api.labelscan.NodeLabelUpdate;
import org.neo4j.kernel.extension.KernelExtensionFactory;
import org.neo4j.kernel.impl.MyRelTypes;
import org.neo4j.kernel.impl.api.index.inmemory.InMemoryIndexProviderFactory;
import org.neo4j.kernel.impl.api.index.sampling.IndexSamplingConfig;
import org.neo4j.kernel.impl.api.scan.InMemoryLabelScanStoreExtension;
import org.neo4j.kernel.impl.api.scan.LabelScanStoreProvider;
import org.neo4j.kernel.impl.logging.StoreLogService;
import org.neo4j.kernel.impl.store.NeoStore;
import org.neo4j.kernel.impl.store.NodeLabels;
import org.neo4j.kernel.impl.store.NodeLabelsField;
import org.neo4j.kernel.impl.store.NodeStore;
import org.neo4j.kernel.impl.store.SchemaStorage;
import org.neo4j.kernel.impl.store.SchemaStore;
import org.neo4j.kernel.impl.store.StoreFactory;
import org.neo4j.kernel.impl.store.UnderlyingStorageException;
import org.neo4j.kernel.impl.store.UniquePropertyConstraintRule;
import org.neo4j.kernel.impl.store.record.DynamicRecord;
import org.neo4j.kernel.impl.store.record.IndexRule;
import org.neo4j.kernel.impl.store.record.NodeRecord;
import org.neo4j.kernel.impl.store.record.SchemaRule;
import org.neo4j.kernel.impl.transaction.state.NeoStoreSupplier;
import org.neo4j.kernel.lifecycle.Lifecycle;
import org.neo4j.kernel.monitoring.Monitors;
import org.neo4j.logging.NullLogProvider;
import org.neo4j.test.PageCacheRule;
import org.neo4j.test.TargetDirectory;
import org.neo4j.test.TestGraphDatabaseFactory;

import static java.lang.Integer.parseInt;
import static org.hamcrest.CoreMatchers.equalTo;
import static org.hamcrest.Matchers.arrayContaining;
import static org.hamcrest.Matchers.emptyArray;
import static org.hamcrest.Matchers.is;
import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertThat;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;
import static org.mockito.Matchers.any;
import static org.mockito.Matchers.anyLong;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoMoreInteractions;
import static org.mockito.Mockito.when;
import static org.neo4j.graphdb.DynamicLabel.label;
import static org.neo4j.graphdb.Neo4jMatchers.hasProperty;
import static org.neo4j.graphdb.Neo4jMatchers.inTx;
import static org.neo4j.helpers.collection.Iterables.map;
import static org.neo4j.helpers.collection.Iterables.single;
import static org.neo4j.helpers.collection.IteratorUtil.addToCollection;
import static org.neo4j.helpers.collection.IteratorUtil.asCollection;
import static org.neo4j.helpers.collection.IteratorUtil.asList;
import static org.neo4j.helpers.collection.IteratorUtil.asSet;
import static org.neo4j.helpers.collection.IteratorUtil.iterator;
import static org.neo4j.helpers.collection.MapUtil.map;
import static org.neo4j.helpers.collection.MapUtil.stringMap;
import static org.neo4j.kernel.impl.api.index.SchemaIndexTestHelper.singleInstanceSchemaIndexProviderFactory;

@RunWith( Parameterized.class )
public class BatchInsertTest
{
    private final int denseNodeThreshold;

    @Parameterized.Parameters
    public static Collection<Object[]> data()
    {
        Collection<Object[]> result = new ArrayList<>();
        result.add( new Object[] { 3 } );
        result.add( new Object[] { 20 } );
        result.add( new Object[] { parseInt( GraphDatabaseSettings.dense_node_threshold.getDefaultValue() ) } );
        return result;
    }

    public BatchInsertTest( int denseNodeThreshold )
    {
        this.denseNodeThreshold = denseNodeThreshold;
    }

    private static Map<String,Object> properties = new HashMap<>();

    private enum RelTypes implements RelationshipType
    {
        BATCH_TEST,
        REL_TYPE1,
        REL_TYPE2,
        REL_TYPE3,
        REL_TYPE4,
        REL_TYPE5
    }

    private static RelationshipType[] relTypeArray = {
        RelTypes.REL_TYPE1, RelTypes.REL_TYPE2, RelTypes.REL_TYPE3,
        RelTypes.REL_TYPE4, RelTypes.REL_TYPE5 };

    static
    {
        properties.put( "key0", "SDSDASSDLKSDSAKLSLDAKSLKDLSDAKLDSLA" );
        properties.put( "key1", 1 );
        properties.put( "key2", (short) 2 );
        properties.put( "key3", 3L );
        properties.put( "key4", 4.0f );
        properties.put( "key5", 5.0d );
        properties.put( "key6", (byte) 6 );
        properties.put( "key7", true );
        properties.put( "key8", (char) 8 );
        properties.put( "key10", new String[] {
            "SDSDASSDLKSDSAKLSLDAKSLKDLSDAKLDSLA", "dsasda", "dssadsad"
        } );
        properties.put( "key11", new int[] {1,2,3,4,5,6,7,8,9 } );
        properties.put( "key12", new short[] {1,2,3,4,5,6,7,8,9} );
        properties.put( "key13", new long[] {1,2,3,4,5,6,7,8,9 } );
        properties.put( "key14", new float[] {1,2,3,4,5,6,7,8,9} );
        properties.put( "key15", new double[] {1,2,3,4,5,6,7,8,9} );
        properties.put( "key16", new byte[] {1,2,3,4,5,6,7,8,9} );
        properties.put( "key17", new boolean[] {true,false,true,false} );
        properties.put( "key18", new char[] {1,2,3,4,5,6,7,8,9} );
    }

    private final FileSystemAbstraction fs = new org.neo4j.io.fs.DefaultFileSystemAbstraction();

    @Rule
    public TargetDirectory.TestDirectory storeDir = TargetDirectory.testDirForTest( getClass() );
    @Rule
    public final PageCacheRule pageCacheRule = new PageCacheRule();

    private Map<String, String> configuration()
    {
        return stringMap( GraphDatabaseSettings.dense_node_threshold.name(), String.valueOf( denseNodeThreshold ) );
    }

    private BatchInserter newBatchInserter() throws Exception
    {
        return BatchInserters.inserter( storeDir.absolutePath(), fs, configuration() );
    }

    private BatchInserter newBatchInserterWithSchemaIndexProvider( KernelExtensionFactory<?> provider ) throws Exception
    {
        List<KernelExtensionFactory<?>> extensions = Arrays.asList(
                provider, new InMemoryLabelScanStoreExtension() );
        return BatchInserters.inserter( storeDir.absolutePath(), fs, configuration(), extensions );
    }

    private BatchInserter newBatchInserterWithLabelScanStore( KernelExtensionFactory<?> provider ) throws Exception
    {
        List<KernelExtensionFactory<?>> extensions = Arrays.asList(
                new InMemoryIndexProviderFactory(), provider );
        return BatchInserters.inserter( storeDir.absolutePath(), fs, configuration(), extensions );
    }

    @Test
    public void shouldUpdateStringArrayPropertiesOnNodesUsingBatchInserter1() throws Exception
    {
        // Given
        BatchInserter batchInserter = newBatchInserter();

        String[] array1 = { "1" };
        String[] array2 = { "a" };

        long id1 = batchInserter.createNode(map("array", array1));
        long id2 = batchInserter.createNode(map());

        // When
        batchInserter.getNodeProperties( id1 ).get( "array" );
        batchInserter.setNodeProperty( id1, "array", array1 );
        batchInserter.setNodeProperty( id2, "array", array2 );

        batchInserter.getNodeProperties( id1 ).get( "array" );
        batchInserter.setNodeProperty( id1, "array", array1 );
        batchInserter.setNodeProperty( id2, "array", array2 );

        // Then
        assertThat( (String[])batchInserter.getNodeProperties( id1 ).get( "array" ), equalTo(array1) );

        batchInserter.shutdown();

    }

    @Test
    public void testSimple() throws Exception
    {
        BatchInserter graphDb = newBatchInserter();
        long node1 = graphDb.createNode( null );
        long node2 = graphDb.createNode( null );
        long rel1 = graphDb.createRelationship( node1, node2, RelTypes.BATCH_TEST,
                null );
        BatchRelationship rel = graphDb.getRelationshipById( rel1 );
        assertEquals( rel.getStartNode(), node1 );
        assertEquals( rel.getEndNode(), node2 );
        assertEquals( RelTypes.BATCH_TEST.name(), rel.getType().name() );
        graphDb.shutdown();
    }

    @Test
    public void testSetAndAddNodeProperties() throws Exception
    {
        BatchInserter inserter = newBatchInserter();

        long tehNode = inserter.createNode( MapUtil.map( "one", "one" ,"two","two","three","three") );
        inserter.setNodeProperty( tehNode, "four", "four" );
        inserter.setNodeProperty( tehNode, "five", "five" );
        Map<String, Object> props = inserter.getNodeProperties( tehNode );
        assertEquals( 5, props.size() );
        assertEquals( "one", props.get( "one" ) );
        assertEquals( "five", props.get( "five" ) );

        inserter.shutdown();
    }

    @Test
    public void setSingleProperty() throws Exception
    {
        BatchInserter inserter = newBatchInserter();
        long node = inserter.createNode( null );

        String value = "Something";
        String key = "name";
        inserter.setNodeProperty( node, key, value );

        GraphDatabaseService db = switchToEmbeddedGraphDatabaseService( inserter );
        assertThat( getNodeInTx( node, db ), inTx( db, hasProperty( key ).withValue( value )  ) );
        db.shutdown();
    }

    private GraphDatabaseService switchToEmbeddedGraphDatabaseService( BatchInserter inserter )
    {
        inserter.shutdown();
        TestGraphDatabaseFactory factory = new TestGraphDatabaseFactory();
        factory.setFileSystem( fs );
        return factory.newImpermanentDatabaseBuilder( new File( inserter.getStoreDir() ) )
                // Shouldn't be necessary to set dense node threshold since it's a stick config
                .setConfig( configuration() )
                .newGraphDatabase();
    }

    private NeoStore switchToNeoStore( BatchInserter inserter )
    {
        inserter.shutdown();
        File dir = new File( inserter.getStoreDir() );
        PageCache pageCache = pageCacheRule.getPageCache( fs );
        StoreFactory storeFactory = new StoreFactory( fs, dir, pageCache, NullLogProvider.getInstance(), new Monitors() );
        return storeFactory.newNeoStore( false );
    }

    @Test
    public void testSetAndKeepNodeProperty() throws Exception
    {
        BatchInserter inserter = newBatchInserter();

        long tehNode = inserter.createNode( MapUtil.map( "foo", "bar" ) );
        inserter.setNodeProperty( tehNode, "foo2", "bar2" );
        Map<String, Object> props = inserter.getNodeProperties( tehNode );
        assertEquals( 2, props.size() );
        assertEquals( "bar", props.get( "foo" ) );
        assertEquals( "bar2", props.get( "foo2" ) );

        inserter.shutdown();

        inserter = newBatchInserter();

        props = inserter.getNodeProperties( tehNode );
        assertEquals( 2, props.size() );
        assertEquals( "bar", props.get( "foo" ) );
        assertEquals( "bar2", props.get( "foo2" ) );

        inserter.setNodeProperty( tehNode, "foo", "bar3" );

        props = inserter.getNodeProperties( tehNode );
        assertEquals( "bar3", props.get( "foo" ) );
        assertEquals( 2, props.size() );
        assertEquals( "bar3", props.get( "foo" ) );
        assertEquals( "bar2", props.get( "foo2" ) );

        inserter.shutdown();
        inserter = newBatchInserter();

        props = inserter.getNodeProperties( tehNode );
        assertEquals( "bar3", props.get( "foo" ) );
        assertEquals( 2, props.size() );
        assertEquals( "bar3", props.get( "foo" ) );
        assertEquals( "bar2", props.get( "foo2" ) );

        inserter.shutdown();
    }

    @Test
    public void testSetAndKeepRelationshipProperty() throws Exception
    {
        BatchInserter inserter = newBatchInserter();

        long from = inserter.createNode( Collections.<String,Object>emptyMap() );
        long to = inserter.createNode( Collections.<String,Object>emptyMap() );
        long theRel = inserter.createRelationship( from, to,
                DynamicRelationshipType.withName( "TestingPropsHere" ),
                MapUtil.map( "foo", "bar" ) );
        inserter.setRelationshipProperty( theRel, "foo2", "bar2" );
        Map<String, Object> props = inserter.getRelationshipProperties( theRel );
        assertEquals( 2, props.size() );
        assertEquals( "bar", props.get( "foo" ) );
        assertEquals( "bar2", props.get( "foo2" ) );

        inserter.shutdown();

        inserter = newBatchInserter();

        props = inserter.getRelationshipProperties( theRel );
        assertEquals( 2, props.size() );
        assertEquals( "bar", props.get( "foo" ) );
        assertEquals( "bar2", props.get( "foo2" ) );

        inserter.setRelationshipProperty( theRel, "foo", "bar3" );

        props = inserter.getRelationshipProperties( theRel );
        assertEquals( "bar3", props.get( "foo" ) );
        assertEquals( 2, props.size() );
        assertEquals( "bar3", props.get( "foo" ) );
        assertEquals( "bar2", props.get( "foo2" ) );

        inserter.shutdown();
        inserter = newBatchInserter();

        props = inserter.getRelationshipProperties( theRel );
        assertEquals( "bar3", props.get( "foo" ) );
        assertEquals( 2, props.size() );
        assertEquals( "bar3", props.get( "foo" ) );
        assertEquals( "bar2", props.get( "foo2" ) );

        inserter.shutdown();
    }

    @Test
    public void testNodeHasProperty() throws Exception
    {
        BatchInserter inserter = newBatchInserter();

        long theNode = inserter.createNode( properties );
        long anotherNode = inserter.createNode( Collections.<String,Object>emptyMap() );
        long relationship = inserter.createRelationship( theNode, anotherNode,
                DynamicRelationshipType.withName( "foo" ), properties );
        for ( String key : properties.keySet() )
        {
            assertTrue( inserter.nodeHasProperty( theNode, key ) );
            assertFalse( inserter.nodeHasProperty( theNode, key + "-" ) );
            assertTrue( inserter.relationshipHasProperty( relationship, key ) );
            assertFalse( inserter.relationshipHasProperty( relationship, key + "-" ) );
        }

        inserter.shutdown();
    }

    @Test
    public void testRemoveProperties() throws Exception
    {
        BatchInserter inserter = newBatchInserter();

        long theNode = inserter.createNode( properties );
        long anotherNode = inserter.createNode( Collections.<String,Object>emptyMap() );
        long relationship = inserter.createRelationship( theNode, anotherNode,
                DynamicRelationshipType.withName( "foo" ), properties );

        inserter.removeNodeProperty( theNode, "key0" );
        inserter.removeRelationshipProperty( relationship, "key1" );

        for ( String key : properties.keySet() )
        {
            switch ( key )
            {
                case "key0":
                    assertFalse( inserter.nodeHasProperty( theNode, key ) );
                    assertTrue( inserter.relationshipHasProperty( relationship, key ) );
                    break;
                case "key1":
                    assertTrue( inserter.nodeHasProperty( theNode, key ) );
                    assertFalse( inserter.relationshipHasProperty( relationship,
                            key ) );
                    break;
                default:
                    assertTrue( inserter.nodeHasProperty( theNode, key ) );
                    assertTrue( inserter.relationshipHasProperty( relationship, key ) );
                    break;
            }
        }
        inserter.shutdown();
        inserter = newBatchInserter();

        for ( String key : properties.keySet() )
        {
            switch ( key )
            {
                case "key0":
                    assertFalse( inserter.nodeHasProperty( theNode, key ) );
                    assertTrue( inserter.relationshipHasProperty( relationship, key ) );
                    break;
                case "key1":
                    assertTrue( inserter.nodeHasProperty( theNode, key ) );
                    assertFalse( inserter.relationshipHasProperty( relationship,
                            key ) );
                    break;
                default:
                    assertTrue( inserter.nodeHasProperty( theNode, key ) );
                    assertTrue( inserter.relationshipHasProperty( relationship, key ) );
                    break;
            }
        }
        inserter.shutdown();
    }

    @Test
    public void shouldBeAbleToRemoveDynamicProperty() throws Exception
    {
        // Only triggered if assertions are enabled

        // GIVEN
        BatchInserter batchInserter = newBatchInserter();
        String key = "tags";
        long nodeId = batchInserter.createNode( MapUtil.map( key, new String[] { "one", "two", "three" } ) );

        // WHEN
        batchInserter.removeNodeProperty( nodeId, key );

        // THEN
        assertFalse( batchInserter.getNodeProperties( nodeId ).containsKey( key ) );
        batchInserter.shutdown();
    }

    @Test
    public void shouldBeAbleToOverwriteDynamicProperty() throws Exception
    {
        // Only triggered if assertions are enabled

        // GIVEN
        BatchInserter batchInserter = newBatchInserter();
        String key = "tags";
        long nodeId = batchInserter.createNode( MapUtil.map( key, new String[] { "one", "two", "three" } ) );

        // WHEN
        String[] secondValue = new String[] { "four", "five", "six" };
        batchInserter.setNodeProperty( nodeId, key, secondValue );

        // THEN
        assertTrue( Arrays.equals( secondValue, (String[]) batchInserter.getNodeProperties( nodeId ).get( key ) ) );
        batchInserter.shutdown();
    }

    @Test
    public void testMore() throws Exception
    {
        BatchInserter graphDb = newBatchInserter();
        long startNode = graphDb.createNode( properties );
        long endNodes[] = new long[25];
        Set<Long> rels = new HashSet<>();
        for ( int i = 0; i < 25; i++ )
        {
            endNodes[i] = graphDb.createNode( properties );
            rels.add( graphDb.createRelationship( startNode, endNodes[i],
                relTypeArray[i % 5], properties ) );
        }
        for ( BatchRelationship rel : graphDb.getRelationships( startNode ) )
        {
            assertTrue( rels.contains( rel.getId() ) );
            assertEquals( rel.getStartNode(), startNode );
        }
        graphDb.setNodeProperties( startNode, properties );
        graphDb.shutdown();
    }

    @Test
    public void makeSureLoopsCanBeCreated() throws Exception
    {
        BatchInserter graphDb = newBatchInserter();
        long startNode = graphDb.createNode( properties );
        long otherNode = graphDb.createNode( properties );
        long selfRelationship = graphDb.createRelationship( startNode, startNode,
                relTypeArray[0], properties );
        long relationship = graphDb.createRelationship( startNode, otherNode,
                relTypeArray[0], properties );
        for ( BatchRelationship rel : graphDb.getRelationships( startNode ) )
        {
            if ( rel.getId() == selfRelationship )
            {
                assertEquals( startNode, rel.getStartNode() );
                assertEquals( startNode, rel.getEndNode() );
            }
            else if ( rel.getId() == relationship )
            {
                assertEquals( startNode, rel.getStartNode() );
                assertEquals( otherNode, rel.getEndNode() );
            }
            else
            {
                fail( "Unexpected relationship " + rel.getId() );
            }
        }

        GraphDatabaseService db = switchToEmbeddedGraphDatabaseService( graphDb );

        try ( Transaction ignored = db.beginTx() )
        {
            Node realStartNode = db.getNodeById( startNode );
            Relationship realSelfRelationship = db.getRelationshipById( selfRelationship );
            Relationship realRelationship = db.getRelationshipById( relationship );
            assertEquals( realSelfRelationship, realStartNode.getSingleRelationship( RelTypes.REL_TYPE1, Direction.INCOMING ) );
            assertEquals( asSet( realSelfRelationship, realRelationship ), asSet( realStartNode.getRelationships( Direction.OUTGOING ) ) );
            assertEquals( asSet( realSelfRelationship, realRelationship ), asSet( realStartNode.getRelationships() ) );
        }
        finally
        {
            db.shutdown();
        }
    }

    private Node getNodeInTx( long nodeId, GraphDatabaseService db )
    {
        try ( Transaction ignored = db.beginTx() )
        {
            return db.getNodeById( nodeId );
        }
    }

    private void setProperties( Node node )
    {
        for ( String key : properties.keySet() )
        {
            node.setProperty( key, properties.get( key ) );
        }
    }

    private void setProperties( Relationship rel )
    {
        for ( String key : properties.keySet() )
        {
            rel.setProperty( key, properties.get( key ) );
        }
    }

    private void assertProperties( Node node )
    {
        for ( String key : properties.keySet() )
        {
            if ( properties.get( key ).getClass().isArray() )
            {
                Class<?> component = properties.get( key ).getClass().getComponentType();
                if ( !component.isPrimitive() ) // then it is String, cast to
                                                // Object[] is safe
                {
                    assertTrue( Arrays.equals(
                            (Object[]) properties.get( key ),
                            (Object[]) node.getProperty( key ) ) );
                }
                else
                {
                    if ( component == Integer.TYPE )
                    {
                        if ( component.isPrimitive() )
                        {
                            assertTrue( Arrays.equals(
                                    (int[]) properties.get( key ),
                                    (int[]) node.getProperty( key ) ) );
                        }
                    }
                    else if ( component == Boolean.TYPE )
                    {
                        if ( component.isPrimitive() )
                        {
                            assertTrue( Arrays.equals(
                                    (boolean[]) properties.get( key ),
                                    (boolean[]) node.getProperty( key ) ) );
                        }
                    }
                    else if ( component == Byte.TYPE )
                    {
                        if ( component.isPrimitive() )
                        {
                            assertTrue( Arrays.equals(
                                    (byte[]) properties.get( key ),
                                    (byte[]) node.getProperty( key ) ) );
                        }
                    }
                    else if ( component == Character.TYPE )
                    {
                        if ( component.isPrimitive() )
                        {
                            assertTrue( Arrays.equals(
                                    (char[]) properties.get( key ),
                                    (char[]) node.getProperty( key ) ) );
                        }
                    }
                    else if ( component == Long.TYPE )
                    {
                        if ( component.isPrimitive() )
                        {
                            assertTrue( Arrays.equals(
                                    (long[]) properties.get( key ),
                                    (long[]) node.getProperty( key ) ) );
                        }
                    }
                    else if ( component == Float.TYPE )
                    {
                        if ( component.isPrimitive() )
                        {
                            assertTrue( Arrays.equals(
                                    (float[]) properties.get( key ),
                                    (float[]) node.getProperty( key ) ) );
                        }
                    }
                    else if ( component == Double.TYPE )
                    {
                        if ( component.isPrimitive() )
                        {
                            assertTrue( Arrays.equals(
                                    (double[]) properties.get( key ),
                                    (double[]) node.getProperty( key ) ) );
                        }
                    }
                    else if ( component == Short.TYPE )
                    {
                        if ( component.isPrimitive() )
                        {
                            assertTrue( Arrays.equals(
                                    (short[]) properties.get( key ),
                                    (short[]) node.getProperty( key ) ) );
                        }
                    }
                }
            }
            else
            {
                assertEquals( properties.get( key ), node.getProperty( key ) );
            }
        }
        for ( String stored : node.getPropertyKeys() )
        {
            assertTrue( properties.containsKey( stored ) );
        }
    }

    @Test
    public void createBatchNodeAndRelationshipsDeleteAllInEmbedded() throws Exception
    {
        /*
         *    ()--[REL_TYPE1]-->(node)--[BATCH_TEST]->()
         */

        BatchInserter inserter = newBatchInserter();
        long nodeId = inserter.createNode( null );
        inserter.createRelationship( nodeId, inserter.createNode( null ),
                RelTypes.BATCH_TEST, null );
        inserter.createRelationship( inserter.createNode( null ), nodeId,
                RelTypes.REL_TYPE1, null );

        // Delete node and all its relationships
        GraphDatabaseService db = switchToEmbeddedGraphDatabaseService( inserter );

        try ( Transaction tx = db.beginTx() )
        {
            Node node = db.getNodeById( nodeId );
            for ( Relationship relationship : node.getRelationships() )
            {
                relationship.delete();
            }
            node.delete();
            tx.success();
        }

        db.shutdown();
    }

    @Test
    public void messagesLogGetsClosed() throws Exception
    {
        File storeDir = this.storeDir.graphDbDir();
        BatchInserter inserter = BatchInserters.inserter( storeDir, stringMap() );
        inserter.shutdown();
        assertTrue( new File( storeDir, StoreLogService.INTERNAL_LOG_NAME ).delete() );
    }

    @Test
    public void createEntitiesWithEmptyPropertiesMap() throws Exception
    {
        BatchInserter inserter = newBatchInserter();

        // Assert for node
        long nodeId = inserter.createNode( map() );
        inserter.getNodeProperties( nodeId );
        //cp=N U http://www.w3.org/1999/02/22-rdf-syntax-ns#type, c=N

        // Assert for relationship
        long anotherNodeId = inserter.createNode( null );
        long relId = inserter.createRelationship( nodeId, anotherNodeId, RelTypes.BATCH_TEST, map() );
        inserter.getRelationshipProperties( relId );
        inserter.shutdown();
    }

    @Test
    public void createEntitiesWithDynamicPropertiesMap() throws Exception
    {
        BatchInserter inserter = newBatchInserter();

        setAndGet( inserter, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" );
        setAndGet( inserter, intArray( 20 ) );

        inserter.shutdown();
    }

    @Test
    public void shouldAddInitialLabelsToCreatedNode() throws Exception
    {
        // GIVEN
        BatchInserter inserter = newBatchInserter();

        // WHEN
        long node = inserter.createNode( map(), Labels.FIRST, Labels.SECOND );

        // THEN
        assertTrue( inserter.nodeHasLabel( node, Labels.FIRST ) );
        assertTrue( inserter.nodeHasLabel( node, Labels.SECOND ) );
        assertFalse( inserter.nodeHasLabel( node, Labels.THIRD ) );
        inserter.shutdown();
    }

    @Test
    public void shouldGetNodeLabels() throws Exception
    {
        // GIVEN
        BatchInserter inserter = newBatchInserter();
        long node = inserter.createNode( map(), Labels.FIRST, Labels.THIRD );

        // WHEN
        Iterable<String> labelNames = asNames( inserter.getNodeLabels( node ) );

        // THEN
        assertEquals( asSet( Labels.FIRST.name(), Labels.THIRD.name() ), asSet( labelNames ) );
        inserter.shutdown();
    }

    @Test
    public void shouldAddManyInitialLabelsAsDynamicRecords() throws Exception
    {
        // GIVEN
        BatchInserter inserter = newBatchInserter();
        Pair<Label[], Set<String>> labels = manyLabels( 200 );
        long node = inserter.createNode( map(), labels.first() );

        // WHEN
        Iterable<String> labelNames = asNames( inserter.getNodeLabels( node ) );

        // THEN
        assertEquals( labels.other(), asSet( labelNames ) );
        inserter.shutdown();
    }

    @Test
    public void shouldReplaceExistingInlinedLabelsWithDynamic() throws Exception
    {
        // GIVEN
        BatchInserter inserter = newBatchInserter();
        long node = inserter.createNode( map(), Labels.FIRST );

        // WHEN
        Pair<Label[], Set<String>> labels = manyLabels( 100 );
        inserter.setNodeLabels( node, labels.first() );

        // THEN
        Iterable<String> labelNames = asNames( inserter.getNodeLabels( node ) );
        assertEquals( labels.other(), asSet( labelNames ) );
        inserter.shutdown();
    }

    @Test
    public void shouldReplaceExistingDynamicLabelsWithInlined() throws Exception
    {
        // GIVEN
        BatchInserter inserter = newBatchInserter();
        long node = inserter.createNode( map(), manyLabels( 150 ).first() );

        // WHEN
        inserter.setNodeLabels( node, Labels.FIRST );

        // THEN
        Iterable<String> labelNames = asNames( inserter.getNodeLabels( node ) );
        assertEquals( asSet( Labels.FIRST.name() ), asSet( labelNames ) );
        inserter.shutdown();
    }

    @Test
    public void shouldCreateDeferredSchemaIndexesInEmptyDatabase() throws Exception
    {
        // GIVEN
        BatchInserter inserter = newBatchInserter();

        // WHEN
        IndexDefinition definition = inserter.createDeferredSchemaIndex( label( "Hacker" ) ).on( "handle" ).create();

        // THEN
        assertEquals( "Hacker", definition.getLabel().name() );
        assertEquals( asCollection( iterator( "handle" ) ), asCollection( definition.getPropertyKeys() ) );
        inserter.shutdown();
    }

    @Test
    public void shouldCreateDeferredUniquenessConstraintInEmptyDatabase() throws Exception
    {
        // GIVEN
        BatchInserter inserter = newBatchInserter();

        // WHEN
        ConstraintDefinition definition =
                inserter.createDeferredConstraint( label( "Hacker" ) ).assertPropertyIsUnique( "handle" ).create();

        // THEN
        assertEquals( "Hacker", definition.getLabel().name() );
        assertEquals( ConstraintType.UNIQUENESS, definition.getConstraintType() );
        assertEquals( asSet( "handle" ), asSet( definition.getPropertyKeys() ) );
        inserter.shutdown();
    }

    @Test
    public void shouldCreateConsistentUniquenessConstraint() throws Exception
    {
        // given
        BatchInserter inserter = newBatchInserter();

        // when
        inserter.createDeferredConstraint( label( "Hacker" ) ).assertPropertyIsUnique( "handle" ).create();

        // then
        GraphDatabaseAPI graphdb = (GraphDatabaseAPI) switchToEmbeddedGraphDatabaseService( inserter );
        try
        {
            NeoStore neoStore = graphdb.getDependencyResolver().resolveDependency( NeoStoreSupplier.class ).get();
            SchemaStore store = neoStore.getSchemaStore();
            SchemaStorage storage = new SchemaStorage( store );
            List<Long> inUse = new ArrayList<>();
            for ( long i = 1, high = store.getHighestPossibleIdInUse(); i <= high; i++ )
            {
                DynamicRecord record = store.forceGetRecord( i );
                if ( record.inUse() && record.isStartRecord() )
                {
                    inUse.add( i );
                }
            }
            assertEquals( "records in use", 2, inUse.size() );
            SchemaRule rule0 = storage.loadSingleSchemaRule( inUse.get( 0 ) );
            SchemaRule rule1 = storage.loadSingleSchemaRule( inUse.get( 1 ) );
            IndexRule indexRule;
            UniquePropertyConstraintRule constraintRule;
            if ( rule0 instanceof IndexRule )
            {
                indexRule = (IndexRule) rule0;
                constraintRule = (UniquePropertyConstraintRule) rule1;
            }
            else
            {
                constraintRule = (UniquePropertyConstraintRule) rule0;
                indexRule = (IndexRule) rule1;
            }
            assertEquals( "index should reference constraint",
                          constraintRule.getId(), indexRule.getOwningConstraint().longValue() );
            assertEquals( "constraint should reference index",
                          indexRule.getId(), constraintRule.getOwnedIndex() );
        }
        finally
        {
            graphdb.shutdown();
        }
    }

    @Test
    public void shouldNotAllowCreationOfDuplicateIndex() throws Exception
    {
        // GIVEN
        BatchInserter inserter = newBatchInserter();

        // WHEN
        inserter.createDeferredSchemaIndex( label( "Hacker" ) ).on( "handle" ).create();

        try
        {
            inserter.createDeferredSchemaIndex( label( "Hacker" ) ).on( "handle" ).create();
            fail( "Should have thrown exception." );
        }
        catch ( ConstraintViolationException e )
        {
            // Good
        }

        // THEN
        inserter.shutdown();
    }

    @Test
    public void shouldNotAllowCreationOfDuplicateConstraint() throws Exception
    {
        // GIVEN
        BatchInserter inserter = newBatchInserter();

        // WHEN
        inserter.createDeferredConstraint( label( "Hacker" ) ).assertPropertyIsUnique( "handle" ).create();

        try
        {
            inserter.createDeferredConstraint( label( "Hacker" ) ).assertPropertyIsUnique( "handle" ).create();
            fail( "Should have thrown exception." );
        }
        catch ( ConstraintViolationException e )
        {
            // Good
        }

        // THEN
        inserter.shutdown();
    }

    @Test
    public void shouldNotAllowCreationOfDeferredSchemaConstraintAfterIndexOnSameKeys() throws Exception
    {
        // GIVEN
        BatchInserter inserter = newBatchInserter();

        // WHEN
        inserter.createDeferredSchemaIndex( label( "Hacker" ) ).on( "handle" ).create();

        try
        {
            inserter.createDeferredConstraint( label( "Hacker" ) ).assertPropertyIsUnique( "handle" ).create();
            fail( "Should have thrown exception." );
        }
        catch ( ConstraintViolationException e )
        {
            // Good
        }

        // THEN
        inserter.shutdown();
    }

    @Test
    public void shouldNotAllowCreationOfDeferredSchemaIndexAfterConstraintOnSameKeys() throws Exception
    {
        // GIVEN
        BatchInserter inserter = newBatchInserter();

        // WHEN
        inserter.createDeferredConstraint( label( "Hacker" ) ).assertPropertyIsUnique( "handle" ).create();

        try
        {
            inserter.createDeferredSchemaIndex( label( "Hacker" ) ).on( "handle" ).create();
            fail( "Should have thrown exception." );
        }
        catch ( ConstraintViolationException e )
        {
            // Good
        }

        // THEN
        inserter.shutdown();
    }

    @Test
    public void shouldRunIndexPopulationJobAtShutdown() throws Throwable
    {
        // GIVEN
        IndexPopulator populator = mock( IndexPopulator.class );
        SchemaIndexProvider provider = mock( SchemaIndexProvider.class );

        when( provider.getProviderDescriptor() ).thenReturn( InMemoryIndexProviderFactory.PROVIDER_DESCRIPTOR );
        when( provider.getPopulator( anyLong(), any( IndexDescriptor.class ),
                any( IndexConfiguration.class ), any( IndexSamplingConfig.class) ) ).thenReturn( populator );

        BatchInserter inserter = newBatchInserterWithSchemaIndexProvider(
                singleInstanceSchemaIndexProviderFactory( InMemoryIndexProviderFactory.KEY, provider ) );

        inserter.createDeferredSchemaIndex( label("Hacker") ).on( "handle" ).create();

        long nodeId = inserter.createNode( map( "handle", "Jakewins" ), label( "Hacker" ) );

        // WHEN
        inserter.shutdown();

        // THEN
        verify( provider ).init();
        verify( provider ).start();
        verify( provider ).getPopulator( anyLong(), any( IndexDescriptor.class ), any( IndexConfiguration.class ),
                any( IndexSamplingConfig.class) );
        verify( populator ).create();
        verify( populator ).add( nodeId, "Jakewins" );
        verify( populator ).close( true );
        verify( provider ).stop();
        verify( provider ).shutdown();
        verifyNoMoreInteractions( populator );
    }

    @Test
    public void shouldRunConstraintPopulationJobAtShutdown() throws Throwable
    {
        // GIVEN
        IndexPopulator populator = mock( IndexPopulator.class );
        SchemaIndexProvider provider = mock( SchemaIndexProvider.class );

        when( provider.getProviderDescriptor() ).thenReturn( InMemoryIndexProviderFactory.PROVIDER_DESCRIPTOR );
        when( provider.getPopulator( anyLong(), any( IndexDescriptor.class ), any( IndexConfiguration.class ),
                any( IndexSamplingConfig.class ) ) ).thenReturn( populator );

        BatchInserter inserter = newBatchInserterWithSchemaIndexProvider(
                singleInstanceSchemaIndexProviderFactory( InMemoryIndexProviderFactory.KEY, provider ) );

        inserter.createDeferredConstraint( label("Hacker") ).assertPropertyIsUnique( "handle" ).create();

        long nodeId = inserter.createNode( map( "handle", "Jakewins" ), label( "Hacker" ) );

        // WHEN
        inserter.shutdown();

        // THEN
        verify( provider ).init();
        verify( provider ).start();
        verify( provider ).getPopulator( anyLong(), any( IndexDescriptor.class ), any( IndexConfiguration.class ),
                any( IndexSamplingConfig.class ) );
        verify( populator ).create();
        verify( populator ).add( nodeId, "Jakewins" );
        verify( populator ).close( true );
        verify( provider ).stop();
        verify( provider ).shutdown();
        verifyNoMoreInteractions( populator );
    }

    @Test
    public void shouldRepopulatePreexistingIndexed() throws Throwable
    {
        // GIVEN
        long jakewins = dbWithIndexAndSingleIndexedNode();

        IndexPopulator populator = mock( IndexPopulator.class );
        SchemaIndexProvider provider = mock( SchemaIndexProvider.class );

        when( provider.getProviderDescriptor() ).thenReturn( InMemoryIndexProviderFactory.PROVIDER_DESCRIPTOR );
        when( provider.getPopulator( anyLong(), any( IndexDescriptor.class ), any( IndexConfiguration.class ),
                any( IndexSamplingConfig.class ) ) ).thenReturn( populator );

        BatchInserter inserter = newBatchInserterWithSchemaIndexProvider(
                singleInstanceSchemaIndexProviderFactory( InMemoryIndexProviderFactory.KEY, provider ) );

        long boggle = inserter.createNode( map( "handle", "b0ggl3" ), label( "Hacker" ) );

        // WHEN
        inserter.shutdown();

        // THEN
        verify( provider ).init();
        verify( provider ).start();
        verify( provider ).getPopulator( anyLong(), any( IndexDescriptor.class ), any( IndexConfiguration.class ),
                any( IndexSamplingConfig.class ) );
        verify( populator ).create();
        verify( populator ).add( jakewins, "Jakewins" );
        verify( populator ).add( boggle, "b0ggl3" );
        verify( populator ).close( true );
        verify( provider ).stop();
        verify( provider ).shutdown();
        verifyNoMoreInteractions( populator );
    }

    private long dbWithIndexAndSingleIndexedNode() throws Exception
    {
        IndexPopulator populator = mock( IndexPopulator.class );
        SchemaIndexProvider provider = mock( SchemaIndexProvider.class );

        when( provider.getProviderDescriptor() ).thenReturn( InMemoryIndexProviderFactory.PROVIDER_DESCRIPTOR );
        when( provider.getPopulator( anyLong(), any( IndexDescriptor.class ), any( IndexConfiguration.class ),
                any( IndexSamplingConfig.class ) ) ).thenReturn( populator );

        BatchInserter inserter = newBatchInserterWithSchemaIndexProvider(
                singleInstanceSchemaIndexProviderFactory( InMemoryIndexProviderFactory.KEY, provider ) );

        inserter.createDeferredSchemaIndex( label("Hacker") ).on( "handle" ).create();
        long nodeId = inserter.createNode( map( "handle", "Jakewins" ), label( "Hacker" ) );
        inserter.shutdown();
        return nodeId;
    }

    @Test
    public void shouldPopulateLabelScanStoreOnShutdown() throws Exception
    {
        // GIVEN
        // -- a database and a mocked label scan store
        UpdateTrackingLabelScanStore labelScanStore = new UpdateTrackingLabelScanStore();
        BatchInserter inserter = newBatchInserterWithLabelScanStore( new ControlledLabelScanStore( labelScanStore ) );

        // -- and some data that we insert
        long node1 = inserter.createNode( null, Labels.FIRST );
        long node2 = inserter.createNode( null, Labels.SECOND );
        long node3 = inserter.createNode( null, Labels.THIRD );
        long node4 = inserter.createNode( null, Labels.FIRST, Labels.SECOND );
        long node5 = inserter.createNode( null, Labels.FIRST, Labels.THIRD );

        // WHEN we shut down the batch inserter
        inserter.shutdown();

        // THEN the label scan store should receive all the updates.
        // of course, we don't know the label ids at this point, but we're assuming 0..2 (bad boy)
        labelScanStore.assertRecivedUpdate( node1, 0 );
        labelScanStore.assertRecivedUpdate( node2, 1 );
        labelScanStore.assertRecivedUpdate( node3, 2 );
        labelScanStore.assertRecivedUpdate( node4, 0, 1 );
        labelScanStore.assertRecivedUpdate( node5, 0, 2 );
    }

    @Test
    public void shouldSkipStoreScanIfNoLabelsAdded() throws Exception
    {
        // GIVEN
        UpdateTrackingLabelScanStore labelScanStore = new UpdateTrackingLabelScanStore();
        BatchInserter inserter = newBatchInserterWithLabelScanStore( new ControlledLabelScanStore( labelScanStore ) );

        // WHEN
        inserter.createNode( null );
        inserter.createNode( null );
        inserter.shutdown();

        // THEN
        assertEquals( 0, labelScanStore.writersCreated );
    }

    @Test
    public void propertiesCanBeReSetUsingBatchInserter() throws Exception
    {
        // GIVEN
        BatchInserter batchInserter = newBatchInserter();
        Map<String, Object> props = new HashMap<>();
        props.put( "name", "One" );
        props.put( "count", 1 );
        props.put( "tags", new String[] { "one", "two" } );
        props.put( "something", "something" );
        batchInserter.createNode( 1, props );
        batchInserter.setNodeProperty( 1, "name", "NewOne" );
        batchInserter.removeNodeProperty( 1, "count" );
        batchInserter.removeNodeProperty( 1, "something" );

        // WHEN setting new properties
        batchInserter.setNodeProperty( 1, "name", "YetAnotherOne" );
        batchInserter.setNodeProperty( 1, "additional", "something" );

        // THEN there should be no problems doing so
        assertEquals( "YetAnotherOne", batchInserter.getNodeProperties( 1 ).get( "name" ) );
        assertEquals( "something", batchInserter.getNodeProperties( 1 ).get( "additional" ) );

        batchInserter.shutdown();
    }

    /**
     * Test checks that during node property set we will cleanup not used property records
     * During initial node creation properties will occupy 5 property records.
     * Last property record will have only empty array for email.
     * During first update email property will be migrated to dynamic property and last property record will become
     * empty. That record should be deleted form property chain or otherwise on next node load user will get an
     * property record not in use exception.
     * @throws Exception
     */
    @Test
    public void testCleanupEmptyPropertyRecords() throws Exception
    {
        BatchInserter inserter = newBatchInserter();

        Map<String, Object> properties = new HashMap<>();
        properties.put("id", 1099511659993l);
        properties.put("firstName", "Edward");
        properties.put("lastName", "Shevchenko");
        properties.put("gender", "male");
        properties.put("birthday", new SimpleDateFormat("yyyy-MM-dd").parse( "1987-11-08" ).getTime());
        properties.put("birthday_month", 11);
        properties.put("birthday_day", 8);
        properties.put("creationDate", new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSZ").parse( "2010-04-22T18:05:40.912+0000" ).getTime());
        properties.put("locationIP", "46.151.255.205");
        properties.put("browserUsed", "Firefox");
        properties.put("email", new String[0]);
        properties.put("languages", new String[0]);
        long personNodeId = inserter.createNode(properties);

        assertEquals( "Shevchenko", inserter.getNodeProperties( personNodeId ).get( "lastName" ) );
        assertThat( (String[]) inserter.getNodeProperties( personNodeId ).get( "email" ), is( emptyArray() ) );

        inserter.setNodeProperty( personNodeId, "email", new String[]{"Edward1099511659993@gmail.com"} );
        assertThat( (String[]) inserter.getNodeProperties( personNodeId ).get( "email" ),
                arrayContaining( "Edward1099511659993@gmail.com" ) );

        inserter.setNodeProperty( personNodeId, "email",
                new String[]{"Edward1099511659993@gmail.com", "backup@gmail.com"} );

        assertThat( (String[]) inserter.getNodeProperties( personNodeId ).get( "email" ),
                arrayContaining( "Edward1099511659993@gmail.com", "backup@gmail.com" ) );
    }

    @Test
    public void propertiesCanBeReSetUsingBatchInserter2() throws Exception
    {
        // GIVEN
        BatchInserter batchInserter = newBatchInserter();
        long id = batchInserter.createNode( new HashMap<String, Object>() );

        // WHEN
        batchInserter.setNodeProperty( id, "test", "looooooooooong test" );
        batchInserter.setNodeProperty( id, "test", "small test" );

        // THEN
        assertEquals( "small test", batchInserter.getNodeProperties( id ).get( "test" ) );

        batchInserter.shutdown();
    }

    @Test
    public void replaceWithBiggerPropertySpillsOverIntoNewPropertyRecord() throws Exception
    {
        // GIVEN
        BatchInserter batchInserter = newBatchInserter();
        Map<String, Object> props = new HashMap<>();
        props.put( "name", "One" );
        props.put( "count", 1 );
        props.put( "tags", new String[] { "one", "two" } );
        long id = batchInserter.createNode( props );
        batchInserter.setNodeProperty( id, "name", "NewOne" );

        // WHEN
        batchInserter.setNodeProperty( id, "count", "something" );

        // THEN
        assertEquals( "something", batchInserter.getNodeProperties( id ).get( "count" ) );
        batchInserter.shutdown();
    }

    @Test
    public void mustSplitUpRelationshipChainsWhenCreatingDenseNodes() throws Exception
    {
        BatchInserter inserter = newBatchInserter();

        inserter.createNode( 1, null );
        inserter.createNode( 2, null );

        for ( int i = 0; i < 1000; i++ )
        {
            for ( MyRelTypes relType : MyRelTypes.values() )
            {
                inserter.createRelationship( 1, 2, relType, null );
            }
        }

        GraphDatabaseAPI db = (GraphDatabaseAPI) switchToEmbeddedGraphDatabaseService( inserter );
        try
        {
            DependencyResolver dependencyResolver = db.getDependencyResolver();
            NeoStoreSupplier neoStoreSupplier = dependencyResolver.resolveDependency( NeoStoreSupplier.class );
            NeoStore neoStore = neoStoreSupplier.get();
            NodeStore nodeStore = neoStore.getNodeStore();
            NodeRecord record = nodeStore.getRecord( 1 );
            assertTrue( "Node " + record + " should have been dense", record.isDense() );
        }
        finally
        {
            db.shutdown();
        }
    }

    @Test
    public void shouldGetRelationships() throws Exception
    {
        // GIVEN
        BatchInserter inserter = newBatchInserter();
        long node = inserter.createNode( null );
        createRelationships( inserter, node, RelTypes.REL_TYPE1, 3, 2, 1 );
        createRelationships( inserter, node, RelTypes.REL_TYPE2, 4, 5, 6 );

        // WHEN
        Set<Long> gottenRelationships = asSet( inserter.getRelationshipIds( node ) );

        // THEN
        assertEquals( 21, gottenRelationships.size() );
        inserter.shutdown();
    }

    @Test
    public void shouldNotCreateSameLabelTwiceOnSameNode() throws Exception
    {
        // GIVEN
        BatchInserter inserter = newBatchInserter();

        // WHEN
        long nodeId = inserter.createNode( map( "itemId", 1000l ), DynamicLabel.label( "Item" ),
                DynamicLabel.label( "Item" ) );

        // THEN
        NeoStore neoStore = switchToNeoStore( inserter );
        try
        {
            NodeRecord node = neoStore.getNodeStore().getRecord( nodeId );
            NodeLabels labels = NodeLabelsField.parseLabelsField( node );
            long[] labelIds = labels.get( neoStore.getNodeStore() );
            assertEquals( 1, labelIds.length );
        }
        finally
        {
            neoStore.close();
        }
    }

    @Test
    public void shouldSortLabelIdsWhenGetOrCreate() throws Exception
    {
        // GIVEN
        BatchInserter inserter = newBatchInserter();

        // WHEN
        long nodeId = inserter.createNode( map( "Item", 123456789123l ), DynamicLabel.label( "AA" ),
                DynamicLabel.label( "BB" ), DynamicLabel.label( "CC" ), DynamicLabel.label( "DD" ) );
        inserter.setNodeLabels( nodeId, DynamicLabel.label( "CC" ), DynamicLabel.label( "AA" ),
                DynamicLabel.label( "DD" ), DynamicLabel.label( "EE" ), DynamicLabel.label( "FF" ) );

        // THEN
        try ( NeoStore neoStore = switchToNeoStore( inserter ) )
        {
            NodeRecord node = neoStore.getNodeStore().getRecord( nodeId );
            NodeLabels labels = NodeLabelsField.parseLabelsField( node );

            long[] labelIds = labels.get( neoStore.getNodeStore() );
            long[] sortedLabelIds = labelIds.clone();
            Arrays.sort( sortedLabelIds );
            assertArrayEquals( sortedLabelIds, labelIds );
        }
    }

    @Test
    public void shouldCreateUniquenessConstraint() throws Exception
    {
        // Given
        Label label = label( "Person" );
        String propertyKey = "name";
        String duplicatedValue = "Tom";

        BatchInserter inserter = newBatchInserter();

        // When
        inserter.createDeferredConstraint( label ).assertPropertyIsUnique( propertyKey ).create();

        // Then
        GraphDatabaseService db = switchToEmbeddedGraphDatabaseService( inserter );
        try
        {
            try ( Transaction tx = db.beginTx() )
            {
                List<ConstraintDefinition> constraints = asList( db.schema().getConstraints() );
                assertEquals( 1, constraints.size() );
                ConstraintDefinition constraint = constraints.get( 0 );
                assertEquals( label.name(), constraint.getLabel().name() );
                assertEquals( propertyKey, single( constraint.getPropertyKeys() ) );

                db.createNode( label ).setProperty( propertyKey, duplicatedValue );

                tx.success();
            }

            try ( Transaction tx = db.beginTx() )
            {
                db.createNode( label ).setProperty( propertyKey, duplicatedValue );
                tx.success();
            }
            fail( "Uniqueness property constraint was violated, exception expected" );
        }
        catch ( ConstraintViolationException e )
        {
            assertEquals( e.getMessage(),
                    "Node 0 already exists with label " + label.name() + " and property \"" + propertyKey + "\"=[" +
                    duplicatedValue + "]"
            );
        }
        finally
        {
            db.shutdown();
        }
    }

    @Test
    public void shouldCreateMandatoryNodePropertyConstraint() throws Exception
    {
        // Given
        Label label = label( "Person" );
        String propertyKey = "name";

        BatchInserter inserter = newBatchInserter();

        // When
        inserter.createDeferredConstraint( label ).assertPropertyExists( propertyKey ).create();

        // Then
        GraphDatabaseService db = switchToEmbeddedGraphDatabaseService( inserter );
        try
        {
            try ( Transaction tx = db.beginTx() )
            {
                List<ConstraintDefinition> constraints = asList( db.schema().getConstraints() );
                assertEquals( 1, constraints.size() );
                ConstraintDefinition constraint = constraints.get( 0 );
                assertEquals( label.name(), constraint.getLabel().name() );
                assertEquals( propertyKey, single( constraint.getPropertyKeys() ) );
                tx.success();
            }

            try ( Transaction tx = db.beginTx() )
            {
                db.createNode( label );
                tx.success();
            }
            fail( "Mandatory node property constraint was violated, exception expected" );
        }
        catch ( ConstraintViolationException e )
        {
            assertEquals(
                    e.getMessage(),
                    "Node 0 with label \"" + label.name() + "\" does not have a \"" + propertyKey + "\" property"
            );
        }
        finally
        {
            db.shutdown();
        }
    }

    @Test
    public void shouldCreateMandatoryRelationshipPropertyConstraint() throws Exception
    {
        // Given
        RelationshipType type = DynamicRelationshipType.withName( "KNOWS" );
        String propertyKey = "since";

        BatchInserter inserter = newBatchInserter();

        // When
        inserter.createDeferredConstraint( type ).assertPropertyExists( propertyKey ).create();

        // Then
        GraphDatabaseService db = switchToEmbeddedGraphDatabaseService( inserter );
        try
        {
            try ( Transaction tx = db.beginTx() )
            {
                List<ConstraintDefinition> constraints = asList( db.schema().getConstraints() );
                assertEquals( 1, constraints.size() );
                ConstraintDefinition constraint = constraints.get( 0 );
                assertEquals( type.name(), constraint.getRelationshipType().name() );
                assertEquals( propertyKey, single( constraint.getPropertyKeys() ) );
                tx.success();
            }

            try ( Transaction tx = db.beginTx() )
            {
                db.createNode().createRelationshipTo( db.createNode(), type );
                tx.success();
            }
            fail( "Mandatory relationship property constraint was violated, exception expected" );
        }
        catch ( ConstraintViolationException e )
        {
            assertEquals(
                    e.getMessage(),
                    "Relationship 0 with type \"" + type.name() + "\" does not have a \"" + propertyKey + "\" property"
            );
        }
        finally
        {
            db.shutdown();
        }
    }

    private void createRelationships( BatchInserter inserter, long node, RelationshipType relType,
            int out, int in, int loop )
    {
        for ( int i = 0; i < out; i++ )
        {
            inserter.createRelationship( node, inserter.createNode( null ), relType, null );
        }
        for ( int i = 0; i < out; i++ )
        {
            inserter.createRelationship( inserter.createNode( null ), node, relType, null );
        }
        for ( int i = 0; i < out; i++ )
        {
            inserter.createRelationship( node, node, relType, null );
        }
    }

    private static class UpdateTrackingLabelScanStore implements LabelScanStore
    {
        private final List<NodeLabelUpdate> allUpdates = new ArrayList<>();
        int writersCreated;

        public void assertRecivedUpdate( long node, long... labels )
        {
            for ( NodeLabelUpdate update : allUpdates )
            {
                if ( update.getNodeId() == node &&
                        Arrays.equals( update.getLabelsAfter(), labels ) )
                {
                    return;
                }
            }

            fail( "No update matching [nodeId:" + node + ", labels:" + Arrays.toString( labels ) + " found among: " +
                    allUpdates );
        }

        @Override
        public void force() throws UnderlyingStorageException
        {
        }

        @Override
        public LabelScanReader newReader()
        {
            return null;
        }

        @Override
        public AllEntriesLabelScanReader newAllEntriesReader()
        {
            return null;
        }

        @Override
        public ResourceIterator<File> snapshotStoreFiles() throws IOException
        {
            return null;
        }

        @Override
        public void init() throws IOException
        {
        }

        @Override
        public void start() throws IOException
        {
        }

        @Override
        public void stop() throws IOException
        {
        }

        @Override
        public void shutdown() throws IOException
        {
        }

        @Override public LabelScanWriter newWriter()
        {
            writersCreated++;
            return new LabelScanWriter()
            {
                @Override
                public void write( NodeLabelUpdate update ) throws IOException
                {
                    addToCollection( Collections.singletonList( update ).iterator(), allUpdates );
                }

                @Override
                public void close() throws IOException
                {
                }
            };
        }
    }

    private static class ControlledLabelScanStore extends KernelExtensionFactory<InMemoryLabelScanStoreExtension.NoDependencies>
    {
        private final LabelScanStore labelScanStore;

        public ControlledLabelScanStore( LabelScanStore labelScanStore )
        {
            super( "batch" );
            this.labelScanStore = labelScanStore;
        }

        @Override
        public Lifecycle newKernelExtension( InMemoryLabelScanStoreExtension.NoDependencies dependencies ) throws Throwable
        {
            return new LabelScanStoreProvider( labelScanStore, 100 );
        }
    }

    private void setAndGet( BatchInserter inserter, Object value )
    {
        long nodeId = inserter.createNode( map( "key", value ) );
        Object readValue = inserter.getNodeProperties( nodeId ).get( "key" );
        if ( readValue.getClass().isArray() )
        {
            assertTrue( Arrays.equals( (int[])value, (int[])readValue ) );
        }
        else
        {
            assertEquals( value, readValue );
        }
    }

    private int[] intArray( int length )
    {
        int[] array = new int[length];
        for ( int i = 0, startValue = (int)Math.pow( 2, 30 ); i < length; i++ )
        {
            array[i] = startValue+i;
        }
        return array;
    }

    private static enum Labels implements Label
    {
        FIRST,
        SECOND,
        THIRD
    }

    private Iterable<String> asNames( Iterable<Label> nodeLabels )
    {
        return map( new Function<Label,String>()
        {
            @Override
            public String apply( Label from )
            {
                return from.name();
            }
        }, nodeLabels );
    }

    private Pair<Label[],Set<String>> manyLabels( int count )
    {
        Label[] labels = new Label[count];
        Set<String> expectedLabelNames = new HashSet<>();
        for ( int i = 0; i < labels.length; i++ )
        {
            String labelName = "bach label " + i;
            labels[i] = label( labelName );
            expectedLabelNames.add( labelName );
        }
        return Pair.of( labels, expectedLabelNames );
    }
}
