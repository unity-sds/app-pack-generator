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
JOB_ENDPOINT = 'MAAP_Build_Trigger_param'
JOB_TOKEN = 'abcdefg123456'

# Load in user token for Jenkins authentication.
USER_TOKEN = ''
with open('.token/secret.txt', 'r') as f:
	USER_TOKEN = f.read().strip()

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


def main(args):
	repo = 'https://github.jpl.nasa.gov/zhan/algorithm-deposit-repo.git'
	payload = {'repository': repo, 'checkout': 'HEAD'}

	server = jenkins.Jenkins(JENKINS_URL, username='zhan', password=USER_TOKEN)
	server._session.verify = False
	print('Count:', server.jobs_count())
	print(JOB_ENDPOINT + ':', server.build_job(JOB_ENDPOINT, parameters=payload))
	return


if __name__ == '__main__':
	time_ms, ret = Util.TimeFunction(main, sys.argv)
	print('Execution Time:', time_ms, 'ms (returned', str(ret) + ')')
	exit(ret)
