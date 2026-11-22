"""
imgutils.py - Carga, guardado y conversión de color de las imágenes.

Convenciones:
  - Las imágenes en color son matrices NumPy uint8 de forma (alto, ancho, 3) en orden BGR (el de OpenCV).
  - La luminancia Y es una matriz uint8 (alto, ancho), la que usa stego.py.
  - Se usa el espacio YCrCb de OpenCV (cv2.COLOR_BGR2YCrCb), que es el mismo de JPEG.
  - Ninguna función modifica su entrada.
"""

import numpy as np
import cv2


def load_bgr(path) -> np.ndarray:
    """
    Carga una imagen como matriz BGR uint8.
    Raises:
        ValueError: Si el fichero no existe o no se puede leer.

    """
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"No se pudo leer la imagen desde {path}")
    
    return img


def save_png(path, bgr: np.ndarray) -> None:
    """
    Guarda la imagen en PNG (sin pérdidas).
    Raises:
        ValueError: Si no se puede guardar.
    """
    saveImg = cv2.imwrite(str(path), bgr)
    if not saveImg:
        raise ValueError(f"No se pudo guardar la imagen en {path}")
    
    if not str(path).lower().endswith(".png"):
        raise ValueError("save_png solo guarda ficheros .png")


def get_luma(bgr: np.ndarray) -> np.ndarray:
    """
    Devuelve la luminancia Y de una imagen BGR.
    Raises:
        ValueError: Si bgr no es (alto, ancho, 3).
    """
    if bgr.ndim != 3 or bgr.shape[2] != 3:
        raise ValueError(f"Se esperaba una imagen BGR de forma (alto, ancho, 3), pero se recibió {bgr.shape}")
    
    luma = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)[:, :, 0].copy()

    return luma

def replace_luma(bgr: np.ndarray, luma: np.ndarray) -> np.ndarray:
    """
    Devuelve una imagen BGR igual a la dada pero con la luminancia sustituida por luma (la crominancia no cambia).
    Raises:
        ValueError: Si bgr no es (alto, ancho, 3) o luma no tiene el mismo alto y ancho.
    """
    if bgr.ndim != 3 or bgr.shape[2] != 3:
        raise ValueError(f"Se esperaba una imagen BGR de forma (alto, ancho, 3), pero se recibió {bgr.shape}")

    if luma.shape != bgr.shape[:2]:
        raise ValueError(f"luma debe tener forma {bgr.shape[:2]}, pero tiene {luma.shape}")
    
    img_ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    img_ycrcb[:, :, 0] = luma

    bgr_replaced = cv2.cvtColor(img_ycrcb, cv2.COLOR_YCrCb2BGR)

    return bgr_replaced