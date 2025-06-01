
def test_station(station):
    loaded_modules = station.get_module_names()
    assert loaded_modules == ["MockModule", ]
    
    name, new_config = station.new_configuration("test_user")
    
    # assert name == "test_user"
    # ct_tree = new_config.get_settings()