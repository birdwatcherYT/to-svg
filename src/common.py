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
    画像を読み込み、透明度を処理し、必要に応じてリサイズします。
    """
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"エラー: {image_path} から画像を読み込めませんでした")
        return None

    # 画像サイズ調整を適用
    if apply_resizing and max_side_length > 0:
        h_orig, w_orig = img.shape[:2]
        
        # 現在の画像の最も長い辺の長さを計算
        current_max_side = max(h_orig, w_orig)

        # 指定されたmax_side_lengthに合わせて画像をリサイズ
        # 縮小の場合も拡大の場合も同じロジックで対応
        if current_max_side != max_side_length:
            scaling_factor = max_side_length / current_max_side
            new_w = int(w_orig * scaling_factor)
            new_h = int(h_orig * scaling_factor)
            
            # 拡大の場合はcv2.INTER_LINEARまたはcv2.INTER_CUBIC、縮小の場合はcv2.INTER_AREAが適している
            # ここでは汎用的にcv2.INTER_LINEARを使用するか、
            # もしくは拡大と縮小で補間方法を切り替えることも可能
            # 今回はシンプルにINTER_LINEARを使用します。
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            print(f"画像を {w_orig}x{h_orig} から {new_w}x{new_h} にリサイズしました。")

    # 透明なPNGのアルファチャンネルを処理します
    if img.shape[2] == 4: # 画像が4チャンネル（BGRA）の場合
        b, g, r, a = cv2.split(img) # チャンネルを分割します
        
        # 処理用の3チャンネル画像を作成します
        img_3_channel = cv2.merge((b, g, r))
        
        # 指定された背景塗りつぶし色を使用します（OpenCV用にBGRに変換）
        bg_b, bg_g, bg_r = background_fill_color # RGBタプルを展開します
        background_color_bgr = (bg_r, bg_g, bg_b) # OpenCVはBGR順

        # 背景画像を作成します
        background = np.full_like(img_3_channel, background_color_bgr)
        
        # アルファチャンネルを正規化してマスクとして使用します
        alpha_normalized = a / 255.0
        alpha_3_channel = cv2.merge((alpha_normalized, alpha_normalized, alpha_normalized))
        
        # 前景と背景をブレンドします
        img_blended = (img_3_channel * alpha_3_channel).astype(np.uint8) + \
                      (background * (1 - alpha_3_channel)).astype(np.uint8)
        return img_blended
    else: # 3チャンネル画像（BGR）の場合、そのまま返します
        return img
