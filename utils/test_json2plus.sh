#!/bin/bash

# print plus2json version
P2J="python -m plus2json"
$P2J -v

# get list of puml files
puml_files=$(ls -1 ../munin/tests/PumlForTesting/PumlRegression/*.puml | sort)

# run each file
echo "Converting job definitions..."
for fn in ${puml_files}; do
  echo ${fn}
  $P2J --json2plus ${fn}
  sleep 0.1
done
echo "Done."
