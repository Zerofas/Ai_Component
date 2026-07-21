import os
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()


def enviar_alerta_discord(
    categoria_spec: str,
    producto_exacto: str,
    precio: float,
    variacion: str,
    resumen_ia: str,
    url_producto: str
) -> bool:
    """
    Empaqueta y transmite alertas de adquisición mediante webhooks REST.
    Implementa el patrón de diseño desacoplado: el pipeline ETL no se detiene
    ante fallos de red en servicios de mensajería externos.

    Args:
        categoria_spec: Categoría de hardware monitoreado.
        producto_exacto: Nombre comercial exacto del producto.
        precio: Precio actual en euros.
        variacion: Cadena con el porcentaje y dirección de cambio (ej. "-15%").
        resumen_ia: Justificación o análisis generado por el LLM.
        url_producto: Enlace directo al producto.

    Returns:
        bool: True si el webhook fue recibido con éxito, False en caso contrario.
    """
    webhook_url: Optional[str] = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("[WEBHOOK WARN] DISCORD_WEBHOOK_URL no definida en variables de entorno. Omite notificación.")
        return False

    # Determinación visual de severidad basada en el signo de la variación porcentual
    es_reduccion = variacion.startswith("-")
    color_embed = 0x2b8a3e if es_reduccion else 0x1971c2  # Verde técnico (Ahorro) vs Azul institucional (Aviso)

    # Formateo de payload según especificación de Discord Embeds API
    payload = {
        "username": "AI Infrastructure Monitor",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/2103/2103633.png",
        "embeds": [
            {
                "title": f"OPORTUNIDAD DE ADQUISICIÓN TI: {categoria_spec}",
                "url": url_producto,
                "description": "El sistema de monitoreo inteligente ha detectado una ventana de entrada óptima de stock.",
                "color": color_embed,
                "fields": [
                    {
                        "name": "Modelo Identificado en Mercado",
                        "value": f"`{producto_exacto}`",
                        "inline": False
                    },
                    {
                        "name": "Precio Mínimo Registrado",
                        "value": f"**{precio:.2f} EUR**",
                        "inline": True
                    },
                    {
                        "name": "Variación Histórica",
                        "value": f"**{variacion}**",
                        "inline": True
                    },
                    {
                        "name": "Inferencia Técnica y Financiera (Meta Llama 3 - Groq)",
                        "value": f"_{resumen_ia}_",
                        "inline": False
                    }
                ],
                "footer": {
                    "text": "B2B Hardware ETL Pipeline | Monitoreo Automatizado de Infraestructura"
                },
                "timestamp": requests.utils.default_headers().get('Date')
            }
        ]
    }

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code in [200, 204]:
            print(f"[WEBHOOK INFO] Alerta transmitida con éxito a Discord para: {categoria_spec}")
            return True
        else:
            print(f"[WEBHOOK ERROR] Discord API rechazó la solicitud. Código: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"[WEBHOOK EXCEPTION] Error de red al intentar conectar con el servicio de mensajería: {e}")
        return False