# EKS Auto Mode: Spot/On-Demand 混合部署方案

基于 AWS Spot Placement Score 的智能实例选择和自动故障转移解决方案。

## 🎯 核心功能

- ✅ **智能实例选择**: 基于 Spot Placement Score 选择高可用性实例
- ✅ **自动故障转移**: Spot 不可用时自动切换到 On-Demand
- ✅ **成本优化**: 节省 70-90% 计算成本
- ✅ **动态配置**: 根据实时评分生成 NodePool 配置

## 📁 项目结构

```
eksspot/
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
│   ├── query-spot-score.py      # 批量查询 Spot 评分
│   ├── query-single-spot-score.py # 查询单个实例类型评分
│   ├── generate-nodepool.sh     # 生成 NodePool 配置
│   ├── test-failover.sh         # 测试故障转移
│   └── test-reclaim.sh          # 测试实例回收
└── examples/                    # 示例代码
    ├── Dockerfile               # 示例应用镜像
    └── app.py                   # 示例应用代码
```

## 🚀 快速开始

### 1. 查询 Spot 评分

#### 批量查询多个实例类型

```bash
# 基本用法 (默认: ap-southeast-2, 评分>=8, 2xlarge-12xlarge, x86架构, 5代及以上, CMRT系列)
python3 scripts/query-spot-score.py ap-southeast-2

# 自定义参数
python3 scripts/query-spot-score.py <region> [min_score] [min_size] [max_size] [x86_only] [interval_ms] [min_generation] [instance_families]

# 示例: 只查询C系列实例，评分>=3，6代及以上
python3 scripts/query-spot-score.py ap-southeast-2 3 2xlarge 4xlarge true 0 6 c

# 示例: 只查询M和R系列，评分>=1，查询间隔500ms，5代及以上
python3 scripts/query-spot-score.py us-west-2 1 2xlarge 8xlarge false 500 5 mr

# 示例: 只查询计算优化C系列，ARM架构也包含
python3 scripts/query-spot-score.py us-west-2 8 2xlarge 8xlarge false 0 6 c
```

**参数说明**:
- `region`: AWS 区域 (必需)
- `min_score`: 最低评分阈值 (默认: 8)
- `min_size`: 最小实例规格 (默认: 2xlarge)
- `max_size`: 最大实例规格 (默认: 12xlarge)
- `x86_only`: 是否只包含 x86 架构 (默认: true)
- `interval_ms`: 查询间隔毫秒数 (默认: 0)
- `min_generation`: 最低机器代数 (默认: 5)
- `instance_families`: 实例系列过滤 (默认: cmrt)
  - `c`: 计算优化 (C5, C6i 等)
  - `m`: 通用型 (M5, M6i 等)
  - `r`: 内存优化 (R5, R6i 等)
  - `t`: 突发性能 (T3, T4g 等)
  - 可组合使用: `cm` (C+M系列), `mr` (M+R系列)

#### 查询单个实例类型

```bash
# 查询单个实例类型的全球 Spot 评分
python3 scripts/query-single-spot-score.py <region> <instance_type>

# 示例: 查询 c5n.4xlarge 在 ap-southeast-2 的评分
python3 scripts/query-single-spot-score.py ap-southeast-2 c5n.4xlarge

# 示例: 查询 m5.2xlarge 在 us-west-2 的评分
python3 scripts/query-single-spot-score.py us-west-2 m5.2xlarge
```

**输出示例**:
```
找到 13 个符合条件的实例类型:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. c4.4xlarge
  2. c5n.2xlarge
  3. c6i.4xlarge
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

开始查询 Spot 评分...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. c4.4xlarge           Score: 3
  2. c5n.2xlarge          Score: 3
  3. c6i.4xlarge          Score: N/A

在 ap-southeast-2 区域的高评分实例类型（评分 >= 3）:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
c4.4xlarge      Score:  3
c5n.2xlarge     Score:  3

共找到 2 个高评分实例类型
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
| `query-spot-score.py` | 批量查询 Spot 实例评分 |
| `query-single-spot-score.py` | 查询单个实例类型的全球 Spot 评分 |
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
