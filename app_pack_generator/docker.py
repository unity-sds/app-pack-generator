import os
import requests
import logging
import subprocess

import docker

from .util import Util

logger = logging.getLogger(__name__)

class DockerUtil:

    def __init__(self, git_mgr, repo_config=None, do_prune=True, use_owner=True):
        self.git_mgr = git_mgr
        self.repo_config = repo_config
        self.do_prune = do_prune
        self.use_owner = use_owner

        self.docker_client = docker.from_env()

    @property
    def image_tag(self):

        if self.git_mgr.owner is not None and self.use_owner:
            image_tag = self.git_mgr.owner + '/' + self.git_mgr.name
        else:
            image_tag = self.git_mgr.name 

        if len(image_tag) > 128:
            image_tag = image_tag[0:128]

        image_tag += ':' + self.git_mgr.commit_identifier

        # Clean up image_tag to confirm to Docker rules
        # 1. Make sure all characters are lower case
        # 2. Remove repeated periods (ie ..) in cases where git_mgr.name is empty
        image_tag = image_tag.lower()
        image_tag = image_tag.replace('..', '.')

        return image_tag

    def repo2docker(self):
        print("graceal1 in repo2docker function")
        """Calls repo2docker on the local git directory to generate the Docker image.

        No further modifications are made to the docker image.
        """

        # Prune all dangling containers and images to reclaim space and prevent cache usage.
        if self.do_prune:
            try:
                self.docker_client.containers.prune()
                self.docker_client.images.prune()
            except requests.exceptions.ReadTimeout as e:
                logger.error('An error occurred while pruning: {}'.format(e.what()))

        logger.debug(f"Building Docker image named {self.image_tag}")

        if self.repo_config is not None:
            print("graceal1 self.repo_config is not none")
            print(self.repo_config)
            # A specific repo2docker config file has been specified, see if it exists
            # relative to the repository path
            repo_config_local = os.path.join(self.git_mgr.directory, self.repo_config)
            print(repo_config_local)

            # If the repo2docker config file does not exist inside the repo already, assume it is a URL
            # and try to download it
            if not os.path.exists(repo_config_local):
                response = Util.DownloadLink(self.repo_config)
                if response is not None:
                    with open(os.path.join(repo_config_local), 'w') as f:
                        f.write(response.text)
                else:
                    msg = 'Failed to download the specified configuration file: ' + REPO2DOCKER_ENV
                    raise RuntimeError(msg)

            cmd = ['jupyter-repo2docker', '--user-id', '1000', '--user-name', 'jovyan',
                   '--no-run', '--debug', '--image-name', self.image_tag, '--config',
                   repo_config_local, self.git_mgr.directory]
        else:
            print("graceal1 repo_config was not specified")
            print(self.git_mgr.directory)
            repo_config_local = os.path.join(self.git_mgr.directory, 'traitlets.config.json')
            print("graceal1 path to config is ")
            print(repo_config_local)
            # Let repo2docker find the config to use automatically
            cmd = ['jupyter-repo2docker', '--user-id', '1000', '--user-name', 'jovyan',
                   '--no-run', '--debug', '--image-name', self.image_tag, '--config',
                   repo_config_local, self.git_mgr.directory]

        try:
            r2d_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            logger.debug(r2d_output)
        except subprocess.CalledProcessError as exc:
            logger.error(exc.output)
            raise exc

        return self.image_tag

    def push_image(self, registry_url, image_tag=None):

        if image_tag is None:
            image_tag = self.image_tag

        # Save the newly created image to a tarball if the build succeeded.
        image = self.docker_client.images.get(image_tag)

        reg_image_dest = f"{registry_url}/{image_tag}"

        logger.debug(f"Pushing {image_tag} to {reg_image_dest}")

        image.tag(reg_image_dest)

        for line in self.docker_client.images.push(reg_image_dest, stream=True, decode=True):
            logger.debug(line)
            if 'errorDetail' in line:
                raise Exception(f"Error pushing {image_tag} to {reg_image_dest}:" + line['errorDetail']['message'])

        if self.do_prune:
            self.docker_client.images.remove(image.id, force=True)
            try:
                self.docker_client.containers.prune()
                self.docker_client.images.prune()
            except requests.exceptions.ReadTimeout as e:
                logger.error('An error occurred while pruning: {}'.format(e.what()))

        return reg_image_dest
