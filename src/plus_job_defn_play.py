"""

Play out (interpret) the job definition.

"""

import datetime
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
    def play(self, flavor):
        """interpret the job"""
        json = ""
        if "pretty" == flavor:
            print( "job:", self.JobDefinitionName )
        elif "aesim" == flavor:
            json = self.aesim_config()
        else:
            print( "[" )
        # Play out the sequences.
        for seq in self.sequences:
            seq.play( flavor, self )
        if "pretty" == flavor:
            print( json ) # NOP
        elif "aesim" == flavor:
            print( json )
        else:
            print( "]" )

class SequenceDefn_play:
    def play( self, flavor, job_defn ):
        """interpret the sequence"""
        if "pretty" == flavor:
            print( "seq:", self.SequenceName )
        for start_event in self.start_events:
            start_event.play( flavor, "", job_defn )

class AuditEvent_play:
    def __init__(self):
        self.visit_count = 0                     # Count visits to this audit event.
    def play(self, flavor, delim, job_defn):
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
            if plus_job_defn.AuditEvent.instances.index( eligible_next_aes[0] ) < plus_job_defn.AuditEvent.instances.index( self ):
                # loop detected in 0 event
                if self.visit_count < 4:
                    # Loop back by selecting the lower index event.  Clear the go forward event.
                    eligible_next_aes.remove( eligible_next_aes[1] )
                else:
                    # Carry on.
                    eligible_next_aes.remove( eligible_next_aes[0] )
            elif plus_job_defn.AuditEvent.instances.index( eligible_next_aes[1] ) < plus_job_defn.AuditEvent.instances.index( self ):
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
        if "pretty" == flavor:
            print( self.EventName,
                   "[" + str( self.visit_count ) + "]" if self.visit_count > 1 else "",
                   fork_text )
        elif "aesim" == flavor:
            self.aesim_config( delim )
        else:
            # TODO - This is a start at actually simulating audit events.
            json = delim + "{"
            json += "\"timestamp\": \"" + "{:%Y-%m-%dT%H:%M:%SZ}".format(datetime.datetime.now()) + "\","
            json += "\"applicationName\": \"" + plus_job_defn.AuditEvent.ApplicationName + "\","
            json += "\"jobId\": \"" + "job UUID here" + "\","
            json += "\"jobName\": " + job_defn.JobDefinitionName + ","
            json += "\"eventType\": \"" + self.EventName + "\","
            json += "\"eventId\": \"" + "event UUID here" + "\""
            json += "}"
            print( json )
        for ae in next_aes:
            ae.play( flavor, ",", job_defn )
