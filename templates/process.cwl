#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool
baseCommand:
  - papermill
  - /home/jovyan/process.ipynb
  - output_nb.ipynb
  - -f
  - /tmp/inputs.json
requirements:
  DockerRequirement:
    dockerPull: marjoluc/hello-world:stable
  ShellCommandRequirement: {}
  InitialWorkDirRequirement:
    listing:
      - entryname: /tmp/inputs.json
        entry: $(inputs)
  NetworkAccess:
    networkAccess: true
inputs:
  input_1: string
outputs:
  output_dir:
    outputBinding:
      glob: output
    type: Directory
  output_nb:
    outputBinding:
      glob: output_nb.ipynb
    type: File
  example_out:
    type: stdout
stdout: _stdout.txt
