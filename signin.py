import sys
import os
import subprocess
from typing import Dict

from PySide6 import QtCore, QtWidgets, QtGui
import json

from datetime import datetime
import pytz

import google.auth
from PySide6.QtCore import QTimer
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from Attendance import AttendanceRecord
from People import PersonRecord
from Swipes import SwipeRecord

f = open("config.json", "r")
j = json.load(f)
SPREADSHEET_ID = j["spreadsheet_id"]
CMD_PASSWORD = j["cmd_password"]
f.close()
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
service: Resource
tried_token_delete = False
people_cache: Dict[str, PersonRecord] = {}
unprocessed_cache: Dict[str, SwipeRecord] = {}


def init_auth():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        print(f"No Valid Token Found")
        if creds and creds.expired and creds.refresh_token:
            try:
                print(f"Attempting credential refresh")
                creds.refresh(Request())
            except google.auth.exceptions.RefreshError as error:
                print(error)
                print("Invalid token.")
                global tried_token_delete
                if not tried_token_delete:
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
            print(f"Attempting Sign-In")
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
            print(f"Sign-In Credentials Validated")
        with open("token.json", "w") as token:
            print(f"Saving Token")
            token.write(creds.to_json())
            print(f"Token Saved")
    try:
        global service
        service = build("sheets", "v4", credentials=creds)
        print(f"Google Sheets Service Built")
    except HttpError as error:
        print(f"An error occured: {error}")


def modify_row(sheet, row_number, values):
    range_name = f"{sheet}!A{row_number}"

    start = datetime.now()
    try:
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='RAW',
            body={"values": values}
        ).execute()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return
    stop = datetime.now()
    api_time = (stop - start).total_seconds() * 1000.0
    print(f"PUT {range_name} API Time: {api_time} ms")


def get_row(sheet, row_number):
    range_name = f"{sheet}!{row_number}:{row_number}"

    start = datetime.now()
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None
    stop = datetime.now()
    api_time = (stop - start).total_seconds() * 1000.0
    print(f"GET {range_name} API Time: {api_time} ms")

    row = result.get('values', [[]])[0]  # Avoid IndexError if empty
    return row


def delete_row(sheet_id, row_number):
    range_name = f"{sheet_id}!{row_number}:{row_number}"
    request_body = {
        "requests": [
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": int(row_number) - 1,
                        "endIndex": int(row_number)
                    }
                }
            }
        ]
    }

    start = datetime.now()
    try:
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=request_body
        ).execute()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return
    stop = datetime.now()
    api_time = (stop - start).total_seconds() * 1000.0
    print(f"DELETE {range_name} API Time: {api_time} ms")


def append_row(sheet, values):
    range_name = f"{sheet}!A1"

    start = datetime.now()
    try:
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [values]}
        ).execute()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return
    stop = datetime.now()
    api_time = (stop - start).total_seconds() * 1000.0
    print(f"POST {range_name} API Time: {api_time} ms")


def refresh_people_cache():
    start = datetime.now()
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="People"
        ).execute()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return
    stop = datetime.now()
    api_time = (stop - start).total_seconds() * 1000.0
    print(f"GET People API Time: {api_time} ms")

    values = result.get('values', [])
    values = values[1:]  # remove the header

    global people_cache
    people_cache.clear()
    for i, row in enumerate(values):
        record = PersonRecord(row, i + 2)
        people_cache[record.id] = record


def refresh_unprocessed_cache():
    start = datetime.now()
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="Unprocessed Sign Ins"
        ).execute()
    except HttpError as error:
        print(f"An error occurred: {error}")
        return
    stop = datetime.now()
    api_time = (stop - start).total_seconds() * 1000.0
    print(f"GET Unprocessed Sign Ins API Time: {api_time} ms")

    values = result.get('values', [])
    values = values[1:]  # remove the header

    global unprocessed_cache
    unprocessed_cache.clear()
    for i, row in enumerate(values):
        record = SwipeRecord(row, i + 2)
        unprocessed_cache[record.person_id] = record


init_auth()

MESSAGE_WAITING = "Scan your ID card OR type your ID above and press ENTER."
MESSAGE_PROCESSING = "Please wait..."
MESSAGE_ALLOWED = "Successfully signed in. Welcome to robotics!"
MESSAGE_SIGNED_OUT = "Successfully signed out. Goodbye!"
MESSAGE_DENIED = "Invalid ID."
MESSAGE_NOT_ON_TASK_LIST = "You aren't on the task list!"
MESSAGE_NOT_ON_ROSTER = "You aren't on the team roster!"
MESSAGE_TOKEN_INVALID = "The token has expired. Type \"fix\", then \"restart\"."
MESSAGE_TOKEN_DELETED = "token.json has been deleted. Please type \"restart\" to get a new one."


class SignInWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LASA Robotics Sign-In App")

        self.id = QtWidgets.QLineEdit(self)
        self.id.setAlignment(QtCore.Qt.AlignCenter)
        self.id.setPlaceholderText("Student ID")
        id_font = self.id.font()
        id_font.setPixelSize(128)
        self.id.setFont(id_font)

        self.text = QtWidgets.QLabel(MESSAGE_WAITING, self)
        self.text.setAlignment(QtCore.Qt.AlignCenter)
        text_font = self.text.font()
        text_font.setPixelSize(32)
        self.text.setFont(text_font)

        self.freshmen = QtWidgets.QLabel("Freshmen:<br>", self)
        self.freshmen.setAlignment(QtCore.Qt.AlignLeft)
        self.sophomores = QtWidgets.QLabel("Sophomores:<br>", self)
        self.sophomores.setAlignment(QtCore.Qt.AlignLeft)
        self.juniors = QtWidgets.QLabel("Juniors:<br>", self)
        self.juniors.setAlignment(QtCore.Qt.AlignLeft)
        self.seniors = QtWidgets.QLabel("Seniors:<br>", self)
        self.seniors.setAlignment(QtCore.Qt.AlignLeft)
        self.mentors = QtWidgets.QLabel("Mentors:<br>", self)
        self.mentors.setAlignment(QtCore.Qt.AlignLeft)

        global unprocessed_cache
        global people_cache

        try:
            refresh_people_cache()
            refresh_unprocessed_cache()
        except RefreshError:
            os.remove("token.json")
            init_auth()
            refresh_people_cache()
            refresh_unprocessed_cache()

        self.update_present_list()

        self.count_text = QtWidgets.QLabel(f"Sign-in count: {len(unprocessed_cache)}")
        self.count_text.setAlignment(QtCore.Qt.AlignRight)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addStretch()
        self.layout.addWidget(self.id)
        self.layout.addWidget(self.text)

        self.present_layout = QtWidgets.QHBoxLayout()
        self.present_layout.addWidget(self.freshmen)
        self.present_layout.addWidget(self.sophomores)
        self.present_layout.addWidget(self.juniors)
        self.present_layout.addWidget(self.seniors)
        self.present_layout.addWidget(self.mentors)
        self.layout.addLayout(self.present_layout)

        self.layout.addStretch()
        self.layout.addWidget(self.count_text)

        self.id.returnPressed.connect(self.id_entered)

        self.queued_flash_reset = None

        self.fun_mode = False

        self.token_refresh_timer = QTimer(self)
        self.token_refresh_timer.timeout.connect(init_auth)
        self.token_refresh_timer.start(1000 * 60 * 60)  # time in milliseconds.

        QTimer.singleShot(0, self.delayed_maximize)

    def update_present_list(self):
        global unprocessed_cache
        global people_cache

        now = datetime.now(pytz.timezone('US/Central'))
        senior_year = now.year + 1 if now.month >= 6 else now.year

        present_mentors = []
        present_seniors = []
        present_juniors = []
        present_sophomores = []
        present_freshmen = []

        for person_id in unprocessed_cache:
            person = people_cache[person_id]
            signin_timg = unprocessed_cache[person_id].swipe_time_dt.strftime("%I:%M:%S %p")
            person_string = f"{signin_timg} {person.last_name}, {person.first_name}"
            if person.roster_status != "On Roster":
                person_string = f"{person_string[:12]}<span style=\"background-color:yellow;\">{person_string[12:]}</span>"
            elif person.role == "Lead":
                person_string = f"{person_string[:12]}<span style=\"background-color:cyan;\">{person_string[12:]}</span>"
            if person.role == "Mentor":
                present_mentors.append(person_string)
            elif int(person.graduation_year) == senior_year:
                present_seniors.append(person_string)
            elif int(person.graduation_year) == senior_year + 1:
                present_juniors.append(person_string)
            elif int(person.graduation_year) == senior_year + 2:
                present_sophomores.append(person_string)
            elif int(person.graduation_year) == senior_year + 3:
                present_freshmen.append(person_string)

        present_mentors.sort(key=lambda x: x[12:])
        present_seniors.sort(key=lambda x: x[12:])
        present_juniors.sort(key=lambda x: x[12:])
        present_sophomores.sort(key=lambda x: x[12:])
        present_freshmen.sort(key=lambda x: x[12:])

        self.mentors.setText(f"<strong>Mentors</strong>:<br>{'<br>'.join(present_mentors)}")
        self.seniors.setText(f"<strong>Seniors</strong>:<br>{'<br>'.join(present_seniors)}")
        self.juniors.setText(f"<strong>Juniors</strong>:<br>{'<br>'.join(present_juniors)}")
        self.sophomores.setText(f"<strong>Sophomores</strong>:<br>{'<br>'.join(present_sophomores)}")
        self.freshmen.setText(f"<strong>Freshmen</strong>:<br>{'<br>'.join(present_freshmen)}")

    def delayed_maximize(self):
        self.showMaximized()

    def reset_text(self):
        self.text.setText(MESSAGE_WAITING)

    def reset_flash(self):
        pal = self.style().standardPalette()
        self.setPalette(pal)
        self.reset_text()

    @QtCore.Slot()
    def id_entered(self):
        print('---------------------------------------')
        swipe_time = datetime.now(pytz.timezone('US/Central'))
        swipe_time_str = swipe_time.strftime('%m/%d/%Y %H:%M:%S')

        raw_id = self.id.text()
        id_text = raw_id
        if id_text == "":
            return
        if id_text.startswith("s"):
            id_text = id_text[1:]
        self.id.clear()
        self.text.setText(MESSAGE_PROCESSING)
        QtWidgets.QApplication.processEvents()

        if id_text == CMD_PASSWORD:
            # one of these will fail, but the other will open, that is intentional
            os.system("cmd.exe /c start cmd")
            os.system("gnome-terminal")
            self.text.setText(MESSAGE_WAITING)
            return
        if id_text == "up":
            subprocess.Popen(["bash", "/home/lasasignin/Desktop/signin.sh"])
            quit()
        if id_text == "exit":
            quit()
        if id_text == "fun":
            self.fun_mode = not self.fun_mode
            self.text.setText(MESSAGE_WAITING)
            return
        if id_text == "fix":
            os.remove("token.json")
            init_auth()
            return

        try:
            global unprocessed_cache
            global people_cache

            refresh_people_cache()
            refresh_unprocessed_cache()

            # ID was not found in people directory
            if id_text not in people_cache:
                self.text.setText(MESSAGE_DENIED)
                self.flash("red", True)
                return

            # ID is in the people directory. Add to raw record regardless of any other status
            append_row('Raw Swipe Records', [swipe_time_str, id_text])

            # If the ID has an unprocessed swipe record, it's a sign-out
            signing_out = id_text in unprocessed_cache

            person = people_cache[id_text]

            if signing_out:
                unprocessed_record = unprocessed_cache[id_text]
                delete_row('1355997247', unprocessed_record.row_number)
                append_row('Attendance Records', [unprocessed_record.swipe_time, swipe_time_str, id_text])
                unprocessed_cache.pop(id_text)
            else:
                unprocessed_record = SwipeRecord([swipe_time_str, id_text], len(unprocessed_cache) + 2)
                unprocessed_cache[id_text] = unprocessed_record
                append_row('Unprocessed Sign Ins', unprocessed_record.get_raw_record())

            self.update_present_list()

            color = "yellow"
            if person.roster_status == 'On Roster':
                color = "lime"
                self.text.setText(MESSAGE_SIGNED_OUT if signing_out else MESSAGE_ALLOWED)
                self.flash(color, False)
            else:
                color = "yellow"
                self.text.setText(MESSAGE_NOT_ON_ROSTER)
                self.flash(color, True)

            self.count_text.setText(f"Sign-in count: {len(unprocessed_cache)}")

            print(f"Total Processing Time: {(datetime.now(pytz.timezone('US/Central')) - swipe_time).total_seconds()}s")

        except RefreshError:
            os.remove("token.json")
            init_auth()
            self.id.setText(raw_id)
            self.id_entered()

    def flash(self, color, full_window):
        pal = self.style().standardPalette()
        if self.fun_mode:
            image = "images/thumbsup.jpg"
            if color == "yellow":
                image = "images/stopsign.jpg"
            pal.setBrush(QtGui.QPalette.Window, QtGui.QBrush(QtGui.QPixmap(image)))
        else:
            pal.setColor(QtGui.QPalette.Base, color)
            if full_window:
                pal.setColor(QtGui.QPalette.Window, color)
        self.setAutoFillBackground(True)
        self.setPalette(pal)

        time = QtCore.QTime.currentTime()
        self.queued_flash_reset = time
        dieTime = time.addSecs(0.25 if color == "green" else 1)
        while (QtCore.QTime.currentTime() < dieTime):
            QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents, 100)
        if self.queued_flash_reset == time:
            self.reset_flash()


app = QtWidgets.QApplication([])
widget = SignInWindow()
widget.resize(800, 500)
widget.show()

sys.exit(app.exec())
