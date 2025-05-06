import os
import requests
from typing import Any, Dict, Union, cast
from requests.models import Response


class HttpClient:
    def __init__(self, default_headers: Union[Dict[str, str], None] = None) -> None:
        if default_headers is None:
            default_headers = {}
        self._headers = default_headers


    def get(self, *args: Any, **kwargs: Any) -> Response:
        kwargs.setdefault('headers', {})
        kwargs['headers'] = {**self._headers, **kwargs['headers']}
        return requests.get(*args, **kwargs) # type: ignore


    def post(self, *args: Any, **kwargs: Any) -> Response:
        kwargs.setdefault('headers', {})
        kwargs['headers'] = {**self._headers, **kwargs['headers']}
        return requests.post(*args, **kwargs) # type: ignore


    def delete(self, *args: Any, **kwargs: Any) -> Response:
        kwargs.setdefault('headers', {})
        kwargs['headers'] = {**self._headers, **kwargs['headers']}
        return requests.delete(*args, **kwargs) # type: ignore


    def put(self, *args: Any, **kwargs: Any) -> Response:
        kwargs.setdefault('headers', {})
        kwargs['headers'] = {**self._headers, **kwargs['headers']}
        return requests.put(*args, **kwargs) # type: ignore


    def patch(self, *args: Any, **kwargs: Any) -> Response:
        kwargs.setdefault('headers', {})
        kwargs['headers'] = {**self._headers, **kwargs['headers']}
        return requests.patch(*args, **kwargs) # type: ignore


    def download(self, url: str, destination_dir: str, *args: Any, **kwargs: Any):
        file_name = url.split('/')[-1]
        file_path = os.path.join(destination_dir, file_name)

        with self.get(url, stream=True, *args, **kwargs) as r:
            r.raise_for_status()
            with open(file_path, 'wb') as file:
                for chunk in r.iter_content(chunk_size=10*1024): # type: ignore
                    chunk = cast(bytes, chunk)
                    file.write(chunk)
        return file_path
