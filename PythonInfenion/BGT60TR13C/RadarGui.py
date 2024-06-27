import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import os
import threading
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from Testingfile import presence_map

script_dir = 'C:/Users/nikhi/Documents/Projekt/TeamProject/PythonInfenion/BGT60TR13C'  # Change with your path
os.chdir(script_dir)

stop_event = threading.Event()

def run_script1():
    try:
        subprocess.run([sys.executable, 'raw_data.py'], check=True)
        messagebox.showinfo("Success", "Script 1 executed successfully!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Script 1 failed: {e}")
    
def run_script2():
    stop_event.clear()
    fig, ax = plt.subplots(nrows=1, ncols=1)
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def thread_target():
        presence_map()

    threading.Thread(target=thread_target).start()

def run_script3():
    stop_event.clear()
    threading.Thread(target=run_presence_detection).start()

def run_presence_detection():
    presence_script = os.path.join(script_dir, 'presence_detection.py')
    process = subprocess.Popen([sys.executable, presence_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    for line in process.stdout:
        if stop_event.is_set():
            process.terminate()
            break
        if ',' in line:
            presence_status, peeking_status = line.strip().split(',')
            presence_status = presence_status == 'True'
            peeking_status = peeking_status == 'True'
            gui.update_labels(presence_status, peeking_status)
    
    process.stdout.close()
    process.stderr.close()
    process.wait()

def stop_script():
    stop_event.set()
    messagebox.showinfo("Info", "Stop signal sent!")

root = tk.Tk()
root.title("RADAR GUI")
root.geometry("1000x700")
root.configure(background='#2c3e50')

def exit_fullscreen(event=None):
    root.attributes('-fullscreen', False)

root.bind('<Escape>', exit_fullscreen)

button_style = {
    "font": ("Helvetica", 12, "bold"),
    "background": "#3498db",
    "foreground": "white",
    "borderwidth": 2,
    "relief": "raised",
    "width": 20,
    "height": 2
}

top_frame = tk.Frame(root, background='#2c3e50')
top_frame.pack(side=tk.TOP, fill=tk.X, pady=20)

button1 = tk.Button(top_frame, text="Script 1", command=run_script1, **button_style)
button1.pack(side=tk.LEFT, padx=20)

button2 = tk.Button(top_frame, text="Script 2", command=run_script2, **button_style)
button2.pack(side=tk.LEFT, padx=20)

button3 = tk.Button(top_frame, text="Script 3", command=run_script3, **button_style)
button3.pack(side=tk.LEFT, padx=20)

stop_button = tk.Button(top_frame, text="Stop Script", command=stop_script, **button_style)
stop_button.pack(side=tk.LEFT, padx=20)

plot_frame = tk.Frame(root, background='#ecf0f1', bd=2, relief="sunken")
plot_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=1, padx=20, pady=20)

label_presence = tk.Label(root, text="Presence: Not Detected", font=("Helvetica", 16), background='#2c3e50', foreground='white')
label_presence.pack(pady=10)
label_peeking = tk.Label(root, text="Peeking: Not Detected", font=("Helvetica", 16), background='#2c3e50', foreground='white')
label_peeking.pack(pady=10)

class RadarGUI:
    def __init__(self, root):
        self.label_presence = label_presence
        self.label_peeking = label_peeking

    def update_labels(self, presence_status, peeking_status):
        self.label_presence.config(text=f"Presence: {'Detected' if presence_status else 'Not Detected'}")
        self.label_peeking.config(text=f"Peeking: {'Detected' if peeking_status else 'Not Detected'}")
        root.update_idletasks()

gui = RadarGUI(root)

root.mainloop()