#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool
baseCommand:
  - papermill
  - /home/jovyan/process.ipynb
  - --cwd
  - /home/jovyan
  - process_output/output_nb.ipynb
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
      - entryname: process_output
        entry: "$({class: 'Directory', listing: []})"
        writable: true
  InplaceUpdateRequirement:
    inplaceUpdate: true
  NetworkAccess:
    networkAccess: true
inputs: {}
outputs:
  process_output_dir:
    outputBinding:
      glob: "$(runtime.outdir)/process_output"
    type: Directory
  process_output_nb:
    outputBinding:
      glob: "$(runtime.outdir)/process_output/output_nb.ipynb"
    type: File
stdout: stdout.txt
