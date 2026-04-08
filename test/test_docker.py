import os

import docker
import pytest

from ogc_ipynb_app_gen import GitManager, DockerUtil

def test_docker_build(tmp_path, example_app_git_url):
    
    git_repo = GitManager(example_app_git_url, tmp_path)

    docker_util = DockerUtil(git_repo)

    docker_util.repo2docker()

    assert docker_util.docker_client.images.get(docker_util.image_tag)
