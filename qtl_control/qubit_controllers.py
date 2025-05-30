from qtl_control.controller_module import (
    Setting,
    StationNode,
    StationNodeRef,
    ControllerModule,
)
from qtl_control.qtl_qm.utils import READOUT_LEN, u
from qualang_tools.results import progress_counter, fetching_tool

class PulseSequence:
    pass

class TransmonQubit(StationNode):
    # TODO: FIX qm to more generic interface
    def __init__(self, label, qm_manager):
        super().__init__(label)

        self.qm_manager = qm_manager

        def set_lo_freq(new_freq):
            self.qm_manager.reload_config(new_freq)

        self.update_settings({
            "readout_LO_frequency": Setting(5.9e9, setter=set_lo_freq),
        })

        



class PulsedQubits(ControllerModule):
    label = "PulsedQubits"
    module_controllers = {
        "TransmonQubit": TransmonQubit,
    }
    module_methods = [
        "run"
    ]

    # TODO: This should be more generic, but oh well, qm programms it is
    def execute_program(self, component, qm_program):
        """
        pulses: dict of components corresponding to readout, flux and drive channels and pulse sequences
        """
        qm = self.controllers[component].qm_manager.qm
        job = qm.execute(qm_program)
        
        from qm import generate_qua_script
        sourceFile = open("debug.py", "w")
        print(generate_qua_script(qm_program, self.controllers[component].qm_manager.config), file=sourceFile)
        sourceFile.close()

        results = fetching_tool(job, data_list=["I", "Q", "iteration"], mode="live")
        while results.is_processing():
            I, Q, iteration = results.fetch_all()
            S = u.demod2volts(I + 1.j * Q, READOUT_LEN)
            progress_counter(iteration, 1024 * 2, start_time=results.get_start_time())

        return S