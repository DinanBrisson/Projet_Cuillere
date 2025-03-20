from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Initialisation de l'objet SQLAlchemy pour gérer la base de données
db = SQLAlchemy()


# Définition du modèle User (table utilisateur)
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(150), nullable=False)  # Prénom (obligatoire)
    lastname = db.Column(db.String(150), nullable=False)  # Nom (obligatoire)
    profession = db.Column(db.String(150), nullable=False)  # Profession (obligatoire)
    birthdate = db.Column(db.Date, nullable=False)  # Date de naissance (obligatoire)

    # Informations de connexion
    email = db.Column(db.String(150), unique=True, nullable=False)  # Email unique (obligatoire)
    password_hash = db.Column(db.String(256), nullable=False)  # Mot de passe haché (obligatoire)

    # Définition du rôle de l'utilisateur
    is_admin = db.Column(db.Boolean, default=False)

    # Méthode pour définir un mot de passe (haché pour la sécurité)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Méthode pour vérifier si un mot de passe entré correspond au haché stocké
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


