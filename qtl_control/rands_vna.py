from qtl_control.controller_module import (
    Setting,
    StationNode,
    StationNodeRef,
    ControllerModule,
)


class ZNBVNA(StationNode):
    def __init__(self, label, host, port):
        super().__init__(label)
        self.host = host
        self.port = port

        self.update_settings({
            "span": Setting(...),
            "center_frequency": Setting(...),
            "power": Setting(...)
        })

    def get_frequency_trace(self):
        """
        Return trace of frequency vs s-parameter
        """
        frequency = []
        Sparam = []
        # TODO actually get a trace
        return frequency, Sparam


class ZNBVNAMock(StationNode):
    def __init__(self, label, host, port):
        super().__init__(label)
        self.host = host
        self.port = port

        self.update_settings({
            "span": Setting(...),
            "center_frequency": Setting(...),
            "power": Setting(...)
        })

    def get_frequency_trace(self):
        """
        Return trace of frequency vs s-parameter
        """
        frequency = [6e9, 6.1e9, 6.2e9]
        Sparam = [3+0.j, 2+0.1j, 5-0.7j]
        return frequency, Sparam


class RandSModule(ControllerModule):
    label = "RhodeAndShwarzModule"
    module_controllers = {
        "ZNB": ZNBVNA,
        "ZNBMock": ZNBVNAMock
    }
    module_methods = [
        "get_frequency_trace"
    ]

    def get_frequency_trace(self, vna_name):
        return self.controllers[vna_name].get_frequency_trace()

