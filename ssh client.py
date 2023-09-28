import importlib
import subprocess
import tkinter as tk
import tkinter.scrolledtext as scrolledtext
from tkinter import ttk, filedialog
import paramiko
import threading
import json
import re
from colorama import init, Fore, Back, Style

# Initialize colorama
init()

# Define a regular expression pattern to match ANSI escape codes
ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# Define ANSI color codes for text formatting
ansi_colors = {
    '0': Style.RESET_ALL,
    '1': Style.BRIGHT,
    '30': Fore.BLACK,
    '31': Fore.RED,
    '32': Fore.GREEN,
    '33': Fore.YELLOW,
    '34': Fore.BLUE,
    '35': Fore.MAGENTA,
    '36': Fore.CYAN,
    '37': Fore.WHITE,
    '40': Back.BLACK,
    '41': Back.RED,
    '42': Back.GREEN,
    '43': Back.YELLOW,
    '44': Back.BLUE,
    '45': Back.MAGENTA,
    '46': Back.CYAN,
    '47': Back.WHITE,
}

# Create main window
root = tk.Tk()
root.title("SSH Client")

# Define color constants for dark and light modes
COLOR_DARK_BACKGROUND = 'gray15'
COLOR_LIGHT_BACKGROUND = 'white'
COLOR_STDOUT = 'white'
COLOR_STDERR = 'red'
COLOR_TEXT_DARK = 'white'
COLOR_TEXT_LIGHT = 'black'

# Set the initial dark mode to True
dark_mode = True

# Initialize style
style = ttk.Style()

# Define custom button styles for dark mode
style.configure("TButton", background="white", foreground="black")
style.configure("DarkButton.TButton", background="dark gray", foreground="white")
style.configure("Dark.TEntry", fieldbackground=COLOR_DARK_BACKGROUND, foreground=COLOR_TEXT_DARK)
style.configure("Light.TEntry", fieldbackground=COLOR_LIGHT_BACKGROUND, foreground=COLOR_TEXT_LIGHT)

def toggle_dark_mode():
    global dark_mode
    dark_mode = not dark_mode
    configure_ui_colors()
    configure_entry_colors()
    if dark_mode:
        style.theme_use("clam")
        dark_mode_button.configure(text="Toggle Light Mode")
    else:
        style.theme_use("default")
        dark_mode_button.configure(text="Toggle Dark Mode")

def configure_ui_colors():
    if dark_mode:
        root.configure(bg=COLOR_DARK_BACKGROUND)
        terminal1.config(bg=COLOR_DARK_BACKGROUND, fg=COLOR_TEXT_DARK)
        style.configure("TEntry", fieldbackground=COLOR_DARK_BACKGROUND, foreground=COLOR_TEXT_DARK)
        send_button.configure(style="DarkButton.TButton")
    else:
        root.configure(bg=COLOR_LIGHT_BACKGROUND)
        terminal1.config(bg=COLOR_LIGHT_BACKGROUND, fg=COLOR_TEXT_LIGHT)
        style.configure("TEntry", fieldbackground=COLOR_LIGHT_BACKGROUND, foreground=COLOR_TEXT_LIGHT)
        send_button.configure(style="TButton")

def configure_entry_colors():
    entry_style = "Dark.TEntry" if dark_mode else "Light.TEntry"
    host_entry.configure(style=entry_style)
    username_entry.configure(style=entry_style)
    password_entry.configure(style=entry_style)

# Save/load session details
def save_sessions(sessions):
    file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
    if file_path:
        with open(file_path, 'w') as f:
            json.dump(sessions, f)

def load_sessions():
    file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
    if file_path:
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            pass
    return []

# Update configure_terminal_colors function
def configure_terminal_colors():
    # ANSI escape codes for text formatting
    if dark_mode:
        terminal1.config(bg=COLOR_DARK_BACKGROUND)
        terminal1.tag_configure('stdout', foreground=COLOR_STDOUT, background=COLOR_DARK_BACKGROUND)
        terminal1.tag_configure('stderr', foreground=COLOR_STDERR, background=COLOR_DARK_BACKGROUND)
    else:
        terminal1.config(bg=COLOR_DARK_BACKGROUND)  # Always set the background to gray15
        terminal1.tag_configure('stdout', foreground=COLOR_STDOUT, background=COLOR_DARK_BACKGROUND)
        terminal1.tag_configure('stderr', foreground=COLOR_STDERR, background=COLOR_DARK_BACKGROUND)

# Function to display text in the terminal with ANSI color codes
def insert_terminal_text(text, tag):
    formatted_text = ""
    segments = ansi_escape.split(text)
    
    for segment in segments:
        if segment.startswith('\x1b['):
            # Extract ANSI color code
            color_code = re.search(r'\x1b\[(.*?)m', segment).group(1)
            
            # Check if the color code is in ansi_colors dictionary
            if color_code in ansi_colors:
                formatted_text += ansi_colors[color_code]
            else:
                formatted_text += Fore.RESET  # Default to reset the color
            
            # Add the segment text (excluding the ANSI code) to the output
            formatted_text += segment.split('m', 1)[-1]
        else:
            formatted_text += segment

    terminal1.insert(tk.END, formatted_text, tag)
    terminal1.see(tk.END)


# Tabbed interface
notebook = ttk.Notebook(root)

terminal1 = scrolledtext.ScrolledText(notebook)
notebook.add(terminal1, text="Terminal 1")
notebook.grid(row=0, column=1, columnspan=2, sticky="nsew")

# Sidebar
sidebar = ttk.Frame(root)
sidebar.grid(row=0, column=0, sticky="ns")

# Dark Mode button in sidebar
dark_mode_button = ttk.Button(sidebar, text="Toggle Dark Mode", command=toggle_dark_mode)
dark_mode_button.pack(fill=tk.X, pady=(10, 0))

# Password entry with Enter key binding removed
password_entry = ttk.Entry(root, show="*")
password_entry.grid(row=5, column=2, pady=5, padx=5)
password_entry.unbind('<Return>')

# Save Session button in sidebar
sessions = []

def save_session():
    global sessions
    host = host_entry.get()
    username = username_entry.get()
    password = password_entry.get()
    sessions.append({"host": host, "username": username, "password": password})
    save_sessions(sessions)

save_session_button = ttk.Button(sidebar, text="Save Session", command=save_session)
save_session_button.pack(fill=tk.X, pady=(10, 0))

def load_and_populate_sessions():
    global sessions
    sessions = load_sessions()
    if sessions:
        session = sessions[0]
        host_entry.delete(0, tk.END)
        host_entry.insert(0, session.get('host', ''))
        username_entry.delete(0, tk.END)
        username_entry.insert(0, session.get('username', ''))
        password_entry.delete(0, tk.END)
        password_entry.insert(0, session.get('password', ''))

load_session_button = ttk.Button(sidebar, text="Load Session", command=load_and_populate_sessions)
load_session_button.pack(fill=tk.X, pady=(10, 0))

# SSH connection function
channel = None


def connect_ssh(host, username, password):
    global channel
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=username, password=password)
        channel = ssh.invoke_shell()  # Initialize the channel here
    except paramiko.AuthenticationException as e:
        print(f"Authentication failed: {e}")
        return

def read_stdout():
    global channel  # Make sure to use the global channel variable
    while True:
        if channel is not None:  # Check if the channel is initialized
            data = channel.recv(1024)
            if not data:
                break
            decoded_data = data.decode("utf-8")
            formatted_data = decoded_data if dark_mode else f"\x1B[37;48;5;231m{decoded_data}\x1B[0m"
            insert_terminal_text(formatted_data, 'stdout')

threading.Thread(target=read_stdout).start()

# Function to send a command
def send_command(event=None):
    command = command_entry.get() + "\n"
    if channel:
        channel.send(command)
    command_entry.delete(0, 'end')

command_entry = ttk.Entry(root)
command_entry.grid(row=2, column=1, columnspan=2, sticky="ew")
command_entry.bind("<Return>", send_command)

# Send button
send_button = ttk.Button(root, text="Send", command=send_command)
send_button.grid(row=2, column=3, sticky="w")

host_label = ttk.Label(root, text="Host:")
host_label.grid(row=3, column=1, pady=5, padx=5)

host_entry = ttk.Entry(root)
host_entry.grid(row=3, column=2, pady=5, padx=5)

username_label = ttk.Label(root, text="Username:")
username_label.grid(row=4, column=1, pady=5, padx=5)

username_entry = ttk.Entry(root)
username_entry.grid(row=4, column=2, pady=5, padx=5)

password_label = ttk.Label(root, text="Password:")
password_label.grid(row=5, column=1, pady=5, padx=5)

password_entry.grid(row=5, column=2, pady=5, padx=5)

ssh_button = ttk.Button(root,
                        text="Connect SSH",
                        command=lambda: connect_ssh(host_entry.get(),
                                                    username_entry.get(),
                                                    password_entry.get()))
ssh_button.grid(row=6, column=2, columnspan=5, pady=5, padx=5)

# Configure grid weights for resizing
root.grid_rowconfigure(1, weight=1)
root.columnconfigure(1, weight=1)

# Configure tags for terminal text
terminal1.tag_configure('stdout', foreground=COLOR_STDOUT, background=COLOR_DARK_BACKGROUND)
terminal1.tag_configure('stderr', foreground=COLOR_STDOUT, background=COLOR_DARK_BACKGROUND)

# Set the initial dark mode
toggle_dark_mode()
configure_terminal_colors()
configure_entry_colors()

root.mainloop()
