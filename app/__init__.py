# Questo file configura e avvia Flask.
# Viene eseguito automaticamente quando Python
# importa la cartella "app".

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# Creiamo gli oggetti database e login_manager.
# Per ora sono "vuoti" — vengono collegati all'app
# dentro la funzione create_app() qui sotto.
db            = SQLAlchemy()
login_manager = LoginManager()


def create_app():

    app = Flask(__name__)

    app.config['SECRET_KEY'] = 'winp-chiave-segreta'

    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    app.config['SQLALCHEMY_DATABASE_URI'] = \
        'sqlite:///' + os.path.join(basedir, 'database', 'winp.db')

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    with app.app_context():

        # IMPORTANTE: i modelli vanno importati QUI DENTRO
        # prima di chiamare create_all().
        # Solo così SQLAlchemy sa quali tabelle creare.
        from app import models

        # Crea tutte le tabelle nel database
        db.create_all()

        # Inserisce i dati iniziali
        from app.init_db import inizializza_db
        inizializza_db()

        # Registra le route
        from app.routes import main as main_blueprint
        app.register_blueprint(main_blueprint)

    return app


# Flask-Login chiama questa funzione ad ogni richiesta
# per sapere chi è l'utente loggato.
# Riceve l'ID dalla sessione e restituisce l'oggetto utente.
@login_manager.user_loader
def load_user(user_id):
    from app.models import Utente
    return Utente.query.get(int(user_id))