"""

Support Audit Event Simulator (AESim) configuration.

"""

import datetime
import sys
from os.path import abspath
from pathlib import Path
package_path = abspath(Path(__file__).parent)
sys.path.insert(0, package_path)
import plus_job_defn

# Here, methods are defined to ease the configuration of the AESimulator
# domain.  Reasonable defaults and placeholders are provided based upon
# the input PLUS job definition.

class JobDefn_AESim:
    """AESim methods for JobDefn"""
    def aesim_config_begin(self):
        """begin output AESimulator Job Specification JSON"""
        j = '{ "JobSpecName": "scenario1",'
        j += '"JobName": "' + self.JobDefinitionName + '",'
        j += '"EventDefinition": ['
        return j
    def aesim_config_end(self):
        """end output AESimulator Job Specification JSON"""
        return ']}'

class SequenceDefn_AESim:
    """AESim methods for Sequence Definition"""
    pass

class AuditEventDefn_AESim:
    """AESim methods Audit Event Definition"""
    DispatchDelay = "PT0S"                                 # default for AE Simulator
    NodeName = "default_node_name"                         # default for AE Simulator
    def aesim_config( self, delim ):
        """output AEOrdering config.json"""
        j = delim + "{ \"EventId\": \"" + str( self.eventId ) + "\","
        # Link to previous event if not starting a sequence.
        if self.previousEventIds:
            j += '"PreviousEventId": "' + str( self.previousEventIds[-1] ) + '",'
        j += '"EventName": "' + self.EventName + '",'
        j += '"SequenceStart": '
        j += '"true",' if self.SequenceStart else '"false",'
        # look for linked Invariants
        event_data = ""
        delim = ""
        # select many invs related by self->Invariant[R11]
        invs = [inv for inv in plus_job_defn.Invariant.instances if inv.R11_AuditEventDefn is self]
        for inv in invs:
            # For EINV there may be a source and no user.
            value = ""
            if inv.R12_AuditEventDefn:
                value = (
                    inv.Type + 's-' + self.EventName +
                    '(' + self.OccurrenceId + ')' +
                    'u-' + inv.R12_AuditEventDefn[0].EventName + "?" +
                    '(' + inv.R12_AuditEventDefn[0].OccurrenceId + ')'
                )
            name = inv.Name
            event_data += delim + '{ "DataName": "' + name + '", "DataValue": "' + value + '"}'
            delim = ','
        # select many invs related by self->Invariant[R12]
        invs = [inv for inv in plus_job_defn.Invariant.instances if self in inv.R12_AuditEventDefn]
        for inv in invs:
            # For EINV there may be a user and no source.
            value = ""
            if inv.R12_AuditEventDefn:
                value = (
                    inv.Type + 's-' + inv.R11_AuditEventDefn.EventName +
                    '(' + inv.R11_AuditEventDefn.OccurrenceId + ')' +
                    'u-' + self.EventName +
                    '(' + self.OccurrenceId + ')'
                )
            name = inv.Name
            event_data += delim + '{ "DataName": "' + name + '", "DataValue": "' + value + '"}'
            delim = ','
        if "" != event_data:
            j += '"EventData": [' + event_data + '],'
        j += '"NodeName": "' + AuditEventDefn_AESim.NodeName + '",'
        j += '"ApplicationName": "' + plus_job_defn.AuditEventDefn.ApplicationName + '"'
        j += '}'
        return j
