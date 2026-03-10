"""
Monitor de Licitaciones de Obras - MercadoPublico.cl
=====================================================
Filtra licitaciones de construccion/obras publicas y genera reporte.

Uso:
  python monitor_licitaciones.py                  # Licitaciones de hoy
  python monitor_licitaciones.py --fecha 03032026 # Fecha especifica (ddmmaaaa)
  python monitor_licitaciones.py --detalle 2405-31-LP26  # Detalle de 1 licitacion
  python monitor_licitaciones.py --dias 7         # Ultimos 7 dias

Requiere: ticket de API de MercadoPublico
  - Solicitar en: api@chilecompra.cl
  - Configurar en .env: MERCADO_PUBLICO_TICKET=tu-ticket-aqui
"""

import json
import os
import urllib.request
import urllib.error
import sys
import time
from datetime import datetime, timedelta

# === CONFIGURACION ===
TICKET = os.getenv("MERCADO_PUBLICO_TICKET", "")
BASE_URL = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"

# Palabras clave para filtrar obras/construccion
KW_INCLUIR = [
    'construcci', 'obra', 'infraestructura', 'paviment', 'vialidad', 'puente',
    'edifici', 'mejoramiento', 'reposici', 'conservaci', 'habilitaci',
    'demolici', 'estructur', 'arquitect'
]
KW_EXCLUIR = [
    'vehicul', 'neumatic', 'dental', 'medic', 'telefon', 'azure', 'internet',
    'kinesiol', 'reactivo', 'cocina', 'gas ', 'agua caliente', 'hiperhipo',
    'compresor', 'seguro de', 'incubador', 'limpieza', 'impresora'
]

ESTADOS = {5: 'Publicada', 6: 'Cerrada', 7: 'Desierta', 8: 'Adjudicada', 18: 'Revocada', 19: 'Suspendida'}
TIPOS = {'L1': 'Menor (<100 UTM)', 'LE': 'Entre (100-1000 UTM)', 'LP': 'Mayor (>1000 UTM)', 'LR': 'Restringida'}


def api_call(params, max_retries=3):
    """Llamada a la API con reintentos."""
    params['ticket'] = TICKET
    query = '&'.join(f'{k}={v}' for k, v in params.items())
    url = f'{BASE_URL}?{query}'

    for i in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if 'Codigo' in data and data['Codigo'] == 10500:
                    print(f"  Rate limit, reintentando en {5*(i+1)}s...")
                    time.sleep(5 * (i + 1))
                    continue
                return data
        except urllib.error.URLError as e:
            print(f"  Error de conexion: {e}")
            time.sleep(3)
    return None


def es_obra(nombre):
    """Filtra licitaciones de obras/construccion reales."""
    n = nombre.lower()
    if not any(kw in n for kw in KW_INCLUIR):
        return False
    if any(ex in n for ex in KW_EXCLUIR):
        return False
    return True


def tipo_licitacion(codigo):
    """Extrae el tipo de licitacion del codigo."""
    for tipo in ['LP', 'LE', 'LR', 'L1']:
        if f'-{tipo}' in codigo:
            return tipo
    return 'Otro'


def listar_por_fecha(fecha_str=None):
    """Lista licitaciones de obras para una fecha."""
    if fecha_str is None:
        fecha_str = datetime.now().strftime('%d%m%Y')

    print(f"\nConsultando licitaciones fecha {fecha_str}...")
    data = api_call({'fecha': fecha_str})

    if not data or 'Listado' not in data:
        print("Error: no se pudo obtener data")
        return []

    print(f"Total licitaciones: {data['Cantidad']}")

    obras = [lic for lic in data['Listado'] if es_obra(lic['Nombre'])]
    abiertas = [o for o in obras if o['CodigoEstado'] == 5]

    print(f"Obras/construccion: {len(obras)} (abiertas: {len(abiertas)})")
    print()

    # Clasificar por tipo
    por_tipo = {}
    for o in abiertas:
        t = tipo_licitacion(o['CodigoExterno'])
        por_tipo.setdefault(t, []).append(o)

    for tipo in ['LP', 'LE', 'LR', 'L1', 'Otro']:
        lics = por_tipo.get(tipo, [])
        if not lics:
            continue
        desc = TIPOS.get(tipo, tipo)
        print(f"--- {tipo} - {desc} ({len(lics)}) ---")
        for o in lics:
            cierre = o['FechaCierre'][:10] if o.get('FechaCierre') else 'N/A'
            print(f"  [{o['CodigoExterno']}] {o['Nombre']}")
            print(f"    Cierre: {cierre}")
        print()

    return abiertas


def detalle_licitacion(codigo):
    """Obtiene detalle completo de una licitacion."""
    print(f"\nObteniendo detalle de {codigo}...")
    data = api_call({'codigo': codigo})

    if not data or 'Listado' not in data or not data['Listado']:
        print("Error: no se encontro la licitacion")
        return None

    lic = data['Listado'][0]

    print(f"\n{'='*60}")
    print(f"LICITACION: {lic.get('Nombre', 'N/A')}")
    print(f"{'='*60}")
    print(f"Codigo: {lic.get('CodigoExterno', 'N/A')}")
    print(f"Estado: {ESTADOS.get(lic.get('CodigoEstado'), lic.get('CodigoEstado'))}")
    print(f"Descripcion: {lic.get('Descripcion', 'N/A')[:500]}")
    print(f"Fecha publicacion: {lic.get('FechaPublicacion', 'N/A')}")
    print(f"Fecha cierre: {lic.get('FechaCierre', 'N/A')}")
    print(f"Monto estimado: {lic.get('MontoEstimado', 'N/A')} {lic.get('UnidadMonetaria', '')}")
    print(f"Tipo: {lic.get('Tipo', 'N/A')}")

    if lic.get('Comprador'):
        comp = lic['Comprador']
        print(f"\nCOMPRADOR:")
        print(f"  Organismo: {comp.get('NombreOrganismo', 'N/A')}")
        print(f"  Unidad: {comp.get('NombreUnidad', 'N/A')}")
        print(f"  Region: {comp.get('RegionUnidad', 'N/A')}")
        print(f"  Comuna: {comp.get('ComunaUnidad', 'N/A')}")

    if lic.get('Items') and lic['Items'].get('Listado'):
        print(f"\nITEMS ({len(lic['Items']['Listado'])}):")
        for item in lic['Items']['Listado']:
            print(f"  - {item.get('NombreProducto', 'N/A')}")
            print(f"    Cantidad: {item.get('Cantidad', 'N/A')} | Unidad: {item.get('UnidadMedida', 'N/A')}")

    # Guardar JSON completo
    filename = f"detalle_{codigo.replace('-','_')}.json"
    filepath = r"C:\Seba\Nueva carpeta (2)\\" + filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(lic, f, indent=2, ensure_ascii=False)
    print(f"\nJSON completo guardado en: {filename}")

    return lic


def buscar_varios_dias(dias=7):
    """Busca licitaciones de los ultimos N dias."""
    todas = []
    codigos_vistos = set()

    for i in range(dias):
        fecha = datetime.now() - timedelta(days=i)
        fecha_str = fecha.strftime('%d%m%Y')
        print(f"\n--- Dia {fecha.strftime('%Y-%m-%d')} ---")

        abiertas = listar_por_fecha(fecha_str)
        for o in abiertas:
            if o['CodigoExterno'] not in codigos_vistos:
                codigos_vistos.add(o['CodigoExterno'])
                todas.append(o)

        time.sleep(3)  # Esperar entre llamadas

    print(f"\n{'='*60}")
    print(f"RESUMEN: {len(todas)} licitaciones unicas de obras abiertas en {dias} dias")

    return todas


if __name__ == '__main__':
    args = sys.argv[1:]

    if '--detalle' in args:
        idx = args.index('--detalle')
        codigo = args[idx + 1]
        detalle_licitacion(codigo)
    elif '--dias' in args:
        idx = args.index('--dias')
        dias = int(args[idx + 1])
        buscar_varios_dias(dias)
    elif '--fecha' in args:
        idx = args.index('--fecha')
        fecha = args[idx + 1]
        listar_por_fecha(fecha)
    else:
        listar_por_fecha()
