CREATE TABLE AuditEvent (
    Id UNIQUE_ID,
    TimeStamp REAL
);
CREATE UNIQUE INDEX I1 ON AuditEvent (Id);
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
CREATE TABLE EventData (
    EvtId UNIQUE_ID,
    Name STRING,
    Value STRING,
    IsSource BOOLEAN,
    Creation REAL,
    Expiration REAL,
    JobDefnName STRING
);
CREATE UNIQUE INDEX I1 ON EventData (EvtId, Name);
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
CREATE TABLE Job (
    Id UNIQUE_ID
);
CREATE UNIQUE INDEX I1 ON Job (Id);
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
CREATE ROP REF_ID R1 FROM M SeqDefn (JobDefnName) TO 1 JobDefn (Name);
CREATE ROP REF_ID R101 FROM 1 JobDefn () TO MC Job ();
CREATE ROP REF_ID R102 FROM M AuditEvent () TO 1 Job ();
CREATE ROP REF_ID R103 FROM 1 AuditEventDefn () TO MC AuditEvent ();
CREATE ROP REF_ID R104 FROM 1C AuditEvent () PHRASE 'follows' TO 1C AuditEvent () PHRASE 'precedes';
CREATE ROP REF_ID R105 FROM 1 AuditEvent () TO 1C Job ();
CREATE ROP REF_ID R106 FROM MC AuditEvent () PHRASE 'must_follow' TO MC AuditEvent () PHRASE 'must_precede';
CREATE ROP REF_ID R107 FROM MC EventData (EvtId) TO 1 AuditEvent (Id);
CREATE ROP REF_ID R108 FROM MC EventData (JobDefnName, Name) TO 1 EvtDataDefn (JobDefnName, Name);
CREATE ROP REF_ID R11 FROM 1C AuditEventDefn () TO MC EvtDataDefn ();
CREATE ROP REF_ID R12 FROM MC AuditEventDefn () TO MC EvtDataDefn ();
CREATE ROP REF_ID R13 FROM M AuditEventDefn (JobDefnName, SequenceName) TO 1C SeqDefn (JobDefnName, Name);
CREATE ROP REF_ID R14 FROM MC EvtDataDefn (JobDefnName) TO 1C JobDefn (Name);
CREATE ROP REF_ID R15 FROM M AuditEventDefn (JobDefnName, SequenceName) TO 1C SeqDefn (JobDefnName, Name);
CREATE ROP REF_ID R16 FROM 1C ConstDefn () TO 1 EvtSucc ();
CREATE ROP REF_ID R17 FROM MC EvtDataDefn (JobDefnName) TO 1C JobDefn (Name);
CREATE ROP REF_ID R18 FROM MC EvtDataDefn () PHRASE 'corresponds_to' TO 1C EvtDataDefn () PHRASE 'referenced_by';
CREATE ROP REF_ID R2 FROM M AuditEventDefn (JobDefnName, SequenceName) TO 1 SeqDefn (JobDefnName, Name);
CREATE ROP REF_ID R3 FROM MC EvtSucc () PHRASE 'follows' TO 1 AuditEventDefn () PHRASE 'precedes';
CREATE ROP REF_ID R3 FROM MC EvtSucc () PHRASE 'precedes' TO 1 AuditEventDefn () PHRASE 'follows';
CREATE ROP REF_ID R51 FROM 1 Fragment () TO 1C Tine ();
CREATE ROP REF_ID R52 FROM 1 Fragment () TO 1C Tine ();
CREATE ROP REF_ID R54 FROM 1C Fork () TO M Tine ();
CREATE ROP REF_ID R55 FROM 1C Loop () TO 1 Tine ();
CREATE ROP REF_ID R56 FROM 1C AuditEventDefn () TO 1 Fragment ();
CREATE ROP REF_ID R56 FROM 1C Fork () TO 1 Fragment ();
CREATE ROP REF_ID R56 FROM 1C Loop () TO 1 Fragment ();
CREATE ROP REF_ID R57 FROM 1C Fragment () PHRASE 'follows' TO 1C Fragment () PHRASE 'precedes';
CREATE ROP REF_ID R58 FROM 1C SeqDefn () TO 1 Fragment ();
CREATE ROP REF_ID R59 FROM M Fragment () TO 1C Tine ();
