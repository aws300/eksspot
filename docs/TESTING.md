# 测试指南

## 测试概述

本文档提供完整的测试方法和验证步骤。

## 测试环境

- **集群**: orbit
- **区域**: us-west-2
- **类型**: EKS Auto Mode

## 测试场景

### 场景 1: Spot 优先调度

**目的**: 验证 Pod 优先调度到 Spot 节点

**步骤**:
```bash
# 1. 确保两个 NodePool 都存在
kubectl get nodepools | grep workload

# 2. 部署应用
kubectl apply -f configs/deployment.yaml

# 3. 等待 Pod 启动
sleep 30

# 4. 查看 Pod 调度
kubectl get pods -n default -l app=spot-demo -o wide

# 5. 验证节点类型
NODE=$(kubectl get pods -n default -l app=spot-demo -o jsonpath='{.items[0].spec.nodeName}')
kubectl get node $NODE -o jsonpath='{.metadata.labels.karpenter\.sh/capacity-type}'
```

**预期结果**: 输出 `spot`

---

### 场景 2: Spot NodePool 删除

**目的**: 模拟 Spot 完全不可用，验证自动切换到 On-Demand

**步骤**:
```bash
./scripts/test-failover.sh
```

**预期结果**:
- ✅ Pod 迁移到 On-Demand 节点
- ✅ 故障转移时间 < 2 分钟
- ✅ 所有 Pod 保持 Running 状态

**详细验证**:
```bash
# 查看新节点类型
NODE=$(kubectl get pods -n default -l app=spot-demo -o jsonpath='{.items[0].spec.nodeName}')
kubectl get node $NODE -o jsonpath='{.metadata.labels.karpenter\.sh/capacity-type}'
# 应该输出: on-demand
```

---

### 场景 3: Spot 节点删除

**目的**: 模拟单个 Spot 实例被回收，验证自动恢复

**步骤**:
```bash
./scripts/test-reclaim.sh
```

**预期结果**:
- ✅ Spot NodePool 依然存在
- ✅ Karpenter 优先尝试创建新 Spot
- ✅ 如果 Spot 不可用，切换到 On-Demand

**详细验证**:
```bash
# 验证 Spot NodePool 存在
kubectl get nodepool workload-spot

# 查看新节点类型
kubectl get nodes -L karpenter.sh/capacity-type
```

---

### 场景 4: 手动驱逐测试

**目的**: 模拟优雅关闭流程

**步骤**:
```bash
# 1. 获取 Spot 节点
SPOT_NODE=$(kubectl get nodes -l capacity-type=spot -o jsonpath='{.items[0].metadata.name}')

# 2. 标记节点不可调度
kubectl cordon $SPOT_NODE

# 3. 驱逐 Pod（2 分钟优雅期）
kubectl drain $SPOT_NODE \
  --ignore-daemonsets \
  --delete-emptydir-data \
  --grace-period=120

# 4. 观察 Pod 重新调度
kubectl get pods -l app=spot-demo -o wide -w

# 5. 删除节点
kubectl delete node $SPOT_NODE
```

**预期结果**:
- ✅ Pod 优雅关闭（120 秒）
- ✅ Pod 重新调度成功
- ✅ 应用无数据丢失

---

### 场景 5: 压力测试

**目的**: 验证大规模调度能力

**步骤**:
```bash
# 1. 扩展副本数
kubectl scale deployment spot-demo --replicas=10

# 2. 观察调度
watch kubectl get pods -l app=spot-demo -o wide

# 3. 查看节点创建
kubectl get nodes -L karpenter.sh/capacity-type

# 4. 恢复副本数
kubectl scale deployment spot-demo --replicas=3
```

**预期结果**:
- ✅ 所有 Pod 成功调度
- ✅ 优先使用 Spot 节点
- ✅ 节点自动扩展

---

## 验证清单

### 部署验证

- [ ] NodePool 创建成功
- [ ] Pod 成功启动
- [ ] Pod 调度到 Spot 节点
- [ ] 节点标签正确
- [ ] 污点和容忍配置正确

### 故障转移验证

- [ ] Spot 不可用时切换到 On-Demand
- [ ] 故障转移时间 < 2 分钟
- [ ] Pod 无数据丢失
- [ ] 应用服务持续可用

### 性能验证

- [ ] 节点创建时间 < 1 分钟
- [ ] Pod 调度时间 < 10 秒
- [ ] 资源利用率合理

### 成本验证

- [ ] Spot 使用率 > 70%
- [ ] 成本节省 > 60%
- [ ] 无异常成本

---

## 监控命令

### 实时监控 Pod

```bash
watch -n 2 'kubectl get pods -l app=spot-demo -o wide'
```

### 实时监控节点

```bash
watch -n 2 'kubectl get nodes -L karpenter.sh/capacity-type'
```

### 查看 Karpenter 日志

```bash
kubectl logs -n kube-system -l app.kubernetes.io/name=karpenter -f
```

### 查看事件

```bash
kubectl get events -A --sort-by='.lastTimestamp' | grep -i "spot\|node"
```

---

## 故障排查

### Pod Pending

**检查**:
```bash
kubectl describe pod <pod-name>
```

**常见原因**:
1. tolerations 配置错误
2. nodeSelector 不匹配
3. 资源不足
4. NodePool 未就绪

**解决方案**:
```bash
# 检查 Pod 配置
kubectl get pod <pod-name> -o yaml | grep -A 10 "tolerations\|nodeSelector"

# 检查 NodePool
kubectl get nodepools -o yaml
```

### 节点未创建

**检查**:
```bash
kubectl logs -n kube-system -l app.kubernetes.io/name=karpenter --tail=100
```

**常见原因**:
1. 实例类型不可用
2. 配额限制
3. NodePool 配置错误

**解决方案**:
```bash
# 检查 NodePool 状态
kubectl describe nodepool workload-spot

# 查询 Spot 可用性
python3 scripts/query-spot-score.py us-west-2 8
```

### Spot 频繁中断

**检查**:
```bash
# 统计中断次数
kubectl get events -A | grep -i "spot.*interrupt" | wc -l
```

**解决方案**:
1. 增加实例类型多样性
2. 查询最新 Spot 评分
3. 调整 On-Demand 比例

---

## 性能测试

### 节点创建时间

```bash
# 记录开始时间
START=$(date +%s)

# 创建 Pod
kubectl run test-pod --image=nginx

# 等待 Pod 运行
kubectl wait --for=condition=Ready pod/test-pod --timeout=120s

# 计算时间
END=$(date +%s)
echo "节点创建时间: $((END - START)) 秒"

# 清理
kubectl delete pod test-pod
```

### Pod 调度时间

```bash
# 创建 Pod 并记录时间
kubectl run test-pod --image=nginx

# 查看事件时间
kubectl describe pod test-pod | grep -A 5 "Events:"
```

---

## 自动化测试

### 创建测试脚本

```bash
#!/bin/bash
# test-all.sh

echo "运行所有测试..."

echo "1. 测试 Spot 优先调度"
./scripts/test-spot-priority.sh

echo "2. 测试故障转移"
./scripts/test-failover.sh

echo "3. 测试实例回收"
./scripts/test-reclaim.sh

echo "所有测试完成！"
```

### 定期测试

```bash
# 添加到 crontab
0 2 * * 1 /home/core/spot-ondemand-eks-nodepool/test-all.sh
```

---

## 测试报告模板

```markdown
# 测试报告

## 测试信息
- 日期: YYYY-MM-DD
- 测试人: XXX
- 集群: orbit
- 区域: us-west-2

## 测试结果

### 场景 1: Spot 优先调度
- 状态: ✅ 通过
- Pod 调度到: Spot 节点
- 调度时间: 15 秒

### 场景 2: 故障转移
- 状态: ✅ 通过
- 故障转移时间: 45 秒
- Pod 状态: 全部 Running

### 场景 3: 实例回收
- 状态: ✅ 通过
- 恢复时间: 50 秒
- 新节点类型: Spot

## 问题和建议

1. 无问题

## 结论

所有测试通过，系统运行正常。
```

---

## 测试最佳实践

1. **定期测试**: 每月至少测试一次
2. **记录结果**: 保存测试报告
3. **自动化**: 使用脚本自动化测试
4. **监控**: 配置告警监控测试结果
5. **文档**: 更新测试文档
