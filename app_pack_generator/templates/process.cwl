#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool
baseCommand:
  - papermill
  - /home/jovyan/process.ipynb
  - --cwd
  - /home/jovyan
  - output_nb.ipynb
  - -f
  - /tmp/inputs.json
  - --log-output
  - -k
  - python3
requirements:
  DockerRequirement:
    dockerPull: marjoluc/hello-world:stable
  InlineJavascriptRequirement: {}
  ShellCommandRequirement: {}
  InitialWorkDirRequirement:
    listing:
      - entryname: /tmp/inputs.json
        entry: $(inputs)
  InplaceUpdateRequirement:
    inplaceUpdate: true
  NetworkAccess:
    networkAccess: true
inputs:
  # Where the incoming data for the process is placed
  input: Directory
outputs:
  # Where the process placed outgoing data
  output:
    outputBinding:
      glob: "$(runtime.outdir)"
    type: Directory
  process_output_nb:
    outputBinding:
      glob: "$(runtime.outdir)/output_nb.ipynb"
    type: File
