import os

import git

from .util import Util

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
        # git.Repo(localdir)
        process = Util.System(['git', 'log', '-1', '--pretty=%B'])
        if process.stdout != '':
            return process.stdout.strip()
        return process.stderr.strip()

    @staticmethod
    def CommitHash(repodir):
        """Return the commit message for the current commit."""
        # git.Repo(localdir)
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


