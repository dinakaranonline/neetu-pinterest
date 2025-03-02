import streamlit as st
# Set page config first
st.set_page_config(
    page_title="Doodles.com",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Update the global CSS right after st.set_page_config()
st.markdown("""
    <style>
    /* Import Aptos font */
    @import url('https://fonts.googleapis.com/css2?family=Aptos:wght@400;500;700&display=swap');
    
    /* Global theme */
    :root {
        --primary-color: #FF4B4B;  /* Red color for buttons */
        --background-color: #2E2E2E;  /* Dark grey background */
        --text-color: #FFFFFF;
        --font-family: 'Aptos', sans-serif;
    }
    
    /* Global background and text */
    .stApp {
        background-color: var(--background-color);
        font-family: var(--font-family) !important;
    }
    
    /* All text elements */
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        font-family: var(--font-family) !important;
        color: var(--text-color);
    }
    
    /* Global button styling */
    .stButton > button {
        background-color: var(--primary-color) !important;
        color: white !important;
        border: none !important;
        font-family: var(--font-family) !important;
        font-weight: 500;
        padding: 0.5rem 1rem;
        border-radius: 4px;
    }
    
    .stButton > button:hover {
        background-color: #E63E3E !important;  /* Darker red on hover */
        border: none !important;
    }
    
    /* File uploader styling */
    .stFileUploader {
        width: 100%;
    }
    
    .stFileUploader > div {
        background-color: var(--primary-color) !important;
        color: white !important;
        border: none !important;
        font-family: var(--font-family) !important;
    }
    
    /* Form elements */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > select {
        font-family: var(--font-family) !important;
        background-color: #3E3E3E !important;
        color: white !important;
        border: 1px solid #4E4E4E !important;
    }
    
    /* Warning/Alert styling */
    .stAlert {
        background-color: #3E3E3E !important;
        color: white !important;
        font-family: var(--font-family) !important;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: #252525 !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #252525 !important;
        font-family: var(--font-family) !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: white !important;
        font-family: var(--font-family) !important;
    }
    
    /* Gallery cards */
    .gallery-card {
        background-color: #3E3E3E !important;
    }
    
    /* Radio buttons */
    .stRadio > div {
        background-color: transparent !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

import os
import json
from datetime import datetime
from PIL import Image
import uuid
import requests
from io import BytesIO
from urllib.parse import urlparse
import base64
import re
from pathlib import Path
import os.path
import time
from streamlit_option_menu import option_menu
import sqlite3
import hashlib
import logging
import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Add this helper function at the top of your file
def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
        return encoded_string

# Add these functions at the top of your file, after imports
def load_pins():
    with open('database.json', 'r') as f:
        return json.load(f)

def save_pins(pins):
    with open('database.json', 'w') as f:
        json.dump(pins, f, indent=4)

def init_db():
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Create tables
        c.execute('''CREATE TABLE IF NOT EXISTS users
                    (username TEXT PRIMARY KEY,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS saved_posts
                    (username TEXT, 
                     post_id TEXT,
                     saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     PRIMARY KEY (username, post_id),
                     FOREIGN KEY (username) REFERENCES users(username))''')
        
        conn.commit()
    finally:
        conn.close()

# Initialize database at startup
init_db()

# Move this function up with other helper functions, after init_db()
def delete_post(post_id):
    # Load all pins
    pins = load_pins()
    
    # Find the pin to delete
    pin_to_delete = next((pin for pin in pins if pin['id'] == post_id), None)
    
    if pin_to_delete:
        # Remove the image/video file
        try:
            os.remove(pin_to_delete['image_path'])
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            
        # Remove from database
        pins = [pin for pin in pins if pin['id'] != post_id]
        save_pins(pins)
        
        # Remove any saved references
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("DELETE FROM saved_posts WHERE post_id=?", (post_id,))
        conn.commit()
        conn.close()
        
        return True
    return False

def show_gallery_item(pin, context=None):
    try:
        is_video = pin["image_path"].lower().endswith(('.mp4', '.mov', '.avi'))
        
        # Create container with proper spacing and margin
        st.markdown("""
            <style>
            .gallery-card {
                margin-bottom: 50px !important;
                background: #1E1E1E;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            }
            
            .image-container {
                position: relative;
                width: 100%;
                padding-bottom: 100%;  /* Create a square container */
                background: #1E1E1E;
                overflow: hidden;
                cursor: pointer;
            }
            
            .image-container img {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 100%;
                height: 100%;
                object-fit: cover;
                transition: transform 0.3s ease;
            }
            
            .image-container:hover img {
                transform: translate(-50%, -50%) scale(1.05);
            }
            
            .content-container {
                padding: 15px;
                background: #1E1E1E;
                color: #FFFFFF;
            }
            
            .username-badge {
                display: inline-block;
                padding: 4px 12px;
                background: var(--accent-color);
                color: white;
                border-radius: 15px;
                margin: 10px 0;
                font-size: 0.9em;
            }
            
            .button-container {
                margin-top: 10px;
                margin-bottom: 20px;
                background: #1E1E1E;
            }

            .content-container h3,
            .content-container p {
                color: #FFFFFF;
            }

            .content-container em {
                color: #B0B0B0;
            }

            .video-container {
                position: relative;
                width: 100%;
                padding-bottom: 100%;
                background: #1E1E1E;
                overflow: hidden;
                cursor: pointer;
            }
            
            .video-container video {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 100%;
                height: 100%;
                object-fit: cover;
            }
            </style>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="gallery-card">', unsafe_allow_html=True)
            
            # Create unique keys
            context_prefix = f"{context}_" if context else ""
            save_key = f"save_btn_{context_prefix}{pin['id']}"
            unsave_key = f"unsave_btn_{context_prefix}{pin['id']}"
            
            # Display video or image
            if is_video:
                st.video(pin["image_path"])
            else:
                image = Image.open(pin["image_path"])
                st.markdown(f"""
                    <div class="image-container" onclick="window.location.href='?view_image={pin['id']}'">
                        <img src="data:image/jpeg;base64,{image_to_base64(pin['image_path'])}" />
                    </div>
                """, unsafe_allow_html=True)
            
            # Content container
            st.markdown(f"""
                <div class="content-container">
                    <h3>{pin['title']}</h3>
                    <p>{pin['description']}</p>
                    <p><em>Category: {pin['category']}</em></p>
                    <a href="?view_profile={pin.get('username', 'admin')}" 
                       style="text-decoration: none;">
                        <div class="username-badge">@{pin.get('username', 'admin')}</div>
                    </a>
                </div>
            """, unsafe_allow_html=True)
            
            # Add buttons container
            st.markdown('<div class="button-container">', unsafe_allow_html=True)
            
            # Create columns for buttons
            col1, col2 = st.columns([1, 1])
            
            # Save/Unsave button
            with col1:
                if st.session_state.get('authenticated'):
                    is_saved = is_post_saved(st.session_state.current_user, pin['id'])
                    if is_saved:
                        if st.button("Unsave", key=f"unsave_{context}_{pin['id']}"):
                            unsave_post(st.session_state.current_user, pin['id'])
                            st.rerun()
                    else:
                        if st.button("Save", key=f"save_{context}_{pin['id']}"):
                            save_post(st.session_state.current_user, pin['id'])
                            st.rerun()
            
            # Delete button (only show for post owner)
            with col2:
                if st.session_state.get('authenticated') and pin.get('username') == st.session_state.current_user:
                    delete_key = f"delete_{context}_{pin['id']}"
                    confirm_key = f"confirm_{context}_{pin['id']}"
                    
                    # Create a unique session state key for this post's delete confirmation
                    confirm_state_key = f"confirm_delete_{pin['id']}"
                    
                    # Initialize the confirmation state if not exists
                    if confirm_state_key not in st.session_state:
                        st.session_state[confirm_state_key] = False
                    
                    # Show delete button or confirmation dialog
                    if not st.session_state[confirm_state_key]:
                        if st.button("Delete", key=delete_key):
                            st.session_state[confirm_state_key] = True
                            st.rerun()
                    else:
                        st.warning("Are you sure you want to delete this post?????")
                        # Use horizontal layout for confirmation buttons
                        st.markdown("""
                            <style>
                            .stButton {
                                display: inline-block;
                                margin-right: 10px;
                            }
                            </style>
                        """, unsafe_allow_html=True)
                        
                        # Place buttons side by side
                        if st.button("Yes, continue", key=f"yes_{confirm_key}"):
                            if delete_post(pin['id']):
                                st.success("Post deleted successfully!")
                                time.sleep(1)
                                st.rerun()
                        if st.button("No, cancel", key=f"no_{confirm_key}"):
                            st.session_state[confirm_state_key] = False
                            st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"Error loading pin: {e}")

    
    # Create main container
   
        
       
     

# Initialize session states
if 'show_splash' not in st.session_state:
    st.session_state.show_splash = True
    st.session_state.splash_time = datetime.now()

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.current_user = None

# Add this CSS right after st.set_page_config()
st.markdown("""
    <style>
    .main-logo-container {
        position: fixed;
        top: 0;
        left: 0;
        z-index: 9999;
        width: 180px;  /* Increased size */
        height: 180px;
        padding: 10px;
        background: grey;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        animation: slideIn 0.5s ease-out;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .main-logo-container img {
        max-width: 160px;  /* Slightly smaller than container */
        max-height: 160px;
        width: auto;
        height: auto;
        object-fit: contain;
        image-rendering: -webkit-optimize-contrast;
        image-rendering: crisp-edges;
        -webkit-backface-visibility: hidden;
        backface-visibility: hidden;
        transform: translateZ(0);
    }

    /* Hide default image caption */
    .stImage > div:nth-child(2) {
        display: none;
    }

    /* Adjust main content spacing */
    .block-container {
        padding-top: 200px !important;  /* Adjusted for new size */
        padding-left: 2rem;
        padding-right: 2rem;
    }

    /* Ensure sidebar appears above other content but below logo */
    .css-1d391kg {
        z-index: 999;
    }
    </style>
""", unsafe_allow_html=True)


# Use environment variables for sensitive paths
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
DATABASE_FILE = os.getenv('DATABASE_FILE', 'database.json')

# Create uploads directory if it doesn't exist
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

if not os.path.exists(DATABASE_FILE):
    with open(DATABASE_FILE, "w") as f:
        json.dump([], f)

# Load existing pins
def load_pins():
    with open(DATABASE_FILE, "r") as f:
        return json.load(f)

# Save pins
def save_pins(pins):
    with open(DATABASE_FILE, "w") as f:
        json.dump(pins, f, indent=4)

# Add these helper functions
def save_post(username, post_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO saved_posts (username, post_id) VALUES (?, ?)", 
                 (username, post_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def unsave_post(username, post_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("DELETE FROM saved_posts WHERE username=? AND post_id=?", 
             (username, post_id))
    conn.commit()
    conn.close()

def is_post_saved(username, post_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM saved_posts WHERE username=? AND post_id=?", 
             (username, post_id))
    result = c.fetchone() is not None
    conn.close()
    return result

def get_saved_posts(username):
    # First get the saved post IDs
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT post_id FROM saved_posts WHERE username=?", (username,))
    saved_post_ids = [row[0] for row in c.fetchall()]
    conn.close()
    
    # Then get the full post data from the JSON file
    with open('database.json', 'r') as f:
        all_pins = json.load(f)
    
    # Filter pins to only include saved ones
    saved_pins = [pin for pin in all_pins if pin['id'] in saved_post_ids]
    return saved_pins

def show_user_profile(username):
    # Create a container for the profile page
    profile_container = st.container()
    
    with profile_container:
        # Profile header with user info
        st.markdown(f"""
            <div class="profile-container">
                <div class="profile-header">
                    <div class="profile-avatar">
                        <div class="avatar-circle">
                            {username[0].upper()}
                        </div>
                    </div>
                    <div class="profile-info">
                        <h1>@{username}</h1>
                    </div>
                </div>
            </div>
            
            <style>
            /* Profile stats styling */
            .profile-stats {{
                display: flex;
                justify-content: center;
                padding: 20px;
                background: var(--card-background);
                border-radius: 10px;
                margin: 20px 0;
            }}
            
            .stat-item {{
                text-align: center;
            }}
            
            .stat-number {{
                font-size: 24px;
                font-weight: bold;
                color: var(--accent-color);
            }}
            
            .stat-label {{
                color: var(--text-color);
                font-size: 14px;
                margin-top: 5px;
            }}
            
            /* Rest of your existing profile styles */
            .profile-container {{
                padding: 20px;
                margin-bottom: 40px;
            }}
            
            .profile-header {{
                display: flex;
                align-items: center;
                gap: 20px;
                padding: 20px;
                background: var(--card-background);
                border-radius: 15px;
            }}
            
            .avatar-circle {{
                width: 80px;
                height: 80px;
                background: var(--accent-color);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 36px;
                color: white;
                font-weight: bold;
            }}
            
            .profile-info h1 {{
                margin: 0;
                color: var(--text-color);
                font-size: 24px;
            }}
            
            .gallery-section {{
                margin-top: 40px;
            }}
            
            .gallery-header {{
                font-size: 20px;
                color: var(--text-color);
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid var(--accent-color);
            }}
            </style>
        """, unsafe_allow_html=True)
        
        # Get user's pins
        all_pins = load_pins()
        user_pins = [pin for pin in all_pins if pin.get('username', 'admin') == username]
        
        # Display post count
        st.markdown(f"""
            <div class="profile-stats">
                <div class="stat-item">
                    <div class="stat-number">{len(user_pins)}</div>
                    <div class="stat-label">Posts</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Update the back button logic
        if st.button("← Back to Gallery"):
            # Clear query params
            st.query_params.clear()
            # If user was authenticated before, stay authenticated
            if st.session_state.authenticated:
                st.rerun()
            else:
                # If viewing profile without auth, return to gallery view
                st.switch_page("app.py")  # This will refresh the page with cleared query params
        
        # Display user's uploads
        st.markdown('<div class="gallery-section">', unsafe_allow_html=True)
        st.markdown('<div class="gallery-header">Uploaded Pictures</div>', unsafe_allow_html=True)
        
        if not user_pins:
            st.info(f"@{username} hasn't posted anything yet!")
        else:
            # Create grid layout for pictures
            cols = st.columns(3)
            for idx, pin in enumerate(user_pins):
                with cols[idx % 3]:
                    try:
                        image = Image.open(pin["image_path"])
                        with st.container():
                            st.image(image, use_container_width=True)
                            st.write(f"**{pin['title']}**")
                            st.write(pin["description"])
                            st.write(f"*Category: {pin['category']}*")
                            
                            # Show save button only if user is logged in
                            if st.session_state.get('authenticated'):
                                is_saved = is_post_saved(st.session_state.current_user, pin['id'])
                                if is_saved:
                                    if st.button("Unsave", key=f"unsave_btn_profile_{pin['id']}"):
                                        unsave_post(st.session_state.current_user, pin['id'])
                                        st.rerun()
                                else:
                                    if st.button("Save", key=f"save_btn_profile_{pin['id']}"):
                                        save_post(st.session_state.current_user, pin['id'])
                                        st.rerun()
                    except Exception as e:
                        st.error(f"Error loading image: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)

# Show splash screen first
if st.session_state.show_splash:
    st.markdown("""
        <style>
        .splash-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-color: white;
            z-index: 9999;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .splash-content {
            text-align: center;
            padding: 40px;
        }
        
        .loading-text {
            font-family: 'Comic Sans MS', cursive, sans-serif;
            font-size: 36px;
            color: #FF6B6B;
            margin-bottom: 20px;
        }
        </style>
        
        <div class="splash-container">
            <div class="splash-content">
                <div class="loading-text">Loading Doodles</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    time.sleep(3)
    st.session_state.show_splash = False
    st.rerun()

# First check for profile viewing
if "view_profile" in st.query_params:
    username_to_view = st.query_params["view_profile"]
    show_user_profile(username_to_view)
    st.stop()

# Then handle authentication for other pages
if not st.session_state.authenticated:
    st.title("Welcome to Doodles!")
    username = st.text_input("Enter your username to continue", key="username_input", placeholder="Enter username")
    if st.button("Continue", key="continue_button"):
        if username.strip():
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("SELECT username FROM users WHERE username=?", (username,))
            user = c.fetchone()
            if not user:
                c.execute("INSERT INTO users (username) VALUES (?)", (username,))
                conn.commit()
            conn.close()
            st.session_state.authenticated = True
            st.session_state.current_user = username
            st.rerun()
        else:
            st.error("Please enter a username")
else:
    # Show main app content
    # ... rest of your main app code
    STATIC_DIR = "static"
    Path(STATIC_DIR).mkdir(parents=True, exist_ok=True)

    # Updated CSS for the logo with transition
    st.markdown("""
        <style>
        .main-logo-container {
            position: fixed;
            top: 0;
            left: 0;
            z-index: 9999;
            width: 180px;  /* Increased size */
            height: 180px;
            padding: 10px;
            background: white;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
            animation: slideIn 0.5s ease-out;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .main-logo-container img {
            max-width: 160px;  /* Slightly smaller than container */
            max-height: 160px;
            width: auto;
            height: auto;
            object-fit: contain;
            image-rendering: -webkit-optimize-contrast;
            image-rendering: crisp-edges;
            -webkit-backface-visibility: hidden;
            backface-visibility: hidden;
            transform: translateZ(0);
        }

        /* Hide default image caption */
        .stImage > div:nth-child(2) {
            display: none;
        }

        /* Adjust main content spacing */
        .block-container {
            padding-top: 200px !important;  /* Adjusted for new size */
            padding-left: 2rem;
            padding-right: 2rem;
        }

        /* Ensure sidebar appears above other content but below logo */
        .css-1d391kg {
            z-index: 999;
        }
        </style>
    """, unsafe_allow_html=True)


    # Main title
    st.title("Doodles.com")

    # Use environment variables for sensitive paths
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    DATABASE_FILE = os.getenv('DATABASE_FILE', 'database.json')

    # Create uploads directory if it doesn't exist
    Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

    if not os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, "w") as f:
            json.dump([], f)

    # Load existing pins
    def load_pins():
        with open(DATABASE_FILE, "r") as f:
            return json.load(f)

    # Save pins
    def save_pins(pins):
        with open(DATABASE_FILE, "w") as f:
            json.dump(pins, f, indent=4)

    # Sidebar for uploading
    with st.sidebar:
        # Add logo at the top of sidebar with custom CSS
        st.markdown("""
            <style>
            .sidebar-logo {
                padding: 0 !important;
                margin: 0 !important;
            }
            .sidebar-logo img {
                width: 100%;
                height: auto;
                object-fit: contain;
                display: block;
            }
            /* Remove ALL default streamlit spacing */
            .css-18e3th9 {
                padding: 0 !important;
                margin: 0 !important;
            }
            .css-1d391kg {
                padding: 0 !important;
                margin: 0 !important;
            }
            .st-emotion-cache-1v0mbdj {
                padding-top: 0 !important;
                margin-top: 0 !important;
            }
            div[data-testid="stVerticalBlock"] {
                padding: 0 !important;
                margin: 0 !important;
            }
            div[data-testid="stVerticalBlock"] > div {
                padding: 0 !important;
                margin: 0 !important;
            }
            .element-container, .stMarkdown {
                padding: 0 !important;
                margin: 0 !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Add logo without any wrapper divs
        try:
            logo_image = Image.open("static/doodles.png")
            st.image(logo_image, use_container_width=True)
        except Exception as e:
            st.error(f"Could not load logo: {e}")

        st.header("Upload New Pin")
        
        # Add upload method selection
        upload_method = st.radio("Choose upload method:", ["Upload File", "Image URL"])
        
        if upload_method == "Upload File":
            uploaded_file = st.file_uploader("Choose a file", 
                                           type=["jpg", "jpeg", "png", "mp4", "mov", "avi"],
                                           help="Upload an image or video file")
            if uploaded_file:
                file_type = uploaded_file.type
                is_video = file_type.startswith('video/')
                
                # Preview the uploaded content
                if is_video:
                    st.video(uploaded_file)
                    file_data = uploaded_file.getvalue()
                else:
                    st.image(uploaded_file)
                    file_data = uploaded_file.getbuffer()
        else:
            image_url = st.text_input("Enter image URL")
            if image_url:
                try:
                    # Check if it's a base64 encoded image
                    if image_url.startswith('data:image'):
                        base64_data = re.sub('^data:image/.+;base64,', '', image_url)
                        try:
                            image_data = base64.b64decode(base64_data)
                            st.image(image_data, caption="Image Preview", use_container_width=True)
                        except Exception as e:
                            st.error("Invalid base64 image data")
                            image_data = None
                    else:
                        response = requests.get(image_url)
                        if response.status_code == 200:
                            image_data = response.content
                            st.image(image_data, caption="Image Preview", use_container_width=True)
                        else:
                            st.error("Could not fetch image from URL")
                            image_data = None
                except Exception as e:
                    st.error(f"Error fetching image: {str(e)}")
                    image_data = None
            else:
                image_data = None
        
        # Add form fields
        with st.form(key="upload_form"):
            title = st.text_input("Title")
            description = st.text_area("Description")
            category = st.selectbox("Category", ["Art", "Recipes", "DIY", "Other"])
            
            # Add the upload button inside the form
            submit_button = st.form_submit_button(label="Upload")
            
            if submit_button and file_data:
                try:
                    # Get file extension
                    if upload_method == "Upload File":
                        file_extension = uploaded_file.name.split(".")[-1].lower()
                        is_video = file_extension in ['mp4', 'mov', 'avi']
                    else:
                        parsed_url = urlparse(image_url)
                        file_extension = os.path.splitext(parsed_url.path)[1].strip('.').lower() or 'jpg'
                        is_video = file_extension in ['mp4', 'mov', 'avi']
                    
                    unique_filename = f"{uuid.uuid4()}.{file_extension}"
                    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                    
                    # Save file
                    with open(file_path, "wb") as f:
                        f.write(file_data)
                    
                    # Save pin information
                    pins = load_pins()
                    new_pin = {
                        "id": str(uuid.uuid4()),
                        "title": title,
                        "description": description,
                        "category": category,
                        "image_path": file_path,
                        "is_video": is_video,
                        "timestamp": datetime.now().isoformat(),
                        "source": "url" if upload_method == "Image URL" else "local",
                        "original_url": image_url if upload_method == "Image URL" else None,
                        "username": st.session_state.current_user or "admin"
                    }
                    pins.append(new_pin)
                    save_pins(pins)
                    st.success("Content uploaded successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving pin: {str(e)}")
            elif submit_button and not file_data:
                st.error("Please select an image first")

    # Main content area
    st.header("Doodles Gallery")

    # Create tabs for categories
    categories = ["All", "Art", "Recipes", "DIY", "Other"]
    tabs = st.tabs(categories)

    # Load all pins once
    all_pins = load_pins()

    # Display pins in each category tab
    for idx, tab in enumerate(tabs):
        with tab:
            category = categories[idx]
            if category == "All":
                filtered_pins = all_pins
            else:
                filtered_pins = [pin for pin in all_pins if pin["category"] == category]
            
            if not filtered_pins:
                st.info(f"No doodles in {category} category yet!")
            else:
                cols = st.columns(3)
                for pin_idx, pin in enumerate(filtered_pins):
                    with cols[pin_idx % 3]:
                        try:
                            show_gallery_item(pin, context=f"gallery_{category}")
                        except Exception as e:
                            st.error(f"Error loading pin: {e}")

    # Main app code here
    st.sidebar.title(f"Welcome {st.session_state.current_user}!")
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.current_user = None
        st.rerun()
    
    # Add navigation
    with st.sidebar:
        selected = option_menu(
            menu_title=None,
            options=["Home", "My Uploads", "All Doodles", "Saved Posts", "About"],
            icons=None,  # Remove icons
            default_index=0,
        )

    # Add handling for the Saved Posts section
    if selected == "Saved Posts":
        st.header("My Saved Posts")
        saved_pins = get_saved_posts(st.session_state.current_user)
        
        if not saved_pins:
            st.info("You haven't saved any posts yet!")
        else:
            cols = st.columns(3)
            for idx, pin in enumerate(saved_pins):
                with cols[idx % 3]:
                    try:
                        show_gallery_item(pin, context="saved")
                    except Exception as e:
                        st.error(f"Error loading saved pin: {e}")

    def view_database_contents():
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        st.subheader("Users Table")
        c.execute("SELECT * FROM users")
        users = c.fetchall()
        if users:
            st.table(pd.DataFrame(users, columns=['username', 'created_at']))
        else:
            st.info("No users found")
        
        st.subheader("Saved Posts Table")
        c.execute("SELECT * FROM saved_posts")
        saved = c.fetchall()
        if saved:
            st.table(pd.DataFrame(saved, columns=['username', 'post_id', 'saved_at']))
        else:
            st.info("No saved posts found")
        
        conn.close()

    # Add this in your sidebar or where you want to view the data
    #if st.session_state.get('authenticated'):
     #   if st.button("View Database Contents"):
     #       view_database_contents()
    