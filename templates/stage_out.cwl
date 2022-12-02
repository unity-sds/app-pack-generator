#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool
baseCommand: ["python3", "/home/jovyan/stage_out.py"]
requirements:
  DockerRequirement:
    dockerPull: 'jplzhan/ci-generated-images:jplzhan.maap-ci-stage-io.v8'
  ShellCommandRequirement: {}
  NetworkAccess:
    networkAccess: true

inputs:
  output_path:
    type:
      - type: record
        name: STAK
        fields:
          aws_access_key_id:
            inputBinding:
              position: 4
              shellQuote: false
              valueFrom: "$(self)"
            type: string
          aws_secret_access_key:
            inputBinding:
              position: 5
              shellQuote: false
              valueFrom: "$(self)"
            type: string
          aws_session_token:
            inputBinding:
              position: 6
              shellQuote: false
              valueFrom: "$(self)"
            type: string
          region:
            inputBinding:
              position: 7
              shellQuote: false
              valueFrom: "$(self)"
            type: string
          s3_url:
            inputBinding:
              position: 3
              shellQuote: false
              valueFrom: "$(self)"
            type: string
      - type: record
        name: LTAK
        fields:
          s3_url:
            inputBinding:
              position: 3
              shellQuote: false
              valueFrom: "$(self)"
            type: string
          aws_config:
            inputBinding:
              position: 4
              shellQuote: false
              valueFrom: "$(self.path)"
            type: Directory
      - type: record
        name: IAM
        fields:
          s3_url:
            inputBinding:
              position: 3
              shellQuote: false
              valueFrom: "$(self)"
            type: string
  output_dir:
    inputBinding:
      position: 1
      shellQuote: false
      valueFrom: "$(self.path)"
    type: Directory
  output_nb:
    inputBinding:
      position: 2
      shellQuote: false
      valueFrom: "$(self.path)"
    type: File
outputs: {}
stderr: stage_out_stderr.txt
stdout: stage_out_stdout.txt