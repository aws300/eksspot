#!/usr/bin/env python3
"""查询指定区域的 Spot 实例评分"""

import sys
import json
import boto3
import time
from botocore.exceptions import ClientError

def extract_generation(instance_type):
    """提取实例类型的代数"""
    # 例如: c5.2xlarge -> 5, m6i.4xlarge -> 6, r7g.large -> 7
    import re
    match = re.match(r'[cmrt](\d+)', instance_type)
    return int(match.group(1)) if match else 0

def get_instance_types(region, min_size="2xlarge", max_size="12xlarge", x86_only=True, exclude_metal=True, exclude_gpu=True, min_generation=5, instance_families="cmrt"):
    """动态查询符合条件的实例类型"""
    
    print(f"正在查询 {region} 区域的实例类型...")
    
    # 创建 EC2 客户端
    ec2 = boto3.client('ec2', region_name=region)
    
    # 定义尺寸映射 - 修复尺寸过滤bug
    size_order = ["nano", "micro", "small", "medium", "large", "xlarge", "2xlarge", "4xlarge", 
                  "6xlarge", "8xlarge", "12xlarge", "16xlarge", "24xlarge", "32xlarge", "48xlarge", "metal"]
    
    min_idx = size_order.index(min_size) if min_size in size_order else 0
    max_idx = size_order.index(max_size) if max_size in size_order else len(size_order) - 1
    
    valid_sizes = size_order[min_idx:max_idx + 1]
    
    try:
        # 查询所有实例类型 - 修复分页问题
        all_instances = []
        next_token = None
        
        while True:
            if next_token:
                response = ec2.describe_instance_types(NextToken=next_token)
            else:
                response = ec2.describe_instance_types()
            
            all_instances.extend(response['InstanceTypes'])
            
            if 'NextToken' not in response:
                break
            next_token = response['NextToken']
        
        instance_types = []
        
        for instance in all_instances:
            instance_type = instance['InstanceType']
            
            # 过滤实例系列
            if not any(instance_type.startswith(prefix) for prefix in instance_families.lower()):
                continue
            
            # 过滤机器代数
            generation = extract_generation(instance_type)
            if generation < min_generation:
                continue
            
            # 过滤尺寸 - 修复尺寸匹配bug
            size = instance_type.split('.')[-1]
            # 处理特殊情况如 metal-24xl
            if 'metal' in size:
                size = 'metal'
            if size not in valid_sizes:
                continue
            
            # 过滤 metal
            if exclude_metal and 'metal' in size:
                continue
            
            # 过滤架构
            if x86_only:
                arch = instance.get('ProcessorInfo', {}).get('SupportedArchitectures', [])
                if 'x86_64' not in arch:
                    continue
            
            # 过滤 GPU
            if exclude_gpu and instance.get('GpuInfo') is not None:
                continue
            
            instance_types.append(instance_type)
        
        instance_types.sort()
        return instance_types
        
    except Exception as e:
        print(f"❌ 查询实例类型失败: {str(e)}")
        return []

def query_spot_scores(region, min_score=8, min_size="2xlarge", max_size="12xlarge", x86_only=True, interval_ms=0, min_generation=5, instance_families="cmrt"):
    """查询 Spot 实例评分"""
    
    print(f"查询 {region} 区域的 Spot 实例评分...")
    print()
    
    # 创建 EC2 客户端
    try:
        ec2 = boto3.client('ec2', region_name=region)
    except Exception as e:
        print(f"❌ 错误: 无法连接到区域 {region}")
        print(f"   {str(e)}")
        return False
    
    # 动态获取实例类型
    instance_types = get_instance_types(region, min_size, max_size, x86_only, min_generation=min_generation, instance_families=instance_families)
    
    if not instance_types:
        print("❌ 没有找到符合条件的实例类型")
        return False
    
    print(f"找到 {len(instance_types)} 个符合条件的实例类型:")
    print("━" * 80)
    for i, instance_type in enumerate(instance_types, 1):
        print(f"{i:3d}. {instance_type}")
    print("━" * 80)
    print()
    
    print("开始查询 Spot 评分...")
    if interval_ms > 0:
        print(f"查询间隔: {interval_ms}ms")
    print("━" * 80)
    
    # 查询每个实例类型的评分并显示
    all_results = []
    api_errors = 0
    
    for i, instance_type in enumerate(instance_types, 1):
        score = "N/A"
        try:
            response = ec2.get_spot_placement_scores(
                InstanceTypes=[instance_type],
                TargetCapacity=1,
                SingleAvailabilityZone=False,
                TargetCapacityUnitType='units'
            )
            
            scores = response.get('SpotPlacementScores', [])
            # 查找当前区域的评分
            for score_item in scores:
                if score_item.get('Region') == region:
                    score = score_item.get('Score', "N/A")
                    break
            # 如果没有找到当前区域，尝试查找任何有效评分
            if score == "N/A" and scores:
                for score_item in scores:
                    if score_item.get('Score') is not None:
                        score = score_item.get('Score')
                        break
                        
        except ClientError as e:
            api_errors += 1
            if "MaxConfigLimitExceeded" in str(e):
                score = "LIMIT"
            elif "Unsupported" in str(e) or "InvalidInstanceType" in str(e):
                score = "UNSUPPORTED"
        except Exception as e:
            api_errors += 1
            score = "ERROR"
        
        all_results.append({
            'InstanceType': instance_type,
            'Score': score,
            'Region': region
        })
        
        print(f"{i:3d}. {instance_type:20} Score: {score}")
        
        # 添加时间间隔
        if interval_ms > 0 and i < len(instance_types):
            time.sleep(interval_ms / 1000.0)
    
    print("━" * 80)
    
    if api_errors > 0:
        print(f"⚠️  {api_errors} 个实例类型查询失败 (API限制或不支持)")
    
    print()
    
    # 过滤高评分实例
    results = [r for r in all_results if isinstance(r['Score'], int) and r['Score'] >= min_score]
    
    if not results:
        print(f"⚠️  在 {region} 区域没有找到评分 >= {min_score} 的实例类型")
        print()
        return True
    
    # 排序并显示高评分实例
    results.sort(key=lambda x: x.get('Score', 0), reverse=True)
    
    print(f"在 {region} 区域的高评分实例类型（评分 >= {min_score}）:")
    print("━" * 50)
    for item in results:
        instance_type = item.get('InstanceType', 'Unknown')
        score = item.get('Score', 0)
        print(f"{instance_type:15} Score: {score:2d}")
    
    print()
    print(f"共找到 {len(results)} 个高评分实例类型")
    return True

def main():
    """主函数"""
    # 解析参数
    if len(sys.argv) < 2:
        print("用法: python3 query-spot-score.py <region> [min_score] [min_size] [max_size] [x86_only] [interval_ms] [min_generation] [instance_families]")
        print("示例: python3 query-spot-score.py ap-southeast-2 3 2xlarge 12xlarge true 500 6 c")
        print("实例系列: c(计算优化) m(通用) r(内存优化) t(突发性能) 或组合如 cm")
        sys.exit(1)
    
    region = sys.argv[1]
    min_score = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    min_size = sys.argv[3] if len(sys.argv) > 3 else "2xlarge"
    max_size = sys.argv[4] if len(sys.argv) > 4 else "12xlarge"
    x86_only = sys.argv[5].lower() == 'true' if len(sys.argv) > 5 else True
    interval_ms = int(sys.argv[6]) if len(sys.argv) > 6 else 0
    min_generation = int(sys.argv[7]) if len(sys.argv) > 7 else 5
    instance_families = sys.argv[8] if len(sys.argv) > 8 else "cmrt"
    
    # 查询评分
    success = query_spot_scores(region, min_score, min_size, max_size, x86_only, interval_ms, min_generation, instance_families)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
