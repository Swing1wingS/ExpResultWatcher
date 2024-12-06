import gradio as gr
import pandas as pd
from difflib import Differ

# 添加 JavaScript 脚本，用于控制 prompt 显示和隐藏
SCRIPT = """
<script>
function togglePrompt(index) {
    var element = document.getElementById('prompt_' + index);
    if (element.style.display === 'none') {
        element.style.display = 'block';
    } else {
        element.style.display = 'none';
    }
}
window.togglePrompt = togglePrompt;
</script>
"""

def highlight_differences(pred, target):
    differ = Differ()
    diff = list(differ.compare(pred.splitlines(True), target.splitlines(True)))
    highlighted = []
    
    for part in diff:
        if not part.endswith('\n'):
            part += '\n'
        if part.startswith("+ "):  # 新增部分
            highlighted.append(f'<span style="color:green;">{part}</span>')
        elif part.startswith("- "):  # 删除部分
            highlighted.append(f'<span style="color:red;">{part}</span>')
        else:
            highlighted.append(part)

    return "".join(highlighted).replace('\n', '<br>')

# 核心功能：处理上传的 Excel 文件
def process_excel(file, page, rows_per_page):
    if not file:
        return "请上传一个有效的 Excel 文件。", None

    df = pd.read_excel(file.name)

    # 检查是否包含必要的列
    required_columns = ["task_id", "prompt", "pred", "target", "em", "es"]
    if not all(col in df.columns for col in required_columns):
        return f"文件必须包含以下列：{', '.join(required_columns)}", None

    df["pred_highlighted"] = [
        highlight_differences(str(pred), str(target))
        for pred, target in zip(df["pred"], df["target"])
    ]
    df["prompt_html"] = [
        '<div id="prompt_{0}" style="display:none;">{1}</div>'.format(i, str(prompt).replace("\n", "<br>"))
        for i, prompt in enumerate(df["prompt"])
    ]
    df["toggle_button"] = [
        f'<button onclick="document.getElementById(\'prompt_{i}\').style.display = '
        f'(document.getElementById(\'prompt_{i}\').style.display === \'none\' ? \'block\' : \'none\')">显示/隐藏</button>'
        for i in range(len(df))
    ]
    
    # import pdb
    # pdb.set_trace()
    df['target_1'] = [
        str(target).replace('\n', '<br>')
        for target in df['target']
    ]

    start_idx = (page - 1) * rows_per_page
    end_idx = start_idx + rows_per_page
    paginated_df = df.iloc[start_idx:end_idx]

    table_html = paginated_df[["task_id", "prompt_html", "pred_highlighted", "target_1", "em", "es", "toggle_button"]].to_html(
        escape=False, index=False
    ).replace(
        '<table border="1" class="dataframe">', 
        '<table border="1" class="dataframe" style="white-space: pre-wrap; word-break: break-word;">'
    ).replace(
        '<th>task_id</th>',
        '<th style="width: 100px;">prompt_html</th>'
    ).replace(
        '<th>prompt_html</th>',
        '<th style="width: 500px;">prompt_html</th>'
    ).replace(
        '<th>em</th>',
        '<th style="width: 50px;">em</th>'
    ).replace(
        '<th>es</th>',
        '<th style="width: 50px;">es</th>'
    )

    def highlight_string(text, string_list):
        for s in string_list:
            text = text.replace(s, f'<span style="color:blue; font-weight:bold;">{s}</span>')
        return text
    
    table_html = highlight_string(table_html, ['<｜fim▁begin｜>', '<｜fim▁hole｜>', '<｜fim▁end｜>', '<|fim_prefix|>', '<|fim_suffix|>', '<|fim_middle|>', '- **Left Code Snippet Context `left_context`:**  ', '- **Right Code Snippet Context `right_context`:**  ', '- **Retreived Code Snippets from Related Files:** ', '**Instructions:** '])

    total_pages = (len(df) + rows_per_page - 1) // rows_per_page
    return f"当前第 {page} 页，共 {total_pages} 页", (SCRIPT + table_html).replace('\t', '    ')


# 创建 Gradio 界面
with gr.Blocks() as demo:
    gr.Markdown("## Excel Viewer with Pagination and Toggle Prompt Visibility")

    file_input = gr.File(label="上传 Excel 文件", file_types=[".xlsx"])
    rows_per_page = gr.Number(value=10, label="每页显示行数", interactive=True)
    process_button = gr.Button("处理文件")
    result_text = gr.Textbox(label="状态", interactive=False)
    result_html = gr.HTML(label="处理结果")
    page_number = gr.Number(value=1, label="页码", interactive=False)
    next_page_button = gr.Button("下一页")
    prev_page_button = gr.Button("上一页")

    def process_new_excel(file, page, rows_per_page):
        page = 1
        return page, process_excel(file, page, rows_per_page)
    
    def next_page(page, rows_per_page, file):
        page += 1
        result_text, result_html = process_excel(file, page, rows_per_page)
        return page, result_text, result_html

    def prev_page(page, rows_per_page, file):
        page = max(1, page - 1)
        result_text, result_html = process_excel(file, page, rows_per_page)
        return page, result_text, result_html

    # 按钮点击事件
    process_button.click(
        fn=process_new_excel,
        inputs=[file_input, page_number, rows_per_page],
        outputs=[page_number, result_text, result_html]
    )

    next_page_button.click(
        fn=next_page,
        inputs=[page_number, rows_per_page, file_input],
        outputs=[page_number, result_text, result_html]
    )

    prev_page_button.click(
        fn=prev_page,
        inputs=[page_number, rows_per_page, file_input],
        outputs=[page_number, result_text, result_html]
    )

demo.launch()
