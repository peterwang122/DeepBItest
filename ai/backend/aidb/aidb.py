import traceback
from ai.backend.util.write_log import logger
from ai.backend.base_config import CONFIG
import re
import ast
import json
from ai.backend.util.token_util import num_tokens_from_messages
import os
import time
from ai.backend.util import base_util
import asyncio
from requests.exceptions import HTTPError
from ai.backend.language_info import LanguageInfo
from ai.backend.util import database_util
from ai.agents.agentchat import TableSelectorAgent

max_retry_times = CONFIG.max_retry_times


class AIDB:
    def __init__(self, chatClass):
        self.agent_instance_util = chatClass.agent_instance_util
        self.outgoing = chatClass.outgoing
        self.language_mode = chatClass.language_mode
        self.set_language_mode(self.language_mode)
        self.user_name = chatClass.user_name
        self.websocket = chatClass.ws
        self.uid = chatClass.uid
        self.log_list = []
        self.db_info_json = None

    def set_language_mode(self, language_mode):
        self.language_mode = language_mode

        # if self.language_mode == CONFIG.language_english:
        #     self.error_message_timeout = 'Sorry, this AI-GPT interface call timed out, please try again.'
        #     self.question_ask = ' This is my question，Answer user questions in English: '
        #     self.error_miss_data = 'Missing database annotation'
        #     self.error_miss_key = 'The ApiKey setting is incorrect, please modify it!'
        #     self.error_no_report_question = 'Sorry, this conversation only deals with report generation issues. Please ask this question in the data analysis conversation.'

        # elif self.language_mode == CONFIG.language_chinese:
        #     self.error_message_timeout = "十分抱歉，本次AI-GPT接口调用超时，请再次重试"
        #     self.question_ask = ' 以下是我的问题，请用中文回答: '
        #     self.error_miss_data = '缺少数据库注释'
        #     self.error_miss_key = "ApiKey设置有误,请修改!"
        #     self.error_no_report_question = "非常抱歉，本对话只处理报表生成类问题，这个问题请您到数据分析对话中提问"

        self.error_message_timeout = LanguageInfo.error_message_timeout
        self.question_ask = LanguageInfo.question_ask
        self.error_miss_data = LanguageInfo.error_miss_data
        self.error_miss_key = LanguageInfo.error_miss_key
        self.error_no_report_question = LanguageInfo.error_no_report_question

    async def get_data_desc(self, q_str):
        """Get data description"""
        planner_user = self.agent_instance_util.get_agent_planner_user()
        database_describer = self.agent_instance_util.get_agent_database_describer()

        try:
            table_message = str(self.agent_instance_util.base_message)
            if base_util.is_json(table_message):
                str_obj = json.loads(table_message)
            else:
                str_obj = ast.literal_eval(table_message)

            table_comments = {'table_desc': [], 'databases_desc': ''}
            for table in str_obj['table_desc']:
                if len(table['table_comment']) > 0:
                    table_comments['table_desc'].append(
                        {'table_name': table['table_name'], 'table_comment': table['table_comment']})
                else:
                    table_comments['table_desc'].append(table)

            qustion_message = "Please explain this data to me."

            if self.language_mode == CONFIG.language_chinese:
                qustion_message = "请为我解释一下这些数据"

            await planner_user.initiate_chat(
                database_describer,
                # message=self.agent_instance_util.base_message + '\n' + self.question_ask + '\n' + str(qustion_message),
                message=str(table_comments) + '\n' + self.question_ask + '\n' + str(qustion_message),
            )
            answer_message = planner_user.last_message()["content"]
            # print("answer_message: ", answer_message)
        except HTTPError as http_err:
            traceback.print_exc()
            error_message = self.generate_error_message(http_err)
            return await self.put_message(500, CONFIG.talker_bi, CONFIG.type_comment_first, error_message)

        except Exception as e:
            traceback.print_exc()
            logger.error("from user:[{}".format(self.user_name) + "] , " + "error: " + str(e))
            return await self.put_message(500, receiver=CONFIG.talker_bi, data_type=CONFIG.type_comment_first,
                                          content=self.error_message_timeout)

        return await self.put_message(200, receiver=CONFIG.talker_bi, data_type=CONFIG.type_comment_first,
                                      content=answer_message)

    async def check_data_base(self, q_str, databases_id=-1):
        """Check whether the comments meet the requirements. Those that have passed will not be tested again."""

        message = [
            {
                "role": "system",
                "content": str(q_str),
            }
        ]

        num_tokens = num_tokens_from_messages(message, model='gpt-4')
        print('num_tokens: ', num_tokens)

        if num_tokens < CONFIG.max_token_num:
            table_content = []
            if q_str.get('table_desc'):
                for tb in q_str.get('table_desc'):

                    table_name = tb.get('table_name')
                    table_comment = tb.get('table_comment')
                    if table_comment == '':
                        table_comment = tb.get('table_name')

                    fd_desc = []
                    if tb.get('field_desc'):
                        for fd in tb.get('field_desc'):
                            fd_comment = fd.get('comment')
                            if fd_comment == '':
                                fd_comment = fd.get('name')
                            if fd.get('is_pass') and fd.get('is_pass') == 1:
                                continue
                            else:
                                fd_desc.append({
                                    "name": fd.get('name'),
                                    "comment": fd_comment
                                })

                    if len(fd_desc) > 0:
                        tb_desc = {
                            "table_name": table_name,
                            "table_comment": table_comment,
                            "field_desc": fd_desc
                        }
                        table_content.append(tb_desc)
                    elif tb.get('is_pass') and fd.get('is_pass') == 1:
                        continue
                    else:
                        tb_desc = {
                            "table_name": table_name,
                            "table_comment": table_comment
                        }
                        # table_content.append(tb_desc)

            print("The number of tables to be processed this time： ", len(table_content))
            if len(table_content) > 0:
                try:
                    num = 1 + (len(q_str.get('table_desc')) - len(table_content))
                    for db_desc in table_content:
                        print("Start processing table: ", str(db_desc))
                        planner_user = self.agent_instance_util.get_agent_planner_user()
                        database_describer = self.agent_instance_util.get_agent_data_checker_assistant()

                        qustion_message = """Help me check that the following data comments are complete and correct."""

                        # if self.language_mode == CONFIG.language_chinese:
                        #     qustion_message = "帮助我检查下列数据注释是否完整且正确: "

                        await asyncio.wait_for(planner_user.initiate_chat(
                            database_describer,
                            # message=content + '\n' + " This is my question: " + '\n' + str(qustion_message),
                            message=str(qustion_message) + '\n' + str(db_desc),
                        ), timeout=120)  # time out 120 seconds

                        answer_message = planner_user.last_message()["content"]
                        print("answer_message: ", answer_message)

                        match = re.search(
                            r"```.*```", answer_message.strip(), re.MULTILINE | re.IGNORECASE | re.DOTALL
                        )
                        json_str = ""
                        if match:
                            json_str = match.group()
                        else:
                            json_str = answer_message

                        try:
                            json_str = json_str.replace("```json", "")
                            json_str = json_str.replace("```", "")
                            # print('json_str ：', json_str)
                            chart_code_str = json_str.replace("\n", "")
                            if base_util.is_json(chart_code_str):
                                table_desc = json.loads(chart_code_str)
                            else:
                                table_desc = ast.literal_eval(chart_code_str)

                            table_name = table_desc.get('table_name')

                            # print("q_str['table_desc'] ,", q_str['table_desc'])
                            for table in q_str['table_desc']:
                                if table.get('table_name') == table_name:
                                    if table_desc.get('is_pass') and table_desc.get('is_pass') == 1:
                                        if table.get('table_comment') == '':
                                            table['table_comment'] = table.get('table_name')

                                        table['is_pass'] = table_desc.get('is_pass')
                                    if table_desc.get('field_desc'):
                                        for fd in table_desc.get('field_desc'):
                                            field_name = fd.get('name')
                                            for field in table.get('field_desc'):
                                                if field.get('name') == field_name:
                                                    if fd.get('is_pass') and fd.get('is_pass') == 1:
                                                        if field.get('comment') == '':
                                                            field['comment'] = field.get('name')
                                                        field['is_pass'] = fd.get(
                                                            'is_pass')

                            percentage = (num / len(q_str.get('table_desc'))) * 100
                            percentage_integer = int(percentage)

                            await self.put_message(200, CONFIG.talker_log, CONFIG.type_data_check,
                                                   content=percentage_integer)
                            num = num + 1
                        except Exception as e:
                            traceback.print_exc()

                except Exception as e:
                    traceback.print_exc()
                    logger.error("from user:[{}".format(self.user_name) + "] , " + "error: " + str(e))
                    await self.put_message(500, CONFIG.talker_log, CONFIG.type_comment, self.error_message_timeout)
                    return
            else:
                percentage_integer = 100
                await self.put_message(200, CONFIG.talker_log, CONFIG.type_data_check,
                                       content=percentage_integer)

            if q_str.get('table_desc'):
                for tb in q_str.get('table_desc'):
                    if not tb.get('is_pass'):
                        tb['is_pass'] = 0
                    if tb.get('field_desc'):
                        for fd in tb.get('field_desc'):
                            if not fd.get('is_pass'):
                                fd['is_pass'] = 0

            # print(" 最终 q_str : ", q_str)
            await self.put_message(200, CONFIG.talker_bi, CONFIG.type_comment, q_str)
        else:
            databases_id = 0

            if databases_id == -1:
                if self.language_mode == CONFIG.language_chinese:
                    content = '所选表格' + str(num_tokens) + ' , 超过了最大长度:' + str(CONFIG.max_token_num) + ' , 请重新选择'
                else:
                    content = 'The selected table length ' + str(num_tokens) + ' ,  exceeds the maximum length: ' + str(
                        CONFIG.max_token_num) + ' , please select again'
                return await self.put_message(500, CONFIG.talker_log, CONFIG.type_data_check, content)
            else:
                table_content = []
                if q_str.get('table_desc'):
                    for tb in q_str.get('table_desc'):

                        table_name = tb.get('table_name')
                        table_comment = tb.get('table_comment')
                        if table_comment == '':
                            table_comment = tb.get('table_name')

                        fd_desc = []
                        if tb.get('field_desc'):
                            for fd in tb.get('field_desc'):
                                fd_comment = fd.get('comment')
                                if fd_comment == '':
                                    fd_comment = fd.get('name')
                                if fd.get('is_pass') and fd.get('is_pass') == 1:
                                    continue
                                else:
                                    fd_desc.append({
                                        "name": fd.get('name'),
                                        "comment": fd_comment
                                    })

                        if len(fd_desc) > 0:
                            tb_desc = {
                                "table_name": table_name,
                                "table_comment": table_comment,
                                "field_desc": fd_desc
                            }
                            table_content.append(tb_desc)
                        elif tb.get('is_pass') and fd.get('is_pass') == 1:
                            continue
                        else:
                            tb_desc = {
                                "table_name": table_name,
                                "table_comment": table_comment
                            }
                            table_content.append(tb_desc)

                print("The number of tables to be processed this time： ", len(table_content))
                if q_str.get('table_desc'):
                    for tb in q_str.get('table_desc'):
                        if not tb.get('is_pass'):
                            tb['is_pass'] = 1
                        if tb.get('field_desc'):
                            for fd in tb.get('field_desc'):
                                if not fd.get('is_pass'):
                                    fd['is_pass'] = 1

                # print(" 最终 q_str : ", q_str)
                await self.put_message(200, CONFIG.talker_bi, CONFIG.type_comment, q_str)

    async def put_message(self, state=200, receiver='log', data_type=None, content=None):
        mess = {'state': state, 'data': {'data_type': data_type, 'content': content}, 'receiver': receiver}
        consume_output = json.dumps(mess)
        # await self.outgoing.put(consume_output)
        # await self.ws.send(consume_output)
        if self.websocket is not None:
            await asyncio.wait_for(self.websocket.send(consume_output), timeout=CONFIG.request_timeout)

        send_mess = str(time.strftime("%Y-%m-%d %H:%M:%S",
                                      time.localtime())) + ' ---- ' + "from user:[{}".format(
            self.user_name) + "], reply a message:{}".format(consume_output)
        print(send_mess)
        logger.info(send_mess)

    async def check_api_key(self):
        # self.agent_instance_util.api_key_use = True
        # .token_[uid].json
        token_path = CONFIG.up_file_path + '.token_' + str(self.uid) + '.json'
        print("token_path++++", token_path)
        if os.path.exists(token_path):
            print("token_path====", token_path)
            try:
                ApiKey, HttpProxyHost, HttpProxyPort, ApiHost, in_use = self.load_api_key(token_path)
                if ApiKey is None or len(ApiKey) == 0:
                    await self.put_message(500, CONFIG.talker_log, CONFIG.type_log_data, self.error_miss_key)
                    return False

                self.agent_instance_util.set_api_key(ApiKey, ApiHost, in_use)

                if HttpProxyHost is not None and len(str(HttpProxyHost)) > 0 and HttpProxyPort is not None and len(
                    str(HttpProxyPort)) > 0:
                    # openai_proxy = "http://127.0.0.1:7890"
                    self.agent_instance_util.openai_proxy = 'http://' + str(HttpProxyHost) + ':' + str(HttpProxyPort)

                planner_user = self.agent_instance_util.get_agent_planner_user(is_log_out=False)
                api_check = self.agent_instance_util.get_agent_api_check()
                await asyncio.wait_for(planner_user.initiate_chat(
                    api_check,
                    # message=content + '\n' + " This is my question: " + '\n' + str(qustion_message),
                    message=""" 5-2 =?? """,
                ), timeout=120)  # time out 120 seconds

                self.agent_instance_util.api_key_use = True

                return True
            except HTTPError as http_err:
                traceback.print_exc()

                error_miss_key = self.generate_error_message(http_err, error_message=LanguageInfo.api_key_fail)
                await self.put_message(500, CONFIG.talker_log, CONFIG.type_log_data, error_miss_key)
                return False
            except Exception as e:
                traceback.print_exc()
                print("e=====", str(e))
                logger.error("from user:[{}".format(self.user_name) + "] , " + "error: " + str(e))
                await self.put_message(500, CONFIG.talker_log, CONFIG.type_log_data, self.error_miss_key)
                return False


        else:
            await self.put_message(500, receiver=CONFIG.talker_log, data_type=CONFIG.type_log_data,
                                   content=self.error_miss_key)
            return False

    def set_base_message(self, message):
        try:
            json_str = json.loads(message) if isinstance(message, str) else message
        except json.JSONDecodeError:
            logger.error("Failed to decode JSON from message.")
            return
        
        base_message = json_str.get('base_message')
        if base_message:
            database = json_str.get('database')
            if database == 'csv':
                self.agent_instance_util.set_base_csv_info(base_message)
                self.agent_instance_util.set_base_message(base_message)
            else:
                databases_id = json_str.get('data', {}).get('databases_id')
                db_id = str(databases_id)
                obj = database_util.Main(db_id)
                if_suss, db_info = obj.run()
                if if_suss:
                    if database == 'pg':
                        database = 'postgresql'
                    setattr(self.agent_instance_util, f"base_{database}_info", ' When connecting to the database, be sure to bring the port. This is ' + database + ' database info :' + '\n' + str(db_info))
                    self.agent_instance_util.set_base_message(base_message, databases_id=db_id)
                    self.agent_instance_util.db_id = db_id
                else:
                    logger.error("Failed to get database info for db_id: {}".format(db_id))
            
    async def test_api_key(self):
        # self.agent_instance_util.api_key_use = True

        # .token_[uid].json
        token_path = CONFIG.up_file_path + '.token_' + str(self.uid) + '.json'
        print('token_path : ', token_path)
        if os.path.exists(token_path):
            try:
                ApiKey, HttpProxyHost, HttpProxyPort, ApiHost, in_use = self.load_api_key(token_path)
                if ApiKey is None or len(ApiKey) == 0:
                    return await self.put_message(200, CONFIG.talker_api, CONFIG.type_test, LanguageInfo.no_api_key)

                self.agent_instance_util.set_api_key(ApiKey, ApiHost, in_use)

                if HttpProxyHost is not None and len(str(HttpProxyHost)) > 0 and HttpProxyPort is not None and len(
                    str(HttpProxyPort)) > 0:
                    # openai_proxy = "http://127.0.0.1:7890"
                    self.agent_instance_util.openai_proxy = 'http://' + str(HttpProxyHost) + ':' + str(HttpProxyPort)

                planner_user = self.agent_instance_util.get_agent_planner_user(is_log_out=False)
                api_check = self.agent_instance_util.get_agent_api_check()
                await asyncio.wait_for(planner_user.initiate_chat(
                    api_check,
                    # message=content + '\n' + " This is my question: " + '\n' + str(qustion_message),
                    message=""" 5-2 =?? """,
                ), timeout=120)  # time out 120 seconds

                self.agent_instance_util.api_key_use = True

                return await self.put_message(200, CONFIG.talker_api, CONFIG.type_test, LanguageInfo.api_key_success)

            except HTTPError as http_err:
                traceback.print_exc()

                error_miss_key = self.generate_error_message(http_err, error_message=LanguageInfo.api_key_fail)
                return await self.put_message(200, CONFIG.talker_api, CONFIG.type_test, error_miss_key)

            except Exception as e:
                traceback.print_exc()
                logger.error("from user:[{}".format(self.user_name) + "] , " + "error: " + str(e))
                return await self.put_message(200, CONFIG.talker_api, CONFIG.type_test, LanguageInfo.api_key_fail)

        else:
            return await self.put_message(200, CONFIG.talker_api, CONFIG.type_test, LanguageInfo.no_api_key)

    def load_api_key(self, token_path):
        ApiKey = None
        HttpProxyHost = None
        HttpProxyPort = None
        ApiHost = None
        in_use = None

        with open(token_path, 'r') as file:
            data = json.load(file)

        if data.get('in_use'):
            in_use = data.get('in_use')
            if in_use == 'OpenAI':
                ApiKey = data[in_use]['OpenaiApiKey']
                print('OpenaiApiKey : ', ApiKey)
                HttpProxyHost = data[in_use]['HttpProxyHost']
                print('HttpProxyHost : ', HttpProxyHost)
                HttpProxyPort = data[in_use]['HttpProxyPort']
                print('HttpProxyPort : ', HttpProxyPort)
                openaiApiHost = data[in_use]['ApiHost']
                if openaiApiHost is not None and len(str(openaiApiHost)) > 0:
                    ApiHost = openaiApiHost
            elif in_use == 'DeepInsight':
                ApiKey = data[in_use]['ApiKey']
                print('DeepBIApiKey : ', ApiKey)
                # ApiHost = "https://apiserver.deep-thought.io/proxy"
                ApiHost = CONFIG.ApiHost
            elif in_use == 'Azure':
                ApiKey = data[in_use]['AzureApiKey']
                print('DeepBIAzureApiKey : ', ApiKey)
                # ApiHost = "https://apiserver.deep-thought.io/proxy"
                ApiHost = data[in_use]['AzureHost']
        else:
            ApiKey = data['OpenaiApiKey']
            print('OpenaiApiKey : ', ApiKey)
            HttpProxyHost = data['HttpProxyHost']
            print('HttpProxyHost : ', HttpProxyHost)
            HttpProxyPort = data['HttpProxyPort']
            print('HttpProxyPort : ', HttpProxyPort)

        return ApiKey, HttpProxyHost, HttpProxyPort, ApiHost, in_use

    def generate_error_message(self, http_err, error_message=' API ERROR '):
        # print(f'HTTP error occurred: {http_err}')
        # print(f'Response status code: {http_err.response.status_code}')
        # print(f'Response text: {http_err.response.text}')

        # error_message = self.error_miss_key
        status_code = http_err.response.status_code
        if str(http_err.response.text).__contains__('deep-thought'):
            if status_code == 401:
                error_message = error_message + str(status_code) + ' , APIKEY Empty Error'
            elif status_code == 402:
                error_message = error_message + str(status_code) + ' , Data Empty Error'
            elif status_code == 403:
                error_message = error_message + str(status_code) + ' , APIKEY Error'
            elif status_code == 404:
                error_message = error_message + str(status_code) + ' , Unsupported Ai Engine Error'
            elif status_code == 405:
                error_message = error_message + str(status_code) + ' , Insufficient Token Error'
            elif status_code == 500:
                error_message = error_message + str(status_code) + ' , OpenAI API Error, ' + str(http_err.response.text)
        else:
            error_message = error_message + ' ' + str(status_code) + ' ' + str(http_err.response.text)
        return error_message

    def get_agent_select_table_assistant(self, db_info_json, use_cache=True):
        """select_table_assistant"""

        table_names = []
        table_message = {}

        for table in db_info_json['table_desc']:
            table_names.append(table['table_name'])
            table_message[table['table_name']] = table['table_comment']

        print('table_names : ', table_names)
        print('table_message : ', table_message)

        table_select = f"Read the conversation above. Then select the name of the table involved in the question from {table_names}. Only the name of the table is returned.It can be one table or multiple tables"

        select_analysis_assistant = TableSelectorAgent(
            name="select_table_assistant",
            system_message="""You are a helpful AI assistant.
                        Divide the questions raised by users into corresponding task types.
                        Different tasks have different processing methods.
                        The output should be formatted as a JSON instance that conforms to the JSON schema below, the JSON is a list of dict,
         [
         {“table_name”: “report_1”},
         {},
         {},
         ].
         Reply "TERMINATE" in the end when everything is done.

                        Task types are generally divided into the following categories:

                         """ + str(table_message) + '\n' + str(table_select),
            human_input_mode="NEVER",
            user_name=self.user_name,
            websocket=self.websocket,
            llm_config={
                "config_list": self.agent_instance_util.config_list_gpt4_turbo,
                "request_timeout": CONFIG.request_timeout,
            },
            openai_proxy=self.agent_instance_util.openai_proxy,
        )
        return select_analysis_assistant

    async def select_table_comment(self, qustion_message, use_cache):


        select_table_assistant = self.get_agent_select_table_assistant(db_info_json=self.db_info_json,
                                                                       use_cache=use_cache)
        planner_user = self.agent_instance_util.get_agent_planner_user()

        await planner_user.initiate_chat(
            select_table_assistant,
            message=qustion_message,
        )
        select_table_message = planner_user.last_message()["content"]

        match = re.search(
            r"\[.*\]", select_table_message.strip(), re.MULTILINE | re.IGNORECASE | re.DOTALL
        )
        json_str = ""
        if match:
            json_str = match.group()
        print("json_str : ", json_str)
        select_table_list = json.loads(json_str)
        print("select_table_list : ", select_table_list)

        selece_table_names = []
        # for table_str in select_table_list:
        #     table_name = table_str.get("table_name")
        #     delete_table_names.append(table_name)
        for table_str in select_table_list:
            keyname = next(iter(table_str))
            if table_str[keyname] == "":
                selece_table_names.append(keyname)
            else:
                selece_table_names.append(table_str[keyname])

        print("selece_table_names : ", selece_table_names)

        table_comment = {'table_desc': [], 'databases_desc': ''}

        for table in self.db_info_json['table_desc']:
            # print('table : ', table)
            if table['table_name'] in selece_table_names:
                table_comment['table_desc'].append(table)

        print('table_comment : ', table_comment)
        return table_comment
