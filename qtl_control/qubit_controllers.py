from qtl_control.controller_module import (
    Setting,
    StationNode,
    StationNodeRef,
    ControllerModule,
)
from qtl_control.qtl_qm.utils import READOUT_LEN, u

class PulseSequence:
    pass

class TransmonQubit(StationNode):
    # TODO: FIX qm to more generic interface
    def __init__(self, label, qm_manager):
        super().__init__(label)

        self.qm_manager = qm_manager

        self.update_settings([
            Setting("qubit_frequency", ),
            Setting("readout_frequency", )
        ])

        



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
        qm_manager = self.controllers[component].qm_manager
        job = qm_manager.execute(qm_program)
        
        results = job.result_handles
        while results.is_processing():
            I, Q, iteration = results.fetch_all()

            S = u.demod2volts(I + 1.j * Q, READOUT_LEN)

        return S