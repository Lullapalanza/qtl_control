from qtl_control.controller_module import (
    Setting,
    StationNode,
    StationNodeRef,
    ControllerModule,
)

class PulseSequence:
    pass

class TransmonQubit(StationNode):
    def __init__(self, label, drive_channel, readout_channel: StationNodeRef):
        super().__init__(label)

        self.update_settings([
            Setting("qubit_frequency"),
        ])


class Qubits(ControllerModule):
    label = "Qubits"
    module_controllers = {
        "TransmonQubit": TransmonQubit,
    }
    module_methods = [
        "run"
    ]

    def run(self, qubits_and_pulses):
        pass
