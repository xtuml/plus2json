import xtuml
import time
import logging
import csv
import random

from datetime import datetime, timedelta

from xtuml import relate, delete, order_by, navigate_many as many, navigate_one as one, navigate_any as any
from uuid import UUID

from .populate import EventDataType  # TODO
from .populate import ConstraintType  # TODO
from .populate import flatten

logger = logging.getLogger(__name__)


def JobDefn_play(self):
    m = self.__metaclass__.metamodel
    opts = m.select_any('_Options')

    jobs = []
    pathways = []
    # DEBUG
    ps = many(self).Pathway[60]()
    for p in ps:
        logger.debug(f'1JobDefnName:{self.Name} Pathway:{p.Number}')
        alts = many(p).Alternative[61]()
        for alt in alts:
            logger.debug(f'2JobDefnName:{self.Name} Pathway:{p.Number} Alternative:{alt.Name}')
    # DEBUG
    # select pathway(s)
    if opts.all:
        # --play --all
        pathways = many(self).Pathway[60]()
    else:
        # --play only one pathway (the first one numerically)
        pathways.append(any(self).Pathway[60](xtuml.order_by('Number')))
    for pathway in pathways:
        # create and link a new job
        job = m.new('Job')
        jobs.append(job)
        relate(job, self, 101)
        relate(job, pathway, 104)

        # play each sequence
        for seq_defn in many(self).SeqDefn[1]():
            SeqDefn_play(seq_defn, job)

    # document graph coverage
    total_aeds = len(many(self).SeqDefn[1].AuditEventDefn[2]())
    # visited AuditEventDefns have a linked AuditEvent
    # TODO - This needs to consider unhappy events.
    visited_aeds = len(many(self).SeqDefn[1].AuditEventDefn[2](lambda sel: any(sel).AuditEvent[103]()))
    graph_coverage = visited_aeds / total_aeds * 100
    logger.info(f'JobDefnName:{self.Name} visited {visited_aeds} of {total_aeds} achieving a coverage of {graph_coverage:.1f}%')

    return jobs


def SeqDefn_play(self, job):
    # play a chain of fragments starting from the first fragment
    Fragment_play(one(self).Fragment[58](), job)


def Fragment_play(self, job, branch_count=1, prev_evts=[[]]):

    # if this event is a merge count user, divide the branch count and previous events
    # NOTE: This implementation does support nested branch/merge, however it
    # expects the merges to happen exactly as the branches but in reverse order.
    # If this assumption is violated, it may not work as expected.
    mcnt = any(any(self).AuditEventDefn[56].EvtDataDefn[12](lambda sel: sel.Type == EventDataType.MCNT)).EventData[108](lambda sel: sel.IsSource)
    if mcnt:
        branch_count = int(branch_count / int(mcnt.Value))
        prev_evts = [flatten(prev_evts[i * int(len(prev_evts) / branch_count):i * int(len(prev_evts) / branch_count) + int(len(prev_evts) / branch_count)]) for i in range(branch_count)]

    # call 'play' on the subtype
    sub = xtuml.navigate_subtype(self, 56)
    # TODO this can be simplified once binding is implemented
    match sub.__metaclass__.kind:
        case 'AuditEventDefn':
            evts = AuditEventDefn_play(sub, job, branch_count, prev_evts)
        case 'Fork':
            evts = Fork_play(sub, job, branch_count, prev_evts)
        case 'Loop':
            evts = Loop_play(sub, job, branch_count, prev_evts)

    # play the next fragment or return to caller with reference to the last events
    next_frag = one(self).Fragment[57, 'precedes']()
    if next_frag:

        # if this event is a branch count user, muliply the branch count and previoius events
        bcnt = any(any(self).AuditEventDefn[56].EvtDataDefn[12](lambda sel: sel.Type == EventDataType.BCNT)).EventData[108](lambda sel: sel.IsSource)
        if bcnt:
            branch_count *= int(bcnt.Value)
            evts *= int(bcnt.Value)

        # play the next fragment
        evts = Fragment_play(next_frag, job, branch_count, evts)

    return evts


def AuditEventDefn_play(self, job, branch_count, prev_evts):
    m = self.__metaclass__.metamodel

    evts = []
    if self.IsCritical and 0 == random.randint(0, 1):
        # critical and coin toss is tails
        # play an unhappy event instead of this critical event
        return UnhappyEventDefn_play(m.select_any('UnhappyEventDefn'), job, branch_count, prev_evts)

    for i in range(branch_count):

        # create an instance of the audit event and link it to the job
        evt = m.new('AuditEvent', TimeStamp=time.time(), SequenceNum=len(many(job).AuditEvent[102]()))
        relate(evt, self, 103)
        relate(evt, job, 102)

        # link the required previous events
        for prev_evt in prev_evts[i]:
            relate(prev_evt, evt, 106, 'must_precede')

        # create event data for source events
        for evt_data_defn in many(self).EvtDataDefn[11]():
            evt_data = EvtDataDefn_play(evt_data_defn)
            relate(evt_data, evt, 107)

        # create event data for user events
        for evt_data_defn in many(self).EvtDataDefn[12](lambda sel: sel.Type in (EventDataType.EINV, EventDataType.IINV)):
            evt_data = EvtDataDefn_play(evt_data_defn, False)
            relate(evt_data, evt, 107)

        evts.append([evt])

    return evts


def UnhappyEventDefn_play(self, job, branch_count, prev_evts):
    m = self.__metaclass__.metamodel

    evts = []

    for i in range(branch_count):

        # create an instance of the audit event and link it to the job and unhappy event definition
        evt = m.new('AuditEvent', TimeStamp=time.time(), SequenceNum=len(many(job).AuditEvent[102]()))
        relate(evt, self, 109)
        relate(evt, job, 102)

        # link the required previous events
        for prev_evt in prev_evts[i]:
            relate(prev_evt, evt, 106, 'must_precede')

        evts.append([evt])

    return evts


def EvtDataDefn_play(self, is_source=True):
    m = self.__metaclass__.metamodel
    opts = m.select_any('_Options')
    evt_data = None

    if is_source:
        source_value = opts.event_data[self.Name] if self.Name in opts.event_data else None
        if self.Type in (EventDataType.EINV, EventDataType.IINV):
            evt_data = m.new('EventData', Value=source_value or str(next(m.id_generator)), Creation=time.time(), Expiration=(time.time() + timedelta(days=30).total_seconds()), IsSource=True)
            relate(evt_data, self, 108)
            if self.Type == EventDataType.EINV:
                if not m.select_any('_Options').no_persist_einv:
                    EventData_persist(evt_data)
                else:
                    logger.warn('Not persisting external invariant value')
        else:
            # use the magic number 4 for all dynamic controls
            evt_data = m.new('EventData', Value=source_value or str(4), Creation=time.time(), Expiration=(time.time() + timedelta(days=30).total_seconds()), IsSource=True)
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
            elif self.Name in opts.event_data:
                evt_data.Value = opts.event_data[self.Name]
                evt_data.Creation = time.time()
                evt_data.Expiration = (time.time() + timedelta(days=30).total_seconds())
            elif self.Type == EventDataType.EINV:
                # try to load from store
                EventData_load(evt_data)
            else:
                logger.warning(f'Unable to find exiting invariant value for invariant "{self.Name}"')

    return evt_data


def Fork_play(self, job, branch_count, prev_evts):
    if self.Type == ConstraintType.XOR:
        # choose the tine with an alternative in our pathway
        pathway = one(job).Pathway[104]()
        for tine in many(self).Tine[54]():
            if pathway in many(tine).Alternative[63].Pathway[61]():
                return Tine_play(tine, job, branch_count, prev_evts)
        # ERROR:  report error and play any tine to avoid crashing
        logger.error(f'no eligible tine for pathway:{pathway.JobDefnName}:{pathway.Number}')
        return Tine_play(any(self).Tine[54](), job, branch_count, prev_evts)

    elif self.Type == ConstraintType.AND:
        # play all tines combining the previous event lists
        evts = [[]] * branch_count
        for tine in many(self).Tine[54]():
            evts = [a + b for a, b in zip(evts, Tine_play(tine, job, branch_count, prev_evts))]
        return evts

    elif self.Type == ConstraintType.IOR:
        # TODO arbitrarily play all tines
        evts = [[]] * branch_count
        for tine in many(self).Tine[54]():
            evts = [a + b for a, b in zip(evts, Tine_play(tine, job, branch_count, prev_evts))]
        return evts

    else:
        return [[]] * branch_count


def Loop_play(self, job, branch_count, prev_evts):
    # there will be exactly one loop count user in the tine of the loop
    lcnts = many(self).Tine[55].Fragment[59].AuditEventDefn[56].EvtDataDefn[12](lambda sel: sel.Type == EventDataType.LCNT)
    if len(lcnts) > 1:
        logger.warning(f'Loop has more than one loop count data definition: {len(lcnts)}')
        return []
    lcnt = any(lcnts).EventData[108](lambda sel: sel.IsSource)

    # play the loop the number of times
    for i in range(int(lcnt.Value) if lcnt else 1):
        evts = Tine_play(one(self).Tine[55](), job, branch_count, prev_evts)
        prev_evts = evts
    return evts


def Tine_play(self, job, branch_count, prev_evts):
    # play starting with the first fragment
    evts = Fragment_play(one(self).Fragment[51](), job, branch_count, prev_evts)
    return evts if not self.IsTerminal else [[]] * branch_count


def Job_pretty_print(self):
    # print the job name
    logger.info(f'job: {one(self).JobDefn[101]().Name}: {self.Id}')

    # print each event
    for evt in many(self).AuditEvent[102](order_by('SequenceNum')):
        AuditEvent_pretty_print(evt)


def Job_json(self, dispose=False):
    j = []
    for evt in many(self).AuditEvent[102](order_by('SequenceNum')):
        j.append(AuditEvent_json(evt))
    if dispose:
        Job_dispose(self)
    return j


def AuditEvent_pretty_print(self):
    name_occurrence = ""
    evt_defn = one(self).AuditEventDefn[103]()
    if evt_defn:
        name_occurrence = f'{evt_defn.Name}({evt_defn.OccurrenceId}):'
    else:
        uevt_defn = one(self).UnhappyEventDefn[109]()
        name_occurrence = f'{uevt_defn.Name}:'
    prev_ids = ', '.join(map(lambda e: str(e.Id), many(self).AuditEvent[106, 'must_follow']()))
    uses = ', '.join(map(lambda ed: ed.Name, many(self).AuditEventDefn[103].EvtDataDefn[12]()))
    logger.info(f'evt: {name_occurrence}: {self.Id} prev_ids: {prev_ids}{" uses: " + uses if uses else ""}')
    for evt_data in many(self).EventData[107]():
        EventData_pretty_print(evt_data)


def id_to_str(id):
    return str(UUID(int=id)) if isinstance(id, int) else str(id)


def AuditEvent_json(self):
    j = {}
    j['jobId'] = id_to_str(one(self).job[102]().Id)
    j['jobName'] = one(self).job[102].JobDefn[101]().Name
    if one(self).AuditEventDefn[103]():
        j['eventType'] = one(self).AuditEventDefn[103]().Name
    else:
        j['eventType'] = one(self).UnhappyEventDefn[109]().Name
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


def EventData_persist(self):
    m = self.__metaclass__.metamodel
    opts = m.select_any('_Options')
    evt_data_defn = one(self).EvtDataDefn[108]()
    row = (evt_data_defn.Name, self.Value, datetime.utcfromtimestamp(self.Creation).isoformat() + 'Z', datetime.utcfromtimestamp(self.Expiration).isoformat() + 'Z', evt_data_defn.SourceJobDefnName, '', '')
    try:
        with open(opts.inv_store_file, 'a') as f:
            writer = csv.writer(f)
            writer.writerow(row)
    except IOError:
        logger.warning(f'Could not write to invariant store: {opts.inv_store_file}')
        logger.debug('', exc_info=True)


def EventData_load(self):  # TODO filename
    m = self.__metaclass__.metamodel
    opts = m.select_any('_Options')
    evt_data_defn = one(self).EvtDataDefn[108]()
    try:
        with open(opts.inv_store_file) as f:
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
        logger.warning(f'Unable to load invariant file: {opts.inv_store_file}')
        logger.debug('', exc_info=True)


def Job_dispose(self):
    for evt in many(self).AuditEvent[102]():
        AuditEvent_dispose(evt)
    delete(self, disconnect=True)


def AuditEvent_dispose(self):
    for data in many(self).EventData[107]():
        delete(data, disconnect=True)
    delete(self, disconnect=True)
