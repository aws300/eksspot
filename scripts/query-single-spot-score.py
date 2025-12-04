#!/usr/bin/env python3
"""查询单个实例类型的 Spot 评分"""

import sys
import boto3
from botocore.exceptions import ClientError

def query_single_spot_score(region, instance_type):
    """查询单个实例类型的 Spot 评分"""
    
    print(f"查询 {instance_type} 在 {region} 区域的 Spot 评分...")
    print()
    
    # 创建 EC2 客户端
    try:
        ec2 = boto3.client('ec2', region_name=region)
    except Exception as e:
        print(f"❌ 错误: 无法连接到区域 {region}")
        print(f"   {str(e)}")
        return False
    
    try:
        # 查询 Spot 评分
        response = ec2.get_spot_placement_scores(
            InstanceTypes=[instance_type],
            TargetCapacity=1,
            SingleAvailabilityZone=False,
            TargetCapacityUnitType='units'
        )
        
        scores = response.get('SpotPlacementScores', [])
        
        if not scores:
            print(f"⚠️  没有找到 {instance_type} 的 Spot 评分数据")
            return True
        
        # 查找当前区域的评分
        target_region_score = None
        for score_item in scores:
            if score_item.get('Region') == region:
                target_region_score = score_item.get('Score')
                break
        
        # 显示结果
        print(f"=== {instance_type} Spot 评分结果 ===")
        print(f"目标区域 ({region}): ", end="")
        
        if target_region_score is not None:
            print(f"Score {target_region_score}")
        else:
            print("无评分数据")
        
        print()
        print("所有区域评分:")
        print("━" * 40)
        
        # 按评分排序显示所有区域
        sorted_scores = sorted(scores, key=lambda x: x.get('Score', 0), reverse=True)
        
        for score_item in sorted_scores:
            region_name = score_item.get('Region', 'Unknown')
            score = score_item.get('Score', 'N/A')
            marker = " ← 目标区域" if region_name == region else ""
            print(f"{region_name:20} Score: {score}{marker}")
        
        print()
        print(f"共找到 {len(scores)} 个区域的评分数据")
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        
        if "MaxConfigLimitExceeded" in str(e):
            print(f"⚠️  API 配置限制: 24小时内查询配置数量已达上限")
        elif "Unsupported" in str(e) or "InvalidInstanceType" in str(e):
            print(f"⚠️  不支持的实例类型: {instance_type}")
        else:
            print(f"❌ API 错误: {error_code} - {error_msg}")
        
        return False
    
    except Exception as e:
        print(f"❌ 未知错误: {str(e)}")
        return False

def main():
    """主函数"""
    # 解析参数
    if len(sys.argv) != 3:
        print("用法: python3 query-single-spot-score.py <region> <instance_type>")
        print("示例: python3 query-single-spot-score.py ap-southeast-2 c5n.4xlarge")
        sys.exit(1)
    
    region = sys.argv[1]
    instance_type = sys.argv[2]
    
    # 查询评分
    success = query_single_spot_score(region, instance_type)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
