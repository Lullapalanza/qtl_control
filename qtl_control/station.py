"""
Defined station which does station stuff based on a configuriation. Collects together some controller modules
"""

import yaml
import importlib

from qtl_control.controller_module import StationNode


class UndefinedController(Exception):
    pass


def generate_modules(module_data):
    modules = {}
    for module_name, path in module_data.items():
        ct_module_import = importlib.import_module(path)
        ct_module = getattr(ct_module_import, module_name)
        modules.update({module_name: ct_module(modules)})

    return modules


def get_controller(
    modules, controller_name, values, existing_controllers, controller_refrences
):
    controller_type = values.pop("type")
    for cm in modules.values():
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
        self._current_configuration_name = None

    def get_module_names(self):
        return self._controller_modules.keys()

    def get_module_methods(self, module_name):
        return self._controller_modules[module_name].module_methods

    def run_module_method(self, module_name, method_name, *args, **kwargs):
        return getattr(self._controller_modules[module_name], method_name)(*args, **kwargs)

    def new_configuration(self, configuration_name):
        # Return config if exists
        if configuration_name in self._configuration_cache.keys():
            return configuration_name, self._configuration_cache[configuration_name]

        # Get a new config
        new_config = self._controller_root.get_current_configuration()
        self._configuration_cache[configuration_name] = new_config
        self._current_configuration_name = configuration_name
        return configuration_name, new_config
    
    def get_configuration(self):
        return self._configuration_cache[self._current_configuration_name]


    # TODO: Make this infinitely nicer
    def force_update_settings_from_cache(self, settings_to_update):
        for setting in settings_to_update:
            root = self._configuration_cache[self._current_configuration_name]["root"]
            remaining = setting
            while True:
                if "." not in remaining:
                    self._controller_root.change_setting(setting, root[remaining])
                    return
                next_label, remaining = remaining.split(".", 1)
                root = root[next_label]

    def change_settings(self, new_settings_and_values: dict, update_cache=True):
        for setting_label, value in new_settings_and_values.items():
            # Change setting
            self._controller_root.change_setting(setting_label, value)

            # Update cache, also validate?
            # TODO: A interface for the config?
            if update_cache:
                root = self._configuration_cache[self._current_configuration_name]["root"]
                remaining = setting_label
                while True:
                    if "." not in remaining:
                        root[remaining] = value
                        return
                    next_label, remaining = remaining.split(".", 1)
                    root = root[next_label]

    def external_sweeps(self, list_of_new_settings_and_values, module_name, module_method, *args, **kwargs):
        results = []
        settings_changed = set()
        for settings_and_values in list_of_new_settings_and_values:
            # Change settings temporarily? Keep list of settings to change back later
            self.change_settings(settings_and_values, update_cache=False)
            settings_changed.update(settings_and_values.keys())
            results.append(
                self.run_module_method(module_name, module_method, *args, **kwargs)
            )
        
        self.force_update_settings_from_cache(settings_changed)

        return results
