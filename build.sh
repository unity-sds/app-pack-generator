#!/bin/bash -xe
WorkingDir=$(pwd)
ParserDir="/home/ubuntu/zhan/app-pack-generator"
Parser="$ParserDir/parser.py"
PythonExe="python3"
ActivateVEnv="source $ParserDir/env/bin/activate"

TestingDir="/home/zhan/downsample-landsat"
ARTIFACT_DIR="$WorkingDir/artifact-deposit-repo"

echo "$(ls -la $ParserDir)"

GIT_SSH=$ARTIFACT_SSH git clone git@github.com:jplzhan/artifact-deposit-repo.git

$ActivateVEnv
env ARTIFACT_DIR=$ARTIFACT_DIR $PythonExe "$Parser" "$repository" "$checkout"
deactivate

ls -la
