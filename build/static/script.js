document.addEventListener('DOMContentLoaded', () => {
    // Mobile Navigation Toggle
    const mobileBtn = document.querySelector('.mobile-menu-btn');
    const navLinks = document.querySelector('.nav-links');

    if (mobileBtn) {
        mobileBtn.addEventListener('click', () => {
            navLinks.style.display = navLinks.style.display === 'flex' ? 'none' : 'flex';
            if (navLinks.style.display === 'flex') {
                navLinks.style.flexDirection = 'column';
                navLinks.style.position = 'absolute';
                navLinks.style.top = '100%';
                navLinks.style.left = '0';
                navLinks.style.width = '100%';
                navLinks.style.backgroundColor = '#FDFBF7';
                navLinks.style.padding = '1rem';
                navLinks.style.boxShadow = '0 4px 6px rgba(0,0,0,0.05)';
            }
        });
    }

    // Smooth Scroll for navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
            // Close mobile menu if open
            if (window.innerWidth <= 968) {
                navLinks.style.display = 'none';
            }
        });
    });

    // Intersection Observer for Animations on Scroll
    const observerOptions = {
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Animate Elements Helper
    const observeElements = (elements, stagger = true) => {
        elements.forEach((el, index) => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            // Reset delay for each group logic could be complex, simple stagger is fine
            // If we iterate a NodeList, index is 0..N.
            el.style.transition = `all 0.6s ease ${stagger ? (index % 3) * 0.1 : 0}s`;
            observer.observe(el);
        });
    };

    // Apply animations
    observeElements(document.querySelectorAll('.product-card'));
    observeElements(document.querySelectorAll('.testimonial-card'));
    observeElements(document.querySelectorAll('.about-content'), false);
    observeElements(document.querySelectorAll('.about-image-wrapper'), false);
    observeElements(document.querySelectorAll('.newsletter-wrapper'), false);

    /* --- CART LOGIC (LOCAL STORAGE) --- */
    const cartSidebar = document.getElementById('cartSidebar');
    const cartOverlay = document.getElementById('cartOverlay');
    const cartToggle = document.getElementById('cartToggle');
    const closeCart = document.getElementById('closeCart');
    const cartItemsContainer = document.getElementById('cartItems');
    const cartTotalElement = document.getElementById('cartTotal');
    const cartCountElement = document.getElementById('cartCount');

    // Initial Cart Setup
    let cart = JSON.parse(localStorage.getItem('swara_cart')) || {};

    // Open/Close Cart
    function toggleCart() {
        if (!cartSidebar) return;
        cartSidebar.classList.toggle('open');
        cartOverlay.classList.toggle('open');
    }

    if (cartToggle) cartToggle.addEventListener('click', toggleCart);
    if (closeCart) closeCart.addEventListener('click', toggleCart);
    if (cartOverlay) cartOverlay.addEventListener('click', toggleCart);

    // Fetch Cart (Now from LocalStorage)
    function fetchCart() {
        renderCart(cart);
    }

    // Render Cart
    function renderCart(cartItems) {
        if (!cartItemsContainer) return;
        cartItemsContainer.innerHTML = '';
        let count = 0;
        let total = 0;

        const items = Object.entries(cartItems);

        if (items.length === 0) {
            cartItemsContainer.innerHTML = '<p style="text-align:center; padding: 2rem;">Your basket is empty.</p>';
        } else {
            for (const [id, item] of items) {
                count += item.quantity;
                total += item.price * item.quantity;
                const itemHTML = `
                    <div class="cart-item">
                        <img src="${item.image}" alt="${item.name}">
                        <div class="cart-item-info">
                            <div class="cart-item-title">${item.name}</div>
                            <div class="cart-item-price">₹ ${item.price.toLocaleString('en-IN')} x ${item.quantity}</div>
                            <div class="remove-item" onclick="removeFromCart('${id}')" title="Remove Item">&minus;</div>
                        </div>
                    </div>
                `;
                cartItemsContainer.insertAdjacentHTML('beforeend', itemHTML);
            }
        }

        if (cartTotalElement) cartTotalElement.textContent = '₹ ' + total.toLocaleString('en-IN');
        if (cartCountElement) cartCountElement.textContent = count;
        
        // Save to localStorage
        localStorage.setItem('swara_cart', JSON.stringify(cartItems));
    }

    // Toast Helper
    function showToast(message) {
        const toast = document.getElementById('toast');
        if (!toast) return;
        toast.className = 'toast show';
        toast.innerText = message || "Product added to bag!";
        setTimeout(function () { toast.className = toast.className.replace('show', ''); }, 3000);
    }

    // Add to Cart
    document.querySelectorAll('.product-card .btn-primary').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const card = e.target.closest('.product-card');
            const name = card.querySelector('.product-title').innerText;
            const priceText = card.querySelector('.product-price').innerText;
            const price = parseFloat(priceText.replace('₹', '').replace(/,/g, '').strip?.() || priceText.replace('₹', '').replace(/,/g, '').trim());
            const image = card.querySelector('.product-image').getAttribute('src');

            const productId = name; // Using name as ID

            if (cart[productId]) {
                cart[productId].quantity += 1;
            } else {
                cart[productId] = {
                    name: name,
                    price: price,
                    image: image,
                    quantity: 1
                };
            }

            showToast("1 product added to bag");
            if (!cartSidebar.classList.contains('open')) toggleCart();
            fetchCart();
        });
    });

    // Remove from Cart
    window.removeFromCart = (id) => {
        if (cart[id]) {
            if (cart[id].quantity > 1) {
                cart[id].quantity -= 1;
            } else {
                delete cart[id];
            }
            fetchCart();
        }
    };

    // Initial Load
    fetchCart();
});
