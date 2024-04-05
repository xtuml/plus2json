# loops with 1 event
# event after loop at end of fork tine
# event data items

import sys
import xtuml
import time
import logging

from datetime import datetime, timedelta

from xtuml import relate, unrelate, delete, order_by, navigate_many as many, navigate_one as one, navigate_any as any

from .populate import EventDataType  # TODO
from .populate import ConstraintType  # TODO
from .populate import flatten

logger = logging.getLogger(__name__)

visited_aeds = []              # audit event definitions that have been processed (loop detection)
loop_count = 0                 # TODO - consider supporting nested loops

def JobDefn_plus(self):
    ''' render PLUS job definition '''
    m = self.__metaclass__.metamodel
    opts = m.select_any('_Options')
    logger.debug( f'JobDefn_plus:  rendering job definition {self.Name}' )
    p = ""
    p += "@startuml\n"
    p += f'partition "{self.Name}"' + ' {\n'
    # render sequences
    for seq_defn in many(self).SeqDefn[1]():
        p += SeqDefn_plus(seq_defn)
    # render packages
    for pkg_defn in many(self).PkgDefn[20]():
        p += PkgDefn_plus(pkg_defn)
    p += "}\n"
    p += "@enduml"
    return p


def SeqDefn_plus(self):
    ''' render PLUS mapping for sequence '''
    logger.debug( f'SeqDefn_plus:  rendering sequence {self.Name}' )
    p = ""
    p += f'  group "{self.Name}"\n'
    # Render fragments (fork, loop or event) for possibly multiple start events.
    sequence_starts = many(self).AuditEventDefn[13]()
    for first_audit_event_defn in sequence_starts:
        s, next_aed = Fragment_plus( first_audit_event_defn )
        p += s
        while next_aed:
            s, next_aed = Fragment_plus( next_aed )
            p += s
    p += "  end group\n"
    return p


def PkgDefn_plus(self):
    ''' render PLUS mapping for package of unhappy events '''
    logger.debug( f'PkgDefn_plus:  rendering package {self.Name}' )
    p = ""
    p += f'  package "{self.Name}"' + ' {\n'
    # render unhappy events
    for unhappy_event_defn in many(self).UnhappyEventDefn[21]():
        p += UnhappyEventDefn_plus(unhappy_event_defn)
    p += "  }\n"
    return p


def Fragment_plus(audit_event_defn):
    ''' render PLUS for the various control structures '''
    p = ""
    next_aed = None
    if audit_event_defn:
        logger.debug( f'Fragment_plus: {audit_event_defn.Name}' )
    else:
        return p, next_aed
    # Detect fork, loop, audit event definition.
    if Fork_detect( audit_event_defn ): 
        s, next_aed = Fork_plus( audit_event_defn )
        p += s
    elif Loop_detect( audit_event_defn ): 
        s, next_aed = Loop_plus( audit_event_defn )
        p += s
    else:
        s, next_aeds = AuditEventDefn_plus( audit_event_defn )
        p += s
        # Multiple next audit event definitions are possible.
        # TODO - Try to return a next_aed that has not been visited.
        for next_aed in next_aeds:
            if not next_aed in visited_aeds:
                break
    return p, next_aed


def Fork_plus(audit_event_defn):
    ''' render PLUS for fork and switch '''

    # Render the top audit event definition.
    # Render the tines.
    # Return the merge point as next (if fork merges).
    logger.debug( f'Fork_plus:  entering {audit_event_defn.Name}' )
    p = ""
    next_aed = None
    # Render the top of the fork (the node that has multiple edges).
    s, next_aeds = AuditEventDefn_plus(audit_event_defn)
    p += s
    # Render the PLUS instruction for the type of fork.
    # Fork_detect already assured us that we have consistent constraints.
    const_defn = any(audit_event_defn).EvtSucc[3, 'precedes'].ConstDefn[16]()
    if const_defn.Type == ConstraintType.AND:
        p += '    fork\n'
    elif const_defn.Type == ConstraintType.XOR:
        p += f'    switch ( "{const_defn.Id}" )\n'
        p += f'    case ( "1" )\n'
    else:
        logger.error( f'Fork_plus:  unsupported constraint type' )
        p += '    UNSUPPORTED FORK\n'
    i = 1
    j = len(next_aeds)
    for tine_aed in next_aeds:
        s, tine_next_aed = Tine_plus(tine_aed)
        p += s
        # Some tines will detach and not have a next.
        # Keep a next from any tine, because it will be the merge point.
        if tine_next_aed:
            next_aed = tine_next_aed
        if i < j:
            i = i + 1
            if const_defn.Type == ConstraintType.AND:
                p += '    fork again\n'
            elif const_defn.Type == ConstraintType.XOR:
                p += f'    case ( "{str(i)}" )\n'
    if const_defn.Type == ConstraintType.AND:
        p += '    end fork\n'
    elif const_defn.Type == ConstraintType.XOR:
        p += '    endswitch\n'
    logger.debug( f'Fork_plus:  exiting {audit_event_defn.Name}' )
    return p, next_aed


def Loop_plus(audit_event_defn):
    ''' render PLUS for a loop '''
    # Render the loop tine.
    logger.debug( f'Loop_plus:  entering {audit_event_defn.Name}' )
    p = ""
    next_aed = None
    global loop_count
    loop_count += 1
    p += "    repeat\n"
    s, next_aed = Tine_plus( audit_event_defn )
    p += s
    p += "    repeat while\n"
    loop_count -= 1
        
    logger.debug( f'Loop_plus:  exiting {audit_event_defn.Name}' )
    return p, next_aed


def Tine_plus(audit_event_defn):
    ''' render PLUS for a tine (sequence of fragments) '''
    # Play out fragments until the end of the tine is detected.
    logger.debug( f'Tine_plus:  entering {audit_event_defn.Name}' )
    p = ""
    s, next_aed = Fragment_plus( audit_event_defn )
    p += s
    # The end of a tine is either:
    #   a dead end (no next_aed)
    #   just ahead of a merge point (multiple prev_aeds) but not a loop start
    #   a loop end
    if Loop_end_detect( audit_event_defn ):
        # detecting single event loop tine
        return p, next_aed

    # Detect the start of a loop and distinguish it from the end of a tine (merge point).
    # Detect merge point as next event with multiple precessors but not a loop.
    start_of_loop = False
    if next_aed:
        start_of_loop = Loop_detect(next_aed)

    precessor_aeds = many(next_aed).AuditEventDefn[3,'follows']()
    # Tine continues when there is a single follow-on event or when a loop is starting.
    while len(precessor_aeds) == 1 or start_of_loop:
        loop_end_detected = Loop_end_detect( next_aed )
        s, next_aed = Fragment_plus(next_aed)
        p += s
        # detect end of loop
        # We rendered the end of loop event.  Check/detect end of loop.
        if next_aed:
            if loop_end_detected:
                break
            precessor_aeds = many(next_aed).AuditEventDefn[3,'follows']()
            start_of_loop = Loop_detect( next_aed )
        else:
            break
    logger.debug( f'Tine_plus:  exiting {audit_event_defn.Name}' )
    return p, next_aed


def AuditEventDefn_plus(self):
    ''' render PLUS for an audit event definition '''
    logger.debug( f'AuditEvent_defn_plus: {self.Name}' )
    p = ""
    p += f'    :{self.Name};\n'
    next_aeds = many(self).AuditEventDefn[3,'precedes']()
    if self.IsBreak:
        p += "    break\n"
    elif not next_aeds:
        p += "    detach\n"
    # Keep track of events that have been processed.
    visited_aeds.append( self )
    return p, next_aeds


def UnhappyEventDefn_plus(self):
    ''' render PLUS for unhappy event definition '''
    logger.debug( f'UnhappyEventDefn_plus: {self.Name}' )
    p = ""
    p += f'    :{self.Name};\n'
    p += f'    kill\n'
    return p

def Loop_detect(audit_event_defn):
    ''' detect the start of a loop '''
    if not audit_event_defn:
        return False
    logger.debug( f'Loop_detect: {audit_event_defn.Name}' )
    # We are starting a loop if the given event is downstream in the graph.
    if loop_count > 0:
        # only try to detect a loop when we are not already in one
        return False
    depth_to_detect = 20  # arbitrary max depth to search
    next_aeds = many(audit_event_defn).AuditEventDefn[3,'precedes']()
    while depth_to_detect > 0:
        if not next_aeds:
            return False
        if audit_event_defn in next_aeds:
            logger.debug( f'Loop_detect: loop detected {audit_event_defn.Name}' )
            return True
        depth_to_detect = depth_to_detect - 1
        next_aeds = many(next_aeds).AuditEventDefn[3,'precedes']()
    return False

def Fork_detect(audit_event_defn):
    ''' detect the start of a fork '''
    # Fork is detected by having multiple successions with the same constraint.
    logger.debug( f'Fork_detect: detecting fork at {audit_event_defn.Name}' )
    fork_detected = False
    evt_succs = many(audit_event_defn).EvtSucc[3,'precedes']()
    if len(evt_succs) > 1:
        fork_detected = True
        constraint_type = None
        const_defn = None
        for evt_succ in evt_succs:
            const_defn = one(evt_succ).ConstDefn[16]()
            if const_defn:
                if constraint_type:
                    if constraint_type != const_defn.Type:
                        # TODO mismatched constraints, maybe nested structures?
                        logger.debug( f'Fork_detect:  mismatched constraints detected at {audit_event_defn.Name}' )
                        fork_detected = False
                        break
                else:
                    # saving constraint type of this succession to compare to the others
                    constraint_type = const_defn.Type
            else:
                # succession with no constraint, probably looping
                fork_detected = False
                break
    return fork_detected

def Loop_end_detect(audit_event_defn):
    ''' detect the end of a loop '''
    # The end of a loop is detected by having exactly two successions with no
    # constraints, one for going onward and one for looping backward.
    # TODO This limits us to not being able to do close nesting of constructs.
    # TODO We could take into account the idea that one of the successions has been visited and one has not.
    logger.debug( f'Loop_end_detect: detecting loop end at {audit_event_defn.Name}' )
    loop_end_detected = False
    if loop_count > 0:
        evt_succs = many(audit_event_defn).EvtSucc[3,'precedes']()
        if len(evt_succs) == 2:
            for evt_succ in evt_succs:
                const_defn = one(evt_succ).ConstDefn[16]()
                if const_defn:
                    loop_end_detected = False
                    break
                else:
                    logger.debug( f'Loop_end_detect: DETECTED loop end at {audit_event_defn.Name}' )
                    loop_end_detected = True
    return loop_end_detected

