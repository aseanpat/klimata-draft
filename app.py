import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from shapely import wkt
from shapely.errors import WKTReadingError
import plotly.express as px
import sqlite3
import hashlib

# UI libraries
from streamlit_option_menu import option_menu
from streamlit_extras.metric_cards import style_metric_cards

# ==========================
# PAGE CONFIGURATION
# ==========================
st.set_page_config(
    page_title="KLIMATA Risk Dashboard",
    page_icon="🌿",
    layout="wide"
)

# ==========================
# DATABASE FUNCTIONS
# ==========================
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT
    )
    ''')
    conn.commit()
    conn.close()

def create_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                  (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def check_user_password(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    data = c.fetchone()
    conn.close()
    if data:
        return data[0] == hash_password(password)
    return False

def update_user_password(username, new_password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET password_hash = ? WHERE username = ?",
              (hash_password(new_password), username))
    conn.commit()
    conn.close()
    return True

def delete_user(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return True

# ==========================
# DATA LOADING FUNCTIONS
# ==========================
@st.cache_data
def load_data(csv_path, encoding='utf-8'):
    def parse_wkt(wkt_string):
        if not isinstance(wkt_string, str):
            return None
        try:
            return wkt.loads(wkt_string)
        except (WKTReadingError, TypeError):
            return None

    df = pd.read_csv(csv_path, encoding=encoding)
    df['geometry'] = df['brgy_names-ILOILO.geometry'].apply(parse_wkt)
    df.dropna(subset=['geometry', 'urban_risk_index'], inplace=True)
    gdf = gpd.GeoDataFrame(df, geometry='geometry')
    gdf.set_crs(epsg=4326, inplace=True)
    return gdf

@st.cache_data
def load_amenity_data(path):
    return pd.read_csv(path, encoding='latin1')

# ==========================
# DASHBOARD BUILDER
# ==========================
def build_dashboard(gdf, df2):
    # --- Standardize Barangay Names for gdf ---
    if 'brgy_names-ILOILO.location.adm4_en' in gdf.columns:
        gdf['barangay_name'] = gdf['brgy_names-ILOILO.location.adm4_en']
    elif 'location1.adm4_en' in gdf.columns:
        gdf['barangay_name'] = gdf['location1.adm4_en']
    else:
        gdf['barangay_name'] = None

    # --- Standardize Barangay Names for df2 ---
    if 'location1.adm4_en' in df2.columns:
        df2['barangay_name'] = df2['location1.adm4_en']
    else:
        df2['barangay_name'] = None

    dark_mode = st.sidebar.toggle("🌗 Dark Mode", value=True)
    
    # Apply nature-themed styling
    if dark_mode:
        st.markdown("""
        <style>
        .stApp {background: linear-gradient(135deg, #1a2f1a 0%, #0d1f0d 100%); color: #E8F5E9;}
        [data-testid="stHeader"] {background-color: #1b5e20;}
        div[data-testid="stMetricValue"] {color: #66BB6A !important; text-shadow: 0px 0px 8px rgba(102,187,106,0.6);}
        section[data-testid="stSidebar"] {background: linear-gradient(180deg, #1b5e20 0%, #2e7d32 100%); color: #E8F5E9;}
        </style>
        """, unsafe_allow_html=True)
        metric_style = dict(background_color="#1E3A1E", border_left_color="#66BB6A", border_color="#2E7D32")
    else:
        st.markdown("""
        <style>
        .stApp {background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%); color: #1B5E20;}
        [data-testid="stHeader"] {background-color: #A5D6A7;}
        div[data-testid="stMetricValue"] {color: #2E7D32 !important;}
        section[data-testid="stSidebar"] {background: linear-gradient(180deg, #C8E6C9 0%, #A5D6A7 100%); color: #1B5E20;}
        </style>
        """, unsafe_allow_html=True)
        metric_style = dict(background_color="#F1F8E9", border_left_color="#66BB6A", border_color="#81C784")

    # Sidebar Navigation
    with st.sidebar:
        st.markdown(f"### Welcome, {st.session_state.get('username','Guest')}")
        selected = option_menu(
            menu_title=None,
            options=["City Overview", "Barangay Deep Dive", "Manage Account", "Log Out"],
            icons=["tree-fill", "geo-alt-fill", "person-circle", "box-arrow-right"],
            menu_icon="globe-americas",
            default_index=0,
            styles={
                "container": {"padding": "5px", "background-color": "transparent"},
                "icon": {"color": "#66BB6A", "font-size": "18px"},
                "nav-link": {"color": "#E8F5E9" if dark_mode else "#1B5E20", "font-size": "15px", "text-align": "left"},
                "nav-link-selected": {"background-color": "#4CAF50", "color": "white"},
            },
        )

    if selected == "Manage Account":
        st.session_state.page = "Manage Account"
        st.rerun()
    if selected == "Log Out":
        st.session_state.logged_in = False
        st.session_state.pop('username', None)
        st.session_state.page = "Login"
        st.rerun()

    # =====================
    # City Overview
    # =====================
    if selected == "City Overview":
        # Carousel background for City Overview
        bg_images = [
            "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/carousel_images/carousel%20slide%201.jpg",
            "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/carousel_images/carousel%20slide%202.jpg",
            "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/carousel_images/carousel%20slide%203.jpg"
        ]
        
        city_overview_bg = f"""
        <style>
        @keyframes cityBgSlide {{
            0%, 33% {{ 
                background-image: linear-gradient(rgba(27, 94, 32, 0.75), rgba(13, 31, 13, 0.85)), url('{bg_images[0]}');
            }}
            33.33%, 66% {{ 
                background-image: linear-gradient(rgba(27, 94, 32, 0.75), rgba(13, 31, 13, 0.85)), url('{bg_images[1]}');
            }}
            66.66%, 100% {{ 
                background-image: linear-gradient(rgba(27, 94, 32, 0.75), rgba(13, 31, 13, 0.85)), url('{bg_images[2]}');
            }}
        }}
        
        [data-testid="stAppViewContainer"] {{
            animation: cityBgSlide 18s ease-in-out infinite;
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            background-repeat: no-repeat;
        }}
        </style>
        """
        st.markdown(city_overview_bg, unsafe_allow_html=True)
        
        st.title("Iloilo City: Climate Vulnerability Index")

        # Sidebar map selector
        selected_layer = st.sidebar.radio(
            "Select Map Layer",
            ["Urban Risk", "Population", "Amenity", "Climate Exposure"]
        )

        layer_config = {
            "Urban Risk": {"col": "urban_risk_index", "color": "YlOrRd", "legend": "Urban Risk Index"},
            "Population": {"col": "pop_total", "color": "Blues", "legend": "Population Total"},
            "Amenity": {"col": "infra_index", "color": "Reds", "legend": "Amenity Index"},
            "Climate Exposure": {"col": "climate_exposure_score", "color": "Greens", "legend": "Climate Exposure Score"},
        }

        col_config = layer_config[selected_layer]
        metric_col = col_config["col"]
        color_scale = col_config["color"]
        legend_name = col_config["legend"]

        avg_risk = gdf['urban_risk_index'].mean()
        avg_infra = gdf['infra_index'].mean()
        avg_wealth = gdf['rwi_mean'].mean()

        col1, col2, col3 = st.columns(3)
        col1.metric("Average Urban Risk", f"{avg_risk:.2f}")
        col2.metric("Average Infrastructure", f"{avg_infra:.2f}")
        col3.metric("Average Relative Wealth", f"{avg_wealth:.2f}")
        style_metric_cards(**metric_style, box_shadow=True)

        iloilo_center = [10.7202, 122.5621]
        m = folium.Map(location=iloilo_center, zoom_start=13)

        folium.Choropleth(
            geo_data=gdf,
            data=gdf,
            columns=['adm4_pcode', metric_col],
            key_on='feature.properties.adm4_pcode',
            fill_color=color_scale,
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name=legend_name
        ).add_to(m)

        if selected_layer == "Urban Risk":
            tooltip_fields = [
                'barangay_name',
                'urban_risk_index',
                'risk_level',
                'infra_risk',
                'climate_exposure_score',
                'coast_risk',
                'ndvi_risk',
                'pop_risk',
                'rwi_risk'
            ]
            tooltip_aliases = [
                'Barangay:',
                'Urban Risk Index:',
                'Risk Level:',
                'Climate Vulnerability Index:',
                'Climate Exposure Score:',
                'Coastal Distance Risk Score:',
                'NDVI Risk Score:',
                'Population Risk Score:',
                'Relative Wealth Index (RWI) Risk Score:'
            ]
        else:
            tooltip_fields = ['barangay_name', metric_col]
            tooltip_aliases = ['Barangay:', legend_name + ":"]

        folium.GeoJson(
            gdf,
            tooltip=folium.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases, localize=True)
        ).add_to(m)

        st_folium(m, width='100%', height=600)

        tab1, tab2 = st.tabs(["Top 5 Barangays", "Value Distribution"])
        with tab1:
            top_5 = gdf.nlargest(5, metric_col)
            top_5_df = top_5[['barangay_name', metric_col]].copy()
            top_5_df.rename(columns={'barangay_name': 'Barangay', metric_col: legend_name}, inplace=True)
            fig = px.bar(top_5_df, x='Barangay', y=legend_name, title=f"Top 5 Barangays by {legend_name}",
                         color=legend_name, color_continuous_scale=color_scale, text=legend_name)
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            color_map = {"YlOrRd": "#F4A261", "Blues": "#1E90FF", "Reds": "#E63946", "Greens": "#2A9D8F"}
            hist_color = color_map.get(color_scale, "#00ADB5")
            fig = px.histogram(gdf, x=metric_col, nbins=20, title=f"Distribution of {legend_name}")
            fig.update_traces(marker_color=hist_color, opacity=0.8)
            st.plotly_chart(fig, use_container_width=True)

    # =====================
    # Barangay Deep Dive
    # =====================
    elif selected == "Barangay Deep Dive":
        # Carousel background for Barangay Deep Dive
        bg_images = [
            "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/carousel_images/carousel%20slide%201.jpg",
            "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/carousel_images/carousel%20slide%202.jpg",
            "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/carousel_images/carousel%20slide%203.jpg"
        ]
        
        deep_dive_bg = f"""
        <style>
        @keyframes deepDiveBgSlide {{
            0%, 33% {{ 
                background-image: linear-gradient(rgba(27, 94, 32, 0.75), rgba(13, 31, 13, 0.85)), url('{bg_images[0]}');
            }}
            33.33%, 66% {{ 
                background-image: linear-gradient(rgba(27, 94, 32, 0.75), rgba(13, 31, 13, 0.85)), url('{bg_images[1]}');
            }}
            66.66%, 100% {{ 
                background-image: linear-gradient(rgba(27, 94, 32, 0.75), rgba(13, 31, 13, 0.85)), url('{bg_images[2]}');
            }}
        }}
        
        [data-testid="stAppViewContainer"] {{
            animation: deepDiveBgSlide 18s ease-in-out infinite;
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            background-repeat: no-repeat;
        }}
        </style>
        """
        st.markdown(deep_dive_bg, unsafe_allow_html=True)
        
        st.title("Barangay Deep Dive")
        brgy_list = sorted(gdf['barangay_name'].dropna().unique())

        search_query = st.sidebar.text_input("Search Barangay")
        filtered_brgy_list = [b for b in brgy_list if search_query.lower() in b.lower()] if search_query else brgy_list

        if len(filtered_brgy_list) == 0:
            st.sidebar.warning("No barangay found. Try a different search.")
            st.stop()

        selected_brgy = st.sidebar.selectbox("Select a Barangay", filtered_brgy_list)
        brgy_data_rows = gdf[gdf['barangay_name'] == selected_brgy]

        if brgy_data_rows.empty:
            st.error("Data not available for this barangay.")
            st.stop()

        brgy_data = brgy_data_rows.iloc[0]
        st.header(f"Dashboard for: {selected_brgy}")

        col1, col2, col3 = st.columns(3)
        col1.metric("Urban Risk Score", f"{brgy_data['urban_risk_index']:.2f}")
        col2.metric("Risk Level", brgy_data['risk_label'])
        col3.metric("Relative Wealth Index", f"{brgy_data['rwi_mean']:.2f}")
        style_metric_cards(**metric_style, box_shadow=True)

        # --- Map visualization ---
        brgy_gdf = gpd.GeoDataFrame([brgy_data], geometry='geometry', crs=gdf.crs)
        centroid = brgy_gdf.geometry.centroid.iloc[0]
        m = folium.Map(location=[centroid.y, centroid.x], zoom_start=15)
        folium.GeoJson(
            brgy_gdf,
            style_function=lambda x: {'fillColor': '#4CAF50', 'color': '#2E7D32', 'fillOpacity': 0.6},
            tooltip=folium.GeoJsonTooltip(
                fields=['barangay_name', 'urban_risk_index', 'risk_label'],
                aliases=['Barangay:', 'Urban Risk Index:', 'Risk Level:'],
                localize=True
            )
        ).add_to(m)
        st_folium(m, width='100%', height=500)

        # --- Amenity Visualization ---
        st.subheader("Nearest Amenities Overview")
        brgy_amenities = df2[df2['barangay_name'] == selected_brgy]

        if not brgy_amenities.empty:
            amenity_cols = ['college_nearest', 'community_centre_nearest', 'school_nearest',
                            'shelter_nearest', 'town_hall_nearest', 'university_nearest']
            amenity_data = brgy_amenities[amenity_cols].melt(var_name='Amenity Type', value_name='Distance (meters)')
            amenity_data['Amenity Type'] = amenity_data['Amenity Type'].str.replace('_nearest', '').str.replace('_', ' ').str.title()

            fig = px.bar(
                amenity_data,
                x='Amenity Type',
                y='Distance (meters)',
                title=f"Nearest Facilities from {selected_brgy}",
                color='Distance (meters)',
                color_continuous_scale='tealgrn'
            )
            fig.update_traces(texttemplate='%{y:.1f}', textposition='outside')
            fig.update_layout(xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(amenity_data)
        else:
            st.info("No amenity data available for this barangay.")

# ==========================
# PAGE FUNCTIONS
# ==========================
def show_login_page():
    """Login page with carousel background"""
    
    # Carousel background images from GitHub
    bg_images = [
        "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/carousel_images/carousel%20slide%201.jpg",
        "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/carousel_images/carousel%20slide%202.jpg",
        "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/carousel_images/carousel%20slide%203.jpg"
    ]
    
    bg_urls = "', '".join(bg_images)
    
    # Apply the carousel background styling with smooth sliding
    page_bg_img = f"""
    <style>
    @keyframes bgSlide {{
        0%, 33% {{ 
            background-image: linear-gradient(rgba(27, 94, 32, 0.5), rgba(46, 125, 50, 0.6)), url('{bg_images[0]}');
            background-position: 0% 50%;
        }}
        33.33%, 66% {{ 
            background-image: linear-gradient(rgba(27, 94, 32, 0.5), rgba(46, 125, 50, 0.6)), url('{bg_images[1]}');
            background-position: 100% 50%;
        }}
        66.66%, 100% {{ 
            background-image: linear-gradient(rgba(27, 94, 32, 0.5), rgba(46, 125, 50, 0.6)), url('{bg_images[2]}');
            background-position: 0% 50%;
        }}
    }}
    
    [data-testid="stAppViewContainer"] {{
        animation: bgSlide 18s ease-in-out infinite;
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }}
    
    /* Hide header completely */
    [data-testid="stHeader"] {{
        display: none;
    }}
    
    /* Hide sidebar on login page */
    [data-testid="stSidebar"] {{
        display: none;
    }}
    
    /* Center the login form */
    .block-container {{
        max-width: 500px !important;
        padding-top: 5rem !important;
    }}
    
    /* Glass effect card with green tint */
    div[data-testid="stVerticalBlock"] > div:first-child {{
        background: rgba(232, 245, 233, 0.15);
        padding: 3rem 2rem;
        border-radius: 20px;
        backdrop-filter: blur(12px);
        border: 2px solid rgba(102, 187, 106, 0.3);
        box-shadow: 0 8px 32px 0 rgba(27, 94, 32, 0.4);
    }}
    
    /* Nature-themed title */
    h1 {{
        color: #F1F8E9 !important;
        text-align: center;
        text-shadow: 2px 2px 8px rgba(27, 94, 32, 0.9);
        font-weight: bold;
    }}
    
    /* Style labels */
    label {{
        color: #F1F8E9 !important;
        font-weight: 600;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.5);
    }}
    
    /* Style inputs */
    .stTextInput > div > div > input {{
        background-color: rgba(232, 245, 233, 0.95);
        border-radius: 8px;
        border: 2px solid #66BB6A;
        color: #1B5E20 !important;
    }}
    
    /* Style error messages */
    .stAlert {{
        background-color: rgba(255, 255, 255, 0.95) !important;
    }}
    
    /* Style buttons with green theme */
    .stButton > button {{
        width: 100%;
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        font-weight: 600;
        border: none;
        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
    }}
    
    .stButton > button:hover {{
        background-color: #388E3C;
        box-shadow: 0 6px 16px rgba(56, 142, 60, 0.5);
    }}
    
    /* Style the divider */
    hr {{
        border-color: rgba(102, 187, 106, 0.4);
    }}
    </style>
    """
    
    st.markdown(page_bg_img, unsafe_allow_html=True)

    # Login form content
    st.title("KLIMATA: Climate Risk Assessment Portal")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In")

        if submitted:
            if check_user_password(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.page = "Dashboard"
                st.rerun()
            else:
                st.error("User not known or password incorrect")

    st.markdown("---")
    if st.button("Need an account? Sign Up"):
        st.session_state.page = "Sign Up"
        st.rerun()


def show_signup_page():
    st.title("Create a New Account")
    with st.form("signup_form"):
        username = st.text_input("New Username")
        password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Create Account")
        if submitted:
            if not username or not password or not confirm_password:
                st.error("Please fill in all fields.")
            elif password != confirm_password:
                st.error("Passwords do not match.")
            else:
                if create_user(username, password):
                    st.success("Account created successfully! Please log in.")
                    st.session_state.page = "Login"
                    st.rerun()
                else:
                    st.error("Username already exists.")
    if st.button("Back to Login"):
        st.session_state.page = "Login"
        st.rerun()

def show_manage_account_page():
    # Carousel background for Manage Account page
    bg_images = [
        "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/carousel_images/carousel%20slide%201.jpg",
        "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/carousel_images/carousel%20slide%202.jpg",
        "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/carousel_images/carousel%20slide%203.jpg"
    ]
    
    manage_bg = f"""
    <style>
    @keyframes manageBgSlide {{
        0%, 33% {{ 
            background-image: linear-gradient(rgba(27, 94, 32, 0.75), rgba(13, 31, 13, 0.85)), url('{bg_images[0]}');
        }}
        33.33%, 66% {{ 
            background-image: linear-gradient(rgba(27, 94, 32, 0.75), rgba(13, 31, 13, 0.85)), url('{bg_images[1]}');
        }}
        66.66%, 100% {{ 
            background-image: linear-gradient(rgba(27, 94, 32, 0.75), rgba(13, 31, 13, 0.85)), url('{bg_images[2]}');
        }}
    }}
    
    [data-testid="stAppViewContainer"] {{
        animation: manageBgSlide 18s ease-in-out infinite;
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }}
    </style>
    """
    st.markdown(manage_bg, unsafe_allow_html=True)
    
    st.title(f"Manage Account: {st.session_state['username']}")
    if st.sidebar.button("Back to Dashboard"):
        st.session_state.page = "Dashboard"
        st.rerun()
    if st.sidebar.button("Log Out"):
        st.session_state.logged_in = False
        st.session_state.pop('username', None)
        st.session_state.page = "Login"
        st.rerun()
    st.subheader("Change Password")
    with st.form("update_password_form"):
        new_password = st.text_input("New Password", type="password")
        confirm_new_password = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Update Password")
        if submitted:
            if not new_password or not confirm_new_password:
                st.error("Please fill in both fields.")
            elif new_password != confirm_new_password:
                st.error("New passwords do not match.")
            else:
                update_user_password(st.session_state['username'], new_password)
                st.success("Password updated successfully!")

# ==========================
# MAIN APP ROUTER
# ==========================
init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "page" not in st.session_state:
    st.session_state.page = "Login"

if st.session_state.logged_in:
    if st.session_state.page == "Dashboard":
        gdf = load_data('URBAN_RISK_data.csv', encoding='latin1')
        df2 = load_amenity_data('AMENITY_FINAL.csv')
        build_dashboard(gdf, df2)
    elif st.session_state.page == "Manage Account":
        show_manage_account_page()
else:
    if st.session_state.page == "Login":
        show_login_page()
    elif st.session_state.page == "Sign Up":
        show_signup_page()
