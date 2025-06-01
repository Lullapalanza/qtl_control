from qm import QuantumMachinesManager
# from qm.octave import QmOctaveConfig

from qtl_control.controller_module import (
    Setting,
    StationNode,
    StationNodeRef,
    ControllerModule,
)
from qtl_control.qtl_qm.utils import get_config

import sys
import atexit
import signal
def kill_handler(*args):
    sys.exit(0)

signal.signal(signal.SIGINT, kill_handler)
signal.signal(signal.SIGTERM, kill_handler)


class QMManager(StationNode):
    """
    QMManager class of OPX + Octave that distributes other channels
    """

    def __init__(self, label, host, port, cluster_name, octave_label):
        super().__init__(label)

        # self.octave_config = QmOctaveConfig()
        # self.octave_config.add_device_info(octave_label, octave_ip, 80)
        # self.octave_label = octave_label
        from qm.octave import QmOctaveConfig

        octave_config = QmOctaveConfig()
        octave_config.set_calibration_db("")
        self.qm_manager = QuantumMachinesManager(
            host=host, port=port, cluster_name=cluster_name, octave=octave_config
        )

        self.config = get_config()
        self.qm = self.qm_manager.open_qm(self.config)


        def exit_handler():
            print("Cleaning up, closing QM")
            self.qm.close()

        atexit.register(exit_handler)


    def reload_config(self, new_lo_frequency):
        self.qm.close()
        self.qm = self.qm_manager.open_qm(get_config(new_lo_frequency))

    def get_channel(self):
        pass


class QMChannel(StationNode):
    def __init__(self, label, qm_manager: StationNodeRef):
        super().__init__(label)


class QuantumMachinesModule(ControllerModule):
    label = "QuantumMachineModule"
    module_controllers = {
        "QMManager": QMManager,
        "QMChannel": QMChannel,
    }
    module_methods = []
