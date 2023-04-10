"""

Supply Audit Event Simulator (AESim) Test Scenario.

"""

import sys
from os.path import abspath
from pathlib import Path
package_path = abspath(Path(__file__).parent)
sys.path.insert(0, package_path)
import plus_job_defn

# Here, methods are defined to ease the configuration of the AESimulator
# test scenario dispatch sequencing.

class JobDefn_AEStest:
    """AEStest methods for JobDefn"""
    @classmethod
    def aesim_test_header(cls):
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
        return j
    @classmethod
    def aesim_test_footer(cls):
        j = '}]'
        j += '}]'
        j += '}'
        return j
    def aesim_test(self):
        """output AEStest JSON"""
        j = '"TestJobSpecName" : "' + self.JobDefinitionName + '",'
        j += '"EventDispatchOrder" : "'
        return j

class SequenceDefn_AEStest:
    """AEStest methods for Sequence Definition"""
    def aesim_test( self, seqdelim ):
        """output Sequence AEStest JSON"""
        j = ""
        aedelim = seqdelim
        for ae in self.R2_AuditEventDefn_defines:
            j += ae.aesim_test( aedelim )
            aedelim = ','
        return j

class AuditEventDefn_AEStest:
    """AEStest methods Audit Event Definition"""
    def aesim_test(self, delim):
        """output AuditEventDefn AEStest JSON"""
        j = delim + str( plus_job_defn.AuditEventDefn.instances.index( self ) + 1 ) # 1-based
        return j
