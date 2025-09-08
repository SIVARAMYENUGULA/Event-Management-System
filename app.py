from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# ---------------- DB CONNECTION ----------------
def get_connection():
    return mysql.connector.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )

# ---------------- CONTEXT PROCESSOR ----------------
@app.context_processor
def inject_now():
    """Inject current UTC datetime into templates."""
    return {"now": datetime.utcnow()}

# ---------------- EMAIL HELPER ----------------
def send_registration_email(to_email, full_name):
    """Send congratulatory email on successful registration."""
    try:
        subject = "Registration Successful"
        body = (
            f"Hello {full_name},\n\n"
            "You have successfully registered to the Event Management System.\n"
            "Please login to register for upcoming events.\n\n"
            "- Event Management Team"
        )

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = config.EMAIL_USER
        msg["To"] = to_email

        with smtplib.SMTP(config.EMAIL_HOST, config.EMAIL_PORT) as server:
            server.starttls()
            server.login(config.EMAIL_USER, config.EMAIL_PASS)
            server.sendmail(config.EMAIL_USER, to_email, msg.as_string())

    except Exception as e:
        # Print error but don’t break app if mail fails
        print(f"Error sending registration email: {e}")

# ---------------- FRONTEND ROUTES ----------------
@app.route("/")
def index():
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM events ORDER BY event_date ASC")
        events = cur.fetchall()

        registered_event_ids = []
        if "user_id" in session:
            cur.execute("SELECT event_id FROM registrations WHERE user_id = %s", (session["user_id"],))
            registered_event_ids = [row["event_id"] for row in cur.fetchall()]
    except Error as e:
        events = []
        registered_event_ids = []
        flash(f"Database error: {e}", "error")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

    return render_template("index.html", events=events, registered_event_ids=registered_event_ids)



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not full_name or not email or not password:
            flash("Please fill in all fields.", "error")
            return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))

        pw_hash = generate_password_hash(password)
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s)",
                (full_name, email, pw_hash),
            )
            conn.commit()

            # Send registration email
            send_registration_email(email, full_name)

            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))
        except Error as e:
            if "Duplicate entry" in str(e):
                flash("Email already registered. Please log in.", "error")
                return redirect(url_for("login"))
            flash(f"Database error: {e}", "error")
        finally:
            try:
                cur.close()
                conn.close()
            except:
                pass
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next", "")
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, full_name, email, password_hash FROM users WHERE email=%s", (email,))
            user = cur.fetchone()
            if not user or not check_password_hash(user["password_hash"], password):
                flash("Incorrect email or password.", "error")
                return redirect(url_for("login", next=next_url))

            session["user_id"] = user["id"]
            session["full_name"] = user["full_name"]

            flash(f"Welcome, {user['full_name']}!", "success")
            return redirect(next_url or url_for("index"))
        except Error as e:
            flash(f"Database error: {e}", "error")
        finally:
            try:
                cur.close()
                conn.close()
            except:
                pass
    return render_template("login.html", next=next_url)

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

@app.route("/register_event/<int:event_id>")
def register_event(event_id):
    if not session.get("user_id"):
        flash("Please log in to register for the event. New user? Create an account first.", "info")
        return redirect(url_for("login", next=url_for("register_event", event_id=event_id)))
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM events WHERE id=%s", (event_id,))
        if cur.fetchone()[0] == 0:
            flash("Event not found.", "error")
            return redirect(url_for("index"))
        cur.execute(
            "INSERT IGNORE INTO registrations (user_id, event_id) VALUES (%s, %s)",
            (session["user_id"], event_id),
        )
        conn.commit()
        flash("You are registered for the event!", "success")
    except Error as e:
        flash(f"Database error: {e}", "error")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass
    return redirect(url_for("index"))

# --------- NEW FRONTEND ROUTES FOR UPDATE / CANCEL ---------
@app.route("/cancel_registration/<int:event_id>", methods=["POST"])
def cancel_registration(event_id):
    if not session.get("user_id"):
        return redirect(url_for("login", next=url_for("my_dashboard")))
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM registrations WHERE user_id=%s AND event_id=%s",
            (session["user_id"], event_id),
        )
        conn.commit()
        flash("Registration cancelled successfully.", "success")
    except Error as e:
        flash(f"Database error: {e}", "error")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass
    return redirect(url_for("my_dashboard"))


@app.route("/update_registration/<int:current_event_id>", methods=["GET", "POST"])
def update_registration(current_event_id):
    if not session.get("user_id"):
        return redirect(url_for("login", next=url_for("my_dashboard")))

    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        if request.method == "POST":
            new_event_id = request.form.get("new_event_id")

            if new_event_id:
                # First, check if user already registered for new_event_id
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM registrations WHERE user_id=%s AND event_id=%s",
                    (session["user_id"], new_event_id),
                )
                exists = cur.fetchone()["cnt"]

                if exists:
                    flash("You are already registered for the selected event.", "error")
                else:
                    cur.execute(
                        "UPDATE registrations SET event_id=%s WHERE user_id=%s AND event_id=%s",
                        (new_event_id, session["user_id"], current_event_id),
                    )
                    conn.commit()
                    flash("Registration updated successfully!", "success")
                    return redirect(url_for("my_dashboard"))

        # For GET request, fetch all other events user can switch to
        cur.execute(
            "SELECT id, title, event_date FROM events WHERE id != %s ORDER BY event_date ASC",
            (current_event_id,),
        )
        available_events = cur.fetchall()

    except Error as e:
        available_events = []
        flash(f"Database error: {e}", "error")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

    return render_template(
        "update_registration.html",
        current_event_id=current_event_id,
        events=available_events,
    )



@app.route("/my")
def my_dashboard():
    """Frontend dashboard page for logged-in user."""
    if not session.get("user_id"):
        return redirect(url_for("login", next=url_for("my_dashboard")))

    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT r.event_id, r.registered_at, e.title, e.event_date, e.description
            FROM registrations r
            JOIN events e ON e.id = r.event_id
            WHERE r.user_id=%s
            ORDER BY e.event_date ASC
            """,
            (session["user_id"],),
        )
        regs = cur.fetchall()
    except Error as e:
        regs = []
        flash(f"Database error: {e}", "error")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

    return render_template("dashboard.html", regs=regs)


# ---------------- API ROUTES ----------------
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json() or {}
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")
    confirm = data.get("confirm", "")

    if not full_name or not email or not password:
        return jsonify({"error": "Please fill in all fields."}), 400
    if password != confirm:
        return jsonify({"error": "Passwords do not match."}), 400

    pw_hash = generate_password_hash(password)
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s)",
            (full_name, email, pw_hash),
        )
        conn.commit()

        # Send registration email
        send_registration_email(email, full_name)

        return jsonify({"message": "Registration successful."}), 201
    except Error as e:
        if "Duplicate entry" in str(e):
            return jsonify({"error": "Email already registered."}), 409
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")

    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, full_name, email, password_hash FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Incorrect email or password."}), 401

        session["user_id"] = user["id"]
        session["full_name"] = user["full_name"]

        return jsonify({"message": f"Welcome, {user['full_name']}!"}), 200
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

@app.route("/api/events", methods=["GET"])
def api_events():
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, title, event_date, description FROM events ORDER BY event_date ASC;")
        events = cur.fetchall()
        return jsonify(events), 200
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

@app.route("/api/register_event/<int:event_id>", methods=["POST"])
def api_register_event(event_id):
    if not session.get("user_id"):
        return jsonify({"error": "Login required"}), 401
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM events WHERE id=%s", (event_id,))
        if cur.fetchone()[0] == 0:
            return jsonify({"error": "Event not found"}), 404
        cur.execute(
            "INSERT IGNORE INTO registrations (user_id, event_id) VALUES (%s, %s)",
            (session["user_id"], event_id),
        )
        conn.commit()
        return jsonify({"message": "You are registered for the event!"}), 201
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

@app.route("/api/my", methods=["GET"])
def api_my_dashboard():
    if not session.get("user_id"):
        return jsonify({"error": "Login required"}), 401
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT r.event_id, r.registered_at, e.title, e.event_date, e.description
            FROM registrations r
            JOIN events e ON e.id = r.event_id
            WHERE r.user_id=%s
            ORDER BY e.event_date ASC
            """,
            (session["user_id"],),
        )
        regs = cur.fetchall()
        return jsonify(regs), 200
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass


# --------- NEW API ROUTES FOR UPDATE / CANCEL ---------
@app.route("/api/cancel_registration/<int:event_id>", methods=["DELETE"])
def api_cancel_registration(event_id):
    if not session.get("user_id"):
        return jsonify({"error": "Login required"}), 401
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM registrations WHERE user_id=%s AND event_id=%s",
            (session["user_id"], event_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "No registration found for this event"}), 404
        return jsonify({"message": "Registration cancelled successfully."}), 200
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass


@app.route("/api/update_registration/<int:current_event_id>", methods=["PUT"])
def api_update_registration(current_event_id):
    if not session.get("user_id"):
        return jsonify({"error": "Login required"}), 401

    data = request.get_json() or {}
    new_event_id = data.get("new_event_id")

    if not new_event_id:
        return jsonify({"error": "New event_id is required"}), 400

    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        # Check if new event exists
        cur.execute("SELECT COUNT(*) AS cnt FROM events WHERE id=%s", (new_event_id,))
        if cur.fetchone()["cnt"] == 0:
            return jsonify({"error": "New event not found"}), 404

        # Check if user already registered for the new_event_id
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM registrations WHERE user_id=%s AND event_id=%s",
            (session["user_id"], new_event_id),
        )
        exists = cur.fetchone()["cnt"]

        if exists:
            return jsonify({"error": "You are already registered for this event"}), 409

        # Perform update
        cur.execute(
            "UPDATE registrations SET event_id=%s WHERE user_id=%s AND event_id=%s",
            (new_event_id, session["user_id"], current_event_id),
        )
        conn.commit()

        if cur.rowcount == 0:
            return jsonify({"error": "No existing registration found"}), 404

        return jsonify({"message": "Registration updated successfully."}), 200

    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass



# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("Starting Flask server on http://127.0.0.1:5000")
    app.run(debug=True)
