import uuid
from typing import Callable

import pytest


@pytest.fixture(scope="function")
def name() -> str:
    id_ = str(uuid.uuid4())
    return ''.join(id_.split('-')[:2])


@pytest.fixture(scope="function")
def get_name() -> Callable[[], str]:
    def _get_name() -> str:
        id_ = str(uuid.uuid4())
        return ''.join(id_.split('-')[:2])
    return _get_name


@pytest.fixture(scope="function")
def remark() -> str:
    return f"test-{uuid.uuid4()}"


@pytest.fixture(scope="function")
def get_remark() -> Callable[[], str]:
    def _get_remark() -> str:
        return f"test-{uuid.uuid4()}"
    return _get_remark


@pytest.fixture(scope="function")
def category_name() -> str:
    return 'my_category'
