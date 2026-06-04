#!/bin/bash
set -e

echo "⏳ Aguardando banco de dados..."
until python -c "
import psycopg2, os
psycopg2.connect(os.environ['DATABASE_URL']).close()
" 2>/dev/null; do
  echo "   banco ainda não disponível, tentando novamente..."
  sleep 2
done
echo "✅ Banco disponível!"

echo "🌱 Rodando seed..."
python seed.py

echo "🚀 Iniciando API..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
