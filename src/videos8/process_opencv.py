import cv2
import numpy as np
import os
import sys

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 视频文件列表和对应的手语类型标签
videos = [
    ("asl_vid3.mp4", "ASL"),
    ("dsgs_vid3.mp4", "DSGS"),
    ("lsf_vid2.mp4", "LSF-CH"),
    ("lis_vid3.mp4", "LIS-CH"),
    ("lsa_vid4.mp4", "LSA"),
    ("tsl_vid2.mp4", "TSL"),
    ("ksl_vid2.mp4", "KSL"),
    ("gsl_vid3.mp4", "DGS")
]

# 当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)

print("步骤1: 读取并处理每个视频...")

# 存储每个视频的帧
video_frames = []
video_sizes = []
max_frames = 0
original_fps = None  # 将使用第一个视频的FPS

for i, (video_file, label) in enumerate(videos):
    print(f"处理 {video_file} ({i+1}/{len(videos)})...")

    cap = cv2.VideoCapture(video_file)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # 保存原始FPS（使用第一个视频的FPS）
    if original_fps is None:
        original_fps = fps

    # 读取前15秒的帧（或全部帧如果少于15秒）
    max_frame_count = min(int(fps * 15), total_frames)
    frames = []
    frame_count = 0

    print(f"  视频信息: FPS={fps:.2f}, 尺寸={width}x{height}, 总帧数={total_frames}, 时长={duration:.2f}秒")
    print(f"  将读取前 {max_frame_count} 帧 (约{max_frame_count/fps:.2f}秒)")

    while frame_count < max_frame_count:
        ret, frame = cap.read()
        if not ret:
            break

        # 保持原始尺寸，不resize
        # 添加标签（白色文字，黑色描边）
        text = label
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 3.6  # 放大3倍
        thickness = 9  # 也放大3倍

        # 获取文本尺寸
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)

        # 文本位置（底部居中）
        text_x = (width - text_width) // 2
        text_y = height - 30

        # 绘制黑色描边
        cv2.putText(frame, text, (text_x, text_y), font, font_scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
        # 绘制白色文字
        cv2.putText(frame, text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

        frames.append(frame)
        frame_count += 1

    cap.release()

    # 循环5次
    frames_looped = frames * 5
    video_frames.append(frames_looped)
    video_sizes.append((width, height))
    max_frames = max(max_frames, len(frames_looped))

    print(f"  读取了 {len(frames)} 帧，循环5次后共 {len(frames_looped)} 帧")

print(f"\n步骤1完成！最长视频: {max_frames} 帧\n")

# 确保所有视频长度一致（用最后一帧填充）
for i in range(len(video_frames)):
    while len(video_frames[i]) < max_frames:
        video_frames[i].append(video_frames[i][-1])

print("步骤2: 拼接成2x4网格...")

# 计算网格尺寸（保持原始比例）
# 第一行：视频0-3
row1_width = sum(video_sizes[i][0] for i in range(4))
row1_height = max(video_sizes[i][1] for i in range(4))

# 第二行：视频4-7
row2_width = sum(video_sizes[i][0] for i in range(4, 8))
row2_height = max(video_sizes[i][1] for i in range(4, 8))

# 网格总尺寸
grid_width = max(row1_width, row2_width)
grid_height = row1_height + row2_height

print(f"网格尺寸: {grid_width}x{grid_height}")
print(f"使用原始FPS: {original_fps}")

# 创建输出视频
output_file = "output_grid.mp4"
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_file, fourcc, original_fps, (grid_width, grid_height))

print(f"步骤3: 生成网格视频 ({max_frames} 帧)...")

# 逐帧生成网格
for frame_idx in range(max_frames):
    if frame_idx % 100 == 0:
        progress = (frame_idx / max_frames) * 100
        print(f"进度: {progress:.1f}% ({frame_idx}/{max_frames})")

    # 创建第一行（可能需要填充到相同高度）
    row1_frames = []
    for i in range(4):
        frame = video_frames[i][frame_idx]
        # 如果高度不够，底部填充黑色
        if frame.shape[0] < row1_height:
            padding = np.zeros((row1_height - frame.shape[0], frame.shape[1], 3), dtype=np.uint8)
            frame = np.vstack([frame, padding])
        row1_frames.append(frame)
    row1 = np.hstack(row1_frames)

    # 创建第二行
    row2_frames = []
    for i in range(4, 8):
        frame = video_frames[i][frame_idx]
        # 如果高度不够，底部填充黑色
        if frame.shape[0] < row2_height:
            padding = np.zeros((row2_height - frame.shape[0], frame.shape[1], 3), dtype=np.uint8)
            frame = np.vstack([frame, padding])
        row2_frames.append(frame)
    row2 = np.hstack(row2_frames)

    # 如果两行宽度不同，右侧填充黑色
    if row1.shape[1] < grid_width:
        padding = np.zeros((row1.shape[0], grid_width - row1.shape[1], 3), dtype=np.uint8)
        row1 = np.hstack([row1, padding])
    if row2.shape[1] < grid_width:
        padding = np.zeros((row2.shape[0], grid_width - row2.shape[1], 3), dtype=np.uint8)
        row2 = np.hstack([row2, padding])

    # 拼接两行
    grid = np.vstack([row1, row2])

    out.write(grid)

out.release()

print(f"\n完成！输出文件: {output_file}")
print(f"视频时长: {max_frames / original_fps:.2f} 秒 (约 {max_frames / original_fps / 60:.2f} 分钟)")
print("\n所有任务完成！")
