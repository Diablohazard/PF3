from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__, template_folder="../templates", static_folder="../static")

# La secret_key est indispensable pour utiliser les sessions. 
# Elle sert à signer cryptographiquement le cookie de session pour que l'utilisateur 
# ne puisse pas modifier ses données de connexion lui-même.
app.secret_key = "une_cle_secrete_tres_longue" 

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
            # Si l'identifiant et le mot de passe sont corrects, 
            # on enregistre dans la session que l'utilisateur est connecté.
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            error = "Identifiants incorrects"

    return render_template("login.html", error=error)


@app.route("/dashboard")
def dashboard():
    # Vérification de sécurité : on regarde dans la session si l'utilisateur est passé par la page de login.
    # Si 'logged_in' n'existe pas ou vaut False, on redirige vers l'accueil.
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("dashboard.html")



# Route pour la page d'administration
@app.route("/admin", methods=["GET", "POST"])
def admin():
    return render_template("admin.html")


# Route pour créer un nouvel utilisateur (pour l'instant, on enregistre dans un fichier)
@app.route("/create_user", methods=["POST"])
def create_user():
    username = request.form["new_username"]
    password = request.form["new_password"]

    # pour l'instant on enregistre dans un fichier
    with open("users.txt", "a") as f:
        f.write(f"{username}:{password}\n")

    return render_template("admin.html", message="Utilisateur créé avec succès !")



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8180, debug=True)
