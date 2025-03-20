from App.app import app, db

# Initialisation de toutes les tables définies par les modèles SQLAlchemy dans la base de données
with app.app_context():
    db.create_all()
    print("Base de données initialisée.")
