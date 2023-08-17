import antlr4
import argparse
import asyncio
import json
import logging
import os
import os.path
import random
import sys
import tempfile
import textwrap
import time
import uuid
import xtuml

from .definition import JobDefn_json
from .play import JobDefn_play, Job_pretty_print, Job_json, Job_dispose
from .plus import PlusLexer, PlusParser
from .populate import PlusPopulator, PlusErrorListener, flatten
from .pretty_print import JobDefn_pretty_print

from antlr4.error.Errors import CancellationException
from importlib.resources import files
from itertools import cycle
from kafka3 import KafkaProducer

from xtuml import navigate_any as any

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
    global_options.add_argument('-o', '--outdir', help='Path to output directory')
    global_options.add_argument('filenames', nargs='*', help='Input .puml files')

    # play specific options
    play_options = parser.add_argument_group(title='Play Options')
    play_options.add_argument('--all', action='store_true', help='Play all pathways through the job definition')
    play_options.add_argument('--msgbroker', help='Play audit events to message broker <host:port>')
    play_options.add_argument('--topic', help='Specify message broker publish topic <topic name>')
    play_options.add_argument('--integer-ids', action='store_true', help='Use deterministic integer IDs')
    play_options.add_argument('--shuffle', action='store_true', help='Shuffle the events before writing to a file.')
    play_options.add_argument('--num-events', type=int, default=0, help='The number of events to produce. If omitted, each job will be played one time.')
    play_options.add_argument('--batch-size', type=int, default=500, help='The number of events per file. Default is 500. Only valid if "--num-events" is present.')
    play_options.add_argument('--rate', type=int, default=0, help='The number of events per second. When present events will be generated indefinitely at the specified rate.')
    play_options.add_argument('--no-persist-einv', action='store_true', help='Do not persist external invariants in a file store')
    play_options.add_argument('--inv-store-file', help='Location to persist external invariant values', default='p2jInvariantStore')
    play_options.add_argument('--event-data', action='append', help='Key/value pairs for source event data values', default=[])
    play_options.add_argument('--replace', nargs='?', const='REPLACEME', default=None, help='Replace named audit event with unhappy event')
    play_options.add_argument('--insert', nargs='?', const='INSERTBEFOREME', default=None, help='Insert an unhappy event before the named audit event')

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
        self.producer = None

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
        opts.event_data = dict((s.split('=') + [1])[:2] for s in (opts.event_data if hasattr(opts, 'event_data') else []))

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

    # validate job definitions
    def validate_job_definitions(self, job_defns):
        '''check various rules to enforce constraints on job definitions'''
        valid = True

        # enforce rule that requires unhappy events and critical events to come together
        for job_defn in job_defns:
            critical_event = any(job_defn).SeqDefn[1].AuditEventDefn[2](lambda sel: sel.IsCritical)
            unhappy_event = any(job_defn).PkgDefn[20].UnhappyEventDefn[21]()
            if (critical_event is None) is not (unhappy_event is None):  # XOR
                logger.error(f'Invalid job definition:  {job_defn.Name} - unhappy event / critical event violation')
                valid = False

        return valid

    # process job definitions
    def process_job_definitions(self):
        opts = self.metamodel.select_any('_Options')

        job_defns = self.metamodel.select_many('JobDefn')

        # enforce validation rules on job definitions
        if not self.validate_job_definitions(job_defns):
            # invalid:  get out
            return

        for job_defn in job_defns:
            if opts.pretty_print:
                JobDefn_pretty_print(job_defn)
            else:
                output = json.dumps(JobDefn_json(job_defn), indent=4)
                if self.outdir:
                    self.write_output_file(output, f'{job_defn.Name}.json')
                else:
                    print(output)

    # process runtime play
    def play_job_definitions(self):
        opts = self.metamodel.select_any('_Options')

        job_defns = self.metamodel.select_many('JobDefn')

        # enforce validation rules on job definitions
        if not self.validate_job_definitions(job_defns):
            # invalid:  get out
            return

        # initialise the message broker
        if opts.msgbroker:
            if not opts.topic:
                logger.error('--msgbroker specified without --topic')
                sys.exit(1)
            else:
                self.producer = KafkaProducer(bootstrap_servers=opts.msgbroker)

        if opts.num_events != 0 and opts.rate != 0:
            logger.error('incompatible options --num-events and --rate')
            sys.exit(1)

        # play all job definitions once
        if opts.num_events != 0:
            self.play_volume_mode(job_defns)

        # play all job definitions at a specified rate
        if opts.rate != 0:
            if opts.msgbroker:
                self.play_rate_mode(job_defns)
            else:
                logger.error('rate mode only supported with --msgbroker')
                sys.exit(1)

        # play all job definitions once
        else:
            self.play_normal_mode(job_defns)

        # shutdown the message broker
        if opts.msgbroker:
            self.producer.flush()
            self.producer.close()

    def play_normal_mode(self, job_defns):
        opts = self.metamodel.select_any('_Options')

        # play each job definition
        jobs = flatten(map(JobDefn_play, job_defns))

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
                if opts.msgbroker:
                    for event in events:
                        msg = self.preprocess_payload(json.dumps(event, indent=4))
                        self.producer.send(opts.topic, msg)
                else:
                    output = json.dumps(events, indent=4)
                    if self.outdir:
                        self.write_output_file(output, f'{xtuml.navigate_one(job).JobDefn[101]().Name.replace(" ", "_")}_{job.Id}.json')
                    else:
                        print(output)

            Job_dispose(job)

    def play_volume_mode(self, job_defns):
        opts = self.metamodel.select_any('_Options')

        # create an infinite cycle iterator of job definitions
        job_defn_iter = cycle(job_defns)

        num_events_produced = 0
        events = []

        # keep generating until we produce 1.2M events
        while num_events_produced < opts.num_events:

            # batches of 500 events per file
            while len(events) < min(opts.batch_size, opts.num_events - num_events_produced):
                jobs = JobDefn_play(next(job_defn_iter))
                if jobs:
                    events.extend(Job_json(jobs[0], dispose=True))

            # shuffle the events
            if opts.shuffle:
                random.shuffle(events)

            # write the batch of events
            if opts.msgbroker:
                fn = opts.msgbroker
                for event in events:
                    msg = self.preprocess_payload(json.dumps(event, indent=4))
                    self.producer.send(opts.topic, msg)
            else:
                output = json.dumps(events, indent=4)
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

    def play_rate_mode(self, job_defns):
        opts = self.metamodel.select_any('_Options')

        # create an infinite cycle iterator of job definitions
        job_defn_iter = cycle(job_defns)

        # create an event queue
        event_queue = []
        buffer_len_low = opts.rate * 1    # start refill when there's 1 seconds of buffer left/
        buffer_len_high = opts.rate * 2  # maintain a 2 second buffer
        delay = 1 / opts.rate

        # refill the queue if it needs more events
        async def fill_queue():
            while True:
                if len(event_queue) < buffer_len_low:
                    # refill
                    new_events = []
                    while len(new_events) < buffer_len_high - len(event_queue):
                        jobs = JobDefn_play(next(job_defn_iter))
                        if jobs:
                            new_events.extend(Job_json(jobs[0], dispose=True))
                    # shuffle the events
                    if opts.shuffle:
                        random.shuffle(new_events)
                    event_queue.extend(new_events)
                await asyncio.sleep(0)  # give up control

        # publish the messages from the queue
        async def publish():
            while True:
                if len(event_queue) > 0:
                    t0 = time.time()
                    msg = self.preprocess_payload(json.dumps(event_queue.pop(0)))  # remove from the front
                    self.producer.send(opts.topic, msg)
                    elapsed = time.time() - t0
                    await asyncio.sleep(delay - elapsed)
                else:
                    await asyncio.sleep(0)

        # start event loop
        loop = asyncio.get_event_loop()
        tasks = asyncio.gather(fill_queue(), publish())
        try:
            loop.run_until_complete(tasks)
        except KeyboardInterrupt:
            tasks.cancel()
        finally:
            loop.close()

    # atomically write output to a file
    def write_output_file(self, output, filename):
        os.makedirs(self.outdir, exist_ok=True)
        outfile = os.path.join(self.outdir, filename)
        with tempfile.NamedTemporaryFile(mode='w', dir=os.getcwd(), delete=False) as f:
            f.write(output)
            f.flush()
            tmpfilename = f.name
        os.replace(tmpfilename, outfile)

    # pre-process message payload
    def preprocess_payload(self, s):
        '''prepend length as 4 byte Big Endian integer to message bytes (C++ architecture)'''
        payload = s.encode('utf-8')
        msglen = len(payload).to_bytes(4, 'big')
        msg = msglen + payload
        return msg
