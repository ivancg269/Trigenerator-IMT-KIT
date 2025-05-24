import serial
import ctypes
import numpy as np
from picosdk.usbtc08 import usbtc08 as tc08
from picosdk.functions import assert_pico2000_ok
import csv
import time
import matplotlib.pyplot as plt
from datetime import datetime

#Code developed by: Ivan Cruz
#This code takes values from teh optris infrared sensor and thermocouple with datalogger and plots its values

#If more fucntions are needed the xor checksum is usefull, for me i just need to send 0x01, which checksum is 0x01 so i dont need it (this is the command to read temperature)
def xor_checksum(data: bytes) -> bytes:
    """Computes XOR checksum for the given data."""
    checksum = 0
    for byte in data:
        checksum ^= byte  # XOR each byte
    return bytes([checksum])
def readOptrics():
    command = b'\x01'
    ser = serial.Serial(port='COM12', baudrate=9600, timeout=1)
    ser.write(command)  # Example binary command
    response = ser.read(10)  # Read response
    while(len(response)==0):
        ser.write(command)
        response = ser.read(10)
        ser.close()
    return(((int.from_bytes(response[:2], "big"))-1000)/10)
def readPicolog (type,channel):
    # Create chandle and status ready for use
    chandle = ctypes.c_int16()
    status = {}

    # open unit
    status["open_unit"] = tc08.usb_tc08_open_unit()
    assert_pico2000_ok(status["open_unit"])
    chandle = status["open_unit"]

    # set mains rejection to 50 Hz
    status["set_mains"] = tc08.usb_tc08_set_mains(chandle,0)
    assert_pico2000_ok(status["set_mains"])

        # set up channel
    # therocouples types and int8 equivalent
    # B=66 , E=69 , J=74 , K=75 , N=78 , R=82 , S=83 , T=84 , ' '=32 , X=88 
    typeK = ctypes.c_int8(type)
    status["set_channel"] = tc08.usb_tc08_set_channel(chandle, channel, typeK)
    assert_pico2000_ok(status["set_channel"])

    # get minimum sampling interval in ms
    status["get_minimum_interval_ms"] = tc08.usb_tc08_get_minimum_interval_ms(chandle)
    assert_pico2000_ok(status["get_minimum_interval_ms"])

    # get single temperature reading
    temp = (ctypes.c_float * 9)()
    overflow = ctypes.c_int16(0)
    units = tc08.USBTC08_UNITS["USBTC08_UNITS_CENTIGRADE"]
    status["get_single"] = tc08.usb_tc08_get_single(chandle,ctypes.byref(temp), ctypes.byref(overflow), units)
    assert_pico2000_ok(status["get_single"])    
    # print data
    #print("Cold Junction ", temp[0]," Channel 1 ", temp[1])

    # close unit
    status["close_unit"] = tc08.usb_tc08_close_unit(chandle)
    assert_pico2000_ok(status["close_unit"])
    return(temp[channel])


experiment_name = input("Enter the experiment name: ").strip().replace(" ", "_")  # Remove spaces
csv_filename = f"{experiment_name}.csv"  # CSV file with experiment name

# Create the CSV file and write headers if it does not exist
with open(csv_filename, mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Radiator", "OptrisIrS","Air Temp", "Time"])  # Write headers

print(f"CSV file '{csv_filename}' created. Logging sensor data every 10 seconds...")

# Lists to store data for plotting
sensor1_values = []
sensor2_values = []
sensor3_values = []
corrections=[]
time_stamps = []

# Infinite loop to log data every 10 seconds
try:
    while True:
        # Generate random sensor values (replace these with actual sensor readings)
        sensor1_value = readPicolog(75,1)  # Example: Temperature sensor
        #sensor1_value=8
        sensor2_value = readOptrics()  # Example: Humidity sensor
        sensor3_value = readPicolog(84,2)
        
        

        a=1.3573018709524816
        b=-2.314821772480257
        #a=0.8842100200966289
        #b=2.2965563459442624
        correction=a * sensor2_value + b
        #nsor3_value = 8
        # Get current timestamp
        current_time = datetime.now().strftime("%H:%M:%S")

        # Append data to the CSV file
        with open(csv_filename, mode="a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([sensor1_value, sensor2_value,sensor3_value, current_time,correction])

        # Store data for graphing
        sensor1_values.append(sensor1_value)
        sensor2_values.append(sensor2_value)
        sensor3_values.append(sensor3_value)
        corrections.append(correction)
        time_stamps.append(current_time)

        print(f"Logged: {sensor1_value}, {sensor2_value}, {sensor3_value},{current_time}")

        # Wait for 10 seconds before next reading
        time.sleep(5)

except KeyboardInterrupt:
    print("\nLogging stopped by user.")

    # Plot the sensor data
    plt.figure(figsize=(10, 5))
    plt.gca().set_facecolor("#f0f0f0")  # Light gray background for the plot area
    plt.gcf().set_facecolor("#d0e0ff")
    plt.plot(time_stamps, sensor1_values, marker="o", linestyle="-", label="TempRad")
    plt.plot(time_stamps, sensor2_values, marker="s", linestyle="-", label="Infrared Sensor")
    plt.plot(time_stamps, sensor3_values, marker="o", linestyle="-", label="TempAir")
    plt.plot(time_stamps, corrections, marker="o", linestyle="-", label="Correction")


    # Format the graph
    plt.xlabel("Time")
    plt.ylabel("Sensor Values")
    plt.title("Sensor Data Over Time")
    plt.xticks(rotation=45)  # Rotate time labels for better visibility
    plt.legend()
    plt.grid()


    # Save the graph as an image
    graph_filename = f"{experiment_name}.png"
    plt.savefig(graph_filename, dpi=300, bbox_inches="tight")
    print(f"Graph saved as '{graph_filename}'")

    # Show the plot
    plt.show()