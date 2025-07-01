#!/usr/bin/env python3
"""
演示不同级别的ANSI码处理效果
"""

import re

# 从实际日志中提取的原始输出示例
raw_output = """[38;2;255;180;84m [38;2;255;179;85m [38;2;255;178;85m [38;2;254;177;86m█[38;2;254;176;86m█[38;2;254;175;87m█[38;2;254;174;87m█[38;2;254;172;88m█[38;2;253;171;88m█[38;2;253;170;89m█[38;2;253;169;89m█[38;2;253;168;90m█[38;2;253;167;91m [38;2;252;166;91m [38;2;252;165;92m█[38;2;252;164;92m█[38;2;252;163;93m█[38;2;252;162;93m█[38;2;251;161;94m█[38;2;251;160;94m█[38;2;251;158;95m█[38;2;251;157;95m█[38;2;251;156;96m█[38;2;250;155;97m█[38;2;250;154;97m [38;2;250;153;98m█[38;2;250;152;98m█[38;2;250;151;99m█[38;2;249;150;99m█[38;2;249;149;100m█[38;2;249;148;100m█[38;2;249;147;101m [38;2;249;146;101m [38;2;249;145;102m [38;2;248;143;103m█[38;2;248;142;103m█[38;2;248;141;104m█[38;2;248;140;104m█[38;2;248;139;105m█[38;2;247;138;105m█[38;2;247;137;106m [38;2;247;136;106m█[38;2;247;135;107m█[38;2;247;134;107m█[38;2;246;133;108m█[38;2;246;132;109m█[38;2;246;131;109m [38;2;246;129;110m█[38;2;246;128;110m█[38;2;245;127;111m█[38;2;245;126;111m█[38;2;245;125;112m█[38;2;245;124;112m█[38;2;245;123;113m [38;2;244;122;113m [38;2;244;121;114m [38;2;244;120;115m█[38;2;244;119;115m█[38;2;244;118;116m█[38;2;243;117;116m█[38;2;243;115;117m█[38;2;243;114;117m [38;2;243;113;118m█[38;2;243;112;118m█[38;2;242;111;119m█[38;2;242;110;119m█[38;2;242;109;120m█[39m
[38;2;191;189;182mTips for getting started:[39m
[38;2;191;189;182m1. Ask questions, edit files, or run commands.[39m
[38;2;191;189;182m2. Be specific for the best results.[39m
[38;2;57;186;230m🐸 Retry backoff: initial 15s, max 60s[39m"""

def no_cleaning(text):
    """不进行任何清理"""
    return text

def basic_ansi_cleaning(text):
    """基础ANSI清理（简单模式）"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def advanced_ansi_cleaning(text):
    """高级ANSI清理（我们当前的实现）"""
    ansi_patterns = [
        r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])',  # 标准ANSI转义
        r'\x1b\[[0-9;]*m',                          # 颜色代码
        r'\x1b\[38;2;[0-9;]*m',                     # 24位RGB颜色代码  
        r'\x1b\[[0-9]*[A-Z]',                       # 光标移动
        r'\x1b\[[0-9]*[a-z]',                       # 其他转义序列
        r'\x1b\[2K',                                # 清除行
        r'\x1b\[1A',                                # 向上移动光标
        r'\x1b\[G',                                 # 移动光标到第1列
    ]
    
    cleaned = text
    for pattern in ansi_patterns:
        cleaned = re.sub(pattern, '', cleaned)
    
    # 移除可能遗漏的转义序列
    cleaned = re.sub(r'\x1b\[[^m]*m?', '', cleaned)
    return cleaned

def smart_content_extraction(text):
    """智能内容提取（包含UI过滤）"""
    # 先清理ANSI码
    clean_text = advanced_ansi_cleaning(text)
    
    # 分行并过滤
    lines = clean_text.split('\n')
    meaningful_lines = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # 跳过空行
        if not line_stripped:
            continue
            
        # 跳过UI装饰行
        if any(char in line_stripped for char in ['╭', '╰', '│', '░', '█']):
            continue
            
        # 跳过系统消息
        skip_patterns = [
            "tips for getting started",
            "ask questions, edit files",
            "be specific for the best",
            "retry backoff:",
            "/help for more information",
        ]
        
        line_lower = line_stripped.lower()
        if any(pattern in line_lower for pattern in skip_patterns):
            continue
            
        # 保留有意义的内容
        meaningful_lines.append(line_stripped)
    
    return '\n'.join(meaningful_lines)

def demo_all_methods():
    """演示所有处理方法"""
    
    print("🔍 ANSI码处理方法对比")
    print("=" * 80)
    
    print("\n1️⃣ 原始输出 (Raw Output):")
    print(f"长度: {len(raw_output)} 字符")
    print(f"预览: {repr(raw_output[:100])}...")
    
    print("\n2️⃣ 无清理 (No Cleaning):")
    result1 = no_cleaning(raw_output)
    print(f"长度: {len(result1)} 字符")
    print(f"预览: {result1[:100]}...")
    
    print("\n3️⃣ 基础ANSI清理 (Basic Cleaning):")
    result2 = basic_ansi_cleaning(raw_output)
    print(f"长度: {len(result2)} 字符")
    print(f"结果: {repr(result2)}")
    
    print("\n4️⃣ 高级ANSI清理 (Advanced Cleaning):")
    result3 = advanced_ansi_cleaning(raw_output)
    print(f"长度: {len(result3)} 字符")
    print(f"结果: {repr(result3)}")
    
    print("\n5️⃣ 智能内容提取 (Smart Extraction):")
    result4 = smart_content_extraction(raw_output)
    print(f"长度: {len(result4)} 字符")
    print(f"结果: {repr(result4)}")
    
    # 统计分析
    print("\n📊 统计对比:")
    print(f"原始: {len(raw_output):4d} 字符")
    print(f"无处理: {len(result1):4d} 字符 (减少 {len(raw_output) - len(result1):3d})")
    print(f"基础清理: {len(result2):4d} 字符 (减少 {len(raw_output) - len(result2):3d})")
    print(f"高级清理: {len(result3):4d} 字符 (减少 {len(raw_output) - len(result3):3d})")
    print(f"智能提取: {len(result4):4d} 字符 (减少 {len(raw_output) - len(result4):3d})")

if __name__ == "__main__":
    demo_all_methods() 