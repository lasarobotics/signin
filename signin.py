import sys
import os
import gi
import time
import json

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

f = open("config.json", "r")
j = json.load(f)
SPREADSHEET_ID = j["spreadsheet_id"]
CMD_PASSWORD = j["cmd_password"]
f.close()
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
service = None

def init_auth():
    """
    Creates the batch_update the user has access to.
    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json")
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    try:
        global service
        service = build("sheets", "v4", credentials=creds)
    except HttpError as error:
        print(f"An error occured: {error}")

def get_next_blank(range_name):
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range=range_name)
            .execute()
        )
        rows = result.get("values", [])
        #print(f"{len(rows)} rows retrieved")
        index = len(rows) + 5
        return index
    except HttpError as error:
        print(f"An error occurred: {error}")
        return error

def get_current_information(index):
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range="A" + str(index) + ":H" + str(index))
            .execute()
        )
        rows = result.get("values", [])
        return {"last_name": rows[0][4], "status": rows[0][7]}
    except HttpError as error:
        print(f"An error occured: {error}")
        return error

def add_to_spreadsheet(id, index):
    try:
        result = (
            service.spreadsheets()
            .values()
            .update(spreadsheetId=SPREADSHEET_ID, range="C" + str(index), valueInputOption="USER_ENTERED", body={"values": [[id]]})
            .execute()
        )
    except HttpError as error:
        print(f"An error occured: {error}")
        return error

def remove_from_spreadsheet(index):
    try:
        result = (
            service.spreadsheets()
            .values()
            .update(spreadsheetId=SPREADSHEET_ID, range="C" + str(index), valueInputOption="USER_ENTERED", body={"values": [[""]]})
            .execute()
        )
    except HttpError as error:
        print(f"An error occured: {error}")
        return error

def check(index):
    info = get_current_information(index)
    if info["last_name"] != "0":
        if info["status"] == "Approved":
            return "allowed"
        else: return "notask"
    return "denied"

init_auth()
index = get_next_blank("C5:C11840")

MESSAGE_WAITING = "Enter your ID above, then press ENTER."
MESSAGE_ALLOWED = "Successfully signed in. Welcome to robotics!"
MESSAGE_SIGNED_OUT = "Successfully signed out. Goodbye!"
MESSAGE_DENIED = "Invalid ID."
MESSAGE_NOT_ON_TASK_LIST = "You aren't on the task list!"

class SignInWindow(Gtk.ApplicationWindow):
    def __init__(self, **kargs):
        super().__init__(**kargs, title='LASA Robotics Sign-In App')

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.props.margin_start = 50
        vbox.props.margin_end = 50
        vbox.props.margin_top = 240
        vbox.props.margin_bottom = 0
        self.set_child(vbox)

        self.id = Gtk.Entry()
        self.id.props.placeholder_text = "Student ID"
        self.id.connect('activate', self.id_entered)
        self.id.get_style_context().add_class("input")
        vbox.append(self.id)

        self.text = Gtk.Label()
        self.text.props.label = MESSAGE_WAITING
        self.text.get_style_context().add_class("text")
        vbox.append(self.text)

        self.log = Gtk.Label()
        self.log.props.label = ""
        vbox.append(self.log)

        self.full_log = []

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
        .flash-green { background-color: green; }
        .flash-red { background-color: darkred; }
        .flash-yellow { background-color: darkblue; }

        .input { font-size: 128px; }
        .text { font-size: 32px; }
        """)
        Gtk.StyleContext.add_provider_for_display(self.get_display(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        #button = Gtk.Button(label="Exit")
        #button.connect('clicked', self.close)
        #vbox.append(button)

    def reset_text(self):
        self.text.props.label = MESSAGE_WAITING

    def reset_flash(self, color):
        self.get_style_context().remove_class(color)
        self.reset_text()

    def id_entered(self, widget):
        id = widget.get_text()
        widget.set_text("")
        # !! UNTESTED !!
        if id == CMD_PASSWORD:
            os.system("cmd.exe /c start cmd")
            return
        signing_out = False
        for entry in self.full_log:
            if entry["id"] == id:
                if time.time() - entry["time"] <= 5: return
                else:
                    signing_out = True
                    self.full_log.remove(entry)
                    break

        global index
        add_to_spreadsheet(id, index)
        result = check(index)
        if result == "notask" and signing_out: result = "allowed"
        if result == "denied": remove_from_spreadsheet(index)
        else: index += 1

        log = self.log.get_text()
        if log.count('\n') == 10:
            log = '\n'.join(log.split('\n')[:-1])
            print("test")
        log = "{} (signing {}, {})\n{}".format(id, "out" if signing_out else "in", result, log)
        self.log.set_text(log)

        if not result == "denied":
            self.full_log.append({
                "id": id,
                "time": time.time()
            })

        if result == "allowed":
            self.text.props.label = MESSAGE_SIGNED_OUT if signing_out else MESSAGE_ALLOWED
            self.flash("flash-green")
        if result == "denied":
            self.text.props.label = MESSAGE_DENIED
            self.flash("flash-red")
        if result == "notask":
            self.text.props.label = MESSAGE_NOT_ON_TASK_LIST
            self.flash("flash-yellow")

    def flash(self, color):
        self.get_style_context().add_class(color)
        GLib.timeout_add_seconds(1 if color == "flash-green" else 3, self.reset_flash, color)

class SignInApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.lasarobotics.signin")
        GLib.set_application_name('Robotics Sign-In')

    def do_activate(self):
        window = SignInWindow(application=self)

        window.present()


app = SignInApplication()
exit_status = app.run(sys.argv)
sys.exit(exit_status)
