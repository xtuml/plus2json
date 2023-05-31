"""

Pretty print the PLUS job definition.

"""

import sys

from xtuml import navigate_many as many, navigate_one as one, navigate_any as any
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
    dcs = many(self).EvtDataDefn[11](lambda sel: sel.Type in (EventDataType.BCNT, EventDataType.LCNT, EventDataType.MCNT))
    for dc in dcs:
        su = "s=" + one(dc).AuditEventDefn[11]().Name + "(" + str(one(dc).AuditEventDefn[11]().OccurrenceId) + ")"
        su += "u=" + any(dc).AuditEventDefn[12]().Name + "(" + str(any(dc).AuditEventDefn[12]().OccurrenceId) + ")"
        if dc.Type == EventDataType.BCNT:
            bcnt += "bc:" + dc.Name + "-" + su
        elif dc.Type == EventDataType.MCNT:
            mcnt += "mc:" + dc.Name + "-" + su
        elif dc.Type == EventDataType.LCNT:
            lcnt += "lc:" + dc.Name + "-" + su
        else:
            print( "ERROR:  malformed dynamic control" )
            sys.exit()
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

    def map_prev_ae(prev_ae):
        ae = one(prev_ae).AuditEventDefn[3, "follows"]()
        s = f'{ae.Name}({ae.OccurrenceId})'
        const_defn = one(prev_ae).ConstDefn[16]()
        if const_defn:
            s += f' {const_defn.Id[:4]} {const_defn.Type.name}'
        return s

    prev_aes = '    ' + ','.join(sorted(map(map_prev_ae, many(self).EvtSucc[3, 'follows']())))
    longest_name_length = max(map(lambda sel: len(sel.Name), self.__metaclass__.select_many()))
    print(f'{self.Name+"("+str(self.OccurrenceId)+")":{longest_name_length+3}}', f'{ss:{5}}', f'{se:{3}}', b, prev_aes, bcnt, mcnt, lcnt, einv, iinv)
