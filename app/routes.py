# Questo file gestisce le pagine dell'applicazione.
# Ogni funzione corrisponde a una pagina o a un'azione.

from flask import Blueprint, render_template, request, redirect, url_for, session
from app.models import Utente

main = Blueprint('main', __name__)


# ── Pagina login ──────────────────────────────────────────────
# Gestisce sia la visualizzazione (GET) che l'invio (POST)
@main.route('/', methods=['GET', 'POST'])
@main.route('/login', methods=['GET', 'POST'])
def login():

    errore = None

    if request.method == 'POST':
        # L'utente ha cliccato Accedi — legge i dati del form
        utente_id = request.form.get('utente_id')
        password  = request.form.get('password')

        # Verifica che sia stato scelto un utente
        if not utente_id:
            errore = 'Seleziona il tuo nome per accedere.'
        else:
            # Cerca l'utente nel database
            utente = Utente.query.get(int(utente_id))

            if not utente:
                errore = 'Utente non trovato.'
            else:
                # Salva le info utente nella sessione
                # La sessione è come un cookie sicuro —
                # ricorda chi è loggato tra una pagina e l'altra
                session['utente_id']   = utente.id
                session['utente_nome'] = utente.nome
                session['reparto']     = utente.reparto
                session['is_admin']    = utente.is_admin

                # Se ha inserito la password verifica che sia corretta
                if password:
                    from app.models import Configurazione
                    cfg = Configurazione.query.filter_by(
                          chiave='password_admin').first()
                    pwd_corretta = cfg.valore if cfg else 'WinP2025'

                    if password == pwd_corretta:
                        session['is_admin'] = True
                        session['reparto']  = 'Amministratore'
                    else:
                        errore = 'Password non corretta. ' \
                                 'Accesso come: ' + utente.reparto

                # Se non c'è errore vai alla dashboard
                if not errore:
                    return redirect(url_for('main.dashboard'))

    # Carica tutti gli utenti attivi per il menu a tendina
    utenti = Utente.query.filter_by(attivo=True).order_by(Utente.nome).all()

    # render_template carica il file HTML e ci passa i dati
    # {{ utenti }} e {{ errore }} nell'HTML vengono sostituiti
    # con i valori reali
    return render_template('login.html', utenti=utenti, errore=errore)


# ── Dashboard principale ──────────────────────────────────────
# Pagina temporanea — la costruiamo nella prossima sessione
@main.route('/dashboard')
def dashboard():
    if 'utente_id' not in session:
        return redirect(url_for('main.login'))

    nome    = session.get('utente_nome', '')
    reparto = session.get('reparto', '')

    return f'<h1>Benvenuto {nome}</h1><p>Reparto: {reparto}</p>'