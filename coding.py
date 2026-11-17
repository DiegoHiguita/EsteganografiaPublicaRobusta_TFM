"""
coding.py - Codificación y decodificación Reed-Solomon RS(8,4) sobre GF(2^8).

Requiere reedsolo >= 1.0 (RSCodec.decode devuelve tres valores).
"""

from reedsolo import RSCodec, ReedSolomonError

# Parámetros Reed-Solomon RS(8,4): 4 bytes de datos + 4 de paridad = 8 bytes (64 bits)
RS_N = 8
RS_K = 4
RS_PARITY = RS_N - RS_K  # Corrige hasta RS_PARITY // 2 = 2 símbolos (bytes) erróneos

# Inicialización del codificador
rs = RSCodec(RS_PARITY)


def encode_rs(data: bytes) -> bytes:
    """
    Codifica 4 bytes mediante Reed-Solomon RS(8,4).
    Args:
        data (bytes): Bloque de exactamente 4 bytes.
    Returns:
        bytes: Bloque codificado de 8 bytes.
    Raises:
        ValueError: Si el bloque de entrada no tiene exactamente 4 bytes.
    """
    if len(data) != RS_K:
        raise ValueError(f"La trama debe tener exactamente {RS_K} bytes. Longitud recibida: {len(data)}")

    return bytes(rs.encode(data))  # rs.encode devuelve un bytearray; lo pasamos a bytes


def decode_rs(encoded_data: bytes) -> bytes:
    """
    Decodifica un bloque Reed-Solomon RS(8,4).
    Args:
        encoded_data (bytes): Bloque codificado de exactamente 8 bytes.
    Returns:
        bytes: Bloque original de 4 bytes recuperado.
    Raises:
        ValueError: Si la longitud del bloque es incorrecta.
        ReedSolomonError: Si no es posible corregir los errores.
    """
    if len(encoded_data) != RS_N:
        raise ValueError(f"El bloque codificado debe tener exactamente {RS_N} bytes. Longitud recibida: {len(encoded_data)}")

    decoded_msg, _, _ = rs.decode(encoded_data)  # RSCodec.decode() devuelve 3 valores

    if len(decoded_msg) != RS_K:
        raise ReedSolomonError("Longitud inesperada del mensaje recuperado.")

    return bytes(decoded_msg)
