"""
stego.py - Inserción y extracción de bits mediante QIM con dither sobre coeficientes DCT.

Estructura: delta_for, qim_embed_value y qim_decide_bit trabajan con UN coeficiente;
embed y extract recorren las 64 posiciones del mapa.

Trabaja sobre la luminancia Y (matriz 2D de uint8). La conversión de la imagen a YCbCr, la carga y el
guardado de ficheros NO van aquí (irán en otro módulo).

Convenciones (apartado 3.3 de la memoria):
  - El bit i se inserta en emap.positions[i] con el dither emap.dither[i] (valor en [0,1)).
  - Paso del coeficiente: Delta = alpha * Q50[u, v]. El dither real es emap.dither[i] * Delta.
  - Regla QIM: s(x, b) = Delta * round((x - d - b*Delta/2) / Delta) + d + b*Delta/2
  - Decisión: se elige el bit cuyo retículo queda más cerca del coeficiente recibido (restando d).
  - DCT ortonormal de bloques 8x8 con desplazamiento de 128: cv2.dct(bloque - 128.0) en float.
  - Redondear y limitar a [0, 255] SOLO al final, al reconstruir cada bloque.
  - Los bloques se numeran por filas (ver positions.py). No se modifica la imagen de entrada.
"""

import numpy as np
import cv2

from positions import EmbeddingMap, BLOCK_SIZE

# Tabla de cuantificación de luminancia del estándar JPEG para Q=50, como matriz [fila, columna].
Q50 = np.array([
    [16, 11, 10, 16,  24,  40,  51,  61],
    [12, 12, 14, 19,  26,  58,  60,  55],
    [14, 13, 16, 24,  40,  57,  69,  56],
    [14, 17, 22, 29,  51,  87,  80,  62],
    [18, 22, 37, 56,  68, 109, 103,  77],
    [24, 35, 55, 64,  81, 104, 113,  92],
    [49, 64, 78, 87, 103, 121, 120, 101],
    [72, 92, 95, 98, 112, 100, 103,  99],
], dtype=np.float64)


def delta_for(u: int, v: int, alpha: float) -> float:
    """
    Paso de cuantificación Delta del coeficiente (u, v): alpha * Q50[u, v].
    Raises:
        ValueError: Si alpha <= 0.
    """
    if alpha <= 0:
        raise ValueError("alpha debe ser mayor que 0")
    return float(alpha * Q50[u, v])


def qim_embed_value(coef: float, bit: int, delta: float, dither: float) -> float:
    """
    Aplica la regla QIM a un coeficiente: devuelve el punto del retículo del bit más cercano a coef.
    Args:
        coef (float): coeficiente DCT original.
        bit (int): 0 o 1.
        delta (float): paso Delta.
        dither (float): dither ya escalado (dither[i] * delta).
    """
    # El retículo del bit 1 está desplazado Delta/2 respecto al del bit 0
    lattice_offset = dither + bit * delta / 2
    return delta * np.round((coef - lattice_offset) / delta) + lattice_offset


def qim_decide_bit(received_coef: float, delta: float, dither: float) -> int:
    """
    Decide el bit de un coeficiente recibido: gana el retículo (bit 0 o bit 1) más cercano.
    """
    # Distancia al punto más próximo del retículo del bit 0
    shifted_0 = received_coef - dither
    dist_to_bit0 = abs(shifted_0 - delta * np.round(shifted_0 / delta))

    # Distancia al punto más próximo del retículo del bit 1 (desplazado Delta/2)
    shifted_1 = received_coef - (dither + delta / 2)
    dist_to_bit1 = abs(shifted_1 - delta * np.round(shifted_1 / delta))

    return 1 if dist_to_bit1 < dist_to_bit0 else 0


def _block_origin(block: int, luma_shape: tuple) -> tuple[int, int]:
    """Esquina superior izquierda (fila, columna) del bloque, numerados por filas. Valida que cabe en la imagen."""
    blocks_per_row = luma_shape[1] // BLOCK_SIZE
    row = (block // blocks_per_row) * BLOCK_SIZE
    col = (block % blocks_per_row) * BLOCK_SIZE
    if row + BLOCK_SIZE > luma_shape[0]:
        raise ValueError(f"Bloque {block} fuera de los límites de la imagen")
    return row, col


def _check_inputs(luma: np.ndarray, emap: EmbeddingMap) -> None:
    if luma.ndim != 2:
        raise ValueError("luma debe ser una matriz 2D")
    if luma.shape[0] < BLOCK_SIZE or luma.shape[1] < BLOCK_SIZE:
        raise ValueError("luma es demasiado pequeña para contener bloques de 8x8")
    if len(emap.positions) != 64:
        raise ValueError("emap debe contener exactamente 64 posiciones")


def embed(luma: np.ndarray, bits: list[int], emap: EmbeddingMap, alpha: float) -> np.ndarray:
    """
    Inserta los 64 bits en la luminancia.
    Args:
        luma (np.ndarray): matriz 2D uint8 (alto x ancho). NO se modifica.
        bits (list[int]): 64 bits (0/1) de la trama codificada con RS.
        emap (EmbeddingMap): mapa de posiciones y dither (positions.generate_map).
        alpha (float): factor de escala del paso.
    Returns:
        np.ndarray: nueva luminancia uint8 con los bits insertados.
    Raises:
        ValueError: Si luma no es 2D, si len(bits) != 64 o si algún bloque del mapa queda fuera de la imagen.
    """
    _check_inputs(luma, emap)
    if len(bits) != 64:
        raise ValueError("bits debe tener exactamente 64 elementos")

    # astype crea una copia en float: la imagen de entrada no se toca y no hay redondeos intermedios
    out = luma.astype(np.float64)
    for i, (block, u, v) in enumerate(emap.positions):
        row, col = _block_origin(block, luma.shape)
        # Vista (no copia) del bloque dentro de out: al asignar con [:] se escribe en out
        block_pixels = out[row:row + BLOCK_SIZE, col:col + BLOCK_SIZE]
        dct_block = cv2.dct(block_pixels - 128.0)

        delta = delta_for(u, v, alpha)
        dct_block[u, v] = qim_embed_value(dct_block[u, v], bits[i], delta, emap.dither[i] * delta)

        block_pixels[:] = cv2.idct(dct_block) + 128.0

    # Redondeo y recorte a [0, 255] solo al final
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def extract(luma: np.ndarray, emap: EmbeddingMap, alpha: float) -> list[int]:
    """
    Extrae los 64 bits de la luminancia (misma geometría y mismos parámetros que en embed).
    Returns:
        list[int]: 64 bits (0/1), en el orden del mapa.
    """
    _check_inputs(luma, emap)

    bits = []
    for i, (block, u, v) in enumerate(emap.positions):
        row, col = _block_origin(block, luma.shape)
        dct_block = cv2.dct(luma[row:row + BLOCK_SIZE, col:col + BLOCK_SIZE] - 128.0)

        delta = delta_for(u, v, alpha)
        bits.append(qim_decide_bit(dct_block[u, v], delta, emap.dither[i] * delta))
    
    return bits  # fuera del bucle: devuelve los 64 bits, no solo el primero
