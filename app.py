import streamlit as st
from crew import HunterCrew

st.title('Crew Hunter!')

query = st.text_input('How can I help?')

if st.button('Submit'):
    with st.spinner("Searching..."):
        results = HunterCrew(query).run()
        results = results.replace("```", "")
        results = results.replace("#", "")
        
        st.write(results)
