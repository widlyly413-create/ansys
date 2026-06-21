"""
一键运行完整的 sEMG 处理与分析流程

使用方法：
  python run_all.py           增量处理（只处理新增受试者，已有数据跳过）
  python run_all.py --force   强制重新处理全部数据
"""

import subprocess
import sys
import time
import os

SCRIPTS = [
    ("batch_preprocess.py",  "步骤1：原始数据预处理"),
    ("extract_mvc.py",       "步骤2：MVC 极大值提取"),
    ("analyze_rms_mvc.py",   "步骤3：RMS %MVC 统计分析"),
    ("visualize_comparison.py", "步骤4：可视化对比分析"),
]


def main():
    force = "--force" in sys.argv

    print("=" * 60)
    print("  表面肌电（sEMG）数据处理与分析流程")
    if force:
        print("  模式：--force 强制重新处理全部数据")
    else:
        print("  模式：增量处理（已有数据自动跳过）")
    print("=" * 60)

    # --force 模式下先清理已有输出
    if force:
        print("\n  清理已有输出文件...")
        # 不清除 data_processed，因为 batch_preprocess.py 有自身的跳过逻辑
        for f in ["MVC_values.csv", "analysis_results.xlsx"]:
            fp = os.path.join(os.path.dirname(__file__), f)
            if os.path.exists(fp):
                os.remove(fp)
                print(f"    已删除: {f}")
        import shutil
        figures_dir = os.path.join(os.path.dirname(__file__), "figures")
        if os.path.exists(figures_dir):
            shutil.rmtree(figures_dir)
            print(f"    已删除: figures/")

    base_dir = os.path.dirname(os.path.abspath(__file__))

    for script_name, description in SCRIPTS:
        script_path = os.path.join(base_dir, script_name)
        print(f"\n▶ 正在执行 {description}...")
        print("-" * 40)
        t0 = time.time()

        result = subprocess.run(
            [sys.executable, script_path],
            cwd=base_dir,
            capture_output=False,
            text=True,
        )

        elapsed = time.time() - t0

        if result.returncode != 0:
            print(f"✗ 脚本 {script_name} 运行失败，终止流程")
            sys.exit(1)

        print(f"✓ 完成（耗时 {elapsed:.1f}s）")

    print("\n" + "=" * 60)
    print("  全部流程执行完毕！")
    print("=" * 60)
    print(f"\n输出文件：")
    print(f"  data_processed/     — 预处理后数据")
    print(f"  MVC_values.csv      — MVC 参考值")
    print(f"  analysis_results.xlsx — %MVC 统计分析结果")
    print(f"  figures/            — 可视化对比图")


if __name__ == "__main__":
    main()