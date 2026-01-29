# context_manager.py
from typing import List, Dict
import prompts # 导入优化后的 prompts

class ContextManager:
    """
    课堂上下文管理器：存储对话历史，提供【智能】知识检索。
    """
    def __init__(self):
        self.history: List[Dict] = []
        # 加载结构化的字典数据
        self.kg_data = prompts.COURSE_KG_DATA 

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})

    def get_context_str(self, limit: int = 6) -> str:
        recent = self.history[-limit:]
        return "\n".join([f"【{msg['role']}】: {msg['content']}" for msg in recent])

    def retrieve_kg(self, query: str) -> str:
        """
        核心优化：根据 Query 关键词，只返回相关的章节知识点。
        """
        if not query: return ""
        
        query = query.lower()
        matched_content = []
        
        # 1. 遍历图谱查找匹配项
        for chapter, topics in self.kg_data.items():
            hit = False
            # 策略A: 章节名匹配 (如 "指针")
            if any(kw in chapter for kw in query.split()): 
                hit = True
            
            # 策略B: 知识点匹配 (如 "malloc")
            # 同时也检查 query 是否包含 topic (例如 query="怎么用malloc", topic="malloc")
            for topic in topics:
                if topic.lower() in query:
                    hit = True
                    break
            
            if hit:
                # 找到匹配章节，格式化输出
                topics_str = ", ".join(topics)
                matched_content.append(f"【参考章节: {chapter}】\n包含知识点: {topics_str}")

        # 2. 如果没找到匹配的，返回空或者通用提示，避免给整个图谱
        if not matched_content:
            return "（当前问题未直接匹配到特定章节，请基于通用C语言知识回答）"
        
        # 3. 返回结果（限制最多返回2个章节，防止Context过长）
        return "\n".join(matched_content[:2])