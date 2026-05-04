import os
import imghdr
import shutil
import rarfile
import zipfile
import hashlib
import exifread
import gradio as gr
import pandas as pd
from PIL import Image
from py7zr import SevenZipFile

ZH2EN = {
    "上传包含多图片的压缩包 (请确保上传完全后再提交)": "Upload compressed package with images (please ensure the package is completely uploaded before clicking submit)",
    "下载清理 EXIF 后的多图片压缩包": "Download cleaned images",
    "下载清理 EXIF 后的图片": "Download cleaned image",
    "图片 EXIF 清理": "Image EXIF Cleaner",
    "导出原格式": "Export original format",
    "单图片处理": "Process single image",
    "批量处理": "Batch processor",
    "上传图片": "Upload image",
    "EXIF 列表": "EXIF list",
    "状态栏": "Status",
}
EN_US = os.getenv("LANG") != "zh_CN.UTF-8"
TMP_DIR = os.path.join(os.path.dirname(__file__), "__pycache__")


def _L(zh_txt: str):
    return ZH2EN[zh_txt] if EN_US else zh_txt


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


def get_exif(origin_file_path):
    with open(origin_file_path, "rb") as image_file:
        tags = exifread.process_file(image_file)

    output = ""
    for key in tags.keys():
        value = str(tags[key])
        output += "{0}:{1}\n".format(key, value)

    return output


def clear_exif(img_path: str, cache: str, img_mode=None, outdir=""):
    save_path = f"{cache}/{outdir}output." + img_path.split(".")[-1]
    img = Image.open(img_path)
    data = list(img.getdata())
    if img_mode:
        save_path = f"{cache}/{outdir}{hashlib.md5(img_path.encode()).hexdigest()}.jpg"
    else:
        img_mode = img.mode

    img_without_exif = Image.new(img_mode, img.size)
    img_without_exif.putdata(data)
    img_without_exif.save(save_path)
    return save_path


def find_images(dir_path: str):
    found_images = []
    for root, _, files in os.walk(dir_path):
        for file in files:
            fpath = os.path.join(root, file).replace("\\", "/")
            if imghdr.what(fpath) != None:
                found_images.append(fpath)

    return found_images


# outer funcs
def infer(img_path: str, keep_ext: bool, cache=TMP_DIR):
    status = "Success"
    out_img = out_exif = None
    try:
        if not img_path or imghdr.what(img_path) == None:
            raise ValueError("请输入图片！")

        clean_dir(cache)
        img_mode = "RGB" if not keep_ext else None
        out_img = clear_exif(img_path, cache, img_mode)
        out_exif = get_exif(img_path)

    except Exception as e:
        status = f"{e}"

    return status, out_img, out_exif


def batch_infer(imgs_zip: str, keep_ext: bool, cache=TMP_DIR):
    status = "Success"
    out_images = out_exifs = None
    try:
        if not imgs_zip:
            raise ValueError("Please upload image archive!")

        clean_dir(cache)
        mk_dir(f"{cache}/outputs")
        extract_to = f"{cache}/inputs"
        unzip(imgs_zip, extract_to)
        imgs = find_images(extract_to)
        img_mode = "RGB" if not keep_ext else None
        exifs = []
        for img in imgs:
            clear_exif(img, cache, img_mode, "outputs/")
            exifs.append({"filename": os.path.basename(img), "exif": get_exif(img)})

        if not exifs:
            raise ValueError("No image in the zip")

        out_images = f"{cache}/outputs.zip"
        compress(f"{cache}/outputs", out_images)
        out_exifs = pd.DataFrame(exifs)

    except Exception as e:
        status = f"{e}"

    return status, out_images, out_exifs


def main():
    return gr.TabbedInterface(
        [
            gr.Interface(
                fn=infer,
                inputs=[
                    gr.File(label=_L("上传图片"), file_types=["image"]),
                    gr.Checkbox(label=_L("导出原格式"), value=False),
                ],
                outputs=[
                    gr.Textbox(label=_L("状态栏"), buttons=["copy"]),
                    gr.Image(
                        label=_L("下载清理 EXIF 后的图片"),
                        type="filepath",
                        buttons=["download", "fullscreen"],
                    ),
                    gr.Textbox(label="EXIF", buttons=["copy"]),
                ],
                flagging_mode="never",
            ),
            gr.Interface(
                fn=batch_infer,
                inputs=[
                    gr.File(
                        label=_L("上传包含多图片的压缩包 (请确保上传完全后再提交)"),
                        file_types=[".zip", ".7z", ".rar"],
                    ),
                    gr.Checkbox(label=_L("导出原格式"), value=False),
                ],
                outputs=[
                    gr.Textbox(label=_L("状态栏"), buttons=["copy"]),
                    gr.File(
                        label=_L("下载清理 EXIF 后的多图片压缩包"),
                        type="filepath",
                    ),
                    gr.Dataframe(label=_L("EXIF 列表")),
                ],
                flagging_mode="never",
            ),
        ],
        tab_names=[_L("单图片处理"), _L("批量处理")],
        title=_L("图片 EXIF 清理"),
    )


if __name__ == "__main__":
    main().launch(css="#gradio-share-link-button-0 { display: none; }", ssr_mode=False)
