"""
test_metrics.py - Pruebas de metrics.py.

Requisitos relacionados: RF-1 (criterio de aceptación), RF-4 (corrección RS), RS-2 (falsas correcciones)
y las métricas del capítulo 3: BER antes y después de RS, tasa de recuperación, PSNR y SSIM.
"""
import random
import unittest

import numpy as np

import metrics
from coding import encode_rs
from frame import build_frame, bytes_to_bits, bits_to_bytes, PROTOCOL_VERSION


def corrupt_bytes(coded: bytes, positions, mask=0xFF) -> list[int]:
    """Devuelve los bits de una palabra RS con los bytes de 'positions' alterados (XOR con mask)."""
    data = bytearray(coded)
    for p in positions:
        data[p] ^= mask
    return bytes_to_bits(bytes(data))


def make_image(seed=0, shape=(64, 64, 3)):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, shape, dtype=np.uint8)


class TestBitErrorRate(unittest.TestCase):

    def test_identical(self):
        self.assertEqual(metrics.bit_error_rate([0, 1, 1, 0], [0, 1, 1, 0]), 0.0)

    def test_all_different(self):
        self.assertEqual(metrics.bit_error_rate([0, 0, 0, 0], [1, 1, 1, 1]), 1.0)

    def test_known_value(self):
        """16 errores de 64 bits son una BER de 0,25."""
        sent = [0] * 64
        got = [1] * 16 + [0] * 48
        self.assertEqual(metrics.bit_error_rate(sent, got), 0.25)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            metrics.bit_error_rate([0, 1], [0, 1, 1])      # longitudes distintas
        with self.assertRaises(ValueError):
            metrics.bit_error_rate([], [])                 # vacío
        with self.assertRaises(ValueError):
            metrics.bit_error_rate([0, 2], [0, 1])         # no es un bit


class TestImageMetrics(unittest.TestCase):

    def test_psnr_identical_is_infinite(self):
        img = make_image()
        self.assertEqual(metrics.psnr(img, img), float("inf"))

    def test_psnr_known_value(self):
        """Diferencia constante de 1 en todos los píxeles: MSE=1, PSNR = 10*log10(255^2) = 48,13 dB."""
        img = np.full((16, 16, 3), 100, dtype=np.uint8)
        other = img + 1
        self.assertAlmostEqual(metrics.psnr(img, other), 48.1308, places=3)

    def test_psnr_symmetric_and_decreases_with_noise(self):
        img = make_image()
        small = img.copy(); small[0, 0, 0] ^= 1
        large = np.clip(img.astype(int) + 20, 0, 255).astype(np.uint8)
        self.assertAlmostEqual(metrics.psnr(img, large), metrics.psnr(large, img))
        self.assertGreater(metrics.psnr(img, small), metrics.psnr(img, large))

    def test_ssim_identical_is_one(self):
        img = make_image()
        self.assertAlmostEqual(metrics.ssim(img, img), 1.0, places=6)

    def test_ssim_lower_when_different(self):
        img = make_image()
        other = make_image(seed=5)
        value = metrics.ssim(img, other)
        self.assertLess(value, 0.5)
        self.assertGreaterEqual(value, -1.0)

    def test_invalid_images(self):
        a = make_image(shape=(64, 64, 3))
        with self.assertRaises(ValueError):
            metrics.psnr(a, make_image(shape=(32, 32, 3)))
        with self.assertRaises(ValueError):
            metrics.ssim(a, make_image(shape=(32, 32, 3)))
        with self.assertRaises(ValueError):
            metrics.psnr(a, a.astype(np.float32))


class TestClassifyDecoding(unittest.TestCase):

    def setUp(self):
        self.frame = build_frame(PROTOCOL_VERSION, 0x123456)
        self.coded = encode_rs(self.frame)
        self.sent_bits = bytes_to_bits(self.coded)

    def test_clean_channel(self):
        r = metrics.classify_decoding(self.frame, self.sent_bits)
        self.assertEqual(r.status, metrics.STATUS_OK)
        self.assertTrue(r.accepted)
        self.assertEqual(r.ber_raw, 0.0)
        self.assertEqual(r.ber_rs, 0.0)
        self.assertEqual(r.decoded_frame, self.frame)

    def test_up_to_two_bad_bytes_are_corrected(self):
        """Con 1 o 2 bytes alterados la trama se recupera, aunque la BER antes de RS no sea 0 (RF-4)."""
        for positions in ((3,), (0, 7), (2, 5)):
            r = metrics.classify_decoding(self.frame, corrupt_bytes(self.coded, positions))
            self.assertEqual(r.status, metrics.STATUS_OK)
            self.assertTrue(r.accepted)
            self.assertGreater(r.ber_raw, 0.0)
            self.assertEqual(r.ber_rs, 0.0)

    def test_three_bad_bytes_are_never_recovered(self):
        """Con 3 o más bytes alterados nunca sale 'correcta': o falla, o hay falsa corrección."""
        rng = random.Random(0)
        statuses = set()
        for _ in range(300):
            positions = rng.sample(range(8), rng.choice((3, 4, 5)))
            r = metrics.classify_decoding(self.frame, corrupt_bytes(self.coded, positions, rng.randrange(1, 256)))
            self.assertNotEqual(r.status, metrics.STATUS_OK)
            statuses.add(r.status)
        self.assertIn(metrics.STATUS_FAIL, statuses)

    def test_failure_has_no_output(self):
        """Un fallo detectado no produce trama: ber_rs y decoded_frame son None y no se acepta."""
        rng = random.Random(1)
        for _ in range(300):
            positions = rng.sample(range(8), 4)
            r = metrics.classify_decoding(self.frame, corrupt_bytes(self.coded, positions, rng.randrange(1, 256)))
            if r.status == metrics.STATUS_FAIL:
                self.assertIsNone(r.ber_rs)
                self.assertIsNone(r.decoded_frame)
                self.assertFalse(r.accepted)
                return
        self.fail("No se encontró ningún fallo detectado en 300 intentos")

    def test_false_correction_is_detected(self):
        """
        Construimos una falsa corrección a propósito: tomamos la palabra RS de OTRA trama válida y le
        alteramos 2 bytes. RS la corrige hacia esa otra trama, que no es la enviada.
        """
        other_frame = build_frame(PROTOCOL_VERSION, 0xABCDEF)
        other_coded = encode_rs(other_frame)
        r = metrics.classify_decoding(self.frame, corrupt_bytes(other_coded, (1, 6)))
        self.assertEqual(r.status, metrics.STATUS_FALSE)
        self.assertEqual(r.decoded_frame, other_frame)
        self.assertGreater(r.ber_rs, 0.0)
        # Con la misma versión V, el criterio de aceptación la acepta: por eso se compara también con M.
        self.assertTrue(r.accepted)

    def test_wrong_version_is_not_accepted(self):
        """Si V no coincide con V_esp, no se acepta aunque RS decodifique sin error (RF-1)."""
        wrong = build_frame(0x7F, 0x123456)
        r = metrics.classify_decoding(wrong, bytes_to_bits(encode_rs(wrong)))
        self.assertEqual(r.status, metrics.STATUS_OK)
        self.assertFalse(r.accepted)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            metrics.classify_decoding(self.frame, self.sent_bits[:63])
        with self.assertRaises(ValueError):
            metrics.classify_decoding(b"123", self.sent_bits)


class TestRecoveryRate(unittest.TestCase):

    def test_known_value(self):
        s = [metrics.STATUS_OK, metrics.STATUS_FAIL, metrics.STATUS_FALSE, metrics.STATUS_OK]
        self.assertEqual(metrics.recovery_rate(s), 0.5)

    def test_extremes(self):
        self.assertEqual(metrics.recovery_rate([metrics.STATUS_OK] * 10), 1.0)
        self.assertEqual(metrics.recovery_rate([metrics.STATUS_FALSE] * 10), 0.0)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            metrics.recovery_rate([])
        with self.assertRaises(ValueError):
            metrics.recovery_rate(["quizas"])


if __name__ == "__main__":
    unittest.main()