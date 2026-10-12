# AnyPS5 → Discord : notifications de progression

Ce petit dépôt vérifie `https://boykopovar.github.io/AnyPS5/progress.json` une fois par heure avec GitHub Actions, sans PC allumé.

## Installation

1. Sur GitHub, crée un dépôt **public ou privé** nommé par exemple `anyps5-discord-monitor`.
2. Envoie dans ce dépôt les fichiers de cette archive en conservant leur arborescence :
   - `monitor.py`
   - `.github/workflows/watch.yml`
   - `state/` (le dossier peut être vide au départ)
3. Dans le dépôt, ouvre **Settings → Secrets and variables → Actions → New repository secret**.
   - Name : `DISCORD_WEBHOOK_URL`
   - Secret : colle l'URL du webhook Discord que tu as créée dans **Paramètres du serveur → Intégrations → Webhooks**.
4. Dans **Settings → Actions → General → Workflow permissions**, vérifie que l'accès en écriture est autorisé (« Read and write permissions »). Le workflow en a besoin pour enregistrer le dernier état.
5. Ouvre l'onglet **Actions**, sélectionne **AnyPS5 progress watcher**, puis **Run workflow** pour faire le premier contrôle.

## Fonctionnement

- Le premier lancement enregistre les statistiques actuelles sans envoyer de notification.
- Ensuite, une notification Discord est envoyée seulement si les nombres de progression changent (valeurs `done`, `todo`, `total` ou `percent`, y compris par bibliothèque).
- Le nouvel état est enregistré dans `state/stats.json` dans le dépôt.
- Le workflow tourne toutes les heures à la minute 17 UTC. GitHub peut démarrer les tâches planifiées avec du retard ; ce n'est pas une garantie à la minute près.

## Sécurité

Ne publie jamais l'URL du webhook dans le code, un commit ou une capture d'écran. Mets-la uniquement dans le secret GitHub `DISCORD_WEBHOOK_URL`. Si elle fuite, supprime ou régénère le webhook dans Discord.

## Dépannage

- Si rien ne se passe au premier lancement, c'est normal : il initialise l'état.
- Pour tester une notification, attends qu'une statistique du site change ; le lancement manuel seul ne crée pas de notification.
- Dans **Actions**, ouvre l'exécution concernée pour consulter les logs en cas d'erreur.
- Si `git push` échoue, vérifie **Settings → Actions → General → Workflow permissions → Read and write permissions**.
