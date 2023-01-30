import collections
import copy
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
SCHEMA_LIST = [os.path.join(LOCAL_PATH, \
	'schemas/nbformat.v4.{v}.schema.json'.format(v=i)) for i in range(0, 6)]
INPUT_TAG = 'parameters'
OUTPUT_TAG = 'outputFiles'
REPO2DOCKER_ENV = os.getenv('env')


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
	def GetKeyType(inferred_type, default_val):
		"""Attempts to convert the inferred type to an equivalent CWL type.
		
		Otherwise, checks if a given key's default value is a string or can be converted to a float."""
		inferred_type = inferred_type.lower()
		convert_dict = {
			'string': ['stage_in', 'stage-in', 'string'],
			'File': ['stage_out', 'stage-out', 'file'],
			'int': ['int', 'integer'],
			'boolean': ['bool', 'boolean'],
			'float': ['float'],
			'double': ['double'],
			'Directory': ['directory'],
			'Any': ['any']
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

	@staticmethod
	def WriteYMLFile(fname, target):
		"""Writes [target] dictionary to a .yml file with filename [fname]."""
		with open(fname, 'w', encoding='utf-8') as f:
			f.write("#!/usr/bin/env cwl-runner\n")
			yaml.dump(target, f, default_flow_style=False)

	@staticmethod
	def DownloadLink(url, default=None):
		"""Downloads the specified URL via a GET request.
		
		If url is not a valid link, or if the request fails, returns the [default]
		parameter instead.
		"""
		try:
			response = requests.get(url)
			if response.status_code == 404:
				raise RuntimeError('<Response 404>')
			return response
		except Exception as e:
			if url.startswith('http://') or url.startswith('https://'):
				print('Could not download assumed URL: \'' + url + '\'')
				print(e)
		return default



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
		Initializes any new submodules as well.
		"""
		self.repo.git.checkout(arg)
		self.repo.git.submodule('update', '--init')

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

		# Prune all dangling containers and images to reclaim space and prevent cache usage.
		docker_client = docker.from_env()
		username = os.getenv('DOCKER_USER')
		password = os.getenv('DOCKER_PASS')
		docker_client.login(username=username, password=password)
		try:
			docker_client.containers.prune()
			docker_client.images.prune()
		except requests.exceptions.ReadTimeout as e:
			print('An error occurred while pruning: {}'.format(e.what()))

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
			response = Util.DownloadLink(REPO2DOCKER_ENV)
			if response is not None:
				with open(os.path.join(repo.directory, 'Dockerfile'), 'w') as f:
					f.write(response.text)
			else:
				msg = 'Failed to download the specified configuration file: ' + REPO2DOCKER_ENV
				raise RuntimeError(msg)

		process = Util.System(cmd)
		print(process.stdout)
		print(process.stderr)

		# Save the newly created image to a tarball if the build succeeded.		
		image = docker_client.images.get(image_tag)
		repo = 'jplzhan/ci-generated-images'
		image.tag(repo, tag=image_tag)
		for line in docker_client.api.push(repo, tag=image_tag, stream=True, decode=True):
			print(line)
		docker_client.images.remove(image.id, force=True)
		try:
			docker_client.containers.prune()
			docker_client.images.prune()
		except requests.exceptions.ReadTimeout as e:
			print('An error occurred while pruning: {}'.format(e.what()))
		
		if process.stdout != '' or process.stderr == '':
			return repo + ':' + image_tag, process.stdout
		return repo + ':' + image_tag, process.stderr



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
		self.workflow_cwl = self.ParseAppCWL(os.path.join(templatedir, 'workflow.cwl'))
		self.stage_in_cwl = self.ParseAppCWL(os.path.join(templatedir, 'stage_in.cwl'))
		self.appcwl = self.ParseAppCWL(os.path.join(templatedir, 'process.cwl'))
		self.stage_out_cwl = self.ParseAppCWL(os.path.join(templatedir, 'stage_out.cwl'))
		self.ParseDescriptor(os.path.join(templatedir, 'app_desc.json'))

		# Define the stage-in inputs fields schema and pop its input bindings.
		self.cache_workflow_cwl = None
		self.stage_in_input_type = copy.deepcopy(self.stage_in_cwl['inputs']['input_path']['type'])
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
			print('Using .sh file with name \'' + self.process + '\' as executable process...')

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
		print('Validating \'' + nb_name + '\' as a valid v4.0 - v4.5 Jupyter notebook...')
		validation_success = False
		for fname in SCHEMA_LIST:
			if os.path.exists(fname):
				try:
					with open(fname, 'r') as f:
						schema = json.load(f)
						jsonschema.validate(instance=self.notebook, schema=schema)
						print('Successfully validated \'' + nb_fname + '\' using ' + fname + '.')
						validation_success = True
						break
				except (jsonschema.exceptions.ValidationError, jsonschema.exceptions.SchemaError) as e:
					print(fname + ' failed...')
					continue
			else:
				print(fname + ' does not exist.')
		if not validation_success:
			msg = 'Failed to validate \'' + nb_fname + '\' as a v4.0 - v4.5 Jupyter Notebook...'
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

	def Generate(self, outdir=os.path.join(os.getcwd(), '.generated/')):
		"""Calls all of the Application Notebook generators.
		
		Returns the list of all files generated by this function (abs. path).
		"""
		dockerurl = self.GenerateDockerImage(outdir)

		generated_files = []
		generated_files.append(self.GenerateWorkflowCWL(outdir=outdir))
		generated_files.append(self.GenerateCacheCWL(outdir=outdir))
		generated_files.append(self.GenerateStageInCWL(outdir=outdir))
		generated_files.append(self.GenerateAppCWL(dockerurl, outdir=outdir))
		generated_files.append(self.GenerateStageOutCWL(outdir=outdir))
		generated_files.append(self.GenerateDescriptor(dockerurl, outdir=outdir))

		return generated_files

	def GenerateWorkflowCWL(self, outdir=os.path.join(os.getcwd(), '.generated/')):
		"""Generates the workflow CWL.
		
		Returns the absolute path of the file generated by this function.
		"""
		self.workflow_cwl['outputs'] = {}

		# Fill out the inputs field for running the workflow CWL
		self.workflow_cwl['inputs'] = {
			'stage_out': {
				'type': [
					{
						'type': 'record',
						'name': 'STAK',
						'fields': {
							's3_url': 'string',
							'aws_access_key_id': 'string',
							'aws_secret_access_key': 'string',
							'aws_session_token': 'string',
							'region_name': 'string',
						},
					},
					{
						'type': 'record',
						'name': 'LTAK',
						'fields': {
							's3_url': 'string',
							'aws_config': 'Directory',
						},
					},
					{
						'type': 'record',
						'name': 'IAM',
						'fields': {
							's3_url': 'string',
						},
					},
				],
			},
			'cache_dir': 'Directory?',
			'cache_only': {
				'type': 'boolean',
				'default': False,
			},
			'parameters': {
				'type': {
					'type': 'record',
					'name': 'parameters',
					'fields': {},
				},
			},
		}
		input_dict = self.workflow_cwl['inputs']['parameters']['type']['fields']
		for key in self.inputs:
			param = self.parameters[key]
			inferred_type = param['inferred_type_name'] if param['inferred_type_name'] != 'None' else param['help']
			input_dict[key] = Util.GetKeyType(inferred_type, param['default'])
		
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
			process_dict['in'][key] = {
				'source': 'parameters',
				'valueFrom': '$(self.{})'.format(key),
			}
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
			raise Exception('AppNB.GenerateCacheCWL must be called after AppNB.GenerateWorkflowCWL.')

		# This is caching workflow is a subset of the workflow CWL, pop extraneous elements
		self.cache_workflow_cwl['steps'].pop('process')
		self.cache_workflow_cwl['steps'].pop('stage_out')
		self.cache_workflow_cwl['inputs'].pop('stage_out')
		self.cache_workflow_cwl['inputs']['cache_only']['default'] = True
		for key in self.inputs:
			self.cache_workflow_cwl['inputs']['parameters']['type']['fields'].pop(key)

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
			self.appcwl['baseCommand'] = ['sh', self.process, '/tmp/inputs.json']

		# Forward the ordinary parameters to the process step directly
		self.appcwl['requirements']['DockerRequirement']['dockerPull'] = dockerurl
		self.appcwl['inputs'] = {}
		input_dict = self.appcwl['inputs']
		for key in self.inputs:
			param = self.parameters[key]
			inferred_type = param['inferred_type_name'] if param['inferred_type_name'] != 'None' else param['help']
			input_dict[key] = Util.GetKeyType(inferred_type, param['default'])

		# Append the stage-in files to the input list with type File[] for explicit
		# forwarding from another container. Enable them to be modified in-place.
		for key in self.stage_in:
			input_dict[key] = 'File[]'

		# Create the outputs field with the output notebook as a default
		self.appcwl['outputs'] = {
			'output_nb': {
				'type': 'File',
				'outputBinding': {'glob': 'output_nb.ipynb'},
			},
			'output_dir': {
				'type': 'Directory',
				'outputBinding': {'glob': 'output'},
			},
		}
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
		tag = self.repo.dirname
		proc_dict = self.descriptor['processDescription']['process']
		proc_dict['id'] = self.repo.owner + '.' + self.repo.name + '.' + self.repo.checkout 
		proc_dict['title'] = GitHelper.Message(self.repo.directory).strip()
		proc_dict['owsContext']['offering']['content']['href'] = deposit_url + '/main/' + tag + '/workflow.cwl'
		
		proc_dict['inputs'] = []
		for key in self.inputs:
			param = self.parameters[key]
			inferred_type = param['inferred_type_name'] if param['inferred_type_name'] != 'None' else param['help']
			key_type = Util.GetKeyType(inferred_type, param['default'])
			proc_dict['inputs'].append({
				'id': key,
				'title': 'Automatically detected using papermill.',
				'literalDataDomains': [{'dataType':{'name': key_type}}], 
			})
		for key in self.stage_in:
			param = self.parameters[key]
			proc_dict['inputs'].append({
				'id': key,
				'title': 'Stage-in input specified for URL-to-PATH conversion.',
				'literalDataDomains': [{'dataType':{'name': 'stage_in'}}], 
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
		print(f'Not enough arguments (min. {min_args}). Now aborting...')
		return 1

	original_dir = os.getcwd()
	repodir = os.path.join(original_dir, 'algorithm')
	repolink = args[1]
	checkout = args[2]

	print('Arguments:')
	for arg in args:
		print(arg)

	# Clone the repository to the specified directory and change to it.
	if repolink == '':
		msg = 'No repository URL was provided, cannot clone. Now exiting...'
		raise RuntimeError(msg)
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
		nb = AppNB(repo, proc=os.getenv('process'))
		files = nb.Generate(outdir)

		# Move the generated files to the artifact directory and commit them.
		os.chdir(outdir)
		Util.System(['git', 'config', 'user.name', 'Automated'])
		Util.System(['git', 'config', 'user.email', 'N/A'])
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
	except RuntimeError as e:
		print(e)
		return_code = 1

	os.chdir(original_dir)
	return return_code


if __name__ == '__main__':
	time_ms, ret = Util.TimeFunction(main, sys.argv)
	print('Execution Time:', time_ms, 'ms (returned', str(ret) + ')')
	exit(ret)
