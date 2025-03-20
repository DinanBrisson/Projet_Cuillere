from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, SubmitField, DateField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange

# Formulaire d'inscription pour les nouveaux utilisateurs
class RegistrationForm(FlaskForm):
    firstname = StringField('Prénom', validators=[DataRequired(), Length(min=2, max=150)])  # Champ prénom (obligatoire)
    lastname = StringField('Nom', validators=[DataRequired(), Length(min=2, max=150)])  # Champ nom (obligatoire)
    profession = StringField('Profession', validators=[DataRequired(), Length(min=2, max=150)])  # Profession (obligatoire)
    birthdate = DateField('Date de naissance', format='%Y-%m-%d', validators=[DataRequired()])  # Date de naissance (obligatoire)
    email = StringField('Email', validators=[DataRequired()])  # Email (obligatoire)
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])  # Mot de passe (min. 6 caractères)
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[DataRequired(), EqualTo('password', message="Les mots de passe ne correspondent pas")])  # Confirmation du mot de passe (doit correspondre au champ précédent)
    submit = SubmitField("S'inscrire")  # Bouton de soumission

# Formulaire de connexion pour les utilisateurs existants
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])  # Email (obligatoire)
    password = PasswordField('Mot de passe', validators=[DataRequired()])  # Mot de passe (obligatoire)
    submit = SubmitField('Se connecter')  # Bouton de connexion

# Formulaire de mise à jour du profil utilisateur
class ProfileUpdateForm(FlaskForm):
    firstname = StringField('Prénom', validators=[DataRequired()])  # Nouveau prénom
    lastname = StringField('Nom', validators=[DataRequired()])  # Nouveau nom
    profession = StringField('Profession', validators=[DataRequired()])  # Nouvelle profession
    email = StringField('Email', validators=[DataRequired()])  # Nouvel email
    submit = SubmitField('Mettre à jour')  # Bouton de mise à jour
