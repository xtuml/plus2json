from setuptools import setup

if __name__ == '__main__':
    setup(name='plus2json',
          version='0.0.1',
          description='PLUS Activity PlantUML Parser/Processor',
          author='Cortland Starrett',
          author_email='cort@roxsoftware.com',
          url='https://github.com/xtuml/plus2json',
          license='Apache 2.0',
          keywords='xtuml bridgepoint protocol verifier',
          packages=['plus2json', 'plus2json.plus', 'plus2json.schema'],
          install_requires=['antlr4-python3-runtime==4.13.0', 'pyxtuml==2.3.1'],
          include_package_data=True,
          zip_safe=True)
