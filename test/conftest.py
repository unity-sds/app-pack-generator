import pytest

@pytest.fixture(scope='session')
def example_app_git_url():
    return "https://github.com/unity-sds/unity-example-application"
