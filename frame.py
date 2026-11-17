"""
frame.py - Construcción y análisis de la trama experimental de 32 bits,
y conversión entre bytes y listas de bits.

Convenciones del prototipo (deben ser las mismas en emisor y receptor):
  - La trama es M = V || T: V (8 bits) en el byte más significativo y T (24 bits) después.
  - Orden de bytes: big-endian.
  - Orden de bits dentro de cada byte: del más significativo al menos significativo.
"""

import random

FRAME_SIZE_BITS = 32
FRAME_SIZE_BYTES = 4
PROTOCOL_VERSION = 0x01  # Valor esperado del campo V (V_esp) en el criterio de aceptación


def build_frame(version: int, test_id: int) -> bytes:
    """
    Construye la trama M = V || T de 32 bits.
    Args:
        version (int): Entero de hasta 8 bits (0 a 255).
        test_id (int): Entero de hasta 24 bits (0 a 16777215).
    Returns:
        bytes: 4 bytes en orden big-endian (V primero).
    Raises:
        ValueError: Si version o test_id están fuera de rango.
    """
    if not (0 <= version <= 0xFF):  # La versión debe caber en 8 bits
        raise ValueError(f"La version debe caber en 8 bits sin signo (0 a 255). Valor recibido: {version}")

    if not (0 <= test_id <= 0xFFFFFF):  # El patrón T debe caber en 24 bits
        raise ValueError(f"El test_id debe caber en 24 bits sin signo (0 a 16777215). Valor recibido: {test_id}")

    frame = (version << 24) | test_id  # [V: 8 bits] + [T: 24 bits] = [M: 32 bits]
    return frame.to_bytes(FRAME_SIZE_BYTES, byteorder="big")


def parse_frame(frame_bytes: bytes) -> tuple[int, int]:
    """
    Recupera V (8 bits) y T (24 bits) a partir de la trama en bytes.
    Args:
        frame_bytes (bytes): Secuencia de exactamente 4 bytes.
    Returns:
        tuple[int, int]: (version, test_id).
    Raises:
        ValueError: Si la longitud no es de 4 bytes.
    """
    if len(frame_bytes) != FRAME_SIZE_BYTES:
        raise ValueError(f"La trama debe tener exactamente {FRAME_SIZE_BYTES} bytes. Longitud recibida: {len(frame_bytes)}")

    value = int.from_bytes(frame_bytes, byteorder="big")
    return (value >> 24) & 0xFF, value & 0xFFFFFF


def is_valid_version(frame_bytes: bytes) -> bool:
    """
    Criterio de aceptación sobre V: comprueba que el campo de versión de la trama
    coincide con PROTOCOL_VERSION.
    Raises:
        ValueError: Si la longitud no es de 4 bytes.
    """
    version, _ = parse_frame(frame_bytes)
    return version == PROTOCOL_VERSION


def make_test_id(rng: random.Random) -> int:
    """
    Genera el patrón sintético T (24 bits) de forma reproducible.
    Args:
        rng (random.Random): Generador con semilla registrada, para repetir los experimentos.
    """
    return rng.getrandbits(24)


def bytes_to_bits(data: bytes) -> list[int]:
    """
    Convierte bytes en una lista de bits (0 y 1), del más al menos significativo.
    Sirve para la trama (4 bytes -> 32 bits) y para la trama codificada (8 bytes -> 64 bits).
    """
    return [(byte >> (7 - i)) & 1 for byte in data for i in range(8)]


def bits_to_bytes(bit_list: list[int]) -> bytes:
    """
    Convierte una lista de bits (0 y 1) en bytes. Operación inversa de bytes_to_bits.
    Raises:
        ValueError: Si la lista está vacía, su longitud no es múltiplo de 8 o contiene valores distintos de 0 y 1.
    """
    if len(bit_list) == 0 or len(bit_list) % 8 != 0:
        raise ValueError(f"La longitud debe ser un múltiplo de 8. Recibida: {len(bit_list)}")

    out = bytearray()
    for start in range(0, len(bit_list), 8):
        value = 0
        for bit in bit_list[start:start + 8]:
            if bit not in (0, 1):
                raise ValueError(f"Los elementos deben ser 0 o 1. Valor hallado: {bit}")
            value = (value << 1) | bit  # Desplazamos y añadimos el nuevo bit
        out.append(value)
    return bytes(out)
