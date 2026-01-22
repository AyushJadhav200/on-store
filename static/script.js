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

    /* --- CART LOGIC --- */
    const cartSidebar = document.getElementById('cartSidebar');
    const cartOverlay = document.getElementById('cartOverlay');
    const cartToggle = document.getElementById('cartToggle');
    const closeCart = document.getElementById('closeCart');
    const cartItemsContainer = document.getElementById('cartItems');
    const cartTotalElement = document.getElementById('cartTotal');
    const cartCountElement = document.getElementById('cartCount');

    // Open/Close Cart
    function toggleCart() {
        cartSidebar.classList.toggle('open');
        cartOverlay.classList.toggle('open');
    }

    if (cartToggle) cartToggle.addEventListener('click', toggleCart);
    if (closeCart) closeCart.addEventListener('click', toggleCart);
    if (cartOverlay) cartOverlay.addEventListener('click', toggleCart);

    // Fetch Cart
    async function fetchCart() {
        try {
            const response = await fetch('/api/cart');
            const data = await response.json();
            renderCart(data);
        } catch (error) {
            console.error('Error fetching cart:', error);
        }
    }

    // Render Cart
    function renderCart(data) {
        if (!cartItemsContainer) return;
        cartItemsContainer.innerHTML = '';
        let count = 0;

        if (!data.items || Object.keys(data.items).length === 0) {
            cartItemsContainer.innerHTML = '<p style="text-align:center; padding: 2rem;">Your basket is empty.</p>';
        } else {
            for (const [id, item] of Object.entries(data.items)) {
                count += item.quantity;
                const itemHTML = `
                    <div class="cart-item">
                        <img src="${item.image}" alt="${item.name}">
                        <div class="cart-item-info">
                            <div class="cart-item-title">${item.name}</div>
                            <div class="cart-item-price">₹ ${item.price} x ${item.quantity}</div>
                            <div class="remove-item" onclick="removeFromCart('${id}')" title="Remove Item">&minus;</div>
                        </div>
                    </div>
                `;
                cartItemsContainer.insertAdjacentHTML('beforeend', itemHTML);
            }
        }

        if (cartTotalElement) cartTotalElement.textContent = '₹ ' + data.total.toLocaleString('en-IN');
        if (cartCountElement) cartCountElement.textContent = count;
    }

    // Toast Helper
    function showToast(message) {
        const toast = document.getElementById('toast');
        toast.className = 'toast show';
        toast.innerText = message || "Product added to bag!";
        setTimeout(function () { toast.className = toast.className.replace('show', ''); }, 3000);
    }

    // Add to Cart
    document.querySelectorAll('.product-card .btn-primary').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const card = e.target.closest('.product-card');
            const name = card.querySelector('.product-title').innerText;
            const price = card.querySelector('.product-price').innerText;
            const image = card.querySelector('.product-image').getAttribute('src');

            try {
                // IMPORTANT: We need correct image path for backend
                // If using relative path like ../static/..., backend might just store it as string
                const response = await fetch('/api/cart/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, price, image })
                });

                if (!response.ok) throw new Error('Network response was not ok');

                const result = await response.json();
                if (result.status === 'success') {
                    showToast("1 product added to bag");
                    // Open cart to show item/success
                    if (!cartSidebar.classList.contains('open')) toggleCart();
                    fetchCart();
                }
            } catch (error) {
                console.error('Error adding to cart:', error);

                // Fallback for user experience if server is down or file opened directly
                alert("To use the Shopping Cart, please make sure the Flask server is running!\n\nRun 'python app.py' in your terminal.");
            }
        });
    });

    // Remove from Cart
    window.removeFromCart = async (id) => {
        try {
            const response = await fetch('/api/cart/remove', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id })
            });
            const data = await response.json();
            fetchCart();
        } catch (error) {
            console.error('Error removing from cart:', error);
            alert("Error connecting to server. Is it running?");
        }
    };

    // Initial Load
    fetchCart();
});
