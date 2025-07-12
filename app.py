import streamlit as st
import os, re
from urllib.parse import urlencode
import firebase_admin
from firebase_admin import credentials, auth, firestore
import requests
from datetime import datetime
#from dotenv import load_dotenv
#load_dotenv()

# Configuración de la página
st.set_page_config(page_title="Fashion Store",page_icon="🛍️",layout="wide",initial_sidebar_state="expanded")

# CSS personalizado para el diseño de lujo
with open("estilos/css_login.html", "r") as file:
    html_content = file.read()
st.markdown(html_content, unsafe_allow_html=True)

# Se ejecuta una única vez cuando carga la aplicación
if 'has_run' not in st.session_state:
    st.session_state.has_run = True
    #service_account_key_path = 'serviceAccountKey.json'
    service_account_key_path = st.secrets["google_service_account"]
    collection_name = "usuarios"
    st.session_state.redirect_uri = "https://xperience-ecommerce.streamlit.app"

    # --- Inicialización de Firebase ADMIN SDK ---
    if not firebase_admin._apps:
        service_account_dict = dict(service_account_key_path)
        cred = credentials.Certificate(service_account_dict)
        firebase_admin.initialize_app(cred)
    st.session_state.db = firestore.client()

    # Inicia el Cliente de Google
    #st.session_state.google_client_id = os.environ.get("GOOGLE_CLIENT_ID")
    #st.session_state.google_client_secret = os.environ.get("GOOGLE_SECRET_ID")
    st.session_state.google_client_id = st.secrets["GOOGLE_CLIENT_ID"]
    st.session_state.google_client_secret = st.secrets["GOOGLE_SECRET_ID"]

    #Inicializa el carrito de compras
    st.session_state.cart = []

# Autenticación con Google
def google_auth():
    # URL de autorización de Google
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": st.session_state.google_client_id,
        "redirect_uri": st.session_state.redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline"
    }
    
    google_auth_url = f"{auth_url}?{urlencode(params)}"
    return google_auth_url

# Intercambiar código por token
def exchange_code_for_tokens(auth_code):
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": st.session_state.google_client_id,
        "client_secret": st.session_state.google_client_secret,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": st.session_state.redirect_uri
    }
    
    response = requests.post(token_url, data=data)
    
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error al obtener tokens: {response.text}")
        return None

# Obtener datos del usuario
def get_user_info(access_token):
    user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    response = requests.get(user_info_url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error al obtener información del usuario: {response.text}")
        return None

# Verificar o crear usuario en Firebase
def verificar_o_crear_usuario(code):
    try:
        # 1. Intercambiar código por tokens
        tokens = exchange_code_for_tokens(code)
        if not tokens:
            return None
        
        access_token = tokens.get("access_token")
        if not access_token:
            st.error("No se pudo obtener el token de acceso")
            return None
        
        # 2. Obtener información del usuario de Google
        user_info = get_user_info(access_token)
        if not user_info:
            return None
        
        # 3. Extraer datos obligatorios
        google_id = user_info.get('id')
        email = user_info.get('email')
        nombre = user_info.get('name')
        foto = user_info.get('picture')
        
        # Verificar que los datos obligatorios estén presentes
        if not all([google_id, email, nombre, foto]):
            st.error("Faltan datos obligatorios del usuario de Google")
            return None
        
        # 4. Verificar si el usuario ya existe en Firebase
        doc_ref = st.session_state.db.collection('usuarios').document(google_id)
        doc = doc_ref.get()
        
        if doc.exists:
            # Usuario existente - cargar datos y actualizar último login
            usuario_data = doc.to_dict()
            usuario_data['last_login'] = datetime.now()
            usuario_data['uid'] = google_id
            
            # Actualizar último login en Firebase
            doc_ref.update({'last_login': datetime.now()})
            
            return usuario_data
        else:
            # Usuario nuevo - crear en Firebase
            nuevo_usuario = {
                'uid': google_id,
                'email': email,
                'nombre': re.sub(r"\s*\(.*?\)", "", nombre).strip(),
                'foto': foto,
                'verified_email': user_info.get('verified_email', False),
                'locale': user_info.get('locale', 'en'),
                'created_at': datetime.now(),
                'last_login': datetime.now()
            }
            
            # Guardar en Firebase
            doc_ref.set(nuevo_usuario)
            
            return nuevo_usuario
            
    except Exception as e:
        st.error(f"Error durante la verificación/creación del usuario: {str(e)}")
        return None

# Función para simular el botón de Google
def google_login_button():
    google_svg = """<svg class="google-icon" viewBox="0 0 24 24">
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
    </svg>
    """

    button_html = f"""<button class="google-login-btn">{google_svg}Continue with Google</button>"""
    return f"""<a href="{google_auth()}" target="_self" style="text-decoration: none;">{button_html}</a>"""

# Función para recuperar el usuario basado en session_id
def get_user_from_firestore(session_id):
    """Recupera el usuario desde Firestore usando session_id del carrito"""
    try:
        # Buscar el documento del carrito por session_id
        cart_doc = st.session_state.db.collection('carts').document(session_id).get()
        
        if cart_doc.exists:
            cart_data = cart_doc.to_dict()
            user_id = cart_data.get('user_id')
            
            if user_id:
                # Buscar el usuario en la colección usuarios
                user_doc = st.session_state.db.collection('usuarios').document(user_id).get()
                
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    return user_data
                else:
                    st.error("Usuario no encontrado en la base de datos")
                    return None
            else:
                st.error("No se encontró user_id en los datos del carrito")
                return None
        else:
            st.error("No se encontró el carrito con ese session_id")
            return None
            
    except Exception as e:
        st.error(f"Error al recuperar usuario: {str(e)}")
        return None

# Verificar si existe algun pedido en el carrito de compras
def get_latest_cart(session_id):
    try:
        doc = st.session_state.db.collection('carts').document(session_id).get()
        
        # Verificar si existe el documento
        if doc.exists:
            data = doc.to_dict()
            st.session_state.cart = []
            firestore_items = data.get('items', [])
            for item in firestore_items:
                cart_item = {
                    'name': item['name'],
                    'price': item['price'],
                    'quantity': item['quantity'],
                    'image': item['image']
                }
                st.session_state.cart.append(cart_item)
            return True  # Indica que se cargó exitosamente
        else:
            return False  # No existe el documento
    except Exception as e:
        st.error(f"Error al obtener el carrito: {e}")
        return False

# --- LÓGICA PRINCIPAL DE LA PÁGINA ---
if 'usuario' not in st.session_state:
    st.session_state.usuario = None

# Captura los parámetros de la URL después de la redirección
query_params = st.query_params
code = query_params.get("code")
state = query_params.get("state")

if 'payment' in query_params:
    if query_params['payment'] == 'success':
        st.session_state['stripe_session_id'] = query_params.get('session_id')
        st.session_state['payment_success'] = True
        st.session_state.usuario = get_user_from_firestore(st.session_state['stripe_session_id'])
        st.session_state.login = True
        st.query_params.clear()
        st.switch_page("pages/compraok.py")
    elif query_params['payment'] == 'cancelled':
        st.session_state['stripe_session_id'] = query_params.get('session_id')
        st.session_state['payment_success'] = False
        st.session_state.usuario = get_user_from_firestore(st.session_state['stripe_session_id'])
        st.session_state.login = True
        load_cart = get_latest_cart(st.session_state['stripe_session_id'])
        if load_cart: st.warning("⚠️ El pago fue cancelado, pero puedes continuar comprando.")
        st.query_params.clear()
        st.switch_page("pages/catalogo.py")

if not st.session_state.usuario:
    if not code:
        # Contenido principal
        st.markdown(f"""
        <div class="main-container">
            <div class="login-card">
                <div class="brand-logo">FASHION STORE</div>
                <div class="brand-subtitle">Luxury Fashion</div>
                <div class="decoration-line"></div>
                <div class="welcome-message">
                    Welcome to the world of exclusive fashion.<br>
                    Sign in to discover your style.
                </div>
                """
                + google_login_button() +
                """
                <div class="legal-text">
                    By continuing, you agree to our <a href="#">Terms of Service</a>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        with st.spinner('Verificando autenticación, espere por favor...'):
            st.session_state.usuario = verificar_o_crear_usuario(code)
            st.query_params.clear()
            st.rerun()
else:
    with st.spinner('Todo listo! Redireccionando a la plataforma...'):
        st.session_state.login = True
        st.switch_page('pages/catalogo.py')
