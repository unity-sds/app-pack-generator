#!/usr/bin/env cwl-runner
cwlVersion: v1.2
$graph:
- class: Workflow
  label: ""
  doc: ""
  id: ""
  inputs: {}
    # Where the incoming data for the process is placed
  outputs:
    out:
      type: Directory
      outputSource: process/outputs_result
  steps:
    process:
      run: '#main'
      in: {}
      out:
      - outputs_result
      - process_output_nb
- class: CommandLineTool
  id: main
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
  inputs: {}
    # Where the incoming data for the process is placed
  outputs:
    # Where the process placed outgoing data
    outputs_result:
      outputBinding:
        glob: "$(runtime.outdir)"
      type: Directory
    process_output_nb:
      outputBinding:
        glob: "$(runtime.outdir)/output_nb.ipynb"
      type: File

s:author:
- class: s:Person
  s:name: arthurduf
s:contributor:
- class: s:Person
  s:name: arthurduf
s:citation: https://github.com/MAAP-Project/sardem-sarsen.git
s:codeRepository: https://github.com/MAAP-Project/sardem-sarsen.git
s:commitHash: 1f2c57760b5334472b0f9d719dcb09cae99297a7
s:dateCreated: 2025-12-04
s:license: https://github.com/MAAP-Project/sardem-sarsen/blob/main/LICENSE
s:softwareVersion: 1.0.0
s:version: mlucas_nasa-ogc
s:releaseNotes: None
s:keywords: ogc, sar
$namespaces:
  s: https://schema.org/
$schemas:
- https://raw.githubusercontent.com/schemaorg/schemaorg/refs/heads/main/data/releases/9.0/schemaorg-current-http.rdf