#!/bin/bash

# print plus2json version
P2J="python -m plus2json"
$P2J -v

# get list of puml files
json_files=$(ls -1 ../munin/deploy/config/job_definitions/*.json | sort)

# run each file
echo "Converting JSON job definitions..."
while IFS= read -r line; do
  echo ${line}
  $P2J --json2plus "${line}"
  sleep 0.1
done <<< "$json_files"
echo "Done."
