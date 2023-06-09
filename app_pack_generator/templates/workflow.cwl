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
        edl_username: string
        edl_password: string
    default:
      download_type: DAAC
      edl_username: ""
      edl_password: ""
      
  ###########
  # Stage Out
  stage_out:
    type:
      type: record
      fields:
        collection_id: string
        aws_access_key_id: string
        aws_secret_access_key: string
        aws_session_token: string
        unity_username: string
        unity_password: string
        unity_client_id: string
        unity_dapa_api: string
        staging_bucket: string

  # Workflow
  parameters:
    type:
      type: record
      fields: {}

outputs: {}

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

    out: [stage_in_catalog_file, stage_in_download_dir]

  process:
    run: process.cwl

    in: {}

    out:
      - process_output_dir
      - process_catalog_file
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
      unity_username:
        source: stage_out
        valueFrom: $(self.unity_username)
      unity_password: 
        source: stage_out
        valueFrom: $(self.unity_password)
      unity_client_id:
        source: stage_out
        valueFrom: $(self.unity_client_id)
      unity_dapa_api:
        source: stage_out
        valueFrom: $(self.unity_dapa_api)
      collection_id:
        source: stage_out
        valueFrom: $(self.collection_id)
      staging_bucket:
        source: stage_out
        valueFrom: $(self.staging_bucket)
      catalog_file: process/process_catalog_file
      output_dir: process/process_output_dir

    out: [stage_out_results] 
