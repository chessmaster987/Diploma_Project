import cv2
import numpy as np
import face_recognition
from datetime import datetime
from os.path import getmtime
from time import time
import os
from flask import Flask, session, Response, flash, render_template, request, redirect, url_for, jsonify
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

last_attendance_time = 0
def check_last_attendance():
    global last_attendance_time

    csv_path = "Attendance.csv"
    if os.path.exists(csv_path):
        last_modified = getmtime(csv_path)
        last_attendance_time = last_modified
    else:
        last_attendance_time = 0

#camera = cv2.VideoCapture(0)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
# Завантаження додаткових каскадів Хаара для очей
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

def findEncodings(images):
    encodeList = []
    for img in images:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(img)
        if encodings:  # Перевірка, чи знайдені обличчя
            encode = encodings[0]
            encodeList.append(encode)
    return encodeList

def load_images_and_encodings():
    global images, classNames, encodeListKnown
    images = []
    classNames = []
    myList = os.listdir(path)
    for cls in myList:
        curImg = cv2.imread(f'{path}/{cls}')
        images.append(curImg)
        classNames.append(os.path.splitext(cls)[0])
    encodeListKnown = findEncodings(images)
    print("Декодування закінчено")

load_images_and_encodings()

def markAttendance(name):
    global last_attendance_time
    now = time()
    if now - last_attendance_time >= 60:  # Якщо минула хвилина з останнього запису
        cur = conn.cursor()
        dtString = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("INSERT INTO attendance (login, timestamp) VALUES (%s, %s)", (name, dtString))
        conn.commit()
        last_attendance_time = now

encodeListKnown = findEncodings(images)
print("Декодування закінчено")

def generate_frames():
    camera = cv2.VideoCapture(0)
    try:
        while True:
            success, frame = camera.read()
            if not success:
                break
            else:
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    finally:
        camera.release()

def generate_frames_with_faces():
    camera = cv2.VideoCapture(0)
    try:
        while True:
            success, frame = camera.read()
            if not success:
                break
            else:
                # Перетворення кадру в сірий колір
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Визначення обличчя за допомогою каскадів Хаара
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

                for (x, y, w, h) in faces:
                    # Виділення обличчя з кадру
                    face_img = frame[y:y+h, x:x+w]

                    # Виділення області обличчя для подальшої обробки
                    roi_gray = gray[y:y+h, x:x+w]
                    roi_color = frame[y:y+h, x:x+w]
                    
                    # Визначення очей
                    eyes = eye_cascade.detectMultiScale(roi_gray)
                    for (ex, ey, ew, eh) in eyes:
                        cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 2)

                    # Конвертація обличчя в формат RGB
                    face_img_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)

                    # Отримання кодування обличчя
                    face_encoding = face_recognition.face_encodings(face_img_rgb)

                    if len(face_encoding) > 0:
                        # Порівняння кодування з обличчями у папці KnownFaces
                        matches = face_recognition.compare_faces(encodeListKnown, face_encoding[0])

                        for i, match in enumerate(matches):
                            if match:
                                # Якщо обличчя розпізнано, виведіть ім'я відповідного файлу
                                name = classNames[i]
                                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                                cv2.putText(frame, name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36,255,12), 2)
                                # Реєстрація часу відвідування
                                markAttendance(name)

                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    finally:
        camera.release()

# Оновлення часу останнього запису в CSV
check_last_attendance()

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
    cur.execute("""select student.full_name, classes.class_name, student.year_of_grade 
                from student
                inner join classes on student.class_number = classes.class_number
                where login = %s""", (username,))
    student_info = cur.fetchall()
    if not student_info:
        student_info = [("Інформація ще не внесена користувачем", "Інформація ще не внесена користувачем")]
    print(student_info)
    can_edit = student_info[0][0] != "Інформація ще не внесена користувачем"
    cur.execute("""select class_number, class_name from classes""")
    class_info = cur.fetchall()
    return render_template('student/student.html', username=username, student_info=student_info, can_edit=can_edit, class_info=class_info)

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
    cur.execute("""select class_number, class_name from classes""")
    class_info = cur.fetchall()
    cur.execute("""select full_name, class_number, year_of_grade from student where login = %s""", (username,))
    student_info = cur.fetchone()
    is_info_complete = student_info and all(student_info)  # Перевірка, чи всі поля заповнені
    if request.method == 'POST':
        fio = request.form['fio']
        class_name = request.form['class']
        year_of_grade = request.form['year_of_grade']
        cur.execute(
            "INSERT INTO student (login, full_name, class_number, year_of_grade) VALUES (%s,%s,%s,%s)", (username, fio, class_name, year_of_grade))
        conn.commit()
        return redirect(url_for('add_info'))
    return render_template('student/add_info.html', class_info=class_info, is_info_complete=is_info_complete)

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
    cur.execute("""select student.login, student.full_name, classes.class_name, student.year_of_grade
                from student
                inner join classes on student.class_number = classes.class_number
                where login = %s""", (id,))
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
    username = session.get('username', None)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT full_name FROM student WHERE login = %s", (username,))
    student_info = cur.fetchone()
    full_name = student_info['full_name'] if student_info else ''
     # Перевірка, чи існує фото
    photo_path = os.path.join('KnownFaces', f'{username}.jpg')
    photo_exists = os.path.exists(photo_path)
    return render_template('student/registration.html', full_name=full_name, username=username, photo_exists=photo_exists)

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
    if request.method == 'POST':
        data = request.get_json()
        photo_data = data['photo_data']
        user_name = data['user_name']

        # Remove the "data:image/jpeg;base64," prefix
        photo_data = photo_data.split(",")[1]

        # Decode base64 data
        photo_data = base64.b64decode(photo_data)

        # Save photo as JPEG file
        save_path = 'KnownFaces'
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        photo_filename = f'{user_name}.jpg'
        photo_path = os.path.join(save_path, photo_filename)
        with open(photo_path, 'wb') as f:
            f.write(photo_data)

        # Оновлення закодованих зображень після додавання нового фото
        load_images_and_encodings()

        return jsonify({'message': 'Photo saved successfully', 'photo_path': photo_path})
    return redirect(url_for('registration'))

@app.route('/verify_registration')
def verify_registration():
    return render_template('student/verify.html')

@app.route('/attendance_history', methods=['GET', 'POST'])
def attendance_history():
    username = session.get('username', None)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    attendance_data = []
    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            """SELECT * FROM attendance_info(%s, %s, %s)""", (start_date, end_date, username))
        attendance_data = cur.fetchall()
    return render_template('student/attendance_history.html', attendance_data=attendance_data)

@app.route('/edit_info', methods=['GET','POST'])
def edit_info():
    username = session.get('username', None)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if not username:
        return redirect(url_for('login'))
    if request.method == 'POST':
        fio = request.form['fio']
        class_name = request.form['class']
        year_of_grade = request.form['year_of_grade']
        cur.execute("""UPDATE student SET full_name = %s, class_number = %s, year_of_grade = %s
                     WHERE login = %s""", (fio, class_name, year_of_grade, username))
        conn.commit()
        return redirect(url_for('student'))
    
@app.route('/delete_student/<id>', methods=['GET', 'POST'])
def delete_student(id):
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""delete from attendance where login = %s""", (id,))
    conn.commit()
    cur.execute("""delete from login where login.username = %s""", (id,))
    conn.commit()
    cur.execute("""delete from student where login = %s""", (id,))
    conn.commit()
    # Видалити фото студента з папки KnownFaces
    photo_path = os.path.join('KnownFaces', f'{id}.jpg')
    if os.path.exists(photo_path):
        os.remove(photo_path)
    return redirect(url_for('info_student'))

@app.route('/info_classes', methods=['GET', 'POST'])
def info_classes():
    cur = conn.cursor()
    cur.execute("""SELECT * FROM classes""")
    classes_data = cur.fetchall()
    return render_template('teacher/info_classes.html', classes_data=classes_data)

@app.route('/add_class', methods=['GET', 'POST'])
def add_class():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        class_name = request.form['class_name']
        # Отримуємо усі існуючі назви класів
        cur.execute("""SELECT class_name FROM classes""")
        class_names = [row['class_name'] for row in cur.fetchall()]
        # Перевіряємо, чи назва класу вже існує
        if class_name in class_names:
            return 'Цей клас вже існує!'
        # Якщо назва класу унікальна, додаємо її до бази даних
        cur.execute("INSERT INTO classes (class_name) VALUES (%s)", (class_name,))
        conn.commit()
        return redirect(url_for('info_classes'))
    
@app.route('/edit_class/<id>', methods=['GET', 'POST'])
def edit_class(id):
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""SELECT class_number, class_name 
                FROM classes
                WHERE class_number = %s""", (id,))
    data = cur.fetchall()
    cur.close()
    print(data[0])
    return render_template('teacher/edit_class.html', classes=data[0])

@app.route('/update_class/<id>', methods=['POST', 'GET'])
def update_class(id):
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        class_name = request.form['class_name']
        cur.execute(
            """UPDATE classes SET class_name = %s WHERE class_number = %s""", (class_name, id))
        conn.commit()
        return redirect(url_for('info_classes'))

@app.route('/check_attendance', methods=['POST', 'GET'])
def check_attendance():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""select class_number, class_name from classes""")
    classes_info = cur.fetchall()
    return render_template('teacher/check_attendance.html', classes_info=classes_info)
    
@app.route('/check_attendance_detailed/<id>', methods=['POST', 'GET'])
def check_attendance_detailed(id):
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    attendance_detailed = []
    if request.method == 'POST':
        year_of_grade = request.form['year_of_grade']
        cur.execute("""select attendance.login, student.full_name, classes.class_name, student.year_of_grade, attendance.timestamp
                    from attendance
                    inner join student on attendance.login = student.login
                    inner join classes on student.class_number = classes.class_number
                    where classes.class_number = %s and student.year_of_grade = %s""", (id, year_of_grade))
        attendance_detailed = cur.fetchall()
    return render_template('teacher/check_attendance_detailed.html', attendance_detailed=attendance_detailed, id=id)

@app.route('/attendance_statistics', methods=['POST', 'GET'])
def attendance_statistics():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    attendance_statistics = []
    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        cur.execute("""select classes.class_name, student.year_of_grade, COUNT(attendance.login) as quantity, RANK() OVER (ORDER BY COUNT(attendance.login) DESC) AS rank
                from attendance
                inner join student on attendance.login = student.login
                inner join classes on student.class_number = classes.class_number
                WHERE attendance.timestamp BETWEEN %s AND %s
                Group By classes.class_name, student.year_of_grade
                """, (start_date, end_date))
        attendance_statistics = cur.fetchall()
    return render_template('teacher/attendance_statistics.html', attendance_statistics=attendance_statistics)



if __name__ == '__main__':
    app.run(debug=True)