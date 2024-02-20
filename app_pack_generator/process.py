import os
import re
import json
import yaml
import logging

logger = logging.getLogger(__name__)

LOCAL_PATH = os.path.dirname(os.path.realpath(__file__))

def write_cwl_file(fname, target):
    """Writes [target] dictionary to a .cwl file with filename [fname]."""

    with open(fname, 'w', encoding='utf-8') as f:
        f.write("#!/usr/bin/env cwl-runner\n")
        yaml.dump(target, f, default_flow_style=False)

class ProcessError(Exception):
    pass

class CWL(object):

    def __init__(self, application, templatedir=os.path.join(LOCAL_PATH, 'templates')):

        self.app = application

        # Template CWL and descriptor files
        self.workflow_cwl = self._read_template( os.path.join(templatedir, 'workflow.cwl'))
        self.stage_in_cwl = self._read_template( os.path.join(templatedir, 'stage_in.cwl'))
        self.process_cwl = self._read_template( os.path.join(templatedir, 'process.cwl'))
        self.stage_out_cwl = self._read_template( os.path.join(templatedir, 'stage_out.cwl'))

    def _read_template(self, app_cwl_fname):
        """Loads the template application CWL."""
        with open(app_cwl_fname, 'r') as f:
            return yaml.safe_load(f)

    def generate_all(self, outdir, dockerurl="undefined"):
        """Calls all of the application CWL generators as well as the application descriptor generator.

        Returns the list of all files generated by this function (abs. path).
        """

        generated_files = []
        generated_files.append(self.generate_workflow_cwl(outdir))
        generated_files.append(self.generate_stage_in_cwl(outdir))
        generated_files.append(self.generate_process_cwl(outdir, dockerurl))
        generated_files.append(self.generate_stage_out_cwl(outdir=outdir))

        return generated_files

    def generate_workflow_cwl(self, outdir):
        """Generates the workflow CWL.

        Returns the absolute path of the file generated by this function.
        """

        # Preocess step section of of workflow
        process_dict = self.workflow_cwl['steps']['process']

        # Add non stage-in/stage-out inputs to the master CWL input/outputs as parameters
        args_input_dict = self.workflow_cwl['inputs']['parameters']['type']['fields']
        for param in self.app.arguments:
            name = param.name

            # Add argument parameter to workflow input, allow null values so that default parameters 
            # from the notebook can be used
            args_input_dict[name] = [ 'null', param.cwl_type ]

            # Connect process step to input argument with the default coming from the notebook's value
            process_dict['in'][name] = {
                'source': 'parameters',
                'valueFrom': f'$(self.{name})',
            }

        # Connect the stage-in parameter to stage_in's collection filename output
        # Otherwise remove stage in from the workflow
        if self.app.stage_in_param is not None:
            process_dict['in']['download_dir'] = 'stage_in/stage_in_download_dir'
        else:
            # No stage-in connected to notebook, delete
            del self.workflow_cwl['steps']['stage_in']
            del self.workflow_cwl['inputs']['stage_in']

        # Remove stage-out if not defined in the notebook
        # The connection of the parameter given to the notebook is done inside the process.cwl
        if self.app.stage_out_param is None:
            del self.workflow_cwl['steps']['stage_out']
            del self.workflow_cwl['inputs']['stage_out']
            del self.workflow_cwl['outputs']['stage_out_results']

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

        # Set correct URL for process Docker container
        self.process_cwl['requirements']['DockerRequirement']['dockerPull'] = dockerurl

        # Forward the ordinary argument parameters to the process step directly
        input_dict = self.process_cwl['inputs']
        for param in self.app.arguments:
            name = param.name

            input_dict[name] = {
                'type': param.cwl_type,
                'default': param.default,
            }

        # The download_dir is carried as an input from stage_in to process to
        # make sure that the contents are exposed to the process container
        # If we had the stage_in collection filename be an input argument
        # to process.cwl then it would be volume mounted in a seperate path
        # and we could not assume that the collection file is in the same
        # directory as the downloaded results it refers to
        # Instead we specifically construct the stage in argument to point
        # to the download directory with the filename mentioned in the stage_in
        # CWL file. So if we change the filename name in that template it is reflected here
        # This seems to be the simpilist solution that works other than doing something
        # complicated using secondaryFiles
        if self.app.stage_in_param is not None:
            input_dict['download_dir'] = 'Directory'

            stage_in_collection_filename = self.stage_in_cwl['outputs']['stage_in_collection_file']['outputBinding']['glob']
            self.process_cwl['arguments'] = self.process_cwl.get('arguments', [])
            self.process_cwl['arguments'] += [
                '-p', self.app.stage_in_param.name,
                f'$(inputs.download_dir.path)/{stage_in_collection_filename}'
            ]

        # Connect the stage-out parameter to the name of the file specified in the template as output
        # That value should contain a full path by using $(runtime.outdir)
        if self.app.stage_out_param is not None:
            stage_out_process_dir = self.process_cwl['outputs']['process_output_dir']['outputBinding']['glob']

            if not re.search('runtime.outdir', stage_out_process_dir):
                raise ProcessError(f"The process CWL template outputs/process_output_dir path needs to contain $(runtime.outdir) in the path")

            self.process_cwl['arguments'] = self.process_cwl.get('arguments', [])
            self.process_cwl['arguments'] += [
                '-p', self.app.stage_out_param.name, 
                stage_out_process_dir
            ]

        else:
            del self.process_cwl['outputs']['process_output_dir']

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

class Descriptor(object):

    def __init__(self, application, repo, templatedir=os.path.join(LOCAL_PATH, 'templates')):

        self.app = application
        self.repo = repo

        self.descriptor = self._read_template(os.path.join(templatedir, 'app_desc.json'))

    def _read_template(self, desc_fname):
        """Loads the template application descriptor and should validate it to
        ensure an exception is not thrown.
        """
        with open(desc_fname, 'r') as f:
            return json.load(f)

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
        for param in self.app.arguments:
            key_type = param.cwl_type
            proc_dict['inputs'].append({
                'id': param.name, 
                'title': 'Automatically detected using papermill.',
                'literalDataDomains': [{'dataType': {'name': key_type}}],
            })

        if self.app.stage_in_param is not None:
            proc_dict['inputs'].append({
                'id': self.app.stage_in_param.name,
                'title': 'Stage-in input specified for URL-to-PATH conversion.',
                'literalDataDomains': [{'dataType': {'name': 'stage_in'}}],
            })

        proc_dict['outputs'] = []
        if self.app.stage_out_param is not None:
            proc_dict['outputs'].append({
                'id': self.app.stage_out_param.name,
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