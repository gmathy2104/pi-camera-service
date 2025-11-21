# Pi Camera Service

Micro-service **FastAPI** production-ready pour contrôler une caméra Raspberry Pi (libcamera / Picamera2)
et diffuser un flux **H.264** vers **MediaMTX** via **RTSP**.

**Version 2.0** - Contrôle avancé de la Camera Module 3, support NoIR optimisé, autofocus, HDR, capture d'images, et bien plus !

> 🆕 **Nouveau en v2.0** : Autofocus, snapshot, AWB manuel, traitement d'image, HDR, ROI, détection jour/nuit, et support NoIR optimisé ! Voir [UPGRADE_v2.md](UPGRADE_v2.md) pour les détails.

---

## 🚀 Démarrage Rapide

```bash
# Installation complète (voir SETUP.md pour les détails)
./install-service.sh

# Tester que tout fonctionne
./test-api.sh

# Accéder au stream RTSP
# VLC: rtsp://<IP_DU_PI>:8554/cam
```

📖 **Documentation complète** : Voir [SETUP.md](SETUP.md) pour l'installation pas à pas.

---

## ✨ Fonctionnalités

Ce service tourne **sur le Raspberry Pi**, prend le contrôle de la caméra (par ex. Raspberry Pi Camera Module v3 Wide NoIR),
et expose une **API HTTP REST** permettant de :

### Core Features (v1.0)
- ✅ Lancer / arrêter le streaming RTSP vers MediaMTX
- ✅ Activer / désactiver l'auto-exposition
- ✅ Passer en exposition manuelle (temps d'expo + gain)
- ✅ Activer / désactiver l'auto white balance (AWB)
- ✅ Récupérer l'état courant de la caméra (lux, expo, gain, température de couleur…)
- ✅ Authentification API par clé (optionnelle)
- ✅ Démarrage automatique au boot (systemd)
- ✅ Tests d'intégration complets

### Advanced Features (v2.0) 🆕
- ✅ **Autofocus Control**: Modes manuel/auto/continuous, position lens manuelle
- ✅ **Snapshot Capture**: Capturer des JPEG sans arrêter le streaming
- ✅ **Manual White Balance**: Gains R/B manuels + presets NoIR optimisés
- ✅ **Image Processing**: Brightness, contrast, saturation, sharpness
- ✅ **HDR Support**: Mode HDR matériel du capteur Camera Module 3
- ✅ **ROI/Digital Zoom**: Crop numérique et zoom sur zones d'intérêt
- ✅ **Exposure Limits**: Contraindre l'auto-exposition (éviter flicker, etc.)
- ✅ **Lens Correction**: Correction de distorsion pour wide-angle (120°)
- ✅ **Day/Night Detection**: Détection automatique du mode jour/nuit
- ✅ **NoIR Optimization**: Auto-détection des tuning files NoIR
- ✅ **Enhanced Metadata**: Focus position, scene mode, HDR status, etc.

Le flux vidéo est publié vers MediaMTX, qui se charge ensuite de le servir
en **RTSP / WebRTC / HLS**, etc.

---

## 📐 Architecture

```
Pi Camera v3  ──>  Picamera2 / libcamera  ──>  H.264 encoder  ──>  MediaMTX (RTSP, WebRTC, HLS...)
                         ▲                         ▲
                         │                         │
                  Pi Camera Service API (FastAPI)  │
                         ▲                         │
                   App externe (backend, UI...) ───┘
```

**Composants** :
- **Pi Camera Service** : ce projet, tournant sur le Pi
- **Picamera2** : librairie Python pour piloter libcamera
- **MediaMTX** : serveur de streaming multiprotocole
- **Application externe** : consomme le flux via MediaMTX et pilote la caméra via HTTP

**Technologies** :
- FastAPI avec lifespan context manager moderne
- Pydantic BaseSettings pour configuration type-safe
- Threading avec RLock pour thread-safety
- Logging structuré
- Tests pytest + tests d'intégration

---

## 📋 Prérequis

### Matériel
- Raspberry Pi (Pi 4 ou Pi 5 recommandé pour l'encodage H.264)
- Caméra compatible libcamera (ex: Raspberry Pi Camera Module v3)

### Logiciel
- Raspberry Pi OS (Bookworm ou plus récent)
- Python 3.9+
- MediaMTX installé et configuré

---

## 📦 Installation

### Installation Rapide

Suivez le guide complet dans [SETUP.md](SETUP.md) :

```bash
# 1. Installer les dépendances système
sudo apt update
sudo apt install -y python3-venv python3-picamera2 python3-libcamera libcamera-apps ffmpeg git

# 2. Cloner le projet
git clone <votre-repo-url> ~/pi-camera-service
cd ~/pi-camera-service

# 3. Créer l'environnement virtuel (IMPORTANT: avec --system-site-packages)
python3 -m venv --system-site-packages venv
source venv/bin/activate

# 4. Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt

# 5. Installer le service systemd
./install-service.sh
```

> **⚠️ Important** : L'environnement virtuel DOIT être créé avec `--system-site-packages`
> pour accéder à picamera2 qui est installé via APT.

---

## ⚙️ Configuration

### Variables d'Environnement

Le service utilise des variables d'environnement avec le préfixe `CAMERA_`.

Créer un fichier `.env` (optionnel) :

```bash
cp .env.example .env
nano .env
```

**Principales variables** :

```bash
# Résolution et qualité vidéo
CAMERA_WIDTH=1920
CAMERA_HEIGHT=1080
CAMERA_FRAMERATE=30
CAMERA_BITRATE=8000000

# Serveur API
CAMERA_HOST=0.0.0.0
CAMERA_PORT=8000

# Authentification (optionnelle)
CAMERA_API_KEY=votre-clé-secrète

# URL RTSP MediaMTX
CAMERA_RTSP_URL=rtsp://127.0.0.1:8554/cam

# Logging
CAMERA_LOG_LEVEL=INFO
```

### Configuration MediaMTX

Dans `mediamtx.yml`, déclarer le path `cam` comme **publisher** :

```yaml
paths:
  cam:
    source: publisher
```

> ⚠️ **Ne PAS utiliser** `source: rpiCamera` (conflit avec ce service)

---

## 🚀 Utilisation

### Démarrage Manuel

```bash
cd ~/pi-camera-service
source venv/bin/activate
python main.py
```

L'API sera disponible sur `http://0.0.0.0:8000`

### Service Systemd (Production)

```bash
# Démarrer
sudo systemctl start pi-camera-service

# Arrêter
sudo systemctl stop pi-camera-service

# Redémarrer
sudo systemctl restart pi-camera-service

# Voir les logs
sudo journalctl -u pi-camera-service -f
```

📖 Voir [SERVICE-SETUP.md](SERVICE-SETUP.md) pour la documentation complète du service.

---

## 📡 API HTTP - Endpoints

**Base URL** : `http://<IP_DU_PI>:8000`

### Santé du Service

**GET** `/health`
```json
{
  "status": "healthy",
  "camera_configured": true,
  "streaming_active": true,
  "version": "1.0.0"
}
```

### Statut de la Caméra

**GET** `/v1/camera/status`
```json
{
  "lux": 45.2,
  "exposure_us": 12000,
  "analogue_gain": 1.5,
  "colour_temperature": 4200.0,
  "auto_exposure": true,
  "streaming": true
}
```

### Contrôle de l'Exposition

**POST** `/v1/camera/auto_exposure`
```json
{"enabled": true}
```

**POST** `/v1/camera/manual_exposure`
```json
{
  "exposure_us": 20000,
  "gain": 2.0
}
```

### Balance des Blancs

**POST** `/v1/camera/awb`
```json
{"enabled": false}
```

### Contrôle du Streaming

**POST** `/v1/streaming/start`
**POST** `/v1/streaming/stop`

📖 **Documentation API complète** : Voir [API.md](API.md)

---

## 🧪 Tests

### Tests d'Intégration API

Vérifier que tout fonctionne correctement :

```bash
# Le service doit être démarré
./test-api.sh
```

**Sortie attendue** :
```
✓ All tests passed! Your Pi Camera Service is working correctly.
```

### Tous les Tests

```bash
# Tests unitaires
pytest tests/ --ignore=tests/test_api_integration.py

# Tests d'intégration (service doit tourner)
pytest tests/test_api_integration.py -v

# Tous les tests
pytest tests/ -v
```

📖 Voir [TESTING.md](TESTING.md) pour le guide complet des tests.

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [SETUP.md](SETUP.md) | Guide d'installation pas à pas |
| [API.md](API.md) | Documentation complète de l'API REST |
| [SERVICE-SETUP.md](SERVICE-SETUP.md) | Configuration et gestion du service systemd |
| [TESTING.md](TESTING.md) | Guide des tests et validation |
| [MIGRATION.md](MIGRATION.md) | Guide de migration depuis versions antérieures |
| [CLAUDE.md](CLAUDE.md) | Guide de développement pour contributeurs |

---

## 🔧 Exemples d'Utilisation

### cURL

```bash
# Obtenir le statut
curl http://raspberrypi:8000/v1/camera/status

# Passer en exposition manuelle (20ms, gain 2.0)
curl -X POST http://raspberrypi:8000/v1/camera/manual_exposure \
  -H "Content-Type: application/json" \
  -d '{"exposure_us": 20000, "gain": 2.0}'

# Arrêter le streaming
curl -X POST http://raspberrypi:8000/v1/streaming/stop

# Avec authentification (si CAMERA_API_KEY est définie)
curl -H "X-API-Key: votre-clé" \
  http://raspberrypi:8000/v1/camera/status
```

### Python

```python
import requests

BASE_URL = "http://raspberrypi:8000"
HEADERS = {"X-API-Key": "votre-clé"}  # Si authentification activée

# Obtenir le statut
response = requests.get(f"{BASE_URL}/v1/camera/status", headers=HEADERS)
status = response.json()
print(f"Lux: {status['lux']}, Exposure: {status['exposure_us']}µs")

# Régler l'exposition
requests.post(
    f"{BASE_URL}/v1/camera/manual_exposure",
    json={"exposure_us": 15000, "gain": 1.5},
    headers=HEADERS
)
```

### JavaScript / TypeScript

```javascript
const BASE_URL = "http://raspberrypi:8000";
const headers = {
  "Content-Type": "application/json",
  "X-API-Key": "votre-clé"  // Si authentification activée
};

// Obtenir le statut
const response = await fetch(`${BASE_URL}/v1/camera/status`, { headers });
const status = await response.json();
console.log(`Exposure: ${status.exposure_us}µs`);

// Régler l'exposition
await fetch(`${BASE_URL}/v1/camera/manual_exposure`, {
  method: "POST",
  headers,
  body: JSON.stringify({ exposure_us: 15000, gain: 1.5 })
});
```

---

## 🐛 Dépannage

### Caméra non détectée

```bash
rpicam-hello --list-cameras
```

Si aucune caméra n'apparaît, vérifier le câble et la connexion.

### Service ne démarre pas

```bash
# Voir les logs d'erreur
sudo journalctl -u pi-camera-service -n 50

# Vérifier le statut
sudo systemctl status pi-camera-service

# Tester manuellement
cd ~/pi-camera-service
source venv/bin/activate
python main.py
```

### Erreur ModuleNotFoundError: picamera2

Recréer le venv avec `--system-site-packages` :

```bash
cd ~/pi-camera-service
rm -rf venv
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Pas d'image en RTSP

1. Vérifier que le service tourne : `curl http://localhost:8000/health`
2. Vérifier MediaMTX : `sudo systemctl status mediamtx`
3. Voir les logs : `sudo journalctl -u pi-camera-service -f`

📖 Voir [SERVICE-SETUP.md](SERVICE-SETUP.md#troubleshooting) pour plus de solutions.

---

## 🏗️ Architecture du Code

```
pi-camera-service/
├── camera_service/
│   ├── __init__.py
│   ├── api.py                 # FastAPI app avec lifespan moderne
│   ├── camera_controller.py   # Contrôle caméra thread-safe
│   ├── streaming_manager.py   # Gestion streaming H.264
│   ├── config.py              # Configuration Pydantic
│   └── exceptions.py          # Exceptions personnalisées
├── tests/
│   ├── test_api.py            # Tests API (mocked)
│   ├── test_api_integration.py # Tests intégration (live API)
│   ├── test_camera_controller.py
│   ├── test_config.py
│   └── test_streaming_manager.py
├── main.py                    # Point d'entrée
├── requirements.txt           # Dépendances production
├── requirements-dev.txt       # Dépendances développement
├── .env.example              # Template configuration
├── test-api.sh               # Script de test
├── install-service.sh        # Installation service
├── pi-camera-service.service # Fichier systemd
└── docs/
    ├── SETUP.md              # Guide installation
    ├── API.md                # Documentation API
    ├── SERVICE-SETUP.md      # Guide systemd
    ├── TESTING.md            # Guide tests
    ├── MIGRATION.md          # Guide migration
    └── CLAUDE.md             # Guide développement
```

---

## 🔄 Changelog - Version 1.0

### Nouvelles Fonctionnalités
- ✅ Configuration via variables d'environnement (.env support)
- ✅ Authentification API optionnelle par clé
- ✅ Endpoint `/health` pour monitoring
- ✅ Versioning API avec préfixe `/v1`
- ✅ Tests d'intégration complets avec script `./test-api.sh`
- ✅ Service systemd avec auto-restart
- ✅ Documentation exhaustive (5 fichiers .md)

### Améliorations Techniques
- ✅ Migration vers Pydantic BaseSettings (configuration type-safe)
- ✅ FastAPI lifespan context manager (remplace @on_event deprecated)
- ✅ Dependency injection pour les singletons
- ✅ Logging structuré dans tous les modules
- ✅ Thread safety avec RLock (reentrant)
- ✅ Validation robuste des paramètres
- ✅ Gestion d'erreurs avec exceptions personnalisées
- ✅ Cleanup automatique des ressources

### Corrections de Bugs
- ✅ Fix streaming restart (caméra non redémarrée après stop)
- ✅ Fix PATH dans systemd (ffmpeg non trouvé)
- ✅ Fix virtual environment (--system-site-packages requis)
- ✅ Messages d'erreur en anglais (était français)

### Documentation
- ✅ SETUP.md - Guide installation complète
- ✅ API.md - Documentation API exhaustive
- ✅ SERVICE-SETUP.md - Guide systemd avec troubleshooting
- ✅ TESTING.md - Guide tests et validation
- ✅ MIGRATION.md - Migration depuis versions antérieures

---

## 📝 Licence

À compléter selon votre choix (MIT, Apache-2.0, etc.).

---

## 🤝 Contribution

Voir [CLAUDE.md](CLAUDE.md) pour le guide de développement.

Pour contribuer :
1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/amazing-feature`)
3. Commit les changements (`git commit -m 'Add amazing feature'`)
4. Push vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

---

## 📞 Support

En cas de problème :
1. Consulter [TESTING.md](TESTING.md) - Lancer `./test-api.sh`
2. Vérifier les logs : `sudo journalctl -u pi-camera-service -f`
3. Consulter [SERVICE-SETUP.md](SERVICE-SETUP.md) - Section troubleshooting
4. Ouvrir une issue sur GitHub

---

**Construit avec ❤️ pour Raspberry Pi**

🤖 Refactorisé avec [Claude Code](https://claude.com/claude-code)
