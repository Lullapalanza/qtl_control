class Setting:
    """
    A setting that has a label for tracking,
    value, setter, getter. A fundamental unit of the state
    """

    def __init__(self, init_value=None, setter=None, getter=None):
        self._value = init_value
        self._setter = setter
        self._getter = getter

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self._value = new_value
        if self._setter:
            self._setter(new_value)


class StationNode:
    def __init__(self, label):
        self._label = label
        self._subnodes = {}  # Sudnodes
        self._settings = {}  # Settings belonging to Node

    @property
    def label(self):
        return self._label

    def update_subnodes(self, new_nodes):
        for node in new_nodes:
            self._subnodes.update({node.label: node})
    
    def update_settings(self, new_settings):
        self._settings.update(new_settings)

    def change_setting(self, label, val):
        if label in self._settings.keys():
            print(self._settings[label])
            self._settings[label].value = val
        else:
            sublabel, remaining = label.split(".", 1)
            if sublabel in self._subnodes.keys():
                self._subnodes[sublabel].change_setting(remaining, val)

    def get_current_configuration(self) -> dict:
        settings = {label: st.value for label, st in self._settings.items()}
        for sn in self._subnodes.values():
            settings.update(sn.get_current_configuration())
        return {self.label: settings}

    def __str__(self):
        return f"{self.label}, {self._settings}, {self._subnodes}"


class StationNodeRef:
    def __init__(self, node):
        self._node = node

    @property
    def node(self):
        return self._node


class ControllerModule:
    """
    Self contained "module" Monoid that collects controllers of the same type
    """

    label = "ControllerModule"
    version = "0.1"

    module_controllers = {}
    module_methods = []

    def __init__(self, modules):
        self.controllers = {}

    def add_controller(self, controller_type, *args, **kwargs):
        """
        Add new controller
        """
        new_controller = self.module_controllers.get(controller_type)(*args, **kwargs)

        self.controllers[new_controller.label] = new_controller

        return new_controller


#
# ==== Mock Module definition ====
#
class MockController(StationNode):
    pass


class MockHWController(StationNode):
    def __init__(self, label, host, port):
        super().__init__(label)

        self.update_settings({
            "amplitude": Setting(0, setter=lambda x: print(f"setting MockHW amplitude to {x}"), getter=None),
        })


class MockCombinedController(StationNode):
    def __init__(self, label, controller_0, controller_1):
        super().__init__(label)

        self.update_subnodes([
            controller_0,
            controller_1
        ])


class MockModule(ControllerModule):
    label = "MockModule"
    module_controllers = {
        "MockController": MockController,
        "MockHWController": MockHWController,
        "MockCombinedController": MockCombinedController,
    }
    module_methods = []
