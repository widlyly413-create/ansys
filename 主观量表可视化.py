import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import sys

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

EXCEL_PATH = r'D:\Gemini_Projects\ansys\主观量表记录.xlsx'
OUTPUT_DIR = r'D:\Gemini_Projects\ansys\figures'
LOG_PATH = r'D:\Gemini_Projects\ansys\_chart_log.txt'
os.makedirs(OUTPUT_DIR, exist_ok=True)

BODY_PARTS = ['颈部', '肩部', '躯干', '腰部', '大臂前伸', '动线连贯性', '长时间工作', '操作稳定性']
CHOICE_LABELS = {
    1: '极度倾向(A)',
    2: '略倾向(A)',
    3: '两者无区别',
    4: '略倾向(B)',
    5: '极度倾向(B)',
}
CHOICE_COLORS = {
    1: '#E74C3C',
    2: '#F39C12',
    3: '#95A5A6',
    4: '#3498DB',
    5: '#2ECC71',
}

def log(msg):
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)

try:
    log(f"Reading Excel: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH, sheet_name='数据汇总', header=1)
    log(f"Raw shape: {df.shape}")
    log(f"Raw columns: {df.columns.tolist()[:15]}")

    df = df.iloc[:, :11]
    df.columns = ['编号', '姓名', '工序'] + BODY_PARTS
    df = df[df['工序'].notna()].copy()

    for col in BODY_PARTS:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.dropna(subset=BODY_PARTS, how='all')

    log(f"Total rows: {len(df)}")
    log(f"打磨 rows: {len(df[df['工序'] == '打磨'])}")
    log(f"装饰 rows: {len(df[df['工序'] == '装饰'])}")
    log(f"Data sample:\n{df.head(10).to_string()}")

    def compute_proportions(sub_df, body_parts, choices=(1, 2, 3, 4, 5)):
        result = {}
        for part in body_parts:
            counts = {}
            total = 0
            for c in choices:
                cnt = (sub_df[part] == c).sum()
                counts[c] = cnt
                total += cnt
            proportions = {c: counts[c] / total if total > 0 else 0 for c in choices}
            result[part] = proportions
        return result

    def plot_stacked_bar(proportions, process_name, output_path):
        fig, ax = plt.subplots(figsize=(14, 7))

        choices = [1, 2, 3, 4, 5]
        n_parts = len(BODY_PARTS)
        x = np.arange(n_parts)
        bar_width = 0.6

        bottoms = np.zeros(n_parts)
        for c in choices:
            vals = [proportions[part][c] for part in BODY_PARTS]
            bars = ax.bar(x, vals, bar_width, bottom=bottoms,
                          label=CHOICE_LABELS[c], color=CHOICE_COLORS[c],
                          edgecolor='white', linewidth=0.5)
            for i, (v, b) in enumerate(zip(vals, bottoms)):
                if v > 0.05:
                    ax.text(x[i], b + v / 2, f'{v:.0%}',
                            ha='center', va='center', fontsize=10, fontweight='bold',
                            color='white' if c in (1, 3, 5) else 'black')
            bottoms += vals

        ax.set_xticks(x)
        ax.set_xticklabels(BODY_PARTS, fontsize=12, fontweight='bold')
        ax.set_ylabel('占比', fontsize=14, fontweight='bold')
        ax.set_title(f'主观量表选择占比 — {process_name}', fontsize=18, fontweight='bold', pad=15)
        ax.set_ylim(0, 1.05)
        ax.legend(loc='upper right', fontsize=11, framealpha=0.9,
                  title='选择项', title_fontsize=12)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))

        plt.tight_layout()
        fig.savefig(output_path, dpi=200, bbox_inches='tight')
        plt.close(fig)
        log(f"Saved: {output_path}")

    def plot_grouped_bar(proportions, process_name, output_path):
        fig, ax = plt.subplots(figsize=(16, 8))

        choices = [1, 2, 3, 4, 5]
        n_parts = len(BODY_PARTS)
        n_choices = len(choices)
        x = np.arange(n_parts)
        group_width = 0.75
        bar_width = group_width / n_choices

        for i, c in enumerate(choices):
            vals = [proportions[part][c] for part in BODY_PARTS]
            offset = (i - n_choices / 2 + 0.5) * bar_width
            bars = ax.bar(x + offset, vals, bar_width * 0.9,
                          label=CHOICE_LABELS[c], color=CHOICE_COLORS[c],
                          edgecolor='white', linewidth=0.5)
            for j, v in enumerate(vals):
                if v > 0.02:
                    ax.text(x[j] + offset, v + 0.01, f'{v:.0%}',
                            ha='center', va='bottom', fontsize=8, fontweight='bold')

        ax.set_xticks(x)
        ax.set_xticklabels(BODY_PARTS, fontsize=12, fontweight='bold')
        ax.set_ylabel('占比', fontsize=14, fontweight='bold')
        ax.set_title(f'主观量表各部位选择占比 — {process_name}', fontsize=18, fontweight='bold', pad=15)
        ax.legend(loc='upper right', fontsize=10, framealpha=0.9,
                  title='选择项', title_fontsize=11)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
        ax.set_ylim(0, ax.get_ylim()[1] * 1.15)

        plt.tight_layout()
        fig.savefig(output_path, dpi=200, bbox_inches='tight')
        plt.close(fig)
        log(f"Saved: {output_path}")

    for process in ['打磨', '装饰']:
        sub = df[df['工序'] == process]
        props = compute_proportions(sub, BODY_PARTS)

        log(f"\n{process} proportions:")
        for part in BODY_PARTS:
            log(f"  {part}: {props[part]}")

        stacked_path = os.path.join(OUTPUT_DIR, f'主观量表_{process}_堆叠占比.png')
        plot_stacked_bar(props, process, stacked_path)

        grouped_path = os.path.join(OUTPUT_DIR, f'主观量表_{process}_分组占比.png')
        plot_grouped_bar(props, process, grouped_path)

    log("\nAll charts generated!")

except Exception as e:
    log(f"Error: {e}")
    import traceback
    log(traceback.format_exc())