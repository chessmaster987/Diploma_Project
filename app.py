import cv2
import os
from flask import Flask, Response, render_template, request, redirect, url_for
import base64

app = Flask(__name__)

camera = cv2.VideoCapture(0)


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


@app.route('/')
def login():
    return render_template('index.html')


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    return render_template('registration.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    return redirect(url_for('login'))


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/save_photo', methods=['POST'])
def save_photo():
    data = request.get_json()
    photo_data = data['photo_data']

    # Remove the "data:image/jpeg;base64," prefix
    photo_data = photo_data.split(",")[1]

    # Decode base64 data
    photo_data = base64.b64decode(photo_data)

    # Save photo as JPEG file
    save_path = 'photos'
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    photo_path = os.path.join(save_path, 'photo.jpg')
    with open(photo_path, 'wb') as f:
        f.write(photo_data)

    return 'Photo saved successfully'


if __name__ == '__main__':
    app.run(debug=True)
