import streamlit as st
import os
import tempfile
import shutil
from main import run_conversion  # main.pyからrun_conversion関数をインポート

st.set_page_config(layout="wide", page_title="画像SVG変換ツール")

# --- Streamlit Session Stateの初期化 ---
if "median_blur_ksize_value" not in st.session_state:
    st.session_state.median_blur_ksize_value = 5
if "gaussian_blur_ksize_value" not in st.session_state:
    st.session_state.gaussian_blur_ksize_value = 0

# スライダーのキーも初期化する
if "ksize_slider_median_blur" not in st.session_state:
    st.session_state.ksize_slider_median_blur = 5
if "ksize_slider_gaussian_blur" not in st.session_state:
    st.session_state.ksize_slider_gaussian_blur = 0

if "uploaded_file_data" not in st.session_state:
    st.session_state.uploaded_file_data = None
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None

if "converted_svg_content" not in st.session_state:
    st.session_state.converted_svg_content = None
if "converted_svg_name" not in st.session_state:
    st.session_state.converted_svg_name = None


def adjust_ksize(key_suffix):
    """
    Streamlitスライダーのコールバック関数。
    カーネルサイズが偶数（ただし0ではない）の場合、自動的に奇数に調整します。
    """
    # 修正: セッションステートのキーをスライダーのキーと一致させる
    # 'key_suffix'がそのままスライダーのキー名として使われるように調整
    slider_key = f"ksize_slider_{key_suffix}"
    current_value = st.session_state[slider_key]

    if current_value != 0 and current_value % 2 == 0:
        if current_value + 1 <= 21: # 最大値21に合わせて調整
            st.session_state[slider_key] = current_value + 1
        else: # 21を超えた場合は1つ減らす
            st.session_state[slider_key] = current_value - 1
    # _value ではなく、直接スライダーのセッションステートを更新
    # ここでの `_value` サフィックスは削除し、直接スライダーの値を参照するようにする
    # スライダーのvalue引数にセッションステートの値を直接渡すことで、コールバック関数で設定された値がスライダーに反映される
    # adjust_ksize関数はスライダーの値を直接更新し、その値がスライダーの表示に反映されるようになる
    if key_suffix == "median_blur":
        st.session_state.median_blur_ksize_value = st.session_state[slider_key]
    elif key_suffix == "gaussian_blur":
        st.session_state.gaussian_blur_ksize_value = st.session_state[slider_key]


st.title("画像をSVGに変換 🎨")

st.write(
    """
このツールは、入力画像ファイルからSVG形式を生成します。色量子化と輪郭抽出に基づいた画像処理を使用します。
"""
)

# --- ファイルアップロード ---
st.header("1. 画像のアップロード")
uploaded_file_widget = st.file_uploader(
    "PNGまたはJPG画像を選択してください", type=["png", "jpg", "jpeg"]
)

if uploaded_file_widget is not None:
    if st.session_state.uploaded_file_name != uploaded_file_widget.name or (
        uploaded_file_widget.getvalue()
        and st.session_state.uploaded_file_data != uploaded_file_widget.getvalue()
    ):
        st.session_state.uploaded_file_data = uploaded_file_widget.getvalue()
        st.session_state.uploaded_file_name = uploaded_file_widget.name
        st.success(f"ファイル '{uploaded_file_widget.name}' がアップロードされました。")
        st.session_state.converted_svg_content = None
        st.session_state.converted_svg_name = None
else:
    if st.session_state.uploaded_file_data is not None and uploaded_file_widget is None:
        st.session_state.uploaded_file_data = None
        st.session_state.uploaded_file_name = None
        st.session_state.converted_svg_content = None
        st.session_state.converted_svg_name = None
        st.info("アップロードされた画像がクリアされました。")

if st.session_state.uploaded_file_data is not None:
    st.image(
        st.session_state.uploaded_file_data,
        caption="アップロードされた画像",
        use_container_width=True,
    )
else:
    st.info("画像をアップロードして開始してください。")


# --- 変換オプション ---
st.header("2. 変換オプション")
st.write(
    "このツールは、色量子化と輪郭抽出に基づいた画像処理を使用してSVGを生成します。"
)


# --- 共通オプション ---
epsilon_factor = st.slider(
    "輪郭近似のための係数 (epsilon_factor)",
    min_value=0.0001,
    max_value=0.01,
    value=0.001,
    step=0.0001,
    format="%.4f",
    help="値が大きいほど頂点数が減り、ファイルサイズが小さくなりますが、形状の忠実度は低下します。",
)

selected_color_rgb_tuple = st.color_picker(
    "透明な領域の背景色",
    value="#FFFFFF",
    help="透明な領域を埋める色を選択してください。",
)
bg_color_r = int(selected_color_rgb_tuple[1:3], 16)
bg_color_g = int(selected_color_rgb_tuple[3:5], 16)
bg_color_b = int(selected_color_rgb_tuple[5:7], 16)
bg_color_str = f"{bg_color_r},{bg_color_g},{bg_color_b}"

st.markdown("---")
st.subheader("画像サイズ調整オプション")
apply_resizing = st.checkbox(
    "画像サイズを調整",
    value=False,
    help="処理前に画像のサイズを変更します。これによりファイルサイズや処理時間に影響します。",
)
max_side_length = 0
if apply_resizing:
    max_side_length = st.slider(
        "最大辺の長さ (px)",
        min_value=32, # 最小値を小さくして拡大も可能に
        max_value=4096, # 最大値を大きくして拡大も可能に
        value=1024,
        step=64,
        help="調整後の画像の最も長い辺の最大ピクセル数を指定します。アスペクト比は維持されます。",
    )


# --- 画像処理オプション ---
st.header("3. 画像処理オプション")
num_colors = st.slider(
    "画像を量子化する色の数",
    min_value=2,
    max_value=128,
    value=16,
    step=1,
    help="色の数を減らすとSVGが単純化されますが、元の画像の情報が失われる可能性があります。",
)

st.markdown("---")
st.subheader("イラスト化のための追加オプション")

apply_sharpening = st.checkbox(
    "シャープニングを適用", value=False, help="輪郭を強調し、より鮮明な線にします。"
)

# メディアンブラー
# スライダーの `value` 引数に直接セッションステートの `ksize_slider_median_blur` を渡す
st.slider(
    "メディアンブラーのカーネルサイズ (奇数のみ、または0でブラーなし)",
    min_value=0,
    max_value=21,
    value=st.session_state.ksize_slider_median_blur,
    step=1,
    key="ksize_slider_median_blur",
    on_change=lambda: adjust_ksize("median_blur"),
    help="ノイズ除去と平滑化の強度を調整します。値を大きくするとより滑らかになります。0に設定するとブラーを適用しません。偶数値が選択された場合、自動的に奇数値に調整されます。",
)
median_blur_ksize = st.session_state.ksize_slider_median_blur # 更新された値を反映

# ガウシアンブラー
# スライダーの `value` 引数に直接セッションステートの `ksize_slider_gaussian_blur` を渡す
st.slider(
    "ガウシアンブラーのカーネルサイズ (奇数のみ、または0でブラーなし)",
    min_value=0,
    max_value=21,
    value=st.session_state.ksize_slider_gaussian_blur,
    step=1,
    key="ksize_slider_gaussian_blur",
    on_change=lambda: adjust_ksize("gaussian_blur"),
    help="画像を滑らかにする強度を調整します。値を大きくするとより滑らかになります。0に設定するとブラーを適用しません。偶数値が選択された場合、自動的に奇数値に調整されます。",
)
gaussian_blur_ksize = st.session_state.ksize_slider_gaussian_blur # 更新された値を反映


dilate_iterations = st.slider(
    "輪郭膨張の繰り返し回数",
    min_value=0,
    max_value=5,
    value=1,
    step=1,
    help="輪郭を検出する前にマスクを膨張させる回数。線を太くしたり、途切れた部分を繋げたりするのに役立ちます。0は膨張なし。",
)

add_stroke = st.checkbox(
    "ストローク（線）を追加", value=False, help="生成されるSVGパスにアウトラインを追加します。"
)

stroke_color_str = "0,0,0" # デフォルトは黒
stroke_width = 1.0
if add_stroke:
    selected_stroke_color_rgb_tuple = st.color_picker(
        "ストロークの色",
        value="#000000",
        help="ストロークの色を選択してください。",
    )
    s_color_r = int(selected_stroke_color_rgb_tuple[1:3], 16)
    s_color_g = int(selected_stroke_color_rgb_tuple[3:5], 16)
    s_color_b = int(selected_stroke_color_rgb_tuple[5:7], 16)
    stroke_color_str = f"{s_color_r},{s_color_g},{s_color_b}"

    stroke_width = st.slider(
        "ストロークの太さ",
        min_value=0.1,
        max_value=5.0,
        value=1.0,
        step=0.1,
        help="ストロークの太さを指定します。",
    )


# --- 変換実行ボタン ---
st.header("4. SVG変換")
if st.session_state.uploaded_file_data is not None:
    if st.button("SVGに変換"):
        temp_dir = tempfile.mkdtemp()
        input_image_path = os.path.join(temp_dir, st.session_state.uploaded_file_name)

        with open(input_image_path, "wb") as f:
            f.write(st.session_state.uploaded_file_data)

        output_svg_name = (
            os.path.splitext(st.session_state.uploaded_file_name)[0] + ".svg"
        )
        output_svg_path = os.path.join(temp_dir, output_svg_name)

        # Spinner added here
        with st.spinner("SVG変換中です...しばらくお待ちください。"):
            try:
                success = run_conversion(
                    input_image_path,
                    output_svg_path,
                    num_colors,
                    apply_sharpening,
                    median_blur_ksize,
                    dilate_iterations,
                    epsilon_factor,
                    bg_color_str,
                    apply_resizing,
                    max_side_length,
                    gaussian_blur_ksize,
                    add_stroke,
                    stroke_color_str,
                    stroke_width,
                )

                if success:
                    st.success("SVG変換が完了しました！")

                    if os.path.exists(output_svg_path):
                        with open(output_svg_path, "rb") as f:
                            svg_content_bytes = f.read()

                        with open(output_svg_path, "r") as f:
                            svg_content_str = f.read()

                        st.session_state.converted_svg_content = svg_content_str
                        st.session_state.converted_svg_name = output_svg_name
                        st.session_state.converted_svg_bytes = svg_content_bytes

                    else:
                        st.error(
                            "出力SVGファイルが見つかりません。変換に失敗した可能性があります。"
                        )
                else:
                    st.error(
                        "SVG変換中にエラーが発生しました。詳細はコンソール出力を確認してください。"
                    )

            except Exception as e:
                st.error(f"予期せぬエラーが発生しました: {e}")
            finally:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    st.info(f"一時ディレクトリ '{temp_dir}' をクリーンアップしました。")
else:
    st.warning("SVGに変換するには、まず画像をアップロードしてください。")

# --- 変換結果の表示 ---
if st.session_state.converted_svg_content is not None:
    st.header("5. 変換結果")
    st.download_button(
        label="SVGファイルをダウンロード",
        data=st.session_state.converted_svg_bytes,
        file_name=st.session_state.converted_svg_name,
        mime="image/svg+xml",
    )

    st.subheader("SVGプレビュー")
    st.markdown(f"```html\n{st.session_state.converted_svg_content[:500]}...\n```")
    st.components.v1.html(
        st.session_state.converted_svg_content, height=400, scrolling=True
    )


st.markdown("---")
st.markdown("Powered by Streamlit and OpenCV")