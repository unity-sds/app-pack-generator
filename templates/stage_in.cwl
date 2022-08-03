#!/usr/bin/env cwltool
cwlVersion: v1.1
class: CommandLineTool
hints:
  DockerRequirement:
    dockerPull: 'jplzhan/ci-generated-images:jplzhan.maap-ci-stage-io.main'
baseCommand: ["python3", "stage_in.py"]
requirements:
  ShellCommandRequirement: {}
  NetworkAccess:
    networkAccess: true

inputs:
  input_path:
    type: string
    inputBinding:
      position: 1
      shellQuote: false
      valueFrom: |
        "$(self)"

outputs:
  output_file:
    type: File
    outputBinding:
      glob: "$(outputs.stdout_of_stage_in_script)"