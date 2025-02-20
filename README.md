<!-- Header block for project -->
<hr>

<div align="center">

![logo](https://user-images.githubusercontent.com/3129134/163255685-857aa780-880f-4c09-b08c-4b53bf4af54d.png)

<h1 align="center">OGC Application Package Generator</h1>

</div>

<pre align="center">This repository contains a library for the generation an OGC complaint application package from a Jupyter Notebook by parsing its contents and metadata. </pre>

<!-- Header block for project -->

This library serves as a base upon which to build project specific application generation software. For example the [Unity Project](https://github.com/unity-sds/) uses this libary for their [Unity specific application genetation software](https://github.com/unity-sds/unity-app-generator). 

[unity-app-generator](https://github.com/unity-sds/unity-app-generator) |  [unity-example-application](https://github.com/unity-sds/unity-example-application)

## Features

- Extracts information from application Git repositorties for metadata reporting
- Creates an algorithm descriptor file that can be used by an OGC compliant ADES server
- Creates Common Workflow Language (CWL) files that expose the notebook's arguments
- Creates a Docker image called by the CWL file to execute parsed notebook applications

## Install from PyPi

```
pip install app-pack-generator
```

## Preparing Your repository

Any application repository used by this library must:

1. Contain an valid Jupyter notebook which can be run using [papermill](https://papermill.readthedocs.io/en/latest/)
3. Contain a [valid configuration file](https://repo2docker.readthedocs.io/en/latest/config_files.html) for `repo2docker` (generally an `environment.yml` or `requirements.txt`)

**NOTE:** `papermill` is required to listed as a dependencies in your configuration file.

By default `repo2docker` will a certain version of Python, currently Python 3.8. Be sure to provied a `runtime.txt` [configuration file](https://repo2docker.readthedocs.io/en/latest/config_files.html#runtime-txt-specifying-runtimes) to specify a different version if your packages require it.

## Preparing Your Notebook

In your Jupyter notebook file, the input parameters will be automatically determined from a code cell in the notebook annotated with the `parameters` tag. An attempt is made to automatically detect the type of the parameters. When that fails, type can be specified through a type hint in the form of a comment following the variable in the form `# type: <type_name>`. See below for examples:

```py
example_argument_int = 1
example_argument_float = 1.0
example_argument_string = "string"
example_argument_bool = True
example_argument_empty = None # type: string Allow a null value or a string
```

Not that a comment can still be provided but it must be given after the type name. If a value is specified with the None it will be come an `Any` type inside of the generated CWL unless a type hint is provided. Parameters like the above are passed to the generated CWL through a parameters block in the CWL job input file. For example, the following YAML would be part of the job input file for the above parameters:

```yaml
parameters:
    example_argument_string: "string"
    example_argument_int: 1
    example_argument_float: 1.0
    example_argument_empty: "Not null string"
    example_argument_bool: True
```

If any of the values in the CWL job input file are given as `null` then the default value inside the notebook will be used.

Two special type hints are used to connect inputs and outputs into the generated CWL file from the ADES processing system. These hints are given by the `stage-in` and `stage-out` type hints:

```py
input_stac_collection_file = 'test/stage_in/stage_in_results.json' # type: stage-in
output_stac_catalog_dir    = 'process_results/'                    # type: stage-out
```

The ``stage-in`` variable will be passed a **filename** to either a STAC [Collection file](https://github.com/radiantearth/stac-spec/blob/master/collection-spec/README.md) or a [STAC Catalog file](https://github.com/radiantearth/stac-spec/blob/master/catalog-spec/catalog-spec.md). The data staged for the application will be located in the same directory as the file. It is recommended to use the [Unity-Py](https://pypi.org/project/unity-sds-client/) ``Collection.from_stac`` method as illustrated in the [unity-example-application](https://github.com/unity-sds/unity-example-application). This method will automatically detect the type of file being passed and handle them both seemlessly.

The ``stage-out`` variable will be passed **path** to the location where a [STAC Catalog file](https://github.com/radiantearth/stac-spec/blob/master/catalog-spec/catalog-spec.md) should be written along with any output data. Application results must be located in this directory for them to be properly staged. Again, please follow the example in the [unity-example-application](https://github.com/unity-sds/unity-example-application) archive for using [Unity-Py](https://pypi.org/project/unity-sds-client/) to write such a catalog.

If either or both ``stage-in`` and ``stage-out`` variables are omitted from the notebook then the related CWL file will not be produced.

## License

See our: [LICENSE](LICENSE)
