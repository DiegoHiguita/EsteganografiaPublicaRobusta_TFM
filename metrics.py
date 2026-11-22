"""
metrics.py - Métricas de la evaluación: BER, estado de la decodificación, tasa de recuperación, PSNR y SSIM.


Definiciones (apartado de métricas del capítulo 3):
  - BER_raw: errores sobre los 64 bits codificados, antes de la corrección RS.
  - BER_RS:  errores sobre los 32 bits de la trama, solo si RS devuelve una trama (si falla, no existe: None).
  - Estado de la decodificación: "correcta" (la trama coincide con M), "fallo" (RS lanza ReedSolomonError)
    o "falsa_correccion" (RS devuelve una trama, pero distinta de M).
  - Aceptación (RF-1): RS decodifica sin error Y el campo V coincide con V_esp. OJO: una falsa corrección
    puede ser aceptada si su V es correcto; por eso el estado se calcula comparando con M.
  - Tasa de recuperación R: fracción de ensayos con estado "correcta".
  - PSNR y SSIM: entre la imagen original I y la estego I' (en color, antes del canal).
"""

from typing import NamedTuple

import numpy as np
from skimage.metrics import peak_signal_noise_ratio, structural_similarity
from reedsolo import ReedSolomonError

from coding import encode_rs, decode_rs
from frame import bytes_to_bits, bits_to_bytes, is_valid_version

STATUS_OK = "correcta"
STATUS_FAIL = "fallo"
STATUS_FALSE = "falsa_correccion"
STATUSES = (STATUS_OK, STATUS_FAIL, STATUS_FALSE)


class DecodingResult(NamedTuple):
    status: str                 # uno de STATUSES
    accepted: bool              # criterio de aceptación (RS sin error y V == V_esp)
    ber_raw: float              # BER sobre los 64 bits codificados
    ber_rs: float | None        # BER sobre los 32 bits de la trama; None si RS falla
    decoded_frame: bytes | None # trama devuelta por RS; None si RS falla


def bit_error_rate(sent: list[int], received: list[int]) -> float:
    """
    Fracción de posiciones en que dos secuencias de bits difieren.
    Raises:
        ValueError: Si las longitudes son distintas, están vacías o algún valor no es 0 o 1.
    """
    if len(sent) != len(received):
        raise ValueError("Las secuencias deben tener la misma longitud.")
    if len(sent) == 0:
        raise ValueError("Las secuencias no pueden estar vacías.")
    if not all(bit in (0, 1) for bit in sent) or not all(bit in (0, 1) for bit in received):
        raise ValueError("Las secuencias deben contener solo 0s y 1s.")

    ber = sum(s != r for s, r in zip(sent, received)) / len(sent)

    return ber      

def psnr(original: np.ndarray, modified: np.ndarray) -> float:
    """
    PSNR en dB entre dos imágenes uint8 de la misma forma.
    Raises:
        ValueError: Si las formas son distintas o alguna no es uint8.
    """
    if original.shape != modified.shape:
        raise ValueError("Las imágenes deben tener la misma forma.")
    if original.dtype != np.uint8 or modified.dtype != np.uint8:
        raise ValueError("Las imágenes deben ser de tipo uint8.")
    
    if np.array_equal(original, modified):
        return float("inf")
    
    psnr_value = peak_signal_noise_ratio(original, modified, data_range=255)

    return  float(psnr_value)

def ssim(original: np.ndarray, modified: np.ndarray) -> float:
    """
    SSIM entre dos imágenes uint8 de la misma forma (en color: channel_axis=2).
    Raises:
        ValueError: Igual que psnr.
    """
    if original.shape != modified.shape:
        raise ValueError("Las imágenes deben tener la misma forma.")
    if original.dtype != np.uint8 or modified.dtype != np.uint8:
        raise ValueError("Las imágenes deben ser de tipo uint8.")

    ssim_value = structural_similarity(original, modified, data_range=255, channel_axis=2 if original.ndim == 3 else None)

    return float(ssim_value)

def recovery_rate(statuses: list[str]) -> float:
    """
    Tasa de recuperación R: fracción de estados "correcta" sobre el total.
    Raises:
        ValueError: Si la lista está vacía o hay un estado que no está en STATUSES.
    """
    if len(statuses) == 0:
        raise ValueError("La lista de estados no puede estar vacía.")
    if not all(status in STATUSES for status in statuses):
        raise ValueError(f"Todos los estados deben estar en {STATUSES}.")
    
    r = statuses.count(STATUS_OK) / len(statuses)
    return r


def classify_decoding(sent_frame: bytes, received_bits: list[int]) -> DecodingResult:
    """
    Decodifica los 64 bits recibidos y los compara con la trama enviada.
    Args:
        sent_frame (bytes): trama M de 4 bytes que se envió.
        received_bits (list[int]): 64 bits extraídos de la imagen.
    Raises:
        ValueError: Si received_bits no tiene 64 elementos o sent_frame no tiene 4 bytes.
    """
    if len(received_bits) != 64:
        raise ValueError("received_bits debe tener exactamente 64 elementos.")
    if len(sent_frame) != 4:
        raise ValueError("sent_frame debe tener exactamente 4 bytes.")
    
    sent_bits = bytes_to_bits(encode_rs(sent_frame))
    ber = bit_error_rate(sent_bits, received_bits)

    try:
        decoded = decode_rs(bits_to_bytes(received_bits)) #decodificamos los bits recibidos a bytes y luego decodificamos con RS
    except ReedSolomonError:
        return DecodingResult(STATUS_FAIL, False, ber, None, None)

    if decoded == sent_frame:
        status = STATUS_OK
    else:
        status = STATUS_FALSE

    ber_rs = bit_error_rate(bytes_to_bits(sent_frame), bytes_to_bits(decoded))
    accepted = is_valid_version(decoded)

    return DecodingResult(status, accepted, ber, ber_rs, decoded)
    
    