"""
test_frame.py
Pruebas unitarias para la construcción, deserialización y conversión binaria de la trama de 32 bits.
"""
import unittest
from frame import build_frame, parse_frame, bits_to_bytes, bytes_to_bits, FRAME_SIZE_BYTES, FRAME_SIZE_BITS

class TestFrame(unittest.TestCase):

    def test_build_and_parse_valid(self):
        """Verifica que build_frame y parse_frame sean simétricos con valores válidos."""
        print('\nTest Simetría [TF]')
        version_in = 0x01
        test_id_in = 0xABCDEF
        
        frame_bytes = build_frame(version_in, test_id_in)
        self.assertEqual(len(frame_bytes), FRAME_SIZE_BYTES)
        
        version_out, test_id_out = parse_frame(frame_bytes)
        self.assertEqual(version_out, version_in)
        self.assertEqual(test_id_out, test_id_in)

    def test_build_frame_edge_cases(self):
        """Verifica los límites de los enteros (0 y máximos de 8/24 bits)."""
        print('\nTest Limites [TF]')
        # Mínimos
        min_bytes = build_frame(0, 0)
        self.assertEqual(parse_frame(min_bytes), (0, 0))
        
        # Máximos (0xFF y 0xFFFFFF)
        max_bytes = build_frame(0xFF, 0xFFFFFF)
        self.assertEqual(parse_frame(max_bytes), (255, 16777215))

    def test_build_frame_out_of_bounds(self):
        """Verifica que se lancen excepciones ValueError al superar 8 o 24 bits."""
        print('\nTest Longitud [TF]')
        with self.assertRaises(ValueError):
            build_frame(256, 0x123456)  # Versión > 8 bits
            
        with self.assertRaises(ValueError):
            build_frame(-1, 0x123456)   # Versión negativa
            
        with self.assertRaises(ValueError):
            build_frame(1, 0x1000000)   # test_id > 24 bits

    def test_parse_frame_invalid_length(self):
        """Verifica error al parsear buffers de tamaño distinto a 4 bytes."""
        print('\nTest Tamaño [TF]')
        with self.assertRaises(ValueError):
            parse_frame(b"\x01\x02\x03")  # 3 bytes
            
        with self.assertRaises(ValueError):
            parse_frame(b"\x01\x02\x03\x04\x05")  # 5 bytes

    def test_bytes_to_bits_and_bits_to_bytes_roundtrip(self):
        """Verifica la conversión bidireccional entre bytes y lista de bits."""
        print('\nTest Conversor [TF]')
        original_bytes = build_frame(0x81, 0xA5A5A5)  # Patrón con bits alternados
        
        bit_list = bytes_to_bits(original_bytes)
        self.assertEqual(len(bit_list), FRAME_SIZE_BITS)
        self.assertTrue(all(b in (0, 1) for b in bit_list))
        
        reconstructed_bytes = bits_to_bytes(bit_list)
        self.assertEqual(reconstructed_bytes, original_bytes)

    def test_bits_to_bytes_invalid_input(self):
        """Verifica errores de validación en la lista de bits."""
        print('\nTest Bits [TF]')
        with self.assertRaises(ValueError):
            bits_to_bytes([0] * 31)  # 31 bits en vez de 32
            
        with self.assertRaises(ValueError):
            invalid_bits = [0] * 31 + [2]  # Elemento distinto de 0 o 1
            bits_to_bytes(invalid_bits)

if __name__ == "__main__":
    unittest.main()