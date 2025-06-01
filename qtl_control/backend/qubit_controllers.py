from enum import Enum
from qtl_control.backend.controller_module import (
    Setting,
    StationNode,
    StationNodeRef,
    ControllerModule,
)

class PlaylistOp(Enum):
    readout = 0
    play_pulse = 1
    change_readout_frequency = 2
    change_drive_frequency = 3

class PulsePlaylist:
    def __init__(self, channel_labels, Navg, data_dims):
        self.Navg = Navg
        self.channels = {ch_label: [] for ch_label in channel_labels}
        self.data_dims = data_dims

    def add(self, channel_element, playlist_op, *args):
        self.channels[channel_element].append((playlist_op, *args))



class TransmonQubit(StationNode):
    # TODO: FIX qm to more generic interface
    def __init__(self, label, readout, drive):
        super().__init__(label)

        self.update_settings({
            "readout_frequency": Setting(6e9, setter=readout.set_frequency),
            "drive_frequency": Setting(4.0e9, setter=drive.set_frequency),
        })

        self.readout = readout

    def execute_playlist(self, playlist, Navg, data_dims):
        # TODO: Currently only one OPX so we update playlists on only one channel
        # self.drive_channel.update_playlist(playlist)
        self.readout.execute_playlist(playlist, Navg, data_dims)

        # Pulse storage to load from?
        # self.update_subnodes()
        

class PulsedQubits(ControllerModule):
    label = "PulsedQubits"
    module_controllers = {
        "TransmonQubit": TransmonQubit,
    }
    module_methods = [
        "execute_playlist"
    ]

    def execute_playlist(self, playlist):
        for element, elem_playlist in playlist.channels.items():
            self.controllers[element].execute_playlist(
                elem_playlist,
                playlist.Navg,
                playlist.data_dims
            )

