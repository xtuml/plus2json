import xtuml
import time
import logging
import datetime

from xtuml import relate, navigate_many as many, navigate_one as one, navigate_any as any
from uuid import UUID

from populate import EventDataType  # TODO

logger = logging.getLogger(__name__)


def JobDefn_play(self):
    m = self.__metaclass__.metamodel

    # TODO for now, create exactly one job

    # create and link a new job
    job = m.new('Job')
    relate(job, self, 101)

    # play each sequence
    # LPS: I think this is a location where there is an implicit decision about ordering
    for seq_defn in many(self).SeqDefn[1]():
        SeqDefn_play(seq_defn, job)

    return job


def SeqDefn_play(self, job):
    # play a chain of fragments starting from the first fragment
    Fragment_play(one(self).Fragment[58](), job)


def Fragment_play(self, job, prev_evts=[]):
    sub = xtuml.navigate_subtype(self, 56)
    # TODO this can be simplified once binding is implemented
    match sub.__metaclass__.kind:
        case 'AuditEventDefn':
            evts = AuditEventDefn_play(sub, job, prev_evts)
        case 'Fork':
            evts = Fork_play(sub, job, prev_evts)
        case 'Loop':
            evts = Loop_play(sub, job, prev_evts)

    # play the next fragment or return to caller with reference to the last events
    next_frag = one(self).Fragment[57, 'precedes']()
    if next_frag:
        return Fragment_play(next_frag, job, evts)
    else:
        return evts


def AuditEventDefn_play(self, job, prev_evts):
    m = self.__metaclass__.metamodel

    # create an instance of the audit event and link it to the job
    evt = m.new('AuditEvent', TimeStamp=int(time.time() * 1000))
    relate(evt, self, 103)
    relate(evt, job, 102)
    if not one(job).AuditEvent[105]():
        relate(evt, job, 105)

    # link the event in sequence
    if len(prev_evts) > 0:
        relate(prev_evts[-1], evt, 104, 'precedes')

    # link the required previous events
    for prev_evt in prev_evts:
        relate(prev_evt, evt, 106, 'must_precede')

    # create event data for source events
    for evt_data_defn in many(self).EvtDataDefn[11]():
        evt_data = EvtDataDefn_play(evt_data_defn)
        relate(evt_data, evt, 107)

    # create event data for user events
    for evt_data_defn in many(self).EvtDataDefn[12]():
        evt_data = EvtDataDefn_play(evt_data_defn, False)
        relate(evt_data, evt, 107)

    return [evt]


def EvtDataDefn_play(self, is_source=True):
    m = self.__metaclass__.metamodel

    if is_source:
        if self.Type in (EventDataType.EINV, EventDataType.IINV):
            evt_data = m.new('EventData', Value=str(next(m.id_generator)), IsSource=True)
            relate(evt_data, self, 108)
            if self.Type == EventDataType.EINV:
                pass  # TODO persist the extra-job invariant
        else:
            pass  # TODO dynamic controls

    else:
        if self.Type in (EventDataType.EINV, EventDataType.IINV):
            src_evt_data = any(self).EventData[108](lambda sel: sel.IsSource)
            if not src_evt_data:
                pass  # TODO warn
            evt_data = m.new('EventData', Value=src_evt_data.Value, IsSource=False)
            relate(evt_data, self, 108)
            # TODO consider EINV
        else:
            pass  # TODO dynamic controls

    return evt_data


def Fork_play(self, job):
    pass


def Loop_play(self, job):
    pass


def Job_pretty_print(self):
    # print the job name
    logger.info(f'job: {one(self).JobDefn[101]().Name}: {self.Id}')

    # print each event
    evt = one(self).AuditEvent[105]()
    while evt is not None:
        AuditEvent_pretty_print(evt)
        evt = one(evt).AuditEvent[104, 'precedes']()


def Job_json(self):
    j = []
    evt = one(self).AuditEvent[105]()
    while evt is not None:
        j.append(AuditEvent_json(evt))
        evt = one(evt).AuditEvent[104, 'precedes']()
    return j


def AuditEvent_pretty_print(self):
    evt_defn = one(self).AuditEventDefn[103]()
    prev_ids = ', '.join(map(lambda e: str(e.Id), many(self).AuditEvent[106, 'must_follow']()))
    logger.info(f'evt: {evt_defn.Name}({evt_defn.OccurrenceId}): {self.Id} prev_ids: {prev_ids}')
    for evt_data in many(self).EventData[107]():
        EventData_pretty_print(evt_data)


def id_to_str(id):
    return str(UUID(int=id)) if isinstance(id, int) else str(id)


def AuditEvent_json(self):
    j = {}
    j['jobId'] = id_to_str(one(self).job[102]().Id)
    j['jobName'] = one(self).job[102].JobDefn[101]().Name
    j['eventType'] = one(self).AuditEventDefn[103]().Name
    j['eventId'] = id_to_str(self.Id)
    j['timestamp'] = datetime.datetime.utcfromtimestamp(self.TimeStamp / 1000).isoformat()
    j['previousEventIds'] = list(map(lambda e: id_to_str(e.Id), many(self).AuditEvent[106, 'must_follow']()))
    for evt_data in many(self).EventData[107]():
        j.update(EventData_json(evt_data))
    return j


def EventData_pretty_print(self):
    logger.info(f'  data: {one(self).EvtDataDefn[108]().Name}={self.Value}')


def EventData_json(self):
    val = int(self.Value) if one(self).EvtDataDefn[108]().Type in (EventDataType.BCNT, EventDataType.MCNT, EventDataType.LCNT) else self.Value
    return {one(self).EvtDataDefn[108]().Name: val}
