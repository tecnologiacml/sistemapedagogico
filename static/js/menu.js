/* Menu lateral no celular e no tablet: abre e fecha com o botão, o fundo escuro ou a tecla Esc. */
(function () {
  var botao = document.querySelector(".ml-menu-btn");
  var menu = document.getElementById("menu-lateral");
  var fundo = document.querySelector(".ml-overlay");
  if (!botao || !menu || !fundo) return;

  function definir(aberto) {
    menu.classList.toggle("aberto", aberto);
    fundo.hidden = !aberto;
    botao.setAttribute("aria-expanded", aberto ? "true" : "false");
    botao.setAttribute("aria-label", aberto ? "Fechar menu" : "Abrir menu");
  }
  botao.addEventListener("click", function () { definir(!menu.classList.contains("aberto")); });
  fundo.addEventListener("click", function () { definir(false); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") definir(false); });
  window.addEventListener("resize", function () { if (window.innerWidth >= 992) definir(false); });
})();
