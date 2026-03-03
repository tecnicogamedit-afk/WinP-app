# Questo file descrive la struttura del database.
# Ogni classe qui sotto corrisponde a una tabella.
# SQLAlchemy si occupa di creare le tabelle automaticamente —
# non dobbiamo scrivere nemmeno una riga di SQL.
#
# Analogia con Excel:
#   Classe  = foglio Excel
#   Colonna = intestazione di colonna
#   Riga    = un record (una commessa, un utente, ecc.)

from datetime import datetime
from app import db
from flask_login import UserMixin


# ════════════════════════════════════════════════════════════
# TABELLA UTENTI
# ════════════════════════════════════════════════════════════
# Contiene tutti gli utenti del sistema.
# UserMixin aggiunge automaticamente i metodi che
# Flask-Login richiede (is_authenticated, is_active, ecc.)

class Utente(db.Model, UserMixin):
    __tablename__ = 'utenti'

    id        = db.Column(db.Integer, primary_key=True)
    # primary_key=True significa che questo campo identifica
    # univocamente ogni riga — come l'ID commessa in Excel

    nome      = db.Column(db.String(100), nullable=False)
    # String(100) = testo fino a 100 caratteri
    # nullable=False = campo obbligatorio, non può essere vuoto

    reparto   = db.Column(db.String(50), nullable=False)
    # Es. "Commerciale", "Tecnico", "Grafica" ecc.

    is_admin  = db.Column(db.Boolean, default=False)
    # Boolean = vero/falso
    # default=False = per default non è admin

    attivo    = db.Column(db.Boolean, default=True)
    # Permette di disattivare un utente senza cancellarlo

    creato_il = db.Column(db.DateTime, default=datetime.utcnow)
    # DateTime = data e ora
    # default=datetime.utcnow = viene impostato automaticamente
    # al momento della creazione

    def __repr__(self):
        # Questo metodo decide come viene mostrato l'oggetto
        # quando lo stampi — utile per il debug
        return f'<Utente {self.nome} — {self.reparto}>'


# ════════════════════════════════════════════════════════════
# TABELLA COMMESSE
# ════════════════════════════════════════════════════════════
# Tabella principale del sistema.
# Ogni riga è una versione di una commessa.
#
# Come funziona la storicizzazione:
#   Versione 1: stato_record = 'ATTIVO'   ← versione corrente
#   Dopo modifica:
#   Versione 1: stato_record = 'MODIFICATO' ← storico
#   Versione 2: stato_record = 'ATTIVO'     ← nuova corrente

class Commessa(db.Model):
    __tablename__ = 'commesse'

    # ── Campi di sistema ──────────────────────────────────────
    # Gestiti automaticamente dal codice, non dall'utente

    id              = db.Column(db.Integer, primary_key=True)

    id_commessa     = db.Column(db.String(20), nullable=False, index=True)
    # index=True = crea un indice su questo campo per
    # rendere le ricerche più veloci
    # Es. "2504001" = anno 25, mese 04, progressivo 001

    versione        = db.Column(db.Integer, default=1)
    # Parte da 1 e aumenta ad ogni modifica storicizzata

    stato_record    = db.Column(db.String(20), default='ATTIVO')
    # ATTIVO = versione corrente
    # MODIFICATO = versione precedente conservata
    # ANNULLATO = commessa annullata

    stato_globale   = db.Column(db.String(20), default='VERDE')
    # VERDE / GIALLO / ROSSO — calcolato automaticamente

    creata_il       = db.Column(db.DateTime, default=datetime.utcnow)

    ultima_modifica = db.Column(db.DateTime, default=datetime.utcnow,
                                onupdate=datetime.utcnow)
    # onupdate = si aggiorna automaticamente ad ogni modifica

    modificata_da   = db.Column(db.String(100))
    # Nome dell'utente che ha fatto l'ultima modifica

    # ── Override manuale stato globale ────────────────────────
    # Solo l'admin può forzare manualmente lo stato globale
    override_flag   = db.Column(db.Boolean, default=False)
    override_da     = db.Column(db.String(100))
    override_data   = db.Column(db.DateTime)

    # ── Zona Commerciale ──────────────────────────────────────
    # Campi compilati dal reparto Commerciale

    data_richiesta  = db.Column(db.Date)
    # Date = solo data, senza ora (diverso da DateTime)

    cliente         = db.Column(db.String(200))
    descrizione     = db.Column(db.Text)
    # Text = testo di lunghezza illimitata (diverso da String)

    data_consegna   = db.Column(db.Date)
    # Data consegna richiesta dal cliente

    priorita        = db.Column(db.String(20))
    # Urgente / ASAP / Appena possibile
    # Si azzera automaticamente quando il Tecnico
    # inserisce il Riscontro

    note_co         = db.Column(db.Text)
    responsabile    = db.Column(db.String(100))

    # ── Zona Tecnico ──────────────────────────────────────────
    # Campi compilati dal reparto Tecnico

    num_preventivo  = db.Column(db.String(50))
    data_quotazione = db.Column(db.Date)
    riscontro       = db.Column(db.String(50))
    # Confermata / Non confermata / Variante
    num_commessa    = db.Column(db.String(50))
    data_tassativa  = db.Column(db.Date)

    # ── Stati reparti ─────────────────────────────────────────
    # Ogni reparto ha tre campi:
    #   stato     = lo stato attuale del lavoro
    #   note_rep  = note interne del reparto
    #   operatore = chi sta lavorando su questa commessa

    # Commerciale
    stato_co      = db.Column(db.String(50), default='Da quotare')
    note_rep_co   = db.Column(db.Text)
    operatore_co  = db.Column(db.String(100))

    # Grafica
    stato_gr      = db.Column(db.String(50), default='In attesa file')
    note_rep_gr   = db.Column(db.Text)
    operatore_gr  = db.Column(db.String(100))

    # Stampa/Produzione
    stato_st      = db.Column(db.String(50), default='In attesa')
    note_rep_st   = db.Column(db.Text)
    operatore_st  = db.Column(db.String(100))

    # Legatoria
    stato_le      = db.Column(db.String(50), default='In attesa')
    note_rep_le   = db.Column(db.Text)
    operatore_le  = db.Column(db.String(100))

    # Lavorazioni esterne
    stato_ex      = db.Column(db.String(50), default='N/A')
    note_rep_ex   = db.Column(db.Text)
    operatore_ex  = db.Column(db.String(100))

    # Logistica
    stato_lg      = db.Column(db.String(50), default='In attesa')
    note_rep_lg   = db.Column(db.Text)
    operatore_lg  = db.Column(db.String(100))

    # ── Lavorazioni esterne ───────────────────────────────────
    lav_est_attiva = db.Column(db.Boolean, default=False)
    lav_est_numero = db.Column(db.Integer, default=0)
    lav_est_stato  = db.Column(db.String(50))

    # ── Modalità consegna ─────────────────────────────────────
    modalita_cons  = db.Column(db.String(50))

    def __repr__(self):
        return f'<Commessa {self.id_commessa} v{self.versione}>'

    def calcola_stato_globale(self, giorni_scadenza=3, giorni_inattivita=7):
        # Calcola automaticamente VERDE/GIALLO/ROSSO
        # in base alle regole definite.
        # Chiamato dopo ogni salvataggio.

        # Se c'è un override manuale dell'admin non ricalcola
        if self.override_flag:
            return self.stato_globale

        oggi = datetime.utcnow().date()

        # ── Regole ROSSE — priorità massima ───────────────────
        # Basta che anche un solo reparto sia bloccato
        stati = [self.stato_co, self.stato_gr, self.stato_st,
                 self.stato_le, self.stato_ex, self.stato_lg]
        if 'Bloccato' in stati:
            return 'ROSSO'

        # Data tassativa superata e non ancora consegnato
        if self.data_tassativa:
            if self.data_tassativa < oggi and \
               self.stato_lg not in ('Consegnato', 'In deposito'):
                return 'ROSSO'

        # ── Regole GIALLE — priorità media ────────────────────
        # Scadenza entro N giorni
        if self.data_tassativa:
            giorni_mancanti = (self.data_tassativa - oggi).days
            if 0 <= giorni_mancanti <= giorni_scadenza:
                return 'GIALLO'

        # Lavorazione esterna in ritardo
        if self.stato_ex == 'In ritardo':
            return 'GIALLO'

        # Nessuna modifica da troppi giorni
        if self.ultima_modifica:
            giorni_inatt = (datetime.utcnow() - self.ultima_modifica).days
            if giorni_inatt > giorni_inattivita and \
               self.stato_lg not in ('Consegnato', 'In deposito'):
                return 'GIALLO'

        # ── Verde — tutto ok ──────────────────────────────────
        return 'VERDE'


# ════════════════════════════════════════════════════════════
# TABELLA LOG AZIONI
# ════════════════════════════════════════════════════════════
# Registra ogni operazione importante nel sistema.
# Equivalente del foglio LOG_ERRORI in Excel, ma più completo.

class LogAzione(db.Model):
    __tablename__ = 'log_azioni'

    id          = db.Column(db.Integer, primary_key=True)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow)
    utente      = db.Column(db.String(100))
    azione      = db.Column(db.String(100))
    # Es. 'CREA', 'MODIFICA', 'ANNULLA', 'LOGIN'
    id_commessa = db.Column(db.String(20))
    dettaglio   = db.Column(db.Text)

    def __repr__(self):
        return f'<Log {self.azione} {self.id_commessa}>'


# ════════════════════════════════════════════════════════════
# TABELLA CONFIGURAZIONE
# ════════════════════════════════════════════════════════════
# Parametri operativi modificabili dall'admin.
# Equivalente del foglio TEMPLATE in Excel.
# Formato chiave-valore: ogni riga è un parametro.

class Configurazione(db.Model):
    __tablename__ = 'configurazione'

    id          = db.Column(db.Integer, primary_key=True)
    chiave      = db.Column(db.String(100), unique=True, nullable=False)
    # unique=True = non possono esistere due righe con la stessa chiave
    valore      = db.Column(db.String(200))
    descrizione = db.Column(db.String(300))

    def __repr__(self):
        return f'<Config {self.chiave} = {self.valore}>'