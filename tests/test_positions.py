
"""
test_positions.py - Pruebas de positions.py.

Requisitos relacionados: RF-3, RS-3.
"""
import json
import unittest

import positions


class TestPositions(unittest.TestCase):

    def test_map_is_json_serializable(self):
        """Posiciones y dither son tipos normales de Python, aptos para el registro JSON."""
        emap = positions.generate_map(b"\x01" * 32, 4096)

        json.dumps({
            "positions": [list(p) for p in emap.positions],
            "dither": list(emap.dither)
        })

    def test_blocks_count(self):
        """512x512 -> 4096 bloques; los bordes incompletos se ignoran."""
        self.assertEqual(positions.blocks_count(512, 512), 4096)
        self.assertEqual(positions.blocks_count(515, 517), 4096)

    def test_coefficients_definition(self):
        """COEFFS tiene 8 coeficientes distintos, dentro del bloque 8x8 y sin DC."""
        self.assertEqual(len(set(positions.COEFFS)), 8)

        for u, v in positions.COEFFS:
            self.assertTrue(0 <= u < 8)
            self.assertTrue(0 <= v < 8)

        self.assertNotIn((0, 0), positions.COEFFS)

    def test_map_is_deterministic(self):
        """La misma semilla y el mismo número de bloques generan el mismo mapa."""
        seed = b"\x01" * 32

        map1 = positions.generate_map(seed, 4096)
        map2 = positions.generate_map(seed, 4096)

        self.assertEqual(map1, map2)

    def test_different_seed_gives_different_map(self):
        """Semillas distintas generan mapas distintos."""
        map1 = positions.generate_map(b"\x01" * 32, 4096)
        map2 = positions.generate_map(b"\x02" * 32, 4096)

        self.assertNotEqual(map1, map2)

    def test_number_and_uniqueness_of_positions(self):
        """Hay exactamente 64 posiciones y 64 valores dither, sin posiciones repetidas."""
        emap = positions.generate_map(b"\x01" * 32, 4096)

        self.assertEqual(len(emap.positions), positions.N_BITS)
        self.assertEqual(len(emap.dither), positions.N_BITS)
        self.assertEqual(len(set(emap.positions)), positions.N_BITS)

    def test_values_are_in_range(self):
        """Bloques, coeficientes y valores dither están dentro de sus rangos."""
        n_blocks = 4096
        emap = positions.generate_map(b"\x01" * 32, n_blocks)

        for block, u, v in emap.positions:
            self.assertTrue(0 <= block < n_blocks)
            self.assertIn((u, v), positions.COEFFS)

        for dither in emap.dither:
            self.assertTrue(0 <= dither < 1)

    def test_invalid_inputs(self):
        """Una semilla vacía o menos de 8 bloques deben lanzar ValueError."""
        with self.assertRaises(ValueError):
            positions.generate_map(b"", 4096)

        with self.assertRaises(ValueError):
            positions.generate_map(b"\x01" * 32, 7)

    def test_different_seeds_have_little_overlap(self):
        """Dos semillas distintas deben compartir como máximo 3 posiciones."""
        map1 = positions.generate_map(b"\x01" * 32, 4096)
        map2 = positions.generate_map(b"\x02" * 32, 4096)

        comunes = len(set(map1.positions) & set(map2.positions))

        self.assertLessEqual(comunes, 3)

    def test_positions_by_block(self):
        """El agrupado por bloque contiene los 64 bits exactamente una vez."""
        emap = positions.generate_map(b"\x01" * 32, 4096)

        agrupado = positions.positions_by_block(emap)

        indices = [
            i
            for posiciones in agrupado.values()
            for i, _, _ in posiciones
        ]

        self.assertEqual(sorted(indices), list(range(positions.N_BITS)))


if __name__ == "__main__":
    unittest.main()
