# -*- coding: utf-8 -*-
"""
自动下载 MediaPipe Face Detection 所需文件到 templates/mediapipe/face_detection/
运行：python download_mediapipe.py
"""
import os
import urllib.request
import time

# CDN 镜像列表（按速度排序，自动回退）
MIRRORS = [
    "https://cdn.jsdmirror.com",
    "https://jsd.onmicrosoft.cn",
    "https://cdn.jsdelivr.net.cn",
    "https://cdn.jsdelivr.net",
]

# 需要下载的文件
FILES = [
    "face_detection.js",
    "face_detection_solution_simd_wasm_bin.js",
    "face_detection_solution_simd_wasm_bin.wasm",
    "face_detection_short_range.tflite",
]

VERSION = "@mediapipe/face_detection@0.4.1646425229"
# 目标目录（Flask 默认 static 目录）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_DIR = os.path.join(BASE_DIR, 'static', 'mediapipe', 'face_detection')


def try_download(url, dest):
    """尝试下载，返回 True/False"""
    try:
        print(f"  尝试：{url}")
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(dest, 'wb') as f:
            f.write(data)
        print(f"  ✅ 成功：{os.path.basename(dest)} ({len(data)/1024:.1f} KB)")
        return True
    except Exception as e:
        print(f"  ❌ 失败：{e}")
        return False


def download_file(filename):
    dest = os.path.join(TARGET_DIR, filename)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print(f"  ⏭️  已存在，跳过：{filename}")
        return True

    for mirror in MIRRORS:
        url = f"{mirror}/npm/{VERSION}/{filename}"
        if try_download(url, dest):
            return True
    return False


def main():
    os.makedirs(TARGET_DIR, exist_ok=True)
    print(f"📁 目标目录：{TARGET_DIR}\n")

    success, failed = 0, []
    for f in FILES:
        print(f"⬇️  {f}")
        if download_file(f):
            success += 1
        else:
            failed.append(f)
        print()

    print("=" * 50)
    print(f"完成：{success}/{len(FILES)} 个文件下载成功")
    if failed:
        print("❌ 以下文件下载失败，请手动下载：")
        for f in failed:
            print(f"   - {f}")
        print("\n手动下载地址（任选一个镜像域名拼接）：")
        for f in failed:
            print(f"   {MIRRORS[0]}/npm/{VERSION}/{f}")
    else:
        print("🎉 全部完成！")

    input("\n按回车键退出...")


if __name__ == '__main__':
    main()