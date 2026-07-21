import time
import random
import json
from typing import List, Dict, Any
from scraper import obtener_datos_pccomponentes
from database import inicializar_db, insertar_precio, obtener_chollo_por_categoria
from ia_analyst import analizar_lote_con_ia
from notificador import enviar_alerta_discord

# Catalogo Enterprise enfocado en servidores e infraestructura de Inteligencia Artificial
CATALOGO_IA: List[Dict[str, Any]] = [
    {
        "categoria_spec": "GPU Workstation Nvidia PNY L4 24GB Pasiva",
        "urls": [
            "https://www.pccomponentes.com/tarjeta-grafica-pny-l4-24gb-gddr6-enfriamiento-pasivo-para-estaciones-de-trabajo"
        ]
    },
    {
        "categoria_spec": "Procesador AMD EPYC 8324P 32 Núcleos 2,65 GHz Base 3 GHz Turbo Hexa-channel DDR5",
        "urls": [
            "https://www.pccomponentes.com/procesador-amd-epyc-8324p-32-nucleos-265-ghz-base-3-ghz-turbo-hexa-channel-ddr5"
        ]
    },
    {
        "categoria_spec": "SSD Enterprise Samsung PM9D3a 3.84TB PCIe 5.0",
        "urls": [
            "https://www.pccomponentes.com/disco-duro-samsung-pm9d3a-3-84tb-ssd-2-5-pcie-5-0-nvme-12000mb-s-enterprise"
        ]
    },
    {
        "categoria_spec": "RAM ECC Registered Kingston 32GB DDR5 4800MHz",
        "urls": [
            "https://www.pccomponentes.com/memoria-ram-kingston-ktd-pe548d8-32g-32gb-1x32gb-ddr5-4800mhz-cl40-ecc-registered"
        ]
    }
]


def ejecutar_pipeline() -> None:
    """Orquesta el pipeline ETL: scraping de datos, persistencia SQL, inferencia por lotes con IA y alertas."""
    print("[INFO] Iniciando ejecución del pipeline ETL de monitoreo hardware...\n")

    # 1. Inicializacion y verificacion de la capa de persistencia
    print("[PASO 1] Verificando integridad de la base de datos...")
    inicializar_db()
    print("-" * 60)

    # 2. Extraccion de datos (Scraping)
    print(f"[PASO 2] Extrayendo información para {len(CATALOGO_IA)} categorías de infraestructura...\n")

    for grupo in CATALOGO_IA:
        spec = grupo["categoria_spec"]
        print(f"Procesando: {spec}")

        for url in grupo["urls"]:
            nombre_exacto, precio = obtener_datos_pccomponentes(url)

            # Persistencia en base de datos relacional
            if nombre_exacto and precio > 0:
                insertar_precio(spec, nombre_exacto, "PcComponentes", precio)
            else:
                print(f"[WARN] No se pudo extraer información válida de: {url}")

            # Estrategia anti-bot: retardo aleatorio (jitter) para emular comportamiento de navegación humana
            time.sleep(random.uniform(3.5, 7.2))

        print("-" * 60)

    # 3. Analisis por lotes y gestión de alertas
    print("\n[PASO 3] Consultando SQL y generando análisis integral con IA...\n")

    lote_para_ia = []
    mapa_productos = {}

    for grupo in CATALOGO_IA:
        spec = grupo["categoria_spec"]
        mejor_opcion = obtener_chollo_por_categoria(spec)

        if mejor_opcion:
            mod_exacto, p_min, tienda, fecha = mejor_opcion
            print(f"[SQL DATA] {spec} -> {p_min} EUR | {mod_exacto}")

            lote_para_ia.append({
                "categoria": spec,
                "precio_hoy": p_min
            })

            # Mapeo en memoria para acceso rápido en caso de disparar alerta
            mapa_productos[spec] = {
                "modelo": mod_exacto,
                "precio": p_min,
                "url": grupo["urls"][0]
            }
        else:
            print(f"[INFO] Sin registros en las últimas 24h para: {spec}")

    # Ejecucion de inferencia unificada si existen registros válidos
    if lote_para_ia:
        analisis_ia = analizar_lote_con_ia(lote_para_ia)

        if analisis_ia and isinstance(analisis_ia, dict):
            print("\n" + "=" * 60)
            print("EVALUACIÓN DE ARQUITECTURA GLOBAL - WORKSTATION IA")
            print("=" * 60)

            eval_global = analisis_ia.get("evaluacion_global_workstation", {})
            print(f"Compatibilidad Técnica: {eval_global.get('compatibilidad_tecnica', 'N/D')}")
            print(f"Alertas de Montaje:     {eval_global.get('alertas_montaje', 'Ninguna')}")
            print(f"Veredicto Final:        {eval_global.get('veredicto_final', 'N/D')}")
            print("=" * 60 + "\n")

            print("--- ANÁLISIS FINANCIERO Y DISPARO DE ALERTAS ---")
            for item_analisis in analisis_ia.get("analisis_individual", []):
                cat = item_analisis.get("categoria")
                comprar = item_analisis.get("comprar", False)
                variacion = item_analisis.get("variacion", "0%")
                justificacion = item_analisis.get("justificacion", "Sin justificación detallada.")

                estado_compra = "ACONSEJADA [BUY]" if comprar else "DESACONSEJADA [HOLD]"
                print(f"Categoría: {cat}")
                print(f"Decisión:  Adquisición {estado_compra} (Variación: {variacion})")
                print(f"Detalle:   {justificacion}\n")

                # Desacoplamiento: El sistema de notificación solo se activa si la IA valida la oportunidad
                if comprar and cat in mapa_productos:
                    print(f"[NOTIFICACIÓN] Oportunidad detectada. Enviando webhook a Discord para: {cat}...")
                    enviar_alerta_discord(
                        categoria_spec=cat,
                        producto_exacto=mapa_productos[cat]["modelo"],
                        precio=mapa_productos[cat]["precio"],
                        variacion=variacion,
                        resumen_ia=justificacion,
                        url_producto=mapa_productos[cat]["url"]
                    )
        else:
            print("[ERROR] El formato devuelto por la API de IA no se pudo procesar correctamente.")
    else:
        print("[INFO] No hay datos en el lote actual para ejecutar la inferencia de IA.")

    print("\n[INFO] Ejecución del pipeline ETL finalizada con éxito.")


if __name__ == "__main__":
    ejecutar_pipeline()