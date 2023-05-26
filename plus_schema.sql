CREATE TABLE AuditEventDefn (
    Name STRING,
    OccurrenceId INTEGER,
    IsBreak BOOLEAN,
    SequenceName STRING,
    JobName STRING
);
CREATE UNIQUE INDEX I1 ON AuditEventDefn (Name, OccurrenceId);
CREATE TABLE ConstDefn (
    Id STRING,
    Type INTEGER
);
CREATE TABLE EvtDataDefn (
    Name STRING,
    Type INTEGER,
    SourceJobName STRING
);
CREATE UNIQUE INDEX I1 ON EvtDataDefn (Name, SourceJobName);
CREATE TABLE EvtSucc (
    
);
CREATE TABLE JobDefn (
    Name STRING
);
CREATE UNIQUE INDEX I1 ON JobDefn (Name);
CREATE TABLE SeqDefn (
    Name STRING,
    JobName STRING
);
CREATE UNIQUE INDEX I1 ON SeqDefn (Name, JobName);
CREATE TABLE UnrsvdAEDefn (
    Name STRING,
    OccurenceId INTEGER
);
CREATE ROP REF_ID R1 FROM M SeqDefn (JobName) TO 1 JobDefn (Name);
CREATE ROP REF_ID R11 FROM 1C AuditEventDefn () TO MC EvtDataDefn ();
CREATE ROP REF_ID R12 FROM MC AuditEventDefn () TO MC EvtDataDefn ();
CREATE ROP REF_ID R13 FROM M AuditEventDefn (SequenceName, JobName) TO 1C SeqDefn (Name, JobName);
CREATE ROP REF_ID R14 FROM MC EvtDataDefn (SourceJobName) TO 1 JobDefn (Name);
CREATE ROP REF_ID R15 FROM M AuditEventDefn (SequenceName, JobName) TO 1C SeqDefn (Name, JobName);
CREATE ROP REF_ID R16 FROM 1C ConstDefn () TO 1 EvtSucc ();
CREATE ROP REF_ID R2 FROM M AuditEventDefn (SequenceName, JobName) TO 1 SeqDefn (Name, JobName);
CREATE ROP REF_ID R3 FROM MC EvtSucc () PHRASE 'follows' TO 1 AuditEventDefn () PHRASE 'precedes';
CREATE ROP REF_ID R3 FROM MC EvtSucc () PHRASE 'precedes' TO 1 AuditEventDefn () PHRASE 'follows';
CREATE ROP REF_ID R50 FROM MC EvtDataDefn () TO MC UnrsvdAEDefn ();
