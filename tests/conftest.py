import pytest

from pathlib import Path
from qtl_control.qtl_experiments.station_connection import StationConnection


@pytest.fixture
def station_w_filedb():
    station_conn = StationConnection(
        station_config_path=str(Path(__file__).parent / "test_station.yaml"),
        db_path="tests/",
        db_name="test_db"
    )
    station_conn.load_full_config(["Q7", "Q4"], "test")
    return station_conn


@pytest.fixture
def station_w_relational_db():
    station_conn = StationConnection(
        station_config_path=str(Path(__file__).parent / "test_station.yaml"),
        db_path="tests/",
        db_name="test_db_relational",
        db_type="relational"
    )
    station_conn.load_full_config(["Q7", "Q4"], "test")
    return station_conn