(() => {
  "use strict";
  const shell = document.querySelector("[data-site-nav]");
  if (!shell) return;
  document.documentElement.classList.add("site-nav-js");
  const toggle = shell.querySelector(".site-nav-toggle");
  const nav = shell.querySelector(".site-nav");
  if (!toggle || !nav) return;

  const close = () => {
    toggle.setAttribute("aria-expanded", "false");
    nav.classList.remove("is-open");
  };
  toggle.addEventListener("click", () => {
    const open = toggle.getAttribute("aria-expanded") !== "true";
    toggle.setAttribute("aria-expanded", String(open));
    nav.classList.toggle("is-open", open);
  });
  nav.addEventListener("click", (event) => {
    if (event.target.closest("a")) close();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") close();
  });
  document.addEventListener("click", (event) => {
    if (!shell.contains(event.target)) close();
  });
  window.matchMedia("(min-width: 901px)").addEventListener("change", close);
})();
