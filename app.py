import streamlit as st
import cv2
import numpy as np
import pandas as pd
import easyocr
from PIL import Image
import tempfile

st.set_page_config(page_title="Attendance Digitizer", layout="wide")

st.title("📋 Handwritten Attendance Sheet Digitizer")

st.write("Upload attendance sheet image → Get structured Excel")

uploaded = st.file_uploader("Upload Image", type=["png","jpg","jpeg"])

if uploaded:

    # save temp image
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(uploaded.read())
        path = tmp.name

    img = cv2.imread(path)

    # auto rotate if sideways
    h,w = img.shape[:2]
    if w > h:
        img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # -------- preprocess --------
    thresh = cv2.adaptiveThreshold(
        gray,255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,15,4
    )

    # -------- detect grid --------
    vk = cv2.getStructuringElement(cv2.MORPH_RECT,(1,60))
    hk = cv2.getStructuringElement(cv2.MORPH_RECT,(60,1))

    grid = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vk) + \
           cv2.morphologyEx(thresh, cv2.MORPH_OPEN, hk)

    cnts,_ = cv2.findContours(grid, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    boxes=[]
    for c in cnts:
        x,y,w,h = cv2.boundingRect(c)
        if w>80 and h>30:
            boxes.append((x,y,w,h))

    boxes = sorted(boxes, key=lambda b:(b[1],b[0]))

    # -------- group rows --------
    rows=[]
    cur=[]
    last_y=-100

    for b in boxes:
        if abs(b[1]-last_y) < 40:
            cur.append(b)
        else:
            if cur:
                rows.append(sorted(cur))
            cur=[b]
            last_y=b[1]

    if cur:
        rows.append(sorted(cur))

    st.info(f"Detected {len(rows)} rows")

    # -------- OCR --------
    with st.spinner("Reading handwriting..."):
        reader = easyocr.Reader(['en'])

        table=[]

        for row in rows:
            r=[]
            for (x,y,w,h) in row:
                crop = gray[y:y+h, x:x+w]
                txt = reader.readtext(crop, detail=0)
                val = txt[0] if txt else ""

                val = val.upper().strip()

                # attendance cleaning
                if "AB" in val:
                    val = "A"
                elif val == "A":
                    val = "A"
                elif "P" in val:
                    val = "P"

                r.append(val)

            table.append(r)

    # normalize columns
    maxc = max(len(r) for r in table)
    for r in table:
        r += [""]*(maxc-len(r))

    df = pd.DataFrame(table)

    st.subheader("📊 Detected Table (Editable)")
    edited = st.data_editor(df, use_container_width=True)

    # -------- download --------
    excel_bytes = edited.to_excel(index=False, engine="openpyxl")

    st.download_button(
        "⬇ Download Excel",
        excel_bytes,
        file_name="attendance.xlsx"
    )
