import streamlit as st
from PIL import Image, ImageOps
import io
import zipfile
from datetime import datetime
import cv2
import numpy as np
import os

# ページ設定
st.set_page_config(page_title="画像リサイズ & 連番リネーム", layout="centered")

st.title("🖼️ 画像リサイズ & 連番リネーム")
st.write("画像をアップロードすると、指定サイズにリサイズし、ルールに従ってリネームしてZip化します。")

# --- 設定エリア ---
st.markdown("### 1. リサイズ設定")

# サイズと接頭辞の定義
# キー: 表示名, 値: {"size": (幅, 高さ), "prefix": 接頭辞}
SIZE_SETTINGS = {
    "1200 × 628 (Webサイト・OGP等)": {"size": (1200, 628), "prefix": "c"},
    "1080 × 1080 (Instagram等)": {"size": (1080, 1080), "prefix": "s"},
    "600 × 400 (ブログサムネイル等)": {"size": (600, 400), "prefix": "m"}
}

selected_option_key = st.selectbox("サイズを選択", list(SIZE_SETTINGS.keys()))
selected_setting = SIZE_SETTINGS[selected_option_key]
target_size = selected_setting["size"]
file_prefix = selected_setting["prefix"]

# 連番設定
st.markdown("### 2. ファイル名設定")
col1, col2 = st.columns(2)
with col1:
    start_number = st.number_input("開始番号 (No.)", min_value=1, value=1, step=1, help="ここに入力した番号から連番が始まります。")

with col2:
    st.info(f"命名プレビュー: **{file_prefix}{start_number:03d}.jpg** ...")

# OpenCV処理のオプション
use_sharpen = st.checkbox("画像をくっきりさせる (OpenCV使用)", value=True)

# --- アップロードエリア ---
st.markdown("### 3. 画像をアップロード")
uploaded_files = st.file_uploader(
    "複数の画像を選択できます", 
    type=['png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

# --- 内部関数: OpenCV処理 ---
def process_with_opencv(pil_image):
    # PIL -> OpenCV (BGR)
    img_array = np.array(pil_image)
    cv_image = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    # シャープネス処理
    if use_sharpen:
        kernel = np.array([[0, -1, 0],
                           [-1, 5, -1],
                           [0, -1, 0]])
        cv_image = cv2.filter2D(cv_image, -1, kernel)

    # OpenCV (BGR) -> PIL
    cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
    return Image.fromarray(cv_image)

# ---
