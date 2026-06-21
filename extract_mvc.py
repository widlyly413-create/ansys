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
    """读取 CSV 文件，返回 header 和数据行"""
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return None, None
    return rows[0], rows[1:]


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
    header, data_rows = read_csv_file(mvc_path)
    if header is None:
        return existing
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

    # 加载已有 MVC 记录，用于增量判断
    existing_records = load_existing_mvc(output_path)
    new_results = []       # 本次新增的
    all_results = []       # 最终合并的全部记录

    # 先将已有记录读入 all_results
    if os.path.exists(output_path):
        header, data_rows = read_csv_file(output_path)
        if header is not None:
            subj_idx = get_column_index(header, "受试者")
            file_idx = get_column_index(header, "动作文件")
            chan_idx = get_column_index(header, "通道_肌肉")
            val_idx  = get_column_index(header, "MVC_极大值")
            if all(i != -1 for i in [subj_idx, file_idx, chan_idx, val_idx]):
                all_results = [(r[subj_idx], r[file_idx], r[chan_idx], float(r[val_idx]))
                               for r in data_rows]

    # 遍历 data_processed 下所有受试者文件夹
    for subject_dir in sorted(os.listdir(processed_root)):
        subject_path = os.path.join(processed_root, subject_dir)
        if not os.path.isdir(subject_path):
            continue

        # 查找该受试者下的"最大收缩测试"文件
        for filename in sorted(os.listdir(subject_path)):
            if "最大收缩" not in filename:
                continue

            file_path = os.path.join(subject_path, filename)
            if not os.path.isfile(file_path):
                continue

            print(f"=== MVC 文件: {subject_dir} / {filename} ===")

            header, data_rows = read_csv_file(file_path)
            if header is None:
                print(f"  文件为空，跳过")
                continue

            for col_name in CHANNEL_COLS:
                key = (subject_dir, col_name)

                # === 增量处理：已有记录则跳过 ===
                if key in existing_records:
                    # 从 all_results 中取已有值输出
                    for s, fn, ch, val in all_results:
                        if s == subject_dir and ch == col_name:
                            print(f"  ⏭ 已存在，跳过: {col_name} (MVC={val:.4f})")
                            break
                    continue

                col_idx = get_column_index(header, col_name)
                if col_idx == -1:
                    print(f"  列 {col_name} 不存在，跳过")
                    continue

                signal = np.array(
                    [float(row[col_idx]) for row in data_rows], dtype=np.float64
                )
                try:
                    mvc_value = extract_mvc_max(signal, fs=1000, window_duration=1.0)
                except ValueError as e:
                    print(f"  通道 {col_name} 提取失败: {e}")
                    continue

                new_results.append((subject_dir, filename, col_name, mvc_value))
                all_results.append((subject_dir, filename, col_name, mvc_value))
                print(f"  ✅ {col_name}: MVC = {mvc_value:.4f}")

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

    print(f"\n✅ MVC 提取完成！新增 {len(new_results)} 条，总计 {len(all_results)} 条")
    print(f"   结果已保存至: {output_path}")

    # 终端打印本次新增的汇总
    if new_results:
        print("\n--- 本次新增 ---")
        print(f"{'受试者':<16} {'通道_肌肉':<30} {'MVC_极大值':<16}")
        print("-" * 64)
        for subject, file_name, col_name, mvc in new_results:
            print(f"{subject:<16} {col_name:<30} {mvc:<16.4f}")


if __name__ == "__main__":
    main()