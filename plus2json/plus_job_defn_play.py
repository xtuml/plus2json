"""

Play out (interpret) the job definition.

"""

import datetime
import sys
import uuid
from os.path import abspath
from pathlib import Path
package_path = abspath(Path(__file__).parent)
sys.path.insert(0, package_path)
import plus_job_defn

# This file provides mixin methods to the 3 primary classes to
# interpret and "play out" the job definition.  It will produce
# a valid sequence of events based upon the forks, merges, loops
# and sequencing of audit event definitions.  Three forms of output
# are supported, one for playing out the audit events instances
# in JSON format, one for outputting AESimulator event template
# configuration and one for playout the events in a human readable
# form for visual inspection.

class JobDefn_play:
    """Play Job Definition"""
    c_idFactory = 0
    def __init__(self):
        self.jobId = None              # Identifier of an instance of this job.
    def play(self, flavor):
        """interpret the job"""
        JobDefn_play.c_idFactory += 1
        if 'pretty' == flavor:
            self.jobId = JobDefn_play.c_idFactory
        else:
            self.jobId = uuid.uuid4()
        j = ""
        if 'pretty' == flavor:
            j += 'job:' + self.JobDefinitionName + '\n'
        elif 'aesim' == flavor:
            j += self.aesim_config_begin()
        elif 'aestest' == flavor:
            j += plus_job_defn.JobDefn.aesim_test_header()
            j += self.aesim_test()
        else:
            j += '[' # event instances
        # Play out the sequences.
        for seq in self.sequences:
            j += seq.play( flavor, self )
        if 'pretty' == flavor:
            j = j # NOP
        elif 'aesim' == flavor:
            j += self.aesim_config_end()
        elif 'aestest' == flavor:
            j += plus_job_defn.JobDefn.aesim_test_footer()
        else:
            j += ']' # event instances
        return j

class SequenceDefn_play:
    def play( self, flavor, job_defn ):
        """interpret the sequence"""
        j = ""
        if 'pretty' == flavor:
            j += 'seq:' + self.SequenceName + '\n'
        for start_event in self.start_events:
            j += start_event.play( flavor, "", job_defn, None )
        if 'aestest' == flavor:
            j += '"'
        return j

class AuditEvent_play:
    c_idFactory = 0
    def __init__(self):
        self.visit_count = 0             # Count visits to this audit event.
        self.eventId = None              # Identifier of an instance of this event.
        self.previousEventIds = []       # Id(s) of previous events to this instance.
    def drill_back_for_constraint_type( self, scope ):
        """drill back along previous events to find AND constraint"""
        # It is important to consider events only at the previous scope only
        # and not nested inside previous scopes.
        # TODO:  using simply the zero'th previous event in the list may be naive
        if self.previous_events:
            if "" == self.previous_events[0].ConstraintValue and self.previous_events[0].previous_event.scope == scope:
                return self.previous_events[0].previous_event.drill_back_for_constraint_type( scope )
            else:
                return self.previous_events[0].ConstraintValue
        else:
            return ""
    def play( self, flavor, delim, job_defn, previous_event_id ):
        """interpret the event"""
        if previous_event_id:
            self.previousEventIds.append( previous_event_id )
        # TODO:  Detect a merge point and pass until the branches have completed.
        # Recursively traverse prevs to see if there is an AND constraint.
        if len( self.previous_events ) > len( self.previousEventIds ) and self.drill_back_for_constraint_type( self.scope+1 ) == 'AND':
            return ""
        self.visit_count += 1
        AuditEvent_play.c_idFactory += 1
        if 'pretty' == flavor:
            self.eventId = AuditEvent_play.c_idFactory
        else:
            self.eventId = uuid.uuid4()
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
            if plus_job_defn.AuditEvent.instances.index( eligible_next_aes[0] ) <= plus_job_defn.AuditEvent.instances.index( self ):
                # loop detected in 0 event
                if self.visit_count < 4:
                    # Loop back by selecting the lower index event.  Clear the go forward event.
                    eligible_next_aes.remove( eligible_next_aes[1] )
                else:
                    # Carry on.
                    eligible_next_aes.remove( eligible_next_aes[0] )
            elif plus_job_defn.AuditEvent.instances.index( eligible_next_aes[1] ) <= plus_job_defn.AuditEvent.instances.index( self ):
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
                    if 'AND' == pae.ConstraintValue:
                        next_aes.append( next_ae )
                    elif not xor_included and 'XOR' == pae.ConstraintValue:
                        next_aes.append( next_ae )
                        xor_included = True
                    elif not ior_included and 'IOR' == pae.ConstraintValue:
                        next_aes.append( next_ae )
                        ior_included = True
                    elif "" == pae.ConstraintValue:
                        next_aes.append( next_ae )
        j = ""
        # Give some indication that we are forking.
        fork_count = len( eligible_next_aes )
        fork_text = "" if fork_count < 2 else 'f' + str( fork_count )
        # Give some indication that we are merging.
        merge_count = len( self.previous_events )
        merge_text = "" if merge_count < 2 else 'm' + str( merge_count )
        if 'pretty' == flavor:
            visit_count_string = '[' + str( self.visit_count ) + ']' if self.visit_count > 1 else ""
            j += self.EventName + ":" + str( self.eventId ) + " " +  visit_count_string + fork_text + merge_text + " "
            if self.previousEventIds:
                j += 'peids:'
                if 1 == len( self.previousEventIds ):
                    j += str( self.previousEventIds[-1] )
                else:
                    j += '['
                    peid_delim = ""
                    for peid in self.previousEventIds:
                        j += peid_delim + str( peid )
                        peid_delim = ","
                    j += ']'
                self.previousEventIds.clear()
            j += '\n'
        elif 'aesim' == flavor:
            j += self.aesim_config( delim )
        elif 'aestest' == flavor:
            j += self.aesim_test( delim )
        else:
            # TODO - This is a start at actually producing audit event instances.
            j += delim + '{'
            j += '"jobName": "' + job_defn.JobDefinitionName + '",'
            j += '"jobId": "' + str( job_defn.jobId ) + '",'
            j += '"eventType": "' + self.EventName + '",'
            j += '"eventId": "' + str( self.eventId ) + '",'
            if self.previousEventIds:
                j += '"previousEventIds": '
                if 1 == len( self.previousEventIds ):
                    j += '"' + str( self.previousEventIds[-1] ) + '",'
                else:
                    j += '['
                    peid_delim = ""
                    for peid in self.previousEventIds:
                        j += peid_delim + '"' + str( peid ) + '"'
                        peid_delim = ","
                    j += '],'
            j += '"timestamp": "' + '{:%Y-%m-%dT%H:%M:%SZ}'.format(datetime.datetime.now()) + '",'
            j += '"applicationName": "' + plus_job_defn.AuditEvent.ApplicationName + '"'
            j += '}'
        for ae in next_aes:
            j += ae.play( flavor, ",", job_defn, self.eventId )
        return j
