#!/usr/bin/env cwltool

cwlVersion: v1.1
class: Workflow
$namespaces:
  cwltool: 'http://commonwl.org/cwltool#'
hints:
  'cwltool:Secrets':
    secrets:
      - workflow_aws_access_key_id
      - workflow_aws_secret_access_key

inputs:
  workflow_aws_access_key_id: string
  workflow_aws_secret_access_key: string
  var_1: 
    type:
      - type: record
        name: HTTP
        fields:
          url: string
      - type: record
        name: S3_unsigned
        fields:
          s3_url: string
      - type: record
        name: S3
        fields:
          s3_url: string
          aws_access_key_id: string
          aws_secret_access_key: string
  var_2:
    type:
      - type: record
        name: HTTP
        fields:
          url: string
      - type: record
        name: S3_unsigned
        fields:
          s3_url: string
      - type: record
        name: S3
        fields:
          s3_url: string
          aws_access_key_id: string
          aws_secret_access_key: string

outputs:

steps:
  stage_in_var_1:
    run: stage_in.cwl
    in:
      input_path: var_1
    out:
      - output_file

  stage_in_var_2:
    run: stage_in.cwl
    in:
      input_path: var_2
    out:
      - output_file

  process:
    run: process.cwl
    in:
      var_1: stage_in_var_1/output_file
      var_2: stage_in_var_2/output_file
    out:
      - output_nb

  stage_out:
    run: stage_out.cwl
    in:
      aws_access_key_id: workflow_aws_access_key_id
      aws_secret_access_key: workflow_aws_secret_access_key
      output_nb: process/output_nb
    out: []
