import numpy as np

from dataclasses import dataclass, fields
from typing import Optional


class StationNode:
    """
    Node from which the controllers get built from
    """
    def get_tree(self, indent=0):
        return "\n".join([
            f"{'\t'*indent}{field.name}: {self[field.name]}" if not issubclass(type(self[field.name]), StationNode)
            else f"{'\t'*indent}{field.name}:\n{self[field.name].get_tree(indent+1)}"
        for field in fields(self)
        ])

    def __getitem__(self, item):
        return getattr(self, item)
    
    def __setitem__(self, key, val):
        if hasattr(self, key):
            setattr(self, key, val)
        else:
            print(f"No attr {key}")


@dataclass
class OctaveRFChannel(StationNode):
    channel_id: str
    LO_frequency: float = 6e9
    gain: int = -20


@dataclass
class OPXAnalogChannel(StationNode):
    channel_id: str
    dc_volt: float = 0.0


@dataclass
class ProbeLine(StationNode):
    input: OctaveRFChannel
    output: OctaveRFChannel
    LO_frequency: float = 6e9

    def __setitem__(self, key, val):
        if getattr(self, key):
            if key == "LO_frequency":
                self.input.LO_frequency = val
                self.output.LO_frequency = val
            setattr(self, key, val)


@dataclass
class ReadoutDisc(StationNode):
    param_0: complex
    param_1: complex

    def discriminate_data(self, data):
        data["e_state"] = ((data["iq"] - self.param_0) * self.param_1).real


@dataclass
class TransmonQubit(StationNode):
    drive: OctaveRFChannel
    frequency: float = 5.8e9
    X180_duration: int = 100
    X180_amplitude: float = 0.5
    drag_coef: float = 0.0
    flux: Optional[OPXAnalogChannel] = None
    readout_frequency: float = 5.8e9
    readout_amplitude: float = 0.1
    readout_len: int = 2000
    readout_discriminator: Optional[ReadoutDisc] = None