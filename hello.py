import os
from flask import Flask, request
import psycopg2

app = Flask(__name__) #create an instance of the Flask library

DATABASE_URL = os.environ['https://data.heroku.com/datastores/7f5c6592-8985-46d0-a0c0-6791409c61f0']

conn = psycopg2.connect(DATABASE_URL, sslmode='require')

@app.route('/hello') #whenever this webserver is called with <hostname:port>/hello then this section is called
def hello():
	show = "SELECT * FROM data_latih"
	cur = conn.cursor()
	cur.execute(show)
	row = cur.fetchone()
	print(cur.rowcount)
	
if __name__ == '__main__':
	port = int(os.environ.get('PORT', 5000)) #The port to be listening to — hence, the URL must be <hostname>:<port>/ inorder to send the request to this program
	app.run(host='0.0.0.0', port=port)  #Start listening