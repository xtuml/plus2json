import json
from xtuml import navigate_many as many, navigate_one as one, navigate_any as any

from .populate import EventDataType  # TODO
from .populate import ConstraintType  # TODO


def JobDefn_json(self):
    j = {}
    j['JobDefinitionName'] = self.Name
    if self.Config_JSON:
        j.update(json.loads(self.Config_JSON).items())
    j['Events'] = list(map(AuditEventDefn_json, many(self).SeqDefn[1].AuditEventDefn[2]()))
    if any(self).PkgDefn[20]():
        j['UnhappyEvents'] = list(map(UnhappyEventDefn_json, many(self).PkgDefn[20].UnhappyEventDefn[21]()))
    return j


def AuditEventDefn_json(self):
    j = {}

    # basic information
    j['EventName'] = self.Name
    j['OccurrenceId'] = self.OccurrenceId
    j['SequenceName'] = one(self).SeqDefn[2]().Name
    j['Application'] = 'default_application_name'  # backward compatibility
    if self.Config_JSON:
        j.update(json.loads(self.Config_JSON).items())

    # event features
    if one(self).SeqDefn[13]():
        j['SequenceStart'] = True
    if one(self).SeqDefn[15]():
        j['SequenceEnd'] = True
    if self.IsBreak:
        j['IsBreak'] = True
    if self.IsCritical:
        j['IsCritical'] = True

    # dynamic controls
    dcs = many(self).EvtDataDefn[11](lambda sel: sel.Type in (EventDataType.BCNT, EventDataType.LCNT, EventDataType.MCNT))
    if len(dcs) > 0:
        j['DynamicControl'] = list(map(EvtDataDefn_json, dcs))

    # previous events
    evt_succs = many(self).EvtSucc[3, 'follows']()
    if len(evt_succs) > 0:
        j['PreviousEvents'] = list(map(EvtSucc_json, evt_succs))

    # invariants
    sinvs = many(self).EvtDataDefn[11](lambda sel: sel.Type in (EventDataType.IINV, EventDataType.EINV))
    uinvs = many(self).EvtDataDefn[12](lambda sel: sel.Type in (EventDataType.IINV, EventDataType.EINV))
    if len(sinvs) + len(uinvs) > 0:
        j['EventData'] = list(map(EvtDataDefn_json, sinvs)) + list(map(lambda inv: EvtDataDefn_json(inv, is_source=False), uinvs))

    return j


def EvtSucc_json(self):
    j = {}

    prev_evt = one(self).AuditEventDefn[3, 'follows']()
    j['PreviousEventName'] = prev_evt.Name
    j['PreviousOccurrenceId'] = prev_evt.OccurrenceId

    const_defn = one(self).ConstDefn[16]()
    if const_defn:
        j['ConstraintDefinitionId'] = const_defn.Id
        j['ConstraintValue'] = const_defn.Type.name

    return j


def EvtDataDefn_json(self, is_source=True):
    j = {}

    # handle dynamic controls
    if self.Type in (EventDataType.BCNT, EventDataType.MCNT, EventDataType.LCNT):
        j['DynamicControlName'] = self.Name
        if self.Type == EventDataType.BCNT:
            j['DynamicControlType'] = 'BRANCHCOUNT'
        elif self.Type == EventDataType.MCNT:
            j['DynamicControlType'] = 'MERGECOUNT'
        else:
            j['DynamicControlType'] = 'LOOPCOUNT'
        user_evt = any(self).AuditEventDefn[12]()
        j['UserEventType'] = user_evt.Name
        j['UserOccurrenceId'] = user_evt.OccurrenceId

    # handle invariants
    else:
        j['EventDataName'] = self.Name
        if self.Type == EventDataType.EINV:
            j['EventDataType'] = 'EXTRAJOBINV'
        else:
            j['EventDataType'] = 'INTRAJOBINV'
        if not is_source:  # if this is a user event data definition, specify the source
            j['SourceEventDataName'] = self.Name
            if self.Type == EventDataType.EINV:  # if this is an extra job invariant, specify the source job definition
                j['SourceJobDefinitionName'] = self.SourceJobDefnName
            else:
                src_evt = one(self).AuditEventDefn[11]()
                j['SourceEventType'] = src_evt.Name
                j['SourceEventOccurrenceId'] = src_evt.OccurrenceId

    return j

def UnhappyEventDefn_json(self):
    j = {}

    # basic information
    j['EventName'] = self.Name
    j['PackageName'] = one(self).PkgDefn[21]().Name
    j['Application'] = 'default_application_name'  # backward compatibility

    return j
