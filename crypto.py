"""
crypto.py - Acuerdo de claves X25519 y derivación de la semilla del mapa (HKDF-SHA256).

Convenciones:
  - Las claves se manejan como bytes en bruto (32 bytes), no como objetos de la biblioteca.
  - Nunca se escribe en logs ni en registros ninguna clave privada, secreto compartido ni semilla (RS-4).
  - Documentación de la biblioteca: https://cryptography.io (X25519 y HKDF).
"""

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

KEY_SIZE = 32                      # bytes de una clave X25519 (privada o pública)
SEED_SIZE = 32                     # bytes de la semilla derivada
CONTEXT_LABEL = b"tfm-stego-v1"    # etiqueta del contexto C de la derivación (apartado 3.4 de la memoria)


def generate_keypair(private_bytes: bytes | None = None) -> tuple[bytes, bytes]:
    """
    Genera un par de claves X25519.
    Args:
        private_bytes (bytes | None): si se da, 32 bytes con los que construir la clave privada
            (solo para pruebas reproducibles). Si es None, la clave es aleatoria.
    Returns:
        tuple[bytes, bytes]: (clave_privada, clave_publica), de 32 bytes cada una.
    Raises:
        ValueError: Si private_bytes no tiene 32 bytes.
    """
    if private_bytes is None:
        private_key_obj = X25519PrivateKey.generate()
    else:
        if len(private_bytes) != KEY_SIZE:
            raise ValueError(f"La clave privada debe tener {KEY_SIZE} bytes.")
        private_key_obj = X25519PrivateKey.from_private_bytes(private_bytes)

    private_key = private_key_obj.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
    )
    public_key = private_key_obj.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return private_key, public_key

def compute_shared_secret(private_key: bytes, peer_public_key: bytes) -> bytes:
    """
    Calcula el secreto compartido S = X25519(private_key, peer_public_key).
    Alice lo llama con (esk_A, PK_B) y Bob con (SK_B, epk_A): ambos obtienen el mismo S.
    Returns:
        bytes: secreto compartido de 32 bytes.
    Raises:
        ValueError: Si alguna clave no tiene 32 bytes o si el resultado es todo ceros
                    (clave pública de orden bajo).
    """
    if len(private_key) != KEY_SIZE or len(peer_public_key) != KEY_SIZE:
        raise ValueError("Las claves deben tener 32 bytes.")

    private_key_obj = X25519PrivateKey.from_private_bytes(private_key)
    public_key_obj = X25519PublicKey.from_public_bytes(peer_public_key)

    return private_key_obj.exchange(public_key_obj)


def derive_seed(shared_secret: bytes, epk: bytes, pk_b: bytes) -> bytes:
    """
    Deriva la semilla del mapa: K_mapa = HKDF(S, C), con C = CONTEXT_LABEL || epk || PK_B.
    Args:
        shared_secret (bytes): secreto compartido S.
        epk (bytes): clave pública efímera de Alice.
        pk_b (bytes): clave pública de Bob.
    Returns:
        bytes: semilla de SEED_SIZE bytes.
    """
    info = CONTEXT_LABEL + epk + pk_b
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=SEED_SIZE,
        salt=None,
        info=info
    )
    return hkdf.derive(shared_secret)


def sender_derive_seed(pk_b: bytes) -> tuple[bytes, bytes]:
    """
    Lado de Alice: genera un par efímero, calcula el secreto con PK_B y deriva la semilla.
    Returns:
        tuple[bytes, bytes]: (semilla, epk). La clave privada efímera NO se devuelve (RS-4).
    """
    esk, epk = generate_keypair()  # Genera un par efímero (esk, epk)
    shared_secret = compute_shared_secret(esk, pk_b)  # Calcula el secreto compartido S
    seed = derive_seed(shared_secret, epk, pk_b)  # Deriva la semilla K_mapa

    return seed, epk  # Devuelve la semilla y la clave pública efímera (epk), pero no la clave privada efímera (esk


def receiver_derive_seed(sk_b: bytes, pk_b: bytes, epk: bytes) -> bytes:
    """
    Lado de Bob: reconstruye la semilla con su clave privada y la clave efímera de Alice.
    Returns:
        bytes: la misma semilla que obtuvo Alice.
    """
    shared_secret = compute_shared_secret(sk_b, epk)  # Calcula el secreto compartido S
    seed = derive_seed(shared_secret, epk, pk_b)  # Deriva la semilla K_mapa
    return seed  # Devuelve la semilla
