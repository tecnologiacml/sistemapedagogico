# Sistema Pedagógico Inteligente: guia da estrutura Django

Este README explica, pasta por pasta e arquivo por arquivo, o que cada parte do projeto faz, com um exemplo de código em cada uma. Use como material de estudo e como documentação do repositório.

## Sumário

1. [Como rodar o projeto](#1-como-rodar-o-projeto)
2. [Visão geral da estrutura](#2-visão-geral-da-estrutura)
3. [Arquivos da raiz](#3-arquivos-da-raiz)
4. [A pasta `config/`](#4-a-pasta-config)
5. [A pasta `apps/` e os arquivos de um app](#5-a-pasta-apps-e-os-arquivos-de-um-app)
6. [Os três apps do sistema](#6-os-três-apps-do-sistema)
7. [As pastas `templates/` e `static/`](#7-as-pastas-templates-e-static)
8. [O caminho de um pedido (MVT)](#8-o-caminho-de-um-pedido-mvt)
9. [Comandos essenciais](#9-comandos-essenciais)
10. [Erros comuns](#10-erros-comuns)
11. [Roteiro de estudo](#11-roteiro-de-estudo)

---

## 1. Como rodar o projeto

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Instalar as dependências
pip install -r requirements.txt

# 3. Criar o arquivo .env na raiz (veja a seção 3)

# 4. Criar as tabelas no banco
python manage.py migrate

# 5. Criar o usuário administrador
python manage.py createsuperuser

# 6. Ligar o servidor
python manage.py runserver
```

Abra `http://127.0.0.1:8000/admin/` no navegador.

---

## 2. Visão geral da estrutura

```
projeto/
├── manage.py
├── .env
├── .gitignore
├── requirements.txt
├── db.sqlite3
├── config/                  ← o PROJETO (configurações gerais)
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/                    ← os MÓDULOS do sistema
│   ├── __init__.py
│   ├── usuarios/
│   ├── alunos/
│   └── importacao/
├── templates/               ← páginas HTML compartilhadas
└── static/                  ← CSS, JavaScript, imagens
```

A ideia central: o **projeto** (`config/`) cuida do que é geral, e cada **app** (dentro de `apps/`) é um módulo do sistema com seus dados, regras e telas. Isso é o "monolito modular" da arquitetura: um único sistema, dividido em módulos separados.

---

## 3. Arquivos da raiz

### `manage.py`

**O que é:** a porta de entrada de todos os comandos do Django (ligar o servidor, criar tabelas, criar usuário). Foi gerado pelo `startproject` e quase nunca é editado.

**Para que serve:** quando você digita `python manage.py runserver`, é este arquivo que carrega as configurações e executa o comando.

```python
#!/usr/bin/env python
import os
import sys

def main():
    # Diz ao Django onde estão as configurações
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
```

### `.env`

**O que é:** um arquivo de texto com segredos e configurações que mudam de um ambiente para outro (seu computador, homologação, produção).

**Para que serve:** manter senhas e chaves **fora do código**. O `settings.py` lê estes valores com `os.environ`. Este arquivo **nunca** vai para o GitHub.

```
SECRET_KEY=troque-por-uma-chave-longa-e-aleatoria
DEBUG=True
```

Para gerar uma chave:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Como o `settings.py` usa o `.env`:

```python
from dotenv import load_dotenv   # pip install python-dotenv
import os

load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ['SECRET_KEY']
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
```

### `.gitignore`

**O que é:** a lista do que o Git deve ignorar.

**Para que serve:** evitar que segredos e dados de alunos subam para o repositório.

```
.env
db.sqlite3
venv/
__pycache__/
*.pyc
staticfiles/
```

### `requirements.txt`

**O que é:** a lista das bibliotecas que o projeto usa.

**Para que serve:** instalar tudo de uma vez em outro computador ou no servidor com `pip install -r requirements.txt`. Para gerar a lista a partir do seu ambiente: `pip freeze > requirements.txt` (isso também grava as versões).

```
Django
python-dotenv
pandas
openpyxl
gunicorn
whitenoise
```

Cada uma tem um papel: `Django` é o framework, `python-dotenv` lê o `.env`, `pandas` e `openpyxl` leem o Excel, `gunicorn` e `whitenoise` entram na hora de publicar.

### `db.sqlite3`

**O que é:** o banco de dados de desenvolvimento, em um único arquivo.

**Para que serve:** guardar os dados enquanto você desenvolve, sem instalar nada. Em produção ele será trocado pelo PostgreSQL. **Não vai para o GitHub**, porque pode conter dados reais.

Para olhar dentro dele:

```bash
python manage.py dbshell
```

```sql
.tables
SELECT * FROM alunos_aluno;
```

---

## 4. A pasta `config/`

É o **projeto** em si. Aqui ficam as configurações gerais e o mapa de endereços.

### `config/__init__.py`

**O que é:** um arquivo vazio.

**Para que serve:** avisar ao Python que a pasta é um pacote importável (`config.settings`, `config.urls`). Não precisa editar.

### `config/settings.py`

**O que é:** o painel de controle do sistema. Todas as configurações ficam aqui.

**Para que serve:** dizer ao Django quais apps existem, qual banco usar, onde estão os templates, qual o idioma, etc. As partes mais importantes:

**Apps instalados** (se um app não estiver aqui, o Django não o enxerga):

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Apps do projeto
    'apps.usuarios',
    'apps.alunos',
    'apps.importacao',
]
```

**Banco de dados** (em desenvolvimento, SQLite; depois, PostgreSQL com dados vindos do `.env`):

```python
# Desenvolvimento
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Produção (PostgreSQL), lendo do .env
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ['DB_HOST'],
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}
```

**Templates** (onde ficam as páginas HTML compartilhadas):

```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],   # a pasta templates/ da raiz
        'APP_DIRS': True,                   # e os templates/ de cada app
        'OPTIONS': {'context_processors': [
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ]},
    },
]
```

**Idioma, fuso e arquivos estáticos:**

```python
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Maceio'

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
```

**Login** (para onde mandar quem não está logado):

```python
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'lista_alunos'
LOGOUT_REDIRECT_URL = 'login'
```

### `config/urls.py`

**O que é:** o mapa principal de endereços do site.

**Para que serve:** dizer qual parte do endereço pertence a qual app. Cada app terá o seu próprio `urls.py`, e este arquivo só os liga.

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('contas/', include('django.contrib.auth.urls')),  # login e logout prontos
    path('alunos/', include('apps.alunos.urls')),
    path('importacao/', include('apps.importacao.urls')),
]
```

Com isso, `/alunos/` é atendido pelo app `alunos`, e `/importacao/` pelo app `importacao`.

### `config/wsgi.py`

**O que é:** o ponto de entrada usado pelo servidor de produção.

**Para que serve:** o servidor Gunicorn usa este arquivo para "conversar" com o seu sistema. Você não edita; só o referencia na hora de publicar.

```python
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_wsgi_application()
```

Comando de produção que usa este arquivo:

```bash
gunicorn config.wsgi
```

### `config/asgi.py`

**O que é:** parecido com o `wsgi.py`, mas para recursos em tempo real (WebSockets).

**Para que serve:** no começo você não usa. Fica aí para o futuro.

```python
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_asgi_application()
```

---

## 5. A pasta `apps/` e os arquivos de um app

### `apps/__init__.py`

**O que é:** um arquivo vazio que transforma a pasta `apps/` em um pacote Python. É por causa dele que `'apps.alunos'` funciona no `INSTALLED_APPS`.

### Como criar um app dentro de `apps/`

```bash
mkdir apps/alunos
python manage.py startapp alunos apps/alunos
```

Depois, **abra o `apps.py` do app e ajuste o nome**:

```python
# apps/alunos/apps.py
from django.apps import AppConfig

class AlunosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.alunos'      # precisa ser igual ao INSTALLED_APPS
```

### Estrutura de um app (exemplo: `apps/alunos/`)

```
alunos/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── views.py
├── urls.py          ← você cria
├── forms.py         ← você cria
├── tests.py
├── migrations/
└── templates/
    └── alunos/
        └── lista.html
```

### `models.py`: os dados (o **M**)

**O que é:** onde você descreve as tabelas do banco como classes Python.

**Para que serve:** cada classe vira uma tabela, e cada atributo vira uma coluna. O Django cria e consulta a tabela por você, sem SQL escrito à mão (isso é o ORM).

```python
from django.db import models

class Aluno(models.Model):
    nome = models.CharField(max_length=200)
    matricula = models.CharField(max_length=20, unique=True)
    data_nascimento = models.DateField()
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return f'{self.nome} ({self.matricula})'
```

Consultas usando o ORM (em qualquer view ou no `python manage.py shell`):

```python
Aluno.objects.all()                          # todos
Aluno.objects.filter(ativo=True)             # só os ativos
Aluno.objects.get(matricula='2024001')       # um aluno específico
Aluno.objects.filter(nome__icontains='ana')  # nome contém "ana"
Aluno.objects.create(nome='Ana', matricula='2024001', data_nascimento='2005-03-10')
```

### `migrations/`: o histórico das tabelas

**O que é:** uma pasta com arquivos gerados automaticamente pelo Django (`0001_initial.py`, `0002_...`).

**Para que serve:** cada arquivo registra uma mudança nas tabelas. É assim que o banco acompanha o seu `models.py`. Você **não escreve** esses arquivos; você manda o Django gerá-los e aplicá-los:

```bash
python manage.py makemigrations    # lê o models.py e gera o arquivo de migração
python manage.py migrate           # aplica no banco
```

Parte de um arquivo gerado, só para você reconhecer:

```python
class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Aluno',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('nome', models.CharField(max_length=200)),
                ('matricula', models.CharField(max_length=20, unique=True)),
            ],
        ),
    ]
```

Os arquivos de migração **vão para o Git**, porque o servidor precisa deles para montar as tabelas.

### `admin.py`: o painel pronto

**O que é:** onde você registra os modelos no painel de administração do Django.

**Para que serve:** ganhar telas de listagem, busca, cadastro e edição **sem escrever HTML**. É o grande atalho da primeira entrega.

```python
from django.contrib import admin
from .models import Aluno

@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'matricula', 'ativo')   # colunas da listagem
    search_fields = ('nome', 'matricula')           # caixa de busca
    list_filter = ('ativo',)                        # filtro lateral
```

### `views.py`: a lógica de cada página (o **V**)

**O que é:** funções (ou classes) que recebem um pedido do navegador e devolvem uma resposta.

**Para que serve:** buscar dados, aplicar regras e **permissões**, e escolher o template. É aqui que a segurança do sistema acontece, porque roda no servidor.

```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .forms import AlunoForm
from .models import Aluno

@login_required                       # só entra quem está logado
def lista_alunos(request):
    busca = request.GET.get('q', '')
    alunos = Aluno.objects.filter(nome__icontains=busca)
    return render(request, 'alunos/lista.html', {'alunos': alunos, 'busca': busca})

@login_required
def cadastrar_aluno(request):
    if request.method == 'POST':
        form = AlunoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_alunos')
    else:
        form = AlunoForm()
    return render(request, 'alunos/form.html', {'form': form})

@login_required
def detalhe_aluno(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk)    # 404 se não existir
    return render(request, 'alunos/detalhe.html', {'aluno': aluno})
```

### `urls.py` do app: os endereços do módulo

**O que é:** o mapa de endereços **deste app**. **Não vem pronto**: você cria o arquivo.

**Para que serve:** ligar cada endereço a uma view. Depois o `config/urls.py` inclui este arquivo (com `include`).

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_alunos, name='lista_alunos'),                 # /alunos/
    path('novo/', views.cadastrar_aluno, name='cadastrar_aluno'),      # /alunos/novo/
    path('<int:pk>/', views.detalhe_aluno, name='detalhe_aluno'),      # /alunos/5/
]
```

O `name` é um apelido que você usa nos templates e nos redirecionamentos, em vez de escrever o endereço à mão:

```html
<a href="{% url 'cadastrar_aluno' %}">Novo aluno</a>
<a href="{% url 'detalhe_aluno' aluno.pk %}">Ver</a>
```

### `forms.py`: formulários e validação

**O que é:** classes que descrevem formulários. **Não vem pronto**: você cria quando precisar.

**Para que serve:** gerar o formulário HTML e **validar** o que o usuário enviou (nunca confie só no navegador).

```python
from django import forms
from .models import Aluno

class AlunoForm(forms.ModelForm):
    class Meta:
        model = Aluno
        fields = ['nome', 'matricula', 'data_nascimento']
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_matricula(self):
        matricula = self.cleaned_data['matricula'].strip()
        if not matricula.isdigit():
            raise forms.ValidationError('A matrícula deve conter apenas números.')
        return matricula
```

### `templates/alunos/`: as páginas do app (o **T**)

**O que é:** arquivos HTML com "buracos" que o Django preenche com dados.

**Para que serve:** montar o que o usuário vê. A pasta repete o nome do app (`templates/alunos/`) para evitar conflito se outro app tiver um `lista.html`.

```html
{% extends 'base.html' %}

{% block conteudo %}
  <h1>Alunos</h1>

  <form method="get">
    <input type="text" name="q" value="{{ busca }}" placeholder="Buscar por nome">
    <button type="submit">Buscar</button>
  </form>

  <ul>
    {% for aluno in alunos %}
      <li><a href="{% url 'detalhe_aluno' aluno.pk %}">{{ aluno.nome }}</a> - {{ aluno.matricula }}</li>
    {% empty %}
      <li>Nenhum aluno encontrado.</li>
    {% endfor %}
  </ul>
{% endblock %}
```

E o template do formulário (`form.html`). **Todo formulário com POST precisa do `{% csrf_token %}`**, que é a proteção do Django contra ataques CSRF:

```html
{% extends 'base.html' %}

{% block conteudo %}
  <h1>Novo aluno</h1>
  <form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Salvar</button>
  </form>
{% endblock %}
```

### `tests.py`: testes automatizados

**O que é:** onde você escreve testes que verificam se o código funciona.

**Para que serve:** garantir que uma mudança nova não quebre o que já funcionava. É especialmente importante na importação de Excel.

```python
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from .models import Aluno

class AlunoTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user('teste', password='senha12345')

    def test_lista_exige_login(self):
        resposta = self.client.get(reverse('lista_alunos'))
        self.assertEqual(resposta.status_code, 302)    # redireciona para o login

    def test_lista_mostra_aluno(self):
        Aluno.objects.create(nome='Ana', matricula='2024001', data_nascimento='2005-03-10')
        self.client.login(username='teste', password='senha12345')
        resposta = self.client.get(reverse('lista_alunos'))
        self.assertContains(resposta, 'Ana')
```

Para rodar: `python manage.py test`.

---

## 6. Os três apps do sistema

### App `usuarios`: login e perfis

**Responsabilidade:** quem pode entrar e o que cada perfil (administrador, coordenação, professor) pode fazer.

`apps/usuarios/models.py`: um perfil ligado ao usuário que o Django já traz:

```python
from django.conf import settings
from django.db import models

class Perfil(models.Model):
    class Papel(models.TextChoices):
        ADMIN = 'admin', 'Administrador'
        COORDENADOR = 'coordenador', 'Coordenação'
        PROFESSOR = 'professor', 'Professor'

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    papel = models.CharField(max_length=20, choices=Papel.choices, default=Papel.PROFESSOR)

    def __str__(self):
        return f'{self.usuario.username} ({self.get_papel_display()})'
```

`apps/usuarios/permissoes.py`: um decorador que bloqueia por perfil, **no servidor**:

```python
from functools import wraps
from django.core.exceptions import PermissionDenied

def papel_necessario(*papeis):
    def decorador(view):
        @wraps(view)
        def interna(request, *args, **kwargs):
            perfil = getattr(request.user, 'perfil', None)
            if perfil is None or perfil.papel not in papeis:
                raise PermissionDenied          # responde 403
            return view(request, *args, **kwargs)
        return interna
    return decorador
```

Uso em uma view:

```python
from django.contrib.auth.decorators import login_required
from apps.usuarios.permissoes import papel_necessario

@login_required
@papel_necessario('admin', 'coordenador')
def importar_planilha(request):
    ...
```

Template do login, em `templates/registration/login.html` (o Django procura exatamente esse caminho):

```html
{% extends 'base.html' %}

{% block conteudo %}
  <h1>Entrar</h1>
  <form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Entrar</button>
  </form>
{% endblock %}
```

### App `alunos`: cadastro e consulta

**Responsabilidade:** cadastrar, editar, listar e buscar alunos. Todos os exemplos das seções 5 (models, views, urls, forms, templates, admin e testes) são deste app.

### App `importacao`: Excel para o banco

**Responsabilidade:** receber a planilha, validar e gravar, guardando o histórico. A regra é **nunca gravar direto na tabela final**: ler, validar, mostrar os erros e só então confirmar.

`apps/importacao/models.py`: o histórico de cada importação:

```python
from django.conf import settings
from django.db import models

class Importacao(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    arquivo = models.CharField(max_length=255)
    total_linhas = models.PositiveIntegerField(default=0)
    linhas_com_erro = models.PositiveIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.arquivo} em {self.criado_em:%d/%m/%Y %H:%M}'
```

`apps/importacao/services.py`: a lógica de ler e validar fica num arquivo à parte (é uma convenção sua, não do Django), para a view ficar curta e a regra poder ser testada:

```python
import pandas as pd

COLUNAS = ['nome', 'matricula', 'data_nascimento']

def ler_planilha(arquivo):
    """Lê o Excel e devolve (linhas_validas, erros)."""
    df = pd.read_excel(arquivo, dtype=str)

    faltando = [c for c in COLUNAS if c not in df.columns]
    if faltando:
        return [], [f'Colunas ausentes: {", ".join(faltando)}']

    validas, erros = [], []
    vistas = set()
    for i, linha in df.iterrows():
        numero = i + 2                               # +2: cabeçalho e base 1
        nome = str(linha['nome']).strip()
        matricula = str(linha['matricula']).strip()

        if not nome or nome == 'nan':
            erros.append(f'Linha {numero}: nome vazio')
        elif not matricula or matricula == 'nan':
            erros.append(f'Linha {numero}: matrícula vazia')
        elif matricula in vistas:
            erros.append(f'Linha {numero}: matrícula {matricula} repetida na planilha')
        else:
            vistas.add(matricula)
            validas.append({
                'nome': nome,
                'matricula': matricula,
                'data_nascimento': linha['data_nascimento'],
            })
    return validas, erros
```

`apps/importacao/views.py`: recebe o upload e mostra o relatório:

```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Importacao
from .services import ler_planilha

@login_required
def importar_planilha(request):
    if request.method == 'POST' and request.FILES.get('arquivo'):
        arquivo = request.FILES['arquivo']
        if not arquivo.name.endswith('.xlsx'):
            return render(request, 'importacao/enviar.html', {'erro': 'Envie um arquivo .xlsx.'})

        validas, erros = ler_planilha(arquivo)
        Importacao.objects.create(
            usuario=request.user,
            arquivo=arquivo.name,
            total_linhas=len(validas) + len(erros),
            linhas_com_erro=len(erros),
        )
        return render(request, 'importacao/relatorio.html', {'validas': validas, 'erros': erros})
    return render(request, 'importacao/enviar.html')
```

Template do upload (`importacao/enviar.html`). Note o `enctype`, sem ele o arquivo não chega:

```html
{% extends 'base.html' %}

{% block conteudo %}
  <h1>Importar planilha</h1>
  {% if erro %}<p style="color:red">{{ erro }}</p>{% endif %}
  <form method="post" enctype="multipart/form-data">
    {% csrf_token %}
    <input type="file" name="arquivo" accept=".xlsx">
    <button type="submit">Enviar</button>
  </form>
{% endblock %}
```

---

## 7. As pastas `templates/` e `static/`

### `templates/` (da raiz)

**O que é:** páginas HTML que **todos** os apps usam.

**Para que serve:** o layout comum (menu, rodapé, cabeçalho) fica aqui uma vez só, e cada página só preenche o miolo com `{% extends %}`. Esta pasta só é encontrada porque o `settings.py` tem `'DIRS': [BASE_DIR / 'templates']`.

`templates/base.html`:

```html
{% load static %}
<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block titulo %}Sistema Pedagógico{% endblock %}</title>
  <link rel="stylesheet" href="{% static 'css/estilo.css' %}">
</head>
<body>
  <nav>
    <a href="{% url 'lista_alunos' %}">Alunos</a>
    {% if user.is_authenticated %}
      <span>Olá, {{ user.username }}</span>
    {% endif %}
  </nav>

  <main>
    {% block conteudo %}{% endblock %}
  </main>
</body>
</html>
```

As páginas dos apps "encaixam" nos blocos `titulo` e `conteudo`, como você viu nos exemplos acima.

### `static/`

**O que é:** arquivos fixos que o navegador baixa como estão: CSS, JavaScript e imagens.

**Para que serve:** o visual do site. Funciona porque o `settings.py` tem `STATICFILES_DIRS = [BASE_DIR / 'static']`.

```
static/
├── css/
│   └── estilo.css
├── js/
│   └── app.js
└── img/
    └── logo.png
```

`static/css/estilo.css`:

```css
body { font-family: Arial, sans-serif; margin: 0; }
nav  { background: #3c3489; padding: 12px 20px; }
nav a { color: white; margin-right: 16px; text-decoration: none; }
main { max-width: 900px; margin: 24px auto; padding: 0 16px; }
```

Para usar em um template, lembre do `{% load static %}` no topo:

```html
<img src="{% static 'img/logo.png' %}" alt="Logo">
```

**Atenção em produção:** com `DEBUG=False`, o Django não serve mais os arquivos estáticos sozinho. É para isso que serve o `whitenoise` (e o comando `python manage.py collectstatic`).

---

## 8. O caminho de um pedido (MVT)

Quando alguém abre `/alunos/` no navegador:

```
Navegador
   │  1. pede /alunos/
   ▼
config/urls.py          2. "/alunos/" é do app alunos
   ▼
apps/alunos/urls.py     3. "/" aponta para views.lista_alunos
   ▼
apps/alunos/views.py    4. confere o login e pede os dados ao model
   ▼
apps/alunos/models.py   5. busca os alunos no banco
   ▼
templates/alunos/lista.html   6. monta o HTML com os dados
   ▼
Navegador               7. recebe a página pronta
```

Resumo: **URL → View → Model → banco → Template → resposta.**

| Django (MVT) | Equivale a (MVC) |
|---|---|
| Model (`models.py`) | Model |
| View (`views.py`) | Controller |
| Template (`.html`) | View |

---

## 9. Comandos essenciais

| Comando | O que faz |
|---|---|
| `python manage.py runserver` | Liga o site no seu computador |
| `python manage.py startapp nome apps/nome` | Cria um app novo (a pasta precisa existir) |
| `python manage.py makemigrations` | Gera migrações a partir do `models.py` |
| `python manage.py migrate` | Aplica as migrações no banco |
| `python manage.py createsuperuser` | Cria o administrador |
| `python manage.py shell` | Console Python com o Django carregado, bom para testar consultas |
| `python manage.py test` | Roda os testes |
| `python manage.py check` | Procura erros de configuração |
| `python manage.py collectstatic` | Junta os arquivos estáticos para produção |

Rotina ao mudar um modelo: editar o `models.py`, depois `makemigrations`, depois `migrate`.

---

## 10. Erros comuns

| Sintoma | Causa provável |
|---|---|
| `NameError: load_dotenv is not defined` | Faltou `from dotenv import load_dotenv` ou `pip install python-dotenv` |
| `KeyError: 'SECRET_KEY'` | O `.env` não existe, está vazio ou está fora da raiz |
| App não aparece / erro de import | Falta o app em `INSTALLED_APPS`, ou o `name` no `apps.py` não é `apps.alunos` |
| `no such table` | Faltou rodar `makemigrations` e `migrate` |
| `TemplateDoesNotExist` | Template na pasta errada; o caminho correto é `templates/alunos/lista.html` dentro do app |
| `NoReverseMatch` | O nome usado em `{% url %}` não existe no `urls.py` |
| CSRF verification failed | Faltou `{% csrf_token %}` no formulário |
| Arquivo enviado não chega na view | Faltou `enctype="multipart/form-data"` no formulário |
| CSS não carrega | Falta `{% load static %}` no template, ou `STATICFILES_DIRS` no settings |

---

## 11. Roteiro de estudo

1. Rodar o projeto e entrar em `/admin/` com o superusuário.
2. No app `alunos`, criar o model `Aluno`, rodar `makemigrations` e `migrate`.
3. Registrar no `admin.py` e cadastrar um aluno pelo painel.
4. Criar a view, a URL e o template da listagem.
5. Criar o `forms.py` e a tela de cadastro com validação.
6. Criar o `base.html` e usar `{% extends %}` nas páginas.
7. Colocar o CSS em `static/` e carregá-lo no `base.html`.
8. Configurar login e logout, e proteger as views com `@login_required`.
9. Criar o `Perfil` e o decorador de permissão no app `usuarios`.
10. Criar o `Importacao` e o `services.py` de leitura do Excel no app `importacao`.
11. Escrever os primeiros testes em `tests.py`, começando pela importação.
12. Trocar o SQLite pelo PostgreSQL usando variáveis do `.env`.

Para aprofundar, o tutorial oficial do Django (o projeto de enquetes, em `docs.djangoproject.com`) cobre o mesmo caminho. Faça os dois em paralelo: o tutorial para entender, e este sistema para praticar.
