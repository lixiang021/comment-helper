import streamlit as st
import requests

# --- 1. 页面基础设置 ---
st.set_page_config(
    page_title="班主任寄语助手(手机版)",
    page_icon="🎓",
    layout="wide"
)

# --- 2. 侧边栏：设置区域 ---
with st.sidebar:
    st.header("⚙️ 系统设置")
    
    # 获取 API Key
    api_key = st.text_input("请输入 API Key", type="password", help="DeepSeek 或 智谱AI 的 Key")
    
    # 选择服务商
    provider = st.selectbox("选择模型服务商", ["DeepSeek", "智谱AI (GLM-4)"])
    
    st.divider()
    st.info("💡 **提示**：手机横屏使用体验更好哦！")
    st.markdown("---")
    st.caption("Designed for Teachers 🎓")

# --- 3. 主界面：学生信息 ---
st.title("🎓 班主任寄语助手")

# 使用两列布局
col1, col2 = st.columns(2)
with col1:
    student_name = st.text_input("学生姓名", placeholder="例如：张三")
with col2:
    student_gender = st.selectbox("性别", ["男", "女"])

# 等第选择
grade = st.radio("综合等第", ["优", "良", "中", "加油"], horizontal=True, index=1)

# --- 4. 标签选择区 (使用选项卡) ---
st.subheader("🏷️ 表现标签 (多选)")

# 预设标签库 (你可以直接在这里修改词库)
tags_data = {
    "学习": ["勤奋刻苦", "思维敏捷", "基础扎实", "作业工整", "积极发言", "稍微粗心", "书写潦草"],
    "特长": ["体育健将", "绘画天才", "乐器达人", "写作能手", "劳动模范", "小小主持人"],
    "品行": ["乐于助人", "诚实守信", "礼貌待人", "团结同学", "活泼开朗", "沉稳内敛"],
    "建议": ["戒骄戒躁", "细心审题", "多读好书", "提高效率", "增强自信", "敢于提问"]
}

selected_tags = []

# 创建四个标签页
tab1, tab2, tab3, tab4 = st.tabs(tags_data.keys())

with tab1:
    t1 = st.multiselect("学习表现", tags_data["学习"])
    selected_tags.extend(t1)
with tab2:
    t2 = st.multiselect("闪光特长", tags_data["特长"])
    selected_tags.extend(t2)
with tab3:
    t3 = st.multiselect("品行性格", tags_data["品行"])
    selected_tags.extend(t3)
with tab4:
    t4 = st.multiselect("改进建议", tags_data["建议"])
    selected_tags.extend(t4)

# 补充细节
detail_input = st.text_area("✍️ 补充具体细节 (可选)", placeholder="例如：这次运动会拿了长跑第一名，非常棒！", height=80)

# --- 5. 生成逻辑 ---
if st.button("🚀 生成专属寄语", type="primary", use_container_width=True):
    if not api_key:
        st.error("请先在左侧边栏输入 API Key！")
    elif not student_name:
        st.warning("请填写学生姓名！")
    else:
        with st.spinner("AI 正在思考中，请稍候..."):
            try:
                # 构造 Prompt
                tags_str = "、".join(selected_tags)
                prompt = (
                    f"你是一名班主任。请为学生【{student_name}】({student_gender})写期末评语。\n"
                    f"等第：{grade}。\n"
                    f"关键词：{tags_str}。\n"
                    f"具体细节：{detail_input}。\n"
                    f"要求：语气亲切温暖，多挖掘亮点，字数80-100字左右。"
                )

                # 调用 API
                headers = {
                    "Authorization": f"Bearer {api_key.strip()}",
                    "Content-Type": "application/json"
                }
                
                # 根据选择切换服务商
                if provider == "DeepSeek":
                    url = "https://api.deepseek.com/chat/completions"
                    model = "deepseek-chat"
                else:
                    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
                    model = "glm-4-flash"

                data = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.8,
                    "stream": False
                }

                resp = requests.post(url, headers=headers, json=data, timeout=60)
                
                if resp.status_code == 200:
                    result = resp.json()['choices'][0]['message']['content']
                    st.success("✅ 生成成功！")
                    st.text_area("结果 (可全选复制)", value=result, height=150)
                else:
                    st.error(f"请求失败: {resp.status_code} - {resp.text}")
                    
            except Exception as e:
                st.error(f"发生错误: {str(e)}")