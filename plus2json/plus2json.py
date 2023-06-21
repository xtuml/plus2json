import antlr4
import argparse
import json
import logging
import os
import os.path
import random
import sys
import tempfile
import textwrap
import uuid
import xtuml

from .definition import JobDefn_json
from .play import JobDefn_play, Job_pretty_print, Job_json, Job_dispose
from .plus import PlusLexer, PlusParser
from .populate import PlusPopulator, PlusErrorListener
from .pretty_print import JobDefn_pretty_print

from antlr4.error.Errors import CancellationException
from importlib.resources import files
from itertools import cycle

logger = logging.getLogger('plus2json')


def main():

    # get version
    version = json.loads(files(__package__).joinpath('version.json').read_text())

    # configure command line
    parser = argparse.ArgumentParser(prog='plus2json',
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     description='plus2json is a utility for processing PLUS job definitions and producing JSON ouptut for congifuring and testing the protocol verifier.',
                                     epilog=textwrap.dedent('''\
                                             Examples:
                                                 # load Tutorial_1.puml and print a human readable version of the definition to the console
                                                 python plus2json.pyz job Tutorial_1.puml --pretty-print

                                                 # convert Tutorial_1.puml into JSON and output to the console
                                                 python plus2json.pyz job Tutorial_1.puml

                                                 # convert all .puml files in the 'puml' directory and write each to a JSON file in 'job_definitions'
                                                 python plus2json.pyz job -o job_definitions puml/*.puml
                                                 # load Tutorial_1.puml and print a human readable stream of events to the console
                                                 python plus2json.pyz play Tutorial_1.puml --pretty-print

                                                 # load Tutorial_1.puml and print a JSON stream of events to the console
                                                 python plus2json.pyz play Tutorial_1.puml

                                                 # load all .puml files in the 'puml' directory and write steam of events for each to a JSON file in 'job_definitions'
                                                 python plus2json.pyz play -o job_definitions puml/*.puml
                                     '''), add_help=False)

    # commands
    commands_group = parser.add_argument_group(title='Commands')
    commands = commands_group.add_mutually_exclusive_group()
    commands.add_argument('--job', action='store_true', help='Ouput PLUS job definition')
    commands.add_argument('--play', action='store_true', help='Generate runtime event data')

    # global options
    global_options = parser.add_argument_group(title='Global Options')
    global_options.add_argument('-v', '--version', action='version', version=f'plus2json v{version["version"]} ({version["build_id"]})')
    global_options.add_argument('-h', '--help', action='help', help='Show this help message and exit')
    global_options.add_argument('--debug', action='store_true', help='Enable debug logging')
    global_options.add_argument('-p', '--pretty-print', action='store_true', help='Print human readable debug output')
    global_options.add_argument('-o', '--outdir', metavar='dir', help='Path to output directory')
    global_options.add_argument('filenames', nargs='*', help='Input .puml files')

    # play specific options
    play_options = parser.add_argument_group(title='Play Options')
    play_options.add_argument('--integer-ids', action='store_true', help='Use deterministic integer IDs')
    play_options.add_argument('--num-events', type=int, default=0, help='The number of events to produce. If omitted, each job will be played one time.')
    play_options.add_argument('--batch-size', type=int, default=500, help='The number of events per file. Default is 500. Only valid if "--num-events" is present.')
    play_options.add_argument('--shuffle', action='store_true', help='Shuffle the events before writing to a file.')
    play_options.add_argument('--no-persist-einv', action='store_true', help='Do not persist external invariants in a file store')
    play_options.add_argument('--inv-store-file', metavar='filename', help='Location to persist external invariant values', default='p2jInvariantStore')
    play_options.add_argument('--event-data', action='append', metavar='data', help='Key/value pairs for source event data values', default=[])

    # parse command line
    args = parser.parse_args()

    # configure logging
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(stream=sys.stderr, level=(logging.DEBUG if args.debug else logging.INFO), format='%(levelname)s: %(message)s')

    # execute the command
    if args.job:
        job(**vars(args))
    elif args.play:
        play(**vars(args))
    else:
        check(**vars(args))


def check(**kwargs):
    p2j = Plus2Json(outdir=kwargs['outdir'])
    if 'filenames' in kwargs and len(kwargs['filenames']) > 0:
        p2j.filename_input(kwargs['filenames'])
    elif 'input' in kwargs:
        p2j.string_input(kwargs['input'])
    else:
        p2j.stream_input(sys.stdin)
    p2j.load()


def job(**kwargs):
    p2j = Plus2Json(outdir=kwargs['outdir'])
    if 'filenames' in kwargs and len(kwargs['filenames']) > 0:
        p2j.filename_input(kwargs['filenames'])
    elif 'input' in kwargs:
        p2j.string_input(kwargs['input'])
    else:
        p2j.stream_input(sys.stdin)
    p2j.load(integer_ids=kwargs['pretty_print'], opts=kwargs)
    p2j.process_job_definitions()


def play(**kwargs):
    p2j = Plus2Json(outdir=kwargs['outdir'])
    if 'filenames' in kwargs and len(kwargs['filenames']) > 0:
        p2j.filename_input(kwargs['filenames'])
    elif 'input' in kwargs:
        p2j.string_input(kwargs['input'])
    else:
        p2j.stream_input(sys.stdin)
    p2j.load(integer_ids=(kwargs['integer_ids'] or kwargs['pretty_print']), opts=kwargs)
    p2j.play_job_definitions()


class Plus2Json:

    def __init__(self, outdir=None):
        self.outdir = outdir
        self.inputs = []

    def filename_input(self, filenames):
        if isinstance(filenames, str):
            filenames = [filenames]
        self.inputs += map(lambda fn: (fn, antlr4.FileStream(fn)), filenames)

    def stream_input(self, stream):
        self.inputs += [('STDIN', antlr4.InputStream(stream.read()))]

    def string_input(self, input):
        self.inputs += [('INPUT', antlr4.InputStream(str(input)))]

    def load(self, integer_ids=False, opts={}):
        # load the metamodel
        loader = xtuml.ModelLoader()
        loader.input(files(__package__).joinpath('schema').joinpath('plus_schema.sql').read_text())
        self.metamodel = loader.build_metamodel()

        # configure the unique ID generator
        if integer_ids:
            self.metamodel.id_generator = xtuml.IntegerGenerator()
        else:
            self.metamodel.id_generator = type('PlusUUIDGenerator', (xtuml.IdGenerator,), {'readfunc': lambda self: uuid.uuid4()})()

        # create a global arguments class and singleton instance
        opts = self.metamodel.define_class('_Options', map(lambda item: (item[0], 'STRING'), opts.items())).new(**opts)

        # process input event data
        opts.event_data = dict((s.split('=') + [1])[:2] for s in opts.event_data)

        # process each .puml input stream
        for filename, stream in self.inputs:
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
    def process_job_definitions(self):
        opts = self.metamodel.select_any('_Options')

        # output each job definition
        for job_defn in self.metamodel.select_many('JobDefn'):
            if opts.pretty_print:
                JobDefn_pretty_print(job_defn)
            else:
                output = json.dumps(JobDefn_json(job_defn), indent=4, separators=(',', ': '))
                if self.outdir:
                    self.write_output_file(output, f'{job_defn.Name}.json')
                else:
                    print(output)

    # process runtime play
    def play_job_definitions(self):
        opts = self.metamodel.select_any('_Options')

        job_defns = self.metamodel.select_many('JobDefn')

        # play all job definitions once
        if opts.num_events == 0:

            # play each job definition
            jobs = map(JobDefn_play, job_defns)

            # assure model consistency
            self.check_consistency()

            # render each runtime job
            for job in jobs:
                if opts.pretty_print:
                    Job_pretty_print(job)
                else:
                    # create events
                    events = Job_json(job)

                    # shuffle events
                    if opts.shuffle:
                        random.shuffle(events)

                    # dump to JSON
                    output = json.dumps(events, indent=4, separators=(',', ': '))
                    if self.outdir:
                        self.write_output_file(output, f'{xtuml.navigate_one(job).JobDefn[101]().Name.replace(" ", "_")}_{job.Id}.json')
                    else:
                        print(output)

                Job_dispose(job)

        # play jobs in volume mode
        else:

            # create an infinite cycle iterator of job definitions
            job_defn_iter = cycle(job_defns)

            num_events_produced = 0
            events = []

            # keep generating until we produce 1.2M events
            while num_events_produced < opts.num_events:

                # batches of 500 events per file
                while len(events) < min(opts.batch_size, opts.num_events - num_events_produced):
                    job = JobDefn_play(next(job_defn_iter))
                    events.extend(Job_json(job, dispose=True))

                # shuffle the events
                if opts.shuffle:
                    random.shuffle(events)

                # write the file
                output = json.dumps(events, indent=4, separators=(',', ': '))
                if self.outdir:
                    fn = f'{uuid.uuid4()}.json'
                    self.write_output_file(output, fn)
                else:
                    fn = 'stdout'
                    print(output)

                logger.info(f'File {fn} written with {len(events)} events')

                num_events_produced += len(events)
                events = []

            logger.info(f'Total events produced: {num_events_produced}')

    # atomically write output to a file
    def write_output_file(self, output, filename):
        os.makedirs(self.outdir, exist_ok=True)
        outfile = os.path.join(self.outdir, filename)
        with tempfile.NamedTemporaryFile(mode='w', dir=os.getcwd(), delete=False) as f:
            f.write(output)
            f.flush()
            tmpfilename = f.name
        os.replace(tmpfilename, outfile)
