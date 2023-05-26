"""

Pretty print the PLUS job definition.

"""

import sys
import xtuml

# These mixin classes supply methods for pretty-printing the
# job definition in a way that makes it understandable.  It is
# meant to help a user confirm that the job definition is set
# up correctly.


def JobDefn_pretty_print(self):
    print("job defn:", self.JobDefinitionName)
    for seq in xtuml.navigate_many(self).SequenceDefn[1]():
        SequenceDefn_pretty_print(seq)


def SequenceDefn_pretty_print(self):
    print("sequence:", self.SequenceName)
    for ae in xtuml.navigate_many(self).AuditEventDefn[2]():
        AuditEventDefn_pretty_print(ae)


def AuditEventDefn_pretty_print(self):
    ss = 'start' if self.SequenceStart else ''
    se = 'end' if self.SequenceEnd else ''
    b = 'break' if self.isBreak else '     '
    # look for linked DynamicControls
    bcnt = ''
    lcnt = ''
    mcnt = ''
    for dc in xtuml.navigate_many(self).DynamicControl[9]():
        su = f's={dc.src_evt_txt}({dc.src_occ_txt})'
        su += f'u={dc.user_evt_txt}({dc.user_occ_txt})'
        if dc.DynamicControlType == 'BRANCHCOUNT':
            bcnt += f'bc:{dc.DynamicControlName}-{su}'
        elif dc.DynamicControlType == 'MERGECOUNT':
            mcnt += f'mc:{dc.DynamicControlName}-{su}'
        elif dc.DynamicControlType == 'LOOPCOUNT':
            lcnt += f'lc:{dc.DynamicControlName}-{su}'
        else:
            print("ERROR:  malformed dynamic control")
            sys.exit()
    # look for linked Invariant
    einv = ''
    iinv = ''
    # select many invs related by self->Invariant[R11]
    for inv in xtuml.navigate_many(self).Invariant[11]():
        if inv.Type == 'EINV':
            einv += f' s-einv:{inv.Name}'
        elif inv.Type == 'IINV':
            iinv += f' s-iinv:{inv.Name}'
        else:
            print("ERROR:  malformed invariant type")
            sys.exit()
    # select many invs related by self->Invariant[R12]
    for inv in xtuml.navigate_many(self).Invariant[12]():
        if inv.Type == 'EINV':
            einv += f' u-einv:{inv.Name}'
        elif inv.Type == 'IINV':
            iinv += f' u-iinv:{inv.Name}'
        else:
            print("ERROR:  malformed invariant type")
            sys.exit()
    prev_aes = '    ' + ','.join(map(lambda prev_ae: f'{xtuml.navigate_one(prev_ae).AuditEventDefn[3]().EventName}({xtuml.navigate_one(prev_ae).AuditEventDefn[3]().OccurrenceId}){prev_ae.ConstraintDefinitionId}{prev_ae.ConstraintValue}',
                                     xtuml.navigate_many(self).PreviousAuditEventDefn[3]()))
    print(f'{self.EventName+"("+self.OccurrenceId+")":{10}}',
          f'{ss:{5}}', f'{se:{3}}', b, prev_aes, bcnt, mcnt, lcnt, einv, iinv)
