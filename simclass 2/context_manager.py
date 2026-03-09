# controller.py
import json
from typing import List, Dict
from tom_agent_core import OnlineMateAgent
from config import client, MODEL_NAME

class BehaviorController:
    def __init__(self, agents: List[OnlineMateAgent], context_mgr):
        self.agents = agents
        self.context_mgr = context_mgr
        self.agent_map = {a.name: a for a in self.agents}

    def select_speaker(self, last_role: str, last_content: str) -> OnlineMateAgent:
        
        # 1. 响应点名
        if last_role == "Student":
            name_map = {
                "Insight Sparker": ["引导", "比喻", "Sparker"],
                "Fundamentals Checker": ["基础", "定义", "Checker"],
                "Synthesis Expert": ["总结", "底层", "Expert"],
                "Critical Challenger": ["提问", "挑战", "Challenger"]
            }
            for en_name, agent_instance in self.agent_map.items():
                if any(alias in last_content for alias in name_map[en_name]):
                    return agent_instance

        # 2. 助教接龙 (如果学生没说话，按照流水线自动补充)
        if last_role != "Student":
            next_agent = self._get_next_agent_in_pipeline(last_role)
            print(f"\n[控制器] 同伴流转: {last_role} -> {next_agent.name}")
            return next_agent

        # 3. 如果学生发言了 -> 触发【精准画像更新】
        print(f"\n[执行精准认知诊断] 更新学生画像...")
        new_profile_data = self._diagnose_and_update_profile(last_content)
        self.context_mgr.update_profile(new_profile_data)
        
        # 4. 基于更新后的画像，执行策略映射
        selected_agent = self._map_profile_to_agent()
        print(f"[策略执行] 诊断完成 -> 激活角色: {selected_agent.name}")
        
        return selected_agent

    def _diagnose_and_update_profile(self, content: str) -> Dict:
        """利用 LLM 基于学生的新发言，精准更新特定属性的画像"""
        context = self.context_mgr.get_context_str()
        current_profile = self.context_mgr.get_profile_str()
        
        prompt = f"""
        任务：作为教育评估专家，请根据对话历史和学生最新发言，更新学生画像。
        
        【已有画像】：
        {current_profile}
        
        【对话背景】：\n{context}\n
        【学生最新发言】："{content}"
        
        请重新评估并输出以下四个维度的JSON格式数据：
        1. "Belief": 描述学生当前脑海中对这个知识点的理解状态或存在的误区。
        2. "Intention": 描述学生当前的诉求（例如：求定义、求比喻、求验证）。
        3. "Cognitive_Level": 必须是以下之一：记忆、理解、应用、分析、评价、创造。
        4. "Emotion": 描述情绪状态，例如：困惑、平静、自信。
        
        返回JSON格式：
        {{
            "Belief": "...",
            "Intention": "...",
            "Cognitive_Level": "...",
            "Emotion": "..."
        }}
        """
        try:
            res = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            return json.loads(res.choices[0].message.content)
        except:
            return {}

    def _map_profile_to_agent(self) -> OnlineMateAgent:
        """基于全局画像的认知层级和情绪进行决策"""
        p = self.context_mgr.student_profile
        cog_level = p.get("Cognitive_Level", "记忆")
        emotion = p.get("Emotion", "困惑")
        
        # 1. 记忆阶段 或 困惑求知 -> Modeling (Checker 基础者)
        if cog_level == "记忆" or "困惑" in emotion:
            return self.agent_map["Fundamentals Checker"]
            
        # 2. 理解阶段，需要消化 -> Coaching (Sparker 引导者)
        if cog_level == "理解":
            return self.agent_map["Insight Sparker"]
            
        # 3. 应用/分析阶段，情绪稳定 -> Reflection (Expert 总结者)
        if cog_level in ["应用", "分析"] and "自信" not in emotion:
            return self.agent_map["Synthesis Expert"]
            
        # 4. 高阶认知 或 非常自信 -> Exploration (Challenger 提问者，唯一负责拔高)
        if cog_level in ["评价", "创造"] or "自信" in emotion:
            return self.agent_map["Critical Challenger"]
            
        return self.agent_map["Fundamentals Checker"]

    def _get_next_agent_in_pipeline(self, last_role_name: str) -> OnlineMateAgent:
        """学生沉默时的自动流水线"""
        pipeline = ["Fundamentals Checker", "Insight Sparker", "Synthesis Expert", "Critical Challenger"]
        for i, name in enumerate(pipeline):
            if name == last_role_name:
                next_idx = (i + 1) % len(pipeline)
                return self.agent_map[pipeline[next_idx]]
        return self.agent_map["Fundamentals Checker"]