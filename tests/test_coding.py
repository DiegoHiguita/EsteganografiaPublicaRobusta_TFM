"""
test_coding.py - Pruebas unitarias para la codificación y decodificación RS(8,4).
"""

import unittest
from reedsolo import ReedSolomonError
from coding import encode_rs, decode_rs, RS_N, RS_K


class TestCoding(unittest.TestCase):

    def setUp(self):
        self.raw_data = b"\x01\xAB\xCD\xEF"  # 4 bytes de prueba
        self.encoded_data = encode_rs(self.raw_data)

    def test_encode_length(self):
        """Verifica que la salida codificada tenga exactamente 8 bytes."""
        print('\nTest Codificar [TC]')
        self.assertEqual(len(self.encoded_data), RS_N)

    def test_decode_clean(self):
        """Verifica la recuperación sin errores en el canal."""
        print('\nTest Decodificar [TC]')
        decoded = decode_rs(self.encoded_data)
        self.assertEqual(decoded, self.raw_data)

    def test_correct_one_byte_error(self):
        """Verifica la corrección de 1 byte corrompido."""
        print('\nTest Correción 1 [TC]')
        corrupted = bytearray(self.encoded_data)
        corrupted[2] ^= 0xFF  # Alteramos 1 byte

        decoded = decode_rs(bytes(corrupted))
        self.assertEqual(decoded, self.raw_data)

    def test_correct_two_byte_errors(self):
        """Verifica la corrección del límite máximo (2 bytes corrompidos)."""
        print('\nTest Correción 2 [TC]')
        corrupted = bytearray(self.encoded_data)
        corrupted[0] ^= 0xAA  # Alteramos el primer byte
        corrupted[7] ^= 0x55  # Alteramos el último byte (paridad)

        decoded = decode_rs(bytes(corrupted))
        self.assertEqual(decoded, self.raw_data)

    def test_more_than_two_errors_behavior(self):
        """
        Verifica el comportamiento cuando hay más de 2 errores (fuera del límite teórico t=2).
        La recuperación de la trama original NUNCA debe garantizarse:
        o bien el decodificador lanza ReedSolomonError (detección de fallo),
        o bien devuelve un mensaje desalineado/incorrecto (miscorrection).
        """
        print('\nTest Correción 3 [TC]')
        corrupted = bytearray(self.encoded_data)
        corrupted[0] ^= 0x11
        corrupted[3] ^= 0x22
        corrupted[5] ^= 0x33  # 3 bytes alterados

        try:
            decoded = decode_rs(bytes(corrupted))
            # Si no lanza excepción (ocurrió miscorrection), verificamos que NO coincida con la trama original
            self.assertNotEqual(decoded, self.raw_data)
        except ReedSolomonError:
            # Si lanza excepción, el decodificador detectó la imposibilidad de corregir
            pass

    def test_invalid_lengths(self):
        """Verifica las excepciones de longitud en encode_rs y decode_rs."""
        print('\nTest Longitud [TC]')
        with self.assertRaises(ValueError):
            encode_rs(b"\x01\x02\x03")  # 3 bytes en lugar de 4

        with self.assertRaises(ValueError):
            decode_rs(b"\x01\x02\x03\x04\x05")  # 5 bytes en lugar de 8


if __name__ == "__main__":
    unittest.main()