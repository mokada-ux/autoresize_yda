import streamlit as st
from PIL import Image, ImageOps
import io
import zipfile
from datetime import datetime
import cv2
import numpy as np
import os

# --- ページ設定 ---
st.set_page_config(page_title="画像リサイズアプリ", layout="wide")

# --- セッション状態の初期化（画像の追加・削除用） ---
if 'file_list' not in st.session_state:
    st.session_state['file_list'] = []
if 'uploader_key' not in st.session_state:
    st.session_state['uploader_key'] = 0

# --- 関数定義 ---

def add_uploaded_files():
    """アップロードされたファイルをセッション状態に追加し、アップローダーをリセットする"""
    if st.session_state.uploaded_temp:
        for uploaded_file in st.session_state.uploaded_temp:
            # 既存リストに同じファイル名がないか確認（重複回避）
            if not any(f['name'] == uploaded_file.name for f in st.session_state['file_list']):
                # 画像を開いてメモリに保持（バイトデータとして）
                img_bytes = uploaded_file.getvalue()
                st.session_state['file_list'].append({
                    'name': uploaded_file.name,
                    'data': img_bytes
                })
        # アップローダーをリセットするためにキーを更新
        st.session_state['uploader_key'] += 1

def remove_file(index):
    """指定したインデックスの画像をリストから削除"""
    st.session_state['file_list'].pop(index)

def process_with_opencv(pil_image):
    """OpenCVによるシャープネス処理"""
    # PIL -> OpenCV (BGR)
    img_array = np.array(pil_image)
    cv_image = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    # シャープネスカーネル（適度に適用）
    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]])
    cv_image = cv2.filter2D(cv_image, -1, kernel)

    # OpenCV (BGR) -> PIL
    cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
    return Image.fromarray(cv_image)

# ==========================================
# レイアウト：サイドバー（設定）
# ==========================================
with st.sidebar:
    st.header("⚙️ 設定")
    
    st.markdown("### 1. リサイズサイズ")
    SIZE_SETTINGS = {
        "1200 × 628 (Web/OGP)": {"size": (1200, 628), "prefix": "c"},
        "1080 × 1080 (Insta)": {"size": (1080, 1080), "prefix": "s"},
        "600 × 400 (Blog)": {"size": (600, 400), "prefix": "m"}
    }
    selected_option_key = st.selectbox("サイズを選択", list(SIZE_SETTINGS.keys()))
    selected_setting = SIZE_SETTINGS[selected_option_key]
    target_size = selected_setting["size"]
    file_prefix = selected_setting["prefix"]

    st.markdown("### 2. ファイル名")
    # デフォルトは空白
    start_number_input = st.text_input("開始番号 (No.)", value="", placeholder="例: 1")
    
    st.markdown("### 3. オプション")
    use_sharpen = st.checkbox("くっきり補正 (OpenCV)", value=True)

    st.divider()
    
    # 実行ボタンエリア（サイドバー下部）
    # 開始番号のバリデーション
    is_valid_number = start_number_input.isdigit()
    
    if is_valid_number and st.session_state['file_list']:
        if st.button("変換してZipを作成", type="primary", use_container_width=True):
            # --- 処理実行 ---
            start_number = int(start_number_input)
            progress_bar = st.progress(0)
            zip_buffer = io.BytesIO()
            today_str = datetime.now().strftime('%Y%m%d')
            zip_filename = f"{today_str}.zip"

            try:
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    total_files = len(st.session_state['file_list'])
                    
                    for i, file_info in enumerate(st.session_state['file_list']):
                        # 画像データの読み込み
                        image = Image.open(io.BytesIO(file_info['data']))
                        
                        # --- 強制的にRGBモードに変換（JPG保存のため必須） ---
                        # 透過PNGなどの場合、背景を白にする処理
                        if image.mode in ("RGBA", "P"):
                            image = image.convert("RGBA")
                            background = Image.new("RGB", image.size, (255, 255, 255))
                            background.paste(image, mask=image.split()[3]) # 3 is alpha channel
                            image = background
                        else:
                            image = image.convert("RGB")

                        # OpenCV処理
                        if use_sharpen:
                            image = process_with_opencv(image)
                        
                        # リサイズ (LANCZOS: 高品質リサンプリング)
                        resized_image = ImageOps.fit(image, target_size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
                        
                        # --- ファイル名生成 ---
                        current_no = start_number + i
                        new_filename = f"{file_prefix}{current_no:03d}.jpg" # 強制的にjpg

                        # --- 最高画質で保存 ---
                        img_byte_arr = io.BytesIO()
                        resized_image.save(
                            img_byte_arr, 
                            format='JPEG', 
                            quality=100,      # 最高画質 (1-100)
                            subsampling=0     # 色情報の圧縮なし（4:4:4）
                        )
                        
                        # Zipに追加
                        zf.writestr(new_filename, img_byte_arr.getvalue())
                        progress_bar.progress((i + 1) / total_files)

                zip_buffer.seek(0)
                st.success("完了しました！")
                st.download_button(
                    label=f"📥 Zipをダウンロード",
                    data=zip_buffer,
                    file_name=zip_filename,
                    mime="application/zip",
                    type="primary",
                    use_container_width=True
                )
                
            except Exception as e:
                st.error(f"エラー: {e}")
    else:
        if not st.session_state['file_list']:
            st.info("画像をアップロードしてください")
        elif not is_valid_number:
            st.warning("開始番号を入力してください（半角数字）")


# ==========================================
# メインエリア
# ==========================================
st.title("🖼️ 画像一括リサイズツール")

# --- 1. 画像アップロードエリア (上部固定) ---
st.file_uploader(
    "ここに画像をドラッグ＆ドロップ (追加アップロード可能)", 
    type=['png', 'jpg', 'jpeg', 'webp'], 
    accept_multiple_files=True,
    key=f"uploader_{st.session_state['uploader_key']}", # キーを変えることでリセットするテクニック
    on_change=add_uploaded_files, # ファイル選択時に自動でリストに追加
    key_label="uploaded_temp" # session_stateに一時保存されるキー
)

st.divider()

# --- 2. 画像リスト表示エリア (縦スクロール) ---
st.markdown(f"### 📋 アップロード済みリスト ({len(st.session_state['file_list'])}枚)")

if st.session_state['file_list']:
    # グリッド表示の作成 (サムネイル + 削除ボタン)
    for index, file_info in enumerate(st.session_state['file_list']):
        with st.container():
            col_thumb, col_name, col_del = st.columns([1, 4, 1])
            
            # 画像データの読み込み
            img = Image.open(io.BytesIO(file_info['data']))
            
            with col_thumb:
                st.image(img, use_container_width=True)
            
            with col_name:
                st.write(f"**元ファイル名:** {file_info['name']}")
                st.caption(f"サイズ: {img.width} x {img.height}")
            
            with col_del:
                # 削除ボタン: クリックするとremove_fileが呼ばれ再描画される
                if st.button("❌ 削除", key=f"del_{index}"):
                    remove_file(index)
                    st.rerun() # 即座に画面更新
            
            st.markdown("---") # 区切り線
else:
    st.info("まだ画像がありません。上部からアップロードしてください。")
