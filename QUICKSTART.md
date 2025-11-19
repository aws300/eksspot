# 快速开始指南

## 前提条件

- EKS Auto Mode 集群已创建
- kubectl 已配置
- 具有管理员权限

## 5 分钟部署

### 步骤 1: 查询 Spot 评分

```bash
cd /home/core/spot-ondemand-eks-nodepool
./scripts/query-spot-score.sh us-west-2 8
```

**输出示例**:
```
查询 us-west-2 区域评分 >= 8 的 Spot 实例类型...
ap-east-1
ap-northeast-1
ap-southeast-1
...
```

### 步骤 2: 部署 NodePool

```bash
# 部署 Spot NodePool（优先）
kubectl apply -f configs/nodepool-spot.yaml

# 部署 On-Demand NodePool（备用）
kubectl apply -f configs/nodepool-ondemand.yaml

# 验证
kubectl get nodepools | grep workload
```

**预期输出**:
```
workload-spot       default     0       True    5s
workload-ondemand   default     0       True    4s
```

### 步骤 3: 部署应用

```bash
kubectl apply -f configs/deployment.yaml
```

### 步骤 4: 验证部署

```bash
# 等待 Pod 启动
sleep 30

# 查看 Pod 状态
kubectl get pods -n default -l app=spot-demo -o wide

# 验证节点类型
NODE=$(kubectl get pods -n default -l app=spot-demo -o jsonpath='{.items[0].spec.nodeName}')
kubectl get node $NODE -o jsonpath='{.metadata.labels.karpenter\.sh/capacity-type}'
echo ""
```

**预期输出**: `spot`

## 测试故障转移

### 测试 1: Spot 完全不可用

```bash
./scripts/test-failover.sh
```

**预期**: Pod 迁移到 On-Demand 节点，时间 < 2 分钟

### 测试 2: 单个实例被回收

```bash
./scripts/test-reclaim.sh
```

**预期**: Karpenter 优先尝试创建新 Spot，失败则 On-Demand

## 监控

```bash
# 查看节点类型
kubectl get nodes -L karpenter.sh/capacity-type

# 查看 Pod 分布
kubectl get pods -l app=spot-demo -o wide

# 实时监控
watch -n 2 'kubectl get pods -l app=spot-demo -o wide'
```

## 清理

```bash
kubectl delete -f configs/deployment.yaml
kubectl delete -f configs/nodepool-spot.yaml
kubectl delete -f configs/nodepool-ondemand.yaml
```

## 下一步

- 阅读 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 了解架构设计
- 阅读 [docs/BEST-PRACTICES.md](docs/BEST-PRACTICES.md) 学习最佳实践
- 阅读 [docs/TESTING.md](docs/TESTING.md) 了解详细测试方法

## 常见问题

### Pod 一直 Pending？

```bash
kubectl describe pod <pod-name>
```

检查 tolerations 和 nodeSelector 配置。

### 节点未创建？

```bash
kubectl logs -n kube-system -l app.kubernetes.io/name=karpenter
```

查看 Karpenter 日志。

### Spot 实例频繁中断？

- 增加实例类型多样性
- 调整 On-Demand 比例
- 查询最新 Spot 评分
