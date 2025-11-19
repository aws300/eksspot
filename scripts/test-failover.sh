#!/bin/bash
# 测试 Spot NodePool 删除场景（模拟 Spot 完全不可用）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Spot 故障转移测试"
echo "=========================================="

echo -e "\n[1/6] 初始状态检查"
kubectl get pods -n default -l app=spot-demo -o wide
echo ""
kubectl get nodepools | grep workload

echo -e "\n[2/6] 删除 Spot NodePool（模拟 Spot 不可用）"
kubectl delete nodepool workload-spot
echo "✓ Spot NodePool 已删除"

echo -e "\n[3/6] 等待 Pod 重新调度（60秒）..."
for i in {1..12}; do
  echo -n "."
  sleep 5
done
echo ""

echo -e "\n[4/6] 检查 Pod 新状态"
kubectl get pods -n default -l app=spot-demo -o wide

echo -e "\n[5/6] 检查节点容量类型"
kubectl get nodes -L karpenter.sh/capacity-type,workload-type | grep -E "NAME|workload" || true

echo -e "\n[6/6] 恢复 Spot NodePool"
kubectl apply -f "$PROJECT_DIR/configs/nodepool-spot.yaml"

echo -e "\n=========================================="
echo "测试完成！"
echo "=========================================="
echo ""
echo "验证要点："
echo "- Pod 应该运行在新节点上"
echo "- 新节点应该是 On-Demand 类型"
echo "- 所有 Pod 应该处于 Running 状态"
