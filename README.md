# TeamProject
>This Respository contains the following codes and an STL file(Seeed Sensor and ESP32).

## ESP32 with LED's for the SEEED STUDIO 60GHz mmWave Sensor - Fall Detection Module Pro (MR60FDA1)
- The Human Presence detection is working and only gives visual feedback via the LED's.
- With the help of an ESP32, the presence detection information can be sent to the Care-Taker's devices via internet.
- The provided libraries from Seeed Studio help communicate with the sensor.
- The entire code is developed in **Arduino IDE**.
- Further development are currently halted with this sensor for the project.
## Python script for the Infenion XENSIV™ 60GHz radar sensor for advanced sensing BGT60TR13C module
- The **Infenion BGT60TR13C** module can send raw data for presence and activity sensing to the console.
- This is possible by using the libraries provided for the sensor from Infenion.
- Before running the code, the following needs to be done.
### Steps to install the library
- A **Python Version** of **3.8** or higher is required for the wrapper and is tested on **Windows 10 (64-bit)**.
- To install the **ifxradarsdk**, it is advisable to do it in a virtual environment.

		 python  -m  pip  install  /path/to/ifxradarsdk.whl

### Steps to display data from the sensor
- The **main_gui.py** with the help of the libraries is developed to show all the usecases in a single GUI.
- Start by connecting the Sensor to the pc.
- Then run the **main_gui.py**.
- The Fall Detection usecase requires a different sensor configuration and has to be set in the **radar_data_acquisition.py**
