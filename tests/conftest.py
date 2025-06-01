import pytest

from pathlib import Path
from qtl_control.station import parse_config_to_station


@pytest.fixture
def station():
    return parse_config_to_station(
        str(Path(__file__).parent / "test_station.yaml")
    )