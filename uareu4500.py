import os
import ctypes
from ctypes import c_int, c_char_p, POINTER, c_uint, c_ubyte

from ctypes import c_int, c_char_p, POINTER, c_uint, c_ubyte

directorio_actual = os.path.dirname(os.path.abspath(__file__))
if hasattr(os, 'add_dll_directory'):
    os.add_dll_directory(directorio_actual)

ruta_dll = os.path.join(directorio_actual, 'uareu4500.dll')
fingerprint_lib = ctypes.CDLL(ruta_dll, winmode=0)

# --- PROTECCIÓN DE MEMORIA CORREGIDA ---
# Le decimos que nos devuelva un PUNTERO real, no una cadena convertida a la fuerza
fingerprint_lib.python_read_fingerprint_and_get_base64_string.restype = ctypes.POINTER(ctypes.c_char)
fingerprint_lib.python_compare_base64_string_with_finger.argtypes = [ctypes.c_char_p]
fingerprint_lib.python_compare_base64_string_with_finger.restype = ctypes.c_int

# Obligamos a que la limpieza de memoria use el puntero correcto
fingerprint_lib.free_memory.argtypes = [ctypes.POINTER(ctypes.c_char)]

def getFingerReadingAsBase64String():
    # 1. Atrapamos la dirección de memoria exacta
    fmd_ptr = fingerprint_lib.python_read_fingerprint_and_get_base64_string()
    
    # 2. EL ESCUDO DE ACERO: Si el lector marca Timeout o el usuario quita el dedo (Devuelve NULL)
    if not fmd_ptr:
        return None
        
    try:
        # 3. Extraemos el texto de forma segura
        base64_string = ctypes.string_at(fmd_ptr).decode('utf-8')
    except Exception as e:
        print("Error al decodificar la huella:", e)
        base64_string = None
        
    # 4. Limpiamos la memoria de C++ SIN destruir la memoria de Python
    fingerprint_lib.free_memory(fmd_ptr)
    
    if not base64_string:
        return None
        
    return base64_string

def compareBase64StringWithFingerReading(base64_string):
    # Si la lectura falló por timeout, devolverá False en lugar de crashear
    return bool(fingerprint_lib.python_compare_base64_string_with_finger(base64_string.encode('utf-8')))

# --- PRUEBA DIRECTA ---
if __name__ == "__main__":
    print("Iniciando lector. Coloca tu huella...")
    fmd_base64_str_ptr = fingerprint_lib.python_read_fingerprint_and_get_base64_string()
    base64_string = ctypes.string_at(fmd_base64_str_ptr).decode('utf-8')
    print("FMD en Base64:", base64_string)

    print("\nComprobando huella. Vuelve a colocar el mismo dedo...")
    comparision_result = fingerprint_lib.python_compare_base64_string_with_finger(base64_string.encode('utf-8'))
    print("¿Las huellas coinciden?:", comparision_result)