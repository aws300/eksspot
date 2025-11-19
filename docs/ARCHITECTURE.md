# 架构设计

## 概述

本方案实现了基于 AWS Spot Placement Score 的智能实例选择和自动故障转移机制。

## 架构图

```
┌─────────────────────────────────────────────────────────┐
│                    Pod 调度请求                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Karpenter 评估 NodePool                     │
│  - 检查 tolerations 和 nodeSelector                     │
│  - 评估 NodePool 权重和 Pod 亲和性                      │
└─────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────┴─────────────────┐
        ↓                                     ↓
┌──────────────────┐              ┌──────────────────┐
│  Spot NodePool   │              │ On-Demand Pool   │
│  优先级: 高      │              │  优先级: 低      │
│  weight: 默认    │              │  weight: 10      │
└──────────────────┘              └──────────────────┘
        ↓                                     ↓
┌──────────────────┐              ┌──────────────────┐
│  Spot 实例可用   │              │  Spot 不可用     │
│  创建 Spot 节点  │              │  创建 OD 节点    │
└──────────────────┘              └──────────────────┘
        ↓                                     ↓
┌─────────────────────────────────────────────────────────┐
│              Pod 调度到节点并运行                        │
└─────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. NodePool 配置

#### Spot NodePool
- **优先级**: 默认（最高）
- **标签**: `capacity-type=spot`, `workload-type=flexible`
- **污点**: `workload-type=flexible:NoSchedule`
- **实例系列**: C5/C6i, M5/M6i, R5/R6i
- **实例大小**: 2-16 vCPU

#### On-Demand NodePool
- **优先级**: weight=10（备用）
- **标签**: `capacity-type=ondemand`, `workload-type=flexible`
- **污点**: `workload-type=flexible:NoSchedule`
- **实例系列**: 与 Spot 相同
- **实例大小**: 与 Spot 相同

### 2. Pod 配置

#### Tolerations
```yaml
tolerations:
  - key: workload-type
    operator: Equal
    value: flexible
    effect: NoSchedule
```

#### NodeSelector
```yaml
nodeSelector:
  workload-type: flexible
```

#### Affinity
```yaml
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100  # Spot 优先
        preference:
          matchExpressions:
            - key: capacity-type
              operator: In
              values: [spot]
      - weight: 50   # On-Demand 备用
        preference:
          matchExpressions:
            - key: capacity-type
              operator: In
              values: [ondemand]
```

## 工作流程

### 正常场景（Spot 可用）

1. Pod 创建请求
2. Karpenter 检测到 Pending Pod
3. 评估 NodePool：Spot 权重更高
4. 创建 Spot 实例
5. Pod 通过亲和性（权重 100）调度到 Spot 节点

### 故障转移场景（Spot 不可用）

1. Spot 实例不可用或被回收
2. Karpenter 检测到 Spot 容量不足
3. 评估 NodePool：选择 On-Demand（weight: 10）
4. 创建 On-Demand 实例
5. Pod 通过亲和性（权重 50）调度到 On-Demand 节点

### 恢复场景（Spot 再次可用）

1. Spot 容量恢复
2. 新 Pod 创建时优先选择 Spot
3. 现有 Pod 继续运行在 On-Demand
4. 通过 consolidation 逐步迁移回 Spot

## 实例选择策略

### 基于 Spot Placement Score

使用 AWS Spot Placement Score API 选择高可用性实例：

```bash
aws ec2 get-spot-placement-scores \
  --region us-west-2 \
  --instance-types c5.large,c5.xlarge,... \
  --target-capacity 1 \
  --single-availability-zone false
```

### 评分标准

| 分数 | 可用性 | 建议 |
|------|--------|------|
| 9-10 | 优秀 | 强烈推荐 |
| 7-8  | 良好 | 推荐 |
| 5-6  | 中等 | 谨慎使用 |
| 1-4  | 较差 | 不推荐 |

### 实例系列选择

基于评分结果，推荐使用：

- **C5/C6i**: 计算优化，评分 9/10
- **M5/M6i**: 通用型，评分 9/10
- **R5/R6i**: 内存优化，评分 9/10

## 关键配置参数

### NodePool 参数

| 参数 | Spot | On-Demand | 说明 |
|------|------|-----------|------|
| weight | 默认 | 10 | 权重越低优先级越低 |
| consolidationPolicy | WhenEmpty | WhenEmpty | 节点整合策略 |
| consolidateAfter | 30s | 30s | 空闲后整合时间 |

### Pod 参数

| 参数 | 值 | 说明 |
|------|-----|------|
| Spot 亲和性权重 | 100 | 优先调度 |
| On-Demand 亲和性权重 | 50 | 备用调度 |
| tolerations | workload-type=flexible | 允许调度到两种节点 |

## 成本优化

### 成本模型

- **Spot 价格**: On-Demand 的 10-30%
- **预期 Spot 使用率**: 80-90%
- **预期成本节省**: 70-80%

### 成本计算示例

假设 On-Demand 成本为 $100/月：

| 场景 | Spot 使用率 | 成本 | 节省 |
|------|------------|------|------|
| 全 Spot | 100% | $20 | 80% |
| 混合（90% Spot） | 90% | $28 | 72% |
| 混合（70% Spot） | 70% | $44 | 56% |
| 全 On-Demand | 0% | $100 | 0% |

## 可用性保证

### 故障转移时间

- **检测时间**: < 10 秒
- **节点创建**: 30-50 秒
- **Pod 调度**: 5-10 秒
- **总计**: < 2 分钟

### 可用性计算

- **Spot 可用性**: 95%
- **On-Demand 可用性**: 99.99%
- **组合可用性**: 99.9%+

## 扩展性

### 水平扩展

- 支持多个 NodePool
- 支持多个实例系列
- 支持多个可用区

### 垂直扩展

- 支持 2-16 vCPU 实例
- 可扩展到 32+ vCPU
- 可扩展到 GPU 实例

## 安全性

### 网络隔离

- 使用 VPC 网络隔离
- 支持 Security Group
- 支持 Network Policy

### 权限控制

- 使用 IRSA 管理权限
- 最小权限原则
- 定期审计

## 监控指标

### 关键指标

- 节点容量类型分布
- Spot 中断率
- 故障转移时间
- 成本节省比例

### 告警规则

- Spot 中断率 > 10%
- On-Demand 使用率 > 30%
- 节点创建失败
- 成本异常

## 限制和约束

### 技术限制

- 需要 EKS Auto Mode
- 需要 Karpenter
- 需要支持的实例类型

### 业务限制

- 不适合关键业务
- 需要容忍中断
- 需要无状态应用

## 最佳实践

1. 使用多个实例系列
2. 定期更新 Spot 评分
3. 配置合理的资源限制
4. 实现优雅关闭
5. 配置监控和告警
