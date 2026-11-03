# Issues do Sistema Pedagógico (GitHub)

Como usar: crie os **milestones** e **labels** abaixo, depois uma issue por bloco `## #N`, copiando o título e o corpo. Crie **na ordem**, assim os números do GitHub batem com os `#N` citados em "Depende de".

Capacidade: 12h por semana, sprints de 2 semanas, cerca de 24h por sprint. Planejei 18 a 20h por sprint para deixar folga.

## Milestones

| Milestone | Foco | Horas planejadas |
|---|---|---|
| Sprint 1 | Fundação e interface | 19h |
| Sprint 2 | Turmas e encontros | 21h |
| Sprint 3 | Adesão e acompanhamento | 19h |
| Sprint 4 | Boletim | 18h |
| Sprint 5 | Segurança e entrega | 19h |
| Backlog | Depende de decisões | sem data |

## Labels

`banco`, `backend`, `tela`, `interface`, `importacao`, `boletim`, `lgpd`, `teste`, `docs`, `secretaria` (depende de resposta da escola), `bloqueada`, `sprint-1` a `sprint-5`.

Definição de pronto (vale para toda issue de código): testes passando (`python manage.py test`), migração versionada quando houver, nenhum dado pessoal ou `.env` no commit, e a issue revisada contra os critérios de aceite.

---

# Sprint 1: Fundação e interface

## #1 Aplicar a modelagem v2 no Supabase
**Labels:** banco, sprint-1 · **Estimativa:** 3h · **Depende de:** patch `patch_sistema_pedagogico_v2.zip`

**Contexto:** o patch traz os models de Unidade, Série, Aluno, Responsável, importação e perfis, já testados numa cópia do projeto. Falta aplicá-los ao repositório e ao Supabase.

**Tarefas**
- [ ] Criar a branch `feature/modelagem-v2` e rodar `python manage.py migrate alunos zero` com o código antigo
- [ ] Extrair o patch na raiz e apagar a migração antiga `0002_alter_aluno_cpf_alter_aluno_data_nascimento.py`
- [ ] Rodar `python manage.py check` e `python manage.py test`
- [ ] Rodar `python manage.py migrate` e conferir `escola_unidade` (2 linhas) e `escola_serie` (16 linhas) no Supabase
- [ ] Executar `docs/supabase_seguranca.sql` no SQL Editor e conferir `rowsecurity = true` em todas as tabelas
- [ ] Atribuir perfil e unidades aos usuários em `/admin/`

**Critérios de aceite:** testes passando; tabelas novas no Supabase com RLS ligado; login funcionando; PR aberto com a branch.

## #2 Importar alunos do Centro e da Chiara
**Labels:** importacao, sprint-1 · **Estimativa:** 2h · **Depende de:** #1

**Tarefas**
- [ ] Rodar o comando `importar_planilha alunos` em simulação para cada unidade e ler o relatório
- [ ] Confirmar com `--confirmar` (Centro e depois Chiara)
- [ ] Conferir contagens: 422 alunos no Centro e 97 na Chiara, nenhum aluno sem responsável
- [ ] Guardar as planilhas fora do repositório

**Critérios de aceite:** 519 alunos e 469 responsáveis no banco; reimportar o mesmo arquivo marca tudo como duplicado.

## #3 Levantar pendências com o orientador
**Labels:** secretaria, bloqueada, sprint-1 · **Estimativa:** 2h

**Contexto:** o documento de requisitos lista as perguntas P1 a P12. Várias bloqueiam as sprints seguintes (formato do boletim, R.A. e turma, formato dos aspectos).

**Tarefas**
- [ ] Enviar as perguntas P1 a P12 ao orientador
- [ ] Receber o **documento de histórico de reuniões** e as **2 planilhas**
- [ ] Atualizar o documento de requisitos com as respostas
- [ ] Atualizar as issues #8, #9, #14, #15 e #21 se as respostas mudarem o escopo

**Critérios de aceite:** P1, P2, P4, P5, P6 e P7 respondidas e registradas.

## #4 Desenhar as telas principais (wireframes)
**Labels:** interface, sprint-1 · **Estimativa:** 5h · **Depende de:** #3 (parcial)

**Contexto:** o orientador pediu para definir a interface, validar e só então implementar.

**Tarefas**
- [ ] Busca de aluno por nome ou R.A.
- [ ] Ficha do aluno (abas Dados, Encontros, Orientações, Boletim; resumo no topo)
- [ ] Novo encontro (campos do documento de histórico de reuniões, notas ao lado, orientações pendentes)
- [ ] Alunos por turma (encontros feitos, situação de adesão)
- [ ] Versões para notebook e celular

**Critérios de aceite:** protótipo navegável (Figma ou imagens) cobrindo as 4 telas.

## #5 Validar o protótipo com o orientador
**Labels:** interface, secretaria, sprint-1 · **Estimativa:** 2h · **Depende de:** #4

**Tarefas**
- [ ] Apresentar o protótipo e anotar ajustes
- [ ] Registrar a aprovação (ou os ajustes pendentes) como comentário na issue
- [ ] Atualizar as telas conforme o retorno

**Critérios de aceite:** aprovação registrada para busca, ficha e novo encontro.

## #6 Tratar matrícula como R.A. no cadastro de aluno
**Labels:** backend, tela, sprint-1 · **Estimativa:** 2h · **Depende de:** #1

**Contexto:** o orientador identifica o aluno por nome e R.A. O campo `matricula` já existe (opcional e único por unidade). O rótulo e as buscas devem dizer R.A.

**Tarefas**
- [ ] Trocar o rótulo "Matrícula" por "R.A." em formulário, lista e detalhe
- [ ] Permitir buscar por R.A. na lista
- [ ] Atualizar os testes

**Critérios de aceite:** formulário e listas mostram "R.A."; busca por R.A. funciona; testes passando.

## #7 Organizar o repositório no GitHub
**Labels:** docs, sprint-1 · **Estimativa:** 3h

**Tarefas**
- [ ] Criar labels e milestones desta página
- [ ] README com como rodar o projeto e os testes
- [ ] Template de issue e de pull request
- [ ] GitHub Actions rodando `python manage.py test` em cada PR
- [ ] Conferir `.gitignore` (planilhas, relatórios, `.env`)

**Critérios de aceite:** um PR de teste dispara os testes automaticamente.

---

# Sprint 2: Turmas e encontros

## #8 Criar Turma e vínculo aluno-turma por ano letivo
**Labels:** banco, backend, sprint-2 · **Estimativa:** 3h · **Depende de:** #1, #3

**Contexto:** o orientador quer ver os alunos por turma e manter o histórico quando o aluno muda de turma.

**Tarefas**
- [ ] Model `Turma` (série, nome, ano letivo, unidade) e `AlunoTurma` (aluno, turma)
- [ ] Restrições: uma turma ativa por aluno por ano letivo
- [ ] Admin e testes

**Critérios de aceite:** turmas e vínculos criados no admin; restrição testada.

## #9 Importar turmas e R.A. dos alunos
**Labels:** importacao, secretaria, sprint-2 · **Estimativa:** 3h · **Depende de:** #8, #3

**Contexto:** a exportação atual do Proesc não tem R.A. nem turma. Usar a planilha do orientador ou uma nova exportação (pendências P4 e P9).

**Tarefas**
- [ ] Definir a planilha de origem e as colunas
- [ ] Estender o importador para ler R.A. e turma, casando o aluno por nome e data de nascimento
- [ ] Relatório de alunos sem correspondência

**Critérios de aceite:** alunos do 6º ano à 3ª série com R.A. e turma; casos sem correspondência listados.

## #10 Tela de alunos por turma
**Labels:** tela, sprint-2 · **Estimativa:** 3h · **Depende de:** #8, #5

**Tarefas**
- [ ] Lista de turmas e, ao abrir uma, seus alunos
- [ ] Mostrar R.A. e quantidade de encontros (ex.: 2 de 4)
- [ ] Respeitar a unidade do usuário

**Critérios de aceite:** orientador da unidade Centro só vê turmas do Centro; layout igual ao protótipo aprovado.

## #11 Model de Encontro com número sequencial
**Labels:** banco, backend, sprint-2 · **Estimativa:** 4h · **Depende de:** #8, #3

**Tarefas**
- [ ] Model `Encontro`: aluno, orientador, data, ano letivo, número, o que foi conversado, sonhos, pontos fortes, pontos fracos
- [ ] Número calculado automaticamente (sequencial por aluno e ano letivo), com restrição de unicidade
- [ ] Meta de encontros por série: 4 no fundamental, 5 no médio
- [ ] Testes (sequência, dois encontros no mesmo número, meta por série)

**Critérios de aceite:** não é possível repetir o número do encontro do mesmo aluno no mesmo ano; testes passando.

## #12 Tela de novo encontro
**Labels:** tela, sprint-2 · **Estimativa:** 4h · **Depende de:** #11, #5

**Tarefas**
- [ ] Formulário com os campos do documento de histórico de reuniões
- [ ] Número do encontro preenchido automaticamente
- [ ] Mensagens de erro claras e salvamento com confirmação

**Critérios de aceite:** orientador registra um encontro completo em poucos minutos; testes de tela.

## #13 Busca de aluno e ficha com histórico
**Labels:** tela, sprint-2 · **Estimativa:** 4h · **Depende de:** #11, #5

**Tarefas**
- [ ] Busca por parte do nome (sem acento e sem diferenciar maiúscula) ou por R.A.
- [ ] Ficha com dados, turma e encontros em ordem cronológica
- [ ] Atalho "novo encontro" na ficha

**Critérios de aceite:** chegar à ficha em até 3 cliques; busca responde em até 2 segundos com a base atual.

---

# Sprint 3: Adesão e acompanhamento

## #14 Aspectos de acompanhamento no encontro
**Labels:** banco, tela, lgpd, sprint-3 · **Estimativa:** 3h · **Depende de:** #12, #3 (P5)

**Contexto:** noite de sono, alimentação, parte cognitiva, atenção e memória. São dados sensíveis de menores.

**Tarefas**
- [ ] Definir o formato com o orientador (escala, opções ou texto)
- [ ] Model e campos no formulário do encontro
- [ ] Exibir na ficha, só para quem tem permissão

**Critérios de aceite:** aspectos gravados e exibidos conforme o formato aprovado; perfil sem permissão não os vê.

## #15 Orientações com status de adesão
**Labels:** banco, backend, tela, sprint-3 · **Estimativa:** 5h · **Depende de:** #12, #3 (P6)

**Contexto:** cada orientação dada ao aluno é avaliada no encontro seguinte: bem sucedida, parcialmente ou não fez.

**Tarefas**
- [ ] Model `Orientacao` (texto, encontro de origem, status, encontro de avaliação)
- [ ] No novo encontro, listar as orientações pendentes do encontro anterior para avaliar
- [ ] Aba Orientações na ficha, com o status por orientação
- [ ] Testes (avaliação só no encontro seguinte)

**Critérios de aceite:** fluxo completo de dar, avaliar e consultar orientações; testes passando.

## #16 Progresso dos encontros (4 no fundamental, 5 no médio)
**Labels:** backend, tela, sprint-3 · **Estimativa:** 3h · **Depende de:** #11

**Tarefas**
- [ ] Indicador "2 de 4" na ficha e na lista por turma
- [ ] Aviso (sem bloquear) quando faltar encontro ou passar da meta
- [ ] Testes por série

**Critérios de aceite:** meta correta por série e aviso visível.

## #17 Filtros da lista de alunos
**Labels:** tela, sprint-3 · **Estimativa:** 3h · **Depende de:** #15, #16

**Tarefas**
- [ ] Filtrar por série, turma, número do encontro e situação de adesão
- [ ] Manter os filtros ao paginar

**Critérios de aceite:** combinações de filtros retornam o resultado esperado (testado).

## #18 Histórico de alterações e exclusão lógica de encontros
**Labels:** backend, lgpd, sprint-3 · **Estimativa:** 3h · **Depende de:** #11

**Tarefas**
- [ ] Registrar quem editou e quando
- [ ] Exclusão lógica, restrita ao administrador
- [ ] Testes de permissão

**Critérios de aceite:** nenhum encontro some do banco; edição deixa rastro.

## #19 Testes de tela por perfil
**Labels:** teste, sprint-3 · **Estimativa:** 2h · **Depende de:** #10 a #18

**Tarefas**
- [ ] Orientador, coordenação, secretaria e administrador: o que cada um vê e faz
- [ ] Acesso por link direto a aluno de outra unidade (deve dar 404)

**Critérios de aceite:** matriz de permissões coberta por testes.

---

# Sprint 4: Boletim

## #20 Modelar disciplinas, notas e média mínima
**Labels:** banco, boletim, sprint-4 · **Estimativa:** 4h · **Depende de:** #3 (P7)

**Tarefas**
- [ ] Models `Disciplina`, `Nota` (aluno, disciplina, período, valor) e configuração da média mínima e das faixas
- [ ] Restrições (uma nota por aluno, disciplina e período)
- [ ] Testes

**Critérios de aceite:** notas gravadas e consultáveis; média mínima configurável sem mexer no código.

## #21 Importar boletim com tela de conferência
**Labels:** importacao, boletim, tela, secretaria, sprint-4 · **Estimativa:** 6h · **Depende de:** #20, #3 (P7)

**Contexto:** o formato do Proesc (Excel ou PDF) ainda é desconhecido. Também é a primeira tela web de importação; reaproveitar o serviço de validação e confirmação existente.

**Tarefas**
- [ ] Definir o formato de entrada e escrever o leitor
- [ ] Tela: enviar arquivo, ver erros e duplicados, confirmar
- [ ] Permissão `pode_importar`
- [ ] Testes com planilha de exemplo (sem dados reais)

**Critérios de aceite:** boletim de uma turma importado ponta a ponta; linhas com problema aparecem antes de gravar.

## #22 Aba Boletim na ficha do aluno
**Labels:** tela, boletim, sprint-4 · **Estimativa:** 3h · **Depende de:** #20

**Critérios de aceite:** notas por disciplina e período, conforme o protótipo.

## #23 Situação das notas (bem, atenção, abaixo)
**Labels:** backend, boletim, sprint-4 · **Estimativa:** 3h · **Depende de:** #20

**Tarefas**
- [ ] Regra por disciplina e geral, usando a média mínima configurada
- [ ] Indicador na ficha e na lista por turma
- [ ] Testes de borda (nota igual à média)

**Critérios de aceite:** a situação muda ao alterar a média mínima.

## #24 Notas visíveis no novo encontro
**Labels:** tela, boletim, sprint-4 · **Estimativa:** 2h · **Depende de:** #22, #23

**Critérios de aceite:** ao registrar o encontro, o orientador vê a situação das notas do aluno sem sair da tela.

---

# Sprint 5: Segurança e entrega

## #25 Registrar acesso às fichas (LogAcesso)
**Labels:** backend, lgpd, sprint-5 · **Estimativa:** 3h

**Tarefas**
- [ ] Gravar consulta, criação, edição e exclusão de fichas e encontros (usuário, objeto, IP, data)
- [ ] Tela simples para o administrador consultar
- [ ] Testes

**Critérios de aceite:** toda abertura de ficha gera registro.

## #26 Confidencialidade das anotações por perfil
**Labels:** backend, lgpd, sprint-5 · **Estimativa:** 3h · **Depende de:** #3 (P8)

**Critérios de aceite:** perfis sem permissão não veem anotações nem aspectos, nem por link direto.

## #27 Exportar por turma (Excel) e ficha do aluno (PDF)
**Labels:** backend, tela, sprint-5 · **Estimativa:** 5h

**Contexto:** substitui as planilhas e pastas por turma que o orientador usa hoje.

**Critérios de aceite:** Excel com alunos, R.A., encontros e adesão por turma; PDF da ficha legível; exportações entram no log.

## #28 Documentar LGPD: finalidade, guarda e consentimento
**Labels:** lgpd, docs, secretaria, sprint-5 · **Estimativa:** 3h

**Tarefas**
- [ ] Definir com a escola a base legal, o prazo de guarda e o consentimento dos responsáveis
- [ ] Texto de aviso no sistema
- [ ] Rotina de descarte conforme o prazo

**Critérios de aceite:** documento aprovado pela escola e aviso exibido no login.

## #29 Publicar com HTTPS, backups e checklist de produção
**Labels:** backend, sprint-5 · **Estimativa:** 5h

**Tarefas**
- [ ] `DEBUG` desligado, `ALLOWED_HOSTS`, cookies seguros e HTTPS
- [ ] Backup do Supabase e teste de restauração
- [ ] Verificação em duas etapas para administração
- [ ] Teste de ponta a ponta com o orientador

**Critérios de aceite:** sistema acessível pela internet só por HTTPS, com backup restaurado em teste.

---

# Backlog (sem sprint definida)

## #30 Painel por turma (adesão e encontros pendentes)
**Labels:** tela · **Estimativa:** a definir · **Depende de:** #15, #16

## #31 Decidir o destino do módulo de leads e do cadastro geral
**Labels:** secretaria · **Estimativa:** 1h

**Contexto:** as respostas do orientador não citam leads. O modelo e o importador existem. Confirmar com a escola (P12) se entram no estágio.

## #32 Integração ou importação periódica do Proesc e do Plural
**Labels:** importacao, secretaria · **Estimativa:** a definir

**Contexto:** o orientador quer tudo em um sistema só. Verificar se há API ou exportação estável antes de prometer integração (P11).

## #33 Migrar histórico de encontros de anos anteriores
**Labels:** importacao, secretaria · **Estimativa:** a definir · **Depende de:** #3 (P10)

---

# Revisão de 30/10/2026: novas issues e plano de 7 sprints

Segunda conversa com o orientador: primeiro ciclo só de leitura para gestão, perfis com visões próprias, dashboard, dificuldades por matéria, responsável na ficha e início só com as turmas do Rafael. Os acréscimos somam cerca de 26h, então o plano passa de 5 para 7 sprints. **Use esta tabela no lugar dos milestones de cada issue acima.**

| Sprint | Issues | Horas |
|---|---|---|
| 1 | #1, #2, #3, #4, #5, #6, #7 | 19h |
| 2 | #8, #11, #34, #35, #36, #37 | 19h |
| 3 | #9, #10, #12, #13, #38 | 19h |
| 4 | #14, #15, #16, #17, #18, #19 | 19h |
| 5 | #20, #21, #22, #23, #24 | 18h |
| 6 | #39, #40, #27, #25, #26 | 20h |
| 7 | #28, #29 e folga para ajustes | 8h |
| Backlog | #30, #31, #32, #33 | sem data |

## #34 Perfis de leitura e visões por perfil
**Labels:** backend, tela, sprint-2 · **Estimativa:** 5h · **Depende de:** #1, #5

**Contexto:** no primeiro ciclo gestor pedagógico, coordenação e direção só visualizam. No código atual a coordenação ainda pode editar.

**Tarefas**
- [ ] Criar os perfis Orientador, Gestor pedagógico e Direção; a Coordenação passa a ser só leitura
- [ ] Menu e telas diferentes por perfil (visões atribuídas aos poucos)
- [ ] Bloquear criar, editar e excluir no servidor para os perfis de leitura (não só esconder botões)
- [ ] Ajustar `pode_importar` e os testes de permissão

**Critérios de aceite:** perfil de leitura recebe 403 ao tentar criar, editar ou excluir; testes cobrem cada perfil.

## #35 Administrador cadastra usuários, perfis e turmas visíveis
**Labels:** backend, tela, sprint-2 · **Estimativa:** 3h · **Depende de:** #34

**Critérios de aceite:** administrador cria usuário, escolhe perfil e turmas; os demais perfis não acessam essa tela.

## #36 Escopo inicial: só as turmas do Rafael
**Labels:** banco, sprint-2 · **Estimativa:** 2h · **Depende de:** #8, #3 (confirmar quem é o Rafael)

**Tarefas**
- [ ] Campo de orientador responsável na turma
- [ ] Importar e exibir apenas as turmas e os alunos dele; modelo pronto para outras turmas depois

**Critérios de aceite:** incluir uma turma nova não exige mudar o modelo nem as telas.

## #37 Responsável na ficha do aluno (somente leitura)
**Labels:** tela, sprint-2 · **Estimativa:** 2h · **Depende de:** #1

**Contexto:** os dados já foram importados (469 responsáveis). Editar e registrar contato ficam para depois (P16).

**Critérios de aceite:** ficha mostra nome, celular e e-mail do responsável financeiro.

## #38 Habilidades, dificuldades e objetivos do aluno
**Labels:** banco, backend, tela, sprint-3 · **Estimativa:** 5h · **Depende de:** #12, #3 (P14, P15)

**Tarefas**
- [ ] Models de habilidade, dificuldade (sempre com disciplina) e objetivo
- [ ] Campos no novo encontro e blocos na ficha
- [ ] Testes (dificuldade sem disciplina é recusada)

**Critérios de aceite:** dificuldades registradas alimentam o ranking da issue #40.

## #39 Dashboard do gestor
**Labels:** tela, backend, sprint-6 · **Estimativa:** 5h · **Depende de:** #16, #15, #23, #38

**Tarefas**
- [ ] Alunos acompanhados, encontros contra a meta, adesão às orientações e notas abaixo da média
- [ ] Filtros por série e turma; consultas agregadas (abre em até 3 segundos)
- [ ] Visão própria para gestor, coordenação e direção

**Critérios de aceite:** layout igual ao protótipo aprovado; perfil de leitura só visualiza.

## #40 Ranking de matérias com mais dificuldade
**Labels:** tela, backend, boletim, sprint-6 · **Estimativa:** 4h · **Depende de:** #38, #23

**Critérios de aceite:** ranking por turma e série combinando dificuldades registradas e notas abaixo da média; clicar numa matéria lista os alunos.
