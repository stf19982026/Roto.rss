# Feed RSS Rotoworld NBA

Crea un feed RSS dalle news di nbcsports.com/fantasy/basketball/player-news,
aggiornato ogni 10 minuti gratis tramite GitHub. Lo leggi su Android con un
lettore RSS che manda le notifiche.

## Setup (una volta sola, ~10 minuti)

1. Crea un account su github.com (gratis).
2. Crea un nuovo repository **pubblico**, ad esempio `rotoworld-rss`.
3. Carica tutti i file di questa cartella (Add file → Upload files), compresa
   la cartella `.github/workflows/`.
   Se l'upload web salta la cartella nascosta `.github`: Add file → Create new
   file, nome `.github/workflows/feed.yml`, e incolla il contenuto del file.
4. Settings → Actions → General → "Workflow permissions": scegli
   **Read and write permissions** → Save.
5. Tab **Actions** → "Aggiorna feed Rotoworld NBA" → **Run workflow**.
   Dopo ~1 minuto deve comparire la cartella `docs/` con `feed.xml`.
6. Settings → Pages → Source: **Deploy from a branch**, branch `main`,
   cartella `/docs` → Save.

Il feed sarà a:

    https://<tuo-utente>.github.io/rotoworld-rss/feed.xml        (tutte le news)
    https://<tuo-utente>.github.io/rotoworld-rss/feed-miei.xml   (solo i tuoi giocatori)

## Su Android

Installa **Feeder** (gratis, open source) dal Play Store, poi:
- "+" → incolla l'URL del feed
- nelle impostazioni del feed attiva **Notifiche**
- Impostazioni → sincronizzazione ogni 15 minuti

In alternativa vanno bene Inoreader o Feedly.

## I tuoi giocatori

Modifica `players.txt` direttamente su GitHub (un nome per riga, anche
parziale: "Wembanyama" basta). Al giro successivo `feed-miei.xml` si aggiorna.
Iscrivendoti solo a quel feed ricevi notifiche solo sulla tua rosa.

## Note

- GitHub può ritardare i job programmati di qualche minuto nelle ore di punta.
- Se un giorno il feed smette di aggiornarsi, guarda il tab Actions: un errore
  "nessuna news trovata" vuol dire che NBC ha cambiato la pagina e lo script
  va adattato.
- Uso personale: il feed riprende contenuti di NBC Sports/Rotoworld.
