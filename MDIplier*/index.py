import os
import re

def process_indexes(index_str):
    """处理索引字符串，将所有数字除以2"""
    # 提取所有数字
    numbers = list(map(int, re.findall(r'\d+', index_str)))
    # 每个数字除以2并取整
    processed_numbers = [str(num // 2) for num in numbers]
    # 重新构建索引字符串
    return '[' + ', '.join(processed_numbers) + ']'

def process_line(line):
    """处理单行内容，仅更改索引部分的数字"""
    # 使用正则表达式匹配索引部分
    index_match = re.search(r'"(\[.*?\])"', line)
    if index_match:
        # 提取索引部分
        index_str = index_match.group(1)
        # 处理索引部分
        processed_index_str = process_indexes(index_str)
        # 替换原字符串中的索引部分
        return line.replace(index_str, processed_index_str)
    return line

def process_file(input_file, output_file):
    """处理单个文件，并将结果输出到新文件"""
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            processed_line = process_line(line)
            outfile.write(processed_line)

def process_directory(input_dir, output_dir):
    """处理指定目录下的所有.out文件，并将结果输出到新的目录"""
    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 遍历输入目录中的所有文件
    for filename in os.listdir(input_dir):
        if filename.endswith('.out'):
            input_file = os.path.join(input_dir, filename)
            output_file = os.path.join(output_dir, filename)
            process_file(input_file, output_file)

# 设置输入和输出目录路径
input_dir = "/root/OP-MDIplier/tmp"
output_dir = "/root/OP-MDIplier/final_res"

if os.path.isdir(input_dir):
    process_directory(input_dir, output_dir)
    print("All files processed and saved successfully!")
else:
    print(f"Error: Directory not found - {input_dir}")
