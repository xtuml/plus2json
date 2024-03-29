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


def JobDefn_plus(self):
    ''' render PLUS job definition '''
    m = self.__metaclass__.metamodel
    opts = m.select_any('_Options')

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

    p = ""
    p += f'  group "{self.Name}"\n'
    # Render fragments (fork, loop or event) for possibly multiple start events.
    sequence_starts = many(self).AuditEventDefn[13]()
    for first_audit_event_defn in sequence_starts:
        s, next_aed = Fragment_plus(first_audit_event_defn)
        p += s
        while next_aed:
            s, next_aed = Fragment_plus(next_aed)
            p += s
    p += "  end group\n"
    return p


def PkgDefn_plus(self):
    ''' render PLUS mapping for package of unhappy events '''

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
    next_aed = []
    # Detect fork, loop, audit event definition.
    # Fork is detected by having multiple successions with the same constraint.
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
                        # TODO mismatched constraints, maybe nested forks?
                        fork_detected = False
                        break
                else:
                    constraint_type = const_defn.Type
            else:
                # probably a loop
                fork_detected = False
                break
        if fork_detected:
            s, next_aed = Fork_plus(audit_event_defn, const_defn)
            p += s
    else:
        #prev_next_aeds = many(audit_event_defn).AuditEventDefn[3,'follows']()
        #if len(prev_next_aeds) > 1:
        #    return p
        s, next_aeds = AuditEventDefn_plus(audit_event_defn)
        p += s
        for next_aed in next_aeds:
            s = '' # NOP
    return p, next_aed


def Fork_plus(audit_event_defn, const_defn):
    ''' render PLUS for fork and switch '''

    # Render the top aed.
    # Render the tines.
    # Return the merge point as next (if fork merges).
    p = ""
    next_aed = []
    # Render the top of the fork (the node that has multiple edges).
    s, next_aeds = AuditEventDefn_plus(audit_event_defn)
    p += s
    # Render the PLUS instruction for the type of fork.
    if const_defn.Type == ConstraintType.AND:
        p += '    fork\n'
    elif const_defn.Type == ConstraintType.XOR:
        p += f'    switch ( "{const_defn.Id}" )\n'
        p += f'    case ( "1" )\n'
    else:
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
    return p, next_aed


def Loop_plus(audit_event_defn):
    ''' render PLUS for loops '''

    p = ""
    return p


def Tine_plus(audit_event_defn):
    ''' render PLUS for a tine (sequence of fragments) '''

    p = ""
    s, next_aed = Fragment_plus(audit_event_defn)
    p += s
    # Detect end of tine here.
    # The end of a tine is either:
    #   a dead end (no next_aed)
    #   just ahead of a merge point (multiple prev_aeds)
    prev_next_aeds = many(next_aed).AuditEventDefn[3,'follows']()
    while len(prev_next_aeds) == 1:
        s, next_aed = Fragment_plus(next_aed)
        p += s
        prev_next_aeds = many(next_aed).AuditEventDefn[3,'follows']()
    return p, next_aed


def AuditEventDefn_plus(self):
    ''' render PLUS for audit event definition '''

    p = ""
    p += f'    :{self.Name};\n'
    next_aeds = many(self).AuditEventDefn[3,'precedes']()
    if not next_aeds:
        p += "    detach\n"
    return p, next_aeds


def UnhappyEventDefn_plus(self):
    ''' render PLUS for unhappy event definition '''

    p = ""
    p += f'    :{self.Name};\n'
    p += f'    kill\n'
    return p

