const tg = window.Telegram.WebApp;
const BACKEND_URL = "https://roundly-unmedicinal-annalise.ngrok-free.dev";

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
    depositSheet: document.getElementById('deposit-sheet'),

    // Sheet Content
    sheetTitle: document.getElementById('sheet-title'),
    sheetBrand: document.getElementById('sheet-brand'),
    sheetPrice: document.getElementById('sheet-price'),
    sheetIcon: document.getElementById('sheet-icon'),

    // Inputs/Buttons
    playerIdInput: document.getElementById('player-id'),
    confirmBtn: document.getElementById('confirm-btn'),
    depositAmount: document.getElementById('deposit-amount'),

    // Profile Elements
    profileBalance: document.getElementById('profile-balance'),
    profileUserId: document.getElementById('profile-user-id')
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
    elements.overlay.addEventListener('click', closeAllSheets);
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

// Tab Switching
function switchTab(tab) {
    document.querySelectorAll('.view-section').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

    if (tab === 'home') {
        document.getElementById('view-home').classList.remove('hidden');
        document.getElementById('nav-home').classList.add('active');
    } else if (tab === 'profile') {
        document.getElementById('view-profile').classList.remove('hidden');
        document.getElementById('nav-profile').classList.add('active');
        // Update profile data in case balance changed
        if (currentUser) {
            elements.profileBalance.innerText = formatPrice(currentUser.balance);
            elements.profileUserId.innerText = currentUser.id;
        }
    }
}

// Deposit Logic
function openDeposit() {
    elements.overlay.classList.remove('hidden');
    elements.depositSheet.classList.remove('hidden');
}

async function handleDeposit() {
    const amount = parseInt(elements.depositAmount.value);
    const btn = document.getElementById('deposit-confirm-btn');

    // UI Loading
    const originalText = btn.innerHTML;
    btn.innerHTML = `<i class="ri-loader-4-line" style="animation: spin 1s linear infinite"></i> Processing`;
    btn.disabled = true;

    try {
        const payload = {
            user_id: currentUser.id,
            amount: amount,
            ref_id: "DEP-" + Date.now()
        };

        const response = await fetch(`${BACKEND_URL}/api/deposit`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true"
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();
        if (result.success) {
            currentUser.balance = result.new_balance;
            elements.balance.innerText = formatPrice(result.new_balance);
            elements.profileBalance.innerText = formatPrice(result.new_balance);

            showToast(`Successfully added ${formatPrice(amount)}`, "success");
            closeAllSheets();
            if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
        } else {
            showToast("Deposit Failed", "error");
        }
    } catch (e) {
        showToast("Connection Error", "error");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function closeAllSheets() {
    elements.overlay.classList.add('hidden');
    elements.sheet.classList.add('hidden');
    elements.depositSheet.classList.add('hidden');
    elements.playerIdInput.blur();
}

function renderCatalog(items) {
    elements.skeleton.classList.add('hidden');
    elements.catalog.classList.remove('hidden');
    elements.catalog.innerHTML = "";

    items.forEach(item => {
        const card = document.createElement("div");
        card.className = "product-card fade-in";

        // Brand Icons
        let iconClass = "ri-gamepad-line";
        if (item.brand.includes("Mobile Legends")) iconClass = "ri-sword-line";
        if (item.brand.includes("Free Fire")) iconClass = "ri-fire-line";
        if (item.brand.includes("PUBG")) iconClass = "ri-target-line";

        const price = formatPrice(item.price_uzs);

        card.innerHTML = `
            <i class="${iconClass} card-icon"></i>
            <div class="card-brand">${item.brand}</div>
            <div class="card-title">${item.product_name}</div>
            <div class="card-price">${price}</div>
        `;

        card.onclick = () => openSheet(item);
        elements.catalog.appendChild(card);
    });
}

