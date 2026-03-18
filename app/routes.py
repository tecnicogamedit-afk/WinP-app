# =============================================================
# routes.py — Pagine e logica dell'applicazione
# =============================================================
# Questo file definisce tutte le URL dell'applicazione e
# cosa succede quando un utente le visita.
#
# STRUTTURA:
#   Ogni funzione decorata con @main.route() e' una pagina.
#   Il decoratore specifica l'URL e i metodi HTTP accettati:
#     GET  = l'utente sta visitando la pagina
#     POST = l'utente ha inviato un modulo
#
# PROTEZIONE PAGINE:
#   Ogni pagina protetta controlla 'utente_id' nella sessione.
#   Le pagine admin controllano 'is_admin' nella sessione.
#   Se il controllo fallisce, reindirizza al login/dashboard.
#
# SESSIONE UTENTE (session[]):
#   utente_id    = ID numerico dell'utente loggato
#   utente_nome  = Nome dell'utente (es. 'Wilma')
#   reparto      = Reparto dell'utente (es. 'Commerciale')
#   is_admin     = True se l'utente e' Amministratore
#   livello      = 'base' / 'avanzato' / 'amministratore'
# =============================================================

from flask import Blueprint, render_template, request, redirect, url_for, session
from app.models import Utente, Commessa, Configurazione
from app import db
from datetime import date, datetime

main = Blueprint('main', __name__)


# =============================================================
# LOGIN
# =============================================================
# Accessibile da / e /login
#
# LOGICA DI ACCESSO:
#   Amministratore -> richiede password admin
#   Utente normale -> nessuna password (livello base)
#                  -> password avanzato (livello avanzato)
#
# Le password sono configurabili dal pannello Admin
# senza toccare il codice (tabella Configurazione).
# =============================================================

@main.route('/', methods=['GET', 'POST'])
@main.route('/login', methods=['GET', 'POST'])
def login():

    if 'utente_id' in session:
        return redirect(url_for('main.dashboard'))

    errore = None

    if request.method == 'POST':
        utente_id = request.form.get('utente_id')
        password  = request.form.get('password', '')

        if not utente_id:
            errore = 'Seleziona il tuo nome per accedere.'
        else:
            utente = Utente.query.get(int(utente_id))

            if not utente:
                errore = 'Utente non trovato.'
            elif not utente.attivo:
                errore = 'Utente disattivato. Contatta l\'amministratore.'
            else:
                cfg_admin = Configurazione.query.filter_by(chiave='password_admin').first()
                cfg_avanz = Configurazione.query.filter_by(chiave='password_avanzato').first()
                pwd_admin = cfg_admin.valore if cfg_admin else 'admin'
                pwd_avanz = cfg_avanz.valore if cfg_avanz else 'utente'

                if utente.is_admin:
                    if not password:
                        errore = 'L\'account Amministratore richiede la password.'
                    elif password == pwd_admin:
                        session['utente_id']   = utente.id
                        session['utente_nome'] = utente.nome
                        session['reparto']     = 'Amministratore'
                        session['is_admin']    = True
                        session['livello']     = 'amministratore'
                    else:
                        errore = 'Password non corretta.'
                else:
                    session['utente_id']   = utente.id
                    session['utente_nome'] = utente.nome
                    session['reparto']     = utente.reparto
                    session['is_admin']    = False
                    session['livello']     = 'avanzato' if password == pwd_avanz else 'base'

                if not errore:
                    return redirect(url_for('main.dashboard'))

    utenti = Utente.query.filter_by(attivo=True).order_by(Utente.nome).all()
    return render_template('login.html', utenti=utenti, errore=errore)


# =============================================================
# LOGOUT
# =============================================================

@main.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))


# =============================================================
# DASHBOARD
# =============================================================

@main.route('/dashboard')
def dashboard():

    if 'utente_id' not in session:
        return redirect(url_for('main.login'))

    # Filtra le commesse in base al reparto dell'utente
    # Commerciale e Tecnico vedono tutto
    # Utente avanzato vede tutto
    # Gli altri reparti vedono solo le commesse dove sono coinvolti
    reparto = session.get('reparto')
    livello = session.get('livello')

    query = Commessa.query.filter_by(stato_record='ATTIVO')

    if livello == 'avanzato' or reparto in ['Amministratore', 'Tecnico', 'Commerciale']:
        # Nessun filtro — vede tutto
        pass
    elif reparto == 'Grafica':
        query = query.filter_by(coinvolto_gr=True)
    elif reparto == 'Produzione':
        query = query.filter_by(coinvolto_st=True)
    elif reparto == 'Legatoria':
        query = query.filter_by(coinvolto_le=True)
    elif reparto == 'Logistica':
        query = query.filter_by(coinvolto_lg=True)

    commesse = query.order_by(Commessa.ultima_modifica.desc()).all()

    contatori = {
        'rosso':  sum(1 for c in commesse if c.stato_globale == 'ROSSO'),
        'giallo': sum(1 for c in commesse if c.stato_globale == 'GIALLO'),
        'verde':  sum(1 for c in commesse if c.stato_globale == 'VERDE'),
        'attesa': sum(1 for c in commesse if c.in_attesa),
        'totale': len(commesse)
    }

    return render_template('dashboard.html', commesse=commesse, contatori=contatori)

# =============================================================
# NUOVA RICHIESTA DI QUOTAZIONE
# =============================================================
# Solo Commerciale e Amministratore possono creare richieste.
#
# ID COMMESSA AUTOMATICO:
#   Formato AAMMXXX es. 2603001
#   AA  = anno a 2 cifre
#   MM  = mese a 2 cifre
#   XXX = progressivo del mese a 3 cifre (si azzera ogni mese)
#
# CAMPI OBBLIGATORI: cliente, descrizione
# =============================================================

@main.route('/nuova-richiesta', methods=['GET', 'POST'])
def nuova_richiesta():

    if 'utente_id' not in session:
        return redirect(url_for('main.login'))

    if session.get('reparto') not in ['Commerciale', 'Amministratore']:
        return redirect(url_for('main.dashboard'))

    errore = None
    form   = None

    if request.method == 'POST':
        cliente     = request.form.get('cliente', '').strip()
        descrizione = request.form.get('descrizione', '').strip()
        data_rich   = request.form.get('data_richiesta', '')
        data_cons   = request.form.get('data_consegna', '')
        priorita    = request.form.get('priorita', '')
        note_co     = request.form.get('note_co', '').strip()

        if not cliente:
            errore = 'Il campo Cliente e\' obbligatorio.'
        elif not descrizione:
            errore = 'Il campo Descrizione e\' obbligatorio.'
        elif not data_rich:
            errore = 'Il campo Data richiesta e\' obbligatorio.'
        else:
            # Genera ID commessa automatico formato AAMMXXX
            oggi     = date.today()
            prefisso = oggi.strftime('%y%m')
            count    = Commessa.query.filter(
                Commessa.id_commessa.like(f'{prefisso}%')
            ).count()
            id_commessa = f'{prefisso}{str(count + 1).zfill(3)}'

            nuova = Commessa(
                id_commessa    = id_commessa,
                versione       = 1,
                stato_record   = 'ATTIVO',
                stato_globale  = 'VERDE',
                data_richiesta = datetime.strptime(data_rich, '%Y-%m-%d').date(),
                cliente        = cliente,
                descrizione    = descrizione,
                priorita       = priorita or None,
                note_co        = note_co or None,
                stato_co       = 'Da quotare',
                modificata_da  = session.get('utente_nome')
            )

            if data_cons:
                nuova.data_consegna = datetime.strptime(data_cons, '%Y-%m-%d').date()

            db.session.add(nuova)
            db.session.commit()
            return redirect(url_for('main.dashboard'))

        form = request.form

    return render_template('nuova_richiesta.html', errore=errore, form=form)


# =============================================================
# DETTAGLIO COMMESSA
# =============================================================

@main.route('/commessa/<commessa_id>')
def dettaglio_commessa(commessa_id):

    if 'utente_id' not in session:
        return redirect(url_for('main.login'))

    commessa = Commessa.query.filter_by(
        id_commessa  = commessa_id,
        stato_record = 'ATTIVO'
    ).first_or_404()

    return render_template('dettaglio.html', commessa=commessa)


# =============================================================
# AGGIORNA COMMESSA
# =============================================================
# Riceve i dati dal form del dettaglio e li salva.
#
# SEZIONI DISPONIBILI:
#   'commerciale' -> aggiorna campi zona Commerciale
#   'tecnico'     -> aggiorna campi zona Tecnico
#
# STATO AUTOMATICO:
#   Dopo ogni salvataggio viene ricalcolato stato_globale.
#   Se viene inserito num_commessa, stato_co = 'In lavorazione'.
# =============================================================

@main.route('/commessa/<commessa_id>/aggiorna', methods=['POST'])
def aggiorna_commessa(commessa_id):

    if 'utente_id' not in session:
        return redirect(url_for('main.login'))

    commessa = Commessa.query.filter_by(
        id_commessa  = commessa_id,
        stato_record = 'ATTIVO'
    ).first_or_404()

    sezione = request.form.get('sezione')

    if sezione == 'commerciale' and        session.get('reparto') in ['Commerciale', 'Amministratore']:

        commessa.cliente     = request.form.get('cliente', '').strip()
        commessa.descrizione = request.form.get('descrizione', '').strip()
        commessa.note_co     = request.form.get('note_co', '').strip() or None
        commessa.riscontro   = request.form.get('riscontro', '') or None
        commessa.priorita    = request.form.get('priorita', '') or None

        data_cons = request.form.get('data_consegna', '')
        commessa.data_consegna = datetime.strptime(data_cons, '%Y-%m-%d').date() if data_cons else None

        data_tass = request.form.get('data_tassativa_co', '')
        commessa.data_tassativa = datetime.strptime(data_tass, '%Y-%m-%d').date() if data_tass else None

        data_invio = request.form.get('data_invio_quotazione', '')
        commessa.data_invio_quotazione = datetime.strptime(data_invio, '%Y-%m-%d').date() if data_invio else None

    elif sezione == 'tecnico' and          session.get('reparto') in ['Tecnico', 'Amministratore']:

        commessa.num_preventivo = request.form.get('num_preventivo', '').strip() or None
        commessa.num_commessa   = request.form.get('num_commessa', '').strip() or None

        data_quot = request.form.get('data_quotazione', '')
        commessa.data_quotazione = datetime.strptime(data_quot, '%Y-%m-%d').date() if data_quot else None

        if commessa.num_commessa:
            commessa.stato_co = 'In lavorazione'

    commessa.modificata_da   = session.get('utente_nome')
    commessa.ultima_modifica = datetime.utcnow()
    commessa.stato_globale   = commessa.calcola_stato_globale()

    db.session.commit()
    return redirect(url_for('main.dettaglio_commessa', commessa_id=commessa_id))

# =============================================================
# ADMIN — GESTIONE UTENTI
# =============================================================
# Solo Amministratore.
#
# REGOLE ELIMINAZIONE:
#   - Non si puo' eliminare se stessi
#   - Utenti con commesse associate vengono disattivati
#     invece di eliminati (per preservare lo storico)
# =============================================================

@main.route('/admin/utenti', methods=['GET', 'POST'])
def admin_utenti():

    if not session.get('is_admin'):
        return redirect(url_for('main.dashboard'))

    errore   = None
    successo = None

    if request.method == 'POST':
        nome     = request.form.get('nome', '').strip()
        reparto  = request.form.get('reparto', '').strip()
        is_admin = request.form.get('is_admin') == '1'

        if not nome:
            errore = 'Il nome e\' obbligatorio.'
        elif not reparto:
            errore = 'Il reparto e\' obbligatorio.'
        else:
            esiste = Utente.query.filter_by(nome=nome).first()
            if esiste:
                errore = f'Esiste gia\' un utente con il nome "{nome}".'
            else:
                db.session.add(Utente(
                    nome=nome, reparto=reparto,
                    is_admin=is_admin, attivo=True
                ))
                db.session.commit()
                successo = f'Utente "{nome}" aggiunto con successo.'

    utenti = Utente.query.order_by(Utente.reparto, Utente.nome).all()

    def colore_reparto(reparto):
        colori = {
            'Commerciale':    '#2e5f8a',
            'Tecnico':        '#1a5c6b',
            'Grafica':        '#5b4a6b',
            'Produzione':     '#3a6b4a',
            'Logistica':      '#8a4f2e',
            'Amministratore': '#2e2e50',
        }
        return colori.get(reparto, '#888888')

    return render_template('admin_utenti.html',
                           utenti=utenti,
                           errore=errore,
                           successo=successo,
                           colore_reparto=colore_reparto)


# =============================================================
# ADMIN — ATTIVA/DISATTIVA UTENTE
# =============================================================

@main.route('/admin/utenti/<int:utente_id>/toggle', methods=['POST'])
def toggle_utente(utente_id):

    if not session.get('is_admin'):
        return redirect(url_for('main.dashboard'))

    utente = Utente.query.get(utente_id)
    if utente:
        utente.attivo = not utente.attivo
        db.session.commit()

    return redirect(url_for('main.admin_utenti'))


# =============================================================
# ADMIN — ELIMINA UTENTE
# =============================================================

@main.route('/admin/utenti/<int:utente_id>/elimina', methods=['POST'])
def elimina_utente(utente_id):

    if not session.get('is_admin'):
        return redirect(url_for('main.dashboard'))

    if utente_id == session.get('utente_id'):
        return redirect(url_for('main.admin_utenti'))

    utente = Utente.query.get(utente_id)
    if utente:
        ha_commesse = Commessa.query.filter_by(modificata_da=utente.nome).count() > 0
        if ha_commesse:
            utente.attivo = False
        else:
            db.session.delete(utente)
        db.session.commit()

    return redirect(url_for('main.admin_utenti'))


# =============================================================
# ELEVAZIONE LIVELLO AVANZATO
# =============================================================
# Il popup ingranaggio nella navbar chiama questa route.
# Eleva il livello SOLO ad 'avanzato' — mai ad 'amministratore'.
# Per diventare admin bisogna fare logout e login come admin.
# =============================================================

@main.route('/eleva-admin', methods=['POST'])
def eleva_admin():

    password     = request.form.get('password', '')
    redirect_url = request.form.get('redirect_url', '/')

    cfg_avanz = Configurazione.query.filter_by(chiave='password_avanzato').first()
    pwd_avanz = cfg_avanz.valore if cfg_avanz else 'utente'

    if password == pwd_avanz:
        session['livello'] = 'avanzato'
        session['livello_messaggio'] = 'Accesso avanzato attivato'
    else:
        session['livello_messaggio'] = 'Password non corretta'

    return redirect(redirect_url)


# =============================================================
# ADMIN — IMPOSTAZIONI
# =============================================================
# Permette di cambiare le password di accesso.
# I valori vengono salvati nella tabella Configurazione.
#
# COME AGGIUNGERE UN'IMPOSTAZIONE:
#   1. Aggiungi il campo in admin_impostazioni.html
#   2. Aggiungi la logica di salvataggio qui sotto
#   3. Aggiungi il parametro default in init_db.py
# =============================================================

@main.route('/admin/impostazioni', methods=['GET', 'POST'])
def admin_impostazioni():

    if not session.get('is_admin'):
        return redirect(url_for('main.dashboard'))

    errore   = None
    successo = None

    if request.method == 'POST':
        pwd_admin = request.form.get('password_admin', '').strip()
        pwd_avanz = request.form.get('password_avanzato', '').strip()

        if pwd_admin:
            cfg = Configurazione.query.filter_by(chiave='password_admin').first()
            if cfg:
                cfg.valore = pwd_admin

        if pwd_avanz:
            cfg = Configurazione.query.filter_by(chiave='password_avanzato').first()
            if cfg:
                cfg.valore = pwd_avanz

        db.session.commit()
        successo = 'Impostazioni salvate.'

    cfg_admin = Configurazione.query.filter_by(chiave='password_admin').first()
    cfg_avanz = Configurazione.query.filter_by(chiave='password_avanzato').first()

    return render_template('admin_impostazioni.html',
                           pwd_admin=cfg_admin.valore if cfg_admin else '',
                           pwd_avanz=cfg_avanz.valore if cfg_avanz else '',
                           errore=errore,
                           successo=successo)

# =============================================================
# ADMIN — VISUALIZZAZIONE DATABASE
# =============================================================
# Mostra il contenuto di tutte le tabelle del database.
# Accessibile solo dall'amministratore.
# Organizzata in 4 tab: Commesse, Utenti, Log, Configurazione
#
# NOTA: il log viene limitato alle ultime 200 righe per
# evitare di caricare troppi dati in memoria
# =============================================================

@main.route('/admin/database')
def admin_database():

    # Controllo permessi — solo admin
    if not session.get('is_admin'):
        return redirect(url_for('main.dashboard'))

    from app.models import LogAzione, Configurazione

    # Carica tutte le righe di ogni tabella
    # .order_by() ordina i risultati
    # .desc() = ordine decrescente (dal più recente al più vecchio)
    # .limit(200) = massimo 200 righe per il log
    commesse       = Commessa.query.order_by(Commessa.ultima_modifica.desc()).all()
    utenti         = Utente.query.order_by(Utente.reparto, Utente.nome).all()
    log_azioni     = LogAzione.query.order_by(LogAzione.timestamp.desc()).limit(200).all()
    configurazione = Configurazione.query.order_by(Configurazione.chiave).all()

    # Passa i dati al template admin_database.html
    return render_template('admin_database.html',
                           commesse=commesse,
                           utenti=utenti,
                           log_azioni=log_azioni,
                           configurazione=configurazione)