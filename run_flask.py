import threading
import subprocess
import os

def run_flask():
        # Set the working directory to the project directory
    os.chdir('/Users/ompandey/Desktop/dtcc/ainews/')
        # Run the Flask application
    subprocess.run(["python", "app/main.py"])

    # Run the Flask application in a new thread
    threading.Thread(target=run_flask).start()