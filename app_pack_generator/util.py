import requests
import datetime
import subprocess
import yaml

class Util:
    @staticmethod
    def System(cmd):
        """Runs a terminal commands with the specified command."""
        return subprocess.run(cmd,
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
    def GetKeyType(inferred_type, default_val):
        """Attempts to convert the inferred type to an equivalent CWL type.

        Otherwise, checks if a given key's default value is a string or can be converted to a float."""
        inferred_type = inferred_type.lower()
        convert_dict = {
            'string': ['stage_in', 'stage-in', 'string'],
            'File': ['stage_out', 'stage-out', 'file'],
            'int': ['int', 'integer'],
            'boolean': ['bool', 'boolean'],
            'float': ['float'],
            'double': ['double'],
            'Directory': ['directory'],
            'Any': ['any']
        }
        for key in convert_dict:
            if inferred_type in convert_dict[key]:
                return key

        if default_val.find('"') != -1 or default_val.find('\'') != -1:
            return 'string'
        key_type = 'Any'
        try:
            temp = float(default_val)
            key_type = 'float'
        except ValueError:
            pass
        return key_type

    @staticmethod
    def WriteYMLFile(fname, target):
        """Writes [target] dictionary to a .yml file with filename [fname]."""
        with open(fname, 'w', encoding='utf-8') as f:
            f.write("#!/usr/bin/env cwl-runner\n")
            yaml.dump(target, f, default_flow_style=False)

    @staticmethod
    def DownloadLink(url, default=None):
        """Downloads the specified URL via a GET request.

        If url is not a valid link, or if the request fails, returns the [default]
        parameter instead.
        """
        try:
            response = requests.get(url)
            if response.status_code == 404:
                raise RuntimeError('<Response 404>')
            return response
        except Exception as e:
            if url.startswith('http://') or url.startswith('https://'):
                print('Could not download assumed URL: \'' + url + '\'')
                print(e)
        return default
