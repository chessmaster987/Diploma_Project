import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from flask import Flask, session, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "diploma"


@app.route('/', methods=['GET', 'POST'])
def test():
    #return 'It is a testing example'
    return render_template('index.html')







'''
cred = credentials.Certificate(
    "test-d450b-firebase-adminsdk-5y2qa-79be3097eb.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

Obj1 = {
    'Name': 'Mike',
    'Age': 25,
    'Gender': 'M'
}

Obj2 = {
    'Name': 'Alice',
    'Age': 15,
    'Gender': 'F'
}

data = [Obj1, Obj2]

print(data)

for record in data:
    doc_ref = db.collection(u'Users').document(record['Name'])
    doc_ref.set(record)
'''

if __name__ == '__main__':
    app.run(debug=True)
