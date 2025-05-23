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


def get_pulse_program(playlist, averages, internal_sweeps):
    with program() as pulse_program:
        Navg = declare(int)
        



class PulsedQubits(ControllerModule):
    label = "PulsedQubits"
    module_controllers = {
        "TransmonQubit": TransmonQubit,
    }
    module_methods = [
        "run"
    ]

    # TODO: This should be more generic, but oh well, qm programms it is
    def execute_program(self, qm_program):
        """
        pulses: dict of components corresponding to readout, flux and drive channels and pulse sequences
        """
        job = qm.execute(qm_program)
        results = job.result_handles
        while results.is_processing():
            I, Q, iteration = results.fetch_all()

            S = u.demod2volts(I + 1.j * Q, readout_length)

        return S