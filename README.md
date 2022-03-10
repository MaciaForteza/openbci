# openbci
Python connection with OpenBCI using C3 & C4 electrode. FFT and deviation included to detect hand/arm movement.

## Description
Code intented to use OpenBCI Cyton+Daisy Biosensing Board 16-channel Cap (https://shop.openbci.com/products/openbci-eeg-electrocap-kit).

## Files

### `OpenBCI.py`
Connects OpenBCI Cyton+Daisy Biosensing Board and plots C3 and C4 electrodes on screen. The code also shows C3 and C4 electrode signals filtered using
-  Butterworth.Remove Direct Current: Band pass filter from 0.5 Hz to 90 Hz
-  Noise Reduction: Notch filter 50 Hz & 60 Hz

### `OpenFFT.py`
Connects OpenBCI Cyton+Daisy Biosensing Board and plots C4 electrode on screen:
- C4 raw data
- C4 filtered using same filters than in OpenBCI.py code
- Fast Fourier Transformation in order to detect main frequencies on signal
- Deviation calculation in order to distinguish between hand/arm movement and relaxation states

### `OpenDroneTakeoffLand.py`
Code that controls a drone using C4 electrode and FFT deviation calculation. When deviation is more than 300000, the dron takes off and, after 2 seconds, lands. Then, the program exits.

### `OpenDroneUpDown.py`
A dron takes off when clicking on button. The code controls a drone using C4 electrode and FFT deviation calculation. When deviation is more than 300000, the dron rises up. When user relaxes, deviation goes down, so does the dron.
