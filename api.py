import os
import asyncio
from threading import Thread
from tingwu import tingwu_main
from to_pdf import to_pdf_main
import secrets
import string
from graph import main
from markdown_process import insert_picture_main
global_loop = asyncio.new_event_loop()

def run_event_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()
loop_thread = Thread(target=run_event_loop, args=(global_loop,), daemon=True)
loop_thread.start()


def save_md(markdown_content: str, write_mode: str = "w") -> str:
    chars = string.ascii_letters + string.digits
    random_filename = ''.join(secrets.choice(chars) for _ in range(8)) + ".md"
    parent_folder = os.getenv("SAVE_MARKDOWN_PATH")
    # 拼接路径
    save_path = os.path.join(parent_folder, random_filename)  
    standard_absolute_path = os.path.abspath(save_path)
    parent_folder_path = os.path.dirname(standard_absolute_path)
    if parent_folder_path and not os.path.exists(parent_folder_path):
        os.makedirs(parent_folder_path, exist_ok=True)
    with open(standard_absolute_path, write_mode, encoding="utf-8") as f:
        f.write(markdown_content)
    
    return standard_absolute_path

async def task_main(video_file_path: str):
    full_text = await tingwu_main(video_file_path)
    md_content = await main(full_text)
    md_file_path = save_md(md_content)
    insert_picture_main(md_file_path,video_file_path)
    pdf_file_path = await to_pdf_main(md_file_path)
    return pdf_file_path


def set_env(model_name, api_key, base_url,oss_ak,oss_sk,bucket_name,region,markdown_file_path,tingwu_ak,tingwu_sk,tingwu_appkey):
    os.environ["MODEL_NAME"] = model_name
    os.environ["API_KEY"] = api_key
    os.environ["BASE_URL"] = base_url
    os.environ["SAVE_MARKDOWN_PATH"] = markdown_file_path
    os.environ["OSS_AK"] = oss_ak
    os.environ["OSS_SK"] = oss_sk
    os.environ["BUCKET_NAME"] = bucket_name
    os.environ["REGION"] = region
    # os.environ["FILE_PATH"] = file_path
    os.environ["TINGWU_AK"] = tingwu_ak
    os.environ["TINGWU_SK"] = tingwu_sk
    os.environ["TINGWU_APPKEY"] = tingwu_appkey




if __name__ == "__main__":
    # set_env()
    asyncio.run(task_main(r"D:\video_save\glmtest.mp4"))