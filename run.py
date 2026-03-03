# Questo è il file che avvia il server.
# Quando lo esegui dal Terminale con "python3 run.py"
# parte il server e puoi aprire il browser su localhost:5000

from app import create_app

app = create_app()

if __name__ == '__main__':
    print("Server WinP avviato — apri http://localhost:5000")
    app.run(debug=True, port=5000)