class: CommandLineTool
cwlVersion: v1.0
baseCommand: ["sh", "stage_in.sh"]

requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: stage_in.sh
        entry: |-
            #!/bin/bash -xe
            mkdir -f /home/jovyan/input

inputs:
  message: string
  input_1: string
  numeral: float
outputs:
  inputs_yml:
    type: File
    outputBinding:
        glob: /home/jovyan/inputs/inputs.yml
stdout: stage_in_stdout.txt
stderr: stage_in_stderr.txt