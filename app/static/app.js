/* ═══════════════════════════════════════════════
   ThunderPay — SPA Application Logic
   ═══════════════════════════════════════════════ */

const API = 'https://thunderpay-huhhuku-7744s-projects.vercel.app';  // Backend URL
const tg = window.Telegram?.WebApp;

// ─── State ───
let state = {
    tg_id: 0,
    name: 'User',
    balance: 0,
    is_admin: false,
    catalog: [],
    currentPage: 'home'
};

// ─── Games Config ───
const GAMES = [
    { id: 'MLBB', name: 'Mobile Legends', emoji: '⚔️', color: '#3b82f6', tag: 'Diamonds, Pass' },
    { id: 'PUBG', name: 'PUBG Mobile', emoji: '🔫', color: '#f59e0b', tag: 'UC, Royale Pass' },
    { id: 'FREEFIRE', name: 'Free Fire', emoji: '🔥', color: '#ef4444', tag: 'Diamonds' },
    { id: 'GENSHIN', name: 'Genshin Impact', emoji: '🌟', color: '#8b5cf6', tag: 'Crystals, Welkin' },
    { id: 'STANDOFF2', name: 'Standoff 2', emoji: '🎯', color: '#06b6d4', tag: 'Gold' },
    { id: 'CLASHROYALE', name: 'Clash Royale', emoji: '👑', color: '#22c55e', tag: 'Gems, Pass' },
    { id: 'HOK', name: 'Honor of Kings', emoji: '🏆', color: '#f97316', tag: 'Tokens' },
    { id: 'CODM', name: 'Call of Duty', emoji: '💣', color: '#64748b', tag: 'CP, Battle Pass' },
    { id: 'BRAWLSTARS', name: 'Brawl Stars', emoji: '💥', color: '#a855f7', tag: 'Gems, Brawl Pass' },
    { id: 'ROBLOX', name: 'Roblox', emoji: '🧊', color: '#ec4899', tag: 'Robux' },
];

// ─── Init ───
async function init() {
    if (tg) {
        tg.expand();
        tg.disableClosingConfirmation();
        tg.ready();
    }

    // Auth
    const initData = tg?.initData || 'test_mode=1';
    try {
        const res = await fetch(`${API}/api/auth`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initData })
        });
        const data = await res.json();
        if (data.ok) {
            state.tg_id = data.tg_id;
            state.name = data.name;
            state.balance = data.balance;
            state.is_admin = data.is_admin;
        }
    } catch (e) {
        console.log('Auth fallback', e);
        state.tg_id = 999999;
        state.name = 'Test User';
    }

    updateBalance();
    await loadCatalog();
    router.navigate('home');
}

async function loadCatalog() {
    try {
        const res = await fetch(`${API}/api/catalog`);
        const data = await res.json();
        if (data.ok) state.catalog = data.data;
    } catch (e) {
        console.log('Catalog load error', e);
    }
}

function updateBalance() {
    document.getElementById('user-balance').textContent = state.balance.toLocaleString('ru');
}

async function refreshBalance() {
    try {
        const res = await fetch(`${API}/api/user/${state.tg_id}/balance`);
        const data = await res.json();
        if (data.ok) state.balance = data.balance;
        updateBalance();
    } catch (e) { }
}

// ─── Router ───
const router = {
    navigate(page, params = {}) {
        state.currentPage = page;
        const content = document.getElementById('page-content');
        content.style.animation = 'none';
        content.offsetHeight;
        content.style.animation = 'fadeIn 0.25s ease';

        // Update nav
        document.querySelectorAll('.nav-btn').forEach(b => {
            b.classList.toggle('active', b.dataset.page === page);
        });

        switch (page) {
            case 'home': renderHome(); break;
            case 'game': renderGame(params.gameId); break;
            case 'deposit': renderDeposit(); break;
            case 'deposit-pay': renderDepositPay(params); break;
            case 'orders': renderOrders(); break;
            case 'profile': renderProfile(); break;
            case 'admin': renderAdmin(); break;
            default: renderHome();
        }
    }
};

// ═══════════════════════════════════════════════
// PAGES
// ═══════════════════════════════════════════════

// ─── HOME ───
function renderHome() {
    const content = document.getElementById('page-content');
    let html = `<h2 class="section-title">🎮 Каталог игр</h2>`;
    html += `<div class="games-grid">`;
    for (const g of GAMES) {
        html += `
        <div class="game-card" onclick="router.navigate('game', {gameId:'${g.id}'})"
             style="background: linear-gradient(135deg, ${g.color}22, ${g.color}08);">
            <div class="game-card-bg">${g.emoji}</div>
            <div class="game-card-info">
                <div class="game-card-name">${g.name}</div>
                <div class="game-card-tag">${g.tag}</div>
            </div>
        </div>`;
    }
    html += `</div>`;

    // Bonus row
    html += `
    <h2 class="section-title" style="margin-top:20px">✨ Ещё</h2>
    <div class="bonus-row">
        <div class="bonus-card bonus-stars" onclick="router.navigate('game', {gameId:'TGSTARS'})">
            <div class="emoji">⭐</div>
            <div class="bonus-name">Telegram Stars</div>
            <div class="bonus-desc">Stars & Premium</div>
        </div>
        <div class="bonus-card bonus-crypto" onclick="showToast('Скоро!','info')">
            <div class="emoji">₿</div>
            <div class="bonus-name">Крипта</div>
            <div class="bonus-desc">USDT, TON</div>
        </div>
    </div>`;

    content.innerHTML = html;
}

// ─── GAME PAGE ───
function renderGame(gameId) {
    const content = document.getElementById('page-content');
    const game = GAMES.find(g => g.id === gameId) ||
        { id: 'TGSTARS', name: 'Telegram Stars', emoji: '⭐', color: '#f59e0b' };
    const products = state.catalog.filter(p => p.category === gameId && p.buyer_product_status);

    let html = `
    <button class="back-btn" onclick="router.navigate('home')">← Назад</button>
    <h2 class="section-title">${game.emoji} ${game.name}</h2>
    <p class="section-subtitle">${products.length} товаров доступно</p>
    <div class="product-list">`;

    if (products.length === 0) {
        html += `<div class="empty-state"><div class="emoji">📦</div><p>Товары загружаются...</p></div>`;
    }

    // Emoji map for product types
    const emojiMap = (name) => {
        const n = name.toLowerCase();
        if (n.includes('diamond')) return '💎';
        if (n.includes('pass') || n.includes('royale')) return '🎫';
        if (n.includes('uc') || n.includes('cp') || n.includes('robux')) return '💰';
        if (n.includes('gem')) return '💎';
        if (n.includes('gold')) return '🪙';
        if (n.includes('crystal')) return '✨';
        if (n.includes('token')) return '🏅';
        if (n.includes('welkin')) return '🌙';
        if (n.includes('battle')) return '⚔️';
        if (n.includes('member')) return '⭐';
        if (n.includes('star')) return '⭐';
        if (n.includes('premium')) return '👑';
        return '🎁';
    };

    for (const p of products) {
        html += `
        <div class="product-item" onclick="openBuySheet('${p.buyer_sku_code}')">
            <div class="product-emoji">${emojiMap(p.product_name)}</div>
            <div class="product-info">
                <div class="product-name">${p.product_name}</div>
            </div>
            <div class="product-price">${p.sell_price.toLocaleString('ru')} UZS</div>
        </div>`;
    }
    html += `</div>`;
    content.innerHTML = html;
}

// ─── BUY SHEET ───
function openBuySheet(sku) {
    const product = state.catalog.find(p => p.buyer_sku_code === sku);
    if (!product) return;

    const sheetContent = document.getElementById('sheet-content');
    sheetContent.innerHTML = `
        <h2 style="margin-bottom:4px">${product.product_name}</h2>
        <p style="color:var(--accent-light);font-size:20px;font-weight:700;margin-bottom:20px">
            ${product.sell_price.toLocaleString('ru')} UZS
        </p>
        <div class="sheet-input-group">
            <label>Player ID / Game ID</label>
            <input type="text" id="buy-player-id" placeholder="Введите ваш игровой ID">
        </div>
        <p style="font-size:12px;color:var(--tg-theme-hint-color);margin-bottom:16px">
            💰 Ваш баланс: ${state.balance.toLocaleString('ru')} UZS
        </p>
        <button class="btn-primary" onclick="executeBuy('${sku}')" 
                ${state.balance < product.sell_price ? 'disabled' : ''}>
            ${state.balance < product.sell_price ? '❌ Недостаточно средств' : '⚡ Купить'}
        </button>
        ${state.balance < product.sell_price ?
            '<button class="btn-secondary" style="margin-top:8px" onclick="closeSheet();router.navigate(\'deposit\')">Пополнить баланс</button>' : ''}
    `;
    openSheet();
}

async function executeBuy(sku) {
    const playerId = document.getElementById('buy-player-id').value.trim();
    if (!playerId) { showToast('Введите Player ID', 'error'); return; }

    closeSheet();
    showToast('⏳ Отправляем заказ...', 'info');

    try {
        const res = await fetch(`${API}/api/buy`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tg_id: state.tg_id, buyer_sku_code: sku, customer_no: playerId })
        });
        const data = await res.json();
        if (data.ok) {
            showToast('✅ Заказ отправлен! Ожидайте доставку.', 'success');
            await refreshBalance();
        } else {
            showToast(data.error || 'Ошибка', 'error');
        }
    } catch (e) {
        showToast('Ошибка сети', 'error');
    }
}

// ─── DEPOSIT PAGE ───
function renderDeposit() {
    const content = document.getElementById('page-content');
    const amounts = [5000, 10000, 25000, 50000, 100000, 200000];

    let html = `
    <h2 class="section-title">💳 Пополнить баланс</h2>
    <p class="section-subtitle">Выберите сумму или введите свою</p>
    <div class="amount-grid">`;

    for (const a of amounts) {
        html += `<button class="amount-btn" onclick="selectAmount(this, ${a})">${(a).toLocaleString('ru')}</button>`;
    }
    html += `</div>`;

    html += `
    <input type="number" class="custom-amount" id="deposit-amount" placeholder="Или введите свою сумму (мин. 1 000)" min="1000">
    <button class="btn-primary" onclick="createDeposit()">Перейти к оплате</button>`;

    content.innerHTML = html;
}

function selectAmount(btn, amount) {
    document.querySelectorAll('.amount-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    document.getElementById('deposit-amount').value = amount;
}

async function createDeposit() {
    const amount = parseInt(document.getElementById('deposit-amount').value);
    if (!amount || amount < 1000) {
        showToast('Минимум 1 000 UZS', 'error'); return;
    }

    showToast('⏳ Создаём заявку...', 'info');
    try {
        const res = await fetch(`${API}/api/deposit/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tg_id: state.tg_id, amount })
        });
        const data = await res.json();
        if (data.ok) {
            router.navigate('deposit-pay', data);
        } else {
            showToast(data.error || 'Ошибка', 'error');
        }
    } catch (e) {
        showToast('Ошибка сети', 'error');
    }
}

// ─── DEPOSIT PAY PAGE ───
function renderDepositPay(params) {
    const content = document.getElementById('page-content');
    let timeLeft = params.expires_in || 300;

    content.innerHTML = `
    <button class="back-btn" onclick="router.navigate('deposit')">← Назад</button>
    <h2 class="section-title">⏳ Ожидание перевода</h2>
    
    <div class="payment-card">
        <div class="label">Номер карты</div>
        <div class="card-num" onclick="copyText('${params.card_number}')">${params.card_number} 📋</div>
        <div class="label">Переведите РОВНО</div>
        <div class="amount-display">${params.locked_amount?.toLocaleString('ru')} UZS</div>
        <div class="holder">${params.card_holder}</div>
    </div>
    
    <div class="timer" id="deposit-timer">05:00</div>
    
    <p style="text-align:center;font-size:13px;color:var(--tg-theme-hint-color);margin-bottom:20px">
        ⚠️ Если переведёте другую сумму — платёж не будет идентифицирован!
    </p>
    
    <button class="btn-primary" onclick="checkDeposit(${params.payment_id})">✅ Я оплатил</button>
    `;

    // Timer
    const timerEl = document.getElementById('deposit-timer');
    const interval = setInterval(() => {
        timeLeft--;
        if (timeLeft <= 0) {
            clearInterval(interval);
            timerEl.textContent = '00:00';
            timerEl.style.color = 'var(--danger)';
            return;
        }
        const m = Math.floor(timeLeft / 60);
        const s = timeLeft % 60;
        timerEl.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }, 1000);
}

async function checkDeposit(paymentId) {
    try {
        const res = await fetch(`${API}/api/deposit/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tg_id: state.tg_id, payment_id: paymentId })
        });
        const data = await res.json();
        if (data.ok) {
            showToast(data.message || 'Отправлено на проверку!', 'success');
            await refreshBalance();
        } else {
            showToast(data.error || 'Ошибка', 'error');
        }
    } catch (e) {
        showToast('Ошибка сети', 'error');
    }
}

// ─── ORDERS ───
async function renderOrders() {
    const content = document.getElementById('page-content');
    content.innerHTML = `<h2 class="section-title">📦 Мои заказы</h2><div class="loading"><div class="spinner"></div></div>`;

    try {
        const res = await fetch(`${API}/api/orders/${state.tg_id}`);
        const data = await res.json();

        if (!data.ok || !data.data.length) {
            content.innerHTML = `<h2 class="section-title">📦 Мои заказы</h2>
            <div class="empty-state"><div class="emoji">📭</div><p>Заказов пока нет</p></div>`;
            return;
        }

        let html = `<h2 class="section-title">📦 Мои заказы</h2>`;
        for (const o of data.data) {
            const statusClass = o.status === 'success' ? 'status-success' :
                o.status === 'failed' ? 'status-failed' : 'status-pending';
            const statusText = o.status === 'success' ? 'Доставлено' :
                o.status === 'failed' ? 'Ошибка' : 'В обработке';
            html += `
            <div class="order-item">
                <div class="order-header">
                    <div class="order-product">${o.product_name}</div>
                    <span class="status-badge ${statusClass}">${statusText}</span>
                </div>
                <div class="order-id">ID: ${o.customer_no} • ${o.sell_price.toLocaleString('ru')} UZS</div>
            </div>`;
        }
        content.innerHTML = html;
    } catch (e) {
        content.innerHTML = `<h2 class="section-title">📦 Мои заказы</h2>
        <div class="empty-state"><div class="emoji">🌐</div><p>Нет подключения к серверу</p></div>`;
    }
}

// ─── PROFILE ───
function renderProfile() {
    const content = document.getElementById('page-content');
    let html = `
    <div class="profile-header">
        <div class="profile-avatar">⚡</div>
        <div class="profile-name">${state.name}</div>
        <div class="profile-id">ID: ${state.tg_id}</div>
    </div>
    
    <div class="profile-balance-card">
        <div class="profile-balance-label">Баланс</div>
        <div class="profile-balance-amount">${state.balance.toLocaleString('ru')} UZS</div>
    </div>
    
    <div class="menu-list">
        <div class="menu-item" onclick="router.navigate('deposit')">
            <span class="menu-icon">💳</span>
            <span class="menu-text">Пополнить баланс</span>
            <span class="menu-arrow">→</span>
        </div>
        <div class="menu-item" onclick="router.navigate('orders')">
            <span class="menu-icon">📦</span>
            <span class="menu-text">Мои заказы</span>
            <span class="menu-arrow">→</span>
        </div>`;

    if (state.is_admin) {
        html += `
        <div class="menu-item" onclick="router.navigate('admin')" style="border-color:var(--accent)">
            <span class="menu-icon">🔧</span>
            <span class="menu-text">Админ-панель</span>
            <span class="menu-arrow">→</span>
        </div>`;
    }

    html += `</div>`;
    content.innerHTML = html;
}

// ─── ADMIN ───
async function renderAdmin() {
    const content = document.getElementById('page-content');
    content.innerHTML = `<h2 class="section-title">🔧 Админ-панель</h2><div class="loading"><div class="spinner"></div></div>`;

    try {
        const [settingsRes, paymentsRes, statsRes] = await Promise.all([
            fetch(`${API}/api/admin/settings`),
            fetch(`${API}/api/admin/payments`),
            fetch(`${API}/api/admin/stats`)
        ]);
        const settings = (await settingsRes.json()).data || {};
        const payments = (await paymentsRes.json()).data || [];
        const stats = (await statsRes.json());

        let html = `
        <button class="back-btn" onclick="router.navigate('profile')">← Назад</button>
        <h2 class="section-title">🔧 Админ-панель</h2>
        
        <!-- Stats -->
        <div class="admin-card">
            <h3>📊 Статистика</h3>
            <div class="stat-grid">
                <div class="stat-card"><div class="stat-value">${stats.users || 0}</div><div class="stat-label">Пользователи</div></div>
                <div class="stat-card"><div class="stat-value">${stats.orders || 0}</div><div class="stat-label">Заказы</div></div>
                <div class="stat-card"><div class="stat-value">${(stats.revenue || 0).toLocaleString('ru')}</div><div class="stat-label">Выручка UZS</div></div>
                <div class="stat-card"><div class="stat-value">${(stats.supplier_balance || 0).toLocaleString('ru')}</div><div class="stat-label">Баланс Digiflazz</div></div>
            </div>
        </div>
        
        <!-- Pending payments -->
        <div class="admin-card">
            <h3>💳 Ожидающие платежи (${payments.length})</h3>`;

        if (payments.length === 0) {
            html += `<p style="color:var(--tg-theme-hint-color);font-size:13px">Нет ожидающих платежей</p>`;
        }
        for (const p of payments) {
            html += `
            <div class="admin-payment-item">
                <div>
                    <div style="font-weight:600">${p.name || 'User'} • ${p.locked_amount?.toLocaleString('ru')} UZS</div>
                    <div style="font-size:11px;color:var(--tg-theme-hint-color)">
                        База: ${p.base_amount?.toLocaleString('ru')} | Статус: ${p.status}
                    </div>
                </div>
                <button class="admin-approve-btn" onclick="approvePayment(${p.id})">✅</button>
            </div>`;
        }

        html += `</div>
        
        <!-- Settings -->
        <div class="admin-card">
            <h3>⚙️ Настройки</h3>
            <div class="admin-field">
                <label>Номер карты</label>
                <input id="set-card_number" value="${settings.card_number || ''}" onchange="saveSetting('card_number', this.value)">
            </div>
            <div class="admin-field">
                <label>Имя держателя карты</label>
                <input id="set-card_holder" value="${settings.card_holder || ''}" onchange="saveSetting('card_holder', this.value)">
            </div>
            <div class="admin-field">
                <label>Наценка (%)</label>
                <input id="set-markup" type="number" value="${settings.markup_percent || 25}" onchange="saveSetting('markup_percent', this.value)">
            </div>
            <div class="admin-field">
                <label>Мин. баланс Digiflazz (рубильник)</label>
                <input type="number" value="${settings.min_supplier_balance || 50000}" onchange="saveSetting('min_supplier_balance', this.value)">
            </div>
        </div>
        
        <div class="admin-card">
            <h3>🔑 API Digiflazz</h3>
            <div class="admin-field">
                <label>Username</label>
                <input value="${settings.df_username || ''}" onchange="saveSetting('df_username', this.value)">
            </div>
            <div class="admin-field">
                <label>API Key</label>
                <input value="${settings.df_api_key || ''}" onchange="saveSetting('df_api_key', this.value)">
            </div>
            <div class="admin-field">
                <label>Base URL</label>
                <input value="${settings.df_base_url || ''}" onchange="saveSetting('df_base_url', this.value)">
            </div>
        </div>`;

        content.innerHTML = html;
    } catch (e) {
        content.innerHTML = `<h2 class="section-title">🔧 Админ-панель</h2>
        <div class="empty-state"><p>Ошибка загрузки</p></div>`;
    }
}

async function approvePayment(id) {
    try {
        const res = await fetch(`${API}/api/admin/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ payment_id: id })
        });
        const data = await res.json();
        showToast(data.message || data.error, data.ok ? 'success' : 'error');
        if (data.ok) renderAdmin();
    } catch (e) {
        showToast('Ошибка', 'error');
    }
}

async function saveSetting(key, value) {
    try {
        await fetch(`${API}/api/admin/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key, value })
        });
        showToast('Сохранено!', 'success');
    } catch (e) {
        showToast('Ошибка', 'error');
    }
}

// ─── Sheet helpers ───
function openSheet() {
    document.getElementById('overlay').classList.add('show');
    document.getElementById('bottom-sheet').classList.add('show');
    document.body.style.overflow = 'hidden';
}
function closeSheet() {
    document.getElementById('overlay').classList.remove('show');
    document.getElementById('bottom-sheet').classList.remove('show');
    document.body.style.overflow = '';
}

// Swipe to close
let sheetStartY = 0;
document.getElementById('bottom-sheet')?.addEventListener('touchstart', e => {
    sheetStartY = e.touches[0].clientY;
}, { passive: true });
document.getElementById('bottom-sheet')?.addEventListener('touchmove', e => {
    if (e.touches[0].clientY - sheetStartY > 60) closeSheet();
}, { passive: true });

// ─── Toast ───
function showToast(msg, type = 'info') {
    let toast = document.querySelector('.toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.className = `toast ${type} show`;
    setTimeout(() => toast.classList.remove('show'), 2500);
}

// ─── Copy ───
function copyText(text) {
    navigator.clipboard?.writeText(text).then(() => showToast('Скопировано!', 'success'));
}

// ─── Start ───
init();
