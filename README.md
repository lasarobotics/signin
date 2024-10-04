# Sign-In Application
This is the application that will run on the sign-in computer. It provides a simple interface to log sign-ins and sign-outs.

## Logic
- When an ID is valid and the person is on the task list, it's added to the spreadsheet and the screen flashes green for 1 second.
- When an ID is valid but the person is NOT on the task list, it's still added to the spreadsheet, but the screen flashes blue for 3 seconds as an indicator.
- When an ID is invalid, it is NOT added to the spreadsheet, and the screen flashes red for 3 seconds.

- There's a small log at the bottom of the screen showing the past 10 entries.

- If someone has signed in in the past 5 seconds and enters their ID again, it is ignored. This is to prevent people accidentally scanning their IDs twice in a row.
- If someone has already signed in, it is assumed they are signing out (though it's not logged in the spreadsheet differently; only the message and small log show this)

## Installation
1. Make sure you have python, GTK, etc on the system (will add detailed instructions later)
2. Download the source from this repository and extract it in the home directory.
3. `cd` into the directory, then run `./install.sh`. If it gives a permission error, give it execute permissions with `chmod +x ./install.sh`.

## Running
Simply run `./run.sh`. If it gives a permission error, give it execute permissions with `chmod +x ./run.sh`.
