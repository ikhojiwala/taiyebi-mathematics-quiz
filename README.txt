TAIYEBI STUDENT QUIZ — DEPLOYMENT

Local test:
1. Install Python 3.11+.
2. Open a terminal in this folder.
3. Create a virtual environment: py -m venv .venv
4. Activate it: .venv\Scripts\activate (Windows) or source .venv/bin/activate (Mac/Linux).
5. Install: pip install -r requirements.txt
6. Run: python app.py
7. Visit http://127.0.0.1:8080

Deploy:
1. Upload app.py, requirements.txt, Procfile and render.yaml to a GitHub repository.
2. Create a Python web service on a host supporting Flask and Gunicorn.
3. Build command: pip install -r requirements.txt
4. Start command: gunicorn app:app
5. Set SECRET_KEY to a long random value.
6. Create a managed PostgreSQL database and set DATABASE_URL to its connection URL.
7. Deploy, then add your custom domain in the host dashboard and set the DNS records it provides.

Notes:
- Production should use managed PostgreSQL via DATABASE_URL; SQLite is for local testing only.
- First version has no admin panel. The question bank is built into app.py; admin management will be a later step.
- Roll number validation checks that the digits begin with the selected class number.
- Student roll/class is not a secure identity verification system; use school-approved authentication for official exams.
