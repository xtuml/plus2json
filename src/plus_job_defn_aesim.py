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
    def aesim_config( self, delim ):
        """output AEOrdering config.json"""
        json = delim + "{ \"EventId\": \"" + str( self.eventId ) + "\","
        # Link to previous event if not starting a sequence.
        if self.previousEventIds:
            json += "\"PreviousEventId\": \"" + str( self.previousEventIds[-1] ) + "\","
        json += "\"EventName\": \"" + self.EventName + "\","
        json += "\"SequenceStart\": "
        json += "\"true\"," if self.SequenceStart else "\"false\","
        # look for linked Invariant
        event_data = ""
        delim = ""
        inv = [inv for inv in plus_job_defn.Invariant.instances if inv.source_event is self]
        if inv:
            value = (
                inv[-1].Type + "s-" + inv[-1].src_evt_txt +
                "(" + inv[-1].src_occ_txt + ")" +
                "u-" + inv[-1].user_evt_txt +
                "(" + inv[-1].user_occ_txt + ")"
            )
            name = inv[-1].Name
            event_data += "{ \"DataName\": \"" + name + "\", \"DataValue\": \"" + value + "\"}"
            delim = ","
        inv = [inv for inv in plus_job_defn.Invariant.instances if self in inv.user_events]
        if inv:
            value = (
                inv[-1].Type + "s-" + inv[-1].src_evt_txt +
                "(" + inv[-1].src_occ_txt + ")" +
                "u-" + inv[-1].user_evt_txt +
                "(" + inv[-1].user_occ_txt + ")"
            )
            name = inv[-1].Name
            event_data += delim + "{ \"DataName\": \"" + name + "\", \"DataValue\": \"" + value + "\"}"
        if "" != event_data:
            json += "\"EventData\": [" + event_data + "],"
        json += "\"NodeName\": \"" + AuditEvent_AESim.NodeName + "\","
        json += "\"ApplicationName\": \"" + plus_job_defn.AuditEvent.ApplicationName + "\""
        json += "}"
        print( json )
