# EKS Auto Mode: Spot/On-Demand 混合部署方案

基于 AWS Spot Placement Score 的智能实例选择和自动故障转移解决方案。

## 🎯 核心功能

- ✅ **智能实例选择**: 基于 Spot Placement Score 选择高可用性实例
- ✅ **自动故障转移**: Spot 不可用时自动切换到 On-Demand
- ✅ **成本优化**: 节省 70-90% 计算成本
- ✅ **动态配置**: 根据实时评分生成 NodePool 配置

## 📁 项目结构

```
spot-ondemand-eks-nodepool/
├── README.md                    # 本文档
├── QUICKSTART.md                # 快速开始指南
├── docs/                        # 详细文档
│   ├── ARCHITECTURE.md          # 架构设计
│   ├── BEST-PRACTICES.md        # 最佳实践
│   └── TESTING.md               # 测试指南
├── configs/                     # 配置文件
│   ├── nodepool-spot.yaml       # Spot NodePool
│   ├── nodepool-ondemand.yaml   # On-Demand NodePool
│   └── deployment.yaml          # 示例应用
├── scripts/                     # 工具脚本
│   ├── query-spot-score.sh      # 查询 Spot 评分
│   ├── generate-nodepool.sh     # 生成 NodePool 配置
│   ├── test-failover.sh         # 测试故障转移
│   └── test-reclaim.sh          # 测试实例回收
└── examples/                    # 示例代码
    ├── Dockerfile               # 示例应用镜像
    └── app.py                   # 示例应用代码
```

## 🚀 快速开始

### 1. 查询 Spot 评分

```bash
cd /home/core/spot-ondemand-eks-nodepool
./scripts/query-spot-score.sh us-west-2 8
```

### 2. 部署 NodePool

```bash
kubectl apply -f configs/nodepool-spot.yaml
kubectl apply -f configs/nodepool-ondemand.yaml
```

### 3. 部署应用

```bash
kubectl apply -f configs/deployment.yaml
```

### 4. 验证部署

```bash
kubectl get nodepools
kubectl get pods -l app=spot-demo -o wide
```

## 📊 预期效果

| 指标 | 结果 |
|------|------|
| 成本节省 | 70-90% |
| 故障转移时间 | < 2 分钟 |
| Spot 评分 | 9/10 |
| 可用性 | 99.9%+ |

## 📖 文档

- **[QUICKSTART.md](QUICKSTART.md)** - 5 分钟快速上手
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - 架构设计详解
- **[docs/BEST-PRACTICES.md](docs/BEST-PRACTICES.md)** - 完整最佳实践
- **[docs/TESTING.md](docs/TESTING.md)** - 测试方法和验证

## 🔧 工具脚本

| 脚本 | 功能 |
|------|------|
| `query-spot-score.sh` | 查询 Spot 实例评分 |
| `generate-nodepool.sh` | 动态生成 NodePool 配置 |
| `test-failover.sh` | 测试 Spot 完全不可用场景 |
| `test-reclaim.sh` | 测试单个实例被回收场景 |

## 💡 关键配置

### NodePool 权重策略

- **Spot NodePool**: 默认权重（优先）
- **On-Demand NodePool**: weight=10（备用）

### Pod 亲和性

- **Spot**: 权重 100（优先调度）
- **On-Demand**: 权重 50（备用调度）

### 实例类型（基于评分 >= 8）

- C5/C6i: 计算优化（2-16 vCPU）
- M5/M6i: 通用型（2-16 vCPU）
- R5/R6i: 内存优化（2-16 vCPU）

## 🧪 测试

```bash
# 测试 Spot 完全不可用
./scripts/test-failover.sh

# 测试单个实例被回收
./scripts/test-reclaim.sh
```

## 📈 监控

```bash
# 查看节点类型分布
kubectl get nodes -L karpenter.sh/capacity-type

# 查看 Pod 分布
kubectl get pods -l app=spot-demo -o wide

# 查看 Karpenter 日志
kubectl logs -n kube-system -l app.kubernetes.io/name=karpenter -f
```

## 🔗 相关资源

- [AWS Spot Placement Score](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/work-with-spot-placement-score.html)
- [Karpenter 文档](https://karpenter.sh/)
- [EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)

## 📝 集群信息

- **集群名称**: orbit
- **区域**: us-west-2
- **类型**: EKS Auto Mode

## 🤝 支持

遇到问题？查看：
1. [QUICKSTART.md](QUICKSTART.md) - 快速开始
2. [docs/TESTING.md](docs/TESTING.md) - 故障排查
3. Karpenter 日志
