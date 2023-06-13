import antlr4
import argparse
import json
import logging
import os
import os.path
import sys
import tempfile
import textwrap
import uuid
import xtuml

from .definition import JobDefn_json
from .play import JobDefn_play, Job_pretty_print, Job_json
from .plus import PlusLexer, PlusParser
from .populate import PlusPopulator, PlusErrorListener
from .pretty_print import JobDefn_pretty_print

from antlr4.error.Errors import CancellationException
from importlib.resources import files

logger = logging.getLogger('plus2json')


def main():

    # get version
    version = json.loads(files(__package__).joinpath('version.json').read_text())

    # parse command line
    parent_parser = argparse.ArgumentParser(add_help=False)
    global_options = parent_parser.add_argument_group(title='Global Options')
    global_options.add_argument('-v', '--version', action='version', version=f'plus2json v{version["version"]} ({version["build_id"]})')
    global_options.add_argument('-h', '--help', action='help', help='Show this help message and exit')
    global_options.add_argument('--debug', action='store_true', help='Enable debug logging')
    global_options.add_argument('-p', '--pretty-print', action='store_true', help='Print human readable debug output')
    global_options.add_argument('-o', '--outdir', metavar='dir', help='Path to output directory')
    global_options.add_argument('filenames', nargs='*', help='Input .puml files')

    parser = argparse.ArgumentParser(prog='plus2json',
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     usage='python plus2json.pyz <command> [-v] [-h] [--debug] [--pretty-print] [-o dir]  [filenames ...]',
                                     description=textwrap.dedent('''\
                                         plus2json is a utility for processing PLUS job definitions and producing
                                         JSON ouptut for congifuring and testing the protocol verifier.'''),
                                     epilog='See individual command help for usage examples.\n\n',
                                     parents=[parent_parser], add_help=False)
    subparsers = parser.add_subparsers(title='Commands', required=False)

    # job command parser
    job_parser = subparsers.add_parser('job', help='Ouput PLUS job definition', parents=[parent_parser], add_help=False,
                                       formatter_class=argparse.RawTextHelpFormatter,
                                       usage='python plus2json.pyz job [-v] [-h] [--debug] [--pretty-print] [-o dir] [filenames ...]',
                                       description='Process the PLUS file(s) and output the resulting JSON job definition(s).',
                                       epilog=textwrap.dedent('''\
                                           Examples:
                                               # load Tutorial_1.puml and print a human readable version of the definition to the console
                                               python plus2json.pyz job Tutorial_1.puml --pretty-print

                                               # convert Tutorial_1.puml into JSON and output to the console
                                               python plus2json.pyz job Tutorial_1.puml

                                               # convert all .puml files in the 'puml' directory and write each to a JSON file in 'job_definitions'
                                               python plus2json.pyz job -o job_definitions puml/*.puml
                                       '''))
    job_parser.set_defaults(func=job)

    # play command parser
    play_parser = subparsers.add_parser('play', help='Generate runtime event data', parents=[parent_parser], add_help=False,
                                        formatter_class=argparse.RawTextHelpFormatter,
                                        # usage='python plus2json.pyz play [-v] [-h] [--debug] [--pretty-print] [-o dir] [--integer-ids] [--persist-einv] [--inv-store store_file] [filenames ...]',
                                        usage='python plus2json.pyz play [-v] [-h] [--debug] [--pretty-print] [-o dir] [--integer-ids] [filenames ...]',
                                        description='Process the PLUS file(s) and output runtime data corresponding to each job definition.',
                                        epilog=textwrap.dedent('''\
                                            Examples:
                                                # load Tutorial_1.puml and print a human readable stream of events to the console
                                                python plus2json.pyz play Tutorial_1.puml --pretty-print

                                                # load Tutorial_1.puml and print a JSON stream of events to the console
                                                python plus2json.pyz play Tutorial_1.puml

                                                # load all .puml files in the 'puml' directory and write steam of events for each to a JSON file in 'job_definitions'
                                                python plus2json.pyz play -o job_definitions puml/*.puml
                                        '''))
    play_options = play_parser.add_argument_group(title='Play Options')
    play_options.add_argument('--integer-ids', action='store_true', help='Use deterministic integer IDs')
    # play_options.add_argument('--persist-einv', action='store_true', help='Persist external invariants in a file store')
    # play_options.add_argument('--inv-store', metavar='store_file', help='Location to persist external invariant values', default='p2jInvariantStore')
    play_parser.set_defaults(func=play)

    args = parser.parse_args()

    # configure logging
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(stream=sys.stderr, level=(logging.DEBUG if args.debug else logging.INFO), format='%(levelname)s: %(message)s')

    if hasattr(args, 'func'):
        args.func(**vars(args))
    else:
        check(**vars(args))


def check(**kwargs):
    p2j = Plus2Json(outdir=kwargs['outdir'])
    if 'filenames' in kwargs and len(kwargs['filenames']) > 0:
        p2j.load_files(kwargs['filenames'])
    elif 'input' in kwargs:
        p2j.load_string(kwargs['input'])
    else:
        p2j.load_stream(sys.stdin)


def job(**kwargs):
    p2j = Plus2Json(outdir=kwargs['outdir'])
    integer_ids = kwargs['pretty_print']
    if 'filenames' in kwargs and len(kwargs['filenames']) > 0:
        p2j.load_files(kwargs['filenames'], integer_ids=integer_ids)
    elif 'input' in kwargs:
        p2j.load_string(kwargs['input'], integer_ids=integer_ids)
    else:
        p2j.load_stream(sys.stdin, integer_ids=integer_ids)
    p2j.process_job_definitions(**kwargs)


def play(**kwargs):
    p2j = Plus2Json(outdir=kwargs['outdir'])
    integer_ids = (kwargs['integer_ids'] or kwargs['pretty_print'])
    if 'filenames' in kwargs and len(kwargs['filenames']) > 0:
        p2j.load_files(kwargs['filenames'], integer_ids=integer_ids)
    elif 'input' in kwargs:
        p2j.load_string(kwargs['input'], integer_ids=integer_ids)
    else:
        p2j.load_stream(sys.stdin, integer_ids=integer_ids)
    p2j.play_job_definitions(**kwargs)


class Plus2Json:

    def __init__(self, outdir=None):
        self.outdir = outdir

    def load_files(self, filenames, integer_ids=False):
        inputs = map(lambda fn: (fn, antlr4.FileStream(fn)), filenames)
        self.load(inputs, integer_ids)

    def load_stream(self, stream, integer_ids=False):
        inputs = [('STDIN', antlr4.InputStream(stream.read()))]
        self.load(inputs, integer_ids)

    def load_string(self, input, integer_ids=False):
        inputs = [('INPUT', antlr4.InputStream(str(input)))]
        self.load(inputs, integer_ids)

    def load(self, inputs, integer_ids):
        # load the metamodel
        loader = xtuml.ModelLoader()
        loader.input(files(__package__).joinpath('schema').joinpath('plus_schema.sql').read_text())
        self.metamodel = loader.build_metamodel()

        # configure the unique ID generator
        if integer_ids:
            self.metamodel.id_generator = xtuml.IntegerGenerator()
        else:
            self.metamodel.id_generator = type('PlusUUIDGenerator', (xtuml.IdGenerator,), {'readfunc': lambda self: uuid.uuid4()})()

        # process each .puml input stream
        for filename, stream in inputs:
            try:
                error_listener = PlusErrorListener(filename)
                lexer = PlusLexer(stream)
                lexer.addErrorListener(error_listener)
                tokens = antlr4.CommonTokenStream(lexer)
                parser = PlusParser(tokens)
                parser.addErrorListener(error_listener)
                tree = parser.plusdefn()
            except (CancellationException, IOError):
                logger.error(f'Failed to parse file "{os.path.basename(filename)}".')
                continue
            populator = PlusPopulator(self.metamodel)
            populator.visit(tree)

        # assure model consistency
        self.check_consistency()

    def check_consistency(self):
        if xtuml.check_association_integrity(self.metamodel) + xtuml.check_uniqueness_constraint(self.metamodel) > 0:
            logger.error('Failed model integrity check')
            sys.exit(1)

    # process job definitions
    def process_job_definitions(self, **kwargs):

        # output each job definition
        for job_defn in self.metamodel.select_many('JobDefn'):
            if kwargs['pretty_print']:
                JobDefn_pretty_print(job_defn)
            else:
                output = json.dumps(JobDefn_json(job_defn), indent=4, separators=(',', ': '))
                if self.outdir:
                    self.write_output_file(output, f'{job_defn.Name}.json')
                else:
                    print(output)

    # process runtime play
    def play_job_definitions(self, **kwargs):

        # play each job definition
        jobs = map(JobDefn_play, self.metamodel.select_many('JobDefn'))

        # assure model consistency
        self.check_consistency()

        # render each runtime job
        for job in jobs:
            if kwargs['pretty_print']:
                Job_pretty_print(job)
            else:
                output = json.dumps(Job_json(job), indent=4, separators=(',', ': '))
                if self.outdir:
                    self.write_output_file(output, f'{xtuml.navigate_one(job).JobDefn[101]().Name.replace(" ", "_")}_{job.Id}.json')
                else:
                    print(output)

    # atomically write output to a file
    def write_output_file(self, output, filename):
        os.makedirs(self.outdir, exist_ok=True)
        outfile = os.path.join(self.outdir, filename)
        with tempfile.NamedTemporaryFile(mode='w', dir=os.getcwd(), delete=False) as f:
            f.write(output)
            f.flush()
            tmpfilename = f.name
        os.replace(tmpfilename, outfile)
