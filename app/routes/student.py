import os

from flask import Blueprint, Response, jsonify, redirect, render_template, request, session, url_for

from app.services.db import get_cursor, get_db_connection
from app.services.face_recognition_service import face_service


student_bp = Blueprint("student", __name__)


def require_student_session():
    username = session.get("username")
    role = session.get("role")
    if not username or not role:
        return None, redirect(url_for("auth.login"))
    if role != "student":
        if role == "admin":
            return None, redirect(url_for("teacher.teacher_dashboard"))
        return None, redirect(url_for("auth.login"))
    return username, None


@student_bp.route("/student", methods=["GET", "POST"])
def student_dashboard():
    username, redirect_response = require_student_session()
    if redirect_response:
        return redirect_response

    connection = get_db_connection()
    try:
        with get_cursor(connection, dict_cursor=True) as cursor:
            cursor.execute(
                """
                SELECT student.full_name, classes.class_name, student.year_of_grade
                FROM student
                INNER JOIN classes ON student.class_number = classes.class_number
                WHERE login = %s
                """,
                (username,),
            )
            student_info = cursor.fetchall()

            cursor.execute("SELECT class_number, class_name FROM classes")
            class_info = cursor.fetchall()
    finally:
        connection.close()

    if not student_info:
        student_info = [("Інформація ще не внесена користувачем", "", "")]

    can_edit = student_info[0][0] != "Інформація ще не внесена користувачем"
    return render_template(
        "student/student.html",
        username=username,
        student_info=student_info,
        can_edit=can_edit,
        class_info=class_info,
    )


@student_bp.route("/add_info", methods=["GET", "POST"])
def add_info():
    username, redirect_response = require_student_session()
    if redirect_response:
        return redirect_response

    connection = get_db_connection()
    try:
        with get_cursor(connection, dict_cursor=True) as cursor:
            cursor.execute("SELECT class_number, class_name FROM classes")
            class_info = cursor.fetchall()

            cursor.execute(
                """
                SELECT full_name, class_number, year_of_grade
                FROM student
                WHERE login = %s
                """,
                (username,),
            )
            student_info = cursor.fetchone()

            is_info_complete = student_info and all(student_info)

            if request.method == "POST" and not is_info_complete:
                cursor.execute(
                    """
                    INSERT INTO student (login, full_name, class_number, year_of_grade)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        username,
                        request.form["fio"],
                        request.form["class"],
                        request.form["year_of_grade"],
                    ),
                )
                connection.commit()
                return redirect(url_for("student.add_info"))
    finally:
        connection.close()

    return render_template(
        "student/add_info.html",
        class_info=class_info,
        is_info_complete=is_info_complete,
    )


@student_bp.route("/edit_info", methods=["POST"])
def edit_info():
    username, redirect_response = require_student_session()
    if redirect_response:
        return redirect_response

    connection = get_db_connection()
    try:
        with get_cursor(connection, dict_cursor=True) as cursor:
            cursor.execute(
                """
                UPDATE student
                SET full_name = %s, class_number = %s, year_of_grade = %s
                WHERE login = %s
                """,
                (
                    request.form["fio"],
                    request.form["class"],
                    request.form["year_of_grade"],
                    username,
                ),
            )
        connection.commit()
    finally:
        connection.close()

    return redirect(url_for("student.student_dashboard"))


@student_bp.route("/registration", methods=["GET", "POST"])
def registration():
    username, redirect_response = require_student_session()
    if redirect_response:
        return redirect_response

    connection = get_db_connection()
    try:
        with get_cursor(connection, dict_cursor=True) as cursor:
            cursor.execute("SELECT full_name FROM student WHERE login = %s", (username,))
            student_info = cursor.fetchone()
    finally:
        connection.close()

    full_name = student_info["full_name"] if student_info else ""
    photo_path = os.path.join("KnownFaces", f"{username}.jpg")
    photo_exists = os.path.exists(photo_path)

    return render_template(
        "student/registration.html",
        full_name=full_name,
        username=username,
        photo_exists=photo_exists,
    )


@student_bp.route("/authorization", methods=["GET", "POST"])
def authorization():
    return redirect(url_for("student.verify_registration"))


@student_bp.route("/video_feed")
def video_feed():
    _, redirect_response = require_student_session()
    if redirect_response:
        return redirect_response

    return Response(
        face_service.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@student_bp.route("/video_feed_with_faces")
def video_feed_with_faces():
    _, redirect_response = require_student_session()
    if redirect_response:
        return redirect_response

    return Response(
        face_service.generate_frames_with_faces(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@student_bp.route("/save_photo", methods=["POST"])
def save_photo():
    _, redirect_response = require_student_session()
    if redirect_response:
        return redirect_response

    data = request.get_json()
    photo_path = face_service.save_photo(data["photo_data"], data["user_name"])
    return jsonify({"message": "Photo saved successfully", "photo_path": photo_path})


@student_bp.route("/verify_registration")
def verify_registration():
    _, redirect_response = require_student_session()
    if redirect_response:
        return redirect_response

    return render_template("student/verify.html")


@student_bp.route("/attendance_history", methods=["GET", "POST"])
def attendance_history():
    username, redirect_response = require_student_session()
    if redirect_response:
        return redirect_response

    attendance_data = []
    if request.method == "POST":
        connection = get_db_connection()
        try:
            with get_cursor(connection, dict_cursor=True) as cursor:
                cursor.execute(
                    "SELECT * FROM attendance_info(%s, %s, %s)",
                    (
                        request.form["start_date"],
                        request.form["end_date"],
                        username,
                    ),
                )
                attendance_data = cursor.fetchall()
        finally:
            connection.close()

    return render_template(
        "student/attendance_history.html",
        attendance_data=attendance_data,
    )
