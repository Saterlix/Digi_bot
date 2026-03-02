const tg = window.Telegram.WebApp;

// Initialize Telegram WebApp
tg.expand();
tg.enableClosingConfirmation();

// --- MOCK DATA ---
const MOCK_USER = {
    id: 12345678,
    first_name: "Demo User",
    username: "demo_guest",
    balance: 0,
    photo_url: ""
};

const MOCK_CATALOG = [
    // Mobile Legends
    { product_name: "Weekly Diamond Pass", category: "Games", brand: "Mobile Legends", price_uzs: 24000, buyer_sku_code: "mlbb_wdp" },
    { product_name: "86 Diamonds", category: "Games", brand: "Mobile Legends", price_uzs: 12500, buyer_sku_code: "mlbb_86" },
    { product_name: "172 Diamonds", category: "Games", brand: "Mobile Legends", price_uzs: 25000, buyer_sku_code: "mlbb_172" },
    { product_name: "257 Diamonds", category: "Games", brand: "Mobile Legends", price_uzs: 38000, buyer_sku_code: "mlbb_257" },

    // Free Fire
    { product_name: "100 Diamonds", category: "Games", brand: "Free Fire", price_uzs: 11000, buyer_sku_code: "ff_100" },
    { product_name: "310 Diamonds", category: "Games", brand: "Free Fire", price_uzs: 32000, buyer_sku_code: "ff_310" },
    { product_name: "520 Diamonds", category: "Games", brand: "Free Fire", price_uzs: 53000, buyer_sku_code: "ff_520" },

    // PUBG Mobile
    { product_name: "60 UC", category: "Games", brand: "PUBG Mobile", price_uzs: 11500, buyer_sku_code: "pubg_60" },
    { product_name: "325 UC", category: "Games", brand: "PUBG Mobile", price_uzs: 58000, buyer_sku_code: "pubg_325" },
    { product_name: "660 UC", category: "Games", brand: "PUBG Mobile", price_uzs: 115000, buyer_sku_code: "pubg_660" }
];

// State
let selectedItem = null;
let currentUser = null;

// DOM Elements
const elements = {
    catalog: document.getElementById('catalog'),
    skeleton: document.getElementById('loading-skeleton'),
    balance: document.getElementById('user-balance'),

    // Views
    viewHome: document.getElementById('view-home'),
    viewProfile: document.getElementById('view-profile'),
    navHome: document.getElementById('nav-home'),
    navProfile: document.getElementById('nav-profile'),

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
    // Simulate Auth
    currentUser = MOCK_USER;

    // If in Telegram, try to get real name
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        currentUser.first_name = tg.initDataUnsafe.user.first_name;
        currentUser.id = tg.initDataUnsafe.user.id;
    }

    updateBalanceUI();

    // Load Content
    renderSkeletons();

    // Setup Listeners
    elements.overlay.addEventListener('click', closeAllSheets);
    elements.confirmBtn.addEventListener('click', handlePurchase);

    // Simulate Network Delay for Catalog
    setTimeout(() => {
        renderCatalog(MOCK_CATALOG);
        showToast(`Welcome, ${currentUser.first_name}!`, "success");
    }, 800);
}

// UI Updating
function updateBalanceUI() {
    if (!currentUser) return;
    const formatted = formatPrice(currentUser.balance);
    elements.balance.innerText = formatted;
    elements.profileBalance.innerText = formatted;
    elements.profileUserId.innerText = currentUser.id;
}

function renderSkeletons() {
    elements.skeleton.innerHTML = Array(4).fill('<div class="skeleton-card"></div>').join('');
    elements.skeleton.classList.remove('hidden');
    elements.catalog.classList.add('hidden');
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

// Tab Switching
window.switchTab = function (tab) {
    document.querySelectorAll('.view-section').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

    if (tab === 'home') {
        elements.viewHome.classList.remove('hidden');
        elements.navHome.classList.add('active');
    } else if (tab === 'profile') {
        elements.viewProfile.classList.remove('hidden');
        elements.navProfile.classList.add('active');
        updateBalanceUI();
    }

    if (tg.HapticFeedback) tg.HapticFeedback.selectionChanged();
}

// Filter Logic (Visual)
window.filterCategory = function (cat) {
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    event.target.classList.add('active');

    const cards = document.querySelectorAll('.product-card');
    cards.forEach(card => card.style.display = 'flex');

    if (cat === 'Vouchers') {
        cards.forEach((card, index) => {
            if (index % 2 === 0) card.style.display = 'none';
        });
    }
    if (cat === 'Apps') {
        cards.forEach((card) => card.style.display = 'none');

        // Show empty state for Apps
        if (!document.getElementById('empty-msg')) {
            const msg = document.createElement('div');
            msg.id = 'empty-msg';
            msg.style.gridColumn = "span 2";
            msg.style.textAlign = "center";
            msg.style.color = "var(--text-muted)";
            msg.style.padding = "20px";
            msg.innerText = "No apps available yet";
            elements.catalog.appendChild(msg);
        } else {
            document.getElementById('empty-msg').style.display = 'block';
        }
    } else {
        const msg = document.getElementById('empty-msg');
        if (msg) msg.style.display = 'none';
    }

    if (tg.HapticFeedback) tg.HapticFeedback.selectionChanged();
}

// Deposit Logic
window.openDeposit = function () {
    elements.overlay.classList.remove('hidden');
    elements.depositSheet.classList.remove('hidden');
    if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
}

window.handleDeposit = function () {
    const amount = parseInt(elements.depositAmount.value);
    const btn = document.getElementById('deposit-confirm-btn');

    // UI Loading
    const originalText = btn.innerHTML;
    btn.innerHTML = `<i class="ri-loader-4-line" style="animation: spin 1s linear infinite"></i> Processing`;
    btn.disabled = true;

    // Simulate API Delay
    setTimeout(() => {
        currentUser.balance += amount;
        updateBalanceUI();

        showToast(`Successfully added ${formatPrice(amount)}`, "success");
        closeAllSheets();
        if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');

        btn.innerHTML = originalText;
        btn.disabled = false;
    }, 1500);
}

// Purchase Logic
function openSheet(item) {
    selectedItem = item;

    elements.sheetTitle.innerText = item.product_name;
    elements.sheetBrand.innerText = item.brand;
    elements.sheetPrice.innerText = formatPrice(item.price_uzs);
    elements.playerIdInput.value = "";

    elements.overlay.classList.remove('hidden');
    elements.sheet.classList.remove('hidden');

    if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('medium');
}

function handlePurchase() {
    const playerId = elements.playerIdInput.value.trim();
    if (!playerId) {
        showToast("Enter your Player ID", "error");
        elements.playerIdInput.focus();
        if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('error');
        return;
    }

    const btn = elements.confirmBtn;
    const originalText = btn.innerHTML;
    btn.innerHTML = `<i class="ri-loader-4-line" style="animation: spin 1s linear infinite"></i> Processing...`;
    btn.disabled = true;

    // Simulate API Processing
    setTimeout(() => {
        // Check Balance
        if (currentUser.balance < selectedItem.price_uzs) {
            showToast("Insufficient Balance!", "error");
            if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('error');
        } else {
            // Success
            currentUser.balance -= selectedItem.price_uzs;
            updateBalanceUI();

            closeAllSheets();
            showToast("Purchase Successful!", "success");
            if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
        }

        btn.innerHTML = originalText;
        btn.disabled = false;
    }, 1500);
}

function closeAllSheets() {
    elements.overlay.classList.add('hidden');
    elements.sheet.classList.add('hidden');
    elements.depositSheet.classList.add('hidden');
    elements.playerIdInput.blur();
}

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

    setTimeout(() => {
        toast.style.animation = "fade-out-up 0.4s forwards";
        setTimeout(() => toast.remove(), 400);
    }, 3000);
}

function formatPrice(amount) {
    return new Intl.NumberFormat('uz-UZ', { style: 'currency', currency: 'UZS', maximumFractionDigits: 0 }).format(amount);
}
