import numpy as np

from qtl_control.qtl_experiments import QTLQMExperiment

from qm.qua import *
from qualang_tools.loops import from_array
from qtl_control.qtl_experiments.utils import standard_readout, format_res


# Define matrices
I_m = np.array([[1, 0], [0, 1]])
X_m = np.array([[0, -1.j], [-1.j, 0]])
Y_m = np.array([[0, -1], [1, 0]])

Xh_m = np.sqrt(2) * np.array([
    [1, -1.j],
    [-1.j, 1]
]) / 2
Xhm_m = np.conjugate(Xh_m)

Yh_m = np.sqrt(2) * np.array([
    [1, -1],
    [1, 1]
]) / 2
Yhm_m = np.transpose(np.conjugate(Yh_m))
# Yhm_m = np.sqrt(2) * np.array([
#     [1, 1],
#     [-1, 1]
# ]) / 2


CLIFFORDS = [
    I_m, # 0 Id
    X_m, # 1, X180
    Y_m, # 2, Y180
    Y_m @ X_m, # 3 Y180, X180

    Yh_m @ Xh_m, # 4 x90, y90
    Yhm_m @ Xh_m, # 5 x90, -y90
    Yh_m @ Xhm_m, # 6 -x90, y90
    Yhm_m @ Xhm_m, # 7  -x90, -y90

    Xh_m @ Yh_m, #8 y90, x90
    Xhm_m @ Yh_m, #9 y90, -x90
    Xh_m @ Yhm_m, #10 -y90, x90
    Xhm_m @ Yhm_m, #11 -y90, -x90

    Xh_m, #12 x90
    Xhm_m, #13 -x90
    Yh_m, #14 y90
    Yhm_m, #15 -y90

    Xh_m @ Yh_m @ Xhm_m, #16 
    Xh_m @ Yhm_m @ Xhm_m, #17
    Yh_m @ X_m, #18
    Yhm_m @ X_m, #19

    Xh_m @ Y_m, #20
    Xhm_m @ Y_m, #21
    Xh_m @ Yh_m @ Xh_m, #22
    Xhm_m @ Yh_m @ Xhm_m, #23
]

GATE_TABLE = []
for i in range(24):
    GATE_TABLE.append([])
    for j in range(24):
        new_gate = CLIFFORDS[i] @ CLIFFORDS[j]
        for _ in range(24):
            if np.allclose(new_gate, CLIFFORDS[_]) or np.allclose(-new_gate, CLIFFORDS[_]):
                GATE_TABLE[i].append(_)

INVERSE_GATES = []
for i in range(24):
    op = CLIFFORDS[i]
    invop = np.transpose(np.conjugate(op))
    for j in range(24):
        if np.allclose(invop, CLIFFORDS[j]) or np.allclose(-invop, CLIFFORDS[j]):
            INVERSE_GATES.append(j)

def get_sequence_inverse(sequence):
    op = 0
    for i in sequence[::-1]:
        op = GATE_TABLE[op][i]
    return INVERSE_GATES[op]

def generate_sequence_for_depth(depth):
    sequence = np.random.randint(24, size=depth-1).tolist()
    inverse = get_sequence_inverse(sequence)
    sequence.append(inverse)
    return sequence

def play_sequence(sequence_list, start, N, element):
    i = declare(int)
    with for_(i, start, i < N + start, i+1):
        with switch_(sequence_list[i], unsafe=True):
            with case_(0):
                wait(100//4, f"drive_{element}")
            with case_(1):
                play(f"{element}_x180", f"drive_{element}")
            with case_(2):
                play(f"{element}_y180", f"drive_{element}")
            with case_(3):
                play(f"{element}_y180", f"drive_{element}")
                play(f"{element}_x180", f"drive_{element}")
            with case_(4):
                play(f"{element}_x90", f"drive_{element}")
                play(f"{element}_y90", f"drive_{element}")
            with case_(5):
                play(f"{element}_x90", f"drive_{element}")
                play(f"{element}_-y90", f"drive_{element}")
            with case_(6):
                play(f"{element}_-x90", f"drive_{element}")
                play(f"{element}_y90", f"drive_{element}")
            with case_(7):
                play(f"{element}_-x90", f"drive_{element}")
                play(f"{element}_-y90", f"drive_{element}")
            with case_(8):
                play(f"{element}_y90", f"drive_{element}")
                play(f"{element}_x90", f"drive_{element}")
            with case_(9):
                play(f"{element}_y90", f"drive_{element}")
                play(f"{element}_-x90", f"drive_{element}")
            with case_(10):
                play(f"{element}_-y90", f"drive_{element}")
                play(f"{element}_x90", f"drive_{element}")
            with case_(11):
                play(f"{element}_-y90", f"drive_{element}")
                play(f"{element}_-x90", f"drive_{element}")
            with case_(12):
                play(f"{element}_x90", f"drive_{element}")
            with case_(13):
                play(f"{element}_-x90", f"drive_{element}")
            with case_(14):
                play(f"{element}_y90", f"drive_{element}")
            with case_(15):
                play(f"{element}_-y90", f"drive_{element}")
            with case_(16):
                play(f"{element}_-x90", f"drive_{element}")
                play(f"{element}_y90", f"drive_{element}")
                play(f"{element}_x90", f"drive_{element}")
            with case_(17):
                play(f"{element}_-x90", f"drive_{element}")
                play(f"{element}_-y90", f"drive_{element}")
                play(f"{element}_x90", f"drive_{element}")
            with case_(18):
                play(f"{element}_x180", f"drive_{element}")
                play(f"{element}_y90", f"drive_{element}")
            with case_(19):
                play(f"{element}_x180", f"drive_{element}")
                play(f"{element}_-y90", f"drive_{element}")
            with case_(20):
                play(f"{element}_y180", f"drive_{element}")
                play(f"{element}_x90", f"drive_{element}")
            with case_(21):
                play(f"{element}_y180", f"drive_{element}")
                play(f"{element}_-x90", f"drive_{element}")
            with case_(22):
                play(f"{element}_x90", f"drive_{element}")
                play(f"{element}_y90", f"drive_{element}")
                play(f"{element}_x90", f"drive_{element}")
            with case_(23):
                play(f"{element}_-x90", f"drive_{element}")
                play(f"{element}_y90", f"drive_{element}")
                play(f"{element}_-x90", f"drive_{element}")


class SingleQubitRB(QTLQMExperiment):
    experiment_name = "QM-SQRB"

    def sweep_labels(self):
        return [("clifford_depth", ""), ]

    def get_program(self, element, Navg, sweeps, wait_after=50000):
        depth_sweep = sweeps[0]
        depth_sequencies = []
        for d in depth_sweep:
            seq = generate_sequence_for_depth(d)
            print(seq)
            depth_sequencies += seq

        seq_indexes = [0] + [sum(depth_sweep[:_]) for _ in range(1, len(depth_sweep))]

        with program() as rb_prog:
            i = declare(int)
            
            I = declare(fixed)
            Q = declare(fixed)
            n = declare(int)

            I_stream = declare_stream()
            Q_stream = declare_stream()
            n_stream = declare_stream()
            
            depths = declare(int, value=depth_sweep.tolist())
            depth_seqs = declare(int, value=depth_sequencies)
            seqs_ind = declare(int, value=seq_indexes)


            with for_(n, 0, n < Navg, n+1):
                with for_(i, 0, i < len(depth_sweep), i+1):
                    align(f"drive_{element}", f"resonator_{element}")
                    with strict_timing_():
                        play_sequence(depth_seqs, seqs_ind[i], depths[i], element)
                    wait(100, f"drive_{element}") # 400ns
                    align(f"drive_{element}", f"resonator_{element}")
                    standard_readout(f"resonator_{element}", I, I_stream, Q, Q_stream, wait_after)
                    align(f"drive_{element}", f"resonator_{element}")
                save(n, n_stream)
        
            with stream_processing():
                I_stream.buffer(len(depth_sweep)).average().save("I")
                Q_stream.buffer(len(depth_sweep)).average().save("Q")
                n_stream.save("iteration")
        
        return rb_prog
    
