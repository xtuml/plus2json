import xtuml
import time
import logging
import csv

from datetime import datetime, timedelta

from xtuml import relate, delete, navigate_many as many, navigate_one as one, navigate_any as any
from uuid import UUID

from .populate import EventDataType  # TODO
from .populate import ConstraintType  # TODO

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
        # TODO get the branch count
        # this is a very limited implementation that will fail if the fragment is a loop or fork
        # this also does not support merge -- it will go to the end of the current tine or sequence
        prev_evts = evts
        evts = []
        bcnt = any(any(self).AuditEventDefn[56].EvtDataDefn[12](lambda sel: sel.Type == EventDataType.BCNT)).EventData[108](lambda sel: sel.IsSource)
        for i in range(int(bcnt.Value) if bcnt else 1):
            evts.extend(Fragment_play(next_frag, job, prev_evts))

    return evts


def AuditEventDefn_play(self, job, prev_evts):
    m = self.__metaclass__.metamodel

    # get the last event in the job
    last_evt = any(job).AuditEvent[102](lambda sel: not one(sel).AuditEvent[104, 'precedes']())

    # create an instance of the audit event and link it to the job
    evt = m.new('AuditEvent', TimeStamp=time.time())
    relate(evt, self, 103)
    relate(evt, job, 102)
    if not one(job).AuditEvent[105]():
        relate(evt, job, 105)

    # link the event in order
    if last_evt:
        relate(last_evt, evt, 104, 'precedes')

    # link the required previous events
    for prev_evt in prev_evts:
        relate(prev_evt, evt, 106, 'must_precede')

    # create event data for source events
    for evt_data_defn in many(self).EvtDataDefn[11]():
        evt_data = EvtDataDefn_play(evt_data_defn)
        relate(evt_data, evt, 107)

    # create event data for user events
    for evt_data_defn in many(self).EvtDataDefn[12](lambda sel: sel.Type in (EventDataType.EINV, EventDataType.IINV)):
        evt_data = EvtDataDefn_play(evt_data_defn, False)
        relate(evt_data, evt, 107)

    return [evt]


def EvtDataDefn_play(self, is_source=True):
    m = self.__metaclass__.metamodel
    evt_data = None

    if is_source:
        if self.Type in (EventDataType.EINV, EventDataType.IINV):
            evt_data = m.new('EventData', Value=str(next(m.id_generator)), Creation=time.time(), Expiration=(time.time() + timedelta(days=30).total_seconds()), IsSource=True)
            relate(evt_data, self, 108)
            if self.Type == EventDataType.EINV:
                EventData_persist(evt_data)
        else:
            # use the magic number 4 for all dynamic controls
            evt_data = m.new('EventData', Value=str(4), Creation=time.time(), Expiration=(time.time() + timedelta(days=30).total_seconds()), IsSource=True)
            relate(evt_data, self, 108)

    else:
        if self.Type in (EventDataType.EINV, EventDataType.IINV):
            # create a new dataum
            evt_data = m.new('EventData', IsSource=False)
            relate(evt_data, self, 108)

            # try to get the value from the source
            if self.Type == EventDataType.EINV:
                src_evt_data = any(self).EvtDataDefn[18, 'corresponds_to'].EventData[108](lambda sel: sel.IsSource)
            else:
                src_evt_data = any(self).EventData[108](lambda sel: sel.IsSource)

            # update the event data from the source
            if src_evt_data:
                evt_data.Value = src_evt_data.Value
                evt_data.Creation = src_evt_data.Creation
                evt_data.Expiration = src_evt_data.Expiration
            elif self.Type == EventDataType.EINV:
                # try to load from store
                EventData_load(evt_data)
            else:
                logger.warning(f'Unable to find exiting invariant value for invariant "{self.Name}"')

    return evt_data


def Fork_play(self, job, prev_evts=[]):
    if self.Type == ConstraintType.XOR:
        # TODO arbitrarily choose the first tine
        return Tine_play(any(self).Tine[54](), job, prev_evts)

    elif self.Type == ConstraintType.AND:
        # play all tines
        evts = []
        for tine in many(self).Tine[54]():
            evts.extend(Tine_play(tine, job, prev_evts))
        return evts

    elif self.Type == ConstraintType.IOR:
        # TODO arbitrarily choose the first tine
        return Tine_play(any(self).Tine[54](), job, prev_evts)

    else:
        return []


def Loop_play(self, job, prev_evts=[]):
    # there will be exactly one loop count user in the tine of the loop
    lcnts = many(self).Tine[55].Fragment[59].AuditEventDefn[56].EvtDataDefn[12](lambda sel: sel.Type == EventDataType.LCNT)
    if len(lcnts) > 1:
        logger.warning(f'Loop has more than one loop count data definition: {len(lcnts)}')
        return []
    lcnt = any(lcnts).EventData[108](lambda sel: sel.IsSource)

    # play the loop the number of times
    for i in range(int(lcnt.Value) if lcnt else 1):
        evts = Tine_play(one(self).Tine[55](), job, prev_evts)
        prev_evts = evts
    return evts


def Tine_play(self, job, prev_evts=[]):
    # play starting with the first fragment
    evts = Fragment_play(one(self).Fragment[51](), job, prev_evts)
    return evts if not self.IsTerminal else []


def Job_pretty_print(self):
    # print the job name
    logger.info(f'job: {one(self).JobDefn[101]().Name}: {self.Id}')

    # print each event
    evt = one(self).AuditEvent[105]()
    while evt is not None:
        AuditEvent_pretty_print(evt)
        evt = one(evt).AuditEvent[104, 'precedes']()


def Job_json(self, dispose=False):
    j = []
    evt = one(self).AuditEvent[105]()
    while evt is not None:
        j.append(AuditEvent_json(evt))
        evt = one(evt).AuditEvent[104, 'precedes']()
    if dispose:
        Job_dispose(self)
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
    j['timestamp'] = datetime.utcfromtimestamp(self.TimeStamp).isoformat() + 'Z'
    j['applicationName'] = 'default_application_name'  # backwards compatibility
    prev_evts = many(self).AuditEvent[106, 'must_follow']()
    if len(prev_evts) > 0:
        j['previousEventIds'] = list(map(lambda e: id_to_str(e.Id), prev_evts))
    for evt_data in many(self).EventData[107]():
        j.update(EventData_json(evt_data))
    return j


def EventData_pretty_print(self):
    logger.info(f'  data: {self.Name}={self.Value}')


def EventData_json(self):
    val = int(self.Value) if one(self).EvtDataDefn[108]().Type in (EventDataType.BCNT, EventDataType.MCNT, EventDataType.LCNT) else self.Value
    return {self.Name: val}


def EventData_persist(self, filename='p2jInvariantStore'):  # TODO filename
    evt_data_defn = one(self).EvtDataDefn[108]()
    row = (evt_data_defn.Name, self.Value, datetime.utcfromtimestamp(self.Creation).isoformat() + 'Z', datetime.utcfromtimestamp(self.Expiration).isoformat() + 'Z', evt_data_defn.SourceJobDefnName, '', '')
    try:
        with open(filename, 'a') as f:
            writer = csv.writer(f)
            writer.writerow(row)
    except IOError:
        logger.warning(f'Could not write to invariant store: {filename}')
        logger.debug('', exc_info=True)


def EventData_load(self, filename='p2jInvariantStore'):  # TODO filename
    evt_data_defn = one(self).EvtDataDefn[108]()
    try:
        with open(filename) as f:
            reader = csv.reader(f)
            for row in reader:
                if row[0] == evt_data_defn.Name and row[4] == evt_data_defn.SourceJobDefnName:
                    self.Value = row[1]
                    self.Creation = datetime.fromisoformat(row[2][:-1]).timestamp()
                    self.Expiration = datetime.fromisoformat(row[3][:-1]).timestamp()
                    return True
            logger.warning(f'Did not find invariant value for "{evt_data_defn.Name}" in store')
            return False

    except IOError:
        logger.warning(f'Unable to load invariant file: {filename}')
        logger.debug('', exc_info=True)


def Job_dispose(self):
    for evt in many(self).AuditEvent[102]():
        AuditEvent_dispose(evt)
    delete(self, disconnect=True)


def AuditEvent_dispose(self):
    for data in many(self).EventData[107]():
        delete(data, disconnect=True)
    delete(self, disconnect=True)
