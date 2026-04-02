import uuid

import pytest


@pytest.fixture
def sample_claims():
    return {
        "sub": str(uuid.uuid4()),
        "email": "user@example.com",
        "org_id": str(uuid.uuid4()),
        "role": "admin",
    }
