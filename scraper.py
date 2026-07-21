import re
import json
from typing import Optional, Tuple, Any
import cloudscraper
from bs4 import BeautifulSoup


def buscar_producto_recursivo(obj: Any) -> Optional[Tuple[str, float]]:
    """
    Motor de extracción semántica profunda: recorre cualquier estructura JSON 
    (árboles @graph, listas anidadas o diccionarios complejos) buscando nodos 
    de producto sin importar la jerarquía ni mayúsculas/minúsculas.

    Args:
        obj: Objeto deserializado (dict, list u otro tipo primitivo) del JSON-LD.

    Returns:
        Tupla con (nombre_producto, precio) si se localiza, o None en caso contrario.
    """
    if isinstance(obj, dict):
        # Blindaje case-insensitive para detectar 'Product', 'https://schema.org/Product', etc.
        tipo = str(obj.get('@type', '')).lower()
        if any(k in tipo for k in ['product', 'itempage', 'individualproduct']):
            nombre_tmp = obj.get('name')
            precio_tmp = None

            # Buscamos el precio en todas las ubicaciones posibles del estándar Schema.org
            fuentes_precio = [obj, obj.get('offers', {}), obj.get('priceSpecification', {})]

            for fuente in fuentes_precio:
                elementos = fuente if isinstance(fuente, list) else [fuente]
                for item in elementos:
                    if isinstance(item, dict):
                        p = item.get('price') or item.get('lowPrice') or item.get('highPrice')

                        # Si las ofertas tienen sub-ofertas anidadas (común en B2B/Marketplaces)
                        if not p and 'offers' in item:
                            sub = item['offers']
                            sub_elems = sub if isinstance(sub, list) else [sub]
                            for sub_item in sub_elems:
                                if isinstance(sub_item, dict):
                                    p = sub_item.get('price') or sub_item.get('lowPrice')
                                    if p:
                                        break
                        if p:
                            precio_tmp = p
                            break
                if precio_tmp:
                    break

            if nombre_tmp and precio_tmp:
                return nombre_tmp, precio_tmp

        # Si este nodo no era el producto, seguimos buscando en sus hijos
        for valor in obj.values():
            res = buscar_producto_recursivo(valor)
            if res:
                return res

    elif isinstance(obj, list):
        for elemento in obj:
            res = buscar_producto_recursivo(elemento)
            if res:
                return res

    return None


def obtener_datos_pccomponentes(url: str) -> Tuple[Optional[str], float]:
    """
    Ejecuta una extracción resiliente en 3 niveles de degradación:
    1. JSON-LD (Semántico Recursivo): Resistente a cambios en la UI y estructuras complejas.
    2. Meta Tags (OpenGraph/Twitter): Metadatos inyectados para motores de búsqueda.
    3. Selectores CSS y Regex (DOM): Fallback visual ante ausencia de metadatos.

    Args:
        url: Dirección web del producto a procesar.

    Returns:
        Tupla con (nombre_exacto, precio). Retorna (None, 0.0) si fallan los 3 niveles.
    """
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    try:
        response = scraper.get(url, timeout=15)
        if response.status_code != 200:
            print(f"[SCRAPER ERROR] Respuesta HTTP {response.status_code} al solicitar: {url}")
            return None, 0.0

        # FORZADO DE CODIFICACIÓN: Evita problemas de Mojibake (ej. GrÃ¡fica -> Gráfica)
        response.encoding = 'utf-8'

        soup = BeautifulSoup(response.text, 'html.parser')

        # -------------------------------------------------------------------------
        # NIVEL 1: Extracción semántica profunda (JSON-LD / Schema.org)
        # -------------------------------------------------------------------------
        scripts_jsonld = soup.find_all('script', type='application/ld+json')
        for script in scripts_jsonld:
            try:
                # Usamos .text en lugar de .string por si hay comentarios en el DOM
                contenido = script.text.strip() if script.text else ""
                if not contenido:
                    continue

                data = json.loads(contenido)
                resultado_recursivo = buscar_producto_recursivo(data)

                if resultado_recursivo:
                    nombre_tmp, precio_tmp = resultado_recursivo

                    # Limpieza robusta de formato numérico con Regex
                    precio_limpio = re.sub(r'[^\d,.]', '', str(precio_tmp))
                    if ',' in precio_limpio and '.' in precio_limpio:
                        precio_limpio = precio_limpio.replace('.', '').replace(',', '.')
                    elif ',' in precio_limpio:
                        precio_limpio = precio_limpio.replace(',', '.')

                    if precio_limpio:
                        nombre = str(nombre_tmp).strip()
                        precio = float(precio_limpio)
                        print(f"[SCRAPER INFO] Extracción exitosa (Nivel 1 - Semántico): {nombre[:40]}... -> {precio} EUR")
                        return nombre, precio
            except (json.JSONDecodeError, ValueError, TypeError, AttributeError):
                continue

        # -------------------------------------------------------------------------
        # NIVEL 2: Metadatos OpenGraph y Twitter Cards
        # -------------------------------------------------------------------------
        nombre_meta = soup.find('meta', property='og:title') or soup.find('meta', attrs={'name': 'twitter:title'})
        precio_meta = soup.find('meta', property='product:price:amount') or soup.find('meta', property='og:price:amount')

        if nombre_meta and precio_meta:
            try:
                nombre = nombre_meta['content']
                precio_limpio = re.sub(r'[^\d,.]', '', str(precio_meta['content'])).replace(',', '.')
                precio = float(precio_limpio)
                print(f"[SCRAPER INFO] Extracción exitosa (Nivel 2 - Meta Tags): {nombre[:40]}... -> {precio} EUR")
                return nombre.strip(), precio
            except (ValueError, KeyError):
                pass

        # -------------------------------------------------------------------------
        # NIVEL 3: Fallback de DOM (Selectores CSS y Expresiones Regulares)
        # -------------------------------------------------------------------------
        print("[SCRAPER WARN] Falló extracción semántica. Iniciando fallback de análisis DOM (Nivel 3)...")

        nombre_dom = soup.find('h1')
        nombre = nombre_dom.text.strip() if nombre_dom else "Modelo desconocido (Fallback DOM)"

        selector_precio = soup.select_one('#precio-main, .price, [data-price], [class*="price"], [class*="Precio"]')

        if selector_precio:
            texto_precio = selector_precio.text
            match = re.search(r'(\d+[\.,]\d{2})', texto_precio)
            if match:
                precio_str = match.group(1).replace(',', '.')
                precio = float(precio_str)
                print(f"[SCRAPER INFO] Extracción exitosa (Nivel 3 - DOM CSS): -> {precio} EUR")
                return nombre, precio

        match_global = re.search(r'(\d{1,4}[.,]\d{2})\s*(?:€|EUR|euros)', soup.text, re.IGNORECASE)
        if match_global:
            precio_str = match_global.group(1).replace(',', '.')
            precio = float(precio_str)
            print(f"[SCRAPER INFO] Extracción exitosa (Nivel 3 - RegEx Global): -> {precio} EUR")
            return nombre, precio

        print(f"[SCRAPER ERROR] Agotados los 3 niveles de extracción sin resultados en: {url}")
        return None, 0.0

    except Exception as e:
        print(f"[SCRAPER EXCEPTION] Error crítico de ejecución durante scraping de {url}: {e}")
        return None, 0.0