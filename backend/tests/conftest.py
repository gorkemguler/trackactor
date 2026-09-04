import os
import shutil
import tempfile

import pytest

# Point the app at throwaway storage before it is imported. A DB URL from the
# environment wins (CI runs the suite against Postgres too).
_data_dir = tempfile.mkdtemp(prefix="trackactor-test-")
os.environ["TRACKACTOR_DATA_DIR"] = _data_dir
if not os.environ.get("TRACKACTOR_DB_URL"):
    _tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _tmp.close()
    os.environ["TRACKACTOR_DB_URL"] = f"sqlite:///{_tmp.name}"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    shutil.rmtree(os.path.join(_data_dir, "attachments"), ignore_errors=True)


@pytest.fixture
def client():
    return TestClient(app)
