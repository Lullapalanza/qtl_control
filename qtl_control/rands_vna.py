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


    def get_trace(self):
        """
        Return trace
        """
        return None



class RandSModule(ControllerModule):
    label = "RhodeAndShwarzModule"
    module_controllers = {
        "ZNB": ZNBVNA,
    }
    module_methods = [
        "get_sweep"
    ]
