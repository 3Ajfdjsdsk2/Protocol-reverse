import json
from typing import Dict, List, Tuple, Optional
from enum import Enum

class Protocol(Enum):
    """支持的协议类型"""
    BACNET = "BACnet"
    MODBUS = "Modbus"
    HTTP = "HTTP"
    CUSTOM = "Custom"

class MessageAnalyzer:
    def __init__(self, protocol: Protocol = Protocol.BACNET):
        self.protocol = protocol
        self.known_headers = {
            Protocol.BACNET: 4,  # BACnet/IP通常有4字节头部
            Protocol.MODBUS: 8,  # Modbus TCP头部通常为8字节
            Protocol.HTTP: 0     # HTTP无固定头部，需动态分析
        }

    def load_data(self, filepath: str) -> Dict[str, str]:
        """从JSON文件加载消息数据"""
        with open(filepath, "r") as f:
            data = json.load(f)
        return {str(idx): msg["Hexstream"] for idx, msg in enumerate(data)}

    def calculate_differences(self, data: Dict[str, str]) -> Tuple[List[int], List[bool]]:
        """计算每个字节位置的差异特征"""
        min_len = min(len(v) for v in data.values()) // 2
        diff_list = []
        stable_list = []

        for pos in range(min_len):
            diffs = []
            keys = list(data.keys())
            for i in range(1, len(keys)):
                prev = int(data[keys[i-1]][pos*2:(pos+1)*2], 16)
                curr = int(data[keys[i]][pos*2:(pos+1)*2], 16)
                diffs.append(abs(curr - prev))

            diff_list.append(sum(diffs))
            # 判断该位置是否稳定（差异<=1的比例超过90%）
            stable = sum(1 for d in diffs if d <= 1) / len(diffs) > 0.9
            stable_list.append(stable)

        return diff_list, stable_list

    def apply_rules(self, diff_list: List[int], stable_list: List[bool]) -> Dict[str, int]:
        """应用四条规则分析分隔位置"""
        results = {}
        
        # Rule 1: 从后向前第一个非零差异
        for i in range(len(diff_list)-1, -1, -1):
            if diff_list[i] != 0:
                results['rule1'] = i
                break

        # Rule 2: 从后向前第一个大于平均差异
        non_zero = [d for d in diff_list if d != 0]
        avg_diff = sum(non_zero)/len(non_zero) if non_zero else 0
        for i in range(len(diff_list)-1, -1, -1):
            if diff_list[i] > avg_diff:
                results['rule2'] = i
                break

        # Rule 3: 第一个不稳定位置
        for i, stable in enumerate(stable_list):
            if not stable:
                results['rule3'] = i
                break

        # Rule 4: 最大增益位置
        gain = [0] * len(diff_list)
        for i in range(1, len(diff_list)):
            gain[i] = gain[i-1] + (avg_diff if stable_list[i] else -diff_list[i])
        results['rule4'] = gain.index(max(gain))

        return results

    def protocol_specific_adjustment(self, results: Dict[str, int]) -> int:
        """根据协议特性调整最终结果"""
        if self.protocol in self.known_headers:
            expected_header = self.known_headers[self.protocol]
            # 选择最接近已知头部长度的结果
            closest = min(results.values(), key=lambda x: abs(x - expected_header))
            return closest
        else:
            # 默认优先使用Rule3和Rule4的结果
            preferred = [results.get('rule3'), results.get('rule4')]
            valid = [x for x in preferred if x is not None]
            return min(valid) if valid else results.get('rule1', 0)

    def analyze(
        self, 
        data: Dict[str, str], 
        verbose: bool = False
    ) -> Tuple[int, Dict[str, int]]:
        """分析消息结构"""
        diff_list, stable_list = self.calculate_differences(data)
        if verbose:
            print(f"Diff List: {diff_list[:20]}...")
            print(f"Stable Positions: {stable_list[:20]}...")

        rule_results = self.apply_rules(diff_list, stable_list)
        best_split = self.protocol_specific_adjustment(rule_results)

        return best_split, rule_results

# 示例用法
if __name__ == "__main__":
    # 1. 创建分析器（指定协议）
    analyzer = MessageAnalyzer(protocol=Protocol.BACNET)
    
    # 2. 加载数据
    data = analyzer.load_data("bacnet_5000.json")
    
    # 3. 执行分析
    split_pos, rules = analyzer.analyze(data, verbose=True)
    
    # 4. 输出结果
    print(f"\nProtocol: {analyzer.protocol.value}")
    print(f"Recommended split position: byte {split_pos} (hex char {split_pos*2})")
    print("Rule results:")
    for name, pos in rules.items():
        print(f"  {name}: byte {pos}")
    
    # 示例：分析Modbus消息
    print("\nAnalyzing Modbus messages...")
    modbus_analyzer = MessageAnalyzer(protocol=Protocol.MODBUS)
    modbus_data = modbus_analyzer.load_data("modbus_messages.json")
    modbus_split, _ = modbus_analyzer.analyze(modbus_data)
    print(f"Modbus split position: {modbus_split}")