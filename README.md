# Mini Event Management System (Flask + MySQL)

A tiny, beginner-friendly project to learn:
- HTML/CSS templating (Jinja)
- User registration & login (with password hashing)
- MySQL database via `mysql-connector-python`
- Session-based authentication
- Registering for events

## 1) Prerequisites

- Python 3.10+ installed
- MySQL Server and MySQL Workbench installed
- A MySQL user (e.g., `root`) with a password you know

## 2) Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
cd event_management_miniproject
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
```

**macOS/Linux (bash):**
```bash
cd event_management_miniproject
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3) Create the database

1. Open **MySQL Workbench**.
2. Connect to your local server.
3. Open `schema.sql` (File → Open SQL Script), review, then click the lightning bolt to run.
   - This creates a database `event_mini` and seeds a few sample events.
4. (Optional) In Workbench, expand `Schemas → event_mini` to see tables.

## 4) Configure DB credentials (if needed)

Edit `config.py` to match your MySQL setup:

```python
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "your_password_here"
DB_NAME = "event_mini"
SECRET_KEY = "change-this"
```

## 5) Run the app

```bash
python app.py
```

Now open http://127.0.0.1:5000 in your browser.

## 6) Flow to test

1. Click **Register for this event** on the homepage.
2. You’ll be asked to **log in** → If you are new, click **Create an account**.
3. After registration, go back to **Log in** and sign in with the same email/password.
   - If the password is wrong, you’ll see **Incorrect email or password.**
4. Once logged in, click **Register for this event** again to register.
5. Click **My Registrations** to confirm.

## 7) See your data in MySQL Workbench

Run these queries:

```sql
USE event_mini;
SELECT id, full_name, email, created_at FROM users;
SELECT * FROM registrations;
SELECT e.title, e.event_date, r.registered_at
FROM registrations r JOIN events e ON e.id = r.event_id
ORDER BY r.registered_at DESC;
```

## 8) Common issues

- **`Access denied for user`**: Check `DB_USER`/`DB_PASSWORD` in `config.py`.
- **`Can't connect to MySQL`**: Make sure MySQL service is running and host/port are correct.
- **`Email already registered`**: Try logging in or use a different email.

## 9) Next steps / ideas

- Add form validations and CSRF protection (Flask-WTF)
- Add event detail pages and cancel registration
- Add admin to create/edit events
- Send confirmation email (Flask-Mail)
- Deploy to a hosting provider
