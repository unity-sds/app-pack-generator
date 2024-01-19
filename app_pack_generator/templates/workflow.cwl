#!/usr/bin/env cwltool

cwlVersion: v1.2
class: Workflow

$namespaces:
  cwltool: 'http://commonwl.org/cwltool#'

requirements:
  SubworkflowFeatureRequirement: {}
  StepInputExpressionRequirement: {}
  InlineJavascriptRequirement: {}
  NetworkAccess:
    networkAccess: true

inputs:

  ##########
  # Stage In
  stage_in:
    type:
      type: record
      fields:
        stac_json: File
        download_type: string # DAAC or S3
        edl_username: [ string, 'null' ]
        edl_password: [ string, 'null' ]
        edl_password_type: [ string, 'null' ]
        downloading_keys: [ string, 'null' ]
      
  ###########
  # Stage Out
  stage_out:
    type:
      type: record
      fields:
        collection_id: [ string, 'null' ]
        aws_region: [ string, 'null' ]
        aws_access_key_id: [ string, 'null' ]
        aws_secret_access_key: [ string, 'null' ]
        aws_session_token: [ string, 'null' ]
        staging_bucket: [ string, 'null' ]

  # Workflow
  parameters:
    type:
      type: record
      fields: {}

outputs:
  stage_out_results:
    type: File
    outputSource: stage_out/stage_out_results  

steps:
  stage_in:
    run: stage_in.cwl

    in:
      stac_json:
        source: stage_in
        valueFrom: $(self.stac_json)
      download_type:
        source: stage_in
        valueFrom: $(self.download_type)
      edl_username:
        source: stage_in
        valueFrom: $(self.edl_username)
      edl_password:
        source: stage_in
        valueFrom: $(self.edl_password)
      edl_password_type:
        source: stage_in
        valueFrom: $(self.edl_password_type)
      downloading_keys:
        source: stage_in
        valueFrom: $(self.downloading_keys)

    out: [stage_in_collection_file, stage_in_download_dir]

  process:
    run: process.cwl

    in: {}

    out:
      - process_output_dir
      - process_output_nb

  stage_out:
    run: stage_out.cwl

    in:
      aws_access_key_id:
        source: stage_out
        valueFrom: $(self.aws_access_key_id)
      aws_secret_access_key:
        source: stage_out
        valueFrom: $(self.aws_secret_access_key)
      aws_session_token:
        source: stage_out
        valueFrom: $(self.aws_session_token)
      collection_id:
        source: stage_out
        valueFrom: $(self.collection_id)
      staging_bucket:
        source: stage_out
        valueFrom: $(self.staging_bucket)
      output_dir: process/process_output_dir

    out: [stage_out_results] 
