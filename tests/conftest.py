import pytest


@pytest.fixture(autouse=True, scope='session')
def isolated_user_data(tmp_path_factory):
    """Never touch the real user data folder (%LOCALAPPDATA%/OTECImpronta) from tests."""
    mp = pytest.MonkeyPatch()
    mp.setenv('OTEC_DATA_DIR', str(tmp_path_factory.mktemp('user_data')))
    yield
    mp.undo()
