import xtuml
from plus2jsonParser import plus2jsonParser
import plus2jsonVisitor

from enum import IntEnum, auto
from uuid import uuid3, UUID
from xtuml import relate, relate_using, navigate_one as one, navigate_many as many, navigate_any as any


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


class PlusPopulator(plus2jsonVisitor.plus2jsonVisitor):

    def __init__(self, metamodel):
        super(PlusPopulator, self).__init__()
        self.m = metamodel
        self.current_job = None
        self.current_sequence = None
        self.current_fragment = None
        self.current_tine = None
        self.current_event = None

    def aggregateResult(self, aggregate, nextResult):
        return nextResult or aggregate  # do not overwrite with None

    def visitJob_defn(self, ctx: plus2jsonParser.Job_defnContext):
        # create a new job
        job = self.m.new('JobDefn', Name=self.visit(ctx.job_name()))
        self.current_job = job

        # process external invariant declarations
        for extern in ctx.extern():
            self.visit(extern)

        # process all sequences
        for seq in ctx.sequence_defn():
            self.visit(seq)

        self.current_job = None
        return job

    def visitExtern(self, ctx: plus2jsonParser.ExternContext):
        inv = self.m.new('EvtDataDefn', Name=self.visit(ctx.invname), Type=EventDataType.EINV, SourceJobDefnName=self.visit(ctx.jobdefn))
        relate(inv, self.current_job, 17)
        return inv

    def visitSequence_defn(self, ctx: plus2jsonParser.Sequence_defnContext):
        # create a new sequence
        seq = self.m.new('SeqDefn', Name=self.visit(ctx.sequence_name()))
        relate(seq, self.current_job, 1)
        self.current_sequence = seq

        # process all statements
        self.current_fragment = None
        for smt in ctx.statement():
            # process the statement
            frag = self.visit(smt)

            # set the start event(s)
            if not any(self.current_sequence).AuditEventDefn[13]():
                for start_evt in self.get_first_events(frag):
                    relate(start_evt, self.current_sequence, 13)

            # link the fragments in order
            if self.current_fragment:
                relate(self.current_fragment, frag, 57, 'precedes')

            # set the current fragment
            self.current_fragment = frag

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

    def visitStatement(self, ctx: plus2jsonParser.StatementContext):
        # visit the subtype
        frag = self.visitChildren(ctx)

        # link all event successions
        prev_evts = self.get_last_events(self.current_fragment) if self.current_fragment else []
        next_evts = self.get_first_events(frag)
        for prev_evt in prev_evts:
            for next_evt in next_evts:
                relate_using(prev_evt, next_evt, self.m.new('EvtSucc'), 3, 'precedes')

        return frag

    def visitEvent_defn(self, ctx: plus2jsonParser.Event_defnContext):
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

        # check if this is the termination of a tine
        if self.current_tine and ctx.detach():
            self.current_tine.IsTerminal = True

        # relate the event to the current sequence
        relate(evt, self.current_sequence, 2)

        # process event data
        self.current_event = evt
        for tag in ctx.event_tag():
            self.visit(tag)
        self.current_event = None

        return frag

    def visitEvent_name(self, ctx: plus2jsonParser.Event_nameContext):
        name = self.visit(ctx.identifier())
        if ctx.number():
            occurrence = self.visit(ctx.number())
        else:
            occurrence = 0
        return name, occurrence

    def visitEvent_ref(self, ctx: plus2jsonParser.Event_refContext):
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

        return dc

    def visitBranch_count(self, ctx: plus2jsonParser.Branch_countContext):
        return self.processDynamicControl(ctx, self.visit(ctx.bcname), EventDataType.BCNT)

    def visitMerge_count(self, ctx: plus2jsonParser.Merge_countContext):
        return self.processDynamicControl(ctx, self.visit(ctx.mcname), EventDataType.MCNT)

    def visitLoop_count(self, ctx: plus2jsonParser.Loop_countContext):
        return self.processDynamicControl(ctx, self.visit(ctx.lcname), EventDataType.LCNT)

    def visitInvariant(self, ctx: plus2jsonParser.InvariantContext):
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

        # link the user event
        if ctx.uevt:
            relate(self.visit(ctx.uevt), inv, 12)
        elif ctx.USER():
            relate(self.current_event, inv, 12)

        return inv

    def processFork(self, type, tines):
        # cache the current fragment
        pre_fork_frag = self.current_fragment

        # create a new fork and corresponding fragment
        frag = self.m.new('Fragment')
        fork = self.m.new('Fork', Type=type)
        relate(frag, fork, 56)

        # process all tines
        for tine in tines:
            relate(fork, self.processTine(tine), 54)

        # link all event successions
        prev_evts = self.get_last_events(pre_fork_frag) if pre_fork_frag else []
        next_evts = self.get_first_events(frag)
        for prev_evt in prev_evts:
            for next_evt in next_evts:
                evt_succ = self.m.new('EvtSucc')
                id_str = str(generate_id(prev_evt.Name, prev_evt.OccurrenceId, prev_evt.JobDefnName, next_evt.Name, next_evt.OccurrenceId, next_evt.JobDefnName))
                relate(evt_succ, self.m.new('ConstDefn', Id=id_str, Type=fork.Type), 16)
                relate_using(prev_evt, next_evt, evt_succ, 3, 'precedes')

        self.current_fragment = None
        return frag

    def processTine(self, ctx):
        # process the tine
        self.current_fragment = None
        tine = self.m.new('Tine')
        self.current_tine = tine
        for smt in ctx.statement():
            # process the statement
            frag = self.visit(smt)

            # link the first fragment
            if not one(tine).Fragment[51]():
                relate(frag, tine, 51)

            # link the fragments in order
            if self.current_fragment:
                relate(self.current_fragment, frag, 57, 'precedes')

            # set the current fragment
            self.current_fragment = frag

        self.current_tine = None

        # link the last fragment
        relate(frag, tine, 52)
        return tine

    def visitIf(self, ctx: plus2jsonParser.IfContext):
        return self.processFork(ConstraintType.XOR, [ctx] + ctx.elseif() + [ctx.else_()])

    def visitElseif(self, ctx: plus2jsonParser.ElseifContext):
        return self.processTine(ctx)

    def visitElse(self, ctx: plus2jsonParser.ElseContext):
        return self.processTine(ctx)

    def visitSwitch(self, ctx: plus2jsonParser.SwitchContext):
        return self.processFork(ConstraintType.XOR, ctx.case())

    def visitCase(self, ctx: plus2jsonParser.CaseContext):
        return self.processTine(ctx)

    def visitLoop(self, ctx: plus2jsonParser.LoopContext):
        # cache the current fragment
        pre_loop_frag = self.current_fragment

        # create a new loop and corresponding fragment
        frag = self.m.new('Fragment')
        loop = self.m.new('Loop')
        relate(frag, loop, 56)

        # process the tine
        relate(loop, self.processTine(ctx), 55)

        # link all event successions
        prev_evts = self.get_last_events(frag) + (self.get_last_events(pre_loop_frag) if pre_loop_frag else [])
        next_evts = self.get_first_events(frag)
        for prev_evt in prev_evts:
            for next_evt in next_evts:
                relate_using(prev_evt, next_evt, self.m.new('EvtSucc'), 3, 'precedes')

        self.current_fragment = None

        return frag

    def visitFork(self, ctx: plus2jsonParser.ForkContext):
        return self.processFork(ConstraintType.AND, [ctx] + ctx.fork_again())

    def visitFork_again(self, ctx: plus2jsonParser.Fork_againContext):
        return self.processTine(ctx)

    def visitSplit(self, ctx: plus2jsonParser.SplitContext):
        return self.processFork(ConstraintType.IOR, [ctx] + ctx.split_again())

    def visitSplit_again(self, ctx: plus2jsonParser.Split_againContext):
        return self.processTine(ctx)

    def visitIdentifier(self, ctx: plus2jsonParser.IdentifierContext):
        return ctx.getText().strip('"')

    def visitNumber(self, ctx: plus2jsonParser.NumberContext):
        return int(ctx.getText())
