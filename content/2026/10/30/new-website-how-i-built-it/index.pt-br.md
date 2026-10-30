---
title: "Meu novo site — como eu fiz"
date: "2026-10-30T18:00:00-04:00"
slug: meu-novo-site-como-eu-fiz
description: "Hugo + Hextra na Netlify, três idiomas e todas as ferramentas e tarefas controladas pelo mise — baseado no blog do Fabio Akita, com Python no lugar de Ruby."
tags:
- blog
- desenvolvimento-de-software
featured: true
draft: false
---

Este site é feito do mesmo jeito que o [blog do Fabio Akita](https://akitaonrails.com/2025/09/10/meu-novo-blog-como-eu-fiz/) ([código](https://github.com/akitaonrails/akitaonrails.github.io)), com duas mudanças: os scripts de apoio são em **Python** em vez de Ruby, e o **[mise](https://mise.jdx.dev)** controla tudo — versões das ferramentas, o ambiente Python e todas as tarefas.

## A stack

- **[Hugo](https://gohugo.io)** transforma Markdown em HTML estático. Sem banco de dados, sem servidor.
- **[Hextra](https://imfing.github.io/hextra/)** é o tema: modo escuro, busca (`Ctrl K`), tags, RSS e syntax highlighting.
- **[Netlify](https://www.netlify.com)** faz o build e publica a cada push na `main`.
- **mise** fixa as versões de Hugo, Go e Python, então meu notebook, o GitHub Actions e a Netlify rodam exatamente as mesmas.

## Três idiomas

Cada post é uma pasta com um arquivo por idioma:

```text
content/2026/10/30/new-website-how-i-built-it/
├── index.en.md      → /en/2026/10/30/my-new-website-how-i-built-it/
├── index.es.md      → /es/2026/10/30/mi-nueva-web-como-la-hice/
└── index.pt-br.md   → /pt-br/2026/10/30/meu-novo-site-como-eu-fiz/
```

O Hugo liga as traduções, então o seletor de idioma leva para o mesmo post.

## O fluxo de trabalho

```bash
mise install                 # Hugo, Go, Python
mise run setup               # dependências Python
mise run new "Título"        # cria os 3 arquivos como rascunho
mise run tags:search "ia"    # reaproveitar tags existentes
mise run dev                 # http://localhost:1313/pt-br/
mise run check               # o mesmo que a CI: tags, índices, testes, build
git push                     # a Netlify publica
```

A home e o arquivo são gerados pelo `scripts/generate_index.py` (o `generate_index.rb` do Akita, portado), e o `scripts/tag_catalog.py` mantém as tags consistentes nos três idiomas.
