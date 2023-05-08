import os
import os.path
import sys
import json
import tempfile
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
--aeo_config             output AEOrdering config.json (JSON)
--aesim_test             output AESimulator scenario dispatch JSON with --play
--aesim_config           output AESimulator config JSON when combined with --play
--print, -p              pretty print human readable output

Examples:

python plus2json.pyz Tutorial_1.puml --job                # convert Tutorial_1.puml into JSON
python plus2json.pyz myjobdefn.puml --play                # interpret the job producing event instances
python plus2json.pyz myjobdefn.puml --play --aesim_config # produce a valid AESimulator sequence
python -m plus2json Tutorial_1.puml --job -p              # show job in human readable view
python ../plus2json/__main__.py Tutorial_1.puml --job -p  # run from the raw source code

        """)

    input_stream = FileStream(argv[1])
    lexer = plus2jsonLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = plus2jsonParser(stream)
    tree = parser.plusdefn()
    if ( "--print" in argv or "-p" in argv or "--job" in argv or "-j" in argv or
        "--play" in argv or "--aeo_config" in argv or "--aesim_config" in argv or
        "--aesim_test" in argv ):
        run = plus2json_run() # custom listener
        walker = ParseTreeWalker()
        walker.walk(run, tree)
    if "--job" in argv or "-j" in argv:
        if "--print" in argv or "-p" in argv:
            JobDefn.instances[-1].pretty_print()
        else:
            j = JobDefn.instances[-1].json()
            if j:
                write_json_output(j, argv, JobDefn.instances[-1].JobDefinitionName + '.json')
    elif "--play" in argv:
        outfile = None
        if "--print" in argv or "-p" in argv:
            print( JobDefn.instances[-1].play("pretty") )
        elif "--aesim_config" in argv:
            j = JobDefn.instances[-1].play("aesim")
            if j:
                write_json_output(j, argv, 'test-scenario.json')
        elif "--aesim_test" in argv:
            j = JobDefn.instances[-1].play("aestest")
            if j:
                write_json_output(j, argv, 'test-specification.json')
        else:
            j = JobDefn.instances[-1].play("")
            if j:
                write_json_output(j, argv, str(JobDefn.instances[-1].jobId) + '.json')
    elif "--aeo_config" in argv:
        j = JobDefn.aeo_config_all()
        if j:
            write_json_output(j, argv)
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
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write(output)
                f.flush()
                os.replace(f.name, outfile)
        else:
            print(output)

 
if __name__ == '__main__':
    main(sys.argv)

