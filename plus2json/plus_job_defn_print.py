"""

Pretty print the PLUS job definition.

"""

import sys
from os.path import abspath
from pathlib import Path
package_path = abspath(Path(__file__).parent)
sys.path.insert(0, package_path)
import plus_job_defn

# These mixin classes supply methods for pretty-printing the
# job definition in a way that makes it understandable.  It is
# meant to help a user confirm that the job definition is set
# up correctly.

class JobDefn_print:
    """Print Job Definition"""
    def pretty_print(self):
        print("job defn:", self.JobDefinitionName)
        for seq in self.R1_SequenceDefn_defines:
            seq.pretty_print()

class SequenceDefn_print:
    """Print Sequence Definition"""
    def pretty_print(self):
        print("sequence:", self.SequenceName)
        for ae in self.R2_AuditEventDefn_defines:
            ae.pretty_print()

class AuditEventDefn_print:
    """Print Audit Event Definition"""
    def pretty_print(self):
        ss = "start" if self.SequenceStart else ""
        se = "end" if self.SequenceEnd else ""
        b = "break" if self.isBreak else "     "
        # look for linked DynamicControls
        bcnt = ""
        lcnt = ""
        mcnt = ""
        dcs = [dc for dc in plus_job_defn.DynamicControl.instances if dc.R9_AuditEventDefn is self]
        for dc in dcs:
            su = "s=" + dc.src_evt_txt + "(" + dc.src_occ_txt + ")"
            su += "u=" + dc.user_evt_txt + "(" + dc.user_occ_txt + ")"
            if dc.DynamicControlType == "BRANCHCOUNT":
                bcnt += "bc:" + dc.DynamicControlName + "-" + su
            elif dc.DynamicControlType == "MERGECOUNT":
                mcnt += "mc:" + dc.DynamicControlName + "-" + su
            elif dc.DynamicControlType == "LOOPCOUNT":
                lcnt += "lc:" + dc.DynamicControlName + "-" + su
            else:
                print( "ERROR:  malformed dynamic control" )
                sys.exit()
        # look for linked Invariant
        einv = ""
        iinv = ""
        # select many invs related by self->Invariant[R11]
        invs = [inv for inv in plus_job_defn.Invariant.instances if inv.R11_AuditEventDefn is self]
        for inv in invs:
            if inv.Type == "EINV":
                einv += " s-einv:" + inv.Name
            elif inv.Type == "IINV":
                iinv += " s-iinv:" + inv.Name
            else:
                print( "ERROR:  malformed invariant type" )
                sys.exit()
        # select many invs related by self->Invariant[R12]
        invs = [inv for inv in plus_job_defn.Invariant.instances if self in inv.R12_AuditEventDefn]
        for inv in invs:
            if inv.Type == "EINV":
                einv += " u-einv:" + inv.Name
            elif inv.Type == "IINV":
                iinv += " u-iinv:" + inv.Name
            else:
                print( "ERROR:  malformed invariant type" )
                sys.exit()
        prev_aes = "    "
        delim = ""
        for prev_ae in self.R3_PreviousAuditEventDefn:
            prev_aes = ( prev_aes + delim + prev_ae.R3_AuditEventDefn_precedes.EventName +
                         "(" + prev_ae.R3_AuditEventDefn_precedes.OccurrenceId + ")" +
                         prev_ae.ConstraintDefinitionId + prev_ae.ConstraintValue
                       )
            delim = ","
        print( f'{self.EventName+"("+self.OccurrenceId+")":{plus_job_defn.AuditEventDefn.c_longest_name_length+3}}',
               f'{ss:{5}}', f'{se:{3}}', b, prev_aes, bcnt, mcnt, lcnt, einv, iinv )
