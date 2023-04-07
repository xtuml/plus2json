"""

This is the data model to capture the PLUS Job Definition.

"""

import sys
from os.path import abspath
from pathlib import Path
package_path = abspath(Path(__file__).parent)
sys.path.insert(0, package_path)
from plus_job_defn_aeo import *
from plus_job_defn_json import *
from plus_job_defn_play import *
from plus_job_defn_print import *
from plus_job_defn_aesim import *
from plus_job_defn_aesim_test import *

# TODO
# Deal with merge-in-merge with no event in between.  This may require joining 2 merge usages.
# !include
# Use a notational mark and some data to indicate where instance forks occur.
# Enforce CRITICAL when unhappy events are defined.

# Key classes (JobDefn, SequenceDefn, AuditEventDefn, Invariant) are inheriting from
# classes that provide methods for various forms of output.  This is a "mixin" pattern,
# which allows cohesive packaging of special-purpose output routines in one file each.

class JobDefn( JobDefn_AEO, JobDefn_JSON, JobDefn_play, JobDefn_print, JobDefn_AESim, JobDefn_AEStest ):
    """PLUS Job Definition"""
    instances = []                                         # instance population (pattern for all)
    def __init__(self, name):
        self.JobDefinitionName = name                      # created when the name is encountered
        self.R1_SequenceDefn_defines = []                  # job may contain multiple peer sequences
        JobDefn.instances.append(self)

class SequenceDefn( SequenceDefn_AEO, SequenceDefn_JSON, SequenceDefn_play, SequenceDefn_print, SequenceDefn_AESim, SequenceDefn_AEStest ):
    """PLUS Sequence Definition"""
    instances = []
    merge_usage_cache = []                                 # previous event collection carried across scopes
                                                           # used for previous events after 'end split',
                                                           # 'end fork', 'endswitch' and 'end if'
    c_current_sequence = None                              # set at creation, emptied at exit
    def __init__(self, name):
        self.SequenceName = name                           # created when the name is encountered
        if any( s.SequenceName == name for s in SequenceDefn.instances ):
            print( "ERROR:  duplicate sequence detected:", name )
            sys.exit()
        JobDefn.instances[-1].R1_SequenceDefn_defines.append(self) # link self to JobDefn across R1
        self.R1_JobDefn = JobDefn.instances[-1]
        self.R2_AuditEventDefn_defines = []                             # appended with each new event encountered
        self.start_events = []                             # start_events get added by the first event
                                                           # ... that sees an empty list
                                                           # ... and by any event preceded by HIDE
        SequenceDefn.c_current_sequence = self
        SequenceDefn.instances.append(self)

class AuditEventDefn( AuditEventDefn_AEO, AuditEventDefn_JSON, AuditEventDefn_play, AuditEventDefn_print, AuditEventDefn_AESim, AuditEventDefn_AEStest ):
    """PLUS Audit Event Definition"""
    instances = []
    ApplicationName = "default_application_name"           # not presently used
    c_current_event = None                                 # set at creation, reset at sequence exit
    c_longest_name_length = 0                              # Keep longest name length for pretty printing.
    def __init__(self, name, occurrence):
        self.EventName = name
        self.scope = Fork.c_scope
        if len( name ) > AuditEventDefn.c_longest_name_length:
            AuditEventDefn.c_longest_name_length = len( name )
        self.sequence = SequenceDefn.c_current_sequence
        if occurrence:
            if any( ae for ae in self.sequence.R2_AuditEventDefn_defines if ae.EventName == name and ae.OccurrenceId == occurrence ):
                print( "ERROR:  duplicate audit event detected:", name + "(" + occurrence + ")" )
                sys.exit()
            self.OccurrenceId = occurrence
        else:
            # here, we count previous occurrences and assign an incremented value
            items = [ae for ae in self.sequence.R2_AuditEventDefn_defines if ae.EventName == name]
            self.OccurrenceId = str( len(items) )
        self.SequenceStart = False                         # set when 'HIDE' precedes
        self.SequenceEnd = False                           # set when 'detach' follows
        self.isBreak = False                               # set when 'break' follows
        self.sequence.R2_AuditEventDefn_defines.append(self) # link self to SequenceDefn across R2
        if not self.sequence.start_events:                 # ... or when no starting event, yet
            self.sequence.start_events.append( self )
            self.SequenceStart = True
        # Initialize instance of JSON supertype.
        super( AuditEventDefn_JSON, self ).__init__()
        self.R3_PreviousAuditEventDefn = []                          # extended at creation when c_current_event exists
                                                           # emptied at sequence exit
        if Fork.instances:                                 # get fork, split or if previous event
            if Fork.instances[-1].fork_point_usage:
                self.R3_PreviousAuditEventDefn.append( Fork.instances[-1].fork_point_usage )
                Fork.instances[-1].fork_point_usage = None
        if self.sequence.merge_usage_cache:                # get merge previous events
            self.R3_PreviousAuditEventDefn.extend( self.sequence.merge_usage_cache )
            self.sequence.merge_usage_cache.clear()
        if AuditEventDefn.c_current_event:
            self.R3_PreviousAuditEventDefn.append( PreviousAuditEventDefn( AuditEventDefn.c_current_event ) )
            AuditEventDefn.c_current_event = None
        # detect loop
        # if it exists but has no starting event, add this one
        if Loop.instances and not Loop.instances[-1].start_event:
            Loop.instances[-1].start_event = self
        AuditEventDefn.c_current_event = self
        AuditEventDefn.instances.append(self)

# A previous audit event contains a reference to the previous event
# but also contains attributes that decorate the "edge" from the
# previous event to the current event.
class PreviousAuditEventDefn( PreviousAuditEventDefn_JSON ):
    """PreviousAuditEvents are instances pointing to an AuditEventDefn"""
    instances = []
    def __init__(self, ae):
        self.R3_AuditEventDefn_precedes = ae
        self.ConstraintValue = ""
        self.ConstraintDefinitionId = ""
        PreviousAuditEventDefn.instances.append(self)

class Fork:
    """A Fork keeps linkages to fork and merge points."""
    # Instances of Fork are stacked to allow nesting.
    instances = []
    c_scope = -1
    c_number = 1
    def __init__(self, flavor):
        self.id = flavor.lower() + "fork" + str( Fork.c_number )            # ID factory for ConstraintDefinitionId
        Fork.c_number += 1
        self.flavor = flavor                               # AND, XOR or IOR
        self.fork_point = None                             # c_current_event pushed as PreviousAuditEventDefn
                                                           # when 'split', 'fork', 'if' or 'switch' encountered
                                                           # popped at 'end split', 'end merge', 'endif' or 'endswitch'
        self.fork_point_usage = None                       # cached here each time 'split again', 'fork again',
                                                           # 'elsif' or 'else' encountered
        self.merge_inputs = []                             # c_current_event pushed when 'split again', 'fork again',
                                                           # 'case', 'end split', 'end fork', 'endswitch',
                                                           # 'elsif', 'else' or 'endif' entered
        Fork.c_scope += 1
        Fork.instances.append(self)
    def __del__(self):
        #Fork.print_forks()
        Fork.c_scope -= 1
    def begin(self):
        # instead of c_current_event, I might need to copy from the fork_point stack
        if AuditEventDefn.c_current_event: # We may be starting with HIDE.
            Fork.instances[-1].fork_point = PreviousAuditEventDefn( AuditEventDefn.c_current_event )
            AuditEventDefn.c_current_event = None
            Fork.instances[-1].fork_point.ConstraintValue = self.flavor
            Fork.instances[-1].fork_point.ConstraintDefinitionId = Fork.instances[-1].id
            Fork.instances[-1].fork_point_usage = Fork.instances[-1].fork_point
        else:
            # detecting a nested fork (combined split, fork and/or if)
            # Look to the previous (outer scope) fork in the stack.
            if Fork.instances[Fork.c_scope-1].fork_point_usage:
                Fork.instances[-1].fork_point = PreviousAuditEventDefn( Fork.instances[Fork.c_scope-1].fork_point_usage.R3_AuditEventDefn_precedes )
                Fork.instances[-1].fork_point.ConstraintValue = self.flavor
                Fork.instances[-1].fork_point.ConstraintDefinitionId = Fork.instances[-1].id
                Fork.instances[-1].fork_point_usage = Fork.instances[-1].fork_point
    def again(self):
        if SequenceDefn.instances[-1].merge_usage_cache:
            # The merge usage did not get consumed by an event following the
            # fork/merge.  Therefore, propagate it into the next outer scope.
            Fork.instances[Fork.c_scope-1].merge_inputs.extend( SequenceDefn.instances[-1].merge_usage_cache )
            SequenceDefn.instances[-1].merge_usage_cache.clear()
        if AuditEventDefn.c_current_event: # We may have 'detach'd and have no c_current_event.
            Fork.instances[-1].merge_inputs.append( PreviousAuditEventDefn( AuditEventDefn.c_current_event ) )
            AuditEventDefn.c_current_event = None
        if Fork.instances[-1].fork_point:
            Fork.instances[-1].fork_point_usage = Fork.instances[-1].fork_point
    def endfork(self):
        if AuditEventDefn.c_current_event: # We may have 'detach'd and have no c_current_event.
            self.merge_inputs.append( PreviousAuditEventDefn( AuditEventDefn.c_current_event ) )
            AuditEventDefn.c_current_event = None
        SequenceDefn.instances[-1].merge_usage_cache.extend( Fork.instances[-1].merge_inputs )
        self.merge_inputs.clear()
        self.fork_point_usage = None
        Fork.instances.pop()                       # done with this Fork
        if Fork.instances:
            # Clear out usage, because no event was encountered to use it.
            Fork.instances[-1].fork_point_usage = None
    def print_fork(self):
        merge_inputs = ""
        merge_usages = ""
        fp = ""
        fu = ""
        if self.fork_point:
            fp = ( self.fork_point.R3_AuditEventDefn_precedes.EventName +
                   "-" + self.fork_point.ConstraintDefinitionId +
                   "-" + self.fork_point.ConstraintValue )
        if self.fork_point_usage:
            fu = ( self.fork_point_usage.R3_AuditEventDefn_precedes.EventName +
                   "-" + self.fork_point_usage.ConstraintDefinitionId +
                   "-" + self.fork_point.ConstraintValue )
        if self.merge_inputs:
            for mi in self.merge_inputs:
                merge_inputs += mi.R3_AuditEventDefn_precedes.EventName + mi.ConstraintValue
        if SequenceDefn[-1].merge_usage_cache:
            for mu in SequenceDefn[-1].merge_usage_cache:
                merge_usages += mu.R3_AuditEventDefn_precedes.EventName + mu.ConstraintValue
        print( "Fork:", Fork.c_scope, self.flavor, "fp:" + fp, "fu:" + fu, "mis:" + merge_inputs, "mus:" + merge_usages )
    @classmethod
    def print_forks(cls):
        for f in Fork.instances:
            f.print_fork()

# Dynamic control must deal with forward references.
# During the walk, capture the audit EventNames and OccurrenceIds as text.
# At the end of the walk and before output, resolve all DynamicControls.
class DynamicControl( DynamicControl_JSON ):
    """branch and loop information"""
    instances = []
    def __init__(self, name, control_type):
        if any( dc.DynamicControlName == name for dc in DynamicControl.instances ):
            print( "ERROR:  duplicate dynamic control detected:", name )
            sys.exit()
        self.DynamicControlName = name                     # unique name
        if control_type in ('BRANCHCOUNT', 'MERGECOUNT', 'LOOPCOUNT'):
            self.DynamicControlType = control_type         # branch or loop
        else:
            print( "ERROR:  invalid dynamic control type:", control_type, "with name:", name )
            sys.exit()
        # Default source and user event to be the host audit event.  Adjustments will be made by SRC/USER.
        self.src_evt_txt = AuditEventDefn.c_current_event.EventName
        self.src_occ_txt = AuditEventDefn.c_current_event.OccurrenceId
        self.user_evt_txt = AuditEventDefn.c_current_event.EventName
        self.user_occ_txt = AuditEventDefn.c_current_event.OccurrenceId
        self.R9_AuditEventDefn = None                           # audit event hosting the control
        self.user_event = None                             # audit event to be dynamically tested
        DynamicControl.instances.append(self)
    @classmethod
    def resolve_event_linkage(cls):
        for dc in DynamicControl.instances:
            sae = [ae for ae in AuditEventDefn.instances if ae.EventName == dc.src_evt_txt and ae.OccurrenceId == dc.src_occ_txt]
            if sae:
                dc.R9_AuditEventDefn = sae[-1]
            else:
                print( "ERROR:  unresolved SRC event in dynamic control:", dc.DynamicControlName, "with name:", dc.src_evt_txt  )
                sys.exit()
            uae = [ae for ae in AuditEventDefn.instances if ae.EventName == dc.user_evt_txt and ae.OccurrenceId == dc.user_occ_txt]
            if uae:
                dc.user_event = uae[-1]
            else:
                print( "ERROR:  unresolved USER event in dynamic control:", dc.DynamicControlName, "with name:", dc.user_evt_txt  )
                sys.exit()
    @classmethod
    def print_dynamic_control(cls):
        print( "Print Dynamic Control" )
        for dc in DynamicControl.instances:
            print( "dc:", dc.DynamicControlName, "src:", dc.src_evt_txt, "src_occ:", dc.src_occ_txt, "user:", dc.user_evt_txt, "uocc:", dc.user_occ_txt  )

# Invariants must deal with forward references.
# During the walk, capture the audit EventNames and OccurrenceIds as text.
# At the end of the walk and before output, resolve all Invariants.
class Invariant( Invariant_JSON ):
    """intra- and extra- job invariant information"""
    instances = []
    def __init__(self, name, invariant_type):
        if any( inv.Name == name for inv in Invariant.instances ):
            print( "ERROR:  duplicate invariant detected:", name )
            sys.exit()
        self.Name = name                                   # unique name
        if invariant_type in ('EINV', 'IINV'):
            self.Type = invariant_type                     # extra-job or intra-job invariant
        else:
            print( "ERROR:  invalid invariant type:", invariant_type, "with name:", name )
            sys.exit()
        self.src_evt_txt = ""                              # SRC event textual EventName
        self.src_occ_txt = "0"                             # SRC event textual OccurrenceId (default)
        self.user_evt_txt = []                             # USER event textual EventName
        self.user_occ_txt = []                             # USER event textual OccurrenceId (default)
        self.R11_AuditEventDefn = None                     # audit event hosting the invariant
        self.R12_AuditEventDefn = []                       # audit events to be dynamically tested
        Invariant.instances.append(self)
    @classmethod
    def resolve_event_linkage(cls):
        for inv in Invariant.instances:
            #print( "Resolving invariants:", inv.src_evt_txt, inv.src_occ_txt, inv.user_evt_txt, inv.user_occ_txt )
            saes = [ae for ae in AuditEventDefn.instances if ae.EventName in inv.src_evt_txt and ae.OccurrenceId in inv.src_occ_txt]
            if not saes:
                if "IINV" == inv.Type:
                    print( "resolve_event_linkage:  ERROR, no source events for IINV:", inv.Name )
            for sae in saes:
                inv.R11_AuditEventDefn = sae               # link inv to sae across R11
            uaes = [ae for ae in AuditEventDefn.instances if ae.EventName in inv.user_evt_txt and ae.OccurrenceId in inv.user_occ_txt]
            if not uaes:
                if "IINV" == inv.Type:
                    print( "resolve_event_linkage:  ERROR, no user events for IINV:", inv.Name )
            # We can have more than one user for an invariant.
            for uae in uaes:
                #print( "Resolving invariant users:", inv.src_evt_txt, inv.src_occ_txt, inv.user_evt_txt, inv.user_occ_txt )
                inv.R12_AuditEventDefn.append( uae )       # link inv to uae across R12

class Loop:
    """data collected from PLUS repeat loop"""
    instances = []
    c_scope = 0
    def __init__(self):
        self.start_event = None                            # first event encountered
        Loop.instances.append(self)
