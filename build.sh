#!/bin/bash -xe
WorkingDir=$(pwd)
ParserDir="/home/ubuntu/zhan/app-pack-generator"
Parser="$ParserDir/parser.py"
PythonExe="python3"
ActivateVEnv="source $ParserDir/env/bin/activate"

TestingDir="/home/zhan/downsample-landsat"
ARTIFACT_DIR="$WorkingDir/artifact-deposit-repo"
ARTIFACT_URL="git@github.com:jplzhan/artifact-deposit-repo.git"
export GIT_SSH_COMMAND="ssh -i $ARTIFACT_SSH"

echo "$(ls -la $ParserDir)"

git clone "$ARTIFACT_URL" "$ARTIFACT_DIR"

$ActivateVEnv
env ARTIFACT_DIR=$ARTIFACT_DIR $PythonExe "$Parser" "$repository" "$checkout"
deactivate
