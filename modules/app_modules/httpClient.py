import requests
from typing import Any, Dict, Union
from requests.models import Response


class HttpClient:
    def __init__(self, default_headers: Union[Dict[str, str], None] = None) -> None:
        if default_headers is None:
            default_headers = {}
        self._headers = default_headers

    def get(self, *args: Any, **kwargs: Any) -> Response:
        kwargs.setdefault('headers', {})
        kwargs['headers'] = {**self._headers, **kwargs['headers']}
        return requests.get(*args, **kwargs)

    def post(self, *args: Any, **kwargs: Any) -> Response:
        kwargs.setdefault('headers', {})
        kwargs['headers'] = {**self._headers, **kwargs['headers']}
        return requests.post(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> Response:
        kwargs.setdefault('headers', {})
        kwargs['headers'] = {**self._headers, **kwargs['headers']}
        return requests.delete(*args, **kwargs)

    def put(self, *args: Any, **kwargs: Any) -> Response:
        kwargs.setdefault('headers', {})
        kwargs['headers'] = {**self._headers, **kwargs['headers']}
        return requests.put(*args, **kwargs)

    def patch(self, *args: Any, **kwargs: Any) -> Response:
        kwargs.setdefault('headers', {})
        kwargs['headers'] = {**self._headers, **kwargs['headers']}
        return requests.patch(*args, **kwargs)
