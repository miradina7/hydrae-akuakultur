import streamlit as st
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import pandas as pd
import os
import requests
from datetime import datetime
import streamlit.components.v1 as components

# --- 1. PAGE SETUP & STYLING ---
st.set_page_config(page_title="Hydrae App", layout="centered", page_icon="💧")

st.markdown("""
<style>
    .dss-card { padding: 20px; border-radius: 15px; margin-top: 15px; color: white; }
    .dss-critical { background-color: #EF4444; border-left: 8px solid #991B1B; }
    .dss-warning { background-color: #F59E0B; border-left: 8px solid #B45309; }
    .dss-optimal { background-color: #10B981; border-left: 8px solid #047857; }
    .app-header { text-align: center; margin-bottom: 30px; }
</style>
""", unsafe_allow_html=True)

# --- 2. APP MEMORY (SESSION STATE) ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = "login"
if 'farm_profile' not in st.session_state:
    st.session_state.farm_profile = {}

def go_to_setup():
    st.session_state.current_page = "setup"

def go_to_dashboard(farm_name, location, sys_type, water_type):
    st.session_state.farm_profile = {
        "name": farm_name, "location": location, "system": sys_type, "water": water_type
    }
    st.session_state.current_page = "dashboard"

def logout():
    st.session_state.current_page = "login"
    st.session_state.farm_profile = {}

# --- 3. SCREEN 1: LOGIN ---
if st.session_state.current_page == "login":
    st.markdown("<h1 class='app-header'>💧 Hydrae</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Collaborate with Universiti Putra Malaysia</p>", unsafe_allow_html=True)
    st.write("---")
    st.subheader("Log In / Sign Up")
    phone = st.text_input("Mobile Number", placeholder="+60 12-345-6789")
    otp = st.text_input("Enter OTP", type="password", placeholder="6-digit code")
    if st.button("Verify & Login", use_container_width=True, type="primary"):
        if phone and otp: go_to_setup()
        else: st.error("Please enter any phone number and OTP to test the flow.")

# --- 4. SCREEN 2: FARM SETUP ---
elif st.session_state.current_page == "setup":
    st.title("Welcome to Hydrae!")
    st.write("Let's set up your farm's profile.")
    farm_name = st.text_input("Farm Name", "Abdullah's Farm")
    farm_loc = st.text_input("Location (City, Country)", "Selangor, MY")
    
    c1, c2 = st.columns(2)
    with c1: water_type = st.selectbox("Type of Water", ["Freshwater", "Saltwater"])
    with c2: sys_type = st.selectbox("System Type", ["Pond", "Tank", "Cage", "RAS"])
        
    st.write("### Water Body Dimensions")
    d1, d2, d3 = st.columns(3)
    d1.number_input("Length (m)", value=10)
    d2.number_input("Width (m)", value=5)
    d3.number_input("Depth (m)", value=2)
    
    st.write("---")
    if st.button("Complete Setup & Open DSS", use_container_width=True, type="primary"):
        go_to_dashboard(farm_name, farm_loc, sys_type, water_type)

# --- 5. SCREEN 3: THE MAIN APP (WITH TABS) ---
elif st.session_state.current_page == "dashboard":
    
    # [ANA'S FUZZY LOGIC ENGINE]
    temp = ctrl.Antecedent(np.arange(20, 36, 1), 'temp')
    salinity = ctrl.Antecedent(np.arange(0, 31, 1), 'salinity')
    action = ctrl.Consequent(np.arange(0, 101, 1), 'action')

    temp['optimal'] = fuzz.trimf(temp.universe, [20, 20, 30])
    temp['high'] = fuzz.trimf(temp.universe, [28, 35, 35])
    salinity['low'] = fuzz.trimf(salinity.universe, [0, 0, 15])
    salinity['high'] = fuzz.trimf(salinity.universe, [10, 30, 30])

    action['status_quo'] = fuzz.trimf(action.universe, [0, 0, 35])
    action['aeration'] = fuzz.trimf(action.universe, [30, 50, 70])
    action['change_water'] = fuzz.trimf(action.universe, [65, 100, 100])

    rule1 = ctrl.Rule(temp['high'] & salinity['high'], action['change_water'])
    rule2 = ctrl.Rule(temp['high'] & salinity['low'], action['aeration'])
    rule3 = ctrl.Rule(temp['optimal'] & salinity['high'], action['aeration'])
    rule4 = ctrl.Rule(temp['optimal'] & salinity['low'], action['status_quo'])

    dss_ctrl = ctrl.ControlSystem([rule1, rule2, rule3, rule4])
    dss_sim = ctrl.ControlSystemSimulation(dss_ctrl)

    def get_live_weather(location):
        api_key = "59f5830a6b44d7d166644e4977168038"
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                return data['main']['temp'], data['weather'][0]['main'], True
            return None, None, False
        except:
            return None, None, False

    def save_reading(t, s, d, a, r, stat):
        file = "farm_log.csv"
        entry = pd.DataFrame([{
            "Date/Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Temp (°C)": t, "Salinity (ppt)": s, "DO (mg/L)": d, "Ammonia (ppm)": a,
            "Risk Score (%)": round(r, 2), "DSS Status": stat
        }])
        entry.to_csv(file, mode='a', index=False, header=not os.path.exists(file))

    # [UI HEADER]
    col_head, col_out = st.columns([4, 1])
    with col_head:
        st.title(f"💧 {st.session_state.farm_profile['name']}")
        st.write(f"📍 {st.session_state.farm_profile['location']} | {st.session_state.farm_profile['system']} ({st.session_state.farm_profile['water']})")
    with col_out:
        if st.button("Log Out"): logout()

    st.write("---")

    # === THE APP NAVIGATION TABS ===
    tab_dash, tab_report, tab_notif, tab_ana = st.tabs(["📊 DSS Dashboard", "📑 Farm Reports", "🔔 Notifications", "📱 Mobile UI (Ana)"])

    # -----------------------------------------
    # TAB 1: THE DSS DASHBOARD
    # -----------------------------------------
    with tab_dash:
        st.subheader("⚙️ Live Inputs")
        with st.expander("External API (Weather/Tides)", expanded=True):
            loc = st.session_state.farm_profile['location']
            api_temp, api_condition, api_success = get_live_weather(loc)
            
            if api_success:
                st.success(f"Live: {api_condition} | {api_temp}°C")
                if api_condition in ["Rain", "Drizzle", "Thunderstorm"]: weather = "Heavy Rain ⛈️"
                elif api_condition in ["Clouds"]: weather = "Cloudy ☁️"
                else: weather = "Sunny ☀️"
                st.write(f"**DSS Override:** {weather}")
                default_temp = float(api_temp)
            else:
                st.warning("API offline. Manual override.")
                weather = st.selectbox("Current Weather", ["Sunny ☀️", "Heavy Rain ⛈️", "Cloudy ☁️"])
                default_temp = 26.0

        with st.expander("Water Quality Sensors", expanded=True):
            input_t = st.slider("Temperature (°C)", 20.0, 35.0, default_temp, step=0.1)
            input_s = st.slider("Salinity (ppt)", 0, 30, 12)
            input_do = st.slider("Dissolved Oxygen (mg/L)", 2.0, 10.0, 6.5)
            input_amm = st.number_input("Ammonia (ppm)", 0.0, 2.0, 0.05, step=0.01)

        st.subheader("🧠 DSS: Decide & Act")
        
        try:
            dss_sim.input['temp'] = input_t
            dss_sim.input['salinity'] = input_s
            dss_sim.compute()
            risk_score = dss_sim.output['action']
        except:
            risk_score = 0

        final_status, cause, impact, action_step, css_class = "", "", "", "", ""

        if weather == "Heavy Rain ⛈️" and input_t < 26:
            final_status, cause, impact, action_step, css_class = "WARNING: Climate Stress", "API detects Rain.", "Potential pH crash.", "1. Apply Lime.\n2. Delay feeding.", "dss-warning"
        elif input_amm > 0.5:
            final_status, cause, impact, action_step, css_class = "CRITICAL: Toxicity", f"Ammonia ({input_amm:.2f} ppm) is high.", "Gill damage.", "1. STOP FEEDING.\n2. 30% water exchange.", "dss-critical"
        elif risk_score >= 60:
            final_status, cause, impact, action_step, css_class = "CRITICAL: Poor Water Quality", "High Temp & Salinity.", "Osmotic stress.", "1. 50% Water Exchange.\n2. Turn on aerators.", "dss-critical"
        elif risk_score >= 30:
            final_status, cause, impact, action_step, css_class = "WARNING: System Degradation", "Rising Temp.", "Oxygen demand rising.", "1. Increase Aeration.\n2. Monitor closely.", "dss-warning"
        else:
            final_status, cause, impact, action_step, css_class = "OPTIMAL: Stable Conditions", "Parameters safe.", "Maximum growth.", "Maintain standard procedures.", "dss-optimal"

        st.markdown(f"""
            <div class="dss-card {css_class}">
                <h2 style="margin-top:0; border-bottom: 2px solid rgba(255,255,255,0.3); padding-bottom: 10px;">{final_status}</h2>
                <p><b>🔍 CAUSE:</b> {cause} | <b>⚠️ IMPACT:</b> {impact}</p>
                <div style="background: rgba(0,0,0,0.2); padding: 15px; border-radius: 8px; margin-top: 15px;">
                    <h4 style="margin:0; color: #FFF;">📋 ACTION: {action_step}</h4>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Risk Score", f"{risk_score:.1f}%")
        m2.metric("Temp", f"{input_t:.1f} °C")
        m3.metric("Salinity", f"{input_s} ppt")
        m4.metric("Ammonia", f"{input_amm:.2f} ppm")

        st.write("---")
        if st.button("💾 Log Current Reading", use_container_width=True):
            save_reading(input_t, input_s, input_do, input_amm, risk_score, final_status)
            st.success("Reading saved to your farm database!")

    # -----------------------------------------
    # TAB 2: FARM REPORTS 
    # -----------------------------------------
    with tab_report:
        st.subheader("📑 Farm Systems Analytics")
        st.write("Historical water quality tracking and database.")
        
        if os.path.exists("farm_log.csv"):
            df = pd.read_csv("farm_log.csv")
            if not df.empty:
                st.write("**📈 Parameter Trend Graph**")
                st.line_chart(df[['Temp (°C)', 'DO (mg/L)', 'Ammonia (ppm)']])
                
                st.write("**🗄️ Raw Data Logs**")
                st.dataframe(df, use_container_width=True)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Export Database to CSV", data=csv, file_name="Hydrae_Reports.csv", mime="text/csv", use_container_width=True)
            else:
                st.info("No data logged yet. Take a reading in the Dashboard to see reports.")
        else:
            st.info("No data logged yet. Take a reading in the Dashboard to see reports.")

    # -----------------------------------------
    # TAB 3: NOTIFICATIONS 
    # -----------------------------------------
    with tab_notif:
        st.subheader("🔔 System Alerts & Notifications")
        
        if os.path.exists("farm_log.csv"):
            df = pd.read_csv("farm_log.csv")
            alerts_df = df[df['DSS Status'].str.contains("WARNING|CRITICAL", na=False)]
            
            if alerts_df.empty:
                st.success("🎉 All clear! No critical alerts or warnings recorded in the system.")
            else:
                st.write("Recent system triggers requiring attention:")
                for index, row in alerts_df.iloc[::-1].iterrows():
                    if "CRITICAL" in row['DSS Status']:
                        st.error(f"🚨 **{row['Date/Time']}**\n\n{row['DSS Status']} | Risk Score: {row['Risk Score (%)']}%")
                    elif "WARNING" in row['DSS Status']:
                        st.warning(f"⚠️ **{row['Date/Time']}**\n\n{row['DSS Status']} | Risk Score: {row['Risk Score (%)']}%")
        else:
            st.info("No system activity recorded yet.")

    # -----------------------------------------
    # TAB 4: ANA'S FRONTEND HTML
    # -----------------------------------------
    with tab_ana:
        st.subheader("📱 Native Mobile Experience")
        st.write("This is Ana's frontend design embedded directly into our app.")
        
        try:
            with open("dss_akuakultur.html", "r", encoding="utf-8") as f:
                html_code = f.read()
            components.html(html_code, height=850, scrolling=True)
        except FileNotFoundError:
            st.error("Could not find 'dss_akuakultur.html'. Please make sure it is saved in the exact same folder as this Python script!")