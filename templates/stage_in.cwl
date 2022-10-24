#!/usr/bin/env cwl-runner
cwlVersion: v1.1
class: CommandLineTool
hints:
  DockerRequirement:
    dockerPull: 'jplzhan/ci-generated-images:jplzhan.maap-ci-stage-io.v7'
baseCommand: ["python3", "/home/jovyan/stage_in.py"]
requirements:
  ShellCommandRequirement: {}
  NetworkAccess:
    networkAccess: true

inputs:
  input_path:
    type:
      - type: record
        name: HTTP
        fields:
          url:
            type: string
            inputBinding:
              position: 1
              shellQuote: false
              valueFrom: HTTP "$(self)"
      - type: record
        name: S3_unsigned
        fields:
          s3_url:
            type: string
            inputBinding:
              position: 1
              shellQuote: false
              valueFrom: S3_unsigned "$(self)"
      - type: record
        name: S3
        fields:
          s3_url:
            type: string
            inputBinding:
              position: 1
              shellQuote: false
              valueFrom: S3 "$(self)"
          aws_access_key_id:
            type: string
            inputBinding:
              position: 2
              shellQuote: false
              valueFrom: "$(self)"
          aws_secret_access_key:
            type: string
            inputBinding:
              position: 3
              shellQuote: false
              valueFrom: "$(self)"
          aws_session_token:
            type: string
            inputBinding:
              position: 4
              shellQuote: false
              valueFrom: "$(self)"
          region:
            type: string
            inputBinding:
              position: 5
              shellQuote: false
              valueFrom: "$(self)"
      - type: record
        name: DAAC
        fields:
          url:
            type: string
            inputBinding:
              position: 1
              shellQuote: false
              valueFrom: DAAC "$(self)"
          username:
            type: string
            inputBinding:
              position: 2
              shellQuote: false
              valueFrom: "$(self)"
          password:
            type: string
            inputBinding:
              position: 3
              shellQuote: false
              valueFrom: "$(self)"
      - type: record
        name: MAAP
        fields:
          collection_id:
            type: string
            inputBinding:
              position: 1
              shellQuote: false
              valueFrom: MAAP "$(self)"
          granule_name:
            type: string
            inputBinding:
              position: 2
              shellQuote: false
              valueFrom: "$(self)"
      - type: record
        name: Role
        fields:
          role_arn:
            type: string
            inputBinding:
              position: 1
              shellQuote: false
              valueFrom: Role "$(self)"
          source_profile:
            type: string
            inputBinding:
              position: 2
              shellQuote: false
              valueFrom: "$(self)"
      - type: record
        name: Local
        fields:
          path:
            type: File
            inputBinding:
              position: 1
              shellQuote: false
              valueFrom: Local "$(self.path)"

outputs:
  stdout_txt:
    type: stdout
  output_file:
    type: File
    outputBinding:
      glob: inputs/*