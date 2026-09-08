# ELIM Backend — Production architecture (Supabase + Cloudflare R2)

Backend FastAPI pour l'application ELIM (Benin/Nigeria).

## Architecture
- **FastAPI/Uvicorn**: API, RBAC, WebSocket, administration.
- **Supabase PostgreSQL**: uniquement les données structurées et métadonnées.
- **Cloudflare R2 Standard**: PDF, Excel, Word, photos, logos, audio, vidéo, documents et pièces jointes.
- **Firebase Authentication**: identité téléphone/OTP et e-mail (l'application Android obtient un Firebase ID token, envoyé à `/api/v1/auth/firebase`).
- Aucun stockage de fichiers local dans le serveur API.
- Redis n'est pas obligatoire dans cette version : on garde l'architecture gratuite minimale.

## Déploiement gratuit de départ
Pour les tests, l'API peut être déployée sur **Render Free**. Attention : Render indique que ses instances Free ne sont pas destinées à la production et qu'elles s'endorment après 15 min d'inactivité. Ne stockez donc aucun fichier sur le disque local du service.

## 1. Supabase
Créer un projet Free et récupérer la chaîne PostgreSQL directe (Settings > Database > Connection string). Mettre la chaîne dans `DATABASE_URL`.

## 2. Cloudflare R2
Créer un bucket `elim-media`, une API Token R2 avec accès limité à ce bucket, puis renseigner :
- `R2_ENDPOINT=https://<ACCOUNT_ID>.r2.cloudflarestorage.com`
- `R2_BUCKET=elim-media`
- `R2_ACCESS_KEY_ID=...`
- `R2_SECRET_ACCESS_KEY=...`
- `R2_PUBLIC_BASE_URL` seulement si vous configurez un domaine public/custom pour les objets. Sinon les URLs de lecture sont présignées.

Le backend utilise des **presigned URLs** : l'application Android envoie directement le fichier vers R2 sans faire transiter la vidéo/PDF par Render.

## 3. Firebase
Configurer Firebase Authentication (Phone + Email/Password). Générer un compte de service Firebase et placer son JSON dans `FIREBASE_CREDENTIALS_JSON` sous forme de JSON sur une seule ligne, ou injecter ce secret depuis votre plateforme.

## 4. Variables
Copier `.env.example` vers `.env` et remplir TOUS les secrets. Ne jamais committer `.env`.

## 5. Lancer localement
```bash
docker compose up -d --build
```
Puis : `http://localhost:8000/docs`.

## 6. Render
- New Web Service > connecter le dépôt GitHub.
- Runtime: Docker.
- Port: `8000`.
- Ajouter les variables du `.env` dans Environment.
- Health check: `/health`.

## 7. Sécurité
- Changer immédiatement `JWT_SECRET` et `ADMIN_PASSWORD`.
- Restreindre `CORS_ORIGINS` aux domaines réels.
- Ne jamais mettre les clés R2 ou le compte de service Firebase dans l'APK.
- Utiliser HTTPS.
- Les gros fichiers sont envoyés directement vers R2 avec des URLs temporaires.

## Rôles
`member`, `registration_agent`, `group_leader`, `church_leader`, `regional_admin`, `national_admin`, `super_admin`.

## Administration de l'identité visuelle
Le Super Admin peut modifier via `/api/v1/admin/config` : nom, slogan, logo, favicon, image d'accueil, couleurs, langue par défaut et coordonnées. Les images/logos sont d'abord uploadés dans R2, puis leur URL est enregistrée dans `app_settings`. L'application récupère `/api/v1/config/public` pour appliquer les changements sans nouvelle APK.
