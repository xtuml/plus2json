import os
import os.path
import sys
import json
import tempfile
import xtuml
from antlr4 import *
from os.path import abspath
from pathlib import Path
package_path = abspath(Path(__file__).parent)
sys.path.insert(0, package_path)
from plus2jsonLexer import plus2jsonLexer
from plus2jsonParser import plus2jsonParser
from plus2jsonListener import plus2jsonListener
from plus2json_run import plus2json_run
from plus_job_defn import *

from populate import PlusPopulator
import plus_job_defn_print3

def main(argv):

    if ( "--help" in argv or "-h" in argv or len(argv) < 2 ):
        print("""
Usage
=====
  python3 plus2json.pyz <PLUS PlantUML file> [options]

  With no options, plus2json will check the syntax of the input PlantUML file.

Options
=======
--help, -h               show this help message and exit
--job, -j                output PLUS Job Definition (JSON)
--play                   interpret the job and produce events
--print, -p              pretty print human readable output

Examples:

python plus2json.pyz Tutorial_1.puml --job                # convert Tutorial_1.puml into JSON
python plus2json.pyz myjobdefn.puml --play                # interpret the job producing event instances
python -m plus2json Tutorial_1.puml --job -p              # show job in human readable view
python ../plus2json/__main__.py Tutorial_1.puml --job -p  # run from the raw source code

        """)

    input_stream = FileStream(argv[1])
    lexer = plus2jsonLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = plus2jsonParser(stream)
    tree = parser.plusdefn()
    populator = PlusPopulator()
    populator.visit(tree)
    if ( "--print" in argv or "-p" in argv or "--job" in argv or "-j" in argv or
        "--play" in argv ):
        run = plus2json_run() # custom listener
        walker = ParseTreeWalker()
        walker.walk(run, tree)
    if "--job" in argv or "-j" in argv:
        if "--print" in argv or "-p" in argv:
            #JobDefn.instances[-1].pretty_print()
            plus_job_defn_print3.JobDefn_pretty_print(populator.m.select_one('JobDefn'))
        else:
            j = JobDefn.instances[-1].json()
            if j:
                write_json_output(j, argv, JobDefn.instances[-1].JobDefinitionName + '.json')
    elif "--play" in argv:
        if "--print" in argv or "-p" in argv:
            print( JobDefn.instances[-1].play("pretty") )
        else:
            j = JobDefn.instances[-1].play("")
            if j:
                write_json_output(j, argv, str(JobDefn.instances[-1].jobId) + '.json')
    elif 2 == len( argv ):
        print( "syntax check complete" )
    else:
        main( "--help" )


def write_json_output(j, argv, outfilename):
    if j:
        try:
            output = json.dumps(json.loads(str(j)), indent=4, separators=(',', ': '))
        except json.decoder.JSONDecodeError:
            print('Failed to parse JSON:\n' + j, file=sys.stderr)
            raise
        outfile = None
        if '--outdir' in argv:
            outdir = argv[ argv.index( '--outdir' ) + 1 ]
            os.makedirs(outdir, exist_ok=True)
            outfile = os.path.join(outdir, outfilename)
            with tempfile.NamedTemporaryFile(mode='w', dir=os.getcwd(), delete=False) as f:
                f.write(output)
                f.flush()
                tmpfilename = f.name
            os.replace(tmpfilename, outfile)
        else:
            print(output)

 
if __name__ == '__main__':
    main(sys.argv)

