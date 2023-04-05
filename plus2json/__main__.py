import sys
import json
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
--audit_event_data, -d   output PLUS audit event data (JSON)
--play                   interpret the job and produce events
--aeo_config             output AEOrdering config.json (JSON)
--aesim_test             output AESimulator scenario dispatch JSON with --play
--aesim_config           output AESimulator config JSON when combined with --play
--print, -p              pretty print human readable output

Examples:

python plus2json.pyz Tutorial_1.puml --job                # convert Tutorial_1.puml into JSON
python plus2json.pyz Tutorial_13.puml -d                  # produce audit event data definition as JSON
python plus2json.pyz myjobdefn.puml --play                # interpret the job producing event instances
python plus2json.pyz myjobdefn.puml --play --aesim_config # produce a valid AESimulator sequence
python -m plus2json Tutorial_1.puml --job -p              # show job in human readable view
python plus2json.pyz j.puml --job | python -m json.tool   # format output JSON
python ../src/__main__.py Tutorial_1.puml --job -p        # run from the raw source code

        """)
        exit()

    input_stream = FileStream(argv[1])
    lexer = plus2jsonLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = plus2jsonParser(stream)
    tree = parser.plusdefn()
    if ( "--print" in argv or "-p" in argv or "--job" in argv or "-j" in argv or
         "--audit_event_data" in argv or "-d" in argv or "--play" in argv or
        "--aeo_config" in argv or "--aesim_config" in argv or "--aesim_test" in argv ):
        run = plus2json_run() # custom listener
        walker = ParseTreeWalker()
        walker.walk(run, tree)
    if "--job" in argv or "-j" in argv:
        if "--print" in argv or "-p" in argv:
            JobDefn.instances[-1].pretty_print()
        else:
            j = JobDefn.instances[-1].json()
            json.dump(json.loads(j), sys.stdout, sort_keys=True, indent=4, separators=(',', ': '))
    elif "--audit_event_data" in argv or "-d" in argv:
        j = Invariant.json()
        # TODO - name the file after the event?
        outfile = None
        if "--outdir" in argv:
            outdir = argv[ argv.index( "--outdir" ) + 1 ]
            outfile = outdir + "/" + "audit_event_data.json"
        f = open( outfile, 'w') if outfile else sys.stdout
        json.dump(json.loads(j), f, sort_keys=True, indent=4, separators=(',', ': '))
    elif "--play" in argv:
        outfile = None
        if "--print" in argv or "-p" in argv:
            print( JobDefn.instances[-1].play("pretty") )
        elif "--aesim_config" in argv:
            j = JobDefn.instances[-1].play("aesim")
            if "--outdir" in argv:
                outdir = argv[ argv.index( "--outdir" ) + 1 ]
                outfile = outdir + "/" + "test-scenario.json"
            f = open( outfile, 'w') if outfile else sys.stdout
            json.dump(json.loads(j), f, sort_keys=True, indent=4, separators=(',', ': '))
        elif "--aesim_test" in argv:
            j = JobDefn.instances[-1].play("aestest")
            if "--outdir" in argv:
                outdir = argv[ argv.index( "--outdir" ) + 1 ]
                outfile = outdir + "/" + "test-specification.json"
            f = open( outfile, 'w') if outfile else sys.stdout
            json.dump(json.loads(j), f, sort_keys=True, indent=4, separators=(',', ': '))
        else:
            j = JobDefn.instances[-1].play("")
            print( json.dumps(json.loads(j), sort_keys=True, indent=4, separators=(',', ': ')) )
    elif "--aeo_config" in argv:
        j = JobDefn.aeo_config_all()
        outfile = None
        if "--outdir" in argv:
            outdir = argv[ argv.index( "--outdir" ) + 1 ]
            outfile = outdir + "/" + "config.json"
        f = open( outfile, 'w') if outfile else sys.stdout
        json.dump(json.loads(j), f, sort_keys=True, indent=4, separators=(',', ': '))
    elif 2 == len( argv ):
        print( "syntax check complete" )
    else:
        main( "--help" )

 
if __name__ == '__main__':
    main(sys.argv)

