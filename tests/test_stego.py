"""
test_stego.py - Pruebas de stego.py.

Requisitos relacionados: RF-1 (extracción ciega, ida y vuelta sin canal con BER = 0), RS-1 (clave incorrecta, BER ~ 0,5),
PSNR >= 38 dB. Se usa una imagen sintética reproducible (semilla fija), sin ficheros externos.
"""
import unittest

import numpy as np

import stego
from positions import generate_map, blocks_count, BLOCK_SIZE

ALPHAS = (1.5, 2, 3, 4)


def make_luma(height=512, width=512, seed=0):
    """Luminancia sintética reproducible, con valores lejos de 0 y 255 para evitar saturación."""
    rng = np.random.default_rng(seed)
    return np.clip(rng.normal(128, 30, (height, width)), 30, 225).round().astype(np.uint8)


def make_bits(seed=1):
    rng = np.random.default_rng(seed)
    return [int(b) for b in rng.integers(0, 2, 64)]


def psnr(a, b):
    mse = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)
    return float("inf") if mse == 0 else 10 * np.log10(255.0 ** 2 / mse)


class TestStego(unittest.TestCase):

    def setUp(self):
        self.luma = make_luma()
        self.bits = make_bits()
        self.emap = generate_map(b"k" * 32, blocks_count(*self.luma.shape))

    def test_delta_for(self):
        """delta_for(0, 3, 3) = 3 * Q50[0,3] = 3 * 16 = 48; alpha <= 0 lanza ValueError."""
        self.assertEqual(stego.delta_for(0, 3, 3), 48.0)
        with self.assertRaises(ValueError):
            stego.delta_for(0, 3, 0)
        with self.assertRaises(ValueError):
            stego.delta_for(0, 3, -1)

    def test_qim_single_value_roundtrip(self):
        """Para varios x, bits, delta y dither: decidir(insertar(x, b)) == b."""
        rng = np.random.default_rng(2)
        for _ in range(500):
            x = rng.uniform(-300, 300)
            delta = rng.uniform(10, 200)
            dither = rng.uniform(0, 1) * delta
            for bit in (0, 1):
                s = stego.qim_embed_value(x, bit, delta, dither)
                self.assertEqual(stego.qim_decide_bit(s, delta, dither), bit)

    def test_qim_moves_at_most_half_delta(self):
        """El coeficiente insertado queda a distancia <= Delta/2 del original (distorsión acotada)."""
        rng = np.random.default_rng(3)
        for _ in range(500):
            x, delta = rng.uniform(-300, 300), rng.uniform(10, 200)
            dither = rng.uniform(0, 1) * delta
            for bit in (0, 1):
                s = stego.qim_embed_value(x, bit, delta, dither)
                self.assertLessEqual(abs(s - x), delta / 2 + 1e-9)

    def test_qim_tolerates_noise_below_quarter_delta(self):
        """Con ruido |e| < Delta/4 sobre el valor insertado, el bit se sigue leyendo bien."""
        delta, dither = 48.0, 17.0
        for x in (-100.3, 0.0, 37.7, 250.1):
            for bit in (0, 1):
                s = stego.qim_embed_value(x, bit, delta, dither)
                for noise in (-0.24 * delta, 0.24 * delta):
                    self.assertEqual(stego.qim_decide_bit(s + noise, delta, dither), bit)

    def test_qim_fails_noise_above_quarter_delta(self):
        """Con ruido de 0,4 Delta (más allá de Delta/4) el bit se lee mal."""
        delta, dither = 48.0, 17.0
        for x in (-100.3, 0.0, 37.7, 250.1):
            for bit in (0, 1):
                s = stego.qim_embed_value(x, bit, delta, dither)
                self.assertNotEqual(stego.qim_decide_bit(s + 0.4 * delta, delta, dither), bit)

    def test_embed_does_not_modify_input(self):
        """La matriz de entrada es idéntica antes y después de embed."""
        copia = self.luma.copy()
        stego.embed(self.luma, self.bits, self.emap, 2.0)
        np.testing.assert_array_equal(self.luma, copia)

    def test_embed_output_type_and_shape(self):
        """La salida es uint8 y tiene la misma forma que la entrada."""
        out = stego.embed(self.luma, self.bits, self.emap, 2.0)
        self.assertEqual(out.dtype, np.uint8)
        self.assertEqual(out.shape, self.luma.shape)

    def test_roundtrip_without_channel(self):
        """embed + extract con el mismo mapa devuelven los 64 bits exactos, para cada alpha (RF-1)."""
        for alpha in ALPHAS:
            with self.subTest(alpha=alpha):
                out = stego.embed(self.luma, self.bits, self.emap, alpha)
                self.assertEqual(stego.extract(out, self.emap, alpha), self.bits)

    def test_roundtrip_all_zeros_and_all_ones(self):
        """Casos extremos: trama de todo ceros y de todo unos."""
        for bits in ([0] * 64, [1] * 64):
            out = stego.embed(self.luma, bits, self.emap, 2.0)
            self.assertEqual(stego.extract(out, self.emap, 2.0), bits)

    def test_roundtrip_non_square_and_non_multiple_of_8(self):
        """Imagen rectangular con ancho y alto no múltiplos de 8: los bordes sobrantes se ignoran."""
        luma = make_luma(300, 413, seed=5)
        emap = generate_map(b"z" * 32, blocks_count(*luma.shape))
        out = stego.embed(luma, self.bits, emap, 2.0)
        self.assertEqual(stego.extract(out, emap, 2.0), self.bits)

    def test_only_mapped_blocks_change(self):
        """Solo cambian píxeles de los bloques del mapa."""
        out = stego.embed(self.luma, self.bits, self.emap, 2.0)
        changed = np.argwhere(out != self.luma)
        blocks_per_row = self.luma.shape[1] // BLOCK_SIZE
        changed_blocks = {(r // BLOCK_SIZE) * blocks_per_row + (c // BLOCK_SIZE) for r, c in changed}
        mapped_blocks = {pos.block for pos in self.emap.positions}
        self.assertTrue(changed_blocks.issubset(mapped_blocks))
        self.assertLessEqual(len(changed_blocks), 64)

    def test_psnr_is_high(self):
        """El PSNR entre entrada y salida es >= 38 dB (esperado ~58-68 dB con 64 bits)."""
        for alpha in ALPHAS:
            out = stego.embed(self.luma, self.bits, self.emap, alpha)
            self.assertGreaterEqual(psnr(self.luma, out), 38.0)

    def test_wrong_map_gives_random_bits(self):
        """Con otro mapa (otra semilla), la BER media sobre 50 semillas ronda 0,5 (RS-1)."""
        out = stego.embed(self.luma, self.bits, self.emap, 2.0)
        bers = []
        for i in range(50):
            wrong = generate_map(f"otra-clave-{i}".encode(), blocks_count(*self.luma.shape))
            got = stego.extract(out, wrong, 2.0)
            bers.append(np.mean(np.array(got) != np.array(self.bits)))
        self.assertGreater(np.mean(bers), 0.4)
        self.assertLess(np.mean(bers), 0.6)

    def test_invalid_inputs(self):
        """luma 1D, luma demasiado pequeña, 63 bits o alpha <= 0 lanzan ValueError."""
        with self.assertRaises(ValueError):
            stego.embed(self.luma.ravel(), self.bits, self.emap, 2.0)
        with self.assertRaises(ValueError):
            stego.embed(np.zeros((4, 4), dtype=np.uint8), self.bits, self.emap, 2.0)
        with self.assertRaises(ValueError):
            stego.embed(self.luma, self.bits[:63], self.emap, 2.0)
        with self.assertRaises(ValueError):
            stego.embed(self.luma, self.bits, self.emap, 0)
        with self.assertRaises(ValueError):
            stego.extract(self.luma.ravel(), self.emap, 2.0)

    def test_block_outside_image(self):
        """Un mapa generado para una imagen grande no cabe en una imagen pequeña: ValueError."""
        big_map = generate_map(b"k" * 32, blocks_count(2048, 2048))
        with self.assertRaises(ValueError):
            stego.embed(self.luma, self.bits, big_map, 2.0)


if __name__ == "__main__":
    unittest.main()
