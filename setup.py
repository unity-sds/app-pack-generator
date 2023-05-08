"""Install packages as defined in this file into the Python environment."""
from setuptools import setup, find_packages

# The version of this tool is based on the following steps:
# https://packaging.python.org/guides/single-sourcing-package-version/
VERSION = {}

with open("./app_pack_generator/version.py") as fp:
    # pylint: disable=W0122
    exec(fp.read(), VERSION)

setup(
    name="app_pack_generator",
    author="Max Zhan, James McDuffie",
    url="https://github.com/unity-sds/app-pack-generator",
    description="Generates an application package from a Jupyter Notebook by parsing its contents metadata.",
    version=VERSION.get("__version__", "0.0.0"),
    packages=find_packages(where=".", exclude=["tests"]),
    include_package_data=True,
    package_data={"app_pack_generator": ["schemas/*", "templates/*"]},
    install_requires=[
        "setuptools>=45.0",
        "papermill>=2.4.0",
        "GitPython>=3.1.30",
        "docker>=6.0.1",
        "jsonschema>=4.17.3",
        "jupyter-repo2docker>=2022.10.0",
        "giturlparse==0.10.0",
    ],
    classifiers=[
        "Development Status :: 1 - Planning",
        "Programming Language :: Python :: 3.0",
        "Topic :: Utilities",
    ],
)
