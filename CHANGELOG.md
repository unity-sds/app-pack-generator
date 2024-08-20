# Changelog

All notable changes to this project will be documented in this file. 

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1]

### Updated

- Updated UDS docker images for stage-in/out to 7.12.2.

## [0.4.0]

### Updated

- Update to use unity-data-services to 7.10.1.
- Update CWL to incorporate features present in that version that were not previously exposed for override by the job input file.

## [0.3.0]

### Issues Addressed

#11 - Convert app-pack-generator to use PEP 621 package metadata
#12 - Update to use U-DS 5.2.2
#13 - Modify papermill to use jovyan home directory as execution context
#15 - Seperate CWL generation logic from application parsing logic
#16 - Application Package workflows should have the output of stage-out
#17 - Allow for EDL_PASSWORD type at the stage-in to be modified at run time (non hardcoded)
#20 - Update stage-in, stage-out versions and environments to support new STAC metadata requirements
#8 - Update stage-out to use U-DS stage-out version 5.2.1
#4 - Update notebook testing to reflect changes to app-pack-generator update to U-DS 5.2.1

### PRs Merged
* updated uds image to 5.3.1 by @mike-gangl in https://github.com/unity-sds/app-pack-generator/pull/18
* Update stage_in.cwl, stage_out, and workflow.cwl templates for updated STAC interface by @mike-gangl in https://github.com/unity-sds/app-pack-generator/pull/19
* Stage in from hrefs by @mike-gangl in https://github.com/unity-sds/app-pack-generator/pull/21

## [0.2.0] - 2023-07-12

### Added 
- [#1](https://github.com/unity-sds/app-pack-generator/issues/1) - Modify app-pack-generator to use U-DS STAC based stage in and stage out
- [#2](https://github.com/unity-sds/app-pack-generator/issues/2) - Provide example CWL files that call U-DS stage in/out Docker images
- [#3](https://github.com/unity-sds/app-pack-generator/issues/3) - Add missing requirement "giturlparse>=0.10.0" to setup.py file.
- [#4](https://github.com/unity-sds/app-pack-generator/issues/4) - Modify GitHelper to support more use case other than remote URL cloning only, support local repos
- [#5](https://github.com/unity-sds/app-pack-generator/issues/5) - Allow optional arguments in generated CWL files so that they do not need to be supplied in a cwltool call
- [#10](https://github.com/unity-sds/app-pack-generator/issues/10) - Update app-pack-generator README for release

