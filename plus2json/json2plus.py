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

def JobDefn_plus(job_defn):
    ''' render PLUS job definition '''
    m = job_defn.__metaclass__.metamodel
    opts = m.select_any('_Options')
    logger.debug( f'JobDefn_plus:  rendering job definition {job_defn.Name}' )
    p = ""
    p += "@startuml\n"
    p += f'partition "{job_defn.Name}"' + ' {\n'
    # render sequences
    for seq_defn in many(job_defn).SeqDefn[1]():
        p += SeqDefn_plus(seq_defn)
    # render packages
    for pkg_defn in many(job_defn).PkgDefn[20]():
        p += PkgDefn_plus(pkg_defn)
    p += "}\n"
    p += "@enduml"
    return p


def SeqDefn_plus(seq_defn):
    ''' render PLUS mapping for sequence '''
    logger.debug( f'SeqDefn_plus:  rendering sequence {seq_defn.Name}' )
    p = ""
    p += f'  group "{seq_defn.Name}"\n'
    # Render fragments (fork, loop or event) for possibly multiple start events.
    sequence_starts = many(seq_defn).AuditEventDefn[13]()
    for first_audit_event_defn in sequence_starts:
        s, next_aed = Fragment_plus( first_audit_event_defn )
        p += s
        while next_aed:
            s, next_aed = Fragment_plus( next_aed )
            p += s
    p += "  end group\n"
    return p


def PkgDefn_plus(pkg_defn):
    ''' render PLUS mapping for package of unhappy events '''
    logger.debug( f'PkgDefn_plus:  rendering package {pkg_defn.Name}' )
    p = ""
    p += f'  package "{pkg_defn.Name}"' + ' {\n'
    # render unhappy events
    for unhappy_event_defn in many(pkg_defn).UnhappyEventDefn[21]():
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
        s, tine_next_aed = Fork_Tine_plus(tine_aed)
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
    s, next_aed = Loop_Tine_plus( audit_event_defn )
    p += s
    p += "    repeat while\n"
    loop_count -= 1
        
    logger.debug( f'Loop_plus:  exiting {audit_event_defn.Name}' )
    return p, next_aed


def Fork_Tine_plus(audit_event_defn):
    ''' render PLUS for a fork tine (sequence of fragments) '''
    # Play out fragments until the end of the tine is detected.
    logger.debug( f'Fork_Tine_plus:  entering {audit_event_defn.Name}' )
    p = ""
    s, next_aed = Fragment_plus( audit_event_defn )
    p += s
    # The end of a fork tine is either:
    #   a dead end (no next_aed)
    #   just ahead of a merge point (multiple prev_aeds) but not a loop start

    # Detect the start of a loop or fork.
    start_of_loop = Loop_detect( next_aed )
    fork_detected = Fork_detect( audit_event_defn )

    precessor_aeds = many(next_aed).AuditEventDefn[3,'follows']()
    # Tine continues when there is a single follow-on event or when a loop or fork is starting.
    # Detect merge point as next event with multiple precessors but not a loop.
    # TODO - CDS - Apr 10 - A fork fragment will return with an event that has more than 1 next aed.
    # TODO The merge point may not have multiple precessors because of 'detach'!
    # TODO Is there a way to detect the end of the tine?
    # TODO Perhaps we need to keep track of the fork count and then do math as we go along including subtraction with detach?
    # TODO We need Fork_find_merge() to identify the audit event that is the merge point.
    # TODO This could be done by looping through the head of tines, looking forward, and matching a common downstream event.
    # TODO Perhaps we can be smart by recognizing tines with detach... meaning ending without encountering an event with multiple precessors... no, that is the same as what we see.
    while len(precessor_aeds) == 1 or start_of_loop or fork_detected:
        s, next_aed = Fragment_plus(next_aed)
        p += s
        # We rendered the end of loop event.  Check/detect end of loop.
        if next_aed:
            precessor_aeds = many(next_aed).AuditEventDefn[3,'follows']()
            start_of_loop = Loop_detect( next_aed )
            fork_detected = Fork_detect( next_aed )
        else:
            break
    logger.debug( f'Fork_Tine_plus:  exiting {audit_event_defn.Name}' )
    return p, next_aed


def Loop_Tine_plus(audit_event_defn):
    ''' render PLUS for a loop tine (sequence of fragments) '''
    # Play out fragments until the end of the tine is detected.
    logger.debug( f'Loop_Tine_plus:  entering {audit_event_defn.Name}' )
    p = ""
    next_aed = audit_event_defn
    loop_end_detected = False
    escape = 30
    while not loop_end_detected:
        loop_end_detected = Loop_end_detect( next_aed )
        s, next_aed = Fragment_plus( next_aed )
        p += s
        escape = escape - 1
        # TODO
        if escape == 0:
            p += "ESCAPING LOOP... probably fork snugged into end of loop\n"
            break
    logger.debug( f'Loop_Tine_plus:  exiting {audit_event_defn.Name}' )
    return p, next_aed


def AuditEventDefn_plus(audit_event_defn):
    ''' render PLUS for an audit event definition '''
    logger.debug( f'AuditEvent_defn_plus: {audit_event_defn.Name}' )
    p = ""
    p += f'    :{audit_event_defn.Name};\n'
    next_aeds = many(audit_event_defn).AuditEventDefn[3,'precedes']()
    if audit_event_defn.IsBreak:
        p += "    break\n"
    elif not next_aeds:
        p += "    detach\n"
    # Keep track of events that have been processed.
    visited_aeds.append( audit_event_defn )
    return p, next_aeds


def UnhappyEventDefn_plus(unhappy_event_defn):
    ''' render PLUS for unhappy event definition '''
    logger.debug( f'UnhappyEventDefn_plus: {unhappy_event_defn.Name}' )
    p = ""
    p += f'    :{unhappy_event_defn.Name};\n'
    p += f'    kill\n'
    return p

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
    if fork_detected:
        logger.debug( f'Fork_detect: DETECTED fork at {audit_event_defn.Name}' )
    return fork_detected

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
            logger.debug( f'Loop_detect: loop DETECTED {audit_event_defn.Name}' )
            return True
        depth_to_detect = depth_to_detect - 1
        next_aeds = many(next_aeds).AuditEventDefn[3,'precedes']()
    return False

def Loop_end_detect(audit_event_defn):
    ''' detect the end of a loop '''
    # The end of a loop is detected by having exactly two successions with no
    # constraints, one for going onward and one for looping backward.
    # TODO This limits us to not being able to do close nesting of constructs.
    # TODO We could take into account the idea that one of the successions has been visited and one has not.
    # TODO If this is a fork (snugged up to end of loop), we do not know how to detect end of loop.
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
        # TODO - Detect the end of loop when the fragment is a fork.
        if not loop_end_detected:
            logger.debug( f'Loop_end_detect: attempting fork in loop' )
            if audit_event_defn:
                if Fork_detect( audit_event_defn ):
                    logger.debug( f'Loop_end_detect: fork in loop at {audit_event_defn.Name}' )
    return loop_end_detected

def json2plus_populate(populator, filename, j):
    ''' populate model of PLUS from JSON object '''

    logger.debug( f'json2plus_populate:  {filename}' )
    # create a new job
    job_defn = populator.m.new('JobDefn', Name=j['JobDefinitionName'] )
    # add default pathway
    pathway = populator.m.new('Pathway', Number=1 )
    relate(job_defn, pathway, 60)

    # Create the audit events in a first pass.
    previous_fragment = None
    for event in j['Events']:
        # Create audit event definition.
        fragment = populator.m.new('Fragment')
        aed = populator.m.new('AuditEventDefn',
                              Name=event['EventName'],
                              OccurrenceId=event['OccurrenceId'],
                              Application=event['Application'])
        relate(fragment, aed, 56)
        # Create and relate the sequence if not already in place.
        seq_defn = one(job_defn).SeqDefn[1](lambda sel: sel.Name == event['SequenceName'])
        if not seq_defn:
            seq_defn = populator.m.new('SeqDefn', Name=event['SequenceName'])
            logger.debug( f'json2plus: creating sequence {seq_defn.Name}' )
            relate(seq_defn, job_defn, 1)
        relate(seq_defn, aed, 2)
        if 'SequenceStart' in event and event['SequenceStart']:
            relate(seq_defn, aed, 13)
            relate(seq_defn, fragment, 58)
            logger.debug( f'json2plus: detected start event {aed.Name}' )
        if 'SequenceEnd' in event and event['SequenceEnd']:
            relate(seq_defn, aed, 15)
            logger.debug( f'json2plus: detected end event {aed.Name}' )
        if 'IsBreak' in event and event['IsBreak']:
            aed.IsBreak = True
            logger.debug( f'json2plus: detected break event {aed.Name}' )
        if 'IsCritical' in event and event['IsCritical']:
            aed.IsCritical = True
            logger.debug( f'json2plus: detected critical event {aed.Name}' )
        if previous_fragment:
            relate(fragment, previous_fragment, 57, 'follows')
        previous_fragment = fragment

    # Loop through and link events and constraints in a second pass.
    for event in j['Events']:
        aed = one(job_defn).SeqDefn[1].AuditEventDefn[2](lambda sel: sel.Name == event['EventName'] and sel.OccurrenceId == event['OccurrenceId'])
        if 'PreviousEvents' in event:
            for previous_event in event['PreviousEvents']:
                prev_aed = one(job_defn).SeqDefn[1].AuditEventDefn[2](lambda sel: sel.Name == previous_event['PreviousEventName'] and sel.OccurrenceId == previous_event['PreviousOccurrenceId'])
                evt_succ = populator.m.new('EvtSucc')
                relate(prev_aed, evt_succ, 3, 'precedes')
                relate(evt_succ, aed, 3, 'precedes')
                if 'ConstraintDefinitionId' in previous_event:
                    # Create the constraint if one does not exist.  Link it to the succession.
                    const_defn = populator.m.select_any('ConstDefn', lambda sel: sel.Id == previous_event['ConstraintDefinitionId'])
                    if not const_defn:
                        const_defn = populator.m.new('ConstDefn', Id=previous_event['ConstraintDefinitionId'])
                    if 'AND' == previous_event['ConstraintValue']:
                        const_defn.Type = ConstraintType.AND
                    elif 'XOR' == previous_event['ConstraintValue']:
                        const_defn.Type = ConstraintType.XOR
                    else:
                        const_defn.Type = ConstraintType.IOR
                    relate(evt_succ, const_defn, 16)

    # Create the unhappy audit events.
    if 'UnhappyEvents' in j:
        previous_fragment = None
        for unhappy_event in j['UnhappyEvents']:
            # Create unhappy event definition.
            fragment = populator.m.new('Fragment')
            ued = populator.m.new('UnhappyEventDefn',
                                  Name=unhappy_event['EventName'],
                                  Application=unhappy_event['Application'])
            relate(fragment, ued, 56)
            # Create and relate the package if not already in place.
            pkg_defn = one(job_defn).PkgDefn[20](lambda sel: sel.Name == unhappy_event['PackageName'])
            if not pkg_defn:
                pkg_defn = populator.m.new('PkgDefn', Name=unhappy_event['PackageName'])
                logger.debug( f'json2plus: creating package {pkg_defn.Name}' )
                relate(pkg_defn, job_defn, 20)
            relate(pkg_defn, ued, 21)

