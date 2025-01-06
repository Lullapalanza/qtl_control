from qtl_control.controller_module import Setting

def test_setting():
    setting = Setting("setting_0", 5e9)
    assert setting.label == "setting_0"
    assert setting.value == 5e9

    setting.value = 4e9
    assert setting.value == 4e9

