CREATE TABLE AuditEventDefn (
    EventName STRING,
    OccurrenceId STRING,
    c_longest_event_name INTEGER,
    c_idFactory INTEGER,
    SequenceStart BOOLEAN,
    SequenceEnd BOOLEAN,
    isBreak BOOLEAN,
    visit_count INTEGER,
    eventId STRING,
    previousEventIds INTEGER
);
CREATE UNIQUE INDEX I1 ON AuditEventDefn (EventName, OccurrenceId);
CREATE TABLE DynamicControl (
    DynamicControlName STRING,
    DynamicControlType STRING,
    src_evt_txt STRING,
    src_occ_txt STRING,
    user_evt_txt STRING,
    user_occ_txt STRING
);
CREATE UNIQUE INDEX I1 ON DynamicControl (DynamicControlName);
CREATE TABLE Fork (
    id STRING,
    flavor STRING,
    c_scope INTEGER,
    c_number INTEGER
);
CREATE UNIQUE INDEX I1 ON Fork (id);
CREATE TABLE Invariant (
    Name STRING,
    Type STRING,
    SourceJobDefinitionName STRING,
    value STRING,
    src_evt_txt STRING,
    src_occ_txt STRING,
    user_tuples STRING,
    is_extern BOOLEAN,
    c_idFactory INTEGER,
    c_invariant_store_filename STRING
);
CREATE UNIQUE INDEX I1 ON Invariant (Name, SourceJobDefinitionName);
CREATE UNIQUE INDEX I2 ON Invariant (value);
CREATE TABLE JobDefn (
    JobDefinitionName STRING,
    c_idFactory INTEGER,
    jobId STRING
);
CREATE UNIQUE INDEX I1 ON JobDefn (JobDefinitionName);
CREATE TABLE Loop (
    c_scope INTEGER
);
CREATE TABLE PreviousAuditEventDefn (
    ConstraintDefinitionId STRING,
    ConstraintValue STRING
);
CREATE TABLE SequenceDefn (
    SequenceName STRING
);
CREATE UNIQUE INDEX I1 ON SequenceDefn (SequenceName);
CREATE ROP REF_ID R1 FROM 1 JobDefn () TO M SequenceDefn ();
CREATE ROP REF_ID R10 FROM 1 AuditEventDefn () TO MC DynamicControl ();
CREATE ROP REF_ID R11 FROM 1C AuditEventDefn () TO MC Invariant ();
CREATE ROP REF_ID R12 FROM MC AuditEventDefn () TO MC Invariant ();
CREATE ROP REF_ID R13 FROM M AuditEventDefn () TO 1C SequenceDefn ();
CREATE ROP REF_ID R2 FROM M AuditEventDefn () TO 1 SequenceDefn ();
CREATE ROP REF_ID R3 FROM 1 AuditEventDefn () TO MC PreviousAuditEventDefn ();
CREATE ROP REF_ID R4 FROM 1C Fork () TO 1C PreviousAuditEventDefn ();
CREATE ROP REF_ID R5 FROM 1C Fork () TO 1C PreviousAuditEventDefn ();
CREATE ROP REF_ID R6 FROM 1C Fork () TO MC PreviousAuditEventDefn ();
CREATE ROP REF_ID R7 FROM 1C Fork () TO MC PreviousAuditEventDefn ();
CREATE ROP REF_ID R8 FROM 1C Loop () TO 1C PreviousAuditEventDefn ();
CREATE ROP REF_ID R9 FROM 1 AuditEventDefn () TO MC DynamicControl ();
