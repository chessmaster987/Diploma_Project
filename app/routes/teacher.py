import os

from flask import Blueprint, redirect, render_template, request, session, url_for

from app.services.db import get_cursor, get_db_connection
from app.services.face_recognition_service import face_service


teacher_bp = Blueprint("teacher", __name__)


def require_teacher_session():
    username = session.get("username")
    if not username:
        return None, redirect(url_for("auth.login"))
    return username, None


@teacher_bp.route("/teacher", methods=["GET", "POST"])
def teacher_dashboard():
    username, redirect_response = require_teacher_session()
    if redirect_response:
        return redirect_response

    return render_template("teacher/teacher.html", username=username)


@teacher_bp.route("/info_student")
def info_student():
    _, redirect_response = require_teacher_session()
    if redirect_response:
        return redirect_response

    connection = get_db_connection()
    try:
        with get_cursor(connection) as cursor:
            cursor.execute("SELECT * FROM login WHERE login.role = 'student'")
            student_data = cursor.fetchall()
    finally:
        connection.close()

    return render_template("teacher/info_student.html", student_data=student_data)


@teacher_bp.route("/add_student", methods=["POST"])
def add_student():
    _, redirect_response = require_teacher_session()
    if redirect_response:
        return redirect_response

    connection = get_db_connection()
    try:
        with get_cursor(connection, dict_cursor=True) as cursor:
            cursor.execute(
                "INSERT INTO login (username, password, role) VALUES (%s, %s, %s)",
                (
                    request.form["login"],
                    request.form["password"],
                    request.form["student_role"],
                ),
            )
        connection.commit()
    finally:
        connection.close()

    return redirect(url_for("teacher.info_student"))


@teacher_bp.route("/student_detailed/<id>", methods=["GET"])
def student_detailed(id):
    _, redirect_response = require_teacher_session()
    if redirect_response:
        return redirect_response

    connection = get_db_connection()
    try:
        with get_cursor(connection, dict_cursor=True) as cursor:
            cursor.execute(
                """
                SELECT student.login, student.full_name, classes.class_name, student.year_of_grade
                FROM student
                INNER JOIN classes ON student.class_number = classes.class_number
                WHERE login = %s
                """,
                (id,),
            )
            student_detailed_info = cursor.fetchall()
    finally:
        connection.close()

    return render_template(
        "teacher/student_detailed.html",
        student_detailed=student_detailed_info,
    )


@teacher_bp.route("/delete_student/<id>", methods=["GET", "POST"])
def delete_student(id):
    _, redirect_response = require_teacher_session()
    if redirect_response:
        return redirect_response

    connection = get_db_connection()
    try:
        with get_cursor(connection, dict_cursor=True) as cursor:
            cursor.execute("DELETE FROM attendance WHERE login = %s", (id,))
            cursor.execute("DELETE FROM student WHERE login = %s", (id,))
            cursor.execute("DELETE FROM login WHERE login.username = %s", (id,))
        connection.commit()
    finally:
        connection.close()

    photo_path = os.path.join("KnownFaces", f"{id}.jpg")
    if os.path.exists(photo_path):
        os.remove(photo_path)
    face_service.load_images_and_encodings()

    return redirect(url_for("teacher.info_student"))


@teacher_bp.route("/info_classes")
def info_classes():
    _, redirect_response = require_teacher_session()
    if redirect_response:
        return redirect_response

    connection = get_db_connection()
    try:
        with get_cursor(connection, dict_cursor=True) as cursor:
            cursor.execute("SELECT * FROM classes")
            classes_data = cursor.fetchall()
    finally:
        connection.close()

    return render_template("teacher/info_classes.html", classes_data=classes_data)


@teacher_bp.route("/add_class", methods=["GET", "POST"])
def add_class():
    _, redirect_response = require_teacher_session()
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        connection = get_db_connection()
        try:
            with get_cursor(connection, dict_cursor=True) as cursor:
                class_name = request.form["class_name"]
                cursor.execute("SELECT class_name FROM classes")
                class_names = [row["class_name"] for row in cursor.fetchall()]

                if class_name in class_names:
                    return "Цей клас вже існує!"

                cursor.execute(
                    "INSERT INTO classes (class_name) VALUES (%s)",
                    (class_name,),
                )
            connection.commit()
        finally:
            connection.close()

        return redirect(url_for("teacher.info_classes"))

    return redirect(url_for("teacher.info_classes"))


@teacher_bp.route("/edit_class/<id>", methods=["GET"])
def edit_class(id):
    _, redirect_response = require_teacher_session()
    if redirect_response:
        return redirect_response

    connection = get_db_connection()
    try:
        with get_cursor(connection, dict_cursor=True) as cursor:
            cursor.execute(
                """
                SELECT class_number, class_name
                FROM classes
                WHERE class_number = %s
                """,
                (id,),
            )
            class_data = cursor.fetchone()
    finally:
        connection.close()

    return render_template("teacher/edit_class.html", classes=class_data)


@teacher_bp.route("/update_class/<id>", methods=["POST"])
def update_class(id):
    _, redirect_response = require_teacher_session()
    if redirect_response:
        return redirect_response

    connection = get_db_connection()
    try:
        with get_cursor(connection, dict_cursor=True) as cursor:
            cursor.execute(
                "UPDATE classes SET class_name = %s WHERE class_number = %s",
                (request.form["class_name"], id),
            )
        connection.commit()
    finally:
        connection.close()

    return redirect(url_for("teacher.info_classes"))


@teacher_bp.route("/check_attendance")
def check_attendance():
    _, redirect_response = require_teacher_session()
    if redirect_response:
        return redirect_response

    connection = get_db_connection()
    try:
        with get_cursor(connection, dict_cursor=True) as cursor:
            cursor.execute("SELECT class_number, class_name FROM classes")
            classes_info = cursor.fetchall()
    finally:
        connection.close()

    return render_template("teacher/check_attendance.html", classes_info=classes_info)


@teacher_bp.route("/check_attendance_detailed/<int:id>", methods=["GET", "POST"])
def check_attendance_detailed(id):
    _, redirect_response = require_teacher_session()
    if redirect_response:
        return redirect_response

    attendance_detailed = []

    connection = get_db_connection()
    try:
        with get_cursor(connection, dict_cursor=True) as cursor:
            if request.method == "POST":
                cursor.execute(
                    """
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
                    """,
                    (id, request.form["year_of_grade"]),
                )
                attendance_detailed = cursor.fetchall()
    finally:
        connection.close()

    return render_template(
        "teacher/check_attendance_detailed.html",
        attendance_detailed=attendance_detailed,
        id=id,
    )


@teacher_bp.route("/attendance_statistics", methods=["GET", "POST"])
def attendance_statistics():
    _, redirect_response = require_teacher_session()
    if redirect_response:
        return redirect_response

    attendance_statistics_data = []

    connection = get_db_connection()
    try:
        with get_cursor(connection, dict_cursor=True) as cursor:
            if request.method == "POST":
                cursor.execute(
                    """
                    SELECT classes.class_name,
                           student.year_of_grade,
                           COUNT(attendance.login) AS quantity,
                           RANK() OVER (ORDER BY COUNT(attendance.login) DESC) AS rank
                    FROM attendance
                    INNER JOIN student ON attendance.login = student.login
                    INNER JOIN classes ON student.class_number = classes.class_number
                    WHERE attendance.timestamp BETWEEN %s AND %s
                    GROUP BY classes.class_name, student.year_of_grade
                    """,
                    (request.form["start_date"], request.form["end_date"]),
                )
                attendance_statistics_data = cursor.fetchall()
    finally:
        connection.close()

    return render_template(
        "teacher/attendance_statistics.html",
        attendance_statistics=attendance_statistics_data,
    )
