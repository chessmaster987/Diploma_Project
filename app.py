import cv2
import numpy as np
import face_recognition
from datetime import datetime
import threading
import tkinter as tk
from tkinter import messagebox
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

path = 'KnownFaces'
images = []
classNames = []
myList = os.listdir(path)
print(myList)

camera = cv2.VideoCapture(0)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

for cls in myList:
    curImg = cv2.imread(f'{path}/{cls}')
    images.append(curImg)
    classNames.append(os.path.splitext(cls)[0])

print(classNames)

def findEncodings(images):
    encodeList = []
    for img in images:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(img)
        if encodings:  # Перевірка, чи знайдені обличчя
            encode = encodings[0]
            encodeList.append(encode)
    return encodeList

def markAttendance(name):
    with open("Attendance.csv", "r+") as f:
        myDataList = f.readlines()
        nameList = []
        for line in myDataList:
            entry = line.split(',')
            nameList.append(entry[0])
        if name not in nameList:
            now = datetime.now()
            dtString = now.strftime("%Y-%m-%d %H:%M:%S")
            f.writelines(f'\n{name}, {dtString}')

encodeListKnown = findEncodings(images)
print("Декодування закінчено")

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
            imgS = cv2.resize(frame, (0, 0), None, 0.25, 0.25)
            imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

            facesCurFrame = face_recognition.face_locations(imgS)
            encodeCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)

            for encodeFace, faceLoc in zip(encodeCurFrame, facesCurFrame):
                matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
                faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
                matchIndex = np.argmin(faceDis)

                if matches[matchIndex]:
                    name = classNames[matchIndex]
                    y1, x2, y2, x1 = faceLoc
                    y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.rectangle(frame, (x1, y2 - 35), (x2, y2), (0, 255, 0), cv2.FILLED)
                    cv2.putText(frame, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
                    markAttendance(name)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
def start_face_check():
    def run():
        window = tk.Tk()
        window.title("Перевірка відвідування")

        lmain = tk.Label(window)
        lmain.pack()

        def show_frame():
            success, frame = camera.read()
            if success:
                imgS = cv2.resize(frame, (0, 0), None, 0.25, 0.25)
                imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

                facesCurFrame = face_recognition.face_locations(imgS)
                encodeCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)

                for encodeFace, faceLoc in zip(encodeCurFrame, facesCurFrame):
                    matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
                    faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
                    matchIndex = np.argmin(faceDis)

                    if matches[matchIndex]:
                        name = classNames[matchIndex]
                        y1, x2, y2, x1 = faceLoc
                        y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.rectangle(frame, (x1, y2 - 35), (x2, y2), (0, 255, 0), cv2.FILLED)
                        cv2.putText(frame, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
                        markAttendance(name)

                cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
                img = tk.PhotoImage(image=tk.fromarray(cv2image))
                lmain.imgtk = img
                lmain.configure(image=img)
            lmain.after(10, show_frame)

        show_frame()
        window.mainloop()

    thread = threading.Thread(target=run)
    thread.start()

@app.route('/start_face_check', methods=['POST'])
def start_face_check_route():
    start_face_check()
    return jsonify({'success': True})


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
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""select full_name, class_number from student where login = %s""", (username,))
    student_info = cur.fetchall()
    print(student_info)
    return render_template('student/student.html', username=username, student_info=student_info)

@app.route('/teacher', methods=['GET', 'POST'])
def teacher():
    username = session.get('username', None)
    print(username)
    cur = conn.cursor()
    return render_template('teacher/teacher.html', username=username)

@app.route('/add_info', methods=['GET', 'POST'])
def add_info():
    username = session.get('username', None)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        fio = request.form['fio']
        class_name = request.form['class']
        cur.execute(
            "INSERT INTO student (login, full_name, class_number) VALUES (%s,%s,%s)", (username, fio, class_name))
        conn.commit()
        return redirect(url_for('add_info'))
    return render_template('student/add_info.html')

@app.route('/info_student', methods=['GET', 'POST'])
def info_student():
    username = session.get('username', None)
    cur = conn.cursor()
    cur.execute("""select * from login where login.role = 'student'""")
    student_data = cur.fetchall()
    return render_template('teacher/info_student.html', student_data=student_data)

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        role = request.form['student_role']
        cur.execute(
            "INSERT INTO login (username, password, role) VALUES (%s,%s,%s)", (login, password, role))
        conn.commit()
        return redirect(url_for('info_student'))
    
@app.route('/student_detailed/<id>', methods=['GET', 'POST'])
def student_detailed(id):
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""select * from student where login = %s""", (id,))
    student_detailed = cur.fetchall()
    print(student_detailed)
    return render_template('teacher/student_detailed.html', student_detailed=student_detailed)

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
    return render_template('student/registration.html')

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
    return render_template('student/verify.html')

if __name__ == '__main__':
    app.run(debug=True)