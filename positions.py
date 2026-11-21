"""
positions.py - Mapa pseudoaleatorio de posiciones de inserción y valores de dither.

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
    Args:
        height (int): altura de la imagen en píxeles.
        width (int): anchura de la imagen en píxeles."""
    return (height // BLOCK_SIZE) * (width // BLOCK_SIZE)


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
    """
    if len(seed) == 0:
        raise ValueError("La semilla no puede estar vacía.")
    
    if n_blocks < N_BITS // len(COEFFS):
        raise ValueError("No hay suficientes bloques para generar el mapa de inserción.")
    
    seed_int = int.from_bytes(seed, "big")
    rng = np.random.default_rng(seed_int)  # Crear el generador
    candidate_count = n_blocks * len(COEFFS) # Número total de candidatos (bloque, coeficiente)
    candidates = np.arange(candidate_count)  # Crear un array de candidatos
    selected_candidates = rng.choice(candidates, size=N_BITS, replace=False).tolist() # Elegir N_BITS candidatos sin repetición
    idx_positions = [(idx // len(COEFFS), COEFFS[idx % len(COEFFS)]) for idx in selected_candidates]  # Convertir cada índice en Position
    positions = tuple(Position(block=block, u=u, v=v) for block, (u, v) in idx_positions)  # Crear tuplas de posiciones
    dither = tuple(rng.random(N_BITS).tolist())  # Generar los valores de dither
    return EmbeddingMap(positions=positions, dither=dither)  # Devolver EmbeddingMap con tuplas (no listas) para que el mapa no se pueda modificar
       

def positions_by_block(emap: EmbeddingMap) -> dict[int, list[tuple[int, int, int]]]:
    """
    Agrupa las posiciones por bloque, para procesar cada bloque una sola vez
    (el pseudocódigo de EMBED/EXTRACT lo necesita: "para cada bloque b que aparece en P").
    Returns:
        dict: {bloque: [(i, u, v), ...]}, donde i es el índice del bit (0..63).
    """
    block_dict = {}
    for i, pos in enumerate(emap.positions):
        if pos.block not in block_dict:
            block_dict[pos.block] = []
        block_dict[pos.block].append((i, pos.u, pos.v))
    return block_dict