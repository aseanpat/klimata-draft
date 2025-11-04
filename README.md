KLIMATA: Iloilo City Climate Vulnerability Index
KLIMATA is an interactive web dashboard built with Streamlit for visualizing the urban risk and climate vulnerability of barangays in Iloilo City. It features a full user authentication system (CRUD) and a dual-view dashboard for both high-level "City Overview" and detailed "Barangay Deep Dive" analysis.
🚀 Features
•	Full User Account CRUD:
o	Create: Secure user sign-up page with password hashing.
o	Read: Secure login page to verify user credentials.
o	Update: "Manage Account" page for users to change their password.
o	Delete: (Not included in your final code, but delete_user function exists).
•	Database Persistence: Uses Python's built-in sqlite3 to create a users.db file to store and manage user accounts. No external database server required.
•	"City Overview" Dashboard:
o	Interactive choropleth map of Iloilo City.
o	Map layer selector to visualize: Urban Risk, Population, Amenity Index, and Climate Exposure.
o	Dynamic KPIs for city-wide averages.
o	Plotly charts showing the "Top 5 At-Risk Barangays" and "Risk Level Distribution."
•	"Barangay Deep Dive" Dashboard:
o	Searchable dropdown menu to select any barangay.
o	Detailed KPIs, a zoomed-in map, and a comparative chart for nearest amenities.
•	Custom UI:
o	Polished interface using streamlit-option-menu and streamlit-extras.
o	Themed background images for different sections of the app.
🛠️ Tech Stack
•	Framework: Streamlit
•	Data Analysis: pandas
•	Geospatial: geopandas, folium, streamlit-folium, shapely
•	Data Visualization: plotly.express
•	Database & Auth: sqlite3, hashlib
•	UI Components: streamlit-option-menu, streamlit-extras
⚙️ Setup and Installation
To run this project locally, follow these steps:
1. Clone the Repository
Bash
git clone https://github.com/your-username/klimata.git
cd klimata
2. Create a Virtual Environment (Recommended)
Bash
# For Windows
python -m venv venv
venv\Scripts\activate

# For macOS/Linux
python3 -m venv venv
source venv/bin/activate
3. Install Dependencies Create a file named requirements.txt in the project folder and paste the following lines into it:
Plaintext
streamlit
pandas
geopandas
folium
streamlit-folium
plotly
shapely
streamlit-option-menu
streamlit-extras
Then, install all the libraries at once:
Bash
pip install -r requirements.txt
4. Place Data Files Make sure your data files are in the same project directory as app.py:
•	URBAN_RISK_data.csv
•	AMENITY_FINAL.csv
5. Run the Application
Bash
streamlit run app.py
Your browser will automatically open to the login page.
Usage
1.	Sign Up: Launch the app and click the "Need an account? Sign Up" button. Create a new user. The app will create a users.db file in your folder to store your credentials.
2.	Log In: Use your new credentials to log in.
3.	Explore:
o	City Overview: View the city map. Use the sidebar radio buttons to change the map layer.
o	Barangay Deep Dive: Select this view, then use the sidebar search to find a specific barangay and see its detailed stats.
o	Manage Account: Change your password from the sidebar menu.
o	Log Out: Securely log out of the application.

