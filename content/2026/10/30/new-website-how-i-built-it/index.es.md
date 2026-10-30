---
title: "Mi nueva web: cómo la hice"
date: "2026-10-30T18:00:00-04:00"
slug: mi-nueva-web-como-la-hice
description: "Hugo + Hextra en Netlify, tres idiomas y todas las herramientas y tareas gestionadas con mise — basada en el blog de Fabio Akita, con Python en lugar de Ruby."
tags:
- blog
- desarrollo-de-software
featured: true
draft: false
---

Esta web está hecha igual que el [blog de Fabio Akita](https://akitaonrails.com/2025/09/10/meu-novo-blog-como-eu-fiz/) ([código](https://github.com/akitaonrails/akitaonrails.github.io)), con dos cambios: los scripts de apoyo están en **Python** en lugar de Ruby, y **[mise](https://mise.jdx.dev)** lo controla todo: versiones de las herramientas, el entorno de Python y todas las tareas.

## El stack

- **[Hugo](https://gohugo.io)** convierte Markdown en HTML estático. Sin base de datos ni servidor.
- **[Hextra](https://imfing.github.io/hextra/)** es el tema: modo oscuro, búsqueda (`Ctrl K`), etiquetas, RSS y resaltado de código.
- **[Netlify](https://www.netlify.com)** compila y publica con cada push a `main`.
- **mise** fija las versiones de Hugo, Go y Python, así que mi portátil, GitHub Actions y Netlify usan exactamente las mismas.

## Tres idiomas

Cada entrada es una carpeta con un fichero por idioma:

```text
content/2026/10/30/new-website-how-i-built-it/
├── index.en.md      → /en/2026/10/30/my-new-website-how-i-built-it/
├── index.es.md      → /es/2026/10/30/mi-nueva-web-como-la-hice/
└── index.pt-br.md   → /pt-br/2026/10/30/meu-novo-site-como-eu-fiz/
```

Hugo enlaza las traducciones, así que el selector de idioma te lleva a la misma entrada.

## El flujo de trabajo

```bash
mise install                 # Hugo, Go, Python
mise run setup               # dependencias de Python
mise run new "Título"        # crea los 3 ficheros como borradores
mise run tags:search "ia"    # reutilizar etiquetas existentes
mise run dev                 # http://localhost:1313/es/
mise run check               # lo mismo que la CI: etiquetas, índices, tests, build
git push                     # Netlify publica
```

La portada y el archivo los genera `scripts/generate_index.py` (el `generate_index.rb` de Akita, portado), y `scripts/tag_catalog.py` mantiene las etiquetas coherentes en los tres idiomas.
