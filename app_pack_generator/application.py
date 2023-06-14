import os
import copy
import json
import logging

import yaml
import papermill
import jsonschema
from tabulate import tabulate

logger = logging.getLogger(__name__)

"""
Loads the .ipynb jsonschema for validation purposes (TBD).
"""
LOCAL_PATH = os.path.dirname(os.path.realpath(__file__))
SCHEMA_LIST = [os.path.join(LOCAL_PATH,
                            'schemas/nbformat.v4.{v}.schema.json'.format(v=i)) for i in range(0, 6)]
INPUT_TAG = 'parameters'
OUTPUT_TAG = 'outputFiles'


def write_cwl_file(fname, target):
    """Writes [target] dictionary to a .cwl file with filename [fname]."""

    with open(fname, 'w', encoding='utf-8') as f:
        f.write("#!/usr/bin/env cwl-runner\n")
        yaml.dump(target, f, default_flow_style=False)

class ApplicationParameter(object):
    def __init__(self, papermill_info):

        self.papermill_info = papermill_info

    @property
    def name(self):
        return self.papermill_info['name']

    @property
    def inferred_type(self):

        if self.papermill_info['inferred_type_name'] != 'None':
            return self.papermill_info['inferred_type_name']
        elif len(self.papermill_info['help']) > 0:
            return self.papermill_info['help'] 
        else:
            return type(self.default).__name__

    @property
    def default(self):
        return eval(self.papermill_info['default'])

    @property
    def cwl_type(self):
        """Attempts to convert the inferred type to an equivalent CWL type.

        Otherwise, checks if a given key's default value is a string or can be converted to a float."""

        inferred_type = self.inferred_type

        # Use papermill version of default since we will massage default into 
        # a Python type
        default_val = self.papermill_info['default']

        inferred_type = inferred_type.lower()
        convert_dict = {
            'string': ['stage_in', 'stage-in', 'string'],
            'File': ['stage_out', 'stage-out', 'file'],
            'int': ['int', 'integer'],
            'boolean': ['bool', 'boolean'],
            'float': ['float'],
            'double': ['double'],
            'Directory': ['directory'],
            'Any': ['any'],
            'null': ['nonetype'],
        }
        for key in convert_dict:
            if inferred_type in convert_dict[key]:
                return key

        if default_val.find('"') != -1 or default_val.find('\'') != -1:
            return 'string'
        key_type = 'Any'
        try:
            temp = float(default_val)
            key_type = 'float'
        except ValueError:
            pass
        return key_type

class ApplicationError(Exception):
    pass

class ApplicationNotebook:
    """Defines a parsed Jupyter Notebook read as a JSON file."""

    def __init__(self, repo, proc=None, templatedir=os.path.join(LOCAL_PATH, 'templates')):

        self.repo = repo

        # Parsed notebook
        self.notebook = {}

        # All parameters parsed from the notebook
        self.parameters = []

        # Parameters labeled for supplying the stage in/stage out STAC catalog file names
        # The stage in catalog file is written by the stage in step
        # The stage out catalog file is written by the application
        self.stage_in_param = None
        self.stage_out_param = None

        # Free arguments that are papermill parameters not associated with stage
        self.arguments = []

        # Template CWL and descriptor files
        self.workflow_cwl = self._read_yaml_template( os.path.join(templatedir, 'workflow.cwl'))
        self.stage_in_cwl = self._read_yaml_template( os.path.join(templatedir, 'stage_in.cwl'))
        self.process_cwl = self._read_yaml_template( os.path.join(templatedir, 'process.cwl'))
        self.stage_out_cwl = self._read_yaml_template( os.path.join(templatedir, 'stage_out.cwl'))

        self.descriptor = self._read_json_template(os.path.join(templatedir, 'app_desc.json'))

        # TODO - Need more rigorous checks here...
        self.process = proc if proc is not None and os.path.exists(proc) else 'process.ipynb'
        if self.process.endswith('.ipynb'):
            self.parse_notebook(self.process)
        elif not self.process.endswith('.sh'):
            raise ApplicationError('Unsupported file format submitted for entrypoint.')
        else:
            logger.debug(f'Using .sh file with name "{self.process}" as executable process')

    def _read_yaml_template(self, app_cwl_fname):
        """Loads the template application CWL."""
        with open(app_cwl_fname, 'r') as f:
            return yaml.safe_load(f)

    def _read_json_template(self, desc_fname):
        """Loads the template application descriptor and should validate it to
        ensure an exception is not thrown.
        """
        with open(desc_fname, 'r') as f:
            return json.load(f)

    def parse_notebook(self, nb_name='process.ipynb'):
        """Deduces the application notebook within the repository using nb_fname as a hint.

        Should validate nb_fname as a valid, existing Jupyter Notebook to
        ensure no exception is thrown.
        """
        nb_fname = os.path.join(self.repo.directory, nb_name)
        if not os.path.exists(nb_fname):
            raise ApplicationError(f'No file named {nb_name} was detected in the directory \'{self.repo.directory}\'. Now aborting...')

        logger.debug(f'Reading notebook: "{nb_fname}"')
        with open(nb_fname, 'r') as f:
            self.notebook = json.load(f)

        # Validate the notebook using the list of supported v4.X schemas.
        logger.debug(f'Validating {nb_name} as a valid v4.0 - v4.5 Jupyter notebook')
        validation_success = False
        for fname in SCHEMA_LIST:
            if os.path.exists(fname):
                try:
                    with open(fname, 'r') as f:
                        schema = json.load(f)
                        jsonschema.validate(
                            instance=self.notebook, schema=schema)
                        logger.debug(f'Successfully validated using "{os.path.basename(fname)}"')
                        validation_success = True
                        break
                except (jsonschema.exceptions.ValidationError, jsonschema.exceptions.SchemaError) as e:
                    logger.error(f'Failed validation using "{os.path.basename(fname)}"')
                    continue
            else:
                logger.error(f'Validation file "{fname}" does not exist.')

        if not validation_success:
            raise ApplicationError(f'Failed to validate "{nb_fname}" as a v4.0 - v4.5 Jupyter Notebook...')

        # Inspect notebook parameters using papermill and parse them into a list.
        self.parameters = []
        for papermill_param in papermill.inspect_notebook(nb_fname).values():
            app_param = ApplicationParameter(papermill_param)
            self.parameters.append(app_param)

            inferred_type = app_param.inferred_type

            if inferred_type in ['stage-in', 'stage_in']:
                if self.stage_in_param is None:
                    self.stage_in_param = app_param
                else:
                    raise ApplicationError(f"Only one stage-in parameter allowed per notebook")

            elif inferred_type in ['stage-out', 'stage_out']:
                if self.stage_out_param is None:
                    self.stage_out_param = app_param
                else:
                    raise ApplicationError(f"Only one stage-out parameter allowed per notebook")
            else:
                self.arguments.append(app_param)

    def parameter_summary(self):

        headers = [ 'name', 'inferred_type', 'cwl_type', 'default' ]

        # Build up rows of the table using the header values as the columns
        table_data = []
        for app_param in self.parameters:
            table_row = []
            for column_name in headers:
                table_row.append(getattr(app_param, column_name))
            table_data.append(table_row)

        return tabulate(table_data, headers=headers)

    def generate_all(self, outdir, dockerurl="undefined"):
        """Calls all of the application CWL generators as well as the application descriptor generator.

        Returns the list of all files generated by this function (abs. path).
        """

        generated_files = []
        generated_files.append(self.generate_workflow_cwl(outdir))
        generated_files.append(self.generate_stage_in_cwl(outdir))
        generated_files.append(self.generate_process_cwl(outdir, dockerurl))
        generated_files.append(self.generate_stage_out_cwl(outdir=outdir))
        generated_files.append(self.generate_descriptor(outdir, dockerurl))

        return generated_files

    def generate_workflow_cwl(self, outdir):
        """Generates the workflow CWL.

        Returns the absolute path of the file generated by this function.
        """
        self.workflow_cwl['outputs'] = {}

        # Preocess step section of of workflow
        process_dict = self.workflow_cwl['steps']['process']

        # Add non stage-in/stage-out inputs to the master CWL input/outputs as parameters
        args_input_dict = self.workflow_cwl['inputs']['parameters']['type']['fields']
        for param in self.arguments:
            name = param.name

            # Add argument parameter to workflow input, allow null values so that default parameters 
            # from the notebook can be used
            args_input_dict[name] = [ 'null', param.cwl_type ]

            # Connect process step to input argument with the default coming from the notebook's value
            process_dict['in'][name] = {
                'source': 'parameters',
                'valueFrom': f'$(self.{name})',
            }

        # Connect the stage-in parameter to stage_in's catalog filename output
        # Otherwise remove stage in from the workflow
        if self.stage_in_param is not None:
            name = self.stage_in_param.name
            process_dict['in'][name] = 'stage_in/stage_in_catalog_file'
            process_dict['in']['download_dir'] = 'stage_in/stage_in_download_dir'
        else:
            # No stage-in connected to notebook, delete
            del self.workflow_cwl['steps']['stage_in']
            del self.workflow_cwl['inputs']['stage_in']

        # Remove stage-out if not defined in the notebook
        # The connection of the parameter given to the notebook is done inside the process.cwl
        if self.stage_out_param is None:
            del self.workflow_cwl['steps']['stage_out']
            del self.workflow_cwl['inputs']['stage_out']
            self.workflow_cwl['steps']['process']['out'].remove('process_catalog_file')

        fname = os.path.join(outdir, 'workflow.cwl')
        write_cwl_file(fname, self.workflow_cwl)
        return fname

    def generate_stage_in_cwl(self, outdir):
        """Generates the stage-in CWL.

        Returns the absolute path of the file generated by this function.
        """
        if not os.path.isdir(outdir):
            os.makedirs(outdir)

        # Generate the stage-in CWL as is, no need for modification
        fname = os.path.join(outdir, 'stage_in.cwl')
        write_cwl_file(fname, self.stage_in_cwl)
        return fname

    def generate_process_cwl(self, outdir, dockerurl):
        """Generates the application CWL.

        Returns the absolute path of the file generated by this function.
        """
        if not os.path.isdir(outdir):
            os.makedirs(outdir)

        if self.process.endswith('.sh'):
            self.process_cwl['baseCommand'] = [
                'sh', self.process, '/tmp/inputs.json']

        # Set correct URL for process Docker container
        self.process_cwl['requirements']['DockerRequirement']['dockerPull'] = dockerurl

        # Forward the ordinary argument parameters to the process step directly
        input_dict = self.process_cwl['inputs']
        for param in self.arguments:
            name = param.name

            input_dict[name] = {
                'type': param.cwl_type,
                'default': param.default,
            }

        # Append the stage-in file to the input list with type File for explicit
        # forwarding from another container
        if self.stage_in_param is not None:
            name = self.stage_in_param.name
            input_dict[name] = 'File'

            input_dict['download_dir'] = 'Directory'

        # Connect the stage-out parameter to the name of the file specified in the template as output
        if self.stage_out_param is not None:
            name = self.stage_out_param.name
            input_dict[name] = {
                'type': 'string',
                'default': self.process_cwl['outputs']['process_catalog_file']['outputBinding']['glob'],
            }
        else:
            del self.process_cwl['outputs']['process_catalog_file']

        fname = os.path.join(outdir, 'process.cwl')
        write_cwl_file(fname, self.process_cwl)
        return fname

    def generate_stage_out_cwl(self, outdir):
        """Generates the stage-in CWL.

        Returns the absolute path of the file generated by this function.
        """
        if not os.path.isdir(outdir):
            os.makedirs(outdir)

        # Generate the outputs CWL as-is, no need for modifications
        fname = os.path.join(outdir, 'stage_out.cwl')
        write_cwl_file(fname, self.stage_out_cwl)
        return fname

    def generate_descriptor(self, outdir, dockerurl):
        """Generates the application descriptor JSON.

        Returns the absolute  path of the file generated by this function.
        """
        if not os.path.isdir(outdir):
            os.makedirs(outdir)
        deposit_url = 'https://raw.githubusercontent.com/jplzhan/artifact-deposit-repo'
        tag = self.repo.name
        proc_dict = self.descriptor['processDescription']['process']

        if self.repo.owner is not None:
            proc_dict['id'] = self.repo.owner + '.' + \
                self.repo.name + '.' + self.repo.commit_identifier
        else:
            proc_dict['id'] = self.repo.name + '.' + self.repo.commit_identifier
 
        proc_dict['title'] = self.repo.commit_message
        proc_dict['owsContext']['offering']['content']['href'] = deposit_url + \
            '/main/' + tag + '/workflow.cwl'

        proc_dict['inputs'] = []
        for param in self.arguments:
            key_type = param.cwl_type
            proc_dict['inputs'].append({
                'id': param.name, 
                'title': 'Automatically detected using papermill.',
                'literalDataDomains': [{'dataType': {'name': key_type}}],
            })

        if self.stage_in_param is not None:
            proc_dict['inputs'].append({
                'id': self.stage_in_param.name,
                'title': 'Stage-in input specified for URL-to-PATH conversion.',
                'literalDataDomains': [{'dataType': {'name': 'stage_in'}}],
            })

        proc_dict['outputs'] = []
        if self.stage_out_param is not None:
            proc_dict['outputs'].append({
                'id': self.stage_out_param.name,
                'title': 'Automatically detected from .ipynb parsing.',
                'output': {
                    'formats': [
                        {'mimeType': 'text/*', 'default': True}
                    ]
                }
            })

        self.descriptor['executionUnit'][0]['href'] = 'docker://' + dockerurl

        fname = os.path.join(outdir, 'applicationDescriptor.json')
        with open(fname, 'w', encoding='utf-8') as f:
            json.dump(self.descriptor, f, ensure_ascii=False, indent=4)
        return fname
