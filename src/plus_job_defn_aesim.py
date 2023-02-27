"""

Support Audit Event Simulator (AESim) configuration.

"""

import datetime
import plus_job_defn

# Here, methods are defined to ease the configuration of the AESimulator
# domain.  Reasonable defaults and placeholders are provided based upon
# the input PLUS job definition.

class JobDefn_AESim:
    """AESim methods for JobDefn"""
    def aesim_config(self):
        """output AESimulator Job Specification JSON"""
        json = "{ \"JobSpecName\": " + self.JobDefinitionName + ","
        json += "\"EventDefinition\": [\n"
        print( json )
        return "\n]}\n"

class SequenceDefn_AESim:
    """AESim methods for Sequence Definition"""
    pass

class AuditEvent_AESim:
    """AESim methods Audit Event Definition"""
    DispatchDelay = "PT0S"                                 # default for AE Simulator
    NodeName = "default_node_name"                         # default for AE Simulator
    def aesim_config(self, delim):
        """output AEOrdering config.json"""
        # Calculate a small but unique number of event ID.
        # TODO - store this for reference as previous event
        event_id = 10 * ( plus_job_defn.AuditEvent.instances.index( self ) + 1 ) + self.visit_count
        json = delim + "{ \"EventId\": \"" + str( event_id ) + "\","
        json += "\"EventName\": \"" + self.EventName + "\","
        json += "\"NodeName\": \"" + AuditEvent_AESim.NodeName + "\","
        json += "\"SequenceStart\": "
        json += "\"true\"," if self.SequenceStart else "\"false\","
        json += "\"ApplicationName\": \"" + plus_job_defn.AuditEvent.ApplicationName + "\""
        json += "}"
        print( json )
