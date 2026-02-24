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
- class: CommandLineTool
  id: main
  baseCommand:
    - papermill
    - /home/jovyan/process.ipynb
    - output_nb.ipynb
    - -f
    - /tmp/inputs.json
    - --log-output
    - -k
    - python3
  requirements:
    DockerRequirement:
      dockerPull: unity-sds/mdps-example-application:latest
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

s:author:
- class: s:Person
  s:name: mdps-app-generator
s:citation: ""
s:codeRepository: ""
s:commitHash: ""
s:dateCreated: ""
s:license: ""
s:softwareVersion: ""
s:version: ""
s:releaseNotes: ""
s:keywords: ""
$namespaces:
  s: https://schema.org/
$schemas:
- https://raw.githubusercontent.com/schemaorg/schemaorg/refs/heads/main/data/releases/9.0/schemaorg-current-http.rdf