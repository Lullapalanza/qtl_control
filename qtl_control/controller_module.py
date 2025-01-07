class Setting:
    """
    A setting that has a label, value, setter, getter. A fundamental unit of the state
    """

    def __init__(self, label, default_value=None, setter=None, getter=None):
        self._label = label
        self._value = default_value
        self._setter = setter
        self._getter = getter

    @property
    def label(self):
        return self._label

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
        self._subnodes = []  # Sudnodes
        self._settings = []  # Settings belonging to Node

    @property
    def label(self):
        return self._label

    def update_subnodes(self, new_nodes):
        self._subnodes = self._subnodes + new_nodes

    def update_settings(self, new_settings):
        self._settings = self._settings + new_settings

    def get_current_configuration(self) -> dict:
        settings = {st.label: st.value for st in self._settings}
        for sn in self._subnodes:
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
    def __init__(self, label, driver):
        super().__init__(label)
        self._driver = driver


class MockCombinedController(StationNode):
    def __init__(self, label, controller_0, controller_1):
        super().__init__(label)
        self._ct0 = controller_0
        self._ct1 = controller_1


class MockModule(ControllerModule):
    label = "MockModule"
    module_controllers = {
        "MockController": MockController,
        "MockHWController": MockHWController,
        "MockCombinedController": MockCombinedController,
    }
    module_methods = []
