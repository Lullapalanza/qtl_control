from qm import QuantumMachinesManager
from qm.octave import QmOctaveConfig

from qm.qua import *
from qualang_tools.loops import from_array
from qualang_tools.results import progress_counter, fetching_tool
from qualang_tools.units import unit
u = unit(coerce_to_integer=True)

from qtl_control.backend.controller_module import (
    Setting,
    StationNode,
    StationNodeRef,
    ControllerModule,
)
from qtl_control.backend.qtl_qm.qm_config import get_config
from qtl_control.backend.qubit_controllers import PlaylistOp

import sys
import atexit
import signal
def kill_handler(*args):
    sys.exit(0)
signal.signal(signal.SIGINT, kill_handler)
signal.signal(signal.SIGTERM, kill_handler)


class QMOPXManager(StationNode):
    """
    QMManager class of OPX + Octave that distributes other channels
    """

    def __init__(self, label, host, port, cluster_name):
        super().__init__(label)

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

class QMOPXManagerMock(StationNode):
    """
    QMManager class of OPX + Octave that distributes other channels
    """

    def __init__(self, label, host, port, cluster_name):
        super().__init__(label)

    def reload_config(self, new_lo_frequency):
        pass

    def get_channel(self):
        pass


def get_program_from_playlist(playlist, Navg, data_dims, readout_LO):
    with program() as built_prog:
        n = declare(int)
        I = declare(fixed)
        Q = declare(fixed)
        I_st = declare_stream()  # Stream for the 'I' quadrature
        Q_st = declare_stream()  # Stream for the 'Q' quadrature
        n_st = declare_stream()  # Stream for the averaging iteration 'n'

        with for_(n, 0, n < Navg, n + 1):
            for op in playlist:
                if op[0] == PlaylistOp.readout:
                    measure(
                        "readout",
                        "resonator",
                        None,
                        dual_demod.full("cos", "sin", I),
                        dual_demod.full("minus_sin", "cos", Q),
                    )
                elif op[0] == PlaylistOp.change_drive_frequency:
                    update_frequency("drive", op[1])

                elif op[0] == PlaylistOp.change_readout_frequency:
                    update_frequency("readout", op[1] - readout_LO.value)

                elif op[0] == PlaylistOp.play_pulse:
                    play(op[1] * amp(op[2]), "drive", duration=op[3])

            save(n, n_st)
        with stream_processing():
            # Cast the data into a 1D vector, average the 1D vectors together and store the results on the OPX processor
            I_st.buffer(len(data_dims)).average().save("I")
            Q_st.buffer(len(data_dims)).average().save("Q")
            n_st.save("iteration")
        
    return built_prog

class QMOPXReadoutChannel(StationNode):
    def __init__(self, label, qm_manager: StationNodeRef, channel_in, channel_out):
        super().__init__(label)

        self.channel = qm_manager.get_channel()

        self.update_settings({
            "readout_LO_frequency": Setting(),
            "readout_IF_frequency": Setting(),
            "readout_pulse_amplitude": Setting(),
            "readout_output_gain": Setting(),
            "readout_length": Setting()
        })

    def set_frequency(self, target_f):
        self._settings["readout_IF_frequency"].value(
            target_f - self._settings["readout_LO_frequency"].value()
        )

    def execute_playlist(self, playlist, Navg, data_dims):
        program = get_program_from_playlist(playlist, Navg, data_dims, self._settings["readout_LO_frequency"])

        job = self.qm_manager.execute(program)
        results = fetching_tool(
            job, data_list=["I", "Q", "iteration"], mode="live"
        )
        
        while results.is_processing():
            I, Q, iteration = results.fetch_all()
            S = u.demod2volts(I + 1.j * Q, self._settings["readout_length"])
            progress_counter(iteration, Navg, start_time=results.get_start_time())

        return S            


class QMOPXDriveChannel(StationNode):
    def __init__(self, label, qm_manager: StationNodeRef, channel_out):
        super().__init__(label)

        self.channel = qm_manager.get_channel()

        self.update_settings({
            "drive_LO_frequency": Setting(4.2e9),
            "drive_IF_frequency": Setting(-200e6),
        })

    def set_frequency(self, target_f):
        self._settings["drive_IF_frequency"] = target_f - self._settings["drive_LO_frequency"]

    def update_playlist(self, playlist):
        pass


class QuantumMachinesModule(ControllerModule):
    label = "QuantumMachineModule"
    module_controllers = {
        "QMOPXManager": QMOPXManager,
        "QMOPXManagerMock": QMOPXManagerMock,
        "QMOPXDriveChannel": QMOPXDriveChannel,
        "QMOPXReadoutChannel": QMOPXReadoutChannel,
    }
    module_methods = []
