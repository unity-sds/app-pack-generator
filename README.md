# MAAP Application Package Generator
Generates an application package from a Jupyter Notebook by parsing its contents and metadata.

This repository serves as an endpoint for triggering CI/CD jobs for creating Application Packages for the MAAP project. Whenever a new job is created, this repository will be cloned to a clean folder and then the `build.sh` script will be ran. This script will then run `parser.py`, which will clone the algorithm repository and build an application package from it.

The algorithm descriptor and CWL files are uploaded to https://github.com/jplzhan/artifact-deposit-repo.

The docker images (referenced by the corresponding CWL/JSON files) are uploaded to https://hub.docker.com/repository/docker/jplzhan/ci-generated-images.

## Preparing Your repository
Any submitted algorithm repository must be:

1. Publically cloneable (via its HTTPS .git URL) using the command `git clone <YOUR_URL>`. **You DO NOT have to own this repository to submit a job for it.**
2. Contain an valid executable file (an .sh file with `chmod +x` permissions or a .ipynb file which can be ran using `papermill`, view [this link](https://papermill.readthedocs.io/en/latest/) for more information on `papermill`).
3. Contain a valid configuration file for `repo2docker` (generally an `environment.yml` or `Dockerfile`). Alternatively, this file can be stored elsewhere so long as it is downloadable via a public URL (NOTE: You will have provide this URL in the payload of a POST request if you choose to store this file externally).

**NOTE:** If you are attempting to run an `.ipynb` notebook, `papermill` is required to be one of your dependencies in your configuration file.

If the algorithm repository satisfies all of the listed conditions, a POST request can be submitted to [this URL](https://repo.dit.maap-project.org/api/v4/projects/19/trigger/pipeline) to create a CI/CD job which will build the repository as an algorithm package.

## Preparing Your Notebook

If you are using .ipynb files as your executable, the input parameters will be automatically determined using the `papermill --inspect_notebook <NOTEBOOK_NAME>` command, and correspond to a code cell in the notebook annotated with the `parameters` tag. Numeric parameters are always assumed to be `float` unless a type-hint is provided.

```py
input_1 = 12.5
string_var = 'abcdefg'
integer_var = 86 #type: int
input_file = [{'path': '/path/to/file'}] # type: stage-in
```

By default, the notebook is assumed to be called `process.ipynb` and located at the top of your repository (you can override this by using the `process` property in the payload you submit).

Outputs can be specified in a similar manner by type-hinting parameters (still in the parameters cell) with the `stage_out` (or `stage-out`) type. These variables should be strings and their values will specify their glob pattern:

```py
# Both stage_out and stage-out are parsable types
stdout = 'stdout.txt' # type: stage_out
tempfile = 'temp.txt' # type: stage-out
image = 'image.png' # type: stage-out
wildcard = 'wildcard_*.log' # type: stage_out
```

Similarly, stage-in inputs can be specified using the `stage_in` (or `stage-in`) type hint. These parameters are expected to refer to a relative file path. When deploying the job, they will be submitted as a URL, which will be downloaded by the stage-in script and then injected as a dictionary with the following form into the notebook:

```py
input_file = [{
    "basename": "0_geoBoundaries-GAB-ADM0.geojson",
    "checksum": "sha1$001e7d353bd8143e1315d30ab6aed44139c8f344",
    "class": "File",
    "dirname": "/var/lib/cwl/stg36ad3228-566a-4426-90f7-ed42f53bb4e0",
    "http://commonwl.org/cwltool#generation": 0,
    "location": "file:///data/home/hysdsops/zhan/artifact-deposit-repo/jplzhan/gedi-subset/main/output-nbjb75r8/inputs/0/0_geoBoundaries-GAB-ADM0.geojson",
    "nameext": ".geojson",
    "nameroot": "geoBoundaries-GAB-ADM0",
    "path": "/var/lib/cwl/stg36ad3228-566a-4426-90f7-ed42f53bb4e0/0_geoBoundaries-GAB-ADM0.geojson",
    "size": 51350
}]

print(input_file[0]["path"]) # output: /var/lib/cwl/stg36ad3228-566a-4426-90f7-ed42f53bb4e0/0_geoBoundaries-GAB-ADM0.geojson
```

The `path` varaible contains the absolute file path of the staged-in file. The stage-in variable is a list of descriptors containing these paths. This is to accommodate a dynamic number of stage-in URLs per stage-in input.

## Creating a CI/CD Job
Users can trigger a CI/CD build by sending a POST request to [this URL](https://repo.dit.maap-project.org/api/v4/projects/19/trigger/pipeline), with a payload following this example:
```json
{
    'variables[repository]': 'https://github.com/lauraduncanson/icesat2_boreal.git',
    'variables[checkout]': 'master',
    'variables[process]': 'dps/alg_3-1-5/run.sh',
    'variables[env]': 'https://mas.maap-project.org/root/ade-base-images/-/raw/vanilla/docker/Dockerfile',
    'token': GITLAB_TOKEN,
    'ref': 'main',
}
```

Refer to `query.py` (https://repo.dit.maap-project.org/max.zhan/app-pack-generator/-/blob/main/query.py) for an example of how to use Python to send this payload. You can also use cURL to send this POST request.

You can use the following [JSON schema](https://json-schema.org/) to validate your payload (refer to the property descriptions for the meaning/usage of each parameter):
```json
{
    "type": "object",
    "properties": {
        "variables[repository]": {
            "type": "string",
            "description": "The link the CI/CD script will use to clone the algorithm repository.
                Must be publically cloneable (do not use the SSH link).
                Equivalent to running 'git clone <variables[repository]>'.
                This parameter is required.",
        },
        "variables[checkout]": {
            "type": "string",
            "description": "After cloning the algorithm repository, the script will run 'git checkout <variables[checkout]>'.
                This can be either a commit hash, a branch name, or a tag name.
                This field will be used as part of the naming scheme for the resulting docker image.
                Because of this, capital letters and some special characters are forbidden in this name.
                Valid characters include lowercase letters, numbers, and the '-' character.
                This parameter is required.",
        },
        "variables[process]": {
            "type": "string",
            "description": "This must be a relative path (from the top of the algorithm repository)
                to the file that will be ran when the algorithm package is deployed.
                Must be either a shell script (.sh file), or a Jupyter notebook (.ipynb file).
                This parameter is optional.",
        },
        "variables[env]": {
            "type": "string",
            "description": "This must either be a relative path (from the top of the algorithm repository),
                or a URL to a downloadable file. The file this parameter points to must be a valid configuration
                file for building a docker image using repo2docker. Generally, this would be either a Dockerfile,
                or an environment.yml file. For further details, visit the https://repo2docker.readthedocs.io/.
                This parameter is optional.",
        },
        "token": {
            "type": "string",
            "description": "Secret authentication token. Contact Max Zhan to receive it. This parameter is required.",
        },
        "ref": {
            "type": "string",
            "enum": ["main"],
            "description": "Boilerplate parameter. Specifies the branch of the parsing script to run.
                Just set this parameter to 'main'. This parameter is required.",
        }
    },
    "required": [
        "variables[repository]",
        "variables[checkout]",
        "token",
        "ref",
    ],
}
```

**NOTE:** As this schema has yet to be used, please keep in mind that you may need to fix minor syntax errors with this schema if you were to directly copy and paste it into a Python script.

## Checking Your CI/CD Job

Upon successfully creating your job via a POST request, you should receive a payload similar to this:

```json
{
  "id": 522,
  "iid": 62,
  "project_id": 19,
  "sha": "e64715eeb0c12f5456c016593329d3a9e6b09c0e",
  "ref": "main",
  "status": "created",
  "source": "trigger",
  "created_at": "2022-05-31T23:20:55.828Z",
  "updated_at": "2022-05-31T23:20:55.828Z",
  "web_url": "https://repo.dit.maap-project.org/max.zhan/app-pack-generator/-/pipelines/522",
  "before_sha": "0000000000000000000000000000000000000000",
  "tag": false,
  "yaml_errors": null,
  "user": {
    "id": 40,
    "username": "max.zhan",
    "name": "Max Zhan",
    "state": "active",
    "avatar_url": "https://secure.gravatar.com/avatar/5b95f035b424013dcb70653234289eb2?s=80&d=identicon",
    "web_url": "https://repo.dit.maap-project.org/max.zhan"
  },
  "started_at": null,
  "finished_at": null,
  "committed_at": null,
  "duration": null,
  "queued_duration": null,
  "coverage": null,
  "detailed_status": {
    "icon": "status_created",
    "text": "created",
    "label": "created",
    "group": "created",
    "tooltip": "created",
    "has_details": true,
    "details_path": "/max.zhan/app-pack-generator/-/pipelines/522",
    "illustration": null,
    "favicon": "/assets/ci_favicons/favicon_status_created-4b975aa976d24e5a3ea7cd9a5713e6ce2cd9afd08b910415e96675de35f64955.png"
  }
}
```

**Use the `web_url` field to get the link to the associated job.** This link will contain the build log for your particular job and will report whether it is ongoing, canceled, succeded, or failed.

To see the list of all ongoing/completed jobs, visit https://repo.dit.maap-project.org/max.zhan/app-pack-generator/-/pipelineshttps://repo.dit.maap-project.org/max.zhan/app-pack-generator/-/pipelines.

You can also check the status of your job programatically by submitting a GET request to https://repo.dit.maap-project.org/api/v4/projects/19/jobs. This will require a **different token** from the one used to create CI/CD job, and is **submitted via the header instead of the payload (under the `PRIVATE-TOKEN` field as a string)**. Once again, see `query.py` for an example on how to send this GET request via Python.

The payload to this GET request can be vaidated with the following schema:
```json
{
    "type": "object",
    "properties": {
        "scope": {
            "type": "array",
            "items":{
                "type": "string",
                "enum": [
                    "created",
                    "pending",
                    "running",
                    "failed",
                    "success",
                    "canceled",
                    "skipped",
                    "manual"
                ],
            },
            "description": "Filters the list of jobs for only jobs which satisfy at least one of the specified
                fields. If this parameter is not provided, all jobs are returned in the payload instead.",
        },
    },
}
```

**NOTE:** As this schema has yet to be used, please keep in mind that you may need to fix minor syntax errors with this schema if you were to directly copy and paste it into a Python script.
