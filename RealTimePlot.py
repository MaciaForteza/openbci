import argparse
import logging
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore 

from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from brainflow.data_filter import DataFilter, FilterTypes, DetrendOperations

# Usage:
#   TESTING          python RealTimePlot.py
#   OPENBCI DATA     python RealTimePlot.py --board-id 2 --serial-port COM5
#                       NOTE: COM5 depends on port available in your Device Manage

class Graph:
    def __init__(self, board_shim):
        self.board_id = board_shim.get_board_id()
        self.board_shim = board_shim
        self.eeg_channels = BoardShim.get_eeg_channels(self.board_id)
        self.sampling_rate = BoardShim.get_sampling_rate(self.board_id)
        self.update_speed_ms = 50
        self.window_size = 4
        self.num_points = self.window_size * self.sampling_rate

        self.app = QtGui.QApplication([])
        self.win = pg.GraphicsWindow(title='BrainFlow Plot',size=(1920, 1080))
        self.win.setBackground('w')

        self._init_timeseries()

        timer = QtCore.QTimer()
        timer.timeout.connect(self.update)
        timer.start(self.update_speed_ms)
        QtGui.QApplication.instance().exec_()


    def _init_timeseries(self):
        self.plots = list()
        self.curves = list()
        for i in range(len(self.eeg_channels)):
            p = self.win.addPlot(row=i,col=0)
            p.showAxis('left', True)
            p.setRange(yRange=[-1000,1000])
            p.setMenuEnabled('left', False)
            p.showAxis('bottom', True)
            p.setMenuEnabled('bottom', False)
            if i == 0:
                p.setTitle('TimeSeries Plot')
                p.setLabel("left", "FP1")
            if i == 1:
                p.setLabel("left", "FP2")
            if i == 2:
                p.setLabel("left", "F7")
            if i == 3:
                p.setLabel("left", "F3")
            if i == 4:
                p.setLabel("left", "Fz")
            if i == 5:
                p.setLabel("left", "F4")
            if i == 6:
                p.setLabel("left", "F8")
            if i == 7:
                p.setLabel("left", "T3")
            if i == 8:
                p.setLabel("left", "C3")
            if i == 9:
                p.setLabel("left", "Cz")
            if i == 10:
                p.setLabel("left", "C4")
            if i == 11:
                p.setLabel("left", "T4")
            if i == 12:
                p.setLabel("left", "T5")
            if i == 13:
                p.setLabel("left", "P3")
            if i == 14:
                p.setLabel("left", "Pz")
            if i == 15:
                p.setLabel("left", "P4")
            self.plots.append(p)
            curve = p.plot()
            self.curves.append(curve)

        for i in range(len(self.eeg_channels)):
            p = self.win.addPlot(row=i,col=1)
            p.showAxis('left', True)
            p.setRange(yRange=[0,100000])
            p.setMenuEnabled('left', False)
            p.showAxis('bottom', True)
            p.setMenuEnabled('bottom', False)
            if i == 0:
                p.setTitle('FFT')
            p.setLabel("left", "|Y(freq)|")

            self.plots.append(p)
            curve = p.plot()
            self.curves.append(curve)

    def update(self):
        data = self.board_shim.get_current_board_data(self.num_points)
        for count, channel in enumerate(self.eeg_channels):
            # plot timeseries
            DataFilter.detrend(data[channel], DetrendOperations.CONSTANT.value)
            # Butterworth.Remove Direct Current: Band pass filter from 0.5 Hz to 90 Hz
            DataFilter.perform_bandpass(data[channel], self.sampling_rate, 0.5, 90.0, 2,
                                        FilterTypes.BUTTERWORTH.value, 0)
            # Noise Reduction: Notch filter 50 Hz & 60 Hz
            DataFilter.perform_bandstop(data[channel], self.sampling_rate, 50.0, 4.0, 2,
                                        FilterTypes.BUTTERWORTH.value, 0)
            DataFilter.perform_bandstop(data[channel], self.sampling_rate, 60.0, 4.0, 2,
                                        FilterTypes.BUTTERWORTH.value, 0)
        
            self.curves[count].setData(data[channel].tolist())

            # FFT Plot per channel
            YY = np.fft.fft(data[channel]) 
            self.curves[count + 16].setData(abs(YY))

        self.app.processEvents()


def main():
    BoardShim.enable_dev_board_logger()
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    # use docs to check which parameters are required for specific board, e.g. for Cyton - set serial port
    parser.add_argument('--timeout', type=int, help='timeout for device discovery or connection', required=False,
                        default=0)
    parser.add_argument('--ip-port', type=int, help='ip port', required=False, default=0)
    parser.add_argument('--ip-protocol', type=int, help='ip protocol, check IpProtocolType enum', required=False,
                        default=0)
    parser.add_argument('--ip-address', type=str, help='ip address', required=False, default='')
    parser.add_argument('--serial-port', type=str, help='serial port', required=False, default='')
    parser.add_argument('--mac-address', type=str, help='mac address', required=False, default='')
    parser.add_argument('--other-info', type=str, help='other info', required=False, default='')
    parser.add_argument('--streamer-params', type=str, help='streamer params', required=False, default='')
    parser.add_argument('--serial-number', type=str, help='serial number', required=False, default='')
    parser.add_argument('--board-id', type=int, help='board id, check docs to get a list of supported boards',
                        required=False, default=BoardIds.SYNTHETIC_BOARD)
    parser.add_argument('--file', type=str, help='file', required=False, default='')
    args = parser.parse_args()

    params = BrainFlowInputParams()
    params.ip_port = args.ip_port
    params.serial_port = args.serial_port
    params.mac_address = args.mac_address
    params.other_info = args.other_info
    params.serial_number = args.serial_number
    params.ip_address = args.ip_address
    params.ip_protocol = args.ip_protocol
    params.timeout = args.timeout
    params.file = args.file

    try:
        board_shim = BoardShim(args.board_id, params)
        board_shim.prepare_session()
        board_shim.start_stream(450000, args.streamer_params)
        
        Graph(board_shim)
    except BaseException:
        logging.warning('Exception', exc_info=True)
    finally:
        logging.info('End')
        if board_shim.is_prepared():
            logging.info('Releasing session')
            board_shim.release_session()


if __name__ == '__main__':
    main()
