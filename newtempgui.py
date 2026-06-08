from tkinter import *
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import serial
from threading import Thread
from tkinter import messagebox

# --- Global Configuration (Matches Arduino TOTAL_IC, TOTAL_CELL, TEMPS) ---
# Define ports for voltage and temperature data streams
voltage_port_var = "COM7"  # Default port for Voltage data
temp_port_var = "COM8"     # Default port for Temperature data

root = Tk()
root.title("Multi-Port BMS Data Viewer")

# Total number of ICs/Stacks defined in the Arduino code (TOTAL_IC = 18)
TOTAL_IC = 18 
# Total number of cell voltages per stack (TOTAL_CELL = 6)
TOTAL_CELL = 6 
# Total number of temperature sensors per stack (TEMPS = 4)
TEMPS = 4 

# Total number of data values per cycle: 18 * (6 V + 4 T) = 180
TOTAL_VALUES = TOTAL_IC * (TOTAL_CELL + TEMPS)

# Create a StringVar for every single value to be displayed (180 variables)
serial_vals = [StringVar(value='0.0') for _ in range(TOTAL_VALUES)] 

serial_running = False
voltage_serial_port = None
temp_serial_port = None

rows = 3 # Display grid rows (3 x 6 = 18 stacks)
cols = 6 # Display grid columns
# --------------------------------------------------------------------------


def serial_ports():
    """ Lists serial port names """
    ports = ['COM%s' % (i + 1) for i in range(256)]
    comms = []
    for port in ports:
        try:
            # Only test opening the port, not configuring it
            s = serial.Serial(port)
            s.close()
            comms.append(port)
        except (OSError, serial.SerialException):
            pass
    return comms


def start_serial_read():
    global voltage_serial_port, temp_serial_port, serial_running

    if serial_running:
        messagebox.showinfo("Status", "Serial threads are already running.")
        return

    # --- Attempt to open Voltage Port ---
    try:
        voltage_serial_port = serial.Serial(voltage_port_var, 115200, timeout=1) 
        print(f"Voltage port {voltage_port_var} opened.")
    except serial.SerialException:
        messagebox.showerror("Connection Error", f"Could not open Voltage port {voltage_port_var}. Check connection.")
        return # Stop if voltage port fails

    # --- Attempt to open Temperature Port ---
    try:
        temp_serial_port = serial.Serial(temp_port_var, 115200, timeout=1) 
        print(f"Temperature port {temp_port_var} opened.")
    except serial.SerialException:
        messagebox.showerror("Connection Error", f"Could not open Temperature port {temp_port_var}. Check connection.")
        # Clean up the voltage port if temperature port fails
        voltage_serial_port.close()
        return # Stop if temperature port fails

    # --- Start Threads if both ports opened successfully ---
    serial_running = True
    Thread(target=voltage_worker, daemon=True).start()
    Thread(target=temp_worker, daemon=True).start()
    messagebox.showinfo("Status", f"Reading from ports {voltage_port_var} (V) and {temp_port_var} (T).")


def stop_serial_read():
    global serial_running
    serial_running = False
    if voltage_serial_port and voltage_serial_port.is_open:
        voltage_serial_port.close()
        print(f"Voltage port {voltage_port_var} closed.")
    if temp_serial_port and temp_serial_port.is_open:
        temp_serial_port.close()
        print(f"Temperature port {temp_port_var} closed.")
    messagebox.showinfo("Status", "Serial reading stopped and ports closed.")


def voltage_worker():
    """Reads voltage data (TOTAL_IC * TOTAL_CELL) from the voltage port."""
    global serial_running
    expected_volts = TOTAL_IC * TOTAL_CELL  # 18 * 6 = 108 values
    while serial_running:
        try:
            line = voltage_serial_port.readline().decode('utf-8').rstrip()
            
            if line:
                values = line.split(', ') 
                
                if len(values) == expected_volts:
                    for stack_index in range(TOTAL_IC):
                        # The voltage data is expected to be in a single flat list:
                        # V1_C1, V1_C2, ..., V1_C6, V2_C1, ..., V18_C6
                        
                        # Find the start index of the received data for the current stack
                        volt_start_in_input = stack_index * TOTAL_CELL
                        
                        for i in range(TOTAL_CELL): # i = 0 to 5 (Cell V1 to V6)
                            # Calculate the index in the global serial_vals list:
                            # Start of stack + cell voltage offset (0 to 5)
                            data_index = stack_index * (TOTAL_CELL + TEMPS) + i 
                            
                            # Get the value from the received data list
                            val_to_set = values[volt_start_in_input + i]
                            
                            if data_index < len(serial_vals):
                                # Safely update the StringVar in the main thread
                                root.after(0, serial_vals[data_index].set, val_to_set)
                else:
                    print(f"Voltage Warning: Received {len(values)} values, expected {expected_volts}")
                    
        except Exception as e:
            if serial_running: # Only print error if it wasn't triggered by stop
                print(f"Error reading from Voltage port: {e}")
                # Consider breaking the loop/stopping if a critical error occurs


def temp_worker():
    """Reads temperature data (TOTAL_IC * TEMPS) from the temperature port."""
    global serial_running
    expected_temps = TOTAL_IC * TEMPS # 18 * 4 = 72 values
    while serial_running:
        try:
            line = temp_serial_port.readline().decode('utf-8').rstrip()
            
            if line:
                values = line.split(', ') 
                
                if len(values) == expected_temps:
                    for stack_index in range(TOTAL_IC):
                        # The temperature data is expected to be in a single flat list:
                        # T1_T1, T1_T2, T1_T3, T1_T4, T2_T1, ..., T18_T4
                        
                        # Find the start index of the received data for the current stack
                        temp_start_in_input = stack_index * TEMPS
                        
                        for j in range(TEMPS): # j = 0 to 3 (Temp T1 to T4)
                            # Calculate the index in the global serial_vals list:
                            # Start of stack + TOTAL_CELL (6) offset + current temp sensor index (0 to 3)
                            data_index = stack_index * (TOTAL_CELL + TEMPS) + TOTAL_CELL + j
                            
                            # Get the value from the received data list
                            val_to_set = values[temp_start_in_input + j]

                            if data_index < len(serial_vals):
                                # Safely update the StringVar in the main thread
                                root.after(0, serial_vals[data_index].set, val_to_set)
                else:
                    print(f"Temperature Warning: Received {len(values)} values, expected {expected_temps}")
                    
        except Exception as e:
            if serial_running: # Only print error if it wasn't triggered by stop
                print(f"Error reading from Temperature port: {e}")
                # Consider breaking the loop/stopping if a critical error occurs

def show_ports():
    ports = serial_ports()
    port_list = "\n".join(ports) if ports else "No serial ports found."
    messagebox.showinfo("Available Serial Ports", f"**Voltage Port (V):** {voltage_port_var}\n**Temperature Port (T):** {temp_port_var}\n\n**Detected Ports:**\n{port_list}")


# --- GUI Layout Generation (3x6 Grid for 18 Stacks) ---
for row in range(rows):
    for col in range(cols):
        stack_index = row * cols + col # 0 to 17
        
        if stack_index >= TOTAL_IC:
            break
            
        # Create a LabelFrame for each Stack/IC
        lf = ttk.Labelframe(root, text=f'Stack {stack_index+1}', bootstyle=PRIMARY)
        lf.grid(row=row, column=col, padx=5, pady=5, sticky="news") 
        
        # --- Display Cell Voltages (6 values) ---
        for i in range(TOTAL_CELL): # i = 0 to 5
            # Calculate the global index for the StringVar (V)
            data_index = stack_index * (TOTAL_CELL + TEMPS) + i 
            
            # Label for Cell Voltage (e.g., Cell V1:)
            ttk.Label(lf, text=f'Cell V{i+1}:', bootstyle=SECONDARY).grid(row=i, column=0, sticky='w', padx=5)
            # Label for the value
            ttk.Label(lf, textvariable=serial_vals[data_index], bootstyle=INFO).grid(row=i, column=1, sticky='e', padx=5)
            
        # --- Display Temperatures (4 values) ---
        for j in range(TEMPS): # j = 0 to 3
            # Calculate the global index for the StringVar (T)
            data_index = stack_index * (TOTAL_CELL + TEMPS) + TOTAL_CELL + j
            
            # Label for Temperature (e.g., Temp T1:)
            ttk.Label(lf, text=f'Temp T{j+1}:', bootstyle=SECONDARY).grid(row=TOTAL_CELL + j, column=0, sticky='w', padx=5)
            # Label for the value
            ttk.Label(lf, textvariable=serial_vals[data_index], bootstyle=SUCCESS).grid(row=TOTAL_CELL + j, column=1, sticky='e', padx=5)

# Place the control buttons below the 3x6 grid
ttk.Button(root, text='Start', command=start_serial_read, bootstyle=SUCCESS).grid(
    row=rows, column=0, pady=10)
ttk.Button(root, text='Stop', command=stop_serial_read, bootstyle=DANGER).grid(
    row=rows, column=1, pady=10)
ttk.Button(root, text='List Ports & Status', command=show_ports, bootstyle=INFO).grid(
    row=rows+1, column=0, columnspan=2, pady=10)

root.mainloop()