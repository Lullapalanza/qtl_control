class QTLExperiment:
    """
    An experiment instance that allows to predefine some operations and experiments
    """
    default_db = None
    default_station = None

    def run(self, autosave=True):
        pass

class VNATrace(QTLExperiment):
    experiment_name = "VNATrace"

    def run(self, vna_name, parameter=None, sweep_points=None):
        if parameter is None:
            sweep_points = []
        # Run experiment
        data = self.default_station.external_sweeps(
            [{parameter: sp for sp in sweep_points}],
            "RandSModule",
            "get_frequency_trace",
            vna_name
        )

        saved_id = self.default_db.save_data(
            self.experiment_name,
            data,
            [(parameter, sweep_points), ],
        )

        return saved_id, data, [(parameter, sweep_points)]
    
    def analyze(self):
        pass


class SingleQubitRB(QTLExperiment):
    experiment_name = "SingleQubitRB"

    def run(self, controller_name, nr_of_iterations):
        full_data = None
        for i in nr_of_iterations:
            new_hash = ...
            new_sqrb_sequence = ...

            # station.run(...)

        self.default_db.save_data(
            self.experiment_name,
            full_data,
            [("hash", [i for i in nr_of_iterations])]
        )