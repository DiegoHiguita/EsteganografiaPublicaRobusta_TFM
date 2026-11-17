"""
test_frame.py
Pruebas unitarias para la construcción, análisis y conversión binaria de la trama.
"""
import random
import unittest

from frame import (
    build_frame, parse_frame, bits_to_bytes, bytes_to_bits,
    is_valid_version, make_test_id,
    FRAME_SIZE_BYTES, FRAME_SIZE_BITS, PROTOCOL_VERSION,
)


class TestFrame(unittest.TestCase):

    def test_build_and_parse_valid(self):
        """Verifica que build_frame y parse_frame sean simétricos con valores válidos."""
        frame_bytes = build_frame(0x01, 0xABCDEF)
        self.assertEqual(len(frame_bytes), FRAME_SIZE_BYTES)
        self.assertEqual(parse_frame(frame_bytes), (0x01, 0xABCDEF))

    def test_field_order(self):
        """Verifica que V ocupa el primer byte y T los tres siguientes (big-endian)."""
        self.assertEqual(build_frame(0x01, 0xABCDEF), b"\x01\xAB\xCD\xEF")

    def test_build_frame_edge_cases(self):
        """Verifica los límites de los enteros (0 y máximos de 8/24 bits)."""
        self.assertEqual(parse_frame(build_frame(0, 0)), (0, 0))
        self.assertEqual(parse_frame(build_frame(0xFF, 0xFFFFFF)), (255, 16777215))

    def test_build_frame_out_of_bounds(self):
        """Verifica que se lance ValueError al superar 8 o 24 bits, o con valores negativos."""
        with self.assertRaises(ValueError):
            build_frame(256, 0x123456)
        with self.assertRaises(ValueError):
            build_frame(-1, 0x123456)
        with self.assertRaises(ValueError):
            build_frame(1, 0x1000000)
        with self.assertRaises(ValueError):
            build_frame(1, -1)

    def test_parse_frame_invalid_length(self):
        """Verifica error al analizar buffers de tamaño distinto a 4 bytes."""
        with self.assertRaises(ValueError):
            parse_frame(b"\x01\x02\x03")
        with self.assertRaises(ValueError):
            parse_frame(b"\x01\x02\x03\x04\x05")

    def test_is_valid_version(self):
        """Verifica el criterio de aceptación sobre el campo V."""
        self.assertTrue(is_valid_version(build_frame(PROTOCOL_VERSION, 0x123456)))
        self.assertFalse(is_valid_version(build_frame(PROTOCOL_VERSION ^ 0x01, 0x123456)))

    def test_make_test_id_is_reproducible(self):
        """Verifica que T es de 24 bits y que la misma semilla da el mismo patrón."""
        a = make_test_id(random.Random(42))
        b = make_test_id(random.Random(42))
        self.assertEqual(a, b)
        self.assertTrue(0 <= a <= 0xFFFFFF)

    def test_bytes_to_bits_known_vector(self):
        """Verifica el orden de los bits: del más al menos significativo."""
        bits = bytes_to_bits(b"\x80\x00\x00\x01")
        self.assertEqual(bits[:8], [1, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(bits[-8:], [0, 0, 0, 0, 0, 0, 0, 1])

    def test_roundtrip_32_bits(self):
        """Verifica la conversión bidireccional con la trama de 32 bits."""
        original = build_frame(0x81, 0xA5A5A5)
        bit_list = bytes_to_bits(original)
        self.assertEqual(len(bit_list), FRAME_SIZE_BITS)
        self.assertTrue(all(b in (0, 1) for b in bit_list))
        self.assertEqual(bits_to_bytes(bit_list), original)

    def test_roundtrip_64_bits(self):
        """Verifica la conversión con la trama codificada (8 bytes = 64 bits)."""
        original = bytes(range(8))
        bit_list = bytes_to_bits(original)
        self.assertEqual(len(bit_list), 64)
        self.assertEqual(bits_to_bytes(bit_list), original)

    def test_bits_to_bytes_invalid_input(self):
        """Verifica errores de validación en la lista de bits."""
        with self.assertRaises(ValueError):
            bits_to_bytes([0] * 31)          # no es múltiplo de 8
        with self.assertRaises(ValueError):
            bits_to_bytes([])                # vacía
        with self.assertRaises(ValueError):
            bits_to_bytes([0] * 31 + [2])    # valor distinto de 0 y 1


if __name__ == "__main__":
    unittest.main()
