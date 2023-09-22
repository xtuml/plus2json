from setuptools import setup

if __name__ == '__main__':
    version='1.1.0',
    setup(name='plus2json',
          description='PLUS Activity PlantUML Parser/Processor',
          author='Cortland Starrett',
          author_email='cort@roxsoftware.com',
          url='https://github.com/xtuml/plus2json',
          license='Apache 2.0',
          keywords='xtuml bridgepoint protocol verifier',
          packages=['plus2json', 'plus2json.plus', 'plus2json.schema'],
          package_data={'plus2json': ['version.json'], 'plus2json.plus': ['*.interp', '*.tokens'], 'plus2json.schema': ['plus_schema.sql']},
          install_requires=['antlr4-python3-runtime==4.13.0', 'pyxtuml==2.3.1', 'kafka-python3==3.0.0'],
          test_suite='tests',
          include_package_data=True,
          zip_safe=True)
