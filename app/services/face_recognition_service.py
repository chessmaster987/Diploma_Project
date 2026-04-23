import base64
import math
import os
from datetime import datetime
from pathlib import Path
from time import time

import cv2
import face_recognition
import numpy as np

from app.services.db import get_db_connection


class FaceRecognitionService:
    def __init__(self):
        self.known_faces_path = Path(__file__).resolve().parents[2] / "KnownFaces"
        self.last_attendance_time = 0
        self.images = []
        self.class_names = []
        self.encode_list_known = []
        self.liveness_sessions = {}
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_eye.xml"
        )
        self.load_images_and_encodings()

    def find_encodings(self, images):
        encode_list = []
        for image in images:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            encodings = face_recognition.face_encodings(rgb_image)
            if encodings:
                encode_list.append(encodings[0])
        return encode_list

    def load_images_and_encodings(self):
        self.images = []
        self.class_names = []

        if not self.known_faces_path.exists():
            self.known_faces_path.mkdir(parents=True, exist_ok=True)
            self.encode_list_known = []
            return

        for file_name in os.listdir(self.known_faces_path):
            image_path = self.known_faces_path / file_name
            image = cv2.imread(str(image_path))
            if image is None:
                continue
            self.images.append(image)
            self.class_names.append(Path(file_name).stem)

        self.encode_list_known = self.find_encodings(self.images)

    def mark_attendance(self, username):
        now = time()
        if now - self.last_attendance_time < 60:
            return

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO attendance (login, timestamp) VALUES (%s, %s)",
                    (username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                )
            connection.commit()
            self.last_attendance_time = now
        finally:
            connection.close()

    def _default_liveness_session(self):
        steps = [
            {"id": "blink", "label": "Blink"},
            {"id": "turn_left", "label": "Turn your head left"},
            {"id": "turn_right", "label": "Turn your head right"},
        ]
        return {
            "steps": steps,
            "step_index": 0,
            "completed": False,
            "message": f"Step 1 of {len(steps)}: {steps[0]['label']}",
            "blink_ready": False,
            "blink_closed": False,
            "metrics": {},
        }

    def start_liveness_session(self, username):
        self.liveness_sessions[username] = self._default_liveness_session()
        return self.get_liveness_status(username)

    def get_liveness_status(self, username):
        session = self.liveness_sessions.get(username)
        if not session:
            session = self._default_liveness_session()
            self.liveness_sessions[username] = session

        current_step = None
        if not session["completed"]:
            current_step = session["steps"][session["step_index"]]["id"]

        return {
            "completed": session["completed"],
            "message": session["message"],
            "step_index": session["step_index"],
            "steps": session["steps"],
            "current_step": current_step,
            "metrics": session.get("metrics", {}),
        }

    def is_liveness_complete(self, username):
        session = self.liveness_sessions.get(username)
        return bool(session and session["completed"])

    def _decode_base64_image(self, photo_data):
        encoded_photo = photo_data.split(",")[1]
        decoded_photo = base64.b64decode(encoded_photo)
        image_array = np.frombuffer(decoded_photo, dtype=np.uint8)
        return cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    def _point_distance(self, point_a, point_b):
        return math.dist(point_a, point_b)

    def _eye_aspect_ratio(self, eye_points):
        vertical_1 = self._point_distance(eye_points[1], eye_points[5])
        vertical_2 = self._point_distance(eye_points[2], eye_points[4])
        horizontal = self._point_distance(eye_points[0], eye_points[3])
        if horizontal == 0:
            return 0
        return (vertical_1 + vertical_2) / (2.0 * horizontal)

    def _complete_liveness_step(self, session):
        session["step_index"] += 1
        if session["step_index"] >= len(session["steps"]):
            session["completed"] = True
            session["message"] = "Liveness check completed. You can now save your registration photo."
            return

        next_step = session["steps"][session["step_index"]]["label"]
        session["message"] = (
            f"Great. Step {session['step_index'] + 1} of {len(session['steps'])}: {next_step}"
        )

    def analyze_liveness_frame(self, username, photo_data):
        session = self.liveness_sessions.get(username)
        if not session:
            session = self._default_liveness_session()
            self.liveness_sessions[username] = session

        if session["completed"]:
            return self.get_liveness_status(username)

        image = self._decode_base64_image(photo_data)
        if image is None:
            session["message"] = "Camera frame is invalid. Please try again."
            return self.get_liveness_status(username)

        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        landmarks_list = face_recognition.face_landmarks(rgb_image)
        if not landmarks_list:
            session["message"] = "Face not detected. Keep your face centered in the frame."
            return self.get_liveness_status(username)

        landmarks = landmarks_list[0]
        current_step = session["steps"][session["step_index"]]["id"]

        if current_step == "blink":
            if "left_eye" not in landmarks or "right_eye" not in landmarks:
                session["message"] = "Eyes are not clearly visible. Look straight into the camera."
                return self.get_liveness_status(username)

            left_ear = self._eye_aspect_ratio(landmarks["left_eye"])
            right_ear = self._eye_aspect_ratio(landmarks["right_eye"])
            avg_ear = (left_ear + right_ear) / 2
            session["metrics"] = {"eye_ratio": round(float(avg_ear), 3)}

            if avg_ear > 0.215:
                session["blink_ready"] = True
            elif session["blink_ready"] and avg_ear < 0.185:
                session["blink_closed"] = True
            elif session["blink_ready"] and session["blink_closed"] and avg_ear > 0.205:
                session["blink_ready"] = False
                session["blink_closed"] = False
                self._complete_liveness_step(session)
                return self.get_liveness_status(username)

            session["message"] = "Step 1 of 3: Blink once."
            return self.get_liveness_status(username)

        if "left_eye" not in landmarks or "right_eye" not in landmarks or "nose_tip" not in landmarks:
            session["message"] = "Face landmarks are unclear. Please keep your face visible."
            return self.get_liveness_status(username)

        left_eye_center = np.mean(landmarks["left_eye"], axis=0)
        right_eye_center = np.mean(landmarks["right_eye"], axis=0)
        nose_point = np.array(landmarks["nose_tip"][2], dtype=float)
        eye_midpoint = (left_eye_center + right_eye_center) / 2
        eye_distance = np.linalg.norm(right_eye_center - left_eye_center)

        if eye_distance == 0:
            session["message"] = "Hold your head steady and try again."
            return self.get_liveness_status(username)

        horizontal_offset = (nose_point[0] - eye_midpoint[0]) / eye_distance
        session["metrics"] = {"head_turn_offset": round(float(horizontal_offset), 3)}

        if current_step == "turn_left":
            if horizontal_offset < -0.075:
                self._complete_liveness_step(session)
            else:
                session["message"] = "Step 2 of 3: Turn your head left a bit more."
            return self.get_liveness_status(username)

        if current_step == "turn_right":
            if horizontal_offset > 0.075:
                self._complete_liveness_step(session)
            else:
                session["message"] = "Step 3 of 3: Turn your head right a bit more."

        return self.get_liveness_status(username)

    def generate_frames(self):
        camera = cv2.VideoCapture(0)
        try:
            while True:
                success, frame = camera.read()
                if not success:
                    break

                _, buffer = cv2.imencode(".jpg", frame)
                frame_bytes = buffer.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
        finally:
            camera.release()

    def generate_frames_with_faces(self):
        camera = cv2.VideoCapture(0)
        try:
            while True:
                success, frame = camera.read()
                if not success:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
                )

                for (x, y, w, h) in faces:
                    face_image = frame[y : y + h, x : x + w]
                    roi_gray = gray[y : y + h, x : x + w]
                    roi_color = frame[y : y + h, x : x + w]

                    eyes = self.eye_cascade.detectMultiScale(roi_gray)
                    for (ex, ey, ew, eh) in eyes:
                        cv2.rectangle(
                            roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2
                        )

                    face_image_rgb = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
                    face_encoding = face_recognition.face_encodings(face_image_rgb)

                    if face_encoding:
                        matches = face_recognition.compare_faces(
                            self.encode_list_known, face_encoding[0]
                        )
                        for index, match in enumerate(matches):
                            if not match:
                                continue

                            name = self.class_names[index]
                            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                            cv2.putText(
                                frame,
                                name,
                                (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.9,
                                (36, 255, 12),
                                2,
                            )
                            self.mark_attendance(name)

                    for landmarks in face_recognition.face_landmarks(face_image_rgb):
                        for landmark in landmarks.values():
                            for point in landmark:
                                cv2.circle(
                                    frame,
                                    (x + point[0], y + point[1]),
                                    1,
                                    (255, 255, 255),
                                    -1,
                                )

                _, buffer = cv2.imencode(".jpg", frame)
                frame_bytes = buffer.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
        finally:
            camera.release()

    def save_photo(self, photo_data, user_name):
        encoded_photo = photo_data.split(",")[1]
        decoded_photo = base64.b64decode(encoded_photo)

        self.known_faces_path.mkdir(parents=True, exist_ok=True)
        photo_path = self.known_faces_path / f"{user_name}.jpg"
        with open(photo_path, "wb") as image_file:
            image_file.write(decoded_photo)

        self.load_images_and_encodings()
        return str(photo_path)


face_service = FaceRecognitionService()
