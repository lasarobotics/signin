# Sign-In Application
This is the application that will run on the sign-in computer. It provides a simple interface to log sign-ins and sign-outs.

## Commands
There are some built-in commands you can enter instead of an ID to do certain things:
- Open terminal / command prompt: configurable in config.json, only really useful on Windows 
- Update & restart the program (doesn't reset the log): up
- Close the window: exit
- Manually remove the auth token and try to re-authenticate: fix
- Toggle ✨Fun Mode✨ (no confetti unfortunately): fun

## Logic
- When an ID is valid and the person is signed out, the person is signed in and their name is displayed on the signed in list.
- When an ID is valid and the person is signed in, the person is signed out and their name is removed from the signed in list.
- When an ID is invalid, it is NOT recorded, and the screen flashes red for 3 seconds.
- The screen displays the individuals that are currently signed in.

## Installation
1. Use Git (`sudo apt-get install git` or download it [here](https://git-scm.com/downloads) for Windows) to clone this repository or download the source and extract it in a directory of your choice.
2.
  - If you're on Linux, `cd` into the directory, then run `./install.sh`. If it gives a permission error, give it execute permissions with `chmod +x ./install.sh`. Linux distros other than Debian are not currently supported.
  - If you're on Windows, you'll need to install [Python](https://python.org/downloads). **ONLY VERSIONS <3.12 ARE SUPPORTED BY QT.** [3.11.9](https://www.python.org/downloads/release/python-3119/) is the latest supported version with Windows support. `cd` into the directory and run `install.bat`. 
3. Through Google Cloud, create credentials and put them in `credentials.json`.
4. Create `config.json` and put the ID of the spreadsheet and password to open CMD, formatted like `{"spreadsheet_id": "YOUR_SPREADSHEET_ID", "cmd_password": "YOUR_CMD_PASSWORD"}`.

## Running
Simply run `./run.sh` on Linux, or `run.bat` on Windows. If it gives a permission error on Linux, give it execute permissions with `chmod +x ./run.sh`.

## Screenshots
![Screenshot of the application running in Qt](./screenshots/qt-bigtext.png)
