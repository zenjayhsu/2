# main.py
import json
from context_manager import ContextManager
from tom_agent_core import OnlineMateAgent
from controller import BehaviorController
from config import client, MODEL_NAME
import prompts 

def init_student_profile_via_llm(bg_input: str) -> dict:
    """系统冷启动：根据学生的第一句话生成初始画像"""
    prompt = f"""
    请根据学生提供的背景描述，初始化他的认知画像。
    背景描述："{bg_input}"
    
    返回JSON格式，包含以下严格的四个字段：
    {{
        "Belief": "客观描述学生当前的认知状态",
        "Intention": "描述学生的诉求",
        "Cognitive_Level": "记忆/理解/应用/分析/评价/创造",
        "Emotion": "困惑/平静/自信等"
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
        return {"Belief": "状态未知", "Intention": "未知", "Cognitive_Level": "记忆", "Emotion": "平静"}

def main():
    print("=== OnlineMate C语言同伴学习系统 (认知诊断版) ===")
    
    ctx_mgr = ContextManager()
    
    # --- 画像冷启动 (Cold Start) ---
    print("\n【系统冷启动】建立初始学生画像。")
    bg_input = input("👨‍🎓 请用一句话描述你现在想学习的C语言内容以及目前的理解程度：\n>> ")
    if not bg_input: 
        bg_input = "我对指针概念缺乏基本了解，感觉很抽象，希望能得到清晰的定义。"
        print(f"（默认输入: {bg_input}）")
        
    print("⏳ 正在生成初始学生画像...")
    init_profile = init_student_profile_via_llm(bg_input)
    ctx_mgr.update_profile(init_profile)
    print(ctx_mgr.get_profile_str())
    print("-" * 50)
    
    # --- 初始化 Agent 与控制器 ---
    agent_sparker = OnlineMateAgent("Insight Sparker", prompts.PROMPT_INSIGHT_SPARKER, ctx_mgr)
    agent_checker = OnlineMateAgent("Fundamentals Checker", prompts.PROMPT_FUNDAMENTALS_CHECKER, ctx_mgr)
    agent_expert = OnlineMateAgent("Synthesis Expert", prompts.PROMPT_SYNTHESIS_EXPERT, ctx_mgr)
    agent_challenger = OnlineMateAgent("Critical Challenger", prompts.PROMPT_CRITICAL_CHALLENGER, ctx_mgr)
    
    all_agents = [agent_sparker, agent_checker, agent_expert, agent_challenger]
    controller = BehaviorController(all_agents, ctx_mgr)
    
    ctx_mgr.add_message("Student", bg_input)
    last_role = "Student"
    last_content = bg_input

    # --- 进入主循环 ---
    while True:
        try:
            # A: 控制器决策
            selected_agent = controller.select_speaker(last_role, last_content)
            
            # B: 生成回复
            response, profile_display = selected_agent.process(last_content)
            
            # C: 【核心修复点】每次必定打印当前全局画像，无论学生是否发言
            print(f"\n\033[0;33m🧠 [当前全局画像依据]:\n{ctx_mgr.get_profile_str()}\033[0m")
            
            # D: 打印 AI 智能体的回复
            print(f"\n🤖 \033[1;36m{selected_agent.name}\033[0m: \n{response}\n")
            
            ctx_mgr.add_message(selected_agent.name, response)
            last_role = selected_agent.name
            last_content = response
            
            # E: 轮换
            print("-" * 60)
            next_input = input("\033[1;32m👨‍🎓 您的发言 (回车保持AI同伴接龙，'q'退出): \033[0m")
            
            if next_input.strip() == "":
                print(">> (学生保持沉默，同伴继续讨论...)")
            elif next_input.lower() == 'q':
                break
            else:
                ctx_mgr.add_message("Student", next_input)
                last_role = "Student"
                last_content = next_input
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n发生错误: {e}")
            break

if __name__ == "__main__":
    main()