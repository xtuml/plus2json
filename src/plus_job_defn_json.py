"""

Output Job Definition as JSON.

"""

import plus_job_defn

# This file provides mixin methods to the 3 primary classes to output
# Job Definition JSON which is consumable by the Protocol Verifier.

class JobDefn_JSON:
    """Job Definition JSON"""
    def output_json(self):
        json = "{ \"JobDefinitionName\":" + self.JobDefinitionName + ",\n"
        json += "\"Events\": ["
        print( json )
        seqdelim = ""
        for seq in self.sequences:
            seq.output_json( seqdelim )
            seqdelim = ","
        # All events for all sequences are defined together.
        json = "]"
        json += "\n}\n"
        print( json )

class SequenceDefn_JSON:
    """Sequence Definition JSON"""
    def output_json(self, seqdelim):
        aedelim = seqdelim
        for ae in self.audit_events:
            ae.output_json( aedelim )
            aedelim = ","

class AuditEvent_JSON:
    """Audit Event Definition JSON"""
    def output_json(self, aedelim):
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
        for dc in dcs: # preparing for when multiple DynamicControls are allowed.
            json += "\"DynamicControl\": {"
            json += "\"DynamicControlName\": \"" + dc.DynamicControlName + "\","
            json += "\"DynamicControlType\": \"" + dc.DynamicControlType + "\","
            json += "\"UserEventType\": \"" + dc.user_evt_txt + "\","
            json += "\"UserOccurrenceId\": " + dc.user_occ_txt
            json += "},"
        prev_aes = ""
        pdelim = ""
        for prev_ae in self.previous_events:
            constraintid = "" if "" == prev_ae.ConstraintDefinitionId else ", \"ConstraintDefinitionId\": \"" + prev_ae.ConstraintDefinitionId + "\""
            constraint = "" if "" == prev_ae.ConstraintValue else ", \"ConstraintValue\": \"" + prev_ae.ConstraintValue + "\""
            prev_aes = ( prev_aes + pdelim +
                  "{ \"PreviousEventName\": \"" + prev_ae.previous_event.EventName + "\","
                  "\"PreviousOccurrenceId\": " + prev_ae.previous_event.OccurrenceId +
                  constraintid + constraint +
                  " }" )
            pdelim = ","
        if "" != prev_aes: json += "\"PreviousEvents\": [ " + prev_aes + "],"
        json += "\"Application\": \"" + plus_job_defn.AuditEvent.ApplicationName + "\""
        json += "}"
        print( json )
