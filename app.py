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
    page_icon="🌿"
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

    # Apply dark mode nature-themed styling
    st.markdown("""
    <style>
    .stApp {background: #1a2e1a; color: #FFFFFF;}
    [data-testid="stHeader"] {background-color: #2d5016;}
    div[data-testid="stMetricValue"] {color: #a8d5a8 !important; font-size: 1.8rem !important; font-weight: 600 !important;}
    div[data-testid="stMetricLabel"] {color: #d4e8d4 !important; font-size: 1rem !important;}
    section[data-testid="stSidebar"] {background: #1f3a11; color: #FFFFFF;}
    h1, h2, h3 {color: #FFFFFF !important;}
    .stRadio > label {color: #FFFFFF !important; font-weight: 500 !important;}
    .stRadio > div {color: #FFFFFF !important;}
    .stSelectbox > label {color: #FFFFFF !important;}
    .stSelectbox div[data-baseweb="select"] {color: #FFFFFF !important;}
    .stSelectbox div[data-baseweb="select"] > div {color: #FFFFFF !important;}
    .stSelectbox [data-baseweb="select"] span {color: #FFFFFF !important;}
    .stSelectbox input {color: #FFFFFF !important;}
    .stTextInput > label {color: #FFFFFF !important;}
    .stTextInput input {background-color: #FFFFFF; color: #1a1a1a !important;}
    </style>
    """, unsafe_allow_html=True)
    metric_style = dict(background_color="#2a3f2a", border_left_color="#8abf8b", border_color="#558b2f")

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
                "icon": {"color": "#8abf8b", "font-size": "18px"},
                "nav-link": {"color": "#d4e8d4", "font-size": "15px", "text-align": "left"},
                "nav-link-selected": {"background-color": "#8abf8b", "color": "white"},
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
        # Static background for City Overview
        city_overview_bg = """
        <style>
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(rgba(10, 31, 10, 0.85), rgba(10, 31, 10, 0.85)),
                        url('https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=1920&q=80');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            background-repeat: no-repeat;
        }
        [data-testid="stAppViewContainer"] h1 {
            color: #FFFFFF !important;
        }
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
        # Static background for Barangay Deep Dive
        deep_dive_bg = """
        <style>
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(rgba(10, 31, 10, 0.85), rgba(10, 31, 10, 0.85)),
                        url('https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?w=1920&q=80');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            background-repeat: no-repeat;
        }
        </style>
        """
        st.markdown(deep_dive_bg, unsafe_allow_html=True)
        
        st.title("Barangay Deep Dive")
        brgy_list = sorted(gdf['barangay_name'].dropna().unique())

        selected_brgy = st.sidebar.selectbox("Select a Barangay", brgy_list)
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
        
        if 'date' in df2.columns:
            df2['date'] = pd.to_datetime(df2['date'], errors='coerce')
            df2['year'] = df2['date'].dt.year
            available_years = sorted(df2['year'].dropna().unique().astype(int))
            selected_year = st.selectbox("Filter by Year", available_years, index=len(available_years)-1 if available_years else 0)
            brgy_amenities = df2[(df2['barangay_name'] == selected_brgy) & (df2['year'] == selected_year)]
        else:
            brgy_amenities = df2[df2['barangay_name'] == selected_brgy]

        if not brgy_amenities.empty:
            amenity_cols = ['college_nearest', 'community_centre_nearest', 'school_nearest',
                            'shelter_nearest', 'town_hall_nearest', 'university_nearest']
            amenity_data = brgy_amenities[amenity_cols].melt(var_name='Amenity Type', value_name='Distance (km)')
            amenity_data['Distance (km)'] = amenity_data['Distance (km)'] / 1000
            amenity_data['Amenity Type'] = amenity_data['Amenity Type'].str.replace('_nearest', '').str.replace('_', ' ').str.title()

            fig = px.bar(
                amenity_data,
                x='Amenity Type',
                y='Distance (km)',
                title=f"Nearest Facilities from {selected_brgy}",
                color='Distance (km)',
                color_continuous_scale='tealgrn'
            )
            fig.update_traces(texttemplate='%{y:.2f}', textposition='outside')
            fig.update_layout(xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)

            amenity_data['Distance (km)'] = amenity_data['Distance (km)'].apply(lambda x: f"{x:.2f} km")
            st.dataframe(amenity_data)
        else:
            st.info("No amenity data available for this barangay.")

# ==========================
# PAGE FUNCTIONS
# ==========================
def show_login_page():
    """Login page with enhanced UI"""
    
    page_bg_img = """
    <style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, rgba(27, 94, 32, 0.7), rgba(46, 125, 50, 0.8)),
                    url('https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=1920&q=80');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    
    [data-testid="stHeader"], [data-testid="stSidebar"] {{ display: none; }}
    
    .block-container {{
        max-width: 480px !important;
        padding-top: 8vh !important;
        margin: 0 auto !important;
    }}
    
    .main .block-container {{
        max-width: 480px !important;
    }}
    
    div[data-testid="stVerticalBlock"] > div:first-child {{
        background: rgba(255, 255, 255, 0.12);
        padding: 3.5rem 2.5rem;
        border-radius: 24px;
        backdrop-filter: blur(16px);
        border: 1px solid rgba(138, 191, 139, 0.4);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3), 0 0 80px rgba(138, 191, 139, 0.15);
    }}
    
    h1 {{
        color: #FFFFFF !important;
        text-align: center;
        text-shadow: 2px 4px 12px rgba(0, 0, 0, 0.6);
        font-weight: 700;
        font-size: 2rem !important;
        margin-bottom: 0.5rem !important;
        letter-spacing: 0.5px;
    }}
    
    .subtitle {{
        color: #C8E6C9;
        text-align: center;
        font-size: 0.95rem;
        margin-bottom: 2rem;
        text-shadow: 1px 2px 6px rgba(0, 0, 0, 0.5);
    }}
    
    label {{
        color: #FFFFFF !important;
        font-weight: 600;
        font-size: 0.95rem !important;
        text-shadow: 1px 2px 4px rgba(0, 0, 0, 0.4);
        margin-bottom: 0.5rem !important;
    }}
    
    .stTextInput > div > div > input {{
        background-color: rgba(255, 255, 255, 0.95) !important;
        border-radius: 12px;
        border: 2px solid rgba(138, 191, 139, 0.6);
        color: #1B5E20 !important;
        padding: 0.75rem 1rem !important;
        font-size: 1rem !important;
        transition: all 0.3s ease;
    }}
    
    .stTextInput > div > div > input:focus {{
        border-color: #8abf8b !important;
        box-shadow: 0 0 0 3px rgba(138, 191, 139, 0.2) !important;
    }}
    
    .stButton > button {{
        width: 100%;
        background: linear-gradient(135deg, #8abf8b, #6fa870);
        color: white;
        border-radius: 12px;
        font-weight: 700;
        font-size: 1.05rem;
        padding: 0.75rem 1.5rem;
        border: none;
        box-shadow: 0 6px 20px rgba(138, 191, 139, 0.4);
        transition: all 0.3s ease;
        margin-top: 1rem;
    }}
    
    .stButton > button:hover {{
        background: linear-gradient(135deg, #6fa870, #5a8f5b);
        box-shadow: 0 8px 24px rgba(111, 168, 112, 0.5);
        transform: translateY(-2px);
    }}
    
    hr {{
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(138, 191, 139, 0.5), transparent);
        margin: 2rem 0;
    }}
    
    .stAlert {{
        background-color: rgba(255, 255, 255, 0.95) !important;
        border-radius: 10px;
    }}
    </style>
    """
    
    st.markdown(page_bg_img, unsafe_allow_html=True)
    st.title("KLIMATA")
    st.markdown('<p class="subtitle">Climate Risk Assessment Portal</p>', unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
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
    page_bg_img = """
    <style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, rgba(27, 94, 32, 0.7), rgba(46, 125, 50, 0.8)),
                    url('https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=1920&q=80');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    
    [data-testid="stHeader"], [data-testid="stSidebar"] {{ display: none; }}
    
    .block-container {{
        max-width: 480px !important;
        padding-top: 6vh !important;
        margin: 0 auto !important;
    }}
    
    .main .block-container {{
        max-width: 480px !important;
    }}
    
    div[data-testid="stVerticalBlock"] > div:first-child {{
        background: rgba(255, 255, 255, 0.12);
        padding: 3.5rem 2.5rem;
        border-radius: 24px;
        backdrop-filter: blur(16px);
        border: 1px solid rgba(138, 191, 139, 0.4);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3), 0 0 80px rgba(138, 191, 139, 0.15);
    }}
    
    h1 {{
        color: #FFFFFF !important;
        text-align: center;
        text-shadow: 2px 4px 12px rgba(0, 0, 0, 0.6);
        font-weight: 700;
        font-size: 1.9rem !important;
        margin-bottom: 0.5rem !important;
        letter-spacing: 0.5px;
    }}
    
    .subtitle {{
        color: #C8E6C9;
        text-align: center;
        font-size: 0.9rem;
        margin-bottom: 2rem;
        text-shadow: 1px 2px 6px rgba(0, 0, 0, 0.5);
    }}
    
    label {{
        color: #FFFFFF !important;
        font-weight: 600;
        font-size: 0.95rem !important;
        text-shadow: 1px 2px 4px rgba(0, 0, 0, 0.4);
        margin-bottom: 0.5rem !important;
    }}
    
    .stTextInput > div > div > input {{
        background-color: rgba(255, 255, 255, 0.95) !important;
        border-radius: 12px;
        border: 2px solid rgba(138, 191, 139, 0.6);
        color: #1B5E20 !important;
        padding: 0.75rem 1rem !important;
        font-size: 1rem !important;
        transition: all 0.3s ease;
    }}
    
    .stTextInput > div > div > input:focus {{
        border-color: #8abf8b !important;
        box-shadow: 0 0 0 3px rgba(138, 191, 139, 0.2) !important;
    }}
    
    .stButton > button {{
        width: 100%;
        background: linear-gradient(135deg, #8abf8b, #6fa870);
        color: white;
        border-radius: 12px;
        font-weight: 700;
        font-size: 1.05rem;
        padding: 0.75rem 1.5rem;
        border: none;
        box-shadow: 0 6px 20px rgba(138, 191, 139, 0.4);
        transition: all 0.3s ease;
        margin-top: 1rem;
    }}
    
    .stButton > button:hover {{
        background: linear-gradient(135deg, #6fa870, #5a8f5b);
        box-shadow: 0 8px 24px rgba(111, 168, 112, 0.5);
        transform: translateY(-2px);
    }}
    
    .stAlert {{
        background-color: rgba(255, 255, 255, 0.95) !important;
        border-radius: 10px;
    }}
    </style>
    """
    
    st.markdown(page_bg_img, unsafe_allow_html=True)
    st.title("Create Account")
    st.markdown('<p class="subtitle">Join KLIMATA to access climate risk data</p>', unsafe_allow_html=True)
    
    with st.form("signup_form"):
        username = st.text_input("Username", placeholder="Choose a username")
        password = st.text_input("Password", type="password", placeholder="Create a password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter your password")
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
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Back to Login"):
        st.session_state.page = "Login"
        st.rerun()

def show_manage_account_page():
    # Static background for Manage Account page
    manage_bg = """
    <style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(rgba(10, 31, 10, 0.85), rgba(10, 31, 10, 0.85)),
                    url('https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?w=1920&q=80');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }
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
