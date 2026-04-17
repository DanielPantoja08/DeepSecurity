"""
Centralised error / info message strings.

All user-facing messages live here so they can be updated in one place
and, in the future, replaced by a proper i18n library (e.g. Babel).
"""

# ── Faces ────────────────────────────────────────────────────────────────────
INVALID_IDENTITY_NAME = (
    "Nombre de identidad inválido. "
    "Use solo letras, números, espacios, guiones o guiones bajos (máx 64 caracteres)."
)
IDENTITY_NOT_FOUND = "Identity '{name}' not found"

# ── Recognition ──────────────────────────────────────────────────────────────
IMAGE_TOO_LARGE = "Imagen demasiado grande (máx 10 MB)"
UNSUPPORTED_IMAGE_FORMAT = "Formato no soportado. Use JPEG, PNG o WebP"

# ── Settings ─────────────────────────────────────────────────────────────────
EMPTY_PATH = "La ruta no puede estar vacía."
INVALID_PATH = "Ruta inválida: {error}"
PATH_NOT_A_DIRECTORY = "La ruta debe ser un directorio."
NATIVE_PICKER_DISABLED = (
    "La selección de carpetas nativa está desactivada en este entorno. "
    "Configure la ruta mediante la variable de entorno DB_PATH."
)

# ── History ──────────────────────────────────────────────────────────────────
RECORDING_NOT_FOUND = "Grabación no encontrada"
RECORDING_DELETED = "Grabación eliminada correctamente"
INVALID_DOWNLOAD_TOKEN = "Token de descarga inválido o expirado. Solicite uno nuevo."
VIDEO_FILE_NOT_FOUND = "Archivo de video no encontrado en el servidor"
