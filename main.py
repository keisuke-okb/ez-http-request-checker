import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import time
import os
import threading
import re
from datetime import datetime

class EZHttpRequestCheckerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.load_ui_texts()  # Load UI texts from ui_lang.json

        self.title(self.ui_texts.get("title", "EZ-HTTPRequestChecker"))
        self.geometry("1200x700")

        self.fixedfont = ctk.CTkFont(family="Consolas", size=12)

        # Folder for history files and file for saved requests/global variables
        self.history_folder = "history"
        self.request_file = "saved_requests.json"

        # Each request is a dict: {"method": ..., "description": ..., "url": ..., "headers": ..., "body": ...}
        self.saved_requests = []
        self.variable_dict = {}  # Global dictionary for variables (common to all requests)
        self.load_requests()  # Load saved requests and global variables from file

        self.current_request_index = None  # Currently selected request (None if none selected)

        # Left pane: Saved requests list (Treeview)
        self.left_frame = ctk.CTkFrame(self, width=250)
        self.left_frame.pack(side="left", fill="y", padx=5, pady=5)

        self.request_tree = ttk.Treeview(
            self.left_frame,
            columns=("method", "description", "url"),
            show="headings",
            selectmode="browse"
        )
        self.request_tree.heading("method", text=self.ui_texts.get("tree_heading_method", "Method"))
        self.request_tree.heading("description", text=self.ui_texts.get("tree_heading_description", "Description"))
        self.request_tree.heading("url", text=self.ui_texts.get("tree_heading_url", "URL"))
        self.request_tree.column("method", width=80, anchor="w")
        self.request_tree.column("description", width=100, anchor="w")
        self.request_tree.column("url", width=200, anchor="w")
        self.request_tree.pack(fill="both", expand=True, padx=5, pady=5)

        self.request_tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        self.new_button = ctk.CTkButton(self.left_frame, text=self.ui_texts.get("new_button", "New"), command=self.new_request)
        self.new_button.pack(padx=5, pady=5, fill="x")
        self.delete_button = ctk.CTkButton(self.left_frame, text=self.ui_texts.get("delete_button", "Delete"), command=self.delete_request)
        self.delete_button.pack(padx=5, pady=5, fill="x")

        # Right pane: Tab view for Request and Variables
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.tabview = ctk.CTkTabview(self.right_frame)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=5)
        self.request_tab = self.tabview.add(self.ui_texts.get("request_tab", "Request"))
        self.variables_tab = self.tabview.add(self.ui_texts.get("variables_tab", "Variables"))

        # Request Tab
        self.description_frame = ctk.CTkFrame(self.request_tab)
        self.description_frame.pack(fill="x", padx=5, pady=(5, 0))
        self.description_label = ctk.CTkLabel(self.description_frame, text=self.ui_texts.get("request_description_label", "Request Description"))
        self.description_label.pack(anchor="w", padx=5)
        self.description_entry = ctk.CTkEntry(self.description_frame, placeholder_text=self.ui_texts.get("request_description_placeholder", "Enter request description"))
        self.description_entry.pack(fill="x", padx=5, pady=5)

        self.top_frame = ctk.CTkFrame(self.request_tab)
        self.top_frame.pack(fill="x", padx=5, pady=5)
        self.method_var = ctk.StringVar(value="GET")
        self.method_option = ctk.CTkOptionMenu(
            self.top_frame,
            variable=self.method_var,
            values=["GET", "POST", "PUT", "DELETE"]
        )
        self.method_option.pack(side="left", padx=(0, 5))
        self.url_entry = ctk.CTkEntry(self.top_frame, placeholder_text=self.ui_texts.get("request_url_placeholder", "Request URL"), font=self.fixedfont)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.send_button = ctk.CTkButton(self.top_frame, text=self.ui_texts.get("send_button", "Send"), command=self.send_request)
        self.send_button.pack(side="left")

        self.headers_label = ctk.CTkLabel(self.request_tab, text=self.ui_texts.get("http_headers_label", "HTTP Headers (key: value per line)"))
        self.headers_label.pack(anchor="w", padx=5, pady=(10, 0))
        self.headers_textbox = ctk.CTkTextbox(self.request_tab, height=50, font=self.fixedfont)
        self.headers_textbox.pack(fill="x", padx=5, pady=5)

        self.body_label = ctk.CTkLabel(self.request_tab, text=self.ui_texts.get("http_body_label", "HTTP Body (JSON format)"))
        self.body_label.pack(anchor="w", padx=5, pady=(10, 0))
        self.body_textbox = ctk.CTkTextbox(self.request_tab, height=150, font=self.fixedfont)
        self.body_textbox.pack(fill="both", padx=5, pady=5, expand=True)

        self.response_info_label = ctk.CTkLabel(self.request_tab, text=self.ui_texts.get("response_label", "Response: "))
        self.response_info_label.pack(anchor="w", padx=5, pady=(10, 0))
        self.response_textbox = ctk.CTkTextbox(self.request_tab, height=150, font=self.fixedfont)
        self.response_textbox.pack(fill="both", padx=5, pady=5, expand=True)

        # Variables Tab
        self.variable_input_frame = ctk.CTkFrame(self.variables_tab)
        self.variable_input_frame.pack(fill="x", padx=5, pady=5)
        self.variable_name_entry = ctk.CTkEntry(self.variable_input_frame, placeholder_text=self.ui_texts.get("variable_name_placeholder", "Variable Name"))
        self.variable_name_entry.pack(side="left", fill="x", expand=True, padx=(5, 2))
        self.variable_value_entry = ctk.CTkEntry(self.variable_input_frame, placeholder_text=self.ui_texts.get("variable_value_placeholder", "Variable Value"))
        self.variable_value_entry.pack(side="left", fill="x", expand=True, padx=(2, 5))
        self.add_variable_button = ctk.CTkButton(self.variable_input_frame, text=self.ui_texts.get("add_variable_button", "Add Variable"), command=self.add_variable)
        self.add_variable_button.pack(side="left", padx=5)

        self.variables_tree = ttk.Treeview(self.variables_tab, columns=("name", "value"), show="headings", selectmode="browse")
        self.variables_tree.heading("name", text=self.ui_texts.get("variable_column_name", "Variable"))
        self.variables_tree.heading("value", text=self.ui_texts.get("value_column_name", "Value"))
        self.variables_tree.column("name", width=150, anchor="w")
        self.variables_tree.column("value", width=150, anchor="w")
        self.variables_tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.variables_tree.bind("<<TreeviewSelect>>", self.on_variable_select)

        self.delete_variable_button = ctk.CTkButton(self.variables_tab, text=self.ui_texts.get("delete_variable_button", "Delete Variable"), command=self.delete_variable)
        self.delete_variable_button.pack(padx=5, pady=(0, 5))

        self.refresh_request_list()
        self.refresh_variables_table()

    def load_ui_texts(self):
        """Load UI display texts from ui_lang.json"""
        try:
            with open("ui_lang.json", "r", encoding="utf-8") as f:
                self.ui_texts = json.load(f)
        except Exception as e:
            print("Error loading ui_lang.json:", e)
            self.ui_texts = {}

    def load_requests(self):
        """
        Load saved requests and global variables from file.
        The file structure is:
        {
          "requests": [ ... ],
          "global_variables": { ... }
        }
        """
        if os.path.exists(self.request_file):
            try:
                with open(self.request_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.saved_requests = data.get("requests", [])
                    self.variable_dict = data.get("global_variables", {})
            except Exception as e:
                print("Error loading requests:", e)
                self.saved_requests = []
                self.variable_dict = {}

    def save_requests(self):
        """
        Save current list of requests and global variables to file,
        using the following structure:
        {
          "requests": [ ... ],
          "global_variables": { ... }
        }
        """
        data = {
            "requests": self.saved_requests,
            "global_variables": self.variable_dict
        }
        try:
            with open(self.request_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print("Error saving requests:", e)

    def refresh_request_list(self):
        """Redraw the request list in the treeview"""
        for item in self.request_tree.get_children():
            self.request_tree.delete(item)
        for index, req in enumerate(self.saved_requests):
            method = req.get("method", "GET")
            description = req.get("description", "")
            url = req.get("url", "No URL")
            self.request_tree.insert("", "end", iid=str(index), values=(method, description, url))

    def refresh_variables_table(self):
        """Refresh the variables table in the Variables tab using self.variable_dict"""
        for item in self.variables_tree.get_children():
            self.variables_tree.delete(item)
        for var_name, var_value in self.variable_dict.items():
            self.variables_tree.insert("", "end", values=(var_name, var_value))

    def on_tree_select(self, event):
        """When a request is selected in the treeview, load its details into the editing areas"""
        selected_item = self.request_tree.selection()
        if selected_item:
            index = int(selected_item[0])
            self.load_request(index)

    def load_request(self, index):
        """Load the selected saved request into the editing areas (global variables remain unchanged)"""
        self.current_request_index = index
        req = self.saved_requests[index]
        self.method_var.set(req.get("method", "GET"))
        self.description_entry.delete(0, "end")
        self.description_entry.insert(0, req.get("description", ""))
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, req.get("url", ""))
        self.headers_textbox.delete("1.0", "end")
        self.headers_textbox.insert("1.0", req.get("headers", ""))
        self.body_textbox.delete("1.0", "end")
        self.body_textbox.insert("1.0", req.get("body", ""))

    def new_request(self):
        """Create a new request by clearing the editing areas and deselecting any current selection"""
        self.current_request_index = None
        self.method_var.set("GET")
        self.description_entry.delete(0, "end")
        self.url_entry.delete(0, "end")
        self.headers_textbox.delete("1.0", "end")
        self.body_textbox.delete("1.0", "end")
        self.response_textbox.delete("1.0", "end")
        self.response_info_label.configure(text=self.ui_texts.get("response_label", "Response: "))
        self.request_tree.selection_remove(self.request_tree.selection())

    def delete_request(self):
        """Delete the selected request and update the file"""
        if self.current_request_index is not None:
            del self.saved_requests[self.current_request_index]
            self.current_request_index = None
            self.refresh_request_list()
            self.new_request()
            self.save_requests()

    def add_variable(self):
        """Add or update a variable from the Variables tab input fields"""
        var_name = self.variable_name_entry.get().strip()
        var_value = self.variable_value_entry.get().strip()
        if not var_name:
            messagebox.showerror("Error", "Variable name is required!")
            return
        self.variable_dict[var_name] = var_value
        self.refresh_variables_table()
        self.variable_name_entry.delete(0, "end")
        self.variable_value_entry.delete(0, "end")
        self.save_requests()  # Save global variables immediately

    def delete_variable(self):
        """Delete the selected variable from the variables table"""
        selected = self.variables_tree.selection()
        if selected:
            item = self.variables_tree.item(selected[0])
            var_name = item["values"][0]
            if var_name in self.variable_dict:
                del self.variable_dict[var_name]
            self.refresh_variables_table()
            self.save_requests()  # Save changes immediately

    def on_variable_select(self, event):
        """When a variable is clicked in the variables table, update the input fields with its data"""
        selected = self.variables_tree.selection()
        if selected:
            item = self.variables_tree.item(selected[0])
            values = item.get("values", [])
            if len(values) >= 2:
                self.variable_name_entry.delete(0, "end")
                self.variable_name_entry.insert(0, values[0])
                self.variable_value_entry.delete(0, "end")
                self.variable_value_entry.insert(0, values[1])

    def substitute_variables(self, text):
        """
        Replace all occurrences of {{variable}} in the text with the value from self.variable_dict.
        If a variable value is in the format [filename], load the content from the corresponding file in the 'variables' folder.
        """
        pattern = r"\{\{\s*(\w+)\s*\}\}"

        def replacer(match):
            var_name = match.group(1)
            if var_name in self.variable_dict:
                var_value = self.variable_dict[var_name]
                # Check if variable value is in the format [filename]
                if re.fullmatch(r"\[.+\]", var_value):
                    filename = var_value.strip("[]")
                    filepath = os.path.join("variables", filename)
                    if os.path.exists(filepath):
                        try:
                            with open(filepath, "r", encoding="utf-8") as f:
                                content = f.read()
                            return content
                        except Exception as e:
                            messagebox.showerror("Error", f"Error reading file {filename}: {e}")
                            return var_value
                    else:
                        # If file is not found, return the original value
                        return var_value
                else:
                    return str(var_value)
            else:
                raise ValueError(var_name)

        try:
            return re.sub(pattern, replacer, text)
        except ValueError as e:
            undefined_var = e.args[0]
            messagebox.showerror("Error", self.ui_texts.get("undefined_variable_error", "Undefined variable: ") + undefined_var)
            raise

    def show_progress_dialog(self):
        """Display a progress dialog in the center of the screen while sending the request"""
        dialog = ctk.CTkToplevel(self)
        dialog.title(self.ui_texts.get("progress_dialog_title", "Processing"))
        window_width, window_height = 300, 100
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")
        dialog.resizable(False, False)
        label = ctk.CTkLabel(dialog, text=self.ui_texts.get("progress_dialog_label", "Sending request..."))
        label.pack(pady=(10, 5))
        progressbar = ctk.CTkProgressBar(dialog, mode="indeterminate")
        progressbar.pack(fill="x", padx=20, pady=5)
        progressbar.start()
        return dialog

    def open_history_file(self, filepath):
        """Open the given history file in a new window to display the full response."""
        if not os.path.exists(filepath):
            messagebox.showerror("Error", "History file not found!")
            return
        top = ctk.CTkToplevel(self)
        top.title(self.ui_texts.get("full_response_title", "Full Response"))
        top.geometry("800x600")
        text_box = ctk.CTkTextbox(top, font=self.fixedfont)
        text_box.pack(fill="both", expand=True, padx=5, pady=5)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            text_box.insert("1.0", content)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {e}")

    def send_request(self):
        """
        Called when the Send button is pressed:
         - Save the current input (new or update) to file without performing variable substitution in the saved data.
         - Replace any occurrences of {{variable}} in the request URL, headers, and body with the defined variable values for sending.
           If an undefined variable is found, an error dialog is shown.
         - Send the HTTP request using the substituted values.
         - Show a progress dialog and display "Sending request..." in the response area while processing.
         - After receiving the response, display the status info and (up to) the first 10000 characters of the response.
         - Save the request and full response (with timestamps) to a history file.
        """
        method = self.method_var.get().strip()
        description = self.description_entry.get().strip()
        original_url = self.url_entry.get().strip()
        original_headers_text = self.headers_textbox.get("1.0", "end").strip()
        original_body_text = self.body_textbox.get("1.0", "end").strip()

        if not original_url:
            self.response_textbox.delete("1.0", "end")
            self.response_textbox.insert("1.0", "URL is required!")
            return

        try:
            substituted_url = self.substitute_variables(original_url)
            substituted_headers_text = self.substitute_variables(original_headers_text)
            substituted_body_text = self.substitute_variables(original_body_text)
        except ValueError:
            return

        self.response_textbox.delete("1.0", "end")
        self.response_textbox.insert("1.0", self.ui_texts.get("sending_request", "Sending request..."))
        self.response_info_label.configure(text=self.ui_texts.get("response_label", "Response: "))

        headers = {}
        for line in substituted_headers_text.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

        try:
            json_body = json.loads(substituted_body_text) if substituted_body_text else None
        except json.JSONDecodeError:
            json_body = None

        # Save the current request using the original texts with placeholders.
        request_data = {
            "method": method,
            "description": description,
            "url": original_url,
            "headers": original_headers_text,
            "body": original_body_text
        }
        if self.current_request_index is None:
            self.saved_requests.append(request_data)
            self.current_request_index = len(self.saved_requests) - 1
        else:
            self.saved_requests[self.current_request_index] = request_data

        self.refresh_request_list()
        self.save_requests()

        request_time = datetime.now()
        progress_dialog = self.show_progress_dialog()

        def thread_func():
            try:
                start_time = time.time()
                if json_body is not None:
                    response = requests.request(method, substituted_url, headers=headers, json=json_body)
                else:
                    response = requests.request(method, substituted_url, headers=headers, data=substituted_body_text)
                elapsed = time.time() - start_time

                status_message = f"{response.status_code}"
                if response.reason:
                    status_message += f" {response.reason}"
                info_text = f"Status: {status_message} | Time: {elapsed:.2f} sec"

                try:
                    response_json = response.json()
                    response_pretty = json.dumps(response_json, indent=4, ensure_ascii=False)
                except ValueError:
                    response_pretty = response.text
            except requests.exceptions.RequestException as e:
                status_message = ""
                if hasattr(e, 'response') and e.response is not None:
                    status_message = f"{e.response.status_code}"
                    if e.response.reason:
                        status_message += f" {e.response.reason}"
                info_text = "Response: Error"
                response_pretty = "An error occurred"
                if status_message:
                    response_pretty += f"\nStatus: {status_message}"

            # If the response body exceeds 10000 characters, display partially
            if len(response_pretty) > 10000:
                response_display = response_pretty[:10000] + "[Partially displayed]"
            else:
                response_display = response_pretty

            response_time = datetime.now()

            history_content = (
                f"[Request Timestamp] {request_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Method: {method}\n"
                f"Description: {description}\n"
                f"URL: {substituted_url}\n"
                f"Headers:\n{substituted_headers_text}\n"
                f"Body:\n{substituted_body_text}\n\n"
                f"[Response Timestamp] {response_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Response Info: {info_text}\n"
                f"Response Body:\n{response_pretty}\n"
            )
            if not os.path.exists(self.history_folder):
                os.makedirs(self.history_folder)
            filename = os.path.join(self.history_folder, f"{response_time.strftime('%Y-%m-%d-%H-%M-%S')}.txt")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(history_content)

            def update_gui():
                self.response_info_label.configure(text=self.ui_texts.get("response_label", "Response: ") + info_text)
                self.response_textbox.delete("1.0", "end")
                self.response_textbox.insert("1.0", response_display)
                progress_dialog.destroy()
                # If the response body exceeds 10000 characters, ask if the user wants to display the full response
                if len(response_pretty) > 10000:
                    answer = messagebox.askyesno(
                        self.ui_texts.get("confirmation_title", "Confirmation"),
                        self.ui_texts.get("full_response_prompt", "Do you want to display the full response body?")
                    )
                    if answer:
                        self.open_history_file(filename)
            self.after(0, update_gui)

        threading.Thread(target=thread_func, daemon=True).start()

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = EZHttpRequestCheckerApp()
    app.mainloop()
