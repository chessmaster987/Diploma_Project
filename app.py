import cv2
import os
from flask import Flask, session, Response, render_template, request, redirect, url_for, jsonify
import base64
import psycopg2  # pip install psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = "vlad"

DB_HOST = "localhost"
DB_NAME = "Dyplom"
DB_USER = "postgres"
DB_PASS = "25082003"

conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER,
                        password=DB_PASS, host=DB_HOST)

camera = cv2.VideoCapture(0)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def generate_frames_with_faces():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = conn.cursor()
        cur.execute(
            "SELECT username FROM login WHERE username = %s AND password = %s", (username, password))
        user = cur.fetchone()

        if user:
            cur.execute(
                "SELECT role FROM login WHERE username = %s", (username,))
            role = cur.fetchone()
            if role and role[0] == 'admin':
                session['username'] = username
                return redirect('/teacher')
            elif role and role[0] == 'student':
                session['username'] = username
                return redirect('/student')
        else:
            return 'Неправильний логін або пароль'

    return render_template('login.html')

@app.route('/student', methods=['GET', 'POST'])
def student():
    username = session.get('username', None)
    print(username)
    cur = conn.cursor()
    return render_template('student/student.html', username=username)

@app.route('/teacher', methods=['GET', 'POST'])
def teacher():
    username = session.get('username', None)
    print(username)
    cur = conn.cursor()
    return render_template('teacher/teacher.html', username=username)

@app.route('/add_info', methods=['GET', 'POST'])
def add_info():
    username = session.get('username', None)
    return render_template('student/add_info.html')










@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        # Код для виходу
        # удалить из сессии имя пользователя, если оно там есть
        session.pop('username', None)
        print(session.get('username', None))
        return redirect(url_for('login'))  # Переадресація на сторінку login

@app.route('/registration', methods=['GET', 'POST'])
def registration():
    return render_template('registration.html')

@app.route('/authorization', methods=['GET', 'POST'])
def authorization():
    return redirect(url_for('verify_registration'))

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed_with_faces')
def video_feed_with_faces():
    return Response(generate_frames_with_faces(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/save_photo', methods=['POST'])
def save_photo():
    data = request.get_json()
    photo_data = data['photo_data']
    user_name = data['user_name']
    surname = data['surname']

    # Remove the "data:image/jpeg;base64," prefix
    photo_data = photo_data.split(",")[1]

    # Decode base64 data
    photo_data = base64.b64decode(photo_data)

    # Save photo as JPEG file
    save_path = 'photos'
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    photo_filename = f'{user_name} - {surname}.jpg'
    photo_path = os.path.join(save_path, photo_filename)
    with open(photo_path, 'wb') as f:
        f.write(photo_data)

    return jsonify({'message': 'Photo saved successfully', 'photo_path': photo_path})

@app.route('/verify_registration')
def verify_registration():
    return render_template('verify.html')

if __name__ == '__main__':
    app.run(debug=True)