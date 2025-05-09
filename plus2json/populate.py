import xtuml
import logging
import os.path
import json
import sys

from .plus import PlusParser, PlusVisitor

from enum import IntEnum, auto
from uuid import uuid3, UUID
from xtuml import relate, navigate_one as one, navigate_many as many, navigate_any as any

from antlr4.error.ErrorListener import ErrorListener
from antlr4.error.Errors import CancellationException


logger = logging.getLogger(__name__)


def flatten(lst):
    return [item for sublist in lst for item in sublist]


def generate_id(*args):
    return uuid3(UUID(int=0), ''.join([str(arg) for arg in args]))


# TODO move this somewhere else
class ConstraintType(IntEnum):
    AND = auto()
    XOR = auto()
    IOR = auto()


# TODO move this somewhere else
class EventDataType(IntEnum):
    EINV = auto()
    IINV = auto()
    LCNT = auto()
    BCNT = auto()
    MCNT = auto()


class PlusErrorListener(ErrorListener):

    def __init__(self, filename=None):
        super(PlusErrorListener, self).__init__()
        self.filename = filename

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        logger.error(f'{os.path.basename(self.filename)}[{line}:{column}]:  {msg}')
        raise CancellationException(msg)


class PlusPopulator(PlusVisitor):

    def __init__(self, metamodel):
        super(PlusPopulator, self).__init__()
        self.m = metamodel
        self.current_job = None
        self.current_sequence = None
        self.current_package = []    # stack
        self.current_fragment = None
        self.current_tine = []       # stack
        self.current_event = None
        self.id_factory = xtuml.IntegerGenerator()

    def aggregateResult(self, aggregate, nextResult):
        return nextResult or aggregate  # do not overwrite with None

    def linkPathway(self, alternative, pathway):
        '''link the given alternative and upstream alternatives to the given pathway'''
        if alternative:
            relate(alternative, pathway, 61)
            self.linkPathway(one(alternative).Alternative[62, 'is_downstream_of'](), pathway)

    def visitJob_defn(self, ctx: PlusParser.Job_defnContext):
        # create a new job
        job = self.m.new('JobDefn', Name=self.visit(ctx.job_name()))
        self.current_job = job

        # process external invariant declarations
        for extern in ctx.extern():
            self.visit(extern)

        # process all sequences
        for seq in ctx.sequence_defn():
            self.visit(seq)

        # process all packages
        for pkg in ctx.package_defn():
            self.visit(pkg)

        # create pathways for combinations of alternatives
        alternatives = self.m.select_many('Alternative', lambda sel: not one(sel).Alternative[62, 'is_upstream_of']() and not any(sel).Pathway[61]())
        for alternative in alternatives:
            # recursively link pathway to alternative and all upstream alternatives
            # each end-of-list Alternative implies a new Pathway
            pathway = self.m.new('Pathway', Number=next(self.id_factory))
            relate(self.current_job, pathway, 60)
            self.linkPathway(alternative, pathway)

        # create/link ordinal pathway if no alternatives detected
        if not any(job).Pathway[60]():
            pathway = self.m.new('Pathway', Number=next(self.id_factory))
            relate(job, pathway, 60)

        # Detect empty Fork Tines (if without else) and patch additional event successions.
        self.patch_empty_tines(job)

        self.current_job = None
        return job

    def visitJson(self, ctx: PlusParser.JsonContext):
        return ctx.getText()

    def visitExtern(self, ctx: PlusParser.ExternContext):
        inv = self.m.new('EvtDataDefn', Name=self.visit(ctx.invname), Type=EventDataType.EINV, SourceJobDefnName=self.visit(ctx.jobdefn))
        relate(inv, self.current_job, 17)

        # check if the source invariant definition is already in place
        source_inv = any(self.m.select_any('JobDefn', lambda sel: sel.Name == inv.SourceJobDefnName)).EvtDataDefn[14](lambda sel: sel.Name == inv.Name)
        if source_inv:
            relate(inv, source_inv, 18, 'corresponds_to')

        if ctx.json():
            j = self.visit(ctx.json())
            try:
                js = json.loads(j)
            except json.decoder.JSONDecodeError:
                logger.error(f'Invalid JSON configuration parameter for JobDefn:{self.current_job.Name}')
                sys.exit(1)
            else:
                self.current_job.Config_JSON = j

        return inv

    def visitSequence_defn(self, ctx: PlusParser.Sequence_defnContext):
        # create a new sequence
        seq = self.m.new('SeqDefn', Name=self.visit(ctx.sequence_name()))
        relate(seq, self.current_job, 1)
        self.current_sequence = seq

        # process all statements
        self.current_fragment = None
        for smt in ctx.statement():
            # process the statement
            frag = self.visit(smt)

            # link the fragments in order
            if self.current_fragment:
                relate(self.current_fragment, frag, 57, 'precedes')
            else:
                if not any(self.current_sequence).Fragment[58]():
                    relate(frag, self.current_sequence, 58)

            # set the current fragment
            self.current_fragment = frag

        # set the start event(s)
        for evt in many(self.current_sequence).AuditEventDefn[2]():
            if not any(evt).EvtSucc[3,'follows']():
                relate(evt, self.current_sequence, 13)

        # set the end event(s)
        # all the last events of the most recent fragment and the last event in any terminal
        # tines can be an end event for the sequence
        end_evts = self.get_last_events(self.current_fragment) + list(many(self.current_sequence).AuditEventDefn[2](lambda sel: any(sel).Fragment[56].Tine[52](lambda sel: sel.IsTerminal)))
        for end_evt in end_evts:
            relate(end_evt, self.current_sequence, 15)

        self.current_sequence = None
        return seq

    # TODO maybe the belongs on the model and is useful for later
    def get_first_events(self, fragment):
        sub = xtuml.navigate_subtype(fragment, 56)
        match sub.__metaclass__.kind:
            case 'Fork':
                return flatten(map(lambda f: self.get_last_events(f), many(sub).Tine[54].Fragment[51]()))
            case 'Loop':
                return flatten(map(lambda f: self.get_last_events(f), many(sub).Tine[55].Fragment[51]()))
            case 'AuditEventDefn':
                return [sub]

    # TODO maybe the belongs on the model and is useful for later
    def get_last_events(self, fragment):
        sub = xtuml.navigate_subtype(fragment, 56)
        match sub.__metaclass__.kind:
            case 'Fork':
                return flatten(map(lambda f: self.get_last_events(f), many(many(sub).Tine[54](lambda sel: not sel.IsTerminal)).Fragment[52]()))
            case 'Loop':
                return flatten(map(lambda f: self.get_last_events(f), many(many(sub).Tine[55](lambda sel: not sel.IsTerminal)).Fragment[52]()))
            case 'AuditEventDefn':
                return [sub]

    # Patch event successions around empty Fork Tines.
    # This is to support if without else.
    def patch_empty_tines(self, job):
        # select all tines in this job
        tines = many(job).Pathway[60].Alternative[61].Tine[63]()
        for tine in tines:
            frag = any(tine).Fragment[59]()
            if not frag:
                # emtpy tine
                prev_frag = any(tine).Fork[54].Fragment[56].Fragment[57,'follows']()
                prev_evts = self.get_last_events(prev_frag)
                next_frag = any(tine).Fork[54].Fragment[56].Fragment[57,'precedes']()
                next_evts = self.get_first_events(next_frag)
                for prev_evt in prev_evts:
                    for next_evt in next_evts:
                        if not any(prev_evt).EvtSucc[3, 'precedes'](lambda sel: one(sel).AuditEventDefn[3, 'precedes']() == next_evt):
                            evt_succ = self.m.new('EvtSucc')
                            relate(prev_evt, evt_succ, 3, 'precedes')
                            relate(evt_succ, next_evt, 3, 'precedes')

    def visitEvent_defn(self, ctx: PlusParser.Event_defnContext):
        name, occurrence = self.visit(ctx.event_name())

        # if a positive occurrence ID is not provided, choose a default
        if occurrence < 1:
            occurrence = len(many(self.current_job).SeqDefn[1].AuditEventDefn[2](lambda sel: sel.Name == name))

        # search for audit events created via forward reference
        evt = self.m.select_any('AuditEventDefn', lambda sel: sel.Name == name and sel.OccurrenceId == occurrence and hasattr(sel, 'JobDefnNameCached') and sel.JobDefnNameCached == self.current_job.Name)
        frag = one(evt).Fragment[56]()
        if not evt:
            # create a new audit event definition and corresponding fragment
            evt = self.m.new('AuditEventDefn', Name=name, OccurrenceId=occurrence, IsBreak=(ctx.break_() is not None))
            frag = self.m.new('Fragment')
            relate(frag, evt, 56)
        # break is often found on events created via forward reference (e.g. loop count users)
        if ctx.break_():
            evt.IsBreak = True

        # check if this is the termination of a tine
        if self.current_tine and ctx.detach():
            self.current_tine[-1].IsTerminal = True

        # relate the event to the current sequence
        relate(evt, self.current_sequence, 2)

        # process event data
        self.current_event = evt
        for tag in ctx.event_tag():
            self.visit(tag)
        self.current_event = None

        if ctx.json():
            j = self.visit(ctx.json())
            try:
                js = json.loads(j)
            except json.decoder.JSONDecodeError:
                logger.error(f'Invalid JSON configuration parameter for AuditEventDefn:{evt.Name}')
                sys.exit(1)
            else:
                evt.Config_JSON = j

        # link all event successions
        prev_evts = self.get_last_events(self.current_fragment) if self.current_fragment else []
        next_evts = self.get_first_events(frag)
        for prev_evt in prev_evts:
            for next_evt in next_evts:
                if not any(prev_evt).EvtSucc[3, 'precedes'](lambda sel: one(sel).AuditEventDefn[3, 'precedes']() == next_evt):
                    evt_succ = self.m.new('EvtSucc')
                    relate(prev_evt, evt_succ, 3, 'precedes')
                    relate(evt_succ, next_evt, 3, 'precedes')

        return frag

    def visitEvent_name(self, ctx: PlusParser.Event_nameContext):
        name = self.visit(ctx.identifier())
        if ctx.number():
            occurrence = self.visit(ctx.number())
        else:
            occurrence = 0
        return name, occurrence

    def visitEvent_ref(self, ctx: PlusParser.Event_refContext):
        name, occurrence = self.visit(ctx.event_name())
        evt = one(self.current_job).SeqDefn[1].AuditEventDefn[2](lambda sel: sel.Name == name and sel.OccurrenceId == occurrence)
        if not evt:
            evt = self.m.new('AuditEventDefn', Name=name, OccurrenceId=occurrence, JobDefnNameCached=self.current_job.Name)
            frag = self.m.new('Fragment')
            relate(frag, evt, 56)
        return evt

    def processDynamicControl(self, ctx, name, type):
        # find or create dynamic control
        dc = one(self.current_job).EvtDataDefn[14](lambda sel: sel.Name == name)
        if not dc:
            dc = self.m.new('EvtDataDefn', Name=name, Type=type, SourceJobDefnName=self.current_job.Name)
            relate(dc, self.current_job, 14)

        # link the source event
        if ctx.sevt:
            relate(self.visit(ctx.sevt), dc, 11)
        else:
            relate(self.current_event, dc, 11)

        # link the user event
        if ctx.uevt:
            relate(self.visit(ctx.uevt), dc, 12)
        else:
            # default user is source
            relate(self.current_event, dc, 12)

        return dc

    def visitBranch_count(self, ctx: PlusParser.Branch_countContext):
        return self.processDynamicControl(ctx, self.visit(ctx.bcname), EventDataType.BCNT)

    def visitMerge_count(self, ctx: PlusParser.Merge_countContext):
        return self.processDynamicControl(ctx, self.visit(ctx.mcname), EventDataType.MCNT)

    def visitLoop_count(self, ctx: PlusParser.Loop_countContext):
        return self.processDynamicControl(ctx, self.visit(ctx.lcname), EventDataType.LCNT)

    def visitInvariant(self, ctx: PlusParser.InvariantContext):
        name = self.visit(ctx.invname)

        # find or create invariant definition
        inv = one(self.current_job).EvtDataDefn[14](lambda sel: sel.Name == name) or one(self.current_job).EvtDataDefn[17](lambda sel: sel.Name == name)
        if not inv:
            inv = self.m.new('EvtDataDefn', Name=name, Type=(EventDataType.IINV if ctx.IINV() else EventDataType.EINV), SourceJobDefnName=self.current_job.Name)
            relate(inv, self.current_job, 14)

        # link the source event
        if ctx.sevt:
            relate(self.visit(ctx.sevt), inv, 11)
        elif ctx.SRC() or (not ctx.SRC() and not ctx.USER()):
            relate(self.current_event, inv, 11)
            # for external invariants, see if there are externs that need to be linked
            if inv.Type == EventDataType.EINV:
                extern_invs = many(self.m.select_many('JobDefn')).EvtDataDefn[17](lambda sel: sel.Name == inv.Name and sel.SourceJobDefnName == self.current_job.Name and not one(sel).EvtDataDefn[18, 'corresponds_to']())
                for extern_inv in extern_invs:
                    relate(extern_inv, inv, 18, 'corresponds_to')

        # link the user event
        if ctx.uevt:
            relate(self.visit(ctx.uevt), inv, 12)
        elif ctx.USER():
            relate(self.current_event, inv, 12)

        return inv

    def visitCritical(self, ctx: PlusParser.CriticalContext):
        self.current_event.IsCritical = True

    def processFork(self, type, tine_ctxs):
        # cache the current fragment
        pre_fork_frag = self.current_fragment

        # create a new fork and corresponding fragment
        frag = self.m.new('Fragment')
        fork = self.m.new('Fork', Type=type)
        relate(frag, fork, 56)

        # process all tines
        for tine_ctx in tine_ctxs:
            relate(fork, self.processTine(tine_ctx, type), 54)

        # link all event successions
        const_defn = None
        prev_evts = self.get_last_events(pre_fork_frag) if pre_fork_frag else []
        next_evts = self.get_first_events(frag)
        for prev_evt in prev_evts:
            for next_evt in next_evts:
                if not any(prev_evt).EvtSucc[3, 'precedes'](lambda sel: one(sel).AuditEventDefn[3, 'precedes']() == next_evt):
                    evt_succ = self.m.new('EvtSucc')
                    if type != ConstraintType.IOR:
                        if not const_defn:
                            id_str = str(generate_id(prev_evt.Name, prev_evt.OccurrenceId, prev_evt.JobDefnName, next_evt.Name, next_evt.OccurrenceId, next_evt.JobDefnName))
                            const_defn = self.m.new('ConstDefn', Id=id_str, Type=fork.Type)
                        relate(evt_succ, const_defn, 16)
                    relate(prev_evt, evt_succ, 3, 'precedes')
                    relate(evt_succ, next_evt, 3, 'precedes')

        self.current_fragment = pre_fork_frag
        return frag

    def processTine(self, ctx, type):
        # process the tine
        self.current_fragment = None
        tine = self.m.new('Tine')

        # create/relate an alternative on XOR tines
        if ConstraintType.XOR == type:
            alternative_name = ""
            if ctx and ctx.label:
                alternative_name = ctx.label
            alternative = self.m.new('Alternative', Name=alternative_name)
            relate(tine, alternative, 63)
            # walk downwards from the top of the stack of tines looking for alternatives
            for t in list(reversed(self.current_tine)):
                upstream_alternative = one(t).Alternative[63]()
                if upstream_alternative:
                    relate(upstream_alternative, alternative, 62, 'is_upstream_of')
                    break

        self.current_tine.append(tine)

        # Add statements unless this is an empty tine (if without else).
        if ctx:
            for smt in ctx.statement():
                # process the statement
                frag = self.visit(smt)
                relate(frag, tine, 59)

                # link the first fragment
                if not one(tine).Fragment[51]():
                    relate(frag, tine, 51)

                # link the fragments in order
                if self.current_fragment:
                    relate(self.current_fragment, frag, 57, 'precedes')

                # set the current fragment
                self.current_fragment = frag
        else:
            frag = None

        self.current_tine.pop()

        # link the last fragment
        if frag:
            relate(frag, tine, 52)
        return tine

    def visitIf(self, ctx: PlusParser.IfContext):
        return self.processFork(ConstraintType.XOR, [ctx] + ctx.elseif() + [ctx.else_()])

    def visitSwitch(self, ctx: PlusParser.SwitchContext):
        return self.processFork(ConstraintType.XOR, ctx.case())

    def visitLoop(self, ctx: PlusParser.LoopContext):
        # cache the current fragment
        pre_loop_frag = self.current_fragment

        # create a new loop and corresponding fragment
        frag = self.m.new('Fragment')
        loop = self.m.new('Loop')
        relate(frag, loop, 56)
        # Count gets initialised to 1, defaulted to 1, set to the LCNT
        # event data value and potentially reset by 'break'.
        loop.Count = 1

        # process the tine
        relate(loop, self.processTine(ctx, ConstraintType.AND), 55)

        # link all event successions
        prev_evts = self.get_last_events(frag) + (self.get_last_events(pre_loop_frag) if pre_loop_frag else [])
        next_evts = self.get_first_events(frag)
        for prev_evt in prev_evts:
            for next_evt in next_evts:
                if not any(prev_evt).EvtSucc[3, 'precedes'](lambda sel: one(sel).AuditEventDefn[3, 'precedes']() == next_evt):
                    evt_succ = self.m.new('EvtSucc')
                    relate(prev_evt, evt_succ, 3, 'precedes')
                    relate(evt_succ, next_evt, 3, 'precedes')

        self.current_fragment = pre_loop_frag
        return frag

    def visitFork(self, ctx: PlusParser.ForkContext):
        return self.processFork(ConstraintType.AND, [ctx] + ctx.fork_again())

    def visitSplit(self, ctx: PlusParser.SplitContext):
        return self.processFork(ConstraintType.IOR, [ctx] + ctx.split_again())

    def visitIdentifier(self, ctx: PlusParser.IdentifierContext):
        return ctx.getText().strip('"')

    def visitNumber(self, ctx: PlusParser.NumberContext):
        return int(ctx.getText())

    def visitPackage_defn(self, ctx: PlusParser.Package_defnContext):
        # create and relate a new package
        pkg = self.m.new('PkgDefn', Name=self.visit(ctx.package_name()))
        relate(pkg, self.current_job, 20)
        # Stack the current (maybe nesting) package and pop it at the end.
        self.current_package.append(pkg)

        # process package members
        self.current_fragment = None
        for pkg_member in ctx.pkg_member():
            self.visit(pkg_member)

        self.current_package.pop()
        return pkg

    def visitUnhappy_event(self, ctx: PlusParser.Unhappy_eventContext):
        # create and relate a new unhappy event definition
        unhappy_event = self.m.new('UnhappyEventDefn', Name=self.visit(ctx.unhappy_name()))
        relate(unhappy_event, self.current_package[-1], 21)

        # create and relate a fragment to the unhappy event and top of stack package
        frag = self.m.new('Fragment')
        relate(frag, unhappy_event, 56)
        relate(frag, self.current_package[-1], 53)
