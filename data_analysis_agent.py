import sqlite3
import requests
import json

def execute_sql_with_error_handling(sql: str, db_path: str = 'ecommerce_ads.db') -> tuple:
    """
    执行 SQL 查询并获取结果（带异常兜底）
    
    Args:
        sql: SQL 查询语句
        db_path: 数据库文件路径
    
    Returns:
        (success: bool, result: list or str)
        - success=True 时，result 为查询结果列表
        - success=False 时，result 为错误信息
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 执行 SQL
        cursor.execute(sql)
        
        # 获取列名
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        
        # 获取结果
        results = cursor.fetchall()
        
        conn.close()
        
        # 转换结果为一致的数据类型，避免 pyarrow 转换错误
        # 将所有数据转换为字符串，确保类型一致
        formatted_results = []
        for row in results:
            formatted_row = []
            for value in row:
                # 处理 None 值
                if value is None:
                    formatted_row.append("")
                # 转换所有数值为字符串
                elif isinstance(value, (int, float)):
                    # 保留2位小数
                    if isinstance(value, float):
                        formatted_row.append(f"{value:.2f}")
                    else:
                        formatted_row.append(str(value))
                else:
                    formatted_row.append(str(value))
            formatted_results.append(tuple(formatted_row))
        
        return (True, {'columns': columns, 'data': formatted_results})
    
    except sqlite3.Error as e:
        error_msg = f"SQL 执行错误: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return (False, error_msg)
    except Exception as e:
        error_msg = f"数据库操作异常: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return (False, error_msg)

def ai_attribution_analysis(user_question: str, sql: str, raw_data: dict, api_key: str, model_name: str = "Qwen/Qwen3.5-9B") -> str:
    """
    调用大模型进行 AI 归因分析
    
    Args:
        user_question: 用户原始问题
        sql: 执行的 SQL 语句
        raw_data: 查询到的真实数据（包含 columns 和 data）
        api_key: 硅基流动 API Key（由调用方传入）
    
    Returns:
        归因分析报告（Markdown 格式）
    """
    # 检查 API Key 是否有效
    if not api_key:
        return "❌ API Key 未提供，请联系管理员配置"
    # 系统提示词 - Agent 2 配置
    system_prompt = """
你是一个资深的商业化数据分析专家和投流优化师，擅长电商广告投放数据分析和异常归因。

你的任务：
根据用户提出的问题、执行的SQL语句和查询到的真实数据，进行深度的异常归因分析。

数据字段说明：
- date: 日期
- campaign_type: 渠道类型（直通车、引力魔方、万相台）
- campaign_name: 计划名称
- spend: 花费（金额，单位：元）
- impressions: 曝光量
- clicks: 点击量
- orders: 订单数
- gmv: 成交额（单位：元）
- roi: 投入产出比 = gmv/spend

输出规范（必须严格遵守）：
1. 使用 Markdown 格式输出
2. 包含三个板块，每个板块使用标题（##）开头
3. 语言要专业但易懂，面向业务人员
4. 数字必须使用阿拉伯数字，禁止使用中文数字（如：一、二、三）
5. 不要添加任何额外的符号或标记，只输出纯净的中文内容
6. 不要输出任何代码、公式或特殊字符
7. 每个板块的内容必须完整、连贯，不要有不完整的句子
8. 业务干预建议必须使用阿拉伯数字编号（1、2、3...），每个建议占一行
9. 禁止出现乱码、重复字符或无意义的符号
10. 所有指标数值必须是合理的正数，不要输出负数或异常值

【板块结构】
## 核心结论
- 一句话概括数据异动的根本原因
- 明确指出是哪个渠道、哪个计划的什么指标出了问题
- 用简洁的语言点明核心问题

## 数据支撑
- 引用查出的具体数据进行论证
- 对比正常情况和异常情况
- 使用清晰的对比格式，例如：A计划的spend从X增长到Y，涨幅Z%
- 所有数字必须为正数，花费、订单、GMV等指标不可能为负数

## 业务干预建议
- 给出明确的操作建议
- 具体可执行，例如：暂停计划、排查商品详情页承接、调整出价等
- 按优先级排序建议，使用阿拉伯数字编号（1、2、3...）

【输出示例】
## 核心结论
直通车渠道的"爆款引流计划"出现异常，花费大幅增长但订单未同步提升，导致ROI显著下降。

## 数据支撑
- 该计划近3天平均花费从2717元增长至6181元，涨幅达227%
- 但订单量维持在低位（平均8单/天），与正常时期持平
- 导致ROI从2.5降至0.3

## 业务干预建议
1. 立即暂停该计划，避免进一步损失
2. 排查落地页转化问题，检查是否存在页面加载异常
3. 分析点击质量，确认流量真实性
4. 调整出价策略，优化投放人群定向

【禁止输出】
- 不要输出类似 ";'5" 或 ";'3" 这样的乱码
- 不要在句子末尾添加无意义的数字
- 不要出现"投敌"等错别字，正确应为"投放"
- 不要输出不完整或断裂的句子
"""
    
    # 将数据格式化为更清晰的表格形式
    columns = raw_data.get('columns', [])
    data_rows = raw_data.get('data', [])
    
    # 格式化数据展示
    formatted_data = "| " + " | ".join(columns) + " |\n"
    formatted_data += "| " + " | ".join(["---"] * len(columns)) + " |\n"
    for row in data_rows:
        formatted_data += "| " + " | ".join(str(cell) for cell in row) + " |\n"
    
    # 构建用户消息
    user_message = f"""
用户问题：{user_question}

执行的SQL：{sql}

查询结果（表格格式）：
{formatted_data}

请基于以上数据进行深度归因分析，注意：
1. 所有指标（花费、订单、GMV等）都是正数，不可能为负数
2. 分析时要注意数据的准确性，不要误解数据含义
"""
    
    # API 请求配置
    url = "https://api.siliconflow.cn/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        "temperature": 0.1,  # 极低温度确保输出稳定准确
        "max_tokens": 1500
    }
    
    try:
        # 发送请求
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        
        # 解析响应
        result = response.json()
        analysis = result["choices"][0]["message"]["content"].strip()
        
        # 后处理：清理乱码和错别字
        analysis = _clean_output(analysis)
        
        return analysis
    
    except Exception as e:
        error_msg = f"AI 归因分析失败: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return f"## 核心结论\n分析失败：{error_msg}\n\n## 数据支撑\n无\n\n## 业务干预建议\n请检查API配置并重试"

def _clean_output(text: str) -> str:
    """
    清理大模型输出中的乱码、错别字和格式问题
    
    Args:
        text: 原始输出文本
    
    Returns:
        清理后的文本
    """
    import re
    
    # 1. 修复常见错别字
    text = text.replace('投敌', '投放')
    text = text.replace('投敌人群', '投放人群')
    text = text.replace('GMGM', 'GMV')
    text = text.replace('GMM', 'GMV')
    
    # 2. 清理乱码字符组合
    # 移除类似 ";'5" 或 ";'3" 的乱码
    text = re.sub(r";'(\d)", r'', text)
    # 移除类似 "\';" 的乱码
    text = re.sub(r"\\?;'?", r'', text)
    # 移除连续的特殊字符
    text = re.sub(r'[;:"\'\\]{2,}', r'', text)
    
    # 3. 修复业务建议中的编号问题（移除末尾多余数字）
    # 匹配 "定向 5" 或 "定向5" 这种模式
    text = re.sub(r'(定向)\s*\d+$', r'\1', text)
    text = re.sub(r'(定向)\d+', r'\1', text)
    
    # 4. 清理句子末尾的无意义数字
    text = re.sub(r'(\D)\s*\d+$', r'\1', text)
    
    # 5. 修复重复的标点符号
    text = re.sub(r'([，。！？；])\1+', r'\1', text)
    
    # 6. 修复中英文混排的空格问题
    text = re.sub(r'([a-zA-Z]+)([\u4e00-\u9fa5])', r'\1 \2', text)
    text = re.sub(r'([\u4e00-\u9fa5])([a-zA-Z]+)', r'\1 \2', text)
    
    # 7. 移除多余的空格
    text = re.sub(r' +', r' ', text)
    text = text.strip()
    
    return text

def ai_knowledge_qa(user_question: str, api_key: str, model_name: str = "Qwen/Qwen3.5-9B") -> str:
    """
    业务概念与知识问答 - 直接调用大模型解答电商投流相关的概念和知识问题
    
    Args:
        user_question: 用户的知识问题
        api_key: 硅基流动 API Key
    
    Returns:
        知识问答答案（Markdown 格式）
    """
    system_prompt = """
你是一位资深的电商广告投放专家，专注于淘宝/天猫平台的直通车、引力魔方、万相台等广告渠道。

请用清晰、专业但易懂的语言回答用户的问题。

【回答要求】
1. 使用 Markdown 格式，结构清晰
2. 对于指标定义类问题，给出明确的计算公式（如果适用）
3. 对于运营策略类问题，提供可操作的建议
4. 确保所有输出都是中文，避免使用英文缩写（首次出现时注明缩写）

【禁止输出】
- 不要输出类似 ";'5" 或 ";'3" 这样的乱码
- 不要在句子末尾添加无意义的数字
- 不要出现"投敌"等错别字，正确应为"投放"
- 不要输出不完整或断裂的句子

【示例】
用户问：点击率代表什么？
回答：点击率（CTR）是指广告被点击的次数占展现次数的比例。
计算公式：CTR = 点击量 / 展现量 × 100%
它反映了广告素材和标题对用户的吸引力，是衡量广告效果的重要指标之一。
"""
    
    # API 请求配置
    url = "https://api.siliconflow.cn/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_question
            }
        ],
        "temperature": 0.1,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        answer = result["choices"][0]["message"]["content"].strip()
        
        # 清理输出
        answer = _clean_output(answer)
        
        # 格式化答案
        formatted_answer = f"""
**📚 知识解答**

{answer}
"""
        return formatted_answer
        
    except Exception as e:
        error_msg = f"知识问答失败: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return f"**📚 知识解答**\n\n抱歉，暂时无法回答这个问题。请稍后重试。"

if __name__ == "__main__":
    """测试用例"""
    API_KEY = "your_api_key_here"  # 请替换为实际的 API Key
    
    # 测试数据
    test_sql = "SELECT campaign_type, campaign_name, SUM(spend) as total_spend, SUM(gmv) as total_gmv, SUM(gmv)/SUM(spend) as roi FROM ad_campaign_daily_reports WHERE date >= DATE('now', '-3 days') GROUP BY campaign_type, campaign_name ORDER BY roi ASC"
    test_question = "查一下最近3天，哪个计划的ROI最低？"
    
    # 执行SQL
    success, result = execute_sql_with_error_handling(test_sql)
    
    if success:
        print("SQL执行成功，开始AI归因分析...")
        analysis = ai_attribution_analysis(test_question, test_sql, result, API_KEY)
        print("\n归因分析报告：")
        print(analysis)
    else:
        print(f"SQL执行失败: {result}")
