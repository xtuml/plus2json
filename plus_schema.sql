CREATE TABLE AuditEventDefn (
    Name STRING,
    OccurrenceId INTEGER,
    JobDefnName STRING,
    SequenceName STRING,
    IsBreak BOOLEAN
);
CREATE UNIQUE INDEX I1 ON AuditEventDefn (Name, OccurrenceId, JobDefnName);
CREATE TABLE ConstDefn (
    Id STRING,
    Type INTEGER
);
CREATE TABLE EvtDataDefn (
    Name STRING,
    Type INTEGER,
    JobDefnName STRING,
    SourceJobDefnName STRING
);
CREATE UNIQUE INDEX I1 ON EvtDataDefn (Name, JobDefnName);
CREATE TABLE EvtSucc (
    
);
CREATE TABLE Fork (
    Type INTEGER
);
CREATE TABLE Fragment (
    
);
CREATE TABLE JobDefn (
    Name STRING
);
CREATE UNIQUE INDEX I1 ON JobDefn (Name);
CREATE TABLE Loop (
    
);
CREATE TABLE SeqDefn (
    Name STRING,
    JobDefnName STRING
);
CREATE UNIQUE INDEX I1 ON SeqDefn (Name, JobDefnName);
CREATE TABLE Tine (
    IsTerminal BOOLEAN
);
CREATE TABLE UnrsvdAEDefn (
    Name STRING,
    OccurenceId INTEGER
);
CREATE ROP REF_ID R1 FROM M SeqDefn (JobDefnName) TO 1 JobDefn (Name);
CREATE ROP REF_ID R11 FROM 1C AuditEventDefn () TO MC EvtDataDefn ();
CREATE ROP REF_ID R12 FROM MC AuditEventDefn () TO MC EvtDataDefn ();
CREATE ROP REF_ID R13 FROM M AuditEventDefn (JobDefnName, SequenceName) TO 1C SeqDefn (JobDefnName, Name);
CREATE ROP REF_ID R14 FROM MC EvtDataDefn (JobDefnName) TO 1C JobDefn (Name);
CREATE ROP REF_ID R15 FROM M AuditEventDefn (JobDefnName, SequenceName) TO 1C SeqDefn (JobDefnName, Name);
CREATE ROP REF_ID R16 FROM 1C ConstDefn () TO 1 EvtSucc ();
CREATE ROP REF_ID R17 FROM MC EvtDataDefn (JobDefnName) TO 1C JobDefn (Name);
CREATE ROP REF_ID R2 FROM M AuditEventDefn (JobDefnName, SequenceName) TO 1 SeqDefn (JobDefnName, Name);
CREATE ROP REF_ID R3 FROM MC EvtSucc () PHRASE 'follows' TO 1 AuditEventDefn () PHRASE 'precedes';
CREATE ROP REF_ID R3 FROM MC EvtSucc () PHRASE 'precedes' TO 1 AuditEventDefn () PHRASE 'follows';
CREATE ROP REF_ID R50 FROM MC EvtDataDefn () TO MC UnrsvdAEDefn ();
CREATE ROP REF_ID R51 FROM 1 Fragment () TO 1C Tine ();
CREATE ROP REF_ID R52 FROM 1 Fragment () TO 1C Tine ();
CREATE ROP REF_ID R54 FROM 1C Fork () TO M Tine ();
CREATE ROP REF_ID R55 FROM 1C Loop () TO 1 Tine ();
CREATE ROP REF_ID R56 FROM 1C AuditEventDefn () TO 1 Fragment ();
CREATE ROP REF_ID R56 FROM 1C Fork () TO 1 Fragment ();
CREATE ROP REF_ID R56 FROM 1C Loop () TO 1 Fragment ();
CREATE ROP REF_ID R57 FROM 1C Fragment () PHRASE 'follows' TO 1C Fragment () PHRASE 'precedes';
