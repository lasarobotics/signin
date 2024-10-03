import sys
import gi
import time

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

MESSAGE_WAITING = "Enter your ID above, then press ENTER."
MESSAGE_ALLOWED = "Successfully signed in. Welcome to robotics!"
MESSAGE_SIGNED_OUT = "Successfully signed out. Goodbye!"
MESSAGE_DENIED = "Invalid ID."
MESSAGE_NOT_ON_TASK_LIST = "You aren't on the task list!"

def check_id(id):
    if id == "valid": return "allowed"
    elif id == "taskless": return "notask"
    else: return "denied"

def add_to_spreadsheet(id):
    pass # replace with logic to log the ID to the spreadsheet

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
        signing_out = False
        for entry in self.full_log:
            if entry["id"] == id:
                if time.time() - entry["time"] <= 5: return
                else: signing_out = True

        result = check_id(id)
        if result == "notask" and signing_out: result = "allowed"

        log = self.log.get_text()
        if log.count('\n') == 10:
            log = '\n'.join(log.split('\n')[:-1])
            print("test")
        log = "{} (signing {}, {})\n{}".format(id, "out" if signing_out else "in", result, log)
        self.log.set_text(log)

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
        GLib.set_application_name('Sign-In Interface')

    def do_activate(self):
        window = SignInWindow(application=self)

        window.present()


app = SignInApplication()
exit_status = app.run(sys.argv)
sys.exit(exit_status)
