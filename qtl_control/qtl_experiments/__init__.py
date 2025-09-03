from .experiment import QTLQMExperiment, ExperimentResult
from .qubit_experiments import (
    QubitSpectroscopy,
    FluxQubitSpectrsocopy,
    Rabi,
    TimeRabi,
    Ramsey2F,
    T1,
    SingleShotReadout,
    ReadoutOptimization,
    ErrorRabi,
    DragCalibration,
    AllXY
)
from .resonator_experiments import (
    ReadoutResonatorSpectroscopy, ReadoutFluxSpectroscopy, PunchOut, DispersiveShift
)
from .single_qubit_rb import (
    SingleQubitRB
)

experiments_dict = {
    exp.experiment_name: exp for exp in [
        QubitSpectroscopy,
        FluxQubitSpectrsocopy,
        Rabi,
        TimeRabi,
        Ramsey2F,
        T1,
        SingleShotReadout,
        ReadoutOptimization,
        ErrorRabi,
        DragCalibration,
        AllXY
    ] + [
        ReadoutResonatorSpectroscopy,
        ReadoutFluxSpectroscopy,
        PunchOut,
        DispersiveShift
    ] + [
        SingleQubitRB
    ]
}