"""Fixtures for pytest."""

import contextlib
from unittest import mock

import pytest


@pytest.fixture(scope="session")
def mock_client_factory():
    """Factory to create a mock client for httpx.

    The AClient will always produce the response invariant of http method.
    """

    @contextlib.contextmanager
    def create(response):
        def areturn(*_, **__):
            return response

        def call(*_, **__):
            return areturn

        def consume(*_, **__): ...

        def self(self, *_, **__):
            return self

        MockClient = type(
            "MockAsyncClient",
            (contextlib.AbstractContextManager,),
            {
                "__getattribute__": call,
                "__init__": consume,
                "__enter__": self,
                "__exit__": consume,
            },
        )
        with mock.patch("httpx.Client", MockClient):
            yield

    return create
