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

from .pretty_print import JobDefn_pretty_print
from .definition import JobDefn_json
from .play import JobDefn_play, Job_pretty_print, Job_json
from .populate import PlusPopulator, PlusErrorListener
from .plus import PlusLexer, PlusParser

from antlr4.error.Errors import CancellationException
from importlib.resources import files

logger = logging.getLogger('plus2json')


def plus2json():

    # parse command line
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--pretty-print', action='store_true', help='Print human readable debug output')
    parser.add_argument('-o', '--outdir', metavar='dir', help='Path to output directory')
    parser.add_argument('-v', '--version', action='version', version='v0.x')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('filenames', nargs='*', help='Input .puml files')
    parser2 = argparse.ArgumentParser()
    subparsers = parser2.add_subparsers(help='TODO test subcommand help', required=True)
    job_parser = subparsers.add_parser('job', help='Ouput PLUS job definition', parents=[parser])
    job_parser.set_defaults(func=process_job_definitions)
    play_parser = subparsers.add_parser('play', help='Generate runtime event data for a job', parents=[parser])
    play_parser.add_argument('--integer-ids', action='store_true', help='Use deterministic integer IDs')
    play_parser.add_argument('--persist-einv', action='store_true', help='Persist external invariants in a file store')
    play_parser.add_argument('--inv-store', help='Location to persist external invariant values', default='p2jInvariantStore')
    play_parser.set_defaults(func=play_job_definitions)
    args = parser2.parse_args()

    # configure logging
    logging.basicConfig(stream=sys.stderr, level=(logging.DEBUG if args.debug else logging.INFO))

    if len(args.filenames) > 0:

        # load the metamodel
        loader = xtuml.ModelLoader()
        loader.input(files('plus2json.schema').joinpath('plus_schema.sql').read_text())
        metamodel = loader.build_metamodel()

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
        args.func(metamodel, args)

    else:
        logger.warning('No files to process')


# process job definitions
def process_job_definitions(metamodel, args):

    # output each job definition
    for job_defn in metamodel.select_many('JobDefn'):
        if args.pretty_print:
            JobDefn_pretty_print(job_defn)
        else:
            output = json.dumps(JobDefn_json(job_defn), indent=4, separators=(',', ': '))
            if args.outdir:
                write_output_file(output, args.outdir, f'{job_defn.Name}.json')
            else:
                print(output)


# process runtime play
def play_job_definitions(metamodel, args):

    # configure the unique ID generator
    if args.integer_ids or args.pretty_print:
        metamodel.id_generator = xtuml.IntegerGenerator()
    else:
        metamodel.id_generator = type('PlusUUIDGenerator', (xtuml.IdGenerator,), {'readfunc': lambda self: uuid.uuid4()})()

    # play each job definition
    jobs = map(JobDefn_play, metamodel.select_many('JobDefn'))

    # assure model consistency
    if xtuml.check_association_integrity(metamodel) + xtuml.check_uniqueness_constraint(metamodel) > 0:
        logger.error('Failed model integrity check')
        sys.exit(1)

    # render each runtime job
    for job in jobs:
        if args.pretty_print:
            Job_pretty_print(job)
        else:
            output = json.dumps(Job_json(job), indent=4, separators=(',', ': '))
            if args.outdir:
                write_output_file(output, args.outdir, f'{xtuml.navigate_one(job).JobDefn[101]().Name.replace(" ", "_")}_{job.Id}.json')
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
