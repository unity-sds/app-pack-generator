import os
import git

import pytest

from app_pack_generator import GitManager, GitRepoError

def init_empty_repo(path):
    repo = git.Repo.init(path)

    file_name = os.path.join(repo.working_tree_dir, "new-file")
    # This function just creates an empty file ...
    open(file_name, "wb").close()
    repo.index.add([file_name])
    repo.index.commit("initial commit")

    return repo

def check_empty_repo(git_mgr, repo_path):

    assert os.path.exists(os.path.join(git_mgr.directory, ".git"))

    assert(os.path.realpath(repo_path) == os.path.realpath(git_mgr.directory))
    assert(git_mgr.name == os.path.basename(str(repo_path).rstrip("/")))
    assert(git_mgr.owner is None)

def check_remote_clone(git_mgr):

    assert os.path.exists(os.path.join(git_mgr.directory, ".git"))

    assert(git_mgr.owner == "unity-sds")
    assert(git_mgr.name == "unity-example-application")

def test_no_dest_no_existing_git(tmp_path):

    with pytest.raises(GitRepoError, match=r"In order for destination to be left empty .* needs to be an existing git repository"):
        git_mgr = GitManager(str(tmp_path))

def test_no_dest_existing_git(tmp_path):

    repo = init_empty_repo(str(tmp_path))

    git_mgr = GitManager(str(tmp_path))

    check_empty_repo(git_mgr, repo.working_tree_dir)

def test_existing_dest_existing_source(tmp_path):

    repo = init_empty_repo(str(tmp_path))

    with pytest.raises(GitRepoError, match=r"Source .* is not a URL but destination path .* is an existing git repository"):
        git_mgr = GitManager(str(tmp_path), str(tmp_path))

def test_existing_dest_no_existing_source(tmp_path, example_app_git_url):

    repo = git.Repo.clone_from(example_app_git_url, str(tmp_path))

    git_mgr = GitManager(example_app_git_url, str(tmp_path))

    check_remote_clone(git_mgr)

def test_existing_file(tmp_path, example_app_git_url):

    test_filename = tmp_path / "dummy.txt"
    test_filename.write_text("Duh")

    with pytest.raises(GitRepoError, match=r"Destination path .* is a file not a directory"):
        git_mgr = GitManager(example_app_git_url, str(test_filename))

def test_existing_nonempty(tmp_path, example_app_git_url):

    test_filename = tmp_path / "dummy.txt"
    test_filename.write_text("Duh")

    with pytest.raises(GitRepoError, match=r"Destination path .* exists and is a non empty directory"):
        git_mgr = GitManager(example_app_git_url, str(tmp_path))

def test_clone_remote(tmp_path, example_app_git_url):

    git_mgr = GitManager(example_app_git_url, str(tmp_path))

    check_remote_clone(git_mgr)

def test_clone_local(tmp_path):

    source_path = str(tmp_path / "source_repo")
    dest_path = str(tmp_path / "dest_repo")

    repo = init_empty_repo(source_path)

    git_mgr = GitManager(source_path, dest_path)

    check_empty_repo(git_mgr, dest_path)
