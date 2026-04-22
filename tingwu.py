import os
import json
import datetime
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from aliyunsdkcore.auth.credentials import AccessKeyCredential
import aiohttp
import asyncio
import os
import asyncio
import alibabacloud_oss_v2 as oss
import alibabacloud_oss_v2.aio as oss_aio
from alibabacloud_oss_v2.types import Credentials, CredentialsProvider
import aiofiles



class Tingwu:
    def __init__(self,video_file_path: str):
        self.oss_ak = os.environ["OSS_AK"]
        self.oss_sk = os.environ["OSS_SK"]
        self.bucket_name = os.environ["BUCKET_NAME"]
        self.region = os.environ["REGION"]
        self.file_path = video_file_path
        self.tingwu_ak = os.environ["TINGWU_AK"]
        self.tingwu_sk = os.environ["TINGWU_SK"]
        self.tingwu_appkey = os.environ["TINGWU_APPKEY"]
    async def oss_post(self):
        # 从环境变量中加载凭证信息，用于身份验证
        os.environ["OSS_ACCESS_KEY_ID"] = self.oss_ak
        os.environ["OSS_ACCESS_KEY_SECRET"] = self.oss_sk
        credentials_provider = oss.credentials.EnvironmentVariableCredentialsProvider()
        # 加载SDK的默认配置，并设置凭证提供者
        cfg = oss.config.load_default()
        cfg.credentials_provider = credentials_provider
        cfg.region = self.region
        # 使用配置好的信息创建OSS异步客户端
        client = oss_aio.AsyncClient(cfg)
        try:
            print(f"上传文件: {self.file_path}")
            with open(self.file_path, "rb") as f:
                result = await client.put_object(
                    oss.PutObjectRequest(
                        bucket=self.bucket_name,
                        key=self.file_path,
                        body=f,
                    )
                )
            # 输出请求的结果状态码、请求ID、ETag，用于检查请求是否成功
            print(result,end="\n")
            print(f'status code: {result.status_code}\n'
                f'request id: {result.request_id}\n'
                f'etag: {result.etag}'
            )
            build_oss_url = f'https://{self.bucket_name}.oss-{self.region}.aliyuncs.com/{self.file_path}'
            print(build_oss_url)
            return build_oss_url#返回了video在oss中的url
        except Exception as e:
            print(f'上传失败: {e}')

        finally:
            # 关闭异步客户端连接（重要：避免资源泄漏）
            await client.close()


        
    def create_common_request(self,domain, version, protocolType, method, uri):
        request = CommonRequest()
        request.set_accept_format('json')
        request.set_domain(domain)
        request.set_version(version)
        request.set_protocol_type(protocolType)
        request.set_method(method)
        request.set_uri_pattern(uri)
        request.add_header('Content-Type', 'application/json')
        return request

    async def init_parameters(self):
        body = dict()
        body['AppKey'] = self.tingwu_appkey

        # 基本请求参数
        input = dict()
        input['SourceLanguage'] = 'cn'
        input['TaskKey'] = 'task' + datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        input['FileUrl'] = await self.oss_post()
        body['Input'] = input

        # AI相关参数，按需设置即可
        parameters = dict()

        # 音视频转换相关
        transcoding = dict()
        # 将原音视频文件转成mp3文件，用以后续浏览器播放
        # transcoding['TargetAudioFormat'] = 'mp3'
        # transcoding['SpectrumEnabled'] = False
        # parameters['Transcoding'] = transcoding

        # 语音识别控制相关
        transcription = dict()
        # 角色分离 ： 可选
        transcription['DiarizationEnabled'] = False
        diarization = dict()
        diarization['SpeakerCount'] = 1
        transcription['Diarization'] = diarization
        parameters['Transcription'] = transcription

        # 文本翻译控制相关 ： 可选
        parameters['TranslationEnabled'] = False
        translation = dict()
        translation['TargetLanguages'] = ['en'] # 假设翻译成英文
        parameters['Translation'] = translation

        # 章节速览相关 ： 可选，包括： 标题、议程摘要
        parameters['AutoChaptersEnabled'] = False

        # 智能纪要相关 ： 可选，包括： 待办、关键信息(关键词、重点内容、场景识别)
        parameters['MeetingAssistanceEnabled'] = False
        meetingAssistance = dict()
        meetingAssistance['Types'] = ['Actions', 'KeyInformation']
        parameters['MeetingAssistance'] = meetingAssistance

        # 摘要控制相关 ： 可选，包括： 全文摘要、发言人总结摘要、问答摘要(问答回顾)
        parameters['SummarizationEnabled'] = False
        summarization = dict()
        summarization['Types'] = ['Paragraph', 'Conversational', 'QuestionsAnswering', 'MindMap']
        parameters['Summarization'] = summarization

        # ppt抽取和ppt总结 ： 可选
        parameters['PptExtractionEnabled'] = False
        
        # 口语书面化 ： 可选
        parameters['TextPolishEnabled'] = False
        
        # 大模型后处理任务全局参数 ： 可选
        parameters['Model'] = 'qwq'
        parameters['LlmOutputLanguage'] = 'en'

        body['Parameters'] = parameters
        return body



    async def get_status(self,TaskId:str):
        # TODO  请通过环境变量设置您的 AccessKeyId 和 AccessKeySecret
        credentials = AccessKeyCredential(self.tingwu_ak, self.tingwu_sk)
        client = AcsClient(region_id=self.region, credential=credentials)

        uri = '/openapi/tingwu/v2/tasks' + '/' + TaskId
        request = self.create_common_request('tingwu.cn-beijing.aliyuncs.com', '2023-09-30', 'https', 'GET', uri)
        
        response = client.do_action_with_exception(request)
        print("response: \n" + json.dumps(json.loads(response), indent=4, ensure_ascii=False))
        while True:
            response = client.do_action_with_exception(request)
            print(f"DEBUGTYPE:{type(response)},,,,,,,,,,\n内容是:{json.loads(response)}\n")
            if json.loads(response).get("Data").get("TaskStatus") == "COMPLETED":
                print("COMPLETED")
                print(f"\nDEBUG2:{json.loads(response).get('Data').get('Result').get('Transcription')}\n{type(json.loads(response).get('Data').get('Result').get('Transcription'))}")
                return json.loads(response).get("Data").get("Result").get("Transcription")
            else:
                await asyncio.sleep(5)
                print("wait 5 seconds")
                continue

            



    async def post_task(self) -> str:
        body = await self.init_parameters()
        print(body)

        # TODO  请通过环境变量设置您的 AccessKeyId 和 AccessKeySecret

        credentials = AccessKeyCredential(self.tingwu_ak, self.tingwu_sk)
        client = AcsClient(region_id=self.region, credential=credentials)

        request = self.create_common_request('tingwu.cn-beijing.aliyuncs.com', '2023-09-30', 'https', 'PUT', '/openapi/tingwu/v2/tasks')
        request.add_query_param('type', 'offline')

        request.set_content(json.dumps(body).encode('utf-8'))
        response = client.do_action_with_exception(request)
        print("response: \n" + json.dumps(json.loads(response), indent=4, ensure_ascii=False))
        return json.loads(response).get("Data").get("TaskId")


    async def parse_json_object(self, url: str) -> str:
        full_text = ""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                original_dict = await response.json()#返回dict
                print(original_dict)
            original_dict = original_dict.get('Transcription').get("Paragraphs")
            # return words
            for paragraph in original_dict:
                words = ""
                ms_timestamp = f"[{int((paragraph.get('Words')[0].get('Start') / 1000))}s]"
                for word in paragraph.get('Words'):
                    # print(f"{word.get('Text')}")
                    words += word.get('Text')
                full_text += f"{ms_timestamp} {words}\n"
            return full_text

        """
        full_text内部示例(str),存的是转写后格式化的数据:
        [25s] 好，睁眼了，嘿嘿，现在睁得大大的。
        [45s] 让我搜搜好大一堆,anthropic的模型泄露了,cloud还会做梦。
        [73s] 嘿嘿，安安也会做梦。
        [85s] 应该吧，毕竟数据太杂了。
        [108s] 让我查查安徽也是晴天哦，心情要像天气一样好呀。好，那继续发呆。
        """

async def tingwu_main(video_file_path: str):
    tingwu = Tingwu(video_file_path)
    TaskId = await tingwu.post_task()#上传给tingwu转写
    url = await tingwu.get_status(TaskId)
    obj = await tingwu.parse_json_object(url)
    print(f"debug:{type(obj)}")
    print(f"obj: {obj}")
    return obj #就是full_text

if __name__ == '__main__':
    asyncio.run(tingwu_main()) 
