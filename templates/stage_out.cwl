#!/usr/bin/env cwltool
class: CommandLineTool
cwlVersion: v1.1
baseCommand: ["sh", "stage_out.sh"]

requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: stage_out.sh
        entry: |-
            #!/bin/bash -xe
            echo "Hello world!"
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

  output_nb: File
outputs:
stdout: stage_out_stdout.txt
stderr: stage_out_stderr.txt