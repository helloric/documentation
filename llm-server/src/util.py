from flask import Request
from typing_extensions import Self
from typing import Any, Callable, TypeAlias
from pathlib import Path
import os

RestError: TypeAlias = tuple[dict, int] | None


ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))


def get_resource(path: str) -> str:
    return f'{ROOT_DIRECTORY}/resources/{path}'


class RestMaybe:
    """RestMaybe is a class that should make checking if the request is valid easier.

    Currently, the capabilities of RestMaybe are limited to checking if a given request is a Json and if a given request has valid keys.
    """

    def __init__(self, request: Request) -> None:
        """Passes initial Request to the RestMaybe.

        Args:
            request (Request): The sent HTTP Request to handle.
        """
        self.request = request
        self.json = request.get_json(silent=True)
        self.request_object = {}
        self.error = None

    def wellformed(self) -> Self:
        """Checks if the HTTP Request is a Json. Modifies the error variable, if not.

        Returns:
            self (Self): Itself to chain the next call.
        """
        if not self.error is None:
            return self
        if self.json is None:
            self.error: RestError = ({'error': 'Request Body is not a json.'}, 400)
        return self

    def exists(self, key: str) -> Self:
        """Checks if a given key exists in the request Json. Modifies the error variable, if not.

        !!! warning
            This function will not check if the request was a Json in the first place. Use `wellformed` first.

        Args:
            key (str): The key to check for if it is in the request.

        Returns:
            self (Self): Itself to chain the next call.
        """
        if not self.error is None:
            return self
        if self.json.get(key) is None:  # type: ignore
            self.error: RestError = ({'error': f'Property "{key}" missing.'}, 400)
        else:
            self.request_object.update({key: self.json.get(key)})  # type: ignore
        return self

    def optional(self, key: str) -> Self:
        """Collects an optional key. Will not throw an error if the key isn't passed.

        !!! warning
            This function will not check if the request was a Json in the first place. Use `wellformed` first.

        Args:
            key (str): The key to check for if it is in the request.

        Returns:
            self (Self): Itself to chain the next call.
        """
        if not self.error is None:
            return self
        if self.json.get(key) is None:  # type: ignore
            self.request_object.update({key: None})
        else:
            self.request_object.update({key: self.json.get(key)})  # type: ignore
        return self

    def run(self, function: Callable[[Request, Any], Any]):
        """If every check made was true, this function will call another function that the user can pass. If not, the error will be returned directly.

        Args:
            function (Callable[[Request, Any], Any]): The function `f : Request -> Json -> Response`, which takes in the request
                and the value for every key checked before and gives out any response at will.

        Returns:
            response: A valid Flask Response.
        """
        if not self.error is None:
            return self.error
        return function(self.request, self.request_object)
