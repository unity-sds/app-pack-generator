import collections
import datetime
import docker
import functools
import git
import json
import jsonschema
import os
import papermill
import requests
import subprocess
import sys
import tempfile
import yaml


"""
Loads the .ipynb jsonschema for validation purposes (TBD).
"""
LOCAL_PATH = os.path.dirname(os.path.realpath(__file__))
IPYNB_SCHEMA = {}
SCHEMA_FNAME = os.path.join(LOCAL_PATH, 'schemas/nbformat.v4.schema.json')
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
	def Message(repodir):
		"""Return the commit message for the current commit."""
		#git.Repo(localdir)
		process = Util.System(['git', 'log', '-1', '--pretty=%B'])
		if process.stdout != '':
			return process.stdout
		return process.stderr

	@staticmethod
	def CommitHash(repodir):
		"""Return the commit message for the current commit."""
		#git.Repo(localdir)
		process = Util.System(['git', 'rev-parse', 'HEAD'])
		if process.stdout != '':
			return process.stdout
		return process.stderr

	@staticmethod
	def RemoteURL(repodir, https=True):
		"""Return the remote URL for the current repository."""
		process = Util.System(['git', 'config', '--get', 'remote.origin.url'])
		if process.stdout != '':
			if https:
				process.stdout = process.stdout.strip()
				process.stdout = process.stdout.replace(':', '/')
				process.stdout = process.stdout.replace('git@', 'https://')
			return process.stdout
		return process.stderr

	@staticmethod
	def Push(repodir):
		"""Pushes all changes from the specified repository."""
		repo = git.Repo(repodir)
		repo.git.add(update=True)
		repo.index.commit('Automatic push from Jenkins.')
		origin = repo.remote(name='origin')
		origin.push()

	@staticmethod
	def GetTag(repodir):
		"""Gets the current repository tag associated with the current commit."""
		commit_hash = GitHelper.CommitHash(repodir)
		process = Util.System(['git', 'describe', '--tags', '--abbrev=0', commit_hash])
		if process.stdout != '':
			return process.stdout
		return process.stderr


class Docker:
	@staticmethod
	def Repo2Docker(repodir, workingdir=os.path.join(os.getcwd(), '.docker')):
		"""Calls repo2docker on the local git directory to generate the Docker image.
		
		No further modifications are made to the docker image.
		"""
		if not os.path.isdir(workingdir):
			os.makedirs(workingdir)

		# Repo2Docker call using the command line.
		image_tag = GitHelper.GetTag(repodir)
		process = Util.System(['jupyter-repo2docker', '--user-id', '1000', '--user-name', 'jovyan',
			'--target-repo-dir', workingdir, '--no-run', '--debug', '--image-name', image_tag, repodir])

		# Save the newly created image to a tarball if the build succeeded.
		docker_client = docker.from_env()
		username = os.getenv('DOCKER_USER')
		password = os.getenv('DOCKER_PASS')
		docker_client.login(username=username, password=password)
		
		image = docker_client.images.get(image_name)
		repo = 'jplzhan/ci-generated-images'
		image.tag(repo, tag=image_tag)
		for line in docker_client.api.push(repo, tag=image_tag, stream=True, decode=True):
			print(line)
		docker_client.images.remove(image.id, force=True)
		if process.stdout != '' or process.stderr == '':
			return 'docker://' + repo + ':' + image_tag, process.stdout
		return 'docker://' + repo + ':' + image_tag, process.stderr



class AppNB:
	"""Defines a parsed Jupyter Notebook read as a JSON file."""
	def __init__(self, nb_fname, templatedir=os.path.join(LOCAL_PATH, 'templates')):
		self.notebook = {}
		self.inputs = []
		self.outputs = []
		self.repodir = os.getcwd()
		self.descriptor = {}
		self.appcwl = {}
		self.ParseAppCWL(os.path.join(templatedir, 'process.cwl'))
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
		self.repodir = os.path.dirname(nb_fname)
		
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

	def Generate(self, outdir=os.path.join(os.getcwd(), '.generated/')):
		"""Calls all of the Application Notebook generators.
		
		Returns the list of all files generated by this function (abs. path).
		"""
		dockerurl = self.GenerateDockerImage(outdir)

		generated_files = []
		generated_files.append(self.GenerateAppCWL(dockerurl, outdir=outdir))
		generated_files.append(self.GenerateDescriptor(dockerurl, outdir=outdir))

		return generated_files

	def GenerateAppCWL(self, dockerurl, outdir=os.path.join(os.getcwd(), '.generated/')):
		"""Generates the application CWL.
		
		Returns the absolute path of the file generated by this function.
		"""
		if not os.path.isdir(outdir):
			os.makedirs(outdir)
		self.appcwl['hints']['DockerRequirement']['dockerPull'] = dockerurl
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
		fname = os.path.join(outdir, 'process.cwl')
		with open(fname, 'w', encoding='utf-8') as f:
			f.write("#!/usr/bin/env cwl-runner\n")
			yaml.dump(self.appcwl, f, default_flow_style=False)
		return fname

	def GenerateDescriptor(self, dockerurl, outdir=os.path.join(os.getcwd(), '.generated/')):
		"""Generates the application descriptor JSON.
		
		Returns the absolute  path of the file generated by this function.
		"""
		if not os.path.isdir(outdir):
			os.makedirs(outdir)
		url = GitHelper.RemoteURL(self.repodir).replace('.git', '')
		deposit_url = 'https://github.com/jplzhan/artifact-deposit-repo'
		commit_hash = GitHelper.CommitHash(self.repodir).strip()
		split = url.split('/')
		proc_dict = self.descriptor['processDescription']['process']
		proc_dict['id'] = split[-2] + '/' + split[-1].strip() + ':' + GitHelper.GetTag(self.repodir)
		proc_dict['title'] = GitHelper.Message(self.repodir).strip()
		proc_dict['owsContext']['offering']['content']['href'] = deposit_url + '/blob/main/' + commit_hash + '/process.cwl'
		proc_dict['inputs'] = self.inputs
		proc_dict['outputs'] = self.outputs
		self.descriptor['executionUnit'][0]['href'] = dockerurl

		fname = os.path.join(outdir, 'applicationDescriptor.json')
		with open(fname, 'w', encoding='utf-8') as f:
			json.dump(self.descriptor, f, ensure_ascii=False, indent=4)
		return fname

	def GenerateDockerImage(self, outdir=os.path.join(os.getcwd(), '.generated/')):
		if not os.path.isdir(outdir):
			os.makedirs(outdir)
		dockerurl, output = Docker.Repo2Docker(self.repodir, outdir)
		print(output)
		return dockerurl



def main(args):
	min_args = 3
	if len(args) < min_args:
		print('Not enough arguments (min. {}). Now aborting...' % (min_args))
	original_dir = os.getcwd()
	directory = os.path.abspath(args[1])
	outputdir = os.path.abspath(args[2])
	#algorithm = os.path.abspath(args[4])

	if not os.path.isdir(directory):
		print('\'{}\' is not a directory. Now aborting...' % (directory))
		return 1

	# Check if the build command was issued on its own line within the commit message.
	print('Remote URL: ' + GitHelper.RemoteURL(directory))
	tag = GitHelper.GetTag(directory)
	if tag.startswith('fatal: '):
		print('No tag is associated with this commit. Now aborting...')
		return 1

	# Find the first Jupyter Notebook inside the directory.
	nb_fname = ''
	for fname in os.listdir(args[1]):
		if os.path.splitext(fname)[1] == '.ipynb':
			nb_fname = os.path.join(args[1], fname)
			break
	if nb_fname == '':
		print('No jupyter notebook was detected in the directory \'{}\'. Now aborting...' % (directory))
		return 1

	try:
		nb = AppNB(nb_fname)
		files = nb.Generate(outputdir)
		for fname in files:
			print('Created:', fname)

	except (jsonschema.exceptions.ValidationError, jsonschema.exceptions.SchemaError) as e:
		print(e)
		os.chdir(original_dir)
		return 1

	os.chdir(original_dir)
	return 0


if __name__ == '__main__':
	time_ms, ret = Util.TimeFunction(main, sys.argv)
	print('Execution Time:', time_ms, 'ms (returned', str(ret) + ')')
	exit(ret)
