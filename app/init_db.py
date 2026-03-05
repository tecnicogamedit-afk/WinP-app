# Questo file inserisce i dati iniziali nel database
# al primo avvio del sistema.
#
# Viene chiamato automaticamente da __init__.py
# ogni volta che si avvia il server, ma è scritto
# in modo sicuro: se i dati esistono già non fa nulla.
#
# Cosa inserisce:
#   - Parametri di configurazione di default
#   - Un utente amministratore per il primo accesso

from app import db
from app.models import Utente, Configurazione


def inizializza_db():

    # ── Configurazione di default ─────────────────────────────
    # Lista di parametri nel formato:
    # (chiave, valore, descrizione)
    #
    # La chiave è il nome del parametro — deve essere unica.
    # Il valore è modificabile dall'admin nel pannello impostazioni.

    parametri = [
        (
            'giorni_scadenza',
            '3',
            'Giorni di preavviso prima della scadenza — passa a GIALLO'
        ),
        (
            'giorni_inattivita',
            '7',
            'Giorni senza modifiche prima dell allerta inattività'
        ),
        (
            'soglia_storico',
            '1',
            'Ore entro cui una modifica sovrascrive invece di storicizzare'
        ),
        (
            'password_admin',
            'admin',
            'Password per accesso amministratore — cambiarla subito'
        ),
        (
            'password_avanzato',
            'admin',
            'Password per accesso utente avanzato — cambiarla subito'
        ),

    ]

    # Per ogni parametro controlla se esiste già.
    # Se non esiste lo inserisce, altrimenti non fa nulla.
    for chiave, valore, descrizione in parametri:
        esiste = Configurazione.query.filter_by(chiave=chiave).first()
        if not esiste:
            nuovo = Configurazione(
                chiave      = chiave,
                valore      = valore,
                descrizione = descrizione
            )
            db.session.add(nuovo)

    # ── Utente amministratore di default ─────────────────────
    # Inserisce l'admin solo se non esistono ancora utenti.
    # Così al primo avvio c'è sempre almeno un utente
    # con cui accedere e configurare il sistema.

    if Utente.query.count() == 0:
        admin = Utente(
            nome     = 'Amministratore',
            reparto  = 'Amministratore',
            is_admin = True,
            attivo   = True
        )
        db.session.add(admin)

    # Salva tutte le modifiche nel database.
    # Senza questo commit i dati non vengono scritti.
    db.session.commit()