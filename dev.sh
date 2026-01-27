#!/bin/bash

set -euo pipefail

readonly GREEN='\033[0;32m'
readonly RED='\033[0;31m'
readonly NC='\033[0m'
readonly SERVICE_NAME="akitaonrails-blog"

print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

slugify() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g; s/-\+/-/g; s/^-\|-$//g'
}

new_post() {
    if [ -z "${1:-}" ]; then
        print_error "Título do post não especificado"
        print_message "Uso: ./scripts/dev.sh new-post 'Título do Post'"
        exit 1
    fi

    local title="$1"
    local date_path
    local slug
    local post_dir

    date_path=$(date +%Y/%m/%d)
    slug=$(slugify "$title")
    post_dir="content/${date_path}/${slug}"

    print_message "Criando post: $post_dir"

    mkdir -p "$post_dir"

    cat > "$post_dir/index.md" << EOF
---
title: "$title"
date: $(date +%Y-%m-%dT%H:%M:%S%z)
draft: false
description: "Descrição do post aqui"
tags: []
categories: []
---

Conteúdo do post aqui...

EOF

    print_message "Post criado em: $post_dir/index.md"
}

show_help() {
    echo "Comandos:"
    echo "  rebuild        - Rebuilda a imagem"
    echo "  generate-index - Gera o índice de posts"
    echo "  new-post <title> - Cria um novo post"
    echo "  help           - Mostra esta ajuda"
}

main() {
    check_docker
    
    case "${1:-help}" in
        rebuild)
            rebuild
            ;;
        generate-index)
            generate_index
            ;;
        new-post)
            shift
            new_post "$@"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Comando desconhecido: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"