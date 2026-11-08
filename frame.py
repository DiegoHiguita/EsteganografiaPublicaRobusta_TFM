"""
frame.py - Construcción y extracción de la trama de 32 bits.
"""

FRAME_SIZE_BITS = 32
FRAME_SIZE_BYTES = 4


def build_frame(version: int, test_id: int) -> bytes:
    """
    Construye una trama de 32 bits a partir de un entero sin signo.
    Args:
        version (int): Valor entero de hasta 8 bits (0 a 2^8 - 1).
        test_id (int): Valor entero de hasta 24 bits (0 a 2^24 - 1).
    Returns:
        bytes: Secuencia de 4 bytes en orden big-endian (big mas significativo).
    Raises:
        ValueError: Si el valor de la version excede los 8 bits o es negativo.
        ValueError: Si el valor de la test_id excede los 24 bits o es negativo.
    """
    if not (0 <= version <= 0xFF): #comprobamos que la version cabe en 8 bits
        raise ValueError(f"La version debe caber en 8 bits sin signo (0 a 255). Valor recibido: {version}")

    if not (0 <= test_id <= 0xFFFFFF): #comprobamos que el entero cabe en 24 bits
            raise ValueError(f"El test_id debe caber en 24 bits sin signo (0 a 16777215). Valor recibido: {test_id}")

    frame = (version << 24) | test_id #construimos [V: 8 bits] + [T: 24 bits] = [M: 32 bits]
    frame_bytes = frame.to_bytes(FRAME_SIZE_BYTES, byteorder="big")

    return frame_bytes


def parse_frame(frame_bytes: bytes) -> tuple[int, int]:
    """
    Recupera los dos enteros de 8 y 24 bits a partir de la trama en bytes.
    Args:
        frame_bytes (bytes): Secuencia de exactamente 4 bytes.
    Returns:
        version: Entero de 8 bits desemparejado.
        test_id: Entero de 24 bits desemparejado.
    Raises:
        ValueError: Si la longitud de bytes no es de 4 bytes.
    """
    if len(frame_bytes) != FRAME_SIZE_BYTES: # Comprobamos que la longitud sea correcta con 4 bytes
        raise ValueError(f"La trama debe tener exactamente {FRAME_SIZE_BYTES} bytes. Longitud recibida: {len(frame_bytes)}")

    bits = int.from_bytes(frame_bytes, byteorder="big")

    version =  0xFF & (bits >> 24)
    test_id = bits & 0xFFFFFF

    return version, test_id


def bits_to_bytes(bit_list: list[int]) -> bytes:
    """
    Convierte una lista de 32 bits (0s y 1s) en 4 bytes.
    Args:
        bit_list (list[int]): Lista con exactamente 32 valores binarios (0 o 1).
    Returns:
        bytes: Trama de 4 bytes.
    """
    if len(bit_list) != FRAME_SIZE_BITS: # Comprobamos que la longitud de bits sea la correcta
        raise ValueError(f"Se requieren exactamente {FRAME_SIZE_BITS} bits. Recibidos: {len(bit_list)}")

    value = 0
    for bit in bit_list:
        if bit not in (0, 1): #Nos aseguramos que el bit tenga el valor adecuado
            raise ValueError(f"Los elementos deben ser 0 o 1. Valor hallado: {bit}")
        value = (value << 1) | bit #Desplazamos el valor acumulado una posición a la izquierda y añadimos el nuevo bit.

    return value.to_bytes(FRAME_SIZE_BYTES, byteorder="big")#convertimos un entero en 4 bytes.


def bytes_to_bits(frame_bytes: bytes) -> list[int]:
    """
    Convierte una trama de 4 bytes en una lista de 32 bits (0s y 1s).
    Args:
        frame_bytes (bytes): Secuencia de 4 bytes.
    Returns:
        list[int]: Lista de 32 enteros (0 o 1).
    """

    if len(frame_bytes) != FRAME_SIZE_BYTES: # Comprobamos que la longitud de bytes sea la correcta
        raise ValueError(f"Se requieren exactamente {FRAME_SIZE_BYTES} bytes. Recibidos: {len(frame_bytes)}")

    value = int.from_bytes(frame_bytes, byteorder="big")
    bits = []

    for i in range(FRAME_SIZE_BITS):
        bit = (value >> (31 - i)) & 1
        bits.append(bit)

    return bits