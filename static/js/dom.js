// Tiny DOM helpers. All text goes through text nodes (never parsed as HTML) to prevent XSS.

/**
 * Create an element.
 * @param {string} tag
 * @param {Record<string, any>} [props] attributes; `class`, `dataset`, and `on*` handlers supported
 * @param {...any} children strings, numbers, nodes or arrays of them
 */
export function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") el.className = value;
    else if (key === "dataset") Object.assign(el.dataset, value);
    else if (key.startsWith("on") && typeof value === "function") {
      el.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (key in el && typeof value !== "string") el[key] = value;
    else el.setAttribute(key, value === true ? "" : String(value));
  }
  append(el, children);
  return el;
}

function append(el, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

/** Replace all children of an element. */
export function render(el, ...children) {
  el.replaceChildren();
  append(el, children);
}

let idCounter = 0;
/** Unique id for label/input pairs. */
export function uid(prefix = "id") {
  idCounter += 1;
  return `${prefix}-${idCounter}`;
}

/** Ask the user to confirm a destructive action with the accessible <dialog>. */
export function confirmAction(message, confirmLabel = "Delete") {
  const dialog = document.getElementById("confirm-dialog");
  document.getElementById("confirm-text").textContent = message;
  dialog.querySelector('button[value="confirm"]').textContent = confirmLabel;
  const opener = document.activeElement;
  return new Promise((resolve) => {
    dialog.addEventListener(
      "close",
      () => {
        if (opener instanceof HTMLElement) opener.focus();
        resolve(dialog.returnValue === "confirm");
      },
      { once: true },
    );
    dialog.showModal();
  });
}
