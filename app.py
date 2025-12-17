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

# --- CSSスタイル設定 (UI調整・完全固定用) ---
st.markdown("""
    <style>
    /* 1. 全体の余白を調整 */
    .block-container {
        padding-top: 0rem !important; /* 上部余白を完全削除 */
        padding-bottom: 5rem !important;
    }
    
    /* 2. 固定ヘッダーエリアの強力なスタイル設定 */
    /* data-testid="stVerticalBlock" の直下にある、fixed-header-markerを含むdivをターゲット */
    div[data-testid="stVerticalBlock"] > div:has(div.fixed-header-marker) {
        position: sticky;
        top: 2.875rem; /* ツールバーの高さ分確保 */
        
        /* 【重要】背景色の指定 */
        /* 変数が効かない場合のために、明示的にテーマの背景色（通常は白か黒）を描画させる */
        background-color: var(--background-color, #0e1117); 
        
        /* それでも透ける場合のために、背景画像を無地でセットして強制塗りつぶし */
        background-image: linear-gradient(var(--background-color), var(--background-color));
        
        /* 重なり順を最強にする */
        z-index: 999999;
        
        /* 境界線と余白 */
        padding-top: 2rem; /* 上に少し余白を持たせる */
        padding-bottom: 1.5rem;
        border-bottom: 1px solid rgba(128, 128, 128, 0.2);
        
        /* コンテナの形を整える */
        display: block;
        width: 100%;
    }

    /* 3. 要素間の隙間から透けるのを防ぐためのダメ押し設定 */
    div[data-testid="stVerticalBlock"] > div:has(div.fixed-header-marker)::before {
        content: "";
        position: absolute;
        top: 0;
        left: -100px; /* 横幅いっぱいに広げるための調整 */
        width: 200%; /* 画面幅より大きくして確実にカバー */
        height: 100%;
        background-color: var(--background-color, #0e1117);
        z-index: -1; /* コンテンツの後ろに配置 */
    }
    </style>
""", unsafe_allow_html=True)

# --- セッション状態の初期化 ---
if 'file_list' not in st.session_state:
    st.session_state['file_list'] = []
if 'uploader_key' not in st.session_state:
    st.session_state['uploader_key'] = 0

# --- 関数定義 ---

def add_uploaded_files():
    """アップロードされたファイルをセッション状態に追加し、アップローダーをリセットする"""
    current_key = f"uploader_{st.session_state['uploader_key']}"
    
    if current_key in st.session_state and st.session_state[current_key]:
        for uploaded_file in st.session_state[current_key]:
            # 重複チェック
            if not any(f['name'] == uploaded_file.name for f in st.session_state['file_list']):
                img_bytes = uploaded_file.getvalue()
                st.session_state['file_list'].append({
                    'name': uploaded_file.name,
                    'data': img_bytes
                })
        # キーを更新してアップローダーをリセット
        st.session_state['uploader_key'] += 1

def remove_file(index):
    st.session_state['file_list'].pop(index)

def process_with_opencv(pil_image):
    """OpenCVによるシャープネス処理 (必ず適用)"""
    img_array = np.array(pil_image)
    cv_image = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]])
    cv_image = cv2.filter2D(cv_image, -1, kernel)

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
    start_number_input = st.text_input("開始番号 (No.)", value="", placeholder="例: 1")
    
    st.info("※ くっきり補正が自動適用されます。")

    st.divider()
    
    # 実行ボタンエリア
    is_valid_number = start_number_input.isdigit()
    
    if is_valid_number and st.session_state['file_list']:
        if st.button("変換してZipを作成", type="primary", use_container_width=True):
            start_number = int(start_number_input)
            progress_bar = st.progress(0)
            zip_buffer = io.BytesIO()
            today_str = datetime.now().strftime('%Y%m%d')
            zip_filename = f"{today_str}.zip"

            try:
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    total_files = len(st.session_state['file_list'])
                    
                    for i, file_info in enumerate(st.session_state['file_list']):
                        image = Image.open(io.BytesIO(file_info['data']))
                        
                        # 透過処理とRGB変換
                        if image.mode in ("RGBA", "P"):
                            image = image.convert("RGBA")
                            background = Image.new("RGB", image.size, (255, 255, 255))
                            background.paste(image, mask=image.split()[3])
                            image = background
                        else:
                            image = image.convert("RGB")

                        # OpenCV処理
                        image = process_with_opencv(image)
                        
                        # リサイズ
                        resized_image = ImageOps.fit(image, target_size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
                        
                        # ファイル名生成
                        current_no = start_number + i
                        new_filename = f"{file_prefix}{current_no:03d}.jpg"

                        # 保存
                        img_byte_arr = io.BytesIO()
                        resized_image.save(
                            img_byte_arr, 
                            format='JPEG', 
                            quality=100,
                            subsampling=0
                        )
                        
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

# --- 1. 固定ヘッダーエリア ---
# このコンテナはCSSによって強力に固定・不透明化されます
with st.container():
    # CSS適用のための目印
    st.markdown('<div class="fixed-header-marker"></div>', unsafe_allow_html=True)
    
    st.title("🖼️ 画像一括リサイズツール")
    
    # アップローダー
    st.file_uploader(
        "ここに画像をドラッグ＆ドロップ (追加アップロード可能)", 
        type=['png', 'jpg', 'jpeg', 'webp'], 
        accept_multiple_files=True,
        key=f"uploader_{st.session_state['uploader_key']}", 
        on_change=add_uploaded_files
    )
    
    # リストヘッダー
    st.markdown(f"### 📋 アップロード済みリスト ({len(st.session_state['file_list'])}枚)")

# --- 2. 画像リスト表示エリア (スクロール可) ---
if st.session_state['file_list']:
    # 2列のカラムを作成
    cols = st.columns(2)
    
    for index, file_info in enumerate(st.session_state['file_list']):
        col = cols[index % 2]
        
        with col:
            with st.container(border=True):
                img = Image.open(io.BytesIO(file_info['data']))
                
                # サムネイル表示
                st.image(img, use_container_width=True)
                
                # ファイル名と削除ボタン
                st.caption(f"{file_info['name']} ({img.width}x{img.height})")
                if st.button("❌ 削除", key=f"del_{index}", use_container_width=True):
                    remove_file(index)
                    st.rerun()

else:
    # リストがない場合の余白調整
    st.markdown("")
