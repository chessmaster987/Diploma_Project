# Diploma Project

Flask-based attendance tracking system with role-based access for teachers and students, plus face recognition for photo registration and attendance verification.

## Features
- authentication for `admin` and `student` users
- teacher dashboard for student management, class management, attendance review, and statistics
- student dashboard for personal data, photo registration, attendance verification, and attendance history
- face recognition flow backed by images stored in `KnownFaces/`

## Project Structure
- `app/__init__.py`: application factory and blueprint registration
- `app/routes/`: route modules for `auth`, `student`, and `teacher`
- `app/services/`: shared database and face-recognition services
- `app/templates/`: application templates
- `KnownFaces/`: stored student photos used for face recognition
- `static/`: static assets
- `app.py`: local development entrypoint

## Environment Variables
Create a `.env` file with:

```env
DB_HOST="localhost"
DB_NAME="Dyplom"
DB_USER="postgres"
DB_PASS="your-password"
SECRET_KEY="change-me-for-production"
```

`SECRET_KEY` is required for application startup.

## Local Setup
1. Create and activate a virtual environment.
2. Install project dependencies.
3. Configure the `.env` file.
4. Run the application:

```bash
python app.py
```

## Roles
- `admin`: access to teacher routes and management features
- `student`: access to personal data, photo registration, and attendance history

## Notes
- face encodings are currently loaded from images in `KnownFaces/`
- for full local verification you need the required Python packages, camera access, and a configured PostgreSQL database
