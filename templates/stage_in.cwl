#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool
baseCommand: ["python3", "/home/jovyan/stage_in.py", "/tmp/inputs.json"]
requirements:
  DockerRequirement:
    dockerPull: 'jplzhan/ci-generated-images:jplzhan.maap-ci-stage-io.v8'
  ShellCommandRequirement: {}
  InitialWorkDirRequirement:
    listing:
      - entryname: /tmp/inputs.json
        entry: $(inputs)
  NetworkAccess:
    networkAccess: true

inputs:
  cache_dir: Directory?
  cache_only: boolean?
  input_path:
    type:
      - type: record
        name: S3
        inputBinding:
          valueFrom: S3
        fields:
          s3_url:
            type:
              - string
              - string[]
          aws_access_key_id: string
          aws_secret_access_key: string
          aws_session_token: string?
          region: string?
      - type: record
        name: DAAC
        inputBinding:
          valueFrom: DAAC
        fields:
          url:
            type:
              - string
              - string[]
          username: string
          password: string
      - type: record
        name: MAAP
        inputBinding:
          valueFrom: MAAP
        fields:
          collection_id: string
          granule_name: string
      - type: record
        name: Role
        inputBinding:
          valueFrom: Role
        fields:
          role_arn: string
          source_profile: string
      - type: record
        name: Local
        inputBinding:
          valueFrom: Local
        fields:
          path:
            type:
              - File
              - File[]
      - type: record
        name: HTTP
        inputBinding:
          valueFrom: HTTP
        fields:
          url:
            type:
              - string
              - string[]
      - type: record
        name: S3_unsigned
        inputBinding:
          valueFrom: S3_unsigned
        fields:
          s3_url:
            type:
              - string
              - string[]

outputs:
  stdout_txt:
    type: stdout
  output_file:
    type: File[]
    outputBinding:
      glob: inputs/*/*