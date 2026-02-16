import streamlit as st
import easyocr
import cv2
import numpy as np
import pandas as pd
from PIL import Image
import tempfile

st.set_page_config(page_title="Attendance Sheet Digitizer", layout="wide")

st.title("📋 Attendance Sheet → Excel Converter (Handwriting OCR)")

st.write("Upload attendance sheet image. System will extract names and P/AB marks. You can edit before export.")

# -------------------------
# Load OCR reader (cached)
# -------------------------
@st.cache_resource
def load_reader():
    return easyocr.Reader(['en'])

reader = load_reader()

# -------------------------
# Upload Image
# -------------------------
uploaded = st.file_uploader("Upload attendance sheet image", type=["jpg","jpeg","png"])

if uploaded:

    image = Image.open(uploaded)
    st.image(image, caption="Uploaded Image", use_column_width=True)

    # Convert to OpenCV format
    img = np.array(image)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Improve contrast
    gray = cv2.adaptiveThreshold(
        gray,255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,11,2
    )

    st.subheader("🔍 Running OCR...")
    results = reader.readtext(gray)

    texts = [r[1] for r in results]

    # -------------------------
    # Extract names
    # -------------------------
    names = []
    for t in texts:
        if len(t) > 5 and t.replace(" ", "").isalpha():
            names.append(t.title())

    # remove duplicates
    names = list(dict.fromkeys(names))

    # -------------------------
    # Extract P / AB marks
    # -------------------------
    marks = []
    for t in texts:
        val = t.upper().strip()

        if val in ["P","A","AB"]:
            marks.append(val)

    # -------------------------
    # Guess number of sessions
    # -------------------------
    if len(names) > 0:
        sessions = max(1, len(marks)//len(names))
    else:
        sessions = 1

    # -------------------------
    # Build attendance table
    # -------------------------
    data = []

    idx = 0
    for n in names:
        row = {"Name": n}
        for s in range(sessions):
            if idx < len(marks):
                row[f"S{s+1}"] = marks[idx]
            else:
                row[f"S{s+1}"] = ""
            idx += 1
        data.append(row)

    df = pd.DataFrame(data)

    # -------------------------
    # Editable table
    # -------------------------
    st.subheader("✏️ Edit if needed")
    edited = st.data_editor(df, use_container_width=True)

    # -------------------------
    # Totals
    # -------------------------
    if not edited.empty:
        session_cols = [c for c in edited.columns if c.startswith("S")]

        edited["Present"] = edited[session_cols].apply(
            lambda r: sum(x=="P" for x in r), axis=1)

        edited["Absent"] = edited[session_cols].apply(
            lambda r: sum(x in ["A","AB"] for x in r), axis=1)

        edited["Attendance %"] = (
            edited["Present"] /
            (edited["Present"] + edited["Absent"]).replace(0,1)
        ) * 100

        st.subheader("📊 Final Table")
        st.dataframe(edited)

        # -------------------------
        # Download Excel
        # -------------------------
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        edited.to_excel(tmp.name, index=False)

        with open(tmp.name, "rb") as f:
            st.download_button(
                "⬇️ Download Excel",
                f,
                file_name="attendance.xlsx"
            )
