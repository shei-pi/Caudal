# Caudal — Instrucciones para Claude

## Idioma
Responder siempre en español.

## Git
- Hacer commit y push después de cada cambio funcional.
- Branch de desarrollo: `claude/budget-finance-app-nYgA0`
- No crear PRs salvo que se pida explícitamente.

## Stack
- Backend: FastAPI + SQLAlchemy 2.0 + SQLite, Python 3.11+, pyproject.toml con hatchling
- Frontend: React 18 + Mantine 7 + Vite, TypeScript estricto
- Tests backend: pytest en `backend/tests/`

## Convenciones de código

### Nombres de variables vs tipos
Nunca usar un nombre de variable (campo, parámetro, argumento) igual al nombre de un tipo importado.
Si hay colisión potencial, renombrar la variable con un prefijo descriptivo.

Ejemplos:
- MAL: `date: date` — el campo `date` pisa el tipo `date` de `datetime`
- BIEN: `transaction_date: date` — el campo tiene nombre distinto al tipo
- MAL: `from datetime import date as Date` — el alias oculta el problema en vez de resolverlo
- BIEN: renombrar el campo/variable, no el tipo importado

Esta regla aplica a Python y TypeScript.

## Estilo
- Sin comentarios que expliquen qué hace el código; solo comentar el "por qué" cuando no es obvio.
- Preferir editar archivos existentes antes de crear nuevos.
- No agregar features no pedidas ni abstracciones prematuras.
- No crear archivos de documentación (*.md) salvo que se pidan explícitamente.
