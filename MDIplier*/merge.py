import os
import re
#根据分隔位置合并报文头和报文体的解析结果
def parse_line(line):
    """解析单行数据，按照第一个和最后一个逗号分割为三部分"""
    line = line.strip().strip('"')
    
    # 找到第一个逗号的位置
    first_comma = line.find(',')
    if first_comma == -1:
        raise ValueError(f"Invalid line format - no comma found: {line}")
    
    # 找到最后一个逗号的位置
    last_comma = line.rfind(',')
    if last_comma == -1 or last_comma == first_comma:
        raise ValueError(f"Invalid line format - only one comma found: {line}")
    
    # 分割三部分
    hexstr = line[:first_comma].strip('"')
    indexes_str = line[first_comma+1:last_comma].strip('"[]')
    splithex = line[last_comma+1:].strip('"')
    
    # 解析索引列表
    indexes = [int(idx) for idx in re.findall(r'\d+', indexes_str)] if indexes_str else []
    
    return hexstr, indexes, splithex

def merge_lines(line1, line2, split_pos):
    """合并两行数据，基于字符位置 split_pos 分割"""
    hex1, indexes1, splithex1 = parse_line(line1)
    hex2, indexes2, splithex2 = parse_line(line2)
    
    # 确保两个hexstr相同
    if hex1 != hex2:
        raise ValueError(f"Hex strings do not match: {hex1} vs {hex2}")
    
    # 提取第一个文件的splithex前split_pos部分
    splithex1_parts = splithex1.split()
    part1 = ' '.join(splithex1_parts[:split_pos]) if split_pos <= len(splithex1_parts) else splithex1
    
    # 提取第二个文件的splithex后split_pos部分
    splithex2_parts = splithex2.split()
    part2 = ' '.join(splithex2_parts[split_pos:]) if split_pos <= len(splithex2_parts) else ''
    
    # 合并两部分
    merged_splithex = part1 + (' ' + part2 if part2 else '')
    
    # 处理索引：保留两个索引列表的并集
    merged_indexes = sorted(list(set(indexes1 + indexes2)))
    
    # 格式化索引部分
    indexes_str = '[' + ', '.join(map(str, merged_indexes)) + ']'
    
    # 返回合并后的三个部分
    return hex1, indexes_str, merged_splithex

def main(file1_path, file2_path, output_path, split_pos):
    """主函数：处理两个文件并输出合并结果"""
    with open(file1_path, 'r') as f1, open(file2_path, 'r') as f2, open(output_path, 'w') as out:
        # 跳过文件头行（如果有）
        header1 = f1.readline()
        header2 = f2.readline()
        
        # 检查文件头是否一致
        if header1 != header2:
            print("Warning: File headers don't match. Using first file's header.")
        
        # 写入输出文件头
        out.write(header1)
        
        # 逐行处理
        line_count = 0
        for line1, line2 in zip(f1, f2):
            line_count += 1
            try:
                hexstr, indexes_str, merged_splithex = merge_lines(line1, line2, split_pos)
                out.write(f'"{hexstr}","{indexes_str}","{merged_splithex}"\n')
            except ValueError as e:
                print(f"Error processing line {line_count}: {e}")
                continue

if __name__ == "__main__":
    # 输入输出路径配置
    input_file1 = "/root/OP-MDIplier/header_res/bacnet_1000.out"  # 文件1路径
    input_file2 = "/root/OP-MDIplier/body_res/bacnet_1000.out" # 文件2路径
    output_dir = "/root/OP-MDIplier/tmp/"            # 输出目录
    output_file = f"{output_dir}bacnet_1000.out"           # 输出文件路径

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 执行合并（取前20个字符）
    main(
        file1_path=input_file1,
        file2_path=input_file2,
        output_path=output_file,
        split_pos=6 # 修改为您需要的分割位置
    )