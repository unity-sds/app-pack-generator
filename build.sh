#!/bin/sh -xe
WorkingDir=$(pwd)
ParserDir="/home/zhan/app-pack-generator"
Parser="$ParserDir/parser.py"
PythonExe="python3.6"
ActivateVEnv="source $ParserDir/env/bin/activate"

TestingDir="/home/zhan/downsample-landsat"
ARTIFACT_DIR="$WorkingDir/artifact-deposit-repo"

$ActivateVEnv
env ARTIFACT_DIR=$ARTIFACT_DIR $PythonExe "$Parser" "$repository" "$checkout"
deactivate

ls -la
