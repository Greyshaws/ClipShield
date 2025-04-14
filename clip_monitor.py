import pyperclip
import time
import re
import threading
import json
import os
from similarity import similarity_score, hamming_similarity, calculate_dynamic_threshold

# Stores previously copied addresses
previously_copied_addresses = []

# Stores trusted addresses manually added by the user
trusted_addresses = []

# File to store trusted addresses and wallet addresses
DATA_FILE = "addresses_data.json"

# Ethereum address pattern
ETH_ADDRESS_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")
# Bitcoin address pattern (for legacy, P2PKH)
BTC_ADDRESS_REGEX = re.compile(r"^(1[a-km-zA-HJ-NP-Z0-9]{25,34})$")
# Binance Smart Chain (BSC) address pattern
BSC_ADDRESS_REGEX = ETH_ADDRESS_REGEX

def is_valid_address(address):
    """Checks if the address is valid for any supported blockchain format."""
    return (
        bool(ETH_ADDRESS_REGEX.match(address)) or
        bool(BTC_ADDRESS_REGEX.match(address)) or
        bool(BSC_ADDRESS_REGEX.match(address))
    )

def is_suspicious(copied_address):
    """Checks if the copied address is suspicious."""
    global previously_copied_addresses, trusted_addresses

    copied_address = copied_address.strip().lower()

    # Calculate dynamic threshold based on the copied address
    dynamic_threshold = calculate_dynamic_threshold(copied_address)

    if copied_address in trusted_addresses:
        return False
     
    # Compare with trusted addresses
    for trusted in trusted_addresses:
        trusted = trusted.lower()  # Convert trusted address to lowercase
        lev_sim = similarity_score(copied_address, trusted)
        ham_sim = hamming_similarity(copied_address, trusted)
        combined_score = (lev_sim + ham_sim) / 2
        prefix_match = copied_address[:10] == trusted[:10]
        suffix_match = copied_address[-10:] == trusted[-10:]

        if (lev_sim > dynamic_threshold or ham_sim > dynamic_threshold or combined_score > dynamic_threshold) or prefix_match or suffix_match:
            print(f"⚠️ Address is similar to a trusted address: {trusted}")
            pyperclip.copy("") 
            return True 

    # Compare with previously copied addresses
    for prev_address in previously_copied_addresses:
        lev_sim = similarity_score(copied_address, prev_address)
        ham_sim = hamming_similarity(copied_address, prev_address)
        combined_score = (lev_sim + ham_sim) / 2
        prefix_match = copied_address[:10] == prev_address[:10]
        suffix_match = copied_address[-10:] == prev_address[-10:]

        if (lev_sim > dynamic_threshold or ham_sim > dynamic_threshold or combined_score > dynamic_threshold) or prefix_match or suffix_match:
            print(f"⚠️ Address is similar to previously copied address")
            pyperclip.copy("")
            return True 

    return False  

def show_clipboard_history():
    """Displays previously copied addresses."""
    if previously_copied_addresses:
        print("\n📋 Previously Copied Addresses:")
        for addr in previously_copied_addresses:
            print(addr)
    else:
        print("\nℹ️ No addresses copied yet.")

def clear_clipboard():
    """Clears clipboard and history."""
    global previously_copied_addresses
    previously_copied_addresses.clear()
    pyperclip.copy("")
    print("✅ Clipboard cleared.")

def add_trusted_address():
    """Allows the user to add a trusted address"""
    global trusted_addresses
    while True:
        print("\n🔹 Do you want to add, view, or remove trusted addresses? (add/view/remove/exit): ")
        action = input().strip().lower()

        if action == "add":
            print("Enter a trusted address to whitelist: ")
            new_trusted = input().strip()
            if is_valid_address(new_trusted):
                trusted_addresses.append(new_trusted.lower())
                save_addresses(trusted_addresses)  # Save after adding
                print(f"✅ Trusted address added: {new_trusted}")
            else:
                print("❌ Invalid address format. Please try again.")

        elif action == "view":
            if trusted_addresses:
                print("\n📋 Your current trusted addresses:")
                for i, addr in enumerate(trusted_addresses, 1):
                    print(f"{i}. {addr}")
            else:
                print("❌ No trusted addresses available.")

        elif action == "remove":
            if trusted_addresses:
                print("\n📋 Your current trusted addresses:")
                for i, addr in enumerate(trusted_addresses, 1):
                    print(f"{i}. {addr}")
                print("\nEnter the number of the address to remove: ")
                try:
                    address_to_remove = int(input())
                    if 0 < address_to_remove <= len(trusted_addresses):
                        removed_address = trusted_addresses.pop(address_to_remove - 1)
                        save_addresses(trusted_addresses)  # Save after removing
                        print(f"✅ Trusted address removed: {removed_address}")
                    else:
                        print("❌ Invalid number. Please try again.")
                except ValueError:
                    print("❌ Invalid input. Please enter a valid number.")
            else:
                print("❌ No trusted addresses to remove.")

        elif action == "exit":
            print("\n🔹 Exiting trusted address management.")
            break
        
        else:
            print("❌ Invalid option. Please enter 'add', 'remove', 'view', or 'exit'.")

def monitor_clipboard(callback=None):
    """Monitors clipboard for similar addresses."""
    try:
        previous_clipboard = pyperclip.paste() or ""
    except Exception as e:
        print(f"Clipboard access error: {e}")
        previous_clipboard = ""

    current_clipboard = previous_clipboard
    last_valid_address = None

    if previous_clipboard and isinstance(previous_clipboard, str):
        if is_valid_address(previous_clipboard) and previous_clipboard not in previously_copied_addresses:
            is_suspicious_flag = is_suspicious(previous_clipboard)
            if is_suspicious_flag:
                print(f"⚠️ Warning: Similar address detected!")
                if callback:
                    callback(
                        "⚠️ Warning: Similar address detected!",
                        is_warning=True,
                        suspicious_address=previous_clipboard,
                        original_address=last_valid_address
                    )
            else:
                print(f"✅ Address is safe: {previous_clipboard}")
                previously_copied_addresses.append(previous_clipboard)
                last_valid_address = previous_clipboard 

    while True:
        try:
            current_clipboard = pyperclip.paste()
        except Exception as e:
            print(f"Clipboard access error: {e}")
            time.sleep(1)
            continue

        if not current_clipboard or not isinstance(current_clipboard, str):
            time.sleep(1)
            continue

        if current_clipboard != previous_clipboard:
            previous_clipboard = current_clipboard

            if is_valid_address(current_clipboard) and current_clipboard not in previously_copied_addresses:
                is_suspicious_flag = is_suspicious(current_clipboard)
                if is_suspicious_flag:
                    print(f"⚠️ Warning: Similar address detected!")
                    if callback:
                        callback(
                            "⚠️ Warning: Similar address detected!",
                            is_warning=True,
                            suspicious_address=current_clipboard,
                            original_address=last_valid_address
                        )
                else:
                    print(f"✅ Address is safe: {current_clipboard}")
                    previously_copied_addresses.append(current_clipboard)
                    last_valid_address = current_clipboard

        time.sleep(1)

def handle_suspicious_clipboard(copied_address, is_warning):
    if is_warning:
        print(f"\n❗ Similar address detected: {copied_address}")
    else:
        print(f"✅ Address is safe: {copied_address}")

def load_addresses():
    """Load trusted from the JSON file."""
    global trusted_addresses

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                
                # Ensure trusted_addresses is a dictionary
                trusted_addresses = data.get("trusted_addresses", {})
                
                # Check if trusted_addresses is a dictionary
                if not isinstance(trusted_addresses, dict):
                    print("❌ Error: trusted_addresses is not a dictionary.")
                    trusted_addresses = {}  # Reset to an empty dictionary if the format is incorrect

                print("🔄 Loaded saved addresses.")
        except Exception as e:
            print(f"❌ Error loading addresses: {e}")
            trusted_addresses = {}
    else:
        trusted_addresses = {}

    return trusted_addresses

def save_addresses(trusted):
    data = {
        "trusted_addresses": trusted
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def user_command_listener():
    """Listens for user commands to interact with the tool."""
    while True:
        print("\n🔹 Available Commands:")
        print("1. Add trusted addresses")
        print("2. View clipboard history")
        print("3. Clear clipboard")
        print("4. Exit")

        command = input("Enter command: ").strip()

        if command == "1":
            add_trusted_address()
        elif command == "2":
            show_clipboard_history()
        elif command == "3":
            clear_clipboard()
        elif command == "4":
            print("\n🔹 Exiting the program.")
            break
        else:
            print("❌ Invalid command, please try again.")


if __name__ == "__main__":
    # Load existing addresses
    trusted_addresses = load_addresses()
    
    # Start monitoring in a background thread
    clipboard_monitor_thread = threading.Thread(target=monitor_clipboard)
    clipboard_monitor_thread.daemon = True
    clipboard_monitor_thread.start()
    
    # Start listening for user commands
    user_command_listener()