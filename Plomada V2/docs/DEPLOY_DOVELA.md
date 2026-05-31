# Deploy Dovela en GitHub Pages

Estado preparado:

- Landing publica: `Plomada V2/site/index.html`.
- Dominio custom: `dovela.cl`.
- Archivo GitHub Pages: `Plomada V2/site/CNAME`.
- Sitemap: `https://dovela.cl/sitemap.xml`.
- Robots: `https://dovela.cl/robots.txt`.
- Contacto publico en landing: `hola@dovela.cl`.
- Workflow listo: `.github/workflows/deploy-dovela-pages.yml`.

## Publicar en GitHub Pages

1. Subir el repo a GitHub.
2. En GitHub: Settings > Pages.
3. En Source, elegir `GitHub Actions`.
4. Ejecutar el workflow `Deploy Dovela to GitHub Pages` o hacer push a `main`/`master`.
5. En Settings > Pages > Custom domain, confirmar `dovela.cl`.
6. Activar `Enforce HTTPS` cuando GitHub permita marcarlo.

El workflow publica solamente `Plomada V2/site`, no el resto del repo.

## DNS en NIC Chile

Para `dovela.cl` como dominio apex/root, configurar estos registros A:

| Tipo | Nombre | Valor |
| --- | --- | --- |
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |

Para `www.dovela.cl`, configurar un CNAME:

| Tipo | Nombre | Valor |
| --- | --- | --- |
| CNAME | www | `kcortes765.github.io` |

El remote local actual apunta a `https://github.com/kcortes765/licitaciones-chile.git`, por eso el target para `www` queda como `kcortes765.github.io`.

Opcional si NIC permite IPv6:

| Tipo | Nombre | Valor |
| --- | --- | --- |
| AAAA | @ | 2606:50c0:8000::153 |
| AAAA | @ | 2606:50c0:8001::153 |
| AAAA | @ | 2606:50c0:8002::153 |
| AAAA | @ | 2606:50c0:8003::153 |

## Correo

El correo lo configura Sebastian en Google Workspace.

No tocar MX/SPF/DKIM/DMARC desde esta guia, salvo que sea para copiar los valores que entregue Google Workspace.

La landing ya usa `hola@dovela.cl` como contacto publico.

## Checklist final

- `https://dovela.cl` abre la landing.
- `https://www.dovela.cl` abre o redirige correctamente.
- HTTPS activo.
- `https://dovela.cl/sitemap.xml` responde.
- `https://dovela.cl/robots.txt` responde.
- El boton "Escribir a Dovela" abre `hola@dovela.cl`.
- No hay menciones publicas a Plomada.
- No hay datos internos de prospectos, scoring, API o correo pendiente.
