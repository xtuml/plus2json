"""

Pretty print the PLUS job definition.

"""

import logging
import json

from xtuml import navigate_many as many, navigate_one as one, navigate_any as any

from .populate import EventDataType  # TODO

logger = logging.getLogger(__name__)

# These mixin classes supply methods for pretty-printing the
# job definition in a way that makes it understandable.  It is
# meant to help a user confirm that the job definition is set
# up correctly.


def JobDefn_pretty_print(self):
    logger.info(f'job defn: {self.Name}')
    if self.Config_JSON:
        js = json.dumps(json.loads(self.Config_JSON))
        logger.info(f'config JSON: {js[1:-1]}')
    for seq in many(self).SeqDefn[1]():
        SeqDefn_pretty_print(seq)
    for pkg in many(self).PkgDefn[20]():
        PkgDefn_pretty_print(pkg)


def SeqDefn_pretty_print(self):
    logger.info(f'sequence: {self.Name}')
    for ae in many(self).AuditEventDefn[2]():
        AuditEventDefn_pretty_print(ae)


def AuditEventDefn_pretty_print(self):
    ss = 'start' if one(self).SeqDefn[13]() else ''
    se = 'end' if one(self).SeqDefn[15]() else ''
    b = 'break' if self.IsBreak else '     '
    c = 'critical' if self.IsCritical else '        '
    bcnt = ''
    lcnt = ''
    mcnt = ''
    dcs = many(self).EvtDataDefn[11](lambda sel: sel.Type in (EventDataType.BCNT, EventDataType.LCNT, EventDataType.MCNT))
    for dc in dcs:
        su = f's={one(dc).AuditEventDefn[11]().Name}({one(dc).AuditEventDefn[11]().OccurrenceId})'
        su += f'u={any(dc).AuditEventDefn[12]().Name}({any(dc).AuditEventDefn[12]().OccurrenceId})'
        if dc.Type == EventDataType.BCNT:
            bcnt += f' bc:{dc.Name}-{su}'
        elif dc.Type == EventDataType.MCNT:
            mcnt += f' mc:{dc.Name}-{su}'
        else:
            lcnt += f' lc:{dc.Name}-{su}'
    einv = ''
    iinv = ''
    invs = many(self).EvtDataDefn[11](lambda sel: sel.Type in (EventDataType.IINV, EventDataType.EINV))
    for inv in invs:
        if inv.Type == EventDataType.EINV:
            einv += f' s-einv:{inv.Name}'
        else:
            iinv += f' s-iinv:{inv.Name}'
    invs = many(self).EvtDataDefn[12](lambda sel: sel.Type in (EventDataType.IINV, EventDataType.EINV))
    for inv in invs:
        if inv.Type == EventDataType.EINV:
            einv += f' u-einv:{inv.Name}'
        else:
            iinv += f' u-iinv:{inv.Name}'

    def map_prev_ae(prev_ae):
        ae = one(prev_ae).AuditEventDefn[3, 'follows']()
        s = f'{ae.Name}({ae.OccurrenceId})'
        const_defn = one(prev_ae).ConstDefn[16]()
        if const_defn:
            s += f' {const_defn.Id[:4]} {const_defn.Type.name}'
        return s

    prev_aes = '    ' + ','.join(sorted(map(map_prev_ae, many(self).EvtSucc[3, 'follows']())))
    longest_name_length = max(map(lambda sel: len(sel.Name), self.__metaclass__.select_many()))
    name = f'{self.Name}({self.OccurrenceId})'
    configjson = ''
    if self.Config_JSON:
        configjson = json.dumps(json.loads(self.Config_JSON))
    logger.info(f'{name:{longest_name_length+3}} {ss:{5}} {se:{3}} {b} {c} {prev_aes} {bcnt} {mcnt} {lcnt} {einv} {iinv} {configjson}')

def PkgDefn_pretty_print(self):
    logger.info(f'package: {self.Name}')
    for ue in many(self).UnhappyEventDefn[21]():
        UnhappyEventDefn_pretty_print(ue)

def UnhappyEventDefn_pretty_print(self):
    logger.info(f'unhappy event: {self.Name}')
