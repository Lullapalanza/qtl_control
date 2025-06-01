from qtl_control.backend.controller_module import Setting

def test_setting():
    setting = Setting(5e9)
    assert setting.value == 5e9

    setting.value = 4e9
    assert setting.value == 4e9

