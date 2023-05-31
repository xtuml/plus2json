grammar plus2json;

plusdefn       : NEWLINE* umlblock+
               ;

umlblock       : STARTUML ( '(' 'id' '=' identifier ')' )? NEWLINE
                 ( job_defn      // primary use case defining full job
//               | sequence_defn // sequence to be referenced from elsewhere
//               | statement+    // simple grouping of statements to be !included
                 )
                 ENDUML NEWLINE?
               ;

job_defn       : PARTITION job_name '{' NEWLINE
                 extern*
                 sequence_defn+
                 '}' NEWLINE
                 ( PACKAGE package_name '{' NEWLINE unhappy_event* '}' NEWLINE )*
               ;

job_name       : identifier
               ;

extern         : ':' EINV ',' SRC ',' JOBDEFN '=' jobdefn=identifier ',' NEWLINE? NAME '=' invname=identifier '|' NEWLINE? detach NEWLINE
               ;

sequence_defn  : GROUP sequence_name NEWLINE statement+ ( HIDE NEWLINE )? ENDGROUP NEWLINE
               ;

sequence_name  : identifier
               ;

statement      : ( event_defn
                 | if
                 | switch
                 | fork
                 | split
                 | loop
                 | // empty line
                 ) NEWLINE
               ;

event_defn     : ( HIDE NEWLINE )?
                 ':' event_name
                 event_tag*
                 ( ';' | '<' | '>' | ']' )
                 ( NEWLINE ( break | detach ) )?
               ;

event_tag      : branch_count
                 | merge_count
                 | loop_count
                 | invariant
                 | critical
	       ;

event_name     : identifier ( '(' number ')' )?
               ;

event_ref      : event_name
               ;

branch_count   : ',' BCNT
                 ( ',' SRC ( '=' sevt=event_ref )? )?
                 ( ',' USER ( '=' uevt=event_ref )? )?
                 ',' NAME '=' bcname=identifier
               ;

merge_count    : ',' MCNT
                 ( ',' SRC ( '=' sevt=event_ref )? )?
                 ( ',' USER ( '=' uevt=event_ref )? )?
                 ',' NAME '=' mcname=identifier
               ;

loop_count     : ',' LCNT
                 ( ',' SRC ( '=' sevt=event_ref )? )?
                 ( ',' USER ( '=' uevt=event_ref )? )?
                 ',' NAME '=' lcname=identifier
               ;

invariant      : ',' ( IINV | EINV )
                 ( ',' SRC ( '=' sevt=event_ref )? )?
                 ( ',' USER ( '=' uevt=event_ref )? )?
                 ',' NAME '=' invname=identifier
               ;

critical       : ',' CRITICAL
               ;

break          : BREAK
               ;

detach         : DETACH
               ;

if             : IF '(' condition ')' THEN ( '(' identifier ')' )? NEWLINE
                 statement+
                 elseif*
                 else?
                 ENDIF
               ;

elseif         : ELSEIF ( '(' identifier ')' )? NEWLINE
                 statement+
               ;

else           : ELSE ( '(' identifier ')' )? NEWLINE
                 statement+
               ;

condition      : identifier
               ;

switch         : SWITCH '(' condition ')' NEWLINE
                 case+
                 ENDSWITCH
               ;

case           : CASE '(' condition ')' NEWLINE
                 statement+
               ;

loop           : REPEAT NEWLINE
                 statement+
                 REPEAT WHILE
                 ( '(' identifier ')' )?
               ;

fork           : FORK NEWLINE
                 statement+
                 fork_again+
                 ENDFORK
               ;

fork_again     : FORKAGAIN NEWLINE statement+
               ;

split          : SPLIT NEWLINE
                 statement+
                 split_again+
                 ENDSPLIT
               ;

split_again    : SPLITAGAIN NEWLINE statement+
               ;

package_name   : identifier
               ;

unhappy_event  : PACKAGE package_name '{' NEWLINE unhappy_event* '}' NEWLINE
               | ':' unhappy_name
                 ( ';' | '<' | '>' | ']' )
                 NEWLINE KILL NEWLINE
               ;

unhappy_name   : identifier
               ;

identifier     : IDENT
               | StringLiteral // allowing blanks delimited with double-quotes
               ;

number         : NUMBER
               ;

StringLiteral  : '"' ( ~('\\'|'"') )* '"'
               ;


// keywords
BCNT           : 'bcnt' | 'BCNT'; // branch count
BREAK          : 'break';
CASE           : 'case';
CRITICAL       : 'critical' | 'CRITICAL';
DETACH         : 'detach';
EINV           : 'einv' | 'EINV'; // extra-job invariant
ELSE           : 'else';
ELSEIF         : 'elseif';
ENDFORK        : 'end fork';
ENDGROUP       : 'end group';
ENDIF          : 'endif' | 'end if';
ENDSPLIT       : 'end split';
ENDSWITCH      : 'endswitch';
ENDUML         : '@enduml';
FORKAGAIN      : 'fork again';
FORK           : 'fork';
GROUP          : 'group';         // sequence
HIDE           : '-[hidden]->';
IF             : 'if';
IINV           : 'iinv' | 'IINV'; // intra-job invariant
JOBDEFN        : 'jobdefn' | 'JOBDEFN' ;
KILL           : 'kill';
LCNT           : 'lcnt' | 'LCNT'; // loop count
MCNT           : 'mcnt' | 'MCNT'; // merge count
NAME           : 'name' | 'NAME'; // marking target event
PACKAGE        : 'package';       // grouping of unsequenced events
PARTITION      : 'partition';     // job
REPEAT         : 'repeat';
SPLITAGAIN     : 'split again';
SPLIT          : 'split';
SRC            : 'src' | 'SRC';
STARTUML       : '@startuml';
SWITCH         : 'switch';
THEN           : 'then';
USER           : 'user' | 'USER';
WHILE          : 'while';

NEWLINE        : [\r\n]+;

NOTE           : ( 'floating' )? ' '+ 'note' .*? 'end note' NEWLINE -> channel(HIDDEN);
COLOR          : '#' LABEL -> channel(HIDDEN);
NUMBER         : DIGIT+;
IDENT          : NONDIGIT ( NONDIGIT | DIGIT )*;
LABEL          : ( NONDIGIT | DIGIT )+;
COMMENT        : ( '\'' .*? NEWLINE | '/\'' .*? '\'/' NEWLINE ) -> channel(HIDDEN);
WS             : [ \t]+ -> skip ; // toss out whitespace

//=========================================================
// Fragments
//=========================================================
fragment NONDIGIT : [-_a-zA-Z*];
fragment DIGIT :  [0-9];
fragment UNSIGNED_INTEGER : DIGIT+;


