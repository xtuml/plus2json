"""

Output Job Definition as JSON.

"""

import sys
from os.path import abspath
from pathlib import Path
package_path = abspath(Path(__file__).parent)
sys.path.insert(0, package_path)
import plus_job_defn

# This file provides mixin methods to the 3 primary classes to output
# Job Definition JSON which is consumable by the Protocol Verifier.

class JobDefn_JSON:
    """Job Definition JSON"""
    def json(self):
        j = '{ "JobDefinitionName": "' + self.JobDefinitionName + '",'
        j += '"Events": ['
        seqdelim = ""
        for seq in self.sequences:
            j += seq.json( seqdelim )
            seqdelim = ','
        # All events for all sequences are defined together.
        j += ']}'
        return j

class SequenceDefn_JSON:
    """Sequence Definition JSON"""
    def json(self, seqdelim):
        j = ""
        aedelim = seqdelim
        for ae in self.audit_events:
            j += ae.json( aedelim )
            j += '\n'
            aedelim = ','
        return j

class AuditEventDefn_JSON:
    """Audit Event Definition JSON"""
    def json(self, aedelim):
        j = aedelim
        aedelim = ',\n'
        j += '{ "EventName": "' + self.EventName + '",'
        j += '"OccurrenceId": ' + self.OccurrenceId + ','
        j += '"SequenceName": ' + self.sequence.SequenceName + ','
        if self.SequenceStart: j += '"SequenceStart": true,'
        if self.SequenceEnd: j += '"SequenceEnd": true,'
        if self.isBreak: j += '"IsBreak": true,'
        # look for linked DynamicControl
        dcs = [dc for dc in plus_job_defn.DynamicControl.instances if dc.source_event is self]
        for dc in dcs: # preparing for when multiple DynamicControls are allowed
            j += dc.json()
        prev_aes = ""
        pdelim = ""
        for prev_ae in self.previous_events:
            prev_aes += prev_ae.json( pdelim )
            pdelim = ','
        if "" != prev_aes: j += '"PreviousEvents": [ ' + prev_aes + '],'
        j += '"Application": "' + plus_job_defn.AuditEventDefn.ApplicationName + '"'
        j += '}'
        return j

class PreviousAuditEventDefn_JSON:
    """Previous Audit Event Definition JSON"""
    def json( self, pdelim ):
        constraintid = "" if "" == self.ConstraintDefinitionId else ', "ConstraintDefinitionId": "' + self.ConstraintDefinitionId + '"'
        constraint = "" if "" == self.ConstraintValue else ', "ConstraintValue": "' + self.ConstraintValue + '"'
        # Omit the constraint when it is IOR.
        if 'IOR' == constraint:
            constraint = ""
            constraintid = ""
        return ( pdelim +
              '{ "PreviousEventName": "' + self.previous_event.EventName + '",'
              '"PreviousOccurrenceId": ' + self.previous_event.OccurrenceId +
              constraintid + constraint +
              ' }' )

class DynamicControl_JSON:
    """branch and loop information"""
    def json( self ):
        j = '"DynamicControl": {'
        j += '"DynamicControlName": "' + self.DynamicControlName + '",'
        j += '"DynamicControlType": "' + self.DynamicControlType + '",'
        j += '"UserEventType": "' + self.user_evt_txt + '",'
        j += '"UserOccurrenceId": ' + self.user_occ_txt
        j += '},'
        return j

class Invariant_JSON:
    """Produce Invariant JSON"""
    @classmethod
    def json(cls):
        # Output invariants separately.
        if plus_job_defn.Invariant.instances:
            j = '['
            idelim = ""
            for invariant in plus_job_defn.Invariant.instances:
                j += idelim + '{'
                j += '"EventDataName": "' + invariant.Name + '",'
                invariant_type = 'INTRAJOBINV' if invariant.Type == 'IINV' else 'EXTRAJOBINV'
                j += '"EventDataType": "' + invariant_type + '",'
                j += '"SourceEventJobDefinitionName": "' + plus_job_defn.JobDefn.instances[-1].JobDefinitionName + '",'
                j += '"SourceEventType": "' + invariant.src_evt_txt + '",'
                j += '"SourceEventOccurrenceId": ' + invariant.src_occ_txt + ','
                j += '"UserEvents": ['
                j += '{ "UserEventName": "' + invariant.user_evt_txt + '",'
                j += '"UserOccurrenceId": ' + invariant.user_occ_txt + ','
                j += '"UserEventDataItemName": "' + invariant.Name + '" }'
                j += ']'
                j += '}'
                idelim = ','
            j += ']'
            return j
