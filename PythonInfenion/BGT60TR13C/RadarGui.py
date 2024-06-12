import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from range_angle_map import *


script_dir = 'C:/Users/nikhi/Documents/Projekt/TeamProject/PythonInfenion/BGT60TR13C'  #my path, change with your path
os.chdir(script_dir)


class ReloadHandler(FileSystemEventHandler):
    def __init__(self, root):
        self.root = root

    def on_modified(self, event):
        if event.src_path == os.path.abspath(__file__):
            self.reload_app()

    def reload_app(self):
        python = sys.executable
        os.execl(python, python, *sys.argv)

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
      
        ##concurrent.future
        
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

##------------------------------------------------------------------------------------------------

    ## GUI impl
    
##------------------------------------------------------------------------------------------------

def GUI():
    root = tk.Tk()
    root.geometry("1200x1080")
    root.attributes('-fullscreen', True)
    return root


def exit_fullscreen(event=None):
    root.attributes('-fullscreen', False)

root.bind('<Escape>', exit_fullscreen)

button_style = {
    "font": ("Helvetica", 12, "bold"),
    "background": "#4CAF50",
    "foreground": "white",
    "borderwidth": 2,
    "relief": "raised",
    "width": 20,
    "height": 2
}


if __name__ == "__main__":
    root = GUI()
    event_handler = ReloadHandler(root)
    observer = Observer()
    observer.schedule(event_handler, path=os.path.dirname(os.path.abspath(__file__)), recursive=False)
    observer.start()

try:
    root.mainloop()
except KeyboardInterrupt:
    observer.stop()
    observer.join

button1 = tk.Button(root, text="Script 1", command=run_script1, **button_style)
button1.pack(pady=20)

button2 = tk.Button(root, text="Script 2", command=run_script2, **button_style)
button2.pack(pady=20)

button3 = tk.Button(root, text="Script 3", command=run_script3, **button_style)
button3.pack(pady=20)

# Run the main loop
root.mainloop()
