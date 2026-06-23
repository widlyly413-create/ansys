import numpy as np
import os
import csv

# ========== 通道-肌肉映射（与 batch_preprocess.py 保持一致） ==========

CHANNEL_COLS = [
    "Channel 1_三角肌前束",
    "Channel 2_胸锁乳突肌",
    "Channel 3_斜方肌",
    "Channel 4_竖脊肌",
]


# ========== MVC 提取函数 ==========

def extract_mvc_max(rectified_mvc_signal, fs=1000, window_duration=1.0):
    """
    提取单通道的 MVC 极大值

    :param rectified_mvc_signal: 已经过预处理和全波整流的单通道 MVC 信号 (1D array)
    :param fs: 采样率，默认 1000 Hz
    :param window_duration: 滑动窗口时间长度，标准为 1.0 秒
    :return: 该通道的 MVC 极大值 (分母)
    """
    window_size = int(window_duration * fs)
    if len(rectified_mvc_signal) < window_size:
        raise ValueError("MVC信号长度小于定义的滑动窗口长度，请检查数据！")

    # 移动平均平滑：卷积计算滑动窗口均值
    window = np.ones(window_size) / window_size
    smoothed_signal = np.convolve(rectified_mvc_signal, window, mode='valid')

    mvc_max_value = np.max(smoothed_signal)
    return mvc_max_value


def read_csv_file(filepath):
    """
    读取 CSV 文件，返回 (header, data)
      - header: 列名列表
      - data: numpy 2D array (n_rows x n_cols)，不含表头行
    使用 numpy.loadtxt 加速大文件读取。
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            header_line = f.readline()
            if not header_line:
                return None, None
            header = header_line.strip().split(',')

        # Windows 需显式指定 encoding='utf-8'，否则默认 gbk 解码失败
        data = np.loadtxt(filepath, delimiter=',', skiprows=1,
                          dtype=np.float64, encoding='utf-8')
    except (UnicodeDecodeError, ValueError, OSError) as e:
        print(f"    ⚠ 文件读取失败: {e}")
        return None, None

    if data.ndim == 0 or data.size == 0:
        return None, None
    if data.ndim == 1:
        data = data.reshape(-1, 1)

    return header, data


def get_column_index(header, col_name):
    """获取列索引"""
    for i, h in enumerate(header):
        if h.strip() == col_name:
            return i
    return -1


# ========== 主程序 ==========

def load_existing_mvc(mvc_path):
    """读取已有的 MVC_values.csv，返回已记录的 (subject, channel_col) 集合"""
    existing = set()
    if not os.path.exists(mvc_path):
        return existing
    try:
        with open(mvc_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
    except (UnicodeDecodeError, OSError):
        return existing
    if not rows:
        return existing
    header = rows[0]
    data_rows = rows[1:]
    subj_idx = get_column_index(header, "受试者")
    chan_idx = get_column_index(header, "通道_肌肉")
    if subj_idx == -1 or chan_idx == -1:
        return existing
    for row in data_rows:
        existing.add((row[subj_idx].strip(), row[chan_idx].strip()))
    return existing


def main():
    processed_root = r"e:\Coding_projects\SEMG_ANSYS\data_processed"
    output_path = r"e:\Coding_projects\SEMG_ANSYS\MVC_values.csv"

    all_results = []  # 最终结果: (subject, best_file, channel, mvc_value)

    # 遍历 data_processed 下所有受试者文件夹
    for subject_dir in sorted(os.listdir(processed_root)):
        subject_path = os.path.join(processed_root, subject_dir)
        if not os.path.isdir(subject_path):
            # 跳过预测试子目录（但保留 pretest 目录本身是文件夹，需要排除）
            continue

        # 查找该受试者下的所有"最大收缩测试"文件
        mvc_files = []
        for filename in sorted(os.listdir(subject_path)):
            if "最大收缩" not in filename:
                continue
            file_path = os.path.join(subject_path, filename)
            # 跳过子目录（如"预测试"文件夹）
            if os.path.isfile(file_path):
                mvc_files.append(filename)

        if not mvc_files:
            print(f"=== {subject_dir}: 未找到最大收缩文件，跳过 ===")
            continue

        print(f"=== 受试者: {subject_dir} (找到 {len(mvc_files)} 个 MVC 文件) ===")
        for mf in mvc_files:
            print(f"      - {mf}")

        # 对每个通道，遍历所有 MVC 文件，取全局最大值
        for col_name in CHANNEL_COLS:
            best_mvc = -1.0
            best_file = None

            for mvc_file in mvc_files:
                file_path = os.path.join(subject_path, mvc_file)
                header, data_rows = read_csv_file(file_path)
                if header is None:
                    print(f"    ⚠ {mvc_file} 为空，跳过")
                    continue

                col_idx = get_column_index(header, col_name)
                if col_idx == -1:
                    print(f"    ⚠ {mvc_file} 缺少列 {col_name}，跳过")
                    continue

                signal = data_rows[:, col_idx]
                try:
                    mvc_value = extract_mvc_max(signal, fs=1000, window_duration=1.0)
                except ValueError as e:
                    print(f"    ⚠ {col_name} 在 {mvc_file} 中提取失败: {e}")
                    continue

                print(f"      {col_name}: {mvc_file} → MVC = {mvc_value:.4f}")

                if mvc_value > best_mvc:
                    best_mvc = mvc_value
                    best_file = mvc_file

            if best_mvc > 0:
                all_results.append((subject_dir, best_file, col_name, best_mvc))
                print(f"  ✅ {col_name}: MVC = {best_mvc:.4f} (来自 {best_file})")
            else:
                print(f"  ❌ {col_name}: 所有文件均无法提取 MVC")

    # ========== 输出汇总文件 ==========
    if not all_results:
        print("未找到任何 MVC 数据，请检查 data_processed 目录。")
        return

    output_header = ["受试者", "动作文件", "通道_肌肉", "MVC_极大值"]
    output_rows = [
        [subject, file_name, col_name, f"{mvc:.6f}"]
        for subject, file_name, col_name, mvc in all_results
    ]

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(output_header)
        writer.writerows(output_rows)

    print(f"\n✅ MVC 提取完成！共处理 {len(all_results)} 条记录")
    print(f"   结果已保存至: {output_path}")

    # 终端打印汇总
    print("\n--- MVC 汇总 ---")
    print(f"{'受试者':<16} {'来源文件':<36} {'通道_肌肉':<30} {'MVC_极大值':<16}")
    print("-" * 100)
    for subject, file_name, col_name, mvc in all_results:
        print(f"{subject:<16} {file_name:<36} {col_name:<30} {mvc:<16.4f}")


if __name__ == "__main__":
    main()