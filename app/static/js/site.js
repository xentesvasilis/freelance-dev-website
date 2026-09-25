"use strict";
document.documentElement.classList.add("js");

const menuButton = document.querySelector(".menu-toggle");
const navigation = document.querySelector("#primary-nav");
if (menuButton && navigation) {
  menuButton.addEventListener("click", () => {
    const open = menuButton.getAttribute("aria-expanded") !== "true";
    menuButton.setAttribute("aria-expanded", String(open));
    navigation.classList.toggle("is-open", open);
  });
  navigation.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      navigation.classList.remove("is-open");
      menuButton.setAttribute("aria-expanded", "false");
      menuButton.focus();
    }
  });
}

const loadCalendar = document.querySelector("#load-calendar");
if (loadCalendar) {
  loadCalendar.addEventListener("click", () => {
    const config = JSON.parse(document.querySelector("#calendar-config").textContent);
    const container = document.querySelector("#calendly-embed");
    const status = document.querySelector("#calendar-status");
    loadCalendar.disabled = true;
    status.hidden = false;
    // No Calendly network requests before an explicit visitor action.
    const style = document.createElement("link");
    style.rel = "stylesheet";
    style.href = "https://assets.calendly.com/assets/external/widget.css";
    document.head.appendChild(style);
    const script = document.createElement("script");
    script.src = "https://assets.calendly.com/assets/external/widget.js";
    script.onload = () => {
      container.hidden = false;
      window.Calendly.initInlineWidget({url: config.url, parentElement: container, prefill: config.prefill});
      // Calendly inserts an iframe asynchronously; name it for assistive technology.
      const observer = new MutationObserver(() => {
        const frame = container.querySelector("iframe");
        if (frame) { frame.title = "Calendly booking calendar"; observer.disconnect(); }
      });
      const frame = container.querySelector("iframe");
      if (frame) { frame.title = "Calendly booking calendar"; }
      else { observer.observe(container, {childList: true, subtree: true}); }
      document.querySelector("#calendar-consent").hidden = true;
    };
    script.onerror = () => { loadCalendar.disabled = false; };
    document.head.appendChild(script);
  });
}
