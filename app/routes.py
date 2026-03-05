from flask import Blueprint, render_template, request, redirect, url_for, session
from app.models import Utente, Commessa, Configurazione

main = Blueprint('main', __name__)


# ── Login ─────────────────────────────────────────────────────
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
                pwd_admin = cfg_admin.valore if cfg_admin else 'WinP2025'
                pwd_avanz = cfg_avanz.valore if cfg_avanz else 'WinP2025'

                if utente.is_admin:
                    # Account Amministratore — richiede sempre password
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
                    # Utenti normali — mai admin
                    session['utente_id']   = utente.id
                    session['utente_nome'] = utente.nome
                    session['reparto']     = utente.reparto
                    session['is_admin']    = False
                    if password == pwd_avanz:
                        session['livello'] = 'avanzato'
                    else:
                        session['livello'] = 'base'

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

    if 'utente_id' not in session:
        return redirect(url_for('main.login'))

    commesse = Commessa.query.filter_by(
        stato_record='ATTIVO'
    ).order_by(Commessa.ultima_modifica.desc()).all()

    contatori = {
        'rosso':  sum(1 for c in commesse if c.stato_globale == 'ROSSO'),
        'giallo': sum(1 for c in commesse if c.stato_globale == 'GIALLO'),
        'verde':  sum(1 for c in commesse if c.stato_globale == 'VERDE'),
        'totale': len(commesse)
    }

    return render_template('dashboard.html',
                           commesse=commesse,
                           contatori=contatori)


# ── Nuova richiesta ───────────────────────────────────────────
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
        data_cons   = request.form.get('data_consegna', '')
        priorita    = request.form.get('priorita', '')
        note_co     = request.form.get('note_co', '').strip()

        if not cliente:
            errore = 'Il campo Cliente è obbligatorio.'
        elif not descrizione:
            errore = 'Il campo Descrizione è obbligatorio.'
        else:
            from datetime import date, datetime

            oggi     = date.today()
            anno     = oggi.strftime('%y')
            mese     = oggi.strftime('%m')
            prefisso = f'{anno}{mese}'

            count       = Commessa.query.filter(Commessa.id_commessa.like(f'{prefisso}%')).count()
            progressivo = str(count + 1).zfill(3)
            id_commessa = f'{prefisso}{progressivo}'

            nuova = Commessa(
                id_commessa    = id_commessa,
                versione       = 1,
                stato_record   = 'ATTIVO',
                stato_globale  = 'VERDE',
                data_richiesta = oggi,
                cliente        = cliente,
                descrizione    = descrizione,
                priorita       = priorita if priorita else None,
                note_co        = note_co if note_co else None,
                stato_co       = 'Da quotare',
                modificata_da  = session.get('utente_nome')
            )

            if data_cons:
                nuova.data_consegna = datetime.strptime(data_cons, '%Y-%m-%d').date()

            from app import db
            db.session.add(nuova)
            db.session.commit()

            return redirect(url_for('main.dashboard'))

        form = request.form

    return render_template('nuova_richiesta.html', errore=errore, form=form)


# ── Dettaglio commessa ────────────────────────────────────────
@main.route('/commessa/<commessa_id>')
def dettaglio_commessa(commessa_id):

    if 'utente_id' not in session:
        return redirect(url_for('main.login'))

    commessa = Commessa.query.filter_by(
        id_commessa  = commessa_id,
        stato_record = 'ATTIVO'
    ).first_or_404()

    return render_template('dettaglio.html', commessa=commessa)


# ── Aggiorna commessa ─────────────────────────────────────────
@main.route('/commessa/<commessa_id>/aggiorna', methods=['POST'])
def aggiorna_commessa(commessa_id):

    if 'utente_id' not in session:
        return redirect(url_for('main.login'))

    from app import db
    from datetime import datetime

    commessa = Commessa.query.filter_by(
        id_commessa  = commessa_id,
        stato_record = 'ATTIVO'
    ).first_or_404()

    sezione = request.form.get('sezione')

    if sezione == 'commerciale' and \
       session.get('reparto') in ['Commerciale', 'Amministratore']:

        commessa.cliente     = request.form.get('cliente', '').strip()
        commessa.descrizione = request.form.get('descrizione', '').strip()
        commessa.note_co     = request.form.get('note_co', '').strip()
        commessa.riscontro   = request.form.get('riscontro', '') or None

        priorita = request.form.get('priorita', '')
        commessa.priorita = priorita if priorita else None

        data_cons = request.form.get('data_consegna', '')
        commessa.data_consegna = datetime.strptime(data_cons, '%Y-%m-%d').date() if data_cons else None

        data_tass = request.form.get('data_tassativa_co', '')
        commessa.data_tassativa = datetime.strptime(data_tass, '%Y-%m-%d').date() if data_tass else None

    elif sezione == 'tecnico' and \
         session.get('reparto') in ['Tecnico', 'Amministratore']:

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


# ── Gestione utenti ───────────────────────────────────────────
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
            errore = 'Il nome è obbligatorio.'
        elif not reparto:
            errore = 'Il reparto è obbligatorio.'
        else:
            esiste = Utente.query.filter_by(nome=nome).first()
            if esiste:
                errore = f'Esiste già un utente con il nome "{nome}".'
            else:
                from app import db
                nuovo = Utente(nome=nome, reparto=reparto,
                               is_admin=is_admin, attivo=True)
                db.session.add(nuovo)
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


# ── Toggle utente ─────────────────────────────────────────────
@main.route('/admin/utenti/<int:utente_id>/toggle', methods=['POST'])
def toggle_utente(utente_id):

    if not session.get('is_admin'):
        return redirect(url_for('main.dashboard'))

    from app import db
    utente = Utente.query.get(utente_id)
    if utente:
        utente.attivo = not utente.attivo
        db.session.commit()

    return redirect(url_for('main.admin_utenti'))


# ── Elimina utente ────────────────────────────────────────────
@main.route('/admin/utenti/<int:utente_id>/elimina', methods=['POST'])
def elimina_utente(utente_id):

    if not session.get('is_admin'):
        return redirect(url_for('main.dashboard'))

    if utente_id == session.get('utente_id'):
        return redirect(url_for('main.admin_utenti'))

    from app import db
    utente = Utente.query.get(utente_id)

    if utente:
        commesse = Commessa.query.filter_by(modificata_da=utente.nome).count()
        if commesse > 0:
            utente.attivo = False
        else:
            db.session.delete(utente)
        db.session.commit()

    return redirect(url_for('main.admin_utenti'))


# ── Elevazione admin temporanea ───────────────────────────────
@main.route('/eleva-admin', methods=['POST'])
def eleva_admin():

    password     = request.form.get('password', '')
    redirect_url = request.form.get('redirect_url', '/')

    cfg_avanz = Configurazione.query.filter_by(chiave='password_avanzato').first()
    pwd_avanz = cfg_avanz.valore if cfg_avanz else 'WinP2025'

    # Il popup eleva SOLO ad avanzato — mai ad amministratore
    # Per diventare amministratore bisogna fare logout e login
    if password == pwd_avanz:
        session['livello'] = 'avanzato'
        session['livello_messaggio'] = 'Accesso avanzato attivato'
    else:
        session['livello_messaggio'] = 'Password non corretta'

    return redirect(redirect_url)


# ── Impostazioni admin ────────────────────────────────────────
@main.route('/admin/impostazioni', methods=['GET', 'POST'])
def admin_impostazioni():

    if not session.get('is_admin'):
        return redirect(url_for('main.dashboard'))

    from app import db
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
