import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from shapely import wkt
from shapely.errors import WKTReadingError
import plotly.express as px
import warnings
warnings.filterwarnings('ignore')

# --- Page Configuration ---
st.set_page_config(
    page_title="KLIMATA Risk Dashboard",
    page_icon="🗺️",
    layout="wide"
)

# --- Data Loading Function ---
@st.cache_data
def load_data(csv_path, encoding='utf-8'):
    """Loads, cleans, and prepares the data, returning a GeoDataFrame."""

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


# --- Login Logic ---
def check_password():
    """Returns True if the user entered the correct password."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.title("KLIMATA: Urban Risk Assessment Portal")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Log In"):
            if username == "admin" and password == "klimata!":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("😕 User not known or password incorrect")
        return False
    else:
        return True


# --- Dashboard Builder ---
def build_dashboard(gdf):
    # --- Sidebar ---
    st.sidebar.header("Navigation")
    mode = st.sidebar.radio("Select View", ["City Overview", "Barangay Deep Dive"])

    # =======================
    # CITY OVERVIEW SECTION
    # =======================
    if mode == "City Overview":
        st.title("Iloilo City: Urban Risk Dashboard")

        # --- KPIs ---
        avg_risk = gdf['urban_risk_index'].mean()
        avg_infra = gdf['infra_index'].mean()
        avg_wealth = gdf['rwi_mean'].mean()

        col1, col2, col3 = st.columns(3)
        col1.metric("Average Urban Risk", f"{avg_risk:.2f}")
        col2.metric("Average Infrastructure", f"{avg_infra:.2f}")
        col3.metric("Average Relative Wealth", f"{avg_wealth:.2f}")

        # --- INTERACTIVE MAP ---
        iloilo_center = [10.7202, 122.5621]
        m = folium.Map(location=iloilo_center, zoom_start=13)

        # Choropleth
        folium.Choropleth(
            geo_data=gdf,
            name='Urban Risk Index',
            data=gdf,
            columns=['adm4_pcode', 'urban_risk_index'],
            key_on='feature.properties.adm4_pcode',
            fill_color='YlOrRd',
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name='Urban Risk Index'
        ).add_to(m)

        # Tooltips
        folium.GeoJson(
            gdf,
            tooltip=folium.GeoJsonTooltip(
                fields=['brgy_names-ILOILO.location.adm4_en', 'urban_risk_index', 'risk_label'],
                aliases=['Barangay:', 'Risk Index:', 'Risk Level:'],
                localize=True
            )
        ).add_to(m)

        st_folium(m, width='100%', height=600)

        # --- CHARTS ---
        tab1, tab2 = st.tabs(["Top 5 At-Risk Barangays", "Risk Level Distribution"])

        with tab1:
            # --- Top 5 At-Risk Barangays ---
            top_5 = gdf.nlargest(5, 'urban_risk_index')
            top_5_df = top_5[['brgy_names-ILOILO.location.adm4_en', 'urban_risk_index']].copy()
            top_5_df.rename(
                columns={
                    'brgy_names-ILOILO.location.adm4_en': 'Barangay',
                    'urban_risk_index': 'Urban Risk Index'
                },
                inplace=True
            )

            # Create a styled Plotly bar chart
            fig = px.bar(
                top_5_df,
                x='Barangay',
                y='Urban Risk Index',
                title='Top 5 At-Risk Barangays',
                color='Urban Risk Index',
                color_continuous_scale='YlOrRd',
                text='Urban Risk Index',
                labels={'Urban Risk Index': 'Risk Index Value'}
            )
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig.update_layout(
                xaxis_tickangle=-45,
                yaxis_title='Urban Risk Index',
                xaxis_title='Barangay',
                title_x=0.3
            )
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            # --- Risk Level Distribution ---
            st.subheader("Risk Level Distribution")
            risk_counts = gdf['risk_label'].value_counts()
            risk_df = pd.DataFrame({'Risk Level': risk_counts.index, 'Count': risk_counts.values})

            color_map = {'High Risk': 'red', 'Medium Risk': 'orange', 'Low Risk': 'yellow'}

            fig = px.pie(
                risk_df,
                values='Count',
                names='Risk Level',
                color='Risk Level',
                color_discrete_map=color_map,
                title='Risk Level Distribution'
            )
            st.plotly_chart(fig, use_container_width=True)

    # ============================
    # BARANGAY DEEP DIVE SECTION
    # ============================
    else:
        brgy_list = gdf['brgy_names-ILOILO.location.adm4_en'].unique()
        selected_brgy = st.sidebar.selectbox("Select a Barangay", brgy_list)
        brgy_data = gdf[gdf['brgy_names-ILOILO.location.adm4_en'] == selected_brgy].iloc[0]

        st.title(f"Dashboard for: {selected_brgy}")

        # --- KPIs ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Urban Risk Score", f"{brgy_data['urban_risk_index']:.2f}")
        col2.metric("Risk Level", brgy_data['risk_label'])
        col3.metric("Relative Wealth Index", f"{brgy_data['rwi_mean']:.2f}")

        # --- INTERACTIVE MAP for specific Barangay ---
        brgy_gdf = gpd.GeoDataFrame([brgy_data], geometry='geometry')
        brgy_gdf.set_crs(epsg=4326, inplace=True)

        m = folium.Map(
            location=[
                brgy_gdf.geometry.centroid.y.iloc[0],
                brgy_gdf.geometry.centroid.x.iloc[0]
            ],
            zoom_start=15
        )

        folium.GeoJson(
            brgy_gdf,
            style_function=lambda x: {'fillColor': 'blue', 'color': 'blue'},
            tooltip=folium.GeoJsonTooltip(
                fields=['brgy_names-ILOILO.location.adm4_en', 'urban_risk_index', 'risk_label'],
                aliases=['Barangay:', 'Risk Index:', 'Risk Level:'],
                localize=True
            )
        ).add_to(m)

        st_folium(m, width='100%', height=500)

        # --- BARANGAY vs CITY COMPARISON ---
        st.subheader("Barangay vs. City Average")

        avg_scores = {
            'Climate Exposure': gdf['climate_exposure_score'].mean(),
            'Infrastructure Index': gdf['infra_index'].mean(),
            'Relative Wealth': gdf['rwi_mean'].mean()
        }

        brgy_scores = {
            'Climate Exposure': brgy_data['climate_exposure_score'],
            'Infrastructure Index': brgy_data['infra_index'],
            'Relative Wealth': brgy_data['rwi_mean']
        }

        chart_data = pd.DataFrame({'City Average': avg_scores, selected_brgy: brgy_scores})
        st.bar_chart(chart_data)


# --- Main App Execution ---
if check_password():
    gdf = load_data('URBAN_RISK_data.csv', encoding='latin1')
    build_dashboard(gdf)
