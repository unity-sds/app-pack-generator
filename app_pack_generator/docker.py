import os
import requests
import logging
import subprocess

import docker

from .util import Util

# Default from docker-py is 60 seconds
# This was found to be to small when dealing with pushing large images to remote repos like ECR
DOCKER_CLIENT_TIMEOUT = 600

logger = logging.getLogger(__name__)

class DockerUtil:

    def __init__(self, git_mgr, repo_config=None, do_prune=True, use_namespace=None, use_repository=None, use_tag=None):
        self.git_mgr = git_mgr
        self.repo_config = repo_config
        self.do_prune = do_prune

        self.use_namespace = use_namespace
        self.use_repository = use_repository
        self.use_tag = use_tag

        self.docker_client = docker.from_env(timeout=DOCKER_CLIENT_TIMEOUT)

    @property
    def image_namespace(self):
        "namespace portion of a Docker image reference string"

        if self.use_namespace is not None:
            return self.use_namespace

        if self.git_mgr.owner is not None:
            return self.git_mgr.owner

    @property
    def image_repository(self):
        "namespace portion of a Docker image reference string"

        if self.use_repository is not None:
            return self.use_repository

        return self.git_mgr.name

    @property
    def image_tag(self):
        "tag portion of a Docker image reference string"

        if self.use_tag is not None:
            return self.use_tag

        image_tag = self.git_mgr.commit_identifier

        # Clean up image_tag to confirm to Docker rules
        # 1. Make sure all characters are lower case
        # 2. Remove repeated periods (ie ..) in cases where git_mgr.name is empty
        image_tag = image_tag.lower()
        image_tag = image_tag.replace('..', '.')

        return image_tag

    @property
    def image_reference(self):
        """
        A Docker image reference consists of several components that describe where the image is stored and its identity. These components are:

        [HOST[:PORT]/]NAMESPACE/REPOSITORY[:TAG]

        https://docs.docker.com/reference/cli/docker/image/tag/

        HOST:PORT are added in push_image
        """

        if self.image_namespace is not None and self.image_namespace != "":
            return f"{self.image_namespace}/{self.image_repository}:{self.image_tag}"
        else:
            return f"{self.image_repository}:{self.image_tag}"

    def repo2docker(self):
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

        logger.info(f"Building Docker image named {self.image_reference}")

        # Build initial repo2docker command line arguments
        cmd = ['jupyter-repo2docker', '--user-id', '1000', '--user-name', 'jovyan',
               '--no-run', '--debug', '--image-name', self.image_reference]

        if self.repo_config is not None:
            # If the repo2docker config file does not exist inside the repo already, assume it is a URL
            # and try to download it
            if not os.path.exists(self.repo_config):
                repo_config_local = os.path.join(self.git_mgr.directory, os.path.basename(self.repo_config))

                response = Util.DownloadLink(self.repo_config)
                if response is not None:
                    with open(os.path.join(repo_config_local), 'w') as f:
                        f.write(response.text)
                else:
                    msg = 'Failed to download the specified configuration file: ' + self.repo_config
                    raise RuntimeError(msg)
            else:
                repo_config_local = self.repo_config

            cmd += ['--config', repo_config_local]

        # The repository must be the last argument to repo2docker
        cmd += [self.git_mgr.directory]

        #, self.git_mgr.directory]
        logger.debug("Executing repo2docker with command line:")
        logger.debug(" ".join(cmd))

        try:
            r2d_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
            logger.debug(r2d_output)
        except subprocess.CalledProcessError as exc:
            logger.error(exc.output)
            raise exc

        return self.image_reference

    def build_image(self):
        "Use instead of calling the repo2docker function since it could possibly be deprecated in the future"

        return self.repo2docker()

    def push_image(self, registry_url, image_reference=None):
        "Pushes the Docker image created by the build_image command into a remote registry with an optional different image reference string"

        if image_reference is None:
            image_reference = self.image_reference

        # Save the newly created image to a tarball if the build succeeded.
        image = self.docker_client.images.get(image_reference)

        reg_image_dest = f"{registry_url}/{image_reference}"

        logger.info(f"Pushing {image_reference} to {reg_image_dest}")

        # Use two argument call to .tag() per the API documentation
        # The Docker API is more lenient that Podman and will
        # Parse the URL for us if we just supply reg_image_dest
        # But we need to use the actual documented API to get this working
        # With Podman
        #
        # https://docker-py.readthedocs.io/en/stable/images.html?highlight=tag#docker.models.images.Image.tag
        if image_reference.find(":") >= 0:
            local_repo, local_tag = image_reference.split(":")

            repository = f"{registry_url}/{local_repo}"
            image.tag(repository, local_tag)
        else:
            image.tag(reg_image_dest)

        for line in self.docker_client.images.push(reg_image_dest, stream=True, decode=True):
            logger.info(line)
            if 'errorDetail' in line:
                raise Exception(f"Error pushing {image_reference} to {reg_image_dest}:" + line['errorDetail']['message'])

        if self.do_prune:
            self.docker_client.images.remove(image.id, force=True)
            try:
                self.docker_client.containers.prune()
                self.docker_client.images.prune()
            except requests.exceptions.ReadTimeout as e:
                logger.error('An error occurred while pruning: {}'.format(e.what()))

        return reg_image_dest