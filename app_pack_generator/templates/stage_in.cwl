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
    type: 
    - string
    - File 

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
      glob: catalog.json
    type: File
  stage_in_download_dir:
    outputBinding:
      glob: .
    type: Directory
requirements:
  InlineJavascriptRequirement: {}
  DockerRequirement:
    dockerPull: ghcr.io/unity-sds/unity-data-services:9.4.0
  EnvVarRequirement:
    envDef: 
      -  envName: CLIENT_ID
         envValue: $(inputs.unity_client_id)
      -  envName: COGNITO_URL 
         envValue: $(inputs.unity_cognito)
      -  envName: DOWNLOADING_KEYS
         envValue: $(inputs.downloading_keys)
      -  envName: DOWNLOADING_ROLES
         envValue: $(inputs.downloading_roles)
      -  envName: DOWNLOAD_DIR
         envValue: $(runtime.outdir)
      -  envName: DOWNLOAD_RETRY_TIMES
         envValue: '5'
      -  envName: DOWNLOAD_RETRY_WAIT_TIME
         envValue: '30'
      -  envName: EDL_BASE_URL
         envValue: https://urs.earthdata.nasa.gov/
      -  envName: EDL_PASSWORD
         envValue: $(inputs.edl_password)
      -  envName: EDL_PASSWORD_TYPE
         envValue: $(inputs.edl_password_type)
      -  envName: EDL_USERNAME
         envValue: $(inputs.edl_username)
      -  envName: GRANULES_DOWNLOAD_TYPE
         envValue: $(inputs.download_type)
      -  envName: LOG_LEVEL
         envValue: '20'
      -  envName: OUTPUT_FILE
         envValue: $(runtime.outdir)/catalog.json
      -  envName: PARALLEL_COUNT
         envValue: '-1'
      -  envName: PASSWORD
         envValue: $(inputs.unity_password)
      -  envName: PASSWORD_TYPE
         envValue: $(inputs.unity_type)
      -  envName: STAC_AUTH_TYPE
         envValue: $(inputs.unity_stac_auth)
      -  envName: USERNAME
         envValue: $(inputs.unity_username)
      -  envName: VERIFY_SSL
         envValue: $(inputs.unity_ssl)
      -  envName: STAC_JSON
         envValue: "${\n console.log(typeof inputs.stac_json);\n if (typeof inputs.stac_json === 'object'){\n    return inputs.stac_json.path;\n\
        \  }\n  else{\n    return inputs.stac_json;\n  }\n}\n"
