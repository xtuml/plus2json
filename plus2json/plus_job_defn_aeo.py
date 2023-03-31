"""

Support Audit Event Ordering (AEO) configuration.

"""

import datetime
import sys
from os.path import abspath
from pathlib import Path
package_path = abspath(Path(__file__).parent)
sys.path.insert(0, package_path)
import plus_job_defn

# Here, methods are defined to ease the configuration of the AEOrdering
# domain.  Reasonable defaults and placeholders are provided based upon
# the input job definition.

class JobDefn_AEO:
    """AEO methods for JobDefn"""
    @classmethod
    def aeo_config_all(cls):
        """output AEOrdering config.json"""
        j = """
        { "SpecUpdateRate": "PT2M",
          "MaxOutOfSequenceEvents": 10,
          "MaximumJobTime": "PT10M",
          "JobCompletePeriod": "PT24H",
          "IncomingDirectory": "incoming",
          "ProcessingDirectory": "processing",
          "ProcessedDirectory": "processed",
          "EventThrottleRate": "PT0S",
          "ReceptionDeletionTime": "PT10M",
          "ConcurrentReceptionLimit": 1,
          "JobStoreLocation": "./JobIdStore",
          "JobStoreAgeLimit": "P7D",
          "InvariantStoreLoadRate": "PT2M",
          "Jobs": [
        """
        for job_defn in plus_job_defn.JobDefn.instances:
            j += job_defn.aeo_config()
        j += "]}"
        return j
    def aeo_config(self):
        """output AEOrdering json"""
        j = '{ "JobDefinitionName": "' + self.JobDefinitionName + '",' + """
                "JobDeprecated": false,
                "JobTypeExpiryDate": "2022-04-11T18:08:00Z",
                "StaleAuditEventDuration": "P99W",
                "BlockedAuditEventDuration": "PT5M",
                "EventRules": [
               """
        for seq in self.sequences:
            j += seq.aeo_config()
        j += ']}'
        return j

class SequenceDefn_AEO:
    """AEO methods for Sequence Definition"""
    def aeo_config(self):
        """output Sequence AEOrdering json"""
        # Generate only a single event with default parameters.  The user can duplicate to make more.
        return self.start_events[0].aeo_config( "" )

class AuditEvent_AEO:
    """AEO methods Audit Event Definition"""
    BlockedAuditEventDuration = "PT1H"                     # default for AEO
    StaleAuditEventDuration = "PT2H"                       # default for AEO
    def aeo_config(self, delim):
        """output AuditEvent AEOrdering json"""
        j = delim + '{ "EventName": "' + self.EventName + '",'
        j += '"OccurrenceId": ' + str( self.OccurrenceId ) + ','
        j += '"ApplicationName": "' + plus_job_defn.AuditEvent.ApplicationName + '",'
        j += '"BlockedAuditEventDuration": "' + AuditEvent_AEO.BlockedAuditEventDuration + '",'
        j += '"StaleAuditEventDuration": "' + AuditEvent_AEO.StaleAuditEventDuration + '"'
        j += '}'
        return j
