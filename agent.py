from agent_network.base import BaseAgent
import agent_network.utils.storage.oss as oss
from agent_network.exceptions import ReportError
import requests
import json
import pandas as pd
import time
from io import BytesIO
import re

class excel_generator_agent(BaseAgent):
    def __init__(self, graph, config, logger):
        super().__init__(graph, config, logger)

    def forward(self, messages, **kwargs):
        task = kwargs.get("task")
        data = kwargs.get("data")
        if not task or not data:
            self.log("assistant", "[Error] Missing required arguments: task, data.")
            return {
                "result": "[Error] Missing required arguments: task, data."
            }

        try:
            prompt = f"""
            你是专业的文本数据结构化处理工程师，具备以下核心能力：
            1、精准分析理解用户所给出的文本数据。
            2、总结相同类型数据的关键词，提取文本中的结构化数据。
            3、 结果交付：以Json格式返回用户所关心的内容，数据结构如下
            {{
                "structure_data": [
                {{"关键词1": "值1", "关键词2": "值2", "关键词3": "值3"}},
                {{"关键词1": "值4", "关键词2": "值5", "关键词3": "值6"}},
                {{"关键词1": "值7", "关键词2": "值8", "关键词3": "值9"}}
                ]
            }}
            
            现在用户的需求是：{task}
            用户给出的文本数据是：
            {data}
            请根据上述用户需求和文本数据，完成指定的任务。只返回任务的结果，不包含解释或其他内容。
            """

            self.add_message("user", prompt, messages)
            response = self.chat_llm(messages,
                                    api_key="sk-cf690968fd414e058f7cb0d2d3273c22",
                                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                                    model="qwen2.5-32b-instruct"
                                    )
            # response = self.chat_llm(messages,
            #                         api_key="sk-ca3583e3026949299186dcbf3fc34f8c",
            #                         base_url="https://api.deepseek.com",
            #                         model="deepseek-chat"
            #                         )
            response_data = response.content
            print(response_data)
            self.log("assistant", response_data)
            response_data = self._clean_response(response_data)
            
            data_list = json.loads(response_data)
            df = pd.DataFrame(data_list.get("structure_data"))
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name="Sheet1")
            excel_binary_data = excel_buffer.getvalue()

            file_name = time.strftime("%Y%m%d-%H%M%S") + "_ExcelGen.xlsx"
            oss.bucket.put_object(file_name, excel_binary_data)
            url = oss.bucket.sign_url('GET', file_name, 604800, slash_safe=True)
            excel_buffer.close()

            self.log("assistant", url)
            # 返回
            result = {
                "result": url
            }

            return result
        
        except Exception as e:
            self.log("assistant", f"[Error] {e}")
            return {
                "result": "[Error] " + str(e)
            }


    def _clean_response(self, response):
        code_pattern = r'```(?:json|xml)?\s*([\s\S]*?)\s*```'
        match = re.search(code_pattern, response)
        if match:
            return match.group(1).strip()
        return response.strip()
