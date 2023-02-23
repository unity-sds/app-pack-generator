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
  InlineJavascriptRequirement: {}
  ShellCommandRequirement: {}
  InitialWorkDirRequirement:
    listing:
      - entryname: /tmp/inputs.json
        entry: $(inputs)
      - entryname: $(inputs.output_directory)
        entry: "$({class: 'Directory', listing: []})"
        writable: true
  InplaceUpdateRequirement:
    inplaceUpdate: true
  NetworkAccess:
    networkAccess: true
inputs:
  output_directory: string
outputs:
  output_dir:
    outputBinding:
      glob: $(inputs.output_directory)
    type: Directory
  output_nb:
    outputBinding:
      glob: output_nb.ipynb
    type: File
stdout: _stdout.txt
