from flask import Blueprint, render_template, session, request, redirect, url_for
import psycopg2.extras
import os

teacher_bp = Blueprint(
    'teacher',
    __name__
)

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASS,
    host=DB_HOST
)

@teacher_bp.route('/teacher', methods=['GET', 'POST'])
def teacher():
    username = session.get('username', None)
    print(username)

    cur = conn.cursor()

    return render_template('teacher/teacher.html', username=username)

# 📌 1. Інформація про студентів
@teacher_bp.route('/info_student')
def info_student():
    username = session.get('username', None)
    cur = conn.cursor()
    cur.execute("""select * from login where login.role = 'student'""")
    student_data = cur.fetchall()
    return render_template('teacher/info_student.html', student_data=student_data)


# 📌 2. Управління класами
@teacher_bp.route('/info_classes')
def info_classes():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""SELECT * FROM classes""")
    classes_data = cur.fetchall()
    return render_template('teacher/info_classes.html', classes_data=classes_data)

@teacher_bp.route('/add_class', methods=['GET', 'POST'])
def add_class():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == 'POST':
        class_name = request.form['class_name']

        cur.execute("SELECT class_name FROM classes")
        class_names = [row['class_name'] for row in cur.fetchall()]

        if class_name in class_names:
            return 'Цей клас вже існує!'

        cur.execute(
            "INSERT INTO classes (class_name) VALUES (%s)",
            (class_name,)
        )
        conn.commit()

        return redirect(url_for('teacher.info_classes'))


# 📌 3. Перегляд відвідувань
@teacher_bp.route('/check_attendance')
def check_attendance():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""select class_number, class_name from classes""")
    classes_info = cur.fetchall()
    return render_template('teacher/check_attendance.html', classes_info=classes_info)

@teacher_bp.route('/check_attendance_detailed/<int:id>', methods=['GET', 'POST'])
def check_attendance_detailed(id):
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    attendance_detailed = []

    if request.method == 'POST':
        year_of_grade = request.form['year_of_grade']

        cur.execute("""
            SELECT attendance.login,
                   student.full_name,
                   classes.class_name,
                   student.year_of_grade,
                   attendance.timestamp
            FROM attendance
            INNER JOIN student ON attendance.login = student.login
            INNER JOIN classes ON student.class_number = classes.class_number
            WHERE classes.class_number = %s
              AND student.year_of_grade = %s
        """, (id, year_of_grade))

        attendance_detailed = cur.fetchall()

    return render_template(
        'teacher/check_attendance_detailed.html',
        attendance_detailed=attendance_detailed,
        id=id
    )


# 📌 4. Статистика відвідувань
@teacher_bp.route('/attendance_statistics', methods=['GET', 'POST'])
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