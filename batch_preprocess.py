import numpy as np
import os
import csv
from scipy.signal import butter, filtfilt, iirnotch

# ========== 预处理函数 ==========

def butter_bandpass_filter(data, lowcut=20, highcut=450, fs=1000, order=4):
    """20-450Hz 带通滤波"""
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    y = filtfilt(b, a, data)
    return y


def notch_filter(data, cutoff=50, Q=30, fs=1000):
    """50Hz 陷波滤波，消除工频干扰"""
    nyq = 0.5 * fs
    w0 = cutoff / nyq
    b, a = iirnotch(w0, Q)
    y = filtfilt(b, a, data)
    return y


def preprocess_semg(raw_data, fs=1000):
    """
    sEMG 预处理流水线
    raw_data : 1-D array, 单通道原始信号
    fs       : 采样频率 (Hz)
    
    步骤:
      1. 去直流
      2. 20-450Hz 带通滤波
      3. 50Hz 陷波
      4. 全波整流
    """
    # 1. 去直流
    step1 = raw_data - np.mean(raw_data)
    # 2. 20-450Hz 带通滤波
    step2 = butter_bandpass_filter(step1, lowcut=20, highcut=450, fs=fs, order=4)
    # 3. 50Hz 陷波
    step3 = notch_filter(step2, cutoff=50, Q=30, fs=fs)
    # 4. 全波整流
    rectified = np.abs(step3)
    return rectified


# ========== 通道-肌肉映射 ==========

CHANNEL_MUSCLE_MAP = {
    1: "三角肌前束",
    2: "胸锁乳突肌",
    3: "斜方肌",
    4: "竖脊肌",
}


def read_csv_file(filepath):
    """读取无扩展名的 CSV 文件，返回 header 列表和数据行（列表的列表）"""
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return None, None
    header = rows[0]
    data_rows = rows[1:]
    return header, data_rows


def write_csv_file(filepath, header, data_rows):
    """将数据写入 CSV 文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data_rows)


def get_column_index(header, col_name):
    """获取列名在 header 中的索引，不存在则返回 -1"""
    for i, h in enumerate(header):
        if h.strip() == col_name:
            return i
    return -1


def extract_column(data_rows, col_idx):
    """提取某一列的所有数据为 float 数组"""
    return np.array([float(row[col_idx]) for row in data_rows], dtype=np.float64)


# ========== 批量处理主程序 ==========

def main():
    data_root = r"e:\Coding_projects\SEMG_ANSYS\data_raw"
    output_root = r"e:\Coding_projects\SEMG_ANSYS\data_processed"

    processed_count = 0
    skipped_count = 0

    # 遍历 data_raw 下所有受试者文件夹
    for subject_dir in sorted(os.listdir(data_root)):
        subject_path = os.path.join(data_root, subject_dir)
        if not os.path.isdir(subject_path):
            continue

        print(f"=== 处理受试者: {subject_dir} ===")

        # 遍历该受试者所有动作文件
        for filename in sorted(os.listdir(subject_path)):
            file_path = os.path.join(subject_path, filename)
            if not os.path.isfile(file_path):
                continue

            output_path = os.path.join(output_root, subject_dir, filename)

            # === 增量处理：输出已存在则跳过 ===
            if os.path.exists(output_path):
                print(f"  ⏭ 已存在，跳过: {filename}")
                skipped_count += 1
                continue

            print(f"  处理文件: {filename}")

            # 读取 CSV
            header, data_rows = read_csv_file(file_path)
            if header is None:
                print(f"    文件为空，跳过")
                continue

            # 检查通道 1-4 是否存在
            required_cols = [f"Channel {i}" for i in range(1, 5)]
            col_indices = {}
            for col_name in required_cols:
                idx = get_column_index(header, col_name)
                if idx == -1:
                    print(f"    缺少列: {col_name}，跳过")
                    break
                col_indices[col_name] = idx
            else:
                # 所有通道都存在，继续处理
                pass
            if len(col_indices) < 4:
                continue

            # 逐通道预处理
            processed_cols = {}
            for ch_idx in range(1, 5):
                col_name = f"Channel {ch_idx}"
                raw_signal = extract_column(data_rows, col_indices[col_name])
                processed_signal = preprocess_semg(raw_signal, fs=1000)
                muscle_name = CHANNEL_MUSCLE_MAP[ch_idx]
                new_col_name = f"{col_name}_{muscle_name}"
                processed_cols[new_col_name] = processed_signal

            # 构建输出 header
            output_header = []
            # 保留 timestamp 列（如果存在）
            ts_idx = get_column_index(header, "timestamp")
            if ts_idx != -1:
                output_header.append("timestamp")

            for ch_idx in range(1, 5):
                col_name = f"Channel {ch_idx}"
                muscle_name = CHANNEL_MUSCLE_MAP[ch_idx]
                output_header.append(f"{col_name}_{muscle_name}")

            # 构建输出数据行
            output_rows = []
            n_samples = len(data_rows)
            for i in range(n_samples):
                row = []
                if ts_idx != -1:
                    row.append(data_rows[i][ts_idx])
                for ch_idx in range(1, 5):
                    col_name = f"Channel {ch_idx}"
                    new_col_name = f"{col_name}_{CHANNEL_MUSCLE_MAP[ch_idx]}"
                    # 保留 6 位小数
                    row.append(f"{processed_cols[new_col_name][i]:.6f}")
                output_rows.append(row)

            # 保存
            output_path = os.path.join(output_root, subject_dir, filename)
            write_csv_file(output_path, output_header, output_rows)
            processed_count += 1
            print(f"    已保存 -> {output_path}")

    print(f"\n✅ 预处理完成！新增 {processed_count} 个，跳过 {skipped_count} 个（已存在）")


if __name__ == "__main__":
    main()