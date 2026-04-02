"""
06 - Enriquecimiento de contactos para top N leads.
Fuentes (en orden de prioridad):
  1. Google Places API (New) — teléfono, web, dirección, rating (gratis: 1000/mes)
  2. Email scraping — extrae emails de los sitios web descubiertos
  3. OCDS contactPoint — contacto del comprador (API, gratis)
  4. Apify Google Maps — fallback si Places API falla (--use-apify)

Resultado: data/filtered/leads_enriched.parquet

Uso:
  python 06_enrich_contacts.py             # Top 100 con Google Places
  python 06_enrich_contacts.py --top 50    # Top 50
  python 06_enrich_contacts.py --use-apify # También usar Apify como fallback
  python 06_enrich_contacts.py --skip-places --use-apify  # Solo Apify
  python 06_enrich_contacts.py --skip-email  # Sin scraping de emails
  python 06_enrich_contacts.py --reset     # Limpiar checkpoint y re-procesar todo

Resiliencia:
  - Checkpoint por empresa en data/filtered/.places_checkpoint.json
  - Al re-ejecutar, retoma desde donde quedó
  - --reset para forzar re-procesamiento completo
"""
from __future__ import annotations

import re
import sys
import time
import json
import unicodedata
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

from config import (FILTERED_DIR, ENRICH_TOP_N, APIFY_TOKEN,
                    GOOGLE_MAPS_API_KEY, OCDS_TENDER_URL,
                    APIFY_GOOGLE_MAPS_ACTOR, redact_secret)
from pipeline_core import load_best_leads_dataframe, recompute_score_combined, recompute_score_total
from pipeline_validation import assert_dataframe_contract
from utils import extraer_rut_de_id, print_header, safe_request


# ============================================================
# Coordenadas centrales por región de Chile (para location bias)
# ============================================================
REGION_COORDS = {
    "Región de Arica y Parinacota": (-18.48, -70.33),
    "Región de Tarapacá": (-20.21, -70.14),
    "Región de Antofagasta": (-23.65, -70.40),
    "Región de Atacama": (-27.37, -70.33),
    "Región de Coquimbo": (-29.95, -71.34),
    "Región de Valparaíso": (-33.05, -71.62),
    "Región Metropolitana de Santiago": (-33.45, -70.65),
    "Región del Libertador General Bernardo O'Higgins": (-34.17, -70.74),
    "Región del Maule": (-35.43, -71.66),
    "Región de Ñuble": (-36.62, -72.10),
    "Región del Biobío": (-36.83, -73.05),
    "Región de La Araucanía": (-38.74, -72.60),
    "Región de Los Ríos": (-39.81, -73.24),
    "Región de Los Lagos": (-41.47, -72.94),
    "Región de Aysén del General Carlos Ibáñez del Campo": (-45.57, -72.07),
    "Región de Magallanes y de la Antártica Chilena": (-53.15, -70.92),
}

# Centro de Chile (fallback)
CHILE_CENTER = (-33.45, -70.65)
CHILE_RADIUS = 50_000.0   # 50 km (máximo permitido por API)
REGION_RADIUS = 50_000.0  # 50 km (máximo permitido por API)

# Places API (New) endpoint
PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

# Campos a pedir (tier Enterprise por internationalPhoneNumber/websiteUri)
PLACES_FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.shortFormattedAddress",
    "places.nationalPhoneNumber",
    "places.internationalPhoneNumber",
    "places.websiteUri",
    "places.googleMapsUri",
    "places.businessStatus",
    "places.rating",
    "places.userRatingCount",
    "places.types",
    "places.primaryType",
])


# ============================================================
# Utilidades de matching
# ============================================================
def _normalize_name(name: str) -> str:
    """Normaliza nombre para comparación: sin acentos, minúscula, sin puntuación."""
    if not name:
        return ""
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    name = re.sub(r"[^a-zA-Z0-9\s]", " ", name.lower())
    return " ".join(name.split())


def _name_similarity(query_name: str, result_name: str) -> float:
    """
    Calcula similitud entre nombre buscado y resultado de Google Places.
    Retorna 0.0-1.0.
    """
    q = set(_normalize_name(query_name).split())
    r = set(_normalize_name(result_name).split())

    # Remover palabras genéricas
    stopwords = {"spa", "ltda", "limitada", "eirl", "sa", "srl", "chile",
                 "constructora", "construcciones", "ingenieria", "servicios",
                 "empresa", "sociedad", "comercial", "de", "y", "la", "el",
                 "los", "las", "del", "en", "con", "e", "s", "a"}
    q_clean = q - stopwords
    r_clean = r - stopwords

    if not q_clean or not r_clean:
        # Sin palabras significativas, comparar sets completos
        q_clean, r_clean = q, r

    if not q_clean or not r_clean:
        return 0.0

    intersection = q_clean & r_clean
    union = q_clean | r_clean
    return len(intersection) / len(union) if union else 0.0


def _get_region_coords(region: str) -> tuple:
    """Obtiene coordenadas para una región, con fuzzy matching."""
    if not region or pd.isna(region):
        return CHILE_CENTER

    region_norm = _normalize_name(region)
    for reg_name, coords in REGION_COORDS.items():
        if _normalize_name(reg_name) in region_norm or region_norm in _normalize_name(reg_name):
            return coords

    # Buscar coincidencia parcial
    for reg_name, coords in REGION_COORDS.items():
        reg_words = set(_normalize_name(reg_name).split())
        query_words = set(region_norm.split())
        if reg_words & query_words - {"region", "de", "del", "la", "y"}:
            return coords

    return CHILE_CENTER


# ============================================================
# Checkpoint management
# ============================================================
def _places_checkpoint_path() -> Path:
    return FILTERED_DIR / ".places_checkpoint.json"


def _load_places_checkpoint() -> dict:
    cp_path = _places_checkpoint_path()
    if cp_path.exists():
        try:
            with open(cp_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"processed_ruts": {}}


def _save_places_checkpoint(checkpoint: dict) -> None:
    cp_path = _places_checkpoint_path()
    with open(cp_path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)


# ============================================================
# 1. Google Places API (New) — Fuente principal
# ============================================================
def _clean_query(text: str) -> str:
    """Limpia texto para query: remueve pipe y caracteres problemáticos."""
    text = text.replace("|", " ").strip()
    # Colapsar espacios múltiples
    text = " ".join(text.split())
    return text


def _search_places(query: str, lat: float, lng: float,
                   radius: float = REGION_RADIUS,
                   max_retries: int = 3) -> Optional[dict]:
    """
    Busca un negocio en Google Places API (New).
    Retorna el dict de respuesta o None. Incluye reintentos.
    """
    query = _clean_query(query)

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": PLACES_FIELD_MASK,
    }
    body = {
        "textQuery": query,
        "languageCode": "es",
        "regionCode": "CL",
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius,
            }
        },
        "pageSize": 3,
    }

    for attempt in range(max_retries):
        try:
            resp = requests.post(PLACES_TEXT_SEARCH_URL, json=body,
                                 headers=headers, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                wait = 5 * (attempt + 1)
                print(f"    Rate limit (429), esperando {wait}s...")
                time.sleep(wait)
                continue
            else:
                # Log error para debug
                err_msg = ""
                try:
                    err_msg = resp.json().get("error", {}).get("message", "")[:80]
                except Exception:
                    err_msg = resp.text[:80]
                if attempt == 0:
                    print(f"    API {resp.status_code}: {err_msg}")
                time.sleep(1 * (attempt + 1))
                continue
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return None
    return None


def _pick_best_match(nombre_empresa: str, places_results: list) -> Optional[dict]:
    """
    De los resultados de Places, elige el que mejor matchea el nombre.
    Retorna None si ninguno supera el threshold.
    """
    if not places_results:
        return None

    best_score = 0.0
    best_place = None

    for place in places_results:
        display = place.get("displayName", {}).get("text", "")
        score = _name_similarity(nombre_empresa, display)

        # Bonus si es contractor/construction
        types = place.get("types", [])
        if any(t in types for t in ["general_contractor", "construction_company",
                                     "contractor", "engineering_consultant"]):
            score += 0.15

        # Bonus si está operacional
        if place.get("businessStatus") == "OPERATIONAL":
            score += 0.05

        if score > best_score:
            best_score = score
            best_place = place

    # Threshold mínimo: al menos 1 palabra significativa en común
    if best_score >= 0.1:
        return best_place

    # Si no hay buen match pero solo hay 1 resultado, aceptar si tiene teléfono
    if len(places_results) == 1 and places_results[0].get("nationalPhoneNumber"):
        return places_results[0]

    return None


def enrich_google_places(leads_df: pd.DataFrame) -> pd.DataFrame:
    """
    Enriquece leads usando Google Places API (New).
    1000 requests Enterprise gratis/mes. Usa ~100 para el top 100.
    """
    print("\n--- Enriquecimiento Google Places API ---")

    if not GOOGLE_MAPS_API_KEY:
        print("  AVISO: No hay GOOGLE_MAPS_API_KEY en .env — saltando")
        return leads_df

    leads_df = leads_df.reset_index(drop=True)

    # Inicializar columnas
    for col in ["gm_telefono", "gm_web", "gm_direccion", "gm_rating",
                "gm_nombre_maps", "gm_maps_url", "gm_business_status"]:
        if col not in leads_df.columns:
            leads_df[col] = None

    # Cargar checkpoint
    checkpoint = _load_places_checkpoint()
    processed = checkpoint["processed_ruts"]

    # Restaurar datos del checkpoint
    restored = 0
    for df_idx, row in leads_df.iterrows():
        rut = row["rut"]
        if rut in processed:
            cached = processed[rut]
            for field, col in [("phone", "gm_telefono"), ("website", "gm_web"),
                               ("address", "gm_direccion"), ("rating", "gm_rating"),
                               ("maps_name", "gm_nombre_maps"),
                               ("maps_url", "gm_maps_url"),
                               ("status", "gm_business_status")]:
                if cached.get(field):
                    leads_df.at[df_idx, col] = cached[field]
            restored += 1

    if restored:
        phones_restored = leads_df["gm_telefono"].notna().sum()
        print(f"  Checkpoint: {restored} restaurados ({phones_restored} con teléfono)")

    # Procesar pendientes
    pending = [(idx, row) for idx, row in leads_df.iterrows()
               if row["rut"] not in processed]

    if not pending:
        print("  Todos los leads ya procesados (checkpoint completo)")
        return leads_df

    print(f"  Pendientes: {len(pending)} empresas")
    print(f"  API key: {redact_secret(GOOGLE_MAPS_API_KEY)}")

    found_total = leads_df["gm_telefono"].notna().sum()
    errors = 0

    for i, (df_idx, row) in enumerate(pending):
        rut = row["rut"]
        nombre = row.get("nombre", "")
        region = row.get("region", "Chile")

        if pd.isna(nombre) or not nombre:
            nombre = f"empresa {rut}"
        if pd.isna(region):
            region = ""

        # Separar nombre formal de nombre comercial (formato: "FORMAL | COMERCIAL")
        parts = [p.strip() for p in nombre.split("|")]
        nombre_buscar = parts[0]  # Usar nombre formal primero
        nombre_comercial = parts[1] if len(parts) > 1 else ""

        # Obtener coordenadas de la región
        lat, lng = _get_region_coords(region)

        # Estrategia de búsqueda: intentar con variantes
        queries = [
            f"{nombre_buscar} {region} Chile",
        ]
        if nombre_comercial:
            queries.insert(0, f"{nombre_comercial} {region} Chile")

        result_place = None
        for query in queries:
            data = _search_places(query, lat, lng)
            if data and data.get("places"):
                result_place = _pick_best_match(nombre, data["places"])
                if result_place:
                    break
            time.sleep(0.5)  # Rate limit conservador

        # Si no encontró con región, intentar solo nombre + Chile
        if not result_place:
            data = _search_places(f"{nombre_buscar} Chile", *CHILE_CENTER,
                                  radius=CHILE_RADIUS)
            if data and data.get("places"):
                result_place = _pick_best_match(nombre, data["places"])
            time.sleep(0.5)

        # Extraer datos del resultado
        cached_entry = {"searched": True}

        if result_place:
            phone = (result_place.get("nationalPhoneNumber") or
                     result_place.get("internationalPhoneNumber"))
            website = result_place.get("websiteUri")
            address = result_place.get("formattedAddress")
            rating = result_place.get("rating")
            maps_name = result_place.get("displayName", {}).get("text")
            maps_url = result_place.get("googleMapsUri")
            status = result_place.get("businessStatus")

            if phone:
                leads_df.at[df_idx, "gm_telefono"] = phone
                cached_entry["phone"] = phone
                found_total += 1
            if website:
                leads_df.at[df_idx, "gm_web"] = website
                cached_entry["website"] = website
            if address:
                leads_df.at[df_idx, "gm_direccion"] = address
                cached_entry["address"] = address
            if rating:
                leads_df.at[df_idx, "gm_rating"] = rating
                cached_entry["rating"] = rating
            if maps_name:
                leads_df.at[df_idx, "gm_nombre_maps"] = maps_name
                cached_entry["maps_name"] = maps_name
            if maps_url:
                leads_df.at[df_idx, "gm_maps_url"] = maps_url
                cached_entry["maps_url"] = maps_url
            if status:
                leads_df.at[df_idx, "gm_business_status"] = status
                cached_entry["status"] = status

        # Guardar en checkpoint (solo si encontró algo o la búsqueda fue exitosa)
        if result_place is not None or cached_entry.get("searched"):
            processed[rut] = cached_entry
        # Si no encontró nada Y hubo error de API, NO marcar como processed para reintentar
        elif result_place is None and not cached_entry.get("searched"):
            pass  # skip checkpoint — será reintentado
        else:
            processed[rut] = cached_entry

        # Checkpoint cada 10 empresas
        if (i + 1) % 10 == 0:
            checkpoint["processed_ruts"] = processed
            _save_places_checkpoint(checkpoint)
            print(f"  [{i+1}/{len(pending)}] teléfonos: {found_total}, "
                  f"checkpoint guardado")

    # Checkpoint final
    checkpoint["processed_ruts"] = processed
    _save_places_checkpoint(checkpoint)

    webs = leads_df["gm_web"].notna().sum()
    addrs = leads_df["gm_direccion"].notna().sum()
    print(f"\n  Google Places completado:")
    print(f"    Teléfonos: {found_total}/{len(leads_df)}")
    print(f"    Websites:  {webs}/{len(leads_df)}")
    print(f"    Direcciones: {addrs}/{len(leads_df)}")

    return leads_df


# ============================================================
# 2. Email scraping desde websites descubiertos
# ============================================================
EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE
)

# Emails a ignorar (genéricos, no útiles para contacto)
BLACKLIST_EMAILS = {
    "info@", "contacto@", "noreply@", "no-reply@",
    "webmaster@", "admin@", "root@", "postmaster@",
    "example@", "test@", "support@", "ventas@",
}

CONTACT_PATHS = ["", "/contacto", "/contact", "/nosotros", "/about",
                 "/quienes-somos", "/empresa"]


def _extract_emails_from_html(html: str) -> list:
    """Extrae emails de HTML, filtrando basura."""
    emails = EMAIL_REGEX.findall(html)
    result = []
    seen = set()
    for email in emails:
        email = email.lower().strip()
        if email in seen:
            continue
        seen.add(email)
        # Filtrar extensiones de archivo
        if any(email.endswith(ext) for ext in [".png", ".jpg", ".gif", ".svg",
                                                ".css", ".js", ".webp"]):
            continue
        # Filtrar dominios de tracking/framework
        if any(d in email for d in ["wixpress", "sentry", "webpack",
                                     "cloudflare", "googleapis", "gstatic"]):
            continue
        result.append(email)
    return result


def _prioritize_emails(emails: list, empresa_nombre: str) -> Optional[str]:
    """
    Prioriza emails encontrados:
    1. Emails con nombre de la empresa en el dominio
    2. Emails de gerencia/contacto personal
    3. Emails genéricos (info@, contacto@)
    """
    if not emails:
        return None

    nombre_norm = _normalize_name(empresa_nombre)
    nombre_words = set(nombre_norm.split()) - {"spa", "ltda", "sa", "eirl",
                                                 "de", "y", "la", "el",
                                                 "constructora", "construcciones"}

    # Score each email
    scored = []
    for email in emails:
        score = 0
        domain = email.split("@")[1] if "@" in email else ""
        local = email.split("@")[0] if "@" in email else ""
        domain_norm = _normalize_name(domain.split(".")[0])

        # Bonus: dominio coincide con nombre empresa
        if any(w in domain_norm for w in nombre_words if len(w) > 3):
            score += 10

        # Bonus: es email personal (nombre.apellido@)
        if "." in local and not any(local.startswith(bl.split("@")[0])
                                     for bl in BLACKLIST_EMAILS):
            score += 5

        # Penalizar: es genérico
        if any(local.startswith(bl.split("@")[0]) for bl in BLACKLIST_EMAILS):
            score -= 2

        # Penalizar: gmail/hotmail (menos profesional para empresa)
        if domain in ["gmail.com", "hotmail.com", "yahoo.com", "outlook.com"]:
            score -= 1

        scored.append((score, email))

    scored.sort(key=lambda x: -x[0])
    return scored[0][1]


def scrape_emails_from_websites(leads_df: pd.DataFrame) -> pd.DataFrame:
    """
    Para cada lead con website, intenta extraer un email de contacto
    visitando la web y sus páginas de contacto.
    """
    print("\n--- Scraping emails desde websites ---")

    if "gm_web" not in leads_df.columns:
        print("  No hay websites descubiertos — saltando")
        return leads_df

    if "gm_email" not in leads_df.columns:
        leads_df["gm_email"] = None

    leads_with_web = leads_df[leads_df["gm_web"].notna()]
    if leads_with_web.empty:
        print("  No hay websites para scraper — saltando")
        return leads_df

    print(f"  Websites a revisar: {len(leads_with_web)}")
    found = 0

    for df_idx, row in leads_with_web.iterrows():
        website = str(row["gm_web"]).strip().rstrip("/")
        nombre = row.get("nombre", "")

        if not website.startswith("http"):
            website = "https://" + website

        all_emails = []

        for path in CONTACT_PATHS:
            url = website + path
            try:
                resp = requests.get(url, timeout=8, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/120.0.0.0 Safari/537.36"
                }, allow_redirects=True)
                if resp.status_code == 200:
                    emails = _extract_emails_from_html(resp.text)
                    all_emails.extend(emails)
            except requests.RequestException:
                continue
            time.sleep(0.3)

            # Si ya encontramos emails, no seguir buscando
            if all_emails:
                break

        best_email = _prioritize_emails(all_emails, nombre)
        if best_email:
            leads_df.at[df_idx, "gm_email"] = best_email
            found += 1

    print(f"  Emails encontrados: {found}/{len(leads_with_web)}")
    return leads_df


# ============================================================
# 3. OCDS contactPoint (existente, bajo hit rate)
# ============================================================
def enrich_ocds_batch(leads_df: pd.DataFrame, tenderers_path) -> pd.DataFrame:
    """Busca contactPoint en OCDS para las licitaciones recientes de cada lead."""
    print("\n--- Enriquecimiento OCDS (contactPoint) ---")

    if not tenderers_path.exists():
        print("  AVISO: No hay tenderers filtrados, saltando OCDS")
        return leads_df

    tenderers = pd.read_parquet(tenderers_path)

    str_cols = tenderers.select_dtypes(include="object").columns
    tenderers["_rut"] = tenderers[str_cols].apply(
        lambda row: next((r for v in row if (r := extraer_rut_de_id(str(v)))), None),
        axis=1
    )
    tenderers = tenderers[tenderers["_rut"].notna()]

    tender_id_col = None
    for col in tenderers.columns:
        if any(k in col.lower() for k in ["tender_id", "ocid", "release"]):
            tender_id_col = col
            break
    if tender_id_col is None:
        tender_id_col = tenderers.columns[0]

    contacts_found = 0
    for col in ["ocds_contacto", "ocds_email", "ocds_telefono"]:
        if col not in leads_df.columns:
            leads_df[col] = None

    for i, (idx, row) in enumerate(leads_df.iterrows()):
        rut = row["rut"]
        empresa_tenders = tenderers[tenderers["_rut"] == rut][tender_id_col].unique()
        if len(empresa_tenders) == 0:
            continue

        tender_code = str(empresa_tenders[0]).strip()
        url = OCDS_TENDER_URL.format(codigo=tender_code)
        resp = safe_request(url, max_retries=2, delay=1)
        if resp is None:
            continue

        try:
            data = resp.json()
            releases = data.get("releases", [data]) if isinstance(data, dict) else []
            for release in releases:
                tender = release.get("tender", {})
                contact = tender.get("contactPoint", {})
                if contact:
                    leads_df.at[idx, "ocds_contacto"] = contact.get("name", "")
                    leads_df.at[idx, "ocds_email"] = contact.get("email", "")
                    leads_df.at[idx, "ocds_telefono"] = contact.get("telephone", "")
                    contacts_found += 1
                    break

            if not leads_df.at[idx, "ocds_contacto"]:
                for release in releases:
                    for party in release.get("parties", []):
                        party_id = str(party.get("id", ""))
                        if rut in party_id:
                            contact = party.get("contactPoint", {})
                            if contact:
                                leads_df.at[idx, "ocds_contacto"] = contact.get("name", "")
                                leads_df.at[idx, "ocds_email"] = contact.get("email", "")
                                leads_df.at[idx, "ocds_telefono"] = contact.get("telephone", "")
                                contacts_found += 1
                                break
        except (json.JSONDecodeError, KeyError):
            pass

        time.sleep(0.5)
        if (i + 1) % 20 == 0:
            print(f"  Procesados {i+1}/{len(leads_df)} — contactos: {contacts_found}")

    print(f"  Contactos OCDS encontrados: {contacts_found}/{len(leads_df)}")
    return leads_df


# ============================================================
# 4. Apify fallback (existente, por si se necesita)
# ============================================================
def _apify_checkpoint_path() -> Path:
    return FILTERED_DIR / ".apify_checkpoint.json"


def _load_apify_checkpoint() -> dict:
    cp_path = _apify_checkpoint_path()
    if cp_path.exists():
        try:
            with open(cp_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"processed_ruts": {}, "last_batch_done": -1}


def _save_apify_checkpoint(checkpoint: dict) -> None:
    cp_path = _apify_checkpoint_path()
    with open(cp_path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)


def _is_credit_error(error) -> bool:
    msg = str(error).lower()
    return any(k in msg for k in ["402", "payment required", "insufficient",
                                   "credit", "balance", "usage limit",
                                   "exceeded", "quota", "plan limit"])


def enrich_apify_google_maps(leads_df: pd.DataFrame) -> pd.DataFrame:
    """Busca info de contacto en Google Maps via Apify (fallback)."""
    print("\n--- Enriquecimiento Google Maps (Apify) — fallback ---")

    token = APIFY_TOKEN
    if "--apify-token" in sys.argv:
        idx = sys.argv.index("--apify-token")
        if idx + 1 < len(sys.argv):
            token = sys.argv[idx + 1]

    if not token:
        print("  AVISO: No hay APIFY_TOKEN — saltando")
        return leads_df

    # Solo buscar empresas que NO tienen teléfono de Places API
    mask_sin_tel = leads_df["gm_telefono"].isna()
    sin_telefono = mask_sin_tel.sum()
    if sin_telefono == 0:
        print("  Todos ya tienen teléfono de Places API — saltando Apify")
        return leads_df

    print(f"  Buscando {sin_telefono} empresas sin teléfono...")

    for col in ["gm_telefono", "gm_web", "gm_direccion", "gm_rating"]:
        if col not in leads_df.columns:
            leads_df[col] = None

    checkpoint = _load_apify_checkpoint()
    processed_ruts = checkpoint["processed_ruts"]

    # Restaurar checkpoint
    restored = 0
    for df_idx, row in leads_df.iterrows():
        rut = row["rut"]
        if rut in processed_ruts and mask_sin_tel[df_idx]:
            cached = processed_ruts[rut]
            if cached.get("phone"):
                leads_df.at[df_idx, "gm_telefono"] = cached["phone"]
            if cached.get("website") and pd.isna(leads_df.at[df_idx, "gm_web"]):
                leads_df.at[df_idx, "gm_web"] = cached["website"]
            if cached.get("address") and pd.isna(leads_df.at[df_idx, "gm_direccion"]):
                leads_df.at[df_idx, "gm_direccion"] = cached["address"]
            if cached.get("rating") and pd.isna(leads_df.at[df_idx, "gm_rating"]):
                leads_df.at[df_idx, "gm_rating"] = cached["rating"]
            restored += 1

    if restored:
        print(f"  Checkpoint Apify: {restored} restaurados")

    # Preparar queries solo para leads sin teléfono y no procesados en Apify
    queries = []
    query_to_idx = {}
    query_to_rut = {}
    for df_idx, row in leads_df.iterrows():
        rut = row["rut"]
        if not mask_sin_tel[df_idx] or rut in processed_ruts:
            continue
        nombre = row.get("nombre", "")
        if pd.isna(nombre) or not nombre:
            nombre = f"empresa RUT {rut}"
        region = row.get("region", "Chile")
        if pd.isna(region):
            region = "Chile"
        q = f"constructora {nombre} {region}"
        queries.append(q)
        query_to_idx[q] = df_idx
        query_to_rut[q] = rut

    if not queries:
        print("  Todos procesados (checkpoint + Places API)")
        return leads_df

    print(f"  Queries Apify pendientes: {len(queries)}")

    try:
        from apify_client import ApifyClient
        client = ApifyClient(token)
        batch_size = 20
        enriched = restored

        for batch_start in range(0, len(queries), batch_size):
            batch_queries = queries[batch_start:batch_start + batch_size]
            batch_num = batch_start // batch_size + 1
            total_batches = (len(queries) + batch_size - 1) // batch_size

            run_input = {
                "searchStringsArray": batch_queries,
                "maxCrawledPlacesPerSearch": 1,
                "language": "es",
                "countryCode": "cl",
            }

            print(f"  Batch {batch_num}/{total_batches}: {len(batch_queries)} empresas...")

            try:
                run = client.actor(APIFY_GOOGLE_MAPS_ACTOR).call(run_input=run_input)
                results = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            except Exception as batch_err:
                if _is_credit_error(batch_err):
                    print(f"\n  *** CREDITOS APIFY AGOTADOS ***")
                    break
                raise

            for result in results:
                search_str = result.get("searchString") or result.get("query") or ""
                idx_found = query_to_idx.get(search_str)
                rut = query_to_rut.get(search_str)
                if idx_found is None:
                    for q, q_idx in query_to_idx.items():
                        if q in search_str or search_str in q:
                            idx_found = q_idx
                            rut = query_to_rut.get(q)
                            break
                if idx_found is None:
                    continue

                cached_entry = {}
                if result.get("phone"):
                    leads_df.at[idx_found, "gm_telefono"] = result["phone"]
                    cached_entry["phone"] = result["phone"]
                    enriched += 1
                if result.get("website"):
                    leads_df.at[idx_found, "gm_web"] = result["website"]
                    cached_entry["website"] = result["website"]
                if result.get("address"):
                    leads_df.at[idx_found, "gm_direccion"] = result["address"]
                    cached_entry["address"] = result["address"]
                if result.get("totalScore"):
                    leads_df.at[idx_found, "gm_rating"] = result["totalScore"]
                    cached_entry["rating"] = result["totalScore"]
                if rut:
                    processed_ruts[rut] = cached_entry

            for q in batch_queries:
                rut = query_to_rut.get(q)
                if rut and rut not in processed_ruts:
                    processed_ruts[rut] = {}

            checkpoint["processed_ruts"] = processed_ruts
            _save_apify_checkpoint(checkpoint)
            time.sleep(2)

        print(f"  Apify fallback: {enriched} adicionales")

    except ImportError:
        print("  AVISO: apify-client no instalado — saltando")
    except Exception as e:
        checkpoint["processed_ruts"] = processed_ruts
        _save_apify_checkpoint(checkpoint)
        print(f"  Error Apify: {e}")

    return leads_df


# ============================================================
# 5. Consolidación
# ============================================================
def consolidate_contacts(df: pd.DataFrame) -> pd.DataFrame:
    """Consolida contactos de múltiples fuentes en campos unificados."""
    print("\n--- Consolidando contactos ---")

    # Teléfono: Google Places > Apify > OCDS
    df["telefono"] = df.get("gm_telefono")
    if "gm_telefono" in df.columns:
        df["telefono"] = df["gm_telefono"]
    mask_no_tel = df["telefono"].isna()
    if "ocds_telefono" in df.columns:
        df.loc[mask_no_tel, "telefono"] = df.loc[mask_no_tel, "ocds_telefono"]

    # Email: scraping web > OCDS
    df["email"] = df.get("gm_email")
    if "gm_email" in df.columns:
        df["email"] = df["gm_email"]
    mask_no_email = df["email"].isna()
    if "ocds_email" in df.columns:
        df.loc[mask_no_email, "email"] = df.loc[mask_no_email, "ocds_email"]

    # Web: Google Places
    df["web"] = df["gm_web"] if "gm_web" in df.columns else None

    # Contacto: OCDS
    df["contacto_nombre"] = df["ocds_contacto"] if "ocds_contacto" in df.columns else None

    # Dirección: Google Places
    df["direccion"] = df["gm_direccion"] if "gm_direccion" in df.columns else None

    # score_digital basado en presencia real
    has_web = df["web"].notna()
    has_email = df["email"].notna()
    has_phone = df["telefono"].notna()
    df["score_digital"] = 70  # sin presencia = más oportunidad
    df.loc[has_phone & ~has_web & ~has_email, "score_digital"] = 60
    df.loc[(has_web | has_email) & ~(has_web & has_email), "score_digital"] = 50
    df.loc[has_web & has_email, "score_digital"] = 30

    # Recalcular scores
    if "score_actividad" in df.columns:
        df = recompute_score_total(df)
        print(f"  score_total recalculado: mean={df['score_total'].mean():.1f}")

    if "score_total" in df.columns:
        df = recompute_score_combined(df)
        print(f"  score_combined recalculado: mean={df['score_combined'].mean():.1f}")

    # Stats
    print(f"\n  === RESUMEN CONTACTOS ===")
    print(f"  Con teléfono: {df['telefono'].notna().sum()}/{len(df)}")
    print(f"  Con email:    {df['email'].notna().sum()}/{len(df)}")
    print(f"  Con web:      {df['web'].notna().sum()}/{len(df)}")
    print(f"  Con dirección: {df['direccion'].notna().sum()}/{len(df)}")
    print(f"  Con contacto: {df['contacto_nombre'].notna().sum()}/{len(df)}")

    return df


# ============================================================
# Main
# ============================================================
def main():
    print_header("06 — Enriquecimiento de Contactos")

    # Flags
    skip_places = "--skip-places" in sys.argv
    skip_email = "--skip-email" in sys.argv
    use_apify = "--use-apify" in sys.argv
    reset = "--reset" in sys.argv

    if reset:
        for cp in [_places_checkpoint_path(), _apify_checkpoint_path()]:
            if cp.exists():
                cp.unlink()
                print(f"  Checkpoint eliminado: {cp.name}")

    # Seleccionar fuente de leads
    try:
        _, ranked_path = load_best_leads_dataframe(
            priority=("leads_ml_ranked.parquet", "leads_ranked.parquet")
        )
    except FileNotFoundError:
        print("ERROR: No existe leads_ranked ni leads_ml_ranked")
        print("Ejecuta primero: python 05_score_leads.py")
        sys.exit(1)

    top_n = ENRICH_TOP_N
    if "--top" in sys.argv:
        idx = sys.argv.index("--top")
        if idx + 1 >= len(sys.argv):
            print("ERROR: --top requiere un valor numérico")
            sys.exit(1)
        try:
            top_n = int(sys.argv[idx + 1])
        except ValueError:
            print(f"ERROR: --top requiere un número, se recibió '{sys.argv[idx + 1]}'")
            sys.exit(1)

    df = pd.read_parquet(ranked_path)
    print(f"Fuente: {ranked_path.name}")
    leads = df.head(top_n).copy()
    print(f"Enriqueciendo top {len(leads)} leads...")

    # 1. Google Places API (principal)
    if not skip_places:
        leads = enrich_google_places(leads)
    else:
        print("\n  Google Places saltado (--skip-places)")

    # 2. Email scraping
    if not skip_email:
        leads = scrape_emails_from_websites(leads)
    else:
        print("\n  Email scraping saltado (--skip-email)")

    # 3. OCDS contactPoint
    tenderers_path = FILTERED_DIR / "tenderers_construction.parquet"
    leads = enrich_ocds_batch(leads, tenderers_path)

    # 4. Apify fallback (solo si se pide)
    if use_apify:
        leads = enrich_apify_google_maps(leads)

    # 5. Consolidar
    leads = consolidate_contacts(leads)

    # Guardar
    out_path = FILTERED_DIR / "leads_enriched.parquet"
    assert_dataframe_contract(leads, "leads_enriched")
    leads.to_parquet(out_path, index=False)

    print(f"\n{'='*60}")
    print(f"  LEADS ENRIQUECIDOS")
    print(f"{'='*60}")
    print(f"  Archivo: {out_path}")
    print(f"  Total leads: {len(leads)}")
    print(f"  Con teléfono: {leads['telefono'].notna().sum()}")
    print(f"  Con email:    {leads['email'].notna().sum()}")
    print(f"  Con web:      {leads['web'].notna().sum()}")
    print(f"  Con dirección: {leads['direccion'].notna().sum()}")

    print(f"\nSiguiente paso: python 07_export_output.py")


if __name__ == "__main__":
    main()
