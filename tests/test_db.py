from qtl_control.qtl_experiments import ExperimentResult

def test_db(station):
    db = ExperimentResult.db
    db.load_result(0)