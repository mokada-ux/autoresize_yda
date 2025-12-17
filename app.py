import streamlit as st
from PIL import Image, ImageOps
import io
import zipfile
from datetime import datetime
import cv2
import numpy as np

# ページ設定
st.set_page_config(page_title="画像一括リサイズアプリ (+OpenCV)", layout="centered")

st.title("🖼️ 画像一括リサイズ & Zip化")
st.write("OpenCVによる補正を行い、指定サイズにリサイズして一括ダウンロードします。")

# --- 設定エリア ---
st.markdown("### 1. 設定")

# サイズ選択
size_options = {
    "1200 × 628 (Webサイト・OGP等)": (1200, 628),
    "1080 × 1080 (Instagram等)": (1080, 1080),
    "600 × 400 (ブログサムネイル等)": (600, 400)
}
selected_option = st.selectbox("リサイズするサイズを選んでください", list(size_options.keys()))
target_size = size_options[selected_option]

# OpenCV処理のオプション
use_sharpen = st.checkbox("画像をくっきりさせる (OpenCV使用)", value=True, help="縮小時のぼやけを防ぐため、アンシャープマスク処理を適用します。")

# --- アップロードエリア ---
st.markdown("### 2. 画像をアップロード")
uploaded_files = st.file_uploader(
    "複数の画像を選択できます", 
    type=['png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

# --- 内部関数: OpenCV処理 ---
def process_with_opencv(pil_image):
    """
    Pillow画像をOpenCV形式に変換して処理し、Pillow形式に戻す関数
    """
    # 1. PIL -> OpenCV (NumPy配列) 変換
    # PILはRGB、OpenCVはBGRで扱うため変換が必要ですが、
    # 計算だけならRGBのままでもいける場合が多いです。ここでは一旦BGRに変換して作法通りにします。
    img_array = np.array(pil_image)
    cv_image = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    # --- ここでOpenCVの処理を行う ---
    if use_sharpen:
        # シャープネスカーネルの作成（画像をくっきりさせる）
        kernel = np.array([[0, -1, 0],
                           [-1, 5, -1],
                           [0, -1, 0]])
        cv_image = cv2.filter2D(cv_image, -1, kernel)
    # -------------------------------

    # 3. OpenCV -> PIL 変換
    cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
    return Image.fromarray(cv_image)


# --- 処理実行エリア ---
if uploaded_files:
    st.markdown("### 3. 処理結果")
    
    if st.button("リサイズしてZipを作成"):
        progress_bar = st.progress(0)
        zip_buffer = io.BytesIO()
        today_str = datetime.now().strftime('%Y%m%d')
        zip_filename = f"{today_str}.zip"

        try:
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for i, uploaded_file in enumerate(uploaded_files):
                    # 画像を開く
                    image = Image.open(uploaded_file)
                    
                    # 画像のフォーマット情報を保持
                    img_format = image.format if image.format else 'JPEG'

                    # ==========================================
                    # OpenCV処理の呼び出し
                    # ==========================================
                    if use_sharpen:
                        image = process_with_opencv(image)
                    # ==========================================
                    
                    # 中心基準でリサイズ＆トリミング (ImageOps.fit)
                    resized_image = ImageOps.fit(image, target_size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
                    
                    # メモリ保存
                    img_byte_arr = io.BytesIO()
                    resized_image.save(img_byte_arr, format=img_format)
                    
                    # Zipに追加
                    zf.writestr(uploaded_file.name, img_byte_arr.getvalue())
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))

            zip_buffer.seek(0)
            
            st.success(f"完了しました！ {len(uploaded_files)}枚の画像を処理しました。")
            
            st.download_button(
                label=f"📥 Zipファイルをダウンロード ({zip_filename})",
                data=zip_buffer,
                file_name=zip_filename,
                mime="application/zip"
            )
            
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")

else:
    st.info("画像をアップロードしてください。")