"""

Provide a listener to the PLUS parser and tree walker.

"""

import sys
from plus2jsonListener import plus2jsonListener
from plus2jsonParser import plus2jsonParser

# TODO
# Deal with merge-in-merge with no event in between.  This may require joining 2 merge usages.
# !include
# Use a notational mark and some data to indicate where instance forks occur.

class JobDefn:
    """PLUS Job Definition"""
    instances = []                                        # instance population (pattern for all)
    def __init__(self, name):
        self.JobDefinitionName = name                      # created when the name is encountered
        self.sequences = []                                # job may contain multiple peer sequences
        JobDefn.instances.append(self)
    def output_json(self):
        json = ""
        for job_defn in JobDefn.instances:
            json += "{ \"JobDefinitionName\":" + job_defn.JobDefinitionName + ",\n"
            json += "\"Events\": [\n"
            seqdelim = ""
            for seq in job_defn.sequences:
                json += seqdelim
                seqdelim = ","
                aedelim = ""
                for ae in seq.audit_events:
                    json += aedelim
                    aedelim = ",\n"
                    json += "{ \"EventName\": \"" + ae.EventName + "\","
                    json += "\"OccurrenceId\": " + ae.OccurrenceId + ","
                    json += "\"SequenceName\": " + seq.SequenceName + ","
                    if ae.SequenceStart: json += "\"SequenceStart\": true,"
                    if ae.SequenceEnd: json += "\"SequenceEnd\": true,"
                    if ae.isBreak: json += "\"isBreak\": true,"
                    # look for linked DynamicControl
                    dcs = [dc for dc in DynamicControl.instances if dc.source_event is ae]
                    for dc in dcs: # preparing for when multiple DynamicControls are allowed.
                        json += "\"DynamicControl\": {"
                        json += "\"DynamicControlName\": \"" + dc.DynamicControlName + "\","
                        json += "\"DynamicControlType\": \"" + dc.DynamicControlType + "\","
                        json += "\"UserEventType\": \"" + dc.user_evt_txt + "\","
                        json += "\"UserOccurrenceId\": " + dc.user_occ_txt
                        json += "},"
                    prev_aes = ""
                    pdelim = ""
                    for prev_ae in ae.previous_events:
                        constraintid = "" if "" == prev_ae.ConstraintDefinitionId else ", \"ConstraintDefinitionId\": \"" + prev_ae.ConstraintDefinitionId + "\""
                        constraint = "" if "" == prev_ae.ConstraintValue else ", \"ConstraintValue\": \"" + prev_ae.ConstraintValue + "\""
                        prev_aes = ( prev_aes + pdelim +
                              "{ \"PreviousEventName\": \"" + prev_ae.previous_event.EventName + "\","
                              "\"PreviousOccurrenceId\": " + prev_ae.previous_event.OccurrenceId +
                              constraintid + constraint +
                              " }" )
                        pdelim = ","
                    if "" != prev_aes: json += "\"PreviousEvents\": [ " + prev_aes + "],"
                    json += "\"Application\": \"" + AuditEvent.ApplicationName + "\""
                    json += "}"
            # All events for all sequences are defined together.
            json += "\n]"
        json += "\n}\n"
        print( json )
    def pretty_print(self):
        for job_defn in JobDefn.instances:
            print("job defn:", job_defn.JobDefinitionName)
            for seq in job_defn.sequences:
                print("sequence:", seq.SequenceName)
                for ae in seq.audit_events:
                    ss = "start" if ae.SequenceStart else ""
                    se = "end" if ae.SequenceEnd else ""
                    b = "break" if ae.isBreak else "     "
                    # look for linked DynamicControls
                    bcnt = ""
                    lcnt = ""
                    mcnt = ""
                    dcs = [dc for dc in DynamicControl.instances if dc.source_event is ae]
                    for dc in dcs:
                        su = "s=" + dc.src_evt_txt + "(" + dc.src_occ_txt + ")"
                        su += "u=" + dc.user_evt_txt + "(" + dc.user_occ_txt + ")"
                        if dc.DynamicControlType == "BRANCHCOUNT":
                            bcnt += "bc:" + dc.DynamicControlName + "-" + su
                        elif dc.DynamicControlType == "MERGECOUNT":
                            mcnt += "mc:" + dc.DynamicControlName + "-" + su
                        elif dc.DynamicControlType == "LOOPCOUNT":
                            lcnt += "lc:" + dc.DynamicControlName + "-" + su
                        else:
                            print( "ERROR:  malformed dynamic control" )
                            sys.exit()
                    # look for linked Invariant
                    einv = ""
                    iinv = ""
                    inv = [inv for inv in Invariant.instances if inv.source_event is ae]
                    if inv:
                        su = ""
                        if "" != inv[-1].src_evt_txt:
                            su += "s=" + inv[-1].src_evt_txt + "(" + inv[-1].src_occ_txt + ")"
                        if "" != inv[-1].user_evt_txt:
                            su += "u=" + inv[-1].user_evt_txt + "(" + inv[-1].user_occ_txt + ")"
                        if inv[-1].Type == "EINV":
                            einv = "einv:" + inv[-1].Name + "-" + su
                        elif inv[-1].Type == "IINV":
                            iinv = "iinv:" + inv[-1].Name + "-" + su
                    inv = [inv for inv in Invariant.instances if ae in inv.user_events]
                    if inv:
                        su = ""
                        if "" != inv[-1].src_evt_txt:
                            su += "s=" + inv[-1].src_evt_txt + "(" + inv[-1].src_occ_txt + ")"
                        if "" != inv[-1].user_evt_txt:
                            su += "u=" + inv[-1].user_evt_txt + "(" + inv[-1].user_occ_txt + ")"
                        if inv[-1].Type == "EINV":
                            einv = "einv:" + inv[-1].Name + "-" + su
                        elif inv[-1].Type == "IINV":
                            iinv = "iinv:" + inv[-1].Name + "-" + su
                        else:
                            print( "ERROR:  malformed invariant type" )
                            sys.exit()
                    prev_aes = "    "
                    delim = ""
                    for prev_ae in ae.previous_events:
                        prev_aes = ( prev_aes + delim + prev_ae.previous_event.EventName +
                                     "(" + prev_ae.previous_event.OccurrenceId + ")" +
                                     prev_ae.ConstraintDefinitionId + prev_ae.ConstraintValue
                                   )
                        delim = ","
                    print( f'{ae.EventName+"("+ae.OccurrenceId+")":{AuditEvent.c_longest_name_length+3}}',
                       f'{ss:{5}}', f'{se:{3}}', b, prev_aes, bcnt, mcnt, lcnt, einv, iinv )
    def play(self, pretty):
        """interpret the job"""
        if pretty:
            print( "job:", self.JobDefinitionName )
        else:
            json = "{ \"SpecUpdateRate\": \"PT2M\","
            json += "\"MaxOutOfSequenceEvents\": 10,"
            json += "\"MaximumJobTime\": \"PT10M\","
            json += "\"JobCompletePeriod\": \"PT24H\","
            json += "\"Jobs\": [\n"
            json += "{ \"JobDefinitionName\": " + self.JobDefinitionName + ","
            json += "\"JobDeprecated\": false,"
            json += "\"JobTypeExpiryDate\": \"2022-04-11T18:08:00Z\","
            json += "\"StaleAuditEventDuration\": \"P99W\","
            json += "\"BlockedAuditEventDuration\": \"PT5M\","
            json += "\n\"EventRules\": [\n"
            print( json )
        for seq in self.sequences:
            seq.play(pretty)
        if not pretty:
            print( "\n]}]}\n" )

class SequenceDefn:
    """PLUS Sequence Definition"""
    instances = []
    c_current_sequence = None                              # set at creation, emptied at exit
    def __init__(self, name):
        self.SequenceName = name                           # created when the name is encountered
        if any( s.SequenceName == name for s in SequenceDefn.instances ):
            print( "ERROR:  duplicate sequence detected:", name )
            sys.exit()
        JobDefn.instances[-1].sequences.append(self)
        self.audit_events = []                             # appended with each new event encountered
        self.start_events = []                             # start_events get added by the first event
                                                           # ... that sees an empty list
                                                           # ... and by any event preceded by HIDE
        SequenceDefn.c_current_sequence = self
        SequenceDefn.instances.append(self)
    def play(self, pretty):
        """interpret the sequence"""
        if pretty:
            print( "seq:", self.SequenceName )
        for start_event in self.start_events:
            start_event.play(pretty, "")

class AuditEvent:
    """PLUS Audit Event Definition"""
    instances = []
    ApplicationName = "default"                            # not presently used
    BlockedAuditEventDuration = "PT1H"                     # default for AE Simulator
    StaleAuditEventDuration = "PT2H"                       # default for AE Simulator
    c_current_event = None                                 # set at creation, reset at sequence exit
    c_longest_name_length = 0                              # Keep longest name length for pretty printing.
    def __init__(self, name, occurrence):
        self.EventName = name
        if len( name ) > AuditEvent.c_longest_name_length:
            AuditEvent.c_longest_name_length = len( name )
        self.sequence = SequenceDefn.c_current_sequence
        if occurrence:
            if any( ae for ae in self.sequence.audit_events if ae.EventName == name and ae.OccurrenceId == occurrence ):
                print( "ERROR:  duplicate audit event detected:", name + "(" + occurrence + ")" )
                sys.exit()
            self.OccurrenceId = occurrence
        else:
            # here, we count previous occurrences and assign an incremented value
            items = [ae for ae in self.sequence.audit_events if ae.EventName == name]
            self.OccurrenceId = str( len(items) )
        self.SequenceStart = False                         # set when 'HIDE' precedes
        self.SequenceEnd = False                           # set when 'detach' follows
        self.isBreak = False                               # set when 'break' follows
        self.sequence.audit_events.append(self)
        if not self.sequence.start_events:                 # ... or when no starting event, yet
            self.sequence.start_events.append( self )
            self.SequenceStart = True
        self.previous_events = []                          # extended at creation when c_current_event exists
                                                           # emptied at sequence exit
        if Fork.instances:                                # get fork, split or if previous event
            if Fork.instances[-1].fork_point_usage:
                self.previous_events.append( Fork.instances[-1].fork_point_usage )
                Fork.instances[-1].fork_point_usage = None
            if Fork.instances[-1].merge_usage:            # get merge previous events
                self.previous_events.extend( Fork.instances[-1].merge_usage )
                Fork.instances.pop()                      # done with this Fork
        if AuditEvent.c_current_event:
            self.previous_events.append( PreviousAuditEvent( AuditEvent.c_current_event ) )
            AuditEvent.c_current_event = None
        # detect loop
        # if it exists but has no starting event, add this one
        if Loop.instances and not Loop.instances[-1].start_event:
            Loop.instances[-1].start_event = self
        # Interpret/play variables.
        self.visit_count = 0
        AuditEvent.c_current_event = self
        AuditEvent.instances.append(self)
    def play(self, pretty, delim):
        """interpret the event"""
        self.visit_count += 1
        next_aes = []
        eligible_next_aes = []
        xor_included = False
        ior_included = False # TODO:  need to select at least one
        # Find the next event(s) to play if they exist.
        # This requires collecting all events in the sequence that carry this event (self)
        # as a previous event.  The list needs to be reduced based upon the following rules:
        # (Note that contraints may be marked on the edges leading to next events.)
        #   default:  If there is only one next event with no constraints on the edge, play it.
        #   XOR:  for next events with XOR on the edge, select only one.
        #   IOR:  for next events with IOR on the edge, select only one.
        #   AND:  for next events with AND on the edge, select all of them.
        #   loop:  for exactly 2 next events with one of them having a lower index, prefer
        #          the lower index event (loop back) until a count has reached a threshold,
        #          then select the event following the loop.
        for next_ae in self.sequence.audit_events:
            paes = [pae for pae in next_ae.previous_events if pae.previous_event is self]
            if paes:
                eligible_next_aes.append( next_ae )
        # loop detection
        if len( eligible_next_aes ) == 2:
            if AuditEvent.instances.index( eligible_next_aes[0] ) < AuditEvent.instances.index( self ):
                # loop detected in 0 event
                if self.visit_count < 4:
                    # Loop back by selecting the lower index event.  Clear the go forward event.
                    eligible_next_aes.remove( eligible_next_aes[1] )
                else:
                    # Carry on.
                    eligible_next_aes.remove( eligible_next_aes[0] )
            elif AuditEvent.instances.index( eligible_next_aes[1] ) < AuditEvent.instances.index( self ):
                # loop detected in 1 event
                if self.visit_count < 4:
                    # Loop back by selecting the lower index event.  Clear the go forward event.
                    eligible_next_aes.remove( eligible_next_aes[0] )
                else:
                    # Carry on.
                    eligible_next_aes.remove( eligible_next_aes[1] )
        for next_ae in eligible_next_aes:
            paes = [pae for pae in next_ae.previous_events if pae.previous_event is self]
            if paes:
                for pae in paes:
                    # Check AND, IOR, XOR edges on the paes.
                    if "AND" == pae.ConstraintValue:
                        next_aes.append( next_ae )
                    elif not xor_included and "XOR" == pae.ConstraintValue:
                        next_aes.append( next_ae )
                        xor_included = True
                    elif not ior_included and "IOR" == pae.ConstraintValue:
                        next_aes.append( next_ae )
                        ior_included = True
                    elif "" == pae.ConstraintValue:
                        next_aes.append( next_ae )
        # Give some indication that we are forking.
        fork_count = len( next_aes )
        fork_text = "" if fork_count < 2 else "f" + str( fork_count )
        if pretty:
            print( self.EventName,
                   "[" + str( self.visit_count ) + "]" if self.visit_count > 1 else "",
                   fork_text )
        else:
            json = delim + "{ \"EventName\": \"" + self.EventName + "\","
            json += "\"OccurrenceId\": " + str( self.OccurrenceId ) + ","
            json += "\"ApplicationName\": \"" + AuditEvent.ApplicationName + "\","
            json += "\"BlockedAuditEventDuration\": \"" + AuditEvent.BlockedAuditEventDuration + "\","
            json += "\"StaleAuditEventDuration\": \"" + AuditEvent.StaleAuditEventDuration + "\""
            json += "}"
            print( json )
        for ae in next_aes:
            ae.play(pretty, ",")

# A previous audit event contains a reference to the previous event
# but may also contain attributes that decorate the "edge" from the
# previous event to the current event.
class PreviousAuditEvent:
    """PreviousAuditEvents are instances pointing to an AuditEvent"""
    instances = []
    def __init__(self, ae):
        self.previous_event = ae
        self.ConstraintValue = ""
        self.ConstraintDefinitionId = ""
        PreviousAuditEvent.instances.append(self)

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
        self.fork_point = None                             # c_current_event pushed as PreviousAuditEvent
                                                           # when 'split', 'fork', 'if' or 'switch' encountered
                                                           # popped at 'end split', 'end merge', 'endif' or 'endswitch'
        self.fork_point_usage = None                       # cached here each time 'split again', 'fork again',
                                                           # 'elsif' or 'else' encountered
        self.merge_inputs = []                             # c_current_event pushed when 'split again', 'fork again',
                                                           # 'case', 'end split', 'end fork', 'endswitch',
                                                           # 'elsif', 'else' or 'endif' entered
        self.merge_usage = []                              # used for previous events after 'end split',
                                                           # 'end fork', 'endswitch' and 'end if'
        Fork.c_scope += 1
        Fork.instances.append(self)
    def __del__(self):
        #Fork.print_forks()
        Fork.c_scope -= 1
    def begin(self):
        # instead of c_current_event, I might need to copy from the fork_point stack
        if AuditEvent.c_current_event: # We may be starting with HIDE.
            Fork.instances[-1].fork_point = PreviousAuditEvent( AuditEvent.c_current_event )
            AuditEvent.c_current_event = None
            Fork.instances[-1].fork_point.ConstraintValue = self.flavor
            Fork.instances[-1].fork_point.ConstraintDefinitionId = Fork.instances[-1].id
            Fork.instances[-1].fork_point_usage = Fork.instances[-1].fork_point
        else:
            # detecting a nested fork (combined split, fork and/or if)
            # Look to the previous (outer scope) fork in the stack.
            if Fork.instances[Fork.c_scope-1].fork_point_usage:
                Fork.instances[-1].fork_point = PreviousAuditEvent( Fork.instances[Fork.c_scope-1].fork_point_usage.previous_event )
                Fork.instances[-1].fork_point.ConstraintValue = self.flavor
                Fork.instances[-1].fork_point.ConstraintDefinitionId = Fork.instances[-1].id
                Fork.instances[-1].fork_point_usage = Fork.instances[-1].fork_point
    def again(self):
        if AuditEvent.c_current_event: # We may have 'detach'd and have no c_current_event.
            Fork.instances[-1].merge_inputs.append( PreviousAuditEvent( AuditEvent.c_current_event ) )
            AuditEvent.c_current_event = None
        if Fork.instances[-1].fork_point:
            Fork.instances[-1].fork_point_usage = Fork.instances[-1].fork_point
    def end(self):
        if AuditEvent.c_current_event: # We may have 'detach'd and have no c_current_event.
            self.merge_inputs.append( PreviousAuditEvent( AuditEvent.c_current_event ) )
            AuditEvent.c_current_event = None
        self.merge_usage.extend( Fork.instances[-1].merge_inputs )
        self.merge_inputs.clear()
        self.fork_point_usage = None
    def print_fork(self):
        merge_inputs = ""
        merge_usages = ""
        fp = ""
        fu = ""
        if self.fork_point:
            fp = ( self.fork_point.previous_event.EventName +
                   "-" + self.fork_point.ConstraintDefinitionId +
                   "-" + self.fork_point.ConstraintValue )
        if self.fork_point_usage:
            fu = ( self.fork_point_usage.previous_event.EventName +
                   "-" + self.fork_point_usage.ConstraintDefinitionId +
                   "-" + self.fork_point.ConstraintValue )
        if self.merge_inputs:
            for mi in self.merge_inputs:
                merge_inputs += mi.previous_event.EventName + mi.ConstraintValue
        if self.merge_usage:
            for mu in self.merge_usage:
                merge_usages += mu.previous_event.EventName + mu.ConstraintValue
        print( "Fork:", Fork.c_scope, self.flavor, "fp:" + fp, "fu:" + fu, "mis:" + merge_inputs, "mus:" + merge_usages )
    @classmethod
    def print_forks(cls):
        for f in Fork.instances:
            f.print_fork()

# Dynamic control must deal with forward references.
# During the walk, capture the audit EventNames and OccurrenceIds as text.
# At the end of the walk and before output, resolve all DynamicControls.
class DynamicControl:
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
        self.src_evt_txt = AuditEvent.c_current_event.EventName
        self.src_occ_txt = AuditEvent.c_current_event.OccurrenceId
        self.user_evt_txt = AuditEvent.c_current_event.EventName
        self.user_occ_txt = AuditEvent.c_current_event.OccurrenceId
        self.source_event = None                           # audit event hosting the control
        self.user_event = None                             # audit event to be dynamically tested
        DynamicControl.instances.append(self)
    @classmethod
    def resolve_event_linkage(cls):
        for dc in DynamicControl.instances:
            sae = [ae for ae in AuditEvent.instances if ae.EventName == dc.src_evt_txt and ae.OccurrenceId == dc.src_occ_txt]
            if sae:
                dc.source_event = sae[-1]
            else:
                print( "ERROR:  unresolved SRC event in dynamic control:", dc.DynamicControlName, "with name:", dc.src_evt_txt  )
                sys.exit()
            uae = [ae for ae in AuditEvent.instances if ae.EventName == dc.user_evt_txt and ae.OccurrenceId == dc.user_occ_txt]
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
class Invariant:
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
        self.user_evt_txt = ""                             # USER event textual EventName
        self.user_occ_txt = "0"                            # USER event textual OccurrenceId (default)
        self.source_event = None                           # audit event hosting the invariant
        self.user_events = []                              # audit events to be dynamically tested
        Invariant.instances.append(self)
    @classmethod
    def resolve_event_linkage(cls):
        for inv in Invariant.instances:
            #print( "Resolving invariants:", inv.src_evt_txt, inv.src_occ_txt, inv.user_evt_txt, inv.user_occ_txt )
            sae = [ae for ae in AuditEvent.instances if ae.EventName == inv.src_evt_txt and ae.OccurrenceId == inv.src_occ_txt]
            if sae:
                inv.source_event = sae[-1]
            uaes = [ae for ae in AuditEvent.instances if ae.EventName == inv.user_evt_txt and ae.OccurrenceId == inv.user_occ_txt]
            if uaes:
                # We can have more than one user for an invariant.
                for uae in uaes:
                    #print( "Resolving invariant users:", inv.src_evt_txt, inv.src_occ_txt, inv.user_evt_txt, inv.user_occ_txt )
                    inv.user_events.append( uae )
    @classmethod
    def output_json(cls):
        # Output invariants separately.
        if Invariant.instances:
            ijson = "["
            idelim = ""
            for invariant in Invariant.instances:
                ijson += idelim + "\n{"
                ijson += "\"EventDataName\": \"" + invariant.Name + "\","
                invariant_type = "INTRAJOBINV" if invariant.Type == "IINV" else "EXTRAJOBINV"
                ijson += "\"EventDataType\": \"" + invariant_type + "\","
                ijson += "\"SourceEventJobDefinitionName\": " + JobDefn.instances[-1].JobDefinitionName + ","
                ijson += "\"SourceEventType\": \"" + invariant.src_evt_txt + "\","
                ijson += "\"SourceOccurrenceId\": " + invariant.src_occ_txt + ","
                ijson += "\"UserEvents\": [\n"
                ijson += "{ \"UserEventName\": \"" + invariant.user_evt_txt + "\","
                ijson += "\"UserOccurrenceId\": " + invariant.user_occ_txt + ","
                ijson += "\"UserEventDataItemName\": \"" + invariant.Name + "\" }"
                ijson += "]\n"
                ijson += "}"
                idelim = ","
            ijson += "]\n"
            print( ijson )

class Loop:
    """data collected from PLUS repeat loop"""
    instances = []
    c_scope = 0
    def __init__(self):
        self.start_event = None                            # first event encountered
        Loop.instances.append(self)
