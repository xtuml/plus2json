"""

Supply Audit Event Simulator (AESim) Test Scenario.

"""

import plus_job_defn

# Here, methods are defined to ease the configuration of the AESimulator
# test scenario dispatch sequencing.

class JobDefn_AEStest:
    """AEStest methods for JobDefn"""
    @classmethod
    def aesim_test_all(cls):
        """output AEStest JSON"""
        j = """
        { "OneFilePerJob" : "true",
          "MaxEventsPerFile" : 20,
          "FileTimoutPeriod" : "PT10S",
          "JobSpecificationLocation" : "config/scenario1",
          "TestFileLocation" : "test-files/generated",
          "TestFileDestination" : "test-files/incoming",
          "Tests" : [{
              "TestId" : 1,
              "TestName" : "Scenario1",
              "TotalTests" : 1,
              "TestFrequency" : "PT1S",
              "TestJobSpec" : [{
        """
        for job_defn in plus_job_defn.JobDefn.instances:
            j += job_defn.aesim_test()
        j += '}]'
        j += '}]'
        j += '}'
        return j
    def aesim_test(self):
        """output AEStest JSON"""
        j = '"TestJobSpecName" : "' + self.JobDefinitionName + '",'
        j += '"EventDispatchOrder" : "'
        seqdelim = ""
        for seq in self.sequences:
            j += seq.aesim_test( seqdelim )
            seqdelim = ',' 
        j += '"'
        return j

class SequenceDefn_AEStest:
    """AEStest methods for Sequence Definition"""
    def aesim_test( self, seqdelim ):
        """output Sequence AEStest JSON"""
        j = ""
        aedelim = seqdelim
        for ae in self.audit_events:
            j += ae.aesim_test( aedelim )
            aedelim = ','
        return j

class AuditEvent_AEStest:
    """AEStest methods Audit Event Definition"""
    def aesim_test(self, delim):
        """output AuditEvent AEStest JSON"""
        j = delim + str( plus_job_defn.AuditEvent.instances.index( self ) + 1 ) # 1-based
        return j
