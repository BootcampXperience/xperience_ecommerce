import streamlit as st
import stripe
import os
from datetime import datetime

if 'login' not in st.session_state:
    st.switch_page('app.py')

# CSS personalizado para el diseño de lujo
with open("estilos/css_catalogo.html", "r") as file:
    html_content = file.read()
st.markdown(html_content, unsafe_allow_html=True)

# Configuración de Stripe
#stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]

# Funciones de Firestore
def get_products():
    """Obtiene productos desde Firestore"""
    try:
        products_ref = st.session_state.db.collection('products')
        docs = products_ref.stream()
        
        products = []
        for doc in docs:
            product = doc.to_dict()
            product['id'] = doc.id
            products.append(product)
        
        # Si no hay productos, crear algunos de ejemplo
        if not products:
            sample_products = [
                {
                    "name": "Vestido Elegante",
                    "price": 89.99,
                    "image": "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400",
                    "description": "Vestido elegante perfecto",
                    "category": "vestidos",
                    "stock": 15
                },
                {
                    "name": "Blusa Casual",
                    "price": 45.99,
                    "image": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400",
                    "description": "Blusa cómoda y versátil para el día a día",
                    "category": "blusas",
                    "stock": 25
                },
                {
                    "name": "Jeans Premium",
                    "price": 79.99,
                    "image": "https://images.unsplash.com/photo-1542272604-787c3835535d?w=400",
                    "description": "Jeans de alta calidad con corte moderno",
                    "category": "pantalones",
                    "stock": 20
                },
                {
                    "name": "Chaqueta de Cuero",
                    "price": 129.99,
                    "image": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=400",
                    "description": "Chaqueta de cuero auténtico, estilo urbano",
                    "category": "chaquetas",
                    "stock": 8
                },
                {
                    "name": "Zapatos Elegantes",
                    "price": 95.99,
                    "image": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=400",
                    "description": "Zapatos elegantes para completar tu look",
                    "category": "zapatos",
                    "stock": 12
                },
                {
                    "name": "Bolso de Mano",
                    "price": 65.99,
                    "image": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400",
                    "description": "Bolso de mano versátil y elegante",
                    "category": "accesorios",
                    "stock": 18
                }
            ]
            
            # Agregar productos de ejemplo a Firestore
            for product in sample_products:
                st.session_state.db.collection('products').add(product)
            
            return sample_products
        
        return products
    
    except Exception as e:
        st.error(f"Error al obtener productos: {str(e)}")
        return []

def add_to_cart(product_id, user_id):
    """Agrega producto al carrito"""
    try:
        cart_ref = st.session_state.db.collection('carts').document(user_id)
        cart_doc = cart_ref.get()
        
        if cart_doc.exists:
            cart_data = cart_doc.to_dict()
            items = cart_data.get('items', [])
            
            # Verificar si el producto ya está en el carrito
            product_exists = False
            for item in items:
                if item['product_id'] == product_id:
                    item['quantity'] += 1
                    product_exists = True
                    break
            
            if not product_exists:
                items.append({
                    'product_id': product_id,
                    'quantity': 1,
                    'added_at': datetime.now()
                })
            
            cart_ref.update({'items': items})
        else:
            cart_ref.set({
                'items': [{
                    'product_id': product_id,
                    'quantity': 1,
                    'added_at': datetime.now()
                }],
                'created_at': datetime.now()
            })
        
        return True
    
    except Exception as e:
        st.error(f"Error al agregar al carrito: {str(e)}")
        return False

# Funciones de Stripe
def create_checkout_session(items, user_email):
    """Crea una sesión de pago con Stripe"""
    try:
        line_items = []
        for item in items:
            line_items.append({
                'price_data': {
                    'currency': 'brl',
                    'product_data': {
                        'name': item['name'],
                        'images': [item['image']],
                    },
                    'unit_amount': int(item['price'] * 100),
                },
                'quantity': item['quantity'],
            })
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url='https://xperience-ecommerce.streamlit.app?payment=success&session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://xperience-ecommerce.streamlit.app?payment=cancelled&session_id={CHECKOUT_SESSION_ID}',
            customer_email=user_email,
            metadata={
                'user_id': st.session_state['usuario']['uid'],
                'user_name': st.session_state['usuario']['nombre']
            }
        )
        
        return checkout_session.url, checkout_session.id
    
    except Exception as e:
        st.error(f"Error al crear sesión de pago: {str(e)}")
        return None

# Función para guardar carrito en Firestore
def save_cart_to_firestore(session_id, user_id, cart_items):
    """Guarda el carrito en Firestore antes de ir a Stripe"""
    try:
        cart_data = {
            'session_id': session_id,
            'user_id': user_id,
            'items': cart_items,
            'created_at': datetime.now(),
            'status': 'pending_payment'
        }
        
        # Guardar en la colección 'carts' para recuperar después
        st.session_state.db.collection('carts').document(session_id).set(cart_data)
        
    except Exception as e:
        st.error(f"Error al guardar carrito: {str(e)}")

def clear_user_cart(session_id):
    """Limpia el carrito del usuario después de la compra"""
    try:
        cart_ref = st.session_state.db.collection('carts').document(session_id)
        cart_ref.delete()        
    except Exception as e:
        st.error(f"Sin datos en el carrito: {str(e)}")

def create_stripe_button(cart, user_email, user_uid):
    checkout_url, session_id = create_checkout_session(cart, user_email)
    
    if checkout_url and session_id:
        if 'stripe_session_id' in st.session_state: clear_user_cart(st.session_state['stripe_session_id'])
        st.session_state['stripe_session_id'] = session_id
        save_cart_to_firestore(session_id, user_uid, cart)
        
        # Estilo idéntico al botón morado de la imagen
        button_html = f"""
        <style>
        .payment-container a {{
            text-decoration: none;
            color: inherit;
        }}
        
        .payment-container button {{
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 25px;
            padding: 0.75rem 2rem;
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            outline: none;
            box-sizing: border-box;
            margin: 0.5rem 0;
            width: auto;
            vertical-align: middle;
            font-size: 1rem;
            line-height: 1.2;
        }}
        
        .payment-container button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }}
        
        .payment-container button:active {{
            transform: translateY(0);
        }}
        </style>
        
        <div class="payment-container" style="display: flex; justify-content: flex-start; margin: 0.25rem 0px;">
            <a href="{checkout_url}" target="_self">
                <button>
                    💳 Proceder al Pago
                </button>
            </a>
        </div>
        """
        return button_html
    return None

# --- LÓGICA PRINCIPAL DE LA PÁGINA ---
st.markdown('<div class="main-header"><h1>🛍️ Fashion Store</h1><p>Bienvenido/a a tu tienda de moda</p></div>', unsafe_allow_html=True)

# Sidebar con información del usuario y carrito
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state['usuario']['nombre']}")
    
    if st.button("🚪 Cerrar Sesión"):
        if 'stripe_session_id' in st.session_state: clear_user_cart(st.session_state['stripe_session_id'])
        st.session_state.clear()
        st.rerun()
    
    st.markdown("---")
    
    # Carrito de compras
    st.markdown("### 🛒 Carrito")
    if st.session_state.cart:
        total = 0
        for item in st.session_state.cart:
            st.markdown(f"""
            <div class="cart-item">
                <strong>{item['name']}</strong><br>
                ${item['price']:.2f} x {item['quantity']}
            </div>
            """, unsafe_allow_html=True)
            total += item['price'] * item['quantity']
        
        st.markdown(f"**Total: ${total:.2f}**")

        stripe_button = create_stripe_button(
            st.session_state.cart, 
            st.session_state['usuario']['email'], 
            st.session_state['usuario']['uid']
        )

        if stripe_button:
            st.markdown(stripe_button, unsafe_allow_html=True)
        else:
            st.error("Error al crear la sesión de pago")
    else:
        st.info("Tu carrito está vacío")

# Contenido principal - Catálogo de productos
st.markdown("## 🛍️ Catálogo de Productos")

# Filtros
col1, col2 = st.columns([1, 3])
with col1:
    categories = ["todos", "vestidos", "blusas", "pantalones", "chaquetas", "zapatos", "accesorios"]
    selected_category = st.selectbox("Categoría", categories)

# Obtener productos
products = get_products()

# Filtrar por categoría
if selected_category != "todos":
    products = [p for p in products if p.get('category') == selected_category]

# Mostrar productos en grid
if products:
    # Crear grid de productos
    cols = st.columns(3)
    
    for idx, product in enumerate(products):
        with cols[idx % 3]:
            st.markdown(f"""
            <div class="product-card">
                <img src="{product['image']}" style="width: 100%; height: 200px; object-fit: cover; border-radius: 10px;">
                <h3 style="margin: 1rem 0 0.5rem 0; color: #333;">{product['name']}</h3>
                <p style="color: #666; margin-bottom: 1rem;">{product['description']}</p>
                <div class="price-tag">${product['price']:.2f}</div>
                <p style="color: #999; font-size: 0.9rem;">Stock: {product['stock']} unidades</p>
            </div>
            """, unsafe_allow_html=True)
            
            col4, col5, col6 = st.columns([0.5,2,0.5])
            with col5:
                if st.button(f"🛒 Agregar al Carrito", key=f"add_{product.get('id', idx)}"):
                    # Agregar al carrito en memoria (para demo)
                    cart_item = {
                        'name': product['name'],
                        'price': product['price'],
                        'quantity': 1,
                        'image': product['image']
                    }
                    
                    # Verificar si ya existe en el carrito
                    existing_item = next((item for item in st.session_state.cart if item['name'] == product['name']), None)
                    if existing_item:
                        existing_item['quantity'] += 1
                    else:
                        st.session_state.cart.append(cart_item)
                    
                    st.success(f"✅ {product['name']} agregado al carrito!")
                    st.rerun()
else:
    st.info("No se encontraron productos en esta categoría.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem;">
    <p>🛍️ Fashion Store - Tu estilo, nuestra pasión</p>
    <p>Desarrollado con ❤️ usando Streamlit, Firebase y Stripe</p>
</div>
""", unsafe_allow_html=True)
