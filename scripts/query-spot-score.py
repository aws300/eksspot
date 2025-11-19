#!/usr/bin/env python3
"""查询指定区域的 Spot 实例评分"""

import sys
import json
import boto3
from botocore.exceptions import ClientError

def query_spot_scores(region, min_score=8):
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
    
    # 定义实例类型
    instance_types = [
        "m5.large", "m5.xlarge", "m5.2xlarge", "m5.4xlarge",
        "c5.large", "c5.xlarge", "c5.2xlarge", "c5.4xlarge",
        "r5.large", "r5.xlarge", "r5.2xlarge", "r5.4xlarge",
        "m6i.large", "m6i.xlarge", "m6i.2xlarge",
        "c6i.large", "c6i.xlarge", "c6i.2xlarge",
        "r6i.large", "r6i.xlarge", "r6i.2xlarge"
    ]
    
    try:
        # 调用 API
        response = ec2.get_spot_placement_scores(
            InstanceTypes=instance_types,
            TargetCapacity=1,
            SingleAvailabilityZone=False
        )
        
        # 过滤评分
        scores = response.get('SpotPlacementScores', [])
        high_scores = [s for s in scores if s.get('Score', 0) >= min_score]
        
        if not high_scores:
            print(f"⚠️  没有找到评分 >= {min_score} 的区域")
            print()
            return True
        
        # 排序并显示
        high_scores.sort(key=lambda x: x.get('Score', 0), reverse=True)
        
        print(f"评分结果（评分 >= {min_score}）:")
        print("━" * 40)
        for item in high_scores[:20]:
            region_name = item.get('Region', 'Unknown')
            score = item.get('Score', 0)
            print(f"{region_name}: Score {score}")
        
        print()
        print(f"查询的实例类型: {', '.join(instance_types[:6])}...")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        
        print(f"⚠️  无法查询该区域的 Spot 评分")
        print()
        print("可能的原因:")
        print("1. 该区域不支持指定的实例类型")
        print("2. 该区域不支持 Spot Placement Score API")
        print()
        print("替代方案:")
        print("1. 使用集群内的 Spot 评分查询服务:")
        print("   kubectl run test-curl --image=curlimages/curl:latest --rm -it --restart=Never -- \\")
        print("     curl -s http://spot-score-checker.default.svc.cluster.local/scores")
        print()
        print("2. 尝试其他区域（如 us-west-2, us-east-1, eu-west-1）")
        print()
        print(f"错误详情: {error_code} - {error_msg}")
        return False
    
    except Exception as e:
        print(f"❌ 未知错误: {str(e)}")
        return False

def main():
    """主函数"""
    # 解析参数
    region = sys.argv[1] if len(sys.argv) > 1 else "us-west-2"
    min_score = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    
    # 查询评分
    success = query_spot_scores(region, min_score)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
