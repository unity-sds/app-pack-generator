#!/usr/bin/env cwl-runner
baseCommand:
- UPLOAD
class: CommandLineTool
cwlVersion: v1.2
inputs:
  aws_access_key_id:
    default: ''
    type: string
  aws_region:
    default: us-west-2
    type: string
  aws_secret_access_key:
    default: ''
    type: string
  aws_session_token:
    default: ''
    type: string
  project:
    default: ''
    type: string
  venue:
    default: ''
    type: string
  output_dir:
    type: Directory
  staging_bucket:
    default: ''
    type: string
  result_path_prefix:
    default: ''
    type: string
outputs:
  stage_out_results:
    type: File
    outputBinding:
      glob: "$(runtime.outdir)/stage-out-results.json"
  successful_features:
    type: File
    outputBinding:
      glob: "$(runtime.outdir)/successful_features.json"
  failed_features:
    type: File
    outputBinding:
      glob: "$(runtime.outdir)/failed_features.json"
requirements:
  DockerRequirement:
    dockerPull: ghcr.io/unity-sds/unity-data-services:9.4.0
  EnvVarRequirement:
    envDef:
      AWS_ACCESS_KEY_ID: $(inputs.aws_access_key_id)
      AWS_REGION: $(inputs.aws_region)
      AWS_SECRET_ACCESS_KEY: $(inputs.aws_secret_access_key)
      AWS_SESSION_TOKEN: $(inputs.aws_session_token)
      #CATALOG_FILE: /tmp/outputs/catalog.json
      
      PROJECT: $(inputs.project)
      VENUE: $(inputs.venue)

      STAGING_BUCKET: $(inputs.staging_bucket)
      RESULT_PATH_PREFIX: $(inputs.result_path_prefix)
      CATALOG_FILE: '$(inputs.output_dir.path)/catalog.json'
      OUTPUT_FILE: '$(runtime.outdir)/stage-out-results.json'
      LOG_LEVEL: '20'
      PARALLEL_COUNT: '-1'
      OUTPUT_DIRECTORY: $(runtime.outdir)
      
  InitialWorkDirRequirement:
    listing:
    - entry: $(inputs.output_dir)
      entryname: /tmp/outputs
stdout: stage-out-results.json
