import numpy as np

from qtl_control.qtl_experiments.single_qubit_rb import CLIFFORDS, GATE_TABLE, INVERSE_GATES, get_sequence_inverse, generate_sequence_for_depth

def test_CLIFFORDS():
    assert np.allclose((CLIFFORDS[1] @ CLIFFORDS[1]), -CLIFFORDS[0])

def test_table_sizes():
    assert len(CLIFFORDS) == 24
    
    assert len(GATE_TABLE) == 24
    for i in range(24):
        print(i, GATE_TABLE[i])
        assert len(GATE_TABLE[i]) == 24
    
    assert len(INVERSE_GATES) == 24

def test_sequence_inverse():
    assert get_sequence_inverse([0, 0]) == 0
    assert get_sequence_inverse([1, 1]) == 0
    assert get_sequence_inverse([2, 2]) == 0
    assert get_sequence_inverse([1]) == 1

    assert get_sequence_inverse([13, 15]) == 8
    assert get_sequence_inverse([13, 15, 13]) == 22


def test_sequence_depth():
    assert len(generate_sequence_for_depth(5)) == 5
