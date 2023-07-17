import doctest
import logging
import sys

from plus2json import plus2json


def test_pretty_print(input):
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(levelname)s: %(message)s')
    plus2json.job(pretty_print=True, input=input, outdir=None, event_data=[])


def t01_straight():
    '''
    >>> t01_straight()  # doctest: +NORMALIZE_WHITESPACE
    INFO: job defn: t01_straight
    INFO: sequence: sequence01
    INFO: A(0) start
    INFO: B(0)                     A(0)
    INFO: C(0)                     B(0)
    INFO: D(0)                     C(0)
    INFO: E(0)       end           D(0)
    '''

    input = '''
    @startuml
    partition "t01_straight" {
      group "sequence01"
        :A;
        :B;
        :C;
        :D;
        :E;
      end group
    }
    @enduml
    '''

    test_pretty_print(input)


def t02_fork():
    '''
    >>> t02_fork()  # doctest: +NORMALIZE_WHITESPACE
    INFO: job defn: t02_fork
    INFO: sequence: sequence02
    INFO: A(0) start
    INFO: B(0)                     A(0) c26d AND
    INFO: C(0)                     B(0)
    INFO: D(0)                     A(0) c26d AND
    INFO: E(0)                     D(0)
    INFO: F(0)       end           C(0),E(0)
    '''

    input = '''
    @startuml
    partition "t02_fork" {
      group "sequence02"
        :A;
        fork
          :B;
          :C;
        fork again
          :D;
          :E;
        end fork
        :F;
      end group
    }
    @enduml
    '''

    test_pretty_print(input)


def t03_split():
    '''
    >>> t03_split()  # doctest: +NORMALIZE_WHITESPACE
    INFO: job defn: t03_split
    INFO: sequence: sequence03
    INFO: A(0) start
    INFO: B(0)                     A(0)
    INFO: C(0)                     B(0)
    INFO: D(0)                     A(0)
    INFO: E(0)                     D(0)
    INFO: F(0)       end           C(0),E(0)
    '''

    input = '''
    @startuml
    partition "t03_split" {
      group "sequence03"
        :A;
        split
          :B;
          :C;
        split again
          :D;
          :E;
        end split
        :F;
      end group
    }
    @enduml
    '''

    test_pretty_print(input)


def t04_if():
    '''
    >>> t04_if()  # doctest: +NORMALIZE_WHITESPACE
    INFO: job defn: t04_if
    INFO: sequence: sequence04
    INFO: A(0) start
    INFO: B(0)                     A(0) 8b3f XOR
    INFO: C(0)                     B(0)
    INFO: D(0)                     A(0) 8b3f XOR
    INFO: E(0)                     D(0)
    INFO: F(0)       end           C(0),E(0)
    '''

    input = '''
    @startuml
    partition "t04_if" {
      group "sequence04"
        :A;
        if ( condition ) then ( normal )
          :B;
          :C;
        else
          :D;
          :E;
        endif
        :F;
      end group
    }
    @enduml
    '''

    test_pretty_print(input)


def t05_switch():
    '''
    >>> t05_switch()  # doctest: +NORMALIZE_WHITESPACE
    INFO: job defn: t05_switch
    INFO: sequence: sequence05
    INFO: A(0) start
    INFO: B(0)                     A(0) 3ede XOR
    INFO: C(0)                     B(0)
    INFO: D(0)                     A(0) 3ede XOR
    INFO: E(0)                     D(0)
    INFO: F(0)                     A(0) 3ede XOR
    INFO: G(0)                     F(0)
    INFO: H(0)       end           C(0),E(0),G(0)
    '''

    input = '''
    @startuml
    partition "t05_switch" {
      group "sequence05"
        :A;
        switch ( test )
        case ( one )
          :B;
          :C;
        case ( two )
          :D;
          :E;
        case ( three )
          :F;
          :G;
        endswitch
        :H;
      end group
    }
    @enduml
    '''

    test_pretty_print(input)


def t06_mixed():
    '''
    >>> t06_mixed()  # doctest: +NORMALIZE_WHITESPACE
    INFO: job defn: t06_mixed
    INFO: sequence: sequence06
    INFO: A(0) start
    INFO: A1(0)                    A(0) 7096 XOR
    INFO: B(0)                     A1(0) 3abe AND
    INFO: C(0)                     A1(0) 3abe AND
    INFO: D(0)                     B(0),C(0)
    INFO: E(0)                     A(0) 7096 XOR
    INFO: F(0)       end           D(0),E(0)
    '''

    input = '''
    @startuml
    partition "t06_mixed" {
      group "sequence06"
        :A;
        if ( XOR ) then ( normal )
          :A1;
          fork
            :B;
          fork again
            :C;
          end fork
          :D;
        else
          :E;
        endif
        :F;
      end group
    }
    @enduml
    '''

    test_pretty_print(input)


def t07_mixed2():
    '''
    >>> t07_mixed2()  # doctest: +NORMALIZE_WHITESPACE
    INFO: job defn: t07_mixed2
    INFO: sequence: sequence07
    INFO: A(0) start
    INFO: A1(0)                    A(0) 1ac6 AND
    INFO: B(0)                     A1(0) fab2 XOR
    INFO: C(0)                     A1(0) fab2 XOR
    INFO: D(0)                     A(0) 1ac6 AND
    INFO: E(0)       end           B(0),C(0),D(0)
    '''

    input = '''
    @startuml
    partition "t07_mixed2" {
      group "sequence07"
        :A;
        fork
          :A1;
          switch ( XOR )
          case ( one )
            :B;
          case ( other )
            :C;
          endswitch
        fork again
          :D;
        end fork
        :E;
      end group
    }
    @enduml
    '''

    test_pretty_print(input)


def t08_unhappy1():
    '''
    >>> t08_unhappy1()  # doctest: +NORMALIZE_WHITESPACE
    INFO: job defn: t08_unhappy1
    INFO: sequence: sequence08
    INFO: A(0) start
    INFO: B(0)                              A(0)
    INFO: C(0)       end       critical     B(0)
    INFO: package: unhappy events
    INFO: unhappy event: U
    INFO: unhappy event: V
    '''

    input = '''
    @startuml
    partition "t08_unhappy1" {
      group "sequence08"
        :A;
        :B;
        :C,CRITICAL;
        detach
      end group
      package "unhappy events" {
        :U;
        kill
        :V;
        kill
      }
    }
    @enduml
    '''

    test_pretty_print(input)


def t09_unhappy2():
    '''
    >>> t09_unhappy2()  # doctest: +NORMALIZE_WHITESPACE
    INFO: job defn: t09_unhappy2
    INFO: sequence: sequence09
    INFO: A(0) start
    INFO: B(0)                              A(0)
    INFO: C(0)       end       critical     B(0)
    INFO: package: unhappy events
    INFO: unhappy event: U
    INFO: unhappy event: V
    INFO: package: nested unhappies
    INFO: unhappy event: W
    INFO: package: unhappy more
    INFO: unhappy event: X
    '''

    input = '''
    @startuml
    partition "t09_unhappy2" {
      group "sequence09"
        :A;
        :B;
        :C,CRITICAL;
        detach
      end group
      package "unhappy events" {
        :U;
        kill
        :V;
        kill
        package "nested unhappies" {
          :W;
          kill
        }
      }
      package "unhappy more" {
        :X;
        kill
      }
    }
    @enduml
    '''

    test_pretty_print(input)


if __name__ == '__main__':
    doctest.testmod()
