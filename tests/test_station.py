
def test_station(station):
    loaded_modules = station.get_module_names()
    assert list(loaded_modules) == ["MockModule", "RandSModule", "PulsedQubits", "QuantumMachinesModule"]
    
    name, new_config = station.new_configuration("test_user")
