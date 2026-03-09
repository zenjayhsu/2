# tom_agent_core.py
import json
from context_manager import ContextManager
from config import client, MODEL_NAME

class OnlineMateAgent:
    """
    OnlineMate Agent 
    废除了UCO的全局拉升，让各智能体严格执行自己在认知学徒制中的阶段性任务。
    """
    def __init__(self, name: str, role_prompt: str, context_mgr: ContextManager):
        self.name = name
        self.role_prompt = role_prompt
        self.context_mgr = context_mgr
        self.memory = f"我是{name}，C语言同伴学习小组的一员。"

    def _call_llm(self, system: str, user: str) -> str:
        try:
            res = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=0.8
            )
            return res.choices[0].message.content
        except Exception as e:
            return f"Error: {e}"

    def process(self, student_utterance: str):
        context = self.context_mgr.get_context_str()
        kg_info = self.context_mgr.retrieve_kg(student_utterance)
        
        # 读取全局学生画像
        profile = self.context_mgr.student_profile
        profile_str = self.context_mgr.get_profile_str()

        # 核心：根据不同智能体严格分配行为指令
        action_guide = ""
        if "Fundamentals Checker" in self.name:
            action_guide = "【执行 Modeling 策略】：不要提问。直接向学生展示正确的概念定义和'是什么'，为他建立初始模型。"
        elif "Insight Sparker" in self.name:
            action_guide = "【执行 Coaching 策略】：不要提问。提供一个生动的比喻，辅助学生将抽象概念形象化。"
        elif "Synthesis Expert" in self.name:
            action_guide = "【执行 Reflection 策略】：不要提问。帮学生将知识清晰化、系统化，把前文的讨论做一个结构化总结。"
        elif "Critical Challenger" in self.name:
            # 只有当此角色出场时，才开始培养高阶能力
            action_guide = "【执行 Exploration 策略（提升高阶能力）】：这是撤去保护的环节！提出一个尖锐的 Edge Case、潜在Bug或反问，把学生推向必须独立分析和评价难题的境地。"

        final_prompt = f"""
        【场景】：C语言同伴学习群聊。
        【对话历史】：\n{context}\n
        【相关参考知识】：{kg_info}
        
        {profile_str}
        
        【核心任务】：
        你是 {self.name}。请根据当前的学生画像，{action_guide}
        
        【语气与格式】：
        你是一个平等的学习同伴，不是居高临下的老师。
        字数控制在100字以内，口语化表达。
        """

        response = self._call_llm(self.role_prompt, final_prompt)
        
        # 返回生成文本和供UI展示的画像JSON
        tom_display = json.dumps(profile, ensure_ascii=False)
        return response, tom_display