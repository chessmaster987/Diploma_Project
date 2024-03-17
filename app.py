from flask import Flask, session, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "diploma"

@app.route('/', methods=['GET', 'POST'])
def test():
   return 'It is a testing example'

if __name__ == '__main__':
   app.run(debug = True)
