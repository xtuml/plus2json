"""

Provide a listener to the PLUS parser and tree walker.

"""

import json
import sys
import xtuml
from plus2jsonListener import plus2jsonListener
from plus2jsonParser import plus2jsonParser


class PlusPopulator(plus2jsonListener):
    """extension to tree-walker/listener for PLUS grammar"""

    def __init__(self):
        super(PlusPopulator, self).__init__()
        self.metamodel = xtuml.load_metamodel('plus_schema.sql')
        self.current_job = None
        self.current_sequence = None
        self.current_event = None
        self.current_loop = None

    def exitJob_name(self, ctx: plus2jsonParser.Job_nameContext):
        self.current_job = self.metamodel.new('JobDefn', JobDefinitionName=ctx.identifier().getText().strip('"'))

    def exitExtern(self, ctx: plus2jsonParser.ExternContext):
        # The default of source or target is the event definition carrying
        # the invariant parameters.
        jobdefnname = ctx.jobdefn.getText().strip('"')
        name = ctx.invname.getText().strip('"')
        self.metamodel.new('Invariant', Name=name, Type='EINV', SourceJobDefinitionName=jobdefnname, is_extern=True, user_tuples='[]')

    def exitSequence_name(self, ctx: plus2jsonParser.Sequence_nameContext):
        self.current_sequence = self.metamodel.new('SequenceDefn', SequenceName=ctx.identifier().getText())
        if self.current_job:
            xtuml.relate(self.current_sequence, self.current_job, 1)

    def exitSequence_defn(self, ctx: plus2jsonParser.Sequence_defnContext):
        if self.current_event:
            self.current_event.SequenceEnd = True
        self.current_sequence = None
        self.current_event = None

    def exitEvent_name(self, ctx: plus2jsonParser.Event_nameContext):
        name = ctx.identifier().getText()
        occurrence = str(len(xtuml.navigate_many(self.current_sequence).AuditEventDefn[2](lambda sel: sel.EventName == name))) if not ctx.number() else ctx.number().getText()
        # TODO scope
        evt = self.metamodel.new('AuditEventDefn', EventName=name, OccurrenceId=occurrence, SequenceStart=False, SequenceEnd=False, isBreak=False, scope=-1)
        xtuml.relate(self.current_sequence, evt, 2)

        # link the start event
        if not xtuml.navigate_one(self.current_sequence).AuditEventDefn[13]():
            xtuml.relate(evt, self.current_sequence, 13)
            evt.SequenceStart = True

        # link the previous event
        if self.current_event:
            xtuml.relate_using(self.current_event, evt, self.metamodel.new('PreviousAuditEventDefn'), 3, 'precedes')

        # TODO fork and loop

        self.current_event = evt

    def exitEvent_defn(self, ctx: plus2jsonParser.Event_defnContext):
        if ctx.HIDE():
            self.current_event.SequenceStart = True

    def create_dynamic_control(self, name, control_type):
        dynamic_control = self.metamodel.new('DynamicControl', DynamicControlName=name)
        if control_type in ('BRANCHCOUNT', 'MERGECOUNT', 'LOOPCOUNT'):
            dynamic_control.DynamicControlType = control_type         # branch or loop
        else:
            # TODO error logging
            print(f'ERROR:  invalid dynamic control type: {control_type} with name: {name}')
        # Default source and user event to be the host audit event.  Adjustments will be made by SRC/USER.
        dynamic_control.src_evt_txt = self.current_event.EventName
        dynamic_control.src_occ_txt = self.current_event.OccurrenceId
        dynamic_control.user_evt_txt = self.current_event.EventName
        dynamic_control.user_occ_txt = self.current_event.OccurrenceId

    def exitBranch_count(self, ctx: plus2jsonParser.Branch_countContext):
        """almost the same as Loop and Merge"""
        # The default of source or target is the event definition carrying
        # the branch_count parameters.
        dynamic_control = self.create_dynamic_control(ctx.bcname.getText(), 'BRANCHCOUNT')
        if ctx.SRC():
            # explicit source event
            dynamic_control.src_evt_txt = ctx.sname.getText()
            if ctx.socc:
                dynamic_control.src_evt_occ = ctx.socc.getText()
        if ctx.USER():
            # explicit user event
            dynamic_control.user_evt_txt = ctx.uname.getText()
            if ctx.uocc:
                dynamic_control.user_evt_occ = ctx.uocc.getText()

    def exitMerge_count(self, ctx: plus2jsonParser.Merge_countContext):
        """almost the same as Branch and Loop"""
        # The default of source or target is the event definition carrying
        # the loop_count parameters.
        dynamic_control = self.create_dynamic_control(ctx.mcname.getText(), 'MERGECOUNT')
        if ctx.SRC():
            # explicit source event
            if ctx.sname:
                dynamic_control.src_evt_txt = ctx.sname.getText()
            if ctx.socc:
                dynamic_control.src_evt_occ = ctx.socc.getText()
        if ctx.USER():
            # explicit user event
            if ctx.uname:
                dynamic_control.user_evt_txt = ctx.uname.getText()
            if ctx.uocc:
                dynamic_control.user_evt_occ = ctx.uocc.getText()

    def exitLoop_count(self, ctx: plus2jsonParser.Loop_countContext):
        """almost the same as Branch and Merge"""
        # The default of source or target is the event definition carrying
        # the loop_count parameters.
        dynamic_control = self.create_dynamic_control(ctx.lcname.getText(), 'LOOPCOUNT')
        if ctx.SRC():
            # explicit source event
            if ctx.sname:
                dynamic_control.src_evt_txt = ctx.sname.getText()
            if ctx.socc:
                dynamic_control.src_occ_txt = ctx.socc.getText()
        if ctx.USER():
            # explicit user event
            if ctx.uname:
                dynamic_control.user_evt_txt = ctx.uname.getText()
            if ctx.uocc:
                dynamic_control.user_occ_txt = ctx.uocc.getText()

    def exitInvariant(self, ctx: plus2jsonParser.InvariantContext):
        # The default of source or target is the event definition carrying
        # the invariant parameters.
        name = ctx.invname.getText().strip('"')
        invariant = None
        invariants = self.metamodel.select_many('Invariant', lambda sel: sel.Name == name)
        if invariants:
            # TODO relies on insertion order
            invariant = list(invariants)[-1]
        else:
            invariant = self.metamodel.new('Invariant', Name=name, Type=('EINV' if ctx.EINV() else 'IINV'), SourceJobDefinitionName=self.current_job.JobDefinitionName, user_tuples='[]')
        if ctx.SRC():
            # explicit source event
            if ctx.sname:
                invariant.src_evt_txt = ctx.sname.getText()
            else:
                invariant.src_evt_txt = self.current_event.EventName
            if ctx.socc:
                invariant.src_evt_occ = ctx.socc.getText()
            else:
                invariant.src_occ_txt = self.current_event.OccurrenceId
        if ctx.USER():
            # explicit user event
            uname = ""
            uocc = ""
            if ctx.uname:
                uname = ctx.uname.getText()
            else:
                uname = self.current_event.EventName
            if ctx.uocc:
                uocc = ctx.uocc.getText()
            else:
                uocc = self.current_event.OccurrenceId
            invariant.user_tuples = json.dumps(json.loads(invariant.user_tuples) + [(uname, uocc)])
        # neither SRC nor USER defaults source to host
        if not ctx.SRC() and not ctx.USER():
            invariant.src_evt_txt = self.current_event.EventName
            invariant.src_occ_txt = self.current_event.OccurrenceId

    def enterBreak(self, ctx: plus2jsonParser.BreakContext):
        self.current_event.isBreak = True

    def enterDetach(self, ctx: plus2jsonParser.DetachContext):
        # 'detach' is used after events but also after EINV declarations.
        if self.current_event:
            self.current_event.SequenceEnd = True
            self.current_event = None

    def exitJob_defn(self, ctx: plus2jsonParser.Job_defnContext):
        # Resolve the linkage between audit events using name and occurrence.
        # This is due to forward references made in the job definition.
        self.resolve_event_linkage()
        xtuml.check_uniqueness_constraint(self.metamodel)
        xtuml.check_association_integrity(self.metamodel)

    def resolve_event_linkage(self):
        """ Match the text of the invariant event src and user to audit events.  """
        for inv in self.metamodel.select_many('Invariant'):
            saes = self.metamodel.select_many('AuditEventDefn', lambda sel: sel.EventName == inv.src_evt_txt and sel.OccurrenceId == inv.src_occ_txt)
            if not saes:
                if inv.Type == 'IINV':
                    print(f'resolve_event_linkage:  ERROR, no source events for IINV: {inv.Name}')
            for sae in saes:
                xtuml.relate(inv, sae, 11)
            uaes = self.metamodel.select_many('AuditEventDefn', lambda sel: [sel.EventName, sel.OccurrenceId] in json.loads(inv.user_tuples))
            print(uaes)
            if not uaes:
                if type == 'IINV':
                    print('fresolve_event_linkage:  ERROR, no user events for IINV: {inv.Name}')
            # We can have more than one user for an invariant.
            for uae in uaes:
                xtuml.relate(inv, uae, 12)

        for dc in self.metamodel.select_many('DynamicControl'):
            sae = xtuml.metamodel.select_one('AuditEventDefn', lambda sel: sel.EventName == dc.src_evt_txt and sel.OccurrenceId == dc.src_occ_txt)
            if sae:
                xtuml.relate(dc, sae, 9)
            else:
                print(f'ERROR:  unresolved SRC event in dynamic control: {dc.DynamicControlName} with name: {dc.src_evt_txt}')
                sys.exit()
            uae = xtuml.metamodel.select_one('AuditEventDefn', lambda sel: sel.EventName == dc.user_evt_txt and sel.OccurrenceId == dc.user_occ_txt)
            if uae:
                xtuml.relate(dc, uae, 10)
            else:
                print(f'ERROR:  unresolved USER event in dynamic control: {dc.DynamicControlName} with name: {dc.user_evt_txt}')
                sys.exit()
