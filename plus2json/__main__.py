import argparse
import antlr4
import json
import logging
import os
import os.path
import sys
import tempfile
import xtuml

import plus_job_defn_print3  # TODO
import plus_job_defn_json2  # TODO

from plus2jsonLexer import plus2jsonLexer
from plus2jsonParser import plus2jsonParser
from populate import PlusPopulator, PlusErrorListener
from antlr4.error.Errors import CancellationException

logger = logging.getLogger(__name__)


def main():

    # parse command line
    p = argparse.ArgumentParser(prog='plus2json', description='PlantUML processor')
    p.add_argument('-j', '--job', action='store_true', help='Ouput PLUS job definition')
    p.add_argument('-p', '--play', action='store_true', help='Generate runtime event data for a job')
    p.add_argument('-o', '--outdir', metavar='dir', help='Path to output directory')
    p.add_argument('--pretty-print', action='store_true', help='Print human readable debug output')
    p.add_argument('-v', '--version', action='version', version='v0.x')
    p.add_argument('filenames', nargs='+', help='Input .puml files')
    args = p.parse_args()

    # do not allow -j and -p in the same command
    if args.job and args.play:
        p.error('Cannot process and play jobs in the same command')

    # load the metamodel
    metamodel = xtuml.load_metamodel('plus_schema.sql')

    # process each input .puml file
    for filename in args.filenames:
        try:
            error_listener = PlusErrorListener(filename)
            lexer = plus2jsonLexer(antlr4.FileStream(filename))
            lexer.addErrorListener(error_listener)
            tokens = antlr4.CommonTokenStream(lexer)
            parser = plus2jsonParser(tokens)
            parser.addErrorListener(error_listener)
            tree = parser.plusdefn()
        except CancellationException:
            logger.error(f'Failed to parse {os.path.basename(filename)}.')
            continue
        populator = PlusPopulator(metamodel)
        populator.visit(tree)

    # assure model consistency
    if xtuml.check_association_integrity(metamodel) + xtuml.check_uniqueness_constraint(metamodel) > 0:
        logger.error('Failed model integrity check')
        sys.exit(1)

    # process job definitions
    if args.job:
        for job in metamodel.select_many('JobDefn'):
            if args.pretty_print:
                plus_job_defn_print3.JobDefn_pretty_print(job)
            output = json.dumps(plus_job_defn_json2.JobDefn_json(job), indent=4, separators=(',', ': '))
            if args.outdir:
                write_output_file(output, args.outdir, f'{job.Name}.json')
            else:
                print(output)


# atomically write output to a file
def write_output_file(output, outdir, filename):
    os.makedirs(outdir, exist_ok=True)
    outfile = os.path.join(outdir, filename)
    with tempfile.NamedTemporaryFile(mode='w', dir=os.getcwd(), delete=False) as f:
        f.write(output)
        f.flush()
        tmpfilename = f.name
    os.replace(tmpfilename, outfile)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    main()
