#!/bin/bash
# 测试单个 Spot 实例被回收场景（保留 Spot NodePool）

set -e

echo "=========================================="
echo "模拟 Spot 实例被回收测试"
echo "（保留 Spot NodePool）"
echo "=========================================="

echo -e "\n[1/5] 初始状态"
kubectl get pods -n default -l app=spot-demo -o wide
echo ""
kubectl get nodepools | grep workload

SPOT_NODE=$(kubectl get nodes -l capacity-type=spot -o jsonpath='{.items[0].metadata.name}')
if [ -z "$SPOT_NODE" ]; then
  echo "错误: 没有找到 Spot 节点"
  exit 1
fi
echo -e "\n[2/5] 目标 Spot 节点: $SPOT_NODE"

echo -e "\n[3/5] 删除节点（模拟 AWS 回收实例）"
kubectl delete node $SPOT_NODE

echo -e "\n[4/5] 等待 Pod 重新调度（60秒）..."
for i in {1..12}; do
  echo -n "."
  sleep 5
done
echo ""

echo -e "\n[5/5] 最终状态"
kubectl get pods -n default -l app=spot-demo -o wide
echo ""
kubectl get nodes -L karpenter.sh/capacity-type | grep -E "NAME|workload" || true
echo ""
kubectl get nodepools | grep workload

echo -e "\n=========================================="
echo "测试完成！"
echo "=========================================="
echo ""
echo "验证要点："
echo "- Spot NodePool 依然存在"
echo "- Pod 重新调度（可能在新 Spot 或 On-Demand）"
echo "- 如果 Spot 可用，优先创建 Spot 节点"
