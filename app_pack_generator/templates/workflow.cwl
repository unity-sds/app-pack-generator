#!/usr/bin/env cwltool

cwlVersion: v1.2
class: Workflow
$namespaces:
  cwltool: 'http://commonwl.org/cwltool#'
requirements:
  StepInputExpressionRequirement: {}
inputs:
  stage_out:
    type:
    - fields:
        aws_access_key_id: string
        aws_secret_access_key: string
        aws_session_token: string
        region_name: string
        s3_url: string
      name: STAK
      type: record
    - fields:
        aws_config: Directory
        s3_url: string
      name: LTAK
      type: record
    - fields:
        s3_url: string
      name: IAM
      type: record
  cache_dir: Directory?
  cache_only:
    default: false
    type: boolean
  output_directory:
    type: string
    default: output
  parameters:
    type:
      name: parameters
      type: record
      fields: {}

outputs: {}
steps:
  stage_in_var_1:
    run: stage_in.cwl
    in:
      input_path: var_1
    out:
      - output_files

  stage_in_var_2:
    run: stage_in.cwl
    in:
      input_path: var_2
    out:
      - output_files

  process:
    run: process.cwl
    in:
      var_1: stage_in_var_1/output_files
      var_2: stage_in_var_2/output_files
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
