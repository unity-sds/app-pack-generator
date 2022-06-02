import collections
import datetime
import docker
import functools
import git
import jenkins
import json
import jsonschema
import os
import papermill
import requests
import subprocess
import sys
import tempfile
import urllib3
import yaml


# Disable this warning because the Jenkins server has no certificate.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

JENKINS_URL = 'https://soamc-pcm-ci.jpl.nasa.gov/'
GITLAB_URL = 'https://repo.dit.maap-project.org/api/v4/projects/19/trigger/pipeline'
GITLAB_LOG_URL = 'https://repo.dit.maap-project.org/api/v4/projects/19/jobs'
JOB_ENDPOINT = 'MAAP_Build_Trigger_param'
JOB_TOKEN = 'abcdefg123456'

# Load in user token for Jenkins authentication.
USER_TOKEN = ''
with open('.token/secret.txt', 'r') as f:
	USER_TOKEN = f.read().strip()

# Load in pipeline token for Gitlab Runner authentication
GITLAB_TOKEN = ''
with open('.token/pipeline.txt', 'r') as f:
	GITLAB_TOKEN = f.read().strip()

LOG_TOKEN = ''
with open('.token/gitlab-token.txt', 'r') as f:
	LOG_TOKEN = f.read().strip()

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

def QueryJenkins(args):
	#repo = 'https://github.jpl.nasa.gov/zhan/algorithm-deposit-repo.git'
	repo = 'https://github.com/jplzhan/algorithm-deposit-repo.git'
	payload = {'repository': repo, 'checkout': 'downsample-landsat'}

	server = jenkins.Jenkins(JENKINS_URL, username='zhan', password=USER_TOKEN)
	server._session.verify = False
	print('Count:', server.jobs_count())
	print(JOB_ENDPOINT + ':', server.build_job(JOB_ENDPOINT, parameters=payload))
	return 0


def QueryGitlab(args):
	repo = 'https://github.com/jplzhan/algorithm-deposit-repo.git'
	
	# This payload is the bare minimum expected by the endpoint.
	payload = {
		'variables[repository]': repo,
		'variables[checkout]': 'downsample-landsat',
		'token': GITLAB_TOKEN,
		'ref': 'main'
	}

	# This payload also specifies the entrypoint and an external configuration file.
	payload = {
		'variables[repository]': 'https://github.com/lauraduncanson/icesat2_boreal.git',
		'variables[checkout]': 'master',
		'variables[process]': 'dps/alg_3-1-5/run.sh',
		'variables[env]': 'https://mas.maap-project.org/root/ade-base-images/-/raw/vanilla/docker/Dockerfile',
		'token': GITLAB_TOKEN,
		'ref': 'main',
		}

	response = requests.post(GITLAB_URL, data=payload)
	print(response.content.decode('utf-8'))

	return 0


def GetGitlabLogs(args):
	headers = {'PRIVATE-TOKEN': LOG_TOKEN}
	payload = {'scope': ['success']}#['running', 'success', 'failed']}
	response = requests.get(GITLAB_LOG_URL, headers=headers, data=payload)
	response_json = json.loads(response.content.decode('utf-8'))
	print(response.json()[0])

def main(args):
	return QueryGitlab(args)
	#return GetGitlabLogs(args)


if __name__ == '__main__':
	time_ms, ret = Util.TimeFunction(main, sys.argv)
	print('Execution Time:', time_ms, 'ms (returned', str(ret) + ')')
	exit(ret)

