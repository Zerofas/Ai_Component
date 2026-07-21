import sqlite3
import json
import os
import time
from typing import Optional, List, Dict, Any, Tuple
from dotenv import load_dotenv
from groq import Groq
from database import DB_NAME

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise EnvironmentError("Error: Variable de entorno GROQ_API_KEY no configurada.")

# Inicializamos el cliente de Groq
client = Groq(api_key=api_key)


def obtener_historial(categoria_spec: str, limite: int = 5) -> List[Tuple[str, float, str]]:
    """
    Recupera el historial cronológico reciente para una categoría específica desde la base de datos.

    Args:
        categoria_spec: La categoría del producto a evaluar.
        limite: Número máximo de registros históricos a recuperar (por defecto 5).

    Returns:
        Lista de tuplas con (fecha, precio, producto_exacto).
    """
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT fecha, precio, producto_exacto FROM precios_hardware 
        WHERE categoria_spec = ? 
        ORDER BY fecha DESC LIMIT ?
    """, (categoria_spec, limite))
    datos = cursor.fetchall()
    conexion.close()
    return datos


def analizar_lote_con_ia(lista_hardware: List[Dict[str, Any]], max_reintentos: int = 3) -> Optional[Dict[str, Any]]:
    """
    Procesa un lote de productos enriquecidos con su historial en una sola inferencia de LLM,
    evaluando la viabilidad financiera de compra según la variación temporal.

    Args:
        lista_hardware: Lista de diccionarios con la información actual del producto.
        max_reintentos: Cantidad de intentos en caso de saturación o error de red en la API.

    Returns:
        Diccionario estrictamente estructurado en JSON con la decisión analítica, o None en fallo total.
    """
    if not lista_hardware:
        return {"error": "No se proporcionaron productos para el analisis."}

    lote_enriquecido = []
    for item in lista_hardware:
        categoria = item.get("categoria")
        historial = obtener_historial(categoria)
        lote_enriquecido.append({
            "categoria": categoria,
            "precio_hoy_eur": item.get("precio_hoy"),
            "historial_reciente": historial if historial else "Muestra historica insuficiente"
        })

    prompt_sistema = """
    Actúa EXCLUSIVAMENTE como Analista Financiero B2B de compras tecnológicas.
    
    REGLAS ESTRICTAS:
    1. Tu único objetivo es comparar el precio actual con el historial reciente para detectar oportunidades de ahorro (chollos).
    2. IGNORA la compatibilidad del hardware, no evalúes especificaciones técnicas, ventilación ni arquitecturas.
    3. Si el historial está vacío o no hay variación, la decisión es HOLD (false) por falta de recorrido.
    
    Devuelve ÚNICAMENTE un objeto JSON estrictamente formateado con esta estructura:
    {
        "analisis_individual": [
            {
                "categoria": "nombre de la categoria",
                "comprar": true o false,
                "variacion": "porcentaje",
                "justificacion": "razonamiento puramente financiero basado en el historial"
            }
        ],
        "evaluacion_global_workstation": {
            "compatibilidad_tecnica": "No aplica. Análisis puramente financiero.",
            "alertas_montaje": "Ninguna. Monitoreo de precios activo.",
            "veredicto_final": "Sistema enfocado en detección de ahorro B2B."
        }
    }
    """

    prompt_usuario = f"Analiza estos datos:\n{json.dumps(lote_enriquecido, indent=2, ensure_ascii=False)}"

    for intento in range(1, max_reintentos + 1):
        try:
            print(f"[IA INFO] Solicitando inferencia JSON a Groq API (Llama-3)... (Intento {intento})")

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # Modelo Open Source ultra potente
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": prompt_usuario}
                ],
                response_format={"type": "json_object"},  # Fuerza salida JSON estricta
                temperature=0.2
            )

            print("[IA EXEC] Inferencia completada exitosamente.")
            return json.loads(response.choices[0].message.content)

        except Exception as e:
            print(f"[IA WARN] Error de red o saturación temporal: {e}")
            if intento < max_reintentos:
                time.sleep(5)
            else:
                print("[IA CRITICAL] Fallo total de conexión con la API de Groq.")
                return None