from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from math import ceil
from time import perf_counter, sleep
from urllib.request import ProxyHandler, build_opener

URL = "http://127.0.0.1:8080/api/health"
CLIENTES = 4
DURACION = 30


def cliente(fin):
    tiempos = []
    errores = Counter()
    
    conexion = build_opener(ProxyHandler({}))

    while perf_counter() < fin:
        inicio = perf_counter()

        try:
            with conexion.open(URL, timeout=5) as respuesta:
                respuesta.read()
                if respuesta.status != 200:
                    raise RuntimeError(f"HTTP {respuesta.status}")

            tiempos.append((perf_counter() - inicio) * 1000)

        except Exception as error:
            errores[type(error).__name__] += 1

        sleep(0.1)

    return tiempos, errores


inicio = perf_counter()

with ThreadPoolExecutor(max_workers=CLIENTES) as executor:
    resultados = list(executor.map(
        cliente,
        [inicio + DURACION] * CLIENTES,
    ))

duracion = perf_counter() - inicio
tiempos = sorted(t for valores, _ in resultados for t in valores)
errores = Counter()

for _, fallos in resultados:
    errores.update(fallos)

print(f"Respuestas correctas: {len(tiempos)}")
print(f"Errores: {sum(errores.values())} {dict(errores)}")
print(f"Respuestas correctas/segundo: {len(tiempos) / duracion:.1f}")

if tiempos:
    print(f"Promedio: {sum(tiempos) / len(tiempos):.1f} ms")
    print(f"P95: {tiempos[ceil(len(tiempos) * 0.95) - 1]:.1f} ms")