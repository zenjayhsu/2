# tom_agent_core.py
import json
from context_manager import ContextManager
from config import client, MODEL_NAME
import prompts 

class OnlineMateAgent:
    """
    OnlineMate Agent - 自然对话版 (集成布鲁姆分层策略)
    """
    def __init__(self, name: str, role_prompt: str, context_mgr: ContextManager):
        self.name = name
        self.role_prompt = role_prompt
        self.context_mgr = context_mgr
        self.memory = f"初始记忆：我是{name}，我要帮助学生掌握C语言编程。"

    def _call_llm(self, system: str, user: str, json_mode: bool = False) -> str:
        try:
            kwargs = {
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                "temperature": 0.8  # 稍微调高温度，增加自然度和灵活性
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {e}"

    def process(self, student_utterance: str):
        context = self.context_mgr.get_context_str()
        kg_info = self.context_mgr.retrieve_kg(student_utterance)

        # === 阶段 1: ToM 假设生成 (识别布鲁姆层级) ===
        tom_prompt = f"""
        基于对话历史：\n{context}\n
        当前发言："{student_utterance}"
        
        请推断学生的心理状态，返回JSON。
        【重点】：请判断学生的认知层级（布鲁姆分类）：记忆/理解/应用/分析/评价/创造。
        
        返回格式：
        {{
            "Belief": "学生当前的理解...",
            "Intention": "学生想解决什么...",
            "Cognitive_Level": "记忆/理解/应用/分析/评价/创造",
            "Emotion": "自信/困惑/急切..."
        }}
        """
        mental_state_json = self._call_llm("教育心理学专家", tom_prompt, json_mode=True)
        
        # 解析层级
        try:
            ms_data = json.loads(mental_state_json)
            level_cn = ms_data.get("Cognitive_Level", "理解")
            current_level_key = prompts.BLOOM_MAPPING.get(level_cn, "Understand")
        except:
            current_level_key = "Understand"

        # === 阶段 2: 假设修正 ===
        refine_prompt = f"""
        角色：{self.name}
        设定：{self.role_prompt}
        ToM状态：{mental_state_json}
        请结合你的角色，用一句话修正对当前局势的理解。
        """
        refined_thought = self._call_llm("结合角色修正", refine_prompt)

        # === 阶段 3: 角色分流与响应生成 ===
        
        # 判断是否启用 UCO (仅引导者和挑战者启用)
        enable_uco = False
        if "Insight Sparker" in self.name or "Critical Challenger" in self.name:
            enable_uco = True
            
        final_prompt = ""
        strategy_desc = ""

        if enable_uco:
            # === 策略 A: UCO 拉升模式 (Target = Current + 1) ===
            current_conf = prompts.BLOOM_SCAFFOLD_LEVELS.get(current_level_key, prompts.BLOOM_SCAFFOLD_LEVELS["Understand"])
            target_id = min(current_conf["id"] + 1, 6) # 最高升到 6 (Create)
            
            # 查找目标 Key
            target_key = "Understand"
            for k, v in prompts.BLOOM_SCAFFOLD_LEVELS.items():
                if v["id"] == target_id:
                    target_key = k
                    break
            target_conf = prompts.BLOOM_SCAFFOLD_LEVELS[target_key]
            
            strategy_desc = f"[UCO提升] {current_conf['name']} -> {target_conf['name']}"
            print(strategy_desc)
            
            # 构建“非直接回答”的 Prompt
            instruction = ""
            if "Insight Sparker" in self.name:
                instruction = f"请使用**比喻或启发式提问**，引导学生进入【{target_conf['name']}】层级。不要直接给代码，要让他顿悟。"
            else: # Challenger
                instruction = f"请提出一个犀利的**反例或质疑**，迫使学生进行【{target_conf['name']}】层级的思考。指出他逻辑中的漏洞。"

            final_prompt = f"""
            【场景】：同伴小组讨论协作学习。
            【对话历史】：{context}
            【你的思考】：{refined_thought}
            
            【核心指令】：
            1. **自然对话**：像真人一样说话！严禁使用列表、Markdown标题或僵硬的格式。
            2. **承接上下文**：自然地接过话茬。
            3. **策略执行**：{instruction} (操作定义：{target_conf['guide']})
            
            请作为【{self.name}】回复 (100字以内)。
            """

        else:
            # === 策略 B: 直接响应模式 (Checker & Expert) ===
            strategy_desc = "[直接响应] 提供干货/总结"
            print(f"{strategy_desc} - {self.name}")
            
            instruction = ""
            if "Fundamentals Checker" in self.name:
                instruction = "请直接给出**准确的代码片段或语法修正**。务实、严谨，帮学生解决具体问题。"
            else: # Expert
                instruction = "请从**底层原理(内存/系统)**角度进行总结。将之前的讨论升华，给出一个权威定论。"

            final_prompt = f"""
            【场景】：同伴小组讨论协作学习。
            【对话历史】：{context}
            【知识库参考】：{kg_info}
            
            【核心指令】：
            1. **自然对话**：像真人一样说话！严禁使用列表或僵硬格式。
            2. **直接回答**：{instruction}
            3. **语气**：亲切但专业，不要有机械感。
            
            请作为【{self.name}】回复 (100字以内)。
            """

        # 生成回复
        response = self._call_llm(self.role_prompt, final_prompt)
        
        # 更新状态用于显示
        try:
            ms = json.loads(mental_state_json)
            ms["Strategy"] = strategy_desc
            mental_state_json = json.dumps(ms, ensure_ascii=False)
        except: pass

        return response, mental_state_json