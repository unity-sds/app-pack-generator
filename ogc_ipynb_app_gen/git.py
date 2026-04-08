import os
import logging

import git
from giturlparse import parse as parse_giturl

from .util import Util

HEX_SHA_LENGTH = 8

logger = logging.getLogger(__name__)

class GitRepoError(Exception):
    pass

class GitManager(object):
    def __init__(self, source, dest=None):
        """Manages a information about a git repository for application notebooks"""

        self.source_location = source
        self.source_attrs = parse_giturl(self.source_location)

        if dest is None:
            # If destination is none allow for source to be an existing directory with a git repository

            if not os.path.exists(os.path.join(source, ".git")):
                raise GitRepoError(f"In order for destination to be left empty {source} needs to be an existing git repository")

            logger.info(f"Using existing Git repository from source path {source}")
            self.repo = git.Repo(source)

        elif os.path.exists(os.path.join(dest, ".git")):

            logger.info(f"Using existing Git repository from destination path {dest} with source {source}")
            self.repo = git.Repo(dest)

        elif os.path.exists(dest) and os.path.isfile(dest):
            # Flag an error if the destination is a file
            raise GitRepoError(f"Destination path {dest} is a file not a directory")

        elif os.path.exists(dest) and len(os.listdir(dest)) > 0:
            # Do not allow cloning into an existing non empty directory
            raise GitRepoError(f"Destination path {dest} exists and is a non empty directory")

        else:
            # Hopefully by this point we have a source that is a directory or a URL and destination
            # is an empty or non existent directory
            logger.info(f"Cloning Git repository from {source} to {dest}")

            self.repo = git.Repo.clone_from(source, dest)

    @property
    def directory(self):
        return self.repo.working_tree_dir 

    @property
    def owner(self):

        if hasattr(self.source_attrs, "owner"):
            return self.source_attrs.owner
        else:
            return None

    @property
    def name(self):

        # If no repo attribute then likely a local path to a git repo
        if hasattr(self.source_attrs, "repo"):
            return self.source_attrs.repo
        else:
            return os.path.basename(self.directory.rstrip("/"))

    @property
    def commit_identifier(self):

        return self.repo.commit().hexsha[:HEX_SHA_LENGTH]

    @property
    def commit_message(self):

        return self.repo.commit().message

    def checkout(self, arg):
        """Runs the checkout command on this repository.

        'arg' is either a commit hash, a tag, or a branch name.
        Initializes any new submodules as well.
        """
        self.repo.git.checkout(arg)
        self.repo.git.submodule('update', '--init')
