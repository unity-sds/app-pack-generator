import collections
import datetime
import functools
import git
import json
import jsonschema
import os
import papermill
import requests
import subprocess
import sys
import yaml


"""
Loads the .ipynb jsonschema for validation purposes (TBD).
"""
IPYNB_SCHEMA = {}
SCHEMA_FNAME = 'schemas/nbformat.v4.schema.json'
INPUT_TAG = 'parameters'
OUTPUT_TAG = 'outputFiles'

if os.path.exists(SCHEMA_FNAME):
	with open(SCHEMA_FNAME, 'r') as f:
		IPYNB_SCHEMA = json.load(f)
else:
	print(SCHEMA_FNAME, 'does not exist.')


class Util:
	@staticmethod
	def System(cmd):
		"""Runs a terminal commands with the specified command."""
		return subprocess.run(cmd,\
			stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

	@staticmethod
	def TimeFunction(func, *args, **kwargs):
		"""
		Times the execution of a function and is arguments.

		As this function does not utilize a decorator, it can
		be used to time any arbitrary function call as opposed
		to only the ones the programmer declares.
		"""
		start = datetime.datetime.now()
		ret = func(*args, **kwargs)
		time_diff = datetime.datetime.now() - start
		return time_diff.total_seconds() * 1000, ret


class GitHelper:
	@staticmethod
	def Message(localdir):
		"""Return the commit message for the current commit."""
		#git.Repo(localdir)
		process = Util.System(['git', 'log', '-1', '--pretty=%B'])
		return process.stdout


class Docker:
	@staticmethod
	def Repo2Docker(localdir):
		"""Calls repo2docker on the local git directory to generate the Docker image.
		
		No further modifications are made to the docker image.
		"""
		process = Util.System(['jupyter-repo2docker', localdir])



class AppNB:
	"""Defines a parsed Jupyter Notebook read as a JSON file."""
	def __init__(self, nb_fname, templatedir='templates'):
		self.notebook = {}
		self.descriptor = {}
		self.appcwl = {}
		self.ParseAppCWL(os.path.join(templatedir, 'app.cwl'))
		self.ParseDescriptor(os.path.join(templatedir, 'app_desc.json'))
		self.ParseNotebook(nb_fname)

	def ParseAppCWL(self, app_cwl_fname):
		"""Loads the template application CWL."""
		with open(app_cwl_fname, 'r') as f:
			self.appcwl = yaml.safe_load(f)

	def ParseDescriptor(self, desc_fname):
		"""Loads the template application descriptor and should validate it to
		ensure an exception is not thrown.
		"""
		with open(desc_fname, 'r') as f:
			self.descriptor = json.load(f)

	def ParseNotebook(self, nb_fname):
		"""Should validate nb_fname as a valid, existing Jupyter Notebook to
		ensure no exception is thrown.
		"""
		if not os.path.exists(nb_fname):
			print('Error:', nb_fname, 'does not exist.')
			return

		if os.path.splitext(nb_fname)[1] != '.ipynb':
			print('Error:', nb_fname, 'is not a file with extension .ipynb.')
			return

		print('Opening', nb_fname + '...')


		with open(nb_fname, 'r') as f:
			self.notebook = json.load(f)
		
		jsonschema.validate(instance=self.notebook, schema=IPYNB_SCHEMA)
		self.parameters = papermill.inspect_notebook(nb_fname)
		self.inputs = list(self.parameters.keys())
		
		for cell in self.notebook['cells']:
			cell_type = cell['cell_type']
			metadata = cell['metadata']
			if not 'tags' in metadata.keys():
				continue
			tags = metadata['tags']

			if cell['cell_type'] == 'markdown':
				if OUTPUT_TAG in tags:
					self.outputs = [val for val in cell['source'] if val != '\n']
					self.outputs = list(collections.OrderedDict.fromkeys(self.outputs))
					#print('outputs')
					#print(self.outputs)

	def Generate(self, outdir='generated'):
		"""Calls all of the Application Notebook generators."""
		self.GenerateAppCWL(outdir)
		self.GenerateDescriptor(outdir)

	def GenerateAppCWL(self, outdir='generated'):
		"""Generates the application CWL."""
		self.appcwl['hints']['DockerRequirement']['dockerPull'] = '<<<tempuser/temp-repo:stable>>>'
		self.appcwl['inputs'] = {}
		input_dict = self.appcwl['inputs']
		for key, i in zip(self.inputs, range(1, len(self.inputs) + 1)):
			input_dict[key] = {
				'type': 'string',
				'inputBinding': {
					'position': i,
					'shellQuote': 'false',
					'prefix': '--parameters',
					'valueFrom': key + ' "$(self)"'
				},
			}
		output_dict = self.appcwl['outputs']
		# TODO - Check for stem wildcards
		for key, i in zip(self.outputs, range(1, len(self.outputs) + 1)):
			compound_key = key.replace('.', '_')
			compound_key = compound_key.replace('*', '_')
			output_dict[compound_key] = {
				'type': 'File',
				'outputBinding': {'glob': key},
			}
		with open(os.path.join(outdir, 'app.cwl'), 'w', encoding='utf-8') as f:
			f.write("#!/usr/bin/env cwl-runner\n")
			yaml.dump(self.appcwl, f, default_flow_style=False)

	def GenerateDescriptor(self, outdir='generated'):
		"""Generates the application descriptor JSON."""
		if not os.path.isdir(outdir):
			os.mkdir(outdir)
		proc_dict = self.descriptor['processDescription']['process']
		proc_dict['id'] = '<<<template-repo>>>'
		proc_dict['title'] = '<<<Template description for this generated application descriptor>>>'
		proc_dict['owsContext']['offering']['content']['href'] = '<<<https://raw.githubusercontent.com/temp-user/temp-repo/main/temp.cwl>>>>'
		proc_dict['inputs']
		proc_dict['outputs']
		self.descriptor['executionUnit'][0]['href'] = '<<<docker://tempuser/template-repo:stable>>>'
		with open(os.path.join(outdir, 'app_desc.json'), 'w', encoding='utf-8') as f:
			json.dump(self.descriptor, f, ensure_ascii=False, indent=4)



def main(args):
	if len(args) <= 1:
		print('No arguments were provided (min. 1).')
		return 1

	try:
		nb = AppNB(args[1])
		nb.Generate()
		print(GitHelper.Message(os.getcwd()))
	except (jsonschema.exceptions.ValidationError, jsonschema.exceptions.SchemaError) as e:
		print(e)
		return 1

	return 0


if __name__ == '__main__':
	time_ms, ret = Util.TimeFunction(main, sys.argv)
	print('Execution Time:', time_ms, 'ms (returned', str(ret) + ')')
	exit(ret)
