import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
import psycopg2
from sqlalchemy import create_engine
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle


app = Flask(__name__) #create an instance of the Flask library

global Classifier
global Vectorizer

#make connection
DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
engine = create_engine(os.environ['DATABASE_URL'])

@app.route('/', methods=['GET'])
def index():
	arr_message = request.args.getlist('message')
	error = ''
	predict_proba = ''
	predict = ''

	global Classifier
	global Vectorizer

	Vectorizer = TfidfVectorizer()

	return_arr = []
	for message in arr_message:
		try:
			if len(message) > 0:
				a=stripTagsAndUris(message)
				b=removePunctuation(a)
				c=removeStopwords(b)
				d=stemming(c)
				vectorize_message = Vectorizer.transform([d])
				loaded_model = pickle.load(open('finalized_model.pkl', 'rb'))
				predict = loaded_model.predict(vectorize_message)[0]
				predict_proba = loaded_model.predict_proba(vectorize_message).tolist()
				dicti = {}
				dicti['message'] = message
				dicti['predict'] = predict
				dicti['predict_proba'] = predict_proba
				dicti['error']      = error
				return_arr.append(dicti)
		except BaseException as inst:
			error = str(type(inst).__name__) + ' ' + str(inst)
	return jsonify(return_arr)

@app.route('/', methods=['POST'])
def Create_Data():
	json = {
	'predict': request.json['predict'],
	'message': request.json['message']}

	data = pd.read_sql_table("data_latih", engine, columns=['label', 'term'])
	for index, row in data.iterrows():
		if row["term"] == json['message'] and row["label"] != json['predict']:
			status = 'inconsisten'
			break
		elif row["term"] == json['message'] and row["label"] == json['predict']:
			status = 'duplicate'
			break
		else:
			status = 'not exist'
	print(status)
	if status == 'inconsisten':
		delete_str = "DELETE FROM data_latih WHERE term = %s"
		cur = conn.cursor()
		cur.execute(delete_str, (json['message'],))
		conn.commit()
	if status == 'not exist':
		dataInsert = pd.DataFrame({'label':[json['predict']],'term':[json['message']]})
		dataInsert.to_sql('data_latih', engine, if_exists='append',index=False)
	return jsonify(json), 201

if __name__ == '__main__':
	port = int(os.environ.get('PORT', 5000))
	app.run(debug=True, use_reloader=False, host='0.0.0.0', port=port)