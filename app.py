import streamlit as st
import pandas as pd
import requests
import json
import io

# --- 1. 配置与常量 (源自 zuizhong.py) ---
st.set_page_config(
    page_title="班主任寄语助手 (网页旗舰版)",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 默认标签数据
DEFAULT_TAGS = {
    "学习表现": ["勤奋刻苦", "思维敏捷", "基础扎实", "听讲专心", "积极发言", "善于提问", "作业工整", "自主学习", "成绩优异", "潜力巨大", "举一反三", "逻辑清晰", "稍微粗心", "需补短板", "畏难情绪", "书写潦草"],
    "闪光特长": ["体育健将", "绘画天才", "乐器达人", "写作能手", "书法秀丽", "朗诵明星", "编程高手", "棋艺精湛", "劳动模范", "环保卫士", "班级栋梁", "组织能手", "摄影达人", "舞蹈精灵", "手工巧匠", "英语达人"],
    "品行性格": ["文质彬彬", "活泼开朗", "诚实守信", "乐于助人", "尊师重道", "团结同学", "沉稳内敛", "乐观向上", "正义感强", "心胸宽广", "乖巧懂事", "独立自强", "善解人意", "礼貌待人", "责任心强", "纯真可爱"],
    "改进建议": ["戒骄戒躁", "细心审题", "规范书写", "多读好书", "勇于表达", "提高效率", "制定计划", "劳逸结合", "增强自信", "拓展视野", "坚持锻炼", "取长补短", "珍惜时间", "敢于提问", "保持热爱", "迎难而上"]
}

# 默认提示词模板
DEFAULT_PROMPT_TEMPLATE = (
    "你是一名资深班主任。请为一名{性别}【{姓名}】写期末评语。\n"
    "综合评价等第：{等第}。\n"
    "关键词：{关键词}。\n"
    "具体表现细节：{具体表现}。\n"
    "写作要求：\n"
    "1. 风格要{风格}。\n"
    "2. 语气真诚温暖，多挖掘亮点。\n"
    "3. 字数控制在80-120字之间。\n"
    "4. 直接输出评语内容，不要包含“好的”、“如下”等客套话。"
)

# --- 2. 初始化 Session State (网页版的状态记忆) ---
if 'student_df' not in st.session_state:
    # 初始化一个空的学生表
    st.session_state['student_df'] = pd.DataFrame(columns=['姓名', '性别', '评语', 'Tags', 'Details'])
if 'current_index' not in st.session_state:
    st.session_state['current_index'] = 0
if 'custom_tags' not in st.session_state:
    st.session_state['custom_tags'] = DEFAULT_TAGS.copy()

# --- 3. 侧边栏：全局设置 ---
with st.sidebar:
    st.header("⚙️ 全局设置")
    
    # 3.1 模型设置
    with st.expander("🤖 模型与密钥 (必填)", expanded=True):
        provider = st.selectbox("模型服务商", ["DeepSeek", "智谱AI (GLM-4)"], index=0)
        api_key = st.text_input("API Key", type="password", help="请输入对应服务商的Key")
        
    # 3.2 提示词设置
    with st.expander("🎨 自定义提示词"):
        prompt_template = st.text_area("提示词模板", value=DEFAULT_PROMPT_TEMPLATE, height=150, help="保留{大括号}内的变量")
    
    # 3.3 标签管理
    with st.expander("🏷️ 标签管理"):
        st.caption("在此处临时修改标签库（刷新网页会重置）")
        edit_tag_category = st.selectbox("选择维度", list(DEFAULT_TAGS.keys()))
        current_tags_str = " ".join(st.session_state['custom_tags'][edit_tag_category])
        new_tags_str = st.text_area("编辑标签 (空格隔开)", value=current_tags_str)
        if st.button("更新标签库"):
            tags_list = [t.strip() for t in new_tags_str.replace(",", " ").split() if t.strip()]
            st.session_state['custom_tags'][edit_tag_category] = tags_list
            st.success("标签已更新！")

    st.markdown("---")
    
    # 3.4 导入导出
    st.subheader("📂 文件操作")
    uploaded_file = st.file_uploader("导入学生名单 (Excel)", type=['xlsx', 'xls'])
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            # 确保必要的列存在
            if '姓名' in df.columns:
                # 补充缺失列
                if '性别' not in df.columns: df['性别'] = '学生'
                if '评语' not in df.columns: df['评语'] = ''
                # 初始化临时列
                df['Tags'] = [[] for _ in range(len(df))]
                df['Details'] = ['' for _ in range(len(df))]
                
                st.session_state['student_df'] = df
                st.session_state['current_index'] = 0 # 重置索引
                st.success(f"成功导入 {len(df)} 人")
            else:
                st.error("Excel中必须包含【姓名】列")
        except Exception as e:
            st.error(f"导入失败: {e}")

    # 导出按钮
    if not st.session_state['student_df'].empty:
        # 准备导出数据（只导出核心列）
        export_df = st.session_state['student_df'][['姓名', '性别', '评语']]
        
        # 将 DataFrame 转为 Excel 二进制流
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name='Sheet1')
        excel_data = output.getvalue()
        
        st.download_button(
            label="📥 导出结果到 Excel",
            data=excel_data,
            file_name="学生评语.xlsx",
            mime="application/vnd.ms-excel"
        )

# --- 4. 主界面逻辑 ---

st.title("🎓 班主任寄语助手")

# 检查是否有数据
if st.session_state['student_df'].empty:
    st.info("👈 请先在左侧侧边栏【导入学生名单】，或直接在下方手动输入测试。")
    # 手动模式容器
    manual_name = st.text_input("临时学生姓名", "张三")
    manual_gender = st.selectbox("临时学生性别", ["男", "女"])
    current_student = {"姓名": manual_name, "性别": manual_gender, "评语": ""}
else:
    # --- 学生选择器 ---
    # 创建一个显示列表： "1. 张三 (已完成)"
    df = st.session_state['student_df']
    student_names = []
    for idx, row in df.iterrows():
        mark = "✅" if row['评语'] else "⬜"
        student_names.append(f"{idx+1}. {row['姓名']} {mark}")
    
    selected_option = st.selectbox(
        "选择学生", 
        student_names, 
        index=st.session_state['current_index']
    )
    # 更新当前索引
    current_idx = student_names.index(selected_option)
    st.session_state['current_index'] = current_idx
    current_student = df.iloc[current_idx]

st.markdown(f"### 当前编辑：**{current_student['姓名']}** ({current_student['性别']})")

# --- 5. 核心操作区 (模仿 zuizhong.py 的布局) ---

# 5.1 评价等第
grade = st.radio("综合等第", ["优", "良", "中", "加油"], horizontal=True, index=1)

# 5.2 四个维度 (使用 Tabs 布局更省空间)
tabs = st.tabs(st.session_state['custom_tags'].keys())
selected_tags = []
all_details = []

# 遍历四个维度，生成多选框和输入框
for i, (category, tags) in enumerate(st.session_state['custom_tags'].items()):
    with tabs[i]:
        # 标签选择 (对应 Multiselect)
        col_tags, col_detail = st.columns([2, 1])
        with col_tags:
            s_tags = st.multiselect(f"{category} - 标签", tags, key=f"tags_{i}")
            selected_tags.extend(s_tags)
        with col_detail:
            # 细节输入
            s_detail = st.text_area(f"{category} - 补充细节", height=100, key=f"detail_{i}", placeholder="具体案例...")
            if s_detail:
                all_details.append(s_detail)

# 5.3 风格选择
st.markdown("#### 📝 寄语风格")
style = st.selectbox("", ["温婉亲切", "睿智干练", "文采斐扬", "幽默风趣"], label_visibility="collapsed")

# --- 6. 生成逻辑 ---
if st.button("🚀 生成专属寄语", type="primary", use_container_width=True):
    if not api_key:
        st.error("请先在左侧设置 API Key！")
    else:
        with st.spinner("AI 正在思考中..."):
            try:
                # 1. 准备 Prompt (变量替换逻辑同 zuizhong.py)
                details_text = "；".join(all_details) if all_details else "表现稳定"
                final_prompt = prompt_template \
                    .replace("{姓名}", str(current_student['姓名'])) \
                    .replace("{性别}", str(current_student['性别'])) \
                    .replace("{等第}", grade) \
                    .replace("{风格}", style) \
                    .replace("{关键词}", ",".join(selected_tags)) \
                    .replace("{具体表现}", details_text)

                # 2. 准备 API 参数 (兼容 DeepSeek 和 智谱)
                if provider == "DeepSeek":
                    url = "https://api.deepseek.com/chat/completions"
                    model_name = "deepseek-chat"
                else:
                    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
                    model_name = "glm-4-flash"

                headers = {
                    "Authorization": f"Bearer {api_key.strip()}", 
                    "Content-Type": "application/json"
                }
                data = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": final_prompt}],
                    "temperature": 0.8,
                    "stream": False
                }

                # 3. 发送请求
                response = requests.post(url, headers=headers, json=data, timeout=60)
                
                if response.status_code == 200:
                    result_text = response.json()['choices'][0]['message']['content']
                    
                    # 4. 保存结果到 Session State
                    if not st.session_state['student_df'].empty:
                        # 更新 DataFrame
                        st.session_state['student_df'].at[current_idx, '评语'] = result_text
                        st.rerun() # 刷新页面以更新列表状态
                    else:
                        # 手动模式直接显示
                        st.session_state['manual_result'] = result_text
                        
                else:
                    st.error(f"API请求失败: {response.status_code} - {response.text}")

            except Exception as e:
                st.error(f"发生错误: {str(e)}")

# --- 7. 结果展示区 ---
st.markdown("### 📋 寄语预览")

# 获取当前显示的评语
display_text = ""
if not st.session_state['student_df'].empty:
    display_text = st.session_state['student_df'].iloc[st.session_state['current_index']]['评语']
elif 'manual_result' in st.session_state:
    display_text = st.session_state['manual_result']

# 文本域 (可编辑)
final_text = st.text_area("生成的评语 (可手动修改)", value=display_text, height=200)

# 如果用户手动修改了文本框，是否需要保存回去？
# Streamlit的文本框修改通常需要配合 on_change 回调，这里为了简化，
# 建议用户修改后直接点复制，或者我们可以加一个“保存修改”按钮。
if not st.session_state['student_df'].empty and final_text != display_text:
    if st.button("💾 保存修改"):
        st.session_state['student_df'].at[current_idx, '评语'] = final_text
        st.success("修改已保存！")
        st.rerun()
