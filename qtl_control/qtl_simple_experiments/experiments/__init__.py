from .qubit_experiments import (
    QubitSpectroscopy,
    FluxQubitSpectrsocopy,
    Rabi,
    TimeRabi,
    Ramsey2F,
    T1,
    SingleShotReadout
)
from .resonator_experiments import (
    ReadoutResonatorSpectroscopy,
    ReadoutFluxSpectroscopy,
    DispersiveShift
)

# For reconstructing datasets
experiment_list = [
    QubitSpectroscopy,
    FluxQubitSpectrsocopy,
    Rabi,
    TimeRabi,
    Ramsey2F,
    T1,
    SingleShotReadout,

    ReadoutResonatorSpectroscopy,
    ReadoutFluxSpectroscopy,
    DispersiveShift
]

experiment_dict = {exp.experiment_name: exp for exp in experiment_list}