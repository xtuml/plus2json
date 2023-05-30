"""

Pretty print the PLUS job definition.

"""

import xtuml

# These mixin classes supply methods for pretty-printing the
# job definition in a way that makes it understandable.  It is
# meant to help a user confirm that the job definition is set
# up correctly.


def JobDefn_pretty_print(self):
    print("job defn:", self.Name)
    for seq in xtuml.navigate_many(self).SeqDefn[1]():
        SeqDefn_pretty_print(seq)


def SeqDefn_pretty_print(self):
    print("sequence:", self.Name)
    for ae in xtuml.navigate_many(self).AuditEventDefn[2]():
        AuditEventDefn_pretty_print(ae)


def AuditEventDefn_pretty_print(self):
    ss = 'start' if xtuml.navigate_one(self).SeqDefn[13]() else ''
    se = 'end' if xtuml.navigate_one(self).SeqDefn[15]() else ''
    b = 'break' if self.IsBreak else '     '
    prev_aes = '    ' + ','.join(map(lambda prev_ae: f'{xtuml.navigate_one(prev_ae).AuditEventDefn[3, "follows"]().Name}({xtuml.navigate_one(prev_ae).AuditEventDefn[3, "follows"]().OccurrenceId})',
                                     xtuml.navigate_many(self).EvtSucc[3, 'follows']()))
    print(f'{self.Name+"("+str(self.OccurrenceId)+")":{10}}',
          f'{ss:{5}}', f'{se:{3}}', b, prev_aes)
