#!/bin/bash -xe
WorkingDir=$(pwd)
ParserDir="/home/ubuntu/zhan/app-pack-generator"
Parser="$ParserDir/parser.py"
PythonExe="python3.7"
ActivateVEnv="source $ParserDir/env/bin/activate"

TestingDir="/home/zhan/downsample-landsat"
ARTIFACT_DIR="$WorkingDir/artifact-deposit-repo"

echo "$(ls -la $ParserDir)"

$ActivateVEnv
env ARTIFACT_DIR=$ARTIFACT_DIR $PythonExe "$Parser" "$repository" "$checkout"
deactivate

ls -la
