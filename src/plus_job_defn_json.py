"""

Output Job Definition as JSON.

"""

import plus_job_defn

# This file provides mixin methods to the 3 primary classes to output
# Job Definition JSON which is consumable by the Protocol Verifier.

class JobDefn_JSON:
    """Job Definition JSON"""
    def json(self):
        json = "{ \"JobDefinitionName\":" + self.JobDefinitionName + ",\n"
        json += "\"Events\": ["
        print( json )
        seqdelim = ""
        for seq in self.sequences:
            seq.json( seqdelim )
            seqdelim = ","
        # All events for all sequences are defined together.
        json = "]"
        json += "\n}\n"
        print( json )

class SequenceDefn_JSON:
    """Sequence Definition JSON"""
    def json(self, seqdelim):
        aedelim = seqdelim
        for ae in self.audit_events:
            ae.json( aedelim )
            aedelim = ","

class AuditEvent_JSON:
    """Audit Event Definition JSON"""
    def json(self, aedelim):
        json = aedelim
        aedelim = ",\n"
        json += "{ \"EventName\": \"" + self.EventName + "\","
        json += "\"OccurrenceId\": " + self.OccurrenceId + ","
        json += "\"SequenceName\": " + self.sequence.SequenceName + ","
        if self.SequenceStart: json += "\"SequenceStart\": true,"
        if self.SequenceEnd: json += "\"SequenceEnd\": true,"
        if self.isBreak: json += "\"isBreak\": true,"
        # look for linked DynamicControl
        dcs = [dc for dc in plus_job_defn.DynamicControl.instances if dc.source_event is self]
        for dc in dcs: # preparing for when multiple DynamicControls are allowed
            json += dc.json()
        prev_aes = ""
        pdelim = ""
        for prev_ae in self.previous_events:
            prev_aes += prev_ae.json( pdelim )
            pdelim = ","
        if "" != prev_aes: json += "\"PreviousEvents\": [ " + prev_aes + "],"
        json += "\"Application\": \"" + plus_job_defn.AuditEvent.ApplicationName + "\""
        json += "}"
        print( json )

class PreviousAuditEvent_JSON:
    """Previous Audit Event Definition JSON"""
    def json( self, pdelim ):
        constraintid = "" if "" == self.ConstraintDefinitionId else ", \"ConstraintDefinitionId\": \"" + self.ConstraintDefinitionId + "\""
        constraint = "" if "" == self.ConstraintValue else ", \"ConstraintValue\": \"" + self.ConstraintValue + "\""
        json = ( pdelim +
              "{ \"PreviousEventName\": \"" + self.previous_event.EventName + "\","
              "\"PreviousOccurrenceId\": " + self.previous_event.OccurrenceId +
              constraintid + constraint +
              " }" )
        return json

class DynamicControl_JSON:
    """branch and loop information"""
    def json( self ):
        json = "\"DynamicControl\": {"
        json += "\"DynamicControlName\": \"" + self.DynamicControlName + "\","
        json += "\"DynamicControlType\": \"" + self.DynamicControlType + "\","
        json += "\"UserEventType\": \"" + self.user_evt_txt + "\","
        json += "\"UserOccurrenceId\": " + self.user_occ_txt
        json += "},"
        return json

class Invariant_JSON:
    """Produce Invariant JSON"""
    @classmethod
    def json(cls):
        # Output invariants separately.
        if plus_job_defn.Invariant.instances:
            json = "["
            idelim = ""
            for invariant in plus_job_defn.Invariant.instances:
                json += idelim + "\n{"
                json += "\"EventDataName\": \"" + invariant.Name + "\","
                invariant_type = "INTRAJOBINV" if invariant.Type == "IINV" else "EXTRAJOBINV"
                json += "\"EventDataType\": \"" + invariant_type + "\","
                json += "\"SourceEventJobDefinitionName\": " + plus_job_defn.JobDefn.instances[-1].JobDefinitionName + ","
                json += "\"SourceEventType\": \"" + invariant.src_evt_txt + "\","
                json += "\"SourceOccurrenceId\": " + invariant.src_occ_txt + ","
                json += "\"UserEvents\": [\n"
                json += "{ \"UserEventName\": \"" + invariant.user_evt_txt + "\","
                json += "\"UserOccurrenceId\": " + invariant.user_occ_txt + ","
                json += "\"UserEventDataItemName\": \"" + invariant.Name + "\" }"
                json += "]\n"
                json += "}"
                idelim = ","
            json += "]\n"
            print( json )
