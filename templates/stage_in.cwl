#!/usr/bin/env cwltool
cwlVersion: v1.1
class: CommandLineTool
hints:
  DockerRequirement:
    dockerPull: 'jplzhan/ci-generated-images:jplzhan.maap-ci-stage-io.main'
baseCommand: ["python3", "/home/jovyan/stage_in.py"]
requirements:
  ShellCommandRequirement: {}
  NetworkAccess:
    networkAccess: true
  EnvVarRequirement:
    envDef:
      AWS_ACCESS_KEY_ID: $(inputs.aws_access_key_id)
      AWS_SECRET_ACCESS_KEY: $(inputs.aws_secret_access_key)

inputs:
  # AWS S3 bucket access parameters
  aws_access_key_id: string
  aws_secret_access_key: string

  # The type of path to download (e.g. HTTP, S3, etc...)
  staging_type:
    type: string
    inputBinding:
      position: 1
      shellQuote: false

  # Stage in parameter to download
  input_path:
    type: string
    inputBinding:
      position: 2
      shellQuote: false

outputs:
  stdout_txt:
    type: stdout
  output_file:
    type: File
    outputBinding:
      glob: inputs/*