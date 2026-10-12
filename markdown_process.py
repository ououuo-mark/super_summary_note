import cv2
import re
import os
from pathlib import Path
from typing import Tuple, Optional

# 该页面的注释不准确,这里是把字符转化为整数,始终为秒级而非毫秒
def time_str_to_seconds(time_str: str) -> Optional[float]:
    """
    将代表毫秒的字符串转换为秒。
    例如: "449576" -> 449.576
    """
    try:
        # 将字符串直接转换为整数（秒）
        seconds = int(time_str)
        
        return float(seconds)
    except ValueError:
        # 如果字符串不是纯数字，则转换失败
        print(f"警告: 无法将 '{time_str}' 解析为有效的秒数，跳过此标记。")
        return None

def capture_frame(video_path: Path, time_in_seconds: float, output_image_path: Path, crop_coords: Optional[Tuple[int, int, int, int]] = None) -> bool:
    if not video_path.exists():
        print(f"错误: 视频文件未找到: {video_path}")
        return False

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"错误: 无法打开视频文件: {video_path}")
        return False
    fps = cap.get(cv2.CAP_PROP_FPS); fps = 30 if fps == 0 else fps
    target_frame_number = int(time_in_seconds * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_number)
    success, frame = cap.read()
    if success:
        frame_to_save = frame
        if crop_coords:
            x1, y1, x2, y2 = crop_coords
            if x1 >= x2 or y1 >= y2:
                print(f"❌ 错误: 裁剪坐标无效 ({x1},{y1},{x2},{y2})。")
                cap.release()
                return False
            print(f"✂️ 正在应用统一裁剪，区域: x={x1}-{x2}, y={y1}-{y2}")
            frame_to_save = frame[y1:y2, x1:x2]
        encode_param = [int(cv2.IMWRITE_PNG_COMPRESSION), 3]
        result, buffer = cv2.imencode('.png', frame_to_save, encode_param)
        if result:
            with open(output_image_path, 'wb') as f: f.write(buffer)
            print(f"✅ 成功截图并保存到: {output_image_path}")
        else:
            success = False
    else:
        video_duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
        print(f"❌ 警告: 无法在 {time_in_seconds:.2f} 秒处截取视频帧(视频总长 {video_duration:.2f} 秒)。")
    cap.release()
    return success


def process_markdown_file(markdown_path: Path, video_path: Path, crop_coords: Optional[Tuple[int, int, int, int]] = None, time_offset: float = 0.0):
    if not markdown_path.exists(): print(f"错误: Markdown 文件未找到: {markdown_path}"); return
    if not video_path.exists(): print(f"错误: 视频文件未找到: {video_path}"); return

    print(f"🚀 开始处理 Markdown 文件: {markdown_path.name}")
    print(f"🎬 使用视频文件: {video_path.name}")
    if crop_coords:
        print(f"➡️ 将对所有截图应用统一裁剪区域: {crop_coords}")
    if time_offset != 0:
        print(f"➡️ 将把所有截图时间点向前移动 {time_offset} 秒\n")

    # 安全地创建目录路径，先创建父目录assets，再创建子目录
    assets_parent_dir = markdown_path.parent / "assets"
    assets_parent_dir.mkdir(exist_ok=True)
    
    # 使用文件名（去掉扩展名）作为子目录名，更安全可靠
    file_name_without_ext = markdown_path.stem  # 去掉扩展名
    image_dir = assets_parent_dir / f'assets_{file_name_without_ext}'
    image_dir.mkdir(exist_ok=True)
    
    try:
        content = markdown_path.read_text(encoding='utf-8')
        pattern = re.compile(r"<time_image_start>(.*?)</end>")
        matches = list(pattern.finditer(content))

        if not matches:
            print("未在文件中找到任何 <time_image_start>...</end> 标记。")
            return

        print(f"找到了 {len(matches)} 处标记，正在处理...\n")
        
        replacements = []
        for match in matches:
            original_tag = match.group(0)
            time_str = match.group(1).strip() # time_str 现在是 "449576" 这样的字符串
            print(f"--- 正在处理标记: {original_tag} ---")
            
            time_sec = time_str_to_seconds(time_str)
            if time_sec is None: continue

            adjusted_time_sec = time_sec - time_offset
            
            if adjusted_time_sec < 0:
                print(f"⚠️ 警告: 时间戳 {time_str}ms 向前偏移 {time_offset} 秒后为负数。将从视频开头 (0秒) 处截图。")
                adjusted_time_sec = 0.0
            else:
                print(f"🕒 时间戳 {time_str}ms ({time_sec:.3f}s) 已调整为: {adjusted_time_sec:.3f}s")

            safe_filename = time_str + '.png'
            image_path = image_dir / safe_filename
            
            success = capture_frame(video_path, adjusted_time_sec, image_path, crop_coords)

            if success:
                # 使用完整的绝对路径
                # 将 Path 对象转换为绝对路径字符串，并确保路径分隔符为 '/'，以兼容 Markdown
                absolute_path_str = str(image_path.absolute()).replace('\\', '/')
                
                # 使用绝对路径创建 Markdown 图片标签
                # Alt 文本仍然使用原始的毫秒字符串，以保持与笔记源的一致性
                markdown_image_tag = f"![截图 @ {time_str}ms]({absolute_path_str})"
                replacements.append((original_tag, markdown_image_tag))
            else:
                print(f"跳过对 {original_tag} 的替换，因为截图失败。\n")

        for original, new in reversed(replacements):
            content = content.replace(original, new, 1)

        markdown_path.write_text(content, encoding='utf-8')
        print(f"\n🎉 处理完成！ {len(replacements)} 处标记已成功替换。")

    except Exception as e:
        print(f"\n处理过程中发生意外错误: {e}")

# ==============================================================================

# ==============================================================================

def markdown_process_main(markdown_path,video_pth,subject):
    if subject == "en":
        CROP_COORDINATES = (0, 0, 1370, 875)
    elif subject == "chemistry":
        CROP_COORDINATES = (0, 0, 1920, 1080)
    else:
        print("错误: 不支持的科目类型。请使用 'en' 或 'zh'。")
        return
    TIME_OFFSET_SECONDS = 0.0
    md_path_obj = Path(markdown_path)
    vid_path_obj = Path(video_pth)

    #处理 Markdown
    process_markdown_file(
        md_path_obj, 
        vid_path_obj, 
        crop_coords=CROP_COORDINATES,
        time_offset=TIME_OFFSET_SECONDS
    )

def insert_picture_main(markdown_path,video_path):
    markdown_file_str = markdown_path
    video_file_str = video_path
    # 统一裁剪坐标，如果不需要裁剪则设为 None
    # 格式: (左上角X, 左上角Y, 右下角X, 右下角Y)
    # CROP_COORDINATES = (0, 190, 1920, 1080) 
    CROP_COORDINATES = None

    # 设置截图时间提前的秒数
    # 设置为 1.0 意味着 449576ms (449.576s) 的标签会截取 448.576s 的画面
    TIME_OFFSET_SECONDS = 0.0
    
    # --- 执行代码 ---
    # Path() 会正确处理绝对路径
    md_path_obj = Path(markdown_file_str)
    vid_path_obj = Path(video_file_str)

    process_markdown_file(
        md_path_obj, 
        vid_path_obj, 
        crop_coords=CROP_COORDINATES,
        time_offset=TIME_OFFSET_SECONDS
    )


if __name__ == "__main__":
    
    markdown_file_str = r"D:\video_save\markdowns\5sa9I41c - 副本.md"
    video_file_str = r"D:\download\test_video.mp4"

    # 统一裁剪坐标，如果不需要裁剪则设为 None
    # 格式: (左上角X, 左上角Y, 右下角X, 右下角Y)
    CROP_COORDINATES = (0, 190, 1920, 1080) 
    # CROP_COORDINATES = None

    # 设置截图时间提前的秒数
    # 设置为 1.0 意味着 449576ms (449.576s) 的标签会截取 448.576s 的画面
    TIME_OFFSET_SECONDS = 1.0
    
    # --- 执行代码 ---
    # Path() 会正确处理绝对路径
    md_path_obj = Path(markdown_file_str)
    vid_path_obj = Path(video_file_str)

    process_markdown_file(
        md_path_obj, 
        vid_path_obj, 
        crop_coords=CROP_COORDINATES,
        time_offset=TIME_OFFSET_SECONDS
    )
