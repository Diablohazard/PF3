from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Identifiants
USERNAME = "Operat"
PASSWORD = "Operator"

@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = request.form["username"]
        password = request.form["password"]

        if user == USERNAME and password == PASSWORD:
            return redirect(url_for("dashboard"))
        else:
            error = "Identifiants incorrects"

    return render_template("login.html", error=error)


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


if __name__ == "__main__":
    app.run(debug=True)