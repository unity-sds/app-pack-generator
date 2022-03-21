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
  workflow_input_url: string
  workflow_min_spin_time: int
  workflow_max_spin_time: int
  workflow_aws_access_key_id: string
  workflow_aws_secret_access_key: string
  workflow_base_dataset_url: string

outputs:
  final_dataset_dir:
    type: Directory
    outputSource: process/dataset_dir
  stdout-process:
    type: File
    outputSource: process/stdout_file
  stderr-process:
    type: File
    outputSource: process/stderr_file
  stdout-stage_out:
    type: File
    outputSource: stage_out/stdout_file
  stderr-stage_out:
    type: File
    outputSource: stage_out/stderr_file

steps:

  stage_in:
    run: stage_in.cwl
    in:
      input_url: workflow_input_url
    out:
      - output_nb_file
      - image_file
      - stdout_file
      - stderr_file

  process:
    run: process.cwl
    in:
      input_file: stage_in/image_file
      min_spin_time: workflow_min_spin_time
      max_spin_time: workflow_max_spin_time
    out:
      - output_nb_file
      - dataset_dir
      - stdout_file
      - stderr_file

  stage_out:
    run: stage_out.cwl
    in:
      aws_access_key_id: workflow_aws_access_key_id
      aws_secret_access_key: workflow_aws_secret_access_key
      dataset_dir: process/dataset_dir
      base_dataset_url: workflow_base_dataset_url
    out:
      - stdout_file
      - stderr_file
