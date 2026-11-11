# Sistema Pedagógico Inteligente

Monolito modular em Django (apps: usuarios, alunos, importacao).

## Como rodar
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # preencha SECRET_KEY e os dados do banco (DB_*)
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Gerar uma SECRET_KEY:
```powershell
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

## Quem pode entrar
Não existe cadastro público. Só entra quem o **administrador** cadastrou em **Usuários** (menu lateral, visível só para ele). Para tirar o acesso de alguém, desmarque "Pode entrar no sistema": usuários não são apagados.

## Perfis de acesso
| Perfil | Consultar | Cadastrar/editar alunos | Excluir alunos | Gerenciar usuários |
|---|---|---|---|---|
| Administrador | sim | sim | sim | sim |
| Orientador | sim | sim | não | não |
| Coordenação | sim | não | não | não |
| Gestor pedagógico | sim | não | não | não |

Alunos não são usuários do sistema: são cadastros. O primeiro administrador é criado com `python manage.py createsuperuser` (superusuário é sempre Administrador).

## Contas de teste (só desenvolvimento)
Com `DEBUG=True`, `python manage.py criar_usuarios_teste` cria admin, coord, gestor e orientador (senha padrão `Teste@123`, ou use `--senha`). O comando recusa rodar com `DEBUG=False`. Nunca use essas senhas em produção.

## Testes
```powershell
python manage.py test   # usa SQLite em memória; não toca no Supabase
```
