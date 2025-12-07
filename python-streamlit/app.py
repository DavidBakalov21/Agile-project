import streamlit as st
import requests
import os
st.title("Upload syllabus")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/upload")

with st.form("upload_form", clear_on_submit=False):
    uploaded_file = st.file_uploader("Choose a file", type=['csv', 'xlsx', 'txt', 'pdf', 'png', 'jpg'])

    submitted = st.form_submit_button("Send")

    if submitted:
        if uploaded_file is None:
            st.error("Please upload a file before sending.")
        else:
            st.info(f"Selected file: {uploaded_file.name}")

            files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}

            try:
                resp = requests.post(BACKEND_URL, files=files)

                if resp.status_code == 200:
                    data = resp.json() 

                    st.success("File sent successfully!")
                    st.write("✔ Backend response:")
                    st.json(data)

                
                    returned_filename = data.get("filename")
                    if returned_filename:
                        st.write(f"Backend processed file: **{returned_filename}**")

                else:
                    st.error(f"Backend error: {resp.status_code}")
                    st.write(resp.text)

            except Exception as e:
                st.error(f"Request failed: {e}")