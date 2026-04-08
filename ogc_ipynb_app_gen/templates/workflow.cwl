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
        stac_json: [string, File]
        download_type: string # DAAC or S3
        edl_username: [ string, 'null' ]
        edl_password: [ string, 'null' ]
        edl_password_type: [ string, 'null' ]
        downloading_keys: [ string, 'null' ]
        downloading_roles: [ string, 'null' ]
        unity_client_id: string
        unity_stac_auth: string # UNITY or NONE
      
  ###########
  # Stage Out
  stage_out:
    type:
      type: record
      fields:
        project: [ string, 'null' ]
        venue: [ string, 'null' ]
        aws_region: [ string, 'null' ]
        aws_access_key_id: [ string, 'null' ]
        aws_secret_access_key: [ string, 'null' ]
        aws_session_token: [ string, 'null' ]
        staging_bucket: [ string, 'null' ]
        result_path_prefix: [ string, 'null' ]

  # Workflow
  parameters:
    type:
      type: record
      fields: {}

outputs:
  stage_out_results:
    type: File
    outputSource: stage_out/stage_out_results 
  stage_out_success:
    type: File
    outputSource: stage_out/successful_features
  stage_out_failures:
    type: File
    outputSource: stage_out/failed_features 

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
      downloading_roles:
        source: stage_in
        valueFrom: $(self.downloading_roles)
      unity_client_id:
        source: stage_in
        valueFrom: $(self.unity_client_id)
      unity_stac_auth:
        source: stage_in
        valueFrom: $(self.unity_stac_auth)

    out: [stage_in_collection_file, stage_in_download_dir]

  process:
    run: process.cwl

    in: {}

    out:
      - output
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
      result_path_prefix:
        source: stage_out
        valueFrom: $(self.result_path_prefix)
      output_dir: process/output

    out: [stage_out_results, successful_features, failed_features] 
