# 基于Multi-Agent的电商投放归因分析中台 - 部署指南

## 📖 项目简介

这是一个基于大模型的电商数据智能分析平台，支持自然语言提问、自动生成 SQL、智能归因分析。

**核心功能：**
- ✅ 自然语言转 SQL（基于意图识别）
- ✅ 自动数据查询
- ✅ AI 智能归因分析
- ✅ 交互式对话界面

##  快速部署

### 1. 配置 API Key

编辑 `config.py` 文件，填入您的硅基流动 API Key：

```python
# 配置文件
# 请将您的 API Key 填写在这里

# 硅基流动 API Key
SILICONFLOW_API_KEY = "sk-your-api-key-here"

# 数据库配置
DATABASE_NAME = "ecommerce_ads.db"

# 系统配置
APP_TITLE = "AI 数据异动归因系统"
APP_DESCRIPTION = "基于大模型的电商数据智能分析平台"
```

### 2. 安装依赖

```bash
pip install streamlit requests
```

### 3. 创建数据库（如果是首次部署）

```bash
python create_ecommerce_ads_db.py
```

### 4. 启动应用

```bash
streamlit run app.py --server.headless true --server.port 8501
```

### 5. 访问系统

打开浏览器访问：`http://localhost:8501`

## 🌐 对外发布

### 方案一：本地网络访问

```bash
# 启动时允许外部访问
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

然后其他用户可以通过 `http://你的IP地址:8501` 访问

### 方案二：使用内网穿透工具

推荐使用 **ngrok** 或 **frp** 将本地服务暴露到公网

```bash
# 使用 ngrok
ngrok http 8501
```

### 方案三：部署到云服务器

1. 将项目上传到云服务器
2. 安装 Python 和依赖
3. 配置 API Key
4. 使用 systemd 或 supervisor 守护进程
5. 配置 Nginx 反向代理

## 📊 使用示例

### 支持的分析场景

1. **漏斗流失分析**
   - "分析引力魔方最近 3 天的漏斗流失情况"
   - "查看直通车的曝光到订单转化路径"

2. **ROI 分析**
   - "查询各渠道的 ROI 排名"
   - "哪个计划的投入产出比最低？"

3. **异常检测**
   - "检查最近 3 天有没有异常数据"
   - "分析数据异动原因"

4. **花费分析**
   - "查看直通车最近 7 天的花费趋势"
   - "哪个计划烧钱最多？"

5. **点击率/转化率分析**
   - "分析哪个计划的点击率最低"
   - "查看各渠道的转化率表现"

## ⚙️ 系统架构

```
用户提问
  ↓
意图识别（规则引擎 + 大模型）
  ↓
参数提取（渠道、时间范围）
  ↓
SQL 生成（基于意图模板）
  ↓
数据查询（SQLite）
  ↓
AI 归因分析（大模型）
  ↓
输出分析报告
```

## 🔧 自定义配置

### 修改支持的渠道

编辑 `text_to_sql.py`，修改 `INTENT_DEFINITIONS` 中的渠道列表：

```python
channels = ['引力魔方', '直通车', '万相台']
```

### 添加新的分析场景

在 `text_to_sql.py` 中添加新的意图定义和 SQL 模板：

```python
INTENT_DEFINITIONS = {
    "new_analysis": {
        "name": "新分析类型",
        "patterns": ["关键词 1", "关键词 2"],
        "description": "描述"
    }
}

INTENT_SQL_TEMPLATES = {
    "new_analysis": """SELECT ... FROM ..."""
}
```

## 📝 注意事项

1. **API Key 安全**：不要将 `config.py` 提交到公开仓库
2. **数据库备份**：定期备份 `ecommerce_ads.db`
3. **性能优化**：如果数据量大，考虑添加索引
4. **日志记录**：建议添加日志记录功能便于排查问题

##  常见问题

### Q: 提示"配置文件不存在"
A: 确保 `config.py` 文件存在且包含正确的 API Key

### Q: SQL 生成失败
A: 检查 API Key 是否正确，网络连接是否正常

### Q: 界面无法访问
A: 确保防火墙已开放 8501 端口

## 📄 许可证

本项目仅供学习和内部使用。

---

**技术支持**：如有问题，请联系项目维护人员
