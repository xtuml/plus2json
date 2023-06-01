"""

Test plus2json --job --print.

"""

import sys
import io
import runpy
from contextlib import redirect_stdout
from os.path import abspath
from pathlib import Path
package_path = abspath(Path(__file__).parent)
sys.path.insert(0, package_path)
import unittest
from plus_job_defn import *
from plus_job_defn_aeo import *
from plus_job_defn_json import *
from plus_job_defn_play import *
from plus_job_defn_print import *
from plus_job_defn_aesim import *
from plus_job_defn_aesim_test import *

class TestJobPrint(unittest.TestCase):
    """Test plus2json --job --print"""
    def run_and_compare(self, test_name, job_file, results_file):
        # TODO - The following shows a weakness in the arrangment of data.
        Fork.instances.clear()
        Fork.c_scope = -1
        Fork.c_number = 1
        # end TODO
        job_file = "../tests/" + job_file
        results_file = "../tests/" + results_file
        with open(results_file,"r") as f:
            golden = f.read()
        f_stdout = io.StringIO()
        with redirect_stdout(f_stdout):
            sys.argv = ['', job_file, '--job', '--print']
            runpy.run_path('__main__.py', run_name='__main__')
            #main( sys.argv )
        my_output = f_stdout.getvalue()
        self.assertEqual( my_output, golden, "failed:" + test_name )

    def test_job_print_01(self):
        self.run_and_compare( '01', 't01_straight.puml', 't01-j-p.txt' )

    def test_job_print_02(self):
        self.run_and_compare( '02', 't02_fork.puml', 't02-j-p.txt' )

    def test_job_print_03(self):
        self.run_and_compare( '03', 't03_split.puml', 't03-j-p.txt' )

    def test_job_print_04(self):
        self.run_and_compare( '04', 't04_if.puml', 't04-j-p.txt' )

    def test_job_print_05(self):
        self.run_and_compare( '05', 't05_switch.puml', 't05-j-p.txt' )

    def test_job_print_06(self):
        self.run_and_compare( '06', 't06_mixed.puml', 't06-j-p.txt' )

    def test_job_print_07(self):
        self.run_and_compare( '07', 't07_mixed2.puml', 't07-j-p.txt' )

    def test_job_print_08(self):
        self.run_and_compare( '08', 't08_unhappy1.puml', 't08-j-p.txt' )

    def test_job_print_09(self):
        self.run_and_compare( '09', 't09_unhappy2.puml', 't09-j-p.txt' )

if __name__ == '__main__':
    unittest.main()
