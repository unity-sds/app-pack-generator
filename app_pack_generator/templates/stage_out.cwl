cwlVersion: v1.2
class: CommandLineTool

baseCommand: ["UPLOAD"]

stdout: stage-out-results.json

requirements:
  DockerRequirement:
    dockerPull: ghcr.io/unity-sds/unity-data-services:5.3.1
  InitialWorkDirRequirement:
    listing:
    - entry: $(inputs.output_dir)
      entryname: /tmp/outputs
  EnvVarRequirement:
    envDef:
      AWS_REGION: $(inputs.aws_region)
      AWS_ACCESS_KEY_ID: $(inputs.aws_access_key_id)
      AWS_SECRET_ACCESS_KEY: $(inputs.aws_secret_access_key)
      AWS_SESSION_TOKEN: $(inputs.aws_session_token)

      COLLECTION_ID: $(inputs.collection_id)
      STAGING_BUCKET: $(inputs.staging_bucket)
      CATALOG_FILE: '/tmp/outputs/catalog.json'
      OUTPUT_FILE: '$(runtime.outdir)/stage-out-results.json'

inputs:
  aws_region:
    type: string
    default: us-west-2
  aws_access_key_id:
    type: string
    default: ''
  aws_secret_access_key:
    type: string
    default: ''
  aws_session_token:
    type: string
    default: ''
  collection_id:
    type: string
    default: ''
  staging_bucket:
    type: string
    default: ''
  output_dir:
    type: Directory

outputs:
  stage_out_results:
    type: File
    outputBinding:
      glob: "$(runtime.outdir)/stage-out-results.json"
