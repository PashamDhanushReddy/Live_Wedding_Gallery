"""
Wedding Photo Uploader
Desktop Tool for Live Wedding Gallery
Uploads photos directly to the Android Companion Tablet (FTP) or Gallery Cloud.
"""
import os
import sys
import ftplib
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

DEFAULT_HOST = "192.168.1.106"
DEFAULT_PORT = "2121"
DEFAULT_USER = "dhanush"
DEFAULT_PASS = "Anime@123"

EVENT_FOLDERS = [
    "Wedding Day",
    "Haldi",
    "Pre-wedding Shoot",
    "Before Wedding Rituals",
    "Engagement",
    "Reception",
    "Sangeet",
    "Mehendi",
    "Uncategorized"
]

class WeddingPhotoUploader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Live Wedding Gallery - Photo Uploader")
        self.geometry("640x620")
        self.minsize(580, 560)
        self.configure(bg="#F9FAFB")

        self.selected_files = []
        self.uploading = False

        self.setup_ui()

    def setup_ui(self):
        # Header
        header_frame = tk.Frame(self, bg="#4F46E5", pady=14, padx=20)
        header_frame.pack(fill="x")

        title_lbl = tk.Label(
            header_frame,
            text="Wedding Photo Uploader",
            font=("Segoe UI", 16, "bold"),
            fg="white",
            bg="#4F46E5"
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = tk.Label(
            header_frame,
            text="Send DSLR / Sony photos directly to Android Tablet or Gallery",
            font=("Segoe UI", 9),
            fg="#E0E7FF",
            bg="#4F46E5"
        )
        subtitle_lbl.pack(anchor="w")

        content = tk.Frame(self, bg="#F9FAFB", padx=20, pady=12)
        content.pack(fill="both", expand=True)

        # Connection Settings Frame
        conn_frame = tk.LabelFrame(
            content,
            text=" FTP Server Settings (Tablet) ",
            font=("Segoe UI", 9, "bold"),
            bg="#F9FAFB",
            padx=12,
            pady=8
        )
        conn_frame.pack(fill="x", pady=(0, 10))

        # Row 1: Host and Port
        row1 = tk.Frame(conn_frame, bg="#F9FAFB")
        row1.pack(fill="x", pady=2)

        tk.Label(row1, text="Tablet IP:", font=("Segoe UI", 9), bg="#F9FAFB", width=10, anchor="w").pack(side="left")
        self.host_entry = tk.Entry(row1, font=("Segoe UI", 9), width=20)
        self.host_entry.insert(0, DEFAULT_HOST)
        self.host_entry.pack(side="left", padx=(0, 15))

        tk.Label(row1, text="Port:", font=("Segoe UI", 9), bg="#F9FAFB", width=5, anchor="w").pack(side="left")
        self.port_entry = tk.Entry(row1, font=("Segoe UI", 9), width=8)
        self.port_entry.insert(0, DEFAULT_PORT)
        self.port_entry.pack(side="left")

        # Row 2: User and Password
        row2 = tk.Frame(conn_frame, bg="#F9FAFB")
        row2.pack(fill="x", pady=4)

        tk.Label(row2, text="Username:", font=("Segoe UI", 9), bg="#F9FAFB", width=10, anchor="w").pack(side="left")
        self.user_entry = tk.Entry(row2, font=("Segoe UI", 9), width=20)
        self.user_entry.insert(0, DEFAULT_USER)
        self.user_entry.pack(side="left", padx=(0, 15))

        tk.Label(row2, text="Password:", font=("Segoe UI", 9), bg="#F9FAFB", width=8, anchor="w").pack(side="left")
        self.pass_entry = tk.Entry(row2, font=("Segoe UI", 9), width=14, show="*")
        self.pass_entry.insert(0, DEFAULT_PASS)
        self.pass_entry.pack(side="left")

        # Event Folder Selection Frame
        folder_frame = tk.LabelFrame(
            content,
            text=" Target Event Folder ",
            font=("Segoe UI", 9, "bold"),
            bg="#F9FAFB",
            padx=12,
            pady=8
        )
        folder_frame.pack(fill="x", pady=(0, 10))

        f_row = tk.Frame(folder_frame, bg="#F9FAFB")
        f_row.pack(fill="x", pady=2)

        tk.Label(f_row, text="Event Category:", font=("Segoe UI", 9), bg="#F9FAFB", width=14, anchor="w").pack(side="left")
        self.folder_var = tk.StringVar(value=EVENT_FOLDERS[0])
        self.folder_dropdown = ttk.Combobox(
            f_row,
            textvariable=self.folder_var,
            values=EVENT_FOLDERS,
            state="readonly",
            font=("Segoe UI", 9),
            width=24
        )
        self.folder_dropdown.pack(side="left", padx=(0, 10))

        # File Selection Frame
        file_frame = tk.LabelFrame(
            content,
            text=" Select Photographs ",
            font=("Segoe UI", 9, "bold"),
            bg="#F9FAFB",
            padx=12,
            pady=8
        )
        file_frame.pack(fill="x", pady=(0, 10))

        btn_row = tk.Frame(file_frame, bg="#F9FAFB")
        btn_row.pack(fill="x", pady=2)

        self.btn_select_files = tk.Button(
            btn_row,
            text="📁 Select Photos...",
            font=("Segoe UI", 9),
            bg="#EEF2FF",
            fg="#4338CA",
            relief="groove",
            command=self.choose_files,
            padx=10,
            pady=4
        )
        self.btn_select_files.pack(side="left", padx=(0, 8))

        self.btn_select_dir = tk.Button(
            btn_row,
            text="📂 Select SD Card / Folder...",
            font=("Segoe UI", 9),
            bg="#EEF2FF",
            fg="#4338CA",
            relief="groove",
            command=self.choose_directory,
            padx=10,
            pady=4
        )
        self.btn_select_dir.pack(side="left", padx=(0, 8))

        self.btn_clear = tk.Button(
            btn_row,
            text="Clear",
            font=("Segoe UI", 9),
            bg="#F3F4F6",
            command=self.clear_selection,
            padx=8,
            pady=4
        )
        self.btn_clear.pack(side="right")

        self.file_count_lbl = tk.Label(
            file_frame,
            text="No photos selected yet.",
            font=("Segoe UI", 9, "italic"),
            fg="#6B7280",
            bg="#F9FAFB"
        )
        self.file_count_lbl.pack(anchor="w", pady=(4, 0))

        # Progress Frame
        prog_frame = tk.Frame(content, bg="#F9FAFB")
        prog_frame.pack(fill="x", pady=(0, 10))

        self.progress_bar = ttk.Progressbar(prog_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", pady=(0, 4))

        self.status_lbl = tk.Label(
            prog_frame,
            text="Ready to upload.",
            font=("Segoe UI", 9),
            fg="#374151",
            bg="#F9FAFB",
            anchor="w"
        )
        self.status_lbl.pack(fill="x")

        # Log Output Box
        log_frame = tk.LabelFrame(
            content,
            text=" Activity Log ",
            font=("Segoe UI", 9, "bold"),
            bg="#F9FAFB",
            padx=6,
            pady=6
        )
        log_frame.pack(fill="both", expand=True, pady=(0, 10))

        self.log_text = tk.Text(log_frame, height=6, font=("Consolas", 8), bg="#FFFFFF", fg="#1F2937")
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)

        # Action Buttons
        action_row = tk.Frame(content, bg="#F9FAFB")
        action_row.pack(fill="x")

        self.btn_upload = tk.Button(
            action_row,
            text="🚀 Start Upload to Tablet (FTP)",
            font=("Segoe UI", 10, "bold"),
            bg="#4F46E5",
            fg="white",
            relief="raised",
            command=self.start_upload,
            padx=16,
            pady=6,
            cursor="hand2"
        )
        self.btn_upload.pack(side="left", padx=(0, 10))

        self.btn_shortcut = tk.Button(
            action_row,
            text="📌 Open Windows Network Location",
            font=("Segoe UI", 9),
            bg="#F3F4F6",
            fg="#374151",
            relief="groove",
            command=self.open_network_location,
            padx=10,
            pady=6
        )
        self.btn_shortcut.pack(side="right")

    def log(self, message):
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def choose_files(self):
        files = filedialog.askopenfilenames(
            title="Select Photos",
            filetypes=[("Image files", "*.jpg;*.jpeg;*.JPG;*.JPEG;*.png;*.PNG;*.arw;*.cr2;*.nef")]
        )
        if files:
            self.selected_files = list(files)
            self.file_count_lbl.config(
                text=f"{len(self.selected_files)} photos selected.",
                fg="#16A34A"
            )
            self.log(f"Selected {len(self.selected_files)} photos.")

    def choose_directory(self):
        dir_path = filedialog.askdirectory(title="Select Folder / SD Card")
        if dir_path:
            valid_exts = {".jpg", ".jpeg", ".png", ".arw", ".cr2", ".nef"}
            found = []
            for root, _, filenames in os.walk(dir_path):
                for f in filenames:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in valid_exts:
                        found.append(os.path.join(root, f))
            if found:
                self.selected_files = found
                self.file_count_lbl.config(
                    text=f"{len(self.selected_files)} photos found in folder.",
                    fg="#16A34A"
                )
                self.log(f"Found {len(self.selected_files)} photos in {dir_path}")
            else:
                messagebox.showinfo("No Photos", "No JPG/PNG/RAW photos found in selected directory.")

    def clear_selection(self):
        self.selected_files = []
        self.file_count_lbl.config(text="No photos selected yet.", fg="#6B7280")
        self.progress_bar["value"] = 0
        self.status_lbl.config(text="Ready to upload.")

    def start_upload(self):
        if not self.selected_files:
            messagebox.showwarning("No Photos", "Please select photos or a folder first.")
            return

        if self.uploading:
            return

        host = self.host_entry.get().strip()
        port = int(self.port_entry.get().strip() or "2121")
        user = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()
        folder = self.folder_var.get().strip()

        self.uploading = True
        self.btn_upload.config(state="disabled", text="Uploading...")
        self.btn_select_files.config(state="disabled")
        self.btn_select_dir.config(state="disabled")

        thread = threading.Thread(
            target=self.upload_worker,
            args=(host, port, user, password, folder),
            daemon=True
        )
        thread.start()

    def upload_worker(self, host, port, user, password, folder):
        total = len(self.selected_files)
        success_count = 0
        failed_count = 0

        self.log(f"--- Starting FTP Upload of {total} photos to {host}:{port} [{folder}] ---")

        try:
            ftp = ftplib.FTP()
            ftp.connect(host, port, timeout=15)
            ftp.login(user, password)
            ftp.set_pasv(True)
            self.log(f"Connected to FTP server successfully as '{user}'.")

            # Try to navigate into event subfolder or create it
            safe_folder = folder.replace(" ", "_")
            try:
                ftp.cwd(safe_folder)
            except Exception:
                try:
                    ftp.mkd(safe_folder)
                    ftp.cwd(safe_folder)
                    self.log(f"Created subfolder '{safe_folder}' on server.")
                except Exception:
                    pass # Upload directly to current root if subfolders not supported

            for i, file_path in enumerate(self.selected_files, 1):
                filename = os.path.basename(file_path)
                self.status_lbl.config(text=f"Uploading {i}/{total}: {filename}...")
                self.progress_bar["value"] = int(((i - 1) / total) * 100)

                try:
                    with open(file_path, "rb") as fp:
                        ftp.storbinary(f"STOR {filename}", fp, blocksize=65536)
                    success_count += 1
                    self.log(f"[{i}/{total}] OK: {filename}")
                except Exception as e:
                    failed_count += 1
                    self.log(f"[{i}/{total}] FAIL {filename}: {e}")

            ftp.quit()
            self.progress_bar["value"] = 100
            self.status_lbl.config(text=f"Finished! {success_count} forwarded, {failed_count} failed.")
            self.log(f"--- Completed: {success_count} sent, {failed_count} failed ---")
            messagebox.showinfo(
                "Upload Complete",
                f"Successfully forwarded {success_count} photos to the tablet!\n"
                f"Failed: {failed_count}"
            )

        except Exception as e:
            self.log(f"Connection Error: {e}")
            messagebox.showerror(
                "FTP Connection Failed",
                f"Could not connect to FTP server at {host}:{port}.\n\n"
                f"Details: {e}\n\n"
                f"Make sure:\n"
                f"1. Tablet and PC are on the same Wi-Fi.\n"
                f"2. Wedding Companion app is open and 'Active' on the tablet."
            )
        finally:
            self.uploading = False
            self.btn_upload.config(state="normal", text="🚀 Start Upload to Tablet (FTP)")
            self.btn_select_files.config(state="normal")
            self.btn_select_dir.config(state="normal")

    def open_network_location(self):
        host = self.host_entry.get().strip()
        port = self.port_entry.get().strip() or "2121"
        user = self.user_entry.get().strip()
        # In Windows File Explorer, opening via explorer.exe
        # URL encoding @ in password to %40 is mandatory for explorer.exe
        ftp_url = f"ftp://{user}:{DEFAULT_PASS.replace('@', '%40')}@{host}:{port}/"
        os.system(f'start explorer.exe "{ftp_url}"')

if __name__ == "__main__":
    app = WeddingPhotoUploader()
    app.mainloop()
