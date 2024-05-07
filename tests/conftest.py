"""Fixtures for pytest."""

import contextlib
from unittest import mock

import pytest


@pytest.fixture(scope="session")
def mock_async_client_factory():
    """Factory to create a mock async client for httpx.

    The AsyncClient will always produce the response invariant of http method.
    """

    @contextlib.contextmanager
    def create(response):
        async def areturn(*_, **__):
            return response

        def call(*_, **__):
            return areturn

        def consume(*_, **__): ...

        async def aconsume(*_, **__): ...
        def aself(self, *_, **__):
            return self

        def empty_generator(self, *_, **__):
            async def get_client():
                return self

            return get_client().__await__()

        MockAsyncClient = type(
            "MockAsyncClient",
            (contextlib.AbstractAsyncContextManager,),
            {
                "__getattribute__": call,
                "__init__": consume,
                "__await__": empty_generator,
                "__aenter__": aself,
                "__aexit__": aconsume,
            },
        )
        with mock.patch(
            "httpx.AsyncClient",
            MockAsyncClient,
        ):
            yield

    return create
