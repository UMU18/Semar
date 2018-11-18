import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.multiclass import OneVsRestClassifier
from sklearn.svm import SVC
import pandas as pd
import pickle
import psycopg2
from sqlalchemy import create_engine
import time

#initialization variable
global Classifier
global Vectorizer

#make connection
DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
engine = create_engine(os.environ['DATABASE_URL'])

#read dictionary
def words(text): return re.findall(r'\w+', text.lower())

WORDS = Counter(words(open('spellcheck.txt').read()))
ROOTWORDS = Counter(words(open('kata-dasar.txt').read()))
STOPWORDS = Counter(words(open('stopword.txt').read()))

#perform learning
Classifier = OneVsRestClassifier(SVC(kernel='linear', probability=True))
Vectorizer = TfidfVectorizer()

start=time.time()
print("learning start.....")
df= pd.read_sql_table("data_latih", engine, columns=['label', 'term'])
x = df.iloc[:,0]
y = df.iloc[:,1]
vectorize_text = Vectorizer.fit_transform(y)
Classifier.fit(vectorize_text, x)
model_vectorizer = pickle.dumps(Vectorizer)
model_classifier = pickle.dumps(Classifier)
insert_str = "INSERT INTO model (vectorizer, classifier) values (%s, %s)"
update_str = "UPDATE model SET vectorizer=%s, classifier=%s where ID=%s"
cur = conn.cursor()
cur.execute("SELECT * from model")
msq=cur.fetchone()
if not msq:
    cur.execute(insert_str, (model_vectorizer, model_classifier,))
else:
    cur.execute(update_str,(model_vectorizer, model_classifier, 1))
conn.commit()
end= time.time()
execute_time=end-start
print("learning finish in "+str(execute_time)+" second")
