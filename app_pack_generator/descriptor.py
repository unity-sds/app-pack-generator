import os
import json
import logging

logger = logging.getLogger(__name__)

LOCAL_PATH = os.path.dirname(os.path.realpath(__file__))

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
