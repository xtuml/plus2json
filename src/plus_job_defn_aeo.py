"""

Support Audit Event Ordering (AEO) configuration.

"""

import datetime
import plus_job_defn

# Here, methods are defined to ease the configuration of the AEOrdering
# domain.  Reasonable defaults and placeholders are provided based upon
# the input job definition.

class JobDefn_AEO:
    """AEO methods for JobDefn"""
    def aeo_config(self):
        """output AEOrdering config.json"""
        json = "{ \"SpecUpdateRate\": \"PT2M\","
        json += "\"MaxOutOfSequenceEvents\": 10,"
        json += "\"MaximumJobTime\": \"PT10M\","
        json += "\"JobCompletePeriod\": \"PT24H\","
        json += "\"Jobs\": [\n"
        json += "{ \"JobDefinitionName\": " + self.JobDefinitionName + ","
        json += "\"JobDeprecated\": false,"
        json += "\"JobTypeExpiryDate\": \"2022-04-11T18:08:00Z\","
        json += "\"StaleAuditEventDuration\": \"P99W\","
        json += "\"BlockedAuditEventDuration\": \"PT5M\","
        json += "\n\"EventRules\": [\n"
        print( json )
        for seq in self.sequences:
            seq.aeo_config()
        json = "\n]}]}\n"
        print( json )

class SequenceDefn_AEO:
    """AEO methods for Sequence Definition"""
    def aeo_config(self):
        """output AEOrdering config.json"""
        delim = ""
        for ae in self.audit_events:
            ae.aeo_config( delim )
            delim = ","

class AuditEvent_AEO:
    """AEO methods Audit Event Definition"""
    BlockedAuditEventDuration = "PT1H"                     # default for AE Simulator
    StaleAuditEventDuration = "PT2H"                       # default for AE Simulator
    def aeo_config(self, delim):
        """output AEOrdering config.json"""
        json = delim + "{ \"EventName\": \"" + self.EventName + "\","
        json += "\"OccurrenceId\": " + str( self.OccurrenceId ) + ","
        json += "\"ApplicationName\": \"" + plus_job_defn.AuditEvent.ApplicationName + "\","
        json += "\"BlockedAuditEventDuration\": \"" + AuditEvent_AEO.BlockedAuditEventDuration + "\","
        json += "\"StaleAuditEventDuration\": \"" + AuditEvent_AEO.StaleAuditEventDuration + "\""
        json += "}"
        print( json )
