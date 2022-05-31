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
import shutil
import subprocess
import sys
import tempfile
import yaml


"""
Loads the .ipynb jsonschema for validation purposes (TBD).
"""
LOCAL_PATH = os.path.dirname(os.path.realpath(__file__))
ARTIFACT_DIR = os.getenv('ARTIFACT_DIR')
IPYNB_SCHEMA = {}
SCHEMA_FNAME = os.path.join(LOCAL_PATH, 'schemas/nbformat.v4.schema.json')
INPUT_TAG = 'parameters'
OUTPUT_TAG = 'outputFiles'
REPO2DOCKER_ENV = os.getenv('env')

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

	@staticmethod
	def GetKeyType(default_val):
		"""Check if a given key's default value is a string or can be converted to a float."""
		if default_val.find('"') != -1 or default_val.find('\'') != -1:
			return 'string'
		key_type = 'Any'
		try:
			temp = float(default_val)
			key_type = 'float'
		except ValueError:
			pass
		return key_type



class GitHelper:
	def __init__(self, url, dst=os.getcwd()):
		"""Manages a freshly cloned git repository."""
		self.repo = GitHelper.Clone(url, dst)
		self.url = url
		self.directory = dst

		split = url.replace('.git', '').split('/')
		self.owner = split[-2].strip()
		self.name = split[-1].strip()
		self.checkout = 'HEAD'
		self.dirname = self.owner + '/' + self.name + '/' + self.checkout

	def Checkout(self, arg):
		"""Runs the checkout command on this repository.
		
		'arg' is either a commit hash, a tag, or a branch name.
		"""
		git = self.repo.git
		git.checkout(arg)
		self.checkout = arg
		self.dirname = self.owner + '/' + self.name + '/' + self.checkout

	@staticmethod
	def Clone(repolink, dst=os.getcwd()):
		"""Clones the specified repository using its HTTPS URL."""
		print('Cloning to ' + dst + '...')
		return git.Repo.clone_from(repolink, dst)

	@staticmethod
	def Message(repodir):
		"""Return the commit message for the current commit."""
		#git.Repo(localdir)
		process = Util.System(['git', 'log', '-1', '--pretty=%B'])
		if process.stdout != '':
			return process.stdout.strip()
		return process.stderr.strip()

	@staticmethod
	def CommitHash(repodir):
		"""Return the commit message for the current commit."""
		#git.Repo(localdir)
		process = Util.System(['git', 'rev-parse', 'HEAD'])
		if process.stdout != '':
			return process.stdout.strip()
		return process.stderr.strip()

	@staticmethod
	def RemoteURL(repodir, https=True):
		"""Return the remote URL for the current repository."""
		process = Util.System(['git', 'config', '--get', 'remote.origin.url'])
		if process.stdout != '':
			if https:
				process.stdout = process.stdout.strip()
				process.stdout = process.stdout.replace(':', '/')
				process.stdout = process.stdout.replace('git@', 'https://')
			return process.stdout.strip()
		return process.stderr.strip()

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
		process = Util.System(['git', 'describe', '--tags', '--abbrev=0'])
		if process.stdout != '':
			return process.stdout.strip()
		return process.stderr.strip()


class Docker:
	@staticmethod
	def Repo2Docker(repo, workingdir=os.path.join(os.getcwd(), '.docker')):
		"""Calls repo2docker on the local git directory to generate the Docker image.
		
		No further modifications are made to the docker image.
		"""
		if not os.path.isdir(workingdir):
			os.makedirs(workingdir)

		# Repo2Docker call using the command line.
		image_tag = repo.owner + '.' + repo.name + '.' + repo.checkout
		if len(image_tag) > 128:
			image_tag = image_tag[0:128]

		cmd = ['jupyter-repo2docker', '--user-id', '1000', '--user-name', 'jovyan',
			'--no-run', '--debug', '--image-name', image_tag, repo.directory]
		if REPO2DOCKER_ENV is not None and os.path.exists(REPO2DOCKER_ENV):
			cmd = ['jupyter-repo2docker', '--user-id', '1000', '--user-name', 'jovyan',
			'--no-run', '--debug', '--image-name', '--config',
			REPO2DOCKER_ENV, image_tag, repo.directory]
		elif REPO2DOCKER_ENV is not None:
			try:
				requests.get(REPO2DOCKER_ENV)
			except Exception as e:
				print('Could not download assumed URL: \'' + REPO2DOCKER_ENV + '\'')
				print(e)

		process = Util.System(cmd)
		print(process.stdout)
		print(process.stderr)

		# Save the newly created image to a tarball if the build succeeded.
		docker_client = docker.from_env()
		username = os.getenv('DOCKER_USER')
		password = os.getenv('DOCKER_PASS')
		docker_client.login(username=username, password=password)
		
		image = docker_client.images.get(image_tag)
		repo = 'jplzhan/ci-generated-images'
		image.tag(repo, tag=image_tag)
		for line in docker_client.api.push(repo, tag=image_tag, stream=True, decode=True):
			print(line)
		docker_client.images.remove(image.id, force=True)
		if process.stdout != '' or process.stderr == '':
			return repo + ':' + image_tag, process.stdout
		return repo + ':' + image_tag, process.stderr



class AppNB:
	"""Defines a parsed Jupyter Notebook read as a JSON file."""
	def __init__(self, repo, proc=None, templatedir=os.path.join(LOCAL_PATH, 'templates')):
		self.notebook = {}
		self.parameters = {}
		self.inputs = []
		self.outputs = []
		self.repo = repo
		self.descriptor = {}
		self.appcwl = {}
		print('Checkpoint 0.1')
		self.ParseAppCWL(os.path.join(templatedir, 'process.cwl'))
		print('Checkpoint 0.2')
		self.ParseDescriptor(os.path.join(templatedir, 'app_desc.json'))

		print('Checkpoint 1')

		# TODO - Need more rigorous checks here...
		self.process = proc if proc is not None and os.path.exists(proc) else 'process.ipynb'
		if proc.endswith('.ipynb'):
			self.ParseNotebook()
		elif not proc.endswith('.sh'):
			raise 'Unsupported file format submitted for entrypoint.'

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

	def ParseNotebook(self):
		"""Deduces the application notebook within the managed .
		Should validate nb_fname as a valid, existing Jupyter Notebook to
		ensure no exception is thrown.
		"""
		# Find the first Jupyter Notebook inside the directory.
		nb_fname = ''
		for fname in os.listdir(self.repo.directory):
			if fname == 'process.ipynb':
				nb_fname = os.path.join(self.repo.directory, fname)
				break
		if nb_fname == '':
			raise 'No process.ipynb was detected in the directory \'{}\'. Now aborting...' % (self.repo.directory)
		
		print('Opening', nb_fname + '...')
		with open(nb_fname, 'r') as f:
			self.notebook = json.load(f)
		
		jsonschema.validate(instance=self.notebook, schema=IPYNB_SCHEMA)
		self.parameters = papermill.inspect_notebook(nb_fname)
		self.inputs = list(self.parameters.keys())
		print(self.parameters)
		
		for cell in self.notebook['cells']:
			cell_type = cell['cell_type']
			metadata = cell['metadata']
			if not 'tags' in metadata.keys():
				continue
			tags = metadata['tags']

			if cell['cell_type'] == 'markdown':
				if OUTPUT_TAG in tags:
					self.outputs = [val.strip() for val in cell['source'] if val != '\n']
					self.outputs = list(collections.OrderedDict.fromkeys(self.outputs))
					print('outputs')
					print(self.outputs)

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
		
		if self.process.endswith('.sh'):
			self.appcwl['baseCommand'] = ['sh', self.process]
			return os.path.join(outdir, 'process.cwl')

		self.appcwl['hints']['DockerRequirement']['dockerPull'] = dockerurl
		self.appcwl['inputs'] = {}
		input_dict = self.appcwl['inputs']
		for key, i in zip(self.inputs, range(1, len(self.inputs) + 1)):
			input_dict[key] = {
				'type': Util.GetKeyType(self.parameters[key]['default']),
				'inputBinding': {
					'position': i,
					'shellQuote': False,
					'prefix': '--parameters',
					'valueFrom': key + ' "$(self)"'
				},
			}

		self.appcwl['outputs'] = {}
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
		deposit_url = 'https://raw.githubusercontent.com/jplzhan/artifact-deposit-repo'
		tag = self.repo.dirname
		proc_dict = self.descriptor['processDescription']['process']
		proc_dict['id'] = self.repo.owner + '.' + self.repo.name + '.' + self.repo.checkout 
		proc_dict['title'] = GitHelper.Message(self.repo.directory).strip()
		proc_dict['owsContext']['offering']['content']['href'] = deposit_url + '/main/' + tag + '/process.cwl'
		
		proc_dict['inputs'] = []
		for key in self.inputs:
			key_type = Util.GetKeyType(self.parameters[key]['default'])
			proc_dict['inputs'].append({
				'id': key,
				'title': 'Automatically detected using papermill.',
				'literalDataDomains': [{'dataType':{'name': key_type}}], 
			})
		
		proc_dict['outputs'] = []
		for key in self.outputs:
			proc_dict['outputs'].append({
				'id': key,
				'title': 'Automatically detected from .ipynb parsing.',
				'output': {
					'formats':[
						{'mimeType': 'text/*', 'default': True}
					]
				}
			})
		
		self.descriptor['executionUnit'][0]['href'] = 'docker://' + dockerurl

		fname = os.path.join(outdir, 'applicationDescriptor.json')
		with open(fname, 'w', encoding='utf-8') as f:
			json.dump(self.descriptor, f, ensure_ascii=False, indent=4)
		return fname

	def GenerateDockerImage(self, outdir=os.path.join(os.getcwd(), '.generated/')):
		"""Generates the docker image associated with this repository."""
		if not os.path.isdir(outdir):
			os.makedirs(outdir)
		dockerurl, output = Docker.Repo2Docker(self.repo, outdir)
		print(output)
		return dockerurl



def main(args):
	"""Accepts exactly 2 arguments (3 in total when including the script name):

		1 - The HTTPS link to the repository which will be cloned.
		2 - The identifier the repository will run 'git checkout' to.

	Optional environment variables which may be defined:
		1 - "process": Relative path to an existing .ipynb or .sh file.
		2 - "env": Relative path or URL to an existing file compatible with repo2docker.
	"""
	min_args = 3
	if len(args) < min_args:
		print('Not enough arguments (min. {}). Now aborting...' % (min_args))
	original_dir = os.getcwd()
	repodir = os.path.join(original_dir, 'algorithm')
	repolink = args[1]
	checkout = args[2]

	print('Arguments:')
	for arg in args:
		print(arg)

	# Clone the repository to the specified directory and change to it.
	repo = GitHelper(repolink, dst=repodir)
	repo.Checkout(checkout)
	os.chdir(repodir)

	# Create the destination subdirectory for the artifacts using the link and checkout identifier.
	print('ARTIFACT_DIR:', ARTIFACT_DIR)
	print('repo.dirname:', repo.dirname)
	outdir = os.path.join(ARTIFACT_DIR, repo.dirname)

	# Generate artifacts within the output directory.
	return_code = 0
	try:
		print('Checkpoint 0')
		nb = AppNB(repo, proc=os.getenv('process'))
		print('Checkpoint 2')
		files = nb.Generate(outdir)

		# Move the generated files to the artifact directory and commit them.
		os.chdir(outdir)
		for fname in files:
			print('Adding artifact:', fname)

			proc = Util.System(['git', 'add', fname])
			print(proc.stdout)
			print(proc.stderr)
			proc.check_returncode()

		proc = Util.System(['git', 'commit', '-m', 'Update from CI/CD server.'])
		print(proc.stdout)
		print(proc.stderr)

	except (jsonschema.exceptions.ValidationError, jsonschema.exceptions.SchemaError) as e:
		print(e)
		return_code = 1
	except Exception as e:
		print(e)
		return_code = 1

	os.chdir(original_dir)
	return return_code


if __name__ == '__main__':
	time_ms, ret = Util.TimeFunction(main, sys.argv)
	print('Execution Time:', time_ms, 'ms (returned', str(ret) + ')')
	exit(ret)
