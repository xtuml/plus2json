import argparse
import antlr4
import json
import logging
import os
import os.path
import sys
import tempfile
import uuid
import xtuml

from pretty_print import JobDefn_pretty_print
from definition import JobDefn_json
from play import JobDefn_play, Job_pretty_print, Job_json

from PlusLexer import PlusLexer
from PlusParser import PlusParser
from populate import PlusPopulator, PlusErrorListener
from antlr4.error.Errors import CancellationException

logger = logging.getLogger(__name__)


def main():

    # parse command line
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--pretty-print', action='store_true', help='Print human readable debug output')
    parser.add_argument('-o', '--outdir', metavar='dir', help='Path to output directory')
    parser.add_argument('-v', '--version', action='version', version='v0.x')
    parser.add_argument('filenames', nargs='*', help='Input .puml files')
    parser2 = argparse.ArgumentParser()
    subparsers = parser2.add_subparsers(help='TODO test subcommand help', required=True)
    job_parser = subparsers.add_parser('job', help='Ouput PLUS job definition', parents=[parser])
    job_parser.set_defaults(func=process_job_definitions)
    play_parser = subparsers.add_parser('play', help='Generate runtime event data for a job', parents=[parser])
    play_parser.add_argument('--integer-ids', action='store_true', help='Use deterministic integer IDs')
    play_parser.set_defaults(func=play_job_definitions)
    args = parser2.parse_args()

    if len(args.filenames) > 0:

        # load the metamodel
        metamodel = xtuml.load_metamodel('plus_schema.sql')

        # process each input .puml file
        for filename in args.filenames:
            try:
                error_listener = PlusErrorListener(filename)
                lexer = PlusLexer(antlr4.FileStream(filename))
                lexer.addErrorListener(error_listener)
                tokens = antlr4.CommonTokenStream(lexer)
                parser = PlusParser(tokens)
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

        # call the subcommand
        args.metamodel = metamodel
        args.func(**vars(args))

    else:
        logger.warning('No files to process')


# process job definitions
def process_job_definitions(metamodel=None, pretty_print=False, outdir=None, **kwargs):

    # output each job definition
    for job_defn in metamodel.select_many('JobDefn'):
        if pretty_print:
            JobDefn_pretty_print(job_defn)
        else:
            output = json.dumps(JobDefn_json(job_defn), indent=4, separators=(',', ': '))
            if outdir:
                write_output_file(output, outdir, f'{job_defn.Name}.json')
            else:
                print(output)


# process runtime play
def play_job_definitions(metamodel=xtuml.MetaModel(), pretty_print=False, integer_ids=False, outdir=None, **kwargs):

    # configure the unique ID generator
    if integer_ids or pretty_print:
        metamodel.id_generator = xtuml.IntegerGenerator()
    else:
        metamodel.id_generator = type('PlusUUIDGenerator', (xtuml.IdGenerator,), {'readfunc': lambda self: uuid.uuid4()})()

    # play each job definition
    for job_defn in metamodel.select_many('JobDefn'):
        job = JobDefn_play(job_defn)
        if pretty_print:
            Job_pretty_print(job)
        else:
            output = json.dumps(Job_json(job), indent=4, separators=(',', ': '))
            if outdir:
                write_output_file(output, outdir, f'{job.Id}.json')
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
