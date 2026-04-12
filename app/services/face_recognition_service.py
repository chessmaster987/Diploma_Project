import base64
import os
from datetime import datetime
from pathlib import Path
from time import time

import cv2
import face_recognition

from app.services.db import get_db_connection


class FaceRecognitionService:
    def __init__(self):
        self.known_faces_path = Path(__file__).resolve().parents[2] / "KnownFaces"
        self.last_attendance_time = 0
        self.images = []
        self.class_names = []
        self.encode_list_known = []
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
