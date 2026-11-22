"""
channel.py - Canal con pérdida: recompresión JPEG de la imagen estego.

El canal comprime la imagen COMPLETA en color (no solo Y) y la vuelve a decodificar, como haría
una plataforma real. La extracción posterior toma la luminancia de la imagen recibida (imgutils.get_luma).
"""

import numpy as np
import cv2


def jpeg_recompress(bgr: np.ndarray, quality: int) -> np.ndarray:
    """
    Comprime la imagen en JPEG con la calidad dada y la decodifica de nuevo.
    Args:
        bgr (np.ndarray): imagen uint8 (alto, ancho, 3) en BGR. NO se modifica.
        quality (int): calidad JPEG, entero entre 1 y 100.
    Returns:
        np.ndarray: imagen BGR uint8 del mismo tamaño tras pasar por JPEG.
    Raises:
        ValueError: Si quality no es un entero entre 1 y 100 (cuidado: True/False también son int en Python),
                    o si bgr no es uint8 con forma (alto, ancho, 3).
        RuntimeError: Si falla la codificación.
    """
    if isinstance(quality, bool) or not isinstance(quality, int) or not 1 <= quality <= 100:
        raise ValueError(f"quality debe ser un entero entre 1 y 100, pero se recibió {quality!r}")
    
    if bgr.dtype != np.uint8 or bgr.ndim != 3 or bgr.shape[2] != 3:
        raise ValueError("bgr debe ser una imagen uint8 de forma (alto, ancho, 3)")
    
    ok, buffer = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("Error al comprimir la imagen en JPEG")

    img_compressed = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if img_compressed is None:
        raise RuntimeError("Error al decodificar la imagen JPEG")

    return img_compressed