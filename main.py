# 开发人员: ymxu
# 开发时间: 2026/11/9 16:05
# 文件名称: main.py.py
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import OpenAI
from starlette.responses import JSONResponse

# 设置日志配置
# asctime: 时间戳
# levelname: 日志级别
# filename: 文件名
# lineno: 行号
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] %(message)s"
)

app = FastAPI(title="汉字谜盒")
SESSIONS_DIR = Path(__file__).resolve().parent / "sessions"

# 系统提示词 - 适配DeepSeek V4
SYSTEM_PROMPT = """
# 角色定义
你是一个专门玩猜字谜的AI小助手，只进行字谜互动，不闲聊无关内容，全程纯文本交互，不使用表情符号。

## 核心能力
- 出字谜、判对错、给提示
- 记忆已用谜题，确保会话内不重复
- 简洁明快回应

## 出题规则（严格执行！）
1. 开场先友好打招呼，并随机出一道常见、简单、适合大众并必须符合逻辑推理的字谜，禁止使用生僻、低俗、网络烂梗。
2. 题目格式：“谜面”（打一字）。
3. 每次出题必须完全随机，禁止重复使用相同题目，也可以偶尔穿插使用，下面示例中的谜语。
4. 新出题目时, 不要提示, 用户需要提示时, 或者答错时, 再给予合理的提示。

## 判题规则（严格执行！）
1. 用户只回复一个字时，直接视为答案。
2. 答对：立即夸奖并揭晓谜底，格式如“太棒了！就是‘X’字！要不要再来一题？”
3. 答错：告知不对，可给一句简短提示，但不泄露答案。格式如“不对哦，再想想~”
4. 严禁在用户答错后直接公布答案！只有用户说“公布答案”或“不知道”等情况时才公布。

## 互动流程
1. 用户答对：夸奖 + 确认正确 + 询问“要不要再来一题？”
2. 用户答错：告知不对 + 简单提示 + 鼓励继续猜
3. 用户说“提示一下”：给出简短线索，不公布答案
4. 用户说“公布答案”或“不知道”：揭晓谜底并解释 + 询问“要不要再来一题？”
5. 用户说“换一题”“再来一题”：立即更换新字谜

## 回复风格约束
- 语气轻松有趣，但保持简洁
- 全程只围绕字谜，拒绝回答其他问题
- 回复不超过3句话
- **绝对不要在回复中说“这个出过了，我来个新的”或类似表述** — 直接给出新谜语即可
- 判题错误零容忍，不确定谜底时，先回复“我再想想”而不是乱判

## 常见谜语类型及谜底参考示例, 仅仅为参照示例
### 组合类
- 「一加一不是二」= 王
- 「二人不是天」= 夫
- 「十口不是田」= 古

### 包含类
- 「一人在内」= 肉
- 「口里有人」= 囚
- 「门里有口」= 问
- 「田里长草」= 苗
- 「心里有你」= 您
- 「山里有山」= 出
- 「王头上有人」= 全
- 「水上有石」= 泵

### 半取类
- 「半吃半拿」= 哈
- 「半真半假」= 值
- 「半青半紫」= 素
- 「半朋半友」= 有
- 「半推半就」= 扰
- 「半山半水」= 汕

### 象形类
- 「三人又重逢」= 众
- 「一口咬掉牛尾巴」= 告
- 「两座山」= 出
- 「三日又重逢」= 晶
"""

# 根据session_id获取文件名
def get_session_file_name(session_id):
    return SESSIONS_DIR / f"{session_id}.json"

# 创建与AI大模型交互的客户端对象 (DEEPSEEK_API_KEY 环境变量的名字, 值就是DeepSeek的API_KEY的)
client = OpenAI(api_key=os.environ.get('DEEPSEEK_API_KEY'), base_url="https://api.deepseek.com")

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 生成会话标识
def generate_session_id():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# 数据模型
class ApiResponse(BaseModel):
    code: int
    message: str
    data: Any

class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.get("/")
def root():
    logging.info("欢迎使用汉字谜盒！")
    return  FileResponse("static/index.html")

# 创建新会话
@app.post("/api/sessions")
def create_session() -> ApiResponse:
    logging.info("创建新会话")
    session_id = generate_session_id()
    session_data = {
        "current_session": session_id,
        "messages": []
    }
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    with open(SESSIONS_DIR / f"{session_id}.json", "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)
    return ApiResponse(code=200, message="会话创建成功", data=session_id)

# 与AI进行对话
@app.post("/api/chat")
def chat(request: ChatRequest) -> ApiResponse:
    logging.info(f"收到消息: {request.message}，会话ID: {request.session_id}")

    # 加载json文件
    session_path = get_session_file_name(request.session_id)
    with open(session_path, "r", encoding="utf-8") as f:
        session_data = json.load(f)

    # 将用户消息添加到会话中
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for message in session_data["messages"]:
        messages.append(message)
    messages.append({"role": "user", "content": request.message})

    # 调用AI大模型进行回复
    # 这里使用DeepSeek API进行对话，实际调用时请根据DeepSeek的API文档进行调整
    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=messages,
        stream=False,
        temperature=1.5
    )

    # 获取AI回复内容
    ai_response = response.choices[0].message.content.strip()

    # 将AI回复添加到会话中
    messages.pop(0)  # 移除系统提示词
    messages.append({"role": "assistant", "content": ai_response})
    session_data["messages"] = messages

    # 保存更新后的会话数据
    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)

    return ApiResponse(code=200, message="消息接收成功", data=ai_response)

# 加载历史会话列表
@app.get("/api/sessions")
def get_sessions() -> ApiResponse:
    logging.info("加载会话列表")
    # 获取sessions目录下的所有json文件
    session_files = os.listdir(SESSIONS_DIR) if SESSIONS_DIR.exists() else []
    # 获取文件名中的会话ID
    session_ids = [f.split(".")[0] for f in session_files if f.endswith(".json")]
    session_ids.sort(reverse=True)  # 按时间倒序排列
    # 返回会话列表
    return ApiResponse(code=200, message="会话列表获取成功", data=session_ids)

# 获取指定会话的历史消息
@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> ApiResponse:
    logging.info(f"获取会话 {session_id} 的历史消息")
    session_file = get_session_file_name(session_id)
    if not session_file.exists():
        return ApiResponse(code=404, message="会话不存在", data=None)

    with open(session_file, "r", encoding="utf-8") as f:
        session_data = json.load(f)

    return ApiResponse(code=200, message="历史消息获取成功", data=session_data)

# 删除指定会话
@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str) -> ApiResponse:
    logging.info(f"删除会话 {session_id}")
    session_file = get_session_file_name(session_id)
    if not session_file.exists():
        return ApiResponse(code=404, message="会话不存在", data=None)

    os.remove(session_file)
    return ApiResponse(code=200, message="会话删除成功", data=None)

# 统一异常处理
@app.exception_handler(Exception)
def handle_exception(request, exc):
    logging.error(f"发生异常: {exc}")
    return JSONResponse(content={"code": 500, "message": "服务器内部错误", "data": None}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    # access_log 设置为False，避免在控制台输出访问日志
    uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False)
