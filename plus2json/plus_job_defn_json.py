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
        for seq in self.R1_SequenceDefn_defines:
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
        for ae in self.R2_AuditEventDefn_defines:
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
        j += '"SequenceName": ' + self.R2_SequenceDefn.SequenceName + ','
        if self.SequenceStart: j += '"SequenceStart": true,'
        if self.SequenceEnd: j += '"SequenceEnd": true,'
        if self.isBreak: j += '"IsBreak": true,'
        # look for linked DynamicControl
        dcs = [dc for dc in plus_job_defn.DynamicControl.instances if dc.R9_AuditEventDefn is self]
        if len(dcs) > 0:
            j += '"DynamicControl": ['
            j += ','.join(map(lambda dc: dc.json(), dcs))
            j += '],'
        prev_aes = ""
        pdelim = ""
        for prev_ae in self.R3_PreviousAuditEventDefn:
            prev_aes += prev_ae.json( pdelim )
            pdelim = ','
        if "" != prev_aes: j += '"PreviousEvents": [ ' + prev_aes + '],'
        # look for linked Invariant
        invs = [inv for inv in plus_job_defn.Invariant.instances if inv.R11_AuditEventDefn is self or self in inv.R12_AuditEventDefn]
        if len(invs) > 0:
            j += '"EventData": ['
            j += ','.join(map(lambda inv: inv.json(is_source=inv.R11_AuditEventDefn is self), invs))
            j += '],'
        j += '"Application": "' + plus_job_defn.AuditEventDefn.ApplicationName + '"'
        j += '}'
        return j

class PreviousAuditEventDefn_JSON:
    """Previous Audit Event Definition JSON"""
    def json( self, pdelim ):
        constraintid = "" if "" == self.ConstraintDefinitionId else ', "ConstraintDefinitionId": "' + self.ConstraintDefinitionId + '"'
        constraint = "" if "" == self.ConstraintValue else ', "ConstraintValue": "' + self.ConstraintValue + '"'
        # Omit the constraint when it is IOR.
        if 'IOR' == self.ConstraintValue:
            constraint = ""
            constraintid = ""
        return ( pdelim +
              '{ "PreviousEventName": "' + self.R3_AuditEventDefn_precedes.EventName + '",'
              '"PreviousOccurrenceId": ' + self.R3_AuditEventDefn_precedes.OccurrenceId +
              constraintid + constraint +
              ' }' )

class DynamicControl_JSON:
    """branch and loop information"""
    def json( self ):
        j = '{'
        j += '"DynamicControlName": "' + self.DynamicControlName + '",'
        j += '"DynamicControlType": "' + self.DynamicControlType + '",'
        j += '"UserEventType": "' + self.user_evt_txt + '",'
        j += '"UserOccurrenceId": ' + self.user_occ_txt
        j += '}'
        return j

class Invariant_JSON:
    """Produce Invariant JSON"""
    def json(self, is_source=False):
        j = '{'
        j += '"EventDataName": "' + self.Name + '"'
        j += ',' + '"EventDataType": "' + ('INTRAJOBINV' if self.Type == 'IINV' else 'EXTRAJOBINV') + '"'
        if not is_source:  # if this is a user event data definition, specify the source
            j += ',' + '"SourceEventDataName": "' + self.Name + '"'
            if self.Type == 'EINV':  # if this is an extra job invariant, specify the source job definition
                j += ', "SourceJobDefinitionName": "' + self.SourceJobDefinitionName + '"'
            else:
                j += ',' + '"SourceEventType": "' + self.R11_AuditEventDefn.EventName + '"'
                j += ',' + '"SourceEventOccurrenceId": ' + self.R11_AuditEventDefn.OccurrenceId
        j += '}'
        return j
