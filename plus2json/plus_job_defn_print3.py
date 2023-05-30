"""

Pretty print the PLUS job definition.

"""

import sys

from xtuml import navigate_many as many, navigate_one as one
from populate import EventDataType  # TODO

# These mixin classes supply methods for pretty-printing the
# job definition in a way that makes it understandable.  It is
# meant to help a user confirm that the job definition is set
# up correctly.


def JobDefn_pretty_print(self):
    print("job defn:", self.Name)
    for seq in many(self).SeqDefn[1]():
        SeqDefn_pretty_print(seq)


def SeqDefn_pretty_print(self):
    print("sequence:", self.Name)
    for ae in many(self).AuditEventDefn[2]():
        AuditEventDefn_pretty_print(ae)


def AuditEventDefn_pretty_print(self):
    ss = "start" if one(self).SeqDefn[13]() else ""
    se = "end" if one(self).SeqDefn[15]() else ""
    b = "break" if self.IsBreak else "     "
    # look for linked DynamicControls
    bcnt = ""
    lcnt = ""
    mcnt = ""
    # dcs = many(self).EvtDataDefn[12](lambda sel: sel.Type in (EventDataType.BCNT, EventDataType.LCNT, EventDataType.MCNT))
    # for dc in dcs:
    #     su = "s=" + dc.src_evt_txt + "(" + dc.src_occ_txt + ")"
    #     su += "u=" + dc.user_evt_txt + "(" + dc.user_occ_txt + ")"
    #     if dc.DynamicControlType == "BRANCHCOUNT":
    #         bcnt += "bc:" + dc.DynamicControlName + "-" + su
    #     elif dc.DynamicControlType == "MERGECOUNT":
    #         mcnt += "mc:" + dc.DynamicControlName + "-" + su
    #     elif dc.DynamicControlType == "LOOPCOUNT":
    #         lcnt += "lc:" + dc.DynamicControlName + "-" + su
    #     else:
    #         print( "ERROR:  malformed dynamic control" )
    #         sys.exit()
    # look for linked Invariant
    einv = ""
    iinv = ""
    invs = many(self).EvtDataDefn[11](lambda sel: sel.Type in (EventDataType.IINV, EventDataType.EINV))
    for inv in invs:
        if inv.Type == EventDataType.EINV:
            einv += " s-einv:" + inv.Name
        elif inv.Type == EventDataType.IINV:
            iinv += " s-iinv:" + inv.Name
        else:
            print("ERROR:  malformed invariant type")
            sys.exit()
    invs = many(self).EvtDataDefn[12](lambda sel: sel.Type in (EventDataType.IINV, EventDataType.EINV))
    for inv in invs:
        if inv.Type == EventDataType.EINV:
            einv += " u-einv:" + inv.Name
        elif inv.Type == EventDataType.IINV:
            iinv += " u-iinv:" + inv.Name
        else:
            print("ERROR:  malformed invariant type")
            sys.exit()
    prev_aes = '    ' + ','.join(map(lambda prev_ae: f'{one(prev_ae).AuditEventDefn[3, "follows"]().Name}({one(prev_ae).AuditEventDefn[3, "follows"]().OccurrenceId})', many(self).EvtSucc[3, 'follows']()))
    longest_name_length = max(map(lambda sel: len(sel.Name), self.__metaclass__.select_many()))
    print(f'{self.Name+"("+str(self.OccurrenceId)+")":{longest_name_length+3}}', f'{ss:{5}}', f'{se:{3}}', b, prev_aes, bcnt, mcnt, lcnt, einv, iinv)
