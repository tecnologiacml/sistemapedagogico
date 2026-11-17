(function () {
  const form = document.getElementById("form-encontro");
  if (!form) return;

  const busca = document.getElementById("busca-aluno");
  const lista = document.getElementById("busca-resultados");
  const campoAluno = form.querySelector('input[name="aluno"]');
  const nome = document.getElementById("aluno-nome");
  const serie = document.getElementById("aluno-serie");
  const numero = document.getElementById("aluno-numero");
  const dica = document.getElementById("ultimo-combinado");
  const segCombinados = document.getElementById("seg-combinados");
  const blocoDuracao = document.getElementById("bloco-duracao");
  let timer = null;

  function aplicarNumero(n) {
    // 1º encontro: só "1º Encontro". Demais: só Realizou / Parcialmente / Não realizou.
    const primeiro = String(n) === "1";
    segCombinados.querySelectorAll("label").forEach(function (l) {
      const ehPrimeiro = l.dataset.valor === "primeiro";
      l.hidden = primeiro ? !ehPrimeiro : ehPrimeiro;
      const input = l.querySelector("input");
      if (l.hidden && input.checked) input.checked = false;
      if (primeiro && ehPrimeiro) input.checked = true;
    });
  }

  function aplicarPresenca() {
    const presente = form.querySelector('input[name="presente"]:checked');
    const ausente = presente && presente.value === "False";
    blocoDuracao.querySelector(".seg").classList.toggle("desativado", ausente);
    if (ausente) blocoDuracao.querySelectorAll("input").forEach(function (i) { i.checked = false; });
  }

  function escolher(a) {
    campoAluno.value = a.id;
    busca.value = a.ra || a.nome;
    nome.value = a.nome;
    serie.value = a.serie;
    numero.value = a.numero;
    lista.hidden = true;
    aplicarNumero(a.numero);
    if (a.ultimo_combinado) {
      dica.textContent = "Combinado no encontro anterior: " + a.ultimo_combinado;
      dica.hidden = false;
    } else {
      dica.hidden = true;
    }
  }

  function limparSelecao() {
    campoAluno.value = "";
    nome.value = serie.value = numero.value = "";
    dica.hidden = true;
  }

  function mostrar(resultados) {
    lista.innerHTML = "";
    if (!resultados.length) {
      const vazio = document.createElement("div");
      vazio.className = "p-2 small text-muted";
      vazio.textContent = "Nenhum aluno encontrado.";
      lista.appendChild(vazio);
    }
    resultados.forEach(function (a) {
      const b = document.createElement("button");
      b.type = "button";
      const forte = document.createElement("strong");
      forte.textContent = a.nome;
      const peq = document.createElement("small");
      peq.textContent = " · " + (a.ra || "sem RA") + " · " + (a.serie || "sem série");
      b.appendChild(forte);
      b.appendChild(peq);
      b.addEventListener("click", function () { escolher(a); });
      lista.appendChild(b);
    });
    lista.hidden = false;
  }

  busca.addEventListener("input", function () {
    limparSelecao();
    clearTimeout(timer);
    const q = busca.value.trim();
    if (q.length < 2) { lista.hidden = true; return; }
    timer = setTimeout(function () {
      fetch(form.dataset.urlBusca + "?q=" + encodeURIComponent(q), { headers: { Accept: "application/json" } })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          // RA exato: seleciona direto.
          const exato = d.resultados.filter(function (a) { return a.ra === q; });
          if (exato.length === 1) escolher(exato[0]); else mostrar(d.resultados);
        })
        .catch(function () { lista.hidden = true; });
    }, 250);
  });

  busca.addEventListener("keydown", function (e) { if (e.key === "Enter") e.preventDefault(); });
  document.addEventListener("click", function (e) { if (!lista.contains(e.target) && e.target !== busca) lista.hidden = true; });
  form.querySelectorAll('input[name="presente"]').forEach(function (i) { i.addEventListener("change", aplicarPresenca); });

  aplicarNumero(numero.value || 1);
  aplicarPresenca();
})();
