class: CommandLineTool
cwlVersion: v1.0
baseCommand: ["sh", "stage_out.sh"]

requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: stage_out.sh
        entry: |-
            #!/bin/bash -xe
            echo "Hello world!"

inputs:
  output_nb: File
outputs:
stdout: stage_out_stdout.txt
stderr: stage_out_stderr.txt