import os
#解析的报文头体消息数量有问题，用该文件复原
def parse_first_part(line):
    """Extract the first part before the first comma from a line"""
    return line.split(',', 1)[0].strip()

def filter_matching_lines(file1_path, file2_path, output_path):
    """Filter file2 to keep lines matching file1's first parts, maintaining file1's order and count"""
    with open(file1_path, 'r') as f1, open(file2_path, 'r') as f2, open(output_path, 'w') as out:
        # Read all lines from both files
        lines1 = [line.strip() for line in f1.readlines()]
        lines2 = [line.strip() for line in f2.readlines()]
        
        # Create a dictionary mapping first parts to full lines in file2
        file2_dict = {}
        for line in lines2:
            first_part = parse_first_part(line)
            if first_part not in file2_dict:  # Only store the first occurrence
                file2_dict[first_part] = line
        
        # Process file1 in order and find matches in file2
        matched_lines = 0
        missing_messages = 0
        
        for line1 in lines1:
            first_part1 = parse_first_part(line1)
            if first_part1 in file2_dict:
                out.write(file2_dict[first_part1] + '\n')
                matched_lines += 1
            else:
                missing_messages += 1
                print(f"Warning: No match found in file2 for first part: {first_part1}")
        
        print(f"Processed {matched_lines} matching lines out of {len(lines1)} in file1")
        if missing_messages > 0:
            print(f"Warning: {missing_messages} messages from file1 had no match in file2")

if __name__ == "__main__":
    # 输入输出路径配置
    input_file1 = "/root/OP-MDIplier/header_res/bacnet_1000.out"  # 文件1路径
    input_file2 = "/root/OP-MDIplier/body_res/bacnet_1000.out" # 文件2路径
    output_dir = "/root/OP-MDIplier/body_res/"            # 输出目录
    output_file = f"{output_dir}n_bacnet_1000.out"  

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 执行过滤
    filter_matching_lines(input_file1, input_file2, output_file)