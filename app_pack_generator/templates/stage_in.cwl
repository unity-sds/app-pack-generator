cwlVersion: v1.2
class: CommandLineTool

baseCommand: ["DOWNLOAD"]

requirements:
  DockerRequirement:
    dockerPull: ghcr.io/unity-sds/unity-data-services:3.8.1
  EnvVarRequirement:
    envDef:
      DOWNLOAD_DIR: $(runtime.outdir)/download_dir
      STAC_JSON: $(inputs.stac_json.path)
      GRANULES_DOWNLOAD_TYPE: $(inputs.download_type)
      EDL_BASE_URL: 'https://urs.earthdata.nasa.gov/'
      EDL_USERNAME: $(inputs.edl_username)
      EDL_PASSWORD: $(inputs.edl_password)
      EDL_PASSWORD_TYPE: 'BASE64'
      LOG_LEVEL: '20'
      OUTPUT_FILE: $(runtime.outdir)/download_dir/stage-in-results.json

inputs:
  download_type:
    type: string
  stac_json:
    type: File
  edl_username:
    type: string
  edl_password:
    type: string

outputs:
  stage_in_catalog_file:
    type: File
    outputBinding:
      glob: download_dir/stage-in-results.json
  stage_in_download_dir:
    type: Directory
    outputBinding:
      glob: download_dir
