#!/usr/bin/env python3
"""验证项目设置和文档中的命令"""

import os
import sys
import subprocess

def run_command(cmd, description):
    """运行命令并返回结果"""
    print(f"\n{'='*60}")
    print(f"测试: {description}")
    print(f"命令: {cmd}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ 成功")
            if result.stdout:
                print(result.stdout[:500])
            return True
        else:
            print("❌ 失败")
            print(f"错误: {result.stderr[:500]}")
            return False
    except subprocess.TimeoutExpired:
        print("⚠️  超时")
        return False
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        return False

def main():
    """主函数"""
    os.chdir('/home/core/spot-ondemand-eks-nodepool')
    
    tests = [
        ("python3 scripts/query-spot-score.py us-west-2 9", "查询 Spot 评分"),
        ("./scripts/generate-nodepool.sh us-west-2 8 | head -20", "生成 NodePool 配置"),
        ("ls -l configs/", "检查配置文件"),
        ("ls -l scripts/", "检查脚本文件"),
        ("kubectl get nodepools 2>&1 | head -5", "检查 kubectl 连接"),
    ]
    
    results = []
    for cmd, desc in tests:
        results.append(run_command(cmd, desc))
    
    print(f"\n{'='*60}")
    print("验证总结")
    print(f"{'='*60}")
    print(f"总计: {len(results)} 个测试")
    print(f"成功: {sum(results)} 个")
    print(f"失败: {len(results) - sum(results)} 个")
    
    if all(results):
        print("\n✅ 所有测试通过！")
        return 0
    else:
        print("\n⚠️  部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
