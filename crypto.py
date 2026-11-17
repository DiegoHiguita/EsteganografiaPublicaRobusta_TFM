"""
crypto.py - Acuerdo de claves X25519 y derivación de la semilla del mapa (HKDF-SHA256).

ESQUELETO: implementa las funciones marcadas con TODO. Orden sugerido:
  1) generate_keypair   2) compute_shared_secret   3) derive_seed
  4) sender_derive_seed y receiver_derive_seed (usan las anteriores)

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


def generate_keypair() -> tuple[bytes, bytes]:
    """
    Genera un par de claves X25519.
    Returns:
        tuple[bytes, bytes]: (clave_privada, clave_publica), de 32 bytes cada una.

    TODO:
      - Crear la clave privada con X25519PrivateKey.generate().
      - Obtener los bytes de la privada con private_bytes(encoding=Raw, format=Raw,
        encryption_algorithm=NoEncryption()) (serialization.Encoding.Raw, serialization.PrivateFormat.Raw...).
      - Obtener los bytes de la pública con private_key.public_key().public_bytes(Raw, Raw).
    """
    raise NotImplementedError


def compute_shared_secret(private_key: bytes, peer_public_key: bytes) -> bytes:
    """
    Calcula el secreto compartido S = X25519(private_key, peer_public_key).
    Alice lo llama con (esk_A, PK_B) y Bob con (SK_B, epk_A): ambos obtienen el mismo S.
    Returns:
        bytes: secreto compartido de 32 bytes.
    Raises:
        ValueError: Si alguna clave no tiene 32 bytes o si el resultado es todo ceros
                    (clave pública de orden bajo).

    TODO:
      - Validar longitudes (KEY_SIZE).
      - Cargar con X25519PrivateKey.from_private_bytes y X25519PublicKey.from_public_bytes.
      - Calcular private.exchange(public).
      - Comprobar que el resultado no es b"\\x00" * 32 (según la versión de la biblioteca,
        exchange() ya lanza ValueError; compruébalo con una prueba).
    """
    raise NotImplementedError


def derive_seed(shared_secret: bytes, epk: bytes, pk_b: bytes) -> bytes:
    """
    Deriva la semilla del mapa: K_mapa = HKDF(S, C), con C = CONTEXT_LABEL || epk || PK_B.
    Args:
        shared_secret (bytes): secreto compartido S.
        epk (bytes): clave pública efímera de Alice.
        pk_b (bytes): clave pública de Bob.
    Returns:
        bytes: semilla de SEED_SIZE bytes.

    TODO:
      - HKDF(algorithm=hashes.SHA256(), length=SEED_SIZE, salt=None, info=CONTEXT_LABEL + epk + pk_b)
      - Devolver .derive(shared_secret).
    """
    raise NotImplementedError


def sender_derive_seed(pk_b: bytes) -> tuple[bytes, bytes]:
    """
    Lado de Alice: genera un par efímero, calcula el secreto con PK_B y deriva la semilla.
    Returns:
        tuple[bytes, bytes]: (semilla, epk). La clave privada efímera NO se devuelve (RS-4).

    TODO: generate_keypair -> compute_shared_secret(esk, pk_b) -> derive_seed(S, epk, pk_b).
    """
    raise NotImplementedError


def receiver_derive_seed(sk_b: bytes, pk_b: bytes, epk: bytes) -> bytes:
    """
    Lado de Bob: reconstruye la semilla con su clave privada y la clave efímera de Alice.
    Returns:
        bytes: la misma semilla que obtuvo Alice.

    TODO: compute_shared_secret(sk_b, epk) -> derive_seed(S, epk, pk_b).
    """
    raise NotImplementedError
