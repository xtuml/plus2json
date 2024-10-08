import sys
import xtuml
import time
import logging
import csv
import random

from datetime import datetime, timedelta

from xtuml import relate, unrelate, delete, order_by, navigate_many as many, navigate_one as one, navigate_any as any
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
    if opts.num_events == 0:
        # Do not output statistics when running in volume mode.
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

        # if this event is a branch count user, multiply the branch count and previous events
        bcnt = any(any(self).AuditEventDefn[56].EvtDataDefn[12](lambda sel: sel.Type == EventDataType.BCNT)).EventData[108](lambda sel: sel.IsSource)
        if bcnt:
            branch_count *= int(bcnt.Value)
            evts *= int(bcnt.Value)

        # play the next fragment checking to ensure there is at least one non-empty event in the list
        for e in evts:
            if e:
                evts = Fragment_play(next_frag, job, branch_count, evts)
                break

    return evts


def AuditEventDefn_play(self, job, branch_count, prev_evts):
    m = self.__metaclass__.metamodel
    opts = m.select_any('_Options')

    evts = []
    if self.IsCritical and 0 == random.randint(0, 1) and not opts.replace and not opts.insert and not opts.sibling and not opts.append and not opts.orphan and not opts.omit and not opts.injectAb4B:
        # critical and coin toss is tails
        # play an (any) unhappy event instead of this critical event
        unhappy_event_defn = any(job).JobDefn[101].PkgDefn[20].UnhappyEventDefn[21]()
        return UnhappyEventDefn_play(unhappy_event_defn, job, branch_count, prev_evts)
    elif opts.replace and self.Name in opts.replace:
        # --replace ABC
        # replace this event with an (any) unhappy event
        unhappy_event_defn = any(job).JobDefn[101].PkgDefn[20].UnhappyEventDefn[21]()
        return UnhappyEventDefn_play(unhappy_event_defn, job, branch_count, prev_evts)
    elif opts.insert and self.Name in opts.insert:
        # --insert XYZ
        # ahead of this event insert an (any) unhappy event
        # for insert behaviour, the previous event ids need to be updated
        prev_evts = UnhappyEventDefn_play(m.select_any('UnhappyEventDefn'), job, branch_count, prev_evts)
    elif opts.injectAb4B and self.Name == opts.injectAb4B[1]:
        # --injectAb4B A B
        # ahead of this event (B) inject the event with name (A)
        # for injectAb4B behaviour, the previous event ids need to be updated
        if opts.injectAb4B[0] == opts.injectAb4B[1]:
            logger.error(f'injectAb4B:  Cannot inject an event ({opts.injectAb4B[0]}) before the same event ({opts.injectAb4B[1]}).')
            sys.exit()
        a = m.select_any('AuditEventDefn', lambda sel: sel.Name == opts.injectAb4B[0])
        if a:
            prev_evts = AuditEventDefn_play(a, job, branch_count, prev_evts)
        else:
            logger.error(f'injectAb4B:  Did not find an event named:{opts.injectAb4B[0]}.')
            sys.exit()
    elif opts.sibling and self.Name in opts.sibling:
        # --sibling MNO
        # play an unhappy event and then continue passing forward with prev_evts
        unhappy_event_defn = any(job).JobDefn[101].PkgDefn[20].UnhappyEventDefn[21]()
        ignored_evts = UnhappyEventDefn_play(unhappy_event_defn, job, branch_count, prev_evts)
    elif opts.orphan and self.Name in opts.orphan:
        # --orphan PQR
        # play an unhappy event with no previous event IDs and then continue forward with prev_evts
        unhappy_event_defn = any(job).JobDefn[101].PkgDefn[20].UnhappyEventDefn[21]()
        ignored_evts = UnhappyEventDefn_play(unhappy_event_defn, job, branch_count, [[]])
    elif opts.omit and self.Name in opts.omit:
        # --omit BYE
        # skip this event returning the prev_evts
        return prev_evts

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

    if opts.append and self.Name in opts.append:
        # --append STU
        # following this event append an (any) unhappy event
        unhappy_event_defn = any(job).JobDefn[101].PkgDefn[20].UnhappyEventDefn[21]()
        return UnhappyEventDefn_play(unhappy_event_defn, job, branch_count, evts)

    # reset loop count to cause loop to break
    if self.IsBreak:
        # Search upwards through Fragment and Tine to find containing Loop.
        # The fragments we care about are Forks and Loops.
        fragment = one(self).Fragment[56]()
        while ( fragment ):
            loop = one(fragment).Tine[59].Loop[55]()
            if loop:
                loop.Count = 0
                break
            # not a Loop, must be a Fork
            fragment = one(fragment).Tine[59].Fork[54].Fragment[56]()

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
                    logger.warning('Not persisting external invariant value')
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
                logger.warning(f'Unable to find existing invariant value for invariant "{self.Name}"')

    return evt_data


def Fork_play(self, job, branch_count, prev_evts):
    if self.Type == ConstraintType.XOR:
        # choose the tine with an alternative in our pathway
        pathway = one(job).Pathway[104]()
        for tine in many(self).Tine[54]():
            if pathway in many(tine).Alternative[63].Pathway[61]():
                frag = one(tine).Fragment[51]()
                if frag:
                    return Tine_play(tine, job, branch_count, prev_evts)
                else:
                    # if tine has no Fragment (if without else), return previous events
                    return prev_evts
        # WARNING:  report error and play any tine to avoid crashing
        logger.debug(f'no eligible tine for pathway:{pathway.JobDefnName}:{pathway.Number}', exc_info=True)
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
    self.Count = int(lcnt.Value) if lcnt else 1
    i = 0
    while i < self.Count:
        # self.Count may get reset by a break statement in the Loop
        evts = Tine_play(one(self).Tine[55](), job, branch_count, prev_evts)
        prev_evts = evts
        i = i + 1
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
    unrelate(self, one(self).JobDefn[101](), 101)
    unrelate(self, one(self).Pathway[104](), 104)
    delete(self, disconnect=True)


def AuditEvent_dispose(self):
    unrelate(self, one(self).Job[102](), 102)
    audit_event_defn = one(self).AuditEventDefn[103]()
    if audit_event_defn:
        unrelate(self, audit_event_defn, 103)
    unhappy_event_defn = one(self).UnhappyEventDefn[109]()
    if unhappy_event_defn:
        unrelate(self, unhappy_event_defn, 109)
    for prev in many(self).AuditEvent[106,'must_precede']():
        unrelate(self, prev, 106,'must_precede')
    for succ in many(self).AuditEvent[106,'must_follow']():
        unrelate(self, succ, 106,'must_follow')
    for data in many(self).EventData[107]():
        unrelate(data, one(data).EvtDataDefn[108](), 108)
        unrelate(self, data, 107)
        delete(data, disconnect=True)
    delete(self, disconnect=True)
