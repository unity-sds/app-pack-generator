cwlVersion: v1.2
class: CommandLineTool

baseCommand: ["DOWNLOAD"]

requirements:
  DockerRequirement:
    dockerPull: ghcr.io/unity-sds/unity-data-services:5.3.1
  EnvVarRequirement:
    envDef:
      DOWNLOAD_DIR: $(runtime.outdir)
      DOWNLOADING_KEYS: $(inputs.downloading_keys) 
      STAC_JSON: $(inputs.stac_json.path)
      GRANULES_DOWNLOAD_TYPE: $(inputs.download_type)
      EDL_BASE_URL: 'https://urs.earthdata.nasa.gov/'
      EDL_USERNAME: $(inputs.edl_username)
      EDL_PASSWORD: $(inputs.edl_password)
      EDL_PASSWORD_TYPE: $(inputs.edl_password_type)
      OUTPUT_FILE: $(runtime.outdir)/stage-in-results.json
      LOG_LEVEL: '20'
      PARALLEL_COUNT: '-1'
      DOWNLOAD_RETRY_WAIT_TIME: '30'
      DOWNLOAD_RETRY_TIMES: '5'

inputs:
  download_type:
    type: string
  stac_json:
    type: File
  edl_username:
    type: string
  edl_password:
    type: string
  edl_password_type:
    type: string
    default: "BASE64"
  downloading_keys:
    type: string
    default: "data, metadata"

outputs:
  stage_in_collection_file:
    type: File
    outputBinding:
      glob: stage-in-results.json
  stage_in_download_dir:
    type: Directory
    outputBinding:
      glob: .
