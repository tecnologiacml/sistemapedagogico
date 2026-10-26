# Sistema Pedagógico Inteligente

Monolito modular em Django (apps: usuarios, alunos, importacao).

## Como rodar
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # preencha a SECRET_KEY
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Gerar uma SECRET_KEY:
```powershell
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

## Perfis de acesso (Sprint 1)
| Perfil | Consultar alunos | Cadastrar/editar | Excluir |
|---|---|---|---|
| Professor | sim | não | não |
| Coordenação | sim | sim | não |
| Administrador | sim | sim | sim |

Usuários e perfis são criados em `/admin/`. Superusuário é sempre Administrador.

## Testes
```powershell
python manage.py test
```
