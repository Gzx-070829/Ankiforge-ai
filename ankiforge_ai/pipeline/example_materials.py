"""Offline, non-sensitive example materials for onboarding and regression tests."""

from dataclasses import dataclass


@dataclass(frozen=True, repr=False)
class ExampleMaterial:
    example_id: str
    title_zh: str
    title_en: str
    description_zh: str
    description_en: str
    recommended_mode: str
    material_text: str
    expected_card_count_range: tuple[int, int]
    source_label: str
    requires_network: bool = False

    def __post_init__(self) -> None:
        strings = (
            self.example_id,
            self.title_zh,
            self.title_en,
            self.description_zh,
            self.description_en,
            self.recommended_mode,
            self.material_text,
            self.source_label,
        )
        if not all(isinstance(value, str) and value.strip() for value in strings):
            raise ValueError("example text fields must be non-empty")
        low, high = self.expected_card_count_range
        if low < 1 or high < low:
            raise ValueError("invalid expected card count range")
        if self.requires_network:
            raise ValueError("built-in examples must be offline")

    def __repr__(self) -> str:
        return (
            "ExampleMaterial("
            f"example_id={self.example_id!r}, recommended_mode={self.recommended_mode!r}, "
            f"expected_card_count_range={self.expected_card_count_range!r})"
        )


def _example(example_id, title_zh, title_en, description_zh, description_en, mode, text):
    return ExampleMaterial(
        example_id=example_id,
        title_zh=title_zh,
        title_en=title_en,
        description_zh=description_zh,
        description_en=description_en,
        recommended_mode=mode,
        material_text=text.strip(),
        expected_card_count_range=(3, 5),
        source_label=f"AnkiForge example: {example_id}",
    )


_EXAMPLES = (
    _example("zh_concept", "中文概念", "Chinese concept", "理解概念与因果", "Understand a concept and its causes", "concept", "交叉验证把数据分成多个训练和验证子集。它重复训练并在未参与当轮训练的数据上评估模型，用于估计泛化能力。折数过少可能让估计不稳定，折数过多则会增加计算成本。"),
    _example("en_concept", "英文概念", "English concept", "英文概念理解", "Concept learning in English", "concept", "Caching stores a reusable result closer to where it is needed. A cache hit avoids repeating expensive work, while a cache miss requires loading or computing the original value. Invalidation matters because stale entries can return outdated results."),
    _example("term_definition", "术语定义", "Term definition", "区分关键术语", "Distinguish key terms", "definition", "精确率表示被模型预测为正类的样本中真正为正类的比例。召回率表示所有真正正类样本中被模型识别出来的比例。两者关注的错误类型不同。"),
    _example("exam_review", "考试复习", "Exam review", "练习标准答题点", "Practice concise scoring points", "exam", "光合作用的光反应发生在类囊体膜上，利用光能生成 ATP 和 NADPH，并释放氧气。碳反应发生在叶绿体基质中，利用 ATP 和 NADPH 固定二氧化碳。"),
    _example("quick_review", "快速回顾", "Quick review", "短问短答复习", "Fast one-fact recall", "quick_review", "HTTP 404 表示资源未找到。HTTP 401 表示请求缺少有效身份验证。HTTP 403 表示服务器理解请求但拒绝授权。"),
    _example("markdown_notes", "Markdown 笔记", "Markdown notes", "体验结构化笔记", "Try structured notes", "concept", "# SQL 连接\n\n- INNER JOIN 只返回两侧匹配的行。\n- LEFT JOIN 保留左表全部行。\n- 连接条件决定哪些行被视为匹配。"),
    _example("compare_contrast", "对比辨析", "Compare and contrast", "辨析相近概念", "Separate similar concepts", "compare_contrast", "进程拥有独立地址空间和系统资源，切换成本通常较高。线程共享所属进程的地址空间，通信更直接，但共享状态需要同步。"),
    _example("process_steps", "流程步骤", "Process steps", "记忆有序流程", "Learn an ordered process", "process_steps", "数据库事务提交前先执行操作并记录变更；系统验证约束；提交时持久化日志；成功后变更对其他事务可见。任何关键步骤失败都应回滚。"),
    _example("formula_rule", "公式规则", "Formula and rule", "掌握公式与条件", "Learn a formula and its conditions", "formula_rule", "匀速直线运动中，速度 v 等于位移变化量 Δx 除以时间变化量 Δt。该关系要求研究区间内速度保持不变，v 的常用单位是米每秒。"),
    _example("mistake_trap", "常见误区", "Mistake trap", "识别易错理解", "Spot a common misconception", "mistake_trap", "相关性描述变量共同变化，但不能单独证明因果。即使相关系数很高，也可能由共同原因、选择偏差或偶然性造成。"),
)

_BY_ID = {item.example_id: item for item in _EXAMPLES}


def all_example_materials() -> tuple[ExampleMaterial, ...]:
    return _EXAMPLES


def get_example_material(example_id: str) -> ExampleMaterial:
    try:
        return _BY_ID[example_id]
    except (KeyError, TypeError):
        raise ValueError(f"unknown example_id: {example_id!r}") from None
