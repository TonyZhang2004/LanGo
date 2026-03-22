import tkinter as tk
from tkinter import ttk

def on_click():
    status_label.config(text="Button clicked!")

root = tk.Tk()
root.title("My App")
root.attributes('-fullscreen', True)
root.configure(bg="#f5f7fa")

def exit_fullscreen(event=None):
    root.attributes('-fullscreen', False)

root.bind("<Escape>", exit_fullscreen)

# ---------- STYLE ----------
style = ttk.Style()
style.theme_use("clam")

style.configure(
    "Custom.TButton",
    font=("Helvetica", 22, "bold"),
    padding=15,
    foreground="white",
    background="#4a90e2",
    borderwidth=0
)

style.map(
    "Custom.TButton",
    background=[("active", "#357abd"), ("pressed", "#2f69a3")]
)

# ---------- MAIN CONTAINER ----------
main_frame = tk.Frame(root, bg="#f5f7fa")
main_frame.pack(expand=True)

# ---------- TITLE ----------
title = tk.Label(
    main_frame,
    text="My App",
    font=("Helvetica", 36, "bold"),
    bg="#f5f7fa",
    fg="#1f2933"
)
title.pack(pady=(0, 30))

# ---------- BUTTON ----------
button = ttk.Button(
    main_frame,
    text="Click Me",
    command=on_click,
    style="Custom.TButton"
)
button.pack(ipadx=30, ipady=10)

# ---------- STATUS TEXT ----------
status_label = tk.Label(
    main_frame,
    text="Waiting...",
    font=("Helvetica", 18),
    bg="#f5f7fa",
    fg="#52606d"
)
status_label.pack(pady=(30, 0))

root.mainloop()