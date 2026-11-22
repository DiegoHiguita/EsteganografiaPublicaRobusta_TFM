"""
test_channel.py - Pruebas de imgutils.py (conversión de color) y channel.py (recompresión JPEG).

Usa imágenes sintéticas reproducibles: un fondo suave con algo de ruido, parecido a una foto, sin ficheros externos.
Requisitos relacionados: RF-5 (parámetros configurables), RNF-3 (módulos independientes) y, en la prueba
de extremo a extremo, RF-1 (extracción ciega tras el canal).
"""
import os
import tempfile
import unittest

import cv2
import numpy as np

import channel
import imgutils
import stego
from positions import generate_map, blocks_count


def make_bgr(seed=0, height=512, width=512):
    """Creamos una imagen en color sintética: ondas suaves + ruido ligero + desenfoque pequeño."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:height, 0:width]
    base = 100 + 60 * np.sin(x / 37.0) + 40 * np.cos(y / 23.0)
    img = np.stack([base + rng.normal(0, 6, (height, width)) + k * 10 for k in range(3)], axis=-1)
    img = cv2.GaussianBlur(img.astype(np.float32), (0, 0), 1.2)
    return np.clip(img, 20, 235).astype(np.uint8)


def make_bits(seed=1):
    rng = np.random.default_rng(seed)
    return [int(b) for b in rng.integers(0, 2, 64)]


class TestImgUtils(unittest.TestCase):

    def test_get_luma_shape_and_type(self):
        """La luminancia es 2D, uint8, y del mismo alto y ancho que la imagen."""
        bgr = make_bgr()
        luma = imgutils.get_luma(bgr)
        self.assertEqual(luma.shape, bgr.shape[:2])
        self.assertEqual(luma.dtype, np.uint8)

    def test_get_luma_does_not_modify_input(self):
        bgr = make_bgr()
        copia = bgr.copy()
        imgutils.get_luma(bgr)
        np.testing.assert_array_equal(bgr, copia)

    def test_replace_luma_with_same_luma_changes_little(self):
        """Sustituir Y por la propia Y deja la imagen casi igual (el redondeo de color permite +-2)."""
        bgr = make_bgr()
        out = imgutils.replace_luma(bgr, imgutils.get_luma(bgr))
        self.assertEqual(out.shape, bgr.shape)
        self.assertLessEqual(np.max(np.abs(out.astype(int) - bgr.astype(int))), 2)

    def test_replace_luma_returns_requested_luma(self):
        """Tras sustituir Y y volver a leerla, la diferencia es pequeña (redondeo del paso a color)."""
        bgr = make_bgr()
        new_luma = np.clip(imgutils.get_luma(bgr).astype(int) + 3, 0, 255).astype(np.uint8)
        out = imgutils.replace_luma(bgr, new_luma)
        diff = np.abs(imgutils.get_luma(out).astype(int) - new_luma.astype(int))
        self.assertLessEqual(diff.max(), 2)

    def test_replace_luma_does_not_modify_input(self):
        bgr = make_bgr()
        copia = bgr.copy()
        imgutils.replace_luma(bgr, imgutils.get_luma(bgr))
        np.testing.assert_array_equal(bgr, copia)

    def test_replace_luma_invalid_inputs(self):
        bgr = make_bgr()
        with self.assertRaises(ValueError):
            imgutils.replace_luma(bgr, np.zeros((10, 10), dtype=np.uint8))
        with self.assertRaises(ValueError):
            imgutils.get_luma(np.zeros((8, 8), dtype=np.uint8))

    def test_png_roundtrip_is_lossless(self):
        """Guardar en PNG y volver a cargar devuelve exactamente la misma imagen."""
        bgr = make_bgr()
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, "estego.png")
            imgutils.save_png(ruta, bgr)
            np.testing.assert_array_equal(imgutils.load_bgr(ruta), bgr)

    def test_load_missing_file(self):
        with self.assertRaises(ValueError):
            imgutils.load_bgr("no_existe_esta_imagen.png")


class TestChannel(unittest.TestCase):

    def test_output_shape_and_type(self):
        bgr = make_bgr()
        out = channel.jpeg_recompress(bgr, 75)
        self.assertEqual(out.shape, bgr.shape)
        self.assertEqual(out.dtype, np.uint8)

    def test_does_not_modify_input(self):
        bgr = make_bgr()
        copia = bgr.copy()
        channel.jpeg_recompress(bgr, 75)
        np.testing.assert_array_equal(bgr, copia)

    def test_deterministic(self):
        """Mismos datos y misma calidad dan siempre el mismo resultado (RF-5)."""
        bgr = make_bgr()
        np.testing.assert_array_equal(channel.jpeg_recompress(bgr, 80), channel.jpeg_recompress(bgr, 80))

    def test_lower_quality_means_more_distortion(self):
        """El error medio respecto al original crece al bajar la calidad: Q=50 > Q=90 > Q=100."""
        bgr = make_bgr()
        errors = [np.mean(np.abs(channel.jpeg_recompress(bgr, q).astype(float) - bgr.astype(float)))
                  for q in (50, 90, 100)]
        self.assertGreater(errors[0], errors[1])
        self.assertGreater(errors[1], errors[2])

    def test_invalid_quality(self):
        bgr = make_bgr()
        for q in (0, 101, -5, 75.5, "80", None):
            with self.subTest(q=q):
                with self.assertRaises(ValueError):
                    channel.jpeg_recompress(bgr, q)

    def test_invalid_image(self):
        with self.assertRaises(ValueError):
            channel.jpeg_recompress(np.zeros((16, 16), dtype=np.uint8), 75)
        with self.assertRaises(ValueError):
            channel.jpeg_recompress(np.zeros((16, 16, 3), dtype=np.float32), 75)


class TestEndToEnd(unittest.TestCase):
    """Cadena completa: insertar en Y, volver a color, comprimir en JPEG, extraer de Y."""
    """ Inserto 64 bits en Y.
        Devuelvo la Y a la imagen en color.
        Paso la imagen por JPEG con una calidad Q.
        Saco la Y de la imagen recibida.
        Extraigo los 64 bits y compruebo si son los mismos."""

    def run_chain(self, alpha, quality, seed=0):
        bgr = make_bgr(seed)
        bits = make_bits(seed + 1)
        emap = generate_map(bytes([seed + 1]) * 32, blocks_count(*bgr.shape[:2]))
        stego_bgr = imgutils.replace_luma(bgr, stego.embed(imgutils.get_luma(bgr), bits, emap, alpha))
        received = channel.jpeg_recompress(stego_bgr, quality)
        return bits, stego.extract(imgutils.get_luma(received), emap, alpha)

    def test_without_jpeg_color_conversion_is_harmless(self):
        """Sin compresión, solo con la conversión de color, los 64 bits se recuperan (alpha=1.5, el caso más fino)."""
        bgr = make_bgr()
        bits = make_bits()
        emap = generate_map(b"k" * 32, blocks_count(*bgr.shape[:2]))
        stego_bgr = imgutils.replace_luma(bgr, stego.embed(imgutils.get_luma(bgr), bits, emap, 1.5))
        self.assertEqual(stego.extract(imgutils.get_luma(stego_bgr), emap, 1.5), bits)

    def test_survives_jpeg_when_delta_is_large_enough(self):
        """Con Q=90 y alpha en (2, 3, 4), sobre varias imágenes, se recuperan los 64 bits exactos."""
        for alpha in (2, 3, 4):
            for seed in range(5):
                with self.subTest(alpha=alpha, seed=seed):
                    bits, got = self.run_chain(alpha, 90, seed)
                    self.assertEqual(got, bits)

    def test_survives_quality_100(self):
        """Con Q=100 todos los alpha recuperan la trama."""
        for alpha in (1.5, 2, 3, 4):
            with self.subTest(alpha=alpha):
                bits, got = self.run_chain(alpha, 100)
                self.assertEqual(got, bits)

    def test_survives_q50_with_alpha_4(self):
        """Con Q=50 y alpha=4 (Delta = 4*q > 2*q) la trama también sobrevive; es el extremo duro del barrido."""
        for seed in range(5):
            with self.subTest(seed=seed):
                bits, got = self.run_chain(4, 50, seed)
                self.assertEqual(got, bits)


if __name__ == "__main__":
    unittest.main()