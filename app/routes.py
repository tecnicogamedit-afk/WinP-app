from flask import Blueprint, render_template, request, redirect, url_for, session
from app.models import Utente, Commessa, Configurazione

main = Blueprint('main', __name__)


# ── Login ─────────────────────────────────────────────────────
@main.route('/', methods=['GET', 'POST'])
@main.route('/login', methods=['GET', 'POST'])
def login():

    # Se è già loggato va direttamente alla dashboard
    if 'utente_id' in session:
        return redirect(url_for('main.dashboard'))

    errore = None

    if request.method == 'POST':
        utente_id = request.form.get('utente_id')
        password  = request.form.get('password')

        if not utente_id:
            errore = 'Seleziona il tuo nome per accedere.'
        else:
            utente = Utente.query.get(int(utente_id))

            if not utente:
                errore = 'Utente non trovato.'
            else:
                session['utente_id']   = utente.id
                session['utente_nome'] = utente.nome
                session['reparto']     = utente.reparto
                session['is_admin']    = utente.is_admin

                if password:
                    cfg = Configurazione.query.filter_by(
                          chiave='password_admin').first()
                    pwd_corretta = cfg.valore if cfg else 'WinP2025'

                    if password == pwd_corretta:
                        session['is_admin'] = True
                        session['reparto']  = 'Amministratore'
                    else:
                        errore = 'Password non corretta. ' \
                                 'Accesso come: ' + utente.reparto

                if not errore:
                    return redirect(url_for('main.dashboard'))

    utenti = Utente.query.filter_by(attivo=True).order_by(Utente.nome).all()
    return render_template('login.html', utenti=utenti, errore=errore)


# ── Logout ────────────────────────────────────────────────────
@main.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))


# ── Dashboard ─────────────────────────────────────────────────
@main.route('/dashboard')
def dashboard():

    # Protegge la pagina — se non loggato rimanda al login
    if 'utente_id' not in session:
        return redirect(url_for('main.login'))

    # Carica solo le commesse attive
    commesse = Commessa.query.filter_by(
        stato_record='ATTIVO'
    ).order_by(Commessa.ultima_modifica.desc()).all()

    # Calcola i contatori per il semaforo
    contatori = {
        'rosso':  sum(1 for c in commesse if c.stato_globale == 'ROSSO'),
        'giallo': sum(1 for c in commesse if c.stato_globale == 'GIALLO'),
        'verde':  sum(1 for c in commesse if c.stato_globale == 'VERDE'),
        'totale': len(commesse)
    }

    return render_template('dashboard.html',
                           commesse=commesse,
                           contatori=contatori)