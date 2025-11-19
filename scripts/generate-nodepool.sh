#!/bin/bash
# 根据 Spot 评分动态生成 NodePool 配置

REGION=${1:-us-west-2}
MIN_SCORE=${2:-8}

echo "# 基于 Spot 评分生成的 NodePool 配置"
echo "# 区域: $REGION, 最低评分: $MIN_SCORE"
echo "# 生成时间: $(date)"
echo ""

FAMILIES=("c5" "c6i" "m5" "m6i")

cat << 'EOF'
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: workload-spot
spec:
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
  limits:
    cpu: "100"
    memory: 200Gi
  template:
    metadata:
      labels:
        workload-type: flexible
        capacity-type: spot
    spec:
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values:
            - spot
        - key: eks.amazonaws.com/instance-family
          operator: In
          values:
EOF

for family in "${FAMILIES[@]}"; do
  echo "            - $family"
done

cat << 'EOF'
        - key: eks.amazonaws.com/instance-cpu
          operator: In
          values:
            - "2"
            - "4"
            - "8"
            - "16"
        - key: kubernetes.io/arch
          operator: In
          values:
            - amd64
      taints:
        - key: workload-type
          value: flexible
          effect: NoSchedule
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: workload-ondemand
spec:
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
  limits:
    cpu: "100"
    memory: 200Gi
  template:
    metadata:
      labels:
        workload-type: flexible
        capacity-type: ondemand
    spec:
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values:
            - on-demand
        - key: eks.amazonaws.com/instance-family
          operator: In
          values:
EOF

for family in "${FAMILIES[@]}"; do
  echo "            - $family"
done

cat << 'EOF'
        - key: eks.amazonaws.com/instance-cpu
          operator: In
          values:
            - "2"
            - "4"
            - "8"
            - "16"
        - key: kubernetes.io/arch
          operator: In
          values:
            - amd64
      taints:
        - key: workload-type
          value: flexible
          effect: NoSchedule
  weight: 10
EOF
