import streamlit as st
import streamlit.web.bootstrap


# -- Set page config
apptitle = 'Navigator'
st.set_page_config(page_title=apptitle,
                   layout="wide",
                   initial_sidebar_state="expanded")

st.title("Relocation Navigator")

#Sidebar ----------------------------------------------------
st.sidebar.markdown("## Sidebar")

#Main --------------------------------------------------------
st.write("Map")



