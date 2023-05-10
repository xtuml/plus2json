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
        for seq in self.R1_SequenceDefn_defines:
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
        for start_event in self.R13_AuditEventDefn_starts:
            j += start_event.play( flavor, "", job_defn, None )
        if 'aestest' == flavor:
            j += '"'
        return j

class AuditEventDefn_play:
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
        if self.R3_PreviousAuditEventDefn:
            if "" == self.R3_PreviousAuditEventDefn[0].ConstraintValue and self.R3_PreviousAuditEventDefn[0].R3_AuditEventDefn_precedes.scope == scope:
                return self.R3_PreviousAuditEventDefn[0].R3_AuditEventDefn_precedes.drill_back_for_constraint_type( scope )
            else:
                return self.R3_PreviousAuditEventDefn[0].ConstraintValue
        else:
            return ""
    def play( self, flavor, delim, job_defn, previous_event_id ):
        """interpret the event"""
        if previous_event_id:
            self.previousEventIds.append( previous_event_id )
        # TODO:  Detect a merge point and pass until the branches have completed.
        # Recursively traverse prevs to see if there is an AND constraint.
        if len( self.R3_PreviousAuditEventDefn ) > len( self.previousEventIds ) and self.drill_back_for_constraint_type( self.scope+1 ) == 'AND':
            return ""
        self.visit_count += 1
        AuditEventDefn_play.c_idFactory += 1
        if 'pretty' == flavor:
            self.eventId = AuditEventDefn_play.c_idFactory
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
        for next_ae in self.R2_SequenceDefn.R2_AuditEventDefn_defines:
            paes = [pae for pae in next_ae.R3_PreviousAuditEventDefn if pae.R3_AuditEventDefn_precedes is self]
            if paes:
                eligible_next_aes.append( next_ae )
                # (instance) branch detection
                # select many dcs related by self->DynamicControl[R10]
                user_dcs = [dc for dc in plus_job_defn.DynamicControl.instances if dc.R10_AuditEventDefn is self]
                for user_dc in user_dcs:
                    if user_dc.DynamicControlType == "BRANCHCOUNT":
                        for i in range( user_dc.value-1 ): # duplicate next_ae branch count - 1 times
                            eligible_next_aes.append( next_ae )
        # loop detection
        if len( eligible_next_aes ) == 2:
            if plus_job_defn.AuditEventDefn.instances.index( eligible_next_aes[0] ) <= plus_job_defn.AuditEventDefn.instances.index( self ):
                # loop detected in 0 event
                if self.visit_count < 4:
                    # Loop back by selecting the lower index event.  Clear the go forward event.
                    eligible_next_aes.remove( eligible_next_aes[1] )
                else:
                    # Carry on.
                    eligible_next_aes.remove( eligible_next_aes[0] )
            elif plus_job_defn.AuditEventDefn.instances.index( eligible_next_aes[1] ) <= plus_job_defn.AuditEventDefn.instances.index( self ):
                # loop detected in 1 event
                if self.visit_count < 4:
                    # Loop back by selecting the lower index event.  Clear the go forward event.
                    eligible_next_aes.remove( eligible_next_aes[0] )
                else:
                    # Carry on.
                    eligible_next_aes.remove( eligible_next_aes[1] )
        for next_ae in eligible_next_aes:
            paes = [pae for pae in next_ae.R3_PreviousAuditEventDefn if pae.R3_AuditEventDefn_precedes is self]
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
        merge_count = len( self.R3_PreviousAuditEventDefn )
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
            else:
                j += '       '
            # select many dcs related by self->DynamicControl[R9]
            source_dcs = [dc for dc in plus_job_defn.DynamicControl.instances if dc.R9_AuditEventDefn is self]
            for dc in source_dcs:
                j += ' s-'
                j += dc.play( flavor )
            # select many dcs related by self->DynamicControl[R10]
            user_dcs = [dc for dc in plus_job_defn.DynamicControl.instances if dc.R10_AuditEventDefn is self]
            for dc in user_dcs:
                j += ' u-'
                j += dc.play( flavor )
            # select many invs related by self->Invariant[R11]
            source_invs = [inv for inv in plus_job_defn.Invariant.instances if inv.R11_AuditEventDefn is self]
            for inv in source_invs:
                j += ' s-'
                j += inv.play( flavor )
            # select many invs related by self->Invariant[R12]
            user_invs = [inv for inv in plus_job_defn.Invariant.instances if self in inv.R12_AuditEventDefn]
            for inv in user_invs:
                j += ' u-'
                j += inv.play( flavor )
            j += '\n'
        elif 'aesim' == flavor:
            j += self.aesim_config( delim )
        elif 'aestest' == flavor:
            j += self.aesim_test( delim )
        else:
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
                self.previousEventIds.clear()
            # Dynamic controls are attached only to the source audit event.  No output for user events.
            # select many source_dcs related by self->DynamicControl[R9]
            source_dcs = [dc for dc in plus_job_defn.DynamicControl.instances if dc.R9_AuditEventDefn is self]
            if source_dcs:
                delim = ""
                for dc in source_dcs:
                    j += delim + dc.play( flavor )
                    delim = ','
                j += ','
            # select many invs related by self->Invariant[R11]
            source_invs = [inv for inv in plus_job_defn.Invariant.instances if inv.R11_AuditEventDefn is self]
            # select many invs related by self->Invariant[R12]
            user_invs = [inv for inv in plus_job_defn.Invariant.instances if self in inv.R12_AuditEventDefn]
            if source_invs or user_invs:
                delim = ""
                for inv in source_invs:
                    j += delim + inv.play( flavor )
                    delim = ','
                for inv in user_invs:
                    j += delim + inv.play( flavor )
                    delim = ','
                j += ','
            j += '"timestamp": "' + '{:%Y-%m-%dT%H:%M:%SZ}'.format(datetime.datetime.utcnow()) + '",'
            j += '"applicationName": "' + plus_job_defn.AuditEventDefn.ApplicationName + '"'
            j += '}'
        for ae in next_aes:
            j += ae.play( flavor, ",", job_defn, self.eventId )
        return j

class DynamicControl_play:
    c_idFactory = 0
    def __init__(self):
        DynamicControl_play.c_idFactory += 1
        self.iId = DynamicControl_play.c_idFactory     # pretty printable id
        self.value = 4                                 # value of an instance of this dynamic control
    def play( self, flavor ):
        j = ""
        if 'pretty' == flavor:
            if self.DynamicControlType == "BRANCHCOUNT":
                j += "bc:"
            elif self.DynamicControlType == "MERGECOUNT":
                j += "mc:"
            elif self.DynamicControlType == "LOOPCOUNT":
                j += "lc:"
            else:
                print( "ERROR:  malformed dynamic control" )
                sys.exit()
            j += self.DynamicControlName + ':' + str( self.value )
        else:
            j += '"' + self.DynamicControlName + '": { "dataItemType":' + '"' + self.DynamicControlType + '",'
            j += '"value": ' + str( self.value ) + ' }'
        return j

class Invariant_play:
    c_idFactory = 0
    def __init__(self, is_extern):
        Invariant_play.c_idFactory += 1
        self.iId = str( Invariant_play.c_idFactory ) # pretty printable id
        self.value = str( uuid.uuid4() )             # value of an instance of this invariant
        self.is_extern = is_extern                   # external declaration of extra-job invariant
    def play( self, flavor ):
        j = ""
        if self.Type == "EINV":
            # An 'extern' is an extra-job invariant from a previous source job.
            if self.is_extern:
                # It is loaded from the invariant persistent store.
                i = self.load_named_invariant( self.Name, self.SourceJobDefinitionName )
                if i:
                    self.value = i[1]
                else:
                    plus_job_defn.eprint( "Named invariant:", self.Name, "not found in invariant store." )
            else:
                # It is persisted to the invariant store.
                i = ( self.Name, self.value,
                    '{:%Y-%m-%dT%H:%M:%SZ}'.format(datetime.datetime.utcnow()),
                    '{:%Y-%m-%dT%H:%M:%SZ}'.format(datetime.datetime.utcnow() + datetime.timedelta(days=30)),
                    self.SourceJobDefinitionName, "", "" )
                self.persist( i )
        if 'pretty' == flavor:
            if self.Type == "EINV":
                j += "einv:" + self.Name + ":" + self.value[0]
            elif self.Type == "IINV":
                j += "iinv:" + self.Name + ":" + self.value[0]
            else:
                print( "ERROR:  malformed invariant type" )
                sys.exit()
        else:
            j += '"' + self.Name + '": "' + self.value + '"'
        return j
