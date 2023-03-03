import os
import requests

import docker

from .util import Util

class DockerUtil:

    def __init__(self, repo, repo_config=None, do_prune=True):
        self.repo = repo
        self.repo_config = repo_config
        self.do_prune = do_prune

        self.docker_client = docker.from_env()
        username = os.getenv('DOCKER_USER')
        password = os.getenv('DOCKER_PASS')
        self.docker_client.login(username=username, password=password)

    def Repo2Docker(self):
        """Calls repo2docker on the local git directory to generate the Docker image.

        No further modifications are made to the docker image.
        """

        # Prune all dangling containers and images to reclaim space and prevent cache usage.
        if self.do_prune:
            try:
                self.docker_client.containers.prune()
                self.docker_client.images.prune()
            except requests.exceptions.ReadTimeout as e:
                print('An error occurred while pruning: {}'.format(e.what()))

        # Repo2Docker call using the command line.
        image_tag = self.repo.owner + '.' + self.repo.name + '.' + self.repo.checkout
        if len(image_tag) > 128:
            image_tag = image_tag[0:128]

        # Clean up image_tag to confirm to Docker rules
        # 1. Make sure all characters are lower case
        # 2. Remove repeated periods (ie ..) in cases where repo.name is empty
        image_tag = image_tag.lower()
        image_tag = image_tag.replace('..', '.')

        if self.repo_config is not None:
            # A specific repo2docker config file has been specified, see if it exists
            # relative to the repository path
            repo_config_local = os.path.join(self.repo.directory, self.repo_config)

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
                   '--no-run', '--debug', '--image-name', image_tag, '--config',
                   repo_config_local, self.repo.directory]
        else:
            # Let repo2docker find the config to use automatically
            cmd = ['jupyter-repo2docker', '--user-id', '1000', '--user-name', 'jovyan',
                   '--no-run', '--debug', '--image-name', image_tag, self.repo.directory]

        process = Util.System(cmd)
        print(process.stdout)
        print(process.stderr)

        return image_tag

    def PushImage(self, image_tag, registry):

        # Save the newly created image to a tarball if the build succeeded.
        image = self.docker_client.images.get(image_tag)
        image.tag(registry, tag=image_tag)
        for line in self.docker_client.api.push(registry, tag=image_tag, stream=True, decode=True):
            print(line)

        if self.do_prune:
            self.docker_client.images.remove(image.id, force=True)
            try:
                self.docker_client.containers.prune()
                self.docker_client.images.prune()
            except requests.exceptions.ReadTimeout as e:
                print('An error occurred while pruning: {}'.format(e.what()))

        return registry + ':' + image_tag

