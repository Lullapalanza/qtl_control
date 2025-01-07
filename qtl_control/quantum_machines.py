from qm import QuantumMachinesManager
from qm.octave import QmOctaveConfig

from qtl_control.controller_module import (
    Setting,
    StationNode,
    StationNodeRef,
    ControllerModule,
)


class QMManager(StationNode):
    """
    QMManager class of OPX + Octave that distributes other channels
    """

    def __init__(self, label, host, port, cluster_name, octave_label, octave_ip):
        super().__init__(label)

        self.qm_manager = QuantumMachinesManager(
            host=host, port=port, cluster_name=cluster_name, octave=None
        )

        self.octave_config = QmOctaveConfig()
        self.octave_config.add_device_info(octave_label, octave_ip, 80)
        self.octave_label = octave_label

    def get_channel(self):
        pass


class QMChannel(StationNode):
    def __init__(
        self, label, qm_manager: StationNodeRef, analog_outputs, analog_inputs=None
    ):
        super().__init__(label)


class QuantumMachinesModule(ControllerModule):
    label = "QuantumMachineModule"
    module_controllers = {
        "QMManager": QMManager,
        "QMChannel": QMChannel,
    }
    module_methods = []
