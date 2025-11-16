# Pi Camera Service

Micro-service **FastAPI** pour contrôler une caméra Raspberry Pi (libcamera / Picamera2)
et diffuser un flux **H.264** vers **MediaMTX** via **RTSP**.

Ce service tourne **sur le Raspberry Pi**, prend le contrôle de la caméra (par ex. Raspberry Pi Camera Module v3),
et expose une **API HTTP** permettant de :

- lancer / arrêter le streaming vers MediaMTX,
- activer / désactiver l’auto-exposition,
- passer en exposition manuelle (temps d’expo + gain),
- activer / désactiver l’auto white balance (AWB),
- récupérer l’état courant de la caméra (lux, expo, gain, température de couleur…).

Le flux vidéo est publié vers MediaMTX, qui se charge ensuite de le servir
en **RTSP / WebRTC / HLS**, etc.

---

## 1. Architecture

Schéma logique :

    Pi Camera v3  ──>  Picamera2 / libcamera  ──>  H.264 encoder  ──>  MediaMTX (RTSP, WebRTC, HLS...)
                             ▲                         ▲
                             │                         │
                      Pi Camera Service API (FastAPI)  │
                             ▲                         │
                       App externe (backend, UI...) ───┘

- **Pi Camera Service** : ce projet, tournant sur le Pi.
- **Picamera2** : librairie Python pour piloter libcamera.
- **MediaMTX** : serveur de streaming (RTSP / WebRTC / HLS).
- **Application externe** : consomme le flux via MediaMTX et pilote la caméra via HTTP.

## 2. Prérequis

### 2.1. Matériel

- Raspberry Pi (Pi 4 ou Pi 5 recommandé pour l’encodage H.264).
- Caméra compatible libcamera (par exemple : Raspberry Pi Camera Module v3).

### 2.2. Paquets système (Raspberry Pi)

Sur le Pi :

    sudo apt update
    sudo apt install -y \
      git \
      python3-venv \
      python3-picamera2 \
      python3-libcamera \
      libcamera-apps \
      ffmpeg

Ces paquets fournissent notamment :

- `python3-picamera2` / `python3-libcamera` : interface caméra en Python,
- `libcamera-apps` : outils `rpicam-*` (debug/validation),
- `ffmpeg` : utilisé par `FfmpegOutput` (Picamera2),
- `python3-venv` : gestion des environnements virtuels,
- `git` : gestion de version.

Assure-toi également que **MediaMTX** est installé et fonctionne sur le Pi
(fichier de configuration `mediamtx.yml` disponible).

## 3. Installation du projet

### 3.1. Cloner le dépôt

Sur le Raspberry Pi :

    cd ~
    git clone https://github.com/<TON_USER>/pi-camera-service.git
    cd pi-camera-service

Remplace `<TON_USER>` par ton nom d’utilisateur GitHub.

### 3.2. Créer et activer l’environnement virtuel

    python3 -m venv venv
    source venv/bin/activate

Tu devrais voir `(venv)` au début du prompt.

### 3.3. Installer les dépendances Python

#### Option A – À partir de `requirements.txt`

    pip install --upgrade pip
    pip install -r requirements.txt

#### Option B – Installation minimale (si tu reconstruis le projet)

Le projet nécessite au minimum :

- `fastapi`
- `uvicorn[standard]`
- `pydantic`

Installation rapide :

    pip install --upgrade pip
    pip install "fastapi>=0.110" "uvicorn[standard]>=0.27" "pydantic>=2.0"

Note : la librairie **Picamera2** est fournie par le paquet APT `python3-picamera2`
et non par `pip`.

## 4. Configuration MediaMTX

Le service pousse un flux H.264 vers MediaMTX sur l’URL RTSP suivante :

- `rtsp://127.0.0.1:8554/cam`

Dans `mediamtx.yml` (sur le Pi), il faut déclarer le path `cam` comme **source publisher** :

    paths:
      cam:
        source: publisher
        # auth / options supplémentaires possibles ici

Important :

- ne **pas** utiliser `source: rpiCamera` sur ce path,
- sinon MediaMTX essaiera d’ouvrir directement la caméra et entrera en conflit
  avec le Pi Camera Service.

Redémarre MediaMTX après modification de la configuration.

---

## 5. Configuration du service (camera_service/config.py)

Le fichier `camera_service/config.py` contient les paramètres par défaut :

    from dataclasses import dataclass


    @dataclass
    class CameraConfig:
        width: int = 1920
        height: int = 1080
        framerate: int = 30
        bitrate: int = 8_000_000  # bits/s pour H.264
        rtsp_url: str = "rtsp://127.0.0.1:8554/cam"
        enable_awb: bool = True
        default_auto_exposure: bool = True


    CONFIG = CameraConfig()

Principaux paramètres :

- `width` / `height` : résolution de la sortie vidéo,
- `framerate` : nombre d’images par seconde,
- `bitrate` : bitrate H.264 (en bits/s),
- `rtsp_url` : URL RTSP de publication vers MediaMTX,
- `enable_awb` : active l’auto white balance à l’initialisation,
- `default_auto_exposure` : active l’auto-exposition au démarrage.


## 6. Lancement du service

### 6.1. Démarrage manuel

Dans le répertoire du projet :

    cd ~/pi-camera-service
    source venv/bin/activate
    python main.py

Par défaut, l’API écoute sur :

- `http://0.0.0.0:8000`

Au démarrage :

1. `CameraController` configure la caméra via Picamera2.
2. `StreamingManager` démarre l’encodage H.264.
3. Le flux est poussé vers `CONFIG.rtsp_url` (MediaMTX).

### 6.2. Vérifier le flux RTSP

Depuis un autre PC, avec VLC :

1. Menu « Média → Ouvrir un flux réseau… »
2. URL : `rtsp://<IP_DU_PI>:8554/cam`

---

## 7. API HTTP – Endpoints

Base URL de l’API :

- `http://<IP_DU_PI>:8000`

### 7.1. GET `/camera/status`

Retourne un snapshot de l’état courant de la caméra.

Exemple de réponse 200 :

    {
      "lux": 45.2,
      "exposure_us": 12000,
      "analogue_gain": 1.5,
      "colour_temperature": 4200.0,
      "auto_exposure": true,
      "streaming": true
    }

Champs :

- `lux` : estimation de la luminosité de la scène (si disponible),
- `exposure_us` : temps d’exposition actuel (µs),
- `analogue_gain` : gain analogique actuel,
- `colour_temperature` : température de couleur estimée (K),
- `auto_exposure` : `true` si l’auto-exposition est active,
- `streaming` : `true` si le flux vers MediaMTX est actif.

---

### 7.2. POST `/camera/auto_exposure`

Active ou désactive l’auto-exposition.

Corps JSON :

    {
      "enabled": true
    }

- `enabled` (`bool`) :
  - `true` : auto-exposition activée (`AeEnable = True` + `ExposureTime = 0`),
  - `false` : auto-exposition désactivée (`AeEnable = False`).

Réponse 200 :

    {
      "status": "ok",
      "auto_exposure": true
    }

---

### 7.3. POST `/camera/manual_exposure`

Passe la caméra en exposition manuelle.

Corps JSON :

    {
      "exposure_us": 20000,
      "gain": 2.0
    }

- `exposure_us` (`int`, obligatoire, > 0) : temps d’expo en microsecondes,
- `gain` (`float`, optionnel, > 0) : gain analogique (par défaut 1.0).

Effets :

- `AeEnable` est mis à `False`,
- `ExposureTime` et `AnalogueGain` sont fixés aux valeurs fournies.

Réponse 200 :

    {
      "status": "ok",
      "exposure_us": 20000,
      "gain": 2.0
    }

Réponse 400 (exemple de valeurs invalides) :

    {
      "detail": "exposure_us doit être > 0"
    }

---

### 7.4. POST `/camera/awb`

Active ou désactive l’auto white balance (AWB).

Corps JSON :

    {
      "enabled": false
    }

- `enabled` (`bool`) :
  - `true` : `AwbEnable = True`,
  - `false` : `AwbEnable = False`.

Réponse 200 :

    {
      "status": "ok",
      "awb_enabled": false
    }

---

### 7.5. POST `/streaming/start`

Démarre le streaming H.264 → MediaMTX (si ce n’est pas déjà actif).

Réponse 200 :

    {
      "status": "ok",
      "streaming": true
    }

---

### 7.6. POST `/streaming/stop`

Arrête le streaming H.264 → MediaMTX (si actif).

Réponse 200 :

    {
      "status": "ok",
      "streaming": false
    }

## 8. Exemples d’utilisation (curl)

Remplace `<IP_DU_PI>` par l’adresse IP réelle du Raspberry Pi.

### 8.1. Lire l’état de la caméra

    curl http://<IP_DU_PI>:8000/camera/status

### 8.2. Activer l’auto-exposition

    curl -X POST http://<IP_DU_PI>:8000/camera/auto_exposure \
      -H "Content-Type: application/json" \
      -d '{"enabled": true}'

### 8.3. Passer en manuel (20 ms, gain 2.0)

    curl -X POST http://<IP_DU_PI>:8000/camera/manual_exposure \
      -H "Content-Type: application/json" \
      -d '{"exposure_us": 20000, "gain": 2.0}'

### 8.4. Désactiver l’AWB

    curl -X POST http://<IP_DU_PI>:8000/camera/awb \
      -H "Content-Type: application/json" \
      -d '{"enabled": false}'

### 8.5. Démarrer / arrêter le streaming

    curl -X POST http://<IP_DU_PI>:8000/streaming/stop
    curl -X POST http://<IP_DU_PI>:8000/streaming/start

---

## 9. Exemple de client Python

Exemple minimal côté application externe :

    import requests

    PI_HOST = "http://raspberrypi:8000"  # ou http://<IP_DU_PI>:8000


    def get_status():
        resp = requests.get(f"{PI_HOST}/camera/status", timeout=2)
        resp.raise_for_status()
        return resp.json()


    def set_auto_exposure(enabled: bool = True):
        resp = requests.post(
            f"{PI_HOST}/camera/auto_exposure",
            json={"enabled": enabled},
            timeout=2,
        )
        resp.raise_for_status()
        return resp.json()


    def set_manual_exposure(exposure_us: int, gain: float = 1.0):
        resp = requests.post(
            f"{PI_HOST}/camera/manual_exposure",
            json={"exposure_us": exposure_us, "gain": gain},
            timeout=2,
        )
        resp.raise_for_status()
        return resp.json()


    if __name__ == "__main__":
        print("Status avant :", get_status())
        print("Passage en manuel :", set_manual_exposure(20000, 2.0))
        print("Status après :", get_status())

---

## 10. Lancer le service au démarrage (systemd)

Pour la production, tu peux créer un service `systemd` pour démarrer automatiquement
le Pi Camera Service au boot du Pi.

### 10.1. Unité systemd

Créer `/etc/systemd/system/pi-camera-service.service` :

    [Unit]
    Description=Pi Camera Service (FastAPI + Picamera2)
    After=network.target

    [Service]
    User=pi
    WorkingDirectory=/home/pi/pi-camera-service
    ExecStart=/home/pi/pi-camera-service/venv/bin/python /home/pi/pi-camera-service/main.py
    Restart=always
    RestartSec=3

    [Install]
    WantedBy=multi-user.target

Adapte `User` et les chemins si ton user n’est pas `pi`.

### 10.2. Activer et démarrer le service

    sudo systemctl daemon-reload
    sudo systemctl enable pi-camera-service.service
    sudo systemctl start pi-camera-service.service
    sudo systemctl status pi-camera-service.service

---

## 11. Dépannage

### 11.1. Caméra non détectée

Test rapide :

    rpicam-hello --list-cameras

Si aucune caméra n’apparaît :

- vérifier le câble et le connecteur,
- vérifier la configuration caméra dans Raspberry Pi OS (libcamera est utilisé par défaut
  sur les versions récentes).

### 11.2. Erreurs `ModuleNotFoundError: picamera2`

- vérifier le paquet :

      dpkg -l | grep picamera2

- s’assurer que tu lances le service avec le bon Python :
  l’interpréteur du venv basé sur `python3` du système.

### 11.3. Pas d’image en RTSP

- vérifier le statut de l’API :

      curl http://<IP_DU_PI>:8000/camera/status

- vérifier que MediaMTX tourne :

      systemctl status mediamtx

- consulter les logs :

      sudo journalctl -u mediamtx -f
      sudo journalctl -u pi-camera-service -f

---

## 12. Licence

À compléter selon ton choix (MIT, Apache-2.0, licence propriétaire interne, etc.).


