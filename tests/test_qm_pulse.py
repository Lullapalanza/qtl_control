from qtl_control.qtl_experiment.experiments import ReadoutResonatorSpectroscopy

def test_experiment(station):
    ro_spec = ReadoutResonatorSpectroscopy()
    ro_spec.default_station = station
    ro_spec.run("qubit_0")

