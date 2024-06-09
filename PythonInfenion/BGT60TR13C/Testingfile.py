import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import os
import threading
import concurrent.futures
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from range_angle_map import *


script_dir = 'C:/Users/nikhi/Documents/Projekt/TeamProject/PythonInfenion/BGT60TR13C'  #my path, change with your path
os.chdir(script_dir)

##--------------------------------------------------------------------------------------------------------------------------

## basic impl

##--------------------------------------------------------------------------------------------------------------------------

def run_script1():
    try:
        subprocess.run([sys.executable, 'raw_data.py'], check=True)
        messagebox.showinfo("Success", "Script 1 executed successfully!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Script 1 failed: {e}")

def run_script2():
    try:
        subprocess.run([sys.executable, 'range_angle_map.py'], check=True)
        messagebox.showinfo("Success", "Script 2 executed successfully!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Script 2 failed: {e}")

def run_script3():
    try:
        subprocess.run([sys.executable, 'presence_detection.py'], check=True)
        messagebox.showinfo("Success", "Script 3 executed successfully!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Script 3 failed: {e}")
        
##--------------------------------------------------------------------------------------------------------------------------

        ## plot of the heatmap

##--------------------------------------------------------------------------------------------------------------------------

    ##running processess's as subprocessess's for threads and futures

##--------------------------------------------------------------------------------------------------------------------------

# def run_script(script_name):
#     try:
#         subprocess.run([sys.executable, script_name], check=True)
#         messagebox.showinfo("Success", f"{script_name} executed successfully!")
#     except subprocess.CalledProcessError as e:
#         messagebox.showerror("Error", f"{script_name} failed: {e}")

##--------------------------------------------------------------------------------------------------------------------------
     
        ##mutlithreading
 
##--------------------------------------------------------------------------------------------------------------------------
       
# def run_scripts_concurrently():
#     scripts = ['presence_detection.py', 'range_angle_map.py']  
#     threads = []
#     for script in scripts:
#         thread = threading.Thread(target=run_script, args=(script,))
#         thread.start()
#         threads.append(thread)

#     for thread in threads:
#         thread.join()
        
##--------------------------------------------------------------------------------------------------------------------------
      
        ##futures
        
##--------------------------------------------------------------------------------------------------------------------------

# def run_scripts_concurrently():
#     scripts = ['presence_detection.py', 'range_angle_map.py']  
#     with concurrent.futures.ThreadPoolExecutor() as executor:
#         futures = [executor.submit(run_script, script) for script in scripts]
#         for future in concurrent.futures.as_completed(futures):
#             try:
#                 future.result()
#             except Exception as e:
#                 print(f"Script failed: {e}")
        ##basic imnplementation
        
        
##--------------------------------------------------------------------------------------------------------------------------


# Create the main window
root = tk.Tk()
root.title("RADAR GUI")

##--------------------------------------------------------------------------------------------------------------------------

## multithreading
# button = tk.Button(root, text="Execute Script", command=run_scripts_concurrently)
# button.pack(pady=10)

##--------------------------------------------------------------------------------------------------------------------------

## basic impl

##--------------------------------------------------------------------------------------------------------------------------


button1 = tk.Button(root, text="Execute Script 1", command=run_script1)
button1.pack(pady=10)

button2 = tk.Button(root, text="Execute Script 2", command=run_script2)
button2.pack(pady=10)

button3 = tk.Button(root, text="Execute Script 3", command=run_script3)
button3.pack(pady=10)

# Run the main loop
root.mainloop()
