import os
import shutil
import rarfile
import zipfile

from py7zr import SevenZipFile

EN_US = os.getenv("LANG") != "zh_CN.UTF-8"
TMP_DIR = "./__pycache__"


def mk_dir(dir_path: str):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def clean_dir(dir_path: str):
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)

    os.makedirs(dir_path)


def unzip(archive: str, extract_to: str):
    mk_dir(extract_to)
    if archive.endswith(".zip"):
        with zipfile.ZipFile(archive, "r") as f:
            f.extractall(extract_to)

    elif archive.endswith(".7z"):
        with SevenZipFile(archive, "r") as f:
            f.extractall(extract_to)

    elif archive.endswith(".rar"):
        with rarfile.RarFile(archive, "r") as f:
            f.extractall(extract_to)

    else:
        raise ValueError("Unsupported file type!")


def compress(folder_path: str, zip_file: str):
    if not os.path.exists(folder_path):  # 确保文件夹存在
        raise ValueError(f"错误: 文件夹 '{folder_path}' 不存在")
    # 打开 ZIP 文件，使用 'w' 模式表示写入
    with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):  # 遍历文件夹中的文件和子文件夹
            for file in files:
                file_path = os.path.join(root, file)  # 计算相对路径，保留文件夹的根目录
                relative_path = os.path.relpath(file_path, folder_path)
                zipf.write(
                    file_path,
                    arcname=os.path.join(os.path.basename(folder_path), relative_path),
                )
