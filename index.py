import os
from flask import Flask, request, jsonify
import psycopg2
from sqlalchemy import create_engine
import pickle
import pandas as pd
from bs4 import BeautifulSoup
import re
import string
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from collections import Counter


app = Flask(__name__) #create an instance of the Flask library

#connect database
DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
engine = create_engine(os.environ['DATABASE_URL'])

#read dictionary
def words(text): return re.findall(r'\w+', text.lower())

WORDS = Counter(words(open('spellcheck.txt').read()))
ROOTWORDS = Counter(words(open('kata-dasar.txt').read()))
STOPWORDS = Counter(words(open('stopword.txt').read()))

#remove URI
uri_re = r'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))'

def stripTagsAndUris(x):
	if x:
		# BeautifulSoup on content
		soup = BeautifulSoup(x, "html.parser")
		# Stripping all <code> tags with their content if any
		if soup.code:
			soup.code.decompose()
		# Get all the text out of the html
		text =  soup.get_text()
		# Returning text stripping out all uris
		return re.sub(uri_re, "", text)
	else:
		return ""
	
#remove punctuation   
def removePunctuation(x):
	# Lowercasing all words
	x = x.lower()
	# Removing non ASCII chars
	x = re.sub(r'[^\x00-\x7f]|(@[a-z0-9_.-]+)|(#[A-Za-z0-9]+)|([^a-zA-Z ]+?)',r' ',x)
	# Removing (replacing with empty spaces actually) all the punctuations
	return re.sub("["+string.punctuation+"]", " ", x)

#stemming
factory = StemmerFactory()
stemmer = factory.create_stemmer()

def stemming(x):
	return stemmer.stem(x)

#handle lengthning word
def shortening(x):
	result = []
	for word in x.split():
		if word not in ROOTWORDS:
			karakter = list(word)
			for i in range(len(word)-1):
				if karakter[i]==karakter[i+1]:
					karakter[i]=''
			word=''.join(karakter)
			if word not in ROOTWORDS:
				karakter = list(word)
				for i in range(len(word)-3):
					if karakter[i]==karakter[i+2] and karakter[i+1]==karakter[i+3]:
						karakter[i]=''
						karakter[i+1]=''
				word=''.join(karakter)
				if len(word)<4 and word not in ROOTWORDS:
					word=''
		result.append(word)
		
	return " ".join(result)

def P(word, N=sum(WORDS.values())): 
	# "Probability of `word`."
	return WORDS[word] / N

def correction(x):
	word=shortening(x).split()
	result=[]
	for w in word:
		if w not in ROOTWORDS:
			w=max(candidates(w), key=P)
		result.append(w)
	return " ".join(result)

def candidates(word): 
	# "Generate possible spelling corrections for word."
	if len (word) < 5:
		candidate=known([word]) or known(edits1(word)) or [word]
	else:
		candidate=known([word]) or known(edits1(word)) or known(edits2(word)) or [word]
	return candidate

def known(words): 
	# "The subset of `words` that appear in the dictionary of WORDS."
	return set(w for w in words if w in WORDS)

def edits1(word):
	# "All edits that are one edit away from `word`."
	letters    = 'abcdefghijklmnopqrstuvwxyz'
	splits     = [(word[:i], word[i:])    for i in range(len(word) + 1)] # [('', 'kemarin'), ('k', 'emarin'), ('ke', 'marin'), dst]
	deletes    = [L + R[1:]               for L, R in splits if R] # ['emarin', 'kmarin', 'kearin', dst]
	transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R)>1] # ['ekmarin', 'kmearin', 'keamrin', dst]
	replaces   = [L + c + R[1:]           for L, R in splits if R for c in letters] # ['aemarin', 'bemarin', 'cemarin', dst]
	inserts    = [L + c + R               for L, R in splits for c in letters] # ['akemarin', 'bkemarin', 'ckemarin', dst]
	return set(deletes + transposes + replaces + inserts)

def edits2(word): 
	# "All edits that are two edits away from `word`."
	return (e2 for e1 in edits1(word) for e2 in edits1(e1))

#remove stopword
def removeStopwords(x):
	# Removing all the stopwords
	filtered_words = [word for word in x.split() if word not in STOPWORDS]
	
	return " ".join(filtered_words)

@app.route('/predict', methods=['GET'])
def index():
	arr_message = request.args.getlist('message')
	error = ''
	predict_proba = ''
	predict = ''

	return_arr = []
	for message in arr_message:
		try:
			if len(message) > 0:
				a=stripTagsAndUris(message)
				b=removePunctuation(a)
				c=removeStopwords(b)
				d=stemming(c)
				e=correction(d)

				select_vectorizer="SELECT vectorizer FROM model"
				select_classifier="SELECT classifier FROM model"
				cur = conn.cursor()
				cur.execute(select_vectorizer)
				vectorizer=cur.fetchone()
				unpickling_vectorizer=[]
				for unvect in vectorizer:
					unpickling_vectorizer.append(unvect)
				cur.execute(select_classifier)
				classifier=cur.fetchone()
				unpickling_classifier=[]
				for unclassy in classifier:
					unpickling_classifier.append(unclassy)
				loadvectorizer=pickle.loads(b"".join(unpickling_vectorizer))
				loadclassifier=pickle.loads(b"".join(unpickling_classifier))
				vectorize_message = loadvectorizer.transform([e])
				predict = loadclassifier.predict(vectorize_message)[0]
				predict_proba = loadclassifier.predict_proba(vectorize_message).tolist()
				dicti = {}
				dicti['message'] = message
				dicti['predict'] = predict
				dicti['predict_proba'] = predict_proba
				dicti['error']      = error
				return_arr.append(dicti)
		except BaseException as inst:
			error = str(type(inst).__name__) + ' ' + str(inst)
	return jsonify(return_arr)

@app.route('/feedback', methods=['POST'])
def Create_Data():
	json = {
	'category': request.json['category'],
	'message': request.json['message']}

	a=stripTagsAndUris(json['message'])
	b=removePunctuation(a)
	c=removeStopwords(b)
	d=stemming(c)
	e=correction(d)

	data = pd.read_sql_table("data_latih", engine, columns=['label', 'term'])
	for index, row in data.iterrows():
		if row["term"] == e and row["label"] != json['category']:
			status = 'inconsisten'
			break
		elif row["term"] == e and row["label"] == json['category']:
			status = 'duplicate'
			break
		else:
			status = 'not exist'

	print(status)
	if status == 'inconsisten':
		delete_str = "DELETE FROM data_latih WHERE term = %s"
		cur = conn.cursor()
		cur.execute(delete_str, (e,))
		conn.commit()
	if status == 'not exist':
		dataInsert = pd.DataFrame({'label':[json['category']],'term':[d]})
		dataInsert.to_sql('data_latih', engine, if_exists='append',index=False)
	return jsonify(json), 201

if __name__ == '__main__':
	port = int(os.environ.get('PORT', 5000))
	app.run(debug=True, use_reloader=False, host='0.0.0.0', port=port)