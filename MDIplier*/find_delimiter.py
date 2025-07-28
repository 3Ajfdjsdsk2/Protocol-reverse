import json
import os
from typing import Dict, List, Tuple, Optional
from enum import Enum

class Protocol(Enum):
    """Supported protocol types"""
    BACNET = "BACnet"
    MODBUS = "Modbus"
    HTTP = "HTTP"
    CIP = "CIP"         # Common Industrial Protocol
    LON = "LON"         # LonWorks
    DNP3 = "DNP3"       # Distributed Network Protocol
    CUSTOM = "Custom"

class ProtocolAnalyzer:
    def __init__(self, protocol: Protocol = Protocol.BACNET):
        self.protocol = protocol
        self.known_headers = {
            Protocol.BACNET: 4,      # BACnet/IP typically has 4-byte header
            Protocol.MODBUS: 7,      # Modbus TCP header is usually 7 bytes
            Protocol.HTTP: 0,        # HTTP has no fixed header
            Protocol.CIP: 24,         # CIP typically has 24-byte encapsulation header
            Protocol.LON: 2,          # LON typically has 2-byte header
            Protocol.DNP3: 10         # DNP3 typically has 10-byte header
        }

    def load_data_from_file(self, file_path: str) -> Dict[str, str]:
        """
        加载JSON文件
        Required format: JSON array containing "Hexstream" field
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.lower().endswith('.json'):
            raise ValueError("Only JSON format files are supported")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if not isinstance(data, list):
                raise ValueError("JSON file should contain a message array")
                
            return {str(idx): msg["Hexstream"] for idx, msg in enumerate(data) 
                    if "Hexstream" in msg and isinstance(msg["Hexstream"], str)}
            
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format")
        except Exception as e:
            raise RuntimeError(f"Failed to load file: {str(e)}")

    def analyze_file(
        self, 
        file_path: str,
        verbose: bool = False
    ) -> Tuple[int, Dict[str, int]]:
        """
        Complete analysis process: load file -> analyze -> return results
        Returns: (best split position, dictionary of rule results)
        """
        print(f"\nAnalyzing {os.path.basename(file_path)} [{self.protocol.value} protocol]...")
        
        try:
            # 1. Load data
            data = self.load_data_from_file(file_path)
            if not data:
                raise ValueError("No valid Hexstream data found")
            print(f"Loaded {len(data)} messages")
            
            # 2. Calculate difference features
            diff_list, stable_list = self._calculate_differences(data)
            if verbose:
                self._print_analysis_details(diff_list, stable_list)
            
            # 3. Apply analysis rules
            rule_results = self._apply_rules(diff_list, stable_list)
            best_split = self._adjust_result(rule_results)
            
            # 4. Display results
            self._print_results(best_split, rule_results)
            return best_split, rule_results
            
        except Exception as e:
            print(f"Analysis failed: {str(e)}")
            return -1, {}

    # 具体实现方法
    def _calculate_differences(self, data: Dict[str, str]) -> Tuple[List[int], List[bool]]:
        """计算每个字节的差异特征"""
        min_len = min(len(v)//2 for v in data.values())
        diff_list = []
        stable_list = []

        for pos in range(min_len):
            diffs = []
            keys = list(data.keys())
            for i in range(1, len(keys)):
                try:
                    prev = int(data[keys[i-1]][pos*2:(pos+1)*2], 16)
                    curr = int(data[keys[i]][pos*2:(pos+1)*2], 16)
                    diffs.append(abs(curr - prev))
                except:
                    continue

            diff_list.append(sum(diffs))
            stable = sum(1 for d in diffs if d <= 1) / len(diffs) > 0.9 if diffs else False
            stable_list.append(stable)

        return diff_list, stable_list

    def _apply_rules(self, diff_list: List[int], stable_list: List[bool]) -> Dict[str, int]:
        """应用四条规则分析"""
        results = {}
        
        # Rule 1: 从后向前第一个非零差异
        results['rule1'] = next((i for i in range(len(diff_list)-1, -1, -1) if diff_list[i] != 0), -1)

        # Rule 2: 从后向前第一个大于平均差异
        non_zero = [d for d in diff_list if d != 0]
        avg_diff = sum(non_zero)/len(non_zero) if non_zero else 0
        results['rule2'] = next((i for i in range(len(diff_list)-1, -1, -1) if diff_list[i] > avg_diff), -1)

        # Rule 3: 第一个不稳定位置
        results['rule3'] = next((i for i, stable in enumerate(stable_list) if not stable), -1)

        # Rule 4: 最大增益位置
        gain = [0] * len(diff_list)
        for i in range(1, len(diff_list)):
            gain[i] = gain[i-1] + (avg_diff if stable_list[i] else -diff_list[i])
        results['rule4'] = gain.index(max(gain)) if gain else -1

        return {k: v for k, v in results.items() if v != -1}

    def _adjust_result(self, results: Dict[str, int]) -> int:
        """根据协议特性调整"""
        if not results:
            return 0
            
        if self.protocol in self.known_headers:
            expected = self.known_headers[self.protocol]
            return min(results.values(), key=lambda x: abs(x - expected))
        
        # 优先采用R3、R4
        preferred = [results.get('rule3'), results.get('rule4')]
        valid = [x for x in preferred if x is not None]
        return min(valid) if valid else results.get('rule1', 0)

    def _print_analysis_details(self, diff_list: List[int], stable_list: List[bool]):
        """打印分析细节"""
        print("\nAnalysis details:")
        print("Pos\tDiff\tStable")
        for i, (diff, stable) in enumerate(zip(diff_list[:20], stable_list[:20])):
            print(f"{i}\t{diff}\t{stable}")
        if len(diff_list) > 20:
            print(f"... (total {len(diff_list)} positions)")

    def _print_results(self, best_split: int, rule_results: Dict[str, int]):
        """打印结果"""
        print("\nAnalysis results:")
        print(f"Protocol type: {self.protocol.value}")
        print(f"Recommended split position: Byte {best_split} (Hex position {best_split*2})")
        print("Rule results:")
        for rule, pos in rule_results.items():
            print(f"  {rule.ljust(6)}: Byte {pos}")

# 传输路径
if __name__ == "__main__":
    
    try:
        analyzer = ProtocolAnalyzer(Protocol.LON)
        analyzer.analyze_file(
            file_path="/root/OP-MDIplier/file/lon_1000.json",
            verbose=True
        )
    except Exception as e:
        print(f"analysis error: {str(e)}")