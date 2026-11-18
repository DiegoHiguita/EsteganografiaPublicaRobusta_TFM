"""
positions.py - Mapa pseudoaleatorio de posiciones de inserción y valores de dither.

ESQUELETO: implementa las funciones marcadas con TODO. Orden sugerido:
  1) blocks_count   2) generate_map   3) positions_by_block (opcional, la usará stego.py)

Qué hace este módulo (apartados 3.3 y 3.4 de la memoria):
  A partir de la semilla que deriva crypto.py, elige 64 posiciones distintas
  (un bloque 8x8 y uno de los 8 coeficientes de frecuencia media) y 64 valores de dither.
  El emisor y el receptor llaman a la misma función con la misma semilla y obtienen el mismo mapa.

Convenciones:
  - El bit i de la trama codificada (los 64 bits de RS) se inserta en positions[i].
  - Los bloques se numeran recorriendo la imagen por filas: bloque = fila_de_bloque * columnas_de_bloques + columna_de_bloque.
  - (u, v) = (fila, columna) del coeficiente dentro del bloque 8x8, como en la tabla de cuantificación.
  - El dither se devuelve en [0, 1): stego.py lo multiplica por el paso Delta del coeficiente.
  - El orden de las extracciones aleatorias importa: primero las posiciones y después los dither.
"""

from typing import NamedTuple

import numpy as np

BLOCK_SIZE = 8
N_BITS = 64  # Bits de la trama codificada con RS(8,4)

# Ocho coeficientes AC de frecuencia media (índices zigzag 6 a 13), como (fila, columna).
# Sus pasos de cuantificación a Q=50 son 16, 14, 13, 14, 18, 17, 16 y 19.
COEFFS = [(0, 3), (1, 2), (2, 1), (3, 0), (4, 0), (3, 1), (2, 2), (1, 3)]


class Position(NamedTuple):
    block: int   # índice del bloque 8x8 (recorrido por filas)
    u: int       # fila del coeficiente dentro del bloque
    v: int       # columna del coeficiente dentro del bloque


class EmbeddingMap(NamedTuple):
    positions: tuple[Position, ...]   # N_BITS posiciones distintas; positions[i] <-> bit i
    dither: tuple[float, ...]         # N_BITS valores en [0, 1); dither[i] <-> bit i


def blocks_count(height: int, width: int) -> int:
    """
    Número de bloques 8x8 completos de una imagen (los bordes incompletos se ignoran).
    Ejemplo: una imagen de 512x512 tiene 64 * 64 = 4096 bloques.

    TODO: (height // BLOCK_SIZE) * (width // BLOCK_SIZE).
    """
    raise NotImplementedError


def generate_map(seed: bytes, n_blocks: int) -> EmbeddingMap:
    """
    Genera el mapa de inserción a partir de la semilla.
    Args:
        seed (bytes): semilla derivada con HKDF (crypto.derive_seed).
        n_blocks (int): número de bloques 8x8 de la imagen (blocks_count).
    Returns:
        EmbeddingMap: 64 posiciones distintas y 64 valores de dither.
    Raises:
        ValueError: Si la semilla está vacía o si hay menos bloques de los necesarios
                    (se necesitan al menos N_BITS // len(COEFFS) = 8 bloques).

    TODO:
      - Validar seed y n_blocks.
      - Crear el generador: rng = np.random.default_rng(int.from_bytes(seed, "big")).
      - Número de candidatos: n_blocks * len(COEFFS). Cada candidato es un par (bloque, coeficiente).
      - Elegir N_BITS candidatos sin repetición: rng.choice(candidatos, size=N_BITS, replace=False).
      - Convertir cada índice idx en Position(block=idx // len(COEFFS),
        u, v = COEFFS[idx % len(COEFFS)]).
      - Generar después los dither: rng.random(N_BITS).
      - Devolver EmbeddingMap con tuplas (no listas) para que el mapa no se pueda modificar.
    """
    raise NotImplementedError


def positions_by_block(emap: EmbeddingMap) -> dict[int, list[tuple[int, int, int]]]:
    """
    Agrupa las posiciones por bloque, para procesar cada bloque una sola vez
    (el pseudocódigo de EMBED/EXTRACT lo necesita: "para cada bloque b que aparece en P").
    Returns:
        dict: {bloque: [(i, u, v), ...]}, donde i es el índice del bit (0..63).

    TODO: recorrer emap.positions con enumerate y acumular en un diccionario.
    """
    raise NotImplementedError