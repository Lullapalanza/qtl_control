"""
Defined station which does station stuff based on a configuriation. Collects together some controller modules
"""

import yaml
import importlib

from qtl_control.controller_module import StationNode


class UndefinedController(Exception):
    pass


def generate_modules(module_data):
    modules = []
    for module_name, path in module_data.items():
        ct_module_import = importlib.import_module(path)
        ct_module = getattr(ct_module_import, module_name)
        modules.append(ct_module(modules))

    return modules


def get_controller(
    modules, controller_name, values, existing_controllers, controller_refrences
):
    controller_type = values.pop("type")
    for cm in modules:
        if controller_type in cm.module_controllers.keys():
            # Controller is with this module
            for key, value in values.items():
                if type(value) != str:  # If str might point to a different controller
                    continue
                if value in existing_controllers.keys():
                    values[key] = existing_controllers.pop(
                        value
                    )  # Existing controller ownership is given to new ct

                # elif value in controller_refrences.keys():
                #     controller_refrences[key] = controller_refrences[value] # Existing controller stays the same, only the ref is given to new ct

            new_controller = cm.add_controller(
                controller_type, controller_name, **values
            )

            return {new_controller.label: new_controller}

    raise UndefinedController(f"Undefined {controller_name}")


def generate_controllers(config_data):
    # Get modules
    modules = config_data.get("ControllerModules")
    controller_modules = generate_modules(modules)

    new_tree = StationNode("root")
    new_controllers = dict()
    controller_refrences = dict()

    for controller_name, values in config_data.get("controllers").items():
        new_controllers.update(
            get_controller(
                controller_modules,
                controller_name,
                values,
                new_controllers,
                controller_refrences,
            )
        )

    print(new_controllers)

    new_tree.update_subnodes(list(new_controllers.values()))

    return new_tree, controller_modules


def parse_config_to_station(config_file):
    with open(config_file, "r") as f:
        config_data = yaml.safe_load(f)

    ct, ct_modules = generate_controllers(config_data)

    return Station(ct, ct_modules)


class Station:
    def __init__(self, controller_tree, controller_modules):
        self._controller_root: StationNode = controller_tree
        self._controller_modules = controller_modules
        self._configuration_cache = {}
        self._current_configuration = None

    def get_module_names(self):
        return [ct_module.label for ct_module in self._controller_modules]

    def new_configuration(self, configuration_name):
        # Return config if exists
        if configuration_name in self._configuration_cache.keys():
            return configuration_name, self._configuration_cache[configuration_name]

        # Get a new config
        new_config = self._controller_root.get_current_configuration()
        self._configuration_cache[configuration_name] = new_config
        self._current_configuration = configuration_name
        return configuration_name, new_config
