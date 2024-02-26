#!/usr/bin/env cwl-runner
baseCommand:
- DOWNLOAD
class: CommandLineTool
cwlVersion: v1.2
inputs:
  # S3 or DAAC or HTTP
  download_type:
    type: string
  downloading_keys:
    default: data, metadata
    type: string
  downloading_roles:
    default: data, metadata
    type: string
  edl_password:
    type: string
    default: '/sps/processing/workflows/edl_password'
  edl_password_type:
    default: 'PARAM_STORE'
    type: string
  edl_username:
    default: '/sps/processing/workflows/edl_username'
    type: string
  stac_json:
    type: string 

# DAPA auth
  unity_username:
    default: '/sps/processing/workflows/unity_username'
    type: string
  unity_password:
    default: '/sps/processing/workflows/unity_password'
    type: string
  unity_type: 
    default: 'PARAM_STORE'
    type: string
  unity_client_id: 
    type: string
  unity_cognito: 
    type: string
    default: 'https://cognito-idp.us-west-2.amazonaws.com'
  unity_ssl:
    type: string
    default: 'TRUE'
  # NONE or UNITY
  unity_stac_auth:
    type: string
    default: 'NONE'
     
outputs:
  stage_in_collection_file:
    outputBinding:
      glob: stage-in-results.json
    type: File
  stage_in_download_dir:
    outputBinding:
      glob: .
    type: Directory
requirements:
  DockerRequirement:
    dockerPull: ghcr.io/unity-sds/unity-data-services:6.4.3
  EnvVarRequirement:
    envDef:
      DOWNLOADING_KEYS: $(inputs.downloading_keys)
      DOWNLOADING_ROLES: $(inputs.downloading_roles)
      DOWNLOAD_DIR: $(runtime.outdir)
      DOWNLOAD_RETRY_TIMES: '5'
      DOWNLOAD_RETRY_WAIT_TIME: '30'
      EDL_BASE_URL: https://urs.earthdata.nasa.gov/
      EDL_PASSWORD: $(inputs.edl_password)
      EDL_PASSWORD_TYPE: $(inputs.edl_password_type)
      EDL_USERNAME: $(inputs.edl_username)
      GRANULES_DOWNLOAD_TYPE: $(inputs.download_type)
      LOG_LEVEL: '20'
      OUTPUT_FILE: $(runtime.outdir)/stage-in-results.json
      PARALLEL_COUNT: '-1'
      #what if this is a string?
      STAC_JSON: $(inputs.stac_json) 

      USERNAME: $(inputs.unity_username)
      PASSWORD: $(inputs.unity_password)
      PASSWORD_TYPE: $(inputs.unity_type)
      CLIENT_ID: $(inputs.unity_client_id)
      COGNITO_URL: $(inputs.unity_cognito)
      VERIFY_SSL: $(inputs.unity_ssl)
      
      #'UNITY | NONE'
      STAC_AUTH_TYPE: $(inputs.unity_stac_auth)
      
