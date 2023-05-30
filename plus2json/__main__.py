import argparse
import antlr4
import xtuml

import plus_job_defn_print3  # TODO

from plus2jsonLexer import plus2jsonLexer
from plus2jsonParser import plus2jsonParser
from populate import PlusPopulator


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
        lexer = plus2jsonLexer(antlr4.FileStream(filename))
        tokens = antlr4.CommonTokenStream(lexer)
        parser = plus2jsonParser(tokens)
        tree = parser.plusdefn()
        populator = PlusPopulator(metamodel)
        populator.visit(tree)

    # process job definitions
    if args.job:
        for job in metamodel.select_many('JobDefn'):
            if args.pretty_print:
                plus_job_defn_print3.JobDefn_pretty_print(job)


if __name__ == '__main__':
    main()
