import cv2
import numpy as np
import svgwrite
from .common import contour_to_svg_path, preprocess_image


def png_color_to_svg_high_fidelity(
    image_path,
    output_path,
    num_colors=16,
    epsilon_factor=0.001,
    background_fill_color=(255, 255, 255),
    apply_sharpening=False,
    median_blur_ksize=5,
    dilate_iterations=1,
    apply_resizing=False,
    max_side_length=1024,
):
    """
    カラーPNGを高精細なSVGに<path>要素を使用して変換します。
    画像の前処理（ノイズ除去など）を追加し、透明度を処理します。

    Args:
        image_path (str): 入力PNG画像へのパス。
        output_path (str): 出力SVGファイルを保存するパス。
        num_colors (int): 画像を量子化する色の数。
        epsilon_factor (float): 輪郭近似のための係数。
        background_fill_color (tuple): 透明な領域の背景色を表すRGBタプル
                                      (0-255, 0-255, 0-255)。
                                      デフォルトは白 (255, 255, 255)。
        apply_sharpening (bool): シャープニングを適用するかどうか。
        median_blur_ksize (int): メディアンブラーのカーネルサイズ。
        dilate_iterations (int): 輪郭抽出前の膨張処理の繰り返し回数。
        apply_resizing (bool): 処理前に画像を縮小するかどうか。
        max_side_length (int): 画像を縮小する場合の最大辺の長さ (px)。
    """

    # --- ステップ1: 画像の読み込みと前処理 ---
    img_processed = preprocess_image(
        image_path, background_fill_color, apply_resizing, max_side_length
    )
    if img_processed is None:
        return

    # ノイズ除去のためにメディアンブラーを適用します
    if median_blur_ksize > 0:  # median_blur_ksizeが0の場合、ブラーを適用しない
        img_processed = cv2.medianBlur(img_processed, median_blur_ksize)

    # シャープニングを適用
    if apply_sharpening:
        # シャープニングカーネル (例: アンシャープマスクの簡略版)
        sharpening_kernel = np.array(
            [[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32
        )
        img_processed = cv2.filter2D(img_processed, -1, sharpening_kernel)

    # 色の量子化のために処理済みの画像を使用します
    pixels = img_processed.reshape((-1, 3))
    pixels = np.float32(pixels)

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1.0)
    _, labels, centers = cv2.kmeans(
        pixels, num_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
    )
    centers = np.uint8(centers)
    quantized_img = centers[labels.flatten()].reshape((img_processed.shape))

    # --- ステップ2: 各色の輪郭を抽出します ---
    all_paths = []
    kernel = np.ones((3, 3), np.uint8)  # 3x3の正方形カーネル

    for color in centers:
        # 量子化された画像内の現在の色のマスクを作成します
        mask = cv2.inRange(quantized_img, color, color)

        # 連結成分を確保し、エッジを滑らかにするためにマスクを膨張させます
        # dilate_iterationsが0の場合、膨張を適用しない
        if dilate_iterations > 0:
            mask_dilated = cv2.dilate(mask, kernel, iterations=dilate_iterations)
        else:
            mask_dilated = mask.copy()

        # 膨張したマスクを使用して輪郭を見つけます
        # 近似はcontour_to_svg_pathで行われるため、cv2.CHAIN_APPROX_NONEを使用します
        contours, _ = cv2.findContours(
            mask_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
        )

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 50:  # ノイズ除去（小さい輪郭は無視します）
                continue

            # 輪郭をSVGパスデータに変換します（epsilon_factorを渡します）
            path_data = contour_to_svg_path(contour, epsilon_factor=epsilon_factor)
            if (
                not path_data
            ):  # path_dataが空の場合（例：空の近似輪郭から）はスキップします
                continue

            # 色の情報を取得します（BGRからRGBへ）
            b, g, r = color

            all_paths.append(
                {
                    "area": area,
                    "path_data": path_data,
                    "color": svgwrite.rgb(r, g, b, "RGB"),
                }
            )

    # --- ステップ3: SVGを生成します ---
    # パスを面積でソートします（大きい面積が最初に来るように、描画順序を考慮）
    all_paths.sort(key=lambda p: p["area"], reverse=True)

    # 元の画像（または透明度処理後の処理済み画像）の寸法を使用します
    h, w, _ = img_processed.shape
    dwg = svgwrite.Drawing(output_path, profile="full", size=(w, h))

    for item in all_paths:
        dwg.add(dwg.path(d=item["path_data"], fill=item["color"], stroke="none"))

    dwg.save()
    print(f"高精細SVGファイルが {output_path} に正常に作成されました")
