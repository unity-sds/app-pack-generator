import requests
import datetime
import yaml

class Util:

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
