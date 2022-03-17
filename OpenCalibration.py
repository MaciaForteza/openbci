import argparse
from contextlib import nullcontext
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore 
import PySimpleGUI as sg
import numpy as np
from numpy import savetxt
import statistics
from djitellopy import tello
from time import sleep

import brainflow
from brainflow.board_shim import BoardShim, BrainFlowInputParams, LogLevels, BoardIds
from brainflow.data_filter import DataFilter, DetrendOperations, FilterTypes

# Usage:
#   TESTING          python OpenCalibration.py
#   OPENBCI DATA     python OpenCalibration.py --board-id 2 --serial-port COM5
#                       NOTE: COM5 depends on port available in your Device Manager

class Graph():
    def __init__(self, board_shim):
        self.board_id = board_shim.get_board_id()
        self.board_shim = board_shim
        self.sampling_rate = BoardShim.get_sampling_rate(self.board_id)
        self.update_speed_ms = 1000
        self.window_size = 4
        self.num_points = self.window_size * self.sampling_rate

        self.arr_deviation = np.array([])
        self.dev_calm = 0
        self.dev_move = 0
        self.second = 0

        self.app = QtGui.QApplication([])
        self.win = pg.GraphicsWindow(title='BrainFlow Plot',size=(800, 600))
        self.win.setBackground('w')

        self._init_timeseries()

        timer = QtCore.QTimer()
        timer.timeout.connect(self.update)
        timer.start(self.update_speed_ms)
        QtGui.QApplication.instance().exec_()

    def _init_timeseries(self):
        self.plots = list()
        self.curves = list()

        # Plot 1 - C4 RAW DATA
        p = self.win.addPlot(0,0)
        p.showAxis('left', True)
        p.setRange(yRange=[-100000,100000])
        p.setMenuEnabled('left', False)
        p.showAxis('bottom', False)
        p.setMenuEnabled('bottom', False)
        p.setTitle('C4 RAW DATA')
        self.plots.append(p)
        curve = p.plot()
        self.curves.append(curve)

        # Plot 2 - C4 FILTERED DATA
        p = self.win.addPlot(1,0)
        p.showAxis('left', True)
        p.setRange(yRange=[-100000,100000])
        p.setMenuEnabled('left', False)
        p.showAxis('bottom', False)
        p.setMenuEnabled('bottom', False)
        p.setTitle('C4 FILTERED DATA')
        self.plots.append(p)
        curve = p.plot()
        self.curves.append(curve)

        #Plot 3 - FFT
        p = self.win.addPlot(2,0)
        p.showAxis('left', True)
        p.setRange(yRange=[0,100000])
        p.setMenuEnabled('left', False)
        p.showAxis('bottom', True)
        p.setMenuEnabled('bottom', False)
        p.setTitle('FFT')
        p.setLabel("bottom", "Freq (Hz)")
        p.setLabel("left", "|Y(freq)|")
        self.plots.append(p)
        curve = p.plot()
        self.curves.append(curve)

        #Plot 4 - Message
        p = self.win.addPlot(3,0)
        p.setTitle("KEEP CALM")
        p.showAxis('bottom', False)
        p.showAxis('left', False)
        self.plots.append(p)
        curve = p.plot()
        self.curves.append(curve)

    def update(self):
        # Plot Data Vars
        plotCharC4Raw = 0
        plotCharC4Filtered = 1
        plotCharC4FFT = 2

        # Channel Vars
        channelC4 = 11

        data = self.board_shim.get_current_board_data(self.num_points)
 
        ### Plot timeseries C4 Raw Data
        DataFilter.detrend(data[channelC4], DetrendOperations.CONSTANT.value)
        self.curves[plotCharC4Raw].setData(data[channelC4].tolist())

        ### Plot timeseries C4 Filtered
        DataFilter.detrend(data[channelC4], DetrendOperations.CONSTANT.value)
        # Butterworth.Remove Direct Current: Band pass filter from 0.5 Hz to 90 Hz
        DataFilter.perform_bandpass(data[channelC4], self.sampling_rate, 0.5, 90.0, 2,
                                    FilterTypes.BUTTERWORTH.value, 0)
        #   Noise Reduction: Notch filter 50 Hz & 60 Hz
        DataFilter.perform_bandstop(data[channelC4], self.sampling_rate, 50.0, 4.0, 2,
                                    FilterTypes.BUTTERWORTH.value, 0)
        DataFilter.perform_bandstop(data[channelC4], self.sampling_rate, 60.0, 4.0, 2,
                                    FilterTypes.BUTTERWORTH.value, 0)
    
        self.curves[plotCharC4Filtered].setData(data[channelC4].tolist())


        ### Plot C4 FFT
        YY = np.fft.fft(data[channelC4]) 
        self.curves[plotCharC4FFT].setData(abs(YY))

        ## Calculate standard deviation on FFT. A large standard deviation indicates that the data is spread out, 
        #  a small standard deviation indicates that the data is clustered closely around the mean.
        #  Right-Hand movement  ---> Large standard deviation from electrode C4
        deviation = statistics.pstdev(abs(YY))
        
        self.second = self.second + 1
        self.arr_deviation = np.append(self.arr_deviation,deviation)

        if self.second == 20:
            self.dev_calm = statistics.mean(self.arr_deviation)
            self.arr_deviation = np.empty([])
            self.plots[3].setTitle("DA-LI BRANCA!!!")
        
        if self.second == 40:
            self.dev_move = statistics.mean(self.arr_deviation)
            self.app.exit()

        self.app.processEvents()

def stream_window(board):
    g = Graph(board)
    print("DEV CALM:", g.dev_calm)
    print("DEV MOVE:", g.dev_move)

def main():
    BoardShim.enable_dev_board_logger()

    parser = argparse.ArgumentParser()
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

    board_id = args.board_id
    sampling_rate = BoardShim.get_sampling_rate(board_id)
    sampling_power_of_two = DataFilter.get_nearest_power_of_two(sampling_rate)
    board = BoardShim(board_id, params)
    board.prepare_session()
    board.start_stream(sampling_power_of_two)
    BoardShim.log_message(LogLevels.LEVEL_INFO.value, 'start sleeping in the main thread')

    layout = [ 
        [sg.Button('Calibration', size=(100,1), key="stream")]
     ]

    window = sg.Window('OpenCalibration', layout, size=(400,200), grab_anywhere=True)
    while True:
        event, values = window.read()
    
        if event == "stream":
            stream_window(board)

        if event == sg.WIN_CLOSED:
            if board.is_prepared():
                    BoardShim.log_message(LogLevels.LEVEL_INFO, 'Releasing session')
                    board.release_session()
            break
            
        window.close()

if __name__ == "__main__":
    main()
