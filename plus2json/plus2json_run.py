"""

Provide a listener to the PLUS parser and tree walker.

"""

import sys
from os.path import abspath
from pathlib import Path
package_path = abspath(Path(__file__).parent)
sys.path.insert(0, package_path)
from plus2jsonListener import plus2jsonListener
from plus2jsonParser import plus2jsonParser
from plus_job_defn import *

# tree-walk listener
# This is the interface to the antlr4 parser/walker.
# It extends the generated listener class and creates instances of
# JobDefn and subordinate classes for a model to produce JSON
# representations of the job, sequence and audit event definitions.
class plus2json_run(plus2jsonListener):
    """extension to tree-walker/listener for PLUS grammar"""
    def exitJob_name(self, ctx:plus2jsonParser.Job_nameContext):
        JobDefn(ctx.identifier().getText().strip('"')) # job name is double-quoted

    def exitSequence_name(self, ctx:plus2jsonParser.Sequence_nameContext):
        SequenceDefn(ctx.identifier().getText())

    def exitSequence_defn(self, ctx:plus2jsonParser.Sequence_defnContext):
        if AuditEventDefn.c_current_event:
            AuditEventDefn.c_current_event.SequenceEnd = True # in case we did not 'detach'
        SequenceDefn.c_current_sequence = None
        AuditEventDefn.c_current_event = None

    def exitEvent_name(self, ctx:plus2jsonParser.Event_nameContext):
        AuditEventDefn( ctx.identifier().getText(), "" if not ctx.number() else ctx.number().getText() )

    def exitEvent_defn(self, ctx:plus2jsonParser.Event_defnContext):
        if ctx.HIDE():
            AuditEventDefn.c_current_event.SequenceStart = True

    def exitBranch_count(self, ctx:plus2jsonParser.Branch_countContext):
        """almost the same as Loop and Merge"""
        # The default of source or target is the event definition carrying
        # the branch_count parameters.
        dynamic_control = DynamicControl( ctx.bcname.getText(), "BRANCHCOUNT" )
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

    def exitMerge_count(self, ctx:plus2jsonParser.Merge_countContext):
        """almost the same as Branch and Loop"""
        # The default of source or target is the event definition carrying
        # the loop_count parameters.
        dynamic_control = DynamicControl( ctx.mcname.getText(), "MERGECOUNT" )
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

    def exitLoop_count(self, ctx:plus2jsonParser.Loop_countContext):
        """almost the same as Branch and Merge"""
        # The default of source or target is the event definition carrying
        # the loop_count parameters.
        dynamic_control = DynamicControl( ctx.lcname.getText(), "LOOPCOUNT" )
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

    def exitInvariant(self, ctx:plus2jsonParser.InvariantContext):
        # The default of source or target is the event definition carrying
        # the invariant parameters.
        name = ctx.invname.getText()
        invariant = None
        invariants = [inv for inv in Invariant.instances if inv.Name == name]
        if invariants:
            invariant = invariants[-1]
        else:
            invariant = Invariant( name, "EINV" if ctx.EINV() else "IINV" )
        if ctx.SRC():
            # explicit source event
            if ctx.sname:
                invariant.src_evt_txt = ctx.sname.getText()
            else:
                invariant.src_evt_txt = AuditEventDefn.c_current_event.EventName
            if ctx.socc:
                invariant.src_evt_occ = ctx.socc.getText()
            else:
                invariant.src_occ_txt = AuditEventDefn.c_current_event.OccurrenceId
        if ctx.USER():
            # explicit user event
            uname = ""
            uocc = ""
            if ctx.uname:
                uname = ctx.uname.getText()
            else:
                uname = AuditEventDefn.c_current_event.EventName
            if ctx.uocc:
                uocc = ctx.uocc.getText()
            else:
                uocc = AuditEventDefn.c_current_event.OccurrenceId
            invariant.users.append( ( uname, uocc ) )
        # neither SRC nor USER defaults source to host
        if not ctx.SRC() and not ctx.USER():
            invariant.src_evt_txt = AuditEventDefn.c_current_event.EventName
            invariant.src_occ_txt = AuditEventDefn.c_current_event.OccurrenceId

    def enterBreak(self, ctx:plus2jsonParser.BreakContext):
        AuditEventDefn.c_current_event.isBreak = True

    def enterDetach(self, ctx:plus2jsonParser.DetachContext):
        AuditEventDefn.c_current_event.SequenceEnd = True
        AuditEventDefn.c_current_event = None

    def enterIf(self, ctx:plus2jsonParser.IfContext):
        f = Fork("XOR")
        f.begin()

    def enterElseif(self, ctx:plus2jsonParser.ElseifContext):
        Fork.instances[-1].again()

    def enterElse(self, ctx:plus2jsonParser.ElseContext):
        Fork.instances[-1].again()

    def exitIf(self, ctx:plus2jsonParser.IfContext):
        Fork.instances[-1].endfork()

    def enterSwitch(self, ctx:plus2jsonParser.SwitchContext):
        f = Fork("XOR")
        f.begin()

    def enterCase(self, ctx:plus2jsonParser.CaseContext):
        Fork.instances[-1].again()

    def exitSwitch(self, ctx:plus2jsonParser.SwitchContext):
        Fork.instances[-1].endfork()

    def enterFork(self, ctx:plus2jsonParser.ForkContext):
        f = Fork("AND")
        f.begin()

    def enterFork_again(self, ctx:plus2jsonParser.Fork_againContext):
        Fork.instances[-1].again()

    def exitFork(self, ctx:plus2jsonParser.ForkContext):
        Fork.instances[-1].endfork()

    def enterSplit(self, ctx:plus2jsonParser.SplitContext):
        f = Fork("IOR")
        f.begin()

    def enterSplit_again(self, ctx:plus2jsonParser.Split_againContext):
        Fork.instances[-1].again()

    def exitSplit(self, ctx:plus2jsonParser.SplitContext):
        Fork.instances[-1].endfork()

    def enterLoop(self, ctx:plus2jsonParser.LoopContext):
        Loop()

    # Link the last event in the loop as a previous event to the first event in the loop.
    def exitLoop(self, ctx:plus2jsonParser.LoopContext):
        if AuditEventDefn.c_current_event: # We may be following a fork/merge.
            Loop.instances[-1].R8_PreviousAuditEventDefn_starts_with.R3_PreviousAuditEventDefn.append( PreviousAuditEventDefn( AuditEventDefn.c_current_event ) )
        else:
            # ended the loop with a merge
            if SequenceDefn.instances[-1].merge_usage_cache:
                for mu_pe in SequenceDefn.instances[-1].merge_usage_cache:
                    # omit break events
                    if not mu_pe.R3_AuditEventDefn_precedes.isBreak:
                        Loop.instances[-1].R8_PreviousAuditEventDefn_starts_with.R3_PreviousAuditEventDefn.append( mu_pe )
        Loop.instances.pop()

    def exitJob_defn(self, ctx:plus2jsonParser.Job_defnContext):
        # Resolve the linkage between audit events using name and occurrence.
        # This is due to forward references made in the job definition.
        DynamicControl.resolve_event_linkage()
        Invariant.resolve_event_linkage()
