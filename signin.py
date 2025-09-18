import sys
import subprocess
from typing import Dict

from PySide6 import QtCore, QtWidgets, QtGui
import json

from datetime import datetime
import pytz
import traceback

from PySide6.QtCore import QTimer

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_document import DocumentSnapshot

people_cache: Dict[str, DocumentSnapshot] = {}
signed_in_cache: Dict[str, DocumentSnapshot] = {}
last_swipes: Dict[str, datetime] = {}

cred = credentials.Certificate("token.json")
firebase_admin.initialize_app(cred)

db = firestore.client()
people_ref = db.collection('people')
attendance_records_ref = db.collection('attendanceRecords')
signed_in_ref = db.collection('signedIn')


def refresh_cache():
    global signed_in_ref
    global people_ref
    global signed_in_cache
    global people_cache
    signed_in_cache = {}
    start = datetime.now()
    signed_in_stream = signed_in_ref.stream()
    for signed_in in signed_in_stream:
        signed_in_cache[signed_in.id] = signed_in
        people_cache[signed_in.id] = people_ref.document(signed_in.id).get()
    stop = datetime.now()
    api_time = (stop - start).total_seconds() * 1000.0
    print(f"Refresh people cache API Time: {api_time} ms")


MESSAGE_WAITING = "Scan your ID card OR type your ID above and press ENTER."
MESSAGE_PROCESSING = "Please wait..."
MESSAGE_ALLOWED = "Successfully signed in. Welcome to robotics!"
MESSAGE_SIGNED_OUT = "Successfully signed out. Goodbye!"
MESSAGE_DENIED = "Invalid ID."
MESSAGE_COOL_DOWN = "Too many swipes! Wait a bit!"
MESSAGE_ERROR = "ERROR ERROR ERROR ERROR ERROR ERROR"


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
        self.teachers = QtWidgets.QLabel("Teachers:<br>", self)
        self.teachers.setAlignment(QtCore.Qt.AlignLeft)
        self.mentors = QtWidgets.QLabel("Mentors:<br>", self)
        self.mentors.setAlignment(QtCore.Qt.AlignLeft)
        self.count_text = QtWidgets.QLabel(f"Sign-in count:")
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
        self.present_adults_layout = QtWidgets.QVBoxLayout()
        self.present_adults_layout.addWidget(self.teachers)
        self.present_adults_layout.addWidget(self.mentors)
        self.present_layout.addLayout(self.present_adults_layout)
        self.layout.addLayout(self.present_layout)

        self.layout.addStretch()
        self.layout.addWidget(self.count_text)

        self.id.returnPressed.connect(self.id_entered)

        self.daily_actions()

        QTimer.singleShot(0, self.showMaximized)

    def daily_actions(self):
        print("Running Daily Actions")

        refresh_cache()
        self.update_present_list()

        now = QtCore.QDateTime.currentDateTime()
        next_execution_time = QtCore.QDateTime(now.date().addDays(1), QtCore.QTime(1, 0, 0, 0))

        delay_ms = now.msecsTo(next_execution_time)
        QTimer.singleShot(delay_ms, self.daily_actions)

    def update_present_list(self):
        global people_cache
        global signed_in_cache

        now = datetime.now(pytz.timezone('US/Central'))
        senior_year = now.year + 1 if now.month >= 6 else now.year

        present_mentors = []
        present_teachers = []
        present_seniors = []
        present_juniors = []
        present_sophomores = []
        present_freshmen = []

        for person_id, signed_in_doc in signed_in_cache.items():
            person = people_cache[person_id].to_dict()
            signed_in_doc = signed_in_cache[person_id]
            sign_in_time_str = signed_in_doc.to_dict()["signInTime"].strftime("%I:%M:%S %p")
            person_string = f"{sign_in_time_str} {person['lastName']}, {person['firstName']}"
            if person['rosterStatus'] != "On Roster":
                person_string = f"{person_string[:12]}<span style=\"background-color:yellow;color:black;\">{person_string[12:]}</span>"
            elif person['role'] == "Lead":
                person_string = f"{person_string[:12]}<span style=\"background-color:cyan;color:black;\">{person_string[12:]}</span>"
            if person['role'] == "Teacher":
                present_teachers.append(person_string)
            elif person['role'] == "Mentor":
                present_mentors.append(person_string)
            elif int(person['graduationYear']) == senior_year:
                present_seniors.append(person_string)
            elif int(person['graduationYear']) == senior_year + 1:
                present_juniors.append(person_string)
            elif int(person['graduationYear']) == senior_year + 2:
                present_sophomores.append(person_string)
            elif int(person['graduationYear']) == senior_year + 3:
                present_freshmen.append(person_string)

        present_teachers.sort(key=lambda x: x[12:])
        present_mentors.sort(key=lambda x: x[12:])
        present_seniors.sort(key=lambda x: x[12:])
        present_juniors.sort(key=lambda x: x[12:])
        present_sophomores.sort(key=lambda x: x[12:])
        present_freshmen.sort(key=lambda x: x[12:])

        self.teachers.setText(f"<strong>Teachers</strong>:<br>{'<br>'.join(present_teachers)}")
        self.mentors.setText(f"<strong>Mentors</strong>:<br>{'<br>'.join(present_mentors)}")
        self.seniors.setText(f"<strong>Seniors</strong>:<br>{'<br>'.join(present_seniors)}")
        self.juniors.setText(f"<strong>Juniors</strong>:<br>{'<br>'.join(present_juniors)}")
        self.sophomores.setText(f"<strong>Sophomores</strong>:<br>{'<br>'.join(present_sophomores)}")
        self.freshmen.setText(f"<strong>Freshmen</strong>:<br>{'<br>'.join(present_freshmen)}")
        self.count_text.setText(f"Sign-in count: {len(signed_in_cache)}")

    @QtCore.Slot()
    def id_entered(self):
        print('---------------------------------------')
        swipe_time = datetime.now(pytz.timezone('US/Central'))

        raw_id = self.id.text()
        id_text = raw_id
        if id_text == "":
            return
        if id_text.startswith("s"):
            id_text = id_text[1:]
        self.id.clear()
        self.text.setText(MESSAGE_PROCESSING)
        QtWidgets.QApplication.processEvents()

        if id_text == "up":
            subprocess.Popen(["bash", "/home/lasasignin/Desktop/signin.sh"])
            quit()
        if id_text == "exit":
            quit()

        try:
            global signed_in_cache
            global people_cache
            global people_ref
            global signed_in_ref
            global attendance_records_ref

            person_doc = people_ref.document(id_text).get()

            # ID was not found in people directory
            if not person_doc.exists:
                self.text.setText(MESSAGE_DENIED)
                self.flash("orange", 1000)
                return

            # If exists, add to people cache
            people_cache[person_doc.id] = person_doc

            # Handle case where someone swipes for the first time
            if person_doc.id not in last_swipes:
                last_swipes[person_doc.id] = swipe_time
            # Don't let someone accidentally double swipe
            elif (swipe_time - last_swipes[person_doc.id]).total_seconds() < 30:
                self.text.setText(MESSAGE_COOL_DOWN)
                self.flash("yellow", 1000)
                return

            last_swipes[person_doc.id] = swipe_time

            sign_in_ref = signed_in_ref.document(person_doc.id)
            sign_in_doc = sign_in_ref.get()

            # If there is a doc in the signed in db, it's a sign-in
            if sign_in_doc.exists:
                sign_in_ref.delete()
                attendance_records_ref.add({
                    "signInTime": sign_in_doc.to_dict()["signInTime"],
                    "signOutTime": swipe_time,
                    "personId": person_doc.id,
                    "recordType": "Regular",
                    "note": ""
                })
                del signed_in_cache[person_doc.id]
                self.text.setText(MESSAGE_SIGNED_OUT)
                self.flash("cyan", 500)
            # If there is no doc in the signed in db, it's a sign-out
            else:
                sign_in_ref.set({
                    "signInTime": swipe_time,
                    "personId": person_doc.id
                })
                signed_in_cache[person_doc.id] = sign_in_ref.get()
                self.text.setText(MESSAGE_ALLOWED)
                self.flash("purple", 500)

            self.update_present_list()
            print(f"Total Processing Time: {(datetime.now(pytz.timezone('US/Central')) - swipe_time).total_seconds()}s")

        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            print("Detailed traceback:")
            traceback.print_exc()
            self.text.setText(MESSAGE_ERROR)
            self.flash("red", 5000)

    def flash(self, color, length):
        pal = self.style().standardPalette()
        pal.setColor(QtGui.QPalette.Base, color)
        pal.setColor(QtGui.QPalette.Window, color)
        self.setAutoFillBackground(True)
        self.setPalette(pal)

        QTimer.singleShot(length, self.reset_window)

    def reset_window(self):
        pal = self.style().standardPalette()
        self.setPalette(pal)
        self.text.setText(MESSAGE_WAITING)


app = QtWidgets.QApplication([])
widget = SignInWindow()
widget.resize(800, 500)
widget.show()

sys.exit(app.exec())
