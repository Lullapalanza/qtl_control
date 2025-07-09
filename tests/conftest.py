import pytest

from pathlib import Path
from qtl_control.start import start_station


@pytest.fixture
def station():
    station = start_station(
        config=str(Path(__file__).parent / "test_station.yaml"),
        db_path="tests/",
        db_name="test_db"
    )
    station.reload_config(["Q7"])
    return station