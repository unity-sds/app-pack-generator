#!/usr/bin/env cwl-runner
cwlVersion: v1.1
class: CommandLineTool
baseCommand: [papermill, /home/jovyan/process.ipynb, output_nb.ipynb]
hints:
  DockerRequirement:
    dockerPull: marjoluc/hello-world:stable
requirements:
  ShellCommandRequirement: {}
  NetworkAccess:
    networkAccess: true
inputs:
  input_1:
    type: string
    inputBinding:
      position: 1
      shellQuote: false
      prefix: --parameters
      valueFrom: |
        input_1 "$(self)"
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
