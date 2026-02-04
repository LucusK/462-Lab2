import time
import math
import board
import busio
import digitalio
import RPi.GPIO as GPIO
import adafruit_mcp4725
import threading

# ------------------- CONFIG -------------------
BUTTON_PIN = 17
VCC = 3.3          # Voltage connected to DAC VCC
MAX_DAC = 4095     # 12-bit resolution
# ----------------------------------------------

# Setup I2C + DAC
i2c = busio.I2C(board.SCL, board.SDA)
dac = adafruit_mcp4725.MCP4725(i2c, address=0x62)

# Setup Button
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

running = False
stop_flag = False

# -------- Helper --------
def voltage_to_dac(v):
    return int((v / VCC) * MAX_DAC)

# -------- Wave Generators --------

def square_wave(freq, vmax):
    global stop_flag
    period = 1.0 / freq
    high = voltage_to_dac(vmax)
    low = 0

    while not stop_flag:
        dac.value = high
        time.sleep(period / 2)
        dac.value = low
        time.sleep(period / 2)


def triangle_wave(freq, vmax):
    global stop_flag
    steps = 100
    period = 1.0 / freq
    step_time = period / (2 * steps)

    while not stop_flag:
        # Rising
        for i in range(steps):
            if stop_flag: break
            v = (i / steps) * vmax
            dac.value = voltage_to_dac(v)
            time.sleep(step_time)

        # Falling
        for i in range(steps, -1, -1):
            if stop_flag: break
            v = (i / steps) * vmax
            dac.value = voltage_to_dac(v)
            time.sleep(step_time)


def sine_wave(freq, vmax):
    global stop_flag
    steps = 100
    period = 1.0 / freq
    step_time = period / steps

    while not stop_flag:
        for i in range(steps):
            if stop_flag: break
            angle = 2 * math.pi * i / steps
            v = (math.sin(angle) * 0.5 + 0.5) * vmax
            dac.value = voltage_to_dac(v)
            time.sleep(step_time)

# -------- User Input --------

def get_inputs():
    while True:
        shape = input("Waveform (square / triangle / sin): ").strip().lower()
        if shape in ["square", "triangle", "sin"]:
            break
        print("Invalid waveform.")

    while True:
        try:
            freq = float(input("Frequency (Hz, max 50): "))
            if 0 < freq <= 50:
                break
            print("Must be 0–50 Hz.")
        except:
            print("Invalid number.")

    while True:
        try:
            vmax = float(input(f"Max voltage (0–{VCC} V): "))
            if 0 <= vmax <= VCC:
                break
            print("Out of range.")
        except:
            print("Invalid number.")

    return shape, freq, vmax

# -------- Button Wait --------

def wait_for_button():
    while GPIO.input(BUTTON_PIN) == GPIO.HIGH:
        time.sleep(0.01)
    time.sleep(0.3)  # debounce

print("Ready. Press button to begin.")

try:
    while True:
        wait_for_button()

        if not running:
            shape, freq, vmax = get_inputs()
            stop_flag = False
            running = True

            if shape == "square":
                t = threading.Thread(target=square_wave, args=(freq, vmax))
            elif shape == "triangle":
                t = threading.Thread(target=triangle_wave, args=(freq, vmax))
            else:
                t = threading.Thread(target=sine_wave, args=(freq, vmax))

            t.start()
            print("Generating wave... Press button to stop.")

        else:
            stop_flag = True
            running = False
            dac.value = 0
            print("Stopped. Press button for new settings.")

except KeyboardInterrupt:
    pass

finally:
    dac.value = 0
    GPIO.cleanup()
