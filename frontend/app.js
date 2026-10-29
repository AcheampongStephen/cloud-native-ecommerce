"use strict";
const $ = (id) => document.getElementById(id);
const money = (cents) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(
    cents / 100,
  );
const state = {
  token: null,
  me: null,
  products: [],
  cart: new Map(),
  category: "",
  register: false,
  busy: false,
  uncertain: false,
  retryKey: null,
};
// Tokens stay in memory. Reloading deliberately signs out.
function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
}
async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}),
    ...options.headers,
  };
  let response;
  try {
    response = await fetch("/api/v1" + path, { ...options, headers });
  } catch {
    throw new Error(
      "Connection unavailable. Try again; your checkout key is retained.",
    );
  }
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401 && state.token) {
      signOut();
    }
    const error = new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Please check your input and try again.",
    );
    error.status = response.status;
    throw error;
  }
  return data;
}
let toastTimer;
function toast(message) {
  $("toast").textContent = message;
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($("toast").hidden = true), 3500);
}
function signOut() {
  state.token = null;
  state.me = null;
  state.retryKey = null;
  state.uncertain = false;
  state.cart.clear();
  renderCart();
  $("account-button").textContent = "Sign in";
}
function changeCart(product, change) {
  if (state.busy) return;
  if (state.uncertain) {
    toast("Resolve your pending checkout before changing the bag.");
    return;
  }
  const old = state.cart.get(product.id),
    quantity = (old?.quantity || 0) + change;
  if (quantity > 100) return toast("Maximum 100 of each item.");
  if (quantity <= 0) state.cart.delete(product.id);
  else state.cart.set(product.id, { ...product, quantity });
  state.retryKey = null;
  renderCart();
}
function renderCart() {
  const items = [...state.cart.values()];
  $("cart-count").textContent = items.reduce((n, p) => n + p.quantity, 0);
  $("cart-items").replaceChildren();
  if (!items.length)
    $("cart-items").append(
      el("p", "hint", "Your bag is ready for something good."),
    );
  for (const p of items) {
    const row = el("div", "cart-item");
    row.append(el("span", "emoji", p.emoji));
    const info = el("div");
    info.append(el("h3", "", p.name), el("p", "", money(p.price_cents)));
    const qty = el("div", "quantity");
    for (const [label, change] of [
      ["−", -1],
      ["+", 1],
    ]) {
      const b = el("button", "", label);
      b.setAttribute(
        "aria-label",
        `${change < 0 ? "Remove" : "Add"} one ${p.name}`,
      );
      b.disabled = state.busy || state.uncertain;
      b.onclick = () => changeCart(p, change);
      if (change === 1) qty.append(el("span", "", p.quantity));
      qty.append(b);
    }
    row.append(info, qty);
    $("cart-items").append(row);
  }
  $("cart-total").textContent = money(
    items.reduce((n, p) => n + p.price_cents * p.quantity, 0),
  );
  $("checkout").disabled = state.busy || !items.length;
  $("payment-method").disabled = state.busy || state.uncertain;
}
async function loadProducts() {
  try {
    const params = new URLSearchParams({
      q: $("search").value,
      category: state.category,
    });
    const data = await api("/products?" + params);
    state.products = data.items;
    $("product-total").textContent = `(${data.total})`;
    $("products").replaceChildren();
    if (!data.items.length)
      $("products").append(el("p", "", "No goods match your search."));
    for (const p of data.items) {
      const card = el("article", "product-card"),
        art = el("div", "product-art");
      art.append(
        el("span", "product-category", p.category),
        el("span", "product-emoji", p.emoji),
      );
      const add = el("button", "add-button", "+");
      add.setAttribute("aria-label", "Add " + p.name + " to bag");
      add.onclick = () => {
        changeCart(p, 1);
        toast(p.name + " added to your bag.");
      };
      art.append(add);
      const info = el("div", "product-info");
      info.append(el("h3", "", p.name), el("strong", "", money(p.price_cents)));
      card.append(art, info, el("p", "", p.description));
      $("products").append(card);
    }
  } catch (error) {
    $("products").replaceChildren(el("p", "error", error.message));
  }
}
function showView(orders) {
  $("shop-view").hidden = orders;
  $("orders-view").hidden = !orders;
  $("shop-nav").classList.toggle("nav-active", !orders);
  $("orders-nav").classList.toggle("nav-active", orders);
  if (orders) loadOrders();
}
async function loadOrders() {
  $("orders-list").replaceChildren();
  $("notifications-list").replaceChildren();
  if (!state.token) {
    $("orders-list").append(el("p", "", "Sign in to view your orders."));
    return;
  }
  try {
    const [orders, notifications] = await Promise.all([
      api("/orders"),
      api("/notifications"),
    ]);
    if (!orders.items.length)
      $("orders-list").append(
        el("p", "", "No orders yet. Your next favorite is waiting."),
      );
    for (const order of orders.items) {
      const card = el("article", "order-card");
      card.append(
        el("span", "status", order.status),
        el("strong", "", money(order.total_cents)),
        el(
          "p",
          "",
          `Order ${order.id.slice(0, 8)} · ${new Date(order.created_at).toLocaleString()}`,
        ),
      );
      for (const item of order.items)
        card.append(el("p", "", `${item.quantity} × ${item.name}`));
      if (order.reason) card.append(el("p", "error", order.reason));
      if (order.status === "pending") {
        const b = el("button", "secondary", "Resume checkout");
        b.onclick = async () => {
          if (state.busy) return;
          state.busy = true;
          b.disabled = true;
          try {
            const result = await api("/orders", {
              method: "POST",
              headers: { "Idempotency-Key": order.retry_key },
              body: JSON.stringify(order.request),
            });
            toast("Order " + result.status);
            if (state.retryKey === order.retry_key) {
              state.retryKey = null;
              state.uncertain = false;
              state.cart.clear();
              renderCart();
            }
            loadOrders();
          } catch (e) {
            toast(e.message);
          } finally {
            state.busy = false;
            b.disabled = false;
            renderCart();
          }
        };
        card.append(b);
      }
      $("orders-list").append(card);
    }
    if (!notifications.items.length)
      $("notifications-list").append(
        el(
          "p",
          "hint",
          "Order confirmations arrive here shortly after checkout.",
        ),
      );
    for (const n of notifications.items)
      $("notifications-list").append(
        el("p", "inbox-item", `${n.message} (Order ${n.order_id.slice(0, 8)})`),
      );
  } catch (e) {
    $("orders-list").append(el("p", "error", e.message));
  }
}
$("account-button").onclick = () => {
  if (state.token) {
    signOut();
    toast("Signed out.");
  } else $("auth-dialog").showModal();
};
$("cart-button").onclick = () => {
  renderCart();
  $("cart-dialog").showModal();
};
document
  .querySelectorAll("[data-close]")
  .forEach((b) => (b.onclick = () => $(b.dataset.close).close()));
$("auth-toggle").onclick = () => {
  state.register = !state.register;
  $("auth-title").textContent = state.register
    ? "Make yourself at home."
    : "Welcome back.";
  $("auth-submit").textContent = state.register ? "Create account" : "Sign in";
  $("auth-toggle").textContent = state.register
    ? "Already a member? Sign in"
    : "New here? Create an account";
  $("password").autocomplete = state.register
    ? "new-password"
    : "current-password";
  $("auth-error").textContent = "";
};
$("auth-form").onsubmit = async (event) => {
  event.preventDefault();
  $("auth-submit").disabled = true;
  $("auth-error").textContent = "";
  const body = JSON.stringify({
    email: $("email").value,
    password: $("password").value,
  });
  try {
    if (state.register) await api("/auth/register", { method: "POST", body });
    const data = await api("/auth/login", { method: "POST", body });
    state.token = data.access_token;
    state.me = await api("/auth/me");
    $("account-button").textContent = "Sign out";
    $("auth-dialog").close();
    $("password").value = "";
    toast("Welcome, " + state.me.email);
    if (!$("orders-view").hidden) loadOrders();
  } catch (e) {
    $("auth-error").textContent = e.message;
  } finally {
    $("auth-submit").disabled = false;
  }
};
$("checkout").onclick = async () => {
  if (!state.token) {
    $("cart-dialog").close();
    $("auth-dialog").showModal();
    return;
  }
  if (state.busy || !state.cart.size) return;
  state.busy = true;
  renderCart();
  $("cart-error").textContent = "";
  state.retryKey ||= crypto.randomUUID();
  const body = {
    items: [...state.cart.values()].map((p) => ({
      product_id: p.id,
      quantity: p.quantity,
    })),
    payment_method: $("payment-method").value,
  };
  try {
    const order = await api("/orders", {
      method: "POST",
      headers: { "Idempotency-Key": state.retryKey },
      body: JSON.stringify(body),
    });
    state.uncertain = false;
    if (order.status === "confirmed") {
      state.cart.clear();
      state.retryKey = null;
      $("cart-dialog").close();
      toast("Order confirmed. Good things are on their way.");
      showView(true);
      setTimeout(loadOrders, 2200);
    } else {
      state.retryKey = null;
      $("cart-error").textContent =
        order.status === "declined"
          ? "Simulated payment declined. Stock was released. Choose approve to try again."
          : order.reason || "Order could not be completed.";
    }
  } catch (e) {
    state.uncertain = Boolean(state.retryKey) && (!e.status || e.status >= 500);
    if (!state.uncertain) state.retryKey = null;
    $("cart-error").textContent =
      e.message + (state.uncertain ? " Retry uses the same checkout key." : "");
  } finally {
    state.busy = false;
    renderCart();
  }
};
$("payment-method").onchange = () => (state.retryKey = null);
$("shop-nav").onclick = () => showView(false);
$("orders-nav").onclick = () => showView(true);
$("refresh-orders").onclick = loadOrders;
document.querySelectorAll(".filter").forEach(
  (b) =>
    (b.onclick = () => {
      state.category = b.dataset.category;
      document
        .querySelectorAll(".filter")
        .forEach((x) => x.classList.toggle("active", x === b));
      loadProducts();
    }),
);
let searchTimer;
$("search").oninput = () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadProducts, 250);
};
loadProducts();
renderCart();
