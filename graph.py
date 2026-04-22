from typing import Annotated, Literal
from pydantic import Field
from langgraph.graph import START, StateGraph,END,START
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AnyMessage
from langchain.agents import AgentState
import asyncio
import asyncio
from pydantic import BaseModel
from langgraph.graph.message import add_messages
import os
# from tingwu import Tingwu
class CustomState(AgentState):
    summary: Annotated[list[AnyMessage], add_messages] 
    suggestion: str = ""
    original_text: str = ""#转写稿
    status: Literal["allow", "reject"] = "allow"
    question: str = ""
    num: int = 0
    
def get_llm():
    return ChatOpenAI(
        model_name=os.getenv("MODEL_NAME"),
        base_url=os.getenv("BASE_URL"),
        api_key=os.getenv("API_KEY"),
        temperature=0.4,
        extra_body={
            "enable_thinking": True,
            "thinking_budget": 4000
        }
    )

def get_llm_structure():
    return ChatOpenAI(
        model_name=os.getenv("MODEL_NAME"),
        base_url=os.getenv("BASE_URL"),
        api_key=os.getenv("API_KEY"),
        temperature=0.2,
        extra_body={
            "enable_thinking": True,
            "thinking_budget": 4000
        }
    )

class Review_Summary_structure(BaseModel):
    suggestion: str = Field(description="对总结内容的建议和不通过的原因,键名必须是suggestion")
    status: Literal["allow", "reject"] = Field(description="总结的信息是否通过审核,若不通过,则为reject,若通过,则为allow,键名必须是status")


async def summary_node(state: CustomState) -> CustomState:
    print("summary_node start")
    SYSTEM_PROMPT ="""
是一位资深的、富有耐心的理科教师和课程设计师。你的任务是将一份带有时间戳的音视频转写稿，转化为一份结构清晰、内容详尽、包含教学、练习与测验的 Markdown 学习笔记，旨在帮助一位零基础的学习者完全掌握课程内容,会严格遵从指令.
"""
    
    if not state.get("summary",[]):
        HUMANMESSAGE = f"""
    角色
    你是一位资深的、富有耐心的理科教师和课程设计师。你的任务是将一份带有时间戳的音视频转写稿，转化为一份结构清晰、内容详尽、包含教学、练习与测验的 Markdown 学习笔记，旨在帮助一位零基础的学习者完全掌握课程内容。

    目标
    分析我提供的音视频转写稿，按照“讲解 → 技巧 → 讲师例题剖析 → 练习 → 小测 → 解析”的流程，系统性地教授稿件中的所有知识点和题型，确保讲师提到的所有例题都被完整讲解。

    输入格式
    一份单人演讲的音视频转写稿（.txt 文件）。文件中的每一行遵循以下格式：
    [秒级别时间戳] 发言内容
    例如：[120s] 先看第三幅图，这幅图很简单...

    核心工作流程
    你需要将整个转写稿内容看作一个完整的课程，并按照逻辑上的知识单元（例如，一个实验、一个概念、一道例题的讲解）进行划分。对每一个知识单元，严格遵循以下全新的步骤进行处理：

    知识点讲解 (Concept Explanation)

    综合该知识单元内的讲师发言，用你自己的语言，以清晰、系统、由浅入深的方式进行讲解。
    解释所有专业术语和背景概念。
    技巧归纳与原理剖析 (Techniques & Principles)

    如果讲师提到了任何解题技巧、快捷方法或重要结论，在此处专门列出。
    深入解释这些技巧或结论的底层原理（若讲稿中提及）。
    讲师例题深度剖析 (Lecturer's Example Analysis) - [新增核心环节]

    识别并呈现：从讲稿中找出该知识单元内讲师讲解的所有例题。将题目清晰地呈现出来。
    步骤化解析：提供比讲师更详细、更步骤化的解题过程。不仅要说明“怎么做”，更要解释“为什么这么做”。
    关联技巧：在解题步骤中，如果用到了步骤2中归纳的技巧，必须明确指出：“此处应用了『XX技巧』”。
    插入关键图片：如果例题的讲解严重依赖某个图表或示意图，请在此处插入最关键的一张图片。
    随堂练习 (Practice Problems)

    基于刚刚剖析的讲师例题，设计1-2道高度相似的练习题，让学习者可以模仿和巩固。
    学习检测 (Quick Quiz)

    设计1-2道选择题或判断题，用于快速检验学习者对核心概念的掌握情况。
    答案与深度解析 (Answers & Detailed Analysis)

    首先，清晰地提供 学习检测 (Quick Quiz) 和 随堂练习 (Practice Problems) 的答案。
    然后，为所有题目提供详尽的解析，解题思路要清晰，步骤要完整。
    输出要求与格式规范
    整体格式: 必须使用纯 Markdown 格式输出。
    结构化: 使用 Markdown 的各级标题（#, ##, ###）来组织内容。
    特殊标记:但遇到一些难以用语言表达的内容,你需要用用特定格式进行标记,每次教学最少要有一处标记,标记格式为<time_image_start>秒级别时间戳</end>,每次使用这个标记的时候必须在那一行里只能由这个标签,程序在后续会自动将音视频对应的视频在那一刻的图片插到你的输出中去
        - 例如一下场景:当遇到一道解析几何时,几何形状难以用语言描述,则可以使用该格式进行标记。以下为案例:
            - ......接下来要讲解的是一道圆锥曲线大题,题目请看图:(在这换行)<time_image_start>120</end>(在这换行)
    语言与翻译 (新增规则): 讲稿中出现的任何英文句子或关键术语，都应在原文后用括号提供其中文翻译。例如：The key is to find the equilibrium point (关键是找到平衡点)。
    原创性与完整性: 严禁直接复制粘贴讲师的原文。必须处理转写稿的全部内容，确保覆盖所有知识点和所有讲师例题。
    注意:当遇到代码讲解但你又不确定代码是什么时,你需要根据转写稿的讲师发言写出差不多的教学和代码,以让用户更好的理解。
    结束标记: 在你的回答完全结束后，必须在最后单独另起一行输出 ``，这是任务完成的唯一标志。

            转写稿如下:
            {state["original_text"]}

          """
    else:
        HUMANMESSAGE = f"""
        修改建议如下,请根据建议并结合上文完整输出整个教学模块,包括特殊标记((这里换行)<time_image_start>秒级时间戳</end>(这里换行))也要输出,且必须保证每次输出必须存在最少一个特殊标记,并且特殊标记必须单独占一行,如其他内容\n<time_image_start>120</end>\n其他内容
        {state["suggestion"]}
        """
    summary = await get_llm().ainvoke([SystemMessage(content=SYSTEM_PROMPT)]+state.get("summary",[])+[HumanMessage(content=HUMANMESSAGE)])
    print(f"\nsummary done:\n{summary}\n")
    return {"summary": [HumanMessage(content=HUMANMESSAGE),summary]}
 
async def review_node(state: CustomState) -> CustomState:
    print("review_node start")
    summary_text = state["summary"][-1].content if state["summary"] else ""
    SYSTEM_PROMPT = """
你是一名审核员,你的输出格式只能是两种情况:
1:{"status":"allow","suggestion":""}
2:{"status":"reject","suggestion":"你要在这里填为什么为什么不予通过"}
不允许出现这两种情况之外的任何情况,绝不允许加入其他键值对,只能是这两种情况.
"""
    HUMANMESSAGE = f"""
    以json格式输出,死守输出格式,绝不允许私自修改输出格式.
    以json格式输出,死守输出格式,绝不允许私自修改输出格式,绝不允许私自加入其他键值对.
    你的输出格式只能是两种情况:
    1:{{"status":"allow","suggestion":""}}
    2:{{"status":"reject","suggestion":"你要在这里填为什么为什么不予通过"}}
    视频总结如下:
    {summary_text}

    原文如下:
    {state["original_text"]}
    """
    review_structured_output = get_llm_structure().with_structured_output(Review_Summary_structure)
    response = await review_structured_output.ainvoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=HUMANMESSAGE)])
    print(f"\nreview_node done,content:{response}\n")
    return {"suggestion": response.suggestion,"status": response.status,"num": state["num"] + 1}

def condition(state: CustomState) -> str:
    if state["status"] == "allow" or state["num"] > 2:
        return "allow"
    else:
        return "reject"


async def change_state(state: CustomState) -> CustomState:
    return {"status": "reject","suggestion": "","num": 0}

async def ai_set_question(state: CustomState) -> CustomState:
    summary_text = state["summary"][-1].content if state["summary"] else ""
    SYSTEMMESSAGE = """你是专业出题老师,根据我向你提供的markdown内容,设计贴合内容的题目,难度不要太高,以基础为主"""
    
    suggestion = state.get("suggestion", "")
    if not suggestion:
        HUMANMESSAGE = f"""
        markdown如下:
        {summary_text}
        请根据markdown内的内容进行出题,需要给出深度解析,答案在最后写,以markdown的形式输出
        """
    else:
        HUMANMESSAGE = f"""
        上次出题存在问题,修改建议如下:
        {suggestion}
        
        原始markdown内容如下:
        {summary_text}
        请根据修改建议重新出题,需要给出深度解析,答案在最后写,以markdown的形式输出,需要完整输出所有内容
        """
    
    question = await get_llm().ainvoke([SystemMessage(content=SYSTEMMESSAGE), HumanMessage(content=HUMANMESSAGE)])
    return {"question": question.content}

async def review_question(state: CustomState) -> CustomState:
    SYSTEMPROMPT = """请以json格式输出.你的任务是审核题目与答案是否有误,若误,则需要在suggestion字段说明理由以及修改建议并且设置status字段为reject,若无误,则status字段设置为allow,suggestion字段为空字符串
    你是一名审核员,你的输出格式只能是两种情况:
1:{"status":"allow","suggestion":""}
2:{"status":"reject","suggestion":"你要在这里填为什么为什么不予通过"}
不允许出现这两种情况之外的任何情况,绝不允许加入其他键值对,只能是这两种情况.
    """
    HUMANMESSAGE = f"""
    以json格式输出,死守输出格式,绝不允许私自修改输出格式,绝不允许私自加入其他键值对.
    你的输出格式只能是两种情况:
    1:{{"status":"allow","suggestion":""}}
    2:{{"status":"reject","suggestion":"你要在这里填为什么为什么不予通过,已经正确的解题流程"}}
    题目与答案如下:
    {state["question"]}
    """
    llm_with_structured = get_llm_structure().with_structured_output(Review_Summary_structure)
    response = await llm_with_structured.ainvoke([SystemMessage(content=SYSTEMPROMPT), HumanMessage(content=HUMANMESSAGE)])
    print(f"\nreview_question done,content:{response}\n")
    return {"suggestion": response.suggestion,"status": response.status,"num": state["num"] + 1}
    


def Graph_Main():
    builder = StateGraph(CustomState)
    builder.add_node("summary_node",summary_node)
    builder.add_node("review_node",review_node)
    builder.add_node("ai_set_question",ai_set_question)
    builder.add_node("change_state",change_state)
    builder.add_node("review_question",review_question)
    builder.add_edge(START,"summary_node")
    builder.add_edge("summary_node","review_node")
    builder.add_conditional_edges("review_node",
                                  condition,
                                  {
                                      "allow":"change_state",
                                      "reject":"summary_node"
                                  })
    builder.add_edge("change_state","ai_set_question")
    builder.add_edge("ai_set_question","review_question")
    builder.add_conditional_edges("review_question",
                                  condition,
                                  {
                                      "allow":END,
                                      "reject":"ai_set_question"
                                  })
    graph = builder.compile()
    return graph

# graph = Graph_Main()

async def main(full_text:str):
    graph = Graph_Main()
    mermaid_code = graph.get_graph().draw_mermaid()
    print(mermaid_code)
    result = await graph.ainvoke(
            input={
            "original_text": full_text,
            "summary": [],
            "suggestion": "",
            "status": "allow",
            "question": "",
            "num": 0,
        },
    )
    markdown_text = result["summary"][-1].content + "\n" + result["question"]
    print(f"\nmarkdown_text:\n{markdown_text}\n")
    return markdown_text

    # print(f"\n最后拿到的结果:\n{result}\n")

if __name__ == "__main__":
    test = """
    [5s] 好，同学们，上课了，今天我们来讲二次函数和一元二次方程的求解。
[12s] 首先回顾一下，什么是二次函数？形如 f(x) = ax² + bx + c，其中 a 不等于零，这就是一个二次函数。
[25s] a 不等于零这个条件非常关键，如果 a 等于零，那就退化成一次函数了，大家注意。
[35s] 那二次函数的图像是什么？是一条抛物线。a 大于零的时候开口朝上，a 小于零的时候开口朝下。
[48s] 我们把这个抛物线的最高点或者最低点叫做顶点，顶点坐标公式是 (-b/2a, (4ac-b²)/4a)。
[62s] 好，大家把这个公式记一下，非常重要，后面会反复用到。
[78s] 接下来讲一元二次方程，也就是 ax² + bx + c = 0 的求解。
[90s] 最核心的工具就是求根公式：x = (-b ± √(b²-4ac)) / 2a。
[105s] 这里面 b²-4ac 这个东西我们给它一个名字，叫做判别式，用希腊字母 Δ 来表示，delta。
[120s] Δ 的取值决定了方程有几个实数根。Δ 大于零，两个不相等的实数根。
[132s] Δ 等于零，两个相等的实数根，也就是只有一个根。Δ 小于零，没有实数根。
[148s] 好，这个是基本概念，接下来我们看第一道例题。
[160s] 例题一：求方程 2x² - 5x + 3 = 0 的解。
[172s] 首先我们识别系数，a 等于 2，b 等于 -5，c 等于 3。
[185s] 先算判别式，Δ = b² - 4ac = 25 - 24 = 1，大于零，所以有两个不相等的实数根。
[200s] 代入求根公式，x = (5 ± √1) / 4 = (5 ± 1) / 4。
[212s] 所以 x₁ = 6/4 = 3/2，x₂ = 4/4 = 1。答案就是 x 等于 3/2 或者 x 等于 1。
[228s] 大家注意，这道题其实也可以用十字相乘法来做，2x² - 5x + 3 可以分解成 (2x-3)(x-1) = 0。
[245s] 所以如果能因式分解的话，因式分解比求根公式更快，这是一个技巧。
[260s] 好，我们看第二道例题，这道稍微复杂一点。
[272s] 例题二：已知方程 x² - 2mx + m + 2 = 0 有两个实数根，求 m 的取值范围。
[288s] 这道题的关键在哪里？题目说"有两个实数根"，那就意味着 Δ ≥ 0。
[302s] 我们来算，a = 1，b = -2m，c = m + 2。
[315s] Δ = (-2m)² - 4(1)(m+2) = 4m² - 4m - 8 ≥ 0。
[330s] 化简一下，m² - m - 2 ≥ 0，再因式分解，(m-2)(m+1) ≥ 0。
[345s] 画个数轴来看一下，这是一个开口朝上的抛物线，零点在 m = -1 和 m = 2。
[358s] 所以解集是 m ≤ -1 或者 m ≥ 2，这就是 m 的取值范围。
[375s] 大家看到了吗？这道题的核心技巧就是把"有实数根"这个条件翻译成 Δ ≥ 0，然后解一个关于参数的不等式。
[392s] 这个思路叫做"参数讨论法"，以后遇到含参数的方程一定要想到这个方法。
[408s] 好，接下来我们讲韦达定理，也叫根与系数的关系。
[420s] 如果 x₁ 和 x₂ 是方程 ax² + bx + c = 0 的两个根，那么 x₁ + x₂ = -b/a，x₁ · x₂ = c/a。
[438s] 这个定理非常有用，很多题目不需要你真的把根解出来，只要知道根的和与积就够了。
[455s] 来看例题三：已知方程 x² - 3x + 1 = 0 的两个根是 x₁ 和 x₂，求 x₁² + x₂² 的值。
[472s] 我们不需要解方程。由韦达定理，x₁ + x₂ = 3，x₁ · x₂ = 1。
[488s] 而 x₁² + x₂² = (x₁ + x₂)² - 2x₁x₂ = 9 - 2 = 7。答案就是 7。
[505s] 大家看，这道题如果你硬算根再平方再相加，多麻烦。用韦达定理三步搞定。
[520s] 记住这个恒等式：x₁² + x₂² = (x₁ + x₂)² - 2x₁x₂，考试高频考点。
[535s] 好，今天的课就到这里，作业是课本第 87 页的第 3、5、8 题，下课。
    """
    asyncio.run(main(test))
