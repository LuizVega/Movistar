"""
config.py - Configuración Global y Carga de Variables de Entorno (Movistar)
"""

import os
from dotenv import load_dotenv

# Cargar variables desde archivo .env local si existe
load_dotenv(override=True)

# Configuración de Google Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash").strip()
GEMINI_TEMPERATURE = float(os.environ.get("GEMINI_TEMPERATURE", "0.2"))

# Base de datos SQLite
MOVISTAR_DB_PATH = os.environ.get("MOVISTAR_DB_PATH", "movistar_desafio2.db").strip()

# Servidor y Entorno
APP_PORT = int(os.environ.get("PORT", "8501"))
IS_PRODUCTION = os.environ.get("ENV", "development").lower() == "production"

# Bandera de disponibilidad de API Key
HAS_GEMINI_KEY = bool(GEMINI_API_KEY and len(GEMINI_API_KEY) > 10 and not GEMINI_API_KEY.startswith("tu_api_key"))
