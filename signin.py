import sys
import os
from PySide6 import QtCore, QtWidgets, QtGui
import time
import json

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
tried_token_delete = False

def init_auth():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json")
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except google.auth.exceptions.RefreshError as error:
                print(error)
                print("Invalid token.")
                if tried_token_delete == False:
                    print("Attempting to refresh by deleting it.")
                    os.remove("token.json")
                    tried_token_delete = True
                    init_auth()
                else:
                    print("Deleting the token didn't seem to work. Dropping you into a terminal, good luck.")
                    os.system("cmd.exe /c start cmd")
                    os.system("gnome-terminal")
                    quit()
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
            .get(spreadsheetId=SPREADSHEET_ID, range="A" + str(index) + ":I" + str(index))
            .execute()
        )
        rows = result.get("values", [])
        return {"last_name": rows[0][4], "first_name": rows[0][5], "time": rows[0][3], "task": rows[0][7] == "Approved", "on_roster": len(rows[0]) == 9 and rows[0][8] == "Yes"}
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

def check(info):
    if info["last_name"] != "0":
        if not info["on_roster"]:
            return "noroster"
        if info["task"]:
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
MESSAGE_NOT_ON_ROSTER = "You aren't on the team roster!"

class SignInWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LASA Robotics Sign-In App")

        self.id = QtWidgets.QLineEdit(self)
        self.id.setAlignment(QtCore.Qt.AlignCenter)
        self.id.setPlaceholderText("Student ID")
        id_font = self.id.font()
        id_font.setPixelSize(64)
        self.id.setFont(id_font)

        self.text = QtWidgets.QLabel(MESSAGE_WAITING, self)
        self.text.setAlignment(QtCore.Qt.AlignCenter)
        text_font = self.text.font()
        text_font.setPixelSize(32)
        self.text.setFont(text_font)

        self.log = QtWidgets.QLabel("", self)
        self.log.setAlignment(QtCore.Qt.AlignBottom)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addStretch()
        self.layout.addWidget(self.id)
        self.layout.addWidget(self.text)
        self.layout.addStretch()
        self.layout.addWidget(self.log)

        self.id.returnPressed.connect(self.id_entered)

        self.full_log = []

    def reset_text(self):
        self.text.setText(MESSAGE_WAITING)

    def reset_flash(self):
        pal = self.style().standardPalette()
        self.setPalette(pal)
        self.reset_text()

    @QtCore.Slot()
    def id_entered(self):
        id = self.id.text()
        self.id.clear()

        if id == CMD_PASSWORD:
            # one of these will fail, but the other will open, that is intentional
            os.system("cmd.exe /c start cmd")
            os.system("gnome-terminal")
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
        info = get_current_information(index)
        result = check(info)
        if result == "notask" and signing_out: result = "allowed"
        if result == "denied": remove_from_spreadsheet(index)
        else: index += 1

        log = self.log.text()
        if log.count('\n') == 10:
            log = '\n'.join(log.split('\n')[:-1])
            print("test")
        log = "{} {} {} (signing {}, {})\n{}".format(id, info["first_name"], info["last_name"], "out" if signing_out else "in", result, log)
        self.log.setText(log)

        if not result == "denied":
            self.full_log.append({
                "id": id,
                "time": time.time()
            })

        if result == "allowed":
            self.text.setText(MESSAGE_SIGNED_OUT if signing_out else MESSAGE_ALLOWED)
            self.flash("lime", False)
        if result == "denied":
            self.text.setText(MESSAGE_DENIED)
            self.flash("red", True)
        if result == "notask":
            self.text.setText(MESSAGE_NOT_ON_TASK_LIST)
            self.flash("blue", True)
        if result == "noroster":
            self.text.setText(MESSAGE_NOT_ON_ROSTER)
            self.flash("red", True)

    def flash(self, color, full_window):
        pal = self.style().standardPalette()
        pal.setColor(QtGui.QPalette.Base, color)
        if full_window:
            pal.setColor(QtGui.QPalette.Window, color)
        self.setAutoFillBackground(True)
        self.setPalette(pal)

        dieTime = QtCore.QTime.currentTime().addSecs(1 if color == "green" else 3)
        while (QtCore.QTime.currentTime() < dieTime):
            QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents, 100);
        self.reset_flash()
        #GLib.timeout_add_seconds(1 if color == "flash-green" else 3, self.reset_flash, color)

app = QtWidgets.QApplication([])
widget = SignInWindow()
widget.resize(800, 500)
widget.show()

sys.exit(app.exec())
