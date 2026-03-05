const tg = window.Telegram.WebApp;

// Разворачиваем и убираем окно подтверждения закрытия
tg.expand();
tg.disableClosingConfirmation();
tg.ready();

// Установка имени пользователя в шапке
const userNameElement = document.getElementById('user-name');
if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
    userNameElement.textContent = tg.initDataUnsafe.user.first_name || 'Игрок';
}

// 3. Тестовый Каталог (Mock Data)
const mockData = [
    { id: 'mlbb_86', category: 'MLBB', name: '86 Diamonds', price: '16 000 UZS' },
    { id: 'mlbb_172', category: 'MLBB', name: '172 Diamonds', price: '32 000 UZS' },
    { id: 'mlbb_257', category: 'MLBB', name: '257 Diamonds', price: '48 000 UZS' },
    { id: 'pubg_60', category: 'PUBG', name: '60 UC', price: '15 000 UZS' },
    { id: 'pubg_325', category: 'PUBG', name: '325 UC', price: '70 000 UZS' },
    { id: 'pubg_660', category: 'PUBG', name: '660 UC', price: '140 000 UZS' },
    { id: 'ff_100', category: 'Free Fire', name: '100 Diamonds', price: '14 000 UZS' },
    { id: 'ff_210', category: 'Free Fire', name: '210 Diamonds', price: '28 000 UZS' },
    { id: 'genshin_60', category: 'Genshin Impact', name: '60 Crystals', price: '15 000 UZS' },
    { id: 'genshin_300', category: 'Genshin Impact', name: '300 Crystals', price: '75 000 UZS' }
];

const categories = ['Все', 'MLBB', 'PUBG', 'Free Fire', 'Genshin Impact'];
let currentCategory = 'Все';
let selectedProduct = null;

const categoriesContainer = document.getElementById('categories-container');
const productsGrid = document.getElementById('products-grid');
const overlay = document.getElementById('overlay');
const bottomSheet = document.getElementById('bottom-sheet');
const sheetProductName = document.getElementById('sheet-product-name');
const sheetProductPrice = document.getElementById('sheet-product-price');
const playerIdInput = document.getElementById('player-id');
const confirmBtn = document.getElementById('confirm-btn');

function renderCategories() {
    categoriesContainer.innerHTML = '';
    categories.forEach(cat => {
        const btn = document.createElement('button');
        btn.className = `category-chip ${currentCategory === cat ? 'active' : ''}`;
        btn.textContent = cat;
        btn.onclick = () => {
            currentCategory = cat;
            renderCategories();
            renderProducts();
        };
        categoriesContainer.appendChild(btn);
    });
}

function renderProducts() {
    productsGrid.innerHTML = '';
    const filteredProducts = currentCategory === 'Все'
        ? mockData
        : mockData.filter(p => p.category === currentCategory);

    filteredProducts.forEach(product => {
        const card = document.createElement('div');
        card.className = 'product-card';
        card.onclick = () => openBottomSheet(product);

        card.innerHTML = `
            <div class="product-category">${product.category}</div>
            <div class="product-name">${product.name}</div>
            <div class="product-price">${product.price}</div>
        `;
        productsGrid.appendChild(card);
    });
}

function openBottomSheet(product) {
    selectedProduct = product;
    sheetProductName.textContent = product.name;
    sheetProductPrice.textContent = product.price;
    playerIdInput.value = '';
    playerIdInput.placeholder = `Введите Player ID для ${product.category}`;

    overlay.classList.add('show');
    bottomSheet.classList.add('show');
    document.body.style.overflow = 'hidden'; // Блокируем скролл фона
}

function closeBottomSheet() {
    overlay.classList.remove('show');
    bottomSheet.classList.remove('show');
    selectedProduct = null;
    document.body.style.overflow = ''; // Восстанавливаем скролл
}

overlay.onclick = closeBottomSheet;

// Закрытие шторки свайпом вниз
let startY = 0;
let currentY = 0;

bottomSheet.addEventListener('touchstart', (e) => {
    startY = e.touches[0].clientY;
}, { passive: true });

bottomSheet.addEventListener('touchmove', (e) => {
    currentY = e.touches[0].clientY;
    if (currentY - startY > 60) {
        closeBottomSheet();
    }
}, { passive: true });

// 4. Интеграция с Telegram (отправка данных)
confirmBtn.onclick = () => {
    const playerId = playerIdInput.value.trim();
    if (!playerId) {
        tg.showAlert('Пожалуйста, введите Player ID');
        return;
    }

    if (!selectedProduct) return;

    const dataToSend = {
        action: 'buy',
        product_id: selectedProduct.id,
        player_id: playerId
    };

    tg.sendData(JSON.stringify(dataToSend));
    closeBottomSheet();
};

// Поддержка смены темы (хотя CSS переменные уже работают)
if (tg.colorScheme === 'dark') {
    document.body.setAttribute('data-theme', 'dark');
}
tg.onEvent('themeChanged', () => {
    if (tg.colorScheme === 'dark') {
        document.body.setAttribute('data-theme', 'dark');
    } else {
        document.body.setAttribute('data-theme', 'light');
    }
});

// Инициализация
renderCategories();
renderProducts();
