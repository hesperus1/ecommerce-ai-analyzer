import streamlit as st
import time
import pandas as pd
from intent_router import route_intent
from text_to_sql import text_to_sql
from data_analysis_agent import execute_sql_with_error_handling, ai_attribution_analysis

# 页面配置
st.set_page_config(
    page_title="电商数据智能分析平台",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 样式
st.markdown("""
<style>
    /* 主内容区 - 修复侧边栏遮挡 */
    .main-content {
        padding: 20px;
        padding-bottom: 100px;
        max-width: 900px;
        margin: 0 auto;
    }
    
    /* 用户消息气泡 - 靠右对齐 */
    .user-message {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 12px;
        padding-right: 10px;
    }
    
    .user-bubble {
        background-color: #3b82f6;
        color: white;
        padding: 10px 16px;
        border-radius: 18px;
        border-bottom-right-radius: 4px;
        max-width: 60%;
        word-break: break-word;
        font-size: 14px;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2);
        display: inline-block;
        width: fit-content;
    }
    
    /* 助手消息气泡 - 靠左对齐 */
    .assistant-message {
        display: block;
        padding-left: 10px;
    }
    
    .assistant-bubble {
        background-color: #f1f5f9;
        color: #334155;
        padding: 10px 16px;
        border-radius: 18px;
        border-bottom-left-radius: 4px;
        max-width: 60%;
        word-break: break-word;
        font-size: 14px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        display: inline-block;
        width: fit-content;
    }
    
    /* 步骤容器 */
    .step-box {
        background-color: #f8fafc;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 8px;
        border-left: 3px solid #94a3b8;
        margin-left: 10px;
    }
    
    .step-box.processing {
        border-left-color: #3b82f6;
        background-color: #eff6ff;
    }
    
    .step-box.completed {
        border-left-color: #22c55e;
        background-color: #f0fdf4;
    }
    
    .step-box.error {
        border-left-color: #ef4444;
        background-color: #fef2f2;
    }
    
    .step-title {
        font-weight: 500;
        color: #334155;
        font-size: 14px;
    }
    
    /* 分析卡片 */
    .analysis-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        margin-top: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        border: 1px solid #e2e8f0;
    }
    
    /* 简单卡片 - 用于无关闲聊和知识问答 */
    .simple-card {
        background-color: #f1f5f9;
        color: #334155;
        padding: 12px 18px;
        border-radius: 18px;
        border-bottom-left-radius: 4px;
        max-width: 70%;
        word-break: break-word;
        font-size: 14px;
    }
    
    /* 思考指示器 */
    .thinking-indicator {
        background-color: #eff6ff;
        color: #1e40af;
        padding: 10px 16px;
        border-radius: 18px;
        border-bottom-left-radius: 4px;
        font-size: 14px;
        display: inline-block;
    }
    
    /* 侧边栏样式 */
    .sidebar-section {
        margin-bottom: 20px;
    }
    
    .sidebar-title {
        font-size: 14px;
        font-weight: 600;
        color: #334155;
        margin-bottom: 10px;
        padding-bottom: 8px;
        border-bottom: 2px solid #e2e8f0;
    }
    
    /* 操作按钮 */
    .action-btn {
        display: flex;
        gap: 8px;
        margin-top: 12px;
        margin-left: 10px;
    }
    
    .action-btn-simple {
        display: flex;
        gap: 8px;
        margin-top: 4px;
    }
    
    .btn {
        padding: 6px 16px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 500;
        border: none;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .btn-retry {
        background-color: #3b82f6;
        color: white;
    }
    
    .btn-retry:hover {
        background-color: #2563eb;
    }
    
    .btn-stop {
        background-color: #f87171;
        color: white;
    }
    
    .btn-stop:hover {
        background-color: #ef4444;
    }
    
    /* 聊天输入框 - 跟随内容区布局 */
    .stChatInput {
        padding: 12px;
        background: white;
        border-top: 1px solid #e2e8f0;
    }
    
    /* 修复 Streamlit 默认样式 */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# 初始化会话状态
if "messages" not in st.session_state:
    st.session_state.messages = []

if "processing" not in st.session_state:
    st.session_state.processing = False

if "current_question" not in st.session_state:
    st.session_state.current_question = ""

if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False

# 从 Streamlit Secrets 读取 API Key 和模型配置（部署到 Streamlit Community Cloud 时使用）
try:
    API_KEY = st.secrets["SILICONFLOW_API_KEY"]
    DEFAULT_MODEL = st.secrets.get("DEFAULT_MODEL", "Qwen/Qwen3.5-9B")
except KeyError:
    API_KEY = ""
    DEFAULT_MODEL = "Qwen/Qwen3.5-9B"

# 检查 API Key 是否配置
if not API_KEY:
    st.error("❌ 请在系统配置中填入 API Key")
    st.markdown("""
    **配置说明：**
    1. 创建 `.streamlit/secrets.toml` 文件
    2. 添加配置：`SILICONFLOW_API_KEY = "your-api-key-here"`
    3. 部署到 Streamlit Community Cloud 时，在 Secrets 管理中配置
    """)
    st.stop()

if "api_key" not in st.session_state:
    st.session_state.api_key = API_KEY

if "model_name" not in st.session_state:
    st.session_state.model_name = DEFAULT_MODEL

# 页面标题
st.markdown('<h1 style="text-align: center; font-size: 2rem; font-weight: 700; color: #1e40af; margin-bottom: 0.5rem;">📊 电商数据智能分析平台</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; font-size: 1rem; color: #64748b; margin-bottom: 1.5rem;">自然语言提问 → 自动生成 SQL → 智能归因分析</p>', unsafe_allow_html=True)
st.markdown("---")

# 侧边栏
with st.sidebar:
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title"> 分析维度</div>', unsafe_allow_html=True)
    dimensions = [
        "📈 漏斗分析",
        "💰 ROI 分析", 
        "🔍 异常检测",
        "📉 花费分析",
        "🎯 点击率",
        "💯 转化率",
        "🏷️ GMV 分析",
        "📦 订单分析"
    ]
    for dim in dimensions:
        st.markdown(f'<div style="padding: 6px 0; color: #64748b; font-size: 13px;">{dim}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">🎯 示例问题</div>', unsafe_allow_html=True)
    
    example_questions = [
        "分析引力魔方最近 3 天的漏斗流失情况",
        "查询各渠道的 ROI 排名",
        "检查最近 3 天有没有异常数据",
        "哪个计划的点击率最低？",
        "分析直通车最近 7 天的花费趋势"
    ]
    
    for i, question in enumerate(example_questions):
        if st.button(question, key=f"example_{i}", use_container_width=True):
            st.session_state.example_input = question
    
    st.markdown('</div>', unsafe_allow_html=True)

# 主界面 - 对话区域
st.markdown("### 💬 智能对话分析")
st.markdown("---")
st.markdown('<div class="main-content">', unsafe_allow_html=True)

# 显示历史消息
for idx, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        # 用户消息 - 靠右对齐
        st.markdown('<div class="user-message">', unsafe_allow_html=True)
        st.markdown(f'<div class="user-bubble">{msg["content"]}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # 获取意图分类
        intent_category = msg.get("intent_category", "")
        intent_route = msg.get("intent_route", "")
        
        # ========== 分支 1: 无关闲聊 - 直接渲染文本，无任何多余容器 ==========
        if intent_category == "IRRELEVANT":
            st.markdown(f'<div class="simple-card">{msg.get("analysis", "")}</div>', unsafe_allow_html=True)
        
        # ========== 分支 2: 知识问答 - 直接渲染文本 ==========
        elif intent_category == "KNOWLEDGE_QA":
            knowledge_qa_status = msg.get("knowledge_qa_status", "")
            
            if knowledge_qa_status == "processing":
                # 思考中状态
                st.markdown('<div class="thinking-indicator">💡 正在思考解答...</div>', unsafe_allow_html=True)
            elif knowledge_qa_status == "completed":
                # 完成状态 - 直接渲染答案
                st.markdown(f'<div class="simple-card">{msg.get("analysis", "")}</div>', unsafe_allow_html=True)
        
        # ========== 分支 3: 数据查询 - 使用结构化容器 ==========
        elif intent_category == "DATA_QUERY" or intent_route == "processing":
            st.markdown('<div class="assistant-message">', unsafe_allow_html=True)
            
            # 意图路由阶段
            if intent_route == "processing":
                st.markdown(f'<div class="step-box processing">', unsafe_allow_html=True)
                st.markdown(f'<div class="step-title">🎯 正在识别意图...</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True) 
                continue
            
            # 数据查询完整步骤
            elif intent_category == "DATA_QUERY":
                # SQL 步骤
                sql_status = msg.get("sql_status", "")
                if sql_status:
                    st.markdown(f'<div class="step-box {sql_status}">', unsafe_allow_html=True)
                    st.markdown(f'<div class="step-title"> SQL{" 生成中..." if sql_status == "processing" else " 生成完成"}</div>', unsafe_allow_html=True)
                    if sql_status == "completed" and "sql" in msg:
                        with st.expander("查看 SQL 代码"):
                            st.code(msg["sql"], language="sql")
                    elif sql_status == "error":
                        st.error("SQL 生成失败")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # 数据查询步骤
                if sql_status in ["completed", "error"]:
                    data_status = msg.get("data_status", "")
                    st.markdown(f'<div class="step-box {data_status}">', unsafe_allow_html=True)
                    st.markdown(f'<div class="step-title">📊 数据{" 查询中..." if data_status == "processing" else " 查询完成"}</div>', unsafe_allow_html=True)
                    if data_status == "completed" and "data" in msg:
                        with st.expander("查看查询结果"):
                            try:
                                df = pd.DataFrame(msg["data"]["data"], columns=msg["data"]["columns"])
                                st.dataframe(df, use_container_width=True)
                            except:
                                st.write(msg["data"])
                    elif data_status == "error":
                        st.error("数据查询失败")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # 分析步骤
                data_status = msg.get("data_status", "")
                analysis_status = msg.get("analysis_status", "")
                if data_status in ["completed", "error"]:
                    st.markdown(f'<div class="step-box {analysis_status}">', unsafe_allow_html=True)
                    st.markdown(f'<div class="step-title">🤖 AI{" 分析中..." if analysis_status == "processing" else " 分析完成"}</div>', unsafe_allow_html=True)
                    if analysis_status == "completed" and "analysis" in msg:
                        # 使用 st.markdown 直接渲染 Markdown 内容，确保标题正确解析
                        st.markdown("📋 **分析报告**")
                        st.markdown(msg["analysis"])
                    elif analysis_status == "error":
                        st.error("AI 分析失败")
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # 关闭 assistant-message 容器
            st.markdown('</div>', unsafe_allow_html=True)
        
        # ========== 操作按钮（根据分支使用不同样式） ==========
        is_finished = False
        
        if intent_category == "IRRELEVANT":
            is_finished = intent_route == "completed"
        elif intent_category == "KNOWLEDGE_QA":
            knowledge_qa_status = msg.get("knowledge_qa_status", "")
            is_finished = knowledge_qa_status in ["completed", "error"]
        elif intent_category == "DATA_QUERY":
            analysis_status = msg.get("analysis_status", "")
            is_finished = analysis_status in ["completed", "error"]
        
        if is_finished:
            # 根据意图分类选择不同的按钮容器样式
            btn_container_class = "action-btn" if intent_category == "DATA_QUERY" else "action-btn-simple"
            st.markdown(f'<div class="{btn_container_class}"></div>', unsafe_allow_html=True)
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button(f"🔄 重试", key=f"retry_{idx}", use_container_width=True):
                    st.session_state.current_question = st.session_state.messages[idx-1]["content"]
                    st.session_state.processing = True
                    st.session_state.messages.pop(idx)
                    assistant_msg = {
                        "role": "assistant",
                        "intent_route": "processing",
                        "intent_category": "",
                        "sql_status": "",
                        "data_status": "",
                        "analysis_status": ""
                    }
                    st.session_state.messages.append(assistant_msg)
                    st.rerun()
            with col2:
                if st.button(f"🗑️ 删除", key=f"delete_{idx}", use_container_width=True):
                    st.session_state.messages.pop(idx)
                    st.session_state.messages.pop(idx-1)
                    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# 处理示例输入
user_input = None
if hasattr(st.session_state, 'example_input') and st.session_state.example_input:
    user_input = st.session_state.example_input
    del st.session_state.example_input

# 聊天输入框（放在底部）
user_input = st.chat_input("请输入您的业务问题，例如：分析引力魔方最近 3 天的漏斗流失情况") or user_input

# 处理用户输入
if user_input and not st.session_state.processing:
    st.session_state.processing = True
    st.session_state.current_question = user_input
    st.session_state.stop_requested = False
    
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    assistant_msg = {
        "role": "assistant",
        "intent_route": "processing",  # 意图路由状态
        "intent_category": "",  # 分类结果：IRRELEVANT/KNOWLEDGE_QA/DATA_QUERY
        "sql_status": "",
        "data_status": "",
        "analysis_status": ""
    }
    st.session_state.messages.append(assistant_msg)
    
    st.rerun()

# 如果正在处理，执行分析流程
if st.session_state.processing and len(st.session_state.messages) > 0:
    last_msg = st.session_state.messages[-1]
    current_question = st.session_state.get("current_question", "")
    
    # 检查是否收到终止请求
    if st.session_state.stop_requested:
        last_msg["sql_status"] = "error"
        last_msg["data_status"] = "error"
        last_msg["analysis_status"] = "error"
        st.session_state.processing = False
        st.session_state.stop_requested = False
        st.rerun()
    
    # ========== 意图路由阶段 ==========
    if last_msg.get("role") == "assistant" and last_msg.get("intent_route") == "processing":
        # 步骤 1: 意图路由 - 调用大模型进行精确分类
        intent_category = route_intent(current_question, st.session_state.api_key, st.session_state.model_name)
        last_msg["intent_route"] = "completed"
        last_msg["intent_category"] = intent_category
        
        # 根据分类结果执行不同分支
        if intent_category == "IRRELEVANT":
            # 分支 1: 无关闲聊 - 直接拦截，输出友好提示
            last_msg["analysis"] = """
**亲，我是您的电商投流数据洞察助手。**  

我目前只擅长解答直通车、引力魔方等广告渠道的数据异动和归因问题哦。  

如果有关于 **ROI 下降、花费飙升、转化异常、漏斗流失** 等问题，请随时考考我！

**示例问题：**
- 分析引力魔方最近3天的漏斗流失情况
- 查询各渠道的ROI排名
- 检查最近3天有没有异常数据
- 哪个计划的点击率最低？
"""
            st.session_state.processing = False
            st.rerun()
        
        elif intent_category == "KNOWLEDGE_QA":
            # 分支 2: 业务概念与知识问答 - 直接调用大模型解答，跳过SQL和查库
            last_msg["knowledge_qa_status"] = "processing"
            st.rerun()
        
        elif intent_category == "DATA_QUERY":
            # 分支 3: 数据查询与诊断 - 进入核心工作流
            last_msg["sql_status"] = "processing"
            st.rerun()
        
        st.rerun()
    
    # ========== 知识问答分支 ==========
    elif last_msg.get("role") == "assistant" and last_msg.get("knowledge_qa_status") == "processing":
        # 直接调用大模型回答知识问题
        from data_analysis_agent import ai_knowledge_qa
        answer = ai_knowledge_qa(current_question, st.session_state.api_key, st.session_state.model_name)
        last_msg["knowledge_qa_status"] = "completed"
        last_msg["analysis"] = answer
        st.session_state.processing = False
        st.rerun()
    
    # ========== 数据查询分支 ==========
    elif last_msg.get("role") == "assistant" and last_msg.get("sql_status") == "processing":
        # 步骤 1: 生成 SQL
        sql = text_to_sql(current_question, st.session_state.api_key, st.session_state.model_name)
        
        if sql:
            last_msg["sql"] = sql
            last_msg["sql_status"] = "completed"
            last_msg["data_status"] = "processing"
        else:
            last_msg["sql_status"] = "error"
            st.session_state.processing = False
        
        st.rerun()
    
    elif last_msg.get("data_status") == "processing":
        # 步骤 2: 执行 SQL
        success, result = execute_sql_with_error_handling(last_msg["sql"])
        
        if success and result is not None:
            last_msg["data"] = result
            last_msg["data_status"] = "completed"
            last_msg["analysis_status"] = "processing"
        else:
            last_msg["data_status"] = "error"
            st.session_state.processing = False
        
        st.rerun()
    
    elif last_msg.get("analysis_status") == "processing":
        # 步骤 3: AI 归因分析
        analysis = ai_attribution_analysis(current_question, last_msg["sql"], last_msg["data"], st.session_state.api_key, st.session_state.model_name)
        last_msg["analysis"] = analysis
        last_msg["analysis_status"] = "completed"
        st.session_state.processing = False
        
        st.rerun()
