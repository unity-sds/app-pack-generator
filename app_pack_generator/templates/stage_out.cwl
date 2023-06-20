cwlVersion: v1.2
class: CommandLineTool

baseCommand: ["UPLOAD"]

stdout: stage-out-results.json

requirements:
  DockerRequirement:
    dockerPull: ghcr.io/unity-sds/unity-data-services:4.0.0
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

      USERNAME: $(inputs.unity_username)
      PASSWORD: $(inputs.unity_password)
      PASSWORD_TYPE: 'BASE64'

      CLIENT_ID: $(inputs.unity_client_id)
      COGNITO_URL: $(inputs.unity_cognito_url)
      DAPA_API: $(inputs.unity_dapa_api)

      COLLECTION_ID: $(inputs.collection_id)
      STAGING_BUCKET: $(inputs.staging_bucket)
      DELETE_FILES: 'FALSE'
      GRANULES_SEARCH_DOMAIN: 'UNITY'
      GRANULES_UPLOAD_TYPE: 'CATALOG_S3'
      CATALOG_FILE: 'catalog.json'

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
  unity_username:
    type: string
    default: ''
  unity_password:
    type: string
    default: ''
  unity_client_id:
    type: string
    default: ''
  unity_cognito_url:
    type: string
    default: https://cognito-idp.us-west-2.amazonaws.com
  unity_dapa_api:
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
    type: stdout
