# main.py
from context_manager import ContextManager
from tom_agent_core import OnlineMateAgent
from controller import BehaviorController
import prompts 

def main():
    print("=== OnlineMate C语言实验课 (交互模式) ===")
    print("说明：")
    print("1. 输入您的问题并回车，开启讨论。")
    print("2. 在每一轮回复后，您可以选择【输入内容插话】或【直接回车保持沉默】。")
    print("3. 如果您保持沉默，其他助教将自动接话（智能体接龙）。")
    print("4. 输入 'q' 退出。\n")
    
    # 1. 初始化系统
    ctx_mgr = ContextManager()
    
    # 初始化 Agents (加载 prompts.py 中的 C语言设定)
    agent_sparker = OnlineMateAgent("Insight Sparker", prompts.PROMPT_INSIGHT_SPARKER, ctx_mgr)
    agent_checker = OnlineMateAgent("Fundamentals Checker", prompts.PROMPT_FUNDAMENTALS_CHECKER, ctx_mgr)
    agent_expert = OnlineMateAgent("Synthesis Expert", prompts.PROMPT_SYNTHESIS_EXPERT, ctx_mgr)
    agent_challenger = OnlineMateAgent("Critical Challenger", prompts.PROMPT_CRITICAL_CHALLENGER, ctx_mgr)
    
    all_agents = [agent_sparker, agent_checker, agent_expert, agent_challenger]
    
    # 注意：请确保 controller.py 已经更新为支持 (last_role, last_content) 参数的版本
    controller = BehaviorController(all_agents, ctx_mgr)
    
    # 2. 初始状态
    last_role = "System"
    last_content = "C语言实验课开始"
    
    # === 用户第一次输入 ===
    try:
        user_input = input("\n\033[1;32m👨‍🎓 请提出你想讨论的C语言问题: \033[0m")
        if not user_input: user_input = "你好，请介绍一下C语言的指针。" # 默认输入
    except KeyboardInterrupt:
        return

    ctx_mgr.add_message("Student", user_input)
    last_role = "Student"
    last_content = user_input

    # === 进入交互循环 ===
    while True:
        try:
            # --- 步骤 A: 控制器决定谁发言 ---
            # 根据“上一句是谁说的”以及“说了什么”来决定
            selected_agent = controller.select_speaker(last_role, last_content)
            print(f"\n👉 系统调度: 决定由 [{selected_agent.name}] 接话...")
            
            # --- 步骤 B: Agent 思考并生成回复 ---
            # 获取 回复文本 和 ToM分析
            response, tom_analysis = selected_agent.process(last_content)
            
            # --- 步骤 C: 打印思维过程 (显式展示 ToM) ---
            print(f"\n\033[0;33m🧠 [{selected_agent.name}] 的心理理论 (ToM) 分析:\033[0m")
            print(f"\033[0;33m{tom_analysis}\033[0m")
            
            # --- 步骤 D: 打印回复内容 ---
            print(f"\n🤖 \033[1;36m{selected_agent.name}\033[0m: \n{response}\n")
            
            # 记录到历史
            ctx_mgr.add_message(selected_agent.name, response)
            
            # 更新状态：现在的“上一句”变成了这个Agent说的话
            last_role = selected_agent.name
            last_content = response
            
            # --- 步骤 E: 话轮转换 (Turn-taking) ---
            print("-" * 60)
            next_input = input("\033[1;32m👨‍🎓 您的轮次 (输入内容发言，或直接【回车】让AI继续讨论): \033[0m")
            
            if next_input.strip() == "":
                # 情况 1: 用户回车 -> 用户沉默 -> 循环继续
                # 控制器将看到 last_role 是某个Agent，从而安排另一个Agent来接话
                print(">> (学生保持沉默，正在倾听...)")
                pass 
                
            elif next_input.lower() == 'q':
                print("退出讨论。")
                break
                
            else:
                # 情况 2: 用户输入了内容 -> 用户插话
                ctx_mgr.add_message("Student", next_input)
                # 更新状态为用户发言，下一轮控制器将优先回应用户
                last_role = "Student"
                last_content = next_input
                
        except KeyboardInterrupt:
            print("\n程序已终止。")
            break
        except Exception as e:
            print(f"\n发生错误: {e}")
            break

if __name__ == "__main__":
    main()