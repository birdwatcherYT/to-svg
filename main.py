import argparse
import os
import src.convert as convert


def run_conversion(
    input_path,
    output_path,
    num_colors,
    apply_sharpening,
    median_blur_ksize,
    dilate_iterations,
    epsilon_factor,
    bg_color,
    apply_resizing,
    max_side_length,
    gaussian_blur_ksize,
    add_stroke,
    stroke_color,
    stroke_width,
):
    """
    画像をSVGに変換する処理を実行する関数。
    """
    # outputのデフォルト値を設定
    if output_path is None:
        base_name, _ = os.path.splitext(input_path)
        output_path = f"{base_name}.svg"

    # 背景色の解析
    try:
        r, g, b = map(int, bg_color.split(","))
        background_fill_color = (r, g, b)
    except ValueError:
        print(f"エラー: 無効な背景色形式 '{bg_color}'。'R,G,B'形式を使用してください。")
        return False
    
    # ストローク色の解析
    stroke_color_rgb = None
    if add_stroke:
        try:
            sr, sg, sb = map(int, stroke_color.split(","))
            stroke_color_rgb = (sr, sg, sb)
        except ValueError:
            print(f"エラー: 無効なストローク色形式 '{stroke_color}'。'R,G,B'形式を使用してください。")
            return False

    if not os.path.exists(input_path):
        print(f"エラー: 入力画像ファイル '{input_path}' が見つかりません。")
        return False

    # median_blur_ksizeが偶数で0でない場合は奇数に調整
    if median_blur_ksize % 2 == 0 and median_blur_ksize != 0:
        median_blur_ksize += 1
        print(
            f"警告: median_blur_ksizeは奇数である必要があります。{median_blur_ksize} に調整しました。"
        )
    
    # gaussian_blur_ksizeが偶数で0でない場合は奇数に調整
    if gaussian_blur_ksize % 2 == 0 and gaussian_blur_ksize != 0:
        gaussian_blur_ksize += 1
        print(
            f"警告: gaussian_blur_ksizeは奇数である必要があります。{gaussian_blur_ksize} に調整しました。"
        )


    print(f"画像処理で '{input_path}' を '{output_path}' に変換しています...")
    convert.png_color_to_svg_high_fidelity(
        image_path=input_path,
        output_path=output_path,
        num_colors=num_colors,
        epsilon_factor=epsilon_factor,
        background_fill_color=background_fill_color,
        apply_sharpening=apply_sharpening,
        median_blur_ksize=median_blur_ksize,
        dilate_iterations=dilate_iterations,
        apply_resizing=apply_resizing,
        max_side_length=max_side_length,
        gaussian_blur_ksize=gaussian_blur_ksize,
        add_stroke=add_stroke,
        stroke_color=stroke_color_rgb,
        stroke_width=stroke_width,
    )
    return True


def main():
    parser = argparse.ArgumentParser(
        description="画像をSVGに変換します。画像処理を使用します。"
    )
    parser.add_argument("input", help="入力画像ファイルへのパス (例: test.png)")
    parser.add_argument(
        "--output",
        help="出力SVGファイルへのパス (デフォルト: 入力ファイルの拡張子を.svgに変更したもの)",
    )

    parser.add_argument(
        "--num_colors",
        type=int,
        default=16,
        help="画像を量子化する色の数 (デフォルト: 16)",
    )
    parser.add_argument(
        "--apply_sharpening", action="store_true", help="シャープニングを適用します。"
    )
    parser.add_argument(
        "--median_blur_ksize",
        type=int,
        default=5,
        help="メディアンブラーのカーネルサイズを指定します (奇数のみ)。0に設定するとブラーを適用しません。 (デフォルト: 5)",
    )
    parser.add_argument(
        "--gaussian_blur_ksize",
        type=int,
        default=0,
        help="ガウシアンブラーのカーネルサイズを指定します (奇数のみ)。0に設定するとブラーを適用しません。 (デフォルト: 0)",
    )
    parser.add_argument(
        "--dilate_iterations",
        type=int,
        default=1,
        help="輪郭抽出前の膨張処理の繰り返し回数を指定します。 (デフォルト: 1)",
    )

    # 共通オプション
    parser.add_argument(
        "--epsilon_factor",
        type=float,
        default=0.001,
        help="輪郭近似のための係数。値が大きいほど頂点数が減り、ファイルサイズが小さくなりますが、形状の忠実度は低下します (デフォルト: 0.001)",
    )
    parser.add_argument(
        "--bg_color",
        type=str,
        default="255,255,255",
        help="透明な領域の背景色をRGB形式で指定します ('R,G,B') (デフォルト: '255,255,255')",
    )

    # 画像サイズ調整オプションを更新
    parser.add_argument(
        "--apply_resizing", action="store_true", help="処理前に画像のサイズを調整します。"
    )
    parser.add_argument(
        "--max_side_length",
        type=int,
        default=1024,
        help="調整後の画像の最も長い辺の最大ピクセル数を指定します。アスペクト比は維持されます。(デフォルト: 1024) 縮小・拡大が可能です。",
    )
    parser.add_argument(
        "--add_stroke", action="store_true", help="SVGパスにアウトラインを追加します。"
    )
    parser.add_argument(
        "--stroke_color",
        type=str,
        default="0,0,0",
        help="ストロークの色をRGB形式で指定します ('R,G,B') (デフォルト: '0,0,0')",
    )
    parser.add_argument(
        "--stroke_width",
        type=float,
        default=1.0,
        help="ストロークの太さを指定します (デフォルト: 1.0)",
    )

    args = parser.parse_args()
    run_conversion(
        args.input,
        args.output,
        args.num_colors,
        args.apply_sharpening,
        args.median_blur_ksize,
        args.dilate_iterations,
        args.epsilon_factor,
        args.bg_color,
        args.apply_resizing,
        args.max_side_length,
        args.gaussian_blur_ksize,
        args.add_stroke,
        args.stroke_color,
        args.stroke_width,
    )


if __name__ == "__main__":
    main()