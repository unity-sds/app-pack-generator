#!/usr/bin/env cwltool

cwlVersion: v1.1
class: Workflow
$namespaces:
  cwltool: 'http://commonwl.org/cwltool#'
inputs:
  stage_out:
    type:
      - type: record
        name: STAK
        fields:
          aws_access_key_id: string
          aws_secret_access_key: string
          aws_session_token: string
          region: string
          s3_url: string
      - type: record
        name: LTAK
        fields:
          s3_url: string
          aws_config: Directory
      - type: record
        name: IAM
        fields:
          s3_url: string
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
          aws_session_token: string
          region: string
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
          aws_session_token: string
          region: string

outputs: {}
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
      - output_dir
      - output_nb

  stage_out:
    run: stage_out.cwl
    in:
      output_path: stage_out
      output_dir: process/output_dir
      output_nb: process/output_nb
    out: []
