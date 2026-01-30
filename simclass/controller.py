# controller.py
import json
import random
from typing import List
from tom_agent_core import OnlineMateAgent
from config import client, MODEL_NAME

class BehaviorController:
    def __init__(self, agents: List[OnlineMateAgent], context_mgr):
        self.agents = agents
        self.context_mgr = context_mgr
        self.agent_map = {a.name: a for a in self.agents}

    def select_speaker(self, last_role: str, last_content: str) -> OnlineMateAgent:
        
        # 映射表：支持中文名和英文名
        name_map = {
            "Insight Sparker": ["Insight Sparker", "引导者", "启发者"],
            "Fundamentals Checker": ["Fundamentals Checker", "跟随者", "基础核查者"],
            "Synthesis Expert": ["Synthesis Expert", "整合者", "综合专家"],
            "Critical Challenger": ["Critical Challenger", "提问者", "挑战者"]
        }

        # === 规则 1: 检查学生直接点名 (最高优先级) ===
        if last_role == "Student":
            for agent_en_name, agent_instance in self.agent_map.items():
                aliases = name_map.get(agent_en_name, [agent_en_name])
                # 检查所有别名是否出现在学生的话里
                if any(alias in last_content for alias in aliases):
                    # print(f"\n[控制器] 检测到学生点名: {agent_en_name}") 
                    return agent_instance

        # === 规则 2: 动态候选池 (核心逻辑) ===
        candidate_agents = list(self.agent_map.keys())
        
        candidates_for_scoring = []
        if last_role == "Student":
            # 情况 A: 学生刚说完 -> 全员开放竞争
            candidates_for_scoring = candidate_agents
        else:
            # 情况 B: 助教刚说完 (学生沉默) -> 强制换人 (Rule of Non-Repetition)
            # 如果上一个说话的是助教，他在本轮被剔除，防止连续发言
            if last_role in candidate_agents:
                candidates_for_scoring = [name for name in candidate_agents if name != last_role]
            else:
                # 异常兜底：如果识别不出last_role，全员开放
                candidates_for_scoring = candidate_agents

        # === 规则 3: LLM 评分逻辑 (增强版) ===
        context = self.context_mgr.get_context_str()
        
        # [保留您的详细描述]：让调度器理解每个角色的功能
        role_descriptions = """
        - Insight Sparker (引导者): 现在扮演的是一门 C 语言程序设计课堂讨论中的引导者。你对 C 语言的核心概念有深入理解（例如：指针、内存管理、函数调用机制、结构体、数组与字符串、编译与运行机制等），并且非常擅长把抽象的编程概念和底层机制转化为生活化、容易理解的类比和隐喻。
        - Critical Challenger (提问者与组织者): 你扮演的是一门 C 语言程序设计课堂讨论中的提问者与组织者。你的核心任务是连接学生发言和其他 AI 角色的输出，通过挖掘其中隐含的前提、概念跳跃和潜在矛盾，制造“有建设性的认知张力”，推动讨论从表层理解走向深层机制分析。你非常熟悉 C 语言中的关键模型与底层假设，例如：内存模型、指针与地址语义、数组退化规则、函数调用栈模型、变量生命周期与作用域规则等。你关注的是“模型适用边界”和“前提是否完整”。
        - Fundamentals Checker (跟随者): 你现在扮演的是一门 C 语言程序设计课堂讨论中的跟随者。你的基础知识比较扎实，但风格偏谨慎。你通常会先吸收他人的观点，再进行发言。你代表着课堂中“巩固基础、确认知识点”的角色，经常从“是否符合教材定义”和“概念是否准确”的角度提出看法。
        - Synthesis Expert (整合者): 你现在扮演的是一门 C 语言程序设计课堂讨论中的整合者。你擅长把零散的观点整理成系统化的知识网络。你对 C 语言中不同机制与技术的适用场景（如指针机制、内存分配方式、函数调用模型、数据结构组织方式等）以及它们之间的权衡关系有深入理解。
        """
        
        # 动态 Prompt
        if last_role == "Student":
            situation_desc = f"学生刚发问：'{last_content}'"
        else:
            situation_desc = f"助教【{last_role}】刚说完：'{last_content}'，现在学生保持沉默"

        prompt = f"""
        对话历史：\n{context}\n
        当前情况：{situation_desc}
        
        【助教角色定义】：
        {role_descriptions}
        
        请根据当前对话状态，判断哪个助教最适合【接话】以推动教学？
        候选名单：{candidates_for_scoring}
        
        请对【候选名单】中的每一位打分（0-10）。
        返回JSON格式：{{"Insight Sparker": 8, ...}}
        """
        
        try:
            res = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "system", "content": "你是课堂调度员，只返回JSON。"}, {"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            scores = json.loads(res.choices[0].message.content)
        except:
            # 随机兜底
            scores = {name: random.randint(1, 10) for name in candidates_for_scoring}
        
        # 打印评分结果 (保留这行很有用，可以看到谁在竞争)
        print(f"\n[控制器评分] {scores}")

        # === 规则 4: 智能阈值选择 (修改点) ===
        # 1. 过滤无效分数并排序
        valid_scores = {k: v for k, v in scores.items() if k in candidates_for_scoring}
        if not valid_scores: 
            valid_scores = {name: 5 for name in candidates_for_scoring} # 兜底

        # 降序排列 [(Name, Score), ...]
        sorted_agents = sorted(valid_scores.items(), key=lambda x: x[1], reverse=True)
        
        selected_name = ""
        
        # 2. 执行分差判断逻辑
        if len(sorted_agents) == 1:
            # 如果只有一个候选人（极端情况），直接选
            selected_name = sorted_agents[0][0]
        else:
            top1_name, top1_score = sorted_agents[0]
            top2_name, top2_score = sorted_agents[1]
            
            diff = top1_score - top2_score
            
            # 这里的 1 就是您设定的阈值
            if diff <= 1:
                selected_name = random.choice([top1_name, top2_name])
            else:
                selected_name = top1_name
        
        return self.agent_map[selected_name]