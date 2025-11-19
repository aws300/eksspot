#!/bin/bash
# 查询指定区域评分最高的 Spot 实例类型

REGION=${1:-us-west-2}
MIN_SCORE=${2:-8}

echo "查询 $REGION 区域评分 >= $MIN_SCORE 的 Spot 实例类型..."

INSTANCE_TYPES=(
  "c5.large" "c5.xlarge" "c5.2xlarge" "c5.4xlarge"
  "c6i.large" "c6i.xlarge" "c6i.2xlarge" "c6i.4xlarge"
  "m5.large" "m5.xlarge" "m5.2xlarge" "m5.4xlarge"
  "m6i.large" "m6i.xlarge" "m6i.2xlarge" "m6i.4xlarge"
  "r5.large" "r5.xlarge" "r5.2xlarge" "r5.4xlarge"
  "r6i.large" "r6i.xlarge" "r6i.2xlarge" "r6i.4xlarge"
)

TYPES_STR=$(IFS=,; echo "${INSTANCE_TYPES[*]}")

aws ec2 get-spot-placement-scores \
  --region $REGION \
  --instance-types $TYPES_STR \
  --target-capacity 1 \
  --single-availability-zone false \
  --query "SpotPlacementScores[?Score>=$MIN_SCORE].Region" \
  --output text | tr '\t' '\n' | sort -u

echo ""
echo "提示：这些区域的 Spot 实例评分 >= $MIN_SCORE"
