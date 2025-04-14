import tkinter as tk
from tkinter import messagebox
import threading
import pyperclip
import time
from clip_monitor import is_suspicious, monitor_clipboard, save_addresses, load_addresses
from similarity import similarity_score, hamming_similarity

# Initialize trusted_addresses 
trusted_addresses = load_addresses()

# Global variable to store the previously copied address
previous_address = None
monitoring_active = False  # Flag to track monitoring state
monitor_event = threading.Event()  # Event to control monitoring thread
monitor_thread = None  # To store the reference to the monitoring thread

# Detection and Monitoring Logic
def initial_check_similarity(suspicious_address, trusted_addresses, threshold=30):
    for trusted, label in trusted_addresses.items():
        sim_score = similarity_score(suspicious_address, trusted)
        hamming_sim = hamming_similarity(suspicious_address, trusted)
        
        # Combine or evaluate these scores (e.g., taking the max or an average)
        combined_similarity = (sim_score + hamming_sim) / 2  # Example combination
        
        print(f"[Initial Check] Similarity with {trusted} ({label}): {combined_similarity}")
        if combined_similarity >= threshold:
            return True  # Address is suspiciously similar
    return False  # Safe

def monitor_clipboard_thread():
    """Run the clipboard monitoring logic in a separate thread."""
    def callback(message, is_warning=False, suspicious_address=None, original_address=None):
        """Callback function to update the GUI."""
        global previous_address

        if not monitoring_active:
            return

        if is_warning and suspicious_address:
            suspicious_address_lower = suspicious_address.lower()

        # Skip duplicate warnings for same address
        if suspicious_address_lower == previous_address:
            print(f"Skipping duplicate warning for: {suspicious_address_lower}")
            return

        previous_address = suspicious_address_lower  # Update it early to avoid re-alerting

        if is_suspicious(suspicious_address_lower):
            if initial_check_similarity(suspicious_address_lower, trusted_addresses, threshold=30):
                message = f"⚠️ Warning: {suspicious_address} is similar to an address in your address book."
            else:
                message = f"⚠️ Warning: Address: {suspicious_address} is similar to a previously copied address"

            root.after(0, show_warning, message)
            root.after(0, update_gui, message)
    while True: 
        if monitor_event.is_set():  # Only monitor if the event is set
            monitor_clipboard(callback) 
        else:
            time.sleep(1)  # Prevent CPU overloading when not monitoring

def toggle_monitoring():
    global monitoring_active
    if not monitoring_active:
        start_monitoring()
    else:
        pause_monitoring()

def start_monitoring():
    global monitoring_active, monitor_thread
    if not monitoring_active:
        print("Starting clipboard monitoring.")
        monitoring_active = True
        monitor_event.set()

        # Start the monitoring thread if it isn't already running
        if monitor_thread is None or not monitor_thread.is_alive():
            monitor_thread = threading.Thread(target=monitor_clipboard_thread, daemon=True)
            monitor_thread.start()

        monitor_button.config(text="Pause Monitoring")
    else:
        print("Monitoring is already active.")

def pause_monitoring():
    """Pause the clipboard monitoring."""
    global monitoring_active
    if monitoring_active:
        print("Pausing clipboard monitoring.")
        monitoring_active = False
        monitor_event.clear()  # Stop the monitoring thread
        monitor_button.config(text="Resume Monitoring")  # Change button text to 'Resume Monitoring'
    else:
        print("Monitoring is already paused.")

def resume_monitoring():
    """Resume the clipboard monitoring."""
    global monitoring_active
    if not monitoring_active:
        print("Resuming clipboard monitoring.")
        monitoring_active = True
        monitor_event.set()  # Restart the monitoring thread
        monitor_button.config(text="Pause Monitoring")  # Change button text to 'Pause Monitoring'
    else:
        print("Monitoring is already active.") 

# Address Book Management
def add_trusted_address():
    global trusted_addresses
    address = trusted_address_entry.get().strip().lower()
    label = label_entry.get().strip()
    if address:
        trusted_addresses[address] = label
        save_addresses(trusted_addresses)
        # Reload addresses to update the current session's view
        trusted_addresses = load_addresses()
        trusted_address_entry.delete(0, tk.END)
        label_entry.delete(0, tk.END)

        # Show the popup in the main GUI thread
        root.after(0, lambda: messagebox.showinfo("Success", "Address added to address book."))
    else:
        root.after(0, lambda: messagebox.showwarning("Input Error", "Please enter a valid address."))

def remove_trusted_address():
    global trusted_addresses
    address = trusted_address_entry.get().strip().lower()
    if address in trusted_addresses:
        del trusted_addresses[address]
        save_addresses(trusted_addresses)
        # Reload addresses to update the current session's view
        trusted_addresses = load_addresses()
        trusted_address_entry.delete(0, tk.END)

        root.after(0, lambda: messagebox.showinfo("Success", "Address removed from address book."))
    else:
        root.after(0, lambda: messagebox.showwarning("Not Found", "Address not found in trusted list."))

def show_trusted_addresses():
    """Displays the trusted addresses in a labeled list."""
    if trusted_addresses:
        # Ensure trusted_addresses is a dictionary
        if isinstance(trusted_addresses, dict):
            numbered_addresses = [
                f"{index + 1}. {address} - {label}" for index, (address, label) in enumerate(trusted_addresses.items())
            ]
            messagebox.showinfo("Trusted Addresses", "\n".join(numbered_addresses))
        else:
            messagebox.showerror("Error", "Trusted addresses data is corrupted.")
    else:
        messagebox.showinfo("No Trusted Addresses", "You have no addresses in address book.")

# Clipboard and GUI Helpers
def clear_clipboard():
    """Clears clipboard content and stored previous address history."""
    global previous_address
    pyperclip.copy("")  
    previous_address = None  
    messagebox.showinfo("Info", "Clipboard cleared.")

def update_gui(message):
    """Update the Text widget with new messages."""
    text_widget.insert(tk.END, message + '\n')
    text_widget.yview(tk.END)  

def show_warning(warning):
    """Show a warning message in the GUI."""
    messagebox.showwarning("Suspicious Address Detected", warning)

# GUI Setup
def main():
    try:
        global root, trusted_address_label, trusted_address_entry, label_entry
        global add_trusted_button, remove_trusted_button, view_trusted_button, clear_button
        global monitor_button, text_widget
    
        root = tk.Tk()
        root.title("ClipShield")

        root.configure()  
        root.geometry("400x500")
    
        # Create frames for layout
        control_frame = tk.Frame(root)  
        control_frame.pack(pady=10)

        log_frame = tk.Frame(root)
        log_frame.pack(pady=2)
    
        # Trusted address input
        trusted_address_label = tk.Label(control_frame, text="Enter a Trusted Address:", font=("Arial", 12), fg="white")
        trusted_address_label.pack(pady=2)
        
        trusted_address_entry = tk.Entry(
            control_frame,
            font=("Arial", 12),
            width=41,
            bg="white",
            fg="black"
        )
        trusted_address_entry.pack(pady=5)

        # Label for address input
        label_label = tk.Label(control_frame, text="Label your address:", font=("Arial", 12), fg="white")
        label_label.pack(pady=2)

        label_entry = tk.Entry(
            control_frame,
            font=("Arial", 12),
            width=41,
            bg="white",
            fg="black"
        )
        label_entry.pack(pady=5)
        
        button_style = {
            "width": 33,
            "bg": "white",
            "fg": "black",
            "bd": 1,
            "font": ("Arial", 14)
        }
        
        add_trusted_button = tk.Button(control_frame, text="Add Trusted Address", command=add_trusted_address, **button_style)
        add_trusted_button.pack(pady=5)
        
        remove_trusted_button = tk.Button(control_frame, text="Remove Trusted Address", command=remove_trusted_address, **button_style)
        remove_trusted_button.pack(pady=5)
        
        view_trusted_button = tk.Button(control_frame, text="View Address Book", command=show_trusted_addresses, **button_style)
        view_trusted_button.pack(pady=5)
        
        clear_button = tk.Button(control_frame, text="Clear Clipboard", command=clear_clipboard, **button_style)
        clear_button.pack(pady=10)
        
        monitor_button = tk.Button(control_frame, text="Start Monitoring", command=toggle_monitoring, **button_style)
        monitor_button.pack(pady=10)

        text_widget = tk.Text(log_frame, height=15, width=50, font=("Arial", 12))
        text_widget.pack(pady=5)

        # Delay start_monitoring to ensure GUI is ready
        root.after(1000, start_monitoring)  # Delay by 1 second

        root.mainloop()

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()