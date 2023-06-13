import antlr4_tool_runner
import bridgepoint
import json
import os
import subprocess
import sys
import xtuml
import zipapp

VERSION = '0.0.1'


def gen_grammar():
    # generate Plus
    print('Genearting Antlr Parser...')
    argv = sys.argv
    sys.argv = ['', '-v', '4.13.0', '-Dlanguage=Python3', '-no-listener', '-visitor', '-o', 'plus2json/plus', '-Xexact-output-dir', 'grammar/Plus.g4']
    antlr4_tool_runner.tool()
    sys.argv = argv
    print('Done')

    # check environment
    if 'BPHOME' not in os.environ or 'WORKSPACE' not in os.environ:
        raise RuntimeError('BPHOME or WORKSPACE environment variables are not set')


def gen_schema():
    # prebuild model
    print('Prebuilding model...')
    args = ('/bin/bash', os.path.join(os.environ['BPHOME'], 'tools', 'mc', 'bin', 'CLI.sh'), 'Build', '-prebuildOnly', '-project', 'plus')
    print(' '.join(args))
    p = subprocess.run(args, capture_output=True)
    print(p.stdout.decode('utf-8'), end='')
    print(p.stderr.decode('utf-8'), end='', file=sys.stderr)
    print('Done')

    # generate schema
    print('Generating schema...')
    os.makedirs(os.path.join('plus2json', 'schema'), exist_ok=True)
    c = bridgepoint.load_component(os.path.join('models', 'plus', 'gen', 'code_generation', 'plus.sql'))
    xtuml.persist_database(c, os.path.join('plus2json', 'schema', 'plus_schema.sql'))
    print('Done')


def gen_version():
    # create a version file
    print('Write version file...')
    args = ('git', 'rev-parse', '--short', 'HEAD')
    p = subprocess.run(args, capture_output=True)
    sha = p.stdout.decode('utf-8').strip()
    version = {'version': VERSION, 'build_id': sha}
    with open(os.path.join('plus2json', 'version.json'), 'w') as f:
        json.dump(version, f)
    print('Done')


def gen_zipapp():
    # install dependencies
    args = ('python', '-m', 'pip', 'install', '--upgrade', '.', '--target', 'dist')
    p = subprocess.run(args, capture_output=True)
    print(p.stdout.decode('utf-8'), end='')
    print(p.stderr.decode('utf-8'), end='', file=sys.stderr)

    # generate zipapp
    print('Creating zipapp...')
    zipapp.create_archive('dist', target='plus2json.pyz', compressed=True, interpreter='/usr/bin/env python3', main='plus2json:main')
    print('Done')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        match sys.argv[1]:
            case 'grammar':
                gen_grammar()
            case 'schema':
                gen_schema()
            case 'version':
                gen_version()
            case 'zipapp':
                gen_zipapp()
            case 'dev':
                gen_grammar()
                gen_schema()
                gen_version()
    else:
        gen_grammar()
        gen_schema()
        gen_version()
        gen_zipapp()
