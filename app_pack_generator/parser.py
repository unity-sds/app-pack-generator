import os
import copy
import yaml

import json
import papermill
import jsonschema

from .util import Util

"""
Loads the .ipynb jsonschema for validation purposes (TBD).
"""
LOCAL_PATH = os.path.dirname(os.path.realpath(__file__))
SCHEMA_LIST = [os.path.join(LOCAL_PATH,
                            'schemas/nbformat.v4.{v}.schema.json'.format(v=i)) for i in range(0, 6)]
INPUT_TAG = 'parameters'
OUTPUT_TAG = 'outputFiles'

class AppNB:
    """Defines a parsed Jupyter Notebook read as a JSON file."""

    def __init__(self, repo, proc=None, templatedir=os.path.join(LOCAL_PATH, 'templates')):
        self.notebook = {}
        self.stage_in = []
        self.parameters = {}
        self.inputs = []
        self.outputs = []
        self.repo = repo
        self.descriptor = {}
        self.appcwl = {}
        self.workflow_cwl = self.ParseAppCWL(
            os.path.join(templatedir, 'workflow.cwl'))
        self.stage_in_cwl = self.ParseAppCWL(
            os.path.join(templatedir, 'stage_in.cwl'))
        self.appcwl = self.ParseAppCWL(
            os.path.join(templatedir, 'process.cwl'))
        self.stage_out_cwl = self.ParseAppCWL(
            os.path.join(templatedir, 'stage_out.cwl'))

        self.ParseDescriptor(os.path.join(templatedir, 'app_desc.json'))

        # Define the stage-in inputs fields schema and pop its input bindings.
        self.cache_workflow_cwl = None
        self.stage_in_input_type = copy.deepcopy(
            self.stage_in_cwl['inputs']['input_path']['type'])
        for record in self.stage_in_input_type:
            record.pop('inputBinding')

        # TODO - Need more rigorous checks here...
        self.process = proc if proc is not None and os.path.exists(proc) else 'process.ipynb'
        if self.process.endswith('.ipynb'):
            self.ParseNotebook(self.process)
        elif not self.process.endswith('.sh'):
            msg = 'Unsupported file format submitted for entrypoint.'
            raise RuntimeError(msg)
        else:
            print('Using .sh file with name \'' +
                  self.process + '\' as executable process...')

    def ParseAppCWL(self, app_cwl_fname):
        """Loads the template application CWL."""
        with open(app_cwl_fname, 'r') as f:
            return yaml.safe_load(f)

    def ParseDescriptor(self, desc_fname):
        """Loads the template application descriptor and should validate it to
        ensure an exception is not thrown.
        """
        with open(desc_fname, 'r') as f:
            self.descriptor = json.load(f)

    def ParseNotebook(self, nb_name='process.ipynb'):
        """Deduces the application notebook within the repository using nb_fname as a hint.

        Should validate nb_fname as a valid, existing Jupyter Notebook to
        ensure no exception is thrown.
        """
        nb_fname = os.path.join(self.repo.directory, nb_name)
        if not os.path.exists(nb_fname):
            msg = f'No file named {nb_name} was detected in the directory \'{self.repo.directory}\'. Now aborting...'
            raise RuntimeError(msg)

        print('Opening', nb_fname + '...')
        with open(nb_fname, 'r') as f:
            self.notebook = json.load(f)

        # Validate the notebook using the list of supported v4.X schemas.
        print('Validating \'' + nb_name +
              '\' as a valid v4.0 - v4.5 Jupyter notebook...')
        validation_success = False
        for fname in SCHEMA_LIST:
            if os.path.exists(fname):
                try:
                    with open(fname, 'r') as f:
                        schema = json.load(f)
                        jsonschema.validate(
                            instance=self.notebook, schema=schema)
                        print('Successfully validated \'' +
                              nb_fname + '\' using ' + fname + '.')
                        validation_success = True
                        break
                except (jsonschema.exceptions.ValidationError, jsonschema.exceptions.SchemaError) as e:
                    print(fname + ' failed...')
                    continue
            else:
                print(fname + ' does not exist.')
        if not validation_success:
            msg = 'Failed to validate \'' + nb_fname + \
                '\' as a v4.0 - v4.5 Jupyter Notebook...'
            raise RuntimeError(msg)

        # Inspect notebook parameters using papermill and parse them into a list.
        self.parameters = papermill.inspect_notebook(nb_fname)
        print(self.parameters)

        for key in list(self.parameters.keys()):
            param = self.parameters[key]
            inferred_type = param['inferred_type_name'] if param['inferred_type_name'] != 'None' else param['help']
            if inferred_type in ['stage-in', 'stage_in']:
                self.stage_in.append(key)
            elif inferred_type in ['stage-out', 'stage_out']:
                self.outputs.append(key)
            else:
                self.inputs.append(key)

    def Generate(self, outdir=os.path.join(os.getcwd(), '.generated/'), dockerurl="undefined"):
        """Calls all of the Application Notebook generators.

        Returns the list of all files generated by this function (abs. path).
        """

        generated_files = []
        generated_files.append(self.GenerateWorkflowCWL(outdir=outdir))
        generated_files.append(self.GenerateCacheCWL(outdir=outdir))
        generated_files.append(self.GenerateStageInCWL(outdir=outdir))
        generated_files.append(self.GenerateAppCWL(dockerurl, outdir=outdir))
        generated_files.append(self.GenerateStageOutCWL(outdir=outdir))
        generated_files.append(
            self.GenerateDescriptor(dockerurl, outdir=outdir))

        return generated_files

    def GenerateWorkflowCWL(self, outdir=os.path.join(os.getcwd(), '.generated/')):
        """Generates the workflow CWL.

        Returns the absolute path of the file generated by this function.
        """
        self.workflow_cwl['outputs'] = {}

        # Fill out the inputs field for running the workflow CWL, make updates to the template
        input_dict = self.workflow_cwl['inputs']['parameters']['type']['fields']
        for key in self.inputs:
            if key not in input_dict and not key in self.workflow_cwl['inputs']:
                param = self.parameters[key]
                inferred_type = param['inferred_type_name'] if param['inferred_type_name'] != 'None' else param['help']
                input_dict[key] = Util.GetKeyType(
                    inferred_type, param['default'])
            else:
                print(
                    f"Warning: {key} defined in notebook but already present in template, not overwriting workflow template definition")

        # Create a new stage-in step at the workflow level for every stage-in input
        self.workflow_cwl['steps'] = {}
        steps_dict = self.workflow_cwl['steps']
        prev_step = None
        for key in self.stage_in:
            step_name = 'stage_in_' + key
            steps_dict[step_name] = {
                'run': 'stage_in.cwl',
                'in': {
                    'cache_dir': 'cache_dir' if prev_step is None else '{}/cache_out'.format(prev_step),
                    'cache_only': 'cache_only',
                    'input_path': {
                        'source': 'parameters',
                        'valueFrom': '$(self.{})'.format(key),
                    },
                },
                'out': ['cache_out', 'output_files'],
            }
            # Splice in the type fields for stage-in parameters.
            input_dict[key] = {
                'type': self.stage_in_input_type,
            }
            # Daisy chain stage-in steps so that caching will actually work
            prev_step = step_name

        # Create the process step at the workflow level
        process_dict = {
            'run': 'process.cwl',

            'in': {},
            'out': ['output_nb', 'output_dir'],
        }
        for key in self.stage_in:
            process_dict['in'][key] = 'stage_in_' + key + '/output_files'
        for key in self.inputs:
            if key in input_dict:
                process_dict['in'][key] = {
                    'source': 'parameters',
                    'valueFrom': '$(self.{})'.format(key),
                }
            else:
                process_dict['in'][key] = key

        for key in self.outputs:
            process_dict['out'].append(key)
        steps_dict['process'] = process_dict

        # Create the stage-out step at the workflow level for eveyr stage-out output
        steps_dict['stage_out'] = {
            'run': 'stage_out.cwl',
            'in': {
                'output_path': 'stage_out',
                'output_nb': 'process/output_nb',
                'output_dir': 'process/output_dir',
            },
            'out': [],
        }
        output_dict = steps_dict['stage_out']
        for key in self.outputs:
            output_dict['in'][key] = 'process/' + key

        # Duplicate the parsed workflow
        self.cache_workflow_cwl = copy.deepcopy(self.workflow_cwl)

        fname = os.path.join(outdir, 'workflow.cwl')
        Util.WriteYMLFile(fname, self.workflow_cwl)
        return fname

    def GenerateCacheCWL(self, outdir=os.path.join(os.getcwd(), '.generated/')):
        """Generates the caching CWL.

        Returns the absolute path of the file generated by this function.
        """
        if not os.path.isdir(outdir):
            os.makedirs(outdir)

        if not isinstance(self.cache_workflow_cwl, dict):
            raise Exception(
                'AppNB.GenerateCacheCWL must be called after AppNB.GenerateWorkflowCWL.')

        # This is caching workflow is a subset of the workflow CWL, pop extraneous elements
        self.cache_workflow_cwl['steps'].pop('process')
        self.cache_workflow_cwl['steps'].pop('stage_out')
        self.cache_workflow_cwl['inputs'].pop('stage_out')
        self.cache_workflow_cwl['inputs']['cache_only']['default'] = True
        for key in self.inputs:
            if key in self.cache_workflow_cwl['inputs']['parameters']['type']['fields']:
                self.cache_workflow_cwl['inputs']['parameters']['type']['fields'].pop(
                    key)

        # Generate the stage-in CWL as is, no need for modification
        fname = os.path.join(outdir, 'cache_workflow.cwl')
        Util.WriteYMLFile(fname, self.cache_workflow_cwl)
        return fname

    def GenerateStageInCWL(self, outdir=os.path.join(os.getcwd(), '.generated/')):
        """Generates the stage-in CWL.

        Returns the absolute path of the file generated by this function.
        """
        if not os.path.isdir(outdir):
            os.makedirs(outdir)

        # Generate the stage-in CWL as is, no need for modification
        fname = os.path.join(outdir, 'stage_in.cwl')
        Util.WriteYMLFile(fname, self.stage_in_cwl)
        return fname

    def GenerateAppCWL(self, dockerurl, outdir=os.path.join(os.getcwd(), '.generated/')):
        """Generates the application CWL.

        Returns the absolute path of the file generated by this function.
        """
        if not os.path.isdir(outdir):
            os.makedirs(outdir)

        if self.process.endswith('.sh'):
            self.appcwl['baseCommand'] = [
                'sh', self.process, '/tmp/inputs.json']

        # Set correct URL for process Docker container
        self.appcwl['requirements']['DockerRequirement']['dockerPull'] = dockerurl

        # Forward the ordinary parameters to the process step directly
        input_dict = self.appcwl['inputs']
        for key in self.inputs:
            if key not in input_dict:
                param = self.parameters[key]
                inferred_type = param['inferred_type_name'] if param['inferred_type_name'] != 'None' else param['help']
                input_dict[key] = Util.GetKeyType(
                    inferred_type, param['default'])
            else:
                print(
                    f"Warning: {key} defined in notebook but already present in template, not overwriting process template definition")

        # Append the stage-in files to the input list with type File[] for explicit
        # forwarding from another container. Enable them to be modified in-place.
        for key in self.stage_in:
            input_dict[key] = 'File[]'

        # Add defined stage-out parameters
        # TODO - Is this necessary?
        output_dict = self.appcwl['outputs']
        for key in self.outputs:
            output_dict[key] = {
                'type': 'File',
                'outputBinding': {'glob': self.parameters[key]['default']},
            }

        fname = os.path.join(outdir, 'process.cwl')
        Util.WriteYMLFile(fname, self.appcwl)
        return fname

    def GenerateStageOutCWL(self, outdir=os.path.join(os.getcwd(), '.generated/')):
        """Generates the stage-in CWL.

        Returns the absolute path of the file generated by this function.
        """
        if not os.path.isdir(outdir):
            os.makedirs(outdir)

        # Generate the outputs CWL as-is, no need for modifications
        fname = os.path.join(outdir, 'stage_out.cwl')
        Util.WriteYMLFile(fname, self.stage_out_cwl)
        return fname

    def GenerateDescriptor(self, dockerurl, outdir=os.path.join(os.getcwd(), '.generated/')):
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
                self.repo.name + '.' + self.repo.checkout
        else:
            proc_dict['id'] = self.repo.name + '.' + self.repo.checkout
 
        proc_dict['title'] = GitHelper.Message(self.repo.directory).strip()
        proc_dict['owsContext']['offering']['content']['href'] = deposit_url + \
            '/main/' + tag + '/workflow.cwl'

        proc_dict['inputs'] = []
        for key in self.inputs:
            param = self.parameters[key]
            inferred_type = param['inferred_type_name'] if param['inferred_type_name'] != 'None' else param['help']
            key_type = Util.GetKeyType(inferred_type, param['default'])
            proc_dict['inputs'].append({
                'id': key,
                'title': 'Automatically detected using papermill.',
                'literalDataDomains': [{'dataType': {'name': key_type}}],
            })
        for key in self.stage_in:
            param = self.parameters[key]
            proc_dict['inputs'].append({
                'id': key,
                'title': 'Stage-in input specified for URL-to-PATH conversion.',
                'literalDataDomains': [{'dataType': {'name': 'stage_in'}}],
            })

        proc_dict['outputs'] = []
        for key in self.outputs:
            proc_dict['outputs'].append({
                'id': key,
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
