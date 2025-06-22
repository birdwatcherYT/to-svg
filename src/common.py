import cv2
import numpy as np

def contour_to_svg_path(contour, epsilon_factor=0.001):
    """OpenCVの輪郭データをSVGパス文字列に変換します（近似付き）"""
    
    # 輪郭が空でないことを確認
    if contour is None or len(contour) < 3: # 少なくとも3点必要
        return ""

    # epsilonを計算します（輪郭の周囲長に対する比率）
    perimeter = cv2.arcLength(contour, True)
    if perimeter == 0: # 周囲長が0の場合は処理しない
        return ""
    epsilon = epsilon_factor * perimeter
    
    # 輪郭を近似します
    approx_contour = cv2.approxPolyDP(contour, epsilon, True)
    
    # 近似された輪郭からパスデータを生成します
    if len(approx_contour) < 1: # 近似された輪郭が空の場合を処理します
        return ""

    path_data = f"M {approx_contour[0][0][0]},{approx_contour[0][0][1]}"
    for point in approx_contour[1:]:
        x, y = point[0]
        path_data += f" L {x},{y}"
    path_data += " Z"
    return path_data

def preprocess_image(image_path: str, background_fill_color: tuple, apply_resizing: bool, max_side_length: int):
    """
    画像を読み込み、オプションで縮小し、透明度を処理します。

    Args:
        image_path (str): 入力画像ファイルへのパス。
        background_fill_color (tuple): 透明な領域の背景色を表すRGBタプル。
        apply_resizing (bool): 処理前に画像を縮小するかどうか。
        max_side_length (int): 画像を縮小する場合の最大辺の長さ (px)。

    Returns:
        numpy.ndarray: 前処理された3チャンネルのBGR画像。
    """
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"エラー: {image_path} から画像を読み込めませんでした")
        return None

    # 画像縮小を適用
    if apply_resizing and max_side_length > 0:
        h_orig, w_orig = img.shape[:2]
        if max(h_orig, w_orig) > max_side_length:
            scaling_factor = max_side_length / max(h_orig, w_orig)
            new_w = int(w_orig * scaling_factor)
            new_h = int(h_orig * scaling_factor)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            print(f"画像を {w_orig}x{h_orig} から {new_w}x{new_h} に縮小しました。")

    # 透明なPNGのアルファチャンネルを処理します
    if img.shape[2] == 4: # 画像が4チャンネル（BGRA）の場合
        b, g, r, a = cv2.split(img) # チャンネルを分割します
        
        # 処理用の3チャンネル画像を作成します
        img_3_channel = cv2.merge((b, g, r))
        
        # 指定された背景塗りつぶし色を使用します（OpenCV用にBGRに変換）
        bg_b, bg_g, bg_r = background_fill_color # RGBタプルを展開します
        background_color_bgr = (bg_b, bg_g, bg_r) # NumPy配列用にBGRに変換します
        
        background_layer = np.full(img_3_channel.shape, background_color_bgr, dtype=np.uint8)
        
        # アルファチャンネルをブレンディング用に[0, 1]に正規化します
        alpha_normalized = a / 255.0
        alpha_normalized = cv2.merge((alpha_normalized, alpha_normalized, alpha_normalized))
        
        # 指定された背景色と画像をブレンドします
        img_processed = np.uint8(img_3_channel * alpha_normalized + background_layer * (1 - alpha_normalized))
    else: # 画像がすでに3チャンネル（BGR）の場合
        img_processed = img.copy()
    
    return img_processed
