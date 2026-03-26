from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__, template_folder="../templates", static_folder="../static")

# On définit les identifiants pour les deux types d'utilisateurs
USERS = {
    "Operat": "Operator",
    "Respo": "Responsable",
    "Integ": "Integrator",
    "Admin": "Administrator"
}

@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = request.form.get("username")
        password = request.form.get("password")

        # 1. Vérification si l'utilisateur existe et si le mot de passe est correct
        if user in USERS and USERS[user] == password:
            
            # 2. Redirection selon le rôle (on compare avec les clés du dictionnaire)
            if user == "Respo":
                return redirect(url_for("dashboard_resp"))
            
            elif user == "Integ":
                return redirect(url_for("dashboard_integ"))
            
            elif user == "Operat":
                return redirect(url_for("dashboard_op"))
        
        else:
            error = "Identifiants incorrects"

    return render_template("login.html", error=error)

@app.route("/dashboard")
def dashboard_op():
    return render_template("dashboard.html")

@app.route("/responsable")
def dashboard_resp():
    return render_template("dashboard_SB_respo.html")

@app.route("/integrateur")
def dashboard_integ():
    return render_template("dashboard_SB_integ.html")

# --- TOUJOURS À LA FIN DU FICHIER ---
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8180, debug=True)