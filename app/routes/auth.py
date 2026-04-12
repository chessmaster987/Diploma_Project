from flask import Blueprint, redirect, render_template, request, session, url_for

from app.services.db import get_db_connection


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT username, role
                    FROM login
                    WHERE username = %s AND password = %s
                    """,
                    (username, password),
                )
                user = cursor.fetchone()
        finally:
            connection.close()

        if not user:
            return "Неправильний логін або пароль"

        session["username"] = user[0]
        if user[1] == "admin":
            return redirect(url_for("teacher.teacher_dashboard"))
        if user[1] == "student":
            return redirect(url_for("student.student_dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("username", None)
    return redirect(url_for("auth.login"))
