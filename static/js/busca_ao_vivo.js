/* Busca em tempo real: ao digitar, atualiza só a lista (sem recarregar a página).
   Uso: <form data-busca-ao-vivo="#resultados"> com um campo name="q" e um bloco #resultados.
   Sem JavaScript, o botão Buscar continua funcionando do jeito normal. */
(function () {
  var form = document.querySelector("form[data-busca-ao-vivo]");
  if (!form) return;
  var seletor = form.getAttribute("data-busca-ao-vivo");
  var alvo = document.querySelector(seletor);
  var campo = form.querySelector("input[name='q']");
  if (!alvo || !campo) return;

  var base = form.getAttribute("action") || window.location.pathname;
  var espera = null;
  var ultimoPedido = 0;   // número do pedido mais recente enviado
  var ultimoAplicado = 0; // número do pedido mais recente já mostrado

  function carregar(url) {
    // Não cancela o pedido anterior: assim cada resposta aparece assim que chega,
    // mesmo que o banco demore e a pessoa continue digitando.
    var meu = ++ultimoPedido;
    alvo.setAttribute("aria-busy", "true");
    fetch(url, { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(function (resposta) {
        if (!resposta.ok || resposta.redirected) throw new Error("falhou");
        return resposta.text();
      })
      .then(function (html) {
        var pagina = new DOMParser().parseFromString(html, "text/html");
        var novo = pagina.querySelector(seletor);
        if (!novo) throw new Error("sem resultados");
        if (meu < ultimoAplicado) return; // resposta velha chegou atrasada: ignora
        ultimoAplicado = meu;
        alvo.innerHTML = novo.innerHTML;
        window.history.replaceState(null, "", url);
      })
      .catch(function () {
        form.submit(); // se algo der errado, faz a busca do jeito tradicional
      })
      .finally(function () {
        if (meu === ultimoPedido) alvo.removeAttribute("aria-busy");
      });
  }

  function urlDaBusca() {
    var texto = campo.value.trim();
    return base + (texto ? "?q=" + encodeURIComponent(texto) : "");
  }

  campo.addEventListener("input", function () {
    clearTimeout(espera);
    espera = setTimeout(function () { carregar(urlDaBusca()); }, 100);
  });
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    clearTimeout(espera);
    carregar(urlDaBusca());
  });
  // paginação dentro da lista também atualiza sem recarregar
  alvo.addEventListener("click", function (e) {
    var link = e.target.closest(".pagination a");
    if (link) { e.preventDefault(); carregar(link.getAttribute("href")); }
  });
})();