#!/bin/bash

pythoncommand="python3"

if [ "$1" == "" ]; then
  echo "warning: argument <python command> missing, default to python3"
else
  pythoncommand="$1"
fi

cp ../mads mads -r

$pythoncommand -c "from mads.const import VERSION;f = open('VERSION', 'w');f.write(str(VERSION))"
version="$(cat VERSION)"

zip -r "../dist/mads_source_${version}.zip" mads/*.py -j

rm mads -rf
rm VERSION
