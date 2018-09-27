import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
import time
import atexit
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

def print_date_time():
    print(time.strftime("%A, %d. %B %Y %I:%M:%S %p"))


# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

@app.route('/')
def index():
    return "YOU GOT IT"

if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=print_date_time, trigger="interval", seconds=10)
    scheduler.start()
    port = int(os.environ.get('PORT', 5000)) #The port to be listening to — hence, the URL must be <hostname>:<port>/ inorder to send the request to this program
    app.run(debug=True, host='0.0.0.0', port=port)
