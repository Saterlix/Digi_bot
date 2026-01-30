// Configuration
// IMPORTANT: GitHub Pages is HTTPS. Your Backend MUST be HTTPS (e.g. valid VPS domain or Ngrok).
// HTTP (localhost) will be blocked by the browser.
const BACKEND_URL = "https://YOUR-NGROK-URL.ngrok-free.app"; // TODO: Replace with your actual Backend URL
// const BACKEND_URL = "http://127.0.0.1:8080"; // Use this ONLY for local testing

// Initialize Telegram WebApp
tg.expand();
tg.enableClosingConfirmation();

// State
let selectedItem = null;
let currentUser = null;

// DOM Elements
const elements = {
    catalog: document.getElementById('catalog'),
    skeleton: document.getElementById('loading-skeleton'),
    balance: document.getElementById('user-balance'),

    // Sheet Modals
    overlay: document.getElementById('purchase-sheet-overlay'),
    sheet: document.getElementById('purchase-sheet'),

    // Sheet Content
    sheetTitle: document.getElementById('sheet-title'),
    sheetBrand: document.getElementById('sheet-brand'),
    sheetPrice: document.getElementById('sheet-price'),
    sheetIcon: document.getElementById('sheet-icon'),

    // Inputs/Buttons
    playerIdInput: document.getElementById('player-id'),
    confirmBtn: document.getElementById('confirm-btn')
};

document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

async function initApp() {
    // Check if running in Telegram
    if (!tg.initData) {
        showDesktopOverlay();
        return;
    }

    // Authenticate
    const user = await authenticateUser();
    if (!user) {
        showToast("Authentication Failed", "error");
        return;
    }

    // Load Content
    renderSkeletons();

    // Setup Listeners
    elements.overlay.addEventListener('click', closeSheet);
    elements.confirmBtn.addEventListener('click', handlePurchase);

    // Fetch Data
    await fetchCatalog();
}

async function authenticateUser() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ initData: tg.initData })
        });

        if (!response.ok) throw new Error("Auth failed");

        const result = await response.json();
        if (result.success) {
            currentUser = result.user;
            elements.balance.innerText = formatPrice(currentUser.balance);
            return currentUser;
        }
    } catch (e) {
        console.error("Auth Error", e);
        return null;
    }
}

function showDesktopOverlay() {
    document.body.innerHTML = `
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;text-align:center;padding:20px;background:var(--bg-dark);">
            <i class="ri-telegram-fill" style="font-size:4rem;color:var(--primary);"></i>
            <h2 style="margin:20px 0 10px;">Open in Telegram</h2>
            <p style="color:var(--text-muted);margin-bottom:30px;">This app works best inside Telegram.</p>
            <a href="https://t.me/Antigravity_Bot" target="_blank" style="background:var(--primary);color:white;text-decoration:none;padding:12px 24px;border-radius:12px;font-weight:600;">Open Bot</a>
        </div>
    `;
}

function renderSkeletons() {
    elements.skeleton.innerHTML = Array(4).fill('<div class="skeleton-card"></div>').join('');
    elements.skeleton.classList.remove('hidden');
    elements.catalog.classList.add('hidden');
}

async function fetchCatalog() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/catalog`);
        if (!response.ok) throw new Error("Network error");

        const json = await response.json();
        const items = json.data || [];

        renderCatalog(items);

    } catch (error) {
        console.error(error);
        showToast("Failed to connect to server", "error");
        elements.skeleton.innerHTML = `<p style="grid-column: span 2; text-align: center; color: var(--danger)">Server Offline</p>`;
    }
}

function renderCatalog(items) {
    elements.skeleton.classList.add('hidden');
    elements.catalog.classList.remove('hidden');
    elements.catalog.innerHTML = "";

    items.forEach(item => {
        const card = document.createElement("div");
        card.className = "product-card fade-in";

        // Format price
        const price = formatPrice(item.price_uzs);

        card.innerHTML = `
            <i class="ri-gamepad-line card-icon"></i>
            <div class="card-brand">${item.brand || "Game"}</div>
            <div class="card-title">${item.product_name}</div>
            <div class="card-price">${price}</div>
        `;

        card.onclick = () => openSheet(item);
        elements.catalog.appendChild(card);
    });
}

// Bottom Sheet Logic
function openSheet(item) {
    selectedItem = item;

    elements.sheetTitle.innerText = item.product_name;
    elements.sheetBrand.innerText = item.brand || "Game Voucher";
    elements.sheetPrice.innerText = formatPrice(item.price_uzs);
    elements.playerIdInput.value = "";

    elements.overlay.classList.remove('hidden');
    elements.sheet.classList.remove('hidden'); // Triggers slide-up via CSS

    // Haptic Feedback
    if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('medium');
}

function closeSheet() {
    elements.overlay.classList.add('hidden');
    elements.sheet.classList.add('hidden');
    elements.playerIdInput.blur();
}

// Purchase Logic
async function handlePurchase() {
    const playerId = elements.playerIdInput.value.trim();
    if (!playerId) {
        showToast("Enter your Player ID", "error");
        elements.playerIdInput.focus();
        if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('error');
        return;
    }

    // UI Loading State
    const btnContent = elements.confirmBtn.innerHTML;
    elements.confirmBtn.innerHTML = `<i class="ri-loader-4-line" style="animation: spin 1s linear infinite"></i> Processing...`;
    elements.confirmBtn.disabled = true;

    try {
        if (!currentUser) {
            showToast("Please restart the app", "error");
            return;
        }

        const payload = {
            user_id: currentUser.id,
            item_sku: selectedItem.buyer_sku_code,
            player_id: playerId
        };

        const response = await fetch(`${BACKEND_URL}/api/buy`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (result.success) {
            closeSheet();
            showToast("Purchase Successful!", "success");
            if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
        } else {
            showToast(result.error || "Transaction Failed", "error");
            if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('error');
        }

    } catch (error) {
        showToast("Connection Error", "error");
    } finally {
        elements.confirmBtn.innerHTML = btnContent;
        elements.confirmBtn.disabled = false;
    }
}

// Utilities
function showToast(message, type = "success") {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icon = type === 'success' ? 'ri-checkbox-circle-fill' : 'ri-error-warning-fill';

    toast.innerHTML = `
        <i class="${icon}" style="color: var(--${type === 'success' ? 'secondary' : 'danger'}); font-size: 1.2rem;"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    // Remove after 3s
    setTimeout(() => {
        toast.style.animation = "fade-out-up 0.4s forwards";
        setTimeout(() => toast.remove(), 400);
    }, 3000);
}

function formatPrice(amount) {
    return new Intl.NumberFormat('uz-UZ', { style: 'currency', currency: 'UZS', maximumFractionDigits: 0 }).format(amount);
}

function filterCategory(cat) {
    // Visual toggle only for demo
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    event.target.classList.add('active');

    // Real logic would re-fetch or filter local items
    const cards = document.querySelectorAll('.product-card');
    cards.forEach(card => card.style.display = 'flex'); // Reset

    if (cat === 'Vouchers') {
        // Just a mock filter effect
        cards.forEach((card, index) => {
            if (index % 2 === 0) card.style.display = 'none';
        });
    }
}
